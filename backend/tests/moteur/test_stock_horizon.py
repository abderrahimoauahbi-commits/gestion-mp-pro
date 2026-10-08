"""L'état du stock dans le temps (`calcul.stock`) : le mois en cours jusqu'à sa vraie fin, un
délai fractionnaire, la prévision sans fenêtre, le fil qui attend sur les métiers, les classes
ABC et XYZ, la dernière sortie.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    FilMonte,
    Fournisseur,
    LigneCommande,
    Metier,
    Mouvement,
    Parametres,
    PlanQualite,
)
from gestion_mp_pro.calcul.outils import debut_de_mois
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from gestion_mp_pro.calcul.stock.classes import classer_abc, jours_securite
from moteur.fabrique import ecriture, journal, ligne_de, usine


def _fil_a(jour: date = date(2026, 10, 8), **autres: Any) -> LigneStock:
    """L'usine de `test_defauts_d` : FIL A seul, 100 000 kg depuis juin."""
    return ligne_de(usine(references=("FIL A",), **autres), "FIL A", jour)


def test_d14a_le_mois_en_cours_se_compte_jusqu_a_sa_vraie_fin() -> None:
    """Hérité : test_defauts_d::test_d14a_le_mois_en_cours_se_compte_jusqu_a_sa_vraie_fin.

    Le 28 février, il ne reste rien de février : un délai de 2 jours prend mars."""
    saisons = [1.0, 1.0, 2.0] + [1.0] * 9
    ligne = _fil_a(
        fournisseurs=[Fournisseur(nom="F", delai_jours=2, couverture_commande_jours=30)],
        plan=[PlanQualite("Q", base_mensuelle=1000, saisonnalite=saisons)],
        mouvements=[Mouvement(date(2026, 1, 1), "STOCK_INITIAL", "FIL A", 100_000)],
        jour=date(2027, 2, 28),
    )
    assert ligne.demande_delai == pytest.approx(2000 * 2 / 30)  # avant : 2 jours de février


def test_d14c_un_delai_fractionnaire_livre_au_jour_suivant() -> None:
    """Hérité : test_defauts_d::test_d14c_un_delai_fractionnaire_livre_au_jour_suivant."""
    jour = date(2026, 10, 8)
    ligne = _fil_a(
        fournisseurs=[Fournisseur(nom="F", delai_jours=4.5, couverture_commande_jours=30)],
        commandes=[
            Commande(
                "BC-1",
                fournisseur="F",
                statut="Envoyée",
                date_livraison_prevue=jour + timedelta(days=5),
                lignes=[LigneCommande("BC-1", "FIL A", quantite_commandee=500)],
            )
        ],
    )
    assert ligne.bc_en_cours == pytest.approx(500) and ligne.bc_hors_horizon == 0


