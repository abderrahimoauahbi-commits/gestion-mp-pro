"""La liste des réceptions (route 167) et la fiche d'une réception (168) : brouillons recalés
**sans rien écrire** (A.12-27), blocages et avertissements annoncés, écarts de pesée, ce qui est
reparti chez le fournisseur, dossier, annulation, gestes permis (ECRANS-PRO § 4.15–4.21).

Lecture groupée : un nombre fixe de requêtes pour toute la liste (aucune par ligne).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.modeles import Facture, Fournisseur, Lot, Reception, ReceptionLigne, Utilisateur
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import reglages
from gestion_mp_pro.services.chargeur.achats import retours_par_ligne_reception
from gestion_mp_pro.services.commandes_socle import nom_commande
from gestion_mp_pro.services.receptions_blocages import (
    Contexte,
    blocages,
    contexte,
)
from gestion_mp_pro.services.receptions_socle import (
    QUALITES,
    STATUTS,
    Recale,
    bons,
    nom_reception,
    quarantaine,
    recalage,
)


@dataclass(frozen=True)
class FiltresReceptions:
    """`?statut=&q=&du=&au=&fournisseur=` de la liste et de son classeur."""

    statut: str = ""
    q: str = ""
    du: dt.date | None = None
    au: dt.date | None = None
    fournisseur: int | None = None


@dataclass
class FactureLue:
    """La facture d'une réception."""

    id: int
    numero: str
    date: dt.date | None
    montant: Decimal | None
    devise: str
    echeance: dt.date | None
    payee_le: dt.date | None
    version: int


@dataclass
class BonCite:
    """Un bon nommé par une réception."""

    id: int
    numero: str


@dataclass
class LigneLue:
    """Une ligne de réception telle que l'écran la montre."""

    id: int
    commande_ligne_id: int | None
    commande_id: int | None
    commande: str
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Decimal
    poids_bobine_catalogue: Decimal
    bobines_palette: Decimal
    lot_numero: str
    lot_interne: bool
    lot_id: int | None
    quantite_commandee: Decimal
    deja_recu: float
    quantite_attendue: Decimal
    quantite_bl: Decimal
    quantite_pesee: Decimal
    reste_apres: float
    nb_palettes: Decimal
    bobines_en_plus: Decimal
    nb_bobines: Decimal
    poids_moyen_bobine: float | None
    ecart: float | None
    ecart_relatif: float | None
    hors_tolerance: bool
    magasin_id: int | None
    magasin: str
    qualite: str
    qualite_libelle: str
    observations: str
    prix: Decimal
    prix_confirme: bool
    retourne: float


@dataclass
class ReceptionResume:
    """Une réception dans la liste."""

    id: int
    numero: str | None
    libelle: str
    statut: str
    statut_libelle: str
    date: dt.date
    fournisseur_id: int
    fournisseur: str
    devise: str
    numero_bl: str
    facture: FactureLue | None
    commandes: list[BonCite]
    nb_lignes: int
    pese: Decimal
    nb_reserve: int
    nb_refus: int
    lots: list[int]
    cree_par: str
    controle_par: str
    validee_par: str
    validee_le: datetime | None
    observations: str
    blocages: list[str]
    annulation_motif: str
    version: int


@dataclass
class Annulation:
    """Qui a annulé la réception, quand, pourquoi."""

    par: str
    le: datetime
    motif: str


@dataclass
class DossierCite:
    """Le dossier d'importation qui porte la réception."""

    id: int
    numero: str
    statut: str


@dataclass
class Tolerances:
    """Les tolérances lues aux réglages (l'écran ne les écrit pas en dur)."""

    ecart_pesee: float
    poids_bobine: float
    excedent: float


@dataclass
class ReceptionFiche(ReceptionResume):
    """La fiche d'une réception (route 168)."""

    cree_le: datetime | None = None
    delai_paiement_jours: int = 0
    lignes: list[LigneLue] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)
    dossier: DossierCite | None = None
    annulation: Annulation | None = None
    tolerances: Tolerances | None = None
    actions: dict[str, str | None] = field(default_factory=dict)


@dataclass
class _Lecture:
    """Ce que la liste lit une fois : contexte des blocages, noms, factures, lots, retours."""

    ctx: Contexte
    noms: dict[int, str]
    fournisseurs: dict[int, Fournisseur]
    factures: dict[int, Facture]
    lots: dict[int, str]
    retours: dict[int, float]
    tolerance_pesee: float


