"""Routes du domaine « Suivi » (API-PRO § 1.23 : routes 221–234).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Les signalements sont
ouverts à tout rôle métier (l'atelier signale, la direction et les achats traitent) ; le reste
est réservé à la direction et aux achats. Les pièces jointes (224–227) sont dans
`routes_pieces.py`.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import Depends, Query, Response
from fastapi.responses import HTMLResponse

from gestion_mp_pro.api.communs import encoder_curseur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.pilotage.routeur import PeriodeAVenirDep, PeriodeDep, Q
from gestion_mp_pro.api.suivi import routes_pieces  # noqa: F401 — 224–227
from gestion_mp_pro.api.suivi.routeur import routeur
from gestion_mp_pro.api.suivi.schemas import (
    BilanMois,
    EcheanceLigne,
    Echeancier,
    IndicateurJour,
    PageSignalements,
    Paiement,
    SignalementCreation,
    SignalementFiche,
    Traitement,
)
from gestion_mp_pro.documents import rendu
from gestion_mp_pro.exports import echeancier as classeur_echeancier
from gestion_mp_pro.exports.classeur import REPONSES_XLSX, reponse
from gestion_mp_pro.securite import A, C, D, QuiDep, droit
from gestion_mp_pro.services import bilan, echeancier, horloge, indicateurs, suivi

Mois = Annotated[str, Query(max_length=10, description="AAAA-MM")]


@routeur.get(
    "/signalements",
    response_model=PageSignalements,
    dependencies=[droit(*C)],
    summary="Les besoins signalés par l'atelier, le plus récent d'abord.",
    responses=reponses(401, 403, 422),
)
def signalements(
    qui: QuiDep, p: PaginationDep, s: SessionDep, a_traiter: bool | None = None, mes: bool = False
) -> PageSignalements:
    """Route 221 : `a_traiter` (vrai : en attente ; faux : traités) ; `mes` : les miens."""
    apres = int(p.apres[0]) if p.apres and isinstance(p.apres[0], int) else None
    lus, total = suivi.lister(s, a_traiter, apres, p.limite, qui.id if mes else None)
    suivant = encoder_curseur([lus[-1].id]) if len(lus) == p.limite else None
    return PageSignalements(
        elements=[SignalementFiche.model_validate(asdict(x)) for x in lus],
        total=total,
        suivant=suivant,
    )


@routeur.post(
    "/signalements",
    response_model=SignalementFiche,
    status_code=201,
    dependencies=[droit(*C)],
    summary="Signaler un besoin (la direction et les achats sont prévenus).",
    responses=reponses(401, 403, 404, 422),
)
def signaler(corps: SignalementCreation, qui: QuiDep, s: SessionDep) -> SignalementFiche:
    """Route 222."""
    x = suivi.signaler(s, qui, corps.matiere_id, corps.texte, corps.urgence)
    return SignalementFiche.model_validate(asdict(x))


@routeur.post(
    "/signalements/{ident}/traiter",
    response_model=SignalementFiche,
    dependencies=[droit(D, A)],
    summary="Marquer un besoin traité, avec la réponse à l'atelier (une fois).",
    responses=reponses(401, 403, 404, 409, 422),
)
def traiter(ident: int, corps: Traitement, qui: QuiDep, s: SessionDep) -> SignalementFiche:
    """Route 223 : déjà traité → 409 (la réponse donnée ne s'écrase pas)."""
    return SignalementFiche.model_validate(asdict(suivi.traiter(s, qui, ident, corps.reponse)))


def filtres_echeancier(
    periode_: PeriodeAVenirDep, q: Q = "", nature: Literal["facture", "frais"] | None = None
) -> echeancier.Filtres:
    """Les filtres de l'échéancier (liste et classeur)."""
    du, au = periode_
    return echeancier.Filtres(q=q, nature=nature, du=du, au=au)


FiltresDep = Annotated[echeancier.Filtres, Depends(filtres_echeancier)]


@routeur.get(
    "/echeancier",
    response_model=Echeancier,
    dependencies=[droit(D, A)],
    summary="Ce qu'il faudra payer, et quand : factures des fournisseurs, frais d'importation.",
    responses=reponses(401, 403, 422),
)
def lire_echeancier(f: FiltresDep, s: SessionDep) -> Echeancier:
    """Route 228 : filtres au serveur ; l'échu se compte quelle que soit la période."""
    return Echeancier.model_validate(asdict(echeancier.calculer(s, f)))


@routeur.put(
    "/echeancier/paiement",
    response_model=EcheanceLigne,
    dependencies=[droit(D, A)],
    summary="Noter le règlement d'une facture ou d'un frais, ou l'annuler (direction, motif).",
    responses=reponses(401, 403, 404, 409, 422),
)
def regler(corps: Paiement, qui: QuiDep, s: SessionDep) -> EcheanceLigne:  # type: ignore[valid-type]
    """Route 229 : facture par `services.factures.regler` (D4) ; frais aux mêmes règles."""
    x = echeancier.regler(
        s,
        qui,
        corps.genre,
        corps.id,
        payee_le=corps.payee_le,
        version=corps.version,
        motif=corps.motif,
    )
    return EcheanceLigne.model_validate(x)


@routeur.get(
    "/export/echeancier",
    response_class=Response,
    dependencies=[droit(D, A)],
    summary="L'échéancier filtré en classeur : échéances, à dater, par mois, réglées, écartées.",
    responses={**reponses(401, 403, 422), **REPONSES_XLSX},
)
def exporter_echeancier(f: FiltresDep, s: SessionDep) -> Response:
    """Route 230 : les mêmes filtres que l'écran."""
    contenu = classeur_echeancier.echeancier(echeancier.calculer(s, f), f)
    return reponse(contenu, "echeancier", horloge.aujourd_hui())


@routeur.get(
    "/indicateurs/historique",
    response_model=list[IndicateurJour],
    dependencies=[droit(D, A)],
    summary="Les photos du jour des indicateurs, dans l'ordre des jours.",
    responses=reponses(401, 403, 422),
)
def historique_indicateurs(periode_: PeriodeDep, s: SessionDep) -> list[IndicateurJour]:
    """Route 231."""
    du, au = periode_
    return [IndicateurJour.model_validate(x) for x in indicateurs.historique(s, du, au)]


@routeur.post(
    "/indicateurs/photographier",
    response_model=IndicateurJour,
    dependencies=[droit(D)],
    summary="Prendre (ou reprendre) tout de suite la photo du jour des indicateurs.",
    responses=reponses(401, 403),
)
def photographier(qui: QuiDep, s: SessionDep) -> IndicateurJour:
    """Route 232 : journalisée (E-17)."""
    return IndicateurJour.model_validate(indicateurs.photographier(s, qui))


@routeur.get(
    "/bilan",
    response_model=BilanMois,
    dependencies=[droit(D, A)],
    summary="Le bilan matières d'un mois (magasins et métiers, kilos et dirhams).",
    responses=reponses(401, 403, 422),
)
def lire_bilan(mois: Mois, s: SessionDep) -> BilanMois:  # type: ignore[valid-type]
    """Route 233 : mois invalide ou futur → 422 (E-03)."""
    return BilanMois.model_validate(bilan.calculer(s, mois))


@routeur.get(
    "/documents/bilan",
    response_class=HTMLResponse,
    dependencies=[droit(D, A)],
    summary="Le bilan du mois à imprimer (A4, papier à en-tête).",
    responses={**reponses(401, 403, 422), **rendu.REPONSES_HTML},
)
def document_bilan(mois: Mois, s: SessionDep) -> HTMLResponse:
    """Route 234."""
    b = bilan.calculer(s, mois)
    html = rendu.rendre(
        "bilan.html",
        societe=rendu.societe(s),
        titre=f"Bilan {b['mois']}",
        b=b,
        libelles=bilan.LIBELLES,
    )
    return rendu.reponse(html)
