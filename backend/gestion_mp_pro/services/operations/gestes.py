"""Créer, modifier, supprimer, valider, annuler une opération (REGLES B.1.14, OR28–OR37, C-01,
C-11 ; API-PRO 117–121).

Chaque geste relit l'opération sous `FOR UPDATE` (deux clics ne valident pas deux fois),
vérifie la version lue (409 qui nomme l'auteur), le droit du type, puis écrit le stock par
`services/stock.py` seulement, et le journal dans la même transaction. `valider: true` à la
création : brouillon et validation dans **une** transaction (rien n'est créé si la validation
est refusée).

Quarantaine (décision de Mohamed, C-01) : l'alimentation met un lot douteux en quarantaine,
elle ne l'en sort pas — ni en modifiant ou supprimant une libération préparée par les achats,
ni en annulant une libération (la matière y retournerait) ou une mise en quarantaine (elle en
sortirait).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Lot, Operation, OperationLigne, Ordre
from gestion_mp_pro.modeles.enums import DocumentMouvement, StatutDocument, TypeOperation
from gestion_mp_pro.services import audit, horloge, lots, numerotation, periode, stock
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.operations import blocages as b
from gestion_mp_pro.services.operations import droits, lecture
from gestion_mp_pro.services.operations.saisie import SaisieOperation, remplir, retour_apres_l_ordre

Recalage = Callable[[Session, Acteur, set[int], str], None]
RECALAGES: list[Recalage] = []
"""Crochet des commandes (lots D3, D4) : appelé après un retour au fournisseur et tout
transfert, validés ou annulés, avec les lots touchés et la raison (« retour au fournisseur »,
« sortie de quarantaine », « TRF-… annulé ») — un retour rouvre le bon qu'il dégarnit, une
libération solde le bon qui n'attendait plus qu'elle (S118)."""

ANNULATION = "annulation opération"


def nom(o: Operation) -> str:
    """Le nom d'une opération dans le journal : son numéro, sinon « brouillon n° 12 » (S89)."""
    return o.numero or f"brouillon n° {o.id}"


def _deja(o: Operation, geste: str) -> Refus:
    """« Une opération validée ne se modifie plus : l'annuler. » (OR29, OR31)."""
    if o.statut == StatutDocument.annulee:
        return Refus.etat(f"Une opération annulée {geste}.")
    return Refus.etat(f"Une opération validée {geste} : l'annuler.")


def _relire(s: Session, ident: int, version: int, qui: Acteur) -> Operation:
    """L'opération verrouillée, à sa version lue, d'un type permis à ce rôle."""
    o = lecture.charger(s, ident, verrou=True)
    audit.verifier_version(s, o, version, "Cette opération")
    droits.autoriser(qui.role, TypeOperation(o.type))
    return o


def _decision_des_achats(s: Session, qui: Acteur, o: Operation, geste: str) -> None:
    """403 si l'alimentation touche à une libération, ou annule une mise en quarantaine (C-01)."""
    if droits.peut_liberer(qui.role):
        return
    libere, met = lecture.passages(o, b.contexte(s, [o]))
    if libere:
        raise Refus.droit(f"{geste} une libération de quarantaine est une décision des achats.")
    if met and geste == "Annuler":
        raise Refus.droit(
            "Annuler une mise en quarantaine en ferait sortir la matière : c'est une décision "
            "des achats, après contrôle."
        )


def creer(s: Session, qui: Acteur, e: SaisieOperation, *, valider: bool = False) -> Operation:
    """Route 117 : un brouillon (sans numéro, sans effet) ; `valider` le valide aussitôt."""
    droits.autoriser(qui.role, e.type)
    o = Operation(type=e.type, date=e.date, cree_par_id=qui.id, cree_le=horloge.maintenant())
    s.add(o)
    remplir(s, o, e, qui.role)
    s.flush()
    audit.journal(
        s, qui, f"{droits.LIBELLES[e.type].lower()} (brouillon)", "operation", o.id,
        detail=nom(o),
    )  # fmt: skip
    if valider:
        return _valider(s, qui, o)
    return o


