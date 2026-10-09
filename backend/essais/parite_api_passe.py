"""Parité par l'API : la passe complète (PLAN-DE-RECETTE-PRO § 7.3).

1. Chaque paire de routes est lue sur les deux serveurs (pages et fiches comprises).
2. Routes du pilotage : la même route de Gestion MP est **rejouée** sur les données de
   Gestion MP (`D0`, doit redonner exactement la réponse du serveur : rejeu fidèle) puis sur
   chaque jeu de la chaîne des traductions ; un écart est expliqué par la première traduction
   dont le rejeu redonne la réponse de PRO — forme et ampleur, par le code de Gestion MP.
3. Routes des documents (et ce qui reste) : règles directes (`parite_api_regles`).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import parite_bases as pb
import parite_comparer as pc
from parite_api import Ecart, Resultat, Route, comparer_route, expliquer
from parite_api_documents import bilans, documents
from parite_api_regles import REGLES
from parite_api_routes import RouteMoteur, pilotage, tout_le_reste
from parite_chaine_base import TRADUCTIONS, traduire
from parite_serveurs import Client, Serveurs, gestion_mp_seul

ESSAIS = Path(__file__).resolve().parent
LIMITE = 5000


def _pages_gmp(client: Client, chemin: str, champ: str) -> list[Any]:
    lignes: list[Any] = []
    sep = "&" if "?" in chemin else "?"
    while True:
        page = client.get(f"{chemin}{sep}limite={LIMITE}&decalage={len(lignes)}")
        lignes += page[champ]
        if not page.get("tronque"):
            return lignes


def _pages_pro(client: Client, chemin: str, champ: str) -> list[Any]:
    elements: list[Any] = []
    sep = "&" if "?" in chemin else "?"
    suivant = ""
    while True:
        apres = f"&apres={suivant}" if suivant else ""
        page = client.get(f"{chemin}{sep}limite={LIMITE}{apres}")
        elements += page[champ]
        suivant = page.get("suivant") or ""
        if not suivant:
            return elements


def lire(client: Client, chemin: str, page: bool, fiche: str, champ: str, pro: bool) -> Any:  # noqa: PLR0917
    """Une réponse entière : toutes les pages, ou la liste remplacée par les fiches."""
    if page:
        return (_pages_pro if pro else _pages_gmp)(client, chemin, champ)
    reponse = client.get(chemin)
    if not fiche:
        return reponse
    liste = reponse if isinstance(reponse, list) else reponse[champ]
    return [client.get(fiche.format(id=e["id"])) for e in liste]


def lire_route(s: Serveurs, route: Route) -> tuple[Any, Any]:
    """Les deux réponses d'une paire (`None` côté Gestion MP pour une route rejouée seule)."""
    gmp = (
        lire(
            s.gestion_mp["direction"],
            route.gmp,
            route.page_gmp,
            route.fiche_gmp,
            route.champ_gmp,
            pro=False,
        )
        if route.gmp
        else None
    )
    pro = lire(
        s.pro["direction"], route.pro, route.page_pro, route.fiche_pro, route.champ_pro, pro=True
    )
    return gmp, pro


def rejouer(copie: str, routes: Iterable[RouteMoteur], jeux: list[str], dossier: Path) -> None:
    """Les routes de Gestion MP rejouées sur les jeux (son interpréteur, lecture seule)."""
    appels = [
        {
            "nom": r.route.nom,
            "module": r.appel.module,
            "fonction": r.appel.fonction,
            "parametres": r.appel.parametres,
        }
        for r in routes
    ]
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "appels.json"
    fichier.write_text(json.dumps(appels, ensure_ascii=False), encoding="utf-8")
    commande = [
        str(pb.PYTHON_GESTION_MP),
        str(ESSAIS / "gestion_mp_parite.py"),
        "routes",
        copie,
        str(fichier),
        str(dossier),
        *jeux,
    ]
    fait = subprocess.run(commande, cwd=pb.GESTION_MP, capture_output=True, text=True, check=False)  # noqa: S603
    if fait.returncode:
        raise SystemExit(f"Rejeu de Gestion MP impossible :\n{fait.stderr[-3000:]}")


def _rejeu(dossier: Path, jeu: str, route: Route) -> Any:
    return json.loads((dossier / jeu / f"{route.nom}.json").read_text(encoding="utf-8"))


@dataclass
class PasseApi:
    """Les résultats de la passe : par route, la fidélité du rejeu, les comptes de la chaîne en
    base (ce que chaque traduction a changé dans la copie)."""

    resultats: list[Resultat] = field(default_factory=list)
    infideles: dict[str, int] = field(default_factory=dict)
    """Routes dont le rejeu sur D0 ne redonne pas la réponse du serveur (doit rester vide)."""
    comptes: dict[str, dict[str, int]] = field(default_factory=dict)


Ouvert = tuple[Route, Resultat, Any, RouteMoteur | None]
"""Une route aux écarts encore inexpliqués : sa paire, son résultat, la réponse de PRO, et
l'appel de Gestion MP à rejouer (`None` : une route des documents, relue sur le serveur)."""


def _non_expliques(ouverts: list[Ouvert]) -> list[Ouvert]:
    return [o for o in ouverts if any(e.classe is None for e in o[1].ecarts)]


def _marquer(route: Route, r: Resultat, gmp: Any, pro: Any, classe: str) -> None:
    """Les écarts qui disparaissent quand Gestion MP rend `gmp` : expliqués par `classe`."""
    vus = {(e.cle, e.champ) for e in comparer_route(route, gmp, pro).ecarts}
    for e in r.ecarts:
        if e.classe is None and (e.cle, e.champ) not in vus:
            e.classe = classe


