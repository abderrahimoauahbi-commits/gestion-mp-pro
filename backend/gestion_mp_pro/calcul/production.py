"""Ordres de fabrication et réalisé du plan (CALCULS B § 7).

Portage de `moteur.consommation_par_of`, `realise_par_qualite` et du calcul de route
`api/production.ajuster_ordre`. Les dicts de Gestion MP deviennent des dataclasses aux mêmes
clés.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, fields
from datetime import date, datetime, time

from gestion_mp_pro.calcul.besoins import CacheRecette, kg_m2_version, versions_recette_pendant
from gestion_mp_pro.calcul.constantes import MOIS
from gestion_mp_pro.calcul.modele import Donnees, Mouvement, OrdreFabrication
from gestion_mp_pro.calcul.outils import debut_de_mois, fin_de_mois, mois_entre
from gestion_mp_pro.calcul.plan import m2_passe, plan_mensuel

INSTANT_MAX = datetime.max  # noqa: DTZ901 — instants du moteur : heure de l'usine, sans fuseau
"""Un ordre sans date ni validation prend la recette la plus récente."""


@dataclass
class Fabrication:
    """Une qualité de l'ordre et ses m²."""

    qualite: str
    m2: float


@dataclass
class ConsommationReference:
    """Ce qu'un ordre a consommé d'un fil, face au prévu de la recette."""

    reference: str
    quantite: float
    theorique: float
    ecart: float | None
    hors_recette: bool


@dataclass
class ConsommationOrdre:
    """Ce qu'un ordre a consommé, fil par fil, et son écart au prévu."""

    numero_of: str
    consomme: float
    retours: float
    references: list[ConsommationReference]
    lots: list[str]
    debut: date
    fin: date
    net: float
    fabrications: list[Fabrication]
    qualite: str
    m2: float
    commentaire: str
    theorique: float
    taux_perte_fige: float | None
    ecart: float | None
    ecart_relatif: float | None


@dataclass
class _Fiche:
    numero_of: str
    premier: date
    consomme: float = 0.0
    retours: float = 0.0
    references: dict[str, float] = field(default_factory=dict)
    lots: set[str] = field(default_factory=set)
    debut: date | None = None
    fin: date | None = None


def _fiches(donnees: Donnees) -> dict[str, _Fiche]:
    """Le journal par ordre ; une écriture annulée et son annulation ne comptent pas."""
    fiches: dict[str, _Fiche] = {}
    annulees = {m.contrepasse_id for m in donnees.mouvements if m.contrepasse_id is not None}
    for m in donnees.mouvements:
        if not m.numero_of:
            continue
        fiche = fiches.setdefault(m.numero_of, _Fiche(numero_of=m.numero_of, premier=m.date))
        fiche.premier = min(fiche.premier, m.date)
        if m.contrepasse_id is not None or (m.id is not None and m.id in annulees):
            continue
        _compter(fiche, m)
    return fiches


def _compter(fiche: _Fiche, m: Mouvement) -> None:
    signee = m.quantite_signee
    if signee < 0:
        fiche.consomme += -signee
        fiche.debut = min(fiche.debut or m.date, m.date)
        fiche.fin = max(fiche.fin or m.date, m.date)
    else:
        fiche.retours += signee
    fiche.references[m.reference] = fiche.references.get(m.reference, 0.0) - signee
    if m.lot_fournisseur:
        fiche.lots.add(m.lot_fournisseur)


def prevu_de(donnees: Donnees, ordre: OrdreFabrication, cache: CacheRecette) -> dict[str, float]:
    """Le prévu de l'ordre : figé à sa validation ; sinon la recette en vigueur ce jour-là."""
    if ordre.theorique is not None:
        return dict(ordre.theorique)
    instant = ordre.valide_le or (
        datetime.combine(ordre.date, time.max) if ordre.date else INSTANT_MAX
    )
    prevu: dict[str, float] = defaultdict(float)
    for qualite, m2 in ordre.fabrications:
        versions = versions_recette_pendant(donnees, qualite, instant, instant)
        for reference, quantite in kg_m2_version(donnees, qualite, versions[-1], cache).items():
            if quantite > 0:
                prevu[reference] += quantite * m2
    return dict(prevu)


