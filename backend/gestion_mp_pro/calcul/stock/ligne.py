"""`LigneStock` : une matière dans `Tbl_Stock`, tous ses champs (CALCULS § 3.9).

Mêmes champs, même ordre, mêmes défauts que `gestion_mp.calcul.moteur.LigneStock`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class LigneStock:
    """L'état d'une matière à la date de référence : stock, prévision, statut, achat."""

    reference: str
    nature: str = ""
    designation: str = ""
    fournisseur: str = ""
    # Classification, reprise du catalogue.
    composition: str = ""
    type_fil: str = ""
    couleur: str = ""
    titrage: str = ""
    titrage_unite: str = ""
    # Le stock est en kilos, le prix lu au kilo ; l'unité d'achat (kg ou ml) traduit la
    # quantité à commander pour le fournisseur qui facture au mètre.
    unite_achat: str = "kg"
    quantite_a_commander_achat: float = 0.0
    prix_unite: float = 0.0
    kg_par_ml: float = 0.0
    stock_initial: float = 0.0
    entrees: float = 0.0
    stock_net: float = 0.0
    stock_machine: float = 0.0
    stock_quarantaine: float = 0.0
    stock_disponible: float = 0.0
    bc_en_cours: float = 0.0
    bc_hors_horizon: float = 0.0
    # Ce qui arrive après le délai mais avant la fin de la couverture d'une commande.
    bc_dans_couverture: float = 0.0
    # Bons en brouillon ou à approuver : pas attendus, mais déjà en préparation.
    bc_en_preparation: float = 0.0
    bons_en_preparation: list[str] = field(default_factory=list)
    sorties_prevues: float = 0.0
    # La demande pendant le délai du fournisseur, que retranche le stock projeté.
    demande_delai: float = 0.0
    stock_projete: float = 0.0
    stock_min: float = 0.0
    stock_min_recalcule: float = 0.0
    stock_min_plafonne: float = 0.0
    statut: str = ""
    statut_couverture: str = ""
    couverture_jours: float | None = None
    couverture_cible_jours: float = 0.0
    conso_mensuelle: float = 0.0
    besoin_annuel: float = 0.0
    # La prévision confrontée au réel.
    conso_plan: float = 0.0
    conso_reelle: float | None = None
    coefficient_realisation: float | None = None
    conso_horizon: float = 0.0
    realisation_heritee: list[str] = field(default_factory=list)
    delai_jours: float = 0.0
    # Pourquoi rien n'est proposé à l'achat (matière ou fournisseur désactivé, non consommée).
    sans_achat: str = ""
    quantite_a_commander: float = 0.0
    quantite_theorique: float = 0.0
    palettes_a_commander: float = 0.0
    unite_commande: str = "kg"
    contenance_commande: float = 1.0
    unites_a_commander: float = 0.0
    prix_kg: float = 0.0
    devise: str = "MAD"
    montant_a_commander: float = 0.0
    montant_a_commander_mad: float = 0.0
    valeur_conso_annuelle: float = 0.0
    valeur_conso_annuelle_mad: float = 0.0
    classe_abc: str = ""
    rang: int = 0
    pourcentage_cumule: float = 0.0
    cv_demande: float = 0.0
    classe_xyz: str = "—"
    groupe_equiv: str = ""
    sourcing: str = ""
    nb_fournisseurs_groupe: int = 0
    substituts: list[str] = field(default_factory=list)
    date_derniere_sortie: date | None = None
    jours_sans_mouvement: float | None = None
    dormant: bool = False
    par_magasin: dict[str, float] = field(default_factory=dict)
    besoins: list[float] = field(default_factory=list)
    action: str = ""
