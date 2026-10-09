"""La liste des réclamations (route 181) et la fiche d'une réclamation (182) : la matière en
cause est celle du lot, sinon celle de la ligne (une ligne refusée n'a pas de lot, A-10) ; la
durée court jusqu'à la clôture (ECRANS-PRO § 4.22–4.24). Lecture groupée.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Fournisseur,
    Lot,
    Matiere,
    Reception,
    ReceptionLigne,
    Reclamation,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import IssueReclamation, MotifReclamation
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import horloge, numerotation
from gestion_mp_pro.services.referentiels import ISSUES_RECLAMATION, MOTIFS_RECLAMATION


@dataclass(frozen=True)
class FiltresReclamations:
    """`?statut=ouverte|close&fournisseur=&reception=&q=`."""

    statut: str = ""
    fournisseur: int | None = None
    reception: int | None = None
    q: str = ""


@dataclass
class ReclamationResume:
    """Une réclamation."""

    id: int
    numero: str
    statut: str
    fournisseur_id: int
    fournisseur: str
    reception_id: int | None
    reception: str
    reception_date: dt.date | None
    numero_bl: str
    reception_ligne_id: int | None
    lot_id: int | None
    lot: str
    matiere_id: int | None
    reference: str
    pese: Decimal | None
    motif: str
    motif_libelle: str
    description: str
    quantite: Decimal
    montant_demande: Decimal
    devise: str
    reponse: str
    issue: str | None
    issue_libelle: str
    montant_obtenu: Decimal
    ouverte_le: dt.date
    close_le: dt.date | None
    jours: int
    cree_par: str
    version: int


@dataclass
class _Lus:
    """Fournisseurs, réceptions, lignes, lots, matières et personnes, lus une fois."""

    fournisseurs: dict[int, str]
    receptions: dict[int, Reception]
    lignes: dict[int, ReceptionLigne]
    lots: dict[int, Lot]
    references: dict[int, str]
    personnes: dict[int, str]


def _lire(s: Session, liste: list[Reclamation]) -> _Lus:
    """Les fiches citées par ces réclamations."""
    rids = {x.reception_id for x in liste if x.reception_id}
    lids = {x.reception_ligne_id for x in liste if x.reception_ligne_id}
    lots = {x.lot_id for x in liste if x.lot_id}
    return _Lus(
        dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all()),
        {r.id: r for r in s.scalars(select(Reception).where(Reception.id.in_(rids)))},
        {x.id: x for x in s.scalars(select(ReceptionLigne).where(ReceptionLigne.id.in_(lids)))},
        {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(lots)))},
        dict(s.execute(select(Matiere.id, Matiere.reference)).all()),
        dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
    )


def _resume(x: Reclamation, lu: _Lus) -> ReclamationResume:
    """Le résumé d'une réclamation."""
    r = lu.receptions.get(x.reception_id) if x.reception_id else None
    ligne = lu.lignes.get(x.reception_ligne_id) if x.reception_ligne_id else None
    lot = lu.lots.get(x.lot_id) if x.lot_id else None
    matiere = lot.matiere_id if lot else ligne.matiere_id if ligne else None
    fin = x.close_le or horloge.aujourd_hui()
    issue = IssueReclamation(x.issue) if x.issue else None
    return ReclamationResume(
        x.id, x.numero, str(x.statut), x.fournisseur_id, lu.fournisseurs.get(x.fournisseur_id, ""),
        x.reception_id, (r.numero or numerotation.libelle_brouillon(r.id)) if r else "",
        r.date if r else None, r.numero_bl if r else "", x.reception_ligne_id, x.lot_id,
        lot.numero if lot else (ligne.lot_numero if ligne else ""), matiere,
        lu.references.get(matiere, "") if matiere else "",
        ligne.quantite_pesee if ligne else None, str(x.motif),
        MOTIFS_RECLAMATION[MotifReclamation(x.motif)], x.description, x.quantite,
        x.montant_demande, x.devise, x.reponse, str(issue) if issue else None,
        ISSUES_RECLAMATION[issue] if issue else "", x.montant_obtenu, x.ouverte_le, x.close_le,
        (fin - x.ouverte_le).days, lu.personnes.get(x.cree_par_id or 0, ""), x.version,
    )  # fmt: skip


def _passe(x: ReclamationResume, f: FiltresReclamations) -> bool:
    """Statut, fournisseur, réception, recherche multi-mots sans accents."""
    if f.statut and x.statut != f.statut:
        return False
    if f.fournisseur is not None and x.fournisseur_id != f.fournisseur:
        return False
    if f.reception is not None and x.reception_id != f.reception:
        return False
    texte = normaliser(
        " ".join([x.numero, x.fournisseur, x.reception, x.lot, x.reference, x.motif_libelle,
                  x.description, x.issue_libelle, x.reponse])
    )  # fmt: skip
    return all(m in texte for m in normaliser(f.q).split())


def liste(s: Session, f: FiltresReclamations) -> list[ReclamationResume]:
    """Route 181 : les réclamations, la plus récente d'abord."""
    s.flush()
    toutes = list(s.scalars(select(Reclamation).order_by(Reclamation.id.desc())))
    lu = _lire(s, toutes)
    return [r for r in (_resume(x, lu) for x in toutes) if _passe(r, f)]


def fiche(s: Session, rid: int) -> ReclamationResume:
    """Route 182 : la fiche d'une réclamation."""
    s.flush()
    x = s.get(Reclamation, rid, populate_existing=True)
    if x is None:
        raise Refus.introuvable("Réclamation introuvable.")
    return _resume(x, _lire(s, [x]))
