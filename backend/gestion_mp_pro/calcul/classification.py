"""La classification d'un fil : composition, type, titrage, couleur (CALCULS A § 2).

Portage tel quel de `gestion_mp/calcul/classification.py`, découpé en fonctions courtes.

Une référence de fil n'est pas un code opaque : elle dit de quoi le fil est
fait, comment il est travaillé, sa grosseur et sa couleur.

    PP FRZ-2900 Dtex-Gold 3423-Hs
    │  │    │    │    │    │    └ suffixe du fournisseur
    │  │    │    │    │    └ code couleur du fournisseur
    │  │    │    │    └ libellé de la couleur
    │  │    │    └ unité du titrage
    │  │    └ titrage
    │  └ type de fil (frisé)
    └ composition (polypropylène)

Ce module fait les deux chemins :

- `decomposer` lit une référence existante et en retire ses parties — c'est ce
  qui a permis de classer les 124 références du classeur sans les ressaisir ;
- `composer` fait l'inverse : on choisit composition, type, titrage et couleur,
  la référence s'écrit toute seule. La saisie reste modifiable : la règle n'est
  pas la loi, un fournisseur peut imposer son propre code.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Les unités de titrage du métier. L'ordre compte : « Deniers » avant « Den ».
UNITES_TITRAGE = ("Dtex", "Deniers", "Den", "Tex", "Nm", "Nec")
UNITE_PAR_DEFAUT = {
    "PP": "Dtex",
    "PES": "Deniers",
    "MICRO PES": "Deniers",
}

# Marques de fin employées par les fournisseurs : elles ne disent rien du fil,
# et il faut les écarter avant de chercher le type — sans quoi tout ce qui finit
# par « -Hs » passerait pour du heat-set.
SUFFIXES_FOURNISSEUR = ("HS", "OZ", "TAT", "SUJ", "SF", "GZM", "TURK", "TEXT")

# Marqueurs de type rencontrés dans les références, et ce qu'ils veulent dire.
TYPES_CONNUS: dict[str, str] = {
    "FRZ": "Frisé",
    "FRIZE": "Frisé",
    "SH": "Shrink (rétractable)",
    "FDY": "Filament continu (FDY)",
    "BCF": "Bouclé continu (BCF)",
    "VER": "Vériné",
    "HS": "Heat-set",
    "CB": "Câblé",
    "MN": "Monofilament",
    "NYLON": "Nylon",
    "SSL": "Ssl",
}

# Compositions courantes, par préfixe de référence.
COMPOSITIONS: dict[str, tuple[str, str]] = {
    "PP": ("Polypropylène", "Synthétique"),
    "PES": ("Polyester", "Synthétique"),
    "MICRO PES": ("Micro polyester", "Synthétique"),
    "PA": ("Polyamide", "Synthétique"),
    "JUTE": ("Jute", "Naturel"),
    "LAINE": ("Laine", "Naturel"),
    "COTON": ("Coton", "Naturel"),
    "SBR": ("SBR (latex)", "Intrant"),
    "PLASTIQUE": ("Plastique", "Intrant"),
    "SIMILI CUIR": ("Simili cuir", "Intrant"),
    "BANDE": ("Bande", "Intrant"),
}


# Le vocabulaire des couleurs du catalogue — français et anglais mêlés, comme
# les fournisseurs les écrivent. Il sert à séparer la couleur du code : dans
# « Beige Cp-1432 », « Beige » est la couleur et « Cp-1432 » la référence du
# teinturier. La liste s'enrichit du référentiel Couleurs à l'usage.
MOTS_COULEUR = {
    "beige",
    "black",
    "bleu",
    "blue",
    "blanc",
    "bordeau",
    "bordeaux",
    "brique",
    "brown",
    "camel",
    "cream",
    "creme",
    "dark",
    "ecru",
    "fonce",
    "gold",
    "green",
    "grey",
    "gris",
    "ivory",
    "jaune",
    "khave",
    "light",
    "marine",
    "marron",
    "mouchete",  # sans accent : le mot testé l'est aussi (« Moucheté » se reconnaît)
    "mouchte",
    "multi",
    "navy",
    "noir",
    "olive",
    "or",
    "orange",
    "pink",
    "red",
    "rose",
    "rouge",
    "seker",
    "taupe",
    "terra",
    "turkoise",
    "turquoise",
    "vert",
    "vison",
    "vizon",
    "white",
    "yellow",
    "antrasit",
    "anty",
    "claire",
    "clair",
}


def _mot_couleur(mot: str) -> bool:
    """« D.Green », « L.Beige », « Dk.Vison » : le préfixe de nuance ne compte pas."""
    propre = _sans_accent(mot).lower().strip(".")
    propre = re.sub(r"^(d|l|dk|lt)\.", "", propre)
    return propre in MOTS_COULEUR


@dataclass
class Classification:
    """Ce qu'une référence dit d'elle-même."""

    composition: str = ""  # code : PP, PES, JUTE…
    type_fil: str = ""  # code : FRZ, SH, FDY…
    titrage: str = ""  # « 2900 », « 20/2 », « 1750*2 »
    titrage_unite: str = ""  # Dtex, Deniers, Nm…
    couleur: str = ""  # libellé : Or, Beige, Bleu marine…
    couleur_code: str = ""  # code du fournisseur : 3423, Cp-1432…
    suffixe: str = ""  # marque de fin : Hs, Oz, Tat, Suj…

    @property
    def titrage_complet(self) -> str:
        """« 2900 Dtex » : le titrage et son unité."""
        return " ".join(x for x in (self.titrage, self.titrage_unite) if x)


def _sans_accent(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()


def code_composition(nature: str) -> str:
    """Le code de composition d'une nature écrite en toutes lettres.

    Le classeur écrit « Polyester Fil Shrink » là où la référence écrit « PES
    Sh » : la nature porte parfois le type. On ne garde que la matière.
    """
    propre = _sans_accent(nature).strip().lower()
    for code, (libelle, _) in COMPOSITIONS.items():
        if propre.startswith(_sans_accent(libelle).lower()):
            return code
    for code in COMPOSITIONS:
        if propre.startswith(code.lower()):
            return code
    return propre.split()[0].upper() if propre else ""


def libelle_composition(code: str) -> tuple[str, str]:
    """Libellé et famille d'une composition, à défaut le code lui-même."""
    return COMPOSITIONS.get(code.upper(), (code, "Autre"))


