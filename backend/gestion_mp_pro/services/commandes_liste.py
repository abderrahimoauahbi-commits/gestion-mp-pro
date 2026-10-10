"""La liste des bons (route 152, paginée par curseur), son aperçu (251), l'accès borné aux bons
ouverts (252) et le classeur de la liste (166, non paginé).

Recherche et filtres (statut d'onglet, fournisseur, devise) poussés en SQL, comme /receptions.
La recherche lit, sans accents, tout ce que lisait l'ancienne recherche Python (`commandes_fiche`)
SAUF **l'état de livraison** (`livraison_libelle`), calculé par le moteur (`suivi_livraison`) et
non reproductible en SQL : il reste accessible par les onglets et le filtre « en retard »
(convention PAGINATION4, comme les colonnes numériques de /operations).

Le filtre « en retard » (drapeau par bon, moteur) est tenu borné : un pré-filtre SQL grossier
(bons partis non clos dont l'échéance est dépassée) puis l'affinage par le moteur — à ×30, on ne
reconstruit jamais tout l'historique. `lister` ne construit le résumé que pour la page rendue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Commande, CommandeLigne, Fournisseur, Matiere, Utilisateur
from gestion_mp_pro.modeles.enums import StatutCommande
from gestion_mp_pro.services import commandes_fiche as cf
from gestion_mp_pro.services import horloge, recherche
from gestion_mp_pro.services.commandes_fiche import BonDetaille, CommandeResume, FiltresCommandes
from gestion_mp_pro.services.commandes_lecture import (
    LIBELLES_STATUT,
    charger_commandes,
    lecture,
    lignes,
)
from gestion_mp_pro.services.commandes_socle import CLOS, reglage_nombre

OUVERTS_MAX = 5000
"""Plafond de l'accès « tous les bons ouverts » (saisie des réceptions, Ma journée, Cockpit)."""


def _tab(statut: str) -> str:
    """L'onglet d'un bon : son statut, ou « clos » pour un bon soldé ou annulé."""
    return "clos" if statut in ("soldee", "annulee") else statut


def _texte_sql() -> ColumnElement[str]:
    """Le texte cherché d'un bon (sans accents), identique à l'ancienne recherche Python SAUF
    l'état de livraison retiré : numéro, fournisseur (nom et pays), devise, statut libellé,
    créateur, remarques, conteneur, navire, références et désignations des lignes."""
    matieres = (
        select(func.string_agg(func.concat_ws(" ", Matiere.reference, Matiere.designation), " "))
        .select_from(CommandeLigne)
        .join(Matiere, Matiere.id == CommandeLigne.matiere_id)
        .where(CommandeLigne.commande_id == Commande.id)
        .scalar_subquery()
    )
    fournisseur = (
        select(func.concat_ws(" ", Fournisseur.nom, Fournisseur.pays))
        .where(Fournisseur.id == Commande.fournisseur_id)
        .scalar_subquery()
    )
    cree_par = (
        select(Utilisateur.nom).where(Utilisateur.id == Commande.cree_par_id).scalar_subquery()
    )
    libelle = case(*[(Commande.statut == StatutCommande(k), v) for k, v in LIBELLES_STATUT.items()])
    texte = func.concat_ws(
        " ",
        func.coalesce(Commande.numero, "brouillon"),
        fournisseur,
        Commande.devise,
        libelle,
        cree_par,
        Commande.observations,
        Commande.conteneur,
        Commande.navire,
        matieres,
    )
    return recherche.sans_accents_sql(texte)


def _verifier(f: FiltresCommandes) -> None:
    """Un onglet inconnu est refusé (comme l'ancienne liste Python)."""
    if f.statut and f.statut not in cf.ONGLETS:
        raise Refus.saisie(
            f"Statut inconnu : « {f.statut} ».",
            code="valeur_inconnue",
            champs={"statut": "inconnu"},
        )


