"""Le rapport de la tournée d'écran : `tournee-ecran.md` depuis `resultats/*.json`.

Toutes les bases parcourues sont mises côte à côte (écran × base : temps jusqu'à l'affichage et
état), puis les anomalies relevées par base, les exports et documents chronométrés, les recherches.
Ce qui suit la ligne `## Constats` du fichier existant (l'analyse écrite à la main) est conservé.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MARQUE_MANUELLE = "## Constats"
SEUIL_LENT = 1000
SEUIL_BLOQUANT = 3000


def _charger(dossier: Path) -> list[dict[str, Any]]:
    """Les résultats, dans l'ordre d'écriture des fichiers."""
    fichiers = sorted(dossier.glob("*.json"), key=lambda f: f.stat().st_mtime)
    resultats = []
    for f in fichiers:
        if f.name.endswith("-recompte.json"):
            continue
        r = json.loads(f.read_text())
        recompte = f.with_name(f"{f.stem}-recompte.json")
        r["recompte"] = json.loads(recompte.read_text()) if recompte.exists() else []
        resultats.append(r)
    return resultats


def _etat(e: dict[str, Any]) -> str:
    """L'état d'un écran : ok / lent / BLOQUANT / anomalie (ce qui domine)."""
    pbs = e.get("pbs", [])
    t = e.get("tAffiche")
    if t is None:
        return "BLOQUÉ"
    autres = [p for p in pbs if not p.startswith(("lent ", "BLOQUANT "))]
    if t > SEUIL_BLOQUANT:
        return "BLOQUANT" + (" +anom." if autres else "")
    if autres:
        return "anomalie"
    return "lent" if t > SEUIL_LENT else "ok"


def _ms(v: Any) -> str:
    return "—" if v is None else f"{int(v):,}".replace(",", " ")


def _lignes_ecrans(
    resultats: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, dict[str, Any]]]:
    """(zone, rôle, url) → étiquette → écran."""
    table: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for r in resultats:
        for p in r["passes"]:
            for e in p["ecrans"]:
                table.setdefault((p["zone"], p["role"], e["url"]), {})[r["etiquette"]] = e
    return table


def _volume(c: dict[str, int]) -> str:
    """Le volume d'une base en une ligne (mouvements, lots, bons, réceptions, ordres)."""

    def n(k: str) -> str:
        return f"{c.get(k, 0):,}".replace(",", " ")

    return (
        f"{n('mouvement')} mvts, {n('lot')} lots, {n('commande')} bons, {n('reception')} réc., "
        f"{n('ordre')} OF"
    )


