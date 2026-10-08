"""Sécurité : qui est là, ce qu'il peut faire, ce qu'il peut voir (ARCHITECTURE § 5).

- `acteur_de_la_requete` : cookie de session → `Acteur` (crochet de `api.dependances.acteur`) ;
- `droit(*roles)` : la garde de chaque route (interdit par défaut, aucun passe-droit implicite) ;
  `exiger(qui, geste)` : les droits fins ;
- `RouteSansPrix`, `sans_prix`, `CLES_MONETAIRES` : aucun prix hors direction et achats ;
- `matrice(app)` : la matrice route × rôle, `python -m gestion_mp_pro.securite matrice` ;
- `journal`, `notifier` : la trace d'un geste et la cloche (services `audit`, `notifications`).

Paquet plutôt que module unique : le plafond de 400 lignes par fichier (décision S2).
"""

from __future__ import annotations

from gestion_mp_pro.securite.acteurs import (
    QuiDep,
    acteur_de_la_requete,
    effacer_cookie_session,
    poser_cookie_appareil,
    poser_cookie_session,
    poste_de,
    poste_local,
)
from gestion_mp_pro.securite.droits import (
    GESTES,
    TOUS,
    A,
    C,
    D,
    L,
    T,
    declarer_geste,
    droit,
    exiger,
    gestes_de,
    message_refus,
    peut,
)
from gestion_mp_pro.securite.matrice import PUBLIQUES, matrice
from gestion_mp_pro.securite.prix import (
    CLES_MONETAIRES,
    VOIT_PRIX,
    RouteSansPrix,
    est_monetaire,
    sans_prix,
)
from gestion_mp_pro.services.audit import journal
from gestion_mp_pro.services.comptes import Acteur
from gestion_mp_pro.services.notifications import notifier

__all__ = [
    "CLES_MONETAIRES",
    "GESTES",
    "PUBLIQUES",
    "QuiDep",
    "TOUS",
    "VOIT_PRIX",
    "A",
    "Acteur",
    "C",
    "D",
    "L",
    "RouteSansPrix",
    "T",
    "acteur_de_la_requete",
    "declarer_geste",
    "droit",
    "effacer_cookie_session",
    "est_monetaire",
    "exiger",
    "gestes_de",
    "journal",
    "matrice",
    "message_refus",
    "notifier",
    "peut",
    "poser_cookie_appareil",
    "poser_cookie_session",
    "poste_de",
    "poste_local",
    "sans_prix",
]
