"""La liste des réceptions filtrée au serveur (route 167, paginée par curseur) et son aperçu
(route 181b : comptes par onglet, fournisseurs du filtre lié) ; le classeur (178) garde la liste
entière, non paginée.

Recherche et filtres (fournisseur, origine, facture, qualité) poussés en SQL, à l'identique de ce
que l'écran calculait sur la liste entière (REGLES A.12-27 ; API-PRO 167). La recherche lit, sans
accents, tout ce que l'écran lisait : n°, fournisseur, BL, facture, personnes, bons, lignes
(référence, désignation, lot), et aussi la devise, le motif d'annulation et le statut libellé.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, case, exists, func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Facture,
    Fournisseur,
    Lot,
    Matiere,
    Reception,
    ReceptionLigne,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.services import receptions_lecture as _rl
from gestion_mp_pro.services import recherche
from gestion_mp_pro.services.receptions_lecture import (
    FiltresReceptions,
    LigneLue,
    ReceptionResume,
    charger_receptions,
    lire_lignes,
    resume,
)
from gestion_mp_pro.services.receptions_socle import STATUTS

ZERO = Decimal(0)


def _texte_sql() -> ColumnElement[str]:
    """Le texte cherché d'une réception (sans accents), identique à ce que lisait l'écran."""
    lignes = (
        select(
            func.string_agg(
                func.concat_ws(
                    " ",
                    Matiere.reference,
                    Matiere.designation,
                    func.coalesce(Lot.numero, ReceptionLigne.lot_numero),
                ),
                " ",
            )
        )
        .select_from(ReceptionLigne)
        .join(Matiere, Matiere.id == ReceptionLigne.matiere_id)
        .outerjoin(Lot, Lot.id == ReceptionLigne.lot_id)
        .where(ReceptionLigne.reception_id == Reception.id)
        .scalar_subquery()
    )
    bons = (
        select(func.string_agg(Commande.numero, " "))
        .select_from(ReceptionLigne)
        .join(CommandeLigne, CommandeLigne.id == ReceptionLigne.commande_ligne_id)
        .join(Commande, Commande.id == CommandeLigne.commande_id)
        .where(ReceptionLigne.reception_id == Reception.id)
        .scalar_subquery()
    )

    def voisin(colonne: Any, cle: Any, ident: Any) -> Any:
        """Un champ d'une fiche voisine (sous-requête)."""
        return select(colonne).where(cle == ident).scalar_subquery()

    libelle = case(*[(Reception.statut == s, lib) for s, lib in STATUTS.items()])
    texte = func.concat_ws(
        " ",
        func.coalesce(Reception.numero, "brouillon"),
        voisin(Fournisseur.nom, Fournisseur.id, Reception.fournisseur_id),
        Reception.numero_bl,
        voisin(Facture.numero, Facture.id, Reception.facture_id),
        voisin(Utilisateur.nom, Utilisateur.id, Reception.cree_par_id),
        Reception.controle_par,
        voisin(Utilisateur.nom, Utilisateur.id, Reception.validee_par_id),
        Reception.observations,
        Reception.devise,
        Reception.annulation_motif,
        libelle,
        lignes,
        bons,
    )
    return recherche.sans_accents_sql(texte)


def _sur_bon() -> ColumnElement[bool]:
    """La réception nomme au moins un bon de commande."""
    return exists().where(
        ReceptionLigne.reception_id == Reception.id,
        ReceptionLigne.commande_ligne_id.isnot(None),
    )


def _a_qualite(q: QualiteReception) -> ColumnElement[bool]:
    """La réception a au moins une ligne de cette qualité."""
    return exists().where(ReceptionLigne.reception_id == Reception.id, ReceptionLigne.qualite == q)


def _avec_facture() -> ColumnElement[bool]:
    """La réception a une facture dont le numéro est renseigné (« Avec facture » à l'écran)."""
    numero = select(Facture.numero).where(Facture.id == Reception.facture_id).scalar_subquery()
    return Reception.facture_id.isnot(None) & (func.coalesce(numero, "") != "")


def _lier_filtres(requete: Select[Reception], f: FiltresReceptions) -> Select[Reception]:
    """Les filtres liés de l'écran (origine, facture, qualité), poussés en SQL."""
    if f.origine == "bon":
        requete = requete.where(_sur_bon())
    elif f.origine == "hors":
        requete = requete.where(~_sur_bon())
    if f.facture == "avec":
        requete = requete.where(_avec_facture())
    elif f.facture == "sans":
        requete = requete.where(~_avec_facture())
    refuse = _a_qualite(QualiteReception.refuse)
    reserve = _a_qualite(QualiteReception.reserve)
    if f.qualite == "refus":
        requete = requete.where(refuse)
    elif f.qualite == "reserve":
        requete = requete.where(~refuse, reserve)
    elif f.qualite == "conforme":
        requete = requete.where(~refuse, ~reserve)
    return requete


