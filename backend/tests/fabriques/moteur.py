"""Une petite usine en base PRO, écrite par les fabriques et le seul chemin du stock (lot S4) :
ce que le chargeur du moteur doit relire exactement (`test_donnees_moteur.py`).

Tout y est : réglages, classification, deux fournisseurs, trois matières (dont un cuir compté
au mètre), deux qualités (dont une arrêtée), plan versionné, recettes versionnées, bons
(parti, brouillon, soldé à la main, annulé), réceptions (validée avec une réserve et un refus,
brouillon), retour au fournisseur, ouverture, ordre au prévu figé et son retour, libération de
quarantaine, ajustement annulé, dossier d'importation (et un dossier annulé), métier monté.
"""

from __future__ import annotations

from fabriques.moteur_base import Monde
from fabriques.moteur_flux import dossiers, flux, metiers, receptions
from fabriques.moteur_referentiels import commandes, qualites, referentiels
from fabriques.stock import vider
from sqlalchemy.orm import Session

__all__ = ["Monde", "batir"]


def batir(s: Session) -> Monde:
    """La petite usine, dans une base vidée de son activité (transaction de l'essai)."""
    vider(s)
    w = Monde()
    for partie in (referentiels, qualites, commandes, receptions, flux, dossiers, metiers):
        partie(s, w)
    s.flush()
    return w
