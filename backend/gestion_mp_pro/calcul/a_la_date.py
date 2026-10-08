"""Rejouer les données au soir d'une date (CALCULS A § 3.3) — portage de `moteur.a_la_date`.

Le journal, les réceptions, les commandes, les prix payés et les ordres sont tronqués à la
date ; une commande reprend ce qu'elle avait reçu ce jour-là (et redevient ouverte si elle a
été soldée ou annulée après). Le catalogue, les réglages et les dossiers restent ceux
d'aujourd'hui ; les soldes tenus ne valent plus (None) ; le montage des métiers, sans
historique, ne compte pas avant aujourd'hui.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date

from gestion_mp_pro.calcul.constantes import EPSILON, STATUTS_BC_CLOS
from gestion_mp_pro.calcul.modele import Commande, Donnees

CleBon = tuple[str, str]
"""(numéro du bon, référence)."""


def derniere_date(donnees: Donnees) -> date:
    """La dernière date écrite dans les données (mémorisée sur l'objet)."""
    if donnees.derniere_date is not None:
        return donnees.derniere_date
    jours = [m.date for m in donnees.mouvements]
    jours += [r.date_reception for r in donnees.receptions if r.date_reception]
    jours += [c.date_bc for c in donnees.commandes if c.date_bc]
    jours += [p.date_bc for p in donnees.historique_prix if p.date_bc]
    jours += [o.date for o in donnees.ordres if o.date]
    # Un bon clos à la main après la date était encore attendu ce jour-là.
    jours += [
        q.date()
        for c in donnees.commandes
        for q in (c.solde_a_la_main_le, c.annulee_le)
        if q is not None
    ]
    derniere = max(jours, default=date.min)
    donnees.derniere_date = derniere
    return derniere


def _recu_apres(donnees: Donnees, date_ref: date) -> tuple[dict[CleBon, float], set[str]]:
    """Ce que les réceptions validées après la date ont apporté à chaque ligne de bon."""
    recu: dict[CleBon, float] = defaultdict(float)
    bons: set[str] = set()
    for r in donnees.receptions:
        if r.date_reception is None or r.date_reception <= date_ref or r.statut != "Validée":
            continue
        for ligne in r.lignes:
            bon = ligne.numero_bc or r.numero_bc
            if bon and ligne.statut_qualite != "Refusé":
                recu[(bon, ligne.reference)] += ligne.quantite_pesee
                bons.add(bon)
    return recu, bons


def _rendre_les_retours(
    donnees: Donnees, date_ref: date, recu: dict[CleBon, float], bons: set[str]
) -> None:
    """Ce qui est reparti chez le fournisseur après la date était encore reçu ce jour-là : on
    le rend au reçu, au prorata des pesées du lot, sans dépasser ce que chaque ligne a apporté."""
    rendu: dict[tuple[str, str], float] = defaultdict(float)
    for m in donnees.mouvements:
        if m.type == "RETOUR_FOURNISSEUR" and m.date > date_ref:
            rendu[(m.reference, m.lot_fournisseur)] -= m.quantite_signee
    if not any(abs(q) > EPSILON for q in rendu.values()):
        return
    pesees: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for r in donnees.receptions:
        if r.statut != "Validée":
            continue
        for ligne in r.lignes:
            bon = ligne.numero_bc or r.numero_bc
            cle = (ligne.reference, ligne.lot_fournisseur)
            if bon and ligne.statut_qualite != "Refusé" and cle in rendu:
                pesees[cle].append((bon, ligne.quantite_pesee))
    for cle, lignes_lot in pesees.items():
        total = sum(q for _, q in lignes_lot)
        for bon, q in lignes_lot:
            if total > 0:
                recu[(bon, cle[0])] -= min(q, rendu[cle] * q / total)
                bons.add(bon)


def statut_ouvert(commande: Commande) -> str:
    """Le statut d'un bon parti et encore attendu : « Confirmée » si tous ses prix le sont,
    sinon « Envoyée » (comme le chargeur le lit)."""
    lignes = commande.lignes
    return "Confirmée" if lignes and all(x.prix_confirme for x in lignes) else "Envoyée"


def _commande_au(
    commande: Commande, date_ref: date, recu: dict[CleBon, float], bons: set[str]
) -> Commande:
    clos_apres = any(
        q is not None and q.date() > date_ref
        for q in (commande.solde_a_la_main_le, commande.annulee_le)
    )
    if clos_apres and commande.statut in STATUTS_BC_CLOS:
        commande = replace(
            commande, statut=statut_ouvert(commande), solde_a_la_main_le=None, annulee_le=None
        )
    if commande.numero not in bons:
        return commande
    return replace(
        commande,
        statut=statut_ouvert(commande) if commande.statut == "Soldée" else commande.statut,
        lignes=[
            replace(
                ligne,
                quantite_recue=max(
                    0.0,
                    ligne.quantite_recue - recu.get((commande.numero, ligne.reference), 0.0),
                ),
            )
            for ligne in commande.lignes
        ],
    )


def a_la_date(donnees: Donnees, date_ref: date, aujourdhui: date | None = None) -> Donnees:
    """Les données telles qu'elles étaient le soir du `date_ref` ; rendues telles quelles si
    rien n'est écrit après la date (hormis le montage, qui ne compte pas avant aujourd'hui)."""
    if aujourdhui is not None and date_ref < aujourdhui and donnees.montage_connu:
        donnees = replace(donnees, montage_connu=False)
    if derniere_date(donnees) <= date_ref:
        return donnees
    recu, bons = _recu_apres(donnees, date_ref)
    _rendre_les_retours(donnees, date_ref, recu, bons)
    passe = replace(
        donnees,
        mouvements=[m for m in donnees.mouvements if m.date <= date_ref],
        receptions=[
            r
            for r in donnees.receptions
            if r.date_reception is None or r.date_reception <= date_ref
        ],
        commandes=[
            _commande_au(c, date_ref, recu, bons)
            for c in donnees.commandes
            if c.date_bc is None or c.date_bc <= date_ref
        ],
        historique_prix=[
            p for p in donnees.historique_prix if p.date_bc is None or p.date_bc <= date_ref
        ],
        ordres=[o for o in donnees.ordres if o.date is None or o.date <= date_ref],
        soldes=None,
    )
    passe.derniere_date = date_ref
    return passe
