"""Concurrence des réceptions (lot D4) : deux postes ne franchissent pas l'excédent à deux (les
bons sont verrouillés avant de lire ce qu'ils ont reçu), deux clics ne valident pas deux fois
un même brouillon. Rejoués dix fois chacun (ESSAIS § 15 : boucles répétées et invariants).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.achats import Achat
from fabriques.receptions import (
    Quai,
    bon_relu,
    camion,
    ligne_du_bon,
    menage,  # noqa: F401 — fixture du module
    parti,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Mouvement

REPETITIONS = 10

pytestmark = pytest.mark.usefixtures("menage")


def _ensemble(appels: list[Callable[[], int]]) -> list[int]:
    """Lance les appels au même instant ; rend leurs codes, triés."""
    depart = threading.Barrier(len(appels))
    codes: list[int] = []

    def courir(appel: Callable[[], int]) -> None:
        depart.wait()
        codes.append(appel())

    fils = [threading.Thread(target=courir, args=(a,)) for a in appels]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    return sorted(codes)


@pytest.fixture(scope="module")
def decor() -> tuple[Achat, Quai]:
    """Un fournisseur et un magasin."""
    return Achat.nouveau(devise="MAD"), Quai.nouveau()


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_deux_postes_ne_franchissent_pas_l_excedent_a_deux(
    application: FastAPI, achats: TestClient, decor: tuple[Achat, Quai], tour: int
) -> None:
    """Hérité : test_audit2_achats::test_deux_postes_ne_franchissent_pas_l_excedent_a_deux —
    deux brouillons de 1 000 kg sur un bon de 1 000 kg validés ensemble : [200, 409], reçu
    1 000 (le second voit le premier : refus `excedent`)."""
    a, quai = decor
    m = a.matiere(f"G2BIS-{tour}")
    b = parti(achats, a, {m: 1000})
    brouillons = [
        camion(
            achats, a.fournisseur_id, [ligne_du_bon(b, m, 1000, f"P{i}", magasin_id=quai.courant)]
        )
        for i in range(2)
    ]
    postes = [client_de(application, "achats"), client_de(application, "achats")]
    appels = [
        (
            lambda p=p, r=r: (
                p.post(
                    f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}
                ).status_code
            )
        )  # fmt: skip
        for p, r in zip(postes, brouillons, strict=True)
    ]
    assert _ensemble(appels) == [200, 409]
    assert bon_relu(achats, b["id"])["recu"] == pytest.approx(1000)


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_deux_clics_ne_valident_pas_deux_fois(
    application: FastAPI, achats: TestClient, decor: tuple[Achat, Quai], tour: int
) -> None:
    """Un même brouillon validé par deux postes au même instant : une entrée en stock, un
    numéro ; le second reçoit 409 (version périmée ou déjà validée)."""
    a, quai = decor
    m = a.matiere(f"CLIC-{tour}")
    r = camion(achats, a.fournisseur_id,
               [{"matiere_id": m, "lot_numero": "C-1", "quantite_pesee": 10,
                 "magasin_id": quai.courant}])  # fmt: skip
    postes = [client_de(application, "achats"), client_de(application, "achats")]
    appels = [
        (
            lambda p=p: (
                p.post(
                    f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}
                ).status_code
            )
        )  # fmt: skip
        for p in postes
    ]
    assert _ensemble(appels) == [200, 409]
    with sessions()() as s:
        n = s.scalar(select(func.count()).where(Mouvement.reception_id == r["id"]))
    assert n == 1
