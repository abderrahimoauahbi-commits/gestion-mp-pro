"""Bilan matières du mois : flux en kilos et en dirhams, stocks, activité (CALCULS B § 10.4).

Portage de la partie calcul de `gestion_mp/api/suivi.py` (`mois_du_bilan`, `bilan`). Les flux
se lisent sur le journal **de la base** (quantités signées, types de la base : OUVERTURE,
RECEPTION, SORTIE, RETOUR_MACHINE, RETOUR_FOURNISSEUR, AJUSTEMENT, TRANSFERT), valorisés au
coût de chaque écriture (`couts_du_journal` à la fin du mois) ; les stocks et valeurs de début
et de fin passent par le moteur (`a_la_date`, `etat_stock`, `valorisation`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.calcul.fournisseurs import performance_receptions
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.production import ConsommationOrdre
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.calcul.valorisation import couts_du_journal, valorisation

ANNEE_MIN, ANNEE_MAX = 2000, 2100
"""Les années qu'un bilan accepte."""
DECEMBRE = 12
"""Le dernier mois : le suivant est janvier de l'année d'après."""
VERS_LES_MACHINES = ("SORTIE", "RETOUR_MACHINE")
"""Les écritures dont le coût entre dans la consommation (comme `couts_du_journal`)."""
ECARTS_AFFICHES = 8
"""Le bilan montre les 8 ordres aux plus grands écarts relatifs."""
ZERO_KG = 1e-9
"""Une annulation sous ce seuil n'est pas détaillée."""


@dataclass
class MouvementBase:
    """Une écriture de la table `mouvement` (quantité **signée**, type de la base), dans
    l'ordre de lecture (id croissant)."""

    id: int
    type: str
    quantite: float
    date_effet: date
    contrepasse_id: int | None = None


@dataclass
class FabricationBase:
    """Une fabrication d'un bon de sortie : qualité, m², statut et date du bon."""

    qualite: str
    m2: float
    statut_bon: str
    date_bon: date


@dataclass
class CommandeBase:
    """Un bon de commande : n° (None tant qu'il n'est pas parti), date, statut de la base."""

    numero: str | None
    date_commande: date | None
    statut: str


@dataclass
class ReceptionBase:
    """Une réception : statut de la base et date."""

    statut: str
    date: date


@dataclass
class BilanMois:
    """Le bilan d'un mois (clés de `bilan`)."""

    mois: str
    stock_debut_kg: float
    stock_fin_kg: float
    entrees_kg: float
    valeur_entrees_mad: float
    valeur_debut_mad: float
    valeur_fin_mad: float
    consommation_mad: float
    valeur_autres_mad: float
    ecart_valorisation_mad: float
    stock_machine_kg: float
    valeur_machine_mad: float
    sorties_kg: float
    retours_machine_kg: float
    retours_fournisseur_kg: float
    ajustements_kg: float
    ouvertures_kg: float
    annulations_kg: float
    annulations: dict[str, float]
    m2_par_qualite: dict[str, float]
    m2_total: float
    commandes: int
    receptions: int
    otif: float | None
    receptions_notees: int
    ordres: int
    ecarts_ordres: list[ConsommationOrdre]
    ruptures: int
    critiques: int


def mois_du_bilan(annee: int, mois: int, aujourdhui: date) -> date:
    """Le premier jour du mois demandé — un vrai mois, pas dans le futur (E-03) ; sinon
    `ValueError` (« Mois invalide : AAAA-MM, pas dans le futur. »)."""
    if not (ANNEE_MIN <= annee <= ANNEE_MAX and 1 <= mois <= DECEMBRE) or (annee, mois) > (
        aujourdhui.year,
        aujourdhui.month,
    ):
        raise ValueError("Mois invalide : AAAA-MM, pas dans le futur.")
    return date(annee, mois, 1)


@dataclass
class _Flux:
    flux: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    valeurs: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    annulations: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    valeur_annulations: float = 0.0
    stock_debut: float = 0.0
    stock_fin: float = 0.0


