"""Accès de la vérification : la base en SQL direct, l'application par HTTP (lot V1).

Rien du paquet `gestion_mp_pro` n'est importé. Le serveur PRO est lancé comme un programme
(`python -m uvicorn gestion_mp_pro.main:app`) sur un port libre au-dessus de 8100, contre la
base vérifiée, puis arrêté. Le compte de lecture est un compte de direction technique
(« verification-chiffres ») écrit en SQL avec une empreinte scrypt au format de PRO
(`scrypt$<sel>$<empreinte>`, N = 2¹⁴, r = 8, p = 1, 32 octets), au code tiré au hasard et jamais
écrit nulle part ; il est fermé (inactif, sessions effacées) à la fin.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

ENTETE = {"X-Gestion-MP-PRO": "1", "Content-Type": "application/json"}
IDENTIFIANT = "verification-chiffres"
PORTS = range(8101, 8999)


def url_libpq(url: str) -> str:
    """`postgresql+psycopg:///base` (forme SQLAlchemy de PRO) → `postgresql:///base`."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def nom_de_base(url: str) -> str:
    """Le nom de la base d'une adresse PostgreSQL."""
    return urllib.parse.urlsplit(url_libpq(url)).path.lstrip("/").split("?")[0]


def empreinte(code: str) -> str:
    """L'empreinte scrypt d'un code, au format des comptes de PRO."""
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(code.encode(), salt=sel, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${sel.hex()}${h.hex()}"


def _float(v: Any) -> Any:
    """Les décimaux en `float` (les comparaisons se font aux tolérances)."""
    return float(v) if isinstance(v, Decimal) else v


class Base:
    """La base vérifiée, lue en SQL direct, en lecture seule."""

    def __init__(self, url: str) -> None:
        self.url = url_libpq(url)
        self.connexion = psycopg.connect(self.url, autocommit=True)

    def ecrire(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Une écriture (le compte de lecture seulement), validée aussitôt."""
        with self.connexion.cursor() as c:
            c.execute(requete, params)
            return [tuple(r) for r in c.fetchall()] if c.description else []

    def sql(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Les lignes d'une lecture, décimaux en `float`."""
        with self.connexion.cursor() as c:
            c.execute(requete, params)
            return [tuple(_float(v) for v in r) for r in c.fetchall()]

    def ouvrir_compte(self) -> str:
        """Crée (ou rouvre) le compte de lecture, rend son code (tiré au hasard)."""
        code = secrets.token_urlsafe(24)
        self.ecrire(
            "INSERT INTO utilisateur (identifiant, nom, role, empreinte_code, actif) "
            "VALUES (%s, 'Vérification des chiffres', 'direction', %s, true) "
            "ON CONFLICT (identifiant) DO UPDATE SET empreinte_code = excluded.empreinte_code, "
            "actif = true, historique = false, role = 'direction'",
            (IDENTIFIANT, empreinte(code)),
        )
        return code

    def fermer_compte(self) -> None:
        """Le compte de lecture fermé : inactif, sessions effacées, code oublié."""
        self.ecrire(
            "DELETE FROM session WHERE utilisateur_id = "
            "(SELECT id FROM utilisateur WHERE identifiant = %s)",
            (IDENTIFIANT,),
        )
        self.ecrire(
            "UPDATE utilisateur SET actif = false, empreinte_code = '' WHERE identifiant = %s",
            (IDENTIFIANT,),
        )

    def fermer(self) -> None:
        """La connexion fermée."""
        self.connexion.close()


class Application:
    """L'API d'un serveur PRO, lue par HTTP avec une session de direction."""

    def __init__(self, adresse: str) -> None:
        self.adresse = adresse.rstrip("/")
        self.ouvreur = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def connecter(self, identifiant: str, code: str) -> None:
        """Ouvre la session (route 10)."""
        corps = json.dumps({"identifiant": identifiant, "code": code}).encode()
        requete = urllib.request.Request(  # noqa: S310 (adresse http du serveur vérifié)
            self.adresse + "/api/connexion", data=corps, headers=ENTETE, method="POST"
        )
        self.ouvreur.open(requete, timeout=60).read()

    def get(self, chemin: str, **params: Any) -> Any:
        """La réponse JSON d'une lecture (paramètres répétés pour une liste)."""
        propres = {k: v for k, v in params.items() if v is not None}
        q = "?" + urllib.parse.urlencode(propres, doseq=True) if propres else ""
        adresse = self.adresse + "/api" + chemin + q
        requete = urllib.request.Request(adresse, headers=ENTETE)  # noqa: S310 (idem)
        try:
            with self.ouvreur.open(requete, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"GET {chemin}{q} : {exc.code} {exc.read()[:300]!r}") from exc


class Serveur:
    """Un serveur PRO lancé sur un port libre contre la base vérifiée, arrêté à la fin."""

    def __init__(self, url_base: str) -> None:
        self.port = _port_libre()
        self.dossier = tempfile.mkdtemp(prefix="verification-chiffres-")
        env = dict(os.environ)
        env.update(
            GESTIONMPPRO_BASE=url_base,
            GESTIONMPPRO_TACHES="0",
            GESTIONMPPRO_SAUVEGARDES=str(Path(self.dossier) / "sauvegardes"),
            GESTIONMPPRO_PIECES=str(Path(self.dossier) / "pieces"),
        )
        commande = [sys.executable, "-m", "uvicorn", "gestion_mp_pro.main:app"]
        commande += ["--host", "127.0.0.1", "--port", str(self.port), "--no-access-log"]
        self.journal = Path(self.dossier) / "serveur.log"
        with self.journal.open("wb") as sortie:  # un fichier : un tube plein bloquerait le serveur
            self.processus = subprocess.Popen(  # noqa: S603 (programme et arguments fixes)
                commande, env=env, stdout=subprocess.DEVNULL, stderr=sortie
            )
        self.adresse = f"http://127.0.0.1:{self.port}"
        self._attendre()

    def _attendre(self) -> None:
        """Attend que `/api/sante` réponde (60 s au plus)."""
        fin = time.monotonic() + 60
        while time.monotonic() < fin:
            if self.processus.poll() is not None:
                erreur = self.journal.read_text(encoding="utf-8", errors="replace")
                self.arreter()
                raise RuntimeError(f"Le serveur PRO s'est arrêté au démarrage :\n{erreur[-2000:]}")
            try:
                urllib.request.urlopen(self.adresse + "/api/sante", timeout=2).read()  # noqa: S310
                return
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.3)
        self.arreter()
        raise RuntimeError("Le serveur PRO n'a pas répondu en 60 s.")

    def arreter(self) -> None:
        """Arrête le serveur (et attend sa fin), puis efface son dossier temporaire."""
        if self.processus.poll() is None:
            self.processus.terminate()
            try:
                self.processus.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.processus.kill()
                self.processus.wait()
        shutil.rmtree(self.dossier, ignore_errors=True)


def _port_libre() -> int:
    """Le premier port libre au-dessus de 8100."""
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("Aucun port libre entre 8101 et 8998.")


class AccesReel:
    """L'accès complet : l'application (HTTP) et la base (SQL), sur la même base."""

    def __init__(self, application: Application, base: Base) -> None:
        self.application = application
        self.base = base

    def get(self, chemin: str, **params: Any) -> Any:
        """Une lecture de l'API."""
        return self.application.get(chemin, **params)

    def sql(self, requete: str, params: Any = None) -> list[tuple[Any, ...]]:
        """Une lecture SQL."""
        return self.base.sql(requete, params)
