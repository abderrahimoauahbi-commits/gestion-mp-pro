"""Schémas Pydantic du domaine « Qualités » (API-PRO § 1.10, routes 82–93).

Les nombres saisis sont des `Decimal` finis (un `NaN` ou un infini est refusé en 422 : D-01) ;
les bornes qui ont un message de Gestion MP (coefficient 0–20, poids négatif, 100 % par rôle)
sont vérifiées par le service, avec ce message mot pour mot. Les sorties portent les
identifiants (matière, rôle, qualité) à côté des libellés.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Personne, Sortie
from gestion_mp_pro.modeles import longueurs as L

Fini = Annotated[Decimal, Field(allow_inf_nan=False)]
POIDS_MAXI = Decimal(1_000_000)
BASE_MAXI = Decimal(1_000_000_000)
COEFFICIENT_SAISI_MAXI = Decimal(1_000_000)
MOIS = 12
LIGNES_MAXI = 500


class PoidsEntree(Entree):
    """Le poids d'un m² de tapis pour un rôle : kg/m², ou ml/m² pour un rôle au mètre."""

    role_id: int = Field(ge=1)
    poids: Fini = Field(le=POIDS_MAXI, description="kg/m² (ml/m² pour Cuir, Franges, Ruban)")


class LigneRecetteEntree(Entree):
    """Une matière de la recette et sa part dans son rôle."""

    matiere_id: int = Field(ge=1)
    pourcentage: Fini = Field(ge=0, le=100)


class QualiteCreation(Entree):
    """Une nouvelle qualité : code (tel qu'il figure sur les ordres), nom, poids par rôle."""

    code: str = Field(min_length=1, max_length=L.CODE_QUALITE)
    nom: str = Field("", max_length=L.NOM_QUALITE)
    actif: bool = True
    poids: list[PoidsEntree] = Field(default_factory=list, max_length=50)


class QualiteModification(QualiteCreation):
    """La fiche entière (remplacement) et, facultative, la recette dans la même transaction."""

    version: int = Field(ge=1)
    recette: list[LigneRecetteEntree] | None = Field(None, max_length=LIGNES_MAXI)
    motif: str = Field("", max_length=L.MOTIF)


class RecetteEntree(Entree):
    """La recette entière d'une qualité (remplacement)."""

    lignes: list[LigneRecetteEntree] = Field(max_length=LIGNES_MAXI)
    motif: str = Field("", max_length=L.MOTIF)
    version: int = Field(ge=1)


class RestaurationVersionRecette(Entree):
    """Revenir à une version : le motif est obligatoire."""

    motif: str = Field(min_length=1, max_length=L.MOTIF)
    version: int = Field(ge=1)


Coefficient = Annotated[Decimal, Field(allow_inf_nan=False, ge=-COEFFICIENT_SAISI_MAXI,
                                       le=COEFFICIENT_SAISI_MAXI)]  # fmt: skip
"""Un coefficient saisi : fini ; « entre 0 et 20 » est dit par le service (message de GMP)."""


class PlanQualiteEntree(Entree):
    """Le plan d'une qualité : base (m² par mois ordinaire) et douze coefficients (0 à 20)."""

    base_mensuelle: Fini = Field(ge=0, le=BASE_MAXI)
    coefficients: list[Coefficient] = Field(min_length=MOIS, max_length=MOIS)
    motif: str = Field("", max_length=L.MOTIF)
    version: int = Field(ge=1)


class PoidsRole(Sortie):
    """Le poids au m² d'un rôle dans une qualité (les rôles à 0 ne sont pas enregistrés)."""

    role_id: int
    role: str
    lineaire: bool
    poids: Nombre


class LigneRecetteFiche(Sortie):
    """Une ligne de recette calculée par le moteur (nomenclature)."""

    qualite_id: int | None
    qualite: str
    matiere_id: int | None
    reference: str
    role_id: int | None
    role: str = Field(description="vide : matière inconnue")
    lineaire: bool
    nature: str
    designation: str
    fournisseur: str
    pourcentage: float
    kg_m2: float
    ml_m2: float | None = Field(description="rôle au mètre : poids du rôle (ml/m²) × part")
    densite: float = Field(description="kg/ml")
    prix_kg: float | None
    prix: float | None = Field(description="comme on l'achète : au kilo ou au mètre")
    unite_prix: str | None
    devise_prix: str | None
    cout_m2_mad: float | None = Field(description="kg/m² × prix au kilo × cours × perte")


class EcartRole(Sortie):
    """Un rôle dont les parts ne font pas 100 %."""

    role: str
    somme: float


class ControleQualite(Sortie):
    """Le contrôle des 100 % par rôle (même tolérance que l'enregistrement : 0,01 point)."""

    roles_utilises: int
    roles_conformes: int
    ecarts: list[EcartRole]
    conforme: bool


class ControleNomenclature(ControleQualite):
    """Le contrôle d'une qualité dans la nomenclature (les arrêtées se signalent à part)."""

    qualite_id: int | None
    qualite: str
    actif: bool


class FacteursCout(Sortie):
    """De quoi recalculer le coût d'une recette à la frappe : perte et cours des devises."""

    perte: float = Field(description="1 + taux de perte")
    cours: dict[str, float] | None


class QualiteResume(Sortie):
    """Une qualité, sa recette calculée, son contrôle, son coût au m² et son plan."""

    id: int
    code: str
    nom: str
    actif: bool
    version: int
    base_mensuelle: Nombre
    saisonnalite: list[float]
    poids: list[PoidsRole]
    recette: list[LigneRecetteFiche]
    controle: ControleQualite
    kg_m2: float
    cout_m2_mad: float | None
    fabrications: int = Field(description="ordres de fabrication qui la nomment")
    facteurs_cout: FacteursCout


class QualiteFiche(QualiteResume):
    """La fiche d'une qualité, avec l'avertissement du dernier geste (rôles sans matière)."""

    avertissement: str = ""


class LigneVersionRecette(Sortie):
    """Une matière d'une version de recette, avec son rôle à cette date."""

    matiere_id: int
    reference: str
    role_id: int
    role: str
    pourcentage: Nombre


class PoidsVersion(Sortie):
    """Le poids au m² d'un rôle avec cette version."""

    role_id: int
    role: str
    poids: Nombre


class RecetteVersionFiche(Sortie):
    """Une version de la recette (la plus récente est « en vigueur »)."""

    id: int
    numero: int
    valide_depuis: datetime
    par: Personne | None
    origine: str
    motif: str
    restauree_de: int | None = Field(description="numéro de la version restaurée")
    en_vigueur: bool
    lignes: list[LigneVersionRecette]
    poids: list[PoidsVersion] | None = Field(description="null : poids non gardés alors")


class PlanVersionFiche(Sortie):
    """Une version du plan ; la plus ancienne vaut « depuis toujours »."""

    id: int
    valide_depuis: datetime
    base_mensuelle: Nombre
    saisonnalite: list[float]
    en_service: bool
    par: Personne | None
    origine: str
    motif: str
    en_vigueur: bool
    depuis_toujours: bool


class Nomenclature(Sortie):
    """Chaque matière de chaque qualité, et le contrôle des recettes."""

    lignes: list[LigneRecetteFiche]
    controle: list[ControleNomenclature]
