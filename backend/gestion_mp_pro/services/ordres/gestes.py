"""Créer, modifier, supprimer, valider, annuler un ordre de fabrication (REGLES B.2.6–B.2.9,
PR11–PR21 ; DEFAUTS D-07, D-09, D-10 ; DECISIONS O1, O5 ; API-PRO 137–141).

Chaque geste relit l'ordre sous `FOR UPDATE` à sa version lue (409 qui nomme l'auteur). La
validation prend le verrou consultatif `ORDRES` **avant** de lire la date du dernier ordre :
deux validations simultanées se suivent, et les numéros suivent les dates (M67). Le numéro
`OF-AAAA-NNNN` est donné dans la transaction (un refus l'annule : aucun trou), le prévu et le
taux de perte sont figés, puis chaque ligne sort du stock par `services/stock` (tout ou rien).
Annuler un ordre annule aussi tout ce qui en est revenu (retours validés, retours repris sans
document) et supprime ses retours en brouillon, en le disant (D-10).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import Verrou, verrouiller
from gestion_mp_pro.modeles import Lot, Mouvement, Operation, Ordre
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    SerieNumero,
    StatutDocument,
    StatutOrdre,
    TypeMouvement,
    TypeOperation,
)
from gestion_mp_pro.services import audit, horloge, numerotation, periode, stock
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.conversions import kg
from gestion_mp_pro.services.ordres import blocages, prevu, regles
from gestion_mp_pro.services.ordres.saisie import SaisieOrdre, remplir

ZERO = Decimal(0)


def charger(s: Session, ident: int, *, verrou: bool = False) -> Ordre:
    """L'ordre, ses qualités et ses lignes ; `verrou` : relu sous `FOR UPDATE` (P41)."""
    requete = (
        select(Ordre)
        .where(Ordre.id == ident)
        .options(selectinload(Ordre.qualites), selectinload(Ordre.lignes))
        .execution_options(populate_existing=True)
    )
    if verrou:
        requete = requete.with_for_update(of=Ordre)
    o = s.scalars(requete).first()
    if o is None:
        raise regles.ordre_introuvable()
    return o


def _relire(s: Session, ident: int, version: int) -> Ordre:
    """L'ordre verrouillé, à sa version lue."""
    o = charger(s, ident, verrou=True)
    audit.verifier_version(s, o, version, "Cet ordre", feminin=False)
    return o


def _resume(o: Ordre) -> str:
    """« 2 matière(s), 1 234,5 kg » (le journal, D-09 : nombres à la française)."""
    total = sum((x.quantite for x in o.lignes), ZERO)
    return f"{len(o.lignes)} matière(s), {kg(total, 1)} kg"


def creer(s: Session, qui: Acteur, e: SaisieOrdre) -> Ordre:
    """Route 137 : un brouillon (sans numéro, sans effet sur le stock)."""
    o = Ordre(
        date=e.date, magasin_id=e.magasin_id, cree_par_id=qui.id, cree_le=horloge.maintenant(),
        qualites=[], lignes=[],
    )  # fmt: skip
    s.add(o)
    remplir(s, o, e)
    s.flush()
    audit.journal(s, qui, "ordre (brouillon)", "ordre", o.id, detail=_resume(o))
    return o


def modifier(s: Session, qui: Acteur, ident: int, version: int, e: SaisieOrdre) -> Ordre:
    """Route 138 : un brouillon seulement ; qualités et lignes remplacées (P42)."""
    o = _relire(s, ident, version)
    if o.statut == StatutOrdre.annule:
        raise Refus.etat("Cet ordre est annulé : il ne se modifie plus. En faire un autre.")
    if o.statut != StatutOrdre.brouillon:
        raise Refus.etat(
            "Cet ordre est déjà validé : il ne se modifie plus (l'annuler, puis en refaire un)."
        )
    remplir(s, o, e)
    flag_modified(o, "commentaire")  # la version avance même si seules les lignes changent
    s.flush()
    audit.journal(s, qui, "modification ordre", "ordre", o.id, detail=_resume(o))
    return o


