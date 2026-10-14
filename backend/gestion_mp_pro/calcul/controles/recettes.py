"""Contrôle des recettes : C01 (T01 du classeur)."""

from __future__ import annotations

from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.nomenclature import controle_recettes, texte_ecart


@controle(
    "C01",
    gravite="bloquant",
    lien="/qualites",
    colonnes=(colonne("qualite", "texte"), colonne("roles", "texte")),
)
def recette_hors_cent(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """La nomenclature doit sommer à 100 % dans chaque rôle utilisé ; un rôle qu'aucune matière
    du catalogue ne porte le dit (« créer la matière Franges »)."""
    lignes: list[Ligne] = [
        {
            "qualite": r.qualite,
            "roles": ", ".join(texte_ecart(e) for e in r.ecarts),
        }
        for r in controle_recettes(ctx.donnees)
        if not r.conforme
    ]
    return "Recette dont un rôle ne fait pas 100 %", lignes
