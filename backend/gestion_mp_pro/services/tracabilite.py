"""La traçabilité (route 112, `gestion_mp/api/pilotage.tracabilite`) : d'où vient un lot et
quels ordres il a servis, ce qu'un ordre a consommé, tout le chemin d'une matière — dans le
vocabulaire de la base (types et libellés de REGLES S4, plus de codes du moteur à émojis).

Une annulation et la ligne annulée ne comptent ni en entrée ni en sortie, un transfert non
plus ; un retour des machines réduit le sorti (S71, S72). Un même numéro de lot peut exister
pour deux matières : un lot se suit par son identifiant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.chargement import TYPE_MOTEUR
from gestion_mp_pro.calcul.lots import tracabilite as tracer
from gestion_mp_pro.calcul.modele import Mouvement as Ecriture
from gestion_mp_pro.modeles import Lot, Matiere, Mouvement, Ordre
from gestion_mp_pro.services import donnees_moteur

TYPE_DE_LA_BASE = {moteur: base for base, moteur in TYPE_MOTEUR.items()}
"""Code du moteur → type de la base."""

LIBELLES = {
    "OUVERTURE": "Stock d'ouverture",
    "RECEPTION": "Entrée de réception",
    "SORTIE": "Sortie vers les machines",
    "RETOUR_MACHINE": "Retour des machines",
    "RETOUR_FOURNISSEUR": "Retour au fournisseur",
    "AJUSTEMENT": "Ajustement d'inventaire",
    "TRANSFERT": "Transfert entre magasins",
}
"""Libellé de chaque type de mouvement (REGLES S4)."""


@dataclass
class EtapeTracee:
    """Une écriture du chemin : quantité signée (un transfert : ce qui a bougé)."""

    id: int | None
    date: date
    type: str
    libelle: str
    reference: str
    quantite: float
    lot: str
    lot_id: int | None
    matiere_id: int | None
    ordre: str
    ordre_id: int | None
    magasin_source: str
    magasin_destination: str
    utilisateur: str
    document: str
    document_type: str | None
    document_id: int | None
    annulation: bool
    annule: bool


@dataclass
class Tracabilite:
    """Le chemin de la matière et ses totaux (hors annulations et transferts)."""

    lot_id: int | None = None
    lot: str = ""
    ordre_id: int | None = None
    ordre: str = ""
    matiere_id: int | None = None
    matiere: str = ""
    references: list[str] = field(default_factory=list)
    lots: list[str] = field(default_factory=list)
    ordres: list[str] = field(default_factory=list)
    entrees: float = 0.0
    sorties: float = 0.0
    mouvements: list[EtapeTracee] = field(default_factory=list)


def _cibles(
    s: Session, lot_id: int | None, ordre_id: int | None, matiere_id: int | None
) -> tuple[Lot | None, Ordre | None, Matiere | None]:
    """Le lot, l'ordre ou la matière suivis (404 s'ils n'existent pas)."""
    if lot_id is None and ordre_id is None and matiere_id is None:
        raise Refus.saisie("Préciser un lot, un ordre de fabrication ou une matière.")
    lot = s.get(Lot, lot_id) if lot_id is not None else None
    if lot_id is not None and lot is None:
        raise Refus.introuvable("Lot introuvable.")
    ordre = s.get(Ordre, ordre_id) if ordre_id is not None else None
    if ordre_id is not None and ordre is None:
        raise Refus.introuvable("Ordre introuvable.")
    ident = lot.matiere_id if lot is not None else matiere_id
    matiere = s.get(Matiere, ident) if ident is not None else None
    if matiere_id is not None and matiere is None:
        raise Refus.introuvable("Matière introuvable.")
    return lot, ordre, matiere


@dataclass(frozen=True)
class Relu:
    """Ce que la base sait d'une écriture : lot, matière, document (genre, id, n°), ordre."""

    lot_id: int | None = None
    matiere_id: int | None = None
    document: str = ""
    document_type: str | None = None
    document_id: int | None = None
    ordre_id: int | None = None
    contrepasse_id: int | None = None


