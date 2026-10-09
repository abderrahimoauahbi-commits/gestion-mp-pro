"""Classeurs des ordres de fabrication (route 144) : la liste de l'écran Sorties (mêmes filtres)
ou la consommation des ordres validés (onglet « Ordres de fabrication » du stock).

Conventions de `exports/classeur.py` (lot D9). Aucun prix : tout est en kilos (le cuir, les
franges et le ruban compris) et en m² ; colonnes de Gestion MP (REGLES P83).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, exporte_le, filtres
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.services.ordres import ConsommationLue, FiltresOrdres, OrdreLu

STATUTS = {
    StatutOrdre.valide: "validés",
    StatutOrdre.brouillon: "brouillons",
    StatutOrdre.annule: "annulés",
}
LIBELLES = {StatutOrdre.valide: "Validé", StatutOrdre.brouillon: "Brouillon",
            StatutOrdre.annule: "Annulé"}  # fmt: skip

COLONNES_ORDRES = (
    Colonne("Ordre", lambda x: x.numero or "Brouillon"),
    Colonne("Statut", lambda x: LIBELLES[x.statut]),
    Colonne("Date", lambda x: x.date, "date"),
    Colonne("Fabrication", lambda x: x.fabrication),
    Colonne("m²", lambda x: x.m2 or None, "m2"),
    Colonne("Métier", lambda x: x.metier),
    Colonne("Magasin", lambda x: x.magasin),
    Colonne("Prévu par la recette (kg)", lambda x: x.prevu or None, "kg"),
    Colonne("Sorti net (kg)", lambda x: x.net, "kg"),
    Colonne("Écart (kg)", lambda x: x.ecart, "kg"),
    Colonne("Écart", lambda x: x.ecart_relatif, "pourcent"),
    Colonne("Revenu (kg)", lambda x: x.revenu or None, "kg"),
    Colonne("Retours", lambda x: ", ".join(r.numero for r in x.retours)),
    Colonne("Commentaire", lambda x: x.commentaire),
    Colonne("Par", lambda x: x.valide_par or x.cree_par),
)

COLONNES_CONSOMMATION = (
    Colonne("Ordre", lambda x: x.numero),
    Colonne("Début", lambda x: x.debut, "date"),
    Colonne("Fin", lambda x: x.fin, "date"),
    Colonne("Fabrication", lambda x: x.fabrication),
    Colonne("m²", lambda x: x.m2 or None, "m2"),
    Colonne("Prévu par la recette (kg)", lambda x: x.prevu or None, "kg"),
    Colonne("Sorti (kg)", lambda x: x.consomme, "kg"),
    Colonne("Revenu (kg)", lambda x: x.retours or None, "kg"),
    Colonne("Sorti net (kg)", lambda x: x.net, "kg"),
    Colonne("Écart (kg)", lambda x: x.ecart, "kg"),
    Colonne("Écart", lambda x: x.ecart_relatif, "pourcent"),
    Colonne("Matières", lambda x: ", ".join(r.reference for r in x.references)),
    Colonne("Lots", lambda x: ", ".join(x.lots)),
    Colonne("Commentaire", lambda x: x.commentaire),
)


def _filtres(f: FiltresOrdres) -> str:
    """La ligne des filtres posés (celle de l'écran)."""
    return filtres([("mots", f.q), ("du", f.du), ("au", f.au)])


def ordres(lignes: Sequence[OrdreLu], f: FiltresOrdres, jour: date) -> bytes:
    """La liste des ordres, telle que l'écran la montre."""
    quels = STATUTS[f.statut] if f.statut else "tous"
    entete = [exporte_le(f"Ordres de fabrication ({quels})", jour), _filtres(f)]
    return classeur([Feuille("Ordres", COLONNES_ORDRES, lignes, entete)], True)


def consommation(lignes: Sequence[ConsommationLue], f: FiltresOrdres, jour: date) -> bytes:
    """Ce que chaque ordre validé a consommé, face au prévu de sa recette."""
    entete = [exporte_le("Consommation des ordres de fabrication", jour), _filtres(f)]
    return classeur([Feuille("Consommation", COLONNES_CONSOMMATION, lignes, entete)], True)
