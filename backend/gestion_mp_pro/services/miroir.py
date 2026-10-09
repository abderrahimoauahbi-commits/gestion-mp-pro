"""Le miroir de Gestion MP : son état et son rafraîchissement depuis l'écran (routes 243–244).

Lot C1 (ARCHITECTURE § 14.2). Tant que PRO n'est pas mis en service, sa base est un **miroir**
de la base de Gestion MP, rafraîchi à la demande par la reprise rejouable du lot R1 :

- `etat` lit les dernières exécutions de la reprise (`reprise_execution`), relève la signature
  actuelle de la source (lecture seule, `reprise.source.empreinte_actuelle`) et dit si le
  miroir est **à jour** (signature de la source = celle de la dernière reprise réussie) et si
  la base de PRO porte une **activité propre** (saisie dans PRO : elle ne vient pas de la
  dernière reprise) ;
- `accepter` (dans la requête) refuse ce qui ne se lance pas — une reprise déjà en cours, une
  activité propre sans « remplacer » confirmé par REMPLACER, une source illisible — puis
  `lancer` (tâche de fond, après la réponse 202) fait la reprise : sauvegarde « avant reprise »
  d'abord (service des sauvegardes de D10, par la reprise elle-même), une transaction, rapport
  et contrôles ; le cache du moteur est oublié ensuite.

La cible est la base du serveur (`GESTIONMPPRO_BASE`), la source `GESTIONMPPRO_SOURCE_GESTION_MP`
(`cible()` et `source()` : les essais les remplacent par des bases à eux).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Connection, create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import Verrou
from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import ModeReprise, ObjetJournal, StatutReprise
from gestion_mp_pro.reprise import activite
from gestion_mp_pro.reprise import source as src
from gestion_mp_pro.reprise.contexte import Contexte, Options
from gestion_mp_pro.reprise.execution import derniere_activite, executer
from gestion_mp_pro.services import audit, donnees_moteur, horloge
from gestion_mp_pro.services.comptes import Acteur

JOURNAL = logging.getLogger("gestion_mp_pro.miroir")
EXECUTION = metadata.tables["reprise_execution"]
MOT_DE_CONFIRMATION = "REMPLACER"
NB_EXECUTIONS = 10
_EN_COURS = threading.Lock()
"""Tenu de l'acceptation de la demande à la fin de la reprise (deux clics, deux postes)."""

_VERROU_REPRISE = text(
    "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND granted"
    " AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
    " AND classid = 0 AND objid = :cle AND objsubid = 1)"
)


def cible() -> str:
    """La base de PRO que le miroir remplit (celle du serveur)."""
    return reglages().base


def source() -> str:
    """La base de Gestion MP que le miroir reflète (lue seulement)."""
    return reglages().source_gestion_mp


def dossiers_pieces() -> tuple[Path, Path]:
    """Les pièces jointes de la source (copiées, jamais déplacées) et celles de la cible."""
    r = reglages()
    return (
        r.pieces_gestion_mp / src.nom_de_base(source()),
        r.pieces / src.nom_de_base(cible()),
    )


@dataclass
class Execution:
    """Une exécution de la reprise, telle que l'écran la liste."""

    id: int
    debut: datetime
    fin: datetime | None
    statut: str
    mode: str
    base_source: str
    empreinte_source: str | None
    duree_s: float | None
    rapport: str
    creees: int
    tables: dict[str, dict[str, int]]


@dataclass
class Etat:
    """L'état du miroir (route 243)."""

    base: str
    base_source: str
    signature_source: str | None
    source_lisible: bool
    message_source: str
    a_jour: bool
    activite_propre: bool
    en_cours: bool
    derniere_reussie: Execution | None
    executions: list[Execution] = field(default_factory=list)


def _connexion(url: str) -> Connection:
    """Une connexion à la cible, à l'heure de l'usine."""
    options = {"options": f"-c timezone={reglages().fuseau}"}
    return create_engine(url, poolclass=NullPool, connect_args=options).connect()


def _execution(ligne: Any) -> Execution:
    tables = (ligne.comptes or {}).get("tables", {})
    duree = (ligne.fin - ligne.debut).total_seconds() if ligne.fin else None
    return Execution(
        id=ligne.id,
        debut=ligne.debut,
        fin=ligne.fin,
        statut=str(ligne.statut),
        mode=str(ligne.mode),
        base_source=ligne.base_source,
        empreinte_source=ligne.empreinte_source,
        duree_s=duree,
        rapport=ligne.rapport or "",
        creees=sum(int(c.get("creees", 0)) for c in tables.values()),
        tables={t: {k: int(v) for k, v in c.items()} for t, c in sorted(tables.items())},
    )


@dataclass
class _Cible:
    """Ce que `reprise.activite` lit d'un contexte pour l'empreinte de la cible : sa connexion."""

    c: Connection


def activite_propre(c: Connection) -> bool:
    """Vrai si la cible porte une activité que la dernière reprise n'a pas écrite (saisie dans
    PRO, ou reprise d'une autre source) : la règle même de la reprise (`activite.decider`)."""
    ctx = cast(Contexte, _Cible(c))
    if activite._vide(ctx):  # noqa: SLF001 — la règle de R1, sans la recopier
        return False
    derniere = derniere_activite(c)
    return derniere is None or derniere.get("cible") != activite.empreinte_cible(ctx)


