"""Classeur des opérations de stock (route 241) : une ligne par ligne d'opération, avec les mêmes
filtres que l'écran ; les types permis au rôle seulement ; **sans prix ni valeur** pour qui ne
les voit pas (un classeur n'est pas filtré par la route, barrière 4).

Conventions communes : `exports.classeur` (lot D9).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from gestion_mp_pro.exports.classeur import Colonne, Feuille, classeur, filtres, titre
from gestion_mp_pro.services.operations.lecture import LigneLue, OperationLue

STATUTS = {"brouillon": "Brouillon", "validee": "Validée", "annulee": "Annulée"}


@dataclass(frozen=True)
class _Rang:
    """Une ligne du classeur : l'opération et une de ses lignes."""

    o: OperationLue
    x: LigneLue


COLONNES = (
    Colonne("Numéro", lambda r: r.o.numero or "Brouillon"),
    Colonne("Type", lambda r: r.o.type_libelle),
    Colonne("État", lambda r: STATUTS.get(r.o.statut, r.o.statut)),
    Colonne("Date", lambda r: r.o.date, "date"),
    Colonne("Motif", lambda r: r.o.motif),
    Colonne("Code motif", lambda r: r.o.code_motif),
    Colonne("Ordre", lambda r: r.o.ordre),
    Colonne("Fournisseur", lambda r: r.o.fournisseur),
    Colonne("Référence", lambda r: r.x.reference),
    Colonne("Lot", lambda r: r.x.lot),
    Colonne("Magasin", lambda r: r.x.magasin),
    Colonne("Vers", lambda r: r.x.magasin_destination),
    Colonne("Quantité (kg)", lambda r: r.x.quantite, "kg_precis"),
    Colonne("Prix / kg", lambda r: r.x.prix if r.o.type == "ouverture" else None, "prix", True),
    Colonne("Devise", lambda r: r.x.devise or "", monetaire=True),
    Colonne("Observations", lambda r: r.o.commentaire),
    Colonne("Créée par", lambda r: r.o.cree_par),
    Colonne("Validée par", lambda r: r.o.validee_par),
    Colonne("Validée le", lambda r: r.o.validee_le, "horodatage"),
    Colonne("Annulée par", lambda r: r.o.annulee_par),
    Colonne("Annulée le", lambda r: r.o.annulee_le, "horodatage"),
)
"""Route 241."""


def operations(
    lues: Sequence[OperationLue],
    voit_prix: bool,
    jour: date,
    criteres: Sequence[tuple[str, object]],
) -> bytes:
    """Les opérations filtrées, une ligne par ligne d'opération ; titre daté, filtres dits."""
    rangs = [_Rang(o, x) for o in lues for x in o.lignes]
    entete = [titre("Opérations de stock", jour), filtres(criteres)]
    return classeur([Feuille("Opérations", COLONNES, rangs, entete)], voit_prix)
