"""Classeurs de la production (route 237) : plan glissant, plan et réalisé, besoins matière.

Conventions de `exports/classeur.py` (lot D9). Les besoins ne portent pas le conseil d'achat
pour l'alimentation (E-01) : la colonne de quantité à commander est retirée (barrière 4).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from gestion_mp_pro.calcul.constantes import LIBELLES_STATUT
from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, titre

MOIS = 12


def _mois(i: int, mois: list[date], cle: str, grandeur: str) -> Colonne:
    """La colonne d'un mois (« 10/2026 ») d'une série de douze valeurs."""
    lire: Callable[[dict[str, Any]], object] = lambda x: x[cle][i]  # noqa: E731
    return Colonne(f"{mois[i]:%m/%Y}", lire, grandeur)


def glissant(vue: dict[str, Any]) -> bytes:
    """Le plan glissant : une ligne par qualité, douze mois (m²)."""
    colonnes = [
        Colonne("Qualité", lambda x: x["code"]),
        Colonne("Nom", lambda x: x["nom"]),
        Colonne("En service", lambda x: x["actif"]),
        Colonne("Base (m²/mois)", lambda x: x["base_mensuelle"], "m2"),
        *[_mois(i, vue["mois"], "glissant", "m2") for i in range(MOIS)],
        Colonne("Total (m²)", lambda x: x["total_glissant"], "m2"),
        Colonne("kg / m² (perte comprise)", lambda x: x["kg_m2"], "#,##0.0000"),
    ]
    entete = [titre("Plan glissant", vue["date_reference"])]
    return classeur([Feuille("Plan glissant", colonnes, vue["qualites"], entete)], True)


def realise(vue: dict[str, Any]) -> bytes:
    """Le plan et le réalisé : deux lignes par qualité (plan, tissé), douze mois écoulés."""
    lignes = [
        {"qualite": x["qualite"], "serie": serie, "valeurs": x[cle], "total": x[total],
         "ecart": x["ecart"]}
        for x in vue["lignes"]
        for serie, cle, total in (("Plan", "plan", "total_plan"),
                                  ("Tissé", "realise", "total_realise"))
    ]  # fmt: skip
    mois = [date.fromisoformat(m) for m in vue["mois"]]
    colonnes = [
        Colonne("Qualité", lambda x: x["qualite"]),
        Colonne("Série", lambda x: x["serie"]),
        *[_mois(i, mois, "valeurs", "m2") for i in range(MOIS)],
        Colonne("Total (m²)", lambda x: x["total"], "m2"),
        Colonne("Écart des mois clos", lambda x: x["ecart"], "pourcent"),
    ]
    entete = [titre("Plan et réalisé", vue["date_reference"])]
    return classeur([Feuille("Plan et réalisé", colonnes, lignes, entete)], True)


def besoins(vue: dict[str, Any], conseil: bool) -> bytes:
    """Les besoins matière : une ligne par matière, douze mois (kg), et ce qu'en retient
    le plan d'achat (sans quantité à commander pour l'alimentation)."""
    colonnes = [
        Colonne("Référence", lambda x: x["reference"]),
        Colonne("Rôle", lambda x: x["role"]),
        Colonne("Fournisseur", lambda x: x["fournisseur"]),
        *[_mois(i, vue["mois"], "kg", "kg") for i in range(MOIS)],
        Colonne("Besoin sur 12 mois (kg)", lambda x: x["total"], "kg"),
        Colonne("Retenu sur 12 mois (kg)", lambda x: x["total_retenu"], "kg"),
        Colonne("Coefficient de réalisation", lambda x: x["coefficient_realisation"], "cours"),
        Colonne("Disponible (kg)", lambda x: x["stock_disponible"], "kg"),
        Colonne("Commandes en cours (kg)", lambda x: x["bc_en_cours"], "kg"),
        Colonne("Projeté (kg)", lambda x: x["stock_projete"], "kg"),
        Colonne("Statut", lambda x: LIBELLES_STATUT.get(x["statut"], x["statut"])),
    ]
    if conseil:
        colonnes.append(Colonne("À commander (kg)", lambda x: x["quantite_a_commander"], "kg"))
    entete = [titre("Besoins matière", vue["date_reference"])]
    return classeur([Feuille("Besoins matière", colonnes, vue["lignes"], entete)], True)