def _relire(s: Session, ids: list[int]) -> dict[int, Relu]:
    """Les écritures du chemin, relues en base (liens de l'écran : RESTES3, F2)."""
    m = Mouvement
    requete = select(m.id, m.lot_id, m.matiere_id, m.document_numero, m.document, m.reception_id,
                     m.ordre_id, m.operation_id, m.inventaire_id, m.contrepasse_id)  # fmt: skip
    relus = {}
    for i, lot, mat, numero, genre, rec, ordre, ope, inv, cp in s.execute(
        requete.where(m.id.in_(ids))
    ).all():
        ident = {"reception": rec, "ordre": ordre, "operation": ope, "inventaire": inv}.get(
            str(genre)
        )
        relus[i] = Relu(lot, mat, numero, str(genre), ident, ordre, cp)
    return relus


def _etape(x: Ecriture, base: dict[int, Relu], annules: set[int]) -> EtapeTracee:
    """Une écriture du moteur, relue avec ce que la base sait d'elle."""
    type_ = TYPE_DE_LA_BASE.get(x.type, x.type)
    r = base.get(x.id or 0, Relu())
    libelle = LIBELLES.get(type_, type_)
    annulation = r.contrepasse_id is not None
    return EtapeTracee(
        id=x.id, date=x.date, type=type_,
        libelle=f"Annulation — {libelle.lower()}" if annulation else libelle,
        reference=x.reference,
        quantite=x.quantite if type_ == "TRANSFERT" else x.quantite_signee,
        lot=x.lot_fournisseur, lot_id=r.lot_id, matiere_id=r.matiere_id, ordre=x.numero_of,
        ordre_id=r.ordre_id,
        magasin_source=x.magasin_source, magasin_destination=x.magasin_destination,
        utilisateur=x.utilisateur, document=r.document or x.reference_doc,
        document_type=r.document_type, document_id=r.document_id,
        annulation=annulation, annule=(x.id or 0) in annules,
    )  # fmt: skip


def tracabilite(
    s: Session,
    *,
    lot_id: int | None = None,
    ordre_id: int | None = None,
    matiere_id: int | None = None,
) -> Tracabilite:
    """Route 112."""
    lot, ordre, matiere = _cibles(s, lot_id, ordre_id, matiere_id)
    brut = tracer(
        donnees_moteur.charger(s),
        lot=lot.numero if lot is not None else "",
        ordre=(ordre.numero or "") if ordre is not None else "",
        reference=matiere.reference if matiere is not None and lot is None else "",
    )
    ecritures = brut.mouvements
    if lot is not None and matiere is not None:
        ecritures = [x for x in ecritures if x.reference == matiere.reference]
    base = _relire(s, [x.id for x in ecritures if x.id is not None])
    annules = {r.contrepasse_id for r in base.values() if r.contrepasse_id is not None}
    etapes = [_etape(x, base, annules) for x in ecritures]
    comptes = [
        (x, e) for x, e in zip(ecritures, etapes, strict=True)
        if not e.annulation and not e.annule and e.type != "TRANSFERT"
    ]  # fmt: skip
    return Tracabilite(
        lot_id=lot.id if lot is not None else None,
        lot=brut.lot,
        ordre_id=ordre.id if ordre is not None else None,
        ordre=brut.ordre,
        matiere_id=matiere.id if matiere is not None else None,
        matiere=matiere.reference if matiere is not None else "",
        references=sorted({x.reference for x in ecritures}),
        lots=sorted({x.lot_fournisseur for x in ecritures if x.lot_fournisseur}),
        ordres=sorted({x.numero_of for x, _ in comptes if x.numero_of}),
        entrees=sum(
            x.quantite_signee for x, e in comptes
            if x.quantite_signee > 0 and e.type != "RETOUR_MACHINE"
        ),
        sorties=-sum(
            x.quantite_signee for x, e in comptes
            if x.quantite_signee < 0 or e.type == "RETOUR_MACHINE"
        ),
        mouvements=etapes,
    )  # fmt: skip
