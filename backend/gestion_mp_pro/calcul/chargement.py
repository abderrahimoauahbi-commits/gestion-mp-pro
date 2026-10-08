"""Les calculs purs du chargeur (`gestion_mp/depot.py`, CALCULS A § 4) : ce que la base dit,
traduit pour le moteur. Le chargeur PRO (`services/donnees_moteur.py`, lot S4) lit la base en
requêtes groupées et passe ici les lignes lues ; rien ici ne touche la base.

- statut d'un bon pour le moteur, qualité d'une ligne reçue, code d'un motif de retour ;
- répartition au prorata des pesées d'un lot (retours, quarantaine) ;
- histoire du plan d'une qualité (`versions_du_plan`, `arret_sans_histoire`) ;
- appariement des entrées de réception à leurs lignes ;
- le journal signé de la base (une ligne par lot et magasin) traduit en journal du moteur
  (quantité positive, signe porté par le type, un transfert en une seule ligne).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from gestion_mp_pro.calcul.constantes import TYPES_MOUVEMENT
from gestion_mp_pro.calcul.modele import Mouvement, VersionPlan

STATUTS_MOTEUR = {
    "brouillon": "Brouillon",
    "a_approuver": "Brouillon",
    "envoyee": "Envoyée",
    "confirmee": "Confirmée",
    "soldee": "Soldée",
    "annulee": "Annulée",
}
"""Statut d'un bon en base → statut du moteur."""
QUALITE_MOTEUR = {"conforme": "Conforme", "reserve": "Réserve", "refuse": "Refusé"}
"""Qualité d'une ligne reçue en base → libellé du moteur."""
TYPE_MOTEUR = {
    "OUVERTURE": "STOCK_INITIAL",
    "RECEPTION": "ENTREE_RECEPTION",
    "SORTIE": "SORTIE_PROD",
    "RETOUR_MACHINE": "RETOUR_PRODUCTION",
    "RETOUR_FOURNISSEUR": "RETOUR_FOURNISSEUR",
    "AJUSTEMENT": "AJUSTEMENT_INVENTAIRE",
    "TRANSFERT": "TRANSFERT_MAGASIN",
}
"""Type de mouvement en base → code du moteur."""
CODES_MOTIF = {
    "Reliquat de fin d'ordre": "R1",
    "Changement de série / arrêt machine": "R2",
    "Erreur de prélèvement": "R4",
    "Non-conformité qualité": "R3",
    "Excédent de réception": "R5",
    "Bobines endommagées": "R6",
    "Refus après quarantaine": "R3",
}
"""Libellé d'un motif de retour → code R1…R6 (`api/operations.CODES_MOTIF`)."""
DECIMALES_PESEE = 6


def statut_moteur(statut: str, numero: str | None, prix_confirmes: list[bool]) -> str:
    """Un bon parti se lit à son numéro : qu'il repasse par la direction ne le refait pas
    brouillon (« Confirmée » si tous ses prix le sont, sinon « Envoyée »)."""
    if numero and statut in ("brouillon", "a_approuver"):
        return "Confirmée" if prix_confirmes and all(prix_confirmes) else "Envoyée"
    return STATUTS_MOTEUR[statut]


def code_motif(motif: str | None) -> str:
    """Le code R1…R6 d'un motif de retour, d'après son libellé (ou son code s'il est écrit)."""
    texte = (motif or "").strip()
    if len(texte) >= 2 and texte[0] == "R" and texte[1].isdigit():  # noqa: PLR2004
        return texte[:2]
    return CODES_MOTIF.get(texte, "")


@dataclass
class LigneRecue:
    """Une ligne de réception entrée : (id, ligne de commande, lot, pesée, qualité)."""

    id: int
    commande_ligne_id: int | None
    lot_id: int | None
    quantite_pesee: float
    qualite: str


