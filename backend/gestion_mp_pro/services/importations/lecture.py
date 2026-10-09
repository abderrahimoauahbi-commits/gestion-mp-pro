"""La liste des dossiers (route 187, paginée par curseur) et son aperçu (route 250), plus le détail
de chacun pour le classeur (route 205) : la même dépendance de filtres, donc les mêmes dossiers.

Ordre de Gestion MP (R-IMP-04) : date d'arrivée décroissante, sans date à la fin, puis id
décroissant. Sans statut demandé : les dossiers ouverts et clos (les annulés sont à part,
`statut=annule`). La recherche cherche chaque mot, sans accents **et à la ponctuation près**
(« FA-2026/117 » = « FA-2026-117 »), dans le numéro, le libellé, la banque, les observations, les
factures, les réceptions, les familles de fil et les fournisseurs : tout cela poussé en SQL (le
détail est joint par sous-requête). Le filtre « à vérifier » tient à un calcul par dossier
(`parties.a_verifier`) non poussable en SQL : il est servi en liste bornée (peu de dossiers).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import (
    Composition,
    Dossier,
    DossierFrais,
    DossierLigne,
    Facture,
    Fournisseur,
    Matiere,
    Reception,
    ReceptionLigne,
    Titrage,
    TypeFil,
)
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.services import recherche
from gestion_mp_pro.services.importations import parties
from gestion_mp_pro.services.importations.fiche import resume
from gestion_mp_pro.services.importations.modele import (
    DossierResume,
    Echeance,
    FraisDossier,
    LigneDossier,
)
from gestion_mp_pro.services.importations.socle import contexte

ZERO = 0.0
SEUIL_NON_REPARTIS = 0.005
"""Sous ce demi-centime, des frais non répartis ne comptent pas (I15, comme l'écran)."""


@dataclass(frozen=True)
class FiltresDossiers:
    """`?statut=&q=&fournisseur=&verifier=` (route 187, son aperçu 250 et son classeur 205)."""

    statut: str = ""
    q: str = ""
    fournisseur: int | None = None
    verifier: str = ""


@dataclass
class DossierDetaille:
    """Un dossier et son détail, pour le classeur."""

    resume: DossierResume
    lignes: list[LigneDossier]
    frais: list[FraisDossier]
    echeancier: list[Echeance]


def _famille_sql() -> ColumnElement[str]:
    """La famille de fil d'une matière, à l'identique de `socle.famille` : code de la composition,
    libellé du type (tronqué au «  ( »), code du titrage ; à défaut, la référence."""
    morceaux = func.concat_ws(
        " ", Composition.code, func.split_part(TypeFil.libelle, " (", 1), Titrage.code
    )
    return func.coalesce(func.nullif(func.trim(morceaux), ""), Matiere.reference)


def _texte_sql() -> ColumnElement[str]:
    """Le texte cherché d'un dossier (brut, normalisé par la recherche) : ses champs et, par
    sous-requête, les réceptions, factures, familles de fil et fournisseurs de ses lignes."""
    derive = (
        select(
            func.string_agg(
                func.concat_ws(
                    " ",
                    Reception.numero,
                    Facture.numero,
                    _famille_sql(),
                    Fournisseur.nom,
                ),
                " ",
            )
        )
        .select_from(DossierLigne)
        .outerjoin(ReceptionLigne, ReceptionLigne.id == DossierLigne.reception_ligne_id)
        .outerjoin(Reception, Reception.id == ReceptionLigne.reception_id)
        .outerjoin(Facture, Facture.id == Reception.facture_id)
        .outerjoin(Matiere, Matiere.id == DossierLigne.matiere_id)
        .outerjoin(Composition, Composition.id == Matiere.composition_id)
        .outerjoin(TypeFil, TypeFil.id == Matiere.type_fil_id)
        .outerjoin(Titrage, Titrage.id == Matiere.titrage_id)
        .outerjoin(Fournisseur, Fournisseur.id == DossierLigne.fournisseur_id)
        .where(DossierLigne.dossier_id == Dossier.id)
        .scalar_subquery()
    )
    return func.concat_ws(
        " ", Dossier.numero, Dossier.libelle, Dossier.banque, Dossier.commentaire, derive
    )


def _fournisseur_facture() -> ColumnElement[int]:
    """Le fournisseur de la facture du dossier (celui que lit le filtre lié de l'écran)."""
    return select(Facture.fournisseur_id).where(Facture.id == Dossier.facture_id).scalar_subquery()


def filtrer(f: FiltresDossiers) -> Select[Dossier]:
    """La requête des dossiers retenus (statut, fournisseur de la facture, mots) ; « à vérifier »
    n'y est pas (calculé par dossier, appliqué après le résumé)."""
    requete: Select[Dossier] = select(Dossier)
    if f.statut:
        requete = requete.where(Dossier.statut == StatutDossier(f.statut))
    else:
        requete = requete.where(Dossier.statut != StatutDossier.annule)
    if f.fournisseur is not None:
        requete = requete.where(_fournisseur_facture() == f.fournisseur)
    if f.q.strip():
        requete = requete.where(*recherche.conditions_tolerantes(_texte_sql(), f.q))
    return requete


def _charger(s: Session, requete: Select[Dossier]) -> list[Dossier]:
    """Les dossiers d'une requête, avec leurs lignes et leurs frais (pour le résumé)."""
    return list(
        s.scalars(
            requete.options(
                selectinload(Dossier.lignes),
                selectinload(Dossier.frais).selectinload(DossierFrais.parts),
            )
        )
    )


def _resumes(s: Session, dossiers: list[Dossier]) -> list[DossierResume]:
    """Les dossiers résumés (coût de revient, contrôles) avec un contexte partagé."""
    if not dossiers:
        return []
    ctx = contexte(s, dossiers)
    return [resume(d, ctx)[0] for d in dossiers]


def _a_verifier(r: DossierResume, verifier: str) -> bool:
    """Le dossier répond-il au filtre « à vérifier » (`oui`/`non`) ?"""
    if not verifier:
        return True
    return (verifier == "oui") == bool(r.a_verifier)


_ORDRE = (Dossier.date_arrivee.desc().nulls_last(), Dossier.id.desc())


def _apres(requete: Select[Dossier], apres: tuple[date | None, int]) -> Select[Dossier]:
    """La condition de curseur pour l'ordre (date d'arrivée décroissante, nulls en fin, puis id)."""
    jour, ident = apres
    if jour is None:
        return requete.where(Dossier.date_arrivee.is_(None), Dossier.id < ident)
    return requete.where(
        or_(
            Dossier.date_arrivee.is_(None),
            Dossier.date_arrivee < jour,
            and_(Dossier.date_arrivee == jour, Dossier.id < ident),
        )
    )


@dataclass
class PageDossiers:
    """Une page de la liste : les dossiers, le total filtré, la clé du dernier."""

    elements: list[DossierResume]
    total: int
    dernier: tuple[date | None, int] | None


def lister(
    s: Session, f: FiltresDossiers, apres: tuple[date | None, int] | None, limite: int
) -> PageDossiers:
    """Route 187 : les dossiers filtrés, le plus récemment arrivé d'abord, par pages. Avec le
    filtre « à vérifier » (calculé), la liste est bornée et rendue d'un coup (peu de dossiers)."""
    s.flush()
    base = filtrer(f)
    if f.verifier:
        resumes = [r for r in _resumes(s, _charger(s, base)) if _a_verifier(r, f.verifier)]
        resumes.sort(key=lambda r: (r.date_arrivee is not None, r.date_arrivee, r.id), reverse=True)
        return PageDossiers(resumes, len(resumes), None)
    total = s.scalar(select(func.count()).select_from(base.subquery())) or 0
    requete = base if apres is None else _apres(base, apres)
    dossiers = _charger(s, requete.order_by(*_ORDRE).limit(limite + 1))
    suite = len(dossiers) > limite
    dossiers = dossiers[:limite]
    dernier = (dossiers[-1].date_arrivee, dossiers[-1].id) if suite and dossiers else None
    return PageDossiers(_resumes(s, dossiers), total, dernier)


def detailler(s: Session, f: FiltresDossiers) -> list[DossierDetaille]:
    """Les dossiers filtrés, chacun avec ses marchandises, ses frais, son échéancier (classeur)."""
    s.flush()
    dossiers = {d.id: d for d in _charger(s, filtrer(f))}
    ctx = contexte(s, list(dossiers.values()))
    resultat = []
    for d in dossiers.values():
        r, m = resume(d, ctx)
        if _a_verifier(r, f.verifier):
            resultat.append(
                DossierDetaille(
                    r, m.lignes, parties.frais_lus(d, ctx), parties.echeancier(d, ctx, m)
                )
            )
    resultat.sort(
        key=lambda x: (x.resume.date_arrivee is not None, x.resume.date_arrivee, x.resume.id),
        reverse=True,
    )
    return resultat


@dataclass
class FournisseurOption:
    """Un fournisseur proposé par le filtre lié de la liste."""

    id: int
    nom: str


@dataclass
class DossierNonReparti:
    """Un dossier à frais non répartis (dans aucun coût) cité à part."""

    id: int
    numero: str
    montant: float


@dataclass
class ApercuDossiers:
    """Route 250 : comptes par statut, totaux (pied/indicateurs), dossiers aux frais non répartis
    et fournisseurs du filtre lié, sur le périmètre demandé (statut, recherche, filtres)."""

    ouvert: int
    clos: int
    annule: int
    nombre: int
    poids: float
    marchandise_mad: float
    charges_mad: float
    revient_mad: float
    decaisse_mad: float
    non_repartis: list[DossierNonReparti]
    fournisseurs: list[FournisseurOption]


def _fournisseurs(s: Session, f: FiltresDossiers) -> list[FournisseurOption]:
    """Les fournisseurs des factures des dossiers du statut (options du filtre lié)."""
    statut = FiltresDossiers(statut=f.statut)
    ids = filtrer(statut).with_only_columns(_fournisseur_facture())
    requete = (
        select(Fournisseur.id, Fournisseur.nom)
        .where(Fournisseur.id.in_(ids.where(_fournisseur_facture().isnot(None))))
        .order_by(Fournisseur.nom)
    )
    return [FournisseurOption(i, n) for i, n in s.execute(requete)]


def apercu(s: Session, f: FiltresDossiers) -> ApercuDossiers:
    """Route 250 : ce que l'écran calculait sur la liste entière (indicateurs, onglets, pied,
    non répartis), sur le périmètre demandé."""
    s.flush()
    resumes = [r for r in _resumes(s, _charger(s, filtrer(f))) if _a_verifier(r, f.verifier)]
    comptes = {"ouvert": 0, "clos": 0, "annule": 0}
    for r in resumes:
        comptes[r.statut] = comptes.get(r.statut, 0) + 1
    non_repartis = [
        DossierNonReparti(r.id, r.numero, r.charges_non_reparties_mad)
        for r in resumes
        if abs(r.charges_non_reparties_mad) > SEUIL_NON_REPARTIS
    ]
    return ApercuDossiers(
        ouvert=comptes["ouvert"],
        clos=comptes["clos"],
        annule=comptes["annule"],
        nombre=len(resumes),
        poids=sum(r.poids for r in resumes),
        marchandise_mad=sum(r.marchandise_mad for r in resumes),
        charges_mad=sum(r.charges_mad for r in resumes),
        revient_mad=sum(r.revient_mad for r in resumes),
        decaisse_mad=sum(r.decaisse_mad for r in resumes),
        non_repartis=non_repartis,
        fournisseurs=_fournisseurs(s, f),
    )
