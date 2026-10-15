"""Sauvegardes de **cette** base : écrites, relues, avec leurs pièces, copiées, purgées.

Lot D10 (ARCHITECTURE § 13.3 ; décisions X2 et X7 de Mohamed) :

- `pg_dump -Fc` dans un fichier provisoire, **relu** (`pg_restore --list` : autant de tables
  que la base en compte), puis renommé ; l'archive des pièces jointes à côté, relue ; la copie
  sur le second disque (`GESTIONMPPRO_SAUVEGARDES_COPIE/<base>`), vérifiée à la taille ;
- les automatiques (décision X7, `services/sauvegarde_calendrier.py`) : quotidienne chaque soir
  à 22:00, hebdomadaire le dimanche, mensuelle le dernier jour du mois, rattrapées au passage
  suivant ; purge 14 / 8 / 12 (mensuelle de fin décembre gardée), dans le dossier **et** dans la
  copie (G-09) ; les manuelles et les « avant-* » ne s'effacent **jamais** seules ;
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
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services import sauvegarde_calendrier as calendrier
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services import sauvegarde_registre as registre
from gestion_mp_pro.services.sauvegarde_pieces import archiver

JOURNAL = logging.getLogger("gestion_mp_pro.sauvegarde")

ALERTE_HEURES = 26
FICHIERS_LISTES = 100
"""Les fichiers listés à l'écran (les automatiques seules en gardent 34, plus fin décembre)."""
POLITIQUE = (
    "Sauvegardes automatiques relues, à 22 h : une quotidienne chaque soir (gardée 14 jours), une "
    "hebdomadaire le dimanche (8 semaines), une mensuelle le dernier jour du mois (12 mois, celle "
    "de fin décembre gardée toujours) ; Mac éteint à 22 h, elles se font à son retour. La copie "
    "de sécurité suit la même conservation ; les sauvegardes manuelles et « avant » "
    "(restauration, reprise, vidage, mise à jour) ne s'effacent jamais seules."
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


def _tables_en_base(url: str | None) -> int:
    """Le nombre de tables du schéma `public` (ce que la relecture doit retrouver)."""
    requete = text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
    if url is None:
        with moteur().connect() as c:
            return int(c.execute(requete).scalar() or 0)
    autre = create_engine(url, poolclass=NullPool)
    try:
        with autre.connect() as c:
            return int(c.execute(requete).scalar() or 0)
    finally:
        autre.dispose()


def _ecrire_dump(pg_dump: Path, cible: Path, url: str | None) -> o.Lecture:
    """`pg_dump -Fc` dans un provisoire, relu (toutes les tables), puis mis à sa place."""
    attendues = _tables_en_base(url)
    provisoire = cible.with_name(f".{cible.name}.{os.getpid()}.partiel")
    try:
        with o.adresse_base(url) as adresse:
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


def _copier(cible: Path, vers: Path | None = None) -> str:
    """La copie de sécurité du fichier et de ses pièces ; rend l'erreur (vide si réussie)."""
    vers = vers or dossier_copie()
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
    genre: str = "manuelle",
    par_id: int | None = None,
    exiger_copie: bool = True,
    url: str | None = None,
) -> FichierSauvegarde:
    """Écrit une sauvegarde relue, avec ses pièces, et sa copie ; 503 lisible si impossible.

    `exiger_copie=False` (sauvegarde « avant restauration ») : une copie de sécurité manquée
    est notée au registre et au journal du serveur sans arrêter le geste — le fichier
    principal, relu, suffit à le défaire. `url` : une autre base que celle du serveur (cible
    d'une reprise, outil de vidage) — mêmes noms, dossiers à son nom ; le registre est alors
    tenu par l'appelant, dans la transaction qu'il ouvre sur cette base.
    """
    pg_dump = o.exiger("pg_dump")
    o.exiger("pg_restore")
    r = reglages()
    base = make_url(url).database or r.nom_base if url else r.nom_base
    d = r.sauvegardes / base
    copie = r.sauvegardes_copie / base if r.sauvegardes_copie is not None else None
    with _ECRITURE:
        d.mkdir(parents=True, exist_ok=True)
        cible = d / _nom_libre(d, genre)
        lecture = _ecrire_dump(pg_dump, cible, url)
        try:
            pieces = archiver(o.archive_de(cible), r.pieces / base)
        except BaseException:
            cible.unlink(missing_ok=True)
            raise
        erreur_copie = _copier(cible, copie)
    lu = o.lire_nom(cible.name)
    quand = lu.instant if lu else horloge.maintenant()
    entree = registre.Entree(
        fichier=cible.name,
        genre=genre,
        base=lecture.base,
        taille=cible.stat().st_size,
        tables=lecture.tables,
        pieces_incluses=True,
        copie_externe=copie is not None and not erreur_copie,
        cree_le=quand,
        par_id=par_id,
        erreur=erreur_copie,
    )
    if url is None:
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


