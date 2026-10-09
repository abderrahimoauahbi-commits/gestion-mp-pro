"""Routes du domaine « Commandes » (API-PRO § 1.18 : routes 152–166).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service. Chaque geste rend la
fiche relue (`commandes_fiche.fiche`). L'approbation et le renvoi sont à la direction seule ;
tout le reste à la direction et aux achats ; l'alimentation n'a aucune de ces routes. Le
document imprimable (164) et les classeurs (165, 166) sont dans `routes_documents.py`.
"""

from __future__ import annotations

from dataclasses import asdict

from gestion_mp_pro.api.commandes import routes_documents  # noqa: F401 — routes 164–166
from gestion_mp_pro.api.commandes.routeur import FiltresDep, routeur
from gestion_mp_pro.api.commandes.schemas import (
    CommandeCreation,
    CommandeFiche,
    CommandeModification,
    CommandeResume,
    ConfirmationPrix,
    Envoi,
    ExpeditionEntree,
    LigneCommandeEntree,
    Renvoi,
    Solde,
)
from gestion_mp_pro.api.communs import ValidationVersion
from gestion_mp_pro.api.dependances import SessionDep, VersionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.securite import A, D, QuiDep, droit
from gestion_mp_pro.services import approbation, commandes, commandes_suivi, contexte
from gestion_mp_pro.services.commandes_fiche import fiche, liste
from gestion_mp_pro.services.commandes_saisie import LigneSaisie

__all__ = ["routeur"]

contexte.COMPTEURS["a_approuver"] = approbation.a_approuver
"""La pastille « Commandes » du menu de la direction (bons à approuver)."""

GESTE = reponses(401, 403, 404, 409, 422)


def _fiche(qui: QuiDep, s: SessionDep, cid: int) -> CommandeFiche:
    """La fiche relue après un geste."""
    return CommandeFiche.model_validate(asdict(fiche(s, cid, qui.role)))


def _lignes(lignes: list[LigneCommandeEntree]) -> list[LigneSaisie]:
    """Les lignes saisies, pour le service."""
    return [
        LigneSaisie(x.matiere_id, x.quantite, x.unite_achat, x.contenance, x.prix) for x in lignes
    ]


@routeur.get(
    "/commandes",
    response_model=list[CommandeResume],
    dependencies=[droit(D, A)],
    summary="Les bons de commande, du plus récent au plus ancien, filtrés au serveur.",
    responses=reponses(401, 403, 422),
)
def lister(f: FiltresDep, s: SessionDep) -> list[CommandeResume]:
    """Route 152."""
    return [CommandeResume.model_validate(asdict(r)) for r in liste(s, f)]


@routeur.get(
    "/commandes/{cid}",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="La fiche d'un bon : lignes, reçu, version partie, décisions, gestes permis.",
    responses=reponses(401, 403, 404),
)
def lire(cid: int, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 153."""
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes",
    response_model=list[CommandeFiche],
    status_code=201,
    dependencies=[droit(D, A)],
    summary="Créer les bons en brouillon chez un fournisseur, un par devise, sans numéro.",
    responses=reponses(401, 403, 409, 422),
)
def creer(corps: CommandeCreation, qui: QuiDep, s: SessionDep) -> list[CommandeFiche]:
    """Route 154."""
    e = commandes.Creation(
        corps.fournisseur_id,
        _lignes(corps.lignes),
        corps.date_livraison_prevue,
        corps.prix_catalogue_a_confirmer,
        corps.observations,
    )
    return [_fiche(qui, s, bon.commande.id) for bon in commandes.creer(s, qui, e)]


@routeur.put(
    "/commandes/{cid}",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Modifier un bon tant que rien n'est reçu (puis le garde-fou de l'approbation).",
    responses=GESTE,
)
def modifier(cid: int, corps: CommandeModification, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 155."""
    e = commandes.Modification(
        corps.version,
        _lignes(corps.lignes),
        corps.observations,
        corps.date_livraison_prevue,
        "date_livraison_prevue" in corps.model_fields_set,
    )
    commandes.modifier(s, qui, cid, e)
    return _fiche(qui, s, cid)


@routeur.delete(
    "/commandes/{cid}",
    status_code=204,
    dependencies=[droit(D, A)],
    summary="Supprimer un brouillon jamais parti et sans réception.",
    responses=GESTE,
)
def supprimer(cid: int, version: VersionDep, qui: QuiDep, s: SessionDep) -> None:
    """Route 156."""
    commandes.supprimer(s, qui, cid, version)


@routeur.post(
    "/commandes/{cid}/envoyer",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Envoyer le bon (numéro et date d'envoi) ou, au-delà du seuil, le soumettre.",
    responses=GESTE,
)
def envoyer(cid: int, corps: Envoi, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 157."""
    commandes.envoyer(s, qui, cid, corps.version, corps.date)
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes/{cid}/approuver",
    response_model=CommandeFiche,
    dependencies=[droit(D)],
    summary="Approuver un bon au montant estimé : il part, daté du jour réel d'envoi.",
    responses=GESTE,
)
def approuver(cid: int, corps: Envoi, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 158."""
    approbation.approuver(s, qui, cid, corps.version, corps.date)
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes/{cid}/renvoyer",
    response_model=CommandeFiche,
    dependencies=[droit(D)],
    summary="Renvoyer un bon aux achats avec un motif (parti : retour à sa version partie).",
    responses=GESTE,
)
def renvoyer(cid: int, corps: Renvoi, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 159."""
    approbation.renvoyer(s, qui, cid, corps.version, corps.motif)
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes/{cid}/prix",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Confirmer les prix du fournisseur (le cours et la date promise se figent).",
    responses=GESTE,
)
def confirmer_prix(cid: int, corps: ConfirmationPrix, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 160."""
    e = commandes.Confirmation(
        corps.version,
        [commandes.PrixConfirme(x.ligne_id, x.prix, x.unite) for x in corps.lignes],
        corps.mettre_a_jour_catalogue,
        corps.date_livraison_prevue,
    )
    commandes.confirmer_prix(s, qui, cid, e)
    return _fiche(qui, s, cid)


@routeur.put(
    "/commandes/{cid}/expedition",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Les jalons de l'expédition (champ absent : inchangé ; null : effacé).",
    responses=GESTE,
)
def expedition(cid: int, corps: ExpeditionEntree, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 161."""
    valeurs = corps.model_dump(include=corps.model_fields_set - {"version"})
    commandes_suivi.suivre_expedition(
        s, qui, cid, commandes_suivi.Expedition(corps.version, valeurs)
    )
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes/{cid}/solder",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Solder (un camion est venu) ou annuler (rien reçu) : on n'attend plus le reste.",
    responses=GESTE,
)
def solder(cid: int, corps: Solde, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 162."""
    commandes_suivi.solder(s, qui, cid, corps.version, corps.motif)
    return _fiche(qui, s, cid)


@routeur.post(
    "/commandes/{cid}/rouvrir",
    response_model=CommandeFiche,
    dependencies=[droit(D, A)],
    summary="Rouvrir un bon soldé ou annulé (parti : il repasse par le garde-fou).",
    responses=GESTE,
)
def rouvrir(cid: int, corps: ValidationVersion, qui: QuiDep, s: SessionDep) -> CommandeFiche:
    """Route 163."""
    commandes_suivi.rouvrir(s, qui, cid, corps.version)
    return _fiche(qui, s, cid)