def filtrer(f: FiltresCommandes) -> Select[Commande]:
    """La requête des bons retenus (onglet, fournisseur, devise, mots) ; le retard est à part."""
    _verifier(f)
    requete: Select[Commande] = select(Commande)
    if f.statut:
        requete = requete.where(Commande.statut.in_(cf.ONGLETS[f.statut]))
    if f.fournisseur_id is not None:
        requete = requete.where(Commande.fournisseur_id == f.fournisseur_id)
    if f.devise:
        requete = requete.where(Commande.devise == f.devise)
    if f.q.strip():
        requete = requete.where(*recherche.conditions(_texte_sql(), f.q))
    return requete


def _resumes(s: Session, commandes: list[Commande]) -> list[CommandeResume]:
    """Les résumés de ces bons, le contexte de lecture monté une seule fois (requêtes groupées)."""
    if not commandes:
        return []
    ctx = lecture(s, commandes)
    return [cf.resume(c, ctx, lignes(c, ctx)) for c in commandes]


def _ordre(requete: Select[Commande]) -> Select[Commande]:
    """Le plus récent d'abord : date du bon puis n° d'entrée."""
    return requete.options(selectinload(Commande.lignes)).order_by(
        Commande.date_commande.desc(), Commande.id.desc()
    )


def _candidats_retard(f: FiltresCommandes, s: Session) -> Select[Commande]:
    """Les bons qui PEUVENT être en retard : partis, ni soldés ni annulés, échéance dépassée au
    retard toléré près (pré-filtre SQL grossier, sur-ensemble des vrais retards ; affinés ensuite
    par le moteur). Le filtre « retard » n'a de sens que hors des onglets clos."""
    tolere = int(reglage_nombre(s, "toler_retard_jours"))
    limite = horloge.aujourd_hui() - timedelta(days=tolere)
    delai = (
        select(func.coalesce(Fournisseur.delai_jours, 0))
        .where(Fournisseur.id == Commande.fournisseur_id)
        .scalar_subquery()
    )
    echeance = func.coalesce(
        Commande.eta, Commande.date_livraison_prevue, Commande.date_commande + delai
    )
    return filtrer(f).where(Commande.parti, Commande.statut.notin_(CLOS), echeance < limite)


def _en_retard(s: Session, f: FiltresCommandes) -> list[CommandeResume]:
    """Les bons en retard retenus par `f`, le plus récent d'abord (drapeau affiné par le moteur)."""
    commandes = list(s.scalars(_ordre(_candidats_retard(f, s))))
    return [r for r in _resumes(s, commandes) if r.en_retard]


@dataclass
class PageCommandes:
    """Une page de la liste : les bons, le total filtré, la clé du dernier (date, n° d'entrée)."""

    elements: list[CommandeResume]
    total: int
    dernier: tuple[date, int] | None


def _apres(requete: Select[Commande], apres: tuple[date, int]) -> Select[Commande]:
    """Le curseur : les bons strictement avant la clé (date, n° d'entrée) rendue."""
    jour, ident = apres
    return requete.where(
        or_(
            Commande.date_commande < jour, and_(Commande.date_commande == jour, Commande.id < ident)
        )
    )


def _page_retard(
    s: Session, f: FiltresCommandes, apres: tuple[date, int] | None, limite: int
) -> PageCommandes:
    """La page des bons en retard : l'ensemble (borné) calculé puis découpé par curseur."""
    retard = _en_retard(s, f)
    total = len(retard)
    if apres is not None:
        retard = [r for r in retard if (r.date_commande, r.id) < apres]
    page = retard[:limite]
    dernier = (page[-1].date_commande, page[-1].id) if len(retard) > limite and page else None
    return PageCommandes(page, total, dernier)


def lister(
    s: Session, f: FiltresCommandes, apres: tuple[date, int] | None, limite: int
) -> PageCommandes:
    """Route 152 : les bons filtrés, le plus récent d'abord, par pages (résumé de la page seule)."""
    s.flush()
    if f.retard:
        return _page_retard(s, f, apres, limite)
    base = filtrer(f)
    total = s.scalar(select(func.count()).select_from(base.subquery())) or 0
    requete = base if apres is None else _apres(base, apres)
    commandes = list(s.scalars(_ordre(requete).limit(limite + 1)))
    suite = len(commandes) > limite
    commandes = commandes[:limite]
    dernier = (commandes[-1].date_commande, commandes[-1].id) if suite and commandes else None
    return PageCommandes(_resumes(s, commandes), total, dernier)


