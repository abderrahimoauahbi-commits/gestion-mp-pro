"""Fabrique des essais : comptes de chaque rôle, connexions, clients (lot S2 ; LOTS § 0.3).

Les lots D écrivent leurs fabriques dans `tests/fabriques/<domaine>.py` et prennent ici les
comptes et les clients connectés. Dans un module d'essai :

    from fabrique import *  # noqa: F403  (les fixtures : direction, achats, alimentation,
                            #  administrateur, anonyme, comptes)
    from fabrique import compte, connecter, client_de, oublier_les_essais

- Quatre comptes de base, un par rôle (`direction`/`direction-1`, `achats`/`achats-12`,
  `alimentation`/`1234`, `administrateur`/`administrateur-1`), recréés d'office si la base a
  été vidée entre-temps (`test_migrations` la remigre) : ne jamais changer leur code ni leur
  rôle dans un essai — prendre un compte à soi avec `compte(role)`.
- Les clients sont des `TestClient` sans cycle de vie (rapides), avec l'en-tête de l'écran ;
  la session d'un compte de base est gardée d'un essai à l'autre tant qu'elle est en base.
- `compte(...)` écrit directement en base (pas de journal) : c'est un décor d'essai.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from functools import lru_cache

import pytest
from conftest import ENTETE_ECRAN
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from gestion_mp_pro.config import COOKIE_SESSION
from gestion_mp_pro.db import fabrique as fabrique_de_sessions
from gestion_mp_pro.modeles import SessionOuverte, Tentative, Utilisateur
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services import comptes as service_comptes
from gestion_mp_pro.services import horloge, sessions

__all__ = [
    "achats",
    "administrateur",
    "alimentation",
    "anonyme",
    "client_de",
    "compte",
    "comptes",
    "connecter",
    "direction",
    "oublier_les_essais",
]

CODES: dict[str, str] = {
    Role.direction: "direction-1",
    Role.achats: "achats-12",
    Role.alimentation: "1234",
    Role.administrateur: "administrateur-1",
}
"""Les codes des comptes de base (identifiant = nom du rôle)."""

NOMS: dict[str, str] = {
    Role.direction: "Direction",
    Role.achats: "Achats",
    Role.alimentation: "Alimentation",
    Role.administrateur: "Administrateur",
}
POSTE_LOCAL = ("127.0.0.1", 50000)
_RANG = itertools.count(1)
_JETONS: dict[str, str] = {}


@lru_cache(maxsize=64)
def empreinte_de(code: str) -> str:
    """L'empreinte d'un code, calculée une fois par séance (scrypt est lent à dessein)."""
    return service_comptes.hacher(code)


def _inserer(identifiant: str, nom: str, role: str, code: str, actif: bool = True) -> int:
    """Insère un compte directement en base ; rend son id."""
    with fabrique_de_sessions()() as s, s.begin():
        u = Utilisateur(
            identifiant=identifiant,
            nom=nom,
            role=Role(role),
            empreinte_code=empreinte_de(code),
            actif=actif,
        )
        s.add(u)
        s.flush()
        return u.id


def assurer_comptes() -> dict[str, int]:
    """Les quatre comptes de base, créés s'ils manquent ; rend `{rôle: id}`."""
    with fabrique_de_sessions()() as s:
        trouves = dict(
            s.execute(
                select(Utilisateur.identifiant, Utilisateur.id).where(
                    Utilisateur.identifiant.in_(list(CODES))
                )
            ).all()
        )
    for role, code in CODES.items():
        if role not in trouves:
            trouves[role] = _inserer(role, NOMS[role], role, code)
    return {str(r): trouves[r] for r in CODES}


def compte(
    role: str,
    *,
    identifiant: str | None = None,
    code: str | None = None,
    nom: str | None = None,
    actif: bool = True,
) -> int:
    """Un compte à soi (identifiant unique par défaut) ; code par défaut celui du rôle."""
    rang = next(_RANG)
    ident = identifiant or f"essai-{role}-{rang}"
    return _inserer(ident, nom or f"Essai {NOMS[role]} {rang}", role, code or CODES[role], actif)


def oublier_les_essais(*cles: str) -> None:
    """Efface les essais de connexion comptés (toutes les clés si aucune n'est donnée)."""
    with fabrique_de_sessions()() as s, s.begin():
        requete = delete(Tentative)
        if cles:
            requete = requete.where(Tentative.identifiant.in_(cles))
        s.execute(requete)


def connecter(
    app: FastAPI, identifiant: str, code: str, *, local: bool = False, entete: bool = True
) -> TestClient:
    """Un client connecté par `POST /api/connexion` (essais de l'identifiant oubliés avant)."""
    oublier_les_essais(identifiant.lower(), sessions.cle_adresse(POSTE_LOCAL[0]))
    options = {"client": POSTE_LOCAL} if local else {}
    client = TestClient(app, headers=ENTETE_ECRAN if entete else None, **options)
    r = client.post("/api/connexion", json={"identifiant": identifiant, "code": code})
    assert r.status_code == 200, r.text
    return client


def _session_en_base(jeton: str) -> bool:
    """La session de ce jeton existe-t-elle encore (base remigrée, sessions fermées) ?"""
    with fabrique_de_sessions()() as s:
        ouverte = s.get(SessionOuverte, sessions.empreinte(jeton))
        return ouverte is not None and ouverte.expire_le > horloge.maintenant()


def client_de(app: FastAPI, role: str) -> TestClient:
    """Le client connecté d'un compte de base (session gardée tant qu'elle vit en base)."""
    assurer_comptes()
    jeton = _JETONS.get(role)
    if jeton is not None and _session_en_base(jeton):
        client = TestClient(app, headers=ENTETE_ECRAN)
        client.cookies.set(COOKIE_SESSION, jeton)
        return client
    client = connecter(app, role, CODES[role])
    _JETONS[role] = str(client.cookies.get(COOKIE_SESSION))
    return client


@pytest.fixture
def comptes() -> dict[str, int]:
    """Les ids des quatre comptes de base."""
    return assurer_comptes()


@pytest.fixture
def direction(application: FastAPI) -> TestClient:
    """Un poste de la direction, connecté."""
    return client_de(application, Role.direction)


@pytest.fixture
def achats(application: FastAPI) -> TestClient:
    """Un poste des achats, connecté."""
    return client_de(application, Role.achats)


@pytest.fixture
def alimentation(application: FastAPI) -> TestClient:
    """Un téléphone de l'alimentation, connecté."""
    return client_de(application, Role.alimentation)


@pytest.fixture
def administrateur(application: FastAPI) -> TestClient:
    """Un poste de l'administrateur technique, connecté."""
    return client_de(application, Role.administrateur)


@pytest.fixture
def anonyme(application: FastAPI) -> Iterator[TestClient]:
    """Un poste de l'écran sans session (en-tête présent)."""
    yield TestClient(application, headers=ENTETE_ECRAN)
