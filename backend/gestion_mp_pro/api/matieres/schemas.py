"""Schémas du domaine « Matières » (API-PRO § 1.9, routes 70–81).

Bornes et longueurs : une seule déclaration (`services.matieres.BORNES`, `modeles.longueurs`),
pour l'écran (OpenAPI), l'API et le tableur. Les prix sont retirés pour l'alimentation par le
filtre des routes ; la devise, l'unité du prix et le minimum de commande aussi (`sans_achat`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Nombre, Sortie
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.services.matieres import BORNES


def _borne(champ: str, defaut: float | None) -> Any:
    """Un nombre fini dans les bornes de la fiche."""
    bas, haut = BORNES[champ]
    return Field(default=defaut, ge=bas, le=haut, allow_inf_nan=False)


class Conditionnement(Sortie):
    """L'unité dans laquelle la matière se commande (déclarée, ou déduite)."""

    unite: str
    contenance: Nombre
    declare: bool


class MatiereResume(Sortie):
    """Une matière du catalogue (route 70)."""

    id: int
    version: int
    reference: str
    designation: str
    role_id: int
    role: str
    lineaire: bool
    composition_id: int | None
    composition: str | None
    composition_libelle: str | None
    type_fil_id: int | None
    type_fil: str | None
    titrage_id: int | None
    titrage: str | None
    titrage_unite: str | None
    couleur_id: int | None
    couleur: str | None
    couleur_libelle: str | None
    couleur_code: str
    fournisseur_id: int | None
    fournisseur: str | None
    prix: Nombre | None
    unite_prix: str | None
    prix_kg: Nombre | None
    devise: str | None
    densite: Nombre
    kg_par_ml: Nombre
    unite_achat: str
    contenance_achat: Nombre
    conditionnement: Conditionnement
    contenance_palette: Nombre
    minimum_commande: Nombre | None
    poids_bobine: Nombre
    bobines_palette: Nombre
    stock_min: Nombre
    couv_min_mois: Nombre
    groupe_equiv: str
    priorite_equiv: Nombre | None
    code_douanier_id: int | None
    code_douanier: str | None
    actif: bool
    stock: Nombre = Field(description="kg, tous magasins, quarantaine comprise")
    utilisee: bool = Field(description="a des traces : se désactive, ne se supprime pas")


class MatiereFiche(MatiereResume):
    """La fiche d'une matière (route 71) : ses traces et qui l'a modifiée."""

    usages: list[str]
    modifie_le: datetime | None
    modifie_par: str | None


class MatiereCreation(Entree):
    """Une matière nouvelle (route 72) ; classification, fournisseur, code douanier par id."""

    reference: str = Field(min_length=2, max_length=L.REFERENCE)
    designation: str = Field(default="", max_length=L.DESIGNATION)
    role_id: int = Field(ge=1)
    composition_id: int | None = Field(default=None, ge=1)
    type_fil_id: int | None = Field(default=None, ge=1)
    titrage_id: int | None = Field(default=None, ge=1)
    couleur_id: int | None = Field(default=None, ge=1)
    couleur_code: str = Field(default="", max_length=L.COULEUR_CODE)
    unite_prix: str = Field(default="kg", max_length=4)
    densite: float = _borne("densite", 0)
    fournisseur_id: int | None = Field(default=None, ge=1)
    prix: float = _borne("prix", 0)
    devise: str = Field(default="MAD", max_length=L.CODE_DEVISE)
    unite_achat: str = Field(default="kg", max_length=L.UNITE_ACHAT)
    contenance_achat: float = _borne("contenance_achat", 1)
    minimum_commande: float = _borne("minimum_commande", 0)
    poids_bobine: float = _borne("poids_bobine", 0)
    bobines_palette: float = _borne("bobines_palette", 0)
    stock_min: float = _borne("stock_min", 0)
    couv_min_mois: float = _borne("couv_min_mois", 0)
    groupe_equiv: str = Field(default="", max_length=L.GROUPE_EQUIV)
    priorite_equiv: float | None = _borne("priorite_equiv", None)
    code_douanier_id: int | None = Field(default=None, ge=1)
    actif: bool = True


class MatiereModification(MatiereCreation):
    """Une matière modifiée (route 73) : la fiche entière et sa version lue (désactiver compris)."""

    version: int = Field(ge=1)


class ReferenceComposee(Sortie):
    """La référence écrite à partir de ses parties (route 75)."""

    reference: str
    designation: str
    existe: bool


class PropositionClassement(Sortie):
    """Ce que la référence d'une matière dit, pour ses seuls champs vides."""

    matiere_id: int
    reference: str
    version: int
    changements: dict[str, str]


class ApercuClassement(Sortie):
    """Ce que le classement ferait (route 76) ou a fait (route 77)."""

    propositions: list[PropositionClassement]
    a_creer: dict[str, list[str]] = Field(description="valeurs de classification à créer")


class ClassementEntree(Entree):
    """Les matières à classer et leur version lue (route 77)."""

    ids: list[int] = Field(min_length=1, max_length=5000)
    versions: list[int] = Field(min_length=1, max_length=5000)


class Changement(Sortie):
    """Un champ qui change, en clair."""

    champ: str
    libelle: str
    avant: str
    apres: str


class LigneImport(Sortie):
    """Une ligne lue du tableur."""

    ligne: int
    reference: str
    etat: str = Field(description="nouvelle, modifiee, inchangee, erreur")
    changements: list[Changement]
    erreurs: list[str]


class ApercuImport(Sortie):
    """L'aperçu du tableur (route 79) : ce qui serait écrit, et ce qui ne va pas."""

    lignes: list[LigneImport]
    creees: int
    modifiees: int
    inchangees: int
    erreurs: int
    appliquable: bool
    empreinte_apercu: str = Field(description="à renvoyer avec l'application")


class ResultatImport(ApercuImport):
    """Le tableur appliqué (route 80)."""
