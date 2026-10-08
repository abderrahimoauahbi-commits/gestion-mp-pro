"""Seuil, couverture et statut d'une matière (CALCULS A § 3.10, finitions).

Portage du bloc « stock min recalculé, couverture, statuts » de `moteur.etat_stock`
(méthode corrigée) : le seuil se compare au stock projeté (demande du délai déjà retirée) ;
le stock minimum du catalogue est plafonné à quelques mois de la consommation qui vient ;
une matière sans consommation n'a pas de seuil.
"""

from __future__ import annotations

from gestion_mp_pro.calcul.constantes import (
    JOURS_PAR_MOIS,
    POUSSIERE,
    SEUIL_ATTENTION,
    SEUIL_CRITIQUE,
    STATUTS,
)
from gestion_mp_pro.calcul.modele import Article, Parametres
from gestion_mp_pro.calcul.stock.ligne import LigneStock


def seuils(ligne: LigneStock, article: Article, jours: float, parametres: Parametres) -> None:
    """Le stock minimum plafonné et le seuil recalculé (le plus protecteur de trois)."""
    conso = ligne.conso_mensuelle
    couv_min = article.couv_min_mois or 0
    saison = ligne.conso_horizon
    plafond = parametres.plafond_stock_min_mois
    if conso <= 0:
        ligne.stock_min_plafonne = 0.0
    else:
        ligne.stock_min_plafonne = (
            min(ligne.stock_min, plafond * saison) if plafond > 0 else ligne.stock_min
        )
    ligne.stock_min_recalcule = max(
        ligne.stock_min_plafonne,
        couv_min * saison * (1 + parametres.marge_securite),
        saison * jours / JOURS_PAR_MOIS,
    )
    if conso:
        ligne.couverture_jours = ligne.stock_projete / (conso / JOURS_PAR_MOIS)


def statut_couverture(ligne: LigneStock, parametres: Parametres) -> str:
    """Le statut du classeur (`Stock!J10`) : couverture contre 60 et 90 jours, pour mémoire."""
    conso = ligne.conso_mensuelle
    if ligne.stock_projete <= 0 and conso == 0:
        return STATUTS["OK"]
    if ligne.stock_projete <= 0:
        return STATUTS["RUPTURE"]
    if conso == 0 or ligne.couverture_jours is None:
        return STATUTS["OK"]
    if ligne.couverture_jours < parametres.seuil_critique:
        return STATUTS["CRITIQUE"]
    if ligne.couverture_jours < parametres.seuil_alerte:
        return STATUTS["ATTENTION"]
    return STATUTS["OK"]


def _par_seuil(stock_projete: float, seuil: float) -> str:
    if seuil <= 0:
        return STATUTS["OK"]
    if stock_projete <= seuil * SEUIL_CRITIQUE:
        return STATUTS["CRITIQUE"]
    if stock_projete <= seuil:
        return STATUTS["URGENT"]
    if stock_projete <= seuil * SEUIL_ATTENTION:
        return STATUTS["ATTENTION"]
    return STATUTS["OK"]


def statut(ligne: LigneStock) -> str:
    """Le statut appliqué : le stock projeté face au seuil recalculé (Notice § 6) ; rien
    demandé d'ici l'horizon n'est pas une rupture."""
    if ligne.conso_mensuelle == 0:
        return STATUTS["SANS_CONSO"]
    if ligne.stock_min_recalcule <= 0 and ligne.stock_projete > -POUSSIERE:
        return STATUTS["OK"]
    if ligne.stock_projete <= 0:
        return STATUTS["RUPTURE"]
    return _par_seuil(ligne.stock_projete, ligne.stock_min_recalcule)


def appliquer_statuts(
    ligne: LigneStock, article: Article, jours: float, parametres: Parametres
) -> None:
    """Seuils, couverture, statuts et couverture cible (le seuil dit en jours)."""
    seuils(ligne, article, jours, parametres)
    ligne.statut_couverture = statut_couverture(ligne, parametres)
    ligne.statut = statut(ligne)
    conso = ligne.conso_mensuelle
    ligne.couverture_cible_jours = (
        ligne.stock_min_recalcule / (conso / JOURS_PAR_MOIS) if conso else 0.0
    )
