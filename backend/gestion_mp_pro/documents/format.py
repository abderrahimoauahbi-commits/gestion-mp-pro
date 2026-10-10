"""La règle unique d'arrondi et d'affichage des documents imprimés (ARCHITECTURE § 9.3).

Le jumeau de `frontend/src/lib/format.ts` : mêmes fonctions, même texte, pour que la page imprimée
dise exactement ce que dit l'écran.

- Arrondi : ARRONDI d'Excel (demi loin de zéro), une seule fois, sur l'écriture décimale la plus
  courte du nombre (`Decimal(str(v))` : 2,675 → 2,68 comme Excel).
- Français : espace insécable U+00A0 des milliers et devant l'unité, virgule, « − » (U+2212) ;
  jamais « -0 » : un nombre qui s'arrondit à zéro n'a pas de signe. Vide : « — ».
- Anglais (bon fournisseur) : « 1,234.5 », zéros inutiles retirés, dates « 08 Oct 2026 ».
"""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from gestion_mp_pro.services import horloge

Langue = Literal["fr", "en"]
VIDE = "—"
INSECABLE = " "
MOINS = "−"
MOIS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

Nombre = Decimal | float | int | None


def affichable(valeur: Nombre) -> bool:
    """Un nombre qu'on peut écrire (ni vide, ni NaN, ni infini)."""
    if valeur is None or isinstance(valeur, bool):
        return False
    if isinstance(valeur, Decimal):
        return valeur.is_finite()
    return math.isfinite(valeur)


def arrondi(valeur: Decimal | float | int, decimales: int = 0) -> Decimal:
    """ARRONDI d'Excel : le demi s'éloigne de zéro (2,5 → 3 ; −2,5 → −3 ; 2,675 → 2,68)."""
    brut = valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))
    r = brut.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)
    return r if r != 0 else abs(r)


def nombre(
    valeur: Nombre, decimales: int = 0, decimales_max: int | None = None, langue: Langue = "fr"
) -> str:
    """« 17 398 184 » ; « 1 234,5 » ; « −3 » (en anglais « 1,234.5 », « -3 »).

    `decimales` exactes, et jusqu'à `decimales_max` quand il en faut (les zéros au-delà de
    `decimales` ne s'écrivent pas).
    """
    if valeur is None or not affichable(valeur):
        return VIDE
    plus = max(decimales, decimales_max if decimales_max is not None else decimales)
    r = arrondi(valeur, plus)
    entier, _, fraction = f"{abs(r):,.{plus}f}".partition(".")
    gardees = fraction[:decimales] + fraction[decimales:].rstrip("0")
    if langue == "en":
        texte = f"{entier}.{gardees}" if gardees else entier
        return f"-{texte}" if r < 0 else texte
    entier = entier.replace(",", INSECABLE)
    texte = f"{entier},{gardees}" if gardees else entier
    return f"{MOINS}{texte}" if r < 0 else texte


def _avec_unite(texte: str, unite: str) -> str:
    return VIDE if texte == VIDE else f"{texte}{INSECABLE}{unite}"


def kg(valeur: Nombre, langue: Langue = "fr") -> str:
    """Kilos au bureau : jusqu'à deux décimales, zéros inutiles enlevés (« 3,15 kg », « 52,4 kg »,
    « 26 000 kg ») ; Excel `#,##0.##`."""
    return _avec_unite(nombre(valeur, 0, 2, langue=langue), "kg")


def kg_entier(valeur: Nombre, langue: Langue = "fr") -> str:
    """Kilos commandés au kilo : entiers (« 5 029 kg »)."""
    return _avec_unite(nombre(valeur, 0, langue=langue), "kg")


def m2(valeur: Nombre, langue: Langue = "fr") -> str:
    """Surface : entière (« 1 200 m² »)."""
    return _avec_unite(nombre(valeur, 0, langue=langue), "m²")


def montant(valeur: Nombre, devise: str) -> str:
    """Montant des tableaux : entier, devise toujours dite (« 1 234 MAD »)."""
    return _avec_unite(nombre(valeur, 0), devise)


def montant_precis(valeur: Nombre, devise: str) -> str:
    """Montant des documents, de l'échéancier, des dossiers : au centime (« 1 234,50 MAD »)."""
    return _avec_unite(nombre(valeur, 2), devise)


def prix(valeur: Nombre) -> str:
    """Prix unitaire : deux décimales, jusqu'à quatre sous 0,1 (« 0,0011 »)."""
    if valeur is None or not affichable(valeur):
        return VIDE
    brut = valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))
    if brut != 0 and abs(brut) < Decimal("0.1"):
        return nombre(brut, 2, 4)
    return nombre(valeur, 2)


def cours(valeur: Nombre) -> str:
    """Cours de change : quatre décimales (« 10,0500 »)."""
    return nombre(valeur, 4)


def pourcent(valeur: Nombre, decimales: int = 1) -> str:
    """Un pourcentage déjà exprimé en % : « 12,5 % »."""
    return _avec_unite(nombre(valeur, decimales), "%")


def part(valeur: Nombre, decimales: int = 1) -> str:
    """Une fraction (0,125) dite en pourcentage : « 12,5 % »."""
    if valeur is None or not affichable(valeur):
        return VIDE
    centaines = (valeur if isinstance(valeur, Decimal) else Decimal(str(valeur))).scaleb(2)
    return pourcent(centaines, decimales)


def date_fr(jour: date | datetime | None) -> str:
    """« 08/10/2026 »."""
    return VIDE if jour is None else f"{jour:%d/%m/%Y}"


def date_en(jour: date | datetime | None) -> str:
    """« 08 Oct 2026 » : sans ambiguïté entre l'ordre européen et l'ordre américain."""
    if jour is None:
        return VIDE
    return f"{jour.day:02d} {MOIS_EN[jour.month - 1]} {jour.year}"


def a_l_usine(instant: datetime) -> datetime:
    """Un instant à l'heure de l'usine (un instant sans fuseau est déjà à l'heure de l'usine)."""
    return instant if instant.tzinfo is None else instant.astimezone(horloge.FUSEAU)


def horodatage(instant: datetime | None) -> str:
    """« 08/10/2026 14:03 » à l'heure de l'usine."""
    return VIDE if instant is None else f"{a_l_usine(instant):%d/%m/%Y %H:%M}"


def jour(valeur: date | datetime | None, langue: Langue = "fr") -> str:
    """Une date dans la langue du document."""
    return date_en(valeur) if langue == "en" else date_fr(valeur)
