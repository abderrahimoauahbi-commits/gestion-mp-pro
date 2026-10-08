"""Dépendances communes des routes : session, acteur, date de référence, pagination, version.

Toutes les routes prennent la session par `SessionDep` (une transaction par requête, validée
avant l'envoi de la réponse) ; jamais `Depends(db.session)` directement, qui ouvrirait une
autre session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import import_module
from importlib.util import find_spec
from typing import Annotated, Protocol

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from gestion_mp_pro.api.communs import LIMITE_DEFAUT, LIMITE_MAX, decoder_curseur
from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import session
from gestion_mp_pro.services import horloge

PREMIER_JOUR = date(2000, 1, 1)
"""Avant, une date est une faute de frappe (héritage REGLES § 0.5, D1)."""

SessionDep = Annotated[Session, Depends(session, scope="function")]
"""La session de la requête : `commit` à la fin de la route, `rollback` sur toute exception."""


class ActeurProtocole(Protocol):
    """Ce qu'une route sait de la personne connectée (l'objet vient de `securite`, lot S2)."""

    id: int
    identifiant: str
    nom: str
    role: str


def acteur(requete: Request, s: SessionDep) -> ActeurProtocole:
    """La personne connectée : délègue à `securite.acteur_de_la_requete` (lot S2).

    Le lot S2 pose aussi `requete.state.acteur` pour la ligne du journal du serveur. Tant que
    `securite` n'existe pas, toute route qui demande un acteur répond 401.
    """
    if find_spec("gestion_mp_pro.securite") is None:
        raise Refus.non_connecte()
    trouve: ActeurProtocole = import_module("gestion_mp_pro.securite").acteur_de_la_requete(
        requete, s
    )
    return trouve


ActeurDep = Annotated[ActeurProtocole, Depends(acteur)]


def borner_date(jour: date) -> date:
    """Une date de référence : du 01/01/2000 à aujourd'hui (heure de l'usine), sinon 422."""
    if jour < PREMIER_JOUR:
        raise Refus.saisie(
            f"Date trop ancienne ({jour:%d/%m/%Y}) : vérifier l'année.",
            code="date_trop_ancienne",
            champs={"date": "date trop ancienne"},
        )
    if jour > horloge.aujourd_hui():
        raise Refus.saisie(
            f"Date dans le futur ({jour:%d/%m/%Y}) : les chiffres se calculent au plus tard "
            "à aujourd'hui.",
            code="date_future",
            champs={"date": "date dans le futur"},
        )
    return jour


def date_reference(
    jour: Annotated[date | None, Query(alias="date", description="AAAA-MM-JJ")] = None,
) -> date:
    """`?date=` des lectures calculées ; absente, c'est aujourd'hui (API-PRO § 0.1)."""
    return horloge.aujourd_hui() if jour is None else borner_date(jour)


DateReferenceDep = Annotated[date, Depends(date_reference)]


@dataclass(frozen=True)
class Pagination:
    """Le curseur relu (`apres`, vide pour la première page) et la taille de page."""

    apres: list[object] | None
    limite: int


def pagination(
    apres: Annotated[str | None, Query(description="curseur rendu dans `suivant`")] = None,
    limite: Annotated[int, Query(ge=1, le=LIMITE_MAX)] = LIMITE_DEFAUT,
) -> Pagination:
    """`?apres=&limite=` des listes paginées (`Page[T]`)."""
    return Pagination(apres=decoder_curseur(apres) if apres else None, limite=limite)


PaginationDep = Annotated[Pagination, Depends(pagination)]


def version_attendue(
    version: Annotated[int, Query(ge=1, description="version lue avec la fiche")],
) -> int:
    """`?version=` des suppressions (sans corps) : la version lue, 409 si elle est périmée."""
    return version


VersionDep = Annotated[int, Depends(version_attendue)]
