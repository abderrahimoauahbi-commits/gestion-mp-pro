"""Routes du domaine « Réclamations » (API-PRO § 1.20 : routes 181–186).

Routes minces ; direction et achats. Chaque geste rend la fiche relue.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import Query

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.reclamations.schemas import (
    Cloture,
    ReclamationCreation,
    ReclamationFiche,
    ReclamationModification,
    ReclamationResume,
    Reouverture,
)
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services import reclamations
from gestion_mp_pro.services.reclamations_lecture import FiltresReclamations, fiche, liste

routeur = nouveau_routeur("reclamations")

__all__ = ["routeur"]

GESTE = reponses(401, 403, 404, 409, 422)


def _fiche(s: SessionDep, rid: int) -> ReclamationFiche:
    """La fiche relue après un geste."""
    return ReclamationFiche.model_validate(asdict(fiche(s, rid)))


@routeur.get(
    "/reclamations",
    response_model=list[ReclamationResume],
    dependencies=[droit(D, A)],
    summary="Les réclamations aux fournisseurs, la plus récente d'abord, filtrées au serveur.",
    responses=reponses(401, 403, 422),
)
def lister(
    s: SessionDep,
    statut: Annotated[str, Query(pattern="^(ouverte|close)?$")] = "",
    fournisseur: Annotated[int | None, Query(ge=1)] = None,
    reception: Annotated[int | None, Query(ge=1)] = None,
    q: Annotated[str, Query(max_length=200)] = "",
) -> list[ReclamationResume]:
    """Route 181."""
    f = FiltresReclamations(statut, fournisseur, reception, q)
    return [ReclamationResume.model_validate(asdict(x)) for x in liste(s, f)]


@routeur.get(
    "/reclamations/{rid}",
    response_model=ReclamationFiche,
    dependencies=[droit(D, A)],
    summary="La fiche d'une réclamation : ce qui est en cause, demandé, obtenu, sa durée.",
    responses=reponses(401, 403, 404),
)
def lire(rid: int, s: SessionDep) -> ReclamationFiche:
    """Route 182."""
    return _fiche(s, rid)


@routeur.post(
    "/reclamations",
    response_model=ReclamationFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ouvrir une réclamation sur ce que le fournisseur a livré (numéro tout de suite).",
    responses=reponses(401, 403, 409, 422),
)
def ouvrir(corps: ReclamationCreation, qui: QuiDep, s: SessionDep) -> ReclamationFiche:
    """Route 183."""
    r = reclamations.ouvrir(s, qui, reclamations.Ouverture(**corps.model_dump()))
    return _fiche(s, r.id)


@routeur.put(
    "/reclamations/{rid}",
    response_model=ReclamationFiche,
    dependencies=[droit(D, A)],
    summary="Noter la réponse du fournisseur et l'avoir obtenu (une close reste close).",
    responses=GESTE,
)
def completer(
    rid: int, corps: ReclamationModification, qui: QuiDep, s: SessionDep
) -> ReclamationFiche:
    """Route 184."""
    valeurs = corps.model_dump(include=corps.model_fields_set - {"version"})
    reclamations.completer(s, qui, rid, corps.version, valeurs)
    return _fiche(s, rid)


@routeur.post(
    "/reclamations/{rid}/clore",
    response_model=ReclamationFiche,
    dependencies=[droit(D, A)],
    summary="Clore la réclamation avec son issue (avoir, remplacement, remise, refusée…).",
    responses=GESTE,
)
def clore(rid: int, corps: Cloture, qui: QuiDep, s: SessionDep) -> ReclamationFiche:
    """Route 185."""
    reclamations.clore(
        s,
        qui,
        rid,
        version=corps.version,
        issue=corps.issue,
        montant_obtenu=corps.montant_obtenu,
        close_le=corps.close_le,
        reponse=corps.reponse,
    )
    return _fiche(s, rid)


@routeur.post(
    "/reclamations/{rid}/rouvrir",
    response_model=ReclamationFiche,
    dependencies=[droit(D, A)],
    summary="Rouvrir une réclamation close (motif au journal) : on attend le fournisseur.",
    responses=GESTE,
)
def rouvrir(rid: int, corps: Reouverture, qui: QuiDep, s: SessionDep) -> ReclamationFiche:
    """Route 186."""
    reclamations.rouvrir(s, qui, rid, corps.version, corps.motif)
    return _fiche(s, rid)
