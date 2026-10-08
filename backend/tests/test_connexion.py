"""Connexion, essais comptés, sessions (lot S2 ; héritage K30–K36, défauts F-02, F-03, F-08).

Les comptes essayés ici sont à eux (`compte(...)`) ; les essais comptés sont oubliés après
chaque essai (une rafale ne bloque pas l'adresse des essais suivants).
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from conftest import ENTETE_ECRAN
from fabrique import *  # noqa: F403
from fabrique import POSTE_LOCAL, compte, connecter, oublier_les_essais
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update

from gestion_mp_pro.config import COOKIE_SESSION
from gestion_mp_pro.db import fabrique as sessions_db
from gestion_mp_pro.modeles import SessionOuverte, Tentative, Utilisateur
from gestion_mp_pro.services import comptes, horloge, sessions

INCORRECT = "Identifiant ou code incorrect."


@pytest.fixture(autouse=True)
def essais_oublies() -> Iterator[None]:
    """Chaque essai repart sans essai compté."""
    oublier_les_essais()
    yield
    oublier_les_essais()


def _connexion(app: FastAPI, corps: dict[str, object], **options: object) -> tuple[int, str]:
    r = TestClient(app, headers=ENTETE_ECRAN, **options).post("/api/connexion", json=corps)  # type: ignore[arg-type]
    return r.status_code, str(r.json().get("detail", ""))


def test_connexion_et_message_unique(application: FastAPI) -> None:
    """Hérité : K31 — inconnu, inactif ou code faux : même 401, même message."""
    compte("achats", identifiant="cx-actif", code="cx-actif-12")
    compte("achats", identifiant="cx-inactif", code="cx-actif-12", actif=False)
    c = connecter(application, " CX-Actif ", "cx-actif-12")
    moi = c.get("/api/moi").json()
    assert (moi["identifiant"], moi["role"], moi["voit_prix"]) == ("cx-actif", "achats", True)
    cookie = c.cookies.get(COOKIE_SESSION)
    assert cookie and len(cookie) >= 40
    for corps in (
        {"identifiant": "cx-actif", "code": "faux-code-1"},
        {"identifiant": "cx-inconnu", "code": "cx-actif-12"},
        {"identifiant": "cx-inactif", "code": "cx-actif-12"},
    ):
        assert _connexion(application, corps) == (401, INCORRECT)
    with sessions_db()() as s:
        assert s.get(SessionOuverte, sessions.empreinte(cookie)) is not None


def test_blocage_apres_cinq_echecs(application: FastAPI) -> None:
    """Hérité : K33 — 5ᵉ échec : 30 s ; même le bon code patiente ; un succès efface (429)."""
    compte("achats", identifiant="cx-bloque", code="cx-bloque-12")
    for _ in range(5):
        assert _connexion(application, {"identifiant": "cx-bloque", "code": "x"})[0] == 401
    statut, detail = _connexion(application, {"identifiant": "cx-bloque", "code": "cx-bloque-12"})
    assert (statut, detail) == (429, "Trop d'essais : patientez 30 secondes.")
    with horloge.figee(horloge.maintenant() + timedelta(seconds=31)):
        assert _connexion(application, {"identifiant": "cx-bloque", "code": "x"})[0] == 401
        statut, detail = _connexion(application, {"identifiant": "cx-bloque", "code": "x"})
        assert (statut, detail) == (429, "Trop d'essais : patientez 60 secondes.")
    assert sessions.duree_blocage(5, 5) == 30
    assert [sessions.duree_blocage(n, 5) for n in (6, 7, 9, 10, 20)] == [60, 120, 480, 900, 900]


def test_rafale_de_connexions_ne_depasse_pas_le_seuil(
    application: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hérité : test_defauts_f::test_rafale_de_connexions_ne_depasse_pas_le_seuil (F-02)."""
    compte("achats", identifiant="cx-rafale", code="rafale-f-02")
    verifies: list[str] = []
    verrou = threading.Lock()
    vrai = comptes.verifier

    def compter(code: str, empreinte: str) -> bool:
        with verrou:
            verifies.append(code)
        return vrai(code, empreinte)

    monkeypatch.setattr(comptes, "verifier", compter)
    with ThreadPoolExecutor(10) as pool:
        codes = list(
            pool.map(
                lambda _: _connexion(application, {"identifiant": "cx-rafale", "code": "mauvais"})[
                    0
                ],
                range(20),
            )
        )
    assert set(codes) <= {401, 429} and 429 in codes
    assert len(verifies) <= 5
    statut, detail = _connexion(application, {"identifiant": "cx-rafale", "code": "rafale-f-02"})
    assert statut == 429 and "patientez" in detail


def test_des_echecs_simultanes_ne_font_pas_d_erreur(application: FastAPI) -> None:
    """16 mauvais codes sur 8 fils : jamais de 500, compteur juste.

    Hérité : test_zz_restauration::test_des_echecs_de_connexion_simultanes_ne_font_pas_d_erreur
    """
    compte("achats", identifiant="cx-simultane", code="simultane-12")
    with ThreadPoolExecutor(8) as pool:
        codes = list(
            pool.map(
                lambda i: _connexion(application, {"identifiant": "cx-simultane", "code": f"f{i}"})[
                    0
                ],
                range(16),
            )
        )
    assert set(codes) <= {401, 429}
    with sessions_db()() as s:
        t = s.get(Tentative, "cx-simultane")
        assert t is not None and t.echecs >= 5


