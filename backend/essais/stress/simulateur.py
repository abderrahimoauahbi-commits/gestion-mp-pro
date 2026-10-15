"""Le simulateur « 10 ans d'exploitation » : la boucle des jours, les rendez-vous du
calendrier, les dumps par année simulée, la reprise depuis une année.

    cd backend
    .venv/bin/python -m essais.stress.simulateur --dump <référentiels.dump> --annees 1
    .venv/bin/python -m essais.stress.simulateur --depuis-annee 3 --annees 10

- `--dump` : la base est (re)créée depuis le dump des référentiels (point de départ), migrée ;
- `--depuis-annee N` : la base est restaurée depuis `<dumps>/annee-N.dump` et la simulation
  reprend à l'année N + 1 ; le hasard est tiré par année (`graine-année`) ;
- sans l'un ni l'autre : la base telle qu'elle est (mise au point).
Une année simulée va du 15 octobre au 14 octobre suivant ; un dump étiqueté la clôt.
"""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from essais.stress import socle
from essais.stress.socle import Horloge, Journal, jours_ouvres

BASE_DEFAUT = "postgresql+psycopg:///gestion_mp_pro_stress_essai"
DUMPS_DEFAUT = Path("~/gestion-mp-pro-sauvegardes/stress").expanduser()
DEBUT = date(2026, 10, 15)


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulateur 10 ans d'exploitation (par les routes)")
    p.add_argument("--base", default=BASE_DEFAUT)
    p.add_argument("--dump", default="", help="dump des référentiels : la base est recréée")
    p.add_argument("--depuis-annee", type=int, default=-1, help="reprendre après l'année N")
    p.add_argument("--annees", type=int, default=10, help="dernière année jouée (exclue)")
    p.add_argument("--graine", default="stress-2026")
    p.add_argument("--jours", type=int, default=0, help="n jours au plus (mise au point)")
    p.add_argument("--dumps", default=str(DUMPS_DEFAUT))
    p.add_argument("--travail", default=str(DUMPS_DEFAUT / "app"))
    p.add_argument("--dates-v1", type=int, default=2, help="dates du vérificateur en fin de mois")
    return p.parse_args(argv)


def _psql(base_admin: str, ordre: str) -> None:
    from gestion_mp_pro.reprise.sauvegarde import outil

    subprocess.run([outil("psql"), base_admin, "-Atc", ordre], check=True, capture_output=True)  # noqa: S603


def preparer_base(base: str, dump: Path) -> None:
    """Recrée la base d'essai depuis un dump (`pg_restore`), puis `alembic upgrade head`."""
    from alembic import command

    from gestion_mp_pro.reprise.sauvegarde import outil
    from gestion_mp_pro.services.installation import configuration

    nom = base.rsplit("/", 1)[-1]
    admin = base.rsplit("/", 1)[0].replace("postgresql+psycopg://", "postgresql://") + "/postgres"
    _psql(admin, f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)')
    _psql(admin, f'CREATE DATABASE "{nom}"')
    subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--no-owner", "-d", base.replace("+psycopg", ""), str(dump)],
        check=False,
        capture_output=True,
    )
    command.upgrade(configuration(), "head")


def sauvegarder_annee(base: str, dumps: Path, annee: int) -> Path:
    """`pg_dump -Fc` de la base à la fin de l'année simulée, étiqueté."""
    from gestion_mp_pro.reprise.sauvegarde import outil

    dumps.mkdir(parents=True, exist_ok=True)
    chemin = dumps / f"annee-{annee}.dump"
    with chemin.open("wb") as f:
        subprocess.run(  # noqa: S603 — outil PostgreSQL, arguments à nous
            [outil("pg_dump"), "-Fc", base.replace("+psycopg", "")], stdout=f, check=True
        )
    return chemin


def poser_direction(base: str) -> None:
    """Le compte de direction d'essai, posé comme l'installation le pose (sans session)."""
    from sqlalchemy import create_engine, text

    from essais.stress.monde import CODES, IDENTIFIANTS, NOMS
    from gestion_mp_pro.services import comptes

    moteur = create_engine(base)
    with moteur.begin() as c:
        c.execute(
            text(
                "INSERT INTO utilisateur (identifiant, nom, role, empreinte_code, actif) "
                "VALUES (:i, :n, 'direction', :e, true) ON CONFLICT (identifiant) DO NOTHING"
            ),
            {
                "i": IDENTIFIANTS["direction"],
                "n": NOMS["direction"],
                "e": comptes.hacher(CODES["direction"]),
            },
        )
    moteur.dispose()


