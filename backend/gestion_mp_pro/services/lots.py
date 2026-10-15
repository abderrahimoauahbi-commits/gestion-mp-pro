"""Les lots : création (numéro du fournisseur ou lot interne `LOT-AAAA-NNNN` donné à la
validation, sans trou), soldes par magasin et statut calculé, ce qu'un lot pouvait donner à
une date passée, lots disponibles dans l'ordre FIFO, histoire d'un lot (REGLES B.1.4, B.1.7,
B.1.9, B.1.10 ; `gestion_mp/services/stock.py`, `api/stock.py`, `api/production.presents_au`).

Le statut d'un lot n'est pas stocké (il ne pourrait que diverger du journal) : disponible, en
partie en quarantaine, en quarantaine, épuisé (S60). La recherche `q` suit la règle unique de
l'écran (`normaliser` : tous les mots, sans accents, `%` et `_` littéraux).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Journal, Lot, Mouvement, Ordre, Solde
from gestion_mp_pro.modeles.enums import ObjetJournal, SerieNumero, TypeMagasin, TypeMouvement
from gestion_mp_pro.modeles.recherche import normaliser, recalculer
from gestion_mp_pro.modeles.types import MESURE, arrondir
from gestion_mp_pro.services import fonds_de_lot, horloge, numerotation
from gestion_mp_pro.services.lots_lecture import Lus, lire, presents_au

ZERO = Decimal(0)
STATUTS_LOT = {
    "disponible": "Disponible",
    "partiel": "En partie en quarantaine",
    "quarantaine": "En quarantaine",
    "epuise": "Épuisé",
}
"""Statut calculé d'un lot → libellé de l'écran."""


def lot_ou_creer(
    s: Session,
    matiere_id: int,
    numero: str,
    entre_le: date,
    *,
    fournisseur_id: int | None = None,
    poids_bobine: Decimal | float = 0,
    interne: bool = False,
) -> Lot:
    """Le lot (matière, numéro), créé s'il manque (`ON CONFLICT DO NOTHING` : deux postes
    simultanés, un seul lot). Un lot existant gagne son fournisseur s'il n'en avait pas, et le
    poids de bobine mesuré s'il en est donné un ; sa date d'entrée ne change jamais (S30–S31)."""
    numero = numero.strip()
    if not numero:
        raise Refus.saisie(
            "Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne ».",
            champs={"lot_numero": "numéro du lot manquant"},
        )
    if re.search(r"\s", numero):
        raise Refus.saisie(
            f"Un numéro de lot s'écrit sans espace : « {numero} ».",
            champs={"lot_numero": "numéro du lot avec un espace"},
        )
    poids = arrondir(poids_bobine, MESURE)
    cree = s.execute(
        insert(Lot)
        .values(
            matiere_id=matiere_id,
            numero=numero,
            entre_le=entre_le,
            fournisseur_id=fournisseur_id,
            poids_bobine=poids,
            poids_bobine_le=entre_le if poids else None,
            interne=interne,
        )
        .on_conflict_do_nothing(index_elements=["matiere_id", "numero"])
        .returning(Lot.id)
    ).scalar()
    lot = s.scalars(
        select(Lot)
        .where(Lot.matiere_id == matiere_id, Lot.numero == numero)
        .execution_options(populate_existing=True)
    ).one()
    if cree is not None:
        recalculer(s, lot)
        return lot
    if fournisseur_id and not lot.fournisseur_id:
        lot.fournisseur_id = fournisseur_id
    if poids:
        lot.poids_bobine, lot.poids_bobine_le = poids, entre_le
    return lot


def numero_interne(s: Session, jour: date) -> str:
    """Le numéro suivant de la série `LOT-AAAA-NNNN` (année de la pièce), donné dans la
    transaction de la validation : un refus l'annule, la série ne se troue pas (M65, T7). Un
    numéro déjà porté par un lot (un fournisseur qui numérote comme nous) est sauté (C-16)."""
    return numerotation.numero(
        s,
        SerieNumero.LOT,
        jour,
        deja_pris=lambda n: bool(s.scalar(select(exists().where(Lot.numero == n)))),
    )


def lot_interne(
    s: Session, matiere_id: int, jour: date, *, poids_bobine: Decimal | float = 0
) -> Lot:
    """Un lot numéroté par l'usine, créé à la validation qui le fait entrer (case « LOT
    INTERNE » d'une ligne de réception, d'ouverture ou d'inventaire)."""
    return lot_ou_creer(
        s, matiere_id, numero_interne(s, jour), jour, poids_bobine=poids_bobine, interne=True
    )


def statut_lot(disponible: Decimal | float, quarantaine: Decimal | float) -> str:
    """Disponible, en partie en quarantaine, en quarantaine ou épuisé (S60)."""
    if quarantaine > 0 and disponible > 0:
        return "partiel"
    if quarantaine > 0:
        return "quarantaine"
    if disponible > 0:
        return "disponible"
    return "epuise"


