"""Côté Gestion MP de la parité sur l'année d'essai (PLAN-DE-RECETTE-PRO § 7.2).

Lancé par l'interpréteur de Gestion MP (`~/gestion-mp/.venv/bin/python`), sur le code de
`~/gestion-mp` en lecture seule, par `essais/parite_gestion_mp.py` :

    python essais/gestion_mp_parite.py donnees <url_copie> <sortie.json.xz>
    python essais/gestion_mp_parite.py sorties <aujourdhui> <d1,d2,…> <dossier> <jeu.json[.xz]>…
    python essais/gestion_mp_parite.py routes <url_copie> <appels.json> <dossier> <nom=jeu+K…>…

`donnees` fige les `Donnees` complètes que le dépôt de Gestion MP charge de la copie (lecture
seule), au format des jeux de S3 (`gestion_mp_calcul.vers_json`). `sorties` rejoue chaque date
avec le moteur de Gestion MP (`gestion_mp_calcul.sorties_du_moteur` : 39 sections, sans arrondi)
sur des données figées — celles de Gestion MP, ou celles que le chargeur de PRO lit dans la base
reprise (la règle d'explication K1 calcule ainsi l'écart qu'une donnée arrondie doit donner).
`routes` rejoue les routes du pilotage de Gestion MP (leur code tel quel) sur ces jeux : le
dépôt rend le jeu au lieu de la base.
"""

from __future__ import annotations

import json
import sys
import typing
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gestion_mp_calcul as calcul  # noqa: E402 — à côté de ce script


def donnees(adresse: str, sortie: str) -> None:
    """Les `Donnees` complètes de la copie, chargées par le dépôt de Gestion MP."""
    calcul._preparer(adresse)  # noqa: SLF001 — l'outil frère, même dossier
    from gestion_mp import depot
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    options = {"options": "-c default_transaction_read_only=on"}
    moteur = create_engine(adresse, connect_args=options)
    with Session(moteur) as s:
        complet = depot.charger(s)
    texte = calcul.texte_json(complet)
    if calcul.texte_json(calcul.relire(json.loads(texte))) != texte:
        raise SystemExit("Aller-retour JSON inexact")
    entete = {"commit_gestion_mp": calcul.commit_gestion_mp(), "source": adresse}
    calcul._ecrire(sortie, {**entete, "donnees": json.loads(texte)})  # noqa: SLF001


def sorties(aujourdhui: str, jours: str, dossier: str, *jeux: str) -> None:
    """Les sorties du moteur de Gestion MP à chaque date, sur chaque jeu de données figé :
    `<dossier>/<nom du jeu>/<date>.json` (JSON simple, sans arrondi)."""
    calcul._preparer()  # noqa: SLF001
    auj = date.fromisoformat(aujourdhui)
    for chemin in jeux:
        with calcul._ouvrir(chemin, "r") as f:  # noqa: SLF001
            complet = calcul.relire(json.load(f)["donnees"])
        nom = Path(chemin).name.split(".")[0]
        (Path(dossier) / nom).mkdir(parents=True, exist_ok=True)
        for jour in jours.split(","):
            rendu = calcul.propre(calcul.sorties_du_moteur(complet, date.fromisoformat(jour), auj))
            calcul._ecrire(Path(dossier) / nom / f"{jour}.json", rendu)  # noqa: SLF001


def _appeler(fonction: Any, session: Any, qui: Any, parametres: dict[str, Any]) -> Any:
    """Une route de Gestion MP appelée comme FastAPI l'appelle : paramètres de requête donnés
    ou à leur défaut, session et compte injectés à la place des dépendances."""
    import inspect

    from fastapi import params
    from fastapi.encoders import jsonable_encoder

    arguments: dict[str, Any] = {}
    types = typing.get_type_hints(fonction)
    for nom, p in inspect.signature(fonction).parameters.items():
        defaut = p.default
        if nom in parametres:
            valeur = parametres[nom]
            dates = (types.get(nom), *typing.get_args(types.get(nom)))
            arguments[nom] = (
                date.fromisoformat(valeur) if isinstance(valeur, str) and date in dates else valeur
            )
        elif nom in ("s", "session"):
            arguments[nom] = session
        elif isinstance(defaut, params.Depends):
            arguments[nom] = qui
        elif isinstance(defaut, params.Param):
            arguments[nom] = defaut.default
    return jsonable_encoder(fonction(**arguments))


