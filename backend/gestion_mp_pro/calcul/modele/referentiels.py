"""Les référentiels du moteur : réglages, fournisseurs, matières, qualités, plan, métiers.

Portage de `gestion_mp/calcul/modele.py` (CALCULS § 1.2 à § 1.8, § 1.17, § 1.18). Mêmes noms
de champs que Gestion MP (les jeux de parité figés en JSON s'y lisent tels quels) ; le
réglage « méthode » n'existe plus : seule la méthode « corrigée » est calculée (P17).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from gestion_mp_pro.calcul.constantes import ROLES_LINEAIRES


def _douze_uns() -> list[float]:
    return [1.0] * 12


@dataclass
class Parametres:
    """Les réglages que le moteur lit (cellules `P_*` du classeur et ajouts de Gestion MP)."""

    seuil_alerte: float = 90
    seuil_critique: float = 60
    delai_defaut: float = 60
    marge_securite: float = 0.20
    marge_jours: float = 30
    taux_perte: float = 0.02
    securite_a: float = 30
    securite_b: float = 30
    securite_c: float = 30
    seuil_dormant: float = 180
    seuil_abc_a: float = 0.80
    seuil_abc_b: float = 0.95
    seuil_xyz_x: float = 0.25
    seuil_xyz_y: float = 0.50
    seuil_bc_urgent: float = 300_000
    seuil_bc_groupe: float = 100_000
    seuil_tier1: float = 300_000
    seuil_tier2: float = 200_000
    seuil_tier3: float = 100_000
    toler_in_full: float = 0.02
    toler_ecart_pesee: float = 0.02
    toler_poids_bobine: float = 0.05
    seuil_hausse_forte: float = 0.05
    fenetre_realisation_jours: float = 90
    plafond_stock_min_mois: float = 3
    fenetre_prix_jours: float = 90
    cible_otif: float = 0.95
    toler_retard_jours: float = 0
    taux_tva_import: float = 0.20
    taux_tpi_import: float = 0.0025
    seuil_surcout_import: float = 1.0
    toler_facture_import: float = 0.02
    toler_tva_import: float = 0.05
    delai_frais_import_jours: float = 30
    taux_eur_mad: float = 11.0
    taux_usd_mad: float = 9.5
    devise: str = "MAD"
    dso: float = 60
    date_saisie: date | None = None
    croissance_annuelle: float = 0.0
    score_strategique: float = 85
    score_standard: float = 65
    score_surveiller: float = 45
    nom_entreprise: str = ""
    secteur: str = "Fabrication de tapis mécaniques"
    cours: dict[str, float] = field(default_factory=dict)

    def taux(self, devise: str | None) -> float:
        """Change vers le dirham : la table des devises, à défaut les deux taux du classeur ;
        toute devise inconnue vaut 1."""
        if devise and devise in self.cours:
            return self.cours[devise]
        if devise == "EUR":
            return self.taux_eur_mad
        if devise == "USD":
            return self.taux_usd_mad
        return 1.0


@dataclass
class Fournisseur:
    """Un fournisseur, par son nom (la clé du moteur)."""

    nom: str
    code: str = ""
    contact: str = ""
    telephone: str = ""
    email: str = ""
    pays: str = ""
    delai_jours: float = 0
    conditions_paiement: str = ""
    devise: str = "MAD"
    delai_paiement_jours: float = 0
    couverture_commande_jours: float = 0
    actif: bool = True


@dataclass
class Article:
    """Une matière du catalogue : l'identifiant du moteur est `reference`."""

    reference: str
    role_bom: str = ""
    nature: str = ""
    designation: str = ""
    titrage: float | str | None = None
    fournisseur: str = ""
    prix_unite: float = 0.0
    unite_prix: str = "kg"
    devise: str = "MAD"
    stock_min: float = 0.0
    couv_min_mois: float = 0.0
    poids_bobine: float = 0.0
    bob_palette: float = 0.0
    unite_commande: str = ""
    contenance_commande: float = 0.0
    minimum_commande: float = 0.0
    actif: bool = True
    densite: float = 0.0
    groupe_equiv: str = ""
    priorite_equiv: float | None = None
    composition: str = ""
    type_fil: str = ""
    couleur: str = ""
    couleur_code: str = ""
    titrage_unite: str = ""

    @property
    def contenance_palette(self) -> float:
        """Kilos par palette, 0 si le conditionnement n'est pas renseigné."""
        return (self.poids_bobine or 0.0) * (self.bob_palette or 0.0)

    @property
    def conditionnement(self) -> tuple[str, float]:
        """Unité de commande et son contenu en kilos : déclarée, sinon palette, bobine, kg."""
        if self.unite_commande and self.contenance_commande > 0:
            return self.unite_commande, self.contenance_commande
        if self.contenance_palette:
            return "Palette", self.contenance_palette
        if self.poids_bobine:
            return "Bobine", self.poids_bobine
        return "kg", 1.0

    def unites_de_commande(self) -> list[dict[str, str | float]]:
        """Les conditionnements possibles pour cette référence, kilos compris."""
        choix: list[dict[str, str | float]] = [{"unite": "kg", "contenance": 1.0}]
        if self.poids_bobine:
            choix.append({"unite": "Bobine", "contenance": self.poids_bobine})
        if self.contenance_palette:
            choix.append({"unite": "Palette", "contenance": self.contenance_palette})
        if self.unite_commande and self.contenance_commande > 0:
            choix.append({"unite": self.unite_commande, "contenance": self.contenance_commande})
        vus: dict[str | float, dict[str, str | float]] = {}
        for entree in choix:
            vus[entree["unite"]] = entree
        return list(vus.values())

    @property
    def prix_kg(self) -> float:
        """Le prix au kilo, celui de tous les calculs (au mètre : ÷ densité kg/ml)."""
        if self.unite_prix == "ml":
            return self.prix_unite / self.densite if self.densite else 0.0
        return self.prix_unite

    @property
    def kg_par_ml(self) -> float:
        """La densité d'une matière d'un rôle au mètre (cuir, franges, ruban), 0 sinon."""
        return (self.densite or 0.0) if self.role_bom in ROLES_LINEAIRES else 0.0


