"""Routes du domaine « Importations » (API-PRO § 1.21 : routes 187–208).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Direction et achats
seulement (l'alimentation ne voit ni dossier, ni coût de revient). Chaque geste rend la fiche
relue. Ici : la liste, ce qui attend son dossier, la fiche, l'ouverture et l'en-tête (187–191) ;
les gestes sur la marchandise, les frais et la vie du dossier dans `routes_gestes.py`
(192–204) ; les classeurs et le coût de revient dans `routes_analyse.py` (205–208).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import Query

from gestion_mp_pro.api.communs import encoder_curseur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.importations import routes_analyse, routes_gestes  # noqa: F401
from gestion_mp_pro.api.importations.routeur import GESTE, FiltresDossiersDep, fiche_relue, routeur
from gestion_mp_pro.api.importations.schemas import DossierCreation, DossierModification
from gestion_mp_pro.api.importations.schemas_fiche import (
    ApercuDossiers,
    DossierFiche,
    DossierResume,
    EnAttente,
    PageDossiers,
)
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services.importations import attente, etats, lecture, ouverture

__all__ = ["routeur"]


def _curseur(pagination: PaginationDep) -> tuple[date | None, int] | None:
    """La clé (date d'arrivée, id) du dernier dossier rendu (curseur de pagination)."""
    if not pagination.apres:
        return None
    try:
        jour, ident = pagination.apres
        return (date.fromisoformat(str(jour)) if jour is not None else None), int(str(ident))
    except (ValueError, TypeError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc


@routeur.get(
    "/dossiers",
    response_model=PageDossiers,
    dependencies=[droit(D, A)],
    summary="Les dossiers d'importation, le plus récemment arrivé d'abord, par pages.",
    responses=reponses(401, 403, 422),
)
def lister_dossiers(
    f: FiltresDossiersDep, pagination: PaginationDep, s: SessionDep
) -> PageDossiers:
    """Route 187 (filtres et recherche poussés en SQL ; curseur date d'arrivée puis id)."""
    page = lecture.lister(s, f, _curseur(pagination), pagination.limite)
    suivant = encoder_curseur(list(page.dernier)) if page.dernier is not None else None
    return PageDossiers(
        elements=[DossierResume.model_validate(asdict(r)) for r in page.elements],
        total=page.total,
        suivant=suivant,
    )


@routeur.get(
    "/dossiers/apercu",
    response_model=ApercuDossiers,
    dependencies=[droit(D, A)],
    summary="Comptes par statut, totaux (indicateurs, pied), frais non répartis et fournisseurs.",
    responses=reponses(401, 403, 422),
)
def apercu_dossiers(f: FiltresDossiersDep, s: SessionDep) -> ApercuDossiers:
    """Route 250 : nourrit les indicateurs, les onglets, le pied et la vue « non répartis »."""
    return ApercuDossiers.model_validate(asdict(lecture.apercu(s, f)))


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
