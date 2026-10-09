"""Outils du scénario de bout en bout (lot V2) : poste HTTP, vérifications, horloge.

- `Poste` : un compte connecté à un vrai serveur, par HTTP (urllib, cookie de session, en-tête
  de l'écran) ; chaque appel rend une `Reponse` (statut, corps JSON ou texte, en-têtes).
- `Verif` : chaque valeur attendue est écrite dans le script **avant** le geste (calculée à la
  main) puis comparée à ce que le serveur rend, aux tolérances de PLAN-DE-RECETTE § 7.5 ; un
  écart est noté (le scénario continue pour tout montrer) ; chaque refus attendu aussi (statut,
  code, phrase).
- `Horloge` : le jour de l'usine que le serveur lit (fichier partagé, voir `scenario_serveur`).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

KG = 0.001
"""Tolérance des quantités (PLAN-DE-RECETTE § 7.5)."""
MAD = 0.01
"""Tolérance des montants (au centime)."""
UNITAIRE = 1e-6
"""Tolérance relative des prix et coûts unitaires (CMUP au millionième)."""
RATIO = 1e-6
"""Tolérance absolue des ratios (OTIF, parts, taux)."""


@dataclass
class Reponse:
    """Ce que le serveur a rendu."""

    statut: int
    corps: Any
    entetes: dict[str, str] = field(default_factory=dict)

    @property
    def code(self) -> str | None:
        """Le code d'erreur PRO (`{"detail", "code"}`), s'il y en a un."""
        return self.corps.get("code") if isinstance(self.corps, dict) else None

    @property
    def detail(self) -> str:
        """La phrase du refus, s'il y en a une."""
        if isinstance(self.corps, dict):
            return str(self.corps.get("detail", ""))
        return str(self.corps)[:300]


class EchecAppel(AssertionError):
    """Un appel qui devait réussir a été refusé : le scénario ne peut pas continuer l'étape."""


class Poste:
    """Un compte connecté (cookie de session) à un serveur."""

    def __init__(self, adresse: str, entete: str, nom: str, cookie: str = "") -> None:
        self.adresse = adresse
        self.cookie = cookie
        self.entete = entete
        self.nom = nom
        self.cookies = CookieJar()
        self._ouvreur = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.appels = 0

    def appeler(self, methode: str, chemin: str, corps: Any = None) -> Reponse:
        """Une requête sous `/api` ; rend la réponse quel que soit le statut."""
        donnees = None if corps is None else json.dumps(corps, default=_json).encode()
        requete = urllib.request.Request(  # noqa: S310 — adresse locale construite ici
            f"{self.adresse}/api{chemin}", data=donnees, method=methode
        )
        requete.add_header(self.entete, "1")
        if self.cookie:
            requete.add_header("Cookie", self.cookie)
        if donnees is not None:
            requete.add_header("Content-Type", "application/json")
        self.appels += 1
        try:
            with self._ouvreur.open(requete, timeout=300) as r:
                return Reponse(r.status, _lu(r.read(), r.headers), dict(r.headers))
        except urllib.error.HTTPError as e:
            return Reponse(e.code, _lu(e.read(), e.headers), dict(e.headers))

    def ok(self, methode: str, chemin: str, corps: Any = None, attendu: int = 0) -> Any:
        """Un appel qui doit réussir (2xx, ou exactement `attendu`) ; rend le corps."""
        r = self.appeler(methode, chemin, corps)
        bon = r.statut == attendu if attendu else 200 <= r.statut < 300  # noqa: PLR2004
        if not bon:
            raise EchecAppel(f"{self.nom} : {methode} {chemin} → {r.statut} {r.detail}")
        return r.corps

    def get(self, chemin: str) -> Any:
        """Une lecture qui doit réussir."""
        return self.ok("GET", chemin)

    def post(self, chemin: str, corps: Any = None) -> Any:
        """Un geste qui doit réussir."""
        return self.ok("POST", chemin, {} if corps is None else corps)

    def put(self, chemin: str, corps: Any) -> Any:
        """Une modification qui doit réussir."""
        return self.ok("PUT", chemin, corps)


def _json(valeur: object) -> object:
    if isinstance(valeur, Decimal):
        return float(valeur)
    if isinstance(valeur, date):
        return valeur.isoformat()
    raise TypeError(repr(valeur))


def _lu(octets: bytes, entetes: Any) -> Any:
    if "json" in (entetes.get("Content-Type") or ""):
        try:
            return json.loads(octets)
        except ValueError:
            pass
    if "spreadsheet" in (entetes.get("Content-Type") or ""):
        return octets
    return octets.decode(errors="replace")


@dataclass
class Ligne:
    """Une étape du résultat."""

    numero: str
    titre: str
    verifications: int = 0
    echecs: list[str] = field(default_factory=list)
    duree: float = 0.0


