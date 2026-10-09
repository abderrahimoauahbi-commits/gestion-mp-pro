"""Schémas Pydantic du domaine « Commandes » (routes 152–166, API-PRO § 1.18).

Entrées dérivées de `communs.Entree` (champ inconnu refusé) ; sorties lues depuis les
dataclasses des services (`commandes_fiche`). Bornes de Gestion MP (`api/achats.py`) :
quantité et contenance > 0 et ≤ 10⁹ kg, prix ≥ 0 (confirmé > 0) et ≤ 10⁷, remarques au
fournisseur ≤ 2 000 caractères, motif de renvoi de 3 à 500.
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Sortie
from gestion_mp_pro.modeles import longueurs as L

MAX_KG = Decimal(10**9)
MAX_PRIX = Decimal(10**7)
MAX_REMARQUES = 2000


class LigneCommandeEntree(Entree):
    """Une ligne saisie : kilos, unité de commande de la fiche et sa contenance."""

    matiere_id: int = Field(ge=1)
    quantite: Decimal = Field(gt=0, le=MAX_KG, description="kg")
    unite_achat: str = Field("kg", min_length=1, max_length=L.UNITE_ACHAT)
    contenance: Decimal = Field(Decimal(1), gt=0, le=MAX_KG, description="kg par unité")
    prix: Decimal | None = Field(None, ge=0, le=MAX_PRIX, description="au kg, devise du bon")


class CommandeCreation(Entree):
    """Les bons à créer chez un fournisseur (un par devise des matières)."""

    fournisseur_id: int = Field(ge=1)
    date_livraison_prevue: date | None = Field(
        None, description="vide : date d'envoi + délai du fournisseur, comptée à l'envoi"
    )
    prix_catalogue_a_confirmer: bool = Field(
        False, description="poser le prix du catalogue sur les lignes, non confirmé"
    )
    observations: str = Field("", max_length=MAX_REMARQUES, description="remarques au fournisseur")
    lignes: list[LigneCommandeEntree] = Field(min_length=1, max_length=500)


class CommandeModification(Entree):
    """Ce que la fiche modifie ; `date_livraison_prevue` absente = inchangée, `null` = vidée."""

    version: int = Field(ge=1)
    date_livraison_prevue: date | None = None
    observations: str = Field("", max_length=MAX_REMARQUES)
    lignes: list[LigneCommandeEntree] = Field(min_length=1, max_length=500)


class Envoi(Entree):
    """L'envoi (ou l'approbation) : le jour réel où le bon est parti ; vide = aujourd'hui."""

    version: int = Field(ge=1)
    date: dt.date | None = None


class Renvoi(Entree):
    """Le renvoi aux achats, avec le motif que les achats liront sur le bon."""

    version: int = Field(ge=1)
    motif: str = Field(min_length=3, max_length=L.MOTIF_DECISION)


class PrixLigne(Entree):
    """Un prix annoncé par le fournisseur, au kilo (ou au mètre pour une matière au mètre)."""

    ligne_id: int = Field(ge=1)
    prix: Decimal = Field(gt=0, le=MAX_PRIX)
    unite: Literal["kg", "ml"] = "kg"


class ConfirmationPrix(Entree):
    """Les prix confirmés, et la date promise que le fournisseur confirme avec eux."""

    version: int = Field(ge=1)
    lignes: list[PrixLigne] = Field(min_length=1, max_length=500)
    mettre_a_jour_catalogue: bool = True
    date_livraison_prevue: date | None = None


class ExpeditionEntree(Entree):
    """Les jalons : un champ absent garde sa valeur, `null` l'efface (A-16)."""

    version: int = Field(ge=1)
    proforma_le: date | None = None
    acompte_le: date | None = None
    embarquee_le: date | None = None
    eta: date | None = None
    au_port_le: date | None = None
    dedouanee_le: date | None = None
    arrivee_usine_le: date | None = None
    conteneur: str | None = Field(None, max_length=L.CONTENEUR)
    navire: str | None = Field(None, max_length=L.NAVIRE)


class Solde(Entree):
    """Solder : on n'attend plus le reste (motif facultatif, au journal)."""

    version: int = Field(ge=1)
    motif: str = Field("", max_length=L.MOTIF)


# ── Sorties ──────────────────────────────────────────────────────────────────