def _receptions_annulees(mvt: list[MouvementBase], debut: date, fin: date) -> set[int]:
    """Les réceptions du mois annulées dans le mois : ni leurs kilos ni leurs dirhams ne
    sont des entrées, et la paire s'annule (une annulation prend la date qu'elle défait)."""
    annulee_le = {x.contrepasse_id: x.date_effet for x in mvt if x.contrepasse_id is not None}
    return {
        x.id
        for x in mvt
        if x.type == "RECEPTION"
        and x.contrepasse_id is None
        and debut <= x.date_effet < fin
        and x.id in annulee_le
        and debut <= annulee_le[x.id] < fin
    }


def _flux(mvt: list[MouvementBase], debut: date, fin: date, cout: dict[int, float]) -> _Flux:
    """Les flux du mois par type, hors transferts ; une annulation a sa ligne à part."""
    annulees = _receptions_annulees(mvt, debut, fin)
    r = _Flux()
    for x in mvt:
        t, q, jour, annule = x.type, x.quantite, x.date_effet, x.contrepasse_id
        if jour < debut:
            r.stock_debut += q
        if jour < fin:
            r.stock_fin += q
        if not (debut <= jour < fin) or t == "TRANSFERT" or x.id in annulees or annule in annulees:
            continue
        valeur = q * cout.get(x.id, 0.0)
        if annule is not None:
            r.annulations[t] += q
            if t in VERS_LES_MACHINES:
                r.valeurs["CONSOMMATION"] += valeur
            else:
                r.valeur_annulations += valeur
        else:
            r.flux[t] += q
            r.valeurs["CONSOMMATION" if t in VERS_LES_MACHINES else t] += valeur
    return r


@dataclass
class _Activite:
    m2: dict[str, float]
    commandes: int
    receptions: int
    otif: list[int]
    ordres: list[ConsommationOrdre]
    ecarts: list[ConsommationOrdre]


def _activite(
    donnees: Donnees,
    debut: date,
    fin: date,
    entrees: tuple[list[FabricationBase], list[CommandeBase], list[ReceptionBase]],
    ordres: list[ConsommationOrdre],
) -> _Activite:
    """m² fabriqués (bons validés), bons émis non annulés, réceptions validées, OTIF et
    ordres validés dont la première sortie tombe dans le mois."""
    fabrications, commandes, receptions = entrees
    m2: dict[str, float] = defaultdict(float)
    for f in fabrications:
        if f.statut_bon == "valide" and debut <= f.date_bon < fin:
            m2[f.qualite] += f.m2
    nb_commandes = sum(
        1
        for c in commandes
        if c.date_commande is not None
        and debut <= c.date_commande < fin
        and c.numero is not None
        and c.statut != "annulee"
    )
    nb_receptions = sum(1 for r in receptions if r.statut == "validee" and debut <= r.date < fin)
    perf = [
        x
        for x in performance_receptions(donnees)
        if x.date_reception and debut <= x.date_reception < fin
    ]
    valides = {o.numero for o in donnees.ordres}
    du_mois = [x for x in ordres if x.numero_of in valides and x.debut and debut <= x.debut < fin]
    ecarts = sorted(
        (x for x in du_mois if x.ecart_relatif is not None),
        key=lambda x: -abs(x.ecart_relatif or 0.0),
    )[:ECARTS_AFFICHES]
    otif = [x.otif for x in perf if x.otif is not None]
    return _Activite(m2, nb_commandes, nb_receptions, otif, du_mois, ecarts)


@dataclass
class _Valeurs:
    debut: float
    fin: float
    machine_kg: float
    machine_mad: float
    ruptures: int
    critiques: int


def _valeurs(
    donnees: Donnees, au_fin: Donnees, debut: date, jour_calcul: date, aujourdhui: date
) -> _Valeurs:
    """La valeur des magasins au CMUP la veille du mois et à la fin du mois (le fil monté,
    connu pour le mois en cours seulement, à part) ; ruptures et critiques à la fin du mois."""
    lignes = etat_stock(au_fin, jour_calcul)
    veille = debut - timedelta(days=1)
    au_debut = a_la_date(donnees, veille, aujourdhui=aujourdhui)
    valeur_debut = sum(
        v.valeur_magasin_mad
        for v in valorisation(au_debut, etat_stock(au_debut, veille))
        if v.stock_magasin > 0
    )
    fin_valorisee = valorisation(au_fin, lignes)
    valeur_fin = sum(v.valeur_magasin_mad for v in fin_valorisee if v.stock_magasin > 0)
    machine_kg = sum(v.stock_machine for v in fin_valorisee) if au_fin.montage_connu else 0.0
    machine_mad = sum(v.valeur_machine_mad for v in fin_valorisee) if au_fin.montage_connu else 0.0
    return _Valeurs(
        debut=valeur_debut,
        fin=valeur_fin,
        machine_kg=machine_kg,
        machine_mad=machine_mad,
        ruptures=sum(1 for x in lignes if "RUPTURE" in x.statut),
        critiques=sum(1 for x in lignes if "CRITIQUE" in x.statut),
    )


