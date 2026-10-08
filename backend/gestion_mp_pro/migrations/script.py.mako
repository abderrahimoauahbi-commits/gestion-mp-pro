"""${message}

Révision ${up_revision}${" (suit " + down_revision + ")" if down_revision else ""}, créée le ${create_date}.
N'importe que `alembic` et `sqlalchemy` : jamais le paquet `gestion_mp_pro` (MODELE-DONNEES § 9).
Jamais modifiée une fois livrée : un changement = une nouvelle révision.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Applique la révision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Défait la révision."""
    ${downgrades if downgrades else "pass"}
