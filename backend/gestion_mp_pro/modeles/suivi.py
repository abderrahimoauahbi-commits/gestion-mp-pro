"""Suivi : réclamations, besoins signalés, pièces jointes, photo du jour (MODELE-DONNEES § 3.9).

- Une réclamation nomme la ligne reçue en cause (étape 15 de Gestion MP : une ligne refusée
  n'a pas de lot) ; la ligne appartient à sa réception (FK composite).
- Une pièce jointe est attachée à **un** objet, par une clé typée (le polymorphe devient
  explicite) ; la retirer pose `retiree_le` (le fichier et la ligne restent).
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
    Integer,
    String,
    Text,
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
    IssueReclamation,
    MotifReclamation,
    ObjetPiece,
    StatutReclamation,
    Urgence,
)
from gestion_mp_pro.modeles.types import JOURS, MONTANT, QUANTITE, TAUX, enumeration

TAILLE_MAXIMALE_PIECE = 20 * 1024 * 1024
"""20 Mo."""


class Reclamation(AvecVersion, Base):
    """Une réclamation au fournisseur (`RCL-AAAA-NNNN` à l'ouverture), suivie jusqu'à son issue."""

    __tablename__ = "reclamation"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reception_ligne_id", "reception_id"],
            ["reception_ligne.id", "reception_ligne.reception_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "reception_ligne_id IS NULL OR reception_id IS NOT NULL", name="ligne_de_reception"
        ),
        CheckConstraint("quantite >= 0", name="quantite_positive"),
        CheckConstraint("montant_demande >= 0", name="montant_demande_positif"),
        CheckConstraint("montant_obtenu >= 0", name="montant_obtenu_positif"),
        CheckConstraint(
            "(statut = 'close') = (close_le IS NOT NULL)"
            " AND (statut <> 'close' OR issue IS NOT NULL)",
            name="close",
        ),
        Index(None, "fournisseur_id"),
        Index(None, "reception_id"),
        Index(None, "lot_id"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    numero: Mapped[str] = mapped_column(String(L.NUMERO), unique=True)
    fournisseur_id: Mapped[int] = mapped_column(fk("fournisseur.id"))
    reception_id: Mapped[int | None] = mapped_column(fk("reception.id"))
    reception_ligne_id: Mapped[int | None] = mapped_column()
    lot_id: Mapped[int | None] = mapped_column(fk("lot.id"))
    motif: Mapped[MotifReclamation] = mapped_column(enumeration(MotifReclamation, 24))
    description: Mapped[str] = colonne(Text, defaut="")
    quantite: Mapped[Decimal] = colonne(QUANTITE.type_sql(), defaut=Decimal(0))
    montant_demande: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    devise: Mapped[str] = colonne(CHAR(L.CODE_DEVISE), fk("devise.code"), defaut="MAD")
    reponse: Mapped[str] = colonne(Text, defaut="")
    issue: Mapped[IssueReclamation | None] = mapped_column(enumeration(IssueReclamation, 16))
    montant_obtenu: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    statut: Mapped[StatutReclamation] = colonne(
        enumeration(StatutReclamation, 8), defaut=StatutReclamation.ouverte
    )
    ouverte_le: Mapped[dt.date] = mapped_column(Date)
    close_le: Mapped[dt.date | None] = mapped_column(Date)
    cree_par_id: Mapped[int | None] = qui()


class Signalement(Base):
    """Un besoin signalé par l'atelier : « il manque du rouge 2900 pour demain »."""

    __tablename__ = "signalement"
    __table_args__ = (
        CheckConstraint("length(trim(texte)) >= 2", name="texte_utile"),
        CheckConstraint("(traite_le IS NULL) = (traite_par_id IS NULL)", name="traitement"),
        Index("ix_signalement_a_traiter", "quand", postgresql_where=text("traite_le IS NULL")),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire()
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    matiere_id: Mapped[int | None] = mapped_column(fk("matiere.id"))
    texte: Mapped[str] = mapped_column(String(L.TEXTE_SIGNALEMENT))
    urgence: Mapped[Urgence] = colonne(enumeration(Urgence, 8), defaut=Urgence.normale)
    traite_par_id: Mapped[int | None] = qui()
    traite_le: Mapped[datetime | None] = instant()
    reponse: Mapped[str] = chaine(L.TEXTE_SIGNALEMENT)


OBJETS_DES_PIECES = tuple(o.value for o in ObjetPiece)
"""Une colonne `<objet>_id` par objet possible d'une pièce jointe."""

_UN_OBJET = (
    "num_nonnulls("
    + ", ".join(f"{o}_id" for o in OBJETS_DES_PIECES)
    + ") = 1 AND "
    + " AND ".join(f"(objet = '{o}') = ({o}_id IS NOT NULL)" for o in OBJETS_DES_PIECES)
)


class PieceJointe(Base):
    """Un document attaché (facture, BL, DUM, photo d'un défaut), chemin relatif au dossier
    des pièces ; retiré logiquement (`retiree_le`)."""

    __tablename__ = "piece_jointe"
    __table_args__ = (
        CheckConstraint(_UN_OBJET, name="un_objet"),
        CheckConstraint(f"taille BETWEEN 1 AND {TAILLE_MAXIMALE_PIECE}", name="taille_bornee"),
        CheckConstraint("(retiree_le IS NULL) = (retiree_par_id IS NULL)", name="retrait"),
        *(Index(None, f"{o}_id") for o in OBJETS_DES_PIECES),
    )

    id: Mapped[int] = cle_primaire()
    objet: Mapped[ObjetPiece] = mapped_column(enumeration(ObjetPiece, 16))
    dossier_id: Mapped[int | None] = mapped_column(fk("dossier.id"))
    reception_id: Mapped[int | None] = mapped_column(fk("reception.id"))
    commande_id: Mapped[int | None] = mapped_column(fk("commande.id"))
    reclamation_id: Mapped[int | None] = mapped_column(fk("reclamation.id"))
    inventaire_id: Mapped[int | None] = mapped_column(fk("inventaire.id"))
    fournisseur_id: Mapped[int | None] = mapped_column(fk("fournisseur.id"))
    matiere_id: Mapped[int | None] = mapped_column(fk("matiere.id"))
    nom: Mapped[str] = mapped_column(String(L.NOM_PIECE))
    type_mime: Mapped[str] = mapped_column(String(L.TYPE_MIME))
    taille: Mapped[int] = mapped_column(Integer)
    empreinte: Mapped[str] = mapped_column(CHAR(L.EMPREINTE))
    chemin: Mapped[str] = mapped_column(String(L.CHEMIN_PIECE))
    par_id: Mapped[int | None] = qui()
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    retiree_le: Mapped[datetime | None] = instant()
    retiree_par_id: Mapped[int | None] = qui()


class IndicateurJour(Base):
    """La photo du jour des indicateurs du cockpit (colonnes au lieu du JSON de Gestion MP)."""

    __tablename__ = "indicateur_jour"
    __table_args__ = (
        CheckConstraint("ruptures >= 0", name="ruptures_positives"),
        CheckConstraint("critiques >= 0", name="critiques_positifs"),
        CheckConstraint("urgents >= 0", name="urgents_positifs"),
    )
    __activite__ = True

    jour: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    pris_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    pris_par_id: Mapped[int | None] = qui()
    valeur_stock_mad: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    couverture_jours: Mapped[Decimal | None] = mapped_column(JOURS.type_sql())
    ruptures: Mapped[int] = colonne(Integer, defaut=0)
    critiques: Mapped[int] = colonne(Integer, defaut=0)
    urgents: Mapped[int] = colonne(Integer, defaut=0)
    a_commander_mad: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    commandes_en_cours_mad: Mapped[Decimal] = colonne(MONTANT.type_sql(), defaut=Decimal(0))
    otif_moyen: Mapped[Decimal | None] = mapped_column(TAUX.type_sql())
