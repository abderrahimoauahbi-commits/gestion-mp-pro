"""Schémas Pydantic du domaine « Notifications et recherche » (API-PRO § 1.6, routes 53–56)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from gestion_mp_pro.api.communs import Page, Sortie


class Notification(Sortie):
    """Une notification de la cloche ; `lien` ouvre le document (adresse stable)."""

    id: int
    texte: str
    lien: str
    ton: str
    quand: datetime
    lue: bool
    objet: str
    objet_id: int | None


class PageNotifications(Page[Notification]):
    """Route 53 : une page de la cloche et le nombre de non lues (pastille)."""

    non_lues: int = Field(ge=0)


class ResultatRecherche(Sortie):
    """Route 56 : un résultat de la recherche globale (jamais de prix)."""

    genre: str
    id: int
    titre: str
    sous_titre: str
    lien: str
