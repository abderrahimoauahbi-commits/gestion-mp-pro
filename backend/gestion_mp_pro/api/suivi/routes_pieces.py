"""Routes des pièces jointes (API-PRO § 1.23 : routes 224–227), direction et achats.

Un fichier par dépôt (multipart `objet`, `id`, `fichier`), relu en `attachment` (jamais affiché
dans la page), retiré logiquement. Les règles (liste blanche, premiers octets, 20 Mo lus par
blocs, 404 / 410) sont dans `services/pieces.py`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse

from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.suivi.routeur import routeur
from gestion_mp_pro.api.suivi.schemas import PieceFiche
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services import pieces

Objet = Annotated[str, Query(max_length=20, description="dossier, reception, commande, …")]


@routeur.get(
    "/pieces",
    response_model=list[PieceFiche],
    dependencies=[droit(D, A)],
    summary="Les pièces jointes d'un document, la plus ancienne d'abord.",
    responses=reponses(401, 403, 404, 422),
)
def lister(
    objet: Objet, ident: Annotated[int, Query(alias="id")], s: SessionDep
) -> list[PieceFiche]:
    """Route 224 : objet ou document inconnu → 404 « Document inconnu. »."""
    return [PieceFiche.model_validate(x) for x in pieces.fiches(s, pieces.lister(s, objet, ident))]


@routeur.post(
    "/pieces",
    response_model=PieceFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Joindre un fichier à un document (PDF, image, tableur, texte, document ; 20 Mo).",
    responses=reponses(401, 403, 404, 422),
)
def deposer(
    objet: Annotated[str, Form(max_length=20)],
    ident: Annotated[int, Form(alias="id")],
    fichier: Annotated[UploadFile, File()],
    qui: QuiDep,
    s: SessionDep,
) -> PieceFiche:
    """Route 225 : liste blanche, premiers octets, 20 Mo au plus lus par blocs (G-10)."""
    p = pieces.deposer(
        s,
        qui,
        objet,
        ident,
        nom=fichier.filename,
        declare=fichier.content_type,
        source=fichier.file,
    )
    return PieceFiche.model_validate(pieces.fiches(s, [p])[0])


@routeur.get(
    "/pieces/{ident}/fichier",
    response_class=FileResponse,
    dependencies=[droit(D, A)],
    summary="Le fichier d'une pièce jointe, à télécharger.",
    responses={
        **reponses(401, 403, 404, 410),
        200: {"content": {"application/octet-stream": {}}},
    },
)
def fichier(ident: int, s: SessionDep) -> FileResponse:
    """Route 226 : `attachment` ; retirée → 404 ; fichier disparu du disque → 410."""
    p, chemin = pieces.fichier(s, ident)
    return FileResponse(
        chemin,
        media_type=p.type_mime,
        filename=p.nom,
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@routeur.delete(
    "/pieces/{ident}",
    status_code=204,
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="Retirer une pièce jointe (retrait logique, tracé ; le fichier reste).",
    responses=reponses(401, 403, 404, 409),
)
def retirer(ident: int, qui: QuiDep, s: SessionDep) -> Response:
    """Route 227."""
    pieces.retirer(s, qui, ident)
    return Response(status_code=204)
