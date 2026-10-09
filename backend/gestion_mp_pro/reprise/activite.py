"""L'activité : construite en entier depuis la photo, puis écrite d'un bloc (§ 10, § 14.2).

L'activité n'est jamais mise à jour ligne à ligne : elle est **remplacée** entière, avec les
identifiants et les numéros de Gestion MP. Avant d'écrire :

- l'empreinte de chaque table construite est comparée à celle de la dernière reprise réussie :
  identiques, et la cible inchangée depuis → **rien n'est écrit** (rejouée sans changement) ;
- la cible a une activité que la dernière reprise n'a pas écrite (saisie dans PRO, ou base
  d'une autre origine) → **refus**, sauf `--remplacer-activite` (sauvegarde faite avant) ;
- sinon l'activité de la cible (miroir intact) est vidée (`vidage.vider`) et réécrite.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from sqlalchemy import text

from gestion_mp_pro.modeles import metadata, tables_d_activite
from gestion_mp_pro.reprise import (
    activite_achats,
    activite_importations,
    activite_production,
    activite_stock,
    compteurs,
    ecriture,
    pieces,
    vidage,
)
from gestion_mp_pro.reprise import journal_en_tables as jt
from gestion_mp_pro.reprise.contexte import Contexte
from gestion_mp_pro.reprise.normalisation import empreinte, empreinte_lignes
from gestion_mp_pro.reprise.outils import Lignes

ORDRE = (
    "lot",
    "facture",
    "commande",
    "commande_ligne",
    "commande_version",
    "commande_decision",
    "reception",
    "reception_ligne",
    "ordre",
    "ordre_qualite",
    "ordre_ligne",
    "ordre_prevu",
    "operation",
    "operation_ligne",
    "inventaire",
    "inventaire_ligne",
    "inventaire_matiere",
    "mouvement",
    "solde",
    "dossier",
    "dossier_ligne",
    "dossier_frais",
    "dossier_frais_part",
    "reclamation",
    "signalement",
    "indicateur_jour",
    "compteur",
    "piece_jointe",
)
"""Ordre d'écriture (clés étrangères)."""

SOURCES = {
    "lot": "lot",
    "facture": "facture",
    "commande": "commande",
    "commande_ligne": "commande_ligne",
    "reception": "reception",
    "reception_ligne": "reception_ligne",
    "ordre": "bon_sortie",
    "ordre_qualite": "bon_fabrication",
    "ordre_ligne": "bon_ligne",
    "operation": "operation",
    "operation_ligne": "operation_ligne",
    "inventaire": "inventaire",
    "inventaire_ligne": "inventaire_ligne",
    "mouvement": "mouvement",
    "dossier": "dossier",
    "dossier_ligne": "dossier_ligne",
    "dossier_frais": "dossier_charge",
    "reclamation": "reclamation",
    "signalement": "signalement",
    "piece_jointe": "piece_jointe",
}
"""Table PRO → table source (correspondances ligne à ligne, identifiants gardés)."""

GENRES_ACTIVITE = frozenset({"commande", "reception", "dossier", "reclamation", "inventaire"})


class ActiviteRefusee(Exception):
    """La cible a une activité que la reprise n'a pas écrite : refus sans --remplacer-activite."""


def construire(ctx: Contexte, j: jt.Journal, comptes_sources: dict[int, int]) -> Lignes:
    """Toutes les lignes de l'activité, table par table, normalisées."""
    sortie: Lignes = defaultdict(list)
    activite_stock.lots(ctx, sortie)
    activite_achats.factures(ctx, sortie)
    activite_achats.commandes(ctx, j, sortie)
    activite_achats.receptions(ctx, j, sortie)
    activite_production.ordres(ctx, j, sortie)
    activite_production.operations(ctx, j, sortie)
    activite_stock.inventaires(ctx, j, sortie)
    activite_stock.mouvements(ctx, sortie)
    activite_importations.dossiers(ctx, j, sortie)
    activite_achats.reclamations(ctx, sortie)
    activite_production.signalements(ctx, comptes_sources, sortie)
    activite_production.indicateurs(ctx, sortie)
    sortie["compteur"] = compteurs.compteurs(ctx, sortie)
    sortie["piece_jointe"] = pieces.pieces(ctx, GENRES_ACTIVITE)
    return sortie


