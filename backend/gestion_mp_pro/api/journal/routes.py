"""Routes du domaine « Journal et historique » (API-PRO § 1.5, routes 49–51).

La route 52 (`GET /export/journal`, classeur) appartient au lot D9 (`exports/journal.py`) : elle
se branche ici avec les mêmes filtres (`FiltreJournal`).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from gestion_mp_pro.api.communs import encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.journal.schemas import (
    LigneHistorique,
    LigneJournal,
    PageJournal,
    PersonneJournal,
    ValeursJournal,
)
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.securite import TOUS, D, QuiDep, T, droit
from gestion_mp_pro.services import journal

routeur = nouveau_routeur("journal")

MOTS_MAX = 200


def filtres(
    *,
    q: Annotated[str, Query(max_length=MOTS_MAX, description="mots, sans accents")] = "",
    utilisateur: Annotated[int | None, Query(ge=1, description="id du compte")] = None,
    action: Annotated[str, Query(max_length=80)] = "",
    objet: Annotated[ObjetJournal | None, Query()] = None,
    objet_id: Annotated[int | None, Query(ge=1)] = None,
    du: date | None = None,
    au: date | None = None,
) -> journal.FiltreJournal:
    """Les filtres du journal, partagés avec son export (route 52)."""
    return journal.FiltreJournal(
        q=q,
        utilisateur=utilisateur,
        action=action,
        objet=objet.value if objet else "",
        objet_id=objet_id,
        du=du,
        au=au,
    )


FiltresDep = Annotated[journal.FiltreJournal, Depends(filtres)]


def _apres(pagination: PaginationDep) -> int | None:
    """Le curseur du journal : l'id de la dernière ligne rendue."""
    if not pagination.apres:
        return None
    valeur = pagination.apres[0]
    if not isinstance(valeur, int):
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        )
    return valeur


@routeur.get(
    "/journal",
    response_model=PageJournal,
    dependencies=[droit(D, T)],
    summary="Le journal des actions, filtré, les plus récentes d'abord.",
    responses=reponses(401, 403, 422),
)
def lire(f: FiltresDep, pagination: PaginationDep, s: SessionDep) -> PageJournal:
    """Route 49 : qui a fait quoi, sur quoi, et quand (avant/après)."""
    page = journal.lire_journal(s, f, _apres(pagination), pagination.limite)
    suivant = encoder_curseur([page.dernier_id]) if page.dernier_id is not None else None
    return PageJournal(
        elements=[LigneJournal.de(j) for j in page.lignes], total=page.total, suivant=suivant
    )


@routeur.get(
    "/journal/valeurs",
    response_model=ValeursJournal,
    dependencies=[droit(D, T)],
    summary="Les personnes, actions et objets que proposent les filtres du journal.",
    responses=reponses(401, 403),
)
def valeurs(s: SessionDep) -> ValeursJournal:
    """Route 50."""
    v = journal.valeurs_journal(s)
    return ValeursJournal(
        utilisateurs=[PersonneJournal(id=i, nom=n) for i, n in v.utilisateurs],
        actions=v.actions,
        objets=v.objets,
    )


@routeur.get(
    "/historique/{objet}/{ident}",
    response_model=list[LigneHistorique],
    dependencies=[droit(*TOUS)],
    summary="L'historique d'une fiche (avant/après), pour qui peut lire la fiche.",
    responses=reponses(401, 403, 422),
)
def historique(
    objet: ObjetJournal, ident: int, qui: QuiDep, s: SessionDep
) -> list[LigneHistorique]:
    """Route 51 : prix retirés pour les rôles qui ne les voient pas (filtre de la route)."""
    return [LigneHistorique.de(j) for j in journal.historique_lisible(s, qui.role, objet, ident)]
