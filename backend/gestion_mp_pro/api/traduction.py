"""Traduction française des refus de saisie de Pydantic (héritage API, EXPLOITATION § 1).

Reprise de Gestion MP (`main.py:164-187`) : le champ est le chemin `loc` sans `body`, `query`,
`path`, joint par des points (`lignes.0.quantite`), et le message anglais est traduit par les
mêmes remplacements successifs, dans le même ordre. PRO ajoute ce qui sortait en anglais
(incohérence B.13-10 : « valeur incorrecte integer, unable to parse… ») : les types d'erreur
courants ont leur phrase, le préfixe « Value error, » des validateurs est retiré, et chaque
champ est aussi rendu à part (`champs`) pour que l'écran l'affiche sous la saisie.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REMPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Field required", "à renseigner"),
    ("Input should be a valid", "valeur incorrecte"),
    ("should be greater than or equal to", "doit être au moins"),
    ("should be greater than", "doit être supérieur à"),
    ("should be less than or equal to", "doit être au plus"),
    ("should be less than", "doit être inférieur à"),
    ("should have at least", "trop court : au moins"),
    ("should have at most", "trop long : au plus"),
    ("characters", "caractères"),
    ("character", "caractère"),
    ("String", "Texte"),
    ("Input", "La valeur"),
    ("List", "La liste"),
    ("item after validation", "élément"),
    ("items", "éléments"),
)
"""Les remplacements de Gestion MP, dans leur ordre (le plus long d'abord s'ils se recouvrent)."""

PAR_TYPE: dict[str, str] = {
    "missing": "à renseigner",
    "extra_forbidden": "champ inconnu",
    "json_invalid": "JSON illisible",
    "json_type": "JSON attendu",
    "int_parsing": "nombre entier attendu",
    "int_type": "nombre entier attendu",
    "int_from_float": "nombre entier attendu",
    "float_parsing": "nombre attendu",
    "float_type": "nombre attendu",
    "decimal_parsing": "nombre attendu",
    "decimal_type": "nombre attendu",
    "finite_number": "nombre fini attendu",
    "bool_parsing": "oui ou non attendu (true / false)",
    "bool_type": "oui ou non attendu (true / false)",
    "string_type": "texte attendu",
    "list_type": "liste attendue",
    "dict_type": "objet attendu",
    "model_type": "objet attendu",
    "model_attributes_type": "objet attendu",
    "date_parsing": "date attendue (AAAA-MM-JJ)",
    "date_from_datetime_parsing": "date attendue (AAAA-MM-JJ)",
    "date_type": "date attendue (AAAA-MM-JJ)",
    "datetime_parsing": "date et heure attendues (AAAA-MM-JJTHH:MM)",
    "datetime_from_date_parsing": "date et heure attendues (AAAA-MM-JJTHH:MM)",
    "datetime_type": "date et heure attendues (AAAA-MM-JJTHH:MM)",
    "string_pattern_mismatch": "forme incorrecte",
    "none_required": "doit être vide",
    "decimal_max_digits": "trop de chiffres",
    "decimal_max_places": "trop de décimales",
    "decimal_whole_digits": "trop de chiffres avant la virgule",
}
"""Phrases propres à PRO pour les types que les remplacements laissaient en anglais."""

ENLEVER_DU_CHEMIN = frozenset({"body", "query", "path", "header", "cookie"})
PREFIXES_VALIDATEUR = ("Value error, ", "Assertion failed, ")


def chemin(loc: Sequence[Any]) -> str:
    """`("body", "lignes", 0, "quantite")` → `lignes.0.quantite`."""
    return ".".join(str(x) for x in loc if x not in ENLEVER_DU_CHEMIN)


def _par_remplacements(texte: str) -> str:
    """Les remplacements successifs de Gestion MP."""
    for anglais, francais in REMPLACEMENTS:
        texte = texte.replace(anglais, francais)
    return texte


def _choix(contexte: Mapping[str, Any]) -> str:
    """« a, b ou c » pour une énumération ou un littéral."""
    attendu = str(contexte.get("expected", ""))
    return attendu.replace("' or '", "' ou '")


def message(erreur: Mapping[str, Any]) -> str:
    """La phrase française d'une erreur de validation Pydantic."""
    genre = str(erreur.get("type", ""))
    texte = str(erreur.get("msg", ""))
    contexte = erreur.get("ctx") or {}
    if genre in {"value_error", "assertion_error"}:
        for prefixe in PREFIXES_VALIDATEUR:
            texte = texte.removeprefix(prefixe)
        return texte
    if genre in {"enum", "literal_error"}:
        return f"valeur inconnue : {_choix(contexte)} attendu"
    if genre in PAR_TYPE:
        return PAR_TYPE[genre]
    return _par_remplacements(texte)


def traduire_validation(erreurs: Sequence[Mapping[str, Any]]) -> tuple[str, dict[str, str]]:
    """Le détail « champ : message ; champ : message » et le message de chaque champ."""
    phrases: list[str] = []
    champs: dict[str, str] = {}
    for erreur in erreurs:
        champ = chemin(erreur.get("loc", ()))
        texte = message(erreur)
        phrases.append(f"{champ} : {texte}" if champ else texte)
        if champ and champ not in champs:
            champs[champ] = texte
    return " ; ".join(phrases), champs
