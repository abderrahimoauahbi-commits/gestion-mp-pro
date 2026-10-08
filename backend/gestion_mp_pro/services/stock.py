"""L'écriture du stock : **le seul chemin** (ARCHITECTURE § 6, REGLES B.1.2–B.1.6, I01–I05).

Toute écriture passe par `ecrire` : elle verrouille le solde du lot dans le magasin
(`SELECT … FOR UPDATE`), regarde si un inventaire ouvert suspend cette matière dans ce magasin
(**limité à son périmètre**, K2), vérifie que le solde ne passera pas sous zéro et que la sortie
est couverte à sa date, fige le cours, met le solde à jour et ajoute la ligne au journal, dans
la transaction de l'appelant (qui valide tout ou rien). Deux personnes qui sortent la même
palette : la seconde attend la première, puis lit le solde à jour.

Le journal ne se modifie ni ne se supprime (`tr_mouvement_immuable`) : on annule un document
en écrivant l'inverse de chacune de ses lignes, **datée comme l'original** (`contrepasser`),
une fois (`uq_mouvement_contrepasse_id`). Un essai interdit `Mouvement(` hors de ce module
(et de la reprise). Messages des refus : REGLES SR1–SR12, mot pour mot.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import (
    Lot,
    Mouvement,
    Solde,
)
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement
from gestion_mp_pro.modeles.types import PRIX, QUANTITE, arrondir
from gestion_mp_pro.services import horloge, periode
from gestion_mp_pro.services import stock_regles as regles
from gestion_mp_pro.services.lots import lot_ou_creer
from gestion_mp_pro.services.stock_regles import couvert_a_sa_date, inventaire_qui_suspend

__all__ = [
    "Liens",
    "Piece",
    "a_contrepasser",
    "contrepasser",
    "contrepasser_mouvements",
    "couvert_a_sa_date",
    "ecrire",
    "inventaire_qui_suspend",
    "lot_ou_creer",
    "solde_matiere",
    "transferer",
]

ZERO = Decimal(0)
CONTREPASSATION_UNIQUE = "uq_mouvement_contrepasse_id"
_COLONNE_DU_DOCUMENT = {
    DocumentMouvement.reception: "reception_id",
    DocumentMouvement.ordre: "ordre_id",
    DocumentMouvement.operation: "operation_id",
    DocumentMouvement.inventaire: "inventaire_id",
}


@dataclass(frozen=True)
class Piece:
    """Le document qui écrit : son genre, son identifiant (sauf reprise), son numéro."""

    genre: DocumentMouvement
    ident: int | None = None
    numero: str = ""

    def colonnes(self) -> dict[str, int]:
        """La clé typée du document (`reception_id`…), vide pour une reprise."""
        colonne = _COLONNE_DU_DOCUMENT.get(self.genre)
        if colonne is None:
            return {}
        if self.ident is None:
            raise ValueError(f"Un document « {self.genre} » s'écrit avec son identifiant.")
        return {colonne: self.ident}


def _solde_verrouille(s: Session, lot_id: int, magasin_id: int) -> Solde:
    """Le solde (lot, magasin), créé à 0 au besoin, relu en base sous `FOR UPDATE` (S13)."""
    s.execute(
        insert(Solde)
        .values(lot_id=lot_id, magasin_id=magasin_id, quantite=ZERO)
        .on_conflict_do_nothing(index_elements=["lot_id", "magasin_id"])
    )
    return s.scalars(
        select(Solde)
        .where(Solde.lot_id == lot_id, Solde.magasin_id == magasin_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _nouvel_identifiant(s: Session) -> int:
    """Un numéro de mouvement pris d'avance (une jambe de transfert se nomme elle-même)."""
    return int(
        s.execute(text("SELECT nextval(pg_get_serial_sequence('mouvement', 'id'))")).one()[0]
    )


@dataclass(frozen=True)
class Liens:
    """Ce qu'une écriture cite en plus de son document : ordre, paire, contre-passation,
    motif. `paire_soi` : première jambe d'une paire (sa paire est elle-même)."""

    ordre_id: int | None = None
    paire_id: int | None = None
    paire_soi: bool = False
    contrepasse_id: int | None = None
    motif_id: int | None = None
    motif_texte: str = ""
    commentaire: str = ""


