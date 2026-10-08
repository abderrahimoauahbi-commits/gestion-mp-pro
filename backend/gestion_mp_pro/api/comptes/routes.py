"""Routes du domaine « Comptes et appareils » (API-PRO § 1.2, routes 8–22).

Routes minces : chemin, droits, schémas, `summary` ; un appel de service ; les cookies de
session et d'appareil sont posés ici (couche HTTP), jamais dans les services.
"""

from __future__ import annotations

from fastapi import Request, Response

from gestion_mp_pro.api.communs import nouveau_routeur
from gestion_mp_pro.api.comptes.schemas import (
    AppareilCreation,
    AppareilFiche,
    ChangementCode,
    Connexion,
    Enrolement,
    EnrolementEntree,
    Installation,
    Moi,
    MoiModification,
    NouveauCode,
    UtilisateurCreation,
    UtilisateurFiche,
    UtilisateurModification,
    Visage,
)
from gestion_mp_pro.api.dependances import SessionDep
from gestion_mp_pro.api.erreurs import reponses
from gestion_mp_pro.config import COOKIE_SESSION
from gestion_mp_pro.modeles import Utilisateur
from gestion_mp_pro.securite import (
    TOUS,
    D,
    QuiDep,
    T,
    droit,
    effacer_cookie_session,
    gestes_de,
    poser_cookie_appareil,
    poser_cookie_session,
    poste_de,
)
from gestion_mp_pro.services import appareils, comptes, sessions, utilisateurs

routeur = nouveau_routeur("comptes")

SANS_CORPS = {"status_code": 204, "response_class": Response}


def _moi(u: Utilisateur) -> Moi:
    """La fiche `Moi` d'un compte, avec les gestes de son rôle."""
    return Moi.de(u, gestes_de(str(u.role or "")))


@routeur.get(
    "/visages",
    response_model=list[Visage],
    summary="Les noms à toucher pour se connecter (poste local ou appareil enrôlé seulement).",
)
def visages(requete: Request, s: SessionDep) -> list[Visage]:
    """Route 8 : ailleurs, liste vide (on tape son identifiant, P1-26)."""
    if not poste_de(requete, s).autorise:
        return []
    return [Visage.de(u) for u in comptes.visages(s)]


@routeur.post(
    "/installation",
    status_code=201,
    response_model=Moi,
    summary="Crée le premier compte, celui de la direction (une seule fois).",
    responses=reponses(409, 422),
)
def installation(corps: Installation, requete: Request, reponse: Response, s: SessionDep) -> Moi:
    """Route 9 : la session s'ouvre aussitôt (cookie)."""
    ouverture = comptes.installer(
        s,
        societe=corps.societe,
        identifiant=corps.identifiant,
        nom=corps.nom,
        code=corps.code,
        poste=poste_de(requete, s),
    )
    poser_cookie_session(reponse, ouverture.jeton)
    return _moi(ouverture.utilisateur)


@routeur.post(
    "/connexion",
    response_model=Moi,
    summary="Se connecter : nom touché ou identifiant, puis code.",
    responses=reponses(401, 403, 422, 429),
)
def connexion(corps: Connexion, requete: Request, reponse: Response, s: SessionDep) -> Moi:
    """Route 10 : essai compté avant la vérification ; 5 échecs, puis il faut patienter."""
    ouverture = comptes.connecter(
        s,
        compte_id=corps.compte,
        identifiant=corps.identifiant,
        code=corps.code,
        poste=poste_de(requete, s),
    )
    poser_cookie_session(reponse, ouverture.jeton)
    return _moi(ouverture.utilisateur)


@routeur.post(
    "/deconnexion",
    dependencies=[droit(*TOUS)],
    summary="Se déconnecter : la session est fermée et son cookie effacé.",
    responses=reponses(401, 403),
    **SANS_CORPS,
)
def deconnexion(requete: Request, s: SessionDep) -> Response:
    """Route 11 (exige l'en-tête de l'écran, contrairement à Gestion MP)."""
    sessions.fermer(s, requete.cookies.get(COOKIE_SESSION))
    reponse = Response(status_code=204)
    effacer_cookie_session(reponse)
    return reponse


@routeur.get(
    "/moi",
    response_model=Moi,
    dependencies=[droit(*TOUS)],
    summary="Le compte connecté, ce qu'il voit et ses droits fins.",
    responses=reponses(401),
)
def moi(qui: QuiDep, s: SessionDep) -> Moi:
    """Route 12."""
    return _moi(comptes.moi(s, qui))


@routeur.put(
    "/moi",
    response_model=Moi,
    dependencies=[droit(*TOUS)],
    summary="Modifier son courriel.",
    responses=reponses(401, 409, 422),
)
def modifier_moi(corps: MoiModification, qui: QuiDep, s: SessionDep) -> Moi:
    """Route 13."""
    return _moi(comptes.modifier_moi(s, qui, corps.email, corps.version))


