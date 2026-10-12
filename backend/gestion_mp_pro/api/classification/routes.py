"""Routes du domaine « Classification » (API-PRO § 1.7, routes 57–63 et 255–257).

Les routes des rôles et des unités de titrage sont déclarées **avant** les routes génériques
`/classification/{liste}` : « roles » et « unites-titrage » ne sont pas des listes (R-REF-11).
"""

from __future__ import annotations

from fastapi import Response

from gestion_mp_pro.api.classification.schemas import (
    Classification,
    RoleCreation,
    RoleFiche,
    RoleModification,
    UniteCreation,
    UniteFiche,
    UniteModification,
    ValeurCreation,
    ValeurFiche,
    ValeurModification,
)
from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.modeles import RoleNomenclature, UniteTitrage
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import classification as cla
from gestion_mp_pro.services import unites_titrage as ut

routeur = nouveau_routeur("classification")
SANS_CORPS = {"status_code": 204, "response_class": Response}


def _valeur(v: cla.Valeur, portes: int = 0, avertissement: str = "") -> ValeurFiche:
    """La fiche d'une valeur (les seuls champs de sa liste)."""
    fiche = ValeurFiche.model_validate(v, from_attributes=True)
    return fiche.model_copy(update={"nb_matieres": portes, "avertissement": avertissement or None})


def _role(r: RoleNomenclature, matieres: int = 0, qualites: int = 0) -> RoleFiche:
    """La fiche d'un rôle."""
    return RoleFiche(
        id=r.id,
        code=r.code,
        lineaire=r.lineaire,
        de_base=r.de_base,
        ordre=r.ordre,
        version=r.version,
        nb_matieres=matieres,
        nb_qualites=qualites,
    )


def _unite(u: UniteTitrage, e: ut.Emploi, avertissement: str = "") -> UniteFiche:
    """La fiche d'une unité de titrage, son emploi et la raison de la garder."""
    return UniteFiche(
        id=u.id,
        code=u.code,
        libelle=u.libelle,
        ordre=u.ordre,
        actif=u.actif,
        version=u.version,
        nb_titrages=e.titrages,
        nb_matieres=e.matieres,
        raison_garder=ut.raison_de_garder(e),
        avertissement=avertissement or None,
    )


@routeur.get(
    "/classification",
    response_model=Classification,
    dependencies=[droit(*C)],
    summary="Toute la classification et les rôles, avec les matières qui les portent.",
    responses=reponses(401, 403),
)
def lire(s: SessionDep) -> Classification:
    """Route 57."""
    lu = cla.lire(s)

    def liste(nom: str) -> list[ValeurFiche]:
        """Les fiches d'une liste."""
        return [_valeur(v, n) for v, n in lu.valeurs[nom]]

    return Classification(
        compositions=liste("compositions"),
        types_fil=liste("types-fil"),
        titrages=liste("titrages"),
        couleurs=liste("couleurs"),
        roles=[_role(r, m, q) for r, m, q in lu.roles],
        unites_titrage=[_unite(u, e) for u, e in ut.lire(s)],
    )


@routeur.post(
    "/classification/roles",
    response_model=RoleFiche,
    status_code=201,
    dependencies=[droit(D)],
    summary="Ajouter un rôle de nomenclature (compté au poids).",
    responses=reponses(401, 403, 409, 422),
)
def ajouter_role(corps: RoleCreation, qui: QuiDep, s: SessionDep) -> RoleFiche:
    """Route 58."""
    return _role(cla.ajouter_role(s, qui, corps.code, corps.ordre))


