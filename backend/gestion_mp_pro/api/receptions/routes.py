"""Routes du domaine « Réceptions et factures » (API-PRO § 1.19 : routes 167–180).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Direction et achats
seulement (l'alimentation ne voit ni réceptions ni factures : décision D5). Chaque geste rend la
fiche relue. L'archive des pesées et le poids des bobines (176, 177) sont dans
`routes_pesees.py`, déclarés avant `/receptions/{rid}` ; les classeurs (178–180) dans
`routes_exports.py`.
"""

from __future__ import annotations

from dataclasses import asdict

from gestion_mp_pro.api.communs import ValidationVersion, encoder_curseur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.receptions import routes_exports, routes_pesees  # noqa: F401 — 176–180
from gestion_mp_pro.api.receptions.routeur import FiltresDep, routeur
from gestion_mp_pro.api.receptions.schemas import (
    AnnulationReception,
    ApercuReceptions,
    FactureCorrection,
    FactureResume,
    PageReceptions,
    ReceptionCreation,
    ReceptionFiche,
    ReceptionModification,
    ReceptionResume,
)
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services import contexte, receptions, receptions_facture, receptions_liste
from gestion_mp_pro.services.factures_lecture import FiltresFactures, lister
from gestion_mp_pro.services.receptions_fiche import fiche
from gestion_mp_pro.services.receptions_saisie import FactureSaisie, LigneSaisie, Saisie

__all__ = ["routeur"]

contexte.COMPTEURS["receptions_brouillon"] = receptions.brouillons_a_valider
"""La pastille « Réceptions » du menu (brouillons à valider ; direction et achats)."""

GESTE = reponses(401, 403, 404, 409, 422)


def _fiche(s: SessionDep, rid: int) -> ReceptionFiche:
    """La fiche relue après un geste."""
    return ReceptionFiche.model_validate(asdict(fiche(s, rid)))


def _saisie(corps: ReceptionCreation) -> Saisie:
    """La saisie, pour le service."""
    return Saisie(
        date=corps.date,
        fournisseur_id=corps.fournisseur_id,
        lignes=[LigneSaisie(**x.model_dump()) for x in corps.lignes],
        numero_bl=corps.numero_bl,
        controle_par=corps.controle_par,
        observations=corps.observations,
        factures={d: FactureSaisie(**f.model_dump()) for d, f in corps.factures.items()},
    )


def _curseur(pagination: PaginationDep) -> int | None:
    """Le n° d'entrée de la dernière réception rendue (curseur de pagination)."""
    if not pagination.apres:
        return None
    try:
        return int(str(pagination.apres[0]))
    except (ValueError, TypeError, IndexError) as exc:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        ) from exc


@routeur.get(
    "/receptions",
    response_model=PageReceptions,
    dependencies=[droit(D, A)],
    summary="Les réceptions, la plus récente d'abord, par pages ; brouillons recalés sans écrire.",
    responses=reponses(401, 403, 422),
)
def lister_receptions(f: FiltresDep, pagination: PaginationDep, s: SessionDep) -> PageReceptions:
    """Route 167 (filtres et recherche poussés en SQL ; total et pesé de l'onglet au serveur)."""
    page = receptions_liste.lister(s, f, _curseur(pagination), pagination.limite)
    suivant = encoder_curseur([page.dernier]) if page.dernier is not None else None
    return PageReceptions(
        elements=[ReceptionResume.model_validate(asdict(r)) for r in page.elements],
        total=page.total,
        suivant=suivant,
        pese_total=page.pese_total,
    )


@routeur.get(
    "/receptions/apercu",
    response_model=ApercuReceptions,
    dependencies=[droit(D, A)],
    summary="Les comptes par onglet (suivant la recherche) et les fournisseurs du filtre lié.",
    responses=reponses(401, 403, 422),
)
def apercu_receptions(s: SessionDep, q: str = "") -> ApercuReceptions:
    """Route 181b : nourrit les pastilles des onglets et les options du filtre fournisseur."""
    return ApercuReceptions.model_validate(asdict(receptions_liste.apercu(s, q[:200])))


