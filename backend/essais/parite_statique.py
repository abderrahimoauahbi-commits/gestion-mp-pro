"""Parité statique (PLAN-DE-RECETTE-PRO § 7.2) : les deux moteurs sur l'année d'essai, 19 dates.

Pour chaque date :

1. **Moteur** : le moteur PRO sur les données que son chargeur lit dans la base reprise
   (`Dpro`) rend **exactement** ce que le moteur de Gestion MP rend sur ces mêmes données — tout
   écart est un défaut du moteur PRO (à corriger) ;
2. **Parité** : PRO (`Dpro`) contre Gestion MP sur ses propres données (`D0`), aux tolérances
   du § 7.5 ; chaque écart est expliqué par la première traduction de la chaîne D0 → Dpro
   dont le recalcul par Gestion MP redonne la valeur de PRO (`parite_donnees`), sinon il est à
   corriger ;
3. **K7** : la lecture des services de PRO (`services.pilotage.lire` : fil monté du soir de la
   date) contre le moteur seul : l'écart attendu est celui du fil monté ce soir-là ; sans fil
   monté, aucun.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import parite_bases as pb
import parite_comparer as pc

ESSAIS = Path(__file__).resolve().parent
TESTS = ESSAIS.parent / "tests"
AUJOURDHUI = date(2026, 10, 8)
FINS_DE_MOIS = (
    "2025-10-31 2025-11-30 2025-12-31 2026-01-31 2026-02-28 2026-03-31 "
    "2026-04-30 2026-05-31 2026-06-30 2026-07-31 2026-08-31 2026-09-30 2026-10-08"
).split()
MILIEUX = "2025-11-15 2026-01-15 2026-03-15 2026-05-15 2026-07-15 2026-09-15".split()
"""Aucune version de plan ni de recette ne change dans l'année d'essai (une version par
qualité, datée de l'import) : les six dates du milieu d'un mois sont des 15, un mois sur deux."""
DATES = (*FINS_DE_MOIS, *MILIEUX)


def _gmp(*args: str) -> list[str]:
    return [str(pb.PYTHON_GESTION_MP), str(ESSAIS / "gestion_mp_parite.py"), *args]


def donnees_gestion_mp(copie: str, dossier: Path) -> dict[str, Any]:
    """Les `Donnees` du dépôt de Gestion MP sur la copie (son interpréteur, lecture seule)."""
    import gestion_mp_calcul as calcul

    chemin = dossier / "D0.json"
    subprocess.run(_gmp("donnees", copie, str(chemin)), check=True, cwd=pb.GESTION_MP)  # noqa: S603
    with calcul._ouvrir(chemin, "r") as f:  # noqa: SLF001
        return dict(json.load(f))


def donnees_pro(adresse: str) -> Any:
    """Les `Donnees` complètes du chargeur de PRO (S4) sur la base reprise."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from gestion_mp_pro.services import donnees_moteur

    donnees_moteur.invalider()
    moteur = create_engine(adresse, poolclass=NullPool)
    with Session(moteur) as s:
        complet = donnees_moteur.charger(s)
    moteur.dispose()
    return complet


def ecrire_jeux(dossier: Path, d0: dict[str, Any], chaine: list[tuple[str, Any]]) -> list[Path]:
    """D0 et les jeux de la chaîne en fichiers (relus par l'interpréteur de Gestion MP)."""
    chemins = []
    for nom, donnees in (("D0", d0), *chaine):
        chemin = dossier / f"{nom}.json"
        chemin.write_text(json.dumps({"donnees": donnees}, ensure_ascii=False), encoding="utf-8")
        chemins.append(chemin)
    return chemins


def calculer_gestion_mp(jeux: list[Path], dossier: Path, dates: tuple[str, ...]) -> None:
    """Le moteur de Gestion MP sur chaque jeu, aux dates (un processus par jeu, en parallèle)."""
    processus = [
        subprocess.Popen(  # noqa: S603
            _gmp("sorties", AUJOURDHUI.isoformat(), ",".join(dates), str(dossier), str(j)),
            cwd=pb.GESTION_MP,
            stderr=subprocess.PIPE,
        )
        for j in jeux
    ]
    for p in processus:
        _, erreur = p.communicate()
        if p.returncode:
            raise SystemExit(f"Gestion MP n'a pas calculé : {erreur.decode()[-2000:]}")


def sorties_pro(complet: Any, jour: date) -> Any:
    """Les sorties du moteur PRO sur `Dpro`, dans la forme de Gestion MP (`tests/moteur`)."""
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    from moteur import jeux_outils
    from moteur.sorties_pro import sorties_du_moteur

    return jeux_outils.propre(sorties_du_moteur(complet, jour, AUJOURDHUI))


def _lire(dossier: Path, jeu: str, jour: str) -> Any:
    chemin = dossier / jeu / f"{jour}.json"
    return pc.ranger(json.loads(chemin.read_text(encoding="utf-8")))


@dataclass
class Jour:
    """Le résultat d'une date."""

    jour: str
    comparees: dict[str, int] = field(default_factory=dict)
    moteur: list[tuple[pc.Chemin, Any, Any]] = field(default_factory=list)
    ecarts: list[pc.Explique] = field(default_factory=list)
    k7_attendus: int = 0
    k7_vus: list[tuple[pc.Chemin, Any, Any]] = field(default_factory=list)


def comparer_jour(dossier: Path, complet: Any, jour: str, chaine: list[str]) -> Jour:
    """Moteur, parité et explications d'une date (les jeux intermédiaires lus à la demande)."""
    b = pc.ranger(sorties_pro(complet, date.fromisoformat(jour)))
    a = _lire(dossier, "D0", jour)
    r = Jour(jour, dict(pc.feuilles_par_section(a)))
    r.moteur = pc.comparer(_lire(dossier, chaine[-1], jour), b, exact=True).ecarts
    restants = pc.comparer(a, b).ecarts
    for classe in chaine:
        if not restants:
            break
        c = _lire(dossier, classe, jour)
        trouves = pc.expliquer(restants, [(classe, c)])
        r.ecarts += [e for e in trouves if e.classe]
        restants = [(e.chemin, e.gmp, e.pro) for e in trouves if not e.classe]
    r.ecarts += [pc.Explique(ch, x, y, None) for ch, x, y in restants]
    return r


def verifier_k7(adresse: str, complet: Any, r: Jour) -> None:
    """K7 : les services de PRO (fil monté du soir) contre le moteur seul, à la date."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from gestion_mp_pro.calcul.a_la_date import a_la_date
    from gestion_mp_pro.calcul.stock import etat_stock
    from gestion_mp_pro.services import horloge, pilotage, pilotage_machine

    jour = date.fromisoformat(r.jour)
    moteur = create_engine(adresse, poolclass=NullPool)
    with horloge.figee(AUJOURDHUI), Session(moteur) as s:
        lecture = pilotage.lire(s, jour)
        r.k7_attendus = sum(len(v) for v in pilotage_machine.montage_au_soir(s, jour).values())
    moteur.dispose()
    seul = etat_stock(a_la_date(complet, jour, aujourdhui=AUJOURDHUI), jour)
    avec = pc.ranger({"stock": [dataclasses.asdict(x) for x in lecture.lignes]})
    sans = pc.ranger({"stock": [dataclasses.asdict(x) for x in seul]})
    r.k7_vus = pc.comparer(sans, avec, exact=True).ecarts


def resume(jours: list[Jour]) -> dict[str, Counter[str]]:
    """Par section : feuilles comparées, écarts expliqués par classe, à corriger."""
    sortie: dict[str, Counter[str]] = {}
    for r in jours:
        for section, n in r.comparees.items():
            sortie.setdefault(section, Counter())["comparées"] += n
        for e in r.ecarts:
            sortie.setdefault(e.chemin[0], Counter())[e.classe or "à corriger"] += 1
        for ch, _, _ in r.moteur:
            sortie.setdefault(ch[0], Counter())["moteur à corriger"] += 1
    return sortie
