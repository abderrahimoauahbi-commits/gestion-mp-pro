"""L'état partagé des tâches de fond (table `tache_execution`, MODELE-DONNEES § 3.1.11).

Gestion MP le gardait en mémoire du processus (faux à plusieurs processus, perdu au
redémarrage) ; PRO l'écrit en base : `/api/sante`, l'écran et l'alerte de la direction lisent
le même état, quel que soit le processus qui porte les tâches. L'écriture se fait dans une
transaction à elle : l'échec d'une tâche (qui annule la sienne) se note quand même.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import TacheExecution
from gestion_mp_pro.modeles import longueurs as L
from gestion_mp_pro.services import horloge

TACHES = ("sauvegarde", "photo_indicateurs", "courriel", "notifications", "purges")
"""Les tâches de la boucle, dans l'ordre de passage (noms de MODELE-DONNEES § 3.1.11)."""

RESTAURATION = "restauration"
"""L'état de la dernière restauration (écrit dans la base restaurée, ou laissée intacte)."""


@lru_cache(maxsize=1)
def moteur_des_verrous() -> Engine:
    """Un moteur sans réserve de connexions, pour les connexions qui **tiennent** un verrou de
    session (porteur des tâches, restauration) : ni prêtées, ni fermées par `moteur().dispose()`."""
    r = reglages()
    return create_engine(
        r.base, poolclass=NullPool, connect_args={"options": f"-c timezone={r.fuseau}"}
    )


@dataclass(frozen=True)
class EtatTache:
    """L'état d'une tâche, tel que l'écran et la surveillance le lisent."""

    nom: str
    dernier_essai_le: datetime | None
    dernier_succes_le: datetime | None
    erreur: str
    duree_ms: int

    @property
    def en_echec(self) -> bool:
        """Le dernier essai a échoué."""
        return bool(self.erreur)


def lire(s: Session, nom: str) -> EtatTache | None:
    """L'état d'une tâche, ou `None` si elle n'a jamais tourné sur cette base."""
    t = s.get(TacheExecution, nom)
    if t is None:
        return None
    return EtatTache(t.nom, t.dernier_essai_le, t.dernier_succes_le, t.erreur, t.duree_ms)


def lister(s: Session) -> list[EtatTache]:
    """Toutes les tâches connues, dans l'ordre de la boucle (puis les autres)."""
    rang = {nom: i for i, nom in enumerate((*TACHES, RESTAURATION))}
    lignes = s.scalars(select(TacheExecution)).all()
    etats = [
        EtatTache(t.nom, t.dernier_essai_le, t.dernier_succes_le, t.erreur, t.duree_ms)
        for t in lignes
    ]
    return sorted(etats, key=lambda e: (rang.get(e.nom, len(rang)), e.nom))


def noter_dans(s: Session, nom: str, debut: datetime, erreur: str = "", duree_ms: int = 0) -> None:
    """Note un passage dans la session donnée (succès si `erreur` est vide)."""
    valeurs: dict[str, object] = {
        "nom": nom[: L.NOM_TACHE],
        "dernier_essai_le": debut,
        "erreur": erreur[: L.ERREUR],
        "duree_ms": max(0, duree_ms),
    }
    if not erreur:
        valeurs["dernier_succes_le"] = debut
    requete = insert(TacheExecution).values(**valeurs)
    mise_a_jour = {k: v for k, v in valeurs.items() if k != "nom"}
    s.execute(requete.on_conflict_do_update(index_elements=["nom"], set_=mise_a_jour))


def noter(nom: str, debut: datetime, erreur: str = "", duree_ms: int = 0) -> None:
    """Note un passage dans une transaction à lui."""
    with fabrique()() as s, s.begin():
        noter_dans(s, nom, debut, erreur, duree_ms)


def reussie_le(s: Session, nom: str, jour: date) -> bool:
    """La tâche a-t-elle réussi ce jour-là (tâches quotidiennes) ?"""
    e = lire(s, nom)
    if e is None or e.dernier_succes_le is None:
        return False
    return e.dernier_succes_le.astimezone(horloge.FUSEAU).date() == jour


def resume(e: EtatTache | None) -> str:
    """Une phrase courte pour `/api/sante` : « ok », « échec : … », « jamais »."""
    if e is None or e.dernier_essai_le is None:
        return "jamais"
    return f"échec : {e.erreur}" if e.erreur else "ok"


def tous(s: Session) -> list[EtatTache]:
    """Les tâches de la boucle (celles qui n'ont jamais tourné comprises), puis les autres."""
    connues = {e.nom: e for e in lister(s)}
    vides = {nom: EtatTache(nom, None, None, "", 0) for nom in TACHES}
    return [
        *({**vides, **connues}[nom] for nom in TACHES),
        *(e for e in connues.values() if e.nom not in TACHES),
    ]
