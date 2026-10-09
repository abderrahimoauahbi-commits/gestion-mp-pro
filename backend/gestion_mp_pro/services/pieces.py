"""Les pièces jointes (routes 224–227) : déposer, lister, relire, retirer.

- Un fichier par dépôt, rangé sous le dossier des pièces de **cette** base
  (`<GESTIONMPPRO_PIECES>/<base>/<objet>/<id>/<nom aléatoire><extension>`), son chemin gardé
  relatif ; le nom d'origine ne sert jamais à écrire sur le disque (aucune traversée de chemin).
- Ce qui entre : la liste blanche de `pieces_types` (type, extension, premiers octets ; aucun
  programme) ; lu **par blocs**, refusé dès qu'il passe 20 Mo, sans rien laisser sur le disque
  (G-10) ; vide refusé ; empreinte SHA-256 gardée.
- Relire : `attachment` (jamais affiché dans la page) ; une pièce retirée ou inconnue : 404 ; un
  fichier disparu du disque : 410 « … la redéposer » (G-10).
- Retirer est logique (`retiree_le`, `retiree_par_id`) : le fichier et la ligne restent, le
  journal le dit (« pièce retirée »).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles import (
    Commande,
    Dossier,
    Fournisseur,
    Inventaire,
    Matiere,
    PieceJointe,
    Reception,
    Reclamation,
    Utilisateur,
)
from gestion_mp_pro.modeles.base import Base
from gestion_mp_pro.modeles.enums import ObjetJournal, ObjetPiece
from gestion_mp_pro.modeles.suivi import TAILLE_MAXIMALE_PIECE
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services.pieces_types import nom_sur, type_retenu, verifier_tete

BLOC = 1024 * 1024
"""On lit le fichier par blocs d'un Mo : un fichier trop lourd n'est jamais chargé en mémoire."""
MODELES: dict[ObjetPiece, type[Base]] = {
    ObjetPiece.dossier: Dossier,
    ObjetPiece.reception: Reception,
    ObjetPiece.commande: Commande,
    ObjetPiece.reclamation: Reclamation,
    ObjetPiece.inventaire: Inventaire,
    ObjetPiece.fournisseur: Fournisseur,
    ObjetPiece.matiere: Matiere,
}
TROP_LOURD = "Fichier trop lourd (20 Mo au plus)."
DISPARU = "Le fichier de cette pièce a disparu du disque : la redéposer."


def dossier() -> Path:
    """Le dossier des pièces de cette base."""
    return reglages().dossier_pieces


def _objet(s: Session, objet: str, ident: int) -> ObjetPiece:
    """L'objet d'une pièce et sa fiche, ou 404 « Document inconnu. »."""
    try:
        genre = ObjetPiece(objet)
    except ValueError:
        raise Refus.introuvable("Document inconnu.") from None
    if s.get(MODELES[genre], ident) is None:
        raise Refus.introuvable("Document inconnu.")
    return genre


def lister(s: Session, objet: str, ident: int) -> list[PieceJointe]:
    """Route 224 : les pièces non retirées d'un document, la plus ancienne d'abord."""
    genre = _objet(s, objet, ident)
    colonne = getattr(PieceJointe, f"{genre.value}_id")
    requete = select(PieceJointe).where(colonne == ident, PieceJointe.retiree_le.is_(None))
    return list(s.scalars(requete.order_by(PieceJointe.id)))


def _copier(source: BinaryIO, nom: str, genre: str, extension: str, cible: Path) -> tuple[int, str]:
    """Copie par blocs dans `cible` (via un fichier partiel), rend (taille, empreinte) ; refuse
    un programme, un contenu d'un autre type, un fichier vide, au-delà de 20 Mo."""
    cible.parent.mkdir(parents=True, exist_ok=True)
    partiel = cible.with_name(f".{cible.name}.partiel")
    taille, empreinte = 0, hashlib.sha256()
    try:
        with partiel.open("wb") as sortie:
            while bloc := source.read(BLOC):
                if taille == 0:
                    verifier_tete(nom, genre, extension, bloc[:64])
                taille += len(bloc)
                if taille > TAILLE_MAXIMALE_PIECE:
                    raise Refus.saisie(TROP_LOURD, code="fichier_trop_gros")
                empreinte.update(bloc)
                sortie.write(bloc)
        if taille == 0:
            raise Refus.saisie("Fichier vide : rien à joindre.", code="fichier_refuse")
        partiel.replace(cible)
    finally:
        partiel.unlink(missing_ok=True)
    return taille, empreinte.hexdigest()


