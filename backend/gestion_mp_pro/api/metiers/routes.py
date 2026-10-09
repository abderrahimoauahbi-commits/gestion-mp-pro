"""Routes du domaine « Métiers et montage » (API-PRO § 1.11 : routes 94–102 ; § 1.24 : 238).

La direction règle les métiers ; l'alimentation et la direction montent les fils (étage par
étage au téléphone, plusieurs étages au bureau) ; les trois rôles métier lisent (valeurs à
`null` pour l'alimentation, par le filtre générique).
"""

from __future__ import annotations

from typing import Any

from fastapi import Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.metiers.schemas import (
    EtageEntree,
    FilEntree,
    MatiereMontage,
    MetierCreation,
    MetierFiche,
    MetierModification,
    MetierModifie,
    MontageEntree,
    MontageEvenementFiche,
    ResultatMontage,
)
from gestion_mp_pro.exports import metiers as classeurs
from gestion_mp_pro.exports.production import XLSX, telecharger
from gestion_mp_pro.securite import C, D, L, QuiDep, droit
from gestion_mp_pro.services import metiers, metiers_lecture
from gestion_mp_pro.services.metiers import EtageMonte, FicheMetier
from gestion_mp_pro.services.montage import Fil

routeur = nouveau_routeur("metiers")

SANS_CORPS: dict[str, Any] = {"status_code": 204, "response_class": Response}


def _fils(etage: int, fils: list[FilEntree]) -> list[Fil]:
    """Les fils saisis, à leur étage."""
    return [Fil(etage, f.matiere_id, f.metres, f.pourcentage, f.commentaire) for f in fils]


def _demandes(m: MontageEntree) -> list[EtageMonte]:
    """Les étages demandés d'un montage."""
    return [EtageMonte(e.etage, e.version, _fils(e.etage, e.fils)) for e in m.etages]


def _fiche_metier(corps: MetierCreation) -> FicheMetier:
    """Le réglage saisi, pour le service."""
    return FicheMetier(
        corps.code, corps.nom, corps.laize, corps.bobines_par_metre, corps.etages, corps.actif,
        corps.commentaire,
    )  # fmt: skip


def _resultat(s: SessionDep, qui: QuiDep, r: metiers.ResultatMontage) -> dict[str, Any]:
    """Le résultat d'un montage, la fiche du métier relue."""
    s.flush()
    return {
        "metier": metiers_lecture.fiche(s, r.metier.id, qui.voit_prix),
        "effet_kg": r.effet_kg, "avant_kg": r.avant_kg, "apres_kg": r.apres_kg,
        "alertes": r.alertes, "message": r.message,
    }  # fmt: skip


@routeur.get(
    "/metiers",
    response_model=list[MetierFiche],
    dependencies=[droit(*C)],
    summary="Les métiers, leurs fils étage par étage, et ce qu'ils pèsent sur les métiers.",
    responses=reponses(401, 403),
)
def lister(qui: QuiDep, s: SessionDep) -> list[MetierFiche]:
    """Route 94."""
    return [MetierFiche.model_validate(x) for x in metiers_lecture.lister(s, qui.voit_prix)]


@routeur.get(
    "/metiers/{metier_id}",
    response_model=MetierFiche,
    dependencies=[droit(*C)],
    summary="La fiche d'un métier (avec la version de chaque étage).",
    responses=reponses(401, 403, 404),
)
def fiche(metier_id: int, qui: QuiDep, s: SessionDep) -> MetierFiche:
    """Route 95."""
    return MetierFiche.model_validate(metiers_lecture.fiche(s, metier_id, qui.voit_prix))


