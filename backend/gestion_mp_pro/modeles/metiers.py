"""Métiers à tisser, étages, fil monté, événements de montage (MODELE-DONNEES § 3.2.10).

Un fil monté est en stock « en machine » : compté et valorisé. Le montage d'un étage depuis
le téléphone est protégé par la `version` de son étage (deux téléphones : un seul passe).
L'étage d'un montage existe forcément : FK composite `(metier_id, etage)` → `metier_etage`
(le contrôle C24 devient garanti par la base).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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
from gestion_mp_pro.modeles.types import (
    BOBINES_PAR_METRE,
    LONGUEUR,
    POURCENTAGE,
    QUANTITE,
)


class Metier(AvecVersion, Base):
    """Un métier à tisser : ses étages, la laize d'un étage, ses bobines par mètre de laize."""

    __tablename__ = "metier"
    __table_args__ = (
        CheckConstraint("laize >= 0", name="laize_positive"),
        CheckConstraint("bobines_par_metre >= 0", name="bobines_par_metre_positives"),
        CheckConstraint("etages BETWEEN 1 AND 40", name="etages_bornes"),
    )

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_METIER), unique=True)
    nom: Mapped[str] = chaine(L.NOM_METIER)
    laize: Mapped[Decimal] = colonne(LONGUEUR.type_sql(), defaut=Decimal("4.2"))
    bobines_par_metre: Mapped[Decimal] = colonne(BOBINES_PAR_METRE.type_sql(), defaut=Decimal(0))
    etages: Mapped[int] = colonne(SmallInteger, defaut=6)
    actif: Mapped[bool] = colonne(defaut=True)
    commentaire: Mapped[str] = colonne(Text, defaut="")

    etages_montes: Mapped[list[MetierEtage]] = enfants("MetierEtage", "etage")
    montages: Mapped[list[Montage]] = enfants("Montage")


class MetierEtage(AvecVersion, Base):
    """Un étage d'un métier (lignes 1..etages) : verrou optimiste de son montage."""

    __tablename__ = "metier_etage"
    __table_args__ = (CheckConstraint("etage BETWEEN 1 AND 40", name="etage_borne"),)

    metier_id: Mapped[int] = mapped_column(fk("metier.id", ondelete="CASCADE"), primary_key=True)
    etage: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    monte_le: Mapped[datetime | None] = instant()
    monte_par_id: Mapped[int | None] = qui()


class Montage(Base):
    """Un fil monté sur un étage (← `fil_monte`) : mètres et remplissage des bobines
    (`pourcentage`)."""

    __tablename__ = "montage"
    __table_args__ = (
        ForeignKeyConstraint(
            ["metier_id", "etage"],
            ["metier_etage.metier_id", "metier_etage.etage"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("metier_id", "etage", "matiere_id"),
        CheckConstraint("metres >= 0", name="metres_positifs"),
        CheckConstraint("pourcentage BETWEEN 0 AND 100", name="pourcentage_borne"),
        Index(None, "matiere_id"),
    )

    id: Mapped[int] = cle_primaire()
    metier_id: Mapped[int] = mapped_column(fk("metier.id", ondelete="CASCADE"))
    etage: Mapped[int] = mapped_column(SmallInteger)
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    metres: Mapped[Decimal] = colonne(LONGUEUR.type_sql(), defaut=Decimal(0))
    pourcentage: Mapped[Decimal] = colonne(POURCENTAGE.type_sql(), defaut=Decimal(100))
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)


class MontageEvenement(Base):
    """Un montage confirmé : lignes de l'étage avant/après, effet sur le stock, alerte 30 j."""

    __tablename__ = "montage_evenement"
    __table_args__ = (
        CheckConstraint("etage BETWEEN 1 AND 40", name="etage_borne"),
        Index(None, "metier_id", "quand"),
    )

    id: Mapped[int] = cle_primaire()
    metier_id: Mapped[int] = mapped_column(fk("metier.id"))
    etage: Mapped[int | None] = mapped_column(SmallInteger)
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    avant: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    apres: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    effet_kg: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    alerte: Mapped[str] = chaine(L.ALERTE)
