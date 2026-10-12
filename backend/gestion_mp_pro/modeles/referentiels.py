"""Référentiels : devises et cours, classification, rôles de nomenclature, codes douaniers,
magasins, postes de frais, motifs (MODELE-DONNEES § 3.2). Fournisseurs et matières :
`catalogue.py`.

La classification a une clé technique `id` : son `code` se renomme sans toucher aux matières
(plus d'`ON UPDATE CASCADE`, incohérence 22).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    AvecVersion,
    Base,
    chaine,
    cle_primaire,
    colonne,
    fk,
    instant,
    qui,
)
from gestion_mp_pro.modeles.enums import (
    CleRepartition,
    NatureFrais,
    Role,
    TypeMagasin,
    TypeMotif,
)
from gestion_mp_pro.modeles.types import COURS, TAUX, enumeration


class Devise(AvecVersion, Base):
    """Une devise et son cours du jour (MAD pour 1 unité) ; le dirham vaut toujours 1."""

    __tablename__ = "devise"
    __table_args__ = (
        CheckConstraint("code ~ '^[A-Z]{3}$'", name="code_iso"),
        CheckConstraint("cours > 0 AND cours <= 10000", name="cours_borne"),
        CheckConstraint("code <> 'MAD' OR cours = 1", name="mad_unite"),
        CheckConstraint("code <> 'MAD' OR actif", name="mad_actif"),
    )

    code: Mapped[str] = mapped_column(CHAR(L.CODE_DEVISE), primary_key=True)
    nom: Mapped[str] = chaine(L.NOM_DEVISE)
    cours: Mapped[Decimal] = mapped_column(COURS.type_sql())
    cours_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    actif: Mapped[bool] = colonne(defaut=True)


class DeviseCours(Base):
    """L'historique des cours saisis (un cours identique au précédent n'est pas réécrit)."""

    __tablename__ = "devise_cours"
    __table_args__ = (
        CheckConstraint("cours > 0", name="cours_positif"),
        Index(None, "devise", "saisi_le"),
    )

    id: Mapped[int] = cle_primaire()
    devise: Mapped[str] = mapped_column(CHAR(L.CODE_DEVISE), fk("devise.code"))
    cours: Mapped[Decimal] = mapped_column(COURS.type_sql())
    saisi_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()


class _Classification(AvecVersion):
    """Colonnes communes des quatre tables de classification."""

    id: Mapped[int] = cle_primaire()
    commentaire: Mapped[str] = colonne(Text, defaut="")
    actif: Mapped[bool] = colonne(defaut=True)


_CODE_NON_VIDE = "code <> ''"


class Composition(_Classification, Base):
    """La matière du fil : polypropylène, polyester, jute…"""

    __tablename__ = "composition"
    __table_args__ = (CheckConstraint(_CODE_NON_VIDE, name="code_non_vide"),)

    code: Mapped[str] = mapped_column(String(L.CODE_CLASSIFICATION), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE)
    famille: Mapped[str] = chaine(L.FAMILLE)
    composition_detaillee: Mapped[str] = chaine(L.COMPOSITION_DETAILLEE)


class TypeFil(_Classification, Base):
    """La façon dont le fil est travaillé : frisé, shrink, filament continu…"""

    __tablename__ = "type_fil"
    __table_args__ = (CheckConstraint(_CODE_NON_VIDE, name="code_non_vide"),)

    code: Mapped[str] = mapped_column(String(L.CODE_CLASSIFICATION), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE)


class Titrage(_Classification, Base):
    """La grosseur : 2900 Dtex, 1500 Deniers, 20/2 Nm."""

    __tablename__ = "titrage"
    __table_args__ = (CheckConstraint(_CODE_NON_VIDE, name="code_non_vide"),)

    code: Mapped[str] = mapped_column(String(L.CODE_TITRAGE), unique=True)
    valeur: Mapped[str] = chaine(L.VALEUR_TITRAGE)
    unite: Mapped[str] = chaine(L.UNITE_TITRAGE)


class UniteTitrage(AvecVersion, Base):
    """Une unité de titrage (Dtex, Deniers, Nm, Tex, Nec, lbs…), tenue par les achats et la
    direction (décision de Mohamed du 12/10/2026, révision 0008).

    Le `code` s'écrit comme dans les références (« Dtex », « lbs ») : un mot, unique sans tenir
    compte de la casse (index `uq_unite_titrage_code` sur `lower(code)`). `titrage.unite` reste
    un texte (pas de clé étrangère) : l'emploi d'une unité se compte sur ce texte.
    """

    __tablename__ = "unite_titrage"
    __table_args__ = (
        CheckConstraint("code <> '' AND code !~ '[[:space:]]'", name="code_un_mot"),
        CheckConstraint("ordre >= 0", name="ordre_positif"),
        Index("uq_unite_titrage_code", text("lower(code)"), unique=True),
    )

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.UNITE_TITRAGE))
    libelle: Mapped[str] = chaine(L.LIBELLE)
    ordre: Mapped[int] = colonne(Integer, defaut=0)
    actif: Mapped[bool] = colonne(defaut=True)


class Couleur(_Classification, Base):
    """Une couleur de fil."""

    __tablename__ = "couleur"
    __table_args__ = (CheckConstraint(_CODE_NON_VIDE, name="code_non_vide"),)

    code: Mapped[str] = mapped_column(String(L.CODE_COULEUR), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE)
    famille: Mapped[str] = chaine(L.FAMILLE)


class RoleNomenclature(AvecVersion, Base):
    """Poil, Chaîne, Trame… ; Cuir, Franges et Ruban se comptent au mètre (`lineaire`) ;
    `version` (révision 0004) : la route 59 la contrôle."""

    __tablename__ = "role_nomenclature"
    __table_args__ = (
        CheckConstraint("NOT lineaire OR de_base", name="lineaire_de_base"),
        CheckConstraint("ordre >= 0", name="ordre_positif"),
    )

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_ROLE), unique=True)
    lineaire: Mapped[bool] = colonne(defaut=False)
    de_base: Mapped[bool] = colonne(defaut=False)
    ordre: Mapped[int] = colonne(Integer, defaut=0)


class CodeDouanier(AvecVersion, Base):
    """Un code douanier et son taux de droits (fraction)."""

    __tablename__ = "code_douanier"
    __table_args__ = (CheckConstraint("taux_droits BETWEEN 0 AND 1", name="taux_borne"),)

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_DOUANIER), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE_DOUANIER)
    taux_droits: Mapped[Decimal] = colonne(TAUX.type_sql(), defaut=Decimal(0))
    actif: Mapped[bool] = colonne(defaut=True)


class Magasin(AvecVersion, Base):
    """Un magasin courant ou une quarantaine ; désactivé, jamais supprimé."""

    __tablename__ = "magasin"

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_MAGASIN), unique=True)
    nom: Mapped[str] = chaine(L.NOM_MAGASIN)
    type: Mapped[TypeMagasin] = colonne(
        enumeration(TypeMagasin, 16), defaut=TypeMagasin.stock_courant
    )
    contenu: Mapped[str] = chaine(L.CONTENU_MAGASIN)
    actif: Mapped[bool] = colonne(defaut=True)


class PosteFrais(AvecVersion, Base):
    """Un poste de frais d'importation ; les postes `systeme` ne changent pas de nature."""

    __tablename__ = "poste_frais"
    __table_args__ = (
        CheckConstraint("ordre BETWEEN 0 AND 999", name="ordre_borne"),
        CheckConstraint("nature <> 'tva' OR recuperable", name="tva_recuperable"),
    )

    id: Mapped[int] = cle_primaire()
    code: Mapped[str] = mapped_column(String(L.CODE_POSTE), unique=True)
    libelle: Mapped[str] = chaine(L.LIBELLE_POSTE)
    recuperable: Mapped[bool] = colonne(defaut=False)
    nature: Mapped[NatureFrais] = colonne(enumeration(NatureFrais, 12), defaut=NatureFrais.autre)
    entre_valeur_douane: Mapped[bool] = colonne(defaut=False)
    cle: Mapped[CleRepartition] = colonne(
        enumeration(CleRepartition, 8), defaut=CleRepartition.valeur
    )
    ordre: Mapped[int] = colonne(SmallInteger, defaut=0)
    systeme: Mapped[bool] = colonne(defaut=False)


class Motif(Base):
    """Un motif de mouvement (liste semée, non modifiable par l'écran) et son code R1–R6.

    `impose_role` : rôle exigé en plus de la direction (« Libération de quarantaine » : achats).
    « Refus après quarantaine » garde R3, comme « Non-conformité qualité » (incohérence 31).
    """

    __tablename__ = "motif"
    __table_args__ = (
        CheckConstraint("code_r ~ '^R[1-6]$'", name="code_r_format"),
        CheckConstraint("ordre >= 0", name="ordre_positif"),
        UniqueConstraint("type_operation", "libelle"),
    )

    id: Mapped[int] = cle_primaire()
    type_operation: Mapped[TypeMotif] = mapped_column(enumeration(TypeMotif, 20))
    libelle: Mapped[str] = mapped_column(String(L.LIBELLE_MOTIF))
    code_r: Mapped[str | None] = mapped_column(CHAR(2))
    ordre: Mapped[int] = colonne(SmallInteger, defaut=0)
    impose_role: Mapped[Role | None] = mapped_column(enumeration(Role, L.ROLE))
