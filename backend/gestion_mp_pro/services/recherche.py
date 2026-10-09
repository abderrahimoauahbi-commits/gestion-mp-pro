"""Recherche sans accents et recherche globale filtrée par rôle (ARCHITECTURE A6 ; route 56).

`normaliser` est la règle unique de l'écran et du serveur (NFD, retrait U+0300–U+036F,
minuscules, blancs réduits) : c'est celle de `modeles.recherche`, qui tient `texte_recherche`.
« Tous les mots, dans n'importe quel ordre » : `conditions(colonne, q)` rend un `LIKE` par mot,
`%` et `_` échappés (chercher « % » ne ramène pas tout). Pour une colonne sans
`texte_recherche`, `sans_accents_sql(colonne)` normalise côté base (`translate`).

La recherche globale est **extensible par domaine** : `@source("matieres", roles)` déclare
une fonction de recherche ; S2 déclare les huit genres de l'en-tête (matières, lots,
commandes, réceptions, dossiers, fournisseurs, qualités, ordres). Un genre n'est cherché que
pour les rôles qui ont le droit d'ouvrir sa fiche ; aucun prix n'y figure.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import QueryableAttribute, Session

from gestion_mp_pro.modeles import (
    Commande,
    Dossier,
    Fournisseur,
    Lot,
    Matiere,
    Ordre,
    Qualite,
    Reception,
)
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.modeles.recherche import normaliser

__all__ = ["normaliser"]

MOTS_MAX = 6
"""Au-delà, les mots sont ignorés (héritage K51)."""

PAR_GENRE = 8
"""Résultats rendus par genre dans la recherche globale."""

ACCENTUES = "àâäáãåéèêëíìîïóòôöõúùûüçñÿ"
SANS_ACCENT = "aaaaaaeeeeiiiiooooouuuucny"
"""`translate` de PostgreSQL : même effet que `normaliser` sur les lettres de l'usine."""

Colonne = ColumnElement[str] | QueryableAttribute[str]
"""Une colonne texte (attribut d'un modèle ou expression)."""

C = frozenset({Role.direction, Role.achats, Role.alimentation})
DA = frozenset({Role.direction, Role.achats})


_PONCTUATION = re.compile(r"[^0-9a-z]+")


def compacter(texte: str) -> str:
    """« FA-2026/117 » → « fa2026117 » : normalisé, sans blancs ni ponctuation."""
    return _PONCTUATION.sub("", normaliser(texte))


def trouve(q: str, *champs: str | None) -> bool:
    """Chaque mot de `q` est dans les champs (sans accents), ou y est à la ponctuation près :
    « FA-2026/117 » trouve « FA-2026-117 » (un numéro de pièce s'écrit de plusieurs façons ;
    RESTES3, F5)."""
    texte = normaliser(" ".join(c for c in champs if c))
    compact = compacter(texte)
    for mot in normaliser(q).split():
        if mot in texte:
            continue
        serre = compacter(mot)
        if not serre or serre not in compact:
            return False
    return True


def mots(q: str) -> list[str]:
    """Les mots cherchés, normalisés (6 au plus)."""
    return normaliser(q).split()[:MOTS_MAX]


def echapper(mot: str) -> str:
    """`%`, `_` et `\\` deviennent littéraux dans un `LIKE … ESCAPE '\\'`."""
    return mot.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def sans_accents_sql(colonne: Colonne) -> ColumnElement[str]:
    """La colonne en minuscules sans accents, côté base."""
    return func.translate(func.lower(colonne), ACCENTUES, SANS_ACCENT)


def compacter_sql(colonne: ColumnElement[str]) -> ColumnElement[str]:
    """La colonne sans accents, sans blancs ni ponctuation (comme `compacter`, côté base)."""
    return func.regexp_replace(colonne, "[^0-9a-z]+", "", "g")


def conditions(colonne: Colonne, q: str) -> list[ColumnElement[bool]]:
    """Un `LIKE '%mot%'` par mot (tous exigés) ; `colonne` déjà normalisée."""
    return [colonne.like(f"%{echapper(m)}%", escape="\\") for m in mots(q)]


def conditions_tolerantes(colonne: Colonne, q: str) -> list[ColumnElement[bool]]:
    """Comme `conditions`, mais chaque mot est trouvé soit dans la colonne, soit à la ponctuation
    près (« FA-2026/117 » trouve « FA-2026-117 »), à l'identique de `trouve`. `colonne` est le texte
    brut (la normalisation est faite ici)."""
    sans = sans_accents_sql(colonne)
    serre = compacter_sql(sans)
    conds: list[ColumnElement[bool]] = []
    for m in mots(q):
        plein = sans.like(f"%{echapper(m)}%", escape="\\")
        compact = compacter(m)
        conds.append(
            plein if not compact else (plein | serre.like(f"%{echapper(compact)}%", escape="\\"))
        )
    return conds


@dataclass(frozen=True)
class Resultat:
    """Un résultat de la recherche globale : ce que l'en-tête affiche et l'adresse à ouvrir."""

    genre: str
    id: int
    titre: str
    sous_titre: str
    lien: str


Chercheur = Callable[[Session, str, int], list[Resultat]]


@dataclass(frozen=True)
class Source:
    """Un genre cherché : les rôles qui peuvent ouvrir ses fiches, et sa fonction."""

    genre: str
    roles: frozenset[str]
    chercher: Chercheur