def _routes_du_moteur(  # noqa: PLR0917
    s: Serveurs,
    copie: str,
    jeux: dict[str, Path],
    dossier: Path,
    dates: list[str],
    mois: list[str],
    resultat: PasseApi,
) -> list[Ouvert]:
    """Pilotage aux dates, autres routes du moteur, bilans ; rejeu sur D0 puis sur la chaîne
    des données traduites (et K9 : les prix connus à la date)."""
    moteur = [rm for d in ("", *dates) for rm in pilotage(d)] + tout_le_reste() + bilans(mois)
    reponses = {rm.route.nom: lire_route(s, rm.route) for rm in moteur}
    rejouer(copie, moteur, [f"D0={jeux['D0']}"], dossier)
    ouverts: list[Ouvert] = []
    for rm in moteur:
        gmp_serveur, pro = reponses[rm.route.nom]
        d0 = _rejeu(dossier, "D0", rm.route)
        if gmp_serveur is not None and pc.comparer(gmp_serveur, d0, exact=True).ecarts:
            resultat.infideles[rm.route.nom] = len(pc.comparer(gmp_serveur, d0, exact=True).ecarts)
        r = comparer_route(rm.route, gmp_serveur if gmp_serveur is not None else d0, pro)
        resultat.resultats.append(r)
        if r.ecarts:
            ouverts.append((rm.route, r, pro, rm))
    chaine = [c for c in jeux if c != "D0"]
    specs = [f"{c}={jeux[c]}" for c in chaine] + [f"K9={jeux[chaine[-1]]}+K9"]
    if ouverts:
        rejouer(copie, [o[3] for o in ouverts if o[3]], specs, dossier)
    for route, r, pro, _ in ouverts:
        for classe in [*chaine, "K9"]:
            _marquer(route, r, _rejeu(dossier, classe, route), pro, classe)
    return ouverts


def _chaine_en_base(bases: pb.Bases, dossier: Path, ouverts: list[Ouvert]) -> dict[str, Any]:
    """Gestion MP relancé (ou rejoué) sur une copie traduite classe après classe ; chaque écart
    prend la première classe après laquelle Gestion MP rend la valeur de PRO."""
    traduite = bases.copie.replace("_source_essai", "_traduite_essai")
    pb.copier(bases.copie.rsplit("/", 1)[-1], traduite)
    comptes: dict[str, Any] = {}
    base = dossier / "base"
    try:
        for classe in TRADUCTIONS:
            comptes[classe] = traduire(traduite, classe)
            encore = _non_expliques(ouverts)
            rejoues = [o[3] for o in encore if o[3] is not None]
            if rejoues:
                rejouer(traduite, rejoues, [f"{classe}=-"], base)
            if any(o[3] is None for o in encore):
                with gestion_mp_seul(traduite, dossier) as client:
                    for route, r, pro, rm in encore:
                        if rm is None:
                            gmp = lire(
                                client,
                                route.gmp,
                                route.page_gmp,
                                route.fiche_gmp,
                                route.champ_gmp,
                                pro=False,
                            )
                            _marquer(route, r, gmp, pro, classe)
            for route, r, pro, rm in encore:
                if rm is not None:
                    _marquer(route, r, _rejeu(base, classe, route), pro, classe)
    finally:
        pb.supprimer(traduite)
    return comptes


def verifier_devises(r: Resultat, gmp: list[dict[str, Any]], pro: list[dict[str, Any]]) -> None:
    """La devise des lignes de Gestion MP (une par ligne) contre celle de l'en-tête de PRO (une
    par réception, I35) : égales, sauf sur une réception payée en deux devises (K8b, prouvée
    par la chaîne en base : l'en-tête de PRO y est la devise de la facture)."""
    fiches = {x["id"]: x for x in pro}
    for g in gmp:
        devises = {x["devise"] for x in g["lignes"]}
        p = fiches.get(g["id"])
        for x in g["lignes"]:
            r.comparees += 1
            if p is not None and x["devise"] != p["devise"]:
                classe = (
                    "K8b"
                    if len(devises) > 1 and (g.get("facture") or {}).get("devise") == p["devise"]
                    else None
                )
                r.ecarts.append(
                    Ecart(
                        "receptions",
                        f"{g['id']} › {x['id']}",
                        "lignes/devise",
                        x["devise"],
                        p["devise"],
                        classe,
                    )
                )


def passe(  # noqa: PLR0917
    s: Serveurs,
    bases: pb.Bases,
    jeux: dict[str, Path],
    dossier: Path,
    dates: list[str],
    mois: list[str],
) -> PasseApi:
    """La passe par l'API entière : routes du moteur (rejeu sur les données traduites), routes
    des documents, puis la chaîne en base pour ce qui reste, puis les règles directes."""
    resultat = PasseApi()
    ouverts = _routes_du_moteur(s, bases.copie, jeux, dossier, dates, mois, resultat)
    for route in documents():
        gmp, pro = lire_route(s, route)
        r = comparer_route(route, gmp, pro)
        if route.nom == "receptions":
            verifier_devises(r, gmp, pro)
        resultat.resultats.append(r)
        if r.ecarts:
            ouverts.append((route, r, pro, None))
    if _non_expliques(ouverts):
        resultat.comptes = _chaine_en_base(bases, dossier, _non_expliques(ouverts))
    for route, r, _, _ in ouverts:
        expliquer(route, r, REGLES)
    return resultat
