"""Routes du domaine « Système ».

Lot S2 (routes 2–7) et D10 (route 1, santé) ; S0 a posé la première forme de `GET /sante`.
Routes minces : chemin, droits, schémas, `summary` ; un appel de service ; aucune règle métier
(ARCHITECTURE § 3.1).
"""

from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from gestion_mp_pro import __version__
from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.systeme.schemas import Sante
from gestion_mp_pro.config import RACINE
from gestion_mp_pro.db import DISPONIBILITE, moteur

routeur = nouveau_routeur("systeme")


def version_servie() -> str:
    """La version servie : le fichier VERSION de la copie figée (scripts/demarrer.sh), sinon
    la version du paquet suivie de « projet » (serveur lancé depuis le dépôt)."""
    fichier = RACINE / "VERSION"
    if fichier.is_file():
        return fichier.read_text(encoding="utf-8").strip() or __version__
    return f"{__version__} (projet)"


def _base_ms() -> float | None:
    """Temps d'un `SELECT 1`, en millisecondes ; `None` si la base ne répond pas."""
    debut = time.perf_counter()
    try:
        with moteur().connect() as c:
            c.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return None
    return round((time.perf_counter() - debut) * 1000, 1)


@routeur.get(
    "/sante",
    response_model=Sante,
    response_model_by_alias=True,
    summary="Santé du serveur pour la surveillance (public, sans donnée métier).",
)
def sante() -> Sante:
    """Route 1 : la base répond-elle, le schéma est-il à jour, quelle version est servie."""
    base_ms = _base_ms()
    etat = "ok" if base_ms is not None and not DISPONIBILITE.schema_en_retard else "degrade"
    return Sante(etat=etat, version=version_servie(), base_ms=base_ms)
