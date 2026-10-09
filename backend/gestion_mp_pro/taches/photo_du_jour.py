"""Tâche « photo_indicateurs » : la photo du jour des indicateurs, si elle manque (§ 12).

D10 possède la tâche, D8 le calcul (LOTS § 2) : si `services.indicateurs.photographier(s)`
existe (lot D8), c'est lui qui photographie ; sinon la photo est prise ici avec le moteur
(`calcul.suivi.photographier_indicateurs`, la même formule). La photo d'un jour n'est jamais
refaite par la tâche (la direction la refait à la main, route 232).
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from importlib.util import find_spec

from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.suivi import photographier_indicateurs
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import IndicateurJour
from gestion_mp_pro.modeles.types import JOURS, MONTANT, TAUX, arrondir
from gestion_mp_pro.services import donnees_moteur, horloge

MODULE_D8 = "gestion_mp_pro.services.indicateurs"


def _photographe() -> Callable[[Session], object] | None:
    """`services.indicateurs.photographier` du lot D8, s'il est livré."""
    if find_spec(MODULE_D8) is None:
        return None
    fonction = getattr(import_module(MODULE_D8), "photographier", None)
    return fonction if callable(fonction) else None


def photographier(s: Session) -> IndicateurJour:
    """La photo du jour par le moteur (repli tant que le lot D8 n'est pas livré)."""
    jour = horloge.aujourd_hui()
    i = photographier_indicateurs(donnees_moteur.charger(s), jour)
    photo = IndicateurJour(
        jour=jour,
        pris_le=horloge.maintenant(),
        valeur_stock_mad=arrondir(i.valeur_stock_mad, MONTANT),
        couverture_jours=arrondir(i.couverture_jours, JOURS),
        ruptures=i.ruptures,
        critiques=i.critiques,
        urgents=i.urgents,
        a_commander_mad=arrondir(i.a_commander_mad, MONTANT),
        commandes_en_cours_mad=arrondir(i.commandes_en_cours_mad, MONTANT),
        otif_moyen=arrondir(i.otif_moyen, TAUX) if i.otif_moyen is not None else None,
    )
    s.add(photo)
    return photo


def executer() -> None:
    """Un passage : la photo du jour si elle manque."""
    with fabrique()() as s, s.begin():
        if s.get(IndicateurJour, horloge.aujourd_hui()) is not None:
            return
        (_photographe() or photographier)(s)