def premier_jour(m: Any) -> None:
    """Le 15 octobre 2026 : comptes, seuil d'approbation, catalogue lu, stock d'ouverture."""
    from essais.stress.monde import CODES, IDENTIFIANTS, NOMS

    d = m.poste("direction")
    for role in ("achats", "alimentation"):
        d.appeler(
            "POST",
            "/utilisateurs",
            {
                "identifiant": IDENTIFIANTS[role],
                "nom": NOMS[role],
                "role": role,
                "code": CODES[role],
            },
            (201, 409),
            note="compte créé",
        )
        m.poste(role)
    lus = d.get("/parametres")
    d.put(
        "/parametres",
        {
            "valeurs": {"seuil_approbation": m.seuil_approbation},
            "version_globale": lus[0]["version_globale"],
        },
        note="seuil d'approbation",
    )
    m.journal.note(
        f"- réglage de la copie : seuil d'approbation {m.seuil_approbation:,.0f} MAD "
        "(0 = jamais chez Mohamed) ; tout le reste tel quel"
    )
    m.lire_catalogue()
    stock_d_ouverture(m)


def stock_d_ouverture(m: Any) -> None:
    """L'usine qui démarre l'ERP a du stock : un à deux mois de consommation par matière
    consommée, en lots internes, au prix catalogue (opération « stock d'ouverture »)."""
    d = m.D
    stock = d.get("/stock")
    lignes = []
    for x in stock["lignes"]:
        conso = float(x["conso_mensuelle"] or 0)
        fiche = next(
            (f for f in m.catalogue.matieres.values() if f["reference"] == x["reference"]), None
        )
        if conso <= 0 or fiche is None:
            continue
        for part in [1.0] if m.chance(0.6) else [0.6, 0.4]:
            lignes.append(
                {
                    "matiere_id": fiche["id"],
                    "lot_interne": True,
                    "magasin_id": m.catalogue.courants[0]
                    if m.chance(0.75)
                    else m.choix(m.catalogue.courants),
                    "quantite": round(conso * m.entre(1.0, 2.2) * part, 1),
                    "unite": "kg",
                    "prix": float(fiche.get("prix_kg") or fiche.get("prix") or 0),
                    "devise": fiche.get("devise") or "MAD",
                }
            )
    for i in range(0, len(lignes), 25):
        d.post(
            "/operations",
            {
                "type": "ouverture",
                "date": m.iso,
                "commentaire": "Stock au démarrage de l'ERP",
                "valider": True,
                "lignes": lignes[i : i + 25],
            },
            socle.CREE,
            note="stock d'ouverture",
        )
        m.journal.geste("opérations de stock d'ouverture")
    m.journal.note(f"- stock d'ouverture : {len(lignes)} lots internes posés par la direction")


def jouer_jour(m: Any, jour: date, precedent: date | None, a: argparse.Namespace) -> None:
    """Une journée d'usine : rendez-vous du calendrier d'abord, puis les gestes de chacun."""
    from essais.stress import achats_commandes, achats_receptions, atelier, erreurs, periodes

    m.horloge.aller(jour)
    if precedent is not None and jour.month != precedent.month:
        mois_clos = precedent.replace(day=1)
        periodes.fin_du_mois(m, mois_clos, a.dates_v1)
        if jour.month in (1, 4, 7, 10):
            periodes.fin_du_trimestre(m)
        if jour.month == 1:
            periodes.fin_d_annee(m, jour.year)
        m.horloge.aller(jour, 10)
    samedi = jour.weekday() == 5
    semaine = jour.weekday()
    gestes: list[Callable[[], None]] = [
        lambda: atelier.ordres_du_jour(m, samedi),
        lambda: atelier.traiter_signalements(m),
    ]
    if not samedi:
        if semaine in (0, 3):
            gestes += [
                lambda: achats_commandes.commandes_de_la_semaine(m),
                lambda: atelier.transferts(m),
            ]
        gestes += [
            lambda: achats_commandes.confirmer_les_prix(m),
            lambda: achats_commandes.jalons_d_expedition(m),
        ]
        if semaine in (1, 4):
            gestes.append(lambda: achats_receptions.camions_de_la_semaine(m))
        gestes.append(lambda: achats_receptions.suites_des_receptions(m))
        if semaine == 2:
            gestes += [lambda: atelier.montage(m), lambda: erreurs.erreurs_humaines(m)]
        if semaine == 4:
            gestes.append(lambda: atelier.signalement(m))
        if semaine in (1, 3):
            gestes.append(lambda: atelier.scan(m))
    for geste in gestes:
        _jouer(m, geste)


