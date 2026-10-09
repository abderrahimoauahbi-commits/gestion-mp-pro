"""Comparer chiffre par chiffre Gestion MP et Gestion MP PRO (lot C1 ; ARCHITECTURE § 14.3).

    backend/.venv/bin/python outils/comparer_avec_gestion_mp.py \\
        --source gestion_mp|gestion_mp_comparaison [--mode moteurs|api] \\
        [--dates 2026-10-08,fins-de-mois] [--sections stock,valorisation,…] \\
        [--pro-base gestion_mp_pro] [--resynchroniser] \\
        [--gestion-mp http://localhost:8030] [--pro http://localhost:8050] \\
        --sortie essais/resultat-comparaison-2026-10-08.md

La base de Gestion MP choisie est **copiée** (`pg_dump`, lecture seule) et comparée à une base
PRO reprise de cette copie — jamais les bases ni les serveurs en service (seule `/api/sante`
des serveurs vivants est lue, pour relever leur version). Code de sortie 0 seulement si « à
corriger : 0 » ; 2 si les deux bases sont désynchronisées ou la source illisible.

Deux modes : `moteurs` (les deux moteurs sur la copie, sans HTTP) et `api` (deux serveurs
lancés par l'outil sur les copies, routes GET comparées). Aucune écriture dans `gestion_mp`,
`gestion_mp_comparaison`, `~/gestion-mp`, ni dans la base PRO installée.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend" / "essais"))

import comparaison as comp  # noqa: E402
import comparaison_bases as cb  # noqa: E402
import comparaison_rapport as cr  # noqa: E402
import parite_bases as pb  # noqa: E402
import parite_statique as st  # noqa: E402

FINS_DE_MOIS = list(st.FINS_DE_MOIS)
SOURCES = ("gestion_mp", "gestion_mp_comparaison")


def dates_de(texte: str) -> list[str]:
    """La liste des dates : « fins-de-mois » et « aujourd'hui » développés."""
    dates: list[str] = []
    for brut in texte.split(","):
        mot = brut.strip()
        if mot == "fins-de-mois":
            dates += FINS_DE_MOIS
        elif mot in ("aujourd-hui", "aujourdhui", "aujourd'hui"):
            dates.append(st.AUJOURDHUI.isoformat())
        elif mot:
            dates.append(mot)
    return list(dict.fromkeys(dates))


def mois_de(dates: list[str]) -> list[str]:
    """Les mois (AAAA-MM) couverts par les dates, pour les bilans de la passe API."""
    return sorted({d[:7] for d in dates})


def version_servie(url: str | None) -> str:
    """La version d'un serveur en service (`/api/sante`, lecture seule) ; '' s'il ne répond pas."""
    if not url:
        return ""
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/sante", timeout=5) as r:  # noqa: S310
            return str(json.loads(r.read()).get("version", ""))
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def comparer(args: argparse.Namespace, dossier: Path) -> comp.Resultat:
    """Prépare les copies et lance la comparaison (un mode, une source)."""
    bases = pb.Bases(prefixe=args.prefixe)
    pb.SOURCE = args.source
    try:
        prep = cb.preparer(args.source, bases, args.pro_base, args.resynchroniser)
    except cb.Desynchronisees as exc:
        sys.stderr.write(f"Comparaison refusée : {exc}\n")
        raise SystemExit(2) from exc
    garder = {s.strip() for s in args.sections.split(",") if s.strip()} if args.sections else None
    dates = dates_de(args.dates)
    saboteur = comp.saboteur_essai if args.prouver_sensibilite else None
    if args.mode == "api":
        r = comp.comparer_api(bases, dates, mois_de(dates), dossier, prep, garder)
    else:
        r = comp.comparer_moteurs(args.source, bases, dates, dossier, prep, garder, saboteur)
    r.versions.setdefault("pro", version_servie(args.pro) or "0.1.0 (projet)")
    live = version_servie(args.gestion_mp)
    if live:
        r.versions["gestion_mp_en_service"] = live
    return r


def analyser(arguments: list[str] | None = None) -> argparse.Namespace:
    """Les options de la ligne de commande."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--source", choices=SOURCES, default="gestion_mp_comparaison")
    p.add_argument("--mode", choices=("moteurs", "api"), default="moteurs")
    p.add_argument("--dates", default="aujourd-hui,fins-de-mois")
    p.add_argument("--sections", default="")
    p.add_argument("--pro-base", default=None, help="base PRO installée à comparer (copiée)")
    p.add_argument("--resynchroniser", action="store_true", help="rejoue la reprise si désync.")
    p.add_argument("--gestion-mp", default=None, help="serveur en service (pour /api/sante)")
    p.add_argument("--pro", default=None, help="serveur PRO en service (pour /api/sante)")
    p.add_argument("--prefixe", default="gestion_mp_pro_c1")
    p.add_argument("--prouver-sensibilite", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--garder", action="store_true", help="ne pas supprimer les bases d'essai")
    p.add_argument("--sortie", default=None)
    return p.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Lance la comparaison, écrit le rapport, rend le code de sortie (0 : à corriger 0)."""
    args = analyser(arguments)
    bases = pb.Bases(prefixe=args.prefixe)
    with tempfile.TemporaryDirectory(prefix="comparaison-") as tmp:
        try:
            r = comparer(args, Path(tmp))
        finally:
            if not args.garder:
                pb.nettoyer(bases)
    rapport = cr.rediger(r)
    sortie = args.sortie or str(
        RACINE / "backend" / "essais" / f"resultat-comparaison-{st.AUJOURDHUI}.md"
    )
    Path(sortie).write_text(rapport, encoding="utf-8")
    sys.stdout.write(
        f"Comparaison {args.source} ({args.mode}) : à corriger {r.a_corriger} — rapport {sortie}\n"
    )
    if not r.prep.source_intacte:
        sys.stderr.write("ALERTE : une base de Gestion MP a changé pendant la comparaison.\n")
        return 2
    return 0 if r.a_corriger == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
