"""Analyse du coût de revient des matières importées, par axe et par critères (CALCULS B § 9.12).

Portage de la partie calcul de `gestion_mp/api/analyse_import.py` (`AXES`, `STATUTS`,
`CRITERES_COMBINABLES`, `_combinaisons`, `_sans_accents`, `_valeur_critere`,
`analyse_revient`). Les refus de la route (400, 422) deviennent `ValueError` au même message,
la qualité inconnue (404) `QualiteInconnue`. Le coût d'une qualité pondéré par sa recette est
dans `analyse_revient_qualite.py`.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.analyse_revient_lignes import (
    AnalyseRevient,
    BlocRevient,
    DossierNonReparti,
    GroupeRevient,
    LigneDetailRevient,
    ajouter,
    groupe,
    ligne_detail,
)
from gestion_mp_pro.calcul.classification import TYPES_CONNUS
from gestion_mp_pro.calcul.constantes import CENTIME
from gestion_mp_pro.calcul.importations import LigneRevient, revient_dossier
from gestion_mp_pro.calcul.modele import Article, Donnees, DossierImport

__all__ = [
    "AXES",
    "AnalyseRevient",
    "DossierNonReparti",
    "FiltresRevient",
    "GroupeRevient",
    "LigneDetailRevient",
    "QualiteInconnue",
    "analyse_revient",
    "combinaisons",
    "sans_accents",
    "valeur_critere",
]

Axe = Callable[[Article, LigneRevient, DossierImport], str]
"""La valeur d'une ligne sur un axe de regroupement."""

AXES: dict[str, tuple[str, Axe]] = {
    "reference": ("Référence", lambda a, r, d: a.reference),
    "composition": ("Composition", lambda a, r, d: a.composition or a.nature),
    "type_fil": ("Type de fil", lambda a, r, d: a.type_fil),
    "titrage": ("Titrage", lambda a, r, d: f"{a.titrage} {a.titrage_unite}".strip()),
    "couleur": ("Couleur", lambda a, r, d: a.couleur or a.designation),
    "fournisseur": ("Fournisseur", lambda a, r, d: r.fournisseur or a.fournisseur),
    "role_bom": ("Rôle", lambda a, r, d: a.role_bom),
    "dossier": ("Dossier", lambda a, r, d: d.numero),
    "lot": ("Lot", lambda a, r, d: r.lot_fournisseur),
}
"""Les axes : code → (libellé, valeur d'une ligne)."""
STATUTS = {"ouvert": "Ouvert", "clos": "Clos"}
"""Le statut demandé (sans casse) → le statut du moteur."""
CRITERES_COMBINABLES = ("composition", "type_fil", "titrage", "couleur", "fournisseur")
"""Les critères qu'une combinaison de la sélection peut cumuler."""
AUCUNE = "\0"
"""La sélection impossible : des références choisies hors de la recette de la qualité."""


class QualiteInconnue(LookupError):
    """Une qualité inconnue ou sans recette (404 à la route)."""


@dataclass
class FiltresRevient:
    """Les paramètres de la route `GET /importations/analyse/revient`."""

    axe: str = "reference"
    q: str = ""
    debut: date | None = None
    fin: date | None = None
    composition: str = ""
    type_fil: str = ""
    titrage: str = ""
    couleur: str = ""
    fournisseur: str = ""
    qualite: str = ""
    statut: str = ""
    references: str = ""
    selection: str = ""
    detail: bool = False


def combinaisons(selection: str) -> list[dict[str, str]]:
    """Lit la sélection multiple (JSON), et refuse (`ValueError`) ce qui n'en est pas une."""
    if not selection.strip():
        return []
    try:
        brut = json.loads(selection)
    except json.JSONDecodeError as erreur:
        raise ValueError(f"sélection illisible : {erreur.msg}") from None
    if not isinstance(brut, list) or not all(isinstance(x, dict) for x in brut):
        raise ValueError("la sélection doit être une liste de combinaisons")
    resultat = []
    for combinaison in brut:
        inconnus = set(combinaison) - set(CRITERES_COMBINABLES)
        if inconnus:
            raise ValueError(f"critère inconnu dans la sélection : {', '.join(inconnus)}")
        propre = {k: str(v).strip() for k, v in combinaison.items() if str(v).strip()}
        if propre:
            resultat.append(propre)
    return resultat


