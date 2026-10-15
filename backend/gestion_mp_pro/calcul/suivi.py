"""Suivi : échéancier des paiements, photo du jour des indicateurs (CALCULS B § 10.1 à § 10.3).

Portage de la partie calcul de `gestion_mp/api/suivi.py` (`_factures_dues`, `echeancier`,
`photographier_indicateurs`). Le bilan du mois est dans `suivi_bilan.py`, l'état de livraison
d'un bon (courriel du lundi) dans `suivi_livraison.py`. Les lignes lues en base arrivent en
petites dataclasses ; la date du jour est un paramètre.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field

from gestion_mp_pro.calcul.constantes import JOURS_PAR_AN
from gestion_mp_pro.calcul.fournisseurs import PerformanceReception, performance_receptions
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.pilotage import cockpit
from gestion_mp_pro.calcul.pilotage_valeurs import Cockpit
from gestion_mp_pro.calcul.stock import etat_stock

REGLEES_AU_PLUS = 300
"""Sans période, l'échéancier ne rend que les 300 règlements les plus récents (et le dit)."""
RAISON_AVOIR = "réglée, réception annulée : avoir à demander"
"""Une facture réglée dont toutes les réceptions sont annulées."""
RAISON_PLUS_DUE = "réception annulée : plus due"
"""Une facture non réglée dont toutes les réceptions sont annulées."""


# ── Échéancier ───────────────────────────────────────────────────────────────


@dataclass
class PeseeFacturee:
    """Une ligne d'une réception qui porte une facture (statut de la réception en base)."""

    facture_id: int
    statut: str
    quantite_pesee: float
    prix: float
    qualite: str = ""


@dataclass
class FacturesDues:
    """`_factures_dues` : l'apporté par facture, les annulées, celles en attente."""

    apporte: dict[int, float]
    annulees: set[int]
    en_attente: set[int]


def factures_dues(lignes: list[PeseeFacturee]) -> FacturesDues:
    """Pour chaque facture, ce que ses réceptions validées ont apporté (Σ pesée × prix, lignes
    non refusées) ; celles dont toutes les réceptions sont annulées (plus dues) ; celles qui ne
    portent que des brouillons (pas encore dues)."""
    apporte: dict[int, float] = defaultdict(float)
    validees: set[int] = set()
    brouillons: set[int] = set()
    toutes: set[int] = set()
    for x in lignes:
        toutes.add(x.facture_id)
        if x.statut == "validee":
            validees.add(x.facture_id)
            if x.qualite != "refuse":
                apporte[x.facture_id] += x.quantite_pesee * x.prix
        elif x.statut == "brouillon":
            brouillons.add(x.facture_id)
    return FacturesDues(dict(apporte), toutes - validees - brouillons, brouillons - validees)


@dataclass
class FactureAPayer:
    """Une facture fournisseur lue en base (`montant` : saisi, ou None / 0)."""

    id: int
    fournisseur: str
    numero: str
    devise: str
    montant: float | None = None
    echeance: dt.date | None = None
    payee_le: dt.date | None = None


@dataclass
class FraisAPayer:
    """Un frais d'importation lu en base (en MAD), avec le n° de son dossier."""

    id: int
    poste: str
    dossier: str
    montant: float
    prestataire: str = ""
    piece: str = ""
    echeance: dt.date | None = None
    payee_le: dt.date | None = None


@dataclass
class Echeance:
    """Une pièce de l'échéancier (clés de la route ; dates en `date`, ISO à l'API)."""

    id: int
    objet: str
    genre: str
    tiers: str
    piece: str
    montant: float
    estime: bool
    devise: str
    montant_mad: float
    date: dt.date | None = None
    payee_le: dt.date | None = None
    raison: str | None = None
    en_retard: bool | None = None


@dataclass
class Echeancier:
    """Ce qu'il faudra payer, et quand (clés de la route `GET /echeancier`)."""

    lignes: list[Echeance]
    par_mois: dict[str, float]
    echu_mad: float
    echues: int
    a_dater: list[Echeance]
    a_dater_mad: float
    reglees: list[Echeance]
    ecartees: list[Echeance]
    total_mad: float


