"""Schémas d'entrée du domaine « Importations » (routes 190–204, API-PRO § 1.21).

Dérivés de `communs.Entree` (champ inconnu refusé : le numéro et la facture ne passent pas par
`PUT /dossiers/{id}`, anomalie 5.13). Bornes de Gestion MP (`gestion_mp/api/importations.py`) :
dates de 2000 à 2100 (« date d'arrivée hors période », « date hors période »), kilos ≤ 10⁹,
valeur ≤ 10¹⁰, cours de 0 à 1 000 (vide : le cours du jour), frais de −10⁹ à 10⁹ MAD, longueurs
des colonnes. Les sorties sont dans `schemas_fiche.py` et `schemas_analyse.py`.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from gestion_mp_pro.api.communs import Entree
from gestion_mp_pro.modeles import longueurs as L

MAX_KG = Decimal(10**9)
MAX_VALEUR = Decimal(10**10)
MAX_COURS = Decimal(1000)
MAX_FRAIS = Decimal(10**9)
MAX_OBSERVATIONS = 2000
ANNEE_MIN, ANNEE_MAX = 2000, 2100


def _plausible(jour: dt.date | None, message: str) -> dt.date | None:
    """Une date de 2000 à 2100 (sinon le message de Gestion MP)."""
    if jour is not None and not ANNEE_MIN <= jour.year <= ANNEE_MAX:
        raise ValueError(message)
    return jour


class Version(Entree):
    """La version du dossier lue avec sa fiche (409 si périmée)."""

    version: int = Field(ge=1)


class DossierCreation(Entree):
    """Ouvrir un dossier : depuis la facture d'une réception validée (`facture_id`), ou à la
    main pour un dossier d'avant la mise en service (`numero` facultatif, `date_arrivee`)."""

    facture_id: int | None = Field(None, ge=1, description="la facture de la livraison")
    numero: str = Field(
        "", max_length=L.NUMERO_DOSSIER, description="à la main seulement (« 07/19 »)"
    )
    libelle: str = Field("", max_length=L.LIBELLE_DOSSIER)
    date_arrivee: dt.date | None = None
    banque: str = Field("", max_length=L.BANQUE_DOSSIER)
    commentaire: str = Field("", max_length=MAX_OBSERVATIONS, description="observations")
    local_confirme: bool = Field(False, description="fournisseur marocain : ouvrir quand même")

    @field_validator("date_arrivee")
    @classmethod
    def _arrivee(cls, v: dt.date | None) -> dt.date | None:
        """2000–2100."""
        return _plausible(v, "date d'arrivée hors période")

    @model_validator(mode="after")
    def _une_facture_ou_une_date(self) -> DossierCreation:
        """Sans facture, un dossier d'avant la mise en service dit sa date d'arrivée."""
        if self.facture_id is None and self.date_arrivee is None:
            raise ValueError(
                "Un dossier saisi à la main est d'avant la mise en service : dire sa date "
                "d'arrivée (ou ouvrir le dossier depuis sa facture)."
            )
        return self


class DossierModification(Version):
    """L'en-tête, fiche entière : libellé, banque, observations, date d'arrivée (vide permis)."""

    libelle: str = Field(max_length=L.LIBELLE_DOSSIER)
    banque: str = Field(max_length=L.BANQUE_DOSSIER)
    commentaire: str = Field(max_length=MAX_OBSERVATIONS, description="observations")
    date_arrivee: dt.date | None

    @field_validator("date_arrivee")
    @classmethod
    def _arrivee(cls, v: dt.date | None) -> dt.date | None:
        """2000–2100."""
        return _plausible(v, "date d'arrivée hors période")


class Rattachement(Version):
    """Le second camion d'une facture du dossier (toute sa marchandise libre)."""

    facture_id: int = Field(ge=1)


class LigneManuelle(Version):
    """Une marchandise d'un dossier d'avant la mise en service, saisie comme un stock
    d'ouverture."""

    matiere_id: int = Field(ge=1)
    lot_numero: str = Field("", max_length=L.NUMERO_LOT, description="facultatif ; créé")
    fournisseur_id: int | None = Field(None, ge=1, description="vide : celui de la matière")
    quantite_kg: Decimal = Field(gt=0, le=MAX_KG)
    valeur_devise: Decimal = Field(ge=0, le=MAX_VALEUR, description="le total de la ligne")
    devise: str = Field("MAD", max_length=L.CODE_DEVISE)
    cours: Decimal | None = Field(
        None, gt=0, le=MAX_COURS, description="MAD pour 1 ; vide : le cours du jour"
    )
    commentaire: str = Field("", max_length=L.COMMENTAIRE, description="observations")


class LigneModification(Version):
    """Le cours payé à la banque (`null` : le cours du jour) et les observations d'une
    marchandise ; un champ absent ne change pas."""

    cours: Decimal | None = Field(None, gt=0, le=MAX_COURS)
    commentaire: str | None = Field(None, max_length=L.COMMENTAIRE, description="observations")


class CoursDevise(Version):
    """Un cours pour toutes les marchandises d'une devise (`null` : le cours du jour)."""

    devise: str = Field("", max_length=L.CODE_DEVISE, description="vide : la seule du dossier")
    cours: Decimal | None = Field(gt=0, le=MAX_COURS)


class Detachement(Version):
    """La réception dont toute la marchandise sort du dossier (les frais restent)."""

    reception_id: int = Field(ge=1)


class FraisEntree(Version):
    """Un frais en MAD (négatif : un avoir), réparti à la clé de son poste ou visé sur une
    marchandise. `version` : celle du dossier (ajout) ou celle du frais (modification)."""

    poste_id: int = Field(ge=1)
    montant: Decimal = Field(ge=-MAX_FRAIS, le=MAX_FRAIS, description="MAD ; négatif : un avoir")
    ligne_id: int | None = Field(None, ge=1, description="vide : tout le dossier")
    piece: str = Field("", max_length=L.PIECE)
    prestataire: str = Field("", max_length=L.PRESTATAIRE)
    date_piece: dt.date | None = None
    echeance: dt.date | None = None
    commentaire: str = Field("", max_length=L.COMMENTAIRE, description="observations")

    @field_validator("date_piece", "echeance")
    @classmethod
    def _dates(cls, v: dt.date | None) -> dt.date | None:
        """2000–2100."""
        return _plausible(v, "date hors période")


class ClotureDossier(Version):
    """Clore : les alertes du dossier ont été lues (sinon elles sont rendues en refus)."""

    alertes_lues: bool = False


class ReouvertureDossier(Version):
    """Rouvrir pour corriger (motif facultatif, au journal)."""

    motif: str = Field("", max_length=L.MOTIF)


class AnnulationDossier(Version):
    """Annuler le dossier (il garde son numéro) : le motif est exigé."""

    motif: str = Field(max_length=L.MOTIF)
