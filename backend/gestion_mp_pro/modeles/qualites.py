"""Qualités, poids au m², saisonnalité, recettes et leurs versions, plan versionné (§ 3.2.7–3.2.8).

Les versions désignent les matières par leur **id** (plus par la référence, renommable :
incohérence 18) et sont écrites explicitement par `services/qualites.enregistrer_version(...)`
dans la transaction du geste (plus d'écouteur caché). « 100 % par rôle à 0,01 point » reste une
règle du service et du contrôle C01 (une contrainte d'agrégat n'a pas sa place en base).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    AvecModification,
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
from gestion_mp_pro.modeles.enums import OrigineVersion
from gestion_mp_pro.modeles.types import COEFFICIENT, MESURE, POURCENTAGE, SURFACE, enumeration

_MOIS = "mois BETWEEN 1 AND 12"
_COEFFICIENT = "coefficient BETWEEN 0 AND 20"
_POURCENTAGE = "pourcentage BETWEEN 0 AND 100"
_MOTIF_DE_RESTAURATION = "origine <> 'restauration' OR motif <> ''"


class Qualite(AvecVersion, AvecModification, Base):
    """Une qualité de tapis ; `base_mensuelle` : valeur courante (historique : plan_version)."""

    __tablename__ = "qualite"
    __table_args__ = (
        CheckConstraint("base_mensuelle >= 0", name="base_positive"),
        index_recherche(),
    )

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_QUALITE), unique=True)
    nom: Mapped[str] = chaine(L.NOM_QUALITE)
    base_mensuelle: Mapped[Decimal] = colonne(SURFACE.type_sql(), defaut=Decimal(0))
    actif: Mapped[bool] = colonne(defaut=True)
    texte_recherche: Mapped[str] = recherche()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)

    poids: Mapped[list[QualitePoids]] = enfants("QualitePoids", "role_id")
    saisons: Mapped[list[QualiteSaison]] = enfants("QualiteSaison", "mois")
    recettes: Mapped[list[Recette]] = enfants("Recette", "matiere_id")


class QualitePoids(Base):
    """Le poids au m² d'un rôle dans une qualité (kg/m², ou ml/m² pour un rôle linéaire)."""

    __tablename__ = "qualite_poids"
    __table_args__ = (CheckConstraint("poids >= 0", name="poids_positif"),)

    qualite_id: Mapped[int] = mapped_column(fk("qualite.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(fk("role_nomenclature.id"), primary_key=True)
    poids: Mapped[Decimal] = colonne(MESURE.type_sql(), defaut=Decimal(0))


class QualiteSaison(Base):
    """Le coefficient de saisonnalité d'un mois (0 à 20)."""

    __tablename__ = "qualite_saison"
    __table_args__ = (
        CheckConstraint(_MOIS, name="mois_valide"),
        CheckConstraint(_COEFFICIENT, name="coefficient_borne"),
    )

    qualite_id: Mapped[int] = mapped_column(fk("qualite.id", ondelete="CASCADE"), primary_key=True)
    mois: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    coefficient: Mapped[Decimal] = colonne(COEFFICIENT.type_sql(), defaut=Decimal(1))


class Recette(Base):
    """La part d'une matière dans son rôle pour une qualité (0 à 100 %)."""

    __tablename__ = "recette"
    __table_args__ = (
        CheckConstraint(_POURCENTAGE, name="pourcentage_borne"),
        Index(None, "matiere_id"),
    )

    qualite_id: Mapped[int] = mapped_column(fk("qualite.id", ondelete="CASCADE"), primary_key=True)
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"), primary_key=True)
    pourcentage: Mapped[Decimal] = colonne(POURCENTAGE.type_sql(), defaut=Decimal(0))


class RecetteVersion(Base):
    """Une version de la recette d'une qualité, numérotée 1, 2, 3… et datée."""

    __tablename__ = "recette_version"
    __table_args__ = (
        UniqueConstraint("qualite_id", "numero"),
        CheckConstraint("numero >= 1", name="numero_positif"),
        CheckConstraint(_MOTIF_DE_RESTAURATION, name="motif_de_restauration"),
        Index(None, "qualite_id", "valide_depuis"),
    )

    id: Mapped[int] = cle_primaire()
    qualite_id: Mapped[int] = mapped_column(fk("qualite.id"))
    numero: Mapped[int] = mapped_column(Integer)
    valide_depuis: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    origine: Mapped[OrigineVersion] = colonne(
        enumeration(OrigineVersion, 16), defaut=OrigineVersion.saisie
    )
    restauree_de_id: Mapped[int | None] = mapped_column(fk("recette_version.id"))
    motif: Mapped[str] = chaine(L.MOTIF)
    poids_connus: Mapped[bool] = colonne(defaut=True)

    lignes: Mapped[list[RecetteVersionLigne]] = enfants("RecetteVersionLigne", "matiere_id")
    poids: Mapped[list[RecetteVersionPoids]] = enfants("RecetteVersionPoids", "role_id")


class RecetteVersionLigne(Base):
    """Une matière de la version, avec son rôle à cette date."""

    __tablename__ = "recette_version_ligne"
    __table_args__ = (CheckConstraint(_POURCENTAGE, name="pourcentage_borne"),)

    version_id: Mapped[int] = mapped_column(
        fk("recette_version.id", ondelete="CASCADE"), primary_key=True
    )
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(fk("role_nomenclature.id"))
    pourcentage: Mapped[Decimal] = mapped_column(POURCENTAGE.type_sql())


class RecetteVersionPoids(Base):
    """Le poids au m² d'un rôle avec cette version."""

    __tablename__ = "recette_version_poids"
    __table_args__ = (CheckConstraint("poids >= 0", name="poids_positif"),)

    version_id: Mapped[int] = mapped_column(
        fk("recette_version.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(fk("role_nomenclature.id"), primary_key=True)
    poids: Mapped[Decimal] = mapped_column(MESURE.type_sql())


class PlanVersion(Base):
    """Une version du plan d'une qualité (base, en service, saisonnalité) : le passé est jugé
    sur la version en vigueur à sa date (`plan_en_vigueur`)."""

    __tablename__ = "plan_version"
    __table_args__ = (
        CheckConstraint("base_mensuelle >= 0", name="base_positive"),
        CheckConstraint(_MOTIF_DE_RESTAURATION, name="motif_de_restauration"),
        Index(None, "qualite_id", "valide_depuis"),
    )

    id: Mapped[int] = cle_primaire()
    qualite_id: Mapped[int] = mapped_column(fk("qualite.id"))
    valide_depuis: Mapped[datetime] = instant(defaut=MAINTENANT)
    base_mensuelle: Mapped[Decimal] = colonne(SURFACE.type_sql(), defaut=Decimal(0))
    en_service: Mapped[bool] = colonne(defaut=True)
    par_id: Mapped[int | None] = qui()
    origine: Mapped[OrigineVersion] = colonne(
        enumeration(OrigineVersion, 16), defaut=OrigineVersion.saisie
    )
    motif: Mapped[str] = chaine(L.MOTIF)
    journal_id: Mapped[int | None] = mapped_column(BigInteger, fk("journal.id"))

    saisons: Mapped[list[PlanVersionSaison]] = enfants("PlanVersionSaison", "mois")


class PlanVersionSaison(Base):
    """Le coefficient d'un mois dans une version du plan."""

    __tablename__ = "plan_version_saison"
    __table_args__ = (
        CheckConstraint(_MOIS, name="mois_valide"),
        CheckConstraint(_COEFFICIENT, name="coefficient_borne"),
    )

    version_id: Mapped[int] = mapped_column(
        fk("plan_version.id", ondelete="CASCADE"), primary_key=True
    )
    mois: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    coefficient: Mapped[Decimal] = mapped_column(COEFFICIENT.type_sql())