def supprimer(s: Session, qui: Acteur, ident: int, version: int) -> None:
    """Route 139 : un brouillon seulement ; aucun numéro consommé (P43)."""
    o = _relire(s, ident, version)
    if o.statut == StatutOrdre.annule:
        raise Refus.etat(
            "Cet ordre est annulé : il reste dans l'historique, il ne se supprime pas."
        )
    if o.statut != StatutOrdre.brouillon:
        raise Refus.etat("Un ordre validé ne se supprime pas : l'annuler.")
    audit.suppression(s, qui, "suppression ordre", o, detail=regles.nom(o))
    s.delete(o)
    s.flush()


def _controler(s: Session, o: Ordre) -> None:
    """Ce qui refuse la validation avant tout verrou (PR14–PR17)."""
    if o.statut == StatutOrdre.annule:
        raise Refus.etat("Cet ordre est annulé : il ne se valide plus.", code="deja_annule")
    if o.statut != StatutOrdre.brouillon:
        raise Refus.etat("Cet ordre est déjà validé.", code="deja_valide")
    periode.date_permise(s, o.date)
    if not o.lignes:
        raise Refus.etat("Cet ordre ne sort aucune matière.", code="validation_bloquee")
    if codes := blocages.arretees(s, o):
        raise Refus.etat(
            f"Qualité arrêtée ({', '.join(codes)}) : elle ne se tisse plus. La retirer de "
            "l'ordre, ou demander à la direction de la remettre en service.",
            code="fiche_inactive",
        )
    if oublis := prevu.oublis(s, prevu.codes(s, (q.qualite_id for q in o.qualites))):
        raise Refus.etat(
            "Recette incomplète — " + " ; ".join(oublis) + " Le prévu figé de l'ordre serait "
            "faux pour toujours : la direction complète la recette (Qualités), ou l'ordre part "
            "hors recette.",
            code="validation_bloquee",
        )
    if manquants := blocages.lots_manquants(s, o):
        raise Refus.etat(
            "À la date de l'ordre, " + " ; ".join(manquants) + ". Choisir un autre lot, ou "
            "dater l'ordre du jour où la matière était là.",
            code="stock_insuffisant",
        )


def valider(s: Session, qui: Acteur, ident: int, version: int) -> Ordre:
    """Route 140 : numéro, prévu figé, sorties sous verrou (P50–P56)."""
    o = _relire(s, ident, version)
    _controler(s, o)
    # Deux validations au même instant : la seconde attend la première avant de lire la date
    # du dernier ordre (sinon les deux passent et les numéros ne suivent plus les dates).
    verrouiller(s, Verrou.ORDRES)
    dernier = regles.dernier_ordre(s, sauf=o.id)
    if dernier is not None and o.date < dernier:
        raise Refus.etat(
            f"Un ordre daté du {dernier:%d/%m/%Y} existe déjà : les numéros suivent les dates, "
            "un ordre ne se valide pas à une date antérieure.",
            code="ordre_des_dates",
        )
    numero = numerotation.numero(s, SerieNumero.OF, o.date)
    o.numero, o.statut = numero, StatutOrdre.valide  # ensemble (numéro ⇔ validé)
    o.valide_par_id, o.valide_le = qui.id, horloge.maintenant()
    prevu.figer(s, o)
    piece = stock.Piece(DocumentMouvement.ordre, o.id, numero)
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_({y.lot_id for y in o.lignes})))}
    for x in o.lignes:
        stock.ecrire(
            s, type=TypeMouvement.SORTIE, lot=lots[x.lot_id], magasin_id=o.magasin_id,
            quantite=-x.quantite, jour=o.date, piece=piece, auteur_id=qui.id,
            liens=stock.Liens(ordre_id=o.id),
        )  # fmt: skip
    s.flush()
    audit.journal(
        s, qui, "validation ordre", "ordre", o.id, numero=numero,
        detail=f"{numero} · {_resume(o).replace(', ', ' · ')}",
    )  # fmt: skip
    return o


