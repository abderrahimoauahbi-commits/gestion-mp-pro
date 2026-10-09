"""Schémas Pydantic du domaine « Réclamations » (routes 181–186, API-PRO § 1.20).

Le motif et l'issue se donnent par leur code (`qualite`, `avoir`…) ou leur libellé (« Avoir ») :
la liste est servie par `GET /motifs` (lot D1) ; hors liste, le refus la cite (A-22).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L

MAX_KG = Decimal(10**9)
MAX_MONTANT = Decimal(10**10)
MAX_TEXTE = 4000
MOTIF_MIN = 3


class ReclamationCreation(Entree):
    """Ouvrir une réclamation : sur une réception, une de ses lignes, un lot, ou sans réception."""

    fournisseur_id: int = Field(ge=1)
    reception_id: int | None = Field(None, ge=1)
    reception_ligne_id: int | None = Field(None, ge=1, description="la ligne en cause")
    lot_id: int | None = Field(None, ge=1)
    motif: str = Field(min_length=1, max_length=80, description="code ou libellé")
    description: str = Field("", max_length=MAX_TEXTE)
    quantite: Decimal = Field(Decimal(0), ge=0, le=MAX_KG, description="kg en cause")
    montant_demande: Decimal = Field(Decimal(0), ge=0, le=MAX_MONTANT)
    devise: str = Field("", max_length=L.CODE_DEVISE, description="vide : celle de la réception")
    ouverte_le: dt.date | None = None


class ReclamationModification(Entree):
    """La réponse du fournisseur et l'avoir obtenu (champ absent : inchangé)."""

    version: int = Field(ge=1)
    reponse: str | None = Field(None, max_length=MAX_TEXTE)
    description: str | None = Field(None, max_length=MAX_TEXTE)
    montant_obtenu: Decimal | None = Field(None, ge=0, le=MAX_MONTANT)


class ClotureReclamation(Entree):
    """Clore avec l'issue (obligatoire)."""

    version: int = Field(ge=1)
    issue: str = Field("", max_length=40, description="code ou libellé")
    montant_obtenu: Decimal | None = Field(None, ge=0, le=MAX_MONTANT)
    close_le: dt.date | None = None
    reponse: str | None = Field(None, max_length=MAX_TEXTE)


class ReouvertureReclamation(Entree):
    """Rouvrir : on attend de nouveau le fournisseur ; le motif reste au journal."""

    version: int = Field(ge=1)
    motif: str = Field(min_length=MOTIF_MIN, max_length=L.MOTIF)


class ReclamationFiche(Sortie):
    """Une réclamation (liste 181 et fiche 182)."""

    id: int
    numero: str
    statut: str
    fournisseur_id: int
    fournisseur: str
    reception_id: int | None
    reception: str
    reception_date: dt.date | None
    numero_bl: str
    reception_ligne_id: int | None
    lot_id: int | None
    lot: str
    matiere_id: int | None
    reference: str
    pese: Nombre | None = Field(description="pesée de la ligne en cause")
    motif: str
    motif_libelle: str
    description: str
    quantite: Nombre
    montant_demande: Nombre
    devise: str
    reponse: str
    issue: str | None
    issue_libelle: str
    montant_obtenu: Nombre
    ouverte_le: dt.date
    close_le: dt.date | None
    jours: int = Field(description="depuis l'ouverture (jusqu'à la clôture pour une close)")
    cree_par: str
    version: int


class ReclamationResume(ReclamationFiche):
    """Une réclamation dans la liste (mêmes champs que la fiche)."""
