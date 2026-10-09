"""Parité : les données que chaque moteur reçoit, et les traductions déclarées de la reprise.

Les `Donnees` que le dépôt de Gestion MP charge de la copie (`D0`) et celles que le chargeur de
PRO lit dans la base reprise (`Dpro`) sont mises au même format (celui des jeux de S3) et
comparées feuille par feuille. Chaque différence doit être l'une des traductions déclarées,
reconnue par une **règle qui vérifie la valeur** (forme et ampleur), jamais par une liste
d'excuses :

| Code | Traduction | Règle |
|---|---|---|
| ORDRE | ordre de lecture des recettes | même multiensemble, autre ordre |
| K1 | arrondi à l'échelle de la colonne (MODELE-DONNEES § 10.2) | Dpro = arrondi(D0, échelle) |
| K8a | prix des sorties, transferts, retours machine à 0 (R1 n° 1) | type de sortie et Dpro = 0 |
| K8b | réception en deux devises scindée (R1 n° 2) | `D0s` : dépôt de Gestion MP, copie scindée |
| K8c | unité d'achat sans contenance → kg (R1 n° 3) | contenance 0 et unité vide |
| K8d | brouillon numéroté : numéro retiré (R1 n° 4) | statut Brouillon et « brouillon n° id » |
| K8e | ordre validé sans date : fin de son jour (R1 n° 5) | `None` → jour T23:59:59.999999 |
| K8i | entrée en devise sans cours : cours du jour figé (V2) | entrée, cours 0, Dpro = cours D0 |
| P17 | méthode de calcul : la seule « corrigée » | `methode = corrigee` absent de PRO |

`chaine()` rend les jeux intermédiaires D0 → D1 → … → Dpro (chaque traduction ajoutée à la
précédente, la valeur prise dans PRO seulement là où sa règle la reconnaît) : le moteur de
Gestion MP les recalcule, et un écart de sortie n'est expliqué par une traduction que si le
jeu qui l'ajoute redonne la valeur de PRO.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

Chemin = tuple[str | int, ...]
ORDRE_DES_CLASSES = ("K8b", "ORDRE", "K1", "K8a", "K8c", "K8d", "K8e", "K8i", "P17")
TITRES = {
    "ORDRE": "ordre de lecture des recettes (même contenu)",
    "K1": "arrondi à l'échelle des colonnes (MODELE-DONNEES § 10.2)",
    "K8a": "prix des sorties, transferts et retours machine non repris (R1 n° 1)",
    "K8b": "réception payée en deux devises scindée, une par devise (R1 n° 2)",
    "K8c": "unité d'achat sans contenance lue au kilo (R1 n° 3)",
    "K8d": "brouillon numéroté : numéro retiré (R1 n° 4)",
    "K8e": "ordre validé sans date : fin de son jour (R1 n° 5)",
    "K8i": "entrée en devise sans cours : cours du jour de la reprise figé (V2)",
    "P17": "méthode de calcul « corrigée » seule (P17)",
}
ECHELLES: dict[str, int] = {
    "commandes/*/lignes/*/contenance_commande": 3,
    "commandes/*/lignes/*/quantite_commandee": 3,
    "receptions/*/lignes/*/quantite_commandee": 3,
    "dossiers_import/*/facture_montant": 2,
    "dossiers_import/*/lignes/*/valeur_devise": 2,
    "mouvements/*/quantite": 3,
    "ordres/*/fabrications/*/*": 3,
}
"""Échelle PRO (QUANTITE 3, MONTANT 2, SURFACE 3) des champs que la reprise arrondit."""
SORTIES_SANS_PRIX = {"SORTIE_PROD", "RETOUR_PRODUCTION", "TRANSFERT_MAGASIN"}
LISTES_ORDONNEES = (re.compile(r"^recettes$"), re.compile(r"^versions_recette/[^/]+/\d+/lignes$"))
BROUILLON = re.compile(r"^brouillon n° \d+$")


def arrondi(v: float, echelle: int) -> float:
    """L'arrondi de la reprise (`ROUND_HALF_UP` sur l'écriture décimale du flottant)."""
    pas = Decimal(1).scaleb(-echelle)
    return float(Decimal(repr(v)).quantize(pas, rounding=ROUND_HALF_UP))


def motif(chemin: Chemin) -> str:
    """Le chemin avec ses indices remplacés par `*` (clé de la table des échelles)."""
    return "/".join("*" if isinstance(x, int) else str(x) for x in chemin)


def texte(chemin: Chemin) -> str:
    """Le chemin lisible."""
    return "/".join(map(str, chemin))


@dataclass
class Contexte:
    """Ce que les règles lisent de Gestion MP."""

    d0_scinde: dict[str, Any] | None = None
    """K8b : les `Donnees` du dépôt de Gestion MP relues sur une copie où chaque réception
    payée en deux devises est scindée (`parite_chaine_base.k8b`) ; `None` : pas de K8b."""
    scindees: int = 0
    """Réceptions nées de la scission dans cette copie."""


def lire_contexte(d0_scinde: dict[str, Any] | None = None, scindees: int = 0) -> Contexte:
    """Le contexte des règles (K8b : les données de la copie scindée)."""
    return Contexte(d0_scinde=d0_scinde, scindees=scindees)


@dataclass(frozen=True)
class Ecart:
    """Une différence de donnée : son chemin, les deux valeurs, sa classe (ou `None`)."""

    chemin: Chemin
    gmp: Any
    pro: Any
    classe: str | None


def _ordre(chemin: Chemin, a: list[Any], b: list[Any]) -> bool:
    """Une liste dont seul l'ordre change (même multiensemble)."""
    if not any(r.match(texte(chemin)) for r in LISTES_ORDONNEES) or len(a) != len(b):
        return False
    cle = lambda x: json.dumps(x, sort_keys=True)  # noqa: E731
    return sorted(map(cle, a)) == sorted(map(cle, b))


