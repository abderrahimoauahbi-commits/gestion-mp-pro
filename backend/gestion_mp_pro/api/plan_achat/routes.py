"""Routes du domaine « Plan d'achat » (API-PRO § 1.17 : routes 149–151 ; § 1.24 : 242).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Direction et achats
seulement (l'alimentation n'a ni plan d'achat ni montant).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import Query, Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import DateReferenceDep, SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.plan_achat.schemas import PlanAchat, PreparationCommande
from gestion_mp_pro.exports import achats as classeurs
from gestion_mp_pro.exports import pilotage_achats
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import plan_achat

routeur = nouveau_routeur("plan_achat")


@routeur.get(
    "/plan-achat",
    response_model=PlanAchat,
    dependencies=[droit(D, A)],
    summary="Le plan d'achat à une date : indicateurs, fournisseurs, références à commander.",
    responses=reponses(401, 403, 422),
)
def lire_plan(s: SessionDep, jour: DateReferenceDep) -> PlanAchat:
    """Route 149."""
    return PlanAchat.model_validate(asdict(plan_achat.plan(s, jour)))


@routeur.get(
    "/plan-achat/fournisseurs/{fournisseur_id}",
    response_model=PreparationCommande,
    dependencies=[droit(D, A)],
    summary="Préparer une commande : les quantités que le calcul suggère chez ce fournisseur.",
    responses=reponses(401, 403, 404, 422),
)
def preparer(fournisseur_id: int, s: SessionDep, jour: DateReferenceDep) -> PreparationCommande:
    """Route 150."""
    return PreparationCommande.model_validate(
        asdict(plan_achat.preparation(s, fournisseur_id, jour))
    )


@routeur.get(
    "/export/pilotage",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le classeur de pilotage : stock, plan d'achat, fournisseurs, besoins, contrôles.",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter_pilotage(s: SessionDep, jour: DateReferenceDep) -> Response:
    """Route 151."""
    return reponse(pilotage_achats.pilotage(plan_achat.pilotage(s, jour)), "pilotage-mp", jour)


@routeur.get(
    "/export/plan-achat",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="L'onglet affiché du plan d'achat (fournisseurs ou références), cherché, en classeur.",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter_plan(
    s: SessionDep,
    jour: DateReferenceDep,
    onglet: Annotated[str, Query(max_length=20)] = "fournisseurs",
    q: Annotated[str, Query(max_length=200, description="mots, sans accents")] = "",
) -> Response:
    """Route 242."""
    p = plan_achat.plan(s, jour)
    lignes = plan_achat.filtrer(p, onglet, q)
    return reponse(classeurs.plan_affiche(p, onglet, q, lignes), "plan-achat", jour)
