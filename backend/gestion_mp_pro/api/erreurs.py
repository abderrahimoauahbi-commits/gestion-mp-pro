"""Convention d'erreur unique (API-PRO § 0.3, ARCHITECTURE C9).

Corps : `{"detail": "<phrase française>", "code": "<code>"}` (+ `"champs"` pour une saisie).
422 saisie · 409 état · 404 introuvable · 403 droit · 401 non connecté · 429 trop d'essais ·
503 indisponible ; jamais de 500 pour une saisie ni pour un refus de la base (contrainte,
version périmée : 409), et un 500 imprévu dit sa référence.

Les codes sont tous déclarés dans `CODES` (fichier du lot S0 ; un ajout se demande). Ce module
n'importe FastAPI qu'à l'installation des gestionnaires : les services y prennent `Refus` sans
charger la couche HTTP.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from gestion_mp_pro.api.traduction import RIEN_ENREGISTRE, traduire_refus_base, traduire_validation

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from starlette.responses import Response

__all__ = ["CODES", "Code", "ErreurReponse", "Refus", "corps_erreur", "reponses"]

MESSAGE_ROUTE_INCONNUE = "Route inconnue."
MESSAGE_CORPS_ILLISIBLE = "Corps de la requête illisible : du JSON est attendu."
MESSAGE_VERSION_PERIMEE = (
    "Cette fiche a été modifiée entre-temps par un autre poste : rouvrez-la pour repartir de "
    f"sa dernière version. {RIEN_ENREGISTRE}"
)
"""Le filet de `StaleDataError` ; `services.audit.verifier_version` (S2) nomme l'auteur."""


@dataclass(frozen=True)
class Code:
    """Un code de refus : son statut HTTP et ce qu'il veut dire."""

    http: int
    sens: str


def _famille(http: int, codes: dict[str, str]) -> dict[str, Code]:
    """Les codes d'une même famille HTTP."""
    return {nom: Code(http, sens) for nom, sens in codes.items()}


