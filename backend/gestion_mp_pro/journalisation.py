"""Journal du serveur (`logging`) et middleware `trace` (ARCHITECTURE C17, § 4, § 13.4).

Une ligne par requête :
`requete=3f9c0a1b2c3d4e5f utilisateur=nadia role=achats POST /api/receptions/42/valider 200 38 ms`.
Vers la sortie standard (Docker, systemd) ou un fichier tournant (`GESTIONMPPRO_JOURNAL_FICHIER`,
poste Mac), au niveau `GESTIONMPPRO_JOURNAL_NIVEAU`, horodaté à l'heure de l'usine. Le
middleware pose aussi les en-têtes communs (`X-Requete`, `X-Heure-Serveur`, `Cache-Control`,
en-têtes de sécurité), y compris sur les refus des autres middlewares et sur un 500 imprévu.
"""

from __future__ import annotations

import logging
import secrets
import sys
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from logging.handlers import RotatingFileHandler

from starlette.requests import Request
from starlette.responses import Response

from gestion_mp_pro.api.erreurs import reponse_erreur_serveur
from gestion_mp_pro.config import Reglages
from gestion_mp_pro.services import horloge

JOURNAL = logging.getLogger("gestion_mp_pro")
JOURNAL_REQUETES = logging.getLogger("gestion_mp_pro.requetes")
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
TAILLE_FICHIER = 10 * 1024 * 1024
FICHIERS_GARDES = 10

ENTETES_SECURITE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}
CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
    "frame-ancestors 'none'"
)
SANS_CSP = ("/api/docs",)
"""La documentation Swagger charge ses scripts ailleurs : pas de CSP sur elle seule."""

Suite = Callable[[Request], Awaitable[Response]]


class FormatUsine(logging.Formatter):
    """Horodatage à l'heure de l'usine, sans toucher au fuseau du processus."""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """`2026-10-08 14:03:12,345` à l'heure de l'usine."""
        instant = datetime.fromtimestamp(record.created, horloge.FUSEAU)
        if datefmt:
            return instant.strftime(datefmt)
        return f"{instant:%Y-%m-%d %H:%M:%S},{int(record.msecs):03d}"


def configurer(r: Reglages) -> None:
    """Configure le journal du paquet (idempotent : rappeler remplace le gestionnaire)."""
    for ancien in [h for h in JOURNAL.handlers if getattr(h, "gestion_mp_pro", False)]:
        JOURNAL.removeHandler(ancien)
        ancien.close()
    gestionnaire: logging.Handler
    if r.journal_fichier is not None:
        r.journal_fichier.parent.mkdir(parents=True, exist_ok=True)
        gestionnaire = RotatingFileHandler(
            r.journal_fichier,
            maxBytes=TAILLE_FICHIER,
            backupCount=FICHIERS_GARDES,
            encoding="utf-8",
        )
    else:
        gestionnaire = logging.StreamHandler(sys.stdout)
    gestionnaire.setFormatter(FormatUsine(FORMAT))
    gestionnaire.gestion_mp_pro = True  # type: ignore[attr-defined]
    JOURNAL.addHandler(gestionnaire)
    JOURNAL.setLevel(r.journal_niveau)


def nouvel_identifiant() -> str:
    """Identifiant de requête : 16 caractères hexadécimaux."""
    return secrets.token_hex(8)


def reference_courte(identifiant: str) -> str:
    """La référence dite à l'utilisateur dans un 500 : les 8 premiers caractères."""
    return identifiant[:8]


def _qui(requete: Request) -> tuple[str, str]:
    """Identifiant et rôle de l'acteur posé par `securite` (lot S2) dans `requete.state`."""
    acteur = getattr(requete.state, "acteur", None)
    if acteur is None:
        return "-", "-"
    return str(getattr(acteur, "identifiant", "-")), str(getattr(acteur, "role", "-"))


def poser_entetes(requete: Request, reponse: Response, identifiant: str) -> None:
    """En-têtes communs à toute réponse, et ceux propres à l'API."""
    chemin = requete.url.path
    for nom, valeur in ENTETES_SECURITE.items():
        reponse.headers.setdefault(nom, valeur)
    if not chemin.startswith(SANS_CSP):
        reponse.headers.setdefault("Content-Security-Policy", CSP)
    reponse.headers["X-Requete"] = identifiant
    if chemin == "/api" or chemin.startswith("/api/"):
        reponse.headers.setdefault("Cache-Control", "no-store")
        # L'heure de l'usine avec son décalage (2026-10-08T13:20:46+01:00) : l'écran l'affiche
        # plutôt que celle du poste, et en tire « aujourd'hui » (lot E0).
        reponse.headers["X-Heure-Serveur"] = horloge.maintenant().isoformat(timespec="seconds")


async def trace(requete: Request, suite: Suite) -> Response:
    """Middleware le plus extérieur : identifiant, chronomètre, 500 tracé, en-têtes, journal."""
    identifiant = nouvel_identifiant()
    requete.state.requete = identifiant
    debut = time.perf_counter()
    try:
        reponse = await suite(requete)
    except Exception:
        reference = reference_courte(identifiant)
        JOURNAL.exception(
            "requete=%s ref=%s erreur imprévue sur %s %s",
            identifiant,
            reference,
            requete.method,
            requete.url.path,
        )
        reponse = reponse_erreur_serveur(reference)
    poser_entetes(requete, reponse, identifiant)
    duree = (time.perf_counter() - debut) * 1000
    utilisateur, role = _qui(requete)
    JOURNAL_REQUETES.info(
        "requete=%s utilisateur=%s role=%s %s %s %d %.0f ms",
        identifiant,
        utilisateur,
        role,
        requete.method,
        requete.url.path,
        reponse.status_code,
        duree,
    )
    return reponse
