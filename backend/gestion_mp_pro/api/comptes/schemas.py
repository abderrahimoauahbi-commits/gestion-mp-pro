"""Schémas Pydantic du domaine « Comptes et appareils » (API-PRO § 1.2, routes 8–22).

Entrées dérivées de `communs.Entree` (champ inconnu refusé), longueurs tirées de
`modeles.longueurs` ; sorties dérivées de `communs.Sortie`. Les règles de code (4 chiffres pour
l'alimentation, 8 ou 12 caractères ailleurs) sont dites par le service, avec leur message.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field

from gestion_mp_pro.api.communs import Entree, Sortie
from gestion_mp_pro.modeles import Utilisateur
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services.appareils import Enrolement as EnrolementService
from gestion_mp_pro.services.appareils import FicheAppareil
from gestion_mp_pro.services.comptes import VOIT_PRIX, libelle_role
from gestion_mp_pro.services.utilisateurs import FicheCompte

CODE_MAX = 200
SOCIETE_MAX = 160


class Visage(Sortie):
    """Un nom à toucher à la connexion (sans identifiant : le compte se désigne par `id`)."""

    id: int
    nom: str
    role: str
    role_libelle: str
    longueur_code: int | None = Field(
        description="4 pour l'alimentation (le code part au 4ᵉ chiffre), sinon null"
    )

    @classmethod
    def de(cls, u: Utilisateur) -> Visage:
        """Le visage d'un compte."""
        role = str(u.role or "")
        longueur = 4 if role == Role.alimentation else None
        return cls(
            id=u.id, nom=u.nom, role=role, role_libelle=libelle_role(role), longueur_code=longueur
        )


class Installation(Entree):
    """Route 9 : le premier compte, celui de la direction."""

    societe: str = Field(default="", max_length=SOCIETE_MAX)
    identifiant: str = Field(min_length=2, max_length=L.IDENTIFIANT)
    nom: str = Field(min_length=2, max_length=L.NOM_PERSONNE)
    code: str = Field(min_length=1, max_length=CODE_MAX)


class Connexion(Entree):
    """Route 10 : le nom touché (`compte`, poste local ou appareil enrôlé) ou l'identifiant."""

    compte: int | None = Field(default=None, ge=1, description="id d'un visage")
    identifiant: str = Field(default="", max_length=L.IDENTIFIANT)
    code: str = Field(max_length=CODE_MAX)


class Moi(Sortie):
    """Route 12 : le compte connecté, ce qu'il voit et ses droits fins."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"droits"})

    id: int
    identifiant: str
    nom: str
    role: str
    role_libelle: str
    email: str
    voit_prix: bool
    droits: list[str] = Field(description="gestes permis (droits fins, securite.GESTES)")
    vu_le: datetime | None
    version: int

    @classmethod
    def de(cls, u: Utilisateur, droits: list[str]) -> Moi:
        """La fiche du compte connecté."""
        role = str(u.role or "")
        return cls(
            id=u.id,
            identifiant=u.identifiant,
            nom=u.nom,
            role=role,
            role_libelle=libelle_role(role),
            email=u.email,
            voit_prix=role in VOIT_PRIX,
            droits=droits,
            vu_le=u.vu_le,
            version=u.version,
        )


class MoiModification(Entree):
    """Route 13 : son courriel."""

    email: str = Field(default="", max_length=L.EMAIL_COMPTE)
    version: int = Field(ge=1)


class ChangementCode(Entree):
    """Route 14 : son code (l'actuel, puis le nouveau)."""

    ancien: str = Field(max_length=CODE_MAX)
    nouveau: str = Field(max_length=CODE_MAX)


class UtilisateurFiche(Sortie):
    """Routes 15–17 : un compte tel que l'administration le montre."""

    id: int
    identifiant: str
    nom: str
    role: str | None
    role_libelle: str
    email: str
    actif: bool
    historique: bool
    vu_le: datetime | None
    code_change_le: datetime | None
    cree_le: datetime
    version: int
    sessions_ouvertes: int

    @classmethod
    def de(cls, fiche: FicheCompte) -> UtilisateurFiche:
        """La fiche d'un compte."""
        u = fiche.utilisateur
        return cls(
            id=u.id,
            identifiant=u.identifiant,
            nom=u.nom,
            role=u.role,
            role_libelle=libelle_role(u.role),
            email=u.email,
            actif=u.actif,
            historique=u.historique,
            vu_le=u.vu_le,
            code_change_le=u.code_change_le,
            cree_le=u.cree_le,
            version=u.version,
            sessions_ouvertes=fiche.sessions_ouvertes,
        )


class UtilisateurCreation(Entree):
    """Route 16 : un nouveau compte."""

    identifiant: str = Field(min_length=2, max_length=L.IDENTIFIANT)
    nom: str = Field(min_length=2, max_length=L.NOM_PERSONNE)
    role: str = Field(max_length=L.ROLE)
    email: str = Field(default="", max_length=L.EMAIL_COMPTE)
    code: str = Field(min_length=1, max_length=CODE_MAX)


class UtilisateurModification(Entree):
    """Route 17 : la fiche entière (désactiver compris) ; `code` exigé si le rôle le demande."""

    nom: str = Field(min_length=2, max_length=L.NOM_PERSONNE)
    role: str = Field(max_length=L.ROLE)
    email: str = Field(default="", max_length=L.EMAIL_COMPTE)
    actif: bool
    version: int = Field(ge=1)
    code: str | None = Field(default=None, max_length=CODE_MAX)


class NouveauCode(Entree):
    """Route 18 : le code remis par la direction ou l'administrateur."""

    code: str = Field(min_length=1, max_length=CODE_MAX)


class AppareilFiche(Sortie):
    """Route 19 : un appareil (téléphone de l'atelier)."""

    id: int
    nom: str
    actif: bool
    enrole: bool
    enrole_le: datetime | None
    enrolement_expire_le: datetime | None
    vu_le: datetime | None
    cree_le: datetime
    cree_par: str
    sessions_ouvertes: int

    @classmethod
    def de(cls, fiche: FicheAppareil) -> AppareilFiche:
        """La fiche d'un appareil."""
        a = fiche.appareil
        return cls(
            id=a.id,
            nom=a.nom,
            actif=a.actif,
            enrole=a.empreinte_jeton is not None,
            enrole_le=a.enrole_le,
            enrolement_expire_le=a.enrolement_expire_le,
            vu_le=a.vu_le,
            cree_le=a.cree_le,
            cree_par=fiche.cree_par,
            sessions_ouvertes=fiche.sessions_ouvertes,
        )


class AppareilCreation(Entree):
    """Route 20 : le nom de l'appareil à enrôler."""

    nom: str = Field(min_length=2, max_length=L.NOM_APPAREIL)


class Enrolement(Sortie):
    """Route 20 : le lien à usage unique (15 minutes) et son QR."""

    id: int
    nom: str
    lien: str
    qr_svg: str
    expire_le: datetime

    @classmethod
    def de(cls, e: EnrolementService) -> Enrolement:
        """L'enrôlement à montrer."""
        a = e.appareil
        return cls(id=a.id, nom=a.nom, lien=e.lien, qr_svg=e.qr_svg, expire_le=e.expire_le)


class EnrolementEntree(Entree):
    """Route 22 : le jeton lu dans le QR."""

    jeton: str = Field(min_length=1, max_length=100)
