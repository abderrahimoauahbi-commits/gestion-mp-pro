"""Sauvegarde de la cible avant d'y écrire (« avant reprise », « base vide de référence »).

Par le service des sauvegardes (lot D10, `services.sauvegarde.sauvegarder(url=…)`) : `pg_dump
-Fc` de la base cible dans `<GESTIONMPPRO_SAUVEGARDES>/<base>/`, relue, avec l'archive de ses
pièces jointes et sa copie de sécurité, au nom que l'écran liste et restaure ; inscrite ici au
registre `sauvegarde` de la cible, dans la transaction de la reprise (MODELE-DONNEES § 10.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Connection, insert
from sqlalchemy.engine import make_url

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import GenreSauvegarde
from gestion_mp_pro.services import horloge, sauvegarde_outils
from gestion_mp_pro.services import sauvegarde as service


class SauvegardeImpossible(Exception):
    """`pg_dump` absent ou en échec : rien n'est écrit dans la cible."""


@dataclass(frozen=True)
class Fichier:
    """Une sauvegarde écrite."""

    chemin: Path
    taille: int
    tables: int


def outil(nom: str) -> str:
    """Le chemin de `pg_dump` / `pg_restore` (GESTIONMPPRO_PG_BIN, sinon le PATH et les dossiers
    connus : `services.sauvegarde_outils.outil`)."""
    chemin = sauvegarde_outils.outil(nom)
    if chemin is None:
        raise SauvegardeImpossible(f"{nom} introuvable (régler GESTIONMPPRO_PG_BIN)")
    return str(chemin)


def sauvegarder(url: str, genre: GenreSauvegarde) -> Fichier:
    """Écrit la sauvegarde de la base `url` par le service du lot D10 (relue, pièces de cette
    base, copie de sécurité, noms que l'écran liste et restaure)."""
    try:
        f = service.sauvegarder(genre.value.replace("_", "-"), exiger_copie=False, url=url)
    except Refus as exc:
        raise SauvegardeImpossible(exc.detail) from exc
    chemin = reglages().sauvegardes / (make_url(url).database or "") / f.nom
    return Fichier(chemin, f.taille, f.tables or 0)


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
            "pieces_incluses": True,
            "copie_externe": False,
            "cree_le": horloge.maintenant(),
        },
    )
