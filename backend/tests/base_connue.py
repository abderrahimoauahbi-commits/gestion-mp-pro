"""Une base remise à un état connu : celle d'une installation neuve, comptes gardés (RESTES3).

Les essais partagent la base de la séance ; un essai qui compte « toute la base » (le monde de
S1, la période close, le courriel du lundi, les semences, le chargeur du moteur) ne doit pas
dépendre de ce que les autres ont laissé, dans quelque ordre qu'ils passent.

- `photographier(c)` : appelée une fois, juste après la migration (`conftest.schema`), garde les
  lignes des tables semées (réglages, devises, rôles, postes de frais, magasins, motifs).
- `remettre(c)` : vide **toutes** les tables sauf les comptes (utilisateurs, sessions,
  appareils, tentatives : les postes connectés de la séance restent connectés) et réécrit les
  semences telles que photographiées — réglages à leur défaut compris. Dans une transaction
  annulée à la fin de l'essai (monde de S1, `fabriques.pilotage.usine`), personne d'autre ne
  voit rien ; validée (`remettre_et_valider`, fixture `base_neuve`), elle sert les essais dont
  le code ouvre ses propres sessions (tâches de fond).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text

COMPTES = frozenset({"alembic_version", "utilisateur", "session", "appareil", "tentative"})
"""Tables gardées telles quelles : comptes et sessions (elles ne citent qu'elles-mêmes)."""
SEMEES = (
    "parametre", "devise", "devise_cours", "role_nomenclature", "poste_frais", "magasin", "motif",
)  # fmt: skip
"""Tables semées à l'installation, dans l'ordre de leurs dépendances."""

_PHOTO: dict[str, list[dict[str, Any]]] = {}


def photographier(c: Connection) -> None:
    """Garde les lignes des tables semées (base tout juste migrée)."""
    _PHOTO.clear()
    for table in SEMEES:
        lignes = c.execute(text(f"SELECT * FROM {table} ORDER BY 1")).mappings().all()  # noqa: S608
        _PHOTO[table] = [dict(x) for x in lignes]


def _tables(c: Connection) -> list[str]:
    """Les tables du schéma, comptes exceptés."""
    noms = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
    return sorted(t for t in noms if t not in COMPTES)


def remettre(c: Connection) -> None:
    """La base d'une installation neuve (comptes gardés), dans la transaction de `c`."""
    if not _PHOTO:
        raise RuntimeError("Semences non photographiées : conftest.schema doit passer d'abord.")
    c.execute(text("TRUNCATE " + ", ".join(f'"{t}"' for t in _tables(c)) + " CASCADE"))
    for table in SEMEES:
        lignes = _PHOTO[table]
        if not lignes:
            continue
        colonnes = list(lignes[0])
        sql = (
            f"INSERT INTO {table} ({', '.join(colonnes)}) "  # noqa: S608
            f"VALUES ({', '.join(':' + k for k in colonnes)})"
        )
        c.execute(text(sql), lignes)


def remettre_et_valider() -> None:
    """La base d'une installation neuve, validée (vue de toutes les sessions)."""
    from gestion_mp_pro.db import moteur
    from gestion_mp_pro.services import donnees_moteur

    with moteur().begin() as c:
        remettre(c)
    donnees_moteur.invalider()
