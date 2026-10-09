"""Socle de la vérification indépendante des chiffres (lot V1) : relevé, tolérances, dates.

Aucun import du paquet `gestion_mp_pro` (critère A5) : ce module et ses voisins `verif_*.py` ne
connaissent la base que par le SQL et l'application que par ses réponses HTTP.

Tolérances (PLAN-DE-RECETTE § 6) : 0,001 kg ; 0,01 MAD ; 1e-6 en relatif sur les ratios et les
prix unitaires. Un écart se juge `|a − b| > max(absolu, 1e-6 × max(|a|, |b|))`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Protocol

KG = 0.001
MAD = 0.01
RELATIF = 1e-6
POUSSIERE = 0.0005
"""Ce qui est sous le demi-gramme n'est pas du stock (soldes en NUMERIC(14,3))."""
MONTRES = 10
"""Écarts montrés au plus par famille (le total est dit)."""


class Acces(Protocol):
    """Ce que la vérification lit : l'application (HTTP) et la base (SQL)."""

    def get(self, chemin: str, **params: Any) -> Any:
        """La réponse JSON d'une lecture de l'API (`/api` + chemin), en direction."""
        ...

    def sql(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Les lignes d'une requête SQL (décimaux rendus en `float`)."""
        ...


def ecart(a: float | None, b: float | None, absolu: float = MAD) -> bool:
    """Deux nombres diffèrent-ils au-delà de la tolérance ?"""
    x, y = float(a or 0.0), float(b or 0.0)
    return abs(x - y) > max(absolu, RELATIF * max(abs(x), abs(y)))


@dataclass
class Famille:
    """Une famille de vérifications : combien de cas jugés, et les écarts trouvés."""

    nom: str
    cas: int = 0
    ecarts: list[str] = field(default_factory=list)


@dataclass
class Releve:
    """Toutes les vérifications d'une base, famille par famille."""

    familles: dict[str, Famille] = field(default_factory=dict)

    def famille(self, nom: str) -> Famille:
        """La famille `nom` (créée vide au premier usage, pour qu'elle figure au relevé)."""
        return self.familles.setdefault(nom, Famille(nom))

    def juger(self, nom: str, sujet: str, juste: bool, detail: str = "") -> bool:
        """Compte un cas ; s'il est faux, note l'écart (`sujet : detail`)."""
        f = self.famille(nom)
        f.cas += 1
        if not juste:
            f.ecarts.append(f"{sujet} : {detail}" if detail else sujet)
        return juste

    def comparer(
        self, nom: str, sujet: str, ecran: float | None, base: float | None, absolu: float = MAD
    ) -> bool:
        """Compte un cas : le chiffre de l'écran contre celui recompté dans la base."""
        juste = not ecart(ecran, base, absolu)
        detail = f"écran {_nombre(ecran)}, recompté {_nombre(base)}"
        return self.juger(nom, sujet, juste, detail)

    @property
    def cas(self) -> int:
        """Le nombre total de vérifications faites."""
        return sum(f.cas for f in self.familles.values())

    @property
    def nb_ecarts(self) -> int:
        """Le nombre total d'écarts."""
        return sum(len(f.ecarts) for f in self.familles.values())

    def ecarts_de(self, nom: str) -> list[str]:
        """Les écarts d'une famille (vide si elle n'a rien trouvé ou n'existe pas)."""
        return list(self.familles[nom].ecarts) if nom in self.familles else []

    def lignes(self) -> list[str]:
        """Le relevé lisible : une ligne ✓/✗ par famille, ses premiers écarts, le total."""
        sortie: list[str] = []
        for f in self.familles.values():
            signe = "✓" if not f.ecarts else "✗"
            dit = f" — {len(f.ecarts)} écart(s)" if f.ecarts else ""
            sortie.append(f"{signe} {f.nom} : {f.cas} vérification(s){dit}")
            sortie.extend(f"      {e}" for e in f.ecarts[:MONTRES])
        sortie.append(
            f"Total : {self.cas} vérifications, {len(self.familles)} familles, "
            f"{self.nb_ecarts} écart(s)."
        )
        return sortie


def _nombre(x: float | None) -> str:
    """Un nombre lisible dans un écart (None dit « rien »)."""
    return "rien" if x is None else f"{float(x):.6g}"


def fin_de_mois(jour: date) -> date:
    """Le dernier jour du mois de `jour`."""
    suivant = (jour.replace(day=28) + timedelta(days=4)).replace(day=1)
    return suivant - timedelta(days=1)


def dates_de_reference(aujourdhui: date, nombre: int = 13) -> list[date]:
    """Les 13 dates (A6) : la fin de chacun des 12 derniers mois clos, puis le jour même."""
    dates: list[date] = []
    jour = aujourdhui.replace(day=1) - timedelta(days=1)
    for _ in range(nombre - 1):
        dates.append(jour)
        jour = jour.replace(day=1) - timedelta(days=1)
    return [*reversed(dates), aujourdhui]


def par_cle(lignes: Iterable[dict[str, Any]], cle: str) -> dict[Any, dict[str, Any]]:
    """Une liste de lignes JSON rangée par l'une de ses clés."""
    return {x[cle]: x for x in lignes}


def somme_par(
    lignes: Iterable[tuple[Any, ...]], cle: Callable[[tuple[Any, ...]], Any] = lambda r: r[0]
) -> dict[Any, float]:
    """Σ de la dernière colonne, par clé (par défaut la première colonne)."""
    total: dict[Any, float] = {}
    for r in lignes:
        k = cle(r)
        total[k] = total.get(k, 0.0) + float(r[-1] or 0.0)
    return total


def cours_de(devise: str | None, cours: float | None, taux: dict[str, float]) -> float:
    """Le cours d'un montant : 1 en MAD ; sinon celui qu'il porte, à défaut celui du jour."""
    if not devise or devise == "MAD":
        return 1.0
    return float(cours or taux.get(devise, 1.0) or 1.0)