def au_prorata(par_lot: dict[int, float], lignes: list[LigneRecue]) -> dict[int, float]:
    """Répartit une quantité connue au lot entre les lignes reçues de ce lot, au prorata de
    leur pesée (un lot reçu en deux camions), sans dépasser ce qu'elles ont apporté."""
    pese_du_lot: dict[int, float] = defaultdict(float)
    for ligne in lignes:
        if ligne.lot_id in par_lot:
            pese_du_lot[ligne.lot_id] += ligne.quantite_pesee
    part: dict[int, float] = {}
    for ligne in lignes:
        lot = ligne.lot_id
        if lot is not None and lot in par_lot and pese_du_lot[lot] > 0:
            part[ligne.id] = min(
                ligne.quantite_pesee, par_lot[lot] * ligne.quantite_pesee / pese_du_lot[lot]
            )
    return part


def recu_par_ligne(lignes: list[LigneRecue], retours: dict[int, float]) -> dict[int, float]:
    """Ce que chaque ligne de commande a reçu, net de ce qui en est reparti chez le
    fournisseur (`retours` : par ligne de réception, voir `au_prorata`)."""
    recu: dict[int, float] = defaultdict(float)
    for ligne in lignes:
        if ligne.commande_ligne_id is not None:
            recu[ligne.commande_ligne_id] += ligne.quantite_pesee - retours.get(ligne.id, 0.0)
    return recu


def _version(quand: datetime | None, plan: dict[str, object], depuis: date | None) -> VersionPlan:
    saisons = plan.get("c", [1.0] * 12)
    return VersionPlan(
        quand=quand,
        base_mensuelle=float(plan.get("b", 0.0)),  # type: ignore[arg-type]
        saisonnalite=[float(x) for x in saisons],  # type: ignore[attr-defined]
        actif=bool(plan.get("a", True)),
        depuis=depuis,
    )


def versions_du_plan(
    brut: list[tuple[datetime, dict[str, object], dict[str, object]]], ouverture: date | None
) -> list[VersionPlan]:
    """L'histoire du plan d'une qualité : le plan d'avant le premier changement (depuis
    toujours), puis chaque plan enregistré ; seule une nouvelle base déplace l'origine de la
    croissance."""
    if not brut:
        return []
    resultat = [_version(None, brut[0][1], ouverture)]
    for quand, _, apres in brut:
        precedent = resultat[-1]
        nouvelle = _version(quand, apres, quand.date())
        if nouvelle.base_mensuelle == precedent.base_mensuelle:
            nouvelle.depuis = precedent.depuis
        resultat.append(nouvelle)
    return resultat


