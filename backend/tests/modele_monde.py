"""Un « monde » minimal et valide : une ligne par table, toutes contraintes respectées (lot S1).

`LIGNES` donne, pour chaque table, les valeurs d'une ligne valide en fonction des identifiants
déjà créés (`ids`) ; `batir(c)` remet la base à l'état d'une installation neuve **dans la
transaction de `c`** (`base_connue.remettre` : les numéros posés à la main — `BC 2026`,
`REC-2026-0001`, `INV-2026-0001`… — ne rencontrent rien de ce que les autres essais ont laissé),
puis les insère dans l'ordre des dépendances et rend `ids`. Les
essais du modèle s'en servent : la ligne valide passe, la même ligne avec **une** valeur
interdite est refusée par **sa** contrainte.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import base_connue
from sqlalchemy import Connection, text

INSTANT = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
JOUR = date(2026, 10, 1)

Ids = dict[str, Any]
Ligne = Callable[[Ids], dict[str, Any]]

SEMEES = {"parametre", "devise", "role_nomenclature", "magasin", "poste_frais", "motif"}
"""Tables dont la ligne valide est une semence (déjà là : pas réinsérée)."""

LIGNES: dict[str, Ligne] = {
    "utilisateur": lambda i: {"identifiant": "essai.modele", "nom": "Essai", "role": "direction"},
    "appareil": lambda i: {"nom": "Téléphone essai", "cree_par_id": i["utilisateur"]},
    "session": lambda i: {
        "empreinte": "a" * 64,
        "utilisateur_id": i["utilisateur"],
        "appareil_id": i["appareil"],
        "expire_le": INSTANT + timedelta(days=1),
    },
    "tentative": lambda i: {"identifiant": "inconnu"},
    "journal": lambda i: {"action": "essai", "objet": "systeme"},
    "parametre": lambda i: {"cle": "dso", "valeur": "60"},
    "parametre_historique": lambda i: {"cle": "dso", "apres": "60"},
    "compteur": lambda i: {"serie": "BC", "annee": 2026},
    "notification": lambda i: {"role": "direction", "texte": "Essai"},
    "notification_lecture": lambda i: {
        "notification_id": i["notification"],
        "utilisateur_id": i["utilisateur"],
    },
    "courriel": lambda i: {"genre": "lundi", "cle": "lundi:2026-10-05"},
    "tache_execution": lambda i: {"nom": "sauvegarde"},
    "sauvegarde": lambda i: {"fichier": "essai.dump", "genre": "manuelle", "base": "essai"},
    "devise": lambda i: {"code": "USD", "nom": "Dollar", "cours": Decimal(10)},
    "devise_cours": lambda i: {"devise": "USD", "cours": Decimal(10)},
    "composition": lambda i: {"code": "PP"},
    "type_fil": lambda i: {"code": "Frisé"},
    "titrage": lambda i: {"code": "2900 Dtex"},
    "couleur": lambda i: {"code": "Rouge"},
    "role_nomenclature": lambda i: {"code": "Nouveau rôle", "ordre": 8},
    "fournisseur": lambda i: {"nom": "Fournisseur essai", "pays": "MAROC"},
    "code_douanier": lambda i: {"code": "5509", "taux_droits": Decimal("0.1")},
    "matiere": lambda i: {
        "reference": "Fil essai",
        "role_id": i["poil"],
        "fournisseur_id": i["fournisseur"],
        "composition_id": i["composition"],
        "code_douanier_id": i["code_douanier"],
        "priorite_equiv": Decimal(50),
    },
    "magasin": lambda i: {"code": "Magasin 2", "type": "stock_courant"},
    "poste_frais": lambda i: {"code": "P2", "nature": "autre"},
    "motif": lambda i: {"type_operation": "ajustement", "libelle": "Essai", "code_r": "R1"},
    "qualite": lambda i: {"code": "Q1", "base_mensuelle": Decimal(100)},
    "qualite_poids": lambda i: {"qualite_id": i["qualite"], "role_id": i["poil"]},
    "qualite_saison": lambda i: {"qualite_id": i["qualite"], "mois": 1},
    "recette": lambda i: {"qualite_id": i["qualite"], "matiere_id": i["matiere"]},
    "recette_version": lambda i: {"qualite_id": i["qualite"], "numero": 1},
    "recette_version_ligne": lambda i: {
        "version_id": i["recette_version"],
        "matiere_id": i["matiere"],
        "role_id": i["poil"],
        "pourcentage": Decimal(100),
    },
    "recette_version_poids": lambda i: {
        "version_id": i["recette_version"],
        "role_id": i["poil"],
        "poids": Decimal(1),
    },
    "plan_version": lambda i: {"qualite_id": i["qualite"]},
    "plan_version_saison": lambda i: {
        "version_id": i["plan_version"],
        "mois": 1,
        "coefficient": Decimal(1),
    },
    "metier": lambda i: {"code": "M1", "etages": 2},
    "metier_etage": lambda i: {"metier_id": i["metier"], "etage": 1},
    "montage": lambda i: {"metier_id": i["metier"], "etage": 1, "matiere_id": i["matiere"]},
    "montage_evenement": lambda i: {"metier_id": i["metier"], "etage": 1},
    "lot": lambda i: {"matiere_id": i["matiere"], "numero": "L1", "entre_le": JOUR},
    "solde": lambda i: {"lot_id": i["lot"], "magasin_id": i["courant"], "quantite": 10},
    "commande": lambda i: {
        "fournisseur_id": i["fournisseur"],
        "date_commande": JOUR,
        "devise": "USD",
    },
    "commande_ligne": lambda i: {
        "commande_id": i["commande"],
        "matiere_id": i["matiere"],
        "quantite": Decimal(100),
    },
    "commande_version": lambda i: {"commande_id": i["commande"], "motif": "envoi"},
    "commande_version_ligne": lambda i: {
        "version_id": i["commande_version"],
        "matiere_id": i["matiere"],
        "quantite": Decimal(100),
    },
    "commande_decision": lambda i: {"commande_id": i["commande"], "decision": "approbation"},
    "facture": lambda i: {"fournisseur_id": i["fournisseur"], "numero": "F1", "devise": "USD"},
    "reception": lambda i: {
        "numero": "REC-2026-0001",
        "statut": "validee",
        "validee_le": INSTANT,
        "date": JOUR,
        "fournisseur_id": i["fournisseur"],
        "devise": "USD",
    },
    "reception_ligne": lambda i: {
        "reception_id": i["reception"],
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "magasin_id": i["courant"],
        "quantite_pesee": Decimal(10),
    },
    "ordre": lambda i: {"date": JOUR, "magasin_id": i["courant"]},
    "ordre_qualite": lambda i: {"ordre_id": i["ordre"], "qualite_id": i["qualite"], "m2": 10},
    "ordre_ligne": lambda i: {
        "ordre_id": i["ordre"],
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "quantite": Decimal(5),
    },
    "ordre_prevu": lambda i: {
        "ordre_id": i["ordre"],
        "matiere_id": i["matiere"],
        "kg_hors_perte": Decimal(5),
    },
    "operation": lambda i: {"type": "ajustement", "date": JOUR},
    "operation_ligne": lambda i: {
        "operation_id": i["operation"],
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "magasin_id": i["courant"],
        "quantite": Decimal(1),
    },
    "inventaire": lambda i: {"numero": "INV-2026-0001", "date": JOUR, "magasin_id": i["courant"]},
    "inventaire_critere": lambda i: {
        "inventaire_id": i["inventaire"],
        "genre": "matiere",
        "matiere_id": i["matiere"],
    },
    "inventaire_matiere": lambda i: {"inventaire_id": i["inventaire"], "matiere_id": i["matiere"]},
    "inventaire_ligne": lambda i: {
        "inventaire_id": i["inventaire"],
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "magasin_id": i["courant"],
    },
    "dossier": lambda i: {"numero": "1/26", "annee": 2026, "rang": 1},
    "dossier_facture": lambda i: {"dossier_id": i["dossier"], "facture_id": i["facture"]},
    "dossier_ligne": lambda i: {
        "dossier_id": i["dossier"],
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "devise": "USD",
        "cours": Decimal(10),
        "cours_origine": "bon",
    },
    "dossier_frais": lambda i: {
        "dossier_id": i["dossier"],
        "poste_id": i["dd"],
        "montant": Decimal(100),
        "ligne_id": i["dossier_ligne"],
    },
    "dossier_frais_part": lambda i: {
        "frais_id": i["dossier_frais"],
        "ligne_id": i["dossier_ligne"],
        "montant": Decimal(100),
        "origine": "changement_cle",
    },
    "reclamation": lambda i: {
        "numero": "RCL-2026-0001",
        "fournisseur_id": i["fournisseur"],
        "reception_id": i["reception"],
        "reception_ligne_id": i["reception_ligne"],
        "motif": "qualite",
        "ouverte_le": JOUR,
    },
    "signalement": lambda i: {"texte": "Il manque du rouge"},
    "piece_jointe": lambda i: {
        "objet": "matiere",
        "matiere_id": i["matiere"],
        "nom": "photo.jpg",
        "type_mime": "image/jpeg",
        "taille": 10,
        "empreinte": "b" * 64,
        "chemin": "matiere/1/photo.jpg",
    },
    "indicateur_jour": lambda i: {"jour": JOUR},
    "mouvement": lambda i: {
        "date_effet": JOUR,
        "type": "RECEPTION",
        "matiere_id": i["matiere"],
        "lot_id": i["lot"],
        "magasin_id": i["courant"],
        "quantite": Decimal(10),
        "document": "reception",
        "reception_id": i["reception"],
    },
    "reprise_correspondance": lambda i: {
        "source": "gestion_mp",
        "table_source": "article",
        "id_source": 1,
        "table_cible": "matiere",
        "id_cible": i["matiere"],
        "empreinte": "c" * 64,
    },
    "reprise_execution": lambda i: {
        "source": "gestion_mp",
        "base_source": "gestion_mp",
        "mode": "tout",
    },
}


def inserer(c: Connection, table: str, valeurs: dict[str, Any]) -> Any:
    """Insère une ligne ; rend sa clé `id` si la table en a une."""
    colonnes = ", ".join(valeurs)
    marques = ", ".join(f":{k}" for k in valeurs)
    retour = " RETURNING id" if _a_un_id(c, table) else ""
    sql = f"INSERT INTO {table} ({colonnes}) VALUES ({marques}){retour}"  # noqa: S608
    resultat = c.execute(text(sql), valeurs)
    return resultat.scalar() if retour else None


def _a_un_id(c: Connection, table: str) -> bool:
    """La table a-t-elle une colonne `id` ?"""
    return bool(
        c.execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'"
                " AND table_name = :t AND column_name = 'id'"
            ),
            {"t": table},
        ).scalar()
    )


def _semences(c: Connection) -> Ids:
    """Les identifiants des semences dont le monde a besoin."""

    def un(sql: str) -> Any:
        return c.execute(text(sql)).scalar_one()

    return {
        "poil": un("SELECT id FROM role_nomenclature WHERE code = 'Poil'"),
        "cuir": un("SELECT id FROM role_nomenclature WHERE code = 'Cuir'"),
        "courant": un("SELECT id FROM magasin WHERE type = 'stock_courant' ORDER BY id LIMIT 1"),
        "quarantaine": un("SELECT id FROM magasin WHERE type = 'quarantaine' ORDER BY id LIMIT 1"),
        "dd": un("SELECT id FROM poste_frais WHERE code = 'DD'"),
    }


def batir(c: Connection) -> Ids:
    """Base neuve (dans la transaction), puis une ligne valide dans chaque table (dans l'ordre de
    `LIGNES`) ; rend les ids."""
    base_connue.remettre(c)
    ids = _semences(c)
    for table, ligne in LIGNES.items():
        if table not in SEMEES:
            ids[table] = inserer(c, table, ligne(ids))
    return ids
