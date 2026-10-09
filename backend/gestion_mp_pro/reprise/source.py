"""La source : base de Gestion MP ouverte en lecture seule, photo cohérente, empreinte (§ 10.1).

- Connexion avec `default_transaction_read_only = on`, puis une seule transaction
  `REPEATABLE READ READ ONLY` : toutes les tables sont lues dans la même photo, aucune écriture
  n'est possible. La lecture seule est **vérifiée par un essai** : une écriture (table
  temporaire) doit être refusée par PostgreSQL (SQLSTATE 25006), sinon la reprise s'arrête.
- Empreinte de la source : par table, nombre de lignes, plus grand `id` et somme de contrôle
  (md5 des lignes en texte, triées) ; l'empreinte globale est le SHA-256 de l'ensemble. Elle est
  relevée dans la photo, puis de nouveau dans une transaction à part après la reprise.
- Le schéma attendu est celui de Gestion MP corrigé (étapes 1 à 19) : une table ou une étape
  manquante arrête la reprise avant toute écriture.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

TABLES_SOURCE: tuple[str, ...] = (
    "article",
    "bon_fabrication",
    "bon_ligne",
    "bon_sortie",
    "code_douanier",
    "commande",
    "commande_ligne",
    "composition",
    "compteur",
    "couleur",
    "devise",
    "dossier",
    "dossier_charge",
    "dossier_charge_part",
    "dossier_ligne",
    "facture",
    "fil_monte",
    "fournisseur",
    "indicateur_jour",
    "inventaire",
    "inventaire_ligne",
    "journal",
    "lot",
    "magasin",
    "metier",
    "mouvement",
    "operation",
    "operation_ligne",
    "parametre",
    "parametre_historique",
    "piece_jointe",
    "poste_frais",
    "qualite",
    "qualite_poids",
    "qualite_saison",
    "reception",
    "reception_ligne",
    "recette",
    "recette_version",
    "reclamation",
    "role_nomenclature",
    "session_ouverte",
    "signalement",
    "solde",
    "tentative",
    "titrage",
    "type_fil",
    "utilisateur",
)
"""Les 48 tables lues (la 49ᵉ, `schema_version`, sert au contrôle du schéma)."""

ETAPE_MINIMALE = 19
"""Gestion MP corrigé : étapes 1 à 19 (la reprise lit les colonnes des étapes 15 à 19)."""

ORDRE_DES_LIGNES: dict[str, str] = {
    "compteur": "serie, annee",
    "dossier_charge_part": "charge_id, ligne_id",
    "indicateur_jour": "jour",
    "parametre": "cle",
    "solde": "lot_id, magasin_id",
    "tentative": "identifiant",
    "session_ouverte": "empreinte",
    "composition": "code",
    "couleur": "code",
    "titrage": "code",
    "type_fil": "code",
    "role_nomenclature": "code",
    "code_douanier": "code",
    "poste_frais": "code",
    "devise": "code",
}
"""Tables sans `id` : l'ordre de lecture (stable d'une photo à l'autre)."""

ECRITURE_REFUSEE = "25006"
"""SQLSTATE `read_only_sql_transaction`."""


class SourceRefusee(Exception):
    """La source ne peut pas être lue (schéma inattendu, lecture seule non garantie)."""


@dataclass
class Photo:
    """Toutes les lignes de la source, lues dans une seule transaction en lecture seule."""

    base: str
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    empreintes: dict[str, str] = field(default_factory=dict)
    lecture_seule_verifiee: bool = False

    @property
    def empreinte(self) -> str:
        """L'empreinte globale de la source (SHA-256 des empreintes par table)."""
        return empreinte_globale(self.empreintes)

    def lignes(self, table: str) -> list[dict[str, Any]]:
        """Les lignes d'une table source (liste vide si la table est vide)."""
        return self.tables.get(table, [])


def empreinte_globale(empreintes: dict[str, str]) -> str:
    """SHA-256 de « table=empreinte » trié : change si une seule ligne change."""
    texte = "\n".join(f"{t}={e}" for t, e in sorted(empreintes.items()))
    return hashlib.sha256(texte.encode()).hexdigest()


