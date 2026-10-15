"""Tournée d'écran du stress test « 10 ans » (épreuve d'écran) : serveur jetable + Chrome sans tête.

    .venv/bin/python essais/stress/tournee.py <base_essai> --etiquette <nom> [--date AAAA-MM-JJ]
                                              [--roles direction,achats] [--sans-onglets]
    .venv/bin/python essais/stress/tournee.py rapport        # tournee-ecran.md depuis resultats/

Pour une base (qui doit finir par `_essai`, jamais celle du service) : un compte par rôle est
inscrit, les enregistrements d'exemple sont lus (`tournee_contexte`), un uvicorn est lancé sur un
port libre > 8100 (processus d'ARCHITECTURE, écran construit `frontend/dist`, horloge figée au jour
demandé par `app_figee`, sans tâche de fond), puis `tournee_ecran.mjs` parcourt tout. Le résultat
va dans `resultats/<etiquette>.json`, les captures dans `captures/<etiquette>/`, et le rapport
`tournee-ecran.md` est régénéré (toutes les bases connues, côte à côte). Le serveur est arrêté et
les comptes retirés en sortie, même en cas d'échec.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from datetime import date
from pathlib import Path

ICI = Path(__file__).resolve().parent
BACKEND = ICI.parent.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(BACKEND / "essais"))

import recompte_ecran as recompte  # noqa: E402
import tournee_contexte as ctx  # noqa: E402
import tournee_rapport as rapport  # noqa: E402
from charge_serveur import Poste  # noqa: E402
from parite_serveurs import port_libre  # noqa: E402

RESULTATS = ICI / "resultats"
CAPTURES = ICI / "captures"
DELAI_DEMARRAGE_S = 90


def _adresse(nom: str) -> str:
    return nom if "://" in nom else f"postgresql+psycopg:///{nom}"


def _port_cdp(depart: int = 9381) -> int:
    """Un port libre pour le Chrome sans tête (hors de la plage des serveurs)."""
    for port in range(depart, depart + 100):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("Aucun port libre pour Chrome")


def _attendre_serveur(port: int, p: subprocess.Popen[bytes], journal: Path) -> None:
    fin = time.monotonic() + DELAI_DEMARRAGE_S
    while time.monotonic() < fin:
        if p.poll() is not None:
            raise SystemExit(f"Serveur arrêté au démarrage :\n{journal.read_text()[-3000:]}")
        with suppress(OSError, http.client.HTTPException):
            cnx = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            cnx.request("GET", "/api/sante")
            if cnx.getresponse().status < 500:
                return
        time.sleep(0.3)
    raise SystemExit(f"Serveur muet après {DELAI_DEMARRAGE_S} s (port {port})")


def _lancer_serveur(
    adresse: str, dossier: Path, jour: date | None
) -> tuple[subprocess.Popen[bytes], int]:
    """uvicorn (2 processus, comme le service) sur `app_figee`, port libre > 8100."""
    port = port_libre(8121)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GESTIONMPPRO")}
    env |= {
        "GESTIONMPPRO_BASE": adresse,
        "GESTIONMPPRO_PORT": str(port),
        "GESTIONMPPRO_TACHES": "0",
        "GESTIONMPPRO_SAUVEGARDES": str(dossier / "sauvegardes"),
        "GESTIONMPPRO_PIECES": str(dossier / "pieces"),
        "PYTHONPATH": str(BACKEND),
    }
    if jour is not None:
        env["GESTIONMPPRO_STRESS_DATE"] = jour.isoformat()
    commande = [sys.executable, "-m", "uvicorn", "essais.stress.app_figee:app", "--host",
                "127.0.0.1", "--port", str(port), "--no-access-log", "--workers", "2"]  # fmt: skip
    journal = dossier / f"serveur-{port}.log"
    with journal.open("wb") as sortie:
        p = subprocess.Popen(  # noqa: S603
            commande, cwd=BACKEND, env=env, stdout=sortie, stderr=subprocess.STDOUT
        )
    _attendre_serveur(port, p, journal)
    return p, port


def _arreter(p: subprocess.Popen[bytes]) -> None:
    p.terminate()
    try:
        p.wait(timeout=20)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=10)


def _tourner(
    args: argparse.Namespace, adresse: str, port: int, dossier: Path, codes: dict[str, str]
) -> Path:
    """Lance le pilote Chrome ; rend le fichier de résultat."""
    jour = args.date or date.today()  # noqa: DTZ011 — le jour du poste, comme l'usine le lit
    contexte = ctx.contexte(adresse, jour) | {"etiquette": args.etiquette}
    (dossier / "codes.json").write_text(json.dumps(codes))
    (dossier / "contexte.json").write_text(json.dumps(contexte))
    RESULTATS.mkdir(exist_ok=True)
    sortie = RESULTATS / f"{args.etiquette}.json"
    captures = CAPTURES / args.etiquette
    captures.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if args.roles:
        env["TOURNEE_ROLES"] = args.roles
    if args.sans_onglets:
        env["TOURNEE_SANS_ONGLETS"] = "1"
    commande = ["node", str(ICI / "tournee_ecran.mjs"), f"http://127.0.0.1:{port}",
                str(dossier / "codes.json"), str(dossier / "contexte.json"), str(captures),
                str(dossier / "profil-chrome"), str(_port_cdp()), str(sortie)]  # fmt: skip
    r = subprocess.run(commande, env=env, check=False)  # noqa: S603
    if r.returncode:
        raise SystemExit(f"Le pilote d'écran a échoué (code {r.returncode}).")
    return sortie


def _recompter(args: argparse.Namespace, adresse: str, port: int, codes: dict[str, str]) -> None:
    """Les chiffres d'écran recomptés en SQL (phase B), sur le même serveur, en direction."""
    from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION

    poste = Poste("127.0.0.1", port, entete=ENTETE_ANTI_FALSIFICATION)
    ident = f"{ctx.PREFIXE_COMPTE}-direction"
    poste.ok("POST", "/api/connexion", {"identifiant": ident, "code": codes[ident]})
    jour = args.date or date.today()  # noqa: DTZ011
    lignes = recompte.recompter(poste, adresse, jour)
    poste.fermer()
    (RESULTATS / f"{args.etiquette}-recompte.json").write_text(json.dumps(lignes))
    faux = [x for x in lignes if not x["ok"]]
    sys.stdout.write(f"Recompte SQL : {len(lignes)} cas, {len(faux)} écart(s).\n")


