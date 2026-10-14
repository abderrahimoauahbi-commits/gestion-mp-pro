"""Les flux du moteur : journal, ordres, commandes, prix payés, réceptions, dossiers.

Portage de `gestion_mp/calcul/modele.py` (CALCULS § 1.9 à § 1.16, § 1.19), mêmes champs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from gestion_mp_pro.calcul.constantes import (
    POSTES_IMPORT,
    POSTES_VALEUR_EN_DOUANE,
    TYPES_MOUVEMENT,
)


@dataclass(slots=True)
class Mouvement:
    """Une écriture du journal ; quantité positive en kilos, signe porté par le type.

    `slots=True` : à trois cent mille écritures, la mémoire d'un dictionnaire par objet se voit.
    """

    date: date
    type: str
    reference: str
    quantite: float = 0.0
    prix_unite: float = 0.0
    devise: str = "MAD"
    total_devise: float = 0.0
    reference_doc: str = ""
    lot_fournisseur: str = ""
    magasin_source: str = ""
    magasin_destination: str = ""
    numero_of: str = ""
    motif_retour: str = ""
    utilisateur: str = ""
    fournisseur: str = ""
    id: int | None = None
    contrepasse_id: int | None = None
    cours: float = 0.0
    ligne_reception_id: int | None = None

    @property
    def signe(self) -> int:
        """+1 (entrée), −1 (sortie), 0 (transfert) ; un type inconnu compte +1."""
        return TYPES_MOUVEMENT.get(self.type, ("", 1))[1]

    @property
    def quantite_signee(self) -> float:
        """La quantité avec son signe."""
        return self.quantite * self.signe


@dataclass
class OrdreFabrication:
    """Ce qu'on a décidé de tisser : (qualité, m²), un jour ; le prévu figé à la validation."""

    numero: str
    date: date | None = None
    fabrications: list[tuple[str, float]] = field(default_factory=list)
    commentaire: str = ""
    theorique: dict[str, float] | None = None
    perte: float | None = None
    valide_le: datetime | None = None

    @property
    def m2(self) -> float:
        """Les m² de toutes les fabrications de l'ordre."""
        return sum(m2 for _, m2 in self.fabrications)


@dataclass
class LigneCommande:
    """Une ligne de bon de commande (reçu net des retours ; dont en quarantaine)."""

    numero_bc: str
    reference: str
    quantite_commandee: float = 0.0
    quantite_recue: float = 0.0
    quantite_en_quarantaine: float = 0.0
    prix_unite: float = 0.0
    devise: str = "MAD"
    prix_confirme: bool = False
    unite_commande: str = "kg"
    contenance_commande: float = 1.0
    prix_estime: float = 0.0
    cours: float = 0.0


@dataclass
class Commande:
    """Un bon de commande, son statut moteur et ses dates (promise, ETA, clôture)."""

    numero: str
    date_bc: date | None = None
    fournisseur: str = ""
    date_livraison_prevue: date | None = None
    statut: str = ""
    observations: str = ""
    lignes: list[LigneCommande] = field(default_factory=list)
    eta: date | None = None
    solde_a_la_main_le: datetime | None = None
    annulee_le: datetime | None = None

    @property
    def arrivee_attendue(self) -> date | None:
        """L'ETA, sinon la date promise."""
        return self.eta or self.date_livraison_prevue


@dataclass
class LignePrix:
    """Un prix d'achat réellement pratiqué (`date_bc` : la date de la réception)."""

    date_bc: date | None
    reference: str
    fournisseur: str = ""
    numero_bc: str = ""
    quantite: float = 0.0
    prix_achat: float = 0.0
    devise: str = "MAD"


@dataclass
class LigneReception:
    """Une pesée : la quantité pesée fait foi, pas le bon de livraison."""

    reference: str
    lot_fournisseur: str = ""
    quantite_commandee: float = 0.0
    quantite_bl: float = 0.0
    quantite_pesee: float = 0.0
    nb_bobines: float = 0.0
    nb_palettes: float = 0.0
    magasin: str = ""
    statut_qualite: str = "Conforme"
    observations: str = ""
    numero_bc: str = ""
    tolerance_partielle: float | None = None

    @property
    def quantite_attendue(self) -> float:
        """L'annonce du BL ; sans BL, le reste à livrer — sauf livraison partielle (0)."""
        if self.quantite_bl:
            return self.quantite_bl
        if self.tolerance_partielle is not None and (
            self.quantite_pesee < self.quantite_commandee * (1 - self.tolerance_partielle)
        ):
            return 0.0
        return self.quantite_commandee

    @property
    def ecart(self) -> float:
        """Pesée − attendu (0 quand rien n'est annoncé)."""
        if not self.quantite_attendue and self.tolerance_partielle is not None:
            return 0.0
        return self.quantite_pesee - self.quantite_attendue

    @property
    def ecart_relatif(self) -> float | None:
        """L'écart en part de l'attendu ; None sans attendu."""
        if not self.quantite_attendue:
            return None
        return self.ecart / self.quantite_attendue

    @property
    def poids_moyen_bobine(self) -> float | None:
        """Pesée ÷ nombre de bobines ; None sans bobines."""
        if not self.nb_bobines:
            return None
        return self.quantite_pesee / self.nb_bobines


