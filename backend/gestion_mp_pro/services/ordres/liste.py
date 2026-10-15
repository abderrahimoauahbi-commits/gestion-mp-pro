"""La liste des ordres (route 135), paginée par curseur, et ce qui l'accompagne (REGLES P81, P82 ;
API-PRO 135, 135bis, 135ter).

- `filtrer` pousse en SQL le statut, les dates, le métier, le magasin, la qualité (par `EXISTS`)
  et la recherche sans accents (numéro, métier, magasin, commentaire, lots, matières, qualités —
  à l'identique de ce que l'écran cherchait sur la liste entière).
- `lister` ne construit le résumé (moteur, blocages) que pour la page rendue.
- `apercu` (135bis) donne à l'écran Sorties, sans lui envoyer toute la liste : les comptes par
  onglet (sur la période), les options des filtres liés (métier, magasin, qualité), les agrégats
  du moteur des indicateurs (sorti net, revenu, prévu, écart) et le compte des brouillons bloqués.
- `ouverts` (135ter) rend la liste **entière** d'un statut, plafonnée : l'atelier (téléphone) et
  la saisie des retours la lisent et la filtrent eux-mêmes ; au volume réel elle est petite.
Le classeur (144) garde la liste entière, non paginée (`toutes`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import (
    Lot,
    Magasin,
    Matiere,
    Metier,
    Ordre,
    OrdreLigne,
    OrdreQualite,
    Qualite,
)
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.services import recherche
from gestion_mp_pro.services.ordres import blocages, consommation, regles
from gestion_mp_pro.services.ordres.lecture import (
    FiltresOrdres,
    OrdreLu,
    contexte,
    lire_un,
    nom_du_metier,
)

ZERO = Decimal(0)
OUVERTS_MAX = 5000
"""Plafond de l'accès « tous les ordres d'un statut » (atelier, saisie) : au-delà, on borne."""


def _texte_sql() -> ColumnElement[str]:
    """Le texte cherché d'un ordre (sans accents), identique à ce que lisait l'écran : numéro
    (ou « brouillon »), métier (code et nom), magasin, commentaire, lots, matières, qualités."""
    lots = (
        select(func.string_agg(func.concat_ws(" ", Lot.numero, Matiere.reference), " "))
        .select_from(OrdreLigne)
        .join(Lot, Lot.id == OrdreLigne.lot_id)
        .join(Matiere, Matiere.id == OrdreLigne.matiere_id)
        .where(OrdreLigne.ordre_id == Ordre.id)
        .scalar_subquery()
    )
    qualites = (
        select(func.string_agg(func.concat_ws(" ", Qualite.code, Qualite.nom), " "))
        .select_from(OrdreQualite)
        .join(Qualite, Qualite.id == OrdreQualite.qualite_id)
        .where(OrdreQualite.ordre_id == Ordre.id)
        .scalar_subquery()
    )
    metier = (
        select(func.concat_ws(" ", Metier.code, Metier.nom))
        .where(Metier.id == Ordre.metier_id)
        .scalar_subquery()
    )
    magasin = select(Magasin.code).where(Magasin.id == Ordre.magasin_id).scalar_subquery()
    texte = func.concat_ws(
        " ",
        func.coalesce(Ordre.numero, "brouillon"),
        metier,
        magasin,
        Ordre.commentaire,
        lots,
        qualites,
    )
    return recherche.sans_accents_sql(texte)


def _tisse(qualite_id: int) -> ColumnElement[bool]:
    """L'ordre tisse cette qualité (au moins une de ses qualités)."""
    return exists().where(OrdreQualite.ordre_id == Ordre.id, OrdreQualite.qualite_id == qualite_id)


def filtrer(f: FiltresOrdres) -> Select[Ordre]:
    """La requête des ordres retenus (statut, dates, métier, magasin, qualité, mots)."""
    requete: Select[Ordre] = select(Ordre)
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
    if f.qualite_id is not None:
        requete = requete.where(_tisse(f.qualite_id))
    if f.q.strip():
        requete = requete.where(*recherche.conditions(_texte_sql(), f.q))
    return requete


def _lus(s: Session, ordres: list[Ordre], *, avec_blocages: bool = True) -> list[OrdreLu]:
    """Les ordres lus (moteur, et blocages si demandés) avec un contexte partagé."""
    if not ordres:
        return []
    ctx = contexte(s, ordres)
    return [lire_un(s, o, ctx, avec_blocages=avec_blocages) for o in ordres]


