"""Migrations Alembic (lot S1, MODELE-DONNEES § 9) : révisions contiguës et autonomes, base vide
migrée puis relancée, aller-retour complet, `alembic check` vide, deux processus à la fois,
schéma migré identique à celui des modèles.

Ces essais vident la base d'essai ; chacun la rend migrée à la tête, semences comprises.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Connection, text

from gestion_mp_pro import modeles
from gestion_mp_pro.db import moteur
from gestion_mp_pro.services import installation

VERSIONS = installation.MIGRATIONS / "versions"
REVISIONS = sorted(p for p in VERSIONS.glob("[0-9]*.py"))


def _vider() -> None:
    """Rend la base vide (schéma `public` recréé)."""
    with moteur().begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))


@pytest.fixture
def base_vide() -> Iterator[None]:
    """Une base vide pour l'essai ; migrée à la tête ensuite, quoi qu'il arrive."""
    _vider()
    yield
    installation.migrer()


def _tables(c: Connection) -> set[str]:
    return set(
        c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
    )


def test_revisions_numerotees_et_contigues() -> None:
    assert REVISIONS, "aucune révision"
    precedente = None
    for rang, fichier in enumerate(REVISIONS, start=1):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        valeurs = {
            n.targets[0].id: ast.literal_eval(n.value)
            for n in arbre.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in {"revision", "down_revision"}
        }  # fmt: skip
        assert valeurs["revision"] == f"{rang:04d}"
        assert fichier.name.startswith(f"{rang:04d}_")
        assert valeurs["down_revision"] == precedente
        precedente = valeurs["revision"]
    assert installation.revision_attendue() == precedente


def test_aucune_revision_n_importe_le_paquet() -> None:
    for fichier in REVISIONS:
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        modules = {a.name for n in ast.walk(arbre) if isinstance(n, ast.Import) for a in n.names}
        modules |= {n.module or "" for n in ast.walk(arbre) if isinstance(n, ast.ImportFrom)}
        racines = {mod.split(".")[0] for mod in modules}
        assert racines <= {"__future__", "alembic", "sqlalchemy"}, fichier.name


def test_base_vide_migree_puis_relancee_ne_fait_rien(base_vide: None) -> None:
    assert installation.schema_en_retard()
    assert installation.migrer() == [r.name[:4] for r in REVISIONS]
    assert installation.migrer() == []
    assert not installation.schema_en_retard()
    with moteur().connect() as c:
        assert len(_tables(c)) == 71
        assert installation.semences_manquantes(c) == []


def test_aller_retour_complet(base_vide: None) -> None:
    installation.migrer()
    cfg = installation.configuration()
    with moteur().connect() as c, c.begin():
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "base")
        assert _tables(c) == {"alembic_version"}
        fonctions = c.execute(text("SELECT count(*) FROM pg_proc WHERE proname LIKE 'fn\\_%'"))
        assert fonctions.scalar() == 0
        assert (
            c.execute(text("SELECT count(*) FROM pg_extension WHERE extname = 'pg_trgm'")).scalar()
            == 0
        )
        command.upgrade(cfg, "0001")
    assert installation.schema_en_retard()
    with moteur().connect() as c:
        assert c.execute(text("SELECT count(*) FROM parametre")).scalar() == 0
    assert installation.migrer() == ["0002"]
    assert not installation.schema_en_retard()


def test_alembic_check_ne_trouve_aucun_ecart() -> None:
    cfg = installation.configuration()
    with moteur().connect() as c:
        cfg.attributes["connection"] = c
        command.check(cfg)


def test_deux_processus_une_seule_application(base_vide: None) -> None:
    programme = (
        "import json; from gestion_mp_pro.services.installation import migrer;"
        " print(json.dumps(migrer()))"
    )
    env = {**os.environ, "GESTIONMPPRO_TACHES": "0"}
    racine = Path(__file__).resolve().parents[1]
    processus = [
        subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", programme],
            cwd=racine,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    sorties = []
    for p in processus:
        sortie, erreur = p.communicate(timeout=120)
        assert p.returncode == 0, erreur
        sorties.append(json.loads(sortie.strip().splitlines()[-1]))
    assert sorted(sorties) == [[], [r.name[:4] for r in REVISIONS]]
    assert not installation.schema_en_retard()


def _schema(c: Connection, nom: str) -> dict[str, set[tuple[str, ...]]]:
    """Colonnes, contraintes et index d'un schéma, sans son nom (pour comparer deux schémas)."""

    def lignes(sql: str) -> set[tuple[str, ...]]:
        resultat = c.execute(text(sql), {"s": nom}).all()
        return {tuple(str(v).replace(f"{nom}.", "") for v in r) for r in resultat}

    return {
        "colonnes": lignes(
            "SELECT table_name, column_name, data_type, coalesce(character_maximum_length, 0),"
            " coalesce(numeric_precision, 0), coalesce(numeric_scale, 0), is_nullable,"
            " coalesce(column_default, ''), is_identity, is_generated,"
            " coalesce(generation_expression, '') FROM information_schema.columns"
            " WHERE table_schema = :s AND table_name <> 'alembic_version'"
        ),
        "contraintes": lignes(
            "SELECT r.relname, c.conname, c.contype, pg_get_constraintdef(c.oid)"
            " FROM pg_constraint c JOIN pg_class r ON r.oid = c.conrelid"
            " JOIN pg_namespace n ON n.oid = r.relnamespace"
            " WHERE n.nspname = :s AND r.relname <> 'alembic_version' AND c.contype <> 't'"
        ),
        "index": lignes(
            "SELECT tablename, indexname, indexdef FROM pg_indexes"
            " WHERE schemaname = :s AND tablename <> 'alembic_version'"
        ),
    }


def test_schema_migre_identique_au_schema_des_modeles() -> None:
    with moteur().connect() as c, c.begin():
        c.execute(text("DROP SCHEMA IF EXISTS modele_essai CASCADE"))
        c.execute(text("CREATE SCHEMA modele_essai"))
        traduit = c.execution_options(schema_translate_map={None: "modele_essai"})
        modeles.metadata.create_all(traduit)
        migre, modele = _schema(c, "public"), _schema(c, "modele_essai")
        c.rollback()
    for partie in ("colonnes", "contraintes", "index"):
        assert migre[partie] - modele[partie] == set(), partie
        assert modele[partie] - migre[partie] == set(), partie
    assert len(migre["contraintes"]) > 500


def test_declencheurs_poses_par_la_migration() -> None:
    with moteur().connect() as c:
        noms = c.execute(
            text("SELECT tgname, tgrelid::regclass::text FROM pg_trigger WHERE NOT tgisinternal")
        ).all()
    assert {tuple(n) for n in noms} == {
        ("tr_mouvement_immuable", "mouvement"),
        ("tr_operation_type_fige", "operation"),
        ("tr_matiere_lineaire_densite", "matiere"),
    }
