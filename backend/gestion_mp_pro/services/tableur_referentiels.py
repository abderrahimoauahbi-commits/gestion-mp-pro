"""Les colonnes du tableur des matières et les référentiels qu'il cite (routes 78–80).

Une seule déclaration des colonnes (intitulé exact, champ de la fiche, genre de la case) pour
le modèle téléchargé (`exports/referentiels`) et la relecture (`services/tableur_matieres`).
Les codes cités (rôle, classification, devise, code douanier) et les fournisseurs (par nom) se
retrouvent **sans tenir compte de la casse** (A-03) ; les messages disent le libellé de la
colonne et où ajouter ce qui manque (P7-10).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    CodeDouanier,
    Composition,
    Couleur,
    Devise,
    Fournisseur,
    RoleNomenclature,
    Titrage,
    TypeFil,
)

COLONNES: tuple[tuple[str, str, str], ...] = (
    ("Référence", "reference", "texte"),
    ("Désignation", "designation", "texte"),
    ("Rôle", "role_id", "role"),
    ("Composition", "composition_id", "composition"),
    ("Type de fil", "type_fil_id", "type_fil"),
    ("Titrage", "titrage_id", "titrage"),
    ("Couleur", "couleur_id", "couleur"),
    ("Code couleur", "couleur_code", "texte"),
    ("Densité", "densite", "nombre"),
    ("Fournisseur", "fournisseur_id", "fournisseur"),
    ("Prix", "prix", "nombre"),
    ("Unité du prix", "unite_prix", "unite_prix"),
    ("Devise", "devise", "devise"),
    ("Unité d'achat", "unite_achat", "texte"),
    ("Contenance", "contenance_achat", "nombre"),
    ("Minimum de commande", "minimum_commande", "nombre"),
    ("kg / bobine", "poids_bobine", "nombre"),
    ("Bobines par palette", "bobines_palette", "nombre"),
    ("Stock minimum", "stock_min", "nombre"),
    ("Couverture minimum (mois)", "couv_min_mois", "nombre"),
    ("Groupe d'équivalence", "groupe_equiv", "texte"),
    ("Priorité dans le groupe", "priorite_equiv", "nombre"),
    ("Code douanier", "code_douanier_id", "code_douanier"),
    ("En service", "actif", "actif"),
)
"""(intitulé, champ, genre), dans l'ordre du modèle (P7-12 : + Priorité, Vider, Version)."""

VIDER = "Vider"
VERSION = "Version"
SE_COMMANDE = "Se commande en (lecture seule)"
LIBELLES = {intitule: champ for intitule, champ, _ in COLONNES}
INTITULES = {champ: intitule for intitule, champ, _ in COLONNES}
ACTIF = {
    **dict.fromkeys(("oui", "1", "vrai", "true", "x"), True),
    **dict.fromkeys(("non", "0", "faux", "false"), False),
}
NE_SE_VIDE_PAS = frozenset({"reference", "role_id", "unite_prix", "devise", "actif"})
VIDE: dict[str, Any] = {
    "designation": "",
    "composition_id": None,
    "type_fil_id": None,
    "titrage_id": None,
    "couleur_id": None,
    "couleur_code": "",
    "densite": Decimal(0),
    "fournisseur_id": None,
    "prix": Decimal(0),
    "unite_achat": "",
    "contenance_achat": Decimal(0),
    "minimum_commande": Decimal(0),
    "poids_bobine": Decimal(0),
    "bobines_palette": Decimal(0),
    "stock_min": Decimal(0),
    "couv_min_mois": Decimal(0),
    "groupe_equiv": "",
    "priorite_equiv": None,
    "code_douanier_id": None,
}
"""La valeur d'un champ vidé par la colonne « Vider »."""

INCONNUS = {
    "role": "Rôle « {} » inconnu",
    "composition": "Composition « {} » inconnue : l'ajouter d'abord à la classification",
    "type_fil": "Type de fil « {} » inconnu : l'ajouter d'abord à la classification",
    "titrage": "Titrage « {} » inconnu : l'ajouter d'abord à la classification",
    "couleur": "Couleur « {} » inconnue : l'ajouter d'abord à la classification",
    "devise": "Devise « {} » inconnue : l'ajouter d'abord (Réglages › Devises)",
    "code_douanier": "Code douanier « {} » inconnu : demander à la direction de l'ajouter",
    "fournisseur": "Fournisseur « {} » inconnu",
}


@dataclass(frozen=True)
class Referentiels:
    """Les codes et noms connus, en minuscules → valeur, et l'inverse pour l'affichage."""

    trouver: dict[str, dict[str, Any]]
    noms: dict[str, dict[Any, str]]

    def chercher(self, genre: str, texte: str) -> Any:
        """La valeur d'un code ou d'un nom (casse ignorée ; espaces retirés d'un code douanier)."""
        cle = "".join(texte.split()) if genre == "code_douanier" else texte
        return self.trouver[genre].get(cle.lower())

    def inconnu(self, genre: str, texte: str) -> str:
        """Le problème d'un code ou d'un nom inconnu."""
        return INCONNUS[genre].format(texte)

    def nom(self, genre: str, valeur: Any) -> str:
        """Ce que l'écran affiche d'une valeur (code, nom), « — » si vide."""
        if valeur is None or valeur == "":
            return "—"
        if genre in self.noms:
            return self.noms[genre].get(valeur, str(valeur))
        if isinstance(valeur, bool):
            return "oui" if valeur else "non"
        if isinstance(valeur, Decimal):
            return f"{valeur.normalize():f}".replace(".", ",")
        return str(valeur)


def referentiels(s: Session) -> Referentiels:
    """Les référentiels cités par le tableur, lus une fois."""
    paires: dict[str, list[tuple[Any, str]]] = {
        "role": list(s.execute(select(RoleNomenclature.id, RoleNomenclature.code))),
        "composition": list(s.execute(select(Composition.id, Composition.code))),
        "type_fil": list(s.execute(select(TypeFil.id, TypeFil.code))),
        "titrage": list(s.execute(select(Titrage.id, Titrage.code))),
        "couleur": list(s.execute(select(Couleur.id, Couleur.code))),
        "devise": [(c, c) for c in s.scalars(select(Devise.code))],
        "code_douanier": list(s.execute(select(CodeDouanier.id, CodeDouanier.code))),
        "fournisseur": list(s.execute(select(Fournisseur.id, Fournisseur.nom))),
    }
    return Referentiels(
        trouver={g: {texte.lower(): v for v, texte in p} for g, p in paires.items()},
        noms={g: {v: texte for v, texte in p} for g, p in paires.items()},
    )


def genre(champ: str) -> str:
    """Le genre de la case d'un champ (« role », « nombre »…)."""
    return next(g for _, c, g in COLONNES if c == champ)
