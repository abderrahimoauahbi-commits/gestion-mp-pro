"""Les besoins (`calcul.besoins`) : la demande sur une fenêtre de jours, le mois en cours sur
sa vraie longueur, au-delà de douze mois ; les recettes de l'époque, qui remplace qui.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.besoins import (
    besoin_sur_fenetre,
    besoins_mensuels,
    besoins_passes,
    fils_remplaces,
    kg_m2_version,
    sortis_des_recettes,
    versions_recette_pendant,
)
from gestion_mp_pro.calcul.modele import Donnees, LigneRecette, Parametres, VersionRecette
from moteur.fabrique import instant, usine

BESOINS = [100.0, 250.0, 0.0, 80.0, 120.0, 90.0, 60.0, 300.0, 10.0, 0.0, 45.0, 70.0]


def test_d14b_une_fenetre_au_dela_de_douze_mois_n_est_pas_diluee() -> None:
    """Hérité : test_defauts_d::test_d14b_une_fenetre_au_dela_de_douze_mois_n_est_pas_diluee."""
    besoins = [100.0] * 12
    total = besoin_sur_fenetre(besoins, 0, 450, 30, jours_du_mois=30, prolonger=True)
    assert total == pytest.approx(1500)  # avant : 1 200, rien au-delà du douzième mois


def test_la_fenetre_proratise_le_mois_en_cours_sur_sa_vraie_longueur() -> None:
    """Nouveau (CALCULS A § 3.7) : mois de 30 jours ; le mois en cours, s'il reste 10 jours
    sur 31, ne pèse que 10/31 de son besoin ; une fenêtre se coupe au prorata des jours."""
    assert besoin_sur_fenetre(BESOINS, 0, 45) == pytest.approx(100 + 250 * 15 / 30)
    premier = 100 * 10 / 31
    assert besoin_sur_fenetre(BESOINS, 0, 45, 10, jours_du_mois=31) == pytest.approx(
        premier + 250 + 0 * 5 / 30
    )
    assert besoin_sur_fenetre(BESOINS, 5, 45, 10, jours_du_mois=31) == pytest.approx(
        premier / 2 + 250
    )
    # Sans longueur dite, le mois en cours compte 30 jours ; un reste négatif ne compte rien.
    assert besoin_sur_fenetre(BESOINS, 0, 15, 15) == pytest.approx(100 * 15 / 30)
    assert besoin_sur_fenetre(BESOINS, 0, 30, -3) == pytest.approx(250)
    assert besoin_sur_fenetre(BESOINS, 30, 30) == 0


def test_la_fenetre_prolongee_voit_l_annee_suivante_comme_celle_ci() -> None:
    """Nouveau (D-14, CALCULS A § 3.7) : au-delà des douze mois, la demande recommence au
    premier mois ; sans `prolonger`, rien au-delà."""
    total = sum(BESOINS)
    debut = 100 * 10 / 31
    sur_un_an = debut + sum(BESOINS[1:])  # 10 jours + 11 mois = 340 jours
    assert besoin_sur_fenetre(BESOINS, 0, 400, 10, jours_du_mois=31) == pytest.approx(sur_un_an)
    prolonge = besoin_sur_fenetre(BESOINS, 0, 400, 10, jours_du_mois=31, prolonger=True)
    assert prolonge == pytest.approx(sur_un_an + 100 + 250)  # 340 → 400 : janvier et février
    assert besoin_sur_fenetre(BESOINS, 360, 720, prolonger=True) == pytest.approx(total)
    assert besoin_sur_fenetre([], 0, 400, prolonger=True) == 0


def _recette_changee() -> Donnees:
    versions = {
        "Q": [
            VersionRecette(instant(2026, 6, 1), [("FIL A", 100)], {"Poil": 1.0}),
            VersionRecette(instant(2026, 9, 20, 10), [("FIL B", 100)], {"Poil": 1.0}),
        ]
    }
    return usine(recettes=[LigneRecette("Q", "FIL B", 100)], versions_recette=versions)


def test_les_besoins_passes_suivent_la_recette_de_l_epoque() -> None:
    """Nouveau (CALCULS A § 3.6) : le 20 septembre, FIL B remplace FIL A : août demandait
    1 000 kg de FIL A, septembre 1 000 kg de FIL B (la dernière version du mois) ; un mois où
    la recette d'un fil a changé ne le juge pas."""
    d = _recette_changee()
    septembre = (instant(2026, 9, 1), instant(2026, 9, 30, 23, 59))
    v1, v2 = d.versions_recette["Q"]
    assert versions_recette_pendant(d, "Q", *septembre) == [v1, v2]
    assert versions_recette_pendant(d, "Q", instant(2026, 8, 1), instant(2026, 8, 31)) == [v1]
    assert versions_recette_pendant(d, "AUTRE", *septembre) == [None]
    assert kg_m2_version(d, "Q", v1) == {"FIL A": 1.0}
    assert kg_m2_version(d, "Q", None) == {"FIL B": 1.0}
    prevus, stables = besoins_passes(d, [date(2026, 8, 31), date(2026, 9, 30)])
    assert prevus == {"FIL A": [1000, 0], "FIL B": [0, 1000]}
    assert stables == {"FIL A": [True, False], "FIL B": [True, False]}
    assert fils_remplaces(d, instant(2026, 7, 1), instant(2026, 10, 8)) == {
        ("Q", "FIL B"): ["FIL A"]
    }
    assert sortis_des_recettes(d, instant(2026, 7, 1), instant(2026, 10, 8)) == {"FIL A"}
    assert fils_remplaces(d, instant(2026, 9, 21), instant(2026, 10, 8)) == {}


def test_une_version_sans_poids_prend_ceux_de_la_suivante() -> None:
    """Nouveau (CALCULS A § 3.6) : les versions d'avant ne gardaient pas les poids au m² : la
    suivante qui les a, sinon ceux d'aujourd'hui ; les besoins comptent la perte."""
    d = usine(parametres=Parametres(taux_perte=0.05))
    d.versions_recette = {
        "Q": [
            VersionRecette(instant(2026, 1, 1), [("FIL A", 50), ("FIL B", 50)], None),
            VersionRecette(instant(2026, 3, 1), [("FIL A", 100)], {"Poil": 3.0}),
            VersionRecette(instant(2026, 4, 1), [("FIL A", 40)], None),
        ]
    }
    ancienne, _, derniere = d.versions_recette["Q"]
    assert kg_m2_version(d, "Q", ancienne) == {"FIL A": 1.5, "FIL B": 1.5}
    assert kg_m2_version(d, "Q", derniere) == {"FIL A": 0.4}  # les poids d'aujourd'hui (1 kg)
    cache: dict[tuple[str, int], dict[str, float]] = {}
    assert kg_m2_version(d, "Q", ancienne, cache) is kg_m2_version(d, "Q", ancienne, cache)
    assert besoins_mensuels(d, date(2026, 10, 8))["FIL A"] == pytest.approx([1050.0] * 12)