@routeur.post(
    "/metiers",
    status_code=201,
    response_model=MetierFiche,
    dependencies=[droit(D)],
    summary="Créer un métier à tisser et ses étages.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: MetierCreation, qui: QuiDep, s: SessionDep) -> MetierFiche:
    """Route 96."""
    x = metiers.creer(s, qui, _fiche_metier(corps))
    s.flush()
    return MetierFiche.model_validate(metiers_lecture.fiche(s, x.id, qui.voit_prix))


@routeur.put(
    "/metiers/{metier_id}",
    response_model=MetierModifie,
    dependencies=[droit(D)],
    summary="Régler un métier (fiche entière), avec son montage dans la même transaction.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier(
    metier_id: int, corps: MetierModification, qui: QuiDep, s: SessionDep
) -> MetierModifie:
    """Route 97 : `montage` facultatif (versions d'étage et effet confirmé)."""
    montage = (_demandes(corps.montage), corps.montage.confirme_effet_kg) if corps.montage else None
    r = metiers.modifier(
        s, qui, metier_id, _fiche_metier(corps), version=corps.version, montage=montage
    )
    resultat = _resultat(s, qui, r)
    return MetierModifie.model_validate(
        {**resultat["metier"], "montage": resultat if corps.montage else None}
    )


@routeur.delete(
    "/metiers/{metier_id}",
    dependencies=[droit(D)],
    summary="Supprimer un métier sans fil monté, jamais nommé par un ordre.",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def supprimer(metier_id: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> Response:
    """Route 98."""
    metiers.supprimer(s, qui, metier_id, version)
    return Response(status_code=204)


@routeur.put(
    "/metiers/{metier_id}/montage",
    response_model=ResultatMontage,
    dependencies=[droit(D, L)],
    summary="Monter les fils de plusieurs étages (versions d'étage, effet confirmé).",
    responses=reponses(401, 403, 404, 409, 422),
)
def monter(metier_id: int, corps: MontageEntree, qui: QuiDep, s: SessionDep) -> ResultatMontage:
    """Route 99 : les étages absents ne bougent pas ; aucun mouvement de stock n'est écrit."""
    r = metiers.monter(s, qui, metier_id, _demandes(corps), corps.confirme_effet_kg)
    return ResultatMontage.model_validate(_resultat(s, qui, r))


@routeur.put(
    "/metiers/{metier_id}/etages/{etage}",
    response_model=ResultatMontage,
    dependencies=[droit(D, L)],
    summary="Monter un étage (au téléphone) : les autres étages ne sont pas touchés.",
    responses=reponses(401, 403, 404, 409, 422),
)
def monter_etage(
    metier_id: int, etage: int, corps: EtageEntree, qui: QuiDep, s: SessionDep
) -> ResultatMontage:
    """Route 100 : protégé par la version de l'étage (deux téléphones : un seul passe)."""
    demande = EtageMonte(etage, corps.version, _fils(etage, corps.fils))
    r = metiers.monter(s, qui, metier_id, [demande], corps.confirme_effet_kg)
    return ResultatMontage.model_validate(_resultat(s, qui, r))


@routeur.get(
    "/metiers/{metier_id}/montages",
    response_model=list[MontageEvenementFiche],
    dependencies=[droit(*C)],
    summary="L'historique des montages d'un métier, le plus récent d'abord.",
    responses=reponses(401, 403, 404),
)
def montages(metier_id: int, s: SessionDep) -> list[MontageEvenementFiche]:
    """Route 101."""
    return [MontageEvenementFiche.model_validate(x) for x in metiers_lecture.montages(s, metier_id)]


@routeur.get(
    "/montage/matieres",
    response_model=list[MatiereMontage],
    dependencies=[droit(*C)],
    summary="Les matières qui se montent : poids de bobine compté, sorti en 30 jours, monté.",
    responses=reponses(401, 403),
)
def matieres(s: SessionDep) -> list[MatiereMontage]:
    """Route 102."""
    return [MatiereMontage.model_validate(x) for x in metiers_lecture.matieres_montables(s)]


@routeur.get(
    "/export/metiers",
    dependencies=[droit(*C)],
    summary="Les métiers et leurs fils montés en classeur (sans valeur pour l'alimentation).",
    responses={**reponses(401, 403), 200: {"content": {XLSX: {}}}},
    response_class=Response,
)
def exporter(qui: QuiDep, s: SessionDep) -> Response:
    """Route 238."""
    return telecharger(
        classeurs.metiers(metiers_lecture.lister(s, qui.voit_prix), qui.voit_prix), "metiers"
    )
