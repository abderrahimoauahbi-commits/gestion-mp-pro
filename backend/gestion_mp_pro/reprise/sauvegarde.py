"""Sauvegarde de la cible avant d'y écrire (« avant reprise », « base vide de référence »).

`pg_dump -Fc` de la base cible dans `<GESTIONMPPRO_SAUVEGARDES>/<base>/`, relue par
`pg_restore --list` (nombre de tables), inscrite au registre `sauvegarde`. Le service complet
des sauvegardes (rotation, copie externe, pièces) est au lot D10 ; la reprise et le vidage
n'ont besoin que de ce geste, qu'ils ne peuvent pas sauter (MODELE-DONNEES § 10.1).
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404 (outils PostgreSQL, arguments en liste)
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Connection, insert
from sqlalchemy.engine import make_url

from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import GenreSauvegarde
from gestion_mp_pro.services import horloge


class SauvegardeImpossible(Exception):
    """`pg_dump` absent ou en échec : rien n'est écrit dans la cible."""


@dataclass(frozen=True)
class Fichier:
    """Une sauvegarde écrite."""

    chemin: Path
    taille: int
    tables: int


def outil(nom: str) -> str:
    """Le chemin de `pg_dump` / `pg_restore` (GESTIONMPPRO_PG_BIN, sinon le PATH)."""
    dossier = reglages().pg_bin
    chemin = str(dossier / nom) if dossier else shutil.which(nom)
    if not chemin or not Path(chemin).is_file():
        raise SauvegardeImpossible(f"{nom} introuvable (régler GESTIONMPPRO_PG_BIN)")
    return chemin


def adresse_libpq(url: str) -> str:
    """L'URL SQLAlchemy en adresse libpq (`postgresql://…`)."""
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def sauvegarder(url: str, genre: GenreSauvegarde) -> Fichier:
    """Écrit la sauvegarde de la base `url` et la relit."""
    base = make_url(url).database or ""
    dossier = reglages().sauvegardes / base
    dossier.mkdir(parents=True, exist_ok=True)
    instant = horloge.maintenant().strftime("%Y-%m-%d-%H%M%S")
    chemin = dossier / f"{instant}-{genre.value.replace('_', '-')}-{base}.dump"
    resultat = subprocess.run(  # noqa: S603
        [outil("pg_dump"), "-Fc", "--no-owner", "-f", str(chemin), "--dbname", adresse_libpq(url)],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultat.returncode != 0:
        chemin.unlink(missing_ok=True)
        raise SauvegardeImpossible(f"pg_dump : {resultat.stderr.strip()[:300]}")
    liste = subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--list", str(chemin)], capture_output=True, text=True, check=False
    )
    if liste.returncode != 0:
        raise SauvegardeImpossible(f"sauvegarde illisible : {liste.stderr.strip()[:300]}")
    tables = sum(1 for x in liste.stdout.splitlines() if " TABLE DATA " in x)
    return Fichier(chemin, chemin.stat().st_size, tables)


def inscrire(c: Connection, fichier: Fichier, genre: GenreSauvegarde, base: str) -> None:
    """Inscrit la sauvegarde au registre de la base."""
    c.execute(
        insert(metadata.tables["sauvegarde"]),
        {
            "fichier": fichier.chemin.name,
            "genre": genre.value,
            "base": base,
            "taille": fichier.taille,
            "tables": fichier.tables,
            "pieces_incluses": False,
            "copie_externe": False,
            "cree_le": horloge.maintenant(),
        },
    )