def sans_accents(texte: str) -> str:
    """« Frisé » et « frise » sont le même mot : la recherche ignore accents et majuscules."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte or "") if unicodedata.category(c) != "Mn"
    ).lower()


def valeur_critere(article: Article, revient: LigneRevient, critere: str) -> str:
    """La valeur d'un critère combinable pour une ligne."""
    return {
        "composition": article.composition or article.nature,
        "type_fil": article.type_fil,
        "titrage": str(article.titrage),
        "couleur": article.couleur or article.designation,
        "fournisseur": revient.fournisseur or article.fournisseur,
    }[critere]


@dataclass
class _Contexte:
    filtres: FiltresRevient
    choisies: set[str]
    mots: list[str]
    types: dict[str, str]
    combinaisons: list[dict[str, str]]
    groupes: dict[str, BlocRevient] = field(default_factory=dict)
    detail: list[LigneDetailRevient] = field(default_factory=list)
    non_repartis: dict[str, float] = field(default_factory=dict)

    @property
    def filtre_matiere(self) -> bool:
        """Un critère sur les marchandises (matière, fournisseur, combinaisons)."""
        f = self.filtres
        return bool(
            self.choisies
            or f.composition
            or f.type_fil
            or f.titrage
            or f.couleur
            or f.fournisseur
            or self.combinaisons
        )


def _choisies(donnees: Donnees, f: FiltresRevient) -> set[str]:
    """Les références choisies ; une qualité et des matières se cumulent (la recette)."""
    choisies = {x.strip() for x in f.references.split(";") if x.strip()}
    if f.qualite:
        recette = {r.reference for r in donnees.recettes if r.qualite == f.qualite}
        if not recette:
            raise QualiteInconnue(f"qualité inconnue ou sans recette : « {f.qualite} »")
        choisies = (choisies & recette) or ({AUCUNE} if choisies else recette)
    return choisies


def _retenue(ctx: _Contexte, a: Article, r: LigneRevient) -> bool:
    """La ligne répond-elle aux critères de matière et à une des combinaisons ?"""
    f = ctx.filtres
    refus = (
        (ctx.choisies and r.reference not in ctx.choisies)
        or (f.composition and (a.composition or a.nature) != f.composition)
        or (f.type_fil and a.type_fil != f.type_fil)
        or (f.titrage and str(a.titrage) != f.titrage)
        or (f.couleur and (a.couleur or a.designation) != f.couleur)
        or (f.fournisseur and (r.fournisseur or a.fournisseur) != f.fournisseur)
    )
    if refus:
        return False
    if not ctx.combinaisons:
        return True
    return any(
        all(valeur_critere(a, r, c) == v for c, v in combinaison.items() if v)
        for combinaison in ctx.combinaisons
    )


def _texte_trouve(ctx: _Contexte, a: Article, r: LigneRevient, d: DossierImport) -> bool:
    """Chaque mot cherché se trouve dans le dossier, la ligne ou la matière."""
    if not ctx.mots:
        return True
    valeurs = (
        d.numero,
        d.libelle,
        r.reference,
        r.lot_fournisseur,
        r.fournisseur,
        a.nature,
        a.composition,
        a.type_fil,
        ctx.types.get(a.type_fil, ""),
        f"{a.titrage} {a.titrage_unite}",
        a.couleur,
        a.designation,
    )
    texte = sans_accents(" ".join(valeur or "" for valeur in valeurs))
    return all(mot in texte for mot in ctx.mots)


def _dossier_retenu(f: FiltresRevient, statut: str, d: DossierImport) -> bool:
    """Le dossier entre-t-il dans la période et le statut demandés ?"""
    if f.debut and d.date_arrivee and d.date_arrivee < f.debut:
        return False
    if f.fin and d.date_arrivee and d.date_arrivee > f.fin:
        return False
    return not (statut and d.statut != statut)


