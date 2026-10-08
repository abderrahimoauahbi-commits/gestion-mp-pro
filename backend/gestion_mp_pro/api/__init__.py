"""Couche HTTP : la liste des domaines, dans l'ordre d'inclusion, et leurs étiquettes OpenAPI.

Fichier du lot S0, pré-rempli avec **tous** les domaines d'API-PRO § 1 ; aucun autre lot ne
l'édite (LOTS § 0.3). Chaque domaine est un paquet `api/<module>/` dont `routes.py` expose
`routeur` (créé par `communs.nouveau_routeur("<module>")`). Ce module n'importe rien de lourd :
`api.erreurs` reste importable par les services sans charger les routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter


@dataclass(frozen=True)
class Domaine:
    """Un domaine de l'API : son paquet, son étiquette OpenAPI, sa section d'API-PRO."""

    module: str
    etiquette: str
    description: str


DOMAINES: tuple[Domaine, ...] = (
    Domaine("systeme", "Système", "Santé, état, contexte, accès, données brutes (API-PRO 1.1)."),
    Domaine("comptes", "Comptes et appareils", "Connexion, sessions, comptes, appareils (1.2)."),
    Domaine("reglages", "Réglages", "Réglages métier, devises et cours, période close (1.3)."),
    Domaine("exploitation", "Exploitation", "Serveur, sauvegardes, restauration, tâches (1.4)."),
    Domaine(
        "journal", "Journal et historique", "Journal des actions, historique d'une fiche (1.5)."
    ),
    Domaine("notifications", "Notifications et recherche", "Cloche, recherche globale (1.6)."),
    Domaine("classification", "Classification", "Compositions, types, titrages, couleurs (1.7)."),
    Domaine("fournisseurs", "Fournisseurs", "Fiches, usages, délais mesurés (1.8)."),
    Domaine("matieres", "Matières", "Catalogue, composition, classement, tableur (1.9)."),
    Domaine("qualites", "Qualités", "Qualités, recettes et versions, plan (1.10)."),
    Domaine("metiers", "Métiers et montage", "Métiers à tisser, étages, montage (1.11)."),
    Domaine("stock", "Stock et lots", "Soldes, lots, mouvements, scan, étiquettes (1.12)."),
    Domaine(
        "operations", "Opérations de stock", "Sorties, retours, transferts, brouillons (1.13)."
    ),
    Domaine("inventaires", "Inventaires", "Ouverture, comptages, validation, abandon (1.14)."),
    Domaine("ordres", "Ordres de fabrication", "Proposition, validation, annulation (1.15)."),
    Domaine("production", "Production et besoins", "Plan global, réalisé, besoins (1.16)."),
    Domaine("plan_achat", "Plan d'achat", "Plan d'achat, préparation par fournisseur (1.17)."),
    Domaine("commandes", "Commandes", "Bons de commande, approbation, expédition (1.18)."),
    Domaine("receptions", "Réceptions et factures", "Réceptions, pesées, factures (1.19)."),
    Domaine("reclamations", "Réclamations", "Réclamations aux fournisseurs (1.20)."),
    Domaine("importations", "Importations", "Dossiers d'importation, coût de revient (1.21)."),
    Domaine("pilotage", "Pilotage et analyse", "Cockpit, valorisation, prix, contrôles (1.22)."),
    Domaine("suivi", "Suivi", "Signalements, pièces jointes, échéancier, bilan (1.23)."),
    Domaine("reprise", "Reprise", "Miroir de Gestion MP : état et rafraîchissement (1.24)."),
    Domaine("documents", "Documents", "Documents imprimables A4 : bon, étiquettes, bilan."),
)
"""Ordre d'inclusion des routeurs (les chemins qui se recouvrent sont départagés par cet ordre)."""

ETIQUETTES: dict[str, str] = {d.module: d.etiquette for d in DOMAINES}


def routeurs() -> list[APIRouter]:
    """Les routeurs de tous les domaines, dans l'ordre d'inclusion (import à la demande)."""
    return [import_module(f"{__name__}.{d.module}.routes").routeur for d in DOMAINES]


def etiquettes_openapi() -> list[dict[str, str]]:
    """Les étiquettes OpenAPI (`openapi_tags`), une par domaine, dans l'ordre."""
    return [{"name": d.etiquette, "description": d.description} for d in DOMAINES]
