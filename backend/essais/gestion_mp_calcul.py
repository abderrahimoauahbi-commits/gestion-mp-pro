"""Côté Gestion MP : les sorties attendues de la parité unitaire du moteur (lot S3).

ARCHITECTURE § 3 : « côté Gestion MP : copie de comparaison_calcul (lancée par le Python de
~/gestion-mp) ». Ce script n'importe pas `gestion_mp_pro` : il tourne dans l'environnement de
Gestion MP (`~/gestion-mp/.venv/bin/python`) et calcule avec son moteur, une fois, ce que le
moteur porté doit retrouver à l'identique sur les jeux figés de `tests/moteur/jeux/`.

    python essais/gestion_mp_calcul.py extraire <url_base> <jour> <nom> <perimetre_json> \\
        <description> <sortie_jeu.json[.xz]>
    python essais/gestion_mp_calcul.py calculer <jeu.json[.xz]> <sortie_attendu.json[.xz]>

`extraire` fige les données COMPLÈTES d'une base (`depot.charger`, journal et soldes compris),
réduites à un périmètre de références : c'est le moteur qui rejoue la date (`a_la_date`), des
deux côtés. `calculer` relit un jeu en dataclasses de `gestion_mp.calcul.modele` et écrit toutes
les sorties du moteur, sans arrondi : la parité se juge à l'égalité exacte.

Format (relu par `tests/moteur/jeux_outils.py`) : une dataclass = l'objet de ses champs ;
dates en ISO ; tuples en listes ; clés entières (`parts`) en texte ; `soldes` = liste triée
`[réf, lot, magasin, q]`. Un fichier `.xz` est compressé. Les annotations disent les types.
"""

from __future__ import annotations

import dataclasses
import json
import lzma
import os
import subprocess
import sys
import types
import typing
from datetime import date, datetime
from pathlib import Path
from typing import Any

GESTION_MP = Path(os.getenv("GESTION_MP_CODE", str(Path.home() / "gestion-mp")))
# Le jour de la production des jeux, figé : le montage des métiers n'est connu qu'à partir de lui.
AUJOURDHUI = date(2026, 10, 8)
CHAMP_DU_PERIMETRE = {"fournisseurs": "fournisseur", "roles": "role_bom", "references": "reference"}
CHAMP_DU_PERIMETRE["compositions"] = "composition"


def _preparer(url: str | None = None) -> None:
    """Rend le code de Gestion MP importable, sur la base voulue et sans tâche de fond."""
    if url:
        os.environ["GESTION_MP_BASE"] = url
    os.environ["GESTION_MP_TACHES"] = "0"
    if str(GESTION_MP) not in sys.path:
        sys.path.insert(0, str(GESTION_MP))
    import gestion_mp.config  # noqa: F401 — le fuseau de l'usine, comme dans l'application


def commit_gestion_mp() -> str:
    """Le commit du code de Gestion MP qui calcule."""
    commande = ["git", "-C", str(GESTION_MP), "rev-parse", "HEAD"]
    sortie = subprocess.run(commande, capture_output=True, text=True, check=True)  # noqa: S603
    return sortie.stdout.strip()


def _ouvrir(chemin: str | Path, mode: str) -> Any:
    """Un fichier texte UTF-8, compressé (xz) quand son nom finit par `.xz`."""
    if str(chemin).endswith(".xz"):
        reglage = {"preset": 9} if mode == "w" else {}
        return lzma.open(chemin, mode + "t", encoding="utf-8", **reglage)
    return open(chemin, mode, encoding="utf-8")  # noqa: SIM115 — rendu à un `with`


def _ecrire(chemin: str | Path, valeur: Any) -> None:
    """Écrit un JSON compact, en UTF-8, sans échappement des accents."""
    with _ouvrir(chemin, "w") as f:
        json.dump(valeur, f, ensure_ascii=False, separators=(",", ":"))


_ANNOTATIONS: dict[type, dict[str, Any]] = {}


