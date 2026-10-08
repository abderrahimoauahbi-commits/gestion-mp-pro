"""Le plan de production (`calcul.plan`) : la croissance comptée depuis l'ancre, un mois passé
jugé sur le plan de son époque au prorata des jours, une croissance bornée.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.modele import Donnees, Parametres, PlanQualite, VersionPlan
from gestion_mp_pro.calcul.plan import m2_du_mois, m2_passe, plan_en_vigueur, plan_mensuel
from moteur.fabrique import UN, instant, usine


def test_un_plan_revise_en_cours_de_mois_compte_pour_ses_jours() -> None:
    """Hérité : test_audit2_achat::test_un_plan_revise_en_cours_de_mois_compte_pour_ses_jours."""
    d = usine(
        100,
        versions_plan={
            "Q": [VersionPlan(None, 1000, UN), VersionPlan(instant(2026, 9, 21), 2000, UN)]
        },
    )
    # Septembre : 20 jours à 1 000, 10 jours à 2 000.
    assert m2_passe(d, d.plan[0], date(2026, 9, 30)) == pytest.approx(
        1000 * 20 / 30 + 2000 * 10 / 30
    )
    assert m2_passe(d, d.plan[0], date(2026, 8, 31)) == pytest.approx(1000)
    # Une qualité arrêtée le 21 : ses 20 premiers jours restent au plan.
    d.versions_plan = {
        "Q": [
            VersionPlan(None, 1000, UN),
            VersionPlan(instant(2026, 9, 21), 1000, UN, actif=False),
        ]
    }
    assert m2_passe(d, d.plan[0], date(2026, 9, 30)) == pytest.approx(1000 * 20 / 30)
    # Le mois vu au 10 septembre : les jours d'avant seulement, au plan d'alors.
    assert m2_passe(d, d.plan[0], date(2026, 9, 30), jusqu_a=date(2026, 9, 10)) == pytest.approx(
        1000
    )


def test_une_croissance_de_moins_100_ne_fait_plus_tomber_un_mois_passe() -> None:
    """Hérité :
    test_audit2_pilotage::test_une_croissance_de_moins_100_ne_fait_plus_tomber_un_mois_passe.

    Une valeur écrite avant la borne (−100 %) : le mois d'avant l'ancre ne divise plus par zéro."""
    donnees = Donnees(parametres=Parametres(croissance_annuelle=-1.0))
    m2 = m2_du_mois(donnees, 1000, [], date(2025, 9, 30), date(2026, 3, 1))
    assert m2 > 0


def test_la_croissance_d_un_mois_ne_depend_pas_du_mois_d_ou_on_le_regarde() -> None:
    """Hérité :
    test_plan_besoins::test_la_croissance_d_un_mois_ne_depend_pas_du_mois_d_ou_on_le_regarde.

    La branche « classeur » de l'essai d'origine n'est pas portée (P17 : seule la méthode
    corrigée est calculée)."""
    p = Parametres(croissance_annuelle=0.12)
    d = usine(parametres=p, plan=[PlanQualite("Q", 1000, UN, depuis=date(2026, 1, 15))])
    vu_en_mars = plan_mensuel(d, date(2026, 3, 1))["Q"][6]  # septembre 2026
    vu_en_septembre = plan_mensuel(d, date(2026, 9, 1))["Q"][0]
    assert vu_en_mars == vu_en_septembre == round(1000 * 1.12 ** (8 / 12))


def test_le_plan_en_vigueur_est_le_dernier_change_avant_la_fin_du_mois() -> None:
    """Nouveau (CALCULS A § 3.4) : sans histoire, le plan d'aujourd'hui (en service) ; avec,
    le dernier changement avant la fin du mois, sinon le plan d'avant le premier."""
    d = usine(plan=[PlanQualite("Q", 1500, UN, actif=False)])
    sans = plan_en_vigueur(d, d.plan[0], date(2026, 9, 30))
    assert (sans.quand, sans.base_mensuelle, sans.actif) == (None, 1500, True)
    d.versions_plan = {
        "Q": [
            VersionPlan(None, 1000, UN),
            VersionPlan(instant(2026, 9, 30, 23, 59), 1200, UN),
            VersionPlan(instant(2026, 10, 1), 1500, UN, actif=False),
        ]
    }
    assert plan_en_vigueur(d, d.plan[0], date(2026, 8, 31)).base_mensuelle == 1000
    assert plan_en_vigueur(d, d.plan[0], date(2026, 9, 30)).base_mensuelle == 1200
    assert plan_en_vigueur(d, d.plan[0], date(2026, 10, 31)).actif is False
    # Une qualité arrêtée ne compte plus pour les mois à venir ; une saison double août.
    assert plan_mensuel(d, date(2026, 10, 8))["Q"] == [0.0] * 12
    saison = [1.0] * 7 + [2.0] + [1.0] * 4
    assert m2_du_mois(d, 1000, saison, date(2026, 8, 31), date(2026, 8, 1)) == 2000
    # ARRONDI d'Excel : 1 002,5 m² → 1 003 (l'arrondi au pair de Python en ferait 1 002).
    assert m2_du_mois(d, 1002.5, UN, date(2026, 8, 31), date(2026, 8, 1)) == 1003
