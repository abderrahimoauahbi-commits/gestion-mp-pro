"""Parité : les traductions de la reprise refaites **dans une copie de Gestion MP**.

Les routes des documents de Gestion MP lisent la base elle-même (pas seulement le dépôt du
moteur) : pour expliquer un écart dans sa forme et son ampleur, Gestion MP est relancé sur une
copie où les traductions déclarées de la reprise ont été faites, une classe après l'autre, et
la route est relue. Un écart est expliqué par la première classe après laquelle la réponse de
Gestion MP égale celle de PRO.

Chaque traduction est écrite ici une seconde fois (sans le code de la reprise) et compte ce
qu'elle change ; les comptes sont confrontés au rapport de la reprise.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from parite_donnees import arrondi
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

K1_COLONNES = (
    ("commande_ligne", "contenance", "commande_ligne"),
    ("commande_ligne", "quantite", "commande_ligne"),
    ("dossier_ligne", "valeur_devise", "dossier_ligne"),
    ("facture", "montant", "facture"),
    ("inventaire_ligne", "theorique", "inventaire_ligne"),
    ("lot", "poids_bobine", "lot"),
    ("mouvement", "quantite", "mouvement"),
    ("bon_ligne", "quantite", "ordre_ligne"),
    ("bon_fabrication", "m2", "ordre_qualite"),
    ("reception_ligne", "quantite_attendue", "reception_ligne"),
)
"""(table de Gestion MP, colonne, table de PRO) : les colonnes que la reprise arrondit."""


def echelle(table_pro: str, colonne: str) -> int:
    """L'échelle de la colonne de PRO (le schéma fait foi)."""
    from gestion_mp_pro.modeles import Base

    type_: Any = Base.metadata.tables[table_pro].c[colonne].type
    return int(type_.scale or 0)


def k1(c: Connection) -> dict[str, int]:
    """K1 : chaque valeur arrondie à l'échelle de sa colonne PRO (`ROUND_HALF_UP`)."""
    comptes = {}
    for table, colonne, table_pro in K1_COLONNES:
        e = echelle(table_pro, colonne)
        lignes = c.execute(text(f"SELECT id, {colonne} FROM {table} WHERE {colonne} IS NOT NULL"))  # noqa: S608
        changees = [{"i": i, "v": arrondi(v, e)} for i, v in lignes if arrondi(v, e) != v]
        if changees:
            c.execute(text(f"UPDATE {table} SET {colonne} = :v WHERE id = :i"), changees)  # noqa: S608
        comptes[f"{table_pro}.{colonne}"] = len(changees)
    return comptes


def _executer(c: Connection, nom: str, sql: str) -> dict[str, int]:
    return {nom: c.execute(text(sql)).rowcount}


TRADUCTIONS: dict[str, Callable[[Connection], dict[str, int]]] = {
    "K1": k1,
    "K8a": lambda c: _executer(
        c,
        "mouvement.prix",
        "UPDATE mouvement SET prix = 0 WHERE type IN ('SORTIE', 'TRANSFERT', 'RETOUR_MACHINE') "
        "AND prix <> 0",
    ),
    "K8b": lambda c: _executer(
        c,
        "reception_ligne.devise",
        "UPDATE reception_ligne l SET devise = f.devise FROM reception r JOIN facture f "
        "ON f.id = r.facture_id WHERE r.id = l.reception_id AND l.devise <> f.devise "
        "AND r.id IN (SELECT reception_id FROM reception_ligne GROUP BY reception_id "
        "HAVING count(DISTINCT devise) > 1)",
    ),
    "K8c": lambda c: _executer(
        c,
        "article.unite_achat",
        "UPDATE article SET unite_achat = 'kg', contenance_achat = 1 "
        "WHERE contenance_achat = 0 AND unite_achat <> 'kg'",
    ),
    "K8d": lambda c: (
        _executer(
            c,
            "reception.numero",
            "UPDATE reception SET numero = NULL WHERE statut = 'brouillon' AND numero IS NOT NULL",
        )
        | _executer(
            c,
            "bon_sortie.numero",
            "UPDATE bon_sortie SET numero = NULL WHERE statut = 'brouillon' AND numero IS NOT NULL",
        )
    ),
    "K8e": lambda c: _executer(
        c,
        "bon_sortie.valide_le",
        "UPDATE bon_sortie SET valide_le = date + "
        "time '23:59:59.999999' WHERE statut = 'valide' AND valide_le IS NULL",
    ),
    "K8f": lambda c: _executer(
        c, "lot.numero", "UPDATE lot SET numero = replace(numero, ' ', '_') WHERE numero LIKE '% %'"
    ),
    "K8g": lambda c: _executer(
        c,
        "mouvement.document_id",
        "UPDATE mouvement m SET document_id = r.id FROM reception r JOIN reception_ligne l "
        "ON l.reception_id = r.id WHERE m.document = 'reception' AND m.document_id IS NULL "
        "AND r.statut = 'validee' AND l.lot_id = m.lot_id AND r.date = m.date_effet",
    ),
    "K8h": lambda c: _executer(
        c,
        "commande_ligne.confirme_le",
        "UPDATE commande_ligne l SET confirme_le = c.cree_le FROM commande c "
        "WHERE c.id = l.commande_id AND l.prix_confirme AND l.confirme_le IS NULL",
    ),
}
"""Les traductions de la reprise, dans l'ordre de la chaîne des routes des documents."""


def traduire(adresse: str, classe: str) -> dict[str, int]:
    """Fait une traduction dans la copie (une transaction) ; rend ce qu'elle a changé."""
    moteur = create_engine(adresse, poolclass=NullPool)
    with moteur.begin() as c:
        comptes = TRADUCTIONS[classe](c)
    moteur.dispose()
    return comptes
