"""Réglage `toler_tva_import` : tolérance de l'écart de TVA d'un dossier d'importation.

Révision 0003 (suit 0002). Gestion MP corrigé (26459d4, E-10) a rendu réglable la tolérance du
contrôle C29, la même sur la fiche du dossier (`tva_ecart_tolere_mad`) : « TVA d'importation à
vérifier au-delà de », défaut 0,05 (5 %), bornes 0–1, en %.

- la clé entre dans la liste fermée : CHECK `ck_parametre_cle_connue` remplacé (`DROP` puis
  `ADD`), 57 clés, dans l'ordre de `modeles.CLES_REGLAGES` ;
- semence `0.05`, `INSERT … ON CONFLICT DO NOTHING` (rejouable, n'écrase rien).

Comme 0001 et 0002, n'importe que `alembic` et `sqlalchemy` : les listes sont écrites en clair.
Le retour arrière retire la clé, sa valeur et son historique, puis remet le CHECK à 56 clés.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

CLE = "toler_tva_import"
DEFAUT = "0.05"

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
    "delai_frais_import_jours", "dso", "nom_entreprise", "forme_juridique", "secteur",
    "adresse", "ville", "telephone", "banques", "ice", "rc", "identifiant_fiscal", "cnss",
    "patente", "date_cloture", "courriel_destinataires", "adresse_publique",
)  # fmt: skip
"""Les 56 clés de 0001, dans leur ordre."""

_RANG = AVANT.index("toler_facture_import") + 1
APRES = (*AVANT[:_RANG], CLE, *AVANT[_RANG:])
"""Les 57 clés : `toler_tva_import` après `toler_facture_import`, comme dans Gestion MP."""

CONTRAINTE = "ck_parametre_cle_connue"


def _cle_connue(cles: tuple[str, ...]) -> None:
    """Remplace le CHECK de la liste fermée des clés."""
    op.drop_constraint(op.f(CONTRAINTE), "parametre", type_="check")
    op.create_check_constraint(
        op.f(CONTRAINTE), "parametre", "cle IN (" + ", ".join(f"'{c}'" for c in cles) + ")"
    )


def upgrade() -> None:
    """Ajoute la clé à la liste fermée, puis sème son défaut."""
    _cle_connue(APRES)
    op.get_bind().execute(
        sa.text(
            "INSERT INTO parametre (cle, valeur) VALUES (:cle, :valeur)"
            " ON CONFLICT (cle) DO NOTHING"
        ),
        {"cle": CLE, "valeur": DEFAUT},
    )


def downgrade() -> None:
    """Retire l'historique et la valeur de la clé, puis la sort de la liste fermée."""
    for table in ("parametre_historique", "parametre"):
        op.get_bind().execute(sa.text(f"DELETE FROM {table} WHERE cle = :cle"), {"cle": CLE})  # noqa: S608
    _cle_connue(AVANT)
