"""Socle du simulateur : environnement, horloge de l'usine, postes connectés, journal.

- `preparer_environnement` : la base (`gestion_mp_pro_stress*_essai` exigé), aucune tâche de
  fond, sauvegardes et pièces dans un dossier de travail à part — **avant** tout import du paquet.
- `Horloge` : le jour de l'usine, avancé jour après jour ; chaque appel fait avancer l'heure
  d'une minute (`tic`) pour que les gestes d'une même journée soient ordonnés.
- `Poste` : un compte connecté (`TestClient`) ; chaque appel est consigné (route, rôle, statut,
  durée) et jugé contre le statut attendu : 5xx, 4xx inattendu, refus manquant, lenteur.
- `Journal` : `appels-annee-N.csv`, `anomalies.jsonl`, `journal-10-ans.md`, compteurs de volumes.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from datetime import time as heure_du_jour
from pathlib import Path
from typing import IO, Any

ICI = Path(__file__).resolve().parent
LENT_S = 1.0
BLOQUANT_S = 3.0
OK = (200, 201)
CREE = (201,)
SUPPRIME = (200, 204)
HEURE_DEBUT = 8
HEURE_FIN = 19


def preparer_environnement(base: str, travail: Path) -> None:
    """Règle les variables du serveur ; refuse toute base qui n'est pas une copie « stress »."""
    nom = base.rsplit("/", 1)[-1]
    if not (nom.startswith("gestion_mp_pro_stress") and nom.endswith("_essai")):
        raise SystemExit(f"Base refusée : « {nom} » (gestion_mp_pro_stress…_essai exigé)")
    os.environ["GESTIONMPPRO_BASE"] = base
    os.environ["GESTIONMPPRO_TACHES"] = "0"
    os.environ["GESTIONMPPRO_SAUVEGARDES"] = str(travail / "sauvegardes")
    os.environ["GESTIONMPPRO_PIECES"] = str(travail / "pieces")
    os.environ["GESTIONMPPRO_ECRAN"] = str(travail / "sans-ecran")
    os.environ.pop("GESTIONMPPRO_SAUVEGARDES_COPIE", None)


class Horloge:
    """Le jour et l'heure de l'usine, que le serveur lit (`services.horloge.fixer`)."""

    def __init__(self) -> None:
        self.jour = date(2026, 10, 15)
        self.instant: datetime | None = None

    def aller(self, jour: date, heure: int = HEURE_DEBUT) -> None:
        """Le serveur se croit `jour` à `heure` h."""
        from gestion_mp_pro.services import horloge

        self.jour = jour
        self.instant = datetime.combine(jour, heure_du_jour(heure, 0), tzinfo=horloge.FUSEAU)
        horloge.fixer(self.instant)

    def tic(self, minutes: int = 1) -> None:
        """L'heure avance (jamais au-delà de 19 h : la journée ne déborde pas sur la suivante)."""
        from gestion_mp_pro.services import horloge

        if self.instant is None:
            return
        suivant = self.instant + timedelta(minutes=minutes)
        if suivant.hour < HEURE_FIN:
            self.instant = suivant
            horloge.fixer(self.instant)


@dataclass
class Reponse:
    """Ce que le serveur a rendu."""

    statut: int
    corps: Any
    duree: float
    entetes: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """2xx."""
        return 200 <= self.statut < 300

    @property
    def code(self) -> str | None:
        """Le code d'erreur PRO (`{"detail", "code"}`), s'il y en a un."""
        return self.corps.get("code") if isinstance(self.corps, dict) else None

    @property
    def detail(self) -> str:
        """La phrase du refus, s'il y en a une."""
        if isinstance(self.corps, dict):
            return str(self.corps.get("detail", ""))[:400]
        return str(self.corps)[:400]


class EchecGeste(Exception):
    """Un appel qui devait réussir a été refusé : le geste en cours s'arrête (consigné)."""

    def __init__(self, reponse: Reponse, texte: str) -> None:
        super().__init__(texte)
        self.reponse = reponse


_ID = re.compile(r"/\d+(?=/|$)")
_CODE_DEVISE = re.compile(r"/devises/[A-Z]{3}")


def route_de(methode: str, chemin: str) -> str:
    """Le gabarit d'une route : identifiants remplacés par `{id}`, paramètres retirés."""
    sans_q = chemin.split("?", 1)[0]
    gabarit = _CODE_DEVISE.sub("/devises/{code}", _ID.sub("/{id}", sans_q))
    return f"{methode} {gabarit}"


