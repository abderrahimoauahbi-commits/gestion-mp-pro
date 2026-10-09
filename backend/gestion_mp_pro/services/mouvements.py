"""Le journal du stock en lecture (routes 105, 106, 113 ; REGLES S61–S64, S68) : les mouvements
filtrés, le plus récent d'abord, par pages (curseur), avec leur valeur au coût du moment ; le
contrôle des soldes contre le journal.

Recherche `q` : tous les mots, sans accents, `%` et `_` littéraux (C-14), sur la matière (son
texte cherché), le lot, le n° de document, le motif, le commentaire et l'auteur.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select, tuple_
from sqlalchemy.orm import Session, aliased

from gestion_mp_pro.calcul.valorisation import couts_du_journal
from gestion_mp_pro.modeles import Lot, Magasin, Matiere, Motif, Mouvement, Solde, Utilisateur
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
from gestion_mp_pro.services import donnees_moteur, recherche
from gestion_mp_pro.services.tracabilite import LIBELLES

ZERO = Decimal(0)


@dataclass(frozen=True)
class FiltresMouvements:
    """Les filtres du journal (route 105, et son export 106)."""

    q: str = ""
    matiere_id: int | None = None
    lot_id: int | None = None
    magasin_id: int | None = None
    type: TypeMouvement | None = None
    document: DocumentMouvement | None = None
    du: date | None = None
    au: date | None = None


@dataclass
class LigneMouvement:
    """Une écriture du journal, telle que l'écran la montre (S64)."""

    id: int
    date: date
    saisi_le: datetime
    type: str
    libelle: str
    matiere_id: int
    reference: str
    lot_id: int
    lot: str
    magasin_id: int
    magasin: str
    quantite: Decimal
    prix: Decimal
    devise: str
    cours: Decimal | None
    document: str
    document_id: int | None
    document_numero: str
    ordre_id: int | None
    paire_id: int | None
    motif: str
    commentaire: str
    auteur: str
    contrepasse_id: int | None
    cout_mad: float | None = None
    valeur_mad: float | None = None


Auteur = aliased(Utilisateur)


def _requete(f: FiltresMouvements) -> Select[Mouvement, str, str, str, str, str]:
    """Les mouvements qui passent les filtres, avec ce que l'écran en cite."""
    requete = (
        select(Mouvement, Matiere.reference, Lot.numero, Magasin.code, Motif.libelle, Auteur.nom)
        .join(Matiere, Matiere.id == Mouvement.matiere_id)
        .join(Lot, Lot.id == Mouvement.lot_id)
        .join(Magasin, Magasin.id == Mouvement.magasin_id)
        .outerjoin(Motif, Motif.id == Mouvement.motif_id)
        .outerjoin(Auteur, Auteur.id == Mouvement.auteur_id)
    )
    egaux = {
        Mouvement.matiere_id: f.matiere_id,
        Mouvement.lot_id: f.lot_id,
        Mouvement.magasin_id: f.magasin_id,
        Mouvement.type: f.type,
        Mouvement.document: f.document,
    }
    requete = requete.where(*(col == v for col, v in egaux.items() if v is not None))
    if f.du is not None:
        requete = requete.where(Mouvement.date_effet >= f.du)
    if f.au is not None:
        requete = requete.where(Mouvement.date_effet <= f.au)
    return requete.where(*_recherche(f.q))


def _recherche(q: str) -> Sequence[ColumnElement[bool]]:
    """Tous les mots, chacun dans l'un des champs cherchés (sans accents)."""
    textes = func.concat_ws(
        " ",
        Matiere.texte_recherche,
        Lot.texte_recherche,
        recherche.sans_accents_sql(Mouvement.document_numero),
        recherche.sans_accents_sql(func.coalesce(Motif.libelle, "")),
        recherche.sans_accents_sql(Mouvement.motif_texte),
        recherche.sans_accents_sql(Mouvement.commentaire),
        recherche.sans_accents_sql(func.coalesce(Auteur.nom, "")),
    )
    return recherche.conditions(textes, q)


def _ligne(rang: Sequence[Any]) -> LigneMouvement:
    """Une ligne du journal pour l'écran : (mouvement, référence, lot, magasin, motif, auteur)."""
    m, ref, lot, magasin, motif, auteur = rang
    document_id = m.reception_id or m.operation_id or m.inventaire_id
    if m.document == DocumentMouvement.ordre:
        document_id = m.ordre_id
    return LigneMouvement(
        id=m.id, date=m.date_effet, saisi_le=m.saisi_le, type=str(m.type),
        libelle=LIBELLES.get(str(m.type), str(m.type)), matiere_id=m.matiere_id, reference=ref,
        lot_id=m.lot_id, lot=lot, magasin_id=m.magasin_id, magasin=magasin, quantite=m.quantite,
        prix=m.prix, devise=m.devise, cours=m.cours, document=str(m.document),
        document_id=document_id, document_numero=m.document_numero, ordre_id=m.ordre_id,
        paire_id=m.paire_id, motif=motif or m.motif_texte, commentaire=m.commentaire,
        auteur=auteur or "", contrepasse_id=m.contrepasse_id,
    )  # fmt: skip


def _couts(s: Session) -> tuple[Any, dict[str, float]]:
    """Le coût de chaque ligne du journal et le coût moyen actuel par matière (une fois)."""
    couts = couts_du_journal(donnees_moteur.charger(s))
    return couts, couts.cmup()


