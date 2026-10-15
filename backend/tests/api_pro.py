"""Lecture du catalogue `docs/API-PRO.md` § 1 : numéro, méthode, chemin et rôles de chaque route.

Sert aux essais des droits (lot S2) : la garde `droit(...)` de chaque route servie doit dire
les mêmes rôles que le catalogue ; un droit hérité de Gestion MP se vérifie sur le catalogue
**et**, dès que la route est servie, par l'appel réel.

Rôles : `P` public, `D`, `A`, `L`, `T`, `C` = D, A, L, `Tous` = D, A, L, T ; le texte entre
parenthèses est ignoré ; « idem » reprend les rôles de la ligne précédente ; une route sans
lettre (l'historique : « droit de lecture de la fiche ») a des rôles `None`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from gestion_mp_pro.config import RACINE

DOCUMENT = RACINE / "docs" / "API-PRO.md"
LETTRES = {
    "D": {"direction"},
    "A": {"achats"},
    "L": {"alimentation"},
    "T": {"administrateur"},
    "C": {"direction", "achats", "alimentation"},
    "Tous": {"direction", "achats", "alimentation", "administrateur"},
}
LIGNE = re.compile(r"^\|\s*(\d+)\s*\|\s*(GET|POST|PUT|DELETE)\s*\|\s*`([^`]+)`\s*\|([^|]*)\|")
AJOUTS = {("GET", "/acces"): {"administrateur"}, ("GET", "/acces/qr"): {"administrateur"}}
"""API-PRO § 1.24 : « GET /acces et GET /acces/qr sont ouverts aussi à T »."""


@dataclass(frozen=True)
class RouteCatalogue:
    """Une route du catalogue."""

    numero: int
    methode: str
    chemin: str
    publique: bool
    roles: frozenset[str] | None


def gabarit(chemin: str) -> str:
    """Le chemin sans les noms de paramètres : `/utilisateurs/{}` (et sans `/api`)."""
    return re.sub(r"\{[^}]*\}", "{}", chemin.removeprefix("/api"))


def _roles(texte: str) -> tuple[bool, frozenset[str] | None]:
    """Publique ? et les rôles d'une cellule « Rôles »."""
    sans_parentheses = re.sub(r"\([^)]*\)", " ", texte)
    jetons = re.findall(r"\b(Tous|P|D|A|L|T|C)\b", sans_parentheses)
    if not jetons:
        return False, None
    roles: set[str] = set()
    for jeton in jetons:
        roles |= LETTRES.get(jeton, set())
    return "P" in jetons, frozenset(roles)


@lru_cache(maxsize=1)
def catalogue() -> dict[tuple[str, str], RouteCatalogue]:
    """`{(méthode, gabarit): route}` pour toutes les routes de API-PRO § 1."""
    texte = DOCUMENT.read_text(encoding="utf-8")
    section = texte.split("## 1. Catalogue PRO", 1)[1].split("\n## 2.", 1)[0]
    routes: dict[tuple[str, str], RouteCatalogue] = {}
    precedent: tuple[bool, frozenset[str] | None] = (False, None)
    for ligne in section.splitlines():
        trouve = LIGNE.match(ligne)
        if trouve is None:
            continue
        numero, methode, chemin, cellule = trouve.groups()
        publique, roles = precedent if cellule.strip() == "idem" else _roles(cellule)
        precedent = (publique, roles)
        cle = (methode, gabarit(chemin))
        if roles is not None and cle in AJOUTS:
            roles = roles | AJOUTS[cle]
        routes[cle] = RouteCatalogue(int(numero), methode, chemin, publique, roles)
    return routes


def route(methode: str, chemin: str) -> RouteCatalogue:
    """La route du catalogue (erreur claire si le chemin n'y est pas)."""
    cle = (methode, gabarit(chemin))
    assert cle in catalogue(), f"{methode} {chemin} absent de docs/API-PRO.md § 1"
    return catalogue()[cle]


TECHNIQUES = frozenset({3, 4, 5, 6, *range(11, 26), *range(43, 56), 243, 259})
"""Les routes où l'administrateur technique est nommé (API-PRO § 4, § 1.24)."""
