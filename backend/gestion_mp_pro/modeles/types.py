"""Types des colonnes : nombres exacts par catégorie, énumérations, arrondi (MODELE-DONNEES § 1.1).

La base garde des `Decimal` exacts ; une écriture se calcule en `Decimal` et s'arrondit **une
fois**, à l'écriture, `ROUND_HALF_UP` à l'échelle de sa colonne : `arrondir(valeur, QUANTITE)`.
Aucun `NaN` n'entre en base (CHECK `ck_<table>_<colonne>_nombre` sur chaque colonne `NUMERIC`,
étape 18 de Gestion MP généralisée) ; l'infini, lui, est refusé par PostgreSQL lui-même
(`numeric field overflow`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

from sqlalchemy import Enum, Numeric


@dataclass(frozen=True)
class Nombre:
    """Une catégorie de nombre : précision et échelle de sa colonne `NUMERIC(p, s)`."""

    nom: str
    precision: int
    echelle: int

    def type_sql(self) -> Numeric[Decimal]:
        """Le type SQLAlchemy de la colonne (valeurs lues en `Decimal`)."""
        return Numeric(self.precision, self.echelle, asdecimal=True)

    @property
    def pas(self) -> Decimal:
        """Le plus petit écart représentable : 0,001 pour une quantité."""
        return Decimal(1).scaleb(-self.echelle)

    @property
    def maximum(self) -> Decimal:
        """La plus grande valeur absolue que la colonne accepte."""
        return Decimal(10) ** (self.precision - self.echelle) - self.pas


QUANTITE = Nombre("quantité (kg)", 14, 3)
PRIX = Nombre("prix unitaire", 18, 6)
MONTANT = Nombre("montant", 16, 2)
COURS = Nombre("cours de change", 14, 6)
TAUX = Nombre("taux (fraction)", 9, 6)
POURCENTAGE = Nombre("pourcentage 0–100", 9, 6)
MESURE = Nombre("mesure fine", 14, 6)
UNITES = Nombre("compte d'unités", 12, 3)
SURFACE = Nombre("surface (m²)", 14, 3)
COEFFICIENT = Nombre("coefficient", 8, 4)
MOIS = Nombre("durée en mois", 8, 3)
LONGUEUR = Nombre("longueur (m)", 8, 3)
PRIORITE = Nombre("priorité 0–100", 6, 2)
BOBINES_PAR_METRE = Nombre("bobines par mètre", 10, 3)
JOURS = Nombre("jours (décimaux)", 10, 2)
TAUX_FRAIS = Nombre("taux d'un frais (%)", 7, 4)

CATEGORIES: tuple[Nombre, ...] = (
    QUANTITE, PRIX, MONTANT, COURS, TAUX, POURCENTAGE, MESURE, UNITES, SURFACE, COEFFICIENT,
    MOIS, LONGUEUR, PRIORITE, BOBINES_PAR_METRE, JOURS, TAUX_FRAIS,
)  # fmt: skip


def arrondir(valeur: Decimal | float | int | str, categorie: Nombre) -> Decimal:
    """La valeur arrondie au pas de sa colonne, demi vers le haut (2,0005 kg → 2,001 kg).

    Un flottant est lu par son écriture la plus courte (`0.1` vaut 0,1, pas 0,1000000000000000055) ;
    `NaN`, l'infini ou une valeur hors de la colonne lèvent `ValueError`.
    """
    if isinstance(valeur, float) and not math.isfinite(valeur):
        raise ValueError(f"{categorie.nom} : nombre attendu, pas {valeur!r}")
    try:
        exact = valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))
    except InvalidOperation as exc:
        raise ValueError(f"{categorie.nom} : nombre attendu, pas {valeur!r}") from exc
    if not exact.is_finite():
        raise ValueError(f"{categorie.nom} : nombre attendu, pas {valeur!r}")
    resultat = exact.quantize(categorie.pas, rounding=ROUND_HALF_UP)
    if abs(resultat) > categorie.maximum:
        raise ValueError(f"{categorie.nom} : {valeur} dépasse {categorie.maximum}")
    return resultat


def enumeration(classe: type[StrEnum], longueur: int) -> Enum:
    """Le type d'une colonne énumérée : `VARCHAR(longueur)`, valeurs (et non noms) de la classe.

    Le CHECK des valeurs n'est pas posé par le type (`create_constraint=False`) mais par
    `base.completer_le_schema`, avec le nom `ck_<table>_<colonne>_enum` : la migration le
    porte en clair, sans dépendre de la convention de nommage du moment.
    """
    return Enum(
        classe,
        native_enum=False,
        create_constraint=False,
        length=longueur,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