def _lire(s: Session, receptions: list[Reception]) -> _Lecture:
    """Le contexte de lecture de ces réceptions (nombre fixe de requêtes)."""
    b = bons(s, receptions)
    ctx = contexte(s, receptions, b, quarantaine(s))
    fids = {r.facture_id for r in receptions if r.facture_id}
    lids = {x.lot_id for r in receptions for x in r.lignes if x.lot_id}
    valides = any(r.statut == StatutDocument.validee for r in receptions)
    return _Lecture(
        ctx,
        dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).tuples().all()),
        {f.id: f for f in s.scalars(select(Fournisseur))},
        {f.id: f for f in s.scalars(select(Facture).where(Facture.id.in_(fids)))} if fids else {},
        dict(s.execute(select(Lot.id, Lot.numero).where(Lot.id.in_(lids))).tuples().all())
        if lids
        else {},
        retours_par_ligne_reception(s) if valides else {},
        reglages.nombre(s, "toler_ecart_pesee"),
    )


def charger_receptions(s: Session, ids: list[int] | None = None) -> list[Reception]:
    """Les réceptions et leurs lignes (la plus récente d'abord)."""
    requete = (
        select(Reception).options(selectinload(Reception.lignes)).order_by(Reception.id.desc())
    )
    if ids is not None:
        requete = requete.where(Reception.id.in_(ids))
    return list(s.scalars(requete))


def _facture(f: Facture | None) -> FactureLue | None:
    if f is None:
        return None
    return FactureLue(
        f.id, f.numero, f.date, f.montant, f.devise, f.echeance, f.payee_le, f.version
    )


def ecart_de_pesee(x: ReceptionLigne, attendu_recale: Decimal, tolerance: float) -> float | None:
    """Pesé − attendu : l'attendu est le BL ; sans BL, le reste à livrer seulement quand on pèse
    au moins ce reste (une livraison partielle sans BL n'est pas un écart, R13r)."""
    pese = float(x.quantite_pesee)
    attendu = float(x.quantite_bl) or (
        float(attendu_recale) if pese >= float(attendu_recale) * (1 - tolerance) else 0.0
    )
    return pese - attendu if attendu else None


def _ligne(x: ReceptionLigne, r: Reception, lu: _Lecture, recale: Recale | None) -> LigneLue:
    """Une ligne lue, recalée (brouillon) sans rien écrire."""
    ctx = lu.ctx
    m = ctx.matieres[x.matiere_id]
    cl = ctx.bons.lignes.get(x.commande_ligne_id) if x.commande_ligne_id else None
    c = ctx.bons.bon(cl.id) if cl is not None else None
    attendu = recale.attendu if recale is not None else x.quantite_attendue
    prix = recale.prix if recale is not None and recale.prix is not None else x.prix
    accepte = x.qualite != QualiteReception.refuse
    compte = (
        float(x.quantite_pesee) - lu.retours.get(x.id, 0.0)
        if r.statut == StatutDocument.validee and accepte
        else 0.0
    )
    ecart = ecart_de_pesee(x, attendu, lu.tolerance_pesee)
    attendu_ecart = float(x.quantite_pesee) - ecart if ecart is not None else 0.0
    relatif = ecart / attendu_ecart if ecart is not None and attendu_ecart else None
    magasin = ctx.magasins.get(x.magasin_id) if x.magasin_id else None
    return LigneLue(
        x.id, x.commande_ligne_id, c.id if c else None, nom_commande(c) if c else "",
        m.id, m.reference, m.designation, m.densite, m.poids_bobine, m.bobines_palette,
        lu.lots.get(x.lot_id, x.lot_numero) if x.lot_id else x.lot_numero, x.lot_interne,
        x.lot_id, cl.quantite if cl else Decimal(0),
        max(0.0, ctx.bons.recu.get(cl.id, 0.0) - compte) if cl else 0.0,
        attendu, x.quantite_bl, x.quantite_pesee,
        max(0.0, float(attendu) - (float(x.quantite_pesee) if accepte else 0.0)) if cl else 0.0,
        x.nb_palettes, x.bobines_en_plus, x.nb_bobines,
        float(x.quantite_pesee / x.nb_bobines) if x.nb_bobines else None,
        ecart, relatif, relatif is not None and abs(relatif) > lu.tolerance_pesee,
        x.magasin_id, magasin.code if magasin else "", str(x.qualite),
        QUALITES[QualiteReception(x.qualite)], x.observations, prix,
        bool(cl and cl.prix_confirme and cl.prix), lu.retours.get(x.id, 0.0),
    )  # fmt: skip


