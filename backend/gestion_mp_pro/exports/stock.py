"""Classeurs du stock (routes 106 et 236) : le journal des mouvements et la liste des lots, avec
les mêmes filtres que l'écran (ARCHITECTURE § 11).

Conventions communes de `exports/classeur.py` (lot D9) : en-tête en gras, volets figés, filtre
automatique, vraies dates Excel, formats de chaque grandeur (ARCHITECTURE § 9.3), texte
commençant par `=`, `+`, `-` ou `@` gardé en texte. **Sans prix ni valeur** pour qui ne les voit
pas (barrière 4 : un classeur n'est pas filtré par la route).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from gestion_mp_pro.exports import classeur as conventions
from gestion_mp_pro.exports.classeur import Colonne
from gestion_mp_pro.services.lots import STATUTS_LOT, LotSolde
from gestion_mp_pro.services.mouvements import LigneMouvement


def classeur(
    titre: str, colonnes: Sequence[Colonne], lignes: Sequence[Any], voit_prix: bool
) -> bytes:
    """Un classeur d'une feuille (en-tête en ligne 1) ; les colonnes monétaires si `voit_prix`."""
    feuille = conventions.Feuille(titre, colonnes, lignes)
    return conventions.classeur([feuille], voit_prix)


COLONNES_MOUVEMENTS = (
    Colonne("Date", lambda x: x.date, "date", largeur=12),
    Colonne("Saisi le", lambda x: x.saisi_le, "horodatage", largeur=17),
    Colonne("Mouvement", lambda x: x.libelle, largeur=24),
    Colonne("Document", lambda x: x.document_numero, largeur=16),
    Colonne("Référence", lambda x: x.reference, largeur=30),
    Colonne("Lot", lambda x: x.lot, largeur=18),
    Colonne("Magasin", lambda x: x.magasin, largeur=18),
    Colonne("Quantité (kg)", lambda x: x.quantite, "kg"),
    Colonne("Prix / kg", lambda x: x.prix, "prix", monetaire=True),
    Colonne("Devise", lambda x: x.devise, monetaire=True, largeur=8),
    Colonne("Cours", lambda x: x.cours, "cours", monetaire=True),
    Colonne("Coût unitaire (MAD)", lambda x: x.cout_mad, "prix", monetaire=True),
    Colonne("Valeur (MAD)", lambda x: x.valeur_mad, "montant", monetaire=True),
    Colonne("Motif", lambda x: x.motif, largeur=24),
    Colonne("Commentaire", lambda x: x.commentaire, largeur=30),
    Colonne("Par", lambda x: x.auteur, largeur=18),
    Colonne("Annule le mouvement n°", lambda x: x.contrepasse_id),
)
"""Route 106."""


def mouvements(lignes: Sequence[LigneMouvement], voit_prix: bool) -> bytes:
    """Le journal des mouvements, le plus récent d'abord."""
    return classeur("Mouvements", COLONNES_MOUVEMENTS, lignes, voit_prix)


def _magasins(x: LotSolde) -> str:
    return ", ".join(f"{m.magasin} : {m.quantite:.3f}".replace(".", ",") for m in x.magasins)


COLONNES_LOTS = (
    Colonne("Lot", lambda x: x.lot, largeur=18),
    Colonne("Statut", lambda x: STATUTS_LOT[x.statut], largeur=22),
    Colonne("Référence", lambda x: x.reference, largeur=30),
    Colonne("Désignation", lambda x: x.designation, largeur=24),
    Colonne("Rôle", lambda x: x.role, largeur=10),
    Colonne("Fournisseur", lambda x: x.fournisseur, largeur=22),
    Colonne("Entré le", lambda x: x.entre_le, "date", largeur=12),
    Colonne("Dernier mouvement", lambda x: x.historique.dernier_mouvement, "date"),
    Colonne("Entré (kg)", lambda x: x.historique.entre, "kg"),
    Colonne("Sorti (kg)", lambda x: x.historique.sorti, "kg"),
    Colonne("Reste (kg)", lambda x: x.quantite, "kg"),
    Colonne("Disponible (kg)", lambda x: x.disponible, "kg"),
    Colonne("En quarantaine (kg)", lambda x: x.quarantaine, "kg"),
    Colonne("Bobines", lambda x: x.bobines),
    Colonne("Magasins", _magasins, largeur=30),
    Colonne(
        "Ordres servis", lambda x: ", ".join(o.numero for o in x.historique.ordres), largeur=30
    ),
)
"""Route 236 (aucune colonne monétaire : la même pour tous les rôles)."""


def lots(lignes: Sequence[LotSolde], voit_prix: bool) -> bytes:
    """La liste des lots, telle que l'onglet Lots la filtre."""
    return classeur("Lots", COLONNES_LOTS, lignes, voit_prix)


def nom_de_fichier(prefixe: str, jour: date) -> str:
    """« mouvements-2026-10-08.xlsx »."""
    return conventions.nom_de_fichier(prefixe, jour)
