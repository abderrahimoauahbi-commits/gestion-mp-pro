"""Sauvegardes de **cette** base : écrites, relues, avec leurs pièces, copiées, purgées.

Lot D10 (ARCHITECTURE § 13.3 ; décision X2 de Mohamed) :

- `pg_dump -Fc` dans un fichier provisoire, **relu** (`pg_restore --list` : autant de tables
  que la base en compte), puis renommé ; l'archive des pièces jointes à côté, relue ; la copie
  sur le second disque (`GESTIONMPPRO_SAUVEGARDES_COPIE/<base>`), vérifiée à la taille ;
- purge : 14 quotidiennes + la première de chacun des 12 derniers mois, dans le dossier **et**
  dans la copie (G-09) ; les manuelles et les « avant-* » ne s'effacent **jamais** seules ;
- état et alerte calculés sur les seules sauvegardes de cette base (G-06), alerte à 26 h ;
  un échec ne se tait jamais (bandeau rouge de la direction, `/api/sante`).

L'état et l'alerte sont dans `services/sauvegarde_etat.py`, la restauration dans
`services/restauration.py`.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services import sauvegarde_registre as registre
from gestion_mp_pro.services.sauvegarde_pieces import archiver

JOURNAL = logging.getLogger("gestion_mp_pro.sauvegarde")

QUOTIDIENNES = 14
MENSUELLES = 12
ALERTE_HEURES = 26
FICHIERS_LISTES = 30
POLITIQUE = (
    "Une sauvegarde automatique par jour, relue, gardée 14 jours, puis la première de chaque "
    "mois gardée 12 mois ; la copie de sécurité suit la même conservation ; les sauvegardes "
    "manuelles et « avant » (restauration, reprise, vidage, mise à jour) ne s'effacent jamais "
    "seules."
)
_ECRITURE = threading.Lock()


def dossier() -> Path:
    """Le dossier des sauvegardes de cette base."""
    return reglages().dossier_sauvegardes


def dossier_copie() -> Path | None:
    """Le dossier de la copie de sécurité de cette base (second disque), s'il est réglé."""
    r = reglages()
    return r.sauvegardes_copie / r.nom_base if r.sauvegardes_copie is not None else None


@dataclass(frozen=True)
class FichierSauvegarde:
    """Une sauvegarde du dossier, telle que l'écran la liste."""

    nom: str
    genre: str
    nature: str
    base: str
    autre_base: bool
    taille: int
    quand: datetime
    tables: int | None
    pieces: bool
    copie: bool


def _nom_libre(d: Path, genre: str) -> str:
    """Un nom pas encore pris (deux sauvegardes dans la même seconde : la seconde suivante)."""
    instant = horloge.maintenant()
    nom = o.nom_de(genre, instant)
    while (d / nom).exists():
        instant += timedelta(seconds=1)
        nom = o.nom_de(genre, instant)
    return nom


def _tables_en_base() -> int:
    """Le nombre de tables du schéma `public` (ce que la relecture doit retrouver)."""
    with moteur().connect() as c:
        requete = text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
        return int(c.execute(requete).scalar() or 0)


def _ecrire_dump(pg_dump: Path, cible: Path) -> o.Lecture:
    """`pg_dump -Fc` dans un provisoire, relu (toutes les tables), puis mis à sa place."""
    attendues = _tables_en_base()
    provisoire = cible.with_name(f".{cible.name}.{os.getpid()}.partiel")
    try:
        with o.adresse_base() as adresse:
            arguments = [str(pg_dump), "-Fc", "-f", str(provisoire), "-d", adresse]
            sortie = o.lancer(arguments, o.DELAI_DUMP_S)
        if sortie.returncode != 0:
            JOURNAL.error("pg_dump a échoué : %s", sortie.stderr)
            raise Refus.indisponible(
                f"La sauvegarde a échoué : {o.raison(sortie)}", code="sauvegarde_impossible"
            )
        lecture = o.relire(provisoire)
        if lecture.tables < attendues:
            raise Refus.indisponible(
                f"La sauvegarde a échoué : {lecture.tables} table(s) relue(s) sur "
                f"{attendues} en base.",
                code="sauvegarde_impossible",
            )
        os.replace(provisoire, cible)
    finally:
        provisoire.unlink(missing_ok=True)
    return lecture


