"""Schémas Pydantic du domaine « Production et besoins » (API-PRO § 1.16, routes 145–148, 237).

Le plan glissant n'est pas stocké : base × coefficient du mois × croissance annuelle. Le passé
(plan et réalisé, coefficient de réalisation) est jugé sur le plan de son époque.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L

Fini = Annotated[Decimal, Field(allow_inf_nan=False)]
COEFFICIENT_SAISI_MAXI = Decimal(1_000_000)
Coefficient = Annotated[
    Decimal, Field(allow_inf_nan=False, ge=-COEFFICIENT_SAISI_MAXI, le=COEFFICIENT_SAISI_MAXI)
]
MOIS = 12


class LignePlanEntree(Entree):
    """Le plan d'une qualité dans le plan global, avec la version lue de la qualité."""

    qualite_id: int = Field(ge=1)
    base_mensuelle: Fini = Field(ge=0, le=1_000_000_000)
    coefficients: list[Coefficient] = Field(min_length=MOIS, max_length=MOIS)
    version: int = Field(ge=1)


class PlanGlobalEntree(Entree):
    """Le plan de plusieurs qualités, enregistré d'un bloc (tout ou rien)."""

    qualites: list[LignePlanEntree] = Field(min_length=1, max_length=1000)
    motif: str = Field("", max_length=L.MOTIF)


class QualitePlan(Sortie):
    """Une qualité du plan de production."""

    id: int
    code: str
    nom: str
    actif: bool
    version: int
    base_mensuelle: Nombre
    saisonnalite: list[float]
    total_annuel: float = Field(description="base × saisonnalité sur un an, hors croissance")
    glissant: list[float] = Field(description="m² des douze mois à venir (M0 = mois en cours)")
    total_glissant: float
    kg_m2: float = Field(description="kg de matière par m², perte comprise")
    lignes_recette: int
    recette_conforme: bool
    tisse_mois_en_cours: float


class TisseHorsPlan(Sortie):
    """Une qualité tissée ce mois-ci alors que son plan du mois est nul."""

    qualite_id: int | None
    qualite: str
    m2: float


class PlanProduction(Sortie):
    """Le plan de toutes les qualités (et, après un enregistrement, combien ont changé)."""

    date_reference: date
    mois: list[date]
    croissance_annuelle: float
    taux_perte: float
    qualites: list[QualitePlan]
    tisse_hors_plan: list[TisseHorsPlan]
    modifiees: int | None = None


class RealiseQualite(Sortie):
    """Le plan et le réalisé d'une qualité sur douze mois écoulés."""

    qualite_id: int | None
    qualite: str
    plan: list[float]
    realise: list[float]
    total_plan: float
    total_realise: float
    ecart: float | None = Field(description="fraction, sur les mois clos")


class PlanEtRealise(Sortie):
    """Ce que l'atelier a tissé face au plan, chaque mois clos sur le plan de son époque."""

    date_reference: date
    mois: list[date]
    mois_clos: int
    lignes: list[RealiseQualite]
    debut_service: date | None
    plan_fige: bool


class BesoinQualite(Sortie):
    """Une qualité qui tire le besoin d'une matière."""

    qualite_id: int | None
    qualite: str
    kg_m2: float
    kg: list[float]
    total: float


class BesoinMatiere(Sortie):
    """Le besoin d'une matière par mois, et ce que le plan d'achat en retient."""

    matiere_id: int | None
    reference: str
    nature: str
    designation: str
    fournisseur: str
    role: str
    kg_par_ml: float
    kg: list[float]
    total: float
    retenu: list[float]
    total_retenu: float
    coefficient_realisation: float | None
    conso_reelle: float | None
    stock_disponible: float
    bc_en_cours: float
    stock_projete: float
    couverture_jours: float | None
    statut: str
    quantite_a_commander: float | None
    unite_achat: str
    quantite_a_commander_achat: float | None
    qualites: list[BesoinQualite]


class BesoinsDetailles(Sortie):
    """Le MRP par matière et par mois, à la date de référence."""

    date_reference: date
    mois: list[date]
    taux_perte: float
    fenetre_realisation_jours: float
    roles: list[str]
    lignes: list[BesoinMatiere]
