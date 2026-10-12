"""Un dossier d'importation, plusieurs factures.

Révision 0007 (suit 0006), lot PLUSIEURS-FACTURES (décision de Mohamed du 12 octobre 2026, qui
amende I3 « un dossier = une facture = une livraison ») : un dossier — une déclaration en douane,
un arrivage — peut regrouper plusieurs factures ; une facture n'appartient qu'à un seul dossier.

- Table `dossier_facture` (PK `(dossier_id, facture_id)`, `dossier_id` FK ON DELETE CASCADE,
  `facture_id` FK RESTRICT, `ajoutee_le`, `ajoutee_par_id`, `liberee_le`) : les factures du
  dossier. `liberee_le` est posé quand l'annulation du dossier rend la facture libre (la trace
  reste sur le dossier annulé).
- Index unique partiel `uq_dossier_facture` `(facture_id) WHERE liberee_le IS NULL` : une
  facture dans un seul dossier vivant (il remplace l'index du même nom de `dossier`, qui portait
  sur `dossier.facture_id WHERE statut <> 'annule'`).
- `dossier.facture_id` disparaît : une seule source de vérité. Chaque dossier qui avait une
  facture la garde (ajoutée à sa création, par son créateur ; libérée à son annulation s'il est
  annulé).

Comme 0001 à 0006, n'importe que `alembic` et `sqlalchemy`. Le retour arrière remet
`dossier.facture_id` (la facture d'ouverture : la première ajoutée) et son index ; il est
**refusé** si un dossier non annulé a plusieurs factures (elles seraient perdues en silence) :
retirer d'abord les factures ajoutées, ou restaurer une sauvegarde.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TABLE = "dossier_facture"
INDEX = "uq_dossier_facture"


def upgrade() -> None:
    """La table et ses liens repris de `dossier.facture_id`, puis la colonne retirée."""
    op.create_table(
        TABLE,
        sa.Column("dossier_id", sa.Integer(), nullable=False),
        sa.Column("facture_id", sa.Integer(), nullable=False),
        sa.Column(
            "ajoutee_le",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ajoutee_par_id", sa.Integer(), nullable=True),
        sa.Column("liberee_le", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["ajoutee_par_id"],
            ["utilisateur.id"],
            name=op.f("fk_dossier_facture_ajoutee_par_id_utilisateur"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossier.id"],
            name=op.f("fk_dossier_facture_dossier_id_dossier"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["facture_id"],
            ["facture.id"],
            name=op.f("fk_dossier_facture_facture_id_facture"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("dossier_id", "facture_id", name=op.f("pk_dossier_facture")),
    )
    op.execute(
        "INSERT INTO dossier_facture (dossier_id, facture_id, ajoutee_le, ajoutee_par_id,"
        " liberee_le) SELECT id, facture_id, cree_le, cree_par_id,"
        " CASE WHEN statut = 'annule' THEN coalesce(annule_le, now()) END"
        " FROM dossier WHERE facture_id IS NOT NULL"
    )
    op.drop_index(INDEX, table_name="dossier", postgresql_where=sa.text("statut <> 'annule'"))
    op.create_index(
        INDEX,
        TABLE,
        ["facture_id"],
        unique=True,
        postgresql_where=sa.text("liberee_le IS NULL"),
    )
    op.drop_constraint(op.f("fk_dossier_facture_id_facture"), "dossier", type_="foreignkey")
    op.drop_column("dossier", "facture_id")


def _plusieurs_factures() -> list[str]:
    """Les dossiers non annulés qui ont plus d'une facture (perdues au retour arrière)."""
    requete = sa.text(
        "SELECT d.numero FROM dossier d JOIN dossier_facture x ON x.dossier_id = d.id"
        " WHERE x.liberee_le IS NULL GROUP BY d.numero HAVING count(*) > 1 ORDER BY d.numero"
    )
    return list(op.get_bind().execute(requete).scalars())


def downgrade() -> None:
    """`dossier.facture_id` remis (la première facture ajoutée), la table retirée."""
    perdus = _plusieurs_factures()
    if perdus:
        raise RuntimeError(
            "Retour arrière refusé : les dossiers " + ", ".join(perdus) + " ont plusieurs "
            "factures (une seule tient dans dossier.facture_id). Retirer d'abord les factures "
            "ajoutées, ou restaurer une sauvegarde."
        )
    op.add_column("dossier", sa.Column("facture_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_dossier_facture_id_facture"),
        "dossier",
        "facture",
        ["facture_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        "UPDATE dossier d SET facture_id = (SELECT x.facture_id FROM dossier_facture x"
        " WHERE x.dossier_id = d.id ORDER BY x.ajoutee_le, x.facture_id LIMIT 1)"
    )
    op.drop_index(INDEX, table_name=TABLE, postgresql_where=sa.text("liberee_le IS NULL"))
    op.drop_table(TABLE)
    op.create_index(
        INDEX,
        "dossier",
        ["facture_id"],
        unique=True,
        postgresql_where=sa.text("statut <> 'annule'"),
    )