def _bons_cites(r: Reception, lu: _Lecture) -> list[BonCite]:
    """Les bons de la réception, dans l'ordre de ses lignes."""
    vus: dict[int, BonCite] = {}
    for x in sorted(r.lignes, key=lambda y: y.id or 0):
        if x.commande_ligne_id:
            c = lu.ctx.bons.bon(x.commande_ligne_id)
            vus.setdefault(c.id, BonCite(c.id, nom_commande(c)))
    return list(vus.values())


def resume(s: Session, r: Reception, lu: _Lecture) -> ReceptionResume:
    """Le résumé d'une réception (blocages d'un brouillon compris)."""
    brouillon = r.statut == StatutDocument.brouillon
    acceptees = [x for x in r.lignes if x.qualite != QualiteReception.refuse]
    return ReceptionResume(
        r.id, r.numero, nom_reception(r), str(r.statut), STATUTS[StatutDocument(r.statut)],
        r.date, r.fournisseur_id, lu.fournisseurs[r.fournisseur_id].nom, r.devise, r.numero_bl,
        _facture(lu.factures.get(r.facture_id) if r.facture_id else None), _bons_cites(r, lu),
        len(r.lignes), sum((x.quantite_pesee for x in acceptees), Decimal(0)),
        sum(1 for x in r.lignes if x.qualite == QualiteReception.reserve),
        sum(1 for x in r.lignes if x.qualite == QualiteReception.refuse),
        sorted({x.lot_id for x in r.lignes if x.lot_id}),
        lu.noms.get(r.cree_par_id or 0, ""), r.controle_par,
        lu.noms.get(r.validee_par_id or 0, ""), r.validee_le, r.observations,
        [b.message for b in blocages(s, r, lu.ctx)] if brouillon else [],
        r.annulation_motif, r.version,
    )  # fmt: skip


def _texte(r: ReceptionResume, lignes: list[ReceptionLigne], lu: _Lecture) -> str:
    """Ce que la recherche lit : n°, fournisseur, BL, facture, personnes, bons, lignes."""
    morceaux = [
        r.numero or "brouillon", r.fournisseur, r.numero_bl,
        r.facture.numero if r.facture else "", r.cree_par, r.controle_par, r.observations,
        *(b.numero for b in r.commandes),
        *(
            f"{lu.ctx.matieres[x.matiere_id].reference} {lu.ctx.matieres[x.matiere_id].designation}"
            f" {lu.lots.get(x.lot_id, '') if x.lot_id else x.lot_numero}"
            for x in lignes
        ),
    ]  # fmt: skip
    return normaliser(" ".join(m for m in morceaux if m))


def _passe(r: Reception, f: FiltresReceptions) -> bool:
    """Les filtres de statut, de dates et de fournisseur."""
    if f.statut and str(r.statut) != f.statut:
        return False
    if f.du is not None and r.date < f.du:
        return False
    if f.au is not None and r.date > f.au:
        return False
    return f.fournisseur is None or r.fournisseur_id == f.fournisseur


def liste(s: Session, f: FiltresReceptions) -> list[ReceptionResume]:
    """Route 167 : la liste filtrée au serveur (recherche multi-mots, sans accents)."""
    receptions = [r for r in charger_receptions(s) if _passe(r, f)]
    lu = _lire(s, receptions)
    mots = normaliser(f.q).split()
    resultat = []
    for r in receptions:
        x = resume(s, r, lu)
        if mots and not all(m in _texte(x, r.lignes, lu) for m in mots):
            continue
        resultat.append(x)
    return resultat


def lire_lignes(
    s: Session, receptions: list[Reception]
) -> tuple[_Lecture, dict[int, list[LigneLue]]]:
    """Les lignes lues de ces réceptions (pour le classeur)."""
    lu = _lire(s, receptions)
    lignes = {}
    for r in receptions:
        recal = recalage(r, lu.ctx.bons)
        lignes[r.id] = [
            _ligne(x, r, lu, recal.get(x.id)) for x in sorted(r.lignes, key=lambda y: y.id or 0)
        ]
    return lu, lignes


def detailler(s: Session, f: FiltresReceptions) -> list[tuple[ReceptionResume, list[LigneLue]]]:
    """Les réceptions de la liste filtrée et leurs lignes (classeur 178 : filtres = écran)."""
    resumes = liste(s, f)
    if not resumes:
        return []
    _, lignes = lire_lignes(s, charger_receptions(s, [r.id for r in resumes]))
    return [(r, lignes[r.id]) for r in resumes]