def _valoriser_une(x: LigneMouvement, couts: Any, actuel: dict[str, float]) -> None:
    """Coût unitaire (MAD) et valeur d'une ligne : l'arrivée d'un transfert vaut son départ ; à
    défaut, le coût moyen actuel de la matière (S55, S63)."""
    cout = couts.unitaire.get(x.id, couts.unitaire.get(x.paire_id or 0))
    x.cout_mad = actuel.get(x.reference, 0.0) if cout is None else cout
    x.valeur_mad = float(x.quantite) * x.cout_mad


def valoriser(s: Session, lignes: list[LigneMouvement]) -> None:
    """Coût unitaire (MAD) et valeur de chaque ligne : le calcul de la valorisation (S55, S63) ;
    l'arrivée d'un transfert vaut son départ ; à défaut, le coût moyen actuel de la matière."""
    if not lignes:
        return
    couts, actuel = _couts(s)
    for x in lignes:
        _valoriser_une(x, couts, actuel)


def tous_en_flux(s: Session, f: FiltresMouvements, avec_valeur: bool) -> Iterator[LigneMouvement]:
    """Route 106 (export en flux) : toutes les lignes filtrées, le plus récent d'abord, rendues
    **une à une** depuis un curseur (`yield_per`) — aucune liste de tout l'historique en mémoire.
    La valorisation lit son coût de ligne au passage (le calcul des coûts est fait une fois)."""
    couts_actuel = _couts(s) if avec_valeur else None
    requete = _requete(f).order_by(Mouvement.date_effet.desc(), Mouvement.id.desc())
    for rang in s.execute(requete).yield_per(1000):
        x = _ligne(rang)
        if couts_actuel is not None:
            _valoriser_une(x, *couts_actuel)
        yield x


@dataclass
class PageMouvements:
    """Une page du journal : `dernier` = (date, n°) de la dernière ligne s'il en reste."""

    lignes: list[LigneMouvement]
    total: int
    dernier: tuple[date, int] | None


def lister(
    s: Session,
    f: FiltresMouvements,
    apres: tuple[date, int] | None = None,
    limite: int = 500,
    avec_valeur: bool = False,
) -> PageMouvements:
    """Route 105 : le plus récent d'abord (date d'effet, puis n°), `limite` lignes après le
    curseur ; `total` = toutes les lignes qui passent les filtres."""
    requete = _requete(f)
    total = s.scalar(select(func.count()).select_from(requete.subquery())) or 0
    if apres is not None:
        requete = requete.where(tuple_(Mouvement.date_effet, Mouvement.id) < tuple_(*apres))
    rangs = s.execute(
        requete.order_by(Mouvement.date_effet.desc(), Mouvement.id.desc()).limit(limite + 1)
    ).all()
    lignes = [_ligne(r) for r in rangs[:limite]]
    if avec_valeur:
        valoriser(s, lignes)
    dernier = (lignes[-1].date, lignes[-1].id) if len(rangs) > limite else None
    return PageMouvements(lignes, total, dernier)


def tous(s: Session, f: FiltresMouvements, avec_valeur: bool) -> list[LigneMouvement]:
    """Route 106 (export) : toutes les lignes, sans limite, le plus récent d'abord."""
    rangs = s.execute(_requete(f).order_by(Mouvement.date_effet.desc(), Mouvement.id.desc()))
    lignes = [_ligne(r) for r in rangs.all()]
    if avec_valeur:
        valoriser(s, lignes)
    return lignes


@dataclass
class EcartDeSolde:
    """Un solde tenu qui ne dit pas ce que dit le journal."""

    lot_id: int
    magasin_id: int
    reference: str
    lot: str
    magasin: str
    journal: Decimal
    solde: Decimal


@dataclass
class ControleSoldes:
    """Route 113 : les soldes égalent-ils le journal (I02) ? Aucun n'est négatif (I03) ?"""

    conforme: bool
    ecarts: list[EcartDeSolde]
    negatifs: int
    lots: int


def controler_soldes(s: Session) -> ControleSoldes:
    """Chaque solde (lot, magasin) confronté à la somme du journal, au gramme (S68)."""
    journal = {
        (lot, mag): q
        for lot, mag, q in s.execute(
            select(Mouvement.lot_id, Mouvement.magasin_id, func.sum(Mouvement.quantite)).group_by(
                Mouvement.lot_id, Mouvement.magasin_id
            )
        ).all()
    }
    tenus = {(x.lot_id, x.magasin_id): x.quantite for x in s.scalars(select(Solde))}
    noms = {
        i: (ref, num)
        for i, ref, num in s.execute(
            select(Lot.id, Matiere.reference, Lot.numero).join(
                Matiere, Matiere.id == Lot.matiere_id
            )
        ).all()
    }
    magasins = dict(s.execute(select(Magasin.id, Magasin.code)).all())
    ecarts = [
        EcartDeSolde(
            lot,
            mag,
            *noms[lot],
            magasins[mag],
            journal.get((lot, mag), ZERO),
            tenus.get((lot, mag), ZERO),
        )  # fmt: skip
        for lot, mag in sorted(set(journal) | set(tenus))
        if journal.get((lot, mag), ZERO) != tenus.get((lot, mag), ZERO)
    ]
    negatifs = sum(1 for q in tenus.values() if q < 0)
    return ControleSoldes(not ecarts and not negatifs, ecarts, negatifs, len(tenus))


def types_presents(s: Session, f: FiltresMouvements) -> list[str]:
    """Les types présents compte tenu des autres filtres (filtres liés, A1)."""
    autres = FiltresMouvements(**{**f.__dict__, "type": None})
    requete = _requete(autres).with_only_columns(Mouvement.type).distinct()
    return sorted(str(t) for t in s.scalars(requete))