@routeur.put(
    "/moi/code",
    dependencies=[droit(*TOUS)],
    summary="Changer son code : les autres sessions se ferment.",
    responses=reponses(401, 403, 422, 429),
    **SANS_CORPS,
)
def changer_mon_code(corps: ChangementCode, qui: QuiDep, s: SessionDep) -> Response:
    """Route 14 : un mauvais code actuel compte comme un échec de connexion (F-03)."""
    comptes.changer_mon_code(s, qui, corps.ancien, corps.nouveau)
    return Response(status_code=204)


@routeur.get(
    "/utilisateurs",
    response_model=list[UtilisateurFiche],
    dependencies=[droit(D, T)],
    summary="Tous les comptes, triés par nom.",
    responses=reponses(401, 403),
)
def lister_utilisateurs(s: SessionDep) -> list[UtilisateurFiche]:
    """Route 15."""
    return [UtilisateurFiche.de(f) for f in utilisateurs.lister(s)]


@routeur.post(
    "/utilisateurs",
    status_code=201,
    response_model=UtilisateurFiche,
    dependencies=[droit(D, T)],
    summary="Créer un compte (son code suit la règle de son rôle).",
    responses=reponses(401, 403, 409, 422),
)
def creer_utilisateur(corps: UtilisateurCreation, qui: QuiDep, s: SessionDep) -> UtilisateurFiche:
    """Route 16."""
    fiche = utilisateurs.creer(
        s,
        qui,
        identifiant=corps.identifiant,
        nom=corps.nom,
        role=corps.role,
        email=corps.email,
        code=corps.code,
    )
    return UtilisateurFiche.de(fiche)


@routeur.put(
    "/utilisateurs/{ident}",
    response_model=UtilisateurFiche,
    dependencies=[droit(D, T)],
    summary="Modifier un compte (fiche entière) ; désactiver ferme ses sessions.",
    responses=reponses(401, 403, 404, 409, 422),
)
def modifier_utilisateur(
    ident: int, corps: UtilisateurModification, qui: QuiDep, s: SessionDep
) -> UtilisateurFiche:
    """Route 17 : un changement de rôle peut exiger un nouveau code (`code`)."""
    modification = utilisateurs.Modification(**corps.model_dump())
    return UtilisateurFiche.de(utilisateurs.modifier(s, qui, ident, modification))


@routeur.post(
    "/utilisateurs/{ident}/code",
    dependencies=[droit(D, T)],
    summary="Remettre le code d'un compte : ses sessions se ferment.",
    responses=reponses(401, 403, 404, 409, 422),
    **SANS_CORPS,
)
def remettre_code(ident: int, corps: NouveauCode, qui: QuiDep, s: SessionDep) -> Response:
    """Route 18."""
    utilisateurs.remettre_code(s, qui, ident, corps.code)
    return Response(status_code=204)


@routeur.get(
    "/appareils",
    response_model=list[AppareilFiche],
    dependencies=[droit(D, T)],
    summary="Les appareils enrôlés (ou à enrôler) et leurs sessions.",
    responses=reponses(401, 403),
)
def lister_appareils(s: SessionDep) -> list[AppareilFiche]:
    """Route 19."""
    return [AppareilFiche.de(f) for f in appareils.lister(s)]


@routeur.post(
    "/appareils",
    status_code=201,
    response_model=Enrolement,
    dependencies=[droit(D, T)],
    summary="Créer un appareil et son QR d'enrôlement (15 minutes, usage unique).",
    responses=reponses(401, 403, 409, 422),
)
def creer_appareil(
    corps: AppareilCreation, requete: Request, qui: QuiDep, s: SessionDep
) -> Enrolement:
    """Route 20 : le QR porte l'adresse publique (ou l'adresse réseau détectée)."""
    base = appareils.acces(s, str(requete.base_url)).adresse_qr
    return Enrolement.de(appareils.creer(s, qui, corps.nom, base))


@routeur.post(
    "/appareils/enroler",
    summary="Enrôler l'appareil qui présente le jeton du QR (cookie d'appareil, 400 jours).",
    responses=reponses(409, 422),
    **SANS_CORPS,
)
def enroler(corps: EnrolementEntree, s: SessionDep) -> Response:
    """Route 22 (publique : le jeton à usage unique fait foi)."""
    jeton = appareils.enroler(s, corps.jeton)
    reponse = Response(status_code=204)
    poser_cookie_appareil(reponse, jeton)
    return reponse


@routeur.delete(
    "/appareils/{ident}",
    dependencies=[droit(D, T)],
    summary="Retirer un appareil : ses sessions se ferment.",
    responses=reponses(401, 403, 404),
    **SANS_CORPS,
)
def retirer_appareil(ident: int, qui: QuiDep, s: SessionDep) -> Response:
    """Route 21."""
    appareils.revoquer(s, qui, ident)
    return Response(status_code=204)
