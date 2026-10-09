"""Classeur des qualités et de leurs recettes (route 93 ; Gestion MP A39).

Une ligne par matière de chaque recette (une ligne vide de recette pour une qualité sans
matière). « En service » dit l'état de la qualité et « Fabriquée » si un ordre l'a tissée :
Gestion MP écrivait l'état sous le titre « Fabriquée » (D-19). Conventions de
`exports/classeur.py` (lot D9).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, exporte_le

Ligne = tuple[dict[str, Any], dict[str, Any]]
"""(qualité, ligne de recette) ; la ligne est vide pour une qualité sans recette."""


def _oui(valeur: object) -> str:
    """« oui » / « non »."""
    return "oui" if valeur else "non"


def _r(cle: str) -> Callable[[Ligne], object]:
    """La valeur d'un champ de la ligne de recette."""
    return lambda x: x[1].get(cle)


def _q(cle: str) -> Callable[[Ligne], object]:
    """La valeur d'un champ de la qualité."""
    return lambda x: x[0].get(cle)


def _unite(x: Ligne) -> str:
    """« USD / kg », « MAD / ml »."""
    ligne = x[1]
    return f"{ligne['devise_prix']} / {ligne['unite_prix']}" if ligne else ""


COLONNES = (
    Colonne("Qualité", _q("code")),
    Colonne("Nom", _q("nom")),
    Colonne("En service", lambda x: _oui(x[0]["actif"])),
    Colonne("Fabriquée", lambda x: _oui(x[0]["fabrications"])),
    Colonne("Rôle", _r("role")),
    Colonne("Référence", _r("reference")),
    Colonne("Fournisseur", _r("fournisseur")),
    Colonne("Part du rôle (%)", _r("pourcentage"), "#,##0.00"),
    Colonne("kg / m²", _r("kg_m2"), "#,##0.0000"),
    Colonne("ml / m²", _r("ml_m2"), "#,##0.0000"),
    Colonne("Prix d'achat", _r("prix"), "prix", monetaire=True),
    Colonne("Unité du prix", _unite, monetaire=True),
    Colonne("Coût / m² (MAD)", _r("cout_m2_mad"), "montant", monetaire=True),
    Colonne("Coût de la qualité / m² (MAD)", _q("cout_m2_mad"), "montant", monetaire=True),
)


def qualites(liste: Sequence[dict[str, Any]], jour: date, voit_prix: bool = True) -> bytes:
    """Le classeur « Qualités et recettes »."""
    lignes: list[Ligne] = [(q, x) for q in liste for x in (q["recette"] or [{}])]
    entete = [exporte_le("Qualités et recettes", jour)]
    return classeur([Feuille("Qualités et recettes", COLONNES, lignes, entete)], voit_prix)
