"""Ce qu'un ordre a consommé : prévu (perte comprise), sorti net, écart, retours, lots sortis
(REGLES B.2.8–B.2.10 : P60, P61, P74, P80 ; DEFAUTS D-03, D-07 ; API-PRO 142, 143).

Les chiffres sont ceux du moteur (`calcul.production.consommation_par_of` puis
`ajuster_ordre`) : la même règle que Production et besoins, le bilan et le pilotage. Un ordre
validé garde **son** taux de perte figé ; un ordre repris sans prévu figé prend le taux en
vigueur à sa validation, relu dans l'historique des réglages (D-07 : changer le réglage
aujourd'hui ne réécrit pas son écart). Les retours se lisent au journal du stock (ceux des
opérations comme ceux repris de l'ERP Fil, sans document) ; un ordre annulé ne compte rien.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.calcul.production import OrdreAjuste, ajuster_ordre, consommation_par_of
from gestion_mp_pro.modeles import Lot, Mouvement, Ordre, ParametreHistorique, Qualite
from gestion_mp_pro.modeles.enums import DocumentMouvement, StatutOrdre, TypeMouvement
from gestion_mp_pro.services import donnees_moteur, lots_lecture, stock_regles
from gestion_mp_pro.services.chargeur.contexte import a_l_usine
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.ordres.regles import POUSSIERE

ZERO = Decimal(0)
CLE_PERTE = "taux_perte"


def taux_perte_au(s: Session, actuel: float) -> Callable[[datetime], float]:
    """Le taux de perte des réglages à un instant passé (D-07) : la dernière valeur enregistrée
    avant lui ; avant tout changement, celle que le premier remplaçait ; sans historique,
    celui d'aujourd'hui."""
    changements = [
        (a_l_usine(quand), avant, apres)
        for quand, avant, apres in s.execute(
            select(ParametreHistorique.quand, ParametreHistorique.avant, ParametreHistorique.apres)
            .where(ParametreHistorique.cle == CLE_PERTE)
            .order_by(ParametreHistorique.quand, ParametreHistorique.id)
        )
    ]
    if not changements:
        return lambda _instant: actuel

    def lu(texte: str | None, defaut: float) -> float:
        """Une valeur du réglage, ou `defaut` si elle est vide ou illisible."""
        try:
            return float(texte) if texte else defaut
        except ValueError:
            return defaut

    premier = lu(changements[0][1], actuel)

    def au(instant: datetime) -> float:
        """Le taux en vigueur à `instant`."""
        valeur = premier
        for quand, _avant, apres in changements:
            if quand is not None and quand > instant:
                break
            valeur = lu(apres, valeur)
        return valeur

    return au


def consommations(s: Session) -> dict[str, OrdreAjuste]:
    """Chaque ordre du journal, tel que l'atelier le lit, par numéro (P80)."""
    d = donnees_moteur.charger(s)
    perte_au = taux_perte_au(s, d.parametres.taux_perte)
    densites = {x.reference: float(x.kg_par_ml) for x in lots_lecture.lire(s).matieres.values()}
    instants = {
        o.numero: o.valide_le or datetime.combine(o.date or date.min, time.max)
        for o in d.ordres
        if o.numero and (o.valide_le or o.date)
    }
    resultat = {}
    for x in consommation_par_of(d):
        instant = instants.get(x.numero_of)
        perte = perte_au(instant) if instant is not None else d.parametres.taux_perte
        resultat[x.numero_of] = ajuster_ordre(x, perte, densites)
    return resultat


@dataclass
class Retour:
    """Un retour des machines de l'ordre : l'opération (ou la reprise de l'ERP Fil), sa date,
    ses kilos."""

    id: int | None
    numero: str
    date: date
    quantite: Decimal


def retours_par_ordre(s: Session, ids: list[int] | None = None) -> dict[int, list[Retour]]:
    """Ce qui est revenu des machines, ordre par ordre, lu au journal ; un retour annulé et son
    annulation n'y sont pas ; un retour par document et par jour (P60)."""
    requete = (
        select(Mouvement)
        .where(Mouvement.type == TypeMouvement.RETOUR_MACHINE, Mouvement.ordre_id.is_not(None))
        .order_by(Mouvement.date_effet, Mouvement.id)
    )
    if ids is not None:
        requete = requete.where(Mouvement.ordre_id.in_(ids))
    lignes = list(s.scalars(requete))
    annules = {x.contrepasse_id for x in lignes if x.contrepasse_id is not None}
    par_ordre: dict[int, dict[tuple[str, int | None, date], Retour]] = defaultdict(dict)
    for x in lignes:
        if x.contrepasse_id is not None or x.id in annules or x.ordre_id is None:
            continue
        operation = x.document == DocumentMouvement.operation
        cle = (str(x.document), x.operation_id if operation else None, x.date_effet)
        retour = par_ordre[x.ordre_id].setdefault(
            cle,
            Retour(
                id=x.operation_id if operation else None,
                numero=x.document_numero
                if operation
                else f"retour repris de l'ERP Fil du {x.date_effet:%d/%m/%Y}",
                date=x.date_effet,
                quantite=ZERO,
            ),
        )
        retour.quantite += x.quantite
    return {k: list(v.values()) for k, v in par_ordre.items()}


