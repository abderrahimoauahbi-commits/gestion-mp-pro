"""Lire les opérations : la fiche (lignes, auteurs, blocages, droits du lecteur) et la liste
paginée, cherchable sans accents (REGLES S88, C-13 ; API-PRO 115, 116, 241).

Les prix et valeurs portent des noms du filtre (`prix`, `valeurs`) : l'alimentation les
reçoit à `null` par la route ; le classeur les retire lui-même.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Fournisseur,
    Magasin,
    Matiere,
    Motif,
    Operation,
    OperationLigne,
    Ordre,
    RoleNomenclature,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import StatutDocument, TypeOperation
from gestion_mp_pro.services import recherche
from gestion_mp_pro.services.operations import blocages as b
from gestion_mp_pro.services.operations import droits
from gestion_mp_pro.services.operations.saisie import est_quarantaine

ZERO = Decimal(0)
LOT_INTERNE = "LOT INTERNE"
"""Ce qu'une ligne « Lot interne » montre avant la validation (numéro donné à ce moment)."""


@dataclass
class LigneLue:
    """Une ligne d'opération telle que l'écran la montre."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Decimal
    lot_id: int | None
    lot: str
    lot_interne: bool
    magasin_id: int
    magasin: str
    magasin_destination_id: int | None
    magasin_destination: str
    quantite: Decimal
    prix: Decimal
    devise: str | None


@dataclass
class ValeurDevise:
    """La valeur d'une ouverture dans une devise (jamais additionnée à une autre)."""

    devise: str
    montant: Decimal


@dataclass
class OperationLue:
    """Une opération : en-tête, auteurs, lignes, total, blocages, ce que le lecteur peut faire."""

    id: int
    numero: str | None
    type: str
    type_libelle: str
    statut: str
    date: date
    ordre_id: int | None
    ordre: str
    fournisseur_id: int | None
    fournisseur: str
    motif_id: int | None
    motif: str
    code_motif: str
    commentaire: str
    cree_par: str
    cree_le: datetime
    validee_par: str
    validee_le: datetime | None
    annulee_par: str
    annulee_le: datetime | None
    annulation_motif: str
    total: Decimal
    version: int
    peut_agir: bool
    raison: str
    liberation: bool
    mise_en_quarantaine: bool
    lignes: list[LigneLue] = field(default_factory=list)
    valeurs: list[ValeurDevise] = field(default_factory=list)
    blocages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FiltresOperations:
    """Les filtres de la liste (et de son classeur)."""

    type: TypeOperation | None = None
    statut: StatutDocument | None = None
    q: str = ""
    types: tuple[TypeOperation, ...] = ()


def charger(s: Session, ident: int, *, verrou: bool = False) -> Operation:
    """L'opération et ses lignes (`FOR UPDATE` de l'opération si `verrou`), ou 404 (OR28)."""
    requete = select(Operation).where(Operation.id == ident).options(selectinload(Operation.lignes))
    if verrou:
        requete = requete.with_for_update(of=Operation)
    o = s.scalars(requete.execution_options(populate_existing=True)).first()
    if o is None:
        raise Refus.introuvable("Opération introuvable.")
    return o


def droit_d_agir(o: Operation, role: str, ctx: b.Contexte) -> tuple[bool, str]:
    """Ce rôle peut-il agir sur cette opération (son type, et une quarantaine que seuls la
    direction et les achats quittent) ? Et sinon pourquoi."""
    type_ = TypeOperation(o.type)
    if not droits.peut_type(role, type_):
        return False, droits.reserve_a(type_)
    if not droits.peut_liberer(role) and passages(o, ctx)[0]:
        return False, droits.REFUS_LIBERATION
    return True, ""


def passages(o: Operation, ctx: b.Contexte) -> tuple[bool, bool]:
    """(libère, met en quarantaine) : un transfert qui sort un lot d'une quarantaine vers un
    magasin ordinaire, ou qui l'y fait entrer."""
    if o.type != TypeOperation.transfert:
        return False, False
    quarantaines = {g.id for g in ctx.magasins.values() if est_quarantaine(g)}
    libere = any(
        x.magasin_id in quarantaines and x.magasin_destination_id not in quarantaines
        for x in o.lignes
    )
    met = any(
        x.magasin_id not in quarantaines and x.magasin_destination_id in quarantaines
        for x in o.lignes
    )
    return libere, met


