# ruff: noqa: S603, S607  (outils PostgreSQL et interpréteur des essais, arguments à nous)
"""Un vrai serveur (uvicorn) sur une base jetable à lui, pour les restaurations (lot D10).

`gestion_mp_pro_d10_jetable_essai` est créée, migrée, peuplée de deux comptes (direction,
achats), servie sur un port libre, puis détruite ; ses sauvegardes et ses pièces vont dans un
dossier temporaire. Jamais la base d'essai commune, jamais une base ni un dossier réels.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx2
import pytest

from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

__all__ = ["BASE", "URL", "Serveur", "serveur", "sql"]

BASE = "gestion_mp_pro_d10_jetable_essai"
URL = f"postgresql+psycopg:///{BASE}"
DOSSIER_SERVEUR = Path(__file__).resolve().parents[2]
CODES = {"direction": "direction-1", "achats": "achats-12"}

PREPARER = """
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Utilisateur
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services import comptes
from gestion_mp_pro.services.installation import migrer
migrer()
with fabrique()() as s, s.begin():
    for role, code in (("direction", "direction-1"), ("achats", "achats-12")):
        s.add(Utilisateur(identifiant=role, nom=role.capitalize(), role=Role(role),
                          empreinte_code=comptes.hacher(code), actif=True))
"""


def sql(requete: str, base: str = BASE) -> str:
    """Une requête psql sur la base jetable ; rend la sortie brute."""
    sortie = subprocess.run(
        ["psql", "-X", "-At", "-v", "ON_ERROR_STOP=1", "-d", base, "-c", requete],
        capture_output=True,
        text=True,
        check=True,
    )
    return sortie.stdout.strip()


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class Serveur:
    """Le serveur jetable : son adresse, ses dossiers, son environnement, un client direction."""

    adresse: str
    sauvegardes: Path
    pieces: Path
    env: dict[str, str]
    direction: httpx2.Client

    def client(self, identifiant: str) -> httpx2.Client:
        """Un client connecté (compte direction ou achats)."""
        c = httpx2.Client(
            base_url=self.adresse, headers={ENTETE_ANTI_FALSIFICATION: "1"}, timeout=60
        )
        corps = {"identifiant": identifiant, "code": CODES[identifiant]}
        c.post("/api/connexion", json=corps).raise_for_status()
        return c

    def python(self, script: str) -> None:
        """Lance un script Python sur la base jetable (même environnement que le serveur)."""
        subprocess.run(  # noqa: S603 — l'interpréteur des essais, un script à nous
            [sys.executable, "-c", script], env=self.env, cwd=DOSSIER_SERVEUR, check=True
        )

    def attendre(self, condition: str, delai: float = 60) -> dict[str, object]:
        """Interroge `/api/sante` jusqu'à ce que `taches[restauration]` vaille `condition`."""
        fin = time.monotonic() + delai
        while time.monotonic() < fin:
            sante = httpx2.get(self.adresse + "/api/sante", timeout=10).json()
            if sante["taches"].get("restauration", "").startswith(condition):
                return dict(sante)
            time.sleep(0.2)
        raise AssertionError(f"restauration jamais « {condition} » : {sante}")


def _environnement(dossier: Path, port: int, taches: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTIONMPPRO_")}
    env.update(
        GESTIONMPPRO_BASE=URL,
        GESTIONMPPRO_TACHES="1" if taches else "0",
        GESTIONMPPRO_SAUVEGARDES=str(dossier / "sauvegardes"),
        GESTIONMPPRO_PIECES=str(dossier / "pieces"),
        GESTIONMPPRO_ECRAN=str(dossier / "sans-ecran"),
        GESTIONMPPRO_PORT=str(port),
    )
    return env


@pytest.fixture
def serveur(tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[Serveur]:
    """`@pytest.mark.parametrize("serveur", [True], indirect=True)` : avec les tâches de fond."""
    taches = bool(getattr(request, "param", False))
    subprocess.run(["dropdb", "--if-exists", "--force", BASE], check=True, capture_output=True)
    subprocess.run(["createdb", BASE], check=True, capture_output=True)
    port = _port_libre()
    env = _environnement(tmp_path, port, taches)
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", PREPARER], env=env, cwd=DOSSIER_SERVEUR, check=True
    )
    journal = (tmp_path / "serveur.log").open("w")
    commande = [sys.executable, "-m", "uvicorn", "gestion_mp_pro.main:app"]
    commande += ["--host", "127.0.0.1", "--port", str(port), "--no-access-log"]
    processus = subprocess.Popen(  # noqa: S603
        commande, env=env, cwd=DOSSIER_SERVEUR, stdout=journal, stderr=subprocess.STDOUT
    )
    adresse = f"http://127.0.0.1:{port}"
    try:
        for _ in range(300):
            try:
                httpx2.get(adresse + "/api/sante", timeout=2)
                break
            except httpx2.TransportError:
                time.sleep(0.1)
        s = Serveur(adresse, tmp_path / "sauvegardes" / BASE, tmp_path / "pieces" / BASE, env, None)  # type: ignore[arg-type]
        s.direction = s.client("direction")
        yield s
    finally:
        processus.terminate()
        processus.wait(20)
        journal.close()
        subprocess.run(["dropdb", "--if-exists", "--force", BASE], capture_output=True, check=False)
