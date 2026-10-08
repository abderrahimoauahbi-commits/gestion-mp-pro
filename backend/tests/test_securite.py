"""Sécurité (lot S2) : gardes `droit()`, messages de refus, droits fins, périmètre de chaque rôle.

Les preuves héritées sur des routes d'autres lots se vérifient sur le catalogue API-PRO (la
garde promise) **et**, dès que la route est servie, par l'appel réel (`_refuse`).
"""

from __future__ import annotations

import logging

import pytest
from api_pro import gabarit, route
from conftest import ENTETE_ECRAN
from fabrique import *  # noqa: F403
from fabrique import client_de
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.securite import (
    GESTES,
    declarer_geste,
    droit,
    exiger,
    gestes_de,
    message_refus,
    peut,
)
from gestion_mp_pro.securite.matrice import matrice
from gestion_mp_pro.services.comptes import Acteur

D, A, L, T = Role.direction, Role.achats, Role.alimentation, Role.administrateur


def _servies(app: FastAPI) -> set[tuple[str, str]]:

    return {(x.methode, gabarit(x.chemin)) for x in matrice(app)}


def _refuse(app: FastAPI, role: Role | None, methode: str, chemin: str) -> None:
    """Le catalogue refuse ce rôle ; si la route est servie, l'appel réel le refuse aussi."""
    entree = route(methode, chemin)
    attendu = 401 if role is None else 403
    if role is None:
        assert not entree.publique, chemin
    else:
        assert entree.roles is not None and role not in entree.roles, f"{role} {chemin}"

    if (methode, gabarit(chemin)) in _servies(app):
        client = TestClient(app, headers=ENTETE_ECRAN) if role is None else client_de(app, role)
        url = chemin.replace("{id}", "999999")
        r = client.request(methode, f"/api{url}", **({} if methode == "GET" else {"json": {}}))
        assert r.status_code == attendu, f"{role} {methode} {chemin} : {r.status_code}"


def _permis(role: Role, methode: str, chemin: str) -> None:
    entree = route(methode, chemin)
    assert entree.roles is not None and role in entree.roles, f"{role} {chemin}"


def test_message_de_refus_mot_pour_mot() -> None:
    """Hérité : KR14 « Cette action est réservée à : {permis}. »."""
    assert message_refus({D}) == "Cette action est réservée à : la direction."
    assert message_refus({D, A}) == "Cette action est réservée à : responsable achats."
    assert message_refus({D, A, L}) == (
        "Cette action est réservée à : responsable achats, responsable alimentation machines."
    )
    assert message_refus({D, L}) == (
        "Cette action est réservée à : responsable alimentation machines."
    )
    assert message_refus({D, T}) == (
        "Cette action est réservée à : la direction, l'administrateur technique."
    )


def test_la_garde_porte_ses_roles_et_aucun_passe_droit() -> None:
    """D3 : `.roles` lu par la matrice ; la direction n'est pas permise d'office."""
    garde = droit(A).dependency
    assert garde is not None and garde.roles == frozenset({A})
    qui = Acteur(1, "direction", "Direction", D)
    with pytest.raises(Refus) as refus:
        garde(qui)
    assert (refus.value.http, refus.value.detail) == (
        403,
        "Cette action est réservée à : responsable achats.",
    )
    assert garde(Acteur(2, "achats", "Achats", A)).role == A
    with pytest.raises(ValueError):
        droit()


def test_droits_fins() -> None:
    """ARCHITECTURE § 5.2 : libération D, A ; mise en quarantaine D, A, L ; approbation D."""
    alim = Acteur(3, "alim", "Alim", L)
    assert peut(alim, "mettre_en_quarantaine") and not peut(alim, "liberer_quarantaine")
    with pytest.raises(Refus) as refus:
        exiger(alim, "liberer_quarantaine")
    assert refus.value.detail == "Cette action est réservée à : responsable achats."
    assert gestes_de(T) == ["gerer_comptes"]
    declarer_geste("essai_s2", D)
    try:
        assert "essai_s2" in gestes_de(D) and "essai_s2" not in gestes_de(A)
    finally:
        GESTES.pop("essai_s2")