def ouverts(s: Session, limite: int = OUVERTS_MAX) -> list[CommandeResume]:
    """Route 252 : tous les bons ouverts (ni soldés ni annulés), plafonnés, le plus récent d'abord.
    La saisie des réceptions, Ma journée et le Cockpit les filtrent eux-mêmes ; ils sont peu
    nombreux (les bons clos, qui s'accumulent, ne sont plus lus hors de leur onglet)."""
    s.flush()
    commandes = list(
        s.scalars(_ordre(select(Commande).where(Commande.statut.notin_(CLOS))).limit(limite))
    )
    return _resumes(s, commandes)


def detailler(s: Session, f: FiltresCommandes) -> list[BonDetaille]:
    """Le classeur de la liste (166, non paginé) : les bons filtrés comme la liste, du plus récent
    au plus ancien, avec leurs lignes ; un bon en retard dit de combien de jours."""
    s.flush()
    if f.retard:
        ids = [r.id for r in _en_retard(s, f)]
        par_id = {c.id: c for c in charger_commandes(s, ids)}
        commandes = [par_id[i] for i in ids]
    else:
        commandes = list(s.scalars(_ordre(filtrer(f))))
    ctx = lecture(s, commandes)
    detail = []
    for c in commandes:
        lues = lignes(c, ctx)
        r = cf.resume(c, ctx, lues)
        detail.append(BonDetaille(r, lues, cf._retard(c, ctx) if r.en_retard else None))
    return detail


# ── Aperçu (route 251) ───────────────────────────────────────────────────────


@dataclass
class IndicateursCommandes:
    """Les indicateurs de l'écran, comptés sur TOUS les bons ouverts (hors onglet, recherche,
    filtres) : la rangée d'indicateurs ne suit ni la recherche ni les filtres (ECRANS-PRO 4.5)."""

    ouverts: int
    brouillons: int
    a_approuver: int
    engage: float
    partis: int
    partis_estimes: int
    reste: float
    a_confirmer: int
    retard: int


@dataclass
class TotalDevise:
    """Un total de montant estimé dans sa devise (jamais additionné entre devises)."""

    devise: str
    montant_estime: float


@dataclass
class OptionFournisseur:
    """Un fournisseur du filtre lié (identifiant et nom)."""

    id: int
    nom: str


@dataclass
class ApercuCommandes:
    """Tout ce que l'écran calculait sur la liste entière : comptes par onglet (suivant recherche,
    filtres et « en retard »), indicateurs, pied de totaux de l'onglet, options des filtres liés."""

    brouillon: int
    a_approuver: int
    envoyee: int
    confirmee: int
    clos: int
    total: int
    indicateurs: IndicateursCommandes
    quantite: float
    montant_estime_mad: float
    montants: list[TotalDevise] = field(default_factory=list)
    fournisseurs: list[OptionFournisseur] = field(default_factory=list)
    devises: list[str] = field(default_factory=list)


def _comptes(s: Session, f: FiltresCommandes) -> dict[str, int]:
    """Les comptes par onglet (tous onglets), suivant la recherche, les filtres liés et « retard »
    — mais pas l'onglet actif (`statut`)."""
    socle = FiltresCommandes(fournisseur_id=f.fournisseur_id, devise=f.devise, q=f.q)
    comptes: dict[str, int] = {}
    if f.retard:
        for r in _en_retard(s, socle):
            comptes[_tab(r.statut)] = comptes.get(_tab(r.statut), 0) + 1
        return comptes
    sub = filtrer(socle).subquery()
    for statut, n in s.execute(select(sub.c.statut, func.count()).group_by(sub.c.statut)):
        comptes[_tab(str(statut))] = comptes.get(_tab(str(statut)), 0) + n
    return comptes


