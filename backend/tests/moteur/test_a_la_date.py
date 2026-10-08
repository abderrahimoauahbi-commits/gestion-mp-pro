"""Les données vues au soir d'une date passée (`calcul.a_la_date`) : le journal rejoué jusqu'à
elle, les commandes rouvertes, les retours d'après rendus au reçu, sans le montage d'aujourd'hui.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from gestion_mp_pro.calcul.a_la_date import a_la_date, derniere_date, statut_ouvert
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Donnees,
    FilMonte,
    LigneCommande,
    LigneReception,
    Magasin,
    Metier,
    Mouvement,
    Reception,
)
from gestion_mp_pro.calcul.stock import etat_stock, stock_en_machine
from moteur.fabrique import J1, J2, J3, ecriture, instant, journal


def _bon(statut: str, **autres: datetime) -> Commande:
    return Commande(
        numero="BC-1",
        date_bc=J1,
        fournisseur="F",
        statut=statut,
        lignes=[LigneCommande(numero_bc="BC-1", reference="P50", quantite_commandee=100)],
        **autres,
    )


def _minuit(jour: date) -> datetime:
    return datetime.combine(jour, datetime.min.time())


def test_a_la_date_commande_soldee_ou_annulee_apres_reste_due() -> None:
    """Hérité : test_defauts_c::test_a_la_date_commande_soldee_ou_annulee_apres_reste_due."""
    mouvement = ecriture(1, J1, "STOCK_INITIAL", 10, prix=10)
    solde = journal(mouvement, commandes=[_bon("Soldée", solde_a_la_main_le=_minuit(J3))])
    passe = a_la_date(solde, J2)
    assert passe.commandes[0].statut == "Envoyée"
    assert etat_stock(passe, J2)[0].bc_en_cours == 100
    annule = journal(mouvement, commandes=[_bon("Annulée", annulee_le=_minuit(J3))])
    assert a_la_date(annule, J2).commandes[0].statut == "Envoyée"
    # Clos avant la date : clos ce jour-là.
    avant = journal(mouvement, commandes=[_bon("Annulée", annulee_le=_minuit(J1))])
    assert a_la_date(avant, J2).commandes[0].statut == "Annulée"


def test_a_la_date_retour_plafonne() -> None:
    """Hérité : test_defauts_c::test_a_la_date_retour_plafonne."""
    bon = Commande(
        numero="BC-1",
        date_bc=J1,
        fournisseur="F",
        statut="Soldée",
        lignes=[LigneCommande("BC-1", "P50", quantite_commandee=100, quantite_recue=0)],
    )
    reception = Reception(
        numero="REC-1",
        date_reception=J1,
        numero_bc="BC-1",
        statut="Validée",
        lignes=[
            LigneReception(
                reference="P50", lot_fournisseur="L1", quantite_pesee=100, numero_bc="BC-1"
            )
        ],
    )
    d = journal(
        ecriture(1, J1, "ENTREE_RECEPTION", 100, prix=10),
        ecriture(2, J1, "STOCK_INITIAL", 200, prix=10),
        ecriture(3, J3, "RETOUR_FOURNISSEUR", 250),
        commandes=[bon],
        receptions=[reception],
    )
    passe = a_la_date(d, J2)
    # Le lot a été rendu au-delà de ce que la ligne avait apporté : elle n'a reçu que 100.
    assert passe.commandes[0].lignes[0].quantite_recue == pytest.approx(100)


def test_une_date_passee_rejoue_le_journal_et_rouvre_les_commandes() -> None:
    """Hérité :
    test_valorisation::test_une_date_passee_rejoue_le_journal_et_rouvre_les_commandes.
    """
    commande = Commande(
        numero="BC-1",
        date_bc=J1,
        fournisseur="F",
        statut="Soldée",
        lignes=[LigneCommande("BC-1", "P50", quantite_commandee=500, quantite_recue=500)],
    )
    reception = Reception(
        numero="REC-1",
        date_reception=J3,
        numero_bc="BC-1",
        statut="Validée",
        lignes=[LigneReception(reference="P50", quantite_pesee=500, numero_bc="BC-1")],
    )
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10),
        ecriture(2, J3, "ENTREE_RECEPTION", 500, prix=12),
        commandes=[commande],
        receptions=[reception],
    )
    passe = a_la_date(d, J2)
    assert [m.id for m in passe.mouvements] == [1] and not passe.receptions
    # Le statut d'un bon encore attendu, lu comme le chargeur : prix non confirmés → « Envoyée ».
    assert passe.commandes[0].statut == "Envoyée"
    assert passe.commandes[0].lignes[0].quantite_recue == 0
    assert d.commandes[0].statut == "Soldée"  # l'instantané d'aujourd'hui n'est pas touché
    ligne = etat_stock(passe, J2)[0]
    assert ligne.stock_net == 100 and ligne.bc_en_cours == 500
    assert a_la_date(d, J3) is d


def test_a_une_date_passee_ni_le_montage_ni_les_retours_d_apres() -> None:
    """Hérité :
    test_valeur_et_dates::test_a_une_date_passee_ni_le_montage_ni_les_retours_d_apres.
    """
    j1, j2, j3 = date(2026, 3, 2), date(2026, 3, 9), date(2026, 3, 16)
    d = Donnees(
        articles=[Article(reference="P", prix_unite=10, poids_bobine=2)],
        magasins=[Magasin(code="MAG")],
        metiers=[Metier(code="CRM", densite=10, fils=[FilMonte(reference="P", metres=1)])],
        commandes=[
            Commande(
                numero="BC1",
                date_bc=j1,
                statut="Confirmée",
                lignes=[LigneCommande("BC1", "P", quantite_commandee=1000, quantite_recue=800)],
            )
        ],
        receptions=[
            Reception(
                numero="R1",
                date_reception=j1,
                numero_bc="BC1",
                statut="Validée",
                lignes=[
                    LigneReception(
                        reference="P", lot_fournisseur="L", quantite_pesee=1000, numero_bc="BC1"
                    )
                ],
            )
        ],
        mouvements=[
            Mouvement(
                j1,
                "ENTREE_RECEPTION",
                "P",
                1000,
                lot_fournisseur="L",
                magasin_destination="MAG",
                id=1,
            ),
            Mouvement(
                j3, "RETOUR_FOURNISSEUR", "P", 200, lot_fournisseur="L", magasin_source="MAG", id=2
            ),
        ],
    )
    assert stock_en_machine(d) == {"P": pytest.approx(20)}
    passe = a_la_date(d, j2, aujourdhui=j3)
    # Le fil monté aujourd'hui n'était pas sur le métier le J2.
    assert stock_en_machine(passe) == {}
    # Le retour du J3 n'avait pas encore eu lieu : le J2, le bon avait reçu 1 000 kg.
    assert passe.commandes[0].lignes[0].quantite_recue == pytest.approx(1000)
    # Aujourd'hui, le montage compte.
    assert stock_en_machine(a_la_date(d, j3, aujourdhui=j3)) == {"P": pytest.approx(20)}


def test_la_derniere_date_et_le_statut_d_un_bon_rouvert() -> None:
    """Nouveau (CALCULS A § 3.3) : la dernière date compte un bon clos à la main ; un bon
    rouvert est « Confirmée » si tous ses prix le sont, sinon « Envoyée »."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 10, prix=10),
        commandes=[_bon("Soldée", solde_a_la_main_le=instant(2026, 4, 2, 15))],
    )
    assert derniere_date(d) == date(2026, 4, 2)
    bon = _bon("Soldée")
    assert statut_ouvert(bon) == "Envoyée"
    bon.lignes[0].prix_confirme = True
    assert statut_ouvert(bon) == "Confirmée"
    bon.lignes = []
    assert statut_ouvert(bon) == "Envoyée"