class Journal:
    """Appels, anomalies, fil des mois et compteurs de volumes, écrits au fil de l'eau."""

    def __init__(self, dossier: Path, horloge: Horloge) -> None:
        self.dossier = dossier
        self.horloge = horloge
        dossier.mkdir(parents=True, exist_ok=True)
        self.md = dossier / "journal-10-ans.md"
        self.anomalies_f: IO[str] = (dossier / "anomalies.jsonl").open("a", encoding="utf-8")
        self.appels_f: IO[str] | None = None
        self.appels_csv: Any = None
        self.statuts: Counter[str] = Counter()
        self.volumes: Counter[str] = Counter()
        self.anomalies: Counter[str] = Counter()
        self.routes: Counter[str] = Counter()
        self.lentes: list[tuple[float, str]] = []
        self.nb_appels = 0
        self.duree_totale = 0.0

    def ouvrir_annee(self, annee: int) -> None:
        """Le fichier des appels de l'année simulée (un par année, pour rester lisible)."""
        if self.appels_f is not None:
            self.appels_f.close()
        chemin = self.dossier / f"appels-annee-{annee}.csv"
        neuf = not chemin.exists()
        self.appels_f = chemin.open("a", encoding="utf-8", newline="")
        self.appels_csv = csv.writer(self.appels_f)
        if neuf:
            self.appels_csv.writerow(["jour", "role", "route", "statut", "duree_ms", "note"])

    def appel(self, role: str, route: str, statut: int, duree: float, note: str) -> None:
        """Une ligne par appel."""
        self.nb_appels += 1
        self.duree_totale += duree
        self.statuts[str(statut)] += 1
        self.routes[route] += 1
        if self.appels_csv is not None:
            self.appels_csv.writerow(
                [self.horloge.jour.isoformat(), role, route, statut, round(duree * 1000), note]
            )

    def anomalie(self, classe: str, genre: str, detail: str, **champs: Any) -> None:
        """Une anomalie classée (CERTAIN / PROBABLE / QUESTION MÉTIER / PRÉSENTATION)."""
        self.anomalies[genre] += 1
        ligne = {"jour": self.horloge.jour.isoformat(), "classe": classe, "genre": genre}
        ligne |= champs
        ligne["detail"] = detail[:1500]
        self.anomalies_f.write(json.dumps(ligne, ensure_ascii=False, default=str) + "\n")
        self.anomalies_f.flush()

    def note(self, texte: str) -> None:
        """Une ligne du journal des mois (écrite tout de suite)."""
        with self.md.open("a", encoding="utf-8") as f:
            f.write(texte + "\n")
        sys.stdout.write(texte + "\n")
        sys.stdout.flush()

    def geste(self, nom: str, n: int = 1) -> None:
        """Un geste d'usine de plus (volumes du rapport)."""
        self.volumes[nom] += n

    def fermer(self) -> None:
        """Ferme les fichiers."""
        self.anomalies_f.close()
        if self.appels_f is not None:
            self.appels_f.close()


