"""Le classeur de pilotage complet (route 151) : le stock par matière, le plan d'achat, les
fournisseurs, les besoins mois par mois et les contrôles, au même instant que les écrans
(`gestion_mp/api/exports.py` : `exporter_pilotage`). Direction et achats seulement.
"""

from __future__ import annotations

from typing import Any

from gestion_mp_pro.calcul.constantes import LIBELLES_STATUT
from gestion_mp_pro.calcul.controles.base import Controle
from gestion_mp_pro.calcul.plan_achat import GroupeFournisseur, LignePlanAchat
from gestion_mp_pro.calcul.stock import LigneStock
from gestion_mp_pro.exports.classeur import GRAVITES, Colonne, Feuille, classeur, titre
from gestion_mp_pro.services.plan_achat import Pilotage


def _a(nom: str, format_: str = "", *, monetaire: bool = False, titre_: str = "") -> Colonne:
    """Une colonne qui lit un attribut."""
    return Colonne(titre_ or nom, lambda x: getattr(x, nom), format_, monetaire=monetaire)


def _statut() -> Colonne:
    """Le statut d'une matière en clair (le moteur rend un code, RESTES3)."""
    return Colonne("Statut", lambda x: LIBELLES_STATUT.get(x.statut, x.statut))


def _stock(p: Pilotage) -> Feuille:
    """Feuille « Stock » : une ligne par matière."""

    def role(x: LigneStock) -> str:
        """Le rôle de nomenclature de la matière."""
        a = p.articles.get(x.reference)
        return a.role_bom if a else ""

    colonnes = [
        _a("reference", titre_="Référence"), _a("designation", titre_="Désignation"),
        Colonne("Rôle", role), _a("fournisseur", titre_="Fournisseur"),
        _statut(), _a("stock_net", "kg", titre_="Stock net"),
        _a("stock_machine", "kg", titre_="Sur les métiers"),
        _a("stock_quarantaine", "kg", titre_="Quarantaine"),
        _a("stock_disponible", "kg", titre_="Disponible"),
        _a("bc_en_cours", "kg", titre_="Commandé dans le délai"),
        _a("bc_hors_horizon", "kg", titre_="Commandé au-delà du délai"),
        _a("sorties_prevues", "kg", titre_="Sorties prévues"),
        _a("stock_projete", "kg", titre_="Stock projeté"),
        _a("stock_min_plafonne", "kg", titre_="Stock minimum"),
        _a("stock_min_recalcule", "kg", titre_="Seuil d'alerte"),
        _a("conso_mensuelle", "kg", titre_="Conso / mois"),
        _a("couverture_jours", "entier", titre_="Couverture (j)"),
        _a("delai_jours", "entier", titre_="Délai (j)"),
        _a("quantite_a_commander", "kg", titre_="À commander"),
        _a("prix_kg", "prix", monetaire=True, titre_="Prix / kg"), _a("devise", titre_="Devise"),
        _a("montant_a_commander_mad", "montant", monetaire=True, titre_="Montant MAD"),
        _a("classe_abc", titre_="Classe ABC"), _a("classe_xyz", titre_="Classe XYZ"),
        _a("date_derniere_sortie", "date", titre_="Dernière sortie"),
        *[Colonne(f"Magasin {g}", lambda x, g=g: x.par_magasin.get(g, 0.0), "kg")
          for g in p.magasins],
    ]  # fmt: skip
    return Feuille("Stock", colonnes, p.stock, [titre("Pilotage des matières premières", p.jour)])


