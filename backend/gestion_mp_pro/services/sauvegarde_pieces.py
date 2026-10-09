"""Les pièces jointes dans les sauvegardes (lot D10 ; défaut G-03 de Gestion MP).

Gestion MP gardait un miroir cumulatif à côté des sauvegardes, jamais réinjecté, avec des
chemins absolus, et qui mêlait les pièces des bases d'essai. PRO :

- les pièces de **cette** base seulement (`<GESTIONMPPRO_PIECES>/<base>`, chemins relatifs dans
  `piece_jointe.chemin`) ;
- une archive `.pieces.tar` à côté de chaque fichier de sauvegarde, relue (nombre de fichiers) ;
- à la restauration, les pièces de l'archive qui manquent sur le disque reviennent ; rien n'est
  écrasé ni effacé (un fichier de pièce ne change jamais : son nom est tiré au hasard), donc
  la restauration **garde** les pièces déposées depuis — elles restent aussi dans l'archive de
  la sauvegarde « avant restauration ».
"""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages


def dossier_pieces() -> Path:
    """Le dossier des pièces jointes de cette base."""
    return reglages().dossier_pieces


def _fichiers(racine: Path) -> list[Path]:
    """Les fichiers des pièces (liens symboliques exclus : on n'archive que du contenu à soi)."""
    if not racine.is_dir():
        return []
    return sorted(f for f in racine.rglob("*") if f.is_file() and not f.is_symlink())


def archiver(cible: Path) -> int:
    """Écrit l'archive des pièces de cette base (atomique, relue) ; rend le nombre de fichiers."""
    racine = dossier_pieces()
    fichiers = _fichiers(racine)
    provisoire = cible.with_name(f".{cible.name}.{os.getpid()}.partiel")
    try:
        with tarfile.open(provisoire, "w") as archive:
            for f in fichiers:
                archive.add(f, arcname=f.relative_to(racine).as_posix(), recursive=False)
        lus = compter(provisoire)
        if lus != len(fichiers):
            raise Refus.indisponible(
                f"La sauvegarde a échoué : l'archive des pièces jointes compte {lus} fichier(s) "
                f"sur {len(fichiers)}.",
                code="sauvegarde_impossible",
            )
        os.replace(provisoire, cible)
    finally:
        provisoire.unlink(missing_ok=True)
    return len(fichiers)


def compter(archive: Path) -> int:
    """Le nombre de fichiers d'une archive de pièces (la relecture)."""
    try:
        with tarfile.open(archive, "r") as a:
            return sum(1 for membre in a.getmembers() if membre.isfile())
    except (OSError, tarfile.TarError) as exc:
        raise Refus.saisie(f"Archive des pièces jointes illisible : {exc}") from exc


def _sur(racine: Path, nom: str) -> Path | None:
    """Le chemin d'un membre sous la racine, ou `None` s'il en sortirait (traversée refusée)."""
    chemin = (racine / nom).resolve()
    return chemin if chemin.is_relative_to(racine.resolve()) else None


def remettre(archive: Path) -> int:
    """Remet dans le dossier des pièces celles de l'archive qui y manquent ; rien n'est écrasé.

    Rend le nombre de fichiers revenus. Un membre qui n'est pas un fichier ordinaire, ou qui
    sortirait du dossier des pièces, est ignoré.
    """
    if not archive.is_file():
        return 0
    racine = dossier_pieces()
    racine.mkdir(parents=True, exist_ok=True)
    revenus = 0
    with tarfile.open(archive, "r") as a:
        for membre in a.getmembers():
            cible = _sur(racine, membre.name)
            if not membre.isfile() or cible is None or cible.exists():
                continue
            source = a.extractfile(membre)
            if source is None:
                continue
            cible.parent.mkdir(parents=True, exist_ok=True)
            provisoire = cible.with_name(f".{cible.name}.partiel")
            with source, provisoire.open("wb") as sortie:
                shutil.copyfileobj(source, sortie)
            os.replace(provisoire, cible)
            revenus += 1
    return revenus
