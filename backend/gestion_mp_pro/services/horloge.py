"""Horloge de l'usine, injectable (ARCHITECTURE C16).

Toute date « du jour » du paquet vient d'ici : `aujourd_hui()` et `maintenant()` à l'heure de
l'usine (`GESTIONMPPRO_FUSEAU`), quel que soit le réglage du poste. Les essais la figent
(`fixer`, `figee`) au 8 octobre 2026 (LOTS § 0 n° 5). Le fuseau n'est jamais posé sur le
processus (`TZ`), seulement passé à `zoneinfo` et à PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from gestion_mp_pro.config import reglages

FUSEAU: ZoneInfo = reglages().zone
"""Le fuseau de l'usine."""

MIDI = time(12, 0)
"""Heure prise quand on fige l'horloge sur un jour sans heure : loin des bascules de date."""


@dataclass
class _Etat:
    """L'instant figé, partagé par tous les fils du processus (le client d'essai en a un)."""

    fixe: datetime | None = None


_ETAT = _Etat()


def maintenant() -> datetime:
    """L'instant présent à l'heure de l'usine (avec son décalage)."""
    if _ETAT.fixe is not None:
        return _ETAT.fixe
    return datetime.now(FUSEAU)


def aujourd_hui() -> date:
    """Le jour présent à l'usine."""
    return maintenant().date()


def _instant(valeur: datetime | date) -> datetime:
    """Un jour devient ce jour à midi ; un instant sans fuseau est lu à l'heure de l'usine."""
    if isinstance(valeur, datetime):
        return valeur if valeur.tzinfo is not None else valeur.replace(tzinfo=FUSEAU)
    return datetime.combine(valeur, MIDI, tzinfo=FUSEAU)


def fixer(valeur: datetime | date | None) -> None:
    """Fige l'horloge sur un instant (ou un jour, à midi) ; `None` la rend au temps réel."""
    _ETAT.fixe = None if valeur is None else _instant(valeur)


def est_figee() -> bool:
    """Vrai si l'horloge est figée (essais)."""
    return _ETAT.fixe is not None


@contextmanager
def figee(valeur: datetime | date) -> Iterator[datetime]:
    """Fige l'horloge le temps d'un bloc, puis remet l'état d'avant."""
    avant = _ETAT.fixe
    fixer(valeur)
    try:
        yield maintenant()
    finally:
        _ETAT.fixe = avant