def _k1(chemin: Chemin, a: Any, b: Any, d0: dict[str, Any]) -> bool:
    """Arrondi de la reprise (et `total_devise` = quantité arrondie × prix, comme le chargeur)."""
    m = motif(chemin)
    if type(a) is int and type(b) is float:
        return float(a) == b
    if not isinstance(a, float) or not isinstance(b, float):
        return False
    if m in ECHELLES:
        return arrondi(a, ECHELLES[m]) == b
    if m == "mouvements/*/total_devise":
        x = d0["mouvements"][chemin[1]]
        return arrondi(x["quantite"], 3) * x["prix_unite"] == b
    return False


def _k8(chemin: Chemin, a: Any, b: Any, d0: dict[str, Any], ctx: Contexte) -> str | None:
    """Les traductions de la reprise de R1 (décisions 1 à 5), chacune vérifiée."""
    m = motif(chemin)
    if m in ("mouvements/*/prix_unite", "mouvements/*/total_devise"):
        return (
            "K8a" if d0["mouvements"][chemin[1]]["type"] in SORTIES_SANS_PRIX and b == 0 else None
        )
    if m == "mouvements/*/cours" and a == 0:
        x = d0["mouvements"][chemin[1]]
        jour = d0["parametres"]["cours"].get(x["devise"])
        return "K8i" if x["devise"] != "MAD" and x["prix_unite"] and b == jour else None
    if m == "articles/*/unite_commande":
        return "K8c" if d0["articles"][chemin[1]]["contenance_commande"] == 0 and b == "" else None
    if m == "receptions/*/numero":
        statut = d0["receptions"][chemin[1]]["statut"]
        return "K8d" if statut == "Brouillon" and a and BROUILLON.match(b) else None
    if m == "ordres/*/valide_le" and a is None and isinstance(b, str):
        return "K8e" if b == f"{d0['ordres'][chemin[1]]['date']}T23:59:59.999999" else None
    return None


