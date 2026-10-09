"""Le plan d'achat (route 149) et la préparation d'une commande chez un fournisseur (150) :
ce qu'il faut commander, chez qui, quand (`gestion_mp/api/pilotage.py` : `plan_achat`,
`preparation_commande` ; CALCULS A § 3.12).

Tout part du chargeur (`donnees_moteur.charger_au`) et du moteur (`calcul.plan_achat`,
`calcul.stock`) : aucune règle de calcul ici, seulement les identifiants que l'écran suit
(matière, fournisseur, bons en préparation) et ce que la ligne du stock dit déjà (disponible,
commandé, couverture, unités possibles) — une lecture au lieu de deux (ECRANS-PRO § 4.1).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.besoins import besoins_mensuels
from gestion_mp_pro.calcul.controles import controler
from gestion_mp_pro.calcul.controles.base import Controle
from gestion_mp_pro.calcul.outils import mois_du_plan
from gestion_mp_pro.calcul.plan_achat import PlanAchat
from gestion_mp_pro.calcul.plan_achat import plan_achat as calculer_plan
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from gestion_mp_pro.modeles import Commande, Fournisseur, Matiere
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import donnees_moteur, horloge, pilotage_machine


@dataclass
class BonEnPreparation:
    """Un bon pas encore parti qui porte déjà la matière (déduit de la suggestion)."""

    id: int | None
    numero: str


@dataclass
class Plan:
    """Le plan d'achat : indicateurs, fournisseurs (budget décroissant), lignes triées."""

    date_reference: date
    indicateurs: dict[str, Any]
    fournisseurs: list[dict[str, Any]]
    lignes: list[dict[str, Any]]


@dataclass
class Preparation:
    """Ce qu'il y a à commander chez un fournisseur, prêt à être arbitré."""

    fournisseur_id: int
    fournisseur: str
    pays: str
    contact: str
    email: str
    delai_jours: float
    devise_par_defaut: str
    date_reference: date
    lignes: list[dict[str, Any]] = field(default_factory=list)


def _bons(s: Session) -> dict[str, int]:
    """Numéro d'un bon pour le moteur (`BC-brouillon-{id}` sans numéro) → identifiant."""
    return {
        numero or f"BC-brouillon-{ident}": ident
        for ident, numero in s.execute(select(Commande.id, Commande.numero))
    }


def _en_preparation(numeros: list[str], bons: dict[str, int]) -> list[BonEnPreparation]:
    """Les bons en préparation, avec leur identifiant (« Brouillon » pour un bon sans numéro)."""
    return [
        BonEnPreparation(bons.get(n), "Brouillon" if n.startswith("BC-brouillon-") else n)
        for n in numeros
    ]


def _stock(ligne: LigneStock, article: c.Article | None) -> dict[str, Any]:
    """Ce que la ligne du stock ajoute à une ligne du plan."""
    return {
        "stock_disponible": ligne.stock_disponible,
        "stock_net": ligne.stock_net,
        "stock_projete": ligne.stock_projete,
        "commande_kg": ligne.bc_en_cours + ligne.bc_hors_horizon,
        "couverture_jours": ligne.couverture_jours,
        "conso_mensuelle": ligne.conso_mensuelle,
        "kg_par_ml": ligne.kg_par_ml,
        "unites_possibles": article.unites_de_commande() if article else [],
    }


def plan(s: Session, jour: date) -> Plan:
    """Route 149 : le plan d'achat au soir du `jour`."""
    d = pilotage_machine.au_soir(s, jour)
    stock = etat_stock(d, jour)
    resultat = calculer_plan(d, stock)
    par_ref = {x.reference: x for x in stock}
    matieres = dict(s.execute(select(Matiere.reference, Matiere.id)).all())
    fournisseurs = dict(s.execute(select(Fournisseur.nom, Fournisseur.id)).all())
    bons = _bons(s)
    lignes = []
    for x in resultat.lignes:
        rendu = asdict(x)
        rendu["matiere_id"] = matieres.get(x.reference)
        rendu["fournisseur_id"] = fournisseurs.get(x.fournisseur)
        rendu["bons_en_preparation"] = [
            asdict(b) for b in _en_preparation(x.bons_en_preparation, bons)
        ]
        lignes.append(rendu | _stock(par_ref[x.reference], d.article(x.reference)))
    groupes = [
        asdict(g) | {"fournisseur_id": fournisseurs.get(g.fournisseur)}
        for g in resultat.fournisseurs
    ]
    indicateurs = {k: v for k, v in asdict(resultat).items() if k not in ("fournisseurs", "lignes")}
    return Plan(jour, indicateurs, groupes, lignes)


def _depart(ligne: LigneStock, possibles: list[dict[str, str | float]]) -> dict[str, Any]:
    """L'unité de départ de la préparation : celle de commande si elle est possible, sinon la
    dernière possible ; la quantité suggérée au kilo supérieur (ECRANS-PRO § 4.4)."""
    choisie = next((u for u in possibles if u["unite"] == ligne.unite_commande), possibles[-1])
    contenance = float(choisie["contenance"]) or 1.0
    kg = float(math.ceil(ligne.quantite_a_commander - 1e-9))
    return {"unite": str(choisie["unite"]), "contenance": contenance, "quantite": kg,
            "unites": kg / contenance}  # fmt: skip


