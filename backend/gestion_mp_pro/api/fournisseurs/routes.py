"""Routes du domaine « Fournisseurs » (API-PRO § 1.8, routes 64–69)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query, Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.fournisseurs.schemas import (
    FournisseurCreation,
    FournisseurFiche,
    FournisseurModification,
    FournisseurResume,
)
from gestion_mp_pro.exports import referentiels as classeurs
from gestion_mp_pro.modeles import Fournisseur
from gestion_mp_pro.securite import A, C, D, QuiDep, droit, peut
from gestion_mp_pro.services import fournisseurs

routeur = nouveau_routeur("fournisseurs")
SANS_CORPS = {"status_code": 204, "response_class": Response}
XLSX = {200: {"content": {classeurs.TYPE_XLSX: {}}, "description": "Classeur Excel"}}


def _fiche(f: Fournisseur, u: fournisseurs.Usages) -> FournisseurFiche:
    """La fiche d'un fournisseur et ses usages."""
    return FournisseurFiche(
        **{k: getattr(f, k) for k in FournisseurCreation.model_fields},
        id=f.id,
        version=f.version,
        local=fournisseurs.est_local(f.pays, f.devise),
        devises=u.devises,
        nb_matieres=u.nombre("matieres"),
        nb_commandes=u.nombre("commandes"),
        nb_receptions=u.nombre("receptions"),
        nb_lots=u.nombre("lots"),
        nb_operations=u.nombre("operations"),
        nb_factures=u.nombre("factures"),
        nb_pieces=u.nombre("pieces"),
        delai_mesure_jours=u.delai_mesure,
        livraisons_mesurees=len(u.delais),
        utilise=bool(u.empechements() or u.pieces_retirees),
        empechements=u.empechements(),
        modifie_le=f.modifie_le,
    )


@routeur.get(
    "/fournisseurs",
    response_model=list[FournisseurFiche | FournisseurResume],
    dependencies=[droit(*C)],
    summary="Les fournisseurs (l'alimentation : nom, pays et état seulement).",
    responses=reponses(401, 403, 422),
)
def lister(
    qui: QuiDep,
    s: SessionDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    actif: bool | None = None,
) -> list[FournisseurFiche | FournisseurResume]:
    """Route 64 : `q` cherche tous les mots, sans accents."""
    liste = fournisseurs.lister(s, q, actif)
    if not peut(qui, "voir_prix"):
        return [FournisseurResume.model_validate(f, from_attributes=True) for f in liste]
    usages = fournisseurs.usages(s)
    return [_fiche(f, usages.get(f.id, fournisseurs.Usages())) for f in liste]


@routeur.get(
    "/fournisseurs/{ident:int}",
    response_model=FournisseurFiche,
    dependencies=[droit(D, A)],
    summary="La fiche d'un fournisseur.",
    responses=reponses(401, 403, 404, 422),
)
def lire(ident: int, s: SessionDep) -> FournisseurFiche:
    """Route 65."""
    f = fournisseurs.fournisseur(s, ident)
    return _fiche(f, fournisseurs.usages(s, ident).get(ident, fournisseurs.Usages()))


@routeur.post(
    "/fournisseurs",
    response_model=FournisseurFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Créer un fournisseur.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: FournisseurCreation, qui: QuiDep, s: SessionDep) -> FournisseurFiche:
    """Route 66."""
    f = fournisseurs.creer(s, qui, corps.model_dump())
    return _fiche(f, fournisseurs.Usages())


@routeur.put(
    "/fournisseurs/{ident:int}",
    response_model=FournisseurFiche,
    dependencies=[droit(D, A)],
    summary="Modifier un fournisseur (la fiche entière, à sa version lue).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(
    ident: int, corps: FournisseurModification, qui: QuiDep, s: SessionDep
) -> FournisseurFiche:
    """Route 67."""
    f = fournisseurs.modifier(s, qui, ident, corps.model_dump(exclude={"version"}), corps.version)
    return _fiche(f, fournisseurs.usages(s, ident).get(ident, fournisseurs.Usages()))


@routeur.delete(
    "/fournisseurs/{ident:int}",
    dependencies=[droit(D, A)],
    summary="Supprimer un fournisseur sans aucune trace (sinon le désactiver).",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer(ident: int, qui: QuiDep, s: SessionDep, version: int | None = None) -> Response:
    """Route 68 : `?version=` facultatif (contrôlé s'il est donné)."""
    fournisseurs.supprimer(s, qui, ident, version)
    return Response(status_code=204)


@routeur.get(
    "/export/fournisseurs/fiches",
    dependencies=[droit(D, A)],
    summary="Les fiches des fournisseurs en classeur Excel.",
    responses={**reponses(401, 403), **XLSX},
    response_class=Response,
)
def exporter(s: SessionDep) -> Response:
    """Route 69 : contact, délais déclaré et mesuré, paiement, port, banque, devises."""
    contenu = classeurs.fournisseurs(fournisseurs.lister(s), fournisseurs.usages(s))
    nom = classeurs.nom_de_fichier("fournisseurs-fiches")
    return Response(
        contenu,
        media_type=classeurs.TYPE_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )
