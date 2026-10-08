"""Agrégats du journal et des commandes, en une passe, pour `etat_stock`.

Portage de la première moitié de `moteur.etat_stock` : stock initial, entrées, sorties,
ajustements, retours, magasins, sorties nettes par mois clos (XYZ), consommation réelle par
mois de la fenêtre de réalisation, dernières entrées et sorties ; bons attendus et en
préparation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.achats import pas_partie, reste_a_livrer
from gestion_mp_pro.calcul.constantes import MOIS, POUSSIERE
from gestion_mp_pro.calcul.modele import Donnees, Mouvement
from gestion_mp_pro.calcul.outils import fin_de_mois

CleMois = tuple[int, int]
"""(année, mois)."""


def _flottants() -> defaultdict[str, float]:
    return defaultdict(float)


def _par_rang() -> defaultdict[int, float]:
    return defaultdict(float)


@dataclass
class Agregat:
    """Ce que le journal dit d'une référence."""

    stock_initial: float = 0.0
    entrees: float = 0.0
    sorties: float = 0.0
    ajustements: float = 0.0
    retours_fournisseur: float = 0.0
    derniere_sortie: date | None = None
    derniere_entree: date | None = None
    premiere_sortie: date | None = None
    magasins: defaultdict[str, float] = field(default_factory=_flottants)
    sorties_par_mois: defaultdict[int, float] = field(default_factory=_par_rang)
    reel_par_mois: defaultdict[int, float] = field(default_factory=_par_rang)

    def stock_net(self) -> float:
        """Le stock net du journal ; sous le gramme, c'est zéro (restes d'arrondi)."""
        net = (
            self.stock_initial
            + self.entrees
            + self.sorties
            + self.ajustements
            + self.retours_fournisseur
        )
        if abs(net) < POUSSIERE:
            net = 0.0
        return net

    def en_magasins(self, codes: list[str]) -> float:
        """Le stock dans ces magasins (la quarantaine)."""
        return sum(self.magasins.get(m, 0.0) for m in codes)


def stock_net_de(agregat: Agregat | None) -> float:
    """Le stock net d'une référence (0 sans écriture)."""
    return agregat.stock_net() if agregat else 0.0


def mois_xyz(date_ref: date) -> dict[CleMois, int]:
    """Les douze mois **clos** de la variabilité de la demande (le mois entamé n'y est pas)."""
    fins = [fin_de_mois(date_ref, -i - 1) for i in range(MOIS - 1, -1, -1)]
    return {(f.year, f.month): i for i, f in enumerate(fins)}


def _dates(agregat: Agregat, m: Mouvement, annulees: set[int]) -> None:
    reelle = m.contrepasse_id is None and (m.id is None or m.id not in annulees)
    if (
        m.type in ("STOCK_INITIAL", "ENTREE_RECEPTION", "RETOUR_PRODUCTION")
        and m.quantite_signee > 0
        and reelle
        and (agregat.derniere_entree is None or m.date > agregat.derniere_entree)
    ):
        agregat.derniere_entree = m.date
    if m.type == "SORTIE_PROD" and reelle:
        if agregat.derniere_sortie is None or m.date > agregat.derniere_sortie:
            agregat.derniere_sortie = m.date
        if agregat.premiere_sortie is None or m.date < agregat.premiere_sortie:
            agregat.premiere_sortie = m.date


def _quantites(
    agregat: Agregat, m: Mouvement, xyz: dict[CleMois, int], fenetre: dict[CleMois, int]
) -> None:
    """Les cumuls par type ; une sortie contre-passée se retranche, un reliquat rendu
    n'a pas été consommé."""
    signee = m.quantite_signee
    cle = (m.date.year, m.date.month)
    if m.type == "STOCK_INITIAL":
        agregat.stock_initial += m.quantite
    elif m.type in ("ENTREE_RECEPTION", "RETOUR_PRODUCTION"):
        agregat.entrees += signee
        if m.type == "RETOUR_PRODUCTION":
            if cle in fenetre:
                agregat.reel_par_mois[fenetre[cle]] -= signee
            if cle in xyz:
                agregat.sorties_par_mois[xyz[cle]] -= signee
    elif m.type == "SORTIE_PROD":
        agregat.sorties += signee
        if cle in xyz:
            agregat.sorties_par_mois[xyz[cle]] += -signee
        if cle in fenetre:
            agregat.reel_par_mois[fenetre[cle]] -= signee
    elif m.type == "AJUSTEMENT_INVENTAIRE":
        agregat.ajustements += signee
    elif m.type == "RETOUR_FOURNISSEUR":
        agregat.retours_fournisseur += signee


def _magasins(agregat: Agregat, m: Mouvement) -> None:
    """L'entrée crédite la destination, la sortie débite la source, le transfert déplace."""
    if m.type == "TRANSFERT_MAGASIN":
        if m.magasin_destination:
            agregat.magasins[m.magasin_destination] += m.quantite
        if m.magasin_source:
            agregat.magasins[m.magasin_source] -= m.quantite
    elif m.magasin_destination:
        agregat.magasins[m.magasin_destination] += m.quantite_signee
    elif m.magasin_source:
        agregat.magasins[m.magasin_source] += m.quantite_signee


def agreger_journal(
    donnees: Donnees, date_ref: date, fenetre: dict[CleMois, int]
) -> dict[str, Agregat]:
    """Les agrégats du journal par référence ; `fenetre` : rang de chaque mois de la fenêtre
    de réalisation (vide sans fenêtre)."""
    xyz = mois_xyz(date_ref)
    annulees = {m.contrepasse_id for m in donnees.mouvements if m.contrepasse_id is not None}
    agregats: dict[str, Agregat] = defaultdict(Agregat)
    for mouvement in donnees.mouvements:
        agregat = agregats[mouvement.reference]
        _dates(agregat, mouvement, annulees)
        _quantites(agregat, mouvement, xyz, fenetre)
        _magasins(agregat, mouvement)
    return agregats


Attendu = tuple[float, date | None]
"""(reste à livrer, arrivée attendue)."""


def commandes_en_cours(
    donnees: Donnees,
) -> tuple[dict[str, list[Attendu]], dict[str, list[tuple[float, str]]]]:
    """Les restes attendus par référence (bons partis) et ce qui est en préparation (bons en
    brouillon ou à approuver : pas attendus, mais déjà proposés)."""
    en_commande: dict[str, list[Attendu]] = defaultdict(list)
    en_preparation: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for commande in donnees.commandes:
        if commande.statut == "Annulée":
            continue
        if pas_partie(commande):
            for ligne in commande.lignes:
                reste = ligne.quantite_commandee - ligne.quantite_recue
                if reste > POUSSIERE:
                    en_preparation[ligne.reference].append((reste, commande.numero))
            continue
        for ligne in commande.lignes:
            reste = reste_a_livrer(commande, ligne, donnees.parametres)
            if reste > 0:
                en_commande[ligne.reference].append((reste, commande.arrivee_attendue))
    return en_commande, en_preparation
