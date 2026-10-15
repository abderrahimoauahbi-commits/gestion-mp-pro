"""Genres de sauvegarde `hebdomadaire` et `mensuelle` (lot SAUVEGARDES-CALENDRIER).

Révision 0010 (suit 0009). Décision X7 de Mohamed, 15 octobre 2026 : « il faut indiquer la nature
de la sauvegarde : manuelle, quotidienne, hebdomadaire et mensuelle » — la quotidienne chaque soir
à 22:00, l'hebdomadaire le dimanche à 22:00, la mensuelle le dernier jour du mois à 22:00, chacune
son fichier, inscrite au registre comme les autres.

- `GenreSauvegarde` gagne `hebdomadaire` et `mensuelle` (après `quotidienne`, ordre de
  `modeles.enums`) : CHECK `ck_sauvegarde_genre_enum` remplacé (`DROP` puis `ADD`).

Comme 0001 à 0009, n'importe que `alembic` et `sqlalchemy` : les listes sont écrites en clair. Le
retour arrière retire du registre les sauvegardes des deux genres (leurs fichiers restent sur le
disque, qui fait foi) et remet le CHECK de 0004.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

AVANT = (
    "quotidienne",
    "manuelle",
    "avant_restauration",
    "avant_reprise",
    "avant_vidage",
    "avant_mise_a_jour",
    "reference_vide",
)
"""Les genres de 0004."""

NOUVEAUX = ("hebdomadaire", "mensuelle")
APRES = (AVANT[0], *NOUVEAUX, *AVANT[1:])
"""Les neuf genres : les deux nouveaux après `quotidienne`."""


def _genres_permis(valeurs: tuple[str, ...]) -> None:
    """Remplace le CHECK `ck_sauvegarde_genre_enum`."""
    nom = op.f("ck_sauvegarde_genre_enum")
    op.drop_constraint(nom, "sauvegarde", type_="check")
    op.create_check_constraint(
        nom, "sauvegarde", "genre IN (" + ", ".join(f"'{v}'" for v in valeurs) + ")"
    )


def upgrade() -> None:
    """La liste des genres élargie."""
    _genres_permis(APRES)


def downgrade() -> None:
    """Les deux genres retirés du registre, puis le CHECK de 0004."""
    op.get_bind().execute(
        sa.text("DELETE FROM sauvegarde WHERE genre IN ('hebdomadaire', 'mensuelle')")
    )
    _genres_permis(AVANT)
