"""La matrice des droits, générée depuis les routes (API-PRO § 4 ; ARCHITECTURE § 5.2).

Chaque route de l'API est soit **publique** (liste fermée `PUBLIQUES` : routes 1, 2, 8, 9, 10,
22), soit gardée par `droit(...)`. La matrice dit, pour chaque route et chaque rôle (anonyme
compris), le résultat attendu : `ok` (la garde laisse passer), `401` ou `403`. Elle est
versionnée dans `backend/tests/matrice_droits.csv` (`make matrice`) et rejouée par l'essai.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from gestion_mp_pro.securite.droits import ATTRIBUT_ROLES, TOUS

PUBLIQUES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/sante"),
        ("GET", "/api/etat"),
        ("GET", "/api/visages"),
        ("POST", "/api/installation"),
        ("POST", "/api/connexion"),
        ("POST", "/api/appareils/enroler"),
    }
)
"""Les seules routes sans `droit(...)` (API-PRO § 4)."""

COLONNES = ("methode", "chemin", "anonyme", *(r.value for r in TOUS))
OK, NON_CONNECTE, REFUSE = "ok", "401", "403"


@dataclass(frozen=True)
class LigneMatrice:
    """Une route : méthode, chemin, publique ou rôles permis (vide = garde absente)."""

    methode: str
    chemin: str
    publique: bool
    roles: frozenset[str]
    domaine: str = ""

    def attendu(self, role: str | None) -> str:
        """`ok`, `401` ou `403` pour un rôle (`None` : sans session)."""
        if self.publique:
            return OK
        if role is None:
            return NON_CONNECTE
        return OK if role in self.roles else REFUSE

    def en_ligne(self) -> list[str]:
        """La ligne CSV."""
        return [self.methode, self.chemin, self.attendu(None), *(self.attendu(r) for r in TOUS)]


def _sans_convertisseur(chemin: str) -> str:
    """`/fournisseurs/{ident:int}` → `/fournisseurs/{ident}` (le chemin de l'OpenAPI)."""
    return re.sub(r"\{(\w+):\w+\}", r"{\1}", chemin)


def _deplier(routes: Iterable[Any]) -> Iterator[tuple[str, APIRoute]]:
    """Les routes et leur chemin complet, routeurs inclus dépliés (inclusion paresseuse) ; un
    convertisseur de chemin (`{ident:int}`, qui départage deux routes) n'est pas écrit."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield _sans_convertisseur(route.path), route
            continue
        candidats = getattr(route, "effective_candidates", None)
        if candidats is None:
            continue
        for candidat in candidats():
            originale = getattr(candidat, "original_route", None)
            if isinstance(originale, APIRoute):
                yield _sans_convertisseur(str(candidat.path)), originale
            else:
                yield from _deplier([candidat])


def routes_api(app: FastAPI) -> Iterator[tuple[str, APIRoute]]:
    """Les routes de l'API (sous `/api`) avec leur chemin complet, hors service de l'écran."""
    for chemin, route in _deplier(app.routes):
        if chemin.startswith("/api/"):
            yield chemin, route


def _gardes(dependant: Any) -> Iterator[frozenset[str]]:
    """Les rôles de chaque garde `droit(...)` rencontrée dans l'arbre des dépendances."""
    for dep in dependant.dependencies:
        roles = getattr(dep.call, ATTRIBUT_ROLES, None)
        if isinstance(roles, frozenset):
            yield roles
        yield from _gardes(dep)


def roles_de(route: APIRoute) -> frozenset[str] | None:
    """Les rôles permis par la route (intersection de ses gardes), `None` sans garde."""
    gardes = list(_gardes(route.dependant))
    if not gardes:
        return None
    permis = gardes[0]
    for autre in gardes[1:]:
        permis &= autre
    return permis


def matrice(app: FastAPI) -> list[LigneMatrice]:
    """La matrice de toutes les routes de l'API, triée par chemin puis méthode."""
    lignes = []
    for chemin, route in routes_api(app):
        roles = roles_de(route)
        for methode in sorted(route.methods or ()):
            if methode == "HEAD":
                continue
            publique = (methode, chemin) in PUBLIQUES
            lignes.append(
                LigneMatrice(
                    methode,
                    chemin,
                    publique,
                    roles or frozenset(),
                    str(route.tags[0]) if route.tags else "",
                )
            )
    return sorted(lignes, key=lambda x: (x.chemin, x.methode))


def sans_garde(app: FastAPI) -> list[str]:
    """Les routes ni publiques ni gardées (doit rester vide)."""
    return [f"{x.methode} {x.chemin}" for x in matrice(app) if not x.publique and not x.roles]


def en_csv(lignes: list[LigneMatrice]) -> str:
    """La matrice en CSV (`;`), une ligne d'en-tête."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\n")
    ecrivain.writerow(COLONNES)
    ecrivain.writerows(x.en_ligne() for x in lignes)
    return tampon.getvalue()


def domaines_permis(app: FastAPI, role: str) -> list[dict[str, Any]]:
    """Pour `/contexte` : les domaines de l'API où le rôle lit ou écrit quelque chose."""
    vus: dict[str, dict[str, Any]] = {}
    for x in matrice(app):
        if x.publique or role not in x.roles or not x.domaine:
            continue
        entree = vus.setdefault(
            x.domaine, {"domaine": x.domaine, "lecture": False, "ecriture": False}
        )
        entree["lecture" if x.methode == "GET" else "ecriture"] = True
    return list(vus.values())
