"""Production et besoins, en lecture (routes 145, 147, 148 ; Gestion MP `api/production_plan.py`).

- Plan de production (145) : chaque qualité, sa saisie, son plan glissant sur douze mois, ce
  qu'elle consomme au m² (perte comprise), ce qui est tissé ce mois-ci ; « tissé hors plan » :
  les qualités tissées ce mois-ci dont le plan du mois est nul (D-17) ; le total annuel est la
  saisie (base × saisonnalité), **hors croissance**, et nul pour une qualité arrêtée.
- Plan et réalisé (147) : douze mois écoulés, chaque mois clos jugé sur le plan **en vigueur
  pendant ce mois** (`plan_version`) ; le réalisé vient des ordres validés (lot D6).
- Besoins détaillés (148) : le MRP par matière et par mois, ce qui le tire (qualités) et ce
  que le plan d'achat en retient, **à la date** (stock, commandes et sorties de ce jour-là).
  L'alimentation ne reçoit pas le conseil d'achat (E-01).

Mêmes données que Gestion MP : `charger` pour 145 et 147, `charger_au` pour 148 (parité).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.besoins import besoins_mensuels
from gestion_mp_pro.calcul.nomenclature import controle_recettes, kg_par_m2
from gestion_mp_pro.calcul.outils import mois_du_plan
from gestion_mp_pro.calcul.plan import plan_mensuel
from gestion_mp_pro.calcul.production import realise_par_qualite
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from gestion_mp_pro.modeles import Matiere, Qualite, RoleNomenclature
from gestion_mp_pro.services import donnees_moteur, horloge
from gestion_mp_pro.services.qualites_lecture import _saisons

MOIS = 12
CONSEIL_D_ACHAT = ("quantite_a_commander", "quantite_a_commander_achat")
"""Ce que l'alimentation ne reçoit pas des besoins détaillés (E-01)."""


def _par_qualite(d: c.Donnees) -> tuple[dict[str, float], dict[str, int]]:
    """kg/m² (perte comprise) et nombre de lignes de la recette de chaque qualité."""
    perte = 1 + d.parametres.taux_perte
    kg: dict[str, float] = defaultdict(float)
    lignes: dict[str, int] = defaultdict(int)
    for r in d.recettes:
        lignes[r.qualite] += 1
        if r.reference:
            kg[r.qualite] += kg_par_m2(d, r.qualite, r.reference, r.pourcentage) * perte
    return kg, lignes


def _ligne_plan(
    q: Qualite,
    coefficients: list[float],
    glissant: list[float],
    calculs: tuple[dict[str, float], dict[str, int], dict[str, bool], dict[str, float]],
) -> dict[str, Any]:
    """Une qualité du plan de production."""
    kg, lignes, conformes, tisse = calculs
    base = float(q.base_mensuelle)
    return {
        "id": q.id, "code": q.code, "nom": q.nom, "actif": q.actif, "version": q.version,
        "base_mensuelle": q.base_mensuelle, "saisonnalite": coefficients,
        "total_annuel": sum(base * k for k in coefficients) if q.actif else 0.0,
        "glissant": glissant, "total_glissant": sum(glissant),
        "kg_m2": kg.get(q.code, 0.0), "lignes_recette": lignes.get(q.code, 0),
        "recette_conforme": conformes.get(q.code, True),
        "tisse_mois_en_cours": tisse.get(q.code, 0.0),
    }  # fmt: skip


def plan(s: Session, jour: date) -> dict[str, Any]:
    """Route 145 : le plan de toutes les qualités à la date de référence."""
    d = donnees_moteur.charger(s)
    glissant = plan_mensuel(d, jour)
    realise = realise_par_qualite(d, jour, horloge.aujourd_hui())
    tisse = {x.qualite: x.realise[-1] for x in realise.lignes}
    kg, lignes = _par_qualite(d)
    conformes = {x.qualite: x.conforme for x in controle_recettes(d)}
    saisons = _saisons(s)
    qualites = list(s.scalars(select(Qualite).order_by(Qualite.code)))
    ids = {q.code: q.id for q in qualites}
    hors_plan = sorted(x.qualite for x in realise.lignes if not glissant.get(x.qualite, [0.0])[0])
    return {
        "date_reference": jour,
        "mois": mois_du_plan(jour),
        "croissance_annuelle": d.parametres.croissance_annuelle,
        "taux_perte": d.parametres.taux_perte,
        "qualites": [
            _ligne_plan(
                q,
                saisons.get(q.id, [1.0] * MOIS),
                glissant.get(q.code, [0.0] * MOIS),
                (kg, lignes, conformes, tisse),
            )
            for q in qualites
        ],
        "tisse_hors_plan": [
            {"qualite_id": ids.get(code), "qualite": code, "m2": tisse[code]}
            for code in hors_plan
            if tisse[code]
        ],
    }


