"""Inventaires : en-tête, périmètre (critères, matières suspendues), lignes (MODELE-DONNEES § 3.7).

Repris de Gestion MP corrigé (étape 17) : un inventaire abandonné **ou annulé** (validé puis
défait, ajustements contre-passés) garde son numéro ; un lot trouvé au comptage n'est créé
qu'à la validation — jusque-là sa ligne porte sa matière et son numéro (`lot_id` vide, ou
`lot_interne` pour un numéro `LOT-AAAA-NNNN` donné à la validation).

Un inventaire ouvert par magasin : index unique partiel `uq_inventaire_ouvert_magasin` (le cas
« un inventaire global exclut tout » reste au service, sous le verrou INVENTAIRE_GLOBAL).
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, Date, Index, String, UniqueConstraint, text
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
from gestion_mp_pro.modeles.enums import CritereInventaire, StatutInventaire
from gestion_mp_pro.modeles.receptions import ANNULE_DATE
from gestion_mp_pro.modeles.stock import fk_lot
from gestion_mp_pro.modeles.types import QUANTITE, TAUX, UNITES, enumeration


class Inventaire(AvecVersion, Base):
    """Un inventaire, numéroté à l'ouverture (`INV-AAAA-NNNN`) ; jamais supprimé."""

    __tablename__ = "inventaire"
    __table_args__ = (
        CheckConstraint("tolerance BETWEEN 0 AND 1", name="tolerance_bornee"),
        CheckConstraint(
            "(statut IN ('valide', 'annule')) = (valide_le IS NOT NULL)", name="validation_date"
        ),
        CheckConstraint(
            ANNULE_DATE.format(statut="abandonne", colonne="abandonne_le"), name="abandon_date"
        ),
        CheckConstraint(
            ANNULE_DATE.format(statut="annule", colonne="annule_le"), name="annulation_date"
        ),
        Index(
            "uq_inventaire_ouvert_magasin",
            text("coalesce(magasin_id, 0)"),
            unique=True,
            postgresql_where=text("statut = 'ouvert'"),
        ),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str] = mapped_column(String(L.NUMERO), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE_INVENTAIRE, "Inventaire")
    statut: Mapped[StatutInventaire] = colonne(
        enumeration(StatutInventaire, 12), defaut=StatutInventaire.ouvert
    )
    date: Mapped[dt.date] = mapped_column(Date)
    magasin_id: Mapped[int | None] = mapped_column(fk("magasin.id"))
    tolerance: Mapped[Decimal] = colonne(TAUX.type_sql(), defaut=Decimal("0.02"))
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    valide_par_id: Mapped[int | None] = qui()
    valide_le: Mapped[datetime | None] = instant()
    abandonne_par_id: Mapped[int | None] = qui()
    abandonne_le: Mapped[datetime | None] = instant()
    abandon_motif: Mapped[str] = chaine(L.MOTIF)
    annule_par_id: Mapped[int | None] = qui()
    annule_le: Mapped[datetime | None] = instant()
    annulation_motif: Mapped[str] = chaine(L.MOTIF)

    criteres: Mapped[list[InventaireCritere]] = enfants("InventaireCritere")
    matieres: Mapped[list[InventaireMatiere]] = enfants("InventaireMatiere", "matiere_id")
    lignes: Mapped[list[InventaireLigne]] = enfants("InventaireLigne")


_UN_CRITERE = (
    "num_nonnulls(matiere_id, role_id, composition_id, classe_abc) = 1"
    " AND (genre = 'matiere') = (matiere_id IS NOT NULL)"
    " AND (genre = 'role') = (role_id IS NOT NULL)"
    " AND (genre = 'composition') = (composition_id IS NOT NULL)"
    " AND (genre = 'classe_abc') = (classe_abc IS NOT NULL)"
)