def _copier_un(source: Path, vers: Path) -> None:
    """Copie un fichier (provisoire puis renommage) et vérifie sa taille."""
    cible = vers / source.name
    provisoire = vers / f".{source.name}.{os.getpid()}.partiel"
    try:
        shutil.copy2(source, provisoire)
        if provisoire.stat().st_size != source.stat().st_size:
            raise OSError(f"{source.name} : taille différente après copie")
        os.replace(provisoire, cible)
    finally:
        provisoire.unlink(missing_ok=True)


def _copier(cible: Path) -> str:
    """La copie de sécurité du fichier et de ses pièces ; rend l'erreur (vide si réussie)."""
    vers = dossier_copie()
    if vers is None:
        return ""
    try:
        vers.mkdir(parents=True, exist_ok=True)
        for f in (cible, o.archive_de(cible)):
            _copier_un(f, vers)
    except OSError as exc:
        JOURNAL.error("Copie de sécurité impossible : %s", exc)
        return f"copie de sécurité impossible ({vers}) : {exc}"
    return ""


def recopier(fichier: Path) -> None:
    """Refait la copie de sécurité d'une sauvegarde (copie manquée la veille) ; 503 si elle
    échoue encore."""
    erreur = _copier(fichier)
    if erreur:
        raise Refus.indisponible(
            f"La sauvegarde {fichier.name} est faite, mais sa {erreur}",
            code="sauvegarde_impossible",
        )


def _noter_au_registre(e: registre.Entree) -> None:
    """Le registre suit ; s'il ne peut pas (base muette), le fichier sur le disque fait foi."""
    try:
        with fabrique()() as s, s.begin():
            registre.enregistrer(s, e)
    except SQLAlchemyError:
        JOURNAL.exception("Registre des sauvegardes non mis à jour pour %s.", e.fichier)


def sauvegarder(
    genre: str = "manuelle", par_id: int | None = None, exiger_copie: bool = True
) -> FichierSauvegarde:
    """Écrit une sauvegarde relue, avec ses pièces, et sa copie ; 503 lisible si impossible.

    `exiger_copie=False` (sauvegarde « avant restauration ») : une copie de sécurité manquée
    est notée au registre et au journal du serveur sans arrêter le geste — le fichier
    principal, relu, suffit à le défaire.
    """
    pg_dump = o.exiger("pg_dump")
    o.exiger("pg_restore")
    d = dossier()
    with _ECRITURE:
        d.mkdir(parents=True, exist_ok=True)
        cible = d / _nom_libre(d, genre)
        lecture = _ecrire_dump(pg_dump, cible)
        try:
            pieces = archiver(o.archive_de(cible))
        except BaseException:
            cible.unlink(missing_ok=True)
            raise
        erreur_copie = _copier(cible)
    lu = o.lire_nom(cible.name)
    quand = lu.instant if lu else horloge.maintenant()
    entree = registre.Entree(
        fichier=cible.name,
        genre=genre,
        base=lecture.base,
        taille=cible.stat().st_size,
        tables=lecture.tables,
        pieces_incluses=True,
        copie_externe=dossier_copie() is not None and not erreur_copie,
        cree_le=quand,
        par_id=par_id,
        erreur=erreur_copie,
    )
    _noter_au_registre(entree)
    JOURNAL.info(
        "Sauvegarde %s écrite (%s tables, %s pièce(s)).", cible.name, lecture.tables, pieces
    )
    if erreur_copie and exiger_copie:
        raise Refus.indisponible(
            f"La sauvegarde {cible.name} est faite, mais sa {erreur_copie}",
            code="sauvegarde_impossible",
        )
    return _fiche(cible, lecture.base, lecture.tables, entree.copie_externe)


