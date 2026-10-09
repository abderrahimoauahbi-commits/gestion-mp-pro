"""Le registre des sauvegardes (table `sauvegarde`, MODELE-DONNEES § 3.1.12).

Le disque fait foi : le registre garde ce que le disque ne dit pas (qui l'a faite, l'erreur
d'une copie) et se recale sur le disque (`recaler`). La restauration le copie en mémoire avant
de remplacer la base et le réécrit après (`photographier`, `reecrire`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Sauvegarde, Utilisateur
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import GenreSauvegarde

GENRES_DU_REGISTRE = {
    "quotidienne": GenreSauvegarde.quotidienne,
    "manuelle": GenreSauvegarde.manuelle,
    "avant-restauration": GenreSauvegarde.avant_restauration,
    "avant-reprise": GenreSauvegarde.avant_reprise,
    "reference-vide": GenreSauvegarde.reference_vide,
}
"""Les genres que le registre sait écrire (« avant-vidage » et « avant-mise-a-jour » : disque
seulement, en attendant leur valeur dans l'énumération — demandé au coordinateur)."""


@dataclass(frozen=True)
class Entree:
    """Une ligne du registre, détachée de la base (survit à une restauration)."""

    fichier: str
    genre: str
    base: str
    taille: int
    tables: int
    pieces_incluses: bool
    copie_externe: bool
    cree_le: datetime
    par_id: int | None = None
    erreur: str = ""


def enregistrer(s: Session, e: Entree) -> None:
    """Écrit (ou met à jour) la ligne d'un fichier."""
    genre = GENRES_DU_REGISTRE.get(e.genre)
    if genre is None:
        return
    valeurs = {
        "fichier": e.fichier[: L.FICHIER],
        "genre": genre,
        "base": e.base[: L.NOM_BASE],
        "taille": e.taille,
        "tables": e.tables,
        "pieces_incluses": e.pieces_incluses,
        "copie_externe": e.copie_externe,
        "cree_le": e.cree_le,
        "par_id": e.par_id,
        "erreur": e.erreur[: L.ERREUR],
    }
    requete = insert(Sauvegarde).values(**valeurs)
    mise_a_jour = {k: v for k, v in valeurs.items() if k not in ("fichier", "par_id")}
    s.execute(requete.on_conflict_do_update(index_elements=["fichier"], set_=mise_a_jour))


def oublier(s: Session, fichiers: list[str]) -> None:
    """Retire du registre des fichiers effacés du disque (purge)."""
    if fichiers:
        s.execute(delete(Sauvegarde).where(Sauvegarde.fichier.in_(fichiers)))


def lire(s: Session) -> dict[str, Sauvegarde]:
    """Le registre, par nom de fichier."""
    return {x.fichier: x for x in s.scalars(select(Sauvegarde))}


def photographier(s: Session) -> list[Entree]:
    """Le registre en mémoire (avant une restauration)."""
    return [
        Entree(
            fichier=x.fichier,
            genre=next((k for k, v in GENRES_DU_REGISTRE.items() if v == x.genre), "manuelle"),
            base=x.base,
            taille=x.taille,
            tables=x.tables,
            pieces_incluses=x.pieces_incluses,
            copie_externe=x.copie_externe,
            cree_le=x.cree_le,
            par_id=x.par_id,
            erreur=x.erreur,
        )
        for x in s.scalars(select(Sauvegarde).order_by(Sauvegarde.id))
    ]


def reecrire(s: Session, entrees: list[Entree]) -> None:
    """Réécrit le registre d'avant dans la base restaurée (auteurs absents de la base : vides)."""
    comptes = set(s.scalars(select(Utilisateur.id)))
    s.execute(delete(Sauvegarde))
    for e in entrees:
        par = e.par_id if e.par_id in comptes else None
        enregistrer(s, replace(e, par_id=par))
