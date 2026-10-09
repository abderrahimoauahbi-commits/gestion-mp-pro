"""Les besoins signalés par l'atelier (routes 221–223) : « il manque du rouge 2900 pour demain ».

Tout rôle métier signale (l'atelier d'abord, au téléphone) ; la direction et les achats
traitent, une fois : la réponse donnée à l'atelier, et qui l'a donnée, ne s'écrasent pas
(409). Signaler prévient la direction et les achats (cloche) ; traiter prévient l'auteur.
Chaque geste s'écrit au journal (« besoin signalé », « besoin traité »).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Matiere, Signalement, Utilisateur
from gestion_mp_pro.modeles.enums import ObjetJournal, Role, TonNotification, Urgence
from gestion_mp_pro.services import audit, horloge, notifications

EXTRAIT = 120
"""Le journal garde les 120 premiers caractères du texte."""
TRAITENT = (Role.direction, Role.achats)


@dataclass
class SignalementLu:
    """Un besoin signalé, avec les noms de qui l'a signalé et traité."""

    id: int
    quand: datetime
    par: str
    par_id: int | None
    matiere_id: int | None
    reference: str
    texte: str
    urgence: str
    traite: bool
    traite_par: str
    traite_le: datetime | None
    reponse: str


def _lus(s: Session, liste: list[Signalement]) -> list[SignalementLu]:
    ids = {x.par_id for x in liste} | {x.traite_par_id for x in liste}
    noms = dict(
        s.execute(
            select(Utilisateur.id, Utilisateur.nom).where(Utilisateur.id.in_(ids - {None}))
        ).all()
    )
    refs = dict(
        s.execute(
            select(Matiere.id, Matiere.reference).where(
                Matiere.id.in_({x.matiere_id for x in liste} - {None})
            )
        ).all()
    )
    return [
        SignalementLu(
            id=x.id,
            quand=x.quand,
            par=noms.get(x.par_id, "") if x.par_id else "",
            par_id=x.par_id,
            matiere_id=x.matiere_id,
            reference=refs.get(x.matiere_id, "") if x.matiere_id else "",
            texte=x.texte,
            urgence=str(x.urgence),
            traite=x.traite_le is not None,
            traite_par=noms.get(x.traite_par_id, "") if x.traite_par_id else "",
            traite_le=x.traite_le,
            reponse=x.reponse,
        )
        for x in liste
    ]


def lister(
    s: Session, a_traiter: bool | None, apres: int | None, limite: int, par_id: int | None = None
) -> tuple[list[SignalementLu], int]:
    """Route 221 : les besoins, le plus récent d'abord (`a_traiter` : vrai, ceux qui
    attendent ; faux, ceux traités ; absent, tous ; `par_id` : ceux d'un compte — « mes
    besoins » de l'atelier), paginés par id ; et leur nombre."""
    condition = [] if par_id is None else [Signalement.par_id == par_id]
    if a_traiter is not None:
        condition.append(
            Signalement.traite_le.is_(None) if a_traiter else Signalement.traite_le.is_not(None)
        )
    total = int(s.scalar(select(func.count()).select_from(Signalement).where(*condition)) or 0)
    requete = select(Signalement).where(*condition)
    if apres is not None:
        requete = requete.where(Signalement.id < apres)
    liste = list(s.scalars(requete.order_by(Signalement.id.desc()).limit(limite)))
    return _lus(s, liste), total


def signaler(
    s: Session, qui: audit.Qui, matiere_id: int | None, texte: str, urgence: Urgence
) -> SignalementLu:
    """Route 222 : un besoin signalé (journal ; cloche de la direction et des achats)."""
    if matiere_id is not None and s.get(Matiere, matiere_id) is None:
        raise Refus.introuvable(
            "Matière inconnue : choisir la matière dans la liste, ou n'en nommer aucune."
        )
    x = Signalement(par_id=qui.id, matiere_id=matiere_id, texte=texte, urgence=urgence)
    s.add(x)
    s.flush()
    audit.journal(s, qui, "besoin signalé", ObjetJournal.signalement, x.id, detail=texte[:EXTRAIT])
    urgent = urgence == Urgence.urgente
    for role in TRAITENT:
        notifications.notifier(
            s,
            role,
            f"Besoin signalé par {qui.nom} : « {texte[:EXTRAIT]} »",
            lien=f"/accueil?signalement={x.id}",
            ton=TonNotification.alerte if urgent else TonNotification.info,
            objet="signalement",
            objet_id=x.id,
        )
    return _lus(s, [x])[0]


def traiter(s: Session, qui: audit.Qui, ident: int, reponse: str) -> SignalementLu:
    """Route 223 : le besoin traité, une fois (409 sinon) ; l'auteur est prévenu."""
    x = s.scalars(select(Signalement).where(Signalement.id == ident).with_for_update()).first()
    if x is None:
        raise Refus.introuvable("Signalement introuvable.")
    if x.traite_le is not None:
        par = s.get(Utilisateur, x.traite_par_id) if x.traite_par_id else None
        quand = x.traite_le.astimezone(horloge.FUSEAU)
        raise Refus.etat(
            f"Ce besoin a déjà été traité par {par.nom if par else 'quelqu’un'} le "
            f"{quand:%d/%m/%Y à %H:%M}."
        )
    x.traite_par_id, x.traite_le, x.reponse = qui.id, horloge.maintenant(), reponse
    s.flush()
    audit.journal(s, qui, "besoin traité", ObjetJournal.signalement, x.id, detail=reponse[:EXTRAIT])
    auteur = s.get(Utilisateur, x.par_id) if x.par_id is not None else None
    if auteur is not None and auteur.id != qui.id:
        lien = "/atelier" if auteur.role == Role.alimentation else f"/accueil?signalement={x.id}"
        notifications.notifier(
            s,
            auteur.id,
            f"Votre besoin « {x.texte[:EXTRAIT]} » est traité : {reponse or 'vu'}.",
            lien=lien,
            ton=TonNotification.succes,
            objet="signalement",
            objet_id=x.id,
        )
    return _lus(s, [x])[0]
