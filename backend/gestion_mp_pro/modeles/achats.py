"""Achats : bons de commande, lignes, versions parties, décisions, factures (MODELE-DONNEES § 3.4).

- `commande.parti` (colonne générée) dit si le bon est parti (numéroté) : il lève le double sens
  de `a_approuver` (incohérence 10).
- `commande_version(_ligne)` remplace le JSON `version_approuvee` et garde **toutes** les
  versions parties ; la version partie est la plus récente.
- `commande_decision` reçoit ce que Gestion MP rangeait dans son journal (renvoi et motif,
  montant avant → après).
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
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
from gestion_mp_pro.modeles.enums import (
    DecisionCommande,
    MotifVersionCommande,
    OrigineSolde,
    StatutCommande,
)
from gestion_mp_pro.modeles.types import COURS, MONTANT, PRIX, QUANTITE, enumeration

JALONS = ("proforma_le", "acompte_le", "embarquee_le", "au_port_le", "dedouanee_le")
"""Jalons constatés d'un bon (avec `arrivee_usine_le`), jamais avant la date du bon."""


def _jalons() -> tuple[CheckConstraint, ...]:
    """Un CHECK par jalon : pas avant la date du bon."""
    return tuple(
        CheckConstraint(f"{j} >= date_commande", name=f"{j}_apres_commande")
        for j in (*JALONS, "arrivee_usine_le")
    )


class Commande(AvecVersion, AvecModification, Base):
    """Un bon de commande fournisseur : numéroté à l'envoi (`BC-AAAA-NNNN`)."""

    __tablename__ = "commande"
    __table_args__ = (
        CheckConstraint("statut <> 'brouillon' OR numero IS NULL", name="numero_statut"),
        CheckConstraint(
            "statut NOT IN ('envoyee', 'confirmee', 'soldee') OR numero IS NOT NULL",
            name="numero_parti",
        ),
        CheckConstraint("date_livraison_prevue >= date_commande", name="livraison_apres"),
        CheckConstraint("cours > 0", name="cours_positif"),
        CheckConstraint("devise <> 'MAD' OR cours IS NULL", name="cours_mad"),
        CheckConstraint("(cours IS NULL) = (cours_fige_le IS NULL)", name="cours_fige"),
        CheckConstraint("montant_approuve > 0", name="montant_approuve_positif"),
        CheckConstraint(
            "(statut IN ('soldee', 'annulee')) = (solde_origine IS NOT NULL)", name="solde"
        ),
        *_jalons(),
        Index(None, "statut"),
        Index(None, "fournisseur_id"),
        index_recherche(),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str | None] = mapped_column(String(L.NUMERO), unique=True)
    parti: Mapped[bool] = mapped_column(Boolean, Computed("numero IS NOT NULL", persisted=True))
    fournisseur_id: Mapped[int] = mapped_column(fk("fournisseur.id"))
    statut: Mapped[StatutCommande] = colonne(
        enumeration(StatutCommande, 12), defaut=StatutCommande.brouillon
    )
    date_commande: Mapped[dt.date] = mapped_column(Date)
    date_livraison_prevue: Mapped[dt.date | None] = mapped_column(Date)
    devise: Mapped[str] = mapped_column(CHAR(L.CODE_DEVISE), fk("devise.code"))
    cours: Mapped[Decimal | None] = mapped_column(COURS.type_sql())
    cours_fige_le: Mapped[datetime | None] = instant()
    observations: Mapped[str] = colonne(Text, defaut="")
    proforma_le: Mapped[dt.date | None] = mapped_column(Date)
    acompte_le: Mapped[dt.date | None] = mapped_column(Date)
    embarquee_le: Mapped[dt.date | None] = mapped_column(Date)
    au_port_le: Mapped[dt.date | None] = mapped_column(Date)
    dedouanee_le: Mapped[dt.date | None] = mapped_column(Date)
    arrivee_usine_le: Mapped[dt.date | None] = mapped_column(Date)
    eta: Mapped[dt.date | None] = mapped_column(Date)
    conteneur: Mapped[str] = chaine(L.CONTENEUR)
    navire: Mapped[str] = chaine(L.NAVIRE)
    montant_approuve: Mapped[Decimal | None] = mapped_column(MONTANT.type_sql())
    approuvee_par_id: Mapped[int | None] = qui()
    approuvee_le: Mapped[datetime | None] = instant()
    solde_origine: Mapped[OrigineSolde | None] = mapped_column(enumeration(OrigineSolde, 12))
    solde_le: Mapped[datetime | None] = instant()
    solde_par_id: Mapped[int | None] = qui()
    texte_recherche: Mapped[str] = recherche()
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)

    lignes: Mapped[list[CommandeLigne]] = enfants("CommandeLigne")
    versions: Mapped[list[CommandeVersion]] = enfants("CommandeVersion", "figee_le")
    decisions: Mapped[list[CommandeDecision]] = enfants("CommandeDecision", "quand")


