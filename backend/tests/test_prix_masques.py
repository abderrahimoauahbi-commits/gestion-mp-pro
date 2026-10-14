"""Aucun prix ni montant chez l'alimentation (ni chez l'administrateur) — lot S2, nourri par les D.

Héritage D5 ; API-PRO § 0.4 ; ARCHITECTURE § 5.3. Trois niveaux de preuve :
1. `sans_prix` : chaque motif de `CLES_MONETAIRES`, à toute profondeur, dans les listes ;
2. `RouteSansPrix` sur des routes d'épreuve qui rendent les réponses de Gestion MP (stock,
   mouvements, lots, opérations, inventaires, nomenclature, matières, qualités, métiers) ;
3. le **balayage** de toutes les routes GET servies, en rôle alimentation et administrateur :
   aucune clé monétaire n'y porte de valeur (chaque lot D ajoute ses données au jeu).
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

import pytest
from api_pro import route
from fabrique import *  # noqa: F403
from fabrique import client_de
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import insert

from gestion_mp_pro.api.communs import Sortie
from gestion_mp_pro.db import fabrique as sessions_db
from gestion_mp_pro.main import creer_application
from gestion_mp_pro.modeles import Journal
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.securite import (
    CLES_MONETAIRES,
    TOUS,
    C,
    RouteSansPrix,
    droit,
    est_monetaire,
    sans_prix,
)
from gestion_mp_pro.securite.matrice import matrice, routes_api
from gestion_mp_pro.securite.prix import cles_exemptees

MONETAIRES = [
    "prix",
    "prix_kg",
    "prix_unite",
    "montant_a_commander_mad",
    "valeur_mad",
    "valeur_conso_annuelle",
    "cout_m2_mad",
    "cmup_mad",
    "budget",
    "cours",
    "cours_le",
    "taux_du_jour",
    "taux_droits",
    "economie_annuelle",
    "revient_kg",
    "tva_attendue",
    "droits_douane",
    "frais_reels",
    "devise_prix",
    "ecart_valeur_mad",
]
NEUTRES = [
    "quantite",
    "reference",
    "designation",
    "devise",
    "taux_perte",
    "stock_machine",
    "lot",
    "kg",
]

GMP = {
    "stock": [
        {
            "reference": "F5 POIL",
            "stock": 560.0,
            "prix_kg": 32.0,
            "prix_unite": 3.2,
            "montant_a_commander_mad": 12800.0,
            "valeur_conso_annuelle_mad": 9000.0,
            "valeur_machine_mad": 128.0,
            "quantite_a_commander": 400.0,
        }
    ],
    "mouvements": {
        "elements": [
            {
                "lot": "F5-P1",
                "quantite": 600.0,
                "prix": 3.2,
                "cours": 10.0,
                "cout_mad": 32.0,
                "valeur_mad": 19200.0,
            }
        ],
        "total": 1,
    },
    "lot": {
        "numero": "F5-P1",
        "mouvements": [{"quantite": -40.0, "prix": 3.2, "valeur_mad": -1280.0}],
    },
    "operations": [{"type": "ouverture", "lignes": [{"quantite": 600.0, "prix": 3.2}]}],
    "inventaire": {
        "ecart_valeur_mad": -640.0,
        "ecart_valeur_absolue_mad": 640.0,
        "lignes": [
            {"theorique": 300.0, "compte": 280.0, "cmup_mad": 15.0, "valeur_ecart_mad": -300.0}
        ],
    },
    "nomenclature": [{"reference": "A2 POIL", "prix": 2.5, "prix_kg": 2.5, "cout_m2_mad": 26.89}],
    "matieres": [{"reference": "A2 POIL", "prix": 2.5, "prix_kg": 25.0, "minimum_commande": 500}],
    "qualites": [
        {
            "code": "F5Q",
            "cout_m2_mad": 26.89,
            "recette": [
                {"reference": "F5 POIL", "prix_kg": 32.0, "prix": 3.2, "cout_m2_mad": 20.0}
            ],
        }
    ],
    "metiers": [
        {
            "code": "F5M",
            "valeur_mad": 128.0,
            "fils": [{"reference": "F5 POIL", "valeur_mad": 128.0}],
        }
    ],
}
"""Les réponses de Gestion MP masquées route par route (REGLES B.3.2, M1–M10)."""


def fuites(donnees: Any, chemin: str = "", exemptees: frozenset[str] = frozenset()) -> list[str]:
    """Les clés monétaires qui portent une valeur, à toute profondeur (hors clés exemptées)."""
    trouve: list[str] = []
    if isinstance(donnees, dict):
        for cle, valeur in donnees.items():
            if (
                est_monetaire(str(cle))
                and cle not in exemptees
                and valeur not in (None, "", [], {})
            ):
                trouve.append(f"{chemin}.{cle}")
            trouve += fuites(valeur, f"{chemin}.{cle}", exemptees)
    elif isinstance(donnees, list):
        for valeur in donnees:
            trouve += fuites(valeur, f"{chemin}[]", exemptees)
    return trouve


def test_chaque_motif_est_monetaire() -> None:
    assert all(est_monetaire(c) for c in MONETAIRES)
    assert not any(est_monetaire(c) for c in NEUTRES)
    for motif in CLES_MONETAIRES:
        exemple = motif.replace("*", "x")
        assert est_monetaire(exemple), motif


def test_sans_prix_a_toute_profondeur() -> None:
    donnees = {
        "prix": 1.0,
        "lignes": [{"quantite": 2.0, "valeur_mad": 3.0, "sous": [{"cout_m2": 4.0}]}],
        "niveau": {"plus": {"plus": {"cmup": 5.0, "nom": "x"}}},
        "liste": [[{"budget_annuel": 6.0}]],
        "droits": ["approuver"],
    }
    assert sans_prix(donnees) == {
        "prix": None,
        "lignes": [{"quantite": 2.0, "valeur_mad": None, "sous": [{"cout_m2": None}]}],
        "niveau": {"plus": {"plus": {"cmup": None, "nom": "x"}}},
        "liste": [[{"budget_annuel": None}]],
        "droits": None,
    }
    assert sans_prix(donnees, frozenset({"droits"}))["droits"] == ["approuver"]  # type: ignore[index]
    assert donnees["prix"] == 1.0  # l'original n'est pas touché


class AvecDroits(Sortie):
    """Un schéma qui exempte une clé qui ressemble à un prix."""

    cles_non_monetaires: ClassVar[frozenset[str]] = frozenset({"droits"})

    droits: list[str]
    prix: float


def _epreuve() -> APIRouter:
    routeur = APIRouter(route_class=RouteSansPrix)
    for nom, corps in GMP.items():
        routeur.add_api_route(f"/epreuve-prix/{nom}", lambda c=corps: c, dependencies=[droit(*C)])
    routeur.add_api_route(
        "/epreuve-prix/tous", lambda: GMP["matieres"], dependencies=[droit(*TOUS)]
    )
    routeur.add_api_route(
        "/epreuve-prix/exempte",
        lambda: AvecDroits(droits=["approuver"], prix=2.5),
        response_model=AvecDroits,
        dependencies=[droit(*C)],
    )
    return routeur


@pytest.fixture(scope="module")
def app_epreuve() -> FastAPI:
    return creer_application(routeurs_en_plus=[_epreuve()])


def test_les_reponses_de_gestion_mp_sont_masquees(app_epreuve: FastAPI) -> None:
    """Hérité : test_stock_atelier::test_alimentation_ne_voit_aucun_prix (stock, mouvements,
    lots, opérations) ; test_referentiels_complets::test_l_alimentation_ne_voit_aucun_prix
    (matières, qualités) ;
    test_audit2_pilotage::test_la_nomenclature_ne_donne_aucun_prix_a_l_alimentation ;
    test_valorisation (valeur d'inventaire masquée)."""
    alimentation, achats = (
        client_de(app_epreuve, Role.alimentation),
        client_de(app_epreuve, Role.achats),
    )
    for nom, corps in GMP.items():
        lu = alimentation.get(f"/api/epreuve-prix/{nom}")
        assert lu.status_code == 200 and fuites(lu.json()) == [], nom
        assert achats.get(f"/api/epreuve-prix/{nom}").json() == corps, nom
    assert alimentation.get("/api/epreuve-prix/stock").json()[0]["stock"] == 560.0
    assert alimentation.get("/api/epreuve-prix/nomenclature").json()[0]["reference"] == "A2 POIL"
    admin = client_de(app_epreuve, Role.administrateur)
    assert fuites(admin.get("/api/epreuve-prix/tous").json()) == []
    assert (
        client_de(app_epreuve, Role.direction).get("/api/epreuve-prix/tous").json()
        == GMP["matieres"]
    )
    exempte = alimentation.get("/api/epreuve-prix/exempte").json()
    assert exempte == {"droits": ["approuver"], "prix": None}


def test_alimentation_ne_lit_ni_parametres_ni_devises() -> None:
    """Hérité : test_defauts_f::test_alimentation_ne_lit_ni_parametres_ni_devises (T9)."""
    for chemin in ("/parametres", "/devises", "/devises/{code}/cours"):
        entree = route("GET", chemin)
        assert entree.roles is not None
        assert Role.alimentation not in entree.roles and Role.achats in entree.roles


def _jeu_de_prix() -> dict[str, str]:
    """Des données qui portent des prix, pour les routes d'S2 (les lots D ajoutent les leurs)."""
    with sessions_db()() as s, s.begin():
        ident = s.execute(
            insert(Journal)
            .values(
                action="modification",
                objet="matiere",
                objet_id=987654,
                avant={"prix": 2.5, "cmup_mad": 25.0},
                apres={"prix": 3.0, "cmup_mad": 30.0},
            )
            .returning(Journal.id)
        ).scalar_one()
    return {"objet": "matiere", "ident": "987654", "id": str(ident), "code": "USD", "q": "poil"}


def _url(chemin: str, valeurs: dict[str, str]) -> str:
    return re.sub(
        r"\{(\w+)\}", lambda g: valeurs.get(g.group(1), "999999"), chemin.removeprefix("/api")
    )


def balayer(app: FastAPI, client: TestClient, valeurs: dict[str, str]) -> dict[str, list[str]]:
    """Chaque route GET servie, lue par ce client : les clés monétaires qui portent une valeur."""
    vu: dict[str, list[str]] = {}
    exemptions = {
        chemin: cles_exemptees(r.response_model)
        for chemin, r in routes_api(app)
        if "GET" in r.methods
    }
    for x in matrice(app):
        if x.methode != "GET":
            continue
        url = (
            "/api"
            + _url(x.chemin, valeurs)
            + ("?q=poil" if x.chemin.endswith("/recherche") else "")
        )
        r = client.get(url)
        assert r.status_code < 500, url
        if r.status_code == 200 and r.headers.get("content-type", "").startswith(
            "application/json"
        ):
            vu[url] = fuites(r.json(), exemptees=exemptions[x.chemin])
    return vu


def test_alimentation_ne_recoit_aucun_montant(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_alimentation_ne_recoit_aucun_montant (F-05, balayage)."""
    valeurs = _jeu_de_prix()
    for role in (Role.alimentation, Role.administrateur):
        lu = balayer(application, client_de(application, role), valeurs)
        assert len(lu) >= 8
        assert {url: x for url, x in lu.items() if x} == {}, role
    vu = balayer(application, client_de(application, Role.achats), valeurs)
    assert vu["/api/historique/matiere/987654"], "l'essai ne voit pas les prix quand ils sont là"
