"""Le planificateur des tâches de fond : un seul porteur, boucle de 15 minutes, échecs isolés.

ARCHITECTURE § 12 ; crochet de `main.py` : `demarrer()` et `arreter()` si `GESTIONMPPRO_TACHES=1`.

- **Un seul porteur** parmi tous les processus (plusieurs workers, plusieurs serveurs) : celui
  qui tient le verrou consultatif de session TACHES, sur une connexion à lui (hors réserve :
  `execution.moteur_des_verrous`). Chaque processus garde son fil : à chaque tour il vérifie
  qu'il tient toujours le verrou (connexion tombée : il le reprend s'il est libre), ou tente de
  le prendre (le porteur s'est arrêté : un autre prend la relève).
- La restauration épargne cette connexion (G-08) ; pendant qu'elle tourne, aucun passage.
- Chaque tâche dans son `try` : un échec (noté dans `tache_execution`, journal du serveur) ne
  gêne pas les suivantes ; la photo et le courriel sont deux tâches (E-15).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

from gestion_mp_pro.db import Verrou, essayer_verrou, liberer, verrou_tenu
from gestion_mp_pro.services import execution, horloge
from gestion_mp_pro.taches import alertes, courriels, photo_du_jour, purges, sauvegarde_du_jour

JOURNAL = logging.getLogger("gestion_mp_pro.taches")

PERIODE_S = 15 * 60.0
"""L'intervalle entre deux passages (le premier a lieu au démarrage)."""

TACHES: tuple[tuple[str, Callable[[], bool | None]], ...] = (
    ("sauvegarde", sauvegarde_du_jour.executer),
    ("photo_indicateurs", photo_du_jour.executer),
    ("courriel", courriels.executer),
    ("notifications", alertes.executer),
    ("purges", purges.executer),
)
"""Les tâches d'un passage, dans l'ordre ; une tâche qui rend `False` n'avait rien à faire."""

_TENU = text(
    "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = pg_backend_pid()"
    " AND locktype = 'advisory' AND granted AND classid = 0 AND objid = :cle AND objsubid = 1)"
)


@dataclass
class _Etat:
    """L'état du planificateur dans ce processus."""

    connexion: Connection | None = None
    fil: threading.Thread | None = None
    arret: threading.Event = field(default_factory=threading.Event)


_ETAT = _Etat()


def _lacher() -> None:
    """Ferme la connexion du verrou (le verrou part avec elle)."""
    if _ETAT.connexion is not None:
        try:
            _ETAT.connexion.close()
        except SQLAlchemyError:
            JOURNAL.warning("Connexion du verrou des tâches déjà fermée.")
        _ETAT.connexion = None


def tenir_le_verrou() -> bool:
    """Vrai si ce processus porte les tâches (verrou vérifié, repris ou pris)."""
    if _ETAT.connexion is not None:
        try:
            tenu = bool(_ETAT.connexion.execute(_TENU, {"cle": int(Verrou.TACHES)}).scalar())
            _ETAT.connexion.commit()
            if tenu:
                return True
        except SQLAlchemyError:
            JOURNAL.warning("Connexion du verrou des tâches perdue : nouvelle tentative.")
        _lacher()
    try:
        c = execution.moteur_des_verrous().connect()
        obtenu = essayer_verrou(c, Verrou.TACHES)
        c.commit()
    except SQLAlchemyError:
        JOURNAL.warning("Base injoignable : les tâches attendent le prochain tour.")
        return False
    if not obtenu:
        c.close()
        return False
    _ETAT.connexion = c
    JOURNAL.info("Ce processus porte les tâches de fond.")
    return True


def porteur() -> bool:
    """Ce processus porte-t-il les tâches (sans rien tenter) ?"""
    return _ETAT.connexion is not None


def executer(nom: str, fonction: Callable[[], bool | None]) -> str:
    """Lance une tâche isolée ; note son passage ; rend l'erreur (vide si réussie)."""
    debut = horloge.maintenant()
    depart = time.monotonic()
    erreur = ""
    try:
        if fonction() is False:
            return ""
    except Exception as exc:  # isolement : une tâche en échec ne gêne pas les suivantes
        JOURNAL.exception("[%s] échec", nom)
        erreur = str(getattr(exc, "detail", "") or exc or type(exc).__name__)[:300]
    duree = int((time.monotonic() - depart) * 1000)
    try:
        execution.noter(nom, debut, erreur, duree)
    except SQLAlchemyError:
        JOURNAL.exception("[%s] état non noté", nom)
    return erreur


def passage() -> dict[str, str]:
    """Un passage de toutes les tâches ; rend {tâche: erreur} (vide si tout a réussi)."""
    try:
        if verrou_tenu(Verrou.RESTAURATION):
            JOURNAL.info("Restauration en cours : passage des tâches remis au tour suivant.")
            return {}
    except SQLAlchemyError:
        return {}
    return {nom: e for nom, fonction in TACHES if (e := executer(nom, fonction))}


def _boucle() -> None:
    """Le fil des tâches : un passage par tour s'il porte le verrou."""
    while not _ETAT.arret.is_set():
        try:
            if tenir_le_verrou():
                passage()
        except Exception:  # le fil ne meurt jamais : il retente au tour suivant
            JOURNAL.exception("Passage des tâches interrompu.")
        _ETAT.arret.wait(PERIODE_S)


def demarrer() -> None:
    """Démarre le fil des tâches de ce processus (premier tour tout de suite)."""
    if _ETAT.fil is not None and _ETAT.fil.is_alive():
        return
    _ETAT.arret.clear()
    _ETAT.fil = threading.Thread(target=_boucle, name="taches", daemon=True)
    _ETAT.fil.start()


def arreter(delai: float = 30.0) -> None:
    """Arrête le fil (après la tâche en cours) et rend le verrou."""
    _ETAT.arret.set()
    if _ETAT.fil is not None:
        _ETAT.fil.join(delai)
        _ETAT.fil = None
    if _ETAT.connexion is not None:
        try:
            liberer(_ETAT.connexion, Verrou.TACHES)
            _ETAT.connexion.commit()
        except SQLAlchemyError:
            JOURNAL.warning("Verrou des tâches rendu par la fermeture de sa connexion.")
    _lacher()