@dataclass
class PageOrdres:
    """Une page de la liste : les ordres, le total filtré, la clé de la dernière."""

    elements: list[OrdreLu]
    total: int
    dernier: tuple[date, int] | None


def lister(s: Session, f: FiltresOrdres, apres: tuple[date, int] | None, limite: int) -> PageOrdres:
    """Route 135 : les ordres filtrés, le plus récent d'abord (date, n° d'entrée), par pages."""
    s.flush()
    base = filtrer(f)
    total = s.scalar(select(func.count()).select_from(base.subquery())) or 0
    requete = base
    if apres is not None:
        jour, ident = apres
        requete = requete.where(or_(Ordre.date < jour, and_(Ordre.date == jour, Ordre.id < ident)))
    ordres = list(
        s.scalars(
            requete.options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
            .order_by(Ordre.date.desc(), Ordre.id.desc())
            .limit(limite + 1)
        )
    )
    suite = len(ordres) > limite
    ordres = ordres[:limite]
    dernier = (ordres[-1].date, ordres[-1].id) if suite and ordres else None
    return PageOrdres(_lus(s, ordres), total, dernier)


def toutes(s: Session, f: FiltresOrdres) -> list[OrdreLu]:
    """Le classeur (144) : tous les ordres filtrés, le plus récent d'abord (non paginé)."""
    s.flush()
    ordres = list(
        s.scalars(
            filtrer(f)
            .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
            .order_by(Ordre.date.desc(), Ordre.id.desc())
        )
    )
    return _lus(s, ordres)


def ouverts(s: Session, f: FiltresOrdres, limite: int = OUVERTS_MAX) -> list[OrdreLu]:
    """Route 135ter : la liste entière d'un statut (ou tous), plafonnée, le plus récent d'abord.
    L'atelier et la saisie des retours la filtrent eux-mêmes ; au volume réel elle est petite."""
    s.flush()
    ordres = list(
        s.scalars(
            filtrer(f)
            .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
            .order_by(Ordre.date.desc(), Ordre.id.desc())
            .limit(limite)
        )
    )
    return _lus(s, ordres)


@dataclass
class OptionOrdres:
    """Une option d'un filtre lié : son code envoyé à la route et son libellé affiché."""

    valeur: str
    libelle: str


@dataclass
class ApercuOrdres:
    """L'aperçu de la liste (135bis), pour l'écran Sorties sans lui envoyer toute la liste."""

    brouillon: int
    valide: int
    annule: int
    net: float
    revenu: float
    prevu: float
    sorti: float
    brouillons_periode: int
    brouillons_bloques: int
    qualites: list[OptionOrdres] = field(default_factory=list)
    metiers: list[OptionOrdres] = field(default_factory=list)
    magasins: list[OptionOrdres] = field(default_factory=list)


def _periode(f: FiltresOrdres) -> FiltresOrdres:
    """Les filtres réduits à la période (dates) : les comptes d'onglets ne tiennent qu'à elle."""
    return FiltresOrdres(du=f.du, au=f.au)


def _comptes(s: Session, f: FiltresOrdres) -> dict[str, int]:
    """Les comptes par statut sur la période (onglets des Sorties)."""
    sub = filtrer(_periode(f)).subquery()
    return {
        str(statut): n
        for statut, n in s.execute(select(sub.c.statut, func.count()).group_by(sub.c.statut))
    }


def _net_total(o: OrdreLu) -> float:
    """Ce que compte le KPI « sorti net » : le net d'un validé, le total d'un brouillon."""
    return float(o.total) if o.statut == StatutOrdre.brouillon else o.net


