"""Reprise depuis Gestion MP : correspondances et exécutions (MODELE-DONNEES § 3.10).

`reprise_correspondance` rend la reprise rejouable et idempotente : une ligne source déjà
reprise et inchangée est sautée ; changée, elle est signalée (jamais écrasée en silence).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CHAR, BigInteger, CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.base import MAINTENANT, Base, cle_primaire, colonne, instant
from gestion_mp_pro.modeles.enums import ModeReprise, SourceReprise, StatutReprise
from gestion_mp_pro.modeles.types import enumeration


class RepriseCorrespondance(Base):
    """Une ligne source reprise : où elle est allée, et l'empreinte de son contenu."""

    __tablename__ = "reprise_correspondance"
    __table_args__ = (Index(None, "table_cible", "id_cible"),)

    source: Mapped[SourceReprise] = mapped_column(enumeration(SourceReprise, 12), primary_key=True)
    table_source: Mapped[str] = mapped_column(String(L.TABLE), primary_key=True)
    id_source: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_cible: Mapped[str] = mapped_column(String(L.TABLE))
    id_cible: Mapped[int] = mapped_column(BigInteger)
    empreinte: Mapped[str] = mapped_column(CHAR(L.EMPREINTE))
    repris_le: Mapped[datetime] = instant(defaut=MAINTENANT)


class RepriseExecution(Base):
    """Une exécution de la reprise : source, empreinte, comptes par table, rapport."""

    __tablename__ = "reprise_execution"
    __table_args__ = (CheckConstraint("(statut = 'en_cours') = (fin IS NULL)", name="fin"),)

    id: Mapped[int] = cle_primaire()
    debut: Mapped[datetime] = instant(defaut=MAINTENANT)
    fin: Mapped[datetime | None] = instant()
    source: Mapped[SourceReprise] = mapped_column(enumeration(SourceReprise, L.SOURCE_REPRISE))
    base_source: Mapped[str] = mapped_column(String(L.NOM_BASE))
    empreinte_source: Mapped[str | None] = mapped_column(CHAR(L.EMPREINTE))
    mode: Mapped[ModeReprise] = mapped_column(enumeration(ModeReprise, 12))
    comptes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    statut: Mapped[StatutReprise] = colonne(
        enumeration(StatutReprise, 12), defaut=StatutReprise.en_cours
    )
    rapport: Mapped[str] = colonne(Text, defaut="")
