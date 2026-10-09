"""Le plan d'achat : le détail trié et la consolidation par fournisseur (CALCULS A § 3.12).

Portage de `moteur.LignePlanAchat`, `GroupeFournisseur`, `PlanAchat`, `_tier`, `plan_achat`
(méthode corrigée) : tout ce que le budget compte est montré ; tri par montant en MAD
pondéré par la classe, le rang du catalogue départage ; l'urgence d'un fournisseur est celle
de sa pire ligne.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from gestion_mp_pro.calcul.constantes import (
    ACTIONS_TIER,
    LIBELLES_STATUT,
    POIDS_CLASSE,
    STATUTS,
    STATUTS_EN_ALERTE,
    TIER_1,
    TIER_2,
    TIER_3,
    TIER_4,
)
from gestion_mp_pro.calcul.modele import Donnees, Parametres
from gestion_mp_pro.calcul.outils import arrondi
from gestion_mp_pro.calcul.stock import LigneStock


@dataclass
class LignePlanAchat:
    """Une matière à commander, dans l'ordre du plan."""

    reference: str
    nature: str
    designation: str
    fournisseur: str
    classe_abc: str
    statut: str
    quantite: float
    unite_achat: str
    quantite_achat: float
    unite_commande: str
    unites_commande: float
    contenance_commande: float
    prix: float
    devise: str
    montant_devise: float
    montant_mad: float
    palettes: float
    tier: str
    risque: str
    action: str
    relance: str
    en_preparation: float = 0.0
    bons_en_preparation: list[str] = field(default_factory=list)


@dataclass
class GroupeFournisseur:
    """Ce qu'il y a à commander chez un fournisseur, montants tenus par devise."""

    fournisseur: str
    pays: str
    devise_par_defaut: str
    devises: list[str]
    delai_jours: float
    contact: str
    nb_references: int
    quantite: float
    montants_par_devise: dict[str, float]
    montant_mad: float
    part_budget: float
    urgence: str
    ruptures: int
    critiques: int = 0
    urgents: int = 0


@dataclass
class PlanAchat:
    """La feuille 📈 Plan_Achat."""

    references_a_commander: int
    references_en_alerte: int
    budget_mad: float
    quantite_totale: float
    references_classe_a: int
    ruptures: int
    critiques: int
    urgents: int
    attentions: int
    ok: int
    tiers: dict[str, int]
    fournisseurs: list[GroupeFournisseur]
    lignes: list[LignePlanAchat]


def tier(ligne: LigneStock, parametres: Parametres) -> str:
    """L'urgence d'émission : rupture ou critique → Tier 1 ; classe A lourde → Tier 1 ;
    puis par montant, une matière urgente au moins Tier 2 (`Plan_Achat!M29`, corrigé)."""
    montant = ligne.montant_a_commander_mad
    if ligne.statut in (STATUTS["RUPTURE"], STATUTS["CRITIQUE"]):
        return TIER_1
    if ligne.classe_abc == "A" and montant >= parametres.seuil_tier1:
        return TIER_1
    if montant >= parametres.seuil_tier2 or ligne.statut == STATUTS["URGENT"]:
        return TIER_2
    if montant >= parametres.seuil_tier3:
        return TIER_3
    return TIER_4


def _ligne(ligne: LigneStock, niveau: str) -> LignePlanAchat:
    return LignePlanAchat(
        reference=ligne.reference,
        nature=ligne.nature,
        designation=ligne.designation,
        fournisseur=ligne.fournisseur,
        classe_abc=ligne.classe_abc,
        statut=ligne.statut,
        quantite=ligne.quantite_a_commander,
        unite_achat=ligne.unite_achat,
        quantite_achat=ligne.quantite_a_commander_achat,
        unite_commande=ligne.unite_commande,
        unites_commande=ligne.unites_a_commander,
        contenance_commande=ligne.contenance_commande,
        prix=ligne.prix_kg,
        devise=ligne.devise,
        montant_devise=ligne.montant_a_commander,
        montant_mad=ligne.montant_a_commander_mad,
        palettes=ligne.palettes_a_commander,
        tier=niveau,
        risque=ligne.sourcing,
        action=ACTIONS_TIER[niveau],
        relance=(
            f"{LIBELLES_STATUT.get(ligne.statut, ligne.statut)} — {ligne.reference} "
            f"({ligne.fournisseur}) — "
            f"Qté: {arrondi(ligne.quantite_a_commander):.0f} kg — "
            f"{arrondi(ligne.montant_a_commander):.0f} {ligne.devise} — "
            f"Délai: {arrondi(ligne.delai_jours):.0f}j"
        ),
        en_preparation=ligne.bc_en_preparation,
        bons_en_preparation=ligne.bons_en_preparation,
    )


