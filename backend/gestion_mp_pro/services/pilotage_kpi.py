"""Les six indicateurs du Cockpit, chacun avec sa formule (ECRANS-PRO « Cockpit — en-tête »).

L'écran affiche les valeurs reçues sans les recalculer (LOTS F1) : chaque indicateur porte sa
valeur, son unité, sa phrase de détail, sa formule (infobulle), l'écran qu'il ouvre et son ton.
Les textes suivent la règle de format (`documents/format.py`, jumeau de `format.ts`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gestion_mp_pro.documents.format import montant, nombre

FORMULES = {
    "valeur": (
        "Σ (magasins, quarantaine comprise, + sur les métiers) × coût moyen pondéré "
        "(sinon prix du catalogue × cours) — la valeur de la Valorisation"
    ),
    "couverture": (
        "Σ stock projeté positif × prix × cours ÷ consommation valorisée par jour "
        "(consommation mensuelle × prix × cours ÷ 30)"
    ),
    "a_commander": "Σ des montants à commander du plan d'achat (MAD, cours du jour)",
    "commande": (
        "Bons partis, ni soldés ni annulés, qui attendent encore de la marchandise ; reste à "
        "livrer au prix confirmé (sinon catalogue), au cours figé (sinon du jour)"
    ),
    "rotation": (
        "Coût de la consommation des 12 derniers mois clos ÷ valeur du stock au coût moyen ; "
        "sans historique : coût matière du plan ÷ stock au catalogue. Cycle de trésorerie = "
        "DIO + DSO − DPO"
    ),
    "controles": (
        "Contrôles conformes ÷ contrôles vérifiés (ceux que la base ou la saisie garantit ne "
        "comptent pas)"
    ),
}


@dataclass(frozen=True)
class Kpi:
    """Un indicateur du Cockpit."""

    cle: str
    libelle: str
    valeur: float
    unite: str
    detail: str
    formule: str
    lien: str
    ton: str


def _valeur(t: dict[str, Any]) -> Kpi:
    stock = t["stock"]
    detail = f"{stock['nb_detenues']} matière(s)"
    if stock["valeur_machine_mad"]:
        detail += f" · dont {montant(stock['valeur_machine_mad'], 'MAD')} sur les métiers"
    return Kpi(
        "valeur",
        "Valeur du stock",
        stock["valeur_mad"],
        "MAD",
        detail,
        FORMULES["valeur"],
        "/analyse?onglet=valorisation",
        "neutre",
    )


def _couverture(t: dict[str, Any]) -> Kpi:
    jours = t["stock"]["couverture_ponderee_jours"]
    return Kpi(
        "couverture",
        "Couverture pondérée",
        jours,
        "j",
        "pondérée par la valeur",
        FORMULES["couverture"],
        "/stock",
        "neutre",
    )


def _a_commander(t: dict[str, Any]) -> Kpi:
    budget = t["achats"]["budget_a_commander_mad"]
    return Kpi(
        "a_commander",
        "À commander",
        budget,
        "MAD",
        "selon le plan d'achat",
        FORMULES["a_commander"],
        "/plan-achat",
        "attention" if budget > 0 else "ok",
    )


def _commande(t: dict[str, Any]) -> Kpi:
    a = t["achats"]
    detail = f"en cours · {montant(a['montant_bc_en_cours_mad'], 'MAD')}"
    detail += f" · {a['en_retard']} en retard"
    return Kpi(
        "commande",
        "Commandé",
        a["bc_actifs"],
        "bons",
        detail,
        FORMULES["commande"],
        "/commandes?onglet=confirmee",
        "urgent" if a["en_retard"] else "neutre",
    )


def _rotation(t: dict[str, Any]) -> Kpi:
    f = t["finance"]
    base = "consommation réelle" if f["base_rotation"] == "consommation" else "plan"
    detail = f"par an ({base}) · cycle de trésorerie {nombre(f['ccc_jours'])} j"
    return Kpi(
        "rotation",
        "Rotation du stock",
        f["rotation_stock"],
        "×",
        detail,
        FORMULES["rotation"],
        "/analyse?onglet=valorisation",
        "neutre",
    )


def _controles(t: dict[str, Any]) -> Kpi:
    c = t["controles"]
    if c["bloquants"]:
        detail, ton = f"{c['bloquants']} bloquant(s) · {c['anomalies']} anomalie(s)", "critique"
    elif c["a_corriger"]:
        detail, ton = f"{c['a_corriger']} à corriger", "attention"
    else:
        detail, ton = "tout est conforme", "ok"
    detail = f"{c['conformes']} / {c['total']} · {detail}"
    return Kpi(
        "controles",
        "Contrôles",
        c["score"],
        "fraction",
        detail,
        FORMULES["controles"],
        "/analyse?onglet=controles",
        ton,
    )


def indicateurs(tableau: dict[str, Any]) -> list[Kpi]:
    """Les six indicateurs, dans l'ordre de l'écran."""
    return [
        f(tableau) for f in (_valeur, _couverture, _a_commander, _commande, _rotation, _controles)
    ]
