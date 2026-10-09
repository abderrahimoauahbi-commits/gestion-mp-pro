"""Ce qui empêcherait aujourd'hui de valider un brouillon d'ordre (REGLES B.2.5 : PB1–PB7,
P30, P31), calculé **sans rien écrire**, pour l'annoncer avant le clic (fiche, « À valider »).

La validation applique les mêmes règles (même fonction pour les lots : `lots_manquants`) ;
une raison annoncée est une raison de refus. L'inventaire ouvert ne suspend que les matières
de son périmètre (K2) ; une recette qui oublie un rôle pesant bloquerait le prévu figé.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Magasin, Matiere, Ordre, Qualite
from gestion_mp_pro.modeles.enums import StatutOrdre, TypeMagasin
from gestion_mp_pro.services import horloge, lots_lecture, periode, stock_regles
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.ordres import prevu
from gestion_mp_pro.services.ordres.regles import POUSSIERE

ZERO = Decimal(0)


def _voulu(o: Ordre) -> dict[int, Decimal]:
    """Ce que l'ordre demande à chaque lot (ses lignes additionnées)."""
    voulu: dict[int, Decimal] = defaultdict(Decimal)
    for x in o.lignes:
        voulu[x.lot_id] += x.quantite
    return dict(voulu)


def _etat(lot: Lot, present: Decimal, jour: date) -> str:
    """Ce que le lot portait à la date (P31)."""
    if lot.entre_le > jour:
        return f"entré le {lot.entre_le:%d/%m/%Y}, après la date de l'ordre"
    passe = f" au {jour:%d/%m/%Y}" if jour < horloge.aujourd_hui() else ""
    if present <= POUSSIERE:
        return "épuisé" + passe
    return f"{kg(present, 3)} kg seulement{passe}"


def lots_manquants(s: Session, o: Ordre) -> list[str]:
    """Les lots qui ne portent pas, à la date de l'ordre, ce qu'il leur demande — entrés après
    cette date, ou déjà vidés depuis ; et la règle même de l'écriture (`couvert_a_sa_date`),
    lue d'avance sans verrou (P30, P31)."""
    voulu = _voulu(o)
    if not voulu:
        return []
    magasin = s.get_one(Magasin, o.magasin_id)
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(voulu)))}
    refs = dict(
        s.execute(
            select(Matiere.id, Matiere.reference).where(
                Matiere.id.in_({x.matiere_id for x in lots.values()})
            )
        ).all()
    )
    presents = lots_lecture.presents_au(s, {(i, magasin.id) for i in voulu}, o.date)
    raisons = []
    for lot_id in dict.fromkeys(x.lot_id for x in o.lignes):
        lot, demande = lots[lot_id], voulu[lot_id]
        nom = f"lot {lot.numero} de {refs[lot.matiere_id]}"
        present = presents.get((lot_id, magasin.id), ZERO)
        if demande <= present + POUSSIERE:
            try:
                stock_regles.couvert_a_sa_date(s, lot, magasin, -demande, o.date)
            except Refus as refus:
                raisons.append(f"{nom} : {refus.detail}")
            continue
        raisons.append(
            f"{nom} : {_etat(lot, present, o.date)} dans « {magasin.code} », "
            f"{kg(demande, 3)} kg demandés"
        )
    return raisons


def _inventaires(s: Session, o: Ordre, magasin: Magasin) -> list[str]:
    """Les inventaires ouverts qui suspendent une matière de l'ordre dans son magasin (K2)."""
    numeros: list[str] = []
    for lot in s.scalars(select(Lot).where(Lot.id.in_({x.lot_id for x in o.lignes}))):
        ouvert = stock_regles.inventaire_qui_suspend(s, lot, magasin.id)
        if ouvert is not None and ouvert.numero not in numeros:
            numeros.append(ouvert.numero)
    return [f"l'inventaire {n} est en cours sur « {magasin.code} »" for n in numeros]


def arretees(s: Session, o: Ordre) -> list[str]:
    """Les codes des qualités arrêtées de l'ordre, triés."""
    ids = {q.qualite_id for q in o.qualites}
    return sorted(
        s.scalars(select(Qualite.code).where(Qualite.id.in_(ids), Qualite.actif.is_(False)))
    )


def blocages(s: Session, o: Ordre, dernier: date | None) -> list[str]:
    """Les raisons, dans l'ordre de Gestion MP et sans doublon ; vide hors brouillon (PB1–PB7).

    `dernier` : la date du dernier ordre validé ou annulé (`regles.dernier_ordre`)."""
    if o.statut != StatutOrdre.brouillon:
        return []
    raisons: list[str] = []
    if not o.lignes:
        raisons.append("aucune matière à sortir")
    try:
        periode.date_permise(s, o.date)
    except Refus as refus:
        raisons.append(refus.detail)
    if dernier is not None and o.date < dernier:
        raisons.append(
            f"un ordre daté du {dernier:%d/%m/%Y} est déjà validé : dater cet ordre au moins "
            "de ce jour"
        )
    magasin = s.get_one(Magasin, o.magasin_id)
    if magasin.type == TypeMagasin.quarantaine:
        raisons.append(f"« {magasin.code} » est un magasin de quarantaine")
    raisons += _inventaires(s, o, magasin)
    if codes := arretees(s, o):
        raisons.append("qualité arrêtée : " + ", ".join(codes))
    raisons += prevu.oublis(s, prevu.codes(s, (q.qualite_id for q in o.qualites)))
    raisons += lots_manquants(s, o)
    return list(dict.fromkeys(raisons))
