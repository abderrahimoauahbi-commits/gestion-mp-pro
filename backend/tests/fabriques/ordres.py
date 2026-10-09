"""Fabriques des ordres de fabrication (lot D6), sur celles du stock (S4), des référentiels (D1)
et des opérations (D5).

    from fabriques.ordres import atelier, saisie, brouillon, valide, retour, ordre_valide

- `atelier(s)` : le décor de `test_stock_atelier` (lots de poil, trame, franges dans deux
  magasins à lui, entrés la veille) et deux qualités à recette complète (E1, E2).
- `saisie(...)`, `brouillon(...)`, `valide(...)` : un ordre par le **service** (le vrai chemin).
- `retour(...)` : un retour des machines par le service des opérations (D5), validé ou non ;
  `retour_repris(...)` : un retour écrit comme la reprise de l'ERP Fil (sans document).
- `ordre_valide(qualite_id, m2)` : un ordre validé **en base** (validé, l'API le voit) par le
  service, daté d'aujourd'hui, avec une sortie d'un kilo d'un lot à lui — remplace la fabrique de
  D2 ; `ordre_repris(...)` : un ordre d'une date passée écrit comme la reprise (décor : sans
  passer par la règle « les numéros suivent les dates », sans sortie).

Les ordres validés en base par les essais sont datés **d'aujourd'hui** : le jour fixe des
essais est le plus récent possible, si bien qu'aucun ordre laissé par un autre essai ne les
refuse (les numéros suivent les dates).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from fabriques import referentiels as ref
from fabriques.operations import Monde, acteur, monde, motif
from fabriques.stock import JOUR, unique
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import Lot, Mouvement, Operation, Ordre, OrdreQualite
from gestion_mp_pro.modeles.enums import (
    DocumentMouvement,
    Role,
    StatutOrdre,
    TypeMouvement,
    TypeOperation,
)
from gestion_mp_pro.services import horloge, ordres, stock
from gestion_mp_pro.services import operations as ops
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.conversions import Unite

__all__ = [
    "JOUR",
    "Atelier",
    "acteur",
    "atelier",
    "brouillon",
    "ordre_repris",
    "ordre_valide",
    "retour",
    "retour_repris",
    "saisie",
    "valide",
]


@dataclass
class Atelier:
    """Le décor : le monde de D5 et deux qualités (E1 : poil 1 kg/m², trame 0,5 ; E2 : poil 2,
    trame 0,5), recettes complètes (poil 100 %, trame 100 %)."""

    m: Monde
    e1: int
    e2: int

    def lot(self, numero: str) -> Lot:
        """Un lot du décor (« E-L1 », « E-T1 »…)."""
        return self.m.lots[numero]


def atelier(s: Session, le: date = JOUR) -> Atelier:
    """Le décor des ordres, dans la transaction de l'essai (lots entrés la veille de `le`)."""
    m = monde(s, le)
    recette: dict[int, float | str] = {m.a1.id: 100, m.a2.id: 100}
    e1 = ref.qualite(unique("E1"), recette=recette, poids={"Poil": 1, "Trame": "0.5"}, s=s)
    e2 = ref.qualite(unique("E2"), recette=recette, poids={"Poil": 2, "Trame": "0.5"}, s=s)
    return Atelier(m, e1, e2)


def saisie(
    magasin_id: int,
    lignes: Iterable[tuple[Lot | int, float | str] | tuple[Lot | int, float | str, Unite]],
    qualites: Iterable[tuple[int, float | str]] = (),
    *,
    le: date = JOUR,
    metier_id: int | None = None,
    commentaire: str = "",
) -> ordres.SaisieOrdre:
    """Un ordre saisi : lignes (lot, quantité[, unité]), qualités (id, m²)."""
    faites = []
    for x in lignes:
        lot = x[0] if isinstance(x[0], int) else x[0].id
        unite = x[2] if len(x) == 3 else Unite.kg  # noqa: PLR2004
        faites.append(ordres.SaisieLigne(lot, Decimal(str(x[1])), unite))
    return ordres.SaisieOrdre(
        date=le, magasin_id=magasin_id, metier_id=metier_id, commentaire=commentaire,
        qualites=tuple(ordres.SaisieQualite(q, Decimal(str(m2))) for q, m2 in qualites),
        lignes=tuple(faites),
    )  # fmt: skip


