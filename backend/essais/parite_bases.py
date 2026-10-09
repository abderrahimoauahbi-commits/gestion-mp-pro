"""Parité (PLAN-DE-RECETTE-PRO § 7.1) : les mêmes données dans les deux logiciels.

1. `gestion_mp_comparaison` (l'année d'essai de l'ERP Fil importée dans Gestion MP) est copiée
   par `pg_dump` (lecture seule) dans une base d'essai : Gestion MP ne calcule que sur la copie.
2. La copie est reprise dans une base PRO neuve par la reprise de R1 (mêmes règles que la mise
   en service).
3. Les empreintes de `gestion_mp` et de `gestion_mp_comparaison` sont relevées avant et après :
   elles doivent être égales (aucune écriture).

Les noms des deux bases d'essai finissent par `_essai` (garde-fou des consignes) ; leur préfixe
vient de `GESTIONMPPRO_PARITE_PREFIXE` (défaut `gestion_mp_pro_parite`).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

SOURCE = "gestion_mp_comparaison"
"""L'année d'essai dans Gestion MP (jamais ouverte en écriture)."""
SERVICE = "gestion_mp"
"""La base de Gestion MP en service : son empreinte doit rester la même."""
GESTION_MP = Path(os.environ.get("GESTION_MP_CODE", str(Path.home() / "gestion-mp")))
PYTHON_GESTION_MP = GESTION_MP / ".venv" / "bin" / "python"


def url(nom: str) -> str:
    """L'adresse SQLAlchemy d'une base locale."""
    return f"postgresql+psycopg:///{nom}"


@dataclass(frozen=True)
class Bases:
    """Les deux bases d'essai de la parité."""

    prefixe: str = field(
        default_factory=lambda: os.environ.get(
            "GESTIONMPPRO_PARITE_PREFIXE", "gestion_mp_pro_parite"
        )
    )

    @property
    def copie(self) -> str:
        """La copie de `gestion_mp_comparaison` (schéma de Gestion MP)."""
        return url(f"{self.prefixe}_source_essai")

    @property
    def pro(self) -> str:
        """La base PRO reprise de la copie."""
        return url(f"{self.prefixe}_cible_essai")

    def toutes(self) -> tuple[str, str]:
        """Les deux adresses."""
        return (self.copie, self.pro)


def _garde_fou(adresse: str) -> str:
    nom = make_url(adresse).database or ""
    if not (nom.startswith("gestion_mp_pro_") and nom.endswith("_essai")):
        raise SystemExit(f"Base refusée : « {nom} » (gestion_mp_pro_…_essai exigé)")
    return nom


def _maintenance(adresse: str) -> object:
    cible = make_url(adresse).set(database="postgres")
    return create_engine(cible, poolclass=NullPool, isolation_level="AUTOCOMMIT")


def creer(adresse: str) -> None:
    """Supprime puis recrée une base d'essai."""
    nom = _garde_fou(adresse)
    moteur = _maintenance(adresse)
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
        c.execute(text(f'CREATE DATABASE "{nom}"'))
    moteur.dispose()  # type: ignore[attr-defined]


def supprimer(adresse: str) -> None:
    """Supprime une base d'essai (sans erreur si elle n'existe pas)."""
    nom = _garde_fou(adresse)
    moteur = _maintenance(adresse)
    with moteur.connect() as c:  # type: ignore[attr-defined]
        c.execute(text(f'DROP DATABASE IF EXISTS "{nom}" WITH (FORCE)'))
    moteur.dispose()  # type: ignore[attr-defined]


def copier(source: str, adresse: str) -> None:
    """`pg_dump` de la source (lecture seule) → `pg_restore` dans la copie d'essai."""
    from gestion_mp_pro.reprise.sauvegarde import outil

    creer(adresse)
    dump = subprocess.run(  # noqa: S603
        [outil("pg_dump"), "-Fc", source], capture_output=True, check=True
    )
    subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--no-owner", "-d", adresse.replace("+psycopg", "")],
        input=dump.stdout,
        capture_output=True,
        check=True,
    )


def empreintes() -> dict[str, str]:
    """L'empreinte de la base en service et de la source de la parité (lecture seule)."""
    from gestion_mp_pro.reprise import source as src

    return {nom: src.empreinte_actuelle(url(nom)) for nom in (SERVICE, SOURCE)}


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


@dataclass
class Preparation:
    """Ce que la préparation a fait : rapport de reprise, empreintes avant et après."""

    rapport: str
    avant: dict[str, str]
    apres: dict[str, str]

    @property
    def source_intacte(self) -> bool:
        """Les empreintes de `gestion_mp` et de `gestion_mp_comparaison` n'ont pas bougé."""
        return self.avant == self.apres


def reprendre(copie: str, cible: str) -> str:
    """La reprise de R1, copie → base PRO neuve ; rend son rapport (contrôle d'import)."""
    from gestion_mp_pro.modeles.enums import ModeReprise
    from gestion_mp_pro.reprise.contexte import Options
    from gestion_mp_pro.reprise.execution import executer

    migrer(cible)
    with tempfile.TemporaryDirectory(prefix="parite-pieces-") as dossier:
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


def preparer(bases: Bases) -> Preparation:
    """Copie la source, la reprend dans PRO, relève les empreintes avant et après."""
    avant = empreintes()
    copier(SOURCE, bases.copie)
    rapport = reprendre(bases.copie, bases.pro)
    return Preparation(rapport, avant, empreintes())


def nettoyer(bases: Bases) -> None:
    """Supprime les deux bases d'essai."""
    for adresse in bases.toutes():
        supprimer(adresse)