def test_une_adresse_qui_essaie_tous_les_comptes_est_bloquee(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_une_adresse_qui_essaie_tous_les_comptes_est_bloquee."""
    for i in range(5):
        compte("achats", identifiant=f"cx-cible-{i}", code="cible-f-02-x")
    codes = [
        _connexion(application, {"identifiant": f"cx-cible-{i}", "code": f"faux-{j}"})[0]
        for i in range(5)
        for j in range(4)
    ]
    assert codes.count(401) == 20
    assert _connexion(application, {"identifiant": "cx-cible-1", "code": "cible-f-02-x"})[0] == 429
    # Une autre adresse n'est pas bloquée par celle-là.
    assert (
        _connexion(
            application, {"identifiant": "cx-cible-2", "code": "cible-f-02-x"}, client=POSTE_LOCAL
        )[0]
        == 200
    )


def test_visages_reserves_au_poste_local(application: FastAPI, anonyme: TestClient) -> None:
    """Hérité : test_defauts_f::test_visages_ne_donne_pas_l_identifiant (F-02) ; P1-26 :
    ailleurs que sur le poste local ou un appareil enrôlé, liste vide."""
    uid = compte("alimentation", identifiant="cx-visage", nom="Visage Atelier", code="4821")
    assert anonyme.get("/api/visages").json() == []
    local = TestClient(application, headers=ENTETE_ECRAN, client=POSTE_LOCAL)
    visages = local.get("/api/visages").json()
    assert visages and all("identifiant" not in v for v in visages)
    moi = next(v for v in visages if v["nom"] == "Visage Atelier")
    assert moi == {
        "id": uid,
        "nom": "Visage Atelier",
        "role": "alimentation",
        "role_libelle": "Responsable alimentation machines",
        "longueur_code": 4,
    }
    r = local.post("/api/connexion", json={"compte": uid, "code": "4821"})
    assert r.status_code == 200 and r.json()["id"] == uid
    statut, detail = _connexion(application, {"compte": uid, "code": "4821"})
    assert statut == 403 and detail.startswith("Choisir son nom n'est possible que sur le poste")
    assert _connexion(application, {"compte": uid, "code": "0000"}, client=POSTE_LOCAL)[0] == 401


def test_deconnexion_exige_l_entete(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_deconnexion_sans_entete_refusee (F-08)."""
    compte("achats", identifiant="cx-sortie", code="cx-sortie-12")
    c = connecter(application, "cx-sortie", "cx-sortie-12")
    sans = TestClient(application, cookies={COOKIE_SESSION: str(c.cookies.get(COOKIE_SESSION))})
    assert sans.post("/api/deconnexion").status_code == 403
    assert c.get("/api/moi").status_code == 200
    r = c.post("/api/deconnexion")
    assert r.status_code == 204 and COOKIE_SESSION in r.headers.get("set-cookie", "")
    assert sans.get("/api/moi").json() == {
        "detail": "Connectez-vous pour continuer.",
        "code": "non_connecte",
    }


def test_compte_desactive_en_cours_de_session(application: FastAPI) -> None:
    """Hérité : K35 — compte inactif : 401 « Ce compte n'est plus actif. » à la requête suivante."""
    uid = compte("achats", identifiant="cx-coupe", code="cx-coupe-12")
    c = connecter(application, "cx-coupe", "cx-coupe-12")
    with sessions_db()() as s, s.begin():
        s.execute(update(Utilisateur).where(Utilisateur.id == uid).values(actif=False))
    assert c.get("/api/moi").json() == {
        "detail": "Ce compte n'est plus actif.",
        "code": "compte_inactif",
    }


def test_la_derniere_activite_suit_l_usage(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_la_derniere_activite_suit_l_usage (F-03)."""
    uid = compte("achats", identifiant="cx-activite", code="activite-f-03")
    c = connecter(application, "cx-activite", "activite-f-03")
    dix_jours = horloge.maintenant() - timedelta(days=10)
    with sessions_db()() as s, s.begin():
        s.execute(update(Utilisateur).where(Utilisateur.id == uid).values(vu_le=dix_jours))
        s.execute(
            update(SessionOuverte)
            .values(vu_le=dix_jours)
            .where(SessionOuverte.utilisateur_id == uid)
        )
    assert c.get("/api/moi").json()["vu_le"].startswith("2026-10-08")
    with sessions_db()() as s:
        u = s.get(Utilisateur, uid)
        assert u is not None and u.vu_le is not None and u.vu_le.date().isoformat() == "2026-10-08"
        assert u.version == 1  # la dernière activité ne touche pas la version de la fiche


def test_les_sessions_expirees_sont_purgees(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_les_sessions_expirees_sont_purgees (F-03 ; 7 et 30 jours)."""
    uid = compte("achats", identifiant="cx-purge", code="purge-f-03xx")
    maintenant = horloge.maintenant()
    vieux, recent = sessions.empreinte("vieux-jeton"), sessions.empreinte("jeton-d-hier")
    with sessions_db()() as s, s.begin():
        s.execute(
            insert(SessionOuverte),
            [
                {
                    "empreinte": vieux,
                    "utilisateur_id": uid,
                    "expire_le": maintenant - timedelta(days=8),
                },
                {
                    "empreinte": recent,
                    "utilisateur_id": uid,
                    "expire_le": maintenant - timedelta(days=1),
                },
            ],
        )
        s.add(
            Tentative(
                identifiant="cx-vieux", echecs=2, dernier_echec_le=maintenant - timedelta(days=31)
            )
        )
    connecter(application, "cx-purge", "purge-f-03xx")
    with sessions_db()() as s:
        assert s.get(SessionOuverte, vieux) is None
        assert s.get(SessionOuverte, recent) is not None
        assert s.get(Tentative, "cx-vieux") is None
        assert s.scalars(select(SessionOuverte).where(SessionOuverte.utilisateur_id == uid)).all()
