"""Ce qui empêcherait de valider un brouillon d'opération, calculé **sans rien écrire**
(REGLES B.1.13, OB1–OB8), annoncé sur le brouillon et dans « À valider ».

Différences voulues avec Gestion MP : la suspension par un inventaire ne vaut que pour les
matières de son périmètre (K2) ; un ajustement en moins dans un magasin désactivé n'est pas
annoncé bloqué (C-12) ; les quantités sont au gramme (plus de seuil de poussière).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Inventaire,
    InventaireMatiere,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    Operation,
    Ordre,
    Solde,
)
from gestion_mp_pro.modeles.enums import StatutDocument, StatutInventaire, TypeOperation
from gestion_mp_pro.services import periode
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.stock_regles import couvert_a_sa_date

ZERO = Decimal(0)


@dataclass(frozen=True)
class OuvertQuiSuspend:
    """Un inventaire ouvert : son numéro, son magasin (`None` : tous), son périmètre."""

    numero: str
    magasin_id: int | None
    matieres: frozenset[int]


@dataclass
class Contexte:
    """Ce qu'il faut savoir pour lire ou juger des opérations, lu en une fois."""

    magasins: dict[int, Magasin]
    matieres: dict[int, Matiere] = field(default_factory=dict)
    lots: dict[int, Lot] = field(default_factory=dict)
    ouverts: list[OuvertQuiSuspend] = field(default_factory=list)


def contexte(s: Session, operations: Iterable[Operation]) -> Contexte:
    """Magasins, matières et lots cités, inventaires ouverts : quatre requêtes."""
    ops = list(operations)
    lignes = [x for o in ops for x in o.lignes]
    ctx = Contexte(magasins={g.id: g for g in s.scalars(select(Magasin))})
    ids_matieres = {x.matiere_id for x in lignes}
    ids_lots = {x.lot_id for x in lignes if x.lot_id is not None}
    if ids_matieres:
        ctx.matieres = {
            m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids_matieres)))
        }
    if ids_lots:
        ctx.lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(ids_lots)))}
    if any(o.statut == StatutDocument.brouillon for o in ops):
        ctx.ouverts = inventaires_ouverts(s)
    return ctx


def inventaires_ouverts(s: Session) -> list[OuvertQuiSuspend]:
    """Les inventaires ouverts et les matières qu'ils suspendent (K2)."""
    perimetres: dict[int, set[int]] = defaultdict(set)
    rangs = s.execute(
        select(InventaireMatiere.inventaire_id, InventaireMatiere.matiere_id)
        .join(Inventaire, Inventaire.id == InventaireMatiere.inventaire_id)
        .where(Inventaire.statut == StatutInventaire.ouvert)
    )
    for inventaire_id, matiere_id in rangs:
        perimetres[inventaire_id].add(matiere_id)
    return [
        OuvertQuiSuspend(i.numero, i.magasin_id, frozenset(perimetres[i.id]))
        for i in s.scalars(
            select(Inventaire).where(Inventaire.statut == StatutInventaire.ouvert)
            .order_by(Inventaire.id)
        )
    ]  # fmt: skip


def suspend(ouvert: OuvertQuiSuspend, matiere_id: int, magasin_id: int) -> bool:
    """Cet inventaire ouvert suspend-il cette matière dans ce magasin ?"""
    return (ouvert.magasin_id in (None, magasin_id)) and matiere_id in ouvert.matieres


def blocages(s: Session, o: Operation, ctx: Contexte) -> list[str]:
    """Les raisons, dans l'ordre d'apparition et sans doublon ; vide hors brouillon."""
    if o.statut != StatutDocument.brouillon:
        return []
    raisons: list[str] = [] if o.lignes else ["aucune ligne"]
    try:
        periode.date_permise(s, o.date)
    except Refus as refus:
        raisons.append(refus.detail)
    raisons += _suspensions(o, ctx)
    raisons += _manques(s, o, ctx)
    raisons += _desactives(o, ctx)
    if o.type == TypeOperation.retour_machine and o.ordre_id is not None:
        raisons += _retour_machine(s, o, ctx)
    return list(dict.fromkeys(raisons))


def _suspensions(o: Operation, ctx: Contexte) -> list[str]:
    """OB3, limité au périmètre : « l'inventaire INV-… compte « RÉF » (CODE) »."""
    raisons = []
    for x in o.lignes:
        touches = [x.magasin_id] + ([x.magasin_destination_id] if x.magasin_destination_id else [])
        for magasin_id in touches:
            for ouvert in ctx.ouverts:
                if suspend(ouvert, x.matiere_id, magasin_id):
                    g = ctx.magasins.get(ouvert.magasin_id or 0)
                    ou = g.code if g is not None else "tous les magasins"
                    ref = ctx.matieres[x.matiere_id].reference
                    raisons.append(f"l'inventaire {ouvert.numero} compte « {ref} » ({ou})")
    return raisons


