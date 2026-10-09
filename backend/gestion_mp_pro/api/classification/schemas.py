"""Schémas du domaine « Classification » (API-PRO § 1.7, routes 57–63).

Une valeur de classification porte les champs de sa liste (composition : libellé, famille,
composition détaillée ; type de fil : libellé ; titrage : valeur, unité ; couleur : libellé,
famille) ; les champs qu'une liste n'a pas sont ignorés à l'écriture et absents à la lecture.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Sortie
from gestion_mp_pro.modeles import longueurs as L

COMMENTAIRE_MAX = 500


class ValeurFiche(Sortie):
    """Une valeur de classification et le nombre de matières qui la portent.

    `valeur` (la grosseur d'un titrage : « 2900 ») n'est pas un montant.
    """

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"valeur"})

    id: int
    code: str
    libelle: str | None = None
    famille: str | None = None
    composition_detaillee: str | None = None
    valeur: str | None = None
    unite: str | None = None
    commentaire: str
    actif: bool
    version: int
    nb_matieres: int = 0
    avertissement: str | None = Field(
        default=None, description="après une désactivation : les matières qui la gardent"
    )


class RoleFiche(Sortie):
    """Un rôle de nomenclature, ses matières et ses qualités (poids > 0)."""

    id: int
    code: str
    lineaire: bool
    de_base: bool
    ordre: int
    nb_matieres: int = 0
    nb_qualites: int = 0


class Classification(Sortie):
    """Toute la classification (route 57)."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"valeur"})

    compositions: list[ValeurFiche]
    types_fil: list[ValeurFiche]
    titrages: list[ValeurFiche]
    couleurs: list[ValeurFiche]
    roles: list[RoleFiche]


class RoleCreation(Entree):
    """Un rôle ajouté (route 58) : compté au poids (seuls Cuir, Franges, Ruban vont au mètre)."""

    code: str = Field(min_length=1, max_length=L.CODE_ROLE)
    ordre: int = Field(default=0, ge=0, le=999)


class RoleModification(RoleCreation):
    """Ordre et nom d'un rôle (route 59).

    `version` est accepté pour l'écran mais la table `role_nomenclature` n'a pas de colonne
    `version` (écart signalé au coordinateur, docs/lots/D1.md) : il n'est pas contrôlé.
    """

    version: int | None = Field(default=None, ge=1)


class ValeurCreation(Entree):
    """Une valeur de classification (route 61) ; le code tient dans sa colonne."""

    code: str = Field(min_length=1, max_length=L.CODE_COULEUR)
    libelle: str = Field(default="", max_length=L.LIBELLE)
    famille: str = Field(default="", max_length=L.FAMILLE)
    composition_detaillee: str = Field(default="", max_length=L.COMPOSITION_DETAILLEE)
    valeur: str = Field(default="", max_length=L.VALEUR_TITRAGE)
    unite: str = Field(default="", max_length=L.UNITE_TITRAGE)
    commentaire: str = Field(default="", max_length=COMMENTAIRE_MAX)
    actif: bool = True


class ValeurModification(ValeurCreation):
    """Une valeur modifiée (route 62) ; le code lui-même se corrige."""

    version: int = Field(ge=1)
