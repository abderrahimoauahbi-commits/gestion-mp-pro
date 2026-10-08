"""Le stock d'une matière et sa prévision : net, machine, quarantaine, attendu, projeté.

Portage de la boucle « lignes » de `moteur.etat_stock` (CALCULS A § 3.10) : la consommation
mensuelle (plan corrigé par le réel), la demande pendant le délai et pendant la couverture
d'une commande, les bons attendus à temps, hors horizon ou dans la couverture, le stock
projeté à la fin du délai.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gestion_mp_pro.calcul.besoins import besoin_sur_fenetre
from gestion_mp_pro.calcul.constantes import JOURS_PAR_MOIS, MOIS
from gestion_mp_pro.calcul.modele import Article, Donnees
from gestion_mp_pro.calcul.outils import fin_de_mois, jour_plus, mois_ecoules
from gestion_mp_pro.calcul.stock.journal import Agregat, Attendu, stock_net_de
from gestion_mp_pro.calcul.stock.ligne import LigneStock
from gestion_mp_pro.calcul.stock.realisation import Realisation


@dataclass
class Contexte:
    """Ce que toutes les lignes partagent."""

    donnees: Donnees
    date_ref: date
    besoins: dict[str, list[float]]
    agregats: dict[str, Agregat]
    monte: dict[str, float]
    magasins: list[str]
    quarantaines: list[str]
    en_commande: dict[str, list[Attendu]]
    en_preparation: dict[str, list[tuple[float, str]]]
    realisations: dict[str, Realisation]
    heritages: dict[str, list[str]]
    fenetre: bool

    @property
    def jours_du_mois(self) -> float:
        """La vraie longueur du mois en cours (D-14)."""
        return float(fin_de_mois(self.date_ref).day)

    @property
    def jours_restants(self) -> float:
        """Les jours qui restent au mois en cours."""
        return self.jours_du_mois - self.date_ref.day


def _demande(ctx: Contexte, besoin: list[float], debut: float, fin: float) -> float:
    return besoin_sur_fenetre(
        besoin, debut, fin, ctx.jours_restants, jours_du_mois=ctx.jours_du_mois, prolonger=True
    )


def _besoin_et_conso(ctx: Contexte, article: Article) -> tuple[list[float], float]:
    """Le besoin des douze mois (corrigé par la réalisation) et la consommation mensuelle :
    le plan fait la prévision ; un fil hors de tout plan garde son historique (D-14 d)."""
    besoin = ctx.besoins.get(article.reference, [0.0] * MOIS)
    coefficient, conso_reelle, hors_recette = ctx.realisations.get(
        article.reference, (None, None, False)
    )
    if coefficient is not None:
        besoin = [valeur * coefficient for valeur in besoin]
    elif hors_recette:
        besoin = [conso_reelle or 0.0] * MOIS
    besoin_annuel = sum(besoin)
    if ctx.fenetre or besoin_annuel > 0:
        return besoin, besoin_annuel / MOIS
    agregat = ctx.agregats.get(article.reference)
    conso_historique = 0.0
    if agregat and agregat.premiere_sortie is not None:
        mois_hist = mois_ecoules(agregat.premiere_sortie, ctx.date_ref)
        conso_historique = abs(agregat.sorties) / mois_hist
    return besoin, max(conso_historique, besoin_annuel / MOIS)


def _attendus(
    ctx: Contexte, reference: str, delai: float, couverture: float
) -> tuple[float, float, float]:
    """(à temps pour le délai, après le délai, dans la couverture d'une commande) ; sans date
    annoncée, on fait confiance. Un délai de 4,5 jours livre le cinquième jour."""
    attendu = ctx.en_commande.get(reference, [])
    limite = jour_plus(ctx.date_ref, delai)
    fin_couverture = jour_plus(ctx.date_ref, delai + couverture)
    a_temps = sum(reste for reste, jour in attendu if jour is None or jour <= limite)
    hors_horizon = sum(reste for reste, jour in attendu if jour is not None and jour > limite)
    dans_couverture = sum(
        reste for reste, jour in attendu if jour is not None and limite < jour <= fin_couverture
    )
    return a_temps, hors_horizon, dans_couverture


def _decrire(ligne: LigneStock, article: Article) -> None:
    """La classification et le prix tels que le catalogue les dit."""
    ligne.composition = article.composition
    ligne.type_fil = article.type_fil
    ligne.couleur = article.couleur
    ligne.titrage = str(article.titrage or "")
    ligne.titrage_unite = article.titrage_unite
    ligne.unite_achat = article.unite_prix
    ligne.prix_unite = article.prix_unite
    ligne.kg_par_ml = article.kg_par_ml
    ligne.groupe_equiv = article.groupe_equiv


def ligne_de_stock(ctx: Contexte, article: Article) -> LigneStock:
    """La ligne d'une matière avant classement (ABC) et finitions (statut, achat)."""
    donnees, ref = ctx.donnees, article.reference
    agregat = ctx.agregats.get(ref)
    stock_net = stock_net_de(agregat)
    besoin, conso = _besoin_et_conso(ctx, article)
    delai = donnees.delai_fournisseur(article.fournisseur)
    couverture = donnees.couverture_commande(article.fournisseur)
    demande_delai = _demande(ctx, besoin, 0, delai)
    a_temps, hors_horizon, dans_couverture = _attendus(ctx, ref, delai, couverture)
    machine = ctx.monte.get(ref, 0.0)
    bloque = agregat.en_magasins(ctx.quarantaines) if agregat else 0.0
    horizon = delai + couverture + JOURS_PAR_MOIS
    devise = donnees.devise_article(article)
    valeur_conso = conso * MOIS * article.prix_kg
    coefficient, conso_reelle, _ = ctx.realisations.get(ref, (None, None, False))
    ligne = LigneStock(
        reference=ref,
        nature=article.nature,
        designation=article.designation,
        fournisseur=article.fournisseur,
        stock_initial=agregat.stock_initial if agregat else 0.0,
        entrees=agregat.entrees if agregat else 0.0,
        stock_net=stock_net,
        stock_machine=machine,
        stock_disponible=stock_net - bloque + machine,
        stock_quarantaine=bloque,
        bc_en_cours=a_temps,
        bc_hors_horizon=hors_horizon,
        bc_dans_couverture=dans_couverture,
        sorties_prevues=_demande(ctx, besoin, delai, delai + couverture),
        demande_delai=demande_delai,
        stock_projete=stock_net - bloque + machine + a_temps - demande_delai,
        stock_min=article.stock_min,
        conso_mensuelle=conso,
        besoin_annuel=sum(besoin),
        conso_plan=sum(ctx.besoins.get(ref, [0.0] * MOIS)) / MOIS,
        conso_reelle=conso_reelle,
        coefficient_realisation=coefficient,
        conso_horizon=_demande(ctx, besoin, 0, horizon) / horizon * JOURS_PAR_MOIS,
        delai_jours=delai,
        prix_kg=article.prix_kg,
        devise=devise,
        valeur_conso_annuelle=valeur_conso,
        valeur_conso_annuelle_mad=valeur_conso * donnees.parametres.taux(devise),
        besoins=besoin,
        date_derniere_sortie=agregat.derniere_sortie if agregat else None,
        par_magasin={m: (agregat.magasins.get(m, 0.0) if agregat else 0.0) for m in ctx.magasins},
    )
    _decrire(ligne, article)
    preparation = ctx.en_preparation.get(ref, [])
    ligne.realisation_heritee = ctx.heritages.get(ref, [])
    ligne.bc_en_preparation = sum(q for q, _ in preparation)
    ligne.bons_en_preparation = sorted({n for _, n in preparation})
    return ligne