def _prix_connus_ce_jour(couts_rendus: Any, jour_de: Any) -> Any:
    """K9 appliquée à Gestion MP : à une date passée, les coûts rendus ne lisent que les
    réceptions jusqu'à cette date (D8 n° 6) — la seule différence avec `couts_rendus`.
    Gestion MP corrigé depuis (d10180e) prend lui-même le jour : il est passé tel quel."""

    def couts(session: Any, donnees: Any, *jour_donne: Any) -> Any:
        jour = jour_de()
        return {
            ref: [c for c in liste if c[0] <= jour]
            for ref, liste in couts_rendus(session, donnees, *jour_donne).items()
            if any(c[0] <= jour for c in liste)
        }

    return couts


def _fil_monte_a_toute_date(a_la_date: Any) -> Any:
    """K7 appliquée à Gestion MP : à une date passée, le fil monté reste connu (décision de
    Mohamed : le fil monté est du stock, à toute date) — la seule différence avec `a_la_date`."""
    import dataclasses

    def rejouer(donnees: Any, date_ref: Any, aujourdhui: Any = None) -> Any:
        rendu = a_la_date(donnees, date_ref, aujourdhui=aujourdhui)
        if donnees.montage_connu and not rendu.montage_connu:
            return dataclasses.replace(rendu, montage_connu=True)
        return rendu

    return rejouer


def _jeu(spec: str) -> tuple[str, str, list[str]]:
    """« nom=chemin+K9 » : le nom du jeu, son fichier (« - » : la base telle quelle), ses
    corrections de PRO appliquées à Gestion MP."""
    nom, _, reste = spec.partition("=")
    chemin, *corrections = reste.split("+")
    return nom, chemin, corrections


def routes(adresse: str, appels: str, dossier: str, *jeux: str) -> None:
    """Les routes de Gestion MP rejouées sur chaque jeu : le dépôt rend le jeu au lieu de la
    base (`depot._charger` remplacé ; « - » : la base elle-même), le reste est lu dans la
    copie (lecture seule)."""
    import dataclasses
    import importlib
    from types import SimpleNamespace

    calcul._preparer(adresse)  # noqa: SLF001
    from gestion_mp import depot
    from gestion_mp.api import pilotage
    from gestion_mp.calcul import moteur
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    liste = json.loads(Path(appels).read_text(encoding="utf-8"))
    options = {"options": "-c default_transaction_read_only=on"}
    qui = SimpleNamespace(id=0, role="direction", nom="Parité", identifiant="parite-direction")
    charger, couts_rendus, a_la_date = depot._charger, pilotage.couts_rendus, moteur.a_la_date  # noqa: SLF001
    jour_courant: list[date] = [date.today()]  # noqa: DTZ011 — l'horloge de Gestion MP
    for spec in jeux:
        nom, chemin, corrections = _jeu(spec)
        depot._charger = charger  # noqa: SLF001
        if chemin != "-":
            with calcul._ouvrir(chemin, "r") as f:  # noqa: SLF001
                complet = calcul.relire(json.load(f)["donnees"])
            vide = dataclasses.replace(complet, mouvements=[], soldes=None)
            depot._charger = lambda _s, avec_journal=True, c=complet, v=vide: (
                c if avec_journal else v
            )  # noqa: SLF001
        depot._cache.clear()  # noqa: SLF001
        moteur.a_la_date = _fil_monte_a_toute_date(a_la_date) if "K7" in corrections else a_la_date
        pilotage.couts_rendus = (
            _prix_connus_ce_jour(couts_rendus, lambda: jour_courant[0])
            if "K9" in corrections
            else couts_rendus
        )
        sortie = Path(dossier) / nom
        sortie.mkdir(parents=True, exist_ok=True)
        with Session(create_engine(adresse, connect_args=options)) as s:
            for a in liste:
                fonction = getattr(importlib.import_module(a["module"]), a["fonction"])
                jour = a["parametres"].get("date_reference")
                jour_courant[0] = date.fromisoformat(jour) if jour else date.today()  # noqa: DTZ011
                rendu = _appeler(fonction, s, qui, a["parametres"])
                calcul._ecrire(sortie / f"{a['nom']}.json", rendu)  # noqa: SLF001


def main() -> None:
    """Point d'entrée : `donnees` ou `sorties`."""
    mode, *args = sys.argv[1:] or [""]
    if mode == "donnees" and len(args) == 2:  # noqa: PLR2004
        donnees(*args)
    elif mode == "sorties" and len(args) >= 4:  # noqa: PLR2004
        sorties(*args)
    elif mode == "routes" and len(args) >= 4:  # noqa: PLR2004
        routes(*args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
