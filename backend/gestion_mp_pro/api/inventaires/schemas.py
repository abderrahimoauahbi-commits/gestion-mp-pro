"""Schémas Pydantic du domaine « Inventaires » (API-PRO § 1.14 : routes 124–133, 245 ; § 1.24 :
239, 240).

Les montants suivent les motifs du filtre des prix (`cmup_mad`, `valeur_ecart_mad`,
`ecart_valeur_mad`…) : l'alimentation, qui lit les inventaires, les reçoit à `null`. Un champ de
comptage **absent** ne change rien, un `null` explicite le vide (C-08).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L

KG_MAX = 1_000_000_000


class CriteresEntree(Entree):
    """Le périmètre : rien = tout le stock ; sinon les matières qui passent tous les critères."""

    matieres: list[int] = Field(default_factory=list, max_length=5000)
    roles: list[int] = Field(default_factory=list, max_length=100)
    compositions: list[int] = Field(default_factory=list, max_length=500)
    classes_abc: list[str] = Field(default_factory=list, max_length=3)


class InventaireOuverture(Entree):
    """Route 128 : date, magasin (vide : tous), libellé, tolérance (vide : le réglage), critères."""

    date: date
    magasin_id: int | None = Field(default=None, ge=1)
    libelle: str = Field(default="", max_length=L.LIBELLE_INVENTAIRE)
    tolerance: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    criteres: CriteresEntree = Field(default_factory=CriteresEntree)


class LigneComptage(Entree):
    """Le comptage d'une ligne existante (un champ absent ne change rien ; `null` le vide)."""

    ligne_id: int = Field(ge=1)
    compte: float | None = Field(default=None, ge=0, le=KG_MAX, allow_inf_nan=False)
    palettes: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    bobines: float | None = Field(default=None, ge=0, le=1_000_000, allow_inf_nan=False)
    justification: str | None = Field(default=None, max_length=L.COMMENTAIRE)
    second_compte: float | None = Field(default=None, ge=0, le=KG_MAX, allow_inf_nan=False)


class Comptages(Entree):
    """Route 129 : la version lue et les lignes comptées."""

    version: int = Field(ge=1)
    lignes: list[LigneComptage] = Field(min_length=1, max_length=5000)


class LotTrouveEntree(Entree):
    """Route 130 : un lot trouvé sur place (nommé, ou « Lot interne »)."""

    version: int = Field(ge=1)
    matiere_id: int = Field(ge=1)
    lot_numero: str = Field(default="", max_length=L.NUMERO_LOT)
    lot_interne: bool = False
    magasin_id: int | None = Field(default=None, ge=1)
    compte: float | None = Field(default=None, ge=0, le=KG_MAX, allow_inf_nan=False)
    palettes: float | None = Field(default=None, ge=0, le=100_000, allow_inf_nan=False)
    bobines: float | None = Field(default=None, ge=0, le=1_000_000, allow_inf_nan=False)
    justification: str = Field(default="", max_length=L.COMMENTAIRE)


class GesteMotive(Entree):
    """Routes 132, 245 : la version lue et le motif (3 caractères au moins)."""

    version: int = Field(ge=1)
    motif: str = Field(default="", max_length=L.MOTIF)


class CriteresLus(Sortie):
    """Les critères du périmètre, tels qu'ils ont été choisis."""

    matieres: list[int]
    roles: list[int]
    compositions: list[int]
    classes_abc: list[str]


class LigneInventaire(Sortie):
    """Une ligne : théorique figé, comptages, compteurs, écart en kilos, en % et en dirhams."""

    id: int
    lot_id: int | None
    lot: str
    lot_interne: bool
    lot_trouve: bool
    matiere_id: int
    reference: str
    designation: str
    kg_par_ml: Nombre
    poids_bobine: Nombre
    bobines_palette: Nombre
    magasin_id: int
    magasin: str
    theorique: Nombre
    compte: Nombre | None
    palettes: Nombre | None
    bobines: Nombre | None
    compte_par: str
    second_compte: Nombre | None
    second_par: str
    quatre_yeux: str
    retenu: Nombre | None
    ecart: Nombre | None
    ecart_pourcent: float | None
    cmup_mad: float | None
    valeur_ecart_mad: float | None
    hors_tolerance: bool
    a_recompter: bool
    justification: str


class InventaireResume(Sortie):
    """Route 124 : un inventaire de la liste (sans ses lignes)."""

    id: int
    numero: str
    libelle: str
    statut: str
    date: date
    magasin_id: int | None
    magasin: str
    tolerance: Nombre
    perimetre: str
    criteres: CriteresLus
    nb_matieres_suspendues: int
    cree_par: str
    cree_le: datetime
    valide_par: str
    valide_le: datetime | None
    abandonne_par: str
    abandonne_le: datetime | None
    abandon_motif: str
    annule_par: str
    annule_le: datetime | None
    annulation_motif: str
    nb_lignes: int
    nb_comptees: int
    hors_tolerance: int
    sans_justification: int
    a_recompter: int
    recomptees: int
    recomptes_meme_personne: int
    ecart_total: float
    ecart_absolu: float
    ecart_valeur_mad: float | None
    ecart_valeur_absolue_mad: float | None
    version: int


class InventaireFiche(InventaireResume):
    """Routes 127–132, 245 : l'inventaire, ce qui bloquerait sa validation, ses lignes."""

    blocages: list[str]
    lignes: list[LigneInventaire]


class Choix(Sortie):
    """Une valeur proposée : son identifiant et son code."""

    id: int
    code: str


class DefautsInventaire(Sortie):
    """Route 125 : tolérance réglée, rôles et compositions en stock, cadences du tournant."""

    tolerance: float
    roles: list[Choix]
    compositions: list[Choix]
    cadence_jours: dict[str, int]


class MatiereACompter(Sortie):
    """Route 126 : une matière due au tournant."""

    article_id: int
    reference: str
    role: str
    classe_abc: str | None
    stock: float
    kg_par_ml: float
    dernier_comptage: date | None
    jours: int | None
    magasins: list[str]
