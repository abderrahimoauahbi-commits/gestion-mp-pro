"""Ce que l'état d'un bon permet : une règle par geste, qui rend la raison du refus (code et
phrase de REGLES § 2.17, mot pour mot) ou `None`.

Une seule source pour deux usages : le service refuse le geste avec cette raison (409), et la
fiche dit d'avance, geste par geste, ce qui est permis et pourquoi pas (`actions` de la route
153, ECRANS-PRO § 4.7 : « refus annoncés avant le clic »). La table de transitions des essais
rejoue chaque geste sur chaque état et vérifie que les deux disent la même chose.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import CommandeVersion
from gestion_mp_pro.modeles.enums import Role, StatutCommande
from gestion_mp_pro.services.commandes_socle import CLOS, Bon, a_des_receptions, nom_commande

Raison = tuple[str, str]
"""(code de refus, phrase)."""

GESTES = (
    "modifier",
    "supprimer",
    "envoyer",
    "approuver",
    "renvoyer",
    "prix",
    "expedition",
    "solder",
    "rouvrir",
    "imprimer",
)
"""Les dix gestes d'un bon (la table de transitions des essais les rejoue tous)."""

DIRECTION_SEULE = frozenset({"approuver", "renvoyer"})
RESERVE_DIRECTION = "Cette action est réservée à : la direction."


@dataclass(frozen=True)
class EtatBon:
    """Ce dont les règles ont besoin : statut, numéro, réceptions, version partie connue."""

    statut: StatutCommande
    numero: str | None
    nom: str
    receptions: bool
    version_connue: bool


def etat(s: Session, bon: Bon) -> EtatBon:
    """L'état d'un bon chargé (deux petites requêtes)."""
    c = bon.commande
    connue = s.scalar(
        select(CommandeVersion.id).where(CommandeVersion.commande_id == c.id).limit(1)
    )
    return EtatBon(c.statut, c.numero, nom_commande(c), a_des_receptions(s, c), connue is not None)


def _modifier(e: EtatBon) -> Raison | None:
    if e.statut in CLOS:
        return "bon_clos", "Ce bon est clos."
    if e.receptions:
        return (
            "documents_lies",
            "Ce bon a déjà des réceptions : ses lignes ne se modifient plus. "
            "Créer un autre bon pour le complément, ou le solder.",
        )
    return None


def _supprimer(e: EtatBon) -> Raison | None:
    if e.receptions:
        return "documents_lies", "Ce bon a des réceptions : le solder plutôt que le supprimer."
    if e.numero:
        return (
            "etat_incompatible",
            f"Le bon {e.numero} est parti chez le fournisseur : l'annuler plutôt que le "
            "supprimer (il garde son numéro, la série reste sans trou).",
        )
    return None


def _envoyer(e: EtatBon) -> Raison | None:
    if e.statut == StatutCommande.a_approuver:
        return "etat_incompatible", "Ce bon attend l'approbation de la direction."
    if e.statut != StatutCommande.brouillon:
        return "etat_incompatible", "Ce bon est déjà parti."
    return None


def _approuver(e: EtatBon) -> Raison | None:
    if e.statut != StatutCommande.a_approuver:
        return "etat_incompatible", "Ce bon n'attend pas d'approbation."
    return None


def _renvoyer(e: EtatBon) -> Raison | None:
    if e.statut != StatutCommande.a_approuver:
        return "etat_incompatible", "Seul un bon qui attend l'approbation se renvoie aux achats."
    if e.numero and not e.version_connue:
        return (
            "etat_incompatible",
            f"Le bon {e.numero} est parti, mais sa version d'alors n'est pas connue : "
            "l'approuver, ou demander aux achats de le ramener à ce qui était accepté.",
        )
    return None


def _prix(e: EtatBon) -> Raison | None:
    if e.statut == StatutCommande.annulee:
        return "bon_clos", "Ce bon est annulé."
    if not e.numero:
        return (
            "etat_incompatible",
            f"Le {e.nom} n'est pas encore parti : le fournisseur n'a pas pu confirmer ses "
            "prix. L'envoyer d'abord (il reçoit son numéro), puis saisir les prix qu'il annonce.",
        )
    if e.statut == StatutCommande.soldee:
        return (
            "bon_clos",
            f"Le bon {e.numero} est soldé : ses prix ne se confirment plus. Le rouvrir d'abord.",
        )
    return None


def _expedition(e: EtatBon) -> Raison | None:
    if not e.numero:
        return (
            "etat_incompatible",
            "Ce bon n'est pas encore parti : son expédition se suit après l'envoi.",
        )
    if e.statut in CLOS:
        quoi = "annulé" if e.statut == StatutCommande.annulee else "soldé"
        return "bon_clos", f"Le bon {e.numero} est {quoi} : son expédition ne se suit plus."
    return None


def _solder(e: EtatBon) -> Raison | None:
    if e.statut in CLOS:
        return "bon_clos", "Ce bon est déjà clos."
    if e.statut == StatutCommande.a_approuver and e.numero:
        return (
            "etat_incompatible",
            f"Le bon {e.numero} attend l'approbation de la direction : elle l'approuve ou le "
            "renvoie aux achats (il revient à sa version partie) ; il se solde ensuite.",
        )
    if not e.numero:
        return "etat_incompatible", "Ce bon n'est pas parti : il se supprime, il ne se solde pas."
    return None


def _rouvrir(e: EtatBon) -> Raison | None:
    if e.statut not in CLOS:
        return "etat_incompatible", "Ce bon n'est pas clos."
    return None


REGLES: dict[str, Callable[[EtatBon], Raison | None]] = {
    "modifier": _modifier,
    "supprimer": _supprimer,
    "envoyer": _envoyer,
    "approuver": _approuver,
    "renvoyer": _renvoyer,
    "prix": _prix,
    "expedition": _expedition,
    "solder": _solder,
    "rouvrir": _rouvrir,
    "imprimer": lambda _e: None,
}


def raison(geste: str, e: EtatBon) -> Raison | None:
    """La raison du refus de ce geste dans cet état, ou `None` s'il est permis."""
    return REGLES[geste](e)


def exiger(geste: str, e: EtatBon) -> None:
    """409 avec la raison du refus si l'état n'autorise pas le geste."""
    refus = raison(geste, e)
    if refus is not None:
        raise Refus.etat(refus[1], code=refus[0])


def permis(e: EtatBon, role: str) -> dict[str, str | None]:
    """Geste par geste : `None` s'il est permis à ce rôle dans cet état, sinon la phrase."""
    resultat: dict[str, str | None] = {}
    for geste in GESTES:
        if geste in DIRECTION_SEULE and role != Role.direction:
            resultat[geste] = RESERVE_DIRECTION
            continue
        refus = raison(geste, e)
        resultat[geste] = None if refus is None else refus[1]
    return resultat
