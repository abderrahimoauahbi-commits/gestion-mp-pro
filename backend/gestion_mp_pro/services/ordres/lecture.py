"""La fiche et la liste des ordres (REGLES P81, P82 ; API-PRO 135, 136).

Un ordre lu dit ses qualités et ses m², ses lignes (kilos, et ce qui se compte en bobines), ce
qui en est revenu, son prévu par la recette perte comprise, son sorti net et son écart (les
chiffres du moteur, `consommation`), et, pour un brouillon, ce qui empêcherait de le valider.
La liste se filtre au serveur (statut, dates, métier, magasin, qualité, mots sans accents dans
le numéro, les qualités, les matières, les lots, le métier, le magasin et le commentaire).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.calcul.production import OrdreAjuste
from gestion_mp_pro.modeles import Lot, Magasin, Metier, Ordre, OrdreLigne, Qualite, Utilisateur
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import conversions, lots_lecture
from gestion_mp_pro.services.ordres import blocages, consommation, prevu, regles
from gestion_mp_pro.services.ordres.consommation import ParMatiere, Retour

ZERO = Decimal(0)


@dataclass
class QualiteOrdre:
    """Une qualité tissée par l'ordre."""

    qualite_id: int
    qualite: str
    nom: str
    m2: Decimal


@dataclass
class LigneOrdre:
    """Un lot sorti (ou à sortir) : kilos, et bobines quand le compte tombe juste."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Decimal
    lot_id: int
    lot: str
    quantite: Decimal
    poids_bobine: Decimal
    bobines_palette: Decimal
    bobines: int | None


@dataclass
class OrdreLu:
    """Un ordre tel que l'écran et l'atelier le lisent (sans aucun prix)."""

    id: int
    version: int
    numero: str | None
    statut: StatutOrdre
    date: date
    magasin_id: int
    magasin: str
    metier_id: int | None
    metier: str
    commentaire: str
    cree_par: str
    cree_le: datetime
    valide_par: str
    valide_le: datetime | None
    annule_par: str
    annule_le: datetime | None
    annulation_motif: str
    prevu_fige: bool
    taux_perte: float
    qualites: list[QualiteOrdre]
    lignes: list[LigneOrdre]
    total: Decimal
    retours: list[Retour]
    revenu: Decimal
    prevu: float
    net: float
    ecart: float | None
    ecart_relatif: float | None
    par_matiere: list[ParMatiere]
    lots: list[str]
    matieres: list[str]
    fabrication: str
    m2: Decimal
    blocages: list[str] = field(default_factory=list)


@dataclass
class Contexte:
    """Ce que la lecture de plusieurs ordres partage (une requête par table)."""

    noms: dict[int, str]
    magasins: dict[int, Magasin]
    metiers: dict[int, Metier]
    qualites: dict[int, Qualite]
    lots: dict[int, Lot]
    lus: lots_lecture.Lus
    retours: dict[int, list[Retour]]
    conso: dict[str, OrdreAjuste]
    dernier: date | None
    taux: float


def contexte(s: Session, ordres: list[Ordre]) -> Contexte:
    """Les référentiels et les chiffres des ordres à lire."""
    ids_lots = {x.lot_id for o in ordres for x in o.lignes}
    valides = [o.id for o in ordres if o.numero]
    return Contexte(
        noms=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
        magasins={g.id: g for g in s.scalars(select(Magasin))},
        metiers={m.id: m for m in s.scalars(select(Metier))},
        qualites={q.id: q for q in s.scalars(select(Qualite))},
        lots={x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(ids_lots)))},
        lus=lots_lecture.lire(s),
        retours=consommation.retours_par_ordre(s, valides) if valides else {},
        conso=consommation.consommations(s) if valides else {},
        dernier=regles.dernier_ordre(s),
        taux=float(prevu.taux_perte(s)),
    )


def _ligne(x: OrdreLigne, ctx: Contexte) -> LigneOrdre:
    """Une ligne de l'ordre, lue."""
    lot = ctx.lots[x.lot_id]
    m = ctx.lus.matieres[lot.matiere_id]
    c = lots_lecture.conditionnement_lu(m, lot.poids_bobine)
    quantite = x.quantite
    nombre = conversions.bobines(quantite, c)
    juste = nombre is not None and abs(nombre * c.poids_bobine - quantite) < regles.POUSSIERE
    return LigneOrdre(
        id=x.id, matiere_id=m.id, reference=m.reference, designation=m.designation,
        kg_par_ml=m.kg_par_ml, lot_id=lot.id, lot=lot.numero, quantite=quantite,
        poids_bobine=c.poids_bobine, bobines_palette=m.bobines_palette,
        bobines=nombre if juste else None,
    )  # fmt: skip


def nom_du_metier(m: Metier | None) -> str:
    """« CODE · Nom » (ECRANS-PRO, champ serveur unique ; RESTES3, F3) ; le code seul sans nom
    distinct."""
    if m is None:
        return ""
    return f"{m.code} · {m.nom}" if m.nom and m.nom != m.code else m.code


