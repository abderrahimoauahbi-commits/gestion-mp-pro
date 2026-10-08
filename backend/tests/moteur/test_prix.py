"""Les prix payés et les pistes d'économies (`calcul.prix`, `calcul.opportunites`) : le dernier
prix d'un jour est le dernier saisi, une matière désactivée n'est pas une piste, un rival hors
fenêtre est compté, les opportunités comparent des coûts rendus usine.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.importations import revient_par_reception
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    Donnees,
    DossierImport,
    Fournisseur,
    LigneImport,
    LignePrix,
)
from gestion_mp_pro.calcul.opportunites import comparer_les_prix
from gestion_mp_pro.calcul.prix import (
    LigneAchatRecu,
    achats_dates,
    couts_rendus,
    historique_prix,
    matrice_prix,
    prix_constates,
)
from gestion_mp_pro.calcul.stock import LigneStock

JOUR = date(2026, 9, 1)


def test_dernier_prix_meme_jour_est_le_dernier_saisi() -> None:
    """Hérité : test_defauts_e::test_dernier_prix_meme_jour_est_le_dernier_saisi."""
    serie = achats_dates(
        Donnees(), {"A": [(JOUR, 20.0, "prix facture"), (JOUR, 10.0, "prix facture")]}
    )
    assert serie["A"][-1] == (JOUR, 10.0)


def _deux_fils(
    actif: bool = True, rival: list[tuple[date, float]] | None = None
) -> tuple[Donnees, list[LigneStock]]:
    articles = [
        Article(
            "MOI",
            fournisseur="F1",
            composition="PP",
            type_fil="FRZ",
            titrage=2900,
            couleur="Rouge",
            prix_unite=30,
            actif=actif,
        ),
        Article(
            "LUI",
            fournisseur="F2",
            composition="PP",
            type_fil="FRZ",
            titrage=2900,
            couleur="Rouge",
            prix_unite=20,
        ),
    ]
    prix = [LignePrix(JOUR, "MOI", "F1", quantite=10, prix_achat=30)]
    for d, p in rival or [(JOUR, 20)]:
        prix.append(LignePrix(d, "LUI", "F2", quantite=10, prix_achat=p))
    donnees = Donnees(
        articles=articles,
        historique_prix=prix,
        fournisseurs=[Fournisseur("F1"), Fournisseur("F2")],
    )
    return donnees, [LigneStock("MOI", conso_mensuelle=100), LigneStock("LUI")]


def test_opportunites_ignore_article_inactif() -> None:
    """Hérité : test_defauts_e::test_opportunites_ignore_article_inactif."""
    donnees, lignes = _deux_fils()
    assert comparer_les_prix(donnees, lignes, meme_couleur=True)[0]
    donnees, lignes = _deux_fils(actif=False)
    assert not comparer_les_prix(donnees, lignes, meme_couleur=True)[0]


def test_rival_hors_fenetre_compte_des_qu_un_prix_est_plus_bas() -> None:
    """Hérité : test_defauts_e::test_rival_hors_fenetre_compte_des_qu_un_prix_est_plus_bas.

    Le dernier prix du rival est plus cher, un plus ancien moins cher : la piste est écartée,
    et comptée comme telle."""
    donnees, lignes = _deux_fils(rival=[(date(2026, 1, 1), 15), (date(2026, 2, 1), 40)])
    resultat, ecartees = comparer_les_prix(donnees, lignes, meme_couleur=True, fenetre_jours=30)
    assert not resultat and ecartees["hors_fenetre"] == 1


def test_M84_les_opportunites_comparent_des_couts_rendus() -> None:
    """Hérité : test_direction::test_M84_les_opportunites_comparent_des_couts_rendus.

    Le fil le moins cher sur facture peut coûter plus une fois dédouané."""
    donnees = Donnees(
        articles=[
            Article(reference="A", fournisseur="F1", prix_unite=2, composition="PP"),
            Article(reference="B", fournisseur="F2", prix_unite=2, composition="PP"),
        ],
        historique_prix=[
            LignePrix(JOUR, "A", "F1", prix_achat=2.0, quantite=10),
            LignePrix(JOUR, "B", "F2", prix_achat=1.9, quantite=10),
        ],
    )
    lignes = [
        LigneStock(reference="A", conso_mensuelle=100),
        LigneStock(reference="B", conso_mensuelle=100),
    ]
    # Au prix de la facture, B est moins cher que A.
    sur_facture, _ = comparer_les_prix(donnees, lignes)
    assert [o.reference for o in sur_facture] == ["A"]
    # Rendu usine, B porte des droits que A n'a pas : c'est A, le moins cher.
    couts = {"A": [(JOUR, 20.0, "prix facture")], "B": [(JOUR, 23.0, "coût rendu")]}
    rendus, _ = comparer_les_prix(donnees, lignes, couts=couts)
    assert [o.reference for o in rendus] == ["B"]
    assert rendus[0].base_prix == "coût rendu" and rendus[0].base_prix_minimum == "prix facture"
    assert rendus[0].economie_mad == pytest.approx((23 - 20) * 100 * 12)


def test_M84_le_cout_d_un_achat_est_le_cout_rendu_usine() -> None:
    """Hérité (partie calcul) : test_direction::test_M84_le_cout_d_un_achat_est_le_cout_rendu_usine.

    Dans un dossier : coût hors TVA du dossier ; hors dossier : prix × cours figé du bon (10),
    pas le cours du jour (12)."""
    donnees = Donnees(
        dossiers_import=[
            DossierImport(
                numero="D",
                lignes=[
                    LigneImport(
                        1, "ROUGE", 1000, 2000, devise="USD", cours=10.5, ligne_reception_id=1
                    )
                ],
                charges=[
                    ChargeImport(poste="DD", montant=2500),
                    ChargeImport(poste="TVA", montant=5000),
                ],
            )
        ]
    )
    donnees.parametres.cours = {"USD": 12.0}
    lignes = [
        LigneAchatRecu(1, JOUR, "ROUGE", 2.0, "USD", cours_commande=10.0, devise_commande="USD"),
        LigneAchatRecu(2, JOUR, "BLEU", 2.0, "USD", cours_commande=10.0, devise_commande="USD"),
        LigneAchatRecu(3, JOUR, "VERT", 2.0, "USD", cours_commande=10.0, devise_commande="EUR"),
    ]
    couts = couts_rendus(donnees, lignes, revient_par_reception(donnees))
    ((jour, rouge, base_rouge),) = couts["ROUGE"]
    ((_, bleu, base_bleu),) = couts["BLEU"]
    assert base_rouge == "coût rendu" and jour == JOUR
    # 1 000 kg × 2 USD × 10,5 (cours de la banque) + 2 500 MAD de droits ; la TVA n'est pas un coût.
    assert rouge == pytest.approx((1000 * 2 * 10.5 + 2500) / 1000)
    assert base_bleu == "prix facture"
    assert bleu == pytest.approx(2 * 10.0)  # le cours figé du bon, pas les 12 du jour
    # Un bon dans une autre devise que la facture : le cours du jour.
    assert couts["VERT"] == [(JOUR, pytest.approx(24.0), "prix facture")]


def test_la_matrice_ne_melange_pas_les_devises() -> None:
    """Hérité (partie calcul) : test_defauts_e::test_matrice_ne_melange_pas_les_devises.

    Une référence payée en dollars et en euros fait deux lignes ; le prix d'un mois est la
    moyenne pondérée des quantités, dans la devise des factures."""
    a = Article(reference="E FIL USD", fournisseur="E", composition="PP", nature="Poil")
    donnees = Donnees(
        articles=[a],
        historique_prix=[
            LignePrix(date(2026, 9, 3), "E FIL USD", quantite=100, prix_achat=2, devise="USD"),
            LignePrix(date(2026, 9, 20), "E FIL USD", quantite=300, prix_achat=2.4, devise="USD"),
            LignePrix(date(2026, 10, 2), "E FIL USD", quantite=100, prix_achat=3, devise="EUR"),
        ],
    )
    mois, lignes = matrice_prix(donnees)
    assert mois == ["2026-09", "2026-10"]
    par_devise = {x.devise: x.prix for x in lignes}
    assert par_devise["USD"] == [pytest.approx((200 + 720) / 400), None]
    assert par_devise["EUR"] == [None, 3]
    assert lignes[0].composition == "PP" and lignes[0].fournisseur == "E"


def test_l_historique_compare_au_prix_precedent_du_meme_fournisseur() -> None:
    """Nouveau (CALCULS B § 2) : l'évolution se lit face au prix précédent du même fournisseur
    dans la même devise ; le prix constaté est le dernier payé, en MAD, sinon le catalogue."""
    donnees = Donnees(
        articles=[
            Article(reference="P", prix_unite=3, devise="USD"),
            Article(reference="Q", prix_unite=7),
        ],
        historique_prix=[
            LignePrix(date(2026, 9, 1), "P", "F", "BC-1", 100, 2.0, "USD"),
            LignePrix(date(2026, 9, 5), "P", "G", "BC-2", 100, 1.0, "USD"),
            LignePrix(date(2026, 9, 9), "P", "F", "BC-3", 50, 2.5, "USD"),
        ],
    )
    recent, milieu, ancien = historique_prix(donnees)
    assert (recent.numero_bc, recent.prix_precedent) == ("BC-3", 2.0)
    assert recent.evolution == pytest.approx(0.25)
    assert recent.prix_mad == pytest.approx(2.5 * 9.5) and recent.montant_mad == pytest.approx(
        50 * 2.5 * 9.5
    )
    assert milieu.prix_precedent is None and ancien.evolution is None
    constates = prix_constates(donnees)
    assert constates["P"] == (pytest.approx(2.5 * 9.5), "payé", date(2026, 9, 9))
    assert constates["Q"] == (7, "catalogue", None)
