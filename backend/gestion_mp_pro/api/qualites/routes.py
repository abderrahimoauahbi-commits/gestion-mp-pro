"""Routes du domaine « Qualités » (API-PRO § 1.10 : routes 82–93).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. La direction écrit
les qualités, les recettes et le plan ; les trois rôles métier lisent (coûts et prix à `null`
pour l'alimentation, par le filtre générique).
"""

from __future__ import annotations

from typing import Any

from fastapi import Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import DateReferenceDep, SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.qualites.schemas import (
    LigneRecetteEntree,
    Nomenclature,
    PlanQualiteEntree,
    PlanVersionFiche,
    PoidsEntree,
    QualiteCreation,
    QualiteFiche,
    QualiteModification,
    QualiteResume,
    RecetteEntree,
    RecetteVersionFiche,
    Restauration,
)
from gestion_mp_pro.exports import qualites as classeurs
from gestion_mp_pro.exports.production import XLSX, telecharger
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import qualites, qualites_lecture
from gestion_mp_pro.services.qualites import FicheSaisie, PoidsSaisi, Resultat
from gestion_mp_pro.services.recettes import LigneSaisie

routeur = nouveau_routeur("qualites")

SANS_CORPS: dict[str, Any] = {"status_code": 204, "response_class": Response}


def _poids(poids: list[PoidsEntree]) -> list[PoidsSaisi]:
    """Les poids saisis, pour le service."""
    return [PoidsSaisi(p.role_id, p.poids) for p in poids]


def _lignes(lignes: list[LigneRecetteEntree]) -> list[LigneSaisie]:
    """Les lignes de recette saisies, pour le service."""
    return [LigneSaisie(x.matiere_id, x.pourcentage) for x in lignes]


def _fiche(s: SessionDep, qui: QuiDep, r: Resultat) -> QualiteFiche:
    """La fiche relue après le geste, avec son avertissement."""
    s.flush()
    lue = qualites_lecture.fiche(s, r.qualite.id, qui.voit_prix)
    return QualiteFiche.model_validate({**lue, "avertissement": r.avertissement})


@routeur.get(
    "/qualites",
    response_model=list[QualiteResume],
    dependencies=[droit(*C)],
    summary="Les qualités : poids, plan, recette calculée, contrôle des 100 %, coût au m².",
    responses=reponses(401, 403),
)
def lister(qui: QuiDep, s: SessionDep) -> list[QualiteResume]:
    """Route 82 (facteurs de coût compris : l'ancienne route A19 y est fondue)."""
    return [QualiteResume.model_validate(x) for x in qualites_lecture.lister(s, qui.voit_prix)]


@routeur.get(
    "/qualites/{qualite_id}",
    response_model=QualiteFiche,
    dependencies=[droit(*C)],
    summary="La fiche d'une qualité.",
    responses=reponses(401, 403, 404),
)
def fiche(qualite_id: int, qui: QuiDep, s: SessionDep) -> QualiteFiche:
    """Route 83."""
    return QualiteFiche.model_validate(qualites_lecture.fiche(s, qualite_id, qui.voit_prix))


