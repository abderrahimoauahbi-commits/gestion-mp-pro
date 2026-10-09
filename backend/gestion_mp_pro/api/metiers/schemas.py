"""Schémas Pydantic du domaine « Métiers et montage » (API-PRO § 1.11, routes 94–102, 238).

`bobines_par_metre` est la « densité » de Gestion MP (bobines par mètre de laize monté,
renommée : incohérence 26). Un montage reçoit la `version` de chaque étage lu et l'effet
annoncé à l'écran (`confirme_effet_kg`, kg ; 409 `effet_change` s'il a changé).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L

Fini = Annotated[Decimal, Field(allow_inf_nan=False)]
ETAGES_MAXI = 40
EFFET_MAXI = Decimal(100_000_000)


class FilEntree(Entree):
    """Un fil à monter : la matière, ses mètres, sa part de l'étage, des observations."""

    matiere_id: int = Field(ge=1)
    metres: Fini = Field(ge=0, le=1000, description="mètres de laize montés")
    pourcentage: Fini = Field(Decimal(100), ge=0, le=100, description="part du fil (%)")
    commentaire: str = Field("", max_length=L.COMMENTAIRE)


class EtageMontage(Entree):
    """Le montage d'un étage dans un montage de plusieurs étages."""

    etage: int = Field(ge=1, le=ETAGES_MAXI)
    version: int = Field(ge=1)
    fils: list[FilEntree] = Field(default_factory=list, max_length=50)


class MontageEntree(Entree):
    """Le montage de plusieurs étages (les étages absents ne bougent pas)."""

    etages: list[EtageMontage] = Field(min_length=1, max_length=ETAGES_MAXI)
    confirme_effet_kg: Fini = Field(ge=-EFFET_MAXI, le=EFFET_MAXI)


class EtageEntree(Entree):
    """Le montage d'un seul étage (au téléphone) : les autres étages ne sont pas touchés."""

    version: int = Field(ge=1)
    fils: list[FilEntree] = Field(default_factory=list, max_length=50)
    confirme_effet_kg: Fini = Field(ge=-EFFET_MAXI, le=EFFET_MAXI)


class MetierCreation(Entree):
    """Un métier à tisser : code, nom, laize d'un étage, bobines par mètre, étages."""

    code: str = Field(min_length=1, max_length=L.CODE_METIER)
    nom: str = Field("", max_length=L.NOM_METIER)
    laize: Fini = Field(Decimal("4.2"), ge=0, le=100, description="m")
    bobines_par_metre: Fini = Field(Decimal(0), ge=0, le=100_000)
    etages: int = Field(6, ge=1, le=ETAGES_MAXI)
    actif: bool = True
    commentaire: str = Field("", max_length=2000)


class MetierModification(MetierCreation):
    """Le réglage entier et, facultatif, le montage (une seule transaction)."""

    version: int = Field(ge=1)
    montage: MontageEntree | None = None


class FilMonteFiche(Sortie):
    """Un fil monté et ce qu'il pèse dans le stock « sur les métiers »."""

    id: int
    matiere_id: int
    reference: str
    designation: str
    fournisseur: str
    etage: int
    metres: Nombre
    pourcentage: Nombre
    commentaire: str
    bobines: float
    poids_bobine: Nombre = Field(description="kg par bobine au catalogue")
    poids_bobine_utilise: Nombre = Field(description="pesé au lot, sinon catalogue (M43)")
    source_poids: str
    ecart_mesure: float | None
    ecart_hors_tolerance: bool
    poids: float = Field(description="kg")
    valeur_mad: float | None


class EtageFiche(Sortie):
    """Un étage : ses fils, sa largeur occupée, sa version (verrou du montage)."""

    etage: int
    version: int
    fils: int
    metres: float = Field(description="largeur occupée : Σ mètres × part")
    bobines: float
    poids: float
    trop_large: bool
    monte_le: datetime | None
    monte_par: str | None


class DernierMontage(Sortie):
    """Le dernier montage d'un métier."""

    par: str | None
    quand: datetime
    etage: int | None
    effet_kg: Nombre


class MetierFiche(Sortie):
    """Un métier, ses fils étage par étage, et ce qu'ils pèsent."""

    id: int
    code: str
    nom: str
    laize: Nombre
    bobines_par_metre: Nombre
    etages: int
    actif: bool
    commentaire: str
    version: int
    fils: list[FilMonteFiche]
    poids: float = Field(description="kg montés (comptés seulement si le métier est en service)")
    sur_les_metiers: float = Field(description="kg comptés dans le stock (0 si arrêté)")
    valeur_mad: float | None
    bobines: float
    metres: float
    etages_detail: list[EtageFiche]
    etages_garnis: int
    etages_trop_larges: list[int]
    densite_a_saisir: bool
    fils_sans_poids: int
    ordres: int = Field(description="ordres de fabrication qui le nomment")
    tolerance_bobine: float
    dernier_montage: DernierMontage | None


class ResultatMontage(Sortie):
    """Ce que le montage a fait au stock sur les métiers (texte unique) et ses alertes."""

    metier: MetierFiche
    effet_kg: Nombre
    avant_kg: Nombre = Field(description="kg des étages montés, avant")
    apres_kg: Nombre = Field(description="kg des étages montés, après")
    alertes: list[str]
    message: str


class MetierModifie(MetierFiche):
    """La fiche après un réglage ; `montage` : le résultat du montage s'il y en avait un."""

    montage: ResultatMontage | None = None


class MontageEvenementFiche(Sortie):
    """Un montage confirmé : lignes avant/après, kilos, effet, alerte, origine."""

    id: int
    quand: datetime
    par: str | None
    etage: int | None = Field(description="null : plusieurs étages (bureau)")
    origine: str
    avant: list[dict[str, Any]]
    apres: list[dict[str, Any]]
    avant_kg: float
    apres_kg: float
    effet_kg: Nombre
    alerte: str


class MatiereMontage(Sortie):
    """Une matière qui se monte : poids de bobine compté, sorti en 30 jours, déjà monté."""

    matiere_id: int
    reference: str
    designation: str
    actif: bool
    poids_bobine_catalogue: Nombre
    poids_bobine_compte: Nombre
    origine_poids: str
    sorti_30_j: Nombre
    deja_monte: Nombre
    jours: int