def filtrer(f: FiltresReceptions) -> Select[Reception]:
    """La requête des réceptions retenues (statut, dates, fournisseur, filtres liés, mots)."""
    requete: Select[Reception] = select(Reception)
    if f.statut:
        requete = requete.where(Reception.statut == StatutDocument(f.statut))
    if f.du is not None:
        requete = requete.where(Reception.date >= f.du)
    if f.au is not None:
        requete = requete.where(Reception.date <= f.au)
    if f.fournisseur is not None:
        requete = requete.where(Reception.fournisseur_id == f.fournisseur)
    requete = _lier_filtres(requete, f)
    if f.q.strip():
        requete = requete.where(*recherche.conditions(_texte_sql(), f.q))
    return requete


def _pese_total(s: Session, f: FiltresReceptions) -> Decimal:
    """Σ des kilos pesés hors refus sur toutes les réceptions retenues (pied de totaux)."""
    ids = filtrer(f).with_only_columns(Reception.id)
    total = s.scalar(
        select(func.coalesce(func.sum(ReceptionLigne.quantite_pesee), ZERO)).where(
            ReceptionLigne.reception_id.in_(ids),
            ReceptionLigne.qualite != QualiteReception.refuse,
        )
    )
    return total or ZERO


@dataclass
class PageReceptions:
    """Une page de la liste : les réceptions, le total filtré, le curseur, le pesé total."""

    elements: list[ReceptionResume]
    total: int
    dernier: int | None
    pese_total: Decimal


def lister(s: Session, f: FiltresReceptions, apres: int | None, limite: int) -> PageReceptions:
    """Route 167 : les réceptions filtrées, la plus récente d'abord (n° d'entrée), par pages."""
    s.flush()
    base = filtrer(f)
    total = s.scalar(select(func.count()).select_from(base.subquery())) or 0
    requete = base if apres is None else base.where(Reception.id < apres)
    recs = list(
        s.scalars(
            requete.options(selectinload(Reception.lignes))
            .order_by(Reception.id.desc())
            .limit(limite + 1)
        )
    )
    suite = len(recs) > limite
    recs = recs[:limite]
    dernier = recs[-1].id if suite and recs else None
    lu = _rl._lire(s, recs)
    return PageReceptions([resume(s, r, lu) for r in recs], total, dernier, _pese_total(s, f))


@dataclass
class FournisseurOption:
    """Un fournisseur du filtre lié (identifiant et nom)."""

    id: int
    nom: str


@dataclass
class ApercuReceptions:
    """L'aperçu : comptes par onglet (suivant la recherche) et fournisseurs du filtre lié."""

    brouillon: int
    validee: int
    annulee: int
    total: int
    fournisseurs: list[FournisseurOption]


def apercu(s: Session, q: str) -> ApercuReceptions:
    """Route 181b : les comptes par statut (recherche seule, tous onglets) et les fournisseurs."""
    s.flush()
    sub = filtrer(FiltresReceptions(q=q)).subquery()
    comptes = {
        str(statut): n
        for statut, n in s.execute(select(sub.c.statut, func.count()).group_by(sub.c.statut))
    }
    fournisseurs = [
        FournisseurOption(ident, nom)
        for ident, nom in s.execute(
            select(Reception.fournisseur_id, Fournisseur.nom)
            .join(Fournisseur, Fournisseur.id == Reception.fournisseur_id)
            .distinct()
            .order_by(Fournisseur.nom)
        )
    ]
    return ApercuReceptions(
        brouillon=comptes.get("brouillon", 0),
        validee=comptes.get("validee", 0),
        annulee=comptes.get("annulee", 0),
        total=sum(comptes.values()),
        fournisseurs=fournisseurs,
    )


def liste(s: Session, f: FiltresReceptions) -> list[ReceptionResume]:
    """La liste entière filtrée (classeur 178, brouillons de « Ma journée ») : non paginée."""
    s.flush()
    recs = list(
        s.scalars(filtrer(f).options(selectinload(Reception.lignes)).order_by(Reception.id.desc()))
    )
    lu = _rl._lire(s, recs)
    return [resume(s, r, lu) for r in recs]


def detailler(s: Session, f: FiltresReceptions) -> list[tuple[ReceptionResume, list[LigneLue]]]:
    """Les réceptions de la liste filtrée et leurs lignes (classeur 178 : filtres = écran)."""
    resumes = liste(s, f)
    if not resumes:
        return []
    _, lignes = lire_lignes(s, charger_receptions(s, [r.id for r in resumes]))
    return [(r, lignes[r.id]) for r in resumes]
