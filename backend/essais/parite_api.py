"""Parité par l'API (PLAN-DE-RECETTE-PRO § 7.3) : les réponses des deux serveurs, champ à champ.

Chaque paire de routes (`parite_api_routes.ROUTES`) dit comment lire les éléments de chaque
réponse (liste, clé), quels champs PRO a renommés, quelles formes il a changées
(`parite_api_formes`), quels champs de Gestion MP sont rendus ailleurs (et où ils sont
comparés) ; le reste est comparé aux tolérances du § 7.5.

- un champ de PRO absent de Gestion MP est un **champ ajouté** (compté, excusé) ;
- un champ de Gestion MP absent de PRO, ni renommé ni déplacé, est un écart (**réciproque**,
  § 7.7) ;
- un élément en plus ou en moins est un écart ;
- un écart de valeur n'est expliqué que par une règle de `parite_api_regles` qui en vérifie la
  forme et l'ampleur ; sinon il est à corriger.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import parite_comparer as pc
from parite_api_formes import Forme, codes_du_stock


@dataclass(frozen=True)
class Liste:
    """Une liste d'éléments comparés par clé (au premier niveau ou dans un élément)."""

    cle: tuple[str, ...]
    renommes: dict[str, str] = field(default_factory=dict)
    formes: dict[str, Forme] = field(default_factory=dict)
    deplaces: dict[str, str] = field(default_factory=dict)
    sous: dict[str, Liste] = field(default_factory=dict)
    cle_pro: tuple[str, ...] | None = None
    vue_pro: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    """La vue « Gestion MP » d'un élément de PRO, quand PRO rend la même chose autrement
    (traduction déclarée, appliquée avant la comparaison)."""


@dataclass(frozen=True)
class Route:
    """Une paire de routes GET comparées."""

    nom: str
    gmp: str
    pro: str
    liste: Liste | None = None
    entete: Liste = field(default_factory=lambda: Liste(()))
    champ_gmp: str = "lignes"
    champ_pro: str = "lignes"
    fiche_gmp: str = ""
    """Adresse de la fiche (`…/{id}`) : la liste est remplacée par les fiches, une par élément."""
    fiche_pro: str = ""
    page_gmp: bool = False
    """Liste paginée (Gestion MP : `limite`, `decalage` ; PRO : `limite`, `apres`)."""
    page_pro: bool = False
    moteur: Callable[[str, str], pc.Chemin | None] | None = None
    jour: str = ""


@dataclass
class Ecart:
    """Un écart : route, élément, champ, valeurs, classe (`None` : à corriger)."""

    route: str
    cle: str
    champ: str
    gmp: Any
    pro: Any
    classe: str | None = None
    element: dict[str, Any] | None = field(default=None, repr=False)
    """L'élément de Gestion MP où l'écart se trouve (les règles y lisent son contexte)."""


@dataclass
class Resultat:
    """Ce qu'une paire de routes a donné."""

    route: str
    comparees: int = 0
    traduites: Counter[str] = field(default_factory=Counter)
    ajoutes: set[str] = field(default_factory=set)
    deplaces: dict[str, str] = field(default_factory=dict)
    ecarts: list[Ecart] = field(default_factory=list)


def _cle(e: dict[str, Any], noms: tuple[str, ...]) -> str:
    return " | ".join(str(e.get(n)) for n in noms)


