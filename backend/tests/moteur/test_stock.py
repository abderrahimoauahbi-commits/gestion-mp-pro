"""L'état du stock (`calcul.stock.etat_stock`) : ce qui ne se consomme plus ne se rachète pas,
le passé se juge sur le plan et les recettes de son époque, un fil remplaçant hérite du taux
de réalisation de l'ancien, une commande déjà passée pour la période ne se commande pas deux
fois, couverture et cible se comparent.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.constantes import STATUTS
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    LigneCommande,
    LigneRecette,
    Mouvement,
    Parametres,
    PlanQualite,
    VersionPlan,
    VersionRecette,
)
from moteur.fabrique import UN, instant, ligne_de, sortie, usine


def test_une_matiere_non_consommee_ne_se_rachete_pas_pour_son_stock_minimum() -> None:
    """Hérité :
    test_audit2_achat::test_une_matiere_non_consommee_ne_se_rachete_pas_pour_son_stock_minimum.
    """
    d = usine(
        100,
        articles=[
            Article(reference="FIL A", role_bom="Poil", fournisseur="F", prix_unite=1),
            Article(
                reference="FIL B", role_bom="Poil", fournisseur="F", prix_unite=1, stock_min=12_900
            ),
        ],
    )
    b = ligne_de(d, "FIL B")
    assert b.conso_mensuelle == 0 and b.quantite_a_commander == 0
    assert b.sans_achat.startswith("non consommée")


def test_la_fenetre_se_compte_en_mois_au_demi_superieur() -> None:
    """Hérité : test_audit2_achat::test_la_fenetre_se_compte_en_mois_au_demi_superieur.

    75 jours font trois mois (au pair, Python en faisait deux)."""
    sorties = [
        sortie(date(2026, 7, 2), "FIL A", 2000),
        sortie(date(2026, 8, 2), "FIL A", 1000),
        sortie(date(2026, 9, 2), "FIL A", 1000),
    ]
    d = usine(
        100,
        mouvements=usine(100).mouvements + sorties,
        parametres=Parametres(taux_perte=0.0, fenetre_realisation_jours=75),
    )
    assert ligne_de(d, "FIL A").coefficient_realisation == pytest.approx(4000 / 3000)


def test_le_fil_qui_en_remplace_un_autre_prend_son_taux_de_realisation() -> None:
    """Hérité :
    test_audit2_achat::test_le_fil_qui_en_remplace_un_autre_prend_son_taux_de_realisation.
    """
    versions = {
        "Q": [
            VersionRecette(instant(2026, 6, 1), [("FIL A", 100)], {"Poil": 1.0}),
            VersionRecette(instant(2026, 9, 20, 10), [("FIL B", 100)], {"Poil": 1.0}),
        ]
    }
    # Du stock d'avance : un fil en rupture ne verrait pas sa prévision baisser.
    sorties = [
        Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", 10_000),
        sortie(date(2026, 7, 3), "FIL A", 800),
        sortie(date(2026, 8, 3), "FIL A", 800),
    ]
    d = usine(
        100,
        recettes=[LigneRecette("Q", "FIL B", 100)],
        versions_recette=versions,
        mouvements=usine(100).mouvements + sorties,
    )
    assert ligne_de(d, "FIL A").coefficient_realisation == pytest.approx(0.8)
    b = ligne_de(d, "FIL B")
    assert b.coefficient_realisation == pytest.approx(0.8) and b.realisation_heritee == ["FIL A"]
    assert b.besoins[1] == pytest.approx(800)


def test_un_fil_abandonne_que_l_atelier_finit_n_est_pas_une_demande_durable() -> None:
    """Hérité :
    test_audit2_achat::test_un_fil_abandonne_que_l_atelier_finit_n_est_pas_une_demande_durable.

    FIL A est sorti de la recette en mai ; l'atelier finit son stock en juillet-septembre :
    ces sorties ne font pas une prévision « hors recette » à racheter."""
    versions = {
        "Q": [
            VersionRecette(instant(2026, 1, 5), [("FIL A", 100)], {"Poil": 1.0}),
            VersionRecette(instant(2026, 5, 15), [("FIL B", 100)], {"Poil": 1.0}),
        ]
    }
    sorties = [sortie(date(2026, m, 3), "FIL A", 30) for m in (7, 8, 9)]
    d = usine(
        100,
        recettes=[LigneRecette("Q", "FIL B", 100)],
        versions_recette=versions,
        mouvements=usine(100).mouvements + sorties,
    )
    a = ligne_de(d, "FIL A")
    assert a.besoin_annuel == 0 and a.quantite_a_commander == 0
    # Un fil jamais en recette, consommé, reste prévu sur ce qui sort.
    d.versions_recette = {}
    assert ligne_de(d, "FIL A").besoin_annuel == pytest.approx(30 * 12)


def test_un_plan_releve_n_est_pas_defait_par_le_reel_d_avant() -> None:
    """Hérité : test_plan_besoins::test_un_plan_releve_n_est_pas_defait_par_le_reel_d_avant.

    Le plan passe de 1 000 à 1 500 m² le 1er octobre ; l'atelier a tissé 1 000 m² par mois,
    comme prévu alors. Le besoin retenu suit le nouveau plan (× 1,5)."""
    sorties = [sortie(date(2026, m, 2), "FIL A", 1000) for m in (7, 8, 9)]
    d = usine(
        plan=[PlanQualite("Q", base_mensuelle=1500, saisonnalite=UN)],
        mouvements=usine().mouvements + sorties,
        versions_plan={
            "Q": [VersionPlan(None, 1000, UN), VersionPlan(instant(2026, 10, 1, 9), 1500, UN)]
        },
    )
    ligne = ligne_de(d, "FIL A")
    assert ligne.coefficient_realisation == pytest.approx(1.0)
    assert ligne.besoins[1] == pytest.approx(1500)
    # Sans l'histoire du plan, le même réel « corrigeait » le relèvement : c'était le défaut.
    d.versions_plan = {}
    assert ligne_de(d, "FIL A").coefficient_realisation == pytest.approx(1000 / 1500)


def test_un_fil_remplace_dans_la_recette_n_est_pas_juge_sur_un_coefficient_qui_ne_le_concerne_pas() -> (  # noqa: E501
    None
):
    """Hérité :
    test_plan_besoins::test_un_fil_remplace_dans_la_recette_n_est_pas_juge_sur_un_coefficient_qui_ne_le_concerne_pas.
    """
    versions = {
        "Q": [
            VersionRecette(instant(2026, 6, 1), [("FIL A", 100)], {"Poil": 1.0}),
            VersionRecette(instant(2026, 9, 20, 10), [("FIL B", 100)], {"Poil": 1.0}),
        ]
    }
    sorties = [
        sortie(date(2026, 7, 3), "FIL A", 1000),
        sortie(date(2026, 8, 3), "FIL A", 1000),
        sortie(date(2026, 9, 3), "FIL A", 600),
        sortie(date(2026, 9, 25), "FIL B", 300),
    ]
    d = usine(
        recettes=[LigneRecette("Q", "FIL B", 100)],
        versions_recette=versions,
        mouvements=usine().mouvements + sorties,
    )
    nouveau, ancien = ligne_de(d, "FIL B"), ligne_de(d, "FIL A")
    assert nouveau.coefficient_realisation == pytest.approx(1.0)  # celui de FIL A
    assert nouveau.realisation_heritee == ["FIL A"]
    assert nouveau.besoins[1] == pytest.approx(1000)  # le plan, pas la moitié
    assert ancien.coefficient_realisation == pytest.approx(1.0)  # juillet et août, au plan
    assert ancien.besoin_annuel == 0  # remplacé : plus rien à prévoir


def test_une_commande_arrivant_apres_le_delai_mais_dans_la_couverture_est_retranchee() -> None:
    """Hérité :
    test_plan_besoins::test_une_commande_arrivant_apres_le_delai_mais_dans_la_couverture_est_retranchee.
    """
    sorties = [sortie(date(2026, m, 2), "FIL A", 1000) for m in (7, 8, 9)]
    base = usine(mouvements=[Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", 4000), *sorties])

    def commande(livraison: date) -> Commande:
        return Commande(
            "BC-1",
            fournisseur="F",
            date_livraison_prevue=livraison,
            statut="Envoyée",
            lignes=[LigneCommande("BC-1", "FIL A", quantite_commandee=500)],
        )

    sans = ligne_de(base, "FIL A")
    assert sans.quantite_theorique > 500
    base.commandes = [commande(date(2026, 11, 22))]  # délai le 7/11, couverture jusqu'au 7/12
    dans = ligne_de(base, "FIL A")
    assert dans.bc_hors_horizon == dans.bc_dans_couverture == 500
    assert dans.stock_projete == pytest.approx(sans.stock_projete)  # trop tard pour le délai
    assert dans.quantite_theorique == pytest.approx(sans.quantite_theorique - 500)
    base.commandes = [commande(date(2027, 1, 15))]  # après la période : la suivante la verra
    apres = ligne_de(base, "FIL A")
    assert apres.bc_dans_couverture == 0
    assert apres.quantite_theorique == pytest.approx(sans.quantite_theorique)


def test_la_couverture_se_compare_au_seuil_d_alerte_en_jours() -> None:
    """Hérité : test_plan_besoins::test_la_couverture_se_compare_au_seuil_d_alerte_en_jours."""
    for stock in (1500, 2600, 4000, 9000):
        d = usine(mouvements=[Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", stock)])
        ligne = ligne_de(d, "FIL A")
        assert ligne.couverture_cible_jours == pytest.approx(
            ligne.stock_min_recalcule / (ligne.conso_mensuelle / 30)
        )
        assert (ligne.couverture_jours >= ligne.couverture_cible_jours) == (
            ligne.stock_projete >= ligne.stock_min_recalcule
        )
        if ligne.statut == STATUTS["OK"]:
            assert ligne.couverture_jours > ligne.couverture_cible_jours
