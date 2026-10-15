"""Le classeur de l'échéancier (route 230) : mêmes filtres que l'écran ; feuilles « Échéances »,
« À dater », « Par mois », « Réglées » (P8-21) et « Écartées » ; vraies dates, montants au
centime, une ligne de titre qui dit les filtres. La feuille « Réglées » dit en plus ce qu'elle
porte : les 300 dernières sans période, toutes celles de la période (date de règlement) sinon.
"""

from __future__ import annotations

from typing import Any

from gestion_mp_pro.documents.format import nombre
from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, filtres, titre
from gestion_mp_pro.services.echeancier import Echeancier, Filtres

NATURES = {"facture": "factures", "frais": "frais d'importation"}


def _c(titre_: str, cle: str, format_: str = "", *, monetaire: bool = False) -> Colonne:
    return Colonne(titre_, lambda x: x.get(cle), format_, monetaire=monetaire)


PIECE = [
    _c("Nature", "genre"),
    _c("Fournisseur ou prestataire", "tiers"),
    _c("Pièce", "piece"),
    _c("Montant", "montant", "montant", monetaire=True),
    _c("Devise", "devise"),
    Colonne("Estimé", lambda x: "estimé" if x.get("estime") else ""),
    _c("Montant (MAD)", "montant_mad", "montant", monetaire=True),
]
"""Les colonnes d'une pièce (la pièce en troisième colonne, comme Gestion MP)."""


def mention_reglees(e: Echeancier, f: Filtres) -> str:
    """Ce que la vue « Réglées » porte (la même phrase qu'à l'écran) : toutes celles de la
    période, ou les N dernières sans période — et comment les voir toutes."""
    n = nombre(e.reglees_total)
    if e.reglees_plafond is None:
        bornes = " ".join(
            f"{nom} {v:%d/%m/%Y}" for nom, v in (("du", f.du), ("au", f.au)) if v is not None
        )
        return f"Réglées : toutes les pièces réglées {bornes} ({n}, date de règlement)."
    p = nombre(e.reglees_plafond)
    if e.reglees_total <= e.reglees_plafond:
        return (
            f"Réglées : toutes ({n}). Au-delà de {p}, seules les {p} dernières paraissent sans "
            "période (du / au, date de règlement)."
        )
    return (
        f"Réglées : les {p} dernières sur {n}. Pour toutes les voir, poser une période "
        "(du / au) : elle s'applique à la date de règlement."
    )


def echeancier(e: Echeancier, f: Filtres) -> bytes:
    """Route 230 : l'échéancier filtré, vue par vue."""
    nature = NATURES.get(f.nature or "", "")
    entete = [
        titre("Échéancier des paiements", e.aujourdhui),
        filtres([("mots", f.q), ("nature", nature), ("du", f.du), ("au", f.au)]),
    ]
    echeances = [
        _c("Échéance", "date", "date"),
        *PIECE,
        Colonne("En retard", lambda x: "en retard" if x.get("en_retard") else ""),
    ]
    reglees = [_c("Réglée le", "payee_le", "date"), _c("Échéance", "date", "date"), *PIECE]
    ecartees = [*PIECE, _c("Réglée le", "payee_le", "date"), _c("Raison", "raison")]
    mois: list[dict[str, Any]] = [{"mois": m, "montant_mad": v} for m, v in e.par_mois.items()]
    par_mois = [_c("Mois", "mois"), _c("À payer (MAD)", "montant_mad", "montant", monetaire=True)]
    return classeur(
        [
            Feuille("Échéances", echeances, e.lignes, entete),
            Feuille("À dater", PIECE, e.a_dater, entete),
            Feuille("Par mois", par_mois, mois, entete),
            Feuille("Réglées", reglees, e.reglees, [*entete, mention_reglees(e, f)]),
            Feuille("Écartées", ecartees, e.ecartees, entete),
        ],
        voit_prix=True,
    )
