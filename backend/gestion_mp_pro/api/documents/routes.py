"""Routes du domaine « Documents » : documents imprimables rendus par le serveur.

Squelette du lot S0, rempli par le lot D9 (route 114, étiquettes QR des lots) et les lots de
chaque document (bon fournisseur 164, feuille de comptage 133, bilan 234), qui se rendent par
`documents.rendu` (environnement commun, papier à en-tête, `rendu.reponse`). Routes minces :
chemin, droits, `summary` ; les données viennent d'un service ; aucune règle métier
(ARCHITECTURE § 3.1).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query, Request
from fastapi.responses import HTMLResponse

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.documents import etiquettes, rendu
from gestion_mp_pro.securite import C, droit
from gestion_mp_pro.services import appareils, lots_lecture

routeur = nouveau_routeur("documents")

LOTS_MAX = 4000
"""Longueur de `?lots=` (comme Gestion MP) : quelques centaines de lots."""


@routeur.get(
    "/documents/etiquettes",
    dependencies=[droit(*C)],
    summary="Les étiquettes QR des lots (100 × 70 mm), prêtes à imprimer.",
    responses={
        **reponses(401, 403, 422),
        **rendu.REPONSES_HTML,
        404: {"description": "Aucun lot à étiqueter (page HTML)", "content": {"text/html": {}}},
    },
    response_class=HTMLResponse,
)
def etiquettes_des_lots(
    requete: Request,
    s: SessionDep,
    lots: Annotated[
        str, Query(max_length=LOTS_MAX, description="identifiants des lots : 1,2,3")
    ] = "",
) -> HTMLResponse:
    """Route 114 : le QR porte l'adresse du lot (`{adresse}/lot/{id}`) ; lots inconnus dits."""
    donnees = lots_lecture.etiquettes(s, lots)
    acces = appareils.acces(s, str(requete.base_url))
    page = etiquettes.rendre(donnees, acces.adresse_qr, acces.alerte_localhost)
    return rendu.reponse(page.html, page.statut)
