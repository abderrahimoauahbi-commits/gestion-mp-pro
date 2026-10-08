"""Réceptions et leurs lignes (MODELE-DONNEES § 3.4.6–3.4.7).

Une devise par réception, portée par l'en-tête (I35) ; le prix d'une ligne est **au kg** dans
cette devise. Le lot n'est posé qu'à la validation ; une ligne refusée n'a jamais de lot (I36).
`UQ (id, reception_id)` sert la FK composite de `reclamation` (la ligne nommée par une
réclamation appartient à sa réception).
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, Date, Index, String, Text, UniqueConstraint
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
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.modeles.stock import fk_lot
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, UNITES, enumeration

NUMERO_SI_VALIDE = "(statut = 'brouillon') = (numero IS NULL)"
VALIDE_DATE = "(statut <> 'brouillon') = ({colonne} IS NOT NULL)"
ANNULE_DATE = "(statut = '{statut}') = ({colonne} IS NOT NULL)"


class Reception(AvecVersion, Base):
    """Un camion reçu : numéroté à la validation (`REC-AAAA-NNNN`)."""

    __tablename__ = "reception"
    __table_args__ = (
        CheckConstraint(NUMERO_SI_VALIDE, name="numero_statut"),
        CheckConstraint(VALIDE_DATE.format(colonne="validee_le"), name="validation_date"),
        CheckConstraint(
            ANNULE_DATE.format(statut="annulee", colonne="annulee_le"), name="annulation_date"
        ),
        Index(None, "statut", "date"),
        Index(None, "fournisseur_id"),
        Index(None, "facture_id"),
        index_recherche(),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str | None] = mapped_column(String(L.NUMERO), unique=True)
    statut: Mapped[StatutDocument] = colonne(
        enumeration(StatutDocument, 12), defaut=StatutDocument.brouillon
    )
    date: Mapped[dt.date] = mapped_column(Date)
    fournisseur_id: Mapped[int] = mapped_column(fk("fournisseur.id"))
    devise: Mapped[str] = mapped_column(CHAR(L.CODE_DEVISE), fk("devise.code"))
    numero_bl: Mapped[str] = chaine(L.NUMERO_BL)
    facture_id: Mapped[int | None] = mapped_column(fk("facture.id"))
    observations: Mapped[str] = colonne(Text, defaut="")
    controle_par: Mapped[str] = chaine(L.CONTROLE_PAR)
    cree_par_id: Mapped[int | None] = qui()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    validee_par_id: Mapped[int | None] = qui()
    validee_le: Mapped[datetime | None] = instant()
    annulee_le: Mapped[datetime | None] = instant()
    annulee_par_id: Mapped[int | None] = qui()
    annulation_motif: Mapped[str] = chaine(L.MOTIF)
    texte_recherche: Mapped[str] = recherche()

    lignes: Mapped[list[ReceptionLigne]] = enfants("ReceptionLigne")


class ReceptionLigne(Base):
    """Une matière reçue : attendu, BL, pesé, palettes et bobines, qualité, rangement, prix."""

    __tablename__ = "reception_ligne"
    __table_args__ = (
        fk_lot(),
        UniqueConstraint("id", "reception_id"),
        CheckConstraint("NOT lot_interne OR qualite <> 'refuse'", name="lot_interne_accepte"),
        CheckConstraint("quantite_attendue >= 0", name="attendu_positif"),
        CheckConstraint("quantite_bl >= 0", name="bl_positif"),
        CheckConstraint("quantite_pesee >= 0", name="pese_positif"),
        CheckConstraint("nb_palettes >= 0", name="palettes_positives"),
        CheckConstraint("bobines_en_plus >= 0", name="bobines_en_plus_positives"),
        CheckConstraint("nb_bobines >= 0", name="bobines_positives"),
        CheckConstraint("lot_id IS NULL OR magasin_id IS NOT NULL", name="lot_range"),
        CheckConstraint("qualite <> 'refuse' OR lot_id IS NULL", name="refus_sans_lot"),
        CheckConstraint("prix >= 0", name="prix_positif"),
        Index(None, "reception_id"),
        Index(None, "commande_ligne_id"),
        Index(None, "lot_id"),
        Index(None, "matiere_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    reception_id: Mapped[int] = mapped_column(fk("reception.id", ondelete="CASCADE"))
    commande_ligne_id: Mapped[int | None] = mapped_column(fk("commande_ligne.id"))
    matiere_id: Mapped[int] = mapped_column(fk("matiere.id"))
    lot_numero: Mapped[str] = chaine(L.NUMERO_LOT)
    lot_interne: Mapped[bool] = colonne(defaut=False)
    quantite_attendue: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    quantite_bl: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    quantite_pesee: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    nb_palettes: Mapped[Decimal] = colonne(UNITES.type_sql(), defaut=Decimal(0))
    bobines_en_plus: Mapped[Decimal] = colonne(UNITES.type_sql(), defaut=Decimal(0))
    nb_bobines: Mapped[Decimal] = colonne(UNITES.type_sql(), defaut=Decimal(0))
    magasin_id: Mapped[int | None] = mapped_column(fk("magasin.id"))
    qualite: Mapped[QualiteReception] = colonne(
        enumeration(QualiteReception, 12), defaut=QualiteReception.conforme
    )
    observations: Mapped[str] = chaine(L.COMMENTAIRE)
    prix: Mapped[Decimal] = colonne(PRIX.type_sql(), defaut=Decimal(0))
    lot_id: Mapped[int | None] = mapped_column()
