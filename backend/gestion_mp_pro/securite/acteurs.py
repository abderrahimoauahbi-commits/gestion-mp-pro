"""Qui est là : cookie de session → acteur ; poste local ou appareil enrôlé ; cookies (§ 5.1).

`acteur_de_la_requete(requete, s)` est le crochet que `api.dependances.acteur` appelle (lot S0) :
cookie `gestion_mp_pro_session` → empreinte SHA-256 → session non expirée → compte actif ;
sinon 401. Il pose `requete.state.acteur` (journal du serveur, filtre des prix).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from gestion_mp_pro.api import dependances
from gestion_mp_pro.config import COOKIE_APPAREIL, COOKIE_SESSION, reglages
from gestion_mp_pro.services import appareils, sessions
from gestion_mp_pro.services.comptes import Acteur, Poste

POSTES_LOCAUX = frozenset({"127.0.0.1", "::1"})
"""Le poste de l'usine (le Mac, qui sert l'application) : il voit les visages."""

SECONDES_PAR_JOUR = 86_400

QuiDep = Annotated[Acteur, Depends(dependances.acteur)]
"""La personne connectée, typée `Acteur` (même dépendance que `ActeurDep` : un seul calcul)."""


def adresse_de(requete: Request) -> str:
    """L'adresse réseau du client (sans croire `X-Forwarded-For`)."""
    return requete.client.host if requete.client is not None else ""


def poste_local(requete: Request) -> bool:
    """La requête vient-elle du poste qui sert l'application ?"""
    return adresse_de(requete) in POSTES_LOCAUX


def poste_de(requete: Request, s: Session) -> Poste:
    """D'où vient la requête : adresse, navigateur, appareil enrôlé, visages permis ou non."""
    appareil = appareils.par_jeton(s, requete.cookies.get(COOKIE_APPAREIL))
    return Poste(
        adresse=adresse_de(requete),
        agent=requete.headers.get("user-agent", ""),
        appareil_id=appareil.id if appareil is not None else None,
        autorise=poste_local(requete) or appareil is not None,
    )


def acteur_de_la_requete(requete: Request, s: Session) -> Acteur:
    """La personne connectée (401 « Connectez-vous pour continuer. » sinon)."""
    valide = sessions.session_valide(s, requete.cookies.get(COOKIE_SESSION))
    u = valide.utilisateur
    acteur = Acteur(
        id=u.id,
        identifiant=u.identifiant,
        nom=u.nom,
        role=str(u.role or ""),
        requete=str(getattr(requete.state, "requete", "")),
        adresse=adresse_de(requete),
        session=valide.session.empreinte,
        appareil_id=valide.session.appareil_id,
    )
    requete.state.acteur = acteur
    return acteur


def poser_cookie_session(reponse: Response, jeton: str) -> None:
    """Le cookie de session : `HttpOnly`, `SameSite=Lax`, `Secure` derrière HTTPS."""
    r = reglages()
    reponse.set_cookie(
        COOKIE_SESSION,
        jeton,
        max_age=r.session_jours * SECONDES_PAR_JOUR,
        httponly=True,
        samesite="lax",
        secure=r.https,
        path="/",
    )


def effacer_cookie_session(reponse: Response) -> None:
    """Efface le cookie de session (déconnexion)."""
    reponse.delete_cookie(COOKIE_SESSION, path="/", httponly=True, samesite="lax")


def poser_cookie_appareil(reponse: Response, jeton: str) -> None:
    """Le cookie d'un appareil enrôlé (400 jours)."""
    reponse.set_cookie(
        COOKIE_APPAREIL,
        jeton,
        max_age=appareils.DUREE_COOKIE_JOURS * SECONDES_PAR_JOUR,
        httponly=True,
        samesite="lax",
        secure=reglages().https,
        path="/",
    )