@dataclass
class Qualite:
    """Poids de chaque rôle pour un m² de tapis (ml/m² pour cuir, franges, ruban)."""

    code: str
    nom: str = ""
    poids: dict[str, float] = field(default_factory=dict)


@dataclass
class LigneRecette:
    """La part d'une référence dans un rôle d'une qualité (%)."""

    qualite: str
    reference: str
    pourcentage: float = 0.0


@dataclass
class PlanQualite:
    """Base mensuelle (m²) et douze coefficients de saisonnalité (janvier → décembre)."""

    qualite: str
    base_mensuelle: float = 0.0
    saisonnalite: list[float] = field(default_factory=_douze_uns)
    actif: bool = True
    depuis: date | None = None


@dataclass
class VersionPlan:
    """Le plan d'une qualité tel qu'en vigueur à partir de `quand` (vide : depuis toujours)."""

    quand: datetime | None
    base_mensuelle: float = 0.0
    saisonnalite: list[float] = field(default_factory=_douze_uns)
    actif: bool = True
    depuis: date | None = None


@dataclass
class VersionRecette:
    """La recette d'une qualité enregistrée à `quand` : (référence, %) et les poids au m²
    relevés avec elle (`None` : les versions d'avant ne les gardaient pas)."""

    quand: datetime
    lignes: list[tuple[str, float]] = field(default_factory=list)
    poids: dict[str, float] | None = None


@dataclass
class FilMonte:
    """Un fil sur un étage d'un métier : une largeur en mètres et une part du poil."""

    reference: str
    etage: int = 1
    metres: float = 0.0
    pourcentage: float = 100.0
    commentaire: str = ""
    poids_bobine: float = 0.0


@dataclass
class Metier:
    """Un métier à tisser : `laize` d'un étage, `densite` en bobines par mètre de laize."""

    code: str
    nom: str = ""
    laize: float = 0.0
    densite: float = 0.0
    etages: int = 6
    actif: bool = True
    commentaire: str = ""
    fils: list[FilMonte] = field(default_factory=list)


@dataclass
class Magasin:
    """Un magasin ; le type « Quarantaine » retient la marchandise sous réserve."""

    code: str
    nom: str = ""
    type: str = "Stock courant"
    contenu: str = "Tout"
    actif: bool = True