_CONFIRMATION = "prix_confirme = (confirme_le IS NOT NULL)"


class CommandeLigne(Base):
    """Une ligne d'un bon : kg commandés, conditionnement, prix au kg dans la devise du bon."""

    __tablename__ = "commande_ligne"
    __table_args__ = (
        UniqueConstraint("commande_id", "matiere_id"),
        CheckConstraint("quantite > 0", name="quantite_positive"),
        CheckConstraint("lower(unite_achat) <> 'ml'", name="unite_achat_pas_ml"),
        CheckConstraint("contenance > 0", name="contenance_positive"),
        CheckConstraint("prix >= 0", name="prix_positif"),
        CheckConstraint(_CONFIRMATION, name="confirmation"),
        Index(None, "matiere_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    commande_id: Mapped[int] = mapped_column(fk("commande.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    quantite: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())
    unite_achat: Mapped[str] = chaine(L.UNITE_ACHAT, "kg")
    contenance: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(1))
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    prix_confirme: Mapped[bool] = colonne(defaut=False)
    confirme_le: Mapped[datetime | None] = instant()
    confirme_par_id: Mapped[int | None] = qui()


class CommandeVersion(Base):
    """Une version partie d'un bon (figée à l'envoi, à l'approbation, au renvoi…)."""

    __tablename__ = "commande_version"
    __table_args__ = (
        CheckConstraint("montant_reference >= 0", name="montant_positif"),
        Index(None, "commande_id", "figee_le"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    commande_id: Mapped[int] = mapped_column(fk("commande.id", ondelete="CASCADE"))
    figee_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    montant_reference: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    motif: Mapped[MotifVersionCommande] = mapped_column(enumeration(MotifVersionCommande, 16))
    par_id: Mapped[int | None] = qui()

    lignes: Mapped[list[CommandeVersionLigne]] = enfants("CommandeVersionLigne", "matiere_id")


class CommandeVersionLigne(Base):
    """Une ligne d'une version partie (mêmes types que la ligne du bon)."""

    __tablename__ = "commande_version_ligne"
    __table_args__ = (
        CheckConstraint("quantite > 0", name="quantite_positive"),
        CheckConstraint("contenance > 0", name="contenance_positive"),
        CheckConstraint("prix >= 0", name="prix_positif"),
    )
    __activite__ = True

    version_id: Mapped[int] = mapped_column(
        fk("commande_version.id", ondelete="CASCADE"), primary_key=True
    )
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"), primary_key=True)
    quantite: Mapped[Decimal] = mapped_column(QUANTITE.type_sql())
    unite_achat: Mapped[str] = chaine(L.UNITE_ACHAT, "kg")
    contenance: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(1))
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    prix_confirme: Mapped[bool] = colonne(defaut=False)
    confirme_par_id: Mapped[int | None] = qui()
    confirme_le: Mapped[datetime | None] = instant()


class CommandeDecision(Base):
    """Une décision sur un bon : demande d'approbation, approbation, renvoi (avec motif)…"""

    __tablename__ = "commande_decision"
    __table_args__ = (
        CheckConstraint("decision <> 'renvoi' OR length(motif) >= 3", name="motif_du_renvoi"),
        Index(None, "commande_id", "quand"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    commande_id: Mapped[int] = mapped_column(fk("commande.id", ondelete="CASCADE"))
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    decision: Mapped[DecisionCommande] = mapped_column(enumeration(DecisionCommande, 32))
    motif: Mapped[str] = chaine(L.MOTIF_DECISION)
    montant_avant: Mapped[Decimal | None] = mapped_column(MONTANT.type_sql())
    montant_apres: Mapped[Decimal | None] = mapped_column(MONTANT.type_sql())


class Facture(AvecVersion, Base):
    """Une facture fournisseur (un dossier d'importation = une facture = une livraison)."""

    __tablename__ = "facture"
    __table_args__ = (
        UniqueConstraint("fournisseur_id", "numero"),
        CheckConstraint("montant > 0", name="montant_positif"),
        CheckConstraint(
            "echeance IS NULL OR date IS NULL OR echeance >= date", name="echeance_apres"
        ),
        CheckConstraint("payee_par_id IS NULL OR payee_le IS NOT NULL", name="reglement"),
        Index("ix_facture_echeance_due", "echeance", postgresql_where=text("payee_le IS NULL")),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    fournisseur_id: Mapped[int] = mapped_column(fk("fournisseur.id"))
    numero: Mapped[str] = mapped_column(String(L.NUMERO_FACTURE))
    date: Mapped[dt.date | None] = mapped_column(Date)
    montant: Mapped[Decimal | None] = mapped_column(MONTANT.type_sql())
    devise: Mapped[str] = mapped_column(CHAR(L.CODE_DEVISE), fk("devise.code"))
    echeance: Mapped[dt.date | None] = mapped_column(Date)
    payee_le: Mapped[dt.date | None] = mapped_column(Date)
    payee_par_id: Mapped[int | None] = qui()