def _jouer(m: Any, geste: Callable[[], None]) -> None:
    """Un geste d'usine ; un appel refusé l'arrête (noté) ; une faute du générateur est
    consignée (classe GENERATEUR) sans arrêter la simulation."""
    try:
        geste()
    except socle.EchecGeste as e:
        m.journal.note(f"  · geste interrompu le {m.iso} : {e}")
        m.journal.geste("gestes interrompus")
    except Exception as e:  # noqa: BLE001 — la simulation continue, la faute est consignée
        m.journal.anomalie(
            "GENERATEUR", "exception", traceback.format_exc()[-1500:], erreur=repr(e)[:200]
        )
        m.journal.note(f"  ✗ faute du générateur le {m.iso} : {e!r}")


def jouer_annee(m: Any, annee: int, a: argparse.Namespace, neuve: bool) -> None:
    """Une année simulée (15 octobre → 14 octobre), puis son dump."""
    from essais.stress.monde import Monde

    assert isinstance(m, Monde)
    m.annee = annee
    m.hasard = random.Random(f"{a.graine}-{annee}")  # noqa: S311
    m.journal.ouvrir_annee(annee)
    debut = date(DEBUT.year + annee, 10, 15)
    fin = date(DEBUT.year + annee + 1, 10, 14)
    m.journal.note(f"\n## Année {annee} : du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}")
    m.horloge.aller(debut)
    chrono = time.monotonic()
    if neuve:
        premier_jour(m)
    else:
        m.connecter_tous()
        m.lire_catalogue()
    precedent: date | None = None
    for n, jour in enumerate(jours_ouvres(debut, fin)):
        if a.jours and n >= a.jours:
            break
        jouer_jour(m, jour, precedent, a)
        precedent = jour
    chemin = sauvegarder_annee(m.base, Path(a.dumps).expanduser(), annee)
    bilan_de_l_annee(m, annee, time.monotonic() - chrono, chemin)


def bilan_de_l_annee(m: Any, annee: int, duree: float, dump: Path) -> None:
    """Le résumé de l'année dans le journal : volumes, statuts, anomalies, lenteurs."""
    j = m.journal
    j.note(
        f"\n### Bilan de l'année {annee} — {duree / 60:.1f} min, {j.nb_appels} appels "
        f"depuis le départ, dump {dump}"
    )
    j.note("- volumes : " + ", ".join(f"{k} {v}" for k, v in sorted(j.volumes.items())))
    j.note("- statuts : " + ", ".join(f"{k} {v}" for k, v in sorted(j.statuts.items())))
    j.note(
        "- anomalies : "
        + (", ".join(f"{k} {v}" for k, v in sorted(j.anomalies.items())) or "aucune")
    )
    if j.lentes:
        pires = sorted(j.lentes, reverse=True)[:8]
        j.note("- plus lents : " + ", ".join(f"{r} {d:.2f} s" for d, r in pires))


def main(argv: list[str] | None = None) -> int:
    """Prépare la base, joue les années demandées, écrit les dumps ; 0 si tout a tourné."""
    a = _arguments(argv)
    travail = Path(a.travail).expanduser()
    travail.mkdir(parents=True, exist_ok=True)
    socle.preparer_environnement(a.base, travail)
    from essais.stress.monde import Monde
    from gestion_mp_pro.main import creer_application

    dumps = Path(a.dumps).expanduser()
    neuve = False
    if a.depuis_annee >= 0:
        preparer_base(a.base, dumps / f"annee-{a.depuis_annee}.dump")
        premiere = a.depuis_annee + 1
    elif a.dump:
        preparer_base(a.base, Path(a.dump))
        poser_direction(a.base)
        premiere, neuve = 0, True
    else:
        premiere = 0
    horloge = Horloge()
    journal = Journal(socle.ICI, horloge)
    journal.note(
        f"\n# Simulation lancée le {time.strftime('%Y-%m-%d %H:%M')} — "
        f"base {a.base.rsplit('/', 1)[-1]}, graine {a.graine}, années {premiere}→{a.annees - 1}"
    )  # noqa: DTZ011
    app = creer_application()
    m = Monde(app, horloge, journal, random.Random(a.graine), base=a.base)  # noqa: S311
    try:
        for annee in range(premiere, a.annees):
            jouer_annee(m, annee, a, neuve and annee == 0)
    finally:
        journal.fermer()
    return 0


if __name__ == "__main__":
    sys.exit(main())
