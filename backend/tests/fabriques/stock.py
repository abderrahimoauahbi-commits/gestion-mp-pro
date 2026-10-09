"""Fabriques du stock (lot S4) : une session d'essai annulée à la fin, une base vidée de son
activité **dans la transaction** de l'essai, et de quoi écrire du stock par le seul chemin.

    from fabriques.stock import s, vider, matiere, lot, entree, …   # noqa: F401 (fixture `s`)

Les référentiels créés ici sont minimaux (le lot D1 écrira les siens) ; leurs noms sont uniques
(compteur), si bien que des essais qui valident leur transaction (concurrence, cache) ne gênent
pas les autres.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal

import base_connue
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import (
    Fournisseur,
    Inventaire,
    InventaireMatiere,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    RoleNomenclature,
    Utilisateur,
)
from gestion_mp_pro.modeles.enums import DocumentMouvement, Role, TypeMagasin, TypeMouvement
from gestion_mp_pro.services import lots, stock

JOUR = date(2026, 10, 8)
"""Le jour des essais (horloge figée par `conftest`)."""


_RANG = itertools.count(1)


def unique(prefixe: str) -> str:
    """Un nom jamais vu dans la séance (« E4-17 »)."""
    return f"{prefixe}-{next(_RANG)}"


def jour(decalage: int) -> date:
    """Le jour des essais décalé de `decalage` jours (−1 : hier)."""
    return JOUR + timedelta(days=decalage)


@pytest.fixture
def s() -> Iterator[Session]:
    """Une session dont la transaction est annulée à la fin de l'essai."""
    session = fabrique()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def vider(s: Session) -> None:
    """La base d'une installation neuve (`base_connue.remettre` : activité et référentiels vidés,
    semences et réglages à leur défaut, comptes gardés), dans la transaction en cours (annulée à
    la fin de l'essai : les autres essais ne voient rien)."""
    base_connue.remettre(s.connection())


def utilisateur(s: Session, nom: str = "Karim", role: Role = Role.alimentation) -> Utilisateur:
    """Un compte (sans code : un décor)."""
    u = Utilisateur(identifiant=unique("essai.stock").lower(), nom=nom, role=role)
    s.add(u)
    s.flush()
    return u


def fournisseur(
    s: Session, nom: str | None = None, devise: str = "MAD", **champs: object
) -> Fournisseur:
    """Un fournisseur."""
    f = Fournisseur(nom=nom or unique("FOURNISSEUR"), devise=devise, pays="MAROC", **champs)
    s.add(f)
    s.flush()
    return f


def role(s: Session, code: str = "Poil") -> RoleNomenclature:
    """Un rôle semé (Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique)."""
    return s.scalars(select(RoleNomenclature).where(RoleNomenclature.code == code)).one()


def matiere(
    s: Session,
    reference: str | None = None,
    role_code: str = "Poil",
    fournisseur_id: int | None = None,
    **champs: object,
) -> Matiere:
    """Une matière (densité posée d'office pour un rôle compté au mètre)."""
    r = role(s, role_code)
    if r.lineaire:
        champs.setdefault("densite", Decimal("0.014"))
    m = Matiere(
        reference=reference or unique("FIL"), role_id=r.id, fournisseur_id=fournisseur_id, **champs
    )
    s.add(m)
    s.flush()
    return m


def magasin(s: Session, genre: TypeMagasin = TypeMagasin.stock_courant) -> Magasin:
    """Le magasin semé de ce type (« Magasin principal » ou « Quarantaine »)."""
    return s.scalars(select(Magasin).where(Magasin.type == genre).order_by(Magasin.id)).first()  # type: ignore[return-value]


def autre_magasin(s: Session, code: str | None = None, actif: bool = True) -> Magasin:
    """Un magasin courant de plus."""
    g = Magasin(code=code or unique("MAG"), nom="Magasin d'essai", actif=actif)
    s.add(g)
    s.flush()
    return g


def lot(
    s: Session, m: Matiere, numero: str | None = None, entre_le: date = JOUR, **champs: object
) -> Lot:
    """Un lot (par le chemin des lots)."""
    return lots.lot_ou_creer(s, m.id, numero or unique("L"), entre_le, **champs)  # type: ignore[arg-type]


REPRISE = stock.Piece(DocumentMouvement.reprise, None, "")
"""Un document sans clé (stock repris) : pour écrire sans document métier."""


def entree(  # noqa: PLR0917 — décor d'essai, appelé à la position
    s: Session,
    x: Lot,
    quantite: float | Decimal | str,
    le: date = JOUR,
    g: Magasin | None = None,
    prix: float | Decimal = 0,
    devise: str = "MAD",
    type: TypeMouvement = TypeMouvement.OUVERTURE,
    **arguments: object,
) -> Mouvement:
    """Une entrée de stock (ouverture par défaut)."""
    return stock.ecrire(
        s,
        type=type,
        lot=x,
        magasin_id=(g or magasin(s)).id,
        quantite=quantite,
        jour=le,
        piece=arguments.pop("piece", REPRISE),  # type: ignore[arg-type]
        auteur_id=arguments.pop("auteur_id", None),  # type: ignore[arg-type]
        prix=prix,
        devise=devise,
        **arguments,  # type: ignore[arg-type]
    )


def sortie(  # noqa: PLR0917 — décor d'essai, appelé à la position
    s: Session,
    x: Lot,
    quantite: float | Decimal | str,
    le: date = JOUR,
    g: Magasin | None = None,
    type: TypeMouvement = TypeMouvement.SORTIE,
) -> Mouvement:
    """Une sortie (vers les machines par défaut, sans document : stock repris)."""
    return entree(s, x, -Decimal(str(quantite)), le, g, type=type)


def inventaire_ouvert(
    s: Session, g: Magasin | None, matieres: list[Matiere], numero: str | None = None
) -> Inventaire:
    """Un inventaire ouvert sur un magasin (`None` : tous), son périmètre figé."""
    i = Inventaire(numero=numero or unique("INV"), date=JOUR, magasin_id=g.id if g else None)
    s.add(i)
    s.flush()
    s.add_all(InventaireMatiere(inventaire_id=i.id, matiere_id=m.id) for m in matieres)
    s.flush()
    return i