def retraits(o: Operation) -> dict[tuple[int, int], Decimal]:
    """Ce que le brouillon retire de chaque (lot, magasin) : transfert et retour au
    fournisseur (leur quantité), ajustement en moins (sa valeur absolue)."""
    retire: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for x in o.lignes:
        if x.lot_id is None:
            continue
        if o.type in (TypeOperation.transfert, TypeOperation.retour_fournisseur):
            retire[(x.lot_id, x.magasin_id)] += x.quantite
        elif o.type == TypeOperation.ajustement and x.quantite < 0:
            retire[(x.lot_id, x.magasin_id)] -= x.quantite
    return retire


def _manques(s: Session, o: Operation, ctx: Contexte) -> list[str]:
    """OB4 (plus que ce que le lot porte) et OB5 (pas couvert à la date de l'opération)."""
    raisons = []
    for (lot_id, magasin_id), q in retraits(o).items():
        present = s.scalar(
            select(Solde.quantite).where(Solde.lot_id == lot_id, Solde.magasin_id == magasin_id)
        )
        present = present if present is not None else ZERO
        lot, g = ctx.lots[lot_id], ctx.magasins[magasin_id]
        if q > present:
            etat = "épuisé" if present <= 0 else f"{kg(present)} seulement"
            ref = ctx.matieres[lot.matiere_id].reference
            raisons.append(
                f"lot {lot.numero} de {ref} : {etat} dans « {g.code} », {kg(q)} demandés"
            )
            continue
        try:
            couvert_a_sa_date(s, lot, g, -q, o.date)
        except Refus as refus:
            raisons.append(refus.detail)
    return raisons


def _desactives(o: Operation, ctx: Contexte) -> list[str]:
    """OB6 : le magasin qui recevrait est désactivé (pas pour ce qui en sort, C-12)."""
    raisons = []
    for x in o.lignes:
        cible = x.magasin_destination_id if o.type == TypeOperation.transfert else x.magasin_id
        sort = o.type == TypeOperation.retour_fournisseur or (
            o.type == TypeOperation.ajustement and x.quantite < 0
        )
        g = ctx.magasins.get(cible or 0)
        if g is not None and not g.actif and not sort:
            raisons.append(f"le magasin « {g.code} » est désactivé")
    return raisons


def quantite_lisible(q: Decimal) -> str:
    """« 30,00 kg », jamais « -0 »."""
    return f"{kg(q if q > 0 else ZERO)} kg"


def rendu_face_au_sorti(
    s: Session, o: Operation, lots: dict[int, Lot]
) -> list[tuple[Lot, Decimal, Decimal]]:
    """Pour un retour des machines : chaque lot, ce que le retour en rend (deux lignes du même
    lot s'additionnent) et ce que l'ordre en a emporté, net de ce qui en est déjà revenu."""
    rendu: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for x in o.lignes:
        if x.lot_id is not None:
            rendu[x.lot_id] += x.quantite
    if not rendu:
        return []
    nets = dict(
        s.execute(
            select(Mouvement.lot_id, func.sum(Mouvement.quantite))
            .where(Mouvement.ordre_id == o.ordre_id, Mouvement.lot_id.in_(rendu))
            .group_by(Mouvement.lot_id)
        ).all()
    )
    return [(lots[lot_id], q, -(nets.get(lot_id) or ZERO)) for lot_id, q in rendu.items()]


def _retour_machine(s: Session, o: Operation, ctx: Contexte) -> list[str]:
    """OB7 (daté avant l'ordre) et OB8 (plus rendu que parti)."""
    raisons = []
    ordre = s.get(Ordre, o.ordre_id)
    if ordre is not None and o.date < ordre.date:
        raisons.append(
            f"daté du {o.date:%d/%m/%Y}, avant l'ordre {ordre.numero} du {ordre.date:%d/%m/%Y}"
        )
    for lot, rendu, sorti in rendu_face_au_sorti(s, o, ctx.lots):
        if rendu > sorti:
            raisons.append(
                f"lot {lot.numero} : seulement {quantite_lisible(sorti)} partis pour cet ordre, "
                f"{quantite_lisible(rendu)} rendus"
            )
    return raisons
