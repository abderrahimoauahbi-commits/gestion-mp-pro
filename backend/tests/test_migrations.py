"""Migrations Alembic (lot S1, MODELE-DONNEES § 9) : révisions contiguës et autonomes, base vide
migrée puis relancée, aller-retour complet, `alembic check` vide, deux processus à la fois,
schéma migré identique à celui des modèles.

Ces essais vident la base d'essai ; chacun la rend migrée à la tête, semences comprises.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

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
        assert len(_tables(c)) == 73
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
    assert installation.migrer() == [
        "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009",
    ]  # fmt: skip
    assert not installation.schema_en_retard()


def _cles_reglages(c: Connection) -> tuple[int, int]:
    """(réglages semés, clés admises par `ck_parametre_cle_connue`)."""
    semes = c.execute(text("SELECT count(*) FROM parametre")).scalar()
    definition = c.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conname = 'ck_parametre_cle_connue'"
        )
    ).scalar()
    return int(semes or 0), str(definition).count("::character varying")


def test_0003_tolerance_tva_import_aller_retour(base_vide: None) -> None:
    installation.migrer()
    cfg = installation.configuration()
    with moteur().connect() as c, c.begin():
        assert _cles_reglages(c) == (58, 58)
        c.execute(
            text(
                "INSERT INTO parametre_historique (cle, avant, apres)"
                " VALUES ('toler_tva_import', '0.05', '0.1')"
            )
        )
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0002")
        assert _cles_reglages(c) == (56, 56)
        refus = c.begin_nested()
        with pytest.raises(SQLAlchemyError):
            c.execute(text("INSERT INTO parametre (cle) VALUES ('toler_tva_import')"))
        refus.rollback()
        command.upgrade(cfg, "head")
        assert _cles_reglages(c) == (58, 58)
        valeur = "SELECT valeur FROM parametre WHERE cle = 'toler_tva_import'"
        assert c.execute(text(valeur)).scalar() == "0.05"
    assert not installation.schema_en_retard()


def test_0009_seuil_rebut_aller_retour(base_vide: None) -> None:
    """0009 (lot FOND-DE-LOT) : la clé `seuil_rebut` (0.1) et le motif « Rebut » ; le retour
    arrière retire la clé, son historique et le motif tant que rien ne le cite ; rejouable."""
    installation.migrer()
    cfg = installation.configuration()
    motif = "SELECT count(*) FROM motif WHERE type_operation = 'ajustement' AND libelle = 'Rebut'"
    valeur = "SELECT valeur FROM parametre WHERE cle = 'seuil_rebut'"
    with moteur().connect() as c, c.begin():
        assert _cles_reglages(c) == (58, 58)
        assert c.execute(text(valeur)).scalar() == "0.1"
        assert c.execute(text(motif)).scalar() == 1
        c.execute(
            text(
                "INSERT INTO parametre_historique (cle, avant, apres)"
                " VALUES ('seuil_rebut', '0.1', '2')"
            )
        )
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0008")
        assert _cles_reglages(c) == (57, 57)
        assert c.execute(text(motif)).scalar() == 0
        refus = c.begin_nested()
        with pytest.raises(SQLAlchemyError):
            c.execute(text("INSERT INTO parametre (cle) VALUES ('seuil_rebut')"))
        refus.rollback()
        command.upgrade(cfg, "head")
        assert _cles_reglages(c) == (58, 58)
        assert c.execute(text(valeur)).scalar() == "0.1"
        assert c.execute(text(motif)).scalar() == 1
    assert not installation.schema_en_retard()


def _enum_permis(c: Connection, contrainte: str) -> str:
    """La définition d'un CHECK de valeurs."""
    definition = c.execute(
        text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
        {"n": contrainte},
    ).scalar()
    return str(definition)