def preparation(s: Session, fournisseur_id: int, jour: date) -> Preparation:
    """Route 150 : les suggestions du calcul chez ce fournisseur (montant décroissant)."""
    f = s.get(Fournisseur, fournisseur_id)
    if f is None:
        raise Refus.introuvable("Fournisseur inconnu.")
    d = pilotage_machine.au_soir(s, jour)
    matieres = dict(s.execute(select(Matiere.reference, Matiere.id)).all())
    bons = _bons(s)
    suggerees = [
        x for x in etat_stock(d, jour) if x.fournisseur == f.nom and x.quantite_a_commander > 0
    ]
    lignes = []
    for x in sorted(suggerees, key=lambda y: -y.montant_a_commander_mad):
        a = d.article(x.reference)
        possibles: list[dict[str, str | float]] = (
            a.unites_de_commande() if a else [{"unite": "kg", "contenance": 1.0}]
        )
        lignes.append(
            {
                "matiere_id": matieres.get(x.reference),
                "reference": x.reference,
                "nature": x.nature,
                "designation": x.designation,
                "statut": x.statut,
                "classe_abc": x.classe_abc,
                "kg_par_ml": x.kg_par_ml,
                "stock_projete": x.stock_projete,
                "conso_mensuelle": x.conso_mensuelle,
                "couverture_jours": x.couverture_jours,
                "quantite_suggeree": x.quantite_a_commander,
                "palettes_suggerees": x.palettes_a_commander,
                "contenance_palette": a.contenance_palette if a else 0.0,
                "unite_commande": x.unite_commande,
                "contenance_commande": x.contenance_commande,
                "unites_suggerees": x.unites_a_commander,
                "unites_possibles": possibles,
                "minimum_commande": a.minimum_commande if a else 0.0,
                "prix_indicatif": x.prix_kg,
                "devise": x.devise,
                "montant_indicatif_mad": x.montant_a_commander_mad,
                "en_preparation": x.bc_en_preparation,
                "bons_en_preparation": [
                    asdict(b) for b in _en_preparation(x.bons_en_preparation, bons)
                ],
                "depart": _depart(x, possibles),
            }
        )
    return Preparation(
        f.id, f.nom, f.pays, f.contact, f.email, d.delai_fournisseur(f.nom), f.devise, jour, lignes
    )


# ── Classeurs : la liste affichée (242), le pilotage complet (151) ─────────────


ONGLETS_PLAN = ("fournisseurs", "references")
CHAMPS_FOURNISSEUR = ("fournisseur", "pays", "contact", "urgence")
CHAMPS_REFERENCE = ("reference", "nature", "designation", "fournisseur", "statut", "tier",
                    "risque", "action")  # fmt: skip


def _cherche(valeurs: list[object], mots: list[str]) -> bool:
    """Tous les mots, sans accents, quelque part dans la ligne (la recherche de l'écran)."""
    texte = normaliser(" ".join(str(v) for v in valeurs if v))
    return all(m in texte for m in mots)


def filtrer(p: Plan, onglet: str, q: str) -> list[dict[str, Any]]:
    """Les lignes de l'onglet affiché, cherchées comme à l'écran (ECRANS-PRO § 4.2, 4.3)."""
    if onglet not in ONGLETS_PLAN:
        raise Refus.saisie(
            f"Onglet inconnu : « {onglet} » (fournisseurs ou references).",
            code="valeur_inconnue",
            champs={"onglet": "inconnu"},
        )
    mots = normaliser(q).split()
    if onglet == "fournisseurs":
        return [
            g
            for g in p.fournisseurs
            if _cherche([*(g[k] for k in CHAMPS_FOURNISSEUR), *g["devises"]], mots)
        ]
    return [
        x
        for x in p.lignes
        if _cherche([*(x[k] for k in CHAMPS_REFERENCE), f"classe {x['classe_abc']}"], mots)
    ]


@dataclass
class Pilotage:
    """Le classeur de pilotage : stock, plan d'achat, fournisseurs, besoins, contrôles."""

    jour: date
    stock: list[LigneStock]
    plan: PlanAchat
    besoins: dict[str, list[float]]
    mois: list[date]
    controles: list[Controle]
    magasins: list[str]
    articles: dict[str, c.Article]


def pilotage(s: Session, jour: date) -> Pilotage:
    """Route 151 : les mêmes chiffres que les écrans, au même instant."""
    complet = donnees_moteur.charger(s)
    d = pilotage_machine.au_soir(s, jour)
    stock = etat_stock(d, jour)
    return Pilotage(
        jour=jour,
        stock=stock,
        plan=calculer_plan(d, stock),
        besoins=besoins_mensuels(d, jour),
        mois=mois_du_plan(jour),
        controles=controler(d, stock, jour, complet=complet, aujourdhui=horloge.aujourd_hui()),
        magasins=[g.code for g in d.magasins if g.actif],
        articles={a.reference: a for a in d.articles},
    )
