"""Outils du moteur : l'arrondi d'Excel, les fins et débuts de mois, les palettes.

Portage de `gestion_mp/calcul/moteur.py` (`arrondi`, `fin_de_mois`, `debut_de_mois`,
`mois_du_plan`, `_mois_entre`, `_mois_ecoules`, `_palettes`) et de `controles._pct`.
"""

from __future__ import annotations

import calendar
import math
from datetime import date

from gestion_mp_pro.calcul.constantes import EPSILON, MOIS

DEMI = 0.5
"""Le demi qu'ARRONDI d'Excel envoie vers l'extérieur."""
CENT = 100


def arrondi(valeur: float, decimales: int = 0) -> float:
    """ARRONDI d'Excel : à l'entier supérieur en valeur absolue sur un demi.

    `round()` de Python arrondit au pair le plus proche, ce qui décalerait le plan de
    production d'un m² sur les demis exacts. Même règle à l'affichage (`format.ts`).
    """
    facteur = float(10**decimales)
    valeur_mise_a_l_echelle = valeur * facteur
    return math.floor(abs(valeur_mise_a_l_echelle) + DEMI) * (1 if valeur >= 0 else -1) / facteur


def fin_de_mois(jour: date, decalage: int = 0) -> date:
    """FIN.MOIS : dernier jour du mois décalé de `decalage` mois."""
    rang = jour.month - 1 + decalage
    annee = jour.year + rang // 12
    mois = rang % 12 + 1
    return date(annee, mois, calendar.monthrange(annee, mois)[1])


def debut_de_mois(jour: date, decalage: int = 0) -> date:
    """Premier jour du mois décalé de `decalage` mois."""
    mois = jour.month - 1 + decalage
    annee = jour.year + mois // 12
    return date(annee, mois % 12 + 1, 1)


def mois_du_plan(date_ref: date) -> list[date]:
    """Les douze fins de mois du plan glissant, M0 = mois en cours (`Production_Plan!B5`)."""
    return [fin_de_mois(date_ref, i) for i in range(MOIS)]


def mois_entre(debut: date, fin: date) -> int:
    """Le nombre de mois du mois de `debut` à celui de `fin` (0 : le même mois)."""
    return (fin.year - debut.year) * 12 + fin.month - debut.month


def mois_ecoules(depuis: date, jusqu_a: date) -> int:
    """DATEDIF(…;"m") + 1, au minimum 1 — le nombre de mois d'historique."""
    mois = (jusqu_a.year - depuis.year) * 12 + (jusqu_a.month - depuis.month)
    if jusqu_a.day < depuis.day:
        mois -= 1
    return max(1, mois + 1)


def palettes(quantite: float, contenance: float) -> int:
    """Unités entières pour cette quantité, à l'epsilon flottant près (82,85 → 83)."""
    if not contenance:
        return 0
    return math.ceil(quantite / contenance - EPSILON)


def pourcentage(part: float) -> str:
    """0,02 → « 2 % » : le nombre, une espace, le signe, comme ailleurs dans les libellés."""
    return f"{round(part * CENT, 2):g} %"


def jour_plus(jour: date, jours: float) -> date:
    """Le jour `jours` plus tard, arrondi au jour supérieur (4,5 jours livrent le cinquième)."""
    return date.fromordinal(jour.toordinal() + math.ceil(jours))
