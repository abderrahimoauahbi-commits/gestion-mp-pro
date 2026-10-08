"""Socle : comptes, sessions, tentatives, appareils, journal, réglages, compteurs (§ 3.1).

`CLES_REGLAGES` est la liste fermée des clés de `parametre` (CHECK `ck_parametre_cle_connue`) :
le registre des réglages (`services/registre_reglages.py`, lot D1) déclare exactement ces clés.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, CheckConstraint, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import (
    MAINTENANT,
    AvecVersion,
    Base,
    chaine,
    cle_primaire,
    cle_primaire_longue,
    colonne,
    fk,
    instant,
    qui,
)
from gestion_mp_pro.modeles.enums import ObjetJournal, Role, SerieNumero
from gestion_mp_pro.modeles.types import enumeration

CLES_REGLAGES: tuple[str, ...] = (
    "seuil_critique", "seuil_alerte", "seuil_dormant", "delai_defaut", "marge_jours",
    "marge_securite", "taux_perte", "securite_a", "securite_b", "securite_c",
    "fenetre_realisation_jours", "plafond_stock_min_mois", "croissance_annuelle",
    "seuil_abc_a", "seuil_abc_b", "seuil_xyz_x", "seuil_xyz_y", "seuil_bc_urgent",
    "seuil_bc_groupe", "seuil_tier1", "seuil_tier2", "seuil_tier3", "seuil_approbation",
    "toler_in_full", "toler_ecart_pesee", "toler_excedent", "toler_poids_bobine",
    "tolerance_inventaire", "toler_retard_jours", "cible_otif", "score_strategique",
    "score_standard", "score_surveiller", "seuil_hausse_forte", "fenetre_prix_jours",
    "taux_tva_import", "taux_tpi_import", "seuil_surcout_import", "toler_facture_import",
    "delai_frais_import_jours", "dso", "nom_entreprise", "forme_juridique", "secteur",
    "adresse", "ville", "telephone", "banques", "ice", "rc", "identifiant_fiscal", "cnss",
    "patente", "date_cloture", "courriel_destinataires", "adresse_publique",
)  # fmt: skip
"""Les 56 clés : les 55 réglages de Gestion MP corrigé (`delai_frais_import_jours` compris)
et `seuil_bc_urgent`, sans effet, gardé pour mémoire (ECRANS-PRO E6)."""


def _dans(colonne_sql: str, valeurs: tuple[str, ...]) -> str:
    """`colonne IN ('a', 'b', …)`."""
    return f"{colonne_sql} IN (" + ", ".join(f"'{v}'" for v in valeurs) + ")"


class Utilisateur(AvecVersion, Base):
    """Un compte ; jamais supprimé (désactivé). Un compte `historique` ne se connecte pas."""

    __tablename__ = "utilisateur"
    __table_args__ = (
        CheckConstraint("identifiant = lower(identifiant)", name="identifiant_minuscules"),
        CheckConstraint("historique OR role IS NOT NULL", name="role_requis"),
        CheckConstraint("NOT historique OR NOT actif", name="historique_inactif"),
    )

    id: Mapped[int] = cle_primaire()
    identifiant: Mapped[str] = mapped_column(String(L.IDENTIFIANT), unique=True)
    nom: Mapped[str] = chaine(L.NOM_PERSONNE)
    role: Mapped[Role | None] = mapped_column(enumeration(Role, L.ROLE))
    email: Mapped[str] = chaine(L.EMAIL_COMPTE)
    empreinte_code: Mapped[str] = chaine(L.EMPREINTE_CODE)
    actif: Mapped[bool] = colonne(defaut=True)
    historique: Mapped[bool] = colonne(defaut=False)
    code_change_le: Mapped[datetime | None] = instant()
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    vu_le: Mapped[datetime | None] = instant()


class SessionOuverte(Base):
    """Une session ouverte (jeton gardé par son empreinte SHA-256)."""

    __tablename__ = "session"
    __table_args__ = (Index(None, "expire_le"), Index(None, "utilisateur_id"))

    empreinte: Mapped[str] = mapped_column(CHAR(L.EMPREINTE), primary_key=True)
    utilisateur_id: Mapped[int] = mapped_column(fk("utilisateur.id", ondelete="CASCADE"))
    appareil_id: Mapped[int | None] = mapped_column(fk("appareil.id", ondelete="SET NULL"))
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    expire_le: Mapped[datetime] = instant()
    vu_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    adresse: Mapped[str] = chaine(L.ADRESSE_IP)
    agent: Mapped[str] = chaine(L.AGENT)


class Tentative(Base):
    """Les échecs de connexion d'un identifiant (blocage progressif dès 5 échecs)."""

    __tablename__ = "tentative"
    __table_args__ = (CheckConstraint("echecs >= 0", name="echecs_positifs"),)

    identifiant: Mapped[str] = mapped_column(String(L.IDENTIFIANT), primary_key=True)
    echecs: Mapped[int] = colonne(Integer, defaut=0)
    bloque_jusqua: Mapped[datetime | None] = instant()
    dernier_echec_le: Mapped[datetime] = instant(defaut=MAINTENANT)


