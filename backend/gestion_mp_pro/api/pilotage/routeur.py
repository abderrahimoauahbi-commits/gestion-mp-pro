"""Le routeur du domaine « Pilotage et analyse » et ses dépendances de requête.

Partagé par `routes.py` (lectures 7, 209–215, 235) et `routes_exports.py` (classeurs 216–220) :
mêmes filtres pour la liste et son classeur (D9 : « filtres = écran »).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import borner_date
from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.services import pilotage_prix

routeur = nouveau_routeur("pilotage")

Q = Annotated[str, Query(max_length=200, description="mots, sans accents")]
Jour = Annotated[date | None, Query(description="AAAA-MM-JJ")]
DateFacultative = Annotated[date | None, Query(alias="date", description="AAAA-MM-JJ")]


def periode(du: Jour = None, au: Jour = None) -> tuple[date | None, date | None]:
    """`?du=&au=` : deux dates bornées, la première au plus la seconde (422 sinon)."""
    du, au = (borner_date(x) if x is not None else None for x in (du, au))
    if du is not None and au is not None and du > au:
        raise Refus.saisie(
            f"Période vide : du {du:%d/%m/%Y} au {au:%d/%m/%Y}.",
            code="date_invalide",
            champs={"au": "avant le début"},
        )
    return du, au


PeriodeDep = Annotated[tuple[date | None, date | None], Depends(periode)]


def criteres(
    meme_couleur: bool = True,
    autre_fournisseur: bool = True,
    prix_catalogue: bool = False,
    fenetre_jours: Annotated[
        int | None,
        Query(ge=pilotage_prix.FENETRE_MIN, le=pilotage_prix.FENETRE_MAX, description="jours"),
    ] = None,
) -> pilotage_prix.Criteres:
    """Les critères des opportunités (défauts : même couleur, autre fournisseur, T6)."""
    return pilotage_prix.Criteres(meme_couleur, autre_fournisseur, prix_catalogue, fenetre_jours)


CriteresDep = Annotated[pilotage_prix.Criteres, Depends(criteres)]
