"""Règles de forme du code serveur (ARCHITECTURE § 3, § 9.1 ; LOTS § 0 n° 3) : 400 lignes par
fichier, 60 lignes par fonction, docstrings, aucun `print`, domaines tous déclarés (lot S0)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import APIRouter

import gestion_mp_pro
from gestion_mp_pro.api import DOMAINES, etiquettes_openapi, routeurs

PAQUET = Path(gestion_mp_pro.__file__).parent
ESSAIS = Path(__file__).parent
GENERES = ("migrations/versions",)
"""Fichiers générés, hors plafonds (révisions Alembic)."""

MAX_LIGNES_FICHIER = 400
MAX_LIGNES_FONCTION = 60


def _fichiers() -> list[Path]:
    tous = [*PAQUET.rglob("*.py"), *ESSAIS.rglob("*.py")]
    return sorted(
        f for f in tous if ".venv" not in f.parts and not any(g in f.as_posix() for g in GENERES)
    )


def _nom(fichier: Path) -> str:
    return fichier.relative_to(PAQUET.parent).as_posix()


@pytest.mark.parametrize("fichier", _fichiers(), ids=_nom)
def test_plafonds(fichier: Path) -> None:
    texte = fichier.read_text(encoding="utf-8")
    assert len(texte.splitlines()) <= MAX_LIGNES_FICHIER
    arbre = ast.parse(texte)
    trop_longues = [
        f"{n.name} ({n.end_lineno - n.lineno + 1} lignes)"
        for n in ast.walk(arbre)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        and n.end_lineno is not None
        and n.end_lineno - n.lineno + 1 > MAX_LIGNES_FONCTION
    ]
    assert trop_longues == []


@pytest.mark.parametrize("fichier", sorted(PAQUET.rglob("*.py")), ids=_nom)
def test_docstrings_et_aucun_print(fichier: Path) -> None:
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    assert ast.get_docstring(arbre), "module sans docstring"
    sans = [
        n.name
        for n in ast.walk(arbre)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not n.name.startswith("_")
        and not ast.get_docstring(n)
    ]
    assert sans == []
    prints = [
        n.lineno
        for n in ast.walk(arbre)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
    ]
    assert prints == []


def test_tous_les_domaines_ont_leur_routeur() -> None:
    assert len(DOMAINES) == len({d.module for d in DOMAINES}) == 25
    for domaine, routeur in zip(DOMAINES, routeurs(), strict=True):
        assert isinstance(routeur, APIRouter)
        assert routeur.tags == [domaine.etiquette]
        assert (PAQUET / "api" / domaine.module / "routes.py").is_file()
    assert [t["name"] for t in etiquettes_openapi()] == [d.etiquette for d in DOMAINES]


def test_les_couches_basses_n_importent_pas_fastapi() -> None:
    for dossier in ("services", "calcul"):
        for fichier in (PAQUET / dossier).rglob("*.py"):
            arbre = ast.parse(fichier.read_text(encoding="utf-8"))
            modules = {
                a.name for n in ast.walk(arbre) if isinstance(n, ast.Import) for a in n.names
            } | {n.module or "" for n in ast.walk(arbre) if isinstance(n, ast.ImportFrom)}
            assert not {m for m in modules if m.split(".")[0] in {"fastapi", "starlette"}}, fichier
