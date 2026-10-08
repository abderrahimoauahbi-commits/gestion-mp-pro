"""Schémas Pydantic du domaine « Système ».

Lot S2 (et D10 pour la santé). Entrées `<Objet>Creation`, `<Objet>Modification`, `<Geste>`
dérivées de `communs.Entree` ; sorties `<Objet>Fiche`, `<Objet>Resume`, `<Objet>Liste`,
`Page[T]` (API-PRO § 0.1).
"""

from __future__ import annotations

import datetime as dt
from typing import ClassVar, Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Sortie
from gestion_mp_pro.api.comptes.schemas import Moi


class Sante(Sortie):
    """Route 1 `GET /sante` (public, sans donnée métier) : ce que la surveillance lit.

    Première forme posée par S0 (`etat`, `version`, `base_ms`) ; S1 remplit `schema` et
    `schema_attendu`, D10 la sauvegarde, les tâches et les courriels (API-PRO § 1.1).
    """

    etat: Literal["ok", "degrade"]
    version: str = Field(description="version servie : contenu de VERSION (copie figée)")
    schema_: str | None = Field(default=None, alias="schema", description="révision Alembic")
    schema_attendu: str | None = None
    base_ms: float | None = Field(default=None, description="temps de réponse de la base")
    sauvegarde_age_h: float | None = None
    sauvegarde_alerte: str = ""
    taches: dict[str, str] = Field(default_factory=dict)
    courriels_en_attente: int = 0


class EtatInstallation(Sortie):
    """Route 2 `GET /etat` (public) : ce que l'écran de connexion a besoin de savoir (K23)."""

    installe: bool
    societe: str
    version: str


class InventaireOuvert(Sortie):
    """Un inventaire ouvert : il suspend son magasin (tous si `null`) pour ses matières."""

    id: int
    numero: str
    date: dt.date
    magasin: str | None
    matieres: list[int]


class DomainePermis(Sortie):
    """Un domaine de l'API où le rôle lit ou écrit (dérivé de la matrice des droits)."""

    domaine: str
    lecture: bool
    ecriture: bool


class Contexte(Sortie):
    """Route 3 `GET /contexte` : le démarrage de l'écran en un appel."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"droits"})

    moi: Moi
    menu: list[DomainePermis]
    heure_serveur: dt.datetime
    societe: str
    date_cloture: dt.date | None
    inventaires_ouverts: list[InventaireOuvert]
    roles_au_metre: list[str]
    base_essai: bool
    compteurs: dict[str, int]
    alerte_serveur: str | None = Field(default=None, description="direction et administrateur")


class AdresseAcces(Sortie):
    """Une adresse par laquelle un téléphone joint le serveur."""

    libelle: str
    adresse: str


class Acces(Sortie):
    """Route 5 `GET /acces` : adresses du serveur, celle du QR, alerte si elle est locale."""

    adresses: list[AdresseAcces]
    adresse_publique: str
    adresse_qr: str
    alerte_localhost: str | None
