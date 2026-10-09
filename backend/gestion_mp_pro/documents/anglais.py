"""Le bon fournisseur parle anglais (décision de Mohamed, DECISIONS A22) : nombres, dates,
conditionnements (`gestion_mp/api/achats.py` : `nombre_en`, `date_en`, `conditionnement_en`).

Fonctions pures, sans base : le HTML (`documents/bon_commande.py`) et le classeur
(`exports/bon_fournisseur.py`) les partagent, pour dire exactement la même chose.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

MOIS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

CONDITIONNEMENTS = {
    "palette": "Pallet",
    "fût": "Drum",
    "fut": "Drum",
    "bobine": "Bobbin",
    "cône": "Cone",
    "cone": "Cone",
    "sac": "Bag",
    "rouleau": "Roll",
    "carton": "Carton",
    "balle": "Bale",
    "caisse": "Case",
    "bidon": "Can",
}
"""Les conditionnements de la fiche matière, traduits ; un nom inconnu reste tel quel."""

AU_POIDS = ("kg", "ml")
"""Une ligne commandée au poids (le bon compte en kilos, le cuir et le ruban compris)."""


def nombre_en(x: float | Decimal, decimales: int = 1) -> str:
    """« 1,234.5 » : l'écriture anglaise, zéros inutiles retirés (« 1,120 », « 2.5 »)."""
    texte = f"{float(x):,.{decimales}f}"
    if "." in texte:
        texte = texte.rstrip("0").rstrip(".")
    return "0" if texte in ("-0", "") else texte


def date_en(jour: date) -> str:
    """« 08 Oct 2026 » : sans ambiguïté entre l'ordre européen et l'ordre américain."""
    return f"{jour.day:02d} {MOIS[jour.month - 1]} {jour.year}"


def au_poids(unite: str, contenance: float | Decimal) -> bool:
    """La ligne est-elle commandée au poids (pas de quantité d'unités à imprimer) ?"""
    return unite.strip().lower() in AU_POIDS or not contenance


def conditionnement_en(unite: str, contenance: float | Decimal) -> str:
    """« Pallet of 756 kg », « Drum of 1,000 kg », « By weight » pour une commande au poids."""
    if unite.strip().lower() in AU_POIDS:
        return "By weight"
    nom = CONDITIONNEMENTS.get(unite.strip().lower(), unite.strip())
    if not contenance or float(contenance) == 1:
        return nom
    return f"{nom} of {nombre_en(contenance, 3)} kg"
