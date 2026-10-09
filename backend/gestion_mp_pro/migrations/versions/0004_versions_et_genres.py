"""Version des rôles de nomenclature, cours figé par la période close, genres de sauvegarde.

Révision 0004 (suit 0003), demandée par les lots D1 et D10 :

- `role_nomenclature.version` (`INTEGER`, défaut 1) : la route 59 contrôle la version reçue
  (409 `conflit_version`) comme pour toute fiche modifiable ;
- `OrigineCours` gagne `periode_close` : le cours du jour posé sur une marchandise de dossier
  ouvert entrée dans une période qu'on clôt (E-02) n'est plus rangé en `saisi` ; CHECK
  `ck_dossier_ligne_cours_origine_enum` remplacé ;
- `GenreSauvegarde` gagne `avant_vidage` et `avant_mise_a_jour` (décision X2) : le registre les
  inscrit (jamais purgées) ; CHECK `ck_sauvegarde_genre_enum` remplacé.

Comme 0001 à 0003, n'importe que `alembic` et `sqlalchemy` : les listes sont écrites en clair,
dans l'ordre de `modeles.enums`. Le retour arrière range les cours `periode_close` en `saisi`,
retire du registre les sauvegardes des deux nouveaux genres (leurs fichiers restent sur le
disque, qui fait foi), remet les deux CHECK et retire la colonne.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

ORIGINES_AVANT = ("bon", "banque", "clos_au_jour", "saisi", "reprise")
ORIGINES_APRES = ("bon", "banque", "clos_au_jour", "periode_close", "saisi", "reprise")
GENRES_AVANT = ("quotidienne", "manuelle", "avant_restauration", "avant_reprise", "reference_vide")
GENRES_APRES = (
    "quotidienne",
    "manuelle",
    "avant_restauration",
    "avant_reprise",
    "avant_vidage",
    "avant_mise_a_jour",
    "reference_vide",
)


def _valeurs_permises(table: str, colonne: str, valeurs: tuple[str, ...]) -> None:
    """Remplace le CHECK `ck_<table>_<colonne>_enum` d'une colonne énumérée."""
    nom = op.f(f"ck_{table}_{colonne}_enum")
    op.drop_constraint(nom, table, type_="check")
    op.create_check_constraint(
        nom, table, f"{colonne} IN (" + ", ".join(f"'{v}'" for v in valeurs) + ")"
    )


def upgrade() -> None:
    """La colonne `version`, puis les deux listes de valeurs élargies."""
    op.add_column(
        "role_nomenclature",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    _valeurs_permises("dossier_ligne", "cours_origine", ORIGINES_APRES)
    _valeurs_permises("sauvegarde", "genre", GENRES_APRES)


def downgrade() -> None:
    """Les valeurs nouvelles rangées (ou retirées du registre), puis les CHECK et la colonne."""
    lien = op.get_bind()
    lien.execute(
        sa.text(
            "UPDATE dossier_ligne SET cours_origine = 'saisi' WHERE cours_origine = 'periode_close'"
        )
    )
    lien.execute(
        sa.text("DELETE FROM sauvegarde WHERE genre IN ('avant_vidage', 'avant_mise_a_jour')")
    )
    _valeurs_permises("sauvegarde", "genre", GENRES_AVANT)
    _valeurs_permises("dossier_ligne", "cours_origine", ORIGINES_AVANT)
    op.drop_column("role_nomenclature", "version")
