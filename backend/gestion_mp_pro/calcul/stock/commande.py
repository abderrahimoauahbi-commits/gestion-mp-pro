"""Ce qu'il faut commander, le sourcing et la dormance d'une matière (`Stock!K10`, `Y10`, `AC10`).

Portage du bloc « quantité à commander », « sourcing », « dormance » de `moteur.etat_stock`
(méthode corrigée) : on commande de quoi passer la couverture **et** rester au-dessus du
seuil, net de ce qui arrive dans la couverture et de ce qui est déjà en préparation ; on
respecte le minimum de commande puis on arrondit au conditionnement.
"""

from __future__ import annotations

from datetime import date

from gestion_mp_pro.calcul.constantes import (
    ACTION_AUCUNE,
    ACTION_CREER_BC,
    HORS_CATALOGUE,
    MONO_SOURCE,
    POUSSIERE,
)
from gestion_mp_pro.calcul.modele import Article, Donnees
from gestion_mp_pro.calcul.outils import palettes
from gestion_mp_pro.calcul.stock.journal import Agregat
from gestion_mp_pro.calcul.stock.ligne import LigneStock


def _sans_achat(donnees: Donnees, ligne: LigneStock, article: Article) -> str:
    """Pourquoi rien n'est proposé : matière ou fournisseur désactivé, non consommée."""
    fournisseur = donnees.fournisseur(ligne.fournisseur)
    if not article.actif:
        return "matière désactivée"
    if fournisseur is not None and not fournisseur.actif:
        return "fournisseur désactivé"
    if ligne.conso_mensuelle <= 0:
        return "non consommée : ni dans une recette du plan, ni sortie"
    return ""


def besoin_net(donnees: Donnees, ligne: LigneStock, article: Article, jours: float) -> float:
    """La quantité théorique : couverture + max(sécurité, seuil) − projeté − déjà attendu dans
    la couverture − déjà en préparation ; zéro sans achat ou sous le gramme."""
    couverture = donnees.couverture_commande(ligne.fournisseur)
    securite = jours * ligne.sorties_prevues / couverture if couverture else 0.0
    besoin = max(
        0.0,
        ligne.sorties_prevues
        + max(securite, ligne.stock_min_recalcule)
        - ligne.stock_projete
        - ligne.bc_dans_couverture,
    )
    besoin = max(0.0, besoin - ligne.bc_en_preparation)
    ligne.sans_achat = _sans_achat(donnees, ligne, article)
    if ligne.sans_achat or besoin < POUSSIERE:
        besoin = 0.0
    return besoin


def quantite_a_commander(
    donnees: Donnees, ligne: LigneStock, article: Article, jours: float
) -> None:
    """Quantité théorique, puis arrondie au conditionnement, en unités, dans l'unité d'achat,
    en montant ; l'action proposée."""
    besoin = besoin_net(donnees, ligne, article, jours)
    ligne.quantite_theorique = besoin
    contenance_palette = article.contenance_palette
    ligne.unite_commande, ligne.contenance_commande = article.conditionnement
    if besoin <= 0:
        ligne.quantite_a_commander = besoin
        ligne.palettes_a_commander = palettes(besoin, contenance_palette) if besoin else 0
    else:
        quantite = max(besoin, article.minimum_commande or 0.0)
        contenance = ligne.contenance_commande
        if contenance > 1:
            # Le nombre d'unités fait foi, la quantité en découle (6 036,8 / 862,4 = 7).
            quantite = palettes(quantite, contenance) * contenance
        ligne.quantite_a_commander = quantite
        ligne.palettes_a_commander = (
            palettes(quantite, contenance_palette) if contenance_palette else 0
        )
    ligne.unites_a_commander = (
        ligne.quantite_a_commander / ligne.contenance_commande if ligne.contenance_commande else 0.0
    )
    ligne.quantite_a_commander_achat = (
        ligne.quantite_a_commander / article.densite
        if ligne.unite_achat == "ml" and article.densite
        else ligne.quantite_a_commander
    )
    ligne.montant_a_commander = ligne.quantite_a_commander * ligne.prix_kg
    ligne.montant_a_commander_mad = ligne.montant_a_commander * donnees.parametres.taux(
        ligne.devise
    )
    ligne.action = ACTION_CREER_BC if ligne.quantite_a_commander > 0 else ACTION_AUCUNE


def sourcing(ligne: LigneStock, fournisseurs_du_groupe: dict[str, set[str]]) -> None:
    """Mono ou multi-source selon les fournisseurs du groupe d'équivalence."""
    fournisseurs = fournisseurs_du_groupe.get(ligne.groupe_equiv, set())
    ligne.nb_fournisseurs_groupe = len(fournisseurs)
    if not ligne.groupe_equiv:
        ligne.sourcing = HORS_CATALOGUE
    elif len(fournisseurs) <= 1:
        ligne.sourcing = MONO_SOURCE
    else:
        ligne.sourcing = f"✅ Multi-source ({len(fournisseurs)})"


def dormance(
    ligne: LigneStock, agregat: Agregat | None, date_ref: date, seuil_dormant: float
) -> None:
    """Dort ce qui est en magasin et n'a ni servi ni été reçu depuis le seuil."""
    dates = [
        x for x in (ligne.date_derniere_sortie, agregat.derniere_entree if agregat else None) if x
    ]
    dernier = max(dates) if dates else None
    ligne.jours_sans_mouvement = (date_ref - dernier).days if dernier else None
    ligne.dormant = ligne.stock_net > POUSSIERE and (
        dernier is None
        or (ligne.jours_sans_mouvement is not None and ligne.jours_sans_mouvement > seuil_dormant)
    )