def classer(chemin: Chemin, a: Any, b: Any, d0: dict[str, Any], ctx: Contexte) -> str | None:
    """La traduction qui explique une différence de donnée, ou `None` (à corriger)."""
    if isinstance(a, list) and isinstance(b, list):
        return "ORDRE" if _ordre(chemin, a, b) else None
    if _k1(chemin, a, b, d0):
        return "K1"
    if chemin == ("parametres", "methode") and a == "corrigee" and b is _ABSENT:
        return "P17"
    return _k8(chemin, a, b, d0, ctx)


class _Absent:
    """Une clé présente d'un seul côté."""

    def __repr__(self) -> str:
        return "— (absent)"


_ABSENT = _Absent()


def _feuilles(a: Any, b: Any, chemin: Chemin) -> Iterator[tuple[Chemin, Any, Any]]:
    """Les différences feuille par feuille ; une liste réordonnée sort entière."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            yield from _feuilles(a.get(k, _ABSENT), b.get(k, _ABSENT), (*chemin, k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b) and not any(r.match(texte(chemin)) for r in LISTES_ORDONNEES):
            for i, (x, y) in enumerate(zip(a, b, strict=True)):
                yield from _feuilles(x, y, (*chemin, i))
        elif a != b:
            yield (chemin, a, b)
    elif a != b or type(a) is not type(b):
        yield (chemin, a, b)


def ecarts(d0: dict[str, Any], dpro: dict[str, Any], ctx: Contexte) -> list[Ecart]:
    """Toutes les différences de données, chacune classée.

    K8b d'abord : ce qui sépare `D0` de `D0s` (le dépôt de Gestion MP lui-même, sur la copie
    scindée) est la scission ; le reste se compare de `D0s` à `Dpro`, chemins de `D0s`."""
    base, sortie = d0, []
    if ctx.d0_scinde is not None:
        base = ctx.d0_scinde
        sortie = [Ecart(c, a, b, "K8b") for c, a, b in _feuilles(d0, base, ())]
    return sortie + [
        Ecart(c, a, b, classer(c, a, b, base, ctx)) for c, a, b in _feuilles(base, dpro, ())
    ]


def _poser(donnees: dict[str, Any], chemin: Chemin, valeur: Any) -> None:
    cible: Any = donnees
    for k in chemin[:-1]:
        cible = cible[k]
    if valeur is _ABSENT:
        del cible[chemin[-1]]
    else:
        cible[chemin[-1]] = copy.deepcopy(valeur)


def chaine(d0: dict[str, Any], liste: list[Ecart]) -> list[tuple[str, dict[str, Any]]]:
    """Les jeux D1 … Dn : chacun ajoute une classe à la précédente (D0 non compris)."""
    jeux: list[tuple[str, dict[str, Any]]] = []
    courant = copy.deepcopy(d0)
    for classe in ORDRE_DES_CLASSES:
        for e in liste:
            if e.classe == classe:
                _poser(courant, e.chemin, e.pro)
        jeux.append((classe, copy.deepcopy(courant)))
    return jeux


def resume(liste: list[Ecart]) -> dict[str, dict[str, int]]:
    """Par classe (`None` : à corriger), le nombre de différences par motif de chemin."""
    sortie: dict[str, dict[str, int]] = {}
    for e in liste:
        par_motif = sortie.setdefault(e.classe or "à corriger", {})
        par_motif[motif(e.chemin)] = par_motif.get(motif(e.chemin), 0) + 1
    return sortie


def sans_index(donnees: dict[str, Any]) -> dict[str, Any]:
    """Les `Donnees` PRO au format des jeux, sans les champs hors constructeur (index)."""
    return {k: v for k, v in donnees.items() if not k.startswith("_") and k != "derniere_date"}
