"""Appareils enrôlés, accès au serveur depuis un téléphone (ARCHITECTURE § 5.1 ; A10–A13).

- Enrôlement : la direction ou l'administrateur crée l'appareil ; un QR à **usage unique**,
  valable 15 minutes, porte l'adresse `/enroler?jeton=…` ; le téléphone l'ouvre, le serveur lui
  remet un cookie d'appareil (400 jours). Seuls le poste local et un appareil enrôlé voient les
  visages à la connexion (R7, P1-26).
- Retrait : l'appareil est révoqué et ses sessions fermées.
- Accès : adresse publique (réglage `adresse_publique`, sinon `GESTIONMPPRO_ADRESSE`), adresse
  réseau détectée, nom de la machine ; alerte si le QR mènerait à `localhost` (X5).
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlsplit

import segno
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import moteur
from gestion_mp_pro.modeles import Appareil, Parametre, SessionOuverte, Utilisateur
from gestion_mp_pro.modeles.enums import ObjetJournal
from gestion_mp_pro.services import audit, horloge, sessions

DUREE_ENROLEMENT = timedelta(minutes=15)
DUREE_COOKIE_JOURS = 400
VU_NOTE_TOUTES = timedelta(minutes=1)
HOTES_LOCAUX = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})
MESSAGE_EXPIRE = (
    "Ce QR d'enrôlement a expiré ou a déjà servi : en demander un nouveau dans "
    "Administration › Appareils."
)


# ── Accès au serveur ─────────────────────────────────────────────────────────


def est_local(adresse: str) -> bool:
    """L'adresse mène-t-elle au poste lui-même (que le téléphone ne joindrait pas) ?"""
    hote = (urlsplit(adresse).hostname or "").lower()
    return hote in HOTES_LOCAUX or hote.endswith(".localhost")


