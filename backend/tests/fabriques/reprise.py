"""Fabriques de la reprise (lot R1) : une base « Gestion MP » d'essai, une cible PRO migrée.

- `creer_base(url)` : base neuve (supprimée d'abord si elle existe) ;
- `source_gestion_mp(url)` : le schéma de Gestion MP corrigé (étapes 1–19), figé dans
  `tests/donnees/gestion_mp_schema.sql` (`pg_dump --schema-only` d'une copie de `gestion_mp`) ;
- `PETITE_USINE` : une petite usine qui exerce chaque traduction de la reprise (une ligne de
  chaque sorte : prix sur une sortie, cours 0, LOT INTERNE, brouillon numéroté, deux devises
  sur une réception, numéro de lot avec blanc, plan au journal, bon soldé à la main…) ;
- `cible_migree(url)` : une base PRO à `head`.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from gestion_mp_pro.services import comptes
from gestion_mp_pro.services.installation import configuration

SCHEMA = Path(__file__).resolve().parents[1] / "donnees" / "gestion_mp_schema.sql"
CODE_DIRECTION = "direction-1"
EMPREINTE = comptes.hacher(CODE_DIRECTION)


def creer_base(url: str) -> None:
    """Supprime puis recrée la base (connexion à la base `postgres` du même serveur)."""
    nom = make_url(url).database
    assert nom and nom.startswith("gestion_mp_pro_") and nom.endswith("_essai")
    maintenance = make_url(url).set(database="postgres")
    moteur = create_engine(maintenance, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    with moteur.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{nom}"'))
    moteur.dispose()


def supprimer_base(url: str) -> None:
    """Supprime la base d'essai."""
    nom = make_url(url).database
    maintenance = make_url(url).set(database="postgres")
    moteur = create_engine(maintenance, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    with moteur.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
    moteur.dispose()


def executer_sql(url: str, sql: str) -> None:
    """Exécute un texte SQL (plusieurs instructions) dans une transaction."""
    moteur = create_engine(url, poolclass=NullPool)
    with moteur.connect() as c, c.begin():
        c.exec_driver_sql(sql)
    moteur.dispose()


def source_gestion_mp(url: str, donnees: str) -> None:
    """Une base au schéma de Gestion MP corrigé, remplie de `donnees` (SQL)."""
    creer_base(url)
    schema = "\n".join(x for x in SCHEMA.read_text().splitlines() if not x.startswith("\\"))
    executer_sql(url, schema)
    etapes = [n for n in range(1, 20) if n not in (10, 12)]
    valeurs = ", ".join(f"({n}, 'étape {n}', now())" for n in etapes)
    executer_sql(url, f"INSERT INTO schema_version VALUES {valeurs};\n{donnees}")  # noqa: S608


def cible_migree(url: str) -> None:
    """Une base PRO neuve, migrée à `head` (semences comprises)."""
    creer_base(url)
    moteur = create_engine(url, poolclass=NullPool)
    with moteur.connect() as c, c.begin():
        cfg = configuration()
        cfg.attributes["connection"] = c
        command.upgrade(cfg, "head")
    moteur.dispose()


PETITE_USINE = (
    (Path(__file__).resolve().parents[1] / "donnees" / "petite_usine.sql")
    .read_text(encoding="utf-8")
    .replace("@@EMPREINTE@@", EMPREINTE)
)
"""La petite usine de Gestion MP (une ligne de chaque sorte), `tests/donnees/petite_usine.sql`."""

FICHIERS = {"article/1/fiche.pdf": b"%PDF1", "commande/1/proforma.pdf": b"%PDF2"}
"""Les fichiers des pièces jointes (la 3ᵉ manque : signalée)."""
