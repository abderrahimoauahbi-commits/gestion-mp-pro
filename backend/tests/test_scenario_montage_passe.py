"""Le fil monté d'un soir passé sur toutes les pages (défaut trouvé par le scénario V2).

Le scénario de bout en bout (étape 22, vérificateur V1) a montré qu'au 30 novembre le Cockpit
ne proposait pas d'acheter le poil monté sur le métier, alors que le Plan d'achat le proposait :
le Cockpit, la Valorisation, les contrôles et le bilan rejouaient le montage du soir (décision
de Mohamed U8, D8 : « le fil monté est du stock, à toute date »), mais l'état du stock et le plan
d'achat d'une date passée l'ignoraient (montage du moteur inconnu avant aujourd'hui). Une date,
un chiffre : les pages de stock et d'achat lisent désormais les mêmes données du soir.
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour  # noqa: F401

from gestion_mp_pro.modeles import MontageEvenement
from gestion_mp_pro.services import horloge


def _ligne(lignes: list[dict[str, Any]], reference: str) -> dict[str, Any]:
    return next(x for x in lignes if x["reference"] == reference)


def test_le_fil_monte_hier_compte_au_stock_et_au_plan_d_achat_d_hier(usine: Usine) -> None:
    u = usine
    m = u.matiere("MONTE HIER", poids_bobine=Decimal(2))
    x = u.ouvrir(m, 100, 10, le=jour(-3))
    u.sortir(x, 40, le=jour(-3))
    metier = u.metier(fils=((1, m, 2),))
    ligne = {"etage": 1, "matiere_id": m, "reference": "MONTE HIER", "metres": 1.0,
             "pourcentage": 100.0, "commentaire": "", "kg": 20.0}  # fmt: skip
    u.s.add(MontageEvenement(
        metier_id=metier.id, etage=1, avant=[ligne], apres=[{**ligne, "metres": 2.0, "kg": 40.0}],
        quand=datetime.combine(jour(), time(9), tzinfo=horloge.FUSEAU),
    ))  # fmt: skip
    u.s.flush()
    hier = jour(-1).isoformat()
    valo = _ligne(u.get(u.achats, "/api/valorisation", date=hier)["lignes"], "MONTE HIER")
    stock = _ligne(u.get(u.achats, "/api/stock", date=hier)["lignes"], "MONTE HIER")
    assert valo["stock_machine"] == 20
    assert stock["stock_machine"] == 20
    assert stock["stock_disponible"] == 60 + 20
    budget = u.get(u.direction, "/api/cockpit", date=hier)["achats"]["budget_a_commander_mad"]
    plan = u.get(u.achats, "/api/plan-achat", date=hier)["indicateurs"]["budget_mad"]
    assert plan == budget