SOURCES: dict[str, Source] = {}
"""Les genres de la recherche globale, dans l'ordre d'affichage."""


def source(genre: str, roles: frozenset[str]) -> Callable[[Chercheur], Chercheur]:
    """Déclare (ou remplace) la recherche d'un genre ; un domaine peut affiner la sienne."""

    def declarer(fonction: Chercheur) -> Chercheur:
        """Enregistre la fonction de recherche du genre."""
        SOURCES[genre] = Source(genre, frozenset(roles), fonction)
        return fonction

    return declarer


def rechercher(s: Session, role: str, q: str, par_genre: int = PAR_GENRE) -> list[Resultat]:
    """Les résultats de tous les genres permis au rôle (rien si aucun mot)."""
    if not mots(q):
        return []
    trouves: list[Resultat] = []
    for src in SOURCES.values():
        if role in src.roles:
            trouves += src.chercher(s, q, par_genre)
    return trouves


def _filtre(colonne: Colonne, q: str) -> Sequence[ColumnElement[bool]]:
    """Les conditions sur un `texte_recherche`."""
    return conditions(colonne, q)


@source("matieres", C)
def _matieres(s: Session, q: str, n: int) -> list[Resultat]:
    """Matières : référence, désignation (catalogue lisible par les trois rôles)."""
    requete = select(Matiere).where(*_filtre(Matiere.texte_recherche, q))
    lignes = s.scalars(requete.order_by(Matiere.reference).limit(n))
    return [
        Resultat("matiere", m.id, m.reference, m.designation, f"/matieres/{m.id}") for m in lignes
    ]


@source("lots", C)
def _lots(s: Session, q: str, n: int) -> list[Resultat]:
    """Lots : numéro, matière."""
    requete = (
        select(Lot.id, Lot.numero, Matiere.reference)
        .join(Matiere, Matiere.id == Lot.matiere_id)
        .where(*_filtre(Lot.texte_recherche, q))
        .order_by(Lot.id.desc())
        .limit(n)
    )
    return [Resultat("lot", i, num, ref, f"/lots/{i}") for i, num, ref in s.execute(requete)]


@source("ordres", C)
def _ordres(s: Session, q: str, n: int) -> list[Resultat]:
    """Ordres de fabrication : numéro (ou brouillon), date."""
    requete = select(Ordre).where(*_filtre(Ordre.texte_recherche, q))
    lignes = s.scalars(requete.order_by(Ordre.id.desc()).limit(n))
    return [
        Resultat("ordre", o.id, o.numero or f"brouillon n° {o.id}", f"{o.date:%d/%m/%Y}",
                 f"/ordres/{o.id}")
        for o in lignes
    ]  # fmt: skip


@source("qualites", C)
def _qualites(s: Session, q: str, n: int) -> list[Resultat]:
    """Qualités : code, nom."""
    requete = select(Qualite).where(*_filtre(Qualite.texte_recherche, q))
    lignes = s.scalars(requete.order_by(Qualite.code).limit(n))
    return [Resultat("qualite", x.id, x.code, x.nom, f"/qualites/{x.id}") for x in lignes]


@source("commandes", DA)
def _commandes(s: Session, q: str, n: int) -> list[Resultat]:
    """Bons de commande : numéro (ou brouillon), fournisseur."""
    requete = (
        select(Commande.id, Commande.numero, Fournisseur.nom)
        .join(Fournisseur, Fournisseur.id == Commande.fournisseur_id)
        .where(*_filtre(Commande.texte_recherche, q))
        .order_by(Commande.id.desc())
        .limit(n)
    )
    return [
        Resultat("commande", i, num or f"BC-brouillon-{i}", nom, f"/commandes/{i}")
        for i, num, nom in s.execute(requete)
    ]


@source("receptions", DA)
def _receptions(s: Session, q: str, n: int) -> list[Resultat]:
    """Réceptions : numéro (ou brouillon), fournisseur."""
    requete = (
        select(Reception.id, Reception.numero, Fournisseur.nom)
        .join(Fournisseur, Fournisseur.id == Reception.fournisseur_id)
        .where(*_filtre(Reception.texte_recherche, q))
        .order_by(Reception.id.desc())
        .limit(n)
    )
    return [
        Resultat("reception", i, num or f"REC-brouillon-{i}", nom, f"/receptions/{i}")
        for i, num, nom in s.execute(requete)
    ]


@source("dossiers", DA)
def _dossiers(s: Session, q: str, n: int) -> list[Resultat]:
    """Dossiers d'importation : numéro, libellé."""
    requete = select(Dossier).where(*_filtre(Dossier.texte_recherche, q))
    lignes = s.scalars(requete.order_by(Dossier.id.desc()).limit(n))
    return [Resultat("dossier", d.id, d.numero, d.libelle, f"/dossiers/{d.id}") for d in lignes]


@source("fournisseurs", DA)
def _fournisseurs(s: Session, q: str, n: int) -> list[Resultat]:
    """Fournisseurs : nom, pays (la fiche est réservée à la direction et aux achats)."""
    requete = select(Fournisseur).where(*_filtre(Fournisseur.texte_recherche, q))
    lignes = s.scalars(requete.order_by(Fournisseur.nom).limit(n))
    return [Resultat("fournisseur", f.id, f.nom, f.pays, f"/fournisseurs/{f.id}") for f in lignes]
