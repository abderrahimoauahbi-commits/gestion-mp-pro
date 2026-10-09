"""Parité : le rapport (`essais/resultat-parite.txt`) et le verdict (critère A6).

Le verdict ne tient qu'à un nombre : les écarts **à corriger** (sans classe), toutes passes
confondues, plus ce qui invalide la parité elle-même (une base de Gestion MP modifiée, un
rejeu infidèle, un prix montré à l'alimentation). Chaque écart expliqué l'est par sa classe,
comptée par passe et par section, avec son ampleur maximale.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

CORRECTIONS = {
    "ORDRE": "Ordre de lecture des recettes (même contenu) — traduction du chargeur ; "
             "preuve : Gestion MP recalculé sur ses données remises dans l'ordre de PRO.",
    "K1": "Arrondi à l'échelle des colonnes (MODELE-DONNEES § 10.2) — preuve : Gestion MP "
          "recalculé sur ses données arrondies par la règle de la reprise (rejeu du moteur et "
          "des routes ; chaîne en base pour les documents).",
    "K2": "Inventaire limité à son périmètre — preuve : geste joué, Gestion MP refuse pour la "
          "suspension du magasin (message vérifié), PRO accepte un fil hors périmètre.",
    "K3": "Inventaire abandonné gardé avec ses lignes (hors des calculs) — preuve : abandonné des "
          "deux côtés, Gestion MP corrigé garde l'en-tête et efface les lignes.",
    "K4": "Réception toute refusée annulable — Gestion MP corrigé l'annule aussi : même issue.",
    "K5": "`controle_par` lu comme contrôleur — vide dans toute l'année d'essai : sans effet.",
    "K6": "Alimentation : ni réglages ni cours (403) — Gestion MP corrigé refuse aussi.",
    "K7": "Fil monté compté à toute date (décision de Mohamed, U8 ; D8) — preuve : copie montée, "
          "Gestion MP rejoué avec le montage connu aux dates passées redonne ce que PRO change.",
    "K8a": "Prix des sorties, transferts, retours machine non repris (R1 n° 1).",
    "K8b": "Réception payée en deux devises : devise de l'en-tête (R1 n° 2 ; Mohamed tranche).",
    "K8c": "Unité d'achat sans contenance lue au kilo (R1 n° 3).",
    "K8d": "Brouillon numéroté : numéro retiré, gardé au compteur (R1 n° 4).",
    "K8e": "Ordre validé sans date : fin de son jour (R1 n° 5).",
    "K8f": "Numéro de lot à blancs : blancs → « _ » (R1 n° 8).",
    "K8g": "Entrée de réception de l'ERP Fil : sa réception retrouvée par (lot, date) (R1 n° 7).",
    "K8h": "Prix confirmé sans date : date de création du bon (R1).",
    "K9": "Prix connus à la date : à une date passée, opportunités et économies du Cockpit ne "
          "lisent que les réceptions jusqu'à cette date (D8 n° 6) — preuve : la route de Gestion "
          "MP rejouée avec ses coûts rendus bornés à la date redonne la valeur de PRO.",
    "P17": "Méthode « corrigée » seule : `methode` retiré des réglages du moteur.",
}  # fmt: skip


@dataclass
class Rapport:
    """Les lignes du rapport et le total à corriger."""

    lignes: list[str] = field(default_factory=list)
    a_corriger: int = 0
    par_classe: Counter[str] = field(default_factory=Counter)

    def titre(self, texte: str) -> None:
        """Un titre de section."""
        self.lignes += ["", texte.upper(), "-" * len(texte)]

    def __call__(self, texte: str = "") -> None:
        """Une ligne."""
        self.lignes.append(texte)


def ampleur(g: Any, p: Any) -> float | None:
    """L'écart absolu de deux nombres (sinon `None`)."""
    nombres = (int, float)
    if isinstance(g, nombres) and isinstance(p, nombres) and not isinstance(g, bool):
        return abs(float(g) - float(p))
    return None


def tableau(r: Rapport, titre: str, ecarts: Iterable[tuple[str, str | None, Any, Any]],
            comparees: dict[str, int]) -> None:  # fmt: skip
    """Par section : valeurs comparées, écarts par classe (et l'ampleur maximale)."""
    classes: dict[str, Counter[str]] = defaultdict(Counter)
    maxi: dict[tuple[str, str], float] = {}
    for section, classe, g, p in ecarts:
        nom = classe or "à corriger"
        classes[section][nom] += 1
        a = ampleur(g, p)
        if a is not None:
            maxi[(section, nom)] = max(maxi.get((section, nom), 0.0), a)
        r.par_classe[nom] += 1
        if classe is None:
            r.a_corriger += 1
    r(f"{titre} — section : comparées | expliquées par classe (ampleur max) | à corriger")
    for section in sorted(set(comparees) | set(classes)):
        c = classes.get(section, Counter())
        detail = ", ".join(
            f"{k} {n}" + (f" ({maxi[(section, k)]:.3g})" if (section, k) in maxi else "")
            for k, n in sorted(c.items()) if k != "à corriger"
        )  # fmt: skip
        r(f"  {section:<42} {comparees.get(section, 0):>9} | {detail or '—'} | "
          f"{c.get('à corriger', 0)}")  # fmt: skip


def detail_a_corriger(r: Rapport, ecarts: Iterable[tuple[str, str, Any, Any]], n: int = 40) -> None:
    """Les premiers écarts à corriger, en clair."""
    liste = list(ecarts)
    if liste:
        r(f"  À CORRIGER ({len(liste)}) :")
        for lieu, champ, g, p in liste[:n]:
            r(f"    {lieu} · {champ} : Gestion MP {str(g)[:80]} / PRO {str(p)[:80]}")


def corrections(r: Rapport) -> None:
    """Le tableau des corrections et traductions déclarées, avec leur compte."""
    r.titre("Corrections et traductions déclarées (écarts expliqués, toutes passes)")
    for code, texte in CORRECTIONS.items():
        r(f"  {code:<5} {r.par_classe.get(code, 0):>7}  {texte}")
