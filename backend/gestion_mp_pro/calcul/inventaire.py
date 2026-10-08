"""Inventaire : écarts en kilos et en dirhams, recomptage, inventaire tournant (CALCULS B § 11).

Portage de la partie calcul de `gestion_mp/api/inventaires.py` : `CADENCE_JOURS`, `retenu`,
`_hors`, `_ecart_hors_tolerance`, `a_recompter`, `couts_inventaire`, les lignes et les totaux
de `inventaire_dict` (sans le masquage des prix, filtre générique des routes) et la règle de
`a_compter` (l'inventaire tournant). Les lignes lues en base arrivent en petites dataclasses ;
la date du jour est un paramètre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.constantes import POUSSIERE
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.valorisation import cmup_par_reference, couts_du_journal

CADENCE_JOURS = {"A": 30, "B": 90, "C": 365}
"""L'inventaire tournant : A chaque mois, B chaque trimestre, C chaque année (jours depuis le
dernier comptage validé)."""
CADENCE_PAR_DEFAUT = 365
"""Une classe inconnue se recompte chaque année."""
CLASSE_PAR_DEFAUT = "C"
"""Une matière sans classe ABC du jour est rangée en C."""
ORDRE_DES_CLASSES = {"A": 0, "B": 1, "C": 2}
"""Le tri du tournant : A d'abord."""
RANG_CLASSE_INCONNUE = 3
"""Une classe hors A, B, C se range après C."""
STATUTS_AJUSTES = ("valide", "annule")
"""Les inventaires qui ont écrit leurs ajustements (leur coût fait foi)."""

CleAjustement = tuple[int | None, int | None]
"""(lot, magasin) d'une ligne d'inventaire : la clé de l'ajustement qu'elle a écrit."""


@dataclass
class LigneInventaire:
    """Une ligne d'inventaire lue en base : son théorique figé et ses comptages.

    `reference` : la matière de son lot (ou du lot trouvé pas encore créé) ; `lot_id`,
    `magasin_id` : de quoi retrouver l'ajustement écrit à la validation.
    """

    id: int
    reference: str
    theorique: float
    compte: float | None = None
    second_compte: float | None = None
    lot_id: int | None = None
    magasin_id: int | None = None


@dataclass
class EcartInventaire:
    """Les champs calculés d'une ligne (clés de `inventaire_dict`)."""

    id: int
    retenu: float | None
    ecart: float | None
    cmup_mad: float
    valeur_ecart_mad: float | None
    hors_tolerance: bool
    a_recompter: bool


@dataclass
class EcartsInventaire:
    """Les totaux d'un inventaire (clés de `inventaire_dict`) et ses lignes calculées."""

    nb_lignes: int
    nb_comptees: int
    hors_tolerance: int
    a_recompter: int
    recomptees: int
    ecart_total: float
    ecart_absolu: float
    ecart_valeur_mad: float
    ecart_valeur_absolue_mad: float
    lignes: list[EcartInventaire] = field(default_factory=list)


@dataclass
class CoutsInventaire:
    """Ce qui valorise un écart : le CMUP de chaque matière, le coût de chaque écriture."""

    cmup: dict[str, float]
    unitaire: dict[int, float]


def retenu(ligne: LigneInventaire) -> float | None:
    """Le comptage qui ajuste : le second (recompté par une autre personne) s'il existe."""
    return ligne.second_compte if ligne.second_compte is not None else ligne.compte


def hors_tolerance(theorique: float, compte: float | None, tolerance: float) -> bool:
    """`_hors` : un écart d'au moins un gramme, sur un théorique nul, ou au-delà de la
    tolérance relative ; rien tant que la ligne n'est pas comptée."""
    if compte is None:
        return False
    ecart = compte - theorique
    if abs(ecart) < POUSSIERE:
        return False
    return theorique <= 0 or abs(ecart) / theorique > tolerance


def ecart_hors_tolerance(ligne: LigneInventaire, tolerance: float) -> bool:
    """Le comptage retenu tombe hors tolérance."""
    return hors_tolerance(ligne.theorique, retenu(ligne), tolerance)


def a_recompter(ligne: LigneInventaire, tolerance: float) -> bool:
    """Le premier comptage tombe hors tolérance et personne ne l'a encore recompté."""
    return ligne.second_compte is None and hors_tolerance(ligne.theorique, ligne.compte, tolerance)


def couts_inventaire(donnees: Donnees) -> CoutsInventaire:
    """Le CMUP de chaque matière aujourd'hui et le coût de chaque ajustement déjà écrit —
    les deux tirés du même calcul que la Valorisation (données d'aujourd'hui)."""
    journal = couts_du_journal(donnees)
    return CoutsInventaire(cmup_par_reference(donnees, journal.cmup()), journal.unitaire)


def _ligne(
    ligne: LigneInventaire,
    tolerance: float,
    couts: CoutsInventaire,
    ajustements: dict[CleAjustement, int],
) -> EcartInventaire:
    ecrit = ajustements.get((ligne.lot_id, ligne.magasin_id))
    if ecrit is not None and ecrit in couts.unitaire:
        cout = couts.unitaire[ecrit]
    else:
        cout = couts.cmup.get(ligne.reference, 0.0)
    compte = retenu(ligne)
    return EcartInventaire(
        id=ligne.id,
        retenu=compte,
        ecart=None if compte is None else compte - ligne.theorique,
        cmup_mad=cout,
        valeur_ecart_mad=None if compte is None else (compte - ligne.theorique) * cout,
        hors_tolerance=ecart_hors_tolerance(ligne, tolerance),
        a_recompter=a_recompter(ligne, tolerance),
    )


