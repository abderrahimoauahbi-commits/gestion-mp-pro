"""Schémas Pydantic du domaine « Suivi » (API-PRO § 1.23, routes 221–234).

Signalements (ouverts à l'alimentation : aucun montant), pièces jointes, échéancier,
indicateurs, bilan du mois. Les montants suivent les motifs du filtre des prix (`montant*`,
`*_mad`, `valeur*`) ; les routes chiffrées sont réservées à la direction et aux achats.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Page, Sortie
from gestion_mp_pro.api.pilotage.schemas import du_moteur
from gestion_mp_pro.calcul.production import ConsommationOrdre as _ConsommationOrdre
from gestion_mp_pro.calcul.suivi import Echeance
from gestion_mp_pro.calcul.suivi_bilan import BilanMois as _BilanMois
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import Urgence

# ── Signalements (221–223) ────────────────────────────────────────────────────────────


class SignalementFiche(Sortie):
    """Un besoin signalé par l'atelier, et sa réponse."""

    id: int
    quand: datetime
    par: str
    par_id: int | None
    matiere_id: int | None
    reference: str
    texte: str
    urgence: str
    traite: bool
    traite_par: str
    traite_le: datetime | None
    reponse: str


class PageSignalements(Page[SignalementFiche]):
    """Route 221 : les besoins, le plus récent d'abord."""


class SignalementCreation(Entree):
    """Route 222 : la matière (facultative), le texte, l'urgence."""

    matiere_id: int | None = None
    texte: str = Field(min_length=2, max_length=L.TEXTE_SIGNALEMENT)
    urgence: Urgence = Urgence.normale


class Traitement(Entree):
    """Route 223 : la réponse à l'atelier (facultative)."""

    reponse: str = Field("", max_length=L.TEXTE_SIGNALEMENT)


# ── Pièces jointes (224–227) ──────────────────────────────────────────────────────────


class PieceFiche(Sortie):
    """Une pièce jointe d'un document (le fichier se relit par la route 226)."""

    id: int
    objet: str
    objet_id: int | None
    nom: str
    type: str
    taille: int
    empreinte: str
    par: str
    par_id: int | None
    quand: datetime


# ── Échéancier (228–230) ──────────────────────────────────────────────────────────────

EcheanceLigne = du_moteur(
    Echeance,
    "EcheanceLigne",
    "Une pièce à payer : facture fournisseur ou frais d'importation.",
    version=(int, ...),
    reception_id=(int | None, None),
    dossier_id=(int | None, None),
    fournisseur_id=(int | None, None),
    etat=(str | None, None),
)


class Echeancier(Sortie):
    """Route 228 : les échéances filtrées, leurs indicateurs, et les quatre vues."""

    aujourdhui: date
    lignes: list[EcheanceLigne]  # type: ignore[valid-type]
    par_mois: dict[str, float]
    total_mad: float
    echu_mad: float
    echues: int
    dans_30_jours_mad: float
    a_dater: list[EcheanceLigne]  # type: ignore[valid-type]
    a_dater_mad: float
    reglees: list[EcheanceLigne]  # type: ignore[valid-type]
    ecartees: list[EcheanceLigne]  # type: ignore[valid-type]


class Paiement(Entree):
    """Route 229 : le jour du règlement ; vide, le règlement est annulé (direction, motif)."""

    genre: Literal["facture", "frais"]
    id: int
    payee_le: date | None
    version: int = Field(ge=1)
    motif: str = Field("", max_length=L.MOTIF)


# ── Indicateurs (231, 232) ────────────────────────────────────────────────────────────


class IndicateurJour(Sortie):
    """La photo d'un jour des grands indicateurs."""

    jour: date
    pris_le: datetime
    pris_par_id: int | None
    valeur_stock_mad: Nombre
    couverture_jours: Nombre | None
    ruptures: int
    critiques: int
    urgents: int
    a_commander_mad: Nombre
    commandes_en_cours_mad: Nombre
    otif_moyen: Nombre | None


# ── Bilan du mois (233) ───────────────────────────────────────────────────────────────

# Nom propre au bilan : la dataclass du moteur porterait sinon le nom `ConsommationOrdre`, déjà
# pris par le schéma de la route 143, et la génération des types de l'écran renommerait l'un.
EcartOrdreBilan = du_moteur(
    _ConsommationOrdre, "EcartOrdreBilan", "Un ordre du mois et son écart au prévu (bilan)."
)

BilanMois = du_moteur(
    _BilanMois,
    "BilanMois",
    "Le bilan matières d'un mois : magasins et métiers, en kilos et en dirhams.",
    ecarts_ordres=(list[EcartOrdreBilan], ...),  # type: ignore[valid-type]
    mois_iso=(str, ...),
    du=(date, ...),
    au=(date, ...),
    stock_debut_magasins_kg=(float, ...),
    stock_fin_magasins_kg=(float, ...),
    metiers_debut_kg=(float, ...),
    metiers_fin_kg=(float, ...),
    variation_metiers_kg=(float, ...),
    valeur_debut_magasins_mad=(float, ...),
    valeur_fin_magasins_mad=(float, ...),
    metiers_debut_mad=(float, ...),
    metiers_fin_mad=(float, ...),
    variation_metiers_mad=(float, ...),
    sorties_nettes_kg=(float, ...),
    alerte_rouge=(int, ...),
)