def _agregats(s: Session, f: FiltresOrdres) -> tuple[float, float, float, float]:
    """Les sommes du moteur sur les ordres affichés (filtre entier) : net, revenu, prévu, sorti.

    Un ordre validé ou annulé est sommé depuis le journal lu une fois pour tous
    (`consommations`, `retours_par_ordre`), sans charger ses lignes ni le lire un à un : lu
    ordre par ordre, l'aperçu croissait avec le nombre d'OF depuis l'origine (stress « 10 ans » :
    0,8 s après un an, 1,8 s après deux). Les brouillons, peu nombreux, et un ordre numéroté
    sans journal passent par le moteur comme avant (sorti net d'un brouillon = total de ses
    lignes). Les blocages ne servent pas aux agrégats."""
    tetes = list(s.execute(filtrer(f).with_only_columns(Ordre.id, Ordre.numero, Ordre.statut)))
    numerotes = [(i, n, st) for i, n, st in tetes if st != StatutOrdre.brouillon and n]
    conso = consommation.consommations(s) if numerotes else {}
    retours = consommation.retours_par_ordre(s, [i for i, _, _ in numerotes]) if numerotes else {}
    net = revenu = prevu = sorti = 0.0
    par_le_moteur = [i for i, n, st in tetes if st == StatutOrdre.brouillon or not n]
    for i, n, st in numerotes:
        c = conso.get(n)
        revenu += sum(float(r.quantite) for r in retours.get(i, []))
        if c is None:
            if st != StatutOrdre.annule:
                par_le_moteur.append(i)
            continue
        net += c.net
        if c.theorique:
            prevu += c.theorique
            sorti += c.net
    if par_le_moteur:
        ordres = list(
            s.scalars(
                select(Ordre)
                .where(Ordre.id.in_(par_le_moteur))
                .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
            )
        )
        lus = _lus(s, ordres, avec_blocages=False)
        net += sum(_net_total(o) for o in lus)
        revenu += sum(float(o.revenu) for o in lus if o.statut == StatutOrdre.brouillon)
        prevu += sum(o.prevu for o in lus if o.prevu)
        sorti += sum(o.net for o in lus if o.prevu)
    return net, revenu, prevu, sorti


def _options(s: Session, f: FiltresOrdres) -> tuple[list[OptionOrdres], list[OptionOrdres]]:
    """Les métiers et magasins présents dans les ordres de l'onglet (hors métier/magasin/mots)."""
    socle = FiltresOrdres(statut=f.statut, du=f.du, au=f.au, qualite_id=f.qualite_id)
    sub = filtrer(socle).subquery()
    metiers = [
        OptionOrdres(str(m.id), nom_du_metier(m))
        for m in s.scalars(
            select(Metier)
            .where(Metier.id.in_(select(sub.c.metier_id).where(sub.c.metier_id.isnot(None))))
            .order_by(Metier.code)
        )
    ]
    magasins = [
        OptionOrdres(str(g.id), g.code)
        for g in s.scalars(
            select(Magasin).where(Magasin.id.in_(select(sub.c.magasin_id))).order_by(Magasin.code)
        )
    ]
    return metiers, magasins


def _qualites_options(s: Session, f: FiltresOrdres) -> list[OptionOrdres]:
    """Les qualités tissées par les ordres de l'onglet (période + statut), par code."""
    socle = FiltresOrdres(statut=f.statut, du=f.du, au=f.au)
    ordres = filtrer(socle).subquery()
    requete = (
        select(Qualite.id, Qualite.code)
        .join(OrdreQualite, OrdreQualite.qualite_id == Qualite.id)
        .where(OrdreQualite.ordre_id.in_(select(ordres.c.id)))
        .distinct()
        .order_by(Qualite.code)
    )
    return [OptionOrdres(code, code) for _, code in s.execute(requete)]


def _brouillons(s: Session, f: FiltresOrdres) -> tuple[int, int]:
    """Les brouillons de la période : leur nombre, et combien seraient refusés (blocages)."""
    brouillons = list(
        s.scalars(
            filtrer(FiltresOrdres(statut=StatutOrdre.brouillon, du=f.du, au=f.au)).options(
                selectinload(Ordre.qualites), selectinload(Ordre.lignes)
            )
        )
    )
    if not brouillons:
        return 0, 0
    dernier = regles.dernier_ordre(s)
    bloques = sum(1 for o in brouillons if blocages.blocages(s, o, dernier))
    return len(brouillons), bloques


def apercu(s: Session, f: FiltresOrdres) -> ApercuOrdres:
    """Route 135bis : tout ce que l'écran Sorties calculait sur la liste entière."""
    s.flush()
    comptes = _comptes(s, f)
    net, revenu, prevu, sorti = _agregats(s, f)
    brouillons_periode, brouillons_bloques = _brouillons(s, f)
    metiers, magasins = _options(s, f)
    return ApercuOrdres(
        brouillon=comptes.get("brouillon", 0),
        valide=comptes.get("valide", 0),
        annule=comptes.get("annule", 0),
        net=net,
        revenu=revenu,
        prevu=prevu,
        sorti=sorti,
        brouillons_periode=brouillons_periode,
        brouillons_bloques=brouillons_bloques,
        qualites=_qualites_options(s, f),
        metiers=metiers,
        magasins=magasins,
    )
