"""Les structures du moteur (dataclasses), identiques à celles de Gestion MP (CALCULS § 1).

Le moteur les reçoit telles quelles : de PostgreSQL par `services/donnees_moteur.py` (S4), ou
d'un jeu figé en JSON (essais de parité). Les types de mouvement sont des codes stables.
"""

from __future__ import annotations

from gestion_mp_pro.calcul.modele.donnees import CleSolde, Donnees
from gestion_mp_pro.calcul.modele.flux import (
    ChargeImport,
    Commande,
    DossierImport,
    LigneCommande,
    LigneImport,
    LignePrix,
    LigneReception,
    Mouvement,
    OrdreFabrication,
    Reception,
)
from gestion_mp_pro.calcul.modele.referentiels import (
    Article,
    FilMonte,
    Fournisseur,
    LigneRecette,
    Magasin,
    Metier,
    Parametres,
    PlanQualite,
    Qualite,
    VersionPlan,
    VersionRecette,
)

__all__ = [
    "Article",
    "ChargeImport",
    "CleSolde",
    "Commande",
    "Donnees",
    "DossierImport",
    "FilMonte",
    "Fournisseur",
    "LigneCommande",
    "LigneImport",
    "LignePrix",
    "LigneReception",
    "LigneRecette",
    "Magasin",
    "Metier",
    "Mouvement",
    "OrdreFabrication",
    "Parametres",
    "PlanQualite",
    "Qualite",
    "Reception",
    "VersionPlan",
    "VersionRecette",
]