def en_mad(montant: float, devise: str, taux: dict[str, float]) -> float:
    """Un montant en dirhams au taux courant de la devise (1 à défaut)."""
    return montant * (1 if devise == "MAD" else taux.get(devise, 1))


def _facture(f: FactureAPayer, apporte: dict[int, float], taux: dict[str, float]) -> Echeance:
    montant = f.montant or apporte.get(f.id, 0.0)
    return Echeance(
        id=f.id,
        objet="facture",
        genre="Facture fournisseur",
        tiers=f.fournisseur,
        piece=f.numero,
        montant=montant,
        estime=not f.montant and montant > 0,
        devise=f.devise,
        montant_mad=en_mad(montant, f.devise, taux),
    )


def _frais(ch: FraisAPayer) -> Echeance:
    return Echeance(
        id=ch.id,
        objet="frais",
        genre=f"Frais d'importation ({ch.poste})",
        tiers=ch.prestataire or "—",
        piece=f"{ch.dossier} · {ch.piece}".strip(" ·"),
        montant=ch.montant,
        estime=False,
        devise="MAD",
        montant_mad=ch.montant,
    )


@dataclass
class _Classement:
    lignes: list[Echeance] = field(default_factory=list)
    a_dater: list[Echeance] = field(default_factory=list)
    reglees: list[Echeance] = field(default_factory=list)
    ecartees: list[Echeance] = field(default_factory=list)


def _classer_factures(
    factures: list[FactureAPayer], dues: FacturesDues, taux: dict[str, float], c: _Classement
) -> None:
    for f in factures:
        x = _facture(f, dues.apporte, taux)
        if f.id in dues.en_attente:
            continue
        if f.id in dues.annulees:
            if f.payee_le:
                x.payee_le, x.raison = f.payee_le, RAISON_AVOIR
                c.ecartees.append(x)
            elif x.montant > 0:
                x.raison = RAISON_PLUS_DUE
                c.ecartees.append(x)
        elif f.payee_le:
            x.date, x.payee_le = f.echeance, f.payee_le
            c.reglees.append(x)
        elif f.echeance:
            x.date = f.echeance
            c.lignes.append(x)
        elif x.montant > 0:
            c.a_dater.append(x)


def _classer_frais(frais: list[FraisAPayer], c: _Classement) -> None:
    for ch in frais:
        x = _frais(ch)
        if ch.payee_le:
            x.date, x.payee_le = ch.echeance, ch.payee_le
            c.reglees.append(x)
        elif ch.echeance:
            x.date = ch.echeance
            c.lignes.append(x)
        elif ch.montant > 0:
            # Dû sans date connue, le dossier fût-il clos : clore fige le coût, pas le paiement.
            c.a_dater.append(x)


def _jour(x: Echeance) -> dt.date:
    """La date d'une ligne datée (toujours posée par le classement)."""
    return x.date or dt.date.min


def _reglees(
    reglees: list[Echeance], du: dt.date | None, au: dt.date | None, au_plus: int | None
) -> list[Echeance]:
    """Les réglées par date de règlement décroissante : celles de la période (bornes incluses)
    quand `du` ou `au` est posé, sinon les `au_plus` plus récentes (`None` : toutes)."""
    if du:
        reglees = [x for x in reglees if x.payee_le is not None and x.payee_le >= du]
    if au:
        reglees = [x for x in reglees if x.payee_le is not None and x.payee_le <= au]
    reglees.sort(key=lambda x: x.payee_le or dt.date.min, reverse=True)
    return reglees if (du or au or au_plus is None) else reglees[:au_plus]


