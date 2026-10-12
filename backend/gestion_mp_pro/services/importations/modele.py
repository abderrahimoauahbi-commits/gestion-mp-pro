"""Ce que les lectures des dossiers rendent (routes 187–189) : des dataclasses aux clés des
schémas de sortie (`api/importations/schemas_fiche.py`).

Montants en MAD (`*_mad`), valeurs en devise de la ligne (`valeur_devise`), poids en kilos ;
toute clé monétaire suit les motifs du filtre des prix (`securite.CLES_MONETAIRES`).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from gestion_mp_pro.calcul.importations import EcartFacture


@dataclass
class FactureDossier:
    """La facture d'un dossier (ou d'une de ses réceptions)."""

    id: int
    numero: str
    fournisseur_id: int
    fournisseur: str
    date: dt.date | None
    montant: Decimal | None
    devise: str
    echeance: dt.date | None
    payee_le: dt.date | None


@dataclass
class ReceptionCitee:
    """Une réception citée (lien vers sa fiche)."""

    id: int
    numero: str


@dataclass
class MatiereCitee:
    """Une matière citée (lien vers sa fiche)."""

    id: int
    reference: str


@dataclass
class Piece:
    """Une facture du dossier et les réceptions qui l'ont apportée."""

    facture: str | None
    receptions: list[str]


@dataclass
class Famille:
    """Une famille de fil du dossier : poids, achat, frais, coût au kilo."""

    famille: str
    references: int
    lots: int
    quantite: float
    valeur_mad: float
    charges_mad: float
    revient_mad: float
    valeur_kg: float
    revient_kg: float
    surcout: float


@dataclass
class CoursDisparates:
    """Une devise à plusieurs cours dans le dossier (second camion après une clôture…)."""

    devise: str
    cours: list[float]


@dataclass
class DossierResume:
    """Un dossier de la liste (route 187) : en-tête, totaux, contrôles, « à vérifier »."""

    id: int
    numero: str
    libelle: str
    date_arrivee: dt.date | None
    banque: str
    commentaire: str
    statut: str
    clos_le: dt.datetime | None
    clos_par: str | None
    annule_le: dt.datetime | None
    annule_par: str | None
    annulation_motif: str
    facture: FactureDossier | None
    a_la_main: bool
    repris: bool
    local_confirme: bool
    nb_lignes: int
    nb_frais: int
    poids: float
    marchandise_mad: float
    charges_mad: float
    tva_mad: float
    tva_saisie_mad: float
    tva_attendue_mad: float | None
    tva_ecart_tolere_mad: float | None
    tva_ecart_mad: float | None
    droits_mad: float
    droits_attendus_mad: float | None
    droits_ecart_mad: float | None
    revient_mad: float
    revient_kg: float | None
    decaisse_mad: float
    surcout: float
    seuil_surcout: float
    surcout_aberrant: bool
    lignes_aberrantes: list[str]
    lignes_negatives: list[str]
    ecart_facture: EcartFacture | None
    lignes_cours_bon: int
    cours_disparates: list[CoursDisparates]
    cours_eloignes: int
    charges_non_reparties_mad: float
    tva_non_repartie_mad: float
    fournisseurs: list[str]
    factures: list[str]
    receptions: list[ReceptionCitee]
    pieces: list[Piece]
    familles: list[Famille]
    a_verifier: list[str]
    version: int


@dataclass
class LigneDossier:
    """Une marchandise du dossier et ce qu'elle coûte, frais répartis."""

    id: int
    reception_ligne_id: int | None
    reception_id: int | None
    reception: str | None
    facture: str | None
    famille: str
    matiere_id: int
    reference: str
    lot_id: int | None
    lot: str
    fournisseur_id: int | None
    fournisseur: str
    quantite_kg: Decimal
    valeur_devise: Decimal
    devise: str
    cours: Decimal | None
    cours_origine: str | None
    cours_applique: float
    cours_jour: float
    cours_bon: Decimal | None
    bon: str | None
    bon_id: int | None
    cours_ecart: float | None
    valeur_mad: float
    part: float
    charges_mad: float
    tva_mad: float
    revient_mad: float
    valeur_kg: float
    revient_kg: float | None
    surcout: float
    frais_par_poste: dict[str, float]
    aberrante: bool
    negative: bool
    commentaire: str
    code_douanier: str | None
    taux_droits: Decimal | None
    valeur_douane_mad: float
    droits_attendus_mad: float | None


