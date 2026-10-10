"""Robustesse des entrées (lot V5, critère A13) : jamais de 500 sur un corps hostile.

`essais/robustesse.py` génère des corps depuis l'OpenAPI (types faux, bornes, chaînes vides,
unicode, nombres énormes, objets trop profonds) et tape chaque route d'écriture avec chaque rôle
permis. Le filet de `api/erreurs.py` doit rendre un refus propre (422/409/4xx), jamais une 500.

Hérité : test_defauts_f::test_une_contrainte_de_base_ne_donne_pas_de_500 (défaut F-08 de Gestion
MP, « IntegrityError/DataError non traités → 500 »).
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from api_pro import gabarit
from fabrique import *  # noqa: F403
from fabrique import CODES, compte, connecter
from fastapi import FastAPI

from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.securite.matrice import matrice

ESSAIS = Path(__file__).resolve().parents[1] / "essais"
sys.path.insert(0, str(ESSAIS))
import robustesse  # noqa: E402


def _clients(app: FastAPI) -> dict[str, object]:
    """Un client connecté par rôle, sur des comptes à soi."""
    clients: dict[str, object] = {}
    for role in Role:
        ident = f"robustesse-{role.value}-{uuid4().hex[:8]}"
        compte(role, identifiant=ident)
        clients[role.value] = connecter(app, ident, CODES[role])
    return clients


def _permis(app: FastAPI) -> dict[tuple[str, str], list[str]]:
    """(méthode, chemin) → rôles dont la matrice dit « ok »."""
    permis: dict[tuple[str, str], list[str]] = {}
    for ligne in matrice(app):
        roles = [r.value for r in Role if ligne.attendu(r.value) == "ok"]
        if roles:
            permis[(ligne.methode, ligne.chemin)] = roles
    return permis


def test_aucune_route_d_ecriture_ne_tombe_en_500(application: FastAPI) -> None:
    """Toute route d'écriture, tapée par corps hostiles et par rôle permis, refuse sans 500."""
    taper = robustesse.Taper(_clients(application))
    rapport = robustesse.campagne(taper, application.openapi(), _permis(application))
    assert rapport.routes > 0, "aucune route d'écriture trouvée"
    assert rapport.envois > rapport.routes, "la campagne n'a presque rien envoyé"
    assert rapport.cinq_cents == [], "\n".join(rapport.cinq_cents)


def test_le_generateur_couvre_les_corps_hostiles() -> None:
    """Le générateur produit les corps globaux et un corps par champ faussé du schéma."""
    schema = {
        "type": "object",
        "required": ["nom"],
        "properties": {"nom": {"type": "string"}, "poids": {"type": "number"}},
    }
    corps = list(robustesse.corps_hostiles(schema, {}))
    assert len(corps) >= len(robustesse.CORPS_GLOBAUX) + 4
    assert {} in corps and [] in corps


def test_le_generateur_resout_les_references() -> None:
    """Un `$ref` est déréférencé, et un schéma récursif ne boucle pas."""
    composants = {
        "Noeud": {
            "type": "object",
            "properties": {"enfant": {"$ref": "#/components/schemas/Noeud"}},
        }
    }
    corps = list(robustesse.corps_hostiles({"$ref": "#/components/schemas/Noeud"}, composants))
    assert len(corps) > len(robustesse.CORPS_GLOBAUX)


def test_gabarit_des_chemins_reste_coherent(application: FastAPI) -> None:
    """Chaque route d'écriture de l'OpenAPI a un gabarit connu de la matrice (garde-fou)."""
    de_la_matrice = {(x.methode, gabarit(x.chemin)) for x in matrice(application)}
    for route in robustesse.routes_ecriture(application.openapi()):
        assert (route.methode, gabarit(route.chemin)) in de_la_matrice
