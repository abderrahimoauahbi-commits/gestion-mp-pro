"""Parité dynamique : les outils (gestes envoyés aux deux serveurs, photos, écarts).

Un geste est envoyé aux deux serveurs ; son issue est comparée (accepté des deux côtés, ou
refusé des deux côtés : une acceptation d'un côté et un refus de l'autre est un écart, sauf
correction déclarée qui le prévoit — K2, K4). Après chaque geste, on photographie le stock, la
valorisation, les lots et les documents touchés des deux côtés, et l'on compare **ce que le
geste a changé** (après − avant) : les écarts de l'année reprise (K1…K9, expliqués par la
passe statique) ne s'y mêlent pas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import parite_comparer as pc
from parite_api import Ecart, Liste, Resultat, comparer_listes
from parite_serveurs import Client, Serveurs


def accepte(statut: int) -> bool:
    """Un geste accepté (2xx)."""
    return 200 <= statut < 300  # noqa: PLR2004


@dataclass
class Issue:
    """Un geste joué des deux côtés : statuts, réponses."""

    nom: str
    statut_gmp: int
    reponse_gmp: Any
    statut_pro: int
    reponse_pro: Any

    @property
    def meme_issue(self) -> bool:
        """Accepté des deux côtés, ou refusé des deux côtés."""
        return accepte(self.statut_gmp) == accepte(self.statut_pro)


@dataclass
class Journal:
    """Ce que la passe dynamique a vu, geste par geste."""

    gestes: list[Issue] = field(default_factory=list)
    resultats: list[Resultat] = field(default_factory=list)

    def resultat(self, nom: str) -> Resultat:
        """Le résultat (comparaisons) du geste `nom`, créé au besoin."""
        for r in self.resultats:
            if r.route == nom:
                return r
        r = Resultat(nom)
        self.resultats.append(r)
        return r


def jouer(  # noqa: PLR0917
    s: Serveurs,
    j: Journal,
    nom: str,
    gmp: tuple[str, str, Any],
    pro: tuple[str, str, Any],
    attendu: str = "",
) -> Issue:
    """Un geste envoyé aux deux serveurs (compte de direction) ; l'issue est notée.

    `attendu` : la correction déclarée qui prévoit une issue différente (K2, K4)."""
    sg, rg = s.gestion_mp["direction"].appeler(*gmp)
    sp, rp = s.pro["direction"].appeler(*pro)
    issue = Issue(nom, sg, rg, sp, rp)
    j.gestes.append(issue)
    if not issue.meme_issue:
        classe = attendu if attendu and not accepte(sg) and accepte(sp) else None
        j.resultat(nom).ecarts.append(Ecart(nom, "(issue)", "statut", sg, sp, classe))
    elif not accepte(sg):  # refusé des deux côtés : le même message (REGLES, mot pour mot)
        mg, mp = _message(rg), _message(rp)
        r = j.resultat(nom)
        r.comparees += 1
        if mg != mp:
            r.ecarts.append(Ecart(nom, "(refus)", "message", mg, mp))
    return issue


def _message(reponse: Any) -> Any:
    return reponse.get("detail") if isinstance(reponse, dict) else reponse


INSTANT = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d")


def au_jour(x: Any) -> Any:
    """Les instants ramenés au jour : deux serveurs, deux horloges, quelques secondes d'écart
    pour un même geste (comparés au jour, jamais ignorés)."""
    if isinstance(x, dict):
        return {k: au_jour(v) for k, v in x.items()}
    if isinstance(x, list):
        return [au_jour(v) for v in x]
    if isinstance(x, str) and INSTANT.match(x):
        return x[:10]
    return x


def comparer_document(j: Journal, nom: str, liste: Liste, gmp: Any, pro: Any) -> None:
    """Le document créé par un geste, des deux côtés, par la paire de routes de la direction."""
    comparer_listes(j.resultat(nom), nom, [au_jour(gmp)], [au_jour(pro)], liste)


def _lignes(rep: Any, champ: str = "lignes") -> list[dict[str, Any]]:
    return rep if isinstance(rep, list) else rep.get(champ, rep.get("elements", []))


STOCK_AJOUTES = ("matiere_id", "role_id", "fournisseur_id")
"""Champs d'une ligne de stock que PRO ajoute (RESTES3 § 1.2) : hors de la comparaison."""


def _ligne_stock(x: dict[str, Any], pro: bool) -> dict[str, Any]:
    """Une ligne de stock sans les champs ajoutés par PRO ; côté PRO, codes du statut et de
    l'action ramenés aux libellés de Gestion MP (RESTES3 § 1.1, forme déclarée)."""
    from parite_api_formes import codes_du_stock

    ligne = {k: v for k, v in x.items() if k not in STOCK_AJOUTES}
    return codes_du_stock(ligne)[0] if pro else ligne


def photo(c: Client, pro: bool, refs: set[str], lots: set[int]) -> dict[str, Any]:
    """Stock et valorisation des matières, soldes des lots, totaux de la valorisation."""
    stock = {x["reference"]: x for x in _lignes(c.get("/api/stock")) if x["reference"] in refs}
    valo = c.get("/api/valorisation")
    lignes_valo = {x["reference"]: x for x in valo["lignes"] if x["reference"] in refs}
    soldes = c.get("/api/lots?non_nuls=false" if pro else "/api/soldes?en_stock=false")
    par_lot = {x["lot_id"]: x for x in soldes if x["lot_id"] in lots}
    totaux = {
        k: valo[k] for k in ("total_mad", "total_kg", "total_magasin_mad", "total_kg_magasin")
    }
    garder = ("quantite", "disponible", "quarantaine")
    return {
        "stock": {r: _ligne_stock(x, pro) for r, x in stock.items()},
        "valorisation": {r: {k: v for k, v in x.items() if k not in ("matiere_id", "designation")}
                         for r, x in lignes_valo.items()},
        "lots": {str(i): {k: x[k] for k in garder} for i, x in par_lot.items()},
        "totaux": totaux,
    }  # fmt: skip


def attendu_pro(avant_p: Any, avant_g: Any, apres_g: Any) -> Any:
    """PRO après le geste, s'il change ce que Gestion MP a changé : avant (PRO) + changement
    (Gestion MP) pour les nombres, la valeur de Gestion MP pour le reste. Comparé ensuite aux
    tolérances des **valeurs** (pas du changement) : l'écart d'arrondi de la reprise (K1) sur
    la valeur de départ ne compte pas deux fois."""
    if isinstance(apres_g, dict):
        a_p = avant_p if isinstance(avant_p, dict) else {}
        a_g = avant_g if isinstance(avant_g, dict) else {}
        return {k: attendu_pro(a_p.get(k), a_g.get(k), v) for k, v in apres_g.items()}
    nombres = (int, float)
    if (isinstance(apres_g, nombres) and isinstance(avant_g, nombres)
            and isinstance(avant_p, nombres) and not isinstance(apres_g, bool)):  # fmt: skip
        return avant_p + (apres_g - avant_g)
    return apres_g


def comparer_photos(
    j: Journal,
    nom: str,
    avant: tuple[dict[str, Any], dict[str, Any]],
    apres: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    """Ce que le geste a changé, de chaque côté, comparé aux tolérances des valeurs."""
    attendu = attendu_pro(avant[1], avant[0], apres[0])
    r = j.resultat(nom)
    bilan = pc.comparer(attendu, apres[1])
    r.comparees += bilan.comparees
    for chemin, g, p in bilan.ecarts:
        r.ecarts.append(Ecart(nom, chemin[0], "/".join(chemin[1:]), g, p))