class Jalons(Sortie):
    """Le suivi de l'expédition."""

    proforma_le: date | None
    acompte_le: date | None
    embarquee_le: date | None
    eta: date | None
    au_port_le: date | None
    dedouanee_le: date | None
    arrivee_usine_le: date | None
    conteneur: str
    navire: str


class RenvoiLu(Sortie):
    """Le dernier renvoi de la direction (s'il vaut encore)."""

    par: str
    le: datetime
    motif: str


class CommandeResume(Sortie):
    """Un bon dans la liste (route 152)."""

    id: int
    numero: str | None
    parti: bool
    statut: str
    statut_libelle: str
    version: int
    fournisseur_id: int
    fournisseur: str
    pays: str
    date_commande: date
    date_livraison_prevue: date | None
    devise: str
    cours: float | None
    taux_du_jour: float
    quantite: float = Field(description="kg")
    recu: float
    reste_kg: float
    part_livree: float
    nb_lignes: int
    references: list[str]
    montant: float = Field(description="au prix confirmé, devise du bon")
    montant_mad: float
    montant_estime: float = Field(description="prix confirmé, sinon catalogue")
    montant_estime_mad: float
    reste_estime_mad: float
    prix_a_confirmer: int
    approbation_requise: bool
    livraison: str = Field(description="code de l'état de livraison (statuts.ts)")
    livraison_libelle: str
    livree_le: date | None
    derniere_reception_le: date | None
    expedition: Jalons
    observations: str
    cree_par: str | None
    cree_le: datetime
    approuvee_par: str | None
    approuvee_le: datetime | None
    montant_approuve: float | None = Field(description="MAD, au cours du bon")
    solde_origine: str | None
    solde_par: str | None
    solde_le: datetime | None
    renvoi: RenvoiLu | None
    en_retard: bool = Field(description="la règle de `?filtre=retard` (P1-11)")
    arrivee_attendue: date | None = Field(description="ETA, sinon livraison promise (bon parti)")
    arrivee_sous_7_jours: bool = Field(description="arrivée attendue d'hier à J+7")
    kg_en_quarantaine: float = Field(
        description="reçu sous réserve encore en quarantaine : attendu jusqu'à sa libération"
    )


class LigneCommande(Sortie):
    """Une ligne du bon : reçu net, quarantaine, reste, prix et montants."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: float
    unite_prix: str
    quantite: float
    unite_achat: str
    contenance: float
    unites: float
    metres: float | None
    prix: float
    prix_confirme: bool
    prix_catalogue: float
    devise_catalogue: str
    prix_estime: float
    montant: float
    montant_estime: float
    recu: float
    en_quarantaine: float = Field(
        description="kg reçus sous réserve, en quarantaine : attendus jusqu'à leur libération"
    )
    reste: float
    reste_estime: float
    confirme_par: str | None
    confirme_le: datetime | None


class ReceptionDuBon(Sortie):
    """Une réception qui nomme une ligne du bon, et ce qu'elle a pesé pour lui."""

    id: int
    numero: str | None
    date: dt.date
    statut: str
    pese: float


class Decision(Sortie):
    """Une décision sur le bon (demande, approbation, renvoi, version rétablie…)."""

    quand: datetime
    par: str | None
    decision: str
    motif: str
    montant_avant: float | None
    montant_apres: float | None


class LigneVersionBon(Sortie):
    """Une ligne de la version partie."""

    matiere_id: int
    reference: str
    quantite: float
    unite_achat: str
    contenance: float
    prix: float
    prix_confirme: bool


class VersionPartie(Sortie):
    """La version que le fournisseur a, et son montant de référence (devise du bon)."""

    figee_le: datetime
    motif: str
    montant_reference: float
    lignes: list[LigneVersionBon]


class CommandeFiche(CommandeResume):
    """La fiche d'un bon (route 153) : `actions` dit, geste par geste, `null` s'il est permis,
    sinon la phrase du refus ; `fin_possible` : « solder » (un camion est venu), « annuler »
    (rien reçu) ou `null` ; `promesse_figee` : pourquoi la date promise ne se change plus."""

    promesse_figee: str | None
    seuil_approbation: float
    contact: str
    email: str
    telephone: str
    delai_jours: int
    confirme_le: datetime | None
    modifiable: bool
    fin_possible: str | None
    raison_sociale_reglee: bool
    actions: dict[str, str | None]
    lignes: list[LigneCommande]
    receptions: list[ReceptionDuBon]
    decisions: list[Decision]
    version_partie: VersionPartie | None
