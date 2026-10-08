"""En-têtes et protections (API-PRO § 0.5, ARCHITECTURE § 4 et § 5.4) : anti-falsification sur
toute écriture (déconnexion comprise), en-têtes de sécurité même sur les refus du middleware,
`X-Heure-Serveur`, `X-Requete`, 503, journal d'une ligne par requête (lot S0)."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

import pytest
from fastapi.testclient import TestClient

from gestion_mp_pro.db import DISPONIBILITE

SECURITE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


def _securite(entetes: Mapping[str, str]) -> None:
    for nom, valeur in SECURITE.items():
        assert entetes[nom] == valeur, nom
    assert "frame-ancestors 'none'" in entetes["Content-Security-Policy"]


@pytest.mark.parametrize("methode", ["POST", "PUT", "DELETE", "PATCH"])
@pytest.mark.parametrize(
    "chemin", ["/api/deconnexion", "/api/commandes/12/envoyer", "/api/matieres", "/api"]
)
def test_ecriture_sans_entete_refusee(client_brut: TestClient, methode: str, chemin: str) -> None:
    r = client_brut.request(methode, chemin, json={})
    assert r.status_code == 403
    assert r.json() == {
        "detail": "Requête refusée : elle ne vient pas de l'écran de Gestion MP PRO.",
        "code": "entete_absente",
    }
    _securite(r.headers)
    assert r.headers["Cache-Control"] == "no-store"
    assert re.fullmatch(r"[0-9a-f]{16}", r.headers["X-Requete"])
    assert r.headers["X-Heure-Serveur"] == "2026-10-08T10:00:00"


def test_entete_de_gestion_mp_ou_valeur_fausse_refusee(client_brut: TestClient) -> None:
    for entetes in ({"X-Gestion-MP": "1"}, {"X-Gestion-MP-PRO": "0"}, {"X-Gestion-MP-PRO": ""}):
        assert client_brut.post("/api/deconnexion", headers=entetes).status_code == 403


@pytest.mark.parametrize(
    "chemin", ["/api/connexion", "/api/installation", "/api/appareils/enroler"]
)
def test_trois_ecritures_sans_entete(client_brut: TestClient, chemin: str) -> None:
    r = client_brut.post(chemin, json={})
    assert r.status_code != 403
    assert r.json()["code"] != "entete_absente"


def test_lecture_sans_entete_permise(client_brut: TestClient) -> None:
    r = client_brut.get("/api/route-inconnue")
    assert r.status_code == 404
    assert r.json()["code"] == "route_inconnue"
    _securite(r.headers)


def test_avec_entete_l_ecriture_passe_le_middleware(client: TestClient) -> None:
    r = client.post("/api/deconnexion")
    assert r.json()["code"] != "entete_absente"


def test_en_tetes_de_l_api(client: TestClient) -> None:
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Heure-Serveur"] == "2026-10-08T10:00:00"
    _securite(r.headers)
    a, b = client.get("/api/openapi.json"), client.get("/api/openapi.json")
    assert a.headers["X-Requete"] != b.headers["X-Requete"]


def test_hors_api_en_tetes_de_securite_sans_heure(client: TestClient) -> None:
    r = client.get("/favicon-absente.png")
    _securite(r.headers)
    assert "X-Heure-Serveur" not in r.headers
    assert re.fullmatch(r"[0-9a-f]{16}", r.headers["X-Requete"])


def test_documentation_sans_csp(client: TestClient) -> None:
    r = client.get("/api/docs")
    assert r.status_code == 200
    assert "Content-Security-Policy" not in r.headers
    assert r.headers["X-Frame-Options"] == "DENY"


def test_503_si_schema_en_retard(client: TestClient) -> None:
    DISPONIBILITE.schema_en_retard = True
    try:
        r = client.get("/api/route-quelconque")
        assert r.status_code == 503
        assert r.json()["code"] == "schema_en_retard"
        _securite(r.headers)
        assert client.get("/api/openapi.json").status_code == 200
        assert client.get("/api/sante").json()["code"] != "schema_en_retard"
    finally:
        DISPONIBILITE.schema_en_retard = False


def test_503_si_restauration_en_cours(client: TestClient) -> None:
    DISPONIBILITE.motif_base, DISPONIBILITE.controle_le = "restauration_en_cours", 1e18
    try:
        r = client.get("/api/route-quelconque")
        assert r.status_code == 503
        assert r.json()["code"] == "restauration_en_cours"
    finally:
        DISPONIBILITE.motif_base, DISPONIBILITE.controle_le = None, 0.0


def test_une_ligne_de_journal_par_requete(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="gestion_mp_pro.requetes"):
        r = client.post("/api/commandes/12/envoyer", json={"version": 1})
    lignes = [x.getMessage() for x in caplog.records if x.name == "gestion_mp_pro.requetes"]
    assert len(lignes) == 1
    attendu = (
        rf"requete={r.headers['X-Requete']} utilisateur=- role=- "
        rf"POST /api/commandes/12/envoyer {r.status_code} \d+ ms"
    )
    assert re.fullmatch(attendu, lignes[0])
