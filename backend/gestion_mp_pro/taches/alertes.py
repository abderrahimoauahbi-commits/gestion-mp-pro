"""Tâche « notifications », une fois par jour : la cloche de chacun (ARCHITECTURE § 12, T4).

Ruptures et critiques (direction, achats), commandes en retard (direction, achats), dossiers
d'importation sans frais (C28) et contrôles bloquants (direction), sauvegarde en échec
(direction et administrateur, ton « danger » ; et un courriel d'alerte si le serveur d'envoi
est réglé — décision X2 : l'échec se dit). Chaque notification a sa clé du jour : rejouer le
passage n'en refait aucune. Des nombres seulement, aucun montant (jamais vues par
l'alimentation de toute façon).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from gestion_mp_pro.calcul.constantes import STATUTS
from gestion_mp_pro.calcul.controles import Controle, controler
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles.enums import GenreCourriel, Role, TonNotification
from gestion_mp_pro.services import courriel, donnees_moteur, execution, horloge
from gestion_mp_pro.services.courriel_contenu import retards
from gestion_mp_pro.services.notifications import notifier
from gestion_mp_pro.services.sauvegarde_etat import etat

DIRECTION_ACHATS = (Role.direction, Role.achats)
SURVEILLANTS = (Role.direction, Role.administrateur)


@dataclass(frozen=True)
class Alerte:
    """Une notification du jour : sa clé, son texte, l'écran où agir, son ton."""

    cle: str
    texte: str
    lien: str
    ton: TonNotification = TonNotification.alerte


def _a_tous(s: Session, roles: tuple[Role, ...], a: Alerte) -> None:
    """La même notification à plusieurs rôles (une clé par rôle)."""
    for role in roles:
        notifier(s, role, a.texte, lien=a.lien, ton=a.ton, objet="systeme", cle=f"{a.cle}:{role}")


def _stock(lignes: list[LigneStock], jour: date) -> Alerte | None:
    """Ruptures et critiques du jour."""
    ruptures = sum(1 for x in lignes if x.statut == STATUTS["RUPTURE"])
    critiques = sum(1 for x in lignes if x.statut == STATUTS["CRITIQUE"])
    if not (ruptures or critiques):
        return None
    texte = f"Aujourd'hui : {ruptures} matière(s) en rupture, {critiques} critique(s)."
    ton = TonNotification.danger if ruptures else TonNotification.alerte
    return Alerte(f"stock:{jour}", texte, "/stock", ton)


def _controles(controles: list[Controle], jour: date) -> list[Alerte]:
    """Dossiers sans frais (C28) et contrôles bloquants (direction)."""
    alertes = [
        Alerte(f"c28:{jour}", f"{c.libelle} : {c.anomalies}.", "/importations")
        for c in controles
        if c.code == "C28" and not c.conforme
    ]
    bloquants = [c.code for c in controles if c.gravite == "bloquant" and not c.conforme]
    if bloquants:
        texte = f"{len(bloquants)} contrôle(s) bloquant(s) : {', '.join(bloquants)}."
        lien = "/analyse?onglet=controles"
        alertes.append(Alerte(f"controles:{jour}", texte, lien, TonNotification.danger))
    return alertes


def _stock_et_achats(s: Session, jour: date) -> None:
    """Ruptures, critiques, commandes en retard, dossiers sans frais, contrôles bloquants."""
    donnees = donnees_moteur.charger(s)
    lignes = etat_stock(donnees, jour)
    stock = _stock(lignes, jour)
    if stock is not None:
        _a_tous(s, DIRECTION_ACHATS, stock)
    en_retard = retards(s, donnees, jour)
    if en_retard:
        texte = f"{len(en_retard)} commande(s) en retard : {', '.join(en_retard[:8])}."
        _a_tous(s, DIRECTION_ACHATS, Alerte(f"retards:{jour}", texte, "/commandes"))
    for a in _controles(controler(donnees, lignes, jour, donnees, jour), jour):
        _a_tous(s, (Role.direction,), a)


def _sauvegarde(s: Session, jour: date) -> None:
    """Sauvegarde en défaut : cloche rouge et courriel d'alerte (une fois par jour)."""
    alerte = etat(s, nb_fichiers=0).alerte
    if not alerte:
        return
    lien = "/administration?onglet=sauvegardes"
    _a_tous(s, SURVEILLANTS, Alerte(f"sauvegarde:{jour}", alerte, lien, TonNotification.danger))
    valides, _ = courriel.adresses(courriel.destinataires_du_reglage(s))
    if courriel.configure() and valides:
        courriel.mettre_en_file(
            s,
            GenreCourriel.alerte,
            cle=f"alerte:sauvegarde:{jour}",
            destinataires=valides,
            sujet=f"Gestion MP PRO — sauvegarde en défaut le {jour:%d/%m/%Y}",
            corps=alerte,
        )


def executer() -> bool:
    """Un passage : les notifications du jour si elles n'ont pas encore été émises."""
    jour = horloge.aujourd_hui()
    with fabrique()() as s, s.begin():
        if execution.reussie_le(s, "notifications", jour):
            return False
        _sauvegarde(s, jour)
        _stock_et_achats(s, jour)
    return True
