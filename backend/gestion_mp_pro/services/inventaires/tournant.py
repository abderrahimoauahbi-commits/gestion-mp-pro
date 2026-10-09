"""Ce que propose l'ouverture d'un inventaire (route 125) et l'inventaire tournant (route 126 ;
REGLES S148, S149 ; `calcul.inventaire.a_compter`) : une matière se recompte selon sa classe ABC
(A tous les 30 jours, B tous les 90, C tous les 365), **magasin par magasin** (un comptage ne
vaut que pour le magasin compté) ; seul un inventaire **validé** compte (ni abandonné, ni
annulé).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import inventaire as calcul
from gestion_mp_pro.modeles import (
    Composition,
    Inventaire,
    InventaireLigne,
    Lot,
    Magasin,
    Matiere,
    RoleNomenclature,
    Solde,
)
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.services import horloge, reglages
from gestion_mp_pro.services.inventaires import perimetre as p

L = InventaireLigne


@dataclass(frozen=True)
class Choix:
    """Une valeur proposée (rôle, composition) : son identifiant et son code."""

    id: int
    code: str


@dataclass
class Defauts:
    """Route 125 : tolérance réglée, rôles et compositions qui portent du stock, cadences."""

    tolerance: float
    roles: list[Choix] = field(default_factory=list)
    compositions: list[Choix] = field(default_factory=list)
    cadence_jours: dict[str, int] = field(default_factory=dict)


def defauts(s: Session) -> Defauts:
    """Ce que propose le formulaire d'ouverture (le périmètre par famille)."""
    en_stock = (
        select(Matiere.role_id, Matiere.composition_id)
        .join(Lot, Lot.matiere_id == Matiere.id)
        .join(Solde, Solde.lot_id == Lot.id)
        .where(Solde.quantite > 0)
        .distinct()
    )
    rangs = s.execute(en_stock).all()
    roles = {r for r, _ in rangs}
    compositions = {c for _, c in rangs if c is not None}
    return Defauts(
        tolerance=reglages.nombre(s, "tolerance_inventaire"),
        roles=[
            Choix(r.id, r.code)
            for r in s.scalars(
                select(RoleNomenclature)
                .where(RoleNomenclature.id.in_(roles))
                .order_by(RoleNomenclature.code)
            )
        ],
        compositions=[
            Choix(c.id, c.code)
            for c in s.scalars(
                select(Composition)
                .where(Composition.id.in_(compositions))
                .order_by(Composition.code)
            )
        ],
        cadence_jours=dict(calcul.CADENCE_JOURS),
    )


def a_compter(s: Session, magasin_id: int | None = None) -> list[calcul.MatiereACompter]:
    """Route 126 : les matières dues au tournant, A d'abord, jamais comptées d'abord."""
    derniers = {
        (m, g): jour
        for m, g, jour in s.execute(
            select(
                InventaireLigne.matiere_id, InventaireLigne.magasin_id, func.max(Inventaire.date)
            )
            .join(Inventaire, Inventaire.id == InventaireLigne.inventaire_id)
            .where(
                Inventaire.statut == StatutInventaire.valide, InventaireLigne.compte.is_not(None)
            )
            .group_by(L.matiere_id, L.magasin_id)
        )
    }
    lineaires = set(s.scalars(select(RoleNomenclature.id).where(RoleNomenclature.lineaire)))
    codes = dict(s.execute(select(RoleNomenclature.id, RoleNomenclature.code)).all())
    stocks = [
        calcul.StockAuMagasin(
            article_id=m.id,
            reference=m.reference,
            magasin_id=g,
            quantite=float(q),
            role=codes.get(m.role_id, ""),
            kg_par_ml=float(m.densite) if m.role_id in lineaires else 0.0,
        )
        for m, g, q in s.execute(
            select(Matiere, Solde.magasin_id, func.sum(Solde.quantite))
            .join(Lot, Lot.matiere_id == Matiere.id)
            .join(Solde, Solde.lot_id == Lot.id)
            .group_by(Matiere.id, Solde.magasin_id)
            .having(func.sum(Solde.quantite) > 0)
        )
    ]
    return calcul.a_compter(
        stocks,
        classes=p.classes_abc(s),
        derniers=derniers,
        magasins=dict(s.execute(select(Magasin.id, Magasin.code)).all()),
        aujourdhui=horloge.aujourd_hui(),
        magasin_id=magasin_id,
    )
