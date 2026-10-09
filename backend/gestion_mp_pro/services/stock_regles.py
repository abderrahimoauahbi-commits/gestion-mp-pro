"""Les règles que l'écriture du stock vérifie (REGLES B.1.2–B.1.3, SR3–SR9 mot pour mot) :
magasin connu et actif pour une entrée, inventaire ouvert qui suspend la matière dans son
périmètre (K2), solde jamais négatif, sortie couverte à sa date, cours figé.

`services/stock.ecrire` les applique sous le verrou du solde ; un brouillon (blocages calculés,
lots D) peut les appeler sans verrou pour annoncer d'avance ce qui sera refusé.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Devise,
    Inventaire,
    InventaireMatiere,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    Solde,
)
from gestion_mp_pro.modeles.enums import DocumentMouvement, StatutInventaire
from gestion_mp_pro.modeles.types import COURS, arrondir
from gestion_mp_pro.services.conversions import kg

ZERO = Decimal(0)


def nom_du_lot(s: Session, lot: Lot) -> str:
    """« « L1 » de « PP rouge » » : le lot et sa matière, comme les refus le disent."""
    reference = s.scalar(select(Matiere.reference).where(Matiere.id == lot.matiere_id))
    return f"« {lot.numero} » de « {reference} »"


def inventaire_qui_suspend(s: Session, lot: Lot, magasin_id: int) -> Inventaire | None:
    """L'inventaire ouvert sur ce magasin (ou sur tous) dont le périmètre compte la matière du
    lot : ses mouvements sont suspendus jusqu'à la validation (K2, DECISIONS N3). Hors du
    périmètre, la matière bouge librement."""
    du_perimetre = exists().where(
        InventaireMatiere.inventaire_id == Inventaire.id,
        InventaireMatiere.matiere_id == lot.matiere_id,
    )
    return s.scalars(
        select(Inventaire)
        .where(
            Inventaire.statut == StatutInventaire.ouvert,
            (Inventaire.magasin_id == magasin_id) | Inventaire.magasin_id.is_(None),
            du_perimetre,
        )
        .order_by(Inventaire.id)
        .limit(1)
    ).first()


def couvert_a_sa_date(
    s: Session, lot: Lot, magasin: Magasin, quantite: Decimal, jour: date
) -> None:
    """Une écriture qui sort de la matière, datée `jour`, doit la trouver ce jour-là et ne pas
    manquer ensuite : le stock du lot dans ce magasin ne passe sous zéro à aucune date à partir
    de `jour` (S21–S25, audit 2-G B1). Sous le verrou du solde, le journal du lot dans ce magasin
    ne bouge pas pendant qu'on le lit ; un brouillon le lit sans verrou, pour dire d'avance ce qui
    sera refusé."""
    par_jour = [
        (d, q)
        for d, q in s.execute(
            select(Mouvement.date_effet, func.sum(Mouvement.quantite))
            .where(Mouvement.lot_id == lot.id, Mouvement.magasin_id == magasin.id)
            .group_by(Mouvement.date_effet)
            .order_by(Mouvement.date_effet)
        )
    ]
    cumul, manque = ZERO, None
    for jour_effet, q in par_jour:
        cumul += q
        if jour_effet >= jour and cumul + quantite < 0 and manque is None:
            manque = (jour_effet, cumul)
    au_jour = sum((q for d, q in par_jour if d <= jour), ZERO)
    if au_jour + quantite < 0:
        manque = (jour, au_jour)
    if manque is None:
        return
    _refuser_le_manque(
        s, lot, magasin, quantite=quantite, jour=jour, manque=manque, par_jour=par_jour
    )


def _refuser_le_manque(
    s: Session,
    lot: Lot,
    magasin: Magasin,
    *,
    quantite: Decimal,
    jour: date,
    manque: tuple[date, Decimal],
    par_jour: Sequence[tuple[date, Decimal]],
) -> None:
    """SR8 (lot pas encore entré à la date) ou SR9 (pas assez à une date), mot pour mot."""
    entree = next((d for d, q in par_jour if q > 0), None)
    ref = nom_du_lot(s, lot)
    if entree is None or entree > jour:
        quand = (
            f"n'est entré dans « {magasin.code} » que le {entree:%d/%m/%Y}"
            if entree
            else f"n'est jamais entré dans « {magasin.code} »"
        )
        raise Refus.etat(
            f"Le lot {ref} {quand} : une écriture datée du {jour:%d/%m/%Y} ne peut pas le "
            "prendre. La dater au jour où la matière était là, ou choisir un lot présent à "
            "cette date.",
            code="lot_absent_a_la_date",
        )
    date_manque, disponible = manque
    suite = " : la matière est sortie depuis par d'autres écritures." if date_manque > jour else "."
    raise Refus.etat(
        f"Au {date_manque:%d/%m/%Y}, il n'y avait que {kg(max(disponible, ZERO))} kg du lot "
        f"{ref} dans « {magasin.code} », {kg(-quantite)} kg demandés au {jour:%d/%m/%Y}"
        + suite
        + " Choisir un autre lot, ou dater l'écriture après l'entrée de la matière.",
        code="stock_insuffisant",
    )


def magasin_qui_recoit(s: Session, magasin_id: int, quantite: Decimal) -> Magasin:
    """Le magasin, connu ; un magasin désactivé ne reçoit plus rien (on peut en sortir)."""
    magasin = s.get(Magasin, magasin_id)
    if magasin is None:
        raise Refus.saisie("Magasin inconnu.", code="valeur_inconnue")
    if not magasin.actif and quantite > 0:
        raise Refus.saisie(f"Le magasin « {magasin.code} » est désactivé : il ne reçoit plus rien.")
    return magasin


def cours_fige(
    s: Session, devise: str, prix: Decimal, cours: Decimal | float | None
) -> Decimal | None:
    """Le cours figé sur l'écriture (S18, I16) : aucun pour le dirham ; pour une entrée payée en
    devise, celui donné (figé par la commande), sinon celui du jour. Changer le cours demain
    ne réécrit pas ce qu'a coûté une entrée d'hier."""
    if devise == "MAD":
        return None
    donne = arrondir(cours, COURS) if cours else None
    if donne or not prix:
        return donne
    actuel = s.scalar(select(Devise.cours).where(Devise.code == devise))
    if actuel is None:
        raise Refus.saisie(f"Devise inconnue : {devise}.", code="valeur_inconnue")
    return actuel


def verifier_solde(s: Session, lot: Lot, magasin: Magasin, solde: Solde, q: Decimal) -> None:
    """Le solde du lot dans ce magasin ne passe jamais sous zéro (SR6, I03)."""
    if solde.quantite + q < 0:
        raise Refus.etat(
            f"Le lot {nom_du_lot(s, lot)} ne porte que {kg(solde.quantite, 3)} kg dans "
            f"« {magasin.code} », {kg(-q, 3)} kg demandés. Choisir un autre lot, ou faire "
            "d'abord un ajustement justifié si la matière est bien là.",
            code="stock_insuffisant",
        )


def verifier_suspension(s: Session, lot: Lot, magasin: Magasin, genre: DocumentMouvement) -> None:
    """Un inventaire ouvert qui compte cette matière dans ce magasin suspend ses mouvements
    (SR5), sauf ceux de l'inventaire lui-même. Lu **après** le verrou du solde (S14) : un
    inventaire qui s'ouvre au même instant attend ce mouvement (et le compte), ou ce mouvement
    le voit ouvert et s'arrête."""
    if genre == DocumentMouvement.inventaire:
        return
    ouvert = inventaire_qui_suspend(s, lot, magasin.id)
    if ouvert is not None:
        raise Refus.etat(
            f"L'inventaire {ouvert.numero} est en cours sur « {magasin.code} » : les "
            "mouvements y sont suspendus jusqu'à sa validation.",
            code="inventaire_en_cours",
        )
