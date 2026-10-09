"""Le résultat du scénario (lot V2) : une ligne par étape, les valeurs vérifiées, les écarts.

Écrit dans `essais/resultat-scenario.txt` (PLAN-DE-RECETTE-PRO § 8 : « une ligne ✓ par étape et
le nombre de valeurs vérifiées, cible ≥ 400 »).
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from scenario_monde import Monde
from scenario_outils import Verif

CIBLE = 400


def _commit() -> str:
    sortie = subprocess.run(  # noqa: S603 — git, arguments à nous
        ["git", "-C", str(Path(__file__).parent), "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return sortie.stdout.strip() or "?"


def ecrire(verif: Verif, monde: Monde | None, infos: dict[str, object], court: bool) -> str:
    """Le texte du résultat."""
    lignes = [
        "Gestion MP PRO — scénario de bout en bout : un mois d'usine (novembre 2026)",
        f"Joué le {datetime.now().astimezone():%Y-%m-%d %H:%M} · commit {_commit()}"  # noqa: DTZ005
        f" · {'version courte' if court else 'version complète'}",
        f"Base : {infos.get('base', '?')}",
    ]
    if "sources_intactes" in infos:
        intactes = "identiques" if infos["sources_intactes"] else "CHANGÉES"
        lignes.append(
            f"Empreintes de gestion_mp et gestion_mp_comparaison avant/après : {intactes}"
        )
    if monde is not None:
        appels = sum(p.appels for p in monde.postes.values())
        lignes.append(
            f"Serveur : {monde.adresse} · {appels} appels HTTP · durée {infos.get('duree_s')} s"
        )
    lignes.append("")
    for e in verif.etapes:
        marque = "✓" if not e.echecs else "✗"
        lignes.append(
            f"{marque} {e.numero:>3} {e.titre} — {e.verifications} vérifications ({e.duree:.1f} s)"
        )
        lignes.extend(f"      ✗ {x}" for x in e.echecs)
    reussies = sum(1 for e in verif.etapes if not e.echecs)
    lignes += [
        "",
        f"Étapes réussies : {reussies}/{len(verif.etapes)}",
        f"Valeurs vérifiées : {verif.total}" + ("" if court else f" (cible ≥ {CIBLE})"),
        f"Écarts : {len(verif.echecs)}",
    ]
    if monde is not None and monde.notes:
        lignes += ["", "Notes :"] + [f"  - {n}" for n in monde.notes]
    return "\n".join(lignes) + "\n"
