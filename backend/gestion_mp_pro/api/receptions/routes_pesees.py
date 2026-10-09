"""L'archive des pesées (route 176, paginée) et le poids des bobines (177). Déclarées avant
`/receptions/{rid}` : un chemin fixe passe avant un identifiant."""

from __future__ import annotations

from dataclasses import asdict

from gestion_mp_pro.api.communs import encoder_curseur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.receptions.routeur import FiltresBobinesDep, FiltresPeseesDep, routeur
from gestion_mp_pro.api.receptions.schemas_pesees import EvolutionBobines, PagePesees, Pesee
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import receptions_pesees as service

__all__ = ["routeur"]


@routeur.get(
    "/receptions/pesees",
    response_model=PagePesees,
    dependencies=[droit(D, A)],
    summary="L'archive des pesées, lot par lot, la plus récente d'abord (paginée).",
    responses=reponses(401, 403, 422),
)
def pesees(f: FiltresPeseesDep, p: PaginationDep, s: SessionDep) -> PagePesees:
    """Route 176."""
    tout = service.pesees(s, f)
    lignes = service.apres(tout.lignes, p.apres)
    page = lignes[: p.limite]
    suivant = encoder_curseur(service.cle(page[-1])) if len(lignes) > p.limite else None
    return PagePesees(
        elements=[Pesee.model_validate(asdict(x)) for x in page],
        total=len(tout.lignes),
        suivant=suivant,
        tolerance=tout.tolerance,
        tolerance_bobine=tout.tolerance_bobine,
        kg_pesees=tout.kg_pesees,
        hors_tolerance=tout.hors_tolerance,
        non_conformes=tout.non_conformes,
        bobines_hors_tolerance=tout.bobines_hors_tolerance,
    )


@routeur.get(
    "/receptions/bobines",
    response_model=EvolutionBobines,
    dependencies=[droit(D, A)],
    summary="Le poids moyen d'une bobine, matière par matière, réception après réception.",
    responses=reponses(401, 403, 422),
)
def bobines(f: FiltresBobinesDep, s: SessionDep) -> EvolutionBobines:
    """Route 177."""
    return EvolutionBobines.model_validate(asdict(service.bobines(s, f)))
