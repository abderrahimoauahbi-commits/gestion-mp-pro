"""Le calendrier des sauvegardes automatiques et leur conservation (décision X7 de Mohamed).

Mohamed, 15/10/2026 : « la sauvegarde quotidienne doit se faire vers 22H00 et l'hebdomadaire le
dimanche, la mensuelle fin de mois vers 22H00 ». Trois genres automatiques, chacun son fichier :

- une **échéance** est un instant, à l'heure de l'usine : chaque jour à 22:00 (quotidienne), le
  dimanche à 22:00 (hebdomadaire), le dernier jour du mois à 22:00 (mensuelle) ;
- une sauvegarde d'un genre est **due** dès que la dernière échéance passée de ce genre n'a aucune
  sauvegarde de ce genre faite depuis elle. La boucle de 15 minutes la fait donc entre 22:00 et
  22:15 ; Mac éteint ou en veille à 22 h, elle se fait au prochain passage (**rattrapage**, une
  seule fois même si plusieurs échéances ont été manquées) ;
- **conservation** : les 14 dernières quotidiennes, les 8 dernières hebdomadaires, les 12
  dernières mensuelles, sauf celle de fin décembre (la photo de fin d'année), jamais effacée. Les
  autres genres (manuelle, « avant-* », base vide de référence) ne s'effacent jamais seuls.

Fonctions pures (aucun fichier lu) : `services/sauvegarde.py` les applique au dossier.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta

from gestion_mp_pro.services import horloge

HEURE = time(22, 0)
"""L'heure des trois échéances (heure de l'usine)."""

DIMANCHE = 6
"""`date.weekday()` du dimanche."""

CONSERVATION: dict[str, int] = {"quotidienne": 14, "hebdomadaire": 8, "mensuelle": 12}
"""Les genres automatiques, dans l'ordre où ils se font, et combien en garder de chacun."""

AUTOMATIQUES = tuple(CONSERVATION)

DECEMBRE = 12
"""La mensuelle dont l'échéance tombe en décembre (photo de fin d'année) ne s'efface jamais."""


def _a_22h(jour: date) -> datetime:
    """Ce jour-là à 22:00, heure de l'usine."""
    return datetime.combine(jour, HEURE, tzinfo=horloge.FUSEAU)


def _fin_de_mois(jour: date) -> date:
    """Le dernier jour du mois de `jour`."""
    return jour.replace(day=calendar.monthrange(jour.year, jour.month)[1])


def derniere_echeance(genre: str, instant: datetime) -> datetime:
    """La dernière échéance de ce genre à cet instant ou avant (22:00 pile compris)."""
    quand = instant.astimezone(horloge.FUSEAU)
    jour = quand.date()
    if genre == "quotidienne":
        precedent, candidat = jour - timedelta(days=1), jour
    elif genre == "hebdomadaire":
        candidat = jour - timedelta(days=(jour.weekday() - DIMANCHE) % 7)
        precedent = candidat - timedelta(days=7)
    elif genre == "mensuelle":
        candidat = _fin_de_mois(jour)
        precedent = jour.replace(day=1) - timedelta(days=1)
    else:
        raise ValueError(f"genre sans échéance : {genre}")
    echeance = _a_22h(candidat)
    return echeance if echeance <= quand else _a_22h(precedent)


def dues(faites: Mapping[str, Iterable[datetime]], instant: datetime) -> list[str]:
    """Les genres automatiques dus à cet instant, dans l'ordre (quotidienne d'abord).

    `faites` : pour chaque genre, les instants des sauvegardes de ce genre déjà faites.
    """
    return [
        genre
        for genre in AUTOMATIQUES
        if not any(i >= derniere_echeance(genre, instant) for i in faites.get(genre, ()))
    ]


def fin_d_annee(instant: datetime) -> bool:
    """Une mensuelle faite à cet instant est-elle celle de fin décembre (gardée toujours) ?"""
    return derniere_echeance("mensuelle", instant).month == DECEMBRE


def a_effacer(fichiers: Iterable[tuple[str, str, datetime]]) -> list[str]:
    """Les noms à effacer parmi `(nom, genre, instant)` : au-delà des N plus récentes de chaque
    genre automatique, sauf une mensuelle de fin décembre ; les autres genres jamais."""
    par_genre: dict[str, list[tuple[datetime, str]]] = {g: [] for g in AUTOMATIQUES}
    for nom, genre, instant in fichiers:
        if genre in par_genre:
            par_genre[genre].append((instant, nom))
    effaces: list[str] = []
    for genre, liste in par_genre.items():
        for instant, nom in sorted(liste, reverse=True)[CONSERVATION[genre] :]:
            if not (genre == "mensuelle" and fin_d_annee(instant)):
                effaces.append(nom)
    return sorted(effaces)
