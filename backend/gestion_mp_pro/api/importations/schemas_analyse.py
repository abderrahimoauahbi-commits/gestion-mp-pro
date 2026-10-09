"""Schémas de sortie du coût de revient (routes 206, 207) : aux clés des dataclasses du moteur
(`calcul/analyse_revient_lignes.py`, `calcul/analyse_revient_qualite.py`), elles-mêmes celles
de Gestion MP (`gestion_mp/api/analyse_import.py`).
"""

from __future__ import annotations

import datetime as dt

from gestion_mp_pro.api.communs import Sortie


class GroupeRevient(Sortie):
    """Un groupe de l'analyse (une valeur de l'axe) ; `role` … `cout_m2` : coût d'une qualité."""

    valeur: str
    quantite: float | None
    unites: list[str]
    poids: float
    marchandise_mad: float
    charges_mad: float
    tva_mad: float
    lignes: int
    dossiers: list[str]
    detail: dict[str, float]
    unite: str | None
    revient_mad: float
    decaisse_mad: float
    marchandise_unite: float | None
    revient_unite: float | None
    marchandise_kg: float
    revient_kg: float
    surcout: float
    role: str | None = None
    part_recette: float | None = None
    poids_m2: float | None = None
    cout_m2: float | None = None


class LigneDetailRevient(Sortie):
    """Une marchandise qui a fait le compte (vue « Lot par lot »)."""

    dossier: str
    date_arrivee: dt.date | None
    statut: str
    reference: str
    lot_fournisseur: str
    fournisseur: str
    composition: str
    type_fil: str
    titrage: str
    couleur: str
    role_bom: str
    quantite: float
    unite: str
    poids: float
    marchandise_mad: float
    charges_mad: float
    revient_mad: float
    tva_mad: float
    decaisse_mad: float
    valeur_unite: float
    revient_unite: float
    revient_kg: float
    surcout: float


class DossierNonReparti(Sortie):
    """Les frais d'un dossier qu'aucune marchandise ne porte (dans aucun coût)."""

    dossier: str
    montant: float


class AnalyseRevient(Sortie):
    """Ce que la matière importée a coûté, rendue usine, regroupé par axe (route 206)."""

    axe: str
    ids_dossiers: dict[str, int]
    frais_non_repartis_mad: float
    dossiers_non_repartis: list[DossierNonReparti]
    libelle_axe: str
    lignes: list[GroupeRevient]
    detail_lignes: list[LigneDetailRevient]
    total_lignes: int
    total_poids: float
    total_marchandise_mad: float
    total_charges_mad: float
    total_revient_mad: float
    total_tva_mad: float
    total_decaisse_mad: float


class RoleQualite(Sortie):
    """Un rôle de la recette : poids au m², part dont le coût est connu, coût au m²."""

    role: str
    poids_m2: float
    lineaire: bool
    connu_m2: float
    cout_m2: float
    fils: int
    importes: int


class CoutQualite(AnalyseRevient):
    """Le coût matière d'une qualité, pondéré par sa recette (route 207)."""

    qualite: str
    nom: str
    references_de_la_recette: int
    references_importees: int
    roles: list[RoleQualite]
    poids_m2: float
    couverture: float
    cout_m2: float
    cout_m2_estime: float
    cout_kg_tapis: float
    roles_sans_cout: list[str]