def _totaux(s: Session, f: FiltresCommandes) -> tuple[float, float, list[TotalDevise]]:
    """Le pied de l'onglet (recherche, filtres et « retard ») : Σ kg, Σ MAD, Σ par devise."""
    if f.retard:
        resumes = _en_retard(s, f)
    else:
        resumes = _resumes(s, list(s.scalars(_ordre(filtrer(f)))))
    par_devise: dict[str, float] = {}
    for r in resumes:
        par_devise[r.devise] = par_devise.get(r.devise, 0.0) + r.montant_estime
    montants = [TotalDevise(d, v) for d, v in sorted(par_devise.items())]
    return (
        sum(r.quantite for r in resumes),
        sum(r.montant_estime_mad for r in resumes),
        montants,
    )


_SANS_INDICATEURS = IndicateursCommandes(0, 0, 0, 0.0, 0, 0, 0.0, 0, 0)
"""Indicateurs vides : l'aperçu d'un onglet ne les calcule pas (l'écran les prend de l'aperçu
global, sans onglet) ; de même, l'aperçu global ne calcule pas le pied, propre à un onglet."""


def _indicateurs(s: Session) -> IndicateursCommandes:
    """Les indicateurs sur tous les bons ouverts (identiques à `liste.indicateurs` de l'écran)."""
    resumes = ouverts(s)
    partis = [r for r in resumes if r.statut in ("envoyee", "confirmee")]
    return IndicateursCommandes(
        ouverts=len(resumes),
        brouillons=sum(1 for r in resumes if r.statut == "brouillon"),
        a_approuver=sum(1 for r in resumes if r.statut == "a_approuver"),
        engage=sum(r.montant_estime_mad for r in partis),
        partis=len(partis),
        partis_estimes=sum(1 for r in partis if r.prix_a_confirmer > 0),
        reste=sum(r.reste_estime_mad for r in resumes if r.parti),
        a_confirmer=sum(1 for r in resumes if r.parti and r.prix_a_confirmer > 0),
        retard=sum(1 for r in resumes if r.en_retard),
    )


def _fournisseurs(s: Session) -> list[OptionFournisseur]:
    """Les fournisseurs présents sur les bons (options du filtre lié), par nom."""
    requete = (
        select(Commande.fournisseur_id, Fournisseur.nom)
        .join(Fournisseur, Fournisseur.id == Commande.fournisseur_id)
        .distinct()
        .order_by(Fournisseur.nom)
    )
    return [OptionFournisseur(ident, nom) for ident, nom in s.execute(requete)]


def _devises(s: Session) -> list[str]:
    """Les devises présentes sur les bons (options du filtre lié), par code."""
    return list(s.scalars(select(Commande.devise).distinct().order_by(Commande.devise)))


def apercu(s: Session, f: FiltresCommandes) -> ApercuCommandes:
    """Route 251 : les comptes par onglet, les indicateurs, le pied et les options des filtres.

    L'écran appelle l'aperçu deux fois : **sans onglet** pour les indicateurs (sur tous les bons
    ouverts) et le défaut, **avec onglet** pour le pied de cet onglet. Chaque appel ne calcule que
    ce qu'il sert (un seul passage O(bornée) par appel) : les comptes et les options sont toujours
    là, le pied seulement avec un onglet, les indicateurs seulement sans."""
    s.flush()
    comptes = _comptes(s, f)
    quantite, mad, montants = _totaux(s, f) if f.statut else (0.0, 0.0, [])
    return ApercuCommandes(
        brouillon=comptes.get("brouillon", 0),
        a_approuver=comptes.get("a_approuver", 0),
        envoyee=comptes.get("envoyee", 0),
        confirmee=comptes.get("confirmee", 0),
        clos=comptes.get("clos", 0),
        total=sum(comptes.values()),
        indicateurs=_SANS_INDICATEURS if f.statut else _indicateurs(s),
        quantite=quantite,
        montant_estime_mad=mad,
        montants=montants,
        fournisseurs=_fournisseurs(s),
        devises=_devises(s),
    )
