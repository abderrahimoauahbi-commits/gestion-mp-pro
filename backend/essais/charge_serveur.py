"""Épreuve de charge : le vrai serveur (uvicorn, processus d'ARCHITECTURE § 12) et ses postes.

- Le serveur est lancé comme `scripts/demarrer.sh` le lance (`uvicorn gestion_mp_pro.main:app
  --workers N`, `GESTIONMPPRO_PROCESSUS`, 2 par défaut), sur un port libre **au-dessus de 8100**
  (jamais 8020, 8030, 8040, 8050), sans tâche de fond, sauvegardes et pièces dans un dossier
  temporaire ; il est toujours arrêté en sortie (`with`).
- Les postes : un compte par rôle (`charge-direction`, `charge-achats`, `charge-alimentation`),
  inscrit dans la base d'essai avec un code tiré au hasard, puis **connecté par la vraie route**
  (`POST /api/connexion`) : chaque poste a sa session, comme vingt personnes dans l'usine.
"""

from __future__ import annotations

import http.client
import json
import os
import secrets
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from parite_serveurs import port_libre
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

PROCESSUS = int(os.environ.get("GESTIONMPPRO_PROCESSUS", "2"))
"""ARCHITECTURE § 12 : « FastAPI (uvicorn, 2 processus) »."""
ROLES = ("direction", "achats", "alimentation")
DELAI_S = 90


@dataclass
class Poste:
    """Un poste connecté : sa connexion HTTP gardée ouverte (comme un navigateur), son cookie."""

    hote: str
    port: int
    cookie: str = ""
    entete: str = "X-Gestion-MP-Pro"
    _cnx: http.client.HTTPConnection | None = field(default=None, repr=False)

    def appeler(self, methode: str, chemin: str, corps: Any = None) -> tuple[int, Any, float]:
        """Une requête ; rend (statut, corps lu, durée en secondes, lecture du corps comprise)."""
        donnees = None if corps is None else json.dumps(corps).encode()
        entetes = {self.entete: "1", "Cookie": self.cookie}
        if donnees is not None:
            entetes["Content-Type"] = "application/json"
        for essai in range(2):
            debut = time.perf_counter()
            try:
                cnx = self._connexion()
                cnx.request(methode, chemin, body=donnees, headers=entetes)
                r = cnx.getresponse()
                brut = r.read()
                duree = time.perf_counter() - debut
                break
            except (http.client.HTTPException, ConnectionError):
                self.fermer()
                if essai:
                    raise
        if r.getheader("Set-Cookie") and "session" in (r.getheader("Set-Cookie") or ""):
            self.cookie = (r.getheader("Set-Cookie") or "").split(";", 1)[0]
        type_ = r.getheader("Content-Type") or ""
        lu: Any = json.loads(brut) if "json" in type_ and brut else brut
        return r.status, lu, duree

    def get(self, chemin: str) -> Any:
        """Un GET qui doit réussir."""
        statut, corps, _ = self.appeler("GET", chemin)
        if statut != 200:  # noqa: PLR2004
            raise AssertionError(f"GET {chemin} → {statut} : {str(corps)[:300]}")
        return corps

    def ok(self, methode: str, chemin: str, corps: Any = None) -> Any:
        """Une écriture qui doit réussir (200 ou 201)."""
        statut, lu, _ = self.appeler(methode, chemin, corps)
        if statut not in (200, 201):
            raise AssertionError(f"{methode} {chemin} → {statut} : {str(lu)[:400]}")
        return lu

    def _connexion(self) -> http.client.HTTPConnection:
        if self._cnx is None:
            self._cnx = http.client.HTTPConnection(self.hote, self.port, timeout=300)
        return self._cnx

    def fermer(self) -> None:
        """Ferme la connexion gardée."""
        if self._cnx is not None:
            self._cnx.close()
            self._cnx = None


@dataclass
class Serveur:
    """Le serveur lancé : son adresse et les codes des comptes de l'épreuve."""

    port: int
    codes: dict[str, str]
    entete: str
    processus: int

    def poste(self, role: str) -> Poste:
        """Un nouveau poste du rôle, connecté par la vraie route."""
        p = Poste("127.0.0.1", self.port, entete=self.entete)
        p.ok("POST", "/api/connexion", {"identifiant": f"charge-{role}", "code": self.codes[role]})
        return p

    def anonyme(self) -> Poste:
        """Un poste non connecté (pour les connexions ratées)."""
        return Poste("127.0.0.1", self.port, entete=self.entete)


def inscrire_comptes(adresse: str) -> dict[str, str]:
    """Un compte par rôle dans la base d'essai (code tiré au hasard) : rôle → code."""
    from gestion_mp_pro.modeles import Utilisateur
    from gestion_mp_pro.modeles.enums import Role
    from gestion_mp_pro.services.comptes import hacher

    codes = {}
    moteur = create_engine(adresse, poolclass=NullPool)
    with Session(moteur) as s, s.begin():
        for role in ROLES:
            code = f"{secrets.randbelow(10_000):04d}" if role == "alimentation" else (
                secrets.token_urlsafe(12)
            )  # fmt: skip
            ident = f"charge-{role}"
            u = s.scalar(select(Utilisateur).where(Utilisateur.identifiant == ident))
            if u is None:
                u = Utilisateur(identifiant=ident, nom=f"Charge {role}", role=Role(role))
                s.add(u)
            u.empreinte_code = hacher(code)
            codes[role] = code
    moteur.dispose()
    return codes


def _attendre(port: int, p: subprocess.Popen[bytes], journal: Path) -> None:
    fin = time.monotonic() + DELAI_S
    while time.monotonic() < fin:
        if p.poll() is not None:
            fin_du_journal = journal.read_text(encoding="utf-8")[-3000:]
            raise SystemExit(f"Serveur arrêté au démarrage :\n{fin_du_journal}")
        with suppress(OSError, http.client.HTTPException):
            cnx = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            cnx.request("GET", "/api/sante")
            if cnx.getresponse().status < 500:  # noqa: PLR2004
                return
        time.sleep(0.3)
    raise SystemExit(f"Serveur muet après {DELAI_S} s (port {port})")


@contextmanager
def servir(adresse: str, dossier: Path, processus: int = PROCESSUS) -> Iterator[Serveur]:
    """Lance uvicorn sur la base, inscrit les comptes ; arrête tout en sortie."""
    from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

    codes = inscrire_comptes(adresse)
    port = port_libre(8111)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTIONMPPRO")}
    env |= {
        "GESTIONMPPRO_BASE": adresse,
        "GESTIONMPPRO_PORT": str(port),
        "GESTIONMPPRO_TACHES": "0",
        "GESTIONMPPRO_SAUVEGARDES": str(dossier / "sauvegardes"),
        "GESTIONMPPRO_PIECES": str(dossier / "pieces"),
    }
    commande = [sys.executable, "-m", "uvicorn", "gestion_mp_pro.main:app", "--host",
                "127.0.0.1", "--port", str(port), "--no-access-log"]  # fmt: skip
    if processus > 1:
        commande += ["--workers", str(processus)]
    journal = dossier / f"serveur-{port}.log"
    with journal.open("wb") as sortie:
        p = subprocess.Popen(  # noqa: S603
            commande,
            cwd=Path(__file__).resolve().parent.parent,
            env=env,
            stdout=sortie,
            stderr=subprocess.STDOUT,
        )
    try:
        _attendre(port, p, journal)
        yield Serveur(port, codes, ENTETE_ANTI_FALSIFICATION, processus)
    finally:
        p.terminate()
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
