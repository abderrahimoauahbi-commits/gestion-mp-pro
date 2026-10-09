"""Parité par l'API : les deux serveurs lancés côte à côte, chacun sur sa base d'essai.

- Gestion MP : son interpréteur, son code (`~/gestion-mp`, lecture seule), sur la **copie**,
  sur un port libre au-dessus de 8100 (jamais 8030), sans tâche de fond, sauvegardes et pièces
  dans un dossier temporaire.
- PRO : ce dépôt, sur la base **reprise**, port libre au-dessus de 8100, sans tâche de fond.

L'année d'essai n'a aucun compte : un compte de chaque rôle comparé (direction, alimentation)
est inscrit dans chaque base d'essai, avec une session ouverte à la main (jeton tiré au hasard,
seule son empreinte est gardée, comme les deux logiciels le font) — aucun code n'est saisi.
Les serveurs sont toujours arrêtés en sortie (`with`).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import parite_bases as pb
from sqlalchemy import create_engine, select, text
from sqlalchemy.pool import NullPool

ROLES = ("direction", "alimentation")
DELAI_S = 60


def port_libre(depart: int = 8101) -> int:
    """Le premier port libre au-dessus de 8100 (8020, 8030, 8040, 8050 ne sont jamais pris)."""
    for port in range(depart, 8200):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("Aucun port libre entre 8101 et 8199")


@dataclass
class Client:
    """Un poste connecté à un serveur : cookie de session et en-tête de l'écran."""

    base: str
    cookie: str
    entete: str

    def appeler(self, methode: str, chemin: str, corps: Any = None) -> tuple[int, Any]:
        """Une requête ; rend (statut, JSON ou texte)."""
        donnees = None if corps is None else json.dumps(corps).encode()
        requete = urllib.request.Request(  # noqa: S310 — adresse locale construite ici
            self.base + chemin, data=donnees, method=methode
        )
        requete.add_header("Cookie", self.cookie)
        requete.add_header(self.entete, "1")
        if donnees is not None:
            requete.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(requete, timeout=120) as r:  # noqa: S310
                return r.status, _lu(r.read())
        except urllib.error.HTTPError as e:
            return e.code, _lu(e.read())

    def get(self, chemin: str) -> Any:
        """Un GET qui doit réussir."""
        statut, corps = self.appeler("GET", chemin)
        if statut != 200:  # noqa: PLR2004
            raise AssertionError(f"GET {self.base}{chemin} → {statut} : {str(corps)[:300]}")
        return corps


def _lu(octets: bytes) -> Any:
    try:
        return json.loads(octets)
    except ValueError:
        return octets.decode(errors="replace")


def _jeton() -> tuple[str, str]:
    jeton = secrets.token_urlsafe(32)
    return jeton, hashlib.sha256(jeton.encode()).hexdigest()


def comptes_gestion_mp(copie: str) -> dict[str, str]:
    """Un compte par rôle dans la copie de Gestion MP, et sa session : rôle → jeton."""
    jetons = {}
    moteur = create_engine(copie, poolclass=NullPool)
    with moteur.begin() as c:
        for role in ROLES:
            jeton, empreinte = _jeton()
            uid = c.execute(
                text(
                    "INSERT INTO utilisateur (identifiant, nom, role, cree_le) "
                    "VALUES (:i, :n, :r, now()) ON CONFLICT (identifiant) "
                    "DO UPDATE SET role = :r RETURNING id"
                ),
                {"i": f"parite-{role}", "n": f"Parité {role}", "r": role},
            ).scalar_one()
            c.execute(
                text("INSERT INTO session_ouverte VALUES (:e, :u, :x)"),
                {"e": empreinte, "u": uid, "x": datetime.now() + timedelta(days=1)},  # noqa: DTZ005
            )
            jetons[role] = jeton
    moteur.dispose()
    return jetons


def comptes_pro(adresse: str) -> dict[str, str]:
    """Un compte par rôle dans la base PRO reprise, et sa session : rôle → jeton."""
    from sqlalchemy.orm import Session

    from gestion_mp_pro.modeles import SessionOuverte, Utilisateur
    from gestion_mp_pro.modeles.enums import Role

    jetons = {}
    moteur = create_engine(adresse, poolclass=NullPool)
    with Session(moteur) as s, s.begin():
        for role in ROLES:
            ident = f"parite-{role}"
            u = s.scalar(select(Utilisateur).where(Utilisateur.identifiant == ident))
            if u is None:
                u = Utilisateur(identifiant=ident, nom=f"Parité {role}", role=Role(role))
                s.add(u)
                s.flush()
            jeton, empreinte = _jeton()
            fin = datetime.now(UTC) + timedelta(days=1)  # l'horloge réelle : celle du serveur
            s.add(SessionOuverte(empreinte=empreinte, utilisateur_id=u.id, expire_le=fin))
            jetons[role] = jeton
    moteur.dispose()
    return jetons


