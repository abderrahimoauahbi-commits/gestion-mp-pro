"""Comparer des `Donnees` à l'ordre et au type près (lot S4) : `propre` (S3) compare les
valeurs, pas l'ordre des clés ni le type des nombres — un total en dépend pourtant."""

from __future__ import annotations

import dataclasses
import types
import typing


def en_ordre(x: object) -> object:
    """La mise à plat de `propre`, l'ordre des clés compris (un total dépend de l'ordre)."""
    if isinstance(x, dict):
        return [[k, en_ordre(v)] for k, v in x.items()]
    if isinstance(x, list):
        return [en_ordre(v) for v in x]
    return x


def flottants(valeur: object, type_: object) -> object:  # noqa: PLR0911
    """Une valeur rendue au type du moteur : un entier écrit à la main là où le moteur attend
    un `float` (comme Gestion MP le lui donne) devient un `float` ; un total en dépend."""
    if isinstance(valeur, bool) or valeur is None:
        return valeur
    origine, args = typing.get_origin(type_), typing.get_args(type_)
    if origine in (typing.Union, types.UnionType):
        utiles = [a for a in args if a is not type(None)]
        return flottants(valeur, utiles[0]) if len(utiles) == 1 else valeur
    if type_ is float and isinstance(valeur, int):
        return float(valeur)
    if dataclasses.is_dataclass(valeur) and not isinstance(valeur, type):
        indices = typing.get_type_hints(type(valeur))
        for f in dataclasses.fields(valeur):
            setattr(valeur, f.name, flottants(getattr(valeur, f.name), indices[f.name]))
        return valeur
    if origine is dict and isinstance(valeur, dict):
        return {k: flottants(v, args[1]) for k, v in valeur.items()}
    if origine is list and isinstance(valeur, list):
        return [flottants(v, args[0]) for v in valeur]
    if origine is tuple and isinstance(valeur, tuple):
        return tuple(flottants(v, a) for v, a in zip(valeur, args, strict=True))
    return valeur


def types_de(x: object, chemin: str = "") -> dict[str, str]:
    """Le type de chaque valeur, par chemin (le moteur doit recevoir les mêmes types)."""
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {
            k: v
            for f in dataclasses.fields(x)
            for k, v in types_de(getattr(x, f.name), f"{chemin}.{f.name}").items()
        }
    if isinstance(x, dict):
        return {k: v for c, e in x.items() for k, v in types_de(e, f"{chemin}[{c!r}]").items()}
    if isinstance(x, list | tuple):
        return {k: v for i, e in enumerate(x) for k, v in types_de(e, f"{chemin}[{i}]").items()}
    return {chemin: type(x).__name__}
