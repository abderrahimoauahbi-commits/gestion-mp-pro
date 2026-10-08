"""Opérations de stock et leurs lignes (MODELE-DONNEES § 3.6).

Le type d'une opération ne change jamais (trigger `tr_operation_type_fige`). Un retour des
machines nomme son ordre ; un retour au fournisseur, son fournisseur ; un ajustement validé
est justifié (au moins 5 caractères). « Lot interne » est une case (`lot_interne`) : le numéro
`LOT-AAAA-NNNN` est donné à la validation.
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    AvecVersion,
    Base,
    chaine,
    cle_primaire,
    colonne,
    enfants,
    fk,
    instant,
    qui,
)
from gestion_mp_pro.modeles.enums import StatutDocument, TypeOperation
from gestion_mp_pro.modeles.receptions import ANNULE_DATE, NUMERO_SI_VALIDE, VALIDE_DATE
from gestion_mp_pro.modeles.stock import fk_lot
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, enumeration


class Operation(AvecVersion, Base):
    """Une opération de stock : ouverture, retour machine, transfert, ajustement, retour
    fournisseur (numéro `OUV|RET|TRF|AJU|RFO-AAAA-NNNN` à la validation)."""

    __tablename__ = "operation"
    __table_args__ = (
        CheckConstraint(NUMERO_SI_VALIDE, name="numero_statut"),
        CheckConstraint(VALIDE_DATE.format(colonne="validee_le"), name="validation_date"),
        CheckConstraint(
            ANNULE_DATE.format(statut="annulee", colonne="annulee_le"), name="annulation_date"
        ),
        CheckConstraint("(type = 'retour_machine') = (ordre_id IS NOT NULL)", name="ordre"),
        CheckConstraint(
            "type <> 'retour_fournisseur' OR fournisseur_id IS NOT NULL", name="fournisseur"
        ),
        CheckConstraint(
            "type <> 'ajustement' OR statut = 'brouillon' OR length(trim(commentaire)) >= 5",
            name="ajustement_justifie",
        ),
        Index(None, "type", "statut"),
        Index(None, "ordre_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str | None] = mapped_column(String(L.NUMERO), unique=True)
    type: Mapped[TypeOperation] = mapped_column(enumeration(TypeOperation, 20))
    statut: Mapped[StatutDocument] = colonne(
        enumeration(StatutDocument, 12), defaut=StatutDocument.brouillon
    )
    date: Mapped[dt.date] = mapped_column(Date)
    ordre_id: Mapped[int | None] = mapped_column(fk("ordre.id"))
    fournisseur_id: Mapped[int | None] = mapped_column(fk("fournisseur.id"))
    motif_id: Mapped[int | None] = mapped_column(fk("motif.id"))
    motif_texte: Mapped[str] = chaine(L.LIBELLE_MOTIF)
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    validee_par_id: Mapped[int | None] = qui()
    validee_le: Mapped[datetime | None] = instant()
    annulee_par_id: Mapped[int | None] = qui()
    annulee_le: Mapped[datetime | None] = instant()
    annulation_motif: Mapped[str] = chaine(L.MOTIF)

    lignes: Mapped[list[OperationLigne]] = enfants("OperationLigne")


class OperationLigne(Base):
    """Une ligne d'opération : lot (ou lot à créer), magasin, destination d'un transfert."""

    __tablename__ = "operation_ligne"
    __table_args__ = (
        fk_lot(),
        CheckConstraint(
            "magasin_destination_id IS NULL OR magasin_destination_id <> magasin_id",
            name="destination_distincte",
        ),
        CheckConstraint("quantite <> 0", name="quantite_non_nulle"),
        CheckConstraint("prix >= 0", name="prix_positif"),
        CheckConstraint("prix = 0 OR devise IS NOT NULL", name="prix_en_devise"),
        Index(None, "operation_id"),
        Index(None, "lot_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    operation_id: Mapped[int] = mapped_column(fk("operation.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_id: Mapped[int | None] = mapped_column()
    lot_numero: Mapped[str] = chaine(L.NUMERO_LOT)
    lot_interne: Mapped[bool] = colonne(defaut=False)
    magasin_id: Mapped[int] = mapped_column(fk("magasin.id"))
    magasin_destination_id: Mapped[int | None] = mapped_column(fk("magasin.id"))
    quantite: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    devise: Mapped[str | None] = mapped_column(CHAR(L.CODE_DEVISE), fk("devise.code"))
