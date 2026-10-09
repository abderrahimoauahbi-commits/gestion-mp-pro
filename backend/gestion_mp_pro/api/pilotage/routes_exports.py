"""Les classeurs de l'analyse (API-PRO § 1.22 : routes 216–220), direction et achats.

Mêmes filtres que les écrans (mêmes dépendances que les routes 211–215) ; fichiers
« controles-AAAA-MM-JJ.xlsx », « valorisation-AAAA-MM-JJ.xlsx » (date de référence), etc.
"""

from __future__ import annotations

from fastapi import Response

from gestion_mp_pro.api.dependances import DateReferenceDep, SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.pilotage.routeur import CriteresDep, PeriodeDep, Q, routeur
from gestion_mp_pro.calcul.controles import synthese
from gestion_mp_pro.exports import pilotage as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import (
    horloge,
    pilotage,
    pilotage_controles,
    pilotage_fournisseurs,
    pilotage_prix,
)

XLSX = {**reponses(401, 403, 422), **REPONSES_XLSX}


@routeur.get(
    "/export/controles",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Les contrôles, quoi faire, et les lignes fautives de chacun, en classeur.",
    responses=XLSX,
)
def exporter_controles(jour: DateReferenceDep, s: SessionDep) -> Response:
    """Route 216 : gravités en clair, une feuille par contrôle en anomalie (toutes ses lignes)."""
    liste = pilotage_controles.rejouer(s, jour)
    return reponse(classeurs.controles(synthese(liste), liste, jour), "controles", jour)


@routeur.get(
    "/export/valorisation",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="La valorisation au soir de la date, matière par matière, en classeur.",
    responses=XLSX,
)
def exporter_valorisation(jour: DateReferenceDep, s: SessionDep) -> Response:
    """Route 217."""
    return reponse(classeurs.valorisation(pilotage.valorisation(s, jour)), "valorisation", jour)


@routeur.get(
    "/export/prix",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="L'historique des achats et la matrice des prix, en classeur.",
    responses=XLSX,
)
def exporter_prix(periode_: PeriodeDep, s: SessionDep, q: Q = "") -> Response:
    """Route 218 : vraies dates ; la matrice dans la devise des factures (E-04, E-12)."""
    du, au = periode_
    jour = horloge.aujourd_hui()
    h, m = pilotage_prix.historique(s, q, du, au), pilotage_prix.matrice(s, q)
    return reponse(classeurs.prix(h, m, jour, q), "prix", jour)


@routeur.get(
    "/export/opportunites",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Les opportunités d'économies avec ces critères, et l'avertissement, en classeur.",
    responses=XLSX,
)
def exporter_opportunites(jour: DateReferenceDep, c: CriteresDep, s: SessionDep) -> Response:
    """Route 219 : fenêtre bornée 1–3 650 jours, date acceptée (E-05)."""
    return reponse(
        classeurs.opportunites(pilotage_prix.opportunites(s, jour, c)), "opportunites", jour
    )


@routeur.get(
    "/export/fournisseurs",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le classement des fournisseurs et leurs réceptions notées, en classeur.",
    responses=XLSX,
)
def exporter_fournisseurs(periode_: PeriodeDep, s: SessionDep) -> Response:
    """Route 220 : classements sans émoji (P8-23)."""
    du, au = periode_
    jour = horloge.aujourd_hui()
    contenu = classeurs.fournisseurs(pilotage_fournisseurs.performance(s, du, au), jour)
    return reponse(contenu, "fournisseurs", jour)
