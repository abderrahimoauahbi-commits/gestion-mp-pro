"""Restauration d'une sauvegarde de **cette** base : réversible, tout ou rien, migrée.

Lot D10 (ARCHITECTURE § 13.3 ; défauts G-02, G-03, G-05, G-08 de Gestion MP). Deux temps :

1. `preparer` (dans la requête) : prend le verrou RESTAURATION sur une connexion à lui — il le
   tient **du début à la fin** (l'API répond 503 `restauration_en_cours` aux autres postes) —,
   puis refuse ce qui ne se restaure pas (fichier absent 404, illisible 422, autre base 409,
   version plus récente 409, outils absents 503), écrit le script SQL de la sauvegarde et fait
   la sauvegarde « avant restauration » (la restauration se défait).
2. `executer` (après la réponse 202, tâche de fond de la requête) : coupe les autres connexions
   à la base **sauf** celles qui tiennent les verrous des tâches et de la restauration (G-08),
   remplace le schéma `public` **en une transaction** (`psql -1`, `ON_ERROR_STOP` : à la
   première erreur rien n'a changé, G-02), migre à la révision de ce code, remet les pièces
   jointes qui manquent (G-03), ferme toutes les sessions sauf celle de qui restaure, réécrit
   le registre des sauvegardes, journalise « restauration » dans la base restaurée et note
   l'état (tâche `restauration`, lue par `/api/sante`).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Connection, delete, select, text
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import DISPONIBILITE, Verrou, essayer_verrou, fabrique, liberer, moteur
from gestion_mp_pro.modeles import Journal, SessionOuverte, Utilisateur
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.services import audit, execution, horloge, installation
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services import sauvegarde_registre as registre
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.sauvegarde import dossier, sauvegarder
from gestion_mp_pro.services.sauvegarde_etat import recaler
from gestion_mp_pro.services.sauvegarde_pieces import remettre

JOURNAL = logging.getLogger("gestion_mp_pro.restauration")
RIEN = "rien n'a été restauré."
HTTP_SAISIE = 422

_COUPER = text(
    "SELECT count(pg_terminate_backend(a.pid)) FROM pg_stat_activity a"
    " WHERE a.datname = current_database() AND a.pid <> pg_backend_pid()"
    " AND a.pid NOT IN (SELECT l.pid FROM pg_locks l WHERE l.locktype = 'advisory'"
    " AND l.granted AND l.classid = 0 AND l.objsubid = 1 AND l.objid = ANY(:gardes)"
    " AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database()))"
)
"""Coupe les connexions des autres postes et processus, sauf celles des verrous gardés."""

VERROUS_GARDES = [int(Verrou.TACHES), int(Verrou.RESTAURATION)]


@dataclass
class Preparation:
    """Une restauration acceptée : le fichier, son script, la sauvegarde d'avant, le verrou."""

    fichier: Path
    script: Path
    avant: str
    motif: str
    qui: Acteur
    connexion: Connection
    debut: datetime = field(default_factory=horloge.maintenant)


def _fichier(nom: str) -> Path:
    """Le fichier nommé, dans le dossier de cette base seulement (pas de remontée de dossier)."""
    fichier = dossier() / Path(nom).name
    if not fichier.is_file() or o.lire_nom(fichier.name) is None:
        raise Refus.introuvable("Sauvegarde introuvable.")
    return fichier


def _refuser_ce_qui_ne_se_restaure_pas(fichier: Path) -> None:
    """Fichier illisible (422), d'une autre base (409), d'une version plus récente (409)."""
    try:
        lecture = o.relire(fichier)
    except Refus as exc:
        if exc.http != HTTP_SAISIE:
            raise
        raise Refus.saisie(f"{exc.detail} — {RIEN}") from exc
    courante = reglages().nom_base
    if lecture.base and lecture.base != courante:
        raise Refus.etat(
            f"Cette sauvegarde est celle de la base « {lecture.base} », pas de « {courante} » : "
            "la restaurer remplacerait toutes les données par celles d'une autre base.",
            code="sauvegarde_autre_base",
        )
    revision = o.revision_du_fichier(fichier)
    connues = {
        r.revision
        for r in ScriptDirectory.from_config(installation.configuration()).walk_revisions()
    }
    if revision is None:
        raise Refus.etat(
            "Cette sauvegarde ne porte pas de révision du schéma de Gestion MP PRO : elle ne "
            "vient pas de ce logiciel. Rien n'a été restauré."
        )
    if revision not in connues:
        raise Refus.etat(
            "Cette sauvegarde vient d'une version plus récente de Gestion MP PRO (révision du "
            f"schéma {revision}, que cette version ne connaît pas) : la restaurer donnerait une "
            "base que ce serveur ne sait pas lire. Rien n'a été restauré."
        )


