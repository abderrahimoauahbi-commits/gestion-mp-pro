"""Reprise au volume réel (lot R1) : copies de `gestion_mp` et de `gestion_mp_comparaison`.

Essais « complets » (GESTIONMPPRO_ESSAIS_COMPLETS=1) : ils lisent les bases de Gestion MP par
`pg_dump` (lecture seule) pour en faire des copies d'essai, et lancent le moteur de Gestion MP
avec son propre interpréteur (`~/gestion-mp/.venv/bin/python`) sur la copie.

- reprise complète < 1 minute, tous les contrôles tenus, rejouée sans changement : rien créé ;
- empreinte de la base de Gestion MP identique avant et après (aucune écriture) ;
- l'état du stock (les 70 colonnes de `etat_stock`, par matière) calculé par le moteur PRO sur
  la base reprise (chargeur de S4) = celui du moteur de Gestion MP sur la copie source.
"""

from __future__ import annotations

import dataclasses
import json
import math
import os
import subprocess
import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fabriques.reprise import cible_migree, creer_base, supprimer_base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from test_reprise import ESSAI

from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles.enums import ModeReprise
from gestion_mp_pro.reprise import source as src
from gestion_mp_pro.reprise.contexte import Options
from gestion_mp_pro.reprise.execution import executer
from gestion_mp_pro.reprise.sauvegarde import outil
from gestion_mp_pro.services import donnees_moteur

pytestmark = pytest.mark.skipif(
    not reglages().essais_complets, reason="essai complet (GESTIONMPPRO_ESSAIS_COMPLETS=1)"
)
GESTION_MP = Path.home() / "gestion-mp"
COPIE = f"postgresql+psycopg:///{ESSAI.removesuffix('_essai')}_rcopie_essai"
CIBLE = f"postgresql+psycopg:///{ESSAI.removesuffix('_essai')}_rreelle_essai"
AUJOURDHUI = date(2026, 10, 9)
DATES = ("2026-10-09", "2026-06-30", "2026-03-31", "2025-12-31")
LIMITE_S = 60

ETAT_GESTION_MP = """
import dataclasses, json, sys
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from gestion_mp import depot
from gestion_mp.calcul import moteur
url, jours, auj = sys.argv[1], sys.argv[2].split(","), date.fromisoformat(sys.argv[3])
e = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
with Session(e) as s:
    complet = depot.charger(s)
    sortie = {j: {l.reference: dataclasses.asdict(l) for l in moteur.etat_stock(
        moteur.a_la_date(complet, date.fromisoformat(j), aujourdhui=auj), date.fromisoformat(j))}
        for j in jours}
json.dump(sortie, sys.stdout, default=str)
"""
"""Le calcul côté Gestion MP (lancé par son interpréteur, base en lecture seule)."""


def copier(base: str) -> None:
    """Copie une base de Gestion MP (pg_dump en lecture, pg_restore dans la copie d'essai)."""
    creer_base(COPIE)
    dump = subprocess.run([outil("pg_dump"), "-Fc", base], capture_output=True, check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--no-owner", "-d", COPIE.replace("+psycopg", "")],
        input=dump.stdout,
        capture_output=True,
        check=True,
    )


def etat_gestion_mp() -> dict[str, Any]:
    """L'état du stock de Gestion MP sur la copie, aux dates."""
    resultat = subprocess.run(  # noqa: S603
        [
            str(GESTION_MP / ".venv/bin/python"),
            "-c",
            ETAT_GESTION_MP,
            COPIE,
            ",".join(DATES),
            AUJOURDHUI.isoformat(),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=GESTION_MP,
        env={
            **os.environ,
            "PYTHONPATH": str(GESTION_MP),
            "GESTION_MP_BASE": COPIE,
            "GESTION_MP_TACHES": "0",
        },
    )
    return dict(json.loads(resultat.stdout))


def etat_pro() -> dict[str, Any]:
    """L'état du stock du moteur PRO sur la base reprise (chargeur de S4)."""
    donnees_moteur.invalider()
    moteur = create_engine(CIBLE, poolclass=NullPool)
    with Session(moteur) as s:
        complet = donnees_moteur.charger(s)
    moteur.dispose()
    donnees_moteur.invalider()
    sortie = {}
    for j in DATES:
        jour = date.fromisoformat(j)
        lignes = etat_stock(a_la_date(complet, jour, aujourdhui=AUJOURDHUI), jour)
        sortie[j] = {x.reference: dataclasses.asdict(x) for x in lignes}
    return sortie


def proche(a: Any, b: Any) -> bool:
    """Égalité au bruit de l'addition flottante près (1e-6 absolu, 1e-9 relatif)."""
    if isinstance(a, int | float) and isinstance(b, int | float) and not isinstance(a, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(proche(a[k], b[k]) for k in a)
    if isinstance(a, list | tuple) and isinstance(b, list | tuple):
        return len(a) == len(b) and all(proche(x, y) for x, y in zip(a, b, strict=True))
    return a == b or str(a) == str(b)


@pytest.mark.parametrize("base", ["gestion_mp", "gestion_mp_comparaison"])
def test_reprise_reelle(base: str, tmp_path: Path) -> None:
    url = f"postgresql+psycopg:///{base}"
    avant = src.empreinte_actuelle(url)
    copier(base)
    cible_migree(CIBLE)
    options = Options(
        source=COPIE,
        cible=CIBLE,
        mode=ModeReprise.tout,
        sauvegarder=False,
        pieces_source=str(tmp_path / "rien"),
        pieces_cible=str(tmp_path / "pieces"),
    )
    debut = time.monotonic()
    r = executer(options)
    assert time.monotonic() - debut < LIMITE_S
    assert r.reussie and "NON TENU" not in r.rapport, r.rapport
    rejeu = executer(options)
    tables = rejeu.comptes["tables"]
    assert sum(c["creees"] + c["mises_a_jour"] + c["supprimees"] for c in tables.values()) == 0
    gmp, pro = etat_gestion_mp(), etat_pro()
    for jour in DATES:
        assert gmp[jour].keys() == pro[jour].keys()
        ecarts = [
            (ref, champ)
            for ref, ligne in gmp[jour].items()
            for champ, v in ligne.items()
            if not proche(v, pro[jour][ref][champ])
        ]
        assert ecarts == [], (jour, ecarts[:5])
    assert src.empreinte_actuelle(url) == avant
    supprimer_base(COPIE)
    supprimer_base(CIBLE)
