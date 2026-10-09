"""Le courriel du lundi : la semaine qui commence, en une page, pour la direction (lot D10).

Contenu repris de Gestion MP (`services/courriel.py`, B.6.4) : valeur du stock et couverture
pondérée, ruptures/critiques/urgentes, à commander, commandes en retard (8 numéros au plus,
la règle de l'écran Commandes : `calcul.suivi_livraison`), à approuver, brouillons, besoins
signalés, réclamations ; plus deux lignes promises par ECRANS-PRO (P8-20) : « Contrôles
bloquants » et « Dernière sauvegarde ». Le titre dit « Gestion MP PRO » (deux logiciels
coexistent : leurs courriels ne doivent pas se confondre). Des chiffres métier, des montants :
l'aperçu est réservé à la direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from gestion_mp_pro.calcul.controles import controler, synthese
from gestion_mp_pro.calcul.modele import Donnees
from gestion_mp_pro.calcul.pilotage import cockpit
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.calcul.suivi_livraison import (
    STATUTS_ATTENDUS,
    BonALivrer,
    LigneBon,
    commandes_en_retard,
)
from gestion_mp_pro.config import reglages
from gestion_mp_pro.modeles import (
    Commande,
    CommandeLigne,
    Fournisseur,
    Operation,
    Ordre,
    Parametre,
    Reception,
    Reclamation,
    Signalement,
)
from gestion_mp_pro.modeles.enums import (
    GenreCourriel,
    StatutCommande,
    StatutDocument,
    StatutOrdre,
    StatutReclamation,
)
from gestion_mp_pro.services import donnees_moteur, horloge
from gestion_mp_pro.services.chargeur.achats import en_quarantaine_par_ligne, recu_par_ligne

NUMEROS_EN_RETARD = 8
TITRE = "Gestion MP PRO — la semaine du {jour:%d/%m/%Y}"


def _milliers(valeur: float) -> str:
    """« 1 234 567 » : milliers séparés par une espace, sans décimale (comme Gestion MP)."""
    return f"{valeur:,.0f}".replace(",", " ")


def _bons(s: Session) -> list[BonALivrer]:
    """Les bons numérotés encore attendus, avec leurs lignes (kg) et leurs dates."""
    requete = (
        select(Commande, Fournisseur.delai_jours)
        .join(Fournisseur, Fournisseur.id == Commande.fournisseur_id)
        .where(Commande.numero.is_not(None), Commande.statut.in_(STATUTS_ATTENDUS))
        .order_by(Commande.id)
    )
    commandes = s.execute(requete).all()
    lignes: dict[int, list[LigneBon]] = {c.id: [] for c, _ in commandes}
    if lignes:
        lues = select(CommandeLigne.commande_id, CommandeLigne.id, CommandeLigne.quantite).where(
            CommandeLigne.commande_id.in_(list(lignes))
        )
        for cid, lid, quantite in s.execute(lues.order_by(CommandeLigne.id)):
            lignes[cid].append(LigneBon(lid, float(quantite)))
    return [
        BonALivrer(
            numero=c.numero,
            statut=str(c.statut),
            lignes=lignes[c.id],
            eta=c.eta,
            date_livraison_prevue=c.date_livraison_prevue,
            date_commande=c.date_commande,
            delai_fournisseur=float(delai or 0),
        )
        for c, delai in commandes
    ]


def retards(s: Session, donnees: Donnees, jour: date) -> list[str]:
    """Les numéros des bons en retard, dans l'ordre des bons (la règle de l'écran Commandes)."""
    p = donnees.parametres
    bons = commandes_en_retard(
        _bons(s),
        recu_par_ligne(s),
        en_quarantaine_par_ligne(s),
        p.toler_in_full,
        jour=jour,
        retard_tolere=p.toler_retard_jours,
    )
    return [b.numero or "" for b in bons]


def _compter(s: Session, condition: ColumnElement[bool]) -> int:
    """Le nombre de lignes qui remplissent la condition (table tirée de la condition)."""
    return int(s.scalar(select(func.count()).where(condition)) or 0)


def _brouillons(s: Session) -> str:
    """« 2 réceptions, 1 ordres de fabrication, 0 opérations » (la phrase de Gestion MP)."""
    nombres = {
        "réceptions": _compter(s, Reception.statut == StatutDocument.brouillon),
        "ordres de fabrication": _compter(s, Ordre.statut == StatutOrdre.brouillon),
        "opérations": _compter(s, Operation.statut == StatutDocument.brouillon),
    }
    return ", ".join(f"{n} {k}" for k, n in nombres.items())


def _derniere_sauvegarde(s: Session) -> str:
    """« 08/10/2026 à 02:00 » ou « aucune »."""
    from gestion_mp_pro.services.sauvegarde_etat import etat

    e = etat(s, nb_fichiers=0)
    return f"{e.derniere:%d/%m/%Y à %H:%M}" if e.derniere else "aucune"


def _lignes_du_stock(donnees: Donnees, jour: date) -> tuple[list[str], int]:
    """Les lignes du stock et des achats, et le nombre de contrôles bloquants."""
    lignes = etat_stock(donnees, jour)
    c = cockpit(donnees, jour, lignes)
    bloquants = synthese(controler(donnees, lignes, jour, donnees, jour)).bloquants
    texte = [
        f"Valeur du stock : {_milliers(c.stock.valeur_mad)} MAD · couverture pondérée "
        f"{c.stock.couverture_ponderee_jours:.0f} jours",
        f"Matières en rupture : {c.stock.ruptures} · critiques : {c.stock.critiques} · "
        f"urgentes : {c.stock.urgents}",
        f"À commander selon le plan : {_milliers(c.achats.budget_a_commander_mad)} MAD",
    ]
    return texte, bloquants


def contenu(s: Session, jour: date | None = None) -> tuple[str, str]:
    """Le sujet et le texte du courriel de la semaine de `jour` (aujourd'hui par défaut)."""
    jour = jour or horloge.aujourd_hui()
    donnees = donnees_moteur.charger(s)
    stock, bloquants = _lignes_du_stock(donnees, jour)
    en_retard = retards(s, donnees, jour)
    numeros = ", ".join(en_retard[:NUMEROS_EN_RETARD])
    nom = s.get(Parametre, "nom_entreprise")
    titre = TITRE.format(jour=jour) + (f" — {nom.valeur}" if nom is not None and nom.valeur else "")
    adresse = reglages().adresse
    texte = [
        titre,
        "",
        *stock,
        f"Commandes en retard : {len(en_retard)}" + (f" — {numeros}" if en_retard else ""),
        "Commandes à approuver : "
        + str(_compter(s, Commande.statut == StatutCommande.a_approuver)),
        f"Brouillons en attente : {_brouillons(s)}",
        "Besoins signalés par l'atelier, non traités : "
        + str(_compter(s, Signalement.traite_le.is_(None))),
        "Réclamations fournisseurs ouvertes : "
        + str(_compter(s, Reclamation.statut == StatutReclamation.ouverte)),
        f"Contrôles bloquants : {bloquants}",
        f"Dernière sauvegarde : {_derniere_sauvegarde(s)}",
        "",
        "Le détail : ouvrir Gestion MP PRO (Cockpit)"
        + (f" : {adresse}/cockpit." if adresse else "."),
    ]
    return TITRE.format(jour=jour), "\n".join(texte)


@dataclass(frozen=True)
class Apercu:
    """Ce que le courriel du lundi dirait aujourd'hui (route 48, direction seule)."""

    sujet: str
    texte: str
    serveur_configure: bool
    destinataires: list[str]
    illisibles: list[str]


def apercu(s: Session) -> Apercu:
    """L'aperçu : contenu du jour, serveur d'envoi réglé ou non, adresses lues."""
    from gestion_mp_pro.services.courriel import adresses, configure, destinataires_du_reglage

    sujet, texte = contenu(s)
    valides, illisibles = adresses(destinataires_du_reglage(s))
    return Apercu(sujet, texte, configure(), valides, illisibles)


@dataclass(frozen=True)
class MiseEnFile:
    """Ce qu'a fait le passage du lundi : courriel mis en file (id) ou non, adresses écartées."""

    courriel_id: int | None
    illisibles: list[str]
    raison: str


def courriel_du_lundi(s: Session, jour: date | None = None) -> MiseEnFile:
    """Met en file le courriel de la semaine, **une fois** par lundi (clé `lundi:AAAA-MM-JJ`).

    Rien un autre jour, sans serveur d'envoi, ou sans destinataire lisible ; les adresses
    illisibles sont écartées et dites (E-15).
    """
    from gestion_mp_pro.services.courriel import (
        adresses,
        configure,
        destinataires_du_reglage,
        mettre_en_file,
    )

    jour = jour or horloge.aujourd_hui()
    valides, illisibles = adresses(destinataires_du_reglage(s))
    if jour.weekday() != 0:
        return MiseEnFile(None, illisibles, "pas un lundi")
    if not configure():
        return MiseEnFile(None, illisibles, "serveur d'envoi non réglé")
    if not valides:
        return MiseEnFile(None, illisibles, "aucun destinataire lisible")
    sujet, texte = contenu(s, jour)
    ident = mettre_en_file(
        s, GenreCourriel.lundi, cle=f"lundi:{jour}", destinataires=valides, sujet=sujet, corps=texte
    )
    return MiseEnFile(ident, illisibles, "" if ident else "déjà mis en file")