def ecarts_inventaire(
    lignes: list[LigneInventaire],
    *,
    statut: str,
    tolerance: float,
    couts: CoutsInventaire,
    ajustements: dict[CleAjustement, int] | None = None,
) -> EcartsInventaire:
    """Les écarts d'un inventaire, en kilos et en dirhams (`inventaire_dict`).

    Un écart se valorise au coût de l'ajustement qu'il a écrit (inventaire validé ou annulé :
    `ajustements` = (lot, magasin) → n° du mouvement, non annulation), sinon au CMUP du moment
    (0 à défaut). Un net en kilos ne dit rien : 50 kg de trop d'un fil à 10 MAD et 50 kg de
    moins d'un fil à 90 font zéro kilo, et 4 000 MAD de perte.
    """
    ecrits = (ajustements or {}) if statut in STATUTS_AJUSTES else {}
    calculees = [_ligne(x, tolerance, couts, ecrits) for x in lignes]
    comptees = [x for x in calculees if x.retenu is not None]
    return EcartsInventaire(
        nb_lignes=len(calculees),
        nb_comptees=len(comptees),
        hors_tolerance=sum(1 for x in calculees if x.hors_tolerance),
        a_recompter=sum(1 for x in calculees if x.a_recompter),
        recomptees=sum(1 for x in lignes if x.second_compte is not None),
        ecart_total=sum(_defini(x.ecart) for x in comptees),
        ecart_absolu=sum(abs(_defini(x.ecart)) for x in comptees),
        ecart_valeur_mad=sum(_defini(x.valeur_ecart_mad) for x in comptees),
        ecart_valeur_absolue_mad=sum(abs(_defini(x.valeur_ecart_mad)) for x in comptees),
        lignes=calculees,
    )


def _defini(valeur: float | None) -> float:
    """Une valeur d'une ligne comptée (jamais None : l'écart existe dès qu'on a compté)."""
    return 0.0 if valeur is None else valeur


# ── Inventaire tournant ──────────────────────────────────────────────────────


@dataclass
class StockAuMagasin:
    """Ce qu'une matière détient dans un magasin (Σ des soldes de ses lots)."""

    article_id: int
    reference: str
    magasin_id: int
    quantite: float
    role: str = ""
    kg_par_ml: float = 0.0


@dataclass
class MatiereACompter:
    """Une matière due au tournant (clés de la route `a_compter`)."""

    article_id: int
    reference: str
    role: str
    classe_abc: str | None
    stock: float
    kg_par_ml: float
    dernier_comptage: date | None
    jours: int | None
    magasins: list[str] = field(default_factory=list)


def _due(
    par_article: dict[int, MatiereACompter],
    x: StockAuMagasin,
    classe: str,
    dernier: date | None,
    retard: int | None,
) -> MatiereACompter:
    due = par_article.get(x.article_id)
    if due is None:
        due = MatiereACompter(
            article_id=x.article_id,
            reference=x.reference,
            role=x.role,
            classe_abc=classe,
            stock=0.0,
            kg_par_ml=x.kg_par_ml,
            dernier_comptage=dernier,
            jours=retard,
        )
        par_article[x.article_id] = due
    return due


def a_compter(
    stocks: list[StockAuMagasin],
    *,
    classes: dict[str, str],
    derniers: dict[tuple[int, int], date],
    magasins: dict[int, str],
    aujourdhui: date,
    magasin_id: int | None = None,
) -> list[MatiereACompter]:
    """L'inventaire tournant : les matières en stock dont le dernier comptage validé est plus
    vieux que la cadence de leur classe ABC (A : 30 j, B : 90 j, C : 365 j ; vide → C).

    `stocks` : (matière, magasin) et leur quantité ; `classes` : la classe ABC du jour par
    référence ; `derniers` : (article, magasin) → date du dernier inventaire validé où la
    ligne a été comptée ; `magasins` : id → code. Un comptage vaut pour le magasin compté :
    la matière est due dès qu'un magasin qui la détient n'a pas été compté à temps ; regroupée
    par matière (stock des magasins dus, leurs codes, le plus ancien comptage — « jamais »
    l'emporte). Tri : classe, dernier comptage (jamais en tête), référence.
    """
    par_article: dict[int, MatiereACompter] = {}
    for x in stocks:
        if x.quantite <= POUSSIERE or (magasin_id and x.magasin_id != magasin_id):
            continue
        classe = classes.get(x.reference) or CLASSE_PAR_DEFAUT
        dernier = derniers.get((x.article_id, x.magasin_id))
        retard = None if dernier is None else (aujourdhui - dernier).days
        if retard is not None and retard < CADENCE_JOURS.get(classe, CADENCE_PAR_DEFAUT):
            continue
        due = _due(par_article, x, classe, dernier, retard)
        due.stock += x.quantite
        due.magasins.append(magasins.get(x.magasin_id, ""))
        # Le plus ancien des magasins dus (jamais compté l'emporte).
        if due.dernier_comptage is not None and (dernier is None or dernier < due.dernier_comptage):
            due.dernier_comptage, due.jours = dernier, retard
    dues = list(par_article.values())
    for due in dues:
        due.magasins.sort()
    dues.sort(
        key=lambda x: (
            ORDRE_DES_CLASSES.get(x.classe_abc or "", RANG_CLASSE_INCONNUE),
            x.dernier_comptage.isoformat() if x.dernier_comptage else "",
            x.reference,
        )
    )
    return dues
