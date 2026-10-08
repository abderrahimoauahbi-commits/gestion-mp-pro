"""Semences : ce que toute base de Gestion MP PRO contient dès l'installation.

Révision 0002 (suit 0001). Données écrites en dur ici (jamais lues dans le paquet) ;
`INSERT … ON CONFLICT DO NOTHING` : rejouable, n'écrase rien de ce qui existe déjà.

- 8 rôles de nomenclature de base (Cuir, Franges, Ruban comptés au mètre) ;
- 11 postes de frais d'importation (5 postes « système » : DD, TPI, TVA, FRET, ASSUR) ;
- 3 devises : MAD 1, USD 10, EUR 10,8 (MAD pour 1) ;
- 2 magasins : « Magasin principal » (courant) et « Quarantaine », chacun seulement si aucun
  magasin de son type n'existe ;
- 16 motifs de mouvement (codes R1–R6 de l'ERP Fil) ;
- 56 réglages à leur défaut : les 55 de Gestion MP corrigé et `seuil_bc_urgent`, gardé pour
  mémoire (DONNEES § 7.1.5, ECRANS-PRO E6 ; décision S1).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ROLES = (
    ("Poil", False), ("Chaîne", False), ("Trame", False), ("Colle", False),
    ("Cuir", True), ("Franges", True), ("Ruban", True), ("Plastique", False),
)  # fmt: skip
"""(code, linéaire), dans l'ordre de la nomenclature."""

POSTES = (
    ("DD", "Droits de douane", False, "droits", False, True),
    ("TPI", "Taxe parafiscale à l'importation", False, "tpi", False, True),
    ("TVA", "TVA à l'importation", True, "tva", False, True),
    ("PORT", "Port Med", False, "autre", False, False),
    ("FRET", "Fret", False, "fret", True, True),
    ("ASSUR", "Assurance", False, "assurance", True, True),
    ("TRANSIT", "Transitaire", False, "autre", False, False),
    ("TIMBRE", "Timbre", False, "autre", False, False),
    ("INT_OC", "Intérêts / ordre de change", False, "autre", False, False),
    ("TMSA", "TMSA", False, "autre", False, False),
    ("AUTRE", "Autre frais", False, "autre", False, False),
)
"""(code, libellé, récupérable, nature, entre dans la valeur en douane, système), dans l'ordre."""

DEVISES = (("MAD", "Dirham", "1"), ("USD", "Dollar américain", "10"), ("EUR", "Euro", "10.8"))

MAGASINS = (("Magasin principal", "stock_courant"), ("Quarantaine", "quarantaine"))

MOTIFS = (
    ("retour_machine", "Reliquat de fin d'ordre", "R1", None),
    ("retour_machine", "Changement de série / arrêt machine", "R2", None),
    ("retour_machine", "Erreur de prélèvement", "R4", None),
    ("retour_fournisseur", "Non-conformité qualité", "R3", None),
    ("retour_fournisseur", "Excédent de réception", "R5", None),
    ("retour_fournisseur", "Bobines endommagées", "R6", None),
    ("retour_fournisseur", "Refus après quarantaine", "R3", None),
    ("ajustement", "Écart constaté au comptage", None, None),
    ("ajustement", "Matière retrouvée", None, None),
    ("ajustement", "Perte / casse", None, None),
    ("ajustement", "Correction de saisie", None, None),
    ("transfert", "Rangement", None, None),
    ("transfert", "Libération de quarantaine", None, "achats"),
    ("transfert", "Mise en quarantaine", None, None),
    ("transfert", "Approvisionnement de l'atelier", None, None),
    ("inventaire", "Écart d'inventaire", None, None),
)
"""(type, libellé, code R, rôle exigé en plus de la direction), dans l'ordre de chaque type."""

