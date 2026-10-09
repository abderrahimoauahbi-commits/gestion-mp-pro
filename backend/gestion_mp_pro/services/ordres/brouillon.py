"""Les brouillons d'ordres dans « À valider » et « Tout valider » (lot D5, `services.brouillons` ;
REGLES B.1.15 ; API-PRO 122, 123).

Un ordre se valide par la direction ou l'alimentation ; le même jour, il passe après ce qui
apporte la matière (rang 3). « Tout valider » appelle la **même** validation qu'à l'unité,
dans un point de reprise par document.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Ordre
from gestion_mp_pro.modeles.enums import Role, StatutOrdre
from gestion_mp_pro.services import brouillons
from gestion_mp_pro.services.comptes import Acteur, libelle_role, message_refus
from gestion_mp_pro.services.operations.droits import RANG
from gestion_mp_pro.services.ordres import gestes, lecture

VALIDENT = frozenset({Role.direction, Role.alimentation})
"""Qui valide un ordre de fabrication."""

LIBELLE = "Ordre de fabrication"
REFERENCES_DU_RESUME = 2


def _resume(x: lecture.OrdreLu) -> str:
    """« E1 10 m² · FIL-1, FIL-2 + 1 » : ce qu'on tisse et deux premières matières."""
    vues = x.matieres[:REFERENCES_DU_RESUME]
    reste = len(x.matieres) - len(vues)
    matieres = ", ".join(vues) + (f" + {reste}" if reste else "")
    return " · ".join(filter(None, [x.fabrication, matieres]))


class _GenreOrdre:
    """Les brouillons d'ordres dans « À valider »."""

    nom = "ordre"

    def lister(self, s: Session, qui: Acteur) -> list[brouillons.Brouillon]:
        """Les ordres en brouillon, avec blocages et droit du lecteur (S130, S132)."""
        ordres = list(
            s.scalars(
                select(Ordre)
                .where(Ordre.statut == StatutOrdre.brouillon)
                .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
                .order_by(Ordre.date, Ordre.id)
            )
        )
        if not ordres:
            return []
        ctx = lecture.contexte(s, ordres)
        peut = qui.role in VALIDENT
        return [
            brouillons.Brouillon(
                genre=self.nom,
                type=self.nom,
                id=x.id,
                version=x.version,
                date=x.date,
                libelle=LIBELLE,
                resume=_resume(x),
                quantite=x.total,
                cree_par=x.cree_par,
                cree_le=x.cree_le,
                lien=f"/ordres/{x.id}",
                rang=RANG[self.nom],
                peut_valider=peut,
                raison="" if peut else message_refus(VALIDENT),
                valide_par="la direction, " + libelle_role(Role.alimentation).lower(),
                blocages=x.blocages,
            )  # fmt: skip
            for x in (lecture.lire_un(s, o, ctx) for o in ordres)
        ]

    def valider(self, s: Session, qui: Acteur, ident: int, version: int | None) -> str:
        """La validation à l'unité (route 140) ; sans version, celle de la base."""
        if qui.role not in VALIDENT:
            raise Refus.droit(message_refus(VALIDENT))
        if version is None:
            version = gestes.charger(s, ident).version
        return gestes.valider(s, qui, ident, version).numero or ""


GENRE_BROUILLON = _GenreOrdre()
brouillons.inscrire(GENRE_BROUILLON)
