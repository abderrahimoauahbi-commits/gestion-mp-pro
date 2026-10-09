"""Personnes : les comptes de Gestion MP, et les noms de l'activité rapprochés des comptes.

- Un compte de Gestion MP devient un compte PRO (rapproché par identifiant, en minuscules).
  Son empreinte de code est gardée si son format est celui de PRO (`scrypt$sel$hash`, mêmes
  paramètres : le même code ouvre PRO) ; sinon le code est **à redonner** (empreinte vide :
  personne ne peut se connecter avec) et c'est signalé. Un compte de l'alimentation est
  signalé : PRO exige exactement 4 chiffres, ce que l'empreinte ne permet pas de vérifier.
- Un nom écrit dans l'activité (« cree_par », « auteur », « par »…) est rapproché des comptes
  par `lower(trim(nom))`, sur le nom affiché puis sur l'identifiant ; un nom inconnu crée un
  compte **historique** (inactif, sans rôle, ne se connecte jamais). « système »,
  « installation », « reprise ERP Fil » (et les marques d'import) ne désignent personne : NULL.
  Deux graphies d'un même nom (« Mohamed », « MOHAMED ») vont au même compte : c'est dit au
  rapport ; deux comptes qui répondent au même nom aussi (le premier est retenu).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import select

from gestion_mp_pro.modeles import Utilisateur
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.reprise import ecriture
from gestion_mp_pro.reprise.contexte import Contexte, Ligne, ident_de_code

SANS_PERSONNE = frozenset(
    {
        "",
        "système",
        "systeme",
        "installation",
        "reprise erp fil",
        "erp fil",
        "premier démarrage",
        "relevé à la mise à jour",
        "papier à en-tête (prototype.doc)",
    }
)
"""Noms qui ne désignent personne : geste du système, de l'installation, d'un import, d'un
relevé fait par une mise à jour de Gestion MP, ou valeurs tirées d'un document (le papier à
en-tête de l'usine)."""

EMPREINTE_PRO = re.compile(r"scrypt\$[0-9a-f]{32}\$[0-9a-f]{64}")
"""Format des empreintes de PRO et de Gestion MP corrigé (n = 2¹⁴, r = 8, p = 1, 32 octets)."""

COLONNES_DE_NOMS: dict[str, tuple[str, ...]] = {
    "article": ("modifie_par",),
    "commande": ("cree_par", "approuvee_par"),
    "commande_ligne": ("confirme_par",),
    "bon_sortie": ("cree_par", "valide_par"),
    "inventaire": ("cree_par", "valide_par"),
    "inventaire_ligne": ("second_par",),
    "journal": ("utilisateur",),
    "mouvement": ("auteur",),
    "operation": ("cree_par", "validee_par"),
    "parametre": ("modifie_par",),
    "parametre_historique": ("par",),
    "piece_jointe": ("par",),
    "reception": ("cree_par", "validee_par"),
    "recette_version": ("par",),
    "reclamation": ("cree_par",),
    "signalement": ("par", "traite_par"),
}
"""Colonnes de la source qui citent une personne par son nom."""

PREFIXE_HISTORIQUE = "historique-"


def cle(nom: str | None) -> str:
    """La clé de rapprochement d'un nom : minuscules, blancs retirés aux bords."""
    return (nom or "").strip().lower()


def _identifiant_historique(nom: str, pris: set[str]) -> str:
    """`historique-mohamed` : identifiant (minuscules, sans blanc) d'un compte historique."""
    base = re.sub(r"[^a-z0-9]+", "-", normaliser(nom)).strip("-") or "inconnu"
    candidat = (PREFIXE_HISTORIQUE + base)[:40]
    rang = 2
    while candidat in pris:
        suffixe = f"-{rang}"
        candidat = (PREFIXE_HISTORIQUE + base)[: 40 - len(suffixe)] + suffixe
        rang += 1
    return candidat


