"""Parité par l'API : les écrans de l'alimentation (PLAN-DE-RECETTE-PRO § 7.3).

Les mêmes routes, lues avec le compte de l'alimentation de chaque logiciel :

- **prix absents des deux côtés** : aucune clé monétaire (motifs écrits ici une seconde fois,
  ceux de `securite/prix.py`) ne porte une valeur ; une valeur vue chez Gestion MP est un
  défaut de Gestion MP, chez PRO un défaut de PRO ;
- **quantités égales** : une fois les clés monétaires retirées des deux côtés, les réponses
  sont comparées par les mêmes paires que la direction ;
- **K6** : les réglages et les cours sont refusés (403) à l'alimentation par PRO ; Gestion MP
  les servait (200) avant d'être corrigé — la règle vérifie le statut de chaque côté ;
- la **devise** est vidée par Gestion MP pour l'alimentation (`masquer_prix`), tenue pour
  neutre par PRO (S2, `test_prix_masques.NEUTRES`) : ni prix ni montant, retirée des deux côtés
  avant la comparaison et signalée ;
- un écart de valeur est expliqué par la classe que la passe de la direction a donnée au même
  écart sur la même route (`direction`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Any

from parite_api import Ecart, Liste, Resultat, Route, comparer_route
from parite_api_documents import _formes
from parite_api_formes import nul, type_magasin
from parite_api_passe import _liste_ou_pages
from parite_serveurs import Serveurs

MONETAIRES = (
    "prix*", "montant*", "valeur*", "cout*", "cmup*", "budget*", "cours*", "taux_droits",
    "economie*", "revient*", "tva*", "droits*", "frais*", "devise_prix", "*_mad",
)  # fmt: skip
RIEN = (None, "", 0, 0.0)
MASQUEES_PAR_GESTION_MP = ("devise",)
"""Vidées par Gestion MP pour l'alimentation sans être des prix (signalé, voir l'en-tête)."""
K6 = ("/api/parametres", "/api/devises")
"""Réglages et cours : 403 pour l'alimentation chez PRO (K6), 200 chez Gestion MP."""


def monetaire(cle: str) -> bool:
    """Une clé de prix ou de montant."""
    return any(fnmatch(cle, motif) for motif in MONETAIRES)


def prix_vus(x: Any, chemin: str = "") -> list[tuple[str, Any]]:
    """Les clés monétaires qui portent une valeur, partout dans la réponse."""
    vus: list[tuple[str, Any]] = []
    if isinstance(x, dict):
        for k, v in x.items():
            if monetaire(str(k)) and not isinstance(v, dict | list) and v not in RIEN:
                vus.append((f"{chemin}/{k}", v))
            vus += prix_vus(v, f"{chemin}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            vus += prix_vus(v, f"{chemin}/{i}")
    return vus


def sans_prix(x: Any) -> Any:
    """La réponse sans ses clés monétaires (masquées des deux côtés)."""
    if isinstance(x, dict):
        return {
            k: sans_prix(v)
            for k, v in x.items()
            if not monetaire(str(k)) and k not in MASQUEES_PAR_GESTION_MP
        }
    if isinstance(x, list):
        return [sans_prix(v) for v in x]
    return x


ROUTES = (
    Route("alimentation : stock", "/api/stock", "/api/stock",
          liste=Liste(("reference",), formes={"action": nul})),
    Route("alimentation : lots", "/api/soldes", "/api/lots",
          liste=Liste(("lot_id",), renommes={"article_id": "matiere_id"},
                      sous={"magasins": Liste(("magasin_id",), formes={"type": type_magasin})})),
    Route("alimentation : ordres", "/api/bons", "/api/ordres",
          liste=Liste(("id",), formes=_formes(),
                      deplaces={"fabrications": "comparé par la direction (« ordres »)",
                                "lignes": "comparé par la direction (« ordres »)",
                                "theorique": "comparé par la direction (`prevu`)",
                                "par_fil": "comparé par la direction",
                                "retours_detail": "comparé par la direction",
                                "retours": "comparé par la direction",
                                "valide_le": "comparé par la direction (K8e)",
                                "numero": "comparé par la direction (K8d)"})),
    Route("alimentation : inventaires", "/api/inventaires", "/api/inventaires",
          liste=Liste(("id",), formes=_formes())),
)  # fmt: skip


@dataclass
class Alimentation:
    """Ce que la passe de l'alimentation a vu."""

    resultats: list[Resultat] = field(default_factory=list)
    prix_gestion_mp: list[tuple[str, str, Any]] = field(default_factory=list)
    prix_pro: list[tuple[str, str, Any]] = field(default_factory=list)
    k6: list[tuple[str, int, int]] = field(default_factory=list)


DIRECTION = {
    "alimentation : stock": "stock",
    "alimentation : lots": "soldes",
    "alimentation : ordres": "ordres",
    "alimentation : inventaires": "inventaires",
}
"""La route de la direction dont la passe explique les écarts de valeur de l'alimentation."""


def _comme_la_direction(r: Resultat, direction: list[Resultat]) -> None:
    """Un écart déjà expliqué, identique, sur la même route lue par la direction."""
    nom = DIRECTION.get(r.route)
    connus = {
        (e.cle, e.champ, repr(e.gmp), repr(e.pro)): e.classe
        for d in direction if d.route == nom for e in d.ecarts if e.classe
    }  # fmt: skip
    for e in r.ecarts:
        e.classe = e.classe or connus.get((e.cle, e.champ, repr(e.gmp), repr(e.pro)))


def passe(s: Serveurs, direction: list[Resultat]) -> Alimentation:
    """Les routes de l'alimentation, des deux côtés."""
    a = Alimentation()
    gmp, pro = s.gestion_mp["alimentation"], s.pro["alimentation"]
    for route in ROUTES:
        g = gmp.get(route.gmp)
        # PRO peut paginer (Page[T]) : on recompose la liste entière (curseur) avant de comparer.
        p = _liste_ou_pages(pro, route.pro, pro.get(route.pro), route.champ_pro)
        a.prix_gestion_mp += [(route.nom, c, v) for c, v in prix_vus(g)]
        a.prix_pro += [(route.nom, c, v) for c, v in prix_vus(p)]
        r = comparer_route(route, sans_prix(g), sans_prix(p))
        _comme_la_direction(r, direction)
        a.resultats.append(r)
    for chemin in K6:
        statut_g, _ = gmp.appeler("GET", chemin)
        statut_p, _ = pro.appeler("GET", chemin)
        a.k6.append((chemin, statut_g, statut_p))
        if statut_p != 403 or statut_g not in (200, 403):
            a.resultats.append(
                Resultat(f"alimentation : {chemin}", ecarts=[
                    Ecart("K6", chemin, "statut", statut_g, statut_p)
                ])
            )  # fmt: skip
    return a
