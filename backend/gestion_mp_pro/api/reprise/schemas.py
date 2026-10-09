"""Schémas Pydantic du domaine « Reprise » (API-PRO § 1.24, routes 243–244). Lot C1.

L'état du miroir n'a ni prix ni montant ; le **rapport** de la reprise (matières signalées,
écarts en valeur) n'est rendu qu'à la direction : l'administrateur technique lit l'état, les
comptes par table et les issues, sans donnée métier.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Sortie
from gestion_mp_pro.modeles.enums import ModeReprise


class ExecutionMiroir(Sortie):
    """Une exécution de la reprise (la plus récente d'abord)."""

    id: int
    debut: dt.datetime
    fin: dt.datetime | None
    statut: str = Field(description="en_cours, reussie, echouee")
    mode: str = Field(description="referentiels, activite, tout")
    base_source: str
    empreinte_source: str | None = Field(description="signature de la source relevée")
    duree_s: float | None
    creees: int = Field(description="lignes créées, toutes tables")
    tables: dict[str, dict[str, int]] = Field(
        description="par table : lues, creees, mises_a_jour, sautees, signalees, supprimees, "
        "ecartees"
    )
    rapport: str | None = Field(description="rapport de contrôle (direction seulement)")


class EtatMiroir(Sortie):
    """Route 243 : l'état du miroir de Gestion MP."""

    base: str = Field(description="base de PRO (cible)")
    base_source: str = Field(description="base de Gestion MP (lue seulement)")
    signature_source: str | None = Field(description="signature actuelle de la source")
    source_lisible: bool
    message_source: str = Field(description="pourquoi la source ne se lit pas (sinon vide)")
    a_jour: bool = Field(description="source inchangée depuis la dernière reprise réussie")
    activite_propre: bool = Field(
        description="activité saisie dans PRO (pas écrite par la dernière reprise)"
    )
    en_cours: bool
    derniere_reussie: ExecutionMiroir | None
    executions: list[ExecutionMiroir] = Field(description="les 10 dernières exécutions")


class RepriseDemandee(Entree):
    """Route 244 : rafraîchir le miroir. `remplacer_activite` exige `confirmation` = REMPLACER
    (casse indifférente) ; sans lui, une activité saisie dans PRO fait refuser (409)."""

    mode: ModeReprise = ModeReprise.tout
    remplacer_activite: bool = False
    confirmation: str | None = Field(default=None, max_length=20)


class ExecutionReprise(Sortie):
    """Route 244 (202) : la reprise a commencé ; l'écran suit son issue par la route 243."""

    etat: Literal["en_cours"] = "en_cours"
    debut: dt.datetime
    mode: str
    remplacer_activite: bool
    message: str