def echeancier(
    factures: list[FactureAPayer],
    frais: list[FraisAPayer],
    dues: FacturesDues,
    *,
    taux: dict[str, float],
    aujourdhui: dt.date,
    du: dt.date | None = None,
    au: dt.date | None = None,
    reglees_au_plus: int | None = REGLEES_AU_PLUS,
) -> Echeancier:
    """Ce qu'il faudra payer, et quand : factures (par id) puis frais d'importation (par id).

    Une pièce réglée en sort ; une facture sans montant saisi vaut ce que ses réceptions ont
    apporté (« estimé ») ; une facture dont toutes les réceptions sont annulées est écartée
    (réglée : un avoir est à demander) ; une facture qui ne porte que des brouillons n'est pas
    encore due. L'échu se compte sur toutes les échéances, **avant** le filtre `du`/`au`.

    `du`/`au` bornent les échéances par leur date, et les réglées par leur **date de règlement**
    (bornes incluses). Sans période, `reglees` garde les `reglees_au_plus` plus récentes (300 ;
    `None` : toutes) ; avec une période, toutes celles de la période.
    """
    c = _Classement()
    _classer_factures(factures, dues, taux, c)
    _classer_frais(frais, c)
    lignes = c.lignes
    echues = [x for x in lignes if _jour(x) < aujourdhui]
    if du:
        lignes = [x for x in lignes if _jour(x) >= du]
    if au:
        lignes = [x for x in lignes if _jour(x) <= au]
    lignes.sort(key=_jour)
    reglees = _reglees(c.reglees, du, au, reglees_au_plus)
    par_mois: dict[str, float] = defaultdict(float)
    for x in lignes:
        par_mois[_jour(x).strftime("%Y-%m")] += x.montant_mad
    for x in lignes:
        x.en_retard = _jour(x) < aujourdhui
    return Echeancier(
        lignes=lignes,
        par_mois=dict(sorted(par_mois.items())),
        echu_mad=sum(x.montant_mad for x in echues),
        echues=len(echues),
        a_dater=c.a_dater,
        a_dater_mad=sum(x.montant_mad for x in c.a_dater),
        reglees=reglees,
        ecartees=c.ecartees,
        total_mad=sum(x.montant_mad for x in lignes),
    )


# ── Photo du jour des indicateurs ────────────────────────────────────────────


@dataclass
class IndicateursDuJour:
    """La photo du jour des grands indicateurs (JSON de `indicateur_jour`)."""

    valeur_stock_mad: float
    couverture_jours: float
    ruptures: int
    critiques: int
    urgents: int
    a_commander_mad: float
    commandes_en_cours_mad: float
    otif_moyen: float | None


def indicateurs_du_cockpit(
    c: Cockpit, performances: list[PerformanceReception], jour: dt.date
) -> IndicateursDuJour:
    """Les indicateurs photographiés : ceux du Cockpit, et l'OTIF moyen des réceptions notées
    des douze derniers mois (une réception, une voix — pas la moyenne des fournisseurs)."""
    depuis = jour - dt.timedelta(days=JOURS_PAR_AN)
    notes = [
        x.otif
        for x in performances
        if x.otif is not None and x.date_reception and depuis < x.date_reception <= jour
    ]
    return IndicateursDuJour(
        valeur_stock_mad=c.stock.valeur_mad,
        couverture_jours=c.stock.couverture_ponderee_jours,
        ruptures=c.stock.ruptures,
        critiques=c.stock.critiques,
        urgents=c.stock.urgents,
        a_commander_mad=c.achats.budget_a_commander_mad,
        commandes_en_cours_mad=c.achats.montant_bc_en_cours_mad,
        otif_moyen=sum(notes) / len(notes) if notes else None,
    )


def photographier_indicateurs(donnees: Donnees, jour: dt.date) -> IndicateursDuJour:
    """La photo du jour (`photographier_indicateurs`, partie calcul) : état du stock, Cockpit
    (sans coûts rendus) et performances des réceptions sur les données d'aujourd'hui."""
    lignes = etat_stock(donnees, jour)
    return indicateurs_du_cockpit(
        cockpit(donnees, jour, lignes), performance_receptions(donnees), jour
    )