def lire(s: Session, operations: list[Operation], role: str) -> list[OperationLue]:
    """Les opérations prêtes à rendre (requêtes groupées, blocages des seuls brouillons)."""
    ctx = b.contexte(s, operations)
    noms = _noms(s, operations)
    lineaires = set(s.scalars(select(RoleNomenclature.id).where(RoleNomenclature.lineaire)))
    return [_lue(s, o, ctx=ctx, noms=noms, lineaires=lineaires, role=role) for o in operations]


def _noms(s: Session, ops: list[Operation]) -> dict[tuple[str, int], str]:
    """Noms des personnes, ordres, fournisseurs et motifs cités, par (genre, id)."""
    ids: dict[str, set[int]] = defaultdict(set)
    for o in ops:
        for qui in (o.cree_par_id, o.validee_par_id, o.annulee_par_id):
            if qui is not None:
                ids["u"].add(qui)
        for genre, ident in (("o", o.ordre_id), ("f", o.fournisseur_id), ("m", o.motif_id)):
            if ident is not None:
                ids[genre].add(ident)
    noms: dict[tuple[str, int], str] = {}
    sources = (
        ("u", Utilisateur.id, Utilisateur.nom),
        ("o", Ordre.id, func.coalesce(Ordre.numero, "")),
        ("f", Fournisseur.id, Fournisseur.nom),
        ("m", Motif.id, func.coalesce(Motif.code_r, "")),
    )
    for genre, cle, valeur in sources:
        if ids[genre]:
            for ident, nom in s.execute(select(cle, valeur).where(cle.in_(ids[genre]))):
                noms[(genre, ident)] = nom
    return noms


def _lue(
    s: Session,
    o: Operation,
    *,
    ctx: b.Contexte,
    noms: dict[tuple[str, int], str],
    lineaires: set[int],
    role: str,
) -> OperationLue:
    """Une opération lue."""

    def nom(genre: str, ident: int | None) -> str:
        return noms.get((genre, ident), "") if ident is not None else ""

    peut, raison = droit_d_agir(o, role, ctx)
    libere, met = passages(o, ctx)
    return OperationLue(
        id=o.id, numero=o.numero, type=o.type, type_libelle=droits.LIBELLES[TypeOperation(o.type)],
        statut=o.statut, date=o.date, ordre_id=o.ordre_id, ordre=nom("o", o.ordre_id),
        fournisseur_id=o.fournisseur_id, fournisseur=nom("f", o.fournisseur_id),
        motif_id=o.motif_id, motif=o.motif_texte, code_motif=nom("m", o.motif_id),
        commentaire=o.commentaire, cree_par=nom("u", o.cree_par_id), cree_le=o.cree_le,
        validee_par=nom("u", o.validee_par_id), validee_le=o.validee_le,
        annulee_par=nom("u", o.annulee_par_id), annulee_le=o.annulee_le,
        annulation_motif=o.annulation_motif, total=sum((x.quantite for x in o.lignes), ZERO),
        version=o.version, peut_agir=peut, raison=raison, liberation=libere,
        mise_en_quarantaine=met,
        lignes=[_ligne_lue(x, ctx, lineaires) for x in o.lignes],
        valeurs=_valeurs(o), blocages=b.blocages(s, o, ctx),
    )  # fmt: skip


def _ligne_lue(x: OperationLigne, ctx: b.Contexte, lineaires: set[int]) -> LigneLue:
    """Une ligne lue (le lot créé, sinon le numéro saisi, sinon « LOT INTERNE »)."""
    m = ctx.matieres[x.matiere_id]
    lot = ctx.lots.get(x.lot_id) if x.lot_id is not None else None
    numero = (
        lot.numero
        if lot is not None
        else (x.lot_numero or ("LOT INTERNE" if x.lot_interne else ""))
    )
    destination = ctx.magasins.get(x.magasin_destination_id or 0)
    return LigneLue(
        id=x.id, matiere_id=x.matiere_id, reference=m.reference, designation=m.designation,
        kg_par_ml=m.densite if m.role_id in lineaires else ZERO, lot_id=x.lot_id, lot=numero,
        lot_interne=x.lot_interne, magasin_id=x.magasin_id,
        magasin=ctx.magasins[x.magasin_id].code,
        magasin_destination_id=x.magasin_destination_id,
        magasin_destination=destination.code if destination is not None else "",
        quantite=x.quantite, prix=x.prix, devise=x.devise,
    )  # fmt: skip