def modifier(s: Session, qui: Acteur, ident: int, version: int, e: SaisieOperation) -> Operation:
    """Route 118 : un brouillon seulement, du même type (OR29, OR30) ; lignes remplacées."""
    o = _relire(s, ident, version, qui)
    if o.statut != StatutDocument.brouillon:
        raise _deja(o, "ne se modifie plus")
    if e.type != o.type:
        raise Refus.saisie("Le type d'une opération ne change pas.")
    _decision_des_achats(s, qui, o, "Modifier")
    remplir(s, o, e, qui.role)
    flag_modified(o, "commentaire")  # la version avance même si seules les lignes changent
    s.flush()
    audit.journal(s, qui, "modification opération", "operation", o.id, detail=nom(o))
    return o


def supprimer(s: Session, qui: Acteur, ident: int, version: int) -> None:
    """Route 119 : un brouillon seulement ; aucun numéro consommé (OR31)."""
    o = _relire(s, ident, version, qui)
    if o.statut != StatutDocument.brouillon:
        raise _deja(o, "ne se supprime pas")
    _decision_des_achats(s, qui, o, "Supprimer")
    audit.suppression(s, qui, "suppression opération", o, detail=nom(o))
    s.delete(o)
    s.flush()


def valider(s: Session, qui: Acteur, ident: int, version: int) -> Operation:
    """Route 120 : le stock bouge ; numéro donné maintenant (M65)."""
    return _valider(s, qui, _relire(s, ident, version, qui))


def _valider(s: Session, qui: Acteur, o: Operation) -> Operation:
    """Valide un brouillon verrouillé (OR32–OR35, S114–S118)."""
    if o.statut == StatutDocument.annulee:
        raise Refus.etat("Cette opération est annulée : elle ne se valide plus.", "deja_annule")
    if o.statut != StatutDocument.brouillon:
        raise Refus.etat("Cette opération est déjà validée.", code="deja_valide")
    periode.date_permise(s, o.date)
    peut, raison = lecture.droit_d_agir(o, qui.role, b.contexte(s, [o]))
    if not peut:
        raise Refus.droit(raison)
    type_ = TypeOperation(o.type)
    o.numero = numerotation.numero(s, droits.SERIES[type_], o.date)
    if type_ is TypeOperation.retour_machine:
        _controler_le_retour(s, o)
    _ecrire(s, qui, o, type_)
    o.statut, o.validee_par_id, o.validee_le = StatutDocument.validee, qui.id, horloge.maintenant()
    s.flush()
    audit.journal(
        s, qui, f"validation — {droits.LIBELLES[type_].lower()}", "operation", o.id,
        numero=o.numero, detail=nom(o),
    )  # fmt: skip
    raison_recalage = (
        "retour au fournisseur" if type_ is TypeOperation.retour_fournisseur
        else "sortie de quarantaine"
    )  # fmt: skip
    _recaler(s, qui, o, raison_recalage)
    return o


def _controler_le_retour(s: Session, o: Operation) -> None:
    """L'ordre verrouillé (deux retours du même ordre se suivent), pas avant sa date, jamais
    plus que le net sorti par lot (OR7, OR34)."""
    ordre = s.scalars(select(Ordre).where(Ordre.id == o.ordre_id).with_for_update(of=Ordre)).one()
    retour_apres_l_ordre(o.date, ordre)
    ids = {x.lot_id for x in o.lignes if x.lot_id is not None}
    lus = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_(ids)))}
    for lot, rendu, sorti in b.rendu_face_au_sorti(s, o, lus):
        if rendu > sorti:
            raise Refus.etat(
                f"Le lot « {lot.numero} » n'est sorti que de {b.quantite_lisible(sorti)} pour "
                f"cet ordre ({b.quantite_lisible(rendu)} rendus) : on ne rend pas plus que ce "
                "qui est parti.",
                code="stock_insuffisant",
            )


