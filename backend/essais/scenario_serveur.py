"""Un vrai serveur pour le scénario (lot V2), à l'heure du scénario.

Lancé comme programme, il sert l'application (uvicorn, un processus, sans tâche de fond) après
avoir branché l'horloge de l'usine sur un fichier : chaque instant demandé est « le jour et
l'heure écrits dans le fichier + le temps réellement écoulé depuis qu'ils y ont été écrits ».
Le scénario fait ainsi passer un mois d'usine en quelques minutes, jour après jour, sans rien
changer d'autre au serveur : l'horloge de PRO est injectable par construction
(`services/horloge.py`, ARCHITECTURE C16) ; seul son état figé est remplacé.

    python essais/scenario_serveur.py pro <port> <fichier_horloge>
    python essais/scenario_serveur.py gestion_mp <port> <fichier_horloge>

Le second sert Gestion MP (son code et son interpréteur, lecture seule de `~/gestion-mp`) sur
une copie : ses modules lisent `date.today()` et `datetime.now()` ; ils reçoivent des classes
qui rendent le jour du fichier (parité dynamique, PLAN-DE-RECETTE § 7.4).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import types
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ICI = Path(__file__).resolve().parent
DOSSIER_SERVEUR = ICI.parent
DELAI_S = 90
ECOULE_MAX_S = 10 * 3600
"""Au plus dix heures écoulées dans une journée du scénario (pas de débord sur la suivante)."""


class _Fichier:
    """L'instant lu dans le fichier de l'horloge, relu seulement quand il change."""

    def __init__(self, fichier: Path) -> None:
        self.fichier = fichier
        self._lu: tuple[int, datetime] | None = None

    def instant(self) -> datetime:
        """Le jour et l'heure du fichier, plus le temps écoulé depuis qu'ils y sont écrits."""
        etat = self.fichier.stat()
        if self._lu is None or self._lu[0] != etat.st_mtime_ns:
            self._lu = (etat.st_mtime_ns, datetime.fromisoformat(self.fichier.read_text().strip()))
        ecoule = min(max(time.time() - etat.st_mtime, 0.0), ECOULE_MAX_S)
        return self._lu[1] + timedelta(seconds=ecoule)


def _brancher_pro(fichier: Path) -> None:
    """L'horloge de PRO lit le fichier : `maintenant()` rend l'instant du scénario."""
    from gestion_mp_pro.services import horloge

    source = _Fichier(fichier)

    class _EtatScenario:
        @property
        def fixe(self) -> datetime:
            return source.instant().replace(tzinfo=horloge.FUSEAU)

        @fixe.setter
        def fixe(self, _valeur: object) -> None:
            """L'horloge du scénario ne se fige pas autrement."""

    horloge._ETAT = _EtatScenario()  # type: ignore[assignment]  # noqa: SLF001


def _brancher_gestion_mp(fichier: Path) -> None:
    """Les modules de Gestion MP lisent le jour du fichier (`date.today()`, `datetime.now()`)."""
    import datetime as vrai

    source = _Fichier(fichier)

    class DateScenario(vrai.date):
        @classmethod
        def __get_pydantic_core_schema__(cls, _source: Any, handler: Any) -> Any:
            return handler(vrai.date)

        @classmethod
        def today(cls) -> date:
            return vrai.date.fromordinal(source.instant().date().toordinal())

    class DatetimeScenario(vrai.datetime):
        @classmethod
        def __get_pydantic_core_schema__(cls, _source: Any, handler: Any) -> Any:
            return handler(vrai.datetime)

        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            instant = source.instant()
            local = vrai.datetime(*instant.timetuple()[:6], instant.microsecond)  # noqa: DTZ001
            return local if tz is None else local.astimezone(tz)

        @classmethod
        def today(cls) -> datetime:
            return cls.now()

    faux = types.ModuleType("datetime")
    faux.__dict__.update(vrai.__dict__)
    faux.date, faux.datetime = DateScenario, DatetimeScenario  # type: ignore[attr-defined]
    for nom, module in list(sys.modules.items()):
        if not nom.startswith("gestion_mp") or module is None:
            continue
        if getattr(module, "date", None) is vrai.date:
            module.date = DateScenario  # type: ignore[attr-defined]
        if getattr(module, "datetime", None) is vrai.datetime:
            module.datetime = DatetimeScenario  # type: ignore[attr-defined]
        for attribut, valeur in list(vars(module).items()):
            if valeur is vrai:
                setattr(module, attribut, faux)


def servir(logiciel: str, port: int, fichier: Path) -> None:
    """Sert l'application du logiciel, l'horloge branchée sur le fichier."""
    import uvicorn

    if logiciel == "pro":
        _brancher_pro(fichier)
        from gestion_mp_pro.main import app
    else:
        import gestion_mp.main as principal

        _brancher_gestion_mp(fichier)
        app = principal.app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)


def port_libre(depart: int) -> int:
    """Le premier port libre au-dessus de `depart` (> 8100 ; jamais 8020–8050)."""
    import socket

    for port in range(depart, 8400):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"aucun port libre entre {depart} et 8400")


def _attendre(adresse: str, processus: subprocess.Popen[bytes], journal: Path) -> None:
    fin = time.monotonic() + DELAI_S
    while time.monotonic() < fin:
        if processus.poll() is not None:
            raise RuntimeError(f"serveur arrêté au démarrage :\n{journal.read_text()[-3000:]}")
        with suppress(OSError), urllib.request.urlopen(adresse + "/api/sante", timeout=2):  # noqa: S310
            return
        time.sleep(0.2)
    raise RuntimeError(f"serveur muet après {DELAI_S} s : {adresse}")


@contextmanager
def lancer(
    logiciel: str, env: dict[str, str], horloge: Path, journal: Path, depart: int = 8231
) -> Iterator[str]:
    """Lance le serveur (sous-processus), rend son adresse ; l'arrête toujours en sortie."""
    port = port_libre(depart)
    python = env.pop("SCENARIO_PYTHON", sys.executable)
    commande = [python, str(ICI / "scenario_serveur.py"), logiciel, str(port), str(horloge)]
    cwd = env.pop("SCENARIO_CWD", str(DOSSIER_SERVEUR))
    with journal.open("wb") as sortie:
        processus = subprocess.Popen(  # noqa: S603 — interpréteur et script à nous
            commande, env=env, cwd=cwd, stdout=sortie, stderr=subprocess.STDOUT
        )
    adresse = f"http://127.0.0.1:{port}"
    try:
        _attendre(adresse, processus, journal)
        yield adresse
    finally:
        processus.terminate()
        try:
            processus.wait(timeout=20)
        except subprocess.TimeoutExpired:
            processus.kill()
            processus.wait()


def environnement_pro(base: str, dossier: Path) -> dict[str, str]:
    """Les variables du serveur PRO : sa base d'essai, ses dossiers temporaires, sans tâches."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTION")}
    return env | {
        "GESTIONMPPRO_BASE": base,
        "GESTIONMPPRO_TACHES": "0",
        "GESTIONMPPRO_SAUVEGARDES": str(dossier / "sauvegardes"),
        "GESTIONMPPRO_PIECES": str(dossier / "pieces"),
        "GESTIONMPPRO_ECRAN": str(dossier / "sans-ecran"),
    }


if __name__ == "__main__":
    servir(sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]))