def _references(fiche: _Fiche, prevu: dict[str, float]) -> list[ConsommationReference]:
    sorties = [
        ConsommationReference(
            reference=reference,
            quantite=quantite,
            theorique=prevu.get(reference, 0.0),
            ecart=quantite - prevu[reference] if reference in prevu else None,
            hors_recette=bool(prevu) and reference not in prevu,
        )
        for reference, quantite in sorted(fiche.references.items())
    ]
    manquants = [
        ConsommationReference(
            reference=reference, quantite=0.0, theorique=kg, ecart=-kg, hors_recette=False
        )
        for reference, kg in sorted(prevu.items())
        if reference not in fiche.references
    ]
    return sorties + manquants


def _ordre(
    fiche: _Fiche, ordre: OrdreFabrication | None, prevu: dict[str, float]
) -> ConsommationOrdre:
    fabrications = ordre.fabrications if ordre else []
    net = fiche.consomme - fiche.retours
    theorique = sum(prevu.values())
    return ConsommationOrdre(
        numero_of=fiche.numero_of,
        consomme=fiche.consomme,
        retours=fiche.retours,
        references=_references(fiche, prevu),
        lots=sorted(fiche.lots),
        debut=fiche.debut or fiche.premier,
        fin=fiche.fin or fiche.premier,
        net=net,
        fabrications=[Fabrication(qualite=q, m2=m2) for q, m2 in fabrications],
        qualite=" · ".join(q for q, _ in fabrications),
        m2=ordre.m2 if ordre else 0.0,
        commentaire=ordre.commentaire if ordre else "",
        theorique=theorique,
        taux_perte_fige=ordre.perte if ordre else None,
        ecart=net - theorique if theorique else None,
        ecart_relatif=(net - theorique) / theorique if theorique else None,
    )


def consommation_par_of(donnees: Donnees) -> list[ConsommationOrdre]:
    """Ce que chaque ordre a consommé, référence par référence, face à la recette (perte non
    comprise) ; les ordres les plus récents d'abord."""
    cache: CacheRecette = {}
    ordres = {o.numero: o for o in donnees.ordres}
    resultat = []
    for fiche in _fiches(donnees).values():
        ordre = ordres.get(fiche.numero_of)
        prevu = prevu_de(donnees, ordre, cache) if ordre else {}
        resultat.append(_ordre(fiche, ordre, prevu))
    return sorted(resultat, key=lambda x: (x.fin, x.numero_of), reverse=True)


@dataclass
class ReferenceAjustee(ConsommationReference):
    """Un fil d'un ordre lu par l'atelier : prévu perte comprise, densité (kg/ml)."""

    kg_par_ml: float = 0.0


@dataclass
class OrdreAjuste(ConsommationOrdre):
    """Un ordre lu par l'atelier : le taux de perte appliqué au prévu."""

    taux_perte: float = 0.0


def ajuster_ordre(
    ordre: ConsommationOrdre, perte: float, densites: dict[str, float]
) -> OrdreAjuste:
    """L'ordre tel que l'atelier le lit : le prévu **perte comprise** (le taux figé avec
    l'ordre, sinon celui des réglages), la densité des fils au mètre (route `ajuster_ordre`)."""
    if ordre.taux_perte_fige is not None:
        perte = ordre.taux_perte_fige
    k = 1 + perte
    refs: list[ConsommationReference] = []
    for r in ordre.references:
        prevu = r.theorique * k
        refs.append(
            ReferenceAjustee(
                reference=r.reference,
                quantite=r.quantite,
                theorique=prevu,
                ecart=r.quantite - prevu if r.ecart is not None else None,
                hors_recette=r.hors_recette,
                kg_par_ml=densites.get(r.reference, 0.0),
            )
        )
    theorique = sum(r.theorique for r in refs)
    net = sum(r.quantite for r in refs)
    champs = {f.name: getattr(ordre, f.name) for f in fields(ConsommationOrdre)}
    champs |= {"references": refs, "theorique": theorique, "net": net}
    champs |= {"ecart": net - theorique if theorique else None}
    champs |= {"ecart_relatif": (net - theorique) / theorique if theorique else None}
    return OrdreAjuste(**champs, taux_perte=perte)


