"""Les classeurs des achats : la liste des bons et leurs lignes (route 166), le plan d'achat
affiché (242) et le classeur de pilotage complet (151) — `gestion_mp/api/exports_achats.py`
(`exporter_commandes`) et `exports.py` (`exporter_pilotage`), aux conventions communes
(`exports/classeur.py`, lot D9). Lus par la direction et les achats seulement (prix compris) ;
les colonnes monétaires sont déclarées comme telles.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from gestion_mp_pro.calcul.constantes import LIBELLES_STATUT
from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, exporte_le, filtres, titre
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.commandes_fiche import BonDetaille, FiltresCommandes
from gestion_mp_pro.services.plan_achat import Plan

ONGLETS = {
    "brouillon": "Brouillons",
    "a_approuver": "À approuver",
    "envoyee": "Envoyées",
    "confirmee": "Confirmées",
    "clos": "Soldées / annulées",
    "soldee": "Soldées",
    "annulee": "Annulées",
}


def _m(titre_: str, lire: Any, format_: str = "montant") -> Colonne:
    """Une colonne monétaire."""
    return Colonne(titre_, lire, format_, monetaire=True)


COLONNES_BONS = (
    Colonne("N°", lambda b: b.resume.numero or "Brouillon"),
    Colonne("Date du bon", lambda b: b.resume.date_commande if b.resume.parti else None, "date"),
    Colonne("Fournisseur", lambda b: b.resume.fournisseur),
    Colonne("Pays", lambda b: b.resume.pays),
    Colonne("Statut", lambda b: b.resume.statut_libelle),
    Colonne("Livraison", lambda b: b.resume.livraison_libelle),
    Colonne("Lignes", lambda b: b.resume.nb_lignes, "entier"),
    Colonne("Commandé (kg)", lambda b: b.resume.quantite, "kg"),
    Colonne("Reçu (kg)", lambda b: b.resume.recu, "kg"),
    Colonne("Reste à livrer (kg)", lambda b: b.resume.reste_kg, "kg"),
    Colonne("Livré", lambda b: b.resume.part_livree, "pourcent"),
    Colonne("Devise", lambda b: b.resume.devise),
    _m("Montant confirmé", lambda b: b.resume.montant),
    _m("Montant estimé", lambda b: b.resume.montant_estime),
    _m("Montant MAD", lambda b: b.resume.montant_estime_mad),
    _m("Reste à livrer MAD", lambda b: b.resume.reste_estime_mad),
    Colonne("Prix à confirmer", lambda b: b.resume.prix_a_confirmer or None, "entier"),
    _m("Cours figé", lambda b: b.resume.cours, "cours"),
    Colonne("Livraison prévue", lambda b: b.resume.date_livraison_prevue, "date"),
    Colonne("ETA", lambda b: b.resume.expedition.eta, "date"),
    Colonne("Livrée le", lambda b: b.resume.livree_le, "date"),
    Colonne("Dernière réception", lambda b: b.resume.derniere_reception_le, "date"),
    Colonne("Retard (jours)", lambda b: b.retard_jours, "entier"),
    Colonne("Conteneur", lambda b: b.resume.expedition.conteneur),
    Colonne("Par", lambda b: b.resume.cree_par),
    Colonne("Approuvé par", lambda b: b.resume.approuvee_par),
    Colonne("Remarques au fournisseur", lambda b: b.resume.observations),
)

COLONNES_LIGNES = (
    Colonne("N°", lambda x: x[0].resume.numero or "Brouillon"),
    Colonne("Fournisseur", lambda x: x[0].resume.fournisseur),
    Colonne("Statut", lambda x: x[0].resume.statut_libelle),
    Colonne("Référence", lambda x: x[1].reference),
    Colonne("Désignation", lambda x: x[1].designation),
    Colonne("Commandé en", lambda x: x[1].unite_achat),
    Colonne("Unités", lambda x: x[1].unites, "#,##0.###"),
    Colonne("Commandé (kg)", lambda x: x[1].quantite, "kg"),
    Colonne("Reçu (kg)", lambda x: x[1].recu, "kg"),
    Colonne("En quarantaine (kg)", lambda x: x[1].en_quarantaine, "kg"),
    Colonne("Reste à livrer (kg)", lambda x: x[1].reste, "kg"),
    _m("Prix / kg", lambda x: x[1].prix_estime, "prix"),
    Colonne("Devise", lambda x: x[0].resume.devise),
    Colonne("Prix confirmé", lambda x: "oui" if x[1].prix_confirme else "non (prix du catalogue)"),
    Colonne("Confirmé par", lambda x: x[1].confirme_par),
    Colonne("Confirmé le", lambda x: x[1].confirme_le, "horodatage"),
    _m("Montant", lambda x: x[1].montant_estime),
)
"""Le prix d'une ligne est celui qui l'estime, dans la devise du bon (A-19) : prix × kg =
montant."""


def commandes(bons: Sequence[BonDetaille], f: FiltresCommandes) -> bytes:
    """Route 166 : la liste des bons telle que l'écran la montre, et leurs lignes."""
    entete = [
        exporte_le("Bons de commande", horloge.aujourd_hui()),
        filtres(
            [
                ("onglet", ONGLETS.get(f.statut, f.statut)),
                ("en retard seulement", "oui" if f.retard else ""),
                ("fournisseur", f.fournisseur_id or ""),
                ("recherche", f.q),
            ]
        ),
    ]
    lignes = [(b, x) for b in bons for x in b.lignes]
    return classeur(
        [
            Feuille("Commandes", COLONNES_BONS, bons, entete),
            Feuille("Lignes", COLONNES_LIGNES, lignes, entete),
        ],
        voit_prix=True,
    )


