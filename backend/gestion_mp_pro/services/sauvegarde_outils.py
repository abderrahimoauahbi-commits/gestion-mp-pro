"""Outils de PostgreSQL et noms des fichiers de sauvegarde (lot D10, ARCHITECTURE § 13.3).

Leçons de Gestion MP gardées : chercher `pg_dump` par son **chemin complet** (un service n'a
pas le PATH d'un terminal) et **relire** un fichier avant de le déclarer bon. Aucune variable
d'environnement n'est lue ni posée (essai `test_config`) : le mot de passe de la base passe par
un fichier `passfile` temporaire (droits 0600) cité dans l'adresse de connexion, jamais sur la
ligne de commande ni dans l'environnement.

Noms : `gestion-mp-pro-AAAA-MM-JJ-HHMMSS-<genre>.dump` (heure de l'usine, horloge du serveur),
pièces jointes à côté dans `<même nom>.pieces.tar`. L'instant est lu dans le nom (pas dans la
date du fichier, qu'une copie change).
"""

from __future__ import annotations

import glob
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from sqlalchemy.engine import make_url

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.services import horloge

DOSSIERS = (
    "/opt/homebrew/bin",
    "/opt/homebrew/opt/postgresql@*/bin",
    "/usr/local/bin",
    "/usr/lib/postgresql/*/bin",
    "/usr/pgsql-*/bin",
    "/usr/bin",
    "/Applications/Postgres.app/Contents/Versions/latest/bin",
)
"""Où chercher les outils quand `GESTIONMPPRO_PG_BIN` n'est pas réglé (versions hautes d'abord)."""

PREFIXE = "gestion-mp-pro-"
EXTENSION = ".dump"
SUFFIXE_PIECES = ".pieces.tar"
MOTIF_NOM = re.compile(r"^gestion-mp-pro-(\d{4}-\d{2}-\d{2})-(\d{6})-([a-z]+(?:-[a-z]+)*)\.dump$")

GENRES = (
    "quotidienne",
    "manuelle",
    "avant-restauration",
    "avant-reprise",
    "avant-vidage",
    "avant-mise-a-jour",
    "reference-vide",
)
"""Les genres d'un fichier ; seules les quotidiennes sont purgées (décision X2)."""

LIBELLES = {
    "quotidienne": "automatique",
    "manuelle": "manuelle",
    "avant-restauration": "avant une restauration",
    "avant-reprise": "avant une reprise",
    "avant-vidage": "avant un vidage de l'activité",
    "avant-mise-a-jour": "avant une mise à jour",
    "reference-vide": "base vide de référence",
}

DELAI_DUMP_S = 1800
DELAI_LECTURE_S = 300
LIGNES_EN_TETE = 12


def outil(nom: str) -> Path | None:
    """Le chemin complet d'un outil de PostgreSQL (`pg_dump`, `pg_restore`, `psql`), ou `None`."""
    dossier = reglages().pg_bin
    if dossier is not None:
        candidat = dossier / nom
        return candidat if candidat.is_file() else None
    trouve = shutil.which(nom)
    if trouve:
        return Path(trouve)
    for motif in DOSSIERS:
        for d in sorted(glob.glob(motif), reverse=True):
            if (Path(d) / nom).is_file():
                return Path(d) / nom
    return None


def exiger(nom: str, geste: str = "Sauvegarde impossible") -> Path:
    """L'outil, ou un 503 lisible (G-05 : jamais de 500 brute)."""
    chemin = outil(nom)
    if chemin is None:
        raise Refus.indisponible(
            f"{geste} : {nom} est introuvable sur le serveur (installer les outils de "
            "PostgreSQL, ou indiquer leur dossier dans GESTIONMPPRO_PG_BIN).",
            code="sauvegarde_impossible",
        )
    return chemin


@contextmanager
def adresse_base() -> Iterator[str]:
    """L'adresse libpq de la base du serveur ; le mot de passe va dans un `passfile` éphémère."""
    url = make_url(reglages().base)
    mot_de_passe = url.password
    sans_secret = url.set(drivername="postgresql", password=None)
    adresse = sans_secret.render_as_string(hide_password=False)
    if not mot_de_passe:
        yield adresse
        return
    with tempfile.TemporaryDirectory(prefix="gmp-pro-") as dossier:
        fichier = Path(dossier) / "pgpass"
        fichier.touch(mode=0o600)
        echappe = str(mot_de_passe).replace("\\", "\\\\").replace(":", "\\:")
        fichier.write_text(f"*:*:*:*:{echappe}\n", encoding="utf-8")
        separateur = "&" if "?" in adresse else "?"
        yield f"{adresse}{separateur}passfile={fichier}"


