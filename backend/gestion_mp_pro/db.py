"""Base de données : moteur, sessions, verrous nommés, disponibilité (ARCHITECTURE § 6).

- Une session par requête (`session`), `autoflush=False`, `expire_on_commit=False`, isolation
  READ COMMITTED : `commit` à la fin de la route, `rollback` sur toute exception (un refus
  annule tout le geste).
- Chaque connexion compte l'heure de l'usine (`-c timezone=…`) et coupe une requête de plus
  de 30 s (`statement_timeout`).
- Verrous consultatifs dans la plage 7426201–7426209, distincte de Gestion MP (7426101–7426110).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from gestion_mp_pro.config import reglages

DELAI_REQUETE_MS = 30_000
"""Une requête SQL plus longue est coupée par PostgreSQL."""


class Verrou(IntEnum):
    """Verrous consultatifs nommés (`db.VERROUS`), clés réservées 7426201–7426209."""

    MIGRATION = 7426201
    TACHES = 7426202
    ORDRES = 7426203
    INVENTAIRE_GLOBAL = 7426204
    RESTAURATION = 7426205
    REPRISE = 7426206


VERROUS = tuple(Verrou)
PLAGE_VERROUS = range(7426201, 7426210)


@lru_cache(maxsize=1)
def moteur() -> Engine:
    """Le moteur SQLAlchemy du processus (créé au premier appel)."""
    r = reglages()
    options = f"-c timezone={r.fuseau} -c statement_timeout={DELAI_REQUETE_MS}"
    return create_engine(
        r.base,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"options": options},
    )


@lru_cache(maxsize=1)
def fabrique() -> sessionmaker[Session]:
    """La fabrique de sessions (hors requête : tâches, outils, essais)."""
    return sessionmaker(bind=moteur(), autoflush=False, expire_on_commit=False)


def session() -> Iterator[Session]:
    """Dépendance FastAPI : une transaction par requête, validée si la route aboutit.

    À déclarer avec `scope="function"` (voir `api/dependances.SessionDep`) : le `commit` a lieu
    avant l'envoi de la réponse, et un échec du `commit` devient une réponse d'erreur.
    """
    s = fabrique()()
    try:
        yield s
        s.commit()
    except BaseException:
        s.rollback()
        raise
    finally:
        s.close()


def verrouiller(s: Session | Connection, verrou: Verrou) -> None:
    """Prend un verrou consultatif pour la transaction en cours (rendu au commit/rollback)."""
    s.execute(text("SELECT pg_advisory_xact_lock(:cle)"), {"cle": int(verrou)})


def essayer_verrou(c: Connection, verrou: Verrou) -> bool:
    """Tente un verrou consultatif de session (porteur unique des tâches) sans attendre."""
    obtenu = c.execute(text("SELECT pg_try_advisory_lock(:cle)"), {"cle": int(verrou)}).scalar()
    return bool(obtenu)


def liberer(c: Connection, verrou: Verrou) -> None:
    """Rend un verrou consultatif de session."""
    c.execute(text("SELECT pg_advisory_unlock(:cle)"), {"cle": int(verrou)})


_VERROU_TENU = text(
    "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND granted"
    " AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
    " AND classid = 0 AND objid = :cle AND objsubid = 1)"
)


def verrou_tenu(verrou: Verrou) -> bool:
    """Vrai si une session de cette base tient le verrou consultatif (lecture de `pg_locks`)."""
    with moteur().connect() as c:
        return bool(c.execute(_VERROU_TENU, {"cle": int(verrou)}).scalar())


@dataclass
class Disponibilite:
    """Ce qui rend l'API indisponible (503) : schéma en retard, restauration, base muette."""

    schema_en_retard: bool = False
    controle_le: float = 0.0
    motif_base: str | None = None


DISPONIBILITE = Disponibilite()
"""État du processus ; `schema_en_retard` est posé au démarrage (et par la restauration)."""

PERIODE_CONTROLE_S = 2.0
"""La base n'est interrogée sur une restauration en cours qu'une fois toutes les 2 s."""


def _motif_base() -> str | None:
    """Restauration en cours (verrou RESTAURATION tenu) ou base injoignable."""
    try:
        return "restauration_en_cours" if verrou_tenu(Verrou.RESTAURATION) else None
    except SQLAlchemyError:
        return "base_indisponible"


def motif_indisponibilite() -> str | None:
    """Le code du refus 503 à opposer à une requête de l'API, ou `None` si elle peut passer."""
    if DISPONIBILITE.schema_en_retard:
        return "schema_en_retard"
    instant = time.monotonic()
    if instant - DISPONIBILITE.controle_le >= PERIODE_CONTROLE_S:
        DISPONIBILITE.motif_base = _motif_base()
        DISPONIBILITE.controle_le = instant
    return DISPONIBILITE.motif_base
