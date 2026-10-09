"""Routes du domaine « Opérations de stock » (API-PRO § 1.13 : routes 115–123 ; § 1.24 : 241).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. La garde est
`droit(*C)` ; le droit **par type** (et la quarantaine : libérer, direction et achats) est
tranché par `services.operations` (une table, `droits.DROITS`).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, Query, Response

from gestion_mp_pro.api.communs import ValidationVersion, encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.operations.schemas import (
    Annulation,
    Brouillons,
    OperationCreation,
    OperationFiche,
    OperationModification,
    PageOperations,
    ResultatValidationGroupee,
    SelectionBrouillons,
)
from gestion_mp_pro.exports import operations as classeur
from gestion_mp_pro.exports.stock import nom_de_fichier
from gestion_mp_pro.modeles.enums import StatutDocument, TypeOperation
from gestion_mp_pro.securite import C, QuiDep, droit
from gestion_mp_pro.services import brouillons, horloge
from gestion_mp_pro.services import operations as service
from gestion_mp_pro.services.operations import droits
from gestion_mp_pro.services.operations.lecture import FiltresOperations, OperationLue

routeur = nouveau_routeur("operations")

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
Q = Annotated[str, Query(max_length=200, description="mots, sans accents")]


def _fiche(lue: OperationLue) -> OperationFiche:
    return OperationFiche.model_validate(asdict(lue))


def _saisie(e: OperationCreation | OperationModification) -> service.SaisieOperation:
    """La saisie de l'écran, en kilos signés et nombres exacts, pour le service."""
    lignes = tuple(
        service.SaisieLigne(
            matiere_id=x.matiere_id,
            magasin_id=x.magasin_id,
            quantite=Decimal(str(x.quantite)),
            lot_id=x.lot_id,
            lot_numero=x.lot_numero,
            lot_interne=x.lot_interne,
            magasin_destination_id=x.magasin_destination_id,
            unite=x.unite,
            prix=Decimal(str(x.prix)),
            devise=x.devise,
        )  # fmt: skip
        for x in e.lignes
    )
    return service.SaisieOperation(
        type=e.type, date=e.date, lignes=lignes, ordre_id=e.ordre_id, motif_id=e.motif_id,
        commentaire=e.commentaire,
    )  # fmt: skip


def filtres(
    type: TypeOperation | None = None,  # noqa: A002 — nom du paramètre d'API-PRO
    statut: StatutDocument | None = None,
    q: Q = "",
) -> FiltresOperations:
    """Les filtres de la liste et de son classeur."""
    return FiltresOperations(type=type, statut=statut, q=q)


FiltresDep = Annotated[FiltresOperations, Depends(filtres)]


