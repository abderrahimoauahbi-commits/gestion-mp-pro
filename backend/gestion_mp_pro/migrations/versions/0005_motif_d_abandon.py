"""Le motif d'abandon d'un inventaire dans sa colonne.

Révision 0005 (suit 0004), demandée par le lot D5 (reste traité par RESTES3) :

- `inventaire.abandon_motif` (`VARCHAR(300)`, défaut ''), comme `annulation_motif` : le motif
  d'un inventaire **abandonné** y est rangé ; il l'était dans `annulation_motif` (états
  exclusifs), que la montée vide pour les inventaires abandonnés.

Comme 0001 à 0004, n'importe que `alembic` et `sqlalchemy`. Le retour arrière remet le motif
d'abandon dans `annulation_motif`, puis retire la colonne.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """La colonne, puis le motif des inventaires abandonnés déplacé."""
    op.add_column(
        "inventaire",
        sa.Column("abandon_motif", sa.String(length=300), server_default="", nullable=False),
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE inventaire SET abandon_motif = annulation_motif, annulation_motif = ''"
            " WHERE statut = 'abandonne'"
        )
    )


def downgrade() -> None:
    """Le motif d'abandon remis dans `annulation_motif`, puis la colonne retirée."""
    op.get_bind().execute(
        sa.text("UPDATE inventaire SET annulation_motif = abandon_motif WHERE statut = 'abandonne'")
    )
    op.drop_column("inventaire", "abandon_motif")