def brouillon(s: Session, qui: Acteur, e: ordres.SaisieOrdre) -> Ordre:
    """Un brouillon, par le service."""
    return ordres.creer(s, qui, e)


def valide(s: Session, qui: Acteur, e: ordres.SaisieOrdre) -> Ordre:
    """Un ordre créé puis validé, par le service."""
    o = ordres.creer(s, qui, e)
    return ordres.valider(s, qui, o.id, o.version)


def retour(
    s: Session,
    qui: Acteur,
    o: Ordre,
    lots: Iterable[tuple[Lot, float | str]],
    *,
    le: date = JOUR,
    valider: bool = True,
) -> Operation:
    """Un retour des machines de l'ordre, par le service des opérations (D5)."""
    lignes = tuple(
        ops.SaisieLigne(matiere_id=x.matiere_id, magasin_id=o.magasin_id,
                        quantite=Decimal(str(q)), lot_id=x.id)
        for x, q in lots
    )  # fmt: skip
    e = ops.SaisieOperation(
        type=TypeOperation.retour_machine, date=le, lignes=lignes, ordre_id=o.id,
        motif_id=motif(s, TypeOperation.retour_machine, "Reliquat de fin d'ordre"),
    )  # fmt: skip
    return ops.creer(s, qui, e, valider=valider)


def retour_repris(s: Session, o: Ordre, x: Lot, kg: float | str, le: date = JOUR) -> Mouvement:
    """Un retour comme ceux que la reprise de l'ERP Fil a écrits : au journal de l'ordre, sans
    document « Retour des machines »."""
    return stock.ecrire(
        s, type=TypeMouvement.RETOUR_MACHINE, lot=x, magasin_id=o.magasin_id,
        quantite=Decimal(str(kg)), jour=le, piece=stock.Piece(DocumentMouvement.reprise),
        auteur_id=None, liens=stock.Liens(ordre_id=o.id),
    )  # fmt: skip


def ordre_valide(
    qualite_id: int, m2: float | str, *, metier_id: int | None = None, s: Session | None = None
) -> int:
    """Un ordre validé (aujourd'hui) qui tisse `m2` d'une qualité, par le service : un kilo
    d'une matière à lui sort d'un magasin à lui."""

    def faire(x: Session) -> int:
        g = ref.magasin(s=x)
        lot = ref.stock_initial(ref.matiere(s=x), 1, magasin_id=g, s=x)
        e = saisie(g, [(lot, 1)], [(qualite_id, m2)], le=horloge.aujourd_hui(),
                   metier_id=metier_id)  # fmt: skip
        return valide(x, acteur(x, Role.alimentation), e).id

    return ref._ecrire(s, faire)


def ordre_repris(
    qualite_id: int,
    m2: float | str,
    *,
    jour: date,
    metier_id: int | None = None,
    s: Session | None = None,
) -> int:
    """Un ordre validé d'une date passée, écrit en base comme la reprise de Gestion MP : sans
    sortie, sans prévu figé, hors de la série des numéros."""

    def faire(x: Session) -> int:
        o = Ordre(
            numero=unique("OF-R"), statut=StatutOrdre.valide, date=jour,
            magasin_id=ref.magasin_seme(s=x), metier_id=metier_id,
            valide_le=datetime.combine(jour, time(12), horloge.FUSEAU),
        )  # fmt: skip
        x.add(o)
        x.flush()
        x.add(OrdreQualite(ordre_id=o.id, qualite_id=qualite_id, m2=Decimal(str(m2))))
        return o.id

    return ref._ecrire(s, faire)
