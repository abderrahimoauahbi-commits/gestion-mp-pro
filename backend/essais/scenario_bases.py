"""Les bases du scénario (lot V2) : toutes à notre nom, finissant par `_essai`, supprimées après.

- **Complet** : `gestion_mp_comparaison` (l'année d'essai de l'ERP Fil importée dans Gestion MP,
  ouverte en lecture seule par `pg_dump`) est copiée dans `<préfixe>_source_essai`, puis reprise
  par la reprise de R1 (mêmes règles que la mise en service) dans `<préfixe>_essai` : le scénario
  joue sur une copie de l'année de parité, référentiels réels compris. Les empreintes de
  `gestion_mp` et `gestion_mp_comparaison` sont relevées avant et après (aucune écriture).
- **Court** (essai pytest) : une base neuve migrée (semences seules).
- Gestion MP (parité dynamique) : une seconde copie, `<préfixe>_gmp_essai`, servie par son code.

Comptes : la base reprise contient les comptes historiques de Gestion MP (inactifs) ; elle est
donc « installée » et `POST /installation` refuse. Le compte de direction du scénario y est posé
comme l'installation le pose (identifiant, nom, rôle, empreinte scrypt du code), sans session :
il se connecte ensuite par `POST /connexion`, et c'est lui qui crée les trois autres comptes
par l'API.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

SOURCE = "gestion_mp_comparaison"
"""L'année d'essai dans Gestion MP (lue par `pg_dump`, jamais ouverte en écriture)."""
EN_SERVICE = "gestion_mp"


def url(nom: str) -> str:
    """L'adresse SQLAlchemy d'une base locale."""
    return f"postgresql+psycopg:///{nom}"


def garde_fou(adresse: str) -> str:
    """Le nom de la base, refusé s'il n'est pas `gestion_mp_pro_…_essai`."""
    nom = make_url(adresse).database or ""
    if not (nom.startswith("gestion_mp_pro_") and nom.endswith("_essai")):
        raise SystemExit(f"Base refusée : « {nom} » (gestion_mp_pro_…_essai exigé)")
    return nom


def _maintenance() -> object:
    return create_engine(url("postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT")


def supprimer(adresse: str) -> None:
    """Supprime une base d'essai (rien si elle n'existe pas)."""
    nom = garde_fou(adresse)
    moteur = _maintenance()
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
    moteur.dispose()  # type: ignore[attr-defined]


def creer(adresse: str) -> None:
    """Supprime puis recrée une base d'essai vide."""
    nom = garde_fou(adresse)
    supprimer(adresse)
    moteur = _maintenance()
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'CREATE DATABASE "{nom}"'))
    moteur.dispose()  # type: ignore[attr-defined]


def cloner(modele: str, adresse: str) -> None:
    """Une base d'essai clonée d'une autre base d'essai (`CREATE DATABASE … TEMPLATE`)."""
    nom, gabarit = garde_fou(adresse), garde_fou(url(modele) if "/" not in modele else modele)
    moteur = _maintenance()
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'CREATE DATABASE "{nom}" TEMPLATE "{gabarit}"'))
    moteur.dispose()  # type: ignore[attr-defined]


def copier(source: str, adresse: str) -> None:
    """`pg_dump` de la source (lecture seule) → `pg_restore` dans une base d'essai neuve."""
    from gestion_mp_pro.reprise.sauvegarde import outil

    creer(adresse)
    dump = subprocess.run(  # noqa: S603 — outils PostgreSQL, arguments à nous
        [outil("pg_dump"), "-Fc", source], capture_output=True, check=True
    )
    subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--no-owner", "-d", adresse.replace("+psycopg", "")],
        input=dump.stdout,
        capture_output=True,
        check=True,
    )


def migrer(adresse: str) -> None:
    """Une base PRO neuve, migrée à `head` (semences comprises)."""
    from alembic import command

    from gestion_mp_pro.services.installation import configuration

    creer(adresse)
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c, c.begin():
        cfg = configuration()
        cfg.attributes["connection"] = c
        command.upgrade(cfg, "head")
    moteur.dispose()


def empreintes() -> dict[str, str]:
    """Empreintes de la base en service et de la source (lecture seule, comme R1)."""
    from gestion_mp_pro.reprise import source as src

    return {nom: src.empreinte_actuelle(url(nom)) for nom in (EN_SERVICE, SOURCE)}


def reprendre(copie: str, cible: str) -> str:
    """La reprise de R1, copie → base PRO neuve ; rend son rapport (contrôle d'import)."""
    from gestion_mp_pro.modeles.enums import ModeReprise
    from gestion_mp_pro.reprise.contexte import Options
    from gestion_mp_pro.reprise.execution import executer

    migrer(cible)
    with tempfile.TemporaryDirectory(prefix="scenario-pieces-") as dossier:
        options = Options(
            source=copie,
            cible=cible,
            mode=ModeReprise.tout,
            sauvegarder=False,
            pieces_source=str(Path(dossier) / "source"),
            pieces_cible=str(Path(dossier) / "cible"),
        )
        r = executer(options)
    if not r.reussie or "NON TENU" in r.rapport:
        raise SystemExit(f"Reprise non tenue :\n{r.rapport}")
    return r.rapport


def poser_direction(adresse: str, identifiant: str, nom: str, code: str) -> None:
    """Le compte de direction du scénario, posé comme l'installation le pose (sans session)."""
    from gestion_mp_pro.services import comptes

    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        c.execute(
            text(
                "INSERT INTO utilisateur (identifiant, nom, role, empreinte_code, actif) "
                "VALUES (:i, :n, 'direction', :e, true)"
            ),
            {"i": identifiant, "n": nom, "e": comptes.hacher(code)},
        )
    moteur.dispose()


def lire(adresse: str, requete: str, **parametres: object) -> list[tuple[object, ...]]:
    """Une lecture SQL (contrôle d'état de la base : empreintes, comptes)."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        lignes = [tuple(x) for x in c.execute(text(requete), parametres)]
    moteur.dispose()
    return lignes
