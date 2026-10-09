"""Le scénario de bout en bout en version courte (lot V2, PLAN-DE-RECETTE-PRO § 8, A7).

`essais/scenario_complet.py --court` joue les 23 étapes du mois de novembre sur une base neuve
(semences seules, `<base d'essai>` → `…_scenario_essai`), par l'API d'un vrai serveur lancé sur
un port libre, chaque rôle avec son compte ; chaque valeur attendue est écrite dans le script.
La version complète part d'une copie de l'année d'essai (`essais/resultat-scenario.txt`).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

SCRIPT = Path(__file__).resolve().parents[1] / "essais" / "scenario_complet.py"


def test_le_mois_d_usine_en_version_courte(tmp_path: Path) -> None:
    essai = make_url(os.environ["GESTIONMPPRO_BASE"]).database or "gestion_mp_pro_essai"
    prefixe = essai.removesuffix("_essai") + "_scenario_court"
    sortie = tmp_path / "resultat.txt"
    r = subprocess.run(  # noqa: S603 — l'interpréteur des essais, un script du dépôt
        [sys.executable, str(SCRIPT), "--court", "--prefixe", prefixe, "--sortie", str(sortie)],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    texte = sortie.read_text(encoding="utf-8") if sortie.exists() else r.stdout + r.stderr
    assert r.returncode == 0, texte[-4000:]
    reussies, etapes = texte.split("Étapes réussies : ")[1].split()[0].split("/")
    assert reussies == etapes == "24", texte[-4000:]
    assert "Écarts : 0" in texte
    total = int(texte.split("Valeurs vérifiées : ")[1].split()[0])
    assert total >= 400, texte[-2000:]
