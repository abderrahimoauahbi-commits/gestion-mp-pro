"""Routes du domaine « Importations » (API-PRO § 1.21 : routes 187–208).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Direction et achats
seulement (l'alimentation ne voit ni dossier, ni coût de revient). Chaque geste rend la fiche
relue. Ici : la liste, ce qui attend son dossier, la fiche, l'ouverture et l'en-tête (187–191) ;
les gestes sur la marchandise, les frais et la vie du dossier dans `routes_gestes.py`
(192–204) ; les classeurs et le coût de revient dans `routes_analyse.py` (205–208).
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Query

from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.importations import routes_analyse, routes_gestes  # noqa: F401
from gestion_mp_pro.api.importations.routeur import GESTE, FiltresDossiersDep, fiche_relue, routeur
from gestion_mp_pro.api.importations.schemas import DossierCreation, DossierModification
from gestion_mp_pro.api.importations.schemas_fiche import DossierFiche, DossierResume, EnAttente
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services.importations import attente, etats, ouverture
from gestion_mp_pro.services.importations.lecture import lister

__all__ = ["routeur"]


@routeur.get(
    "/dossiers",
    response_model=list[DossierResume],
    dependencies=[droit(D, A)],
    summary="Les dossiers d'importation, le plus récemment arrivé d'abord, avec leurs totaux.",
    responses=reponses(401, 403, 422),
)
def lister_dossiers(f: FiltresDossiersDep, s: SessionDep) -> list[DossierResume]:
    """Route 187."""
    return [DossierResume.model_validate(asdict(r)) for r in lister(s, f)]


@routeur.get(
    "/dossiers/a-rattacher",
    response_model=EnAttente,
    dependencies=[droit(D, A)],
    summary="Ce qui attend son dossier : factures reçues, réceptions sans facture.",
    responses=reponses(401, 403, 422),
)
def a_rattacher(
    s: SessionDep,
    locaux: bool = Query(False, description="montrer aussi les fournisseurs marocains"),
) -> EnAttente:
    """Route 188."""
    return EnAttente.model_validate(asdict(attente.en_attente(s, locaux=locaux)))


@routeur.get(
    "/dossiers/{did}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="La fiche d'un dossier : marchandises, frais, coût, contrôles, échéancier, gestes.",
    responses=reponses(401, 403, 404),
)
def lire(did: int, s: SessionDep) -> DossierFiche:
    """Route 189."""
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers",
    response_model=DossierFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ouvrir un dossier depuis une facture reçue, ou à la main s'il est d'avant.",
    responses=GESTE,
)
def creer(corps: DossierCreation, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 190."""
    d = ouverture.creer(s, qui, ouverture.Ouverture(**corps.model_dump()))
    return fiche_relue(s, d.id)


@routeur.put(
    "/dossiers/{did}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Modifier l'en-tête : libellé, banque, observations, date d'arrivée.",
    responses=GESTE,
)
def modifier(did: int, corps: DossierModification, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 191."""
    etats.modifier(s, qui, did, etats.EnTete(**corps.model_dump()))
    return fiche_relue(s, did)
