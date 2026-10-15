"""La proposition de sortie : ce que les recettes demandent, et dans quels lots le prendre
(REGLES B.2.3 : P10–P14 ; DEFAUTS D-11 ; API-PRO 134). N'écrit rien.

Besoin par matière = Σ kg/m² × m² × (1 + perte) sur les qualités demandées — **perte
comprise**, comme Production et besoins ; une matière qui sert plusieurs qualités n'apparaît
qu'une fois (`par_qualite`). Les lots sont pris du plus ancien au plus récent (FIFO), hors
quarantaine, **tels qu'ils étaient à la date de l'ordre** (`lots_lecture.disponibles`). Un
**fond de lot** (reste sous le seuil de rebut, lot FOND-DE-LOT, décision de Mohamed du
15/10/2026) n'est plus proposé : il reste dans `disponibles`, marqué, et la proposition le
nomme dans `fonds_de_lot` (l'atelier n'en fait rien, il se met au rebut). Le magasin (connu,
hors quarantaine) et la date (permise) sont contrôlés d'abord (D-11). Les empêchements connus
d'avance (inventaire en cours sur une matière proposée, ordre validé à une date postérieure)
sont rendus dans `blocages`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Inventaire,
    InventaireMatiere,
    Magasin,
    Matiere,
    Metier,
    RoleNomenclature,
)
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.modeles.types import QUANTITE, arrondir
from gestion_mp_pro.services import donnees_moteur, fonds_de_lot, horloge, lots_lecture, periode
from gestion_mp_pro.services.ordres import prevu, regles
from gestion_mp_pro.services.ordres.saisie import SaisieQualite

ZERO = Decimal(0)
SEUIL = Decimal("0.000001")


@dataclass(frozen=True)
class Demande:
    """Route 134 : ce qu'on tisse, d'où, à quelle date (aujourd'hui sans date)."""

    magasin_id: int
    qualites: tuple[SaisieQualite, ...]
    date: date | None = None
    metier_id: int | None = None


@dataclass
class LotPropose:
    """Un lot disponible à la date, et ce qu'on propose d'y prendre (0 : pas besoin)."""

    lot_id: int
    lot: str
    entre_le: date
    disponible: Decimal
    poids_bobine: Decimal
    propose: Decimal = ZERO
    fond_de_lot: bool = False
    """Sous le seuil de rebut : jamais proposé, laissé en stock (FOND-DE-LOT)."""


@dataclass
class ParQualite:
    """Ce qu'une qualité demande d'une matière, perte comprise."""

    qualite_id: int
    qualite: str
    kg: Decimal


@dataclass
class LigneProposee:
    """Une matière demandée : prévu, lots proposés (FIFO), manque."""

    matiere_id: int
    reference: str
    designation: str
    role: str
    prevu: Decimal
    kg_par_ml: Decimal
    poids_bobine: Decimal
    bobines_palette: Decimal
    par_qualite: list[ParQualite] = field(default_factory=list)
    lots: list[LotPropose] = field(default_factory=list)
    disponibles: list[LotPropose] = field(default_factory=list)
    manque: Decimal = ZERO


@dataclass
class Proposition:
    """Route 134 : les lignes, les totaux, ce qui manque, ce que la recette ne dit pas."""

    date: date
    magasin_id: int
    taux_perte: Decimal
    prevu: Decimal
    manque: Decimal
    lignes: list[LigneProposee]
    manques: list[LigneProposee]
    recettes_incompletes: list[str]
    blocages: list[str]
    fonds_de_lot: list[str] = field(default_factory=list)
    """Les fonds de lot laissés en stock, nommés (« HT-… : 56 g dans Morocco, fond de lot »)."""


def _matieres(s: Session, ids: set[int]) -> dict[int, tuple[Matiere, RoleNomenclature]]:
    """Les matières demandées et leur rôle."""
    requete = (
        select(Matiere, RoleNomenclature)
        .join(RoleNomenclature, RoleNomenclature.id == Matiere.role_id)
        .where(Matiere.id.in_(ids))
    )
    return {m.id: (m, r) for m, r in s.execute(requete).all()}


def _servir(
    ligne: LigneProposee, presents: list[lots_lecture.LotDisponible], seuil: Decimal
) -> list[str]:
    """Les lots du plus ancien au plus récent, jusqu'à couvrir le prévu (P12) ; un fond de lot
    est sauté et nommé (FOND-DE-LOT)."""
    reste = ligne.prevu
    sautes = []
    for x in presents:
        poids = x.poids_bobine if x.poids_bobine > 0 else ligne.poids_bobine
        lot = LotPropose(x.lot_id, x.lot, x.entre_le, x.quantite, poids, fond_de_lot=x.fond_de_lot)
        ligne.disponibles.append(lot)
        if x.fond_de_lot:
            sautes.append(
                f"{ligne.reference} — lot {x.lot} : {fonds_de_lot.poids_lisible(x.quantite)} dans "
                f"{x.magasin}, {fonds_de_lot.marque(seuil)}, laissé en stock (à mettre au rebut)."
            )
            continue
        if reste > SEUIL:
            pris = min(x.quantite, reste)
            lot.propose = arrondir(pris, QUANTITE)
            ligne.lots.append(lot)
            reste -= pris
    ligne.manque = arrondir(max(ZERO, reste), QUANTITE)
    return sautes


def inventaires_ouverts(s: Session, magasin_id: int, matieres: set[int]) -> list[Inventaire]:
    """Les inventaires ouverts sur ce magasin (ou sur tous) dont le périmètre compte une de ces
    matières (K2)."""
    if not matieres:
        return []
    requete = (
        select(Inventaire)
        .join(InventaireMatiere, InventaireMatiere.inventaire_id == Inventaire.id)
        .where(
            Inventaire.statut == StatutInventaire.ouvert,
            (Inventaire.magasin_id == magasin_id) | Inventaire.magasin_id.is_(None),
            InventaireMatiere.matiere_id.in_(matieres),
        )
        .distinct()
        .order_by(Inventaire.id)
    )
    return list(s.scalars(requete))


def empechements(s: Session, magasin_id: int, jour: date, matieres: set[int]) -> list[str]:
    """Ce qui empêcherait de valider un ordre de ces matières à cette date, dit d'avance."""
    raisons = []
    for i in inventaires_ouverts(s, magasin_id, matieres):
        ou = s.get_one(Magasin, i.magasin_id).code if i.magasin_id else "tous les magasins"
        raisons.append(
            f"L'inventaire {i.numero} ({ou}, du {i.date:%d/%m/%Y}) est en cours : les mouvements "
            "y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre."
        )
    dernier = regles.dernier_ordre(s)
    if dernier is not None and jour < dernier:
        raisons.append(
            f"Un ordre du {dernier:%d/%m/%Y} est déjà validé : les numéros suivent les dates, "
            f"cet ordre ne peut pas être daté avant. Pour un oubli, le dater du "
            f"{dernier:%d/%m/%Y} et écrire la vraie date dans le commentaire."
        )
    return raisons


def _m2(s: Session, demande: Demande) -> tuple[dict[str, Decimal], dict[str, int]]:
    """Les m² par code de qualité (une qualité citée deux fois s'additionne, P10)."""
    m2: dict[str, Decimal] = defaultdict(Decimal)
    ids: dict[str, int] = {}
    for q in demande.qualites:
        qualite = regles.qualite_tissable(s, q.qualite_id)
        m2[qualite.code] += q.m2
        ids[qualite.code] = qualite.id
    return dict(m2), ids


def proposer(s: Session, demande: Demande) -> Proposition:
    """Route 134 : magasin et date contrôlés (D-11), puis les lignes FIFO à la date."""
    regles.magasin_de_sortie(s, demande.magasin_id, proposition=True)
    jour = demande.date or horloge.aujourd_hui()
    periode.date_permise(s, jour)
    if demande.metier_id is not None and s.get(Metier, demande.metier_id) is None:
        raise Refus.saisie("Métier inconnu.", code="valeur_inconnue")
    m2, ids = _m2(s, demande)
    d = donnees_moteur.charger(s, avec_journal=False)
    k = 1 + prevu.taux_perte(s)
    besoins = prevu.par_matiere(s, d, m2)
    fiches = _matieres(s, set(besoins))
    seuil = fonds_de_lot.seuil(s)
    lignes: list[LigneProposee] = []
    fonds: list[str] = []
    for mid, par_qualite in besoins.items():
        m, role = fiches[mid]
        ligne = LigneProposee(
            matiere_id=mid, reference=m.reference, designation=m.designation, role=role.code,
            prevu=arrondir(sum(par_qualite.values(), ZERO) * k, QUANTITE),
            kg_par_ml=m.densite if role.lineaire else ZERO, poids_bobine=m.poids_bobine,
            bobines_palette=m.bobines_palette,
            par_qualite=[
                ParQualite(ids[c], c, arrondir(v * k, QUANTITE))
                for c, v in sorted(par_qualite.items())
            ],
        )  # fmt: skip
        fonds += _servir(ligne, lots_lecture.disponibles(s, mid, demande.magasin_id, jour), seuil)
        lignes.append(ligne)
    lignes.sort(key=lambda x: (x.role, x.reference))
    return Proposition(
        date=jour, magasin_id=demande.magasin_id, taux_perte=k - 1,
        prevu=sum((x.prevu for x in lignes), ZERO), manque=sum((x.manque for x in lignes), ZERO),
        lignes=lignes, manques=[x for x in lignes if x.manque > 0],
        recettes_incompletes=prevu.incompletes(d, m2),
        blocages=empechements(s, demande.magasin_id, jour, set(besoins)),
        fonds_de_lot=fonds,
    )  # fmt: skip
