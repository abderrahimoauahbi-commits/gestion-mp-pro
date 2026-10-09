"""Pilotage : la lecture du moteur à une date, la valorisation et le Cockpit (routes 209, 210).

Une lecture : les données du moteur au soir de la date (`donnees_moteur.charger_au`), le fil
monté ce soir-là (`pilotage_machine`, décision de Mohamed : du stock à toute date), l'état du
stock. La valorisation et le Cockpit partagent **une** règle de valeur (E-06 : deux pages, un
chiffre) : Σ (magasins, quarantaine comprise, + sur les métiers) × coût moyen pondéré — un coût
nul est un coût — sur les matières détenues (un stock négatif ne vaut rien). Le Cockpit dit cette
valeur, celle de la Valorisation, et non celle que le moteur additionne à sa façon.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.controles import Synthese
from gestion_mp_pro.calcul.importations import revient_par_reception
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.pilotage import cockpit as cockpit_moteur
from gestion_mp_pro.calcul.prix import CoutDate, LigneAchatRecu, couts_rendus
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from gestion_mp_pro.calcul.valorisation import LigneValorisation
from gestion_mp_pro.calcul.valorisation import valorisation as valoriser
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Fournisseur,
    Matiere,
    Reception,
    ReceptionLigne,
)
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.services import donnees_moteur
from gestion_mp_pro.services.pilotage_kpi import indicateurs
from gestion_mp_pro.services.pilotage_machine import avec_montage

ALERTE_ROUGE = ("RUPTURE", "CRITIQUE")
"""« N en rupture ou critiques » : un seul compte, partout (H-07)."""


@dataclass(frozen=True)
class Lecture:
    """Ce que le moteur dit au soir d'une date."""

    jour: date
    donnees: Donnees
    lignes: list[LigneStock]


def lire(s: Session, jour: date) -> Lecture:
    """Les données au soir de `jour`, fil monté compris, et l'état du stock."""
    d = avec_montage(s, donnees_moteur.charger_au(s, jour), jour)
    return Lecture(jour, d, etat_stock(d, jour))


def ids_matieres(s: Session) -> dict[str, int]:
    """Référence → id de la matière (les liens de l'écran vont aux fiches par id)."""
    return dict(s.execute(select(Matiere.reference, Matiere.id)).all())


def ids_fournisseurs(s: Session) -> dict[str, int]:
    """Nom → id du fournisseur."""
    return dict(s.execute(select(Fournisseur.nom, Fournisseur.id)).all())


def lignes_recues(s: Session, jour: date) -> list[LigneAchatRecu]:
    """Les lignes reçues validées, non refusées, pesées et payées jusqu'au soir de `jour`,
    dans l'ordre (date, n° de ligne) : à date égale, le dernier saisi l'emporte (E-05)."""
    requete = (
        select(
            ReceptionLigne.id,
            Reception.date,
            Matiere.reference,
            ReceptionLigne.prix,
            Reception.devise,
            Commande.cours,
            Commande.devise,
        )
        .join(Reception, Reception.id == ReceptionLigne.reception_id)
        .join(Matiere, Matiere.id == ReceptionLigne.matiere_id)
        .outerjoin(CommandeLigne, CommandeLigne.id == ReceptionLigne.commande_ligne_id)
        .outerjoin(Commande, Commande.id == CommandeLigne.commande_id)
        .where(
            Reception.statut == StatutDocument.validee,
            ReceptionLigne.qualite != QualiteReception.refuse,
            ReceptionLigne.quantite_pesee > 0,
            ReceptionLigne.prix > 0,
            Reception.date <= jour,
        )
        .order_by(Reception.date, ReceptionLigne.id)
    )
    return [
        LigneAchatRecu(
            ligne_id=lid,
            jour=le,
            reference=reference,
            prix=float(prix),
            devise=devise,
            cours_commande=float(cours) if cours is not None else None,
            devise_commande=devise_bon,
        )
        for lid, le, reference, prix, devise, cours, devise_bon in s.execute(requete).all()
    ]


def couts_d_achat(s: Session, lecture: Lecture) -> dict[str, list[CoutDate]]:
    """Le coût rendu usine de chaque achat (M84) : dossier, sinon facture au cours figé."""
    d = lecture.donnees
    return couts_rendus(d, lignes_recues(s, lecture.jour), revient_par_reception(d))