def test_une_ecriture_sans_entete_est_refusee(application: FastAPI, direction: TestClient) -> None:
    """Hérité : test_parcours::test_une_ecriture_sans_entete_est_refusee (K80)."""
    sans = TestClient(application, cookies=dict(direction.cookies))
    r = sans.post("/api/utilisateurs", json={"identifiant": "pirate", "nom": "Pirate"})
    assert (r.status_code, r.json()["code"]) == (403, "entete_absente")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert sans.get("/api/moi").status_code == 200


def test_chacun_a_sa_place(application: FastAPI) -> None:
    """Hérité : test_parcours::test_chacun_a_sa_place (périmètre de chaque rôle)."""
    for methode, chemin in (
        ("POST", "/matieres"),
        ("POST", "/commandes"),
        ("GET", "/utilisateurs"),
        ("PUT", "/parametres"),
    ):
        _refuse(application, L, methode, chemin)
    for methode, chemin in (
        ("GET", "/utilisateurs"),
        ("PUT", "/parametres"),
        ("PUT", "/qualites/{id}"),
        ("POST", "/ordres/{id}/valider"),
        ("GET", "/journal"),
    ):
        _refuse(application, A, methode, chemin)
    _permis(L, "POST", "/ordres/{id}/valider")


def test_l_atelier_ne_lit_pas_le_pilotage_des_achats(application: FastAPI) -> None:
    """Hérité : test_parcours::test_l_atelier_ne_lit_pas_le_pilotage_des_achats."""
    for chemin in (
        "/cockpit",
        "/plan-achat",
        "/valorisation",
        "/prix/matrice",
        "/prix/historique",
        "/opportunites",
        "/controles",
        "/fournisseurs/performance",
        "/receptions/pesees",
        "/analyse/revient",
        "/export/pilotage",
        "/controles/soldes",
    ):
        _refuse(application, L, "GET", chemin)
    for chemin in ("/stock", "/lots", "/ordres", "/production/plan"):
        _permis(L, "GET", chemin)


def test_l_atelier_ne_lit_ni_commandes_ni_receptions(application: FastAPI) -> None:
    """Hérité : test_achats::test_l_atelier_ne_lit_ni_commandes_ni_receptions."""
    for chemin in (
        "/commandes",
        "/receptions",
        "/factures",
        "/export/commandes",
        "/export/receptions",
        "/export/receptions/pesees",
        "/export/receptions/bobines",
    ):
        _refuse(application, L, "GET", chemin)


def test_l_alimentation_n_exporte_pas_un_bon(application: FastAPI) -> None:
    """Hérité : test_exports::test_l_alimentation_n_exporte_pas_un_bon."""
    _refuse(application, L, "GET", "/export/commandes/{id}/bon")
    _permis(D, "GET", "/export/commandes/{id}/bon")
    _permis(A, "GET", "/export/commandes/{id}/bon")


def test_rien_ne_s_exporte_sans_connexion(application: FastAPI) -> None:
    """Hérité : test_exports::test_rien_ne_s_exporte_sans_connexion."""
    for chemin in ("/export/pilotage", "/export/mouvements", "/export/commandes/{id}/bon"):
        _refuse(application, None, "GET", chemin)


def test_l_etat_du_serveur_est_reserve_a_la_direction(application: FastAPI) -> None:
    """Hérité : test_direction::test_l_etat_du_serveur_est_reserve_a_la_direction (D, T)."""
    for role in (A, L):
        _refuse(application, role, "GET", "/serveur")
    _permis(D, "GET", "/serveur")
    _permis(T, "GET", "/serveur")


def test_le_journal_du_serveur_nomme_l_acteur(
    application: FastAPI, achats: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """ARCHITECTURE § 4 : `requete=… utilisateur=achats role=achats GET /api/moi 200`."""
    with caplog.at_level(logging.INFO, logger="gestion_mp_pro.requetes"):
        assert achats.get("/api/moi").status_code == 200
    assert any("utilisateur=achats role=achats GET /api/moi 200" in m for m in caplog.messages)