def ecrire(  # noqa: PLR0913 — les champs d'une écriture du journal
    s: Session,
    *,
    type: TypeMouvement,
    lot: Lot,
    magasin_id: int,
    quantite: Decimal | float,
    jour: date,
    piece: Piece,
    auteur_id: int | None,
    prix: Decimal | float = 0,
    devise: str = "MAD",
    cours: Decimal | float | None = None,
    liens: Liens = Liens(),  # noqa: B008 — valeur immuable
) -> Mouvement:
    """Écrit une ligne au journal du stock, sous le verrou du solde, ou refuse (SR1–SR9).

    `quantite` en kg signés (arrondie au gramme) ; `prix` au kg, entrées seulement ; `cours`
    figé par la commande s'il est donné, sinon celui du jour pour une entrée payée en devise.
    Aucun commit : l'appelant valide la transaction du geste."""
    q = arrondir(quantite, QUANTITE)
    if q == 0:
        raise Refus.saisie(
            "Une écriture de stock ne peut pas être nulle.", code="quantite_invalide"
        )
    periode.date_permise(s, jour)
    magasin = regles.magasin_qui_recoit(s, magasin_id, q)
    solde = _solde_verrouille(s, lot.id, magasin_id)
    regles.verifier_suspension(s, lot, magasin, piece.genre)
    regles.verifier_solde(s, lot, magasin, solde, q)
    if q < 0:
        regles.couvert_a_sa_date(s, lot, magasin, q, jour)
    devise = (devise or "MAD").upper()
    prix_kg = arrondir(prix, PRIX)
    ident = _nouvel_identifiant(s) if liens.paire_soi else None
    mouvement = Mouvement(
        id=ident, date_effet=jour, type=type, matiere_id=lot.matiere_id, lot_id=lot.id,
        magasin_id=magasin_id, quantite=q, prix=prix_kg, devise=devise,
        cours=regles.cours_fige(s, devise, prix_kg, cours), document=piece.genre,
        **piece.colonnes(), document_numero=piece.numero,
        paire_id=ident if liens.paire_soi else liens.paire_id,
        contrepasse_id=liens.contrepasse_id, motif_id=liens.motif_id,
        motif_texte=liens.motif_texte, commentaire=liens.commentaire, auteur_id=auteur_id,
    )  # fmt: skip
    if liens.ordre_id is not None:
        mouvement.ordre_id = liens.ordre_id
    solde.quantite += q
    solde.maj_le = horloge.maintenant()
    s.add(mouvement)
    _ecrire_ou_refuser(s, liens)
    return mouvement


def _ecrire_ou_refuser(s: Session, liens: Liens) -> None:
    """Écrit (`flush` : le numéro du mouvement est connu) ; une seconde contre-passation du
    même mouvement, arrivée en même temps qu'une autre, est refusée (SR12)."""
    try:
        s.flush()
    except IntegrityError as exc:
        contrainte = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if liens.contrepasse_id is not None and contrainte == CONTREPASSATION_UNIQUE:
            raise Refus.etat("Ce document a déjà été annulé.", code="deja_annule") from exc
        raise


def transferer(  # noqa: PLR0913 — les champs d'un transfert
    s: Session,
    *,
    lot: Lot,
    source_id: int,
    destination_id: int,
    quantite: Decimal | float,
    jour: date,
    piece: Piece,
    auteur_id: int | None,
    motif_id: int | None = None,
    motif_texte: str = "",
    commentaire: str = "",
) -> tuple[Mouvement, Mouvement]:
    """Un transfert : la sortie de la source (sa paire est elle-même), puis l'entrée dans la
    destination (sa paire est la sortie), même document, même jour, même motif, prix nul (S35)."""
    if source_id == destination_id:
        raise Refus.saisie("Un transfert va d'un magasin à un autre.")
    q = arrondir(quantite, QUANTITE)
    commun = Liens(motif_id=motif_id, motif_texte=motif_texte, commentaire=commentaire)
    sortie = ecrire(
        s,
        type=TypeMouvement.TRANSFERT,
        lot=lot,
        magasin_id=source_id,
        quantite=-q,
        jour=jour,
        piece=piece,
        auteur_id=auteur_id,
        liens=replace(commun, paire_soi=True),
    )
    entree = ecrire(
        s,
        type=TypeMouvement.TRANSFERT,
        lot=lot,
        magasin_id=destination_id,
        quantite=q,
        jour=jour,
        piece=piece,
        auteur_id=auteur_id,
        liens=replace(commun, paire_id=sortie.id),
    )
    return sortie, entree


