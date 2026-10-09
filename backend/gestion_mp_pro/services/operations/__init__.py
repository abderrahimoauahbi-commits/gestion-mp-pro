"""Les opérations de stock (lot D5) : stock d'ouverture, retour des machines, transfert (dont la
mise en quarantaine et la libération), ajustement justifié, retour au fournisseur.

Brouillon (corrigeable, supprimable, sans numéro, sans effet) → validée (numérotée, écrite au
stock) → annulée (contre-passée, une fois). Modules : `droits` (la table de qui fait quoi),
`saisie` (remplir un brouillon), `blocages` (ce qui empêcherait de valider), `gestes`
(créer… annuler), `lecture` (fiche et liste). Ce module inscrit les brouillons d'opérations
dans « À valider » (`services.brouillons`).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import Operation
from gestion_mp_pro.modeles.enums import StatutDocument
from gestion_mp_pro.services import brouillons
from gestion_mp_pro.services.comptes import Acteur, libelle_role
from gestion_mp_pro.services.operations import droits, gestes, lecture
from gestion_mp_pro.services.operations.gestes import (
    RECALAGES,
    annuler,
    creer,
    modifier,
    supprimer,
    valider,
)
from gestion_mp_pro.services.operations.lecture import fiche, lister, toutes
from gestion_mp_pro.services.operations.saisie import SaisieLigne, SaisieOperation

__all__ = [
    "GENRE_BROUILLON",
    "RECALAGES",
    "SaisieLigne",
    "SaisieOperation",
    "annuler",
    "creer",
    "fiche",
    "lister",
    "modifier",
    "supprimer",
    "toutes",
    "valider",
]


REFERENCES_DU_RESUME = 2
"""Le résumé d'un brouillon cite deux références, puis « + n »."""


def _resume(o: lecture.OperationLue) -> str:
    """« Rangement · FIL-1, FIL-2 + 1 » : motif et deux premières références (S130)."""
    refs = sorted({x.reference for x in o.lignes})
    vues = refs[:REFERENCES_DU_RESUME]
    matieres = ", ".join(vues) + (f" + {len(refs) - len(vues)}" if len(refs) > len(vues) else "")
    return " · ".join(filter(None, [o.motif, matieres]))


def _valide_par(o: lecture.OperationLue) -> str:
    """« validé par la direction, responsable achats » : qui peut valider ce brouillon."""
    roles = droits.DROITS[droits.type_operation(o.type)]
    if o.liberation:
        roles = roles & droits.LIBERER
    noms = [libelle_role(r).lower() for r in sorted(roles) if r != droits.D]
    return "la direction" + "".join(f", {n}" for n in noms)


class _GenreOperation:
    """Les brouillons d'opérations dans « À valider »."""

    nom = "operation"

    def lister(self, s: Session, qui: Acteur) -> list[brouillons.Brouillon]:
        """Les opérations en brouillon, avec blocages et droit du lecteur (S130, S132)."""
        ops = list(
            s.scalars(
                select(Operation)
                .where(Operation.statut == StatutDocument.brouillon)
                .options(selectinload(Operation.lignes))
                .order_by(Operation.date, Operation.id)
            )
        )
        return [
            brouillons.Brouillon(
                genre=self.nom,
                type=o.type,
                id=o.id,
                version=o.version,
                date=o.date,
                libelle=o.type_libelle,
                resume=_resume(o),
                quantite=o.total,
                cree_par=o.cree_par,
                cree_le=o.cree_le,
                lien=f"/operations/{o.id}",
                rang=droits.RANG.get(o.type, brouillons.RANG_PAR_DEFAUT),
                peut_valider=o.peut_agir,
                raison=o.raison,
                valide_par=_valide_par(o),
                blocages=o.blocages,
            )  # fmt: skip
            for o in lecture.lire(s, ops, qui.role)
        ]

    def valider(self, s: Session, qui: Acteur, ident: int, version: int | None) -> str:
        """La validation à l'unité (route 120) ; sans version, celle de la base."""
        if version is None:
            version = lecture.charger(s, ident).version
        return gestes.valider(s, qui, ident, version).numero or ""


GENRE_BROUILLON = _GenreOperation()
brouillons.inscrire(GENRE_BROUILLON)
