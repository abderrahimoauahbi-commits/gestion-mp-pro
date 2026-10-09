"""Les liens que le serveur donne (notifications, recherche, contrôles, Cockpit, alertes) sont
des adresses d'écran déclarées (RESTES3 : reste E2 → S2).

Les écrans sont déclarés dans `frontend/src/pages/*/ecrans.ts` (`chemin: '…'`) et, hors coque,
dans `frontend/src/App.tsx` (`path: '…'`) — lus ici en lecture seule. Chaque texte du serveur
qui commence par « /mot » (hors `api/`, `migrations/`, `reprise/`, chemins de disque et adresses
de l'API) est un lien : `{…}` d'un gabarit vaut un segment ; la requête est ignorée.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SERVEUR = RACINE / "backend" / "gestion_mp_pro"
ECRAN = RACINE / "frontend" / "src"
HORS_LIENS = ("/api", "/assets", "/usr", "/opt", "/lot/(")
"""Adresses de l'API, fichiers, chemins de disque, motif d'analyse d'une étiquette."""


def ecrans() -> set[str]:
    """Les chemins d'écran déclarés (registre des domaines et routes hors coque)."""
    chemins = set()
    for f in ECRAN.glob("pages/*/ecrans.ts"):
        chemins |= set(re.findall(r"chemin:\s*'([^']+)'", f.read_text(encoding="utf-8")))
    chemins |= set(re.findall(r"path:\s*'([^']+)'", (ECRAN / "App.tsx").read_text("utf-8")))
    return chemins


def _texte(n: ast.AST) -> str | None:
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in n.values)
    return None


def liens_du_serveur() -> dict[str, str]:
    """Lien → fichier, pour chaque texte du serveur qui ressemble à une adresse d'écran."""
    trouves: dict[str, str] = {}
    for f in SERVEUR.rglob("*.py"):
        if f.relative_to(SERVEUR).parts[0] in {"api", "migrations", "reprise"}:
            continue
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            t = _texte(n)
            if t and re.match(r"^/[a-z]", t) and " " not in t and not t.startswith(HORS_LIENS):
                trouves[t] = str(f.relative_to(SERVEUR))
    return trouves


def declare(lien: str, chemins: set[str]) -> bool:
    """Le lien répond-il à un écran (`:x` d'un écran, `{}` d'un gabarit : un segment) ?"""
    base = re.split(r"[?#]", lien)[0].rstrip(".")
    morceaux = [x for x in base.split("/") if x]
    if base.endswith("/"):
        morceaux.append("{}")
    for chemin in chemins:
        modele = [x for x in chemin.split("/") if x]
        if len(modele) == len(morceaux) and all(
            m.startswith(":") or v in {"{}", m} for m, v in zip(modele, morceaux, strict=True)
        ):
            return True
    return False


def test_chaque_lien_du_serveur_est_un_ecran_declare() -> None:
    chemins = ecrans()
    assert "/cockpit" in chemins and "/commandes/:id" in chemins and "/enroler" in chemins
    liens = liens_du_serveur()
    assert "/cockpit?signalement={}" in liens and "/commandes/{}" in liens
    assert {lien: f for lien, f in liens.items() if not declare(lien, chemins)} == {}


def test_un_lien_vers_un_ecran_absent_se_voit() -> None:
    chemins = {"/commandes", "/commandes/:id", "/accueil"}
    assert declare("/commandes/{}", chemins) and declare("/accueil?signalement={}", chemins)
    assert not declare("/cockpit?signalement={}", chemins)
    assert not declare("/commandes/{}/lignes", chemins)
