"""La table de transitions des bons (lot D3), rejouée exhaustivement : 7 états (les 6 statuts,
« à approuver » avant et après l'envoi) × 10 gestes × 4 rôles → code et statut suivant ; les
gestes permis annoncés par la fiche (`actions`) disent la même chose que le refus ; une version
périmée → 409 sur chaque écriture ; double envoi, double approbation, approbation contre
modification (deux postes en même temps : un seul passe).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.achats import Achat, bon, fiche, geste, ok, recevoir, reglage
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.services.commandes_gestes import GESTES

ETATS = (
    "brouillon",
    "a_approuver_brouillon",
    "a_approuver_parti",
    "envoyee",
    "confirmee",
    "soldee",
    "annulee",
)
STATUT_DE = {"a_approuver_brouillon": "a_approuver", "a_approuver_parti": "a_approuver"}

# Code attendu (direction ; les achats aussi, sauf approuver et renvoyer) et statut suivant.
TABLE: dict[str, dict[str, tuple[int, str | None]]] = {
    "brouillon": {
        "modifier": (200, "brouillon"), "supprimer": (204, None), "envoyer": (200, "envoyee"),
        "approuver": (409, None), "renvoyer": (409, None), "prix": (409, None),
        "expedition": (409, None), "solder": (409, None), "rouvrir": (409, None),
        "imprimer": (200, "brouillon"),
    },
    "a_approuver_brouillon": {
        "modifier": (200, "brouillon"), "supprimer": (204, None), "envoyer": (409, None),
        "approuver": (200, "envoyee"), "renvoyer": (200, "brouillon"), "prix": (409, None),
        "expedition": (409, None), "solder": (409, None), "rouvrir": (409, None),
        "imprimer": (200, "a_approuver"),
    },
    "a_approuver_parti": {
        "modifier": (200, "envoyee"), "supprimer": (409, None), "envoyer": (409, None),
        "approuver": (200, "envoyee"), "renvoyer": (200, "envoyee"),
        "prix": (200, "a_approuver"), "expedition": (200, "a_approuver"), "solder": (409, None),
        "rouvrir": (409, None), "imprimer": (200, "a_approuver"),
    },
    "envoyee": {
        "modifier": (200, "envoyee"), "supprimer": (409, None), "envoyer": (409, None),
        "approuver": (409, None), "renvoyer": (409, None), "prix": (200, "confirmee"),
        "expedition": (200, "envoyee"), "solder": (200, "annulee"), "rouvrir": (409, None),
        "imprimer": (200, "envoyee"),
    },
    "confirmee": {
        "modifier": (200, "confirmee"), "supprimer": (409, None), "envoyer": (409, None),
        "approuver": (409, None), "renvoyer": (409, None), "prix": (200, "confirmee"),
        "expedition": (200, "confirmee"), "solder": (200, "annulee"), "rouvrir": (409, None),
        "imprimer": (200, "confirmee"),
    },
    "soldee": {
        "modifier": (409, None), "supprimer": (409, None), "envoyer": (409, None),
        "approuver": (409, None), "renvoyer": (409, None), "prix": (409, None),
        "expedition": (409, None), "solder": (409, None), "rouvrir": (200, "envoyee"),
        "imprimer": (200, "soldee"),
    },
    "annulee": {
        "modifier": (409, None), "supprimer": (409, None), "envoyer": (409, None),
        "approuver": (409, None), "renvoyer": (409, None), "prix": (409, None),
        "expedition": (409, None), "solder": (409, None), "rouvrir": (200, "envoyee"),
        "imprimer": (200, "annulee"),
    },
}  # fmt: skip
SEUIL = "5000"
"""100 kg à 10 MAD partent seuls ; 1 000 kg demandent la direction."""


@pytest.fixture(scope="module")
def mad() -> Achat:
    """Une filature en dirhams et sa matière à 10 MAD le kilo."""
    a = Achat.nouveau(devise="MAD", delai=10)
    a.matiere("TABLE")
    return a


@pytest.fixture(scope="module")
def postes(application: FastAPI) -> dict[str, TestClient]:
    """Un poste connecté par rôle."""
    return {
        r: client_de(application, r)
        for r in ("direction", "achats", "alimentation", "administrateur")
    }


def batir(achats: TestClient, direction: TestClient, a: Achat, etat: str) -> dict[str, Any]:
    """Un bon dans l'état voulu (par les gestes de l'API ; la réception par la fabrique)."""
    m = a.matieres["TABLE"]
    if etat in ("brouillon", "a_approuver_brouillon"):
        b = bon(achats, a, {m: 1000 if etat == "a_approuver_brouillon" else 100})
        return b if etat == "brouillon" else geste(achats, b, "envoyer")
    b = geste(achats, bon(achats, a, {m: 100}), "envoyer")
    if etat == "a_approuver_parti":
        corps = {"version": b["version"], "lignes": [{"matiere_id": m, "quantite": 1000}]}
        b = ok(achats.put(f"/api/commandes/{b['id']}", json=corps))
    elif etat == "confirmee":
        b = geste(achats, b, "prix", lignes=[{"ligne_id": b["lignes"][0]["id"], "prix": 10}])
    elif etat == "soldee":
        recevoir(b["lignes"][0]["id"], 100)
        b = fiche(achats, b["id"])
    elif etat == "annulee":
        b = geste(achats, b, "solder")
    return b


def jouer(client: TestClient, b: dict[str, Any], nom: str, version: int | None = None) -> Any:
    """Joue un geste avec la version lue (ou celle donnée) ; rend la réponse."""
    v = b["version"] if version is None else version
    cid, m = b["id"], b["lignes"][0]["matiere_id"]
    if nom == "modifier":
        corps = {"version": v, "lignes": [{"matiere_id": m, "quantite": 100}]}
        return client.put(f"/api/commandes/{cid}", json=corps)
    if nom == "supprimer":
        return client.delete(f"/api/commandes/{cid}", params={"version": v})
    if nom == "expedition":
        return client.put(
            f"/api/commandes/{cid}/expedition", json={"version": v, "conteneur": "C1"}
        )
    if nom == "imprimer":
        return client.get(f"/api/documents/commandes/{cid}/bon")
    corps: dict[str, Any] = {"version": v}
    if nom == "renvoyer":
        corps["motif"] = "Motif d'essai"
    if nom == "prix":
        corps |= {"lignes": [{"ligne_id": b["lignes"][0]["id"], "prix": 10}],
                  "mettre_a_jour_catalogue": False}  # fmt: skip
    return client.post(f"/api/commandes/{cid}/{nom}", json=corps)


def attendu(role: str, etat: str, nom: str) -> tuple[int, str | None]:
    """Le code et le statut suivant de la table, pour ce rôle."""
    if role in ("alimentation", "administrateur"):
        return 403, None
    if role == "achats" and nom in ("approuver", "renvoyer"):
        return 403, None
    return TABLE[etat][nom]


@pytest.mark.parametrize("etat", ETATS)
def test_table_de_transitions(etat: str, postes: dict[str, TestClient], mad: Achat) -> None:
    """Chaque geste, chaque rôle, sur un bon dans cet état : code, statut suivant, et la fiche
    annonçait d'avance le permis ou la raison du refus (même phrase)."""
    achats, direction = postes["achats"], postes["direction"]
    with reglage("seuil_approbation", SEUIL):
        b = batir(achats, direction, mad, etat)
        assert b["statut"] == STATUT_DE.get(etat, etat)
        for role, client in postes.items():
            for nom in GESTES:
                code, suivant = attendu(role, etat, nom)
                annonce = fiche(direction if role != "achats" else achats, b["id"])["actions"][nom]
                r = jouer(client, b, nom)
                assert r.status_code == code, (etat, role, nom, r.text)
                if role in ("direction", "achats"):
                    assert (annonce is None) == (code < 300), (etat, role, nom, annonce)
                    if code == 409:
                        assert r.json()["detail"] == annonce
                if code == 204:
                    assert achats.get(f"/api/commandes/{b['id']}").status_code == 404
                elif code == 200 and nom != "imprimer":
                    assert r.json()["statut"] == suivant, (etat, role, nom)
                if code < 300 and nom != "imprimer":
                    b = batir(achats, direction, mad, etat)


