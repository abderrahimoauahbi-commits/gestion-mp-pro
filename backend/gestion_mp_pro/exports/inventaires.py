"""Classeurs des inventaires (routes 239 et 240 ; direction et achats) : la liste filtrée par
état, et les lignes d'un inventaire avec leurs écarts en kilos **et** en dirhams.

Conventions communes : `exports.classeur` (lot D9).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, filtres, titre
from gestion_mp_pro.services.inventaires.lecture import InventaireLu, LigneLue

STATUTS = {
    "ouvert": "Comptage en cours",
    "valide": "Validé",
    "abandonne": "Abandonné",
    "annule": "Annulé",
}

COLONNES_LISTE = (
    Colonne("Inventaire", lambda x: x.numero),
    Colonne("Libellé", lambda x: x.libelle),
    Colonne("État", lambda x: STATUTS.get(x.statut, x.statut)),
    Colonne("Date", lambda x: x.date, "date"),
    Colonne("Magasin", lambda x: x.magasin),
    Colonne("Périmètre", lambda x: x.perimetre),
    Colonne("Tolérance", lambda x: x.tolerance, "pourcent"),
    Colonne("Lots figés", lambda x: x.nb_lignes, "entier"),
    Colonne("Lots comptés", lambda x: x.nb_comptees, "entier"),
    Colonne("Hors tolérance", lambda x: x.hors_tolerance, "entier"),
    Colonne("Écart (kg)", lambda x: x.ecart_total, "kg_precis"),
    Colonne("Écart sans signe (kg)", lambda x: x.ecart_absolu, "kg_precis"),
    Colonne("Valeur de l'écart (MAD)", lambda x: x.ecart_valeur_mad, "montant", True),
    Colonne("Valeur sans signe (MAD)", lambda x: x.ecart_valeur_absolue_mad, "montant", True),
    Colonne("Par", lambda x: x.cree_par),
    Colonne("Validé par", lambda x: x.valide_par),
    Colonne("Validé le", lambda x: x.valide_le, "horodatage"),
    Colonne("Abandonné ou annulé par", lambda x: x.abandonne_par or x.annule_par),
    Colonne("Motif", lambda x: x.abandon_motif or x.annulation_motif),
)
"""Route 239."""

COLONNES_LIGNES = (
    Colonne("Référence", lambda x: x.reference),
    Colonne("Désignation", lambda x: x.designation),
    Colonne("Lot", lambda x: x.lot),
    Colonne("Trouvé", lambda x: x.lot_trouve),
    Colonne("Magasin", lambda x: x.magasin),
    Colonne("Théorique (kg)", lambda x: x.theorique, "kg_precis"),
    Colonne("Palettes", lambda x: x.palettes),
    Colonne("Bobines", lambda x: x.bobines),
    Colonne("Compté (kg)", lambda x: x.compte, "kg_precis"),
    Colonne("Compté par", lambda x: x.compte_par),
    Colonne("Recompté (kg)", lambda x: x.second_compte, "kg_precis"),
    Colonne("Recompté par", lambda x: x.second_par),
    Colonne("Retenu (kg)", lambda x: x.retenu, "kg_precis"),
    Colonne("Écart (kg)", lambda x: x.ecart, "kg_precis"),
    Colonne(
        "Écart (%)",
        lambda x: None if x.ecart_pourcent is None else x.ecart_pourcent / 100,
        "pourcent",
    ),
    Colonne("Coût unitaire (MAD/kg)", lambda x: x.cmup_mad, "prix", True),
    Colonne("Valeur de l'écart (MAD)", lambda x: x.valeur_ecart_mad, "montant", True),
    Colonne("Hors tolérance", lambda x: x.hors_tolerance),
    Colonne("Justification", lambda x: x.justification),
)
"""Route 240."""


def liste(lus: Sequence[InventaireLu], voit_prix: bool, jour: date, statut: str) -> bytes:
    """Les inventaires (filtrés par état), les plus récents d'abord."""
    entete = [titre("Inventaires", jour), filtres([("état", STATUTS.get(statut, statut))])]
    return classeur([Feuille("Inventaires", COLONNES_LISTE, lus, entete)], voit_prix)


def lignes(lu: InventaireLu, voit_prix: bool, jour: date) -> bytes:
    """Les lignes d'un inventaire, ses écarts en kilos et en dirhams."""
    entete = [titre(f"{lu.numero} — {lu.libelle} ({lu.magasin})", jour), lu.perimetre]
    rangs: Sequence[LigneLue] = lu.lignes
    return classeur([Feuille(lu.numero, COLONNES_LIGNES, rangs, entete)], voit_prix)
