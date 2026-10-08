"""Le Cockpit : ses blocs (mêmes clés que le dict de Gestion MP) et la valeur du stock détenu.

Le stock détenu (magasins, quarantaine comprise, et métiers) vaut ce qu'il a coûté — le CMUP
de la Valorisation, replis compris — et non le prix du catalogue : deux pages, un chiffre.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gestion_mp_pro.calcul.constantes import JOURS_PAR_MOIS
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.opportunites import Opportunite
from gestion_mp_pro.calcul.stock import LigneStock
from gestion_mp_pro.calcul.valorisation import CoutsDuJournal, cmup_par_reference


@dataclass
class StockCockpit:
    """Bloc « stock »."""

    valeur_mad: float
    valeur_machine_mad: float
    nb_references: int
    nb_detenues: int
    nb_sur_metiers: int
    couverture_ponderee_jours: float
    ruptures: int
    critiques: int
    urgents: int
    attentions: int
    ok: int
    sans_consommation: int


@dataclass
class AchatsCockpit:
    """Bloc « achats »."""

    bc_actifs: int
    montant_bc_en_cours_mad: float
    montant_bc_estime_mad: float
    fournisseurs_actifs: int
    budget_a_commander_mad: float


@dataclass
class FinanceCockpit:
    """Bloc « finance » : coût matière, rotation, DIO, DSO, DPO, cycle de trésorerie."""

    cout_matiere_annuel_mad: float
    cout_matiere_mensuel_mad: float
    rotation_stock: float
    dio_jours: float
    cout_rotation_annuel_mad: float
    base_rotation: str
    dso_jours: float
    dpo_jours: float
    ccc_jours: float


@dataclass
class DormantCockpit:
    """Bloc « dormant »."""

    nb_references: int
    valeur_mad: float
    part_valeur: float
    seuil_jours: float


@dataclass
class EconomiesCockpit:
    """Bloc « économies » : le total, le nombre et les cinq premières pistes."""

    total_mad: float
    nb_opportunites: int
    top: list[Opportunite] = field(default_factory=list)


@dataclass
class AlerteCockpit:
    """Une matière en alerte, telle que le Cockpit la liste."""

    reference: str
    nature: str
    designation: str
    fournisseur: str
    stock: float
    conso_mensuelle: float
    couverture_jours: float | None
    delai_jours: float
    quantite_a_commander: float
    statut: str
    statut_couverture: str
    action: str
    titrage: str
    kg_par_ml: float
    stock_machine: float


@dataclass
class ExpositionDevise:
    """La part d'une devise dans le budget d'achat à émettre."""

    devise: str
    references: int
    montant_mad: float
    part: float


@dataclass
class Cockpit:
    """La vue 🚨 Cockpit."""

    date_reference: str
    stock: StockCockpit
    achats: AchatsCockpit
    finance: FinanceCockpit
    abc: dict[str, int]
    dormant: DormantCockpit
    sourcing: dict[str, int]
    economies: EconomiesCockpit
    nb_alertes: int
    alertes: list[AlerteCockpit]
    devises: list[ExpositionDevise]


@dataclass
class Valeurs:
    """Les valeurs du stock que le Cockpit additionne."""

    stock: float
    stock_catalogue: float
    machine: float
    nb_detenues: int
    couverture_ponderee: float
    dormante: float
    nb_dormantes: int


def valeurs_du_stock(
    donnees: Donnees, lignes: list[LigneStock], journal: CoutsDuJournal
) -> Valeurs:
    """Le stock détenu au CMUP (et au catalogue), la machine, la part dormante, la
    couverture pondérée (stock projeté valorisé ÷ consommation valorisée)."""
    taux = donnees.parametres.taux
    cout = cmup_par_reference(donnees, journal.cmup())

    def _detenu(x: LigneStock) -> float:
        return x.stock_disponible + x.stock_quarantaine

    def _catalogue(x: LigneStock) -> float:
        return x.prix_kg * taux(x.devise)

    def _unitaire(x: LigneStock) -> float:
        return cout.get(x.reference, _catalogue(x))

    physique = [x for x in lignes if _detenu(x) > 0]
    conso_valorisee = sum(x.conso_mensuelle * x.prix_kg * taux(x.devise) for x in lignes)
    stock_valorise = sum(
        x.stock_projete * x.prix_kg * taux(x.devise) for x in lignes if x.stock_projete > 0
    )
    dormantes = [x for x in lignes if x.dormant]
    return Valeurs(
        stock=sum(_detenu(x) * _unitaire(x) for x in physique),
        stock_catalogue=sum(_detenu(x) * _catalogue(x) for x in physique),
        machine=sum(x.stock_machine * _unitaire(x) for x in lignes if x.stock_machine > 0),
        nb_detenues=len(physique),
        couverture_ponderee=(
            stock_valorise / (conso_valorisee / JOURS_PAR_MOIS) if conso_valorisee else 0.0
        ),
        dormante=sum(_detenu(x) * _unitaire(x) for x in dormantes if _detenu(x) > 0),
        nb_dormantes=len(dormantes),
    )
