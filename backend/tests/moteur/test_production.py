"""Ordres de fabrication et réalisé du plan (`calcul.production`) : le prévu d'un ordre figé à
sa date, un ordre annulé qui ne compte rien, le réalisé jugé sur le plan de son époque.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.chargement import arret_sans_histoire
from gestion_mp_pro.calcul.modele import (
    Mouvement,
    OrdreFabrication,
    PlanQualite,
    Qualite,
    VersionPlan,
    VersionRecette,
)
from gestion_mp_pro.calcul.plan import m2_passe, plan_mensuel
from gestion_mp_pro.calcul.production import (
    ConsommationOrdre,
    ConsommationReference,
    ajuster_ordre,
    consommation_par_of,
    realise_par_qualite,
)
from moteur.fabrique import JOUR, UN, instant, sortie, usine


def test_le_realise_a_une_date_passee_prend_le_plan_et_les_ordres_de_cette_date() -> None:
    """Hérité :
    test_audit2_achat::test_le_realise_a_une_date_passee_prend_le_plan_et_les_ordres_de_cette_date.
    """
    d = usine(
        100,
        plan=[PlanQualite("Q", base_mensuelle=2000, saisonnalite=UN)],
        versions_plan={
            "Q": [VersionPlan(None, 1000, UN), VersionPlan(instant(2026, 9, 21), 2000, UN)]
        },
        ordres=[
            OrdreFabrication("OF-1", date(2026, 9, 5), [("Q", 300)]),
            OrdreFabrication("OF-2", date(2026, 9, 25), [("Q", 500)]),
        ],
    )
    r = realise_par_qualite(d, date(2026, 9, 15), aujourd_hui=JOUR)
    q = next(x for x in r.lignes if x.qualite == "Q")
    assert q.plan[-1] == pytest.approx(1000)  # le plan du 15 septembre, pas celui d'aujourd'hui
    assert q.realise[-1] == 300  # l'ordre du 25 n'était pas encore tissé


def test_le_realise_garde_le_plan_d_une_qualite_arretee() -> None:
    """Hérité : test_plan_besoins::test_le_realise_garde_le_plan_d_une_qualite_arretee.

    Arrêter une qualité le 5 octobre retire son plan des mois à venir, pas de septembre."""
    d = usine(
        plan=[PlanQualite("Q", base_mensuelle=1000, saisonnalite=UN, actif=False)],
        versions_plan={
            "Q": [
                VersionPlan(None, 1000, UN),
                VersionPlan(instant(2026, 10, 5), 1000, UN, actif=False),
            ]
        },
    )
    r = realise_par_qualite(d, JOUR)
    plan = next(x for x in r.lignes if x.qualite == "Q").plan
    assert plan[-2] == 1000  # septembre, clos : le plan d'alors
    assert plan[-1] == 0  # octobre : arrêtée
    assert plan_mensuel(d, JOUR)["Q"] == [0.0] * 12
    # Sans histoire (arrêtée avant que l'ERP ne trace l'arrêt), le passé garde sa base.
    d.versions_plan = {}
    r = realise_par_qualite(d, JOUR)
    plan = next(x for x in r.lignes if x.qualite == "Q").plan
    # Les mois d'avant la mise en service (juin, le premier mouvement) n'avaient rien à tisser.
    assert r.debut_service == "2026-06-01"
    assert plan[:7] == [0] * 7 and plan[7:11] == [1000] * 4 and plan[-1] == 0


def test_une_qualite_arretee_sans_histoire_garde_son_plan_jusqu_a_son_dernier_tissage() -> None:
    """Hérité :
    test_plan_besoins::test_une_qualite_arretee_sans_histoire_garde_son_plan_jusqu_a_son_dernier_tissage.

    Arrêtée avant que l'ERP ne trace l'arrêt : son plan vaut jusqu'au mois de son dernier
    ordre (août), plus rien ensuite — ni effacé, ni prévu à jamais."""
    versions = arret_sans_histoire([VersionPlan(None, 1000, UN, actif=False)], date(2026, 8, 12))
    d = usine(plan=[PlanQualite("Q", 1000, UN, actif=False)], versions_plan={"Q": versions})
    plan = next(x for x in realise_par_qualite(d, JOUR).lignes if x.qualite == "Q").plan
    assert plan[-3] == 1000 and plan[-2] == 0  # août tissé, septembre non
    jamais = arret_sans_histoire([VersionPlan(None, 1000, UN, actif=False)], None)
    d.versions_plan = {"Q": jamais}
    assert m2_passe(d, d.plan[0], date(2025, 12, 31)) == 0


def test_l_ecart_d_un_ordre_passe_ne_bouge_pas_quand_le_poids_au_m2_change() -> None:
    """Hérité :
    test_plan_besoins::test_l_ecart_d_un_ordre_passe_ne_bouge_pas_quand_le_poids_au_m2_change.
    """
    versions = {
        "Q": [
            VersionRecette(instant(2026, 9, 1), [("FIL A", 100)], {"Poil": 1.0}),
            VersionRecette(instant(2026, 10, 1), [("FIL A", 100)], {"Poil": 2.0}),
        ]
    }
    ordre = OrdreFabrication(
        "OF-1", date(2026, 9, 10), [("Q", 100)], valide_le=instant(2026, 9, 10, 8)
    )
    fige = OrdreFabrication(
        "OF-2", date(2026, 9, 11), [("Q", 100)], theorique={"FIL A": 90.0}, perte=0.03
    )
    d = usine(
        qualites=[Qualite(code="Q", poids={"Poil": 2.0})],
        versions_recette=versions,
        ordres=[ordre, fige],
        mouvements=[
            sortie(date(2026, 9, 10), "FIL A", 101, "OF-1"),
            sortie(date(2026, 9, 11), "FIL A", 92, "OF-2"),
        ],
    )
    par_of = {x.numero_of: x for x in consommation_par_of(d)}
    assert par_of["OF-1"].theorique == pytest.approx(100)  # 1 kg/m² ce jour-là, pas 2
    assert par_of["OF-2"].theorique == pytest.approx(90)  # figé à la validation
    assert par_of["OF-2"].taux_perte_fige == 0.03


def test_un_ordre_annule_avec_retours_ne_compte_rien() -> None:
    """Hérité : test_plan_besoins::test_un_ordre_annule_avec_retours_ne_compte_rien."""
    mouvements = [
        Mouvement(date(2026, 9, 1), "SORTIE_PROD", "FIL A", 100, numero_of="OF-9", id=1),
        Mouvement(date(2026, 9, 5), "RETOUR_PRODUCTION", "FIL A", 20, numero_of="OF-9", id=2),
        # Les contre-passations, datées comme l'original.
        Mouvement(
            date(2026, 9, 1), "SORTIE_PROD", "FIL A", -100, numero_of="OF-9", id=3, contrepasse_id=1
        ),
        Mouvement(
            date(2026, 9, 5),
            "RETOUR_PRODUCTION",
            "FIL A",
            -20,
            numero_of="OF-9",
            id=4,
            contrepasse_id=2,
        ),
    ]
    fiche = next(
        x for x in consommation_par_of(usine(mouvements=mouvements)) if x.numero_of == "OF-9"
    )
    assert fiche.consomme == 0 and fiche.retours == 0 and fiche.net == 0
    assert fiche.debut == fiche.fin == date(2026, 9, 1)


def _ordre(taux_fige: float | None) -> ConsommationOrdre:
    return ConsommationOrdre(
        numero_of="OF-7",
        consomme=110.0,
        retours=0.0,
        references=[
            ConsommationReference("POIL", 105.0, 100.0, 5.0, False),
            ConsommationReference("CUIR", 1.5, 1.0, 0.5, False),
            ConsommationReference("INTRUS", 3.5, 0.0, None, True),
        ],
        lots=[],
        debut=date(2026, 9, 1),
        fin=date(2026, 9, 2),
        net=110.0,
        fabrications=[],
        qualite="Q",
        m2=100.0,
        commentaire="",
        theorique=101.0,
        taux_perte_fige=taux_fige,
        ecart=9.0,
        ecart_relatif=9.0 / 101.0,
    )


def test_ajuster_un_ordre_applique_la_perte_figee_sinon_celle_des_reglages() -> None:
    """Nouveau (CALCULS B § 7, route `ajuster_ordre`) : le prévu perte comprise, le taux figé
    avec l'ordre l'emportant sur celui des réglages ; un fil hors recette garde un écart vide."""
    lu = ajuster_ordre(_ordre(None), 0.02, {"CUIR": 0.014})
    assert lu.taux_perte == 0.02
    poil, cuir, intrus = lu.references
    assert poil.theorique == pytest.approx(102) and poil.ecart == pytest.approx(3)
    assert cuir.theorique == pytest.approx(1.02) and cuir.kg_par_ml == 0.014
    assert intrus.ecart is None and intrus.theorique == 0
    assert lu.theorique == pytest.approx(103.02) and lu.net == pytest.approx(110)
    assert lu.ecart == pytest.approx(110 - 103.02)
    assert lu.ecart_relatif == pytest.approx((110 - 103.02) / 103.02)
    fige = ajuster_ordre(_ordre(0.05), 0.02, {})
    assert fige.taux_perte == 0.05 and fige.theorique == pytest.approx(101 * 1.05)
    assert fige.numero_of == "OF-7" and fige.m2 == 100
