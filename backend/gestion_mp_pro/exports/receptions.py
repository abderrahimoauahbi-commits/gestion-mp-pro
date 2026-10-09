"""Les classeurs des réceptions (routes 178–180 ; `gestion_mp/api/exports_achats.py`), aux
conventions communes (`exports/classeur.py`, lot D9) : la liste et ses lignes pesées, l'archive
des pesées (et ses tolérances), le poids des bobines (par matière et chaque mesure). Mêmes
filtres que l'écran ; lus par la direction et les achats (colonnes monétaires déclarées).
"""

from __future__ import annotations

from typing import Any

from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, exporte_le, filtres
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.receptions_lecture import FiltresReceptions, LigneLue, ReceptionResume
from gestion_mp_pro.services.receptions_pesees import (
    EvolutionBobines,
    FiltresBobines,
    FiltresPesees,
    Pesees,
)

STATUTS = {"brouillon": "Brouillons", "validee": "Validées", "annulee": "Annulées"}


def _m(titre: str, lire: Any, format_: str = "montant") -> Colonne:
    """Une colonne monétaire."""
    return Colonne(titre, lire, format_, monetaire=True)


def _facture(r: ReceptionResume, champ: str) -> object:
    return getattr(r.facture, champ) if r.facture is not None else None


def _bons(r: ReceptionResume) -> str:
    return ", ".join(b.numero for b in r.commandes) or "hors commande"


def _reste(x: LigneLue) -> object:
    return x.quantite_attendue if x.commande_ligne_id else None


COLONNES_RECEPTIONS = (
    Colonne("N°", lambda r: r.numero or "Brouillon"),
    Colonne("Arrivée", lambda r: r.date, "date"),
    Colonne("Fournisseur", lambda r: r.fournisseur),
    Colonne(
        "Bons de commande", lambda r: ", ".join(b.numero for b in r.commandes) or "hors commande"
    ),
    Colonne("N° du BL", lambda r: r.numero_bl),
    Colonne("Facture", lambda r: _facture(r, "numero") or ""),
    Colonne("Date facture", lambda r: _facture(r, "date"), "date"),
    _m("Montant facture", lambda r: _facture(r, "montant")),
    Colonne("Devise", lambda r: r.devise),
    Colonne("Échéance", lambda r: _facture(r, "echeance"), "date"),
    Colonne("Lignes", lambda r: r.nb_lignes, "entier"),
    Colonne("Pesé (kg)", lambda r: r.pese, "kg"),
    Colonne("Statut", lambda r: r.statut_libelle),
    Colonne("Par", lambda r: r.cree_par),
    Colonne("Contrôlé par", lambda r: r.controle_par),
    Colonne("Validée par", lambda r: r.validee_par),
    Colonne("Motif d'annulation", lambda r: r.annulation_motif),
    Colonne("Observations", lambda r: r.observations),
)

COLONNES_LIGNES = (
    Colonne("N°", lambda x: x[0].numero or "Brouillon"),
    Colonne("Arrivée", lambda x: x[0].date, "date"),
    Colonne("Fournisseur", lambda x: x[0].fournisseur),
    Colonne("Bon de commande", lambda x: x[1].commande or "hors commande"),
    Colonne("Référence", lambda x: x[1].reference),
    Colonne("Lot", lambda x: x[1].lot_numero or ("lot interne" if x[1].lot_interne else "")),
    Colonne("Reste à livrer (kg)", lambda x: _reste(x[1]), "kg"),
    Colonne("Annoncé BL (kg)", lambda x: x[1].quantite_bl or None, "kg"),
    Colonne("Pesé (kg)", lambda x: x[1].quantite_pesee, "kg"),
    Colonne("Écart (kg)", lambda x: x[1].ecart, "kg"),
    Colonne("Écart (%)", lambda x: x[1].ecart_relatif, "pourcent"),
    Colonne("Palettes", lambda x: x[1].nb_palettes or None, "#,##0.###"),
    Colonne("Bobines", lambda x: x[1].nb_bobines or None, "entier"),
    Colonne("kg / bobine", lambda x: x[1].poids_moyen_bobine, "#,##0.000"),
    Colonne("Magasin", lambda x: x[1].magasin),
    Colonne("Qualité", lambda x: x[1].qualite_libelle),
    _m("Prix / kg", lambda x: x[1].prix or None, "prix"),
    Colonne("Devise", lambda x: x[0].devise),
    Colonne("Observations", lambda x: x[1].observations),
)  # fmt: skip


def receptions(detail: list[tuple[ReceptionResume, list[LigneLue]]], f: FiltresReceptions) -> bytes:
    """Route 178 : feuilles « Réceptions » et « Lignes »."""
    entete = [
        exporte_le("Réceptions", horloge.aujourd_hui()),
        filtres(
            [("onglet", STATUTS.get(f.statut, "")), ("recherche", f.q), ("du", f.du),
             ("au", f.au)]
        ),
    ]  # fmt: skip
    resumes = [r for r, _ in detail]
    lignes = [(r, x) for r, xs in detail for x in xs]
    return classeur(
        [
            Feuille("Réceptions", COLONNES_RECEPTIONS, resumes, entete),
            Feuille("Lignes", COLONNES_LIGNES, lignes, entete),
        ],
        voit_prix=True,
    )


