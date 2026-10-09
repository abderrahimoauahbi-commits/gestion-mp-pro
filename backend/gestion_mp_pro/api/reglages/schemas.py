"""Schémas du domaine « Réglages » (API-PRO § 1.3, routes 23–42).

Entrées dérivées de `communs.Entree` (champ inconnu refusé) ; sorties de `communs.Sortie`. Les
nombres sortent en nombres JSON ; un nombre saisi est fini (« nan », l'infini sont refusés).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, ClassVar

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Page, Sortie
from gestion_mp_pro.modeles import longueurs as L

Fini = Annotated[float, Field(allow_inf_nan=False)]
"""Un nombre saisi : fini."""


class Reglage(Sortie):
    """Un réglage : sa déclaration (registre), sa valeur en base, sa version (route 23)."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"valeur", "defaut"})

    cle: str
    libelle: str
    famille: str
    unite: str
    echelle: float
    aide: str
    bas: float | None
    haut: float | None
    texte: bool
    defaut: float | str
    valeur: str
    technique: bool
    modifiable: bool
    version: int
    version_globale: int = Field(description="Σ des versions : à renvoyer avec l'écriture")


class ReglagesEcriture(Entree):
    """Un lot de réglages à écrire, tout ou rien (route 24)."""

    valeurs: dict[str, str | float | int | None] = Field(
        description="clé → valeur (nombre en unité rangée : 0,02 pour 2 %, virgule acceptée)"
    )
    version_globale: int = Field(ge=0, description="lue avec les réglages")


class ReglageHistorique(Sortie):
    """Un changement de réglage (route 25)."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"avant", "apres"})

    id: int
    cle: str
    libelle: str
    avant: str | None
    apres: str
    avant_lisible: str
    apres_lisible: str
    quand: datetime
    par: str
    motif: str


PageReglageHistorique = Page[ReglageHistorique]


class ClotureEntree(Entree):
    """Clore la période jusqu'à une date passée, ou la rouvrir (`null`), avec un motif."""

    date_cloture: date | None
    motif: str = Field(max_length=L.MOTIF)
    version: int = Field(ge=1, description="version de la clôture, lue avec la période")


class GenreEnAttente(Sortie):
    """Un genre de document daté de la période à clore (brouillons, inventaires ouverts)."""

    genre: str = Field(description="reception, ordre, operation, inventaire")
    libelle: str
    nombre: int


class BrouillonsPeriode(Sortie):
    """Ce qui empêcherait de clore jusqu'au `jusqu_au` : annoncé avant la fenêtre de clôture."""

    jusqu_au: date
    total: int
    genres: list[GenreEnAttente]
    message: str | None = Field(description="le refus que la clôture opposerait, ou null")


class Periode(Sortie):
    """La période close : jusqu'où, par qui, quand (route 26)."""

    date_cloture: date | None
    par: str
    quand: datetime | None
    version: int


class DeviseFiche(Sortie):
    """Une devise et son cours du jour en MAD (route 27)."""

    code: str
    nom: str
    cours: Nombre
    cours_le: datetime | None
    cours_repris: bool = Field(description="aucun cours saisi depuis la mise en service")
    actif: bool
    version: int


class CoursHistorique(Sortie):
    """Un cours saisi (route 28) ; `variation` : fraction sur le cours précédent."""

    id: int
    cours: Nombre
    saisi_le: datetime
    par: str
    variation: float | None


PageCoursHistorique = Page[CoursHistorique]


class DeviseCreation(Entree):
    """Une devise nouvelle (route 29)."""

    code: str = Field(min_length=3, max_length=3, description="trois lettres : GBP, CNY…")
    nom: str = Field(default="", max_length=L.NOM_DEVISE)
    cours: Fini = Field(gt=0, le=10000, description="MAD pour une unité")


class DeviseModification(Entree):
    """Nom, cours, mise en service d'une devise (route 30)."""

    nom: str = Field(default="", max_length=L.NOM_DEVISE)
    cours: Fini = Field(gt=0, le=10000)
    actif: bool = True
    version: int = Field(ge=1)


