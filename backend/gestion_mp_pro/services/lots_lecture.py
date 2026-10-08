"""Lectures des lots pour l'écran et l'atelier : référentiels utiles lus une fois (`lire`),
lots disponibles d'une matière dans l'ordre FIFO à une date, scan d'une étiquette, données des
étiquettes (REGLES S50, B78, B27, B30 ; DEFAUTS C-18).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    Fournisseur,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    RoleNomenclature,
    Solde,
)
from gestion_mp_pro.modeles.enums import TypeMagasin
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.conversions import Conditionnement, kg_et_metres

ZERO = Decimal(0)


@dataclass(frozen=True)
class MatiereLue:
    """Ce que les lectures des lots disent d'une matière."""

    id: int
    reference: str
    designation: str
    role: str
    kg_par_ml: Decimal
    fournisseur_id: int | None
    poids_bobine: Decimal
    bobines_palette: Decimal


@dataclass(frozen=True)
class Lus:
    """Matières, fournisseurs et magasins, par identifiant (quatre requêtes)."""

    matieres: dict[int, MatiereLue]
    fournisseurs: dict[int, str]
    magasins: dict[int, Magasin]


def lire(s: Session) -> Lus:
    """Les référentiels que les lectures des lots citent."""
    roles = {r.id: r for r in s.scalars(select(RoleNomenclature))}
    matieres = {
        m.id: MatiereLue(
            id=m.id,
            reference=m.reference,
            designation=m.designation,
            role=roles[m.role_id].code,
            kg_par_ml=m.densite if roles[m.role_id].lineaire else ZERO,
            fournisseur_id=m.fournisseur_id,
            poids_bobine=m.poids_bobine,
            bobines_palette=m.bobines_palette,
        )
        for m in s.scalars(select(Matiere))
    }
    return Lus(
        matieres=matieres,
        fournisseurs=dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all()),
        magasins={g.id: g for g in s.scalars(select(Magasin))},
    )


def conditionnement_lu(m: MatiereLue, poids_bobine: Decimal | None = None) -> Conditionnement:
    """Le conditionnement d'une matière lue (le poids mesuré du lot l'emporte)."""
    poids = poids_bobine if poids_bobine is not None and poids_bobine > 0 else m.poids_bobine
    return Conditionnement(m.reference, poids, m.bobines_palette, m.kg_par_ml)


Couple = tuple[int, int]
"""(lot, magasin)."""


def presents_au(s: Session, couples: set[Couple], jour: date) -> dict[Couple, Decimal]:
    """Ce que chaque lot peut donner dans chaque magasin **à la date `jour`** : ce qu'il y
    portait ce soir-là, sans jamais faire passer sous zéro ce qu'il a porté ensuite (ce qui en
    est sorti depuis est déjà parti) ; un lot entré après `jour` ne donne rien (B78, audit 2-G).
    Trois requêtes, quel que soit le nombre de lots."""
    if not couples:
        return {}
    lots = {lot for lot, _ in couples}
    soldes = {
        (lot, mag): q
        for lot, mag, q in s.execute(
            select(Solde.lot_id, Solde.magasin_id, Solde.quantite).where(Solde.lot_id.in_(lots))
        )
    }
    entres = dict(s.execute(select(Lot.id, Lot.entre_le).where(Lot.id.in_(lots))).all())
    apres: dict[Couple, list[tuple[date, Decimal]]] = defaultdict(list)
    for lot, mag, jour_effet, q in s.execute(
        select(
            Mouvement.lot_id,
            Mouvement.magasin_id,
            Mouvement.date_effet,
            func.sum(Mouvement.quantite),
        )
        .where(Mouvement.lot_id.in_(lots), Mouvement.date_effet > jour)
        .group_by(Mouvement.lot_id, Mouvement.magasin_id, Mouvement.date_effet)
    ):
        apres[(lot, mag)].append((jour_effet, q))
    resultat: dict[Couple, Decimal] = {}
    for couple in couples:
        entre = entres.get(couple[0])
        if entre is not None and entre > jour:
            resultat[couple] = ZERO
            continue
        solde = soldes.get(couple, ZERO)
        plus_bas = solde
        for _jour, q in sorted(apres.get(couple, []), reverse=True):
            solde -= q
            plus_bas = min(plus_bas, solde)
        resultat[couple] = max(ZERO, plus_bas)
    return resultat


@dataclass
class LotDisponible:
    """Un lot qu'on peut sortir d'un magasin courant, du plus ancien au plus récent (S50)."""

    lot_id: int
    lot: str
    magasin_id: int
    magasin: str
    quantite: Decimal
    entre_le: date
    poids_bobine: Decimal


