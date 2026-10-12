"""La liste des factures des fournisseurs (route 175, `GET /factures`) : chacune avec ses
réceptions, ce qu'elles ont apporté (pesée × prix, son montant tant qu'il n'est pas saisi), et le
dossier d'importation qui la porte. `sans_dossier` : celles qu'aucun dossier ne porte encore —
le lot D7 ouvre le dossier d'une facture ; une facture n'est que dans un seul dossier, un
dossier en porte une ou plusieurs (décision du 12/10/2026, qui amende I3).
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    Dossier,
    DossierFacture,
    Facture,
    Fournisseur,
    Reception,
    ReceptionLigne,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument, StatutDossier
from gestion_mp_pro.services import numerotation
from gestion_mp_pro.services.recherche import trouve


@dataclass(frozen=True)
class FiltresFactures:
    """`?fournisseur=&q=&sans_dossier=`."""

    fournisseur: int | None = None
    q: str = ""
    sans_dossier: bool = False


@dataclass
class ReceptionDeFacture:
    """Une réception qui porte la facture."""

    id: int
    numero: str
    statut: str
    date: dt.date


@dataclass
class DossierDeFacture:
    """Le dossier d'importation qui porte la facture."""

    id: int
    numero: str
    statut: str


@dataclass
class FactureResume:
    """Une facture dans la liste."""

    id: int
    fournisseur_id: int
    fournisseur: str
    numero: str
    date: dt.date | None
    montant: Decimal | None
    devise: str
    echeance: dt.date | None
    payee_le: dt.date | None
    payee_par: str
    montant_estime: Decimal
    poids: Decimal
    recue_le: dt.date | None
    receptions: list[ReceptionDeFacture] = field(default_factory=list)
    dossier: DossierDeFacture | None = None
    version: int = 1


@dataclass
class _Apport:
    """Ce que les réceptions validées d'une facture ont apporté."""

    valeur: Decimal = Decimal(0)
    poids: Decimal = Decimal(0)


def _apports(s: Session, fids: set[int]) -> dict[int, _Apport]:
    """Σ pesée × prix et Σ pesée des lignes acceptées des réceptions validées, par facture."""
    apports: dict[int, _Apport] = defaultdict(_Apport)
    requete = (
        select(Reception.facture_id, ReceptionLigne.quantite_pesee, ReceptionLigne.prix)
        .join(ReceptionLigne, ReceptionLigne.reception_id == Reception.id)
        .where(
            Reception.facture_id.in_(fids),
            Reception.statut == StatutDocument.validee,
            ReceptionLigne.qualite != QualiteReception.refuse,
        )
    )
    for fid, pese, prix in s.execute(requete):
        if fid is not None:
            apports[fid].valeur += pese * prix
            apports[fid].poids += pese
    return apports


def lister(s: Session, f: FiltresFactures) -> list[FactureResume]:
    """Route 175 : les factures, la plus récente d'abord (date, sinon première réception)."""
    requete = select(Facture)
    if f.fournisseur is not None:
        requete = requete.where(Facture.fournisseur_id == f.fournisseur)
    toutes = list(s.scalars(requete))
    fids = {x.id for x in toutes}
    if not fids:
        return []
    noms = dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all())
    personnes = dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all())
    receptions: dict[int, list[ReceptionDeFacture]] = defaultdict(list)
    for r in s.scalars(
        select(Reception).where(Reception.facture_id.in_(fids)).order_by(Reception.date)
    ):
        nom = r.numero or numerotation.libelle_brouillon(r.id)
        receptions[r.facture_id or 0].append(ReceptionDeFacture(r.id, nom, str(r.statut), r.date))
    dossiers = {
        fid: DossierDeFacture(d.id, d.numero, str(d.statut))
        for fid, d in s.execute(
            select(DossierFacture.facture_id, Dossier)
            .join(Dossier, Dossier.id == DossierFacture.dossier_id)
            .where(
                DossierFacture.facture_id.in_(fids),
                DossierFacture.liberee_le.is_(None),
                Dossier.statut != StatutDossier.annule,
            )
        )
    }
    apports = _apports(s, fids)
    resultat = [
        _resume(x, noms, personnes, receptions[x.id], dossiers.get(x.id), apports.get(x.id))
        for x in toutes
    ]
    resultat = [x for x in resultat if _passe(x, f)]
    resultat.sort(key=lambda x: (x.date or x.recue_le or dt.date.min, x.id), reverse=True)
    return resultat


def _resume(  # noqa: PLR0917 — les morceaux lus en une fois par la liste
    x: Facture,
    noms: dict[int, str],
    personnes: dict[int, str],
    receptions: list[ReceptionDeFacture],
    dossier: DossierDeFacture | None,
    apport: _Apport | None,
) -> FactureResume:
    """Le résumé d'une facture."""
    apport = apport or _Apport()
    return FactureResume(
        x.id, x.fournisseur_id, noms.get(x.fournisseur_id, ""), x.numero, x.date, x.montant,
        x.devise, x.echeance, x.payee_le, personnes.get(x.payee_par_id or 0, ""),
        apport.valeur.quantize(Decimal("0.01")), apport.poids,
        receptions[0].date if receptions else None, receptions, dossier, x.version,
    )  # fmt: skip


def _passe(x: FactureResume, f: FiltresFactures) -> bool:
    """Recherche multi-mots (n°, fournisseur, réceptions) et « sans dossier »."""
    if f.sans_dossier and x.dossier is not None:
        return False
    return trouve(f.q, x.numero, x.fournisseur, *(r.numero for r in x.receptions))