def realise(s: Session, jour: date) -> dict[str, Any]:
    """Route 147 : le plan face au réalisé, chaque mois clos jugé sur le plan de son époque."""
    d = donnees_moteur.charger(s)
    r = realise_par_qualite(d, jour, horloge.aujourd_hui())
    ids = dict(s.execute(select(Qualite.code, Qualite.id)).all())
    rendu = asdict(r)
    for ligne in rendu["lignes"]:
        ligne["qualite_id"] = ids.get(ligne["qualite"])
    return {**rendu, "date_reference": jour, "plan_fige": True}


def _detail_par_qualite(
    d: c.Donnees, plan_glissant: dict[str, list[float]], ids: dict[str, int]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Pour chaque matière : les qualités qui tirent son besoin, kg/m² et kg par mois."""
    perte = 1 + d.parametres.taux_perte
    detail: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for r in d.recettes:
        m2 = plan_glissant.get(r.qualite)
        if not r.reference or m2 is None:
            continue
        kg = kg_par_m2(d, r.qualite, r.reference, r.pourcentage)
        if not kg:
            continue
        x = detail[r.reference].setdefault(
            r.qualite,
            {"qualite_id": ids.get(r.qualite), "qualite": r.qualite, "kg_m2": 0.0,
             "kg": [0.0] * MOIS},
        )  # fmt: skip
        x["kg_m2"] += kg * perte
        for i in range(MOIS):
            x["kg"][i] += kg * m2[i] * perte
    return detail


def _ligne_besoin(
    reference: str, valeurs: list[float], d: c.Donnees, ligne: LigneStock | None
) -> dict[str, Any]:
    """Une matière des besoins détaillés (sans ses qualités)."""
    a = d.article(reference)
    retenu = list(ligne.besoins) if ligne and ligne.besoins else list(valeurs)
    return {
        "reference": reference,
        "nature": a.nature if a else "", "designation": a.designation if a else "",
        "fournisseur": a.fournisseur if a else "", "role": a.role_bom if a else "",
        "kg_par_ml": a.kg_par_ml if a else 0.0,
        "kg": valeurs, "total": sum(valeurs), "retenu": retenu, "total_retenu": sum(retenu),
        "coefficient_realisation": ligne.coefficient_realisation if ligne else None,
        "conso_reelle": ligne.conso_reelle if ligne else None,
        "stock_disponible": ligne.stock_disponible if ligne else 0.0,
        "bc_en_cours": ligne.bc_en_cours if ligne else 0.0,
        "stock_projete": ligne.stock_projete if ligne else 0.0,
        "couverture_jours": ligne.couverture_jours if ligne else None,
        "statut": ligne.statut if ligne else "",
        "quantite_a_commander": ligne.quantite_a_commander if ligne else 0.0,
        "unite_achat": ligne.unite_achat if ligne else "kg",
        "quantite_a_commander_achat": ligne.quantite_a_commander_achat if ligne else 0.0,
    }  # fmt: skip


def besoins(
    s: Session, jour: date, conseil: bool = True, matiere_id: int | None = None
) -> dict[str, Any]:
    """Route 148 : le MRP détaillé à la date ; `matiere_id` : une seule matière."""
    d = donnees_moteur.charger_au(s, jour)
    stock = {x.reference: x for x in etat_stock(d, jour)}
    matieres = dict(s.execute(select(Matiere.reference, Matiere.id)).all())
    ids = dict(s.execute(select(Qualite.code, Qualite.id)).all())
    detail = _detail_par_qualite(d, plan_mensuel(d, jour), ids)
    lignes = []
    for reference, valeurs in sorted(besoins_mensuels(d, jour).items()):
        if matiere_id is not None and matieres.get(reference) != matiere_id:
            continue
        ligne = _ligne_besoin(reference, valeurs, d, stock.get(reference))
        qualites = [{**x, "total": sum(x["kg"])} for x in detail.get(reference, {}).values()]
        qualites.sort(key=lambda x: -x["total"])
        ligne |= {"matiere_id": matieres.get(reference), "qualites": qualites}
        if not conseil:
            ligne |= dict.fromkeys(CONSEIL_D_ACHAT)
        lignes.append(ligne)
    roles = s.scalars(
        select(RoleNomenclature.code).order_by(RoleNomenclature.ordre, RoleNomenclature.code)
    )
    return {
        "date_reference": jour,
        "mois": mois_du_plan(jour),
        "taux_perte": d.parametres.taux_perte,
        "fenetre_realisation_jours": d.parametres.fenetre_realisation_jours,
        "roles": list(roles),
        "lignes": lignes,
    }
