"""Schémas Pydantic du domaine « Réceptions et factures » (routes 167–175, API-PRO § 1.19).

Entrées dérivées de `communs.Entree` (champ inconnu refusé) ; sorties lues depuis les dataclasses
des services (`receptions_lecture`, `receptions_fiche`, `factures_lecture`). Bornes de Gestion MP
(`api/receptions.py`) : pesées et BL ≤ 10⁹ kg, palettes ≤ 10⁵, bobines en plus ≤ 10⁶, prix
≤ 10⁷ (au kilo, dans la devise de la réception), montant de facture > 0 et ≤ 10¹⁰,
observations ≤ 2 000 caractères. Les schémas de l'archive des pesées et du poids des bobines
sont dans `schemas_pesees.py`.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import Field, field_validator

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import QualiteReception

MAX_KG = Decimal(10**9)
MAX_PRIX = Decimal(10**7)
MAX_MONTANT = Decimal(10**10)
MAX_OBSERVATIONS = 2000
MOTIF_MIN = 3


class FactureEntree(Entree):
    """La facture saisie avec la réception (un champ vide n'efface rien)."""

    numero: str = Field("", max_length=L.NUMERO_FACTURE)
    date: dt.date | None = None
    montant: Decimal | None = Field(None, gt=0, le=MAX_MONTANT, description="devise de la clé")
    echeance: dt.date | None = None


class LigneReceptionEntree(Entree):
    """Une ligne pesée au quai (sur un bon, ou hors commande)."""

    commande_ligne_id: int | None = Field(None, ge=1, description="vide : hors commande")
    matiere_id: int = Field(ge=1)
    lot_numero: str = Field("", max_length=L.NUMERO_LOT, description="n° de l'étiquette")
    lot_interne: bool = Field(False, description="numéroté LOT-AAAA-NNNN à la validation")
    quantite_bl: Decimal = Field(Decimal(0), ge=0, le=MAX_KG, description="kg annoncés au BL")
    quantite_pesee: Decimal = Field(Decimal(0), ge=0, le=MAX_KG, description="kg pesés")
    nb_palettes: Decimal = Field(Decimal(0), ge=0, le=Decimal(10**5))
    bobines_en_plus: Decimal = Field(Decimal(0), ge=0, le=Decimal(10**6))
    magasin_id: int | None = Field(None, ge=1)
    qualite: QualiteReception = QualiteReception.conforme
    observations: str = Field("", max_length=L.COMMENTAIRE)
    prix: Decimal | None = Field(
        None, ge=0, le=MAX_PRIX, description="au kilo ; vide : confirmé du bon, sinon catalogue"
    )
    devise: str = Field(
        "", max_length=L.CODE_DEVISE, description="hors commande (vide : celle du fournisseur)"
    )


class ReceptionCreation(Entree):
    """Un camion : en-tête, factures par devise, lignes (une réception par devise)."""

    date: dt.date
    fournisseur_id: int = Field(ge=1)
    numero_bl: str = Field("", max_length=L.NUMERO_BL)
    controle_par: str = Field("", max_length=L.CONTROLE_PAR, description="contrôle au quai")
    observations: str = Field("", max_length=MAX_OBSERVATIONS)
    factures: dict[str, FactureEntree] = Field(
        default_factory=dict, description="par devise : {« EUR » : facture}"
    )
    lignes: list[LigneReceptionEntree] = Field(min_length=1, max_length=500)

    @field_validator("factures")
    @classmethod
    def _devises(cls, valeur: dict[str, FactureEntree]) -> dict[str, FactureEntree]:
        """Les clés en majuscules (« eur » = « EUR »)."""
        return {k.strip().upper(): v for k, v in valeur.items()}


class ReceptionModification(ReceptionCreation):
    """La correction d'un brouillon : la même saisie, sa version ; une seule devise."""

    version: int = Field(ge=1)


class AnnulationReception(Entree):
    """Annuler une réception validée : le motif est exigé (il reste sur la fiche)."""

    version: int = Field(ge=1)
    motif: str = Field(min_length=MOTIF_MIN, max_length=L.MOTIF)


class FactureCorrection(Entree):
    """La facture d'une réception validée : champ absent = inchangé, `null` = vidé ;
    `numero: ""` détache la facture."""

    version: int = Field(ge=1, description="version de la réception")
    numero: str | None = Field(None, max_length=L.NUMERO_FACTURE)
    date: dt.date | None = None
    montant: Decimal | None = Field(None, gt=0, le=MAX_MONTANT)
    echeance: dt.date | None = None


# ── Sorties ──────────────────────────────────────────────────────────────────


class FactureLue(Sortie):
    """La facture d'une réception."""

    id: int
    numero: str
    date: dt.date | None
    montant: Nombre | None
    devise: str
    echeance: dt.date | None
    payee_le: dt.date | None
    version: int


class BonCite(Sortie):
    """Un bon nommé par une réception."""

    id: int
    numero: str


class LigneReception(Sortie):
    """Une ligne de réception (recalée pour un brouillon)."""

    id: int
    commande_ligne_id: int | None
    commande_id: int | None
    commande: str
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Nombre
    poids_bobine_catalogue: Nombre
    bobines_palette: Nombre
    lot_numero: str
    lot_interne: bool
    lot_id: int | None
    quantite_commandee: Nombre
    deja_recu: float
    quantite_attendue: Nombre = Field(description="reste à livrer du moment (kg)")
    quantite_bl: Nombre
    quantite_pesee: Nombre
    reste_apres: float
    nb_palettes: Nombre
    bobines_en_plus: Nombre
    nb_bobines: Nombre
    poids_moyen_bobine: float | None
    ecart: float | None
    ecart_relatif: float | None
    hors_tolerance: bool
    magasin_id: int | None
    magasin: str
    qualite: str
    qualite_libelle: str
    observations: str
    prix: Nombre = Field(description="au kilo, devise de la réception")
    prix_confirme: bool
    retourne: float


class ReceptionResume(Sortie):
    """Une réception dans la liste (route 167)."""

    id: int
    numero: str | None
    libelle: str
    statut: str
    statut_libelle: str
    date: dt.date
    fournisseur_id: int
    fournisseur: str
    devise: str
    numero_bl: str
    facture: FactureLue | None
    commandes: list[BonCite]
    nb_lignes: int
    pese: Nombre = Field(description="kg pesés hors refus")
    nb_reserve: int
    nb_refus: int
    lots: list[int]
    cree_par: str
    controle_par: str
    validee_par: str
    validee_le: dt.datetime | None
    observations: str
    blocages: list[str]
    annulation_motif: str
    version: int


class Annulee(Sortie):
    """Qui a annulé, quand, pourquoi."""

    par: str
    le: dt.datetime
    motif: str


class DossierCite(Sortie):
    """Le dossier d'importation qui porte la réception (ou la facture)."""

    id: int
    numero: str
    statut: str


class Tolerances(Sortie):
    """Les tolérances des réglages (fractions)."""

    ecart_pesee: float
    poids_bobine: float
    excedent: float


class ReclamationDeReception(Sortie):
    """Une réclamation sur la réception."""

    id: int
    numero: str
    ouverte_le: dt.date
    statut: str
    motif: str
    reception_ligne_id: int | None
    lot: str
    reference: str
    quantite: Nombre
    issue: str | None


class ReceptionFiche(ReceptionResume):
    """La fiche d'une réception (route 168)."""

    cree_le: dt.datetime | None
    delai_paiement_jours: int
    lignes: list[LigneReception]
    avertissements: list[str]
    dossier: DossierCite | None
    annulation: Annulee | None
    tolerances: Tolerances | None
    actions: dict[str, str | None] = Field(
        description="geste → null s'il est permis, sinon la raison du refus"
    )
    reclamations: list[ReclamationDeReception]


class ReceptionDeFacture(Sortie):
    """Une réception qui porte la facture."""

    id: int
    numero: str
    statut: str
    date: dt.date


class FactureResume(Sortie):
    """Une facture (route 175)."""

    id: int
    fournisseur_id: int
    fournisseur: str
    numero: str
    date: dt.date | None
    montant: Nombre | None
    devise: str
    echeance: dt.date | None
    payee_le: dt.date | None
    payee_par: str
    montant_estime: Nombre = Field(description="Σ pesée × prix des réceptions validées")
    poids: Nombre
    recue_le: dt.date | None
    receptions: list[ReceptionDeFacture]
    dossier: DossierCite | None
    version: int
