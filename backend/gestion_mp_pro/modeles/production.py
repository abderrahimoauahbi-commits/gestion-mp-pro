"""Ordres de fabrication (← `bon_sortie`), qualités, lignes, prévu figé (MODELE-DONNEES § 3.5).

Une qualité ne figure qu'une fois par ordre (décision O2, étape 18 de Gestion MP). Le prévu
figé à la validation désigne les matières par leur **id** (`ordre_prevu`).
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Index, String, UniqueConstraint
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
    index_recherche,
    instant,
    qui,
    recherche,
)
from gestion_mp_pro.modeles.enums import StatutOrdre
from gestion_mp_pro.modeles.receptions import ANNULE_DATE, NUMERO_SI_VALIDE, VALIDE_DATE
from gestion_mp_pro.modeles.stock import fk_lot
from gestion_mp_pro.modeles.types import QUANTITE, SURFACE, TAUX, enumeration


class Ordre(AvecVersion, Base):
    """Un ordre de fabrication : les sorties vers les machines d'un jour (`OF-AAAA-NNNN`)."""

    __tablename__ = "ordre"
    __table_args__ = (
        CheckConstraint(NUMERO_SI_VALIDE, name="numero_statut"),
        CheckConstraint(VALIDE_DATE.format(colonne="valide_le"), name="validation_date"),
        CheckConstraint(
            ANNULE_DATE.format(statut="annule", colonne="annule_le"), name="annulation_date"
        ),
        CheckConstraint("prevu_fige = (taux_perte_fige IS NOT NULL)", name="prevu_fige"),
        CheckConstraint("taux_perte_fige BETWEEN 0 AND 1", name="taux_perte_borne"),
        Index(None, "statut", "date"),
        Index(None, "metier_id"),
        index_recherche(),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str | None] = mapped_column(String(L.NUMERO), unique=True)
    statut: Mapped[StatutOrdre] = colonne(
        enumeration(StatutOrdre, 12), defaut=StatutOrdre.brouillon
    )
    date: Mapped[dt.date] = mapped_column(Date)
    magasin_id: Mapped[int] = mapped_column(fk("magasin.id"))
    metier_id: Mapped[int | None] = mapped_column(fk("metier.id"))
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    valide_par_id: Mapped[int | None] = qui()
    valide_le: Mapped[datetime | None] = instant()
    annule_le: Mapped[datetime | None] = instant()
    annule_par_id: Mapped[int | None] = qui()
    annulation_motif: Mapped[str] = chaine(L.MOTIF)
    prevu_fige: Mapped[bool] = colonne(defaut=False)
    taux_perte_fige: Mapped[Decimal | None] = mapped_column(TAUX.type_sql())
    texte_recherche: Mapped[str] = recherche()

    qualites: Mapped[list[OrdreQualite]] = enfants("OrdreQualite")
    lignes: Mapped[list[OrdreLigne]] = enfants("OrdreLigne")
    prevus: Mapped[list[OrdrePrevu]] = enfants("OrdrePrevu", "matiere_id")


class OrdreQualite(Base):
    """Une qualité fabriquée par l'ordre et ses m² (← `bon_fabrication`)."""

    __tablename__ = "ordre_qualite"
    __table_args__ = (
        UniqueConstraint("ordre_id", "qualite_id"),
        CheckConstraint("m2 > 0", name="m2_positifs"),
        Index(None, "qualite_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    ordre_id: Mapped[int] = mapped_column(fk("ordre.id", ondelete="CASCADE"))
    qualite_id: Mapped[int] = mapped_column(fk("qualite.id"))
    m2: Mapped[Decimal] = mapped_column(SURFACE.type_sql())


class OrdreLigne(Base):
    """Un lot sorti vers les machines par l'ordre (← `bon_ligne`)."""

    __tablename__ = "ordre_ligne"
    __table_args__ = (
        fk_lot(),
        CheckConstraint("quantite > 0", name="quantite_positive"),
        Index(None, "ordre_id"),
        Index(None, "lot_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    ordre_id: Mapped[int] = mapped_column(fk("ordre.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_id: Mapped[int] = mapped_column()
    quantite: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())


class OrdrePrevu(Base):
    """Le prévu figé à la validation : kg hors perte par matière (← `theorique.fils`)."""

    __tablename__ = "ordre_prevu"
    __table_args__ = (CheckConstraint("kg_hors_perte >= 0", name="kg_positifs"),)
    __activite__ = True

    ordre_id: Mapped[int] = mapped_column(fk("ordre.id", ondelete="CASCADE"), primary_key=True)
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"), primary_key=True)
    kg_hors_perte: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())
