"""La fiche d'un lot (routes 108, 109 ; REGLES S67) : d'où il vient, où il est, ce qu'il a
vécu ; son commentaire se modifie (direction, achats) et a un historique.

Le lot n'a pas de colonne `version` (MODELE-DONNEES § 3.3.1) : sa version est le nombre de
lignes de son journal, plus un. Deux postes qui modifient le même commentaire : le second
reçoit 409 `conflit_version`, qui nomme l'auteur de la version courante (API-PRO § 0.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Facture, Journal, Lot, Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import ObjetJournal, StatutDocument
from gestion_mp_pro.services import audit
from gestion_mp_pro.services.lots import LotSolde, ligne_du_lot
from gestion_mp_pro.services.mouvements import FiltresMouvements, LigneMouvement, tous


@dataclass
class ReceptionDuLot:
    """La première réception validée qui a fait entrer le lot."""

    id: int
    numero: str
    date: date
    bl: str
    facture: str
    pesee: float
    qualite: str


@dataclass
class LotFiche:
    """Tout d'un lot : sa ligne (soldes, statut, histoire), sa réception, son journal."""

    ligne: LotSolde
    poids_bobine_le: date | None
    commentaire: str
    reception: ReceptionDuLot | None
    mouvements: list[LigneMouvement]
    version: int


def _lot(s: Session, lot_id: int) -> Lot:
    """Le lot, ou 404 « Lot introuvable. » (SR14)."""
    lot = s.get(Lot, lot_id)
    if lot is None:
        raise Refus.introuvable("Lot introuvable.")
    return lot


def version(s: Session, lot_id: int) -> int:
    """La version d'un lot : 1 + le nombre de lignes de son journal."""
    lignes = s.scalar(
        select(func.count())
        .select_from(Journal)
        .where(Journal.objet == ObjetJournal.lot, Journal.objet_id == lot_id)
    )
    return 1 + (lignes or 0)


def _reception(s: Session, lot_id: int) -> ReceptionDuLot | None:
    rang = s.execute(
        select(Reception, ReceptionLigne, Facture.numero)
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .outerjoin(Facture, Facture.id == Reception.facture_id)
        .where(ReceptionLigne.lot_id == lot_id, Reception.statut == StatutDocument.validee)
        .order_by(Reception.date, Reception.id)
        .limit(1)
    ).first()
    if rang is None:
        return None
    r, ligne, facture = rang
    return ReceptionDuLot(
        r.id, r.numero or "", r.date, r.numero_bl, facture or "", float(ligne.quantite_pesee),
        str(ligne.qualite),
    )  # fmt: skip


def fiche(s: Session, lot_id: int) -> LotFiche:
    """Route 108 : le journal du lot du plus ancien au plus récent."""
    lot = _lot(s, lot_id)
    journal = tous(s, FiltresMouvements(lot_id=lot.id), avec_valeur=False)
    return LotFiche(
        ligne=ligne_du_lot(s, lot),
        poids_bobine_le=lot.poids_bobine_le,
        commentaire=lot.commentaire,
        reception=_reception(s, lot.id),
        mouvements=list(reversed(journal)),
        version=version(s, lot.id),
    )


def modifier_commentaire(
    s: Session, qui: audit.Qui, lot_id: int, commentaire: str, version_lue: int
) -> LotFiche:
    """Route 109 : le commentaire du lot (journal avant/après) ; 409 si la fiche a changé."""
    lot = s.scalars(select(Lot).where(Lot.id == lot_id).with_for_update()).first()
    if lot is None:
        raise Refus.introuvable("Lot introuvable.")
    if version(s, lot.id) != version_lue:
        ligne = audit.derniere_ligne(s, ObjetJournal.lot, lot.id)
        nom = ligne.utilisateur_nom if ligne is not None else "un autre poste"
        heure = audit.horodatage(ligne.quand) if ligne is not None else "à l'instant"
        raise Refus.etat(
            f"Ce lot a été modifié entre-temps par {nom} ({heure}) : rouvrez-le pour repartir "
            "de sa dernière version.",
            code="conflit_version",
        )
    if commentaire != lot.commentaire:
        with audit.suivre(s, qui, "commentaire du lot", lot, numero=lot.numero):
            lot.commentaire = commentaire
        s.flush()
    return fiche(s, lot.id)
