"""Appareils enrôlés et accès au serveur (lot S2 ; ARCHITECTURE § 5.1, routes 5, 6, 19–22).

QR d'enrôlement à usage unique (15 minutes) ; visages réservés au poste local ou à un appareil
enrôlé ; un appareil retiré perd ses sessions ; l'accès dit l'adresse du QR et alerte s'il
mène à localhost (héritage A11–A13, X5).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

from conftest import ENTETE_ECRAN
from fabrique import *  # noqa: F403
from fabrique import compte
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.config import COOKIE_APPAREIL, COOKIE_SESSION
from gestion_mp_pro.db import fabrique as sessions_db
from gestion_mp_pro.modeles import Journal, SessionOuverte
from gestion_mp_pro.services import appareils, horloge


def _enroler(client: TestClient, nom: str) -> tuple[int, str]:
    r = client.post("/api/appareils", json={"nom": nom})
    assert r.status_code == 201, r.text
    corps = r.json()
    assert corps["qr_svg"].startswith("<svg") and corps["expire_le"].startswith("2026-10-08T10:15")
    lien = urlsplit(corps["lien"])
    assert lien.path == "/enroler"
    return corps["id"], parse_qs(lien.query)["jeton"][0]


def test_enrolement_a_usage_unique(application: FastAPI, direction: TestClient) -> None:
    ident, jeton = _enroler(direction, "Téléphone atelier 1")
    telephone = TestClient(application)  # sans en-tête : l'enrôlement est permis ainsi
    r = telephone.post("/api/appareils/enroler", json={"jeton": jeton})
    assert r.status_code == 204 and COOKIE_APPAREIL in r.headers["set-cookie"]
    assert "Max-Age=34560000" in r.headers["set-cookie"]
    r = TestClient(application).post("/api/appareils/enroler", json={"jeton": jeton})
    assert r.status_code == 409 and r.json() == {
        "detail": "Ce QR d'enrôlement a expiré ou a déjà servi : en demander un nouveau dans "
        "Administration › Appareils.",
        "code": "enrolement_expire",
    }
    fiche = next(a for a in direction.get("/api/appareils").json() if a["id"] == ident)
    assert fiche["enrole"] is True and fiche["cree_par"] == "Direction"
    with sessions_db()() as s:
        actions = s.scalars(
            select(Journal.action)
            .where(Journal.objet == "appareil", Journal.objet_id == ident)
            .order_by(Journal.id)
        )
        assert list(actions) == ["appareil à enrôler", "enrôlement d'appareil"]


def test_enrolement_expire_apres_quinze_minutes(
    application: FastAPI, administrateur: TestClient
) -> None:
    _, jeton = _enroler(administrateur, "Téléphone en retard")
    with horloge.figee(horloge.maintenant() + timedelta(minutes=16)):
        r = TestClient(application).post("/api/appareils/enroler", json={"jeton": jeton})
    assert r.status_code == 409
    assert (
        administrateur.post("/api/appareils", json={"nom": "Téléphone en retard"}).status_code
        == 409
    )


def test_appareil_enrole_voit_les_visages_puis_est_retire(
    application: FastAPI, direction: TestClient
) -> None:
    """P1-26 : les visages sur un appareil enrôlé ; le retirer ferme ses sessions."""
    uid = compte("alimentation", identifiant="ap-atelier", nom="Atelier Enrôlé", code="7531")
    ident, jeton = _enroler(direction, "Téléphone atelier 2")
    telephone = TestClient(application, headers=ENTETE_ECRAN)
    assert telephone.get("/api/visages").json() == []
    assert telephone.post("/api/appareils/enroler", json={"jeton": jeton}).status_code == 204
    assert any(v["id"] == uid for v in telephone.get("/api/visages").json())
    assert telephone.post("/api/connexion", json={"compte": uid, "code": "7531"}).status_code == 200
    with sessions_db()() as s:
        ouvertes = s.scalars(
            select(SessionOuverte).where(SessionOuverte.utilisateur_id == uid)
        ).all()
        assert [o.appareil_id for o in ouvertes] == [ident]
    assert direction.delete(f"/api/appareils/{ident}").status_code == 204
    assert telephone.get("/api/moi").status_code == 401
    assert telephone.get("/api/visages").json() == []
    assert direction.delete("/api/appareils/999999").json()["detail"] == "Appareil introuvable."


def test_appareils_reserves_a_la_direction_et_a_l_administrateur(
    achats: TestClient, alimentation: TestClient
) -> None:
    for client in (achats, alimentation):
        assert client.get("/api/appareils").status_code == 403
        assert client.post("/api/appareils", json={"nom": "Pirate"}).status_code == 403


def test_acces_et_qr(
    direction: TestClient, alimentation: TestClient, administrateur: TestClient
) -> None:
    """Hérité : A11–A13 — adresse du QR jamais localhost sans le dire ; QR en SVG."""
    corps = alimentation.get("/api/acces").json()
    assert corps["adresse_qr"] == "http://testserver"
    assert corps["alerte_localhost"] is None
    assert [a["libelle"] for a in corps["adresses"]] == ["Adresse réseau", "Nom de la machine"]
    r = administrateur.get("/api/acces/qr")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    r = direction.get("/api/acces/qr", params={"adresse": "ftp://usine"})
    assert r.status_code == 422
    assert (
        r.json()["detail"]
        == "L'adresse commence par http:// ou https:// (ex. http://mac-usine:8050)."
    )


def test_alerte_si_le_qr_mene_a_localhost() -> None:
    """X5 : appelé par localhost, le QR prend l'adresse réseau ; s'il reste local, alerte."""
    assert appareils.est_local("http://localhost:8050") and appareils.est_local("http://127.0.0.1")
    assert appareils.est_local("http://poste.localhost") and not appareils.est_local(
        "http://mac-usine:8050"
    )
    with sessions_db()() as s:
        a = appareils.acces(s, "http://localhost:8050/")
    assert not a.adresse_qr.startswith("http://localhost")
    if appareils.est_local(a.adresse_qr):
        assert a.alerte_localhost is not None


def test_acces_https_sans_port(application: FastAPI, alimentation: TestClient) -> None:
    """Hérité : test_defauts_g::test_acces_https_sans_port (G-13) — les adresses d'accès
    reprennent le schéma et le port de la requête : derrière HTTPS, ni « :8050 » ni « http »."""
    jeton = str(alimentation.cookies.get(COOKIE_SESSION))
    ip = appareils.ip_reseau()

    def acces(base_url: str) -> dict[str, Any]:
        poste = TestClient(application, base_url=base_url, headers=ENTETE_ECRAN)
        poste.cookies.set(COOKIE_SESSION, jeton)
        r = poste.get("/api/acces")
        assert r.status_code == 200, r.text
        return dict(r.json())

    https = acces("https://localhost")
    assert https["adresse_qr"] == f"https://{ip}"
    assert https["adresses"][0] == {"libelle": "Adresse réseau", "adresse": f"https://{ip}"}
    assert https["adresses"][1]["adresse"].startswith("https://")
    assert ":8050" not in https["adresses"][1]["adresse"]
    assert acces("http://localhost:8030")["adresse_qr"] == f"http://{ip}:8030"
    assert acces("https://mac-usine:443")["adresses"][0]["adresse"] == f"https://{ip}"
