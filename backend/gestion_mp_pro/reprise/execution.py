"""Une exécution de la reprise, de la photo de la source au rapport (ARCHITECTURE § 14.2).

Ordre : garde-fous (noms des bases, schéma de la cible à jour) → photo de la source (lecture
seule vérifiée) → sauvegarde « avant reprise » de la cible → **une seule transaction** sur la
cible, sous le verrou consultatif REPRISE : personnes, référentiels, journal, journal en
tables, activité, pièces, compteurs, séquences, textes de recherche, contrôle → empreinte de
la source relue → validation (ou annulation pour `--essai`). Une exécution qui échoue est
inscrite « échouée » (avec la raison) dans une transaction à part.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, create_engine, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import Verrou, verrouiller
from gestion_mp_pro.modeles import metadata
from gestion_mp_pro.modeles.enums import GenreSauvegarde, ModeReprise, SourceReprise, StatutReprise
from gestion_mp_pro.reprise import etapes, rapport, sauvegarde, source
from gestion_mp_pro.reprise.contexte import Contexte, Options
from gestion_mp_pro.reprise.normalisation import Normalisation
from gestion_mp_pro.services import horloge

EXECUTION = metadata.tables["reprise_execution"]


class RepriseRefusee(Exception):
    """La reprise ne peut pas commencer (garde-fou) ou a été annulée (contrôle non tenu)."""


@dataclass(frozen=True)
class Resultat:
    """Ce que rend une exécution."""

    execution_id: int | None
    reussie: bool
    rapport: str
    comptes: dict[str, Any]


def cible_permise(url: str) -> str:
    """Le nom de la base cible ; refus s'il n'est pas `gestion_mp_pro` ou `gestion_mp_pro_*`."""
    nom = make_url(url).database or ""
    if nom != "gestion_mp_pro" and not nom.startswith("gestion_mp_pro_"):
        raise RepriseRefusee(
            f"base cible « {nom} » refusée : seules gestion_mp_pro(_*) sont permises"
        )
    return nom


def genre_de(photo: source.Photo) -> SourceReprise:
    """`erp_fil` pour une base dont l'activité vient de l'ERP Fil, sinon `gestion_mp`."""
    erp = any(j["action"] == "reprise classeur" for j in photo.lignes("journal")) or any(
        m["document"] == "reprise" for m in photo.lignes("mouvement")
    )
    return SourceReprise.erp_fil if erp else SourceReprise.gestion_mp


def _connexion(url: str) -> Connection:
    """Connexion à la cible, à l'heure de l'usine, sans délai maximal de requête."""
    options = f"-c timezone={reglages().fuseau} -c statement_timeout=0"
    return create_engine(url, poolclass=NullPool, connect_args={"options": options}).connect()


def _schema_a_jour(c: Connection) -> None:
    """La cible doit être migrée (table `alembic_version` et les tables de la reprise)."""
    present = c.execute(text("SELECT to_regclass('public.reprise_execution') IS NOT NULL")).scalar()
    if not present:
        raise RepriseRefusee("la base cible n'est pas migrée (alembic upgrade head d'abord)")


def _ouvrir(ctx: Contexte) -> int:
    """Inscrit l'exécution « en cours »."""
    return int(
        ctx.c.execute(
            insert(EXECUTION).returning(EXECUTION.c.id),
            {
                "source": ctx.source.value,
                "base_source": ctx.photo.base,
                "empreinte_source": ctx.photo.empreinte,
                "mode": ctx.options.mode.value,
                "debut": horloge.maintenant(),
            },
        ).scalar_one()
    )


def derniere_activite(c: Connection) -> dict[str, Any] | None:
    """Ce que la dernière reprise réussie a écrit de l'activité (empreintes)."""
    comptes = c.execute(
        select(EXECUTION.c.comptes)
        .where(
            EXECUTION.c.statut == StatutReprise.reussie.value,
            EXECUTION.c.comptes.has_key("activite"),
        )
        .order_by(EXECUTION.c.id.desc())
        .limit(1)
    ).scalar()
    return comptes["activite"] if comptes else None


def _echec(url: str, options: Options, photo: source.Photo | None, raison: str) -> None:
    """Inscrit une exécution échouée (transaction à part : la reprise a été annulée)."""
    with _connexion(url) as c, c.begin():
        instant = horloge.maintenant()
        c.execute(
            insert(EXECUTION),
            {
                "source": (options.genre or SourceReprise.gestion_mp).value,
                "base_source": photo.base if photo else source.nom_de_base(options.source),
                "empreinte_source": photo.empreinte if photo else None,
                "mode": options.mode.value,
                "debut": instant,
                "fin": instant,
                "statut": StatutReprise.echouee.value,
                "rapport": raison[:5000],
            },
        )


def executer(options: Options) -> Resultat:
    """Lance une reprise ; lève `RepriseRefusee` (rien n'est écrit) ou rend le résultat."""
    debut = time.monotonic()
    nom_cible = cible_permise(options.cible)
    if source.nom_de_base(options.source) == nom_cible:
        raise RepriseRefusee("la source et la cible sont la même base")
    photo = None
    try:
        photo = source.photographier(options.source)
        if options.sauvegarder and not options.essai:
            fichier = sauvegarde.sauvegarder(options.cible, GenreSauvegarde.avant_reprise)
        else:
            fichier = None
        return _dans_la_cible(options, photo, fichier, nom_cible, debut)
    except Exception as exc:
        if not options.essai and not isinstance(exc, RepriseRefusee | source.SourceRefusee):
            _echec(options.cible, options, photo, f"{type(exc).__name__} : {exc}")
        raise


def _dans_la_cible(
    options: Options,
    photo: source.Photo,
    fichier: sauvegarde.Fichier | None,
    nom: str,
    debut: float,
) -> Resultat:
    """La transaction unique sur la cible."""
    with _connexion(options.cible) as c:
        transaction = c.begin()
        _schema_a_jour(c)
        verrouiller(c, Verrou.REPRISE)
        if fichier:
            sauvegarde.inscrire(c, fichier, GenreSauvegarde.avant_reprise, nom)
        ctx = Contexte(
            options, photo, c, Normalisation(reglages().zone), options.genre or genre_de(photo)
        )
        ident = _ouvrir(ctx)
        verdicts = etapes.derouler(ctx, derniere_activite(c), ident)
        apres = source.empreinte_actuelle(options.source)
        texte = rapport.rediger(ctx, verdicts, apres, time.monotonic() - debut)
        reussie = all(v.tenu for v in verdicts) and apres == photo.empreinte
        comptes: dict[str, Any] = {"tables": dict(ctx.comptes)}
        if ctx.activite_reprise or ctx.empreintes_activite:
            comptes["activite"] = ctx.empreintes_activite
        c.execute(
            update(EXECUTION)
            .where(EXECUTION.c.id == ident)
            .values(
                fin=horloge.maintenant(),
                comptes=comptes,
                rapport=texte,
                statut=(StatutReprise.reussie if reussie else StatutReprise.echouee).value,
            )
        )
        etapes.journaliser(ctx, ident, reussie)
        if options.essai or not reussie:
            transaction.rollback()
        else:
            transaction.commit()
    if not reussie and not options.essai:
        _echec(options.cible, options, photo, texte)
    return Resultat(None if options.essai or not reussie else ident, reussie, texte, comptes)


MODES_REFERENTIELS = (ModeReprise.referentiels, ModeReprise.tout)
MODES_ACTIVITE = (ModeReprise.activite, ModeReprise.tout)
