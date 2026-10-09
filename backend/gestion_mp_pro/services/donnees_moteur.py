"""Le chargeur du moteur : la base PRO traduite en `Donnees`, gardée en cache tant que rien
n'a changé (ARCHITECTURE § 7, CALCULS A § 4 ; `gestion_mp/depot.py`).

- `charger(s)` : l'instantané complet (référentiels, plan, journal, documents, soldes tenus),
  lu en requêtes groupées — leur nombre ne dépend pas de la taille de la base.
- `charger_au(s, jour)` : les données telles qu'elles étaient le soir du `jour`
  (`calcul.a_la_date`, avec la date du jour de l'horloge de l'usine).
- **Cache** par processus, clé = `signature(s)`, lue **en base** à chaque appel : le jour,
  `max(journal.id)`, `max(mouvement.id)`, `max(parametre.modifie_le)`, `Σ parametre.version`,
  `Σ devise.version`, `count(mouvement)`, `Σ solde.quantite`. Tout geste écrit au journal (S2),
  tout mouvement change le journal du stock, tout réglage et tout cours leur `version` (même à
  horloge figée, ou deux écritures dans la même microseconde), et un solde touché hors du
  chemin d'écriture change la somme : un chiffre n'est jamais périmé, même avec plusieurs
  processus (la signature n'est pas en mémoire). Les identifiants ne se réutilisent jamais :
  une transaction annulée ne peut pas laisser en cache une signature qui reviendrait.
- **Ne jamais modifier en place** des `Donnees` rendues ici, ni ce que le moteur en tire : elles
  sont partagées entre les requêtes (`dataclasses.replace` pour une variante).
"""

from __future__ import annotations

import threading
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.a_la_date import a_la_date
from gestion_mp_pro.modeles import Devise, Journal, Mouvement, Parametre, Solde
from gestion_mp_pro.services import horloge
from gestion_mp_pro.services.chargeur import achats, journal, production, qualites, receptions
from gestion_mp_pro.services.chargeur import referentiels as ref
from gestion_mp_pro.services.chargeur.achats import (
    en_quarantaine_par_ligne,
    recu_par_ligne,
    retours_par_ligne_reception,
)
from gestion_mp_pro.services.chargeur.contexte import lire_noms
from gestion_mp_pro.services.chargeur.referentiels import parametres, poids_bobine_mesures

__all__ = [
    "charger",
    "charger_au",
    "en_quarantaine_par_ligne",
    "invalider",
    "lire",
    "parametres",
    "poids_bobine_mesures",
    "recu_par_ligne",
    "retours_par_ligne_reception",
    "signature",
]

Signature = tuple[Any, ...]
"""Ce qui change à la moindre écriture : la clé du cache."""

_cache: dict[bool, tuple[Signature, c.Donnees]] = {}
_verrou = threading.Lock()


def signature(s: Session) -> Signature:
    """La signature lue en base (une requête), précédée du jour de l'usine."""
    ligne = s.execute(
        select(
            select(func.max(Journal.id)).scalar_subquery(),
            select(func.max(Mouvement.id)).scalar_subquery(),
            select(func.max(Parametre.modifie_le)).scalar_subquery(),
            select(func.sum(Parametre.version)).scalar_subquery(),
            select(func.sum(Devise.version)).scalar_subquery(),
            select(func.count()).select_from(Mouvement).scalar_subquery(),
            select(func.sum(Solde.quantite)).scalar_subquery(),
        )
    ).one()
    return (horloge.aujourd_hui(), *ligne)


def lire(s: Session, avec_journal: bool = True) -> c.Donnees:
    """Les données du moteur relues de la base, sans cache. `avec_journal=False` : ni journal
    ni soldes (référentiels, plan, documents seulement — plus rapide)."""
    noms = lire_noms(s)
    bons = achats.commandes(s, noms)
    recus = receptions.receptions(s, noms, bons.numeros, bons.commande_de_ligne)
    q = qualites.qualites(s, noms)
    return c.Donnees(
        parametres=ref.parametres(s),
        fournisseurs=ref.fournisseurs(s),
        articles=ref.articles(s, noms),
        qualites=q.qualites,
        recettes=q.recettes,
        plan=q.plan,
        mouvements=journal.journal(s, noms) if avec_journal else [],
        commandes=bons.commandes,
        historique_prix=recus.prix,
        receptions=recus.receptions,
        magasins=ref.magasins(s),
        metiers=ref.metiers(s, noms),
        dossiers_import=production.dossiers(s, noms),
        ordres=production.ordres(s, noms),
        versions_plan=q.versions_plan,
        versions_recette=q.versions_recette,
        soldes=journal.soldes(s, noms) if avec_journal else None,
    )


def charger(s: Session, avec_journal: bool = True) -> c.Donnees:
    """Les données du moteur, relues seulement si la signature a changé depuis."""
    cle = signature(s)
    with _verrou:
        garde = _cache.get(avec_journal)
        if garde is not None and garde[0] == cle:
            return garde[1]
        donnees = lire(s, avec_journal)
        _cache[avec_journal] = (cle, donnees)
        return donnees


def charger_au(s: Session, jour: date, avec_journal: bool = True) -> c.Donnees:
    """Les données telles qu'elles étaient le soir du `jour` : le journal, les réceptions, les
    commandes, les prix et les ordres tronqués ; catalogue, réglages et dossiers d'aujourd'hui ;
    le montage des métiers ne compte pas à une date passée (`calcul.a_la_date`)."""
    return a_la_date(charger(s, avec_journal), jour, aujourdhui=horloge.aujourd_hui())


def invalider() -> None:
    """Oublie le cache de ce processus (essais, reprise : la signature suffit d'ordinaire)."""
    with _verrou:
        _cache.clear()