def _valeurs(o: Operation) -> list[ValeurDevise]:
    """Σ quantité × prix d'une ouverture, par devise (jamais additionnées entre elles)."""
    if o.type != TypeOperation.ouverture:
        return []
    par_devise: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for x in o.lignes:
        par_devise[x.devise or "MAD"] += x.quantite * x.prix
    return [ValeurDevise(d, v.quantize(Decimal("0.01"))) for d, v in sorted(par_devise.items())]


def fiche(s: Session, ident: int, role: str) -> OperationLue:
    """Route 116 : une opération, même ancienne (C-13)."""
    return lire(s, [charger(s, ident)], role)[0]


def _texte(magasin_source: type[Magasin], magasin_arrivee: type[Magasin]) -> ColumnElement[str]:
    """Le texte cherché d'une opération (numéro, « brouillon », motif, observations, ordre,
    fournisseur, personnes, matières, lots, magasins), sans accents."""
    lignes = (
        select(
            func.string_agg(
                func.concat_ws(
                    " ", Matiere.reference, OperationLigne.lot_numero, magasin_source.code,
                    magasin_arrivee.code,
                ),
                " ",
            )
        )
        .join(Matiere, Matiere.id == OperationLigne.matiere_id)
        .join(magasin_source, magasin_source.id == OperationLigne.magasin_id)
        .outerjoin(magasin_arrivee, magasin_arrivee.id == OperationLigne.magasin_destination_id)
        .where(OperationLigne.operation_id == Operation.id)
        .scalar_subquery()
    )  # fmt: skip

    def voisin(colonne: Any, cle: Any, ident: Any) -> Any:
        return select(colonne).where(cle == ident).scalar_subquery()

    texte = func.concat_ws(
        " ", Operation.numero, case((Operation.statut == StatutDocument.brouillon, "brouillon")),
        Operation.motif_texte, Operation.commentaire, lignes,
        voisin(Ordre.numero, Ordre.id, Operation.ordre_id),
        voisin(Fournisseur.nom, Fournisseur.id, Operation.fournisseur_id),
        voisin(Utilisateur.nom, Utilisateur.id, Operation.cree_par_id),
        voisin(Utilisateur.nom, Utilisateur.id, Operation.validee_par_id),
    )  # fmt: skip
    return recherche.sans_accents_sql(texte)


def filtrer(f: FiltresOperations) -> Select[Operation]:
    """La requête de la liste filtrée (type, statut, types permis, mots)."""
    requete = select(Operation)
    if f.type is not None:
        requete = requete.where(Operation.type == f.type)
    if f.types:
        requete = requete.where(Operation.type.in_(f.types))
    if f.statut is not None:
        requete = requete.where(Operation.statut == f.statut)
    if f.q.strip():
        texte = _texte(aliased(Magasin), aliased(Magasin))
        requete = requete.where(*recherche.conditions(texte, f.q))
    return requete


@dataclass
class PageOperations:
    """Une page de la liste : les opérations, le total filtré, la clé de la dernière."""

    elements: list[OperationLue]
    total: int
    dernier: tuple[date, int] | None


def lister(
    s: Session, f: FiltresOperations, apres: tuple[date, int] | None, limite: int, role: str
) -> PageOperations:
    """Route 115 : les plus récentes d'abord (date, n°), par pages ; le total est dit."""
    requete = filtrer(f)
    total = s.scalar(select(func.count()).select_from(requete.subquery())) or 0
    if apres is not None:
        jour, ident = apres
        requete = requete.where(
            or_(Operation.date < jour, and_(Operation.date == jour, Operation.id < ident))
        )
    ops = list(
        s.scalars(
            requete.options(selectinload(Operation.lignes))
            .order_by(Operation.date.desc(), Operation.id.desc())
            .limit(limite + 1)
        )
    )
    suite = len(ops) > limite
    ops = ops[:limite]
    dernier = (ops[-1].date, ops[-1].id) if suite and ops else None
    return PageOperations(lire(s, ops, role), total, dernier)


def toutes(s: Session, f: FiltresOperations, role: str) -> list[OperationLue]:
    """Le classeur (241) : toutes les opérations filtrées, les plus récentes d'abord."""
    ops = list(
        s.scalars(
            filtrer(f)
            .options(selectinload(Operation.lignes))
            .order_by(Operation.date.desc(), Operation.id.desc())
        )
    )
    return lire(s, ops, role)