# ── Valorisation (route 210) ─────────────────────────────────────────────────────────


@dataclass
class LigneValeur(LigneValorisation):
    """Une matière valorisée, avec ce qu'il faut à l'écran pour l'ouvrir et lire ses mètres."""

    matiere_id: int | None
    designation: str
    kg_par_ml: float


@dataclass
class Valorisation:
    """La valeur du stock détenu au soir d'une date (totaux sur les matières détenues)."""

    date_reference: date
    total_mad: float
    total_magasin_mad: float
    total_machine_mad: float
    total_kg: float
    total_kg_magasin: float
    total_kg_machine: float
    ecart_mad: float
    nb_matieres: int
    nb_en_stock: int
    lignes: list[LigneValeur]


def valoriser_lecture(s: Session, lecture: Lecture) -> Valorisation:
    """La valorisation d'une lecture : chaque matière, la plus lourde d'abord."""
    d = lecture.donnees
    ids = ids_matieres(s)
    lignes = [
        LigneValeur(
            **asdict(v),
            matiere_id=ids.get(v.reference),
            designation=a.designation if (a := d.article(v.reference)) else "",
            kg_par_ml=a.kg_par_ml if a else 0.0,
        )
        for v in valoriser(d, lecture.lignes)
    ]
    lignes.sort(key=lambda x: (-x.valeur_mad, x.reference))
    detenus = [v for v in lignes if v.stock > 0]
    return Valorisation(
        date_reference=lecture.jour,
        total_mad=sum(v.valeur_mad for v in detenus),
        total_magasin_mad=sum(v.valeur_magasin_mad for v in detenus),
        total_machine_mad=sum(v.valeur_machine_mad for v in detenus),
        total_kg=sum(v.stock for v in detenus),
        total_kg_magasin=sum(v.stock_magasin for v in detenus),
        total_kg_machine=sum(v.stock_machine for v in detenus),
        ecart_mad=sum(v.ecart_mad for v in detenus),
        nb_matieres=len(lignes),
        nb_en_stock=len(detenus),
        lignes=lignes,
    )


def valorisation(s: Session, jour: date) -> Valorisation:
    """Route 210 : la valorisation au soir de `jour`."""
    return valoriser_lecture(s, lire(s, jour))


# ── Cockpit (route 209) ──────────────────────────────────────────────────────────────


def alerte_rouge(lignes: list[LigneStock]) -> int:
    """Le nombre de matières en rupture ou critiques (H-07)."""
    return sum(1 for x in lignes if any(mot in x.statut for mot in ALERTE_ROUGE))


def cockpit(s: Session, jour: date, controles: Synthese, en_retard: int) -> dict[str, Any]:
    """Route 209 : le Cockpit du moteur, la valeur du stock de la Valorisation, l'alerte
    rouge, la synthèse des contrôles et les six indicateurs avec leur formule."""
    lecture = lire(s, jour)
    v = valoriser_lecture(s, lecture)
    c = cockpit_moteur(
        lecture.donnees, jour, lecture.lignes, couts_d_achat(s, lecture), meme_couleur=True
    )
    tableau = asdict(c)
    tableau["date_reference"] = jour
    tableau["stock"] |= {
        "valeur_mad": v.total_mad,
        "valeur_magasins_mad": v.total_magasin_mad,
        "valeur_machine_mad": v.total_machine_mad,
        "kg_machine": v.total_kg_machine,
    }
    tableau["achats"]["en_retard"] = en_retard
    tableau["alerte_rouge"] = alerte_rouge(lecture.lignes)
    tableau["controles"] = asdict(controles)
    ids, fournisseurs = ids_matieres(s), ids_fournisseurs(s)
    for x in tableau["alertes"]:
        x["matiere_id"] = ids.get(x["reference"])
        x["fournisseur_id"] = fournisseurs.get(x["fournisseur"])
    for o in tableau["economies"]["top"]:
        o["matiere_id"] = ids.get(o["reference"])
        o["matiere_alternative_id"] = ids.get(o["reference_alternative"])
    tableau["kpi"] = [asdict(k) for k in indicateurs(tableau)]
    return tableau
