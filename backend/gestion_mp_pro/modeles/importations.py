"""Dossiers d'importation : un dossier = une facture = une livraison (MODELE-DONNEES § 3.8).

- Numéro `NN/AA` de la maison : `annee` + `rang` pour un numéro automatique (unique) ; un
  numéro saisi à la main est réservé aux dossiers `saisi_a_la_main` (ou `ANC-…` repris).
- Un dossier s'annule (statut), il ne se supprime plus : la série DOS ne se troue pas. Un
  dossier annulé libère sa facture (index unique partiel) ; ses marchandises doivent être
  détachées de leurs lignes reçues pour qu'un nouveau dossier les reprenne (voir S1.md).
- `cours_origine = 'clos_au_jour'` dit qu'un cours vide a reçu le cours du jour à la clôture
  (étape 16 de Gestion MP, `cours_fige_cloture`) : la réouverture le rend vide.
- Un frais rattaché à une marchandise la prend dans **son** dossier (FK composite).
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Index,
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
    enfants,
    fk,
    index_recherche,
    instant,
    qui,
    recherche,
)
from gestion_mp_pro.modeles.enums import OrigineCours, OriginePart, StatutDossier
from gestion_mp_pro.modeles.receptions import ANNULE_DATE
from gestion_mp_pro.modeles.stock import fk_lot
from gestion_mp_pro.modeles.types import COURS, MONTANT, QUANTITE, TAUX_FRAIS, enumeration


class Dossier(AvecVersion, Base):
    """Un dossier d'importation : la marchandise d'une facture et les frais payés pour elle."""

    __tablename__ = "dossier"
    __table_args__ = (
        UniqueConstraint("annee", "rang"),
        CheckConstraint(
            "numero ~ '^[0-9]{1,3}/[0-9]{2}$' OR numero ~ '^ANC-'", name="numero_format"
        ),
        CheckConstraint("(annee IS NULL) = (rang IS NULL)", name="annee_et_rang"),
        CheckConstraint("saisi_a_la_main OR rang IS NOT NULL", name="numero_automatique"),
        CheckConstraint("annee BETWEEN 2000 AND 2100", name="annee_plausible"),
        CheckConstraint("rang BETWEEN 1 AND 999", name="rang_borne"),
        CheckConstraint(ANNULE_DATE.format(statut="clos", colonne="clos_le"), name="cloture_date"),
        CheckConstraint(
            ANNULE_DATE.format(statut="annule", colonne="annule_le"), name="annulation_date"
        ),
        Index(None, "statut"),
        Index(
            "uq_dossier_facture",
            "facture_id",
            unique=True,
            postgresql_where=text("statut <> 'annule'"),
        ),
        index_recherche(),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str] = mapped_column(String(L.NUMERO_DOSSIER), unique=True)
    annee: Mapped[int | None] = mapped_column(SmallInteger)
    rang: Mapped[int | None] = mapped_column()
    libelle: Mapped[str] = chaine(L.LIBELLE_DOSSIER)
    date_arrivee: Mapped[dt.date | None] = mapped_column(Date)
    banque: Mapped[str] = chaine(L.BANQUE_DOSSIER)
    statut: Mapped[StatutDossier] = colonne(
        enumeration(StatutDossier, 12), defaut=StatutDossier.ouvert
    )
    clos_le: Mapped[datetime | None] = instant()
    clos_par_id: Mapped[int | None] = qui()
    annule_le: Mapped[datetime | None] = instant()
    annule_par_id: Mapped[int | None] = qui()
    annulation_motif: Mapped[str] = chaine(L.MOTIF)
    commentaire: Mapped[str] = colonne(Text, defaut="")
    facture_id: Mapped[int | None] = mapped_column(fk("facture.id"))
    saisi_a_la_main: Mapped[bool] = colonne(defaut=False)
    local_confirme: Mapped[bool] = colonne(defaut=False)
    texte_recherche: Mapped[str] = recherche()
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)

    lignes: Mapped[list[DossierLigne]] = enfants("DossierLigne")
    frais: Mapped[list[DossierFrais]] = enfants("DossierFrais")


class DossierLigne(Base):
    """Une marchandise du dossier : kg, valeur en devise (pesé × prix), cours et son origine."""

    __tablename__ = "dossier_ligne"
    __table_args__ = (
        fk_lot(),
        UniqueConstraint("id", "dossier_id"),
        CheckConstraint("quantite_kg >= 0", name="quantite_positive"),
        CheckConstraint("valeur_devise >= 0", name="valeur_positive"),
        CheckConstraint("cours > 0", name="cours_positif"),
        CheckConstraint("devise <> 'MAD' OR cours IS NULL", name="cours_mad"),
        CheckConstraint("(cours IS NULL) = (cours_origine IS NULL)", name="cours_origine"),
        Index(None, "dossier_id"),
        Index(None, "matiere_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    dossier_id: Mapped[int] = mapped_column(fk("dossier.id", ondelete="CASCADE"))
    reception_ligne_id: Mapped[int | None] = mapped_column(fk("reception_ligne.id"), unique=True)
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_id: Mapped[int | None] = mapped_column()
    fournisseur_id: Mapped[int | None] = mapped_column(fk("fournisseur.id"))
    quantite_kg: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    valeur_devise: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    devise: Mapped[str] = colonne(CHAR(L.CODE_DEVISE), fk("devise.code"), defaut="MAD")
    cours: Mapped[Decimal | None] = mapped_column(COURS.type_sql())
    cours_origine: Mapped[OrigineCours | None] = mapped_column(enumeration(OrigineCours, 16))
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)


class DossierFrais(AvecVersion, Base):
    """Un frais du dossier (← `dossier_charge`) : montant en MAD, négatif pour un avoir.

    `taux` (révision 0006, lot TAUX-FRAIS) : le pourcentage que l'écran a appliqué à sa base
    pour proposer le montant (20 % de TVA, 2,5 % de droits…), gardé pour mémoire ; le montant
    reste celui saisi (la douane arrondit), il n'est **jamais** recalculé depuis le taux.
    """

    __tablename__ = "dossier_frais"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ligne_id", "dossier_id"],
            ["dossier_ligne.id", "dossier_ligne.dossier_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("montant <> 0", name="montant_non_nul"),
        CheckConstraint("taux IS NULL OR (taux > 0 AND taux <= 100)", name="taux_borne"),
        CheckConstraint("payee_par_id IS NULL OR payee_le IS NOT NULL", name="reglement"),
        Index(None, "dossier_id"),
        Index(None, "poste_id"),
        Index(
            "ix_dossier_frais_echeance_due", "echeance", postgresql_where=text("payee_le IS NULL")
        ),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    dossier_id: Mapped[int] = mapped_column(fk("dossier.id", ondelete="CASCADE"))
    poste_id: Mapped[int] = mapped_column(fk("poste_frais.id"))
    montant: Mapped[Decimal] = mapped_column(MONTANT.type_sql())
    taux: Mapped[Decimal | None] = mapped_column(TAUX_FRAIS.type_sql())
    ligne_id: Mapped[int | None] = mapped_column()
    piece: Mapped[str] = chaine(L.PIECE)
    prestataire: Mapped[str] = chaine(L.PRESTATAIRE)
    date_piece: Mapped[dt.date | None] = mapped_column(Date)
    echeance: Mapped[dt.date | None] = mapped_column(Date)
    payee_le: Mapped[dt.date | None] = mapped_column(Date)
    payee_par_id: Mapped[int | None] = qui()
    commentaire: Mapped[str] = chaine(L.COMMENTAIRE)

    parts: Mapped[list[DossierFraisPart]] = enfants("DossierFraisPart", "ligne_id")


class DossierFraisPart(Base):
    """La part figée d'un frais sur une marchandise (Σ parts = montant, aux plus forts restes)."""

    __tablename__ = "dossier_frais_part"
    __table_args__ = (Index(None, "ligne_id"),)
    __activite__ = True

    frais_id: Mapped[int] = mapped_column(
        fk("dossier_frais.id", ondelete="CASCADE"), primary_key=True
    )
    ligne_id: Mapped[int] = mapped_column(fk("dossier_ligne.id"), primary_key=True)
    montant: Mapped[Decimal] = mapped_column(MONTANT.type_sql())
    origine: Mapped[OriginePart] = mapped_column(enumeration(OriginePart, 16))
    figee_le: Mapped[datetime] = instant(defaut=MAINTENANT)