CODES: dict[str, Code] = {
    **_famille(
        422,
        {
            "saisie_invalide": "saisie refusée (type, borne, longueur, champ inconnu)",
            "valeur_inconnue": "une valeur citée n'existe pas (fournisseur, matière, magasin…)",
            "date_future": "date dans le futur",
            "date_trop_ancienne": "date antérieure au 01/01/2000",
            "date_invalide": "date ou mois incohérent (fin avant début, mois inexistant)",
            "quantite_invalide": "quantité nulle, négative ou hors bornes",
            "unite_invalide": "unité ou contenance non permise par la fiche de la matière",
            "devise_incompatible": "devise différente de celle du document",
            "ligne_en_double": "même matière ou même lot deux fois dans un document",
            "recette_incomplete": "une recette ne fait pas 100 % par rôle",
            "code_invalide": "code secret qui ne suit pas la règle de son rôle",
            "motif_requis": "motif obligatoire absent ou trop court",
            "confirmation_requise": "confirmation explicite absente ou fausse",
            "date_figee": "date promise figée depuis la confirmation des prix",
            "fichier_refuse": "type de pièce jointe refusé",
            "fichier_trop_gros": "pièce jointe au-delà de la taille permise",
            "tableur_invalide": "tableur importé avec des lignes en erreur (rien n'est écrit)",
            "curseur_invalide": "curseur de pagination illisible",
        },
    ),
    **_famille(
        409,
        {
            "conflit_version": "la fiche a été modifiée entre-temps (version périmée)",
            "etat_incompatible": "le statut du document interdit ce geste",
            "periode_close": "date dans la période close",
            "cout_periode_close": "coût d'une marchandise entrée dans un mois clos",
            "stock_insuffisant": "stock insuffisant à la date",
            "lot_absent_a_la_date": "lot pas encore entré à la date du mouvement",
            "inventaire_en_cours": "un inventaire ouvert suspend ce magasin ou cette matière",
            "numero_pris": "numéro déjà attribué",
            "doublon": "référence, code ou nom déjà pris",
            "deja_annule": "document déjà annulé",
            "deja_valide": "document déjà validé",
            "deja_installe": "l'installation a déjà été faite",
            "approbation_requise": "le montant demande l'approbation de la direction",
            "validation_bloquee": "des blocages calculés empêchent la validation",
            "bon_clos": "bon de commande soldé ou annulé",
            "dossier_clos": "dossier d'importation clos",
            "documents_lies": "des documents liés empêchent le geste (réceptions d'un bon…)",
            "fiche_utilisee": "fiche utilisée ailleurs : désactiver plutôt que supprimer",
            "fiche_inactive": "fiche désactivée",
            "reference_absente": "une fiche citée n'existe pas ou plus (refus de la base)",
            "regle_de_la_base": "saisie refusée par une contrainte de la base (dernier recours)",
            "excedent": "réception au-delà de la tolérance de la commande",
            "effet_change": "l'effet du montage a changé depuis son calcul",
            "ordre_des_dates": "date antérieure au dernier ordre (numéros dans l'ordre des dates)",
            "derniere_direction": "il doit toujours rester une direction active",
            "enrolement_expire": "QR d'enrôlement expiré ou déjà utilisé",
            "sauvegarde_autre_base": "sauvegarde d'une autre base",
            "activite_presente": "activité saisie dans PRO : la reprise exige de la remplacer",
            "tache_en_cours": "la même tâche tourne déjà",
            "pas_un_fond_de_lot": "reste au-dessus du seuil de rebut (direction seule, avec motif)",
        },
    ),
    **_famille(
        404,
        {
            "introuvable": "objet introuvable",
            "route_inconnue": "adresse inconnue de l'API",
        },
    ),
    **_famille(
        403,
        {
            "droit_refuse": "rôle sans droit sur cette route ou ce geste",
            "entete_absente": "écriture sans l'en-tête X-Gestion-MP-PRO",
            "poste_non_autorise": "visages réservés au poste local ou à un appareil enrôlé",
            "appareil_revoque": "appareil révoqué",
        },
    ),
    **_famille(
        401,
        {
            "non_connecte": "pas de session valide",
            "identifiants_incorrects": "identifiant ou code incorrect",
            "session_expiree": "session expirée ou fermée",
            "compte_inactif": "compte désactivé",
        },
    ),
    **_famille(405, {"methode_non_permise": "méthode HTTP non permise sur cette adresse"}),
    **_famille(410, {"fichier_disparu": "fichier d'une pièce jointe disparu du disque (G-10)"}),
    **_famille(
        429,
        {
            "trop_d_essais": "trop d'essais de connexion pour cet identifiant",
            "trop_de_requetes": "trop de requêtes depuis cette adresse",
        },
    ),
    **_famille(
        503,
        {
            "schema_en_retard": "base pas à la révision attendue",
            "restauration_en_cours": "restauration de sauvegarde en cours",
            "base_indisponible": "base injoignable",
            "sauvegarde_impossible": "sauvegarde ou restauration impossible (outils, disque)",
        },
    ),
    **_famille(
        500,
        {
            "erreur_serveur": "erreur imprévue, tracée avec sa référence",
            "erreur_http": "autre statut HTTP (ne devrait pas arriver)",
        },
    ),
}
"""Tous les codes de refus, par famille HTTP (API-PRO § 0.3)."""


class ErreurReponse(BaseModel):
    """Corps d'un refus, tel qu'il figure dans l'OpenAPI."""

    detail: str
    code: str
    champs: dict[str, str] | None = None


