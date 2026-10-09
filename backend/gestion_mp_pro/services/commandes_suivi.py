"""Le suivi d'un bon parti : jalons de l'expédition, solde (on n'attend plus le reste),
réouverture (REGLES § 2.11–2.13 ; `gestion_mp/api/achats.py` : `expedition`, `solder`,
`rouvrir` ; défaut A-16 corrigé : un champ absent garde sa valeur, refus sur un bon clos).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles.enums import DecisionCommande, OrigineSolde, StatutCommande
from gestion_mp_pro.services import audit, horloge
from gestion_mp_pro.services import commandes_gestes as gestes
from gestion_mp_pro.services.approbation import controler_montant, decider
from gestion_mp_pro.services.commandes_socle import (
    Bon,
    a_ete_livre,
    charger,
    journaliser,
    montant_estime,
    nom_commande,
    photo,
    statut_parti,
    taux_des_devises,
    toucher,
    verifier,
)

JALONS_CONSTATES = {
    "proforma_le": "Proforma reçue le",
    "acompte_le": "Acompte payé le",
    "embarquee_le": "Embarquée le",
    "au_port_le": "Arrivée au port le",
    "dedouanee_le": "Dédouanée le",
    "arrivee_usine_le": "Arrivée à l'usine le",
}
CHAMPS_EXPEDITION = (*JALONS_CONSTATES, "eta", "conteneur", "navire")


@dataclass(frozen=True)
class Expedition:
    """Les jalons envoyés (un champ absent garde sa valeur, `None` l'efface : A-16)."""

    version: int
    valeurs: dict[str, object] = field(default_factory=dict)


# ── Expédition, solde, réouverture ───────────────────────────────────────────


def suivre_expedition(s: Session, qui: audit.Qui, cid: int, e: Expedition) -> Bon:
    """Les jalons d'un bon parti, ni annulé ni soldé ; un jalon constaté n'est jamais futur
    ni d'avant le bon ; seuls les champs envoyés changent (R-CMD-43, A-16)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, e.version)
    gestes.exiger("expedition", gestes.etat(s, bon))
    for cle, libelle in JALONS_CONSTATES.items():
        jour = e.valeurs.get(cle)
        if isinstance(jour, date) and jour > horloge.aujourd_hui():
            raise Refus.saisie(
                f"« {libelle} » ne se date pas dans le futur : c'est un fait constaté. "
                "Une date attendue va dans l'arrivée prévue (ETA).",
                code="date_future",
            )
        if isinstance(jour, date) and jour < c.date_commande:
            raise Refus.saisie(
                f"« {libelle} » ({jour:%d/%m/%Y}) précède la date du bon "
                f"({c.date_commande:%d/%m/%Y}).",
                code="date_invalide",
            )
    avant = photo(bon)
    for cle, valeur in e.valeurs.items():
        setattr(c, cle, valeur if valeur is not None or cle in (*JALONS_CONSTATES, "eta") else "")
    toucher(c, qui)
    detail = f"{nom_commande(c)} · ETA {c.eta:%d/%m/%Y}" if c.eta else nom_commande(c)
    journaliser(s, qui, "expédition", bon, avant, detail=detail)
    return bon


def solder(s: Session, qui: audit.Qui, cid: int, version: int, motif: str = "") -> Bon:
    """On n'attend plus le reste : soldé si un camion est venu, sinon annulé ; jamais un bon
    qui attend la direction, ni un brouillon (R-CMD-44)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, version)
    gestes.exiger("solder", gestes.etat(s, bon))
    avant = photo(bon)
    livre = a_ete_livre(s, c)
    c.statut = StatutCommande.soldee if livre else StatutCommande.annulee
    c.solde_origine, c.solde_le, c.solde_par_id = OrigineSolde.manuel, horloge.maintenant(), qui.id
    toucher(c, qui)
    action = "commande soldée" if livre else "commande annulée"
    detail = nom_commande(c) + (f" · {motif.strip()}" if motif.strip() else "")
    journaliser(s, qui, action, bon, avant, detail=detail)
    return bon


def rouvrir(s: Session, qui: audit.Qui, cid: int, version: int) -> Bon:
    """Le bon attend de nouveau sa livraison ; parti, il repasse par le garde-fou : rouvert
    au-delà de ce que la direction a accepté, il retourne chez elle (R-CMD-45)."""
    bon = charger(s, cid, verrou=True)
    c = bon.commande
    verifier(s, c, version)
    gestes.exiger("rouvrir", gestes.etat(s, bon))
    avant = photo(bon)
    c.statut = statut_parti(c) if c.numero else StatutCommande.brouillon
    c.solde_origine, c.solde_le, c.solde_par_id = None, None, None
    decider(s, qui, c, DecisionCommande.rouverture)
    toucher(c, qui)
    journaliser(s, qui, "commande rouverte", bon, avant, detail=nom_commande(c))
    if c.numero:
        controler_montant(s, qui, bon, montant_estime(bon, taux_des_devises(s)), "réouverture")
    return bon
