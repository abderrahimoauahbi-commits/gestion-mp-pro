"""Notifications : la cloche de chacun (ARCHITECTURE T4, A10 ; MODELE-DONNEES § 3.1.9).

Une notification s'adresse à un **rôle** ou à **une personne** ; `cle` la dédoublonne (une
rupture d'une matière un jour donné ne sonne qu'une fois : `rupture:matiere:12:2026-10-08`).
Une notification `monetaire` n'est jamais montrée à l'alimentation ni à l'administrateur
(aucun prix ni montant chez eux, D5). Le lien est une adresse d'écran stable (`/commandes/12`).

Les domaines émettent par `notifier(...)` dans la transaction de leur geste ; la tâche
`alertes` (lot D10) aussi. Les lues de plus de 90 jours sont purgées (tâche `purges`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Notification, NotificationLecture
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.modeles.enums import Role, TonNotification
from gestion_mp_pro.services import horloge

VOIT_PRIX = frozenset({Role.direction, Role.achats})
"""Les rôles qui voient prix et montants (API-PRO § 0.4)."""

PURGE_LUES_JOURS = 90


@dataclass(frozen=True)
class Lecteur:
    """Celui qui lit sa cloche : son compte et son rôle."""

    id: int
    role: str


def notifier(
    s: Session,
    destinataire: Role | int,
    texte: str,
    *,
    lien: str = "",
    ton: TonNotification = TonNotification.info,
    objet: str = "",
    objet_id: int | None = None,
    cle: str | None = None,
    monetaire: bool = False,
) -> int | None:
    """Émet une notification pour un rôle (`Role`) ou une personne (id) ; rend son id.

    Une notification de même `cle` déjà émise n'est pas refaite (`None`).
    """
    role = destinataire if isinstance(destinataire, Role) else None
    personne = None if isinstance(destinataire, Role) else int(destinataire)
    requete = (
        insert(Notification)
        .values(
            cree_le=horloge.maintenant(),
            role=role,
            utilisateur_id=personne,
            texte=texte[: L.TEXTE_NOTIFICATION],
            lien=lien[: L.LIEN],
            ton=ton,
            objet=objet[: L.OBJET],
            objet_id=objet_id,
            cle=cle[: L.CLE_NOTIFICATION] if cle else None,
            monetaire=monetaire,
        )
        .on_conflict_do_nothing(index_elements=["cle"])
        .returning(Notification.id)
    )
    ident = s.execute(requete).scalar()
    return int(ident) if ident is not None else None


def _visibles(qui: Lecteur) -> ColumnElement[bool]:
    """Les notifications de son rôle ou à son nom ; sans montant hors direction et achats."""
    pour_lui = or_(Notification.role == qui.role, Notification.utilisateur_id == qui.id)
    if qui.role in VOIT_PRIX:
        return pour_lui
    return and_(pour_lui, Notification.monetaire.is_(False))


def _lue(qui: Lecteur) -> ColumnElement[bool]:
    """Vrai si la personne a lu la notification."""
    return exists().where(
        NotificationLecture.notification_id == Notification.id,
        NotificationLecture.utilisateur_id == qui.id,
    )


@dataclass(frozen=True)
class NotificationLue:
    """Une notification telle que la cloche la montre."""

    id: int
    texte: str
    lien: str
    ton: str
    quand: datetime
    lue: bool
    objet: str
    objet_id: int | None


@dataclass(frozen=True)
class Cloche:
    """Une page de la cloche, le total qui passe le filtre et le nombre de non lues."""

    elements: list[NotificationLue]
    total: int
    non_lues: int
    dernier_id: int | None


def lister(
    s: Session, qui: Lecteur, *, non_lues: bool = False, apres: int | None = None, limite: int = 50
) -> Cloche:
    """Les notifications de la personne, les plus récentes d'abord (curseur : l'id)."""
    filtre = _visibles(qui)
    if non_lues:
        filtre = and_(filtre, ~_lue(qui))
    total = int(s.scalar(select(func.count()).select_from(Notification).where(filtre)) or 0)
    compte = select(func.count()).select_from(Notification).where(_visibles(qui), ~_lue(qui))
    requete = select(Notification, _lue(qui).label("lue")).where(filtre)
    if apres is not None:
        requete = requete.where(Notification.id < apres)
    lignes = s.execute(requete.order_by(Notification.id.desc()).limit(limite + 1)).all()
    elements = [
        NotificationLue(n.id, n.texte, n.lien, n.ton, n.cree_le, bool(lue), n.objet, n.objet_id)
        for n, lue in lignes[:limite]
    ]
    suivant = elements[-1].id if len(lignes) > limite else None
    return Cloche(elements, total, int(s.scalar(compte) or 0), suivant)


def marquer_lue(s: Session, qui: Lecteur, ident: int) -> None:
    """Marque une notification lue (404 si elle n'est pas pour cette personne)."""
    visible = s.scalar(select(Notification.id).where(Notification.id == ident, _visibles(qui)))
    if visible is None:
        raise Refus.introuvable("Notification introuvable.")
    s.execute(
        insert(NotificationLecture)
        .values(notification_id=ident, utilisateur_id=qui.id, lue_le=horloge.maintenant())
        .on_conflict_do_nothing()
    )


def tout_marquer_lu(s: Session, qui: Lecteur) -> int:
    """Marque lues toutes ses notifications ; rend le nombre de notifications marquées."""
    a_lire = select(Notification.id).where(_visibles(qui), ~_lue(qui))
    ids = list(s.scalars(a_lire))
    if ids:
        maintenant = horloge.maintenant()
        valeurs = [
            {"notification_id": i, "utilisateur_id": qui.id, "lue_le": maintenant} for i in ids
        ]
        s.execute(insert(NotificationLecture).values(valeurs).on_conflict_do_nothing())
    return len(ids)


def purger(s: Session, jours: int = PURGE_LUES_JOURS) -> int:
    """Supprime les notifications lues depuis plus de `jours` jours (tâche `purges`)."""
    limite = horloge.maintenant() - timedelta(days=jours)
    vieilles = select(NotificationLecture.notification_id).where(
        NotificationLecture.lue_le < limite
    )
    resultat = s.execute(delete(Notification).where(Notification.id.in_(vieilles)))
    return int(getattr(resultat, "rowcount", 0) or 0)
