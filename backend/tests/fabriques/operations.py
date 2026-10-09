"""Fabriques des opérations et des inventaires (lot D5), sur celles du stock (lot S4).

    from fabriques.operations import acteur, motif, ordre_valide, ligne, saisie, quarantaine

Les référentiels viennent des fabriques du lot D1 (`fabriques.referentiels`, avec `s=` : dans
la transaction de l'essai), les lots et le stock de celles du lot S4 (`fabriques.stock`) ; un
ordre de fabrication validé est posé directement avec ses sorties (le lot D6 n'est pas encore
là), par le seul chemin d'écriture du stock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from fabriques import referentiels as ref
from fabriques.stock import JOUR, entree, lot, magasin, unique, utilisateur
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Lot, Magasin, Matiere, Motif, Ordre
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    Role,
    StatutOrdre,
    TypeMagasin,
    TypeMouvement,
    TypeOperation,
)
from gestion_mp_pro.services import horloge, stock
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.operations import SaisieLigne, SaisieOperation

NOMS = {
    Role.direction: "Direction",
    Role.achats: "Achats",
    Role.alimentation: "Karim",
    Role.administrateur: "Technique",
}


def acteur(s: Session, role: Role = Role.achats, nom: str | None = None) -> Acteur:
    """Une personne connectée de ce rôle (un compte décor, sans code)."""
    u = utilisateur(s, nom or NOMS[role], role)
    return Acteur(u.id, u.identifiant, u.nom, role)


def motif(s: Session, type_: str, libelle: str) -> int:
    """L'identifiant d'un motif semé (« Rangement », « Libération de quarantaine »…)."""
    return s.scalars(
        select(Motif.id).where(Motif.type_operation == type_, Motif.libelle == libelle)
    ).one()


def quarantaine(s: Session) -> Magasin:
    """Le magasin de quarantaine semé."""
    return magasin(s, TypeMagasin.quarantaine)


def ordre_valide(
    s: Session, sorties: list[tuple[Lot, float]], le: date = JOUR, g: Magasin | None = None
) -> Ordre:
    """Un ordre validé et ses sorties vers les machines (comme le ferait le lot D6)."""
    g = g or magasin(s)
    o = Ordre(
        numero=unique("OF"), statut=StatutOrdre.valide, date=le, magasin_id=g.id,
        valide_le=horloge.maintenant(),
    )  # fmt: skip
    s.add(o)
    s.flush()
    piece = stock.Piece(DocumentMouvement.ordre, o.id, o.numero or "")
    for x, q in sorties:
        stock.ecrire(
            s, type=TypeMouvement.SORTIE, lot=x, magasin_id=g.id, quantite=-Decimal(str(q)),
            jour=le, piece=piece, auteur_id=None, liens=stock.Liens(ordre_id=o.id),
        )  # fmt: skip
    return o


def ligne(matiere_id: int, magasin_id: int, quantite: float | str, **champs: object) -> SaisieLigne:
    """Une ligne saisie (kg par défaut)."""
    return SaisieLigne(
        matiere_id=matiere_id,
        magasin_id=magasin_id,
        quantite=Decimal(str(quantite)),
        **champs,  # type: ignore[arg-type]
    )


def saisie(
    type_: TypeOperation | str, *lignes: SaisieLigne, le: date = JOUR, **champs: object
) -> SaisieOperation:
    """Une opération saisie."""
    return SaisieOperation(
        type=TypeOperation(type_),
        date=le,
        lignes=tuple(lignes),
        **champs,  # type: ignore[arg-type]
    )


@dataclass
class Monde:
    """Le stock de départ des essais hérités (`test_stock_atelier::monde`) : deux lots de poil,
    un de trame, un de franges dans le magasin courant, un lot de poil en quarantaine."""

    a1: Matiere
    a2: Matiere
    a3: Matiere
    courant: Magasin
    quarantaine: Magasin
    fournisseur: int
    lots: dict[str, Lot] = field(default_factory=dict)


def monde(s: Session, le: date = JOUR, courant: Magasin | None = None) -> Monde:
    """Le décor : E POIL BLEU (2 kg la bobine, 50 bobines la palette), E TRAME, E FRANGE (au
    mètre), entrés la veille de `le` à 20, 22, 8, 1 et 20 MAD/kg."""
    f = ref.fournisseur(s=s)
    a1 = s.get_one(
        Matiere,
        ref.matiere(
            unique("E POIL BLEU"),
            fournisseur_id=f,
            s=s,
            poids_bobine=Decimal(2),
            bobines_palette=Decimal(50),
        ),
    )
    a2 = s.get_one(Matiere, ref.matiere(unique("E TRAME"), role="Trame", fournisseur_id=f, s=s))
    a3 = s.get_one(Matiere, ref.matiere(unique("E FRANGE"), role="Franges", fournisseur_id=f, s=s))
    m = Monde(a1, a2, a3, courant or magasin(s), quarantaine(s), f)
    veille = le - timedelta(days=1)
    for numero, mat, g, q, prix in (
        ("E-L1", a1, m.courant, 500, 20), ("E-L2", a1, m.courant, 300, 22),
        ("E-T1", a2, m.courant, 400, 8), ("E-F1", a3, m.courant, 1000, 1),
        ("E-Q1", a1, m.quarantaine, 100, 20),
    ):  # fmt: skip
        x = lot(s, mat, unique(numero), entre_le=veille)
        entree(s, x, q, veille, g, prix=prix)
        m.lots[numero] = x
    return m
