"""Routes du domaine « Production et besoins » (API-PRO § 1.16 : routes 145–148 ; § 1.24 : 237).

Le plan de production s'écrit par la direction ; le réalisé lit les ordres validés (lot D6) ;
les besoins détaillés sont ceux du plan d'achat, à la date (sans conseil d'achat pour
l'alimentation).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Query, Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import DateReferenceDep, SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.production.schemas import (
    BesoinsDetailles,
    PlanEtRealise,
    PlanGlobalEntree,
    PlanProduction,
)
from gestion_mp_pro.exports import production as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import C, D, QuiDep, droit
from gestion_mp_pro.services import horloge, production, production_lecture

routeur = nouveau_routeur("production")


@routeur.get(
    "/production/plan",
    response_model=PlanProduction,
    dependencies=[droit(*C)],
    summary="Le plan de toutes les qualités : saisie, plan glissant, kg/m², tissé du mois.",
    responses=reponses(401, 403, 422),
)
def plan(jour: DateReferenceDep, s: SessionDep) -> PlanProduction:
    """Route 145."""
    return PlanProduction.model_validate(production_lecture.plan(s, jour))


@routeur.put(
    "/production/plan",
    response_model=PlanProduction,
    dependencies=[droit(D)],
    summary="Enregistrer le plan de plusieurs qualités d'un bloc (tout ou rien).",
    responses=reponses(401, 403, 404, 409, 422),
)
def ecrire_plan(corps: PlanGlobalEntree, qui: QuiDep, s: SessionDep) -> PlanProduction:
    """Route 146 : une version du plan par qualité dont le plan change."""
    lignes = [
        production.LignePlan(x.qualite_id, x.base_mensuelle, tuple(x.coefficients), x.version)
        for x in corps.qualites
    ]
    modifiees = production.ecrire_plan_global(s, qui, lignes, corps.motif)
    vue = production_lecture.plan(s, horloge.aujourd_hui())
    return PlanProduction.model_validate({**vue, "modifiees": modifiees})


@routeur.get(
    "/production/realise",
    response_model=PlanEtRealise,
    dependencies=[droit(*C)],
    summary="Le plan face au réalisé, chaque mois clos jugé sur le plan de son époque.",
    responses=reponses(401, 403, 422),
)
def realise(jour: DateReferenceDep, s: SessionDep) -> PlanEtRealise:
    """Route 147."""
    return PlanEtRealise.model_validate(production_lecture.realise(s, jour))


@routeur.get(
    "/production/besoins",
    response_model=BesoinsDetailles,
    dependencies=[droit(*C)],
    summary="Les besoins par matière et par mois, et ce que le plan d'achat en retient.",
    responses=reponses(401, 403, 422),
)
def besoins(
    jour: DateReferenceDep,
    qui: QuiDep,
    s: SessionDep,
    matiere: Annotated[int | None, Query(ge=1)] = None,
) -> BesoinsDetailles:
    """Route 148 : à la date (stock, commandes, sorties de ce jour-là)."""
    vue = production_lecture.besoins(s, jour, conseil=qui.voit_prix, matiere_id=matiere)
    return BesoinsDetailles.model_validate(vue)


@routeur.get(
    "/export/production",
    dependencies=[droit(*C)],
    summary="Un onglet de la production en classeur (plan glissant, réalisé, besoins).",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
    response_class=Response,
)
def exporter(
    jour: DateReferenceDep,
    qui: QuiDep,
    s: SessionDep,
    onglet: Literal["glissant", "realise", "besoins"] = "glissant",
) -> Response:
    """Route 237."""
    if onglet == "realise":
        contenu = classeurs.realise(production_lecture.realise(s, jour))
    elif onglet == "besoins":
        vue = production_lecture.besoins(s, jour, conseil=qui.voit_prix)
        contenu = classeurs.besoins(vue, qui.voit_prix)
    else:
        contenu = classeurs.glissant(production_lecture.plan(s, jour))
    return reponse(contenu, f"production-{onglet}", jour)
