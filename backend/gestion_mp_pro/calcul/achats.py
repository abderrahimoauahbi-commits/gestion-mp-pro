"""Ce qu'un bon de commande engage : échéance, départ, reste à livrer, montant en MAD.

Portage de `gestion_mp/calcul/modele.py` (`echeance_commande`, `pas_partie`,
`reste_a_livrer`, CALCULS § 1.11-1.12) et de `moteur.montant_ligne_mad` (partie B § 4.2).
"""

from __future__ import annotations

from datetime import date

from gestion_mp_pro.calcul.constantes import STATUTS_BC_CLOS
from gestion_mp_pro.calcul.modele import Commande, LigneCommande, Parametres


def echeance_commande(
    eta: date | None, promise: date | None, date_bc: date | None, delai_jours: float
) -> date | None:
    """Quand un bon est attendu : l'ETA, sinon la date promise, sinon la date du bon plus le
    délai du fournisseur. Une seule règle pour la liste des commandes, le courriel et C06."""
    if eta or promise:
        return eta or promise
    if date_bc is None:
        return None
    return date.fromordinal(date_bc.toordinal() + int(delai_jours or 0))


def pas_partie(commande: Commande) -> bool:
    """Un brouillon (ou un bon pas encore parti qui attend l'approbation) n'engage rien — ni
    stock attendu, ni retard, ni montant à payer."""
    return commande.statut == "Brouillon"


def reste_a_livrer(commande: Commande, ligne: LigneCommande, parametres: Parametres) -> float:
    """Ce qu'on attend encore d'une ligne : commandé − reçu accepté (la quarantaine reste
    attendue, R11r) ; rien pour un bon clos, ni sous la tolérance de livraison."""
    accepte = max(0.0, ligne.quantite_recue - max(0.0, ligne.quantite_en_quarantaine))
    reste = ligne.quantite_commandee - accepte
    if commande.statut in STATUTS_BC_CLOS:
        return 0.0
    if reste <= ligne.quantite_commandee * parametres.toler_in_full:
        return 0.0
    return reste


def montant_ligne_mad(ligne: LigneCommande, quantite: float, parametres: Parametres) -> float:
    """Une quantité d'une ligne de bon, en MAD : au prix confirmé, sinon estimé ; au cours
    figé du bon, sinon au cours du jour — le même chiffre que l'écran Commandes."""
    prix = ligne.prix_unite if ligne.prix_confirme else (ligne.prix_estime or ligne.prix_unite)
    return quantite * prix * (ligne.cours or parametres.taux(ligne.devise))
