"""Le routeur du domaine « Commandes » et les filtres de sa liste, partagés par `routes.py`
(liste, route 152) et `routes_documents.py` (classeur de la liste, route 166) : mêmes filtres
que l'écran."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.services.commandes_fiche import FiltresCommandes

routeur = nouveau_routeur("commandes")


def filtres_commandes(
    statut: Annotated[str, Query(max_length=20, description="statut, ou « clos »")] = "",
    filtre: Annotated[str, Query(pattern="^(retard)?$", description="« retard »")] = "",
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
    devise: Annotated[str, Query(max_length=3, description="code de la devise du bon")] = "",
    q: Annotated[str, Query(max_length=200, description="mots, sans accents")] = "",
) -> FiltresCommandes:
    """`?statut=&filtre=retard&fournisseur=&devise=&q=` de la liste des bons et de son classeur."""
    return FiltresCommandes(statut, filtre == "retard", fournisseur, devise, q)


FiltresDep = Annotated[FiltresCommandes, Depends(filtres_commandes)]