def _annotations(cls: type) -> dict[str, Any]:
    """Les types des champs d'une dataclass, évalués une fois."""
    if cls not in _ANNOTATIONS:
        _ANNOTATIONS[cls] = typing.get_type_hints(cls)
    return _ANNOTATIONS[cls]


def _cles_tuples(annotation: Any) -> bool:
    """Le champ est-il un dict à clés tuples (`soldes`), même vide ou facultatif ?"""
    dicts = [a for a in (annotation, *typing.get_args(annotation)) if typing.get_origin(a) is dict]
    return any(typing.get_origin(typing.get_args(a)[0]) is tuple for a in dicts)


def vers_json(x: Any, en_lignes: bool = False) -> Any:
    """Une valeur des données en JSON (format en tête) ; `en_lignes` : un dict à clés tuples."""
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        hints = _annotations(type(x))
        return {
            f.name: vers_json(getattr(x, f.name), _cles_tuples(hints[f.name]))
            for f in dataclasses.fields(x)
        }
    if isinstance(x, date):  # un instant (datetime) est aussi une date
        return x.isoformat()
    if isinstance(x, list | tuple):
        return [vers_json(e) for e in x]
    if isinstance(x, dict) and (en_lignes or any(isinstance(k, tuple) for k in x)):
        return sorted([*map(vers_json, k), vers_json(v)] for k, v in x.items())
    if isinstance(x, dict):
        return {str(k): vers_json(v) for k, v in x.items()}
    if x is None or isinstance(x, str | int | float):
        return x
    raise TypeError(f"Type inattendu dans les données : {type(x).__name__}")


def _relire_tuple(v: list[Any], *elements: Any) -> tuple[Any, ...]:
    """Un tuple de longueur fixe, chaque élément à son type."""
    return tuple(depuis_json(e, a) for e, a in zip(v, elements, strict=True))


def _relire_dict(v: Any, cle: Any = Any, valeur: Any = Any) -> dict[Any, Any]:
    """Un dict : clés tuples (liste de lignes `[*clé, valeur]`), entières ou texte."""
    if typing.get_origin(cle) is tuple:
        n = len(typing.get_args(cle))
        return {_relire_tuple(r[:n], *typing.get_args(cle)): depuis_json(r[n], valeur) for r in v}
    return {(int(k) if cle is int else k): depuis_json(e, valeur) for k, e in v.items()}


_LECTEURS = {list: lambda v, t=Any: [depuis_json(e, t) for e in v], tuple: _relire_tuple}  # typés
_LECTEURS[dict] = _relire_dict


def depuis_json(v: Any, annotation: Any) -> Any:
    """Une valeur JSON rendue au type que l'annotation du champ demande (nombres tels quels)."""
    if v is None:
        return None
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        utiles = [a for a in typing.get_args(annotation) if a is not type(None)]
        return depuis_json(v, utiles[0]) if len(utiles) == 1 else v
    if annotation in (date, datetime):
        return annotation.fromisoformat(v)
    if dataclasses.is_dataclass(annotation):
        return relire_dataclass(annotation, v)
    lecteur = _LECTEURS.get(typing.get_origin(annotation) or annotation)
    return lecteur(v, *typing.get_args(annotation)) if lecteur else v


def relire_dataclass(cls: Any, v: dict[str, Any]) -> Any:
    """Une dataclass reconstruite champ par champ (son constructeur : `__post_init__` joue)."""
    hints = _annotations(cls)
    return cls(**{f.name: depuis_json(v[f.name], hints[f.name]) for f in dataclasses.fields(cls)})


def relire(donnees: dict[str, Any]) -> Any:
    """Les `Donnees` du moteur de Gestion MP, relues d'un jeu."""
    from gestion_mp.calcul.modele import Donnees

    return relire_dataclass(Donnees, donnees)


def texte_json(x: Any) -> str:
    """La forme JSON exacte d'une valeur des données, pour comparer à l'octet."""
    return json.dumps(vers_json(x), ensure_ascii=False, separators=(",", ":"))


