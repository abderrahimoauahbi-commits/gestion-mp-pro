"""Petits outils partagés par les étapes de l'activité."""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from gestion_mp_pro.reprise.contexte import Contexte

Lignes = dict[str, list[dict[str, Any]]]
"""Les lignes de l'activité à écrire, table PRO par table PRO."""


def fin_du_jour(jour: dt.date | None) -> dt.datetime | None:
    """La dernière seconde d'un jour (ce que le moteur de Gestion MP prend à défaut d'heure)."""
    return None if jour is None else dt.datetime.combine(jour, dt.time.max)  # noqa: DTZ001


def debut_du_jour(jour: dt.date | None) -> dt.datetime | None:
    """Minuit d'un jour."""
    return None if jour is None else dt.datetime.combine(jour, dt.time.min)  # noqa: DTZ001


def numero_de_document(ctx: Contexte, table: str, x: dict[str, Any], brouillon: bool) -> str | None:
    """Le numéro d'un document ; un brouillon numéroté dans la source perd son numéro (signalé).

    PRO exige « brouillon ⇔ sans numéro » ; le numéro retiré reste compté par le compteur
    (il ne sera pas redonné).
    """
    numero = x.get("numero") or None
    if brouillon and numero:
        ctx.signaler(
            table, x["id"], f"brouillon numéroté {numero} : numéro retiré (gardé au compteur)"
        )
        ctx.numeros_retires[table].append(numero)
        return None
    return numero


def plus_frequent(valeurs: list[str], defaut: str) -> str:
    """La valeur la plus fréquente (la première rencontrée à égalité)."""
    if not valeurs:
        return defaut
    return Counter(valeurs).most_common(1)[0][0]


def date_apres(
    ctx: Contexte, table: str, ident: object, nom: str, valeur: dt.date | None, *, debut: dt.date
) -> dt.date | None:
    """Une date qui doit suivre `debut` (CHECK de PRO) : vidée et signalée sinon."""
    if valeur is not None and valeur < debut:
        ctx.signaler(table, ident, f"{nom} {valeur} avant le {debut} : vidé")
        return None
    return valeur


def zero_en_nul(valeur: float | None) -> float | None:
    """Les « trois sens du zéro » : 0 veut dire « inconnu » (cours, montant) → NULL."""
    return None if valeur is None or valeur == 0 else valeur
