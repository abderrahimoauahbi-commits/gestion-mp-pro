"""Santé du serveur (route 1) et état du serveur pour la direction et l'administrateur (route 4).

Lot D10 (ARCHITECTURE § 13.4). `/api/sante` est public et ne dit rien du métier : version
servie, révision Alembic de la base et révision attendue, temps de réponse de la base, âge et
alerte de la sauvegarde **de cette base** (G-06, alerte à 26 h), état des tâches, courriels en
attente. Pendant une restauration, la santé ne lit aucune table (elles sont verrouillées) : elle
dit « restauration : en cours ».

L'adresse réseau de l'état du serveur reprend le schéma et le port **de la requête** (G-13 :
derrière Caddy, `https://nom` sans « :8050 »).
"""

from __future__ import annotations

import platform
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import DISPONIBILITE, Verrou, fabrique, moteur, verrou_tenu
from gestion_mp_pro.modeles import SessionOuverte, Utilisateur
from gestion_mp_pro.services import courriel, execution, horloge, installation
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services.appareils import adresse_de
from gestion_mp_pro.services.sauvegarde_etat import EtatSauvegardes, etat


@dataclass(frozen=True)
class Sante:
    """Ce que lit la surveillance."""

    etat: str
    base_ms: float | None
    schema: str | None = None
    schema_attendu: str | None = None
    sauvegarde_age_h: float | None = None
    sauvegarde_alerte: str = ""
    taches: dict[str, str] = field(default_factory=dict)
    courriels_en_attente: int = 0


def _base_ms() -> float | None:
    """Temps d'un `SELECT 1`, en millisecondes ; `None` si la base ne répond pas."""
    debut = time.perf_counter()
    try:
        with moteur().connect() as c:
            c.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return None
    return round((time.perf_counter() - debut) * 1000, 1)


def _taches(s: Session) -> dict[str, str]:
    """{tâche: « ok » | « échec : … » | « jamais »} (et la dernière restauration si elle existe)."""
    resumes = {nom: execution.resume(execution.lire(s, nom)) for nom in execution.TACHES}
    derniere = execution.lire(s, execution.RESTAURATION)
    if derniere is not None:
        resumes[execution.RESTAURATION] = execution.resume(derniere)
    return resumes


def sante() -> Sante:
    """La santé du serveur ; jamais d'exception (la surveillance doit toujours avoir sa réponse)."""
    base_ms = _base_ms()
    attendu = installation.revision_attendue()
    if base_ms is None:
        return Sante("degrade", None, schema_attendu=attendu)
    try:
        if verrou_tenu(Verrou.RESTAURATION):
            taches = {execution.RESTAURATION: "en cours"}
            return Sante("degrade", base_ms, schema_attendu=attendu, taches=taches)
        with fabrique()() as s:
            schema = installation.revision_de(s.connection())
            e = etat(s, nb_fichiers=0)
            taches = _taches(s)
            attente = courriel.en_attente(s)
    except SQLAlchemyError:
        return Sante("degrade", base_ms, schema_attendu=attendu)
    a_jour = schema == attendu and not DISPONIBILITE.schema_en_retard
    return Sante(
        etat="ok" if a_jour else "degrade",
        base_ms=base_ms,
        schema=schema,
        schema_attendu=attendu,
        sauvegarde_age_h=e.age_h,
        sauvegarde_alerte=e.alerte or "",
        taches=taches,
        courriels_en_attente=attente,
    )


@dataclass(frozen=True)
class SessionsCompte:
    """Les sessions ouvertes d'un compte."""

    nom: str
    role: str
    nb: int
    vu_le: datetime | None
    expire_le: datetime | None
    appareils: int


@dataclass(frozen=True)
class EtatServeur:
    """L'état du serveur (route 4) : versions, base, réseau, tâches, sauvegardes, sessions."""

    application: str
    python: str
    systeme: str
    machine: str
    base: dict[str, object]
    reseau: dict[str, object]
    taches_actives: bool
    porteur_ici: bool
    session_jours: int
    outils: dict[str, str | None]
    sauvegardes: EtatSauvegardes
    sessions: list[SessionsCompte]


def _base(s: Session) -> dict[str, object]:
    """Nom, hôte, port, version et taille de la base ; révisions du schéma."""
    url = make_url(reglages().base)
    version = s.scalar(text("SHOW server_version"))
    taille = s.scalar(text("SELECT pg_database_size(current_database())"))
    return {
        "nom": url.database or "",
        "hote": url.host or "ce serveur (connexion locale)",
        "port": url.port or 5432,
        "version": str(version or ""),
        "taille_octets": int(taille or 0),
        "schema": installation.revision_de(s.connection()),
        "schema_attendu": installation.revision_attendue(),
    }


def _sessions(s: Session) -> list[SessionsCompte]:
    """Les sessions ouvertes non expirées, par compte."""
    requete = (
        select(
            Utilisateur.nom,
            Utilisateur.role,
            func.count(),
            func.max(SessionOuverte.vu_le),
            func.max(SessionOuverte.expire_le),
            func.count(SessionOuverte.appareil_id),
        )
        .join(Utilisateur, Utilisateur.id == SessionOuverte.utilisateur_id)
        .where(SessionOuverte.expire_le > horloge.maintenant())
        .group_by(Utilisateur.id, Utilisateur.nom, Utilisateur.role)
        .order_by(Utilisateur.nom)
    )
    return [
        SessionsCompte(nom, str(role or ""), int(nb), vu, expire, int(app))
        for nom, role, nb, vu, expire, app in s.execute(requete)
    ]


def etat_serveur(s: Session, adresse_demandee: str, version: str) -> EtatServeur:
    """L'état du serveur pour l'onglet Administration › Serveur."""
    r = reglages()
    adresse = adresse_de(adresse_demandee)
    return EtatServeur(
        application=version,
        python=platform.python_version(),
        systeme=f"{platform.system()} {platform.release()}",
        machine=socket.gethostname(),
        base=_base(s),
        reseau={
            "adresse": adresse,
            "ecoute": r.ecoute,
            "port": r.port,
            "https": r.https or adresse.startswith("https://"),
        },
        taches_actives=r.taches,
        porteur_ici=_porteur_ici(),
        session_jours=r.session_jours,
        outils={
            n: str(p) if (p := o.outil(n)) else None for n in ("pg_dump", "pg_restore", "psql")
        },
        sauvegardes=etat(s, nb_fichiers=0),
        sessions=_sessions(s),
    )


def _porteur_ici() -> bool:
    """Ce processus porte-t-il les tâches ?"""
    from gestion_mp_pro.taches import planificateur

    return planificateur.porteur()
