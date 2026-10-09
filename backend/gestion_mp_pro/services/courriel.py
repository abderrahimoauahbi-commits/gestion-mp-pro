"""La file des courriels : mise en file une fois, envoi SMTP, reprises espacées (lot D10).

MODELE-DONNEES § 3.1.10 : chaque courriel a une clé unique (`lundi:2026-10-05`,
`alerte:sauvegarde:2026-10-08`) — le courriel du lundi n'est mis en file qu'**une fois**, quel
que soit le nombre de passages ou de processus ; il est essayé jusqu'à 5 fois, espacées de
15 min × 2ⁿ, puis abandonné (l'échec reste lisible : `GET /api/courriels`).

Défaut E-15 de Gestion MP corrigé : chaque adresse est vérifiée avant l'envoi (une adresse
illisible est écartée et dite) ; l'échec d'envoi se note sur le courriel, pas sous un autre
libellé ; la photo des indicateurs et le courriel sont deux tâches séparées.

Serveur d'envoi : `GESTIONMPPRO_SMTP_*` (STARTTLS, port 587 par défaut). Destinataires : le
réglage `courriel_destinataires` (adresses séparées par des virgules).
"""

from __future__ import annotations

import logging
import re
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Courriel, Parametre
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import GenreCourriel, StatutCourriel
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.reglages import ADRESSE_COURRIEL

JOURNAL = logging.getLogger("gestion_mp_pro.courriel")

ESSAIS_MAX = 5
ECART_DE_BASE = timedelta(minutes=15)
DELAI_SMTP_S = 30


def configure() -> bool:
    """Le serveur d'envoi est-il réglé ?"""
    return bool(reglages().smtp_hote)


def destinataires_du_reglage(s: Session) -> str:
    """La valeur brute du réglage `courriel_destinataires`."""
    p = s.get(Parametre, "courriel_destinataires")
    return (p.valeur if p is not None else "") or ""


def adresses(texte: str) -> tuple[list[str], list[str]]:
    """Les adresses lisibles et les illisibles d'une liste séparée par des virgules (E-15).

    La règle est celle de l'enregistrement du réglage (`services.reglages`, lot D1) : une
    adresse acceptée à la saisie l'est à l'envoi ; une valeur écrite autrement (reprise, base
    restaurée) est revérifiée ici.
    """
    morceaux = [x.strip() for x in re.split(r"[,;]", texte or "") if x.strip()]
    valides = [x for x in morceaux if ADRESSE_COURRIEL.fullmatch(x)]
    return valides, [x for x in morceaux if not ADRESSE_COURRIEL.fullmatch(x)]


def mettre_en_file(
    s: Session, genre: GenreCourriel, *, cle: str, destinataires: list[str], sujet: str, corps: str
) -> int | None:
    """Met un courriel en file ; une clé déjà vue n'est pas remise (`None`)."""
    requete = (
        insert(Courriel)
        .values(
            genre=genre,
            cle=cle[: L.CLE_COURRIEL],
            destinataires=", ".join(destinataires)[: L.DESTINATAIRES],
            sujet=sujet[: L.SUJET],
            corps=corps,
            statut=StatutCourriel.en_attente,
            essais=0,
            erreur="",
            cree_le=horloge.maintenant(),
        )
        .on_conflict_do_nothing(index_elements=["cle"])
        .returning(Courriel.id)
    )
    ident = s.execute(requete).scalar()
    return int(ident) if ident is not None else None


def prochain_essai(c: Courriel) -> datetime:
    """Quand le prochain essai est permis : tout de suite, puis 15 min × 2ⁿ après le dernier."""
    if c.essais == 0 or c.dernier_essai_le is None:
        return c.cree_le
    return c.dernier_essai_le + ECART_DE_BASE * (1 << (c.essais - 1))


def _message(c: Courriel) -> EmailMessage:
    """Le message à envoyer (texte brut)."""
    r = reglages()
    message = EmailMessage()
    message["Subject"] = c.sujet
    message["From"] = r.expediteur
    message["To"] = c.destinataires
    message.set_content(c.corps)
    return message


def envoyer_smtp(message: EmailMessage) -> None:
    """Envoie un message par le serveur réglé (STARTTLS ; identification si réglée)."""
    r = reglages()
    with smtplib.SMTP(r.smtp_hote, r.smtp_port, timeout=DELAI_SMTP_S) as smtp:
        smtp.starttls()
        if r.smtp_utilisateur:
            smtp.login(r.smtp_utilisateur, r.smtp_mot_de_passe.get_secret_value())
        smtp.send_message(message)


def _essayer(s: Session, c: Courriel) -> bool:
    """Un essai d'envoi ; rend vrai s'il est parti. L'échec est noté sur le courriel."""
    maintenant = horloge.maintenant()
    c.essais += 1
    c.dernier_essai_le = maintenant
    try:
        envoyer_smtp(_message(c))
    except (OSError, smtplib.SMTPException) as exc:
        c.erreur = f"{type(exc).__name__} : {exc}"[: L.ERREUR]
        if c.essais >= ESSAIS_MAX:
            c.statut = StatutCourriel.abandonne
        JOURNAL.warning("Courriel %s non envoyé (essai %s) : %s", c.cle, c.essais, exc)
        return False
    c.statut, c.envoye_le, c.erreur = StatutCourriel.envoye, maintenant, ""
    return True


@dataclass(frozen=True)
class Envoi:
    """Le bilan d'un passage sur la file."""

    envoyes: int
    echecs: int
    derniere_erreur: str


def envoyer_la_file() -> Envoi:
    """Envoie les courriels dus de la file, un par transaction (verrou de ligne, sans attente)."""
    if not configure():
        return Envoi(0, 0, "")
    envoyes = echecs = 0
    erreur = ""
    with fabrique()() as s:
        ids = list(
            s.scalars(
                select(Courriel.id)
                .where(Courriel.statut == StatutCourriel.en_attente)
                .order_by(Courriel.id)
            )
        )
    for ident in ids:
        with fabrique()() as s, s.begin():
            c = s.scalar(
                select(Courriel).where(Courriel.id == ident).with_for_update(skip_locked=True)
            )
            if c is None or c.statut != StatutCourriel.en_attente:
                continue
            if prochain_essai(c) > horloge.maintenant():
                continue
            if _essayer(s, c):
                envoyes += 1
            else:
                echecs += 1
                erreur = c.erreur
    return Envoi(envoyes, echecs, erreur)


def en_attente(s: Session) -> int:
    """Le nombre de courriels qui attendent d'être envoyés (`/api/sante`)."""
    requete = select(func.count()).where(Courriel.statut == StatutCourriel.en_attente)
    return int(s.scalar(requete) or 0)


@dataclass(frozen=True)
class PageCourriels:
    """Une page de la file, les plus récents d'abord (curseur : l'id)."""

    elements: list[Courriel]
    total: int
    suivant: int | None


def lister(s: Session, apres: int | None = None, limite: int = 500) -> PageCourriels:
    """La file des courriels (envoyés, en attente, abandonnés), du plus récent au plus ancien."""
    total = int(s.scalar(select(func.count()).select_from(Courriel)) or 0)
    requete = select(Courriel)
    if apres is not None:
        requete = requete.where(Courriel.id < apres)
    lignes = list(s.scalars(requete.order_by(Courriel.id.desc()).limit(limite + 1)))
    suivant = lignes[limite - 1].id if len(lignes) > limite else None
    return PageCourriels(lignes[:limite], total, suivant)