def corps_erreur(code: str, detail: str, champs: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Le corps JSON d'un refus (`champs` seulement s'il y en a)."""
    corps: dict[str, Any] = {"detail": detail, "code": code}
    if champs:
        corps["champs"] = dict(champs)
    return corps


class Refus(Exception):
    """Un refus métier : code déclaré, statut HTTP tiré de `CODES`, phrase française.

    `raise Refus.etat("Ce bon est clos.", code="bon_clos")` (409),
    `Refus.saisie(...)` (422), `Refus.introuvable(...)` (404).
    """

    def __init__(self, code: str, detail: str, champs: Mapping[str, str] | None = None) -> None:
        if code not in CODES:
            raise ValueError(f"Code de refus non déclaré dans api/erreurs.py : {code}")
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http = CODES[code].http
        self.champs = dict(champs) if champs else None

    @classmethod
    def _famille(
        cls, http: int, code: str, detail: str, champs: Mapping[str, str] | None = None
    ) -> Refus:
        """Un refus d'une famille donnée ; le code doit appartenir à cette famille."""
        if code in CODES and CODES[code].http != http:
            raise ValueError(f"Le code {code} est un {CODES[code].http}, pas un {http}.")
        return cls(code, detail, champs)

    @classmethod
    def saisie(
        cls, detail: str, code: str = "saisie_invalide", champs: Mapping[str, str] | None = None
    ) -> Refus:
        """422 : la saisie est refusée (type, borne, valeur inconnue, règle de saisie)."""
        return cls._famille(422, code, detail, champs)

    @classmethod
    def etat(cls, detail: str, code: str = "etat_incompatible") -> Refus:
        """409 : l'état interdit le geste (statut, version, stock, période close, doublon)."""
        return cls._famille(409, code, detail)

    @classmethod
    def introuvable(cls, detail: str, code: str = "introuvable") -> Refus:
        """404 : l'objet n'existe pas."""
        return cls._famille(404, code, detail)

    @classmethod
    def droit(cls, detail: str, code: str = "droit_refuse") -> Refus:
        """403 : le rôle n'y a pas droit."""
        return cls._famille(403, code, detail)

    @classmethod
    def non_connecte(
        cls, detail: str = "Connectez-vous pour continuer.", code: str = "non_connecte"
    ) -> Refus:
        """401 : pas de session valide."""
        return cls._famille(401, code, detail)

    @classmethod
    def trop_d_essais(cls, detail: str, code: str = "trop_d_essais") -> Refus:
        """429 : trop d'essais de connexion."""
        return cls._famille(429, code, detail)

    @classmethod
    def indisponible(cls, detail: str, code: str = "base_indisponible") -> Refus:
        """503 : base en retard de migration, restauration en cours, base injoignable."""
        return cls._famille(503, code, detail)

    def corps(self) -> dict[str, Any]:
        """Le corps JSON du refus."""
        return corps_erreur(self.code, self.detail, self.champs)


def reponses(*statuts: int) -> dict[int | str, dict[str, Any]]:
    """Les `responses` OpenAPI d'une route : `responses=reponses(404, 409)`."""
    sens = {
        401: "Non connecté",
        403: "Droit refusé",
        404: "Introuvable",
        410: "Disparu",
        409: "Conflit ou état",
        422: "Saisie refusée",
        429: "Trop d'essais",
        503: "Service indisponible",
    }
    return {s: {"model": ErreurReponse, "description": sens.get(s, "Refus")} for s in statuts}


MESSAGES_INDISPONIBLE = {
    "schema_en_retard": "La base n'est pas à jour : le serveur attend la fin de sa mise à niveau. "
    "Réessayez dans un instant ; si cela dure, prévenez l'administrateur.",
    "restauration_en_cours": "Une restauration de sauvegarde est en cours : "
    "réessayez dans un instant.",
    "base_indisponible": "La base de données ne répond pas : réessayez dans un instant ; "
    "si cela dure, prévenez l'administrateur.",
}

_CODE_PAR_STATUT = {
    400: "saisie_invalide",
    401: "non_connecte",
    403: "droit_refuse",
    404: "introuvable",
    405: "methode_non_permise",
    409: "etat_incompatible",
    422: "saisie_invalide",
    429: "trop_d_essais",
    503: "base_indisponible",
}


def reponse_erreur(code: str, detail: str, champs: Mapping[str, str] | None = None) -> Response:
    """La réponse JSON d'un refus, au statut de son code."""
    from fastapi.responses import JSONResponse

    return JSONResponse(corps_erreur(code, detail, champs), status_code=CODES[code].http)


def reponse_erreur_serveur(reference: str) -> Response:
    """500 imprévu : la phrase cite la référence que le journal du serveur porte aussi."""
    return reponse_erreur("erreur_serveur", f"Erreur du serveur (réf. {reference}).")


async def _sur_refus(_requete: Request, exc: Exception) -> Response:
    """Un `Refus` levé par un service ou une route."""
    assert isinstance(exc, Refus)  # noqa: S101 — garanti par l'enregistrement
    return reponse_erreur(exc.code, exc.detail, exc.champs)


