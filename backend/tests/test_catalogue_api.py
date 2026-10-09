"""L'OpenAPI servi est la forme exécutable de `docs/API-PRO.md` § 1 (API-PRO, en tête ; LOTS § 2).

- Chaque opération servie sous `/api` est au catalogue (méthode, chemin) ; ses rôles déclarés
  (la garde `droit(...)`, ou publique) sont ceux du catalogue ; elle a son `summary`, une seule
  étiquette (le domaine), une réponse de succès décrite (schéma JSON non vide, ou un autre type
  de contenu, ou 204), et déclare les refus de sa garde (401 hors routes publiques, 403 si un
  rôle en est exclu).
- Les routes du catalogue **pas encore servies** sont listées à part, chacune avec le lot qui
  doit la livrer (`docs/LOTS-DE-TRAVAIL.md`) : sautées tant que la recette finale n'est pas
  atteinte (`docs/RECETTE.md`, lot V5), en échec ensuite. Une route que nul lot ne livre est en
  échec tout de suite.
"""

from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from typing import Any

import pytest
from api_pro import catalogue, gabarit
from fastapi import FastAPI

from gestion_mp_pro.config import RACINE
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.securite.matrice import matrice

LOTS = RACINE / "docs" / "LOTS-DE-TRAVAIL.md"
RECETTE = RACINE / "docs" / "RECETTE.md"
METHODES = ("get", "post", "put", "delete", "patch")
TOUS = frozenset(r.value for r in Role)

_NUMEROS = re.compile(r"(?<![/\w])(\d+)(?:–(\d+))?(?![/\w])")
_LIGNE_DE_LOT = re.compile(r"^\| \*\*([A-Z]\d+)\*\* \|[^|]*\|([^|]*)\|", re.MULTILINE)
_SECTION = re.compile(r"^### ([A-Z]\d+) — ", re.MULTILINE)
_ROUTES = re.compile(r"routes?\s+(\d+(?:–\d+)?(?:\s*(?:,|et)\s*\d+(?:–\d+)?)*)")


def numeros(texte: str) -> set[int]:
    """Les numéros de route d'un texte : « 23–42, 57–81 » ; entre parenthèses, joints par « / »
    (« 133/164/234 (environnement commun) ») ou collés à une lettre (« D7 ») : ignorés."""
    trouves: set[int] = set()
    for debut, fin in _NUMEROS.findall(re.sub(r"\([^)]*\)", " ", texte)):
        trouves.update(range(int(debut), int(fin or debut) + 1))
    return trouves


@lru_cache(maxsize=1)
def lots_des_routes() -> dict[int, tuple[str, ...]]:
    """N° de route → lots qui la livrent : table des lots D (§ 2, colonne « Routes ») et lignes
    « routes … » des sections des autres lots (S2, S4, C1…), hors « Dépend de »."""
    texte = LOTS.read_text(encoding="utf-8")
    lots: dict[int, set[str]] = defaultdict(set)
    for lot, cellule in _LIGNE_DE_LOT.findall(texte):
        for n in numeros(cellule):
            lots[n].add(lot)
    sections = _SECTION.split(texte)[1:]
    for lot, corps in zip(sections[::2], sections[1::2], strict=True):
        utile = "\n".join(x for x in corps.split("\n- ") if not x.startswith("**Dépend de**"))
        for liste in _ROUTES.findall(utile):
            for n in numeros(liste):
                lots[n].add(lot)
    return {n: tuple(sorted(x)) for n, x in lots.items()}


def operations(application: FastAPI) -> dict[tuple[str, str], dict[str, Any]]:
    """`{(MÉTHODE, chemin): opération}` de l'OpenAPI servi, sous `/api`."""
    schema = application.openapi()
    return {
        (methode.upper(), chemin): op
        for chemin, chemins in schema["paths"].items()
        if chemin.startswith("/api/")
        for methode, op in chemins.items()
        if methode in METHODES
    }


def _ecarts_d_une_operation(op: dict[str, Any], publique: bool, roles: frozenset[str]) -> list[str]:
    """Ce qui manque à une opération servie (forme API-PRO § 0.1)."""
    ecarts = []
    if not str(op.get("summary", "")).strip():
        ecarts.append("summary absent")
    if len(op.get("tags", [])) != 1:
        ecarts.append(f"étiquettes {op.get('tags')}")
    reponses: dict[str, Any] = op.get("responses", {})
    succes = [code for code in reponses if code.startswith("2")]
    if not succes:
        ecarts.append("aucune réponse de succès")
    for code in succes:
        contenu = reponses[code].get("content") or {}
        if code != "204" and not contenu:
            ecarts.append(f"{code} sans contenu décrit")
        if contenu.get("application/json", {}).get("schema", {"ok": 1}) == {}:
            ecarts.append(f"{code} : schéma JSON vide (response_model absent)")
    attendus = set() if publique else {"401"} | ({"403"} if roles != TOUS else set())
    if manquants := sorted(attendus - set(reponses)):
        ecarts.append(f"refus non déclarés {manquants}")
    return ecarts