def bilan(
    donnees: Donnees,
    *,
    annee: int,
    mois: int,
    aujourdhui: date,
    mouvements: list[MouvementBase],
    fabrications: list[FabricationBase],
    commandes: list[CommandeBase],
    receptions: list[ReceptionBase],
    ordres: list[ConsommationOrdre],
) -> BilanMois:
    """Le bilan matières du mois (`bilan`) : `donnees` d'aujourd'hui, journal de la base,
    fabrications, bons, réceptions et ordres lus comme l'écran Sorties (prévu perte comprise).

    Équation (vraie par construction) : fin = début + entrées + ouvertures − sorties + retours
    machines − retours fournisseur + ajustements + annulations ; en valeur, l'écart de
    valorisation est ce que le coût moyen laisse en route.
    """
    debut = mois_du_bilan(annee, mois, aujourdhui)
    fin = date(annee + (mois == DECEMBRE), mois % DECEMBRE + 1, 1)
    jour_calcul = min(fin - timedelta(days=1), aujourdhui)
    au_fin = a_la_date(donnees, jour_calcul, aujourdhui=aujourdhui)
    f = _flux(mouvements, debut, fin, couts_du_journal(au_fin).unitaire)
    act = _activite(donnees, debut, fin, (fabrications, commandes, receptions), ordres)
    v = _valeurs(donnees, au_fin, debut, jour_calcul, aujourdhui)
    return _bilan_mois(debut, f, act, v)


def _bilan_mois(debut: date, f: _Flux, act: _Activite, v: _Valeurs) -> BilanMois:
    """Le bilan assemblé : kilos par type, valeurs, activité."""
    consommation = -f.valeurs["CONSOMMATION"]
    autres = (
        f.valeurs["OUVERTURE"]
        + f.valeurs["AJUSTEMENT"]
        + f.valeurs["RETOUR_FOURNISSEUR"]
        + f.valeur_annulations
    )
    kg = f.flux
    return BilanMois(
        mois=debut.strftime("%m/%Y"),
        stock_debut_kg=f.stock_debut,
        stock_fin_kg=f.stock_fin,
        entrees_kg=kg["RECEPTION"],
        valeur_entrees_mad=f.valeurs["RECEPTION"],
        valeur_debut_mad=v.debut,
        valeur_fin_mad=v.fin,
        consommation_mad=consommation,
        valeur_autres_mad=autres,
        ecart_valorisation_mad=v.fin - (v.debut + f.valeurs["RECEPTION"] - consommation + autres),
        stock_machine_kg=v.machine_kg,
        valeur_machine_mad=v.machine_mad,
        sorties_kg=-kg["SORTIE"],
        retours_machine_kg=kg["RETOUR_MACHINE"],
        retours_fournisseur_kg=-kg["RETOUR_FOURNISSEUR"],
        ajustements_kg=kg["AJUSTEMENT"],
        ouvertures_kg=kg["OUVERTURE"],
        annulations_kg=sum(f.annulations.values()),
        annulations={t: q for t, q in f.annulations.items() if abs(q) > ZERO_KG},
        m2_par_qualite=dict(sorted(act.m2.items())),
        m2_total=sum(act.m2.values()),
        commandes=act.commandes,
        receptions=act.receptions,
        otif=sum(act.otif) / len(act.otif) if act.otif else None,
        receptions_notees=len(act.otif),
        ordres=len(act.ordres),
        ecarts_ordres=act.ecarts,
        ruptures=v.ruptures,
        critiques=v.critiques,
    )
