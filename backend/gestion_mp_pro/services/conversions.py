"""Kilos, bobines, palettes, mètres (REGLES-ECRAN § 3 ; `frontend/src/lib/unites.ts`, même règle).

Le stock est **toujours en kilos**, le cuir, les franges et le ruban compris (leurs mètres se
lisent à titre indicatif : kilos ÷ densité). Une bobine pèse le poids **mesuré sur le lot**,
sinon celui du catalogue ; une palette porte `bobines_palette` bobines. Le serveur ramène toute
saisie aux kilos, au gramme.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Matiere
from gestion_mp_pro.modeles.types import QUANTITE, arrondir

ZERO = Decimal(0)


class Unite(StrEnum):
    """Unité d'une saisie de quantité."""

    kg = "kg"
    bobine = "bobine"
    palette = "palette"


def kg(valeur: Decimal | float, decimales: int = 2) -> str:
    """« 1 234,50 » : espace des milliers, virgule (les refus de Gestion MP, mot pour mot)."""
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


@dataclass(frozen=True)
class Conditionnement:
    """Ce qu'il faut savoir pour convertir : poids d'une bobine, bobines d'une palette,
    densité (kg/ml) d'une matière comptée au mètre (0 sinon)."""

    reference: str
    poids_bobine: Decimal = ZERO
    bobines_palette: Decimal = ZERO
    kg_par_ml: Decimal = ZERO


def conditionnement(
    matiere: Matiere, lot: Lot | None = None, lineaire: bool = False
) -> Conditionnement:
    """Le conditionnement d'une matière, ou d'un lot (son poids de bobine mesuré l'emporte)."""
    poids = lot.poids_bobine if lot is not None and lot.poids_bobine > 0 else matiere.poids_bobine
    return Conditionnement(
        reference=matiere.reference,
        poids_bobine=poids,
        bobines_palette=matiere.bobines_palette,
        kg_par_ml=matiere.densite if lineaire else ZERO,
    )


def contenance(c: Conditionnement, unite: Unite | str) -> Decimal | None:
    """Ce que vaut une unité, en kilos ; `None` si on ne le sait pas."""
    unite = Unite(unite)
    if unite is Unite.kg:
        return Decimal(1)
    if c.poids_bobine <= 0:
        return None
    if unite is Unite.bobine:
        return c.poids_bobine
    return c.poids_bobine * c.bobines_palette if c.bobines_palette > 0 else None


def vers_kg(quantite: Decimal | float, unite: Unite | str, c: Conditionnement) -> Decimal:
    """Les kilos d'une quantité saisie dans une unité, au gramme ; refus si l'unité n'a pas de
    sens pour cette matière (poids de bobine ou de palette inconnu)."""
    try:
        unite = Unite(unite)
    except ValueError:
        raise Refus.saisie(
            f"Unité « {unite} » inconnue : kilos, bobines ou palettes.",
            code="unite_invalide",
            champs={"unite": "kg, bobine ou palette"},
        ) from None
    k = contenance(c, unite)
    if k is None:
        manque = "d'une bobine" if c.poids_bobine <= 0 else "d'une palette"
        raise Refus.saisie(
            f"Le poids {manque} de « {c.reference} » n'est pas connu : saisir en kilos.",
            code="unite_invalide",
            champs={"unite": "saisir en kilos"},
        )
    return arrondir(Decimal(str(quantite)) * k, QUANTITE)


def bobines(kilos: Decimal | float, c: Conditionnement) -> int | None:
    """Le nombre de bobines (arrondi), `None` sans poids de bobine (S65)."""
    if c.poids_bobine <= 0:
        return None
    return round(Decimal(str(kilos)) / c.poids_bobine)


def metres(kilos: Decimal | float, c: Conditionnement) -> Decimal | None:
    """Les mètres indicatifs d'une matière comptée au mètre (kilos ÷ densité), `None` sinon."""
    if c.kg_par_ml <= 0:
        return None
    return Decimal(str(kilos)) / c.kg_par_ml


def kg_et_metres(valeur: Decimal | float, c: Conditionnement, decimales: int = 2) -> str:
    """« 14,30 kg », et pour un cuir, des franges, un ruban « 14,30 kg ≈ 1 021 ml »."""
    texte = f"{kg(valeur, decimales)} kg"
    m = metres(valeur, c)
    return texte + (f" ≈ {kg(m, 0)} ml" if m is not None else "")