def _curseur(pagination: PaginationDep) -> tuple[date, int] | None:
    """(date, n°) de la dernière opération rendue."""
    if not pagination.apres:
        return None
    try:
        jour, ident = pagination.apres
        return date.fromisoformat(str(jour)), int(str(ident))
    except (ValueError, TypeError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc


@routeur.get(
    "/operations",
    response_model=PageOperations,
    dependencies=[droit(*C)],
    summary="Les opérations de stock, filtrées, les plus récentes d'abord, par pages.",
    responses=reponses(401, 403, 422),
)
def lister(f: FiltresDep, pagination: PaginationDep, qui: QuiDep, s: SessionDep) -> PageOperations:
    """Route 115 (prix masqués pour l'alimentation par le filtre)."""
    page = service.lister(s, f, _curseur(pagination), pagination.limite, qui.role)
    suivant = encoder_curseur([page.dernier[0], page.dernier[1]]) if page.dernier else None
    return PageOperations(
        elements=[_fiche(x) for x in page.elements], total=page.total, suivant=suivant
    )


@routeur.get(
    "/operations/{ident}",
    response_model=OperationFiche,
    dependencies=[droit(*C)],
    summary="Une opération : lignes, auteurs, blocages, ce que le lecteur peut en faire.",
    responses=reponses(401, 403, 404),
)
def lire(ident: int, qui: QuiDep, s: SessionDep) -> OperationFiche:
    """Route 116."""
    return _fiche(service.fiche(s, ident, qui.role))


@routeur.post(
    "/operations",
    response_model=OperationFiche,
    status_code=201,
    dependencies=[droit(*C)],
    summary="Crée un brouillon d'opération (et le valide aussitôt si `valider`).",
    responses=reponses(401, 403, 409, 422),
)
def creer(e: OperationCreation, qui: QuiDep, s: SessionDep) -> OperationFiche:
    """Route 117 : droit selon le type ; `valider: true` = une seule transaction."""
    o = service.creer(s, qui, _saisie(e), valider=e.valider)
    return _fiche(service.fiche(s, o.id, qui.role))


@routeur.put(
    "/operations/{ident}",
    response_model=OperationFiche,
    dependencies=[droit(*C)],
    summary="Modifie un brouillon d'opération (lignes remplacées), à sa version.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(ident: int, e: OperationModification, qui: QuiDep, s: SessionDep) -> OperationFiche:
    """Route 118."""
    service.modifier(s, qui, ident, e.version, _saisie(e))
    return _fiche(service.fiche(s, ident, qui.role))


@routeur.delete(
    "/operations/{ident}",
    status_code=204,
    dependencies=[droit(*C)],
    summary="Supprime un brouillon d'opération (aucun numéro consommé).",
    responses=reponses(401, 403, 404, 409, 422),
)
def supprimer(ident: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 119."""
    service.supprimer(s, qui, ident, version)
    return Response(status_code=204)


@routeur.post(
    "/operations/{ident}/valider",
    response_model=OperationFiche,
    dependencies=[droit(*C)],
    summary="Valide une opération : numéro donné, le stock bouge.",
    responses=reponses(401, 403, 404, 409, 422),
)
def valider(ident: int, e: ValidationVersion, qui: QuiDep, s: SessionDep) -> OperationFiche:
    """Route 120."""
    service.valider(s, qui, ident, e.version)
    return _fiche(service.fiche(s, ident, qui.role))


@routeur.post(
    "/operations/{ident}/annuler",
    response_model=OperationFiche,
    dependencies=[droit(*C)],
    summary="Annule une opération validée par contre-passation, une fois.",
    responses=reponses(401, 403, 404, 409, 422),
)
def annuler(ident: int, e: Annulation, qui: QuiDep, s: SessionDep) -> OperationFiche:
    """Route 121."""
    service.annuler(s, qui, ident, e.version, e.motif)
    return _fiche(service.fiche(s, ident, qui.role))


@routeur.get(
    "/brouillons",
    response_model=Brouillons,
    dependencies=[droit(*C)],
    summary="Tout ce qui attend d'être validé, avec ce qui le ferait refuser.",
    responses=reponses(401, 403),
)
def lister_brouillons(qui: QuiDep, s: SessionDep) -> Brouillons:
    """Route 122."""
    return Brouillons.model_validate(asdict(brouillons.lister(s, qui)))


@routeur.post(
    "/brouillons/valider",
    response_model=ResultatValidationGroupee,
    dependencies=[droit(*C)],
    summary="Valide les brouillons choisis (ou tous ceux du rôle), dans l'ordre des dates.",
    responses=reponses(401, 403, 422),
)
def tout_valider(e: SelectionBrouillons, qui: QuiDep, s: SessionDep) -> ResultatValidationGroupee:
    """Route 123 : un refus n'empêche pas les autres ; ce que le rôle ne peut pas est dit."""
    if not e.tous and not e.documents:
        raise Refus.saisie("Choisir les documents à valider, ou demander de tout valider.")
    choix = None if e.tous else [brouillons.Choix(x.genre, x.id, x.version) for x in e.documents]
    return ResultatValidationGroupee.model_validate(asdict(brouillons.tout_valider(s, qui, choix)))


@routeur.get(
    "/export/operations",
    response_class=Response,
    dependencies=[droit(*C)],
    summary="Le classeur des opérations (sans prix pour l'alimentation ; ses types seulement).",
    responses={**reponses(401, 403, 422), 200: {"content": {XLSX: {}}}},
)
def exporter(f: FiltresDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 241."""
    permis = tuple(droits.types_permis(qui.role))
    lues = service.toutes(s, FiltresOperations(f.type, f.statut, f.q, permis), qui.role)
    contenu = classeur.operations(lues, qui.voit_prix)
    nom = nom_de_fichier("operations", horloge.aujourd_hui())
    return Response(
        contenu, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nom}"'}
    )
