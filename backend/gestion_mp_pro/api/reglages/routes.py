"""Routes du domaine « Réglages » (API-PRO § 1.3) : réglages, période close, devises (23–30).

Magasins, postes de frais, codes douaniers et motifs (31–42) : `routes_referentiels.py`, qui
s'inscrit sur le même routeur. Routes minces : droits, schémas, un appel de service.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from gestion_mp_pro.api.communs import encoder_curseur, nouveau_routeur
from gestion_mp_pro.api.dependances import PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.reglages.schemas import (
    ClotureEntree,
    CoursHistorique,
    DeviseCreation,
    DeviseFiche,
    DeviseModification,
    PageCoursHistorique,
    PageReglageHistorique,
    Periode,
    Reglage,
    ReglageHistorique,
    ReglagesEcriture,
)
from gestion_mp_pro.modeles import Devise
from gestion_mp_pro.securite import A, D, QuiDep, T, droit
from gestion_mp_pro.services import devises, periode, reglages

routeur = nouveau_routeur("reglages")


def _reglages(s: SessionDep, role: str) -> list[Reglage]:
    """Les réglages tels que le rôle les voit."""
    return [
        Reglage(
            cle=x.reglage.cle,
            libelle=x.reglage.libelle,
            famille=x.reglage.famille,
            unite=x.reglage.unite,
            echelle=x.reglage.echelle,
            aide=x.reglage.aide,
            bas=x.reglage.bas,
            haut=x.reglage.haut,
            texte=x.reglage.texte,
            defaut=x.reglage.defaut,
            valeur=x.valeur,
            technique=x.reglage.technique,
            modifiable=x.reglage.modifiable,
            version=x.version,
            version_globale=x.version_globale,
        )
        for x in reglages.lire(s, role)
    ]


def _apres(pagination: PaginationDep) -> int | None:
    """Le curseur des historiques : l'id de la dernière ligne rendue."""
    if not pagination.apres:
        return None
    valeur = pagination.apres[0]
    if not isinstance(valeur, int):
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        )
    return valeur


@routeur.get(
    "/parametres",
    response_model=list[Reglage],
    dependencies=[droit(D, A, T)],
    summary="Les réglages (l'administrateur : la famille technique seule).",
    responses=reponses(401, 403),
)
def lire_parametres(qui: QuiDep, s: SessionDep) -> list[Reglage]:
    """Route 23 : la direction écrit, les achats lisent ; l'alimentation n'y a pas accès."""
    return _reglages(s, qui.role)


@routeur.put(
    "/parametres",
    response_model=list[Reglage],
    dependencies=[droit(D, T)],
    summary="Écrire des réglages, tout ou rien (seuils dans l'ordre, version à jour).",
    responses=reponses(401, 403, 409, 422),
)
def ecrire_parametres(corps: ReglagesEcriture, qui: QuiDep, s: SessionDep) -> list[Reglage]:
    """Route 24 : l'administrateur n'écrit que la famille technique."""
    reglages.ecrire(s, qui, corps.valeurs, corps.version_globale)
    return _reglages(s, qui.role)


@routeur.get(
    "/parametres/historique",
    response_model=PageReglageHistorique,
    dependencies=[droit(D, T)],
    summary="Les changements des réglages, les plus récents d'abord.",
    responses=reponses(401, 403, 422),
)
def historique_parametres(
    qui: QuiDep,
    s: SessionDep,
    pagination: PaginationDep,
    cle: Annotated[str | None, Query(max_length=60)] = None,
) -> PageReglageHistorique:
    """Route 25 : avant, après, par, quand, motif."""
    lignes, total, dernier = reglages.historique(
        s, qui.role, cle, _apres(pagination), pagination.limite
    )
    return PageReglageHistorique(
        elements=[ReglageHistorique.model_validate(x, from_attributes=True) for x in lignes],
        total=total,
        suivant=encoder_curseur([dernier]) if dernier is not None else None,
    )


def _periode(s: SessionDep, p: periode.Periode) -> Periode:
    """La période close et la version de sa clôture."""
    return Periode(
        date_cloture=p.date_cloture, par=p.par, quand=p.quand, version=reglages.version_cloture(s)
    )


@routeur.put(
    "/periode-close",
    response_model=Periode,
    dependencies=[droit(D)],
    summary="Clore la période jusqu'à une date passée (ou la rouvrir), avec un motif.",
    responses=reponses(401, 403, 409, 422),
)
def clore_periode(corps: ClotureEntree, qui: QuiDep, s: SessionDep) -> Periode:
    """Route 26 : brouillons datés de la période refusés ; historique et journal."""
    p = reglages.clore_periode(s, qui, corps.date_cloture, corps.motif, corps.version)
    return _periode(s, p)


def _devise(d: Devise, reprises: set[str]) -> DeviseFiche:
    """La fiche d'une devise."""
    return DeviseFiche(
        code=d.code,
        nom=d.nom,
        cours=d.cours,
        cours_le=d.cours_le,
        cours_repris=d.code in reprises,
        actif=d.actif,
        version=d.version,
    )


@routeur.get(
    "/devises",
    response_model=list[DeviseFiche],
    dependencies=[droit(D, A)],
    summary="Les devises et leur cours du jour (MAD pour une unité).",
    responses=reponses(401, 403),
)
def lire_devises(s: SessionDep) -> list[DeviseFiche]:
    """Route 27."""
    liste, reprises = devises.lister(s)
    return [_devise(d, reprises) for d in liste]


@routeur.get(
    "/devises/{code}/cours",
    response_model=PageCoursHistorique,
    dependencies=[droit(D, A)],
    summary="Les cours successifs d'une devise, le plus récent d'abord.",
    responses=reponses(401, 403, 404, 422),
)
def cours_devise(code: str, s: SessionDep, pagination: PaginationDep) -> PageCoursHistorique:
    """Route 28 : qui a saisi chaque cours, quand, et sa variation."""
    lignes, total, dernier = devises.cours_successifs(
        s, code, _apres(pagination), pagination.limite
    )
    return PageCoursHistorique(
        elements=[CoursHistorique.model_validate(x, from_attributes=True) for x in lignes],
        total=total,
        suivant=encoder_curseur([dernier]) if dernier is not None else None,
    )


@routeur.post(
    "/devises",
    response_model=DeviseFiche,
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Ajouter une devise et son premier cours.",
    responses=reponses(401, 403, 409, 422),
)
def creer_devise(corps: DeviseCreation, qui: QuiDep, s: SessionDep) -> DeviseFiche:
    """Route 29."""
    return _devise(devises.creer(s, qui, corps.code, corps.nom, corps.cours), set())


@routeur.put(
    "/devises/{code}",
    response_model=DeviseFiche,
    dependencies=[droit(D, A)],
    summary="Changer le nom, le cours ou la mise en service d'une devise.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_devise(
    code: str, corps: DeviseModification, qui: QuiDep, s: SessionDep
) -> DeviseFiche:
    """Route 30 : un cours n'est historisé que s'il change ; un mois clos ne bouge pas."""
    d = devises.modifier(
        s, qui, code, nom=corps.nom, cours=corps.cours, actif=corps.actif, version=corps.version
    )
    return _devise(d, devises.lister(s)[1])


from gestion_mp_pro.api.reglages import routes_referentiels  # noqa: E402, F401  — routes 31–42
