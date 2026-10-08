"""Outils de la petite usine du chargeur (lot S4) : instants de l'usine, identifiants gardés,
ajout d'une fiche, opération validée, écriture dans le magasin principal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from fabriques.stock import magasin
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Lot, Motif, Operation
from gestion_mp_pro.modeles.enums import DocumentMouvement, TypeMouvement, TypeOperation
from gestion_mp_pro.services import horloge, stock


def instant(annee: int, mois: int, jour: int, heure: int = 10) -> datetime:
    """Un instant à l'heure de l'usine (avec fuseau, comme la base les garde)."""
    return datetime(annee, mois, jour, heure, tzinfo=horloge.FUSEAU)


@dataclass
class Monde:
    """Ce que les essais relisent : identifiants des fiches et des mouvements."""

    ids: dict[str, int] = field(default_factory=dict)
    mouvements: dict[str, int] = field(default_factory=dict)


def ajouter[T](s: Session, objet: T) -> T:
    """Ajoute une fiche et l'écrit (son identifiant est connu)."""
    s.add(objet)
    s.flush()
    return objet


def motif(s: Session, libelle: str) -> int:
    """L'identifiant d'un motif semé."""
    return s.scalars(select(Motif.id).where(Motif.libelle == libelle)).one()


def operation(
    s: Session, w: Monde, genre: TypeOperation, numero: str, jour: date, **champs: object
) -> stock.Piece:
    """Une opération validée (numéro gardé dans `w.ids`) et la pièce qui écrit pour elle."""
    o = ajouter(
        s,
        Operation(
            type=genre,
            numero=numero,
            statut="validee",
            date=jour,
            validee_le=instant(jour.year, jour.month, jour.day),
            **champs,
        ),
    )
    w.ids[numero] = o.id
    return stock.Piece(DocumentMouvement.operation, o.id, numero)


def ecrire(  # noqa: PLR0913, PLR0917 — décor d'essai
    s: Session,
    w: Monde,
    cle: str,
    x: Lot,
    kg: float,
    jour: date,
    piece: stock.Piece,
    type_: TypeMouvement,
    prix: float = 0,
    **liens: object,
) -> None:
    """Une écriture dans le magasin principal, par Karim ; son numéro gardé sous `cle`."""
    m = stock.ecrire(
        s,
        type=type_,
        lot=x,
        magasin_id=magasin(s).id,
        quantite=kg,
        jour=jour,
        piece=piece,
        auteur_id=w.ids["karim"],
        prix=prix,
        liens=stock.Liens(**liens),  # type: ignore[arg-type]
    )
    w.mouvements[cle] = m.id