def test_0004_versions_et_genres_aller_retour(base_vide: None) -> None:
    """`role_nomenclature.version`, `periode_close`, `avant_vidage` et `avant_mise_a_jour` :
    posés par 0004, rangés ou retirés au retour (rien n'empêche de redescendre)."""
    installation.migrer()
    cfg = installation.configuration()
    with moteur().connect() as c, c.begin():
        assert c.execute(text("SELECT min(version) FROM role_nomenclature")).scalar() == 1
        assert "'periode_close'" in _enum_permis(c, "ck_dossier_ligne_cours_origine_enum")
        genres = _enum_permis(c, "ck_sauvegarde_genre_enum")
        assert "'avant_vidage'" in genres and "'avant_mise_a_jour'" in genres
        c.execute(
            text(
                "INSERT INTO sauvegarde (fichier, genre, base) VALUES"
                " ('a.dump', 'avant_vidage', 'b'), ('m.dump', 'avant_mise_a_jour', 'b'),"
                " ('q.dump', 'quotidienne', 'b')"
            )
        )
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0003")
        colonnes = "SELECT column_name FROM information_schema.columns WHERE table_name = :t"
        assert "version" not in set(c.execute(text(colonnes), {"t": "role_nomenclature"}).scalars())
        assert "periode_close" not in _enum_permis(c, "ck_dossier_ligne_cours_origine_enum")
        assert list(c.execute(text("SELECT fichier FROM sauvegarde")).scalars()) == ["q.dump"]
        command.upgrade(cfg, "head")
        c.execute(text("DELETE FROM sauvegarde"))
    assert not installation.schema_en_retard()


def test_0005_motif_d_abandon_aller_retour(base_vide: None) -> None:
    """`inventaire.abandon_motif` (RESTES3, demande de D5) : le motif d'un inventaire abandonné
    quitte `annulation_motif` à la montée, y revient au retour."""
    installation.migrer()
    cfg = installation.configuration()
    colonnes = "SELECT column_name FROM information_schema.columns WHERE table_name = 'inventaire'"
    lire = "SELECT abandon_motif, annulation_motif FROM inventaire ORDER BY numero"
    with moteur().connect() as c, c.begin():
        assert "abandon_motif" in set(c.execute(text(colonnes)).scalars())
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0004")
        assert "abandon_motif" not in set(c.execute(text(colonnes)).scalars())
        c.execute(
            text(
                "INSERT INTO inventaire (numero, date, statut, abandonne_le, annulation_motif)"
                " VALUES ('INV-2026-0901', '2026-10-01', 'abandonne', now(), 'comptage reporté'),"
                " ('INV-2026-0902', '2026-10-01', 'ouvert', NULL, '')"
            )
        )
        command.upgrade(cfg, "head")
        assert [tuple(x) for x in c.execute(text(lire))] == [
            ("comptage reporté", ""),
            ("", ""),
        ]
        command.downgrade(cfg, "0004")
        relu = "SELECT annulation_motif FROM inventaire ORDER BY numero"
        assert list(c.execute(text(relu)).scalars()) == ["comptage reporté", ""]
        command.upgrade(cfg, "head")
        c.execute(text("DELETE FROM inventaire"))
    assert not installation.schema_en_retard()


def test_0006_taux_des_frais_aller_retour(base_vide: None) -> None:
    """`dossier_frais.taux` (lot TAUX-FRAIS) : la colonne et ses deux CHECK (bornes, NaN) ; le
    retour arrière les retire, la remontée les remet."""
    installation.migrer()
    cfg = installation.configuration()
    colonnes = (
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'dossier_frais'"
    )
    contraintes = "SELECT conname FROM pg_constraint WHERE conname LIKE 'ck_dossier_frais_taux%'"
    with moteur().connect() as c, c.begin():
        assert "taux" in set(c.execute(text(colonnes)).scalars())
        assert set(c.execute(text(contraintes)).scalars()) == {
            "ck_dossier_frais_taux_borne",
            "ck_dossier_frais_taux_nombre",
        }
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0005")
        assert "taux" not in set(c.execute(text(colonnes)).scalars())
        assert list(c.execute(text(contraintes)).scalars()) == []
        command.upgrade(cfg, "head")
        assert "taux" in set(c.execute(text(colonnes)).scalars())
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


def test_schema_conforme_au_document_modele_donnees(capsys: pytest.CaptureFixture[str]) -> None:
    outil = Path(__file__).resolve().parents[2] / "outils" / "schema_contre_modele.py"
    spec = importlib.util.spec_from_file_location("schema_contre_modele", outil)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    code = module.main(["--base", str(moteur().url.render_as_string(hide_password=False))])
    sortie = capsys.readouterr().out
    assert code == 0, sortie
    assert "73 tables en base, 73 au document" in sortie
    assert sortie.count("Écart déclaré") == len(module.ECARTS_DECLARES)