@dataclass
class SoldeMagasin:
    """Ce qu'un lot porte dans un magasin."""

    magasin_id: int
    magasin: str
    type: str
    quantite: Decimal
    fond_de_lot: bool = False
    """Ce solde est > 0 et sous le seuil de rebut (lot FOND-DE-LOT)."""


@dataclass(frozen=True)
class OrdreServi:
    """Un ordre de fabrication qu'un lot a servi."""

    id: int
    numero: str


@dataclass
class Historique:
    """Ce qu'a vécu un lot : entré, sorti (net des retours des machines), dernier mouvement,
    ordres servis (S70–S73)."""

    entre: Decimal = ZERO
    sorti: Decimal = ZERO
    dernier_mouvement: date | None = None
    ordres: list[OrdreServi] = field(default_factory=list)


def historique(s: Session, ids: set[int]) -> dict[int, Historique]:
    """L'histoire de chaque lot, en deux requêtes : une annulation et la ligne qu'elle annule
    ne comptent ni à l'aller ni au retour ; un transfert ne fait que déplacer ; un retour des
    machines réduit le sorti (Entré − Sorti = Reste)."""
    if not ids:
        return {}
    lignes = s.execute(
        select(
            Mouvement.id,
            Mouvement.lot_id,
            Mouvement.type,
            Mouvement.quantite,
            Mouvement.date_effet,
            Mouvement.ordre_id,
            Mouvement.contrepasse_id,
        ).where(Mouvement.lot_id.in_(ids))
    ).all()
    annules = {x.contrepasse_id for x in lignes if x.contrepasse_id}
    numeros = dict(
        s.execute(
            select(Ordre.id, Ordre.numero).where(
                Ordre.id.in_({x.ordre_id for x in lignes if x.ordre_id} or {0})
            )
        ).all()
    )
    histoire: dict[int, Historique] = {}
    ordres: dict[int, dict[int, str]] = defaultdict(dict)
    for x in lignes:
        h = histoire.setdefault(x.lot_id, Historique())
        if h.dernier_mouvement is None or x.date_effet > h.dernier_mouvement:
            h.dernier_mouvement = x.date_effet
        if x.contrepasse_id or x.id in annules or x.type == TypeMouvement.TRANSFERT:
            continue
        if x.type == TypeMouvement.RETOUR_MACHINE:
            h.sorti -= x.quantite
        elif x.quantite > 0:
            h.entre += x.quantite
        else:
            h.sorti -= x.quantite
        if x.ordre_id and x.type == TypeMouvement.SORTIE:
            ordres[x.lot_id][x.ordre_id] = numeros.get(x.ordre_id) or ""
    for lot, h in histoire.items():
        h.ordres = [OrdreServi(i, n) for i, n in sorted(ordres[lot].items(), key=lambda kv: kv[1])]
    return histoire


@dataclass
class LotSolde:
    """Un lot et ce qu'il porte, magasin par magasin (S65)."""

    lot_id: int
    lot: str
    interne: bool
    matiere_id: int
    reference: str
    designation: str
    role: str
    kg_par_ml: Decimal
    fournisseur: str
    entre_le: date
    poids_bobine: Decimal
    bobines_palette: Decimal
    quantite: Decimal = ZERO
    disponible: Decimal = ZERO
    quarantaine: Decimal = ZERO
    magasins: list[SoldeMagasin] = field(default_factory=list)
    bobines: int | None = None
    statut: str = "epuise"
    historique: Historique = field(default_factory=Historique)
    fond_de_lot: bool = False
    """Au moins un de ses soldes est un fond de lot (lot FOND-DE-LOT)."""
    fond_de_lot_kg: Decimal = ZERO
    """Ce que pèsent ses fonds de lot, tous magasins."""
    version: int = 1
    """1 + les lignes du journal du lot (la fiche la rend aussi ; le rebut la relit)."""


def _texte(x: LotSolde) -> str:
    """Ce que la recherche lit d'un lot (règle unique : `normaliser`)."""
    magasins = " ".join(m.magasin for m in x.magasins)
    return normaliser(
        " ".join((x.lot, x.reference, x.designation, x.role, magasins, x.fournisseur))
    )


def _nouveau(lu: Lus, lot: Lot) -> LotSolde:
    """La ligne d'un lot, avant ses soldes."""
    m = lu.matieres[lot.matiere_id]
    return LotSolde(
        lot_id=lot.id,
        lot=lot.numero,
        interne=lot.interne,
        matiere_id=m.id,
        reference=m.reference,
        designation=m.designation,
        role=m.role,
        kg_par_ml=m.kg_par_ml,
        fournisseur=lu.fournisseurs.get(lot.fournisseur_id or m.fournisseur_id or 0, ""),
        entre_le=lot.entre_le,
        poids_bobine=lot.poids_bobine if lot.poids_bobine > 0 else m.poids_bobine,
        bobines_palette=m.bobines_palette,
    )


