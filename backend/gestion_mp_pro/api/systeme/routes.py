"""Routes du domaine « Système ».

Lot S2 (routes 2–7) et D10 (route 1, santé) ; S0 a posé la première forme de `GET /sante`.
Routes minces : chemin, droits, schémas, `summary` ; un appel de service ; aucune règle métier
(ARCHITECTURE § 3.1).
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import Query, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from gestion_mp_pro import __version__
from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.comptes.schemas import Moi
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import Refus, reponses
from gestion_mp_pro.api.systeme.schemas import (
    Acces,
    AdresseAcces,
    Contexte,
    DomainePermis,
    EtatInstallation,
    InventaireOuvert,
    Sante,
)
from gestion_mp_pro.config import RACINE
from gestion_mp_pro.db import DISPONIBILITE, moteur
from gestion_mp_pro.securite import TOUS, C, QuiDep, T, droit, gestes_de
from gestion_mp_pro.securite.matrice import domaines_permis
from gestion_mp_pro.services import appareils, comptes, horloge
from gestion_mp_pro.services import contexte as service_contexte

routeur = nouveau_routeur("systeme")


def version_servie() -> str:
    """La version servie : le fichier VERSION de la copie figée (scripts/demarrer.sh), sinon
    la version du paquet suivie de « projet » (serveur lancé depuis le dépôt)."""
    fichier = RACINE / "VERSION"
    if fichier.is_file():
        return fichier.read_text(encoding="utf-8").strip() or __version__
    return f"{__version__} (projet)"


def _base_ms() -> float | None:
    """Temps d'un `SELECT 1`, en millisecondes ; `None` si la base ne répond pas."""
    debut = time.perf_counter()
    try:
        with moteur().connect() as c:
            c.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return None
    return round((time.perf_counter() - debut) * 1000, 1)


@routeur.get(
    "/sante",
    response_model=Sante,
    response_model_by_alias=True,
    summary="Santé du serveur pour la surveillance (public, sans donnée métier).",
)
def sante() -> Sante:
    """Route 1 : la base répond-elle, le schéma est-il à jour, quelle version est servie."""
    base_ms = _base_ms()
    etat = "ok" if base_ms is not None and not DISPONIBILITE.schema_en_retard else "degrade"
    return Sante(etat=etat, version=version_servie(), base_ms=base_ms)


@routeur.get(
    "/etat",
    response_model=EtatInstallation,
    summary="Installé ou non, raison sociale, version (public, pour l'écran de connexion).",
)
def etat(s: SessionDep) -> EtatInstallation:
    """Route 2 : seul `installe=false` mène à l'installation (K23)."""
    return EtatInstallation(
        installe=comptes.est_installe(s), societe=comptes.societe(s), version=version_servie()
    )


@routeur.get(
    "/contexte",
    response_model=Contexte,
    dependencies=[droit(*TOUS)],
    summary="Le démarrage de l'écran en un appel : compte, menu, heure, période, inventaires.",
    responses=reponses(401),
)
def contexte(requete: Request, qui: QuiDep, s: SessionDep) -> Contexte:
    """Route 3 : le menu est dérivé de la matrice des droits (domaines lus ou écrits)."""
    c = service_contexte.contexte(s, qui.role)
    return Contexte(
        moi=Moi.de(comptes.moi(s, qui), gestes_de(qui.role)),
        menu=[DomainePermis(**d) for d in domaines_permis(requete.app, qui.role)],
        heure_serveur=horloge.maintenant(),
        societe=c.societe,
        date_cloture=c.date_cloture,
        inventaires_ouverts=[InventaireOuvert(**vars(i)) for i in c.inventaires_ouverts],
        roles_au_metre=c.roles_au_metre,
        base_essai=c.base_essai,
        compteurs=c.compteurs,
        alerte_serveur=c.alerte_serveur,
    )


@routeur.get(
    "/acces",
    response_model=Acces,
    dependencies=[droit(*C, T)],
    summary="Les adresses du serveur pour un téléphone, celle du QR, et l'alerte localhost.",
    responses=reponses(401, 403),
)
def acces(requete: Request, s: SessionDep) -> Acces:
    """Route 5 (ouverte aussi à l'administrateur, API-PRO § 1.24)."""
    a = appareils.acces(s, str(requete.base_url))
    return Acces(
        adresses=[AdresseAcces(libelle=x, adresse=y) for x, y in a.adresses],
        adresse_publique=a.adresse_publique,
        adresse_qr=a.adresse_qr,
        alerte_localhost=a.alerte_localhost,
    )


ADRESSE_MAX = 200


@routeur.get(
    "/acces/qr",
    dependencies=[droit(*C, T)],
    summary="Le QR (SVG) d'une adresse d'accès (par défaut celle du QR).",
    responses={**reponses(401, 403, 422), 200: {"content": {"image/svg+xml": {}}}},
    response_class=Response,
)
def acces_qr(
    requete: Request,
    s: SessionDep,
    adresse: Annotated[str | None, Query(max_length=ADRESSE_MAX)] = None,
) -> Response:
    """Route 6 : une adresse donnée commence par http:// ou https:// (KR35)."""
    texte = adresse.strip() if adresse else appareils.acces(s, str(requete.base_url)).adresse_qr
    if not texte.startswith(("http://", "https://")) or " " in texte:
        raise Refus.saisie(
            "L'adresse commence par http:// ou https:// (ex. http://mac-usine:8050).",
            champs={"adresse": "http:// ou https://"},
        )
    return Response(appareils.qr_svg(texte), media_type="image/svg+xml")
