"""Contrôles du stock et du journal : auteurs, soldes, dates, intégrité, dormants, négatifs,
lots (C04, C12, C14, C16, C18, C20, C26, C27, C37)."""

from __future__ import annotations

from datetime import date

from gestion_mp_pro.calcul.constantes import POUSSIERE
from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.controles.textes import (
    GARANTI_C04,
    GARANTI_C14,
    GARANTI_C16,
    GARANTI_C26,
)
from gestion_mp_pro.calcul.lots import stock_par_lot
from gestion_mp_pro.calcul.modele import Donnees, Mouvement

ECART_MAGASINS = 0.01
"""C12 sans soldes connus : l'écart toléré entre la somme des magasins et le stock net (kg)."""

_REFERENCE = colonne("reference", "texte")
_DATE = colonne("date", "date")


def flux_par_magasin(m: Mouvement) -> list[tuple[str, float]]:
    """Ce qu'une écriture fait à chaque magasin : un transfert sort de la source et entre à la
    destination ; une autre écriture touche un seul magasin, avec son signe."""
    if m.type == "TRANSFERT_MAGASIN":
        return [(m.magasin_destination, m.quantite), (m.magasin_source, -m.quantite)]
    return [(m.magasin_destination or m.magasin_source, m.quantite_signee)]


