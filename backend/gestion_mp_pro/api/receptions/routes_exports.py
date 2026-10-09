"""Les classeurs des réceptions (routes 178–180) : mêmes filtres que leurs listes."""

from __future__ import annotations

from fastapi import Response

from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.receptions.routeur import (
    FiltresBobinesDep,
    FiltresDep,
    FiltresPeseesDep,
    routeur,
)
from gestion_mp_pro.exports import receptions as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import horloge, receptions_pesees
from gestion_mp_pro.services.receptions_liste import detailler

__all__ = ["routeur"]

XLSX = {**reponses(401, 403, 422), **REPONSES_XLSX}


@routeur.get(
    "/export/receptions",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Les réceptions et leurs lignes pesées en classeur (mêmes filtres que la liste).",
    responses=XLSX,
)
def exporter_receptions(f: FiltresDep, s: SessionDep) -> Response:
    """Route 178."""
    return reponse(classeurs.receptions(detailler(s, f), f), "receptions", horloge.aujourd_hui())


@routeur.get(
    "/export/receptions/pesees",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="L'archive des pesées en classeur (mêmes filtres que l'écran).",
    responses=XLSX,
)
def exporter_pesees(f: FiltresPeseesDep, s: SessionDep) -> Response:
    """Route 179."""
    contenu = classeurs.pesees(receptions_pesees.pesees(s, f), f)
    return reponse(contenu, "archive-des-pesees", horloge.aujourd_hui())


@routeur.get(
    "/export/receptions/bobines",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le poids des bobines en classeur : par matière, et chaque mesure.",
    responses=XLSX,
)
def exporter_bobines(f: FiltresBobinesDep, s: SessionDep) -> Response:
    """Route 180."""
    contenu = classeurs.bobines(receptions_pesees.bobines(s, f), f)
    return reponse(contenu, "poids-des-bobines", horloge.aujourd_hui())