def _ecrire_script(fichier: Path) -> Path:
    """Le script SQL de la sauvegarde (`pg_restore -f`), écrit avant de toucher à la base."""
    pg_restore = o.exiger("pg_restore", "Restauration impossible")
    script = dossier() / f".restauration.{os.getpid()}.sql"
    arguments = [str(pg_restore), "--no-owner", "--no-privileges", "-f", str(script)]
    sortie = o.lancer([*arguments, str(fichier)], o.DELAI_DUMP_S)
    if sortie.returncode != 0:
        script.unlink(missing_ok=True)
        raise Refus.saisie(f"La sauvegarde n'a pas pu être lue : {o.raison(sortie)} — {RIEN}")
    return script


def _prendre_le_verrou() -> Connection:
    """La connexion qui tient RESTAURATION ; une autre restauration en cours : 409."""
    c = execution.moteur_des_verrous().connect()
    if not essayer_verrou(c, Verrou.RESTAURATION):
        c.close()
        raise Refus.etat(
            "Une restauration est déjà en cours : attendre sa fin.", code="tache_en_cours"
        )
    c.commit()
    return c


MOT_DE_CONFIRMATION = "RESTAURER"


def preparer(qui: Acteur, nom: str, confirmation: str, motif: str) -> Preparation:
    """Accepte (ou refuse) une restauration ; sauvegarde l'état actuel. Le verrou reste pris."""
    if confirmation.strip().upper() != MOT_DE_CONFIRMATION:
        raise Refus.saisie(
            f"Dernière confirmation : taper {MOT_DE_CONFIRMATION} pour remplacer toute la base.",
            code="confirmation_requise",
            champs={"confirmation": MOT_DE_CONFIRMATION},
        )
    connexion = _prendre_le_verrou()
    script: Path | None = None
    try:
        fichier = _fichier(nom)
        _refuser_ce_qui_ne_se_restaure_pas(fichier)
        o.exiger("psql", "Restauration impossible")
        script = _ecrire_script(fichier)
        try:
            avant = sauvegarder("avant-restauration", par_id=qui.id, exiger_copie=False)
        except Refus as exc:
            raise Refus.indisponible(
                f"L'état actuel n'a pas pu être sauvegardé ({exc.detail}) : {RIEN}",
                code="sauvegarde_impossible",
            ) from exc
        return Preparation(fichier, script, avant.nom, motif, qui, connexion)
    except BaseException:
        if script is not None:
            script.unlink(missing_ok=True)
        _rendre_le_verrou(connexion)
        raise


def _rendre_le_verrou(c: Connection) -> None:
    """Rend le verrou RESTAURATION et ferme sa connexion (même coupée)."""
    try:
        liberer(c, Verrou.RESTAURATION)
        c.commit()
    except Exception:  # la connexion a pu tomber : le verrou part avec elle
        JOURNAL.warning("Verrou de restauration rendu par la fermeture de sa connexion.")
    finally:
        c.close()


@dataclass(frozen=True)
class _Memoire:
    """Ce qui doit survivre au remplacement de la base : le registre et la session de qui
    restaure."""

    registre: list[registre.Entree]
    session: dict[str, object] | None
    identifiant: str


def _memoriser(p: Preparation) -> _Memoire:
    """Copie en mémoire le registre des sauvegardes et la session de qui restaure."""
    with fabrique()() as s:
        ouverte = s.get(SessionOuverte, p.qui.session) if p.qui.session else None
        session = None
        if ouverte is not None:
            colonnes = ("empreinte", "utilisateur_id", "cree_le", "expire_le", "vu_le", "adresse")
            session = {k: getattr(ouverte, k) for k in (*colonnes, "agent")}
        return _Memoire(registre.photographier(s), session, p.qui.identifiant)


