"""Le bon fournisseur — document A4 (164) et classeur (165), en anglais, sans aucun prix,
montant ni devise — et le classeur de la liste des bons (166). Direction et achats."""

from __future__ import annotations

from fastapi import Response
from fastapi.responses import HTMLResponse

from gestion_mp_pro.api.commandes.routeur import FiltresDep, routeur
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.documents import bon_commande, rendu
from gestion_mp_pro.exports import achats as classeurs
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, TYPE_XLSX, reponse
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.commandes_fiche import detailler

__all__ = ["routeur"]


@routeur.get(
    "/documents/commandes/{cid}/bon",
    response_class=HTMLResponse,
    dependencies=[droit(D, A)],
    summary="Le bon de commande à envoyer au fournisseur : A4, en anglais, sans aucun prix.",
    responses={**reponses(401, 403, 404), **rendu.REPONSES_HTML},
)
def imprimer_bon(cid: int, s: SessionDep) -> HTMLResponse:
    """Route 164."""
    return rendu.reponse(bon_commande.html(s, cid))


@routeur.get(
    "/export/commandes/{cid}/bon",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Le bon fournisseur dans un classeur : même contenu que le document, sans prix.",
    responses={**reponses(401, 403, 404, 409), **REPONSES_XLSX},
)
def exporter_bon(cid: int, s: SessionDep) -> Response:
    """Route 165."""
    contenu, nom = bon_commande.classeur(s, cid)
    return Response(
        contenu,
        media_type=TYPE_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@routeur.get(
    "/export/commandes",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Les bons de commande et leurs lignes en classeur (mêmes filtres que la liste).",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter_commandes(f: FiltresDep, s: SessionDep) -> Response:
    """Route 166."""
    return reponse(classeurs.commandes(detailler(s, f), f), "commandes", horloge.aujourd_hui())
