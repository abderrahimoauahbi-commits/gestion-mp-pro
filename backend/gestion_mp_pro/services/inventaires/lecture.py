"""Lire les inventaires : fiche (périmètre, lignes, écarts en kilos **et** en dirhams,
recomptages « à quatre yeux » signalés, blocages), liste, valeurs proposées à l'ouverture,
inventaire tournant (REGLES S144–S149 ; API-PRO 124–127). Les calculs sont ceux de
`calcul.inventaire` ; les montants portent des noms du filtre des prix (`*_mad`) : l'alimentation
les reçoit à `null`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import inventaire as calcul
from gestion_mp_pro.modeles import (
    Composition,
    Inventaire,
    InventaireLigne,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    RoleNomenclature,
)
from gestion_mp_pro.modeles.enums import CritereInventaire, DocumentMouvement, StatutInventaire
from gestion_mp_pro.services import donnees_moteur, periode
from gestion_mp_pro.services.inventaires import perimetre as p
from gestion_mp_pro.services.inventaires.document import (
    JUSTIFICATION_MINIMUM,
    charger,
    ligne_de_calcul,
    noms_des_personnes,
    retenu,
    sans_justification,
)

TOUS_LES_MAGASINS = "Tous les magasins"
CITEES = 8
"""Un refus cite au plus 8 références."""


@dataclass
class LigneLue:
    """Une ligne d'inventaire telle que le comptage la montre."""

    id: int
    lot_id: int | None
    lot: str
    lot_interne: bool
    lot_trouve: bool
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Decimal
    poids_bobine: Decimal
    bobines_palette: Decimal
    magasin_id: int
    magasin: str
    theorique: Decimal
    compte: Decimal | None
    palettes: Decimal | None
    bobines: Decimal | None
    compte_par: str
    second_compte: Decimal | None
    second_par: str
    quatre_yeux: str
    retenu: Decimal | None
    ecart: Decimal | None
    ecart_pourcent: float | None
    cmup_mad: float
    valeur_ecart_mad: float | None
    hors_tolerance: bool
    a_recompter: bool
    justification: str


@dataclass
class CriteresLus:
    """Les critères du périmètre, tels qu'ils ont été choisis."""

    matieres: list[int] = field(default_factory=list)
    roles: list[int] = field(default_factory=list)
    compositions: list[int] = field(default_factory=list)
    classes_abc: list[str] = field(default_factory=list)


@dataclass
class InventaireLu:
    """Un inventaire : en-tête, périmètre, totaux, blocages ; lignes dans la fiche seulement."""

    id: int
    numero: str
    libelle: str
    statut: str
    date: date
    magasin_id: int | None
    magasin: str
    tolerance: Decimal
    perimetre: str
    criteres: CriteresLus
    nb_matieres_suspendues: int
    cree_par: str
    cree_le: datetime
    valide_par: str
    valide_le: datetime | None
    abandonne_par: str
    abandonne_le: datetime | None
    annule_par: str
    annule_le: datetime | None
    annulation_motif: str
    nb_lignes: int
    nb_comptees: int
    hors_tolerance: int
    sans_justification: int
    a_recompter: int
    recomptees: int
    recomptes_meme_personne: int
    ecart_total: float
    ecart_absolu: float
    ecart_valeur_mad: float
    ecart_valeur_absolue_mad: float
    version: int
    blocages: list[str] = field(default_factory=list)
    lignes: list[LigneLue] = field(default_factory=list)


@dataclass
class _Contexte:
    """Ce qui se lit une fois pour plusieurs inventaires."""

    magasins: dict[int, Magasin]
    matieres: dict[int, Matiere]
    lots: dict[int, Lot]
    noms: dict[int, str]
    lineaires: set[int]
    codes: dict[tuple[str, int], str]
    couts: calcul.CoutsInventaire


def _contexte(s: Session, inventaires: Sequence[Inventaire]) -> _Contexte:
    lignes = [x for i in inventaires for x in i.lignes]
    ids_m = {x.matiere_id for x in lignes}
    ids_l = {x.lot_id for x in lignes if x.lot_id is not None}
    ids_u = {
        u
        for i in inventaires
        for u in (i.cree_par_id, i.valide_par_id, i.abandonne_par_id, i.annule_par_id)
        if u is not None
    } | {u for x in lignes for u in (x.compte_par_id, x.second_par_id) if u is not None}
    codes = {("role", r.id): r.code for r in s.scalars(select(RoleNomenclature))}
    codes |= {("composition", c.id): c.code for c in s.scalars(select(Composition))}
    return _Contexte(
        magasins={g.id: g for g in s.scalars(select(Magasin))},
        matieres={m.id: m for m in s.scalars(select(Matiere).where(Matiere.id.in_(ids_m)))},
        lots={x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(ids_l)))},
        noms=noms_des_personnes(s, ids_u),
        lineaires=set(s.scalars(select(RoleNomenclature.id).where(RoleNomenclature.lineaire))),
        codes=codes,
        couts=calcul.couts_inventaire(donnees_moteur.charger(s)),
    )


