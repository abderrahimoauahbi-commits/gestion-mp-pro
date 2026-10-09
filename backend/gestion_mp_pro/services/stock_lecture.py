"""Lectures calculées du stock (routes 103, 104) : l'état du stock à une date, la fiche
d'une matière (sa ligne, d'où vient son besoin, ses lots, ce qui en est monté sur les
métiers) (`gestion_mp/api/pilotage.py` : `/stock`).

Tout part du chargeur (`donnees_moteur.charger_au`) et du moteur (`calcul`) : aucune règle de
calcul ici. L'alimentation ne reçoit ni prix ni montant (filtre générique des routes) ni le
conseil d'achat (`CONSEIL_D_ACHAT`, E-01 de Gestion MP : quantités à commander, classe ABC
tirée de la valeur consommée).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.nomenclature import kg_par_m2
from gestion_mp_pro.calcul.plan import plan_mensuel
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock, fils_en_machine
from gestion_mp_pro.calcul.valorisation import cmup_par_reference
from gestion_mp_pro.modeles import Matiere
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import pilotage_machine
from gestion_mp_pro.services.lots import FiltresLots, LotSolde, lister

CONSEIL_D_ACHAT = (
    "quantite_a_commander", "quantite_a_commander_achat", "quantite_theorique",
    "palettes_a_commander", "unites_a_commander", "bons_en_preparation", "bc_en_preparation",
    "sans_achat", "classe_abc", "rang", "pourcentage_cumule", "action",
)  # fmt: skip
"""Ce que l'alimentation ne reçoit pas de l'état du stock, en plus des montants (`api/pilotage`
de Gestion MP, `MONTANTS_STOCK`)."""

CHAMPS_CHERCHES = (
    "reference", "designation", "fournisseur", "nature", "composition", "type_fil", "couleur",
    "titrage", "groupe_equiv",
)  # fmt: skip


@dataclass
class EtatStock:
    """L'état du stock à une date : une ligne par matière (tous les champs de `LigneStock`,
    plus l'identifiant de la matière et la valeur de ce qui est monté sur les métiers)."""

    date_reference: date
    magasins: list[str]
    lignes: list[dict[str, Any]]


def _lignes(d: c.Donnees, jour: date) -> tuple[list[LigneStock], dict[str, float]]:
    """Les lignes du moteur et le coût moyen de ce qui est monté (seulement s'il y en a)."""
    lignes = etat_stock(d, jour)
    couts = cmup_par_reference(d) if any(x.stock_machine > 0 for x in lignes) else {}
    return lignes, couts


def _ligne(
    x: LigneStock, ids: dict[str, int], couts: dict[str, float], conseil: bool
) -> dict[str, Any]:
    """Une ligne pour l'écran (sans conseil d'achat si `conseil` est faux)."""
    rendu = asdict(x)
    rendu["matiere_id"] = ids.get(x.reference)
    rendu["valeur_machine_mad"] = x.stock_machine * couts.get(x.reference, 0.0)
    if not conseil:
        rendu |= dict.fromkeys(CONSEIL_D_ACHAT)
    return rendu


def etat(s: Session, jour: date, q: str = "", conseil: bool = True) -> EtatStock:
    """Route 103 : l'état du stock au soir du `jour` ; `q` : tous les mots, sans accents."""
    d = pilotage_machine.au_soir(s, jour)
    lignes, couts = _lignes(d, jour)
    mots = normaliser(q).split()
    if mots:
        lignes = [
            x
            for x in lignes
            if all(
                m in normaliser(" ".join(str(getattr(x, k)) for k in CHAMPS_CHERCHES)) for m in mots
            )
        ]
    ids = dict(s.execute(select(Matiere.reference, Matiere.id)).all())
    return EtatStock(
        date_reference=jour,
        magasins=[g.code for g in d.magasins if g.actif],
        lignes=[_ligne(x, ids, couts, conseil) for x in lignes],
    )


@dataclass
class BesoinDeQualite:
    """D'où vient le besoin d'une matière : une qualité qui la consomme, mois par mois."""

    qualite: str
    pourcentage: float
    kg_par_m2: float
    m2: list[float]
    kg: list[float]


@dataclass
class FicheStockMatiere:
    """Route 104 : la ligne de la matière, d'où vient son besoin, ses lots, ses métiers."""

    ligne: dict[str, Any]
    besoins_par_qualite: list[BesoinDeQualite] = field(default_factory=list)
    lots: list[LotSolde] = field(default_factory=list)
    sur_les_metiers: list[dict[str, Any]] = field(default_factory=list)


def _besoins(d: c.Donnees, jour: date, reference: str) -> list[BesoinDeQualite]:
    """Le besoin du plan, qualité par qualité (la somme est la ligne « besoins » du stock) :
    (1 + taux de perte) × kg/m² × m² du mois (`calcul.besoins.besoins_mensuels`)."""
    plan = plan_mensuel(d, jour)
    perte = 1 + d.parametres.taux_perte
    resultat = []
    for recette in d.recettes:
        m2 = plan.get(recette.qualite)
        if recette.reference != reference or m2 is None:
            continue
        kg = kg_par_m2(d, recette.qualite, reference, recette.pourcentage)
        resultat.append(
            BesoinDeQualite(
                recette.qualite, recette.pourcentage, kg, list(m2), [kg * v * perte for v in m2]
            )
        )
    return resultat


def fiche_matiere(
    s: Session, matiere_id: int, jour: date, conseil: bool = True
) -> FicheStockMatiere:
    """Route 104 (404 si la matière est inconnue)."""
    m = s.get(Matiere, matiere_id)
    if m is None:
        raise Refus.introuvable("Matière introuvable.")
    d = pilotage_machine.au_soir(s, jour)
    lignes, couts = _lignes(d, jour)
    ligne = next(x for x in lignes if x.reference == m.reference)
    return FicheStockMatiere(
        ligne=_ligne(ligne, {m.reference: m.id}, couts, conseil),
        besoins_par_qualite=_besoins(d, jour, m.reference),
        lots=lister(s, FiltresLots(matiere_id=matiere_id, jour=jour)),
        sur_les_metiers=[asdict(f) for f in fils_en_machine(d) if f.reference == m.reference]
        if d.montage_connu
        else [],
    )
