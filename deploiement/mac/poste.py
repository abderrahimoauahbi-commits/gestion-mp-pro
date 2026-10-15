"""Gestes du poste Mac sur la base de Gestion MP PRO, avec le code de la copie figée (lot X2).

Appelé par scripts/{demarrer,sauvegarder,restaurer,compter}.sh et deploiement/mac/installer.sh
(par `poste` de commun.sh : PYTHONPATH = la copie figée, Python = son environnement), et par le
kit du serveur Windows (deploiement/windows, `--qui "serveur Windows (scripts)"`). Il ne fait
rien d'autre que les services du paquet (D10, S1) : mêmes noms de fichiers, mêmes refus, même
registre que l'écran (Administration › Sauvegardes).

    poste.py a-un-schema              # code 0 : la base existe et porte un schéma Alembic
    poste.py etat                     # JSON : base, révisions, tables, comptes, mouvements
    poste.py migrer                   # met la base à la révision de ce code (semences comprises)
    poste.py sauvegarder [--genre G]  # écrit une sauvegarde relue, pièces comprises
    poste.py restaurer FICHIER --confirmation RESTAURER [--motif M]
    poste.py comptes                  # JSON : révision et lignes de chaque table
    poste.py comparer-comptes FICHIER # ces lignes contre celles d'un autre serveur (transfert)

Codes de sortie : 0 fait ; 1 échec ; 2 refusé (le message dit pourquoi, rien n'a changé).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import OperationalError

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique, moteur

REFUSE = 2
GENRES = ("manuelle", "avant-mise-a-jour", "reference-vide", "avant-vidage")
QUI = "poste Mac (scripts)"
EXPLOITATION = ("journal", "session", "sauvegarde", "tache_execution")
"""Tables qu'un transfert change forcément (journal de la sauvegarde et de la restauration,
sessions fermées, registre des sauvegardes de ce serveur, état des tâches) : dites, pas fautes."""


def _ecrire(texte: str, flux: Any = None) -> None:
    """Une ligne pour l'appelant (les scripts la lisent ou l'affichent) ; sortie standard par
    défaut, lue à l'appel (pas à l'import)."""
    flux = flux or sys.stdout
    flux.write(texte + "\n")
    flux.flush()


def a_un_schema() -> int:
    """0 si la base existe et porte un schéma de Gestion MP PRO (table `alembic_version`)."""
    try:
        with moteur().connect() as c:
            return 0 if inspect(c).has_table("alembic_version") else 1
    except OperationalError:
        return 1


def etat() -> int:
    """L'état de la base, en JSON : de quoi vérifier une installation sans rien lire du métier."""
    from gestion_mp_pro.modeles import Mouvement, Utilisateur
    from gestion_mp_pro.services import installation

    r = reglages()
    with moteur().connect() as c:
        tables = c.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"))
        proprietaire = c.scalar(
            text(
                "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()"
            )
        )
        utilisateur = c.scalar(text("SELECT current_user"))
    revision = installation.revision_courante()
    resultat: dict[str, Any] = {
        "base": r.nom_base,
        "proprietaire": proprietaire,
        "utilisateur": utilisateur,
        "revision": revision,
        "attendue": installation.revision_attendue(),
        "tables": tables,
        "sauvegardes": str(r.dossier_sauvegardes),
        "pieces": str(r.dossier_pieces),
    }
    if revision is not None:
        with fabrique()() as s:
            resultat["comptes"] = s.scalar(select(func.count()).select_from(Utilisateur))
            resultat["mouvements"] = s.scalar(select(func.count()).select_from(Mouvement))
        with moteur().connect() as c:
            resultat["semences_manquantes"] = installation.semences_manquantes(c)
    _ecrire(json.dumps(resultat, ensure_ascii=False, default=str))
    return 0


def migrer() -> int:
    """Met la base à la révision de ce code, sous le verrou MIGRATION (comme au démarrage)."""
    from gestion_mp_pro.services import installation

    faites = installation.migrer()
    with moteur().connect() as c:
        manque = installation.semences_manquantes(c)
    if manque:
        _ecrire(f"Semences manquantes après migration : {manque}", sys.stderr)
        return 1
    tete = installation.revision_courante()
    _ecrire(f"Base {reglages().nom_base} à la révision {tete} ({len(faites)} appliquée(s)).")
    return 0


def sauvegarder(genre: str, qui: str = QUI) -> int:
    """Une sauvegarde de cette base ; la manuelle est écrite au journal, comme depuis l'écran."""
    from gestion_mp_pro.modeles.enums import ObjetJournal
    from gestion_mp_pro.services import audit, sauvegarde

    fichier = sauvegarde.sauvegarder(genre, exiger_copie=genre == "manuelle")
    if genre == "manuelle" and a_un_schema() == 0:
        with fabrique()() as s, s.begin():
            ligne = audit.journal(
                s, None, "sauvegarde", ObjetJournal.sauvegarde, detail=fichier.nom
            )
            ligne.utilisateur_nom = qui
    _ecrire(str(sauvegarde.dossier() / fichier.nom))
    return 0