def _resume(r: dict[str, Any]) -> dict[str, Any]:
    ecrans = [e for p in r["passes"] for e in p["ecrans"]]
    temps = [e["tAffiche"] for e in ecrans if e["tAffiche"] is not None]
    c = r.get("comptes", {})
    return {
        "etiquette": r["etiquette"],
        "jour": r.get("jour", ""),
        "ecrans": len(ecrans),
        "anomalies": sum(len(e["pbs"]) for e in ecrans),
        "lents": sum(1 for t in temps if SEUIL_LENT < t <= SEUIL_BLOQUANT),
        "bloquants": sum(1 for t in temps if t > SEUIL_BLOQUANT)
        + sum(1 for e in ecrans if e["tAffiche"] is None),
        "max": max(temps, default=0),
        "mediane": sorted(temps)[len(temps) // 2] if temps else 0,
        "volume": _volume(c),
        "telechargements": len(r.get("telechargements", [])),
    }


def _section_resume(resultats: list[dict[str, Any]]) -> list[str]:
    lignes = [
        "## 1. Bases parcourues",
        "",
        "| Base | Jour de l'horloge | Volume | Écrans | > 1 s | > 3 s ou bloqués | Anomalies | "
        "Médiane | Pire |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultats:
        s = _resume(r)
        lignes.append(
            f"| {s['etiquette']} | {s['jour']} | {s['volume']} | {s['ecrans']} | {s['lents']} | "
            f"{s['bloquants']} | {s['anomalies']} | {_ms(s['mediane'])} ms | {_ms(s['max'])} ms |"
        )
    return lignes


def _section_ecrans(resultats: list[dict[str, Any]]) -> list[str]:
    etiquettes = [r["etiquette"] for r in resultats]
    table = _lignes_ecrans(resultats)
    entete = " | ".join(f"{e} (ms, état)" for e in etiquettes)
    lignes = [
        "## 2. Écran × base — temps jusqu'à l'affichage et état",
        "",
        "Temps = navigation → roue disparue, texte présent, plus aucun appel `/api/` en vol "
        "(écran construit, Chrome sans tête, uvicorn 2 processus). État : ok ; lent (> 1 s) ; "
        "BLOQUANT (> 3 s) ; anomalie (voir § 3) ; BLOQUÉ (rien après 30 s).",
        "",
        f"| Zone | Rôle | Écran | {entete} |",
        "|---|---|---|" + "---|" * len(etiquettes),
    ]
    for (zone, role, url), par_base in table.items():
        cases = []
        for e in etiquettes:
            x = par_base.get(e)
            cases.append("—" if x is None else f"{_ms(x['tAffiche'])} {_etat(x)}")
        lignes.append(f"| {zone} | {role} | `{url}` | " + " | ".join(cases) + " |")
    return lignes


def _section_anomalies(resultats: list[dict[str, Any]]) -> list[str]:
    lignes = ["## 3. Anomalies relevées, par base", ""]
    for r in resultats:
        lignes.append(f"### {r['etiquette']}")
        lignes.append("")
        vues = 0
        for p in r["passes"]:
            for e in p["ecrans"]:
                for pb in e["pbs"]:
                    vues += 1
                    lent = e.get("apiLente") or {}
                    api = (
                        f" — appel le plus lent : `{lent.get('url', '')}` {_ms(lent.get('ms'))} ms"
                        if pb.startswith(("lent", "BLOQUANT"))
                        else ""
                    )
                    lignes.append(
                        f"- [{p['zone']}, {p['role']}, {p['taille']}] `{e['url']}` : {pb}{api}"
                    )
        if not vues:
            lignes.append("- aucune.")
        lignes.append("")
    return lignes


def _section_telechargements(resultats: list[dict[str, Any]]) -> list[str]:
    lignes = ["## 4. Exports Excel et documents (A4) — par base", ""]
    etiquettes = [r["etiquette"] for r in resultats]
    table: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for r in resultats:
        for t in r.get("telechargements", []):
            table.setdefault((t["genre"], t["href"]), {})[r["etiquette"]] = t
    lignes.append(
        "| Genre | Route | " + " | ".join(f"{e} (ms, Ko, statut)" for e in etiquettes) + " |"
    )
    lignes.append("|---|---|" + "---|" * len(etiquettes))
    for (genre, href), par_base in sorted(table.items()):
        cases = []
        for e in etiquettes:
            t = par_base.get(e)
            if t is None:
                cases.append("—")
                continue
            verdict = "" if t["statut"] == 200 else f" **{t['statut']}**"
            if t["statut"] == 200 and t["ms"] is not None and t["ms"] > SEUIL_BLOQUANT:
                verdict = " **BLOQUANT**"
            elif t["statut"] == 200 and t["ms"] is not None and t["ms"] > SEUIL_LENT:
                verdict = " lent"
            cases.append(f"{_ms(t['ms'])} ms, {t['octets'] // 1024} Ko{verdict}")
        lignes.append(f"| {genre} | `{href}` | " + " | ".join(cases) + " |")
    return lignes


def _section_recherches(resultats: list[dict[str, Any]]) -> list[str]:
    lignes = ["## 5. Recherche à la frappe (liste de l'écran) et recherche globale", ""]
    etiquettes = [r["etiquette"] for r in resultats]
    table: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for r in resultats:
        for p in r["passes"]:
            for e in p["ecrans"]:
                if e.get("recherche"):
                    table.setdefault((p["role"], e["url"]), {})[r["etiquette"]] = e["recherche"]
    lignes.append(
        "| Rôle | Écran | " + " | ".join(f"{e} (mot → ms, lignes)" for e in etiquettes) + " |"
    )
    lignes.append("|---|---|" + "---|" * len(etiquettes))
    for (role, url), par_base in table.items():
        cases = []
        for e in etiquettes:
            x = par_base.get(e)
            if x is None:
                cases.append("—")
            else:
                ou = "serveur" if x.get("serveur") else "écran"
                lignes_av = f"{x.get('avant')}→{x.get('apres')} l."
                cases.append(f"« {x['mot']} » → {_ms(x['ms'])} ms ({ou}), {lignes_av}")
        lignes.append(f"| {role} | `{url}` | " + " | ".join(cases) + " |")
    lignes += ["", "Recherche globale (coque) :", ""]
    for r in resultats:
        for g in r.get("recherches_globales", []):
            lignes.append(
                f"- {r['etiquette']}, {g['role']} : « {g.get('mot')} » → {g.get('etat')}, "
                f"{_ms(g.get('ms'))} ms, {g.get('resultats')} résultat(s)"
            )
    return lignes


def _section_tableaux(resultats: list[dict[str, Any]]) -> list[str]:
    """Les plus grands tableaux rendus dans le DOM (pagination ou non), par base."""
    lignes = ["## 6. Les plus grands tableaux rendus (lignes dans le DOM)", ""]
    for r in resultats:
        vus: list[tuple[int, str, str, str]] = []
        for p in r["passes"]:
            if p["zone"] != "bureau":
                continue
            for e in p["ecrans"]:
                for t in e.get("tableaux", []):
                    vus.append(
                        (
                            t["lignes"],
                            e["url"],
                            t.get("compteur") or t.get("libelle") or "",
                            t.get("charger") or "",
                        )
                    )
        vus.sort(reverse=True)
        lignes.append(f"### {r['etiquette']}")
        lignes.append("")
        for lignes_dom, url, lib, charger in vus[:15]:
            lignes.append(
                f"- `{url}` : {lignes_dom} lignes — {lib}"
                + (f" — {charger}" if charger else " — pas de « charger la suite »")
            )
        lignes.append("")
    return lignes


def _section_recompte(resultats: list[dict[str, Any]]) -> list[str]:
    """Les chiffres d'écran contre le recompte SQL, par base."""
    lignes = ["## 7. Chiffres d'écran contre recompte SQL", ""]
    for r in resultats:
        cas = r.get("recompte") or []
        if not cas:
            continue
        faux = [x for x in cas if not x["ok"]]
        lignes.append(f"### {r['etiquette']} — {len(cas)} cas, {len(faux)} écart(s)")
        lignes.append("")
        lignes.append("| Cas | Écran | SQL | Verdict |")
        lignes.append("|---|---|---|---|")
        for x in cas:
            ecran = "—" if x["ecran"] is None else f"{x['ecran']:,.2f}".replace(",", " ")
            sql = "—" if x["sql"] is None else f"{x['sql']:,.2f}".replace(",", " ")
            lignes.append(f"| {x['quoi']} | {ecran} | {sql} | {'ok' if x['ok'] else '**ÉCART**'} |")
        lignes.append("")
    if len(lignes) == 2:
        lignes.append("Aucun recompte encore.")
    return lignes


def ecrire(dossier_resultats: Path, cible: Path) -> None:
    """Régénère le rapport ; garde l'analyse manuelle qui suit `## Constats`."""
    resultats = _charger(dossier_resultats)
    manuel = ""
    if cible.exists() and MARQUE_MANUELLE in cible.read_text(encoding="utf-8"):
        manuel = cible.read_text(encoding="utf-8").split(MARQUE_MANUELLE, 1)[1]
    lignes = [
        "# Tournée d'écran — stress test « 10 ans » de Gestion MP PRO",
        "",
        "Généré par `backend/essais/stress/tournee.py` (pilote `tournee_ecran.mjs`). Bureau "
        "1 440 × 900 (direction, achats, alimentation), téléphone 375 × 812 (atelier : direction "
        "et alimentation ; bureau de l'alimentation). Tous les écrans et tous les onglets du "
        "registre, les exports Excel, les documents A4, la recherche à la frappe. Seuils : > 1 s "
        "lent, > 3 s bloquant.",
        "",
    ]
    if not resultats:
        lignes.append("Aucun résultat encore.")
    else:
        lignes += _section_resume(resultats) + [""]
        lignes += _section_ecrans(resultats) + [""]
        lignes += _section_anomalies(resultats)
        lignes += _section_telechargements(resultats) + [""]
        lignes += _section_recherches(resultats) + [""]
        lignes += _section_tableaux(resultats)
        lignes += _section_recompte(resultats) + [""]
    lignes += [
        MARQUE_MANUELLE
        + (manuel if manuel else "\n\n(À écrire à la main : analyse, classement, corrections.)\n")
    ]
    cible.write_text("\n".join(lignes), encoding="utf-8")
