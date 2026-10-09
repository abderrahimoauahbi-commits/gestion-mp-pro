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
    ordre: str
    magasin_source: str
    magasin_destination: str
    utilisateur: str
    document: str
    annulation: bool
    annule: bool


@dataclass
class Tracabilite:
    """Le chemin de la matière et ses totaux (hors annulations et transferts)."""

    lot_id: int | None = None
    lot: str = ""
    ordre: str = ""
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


def _etape(
    x: Ecriture, base: dict[int, tuple[int, str, int | None]], annules: set[int]
) -> EtapeTracee:
    """Une écriture du moteur, relue avec ce que la base sait d'elle."""
    type_ = TYPE_DE_LA_BASE.get(x.type, x.type)
    lot_id, document, contrepasse = base.get(x.id or 0, (None, x.reference_doc, None))
    libelle = LIBELLES.get(type_, type_)
    annulation = contrepasse is not None
    return EtapeTracee(
        id=x.id, date=x.date, type=type_,
        libelle=f"Annulation — {libelle.lower()}" if annulation else libelle,
        reference=x.reference,
        quantite=x.quantite if type_ == "TRANSFERT" else x.quantite_signee,
        lot=x.lot_fournisseur, lot_id=lot_id, ordre=x.numero_of,
        magasin_source=x.magasin_source, magasin_destination=x.magasin_destination,
        utilisateur=x.utilisateur, document=document or x.reference_doc,
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
    ids = [x.id for x in ecritures if x.id is not None]
    base: dict[int, tuple[int, str, int | None]] = {
        i: (lot_, doc, cp)
        for i, lot_, doc, cp in s.execute(
            select(
                Mouvement.id, Mouvement.lot_id, Mouvement.document_numero, Mouvement.contrepasse_id
            ).where(Mouvement.id.in_(ids))
        ).all()
    }
    annules = {cp for _, _, cp in base.values() if cp is not None}
    etapes = [_etape(x, base, annules) for x in ecritures]
    comptes = [
        (x, e) for x, e in zip(ecritures, etapes, strict=True)
        if not e.annulation and not e.annule and e.type != "TRANSFERT"
    ]  # fmt: skip
    return Tracabilite(
        lot_id=lot.id if lot is not None else None,
        lot=brut.lot,
        ordre=brut.ordre,
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