def _ecrire(s: Session, qui: Acteur, o: Operation, type_: TypeOperation) -> None:
    """Les mouvements de chaque ligne (S116) : transfert = deux lignes appariées ; ouverture et
    matière retrouvée créent leur lot (lot interne numéroté maintenant)."""
    piece = stock.Piece(DocumentMouvement.operation, o.id, o.numero or "")
    for x in o.lignes:
        lot = s.get_one(Lot, x.lot_id) if x.lot_id is not None else _nouveau_lot(s, o, x)
        x.lot_id = lot.id
        if type_ is TypeOperation.transfert:
            stock.transferer(
                s, lot=lot, source_id=x.magasin_id, destination_id=x.magasin_destination_id or 0,
                quantite=x.quantite, jour=o.date, piece=piece, auteur_id=qui.id,
                motif_id=o.motif_id, motif_texte=o.motif_texte, commentaire=o.commentaire,
            )  # fmt: skip
            continue
        quantite: Decimal = -x.quantite if type_ is TypeOperation.retour_fournisseur else x.quantite
        stock.ecrire(
            s, type=droits.TYPE_MOUVEMENT[type_], lot=lot, magasin_id=x.magasin_id,
            quantite=quantite, jour=o.date, piece=piece, auteur_id=qui.id, prix=x.prix,
            devise=x.devise or "MAD",
            liens=stock.Liens(
                ordre_id=o.ordre_id if type_ is TypeOperation.retour_machine else None,
                motif_id=o.motif_id, motif_texte=o.motif_texte, commentaire=o.commentaire,
            ),
        )  # fmt: skip


def _nouveau_lot(s: Session, o: Operation, x: OperationLigne) -> Lot:
    """Le lot d'une ouverture ou d'une matière retrouvée, créé à la validation (entré le jour de
    l'opération) ; « Lot interne » : `LOT-AAAA-NNNN` donné maintenant (M65)."""
    if x.lot_interne:
        lot = lots.lot_interne(s, x.matiere_id, o.date)
        x.lot_numero = lot.numero
        return lot
    return stock.lot_ou_creer(s, x.matiere_id, x.lot_numero, o.date)


def annuler(s: Session, qui: Acteur, ident: int, version: int, motif: str = "") -> Operation:
    """Route 121 : une opération validée, une fois, par contre-passation datée comme elle."""
    o = _relire(s, ident, version, qui)
    if o.statut == StatutDocument.annulee:
        raise Refus.etat("Cette opération est déjà annulée.", code="deja_annule")
    if o.statut != StatutDocument.validee:
        raise Refus.etat("Seule une opération validée s'annule ; un brouillon se supprime.")
    _decision_des_achats(s, qui, o, "Annuler")
    stock.contrepasser(s, stock.Piece(DocumentMouvement.operation, o.id, o.numero or ""), qui.id)
    o.statut, o.annulee_par_id, o.annulee_le = StatutDocument.annulee, qui.id, horloge.maintenant()
    o.annulation_motif = motif.strip()
    s.flush()
    audit.journal(
        s, qui, ANNULATION, "operation", o.id, numero=o.numero or "",
        detail=" · ".join(filter(None, [nom(o), o.annulation_motif])),
    )  # fmt: skip
    _recaler(s, qui, o, f"{nom(o)} annulé")
    return o


def _recaler(s: Session, qui: Acteur, o: Operation, raison: str) -> None:
    """Les commandes des lots d'un retour au fournisseur ou d'un transfert (crochet D3/D4)."""
    if o.type not in (TypeOperation.retour_fournisseur, TypeOperation.transfert):
        return
    lots_touches = {x.lot_id for x in o.lignes if x.lot_id is not None}
    for recaler in RECALAGES:
        recaler(s, qui, lots_touches, raison)
