"""Comparaison avec Gestion MP en service (lot C1) : les mêmes données dans les deux logiciels.

1. La base de Gestion MP choisie (`gestion_mp`, la production telle qu'elle est, ou
   `gestion_mp_comparaison`, l'année d'essai) est copiée par `pg_dump` (lecture seule) dans une
   base d'essai : Gestion MP ne calcule et ne sert que sur la copie.
2. PRO : la copie est reprise dans une base PRO neuve (ce que fait `make miroir`), ou une base PRO
   existante (le miroir installé) est **copiée** à son tour — jamais ouverte en écriture.
3. **Même base** : la signature de la copie (empreinte de R1) doit égaler celle de la dernière
   reprise réussie de la base PRO comparée ; sinon la comparaison est refusée, ou la reprise est
   relancée **sur la copie de PRO** (`--resynchroniser`).
4. Empreintes de `gestion_mp` et de la source relevées avant et après : elles doivent être égales.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import parite_bases as pb
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


class Desynchronisees(Exception):
    """La base PRO comparée ne reflète pas la base de Gestion MP comparée."""


def verifier_synchronisation(signature_source: str | None, signature_reprise: str | None) -> None:
    """Refuse de comparer deux bases désynchronisées (aucune reprise, ou source changée depuis)."""
    if signature_reprise is None:
        raise Desynchronisees(
            "La base PRO n'a aucune reprise réussie : rien ne dit qu'elle reflète Gestion MP. "
            "Rafraîchir le miroir (make miroir), ou relancer avec --resynchroniser."
        )
    if signature_source != signature_reprise:
        raise Desynchronisees(
            f"Gestion MP a changé depuis la dernière reprise de PRO (signature "
            f"{(signature_source or '—')[:16]}… contre {signature_reprise[:16]}…) : les deux "
            "bases sont désynchronisées. Rafraîchir le miroir, ou relancer avec --resynchroniser."
        )


def signature_derniere_reprise(adresse: str) -> str | None:
    """La signature de la source relevée par la dernière reprise réussie d'une base PRO."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        valeur = c.execute(
            text(
                "SELECT empreinte_source FROM reprise_execution WHERE statut = 'reussie' "
                "ORDER BY id DESC LIMIT 1"
            )
        ).scalar()
    moteur.dispose()
    return str(valeur) if valeur else None


def copier_pro(source: str, adresse: str) -> None:
    """`pg_dump` d'une base PRO existante (lecture) → copie d'essai (rôles et droits retirés)."""
    from gestion_mp_pro.reprise.sauvegarde import outil

    pb.creer(adresse)
    dump = subprocess.run(  # noqa: S603
        [outil("pg_dump"), "-Fc", "--no-owner", "--no-acl", source], capture_output=True, check=True
    )
    subprocess.run(  # noqa: S603
        [outil("pg_restore"), "--no-owner", "--no-acl", "-d", adresse.replace("+psycopg", "")],
        input=dump.stdout,
        capture_output=True,
        check=True,
    )


@dataclass
class Preparation:
    """Ce que la préparation a fait."""

    source: str
    rapport: str
    avant: dict[str, str]
    apres: dict[str, str] = field(default_factory=dict)
    signature_copie: str = ""
    signature_pro: str = ""
    pro_existante: str | None = None
    resynchronisee: bool = False

    @property
    def source_intacte(self) -> bool:
        """Les bases de Gestion MP n'ont pas bougé pendant la comparaison."""
        return self.avant == self.apres


def empreintes(source: str) -> dict[str, str]:
    """L'empreinte de la base en service et de la source comparée (lecture seule)."""
    from gestion_mp_pro.reprise import source as src

    return {nom: src.empreinte_actuelle(pb.url(nom)) for nom in dict.fromkeys((pb.SERVICE, source))}


def _rapport_derniere(adresse: str) -> str:
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.connect() as c:
        valeur = c.execute(
            text("SELECT rapport FROM reprise_execution WHERE statut = 'reussie' ORDER BY id DESC")
        ).scalar()
    moteur.dispose()
    return str(valeur or "")


def preparer(
    source: str, bases: pb.Bases, pro_existante: str | None = None, resynchroniser: bool = False
) -> Preparation:
    """Copie la source ; reprend la copie dans PRO (ou copie la base PRO donnée et vérifie
    qu'elle est synchronisée) ; relève les empreintes avant et après."""
    from gestion_mp_pro.reprise import source as src

    p = Preparation(source, "", empreintes(source), pro_existante=pro_existante)
    pb.copier(source, bases.copie)
    p.signature_copie = src.empreinte_actuelle(bases.copie)
    if pro_existante is None:
        p.rapport = pb.reprendre(bases.copie, bases.pro)
    else:
        copier_pro(pro_existante, bases.pro)
        try:
            verifier_synchronisation(p.signature_copie, signature_derniere_reprise(bases.pro))
            p.rapport = _rapport_derniere(bases.pro)
        except Desynchronisees:
            if not resynchroniser:
                raise
            p.rapport = _reprendre_dans(bases.copie, bases.pro)
            p.resynchronisee = True
    p.signature_pro = signature_derniere_reprise(bases.pro) or ""
    verifier_synchronisation(p.signature_copie, p.signature_pro)
    p.apres = empreintes(source)
    return p


def _reprendre_dans(copie: str, cible: str) -> str:
    """La reprise relancée sur la copie de la base PRO (activité remplacée, sans sauvegarde)."""
    import tempfile

    from gestion_mp_pro.modeles.enums import ModeReprise
    from gestion_mp_pro.reprise.contexte import Options
    from gestion_mp_pro.reprise.execution import executer

    with tempfile.TemporaryDirectory(prefix="comparaison-pieces-") as dossier:
        r = executer(
            Options(
                source=copie,
                cible=cible,
                mode=ModeReprise.tout,
                remplacer_activite=True,
                sauvegarder=False,
                pieces_source=str(Path(dossier) / "source"),
                pieces_cible=str(Path(dossier) / "cible"),
            )
        )
    if not r.reussie:
        raise SystemExit(f"Reprise non tenue :\n{r.rapport}")
    return r.rapport
