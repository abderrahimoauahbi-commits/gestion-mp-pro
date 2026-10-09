#!/usr/bin/env python3
"""Génère docs/NOTICE.md depuis frontend/src/aide.json (une seule source, ARCHITECTURE § 10.2 A7).

Le Mode d'emploi de l'écran, le « ? » de chaque écran, les formules des indicateurs et cette notice
lisent le même fichier : la notice ne s'écrit jamais à la main.

Usage :
    python3 scripts/generer_notice.py             # écrit docs/NOTICE.md
    python3 scripts/generer_notice.py --verifier  # n'écrit rien ; échoue si elle n'est pas à jour

L'ordre des écrans est celui du menu (`ORDRE_DU_MENU` de frontend/src/routes.ts) ; le chemin de
chaque écran est lu dans frontend/src/pages/*/ecrans.ts. Aucune date n'est écrite : deux
générations du même aide.json donnent le même fichier, au caractère près.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "frontend" / "src" / "aide.json"
ROUTES = RACINE / "frontend" / "src" / "routes.ts"
PAGES = RACINE / "frontend" / "src" / "pages"
CIBLE = RACINE / "docs" / "NOTICE.md"

ENTETE = """# Gestion MP PRO — notice

> Générée depuis `frontend/src/aide.json` par `scripts/generer_notice.py` : ne pas la modifier à
> la main. Le même texte s'affiche dans l'écran (Mode d'emploi, bouton « ? » de chaque écran,
> formules des indicateurs).
"""


def texte(brut: str, communs: dict[str, str]) -> str:
    """Un texte d'aide en Markdown : renvois développés, liens d'écran écrits avec leur adresse."""
    developpe = re.sub(r"\{\{(\w+)\}\}", lambda m: communs.get(m.group(1), m.group(0)), brut)
    return re.sub(r"\[([^\]]+)\]\((/[^)\s]*)\)", r"\1 (`\2`)", developpe)


def cellule(brut: str, communs: dict[str, str]) -> str:
    """Un texte dans une cellule de tableau Markdown."""
    return texte(brut, communs).replace("|", "\\|")


def chemins_des_ecrans() -> dict[str, str]:
    """La clé d'aide → le chemin de l'écran (le premier déclaré pour cette clé)."""
    chemins: dict[str, str] = {}
    for fichier in sorted(PAGES.glob("*/ecrans.ts")):
        source = fichier.read_text(encoding="utf-8")
        for chemin, cle in re.findall(r"chemin: '([^']+)',[\s\S]*?aide: '([^']+)'", source):
            chemins.setdefault(cle, chemin)
    return chemins


def ordre_du_menu() -> list[str]:
    """Les chemins du menu, dans l'ordre de la barre latérale."""
    source = ROUTES.read_text(encoding="utf-8")
    bloc = re.search(r"const ORDRE_DU_MENU[^=\n]*=\s*\[([\s\S]*?)\]", source)
    return re.findall(r"'([^']+)'", bloc.group(1)) if bloc else []