@controle(
    "C04",
    gravite="avertissement",
    lien="/stock?onglet=mouvements",
    colonnes=(_DATE, _REFERENCE),
    garanti=GARANTI_C04,
)
def mouvement_sans_auteur(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Traçabilité : qui a écrit ce mouvement (T04)."""
    lignes: list[Ligne] = [
        {"date": m.date.isoformat(), "reference": m.reference}
        for m in ctx.donnees.mouvements
        if not m.utilisateur
    ]
    return "Mouvement de stock sans auteur", lignes


def _ecarts_aux_soldes(complet: Donnees, soldes: dict[tuple[str, str, str], float]) -> list[Ligne]:
    journal: dict[tuple[str, str, str], float] = {}
    for m in complet.mouvements:
        for magasin, quantite in flux_par_magasin(m):
            if magasin:
                cle = (m.reference, m.lot_fournisseur, magasin)
                journal[cle] = journal.get(cle, 0.0) + quantite
    return [
        {
            "reference": cle[0],
            "lot": cle[1],
            "magasin": cle[2],
            "stock": soldes.get(cle, 0.0),
            "attendu": journal.get(cle, 0.0),
        }
        for cle in sorted(set(journal) | set(soldes))
        if abs(soldes.get(cle, 0.0) - journal.get(cle, 0.0)) > POUSSIERE
    ]


@controle(
    "C12",
    gravite="bloquant",
    lien="/stock?onglet=mouvements",
    colonnes=(
        _REFERENCE,
        colonne("lot", "texte"),
        colonne("magasin", "texte"),
        colonne("stock", "kg"),
        colonne("attendu", "kg"),
        colonne("somme_magasins", "kg"),
        colonne("stock_net", "kg"),
    ),
)
def soldes_hors_journal(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le stock tenu doit retomber sur le journal, lot par lot, magasin par magasin (T15).

    Sans soldes connus (une date passée), l'ancienne règle : la somme des magasins égale le
    stock net de chaque matière.
    """
    if ctx.complet.soldes is not None:
        return (
            "Stock tenu (soldes des lots) différent du journal des mouvements",
            _ecarts_aux_soldes(ctx.complet, ctx.complet.soldes),
        )
    lignes: list[Ligne] = [
        {
            "reference": ligne.reference,
            "somme_magasins": sum(ligne.par_magasin.values()),
            "stock_net": ligne.stock_net,
        }
        for ligne in ctx.lignes_stock
        if abs(sum(ligne.par_magasin.values()) - ligne.stock_net) > ECART_MAGASINS
    ]
    return "Stock par magasin différent du stock net des mouvements", lignes


@controle(
    "C14",
    gravite="avertissement",
    lien="/stock?onglet=mouvements",
    colonnes=(_DATE, _REFERENCE),
    garanti=GARANTI_C14,
)
def mouvement_futur(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un mouvement daté après aujourd'hui, sur toutes les données (C06 de l'audit)."""
    lignes: list[Ligne] = [
        {"date": m.date.isoformat(), "reference": m.reference}
        for m in ctx.complet.mouvements
        if m.date > ctx.aujourdhui
    ]
    return "Mouvement de stock à une date future", lignes


@controle(
    "C16",
    gravite="bloquant",
    lien="/stock?onglet=mouvements",
    colonnes=(_REFERENCE, colonne("fournisseur", "texte"), _DATE),
    garanti=GARANTI_C16,
)
def integrite_des_mouvements(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un mouvement dont la matière, ou le fournisseur, n'est pas au référentiel."""
    references = {a.reference for a in ctx.donnees.articles}
    fournisseurs = {f.nom for f in ctx.donnees.fournisseurs}
    mouvements = ctx.donnees.mouvements
    lignes: list[Ligne] = [
        {"reference": m.reference, "date": m.date.isoformat()}
        for m in mouvements
        if m.reference not in references
    ]
    lignes += [
        {"fournisseur": m.fournisseur, "date": m.date.isoformat()}
        for m in mouvements
        if m.fournisseur and m.fournisseur not in fournisseurs
    ]
    return "Intégrité référentielle des mouvements", lignes


@controle(
    "C18",
    gravite="information",
    lien="/stock",
    colonnes=(_REFERENCE, colonne("stock", "kg"), colonne("jours_sans_mouvement", "j")),
)
def stock_dormant(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Le stock détenu (magasins) qui dort — pas le projeté, commandes comprises."""
    lignes: list[Ligne] = [
        {
            "reference": ligne.reference,
            "stock": ligne.stock_net,
            "jours_sans_mouvement": ligne.jours_sans_mouvement,
        }
        for ligne in ctx.lignes_stock
        if ligne.dormant
    ]
    return f"Stock dormant depuis plus de {ctx.parametres.seuil_dormant:.0f} jours", lignes


@controle(
    "C20",
    gravite="bloquant",
    lien="/inventaire",
    colonnes=(_REFERENCE, colonne("stock_net", "kg")),
)
def negatif_sans_consommation(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un stock négatif sur une matière qui ne sort pas : une erreur de saisie."""
    lignes: list[Ligne] = [
        {"reference": x.reference, "stock_net": x.stock_net}
        for x in ctx.lignes_stock
        if x.stock_net < -POUSSIERE and x.conso_mensuelle == 0
    ]
    return "Stock négatif sur une matière sans consommation", lignes


@controle(
    "C26",
    gravite="avertissement",
    lien="/stock?onglet=mouvements",
    colonnes=(
        _DATE,
        _REFERENCE,
        colonne("quantite", "kg"),
        colonne("numero_of", "texte"),
        colonne("utilisateur", "texte"),
    ),
    garanti=GARANTI_C26,
)
def sortie_sans_lot(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Une sortie sans lot casse la chaîne : des kilos partis, on ne sait d'où."""
    lignes: list[Ligne] = [
        {
            "date": m.date.isoformat(),
            "reference": m.reference,
            "quantite": m.quantite,
            "numero_of": m.numero_of,
            "utilisateur": m.utilisateur,
        }
        for m in ctx.donnees.mouvements
        if m.type in ("SORTIE_PROD", "RETOUR_FOURNISSEUR") and not m.lot_fournisseur
    ]
    return "Sortie de stock sans numéro de lot", lignes


@controle(
    "C27",
    gravite="bloquant",
    lien="/stock?onglet=lots",
    colonnes=(
        _REFERENCE,
        colonne("lot", "texte"),
        colonne("stock", "kg"),
        colonne("entrees", "kg"),
        colonne("sorties", "kg"),
    ),
)
def lot_negatif(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un lot dont il est sorti plus qu'il n'est entré (solde final, toutes les données)."""
    lignes: list[Ligne] = [
        {
            "reference": lot.reference,
            "lot": lot.lot,
            "stock": lot.stock,
            "entrees": lot.entrees,
            "sorties": lot.sorties,
        }
        for lot in stock_par_lot(ctx.complet)
        if lot.negatif
    ]
    return "Lot dont il est sorti plus qu'il n'est entré", lignes


def stock_negatif_passe(donnees: Donnees) -> list[Ligne]:
    """Chaque lot, magasin par magasin, qui a été sous zéro le soir d'un jour passé : le
    premier jour, et le creux. Le journal est cumulé jour par jour (l'ordre de saisie dans
    une journée ne compte pas)."""
    par_jour: dict[tuple[str, str, str], dict[date, float]] = {}
    for m in donnees.mouvements:
        for magasin, quantite in flux_par_magasin(m):
            if magasin:
                jours = par_jour.setdefault((m.reference, m.lot_fournisseur, magasin), {})
                jours[m.date] = jours.get(m.date, 0.0) + quantite
    resultat: list[Ligne] = []
    for (reference, lot, magasin), jours in sorted(par_jour.items()):
        cumul, premier, creux = 0.0, None, 0.0
        for jour in sorted(jours):
            cumul += jours[jour]
            if cumul < -POUSSIERE:
                premier = premier or jour
                creux = min(creux, cumul)
        if premier is not None:
            resultat.append(
                {
                    "reference": reference,
                    "lot": lot,
                    "magasin": magasin,
                    "date": premier.isoformat(),
                    "manque": -creux,
                }
            )
    return resultat


@controle(
    "C37",
    gravite="bloquant",
    lien="/stock?onglet=mouvements",
    colonnes=(
        _REFERENCE,
        colonne("lot", "texte"),
        colonne("magasin", "texte"),
        _DATE,
        colonne("manque", "kg"),
    ),
)
def lot_sous_zero_passe(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """Un lot sous zéro à une date passée : C27 ne voit que le solde final, une sortie datée
    avant l'entrée de son lot lui échappait (et partait à coût nul)."""
    return (
        "Lot sous zéro à une date passée (écriture datée avant l'entrée de la matière)",
        stock_negatif_passe(ctx.complet),
    )