def _completer(
    x: LotSolde, h: Historique | None, seuil: Decimal = ZERO, version: int = 1
) -> LotSolde:
    """Bobines (au poids mesuré, sinon catalogue), statut, histoire, fonds de lot, version."""
    x.bobines = round(x.quantite / x.poids_bobine) if x.poids_bobine > 0 else None
    x.statut = statut_lot(x.disponible, x.quarantaine)
    x.historique = h or Historique()
    for g in x.magasins:
        g.fond_de_lot = fonds_de_lot.est_fond(g.quantite, seuil)
    x.fond_de_lot_kg = sum((g.quantite for g in x.magasins if g.fond_de_lot), ZERO)
    x.fond_de_lot = x.fond_de_lot_kg > 0
    x.version = version
    return x


def versions(s: Session, ids: set[int]) -> dict[int, int]:
    """La version de chaque lot (1 + ses lignes de journal), en une requête."""
    if not ids:
        return {}
    lignes = s.execute(
        select(Journal.objet_id, func.count())
        .where(Journal.objet == ObjetJournal.lot, Journal.objet_id.in_(ids))
        .group_by(Journal.objet_id)
    ).all()
    comptes = {int(i): int(n) for i, n in lignes if i is not None}
    return {i: 1 + comptes.get(i, 0) for i in ids}


@dataclass(frozen=True)
class FiltresLots:
    """Les filtres de la liste des lots (route 107) ; `non_nuls` : en stock seulement."""

    matiere_id: int | None = None
    magasin_id: int | None = None
    lot_id: int | None = None
    statut: str | None = None
    non_nuls: bool = True
    q: str = ""
    jour: date | None = None


def lister(s: Session, f: FiltresLots = FiltresLots()) -> list[LotSolde]:  # noqa: B008
    """Les lots et leurs soldes, par référence puis du plus ancien au plus récent. À une date
    passée, chaque lot dit ce qu'il pouvait donner ce jour-là (`presents_au`)."""
    lu = lire(s)
    requete = select(Lot, Solde.magasin_id, Solde.quantite).join(Solde, Solde.lot_id == Lot.id)
    if f.non_nuls:
        requete = requete.where(Solde.quantite > 0)
    if f.matiere_id is not None:
        requete = requete.where(Lot.matiere_id == f.matiere_id)
    if f.magasin_id is not None:
        requete = requete.where(Solde.magasin_id == f.magasin_id)
    if f.lot_id is not None:
        requete = requete.where(Lot.id == f.lot_id)
    rangs = [(lot, mag, q) for lot, mag, q in s.execute(requete)]
    if f.jour is not None and f.jour < horloge.aujourd_hui():
        au = presents_au(s, {(lot.id, mag) for lot, mag, _ in rangs}, f.jour)
        rangs = [(lot, mag, au[(lot.id, mag)]) for lot, mag, _ in rangs]
        rangs = [r for r in rangs if r[2] > 0 or not f.non_nuls]
    par_lot: dict[int, LotSolde] = {}
    for lot, mag, q in rangs:
        x = par_lot.setdefault(lot.id, _nouveau(lu, lot))
        magasin = lu.magasins[mag]
        x.quantite += q
        if magasin.type == TypeMagasin.quarantaine:
            x.quarantaine += q
        else:
            x.disponible += q
        if q != 0:
            x.magasins.append(SoldeMagasin(mag, magasin.code, str(magasin.type), q))
    lignes = list(par_lot.values())
    if f.q.strip():
        mots = normaliser(f.q).split()
        lignes = [x for x in lignes if all(m in _texte(x) for m in mots)]
    ids = {x.lot_id for x in lignes}
    histoires, numeros, seuil = historique(s, ids), versions(s, ids), fonds_de_lot.seuil(s)
    lignes = [_completer(x, histoires.get(x.lot_id), seuil, numeros[x.lot_id]) for x in lignes]
    if f.statut:
        lignes = [x for x in lignes if x.statut == f.statut]
    return sorted(lignes, key=lambda x: (x.reference, x.entre_le, x.lot_id))


def ligne_du_lot(s: Session, lot: Lot) -> LotSolde:
    """La ligne d'un lot, ses magasins vides compris (un lot sans solde est épuisé)."""
    trouve = lister(s, FiltresLots(lot_id=lot.id, non_nuls=False))
    if trouve:
        return trouve[0]
    return _completer(
        _nouveau(lire(s), lot),
        historique(s, {lot.id}).get(lot.id),
        version=versions(s, {lot.id})[lot.id],
    )