def mode_emploi(me: dict[str, Any], formules: dict[str, Any], communs: dict[str, str]) -> list[str]:
    """Les sept volets du Mode d'emploi."""
    lignes = [f"## {me['titre']}", "", me["sous_titre"], "", f"### {me['regles']['titre']}", ""]
    for i, r in enumerate(me["regles"]["elements"], 1):
        lignes.append(f"{i}. **{r['titre']}** {texte(r['texte'], communs)}")
    lignes += ["", f"### {me['roles']['titre']}", ""]
    for carte in me["roles"]["cartes"]:
        lignes += [f"#### {carte['titre']}", ""]
        lignes += [f"- {texte(p, communs)}" for p in carte["points"]] + [""]
    lignes += [f"### {me['pas']['titre']}", ""]
    for p in me["pas"]["procedures"]:
        lignes += [f"#### {p['titre']} (`{p['vers']}`)", ""]
        lignes += [f"{i}. {texte(e, communs)}" for i, e in enumerate(p["etapes"], 1)] + [""]
    lignes += [
        f"### {me['calculs']['titre']}",
        "",
        "| Grandeur | Comment elle est obtenue |",
        "|---|---|",
    ]
    for cle in me["calculs"]["lignes"]:
        f = formules[cle]
        lignes.append(f"| {cellule(f['grandeur'], communs)} | {cellule(f['texte'], communs)} |")
    lignes += ["", texte(me["calculs"]["pied"], communs), "", f"### {me['analyse']['titre']}", ""]
    lignes += [me["analyse"]["note_permise"], "", "| Onglet | Ce qu'on y lit |", "|---|---|"]
    for a in me["analyse"]["lignes"]:
        vers = f"/analyse?onglet={a['onglet']}"
        lignes.append(f"| {a['nom']} (`{vers}`) | {cellule(a['texte'], communs)} |")
    lignes += ["", f"### {me['ecrans']['titre']}", ""]
    lignes += ["| Écran de l'ERP Fil | Dans Gestion MP PRO | Ce qui a changé |", "|---|---|---|"]
    for e in me["ecrans"]["lignes"]:
        ou = f"{cellule(e['ou'], communs)} (`{e['vers']}`)"
        lignes.append(f"| {cellule(e['erp'], communs)} | {ou} | {cellule(e['note'], communs)} |")
    lignes += ["", me["ecrans"]["pied"], "", f"### {me['telephone']['titre']}", ""]
    lignes += [f"{i}. {texte(e, communs)}" for i, e in enumerate(me["telephone"]["etapes"], 1)]
    return [*lignes, ""]


def ecrans(aide_ecrans: dict[str, Any], communs: dict[str, str]) -> list[str]:
    """L'aide de chaque écran, dans l'ordre du menu, puis les autres par titre."""
    chemins = chemins_des_ecrans()
    par_chemin = {chemin: cle for cle, chemin in chemins.items()}
    menu = [par_chemin[c] for c in ordre_du_menu() if c in par_chemin]
    autres = sorted(
        (c for c in aide_ecrans if c not in menu), key=lambda c: aide_ecrans[c]["titre"]
    )
    lignes = ["## L'aide de chaque écran", ""]
    for cle in [*menu, *autres]:
        e = aide_ecrans[cle]
        chemin = chemins.get(cle)
        lignes += [f"### {e['titre']}" + (f" (`{chemin}`)" if chemin else ""), ""]
        lignes += [texte(e["resume"], communs), ""]
        lignes += [f"- {texte(p, communs)}" for p in e["points"]]
        lignes.append("")
    return lignes


def notice() -> str:
    """Le texte complet de docs/NOTICE.md."""
    aide = json.loads(SOURCE.read_text(encoding="utf-8"))
    communs = {"sur_les_metiers": aide["sur_les_metiers"]}
    corps = [
        ENTETE,
        "## Sur les métiers",
        "",
        aide["sur_les_metiers"],
        "",
        *mode_emploi(aide["mode_emploi"], aide["formule"], communs),
        *ecrans(aide["ecran"], communs),
    ]
    return "\n".join(corps).rstrip() + "\n"


def main() -> int:
    """Écrit la notice, ou vérifie qu'elle est à jour (`--verifier`)."""
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parseur.add_argument(
        "--verifier", action="store_true", help="échoue si la notice n'est pas à jour"
    )
    args = parseur.parse_args()
    attendu = notice()
    if args.verifier:
        actuel = CIBLE.read_text(encoding="utf-8") if CIBLE.exists() else ""
        if actuel != attendu:
            sys.stderr.write(
                "docs/NOTICE.md n'est pas à jour : python3 scripts/generer_notice.py\n"
            )
            return 1
        return 0
    CIBLE.write_text(attendu, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
