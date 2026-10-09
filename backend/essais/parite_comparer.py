"""Parité : comparer deux sorties, aux tolérances déclarées, et expliquer chaque écart.

Tolérances (PLAN-DE-RECETTE-PRO § 7.5), sur les valeurs brutes, avant tout arrondi
d'affichage : quantités 0,001 ; montants 0,01 ou 1e-6 relatif (le plus grand) ; prix, coûts
unitaires et CMUP 1e-6 relatif ; ratios 1e-6 absolu ; entiers, textes, dates : exacts.

Explication (§ 7.6) : un écart n'est expliqué par une traduction que si le moteur de Gestion
MP, recalculé sur les données où cette traduction (et les précédentes) est faite, redonne la
valeur de PRO — forme et ampleur. Sinon il est « à corriger ».
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

Chemin = tuple[str, ...]

CLES: dict[str, tuple[str, ...]] = {
    "stock": ("reference",),
    "nomenclature": ("qualite", "reference"),
    "controle_recettes": ("qualite",),
    "performance_receptions": ("numero",),
    "scorecard": ("fournisseur",),
    "evolution_bobines": ("reference", "fournisseur"),
    "lots": ("reference", "lot"),
    "ordres": ("numero_of",),
    "valorisation": ("reference",),
    "controles": ("code",),
    "plan_achat/lignes": ("reference",),
    "plan_achat/fournisseurs": ("fournisseur",),
    "pesees": ("numero", "reference", "lot_fournisseur"),
    "historique_prix": ("date_bc", "numero_bc", "reference", "quantite"),
}
"""Les listes rangées par clé (un élément en plus ou en moins se voit par son nom ; une clé
répétée prend son rang : « clé #2 »)."""

PRIX = re.compile(r"prix|cout_unit|cmup|unitaire|pu_|_unite$|revient_unite|valeur_unite")
MONTANT = re.compile(
    r"mad|montant|valeur|budget|total|charges|tva|marchandise|decaisse|surcout|revient|cout"
)
RATIO = re.compile(
    r"pct|part|taux|ratio|otif|cv_|coef|pourcent|score|on_time|in_full|in_spec|fraction|perte"
)


class _Absent:
    def __repr__(self) -> str:
        return "— (absent)"


ABSENT = _Absent()


def _nombre(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool)


def egal(champ: str, a: Any, b: Any) -> bool:  # noqa: PLR0911
    """Égalité à la tolérance du champ (§ 7.5)."""
    if not (_nombre(a) and _nombre(b)):
        return bool(a == b and type(a) is type(b))
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    ecart, grand = abs(a - b), max(abs(a), abs(b))
    if RATIO.search(champ) and not MONTANT.search(champ):
        return ecart <= 1e-6
    if PRIX.search(champ):
        return ecart <= max(1e-9, 1e-6 * grand)
    if MONTANT.search(champ):
        return ecart <= max(0.01, 1e-6 * grand)
    return ecart <= 1e-3


def _cle(element: dict[str, Any], noms: tuple[str, ...]) -> str:
    return " | ".join(str(element.get(n)) for n in noms)


def ranger(sortie: Any, chemin: str = "") -> Any:
    """Les listes de `CLES` rangées en dicts par clé (sinon gardées dans l'ordre)."""
    if isinstance(sortie, dict):
        return {k: ranger(v, f"{chemin}/{k}" if chemin else str(k)) for k, v in sortie.items()}
    if isinstance(sortie, list):
        valeurs = [ranger(v, f"{chemin}/*") for v in sortie]
        noms = CLES.get(chemin)
        if noms and all(isinstance(v, dict) for v in valeurs):
            vus: dict[str, int] = {}
            ranges = {}
            for v in valeurs:
                cle = _cle(v, noms)
                vus[cle] = vus.get(cle, 0) + 1
                ranges[cle if vus[cle] == 1 else f"{cle} #{vus[cle]}"] = v
            return ranges
        return valeurs
    return sortie


def champ_de(chemin: Chemin) -> str:
    """Le nom du champ d'une feuille : le dernier élément qui n'est ni un indice ni une clé."""
    for x in reversed(chemin):
        if not x.isdigit() and " | " not in x and not re.match(r"^\d{4}-\d\d", x):
            return x
    return chemin[0] if chemin else ""


def lire(sortie: Any, chemin: Chemin) -> Any:
    """La valeur au chemin, ou `ABSENT`."""
    x = sortie
    for k in chemin:
        if isinstance(x, dict) and k in x:
            x = x[k]
        elif isinstance(x, list) and k.isdigit() and int(k) < len(x):
            x = x[int(k)]
        else:
            return ABSENT
    return x


@dataclass
class Bilan:
    """Ce qu'une comparaison a vu : feuilles comparées, écarts et leur classe."""

    comparees: int = 0
    ecarts: list[tuple[Chemin, Any, Any]] = field(default_factory=list)


def _comparer(a: Any, b: Any, chemin: Chemin, bilan: Bilan, exact: bool) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            _comparer(a.get(k, ABSENT), b.get(k, ABSENT), (*chemin, str(k)), bilan, exact)
        return
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            _comparer(x, y, (*chemin, str(i)), bilan, exact)
        return
    bilan.comparees += 1
    pareil = (a == b and type(a) is type(b)) if exact else egal(champ_de(chemin), a, b)
    if not pareil:
        bilan.ecarts.append((chemin, a, b))


def comparer(a: Any, b: Any, *, exact: bool = False, chemin: Chemin = ()) -> Bilan:
    """Les feuilles comparées et les écarts (aux tolérances, ou à l'égalité exacte)."""
    bilan = Bilan()
    _comparer(a, b, chemin, bilan, exact)
    return bilan


@dataclass
class Explique:
    """Un écart et sa classe (`None` : à corriger)."""

    chemin: Chemin
    gmp: Any
    pro: Any
    classe: str | None


def expliquer(
    ecarts: list[tuple[Chemin, Any, Any]], chaine: Sequence[tuple[str, Any]]
) -> list[Explique]:
    """La première traduction de la chaîne dont le recalcul redonne la valeur de PRO."""
    sortie = []
    for chemin, a, b in ecarts:
        champ = champ_de(chemin)
        classe = next(
            (code for code, c in chaine if _meme(champ, lire(c, chemin), b)),
            None,
        )
        sortie.append(Explique(chemin, a, b, classe))
    return sortie


def _meme(champ: str, x: Any, y: Any) -> bool:
    if isinstance(x, dict | list) or isinstance(y, dict | list):
        return not comparer(x, y).ecarts
    return egal(champ, x, y)


def sections(ecarts: list[Explique]) -> dict[str, dict[str, int]]:
    """Par section, le nombre d'écarts par classe."""
    sortie: dict[str, dict[str, int]] = {}
    for e in ecarts:
        par_classe = sortie.setdefault(e.chemin[0], {})
        nom = e.classe or "à corriger"
        par_classe[nom] = par_classe.get(nom, 0) + 1
    return sortie


def feuilles_par_section(a: Any) -> Iterator[tuple[str, int]]:
    """Le nombre de feuilles de chaque section (ce qui est comparé)."""
    for k, v in a.items():
        yield k, comparer(v, v).comparees
