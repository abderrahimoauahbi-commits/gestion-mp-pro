"""Révision 0008 (lot UNITES-TITRAGE) : la table `unite_titrage`, semée des six unités puis de
celles que les titrages emploient déjà ; le journal la nomme ; le retour arrière la retire, et
refuse si le journal la cite.

L'essai vide la base d'essai ; il la rend migrée à la tête, semences comprises (comme
`test_migrations.py`).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from gestion_mp_pro.db import moteur
from gestion_mp_pro.services import installation

SEMEES = [
    ("Dtex", 10),
    ("Deniers", 20),
    ("Nm", 30),
    ("Tex", 40),
    ("Nec", 50),
    ("lbs", 60),
]
UNITES = "SELECT code, ordre FROM unite_titrage ORDER BY ordre, code"
TABLES = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"


@pytest.fixture
def base_vide() -> Iterator[None]:
    """Une base vide pour l'essai ; migrée à la tête ensuite, quoi qu'il arrive."""
    with moteur().begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    yield
    installation.migrer()


def _titrages_0007(c: Connection) -> None:
    """Sous 0007 : des titrages qui écrivent des unités connues, nouvelles, abrégées, fausses."""
    c.execute(
        text(
            "INSERT INTO titrage (code, valeur, unite) VALUES"
            " ('20 tex', '20', 'tex'), ('20 Ne', '20', 'Ne'), ('25 Ne', '25', 'Ne'),"
            " ('30 NE', '30', 'NE'),"
            " ('1500 den', '1500', 'den'), ('8 g/m', '8', 'g/m'), ('12 GSM', '12', 'GSM'),"
            " ('5 x', '5', 'x'), ('7', '7', '')"
        )
    )


def test_0008_seme_les_unites_et_celles_deja_employees(base_vide: None) -> None:
    """Les six unités dans leur ordre ; à la remontée sur une base qui a des titrages, les
    unités employées et absentes (un mot de lettres, deux au moins, « den » excepté) suivent,
    une par écriture sans casse (la plus employée) ; le retour arrière est refusé si le journal
    cite une unité."""
    installation.migrer()
    cfg = installation.configuration()
    with moteur().connect() as c, c.begin():
        assert [tuple(x) for x in c.execute(text(UNITES))] == SEMEES
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0007")
        assert "unite_titrage" not in set(c.execute(text(TABLES)).scalars())
        _titrages_0007(c)
        command.upgrade(cfg, "head")
        assert [tuple(x) for x in c.execute(text(UNITES))] == [*SEMEES, ("GSM", 70), ("Ne", 80)]
        doublon = c.begin_nested()
        with pytest.raises(IntegrityError, match="uq_unite_titrage_code"):
            c.execute(text("INSERT INTO unite_titrage (code) VALUES ('LBS')"))
        doublon.rollback()
        cite = "INSERT INTO journal (action, objet, objet_id) VALUES ('essai', 'unite_titrage', 1)"
        c.execute(text(cite))
        refus = c.begin_nested()
        with pytest.raises(RuntimeError, match="1 geste"):
            command.downgrade(cfg, "0007")
        refus.rollback()
        c.execute(text("DELETE FROM journal WHERE objet = 'unite_titrage'"))
        command.downgrade(cfg, "0007")
        command.upgrade(cfg, "head")
        c.execute(text("DELETE FROM titrage"))
        c.execute(text("DELETE FROM unite_titrage WHERE ordre > 60"))
    assert not installation.schema_en_retard()