class Poste:
    """Un compte connecté à l'application en mémoire, qui consigne chaque appel."""

    def __init__(
        self,
        app: Any,
        journal: Journal,
        horloge: Horloge,
        *,
        role: str,
        identifiant: str,
        code: str,
    ) -> None:
        from fastapi.testclient import TestClient

        from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

        self.journal = journal
        self.horloge = horloge
        self.role = role
        self.identifiant = identifiant
        self.code = code
        self.client = TestClient(app, headers={ENTETE_ANTI_FALSIFICATION: "1"})
        self.connexions = 0

    def connecter(self, code: str | None = None) -> Reponse:
        """`POST /connexion` (le code peut avoir changé : remise à zéro annuelle)."""
        if code is not None:
            self.code = code
        self.connexions += 1
        return self.appeler(
            "POST",
            "/connexion",
            {"identifiant": self.identifiant, "code": self.code},
            note="connexion",
        )

    def appeler(
        self,
        methode: str,
        chemin: str,
        corps: Any = None,
        attendu: tuple[int, ...] = OK,
        *,
        note: str = "",
        _retente: bool = True,
    ) -> Reponse:
        """Un appel sous `/api`, consigné et jugé ; une session expirée se reconnecte une fois."""
        debut = time.perf_counter()
        brut = self.client.request(methode, "/api" + chemin, json=corps)
        duree = time.perf_counter() - debut
        try:
            lu = brut.json() if "json" in brut.headers.get("content-type", "") else brut.content
        except ValueError:
            lu = brut.text
        r = Reponse(brut.status_code, lu, duree, dict(brut.headers))
        self.horloge.tic()
        if r.statut == 401 and _retente and chemin != "/connexion":
            self.journal.appel(self.role, route_de(methode, chemin), 401, duree, "session expirée")
            self.connecter()
            return self.appeler(methode, chemin, corps, attendu, note=note, _retente=False)
        route = route_de(methode, chemin)
        self.journal.appel(self.role, route, r.statut, duree, note)
        self._juger(route, r, attendu, corps, note)
        return r

    def _juger(
        self, route: str, r: Reponse, attendu: tuple[int, ...], corps: Any, note: str
    ) -> None:
        champs = {"route": route, "role": self.role, "statut": r.statut, "note": note}
        if r.statut >= 500:
            self.journal.anomalie(
                "CERTAIN", "erreur_500", f"{r.detail} — corps envoyé : {_court(corps)}", **champs
            )
        elif r.statut not in attendu:
            if r.statut >= 400 and all(a < 400 for a in attendu):
                self.journal.anomalie(
                    "PROBABLE",
                    "refus_inattendu",
                    f"[{r.code}] {r.detail} — attendu {attendu} — corps : {_court(corps)}",
                    **champs,
                )
            elif r.statut < 400 and all(a >= 400 for a in attendu):
                self.journal.anomalie(
                    "PROBABLE",
                    "refus_manquant",
                    f"accepté alors qu'un refus {attendu} était attendu — corps : {_court(corps)}",
                    **champs,
                )
            else:
                self.journal.anomalie(
                    "PRESENTATION",
                    "statut_inattendu",
                    f"[{r.code}] {r.detail} — attendu {attendu}",
                    **champs,
                )
        if r.duree > LENT_S:
            classe = "PROBABLE" if r.duree > BLOQUANT_S else "PRESENTATION"
            self.journal.lentes.append((r.duree, route))
            self.journal.anomalie(
                classe, "lenteur", f"{r.duree:.2f} s", **champs, duree_s=round(r.duree, 3)
            )

    def ok(
        self, methode: str, chemin: str, corps: Any = None, attendu: tuple[int, ...] = OK, **kw: Any
    ) -> Any:
        """Un appel qui doit réussir ; sinon `EchecGeste` (le geste s'arrête, c'est consigné)."""
        r = self.appeler(methode, chemin, corps, attendu, **kw)
        if not r.ok:
            raise EchecGeste(r, f"{self.role} {methode} {chemin} → {r.statut} {r.detail}")
        return r.corps

    def get(self, chemin: str, **kw: Any) -> Any:
        """Une lecture qui doit réussir."""
        return self.ok("GET", chemin, None, (200,), **kw)

    def post(self, chemin: str, corps: Any = None, attendu: tuple[int, ...] = OK, **kw: Any) -> Any:
        """Un geste qui doit réussir."""
        return self.ok("POST", chemin, {} if corps is None else corps, attendu, **kw)

    def put(self, chemin: str, corps: Any, **kw: Any) -> Any:
        """Une modification qui doit réussir."""
        return self.ok("PUT", chemin, corps, (200,), **kw)

    def refus(
        self, methode: str, chemin: str, corps: Any, *statuts: int, note: str = ""
    ) -> Reponse:
        """Un appel qui **doit** être refusé (erreur humaine voulue) ; rend la réponse."""
        return self.appeler(methode, chemin, corps, statuts or (400, 404, 409, 422), note=note)


def _court(corps: Any) -> str:
    try:
        return json.dumps(corps, ensure_ascii=False, default=str)[:500]
    except (TypeError, ValueError):
        return repr(corps)[:500]


def jours_ouvres(debut: date, fin: date) -> list[date]:
    """Les jours travaillés de l'usine entre deux dates (fin comprise) : jamais le dimanche."""
    jours = []
    j = debut
    while j <= fin:
        if j.weekday() != 6:
            jours.append(j)
        j += timedelta(days=1)
    return jours


def fin_de_mois(jour: date) -> date:
    """Le dernier jour du mois de `jour`."""
    suivant = (jour.replace(day=28) + timedelta(days=4)).replace(day=1)
    return suivant - timedelta(days=1)
