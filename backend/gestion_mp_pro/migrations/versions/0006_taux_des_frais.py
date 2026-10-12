"""Le taux d'un frais de dossier, gardé pour mémoire.

Révision 0006 (suit 0005), lot TAUX-FRAIS (demande de Mohamed, 12 octobre 2026) :

- `dossier_frais.taux` (`NUMERIC(7,4)`, vide permis) : le pourcentage que l'écran a appliqué à
  la base du frais pour en proposer le montant (20 % de TVA, 2,5 % de droits…). Le montant reste
  celui saisi : la douane arrondit, et rien ne le recalcule depuis le taux.
- CHECK `ck_dossier_frais_taux_borne` : vide, ou plus de 0 et au plus 100 ;
  CHECK `ck_dossier_frais_taux_nombre` : aucun `NaN` (règle générique des colonnes `NUMERIC`).

Les frais existants n'ont pas de taux (vide). Comme 0001 à 0005, n'importe que `alembic` et
`sqlalchemy`. Le retour arrière retire les deux CHECK puis la colonne (les taux sont perdus,
les montants restent).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TABLE = "dossier_frais"


def upgrade() -> None:
    """La colonne, puis ses deux CHECK."""
    op.add_column(TABLE, sa.Column("taux", sa.Numeric(precision=7, scale=4), nullable=True))
    op.create_check_constraint(
        op.f("ck_dossier_frais_taux_borne"), TABLE, "taux IS NULL OR (taux > 0 AND taux <= 100)"
    )
    op.create_check_constraint(op.f("ck_dossier_frais_taux_nombre"), TABLE, "taux <> 'NaN'")


def downgrade() -> None:
    """Les CHECK retirés, puis la colonne."""
    op.drop_constraint(op.f("ck_dossier_frais_taux_nombre"), TABLE, type_="check")
    op.drop_constraint(op.f("ck_dossier_frais_taux_borne"), TABLE, type_="check")
    op.drop_column(TABLE, "taux")