COLONNES_PESEES = (
    Colonne("Réception", lambda p: p.numero),
    Colonne("Arrivée", lambda p: p.date, "date"),
    Colonne("Statut", lambda p: "Brouillon" if p.statut_reception == "brouillon" else "Validée"),
    Colonne("Bon de commande", lambda p: p.numero_bc or "hors commande"),
    Colonne("Fournisseur", lambda p: p.fournisseur),
    Colonne("Référence", lambda p: p.reference),
    Colonne("Désignation", lambda p: p.designation),
    Colonne("Lot", lambda p: p.lot),
    Colonne("Magasin", lambda p: p.magasin),
    Colonne("BL (kg)", lambda p: p.quantite_bl or None, "kg"),
    Colonne("Attendu : BL, sinon reste (kg)", lambda p: p.quantite_bl or p.quantite_attendue, "kg"),
    Colonne("Pesé (kg)", lambda p: p.quantite_pesee, "kg"),
    Colonne("Écart (kg)", lambda p: p.ecart, "kg"),
    Colonne("Écart", lambda p: p.ecart_relatif, "pourcent"),
    Colonne("Hors tolérance", lambda p: p.hors_tolerance),
    Colonne("Palettes", lambda p: p.nb_palettes or None, "#,##0.###"),
    Colonne("Bobines", lambda p: p.nb_bobines or None, "entier"),
    Colonne("kg / bobine", lambda p: p.poids_moyen_bobine, "#,##0.000"),
    Colonne("kg / bobine au catalogue", lambda p: p.poids_bobine_catalogue or None, "#,##0.000"),
    Colonne("Écart bobine", lambda p: p.ecart_bobine, "pourcent"),
    Colonne("Qualité", lambda p: p.qualite_libelle),
    Colonne("Observations", lambda p: p.observations),
)  # fmt: skip


def pesees(tout: Pesees, f: FiltresPesees) -> bytes:
    """Route 179 : la feuille « Pesées » et la ligne des tolérances (A-20 : BL et attendu)."""
    entete = [
        exporte_le("Archive des pesées", horloge.aujourd_hui()),
        filtres([("écarts seulement", "oui" if f.ecarts else ""), ("recherche", f.q),
                 ("qualité", f.qualite)]),
        f"Tolérance de pesée ±{tout.tolerance:.0%} · tolérance de bobine "
        f"±{tout.tolerance_bobine:.0%}",
    ]  # fmt: skip
    return classeur([Feuille("Pesées", COLONNES_PESEES, tout.lignes, entete)], voit_prix=True)


COLONNES_BOBINES = (
    Colonne("Référence", lambda x: x.reference),
    Colonne("Fournisseur", lambda x: x.fournisseur),
    Colonne("kg / bobine au catalogue", lambda x: x.poids_catalogue or None, "#,##0.000"),
    Colonne("Réceptions", lambda x: x.receptions, "entier"),
    Colonne("Premier", lambda x: x.premier, "#,##0.000"),
    Colonne("Dernier", lambda x: x.dernier, "#,##0.000"),
    Colonne("Dernière pesée", lambda x: x.derniere_date, "date"),
    Colonne("Évolution", lambda x: x.evolution, "pourcent"),
    Colonne("Moyenne", lambda x: x.moyenne, "#,##0.000"),
    Colonne("Mini", lambda x: x.mini, "#,##0.000"),
    Colonne("Maxi", lambda x: x.maxi, "#,##0.000"),
    Colonne("Écart au catalogue", lambda x: x.ecart_catalogue, "pourcent"),
    Colonne("Hors tolérance", lambda x: x.hors_tolerance),
)

COLONNES_MESURES = (
    Colonne("Référence", lambda x: x[0].reference),
    Colonne("Date", lambda x: x[1].date, "date"),
    Colonne("Réception", lambda x: x[1].reception),
    Colonne("Fournisseur", lambda x: x[1].fournisseur),
    Colonne("Lot", lambda x: x[1].lot),
    Colonne("Pesé (kg)", lambda x: x[1].quantite_pesee, "kg"),
    Colonne("Bobines", lambda x: x[1].nb_bobines, "entier"),
    Colonne("kg / bobine", lambda x: x[1].poids_bobine, "#,##0.000"),
    Colonne("Écart au catalogue", lambda x: x[1].ecart_catalogue, "pourcent"),
)


def bobines(tout: EvolutionBobines, f: FiltresBobines) -> bytes:
    """Route 180 : feuilles « Par matière » et « Mesures »."""
    entete = [
        exporte_le("Poids des bobines", horloge.aujourd_hui()),
        filtres([("écarts au catalogue seulement", "oui" if f.ecarts else ""), ("recherche", f.q)]),
        f"Tolérance au catalogue ±{tout.tolerance:.0%}",
    ]
    mesures = [(x, m) for x in tout.lignes for m in x.historique]
    return classeur(
        [
            Feuille("Par matière", COLONNES_BOBINES, tout.lignes, entete),
            Feuille("Mesures", COLONNES_MESURES, mesures, entete),
        ],
        voit_prix=True,
    )
