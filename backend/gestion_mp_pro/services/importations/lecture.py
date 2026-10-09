"""La liste des dossiers (route 187) et le détail de chacun pour le classeur (route 205) : la
même dépendance de filtres, donc les mêmes dossiers (filtres = écran).

Ordre de Gestion MP (R-IMP-04) : date d'arrivée décroissante, sans date à la fin, puis id
décroissant. Sans statut demandé : les dossiers ouverts et clos (les annulés sont à part,
`statut=annule`). La recherche cherche chaque mot, sans accents, dans le numéro, le libellé, la
banque, les observations, les factures, les réceptions, les familles de fil et les fournisseurs.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import Dossier, DossierFrais
from gestion_mp_pro.modeles.enums import StatutDossier
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services.importations import parties
from gestion_mp_pro.services.importations.fiche import resume
from gestion_mp_pro.services.importations.modele import (
    DossierResume,
    Echeance,
    FraisDossier,
    LigneDossier,
)
from gestion_mp_pro.services.importations.socle import contexte


@dataclass(frozen=True)
class FiltresDossiers:
    """`?statut=&q=&fournisseur=` (route 187 et son classeur 205)."""

    statut: str = ""
    q: str = ""
    fournisseur: int | None = None


@dataclass
class DossierDetaille:
    """Un dossier et son détail, pour le classeur."""

    resume: DossierResume
    lignes: list[LigneDossier]
    frais: list[FraisDossier]
    echeancier: list[Echeance]


def _dossiers(s: Session, statut: str) -> list[Dossier]:
    """Les dossiers du statut demandé (ouverts et clos sans statut), dans l'ordre de la liste."""
    requete = (
        select(Dossier)
        .options(
            selectinload(Dossier.lignes),
            selectinload(Dossier.frais).selectinload(DossierFrais.parts),
        )
        .order_by(Dossier.date_arrivee.desc().nulls_last(), Dossier.id.desc())
    )
    if statut:
        requete = requete.where(Dossier.statut == StatutDossier(statut))
    else:
        requete = requete.where(Dossier.statut != StatutDossier.annule)
    return list(s.scalars(requete))


def _texte(r: DossierResume) -> str:
    """Ce que la recherche lit d'un dossier, sans accents."""
    morceaux = [r.numero, r.libelle, r.banque, r.commentaire, *r.factures, *r.fournisseurs]
    morceaux += [x.numero for x in r.receptions] + [x.famille for x in r.familles]
    return normaliser(" ".join(morceaux))


def _retenu(r: DossierResume, d: Dossier, f: FiltresDossiers, mots: list[str]) -> bool:
    """Le dossier répond-il au fournisseur et à chaque mot cherché ?"""
    if f.fournisseur is not None:
        siens = {x.fournisseur_id for x in d.lignes}
        if r.facture is not None:
            siens.add(r.facture.fournisseur_id)
        if f.fournisseur not in siens:
            return False
    texte = _texte(r) if mots else ""
    return all(mot in texte for mot in mots)


def detailler(s: Session, f: FiltresDossiers) -> list[DossierDetaille]:
    """Les dossiers filtrés, chacun avec ses marchandises, ses frais et son échéancier."""
    dossiers = _dossiers(s, f.statut)
    ctx = contexte(s, dossiers)
    mots = normaliser(f.q).split()
    resultat = []
    for d in dossiers:
        r, m = resume(d, ctx)
        if _retenu(r, d, f, mots):
            resultat.append(
                DossierDetaille(
                    r, m.lignes, parties.frais_lus(d, ctx), parties.echeancier(d, ctx, m)
                )
            )
    return resultat


def lister(s: Session, f: FiltresDossiers) -> list[DossierResume]:
    """Les dossiers filtrés, sans leur détail (route 187)."""
    dossiers = _dossiers(s, f.statut)
    ctx = contexte(s, dossiers)
    mots = normaliser(f.q).split()
    resumes = ((resume(d, ctx)[0], d) for d in dossiers)
    return [r for r, d in resumes if _retenu(r, d, f, mots)]
