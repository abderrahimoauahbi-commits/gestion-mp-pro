"""Environnement Alembic de Gestion MP PRO (MODELE-DONNEES § 9).

- Cible : `gestion_mp_pro.modeles.metadata` (toutes les tables). Les **révisions**, elles,
  n'importent jamais le paquet (essai `test_migrations`) : leur DDL est écrit en clair.
- Base : `-x base=<url>` ; sinon `GESTIONMPPRO_BASE` (lue par `config.Reglages`) ; sinon, pour
  `alembic check` seulement, `base_de_controle` d'`alembic.ini` (la base d'essai que pytest
  vient de migrer) ; sinon la base par défaut de `config`.
- `services.installation.migrer()` passe sa propre connexion (`config.attributes["connection"]`),
  déjà dans une transaction tenant le verrou MIGRATION : Alembic migre dans cette transaction.
- `alembic revision` numérote la nouvelle révision à la suite de la tête : `0003`, `0004`…
"""

from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, create_engine

from gestion_mp_pro import config as configuration
from gestion_mp_pro import modeles

CONFIG = context.config
CIBLE = modeles.metadata


def _commande() -> str:
    """Le nom de la commande Alembic lancée en ligne de commande (vide sinon)."""
    options = getattr(CONFIG.cmd_opts, "cmd", None)
    return getattr(options[0], "__name__", "") if options else ""


def adresse() -> str:
    """L'adresse de la base à migrer (ordre : `-x base`, environnement, contrôle, défaut)."""
    arguments = context.get_x_argument(as_dictionary=True)
    if arguments.get("base"):
        return str(arguments["base"])
    reglages = configuration.reglages()
    if "base" in reglages.model_fields_set:
        return reglages.base
    if _commande() == "check" and CONFIG.file_config.has_section("gestion_mp_pro"):
        controle = CONFIG.get_section_option("gestion_mp_pro", "base_de_controle")
        if controle:
            return controle
    return reglages.base


def _numeroter(contexte: Any, _revision: Any, directives: list[Any]) -> None:
    """Une nouvelle révision prend le numéro qui suit la tête (identifiants contigus)."""
    if not directives:
        return
    tete = ScriptDirectory.from_config(contexte.config).get_current_head()
    directives[0].rev_id = f"{int(tete or 0) + 1:04d}"


def _options() -> dict[str, Any]:
    """Options communes de comparaison et de génération."""
    return {
        "target_metadata": CIBLE,
        "compare_type": True,
        "compare_server_default": True,
        "process_revision_directives": _numeroter,
    }


def _migrer(connexion: Connection) -> None:
    """Migre sur une connexion (dans sa transaction si elle en a une)."""
    context.configure(connection=connexion, **_options())
    with context.begin_transaction():
        context.run_migrations()


def en_ligne() -> None:
    """Migration sur la base (connexion fournie par `migrer()`, ou ouverte ici)."""
    fournie = CONFIG.attributes.get("connection")
    if fournie is not None:
        _migrer(fournie)
        return
    moteur = create_engine(adresse())
    try:
        with moteur.connect() as connexion:
            _migrer(connexion)
            connexion.commit()
    finally:
        moteur.dispose()


def hors_ligne() -> None:
    """Écrit le SQL des migrations sans base (`alembic upgrade head --sql`)."""
    context.configure(url=adresse(), literal_binds=True, **_options())
    with context.begin_transaction():
        context.run_migrations()


if CONFIG.cmd_opts is not None and CONFIG.config_file_name is not None:
    fileConfig(CONFIG.config_file_name, disable_existing_loggers=False)

if context.is_offline_mode():
    hors_ligne()
else:
    en_ligne()
