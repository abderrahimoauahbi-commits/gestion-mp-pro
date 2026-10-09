"""Chaque schéma de l'OpenAPI a un nom court et unique (lot NOMS).

Deux classes exposées du même nom (`Annulation` des réceptions et des opérations…) sont
renommées par FastAPI `gestion_mp_pro__api__<domaine>__schemas__<Nom>` : les types de l'écran
(`frontend/src/lib/types.gen.ts`) en deviennent illisibles, et l'arrivée d'un homonyme renomme
un type déjà employé, ce qui casse l'écran qui le citait. Chaque classe exposée porte donc un nom
parlant, propre à son domaine (`AnnulationReception`, `AnnulationOperation`…).
"""

from __future__ import annotations

import dataclasses
from collections import defaultdict
from enum import Enum
from typing import Any, get_args, get_type_hints

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from pydantic import BaseModel

from gestion_mp_pro.securite.matrice import routes_api


def _nommee(t: Any) -> bool:
    """Une classe qui devient un schéma nommé : modèle Pydantic, énumération, dataclass."""
    return isinstance(t, type) and (issubclass(t, BaseModel | Enum) or dataclasses.is_dataclass(t))


def _parcourir(t: Any, vues: set[type]) -> None:
    """Ajoute à `vues` les classes nommées atteintes depuis l'annotation `t` (récursif)."""
    if _nommee(t):
        if t in vues:
            return
        vues.add(t)
        if issubclass(t, BaseModel):
            for champ in t.model_fields.values():
                _parcourir(champ.annotation, vues)
        elif dataclasses.is_dataclass(t):
            for annotation in get_type_hints(t).values():
                _parcourir(annotation, vues)
        return
    for argument in get_args(t):
        _parcourir(argument, vues)


def classes_exposees(application: FastAPI) -> set[type]:
    """Les classes nommées qu'une route reçoit (paramètres, corps, dépendances comprises) ou rend
    (réponse de succès et réponses déclarées)."""
    vues: set[type] = set()
    for _chemin, route in routes_api(application):
        _parcourir(route.response_model, vues)
        for reponse in route.responses.values():
            _parcourir(reponse.get("model"), vues)
        _parcourir_dependances(route.dependant, vues)
    return vues


def _parcourir_dependances(d: Dependant, vues: set[type]) -> None:
    """Les paramètres (chemin, requête, en-tête, corps) d'une route et de ses dépendances."""
    for parametre in d.path_params + d.query_params + d.header_params + d.body_params:
        _parcourir(parametre.field_info.annotation, vues)
    for sous in d.dependencies:
        _parcourir_dependances(sous, vues)


def test_aucun_schema_n_a_de_nom_long(application: FastAPI) -> None:
    """Un nom de schéma avec `__` est le nom de repli de FastAPI pour deux homonymes."""
    schemas = application.openapi().get("components", {}).get("schemas", {})
    longs = sorted(nom for nom in schemas if "__" in nom)
    assert not longs, f"Schémas homonymes renommés par FastAPI, à nommer à part : {longs}"


def test_deux_classes_exposees_n_ont_pas_le_meme_nom(application: FastAPI) -> None:
    """Deux classes exposées du même nom : la seconde renommerait la première dans l'écran."""
    par_nom: dict[str, list[str]] = defaultdict(list)
    for classe in classes_exposees(application):
        par_nom[classe.__name__].append(f"{classe.__module__}.{classe.__qualname__}")
    homonymes = {nom: sorted(c) for nom, c in par_nom.items() if len(c) > 1}
    assert not homonymes, f"Classes exposées homonymes : {homonymes}"


def test_le_parcours_voit_les_schemas_de_l_openapi(application: FastAPI) -> None:
    """Le parcours des routes retrouve bien les schémas nommés de l'OpenAPI (garde de l'essai)."""
    noms = {c.__name__ for c in classes_exposees(application)}
    schemas = set(application.openapi().get("components", {}).get("schemas", {}))
    assert {"AnnulationReception", "AnnulationOperation", "ReceptionFiche"} <= noms
    generes = ("Body_", "Page_", "HTTPValidationError", "ValidationError")  # noms posés par FastAPI
    oublies = sorted(s for s in schemas - noms if not s.startswith(generes))
    assert not oublies, f"Schémas de l'OpenAPI que le parcours des routes ne voit pas : {oublies}"