@dataclass
class LotSorti:
    """Ce qu'un ordre a emporté d'un lot, net des retours : ce qui peut revenir (P61)."""

    lot_id: int
    lot: str
    matiere_id: int
    reference: str
    designation: str
    sorti_net: Decimal
    kg_par_ml: Decimal
    poids_bobine: Decimal
    bobines_palette: Decimal
    blocage: str = ""


def lots_sortis(s: Session, o: Ordre) -> list[LotSorti]:
    """Route 142 : lot par lot, −Σ des mouvements de l'ordre (annulations comprises), > 1 g ;
    `blocage` : l'inventaire qui suspend la matière dans le magasin de l'ordre (K2)."""
    nets = s.execute(
        select(Mouvement.lot_id, -func.sum(Mouvement.quantite))
        .where(Mouvement.ordre_id == o.id)
        .group_by(Mouvement.lot_id)
        .order_by(Mouvement.lot_id)
    ).all()
    lus = lots_lecture.lire(s)
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_([n for n, _ in nets])))}
    resultat = []
    for lot_id, net in nets:
        if net <= POUSSIERE:
            continue
        lot = lots[lot_id]
        m = lus.matieres[lot.matiere_id]
        ouvert = stock_regles.inventaire_qui_suspend(s, lot, o.magasin_id)
        resultat.append(
            LotSorti(
                lot_id=lot.id,
                lot=lot.numero,
                matiere_id=m.id,
                reference=m.reference,
                designation=m.designation,
                sorti_net=net,
                kg_par_ml=m.kg_par_ml,
                poids_bobine=lot.poids_bobine if lot.poids_bobine > 0 else m.poids_bobine,
                bobines_palette=m.bobines_palette,
                blocage=(
                    f"L'inventaire {ouvert.numero} est en cours : les mouvements de "
                    f"« {m.reference} » y sont suspendus jusqu'à sa validation."
                    if ouvert is not None
                    else ""
                ),
            )  # fmt: skip
        )
    return resultat


@dataclass
class ParMatiere:
    """Le prévu par la recette (perte comprise) et le sorti net d'une matière d'un ordre."""

    matiere_id: int | None
    reference: str
    quantite: float
    prevu: float
    ecart: float | None
    hors_recette: bool
    kg_par_ml: float


def par_matiere(conso: OrdreAjuste | None, lus: lots_lecture.Lus) -> list[ParMatiere]:
    """Matière par matière (vide pour un brouillon : calculé à la validation)."""
    if conso is None:
        return []
    ids = {m.reference: m.id for m in lus.matieres.values()}
    return [
        ParMatiere(
            matiere_id=ids.get(r.reference),
            reference=r.reference,
            quantite=r.quantite,
            prevu=r.theorique,
            ecart=r.ecart,
            hors_recette=r.hors_recette,
            kg_par_ml=getattr(r, "kg_par_ml", 0.0),
        )  # fmt: skip
        for r in conso.references
    ]


@dataclass
class QualiteM2:
    """Une qualité de l'ordre et ses m²."""

    qualite_id: int
    qualite: str
    m2: Decimal


@dataclass
class ConsommationLue:
    """Route 143 : ce qu'un ordre validé a consommé, face au prévu de sa recette."""

    ordre_id: int
    numero: str
    date: dt.date
    debut: dt.date
    fin: dt.date
    qualites: list[QualiteM2]
    fabrication: str
    m2: Decimal
    commentaire: str
    consomme: float
    retours: float
    net: float
    prevu: float
    ecart: float | None
    ecart_relatif: float | None
    taux_perte: float
    references: list[ParMatiere]
    lots: list[str]


def consommation_des_ordres(
    s: Session, du: date | None = None, au: date | None = None, qualite_id: int | None = None
) -> list[ConsommationLue]:
    """Route 143 : les ordres validés (un ordre annulé n'a rien consommé, P74), datés entre `du`
    et `au`, qui tissent `qualite_id` s'il est donné ; la fin la plus récente d'abord."""
    requete = (
        select(Ordre)
        .options(selectinload(Ordre.qualites))
        .where(Ordre.statut == StatutOrdre.valide)
    )
    if du is not None:
        requete = requete.where(Ordre.date >= du)
    if au is not None:
        requete = requete.where(Ordre.date <= au)
    ordres = {
        o.numero: o
        for o in s.scalars(requete)
        if o.numero and (qualite_id is None or any(q.qualite_id == qualite_id for q in o.qualites))
    }
    codes = dict(s.execute(select(Qualite.id, Qualite.code)).all())
    lus = lots_lecture.lire(s)
    resultat = []
    for numero, x in consommations(s).items():
        o = ordres.get(numero)
        if o is None:
            continue
        qualites = [
            QualiteM2(q.qualite_id, codes[q.qualite_id], q.m2)
            for q in sorted(o.qualites, key=lambda y: y.id)
        ]
        resultat.append(
            ConsommationLue(
                ordre_id=o.id,
                numero=numero,
                date=o.date,
                debut=x.debut,
                fin=x.fin,
                qualites=qualites,
                fabrication=" · ".join(f"{q.qualite} {kg(q.m2, 0)} m²" for q in qualites)
                or "hors recette",
                m2=sum((q.m2 for q in qualites), ZERO),
                commentaire=o.commentaire,
                consomme=x.consomme,
                retours=x.retours,
                net=x.net,
                prevu=x.theorique,
                ecart=x.ecart,
                ecart_relatif=x.ecart_relatif,
                taux_perte=x.taux_perte,
                references=par_matiere(x, lus),
                lots=list(x.lots),
            )  # fmt: skip
        )
    return resultat
