"""Le bon fournisseur parle anglais (décision de Mohamed, DECISIONS A22) : les conditionnements
de la fiche matière, traduits (`gestion_mp/api/achats.py` : `CONDITIONNEMENTS_EN`,
`conditionnement_en`). Nombres et dates en anglais : `documents/format.py` (lot D9), jamais
redoublés ici.

Fonctions pures, sans base : le HTML et le classeur du bon les partagent.
"""

from __future__ import annotations

from decimal import Decimal

from gestion_mp_pro.documents.format import nombre

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


def nombre_en(x: float | Decimal, decimales_max: int = 3) -> str:
    """« 1,120 », « 2.5 » : l'écriture anglaise de `format.nombre`, zéros inutiles retirés."""
    return nombre(x, 0, decimales_max, langue="en")


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
    return f"{nom} of {nombre_en(contenance)} kg"
