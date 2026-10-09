"""Routes du domaine « Pilotage et analyse » (API-PRO § 1.22 : 209–215 ; § 1.24 : 235 ; § 1.1 : 7).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Direction et achats
(la route 7, données brutes pour la vérification indépendante : direction seule). Les classeurs
216–220 sont dans `routes_exports.py`. La route 215 (`/fournisseurs/performance`) suit la fiche
d'un fournisseur (`/fournisseurs/{ident:int}`, lot D1) : l'entier du chemin les départage.
"""

from __future__ import annotations

from dataclasses import asdict

from gestion_mp_pro.api.communs import encoder_curseur
from gestion_mp_pro.api.dependances import (
    DateReferenceDep,
    PaginationDep,
    SessionDep,
    borner_date,
)
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.api.pilotage import routes_exports  # noqa: F401 — classeurs 216–220
from gestion_mp_pro.api.pilotage.routeur import CriteresDep, DateFacultative, PeriodeDep, Q, routeur
from gestion_mp_pro.api.pilotage.schemas import (
    Cockpit,
    Controles,
    DonneesBrutes,
    HistoriquePrix,
    MatricePrix,
    Opportunites,
    PageControle,
    PerformanceFournisseurs,
    Valorisation,
)
from gestion_mp_pro.securite import A, D, droit
from gestion_mp_pro.services import (
    donnees_brutes,
    pilotage,
    pilotage_controles,
    pilotage_fournisseurs,
    pilotage_prix,
)


@routeur.get(
    "/cockpit",
    response_model=Cockpit,
    dependencies=[droit(D, A)],
    summary="Le Cockpit : six indicateurs avec leur formule, alertes, ensemble, économies.",
    responses=reponses(401, 403, 422),
)
def cockpit(jour: DateReferenceDep, s: SessionDep) -> Cockpit:
    """Route 209 : la valeur du stock est celle de la Valorisation (E-06)."""
    return Cockpit.model_validate(pilotage_controles.cockpit(s, jour))


@routeur.get(
    "/valorisation",
    response_model=Valorisation,
    dependencies=[droit(D, A)],
    summary="La valeur du stock détenu (magasins et métiers) au coût moyen, matière par matière.",
    responses=reponses(401, 403, 422),
)
def valorisation(jour: DateReferenceDep, s: SessionDep) -> Valorisation:
    """Route 210 : au soir de la date, le fil monté de ce soir-là compris (U8)."""
    return Valorisation.model_validate(asdict(pilotage.valorisation(s, jour)))


@routeur.get(
    "/opportunites",
    response_model=Opportunites,
    dependencies=[droit(D, A)],
    summary="Où une matière comparable s'achète moins cher, à la même époque (coût rendu).",
    responses=reponses(401, 403, 422),
)
def opportunites(jour: DateReferenceDep, c: CriteresDep, s: SessionDep) -> Opportunites:
    """Route 211 : même couleur par défaut ; fenêtre 1–3 650 jours (sinon le réglage)."""
    return Opportunites.model_validate(asdict(pilotage_prix.opportunites(s, jour, c)))


@routeur.get(
    "/controles",
    response_model=Controles,
    dependencies=[droit(D, A)],
    summary="Les 38 contrôles de cohérence, leur synthèse, quoi faire, les lignes fautives.",
    responses=reponses(401, 403, 422),
)
def controles(jour: DateReferenceDep, s: SessionDep) -> Controles:
    """Route 212 : 200 lignes au plus par contrôle, le reste dit (`lignes_total`)."""
    return Controles.model_validate(asdict(pilotage_controles.controles(s, jour)))


@routeur.get(
    "/controles/{code}",
    response_model=PageControle,
    dependencies=[droit(D, A)],
    summary="Le détail complet d'un contrôle, cherché sur tous les mots, page par page.",
    responses=reponses(401, 403, 404, 422),
)
def controle(
    code: str, jour: DateReferenceDep, p: PaginationDep, s: SessionDep, q: Q = ""
) -> PageControle:
    """Route 235 : chaque ligne porte les ids des fiches qu'elle nomme."""
    c, lignes = pilotage_controles.detail(s, jour, code, q)
    debut = int(p.apres[0]) if p.apres and isinstance(p.apres[0], int) else 0
    page = lignes[debut : debut + p.limite]
    fin = debut + len(page)
    return PageControle(
        elements=page,
        total=len(lignes),
        suivant=encoder_curseur([fin]) if fin < len(lignes) else None,
        code=c.code,
        libelle=c.libelle,
        gravite=c.gravite,
        quoi_faire=c.quoi_faire,
        lien=c.lien,
        colonnes=[asdict(x) for x in c.colonnes],
    )


@routeur.get(
    "/prix/historique",
    response_model=HistoriquePrix,
    dependencies=[droit(D, A)],
    summary="Les prix payés, leur précédent et leur évolution, le plus récent d'abord.",
    responses=reponses(401, 403, 422),
)
def historique_des_prix(periode_: PeriodeDep, s: SessionDep, q: Q = "") -> HistoriquePrix:
    """Route 213 : cherché sur tous les mots ; `du`/`au` sur la date de la réception."""
    du, au = periode_
    return HistoriquePrix.model_validate(asdict(pilotage_prix.historique(s, q, du, au)))


@routeur.get(
    "/prix/matrice",
    response_model=MatricePrix,
    dependencies=[droit(D, A)],
    summary="La matrice des prix : prix moyen pondéré par mois, dans la devise des factures.",
    responses=reponses(401, 403, 422),
)
def matrice_des_prix(s: SessionDep, q: Q = "") -> MatricePrix:
    """Route 214 : une ligne par (matière, devise), 36 mois au plus (E-04)."""
    return MatricePrix.model_validate(asdict(pilotage_prix.matrice(s, q)))


@routeur.get(
    "/fournisseurs/performance",
    response_model=PerformanceFournisseurs,
    dependencies=[droit(D, A)],
    summary="Le classement des fournisseurs : OTIF, retours, délai, score sur 100.",
    responses=reponses(401, 403, 422),
)
def performance_fournisseurs(periode_: PeriodeDep, s: SessionDep) -> PerformanceFournisseurs:
    """Route 215 : la note sur toute l'histoire, ou sur une période."""
    du, au = periode_
    return PerformanceFournisseurs.model_validate(
        asdict(pilotage_fournisseurs.performance(s, du, au))
    )


@routeur.get(
    "/donnees/{table}",
    response_model=DonneesBrutes,
    dependencies=[droit(D)],
    summary="Les lignes brutes d'une table métier (liste fermée), pour la vérification.",
    responses=reponses(401, 403, 404, 422),
)
def donnees(table: str, s: SessionDep, jour: DateFacultative = None) -> DonneesBrutes:
    """Route 7 : `?date=` borne les tables datées au soir de ce jour."""
    lues = donnees_brutes.lire(s, table, borner_date(jour) if jour is not None else None)
    return DonneesBrutes.model_validate(asdict(lues))
