"""La marchandise libre (reçue, validée, dans aucun dossier) et les dossiers qui portent une
facture (REGLES R-IMP-15, R-IMP-18, R-IMP-28).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Dossier, DossierLigne, Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument, StatutDossier


def lignes_libres(
    s: Session,
    *,
    facture_id: int | None = None,
    factures: Iterable[int] | None = None,
    verrou: bool = False,
) -> list[tuple[ReceptionLigne, Reception]]:
    """La marchandise validée, non refusée, pesée, qui n'est encore dans aucun dossier — d'une
    facture, ou de plusieurs (R-IMP-15).

    Avec `verrou` (ouvrir, rattacher), leurs réceptions restent verrouillées en partage jusqu'à
    l'enregistrement : l'annulation d'une réception ou la correction de sa facture, qui la
    verrouillent aussi, attendent puis voient le dossier ; passées d'abord, elles retirent la
    réception de ce qui est libre (PostgreSQL relit la ligne après l'attente)."""
    prise = select(DossierLigne.id).where(DossierLigne.reception_ligne_id == ReceptionLigne.id)
    requete = (
        select(ReceptionLigne, Reception)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(
            Reception.statut == StatutDocument.validee,
            ReceptionLigne.qualite != QualiteReception.refuse,
            ReceptionLigne.quantite_pesee > 0,
            ~prise.exists(),
        )
        .order_by(Reception.date.desc(), Reception.id.desc(), ReceptionLigne.id)
    )
    if facture_id is not None:
        requete = requete.where(Reception.facture_id == facture_id)
    if factures is not None:
        requete = requete.where(Reception.facture_id.in_(set(factures)))
    if verrou:
        requete = requete.with_for_update(read=True, of=Reception)
    return [(x, r) for x, r in s.execute(requete).all()]


Porteurs = dict[int, list[tuple[int, str]]]


def porteurs(s: Session, factures: Iterable[int] | None = None) -> Porteurs:
    """Pour chaque facture, les dossiers (non annulés) qui la portent : le sien d'abord, puis
    ceux — repris de l'ERP Fil, sans facture — qui en ont une marchandise (R-IMP-18)."""
    vivant = Dossier.statut != StatutDossier.annule
    siens = select(Dossier.facture_id, Dossier.id, Dossier.numero).where(
        Dossier.facture_id.is_not(None), vivant
    )
    par_lignes = (
        select(Reception.facture_id, Dossier.id, Dossier.numero)
        .distinct()
        .select_from(DossierLigne)
        .join(Dossier, Dossier.id == DossierLigne.dossier_id)
        .join(ReceptionLigne, ReceptionLigne.id == DossierLigne.reception_ligne_id)
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .where(Reception.facture_id.is_not(None), vivant)
    )
    if factures is not None:
        voulues = set(factures)
        siens = siens.where(Dossier.facture_id.in_(voulues))
        par_lignes = par_lignes.where(Reception.facture_id.in_(voulues))
    resultat: Porteurs = defaultdict(list)
    for fid, did, numero in [*s.execute(siens), *sorted(s.execute(par_lignes), key=lambda z: z[2])]:
        if fid is not None and (did, numero) not in resultat[fid]:
            resultat[fid].append((did, numero))
    return dict(resultat)


def factures_acceptees(s: Session, d: Dossier) -> set[int]:
    """Les factures dont la suite entre dans ce dossier : la sienne ; pour un dossier repris,
    celles dont il porte déjà une marchandise ; aucune pour un dossier saisi à la main."""
    if d.facture_id:
        return {d.facture_id}
    ids = [x.reception_ligne_id for x in d.lignes if x.reception_ligne_id]
    if not ids:
        return set()
    requete = (
        select(Reception.facture_id)
        .distinct()
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .where(ReceptionLigne.id.in_(ids), Reception.facture_id.is_not(None))
    )
    return {x for x in s.scalars(requete) if x is not None}
