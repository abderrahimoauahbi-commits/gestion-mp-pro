"""Schémas Pydantic du domaine « Stock et lots » (API-PRO § 1.12, routes 103–113 et 236).

Les noms des champs monétaires suivent les motifs du filtre des prix (`prix*`, `cours*`,
`*_mad`, `valeur*`, `montant*`, `cout*`) : l'alimentation les reçoit à `null`. `LigneStock`
reprend **tous** les champs de `calcul.stock.LigneStock` (CALCULS § 3.9), chacun facultatif :
l'alimentation reçoit aussi à `null` le conseil d'achat (`services.stock_lecture`).
"""

from __future__ import annotations

import dataclasses
import typing
from datetime import date, datetime
from typing import Any

from pydantic import Field, create_model

from gestion_mp_pro.api.communs import Entree, Nombre, Page, Sortie
from gestion_mp_pro.calcul.stock import LigneStock as _LigneDuMoteur
from gestion_mp_pro.modeles import longueurs as L


def _ligne_de_stock() -> type[Sortie]:
    """`LigneStock` : les champs du moteur (facultatifs), l'identifiant de la matière, la valeur
    de ce qui est monté sur les métiers."""
    indices = typing.get_type_hints(_LigneDuMoteur)
    champs: dict[str, Any] = {
        f.name: (indices[f.name] | None, None) for f in dataclasses.fields(_LigneDuMoteur)
    }
    champs |= {
        "matiere_id": (int | None, None),
        "role_id": (int | None, None),
        "fournisseur_id": (int | None, None),
        "valeur_machine_mad": (float | None, None),
    }
    return create_model("LigneStock", __base__=Sortie, __doc__="Une matière à la date.", **champs)


LigneStock = _ligne_de_stock()


class EtatStock(Sortie):
    """Route 103 : l'état du stock à la date de référence."""

    date_reference: date
    magasins: list[str]
    magasin_ids: dict[str, int] = Field(
        description="code du magasin → id (`par_magasin` est par code)"
    )
    lignes: list[LigneStock]  # type: ignore[valid-type]


class SoldeMagasin(Sortie):
    """Ce qu'un lot porte dans un magasin."""

    magasin_id: int
    magasin: str
    type: str
    quantite: Nombre


class OrdreServi(Sortie):
    """Un ordre de fabrication qu'un lot a servi."""

    id: int
    numero: str


class HistoriqueLot(Sortie):
    """Ce qu'a vécu un lot : entré, sorti (net des retours), dernier mouvement, ordres."""

    entre: Nombre
    sorti: Nombre
    dernier_mouvement: date | None
    ordres: list[OrdreServi]


class LotSolde(Sortie):
    """Route 107 : un lot, ses soldes par magasin, son statut calculé, son histoire."""

    lot_id: int
    lot: str
    interne: bool
    matiere_id: int
    reference: str
    designation: str
    role: str
    kg_par_ml: Nombre
    fournisseur: str
    entre_le: date
    poids_bobine: Nombre
    bobines_palette: Nombre
    quantite: Nombre
    disponible: Nombre
    quarantaine: Nombre
    magasins: list[SoldeMagasin]
    bobines: int | None
    statut: str
    historique: HistoriqueLot


class BesoinDeQualite(Sortie):
    """D'où vient le besoin : une qualité qui consomme la matière, mois par mois."""

    qualite: str
    pourcentage: float
    kg_par_m2: float
    m2: list[float]
    kg: list[float]


class FilSurMetier(Sortie):
    """Ce qui est monté de la matière sur un étage d'un métier (sur les métiers)."""

    metier: str
    etage: int
    reference: str
    metres: float
    pourcentage: float
    densite: float
    bobines: float
    poids_bobine: float
    poids: float


class FicheStockMatiere(Sortie):
    """Route 104 : la ligne de la matière, d'où vient son besoin, ses lots, ses métiers."""

    ligne: LigneStock  # type: ignore[valid-type]
    besoins_par_qualite: list[BesoinDeQualite]
    lots: list[LotSolde]
    sur_les_metiers: list[FilSurMetier]


class MouvementLigne(Sortie):
    """Une écriture du journal du stock (S64)."""

    id: int
    date: date
    saisi_le: datetime
    type: str
    libelle: str
    matiere_id: int
    reference: str
    lot_id: int
    lot: str
    magasin_id: int
    magasin: str
    quantite: Nombre
    prix: Nombre | None
    devise: str | None = Field(description="null hors direction et achats (an. 27)")
    cours: Nombre | None
    document: str
    document_id: int | None
    document_numero: str
    ordre_id: int | None
    paire_id: int | None
    motif: str
    commentaire: str
    auteur: str
    contrepasse_id: int | None
    cout_mad: float | None = None
    valeur_mad: float | None = None


class PageMouvements(Page[MouvementLigne]):
    """Route 105 : une page du journal, le plus récent d'abord ; `types` : les types présents
    compte tenu des autres filtres (filtres liés)."""

    types: list[str] = Field(default_factory=list)


class ReceptionDuLot(Sortie):
    """La première réception validée qui a fait entrer le lot."""

    id: int
    numero: str
    date: date
    bl: str
    facture: str
    pesee: float
    qualite: str


class LotFiche(LotSolde):
    """Route 108 : tout d'un lot (son journal du plus ancien au plus récent)."""

    poids_bobine_le: date | None
    commentaire: str
    reception: ReceptionDuLot | None
    mouvements: list[MouvementLigne]
    version: int


class LotModification(Entree):
    """Route 109 : le commentaire du lot et la version lue."""

    commentaire: str = Field(max_length=L.COMMENTAIRE)
    version: int = Field(ge=1)


class LotResume(Sortie):
    """Route 110 : un lot scanné."""

    lot_id: int
    lot: str
    matiere_id: int
    reference: str
    quantite: Nombre


class LotDisponible(Sortie):
    """Route 111 : un lot qu'on peut sortir, dans l'ordre FIFO."""

    lot_id: int
    lot: str
    magasin_id: int
    magasin: str
    quantite: Nombre
    entre_le: date
    poids_bobine: Nombre


class EtapeTracee(Sortie):
    """Une écriture du chemin de la matière (quantité signée ; un transfert : ce qui a bougé)."""

    id: int | None
    date: date
    type: str
    libelle: str
    reference: str
    quantite: float
    lot: str
    lot_id: int | None
    matiere_id: int | None
    ordre: str
    ordre_id: int | None
    magasin_source: str
    magasin_destination: str
    utilisateur: str
    document: str
    document_type: str | None = Field(
        description="reception, ordre, operation, inventaire, reprise"
    )
    document_id: int | None = Field(description="la fiche du document (lien), null pour la reprise")
    annulation: bool
    annule: bool


class Tracabilite(Sortie):
    """Route 112 : le chemin, et ses totaux hors annulations et transferts."""

    lot_id: int | None
    lot: str
    ordre_id: int | None
    ordre: str
    matiere_id: int | None
    matiere: str
    references: list[str]
    lots: list[str]
    ordres: list[str]
    entrees: float
    sorties: float
    mouvements: list[EtapeTracee]


class EcartDeSolde(Sortie):
    """Un solde tenu qui ne dit pas ce que dit le journal."""

    lot_id: int
    magasin_id: int
    reference: str
    lot: str
    magasin: str
    journal: Nombre
    solde: Nombre


class ControleSoldes(Sortie):
    """Route 113 : soldes contre journal, au gramme."""

    conforme: bool
    ecarts: list[EcartDeSolde]
    negatifs: int
    lots: int
