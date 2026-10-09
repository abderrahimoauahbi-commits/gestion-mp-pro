"""Ce que toutes les parties du chargeur partagent : les noms par identifiant (matière, lot,
fournisseur, magasin, compte, rôle), lus une fois, et les conversions de la base au moteur.

Le moteur reçoit des `float` (C2 : la base garde des `Decimal` exacts, le moteur calcule comme
Gestion MP) et des instants **sans fuseau, à l'heure de l'usine** (ceux du journal de Gestion
MP, que `a_la_date` et le plan comparent à des `datetime.combine(jour, …)`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.modeles import (
    Fournisseur,
    Lot,
    Magasin,
    Matiere,
    RoleNomenclature,
    Utilisateur,
)
from gestion_mp_pro.services import horloge


@dataclass(frozen=True)
class Noms:
    """Les clés textuelles du moteur, par identifiant de la base."""

    references: dict[int, str]
    fournisseurs: dict[int, str]
    magasins: dict[int, str]
    utilisateurs: dict[int, str]
    roles: dict[int, str]
    lots: dict[int, str]
    fournisseur_du_lot: dict[int, int | None]
    matiere_du_lot: dict[int, int]

    def utilisateur(self, ident: int | None) -> str:
        """Le nom d'un compte (vide : système, reprise sans auteur)."""
        return self.utilisateurs.get(ident, "") if ident is not None else ""

    def fournisseur(self, ident: int | None) -> str:
        """Le nom d'un fournisseur (vide s'il n'y en a pas)."""
        return self.fournisseurs.get(ident, "") if ident is not None else ""

    def magasin(self, ident: int | None) -> str:
        """Le code d'un magasin (vide s'il n'y en a pas)."""
        return self.magasins.get(ident, "") if ident is not None else ""


def lire_noms(s: Session) -> Noms:
    """Six requêtes, quelle que soit la taille de la base."""
    lots = s.execute(select(Lot.id, Lot.numero, Lot.fournisseur_id, Lot.matiere_id)).all()
    return Noms(
        references=dict(s.execute(select(Matiere.id, Matiere.reference)).all()),
        fournisseurs=dict(s.execute(select(Fournisseur.id, Fournisseur.nom)).all()),
        magasins=dict(s.execute(select(Magasin.id, Magasin.code)).all()),
        utilisateurs=dict(s.execute(select(Utilisateur.id, Utilisateur.nom)).all()),
        roles=dict(s.execute(select(RoleNomenclature.id, RoleNomenclature.code)).all()),
        lots={x.id: x.numero for x in lots},
        fournisseur_du_lot={x.id: x.fournisseur_id for x in lots},
        matiere_du_lot={x.id: x.matiere_id for x in lots},
    )


def nombre(valeur: Decimal | float | int | None) -> float:
    """Un nombre de la base pour le moteur (`NULL` : 0, comme les zéros de Gestion MP)."""
    return float(valeur) if valeur is not None else 0.0


def nombre_ou_rien(valeur: Decimal | float | None) -> float | None:
    """Un nombre facultatif (`NULL` reste `None`)."""
    return float(valeur) if valeur is not None else None


def heure_usine(instant: datetime) -> datetime:
    """Un instant de la base (avec fuseau) à l'heure de l'usine, sans fuseau, pour le moteur."""
    if instant.tzinfo is None:
        return instant
    return instant.astimezone(horloge.FUSEAU).replace(tzinfo=None)


def a_l_usine(instant: datetime | None) -> datetime | None:
    """`heure_usine` d'un instant facultatif (`NULL` reste `None`)."""
    return heure_usine(instant) if instant is not None else None