def references_du_perimetre(donnees: Any, perimetre: dict[str, Any]) -> set[str] | None:
    """Les références retenues ; None : tout."""
    if perimetre["type"] == "tout":
        return None
    champ = CHAMP_DU_PERIMETRE[perimetre["type"]]
    valeurs = set(perimetre["valeurs"])
    return {a.reference for a in donnees.articles if getattr(a, champ) in valeurs}


def _garder_lignes(documents: list[Any], refs: set[str]) -> list[Any]:
    """Les documents réduits à leurs lignes du périmètre ; un document vidé disparaît."""
    gardes = []
    for doc in documents:
        lignes = [x for x in doc.lignes if x.reference in refs]
        if lignes:
            gardes.append(dataclasses.replace(doc, lignes=lignes))
    return gardes


def filtrer(donnees: Any, perimetre: dict[str, Any]) -> Any:
    """Les données réduites aux références du périmètre (le reste est gardé tel quel)."""
    refs = references_du_perimetre(donnees, perimetre)
    if refs is None:
        return donnees
    remplace = dataclasses.replace

    def garder(liste: list[Any]) -> list[Any]:
        return [x for x in liste if x.reference in refs]

    def theorique(o: Any) -> dict[str, float] | None:
        return None if o.theorique is None else {r: q for r, q in o.theorique.items() if r in refs}

    soldes = donnees.soldes
    return remplace(
        donnees,
        articles=garder(donnees.articles),
        recettes=garder(donnees.recettes),
        mouvements=garder(donnees.mouvements),
        historique_prix=garder(donnees.historique_prix),
        commandes=_garder_lignes(donnees.commandes, refs),
        receptions=_garder_lignes(donnees.receptions, refs),
        # Un dossier garde toutes ses charges même si des marchandises partent : c'est voulu.
        dossiers_import=[remplace(x, lignes=garder(x.lignes)) for x in donnees.dossiers_import],
        metiers=[remplace(m, fils=garder(m.fils)) for m in donnees.metiers],
        soldes=None if soldes is None else {k: q for k, q in soldes.items() if k[0] in refs},
        ordres=[remplace(o, theorique=theorique(o)) for o in donnees.ordres],
    )


def _verifier_aller_retour(complet_p: Any, texte: str, jour: date) -> Any:
    """Le JSON relu redonne les mêmes données, et la même journée rejouée."""
    from gestion_mp.calcul import moteur

    relu = relire(json.loads(texte))
    if texte_json(relu) != texte:
        raise AssertionError("Aller-retour JSON inexact")
    if relu != complet_p:
        raise AssertionError("Les données relues diffèrent (types ou valeurs)")
    rejoue = moteur.a_la_date(complet_p, jour, aujourdhui=AUJOURDHUI)
    if texte_json(moteur.a_la_date(relu, jour, aujourdhui=AUJOURDHUI)) != texte_json(rejoue):
        raise AssertionError("a_la_date diffère sur les données relues")
    return rejoue


def extraire(
    url: str, jour_texte: str, nom: str, perimetre_texte: str, *, description: str, sortie: str
) -> None:
    """Fige un jeu : les données complètes d'une base, au périmètre, et leur date."""
    _preparer(url)
    from gestion_mp import depot
    from gestion_mp.db import Sessions

    jour = date.fromisoformat(jour_texte)
    perimetre = json.loads(perimetre_texte)
    with Sessions() as s:
        complet = depot.charger(s)
    complet_p = filtrer(complet, perimetre)
    texte = texte_json(complet_p)
    rejoue = _verifier_aller_retour(complet_p, texte, jour)
    entete = {"nom": nom, "description": description, "jour": jour.isoformat()}
    entete |= {"aujourdhui": AUJOURDHUI.isoformat(), "perimetre": perimetre}
    entete |= {"commit_gestion_mp": commit_gestion_mp()}
    _ecrire(sortie, {**entete, "donnees": json.loads(texte)})
    noms = ("articles", "mouvements", "commandes", "receptions", "dossiers_import", "ordres")
    volumes = {n: len(getattr(complet_p, n)) for n in noms}
    volumes["mouvements_a_la_date"] = len(rejoue.mouvements)
    sys.stdout.write(f"{nom} : {json.dumps(volumes, ensure_ascii=False)}\n")


