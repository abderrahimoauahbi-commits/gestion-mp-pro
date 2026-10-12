"""Révision 0007 (lot PLUSIEURS-FACTURES) : `dossier_facture` remplace `dossier.facture_id` ;
un dossier existant garde sa facture, le retour arrière la remet et refuse d'en perdre une.

L'essai vide la base d'essai ; il la rend migrée à la tête, semences comprises (comme
`test_migrations.py`).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Connection, text

from gestion_mp_pro.db import moteur
from gestion_mp_pro.services import installation


@pytest.fixture
def base_vide() -> Iterator[None]:
    """Une base vide pour l'essai ; migrée à la tête ensuite, quoi qu'il arrive."""
    with moteur().begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
    yield
    installation.migrer()


def _dossiers_0006(c: Connection) -> None:
    """Sous 0006 : deux factures ; un dossier vivant de F1, un annulé de F1, un sans facture."""
    c.execute(text("INSERT INTO fournisseur (id, nom) VALUES (9001, 'Essai 0007')"))
    c.execute(
        text(
            "INSERT INTO facture (id, fournisseur_id, numero, devise) VALUES"
            " (9001, 9001, 'F1-0007', 'USD'), (9002, 9001, 'F2-0007', 'USD')"
        )
    )
    c.execute(
        text(
            "INSERT INTO dossier (id, numero, annee, rang, facture_id, statut, annule_le,"
            " cree_le) VALUES (9001, '01/20', 2020, 1, 9001, 'ouvert', NULL, '2020-01-02'),"
            " (9002, '02/20', 2020, 2, 9001, 'annule', '2020-01-05', '2020-01-01'),"
            " (9003, '03/20', 2020, 3, NULL, 'ouvert', NULL, '2020-01-03')"
        )
    )


LIENS_0007 = (
    "SELECT dossier_id, facture_id, ajoutee_le::date::text, liberee_le::date::text"
    " FROM dossier_facture ORDER BY dossier_id"
)


def test_0007_un_dossier_garde_sa_facture(base_vide: None) -> None:
    """`dossier_facture` (lot PLUSIEURS-FACTURES) : chaque dossier qui avait une facture la garde
    (ajoutée à sa création ; libérée s'il est annulé), `dossier.facture_id` disparaît ; le retour
    arrière la remet, et refuse de perdre une seconde facture d'un dossier vivant."""
    installation.migrer()
    cfg = installation.configuration()
    colonnes = "SELECT column_name FROM information_schema.columns WHERE table_name = 'dossier'"
    with moteur().connect() as c, c.begin():
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0006")
        _dossiers_0006(c)
        command.upgrade(cfg, "head")
        assert "facture_id" not in set(c.execute(text(colonnes)).scalars())
        assert [tuple(x) for x in c.execute(text(LIENS_0007))] == [
            (9001, 9001, "2020-01-02", None),
            (9002, 9001, "2020-01-01", "2020-01-05"),
        ]
        c.execute(text("INSERT INTO dossier_facture (dossier_id, facture_id) VALUES (9001, 9002)"))
        refus = c.begin_nested()
        with pytest.raises(RuntimeError, match="01/20"):
            command.downgrade(cfg, "0006")
        refus.rollback()
        c.execute(text("DELETE FROM dossier_facture WHERE facture_id = 9002"))
        command.downgrade(cfg, "0006")
        relu = "SELECT id, facture_id FROM dossier ORDER BY id"
        assert [tuple(x) for x in c.execute(text(relu))] == [
            (9001, 9001),
            (9002, 9001),
            (9003, None),
        ]
        command.upgrade(cfg, "head")
        c.execute(text("DELETE FROM dossier_facture"))
        c.execute(text("DELETE FROM dossier"))
        c.execute(text("DELETE FROM facture"))
        c.execute(text("DELETE FROM fournisseur WHERE id = 9001"))
    assert not installation.schema_en_retard()