def _urgence(lot: list[LigneStock], montant_mad: float, parametres: Parametres) -> str:
    """La pire ligne fait l'urgence ; un gros montant n'est pas une urgence."""
    if any(x.statut in (STATUTS["RUPTURE"], STATUTS["CRITIQUE"], STATUTS["URGENT"]) for x in lot):
        return "🚨 BC URGENT"
    if montant_mad >= parametres.seuil_bc_groupe:
        return "📋 BC groupé"
    if montant_mad > 0:
        return "📝 Standard"
    return "—"


def _groupe(donnees: Donnees, nom: str, lot: list[LigneStock], budget: float) -> GroupeFournisseur:
    fournisseur = donnees.fournisseur(nom)
    montant_mad = sum(x.montant_a_commander_mad for x in lot)
    par_devise: dict[str, float] = defaultdict(float)
    for ligne in lot:
        par_devise[ligne.devise] += ligne.montant_a_commander
    return GroupeFournisseur(
        fournisseur=nom,
        pays=fournisseur.pays if fournisseur else "",
        devise_par_defaut=fournisseur.devise if fournisseur else "MAD",
        devises=sorted(par_devise),
        # Le délai qui a servi au calcul : un inconnu prend le délai par défaut (D-15).
        delai_jours=donnees.delai_fournisseur(nom),
        contact=fournisseur.contact if fournisseur else "",
        nb_references=len(lot),
        quantite=sum(x.quantite_a_commander for x in lot),
        montants_par_devise=dict(par_devise),
        montant_mad=montant_mad,
        part_budget=montant_mad / budget if budget else 0.0,
        urgence=_urgence(lot, montant_mad, donnees.parametres),
        ruptures=sum(1 for x in lot if x.statut == STATUTS["RUPTURE"]),
        critiques=sum(1 for x in lot if x.statut == STATUTS["CRITIQUE"]),
        urgents=sum(1 for x in lot if x.statut == STATUTS["URGENT"]),
    )


def _compter(lignes: list[LigneStock], cle: str) -> int:
    return sum(1 for x in lignes if x.statut == STATUTS[cle])


def plan_achat(donnees: Donnees, lignes_stock: list[LigneStock]) -> PlanAchat:
    """Consolidation par fournisseur (budget décroissant) et détail trié."""
    a_commander = [x for x in lignes_stock if x.quantite_a_commander > 0]
    budget = sum(x.montant_a_commander_mad for x in a_commander)
    position = {ligne.reference: i for i, ligne in enumerate(lignes_stock, start=1)}
    tries = sorted(
        a_commander,
        key=lambda x: (
            -(x.montant_a_commander_mad * POIDS_CLASSE.get(x.classe_abc, 1)),
            position[x.reference],
        ),
    )
    lignes: list[LignePlanAchat] = []
    tiers: dict[str, int] = defaultdict(int)
    for ligne in tries:
        niveau = tier(ligne, donnees.parametres)
        tiers[niveau] += 1
        lignes.append(_ligne(ligne, niveau))
    par_fournisseur: dict[str, list[LigneStock]] = defaultdict(list)
    for ligne in a_commander:
        par_fournisseur[ligne.fournisseur].append(ligne)
    groupes = [_groupe(donnees, nom, lot, budget) for nom, lot in par_fournisseur.items()]
    groupes.sort(key=lambda g: -g.montant_mad)
    return PlanAchat(
        references_a_commander=len(a_commander),
        references_en_alerte=sum(1 for x in a_commander if x.statut in STATUTS_EN_ALERTE),
        budget_mad=budget,
        quantite_totale=sum(x.quantite_a_commander for x in a_commander),
        references_classe_a=sum(1 for x in a_commander if x.classe_abc == "A"),
        ruptures=_compter(lignes_stock, "RUPTURE"),
        critiques=_compter(lignes_stock, "CRITIQUE"),
        urgents=_compter(lignes_stock, "URGENT"),
        attentions=_compter(lignes_stock, "ATTENTION"),
        ok=_compter(lignes_stock, "OK"),
        tiers=dict(tiers),
        fournisseurs=groupes,
        lignes=lignes,
    )
