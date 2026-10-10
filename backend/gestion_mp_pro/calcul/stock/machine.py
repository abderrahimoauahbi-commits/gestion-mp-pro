"""Le stock monté sur les métiers : du fil sorti du magasin, pas encore tissé (U8).

Portage de `moteur.FilEnMachine`, `fils_en_machine`, `stock_en_machine` (CALCULS § 3.8).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from gestion_mp_pro.calcul.modele import Donnees

CENT = 100


@dataclass
class FilEnMachine:
    """Ce qu'un fil pèse sur un étage d'un métier."""

    metier: str
    etage: int
    reference: str
    metres: float
    pourcentage: float
    densite: float
    bobines: float
    poids_bobine: float
    poids: float


def fils_en_machine(donnees: Donnees) -> list[FilEnMachine]:
    """Le détail de ce qui est monté sur les métiers actifs, ligne par ligne.

    bobines = mètres × densité du métier (le remplissage des bobines n'y entre pas) ;
    poids = bobines × poids d'une bobine (pesé au lot quand il est connu, sinon celui du
    catalogue — M43) × remplissage des bobines / 100. Le remplissage (`pourcentage`) dit à
    quel point les bobines sont pleines : il pèse sur le poids, pas sur le nombre de bobines.
    """
    resultat = []
    for metier in donnees.metiers:
        if not metier.actif:
            continue
        for fil in metier.fils:
            article = donnees.article(fil.reference)
            poids_bobine = fil.poids_bobine or (article.poids_bobine if article else 0.0)
            bobines = fil.metres * metier.densite
            resultat.append(
                FilEnMachine(
                    metier=metier.code,
                    etage=fil.etage,
                    reference=fil.reference,
                    metres=fil.metres,
                    pourcentage=fil.pourcentage,
                    densite=metier.densite,
                    bobines=bobines,
                    poids_bobine=poids_bobine,
                    poids=bobines * poids_bobine * fil.pourcentage / CENT,
                )
            )
    return resultat


def stock_en_machine(donnees: Donnees) -> dict[str, float]:
    """Kilos montés sur les métiers, par référence ; rien à une date passée (le montage n'a
    pas d'historique, voir `a_la_date`)."""
    if not donnees.montage_connu:
        return {}
    total: dict[str, float] = defaultdict(float)
    for fil in fils_en_machine(donnees):
        total[fil.reference] += fil.poids
    return dict(total)