def _plan(p: Pilotage) -> Feuille:
    """Feuille « Plan d'achat »."""

    def metres(x: LignePlanAchat) -> float | None:
        """Les mètres indicatifs d'un cuir, de franges, d'un ruban."""
        a = p.articles.get(x.reference)
        return x.quantite / a.densite if a and a.densite else None

    colonnes = [
        _a("reference", titre_="Référence"), _a("fournisseur", titre_="Fournisseur"),
        _a("classe_abc", titre_="Classe"), _statut(),
        _a("quantite", "kg", titre_="Quantité (kg)"),
        Colonne("Soit (ml, indicatif)", metres, "entier"),
        Colonne("Unité de commande", lambda x: x.unite_commande or "kg"),
        _a("unites_commande", "#,##0.##", titre_="Unités"),
        _a("prix", "prix", monetaire=True, titre_="Prix / kg"), _a("devise", titre_="Devise"),
        _a("montant_devise", "montant", monetaire=True, titre_="Montant devise"),
        _a("montant_mad", "montant", monetaire=True, titre_="Montant MAD"),
        _a("palettes", "#,##0.##", titre_="Palettes"), _a("tier", titre_="Priorité"),
        _a("risque", titre_="Risque"), _a("action", titre_="Action"),
        _a("relance", titre_="Relance"),
    ]  # fmt: skip
    budget = f"Budget : {p.plan.budget_mad:,.0f} MAD".replace(",", " ")
    entete = [titre("Pilotage des matières premières", p.jour), budget]
    return Feuille("Plan d'achat", colonnes, p.plan.lignes, entete)


def _fournisseurs(p: Pilotage) -> Feuille:
    """Feuille « Par fournisseur »."""

    def montants(g: GroupeFournisseur) -> str:
        """Les montants par devise, jamais additionnés."""
        return " · ".join(
            f"{v:,.0f} {d}".replace(",", " ") for d, v in sorted(g.montants_par_devise.items())
        )

    colonnes = [
        _a("fournisseur", titre_="Fournisseur"), _a("pays", titre_="Pays"),
        Colonne("Devises", lambda g: " · ".join(g.devises)),
        _a("delai_jours", "entier", titre_="Délai (j)"),
        _a("nb_references", "entier", titre_="Références"),
        _a("quantite", "kg", titre_="Quantité (kg)"),
        Colonne("Montants par devise", montants, monetaire=True),
        _a("montant_mad", "montant", monetaire=True, titre_="Montant MAD"),
        _a("part_budget", "pourcent", titre_="Part du budget"), _a("urgence", titre_="Urgence"),
        _a("ruptures", "entier", titre_="Ruptures"), _a("contact", titre_="Contact"),
    ]  # fmt: skip
    entete = [titre("Pilotage des matières premières", p.jour)]
    return Feuille("Par fournisseur", colonnes, p.plan.fournisseurs, entete)


def _besoins(p: Pilotage) -> Feuille:
    """Feuille « Besoins » : kilos à consommer selon le plan, mois par mois."""

    def info(reference: str, attribut: str) -> Any:
        """Un attribut de la matière (vide si inconnue)."""
        a = p.articles.get(reference)
        return getattr(a, attribut) if a else ""

    lignes = sorted(p.besoins.items())
    colonnes = [
        Colonne("Référence", lambda x: x[0]),
        Colonne("Rôle", lambda x: info(x[0], "role_bom")),
        Colonne("Fournisseur", lambda x: info(x[0], "fournisseur")),
        *[Colonne(f"{fin:%m/%Y}", lambda x, i=i: x[1][i], "kg") for i, fin in enumerate(p.mois)],
        Colonne("Total", lambda x: sum(x[1]), "kg"),
    ]
    entete = [
        titre("Pilotage des matières premières", p.jour),
        "Kilos à consommer selon le plan de production, mois par mois.",
    ]
    return Feuille("Besoins", colonnes, lignes, entete)


def _etat(c: Controle) -> str:
    """« garanti », « conforme » ou « à corriger »."""
    if c.garanti:
        return "garanti"
    return "conforme" if c.conforme else "à corriger"


def _controles(p: Pilotage) -> Feuille:
    """Feuille « Contrôles » : un contrôle garanti n'est pas « conforme » (E-12)."""
    colonnes = [
        _a("code", titre_="Code"), _a("libelle", titre_="Contrôle"),
        _a("anomalies", "entier", titre_="Anomalies"),
        Colonne("Gravité", lambda c: GRAVITES.get(c.gravite, c.gravite)),
        Colonne("État", _etat),
    ]  # fmt: skip
    return Feuille(
        "Contrôles", colonnes, p.controles, [titre("Pilotage des matières premières", p.jour)]
    )


def pilotage(p: Pilotage) -> bytes:
    """Le classeur complet (cinq feuilles)."""
    feuilles = [_stock(p), _plan(p), _fournisseurs(p), _besoins(p), _controles(p)]
    return classeur(feuilles, voit_prix=True)
