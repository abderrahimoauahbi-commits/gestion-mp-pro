"""Traduction française des refus de saisie de Pydantic (héritage API, EXPLOITATION § 1).

Reprise de Gestion MP (`main.py:164-187`) : le champ est le chemin `loc` sans `body`, `query`,
`path`, joint par des points (`lignes.0.quantite`), et le message anglais est traduit par les
mêmes remplacements successifs, dans le même ordre. PRO ajoute ce qui sortait en anglais
(incohérence B.13-10 : « valeur incorrecte integer, unable to parse… ») : les types d'erreur
courants ont leur phrase, le préfixe « Value error, » des validateurs est retiré, et chaque
champ est aussi rendu à part (`champs`) pour que l'écran l'affiche sous la saisie.

`traduire_refus_base` : le code et la phrase d'une contrainte de la base violée (filet F-07).
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


# --- Refus de la base (dernier recours, défaut F-07 de Gestion MP) ----------------------------

RIEN_ENREGISTRE = "Rien n'a été enregistré."

MESSAGE_REFUS_BASE = (
    "Cette saisie contredit une règle de la base (doublon, valeur hors limites) : la vérifier."
)
"""La phrase de Gestion MP corrigé (F-07), pour un refus que rien ne permet de préciser."""

PAR_SQLSTATE: dict[str, tuple[str, str]] = {
    "23505": (
        "doublon",
        "Cette saisie existe déjà (référence, code ou nom déjà pris) : la vérifier.",
    ),
    "23P01": ("doublon", "Cette saisie chevauche une fiche existante : la vérifier."),
    "23502": ("regle_de_la_base", "Une valeur obligatoire manque : la vérifier."),
    "23514": (
        "regle_de_la_base",
        "Cette saisie contredit une règle de la base (valeur hors limites ou non permise) : "
        "la vérifier.",
    ),
    "23001": (
        "fiche_utilisee",
        "Cette fiche est utilisée ailleurs : la désactiver plutôt que la supprimer.",
    ),
}
"""Code et phrase par état SQL (classe 23, violations d'intégrité de PostgreSQL)."""

FICHE_UTILISEE = PAR_SQLSTATE["23001"]
REFERENCE_ABSENTE = (
    "reference_absente",
    "Une fiche citée n'existe pas ou vient d'être supprimée : recharger, puis refaire la saisie.",
)
PAS_UN_NOMBRE = ("regle_de_la_base", "Une valeur saisie n'est pas un nombre : la vérifier.")
DONNEE_HORS_LIMITES = (
    "regle_de_la_base",
    "Une valeur saisie est hors limites ou mal formée (nombre trop grand, texte trop long) : "
    "la vérifier.",
)


def traduire_refus_base(
    sqlstate: str | None,
    contrainte: str | None = None,
    detail: str | None = None,
    instruction: str | None = None,
) -> tuple[str, str]:
    """Le code (`api/erreurs.CODES`, tous 409) et la phrase d'un refus de la base.

    `sqlstate` : état SQL de PostgreSQL ; `contrainte` : nom de la contrainte violée ;
    `detail` : le DETAIL du serveur (anglais) ; `instruction` : le SQL envoyé. Une clé
    étrangère violée par un `DELETE` (ou « still referenced ») est une fiche utilisée ; par
    un `INSERT`/`UPDATE`, une fiche citée absente. Le refus de `NaN` (`ck_<table>_<col>_nombre`)
    a sa phrase. La phrase finit toujours par « Rien n'a été enregistré. ».
    """
    code, phrase = "regle_de_la_base", MESSAGE_REFUS_BASE
    if sqlstate == "23503":
        supprime = (instruction or "").lstrip().upper().startswith("DELETE")
        code, phrase = (
            FICHE_UTILISEE
            if supprime or "still referenced" in (detail or "")
            else REFERENCE_ABSENTE
        )
    elif sqlstate == "23514" and (contrainte or "").endswith("_nombre"):
        code, phrase = PAS_UN_NOMBRE
    elif sqlstate in PAR_SQLSTATE:
        code, phrase = PAR_SQLSTATE[sqlstate]
    elif sqlstate is not None and sqlstate.startswith("22"):
        code, phrase = DONNEE_HORS_LIMITES
    return code, f"{phrase} {RIEN_ENREGISTRE}"