def _criteres(i: Inventaire) -> CriteresLus:
    c = CriteresLus()
    for x in i.criteres:
        if x.genre == CritereInventaire.matiere and x.matiere_id is not None:
            c.matieres.append(x.matiere_id)
        elif x.genre == CritereInventaire.role and x.role_id is not None:
            c.roles.append(x.role_id)
        elif x.genre == CritereInventaire.composition and x.composition_id is not None:
            c.compositions.append(x.composition_id)
        elif x.classe_abc:
            c.classes_abc.append(x.classe_abc)
    return c


def texte_du_perimetre(c: CriteresLus, codes: dict[tuple[str, int], str]) -> str:
    """« Tout le stock » · « 3 matière(s) » · « Par famille : Poil, PP, classe A »."""
    famille = [codes.get(("role", x), "?") for x in c.roles]
    famille += [codes.get(("composition", x), "?") for x in c.compositions]
    famille += [f"classe {x}" for x in c.classes_abc]
    if not famille:
        return f"{len(c.matieres)} matière(s)" if c.matieres else "Tout le stock"
    suite = f" ; {len(c.matieres)} matière(s)" if c.matieres else ""
    return "Par famille : " + ", ".join(famille) + suite


def _quatre_yeux(i: Inventaire, x: InventaireLigne) -> str:
    """Un recomptage fait par la personne du premier comptage, ou par l'ouvreur : signalé."""
    if x.second_par_id is None:
        return ""
    if x.second_par_id == x.compte_par_id:
        return "même personne que le premier comptage : un recomptage se fait à quatre yeux"
    if x.second_par_id == i.cree_par_id:
        return "même personne que l'ouvreur : un recomptage se fait à quatre yeux"
    return ""


def _ajustements(s: Session, ids: list[int]) -> dict[int, dict[calcul.CleAjustement, int]]:
    """Par inventaire : (lot, magasin) → le mouvement d'ajustement qu'il a écrit."""
    par: dict[int, dict[calcul.CleAjustement, int]] = {i: {} for i in ids}
    if ids:
        for mid, inv, lot, mag in s.execute(
            select(Mouvement.id, Mouvement.inventaire_id, Mouvement.lot_id, Mouvement.magasin_id)
            .where(
                Mouvement.document == DocumentMouvement.inventaire,
                Mouvement.inventaire_id.in_(ids),
                Mouvement.contrepasse_id.is_(None),
            )
            .order_by(Mouvement.id)
        ):
            if inv is not None:
                par[inv].setdefault((lot, mag), mid)
    return par


def _ligne(
    i: Inventaire, x: InventaireLigne, e: calcul.EcartInventaire, ctx: _Contexte
) -> LigneLue:
    m = ctx.matieres[x.matiere_id]
    lot = ctx.lots.get(x.lot_id) if x.lot_id is not None else None
    poids = lot.poids_bobine if lot is not None and lot.poids_bobine > 0 else m.poids_bobine
    ecart = None if retenu(x) is None else (retenu(x) or Decimal(0)) - x.theorique
    pourcent = float(ecart / x.theorique * 100) if ecart is not None and x.theorique > 0 else None
    return LigneLue(
        id=x.id,
        lot_id=x.lot_id,
        lot=lot.numero if lot is not None else (x.lot_numero or "LOT INTERNE"),
        lot_interne=x.lot_interne,
        lot_trouve=x.lot_trouve,
        matiere_id=m.id,
        reference=m.reference,
        designation=m.designation,
        kg_par_ml=m.densite if m.role_id in ctx.lineaires else Decimal(0),
        poids_bobine=poids,
        bobines_palette=m.bobines_palette,
        magasin_id=x.magasin_id,
        magasin=ctx.magasins[x.magasin_id].code,
        theorique=x.theorique,
        compte=x.compte,
        palettes=x.nb_palettes,
        bobines=x.nb_bobines,
        compte_par=ctx.noms.get(x.compte_par_id or 0, ""),
        second_compte=x.second_compte,
        second_par=ctx.noms.get(x.second_par_id or 0, ""),
        quatre_yeux=_quatre_yeux(i, x),
        retenu=retenu(x),
        ecart=ecart,
        ecart_pourcent=pourcent,
        cmup_mad=e.cmup_mad,
        valeur_ecart_mad=e.valeur_ecart_mad,
        hors_tolerance=e.hors_tolerance,
        a_recompter=e.a_recompter,
        justification=x.justification,
    )