def empreinte_cible(ctx: Contexte) -> str:
    """Empreinte de l'activité de la cible (sans `texte_recherche`, tenu par PRO)."""
    morceaux = []
    for nom in [*tables_d_activite(), "piece_jointe"]:
        colonnes = [c.name for c in metadata.tables[nom].columns if c.name != "texte_recherche"]
        liste = ", ".join(f"x.{c}" for c in colonnes)
        filtre = " WHERE x.objet NOT IN ('fournisseur', 'matiere')" if nom == "piece_jointe" else ""
        sql = (
            f"SELECT md5(coalesce(string_agg(t::text, E'\\n' ORDER BY t::text), '')) "  # noqa: S608
            f"FROM (SELECT ROW({liste}) AS t FROM {nom} x{filtre}) y"
        )
        morceaux.append(f"{nom}={ctx.c.execute(text(sql)).scalar()}")
    return hashlib.sha256("\n".join(morceaux).encode()).hexdigest()


def _vide(ctx: Contexte) -> bool:
    """Vrai si la cible n'a aucune activité (ni pièce d'un document)."""
    for nom in tables_d_activite():
        if ctx.c.execute(text(f"SELECT EXISTS (SELECT 1 FROM {nom})")).scalar():  # noqa: S608
            return False
    sql = "SELECT EXISTS (SELECT 1 FROM piece_jointe WHERE objet NOT IN ('fournisseur', 'matiere'))"
    return not ctx.c.execute(text(sql)).scalar()


def empreintes_des_tables(lignes: Lignes) -> dict[str, str]:
    """Empreinte de chaque table construite."""
    return {nom: empreinte_lignes(lignes.get(nom, [])) for nom in ORDRE}


def decider(ctx: Contexte, construites: dict[str, str], derniere: dict[str, Any] | None) -> str:
    """« sauter », « ecrire » ou « remplacer » l'activité ; lève `ActiviteRefusee`."""
    if _vide(ctx):
        return "ecrire"
    intacte = derniere is not None and derniere.get("cible") == empreinte_cible(ctx)
    if intacte and derniere is not None:
        return "sauter" if derniere.get("tables") == construites else "remplacer"
    if ctx.options.remplacer_activite:
        return "remplacer"
    raise ActiviteRefusee(
        "La base cible contient une activité qui ne vient pas de la dernière reprise (saisie "
        "dans PRO, ou reprise d'une autre source) : rien n'est fait. Relancer avec "
        "--remplacer-activite pour la remplacer (une sauvegarde est faite avant)."
    )


def ecrire(ctx: Contexte, lignes: Lignes, remplacer: bool) -> None:
    """Vide (au besoin) puis écrit toute l'activité et ses correspondances."""
    if remplacer:
        retirees = vidage.vider(ctx.c)
        for nom, n in retirees.items():
            ctx.compter(nom, "supprimees", n)
    for nom in ORDRE:
        if nom == "commande_version":
            _versions(ctx, lignes[nom])
        else:
            ecriture.inserer(ctx, nom, lignes.get(nom, []))
    ecriture.oublier(ctx, set(SOURCES.values()) - {"piece_jointe"})
    notes = [
        (SOURCES[nom], int(v["id"]), nom, int(v["id"]), empreinte(v))
        for nom in ORDRE
        if nom in SOURCES and nom != "piece_jointe"
        for v in lignes.get(nom, [])
    ]
    notes += [
        ("piece_jointe", int(v["id"]), "piece_jointe", int(v["id"]), empreinte(v))
        for v in lignes.get("piece_jointe", [])
    ]
    ecriture.noter(ctx, notes)
    for nom in ORDRE:
        ctx.compter(nom, "lues", len(lignes.get(nom, [])))


def _versions(ctx: Contexte, versions: list[dict[str, Any]]) -> None:
    """Versions parties des bons (identifiant de la séquence) et leurs lignes."""
    ids = ecriture.prochains_ids(ctx, "commande_version", len(versions))
    entetes, lignes = [], []
    for v, i in zip(versions, ids, strict=True):
        entetes.append({k: x for k, x in v.items() if k != "_lignes"} | {"id": i})
        lignes += [x | {"version_id": i} for x in v["_lignes"]]
    ecriture.inserer(ctx, "commande_version", entetes)
    ecriture.inserer(ctx, "commande_version_ligne", lignes)