# ── Plan d'achat ─────────────────────────────────────────────────────────────


def _cle(nom: str) -> Any:
    """Lire une clé d'un dictionnaire."""
    return lambda x: x[nom]


COLONNES_FOURNISSEURS = (
    Colonne("Fournisseur", _cle("fournisseur")),
    Colonne("Pays", _cle("pays")),
    Colonne("Devises", lambda g: " · ".join(g["devises"])),
    Colonne("Délai (j)", _cle("delai_jours"), "entier"),
    Colonne("Références", _cle("nb_references"), "entier"),
    Colonne("Quantité (kg)", _cle("quantite"), "kg"),
    _m(
        "Montants par devise",
        lambda g: " · ".join(
            f"{v:,.0f} {d}".replace(",", " ") for d, v in sorted(g["montants_par_devise"].items())
        ),
        "",
    ),
    _m("Montant MAD", _cle("montant_mad")),
    Colonne("Part du budget", _cle("part_budget"), "pourcent"),
    Colonne("Urgence", _cle("urgence")),
    Colonne("Ruptures", _cle("ruptures"), "entier"),
    Colonne("Contact", _cle("contact")),
)

COLONNES_REFERENCES = (
    Colonne("Référence", _cle("reference")),
    Colonne("Désignation", _cle("designation")),
    Colonne("Fournisseur", _cle("fournisseur")),
    Colonne("Classe", _cle("classe_abc")),
    Colonne("Statut", lambda x: LIBELLES_STATUT.get(x["statut"], x["statut"])),
    Colonne("Disponible (kg)", _cle("stock_disponible"), "kg"),
    Colonne("Commandé (kg)", _cle("commande_kg"), "kg"),
    Colonne("Couverture (j)", _cle("couverture_jours"), "entier"),
    Colonne("À commander (kg)", _cle("quantite"), "kg"),
    Colonne(
        "Soit (ml, indicatif)",
        lambda x: x["quantite"] / x["kg_par_ml"] if x["kg_par_ml"] else None,
        "entier",
    ),
    Colonne("Unité de commande", lambda x: x["unite_commande"] or "kg"),
    Colonne("Unités", _cle("unites_commande"), "#,##0.##"),
    Colonne("Palettes", _cle("palettes"), "#,##0.##"),
    _m("Prix / kg", _cle("prix"), "prix"),
    Colonne("Devise", _cle("devise")),
    _m("Montant devise", _cle("montant_devise")),
    _m("Montant MAD", _cle("montant_mad")),
    Colonne("Priorité", _cle("tier")),
    Colonne("Action", _cle("action")),
    Colonne("Risque", _cle("risque")),
    Colonne("Déjà en préparation (kg)", _cle("en_preparation"), "kg"),
)


def plan_affiche(p: Plan, onglet: str, q: str, lignes: Sequence[dict[str, Any]]) -> bytes:
    """Route 242 : l'onglet du plan d'achat affiché (fournisseurs ou références), cherché."""
    entete = [
        titre("Plan d'achat", p.date_reference),
        f"Budget : {p.indicateurs['budget_mad']:,.0f} MAD".replace(",", " "),
        filtres([("recherche", q)]),
    ]
    if onglet == "fournisseurs":
        feuille = Feuille("Par fournisseur", COLONNES_FOURNISSEURS, lignes, entete)
    else:
        feuille = Feuille("Références à commander", COLONNES_REFERENCES, lignes, entete)
    return classeur([feuille], voit_prix=True)
