"""Sessions et essais de connexion (ARCHITECTURE § 5.1 ; héritage K32–K36, défauts F-02, F-03).

- Session : jeton `secrets.token_urlsafe(32)` remis en cookie ; en base, sa seule empreinte
  SHA-256 ; durée fixe `GESTIONMPPRO_SESSION_JOURS`. `vu_le` (session et compte) noté au plus
  une fois par minute, par une connexion à part (la transaction de la requête reste intacte et
  la `version` du compte ne bouge pas).
- Essais : l'essai est **compté avant** de vérifier le code, sous verrou de ligne, et le blocage
  posé dès le 5ᵉ échec (30 s, doublé à chaque échec, 15 min au plus) : vingt essais lancés
  ensemble attendent leur tour, cinq au plus sont vérifiés (F-02). Une même adresse est bloquée
  au-delà de 20 échecs (essais sur plusieurs comptes). Les essais s'écrivent dans une session
  à part, validée tout de suite : le refus qui suit annule la transaction de la requête.
- Purge (tâche `purges`, et à chaque connexion) : sessions expirées depuis plus de 7 jours,
  tentatives sans échec depuis 30 jours et non bloquées.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.modeles import SessionOuverte, Tentative, Utilisateur
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.services import horloge

ECHECS_TOLERES = 5
ECHECS_TOLERES_ADRESSE = 20
BLOCAGE_BASE_S = 30
BLOCAGE_MAX_S = 900
ACTIVITE_NOTEE_TOUTES = timedelta(minutes=1)
SESSIONS_EXPIREES_GARDEES = timedelta(days=7)
TENTATIVES_GARDEES = timedelta(days=30)

MESSAGE_NON_CONNECTE = "Connectez-vous pour continuer."
MESSAGE_INACTIF = "Ce compte n'est plus actif."


def empreinte(jeton: str) -> str:
    """L'empreinte SHA-256 (hexadécimale) d'un jeton : seule elle est gardée en base."""
    return hashlib.sha256(jeton.encode()).hexdigest()


def nouveau_jeton() -> str:
    """Un jeton de session ou d'appareil, imprévisible."""
    return secrets.token_urlsafe(32)


def cle_adresse(adresse: str) -> str:
    """La clé des essais d'une adresse réseau (tient dans les 40 caractères de la table)."""
    return "@" + hashlib.sha256(adresse.encode()).hexdigest()[:32]


def cle_identifiant(identifiant: str) -> str:
    """La clé des essais d'un compte : son identifiant en minuscules."""
    return identifiant.strip().lower()[: L.IDENTIFIANT]


def duree_blocage(echecs: int, toleres: int) -> int:
    """`min(900, 30 × 2^(échecs − tolérés))` secondes dès le seuil atteint (K33)."""
    return int(min(BLOCAGE_MAX_S, BLOCAGE_BASE_S * 2 ** max(0, echecs - toleres)))


