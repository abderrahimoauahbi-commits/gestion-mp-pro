"""Les unités de titrage deviennent un référentiel.

Révision 0008 (suit 0007), lot UNITES-TITRAGE (décision de Mohamed du 12 octobre 2026 : ajouter
lui-même une unité, sans intervention) :

- Table `unite_titrage` (`id`, `code` VARCHAR(16) tel qu'écrit dans les références, `libelle`,
  `ordre`, `actif`, `version`) ; CHECK `ck_unite_titrage_code_un_mot` (un mot, non vide) et
  `ck_unite_titrage_ordre_positif` ; index unique `uq_unite_titrage_code` sur `lower(code)`
  (« LBS » et « lbs » ne coexistent pas).
- Semée de Dtex, Deniers, Nm, Tex, Nec, lbs, dans cet ordre (10, 20… 60), puis des unités déjà
  écrites sur des titrages et absentes de la liste (un mot de lettres, deux au moins ; « den »
  est la façon courte d'écrire Deniers, pas une unité), à la suite, chacune dans son écriture
  la plus employée : la liste dit d'emblée tout ce que la base emploie. `ON CONFLICT DO
  NOTHING` : rejouable, n'écrase rien.
- `ObjetJournal` gagne `unite_titrage` : CHECK `ck_journal_objet_enum` remplacé.

Comme 0001 à 0007, n'importe que `alembic` et `sqlalchemy`. Le retour arrière retire la table et
remet le CHECK ; il est **refusé** si le journal cite déjà une unité de titrage (le journal ne
se réécrit jamais) : restaurer alors une sauvegarde d'avant la révision.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TABLE = "unite_titrage"
UNITES = (
    ("Dtex", "décitex (grammes pour 10 000 m)"),
    ("Deniers", "deniers (grammes pour 9 000 m)"),
    ("Nm", "numéro métrique (mètres par gramme)"),
    ("Tex", "tex (grammes pour 1 000 m)"),
    ("Nec", "numéro anglais coton"),
    ("lbs", "livres (titrage du jute)"),
)
OBJETS_AVANT = (
    "utilisateur", "appareil", "parametre", "devise", "sauvegarde", "composition", "type_fil",
    "titrage", "couleur", "role_nomenclature", "fournisseur", "matiere", "code_douanier",
    "poste_frais", "qualite", "magasin", "metier", "lot", "commande", "reception", "facture",
    "ordre", "operation", "inventaire", "dossier", "dossier_frais", "reclamation", "signalement",
    "piece_jointe", "periode", "reprise", "systeme",
)  # fmt: skip
OBJETS_APRES = (*OBJETS_AVANT[:8], "unite_titrage", *OBJETS_AVANT[8:])


def _objets_permis(valeurs: tuple[str, ...]) -> None:
    """Remplace le CHECK `ck_journal_objet_enum`."""
    nom = op.f("ck_journal_objet_enum")
    op.drop_constraint(nom, "journal", type_="check")
    op.create_check_constraint(
        nom, "journal", "objet IN (" + ", ".join(f"'{v}'" for v in valeurs) + ")"
    )


def _creer_la_table() -> None:
    """La table, ses CHECK et son index unique sans casse."""
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("libelle", sa.String(length=120), server_default="", nullable=False),
        sa.Column("ordre", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "code <> '' AND code !~ '[[:space:]]'", name=op.f("ck_unite_titrage_code_un_mot")
        ),
        sa.CheckConstraint("ordre >= 0", name=op.f("ck_unite_titrage_ordre_positif")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_unite_titrage")),
    )
    op.create_index("uq_unite_titrage_code", TABLE, [sa.text("lower(code)")], unique=True)


def _semer() -> None:
    """Les six unités, puis celles que les titrages emploient déjà."""
    lien = op.get_bind()
    for rang, (code, libelle) in enumerate(UNITES, start=1):
        lien.execute(
            sa.text(
                "INSERT INTO unite_titrage (code, libelle, ordre) VALUES (:code, :libelle, :ordre)"
                " ON CONFLICT DO NOTHING"
            ),
            {"code": code, "libelle": libelle, "ordre": rang * 10},
        )
    employees = lien.execute(
        sa.text(
            "SELECT DISTINCT ON (lower(unite)) unite FROM titrage"
            " WHERE unite ~ '^[[:alpha:]]{2,16}$' AND lower(unite) <> 'den'"
            " AND lower(unite) NOT IN (SELECT lower(code) FROM unite_titrage)"
            ' GROUP BY unite ORDER BY lower(unite), count(*) DESC, unite COLLATE "C"'
        )
    ).scalars()
    for rang, code in enumerate(employees, start=len(UNITES) + 1):
        lien.execute(
            sa.text(
                "INSERT INTO unite_titrage (code, ordre) VALUES (:code, :ordre)"
                " ON CONFLICT DO NOTHING"
            ),
            {"code": code, "ordre": rang * 10},
        )


def upgrade() -> None:
    """La table semée, puis le journal qui la nomme."""
    _creer_la_table()
    _semer()
    _objets_permis(OBJETS_APRES)


def downgrade() -> None:
    """La table retirée, le CHECK remis ; refusé si le journal cite une unité de titrage."""
    lignes = op.get_bind().execute(
        sa.text("SELECT count(*) FROM journal WHERE objet = 'unite_titrage'")
    )
    nombre = lignes.scalar() or 0
    if nombre:
        raise RuntimeError(
            f"Retour arrière refusé : le journal cite {nombre} geste(s) sur des unités de "
            "titrage, et il ne se réécrit jamais. Restaurer une sauvegarde d'avant la révision "
            "0008."
        )
    _objets_permis(OBJETS_AVANT)
    op.drop_index("uq_unite_titrage_code", table_name=TABLE)
    op.drop_table(TABLE)
