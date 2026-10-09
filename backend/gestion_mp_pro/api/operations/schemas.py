"""Schémas Pydantic du domaine « Opérations de stock » (API-PRO § 1.13 : routes 115–123, 241).

Entrées `OperationCreation` (+ `valider`), `OperationModification` (+ `version`), gestes
`ValidationVersion`, `AnnulationOperation` ; sorties `OperationFiche`, `PageOperations`,
`Brouillons`, `ResultatValidationGroupee`. Les champs monétaires suivent les motifs du filtre
des prix (`prix`, `valeurs`) : l'alimentation les reçoit à `null`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Page, Sortie
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import TypeOperation

QUANTITE_MAX = 1_000_000_000
PRIX_MAX = 10_000_000


class LigneOperationEntree(Entree):
    """Une ligne saisie : quantité signée (ajustement), son unité ; prix, devise : ouverture."""

    matiere_id: int = Field(ge=1)
    lot_id: int | None = Field(default=None, ge=1)
    lot_numero: str = Field(default="", max_length=L.NUMERO_LOT)
    lot_interne: bool = Field(default=False, description="numéro LOT-AAAA-NNNN à la validation")
    magasin_id: int = Field(ge=1)
    magasin_destination_id: int | None = Field(default=None, ge=1)
    quantite: float = Field(ge=-QUANTITE_MAX, le=QUANTITE_MAX, allow_inf_nan=False)
    unite: str = Field(default="kg", max_length=10, description="kg, bobine ou palette")
    prix: float = Field(default=0, ge=0, le=PRIX_MAX, allow_inf_nan=False)
    devise: str = Field(default="MAD", max_length=L.CODE_DEVISE)


class _OperationSaisie(Entree):
    """Ce qui se saisit d'une opération."""

    type: TypeOperation
    date: date
    ordre_id: int | None = Field(default=None, ge=1, description="retour des machines")
    fournisseur_id: int | None = Field(
        default=None, ge=1, description="ignoré : le fournisseur d'un retour est celui des lots"
    )
    motif_id: int | None = Field(default=None, ge=1)
    commentaire: str = Field(default="", max_length=L.COMMENTAIRE)
    lignes: list[LigneOperationEntree] = Field(min_length=1, max_length=500)


class OperationCreation(_OperationSaisie):
    """Route 117 : un brouillon ; `valider: true` le valide dans la même transaction."""

    valider: bool = False


class OperationModification(_OperationSaisie):
    """Route 118 : le brouillon entier (lignes remplacées), à la version lue."""

    version: int = Field(ge=1)


class AnnulationOperation(Entree):
    """Route 121 : la version lue et, si l'on veut, pourquoi on annule."""

    version: int = Field(ge=1)
    motif: str = Field(default="", max_length=L.MOTIF)


class LigneOperation(Sortie):
    """Une ligne d'opération (le lot créé, sinon le numéro saisi, sinon « LOT INTERNE »)."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Nombre
    lot_id: int | None
    lot: str
    lot_interne: bool
    magasin_id: int
    magasin: str
    magasin_destination_id: int | None
    magasin_destination: str
    quantite: Nombre
    prix: Nombre | None
    devise: str | None


class ValeurDeviseOperation(Sortie):
    """La valeur d'une ouverture dans une devise."""

    devise: str
    montant: Nombre | None


class OperationFiche(Sortie):
    """Routes 115–121 : une opération, ses lignes, ses auteurs, ses blocages, et ce que le
    lecteur peut en faire (`peut_agir`, sinon `raison`)."""

    id: int
    numero: str | None
    type: TypeOperation
    type_libelle: str
    statut: str
    date: date
    ordre_id: int | None
    ordre: str
    fournisseur_id: int | None
    fournisseur: str
    motif_id: int | None
    motif: str
    code_motif: str
    commentaire: str
    cree_par: str
    cree_le: datetime
    validee_par: str
    validee_le: datetime | None
    annulee_par: str
    annulee_le: datetime | None
    annulation_motif: str
    total: Nombre
    version: int
    peut_agir: bool
    raison: str
    liberation: bool
    mise_en_quarantaine: bool
    lignes: list[LigneOperation]
    valeurs: list[ValeurDeviseOperation] | None
    blocages: list[str]


class PageOperations(Page[OperationFiche]):
    """Route 115 : une page d'opérations (les plus récentes d'abord) et le total filtré."""


class Brouillon(Sortie):
    """Un document en brouillon dans « À valider »."""

    genre: str
    type: str
    id: int
    version: int
    date: date
    libelle: str
    resume: str
    quantite: Nombre
    cree_par: str
    cree_le: datetime | None
    lien: str
    peut_valider: bool
    raison: str
    valide_par: str
    blocages: list[str]


class Brouillons(Sortie):
    """Route 122 : les brouillons (tous, dans l'ordre de validation, puis par genre) et les
    totaux (`validables` : que ce compte peut valider, sans blocage)."""

    lignes: list[Brouillon]
    ordres: list[Brouillon]
    operations: list[Brouillon]
    receptions: list[Brouillon]
    nombre: int
    bloques: int
    validables: int


class DocumentChoisi(Entree):
    """Un document de la sélection : genre, numéro, version lue."""

    genre: Literal["operation", "ordre", "reception"]
    id: int = Field(ge=1)
    version: int | None = Field(default=None, ge=1)


class SelectionBrouillons(Entree):
    """Route 123 : les documents choisis, ou `tous: true` (tout ce que ce compte peut valider)."""

    documents: list[DocumentChoisi] = Field(default_factory=list, max_length=1000)
    tous: bool = False


class Issue(Sortie):
    """Ce qu'est devenu un document : validé (numéro), refusé ou ignoré (raison)."""

    genre: str
    type: str
    id: int
    date: date | None
    libelle: str
    resume: str
    lien: str
    numero: str
    raison: str


class ResultatValidationGroupee(Sortie):
    """Route 123 : validés ; refusés (restés brouillons, intacts) ; ignorés (le rôle ne peut
    pas les valider, avec la raison — C-17)."""

    valides: list[Issue]
    refuses: list[Issue]
    ignores: list[Issue]