def _reserver(s: Session, cle: str, toleres: int) -> int:
    """Compte l'essai d'une clé sous verrou ; rend l'attente (s) si elle est bloquée, sinon 0."""
    maintenant = horloge.maintenant()
    s.execute(
        insert(Tentative)
        .values(identifiant=cle, echecs=0, dernier_echec_le=maintenant)
        .on_conflict_do_nothing(index_elements=["identifiant"])
    )
    requete = (
        select(Tentative)
        .where(Tentative.identifiant == cle)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    t = s.scalars(requete).one()
    if t.bloque_jusqua is not None and t.bloque_jusqua > maintenant:
        return max(1, int((t.bloque_jusqua - maintenant).total_seconds()))
    t.echecs += 1
    t.dernier_echec_le = maintenant
    if t.echecs >= toleres:
        t.bloque_jusqua = maintenant + timedelta(seconds=duree_blocage(t.echecs, toleres))
    s.flush()
    return 0


def reserver_essai(*cles: tuple[str, int]) -> int:
    """Compte un essai pour chaque clé `(clé, seuil)`, dans une transaction à part, validée.

    Rend l'attente en secondes dès qu'une clé est bloquée (les suivantes ne sont pas comptées),
    0 si l'essai peut être vérifié. Un succès efface ensuite les clés (`noter_succes`).
    """
    with fabrique()() as s, s.begin():
        for cle, toleres in cles:
            attente = _reserver(s, cle, toleres)
            if attente:
                return attente
    return 0


def noter_succes(*cles: str) -> None:
    """Un code juste efface les essais comptés (transaction à part, validée)."""
    with fabrique()() as s, s.begin():
        s.execute(delete(Tentative).where(Tentative.identifiant.in_(cles)))


def refus_patienter(secondes: int) -> Refus:
    """429 « Trop d'essais : patientez {n} secondes. » (KR10)."""
    return Refus.trop_d_essais(f"Trop d'essais : patientez {secondes} secondes.")


def ouvrir(
    s: Session,
    u: Utilisateur,
    *,
    adresse: str = "",
    agent: str = "",
    appareil_id: int | None = None,
) -> str:
    """Ouvre une session pour le compte ; rend le jeton à remettre en cookie."""
    jeton = nouveau_jeton()
    maintenant = horloge.maintenant()
    s.add(
        SessionOuverte(
            empreinte=empreinte(jeton),
            utilisateur_id=u.id,
            appareil_id=appareil_id,
            cree_le=maintenant,
            expire_le=maintenant + timedelta(days=reglages().session_jours),
            vu_le=maintenant,
            adresse=adresse[: L.ADRESSE_IP],
            agent=agent[: L.AGENT],
        )
    )
    s.execute(update(Utilisateur).where(Utilisateur.id == u.id).values(vu_le=maintenant))
    set_committed_value(u, "vu_le", maintenant)
    return jeton


def fermer(s: Session, jeton: str | None) -> None:
    """Ferme la session de ce jeton (s'il en a une)."""
    if jeton:
        s.execute(delete(SessionOuverte).where(SessionOuverte.empreinte == empreinte(jeton)))


def fermer_sessions(s: Session, utilisateur_id: int, sauf: str | None = None) -> int:
    """Ferme les sessions du compte, sauf celle d'empreinte `sauf` ; rend leur nombre."""
    requete = delete(SessionOuverte).where(SessionOuverte.utilisateur_id == utilisateur_id)
    if sauf:
        requete = requete.where(SessionOuverte.empreinte != sauf)
    return int(getattr(s.execute(requete), "rowcount", 0) or 0)


def fermer_sessions_appareil(s: Session, appareil_id: int) -> int:
    """Ferme toutes les sessions ouvertes depuis un appareil (révocation)."""
    resultat = s.execute(delete(SessionOuverte).where(SessionOuverte.appareil_id == appareil_id))
    return int(getattr(resultat, "rowcount", 0) or 0)


@dataclass(frozen=True)
class SessionValide:
    """Une session reconnue et son compte."""

    session: SessionOuverte
    utilisateur: Utilisateur


def session_valide(s: Session, jeton: str | None) -> SessionValide:
    """La session du jeton : 401 si absente ou expirée, 401 « plus actif » si le compte l'est."""
    ouverte = s.get(SessionOuverte, empreinte(jeton)) if jeton else None
    if ouverte is None or ouverte.expire_le <= horloge.maintenant():
        raise Refus.non_connecte(MESSAGE_NON_CONNECTE)
    u = s.get(Utilisateur, ouverte.utilisateur_id)
    if u is None or not u.actif or u.historique:
        raise Refus.non_connecte(MESSAGE_INACTIF, code="compte_inactif")
    noter_activite(ouverte, u)
    return SessionValide(ouverte, u)


def noter_activite(ouverte: SessionOuverte, u: Utilisateur) -> None:
    """« Dernière activité » de la session et du compte, au plus une fois par minute (F-03)."""
    maintenant = horloge.maintenant()
    if maintenant - ouverte.vu_le < ACTIVITE_NOTEE_TOUTES:
        return
    with moteur().begin() as c:
        c.execute(
            update(SessionOuverte)
            .where(SessionOuverte.empreinte == ouverte.empreinte)
            .values(vu_le=maintenant)
        )
        c.execute(update(Utilisateur).where(Utilisateur.id == u.id).values(vu_le=maintenant))
    set_committed_value(ouverte, "vu_le", maintenant)
    set_committed_value(u, "vu_le", maintenant)


@dataclass(frozen=True)
class Purge:
    """Ce que la purge a retiré."""

    sessions: int
    tentatives: int


def purger(s: Session) -> Purge:
    """Sessions expirées depuis 7 jours, tentatives vieilles de 30 jours et non bloquées."""
    maintenant = horloge.maintenant()
    sessions = s.execute(
        delete(SessionOuverte).where(
            SessionOuverte.expire_le < maintenant - SESSIONS_EXPIREES_GARDEES
        )
    )
    tentatives = s.execute(
        delete(Tentative).where(
            Tentative.dernier_echec_le < maintenant - TENTATIVES_GARDEES,
            (Tentative.bloque_jusqua.is_(None)) | (Tentative.bloque_jusqua < maintenant),
        )
    )
    return Purge(
        int(getattr(sessions, "rowcount", 0) or 0), int(getattr(tentatives, "rowcount", 0) or 0)
    )


def sessions_ouvertes(s: Session, utilisateur_id: int) -> list[SessionOuverte]:
    """Les sessions non expirées d'un compte."""
    requete = select(SessionOuverte).where(
        SessionOuverte.utilisateur_id == utilisateur_id,
        SessionOuverte.expire_le > horloge.maintenant(),
    )
    return list(s.scalars(requete))
