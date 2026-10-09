"""Schémas Pydantic du domaine « Pilotage et analyse » (API-PRO § 1.22, routes 7, 209–220, 235).

Les lignes rendues par le moteur (`calcul.*`) sont décrites **depuis ses dataclasses**
(`du_moteur`) : un champ ajouté au moteur arrive dans l'OpenAPI sans recopie. S'y ajoutent les
identifiants des fiches (`matiere_id`, `fournisseur_id`…) que l'écran ouvre par id. Direction et
achats seulement (aucune route du domaine n'est ouverte à l'alimentation).
"""

from __future__ import annotations

import dataclasses
import typing
from datetime import date
from typing import Any

from pydantic import create_model

from gestion_mp_pro.api.communs import Page, Sortie
from gestion_mp_pro.calcul.controles import Synthese
from gestion_mp_pro.calcul.fournisseurs import PerformanceReception, ScoreFournisseur
from gestion_mp_pro.calcul.opportunites import Opportunite
from gestion_mp_pro.calcul.pilotage_valeurs import (
    AchatsCockpit,
    AlerteCockpit,
    DormantCockpit,
    ExpositionDevise,
    FinanceCockpit,
    StockCockpit,
)
from gestion_mp_pro.calcul.prix import LigneHistoriquePrix, LigneMatrice
from gestion_mp_pro.services.pilotage import LigneValeur
from gestion_mp_pro.services.pilotage_kpi import Kpi as _Kpi

ID = (int | None, None)
"""Un identifiant de fiche, absent quand la ligne ne nomme aucune fiche connue."""


def du_moteur(classe: type, nom: str, doc: str, **extra: Any) -> type[Sortie]:
    """Le schéma d'une dataclass du moteur (mêmes champs, mêmes types), plus `extra`."""
    indices = typing.get_type_hints(classe)
    champs: dict[str, Any] = {
        f.name: (indices[f.name], ...) for f in dataclasses.fields(classe) if f.init
    }
    return create_model(nom, __base__=Sortie, __doc__=doc, **(champs | extra))


# ── Valorisation (210) ────────────────────────────────────────────────────────────────

LigneValorisation = du_moteur(LigneValeur, "LigneValorisation", "Une matière valorisée.")


class Valorisation(Sortie):
    """Route 210 : la valeur du stock détenu (magasins + métiers) au soir de la date."""

    date_reference: date
    total_mad: float
    total_magasin_mad: float
    total_machine_mad: float
    total_kg: float
    total_kg_magasin: float
    total_kg_machine: float
    ecart_mad: float
    nb_matieres: int
    nb_en_stock: int
    lignes: list[LigneValorisation]  # type: ignore[valid-type]


# ── Cockpit (209) ─────────────────────────────────────────────────────────────────────

Kpi = du_moteur(_Kpi, "Kpi", "Un indicateur du Cockpit, avec sa formule.")
StockCockpitSchema = du_moteur(
    StockCockpit,
    "StockCockpit",
    "Le stock du Cockpit (valeur = celle de la Valorisation).",
    valeur_magasins_mad=(float, ...),
    kg_machine=(float, ...),
)
AchatsCockpitSchema = du_moteur(
    AchatsCockpit, "AchatsCockpit", "Les engagements d'achat.", en_retard=(int, ...)
)
FinanceCockpitSchema = du_moteur(FinanceCockpit, "FinanceCockpit", "Rotation, DIO, DSO, DPO.")
DormantCockpitSchema = du_moteur(DormantCockpit, "DormantCockpit", "Le stock dormant.")
OpportuniteLigne = du_moteur(
    Opportunite,
    "OpportuniteLigne",
    "Une piste d'économie.",
    matiere_id=ID,
    matiere_alternative_id=ID,
)
AlerteLigne = du_moteur(
    AlerteCockpit, "AlerteCockpit", "Une matière en alerte.", matiere_id=ID, fournisseur_id=ID
)
Exposition = du_moteur(ExpositionDevise, "ExpositionDevise", "Une devise du budget à émettre.")
SyntheseControles = du_moteur(Synthese, "SyntheseControles", "La note des contrôles.")


class EconomiesCockpit(Sortie):
    """Les pistes d'économies : total, nombre, les cinq premières."""

    total_mad: float
    nb_opportunites: int
    top: list[OpportuniteLigne]  # type: ignore[valid-type]


