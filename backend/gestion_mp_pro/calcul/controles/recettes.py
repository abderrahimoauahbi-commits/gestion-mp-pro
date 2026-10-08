"""Contrôle des recettes : C01 (T01 du classeur)."""

from __future__ import annotations

from gestion_mp_pro.calcul.controles.base import Contexte, Ligne, colonne, controle
from gestion_mp_pro.calcul.nomenclature import controle_recettes


@controle(
    "C01",
    gravite="bloquant",
    lien="/qualites",
    colonnes=(colonne("qualite", "texte"), colonne("roles", "texte")),
)
def recette_hors_cent(ctx: Contexte) -> tuple[str, list[Ligne]]:
    """La nomenclature doit sommer à 100 % dans chaque rôle utilisé."""
    lignes: list[Ligne] = [
        {
            "qualite": r.qualite,
            "roles": ", ".join(f"{e.role} ({e.somme:.4g} %)" for e in r.ecarts),
        }
        for r in controle_recettes(ctx.donnees)
        if not r.conforme
    ]
    return "Recette dont un rôle ne fait pas 100 %", lignes
