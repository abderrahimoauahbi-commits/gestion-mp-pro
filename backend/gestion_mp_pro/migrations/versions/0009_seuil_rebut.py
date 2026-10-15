"""Réglage `seuil_rebut` et motif d'ajustement « Rebut » : les fonds de lot (lot FOND-DE-LOT).

Révision 0009 (suit 0008). Décision de Mohamed du 15 octobre 2026 : « à partir d'un certain
poids, un fond de lot doit être mis au rebut : il ne sert à rien » ; en dessous d'environ 100 g,
un fond de lot est du rebut. Le seuil se règle (Réglages › Stock et inventaire, direction),
défaut **0,100 kg**, 0 = désactivé.

- la clé `seuil_rebut` entre dans la liste fermée : CHECK `ck_parametre_cle_connue` remplacé
  (`DROP` puis `ADD`), 58 clés, dans l'ordre de `modeles.CLES_REGLAGES` (après
  `tolerance_inventaire`, famille « Stock et inventaire ») ; semence `0.1`, `INSERT … ON
  CONFLICT DO NOTHING` (rejouable, n'écrase rien) ;
- le motif d'ajustement « Rebut » (sans code R, après « Correction de saisie ») : le geste
  « Mettre au rebut » écrit un ajustement en moins à ce motif.

Comme 0001 à 0008, n'importe que `alembic` et `sqlalchemy` : les listes sont écrites en clair.
Le retour arrière retire la clé, sa valeur et son historique, remet le CHECK à 57 clés, et
retire le motif s'il n'est cité par aucun mouvement ni aucune opération (sinon il reste : le
journal du stock ne se réécrit jamais).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

CLE = "seuil_rebut"
DEFAUT = "0.1"
MOTIF = ("ajustement", "Rebut")

AVANT = (
    "seuil_critique", "seuil_alerte", "seuil_dormant", "delai_defaut", "marge_jours",
    "marge_securite", "taux_perte", "securite_a", "securite_b", "securite_c",
    "fenetre_realisation_jours", "plafond_stock_min_mois", "croissance_annuelle",
    "seuil_abc_a", "seuil_abc_b", "seuil_xyz_x", "seuil_xyz_y", "seuil_bc_urgent",
    "seuil_bc_groupe", "seuil_tier1", "seuil_tier2", "seuil_tier3", "seuil_approbation",
    "toler_in_full", "toler_ecart_pesee", "toler_excedent", "toler_poids_bobine",
    "tolerance_inventaire", "toler_retard_jours", "cible_otif", "score_strategique",
    "score_standard", "score_surveiller", "seuil_hausse_forte", "fenetre_prix_jours",
    "taux_tva_import", "taux_tpi_import", "seuil_surcout_import", "toler_facture_import",
    "toler_tva_import", "delai_frais_import_jours", "dso", "nom_entreprise", "forme_juridique",
    "secteur", "adresse", "ville", "telephone", "banques", "ice", "rc", "identifiant_fiscal",
    "cnss", "patente", "date_cloture", "courriel_destinataires", "adresse_publique",
)  # fmt: skip
"""Les 57 clés de 0003, dans leur ordre."""

_RANG = AVANT.index("tolerance_inventaire") + 1
APRES = (*AVANT[:_RANG], CLE, *AVANT[_RANG:])
"""Les 58 clés : `seuil_rebut` après `tolerance_inventaire` (famille « Stock et inventaire »)."""

CONTRAINTE = "ck_parametre_cle_connue"


def _cle_connue(cles: tuple[str, ...]) -> None:
    """Remplace le CHECK de la liste fermée des clés."""
    op.drop_constraint(op.f(CONTRAINTE), "parametre", type_="check")
    op.create_check_constraint(
        op.f(CONTRAINTE), "parametre", "cle IN (" + ", ".join(f"'{c}'" for c in cles) + ")"
    )


def upgrade() -> None:
    """Ajoute la clé à la liste fermée, sème son défaut, puis le motif « Rebut »."""
    _cle_connue(APRES)
    lien = op.get_bind()
    lien.execute(
        sa.text(
            "INSERT INTO parametre (cle, valeur) VALUES (:cle, :valeur)"
            " ON CONFLICT (cle) DO NOTHING"
        ),
        {"cle": CLE, "valeur": DEFAUT},
    )
    lien.execute(
        sa.text(
            "INSERT INTO motif (type_operation, libelle, code_r, ordre, impose_role)"
            " SELECT CAST(:type AS VARCHAR), :libelle, NULL,"
            " COALESCE((SELECT max(ordre) + 1 FROM motif WHERE type_operation = :type), 0), NULL"
            " ON CONFLICT (type_operation, libelle) DO NOTHING"
        ),
        {"type": MOTIF[0], "libelle": MOTIF[1]},
    )


def downgrade() -> None:
    """Retire l'historique et la valeur de la clé, la sort de la liste fermée, puis retire le
    motif « Rebut » s'il n'est cité nulle part."""
    lien = op.get_bind()
    for table in ("parametre_historique", "parametre"):
        lien.execute(sa.text(f"DELETE FROM {table} WHERE cle = :cle"), {"cle": CLE})  # noqa: S608
    _cle_connue(AVANT)
    lien.execute(
        sa.text(
            "DELETE FROM motif m WHERE m.type_operation = :type AND m.libelle = :libelle"
            " AND NOT EXISTS (SELECT 1 FROM mouvement WHERE motif_id = m.id)"
            " AND NOT EXISTS (SELECT 1 FROM operation WHERE motif_id = m.id)"
        ),
        {"type": MOTIF[0], "libelle": MOTIF[1]},
    )
