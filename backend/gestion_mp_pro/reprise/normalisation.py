"""Normalisation à l'entrée, une seule fois (MODELE-DONNEES § 10.2), et signalements.

Chaque valeur est mise au type de sa colonne PRO, lu dans les métadonnées des modèles :

- nombre `NUMERIC(p, s)` : arrondi à l'échelle, demi vers le haut (`types.arrondir`) ; le
  rapport compte, par table et colonne, les valeurs arrondies et l'écart maximal ;
- entier : un flottant entier est gardé ; un flottant décimal est arrondi (compté) ;
- instant (`TIMESTAMPTZ`) : un instant sans fuseau de Gestion MP est l'heure de l'usine ;
- texte borné : tronqué à la longueur de la colonne, et **signalé**.

Un `NaN` n'entre jamais : il devient `NULL` si la colonne le permet, sinon 0, et il est
signalé. Les données douteuses sont **signalées, jamais corrigées en silence** (M11).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Table

from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.types import Nombre, arrondir

UTC = dt.UTC


@dataclass(frozen=True)
class Signalement:
    """Une valeur douteuse ou transformée, dite au rapport."""

    table: str
    ident: str
    message: str


@dataclass
class Arrondi:
    """Les arrondis d'une colonne : combien de valeurs, écart maximal."""

    nombre: int = 0
    ecart_max: Decimal = Decimal(0)


@dataclass
class Normalisation:
    """Met les valeurs sources au type des colonnes PRO et tient le compte de ce qui a changé."""

    zone: ZoneInfo
    arrondis: dict[tuple[str, str], Arrondi] = field(default_factory=lambda: defaultdict(Arrondi))
    signalements: list[Signalement] = field(default_factory=list)

    def signaler(self, table: str, ident: object, message: str) -> None:
        """Ajoute une ligne au rapport (« table n° ident : message »)."""
        self.signalements.append(Signalement(table, str(ident), message))

    def instant(self, valeur: dt.datetime | None) -> dt.datetime | None:
        """Un instant de Gestion MP (sans fuseau : heure de l'usine) avec son fuseau."""
        if valeur is None:
            return None
        return valeur if valeur.tzinfo else valeur.replace(tzinfo=self.zone)

    def ligne(self, table: str, valeurs: dict[str, Any], ident: object = "") -> dict[str, Any]:
        """La ligne mise au type de chaque colonne de la table PRO `table`."""
        t: Table = metadata.tables[table]
        return {nom: self._valeur(t.c[nom], v, ident) for nom, v in valeurs.items()}

    def _valeur(self, colonne: Column[Any], v: Any, ident: object) -> Any:
        """Une valeur au type de sa colonne."""
        if v is None:
            return None
        type_ = colonne.type
        table = str(colonne.table.name)
        if isinstance(type_, Numeric):
            return self._nombre(colonne, v, ident)
        if isinstance(type_, Integer) and isinstance(v, float):
            return self._entier(table, colonne, v, ident)
        if isinstance(type_, DateTime) and isinstance(v, dt.datetime):
            return self.instant(v)
        longueur = getattr(type_, "length", None)
        if isinstance(type_, String) and longueur and isinstance(v, str) and len(v) > longueur:
            self.signaler(table, ident, f"{colonne.name} tronqué à {longueur} caractères")
            return v[:longueur]
        return v

    def _nombre(self, colonne: Column[Any], v: Any, ident: object) -> Decimal | None:
        """Arrondi à l'échelle de la colonne ; `NaN` → NULL ou 0, signalé."""
        table = str(colonne.table.name)
        type_: Any = colonne.type
        categorie = Nombre(colonne.name, type_.precision or 38, type_.scale or 0)
        if isinstance(v, float) and not math.isfinite(v):
            self.signaler(table, ident, f"{colonne.name} = {v} (pas un nombre) : remplacé")
            return None if colonne.nullable else Decimal(0).quantize(categorie.pas)
        exact = v if isinstance(v, Decimal) else Decimal(repr(v) if isinstance(v, float) else v)
        resultat = arrondir(exact, categorie)
        if resultat != exact:
            a = self.arrondis[(table, colonne.name)]
            a.nombre += 1
            a.ecart_max = max(a.ecart_max, abs(resultat - exact))
        return resultat

    def _entier(self, table: str, colonne: Column[Any], v: float, ident: object) -> int:
        """Un flottant mis en entier (jours) ; arrondi compté s'il n'était pas entier."""
        if not math.isfinite(v):
            self.signaler(table, ident, f"{colonne.name} = {v} (pas un nombre) : 0")
            return 0
        entier = int(Decimal(repr(v)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if entier != v:
            a = self.arrondis[(table, colonne.name)]
            a.nombre += 1
            a.ecart_max = max(a.ecart_max, abs(Decimal(repr(v)) - entier))
        return entier


def canonique(v: Any) -> Any:
    """Forme comparable d'une valeur (la même qu'on la lise en base ou qu'on la calcule)."""
    if isinstance(v, dt.datetime):
        return (v if v.tzinfo else v.replace(tzinfo=UTC)).astimezone(UTC).isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, dict | list):
        return json.dumps(v, sort_keys=True, default=str, ensure_ascii=False)
    return v


def empreinte(valeurs: dict[str, Any]) -> str:
    """SHA-256 d'une ligne (colonnes triées, valeurs canoniques)."""
    texte = json.dumps(
        {k: canonique(v) for k, v in sorted(valeurs.items())},
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    return hashlib.sha256(texte.encode()).hexdigest()


def empreinte_lignes(lignes: list[dict[str, Any]]) -> str:
    """SHA-256 d'une liste de lignes, indépendante de leur ordre."""
    return hashlib.sha256("\n".join(sorted(empreinte(x) for x in lignes)).encode()).hexdigest()
