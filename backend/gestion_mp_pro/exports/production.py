"""Classeurs de la production (route 237 : plan glissant, plan et réalisé, besoins matière) et
le téléchargement d'un classeur pour les routes du lot D2 (93, 237, 238).

Les besoins ne portent pas le conseil d'achat pour l'alimentation (E-01) : les colonnes de
quantité à commander sont retirées (barrière 4).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import Response

from gestion_mp_pro.exports.stock import Colonne, classeur, nom_de_fichier
from gestion_mp_pro.services import horloge

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MOIS = 12


def telecharger(contenu: bytes, prefixe: str) -> Response:
    """Un classeur à télécharger (« qualites-2026-10-08.xlsx »)."""
    nom = nom_de_fichier(prefixe, horloge.aujourd_hui())
    return Response(
        contenu, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nom}"'}
    )


def _mois(i: int, mois: list[date], cle: str) -> Colonne:
    """La colonne d'un mois (« 10/2026 ») d'une série de douze valeurs."""
    titre = f"{mois[i]:%m/%Y}"
    lire: Callable[[dict[str, Any]], object] = lambda x: x[cle][i]  # noqa: E731
    return Colonne(titre, lire, "kg", largeur=11)


def glissant(vue: dict[str, Any]) -> bytes:
    """Le plan glissant : une ligne par qualité, douze mois (m²)."""
    colonnes = [
        Colonne("Qualité", lambda x: x["code"], largeur=14),
        Colonne("Nom", lambda x: x["nom"], largeur=24),
        Colonne("En service", lambda x: "oui" if x["actif"] else "non", largeur=10),
        Colonne("Base (m²/mois)", lambda x: x["base_mensuelle"], "kg"),
        *[_mois(i, vue["mois"], "glissant") for i in range(MOIS)],
        Colonne("Total (m²)", lambda x: x["total_glissant"], "kg"),
        Colonne("kg / m² (perte comprise)", lambda x: x["kg_m2"], "prix"),
    ]
    return classeur("Plan glissant", colonnes, vue["qualites"], True)


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
        Colonne("Qualité", lambda x: x["qualite"], largeur=14),
        Colonne("Série", lambda x: x["serie"], largeur=8),
        *[_mois(i, mois, "valeurs") for i in range(MOIS)],
        Colonne("Total (m²)", lambda x: x["total"], "kg"),
        Colonne("Écart des mois clos (%)", lambda x: x["ecart"], "prix"),
    ]
    return classeur("Plan et réalisé", colonnes, lignes, True)


def besoins(vue: dict[str, Any], conseil: bool) -> bytes:
    """Les besoins matière : une ligne par matière, douze mois (kg), et ce qu'en retient
    le plan d'achat (sans quantité à commander pour l'alimentation)."""
    colonnes = [
        Colonne("Référence", lambda x: x["reference"], largeur=30),
        Colonne("Rôle", lambda x: x["role"], largeur=10),
        Colonne("Fournisseur", lambda x: x["fournisseur"], largeur=22),
        *[_mois(i, vue["mois"], "kg") for i in range(MOIS)],
        Colonne("Besoin sur 12 mois (kg)", lambda x: x["total"], "kg"),
        Colonne("Retenu sur 12 mois (kg)", lambda x: x["total_retenu"], "kg"),
        Colonne("Coefficient de réalisation", lambda x: x["coefficient_realisation"], "prix"),
        Colonne("Disponible (kg)", lambda x: x["stock_disponible"], "kg"),
        Colonne("Commandes en cours (kg)", lambda x: x["bc_en_cours"], "kg"),
        Colonne("Projeté (kg)", lambda x: x["stock_projete"], "kg"),
        Colonne("Statut", lambda x: x["statut"], largeur=16),
    ]
    if conseil:
        colonnes.append(Colonne("À commander (kg)", lambda x: x["quantite_a_commander"], "kg"))
    return classeur("Besoins matière", colonnes, vue["lignes"], True)
