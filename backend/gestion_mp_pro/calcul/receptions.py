"""Réceptions : l'archive des pesées et l'évolution du poids des bobines (CALCULS B § 5).

Portage de `moteur.Pesee`, `ecart_bobine`, `pesees`, `evolution_bobines`. L'évolution d'un fil
était un dict dans Gestion MP ; ici une dataclass aux mêmes clés (`EvolutionBobine`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from gestion_mp_pro.calcul.modele import Donnees, LigneReception, Reception


@dataclass
class Pesee:
    """Une ligne d'archive qualité : ce qui a été pesé, et l'écart constaté."""

    numero: str
    date_reception: date | None
    numero_bc: str
    fournisseur: str
    receptionnaire: str
    controleur_qualite: str
    reference: str
    nature: str
    designation: str
    lot_fournisseur: str
    quantite_commandee: float
    quantite_bl: float
    quantite_pesee: float
    ecart: float
    ecart_relatif: float | None
    hors_tolerance: bool
    nb_bobines: float
    poids_moyen_bobine: float | None
    magasin: str
    statut_qualite: str
    observations: str
    statut_reception: str
    quantite_attendue: float = 0.0
    nb_palettes: float = 0.0
    poids_bobine_catalogue: float = 0.0
    ecart_bobine: float | None = None
    bobine_hors_tolerance: bool = False


def ecart_bobine(constate: float | None, catalogue: float) -> float | None:
    """De combien la bobine reçue s'écarte de celle du catalogue, en proportion."""
    if not constate or not catalogue:
        return None
    return (constate - catalogue) / catalogue


def _pesee(donnees: Donnees, reception: Reception, ligne: LigneReception) -> Pesee:
    parametres = donnees.parametres
    article = donnees.article(ligne.reference)
    relatif = ligne.ecart_relatif
    catalogue = article.poids_bobine if article else 0.0
    ecart = ecart_bobine(ligne.poids_moyen_bobine, catalogue)
    return Pesee(
        numero=reception.numero,
        date_reception=reception.date_reception,
        numero_bc=ligne.numero_bc or reception.numero_bc,
        fournisseur=reception.fournisseur,
        receptionnaire=reception.receptionnaire,
        controleur_qualite=reception.controleur_qualite,
        reference=ligne.reference,
        nature=article.nature if article else "",
        designation=article.designation if article else "",
        lot_fournisseur=ligne.lot_fournisseur,
        quantite_commandee=ligne.quantite_commandee,
        quantite_bl=ligne.quantite_bl,
        quantite_attendue=ligne.quantite_attendue,
        quantite_pesee=ligne.quantite_pesee,
        ecart=ligne.ecart,
        ecart_relatif=relatif,
        hors_tolerance=relatif is not None and abs(relatif) > parametres.toler_ecart_pesee,
        nb_bobines=ligne.nb_bobines,
        poids_moyen_bobine=ligne.poids_moyen_bobine,
        magasin=ligne.magasin,
        statut_qualite=ligne.statut_qualite,
        observations=ligne.observations,
        statut_reception=reception.statut,
        nb_palettes=ligne.nb_palettes,
        poids_bobine_catalogue=catalogue,
        ecart_bobine=ecart,
        bobine_hors_tolerance=ecart is not None and abs(ecart) > parametres.toler_poids_bobine,
    )


def pesees(donnees: Donnees) -> list[Pesee]:
    """La feuille 📚 Archive_Réceptions : chaque pesée, la plus récente d'abord."""
    resultat = [
        _pesee(donnees, reception, ligne)
        for reception in donnees.receptions
        for ligne in reception.lignes
    ]
    resultat.sort(key=lambda p: (p.date_reception or date.min, p.numero), reverse=True)
    return resultat


@dataclass
class MesureBobine:
    """Un poids moyen de bobine constaté à une réception."""

    date: date | None
    reception: str
    fournisseur: str
    lot: str
    quantite_pesee: float
    nb_bobines: float
    poids_bobine: float


@dataclass
class EvolutionBobine:
    """La série des poids de bobine d'un fil : début, fin, moyenne, écart au catalogue."""

    reference: str
    fournisseur: str
    poids_catalogue: float
    receptions: int
    premier: float
    dernier: float
    derniere_date: date | None
    moyenne: float
    mini: float
    maxi: float
    evolution: float
    ecart_catalogue: float | None
    hors_tolerance: bool
    historique: list[MesureBobine] = field(default_factory=list)


def _series(donnees: Donnees) -> dict[str, list[MesureBobine]]:
    """Les lignes pesées et comptées, non refusées, des réceptions validées."""
    series: dict[str, list[MesureBobine]] = defaultdict(list)
    for reception in donnees.receptions:
        if reception.statut != "Validée":
            continue
        for ligne in reception.lignes:
            poids = ligne.poids_moyen_bobine
            if not poids or ligne.statut_qualite == "Refusé":
                continue
            series[ligne.reference].append(
                MesureBobine(
                    date=reception.date_reception,
                    reception=reception.numero,
                    fournisseur=reception.fournisseur,
                    lot=ligne.lot_fournisseur,
                    quantite_pesee=ligne.quantite_pesee,
                    nb_bobines=ligne.nb_bobines,
                    poids_bobine=poids,
                )
            )
    return series


def _evolution(donnees: Donnees, reference: str, mesures: list[MesureBobine]) -> EvolutionBobine:
    mesures.sort(key=lambda m: (m.date or date.min, m.reception))
    article = donnees.article(reference)
    catalogue = article.poids_bobine if article else 0.0
    premier, dernier = mesures[0].poids_bobine, mesures[-1].poids_bobine
    # La moyenne des bobines, pas des réceptions : un conteneur pèse plus qu'un colis.
    bobines = sum(m.nb_bobines for m in mesures)
    ecart = ecart_bobine(dernier, catalogue)
    return EvolutionBobine(
        reference=reference,
        fournisseur=article.fournisseur if article else mesures[-1].fournisseur,
        poids_catalogue=catalogue,
        receptions=len(mesures),
        premier=premier,
        dernier=dernier,
        derniere_date=mesures[-1].date,
        moyenne=sum(m.quantite_pesee for m in mesures) / bobines if bobines else 0.0,
        mini=min(m.poids_bobine for m in mesures),
        maxi=max(m.poids_bobine for m in mesures),
        evolution=(dernier - premier) / premier if premier else 0.0,
        ecart_catalogue=ecart,
        hors_tolerance=ecart is not None and abs(ecart) > donnees.parametres.toler_poids_bobine,
        historique=mesures,
    )


def evolution_bobines(donnees: Donnees) -> list[EvolutionBobine]:
    """Le poids moyen d'une bobine, réception après réception, fil par fil ; les plus fortes
    évolutions d'abord."""
    resultat = [_evolution(donnees, ref, mesures) for ref, mesures in _series(donnees).items()]
    resultat.sort(key=lambda x: -abs(x.evolution))
    return resultat
