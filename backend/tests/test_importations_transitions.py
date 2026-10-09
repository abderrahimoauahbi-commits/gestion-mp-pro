"""Table de transitions des dossiers d'importation (lot D7 ; PLAN-DE-RECETTE § 4) : 3 statuts ×
6 gestes × 4 rôles, rejouée exhaustivement — code attendu, statut suivant, et la fiche annonce
d'avance la même chose (`actions`) ; version périmée → 409 sur chaque écriture.
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.importations import Import, a_la_main, fiche, frais, geste, ouvrir, poste
from fastapi.testclient import TestClient

GESTES = ("modifier", "frais", "cours", "cloturer", "rouvrir", "annuler")
STATUTS = ("ouvert", "clos", "annule")
ATTENDU: dict[tuple[str, str], tuple[int, str]] = {
    ("ouvert", "modifier"): (200, "ouvert"),
    ("ouvert", "frais"): (200, "ouvert"),
    ("ouvert", "cours"): (200, "ouvert"),
    ("ouvert", "cloturer"): (200, "clos"),
    ("ouvert", "rouvrir"): (409, "ouvert"),
    ("ouvert", "annuler"): (200, "annule"),
    ("clos", "modifier"): (409, "clos"),
    ("clos", "frais"): (409, "clos"),
    ("clos", "cours"): (409, "clos"),
    ("clos", "cloturer"): (409, "clos"),
    ("clos", "rouvrir"): (200, "ouvert"),
    ("clos", "annuler"): (409, "clos"),
    ("annule", "modifier"): (409, "annule"),
    ("annule", "frais"): (409, "annule"),
    ("annule", "cours"): (409, "annule"),
    ("annule", "cloturer"): (409, "annule"),
    ("annule", "rouvrir"): (409, "annule"),
    ("annule", "annuler"): (409, "annule"),
}
"""(statut, geste) → (code, statut suivant) pour la direction et les achats."""


@pytest.fixture(scope="module")
def imp() -> Import:
    """Un fournisseur étranger (cours 10)."""
    return Import.nouveau(cours="10")


def _en_etat(client: TestClient, imp: Import, statut: str) -> dict[str, Any]:
    """Un dossier d'une facture neuve, dans ce statut."""
    nom = f"TR-{statut}-{len(imp.factures)}"
    imp.recevoir(client, nom, [("FIL", "TR", 100, 2)])
    d = ouvrir(client, imp.f(nom))
    if statut == "clos":
        d = geste(client, d, "cloturer", alertes_lues=True)
    if statut == "annule":
        d = geste(client, d, "annuler", motif="pour la table")
    return d


def _jouer(client: TestClient, d: dict[str, Any], nom: str, version: int) -> Any:
    """Le geste, à la version donnée."""
    url = f"/api/dossiers/{d['id']}"
    if nom == "modifier":
        corps = {
            "libelle": "table",
            "banque": "AWB",
            "commentaire": "",
            "date_arrivee": d["date_arrivee"],
        }
        return client.put(url, json={**corps, "version": version})
    if nom == "cours":
        return client.put(f"{url}/cours", json={"version": version, "cours": 10.2})
    if nom == "frais":
        return client.post(
            f"{url}/frais", json={"version": version, "poste_id": poste("DD"), "montant": 10}
        )
    corps = {"version": version}
    corps |= {"motif": "table"} if nom in ("annuler", "rouvrir") else {}
    corps |= {"alertes_lues": True} if nom == "cloturer" else {}
    return client.post(f"{url}/{nom}", json=corps)


@pytest.mark.parametrize("statut", STATUTS)
@pytest.mark.parametrize("nom", GESTES)
@pytest.mark.parametrize("role", ("direction", "achats", "alimentation", "administrateur"))
def test_table_de_transitions(
    request: pytest.FixtureRequest, imp: Import, statut: str, nom: str, role: str
) -> None:
    """Chaque (statut, geste, rôle) : code attendu, statut suivant, `actions` de la fiche."""
    achats: TestClient = request.getfixturevalue("achats")
    client: TestClient = request.getfixturevalue(role)
    d = _en_etat(achats, imp, statut)
    lu = fiche(achats, d["id"])
    reponse = _jouer(client, d, nom, lu["version"])
    if role in ("alimentation", "administrateur"):
        assert reponse.status_code == 403
        assert fiche(achats, d["id"])["statut"] == statut
        return
    code, suivant = ATTENDU[(statut, nom)]
    assert reponse.status_code == code, reponse.text
    assert (lu["actions"][nom] is None) == (code < 300)
    if code >= 300:
        assert reponse.json()["detail"] == lu["actions"][nom]
    assert fiche(achats, d["id"])["statut"] == suivant


GESTES_VERSIONNES = (
    "modifier",
    "frais",
    "cours",
    "cloturer",
    "annuler",
    "rattacher",
    "detacher",
    "cours-des-bons",
    "ligne",
    "retirer",
    "modifier_frais",
    "retirer_frais",
    "rouvrir",
    "saisir",
)


def _perime_a_la_main(client: TestClient, imp: Import, nom: str) -> Any:
    """Saisir ou retirer une marchandise d'un dossier à la main, à une version périmée."""
    d = a_la_main(client)
    corps = {"matiere_id": imp.matiere("FIL"), "quantite_kg": 1, "valeur_devise": 1}
    d = geste(client, d, "lignes", **corps)
    if nom == "saisir":
        return client.post(f"/api/dossiers/{d['id']}/lignes", json={**corps, "version": 99})
    x = d["lignes"][0]
    return client.delete(f"/api/dossiers/{d['id']}/lignes/{x['id']}", params={"version": 99})


def _perime_frais(client: TestClient, d: dict[str, Any], nom: str) -> Any:
    """Modifier ou retirer un frais, à une version (du frais) périmée."""
    x = frais(client, d, "DD", 10)["frais"][0]
    url = f"/api/dossiers/{d['id']}/frais/{x['id']}"
    if nom == "retirer_frais":
        return client.delete(url, params={"version": x["version"] + 5})
    return client.put(
        url, json={"version": x["version"] + 5, "poste_id": x["poste_id"], "montant": 20}
    )


def _perime(client: TestClient, imp: Import, nom: str) -> Any:
    """Le geste `nom` envoyé à une version périmée (rien ne doit s'écrire)."""
    if nom in ("saisir", "retirer"):
        return _perime_a_la_main(client, imp, nom)
    d = _en_etat(client, imp, "clos" if nom == "rouvrir" else "ouvert")
    if nom in ("modifier_frais", "retirer_frais"):
        return _perime_frais(client, d, nom)
    url = f"/api/dossiers/{d['id']}"
    if nom == "ligne":
        return client.put(
            f"{url}/lignes/{d['lignes'][0]['id']}", json={"version": 99, "commentaire": "x"}
        )
    autres = {
        "rattacher": {"facture_id": d["facture"]["id"]},
        "detacher": {"reception_id": d["receptions"][0]["id"]},
        "annuler": {"motif": "table"},
        "cours-des-bons": {},
    }
    if nom in autres:
        return client.post(f"{url}/{nom}", json={"version": 99, **autres[nom]})
    return _jouer(client, d, nom, 99)


@pytest.mark.parametrize("nom", GESTES_VERSIONNES)
def test_une_version_perimee_est_refusee(achats: TestClient, imp: Import, nom: str) -> None:
    """Version périmée → 409 `conflit_version` (qui nomme l'auteur), rien n'est écrit."""
    reponse = _perime(achats, imp, nom)
    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "conflit_version"
    assert "modifié entre-temps par Achats" in reponse.json()["detail"]