def arret_sans_histoire(versions: list[VersionPlan], dernier: date | None) -> list[VersionPlan]:
    """Une qualité arrêtée avant que l'arrêt ne soit tracé l'a été après son dernier tissage :
    son plan vaut jusqu'au mois de son dernier ordre (rien s'il n'y en a pas)."""
    if dernier is None:
        arret = datetime.min  # noqa: DTZ901 — instants du moteur : heure de l'usine
    else:
        suivant = date(dernier.year + dernier.month // 12, dernier.month % 12 + 1, 1)
        arret = datetime.combine(suivant, datetime.min.time())
    if len(versions) > 1 and versions[1].quand is not None:
        arret = min(arret, versions[1].quand)
    avant = versions[0]
    return [
        VersionPlan(
            quand=None,
            base_mensuelle=avant.base_mensuelle,
            saisonnalite=avant.saisonnalite,
            actif=True,
            depuis=avant.depuis,
        ),
        VersionPlan(
            quand=arret,
            base_mensuelle=avant.base_mensuelle,
            saisonnalite=avant.saisonnalite,
            actif=False,
            depuis=avant.depuis,
        ),
        *versions[1:],
    ]


@dataclass
class EntreeLue:
    """Une entrée de réception du journal, telle que l'appariement la lit."""

    id: int
    reception_id: int | None
    lot_id: int | None
    contrepasse_id: int | None
    jour: date
    quantite: float


@dataclass
class LigneDeReception:
    """Une ligne de réception non refusée qui a un lot."""

    id: int
    reception_id: int
    lot_id: int
    jour: date
    quantite_pesee: float


def lignes_des_receptions(
    lignes: list[LigneDeReception], entrees: list[EntreeLue]
) -> dict[int, int]:
    """{n° du mouvement : n° de ligne de réception} : les entrées d'une réception sur un lot
    s'apparient dans l'ordre à ses lignes sur ce lot ; une entrée reprise sans réception
    retrouve sa ligne par lot, date et poids ; une annulation reprend la ligne de l'entrée
    qu'elle défait. `lignes` et `entrees` dans l'ordre de leurs numéros."""
    par_reception: dict[tuple[int, int], list[int]] = defaultdict(list)
    par_pesee: dict[tuple[int, date, float], list[int]] = defaultdict(list)
    for ligne in lignes:
        par_reception[(ligne.reception_id, ligne.lot_id)].append(ligne.id)
        par_pesee[(ligne.lot_id, ligne.jour, round(ligne.quantite_pesee, DECIMALES_PESEE))].append(
            ligne.id
        )
    resultat: dict[int, int] = {}
    prises: set[int] = set()
    for e in entrees:
        if e.contrepasse_id is not None:
            if e.contrepasse_id in resultat:
                resultat[e.id] = resultat[e.contrepasse_id]
            continue
        lot = e.lot_id if e.lot_id is not None else -1
        candidates = (
            par_reception.get((e.reception_id, lot), [])
            if e.reception_id is not None
            else par_pesee.get((lot, e.jour, round(e.quantite, DECIMALES_PESEE)), [])
        )
        libre = next((x for x in candidates if x not in prises), None)
        if libre is not None:
            resultat[e.id] = libre
            prises.add(libre)
    return resultat


@dataclass
class EcritureLue:
    """Une écriture du journal de la base : quantité signée, un lot, un magasin."""

    id: int
    type: str
    date: date
    reference: str
    quantite: float
    magasin: str
    prix: float = 0.0
    devise: str = "MAD"
    document_numero: str = ""
    lot: str = ""
    numero_of: str = ""
    motif: str = ""
    auteur: str = ""
    fournisseur: str = ""
    contrepasse_id: int | None = None
    cours: float = 0.0
    paire: int | None = None
    ligne_reception_id: int | None = None


def _traduire(x: EcritureLue, quantite: float, source: str, destination: str) -> Mouvement:
    return Mouvement(
        date=x.date,
        type=TYPE_MOTEUR[x.type],
        reference=x.reference,
        quantite=quantite,
        prix_unite=x.prix,
        devise=x.devise or "MAD",
        total_devise=quantite * x.prix,
        reference_doc=x.document_numero,
        lot_fournisseur=x.lot,
        magasin_source=source,
        magasin_destination=destination,
        numero_of=x.numero_of,
        motif_retour=code_motif(x.motif),
        utilisateur=x.auteur,
        fournisseur=x.fournisseur,
        id=x.id,
        contrepasse_id=x.contrepasse_id,
        cours=x.cours or 0.0,
        ligne_reception_id=x.ligne_reception_id,
    )


def journal_du_moteur(ecritures: list[EcritureLue]) -> list[Mouvement]:
    """Le journal du moteur, dans l'ordre (date, n°) des écritures de la base : un transfert
    (deux écritures appariées) devient une seule ligne, de la source vers la destination."""
    resultat: list[Mouvement] = []
    paires: dict[int, list[EcritureLue]] = defaultdict(list)
    for x in ecritures:
        if x.type == "TRANSFERT":
            cle = x.paire or -x.id
            paires[cle].append(x)
            if len(paires[cle]) < 2:  # noqa: PLR2004 — une paire : deux écritures
                continue
            a, b = paires.pop(cle)
            source, destination = (a, b) if a.quantite < 0 else (b, a)
            resultat.append(
                _traduire(source, abs(source.quantite), source.magasin, destination.magasin)
            )
        elif TYPES_MOUVEMENT[TYPE_MOTEUR[x.type]][1] < 0:
            resultat.append(_traduire(x, -x.quantite, x.magasin, ""))
        else:
            resultat.append(_traduire(x, x.quantite, "", x.magasin))
    return resultat
