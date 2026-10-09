"""Table de transitions des ordres de fabrication (lot D6), rejouée exhaustivement : statut
(brouillon, validé, annulé) × geste (modifier, supprimer, valider, annuler) × rôle (direction,
achats, alimentation) → code HTTP et statut suivant. Données validées en base (les routes ont
leurs sessions), ordres datés d'aujourd'hui.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.ordres import JOUR, Atelier, atelier
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Ordre
from gestion_mp_pro.modeles.enums import StatutOrdre

STATUTS = ("brouillon", "valide", "annule")
ROLES = ("direction", "achats", "alimentation")


def _corps(a: Atelier, kg: float = 1) -> dict[str, Any]:
    lot = a.lot("E-L1")
    return {
        "date": str(JOUR),
        "magasin_id": a.m.courant.id,
        "lignes": [{"lot_id": lot.id, "quantite": kg}],
    }


GESTES = ("modifier", "supprimer", "valider", "annuler")


def _requete(geste: str, a: Atelier, o: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """La requête d'un geste sur l'ordre lu (à sa version)."""
    url, version = f"/api/ordres/{o['id']}", o["version"]
    if geste == "modifier":
        return "PUT", url, {"json": {**_corps(a, 2), "version": version}}
    if geste == "supprimer":
        return "DELETE", url, {"params": {"version": version}}
    return "POST", f"{url}/{geste}", {"json": {"version": version}}


PERMIS: dict[tuple[str, str], tuple[int, str | None]] = {
    ("brouillon", "modifier"): (200, "brouillon"),
    ("brouillon", "supprimer"): (204, None),
    ("brouillon", "valider"): (200, "valide"),
    ("brouillon", "annuler"): (409, "brouillon"),
    ("valide", "modifier"): (409, "valide"),
    ("valide", "supprimer"): (409, "valide"),
    ("valide", "valider"): (409, "valide"),
    ("valide", "annuler"): (200, "annule"),
    ("annule", "modifier"): (409, "annule"),
    ("annule", "supprimer"): (409, "annule"),
    ("annule", "valider"): (409, "annule"),
    ("annule", "annuler"): (409, "annule"),
}
"""(statut, geste) → (code, statut après) pour la direction et l'alimentation ; les achats
reçoivent 403 partout et rien ne bouge."""


@pytest.fixture(scope="module")
def a() -> Iterator[Atelier]:
    """Un décor pour toute la table (assez de poil pour 36 ordres)."""
    with fabrique()() as s:
        decor = atelier(s)
        s.commit()
    yield decor


def _ordre(alimentation: TestClient, a: Atelier, statut: str) -> dict[str, Any]:
    o = alimentation.post("/api/ordres", json=_corps(a)).json()
    if statut != "brouillon":
        o = alimentation.post(
            f"/api/ordres/{o['id']}/valider", json={"version": o["version"]}
        ).json()
    if statut == "annule":
        o = alimentation.post(
            f"/api/ordres/{o['id']}/annuler", json={"version": o["version"]}
        ).json()
    assert o["statut"] == statut, o
    return o


@pytest.fixture
def postes(
    direction: TestClient, achats: TestClient, alimentation: TestClient
) -> dict[str, TestClient]:
    """Un client par rôle."""
    return {"direction": direction, "achats": achats, "alimentation": alimentation}


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("geste", GESTES)
@pytest.mark.parametrize("statut", STATUTS)
def test_transitions_des_ordres(
    statut: str, geste: str, role: str, a: Atelier, postes: dict[str, TestClient]
) -> None:
    """Chaque case de la table : le code, puis le statut en base."""
    alimentation = postes["alimentation"]
    o = _ordre(alimentation, a, statut)
    methode, url, options = _requete(geste, a, o)
    r = postes[role].request(methode, url, **options)
    code, apres = (403, statut) if role == "achats" else PERMIS[(statut, geste)]
    assert r.status_code == code, r.text
    with fabrique()() as s:
        lu = s.scalar(select(Ordre.statut).where(Ordre.id == o["id"]))
    assert (StatutOrdre(lu).value if lu else None) == apres
    if lu == StatutOrdre.brouillon:
        version = alimentation.get(f"/api/ordres/{o['id']}").json()["version"]
        alimentation.delete(f"/api/ordres/{o['id']}", params={"version": version})
