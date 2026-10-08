"""Notifications, file des courriels, état des tâches, registre des sauvegardes (§ 3.1.9–3.1.12)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    Base,
    chaine,
    cle_primaire,
    cle_primaire_longue,
    colonne,
    fk,
    instant,
    qui,
)
from gestion_mp_pro.modeles.enums import (
    GenreCourriel,
    GenreSauvegarde,
    Role,
    StatutCourriel,
    TonNotification,
)
from gestion_mp_pro.modeles.types import enumeration


class Notification(Base):
    """Une notification, pour un rôle **ou** une personne ; `cle` la dédoublonne."""

    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint("num_nonnulls(role, utilisateur_id) = 1", name="destinataire"),
        Index(None, "role", "cree_le"),
        Index(None, "utilisateur_id", "cree_le"),
    )
    __activite__ = True

    id: Mapped[int] = cle_primaire_longue()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    role: Mapped[Role | None] = mapped_column(enumeration(Role, L.ROLE))
    utilisateur_id: Mapped[int | None] = qui()
    texte: Mapped[str] = mapped_column(String(L.TEXTE_NOTIFICATION))
    lien: Mapped[str] = chaine(L.LIEN)
    ton: Mapped[TonNotification] = colonne(
        enumeration(TonNotification, 8), defaut=TonNotification.info
    )
    objet: Mapped[str] = chaine(L.OBJET)
    objet_id: Mapped[int | None] = mapped_column(Integer)
    cle: Mapped[str | None] = mapped_column(String(L.CLE_NOTIFICATION), unique=True)
    monetaire: Mapped[bool] = colonne(defaut=False)


class NotificationLecture(Base):
    """Une notification lue par une personne."""

    __tablename__ = "notification_lecture"
    __activite__ = True

    notification_id: Mapped[int] = mapped_column(
        BigInteger, fk("notification.id", ondelete="CASCADE"), primary_key=True
    )
    utilisateur_id: Mapped[int] = mapped_column(fk("utilisateur.id"), primary_key=True)
    lue_le: Mapped[datetime] = instant(defaut=MAINTENANT)


class Courriel(Base):
    """Un courriel de la file (lundi, alertes) ; 5 essais espacés, puis abandonné."""

    __tablename__ = "courriel"
    __table_args__ = (
        CheckConstraint("essais >= 0", name="essais_positifs"),
        CheckConstraint("(statut = 'envoye') = (envoye_le IS NOT NULL)", name="envoi_date"),
    )

    id: Mapped[int] = cle_primaire()
    genre: Mapped[GenreCourriel] = mapped_column(enumeration(GenreCourriel, 8))
    cle: Mapped[str] = mapped_column(String(L.CLE_COURRIEL), unique=True)
    destinataires: Mapped[str] = chaine(L.DESTINATAIRES)
    sujet: Mapped[str] = chaine(L.SUJET)
    corps: Mapped[str] = colonne(Text, defaut="")
    statut: Mapped[StatutCourriel] = colonne(
        enumeration(StatutCourriel, 12), defaut=StatutCourriel.en_attente
    )
    essais: Mapped[int] = colonne(Integer, defaut=0)
    dernier_essai_le: Mapped[datetime | None] = instant()
    erreur: Mapped[str] = chaine(L.ERREUR)
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    envoye_le: Mapped[datetime | None] = instant()


class TacheExecution(Base):
    """L'état partagé d'une tâche de fond (dernier essai, dernier succès, erreur)."""

    __tablename__ = "tache_execution"
    __table_args__ = (CheckConstraint("duree_ms >= 0", name="duree_positive"),)

    nom: Mapped[str] = mapped_column(String(L.NOM_TACHE), primary_key=True)
    dernier_essai_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    dernier_succes_le: Mapped[datetime | None] = instant()
    erreur: Mapped[str] = chaine(L.ERREUR)
    duree_ms: Mapped[int] = colonne(Integer, defaut=0)


class Sauvegarde(Base):
    """Un fichier de sauvegarde de **cette** base (le disque fait foi, le registre se recale)."""

    __tablename__ = "sauvegarde"
    __table_args__ = (
        CheckConstraint("taille >= 0", name="taille_positive"),
        CheckConstraint("tables >= 0", name="tables_positives"),
    )

    id: Mapped[int] = cle_primaire()
    fichier: Mapped[str] = mapped_column(String(L.FICHIER), unique=True)
    genre: Mapped[GenreSauvegarde] = mapped_column(enumeration(GenreSauvegarde, 20))
    base: Mapped[str] = mapped_column(String(L.NOM_BASE))
    taille: Mapped[int] = colonne(BigInteger, defaut=0)
    tables: Mapped[int] = colonne(Integer, defaut=0)
    pieces_incluses: Mapped[bool] = colonne(defaut=False)
    copie_externe: Mapped[bool] = colonne(defaut=False)
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    erreur: Mapped[str] = chaine(L.ERREUR)