def disponibles(
    s: Session, matiere_id: int, magasin_id: int | None = None, jour: date | None = None
) -> list[LotDisponible]:
    """Les lots d'une matière qui portent de la matière hors quarantaine (un magasin désactivé
    n'est pas exclu), dans l'ordre où le magasin doit les sortir (FIFO : entrée puis numéro).
    À une date passée : ce que chaque lot pouvait donner ce jour-là (`lots.presents_au`)."""
    requete = (
        select(Lot, Solde.magasin_id, Solde.quantite, Magasin.code)
        .join(Solde, Solde.lot_id == Lot.id)
        .join(Magasin, Magasin.id == Solde.magasin_id)
        .where(
            Lot.matiere_id == matiere_id,
            Solde.quantite > 0,
            Magasin.type != TypeMagasin.quarantaine,
        )
        .order_by(Lot.entre_le, Lot.id, Magasin.id)
    )
    if magasin_id is not None:
        requete = requete.where(Solde.magasin_id == magasin_id)
    lignes = [
        LotDisponible(lot.id, lot.numero, mag, code, q, lot.entre_le, lot.poids_bobine)
        for lot, mag, q, code in s.execute(requete)
    ]
    if jour is None or jour >= horloge.aujourd_hui():
        return lignes
    au = presents_au(s, {(x.lot_id, x.magasin_id) for x in lignes}, jour)
    for x in lignes:
        x.quantite = au[(x.lot_id, x.magasin_id)]
    return [x for x in lignes if x.quantite > 0]


@dataclass
class LotResume:
    """Ce qu'un scan rend : le lot, sa matière, ce qu'il porte en tout."""

    lot_id: int
    lot: str
    matiere_id: int
    reference: str
    quantite: Decimal


ADRESSE_DU_LOT = re.compile(r"/lot/(\d+)")
"""L'adresse qu'imprime l'étiquette : `…/lot/123`."""


def scan(s: Session, code: str) -> list[LotResume]:
    """Ce que lit l'appareil photo : l'adresse d'une étiquette (`…/lot/123`), ou un numéro de
    lot tapé (sans tenir compte de la casse ; un même numéro peut exister pour deux matières)."""
    trouve = ADRESSE_DU_LOT.search(code)
    requete = select(Lot, Matiere.reference).join(Matiere, Matiere.id == Lot.matiere_id)
    if trouve:
        requete = requete.where(Lot.id == int(trouve.group(1)))
    else:
        requete = requete.where(func.lower(Lot.numero) == code.strip().lower())
    lots = list(s.execute(requete.order_by(Lot.id)))
    totaux = _totaux(s, {lot.id for lot, _ in lots})
    return [
        LotResume(lot.id, lot.numero, lot.matiere_id, ref, totaux.get(lot.id, (ZERO, ZERO))[0])
        for lot, ref in lots
    ]


def _totaux(s: Session, ids: set[int]) -> dict[int, tuple[Decimal, Decimal]]:
    """Par lot : (tout ce qu'il porte, dont en quarantaine)."""
    if not ids:
        return {}
    en_quarantaine = func.coalesce(
        func.sum(Solde.quantite).filter(Magasin.type == TypeMagasin.quarantaine), 0
    )
    requete = (
        select(Solde.lot_id, func.sum(Solde.quantite), en_quarantaine)
        .join(Magasin, Magasin.id == Solde.magasin_id)
        .where(Solde.lot_id.in_(ids))
        .group_by(Solde.lot_id)
    )
    return {lot: (Decimal(t), Decimal(q)) for lot, t, q in s.execute(requete)}


@dataclass
class Etiquette:
    """Ce qu'imprime l'étiquette d'un lot (100 × 70 mm, QR = adresse `/lot/{id}`)."""

    lot_id: int
    lot: str
    reference: str
    fournisseur: str
    entre_le: date
    quantite: Decimal
    en_quarantaine: Decimal
    texte_quantite: str
    texte_quarantaine: str


@dataclass
class Etiquettes:
    """Les étiquettes demandées et les identifiants ignorés (dits en tête de page, C-18)."""

    lots: list[Etiquette] = field(default_factory=list)
    ignores: list[str] = field(default_factory=list)


def etiquettes(s: Session, ids: str) -> Etiquettes:
    """Les étiquettes des lots `1,2,3` : un identifiant inconnu est ignoré **et dit** ; un lot
    en quarantaine porte « QUARANTAINE — NE PAS SORTIR » (et « dont X en quarantaine » s'il
    n'y est qu'en partie)."""
    resultat = Etiquettes()
    voulus: list[int] = []
    for brut in (x.strip() for x in ids.split(",")):
        if brut.isdigit():
            voulus.append(int(brut))
        elif brut:
            resultat.ignores.append(brut[:20])
    lu = lire(s)
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(voulus)))}
    totaux = _totaux(s, set(lots))
    for ident in voulus:
        lot = lots.get(ident)
        if lot is None:
            resultat.ignores.append(str(ident))
            continue
        m = lu.matieres[lot.matiere_id]
        total, attente = totaux.get(lot.id, (ZERO, ZERO))
        c = conditionnement_lu(m, lot.poids_bobine)
        partiel = attente > 0 and total - attente > 0
        resultat.lots.append(
            Etiquette(
                lot_id=lot.id,
                lot=lot.numero,
                reference=m.reference,
                fournisseur=lu.fournisseurs.get(lot.fournisseur_id or m.fournisseur_id or 0, ""),
                entre_le=lot.entre_le,
                quantite=total,
                en_quarantaine=attente,
                texte_quantite=f"{kg_et_metres(total, c)} à l'impression",
                texte_quarantaine=(
                    "QUARANTAINE — NE PAS SORTIR"
                    + (f" (dont {kg_et_metres(attente, c)} en quarantaine)" if partiel else "")
                    if attente > 0
                    else ""
                ),
            )
        )
    return resultat
