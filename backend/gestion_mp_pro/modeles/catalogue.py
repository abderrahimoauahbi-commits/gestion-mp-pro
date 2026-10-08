"""Catalogue : fournisseurs et matières (MODELE-DONNEES § 3.2.4, § 3.2.6).

« Rôle linéaire ⇒ densité > 0 » est tenu par le service **et** par la contrainte de
déclenchement `tr_matiere_lineaire_densite` (migration 0001, `DEFERRABLE INITIALLY DEFERRED`) :
un CHECK ne lit pas une autre table (incohérence 20).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, CheckConstraint, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from gestion_mp_pro.modeles.referentiels import RoleNomenclature

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    AvecModification,
    AvecVersion,
    Base,
    chaine,
    cle_primaire,
    colonne,
    fk,
    index_recherche,
    instant,
    recherche,
    vers,
)
from gestion_mp_pro.modeles.enums import UnitePrix
from gestion_mp_pro.modeles.types import (
    MESURE,
    MOIS,
    PRIORITE,
    PRIX,
    QUANTITE,
    UNITES,
    enumeration,
)


class Fournisseur(AvecVersion, AvecModification, Base):
    """Un fournisseur ; `pays` en majuscules (« MAROC » = local)."""

    __tablename__ = "fournisseur"
    __table_args__ = (
        CheckConstraint("pays = upper(pays)", name="pays_majuscules"),
        CheckConstraint("delai_jours > 0", name="delai_positif"),
        CheckConstraint("couverture_commande_jours >= 0", name="couverture_positive"),
        CheckConstraint("delai_paiement_jours >= 0", name="delai_paiement_positif"),
        index_recherche(),
    )

    id: Mapped[int] = cle_primaire()
    nom: Mapped[str] = mapped_column(String(L.NOM_FOURNISSEUR), unique=True)
    code: Mapped[str] = chaine(L.CODE_FOURNISSEUR)
    pays: Mapped[str] = chaine(L.PAYS)
    contact: Mapped[str] = chaine(L.CONTACT)
    telephone: Mapped[str] = chaine(L.TELEPHONE)
    email: Mapped[str] = chaine(L.EMAIL_FOURNISSEUR)
    devise: Mapped[str] = colonne(CHAR(L.CODE_DEVISE), fk("devise.code"), defaut="MAD")
    delai_jours: Mapped[int] = colonne(Integer, defaut=60)
    couverture_commande_jours: Mapped[int] = colonne(Integer, defaut=0)
    mode_paiement: Mapped[str] = chaine(L.MODE_PAIEMENT)
    delai_paiement_jours: Mapped[int] = colonne(Integer, defaut=0)
    conditions_paiement: Mapped[str] = chaine(L.CONDITIONS_PAIEMENT)
    incoterm: Mapped[str] = chaine(L.INCOTERM)
    port_chargement: Mapped[str] = chaine(L.PORT)
    banque: Mapped[str] = chaine(L.BANQUE)
    notes: Mapped[str] = colonne(Text, defaut="")
    actif: Mapped[bool] = colonne(defaut=True)
    texte_recherche: Mapped[str] = recherche()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)


class Matiere(AvecVersion, AvecModification, Base):
    """Une matière première (← `article`) ; stock toujours en kg, prix au kg ou au mètre."""

    __tablename__ = "matiere"
    __table_args__ = (
        UniqueConstraint("id", "role_id"),
        CheckConstraint("unite_prix = 'kg' OR densite > 0", name="prix_au_metre"),
        CheckConstraint("densite >= 0", name="densite_positive"),
        CheckConstraint("prix >= 0", name="prix_positif"),
        CheckConstraint("lower(unite_achat) <> 'ml'", name="unite_achat_pas_ml"),
        CheckConstraint("contenance_achat > 0", name="contenance_positive"),
        CheckConstraint("minimum_commande >= 0", name="minimum_positif"),
        CheckConstraint("poids_bobine >= 0", name="poids_bobine_positif"),
        CheckConstraint("bobines_palette >= 0", name="bobines_palette_positives"),
        CheckConstraint("stock_min >= 0", name="stock_min_positif"),
        CheckConstraint("couv_min_mois >= 0", name="couv_min_positive"),
        CheckConstraint("priorite_equiv BETWEEN 0 AND 100", name="priorite_bornee"),
        Index(None, "fournisseur_id"),
        Index(None, "role_id"),
        Index(None, "groupe_equiv"),
        index_recherche(),
    )

    id: Mapped[int] = cle_primaire()
    reference: Mapped[str] = mapped_column(String(L.REFERENCE), unique=True)
    designation: Mapped[str] = chaine(L.DESIGNATION)
    role_id: Mapped[int] = mapped_column(fk("role_nomenclature.id"))
    composition_id: Mapped[int | None] = mapped_column(fk("composition.id"))
    type_fil_id: Mapped[int | None] = mapped_column(fk("type_fil.id"))
    titrage_id: Mapped[int | None] = mapped_column(fk("titrage.id"))
    couleur_id: Mapped[int | None] = mapped_column(fk("couleur.id"))
    couleur_code: Mapped[str] = chaine(L.COULEUR_CODE)
    unite_prix: Mapped[UnitePrix] = colonne(enumeration(UnitePrix, 2), defaut=UnitePrix.kg)
    densite: Mapped[Decimal] = colonne(MESURE.type_sql(), defaut=Decimal(0))
    fournisseur_id: Mapped[int | None] = mapped_column(fk("fournisseur.id"))
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    devise: Mapped[str] = colonne(CHAR(L.CODE_DEVISE), fk("devise.code"), defaut="MAD")
    unite_achat: Mapped[str] = chaine(L.UNITE_ACHAT, "kg")
    contenance_achat: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(1))
    minimum_commande: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    poids_bobine: Mapped[Decimal] = colonne(MESURE.type_sql(), defaut=Decimal(0))
    bobines_palette: Mapped[Decimal] = colonne(UNITES.type_sql(), defaut=Decimal(0))
    stock_min: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    couv_min_mois: Mapped[Decimal] = colonne(MOIS.type_sql(), defaut=Decimal(0))
    groupe_equiv: Mapped[str] = chaine(L.GROUPE_EQUIV)
    priorite_equiv: Mapped[Decimal | None] = mapped_column(PRIORITE.type_sql())
    code_douanier_id: Mapped[int | None] = mapped_column(fk("code_douanier.id"))
    actif: Mapped[bool] = colonne(defaut=True)
    texte_recherche: Mapped[str] = recherche()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)

    role: Mapped[RoleNomenclature] = vers("RoleNomenclature")
    fournisseur: Mapped[Fournisseur | None] = vers("Fournisseur")
