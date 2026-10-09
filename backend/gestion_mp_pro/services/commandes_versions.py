"""La version partie d'un bon (ce que le fournisseur a entre les mains), pour la fiche 153.

Sortie de `commandes_fiche` (plafond de 400 lignes, RESTES3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import CommandeVersion, Matiere


@dataclass
class LigneVersion:
    """Une ligne de la version partie."""

    matiere_id: int
    reference: str
    quantite: float
    unite_achat: str
    contenance: float
    prix: float
    prix_confirme: bool


@dataclass
class VersionPartie:
    """Ce que le fournisseur a entre les mains, et le montant auquel une hausse se mesure."""

    figee_le: datetime
    motif: str
    montant_reference: float
    lignes: list[LigneVersion]


def version_partie(s: Session, cid: int) -> VersionPartie | None:
    """La dernière version partie, lisible (références)."""
    v = s.scalars(
        select(CommandeVersion)
        .where(CommandeVersion.commande_id == cid)
        .options(selectinload(CommandeVersion.lignes))
        .order_by(CommandeVersion.figee_le.desc(), CommandeVersion.id.desc())
        .limit(1)
    ).first()
    if v is None:
        return None
    ids = [x.matiere_id for x in v.lignes]
    refs = dict(s.execute(select(Matiere.id, Matiere.reference).where(Matiere.id.in_(ids))).all())
    return VersionPartie(
        v.figee_le,
        str(v.motif),
        float(v.montant_reference),
        [
            LigneVersion(
                x.matiere_id,
                refs.get(x.matiere_id, ""),
                float(x.quantite),
                x.unite_achat,
                float(x.contenance),
                float(x.prix),
                x.prix_confirme,
            )
            for x in v.lignes
        ],  # fmt: skip
    )
