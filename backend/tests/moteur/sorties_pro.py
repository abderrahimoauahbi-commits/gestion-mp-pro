"""Les sorties du moteur PRO sur un jeu figé, dans la forme de `essais/gestion_mp_calcul.py`.

Mêmes sections, mêmes clés : la parité unitaire compare section par section, à l'égalité
exacte. Les seules différences voulues sont ramenées ici à la forme de Gestion MP, chacune
nommée : le détail complet des contrôles (Gestion MP en gardait 200 lignes) et l'écart de
C35 envoyé en fraction (Gestion MP : en pourcent arrondi à 0,1).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from gestion_mp_pro.calcul import (
    controles,
    fournisseurs,
    importations,
    lots,
    nomenclature,
    opportunites,
    pilotage,
    plan_achat,
    prix,
    production,
    receptions,
    valorisation,
)
from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.calcul.besoins import besoins_mensuels
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.plan import plan_mensuel
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock, fils_en_machine, stock_en_machine

DETAIL_GESTION_MP = 200
"""Gestion MP coupait le détail d'un contrôle à 200 lignes (C26 : les 200 dernières)."""


def _resume(d: Donnees) -> dict[str, Any]:
    resume: dict[str, Any] = {"montage_connu": d.montage_connu}
    for nom in ("mouvements", "receptions", "historique_prix", "ordres"):
        resume[nom] = len(getattr(d, nom))
    resume["soldes"] = d.soldes is not None
    resume["commandes"] = [
        {
            "numero": c.numero,
            "statut": c.statut,
            "solde_a_la_main_le": c.solde_a_la_main_le,
            "annulee_le": c.annulee_le,
            "recu": [x.quantite_recue for x in c.lignes],
        }
        for c in d.commandes
    ]
    return resume


def revient_en_dict(r: importations.LigneRevient) -> dict[str, Any]:
    """Une ligne de revient avec ses propriétés calculées."""
    champs = {n: getattr(r, n) for n in r.__dataclass_fields__}
    for n in ("revient_mad", "revient_unite", "valeur_unite", "surcout", "decaisse_mad"):
        champs[n] = getattr(r, n)
    return champs


def _importations(d: Donnees) -> dict[str, Any]:
    p = d.parametres
    revients = {x.numero: importations.revient_dossier(x, p) for x in d.dossiers_import}
    seuil = p.seuil_surcout_import
    return {
        "revient": {n: [revient_en_dict(r) for r in rs] for n, rs in revients.items()},
        "tva_attendue": {x.numero: importations.tva_attendue(x, p) for x in d.dossiers_import},
        "ecart_facture": {x.numero: importations.ecart_facture(x, p) for x in d.dossiers_import},
        "aberrantes": {
            n: [r.ligne_id for r in importations.lignes_aberrantes(rs, seuil)]
            for n, rs in revients.items()
        },
        "negatives": {
            n: [r.ligne_id for r in importations.lignes_negatives(rs)] for n, rs in revients.items()
        },
        "revient_par_reception": {
            k: revient_en_dict(v) for k, v in importations.revient_par_reception(d).items()
        },
        "revient_par_lot": importations.revient_par_lot(d),
    }


def _stock_et_achats(d: Donnees, jour: date, lignes: list[LigneStock]) -> dict[str, Any]:
    couts = valorisation.couts_du_journal(d)
    return {
        "plan_mensuel": plan_mensuel(d, jour),
        "besoins": besoins_mensuels(d, jour),
        "nomenclature": nomenclature.nomenclature(d),
        "controle_recettes": nomenclature.controle_recettes(d),
        "fils_en_machine": fils_en_machine(d),
        "stock_en_machine": stock_en_machine(d),
        "stock": lignes,
        "plan_achat": plan_achat.plan_achat(d, lignes),
        "couts_du_journal": {
            "unitaire": couts.unitaire,
            "stock": couts.stock,
            "consommation": couts.consommation,
            "cmup": couts.cmup(),
        },
        "cmup_par_reference": valorisation.cmup_par_reference(d),
        "valorisation": valorisation.valorisation(d, lignes),
        "prix_constates": prix.prix_constates(d),
        "achats_dates": prix.achats_dates(d),
        "historique_prix": prix.historique_prix(d),
        "opportunites": {
            str(mc): opportunites.comparer_les_prix(d, lignes, meme_couleur=mc)
            for mc in (False, True)
        },
    }


def _pilotage(d: Donnees, jour: date, lignes: list[LigneStock], aujourdhui: date) -> dict[str, Any]:
    en_stock = sorted({x.reference for x in lots.stock_par_lot(d) if x.stock > 1e-3})[:15]
    lots_fournisseur = sorted({m.lot_fournisseur for m in d.mouvements if m.lot_fournisseur})[:5]
    return {
        "cout_matiere_annuel": pilotage.cout_matiere_annuel(d, jour),
        "cockpit": pilotage.cockpit(d, jour, lignes),
        "cockpit_meme_couleur": pilotage.cockpit(d, jour, lignes, meme_couleur=True),
        "performance_receptions": fournisseurs.performance_receptions(d),
        "scorecard": fournisseurs.scorecard_fournisseurs(d),
        "devises_pratiquees": fournisseurs.devises_pratiquees(d),
        "pesees": receptions.pesees(d),
        "evolution_bobines": receptions.evolution_bobines(d),
        "lots": lots.stock_par_lot(d),
        "lots_disponibles": {ref: lots.lots_disponibles(d, ref) for ref in en_stock},
        "tracabilite": {lot: lots.tracabilite(d, lot=lot) for lot in lots_fournisseur},
        "ordres": production.consommation_par_of(d),
        "realise": production.realise_par_qualite(d, jour, aujourdhui),
    }


def detail_comme_gestion_mp(code: str, detail: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Le détail PRO ramené à la forme de Gestion MP (troncature, échelle de C35)."""
    if len(detail) > DETAIL_GESTION_MP:
        detail = detail[-DETAIL_GESTION_MP:] if code == "C26" else detail[:DETAIL_GESTION_MP]
    if code != "C35":
        return detail
    rendu = []
    for ligne in detail:
        copie = dict(ligne)
        fraction = copie.pop("surcout")
        copie["surcout_pct"] = None if fraction is None else round(fraction * 100, 1)
        rendu.append(copie)
    return rendu


def _controles(
    d: Donnees, lignes: list[LigneStock], jour: date, complet: Donnees, aujourdhui: date
) -> dict[str, Any]:
    ctl = controles.controler(d, lignes, jour, complet=complet, aujourdhui=aujourdhui)
    return {
        "controles": [
            {
                "code": c.code,
                "libelle": c.libelle,
                "gravite": c.gravite,
                "anomalies": c.anomalies,
                "garanti": c.garanti,
                "detail": detail_comme_gestion_mp(c.code, c.detail),
            }
            for c in ctl
        ],
        "synthese": controles.synthese(ctl),
    }


def sorties_du_moteur(complet: Donnees, jour: date, aujourdhui: date) -> dict[str, Any]:
    """Tout ce que le moteur PRO produit sur un jeu, à sa date."""
    d = a_la_date(complet, jour, aujourdhui=aujourdhui)
    lignes = etat_stock(d, jour)
    sorties: dict[str, Any] = {"a_la_date": _resume(d)}
    sorties |= _stock_et_achats(d, jour, lignes)
    sorties |= _pilotage(d, jour, lignes, aujourdhui)
    sorties |= _importations(d)
    sorties |= _controles(d, lignes, jour, complet, aujourdhui)
    return sorties