def test_d14d_sans_fenetre_le_plan_fait_la_prevision() -> None:
    """Hérité : test_defauts_d::test_d14d_sans_fenetre_le_plan_fait_la_prevision."""
    sorties = [Mouvement(date(2026, mois, 2), "SORTIE_PROD", "FIL A", 3000) for mois in (7, 8, 9)]
    ligne = _fil_a(
        parametres=Parametres(taux_perte=0.0, fenetre_realisation_jours=0),
        mouvements=[Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", 100_000), *sorties],
    )
    assert ligne.conso_mensuelle == pytest.approx(1000)  # avant : 2 250


def test_d14f_le_coefficient_baisse_quand_le_fil_attend_sur_les_metiers() -> None:
    """Hérité : test_defauts_d::test_d14f_le_coefficient_baisse_quand_le_fil_attend_sur_les_metiers.

    Les magasins sont vides, mais 200 kg sont montés : l'atelier avait de quoi tisser ; sa
    faible consommation dit la demande, pas une rupture."""
    sorties = [Mouvement(date(2026, mois, 2), "SORTIE_PROD", "FIL A", 600) for mois in (7, 8, 9)]
    ligne = _fil_a(
        articles=[
            Article(
                reference="FIL A", role_bom="Poil", fournisseur="F", prix_unite=1, poids_bobine=2.0
            )
        ],
        mouvements=[Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", 1800), *sorties],
        metiers=[Metier(code="M1", densite=10, fils=[FilMonte("FIL A", metres=10)])],
    )
    assert ligne.stock_net == pytest.approx(0) and ligne.stock_machine == pytest.approx(200)
    assert ligne.coefficient_realisation == pytest.approx(0.6)


def test_d16_une_demande_parfaitement_reguliere_est_x() -> None:
    """Hérité : test_defauts_d::test_d16_une_demande_parfaitement_reguliere_est_x."""
    jour = date(2026, 10, 8)
    sorties = [
        Mouvement(debut_de_mois(jour, -i) + timedelta(days=9), "SORTIE_PROD", "FIL A", 100)
        for i in range(1, 13)
    ]
    ligne = _fil_a(
        mouvements=[Mouvement(date(2025, 1, 1), "STOCK_INITIAL", "FIL A", 100_000), *sorties]
    )
    assert ligne.cv_demande == 0 and ligne.classe_xyz == "X"


def _sorties_mensuelles(jour_ref: date, n0: int = 1) -> list[Mouvement]:
    """Un stock d'ouverture, puis 100 kg sortis le 10 de chacun des douze mois clos."""
    mouvements = [ecriture(n0, debut_de_mois(jour_ref, -13), "STOCK_INITIAL", 10_000, prix=10)]
    for i in range(1, 13):
        mouvements.append(
            ecriture(
                n0 + i,
                debut_de_mois(jour_ref, -i) + timedelta(days=9),
                "SORTIE_PROD",
                100,
                of=f"OF-{i}",
            )
        )
    return mouvements


def test_la_classe_xyz_compte_les_sorties_nettes_des_mois_clos() -> None:
    """Hérité : test_valorisation::test_la_classe_xyz_compte_les_sorties_nettes_des_mois_clos."""
    jour = date(2026, 6, 5)  # le mois en cours n'a encore rien sorti
    juin = _sorties_mensuelles(jour)
    mars = debut_de_mois(jour, -3) + timedelta(days=12)
    juin += [
        ecriture(50, mars, "SORTIE_PROD", 100, of="OF-X"),
        ecriture(51, mars, "SORTIE_PROD", -100, annule=50, of="OF-X"),
    ]
    ligne = etat_stock(journal(*juin), jour)[0]
    # Une demande parfaitement régulière est la plus prévisible : X (D-16).
    assert ligne.cv_demande == pytest.approx(0) and ligne.classe_xyz == "X"
    # Une vraie irrégularité se voit toujours.
    juin.append(ecriture(52, mars, "SORTIE_PROD", 300, of="OF-Y"))
    ligne = etat_stock(journal(*juin), jour)[0]
    assert ligne.cv_demande > 0.5 and ligne.classe_xyz == "Z"


def test_une_sortie_annulee_n_est_pas_la_derniere_sortie() -> None:
    """Hérité : test_valorisation::test_une_sortie_annulee_n_est_pas_la_derniere_sortie."""
    j1, j3 = date(2026, 3, 2), date(2026, 3, 16)
    d = journal(
        ecriture(1, j1, "STOCK_INITIAL", 100, prix=10),
        ecriture(2, j1, "SORTIE_PROD", 10, of="OF-1"),
        ecriture(3, j3, "SORTIE_PROD", 10, of="OF-2"),
        ecriture(4, j3, "SORTIE_PROD", -10, annule=3, of="OF-2"),
    )
    ligne = etat_stock(d, date(2026, 4, 1))[0]
    assert ligne.date_derniere_sortie == j1


def test_la_classe_abc_suit_la_valeur_cumulee_et_les_ex_aequo_partagent_leur_rang() -> None:
    """Nouveau (CALCULS A § 3.10) : % cumulé = Σ(valeurs ≥ la mienne) / total, seuils 80 et
    95 % ; deux valeurs égales partagent cumul et rang ; les jours de sécurité suivent la classe."""
    lignes = [
        LigneStock(reference=r, valeur_conso_annuelle_mad=v)
        for r, v in (("A", 700.0), ("B1", 100.0), ("B2", 100.0), ("C", 100.0))
    ]
    p = Parametres(securite_a=10, securite_b=20, securite_c=40)
    classer_abc(lignes, p)
    par = {x.reference: x for x in lignes}
    assert [x.classe_abc for x in lignes] == ["A", "C", "C", "C"]
    assert par["A"].pourcentage_cumule == pytest.approx(0.7) and par["A"].rang == 1
    assert par["B1"].pourcentage_cumule == pytest.approx(1.0)
    assert par["B1"].rang == par["B2"].rang == par["C"].rang == 2
    lignes[1].valeur_conso_annuelle_mad = 200.0
    lignes[3].valeur_conso_annuelle_mad = 0.0
    classer_abc(lignes, p)
    assert [x.classe_abc for x in lignes] == ["A", "B", "C", "C"]
    assert [jours_securite(x.classe_abc, p) for x in lignes] == [10, 20, 40, 40]
    vides = [LigneStock(reference="Z")]
    classer_abc(vides, p)
    assert vides[0].classe_abc == "C" and vides[0].pourcentage_cumule == 0
