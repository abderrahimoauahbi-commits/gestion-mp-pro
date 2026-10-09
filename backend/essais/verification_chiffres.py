"""Vérification indépendante des chiffres de Gestion MP PRO (lot V1, critère A5).

Les écrans passent par le moteur de PRO. Ce script, lui, n'importe **rien** du paquet
`gestion_mp_pro` : il lit la base en SQL direct, et l'application par HTTP (un serveur PRO
lancé sur un port libre au-dessus de 8100 contre la base vérifiée, connecté en direction), puis
recompte par un autre chemin, avec les formules de la documentation écrites une seconde fois,
ce que les écrans affichent — à la date du jour et aux 13 dates de référence (fin des 12
derniers mois clos et jour même). Un écart désigne un défaut de PRO.

    cd backend
    GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp_pro_x_essai \\
        .venv/bin/python essais/verification_chiffres.py [--serveur URL] [--dates 13]

Sortie : une ligne ✓/✗ par famille de vérifications (nombre de cas jugés, 10 écarts au plus),
puis le total. Code 1 s'il y a un écart, 2 si la vérification n'a pas pu se faire.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from datetime import date

import verif_achats
import verif_documents
import verif_fournisseurs
import verif_importations
import verif_pilotage
import verif_production
import verif_stock
import verif_valeur
from verif_acces import IDENTIFIANT, AccesReel, Application, Base, Serveur, nom_de_base
from verif_socle import Acces, Releve, dates_de_reference

Etape = Callable[[Acces, Releve, list[date]], object]


def _etapes() -> list[tuple[str, Etape]]:
    """Les familles de vérifications, dans l'ordre du relevé."""
    return [
        ("données brutes", verif_stock.donnees_brutes),
        ("stock", verif_stock.stock_par_matiere),
        ("soldes", lambda a, r, d: verif_stock.soldes(a, r)),
        ("lots sous zéro", lambda a, r, d: verif_stock.lots_sous_zero(a, r)),
        ("lots", verif_stock.lots),
        ("valeur", verif_valeur.verifier),
        ("achats", verif_achats.verifier),
        ("documents", verif_documents.verifier),
        ("fournisseurs", verif_fournisseurs.verifier),
        ("production", verif_production.verifier),
        ("importations", verif_importations.verifier),
        ("pilotage", verif_pilotage.verifier),
    ]


def verifier(a: Acces, aujourdhui: date, nombre_de_dates: int = 13) -> Releve:
    """Toutes les vérifications d'une base ; rend le relevé (rien n'est écrit)."""
    r = Releve()
    dates = dates_de_reference(aujourdhui, nombre_de_dates)
    for nom, etape in _etapes():
        try:
            etape(a, r, dates)
        except Exception as exc:  # noqa: BLE001 (une famille qui casse est un écart, pas un arrêt)
            r.juger(f"Famille « {nom} » menée à son terme", nom, False, repr(exc)[:500])
    return r


def _options(arguments: list[str] | None) -> argparse.Namespace:
    """Les options de la ligne de commande."""
    p = argparse.ArgumentParser(prog="verification_chiffres.py", description=__doc__)
    p.add_argument("--base", default=os.environ.get("GESTIONMPPRO_BASE", ""))
    p.add_argument("--serveur", help="adresse d'un serveur PRO déjà lancé sur cette base")
    p.add_argument("--identifiant", help="compte de direction existant (sinon compte technique)")
    p.add_argument("--code", help="son code (avec --identifiant)")
    p.add_argument("--dates", type=int, default=13, help="nombre de dates de référence")
    return p.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """Lance la vérification sur une base ; 0 sans écart, 1 avec, 2 impossible."""
    o = _options(arguments)
    if not o.base:
        sys.stderr.write("GESTIONMPPRO_BASE (ou --base) manque.\n")
        return 2
    base = Base(o.base)
    serveur = None if o.serveur else Serveur(o.base)
    try:
        application = Application(o.serveur or (serveur.adresse if serveur else ""))
        identifiant, code = (o.identifiant, o.code) if o.identifiant else (IDENTIFIANT, "")
        if not o.identifiant:
            code = base.ouvrir_compte()
        application.connecter(identifiant, code)
        acces = AccesReel(application, base)
        aujourdhui = date.fromisoformat(acces.get("/stock", q="\x00")["date_reference"])
        releve = verifier(acces, aujourdhui, o.dates)
    finally:
        if not o.identifiant:
            base.fermer_compte()
        if serveur is not None:
            serveur.arreter()
        base.fermer()
    entete = f"Base {nom_de_base(o.base)} — jour {aujourdhui.isoformat()}, {o.dates} dates"
    sys.stdout.write("\n".join([entete, *releve.lignes()]) + "\n")
    return 1 if releve.nb_ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