def lire_un(s: Session, o: Ordre, ctx: Contexte, *, avec_blocages: bool = True) -> OrdreLu:
    """Un ordre lu avec son contexte."""
    lignes = [_ligne(x, ctx) for x in sorted(o.lignes, key=lambda y: y.id)]
    fiches = ctx.qualites
    qualites = [
        QualiteOrdre(q.qualite_id, fiches[q.qualite_id].code, fiches[q.qualite_id].nom, q.m2)
        for q in sorted(o.qualites, key=lambda y: y.id)
    ]
    conso = ctx.conso.get(o.numero or "") if o.statut != StatutOrdre.brouillon else None
    retours = ctx.retours.get(o.id, [])
    total = sum((x.quantite for x in lignes), ZERO)
    metier = ctx.metiers.get(o.metier_id) if o.metier_id else None
    m2 = sum((q.m2 for q in qualites), ZERO)
    return OrdreLu(
        id=o.id, version=o.version, numero=o.numero, statut=StatutOrdre(o.statut), date=o.date,
        magasin_id=o.magasin_id, magasin=ctx.magasins[o.magasin_id].code,
        metier_id=o.metier_id, metier=nom_du_metier(metier),
        commentaire=o.commentaire, cree_par=ctx.noms.get(o.cree_par_id or 0, ""),
        cree_le=o.cree_le, valide_par=ctx.noms.get(o.valide_par_id or 0, ""),
        valide_le=o.valide_le, annule_par=ctx.noms.get(o.annule_par_id or 0, ""),
        annule_le=o.annule_le, annulation_motif=o.annulation_motif, prevu_fige=o.prevu_fige,
        taux_perte=conso.taux_perte if conso else ctx.taux, qualites=qualites, lignes=lignes,
        total=total, retours=retours, revenu=sum((r.quantite for r in retours), ZERO),
        prevu=conso.theorique if conso else 0.0,
        net=conso.net if conso else (0.0 if o.statut == StatutOrdre.annule else float(total)),
        ecart=conso.ecart if conso else None,
        ecart_relatif=conso.ecart_relatif if conso else None,
        par_matiere=consommation.par_matiere(conso, ctx.lus), lots=sorted({x.lot for x in lignes}),
        matieres=sorted({x.reference for x in lignes}),
        fabrication=" · ".join(f"{q.qualite} {conversions.kg(q.m2, 0)} m²" for q in qualites)
        or "hors recette",
        m2=m2,
        blocages=blocages.blocages(s, o, ctx.dernier) if avec_blocages else [],
    )  # fmt: skip


def fiche(s: Session, ident: int) -> OrdreLu:
    """Route 136."""
    from gestion_mp_pro.services.ordres.gestes import charger

    o = charger(s, ident)
    return lire_un(s, o, contexte(s, [o]))


@dataclass(frozen=True)
class FiltresOrdres:
    """Les filtres de la liste (135) et de son classeur (144)."""

    statut: StatutOrdre | None = None
    q: str = ""
    du: date | None = None
    au: date | None = None
    metier_id: int | None = None
    magasin_id: int | None = None
    qualite_id: int | None = None


def _texte(x: OrdreLu) -> str:
    """Ce que la recherche lit d'un ordre, sans accents."""
    mots = [x.numero or "brouillon", x.metier, x.magasin, x.commentaire, *x.lots, *x.matieres]
    mots += [f"{q.qualite} {q.nom}" for q in x.qualites]
    return normaliser(" ".join(mots))


def lister(s: Session, f: FiltresOrdres) -> list[OrdreLu]:
    """Route 135 : les ordres filtrés, le plus récent d'abord (date, puis numéro d'entrée)."""
    requete = (
        select(Ordre)
        .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
        .order_by(Ordre.date.desc(), Ordre.id.desc())
    )
    if f.statut is not None:
        requete = requete.where(Ordre.statut == f.statut)
    if f.du is not None:
        requete = requete.where(Ordre.date >= f.du)
    if f.au is not None:
        requete = requete.where(Ordre.date <= f.au)
    if f.metier_id is not None:
        requete = requete.where(Ordre.metier_id == f.metier_id)
    if f.magasin_id is not None:
        requete = requete.where(Ordre.magasin_id == f.magasin_id)
    ordres = [
        o for o in s.scalars(requete)
        if f.qualite_id is None or any(q.qualite_id == f.qualite_id for q in o.qualites)
    ]  # fmt: skip
    ctx = contexte(s, ordres)
    mots = normaliser(f.q).split()
    gardes = []
    for o in ordres:
        x = lire_un(s, o, ctx, avec_blocages=False)
        if all(m in _texte(x) for m in mots):
            gardes.append((o, x))
    for o, x in gardes:
        x.blocages = blocages.blocages(s, o, ctx.dernier)
    return [x for _, x in gardes]