def restaurer(nom: str, confirmation: str, motif: str, qui: str = QUI) -> int:
    """La restauration de D10 (tout ou rien, pièces, migration à head), attendue jusqu'au bout."""
    from gestion_mp_pro.services import execution, restauration
    from gestion_mp_pro.services.comptes import Acteur

    # Personne n'est connecté : l'auteur n'est pas un compte (sa sauvegarde « avant
    # restauration » n'a pas d'auteur, son nom reste au journal ; toutes les sessions sont
    # fermées).
    auteur = Acteur(id=None, identifiant="", nom=qui, role="")  # type: ignore[arg-type]
    p = restauration.preparer(auteur, Path(nom).name, confirmation, motif)
    _ecrire(f"Sauvegarde « avant restauration » : {p.avant}")
    restauration.executer(p)
    with fabrique()() as s:
        e = execution.lire(s, execution.RESTAURATION)
    if e is None or e.dernier_essai_le is None or e.dernier_essai_le < p.debut:
        _ecrire(
            "La restauration n'a pas noté son issue : voir le journal du serveur.",
            sys.stderr,
        )
        return 1
    if e.erreur:
        _ecrire(f"Restauration échouée : {e.erreur}", sys.stderr)
        return 1
    _ecrire(f"Base {reglages().nom_base} restaurée depuis {p.fichier.name}.")
    return 0


def lignes_par_table() -> dict[str, Any]:
    """La révision du schéma et le nombre de lignes de chaque table de `public`."""
    from gestion_mp_pro.services import installation

    with moteur().connect() as c:
        noms = c.scalars(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        ).all()
        # Noms lus dans le catalogue de la base, cités : aucune saisie dans la requête.
        tables = {
            n: c.scalar(text(f'SELECT count(*) FROM public."{n}"'))  # noqa: S608
            for n in noms
        }
    return {
        "base": reglages().nom_base,
        "revision": installation.revision_courante(),
        "tables": tables,
    }


def ecarts(autre: dict[str, Any], ici: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(fautes, remarques) entre deux comptes : une table métier qui diffère est une faute."""
    fautes: list[str] = []
    remarques: list[str] = []
    if autre.get("revision") != ici.get("revision"):
        remarques.append(
            f"révision du schéma : {autre.get('revision')} là-bas, {ici.get('revision')} ici "
            "(une version plus récente peut ajouter des lignes de référence)"
        )
    a, b = autre.get("tables", {}), ici.get("tables", {})
    for table in sorted(set(a) | set(b)):
        if a.get(table) == b.get(table):
            continue
        ligne = f"{table} : {a.get(table, 'absente')} là-bas, {b.get(table, 'absente')} ici"
        (remarques if table in EXPLOITATION else fautes).append(ligne)
    return fautes, remarques


def comparer_comptes(fichier: str) -> int:
    """Compare cette base aux comptes d'un autre serveur (`poste.py comptes` là-bas)."""
    # utf-8-sig : PowerShell 5.1 écrit un BOM en tête de ses fichiers.
    autre = json.loads(Path(fichier).read_text(encoding="utf-8-sig"))
    ici = lignes_par_table()
    fautes, remarques = ecarts(autre, ici)
    for r in remarques:
        _ecrire(f"Remarque — {r}")
    for f in fautes:
        _ecrire(f"ÉCART — {f}", sys.stderr)
    metier = {k: v for k, v in ici["tables"].items() if k not in EXPLOITATION}
    total = sum(v or 0 for v in metier.values())
    if fautes:
        _ecrire(
            f"{len(fautes)} table(s) métier diffèrent : le transfert n'est pas fidèle.",
            sys.stderr,
        )
        return 1
    _ecrire(f"Mêmes lignes dans les {len(metier)} tables métier ({total} lignes en tout).")
    return 0


def _arguments(arguments: list[str]) -> argparse.Namespace:
    """La ligne de commande."""
    a = argparse.ArgumentParser(prog="poste.py", description=__doc__.splitlines()[0])
    a.add_argument("--qui", default=QUI, help="le nom écrit au journal (défaut : %(default)s)")
    gestes = a.add_subparsers(dest="geste", required=True)
    gestes.add_parser("a-un-schema")
    gestes.add_parser("etat")
    gestes.add_parser("migrer")
    s = gestes.add_parser("sauvegarder")
    s.add_argument("--genre", choices=GENRES, default="manuelle")
    r = gestes.add_parser("restaurer")
    r.add_argument("fichier")
    r.add_argument("--confirmation", required=True)
    r.add_argument("--motif", default="restauration depuis le poste (scripts/restaurer.sh)")
    gestes.add_parser("comptes")
    c = gestes.add_parser("comparer-comptes")
    c.add_argument("fichier")
    return a.parse_args(arguments)


def _comptes() -> int:
    """Les lignes de chaque table, en JSON (à garder avec la sauvegarde d'un transfert)."""
    _ecrire(json.dumps(lignes_par_table(), ensure_ascii=False))
    return 0


def main(arguments: list[str]) -> int:
    """Le geste demandé ; un refus des services (404, 409, 422, 503) est dit, code 2."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
    a = _arguments(arguments)
    gestes = {
        "a-un-schema": a_un_schema,
        "etat": etat,
        "migrer": migrer,
        "comptes": _comptes,
        "sauvegarder": lambda: sauvegarder(a.genre, a.qui),
        "restaurer": lambda: restaurer(a.fichier, a.confirmation, a.motif, a.qui),
        "comparer-comptes": lambda: comparer_comptes(a.fichier),
    }
    try:
        return gestes[a.geste]()
    except Refus as exc:
        _ecrire(f"Refusé : {exc.detail}", sys.stderr)
        return REFUSE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
