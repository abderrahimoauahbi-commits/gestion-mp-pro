"""L'archive des pesées (route 176) et le poids des bobines (177) : la traçabilité qualité, lot
par lot, et le poids moyen d'une bobine réception après réception (CALCULS B § 5 ;
`gestion_mp/api/pilotage.py` B73, B74 ; A-20 corrigé).

- Pesées : chaque ligne des réceptions non annulées, la plus récente d'abord, avec son bon, son
  lot et son magasin (liens de l'écran) ; « Annoncé BL » est le BL seul, et l'écart dit à quoi il
  se compare (le BL, sinon le reste à livrer quand on pèse au moins ce reste) ; paginée par
  curseur, filtres au serveur, indicateurs sur toutes les lignes filtrées.
- Bobines : le calcul du moteur (`calcul.receptions.evolution_bobines`, parité avec Gestion MP),
  complété des identifiants (matière, réception, lot).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.receptions import ecart_bobine, evolution_bobines
from gestion_mp_pro.modeles import Fournisseur, Lot, Matiere, Reception
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.modeles.recherche import normaliser
from gestion_mp_pro.services import donnees_moteur, reglages
from gestion_mp_pro.services.receptions_lecture import (
    LigneLue,
    ReceptionResume,
    charger_receptions,
    lire_lignes,
    resume,
)

CLE = ("date", "reception_id", "-id")
"""La clé du curseur de l'archive."""


@dataclass(frozen=True)
class FiltresPesees:
    """`?q=&ecarts=&fournisseur=&qualite=&magasin=` (mêmes filtres que l'écran et le classeur)."""

    q: str = ""
    ecarts: bool = False
    fournisseur: int | None = None
    qualite: str = ""
    magasin: int | None = None


@dataclass
class Pesee:
    """Une ligne pesée de l'archive."""

    id: int
    reception_id: int
    numero: str
    date: dt.date
    statut_reception: str
    commande_id: int | None
    numero_bc: str
    fournisseur_id: int
    fournisseur: str
    receptionnaire: str
    controleur_qualite: str
    matiere_id: int
    reference: str
    designation: str
    lot_id: int | None
    lot: str
    magasin: str
    quantite_bl: Decimal
    quantite_attendue: Decimal
    quantite_pesee: Decimal
    ecart: float | None
    ecart_relatif: float | None
    compare_au: str | None
    hors_tolerance: bool
    nb_palettes: Decimal
    nb_bobines: Decimal
    poids_moyen_bobine: float | None
    poids_bobine_catalogue: Decimal
    ecart_bobine: float | None
    bobine_hors_tolerance: bool
    qualite: str
    qualite_libelle: str
    observations: str


@dataclass
class Pesees:
    """Toutes les pesées filtrées et leurs indicateurs (la route en rend une page)."""

    lignes: list[Pesee]
    tolerance: float
    tolerance_bobine: float
    kg_pesees: Decimal
    hors_tolerance: int
    non_conformes: int
    bobines_hors_tolerance: int


def _pesee(r: ReceptionResume, x: LigneLue, tol_bobine: float) -> Pesee:
    """Une pesée, de la ligne lue de sa réception."""
    controle = r.controle_par or r.validee_par
    compare = None
    if x.ecart is not None:
        compare = "bl" if x.quantite_bl else "reste"
    bobine = ecart_bobine(x.poids_moyen_bobine, float(x.poids_bobine_catalogue))
    return Pesee(
        x.id, r.id, r.libelle, r.date, r.statut, x.commande_id, x.commande, r.fournisseur_id,
        r.fournisseur, r.cree_par, controle, x.matiere_id, x.reference, x.designation, x.lot_id,
        x.lot_numero, x.magasin, x.quantite_bl, x.quantite_attendue, x.quantite_pesee, x.ecart,
        x.ecart_relatif, compare, x.hors_tolerance, x.nb_palettes, x.nb_bobines,
        x.poids_moyen_bobine, x.poids_bobine_catalogue, bobine,
        bobine is not None and abs(bobine) > tol_bobine, x.qualite, x.qualite_libelle,
        x.observations,
    )  # fmt: skip


def _passe(x: Pesee, magasin: int | None, f: FiltresPesees) -> bool:
    """Filtres de l'archive ; « écarts » : écart de pesée, de bobine, ou ligne non conforme."""
    if f.ecarts and not (
        x.hors_tolerance or x.bobine_hors_tolerance or x.qualite != QualiteReception.conforme
    ):
        return False
    if f.fournisseur is not None and x.fournisseur_id != f.fournisseur:
        return False
    if f.qualite and x.qualite != f.qualite:
        return False
    if f.magasin is not None and magasin != f.magasin:
        return False
    mots = normaliser(f.q).split()
    texte = normaliser(
        " ".join([x.numero, x.numero_bc, x.fournisseur, x.reference, x.designation, x.lot,
                  x.magasin, x.qualite_libelle])
    )  # fmt: skip
    return all(m in texte for m in mots)


