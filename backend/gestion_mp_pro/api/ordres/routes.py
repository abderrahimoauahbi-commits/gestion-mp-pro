"""Routes du domaine « Ordres de fabrication » (API-PRO § 1.15 : routes 134–144).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service
(`services.ordres`). Lire : direction, achats, alimentation ; écrire : direction et
alimentation (les achats lisent, P44).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Depends, Query, Response

from gestion_mp_pro.api.communs import ValidationVersion, encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.ordres.schemas import (
    AnnulationOrdre,
    ApercuOrdres,
    ConsommationOrdre,
    DemandeProposition,
    LotSorti,
    OrdreCreation,
    OrdreFiche,
    OrdreModification,
    OrdreResume,
    PageOrdres,
    Proposition,
)
from gestion_mp_pro.exports import ordres as classeur
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.securite import C, D, L, QuiDep, droit
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services import ordres as service

routeur = nouveau_routeur("ordres")

Q = Annotated[str, Query(max_length=200, description="mots, sans accents")]


def _saisie(e: OrdreCreation) -> service.SaisieOrdre:
    """La saisie de l'écran, en nombres exacts, pour le service."""
    return service.SaisieOrdre(
        date=e.date,
        magasin_id=e.magasin_id,
        metier_id=e.metier_id,
        commentaire=e.commentaire,
        qualites=tuple(service.SaisieQualite(q.qualite_id, Decimal(str(q.m2))) for q in e.qualites),
        lignes=tuple(
            service.SaisieLigne(x.lot_id, Decimal(str(x.quantite)), x.unite, x.matiere_id)
            for x in e.lignes
        ),
    )


def _fiche(s: SessionDep, ident: int, message: str = "") -> OrdreFiche:
    """La fiche relue après un geste."""
    return OrdreFiche.model_validate({**asdict(service.fiche(s, ident)), "message": message})


def filtres(
    *,
    statut: StatutOrdre | None = None,
    q: Q = "",
    du: dt.date | None = None,
    au: dt.date | None = None,
    metier: int | None = None,
    magasin: int | None = None,
    qualite: int | None = None,
) -> service.FiltresOrdres:
    """Les filtres de la liste (135) et de son classeur (144)."""
    if du is not None and au is not None and du > au:
        raise Refus.saisie("« Du » est après « au » : inverser les dates.", code="date_invalide")
    return service.FiltresOrdres(statut, q, du, au, metier, magasin, qualite)


FiltresDep = Annotated[service.FiltresOrdres, Depends(filtres)]


