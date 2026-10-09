"""Tâche « purges », une fois par jour : sessions expirées, tentatives anciennes, notifications
lues depuis 90 jours (ARCHITECTURE § 12 ; incohérence 9 d'EXPLOITATION : Gestion MP ne purgeait
jamais). Le journal, lui, n'est jamais purgé.
"""

from __future__ import annotations

import logging

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.services import execution, horloge, notifications, sessions

JOURNAL = logging.getLogger("gestion_mp_pro.taches")


def executer() -> bool:
    """Un passage : purge si elle n'a pas encore réussi aujourd'hui ; rend vrai si faite."""
    with fabrique()() as s, s.begin():
        if execution.reussie_le(s, "purges", horloge.aujourd_hui()):
            return False
        p = sessions.purger(s)
        lues = notifications.purger(s)
    JOURNAL.info(
        "Purges : %s session(s), %s tentative(s), %s notification(s) lue(s).",
        p.sessions,
        p.tentatives,
        lues,
    )
    return True
