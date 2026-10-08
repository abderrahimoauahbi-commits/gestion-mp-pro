"""Schémas Pydantic du domaine « Journal et historique » (API-PRO § 1.5, routes 49–51).

Les différences `avant` / `apres` ont le **nom du champ en clé** : le filtre des prix les retire
pour les rôles qui ne voient pas les prix (l'administrateur compris).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from gestion_mp_pro.api.communs import Page, Sortie
from gestion_mp_pro.modeles import Journal


class LigneJournal(Sortie):
    """Une ligne du journal des actions."""

    id: int
    quand: datetime
    utilisateur: str
    utilisateur_id: int | None
    role: str
    action: str
    objet: str
    objet_id: int | None
    numero: str
    detail: str
    avant: dict[str, Any] | None
    apres: dict[str, Any] | None

    @classmethod
    def de(cls, j: Journal) -> LigneJournal:
        """La ligne lisible d'une entrée du journal."""
        return cls(
            id=j.id,
            quand=j.quand,
            utilisateur=j.utilisateur_nom,
            utilisateur_id=j.utilisateur_id,
            role=j.role,
            action=j.action,
            objet=str(j.objet),
            objet_id=j.objet_id,
            numero=j.numero,
            detail=j.detail,
            avant=j.avant,
            apres=j.apres,
        )


class PageJournal(Page[LigneJournal]):
    """Route 49 : une page du journal, les plus récentes d'abord."""


class PersonneJournal(Sortie):
    """Une personne citée par le journal (par son compte)."""

    id: int
    nom: str


class ValeursJournal(Sortie):
    """Route 50 : ce que les filtres du journal proposent."""

    utilisateurs: list[PersonneJournal]
    actions: list[str]
    objets: list[str]


class LigneHistorique(Sortie):
    """Route 51 : un geste sur une fiche, avec les champs changés."""

    id: int
    quand: datetime
    utilisateur: str
    role: str
    action: str
    numero: str
    detail: str
    avant: dict[str, Any] | None
    apres: dict[str, Any] | None

    @classmethod
    def de(cls, j: Journal) -> LigneHistorique:
        """La ligne d'historique d'une entrée du journal."""
        return cls(
            id=j.id,
            quand=j.quand,
            utilisateur=j.utilisateur_nom,
            role=j.role,
            action=j.action,
            numero=j.numero,
            detail=j.detail,
            avant=j.avant,
            apres=j.apres,
        )
