"""Fournisseurs : OTIF par réception, score sur 100, devises pratiquées (CALCULS B § 4).

Portage de `moteur.PerformanceReception`, `ScoreFournisseur`, `performance_receptions`,
`points_score`, `scorecard_fournisseurs`, `devises_pratiquees`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.achats import montant_ligne_mad, pas_partie
from gestion_mp_pro.calcul.constantes import (
    DELAI_SANS_PENALITE,
    JOURS_PAR_POINT_DE_DELAI,
    POINTS_DELAI,
    POINTS_OTIF,
    POINTS_RETOURS,
    RETOURS_SANS_POINT,
)
from gestion_mp_pro.calcul.modele import Commande, Donnees, Fournisseur, Reception
from gestion_mp_pro.calcul.outils import arrondi


@dataclass
class PerformanceReception:
    """Ponctualité, complétude, conformité d'une réception validée."""

    numero: str
    fournisseur: str
    date_reception: date | None
    on_time: int | None
    in_full: int | None
    in_spec: int
    otif: int | None
    lignes_hors_tolerance: int
    ecart_pesee: float | None


@dataclass
class ScoreFournisseur:
    """Le score d'un fournisseur et son classement."""

    fournisseur: str
    pays: str
    devise: str
    delai_jours: float
    nb_commandes: int
    montant_mad: float
    receptions: int
    on_time: float | None
    in_full: float | None
    in_spec: float | None
    otif: float | None
    taux_retours: float
    ecart_pesee_moyen: float | None
    score: float | None
    classement: str
    action: str
    sous_performant: bool


CleLigne = tuple[str, str]


