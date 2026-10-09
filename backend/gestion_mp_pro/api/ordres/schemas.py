"""Schémas Pydantic du domaine « Ordres de fabrication » (API-PRO § 1.15 : routes 134–144).

Entrées `DemandeProposition`, `OrdreCreation`, `OrdreModification`, `AnnulationOrdre` (champs
inconnus refusés, `NaN` et infini refusés) ; sorties `Proposition`, `OrdreResume`,
`OrdreFiche`, `LotSorti`, `ConsommationOrdre`. Aucun prix : les quantités sont des kilos, les
surfaces des m² (`Nombre` : nombres JSON).
"""

from __future__ import annotations

import datetime as dt

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.services.conversions import Unite

M2_MAX = 1e8
KG_MAX = 1e9


class QualiteSaisie(Entree):
    """Une qualité tissée et ses m² (une fois par ordre)."""

    qualite_id: int
    m2: float = Field(gt=0, le=M2_MAX, allow_inf_nan=False)


class LigneSaisie(Entree):
    """Un lot à sortir : quantité en kilos, bobines (entières) ou palettes."""

    lot_id: int
    quantite: float = Field(gt=0, le=KG_MAX, allow_inf_nan=False)
    unite: Unite = Unite.kg
    matiere_id: int | None = Field(default=None, description="contrôle : le lot de cette matière")


class DemandeProposition(Entree):
    """Route 134 : ce qu'on tisse, d'où, à quelle date (aujourd'hui sans date)."""

    date: dt.date | None = None
    magasin_id: int
    metier_id: int | None = None
    qualites: list[QualiteSaisie] = Field(min_length=1, max_length=50)


class OrdreCreation(Entree):
    """Route 137 : un brouillon ; sans qualité, l'ordre est « hors recette »."""

    date: dt.date
    magasin_id: int
    metier_id: int | None = None
    commentaire: str = Field(default="", max_length=L.COMMENTAIRE)
    qualites: list[QualiteSaisie] = Field(default_factory=list, max_length=50)
    lignes: list[LigneSaisie] = Field(min_length=1, max_length=500)


class OrdreModification(OrdreCreation):
    """Route 138 : le brouillon entier, à sa version lue."""

    version: int = Field(ge=1)


class AnnulationOrdre(Entree):
    """Route 141 : la version lue ; un motif facultatif."""

    version: int = Field(ge=1)
    motif: str = Field(default="", max_length=L.MOTIF)


class LotPropose(Sortie):
    """Un lot disponible à la date ; `propose` : ce qu'on y prend (0 : pas besoin)."""

    lot_id: int
    lot: str
    entre_le: dt.date
    disponible: Nombre
    poids_bobine: Nombre
    propose: Nombre


class ParQualite(Sortie):
    """Ce qu'une qualité demande d'une matière, perte comprise (kg)."""

    qualite_id: int
    qualite: str
    kg: Nombre


class LigneProposee(Sortie):
    """Une matière demandée : prévu (perte comprise), lots FIFO, manque."""

    matiere_id: int
    reference: str
    designation: str
    role: str
    prevu: Nombre
    kg_par_ml: Nombre
    poids_bobine: Nombre
    bobines_palette: Nombre
    par_qualite: list[ParQualite]
    lots: list[LotPropose]
    disponibles: list[LotPropose]
    manque: Nombre


class Proposition(Sortie):
    """Route 134 : les lignes, les totaux, ce qui manque, la recette incomplète, les blocages."""

    date: dt.date
    magasin_id: int
    taux_perte: Nombre
    prevu: Nombre
    manque: Nombre
    lignes: list[LigneProposee]
    manques: list[LigneProposee]
    recettes_incompletes: list[str]
    blocages: list[str]


class QualiteOrdre(Sortie):
    """Une qualité tissée par l'ordre."""

    qualite_id: int
    qualite: str
    nom: str
    m2: Nombre


class LigneOrdre(Sortie):
    """Un lot sorti (ou à sortir) : kilos, et bobines quand le compte tombe juste."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Nombre
    lot_id: int
    lot: str
    quantite: Nombre
    poids_bobine: Nombre
    bobines_palette: Nombre
    bobines: int | None


class Retour(Sortie):
    """Un retour des machines : l'opération (`id`) ou la reprise de l'ERP Fil (`id` nul)."""

    id: int | None
    numero: str
    date: dt.date
    quantite: Nombre


class ParMatiere(Sortie):
    """Prévu par la recette (perte comprise) et sorti net d'une matière (kg)."""

    matiere_id: int | None
    reference: str
    quantite: float
    prevu: float
    ecart: float | None
    hors_recette: bool
    kg_par_ml: float


class OrdreResume(Sortie):
    """Un ordre dans la liste (135) : ce qu'il tisse, sorti net, écart, retours, lots."""

    id: int
    version: int
    numero: str | None
    statut: StatutOrdre
    date: dt.date
    magasin_id: int
    magasin: str
    metier_id: int | None
    metier: str
    commentaire: str
    cree_par: str
    cree_le: dt.datetime
    valide_par: str
    valide_le: dt.datetime | None
    annule_par: str
    annule_le: dt.datetime | None
    annulation_motif: str
    prevu_fige: bool
    taux_perte: float
    qualites: list[QualiteOrdre]
    fabrication: str
    m2: Nombre
    total: Nombre
    retours: list[Retour]
    revenu: Nombre
    prevu: float
    net: float
    ecart: float | None
    ecart_relatif: float | None
    lots: list[str]
    matieres: list[str]
    blocages: list[str]


class OrdreFiche(OrdreResume):
    """Un ordre (136) : ses lignes et, validé, le prévu et le sorti net par matière ;
    `message` : ce qu'un geste vient de faire (l'annulation le dit)."""

    lignes: list[LigneOrdre]
    par_matiere: list[ParMatiere]
    message: str = ""


class LotSorti(Sortie):
    """Ce qu'un ordre a emporté d'un lot, net des retours (142) : ce qui peut revenir."""

    lot_id: int
    lot: str
    matiere_id: int
    reference: str
    designation: str
    sorti_net: Nombre
    kg_par_ml: Nombre
    poids_bobine: Nombre
    bobines_palette: Nombre
    blocage: str


class QualiteM2(Sortie):
    """Une qualité de l'ordre et ses m²."""

    qualite_id: int
    qualite: str
    m2: Nombre


class ConsommationOrdre(Sortie):
    """Route 143 : ce qu'un ordre validé a consommé, face au prévu de sa recette (kg)."""

    ordre_id: int
    numero: str
    date: dt.date
    debut: dt.date
    fin: dt.date
    qualites: list[QualiteM2]
    fabrication: str
    m2: Nombre
    commentaire: str
    consomme: float
    retours: float
    net: float
    prevu: float
    ecart: float | None
    ecart_relatif: float | None
    taux_perte: float
    references: list[ParMatiere]
    lots: list[str]