def ip_reseau() -> str:
    """L'adresse IP du poste sur le réseau (socket UDP « connecté », aucun paquet envoyé)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonde:
            sonde.connect(("10.255.255.255", 1))
            return str(sonde.getsockname()[0])
    except OSError:
        return "127.0.0.1"


PORTS_IMPLICITES = {"http": 80, "https": 443}


def adresse_de(adresse_demandee: str, hote: str | None = None) -> str:
    """L'adresse du serveur pour un autre poste : schéma et port **de la requête** ; l'hôte
    donné, sinon celui de la requête (un nom local devient l'adresse IP du poste) ; port
    implicite (80, 443) omis — derrière HTTPS, `https://nom` sans « :8050 » (G-13)."""
    morceaux = urlsplit(adresse_demandee)
    schema = morceaux.scheme or "http"
    if hote is None:
        hote = morceaux.hostname or "localhost"
        if est_local(adresse_demandee):
            hote = ip_reseau()
    port = morceaux.port
    if port is None or PORTS_IMPLICITES.get(schema) == port:
        return f"{schema}://{hote}"
    return f"{schema}://{hote}:{port}"


def adresse_publique(s: Session) -> str:
    """Le réglage `adresse_publique`, sinon `GESTIONMPPRO_ADRESSE` (sans « / » final)."""
    p = s.get(Parametre, "adresse_publique")
    valeur = (p.valeur if p is not None else "") or reglages().adresse
    return valeur.strip().rstrip("/")


@dataclass(frozen=True)
class Acces:
    """Les adresses du serveur pour un téléphone, celle du QR, et l'alerte éventuelle."""

    adresses: list[tuple[str, str]]
    adresse_publique: str
    adresse_qr: str
    alerte_localhost: str | None = None


def acces(s: Session, adresse_demandee: str) -> Acces:
    """Les adresses d'accès (route 5) ; `adresse_demandee` = celle par laquelle on appelle :
    son schéma et son port font ceux des adresses rendues (G-13), sinon les réglages."""
    demandee = adresse_demandee.rstrip("/")
    if not urlsplit(demandee).scheme:
        r = reglages()
        demandee = f"{'https' if r.https else 'http'}://localhost:{r.port}"
    reseau = adresse_de(demandee, ip_reseau())
    machine = adresse_de(demandee, socket.gethostname().split(".")[0].lower())
    publique = adresse_publique(s)
    qr = publique or (demandee if demandee and not est_local(demandee) else reseau)
    adresses = [("Adresse réseau", reseau), ("Nom de la machine", machine)]
    if publique:
        adresses.insert(0, ("Adresse publique", publique))
    alerte = None
    if est_local(qr):
        alerte = (
            f"Le QR mène à {qr} : un téléphone ne joindrait pas cette adresse. Régler "
            "l'adresse publique (Administration › Technique)."
        )
    return Acces(adresses, publique, qr, alerte)


def qr_svg(texte: str, echelle: int = 6, marge: int = 2) -> str:
    """Le QR d'un texte en SVG en ligne (correction d'erreur « m »)."""
    return str(segno.make(texte, error="m").svg_inline(scale=echelle, border=marge))


# ── Appareils ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FicheAppareil:
    """Un appareil, son créateur et ses sessions ouvertes."""

    appareil: Appareil
    cree_par: str
    sessions_ouvertes: int


@dataclass(frozen=True)
class Enrolement:
    """Un appareil à enrôler : le lien à usage unique et son QR."""

    appareil: Appareil
    lien: str
    qr_svg: str
    expire_le: datetime
    jeton: str = field(repr=False, default="")


def lister(s: Session) -> list[FicheAppareil]:
    """Tous les appareils, actifs d'abord, puis par nom."""
    ouvertes = dict(
        s.execute(
            select(SessionOuverte.appareil_id, func.count())
            .where(SessionOuverte.appareil_id.is_not(None))
            .group_by(SessionOuverte.appareil_id)
        ).all()
    )
    requete = (
        select(Appareil, Utilisateur.nom)
        .join(Utilisateur, Utilisateur.id == Appareil.cree_par_id)
        .order_by(Appareil.actif.desc(), func.lower(Appareil.nom))
    )
    return [
        FicheAppareil(a, nom, int(ouvertes.get(a.id, 0))) for a, nom in s.execute(requete).all()
    ]


def creer(s: Session, qui: audit.Qui, nom: str, adresse_base: str) -> Enrolement:
    """Crée l'appareil et son QR d'enrôlement (15 minutes, usage unique)."""
    propre = nom.strip()
    jeton = sessions.nouveau_jeton()
    expire = horloge.maintenant() + DUREE_ENROLEMENT
    a = Appareil(
        nom=propre,
        empreinte_enrolement=sessions.empreinte(jeton),
        enrolement_expire_le=expire,
        cree_par_id=qui.id,
        cree_le=horloge.maintenant(),
    )
    try:
        with s.begin_nested():
            s.add(a)
            s.flush()
    except IntegrityError as exc:
        raise Refus.etat(f"Un appareil s'appelle déjà « {propre} ».", code="doublon") from exc
    audit.creation(s, qui, "appareil à enrôler", a, detail=propre)
    lien = f"{adresse_base.rstrip('/')}/enroler?jeton={jeton}"
    return Enrolement(a, lien, qr_svg(lien), expire, jeton)


def enroler(s: Session, jeton: str) -> str:
    """Le téléphone présente le jeton du QR ; rend le jeton d'appareil (cookie, 400 jours)."""
    requete = (
        select(Appareil)
        .where(Appareil.empreinte_enrolement == sessions.empreinte(jeton))
        .with_for_update()
    )
    a = s.scalars(requete).first() if jeton else None
    if (
        a is None
        or not a.actif
        or a.enrolement_expire_le is None
        or a.enrolement_expire_le <= horloge.maintenant()
    ):
        raise Refus.etat(MESSAGE_EXPIRE, code="enrolement_expire")
    cle = sessions.nouveau_jeton()
    a.empreinte_jeton = sessions.empreinte(cle)
    a.empreinte_enrolement = None
    a.enrolement_expire_le = None
    a.enrole_le = a.vu_le = horloge.maintenant()
    audit.journal(s, None, "enrôlement d'appareil", ObjetJournal.appareil, a.id, detail=a.nom)
    return cle


def revoquer(s: Session, qui: audit.Qui, ident: int) -> None:
    """Retire l'appareil : jeton oublié, sessions ouvertes depuis lui fermées."""
    a = s.scalars(select(Appareil).where(Appareil.id == ident).with_for_update()).first()
    if a is None:
        raise Refus.introuvable("Appareil introuvable.")
    with audit.suivre(s, qui, "retrait d'appareil", a, detail=a.nom):
        a.actif = False
        a.empreinte_jeton = None
        a.empreinte_enrolement = None
        a.enrolement_expire_le = None
    sessions.fermer_sessions_appareil(s, a.id)


def par_jeton(s: Session, jeton: str | None) -> Appareil | None:
    """L'appareil actif de ce cookie (sa dernière visite notée au plus une fois par minute)."""
    if not jeton:
        return None
    requete = select(Appareil).where(
        Appareil.empreinte_jeton == sessions.empreinte(jeton), Appareil.actif
    )
    a = s.scalars(requete).first()
    maintenant = horloge.maintenant()
    if a is not None and (a.vu_le is None or maintenant - a.vu_le >= VU_NOTE_TOUTES):
        with moteur().begin() as c:
            c.execute(update(Appareil).where(Appareil.id == a.id).values(vu_le=maintenant))
    return a
