"""Classeur des métiers et de leurs fils montés (route 238 ; ECRANS-PRO partie 3, an. 29).

Une ligne par fil monté (une ligne pour un métier sans fil). La valeur n'apparaît que pour
qui voit les prix (barrière 4 : un classeur n'est pas filtré par la route).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from gestion_mp_pro.exports.stock import Colonne, classeur

Ligne = tuple[dict[str, Any], dict[str, Any]]
"""(métier, fil) ; le fil est vide pour un métier sans fil."""


def _m(cle: str) -> Callable[[Ligne], object]:
    """Un champ du métier."""
    return lambda x: x[0].get(cle)


def _f(cle: str) -> Callable[[Ligne], object]:
    """Un champ du fil."""
    return lambda x: x[1].get(cle)


def _nom(x: Ligne) -> str:
    """« M1 · Métier du fond »."""
    m = x[0]
    return f"{m['code']} · {m['nom']}" if m["nom"] and m["nom"] != m["code"] else m["code"]


COLONNES = (
    Colonne("Métier", _nom, largeur=24),
    Colonne("État", lambda x: "en service" if x[0]["actif"] else "arrêté", largeur=10),
    Colonne("Laize (m)", _m("laize"), "montant"),
    Colonne("Bobines par mètre", _m("bobines_par_metre"), "montant"),
    Colonne("Étage", _f("etage"), largeur=8),
    Colonne("Référence", _f("reference"), largeur=30),
    Colonne("Désignation", _f("designation"), largeur=24),
    Colonne("Mètres", _f("metres"), "montant"),
    Colonne("Part (%)", _f("pourcentage"), "montant"),
    Colonne("Bobines", _f("bobines"), "montant"),
    Colonne("kg / bobine retenu", _f("poids_bobine_utilise"), "kg"),
    Colonne("Origine du poids", _f("source_poids"), largeur=20),
    Colonne("Sur les métiers (kg)", _f("poids"), "kg"),
    Colonne("Valeur (MAD)", _f("valeur_mad"), "montant", monetaire=True),
    Colonne("Observations", _f("commentaire"), largeur=30),
)


def metiers(liste: Sequence[dict[str, Any]], voit_prix: bool) -> bytes:
    """Le classeur « Métiers »."""
    lignes: list[Ligne] = [(m, f) for m in liste for f in (m["fils"] or [{}])]
    return classeur("Métiers", COLONNES, lignes, voit_prix)