def _signature() -> tuple[str | None, str]:
    """La signature actuelle de la source, ou pourquoi elle ne se lit pas."""
    try:
        return src.empreinte_actuelle(source()), ""
    except Exception as exc:  # noqa: BLE001 — base absente, droits, schéma : dit à l'écran
        JOURNAL.warning("source du miroir illisible : %s", exc)
        return None, f"Base de Gestion MP « {src.nom_de_base(source())} » illisible : {exc}"[:500]


def etat() -> Etat:
    """L'état du miroir : exécutions, signature de la source, à jour, activité propre."""
    signature, message = _signature()
    with _connexion(cible()) as c:
        lignes = c.execute(
            select(EXECUTION).order_by(EXECUTION.c.id.desc()).limit(NB_EXECUTIONS)
        ).all()
        reussie = c.execute(
            select(EXECUTION)
            .where(EXECUTION.c.statut == StatutReprise.reussie.value)
            .order_by(EXECUTION.c.id.desc())
            .limit(1)
        ).first()
        propre = activite_propre(c)
        verrou = bool(c.execute(_VERROU_REPRISE, {"cle": int(Verrou.REPRISE)}).scalar())
    derniere = _execution(reussie) if reussie else None
    return Etat(
        base=src.nom_de_base(cible()),
        base_source=src.nom_de_base(source()),
        signature_source=signature,
        source_lisible=signature is not None,
        message_source=message,
        a_jour=derniere is not None and signature == derniere.empreinte_source,
        activite_propre=propre,
        en_cours=verrou or _EN_COURS.locked(),
        derniere_reussie=derniere,
        executions=[_execution(x) for x in lignes],
    )


@dataclass(frozen=True)
class Demande:
    """Une reprise acceptée : ses options et l'instant de l'acceptation."""

    options: Options
    debut: datetime


def _verifier(remplacer: bool, confirmation: str | None) -> None:
    """La confirmation tapée, puis l'état de la cible (activité propre, reprise en cours)."""
    if remplacer and (confirmation or "").strip().upper() != MOT_DE_CONFIRMATION:
        raise Refus.saisie(
            f"Dernière confirmation : taper {MOT_DE_CONFIRMATION} pour remplacer l'activité "
            "saisie dans PRO.",
            code="confirmation_requise",
            champs={"confirmation": MOT_DE_CONFIRMATION},
        )
    with _connexion(cible()) as c:
        if c.execute(_VERROU_REPRISE, {"cle": int(Verrou.REPRISE)}).scalar():
            raise Refus.etat("Une reprise est déjà en cours.", code="tache_en_cours")
        if not remplacer and activite_propre(c):
            raise Refus.etat(
                "La base de PRO contient une activité saisie dans PRO (elle ne vient pas de la "
                "dernière reprise) : rien n'est fait. Pour la remplacer par celle de Gestion MP, "
                f"cocher « Remplacer l'activité » et taper {MOT_DE_CONFIRMATION} (une sauvegarde "
                "« avant reprise » est faite d'abord).",
                code="activite_presente",
            )


def _journaliser(s: Session, qui: Acteur, mode: ModeReprise, remplacer: bool) -> None:
    """« reprise demandée » au journal, au nom de qui la lance, dans la transaction de la
    requête (la reprise ajoute sa propre ligne, « reprise de Gestion MP », à la fin)."""
    detail = f"{src.nom_de_base(source())} · {mode.value}"
    audit.journal(
        s,
        qui,
        "reprise demandée",
        ObjetJournal.reprise,
        detail=detail + (" · activité remplacée" if remplacer else ""),
    )


def accepter(
    s: Session, qui: Acteur, mode: ModeReprise, remplacer: bool, confirmation: str | None
) -> Demande:
    """Refuse ce qui ne se lance pas ; sinon réserve la reprise (rendue par `lancer`)."""
    if not _EN_COURS.acquire(blocking=False):
        raise Refus.etat("Une reprise est déjà en cours.", code="tache_en_cours")
    try:
        _verifier(remplacer, confirmation)
        signature, message = _signature()
        if signature is None:
            raise Refus.indisponible(message, code="base_indisponible")
        _journaliser(s, qui, mode, remplacer)
    except BaseException:
        _EN_COURS.release()
        raise
    pieces_source, pieces_cible = dossiers_pieces()
    options = Options(
        source=source(),
        cible=cible(),
        mode=mode,
        remplacer_activite=remplacer,
        pieces_source=str(pieces_source),
        pieces_cible=str(pieces_cible),
    )
    return Demande(options, horloge.maintenant())


def lancer(demande: Demande) -> None:
    """La reprise elle-même (tâche de fond) : son issue est inscrite dans `reprise_execution`
    (réussie, échouée avec sa raison) ; un refus tardif est inscrit au journal du serveur."""
    try:
        resultat = executer(demande.options)
        JOURNAL.info("miroir rafraîchi : %s", "réussi" if resultat.reussie else "échoué")
    except Exception:
        JOURNAL.exception("miroir : reprise refusée ou interrompue")
    finally:
        donnees_moteur.invalider()
        _EN_COURS.release()