@routeur.get(
    "/receptions/{rid}",
    response_model=ReceptionFiche,
    dependencies=[droit(D, A)],
    summary="La fiche d'une réception : lignes, blocages, avertissements, gestes permis.",
    responses=reponses(401, 403, 404),
)
def lire(rid: int, s: SessionDep) -> ReceptionFiche:
    """Route 168."""
    return _fiche(s, rid)


@routeur.post(
    "/receptions",
    response_model=list[ReceptionFiche],
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Enregistrer un camion en brouillon : une réception par devise, d'un seul coup.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: ReceptionCreation, qui: QuiDep, s: SessionDep) -> list[ReceptionFiche]:
    """Route 169."""
    creees = receptions.creer(s, qui, _saisie(corps))
    return [_fiche(s, r.id) for r in creees]


@routeur.put(
    "/receptions/{rid}",
    response_model=ReceptionFiche,
    dependencies=[droit(D, A)],
    summary="Corriger un brouillon (toutes ses lignes remplacées, une seule devise).",
    responses=GESTE,
)
def modifier(rid: int, corps: ReceptionModification, qui: QuiDep, s: SessionDep) -> ReceptionFiche:
    """Route 170."""
    receptions.modifier(s, qui, rid, corps.version, _saisie(corps))
    return _fiche(s, rid)


@routeur.delete(
    "/receptions/{rid}",
    status_code=204,
    dependencies=[droit(D, A)],
    summary="Supprimer un brouillon : rien n'est entré en stock, aucun numéro n'est perdu.",
    responses=GESTE,
)
def supprimer(rid: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> None:
    """Route 171."""
    receptions.supprimer(s, qui, rid, version)


@routeur.post(
    "/receptions/{rid}/valider",
    response_model=ReceptionFiche,
    dependencies=[droit(D, A)],
    summary="Valider : numéro, lots, entrées en stock au prix payé, soldes des bons recalés.",
    responses=GESTE,
)
def valider(rid: int, corps: ValidationVersion, qui: QuiDep, s: SessionDep) -> ReceptionFiche:
    """Route 172."""
    receptions.valider(s, qui, rid, corps.version)
    return _fiche(s, rid)


@routeur.post(
    "/receptions/{rid}/annuler",
    response_model=ReceptionFiche,
    dependencies=[droit(D, A)],
    summary="Annuler une réception validée (contre-passation ; toute refusée, sans mouvement).",
    responses=GESTE,
)
def annuler(rid: int, corps: AnnulationReception, qui: QuiDep, s: SessionDep) -> ReceptionFiche:
    """Route 173."""
    receptions.annuler(s, qui, rid, corps.version, corps.motif)
    return _fiche(s, rid)


@routeur.put(
    "/receptions/{rid}/facture",
    response_model=ReceptionFiche,
    dependencies=[droit(D, A)],
    summary="Compléter ou corriger la facture d'une réception validée (absent : inchangé).",
    responses=GESTE,
)
def facture(rid: int, corps: FactureCorrection, qui: QuiDep, s: SessionDep) -> ReceptionFiche:
    """Route 174."""
    valeurs = corps.model_dump(include=corps.model_fields_set - {"version"})
    receptions_facture.completer_facture(
        s, qui, rid, receptions_facture.FactureCorrigee(corps.version, valeurs)
    )
    return _fiche(s, rid)


@routeur.get(
    "/factures",
    response_model=list[FactureResume],
    dependencies=[droit(D, A)],
    summary="Les factures des fournisseurs, leurs réceptions et le dossier qui les porte.",
    responses=reponses(401, 403, 422),
)
def factures(
    s: SessionDep,
    fournisseur: int | None = None,
    q: str = "",
    sans_dossier: bool = False,
) -> list[FactureResume]:
    """Route 175."""
    filtres = FiltresFactures(fournisseur, q[:200], sans_dossier)
    return [FactureResume.model_validate(asdict(x)) for x in lister(s, filtres)]