def du_jour() -> FichierSauvegarde | None:
    """La quotidienne du jour si elle manque (puis la purge) ; `None` si elle est déjà faite."""
    jour = horloge.aujourd_hui()
    for f in dossier().glob(f"{o.PREFIXE}*-quotidienne{o.EXTENSION}"):
        lu = o.lire_nom(f.name)
        if lu is not None and lu.jour == jour:
            return None
    fichier = sauvegarder("quotidienne")
    purger()
    return fichier


def _a_garder(jours: list[date], quotidiennes: int, mensuelles: int) -> set[date]:
    """Les 14 jours les plus récents et le premier jour de chacun des 12 derniers mois."""
    gardes = set(sorted(jours, reverse=True)[:quotidiennes])
    premiers: dict[tuple[int, int], date] = {}
    for j in sorted(jours):
        premiers.setdefault((j.year, j.month), j)
    gardes |= set(sorted(premiers.values(), reverse=True)[:mensuelles])
    return gardes


def _purger_dossier(d: Path, quotidiennes: int, mensuelles: int) -> list[str]:
    """Purge les quotidiennes d'un dossier (et leurs pièces) ; rend les noms effacés."""
    par_jour: dict[date, list[Path]] = {}
    for f in d.glob(f"{o.PREFIXE}*-quotidienne{o.EXTENSION}"):
        lu = o.lire_nom(f.name)
        if lu is not None and lu.genre == "quotidienne":
            par_jour.setdefault(lu.jour, []).append(f)
    gardes = _a_garder(list(par_jour), quotidiennes, mensuelles)
    effaces: list[str] = []
    for jour, fichiers in par_jour.items():
        if jour in gardes:
            continue
        for f in fichiers:
            f.unlink(missing_ok=True)
            o.archive_de(f).unlink(missing_ok=True)
            effaces.append(f.name)
    return sorted(effaces)


def purger(quotidiennes: int = QUOTIDIENNES, mensuelles: int = MENSUELLES) -> list[str]:
    """La rotation annoncée, dans le dossier et dans la copie de sécurité ; rend les effacés."""
    effaces = _purger_dossier(dossier(), quotidiennes, mensuelles) if dossier().is_dir() else []
    copie = dossier_copie()
    if copie is not None and copie.is_dir():
        _purger_dossier(copie, quotidiennes, mensuelles)
    if effaces:
        try:
            with fabrique()() as s, s.begin():
                registre.oublier(s, effaces)
        except SQLAlchemyError:
            JOURNAL.exception("Registre des sauvegardes non purgé.")
    return effaces


def _fiche(f: Path, base: str, tables: int | None, copie: bool) -> FichierSauvegarde:
    """La fiche d'un fichier de sauvegarde."""
    lu = o.lire_nom(f.name)
    genre = lu.genre if lu else "manuelle"
    return FichierSauvegarde(
        nom=f.name,
        genre=genre,
        nature=o.LIBELLES.get(genre, genre),
        base=base,
        autre_base=bool(base) and base != reglages().nom_base,
        taille=f.stat().st_size,
        quand=lu.instant if lu else datetime.fromtimestamp(f.stat().st_mtime, horloge.FUSEAU),
        tables=tables,
        pieces=o.archive_de(f).is_file(),
        copie=copie,
    )


def lister(s: Session | None = None) -> list[FichierSauvegarde]:
    """Les sauvegardes du dossier, la plus récente d'abord (celles d'autres bases signalées)."""
    d = dossier()
    if not d.is_dir():
        return []
    connus = registre.lire(s) if s is not None else {}
    copie = dossier_copie()
    fiches = []
    for f in d.glob(f"{o.PREFIXE}*{o.EXTENSION}"):
        if o.lire_nom(f.name) is None:
            continue
        r = connus.get(f.name)
        en_copie = copie is not None and (copie / f.name).is_file()
        fiches.append(_fiche(f, o.base_du_fichier(f), r.tables if r else None, en_copie))
    return sorted(fiches, key=lambda x: (x.quand, x.nom), reverse=True)