@dataclass
class _Suivi:
    """Ce que chaque ligne de bon a déjà reçu, de quels lots, et les retours de ces lots."""

    deja: dict[CleLigne, float] = field(default_factory=lambda: defaultdict(float))
    lots_de_ligne: dict[CleLigne, dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )
    apporte_du_lot: dict[CleLigne, float] = field(default_factory=lambda: defaultdict(float))
    retours_du_lot: dict[CleLigne, list[tuple[date, float]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def reparti_avant(self, cle: CleLigne, jour: date | None) -> float:
        """Ce que la ligne a reçu et qui est reparti chez le fournisseur avant ce camion (le
        jour même compris), au prorata de ce que chaque lot lui a apporté."""
        total = 0.0
        for lot, kg in self.lots_de_ligne[cle].items():
            cle_lot = (cle[1], lot)
            if not self.apporte_du_lot[cle_lot]:
                continue
            renvoye = sum(
                q for d, q in self.retours_du_lot.get(cle_lot, ()) if jour is None or d <= jour
            )
            if renvoye > 0:
                total += min(kg, renvoye * kg / self.apporte_du_lot[cle_lot])
        return total


def _bons(reception: Reception) -> set[str]:
    if reception.numero_bc:
        return {reception.numero_bc}
    return {x.numero_bc for x in reception.lignes if x.numero_bc}


def _a_l_heure(
    donnees: Donnees, reception: Reception, commandes: dict[str, Commande]
) -> int | None:
    """À l'heure si chacun de ses bons l'est, à la date promise (au retard toléré près)."""
    jugements = []
    for numero_bc in sorted(_bons(reception)):
        commande = commandes.get(numero_bc)
        if (
            commande
            and commande.date_bc
            and commande.date_livraison_prevue
            and reception.date_reception
        ):
            reel = (reception.date_reception - commande.date_bc).days
            prevu = (commande.date_livraison_prevue - commande.date_bc).days
            tolere = prevu + donnees.parametres.toler_retard_jours
            jugements.append(1 if reel <= tolere else 0)
    return min(jugements) if jugements else None


def _livre(reception: Reception) -> dict[CleLigne, float]:
    livre: dict[CleLigne, float] = defaultdict(float)
    for ligne in reception.lignes:
        bc = ligne.numero_bc or reception.numero_bc
        if bc and not ligne.statut_qualite.endswith("Refusé"):
            livre[(bc, ligne.reference)] += ligne.quantite_pesee
    return livre


def _complete(
    donnees: Donnees, reception: Reception, commandes: dict[str, Commande], suivi: _Suivi
) -> int | None:
    """Complète si chaque ligne due de ses bons reçoit au moins son reste moins la tolérance ;
    None si elle ne devait rien. Met ensuite le suivi à jour."""
    tolerance = donnees.parametres.toler_in_full
    livre = _livre(reception)
    dues = []
    for numero_bc in sorted(_bons(reception)):
        commande = commandes.get(numero_bc)
        if commande is None or (
            commande.solde_a_la_main_le
            and reception.validee_le
            and reception.validee_le > commande.solde_a_la_main_le
        ):
            continue
        for ligne in commande.lignes:
            cle = (numero_bc, ligne.reference)
            marge = ligne.quantite_commandee * tolerance
            recu = suivi.deja[cle] - suivi.reparti_avant(cle, reception.date_reception)
            reste = ligne.quantite_commandee - recu
            if reste > marge:
                dues.append(livre[cle] >= reste - marge)
    for cle, kg in livre.items():
        suivi.deja[cle] += kg
    for pesee in reception.lignes:
        bc = pesee.numero_bc or reception.numero_bc
        if bc and not pesee.statut_qualite.endswith("Refusé") and pesee.lot_fournisseur:
            suivi.lots_de_ligne[(bc, pesee.reference)][pesee.lot_fournisseur] += (
                pesee.quantite_pesee
            )
            suivi.apporte_du_lot[(pesee.reference, pesee.lot_fournisseur)] += pesee.quantite_pesee
    return (1 if all(dues) else 0) if dues else None


def _performance(
    donnees: Donnees, reception: Reception, commandes: dict[str, Commande], suivi: _Suivi
) -> PerformanceReception:
    on_time = _a_l_heure(donnees, reception, commandes)
    ecarts = [x.ecart_relatif for x in reception.lignes if x.ecart_relatif is not None]
    in_full = _complete(donnees, reception, commandes, suivi)
    in_spec = (
        1
        if reception.lignes and all(x.statut_qualite.endswith("Conforme") for x in reception.lignes)
        else 0
    )
    return PerformanceReception(
        numero=reception.numero,
        fournisseur=reception.fournisseur,
        date_reception=reception.date_reception,
        on_time=on_time,
        in_full=in_full,
        in_spec=in_spec,
        otif=None if in_full is None else (1 if on_time is None else on_time) * in_full * in_spec,
        lignes_hors_tolerance=sum(
            1 for e in ecarts if abs(e) > donnees.parametres.toler_ecart_pesee
        ),
        ecart_pesee=sum(ecarts) / len(ecarts) if ecarts else None,
    )


def performance_receptions(donnees: Donnees) -> list[PerformanceReception]:
    """OTIF par réception validée : ponctualité (date promise), complétude (lignes dues,
    nettes des retours d'avant le camion), conformité (toutes lignes conformes)."""
    commandes = {c.numero: c for c in donnees.commandes}
    suivi = _Suivi()
    for mouvement in donnees.mouvements:
        if mouvement.type == "RETOUR_FOURNISSEUR" and mouvement.lot_fournisseur:
            suivi.retours_du_lot[(mouvement.reference, mouvement.lot_fournisseur)].append(
                (mouvement.date, mouvement.quantite)
            )
    return [
        _performance(donnees, reception, commandes, suivi)
        for reception in donnees.receptions
        if reception.statut == "Validée"
    ]


def points_score(otif: float, taux_retours: float, delai_jours: float) -> float:
    """Score = OTIF × 60 + retours (20 points à 0 %, 0 à 5 % et plus) + délai (20 points
    jusqu'à 15 jours, un de moins par 5 jours au-delà, entre 0 et 20)."""
    points_retours = POINTS_RETOURS * max(0.0, 1 - taux_retours / RETOURS_SANS_POINT)
    points_delai = min(
        float(POINTS_DELAI),
        max(0.0, POINTS_DELAI - (delai_jours - DELAI_SANS_PENALITE) / JOURS_PAR_POINT_DE_DELAI),
    )
    return otif * POINTS_OTIF + points_retours + points_delai


def _moyenne(lot: list[PerformanceReception], champ: str) -> float | None:
    """La moyenne sur les seules réceptions notées (celles qui ont un OTIF)."""
    notees = [x for x in lot if x.otif is not None]
    valeurs = [getattr(x, champ) for x in notees if getattr(x, champ) is not None]
    if not valeurs:
        return None
    return float(sum(valeurs) / len(valeurs))


def _classement(donnees: Donnees, score: float | None) -> tuple[str, str]:
    parametres = donnees.parametres
    if score is None:
        return "—", "—"
    if score >= parametres.score_strategique:
        return "🟢 Stratégique", "Fidéliser + négocier volume"
    if score >= parametres.score_standard:
        return "🟡 Standard", "Maintenir relation"
    if score >= parametres.score_surveiller:
        return "🟠 À surveiller", "Audit qualité + relance"
    return "🔴 À challenger", "Chercher alternative"


def _flux_par_fournisseur(donnees: Donnees) -> tuple[dict[str, float], dict[str, float]]:
    entrees: dict[str, float] = defaultdict(float)
    retours: dict[str, float] = defaultdict(float)
    for mouvement in donnees.mouvements:
        if mouvement.type == "ENTREE_RECEPTION":
            entrees[mouvement.fournisseur] += mouvement.quantite
        elif mouvement.type == "RETOUR_FOURNISSEUR":
            retours[mouvement.fournisseur] += mouvement.quantite
    return entrees, retours


def _score(
    donnees: Donnees,
    fournisseur: Fournisseur,
    lot: list[PerformanceReception],
    flux: tuple[dict[str, float], dict[str, float]],
    commandes: list[Commande],
) -> ScoreFournisseur:
    entrees, retours = flux
    otif = _moyenne(lot, "otif")
    recu = entrees.get(fournisseur.nom, 0.0)
    taux_retours = retours.get(fournisseur.nom, 0.0) / recu if recu else 0.0
    score = (
        None if otif is None else arrondi(points_score(otif, taux_retours, fournisseur.delai_jours))
    )
    classement, action = _classement(donnees, score)
    montants = sum(
        montant_ligne_mad(ligne, ligne.quantite_commandee, donnees.parametres)
        for commande in commandes
        for ligne in commande.lignes
    )
    ecarts = [x.ecart_pesee for x in lot if x.ecart_pesee is not None]
    return ScoreFournisseur(
        fournisseur=fournisseur.nom,
        pays=fournisseur.pays,
        devise=fournisseur.devise,
        delai_jours=fournisseur.delai_jours,
        nb_commandes=len(commandes),
        montant_mad=montants,
        receptions=len(lot),
        on_time=_moyenne(lot, "on_time"),
        in_full=_moyenne(lot, "in_full"),
        in_spec=_moyenne(lot, "in_spec"),
        otif=otif,
        taux_retours=taux_retours,
        ecart_pesee_moyen=sum(ecarts) / len(ecarts) if ecarts else None,
        score=score,
        classement=classement,
        action=action,
        sous_performant=otif is not None and otif < donnees.parametres.cible_otif,
    )


def scorecard_fournisseurs(donnees: Donnees) -> list[ScoreFournisseur]:
    """Le bloc `🏭 Fournisseurs!A54:I90` : score sur 100 (`points_score`) et classement,
    fournisseurs triés par nom ; un bon brouillon ou annulé n'a rien acheté."""
    par_fournisseur: dict[str, list[PerformanceReception]] = defaultdict(list)
    for performance in performance_receptions(donnees):
        par_fournisseur[performance.fournisseur].append(performance)
    commandes: dict[str, list[Commande]] = defaultdict(list)
    for commande in donnees.commandes:
        if not pas_partie(commande) and commande.statut != "Annulée":
            commandes[commande.fournisseur].append(commande)
    flux = _flux_par_fournisseur(donnees)
    return [
        _score(
            donnees,
            fournisseur,
            par_fournisseur.get(fournisseur.nom, []),
            flux,
            commandes.get(fournisseur.nom, []),
        )
        for fournisseur in sorted(donnees.fournisseurs, key=lambda f: f.nom)
    ]


def devises_pratiquees(donnees: Donnees) -> dict[str, dict[str, int]]:
    """Les devises dans lesquelles chaque fournisseur facture, et sur combien de matières —
    déduites des prix du catalogue (la devise appartient au prix)."""
    resultat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for article in donnees.articles:
        if article.fournisseur and article.devise:
            resultat[article.fournisseur][article.devise] += 1
    return {nom: dict(devises) for nom, devises in resultat.items()}
