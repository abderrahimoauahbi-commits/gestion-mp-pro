"""Les 38 contrôles de cohérence (C01 → C38), rejoués sur les données du moteur.

Chaque contrôle rend un compte **et la liste complète des lignes fautives** : on clique sur le
compte, on voit quoi corriger. Portage de `gestion_mp/calcul/controles.py`, méthode
« corrigée » seulement (DECISIONS P17), en registre (ARCHITECTURE § 7) : une fonction par
contrôle, rangée par famille (`recettes`, `production`, `stock`, `catalogue`, `achats`,
`devises`, `metiers`, `importations`), rendue dans l'ordre numérique.

Six contrôles du classeur ont disparu, et c'est voulu : T05, T06 (références et fournisseurs
orphelins) sont devenus des clés étrangères ; T17, T18, T19 (pesées non recopiées) n'ont plus
d'objet ; T20 (formules non propagées) est un problème de tableur.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gestion_mp_pro.calcul.controles import (  # noqa: F401 — chaque module déclare ses contrôles
    achats,
    catalogue,
    devises,
    importations,
    metiers,
    production,
    recettes,
    stock,
)
from gestion_mp_pro.calcul.controles.base import (
    REGISTRE,
    Colonne,
    Contexte,
    Controle,
    Gravite,
    Ligne,
    Unite,
)
from gestion_mp_pro.calcul.controles.production import MOTIFS_PERMIS
from gestion_mp_pro.calcul.controles.stock import stock_negatif_passe
from gestion_mp_pro.calcul.controles.textes import COLONNES, QUOI_FAIRE
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.stock import LigneStock

__all__ = [
    "COLONNES",
    "MOTIFS_PERMIS",
    "QUOI_FAIRE",
    "REGISTRE",
    "Colonne",
    "Contexte",
    "Controle",
    "Gravite",
    "Ligne",
    "Synthese",
    "Unite",
    "controler",
    "stock_negatif_passe",
    "synthese",
]


def controler(
    donnees: Donnees,
    lignes_stock: list[LigneStock],
    date_ref: date,
    complet: Donnees | None = None,
    aujourdhui: date | None = None,
) -> list[Controle]:
    """Rejoue les 38 contrôles, dans l'ordre numérique.

    `donnees` : les données à la date de référence ; `lignes_stock` : `etat_stock` à cette
    date ; `complet` : toutes les données, rien de retiré — les contrôles d'intégrité (C12,
    C14, C27, C37) tournent sur elles ; `aujourdhui` : la date du jour, à laquelle C14 juge le
    futur (jamais avant `date_ref`).
    """
    ctx = Contexte.preparer(donnees, lignes_stock, date_ref, complet, aujourdhui)
    return [REGISTRE[code].executer(ctx) for code in sorted(REGISTRE)]


@dataclass(frozen=True)
class Synthese:
    """La note des contrôles.

    Ceux que la base ou la saisie garantissent (conformes) ne comptent ni parmi les conformes
    ni dans le total : un zéro qui ne peut pas être autre chose ne dit rien des données.
    `anomalies` compte des contrôles, pas des lignes ; `a_corriger` laisse de côté les
    contrôles « pour information » (la pastille du menu le lit).
    """

    total: int
    conformes: int
    garantis: int
    anomalies: int
    a_corriger: int
    bloquants: int
    score: float


def synthese(controles: list[Controle]) -> Synthese:
    """La synthèse d'une liste de contrôles (mêmes formules que Gestion MP)."""
    garantis = sum(1 for c in controles if c.garanti)
    verifies = len(controles) - garantis
    conformes = sum(1 for c in controles if c.conforme and not c.garanti)
    return Synthese(
        total=verifies,
        conformes=conformes,
        garantis=garantis,
        anomalies=sum(1 for c in controles if not c.conforme),
        a_corriger=sum(1 for c in controles if not c.conforme and c.gravite != "information"),
        bloquants=sum(1 for c in controles if c.gravite == "bloquant" and not c.conforme),
        score=conformes / verifies if verifies else 1.0,
    )