class Verif:
    """Les vérifications du scénario : comptées, écarts gardés pour le rapport."""

    def __init__(self) -> None:
        self.etapes: list[Ligne] = []
        self.courante = Ligne("0", "préparation")

    @property
    def total(self) -> int:
        """Nombre de valeurs vérifiées."""
        return sum(e.verifications for e in self.etapes) + self.courante.verifications

    @property
    def echecs(self) -> list[str]:
        """Tous les écarts, étape par étape."""
        return [f"[{e.numero}] {x}" for e in self.etapes for x in e.echecs]

    @contextmanager
    def etape(self, numero: str, titre: str) -> Iterator[Ligne]:
        """Une étape : ses vérifications et ses écarts ; un appel refusé l'arrête (noté)."""
        self.courante = Ligne(numero, titre)
        debut = time.monotonic()
        try:
            yield self.courante
        except EchecAppel as e:
            self.courante.echecs.append(f"étape interrompue : {e}")
        except Exception as e:  # noqa: BLE001 — une étape cassée est notée, les suivantes jouent
            self.courante.echecs.append(f"étape interrompue : {type(e).__name__} {e}")
        finally:
            self.courante.duree = time.monotonic() - debut
            self.etapes.append(self.courante)
            self.courante = Ligne("-", "hors étape")

    def _noter(self, juste: bool, message: str) -> bool:
        self.courante.verifications += 1
        if not juste:
            self.courante.echecs.append(message)
        return juste

    def egal(self, libelle: str, obtenu: Any, attendu: Any, tol: float | None = None) -> bool:
        """Une valeur : exacte, ou à `tol` près (absolue) pour un nombre."""
        if tol is not None and _nombre(obtenu) and _nombre(attendu):
            juste = abs(float(obtenu) - float(attendu)) <= tol + 1e-12
        else:
            juste = obtenu == attendu
        return self._noter(juste, f"{libelle} : obtenu {obtenu!r}, attendu {attendu!r}")

    def proche(self, libelle: str, obtenu: Any, attendu: float, rel: float = UNITAIRE) -> bool:
        """Un coût unitaire : à `rel` près en relatif."""
        juste = _nombre(obtenu) and abs(float(obtenu) - attendu) <= rel * max(1.0, abs(attendu))
        return self._noter(bool(juste), f"{libelle} : obtenu {obtenu!r}, attendu {attendu!r}")

    def vrai(self, libelle: str, condition: bool, detail: str = "") -> bool:
        """Une condition."""
        return self._noter(bool(condition), f"{libelle} {detail}".strip())

    def refus(
        self, libelle: str, r: Reponse, statut: int, code: str | None = None, phrase: str = ""
    ) -> bool:
        """Un refus attendu : statut, code et (morceau de) phrase vérifiés un à un."""
        bon = self.egal(f"{libelle} (statut)", r.statut, statut)
        if code is not None:
            bon = self.egal(f"{libelle} (code)", r.code, code) and bon
        if phrase:
            bon = self.vrai(f"{libelle} (phrase)", phrase in r.detail, f": « {r.detail} »") and bon
        return bon


def _nombre(x: Any) -> bool:
    return isinstance(x, int | float | Decimal) and not isinstance(x, bool)


class Horloge:
    """Le jour de l'usine, écrit dans un fichier que le serveur lit à chaque instant demandé."""

    def __init__(self, fichier: Path) -> None:
        self.fichier = fichier
        self.jour: date | None = None

    def aller(self, jour: date, heure: int = 8) -> None:
        """Le serveur se croit `jour` à `heure` h (plus le temps écoulé depuis)."""
        self.jour = jour
        self.fichier.write_text(f"{jour.isoformat()}T{heure:02d}:00:00")


MOTIFS_MONETAIRES = (
    "prix",
    "montant",
    "valeur",
    "cout",
    "cmup",
    "budget",
    "cours",
    "revient",
    "tva",
    "frais",
    "economie",
)
"""Les motifs de `securite.CLES_MONETAIRES` (API-PRO § 0.4), relus ici sans importer le paquet."""


def montants_visibles(corps: Any, chemin: str = "") -> list[str]:
    """Les chemins des champs monétaires non nuls d'une réponse (balayage « aucun prix »)."""
    trouves: list[str] = []
    if isinstance(corps, dict):
        for cle, valeur in corps.items():
            ici = f"{chemin}.{cle}"
            monetaire = cle.startswith(MOTIFS_MONETAIRES) or cle.endswith("_mad")
            if monetaire and valeur not in (None, 0, 0.0, "", [], {}):
                trouves.append(ici)
            else:
                trouves += montants_visibles(valeur, ici)
    elif isinstance(corps, list):
        for i, x in enumerate(corps):
            trouves += montants_visibles(x, f"{chemin}[{i}]")
    return trouves
