"""Le bilan matières du mois (routes 233, 234) : flux en kilos et en dirhams, stocks, activité.

Les flux des magasins sont ceux du moteur (`calcul.suivi_bilan.bilan`), lus sur le journal de
la base, valorisés au coût de chaque écriture (entrées au coût de revient, E-03) ; une réception
annulée dans le mois n'est nulle part ; une annulation a sa ligne à part ; les bons annulés ne
sont pas des commandes émises. Les écarts d'ordres sont ceux de l'écran Sorties
(`services.ordres.consommation.consommations` : prévu figé, perte de l'époque, retours).

Décision de Mohamed (U8) : le fil monté sur les métiers est du stock, à toute date. Le stock de
début et de fin est donc celui des magasins **plus** celui des métiers ces soirs-là (montages
de l'historique, `pilotage_machine`) ; monter n'écrit aucun mouvement, d'où une ligne « variation
sur les métiers » qui ferme l'équation, en kilos comme en dirhams :

    fin = début + entrées + ouvertures − sorties + retours des machines − retours fournisseur
          + ajustements + annulations ± variation sur les métiers
    valeur de fin = valeur de début + entrées − coût net des sorties + autres mouvements
          ± variation sur les métiers + reste du coût moyen
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.calcul.suivi_bilan import (
    DECEMBRE,
    CommandeBase,
    FabricationBase,
    MouvementBase,
    ReceptionBase,
    mois_du_bilan,
)
from gestion_mp_pro.calcul.suivi_bilan import (
    bilan as bilan_moteur,
)
from gestion_mp_pro.modeles import Commande, Mouvement, Ordre, OrdreQualite, Qualite, Reception
from gestion_mp_pro.services import donnees_moteur, horloge
from gestion_mp_pro.services.ordres.consommation import consommations
from gestion_mp_pro.services.pilotage import alerte_rouge, lire, valoriser_lecture

FORMAT_MOIS = "AAAA-MM"
MOIS_INVALIDE = "Mois invalide : AAAA-MM, pas dans le futur."
LIBELLES = {
    "OUVERTURE": "ouvertures",
    "RECEPTION": "réceptions",
    "SORTIE": "sorties vers les machines",
    "RETOUR_MACHINE": "retours des machines",
    "RETOUR_FOURNISSEUR": "retours fournisseur",
    "AJUSTEMENT": "ajustements",
    "TRANSFERT": "transferts",
}
"""Les types de mouvement dits dans la ligne des annulations."""


def lire_mois(texte: str) -> tuple[int, int]:
    """« 2026-09 » → (2026, 9) : un vrai mois, pas dans le futur (E-03), sinon 422."""
    annee, _, mois = texte.strip().partition("-")
    try:
        a, m = int(annee), int(mois)
        mois_du_bilan(a, m, horloge.aujourd_hui())
    except ValueError:
        raise Refus.saisie(
            MOIS_INVALIDE, code="date_invalide", champs={"mois": FORMAT_MOIS}
        ) from None
    return a, m


def _mouvements(s: Session) -> list[MouvementBase]:
    requete = select(
        Mouvement.id,
        Mouvement.type,
        Mouvement.quantite,
        Mouvement.date_effet,
        Mouvement.contrepasse_id,
    ).order_by(Mouvement.id)
    return [MouvementBase(int(i), str(t), float(q), j, c) for i, t, q, j, c in s.execute(requete)]


def _fabrications(s: Session) -> list[FabricationBase]:
    requete = (
        select(Qualite.code, OrdreQualite.m2, Ordre.statut, Ordre.date)
        .join(OrdreQualite, OrdreQualite.qualite_id == Qualite.id)
        .join(Ordre, Ordre.id == OrdreQualite.ordre_id)
    )
    return [FabricationBase(q, float(m2), str(st), j) for q, m2, st, j in s.execute(requete)]


def _commandes(s: Session) -> list[CommandeBase]:
    requete = select(Commande.numero, Commande.date_commande, Commande.statut)
    return [CommandeBase(n, j, str(st)) for n, j, st in s.execute(requete)]


def _receptions(s: Session) -> list[ReceptionBase]:
    return [
        ReceptionBase(str(st), j) for st, j in s.execute(select(Reception.statut, Reception.date))
    ]


def _metiers(s: Session, jour: date) -> tuple[float, float]:
    """(kg, MAD) sur les métiers au soir de `jour`, au coût moyen de ce soir-là."""
    v = valoriser_lecture(s, lire(s, jour))
    return v.total_kg_machine, v.total_machine_mad


def calculer(s: Session, mois: str) -> dict[str, Any]:
    """Route 233 : le bilan du mois, magasins et métiers, en kilos et en dirhams."""
    annee, numero = lire_mois(mois)
    aujourdhui = horloge.aujourd_hui()
    b = bilan_moteur(
        donnees_moteur.charger(s),
        annee=annee,
        mois=numero,
        aujourdhui=aujourdhui,
        mouvements=_mouvements(s),
        fabrications=_fabrications(s),
        commandes=_commandes(s),
        receptions=_receptions(s),
        ordres=list(consommations(s).values()),
    )
    debut = date(annee, numero, 1)
    fin = date(annee + (numero == DECEMBRE), numero % DECEMBRE + 1, 1) - timedelta(days=1)
    jour_fin = min(fin, aujourdhui)
    kg_debut, mad_debut = _metiers(s, debut - timedelta(days=1))
    kg_fin, mad_fin = _metiers(s, jour_fin)
    fin_lue = lire(s, jour_fin)
    resultat = asdict(b)
    resultat |= {
        "mois_iso": f"{annee:04d}-{numero:02d}",
        "du": debut,
        "au": jour_fin,
        "stock_debut_magasins_kg": b.stock_debut_kg,
        "stock_fin_magasins_kg": b.stock_fin_kg,
        "metiers_debut_kg": kg_debut,
        "metiers_fin_kg": kg_fin,
        "variation_metiers_kg": kg_fin - kg_debut,
        "stock_debut_kg": b.stock_debut_kg + kg_debut,
        "stock_fin_kg": b.stock_fin_kg + kg_fin,
        "valeur_debut_magasins_mad": b.valeur_debut_mad,
        "valeur_fin_magasins_mad": b.valeur_fin_mad,
        "metiers_debut_mad": mad_debut,
        "metiers_fin_mad": mad_fin,
        "variation_metiers_mad": mad_fin - mad_debut,
        "valeur_debut_mad": b.valeur_debut_mad + mad_debut,
        "valeur_fin_mad": b.valeur_fin_mad + mad_fin,
        "stock_machine_kg": kg_fin,
        "valeur_machine_mad": mad_fin,
        "sorties_nettes_kg": b.sorties_kg - b.retours_machine_kg,
        "ruptures": sum(1 for x in fin_lue.lignes if "RUPTURE" in x.statut),
        "critiques": sum(1 for x in fin_lue.lignes if "CRITIQUE" in x.statut),
        "alerte_rouge": alerte_rouge(fin_lue.lignes),
    }
    return resultat
