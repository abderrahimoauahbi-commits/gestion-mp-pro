"""L'application : cycle de vie, middlewares, routeurs, écran (ARCHITECTURE § 4, § 13).

Lancement : `uvicorn gestion_mp_pro.main:app --host 127.0.0.1 --port 8050 --no-access-log`
(le journal d'une ligne par requête est celui de `journalisation.trace`).

Crochets des lots suivants, appelés s'ils existent (aucun fichier de S0 à modifier) :
- `services.installation.migrer()` (S1) au démarrage, sous le verrou MIGRATION ; un échec
  laisse le serveur debout mais l'API répond 503 `schema_en_retard` ;
  `services.installation.schema_en_retard() -> bool` (S1) s'il existe, après la migration ;
- `taches.planificateur.demarrer()` / `arreter()` (D10) si `GESTIONMPPRO_TACHES=1`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from gestion_mp_pro import __version__, journalisation
from gestion_mp_pro.api import etiquettes_openapi, routeurs
from gestion_mp_pro.api.erreurs import (
    MESSAGE_ROUTE_INCONNUE,
    MESSAGES_INDISPONIBLE,
    installer_gestionnaires,
    reponse_erreur,
)
from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION, Reglages, reglages
from gestion_mp_pro.db import DISPONIBILITE, motif_indisponibilite

JOURNAL = journalisation.JOURNAL

SANS_ENTETE = frozenset({"/api/connexion", "/api/installation", "/api/appareils/enroler"})
"""Écritures permises sans l'en-tête anti-falsification (API-PRO § 0.5) ; pas `/deconnexion`."""

TOUJOURS_DISPONIBLES = frozenset({"/api/sante", "/api/etat", "/api/docs", "/api/openapi.json"})
"""Ce qui répond même quand la base est en retard ou en restauration."""

LECTURES = frozenset({"GET", "HEAD", "OPTIONS"})
MESSAGE_ENTETE = "Requête refusée : elle ne vient pas de l'écran de Gestion MP PRO."
SANS_CACHE = frozenset({"index.html", "sw.js", "manifest.webmanifest"})


def _crochet(module: str, nom: str) -> Callable[[], object] | None:
    """La fonction `nom` du module s'il existe (lot pas encore livré : `None`)."""
    complet = f"gestion_mp_pro.{module}"
    try:
        if find_spec(complet) is None:
            return None
    except ModuleNotFoundError:  # paquet parent absent
        return None
    fonction = getattr(import_module(complet), nom, None)
    return fonction if callable(fonction) else None


def _mettre_le_schema_a_jour() -> None:
    """Migre la base (S1) ; un échec est journalisé et rend l'API indisponible (503)."""
    migrer = _crochet("services.installation", "migrer")
    if migrer is not None:
        try:
            migrer()
        except Exception:
            JOURNAL.exception("La migration de la base a échoué : l'API répond 503.")
            DISPONIBILITE.schema_en_retard = True
            return
    en_retard = _crochet("services.installation", "schema_en_retard")
    DISPONIBILITE.schema_en_retard = bool(en_retard()) if en_retard is not None else False
    if DISPONIBILITE.schema_en_retard:
        JOURNAL.error("La base n'est pas à la révision attendue : l'API répond 503.")


@asynccontextmanager
async def _vie(app: FastAPI) -> AsyncIterator[None]:
    """Démarrage : journal, schéma, tâches ; arrêt : tâches."""
    r: Reglages = app.state.reglages
    journalisation.configurer(r)
    await run_in_threadpool(_mettre_le_schema_a_jour)
    arreter = None
    if r.taches:
        demarrer = _crochet("taches.planificateur", "demarrer")
        arreter = _crochet("taches.planificateur", "arreter")
        if demarrer is not None:
            demarrer()
    JOURNAL.info("Gestion MP PRO %s prêt (base %s, port %s).", __version__, r.nom_base, r.port)
    try:
        yield
    finally:
        if arreter is not None:
            arreter()


def _est_api(chemin: str) -> bool:
    """Le chemin est-il sous `/api` ?"""
    return chemin == "/api" or chemin.startswith("/api/")


async def protections(requete: Request, suite: journalisation.Suite) -> Response:
    """Anti-falsification sur toute écriture de l'API, puis 503 si la base n'est pas prête."""
    chemin = requete.url.path
    if not _est_api(chemin):
        return await suite(requete)
    if (
        requete.method not in LECTURES
        and chemin not in SANS_ENTETE
        and requete.headers.get(ENTETE_ANTI_FALSIFICATION) != "1"
    ):
        return reponse_erreur("entete_absente", MESSAGE_ENTETE)
    if chemin not in TOUJOURS_DISPONIBLES:
        motif = await run_in_threadpool(motif_indisponibilite)
        if motif is not None:
            return reponse_erreur(motif, MESSAGES_INDISPONIBLE[motif])
    return await suite(requete)


def _servir_ecran(app: FastAPI, dossier: Path) -> None:
    """L'écran construit (poste Mac, hors Docker+Caddy) : fichiers, sinon `index.html`."""
    if not (dossier / "index.html").is_file():
        return
    racine = dossier.resolve()
    if (racine / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=racine / "assets"), name="assets")

    @app.get("/{chemin:path}", include_in_schema=False)
    def ecran(chemin: str) -> Response:
        """Un fichier de l'écran s'il existe sous son dossier, sinon l'application (SPA)."""
        if _est_api("/" + chemin):
            return reponse_erreur("route_inconnue", MESSAGE_ROUTE_INCONNUE)
        fichier = (racine / chemin).resolve()
        if chemin and fichier.is_file() and fichier.is_relative_to(racine):
            entetes = {"Cache-Control": "no-cache"} if fichier.name in SANS_CACHE else None
            return FileResponse(fichier, headers=entetes)
        return FileResponse(racine / "index.html", headers={"Cache-Control": "no-cache"})


def creer_application(
    r: Reglages | None = None, routeurs_en_plus: Sequence[APIRouter] = ()
) -> FastAPI:
    """Construit l'application ; `routeurs_en_plus` sert aux essais (routes d'épreuve)."""
    r = r or reglages()
    app = FastAPI(
        title="Gestion MP PRO",
        version=__version__,
        description="Matières premières d'une usine de tapis : achats, réceptions, "
        "importations, stock, alimentation des machines, pilotage.",
        lifespan=_vie,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        openapi_tags=etiquettes_openapi(),
    )
    app.state.reglages = r
    installer_gestionnaires(app)
    for routeur in (*routeurs(), *routeurs_en_plus):
        app.include_router(routeur, prefix="/api")
    app.add_middleware(BaseHTTPMiddleware, dispatch=protections)
    app.add_middleware(BaseHTTPMiddleware, dispatch=journalisation.trace)  # le plus extérieur
    _servir_ecran(app, r.ecran)
    return app


app = creer_application()