class InventaireCritere(Base):
    """Un critère du périmètre choisi à l'ouverture (matière, rôle, composition, classe ABC)."""

    __tablename__ = "inventaire_critere"
    __table_args__ = (
        CheckConstraint("classe_abc IN ('A', 'B', 'C')", name="classe_abc_valide"),
        CheckConstraint(_UN_CRITERE, name="un_critere"),
        Index(None, "inventaire_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    inventaire_id: Mapped[int] = mapped_column(fk("inventaire.id", ondelete="CASCADE"))
    genre: Mapped[CritereInventaire] = mapped_column(enumeration(CritereInventaire, 12))
    matiere_id: Mapped[int | None] = mapped_column(fk("matiere.id"))
    role_id: Mapped[int | None] = mapped_column(fk("role_nomenclature.id"))
    composition_id: Mapped[int | None] = mapped_column(fk("composition.id"))
    classe_abc: Mapped[str | None] = mapped_column(CHAR(1))


class InventaireMatiere(Base):
    """Une matière suspendue par l'inventaire (figée à l'ouverture : suspension limitée au
    périmètre, DECISIONS N3)."""

    __tablename__ = "inventaire_matiere"
    __table_args__ = (Index(None, "matiere_id"),)
    __activite__ = True

    inventaire_id: Mapped[int] = mapped_column(
        fk("inventaire.id", ondelete="CASCADE"), primary_key=True
    )
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"), primary_key=True)


class InventaireLigne(Base):
    """Un lot à compter dans un magasin : théorique, comptage, recomptage, justification."""

    __tablename__ = "inventaire_ligne"
    __table_args__ = (
        fk_lot(),
        UniqueConstraint("inventaire_id", "lot_id", "magasin_id"),
        CheckConstraint("theorique >= 0", name="theorique_positif"),
        CheckConstraint("compte >= 0", name="compte_positif"),
        CheckConstraint("nb_palettes >= 0", name="palettes_positives"),
        CheckConstraint("nb_bobines >= 0", name="bobines_positives"),
        CheckConstraint("second_compte >= 0", name="second_compte_positif"),
        CheckConstraint("second_compte IS NULL OR compte IS NOT NULL", name="second_apres_premier"),
        CheckConstraint(
            "lot_id IS NOT NULL OR lot_interne OR lot_numero <> ''", name="lot_designe"
        ),
        CheckConstraint("lot_id IS NOT NULL OR lot_trouve", name="lot_a_creer_trouve"),
        CheckConstraint("NOT lot_trouve OR theorique = 0", name="lot_trouve_sans_theorique"),
        Index(
            "uq_inventaire_ligne_lot_a_creer",
            "inventaire_id",
            "matiere_id",
            "lot_numero",
            "magasin_id",
            unique=True,
            postgresql_where=text("lot_id IS NULL AND NOT lot_interne"),
        ),
        Index(None, "lot_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    inventaire_id: Mapped[int] = mapped_column(fk("inventaire.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_id: Mapped[int | None] = mapped_column()
    lot_numero: Mapped[str] = chaine(L.NUMERO_LOT)
    lot_interne: Mapped[bool] = colonne(defaut=False)
    magasin_id: Mapped[int] = mapped_column(fk("magasin.id"))
    theorique: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    compte: Mapped[Decimal | None] = mapped_column(QUANTITE.type_sql())
    nb_palettes: Mapped[Decimal | None] = mapped_column(UNITES.type_sql())
    nb_bobines: Mapped[Decimal | None] = mapped_column(UNITES.type_sql())
    compte_par_id: Mapped[int | None] = qui()
    compte_le: Mapped[datetime | None] = instant()
    second_compte: Mapped[Decimal | None] = mapped_column(QUANTITE.type_sql())
    second_par_id: Mapped[int | None] = qui()
    second_le: Mapped[datetime | None] = instant()
    justification: Mapped[str] = chaine(L.COMMENTAIRE)
    lot_trouve: Mapped[bool] = colonne(defaut=False)