class Appareil(Base):
    """Un téléphone (ou poste) enrôlé : seul lui voit les visages à la connexion."""

    __tablename__ = "appareil"

    id: Mapped[int] = cle_primaire()
    nom: Mapped[str] = mapped_column(String(L.NOM_APPAREIL), unique=True)
    empreinte_jeton: Mapped[str | None] = mapped_column(CHAR(L.EMPREINTE), unique=True)
    empreinte_enrolement: Mapped[str | None] = mapped_column(CHAR(L.EMPREINTE), unique=True)
    enrolement_expire_le: Mapped[datetime | None] = instant()
    enrole_le: Mapped[datetime | None] = instant()
    vu_le: Mapped[datetime | None] = instant()
    actif: Mapped[bool] = colonne(defaut=True)
    cree_par_id: Mapped[int] = qui(nullable=False)
    cree_le: Mapped[datetime] = instant(defaut=MAINTENANT)


class Journal(Base):
    """Une ligne par geste métier, avec avant/après ; jamais modifiée ni purgée."""

    __tablename__ = "journal"
    __table_args__ = (
        Index(None, "objet", "objet_id", "quand"),
        Index(None, "quand"),
        Index(None, "utilisateur_id", "quand"),
        Index(None, "action"),
    )

    id: Mapped[int] = cle_primaire_longue()
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    utilisateur_id: Mapped[int | None] = qui()
    utilisateur_nom: Mapped[str] = chaine(L.NOM_PERSONNE)
    role: Mapped[str] = chaine(L.ROLE)
    action: Mapped[str] = mapped_column(String(L.ACTION))
    objet: Mapped[ObjetJournal] = colonne(
        enumeration(ObjetJournal, L.OBJET), defaut=ObjetJournal.systeme
    )
    objet_id: Mapped[int | None] = mapped_column(Integer)
    numero: Mapped[str] = chaine(L.NUMERO_DOCUMENT)
    detail: Mapped[str] = chaine(L.DETAIL)
    avant: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    apres: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    requete: Mapped[str] = chaine(L.REQUETE)
    adresse: Mapped[str] = chaine(L.ADRESSE_IP)


class Parametre(AvecVersion, Base):
    """Un réglage métier, valeur en texte normalisé (nombre `repr`, date ISO)."""

    __tablename__ = "parametre"
    __table_args__ = (CheckConstraint(_dans("cle", CLES_REGLAGES), name="cle_connue"),)

    cle: Mapped[str] = mapped_column(String(L.CLE_REGLAGE), primary_key=True)
    valeur: Mapped[str] = chaine(L.VALEUR_REGLAGE)
    modifie_le: Mapped[datetime] = instant(defaut=MAINTENANT)
    modifie_par_id: Mapped[int | None] = qui()


class ParametreHistorique(Base):
    """Chaque changement d'un réglage : avant, après, qui, quand, motif."""

    __tablename__ = "parametre_historique"
    __table_args__ = (Index(None, "cle", "quand"),)

    id: Mapped[int] = cle_primaire()
    cle: Mapped[str] = mapped_column(fk("parametre.cle"))
    avant: Mapped[str | None] = mapped_column(String(L.VALEUR_REGLAGE))
    apres: Mapped[str] = mapped_column(String(L.VALEUR_REGLAGE))
    quand: Mapped[datetime] = instant(defaut=MAINTENANT)
    par_id: Mapped[int | None] = qui()
    motif: Mapped[str] = chaine(L.MOTIF)


class Compteur(Base):
    """Le dernier numéro donné d'une série, par année de la pièce (pris sous FOR UPDATE)."""

    __tablename__ = "compteur"
    __table_args__ = (
        CheckConstraint("annee BETWEEN 2000 AND 2100", name="annee_plausible"),
        CheckConstraint("dernier >= 0", name="dernier_positif"),
    )
    __activite__ = True

    serie: Mapped[SerieNumero] = mapped_column(enumeration(SerieNumero, 4), primary_key=True)
    annee: Mapped[int] = mapped_column(Integer, primary_key=True)
    dernier: Mapped[int] = colonne(Integer, defaut=0)