REGLAGES = (
    ("seuil_critique", "60"), ("seuil_alerte", "90"), ("seuil_dormant", "180"),
    ("delai_defaut", "60"), ("marge_jours", "30"), ("marge_securite", "0.2"),
    ("taux_perte", "0.02"), ("securite_a", "30"), ("securite_b", "30"), ("securite_c", "30"),
    ("fenetre_realisation_jours", "90"), ("plafond_stock_min_mois", "3"),
    ("croissance_annuelle", "0"), ("seuil_abc_a", "0.8"), ("seuil_abc_b", "0.95"),
    ("seuil_xyz_x", "0.25"), ("seuil_xyz_y", "0.5"), ("seuil_bc_urgent", "300000"),
    ("seuil_bc_groupe", "100000"), ("seuil_tier1", "300000"), ("seuil_tier2", "200000"),
    ("seuil_tier3", "100000"), ("seuil_approbation", "0"), ("toler_in_full", "0.02"),
    ("toler_ecart_pesee", "0.02"), ("toler_excedent", "0.1"), ("toler_poids_bobine", "0.05"),
    ("tolerance_inventaire", "0.02"), ("toler_retard_jours", "0"), ("cible_otif", "0.95"),
    ("score_strategique", "85"), ("score_standard", "65"), ("score_surveiller", "45"),
    ("seuil_hausse_forte", "0.05"), ("fenetre_prix_jours", "90"), ("taux_tva_import", "0.2"),
    ("taux_tpi_import", "0.0025"), ("seuil_surcout_import", "1"),
    ("toler_facture_import", "0.02"), ("delai_frais_import_jours", "30"), ("dso", "60"),
    ("nom_entreprise", ""), ("forme_juridique", ""),
    ("secteur", "Fabrication de tapis mécaniques"), ("adresse", ""), ("ville", ""),
    ("telephone", ""), ("banques", ""), ("ice", ""), ("rc", ""), ("identifiant_fiscal", ""),
    ("cnss", ""), ("patente", ""), ("date_cloture", ""), ("courriel_destinataires", ""),
    ("adresse_publique", ""),
)  # fmt: skip
"""(clé, valeur par défaut en texte normalisé : entier sans « .0 », décimal le plus court)."""


def _executer(sql: str, lignes: list[dict[str, object]]) -> None:
    """Une requête paramétrée, une fois par ligne."""
    for ligne in lignes:
        op.get_bind().execute(sa.text(sql), ligne)


def upgrade() -> None:
    """Sème ce qui manque, sans rien écraser."""
    _executer(
        "INSERT INTO role_nomenclature (code, lineaire, de_base, ordre)"
        " VALUES (:code, :lineaire, true, :ordre) ON CONFLICT (code) DO NOTHING",
        [{"code": c, "lineaire": li, "ordre": i} for i, (c, li) in enumerate(ROLES)],
    )
    _executer(
        "INSERT INTO poste_frais (code, libelle, recuperable, nature, entre_valeur_douane,"
        " systeme, ordre) VALUES (:code, :libelle, :recuperable, :nature, :douane, :systeme,"
        " :ordre) ON CONFLICT (code) DO NOTHING",
        [
            {"code": c, "libelle": lb, "recuperable": r, "nature": n, "douane": d,
             "systeme": sy, "ordre": i}
            for i, (c, lb, r, n, d, sy) in enumerate(POSTES)
        ],
    )  # fmt: skip
    _executer(
        "INSERT INTO devise (code, nom, cours) VALUES (:code, :nom, CAST(:cours AS NUMERIC))"
        " ON CONFLICT (code) DO NOTHING",
        [{"code": c, "nom": n, "cours": v} for c, n, v in DEVISES],
    )
    _executer(
        "INSERT INTO magasin (code, nom, type)"
        " SELECT CAST(:code AS VARCHAR), CAST(:code AS VARCHAR), CAST(:type AS VARCHAR)"
        " WHERE NOT EXISTS (SELECT 1 FROM magasin WHERE type = CAST(:type AS VARCHAR))"
        " ON CONFLICT (code) DO NOTHING",
        [{"code": c, "type": t} for c, t in MAGASINS],
    )
    _executer(
        "INSERT INTO motif (type_operation, libelle, code_r, ordre, impose_role)"
        " VALUES (:type, :libelle, :code_r, :ordre, :role)"
        " ON CONFLICT (type_operation, libelle) DO NOTHING",
        [
            {"type": t, "libelle": lb, "code_r": c, "ordre": _rang(t, lb), "role": r}
            for t, lb, c, r in MOTIFS
        ],
    )
    _executer(
        "INSERT INTO parametre (cle, valeur) VALUES (:cle, :valeur) ON CONFLICT (cle) DO NOTHING",
        [{"cle": c, "valeur": v} for c, v in REGLAGES],
    )


def _rang(type_operation: str, libelle: str) -> int:
    """Le rang d'un motif parmi ceux de son type (0, 1, 2…)."""
    du_type = [lb for t, lb, _, _ in MOTIFS if t == type_operation]
    return du_type.index(libelle)


def downgrade() -> None:
    """Retire les semences (celles qu'aucune donnée ne cite encore)."""
    retraits = (
        ("parametre", "cle", [c for c, _ in REGLAGES]),
        ("motif", "libelle", [m[1] for m in MOTIFS]),
        ("magasin", "code", [c for c, _ in MAGASINS]),
        ("devise", "code", [c for c, _, _ in DEVISES]),
        ("poste_frais", "code", [p[0] for p in POSTES]),
        ("role_nomenclature", "code", [r[0] for r in ROLES]),
    )
    for table, cle, valeurs in retraits:
        op.get_bind().execute(sa.text(f"DELETE FROM {table} WHERE {cle} = ANY(:v)"), {"v": valeurs})  # noqa: S608
