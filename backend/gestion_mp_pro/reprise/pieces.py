"""Pièces jointes : fichiers **copiés** (jamais déplacés) du dossier de Gestion MP vers celui
de PRO, empreinte vérifiée, chemin relatif (MODELE-DONNEES § 10.3).

- Source : `<GESTIONMPPRO_PIECES_GESTION_MP>/<base source>` (ou `--pieces-source`) ; le chemin
  d'une pièce y est relatif (Gestion MP corrigé) ou absolu (pièces d'avant) ; à défaut, le
  fichier est cherché à `<objet>/<id>/<nom>`, comme le fait Gestion MP.
- Cible : `<GESTIONMPPRO_PIECES>/<base cible>/<objet PRO>/<id>/<nom du fichier>`.
- Une copie déjà faite et identique (même SHA-256) n'est pas refaite ; un fichier introuvable
  ou vide est signalé et sa ligne n'est pas reprise. Rien n'est jamais écrit côté source.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from gestion_mp_pro.reprise.contexte import Contexte

OBJETS = {
    "article": "matiere",
    "fournisseur": "fournisseur",
    "commande": "commande",
    "reception": "reception",
    "dossier": "dossier",
    "reclamation": "reclamation",
    "inventaire": "inventaire",
}
REFERENTIELS = frozenset({"matiere", "fournisseur"})
BLOC = 1 << 20


def empreinte_fichier(chemin: Path) -> str:
    """SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        while bloc := f.read(BLOC):
            h.update(bloc)
    return h.hexdigest()


def _fichier_source(racine: Path, p: dict[str, Any]) -> Path | None:
    """Le fichier d'une pièce dans le dossier de Gestion MP (règle de Gestion MP)."""
    chemin = Path(p["chemin"] or "")
    if not chemin.is_absolute():
        chemin = racine / chemin
    if chemin.is_file():
        return chemin
    repli = racine / p["objet"] / str(p["objet_id"]) / chemin.name
    return repli if repli.is_file() else None


def _copier(origine: Path, destination: Path, attendu: str) -> None:
    """Copie le fichier (sans toucher l'original) puis vérifie son empreinte."""
    if destination.is_file() and empreinte_fichier(destination) == attendu:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporaire = destination.with_name(destination.name + ".reprise")
    shutil.copyfile(origine, temporaire)
    if empreinte_fichier(temporaire) != attendu:
        temporaire.unlink(missing_ok=True)
        raise OSError(f"copie altérée : {origine}")
    temporaire.replace(destination)


def pieces(ctx: Contexte, genres: frozenset[str]) -> list[dict[str, Any]]:
    """Les lignes `piece_jointe` des objets de `genres` (fichiers copiés au passage)."""
    lignes = []
    racine, cible = ctx.options.pieces_source, ctx.options.pieces_cible
    for p in ctx.photo.lignes("piece_jointe"):
        objet = OBJETS.get(p["objet"])
        if objet is None:
            ctx.signaler("piece_jointe", p["id"], f"objet « {p['objet']} » inconnu : non reprise")
            continue
        if objet not in genres:
            continue
        origine = _fichier_source(Path(racine), p) if racine else None
        if origine is None or origine.stat().st_size == 0:
            ctx.signaler("piece_jointe", p["id"], f"fichier « {p['nom']} » introuvable ou vide")
            continue
        empreinte = empreinte_fichier(origine)
        relatif = Path(objet) / str(p["objet_id"]) / origine.name
        if not ctx.options.essai and cible:
            _copier(origine, Path(cible) / relatif, empreinte)
        v = {
            "id": p["id"],
            "objet": objet,
            f"{objet}_id": p["objet_id"],
            "nom": p["nom"],
            "type_mime": p["type_mime"] or "application/octet-stream",
            "taille": origine.stat().st_size,
            "empreinte": empreinte,
            "chemin": relatif.as_posix(),
            "par_id": ctx.personne(p["par"]),
            "quand": p["quand"],
        }
        lignes.append(ctx.ligne("piece_jointe", v, p["id"]))
    return lignes
