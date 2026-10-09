"""Schémas de l'archive des pesées (route 176) et du poids des bobines (177)."""

from __future__ import annotations

import datetime as dt

from pydantic import Field

from gestion_mp_pro.api.communs import Nombre, Page, Sortie


class Pesee(Sortie):
    """Une ligne pesée : annoncé (BL seul), pesé, écart et à quoi il se compare, bobines."""

    id: int
    reception_id: int
    numero: str
    date: dt.date
    statut_reception: str
    commande_id: int | None
    numero_bc: str
    fournisseur_id: int
    fournisseur: str
    receptionnaire: str
    controleur_qualite: str
    matiere_id: int
    reference: str
    designation: str
    lot_id: int | None
    lot: str
    magasin: str
    quantite_bl: Nombre = Field(description="le BL seul (0 sans BL)")
    quantite_attendue: Nombre = Field(description="le reste à livrer (kg)")
    quantite_pesee: Nombre
    ecart: float | None
    ecart_relatif: float | None
    compare_au: str | None = Field(description="« bl », « reste », ou null sans écart")
    hors_tolerance: bool
    nb_palettes: Nombre
    nb_bobines: Nombre
    poids_moyen_bobine: float | None
    poids_bobine_catalogue: Nombre
    ecart_bobine: float | None
    bobine_hors_tolerance: bool
    qualite: str
    qualite_libelle: str
    observations: str


class PagePesees(Page[Pesee]):
    """Une page de l'archive, et ses indicateurs sur **toutes** les lignes filtrées."""

    tolerance: float
    tolerance_bobine: float
    kg_pesees: Nombre
    hors_tolerance: int
    non_conformes: int
    bobines_hors_tolerance: int


class Mesure(Sortie):
    """Un poids moyen de bobine constaté à une réception."""

    date: dt.date | None
    reception_id: int | None
    reception: str
    fournisseur: str
    lot_id: int | None
    lot: str
    quantite_pesee: float
    nb_bobines: float
    poids_bobine: float
    ecart_catalogue: float | None


class EvolutionBobine(Sortie):
    """Le poids de la bobine d'une matière, réception après réception."""

    matiere_id: int | None
    reference: str
    fournisseur: str
    poids_catalogue: float
    receptions: int
    premier: float
    dernier: float
    derniere_date: dt.date | None
    evolution: float | None = Field(description="null pour une seule réception")
    moyenne: float
    mini: float
    maxi: float
    ecart_catalogue: float | None
    hors_tolerance: bool
    historique: list[Mesure]


class EvolutionBobines(Sortie):
    """Route 177 : les matières suivies, la tolérance du réglage, les indicateurs."""

    tolerance: float
    lignes: list[EvolutionBobine]
    hors_tolerance: int
    alourdies: int
    allegees: int