@dataclass
class PartFigee:
    """La part figée d'un frais sur une marchandise."""

    ligne_id: int
    montant: Decimal


@dataclass
class FraisDossier:
    """Un frais du dossier, sa répartition, son règlement."""

    id: int
    poste_id: int
    poste: str
    libelle: str
    recuperable: bool
    cle: str
    repartition: str
    montant: Decimal
    taux: Decimal | None
    ligne_id: int | None
    piece: str
    prestataire: str
    date_piece: dt.date | None
    echeance: dt.date | None
    payee_le: dt.date | None
    commentaire: str
    parts: list[PartFigee]
    version: int
    blocage: str | None


@dataclass
class Echeance:
    """Ce que le dossier engage à payer : une facture de marchandise, ou un frais."""

    echeance: dt.date | None
    nature: str
    quoi: str
    tiers: str
    piece: str
    date_piece: dt.date | None
    montant: float
    estime: bool
    detachee: bool
    payee_le: dt.date | None
    devise: str
    facture_id: int | None
    frais_id: int | None


@dataclass
class Actions:
    """Chaque geste du dossier : `None` s'il se peut, sinon la phrase de son refus."""

    modifier: str | None
    rattacher: str | None
    saisir: str | None
    cours: str | None
    frais: str | None
    cloturer: str | None
    rouvrir: str | None
    annuler: str | None


@dataclass
class ValeurDevise:
    """Une valeur dans sa devise (les devises ne s'additionnent jamais)."""

    devise: str
    valeur: float


@dataclass
class FamillePoids:
    """Une famille de fil arrivée et son poids."""

    famille: str
    quantite: float


@dataclass
class FactureARattacher:
    """Une facture dont la marchandise reçue attend son dossier (ou rejoint le sien)."""

    facture_id: int
    numero: str
    fournisseur_id: int
    fournisseur: str
    date: dt.date
    receptions: list[ReceptionCitee]
    lignes: int
    lots: int
    quantite: float
    valeurs: list[ValeurDevise]
    familles: list[FamillePoids]
    local: bool
    dossier_id: int | None
    dossier: str | None


@dataclass
class DossierFiche(DossierResume):
    """La fiche d'un dossier (route 189) : marchandises, frais, échéancier, alertes, gestes."""

    taux_tva_import: float
    taux_tpi_import: float
    toler_tva_import: float
    matieres_sans_code: list[MatiereCitee]
    matieres_code_inactif: list[MatiereCitee]
    lignes: list[LigneDossier]
    frais: list[FraisDossier]
    echeancier: list[Echeance]
    alertes: list[str]
    actions: Actions
    a_rattacher: list[FactureARattacher]
    nb_pieces: int


@dataclass
class ReceptionSansFacture:
    """Une réception validée dont la facture n'est pas saisie : elle attend sa facture."""

    reception_id: int
    reception: str
    date: dt.date
    fournisseur_id: int
    fournisseur: str
    numero_bl: str
    local: bool
    lignes: int
    lots: int
    quantite: float
    valeurs: list[ValeurDevise]


@dataclass
class Locaux:
    """Ce qu'un fournisseur marocain a livré sans dossier, écarté de la liste (compté)."""

    factures: int
    lignes: int


@dataclass
class EnAttente:
    """Ce qui attend son dossier (route 188)."""

    factures: list[FactureARattacher]
    sans_facture: list[ReceptionSansFacture]
    locaux: Locaux