def revient_en_dict(r: Any) -> dict[str, Any]:
    """Une `LigneRevient` : ses champs et ses propriétés calculées."""
    noms = [f.name for f in dataclasses.fields(r)]
    noms += ["revient_mad", "revient_unite", "valeur_unite", "surcout", "decaisse_mad"]
    return {n: getattr(r, n) for n in noms}


def _a_la_date(d: Any) -> dict[str, Any]:
    """Ce que la date rejouée a gardé : volumes, et chaque bon tel qu'il était."""
    volumes = ("mouvements", "receptions", "historique_prix", "ordres")
    resume = {"montage_connu": d.montage_connu} | {n: len(getattr(d, n)) for n in volumes}
    resume["soldes"] = d.soldes is not None
    noms = ("numero", "statut", "solde_a_la_main_le", "annulee_le")
    resume["commandes"] = [
        {n: getattr(c, n) for n in noms} | {"recu": [x.quantite_recue for x in c.lignes]}
        for c in d.commandes
    ]
    return resume


# Les sorties tirées des données à la date seules, du jour en plus, de l'état du stock en plus.
# Chaque clé est le nom de la fonction du moteur, sauf les renommées.
SUR_DONNEES = (
    "nomenclature controle_recettes fils_en_machine stock_en_machine cmup_par_reference "
    "prix_constates achats_dates historique_prix performance_receptions scorecard "
    "devises_pratiquees pesees evolution_bobines lots ordres revient_par_lot"
).split()
SUR_JOUR = ("plan_mensuel", "besoins", "cout_matiere_annuel")
SUR_STOCK = ("plan_achat", "valorisation")
RENOMMEES = {"scorecard": "scorecard_fournisseurs", "lots": "stock_par_lot"}
RENOMMEES |= {"ordres": "consommation_par_of", "besoins": "besoins_mensuels"}


def _sorties_particulieres(d: Any, jour: date, lignes: list[Any], aujourdhui: date) -> dict:
    """Coûts du journal, opportunités, pilotage, lots disponibles, traçabilité, réalisé."""
    from gestion_mp.calcul import moteur

    couts = moteur.couts_du_journal(d)
    en_stock = sorted({x.reference for x in moteur.stock_par_lot(d) if x.stock > 1e-3})[:15]
    lots_fournisseur = sorted({m.lot_fournisseur for m in d.mouvements if m.lot_fournisseur})[:5]
    return {
        "couts_du_journal": {n: getattr(couts, n) for n in ("unitaire", "stock", "consommation")}
        | {"cmup": couts.cmup()},
        "opportunites": {
            str(mc): moteur.comparer_les_prix(d, lignes, meme_couleur=mc) for mc in (False, True)
        },
        "cockpit": moteur.cockpit(d, jour, lignes),
        "cockpit_meme_couleur": moteur.cockpit(d, jour, lignes, meme_couleur=True),
        "lots_disponibles": {ref: moteur.lots_disponibles(d, ref) for ref in en_stock},
        "tracabilite": {lot: moteur.tracabilite(d, lot=lot) for lot in lots_fournisseur},
        "realise": moteur.realise_par_qualite(d, jour, aujourdhui),
    }


def _sorties_import(d: Any) -> dict[str, Any]:
    """Le revient des dossiers d'importation, leur TVA, leur facture et leurs alertes."""
    from gestion_mp.calcul import moteur

    p = d.parametres
    revients = {x.numero: moteur.revient_dossier(x, p) for x in d.dossiers_import}
    seuil = p.seuil_surcout_import
    return {
        "revient": {n: [revient_en_dict(r) for r in rs] for n, rs in revients.items()},
        "tva_attendue": {x.numero: moteur.tva_attendue(x, p) for x in d.dossiers_import},
        "ecart_facture": {x.numero: moteur.ecart_facture(x, p) for x in d.dossiers_import},
        "aberrantes": {
            n: [r.ligne_id for r in moteur.lignes_aberrantes(rs, seuil)]
            for n, rs in revients.items()
        },
        "negatives": {
            n: [r.ligne_id for r in moteur.lignes_negatives(rs)] for n, rs in revients.items()
        },
        "revient_par_reception": {
            k: revient_en_dict(v) for k, v in moteur.revient_par_reception(d).items()
        },
    }


