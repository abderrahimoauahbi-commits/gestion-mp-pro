"""Les données brutes d'une table métier (route 7), pour la vérification indépendante (V1).

Le vérificateur ne lit jamais le paquet : il lit ces lignes telles qu'elles sont en base, puis
recalcule avec les formules de la documentation. Liste **fermée** de tables (aucun compte,
aucune session, aucun secret, rien du journal) ; colonnes techniques de recherche retirées.
`?date=` : les tables datées ne rendent que ce qui existait ce soir-là (mouvements à leur date
d'effet, documents à leur date).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import Table, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Base

TABLES = (
    "matiere",
    "fournisseur",
    "devise",
    "devise_cours",
    "magasin",
    "role_nomenclature",
    "composition",
    "type_fil",
    "titrage",
    "couleur",
    "code_douanier",
    "poste_frais",
    "motif",
    "parametre",
    "lot",
    "solde",
    "mouvement",
    "commande",
    "commande_ligne",
    "facture",
    "reception",
    "reception_ligne",
    "dossier",
    "dossier_facture",
    "dossier_ligne",
    "dossier_frais",
    "dossier_frais_part",
    "ordre",
    "ordre_qualite",
    "ordre_ligne",
    "ordre_prevu",
    "operation",
    "operation_ligne",
    "qualite",
    "qualite_poids",
    "qualite_saison",
    "recette",
    "recette_version",
    "recette_version_ligne",
    "recette_version_poids",
    "plan_version",
    "plan_version_saison",
    "metier",
    "metier_etage",
    "montage",
    "montage_evenement",
    "inventaire",
    "inventaire_ligne",
    "inventaire_matiere",
    "inventaire_critere",
    "reclamation",
    "indicateur_jour",
    "parametre_historique",
    "commande_version",
    "commande_version_ligne",
    "commande_decision",
)
"""Les tables lisibles (liste fermée : toute autre → 404)."""
DATEES = {
    "mouvement": "date_effet",
    "commande": "date_commande",
    "reception": "date",
    "ordre": "date",
    "operation": "date",
    "inventaire": "date",
    "facture": "date",
    "indicateur_jour": "jour",
}
"""La colonne qui date une ligne, pour `?date=`."""
RETIREES = frozenset({"texte_recherche"})


@dataclass
class DonneesBrutes:
    """Les lignes d'une table, colonne par colonne."""

    table: str
    date_reference: date | None
    colonnes: list[str]
    lignes: list[dict[str, Any]]


def _valeur(v: object) -> object:
    """Une valeur JSON : nombres pour les décimaux, ISO pour les dates, texte des énumérations."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Enum):
        return v.value
    return v


def lire(s: Session, table: str, jour: date | None) -> DonneesBrutes:
    """Les lignes de `table` (par clé primaire), au soir de `jour` s'il est donné."""
    if table not in TABLES:
        raise Refus.introuvable(f"Table inconnue ou non lisible : « {table} ».")
    t: Table = Base.metadata.tables[table]
    colonnes = [c for c in t.columns if c.name not in RETIREES]
    requete = select(*colonnes).order_by(*t.primary_key.columns)
    if jour is not None and table in DATEES:
        requete = requete.where(t.columns[DATEES[table]] <= jour)
    noms = [c.name for c in colonnes]
    lignes = [
        {n: _valeur(v) for n, v in zip(noms, rangee, strict=True)} for rangee in s.execute(requete)
    ]
    return DonneesBrutes(table=table, date_reference=jour, colonnes=noms, lignes=lignes)
