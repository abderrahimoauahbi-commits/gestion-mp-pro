"""Schémas du domaine « Fournisseurs » (API-PRO § 1.8, routes 64–69).

L'alimentation ne lit que le nom, le pays et l'état d'un fournisseur (`FournisseurResume`) :
ni banque, ni conditions ou mode de paiement, ni notes (A-14).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Sortie
from gestion_mp_pro.modeles import longueurs as L

DELAI_MAX = 730
NOTES_MAX = 2000


class FournisseurResume(Sortie):
    """Ce que l'alimentation lit d'un fournisseur."""

    id: int
    nom: str
    pays: str
    actif: bool


class FournisseurFiche(FournisseurResume):
    """La fiche d'un fournisseur et ce qui pèse sur lui (routes 64–67)."""

    code: str
    contact: str
    telephone: str
    email: str
    devise: str
    delai_jours: int
    couverture_commande_jours: int
    mode_paiement: str
    delai_paiement_jours: int
    conditions_paiement: str
    incoterm: str
    port_chargement: str
    banque: str
    notes: str
    version: int
    local: bool = Field(description="marocain : pays MAROC, MOROCCO ou MA ; sans pays, en MAD")
    devises: dict[str, int] = Field(description="nombre de matières par devise")
    nb_matieres: int
    nb_commandes: int
    nb_receptions: int
    nb_lots: int
    nb_operations: int
    nb_factures: int
    nb_pieces: int
    delai_mesure_jours: float | None = Field(
        description="commande → réception validée, moyenne sur 365 jours"
    )
    livraisons_mesurees: int
    utilise: bool
    empechements: list[str] = Field(description="ce qui empêche la suppression")
    modifie_le: datetime | None


class FournisseurCreation(Entree):
    """Un fournisseur nouveau (route 66)."""

    nom: str = Field(min_length=2, max_length=L.NOM_FOURNISSEUR)
    code: str = Field(default="", max_length=L.CODE_FOURNISSEUR)
    pays: str = Field(default="", max_length=L.PAYS)
    contact: str = Field(default="", max_length=L.CONTACT)
    telephone: str = Field(default="", max_length=L.TELEPHONE)
    email: str = Field(default="", max_length=L.EMAIL_FOURNISSEUR)
    devise: str = Field(default="MAD", max_length=L.CODE_DEVISE)
    delai_jours: int = Field(default=60, gt=0, le=DELAI_MAX)
    couverture_commande_jours: int = Field(default=0, ge=0, le=DELAI_MAX)
    mode_paiement: str = Field(default="", max_length=L.MODE_PAIEMENT)
    delai_paiement_jours: int = Field(default=0, ge=0, le=DELAI_MAX)
    conditions_paiement: str = Field(default="", max_length=L.CONDITIONS_PAIEMENT)
    incoterm: str = Field(default="", max_length=L.INCOTERM)
    port_chargement: str = Field(default="", max_length=L.PORT)
    banque: str = Field(default="", max_length=L.BANQUE)
    notes: str = Field(default="", max_length=NOTES_MAX)
    actif: bool = True


class FournisseurModification(FournisseurCreation):
    """Un fournisseur modifié (route 67) : la fiche entière et sa version lue."""

    version: int = Field(ge=1)