async def _sur_validation(_requete: Request, exc: Exception) -> Response:
    """Une saisie refusée par Pydantic : 422 en français, champ par champ."""
    from fastapi.exceptions import RequestValidationError

    assert isinstance(exc, RequestValidationError)  # noqa: S101
    detail, champs = traduire_validation(exc.errors())
    return reponse_erreur("saisie_invalide", detail or MESSAGE_CORPS_ILLISIBLE, champs)


async def _sur_http(requete: Request, exc: Exception) -> Response:
    """Une `HTTPException` (route inconnue, méthode, corps illisible) mise à la convention."""
    from starlette.exceptions import HTTPException

    assert isinstance(exc, HTTPException)  # noqa: S101
    code = _CODE_PAR_STATUT.get(exc.status_code)
    if code is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(corps_erreur("erreur_http", str(exc.detail)), exc.status_code)
    if exc.status_code == HTTPStatus.NOT_FOUND and exc.detail in (None, "Not Found"):
        code, detail = "route_inconnue", MESSAGE_ROUTE_INCONNUE
    elif exc.status_code == HTTPStatus.METHOD_NOT_ALLOWED:
        detail = f"La méthode {requete.method} n'est pas permise sur cette adresse."
    elif exc.status_code == HTTPStatus.BAD_REQUEST:
        detail = MESSAGE_CORPS_ILLISIBLE
    else:
        detail = str(exc.detail)
    reponse = reponse_erreur(code, detail)
    for nom, valeur in (exc.headers or {}).items():
        reponse.headers[nom] = valeur
    return reponse


async def _sur_refus_base(requete: Request, exc: Exception) -> Response:
    """Dernier recours (défaut F-07) : une contrainte de la base violée → 409 en français.

    Chaque route refuse d'abord elle-même ce qu'elle sait refuser. La session de la requête a
    déjà été annulée (`db.session`, `rollback` sur toute exception) : rien n'est enregistré.
    Le détail technique (état SQL, contrainte, table, message) va au journal du serveur,
    jamais au client.
    """
    from sqlalchemy.exc import DBAPIError

    assert isinstance(exc, DBAPIError)  # noqa: S101
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None)
    diag = getattr(orig, "diag", None)
    contrainte = getattr(diag, "constraint_name", None)
    code, detail = traduire_refus_base(
        sqlstate, contrainte, getattr(diag, "message_detail", None), exc.statement
    )
    lignes = str(orig if orig is not None else exc).strip().splitlines()
    logging.getLogger("gestion_mp_pro").warning(
        "requete=%s refus de la base sur %s %s : %s (etat=%s contrainte=%s table=%s) %s",
        getattr(requete.state, "requete", "-"),
        requete.method,
        requete.url.path,
        code,
        sqlstate,
        contrainte,
        getattr(diag, "table_name", None),
        lignes[0] if lignes else type(exc).__name__,
    )
    return reponse_erreur(code, detail)


async def _sur_version_perimee(requete: Request, exc: Exception) -> Response:
    """Filet : l'ORM a trouvé une `version` changée au `flush` → 409 `conflit_version`."""
    logging.getLogger("gestion_mp_pro").warning(
        "requete=%s version périmée sur %s %s : %s",
        getattr(requete.state, "requete", "-"),
        requete.method,
        requete.url.path,
        exc,
    )
    return reponse_erreur("conflit_version", MESSAGE_VERSION_PERIMEE)


def installer_gestionnaires(app: FastAPI) -> None:
    """Pose les gestionnaires d'erreurs sur l'application (le 500 est tracé par `trace`).

    `IntegrityError` et `DataError` (contrainte de la base) et `StaleDataError` (version
    périmée) deviennent des 409 : jamais de 500 pour un refus de la base.
    """
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import DataError, IntegrityError
    from sqlalchemy.orm.exc import StaleDataError
    from starlette.exceptions import HTTPException

    app.add_exception_handler(Refus, _sur_refus)
    app.add_exception_handler(RequestValidationError, _sur_validation)
    app.add_exception_handler(HTTPException, _sur_http)
    app.add_exception_handler(IntegrityError, _sur_refus_base)
    app.add_exception_handler(DataError, _sur_refus_base)
    app.add_exception_handler(StaleDataError, _sur_version_perimee)
