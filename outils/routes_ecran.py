"""Chaque appel de l'écran a sa route dans l'OpenAPI du serveur (S0, `make verifier-outils`).

Lit `frontend/src` (lecture seule, essais exclus) et relève le premier argument de chaque appel
`api.get|post|put|supprimer|envoyerFichier(…)`, `useLecture(…)` et `adresseApi(…)` : les
chaînes et gabarits qui commencent par « / » (dans un `cond ? '/a' : null`, chacune). Un
`${…}` vaut un segment quelconque ; la requête (`?…`) est ignorée. Chaque (méthode, chemin)
doit répondre à une route de l'OpenAPI (`/api` retiré), à paramètres près.

Un appel dont le chemin est une variable (`api.get(chemin)`) ne se vérifie pas ici : il est
compté et dit. Sortie 1 si un appel n'a pas de route ; 0 sinon.

    backend/.venv/bin/python outils/routes_ecran.py [--detail]
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
ECRAN = RACINE / "frontend" / "src"

APPELS = re.compile(
    r"\b(?P<qui>api\.(?:get|post|put|supprimer|envoyerFichier)|useLecture|adresseApi)"
    r"\s*(?:<[^()]*?>)?\s*\("
)
METHODES = {
    "api.get": "get",
    "useLecture": "get",
    "adresseApi": "get",
    "api.post": "post",
    "api.envoyerFichier": "post",
    "api.put": "put",
    "api.supprimer": "delete",
}
PROPRIETE = re.compile(r"""\broute\s*[:=]\s*\{?\s*(?P<lit>'/[^']*'|"/[^"]*"|`/[^`]*`)""")
"""`exporter={{ route: '/export/…' }}`, `<ExportExcel route="/export/…">` : des GET."""
CHAINE = re.compile(r"'(/[^']*)'|\"(/[^\"]*)\"|`(/[^`]*)`")
GABARIT = re.compile(r"\$\{[^}]*\}")


@dataclass(frozen=True)
class Appel:
    """Un appel relevé dans l'écran."""

    fichier: str
    ligne: int
    methode: str
    chemin: str


def premier_argument(texte: str, debut: int) -> str:
    """Le premier argument d'un appel (jusqu'à la virgule ou la parenthèse de même niveau)."""
    niveau, i, guillemet = 0, debut, ""
    while i < len(texte):
        c = texte[i]
        if guillemet:
            if c == "\\":
                i += 1
            elif c == guillemet:
                guillemet = ""
        elif c in "'\"`":
            guillemet = c
        elif c in "([{":
            niveau += 1
        elif c in ")]}":
            if niveau == 0:
                break
            niveau -= 1
        elif c == "," and niveau == 0:
            break
        i += 1
    return texte[debut:i]


def chemins(argument: str) -> list[str]:
    """Les chemins littéraux d'un argument (`${…}` → `{}`), sans requête."""
    trouves = []
    for m in CHAINE.finditer(argument):
        brut = next(g for g in m.groups() if g is not None)
        trouves.append(GABARIT.sub("{}", brut).split("?")[0].split("#")[0])
    return trouves


def relever(racine: Path = ECRAN) -> tuple[list[Appel], list[tuple[str, int]]]:
    """Les appels à chemin littéral, et ceux dont le chemin est une variable."""
    appels: list[Appel] = []
    variables: list[tuple[str, int]] = []
    for f in sorted([*racine.rglob("*.ts"), *racine.rglob("*.tsx")]):
        nom = str(f.relative_to(RACINE))
        if ".test." in f.name or "/essais/" in nom or f.name == "types.gen.ts":
            continue
        texte = f.read_text(encoding="utf-8")
        for m in APPELS.finditer(texte):
            argument = premier_argument(texte, m.end())
            ligne = texte.count("\n", 0, m.start()) + 1
            trouves = chemins(argument)
            if not trouves:
                if argument.strip():
                    variables.append((nom, ligne))
                continue
            methode = METHODES[m.group("qui")]
            appels.extend(Appel(nom, ligne, methode, c) for c in trouves)
        for m in PROPRIETE.finditer(texte):
            ligne = texte.count("\n", 0, m.start()) + 1
            appels.extend(Appel(nom, ligne, "get", c) for c in chemins(m.group("lit")))
    return appels, variables


def _segments(chemin: str) -> list[str]:
    return [x for x in chemin.split("/") if x]


def correspond(modele: str, chemin: str) -> bool:
    """Le chemin de l'écran répond-il au chemin de l'OpenAPI (`{x}` : un segment) ?"""
    a, b = _segments(modele), _segments(chemin)
    if len(a) != len(b):
        return False
    for x, y in zip(a, b, strict=True):
        if x.startswith("{") or y == "{}" or y.startswith("{}") or y.endswith("{}"):
            continue
        if x != y:
            return False
    return True


def routes_du_serveur() -> list[tuple[str, str]]:
    """(méthode, chemin sans `/api`) de chaque route de l'OpenAPI."""
    os.environ.setdefault("GESTIONMPPRO_TACHES", "0")
    from gestion_mp_pro.main import creer_application

    schema = creer_application().openapi()
    return [
        (methode, chemin.removeprefix("/api"))
        for chemin, operations in schema["paths"].items()
        for methode in operations
    ]


def sans_route(appels: list[Appel], routes: list[tuple[str, str]]) -> list[Appel]:
    """Les appels qu'aucune route ne sert."""
    return [
        a for a in appels if not any(m == a.methode and correspond(c, a.chemin) for m, c in routes)
    ]


def main(arguments: list[str]) -> int:
    """Vérifie et dit le résultat."""
    appels, variables = relever()
    manquants = sans_route(appels, routes_du_serveur())
    sortie = sys.stdout
    sortie.write(
        f"Appels de l'écran : {len(appels)} à chemin écrit, {len(variables)} à chemin variable "
        "(non vérifiés ici).\n"
    )
    if "--detail" in arguments:
        for f, n in variables:
            sortie.write(f"  variable : {f}:{n}\n")
    for a in manquants:
        sortie.write(f"SANS ROUTE : {a.methode.upper()} {a.chemin} ({a.fichier}:{a.ligne})\n")
    if manquants:
        sortie.write(f"{len(manquants)} appel(s) de l'écran sans route dans l'OpenAPI.\n")
        return 1
    sortie.write("Chaque appel écrit de l'écran a sa route dans l'OpenAPI.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