def sorties_du_moteur(complet: Any, jour: date, aujourdhui: date) -> dict[str, Any]:
    """Tout ce que le moteur de Gestion MP produit sur un jeu, à sa date."""
    from gestion_mp.calcul import controles, moteur

    d = moteur.a_la_date(complet, jour, aujourdhui=aujourdhui)
    lignes = moteur.etat_stock(d, jour)
    ctl = controles.controler(d, lignes, jour, complet=complet, aujourdhui=aujourdhui)
    sorties: dict[str, Any] = {"a_la_date": _a_la_date(d), "stock": lignes}
    for cles, args in ((SUR_DONNEES, (d,)), (SUR_JOUR, (d, jour)), (SUR_STOCK, (d, lignes))):
        sorties |= {cle: getattr(moteur, RENOMMEES.get(cle, cle))(*args) for cle in cles}
    sorties |= _sorties_particulieres(d, jour, lignes, aujourdhui) | _sorties_import(d)
    noms = ("code", "libelle", "gravite", "anomalies", "garanti", "detail")
    sorties["controles"] = [{n: getattr(c, n) for n in noms} for c in ctl]
    sorties["synthese"] = controles.synthese(ctl)
    return sorties


def _texte_cle(k: Any) -> str:
    """Une clé de dict en texte : un tuple joint par « | »."""
    return " | ".join(map(str, map(propre, k))) if isinstance(k, tuple) else str(propre(k))


def _propre_dict(x: dict[Any, Any]) -> dict[str, Any]:
    """Un dict à clés texte ; deux clés qui donneraient le même texte sont refusées."""
    rendu = {_texte_cle(k): propre(v) for k, v in x.items()}
    if len(rendu) != len(x):
        raise ValueError("Deux clés distinctes donnent le même texte")
    return rendu


def propre(x: Any) -> Any:
    """Une sortie du moteur à plat, sans arrondi : l'égalité doit être exacte."""
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        x = {f.name: getattr(x, f.name) for f in dataclasses.fields(x)}
    elif not isinstance(x, dict | list | tuple | set | frozenset | date) and hasattr(x, "__dict__"):
        x = vars(x)
    if isinstance(x, dict):
        return _propre_dict(x)
    if isinstance(x, list | tuple | set | frozenset):
        valeurs = [propre(v) for v in x]
        return sorted(valeurs, key=str) if isinstance(x, set | frozenset) else valeurs
    if isinstance(x, date):  # un instant (datetime) est aussi une date
        return x.isoformat()
    if x is None or isinstance(x, str | int | float):
        return x
    raise TypeError(f"Sortie de type inattendu : {type(x).__name__}")


def calculer(chemin_jeu: str, sortie: str) -> None:
    """Calcule une fois, avec le moteur de Gestion MP, les sorties attendues d'un jeu."""
    _preparer()
    with _ouvrir(chemin_jeu, "r") as f:
        jeu = json.load(f)
    complet = relire(jeu["donnees"])
    jour, aujourdhui = date.fromisoformat(jeu["jour"]), date.fromisoformat(jeu["aujourdhui"])
    sorties = propre(sorties_du_moteur(complet, jour, aujourdhui))
    entete = {"commit_gestion_mp": commit_gestion_mp(), "jeu": jeu["nom"]}
    _ecrire(sortie, {**entete, "sorties": sorties})


def main() -> None:
    """Point d'entrée : `extraire` ou `calculer`."""
    mode, *args = sys.argv[1:] or [""]
    if mode == "extraire" and len(args) == 6:
        extraire(*args[:4], description=args[4], sortie=args[5])
    elif mode == "calculer" and len(args) == 2:
        calculer(*args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
