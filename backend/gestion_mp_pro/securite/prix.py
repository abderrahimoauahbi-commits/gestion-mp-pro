"""Prix jamais montrés hors direction et achats : filtre générique `sans_prix` (API-PRO § 0.4).

Toute réponse JSON passe, pour un rôle hors `VOIT_PRIX` (alimentation, administrateur, anonyme),
par `sans_prix`, qui met à `null` **à toute profondeur** (dictionnaires imbriqués, listes) les
clés de `CLES_MONETAIRES` (motifs `fnmatch`, déclarés une fois). La classe de route
`RouteSansPrix` le pose sur **toutes** les routes (`api.communs.nouveau_routeur`).

Un champ dont le nom ressemble à un prix sans en être un (le `droits` de `/moi`) est exempté par
son schéma de sortie : `cles_non_monetaires: ClassVar[frozenset[str]]` ; l'exemption vaut pour
toute la réponse de la route.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from fnmatch import fnmatchcase
from functools import lru_cache
from typing import Any, get_args

from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

from gestion_mp_pro.modeles.enums import Role

VOIT_PRIX = frozenset({Role.direction, Role.achats})
"""Les rôles qui voient prix et montants."""

CLES_MONETAIRES: tuple[str, ...] = (
    "prix*",
    "montant*",
    "valeur*",
    "cout*",
    "cmup*",
    "budget*",
    "cours*",
    "taux_droits",
    "economie*",
    "revient*",
    "tva*",
    "droits*",
    "frais*",
    "devise_prix",
    "*_mad",
)
"""Les clés monétaires (motifs) : liste unique, rejouée par l'essai de balayage des routes GET."""


@lru_cache(maxsize=8192)
def est_monetaire(cle: str) -> bool:
    """La clé porte-t-elle un prix, un montant, une valeur, un coût, un cours ?"""
    cle = cle.lower()
    return any(fnmatchcase(cle, motif) for motif in CLES_MONETAIRES)


def sans_prix(donnees: object, exemptees: frozenset[str] = frozenset()) -> object:
    """Copie des données où chaque clé monétaire vaut `null`, à toute profondeur."""
    if isinstance(donnees, dict):
        return {
            cle: None
            if est_monetaire(str(cle)) and cle not in exemptees
            else sans_prix(valeur, exemptees)
            for cle, valeur in donnees.items()
        }
    if isinstance(donnees, list | tuple):
        return [sans_prix(x, exemptees) for x in donnees]
    return donnees


def cles_exemptees(annotation: object, vus: set[int] | None = None) -> frozenset[str]:
    """Les `cles_non_monetaires` déclarées par un schéma de sortie et ses sous-schémas."""
    vus = set() if vus is None else vus
    if id(annotation) in vus:
        return frozenset()
    vus.add(id(annotation))
    cles: set[str] = set()
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        cles |= set(getattr(annotation, "cles_non_monetaires", frozenset()))
        for champ in annotation.model_fields.values():
            cles |= cles_exemptees(champ.annotation, vus)
    for argument in get_args(annotation):
        cles |= cles_exemptees(argument, vus)
    return frozenset(cles)


def voit_prix(requete: Request) -> bool:
    """La personne de la requête voit-elle les prix (rôle posé par `acteur_de_la_requete`) ?"""
    acteur = getattr(requete.state, "acteur", None)
    return getattr(acteur, "role", None) in VOIT_PRIX


def filtrer_reponse(requete: Request, reponse: Response, exemptees: frozenset[str]) -> Response:
    """Retire les prix d'une réponse JSON destinée à un rôle qui ne les voit pas."""
    if voit_prix(requete) or not reponse.headers.get("content-type", "").startswith(
        "application/json"
    ):
        return reponse
    corps = bytes(reponse.body or b"")
    if not corps:
        return reponse
    donnees = json.loads(corps)
    filtrees = sans_prix(donnees, exemptees)
    if filtrees == donnees:
        return reponse
    nouveau = json.dumps(filtrees, ensure_ascii=False, separators=(",", ":")).encode()
    reponse.body = nouveau
    reponse.headers["content-length"] = str(len(nouveau))
    return reponse


Traitant = Callable[[Request], Coroutine[Any, Any, Response]]


class RouteSansPrix(APIRoute):
    """La classe de toutes les routes : leur réponse JSON passe par `sans_prix`."""

    def get_route_handler(self) -> Traitant:
        """Le traitant de FastAPI, suivi du filtre des prix."""
        original = super().get_route_handler()
        exemptees = cles_exemptees(self.response_model)

        async def traitant(requete: Request) -> Response:
            """Appelle la route, puis filtre sa réponse selon le rôle."""
            return filtrer_reponse(requete, await original(requete), exemptees)

        return traitant
