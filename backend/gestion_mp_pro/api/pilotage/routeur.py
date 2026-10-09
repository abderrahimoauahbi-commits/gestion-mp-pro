"""Le routeur du domaine « Pilotage et analyse » et ses dépendances de requête.

Partagé par `routes.py` (lectures 7, 209–215, 235) et `routes_exports.py` (classeurs 216–220) :
mêmes filtres pour la liste et son classeur (D9 : « filtres = écran »).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import PREMIER_JOUR, borner_date
from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.services import pilotage_prix

routeur = nouveau_routeur("pilotage")

Q = Annotated[str, Query(max_length=200, description="mots, sans accents")]
Jour = Annotated[date | None, Query(description="AAAA-MM-JJ")]
DateFacultative = Annotated[date | None, Query(alias="date", description="AAAA-MM-JJ")]


def _periode(du: date | None, au: date | None, futur: bool) -> tuple[date | None, date | None]:
    """Deux dates bornées (2000 au plus tôt ; aujourd'hui au plus tard sauf `futur`), la
    première au plus la seconde (422 sinon)."""
    du, au = (
        None if x is None else borner_date(x) if not futur else _depuis_2000(x) for x in (du, au)
    )
    if du is not None and au is not None and du > au:
        raise Refus.saisie(
            f"Période vide : du {du:%d/%m/%Y} au {au:%d/%m/%Y}.",
            code="date_invalide",
            champs={"au": "avant le début"},
        )
    return du, au


def _depuis_2000(jour: date) -> date:
    """Une date d'échéance : du 01/01/2000 à 2100 (le futur est permis)."""
    if not PREMIER_JOUR <= jour <= DERNIER_JOUR:
        raise Refus.saisie(
            f"Date hors période ({jour:%d/%m/%Y}) : vérifier l'année.",
            code="date_invalide",
            champs={"date": "hors période"},
        )
    return jour


def periode(du: Jour = None, au: Jour = None) -> tuple[date | None, date | None]:
    """`?du=&au=` des lectures passées : au plus tard aujourd'hui."""
    return _periode(du, au, futur=False)


def periode_a_venir(du: Jour = None, au: Jour = None) -> tuple[date | None, date | None]:
    """`?du=&au=` de l'échéancier : des échéances à venir se cherchent aussi."""
    return _periode(du, au, futur=True)


PeriodeDep = Annotated[tuple[date | None, date | None], Depends(periode)]
PeriodeAVenirDep = Annotated[tuple[date | None, date | None], Depends(periode_a_venir)]
DERNIER_JOUR = date(2100, 12, 31)


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
