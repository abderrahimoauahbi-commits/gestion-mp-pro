"""Vider l'activité d'une base PRO en gardant **intacts** tous les référentiels.

Leçon de G-01 (Gestion MP : « vider l'activité » échouait sur les clés étrangères, la mise en
service était impossible) : toutes les tables d'activité partent **ensemble**, dans un seul
`TRUNCATE` sans `CASCADE` (rien d'autre ne part en silence). La liste vient des modèles
(`modeles.tables_d_activite()`, marqueur `__activite__`, incohérence 32) : une table ajoutée
plus tard est vidée sans retoucher ce code.

`piece_jointe` porte des clés vers des documents d'activité : PostgreSQL exige qu'elle soit
dans le même `TRUNCATE`. Les pièces des référentiels (matières, fournisseurs) sont donc lues
avant et réécrites à l'identique après ; les fichiers ne sont jamais effacés. Les identifiants
ne repartent pas à 1 (pas de `RESTART IDENTITY`) : le journal garde la trace des documents
vidés par leur identifiant, un nouveau document ne doit pas hériter de leur histoire.

L'empreinte de chaque référentiel est prise avant et après : si une seule ligne a bougé, tout
est annulé (`ReferentielModifie`).
"""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import Connection, insert, select, text

from gestion_mp_pro.modeles import metadata, tables_d_activite

OBJETS_REFERENTIELS = ("fournisseur", "matiere")
"""Pièces jointes gardées : celles des fiches de référentiel."""

GARDEES = frozenset(
    {
        "journal",
        "session",
        "tentative",
        "appareil",
        "sauvegarde",
        "tache_execution",
        "courriel",
        "reprise_correspondance",
        "reprise_execution",
        "alembic_version",
        "piece_jointe",
    }
)
"""Tables ni activité ni référentiel : gardées sans empreinte (elles vivent pendant le vidage)."""


class ReferentielModifie(Exception):
    """Un référentiel aurait changé pendant le vidage : la transaction est annulée."""


def referentiels() -> list[str]:
    """Les tables de référentiel : toutes celles qui ne sont ni activité ni gardées."""
    activite = set(tables_d_activite())
    return sorted(t for t in metadata.tables if t not in activite and t not in GARDEES)


def empreintes(c: Connection) -> dict[str, str]:
    """Une empreinte par référentiel (lignes en texte, triées), pièces des fiches comprises."""
    requetes = {t: f"SELECT x::text FROM {t} x ORDER BY 1" for t in referentiels()}  # noqa: S608
    objets = ", ".join(f"'{o}'" for o in OBJETS_REFERENTIELS)
    requetes["piece_jointe (référentiels)"] = (
        f"SELECT x::text FROM piece_jointe x WHERE objet IN ({objets}) ORDER BY 1"  # noqa: S608
    )
    return {
        nom: hashlib.sha256("\n".join(c.execute(text(sql)).scalars()).encode()).hexdigest()
        for nom, sql in requetes.items()
    }


def vider(c: Connection) -> dict[str, int]:
    """Vide l'activité dans la transaction de `c` ; rend le nombre de lignes retirées par table."""
    avant = empreintes(c)
    comptes = {
        t: int(c.execute(text(f"SELECT count(*) FROM {t}")).scalar() or 0)  # noqa: S608
        for t in tables_d_activite()
    }
    table_pieces = metadata.tables["piece_jointe"]
    gardees: list[dict[str, Any]] = [
        dict(r._mapping)
        for r in c.execute(
            select(table_pieces).where(table_pieces.c.objet.in_(OBJETS_REFERENTIELS))
        )
    ]
    comptes["piece_jointe"] = int(
        c.execute(text("SELECT count(*) FROM piece_jointe")).scalar() or 0
    )
    comptes["piece_jointe"] -= len(gardees)
    c.execute(text(f"TRUNCATE {', '.join([*tables_d_activite(), 'piece_jointe'])}"))
    if gardees:
        c.execute(insert(table_pieces), gardees)
    if empreintes(c) != avant:
        raise ReferentielModifie("un référentiel aurait bougé : rien n'est fait")
    return comptes
