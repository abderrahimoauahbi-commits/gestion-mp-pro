"""Gestion MP pour la parité dynamique du scénario (lot V2, PLAN-DE-RECETTE-PRO § 7.4).

Gestion MP (code et interpréteur de `~/gestion-mp`, en lecture seule) est servi sur une **copie**
de `gestion_mp_comparaison` (`<préfixe>_gmp_essai`), sur un port libre au-dessus de 8100 (jamais
8030), sans tâche de fond, sauvegardes et pièces dans un dossier temporaire, à l'heure du
scénario (`scenario_serveur`). Gestion MP n'a pas de création de compte par API sans code saisi
à l'écran : un compte par rôle est inscrit dans la copie avec une session ouverte (jeton tiré au
hasard, seule son empreinte est gardée, comme Gestion MP le fait).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import scenario_bases as bases
import scenario_serveur as serveur
from scenario_outils import Horloge, Poste
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

GESTION_MP = Path(os.environ.get("GESTION_MP_CODE", str(Path.home() / "gestion-mp")))
PYTHON = GESTION_MP / ".venv" / "bin" / "python"
ROLES = {"D": "direction", "A": "achats", "L": "alimentation"}


def disponible() -> bool:
    """Gestion MP est-il installé sur ce poste (code et interpréteur) ?"""
    return PYTHON.exists() and (GESTION_MP / "gestion_mp" / "main.py").exists()


def comptes(adresse: str) -> dict[str, str]:
    """Un compte par rôle dans la copie, et sa session (expire fin 2027) : rôle → jeton."""
    jetons = {}
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        for cle, role in ROLES.items():
            jeton = secrets.token_urlsafe(32)
            uid = c.execute(
                text(
                    "INSERT INTO utilisateur (identifiant, nom, role, cree_le) "
                    "VALUES (:i, :n, :r, now()) RETURNING id"
                ),
                {"i": f"scn-{role}", "n": f"Scénario {role}", "r": role},
            ).scalar_one()
            c.execute(
                text("INSERT INTO session_ouverte VALUES (:e, :u, '2027-12-31')"),
                {"e": hashlib.sha256(jeton.encode()).hexdigest(), "u": uid},
            )
            jetons[cle] = jeton
    moteur.dispose()
    return jetons


def _environnement(copie: str, dossier: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTION")}
    return env | {
        "GESTION_MP_BASE": copie,
        "GESTION_MP_TACHES": "0",
        "GESTION_MP_SAUVEGARDES": str(dossier / "gmp-sauvegardes"),
        "GESTION_MP_PIECES": str(dossier / "gmp-pieces"),
        "PYTHONPATH": str(GESTION_MP),
        "SCENARIO_PYTHON": str(PYTHON),
        "SCENARIO_CWD": str(GESTION_MP),
    }


@contextmanager
def lancer(copie: str, dossier: Path, horloge: Horloge) -> Iterator[dict[str, Poste]]:
    """Copie la source, lance Gestion MP dessus ; rend un poste par rôle ; arrête tout."""
    bases.supprimer(copie)
    bases.copier(bases.SOURCE, copie)
    jetons = comptes(copie)
    journal = dossier / "gestion_mp.log"
    with serveur.lancer(
        "gestion_mp", _environnement(copie, dossier), horloge.fichier, journal, depart=8261
    ) as adresse:
        yield {
            r: Poste(adresse, "X-Gestion-MP", f"GMP {r}", cookie=f"gestion_mp_session={j}")
            for r, j in jetons.items()
        }


def commit() -> str:
    """Le commit du code de Gestion MP servi."""
    import subprocess

    sortie = subprocess.run(  # noqa: S603 — git, arguments à nous
        ["git", "-C", str(GESTION_MP), "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return sortie.stdout.strip() or "?"