def _curseur(pagination: PaginationDep) -> tuple[dt.date, int] | None:
    """La clé (date, n° d'entrée) du dernier ordre rendu (curseur de pagination)."""
    if not pagination.apres:
        return None
    try:
        jour, ident = pagination.apres
        return dt.date.fromisoformat(str(jour)), int(str(ident))
    except (ValueError, TypeError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc


@routeur.post(
    "/ordres/proposition",
    response_model=Proposition,
    dependencies=[droit(*C)],
    summary="Ce que les recettes demandent et les lots à prendre (FIFO à la date) ; n'écrit rien.",
    responses=reponses(401, 403, 404, 409, 422),
)
def proposer(e: DemandeProposition, s: SessionDep) -> Proposition:
    """Route 134 : lecture en POST (corps structuré)."""
    demande = service.Demande(
        magasin_id=e.magasin_id,
        qualites=tuple(service.SaisieQualite(q.qualite_id, Decimal(str(q.m2))) for q in e.qualites),
        date=e.date,
        metier_id=e.metier_id,
    )
    return Proposition.model_validate(asdict(service.proposer(s, demande)))


@routeur.get(
    "/ordres",
    response_model=PageOrdres,
    dependencies=[droit(*C)],
    summary="Les ordres filtrés, le plus récent d'abord, par pages : sorti net, écart, retours.",
    responses=reponses(401, 403, 422),
)
def lister(f: FiltresDep, pagination: PaginationDep, s: SessionDep) -> PageOrdres:
    """Route 135 (filtres et recherche poussés en SQL ; curseur date puis n° d'entrée)."""
    page = service.lister(s, f, _curseur(pagination), pagination.limite)
    suivant = encoder_curseur(list(page.dernier)) if page.dernier is not None else None
    return PageOrdres(
        elements=[OrdreResume.model_validate(asdict(x)) for x in page.elements],
        total=page.total,
        suivant=suivant,
    )


@routeur.get(
    "/ordres/apercu",
    response_model=ApercuOrdres,
    dependencies=[droit(*C)],
    summary="Comptes par onglet, agrégats des indicateurs et options des filtres de la liste.",
    responses=reponses(401, 403, 422),
)
def apercu(f: FiltresDep, s: SessionDep) -> ApercuOrdres:
    """Route 135bis : nourrit les onglets, les indicateurs et les filtres liés des Sorties."""
    return ApercuOrdres.model_validate(asdict(service.apercu(s, f)))


@routeur.get(
    "/ordres/ouverts",
    response_model=list[OrdreResume],
    dependencies=[droit(*C)],
    summary="La liste entière d'un statut (plafonnée) : l'atelier et la saisie la filtrent.",
    responses=reponses(401, 403, 422),
)
def ouverts(f: FiltresDep, s: SessionDep) -> list[OrdreResume]:
    """Route 135ter : accès borné « tous les ordres » (téléphone, retours) ; non paginé."""
    return [OrdreResume.model_validate(asdict(x)) for x in service.ouverts(s, f)]


@routeur.get(
    "/ordres/consommation",
    response_model=list[ConsommationOrdre],
    dependencies=[droit(*C)],
    summary="Ce que chaque ordre validé a consommé, face au prévu de sa recette.",
    responses=reponses(401, 403, 422),
)
def consommation(
    s: SessionDep,
    du: dt.date | None = None,
    au: dt.date | None = None,
    qualite: int | None = None,
) -> list[ConsommationOrdre]:
    """Route 143 (les ordres annulés n'ont rien consommé)."""
    lues = service.consommation_des_ordres(s, du, au, qualite)
    return [ConsommationOrdre.model_validate(asdict(x)) for x in lues]


@routeur.get(
    "/ordres/{ident}",
    response_model=OrdreFiche,
    dependencies=[droit(*C)],
    summary="Un ordre : qualités, lignes, prévu figé, sorti net, retours, blocages.",
    responses=reponses(401, 403, 404),
)
def lire(ident: int, s: SessionDep) -> OrdreFiche:
    """Route 136."""
    return _fiche(s, ident)


@routeur.post(
    "/ordres",
    response_model=OrdreFiche,
    status_code=201,
    dependencies=[droit(D, L)],
    summary="Crée un brouillon d'ordre (sans numéro, le stock ne bouge pas).",
    responses=reponses(401, 403, 404, 409, 422),
)
def creer(e: OrdreCreation, qui: QuiDep, s: SessionDep) -> OrdreFiche:
    """Route 137."""
    return _fiche(s, service.creer(s, qui, _saisie(e)).id)


@routeur.put(
    "/ordres/{ident}",
    response_model=OrdreFiche,
    dependencies=[droit(D, L)],
    summary="Modifie un brouillon d'ordre (qualités et lignes remplacées), à sa version.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(ident: int, e: OrdreModification, qui: QuiDep, s: SessionDep) -> OrdreFiche:
    """Route 138."""
    service.modifier(s, qui, ident, e.version, _saisie(e))
    return _fiche(s, ident)


@routeur.delete(
    "/ordres/{ident}",
    status_code=204,
    dependencies=[droit(D, L)],
    summary="Supprime un brouillon d'ordre (aucun numéro consommé).",
    responses=reponses(401, 403, 404, 409, 422),
)
def supprimer(ident: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 139."""
    service.supprimer(s, qui, ident, version)
    return Response(status_code=204)


@routeur.post(
    "/ordres/{ident}/valider",
    response_model=OrdreFiche,
    dependencies=[droit(D, L)],
    summary="Valide un ordre : numéro dans l'ordre des dates, prévu figé, le stock sort.",
    responses=reponses(401, 403, 404, 409, 422),
)
def valider(ident: int, e: ValidationVersion, qui: QuiDep, s: SessionDep) -> OrdreFiche:
    """Route 140."""
    o = service.valider(s, qui, ident, e.version)
    return _fiche(s, ident, f"Ordre {o.numero} validé : le stock est sorti.")


@routeur.post(
    "/ordres/{ident}/annuler",
    response_model=OrdreFiche,
    dependencies=[droit(D, L)],
    summary="Annule un ordre validé et ses retours ; ses retours en brouillon sont supprimés.",
    responses=reponses(401, 403, 404, 409, 422),
)
def annuler(ident: int, e: AnnulationOrdre, qui: QuiDep, s: SessionDep) -> OrdreFiche:
    """Route 141 : la réponse dit tout ce qui a été fait (`message`)."""
    _, phrase = service.annuler(s, qui, ident, e.version, e.motif)
    return _fiche(s, ident, phrase)


@routeur.get(
    "/ordres/{ident}/lots-sortis",
    response_model=list[LotSorti],
    dependencies=[droit(*C)],
    summary="Ce que l'ordre a emporté, lot par lot, net des retours : ce qui peut revenir.",
    responses=reponses(401, 403, 404),
)
def lots_sortis(ident: int, s: SessionDep) -> list[LotSorti]:
    """Route 142."""
    o = service.charger(s, ident)
    return [LotSorti.model_validate(asdict(x)) for x in service.lots_sortis(s, o)]


@routeur.get(
    "/export/ordres",
    response_class=Response,
    dependencies=[droit(*C)],
    summary="Le classeur des ordres (mêmes filtres que la liste) ou de leur consommation.",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter(
    f: FiltresDep,
    s: SessionDep,
    vue: Literal["ordres", "consommation"] = "ordres",
) -> Response:
    """Route 144 : `vue=consommation` = l'onglet « Ordres de fabrication » du stock (143)."""
    jour = horloge.aujourd_hui()
    if vue == "consommation":
        lues = service.consommation_des_ordres(s, f.du, f.au, f.qualite_id)
        return reponse(classeur.consommation(lues, f, jour), "consommation-ordres", jour)
    return reponse(classeur.ordres(service.toutes(s, f), f, jour), "ordres", jour)