@dataclass
class RealiseQualite:
    """Le plan et le réalisé d'une qualité sur douze mois, et l'écart des mois clos."""

    qualite: str
    plan: list[float]
    realise: list[float]
    total_plan: float
    total_realise: float
    ecart: float | None


@dataclass
class Realise:
    """Ce que l'atelier a tissé face au plan : douze mois écoulés."""

    mois: list[str]
    mois_clos: int
    lignes: list[RealiseQualite]
    debut_service: str | None


def _plan_des_mois(
    donnees: Donnees, date_ref: date, mois: list[date], passe: bool
) -> tuple[dict[str, list[float]], date | None]:
    """Chaque mois clos sur le plan de son époque ; le mois en cours sur le plan d'aujourd'hui
    (vu à une date passée : celui de cette date) ; rien avant la mise en service."""
    premier = min((m.date for m in donnees.mouvements), default=None)
    service = debut_de_mois(premier) if premier is not None else None
    courant = plan_mensuel(donnees, date_ref)
    plan = {
        ligne.qualite: [
            0.0
            if service is not None and fin < service
            else m2_passe(donnees, ligne, fin)
            if fin < date_ref
            else m2_passe(donnees, ligne, fin, jusqu_a=date_ref)
            if passe
            else courant[ligne.qualite][mois_entre(date_ref, fin)]
            for fin in mois
        ]
        for ligne in donnees.plan
    }
    return plan, service


def realise_par_qualite(
    donnees: Donnees, date_ref: date, aujourd_hui: date | None = None
) -> Realise:
    """Qualité par qualité et mois par mois, ce que le plan annonçait et ce que les ordres ont
    tissé ; l'écart se juge sur les mois clos."""
    debut = fin_de_mois(date_ref, -(MOIS - 1))
    mois = [fin_de_mois(debut, i) for i in range(MOIS)]
    rangs = {(fin.year, fin.month): i for i, fin in enumerate(mois)}
    plan, service = _plan_des_mois(
        donnees, date_ref, mois, aujourd_hui is not None and date_ref < aujourd_hui
    )
    realise: dict[str, list[float]] = defaultdict(lambda: [0.0] * MOIS)
    for ordre in donnees.ordres:
        if ordre.date is None or ordre.date > date_ref:
            continue
        rang = rangs.get((ordre.date.year, ordre.date.month))
        if rang is not None:
            for qualite, m2 in ordre.fabrications:
                realise[qualite][rang] += m2
    clos = sum(1 for fin in mois if fin < date_ref)
    lignes = []
    for qualite in sorted(set(plan) | set(realise)):
        prevu, fait = plan.get(qualite, [0.0] * MOIS), realise.get(qualite, [0.0] * MOIS)
        prevu_clos, fait_clos = sum(prevu[:clos]), sum(fait[:clos])
        lignes.append(
            RealiseQualite(
                qualite=qualite,
                plan=prevu,
                realise=fait,
                total_plan=sum(prevu),
                total_realise=sum(fait),
                ecart=(fait_clos - prevu_clos) / prevu_clos if prevu_clos else None,
            )
        )
    return Realise(
        mois=[fin.isoformat() for fin in mois],
        mois_clos=clos,
        lignes=lignes,
        debut_service=service.isoformat() if service else None,
    )