def pesees(s: Session, f: FiltresPesees) -> Pesees:
    """Route 176 : l'archive filtrée, la plus récente d'abord."""
    receptions = [r for r in charger_receptions(s) if r.statut != StatutDocument.annulee]
    lu, lignes = lire_lignes(s, receptions)
    tol_bobine = reglages.nombre(s, "toler_poids_bobine")
    resultat: list[Pesee] = []
    for r in receptions:
        base = resume(s, r, lu)
        for x in lignes[r.id]:
            p = _pesee(base, x, tol_bobine)
            if _passe(p, x.magasin_id, f):
                resultat.append(p)
    resultat.sort(key=lambda p: (p.date, p.reception_id, -p.id), reverse=True)
    return Pesees(
        resultat,
        lu.tolerance_pesee,
        tol_bobine,
        sum((p.quantite_pesee for p in resultat), Decimal(0)),
        sum(1 for p in resultat if p.hors_tolerance),
        sum(1 for p in resultat if p.qualite != QualiteReception.conforme),
        sum(1 for p in resultat if p.bobine_hors_tolerance),
    )


def cle(p: Pesee) -> list[object]:
    """La clé de tri d'une pesée, pour le curseur."""
    return [p.date.isoformat(), p.reception_id, -p.id]


def apres(lignes: list[Pesee], curseur: list[object] | None) -> list[Pesee]:
    """Les pesées qui suivent le curseur (ordre décroissant) ; un curseur illisible : 422."""
    if not curseur:
        return lignes
    forme = (
        len(curseur) == len(CLE)
        and isinstance(curseur[0], str)
        and all(isinstance(x, int) for x in curseur[1:])
    )
    if not forme:
        raise Refus.saisie(
            "Curseur de pagination illisible : recharger la liste.", code="curseur_invalide"
        )
    borne = (str(curseur[0]), int(str(curseur[1])), int(str(curseur[2])))
    return [x for x in lignes if (x.date.isoformat(), x.reception_id, -x.id) < borne]


# ── Poids des bobines ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FiltresBobines:
    """`?q=&ecarts=&matiere=&fournisseur=`."""

    q: str = ""
    ecarts: bool = False
    matiere: int | None = None
    fournisseur: int | None = None


@dataclass
class Mesure:
    """Un poids moyen de bobine constaté à une réception."""

    date: dt.date | None
    reception_id: int | None
    reception: str
    fournisseur: str
    lot_id: int | None
    lot: str
    quantite_pesee: float
    nb_bobines: float
    poids_bobine: float
    ecart_catalogue: float | None


@dataclass
class EvolutionLue:
    """Le poids de la bobine d'une matière, réception après réception."""

    matiere_id: int | None
    reference: str
    fournisseur: str
    poids_catalogue: float
    receptions: int
    premier: float
    dernier: float
    derniere_date: dt.date | None
    evolution: float | None
    moyenne: float
    mini: float
    maxi: float
    ecart_catalogue: float | None
    hors_tolerance: bool
    historique: list[Mesure] = field(default_factory=list)


@dataclass
class EvolutionBobines:
    """Route 177 : les matières suivies et leurs indicateurs."""

    tolerance: float
    lignes: list[EvolutionLue]
    hors_tolerance: int
    alourdies: int
    allegees: int


def bobines(s: Session, f: FiltresBobines) -> EvolutionBobines:
    """Route 177 : le calcul du moteur, filtré, avec les identifiants pour les liens."""
    d = donnees_moteur.charger(s, avec_journal=False)
    tol = d.parametres.toler_poids_bobine
    matieres = dict(s.execute(select(Matiere.reference, Matiere.id)).tuples().all())
    receptions = {
        r.numero: r.id for r in s.scalars(select(Reception).where(Reception.numero.is_not(None)))
    }
    lots = {(m, n): i for i, m, n in s.execute(select(Lot.id, Lot.matiere_id, Lot.numero)).tuples()}
    lignes: list[EvolutionLue] = []
    for e in evolution_bobines(d):
        mid = matieres.get(e.reference)
        historique = [
            Mesure(
                m.date,
                receptions.get(m.reception),
                m.reception,
                m.fournisseur,
                lots.get((mid or 0, m.lot)),
                m.lot,
                m.quantite_pesee,
                m.nb_bobines,
                m.poids_bobine,
                ecart_bobine(m.poids_bobine, e.poids_catalogue),
            )  # fmt: skip
            for m in reversed(e.historique)
        ]
        lignes.append(
            EvolutionLue(
                mid,
                e.reference,
                e.fournisseur,
                e.poids_catalogue,
                e.receptions,
                e.premier,
                e.dernier,
                e.derniere_date,
                e.evolution if e.receptions > 1 else None,
                e.moyenne,
                e.mini,
                e.maxi,
                e.ecart_catalogue,
                e.hors_tolerance,
                historique,
            )  # fmt: skip
        )
    nom = s.scalar(select(Fournisseur.nom).where(Fournisseur.id == f.fournisseur))
    lignes = [x for x in lignes if _bobine_passe(x, f, nom)]
    return EvolutionBobines(
        tol,
        lignes,
        sum(1 for x in lignes if x.hors_tolerance),
        sum(1 for x in lignes if x.receptions > 1 and (x.evolution or 0) > tol),
        sum(1 for x in lignes if x.receptions > 1 and (x.evolution or 0) < -tol),
    )


def _bobine_passe(x: EvolutionLue, f: FiltresBobines, fournisseur: str | None) -> bool:
    """Filtres du poids des bobines."""
    if f.ecarts and not x.hors_tolerance:
        return False
    if f.matiere is not None and x.matiere_id != f.matiere:
        return False
    if f.fournisseur is not None and x.fournisseur != fournisseur:
        return False
    mots = normaliser(f.q).split()
    texte = normaliser(f"{x.reference} {x.fournisseur}")
    return all(m in texte for m in mots)
