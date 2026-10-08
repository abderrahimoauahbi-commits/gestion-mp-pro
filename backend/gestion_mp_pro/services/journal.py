"""Lire le journal des actions et l'historique d'une fiche (routes 49–51 ; héritage K51, K52, F-09).

- Filtres exacts (personne, action, objet, `objet_id`), dates `du`/`au` (au inclus), et jusqu'à
  6 mots cherchés **sans accents** (F-09) dans le nom, l'action, l'objet, le numéro et la
  phrase ; `%` et `_` cherchés littéralement.
- Historique d'une fiche : lisible par qui peut lire la fiche (`LECTURE_HISTORIQUE`) ; les prix
  de `avant`/`apres` sont retirés par le filtre de la route pour les autres rôles.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles import Journal
from gestion_mp_pro.modeles.enums import ObjetJournal, Role
from gestion_mp_pro.services import horloge, recherche
from gestion_mp_pro.services.audit import historique
from gestion_mp_pro.services.comptes import message_refus

C = frozenset({Role.direction, Role.achats, Role.alimentation})
DA = frozenset({Role.direction, Role.achats})
DT = frozenset({Role.direction, Role.administrateur})

LECTURE_HISTORIQUE: dict[ObjetJournal, frozenset[str]] = {
    **dict.fromkeys(
        (ObjetJournal.utilisateur, ObjetJournal.appareil, ObjetJournal.sauvegarde),
        DT,
    ),
    **dict.fromkeys((ObjetJournal.reprise, ObjetJournal.systeme), DT),
    **dict.fromkeys((ObjetJournal.parametre, ObjetJournal.periode, ObjetJournal.devise), DA),
    **dict.fromkeys(
        (
            ObjetJournal.code_douanier,
            ObjetJournal.poste_frais,
            ObjetJournal.fournisseur,
            ObjetJournal.commande,
            ObjetJournal.reception,
            ObjetJournal.facture,
            ObjetJournal.dossier,
            ObjetJournal.dossier_frais,
            ObjetJournal.reclamation,
            ObjetJournal.piece_jointe,
        ),
        DA,
    ),
}
"""Qui lit l'historique de quelle fiche (le droit de lecture de la fiche, API-PRO route 51) ;
tout objet absent de la table est lisible par les trois rôles métier (matières, lots…)."""


def lecteurs_historique(objet: ObjetJournal | str) -> frozenset[str]:
    """Les rôles qui lisent l'historique d'une fiche de cet objet."""
    return LECTURE_HISTORIQUE.get(ObjetJournal(objet), C)


def historique_lisible(
    s: Session, role: str, objet: ObjetJournal | str, objet_id: int
) -> list[Journal]:
    """L'historique d'une fiche, si le rôle peut lire la fiche (403 sinon)."""
    lecteurs = lecteurs_historique(objet)
    if role not in lecteurs:
        raise Refus.droit(message_refus(lecteurs))
    return historique(s, objet, objet_id)


@dataclass(frozen=True)
class FiltreJournal:
    """Les filtres du journal des actions (héritage K51, plus `objet_id`)."""

    q: str = ""
    utilisateur: int | None = None
    action: str = ""
    objet: str = ""
    objet_id: int | None = None
    du: dt.date | None = None
    au: dt.date | None = None


def _requete_journal(f: FiltreJournal) -> Select[Journal]:
    """Le journal filtré : qui, quoi, sur quoi, quand, et des mots cherchés partout."""
    requete = select(Journal)
    if f.utilisateur is not None:
        requete = requete.where(Journal.utilisateur_id == f.utilisateur)
    if f.action:
        requete = requete.where(Journal.action == f.action)
    if f.objet:
        requete = requete.where(Journal.objet == f.objet)
    if f.objet_id is not None:
        requete = requete.where(Journal.objet_id == f.objet_id)
    if f.du is not None:
        requete = requete.where(Journal.quand >= _debut_du_jour(f.du))
    if f.au is not None:
        requete = requete.where(Journal.quand < _debut_du_jour(f.au + dt.timedelta(days=1)))
    for mot in recherche.mots(f.q):
        motif = f"%{recherche.echapper(mot)}%"
        requete = requete.where(
            or_(
                *(
                    recherche.sans_accents_sql(colonne).like(motif, escape="\\")
                    for colonne in (
                        Journal.utilisateur_nom,
                        Journal.action,
                        Journal.objet,
                        Journal.numero,
                        Journal.detail,
                    )
                )
            )
        )
    return requete


def _debut_du_jour(jour: dt.date) -> dt.datetime:
    """Minuit à l'heure de l'usine."""
    return dt.datetime.combine(jour, dt.time.min, tzinfo=horloge.FUSEAU)


@dataclass(frozen=True)
class PageJournal:
    """Une page du journal (les plus récentes d'abord) et le total qui passe les filtres."""

    lignes: list[Journal]
    total: int
    dernier_id: int | None


def lire_journal(
    s: Session, f: FiltreJournal, apres: int | None = None, limite: int = 500
) -> PageJournal:
    """Le journal filtré, du plus récent au plus ancien (curseur : l'id de la dernière ligne)."""
    if f.du is not None and f.au is not None and f.au < f.du:
        raise Refus.saisie(
            "La date de fin précède la date de début.",
            code="date_invalide",
            champs={"au": "avant « du »"},
        )
    requete = _requete_journal(f)
    total = int(s.scalar(select(func.count()).select_from(requete.subquery())) or 0)
    if apres is not None:
        requete = requete.where(Journal.id < apres)
    lignes: list[Journal] = list(s.scalars(requete.order_by(Journal.id.desc()).limit(limite + 1)))
    suivant = lignes[limite - 1].id if len(lignes) > limite else None
    return PageJournal(lignes[:limite], total, suivant)


@dataclass(frozen=True)
class ValeursJournal:
    """Ce que les filtres du journal proposent : les personnes, les gestes, les objets."""

    utilisateurs: list[tuple[int, str]]
    actions: list[str]
    objets: list[str]


def valeurs_journal(s: Session) -> ValeursJournal:
    """Valeurs distinctes non vides (héritage K52) ; une personne par id, son dernier nom."""
    personnes = s.execute(
        select(Journal.utilisateur_id, func.max(Journal.utilisateur_nom))
        .where(Journal.utilisateur_id.is_not(None))
        .group_by(Journal.utilisateur_id)
        .order_by(func.max(Journal.utilisateur_nom))
    ).all()
    actions = s.scalars(select(Journal.action).distinct().order_by(Journal.action))
    objets = s.scalars(select(Journal.objet).distinct().order_by(Journal.objet))
    return ValeursJournal(
        [(int(i or 0), str(n)) for i, n in personnes],
        [a for a in actions if a],
        [str(o) for o in objets if o],
    )
