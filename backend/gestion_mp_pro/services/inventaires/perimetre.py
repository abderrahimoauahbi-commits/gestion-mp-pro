"""Le périmètre d'un inventaire (REGLES S150–S154 ; DECISIONS N1, N3 ; K2) : les critères
choisis à l'ouverture, les matières qu'il suspend, les soldes qu'il fige, les conflits.

- Rien de coché = tout le stock (du magasin, ou de tous) ; sinon les matières qui passent
  **tous** les critères donnés (matières choisies, rôles, compositions, classes ABC).
- Les matières du périmètre sont écrites dans `inventaire_matiere` : c'est ce qui suspend leurs
  mouvements (dans son magasin, dans tous s'il est global), et rien d'autre (K2).
- Un inventaire ouvert par magasin (index unique de la base) ; un inventaire de tous les
  magasins exclut tout autre : vérifié sous le verrou `INVENTAIRE_GLOBAL` (messages C-07).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.db import Verrou, verrouiller
from gestion_mp_pro.modeles import (
    Composition,
    Inventaire,
    Lot,
    Magasin,
    Matiere,
    Mouvement,
    RoleNomenclature,
    Solde,
)
from gestion_mp_pro.modeles.enums import StatutInventaire
from gestion_mp_pro.services import donnees_moteur, horloge

CLASSES = ("A", "B", "C")
NOMS_DANS_UN_REFUS = 5
"""Un refus cite au plus 5 lots (« … » ensuite)."""


@dataclass(frozen=True)
class Criteres:
    """Les critères du périmètre (vides : tout le stock)."""

    matieres: tuple[int, ...] = ()
    roles: tuple[int, ...] = ()
    compositions: tuple[int, ...] = ()
    classes_abc: tuple[str, ...] = ()

    @property
    def vides(self) -> bool:
        """Aucun critère : tout le stock."""
        return not (self.matieres or self.roles or self.compositions or self.classes_abc)


@dataclass
class Perimetre:
    """Les matières suspendues et les soldes figés (lot, magasin, théorique)."""

    matieres: set[int]
    soldes: list[Solde] = field(default_factory=list)


def conflit(s: Session, magasin_id: int | None) -> None:
    """Un inventaire ouvert sur ce magasin ou sur tous (et, pour tous, n'importe lequel) : 409
    au message de Gestion MP corrigé (C-07). Sous le verrou des ouvertures."""
    verrouiller(s, Verrou.INVENTAIRE_GLOBAL)
    requete = select(Inventaire).where(Inventaire.statut == StatutInventaire.ouvert)
    if magasin_id is not None:
        requete = requete.where(
            (Inventaire.magasin_id == magasin_id) | Inventaire.magasin_id.is_(None)
        )
    ouvert = s.scalars(requete.order_by(Inventaire.id).limit(1)).first()
    if ouvert is None:
        return
    if ouvert.magasin_id is None:
        sur = "sur tous les magasins"
    else:
        sur = f"sur « {s.get_one(Magasin, ouvert.magasin_id).code} »"
    suite = (
        " : un inventaire de tous les magasins attend qu'il soit validé ou abandonné."
        if magasin_id is None and ouvert.magasin_id is not None
        else "."
    )
    raise Refus.etat(f"L'inventaire {ouvert.numero} est déjà ouvert {sur}{suite}")


def _inconnus(
    s: Session, modele: type[Matiere | RoleNomenclature | Composition], ids: Iterable[int]
) -> list[str]:
    """Les identifiants qui ne désignent rien."""
    voulus = list(dict.fromkeys(ids))
    if not voulus:
        return []
    connus = set(s.scalars(select(modele.id).where(modele.id.in_(voulus))))
    return [str(x) for x in voulus if x not in connus]


def verifier(s: Session, c: Criteres) -> None:
    """Matières, rôles, compositions connus ; classes A, B ou C (IR5, IR6)."""
    for modele, ids, nom in (
        (Matiere, c.matieres, "Matière inconnue"),
        (RoleNomenclature, c.roles, "Rôle inconnu"),
        (Composition, c.compositions, "Composition inconnue"),
    ):
        inconnus = _inconnus(s, modele, ids)
        if inconnus:
            raise Refus.saisie(
                f"{nom} : n° " + ", ".join(inconnus[:NOMS_DANS_UN_REFUS]) + ".",
                code="valeur_inconnue",
            )
    if any(x not in CLASSES for x in c.classes_abc):
        raise Refus.saisie("Classe ABC : A, B ou C.", code="valeur_inconnue")


def classes_abc(s: Session, jour: date | None = None) -> dict[str, str]:
    """La classe ABC de chaque matière (référence → A, B, C), calculée comme l'état du stock."""
    jour = jour or horloge.aujourd_hui()
    return {x.reference: x.classe_abc for x in etat_stock(donnees_moteur.charger_au(s, jour), jour)}


def matieres(s: Session, c: Criteres) -> set[int]:
    """Les matières qui passent tous les critères (toutes s'il n'y en a pas)."""
    requete = select(Matiere.id, Matiere.reference)
    if c.matieres:
        requete = requete.where(Matiere.id.in_(c.matieres))
    if c.roles:
        requete = requete.where(Matiere.role_id.in_(c.roles))
    if c.compositions:
        requete = requete.where(Matiere.composition_id.in_(c.compositions))
    rangs = s.execute(requete).all()
    if not c.classes_abc:
        return {ident for ident, _ in rangs}
    classes = classes_abc(s)
    return {ident for ident, ref in rangs if (classes.get(ref) or "C") in c.classes_abc}


def soldes_a_figer(s: Session, magasin_id: int | None, perimetre: set[int]) -> list[Solde]:
    """Les soldes > 0 du périmètre (dans ce magasin, ou partout), **verrouillés** : un mouvement
    en cours finit d'abord, et il est compté (S153). Un inventaire global fige la quarantaine."""
    if not perimetre:
        return []
    requete = (
        select(Solde)
        .join(Lot, Lot.id == Solde.lot_id)
        .where(Solde.quantite > 0, Lot.matiere_id.in_(perimetre))
        .order_by(Solde.magasin_id, Solde.lot_id)
        .with_for_update(of=Solde)
        .options(selectinload(Solde.lot))
        .execution_options(populate_existing=True)
    )
    if magasin_id is not None:
        requete = requete.where(Solde.magasin_id == magasin_id)
    return list(s.scalars(requete))


def bouge_apres(s: Session, jour: date, paires: set[tuple[int, int]]) -> list[str]:
    """Les lots (dans leur magasin) qui ont bougé après `jour`, du plus ancien mouvement au plus
    récent : « « RÉF », lot L (le jj/mm/aaaa) »."""
    if not paires:
        return []
    derniers = s.execute(
        select(Mouvement.lot_id, Mouvement.magasin_id, func.max(Mouvement.date_effet))
        .where(Mouvement.lot_id.in_({lot for lot, _ in paires}))
        .group_by(Mouvement.lot_id, Mouvement.magasin_id)
    ).all()
    tard = sorted((d, lot) for lot, g, d in derniers if (lot, g) in paires and d > jour)
    noms = []
    for d, lot_id in tard:
        lot = s.get_one(Lot, lot_id)
        ref = s.get_one(Matiere, lot.matiere_id).reference
        noms.append(f"« {ref} », lot {lot.numero} (le {d:%d/%m/%Y})")
    return list(dict.fromkeys(noms))


def refus_si_bouge_apres(s: Session, jour: date, paires: set[tuple[int, int]]) -> None:
    """IR7 : un comptage porte sur le stock d'aujourd'hui ; un inventaire daté avant le dernier
    mouvement d'un lot qu'il fige écrirait son écart dans le passé."""
    message = message_bouge_apres(jour, bouge_apres(s, jour, paires))
    if message:
        raise Refus.etat(message)


def message_bouge_apres(jour: date, noms: Sequence[str]) -> str:
    """Le texte de IR7 (vide si aucun lot n'a bougé)."""
    if not noms:
        return ""
    suite = " …" if len(noms) > NOMS_DANS_UN_REFUS else ""
    return (
        f"L'inventaire est daté du {jour:%d/%m/%Y}, mais des lots qu'il fige ont bougé depuis : "
        f"{', '.join(noms[:NOMS_DANS_UN_REFUS])}{suite}. Un comptage porte sur le stock "
        "d'aujourd'hui : le dater au plus tôt du dernier mouvement."
    )