@dataclass
class Reception:
    """Un camion : ses pesées, son statut (Brouillon | Validée)."""

    numero: str
    date_reception: date | None = None
    numero_bc: str = ""
    fournisseur: str = ""
    numero_bl: str = ""
    numero_facture: str = ""
    receptionnaire: str = ""
    controleur_qualite: str = ""
    statut: str = "Brouillon"
    lignes: list[LigneReception] = field(default_factory=list)
    validee_le: datetime | None = None


@dataclass
class ChargeImport:
    """Un frais du dossier ; `ligne` le rattache à une seule marchandise.

    Les repères du dossier (droits et TVA attendus, valeur en douane) suivent la **nature** du
    poste (`droits`, `tpi`, `tva`, `fret`, `assurance`) et `entre_valeur_douane`, comme l'écran et
    le vérificateur indépendant (audit n° 2, 14/10/2026) : un poste sur mesure de nature
    « droits » compte avec les droits. Sans nature (jeux du moteur, données d'origine), le code
    (`DD`, `TPI`, `TVA`, `FRET`, `ASSUR`) fait foi : les cinq postes système donnent le même
    résultat par les deux chemins (parité conservée).
    """

    poste: str
    montant: float = 0.0
    ligne: int | None = None
    piece: str = ""
    commentaire: str = ""
    recuperable_poste: bool | None = None
    cle: str = "valeur"
    parts: dict[int, float] = field(default_factory=dict)
    nature: str | None = None
    entre_valeur_douane: bool | None = None

    @property
    def recuperable(self) -> bool:
        """Le référentiel des postes l'emporte sur la liste d'origine."""
        if self.recuperable_poste is not None:
            return self.recuperable_poste
        return POSTES_IMPORT.get(self.poste, ("", False))[1]

    def _est(self, nature: str, code: str) -> bool:
        """De cette nature (référentiel), ou de ce code à défaut de nature."""
        return self.nature == nature if self.nature is not None else self.poste == code

    @property
    def est_droits(self) -> bool:
        """Des droits de douane (nature `droits`, à défaut le code DD)."""
        return self._est("droits", "DD")

    @property
    def est_tpi(self) -> bool:
        """La taxe parafiscale (nature `tpi`, à défaut le code TPI)."""
        return self._est("tpi", "TPI")

    @property
    def est_tva(self) -> bool:
        """La TVA de la douane (nature `tva`, à défaut le code TVA)."""
        return self._est("tva", "TVA")

    @property
    def dans_valeur_douane(self) -> bool:
        """Entre dans la valeur en douane (CAF : fret, assurance) — le drapeau du poste, à
        défaut les codes FRET et ASSUR."""
        if self.entre_valeur_douane is not None:
            return self.entre_valeur_douane
        return self.poste in POSTES_VALEUR_EN_DOUANE


@dataclass
class LigneImport:
    """Une marchandise du dossier, pesée ou saisie."""

    id: int
    reference: str
    quantite: float = 0.0
    valeur_devise: float = 0.0
    devise: str = "MAD"
    cours: float = 0.0
    lot_fournisseur: str = ""
    fournisseur: str = ""
    ligne_reception_id: int | None = None
    commentaire: str = ""

    @property
    def poids_kg(self) -> float:
        """Le poids pour les frais au poids : la quantité, en kilos."""
        return self.quantite


@dataclass
class FactureImport:
    """Une facture du dossier : son montant, sa devise, et les marchandises qu'elle a apportées
    (identifiants des `LigneImport`), qu'on rapproche d'elle seule (C36)."""

    numero: str
    montant: float = 0.0
    devise: str = ""
    lignes: list[int] = field(default_factory=list)


@dataclass
class DossierImport:
    """Une arrivée, ses factures (une ou plusieurs : décision du 12/10/2026, qui amende I3),
    ses marchandises et ses frais."""

    numero: str
    libelle: str = ""
    date_arrivee: date | None = None
    banque: str = ""
    statut: str = "Ouvert"
    commentaire: str = ""
    lignes: list[LigneImport] = field(default_factory=list)
    charges: list[ChargeImport] = field(default_factory=list)
    factures: list[FactureImport] = field(default_factory=list)

    @property
    def ouvert(self) -> bool:
        """Tout dossier non clos."""
        return self.statut != "Clos"