def deposer(
    s: Session,
    qui: audit.Qui,
    objet: str,
    ident: int,
    *,
    nom: str | None,
    declare: str | None,
    source: BinaryIO,
) -> PieceJointe:
    """Route 225 : joint un fichier au document (journal « pièce jointe »)."""
    genre_objet = _objet(s, objet, ident)
    propre = nom_sur(nom)
    genre, extension = type_retenu(propre, declare)
    relatif = Path(genre_objet.value) / str(ident) / f"{uuid.uuid4().hex}{extension}"
    taille, empreinte = _copier(source, propre, genre, extension, dossier() / relatif)
    p = PieceJointe(
        objet=genre_objet,
        nom=propre,
        type_mime=genre,
        taille=taille,
        empreinte=empreinte,
        chemin=relatif.as_posix(),
        par_id=qui.id,
        quand=horloge.maintenant(),
        **{f"{genre_objet.value}_id": ident},
    )
    s.add(p)
    s.flush()
    audit.journal(
        s,
        qui,
        "pièce jointe",
        ObjetJournal(genre_objet.value),
        ident,
        detail=f"{propre} ({taille} o)",
    )
    return p


def _piece(s: Session, ident: int) -> PieceJointe:
    p = s.get(PieceJointe, ident)
    if p is None:
        raise Refus.introuvable("Pièce introuvable.")
    return p


def fichier(s: Session, ident: int) -> tuple[PieceJointe, Path]:
    """Route 226 : la pièce et son fichier (retirée : 404 ; disparu du disque : 410)."""
    p = _piece(s, ident)
    if p.retiree_le is not None:
        raise Refus.introuvable("Pièce introuvable : elle a été retirée.")
    racine = dossier().resolve()
    chemin = (racine / p.chemin).resolve()
    if not chemin.is_relative_to(racine) or not chemin.is_file():
        raise Refus("fichier_disparu", DISPARU)
    return p, chemin


def retirer(s: Session, qui: audit.Qui, ident: int) -> None:
    """Route 227 : retrait logique (le fichier reste sur le disque ; journal « pièce retirée »)."""
    p = s.scalars(select(PieceJointe).where(PieceJointe.id == ident).with_for_update()).first()
    if p is None:
        raise Refus.introuvable("Pièce introuvable.")
    if p.retiree_le is not None:
        raise Refus.etat("Cette pièce est déjà retirée.", code="deja_annule")
    p.retiree_le, p.retiree_par_id = horloge.maintenant(), qui.id
    s.flush()
    audit.journal(s, qui, "pièce retirée", ObjetJournal(p.objet.value), _objet_id(p), detail=p.nom)


def _objet_id(p: PieceJointe) -> int | None:
    ident = getattr(p, f"{p.objet.value}_id")
    return ident if isinstance(ident, int) else None


@dataclass
class PieceLue:
    """Une pièce telle que l'écran la liste."""

    id: int
    objet: str
    objet_id: int | None
    nom: str
    type: str
    taille: int
    empreinte: str
    par: str
    par_id: int | None
    quand: datetime


def fiches(s: Session, liste: list[PieceJointe]) -> list[PieceLue]:
    """Les pièces avec le nom de qui les a jointes."""
    ids = {p.par_id for p in liste if p.par_id is not None}
    noms = dict(
        s.execute(select(Utilisateur.id, Utilisateur.nom).where(Utilisateur.id.in_(ids))).all()
    )
    return [
        PieceLue(
            id=p.id,
            objet=p.objet.value,
            objet_id=_objet_id(p),
            nom=p.nom,
            type=p.type_mime,
            taille=p.taille,
            empreinte=p.empreinte,
            par=noms.get(p.par_id, "") if p.par_id else "",
            par_id=p.par_id,
            quand=p.quand,
        )
        for p in liste
    ]