class MagasinFiche(Sortie):
    """Un magasin et les kilos qu'il détient (route 31)."""

    id: int
    code: str
    nom: str
    type: str
    contenu: str
    actif: bool
    kg_detenus: Nombre
    version: int


class MagasinCreation(Entree):
    """Un magasin nouveau (route 32) ; type « stock_courant » ou « quarantaine »."""

    code: str = Field(min_length=1, max_length=L.CODE_MAGASIN)
    nom: str = Field(default="", max_length=L.NOM_MAGASIN)
    type: str = Field(default="stock_courant", max_length=20)
    contenu: str = Field(default="", max_length=L.CONTENU_MAGASIN)
    actif: bool = True


class MagasinModification(MagasinCreation):
    """Un magasin modifié (route 33)."""

    version: int = Field(ge=1)


class PosteFiche(Sortie):
    """Un poste de frais et l'usage qu'en font les dossiers (route 34)."""

    id: int
    code: str
    libelle: str
    recuperable: bool
    nature: str
    entre_valeur_douane: bool
    cle: str
    ordre: int
    systeme: bool
    frais_ouverts: int = Field(description="frais de ce poste dans des dossiers ouverts")
    frais_clos: int = Field(description="frais de ce poste dans des dossiers clos")
    dossiers_ouverts: int
    dossiers_clos: int
    utilise: bool
    version: int
    parts_figees: int | None = Field(
        default=None, description="après une modification : dossiers clos à répartition figée"
    )


class PosteCreation(Entree):
    """Un poste de frais nouveau (route 35)."""

    code: str = Field(min_length=1, max_length=L.CODE_POSTE)
    libelle: str = Field(min_length=1, max_length=L.LIBELLE_POSTE)
    recuperable: bool = False
    cle: str = Field(default="valeur", max_length=8)
    ordre: int | None = Field(default=None, ge=0, le=999)
    nature: str = Field(default="autre", max_length=12)
    entre_valeur_douane: bool = False


class PosteModification(Entree):
    """Un poste modifié (route 36) : le code ne change pas."""

    libelle: str = Field(min_length=1, max_length=L.LIBELLE_POSTE)
    recuperable: bool = False
    cle: str = Field(default="valeur", max_length=8)
    ordre: int | None = Field(default=None, ge=0, le=999)
    nature: str = Field(default="autre", max_length=12)
    entre_valeur_douane: bool = False
    version: int = Field(ge=1)


class CodeDouanierFiche(Sortie):
    """Un code douanier, son taux de droits (fraction) et ses matières (route 38)."""

    id: int
    code: str
    libelle: str
    taux_droits: Nombre
    actif: bool
    nb_matieres: int
    version: int


class CodeDouanierCreation(Entree):
    """Un code douanier nouveau (route 39) ; taux 0,10 = 10 %."""

    code: str = Field(min_length=2, max_length=40)
    libelle: str = Field(default="", max_length=L.LIBELLE_DOUANIER)
    taux_droits: Fini = Field(ge=0, le=1)
    actif: bool = True


class CodeDouanierModification(CodeDouanierCreation):
    """Un code douanier modifié (route 40) ; le code lui-même se corrige."""

    version: int = Field(ge=1)


class TypeOperationLu(Sortie):
    """Un type d'opération (ou l'inventaire) et les rôles qui le font."""

    type: str
    libelle: str
    roles: list[str]


class MotifLu(Sortie):
    """Un motif de mouvement ; `impose_role` : rôle exigé en plus de la direction."""

    id: int
    type: str
    libelle: str
    code_r: str | None
    impose_role: str | None


class Libelle(Sortie):
    """Un code et son libellé."""

    code: str
    libelle: str


class Motifs(Sortie):
    """Les listes fermées des mouvements et des réclamations (route 42)."""

    types: list[TypeOperationLu]
    motifs: list[MotifLu]
    reclamation_motifs: list[Libelle]
    reclamation_issues: list[Libelle]
