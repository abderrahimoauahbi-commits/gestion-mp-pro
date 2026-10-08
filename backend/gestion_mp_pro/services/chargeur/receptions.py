"""Réceptions et prix réellement payés, pour le moteur (CALCULS A § 4.6, `depot._charger`).

Une réception annulée n'a rien livré : ni pesée, ni ponctualité, ni prix (ses écritures de
stock restent au journal avec leur contre-passation). Le contrôleur qualité est la personne
nommée sur la réception (`controle_par`), à défaut celle qui l'a validée (K5).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.chargement import QUALITE_MOTEUR
from gestion_mp_pro.modeles import Facture, Parametre, Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import QualiteReception, StatutDocument
from gestion_mp_pro.services.chargeur.contexte import Noms, a_l_usine, nombre


@dataclass
class Receptions:
    """Ce que le chargeur rend pour les réceptions."""

    receptions: list[c.Reception]
    prix: list[c.LignePrix]


def _tolerance(s: Session) -> float:
    """Le réglage `toler_ecart_pesee` (défaut du moteur s'il est vide ou illisible)."""
    brut = s.scalar(select(Parametre.valeur).where(Parametre.cle == "toler_ecart_pesee"))
    try:
        return float(brut) if brut else c.Parametres().toler_ecart_pesee
    except ValueError:
        return c.Parametres().toler_ecart_pesee


def _bon(x: ReceptionLigne, numeros: dict[int, str], commande_de_ligne: dict[int, int]) -> str:
    """Le bon de la ligne (vide si elle n'en a pas)."""
    if x.commande_ligne_id is None:
        return ""
    return numeros[commande_de_ligne[x.commande_ligne_id]]


def _ligne(x: ReceptionLigne, bon: str, noms: Noms, tolerance: float) -> c.LigneReception:
    """Une pesée pour le moteur (le lot d'une ligne validée est celui qu'elle a créé)."""
    return c.LigneReception(
        reference=noms.references[x.matiere_id],
        lot_fournisseur=noms.lots[x.lot_id] if x.lot_id is not None else x.lot_numero,
        quantite_commandee=nombre(x.quantite_attendue),
        quantite_bl=nombre(x.quantite_bl),
        quantite_pesee=nombre(x.quantite_pesee),
        tolerance_partielle=tolerance,
        nb_bobines=nombre(x.nb_bobines),
        nb_palettes=nombre(x.nb_palettes),
        magasin=noms.magasin(x.magasin_id),
        statut_qualite=QUALITE_MOTEUR[str(x.qualite)],
        observations=x.observations,
        numero_bc=bon,
    )


def receptions(
    s: Session, noms: Noms, numeros: dict[int, str], commande_de_ligne: dict[int, int]
) -> Receptions:
    """Les réceptions non annulées (par date puis numéro d'ordre) et les prix payés."""
    tolerance = _tolerance(s)
    factures = dict(s.execute(select(Facture.id, Facture.numero)).all())
    lignes: dict[int, list[ReceptionLigne]] = defaultdict(list)
    for x in s.scalars(
        select(ReceptionLigne).order_by(ReceptionLigne.reception_id, ReceptionLigne.id)
    ):
        lignes[x.reception_id].append(x)
    resultat = Receptions([], [])
    requete = (
        select(Reception)
        .where(Reception.statut != StatutDocument.annulee)
        .order_by(Reception.date, Reception.id)
    )
    for r in s.scalars(requete):
        bons = [_bon(x, numeros, commande_de_ligne) for x in lignes[r.id]]
        presents = [b for b in bons if b]
        validee = r.statut == StatutDocument.validee
        resultat.receptions.append(
            c.Reception(
                numero=r.numero or f"brouillon n° {r.id}",
                date_reception=r.date,
                numero_bc=presents[0] if len(set(presents)) == 1 else "",
                fournisseur=noms.fournisseur(r.fournisseur_id),
                numero_bl=r.numero_bl,
                numero_facture=factures.get(r.facture_id, "") if r.facture_id else "",
                receptionnaire=noms.utilisateur(r.cree_par_id),
                controleur_qualite=r.controle_par or noms.utilisateur(r.validee_par_id),
                statut="Validée" if validee else "Brouillon",
                validee_le=a_l_usine(r.validee_le),
                lignes=[
                    _ligne(x, b, noms, tolerance) for x, b in zip(lignes[r.id], bons, strict=True)
                ],
            )
        )
        if validee:
            resultat.prix.extend(_prix(r, lignes[r.id], bons, noms))
    return resultat


def _prix(
    r: Reception, lignes: list[ReceptionLigne], bons: list[str], noms: Noms
) -> list[c.LignePrix]:
    """Les prix payés d'une réception validée : lignes non refusées, pesées et payées,
    datées de la réception, dans la devise de la réception."""
    return [
        c.LignePrix(
            date_bc=r.date,
            reference=noms.references[x.matiere_id],
            fournisseur=noms.fournisseur(r.fournisseur_id),
            numero_bc=bon or (r.numero or ""),
            quantite=nombre(x.quantite_pesee),
            prix_achat=nombre(x.prix),
            devise=r.devise,
        )
        for x, bon in zip(lignes, bons, strict=True)
        if x.qualite != QualiteReception.refuse and x.quantite_pesee and x.prix
    ]