def _remplacer(p: Preparation) -> str:
    """Coupe les autres connexions et remplace le schéma en une transaction ; rend l'erreur."""
    moteur().dispose()
    coupees = p.connexion.execute(_COUPER, {"gardes": VERROUS_GARDES}).scalar()
    p.connexion.commit()
    JOURNAL.info("Restauration de %s : %s connexion(s) coupée(s).", p.fichier.name, coupees)
    psql = o.exiger("psql", "Restauration impossible")
    with o.adresse_base() as adresse:
        sortie = o.lancer(
            [str(psql), "-X", "-q", "-1", "-v", "ON_ERROR_STOP=1", "-d", adresse]
            + ["-c", "DROP SCHEMA IF EXISTS public CASCADE", "-c", "CREATE SCHEMA public"]
            + ["-f", str(p.script)],
            o.DELAI_DUMP_S,
        )
    if sortie.returncode != 0:
        JOURNAL.error("Restauration de %s refusée par psql : %s", p.fichier.name, sortie.stderr)
        return (
            f"La restauration a échoué, la base est restée telle qu'elle était : {o.raison(sortie)}"
        )
    return ""


def _sessions(s: Session, m: _Memoire) -> None:
    """Toutes les sessions de la base restaurée sont fermées, sauf celle de qui restaure."""
    s.execute(delete(SessionOuverte))
    if m.session is None:
        return
    u = s.get(Utilisateur, m.session["utilisateur_id"])
    if u is not None and u.actif and u.identifiant == m.identifiant:
        s.add(SessionOuverte(**m.session))


def _journaliser(s: Session, p: Preparation, revenues: int, erreur: str) -> None:
    """La ligne « restauration », écrite dans la base restaurée (auteur absent : son nom reste)."""
    present = s.scalar(select(Utilisateur.id).where(Utilisateur.id == p.qui.id)) is not None
    detail = f"{p.fichier.name} — {p.motif}"
    if revenues:
        detail += f" ({revenues} pièce(s) jointe(s) revenue(s))"
    if erreur:
        detail += f" — {erreur}"
    ligne: Journal = audit.journal(
        s, p.qui if present else None, "restauration", ObjetJournal.sauvegarde, detail=detail
    )
    if not present:
        ligne.utilisateur_nom, ligne.role = p.qui.nom, str(p.qui.role)


def _apres(p: Preparation, m: _Memoire, duree_debut: float) -> None:
    """Migre, remet les pièces, ferme les sessions, réécrit le registre, journalise."""
    erreur = ""
    try:
        installation.migrer()
    except Exception as exc:
        JOURNAL.exception("Restauration : la migration de la base restaurée a échoué.")
        erreur = f"la mise au schéma de cette version a échoué : {str(exc)[:200]}"
    DISPONIBILITE.schema_en_retard = installation.schema_en_retard()
    revenues = remettre(o.archive_de(p.fichier))
    with fabrique()() as s, s.begin():
        _sessions(s, m)
        registre.reecrire(s, m.registre)
        recaler(s)
        _journaliser(s, p, revenues, erreur)
        duree = int((time.monotonic() - duree_debut) * 1000)
        execution.noter_dans(s, execution.RESTAURATION, p.debut, erreur, duree)
    from gestion_mp_pro.services import donnees_moteur

    donnees_moteur.invalider()


def executer(p: Preparation) -> None:
    """Remplace la base par la sauvegarde (tâche de fond de la route 45) ; note son issue."""
    debut = time.monotonic()
    try:
        m = _memoriser(p)
        erreur = _remplacer(p)
        if erreur:
            execution.noter(execution.RESTAURATION, p.debut, erreur)
            return
        _apres(p, m, debut)
        JOURNAL.info(
            "Base restaurée depuis %s en %.1f s.", p.fichier.name, time.monotonic() - debut
        )
    except Exception as exc:
        JOURNAL.exception("Restauration de %s interrompue.", p.fichier.name)
        try:
            execution.noter(execution.RESTAURATION, p.debut, f"restauration interrompue : {exc}")
        except Exception:
            JOURNAL.exception("État de la restauration non noté.")
    finally:
        p.script.unlink(missing_ok=True)
        _rendre_le_verrou(p.connexion)
