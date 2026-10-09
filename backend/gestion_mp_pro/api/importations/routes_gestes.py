"""Les gestes sur un dossier (routes 192–204) : second camion, marchandises, cours, frais,
clôture, réouverture, annulation. Chacun rend la fiche relue."""

from __future__ import annotations

from gestion_mp_pro.api.dependances import SessionDep, VersionDep
from gestion_mp_pro.api.importations.routeur import GESTE, fiche_relue, routeur
from gestion_mp_pro.api.importations.schemas import (
    Annulation,
    Cloture,
    CoursDevise,
    Detachement,
    FraisEntree,
    LigneManuelle,
    LigneModification,
    Rattachement,
    Reouverture,
    Version,
)
from gestion_mp_pro.api.importations.schemas_fiche import DossierFiche
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services.importations import etats, frais, marchandises, ouverture

__all__ = ["routeur"]


def _frais(corps: FraisEntree) -> frais.FraisSaisi:
    """Le frais saisi, pour le service."""
    return frais.FraisSaisi(**corps.model_dump(exclude={"version"}))


@routeur.post(
    "/dossiers/{did}/rattacher",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Ajouter au dossier le second camion de sa facture (toute sa marchandise libre).",
    responses=GESTE,
)
def rattacher(did: int, corps: Rattachement, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 192."""
    ouverture.rattacher(s, qui, did, corps.version, corps.facture_id)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/lignes",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Saisir à la main une marchandise d'un dossier d'avant la mise en service.",
    responses=GESTE,
)
def saisir(did: int, corps: LigneManuelle, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 193."""
    e = marchandises.LigneManuelle(**corps.model_dump(exclude={"version"}))
    marchandises.saisir(s, qui, did, corps.version, e)
    return fiche_relue(s, did)


@routeur.put(
    "/dossiers/{did}/lignes/{lid}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Le cours payé d'une marchandise (vide : le cours du jour) et ses observations.",
    responses=GESTE,
)
def modifier_ligne(
    did: int, lid: int, corps: LigneModification, qui: QuiDep, s: SessionDep
) -> DossierFiche:
    """Route 194 : un champ absent ne change pas."""
    e = marchandises.LigneModifiee(
        version=corps.version,
        cours_donne="cours" in corps.model_fields_set,
        cours=corps.cours,
        commentaire=corps.commentaire,
    )
    marchandises.modifier(s, qui, did, lid, e)
    return fiche_relue(s, did)


@routeur.delete(
    "/dossiers/{did}/lignes/{lid}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Retirer une marchandise saisie à la main (une reçue sort avec sa réception).",
    responses=GESTE,
)
def retirer_ligne(
    did: int, lid: int, version: VersionDep, qui: QuiDep, s: SessionDep
) -> DossierFiche:
    """Route 195."""
    marchandises.retirer(s, qui, did, lid, version)
    return fiche_relue(s, did)


@routeur.put(
    "/dossiers/{did}/cours",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Un cours payé pour toutes les marchandises d'une devise du dossier.",
    responses=GESTE,
)
def cours(did: int, corps: CoursDevise, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 196."""
    marchandises.cours_devise(s, qui, did, corps.version, devise=corps.devise, cours=corps.cours)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/cours-des-bons",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Remettre sur chaque marchandise le cours figé de son bon de commande.",
    responses=GESTE,
)
def cours_des_bons(did: int, corps: Version, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 197."""
    marchandises.cours_des_bons(s, qui, did, corps.version)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/detacher",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Détacher une réception du dossier : sa marchandise attend, les frais restent.",
    responses=GESTE,
)
def detacher(did: int, corps: Detachement, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 198."""
    marchandises.detacher(s, qui, did, corps.version, corps.reception_id)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/frais",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Ajouter un frais (droits, fret, transitaire… ; un avoir en négatif).",
    responses=GESTE,
)
def ajouter_frais(did: int, corps: FraisEntree, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 199 : `version` est celle du dossier."""
    frais.ajouter(s, qui, did, corps.version, _frais(corps))
    return fiche_relue(s, did)


@routeur.put(
    "/dossiers/{did}/frais/{fid}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Corriger un frais (un frais réglé garde son poste, son montant, sa marchandise).",
    responses=GESTE,
)
def modifier_frais(
    did: int, fid: int, corps: FraisEntree, qui: QuiDep, s: SessionDep
) -> DossierFiche:
    """Route 200 : `version` est celle du frais."""
    frais.modifier(s, qui, did, fid, version=corps.version, e=_frais(corps))
    return fiche_relue(s, did)


@routeur.delete(
    "/dossiers/{did}/frais/{fid}",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Retirer un frais non réglé.",
    responses=GESTE,
)
def retirer_frais(
    did: int, fid: int, version: VersionDep, qui: QuiDep, s: SessionDep
) -> DossierFiche:
    """Route 201 : `?version=` est celle du frais."""
    frais.retirer(s, qui, did, fid, version)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/cloturer",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Clore le dossier : son coût se fige (un cours vide prend le cours du jour).",
    responses=GESTE,
)
def cloturer(did: int, corps: Cloture, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 202."""
    etats.cloturer(s, qui, did, corps.version, corps.alertes_lues)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/rouvrir",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Rouvrir un dossier clos pour corriger (c'est tracé).",
    responses=GESTE,
)
def rouvrir(did: int, corps: Reouverture, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 203."""
    etats.rouvrir(s, qui, did, corps.version, corps.motif)
    return fiche_relue(s, did)


@routeur.post(
    "/dossiers/{did}/annuler",
    response_model=DossierFiche,
    dependencies=[droit(D, A)],
    summary="Annuler le dossier : il garde son numéro, sa facture et sa marchandise attendent.",
    responses=GESTE,
)
def annuler(did: int, corps: Annulation, qui: QuiDep, s: SessionDep) -> DossierFiche:
    """Route 204."""
    etats.annuler(s, qui, did, corps.version, corps.motif)
    return fiche_relue(s, did)