def a_contrepasser(s: Session, piece: Piece) -> list[Mouvement]:
    """Les lignes d'un document qui ne sont ni des annulations ni déjà annulées (S40)."""
    annulees = select(Mouvement.contrepasse_id).where(Mouvement.contrepasse_id.is_not(None))
    filtres = [Mouvement.document == piece.genre, Mouvement.contrepasse_id.is_(None)]
    filtres += [getattr(Mouvement, col) == ident for col, ident in piece.colonnes().items()]
    return list(
        s.scalars(
            select(Mouvement).where(*filtres, Mouvement.id.not_in(annulees)).order_by(Mouvement.id)
        )
    )


def contrepasser(s: Session, piece: Piece, auteur_id: int | None) -> int:
    """Annule un document validé : l'inverse de chacune de ses lignes, une fois (SR12)."""
    lignes = a_contrepasser(s, piece) if piece.genre != DocumentMouvement.reprise else []
    if not lignes:
        raise Refus.etat("Ce document a déjà été annulé.", code="deja_annule")
    return contrepasser_mouvements(s, lignes, auteur_id)


def contrepasser_mouvements(s: Session, lignes: Sequence[Mouvement], auteur_id: int | None) -> int:
    """L'inverse de chaque ligne, par `ecrire` (S41–S43) : même type, quantité opposée, datée de
    l'original, même document, prix, devise, cours, ordre et motif ; « Annulation du mouvement
    n°… ». On défait d'abord les sorties (la matière revient), puis les entrées : le solde ne
    passe jamais sous zéro en chemin. Une paire de transfert reste une paire."""
    lots = {x.id: x for x in s.scalars(select(Lot).where(Lot.id.in_({y.lot_id for y in lignes})))}
    nouvelles_paires: dict[int, int] = {}
    for x in sorted(lignes, key=lambda y: (y.quantite > 0, y.id)):
        premiere = x.paire_id is not None and x.paire_id not in nouvelles_paires
        inverse = ecrire(
            s,
            type=x.type,
            lot=lots[x.lot_id],
            magasin_id=x.magasin_id,
            quantite=-x.quantite,
            jour=x.date_effet,
            piece=_piece_de(x),
            auteur_id=auteur_id,
            prix=x.prix,
            devise=x.devise,
            cours=x.cours,
            liens=Liens(
                ordre_id=x.ordre_id,
                paire_id=nouvelles_paires.get(x.paire_id) if x.paire_id else None,
                paire_soi=premiere,
                contrepasse_id=x.id,
                motif_id=x.motif_id,
                motif_texte=x.motif_texte,
                commentaire=f"Annulation du mouvement n°{x.id}",
            ),
        )
        if premiere and x.paire_id is not None:
            nouvelles_paires[x.paire_id] = inverse.id
    return len(lignes)


def _piece_de(x: Mouvement) -> Piece:
    """Le document d'un mouvement (sa clé typée), pour écrire son inverse."""
    colonne = _COLONNE_DU_DOCUMENT.get(DocumentMouvement(x.document))
    ident = getattr(x, colonne) if colonne else None
    return Piece(DocumentMouvement(x.document), ident, x.document_numero)


def solde_matiere(s: Session, matiere_id: int) -> Decimal:
    """Ce que portent tous les lots d'une matière, quarantaine comprise (S51)."""
    total = s.scalar(
        select(func.coalesce(func.sum(Solde.quantite), 0))
        .join(Lot, Lot.id == Solde.lot_id)
        .where(Lot.matiere_id == matiere_id)
    )
    return Decimal(total or 0)