def _parcourir(ctx: _Contexte, donnees: Donnees, d: DossierImport) -> None:
    """Les lignes d'un dossier, groupées ; ses frais non répartis s'il répond aux filtres."""
    repartis = revient_dossier(d, donnees.parametres)
    hors_tva = sum(c.montant for c in d.charges if not c.recuperable)
    ecart = hors_tva - sum(x.charges_mad for x in repartis)
    retenues = 0
    for r in repartis:
        a = donnees.article(r.reference)
        if a is None or not _retenue(ctx, a, r) or not _texte_trouve(ctx, a, r, d):
            continue
        retenues += 1
        cle = AXES[ctx.filtres.axe][1](a, r, d) or "—"
        ajouter(ctx.groupes, cle, r, d.numero)
        if ctx.filtres.detail:
            ctx.detail.append(ligne_detail(a, r, d))
    vide_trouve = (
        not repartis
        and not ctx.filtre_matiere
        and all(mot in sans_accents(f"{d.numero} {d.libelle}") for mot in ctx.mots)
    )
    if abs(ecart) > CENTIME and (not (ctx.filtre_matiere or ctx.mots) or retenues or vide_trouve):
        ctx.non_repartis[d.numero] = ecart


def _statut_voulu(statut: str) -> str:
    """« ouvert » ou « Ouvert » ; un statut inconnu se refuse (`ValueError`)."""
    voulu = STATUTS.get(statut.strip().lower(), "") if statut.strip() else ""
    if statut.strip() and not voulu:
        raise ValueError(
            f"Statut de dossier inconnu : « {statut.strip()} » (attendu : Ouvert ou Clos)."
        )
    return voulu


def analyse_revient(
    donnees: Donnees,
    filtres: FiltresRevient | None = None,
    *,
    types_fil: dict[str, str] | None = None,
    ids_dossiers: dict[str, int] | None = None,
) -> AnalyseRevient:
    """Ce que la matière importée a coûté, rendue usine (`analyse_revient`).

    `types_fil` : code → libellé des types de fil (« frisé » trouve FRZ ; `TYPES_CONNUS` à
    défaut) ; `ids_dossiers` : n° → id de chaque dossier, pour mener à sa fenêtre.
    Les critères se cumulent ; une sélection réunit ses combinaisons ; les frais d'un dossier
    qu'aucune marchandise ne porte se comptent à part, s'il répond aux mêmes critères.
    """
    f = filtres or FiltresRevient()
    if f.axe not in AXES:
        raise ValueError(f"axe inconnu : « {f.axe} » (attendu : {', '.join(AXES)})")
    statut = _statut_voulu(f.statut)
    choisies = _choisies(donnees, f)
    mots = sans_accents(f.q).split()
    types = (TYPES_CONNUS if types_fil is None else types_fil) if mots else {}
    ctx = _Contexte(f, choisies, mots, types, combinaisons(f.selection))
    for d in donnees.dossiers_import:
        if _dossier_retenu(f, statut, d):
            _parcourir(ctx, donnees, d)
    lignes = [groupe(b) for b in ctx.groupes.values()]
    lignes.sort(key=lambda x: -x.revient_mad)
    vus = {n for x in lignes for n in x.dossiers}
    ids = {n: i for n, i in (ids_dossiers or {}).items() if n in vus or n in ctx.non_repartis}
    return AnalyseRevient(
        axe=f.axe,
        ids_dossiers=ids,
        frais_non_repartis_mad=sum(ctx.non_repartis.values()),
        dossiers_non_repartis=[
            DossierNonReparti(k, v) for k, v in sorted(ctx.non_repartis.items())
        ],
        libelle_axe=AXES[f.axe][0],
        lignes=lignes,
        detail_lignes=sorted(
            ctx.detail,
            key=lambda x: (x.date_arrivee.isoformat() if x.date_arrivee else "", x.dossier),
            reverse=True,
        ),
        total_lignes=sum(x.lignes for x in lignes),
        total_poids=sum(x.poids for x in lignes),
        total_marchandise_mad=sum(x.marchandise_mad for x in lignes),
        total_charges_mad=sum(x.charges_mad for x in lignes),
        total_revient_mad=sum(x.revient_mad for x in lignes),
        total_tva_mad=sum(x.tva_mad for x in lignes),
        total_decaisse_mad=sum(x.decaisse_mad for x in lignes),
    )