def _attendre(adresse: str, processus: subprocess.Popen[bytes], journal: Path) -> None:
    fin = time.monotonic() + DELAI_S
    while time.monotonic() < fin:
        if processus.poll() is not None:
            raise SystemExit(f"Serveur arrêté au démarrage :\n{journal.read_text()[-3000:]}")
        with suppress(OSError):
            with urllib.request.urlopen(adresse + "/api/sante", timeout=2):  # noqa: S310
                return
        time.sleep(0.3)
    raise SystemExit(f"Serveur muet après {DELAI_S} s : {adresse}")


def _lancer(
    commande: list[str], env: dict[str, str], cwd: Path, journal: Path
) -> subprocess.Popen[bytes]:
    with journal.open("wb") as sortie:
        return subprocess.Popen(  # noqa: S603
            commande, cwd=cwd, env=env, stdout=sortie, stderr=subprocess.STDOUT
        )


@dataclass
class Serveurs:
    """Les postes connectés aux deux serveurs, par rôle."""

    gestion_mp: dict[str, Client]
    pro: dict[str, Client]
    versions: dict[str, str]


def _env_gestion_mp(copie: str, dossier: Path, port: int) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTION")}
    return env | {
        "GESTION_MP_BASE": copie,
        "GESTION_MP_PORT": str(port),
        "GESTION_MP_TACHES": "0",
        "GESTION_MP_SAUVEGARDES": str(dossier / "gmp-sauvegardes"),
        "GESTION_MP_PIECES": str(dossier / "gmp-pieces"),
        "PYTHONPATH": str(pb.GESTION_MP),
    }


def _env_pro(adresse: str, dossier: Path, port: int) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTION")}
    return env | {
        "GESTIONMPPRO_BASE": adresse,
        "GESTIONMPPRO_PORT": str(port),
        "GESTIONMPPRO_TACHES": "0",
        "GESTIONMPPRO_SAUVEGARDES": str(dossier / "pro-sauvegardes"),
        "GESTIONMPPRO_PIECES": str(dossier / "pro-pieces"),
    }


@contextmanager
def demarrer(bases: pb.Bases, dossier: Path) -> Iterator[Serveurs]:
    """Lance les deux serveurs, ouvre les sessions, rend les postes ; arrête tout en sortie."""
    from gestion_mp_pro import __version__
    from gestion_mp_pro.config import COOKIE_SESSION, ENTETE_ANTI_FALSIFICATION

    port_gmp = port_libre()
    port_pro = port_libre(port_gmp + 1)
    uvicorn = ["-m", "uvicorn", "--host", "127.0.0.1", "--no-access-log", "--port"]
    gmp = _lancer(
        [str(pb.PYTHON_GESTION_MP), *uvicorn, str(port_gmp), "gestion_mp.main:app"],
        _env_gestion_mp(bases.copie, dossier, port_gmp),
        pb.GESTION_MP,
        dossier / "gestion_mp.log",
    )
    pro = _lancer(
        [sys.executable, *uvicorn, str(port_pro), "gestion_mp_pro.main:app"],
        _env_pro(bases.pro, dossier, port_pro),
        Path(__file__).resolve().parent.parent,
        dossier / "pro.log",
    )
    try:
        url_gmp, url_pro = f"http://127.0.0.1:{port_gmp}", f"http://127.0.0.1:{port_pro}"
        _attendre(url_gmp, gmp, dossier / "gestion_mp.log")
        _attendre(url_pro, pro, dossier / "pro.log")
        jg, jp = comptes_gestion_mp(bases.copie), comptes_pro(bases.pro)
        yield Serveurs(
            {r: Client(url_gmp, f"gestion_mp_session={jg[r]}", "X-Gestion-MP") for r in ROLES},
            {
                r: Client(url_pro, f"{COOKIE_SESSION}={jp[r]}", ENTETE_ANTI_FALSIFICATION)
                for r in ROLES
            },
            {"gestion_mp": pb_commit(), "pro": __version__},
        )
    finally:
        for p in (gmp, pro):
            _arreter(p)


@contextmanager
def gestion_mp_seul(adresse: str, dossier: Path) -> Iterator[Client]:
    """Gestion MP seul, sur une base d'essai (copie traduite), compte de direction ; arrêté
    en sortie."""
    port = port_libre(8150)
    journal = dossier / "gestion_mp_traduit.log"
    uvicorn = ["-m", "uvicorn", "--host", "127.0.0.1", "--no-access-log", "--port", str(port)]
    p = _lancer(
        [str(pb.PYTHON_GESTION_MP), *uvicorn, "gestion_mp.main:app"],
        _env_gestion_mp(adresse, dossier, port),
        pb.GESTION_MP,
        journal,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        _attendre(url, p, journal)
        jeton = comptes_gestion_mp(adresse)["direction"]
        yield Client(url, f"gestion_mp_session={jeton}", "X-Gestion-MP")
    finally:
        _arreter(p)


def _arreter(p: subprocess.Popen[bytes]) -> None:
    p.terminate()
    with suppress(subprocess.TimeoutExpired):
        p.wait(timeout=15)
    if p.poll() is None:
        p.kill()
        p.wait()


def pb_commit() -> str:
    """Le commit du code de Gestion MP servi."""
    sortie = subprocess.run(  # noqa: S603
        ["git", "-C", str(pb.GESTION_MP), "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return sortie.stdout.strip()
