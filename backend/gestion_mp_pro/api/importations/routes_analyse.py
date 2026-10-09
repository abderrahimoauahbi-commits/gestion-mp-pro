"""Le classeur des dossiers (route 205) et le coût de revient (206–208) : mêmes filtres que
l'écran."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import Response

from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.importations.routeur import (
    FiltresAnalyseDep,
    FiltresDossiersDep,
    routeur,
)
from gestion_mp_pro.api.importations.schemas_analyse import AnalyseRevient, CoutQualite
from gestion_mp_pro.exports import importations as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import analyse_revient, horloge
from gestion_mp_pro.services.importations.lecture import detailler

__all__ = ["routeur"]

XLSX = {**reponses(401, 403, 404, 422), **REPONSES_XLSX}


@routeur.get(
    "/export/dossiers",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Les dossiers, leurs marchandises, leurs frais et leur échéancier en classeur.",
    responses=XLSX,
)
def exporter_dossiers(f: FiltresDossiersDep, s: SessionDep) -> Response:
    """Route 205."""
    contenu = classeurs.dossiers(detailler(s, f), f)
    return reponse(contenu, "dossiers-importation", horloge.aujourd_hui())


@routeur.get(
    "/analyse/revient",
    response_model=AnalyseRevient,
    dependencies=[droit(D, A)],
    summary="Ce que la matière importée a coûté rendue usine, par axe et par critères.",
    responses=reponses(401, 403, 404, 422),
)
def analyser(f: FiltresAnalyseDep, s: SessionDep) -> AnalyseRevient:
    """Route 206."""
    return AnalyseRevient.model_validate(asdict(analyse_revient.analyser(s, f)))


@routeur.get(
    "/analyse/revient/qualites/{qid}",
    response_model=CoutQualite,
    dependencies=[droit(D, A)],
    summary="Le coût matière d'une qualité, pondéré par sa recette, au coût de revient réel.",
    responses=reponses(401, 403, 404, 422),
)
def cout_qualite(
    qid: int, s: SessionDep, du: date | None = None, au: date | None = None
) -> CoutQualite:
    """Route 207."""
    return CoutQualite.model_validate(asdict(analyse_revient.qualite(s, qid, du, au)))


@routeur.get(
    "/export/revient",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le coût de revient en classeur : le regroupement, puis le détail lot par lot.",
    responses=XLSX,
)
def exporter_revient(f: FiltresAnalyseDep, s: SessionDep) -> Response:
    """Route 208 : les mêmes filtres que l'analyse, le détail compris."""
    complet = analyse_revient.FiltresAnalyse(**{**asdict(f), "detail": True})
    contenu = classeurs.revient(analyse_revient.analyser(s, complet), complet)
    return reponse(contenu, "cout-de-revient", horloge.aujourd_hui())