def _comptes_de_la_source(ctx: Contexte) -> list[Ligne]:
    """Les comptes de Gestion MP, en lignes de `utilisateur`."""
    lignes = []
    for u in ctx.photo.lignes("utilisateur"):
        identifiant = u["identifiant"].strip().lower()
        if identifiant != u["identifiant"]:
            ctx.signaler("utilisateur", u["id"], "identifiant mis en minuscules")
        empreinte = u["empreinte"] or ""
        if not EMPREINTE_PRO.fullmatch(empreinte):
            ctx.signaler(
                "utilisateur", identifiant, "code à redonner (empreinte d'un autre format)"
            )
            empreinte = ""
        if u["role"] == "alimentation":
            ctx.signaler(
                "utilisateur", identifiant, "alimentation : PRO exige un code de 4 chiffres"
            )
        valeurs = {
            "identifiant": identifiant,
            "nom": u["nom"],
            "role": u["role"],
            "email": u["email"] or "",
            "empreinte_code": empreinte,
            "actif": u["actif"],
            "historique": False,
            "cree_le": u["cree_le"],
            "vu_le": u["vu_le"],
        }
        lignes.append(
            Ligne(
                (identifiant,), ctx.ligne("utilisateur", valeurs, u["id"]), "utilisateur", u["id"]
            )
        )
    return lignes


def noms_cites(ctx: Contexte) -> dict[str, list[str]]:
    """Clé → graphies rencontrées dans l'activité (ordre d'apparition)."""
    graphies: dict[str, list[str]] = defaultdict(list)
    for table, colonnes in COLONNES_DE_NOMS.items():
        for x in ctx.photo.lignes(table):
            for col in colonnes:
                nom = (x.get(col) or "").strip()
                k = cle(nom)
                if k not in SANS_PERSONNE and nom not in graphies[k]:
                    graphies[k].append(nom)
    return graphies


def _index(ctx: Contexte) -> dict[str, list[int]]:
    """Clé → comptes de la cible qui répondent à ce nom (nom affiché, puis identifiant)."""
    index: dict[str, list[int]] = defaultdict(list)
    comptes = ctx.c.execute(
        select(Utilisateur.id, Utilisateur.nom, Utilisateur.identifiant).order_by(Utilisateur.id)
    ).all()
    for uid, nom, _ in comptes:
        index[cle(nom)].append(uid)
    for uid, _, identifiant in comptes:
        if uid not in index[cle(identifiant)]:
            index[cle(identifiant)].append(uid)
    return index


def reprendre(ctx: Contexte) -> dict[str, int]:
    """Comptes repris, comptes historiques créés ; rend la table « clé du nom → id »."""
    ecriture.appliquer(ctx, "utilisateur", _comptes_de_la_source(ctx), ("identifiant",))
    graphies = noms_cites(ctx)
    index = _index(ctx)
    pris = {r for (r,) in ctx.c.execute(select(Utilisateur.identifiant))}
    historiques = []
    for k, noms in sorted(graphies.items()):
        if index.get(k):
            continue
        identifiant = _identifiant_historique(noms[0], pris)
        pris.add(identifiant)
        valeurs: dict[str, Any] = {
            "identifiant": identifiant,
            "nom": noms[0],
            "role": None,
            "actif": False,
            "historique": True,
        }
        historiques.append(
            Ligne((identifiant,), ctx.ligne("utilisateur", valeurs, k), "nom", ident_de_code(k))
        )
    ecriture.appliquer(ctx, "utilisateur", historiques, ("identifiant",))
    index = _index(ctx)
    for k, noms in sorted(graphies.items()):
        if len(noms) > 1:
            ctx.norm.signaler("utilisateur", k, f"graphies {', '.join(noms)} → un même compte")
        if len(index[k]) > 1:
            ctx.norm.signaler("utilisateur", k, f"{len(index[k])} comptes pour ce nom : le premier")
    return {k: ids[0] for k, ids in index.items() if ids}


def ids_des_comptes_sources(ctx: Contexte, noms: dict[str, int]) -> dict[int, int]:
    """id d'un compte de Gestion MP → id du compte PRO (pour `signalement.par_id`)."""
    return {
        u["id"]: noms[cle(u["identifiant"])]
        for u in ctx.photo.lignes("utilisateur")
        if cle(u["identifiant"]) in noms
    }