@routeur.post(
    "/qualites",
    status_code=201,
    response_model=QualiteFiche,
    dependencies=[droit(D)],
    summary="Créer une qualité : sa première version de recette et de plan naissent avec elle.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: QualiteCreation, qui: QuiDep, s: SessionDep) -> QualiteFiche:
    """Route 84."""
    saisie = FicheSaisie(corps.code, corps.nom, corps.actif, _poids(corps.poids))
    return _fiche(s, qui, qualites.creer(s, qui, saisie))


@routeur.put(
    "/qualites/{qualite_id}",
    response_model=QualiteFiche,
    dependencies=[droit(D)],
    summary="Modifier une qualité (fiche entière), avec sa recette dans la même transaction.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(
    qualite_id: int, corps: QualiteModification, qui: QuiDep, s: SessionDep
) -> QualiteFiche:
    """Route 85 : `recette` facultative ; un rôle pesant sans matière est refusé pour une
    qualité en service dont la recette est commencée, signalé sinon (`avertissement`)."""
    saisie = FicheSaisie(
        corps.code,
        corps.nom,
        corps.actif,
        _poids(corps.poids),
        _lignes(corps.recette) if corps.recette is not None else None,
        corps.motif,
    )
    return _fiche(s, qui, qualites.modifier(s, qui, qualite_id, saisie, corps.version))


@routeur.delete(
    "/qualites/{qualite_id}",
    dependencies=[droit(D)],
    summary="Supprimer une qualité jamais fabriquée (sa recette, son plan et leurs versions).",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer(qualite_id: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 86."""
    qualites.supprimer(s, qui, qualite_id, version)
    return Response(status_code=204)


@routeur.put(
    "/qualites/{qualite_id}/recette",
    response_model=QualiteFiche,
    dependencies=[droit(D)],
    summary="Remplacer la recette : 100 % dans chaque rôle, aucun rôle pesant sans matière.",
    responses=reponses(401, 403, 404, 409, 422),
)
def ecrire_recette(
    qualite_id: int, corps: RecetteEntree, qui: QuiDep, s: SessionDep
) -> QualiteFiche:
    """Route 87."""
    r = qualites.ecrire_recette(
        s, qui, qualite_id, _lignes(corps.lignes), motif=corps.motif, version=corps.version
    )
    return _fiche(s, qui, r)


@routeur.get(
    "/qualites/{qualite_id}/versions",
    response_model=list[RecetteVersionFiche],
    dependencies=[droit(*C)],
    summary="Les versions de la recette, de la plus récente à la plus ancienne.",
    responses=reponses(401, 403, 404),
)
def versions(qualite_id: int, s: SessionDep) -> list[RecetteVersionFiche]:
    """Route 88."""
    return [
        RecetteVersionFiche.model_validate(x)
        for x in qualites_lecture.versions_recette(s, qualite_id)
    ]


@routeur.post(
    "/qualites/{qualite_id}/versions/{version_id}/restaurer",
    response_model=QualiteFiche,
    dependencies=[droit(D)],
    summary="Revenir à une version : ses parts et ses poids au m², d'un bloc, avec un motif.",
    responses=reponses(401, 403, 404, 409, 422),
)
def restaurer(
    qualite_id: int, version_id: int, corps: Restauration, qui: QuiDep, s: SessionDep
) -> QualiteFiche:
    """Route 89 : une seule version nouvelle, signée et motivée."""
    r = qualites.restaurer(s, qui, qualite_id, version_id, motif=corps.motif, version=corps.version)
    return _fiche(s, qui, r)


@routeur.put(
    "/qualites/{qualite_id}/plan",
    response_model=QualiteFiche,
    dependencies=[droit(D)],
    summary="Le plan d'une qualité : base mensuelle et douze coefficients (version tracée).",
    responses=reponses(401, 403, 404, 409, 422),
)
def ecrire_plan(
    qualite_id: int, corps: PlanQualiteEntree, qui: QuiDep, s: SessionDep
) -> QualiteFiche:
    """Route 90 : une version du plan seulement si quelque chose change."""
    r = qualites.ecrire_plan(
        s,
        qui,
        qualite_id,
        corps.base_mensuelle,
        coefficients=corps.coefficients,
        motif=corps.motif,
        version=corps.version,
    )
    return _fiche(s, qui, r)


@routeur.get(
    "/qualites/{qualite_id}/plan/versions",
    response_model=list[PlanVersionFiche],
    dependencies=[droit(*C)],
    summary="Les versions du plan d'une qualité (la plus ancienne vaut depuis toujours).",
    responses=reponses(401, 403, 404),
)
def versions_plan(qualite_id: int, s: SessionDep) -> list[PlanVersionFiche]:
    """Route 91."""
    return [
        PlanVersionFiche.model_validate(x) for x in qualites_lecture.versions_plan(s, qualite_id)
    ]


@routeur.get(
    "/nomenclature",
    response_model=Nomenclature,
    dependencies=[droit(*C)],
    summary="Chaque matière de chaque qualité (kg/m², ml/m², coût) et le contrôle des recettes.",
    responses=reponses(401, 403, 422),
)
def nomenclature(jour: DateReferenceDep, qui: QuiDep, s: SessionDep) -> Nomenclature:
    """Route 92 : la nomenclature en vigueur (`date` bornée ; les recettes passées sont dans
    les versions, route 88)."""
    del jour
    return Nomenclature.model_validate(qualites_lecture.lire_nomenclature(s, qui.voit_prix))


@routeur.get(
    "/export/qualites",
    dependencies=[droit(D, A)],
    summary="Les qualités et leurs recettes, matière par matière, en classeur.",
    responses={**reponses(401, 403), 200: {"content": {XLSX: {}}}},
    response_class=Response,
)
def exporter(qui: QuiDep, s: SessionDep) -> Response:
    """Route 93 : « En service » et « Fabriquée » (vraie) en deux colonnes (D-19)."""
    return telecharger(classeurs.qualites(qualites_lecture.lister(s, qui.voit_prix)), "qualites")