@routeur.put(
    "/classification/roles/{ident}",
    response_model=RoleFiche,
    dependencies=[droit(D)],
    summary="Changer l'ordre ou le nom d'un rôle (un rôle de base garde son nom).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_role(ident: int, corps: RoleModification, qui: QuiDep, s: SessionDep) -> RoleFiche:
    """Route 59."""
    return _role(cla.modifier_role(s, qui, ident, corps.code, corps.ordre, version=corps.version))


@routeur.delete(
    "/classification/roles/{ident}",
    dependencies=[droit(D)],
    summary="Supprimer un rôle ajouté que rien ne porte.",
    responses=reponses(401, 403, 404, 409),
    **SANS_CORPS,
)
def supprimer_role(ident: int, qui: QuiDep, s: SessionDep) -> Response:
    """Route 60 : ses poids nuls partent avec lui."""
    cla.supprimer_role(s, qui, ident)
    return Response(status_code=204)


def _saisie_unite(corps: UniteCreation) -> ut.UniteSaisie:
    """Ce qu'on saisit d'une unité de titrage."""
    return ut.UniteSaisie(corps.code, corps.libelle, corps.ordre, corps.actif)


@routeur.post(
    "/classification/unites-titrage",
    response_model=UniteFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ajouter une unité de titrage : elle se lit aussitôt dans les références.",
    responses=reponses(401, 403, 409, 422),
)
def ajouter_unite(corps: UniteCreation, qui: QuiDep, s: SessionDep) -> UniteFiche:
    """Route 255 : code unique sans tenir compte de la casse (409 `doublon`)."""
    u = ut.ajouter(s, qui, _saisie_unite(corps))
    return _unite(u, ut.Emploi())


@routeur.put(
    "/classification/unites-titrage/{ident}",
    response_model=UniteFiche,
    dependencies=[droit(D, A)],
    summary="Modifier une unité de titrage (employée : son code ne change pas, elle se désactive).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_unite(ident: int, corps: UniteModification, qui: QuiDep, s: SessionDep) -> UniteFiche:
    """Route 256 : `avertissement` dit les titrages qui gardent une unité désactivée."""
    u, avertissement = ut.modifier(s, qui, ident, _saisie_unite(corps), version=corps.version)
    return _unite(u, ut.emploi(s, u.code), avertissement)


@routeur.delete(
    "/classification/unites-titrage/{ident}",
    dependencies=[droit(D, A)],
    summary="Supprimer une unité de titrage qu'aucun titrage n'écrit.",
    responses=reponses(401, 403, 404, 409),
    **SANS_CORPS,
)
def supprimer_unite(ident: int, qui: QuiDep, s: SessionDep, version: int | None = None) -> Response:
    """Route 257 : `?version=` facultatif (contrôlé s'il est donné)."""
    ut.supprimer(s, qui, ident, version)
    return Response(status_code=204)


def _saisie(corps: ValeurCreation) -> cla.ValeurSaisie:
    """Le code et les champs saisis."""
    return cla.ValeurSaisie(corps.code, corps.model_dump(exclude={"code", "version"}))


@routeur.post(
    "/classification/{liste}",
    response_model=ValeurFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ajouter une valeur à une liste de classification.",
    responses=reponses(401, 403, 404, 409, 422),
)
def ajouter_valeur(liste: str, corps: ValeurCreation, qui: QuiDep, s: SessionDep) -> ValeurFiche:
    """Route 61 : `liste` ∈ compositions, types-fil, titrages, couleurs."""
    return _valeur(cla.ajouter(s, qui, cla.liste(liste), _saisie(corps)))


@routeur.put(
    "/classification/{liste}/{ident}",
    response_model=ValeurFiche,
    dependencies=[droit(D, A)],
    summary="Modifier une valeur (le code se corrige ; désactivée, elle reste portée).",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_valeur(
    liste: str, ident: int, corps: ValeurModification, qui: QuiDep, s: SessionDep
) -> ValeurFiche:
    """Route 62 : `avertissement` dit les matières qui gardent une valeur désactivée."""
    x = cla.liste(liste)
    v, avertissement = cla.modifier(s, qui, x, ident, _saisie(corps), version=corps.version)
    return _valeur(v, avertissement=avertissement)


@routeur.delete(
    "/classification/{liste}/{ident}",
    dependencies=[droit(D, A)],
    summary="Supprimer une valeur que nulle matière ne porte.",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer_valeur(
    liste: str, ident: int, qui: QuiDep, s: SessionDep, version: int | None = None
) -> Response:
    """Route 63 : `?version=` facultatif (contrôlé s'il est donné)."""
    cla.supprimer(s, qui, cla.liste(liste), ident, version)
    return Response(status_code=204)