def nom_de_base(url: str) -> str:
    """Le nom de la base d'une URL SQLAlchemy."""
    return make_url(url).database or ""


def _connexion(url: str) -> Connection:
    """Une connexion en lecture seule par défaut, au fuseau de l'usine, sans délai maximal."""
    moteur = create_engine(
        url,
        poolclass=NullPool,
        connect_args={"options": "-c default_transaction_read_only=on -c statement_timeout=0"},
    )
    return moteur.connect()


def _verifier_lecture_seule(c: Connection) -> None:
    """Essai d'écriture dans la transaction : PostgreSQL doit le refuser (25006)."""
    c.execute(text("SAVEPOINT essai_ecriture"))
    try:
        c.execute(text("CREATE TEMPORARY TABLE reprise_essai_ecriture (x integer)"))
    except DBAPIError as exc:
        code = getattr(exc.orig, "sqlstate", None)
        c.execute(text("ROLLBACK TO SAVEPOINT essai_ecriture"))
        if code != ECRITURE_REFUSEE:
            raise SourceRefusee(f"essai d'écriture refusé pour une autre raison ({code})") from exc
        return
    raise SourceRefusee("la source accepte une écriture : reprise arrêtée (rien n'est fait)")


def _verifier_schema(c: Connection) -> None:
    """Toutes les tables attendues, et Gestion MP corrigé jusqu'à l'étape 19 au moins."""
    presentes = set(
        c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
    )
    manquantes = sorted({*TABLES_SOURCE, "schema_version"} - presentes)
    if manquantes:
        raise SourceRefusee(f"tables absentes de la source : {', '.join(manquantes)}")
    etape = c.execute(text("SELECT max(numero) FROM schema_version")).scalar() or 0
    if etape < ETAPE_MINIMALE:
        raise SourceRefusee(
            f"la source est à l'étape {etape} de Gestion MP ; la reprise attend l'étape "
            f"{ETAPE_MINIMALE} (Gestion MP corrigé)"
        )


def _empreinte_table(c: Connection, table: str) -> str:
    """« lignes:max(id):md5 » d'une table (lignes en texte, triées)."""
    a_un_id = table not in ORDRE_DES_LIGNES
    maximum = "max(x.id)" if a_un_id else "NULL"
    sql = (
        f"SELECT count(*), {maximum}, "  # noqa: S608 (nom de table de la liste fermée)
        f"md5(coalesce(string_agg(x::text, E'\\n' ORDER BY x::text), '')) FROM {table} x"
    )
    n, plus_grand, somme = c.execute(text(sql)).one()
    return f"{n}:{plus_grand or 0}:{somme}"


def empreintes(c: Connection) -> dict[str, str]:
    """L'empreinte de chaque table lue."""
    return {t: _empreinte_table(c, t) for t in TABLES_SOURCE}


def _lire(c: Connection, table: str) -> list[dict[str, Any]]:
    """Toutes les lignes d'une table, dans un ordre stable."""
    ordre = ORDRE_DES_LIGNES.get(table, "id")
    sql = f"SELECT * FROM {table} ORDER BY {ordre}"  # noqa: S608 (liste fermée)
    return [dict(r) for r in c.execute(text(sql)).mappings()]


def photographier(url: str) -> Photo:
    """Lit toute la source dans une transaction `REPEATABLE READ READ ONLY` vérifiée."""
    photo = Photo(base=nom_de_base(url))
    with _connexion(url) as c:
        c.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        _verifier_lecture_seule(c)
        photo.lecture_seule_verifiee = True
        _verifier_schema(c)
        photo.empreintes = empreintes(c)
        photo.tables = {t: _lire(c, t) for t in TABLES_SOURCE}
        c.rollback()
    return photo


def empreinte_actuelle(url: str) -> str:
    """L'empreinte de la source relue dans une transaction à part (contrôle « avant = après »)."""
    with _connexion(url) as c:
        c.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        valeur = empreinte_globale(empreintes(c))
        c.rollback()
    return valeur
