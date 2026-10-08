"""Petites fabriques de `Donnees` pour les essais du moteur, reprises des essais de Gestion MP.

- `ecriture` et `journal` : le journal du moteur comme le traduit le chargeur
  (`test_valorisation.ecriture` et `donnees` de Gestion MP) ;
- `usine` : une usine minimale, un fournisseur à 30 jours, une qualité, du fil en stock depuis
  juin (`_donnees` de `test_plan_besoins`, `test_audit2_achat`, `test_defauts_d`) ;
- `ligne_de` : la ligne de stock d'une référence.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from gestion_mp_pro.calcul.constantes import QUARANTAINE, TYPES_MOUVEMENT
from gestion_mp_pro.calcul.modele import (
    Article,
    Donnees,
    Fournisseur,
    LigneRecette,
    Magasin,
    Mouvement,
    Parametres,
    PlanQualite,
    Qualite,
)
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock

UN = [1.0] * 12
JOUR = date(2026, 10, 8)
"""Le jour des essais de Gestion MP : la fenêtre du réalisé couvre juillet à septembre 2026."""
J1, J2, J3 = date(2026, 3, 2), date(2026, 3, 9), date(2026, 3, 16)


def ecriture(
    n: int,
    jour: date,
    type_: str,
    quantite: float,
    *,
    prix: float = 0.0,
    devise: str = "MAD",
    lot: str = "L1",
    annule: int | None = None,
    cours: float = 0.0,
    ligne: int | None = None,
    ref: str = "P50",
    of: str = "",
) -> Mouvement:
    """Une écriture du journal, comme la traduit le chargeur : quantité positive pour une
    entrée ou une sortie, négative pour son annulation."""
    signe = TYPES_MOUVEMENT[type_][1]
    entree = (signe > 0) == (quantite > 0)
    if entree or annule:
        return Mouvement(
            date=jour,
            type=type_,
            reference=ref,
            quantite=quantite,
            prix_unite=prix,
            devise=devise,
            lot_fournisseur=lot,
            magasin_destination="MAG" if signe > 0 else "",
            magasin_source="MAG" if signe < 0 else "",
            id=n,
            contrepasse_id=annule,
            cours=cours,
            ligne_reception_id=ligne,
            numero_of=of,
            utilisateur="essai",
        )
    return Mouvement(
        date=jour,
        type=type_,
        reference=ref,
        quantite=quantite,
        prix_unite=prix,
        devise=devise,
        lot_fournisseur=lot,
        magasin_source="MAG",
        id=n,
        cours=cours,
        numero_of=of,
        utilisateur="essai",
    )


def journal(
    *mouvements: Mouvement, articles: list[Article] | None = None, **autres: Any
) -> Donnees:
    """Une matière P50 (catalogue 30 MAD), un magasin courant et une quarantaine."""
    return Donnees(
        articles=articles or [Article(reference="P50", prix_unite=30.0, fournisseur="F")],
        magasins=[Magasin(code="MAG"), Magasin(code="QUA", type=QUARANTAINE)],
        mouvements=list(mouvements),
        **autres,
    )


def usine(
    stock: float = 100_000, references: tuple[str, ...] = ("FIL A", "FIL B"), **autres: Any
) -> Donnees:
    """Une usine minimale : un fournisseur à 30 jours, une qualité de 1 000 m² par mois au
    kilo de FIL A le m², du fil en stock depuis juin."""
    valeurs: dict[str, Any] = {
        "parametres": Parametres(taux_perte=0.0, fenetre_realisation_jours=90),
        "fournisseurs": [Fournisseur(nom="F", delai_jours=30, couverture_commande_jours=30)],
        "articles": [
            Article(reference=r, role_bom="Poil", fournisseur="F", prix_unite=1) for r in references
        ],
        "qualites": [Qualite(code="Q", poids={"Poil": 1.0})],
        "recettes": [LigneRecette("Q", "FIL A", 100)],
        "plan": [PlanQualite("Q", base_mensuelle=1000, saisonnalite=UN)],
        "mouvements": [Mouvement(date(2026, 6, 1), "STOCK_INITIAL", r, stock) for r in references],
    }
    valeurs.update(autres)
    return Donnees(**valeurs)


def sortie(jour: date, reference: str, kg: float, of: str = "") -> Mouvement:
    """Une sortie vers la production."""
    return Mouvement(jour, "SORTIE_PROD", reference, kg, numero_of=of)


def instant(annee: int, mois: int, jour: int, heure: int = 0, minute: int = 0) -> datetime:
    """Un instant du moteur : l'heure de l'usine, sans fuseau (`VersionPlan.quand`…)."""
    return datetime(annee, mois, jour, heure, minute)  # noqa: DTZ001


def ligne_de(donnees: Donnees, reference: str, jour: date = JOUR) -> LigneStock:
    """La ligne de stock d'une référence à ce jour."""
    return next(x for x in etat_stock(donnees, jour) if x.reference == reference)
