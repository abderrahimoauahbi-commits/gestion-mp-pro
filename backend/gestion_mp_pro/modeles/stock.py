"""Lots, soldes, journal du stock (MODELE-DONNEES § 3.3).

- `mouvement` est le journal : seul `services/stock.py` y écrit ; jamais modifié ni supprimé
  (trigger `tr_mouvement_immuable`, désactivable seulement par le rôle propriétaire du schéma,
  pour la reprise et le vidage de l'activité).
- `solde` est son cache, tenu dans la même transaction sous `SELECT … FOR UPDATE` ; `>= 0` exact.
- La matière d'un mouvement est celle de son lot : FK composite `(lot_id, matiere_id)` →
  `lot(id, matiere_id)` (invariant I31 garanti par la base, incohérence 6).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from gestion_mp_pro.modeles.catalogue import Matiere

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    Base,
    chaine,
    cle_primaire,
    cle_primaire_longue,
    colonne,
    fk,
    index_recherche,
    instant,
    qui,
    recherche,
    vers,
)
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
from gestion_mp_pro.modeles.types import COURS, MESURE, PRIX, QUANTITE, enumeration


def fk_lot(prefixe: str = "", ondelete: str = "RESTRICT") -> ForeignKeyConstraint:
    """FK composite `(lot_id, matiere_id)` → `lot(id, matiere_id)` : la matière est celle du lot."""
    return ForeignKeyConstraint(
        [f"{prefixe}lot_id", f"{prefixe}matiere_id"],
        ["lot.id", "lot.matiere_id"],
        ondelete=ondelete,
    )


class Lot(Base):
    """Un lot d'une matière (numéro de l'étiquette, ou `LOT-AAAA-NNNN` s'il est interne)."""

    __tablename__ = "lot"
    __table_args__ = (
        UniqueConstraint("id", "matiere_id"),
        UniqueConstraint("matiere_id", "numero"),
        CheckConstraint(r"numero <> '' AND numero !~ '\s'", name="numero_sans_blanc"),
        CheckConstraint("poids_bobine >= 0", name="poids_bobine_positif"),
        Index(None, "matiere_id", "entre_le"),
        index_recherche(),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    numero: Mapped[str] = mapped_column(String(L.NUMERO_LOT))
    interne: Mapped[bool] = colonne(defaut=False)
    fournisseur_id: Mapped[int | None] = mapped_column(fk("fournisseur.id"))
    entre_le: Mapped[date] = mapped_column(Date)
    poids_bobine: Mapped[Decimal] = colonne(MESURE.type_sql(), defaut=Decimal(0))
    poids_bobine_le: Mapped[date | None] = mapped_column(Date)
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)
    texte_recherche: Mapped[str] = recherche()

    matiere: Mapped[Matiere] = vers("Matiere")


class Solde(Base):
    """Le stock d'un lot dans un magasin : cache du journal, jamais négatif."""

    __tablename__ = "solde"
    __table_args__ = (
        CheckConstraint("quantite >= 0", name="positif"),
        Index("ix_solde_present", "magasin_id", "lot_id", postgresql_where=text("quantite > 0")),
    )
    __activite__ = True

    lot_id: Mapped[int] = mapped_column(fk("lot.id"), primary_key=True)
    magasin_id: Mapped[int] = mapped_column(fk("magasin.id"), primary_key=True)
    quantite: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    maj_le: Mapped[datetime] = instant(defaut=MAINTENANT)

    lot: Mapped[Lot] = vers("Lot")


_DOCUMENT = (
    "(document = 'reception' AND reception_id IS NOT NULL"
    " AND num_nonnulls(operation_id, inventaire_id) = 0)"
    " OR (document = 'ordre' AND type = 'SORTIE' AND ordre_id IS NOT NULL"
    " AND num_nonnulls(reception_id, operation_id, inventaire_id) = 0)"
    " OR (document = 'operation' AND operation_id IS NOT NULL"
    " AND num_nonnulls(reception_id, inventaire_id) = 0)"
    " OR (document = 'inventaire' AND inventaire_id IS NOT NULL AND type = 'AJUSTEMENT'"
    " AND num_nonnulls(reception_id, operation_id) = 0)"
    " OR (document = 'reprise' AND num_nonnulls(reception_id, operation_id, inventaire_id) = 0)"
)


class Mouvement(Base):
    """Une écriture du journal du stock : kg signés, prix au kg des entrées, cours figé."""

    __tablename__ = "mouvement"
    __table_args__ = (
        fk_lot(),
        CheckConstraint("date_effet >= DATE '2000-01-01'", name="date_plausible"),
        CheckConstraint("quantite <> 0", name="quantite_non_nulle"),
        CheckConstraint("prix >= 0", name="prix_positif"),
        CheckConstraint("cours IS NULL OR cours > 0", name="cours_positif"),
        CheckConstraint("devise <> 'MAD' OR cours IS NULL", name="cours_mad"),
        CheckConstraint(_DOCUMENT, name="document"),
        CheckConstraint(
            "type NOT IN ('SORTIE', 'RETOUR_MACHINE') OR ordre_id IS NOT NULL"
            " OR document = 'reprise'",
            name="ordre",
        ),
        CheckConstraint(
            "prix = 0 OR type IN ('OUVERTURE', 'RECEPTION', 'RETOUR_FOURNISSEUR', 'AJUSTEMENT')",
            name="prix_entree",
        ),
        Index(None, "matiere_id", "date_effet"),
        Index(None, "lot_id", "magasin_id", "date_effet"),
        Index(None, "date_effet"),
        Index(None, "ordre_id"),
        Index(None, "reception_id"),
        Index(None, "operation_id"),
        Index(None, "inventaire_id"),
        Index(None, "paire_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire_longue()
    date_effet: Mapped[date] = mapped_column(Date)
    saisi_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    type: Mapped[TypeMouvement] = mapped_column(enumeration(TypeMouvement, 20))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_id: Mapped[int] = mapped_column()
    magasin_id: Mapped[int] = mapped_column(fk("magasin.id"))
    quantite: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    devise: Mapped[str] = colonne(CHAR(L.CODE_DEVISE), fk("devise.code"), defaut="MAD")
    cours: Mapped[Decimal | None] = mapped_column(COURS.type_sql())
    document: Mapped[DocumentMouvement] = mapped_column(enumeration(DocumentMouvement, 12))
    reception_id: Mapped[int | None] = mapped_column(fk("reception.id"))
    ordre_id: Mapped[int | None] = mapped_column(fk("ordre.id"))
    operation_id: Mapped[int | None] = mapped_column(fk("operation.id"))
    inventaire_id: Mapped[int | None] = mapped_column(fk("inventaire.id"))
    document_numero: Mapped[str] = chaine(L.NUMERO_DOCUMENT)
    paire_id: Mapped[int | None] = mapped_column(BigInteger, fk("mouvement.id"))
    contrepasse_id: Mapped[int | None] = mapped_column(BigInteger, fk("mouvement.id"), unique=True)
    motif_id: Mapped[int | None] = mapped_column(fk("motif.id"))
    motif_texte: Mapped[str] = chaine(L.LIBELLE_MOTIF)
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)
    auteur_id: Mapped[int | None] = qui()

    lot: Mapped[Lot] = vers("Lot")
