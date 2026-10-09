"""Ce que les étapes de la reprise partagent : options, photo, cible, comptes, correspondances.

Une ligne reprise est décrite par une `Ligne` : sa clé dans la table cible, ses valeurs (déjà
normalisées) et son origine (table source, identifiant source). Les identifiants sources sans
entier (tables à clé texte : classification, devises, postes, réglages) reçoivent un
identifiant stable tiré du code (`ident_de_code`).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection

from gestion_mp_pro.modeles.enums import ModeReprise, SourceReprise
from gestion_mp_pro.reprise.normalisation import Normalisation
from gestion_mp_pro.reprise.source import Photo


@dataclass(frozen=True)
class Options:
    """Les options de la ligne de commande."""

    source: str
    cible: str
    mode: ModeReprise
    remplacer_activite: bool = False
    mettre_a_jour: bool = False
    essai: bool = False
    genre: SourceReprise | None = None
    sauvegarder: bool = True
    rapport: str | None = None
    pieces_source: str | None = None
    pieces_cible: str | None = None


@dataclass
class Ligne:
    """Une ligne à écrire : clé cible, valeurs normalisées, origine dans la source."""

    cle: tuple[Any, ...]
    valeurs: dict[str, Any]
    table_source: str
    id_source: int


COMPTES = (
    "lues",
    "creees",
    "mises_a_jour",
    "sautees",
    "signalees",
    "supprimees",
    "ecartees",
    "scindees",
)
"""« écartées » : lignes sources non reprises ou fusionnées (signalées), hors du compte attendu ;
« scindées » : lignes nées d'une scission (réception en deux devises), en plus du compte."""


@dataclass
class Contexte:
    """L'état d'une exécution de la reprise."""

    options: Options
    photo: Photo
    c: Connection
    norm: Normalisation
    source: SourceReprise
    comptes: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: dict.fromkeys(COMPTES, 0))
    )
    ids: dict[str, dict[Any, int]] = field(default_factory=dict)
    empreintes_activite: dict[str, Any] = field(default_factory=dict)
    numeros_retires: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    activite_reprise: bool = False
    scindees: dict[int, int] = field(default_factory=dict)
    """Réception née d'une scission → réception d'origine (identifiants PRO)."""
    numeros_ajoutes: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    """Numéros sans équivalent dans la source (réceptions scindées), par table PRO."""

    def compter(self, table: str, quoi: str, n: int = 1) -> None:
        """Ajoute `n` au compte `quoi` de la table."""
        self.comptes[table][quoi] += n

    def signaler(self, table: str, ident: object, message: str) -> None:
        """Un signalement au rapport (et au compte de la table)."""
        self.norm.signaler(table, ident, message)
        self.compter(table, "signalees")

    def ligne(self, table: str, valeurs: dict[str, Any], ident: object = "") -> dict[str, Any]:
        """Les valeurs mises au type des colonnes de la table PRO."""
        return self.norm.ligne(table, valeurs, ident)

    def personne(self, nom: str | None) -> int | None:
        """Le compte PRO d'un nom cité dans la source (`None` : personne, ou le système)."""
        return self.ids.get("personnes", {}).get((nom or "").strip().lower())

    def code(self, genre: str, valeur: str | None) -> int | None:
        """L'identifiant PRO d'un code de référentiel (`None` si vide ou inconnu)."""
        if valeur is None or valeur == "":
            return None
        return self.ids.get(genre, {}).get(valeur)


def ident_de_code(code: str) -> int:
    """Un identifiant source stable (63 bits) pour une ligne à clé texte."""
    return int.from_bytes(hashlib.sha256(code.encode()).digest()[:8], "big") >> 1