@pytest.mark.parametrize("nom", [g for g in GESTES if g != "imprimer"])
def test_une_version_perimee_est_refusee(
    nom: str, postes: dict[str, TestClient], mad: Achat
) -> None:
    """Chaque écriture reçoit la version lue : périmée → 409 qui nomme l'auteur et l'heure."""
    etat = next(e for e in ETATS if TABLE[e][nom][0] < 300)
    with reglage("seuil_approbation", SEUIL):
        b = batir(postes["achats"], postes["direction"], mad, etat)
        if b["version"] == 1:  # un brouillon neuf : une modification fait monter sa version
            b = ok(jouer(postes["achats"], b, "modifier"))
        assert b["version"] > 1
        r = jouer(postes["direction"], b, nom, version=b["version"] - 1)
        assert r.status_code == 409 and r.json()["code"] == "conflit_version", r.text
        assert "modifiée entre-temps par" in r.json()["detail"]


def ensemble(*appels: Callable[[], Any]) -> list[int]:
    """Lance les appels au même instant (deux postes) ; rend leurs codes."""
    depart = threading.Barrier(len(appels))
    codes: list[int] = []

    def poste(appel: Callable[[], Any]) -> None:
        depart.wait()
        codes.append(appel().status_code)

    fils = [threading.Thread(target=poste, args=(a,)) for a in appels]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    return sorted(codes)


@pytest.mark.parametrize("rang", range(5))
def test_double_envoi_un_seul_numero(
    rang: int, postes: dict[str, TestClient], mad: Achat, application: FastAPI
) -> None:
    """Deux postes envoient le même brouillon : un numéro, une seule fois (M65)."""
    achats = postes["achats"]
    b = batir(achats, postes["direction"], mad, "brouillon")
    autre = client_de(application, "achats")
    assert ensemble(lambda: jouer(achats, b, "envoyer"), lambda: jouer(autre, b, "envoyer")) == [
        200,
        409,
    ]
    assert fiche(achats, b["id"])["numero"]


@pytest.mark.parametrize("rang", range(5))
def test_double_approbation_et_approbation_contre_modification(
    rang: int, postes: dict[str, TestClient], mad: Achat, application: FastAPI
) -> None:
    """Deux approbations simultanées : une passe ; une approbation pendant que les achats
    modifient : une seule des deux passe, jamais un bon approuvé sur un montant non relu."""
    direction, achats = postes["direction"], postes["achats"]
    autre = client_de(application, "direction")
    with reglage("seuil_approbation", SEUIL):
        b = batir(achats, direction, mad, "a_approuver_brouillon")
        codes = ensemble(
            lambda: jouer(direction, b, "approuver"), lambda: jouer(autre, b, "approuver")
        )
        assert codes == [200, 409]
        b = batir(achats, direction, mad, "a_approuver_brouillon")
        codes = ensemble(
            lambda: jouer(direction, b, "approuver"), lambda: jouer(achats, b, "modifier")
        )
        assert codes == [200, 409]
        f = fiche(achats, b["id"])
        assert (f["statut"], f["quantite"]) in (("envoyee", 1000), ("brouillon", 100))
