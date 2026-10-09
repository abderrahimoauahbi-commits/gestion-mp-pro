"""Table de transitions des réceptions (lot D4 ; PLAN-DE-RECETTE § 4) : 3 statuts × 5 gestes ×
4 rôles, rejouée exhaustivement — code attendu, statut suivant, et la fiche annonce d'avance la
même chose (`actions`) ; version périmée → 409 sur chaque écriture.
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.receptions import (
    Quai,
    camion,
    fiche,
    geste,
    j,
)
from fastapi.testclient import TestClient

GESTES = ("modifier", "supprimer", "valider", "annuler", "facture")
STATUTS = ("brouillon", "validee", "annulee")
ATTENDU: dict[tuple[str, str], tuple[int, str | None]] = {
    ("brouillon", "modifier"): (200, "brouillon"),
    ("brouillon", "supprimer"): (204, None),
    ("brouillon", "valider"): (200, "validee"),
    ("brouillon", "annuler"): (409, "brouillon"),
    ("brouillon", "facture"): (409, "brouillon"),
    ("validee", "modifier"): (409, "validee"),
    ("validee", "supprimer"): (409, "validee"),
    ("validee", "valider"): (409, "validee"),
    ("validee", "annuler"): (200, "annulee"),
    ("validee", "facture"): (200, "validee"),
    ("annulee", "modifier"): (409, "annulee"),
    ("annulee", "supprimer"): (409, "annulee"),
    ("annulee", "valider"): (409, "annulee"),
    ("annulee", "annuler"): (409, "annulee"),
    ("annulee", "facture"): (409, "annulee"),
}
"""(statut, geste) → (code, statut suivant) pour la direction et les achats."""


@pytest.fixture(scope="module")
def decor() -> tuple[Achat, Quai, int]:
    """Un fournisseur, une matière, un magasin."""
    a = Achat.nouveau(devise="MAD")
    return a, Quai.nouveau(), a.matiere("TRANSITION")


def _ligne(decor: tuple[Achat, Quai, int]) -> dict[str, Any]:
    _, quai, m = decor
    return {"matiere_id": m, "lot_numero": "T-1", "quantite_pesee": 5, "magasin_id": quai.courant}


def _en_etat(client: TestClient, decor: tuple[Achat, Quai, int], statut: str) -> dict[str, Any]:
    """Une réception dans ce statut."""
    r = camion(client, decor[0].fournisseur_id, [_ligne(decor)])
    if statut != "brouillon":
        r = geste(client, r, "valider")
    if statut == "annulee":
        r = geste(client, r, "annuler", motif="pour la table")
    return r


def _jouer(client: TestClient, r: dict[str, Any], nom: str, decor: Any, version: int) -> Any:
    """Le geste, à la version donnée."""
    ident = r["id"]
    if nom == "modifier":
        corps = {"date": j(), "fournisseur_id": decor[0].fournisseur_id, "lignes": [_ligne(decor)]}
        return client.put(f"/api/receptions/{ident}", json=corps | {"version": version})
    if nom == "supprimer":
        return client.delete(f"/api/receptions/{ident}", params={"version": version})
    if nom == "facture":
        return client.put(
            f"/api/receptions/{ident}/facture", json={"version": version, "numero": "F-TR"}
        )
    corps = {"version": version} | ({"motif": "table"} if nom == "annuler" else {})
    return client.post(f"/api/receptions/{ident}/{nom}", json=corps)


@pytest.mark.parametrize("statut", STATUTS)
@pytest.mark.parametrize("nom", GESTES)
@pytest.mark.parametrize("role", ("direction", "achats", "alimentation", "administrateur"))
def test_table_de_transitions(
    request: pytest.FixtureRequest, decor: Any, statut: str, nom: str, role: str
) -> None:
    """Chaque (statut, geste, rôle) : code attendu, statut suivant, `actions` de la fiche."""
    achats: TestClient = request.getfixturevalue("achats")
    client: TestClient = request.getfixturevalue(role)
    r = _en_etat(achats, decor, statut)
    lu = fiche(achats, r["id"])
    reponse = _jouer(client, r, nom, decor, lu["version"])
    if role in ("alimentation", "administrateur"):
        assert reponse.status_code == 403
        assert fiche(achats, r["id"])["statut"] == statut
        return
    code, suivant = ATTENDU[(statut, nom)]
    assert reponse.status_code == code, reponse.text
    assert (lu["actions"][nom] is None) == (code < 300)
    if code >= 300:
        assert reponse.json()["detail"] == lu["actions"][nom]
    if suivant is None:
        assert achats.get(f"/api/receptions/{r['id']}").status_code == 404
    else:
        assert fiche(achats, r["id"])["statut"] == suivant


@pytest.mark.parametrize("nom", GESTES)
def test_une_version_perimee_est_refusee(achats: TestClient, decor: Any, nom: str) -> None:
    """Version périmée → 409 `conflit_version` (qui nomme l'auteur), rien n'est écrit."""
    statut = "validee" if nom in ("annuler", "facture") else "brouillon"
    r = _en_etat(achats, decor, statut)
    reponse = _jouer(achats, r, nom, decor, r["version"] + 7)
    assert reponse.status_code == 409 and reponse.json()["code"] == "conflit_version"
    assert "modifiée entre-temps par Achats" in reponse.json()["detail"]
    assert fiche(achats, r["id"])["statut"] == statut