def test_l_openapi_servi_est_celui_du_catalogue(application: FastAPI) -> None:
    """Méthode, chemin et rôles de chaque opération servie = API-PRO § 1 ; forme § 0.1."""
    gardes = {(x.methode, x.chemin): x for x in matrice(application)}
    ops = operations(application)
    assert len(ops) >= 90, "l'OpenAPI ne sert presque rien : application mal construite ?"
    ecarts = []
    for (methode, chemin), op in sorted(ops.items()):
        entree = catalogue().get((methode, gabarit(chemin)))
        garde = gardes.get((methode, chemin))
        if entree is None:
            ecarts.append(f"{methode} {chemin} : absente de API-PRO § 1")
            continue
        assert garde is not None, (methode, chemin)
        if entree.publique != garde.publique:
            ecarts.append(f"{methode} {chemin} ({entree.numero}) : publique {garde.publique}")
        elif not garde.publique and entree.roles is not None and entree.roles != garde.roles:
            ecarts.append(
                f"{methode} {chemin} ({entree.numero}) : rôles {sorted(garde.roles)}"
                f" ≠ {sorted(entree.roles)}"
            )
        for ecart in _ecarts_d_une_operation(op, garde.publique, garde.roles):
            ecarts.append(f"{methode} {chemin} ({entree.numero}) : {ecart}")
    assert ecarts == []


def test_chaque_route_attendue_a_son_lot(application: FastAPI) -> None:
    """Une route du catalogue pas encore servie a un lot qui la livre (LOTS-DE-TRAVAIL)."""
    numeros_catalogue = {x.numero for x in catalogue().values()}
    assert len(numeros_catalogue) == len(catalogue()) >= 245
    servies = {(m, gabarit(c)) for m, c in operations(application)}
    sans_lot = sorted(
        x.numero
        for cle, x in catalogue().items()
        if cle not in servies and x.numero not in lots_des_routes()
    )
    assert sans_lot == [], "routes du catalogue qu'aucun lot ne livre"
    assert lots_des_routes()[1] == ("D10", "S2")
    assert lots_des_routes()[110] == ("S4",)
    assert lots_des_routes()[243] == ("C1",)


def test_routes_du_catalogue_attendues(application: FastAPI) -> None:
    """Les routes du catalogue pas encore servies, par lot : attendues jusqu'à la recette
    finale (sautées et listées), en échec dès que `docs/RECETTE.md` existe."""
    servies = {(m, gabarit(c)) for m, c in operations(application)}
    attendues: dict[str, list[int]] = defaultdict(list)
    for cle, entree in sorted(catalogue().items(), key=lambda x: x[1].numero):
        if cle not in servies:
            lots = lots_des_routes().get(entree.numero, ("?",))
            attendues[" ou ".join(lots)].append(entree.numero)
    if not attendues:
        return
    liste = " ; ".join(f"{lot} : {_plages(ns)}" for lot, ns in sorted(attendues.items()))
    total = sum(len(ns) for ns in attendues.values())
    message = f"{total} routes du catalogue pas encore servies — {liste}"
    if RECETTE.exists():
        pytest.fail(message)
    pytest.skip(f"attendues (avant la recette finale) : {message}")


def _plages(ns: list[int]) -> str:
    """« 82–102, 145 » : des numéros triés écrits en plages."""
    plages: list[list[int]] = []
    for n in sorted(ns):
        if plages and n == plages[-1][-1] + 1:
            plages[-1].append(n)
        else:
            plages.append([n])
    return ", ".join(f"{p[0]}–{p[-1]}" if len(p) > 1 else str(p[0]) for p in plages)


def test_la_lecture_des_lots_suit_le_document() -> None:
    """La lecture de LOTS-DE-TRAVAIL : plages, parenthèses et « / » ignorés."""
    assert numeros("82–102, 145–148 (avec D6 pour le réalisé)") == {
        *range(82, 103),
        *range(145, 149),
    }
    assert numeros("52, 114 (rendu), 133/164/234 (environnement commun)") == {52, 114}
    assert numeros("D7, D1") == set()
    assert _plages([3, 1, 2, 7, 9, 10]) == "1–3, 7, 9–10"
