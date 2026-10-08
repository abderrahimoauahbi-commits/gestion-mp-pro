"""Installation de la base : migration Alembic sous verrou, état du schéma, semences (§ 9).

- `migrer()` applique les révisions manquantes dans **une** transaction qui tient le verrou
  consultatif MIGRATION : plusieurs processus qui démarrent ensemble attendent leur tour, un
  seul applique, les autres trouvent la base à jour (essai à deux processus).
- `schema_en_retard()` : la base n'est pas à la révision attendue (l'API répond alors 503).
- `semences_manquantes()` : ce que la révision 0002 aurait dû semer et qui manque.

Appelé par le démarrage (`main._mettre_le_schema_a_jour`), par les essais (`conftest`) et,
après sa restauration, par la sauvegarde (D10).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, func, select
from sqlalchemy.exc import SQLAlchemyError

from gestion_mp_pro import modeles as m
from gestion_mp_pro.db import Verrou, moteur, verrouiller
from gestion_mp_pro.modeles.enums import TypeMagasin

JOURNAL = logging.getLogger("gestion_mp_pro.installation")

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
"""Le dossier des migrations, dans le paquet (aucun `alembic.ini` nécessaire au serveur)."""

SEMENCES = {"roles": 8, "postes": 11, "motifs": 16}
"""Ce que sème la révision 0002 (et les 57 réglages de `modeles.CLES_REGLAGES`, 0002 et 0003)."""


def configuration() -> Config:
    """La configuration Alembic du paquet, construite sans fichier."""
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS))
    return cfg


@lru_cache(maxsize=1)
def revision_attendue() -> str:
    """La tête des révisions livrées avec ce code (`0002`…)."""
    tete = ScriptDirectory.from_config(configuration()).get_current_head()
    if tete is None:
        raise RuntimeError("aucune révision Alembic livrée")
    return tete


def revision_de(c: Connection) -> str | None:
    """La révision où en est la base (`None` : base vide)."""
    return MigrationContext.configure(c).get_current_revision()


def revision_courante() -> str | None:
    """La révision où en est la base de ce serveur."""
    with moteur().connect() as c:
        return revision_de(c)


def _appliquees(avant: str | None, apres: str | None) -> list[str]:
    """Les révisions appliquées entre deux états, dans l'ordre d'application."""
    if apres is None or apres == avant:
        return []
    script = ScriptDirectory.from_config(configuration())
    faites = [r.revision for r in script.iterate_revisions(apres, avant)]
    return sorted(faites)


def migrer() -> list[str]:
    """Met la base à la révision attendue, sous le verrou MIGRATION ; rend ce qui a été appliqué."""
    cfg = configuration()
    with moteur().connect() as c, c.begin():
        verrouiller(c, Verrou.MIGRATION)
        avant = revision_de(c)
        cfg.attributes["connection"] = c
        command.upgrade(cfg, "head")
        apres = revision_de(c)
    appliquees = _appliquees(avant, apres)
    if appliquees:
        JOURNAL.info("Base migrée : %s → %s (%s).", avant or "vide", apres, ", ".join(appliquees))
    return appliquees


def schema_en_retard() -> bool:
    """Vrai si la base n'est pas à la révision attendue (ou ne répond pas)."""
    try:
        courante = revision_courante()
    except SQLAlchemyError:
        JOURNAL.exception("Révision de la base illisible.")
        return True
    return courante != revision_attendue()


def semences_manquantes(c: Connection) -> list[str]:
    """Les semences absentes de la base (liste vide : tout est là)."""
    manque: list[str] = []
    roles = c.scalar(select(func.count()).where(m.RoleNomenclature.de_base))
    if roles != SEMENCES["roles"]:
        manque.append(f"rôles de nomenclature de base : {roles} sur {SEMENCES['roles']}")
    postes = c.scalar(select(func.count()).where(m.PosteFrais.systeme))
    if not postes:
        manque.append("postes de frais système")
    if c.scalar(select(func.count()).select_from(m.Motif)) != SEMENCES["motifs"]:
        manque.append("motifs de mouvement")
    if c.scalar(select(m.Devise.cours).where(m.Devise.code == "MAD")) is None:
        manque.append("devise MAD")
    for genre in TypeMagasin:
        present = select(m.Magasin.id).where(m.Magasin.type == genre, m.Magasin.actif)
        if c.scalar(present.limit(1)) is None:
            manque.append(f"magasin {genre.value} actif")
    cles = set(c.scalars(select(m.Parametre.cle)))
    absentes = [cle for cle in m.CLES_REGLAGES if cle not in cles]
    if absentes:
        manque.append("réglages : " + ", ".join(absentes))
    return manque
