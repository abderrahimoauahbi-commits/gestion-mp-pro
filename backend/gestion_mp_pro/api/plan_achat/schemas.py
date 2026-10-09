"""Schémas Pydantic du domaine « Plan d'achat » (routes 149, 150, API-PRO § 1.17).

Les libellés du moteur (statut, tier, urgence) sont rendus tels quels, comme l'état du stock
(route 103) : l'écran les traduit en badges (`statuts.ts`).
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from gestion_mp_pro.api.communs import Sortie


class UniteCommande(Sortie):
    """Un conditionnement où la matière se commande, et sa contenance en kilos."""

    unite: str
    contenance: float


class BonEnPreparation(Sortie):
    """Un bon pas encore parti qui porte déjà la matière (déduit de la suggestion)."""

    id: int | None
    numero: str


class LignePlan(Sortie):
    """Une matière à commander, dans l'ordre du plan (montant pondéré par la classe ABC)."""

    matiere_id: int | None
    fournisseur_id: int | None
    reference: str
    nature: str
    designation: str
    fournisseur: str
    classe_abc: str
    statut: str
    quantite: float = Field(description="kg à commander")
    unite_achat: str
    quantite_achat: float
    unite_commande: str
    unites_commande: float
    contenance_commande: float
    prix: float = Field(description="prix du catalogue au kg, devise de la matière")
    devise: str
    montant_devise: float
    montant_mad: float
    palettes: float
    tier: str
    risque: str
    action: str
    relance: str
    en_preparation: float
    bons_en_preparation: list[BonEnPreparation]
    stock_disponible: float
    stock_net: float
    stock_projete: float
    commande_kg: float = Field(description="bons partis attendus (dans et au-delà du délai)")
    couverture_jours: float | None
    conso_mensuelle: float
    kg_par_ml: float
    unites_possibles: list[UniteCommande]


class GroupeFournisseur(Sortie):
    """Ce qu'il y a à commander chez un fournisseur (montants par devise, jamais additionnés)."""

    fournisseur_id: int | None
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
    critiques: int
    urgents: int


class IndicateursPlan(Sortie):
    """Les indicateurs du plan (les ruptures… comptées sur toutes les matières)."""

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


class PlanAchat(Sortie):
    """Route 149 : ce qu'il faut commander, chez qui, et quand."""

    date_reference: date
    indicateurs: IndicateursPlan
    fournisseurs: list[GroupeFournisseur]
    lignes: list[LignePlan]


class Depart(Sortie):
    """La ligne telle que la préparation la propose d'abord (unité, kilos, unités)."""

    unite: str
    contenance: float
    quantite: float
    unites: float


class LignePreparation(Sortie):
    """Une suggestion du calcul chez le fournisseur."""

    matiere_id: int | None
    reference: str
    nature: str
    designation: str
    statut: str
    classe_abc: str
    kg_par_ml: float
    stock_projete: float
    conso_mensuelle: float
    couverture_jours: float | None
    quantite_suggeree: float
    palettes_suggerees: float
    contenance_palette: float
    unite_commande: str
    contenance_commande: float
    unites_suggerees: float
    unites_possibles: list[UniteCommande]
    minimum_commande: float
    prix_indicatif: float
    devise: str
    montant_indicatif_mad: float
    en_preparation: float
    bons_en_preparation: list[BonEnPreparation]
    depart: Depart


class PreparationCommande(Sortie):
    """Route 150 : la préparation d'une commande chez un fournisseur."""

    fournisseur_id: int
    fournisseur: str
    pays: str
    contact: str
    email: str
    delai_jours: float
    devise_par_defaut: str
    date_reference: date
    lignes: list[LignePreparation]
