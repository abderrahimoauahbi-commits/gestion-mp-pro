"""Socle des essais : base d'essai seulement, horloge fixe, schéma recréé, clients (lot S0).

- Garde-fou : la base doit finir par `_essai` (défaut `gestion_mp_pro_essai`, ou
  `GESTIONMPPRO_BASE_ESSAI`) ; sinon les essais s'arrêtent avant toute connexion.
- Horloge figée au 8 octobre 2026, 10 h à l'usine (LOTS § 0 n° 5), remise à chaque essai.
- Schéma : `public` vidé une fois, puis `services.installation.migrer()` (Alembic, lot S1) s'il
  existe ; sans lui, le schéma reste vide. Aucun fichier de S0 à changer quand S1 arrive.
- `client` : un poste qui envoie l'en-tête de l'écran ; `client_brut` : sans en-tête.
- Dossiers (G-03) : sauvegardes et pièces jointes de **toute la séance** dans un dossier
  temporaire (`DOSSIER_DES_ESSAIS`, effacé à la fin), copie de sécurité non réglée : aucun essai
  n'écrit dans `~/gestion-mp-pro-sauvegardes` ni `~/gestion-mp-pro-pieces`. Un essai qui veut ses
  propres dossiers les pose lui-même (`fabriques.exploitation.dossiers`).
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

BASE_ESSAI = os.environ.get("GESTIONMPPRO_BASE_ESSAI", "postgresql+psycopg:///gestion_mp_pro_essai")
_nom = make_url(BASE_ESSAI).database or ""
if not _nom.endswith("_essai"):
    pytest.exit(f"Base d'essai refusée : « {_nom} » ne finit pas par _essai.", returncode=3)
os.environ["GESTIONMPPRO_BASE"] = BASE_ESSAI
os.environ["GESTIONMPPRO_TACHES"] = "0"
DOSSIER_DES_ESSAIS = Path(tempfile.mkdtemp(prefix="gestion-mp-pro-essais-"))
atexit.register(shutil.rmtree, DOSSIER_DES_ESSAIS, ignore_errors=True)
os.environ["GESTIONMPPRO_SAUVEGARDES"] = str(DOSSIER_DES_ESSAIS / "sauvegardes")
os.environ["GESTIONMPPRO_PIECES"] = str(DOSSIER_DES_ESSAIS / "pieces")
os.environ.pop("GESTIONMPPRO_SAUVEGARDES_COPIE", None)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from gestion_mp_pro import config  # noqa: E402
from gestion_mp_pro.db import DISPONIBILITE, moteur  # noqa: E402
from gestion_mp_pro.services import horloge  # noqa: E402

config.reglages.cache_clear()
assert config.reglages().nom_base.endswith("_essai")
assert config.reglages().sauvegardes.is_relative_to(DOSSIER_DES_ESSAIS)

JOUR_DES_ESSAIS = datetime(2026, 10, 8, 10, 0, tzinfo=horloge.FUSEAU)
ENTETE_ECRAN = {config.ENTETE_ANTI_FALSIFICATION: "1"}


def preparer_schema() -> None:
    """Vide `public` puis migre (S1) ; crochet unique pour les lots suivants."""
    with moteur().begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    if find_spec("gestion_mp_pro.services.installation") is not None:
        installation = import_module("gestion_mp_pro.services.installation")
        migrer = getattr(installation, "migrer", None)
        if callable(migrer):
            migrer()


@pytest.fixture(scope="session", autouse=True)
def schema() -> None:
    """Le schéma de la base d'essai, recréé une fois par lancement."""
    preparer_schema()


@pytest.fixture(autouse=True)
def horloge_fixe() -> Iterator[datetime]:
    """Chaque essai commence le 8 octobre 2026 à 10 h (heure de l'usine)."""
    horloge.fixer(JOUR_DES_ESSAIS)
    DISPONIBILITE.schema_en_retard = False
    yield JOUR_DES_ESSAIS
    horloge.fixer(JOUR_DES_ESSAIS)


@pytest.fixture(scope="session")
def application(schema: None) -> FastAPI:
    """L'application telle que servie (cycle de vie compris)."""
    from gestion_mp_pro.main import creer_application

    return creer_application()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    """Un poste de l'écran : chaque requête porte l'en-tête anti-falsification."""
    with TestClient(application, headers=ENTETE_ECRAN) as c:
        yield c


@pytest.fixture
def client_brut(application: FastAPI) -> Iterator[TestClient]:
    """Un client sans l'en-tête de l'écran (page d'un autre site, outil en ligne de commande)."""
    with TestClient(application) as c:
        yield c
