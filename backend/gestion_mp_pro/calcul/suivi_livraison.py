"""État de livraison d'un bon de commande, lu par le courriel du lundi (CALCULS B § 10.5).

Portage de `gestion_mp/api/achats.py` (`est_parti`, `livre`, `_statut_livraison`, mêmes
libellés) et du filtre des bons en retard de `gestion_mp/services/courriel.py` (`contenu`).
Les bons lus en base arrivent en petites dataclasses ; la date du jour est un paramètre.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from gestion_mp_pro.calcul.achats import echeance_commande

# ── État de livraison d'un bon (courriel du lundi) ───────────────────────────


@dataclass
class LigneBon:
    """Une ligne d'un bon de commande en base : son id et sa quantité commandée."""

    id: int
    quantite: float


@dataclass
class BonALivrer:
    """Un bon de commande lu en base (statuts de la base : envoyee, soldee, annulee…)."""

    numero: str | None
    statut: str
    lignes: list[LigneBon] = field(default_factory=list)
    eta: dt.date | None = None
    date_livraison_prevue: dt.date | None = None
    date_commande: dt.date | None = None
    delai_fournisseur: float = 0


def est_parti(bon: BonALivrer) -> bool:
    """Le bon est chez le fournisseur : cela se lit à son numéro, pas à son statut."""
    return bool(bon.numero)


def livre(
    bon: BonALivrer,
    recu: dict[int, float],
    tolerance: float,
    bloque: dict[int, float] | None = None,
) -> bool:
    """Livré ligne par ligne, à la tolérance près, net des retours — et, avec `bloque`, hors
    ce qui attend encore en quarantaine."""
    bloque = bloque or {}
    return bool(bon.lignes) and all(
        recu.get(x.id, 0.0) - bloque.get(x.id, 0.0) >= x.quantite * (1 - tolerance)
        for x in bon.lignes
    )


def _livre_ou_clos(
    bon: BonALivrer,
    recu: dict[int, float],
    bloque: dict[int, float],
    tolerance: float,
    total_recu: float,
) -> str:
    """Livré, soldé, annulé ou reçu sous réserve ; "" pour un bon encore attendu."""
    if livre(bon, recu, tolerance, bloque):
        return "🟢 Livré"
    if bon.statut == "soldee":
        return "⚫ Soldé" if total_recu > 0 else "⚫ Soldé sans livraison"
    if bon.statut == "annulee":
        return "⚫ Annulé"
    if livre(bon, recu, tolerance):
        return "🟡 Reçu sous réserve"  # tout est là, une part attend en quarantaine
    return ""


def statut_livraison(
    bon: BonALivrer,
    recu: dict[int, float],
    bloque: dict[int, float],
    tolerance: float,
    *,
    jour: dt.date,
    retard_tolere: float = 0,
) -> str:
    """L'état de livraison du bon (`_statut_livraison`) ; rien pour un bon pas encore parti.
    En retard au-delà du retard toléré, à compter de l'ETA, de la date promise, sinon de la
    date du bon plus le délai du fournisseur."""
    if not est_parti(bon):
        return ""
    total_recu = sum(recu.get(x.id, 0.0) for x in bon.lignes)
    clos = _livre_ou_clos(bon, recu, bloque, tolerance, total_recu)
    if clos:
        return clos
    prevue = echeance_commande(
        bon.eta, bon.date_livraison_prevue, bon.date_commande, bon.delai_fournisseur
    )
    a_l_heure = (
        prevue is None or dt.date.fromordinal(prevue.toordinal() + int(retard_tolere)) >= jour
    )
    if total_recu > 0:
        return "🟡 En cours" if a_l_heure else "🟠 Partiel retard"
    return "⚪ Attendu" if a_l_heure else "🔴 En retard"


STATUTS_ATTENDUS = ("envoyee", "confirmee", "a_approuver")
"""Les bons du courriel du lundi : numérotés et encore attendus."""


def commandes_en_retard(
    bons: list[BonALivrer],
    recu: dict[int, float],
    bloque: dict[int, float],
    tolerance: float,
    *,
    jour: dt.date,
    retard_tolere: float = 0,
) -> list[BonALivrer]:
    """Les bons en retard du courriel du lundi : numérotés, envoyés, confirmés ou à approuver,
    dont l'état contient « retard » (« reçu sous réserve » n'en est pas un). Dans l'ordre reçu
    (id croissant)."""
    return [
        x
        for x in bons
        if x.numero is not None
        and x.statut in STATUTS_ATTENDUS
        and "retard"
        in statut_livraison(
            x, recu, bloque, tolerance, jour=jour, retard_tolere=retard_tolere
        ).lower()
    ]