def _retours(s: Session, ordre_id: int, statut: StatutDocument) -> list[Operation]:
    """Les retours des machines de l'ordre dans ce statut, verrouillés."""
    return list(
        s.scalars(
            select(Operation)
            .where(
                Operation.ordre_id == ordre_id,
                Operation.type == TypeOperation.retour_machine,
                Operation.statut == statut,
            )
            .order_by(Operation.id)
            .with_for_update(of=Operation)
        )
    )


def _a_defaire(s: Session, ordre_id: int) -> list[Mouvement]:
    """Tout ce que l'ordre a écrit et qui compte encore : ses sorties, ses retours validés,
    ses retours repris sans document (ni annulations, ni lignes déjà annulées)."""
    annulees = select(Mouvement.contrepasse_id).where(Mouvement.contrepasse_id.is_not(None))
    return list(
        s.scalars(
            select(Mouvement)
            .where(
                Mouvement.ordre_id == ordre_id,
                Mouvement.contrepasse_id.is_(None),
                Mouvement.id.not_in(annulees),
            )
            .order_by(Mouvement.id)
        )
    )


def annuler(
    s: Session, qui: Acteur, ident: int, version: int, motif: str = ""
) -> tuple[Ordre, str]:
    """Route 141 : contre-passe l'ordre et ses retours (une transaction), supprime ses retours
    en brouillon (D-10) ; rend l'ordre et la phrase qui dit tout ce qui a été fait."""
    # Les retours d'abord, puis l'ordre : l'ordre des verrous d'une validation de retour
    # (retour, puis ordre) — jamais l'inverse, qui se croiserait avec elle.
    _retours(s, ident, StatutDocument.validee)
    _retours(s, ident, StatutDocument.brouillon)
    o = _relire(s, ident, version)
    if o.statut == StatutOrdre.annule:
        raise Refus.etat("Cet ordre est déjà annulé.", code="deja_annule")
    if o.statut != StatutOrdre.valide:
        raise Refus.etat("Seul un ordre validé s'annule ; un brouillon se supprime.")
    numero = o.numero or ""
    defaits = _a_defaire(s, o.id)
    repris = [x for x in defaits if x.document == DocumentMouvement.reprise and x.quantite > 0]
    if defaits:
        stock.contrepasser_mouvements(s, defaits, qui.id)
    valides = _retours(s, o.id, StatutDocument.validee)
    maintenant = horloge.maintenant()
    for r in valides:
        r.statut, r.annulee_par_id, r.annulee_le = StatutDocument.annulee, qui.id, maintenant
        r.annulation_motif = f"avec l'ordre {numero}"
        audit.journal(
            s, qui, "annulation opération", "operation", r.id, numero=r.numero or "",
            detail=f"{r.numero} (avec {numero})",
        )  # fmt: skip
    brouillons = _retours(s, o.id, StatutDocument.brouillon)
    for r in brouillons:
        audit.suppression(
            s, qui, "suppression opération", r,
            detail=f"retour en brouillon de {numero} (avec l'annulation de l'ordre)",
        )  # fmt: skip
        s.delete(r)
    o.statut, o.annule_par_id, o.annule_le = StatutOrdre.annule, qui.id, maintenant
    o.annulation_motif = motif.strip()
    s.flush()
    phrase = _phrase(numero, [r.numero or "" for r in valides], len(repris), len(brouillons))
    audit.journal(
        s, qui, "annulation ordre", "ordre", o.id, numero=numero,
        detail=" · ".join(filter(None, [phrase, o.annulation_motif])),
    )  # fmt: skip
    return o, phrase


def _phrase(numero: str, retours: list[str], repris: int, brouillons: int) -> str:
    """« Ordre OF-… annulé : sa matière est revenue en stock, avec 1 retour annulé (RET-…) ;
    1 retour en brouillon supprimé. »"""
    texte = f"Ordre {numero} annulé : sa matière est revenue en stock"
    n = len(retours) + repris
    if n:
        noms = ", ".join([*retours, *(["repris de l'ERP Fil"] if repris else [])])
        texte += f", ses retours annulés avec lui ({n} : {noms})"
    if brouillons:
        texte += f" ; {brouillons} retour(s) en brouillon supprimé(s)"
    return texte + "."