def executer(args: argparse.Namespace) -> int:
    """Une base : comptes, serveur, tournée, rapport ; tout est défait en sortie."""
    adresse = _adresse(args.base)
    ctx.garde_fou(adresse)
    codes = ctx.inscrire_comptes(adresse)
    serveur = None
    try:
        with tempfile.TemporaryDirectory(
            prefix=f"tournee-{args.etiquette}-", ignore_cleanup_errors=True
        ) as tmp:
            dossier = Path(tmp)
            serveur, port = _lancer_serveur(adresse, dossier, args.date)
            sys.stdout.write(f"Serveur jetable sur le port {port} ({adresse}).\n")
            if not args.recompte_seul:
                sortie = _tourner(args, adresse, port, dossier, codes)
                sys.stdout.write(f"Résultat : {sortie}\n")
            _recompter(args, adresse, port, codes)
    finally:
        if serveur is not None:
            _arreter(serveur)
        ctx.retirer_comptes(adresse)
    rapport.ecrire(RESULTATS, ICI / "tournee-ecran.md")
    return 0


def main() -> int:
    """Ligne de commande."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("base", help="nom de la base d'essai (…_essai) ou « rapport »")
    p.add_argument("--etiquette", help="nom court du résultat (référentiels, x30, annee-1…)")
    p.add_argument("--date", type=date.fromisoformat, help="jour auquel l'horloge est figée")
    p.add_argument("--roles", help="direction,achats,alimentation (défaut : les trois)")
    p.add_argument("--sans-onglets", action="store_true", help="écrans de base seulement")
    p.add_argument(
        "--recompte-seul", action="store_true", help="seulement le recompte SQL (pas de tournée)"
    )
    args = p.parse_args()
    if args.base == "rapport":
        rapport.ecrire(RESULTATS, ICI / "tournee-ecran.md")
        return 0
    if not args.etiquette:
        p.error("--etiquette est obligatoire pour une tournée")
    return executer(args)


if __name__ == "__main__":
    raise SystemExit(main())
