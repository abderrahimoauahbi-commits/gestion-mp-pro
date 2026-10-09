"""Le classeur du journal des actions (route 52 ; Gestion MP `exporter_journal`, B108).

Les mêmes lignes que l'écran Journal avec les mêmes filtres (personne, action, objet, fiche,
dates, mots), les plus récentes d'abord ; les filtres posés sont écrits au-dessus du tableau ;
« Quand » est un vrai horodatage Excel à l'heure de l'usine. Les changements (avant / après) sont
écrits « champ : valeur » ; pour qui ne voit pas les prix (l'administrateur), les champs
monétaires y sont vidés comme dans la réponse JSON (`securite.sans_prix`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from gestion_mp_pro.documents.format import nombre
from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, filtres, titre
from gestion_mp_pro.modeles import Journal
from gestion_mp_pro.securite.prix import sans_prix
from gestion_mp_pro.services.comptes import libelle_role
from gestion_mp_pro.services.journal import FiltreJournal

LIMITE = 100_000
"""Lignes exportées au plus (comme Gestion MP) ; au-delà, le classeur le dit."""
FEUILLE = "Journal des actions"


def _valeur(v: object) -> str:
    """Une valeur d'un changement, lisible : nombres à la française, vide « — »."""
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "oui" if v else "non"
    if isinstance(v, int | float | Decimal):
        return nombre(v, 0, 6)
    if isinstance(v, list):
        return ", ".join(_valeur(x) for x in v)
    if isinstance(v, dict):
        return "{" + _changements(v) + "}"
    return str(v)


def _changements(champs: Mapping[str, Any] | None) -> str:
    """« prix : 2,5 · statut : envoyée »."""
    return " · ".join(f"{cle} : {_valeur(v)}" for cle, v in (champs or {}).items())


def colonnes(voit_prix: bool) -> tuple[Colonne, ...]:
    """Les colonnes du journal ; avant/après sans prix pour qui ne les voit pas."""

    def lisible(champs: dict[str, Any] | None) -> str:
        """Les champs changés, sans prix pour qui ne les voit pas."""
        if champs is None:
            return ""
        return _changements(champs if voit_prix else sans_prix(champs))  # type: ignore[arg-type]

    return (
        Colonne("Quand", lambda j: j.quand, "horodatage"),
        Colonne("Par", lambda j: j.utilisateur_nom or "système", largeur=20),
        Colonne("Rôle", lambda j: libelle_role(j.role) if j.role else "", largeur=20),
        Colonne("Action", lambda j: j.action, largeur=28),
        Colonne("Sur", lambda j: str(j.objet), largeur=16),
        Colonne("Fiche n°", lambda j: j.objet_id, "entier", largeur=10),
        Colonne("Numéro", lambda j: j.numero, largeur=16),
        Colonne("Détail", lambda j: j.detail, largeur=50),
        Colonne("Avant", lambda j: lisible(j.avant), largeur=40),
        Colonne("Après", lambda j: lisible(j.apres), largeur=40),
    )


def _par(f: FiltreJournal, lignes: Sequence[Journal]) -> str:
    """Le nom de la personne filtrée (lu sur ses lignes), sinon son numéro de compte."""
    if f.utilisateur is None:
        return ""
    nom = next((j.utilisateur_nom for j in lignes if j.utilisateur_id == f.utilisateur), "")
    return nom or f"compte n° {f.utilisateur}"


def entete(f: FiltreJournal, lignes: Sequence[Journal], total: int, jour: date) -> list[str]:
    """Le titre daté, les filtres posés, et ce qui manque si la limite est atteinte."""
    lignes_titre = [
        titre(FEUILLE, jour),
        filtres(
            [
                ("par", _par(f, lignes)),
                ("action", f.action),
                ("sur", f.objet),
                ("fiche n°", f.objet_id),
                ("du", f.du),
                ("au", f.au),
                ("mots", f.q),
            ]
        ),
    ]
    if total > len(lignes):
        lignes_titre.append(
            f"Les {nombre(len(lignes))} plus récentes sur {nombre(total)} : "
            "resserrer les filtres pour tout exporter."
        )
    return lignes_titre


def journal(
    lignes: Sequence[Journal], total: int, f: FiltreJournal, voit_prix: bool, jour: date
) -> bytes:
    """Le classeur du journal filtré."""
    feuille = Feuille(FEUILLE, colonnes(voit_prix), lignes, entete(f, lignes, total, jour))
    return classeur([feuille], voit_prix)
