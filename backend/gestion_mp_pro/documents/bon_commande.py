"""Le bon de commande fournisseur en HTML A4 (route 164), sur le papier à en-tête de l'usine en
anglais (`rendu.rendre(..., langue="en")` : « HEAD OFFICE », « BANKS »), sans aucun prix,
montant ni devise. Le contenu vient de `services/bon_fournisseur.contenu`, le même que l'Excel.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from gestion_mp_pro.documents import rendu
from gestion_mp_pro.exports import bon_fournisseur as exports_bon
from gestion_mp_pro.services import bon_fournisseur


def usine(societe: rendu.Societe) -> bon_fournisseur.Usine:
    """Où livrer, lu sur le papier à en-tête."""
    return bon_fournisseur.Usine(societe.nom, societe.adresse, societe.ville)


def html(s: Session, cid: int) -> str:
    """Le document complet (404 « Commande introuvable. »)."""
    societe = rendu.societe(s)
    bon = bon_fournisseur.contenu(s, cid, usine(societe))
    return rendu.rendre(
        "bon_commande.html",
        societe=societe,
        titre=bon.titre,
        langue="en",
        bon=bon,
        confirmation=bon_fournisseur.CONFIRMATION,
        signature_acheteur=bon_fournisseur.SIGNATURE_ACHETEUR,
        signature_fournisseur=bon_fournisseur.SIGNATURE_FOURNISSEUR,
    )


def classeur(s: Session, cid: int) -> tuple[bytes, str]:
    """Le classeur du bon (route 165) et son nom de fichier ; 404 « Bon de commande
    introuvable. », 409 sans raison sociale."""
    societe = rendu.societe(s)
    bon = bon_fournisseur.contenu(
        s, cid, usine(societe), introuvable="Bon de commande introuvable."
    )
    return exports_bon.classeur(bon, societe), bon.nom_fichier
