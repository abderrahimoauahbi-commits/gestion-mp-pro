"""Le routeur du domaine « Réceptions et factures » et les filtres de ses listes, partagés par
`routes.py`, `routes_pesees.py` et `routes_exports.py` : la liste et son classeur prennent la
**même dépendance de filtres** (filtres = écran)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.services.receptions_lecture import FiltresReceptions
from gestion_mp_pro.services.receptions_pesees import FiltresBobines, FiltresPesees

routeur = nouveau_routeur("receptions")

TEXTE = Query(max_length=200, description="mots, sans accents")


def filtres_receptions(
    statut: Annotated[str, Query(pattern="^(brouillon|validee|annulee)?$")] = "",
    q: Annotated[str, TEXTE] = "",
    du: date | None = None,
    au: date | None = None,
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
) -> FiltresReceptions:
    """`?statut=&q=&du=&au=&fournisseur=` (route 167 et son classeur 178)."""
    return FiltresReceptions(statut, q, du, au, fournisseur)


def filtres_pesees(
    q: Annotated[str, TEXTE] = "",
    ecarts: bool = False,
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
    qualite: Annotated[str, Query(pattern="^(conforme|reserve|refuse)?$")] = "",
    magasin: Annotated[int | None, Query(ge=1)] = None,
) -> FiltresPesees:
    """`?q=&ecarts=&fournisseur=&qualite=&magasin=` (route 176 et son classeur 179)."""
    return FiltresPesees(q, ecarts, fournisseur, qualite, magasin)


def filtres_bobines(
    q: Annotated[str, TEXTE] = "",
    ecarts: bool = False,
    matiere: Annotated[int | None, Query(ge=1)] = None,
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
) -> FiltresBobines:
    """`?q=&ecarts=&matiere=&fournisseur=` (route 177 et son classeur 180)."""
    return FiltresBobines(q, ecarts, matiere, fournisseur)


FiltresDep = Annotated[FiltresReceptions, Depends(filtres_receptions)]
FiltresPeseesDep = Annotated[FiltresPesees, Depends(filtres_pesees)]
FiltresBobinesDep = Annotated[FiltresBobines, Depends(filtres_bobines)]