def _lu(
    s: Session,
    i: Inventaire,
    ctx: _Contexte,
    ajustes: dict[calcul.CleAjustement, int],
    detail: bool,
) -> InventaireLu:
    refs = {k: m.reference for k, m in ctx.matieres.items()}
    lignes = [ligne_de_calcul(x, refs[x.matiere_id]) for x in i.lignes]
    e = calcul.ecarts_inventaire(
        lignes, statut=i.statut, tolerance=float(i.tolerance), couts=ctx.couts, ajustements=ajustes
    )
    criteres = _criteres(i)
    nom = ctx.noms.get
    lues = [_ligne(i, x, ex, ctx) for x, ex in zip(i.lignes, e.lignes, strict=True)]
    g = ctx.magasins.get(i.magasin_id or 0)
    return InventaireLu(
        id=i.id,
        numero=i.numero,
        libelle=i.libelle,
        statut=i.statut,
        date=i.date,
        magasin_id=i.magasin_id,
        magasin=g.code if g is not None else TOUS_LES_MAGASINS,
        tolerance=i.tolerance,
        perimetre=texte_du_perimetre(criteres, ctx.codes),
        criteres=criteres,
        nb_matieres_suspendues=len(i.matieres),
        cree_par=nom(i.cree_par_id or 0, ""),
        cree_le=i.cree_le,
        valide_par=nom(i.valide_par_id or 0, ""),
        valide_le=i.valide_le,
        abandonne_par=nom(i.abandonne_par_id or 0, ""),
        abandonne_le=i.abandonne_le,
        annule_par=nom(i.annule_par_id or 0, ""),
        annule_le=i.annule_le,
        annulation_motif=i.annulation_motif,
        nb_lignes=e.nb_lignes,
        nb_comptees=e.nb_comptees,
        hors_tolerance=e.hors_tolerance,
        sans_justification=sum(1 for x in lues if _non_justifie(x)),
        a_recompter=e.a_recompter,
        recomptees=e.recomptees,
        recomptes_meme_personne=sum(1 for x in lues if x.quatre_yeux),
        ecart_total=e.ecart_total,
        ecart_absolu=e.ecart_absolu,
        ecart_valeur_mad=e.ecart_valeur_mad,
        ecart_valeur_absolue_mad=e.ecart_valeur_absolue_mad,
        version=i.version,
        blocages=blocages(s, i) if detail else [],
        lignes=lues if detail else [],
    )


def _non_justifie(x: LigneLue) -> bool:
    return x.hors_tolerance and len(x.justification.strip()) < JUSTIFICATION_MINIMUM


def blocages(s: Session, i: Inventaire) -> list[str]:
    """Ce qui empêcherait de valider maintenant (sans rien écrire) ; vide hors « ouvert »."""
    if i.statut != StatutInventaire.ouvert:
        return []
    raisons = []
    if all(x.compte is None for x in i.lignes):
        raisons.append("Aucun lot compté : saisir les comptages avant de valider.")
    sans = sans_justification(s, i)
    if sans:
        raisons.append(
            "Écart hors tolérance sans justification : " + ", ".join(sans[:CITEES]) + "."
        )
    try:
        periode.date_permise(s, i.date)
    except Refus as refus:
        raisons.append(refus.detail)
    ecarts = {
        (x.lot_id, x.magasin_id)
        for x in i.lignes
        if x.lot_id is not None and x.compte is not None and retenu(x) != x.theorique
    }
    message = p.message_bouge_apres(i.date, p.bouge_apres(s, i.date, ecarts))
    return raisons + ([message] if message else [])


def lire(s: Session, inventaires: Sequence[Inventaire], *, detail: bool) -> list[InventaireLu]:
    """Des inventaires lus (requêtes groupées ; coûts du moteur lus une fois)."""
    ctx = _contexte(s, inventaires)
    ajustes = _ajustements(s, [i.id for i in inventaires])
    return [_lu(s, i, ctx, ajustes[i.id], detail) for i in inventaires]


def fiche(s: Session, ident: int) -> InventaireLu:
    """Route 127."""
    return lire(s, [charger(s, ident)], detail=True)[0]


def liste(s: Session, statut: StatutInventaire | None = None) -> list[InventaireLu]:
    """Route 124 : les inventaires, les plus récents d'abord (sans leurs lignes)."""
    requete = select(Inventaire).options(
        selectinload(Inventaire.lignes),
        selectinload(Inventaire.criteres),
        selectinload(Inventaire.matieres),
    )
    if statut is not None:
        requete = requete.where(Inventaire.statut == statut)
    return lire(s, list(s.scalars(requete.order_by(Inventaire.id.desc()))), detail=False)
