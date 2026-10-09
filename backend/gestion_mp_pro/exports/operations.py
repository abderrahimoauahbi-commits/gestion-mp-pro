"""Classeur des opérations de stock (route 241) : une ligne par ligne d'opération, avec les mêmes
filtres que l'écran ; les types permis au rôle seulement ; **sans prix ni valeur** pour qui ne
les voit pas (un classeur n'est pas filtré par la route, barrière 4).

Conventions de `exports.stock.classeur` (en attendant `exports/classeur.py` du lot D9).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from gestion_mp_pro.exports.stock import Colonne, classeur
from gestion_mp_pro.services.operations.lecture import LigneLue, OperationLue

STATUTS = {"brouillon": "Brouillon", "validee": "Validée", "annulee": "Annulée"}


@dataclass(frozen=True)
class _Rang:
    """Une ligne du classeur : l'opération et une de ses lignes."""

    o: OperationLue
    x: LigneLue


COLONNES = (
    Colonne("Numéro", lambda r: r.o.numero or "Brouillon", largeur=16),
    Colonne("Type", lambda r: r.o.type_libelle, largeur=24),
    Colonne("État", lambda r: STATUTS.get(r.o.statut, r.o.statut), largeur=10),
    Colonne("Date", lambda r: r.o.date, "date", largeur=12),
    Colonne("Motif", lambda r: r.o.motif, largeur=26),
    Colonne("Code motif", lambda r: r.o.code_motif, largeur=8),
    Colonne("Ordre", lambda r: r.o.ordre, largeur=16),
    Colonne("Fournisseur", lambda r: r.o.fournisseur, largeur=24),
    Colonne("Référence", lambda r: r.x.reference, largeur=30),
    Colonne("Lot", lambda r: r.x.lot, largeur=18),
    Colonne("Magasin", lambda r: r.x.magasin, largeur=14),
    Colonne("Vers", lambda r: r.x.magasin_destination, largeur=14),
    Colonne("Quantité (kg)", lambda r: r.x.quantite, "kg"),
    Colonne(
        "Prix / kg", lambda r: r.x.prix if r.o.type == "ouverture" else None, "prix", monetaire=True
    ),  # fmt: skip
    Colonne("Devise", lambda r: r.x.devise or "", monetaire=True, largeur=8),
    Colonne("Observations", lambda r: r.o.commentaire, largeur=30),
    Colonne("Créée par", lambda r: r.o.cree_par, largeur=16),
    Colonne("Validée par", lambda r: r.o.validee_par, largeur=16),
    Colonne("Validée le", lambda r: r.o.validee_le, "date", largeur=12),
    Colonne("Annulée par", lambda r: r.o.annulee_par, largeur=16),
    Colonne("Annulée le", lambda r: r.o.annulee_le, "date", largeur=12),
)
"""Route 241."""


def operations(lues: Sequence[OperationLue], voit_prix: bool) -> bytes:
    """Les opérations filtrées, une ligne par ligne d'opération."""
    rangs = [_Rang(o, x) for o in lues for x in o.lignes]
    return classeur("Opérations", COLONNES, rangs, voit_prix)