def _ranger(elements: Any, noms: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(elements, dict):
        return {str(k): v for k, v in elements.items()}
    rangees: dict[str, Any] = {}
    for e in elements:
        cle = _cle(e, noms)
        n = sum(1 for k in rangees if k == cle or k.startswith(f"{cle} #"))
        rangees[cle if n == 0 else f"{cle} #{n + 1}"] = e
    return rangees


def _valeurs(  # noqa: PLR0917
    r: Resultat,
    nom: str,
    cle: str,
    champ: str,
    g: Any,
    p: Any,
    forme: Forme | None,
    element: dict[str, Any] | None = None,
) -> None:
    if forme is not None:
        g2, p2 = forme(g, p)
        if (g2, p2) != (g, p):
            r.traduites[champ] += 1
        g, p = g2, p2
    bilan = pc.comparer(g, p, chemin=(champ,))
    r.comparees += bilan.comparees
    for chemin, x, y in bilan.ecarts:
        if x is pc.ABSENT:  # une clé que seul PRO rend, dans un objet imbriqué : un ajout
            r.ajoutes.add(f"{nom}.{'/'.join(c for c in chemin if not c.isdigit())}")
            continue
        r.ecarts.append(Ecart(nom, cle, "/".join(chemin), x, y, element=element))


def comparer_element(  # noqa: PLR0917
    r: Resultat, nom: str, cle: str, g: dict[str, Any], p: dict[str, Any], liste: Liste
) -> None:
    """Un élément : ses champs, renommés et traduits, et ses sous-listes."""
    cibles = {liste.renommes.get(x, x).partition(".")[0] for x in g}
    r.ajoutes |= {f"{nom}.{k}" for k in set(p) - cibles}
    for champ, valeur in g.items():
        if champ in liste.deplaces:
            r.deplaces[f"{nom}.{champ}"] = liste.deplaces[champ]
            continue
        cible = liste.renommes.get(champ, champ)
        if "." in cible:  # un champ rangé dans un objet de PRO (« indicateurs.budget_mad »)
            tete, _, queue = cible.partition(".")
            p = {**p, cible: (p.get(tete) or {}).get(queue, pc.ABSENT)}
            if p[cible] is pc.ABSENT:
                del p[cible]
        if cible not in p:
            r.ecarts.append(
                Ecart(nom, cle, f"{champ} (absent de PRO)", valeur, pc.ABSENT, element=g)
            )
            continue
        if champ in liste.sous:
            sous = liste.sous[champ]
            comparer_listes(r, f"{nom}.{champ}", valeur, p[cible], sous, f"{cle} › ", g)
            continue
        _valeurs(r, nom, cle, champ, valeur, p[cible], liste.formes.get(champ), g)


def comparer_listes(  # noqa: PLR0917
    r: Resultat,
    nom: str,
    g: Any,
    p: Any,
    liste: Liste,
    prefixe: str = "",
    parent: dict[str, Any] | None = None,
) -> None:
    """Deux listes d'éléments rangées par clé : éléments en plus ou en moins, puis champs."""
    gs, ps = _ranger(g, liste.cle), _ranger(p, liste.cle_pro or liste.cle)
    for cle in sorted(set(gs) | set(ps)):
        if cle not in ps or cle not in gs:
            r.ecarts.append(
                Ecart(nom, prefixe + cle, "(élément)", gs.get(cle, pc.ABSENT),
                      ps.get(cle, pc.ABSENT), element=parent)
            )  # fmt: skip
            continue
        p = liste.vue_pro(ps[cle]) if liste.vue_pro else ps[cle]
        if p is not ps[cle]:
            r.traduites["(vue de l'élément)"] += 1
        comparer_element(r, nom, prefixe + cle, gs[cle], p, liste)


def comparer_route(route: Route, gmp: Any, pro: Any) -> Resultat:
    """Les deux réponses d'une paire de routes."""
    r = Resultat(route.nom)
    pro, codes = codes_du_stock(pro)
    if codes:
        r.traduites["codes du stock"] += codes
    if route.liste is not None:
        lg = gmp.get(route.champ_gmp, []) if isinstance(gmp, dict) else gmp
        lp = pro.get(route.champ_pro, []) if isinstance(pro, dict) else pro
        comparer_listes(r, route.nom, lg, lp, route.liste)
    if isinstance(gmp, dict) and isinstance(pro, dict):
        listes = (route.champ_gmp, route.champ_pro) if route.liste is not None else ()
        tete_g = {k: v for k, v in gmp.items() if k not in listes}
        tete_p = {k: v for k, v in pro.items() if k not in listes}
        comparer_element(r, route.nom, "(en-tête)", tete_g, tete_p, route.entete)
    return r


Regle = Callable[[Route, Ecart], str | None]


def expliquer(route: Route, r: Resultat, regles: list[Regle]) -> None:
    """La classe de chaque écart de valeur : la première règle qui le reconnaît."""
    for e in r.ecarts:
        if e.classe is None:
            e.classe = next((c for c in (regle(route, e) for regle in regles) if c), None)


def resume(resultats: list[Resultat]) -> dict[str, Counter[str]]:
    """Par route : feuilles comparées, champs traduits, écarts expliqués par classe."""
    sortie: dict[str, Counter[str]] = {}
    for r in resultats:
        c = sortie.setdefault(r.route, Counter())
        c["comparées"] += r.comparees
        c["traduites"] += sum(r.traduites.values())
        c["champs ajoutés"] += len(r.ajoutes)
        c["champs déplacés"] += len(r.deplaces)
        for e in r.ecarts:
            c[e.classe or "à corriger"] += 1
    return sortie