def _automatiques_du_dossier(d: Path) -> list[tuple[Path, o.NomLu]]:
    """Les sauvegardes automatiques d'un dossier (quotidiennes, hebdomadaires, mensuelles)."""
    trouves = []
    for f in d.glob(f"{o.PREFIXE}*{o.EXTENSION}"):
        lu = o.lire_nom(f.name)
        if lu is not None and lu.genre in calendrier.AUTOMATIQUES:
            trouves.append((f, lu))
    return trouves


def automatiques() -> list[FichierSauvegarde]:
    """Les automatiques dues (décision X7), au plus une par genre, puis la purge ; rend celles
    faites. Une copie de sécurité manquée n'empêche pas les genres suivants : elle est relevée à
    la fin (503, tâche en échec, alerte), comme pour le geste manuel."""
    faites: dict[str, list[datetime]] = {g: [] for g in calendrier.AUTOMATIQUES}
    if dossier().is_dir():
        for _, lu in _automatiques_du_dossier(dossier()):
            faites[lu.genre].append(lu.instant)
    fichiers = [
        sauvegarder(genre, exiger_copie=False)
        for genre in calendrier.dues(faites, horloge.maintenant())
    ]
    if fichiers:
        purger()
    sans_copie = [f.nom for f in fichiers if dossier_copie() is not None and not f.copie]
    if sans_copie:
        raise Refus.indisponible(
            f"La sauvegarde {', '.join(sans_copie)} est faite, mais sa copie de sécurité est "
            f"impossible ({dossier_copie()}).",
            code="sauvegarde_impossible",
        )
    return fichiers


def dernieres_automatiques() -> list[Path]:
    """La plus récente sauvegarde de chaque genre automatique (pour refaire une copie manquée)."""
    if not dossier().is_dir():
        return []
    dernieres: dict[str, tuple[datetime, Path]] = {}
    for f, lu in _automatiques_du_dossier(dossier()):
        if lu.genre not in dernieres or lu.instant > dernieres[lu.genre][0]:
            dernieres[lu.genre] = (lu.instant, f)
    return [f for _, f in dernieres.values()]


def _purger_dossier(d: Path) -> list[str]:
    """Purge les automatiques d'un dossier (et leurs pièces) ; rend les noms effacés."""
    trouves = _automatiques_du_dossier(d)
    effaces = calendrier.a_effacer((f.name, lu.genre, lu.instant) for f, lu in trouves)
    for nom in effaces:
        (d / nom).unlink(missing_ok=True)
        o.archive_de(d / nom).unlink(missing_ok=True)
    return effaces


def purger() -> list[str]:
    """La rotation annoncée (14 / 8 / 12, fin décembre gardée), dans le dossier et dans la copie
    de sécurité ; rend les effacés du dossier."""
    effaces = _purger_dossier(dossier()) if dossier().is_dir() else []
    copie = dossier_copie()
    if copie is not None and copie.is_dir():
        _purger_dossier(copie)
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
