"""Schémas Pydantic du domaine « Système ».

Lot S2 (et D10 pour la santé). Entrées `<Objet>Creation`, `<Objet>Modification`, `<Geste>`
dérivées de `communs.Entree` ; sorties `<Objet>Fiche`, `<Objet>Resume`, `<Objet>Liste`,
`Page[T]` (API-PRO § 0.1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Sortie


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
