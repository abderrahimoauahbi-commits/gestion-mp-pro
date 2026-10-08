"""Schémas et outils partagés par tous les domaines de l'API (API-PRO § 0.1).

- `Entree` : base des schémas d'entrée (champs inconnus refusés) ; `Sortie` : base des sorties
  (lues depuis les objets SQLAlchemy).
- `Page[T]` = `{elements, total, suivant}` : listes longues paginées par curseur opaque
  (`?apres=`, `?limite=` ≤ 5 000, défaut 500).
- `nouveau_routeur("<module>")` : le routeur d'un domaine, avec son étiquette OpenAPI et la
  classe de route du filtre des prix (`securite.RouteSansPrix`, lot S2) dès qu'elle existe.
"""

from __future__ import annotations

import base64
import binascii
import json
from importlib import import_module
from importlib.util import find_spec
from typing import Any

from fastapi import APIRouter
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from gestion_mp_pro.api import ETIQUETTES
from gestion_mp_pro.api.erreurs import Refus

LIMITE_DEFAUT = 500
LIMITE_MAX = 5000
MODULE_SECURITE = "gestion_mp_pro.securite"


class Entree(BaseModel):
    """Base des schémas d'entrée : un champ inconnu est refusé (422 « champ inconnu »)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Sortie(BaseModel):
    """Base des schémas de sortie : lus depuis les attributs des objets."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    """Une page d'une liste longue ; `suivant` est le curseur de la page d'après (ou `None`)."""

    elements: list[T]
    total: int = Field(ge=0, description="nombre total d'éléments qui passent les filtres")
    suivant: str | None = Field(default=None, description="à passer en `?apres=`")


class Message(Sortie):
    """Une phrase de retour (« Réception REC-2026-0318 validée : 3 lots entrés. »)."""

    message: str


class Ok(Sortie):
    """Accusé d'un geste sans autre contenu."""

    ok: bool = True


class ValidationVersion(Entree):
    """Corps d'un geste de document : la version lue avec la fiche (409 si périmée)."""

    version: int = Field(ge=1)


class Personne(Sortie):
    """Un compte, tel qu'on le cite (auteur, destinataire)."""

    id: int
    nom: str
    role: str | None = None


class MatiereCourte(Sortie):
    """Une matière citée dans un document ou une liste."""

    id: int
    reference: str
    designation: str = ""


class LotCourt(Sortie):
    """Un lot cité dans un document ou une liste."""

    id: int
    numero: str
    matiere_id: int


def encoder_curseur(valeurs: list[Any]) -> str:
    """Curseur opaque (base64 d'un JSON) : la clé de tri du dernier élément rendu."""
    brut = json.dumps(valeurs, separators=(",", ":"), default=str).encode()
    return base64.urlsafe_b64encode(brut).decode().rstrip("=")


def decoder_curseur(curseur: str) -> list[Any]:
    """Relit un curseur ; illisible → 422 `curseur_invalide`."""
    try:
        brut = base64.urlsafe_b64decode(curseur + "=" * (-len(curseur) % 4))
        valeurs = json.loads(brut)
    except (binascii.Error, ValueError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc
    if not isinstance(valeurs, list):
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        )
    return valeurs


def _classe_de_route() -> type[APIRoute]:
    """`securite.RouteSansPrix` si le lot S2 l'a posée, sinon la route ordinaire."""
    if find_spec(MODULE_SECURITE) is None:
        return APIRoute
    classe = getattr(import_module(MODULE_SECURITE), "RouteSansPrix", APIRoute)
    if not (isinstance(classe, type) and issubclass(classe, APIRoute)):
        raise TypeError("securite.RouteSansPrix doit dériver de fastapi.routing.APIRoute")
    return classe


def nouveau_routeur(module: str) -> APIRouter:
    """Le routeur du domaine `module` (déclaré dans `api.DOMAINES`)."""
    if module not in ETIQUETTES:
        raise ValueError(f"Domaine non déclaré dans api/__init__.py : {module}")
    return APIRouter(tags=[ETIQUETTES[module]], route_class=_classe_de_route())