def lancer(arguments: list[str], delai: int = DELAI_LECTURE_S) -> subprocess.CompletedProcess[str]:
    """Lance un outil et rend sa sortie (le code de retour est lu par l'appelant)."""
    # Arguments à nous seuls (outil trouvé par son chemin, fichiers du dossier) : pas de shell.
    return subprocess.run(  # noqa: S603
        arguments, capture_output=True, text=True, timeout=delai, check=False
    )


def raison(sortie: subprocess.CompletedProcess[str], longueur: int = 300) -> str:
    """Le message d'erreur d'un outil, raccourci (le détail complet va au journal du serveur)."""
    texte = (sortie.stderr or "").strip() or (sortie.stdout or "").strip()
    return texte[:longueur] or f"code de retour {sortie.returncode}"


@dataclass(frozen=True)
class Lecture:
    """Ce que la relecture d'un fichier y trouve."""

    tables: int
    base: str


def relire(fichier: Path) -> Lecture:
    """Relit une sauvegarde (`pg_restore --list`) ; illisible ou vide → 422 « illisible »."""
    sortie = lancer([str(exiger("pg_restore", "Relecture impossible")), "--list", str(fichier)])
    tables = sortie.stdout.count(" TABLE DATA ")
    if sortie.returncode != 0 or not tables:
        detail = raison(sortie, 200) if sortie.returncode != 0 else "vide"
        raise Refus.saisie(f"Sauvegarde illisible : {detail}")
    return Lecture(tables=tables, base=_base_de_l_en_tete(sortie.stdout))


def _base_de_l_en_tete(texte: str) -> str:
    """La base nommée dans l'en-tête d'un `pg_restore --list` (« dbname: … »)."""
    for ligne in texte.splitlines()[:LIGNES_EN_TETE]:
        if "dbname:" in ligne:
            return ligne.split("dbname:", 1)[1].strip()
    return ""


_BASES: dict[tuple[str, float, int], str] = {}


def base_du_fichier(fichier: Path) -> str:
    """La base d'un fichier, lue dans son en-tête et mémorisée (un fichier garde sa base)."""
    etat = fichier.stat()
    cle = (str(fichier), etat.st_mtime, etat.st_size)
    if cle not in _BASES:
        pg_restore = outil("pg_restore")
        texte = lancer([str(pg_restore), "--list", str(fichier)]).stdout if pg_restore else ""
        _BASES[cle] = _base_de_l_en_tete(texte)
    return _BASES[cle]


def revision_du_fichier(fichier: Path) -> str | None:
    """La révision Alembic qu'une sauvegarde a connue (sa table `alembic_version`)."""
    pg_restore = exiger("pg_restore", "Relecture impossible")
    sortie = lancer([str(pg_restore), "-a", "-t", "alembic_version", "-f", "-", str(fichier)])
    dans_copie = False
    for ligne in sortie.stdout.splitlines():
        if ligne.startswith("COPY "):
            dans_copie = True
        elif ligne == "\\.":
            dans_copie = False
        elif dans_copie and ligne.strip():
            return ligne.split("\t", 1)[0].strip()
    return None


def nom_de(genre: str, instant: datetime | None = None) -> str:
    """Le nom d'une sauvegarde de ce genre, à cet instant (heure de l'usine)."""
    if genre not in GENRES:
        raise ValueError(f"genre de sauvegarde inconnu : {genre}")
    quand = (instant or horloge.maintenant()).astimezone(horloge.FUSEAU)
    return f"{PREFIXE}{quand:%Y-%m-%d-%H%M%S}-{genre}{EXTENSION}"


@dataclass(frozen=True)
class NomLu:
    """Ce qu'un nom de sauvegarde dit : son jour, son instant, son genre."""

    jour: date
    instant: datetime
    genre: str


def lire_nom(nom: str) -> NomLu | None:
    """Lit un nom de sauvegarde ; `None` s'il ne suit pas la règle (fichier étranger)."""
    trouve = MOTIF_NOM.match(nom)
    if trouve is None or trouve.group(3) not in GENRES:
        return None
    heure = trouve.group(2)
    try:
        jour = date.fromisoformat(trouve.group(1))
        instant = datetime.combine(
            jour, time(int(heure[:2]), int(heure[2:4]), int(heure[4:])), tzinfo=horloge.FUSEAU
        )
    except ValueError:
        return None
    return NomLu(jour=instant.date(), instant=instant, genre=trouve.group(3))


def archive_de(fichier: Path) -> Path:
    """L'archive des pièces jointes qui accompagne un fichier de sauvegarde."""
    return fichier.with_name(fichier.name + SUFFIXE_PIECES)
