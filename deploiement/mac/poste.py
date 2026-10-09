"""Gestes du poste Mac sur la base de Gestion MP PRO, avec le code de la copie figée (lot X2).

Appelé par scripts/{demarrer,sauvegarder,restaurer}.sh et deploiement/mac/installer.sh (par
`poste` de commun.sh : PYTHONPATH = la copie figée, Python = son environnement). Il ne fait rien
d'autre que les services du paquet (D10, S1) : mêmes noms de fichiers, mêmes refus, même
registre que l'écran (Administration › Sauvegardes).

    poste.py a-un-schema              # code 0 : la base existe et porte un schéma Alembic
    poste.py etat                     # JSON : base, révisions, tables, comptes, mouvements
    poste.py migrer                   # met la base à la révision de ce code (semences comprises)
    poste.py sauvegarder [--genre G]  # écrit une sauvegarde relue, pièces comprises
    poste.py restaurer FICHIER --confirmation RESTAURER [--motif M]

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


def _ecrire(texte: str, flux: Any = sys.stdout) -> None:
    """Une ligne pour l'appelant (les scripts la lisent ou l'affichent)."""
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


def sauvegarder(genre: str) -> int:
    """Une sauvegarde de cette base ; la manuelle est écrite au journal, comme depuis l'écran."""
    from gestion_mp_pro.modeles.enums import ObjetJournal
    from gestion_mp_pro.services import audit, sauvegarde

    fichier = sauvegarde.sauvegarder(genre, exiger_copie=genre == "manuelle")
    if genre == "manuelle" and a_un_schema() == 0:
        with fabrique()() as s, s.begin():
            ligne = audit.journal(
                s, None, "sauvegarde", ObjetJournal.sauvegarde, detail=fichier.nom
            )
            ligne.utilisateur_nom = QUI
    _ecrire(str(sauvegarde.dossier() / fichier.nom))
    return 0


def restaurer(nom: str, confirmation: str, motif: str) -> int:
    """La restauration de D10 (tout ou rien, pièces, migration à head), attendue jusqu'au bout."""
    from gestion_mp_pro.services import execution, restauration
    from gestion_mp_pro.services.comptes import Acteur

    # Personne n'est connecté : l'auteur n'est pas un compte (sa sauvegarde « avant
    # restauration » n'a pas d'auteur, son nom reste au journal ; toutes les sessions sont
    # fermées).
    qui = Acteur(id=None, identifiant="", nom=QUI, role="")  # type: ignore[arg-type]
    p = restauration.preparer(qui, Path(nom).name, confirmation, motif)
    _ecrire(f"Sauvegarde « avant restauration » : {p.avant}")
    restauration.executer(p)
    with fabrique()() as s:
        e = execution.lire(s, execution.RESTAURATION)
    if e is None or e.dernier_essai_le is None or e.dernier_essai_le < p.debut:
        _ecrire("La restauration n'a pas noté son issue : voir le journal du serveur.", sys.stderr)
        return 1
    if e.erreur:
        _ecrire(f"Restauration échouée : {e.erreur}", sys.stderr)
        return 1
    _ecrire(f"Base {reglages().nom_base} restaurée depuis {p.fichier.name}.")
    return 0


def _arguments(arguments: list[str]) -> argparse.Namespace:
    """La ligne de commande."""
    a = argparse.ArgumentParser(prog="poste.py", description=__doc__.splitlines()[0])
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
    return a.parse_args(arguments)


def main(arguments: list[str]) -> int:
    """Le geste demandé ; un refus des services (404, 409, 422, 503) est dit, code 2."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
    a = _arguments(arguments)
    try:
        if a.geste == "a-un-schema":
            return a_un_schema()
        if a.geste == "etat":
            return etat()
        if a.geste == "migrer":
            return migrer()
        if a.geste == "sauvegarder":
            return sauvegarder(a.genre)
        return restaurer(a.fichier, a.confirmation, a.motif)
    except Refus as exc:
        _ecrire(f"Refusé : {exc.detail}", sys.stderr)
        return REFUSE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