class Cockpit(Sortie):
    """Route 209 : six indicateurs avec formule, stock, achats, finance, alertes, économies."""

    date_reference: date
    kpi: list[Kpi]  # type: ignore[valid-type]
    stock: StockCockpitSchema  # type: ignore[valid-type]
    achats: AchatsCockpitSchema  # type: ignore[valid-type]
    finance: FinanceCockpitSchema  # type: ignore[valid-type]
    abc: dict[str, int]
    dormant: DormantCockpitSchema  # type: ignore[valid-type]
    sourcing: dict[str, int]
    economies: EconomiesCockpit
    nb_alertes: int
    alerte_rouge: int
    alertes: list[AlerteLigne]  # type: ignore[valid-type]
    devises: list[Exposition]  # type: ignore[valid-type]
    controles: SyntheseControles  # type: ignore[valid-type]


# ── Opportunités (211), prix (213, 214), fournisseurs (215) ───────────────────────────


class Opportunites(Sortie):
    """Route 211 : les pistes d'économies et ce que la comparaison compare."""

    date_reference: date
    avertissement: str
    criteres: dict[str, bool]
    fenetre_jours: float
    seuils: dict[str, float]
    ecartees: dict[str, int]
    total_mad: float
    lignes: list[OpportuniteLigne]  # type: ignore[valid-type]


PrixPaye = du_moteur(
    LigneHistoriquePrix,
    "PrixPaye",
    "Un prix payé et son évolution.",
    matiere_id=ID,
    fournisseur_id=ID,
    commande_id=ID,
)


class HistoriquePrix(Sortie):
    """Route 213 : les prix payés, le plus récent d'abord, et leurs indicateurs."""

    lignes: list[PrixPaye]  # type: ignore[valid-type]
    total_achats_mad: float
    hausses: int
    fortes_hausses: int
    baisses: int
    seuils: dict[str, float]


LigneMatriceSchema = du_moteur(
    LigneMatrice, "LigneMatrice", "Une matière, une devise, ses prix mois par mois.", matiere_id=ID
)


class MatricePrix(Sortie):
    """Route 214 : prix moyen pondéré par mois, dans la devise des factures (E-04)."""

    mois: list[str]
    lignes: list[LigneMatriceSchema]  # type: ignore[valid-type]
    seuils: dict[str, float]


ScoreFournisseurSchema = du_moteur(
    ScoreFournisseur, "ScoreFournisseur", "La note d'un fournisseur.", fournisseur_id=ID
)
ReceptionNotee = du_moteur(
    PerformanceReception,
    "ReceptionNotee",
    "Une réception notée (OTIF).",
    reception_id=ID,
    fournisseur_id=ID,
)


class PerformanceFournisseurs(Sortie):
    """Route 215 : le classement des fournisseurs et leurs réceptions notées."""

    du: date | None
    au: date | None
    cible_otif: float
    seuils: dict[str, float]
    lignes: list[ScoreFournisseurSchema]  # type: ignore[valid-type]
    receptions: list[ReceptionNotee]  # type: ignore[valid-type]


# ── Contrôles (212, 235) ──────────────────────────────────────────────────────────────


class ColonneControle(Sortie):
    """Une colonne du détail d'un contrôle : clé, libellé, unité (« % » : une fraction)."""

    cle: str
    libelle: str
    unite: str


class ControleResume(Sortie):
    """Un contrôle : son verdict, quoi faire, où le corriger, ses colonnes et ses lignes."""

    code: str
    libelle: str
    gravite: str
    garanti: str
    anomalies: int
    conforme: bool
    quoi_faire: str
    lien: str
    colonnes: list[ColonneControle]
    lignes: list[dict[str, Any]]
    lignes_total: int
    tronque: bool


class Controles(Sortie):
    """Route 212 : la synthèse et les 38 contrôles (200 lignes au plus chacun, dit)."""

    date_reference: date
    synthese: SyntheseControles  # type: ignore[valid-type]
    controles: list[ControleResume]


class PageControle(Page[dict[str, Any]]):
    """Route 235 : le détail complet d'un contrôle, cherché, page par page."""

    code: str
    libelle: str
    gravite: str
    quoi_faire: str
    lien: str
    colonnes: list[ColonneControle]


# ── Données brutes (7) ────────────────────────────────────────────────────────────────


class DonneesBrutes(Sortie):
    """Route 7 : les lignes d'une table métier, telles qu'en base."""

    table: str
    date_reference: date | None
    colonnes: list[str]
    lignes: list[dict[str, Any]]
