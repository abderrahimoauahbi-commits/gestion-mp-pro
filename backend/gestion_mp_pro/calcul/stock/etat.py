"""`etat_stock` : `Tbl_Stock` en entier, une ligne par matière du catalogue (CALCULS A § 3.10).

Assemble les étapes de `moteur.etat_stock` de Gestion MP, dans le même ordre : besoins,
fenêtre de réalisation, agrégats du journal et des commandes, réalisation, lignes, classe ABC,
finitions (seuil, statut, quantité, sourcing, dormance, XYZ), substituts des ruptures.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from gestion_mp_pro.calcul.besoins import besoins_mensuels
from gestion_mp_pro.calcul.constantes import QUARANTAINE, STATUTS
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.stock.classes import classer_abc, classer_xyz, jours_securite
from gestion_mp_pro.calcul.stock.commande import dormance, quantite_a_commander, sourcing
from gestion_mp_pro.calcul.stock.journal import agreger_journal, commandes_en_cours
from gestion_mp_pro.calcul.stock.ligne import LigneStock
from gestion_mp_pro.calcul.stock.machine import stock_en_machine
from gestion_mp_pro.calcul.stock.projete import Contexte, ligne_de_stock
from gestion_mp_pro.calcul.stock.realisation import (
    Lecture,
    fenetre_de_realisation,
    realisations,
)
from gestion_mp_pro.calcul.stock.statuts import appliquer_statuts


def _contexte(donnees: Donnees, date_ref: date) -> Contexte:
    besoins = besoins_mensuels(donnees, date_ref)
    # La quarantaine est en stock et valorisée, mais pas disponible (ni sortie, ni prévision).
    quarantaines = sorted({m.code for m in donnees.magasins if m.type == QUARANTAINE})
    # Deux stocks : les magasins et les machines (le fil monté, pas encore tissé — U8).
    monte = stock_en_machine(donnees)
    fenetre = fenetre_de_realisation(donnees, date_ref)
    agregats = agreger_journal(donnees, date_ref, fenetre.rangs)
    en_commande, en_preparation = commandes_en_cours(donnees)
    reels, heritages = (
        realisations(Lecture(donnees, fenetre, agregats, besoins, monte, quarantaines), date_ref)
        if fenetre.mois
        else ({}, {})
    )
    return Contexte(
        donnees=donnees,
        date_ref=date_ref,
        besoins=besoins,
        agregats=agregats,
        monte=monte,
        magasins=[m.code for m in donnees.magasins if m.actif],
        quarantaines=quarantaines,
        en_commande=en_commande,
        en_preparation=en_preparation,
        realisations=reels,
        heritages=heritages,
        fenetre=bool(fenetre.mois),
    )


def _finir(ctx: Contexte, lignes: list[LigneStock]) -> None:
    donnees = ctx.donnees
    parametres = donnees.parametres
    groupes: dict[str, set[str]] = defaultdict(set)
    for article in donnees.articles:
        if article.groupe_equiv:
            groupes[article.groupe_equiv].add(article.fournisseur)
    for ligne in lignes:
        fiche = donnees.article(ligne.reference)
        if fiche is None:  # une ligne vient toujours d'une matière du catalogue
            continue
        jours = jours_securite(ligne.classe_abc, parametres)
        appliquer_statuts(ligne, fiche, jours, parametres)
        quantite_a_commander(donnees, ligne, fiche, jours)
        sourcing(ligne, groupes)
        agregat = ctx.agregats.get(ligne.reference)
        dormance(ligne, agregat, ctx.date_ref, parametres.seuil_dormant)
        classer_xyz(ligne, agregat, parametres)


def _substituts(lignes: list[LigneStock]) -> None:
    """Les substituts disponibles (même groupe, stock projeté positif) d'une rupture."""
    par_groupe: dict[str, list[LigneStock]] = defaultdict(list)
    for ligne in lignes:
        if ligne.groupe_equiv:
            par_groupe[ligne.groupe_equiv].append(ligne)
    for ligne in lignes:
        if ligne.statut != STATUTS["RUPTURE"] or not ligne.groupe_equiv:
            continue
        ligne.substituts = [
            autre.reference
            for autre in par_groupe[ligne.groupe_equiv]
            if autre.reference != ligne.reference and autre.stock_projete > 0
        ]


def etat_stock(donnees: Donnees, date_ref: date) -> list[LigneStock]:
    """Une ligne par matière du catalogue (pas de lignes vides, à la différence du classeur)."""
    ctx = _contexte(donnees, date_ref)
    lignes = [ligne_de_stock(ctx, article) for article in donnees.articles]
    classer_abc(lignes, donnees.parametres)
    _finir(ctx, lignes)
    _substituts(lignes)
    return lignes
