"""Routes du domaine « Notifications et recherche » (API-PRO § 1.6, routes 53–56).

La cloche est à chacun (administrateur compris) ; la recherche globale aux trois rôles métier,
chaque genre filtré par le rôle qui peut ouvrir sa fiche.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query, Response

from gestion_mp_pro.api.communs import encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.notifications.schemas import (
    Notification,
    PageNotifications,
    ResultatRecherche,
)
from gestion_mp_pro.securite import TOUS, C, QuiDep, droit
from gestion_mp_pro.services import notifications, recherche

routeur = nouveau_routeur("notifications")

SANS_CORPS = {"status_code": 204, "response_class": Response}
CHERCHE_MIN, CHERCHE_MAX = 2, 200


def _lecteur(qui: QuiDep) -> notifications.Lecteur:
    """La personne qui lit sa cloche."""
    return notifications.Lecteur(qui.id, qui.role)


def _apres(pagination: PaginationDep) -> int | None:
    """Le curseur de la cloche : l'id de la dernière notification rendue."""
    if not pagination.apres:
        return None
    valeur = pagination.apres[0]
    if not isinstance(valeur, int):
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        )
    return valeur


@routeur.get(
    "/notifications",
    response_model=PageNotifications,
    dependencies=[droit(*TOUS)],
    summary="Sa cloche : les notifications de son rôle et à son nom, les plus récentes d'abord.",
    responses=reponses(401, 422),
)
def lister(
    qui: QuiDep, pagination: PaginationDep, s: SessionDep, non_lues: bool = False
) -> PageNotifications:
    """Route 53 : `non_lues` compte les non lues, quel que soit le filtre."""
    cloche = notifications.lister(
        s, _lecteur(qui), non_lues=non_lues, apres=_apres(pagination), limite=pagination.limite
    )
    suivant = encoder_curseur([cloche.dernier_id]) if cloche.dernier_id is not None else None
    return PageNotifications(
        elements=[Notification(**vars(n)) for n in cloche.elements],
        total=cloche.total,
        suivant=suivant,
        non_lues=cloche.non_lues,
    )


@routeur.post(
    "/notifications/{ident}/lue",
    dependencies=[droit(*TOUS)],
    summary="Marquer une notification comme lue.",
    responses=reponses(401, 404),
    **SANS_CORPS,
)
def marquer_lue(ident: int, qui: QuiDep, s: SessionDep) -> Response:
    """Route 54."""
    notifications.marquer_lue(s, _lecteur(qui), ident)
    return Response(status_code=204)


@routeur.post(
    "/notifications/lues",
    dependencies=[droit(*TOUS)],
    summary="Tout marquer comme lu.",
    responses=reponses(401),
    **SANS_CORPS,
)
def tout_marquer_lu(qui: QuiDep, s: SessionDep) -> Response:
    """Route 55."""
    notifications.tout_marquer_lu(s, _lecteur(qui))
    return Response(status_code=204)


@routeur.get(
    "/recherche",
    response_model=list[ResultatRecherche],
    dependencies=[droit(*C)],
    summary="La recherche globale de l'en-tête (tous les mots, sans accents), filtrée par rôle.",
    responses=reponses(401, 403, 422),
)
def rechercher(
    qui: QuiDep,
    s: SessionDep,
    q: Annotated[str, Query(min_length=CHERCHE_MIN, max_length=CHERCHE_MAX)],
) -> list[ResultatRecherche]:
    """Route 56 : matières, lots, ordres, qualités ; et pour D, A commandes, réceptions,
    dossiers, fournisseurs."""
    return [ResultatRecherche(**vars(r)) for r in recherche.rechercher(s, qui.role, q)]