_TITRAGE = re.compile(
    r"(?<![\w/])(\d+(?:[.,]\d+)?(?:\s*[*x]\s*\d+)?(?:\s*/\s*\d+)?)\s*"
    r"(" + "|".join(UNITES_TITRAGE) + r")?\b",
    re.IGNORECASE,
)


def _composition(brut: str, nature: str) -> str:
    """D'abord la nature du catalogue, sinon le début de la référence."""
    composition = code_composition(nature) if nature else ""
    if not composition:
        sans_accent = _sans_accent(brut).upper()
        for code in sorted(COMPOSITIONS, key=len, reverse=True):
            if sans_accent.startswith(code):
                return code
    return composition


def _titrage(resultat: Classification, trouve: re.Match[str]) -> None:
    resultat.titrage = re.sub(r"\s*([*x/])\s*", r"\1", trouve.group(1)).replace("x", "*")
    unite = trouve.group(2)
    if unite:
        resultat.titrage_unite = "Deniers" if unite.lower().startswith("den") else unite.title()
        resultat.titrage_unite = {"Dtex": "Dtex", "Nm": "Nm", "Tex": "Tex", "Nec": "Nec"}.get(
            resultat.titrage_unite, resultat.titrage_unite
        )
    elif "/" in resultat.titrage:
        resultat.titrage_unite = "Nm"  # 20/2, 12/1 : numéro métrique
    else:
        resultat.titrage_unite = UNITE_PAR_DEFAUT.get(resultat.composition, "")


def _couleur(resultat: Classification, reste: str) -> None:
    """Les mots sans chiffre font le libellé, ceux qui en portent font le code."""
    mots = [m for m in re.split(r"[\s-]+", reste.lstrip(" -")) if m]
    libelle: list[str] = []
    codes: list[str] = []
    for mot in mots:
        if _sans_accent(mot).upper() == resultat.type_fil:
            continue
        if re.search(r"\d", mot) or (libelle and not _mot_couleur(mot)):
            codes.append(mot)
        elif not codes:
            libelle.append(mot)
    resultat.couleur = " ".join(libelle)
    resultat.couleur_code = " ".join(codes)


def decomposer(reference: str, nature: str = "") -> Classification:
    """Retire d'une référence ce qu'elle dit : composition, type, titrage, couleur.

    Rien n'est inventé : ce qui ne se lit pas reste vide, à renseigner à la main.
    """
    brut = " ".join(reference.split())
    resultat = Classification()
    if not brut:
        return resultat
    resultat.composition = _composition(brut, nature)
    # Le suffixe du fournisseur se retire d'abord : il ferait passer « …-Hs » pour un type.
    corps = brut
    dernier = re.split(r"[\s-]+", brut)[-1]
    if _sans_accent(dernier).upper() in SUFFIXES_FOURNISSEUR:
        resultat.suffixe = dernier
        corps = brut[: brut.rfind(dernier)].rstrip(" -")
    majuscules = _sans_accent(corps).upper()
    for marqueur in sorted(TYPES_CONNUS, key=len, reverse=True):
        if re.search(rf"(?<![A-Z]){marqueur}(?![A-Z])", majuscules):
            resultat.type_fil = marqueur
            break
    trouve = _TITRAGE.search(corps)
    if trouve:
        _titrage(resultat, trouve)
    _couleur(resultat, corps[trouve.end() :] if trouve else corps)
    return resultat


def composer(
    composition: str,
    *,
    type_fil: str = "",
    titrage: str = "",
    titrage_unite: str = "",
    couleur: str = "",
    couleur_code: str = "",
    suffixe: str = "",
) -> str:
    """Écrit la référence à partir de ses parties — la saisie semi-automatique.

    On suit la façon d'écrire du catalogue : « PP FRZ-2900 Dtex-Gold 3423-Hs ».
    Chaque partie absente disparaît sans laisser de tiret orphelin.
    """
    tete = " ".join(x for x in (composition.strip().upper(), type_fil.strip().upper()) if x)
    grosseur = " ".join(x for x in (titrage.strip(), titrage_unite.strip()) if x)
    teinte = " ".join(x for x in (couleur.strip(), couleur_code.strip()) if x)
    segments = [x for x in (tete, grosseur, teinte, suffixe.strip()) if x]
    return "-".join(segments)


def designation(couleur: str, couleur_code: str = "") -> str:
    """La désignation courte affichée à côté de la référence."""
    return " ".join(x for x in (couleur.strip(), f"({couleur_code})" if couleur_code else "") if x)
