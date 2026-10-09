"""Comptes : installation, codes par rôle, sessions fermées, toujours une direction (lot S2).

Héritage B.5.3–B.5.5 (K20–K24, KR1, KR15, KR16, KR20–KR24), défauts F-01 et F-03, D9, D10.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fabrique import *  # noqa: F403
from fabrique import compte, connecter, oublier_les_essais
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from gestion_mp_pro import db
from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION
from gestion_mp_pro.modeles import Utilisateur
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services import utilisateurs
from gestion_mp_pro.services.comptes import Acteur


@pytest.fixture
def base_sans_compte(application: FastAPI) -> Iterator[TestClient]:
    """L'application sur une base sans aucun compte (transaction annulée à la fin)."""
    with db.moteur().connect() as c:
        transaction = c.begin()
        c.execute(text("TRUNCATE utilisateur CASCADE"))
        s = Session(bind=c, join_transaction_mode="create_savepoint", expire_on_commit=False)

        def session_d_essai() -> Iterator[Session]:
            try:
                yield s
                s.commit()
            except BaseException:
                s.rollback()
                raise

        application.dependency_overrides[db.session] = session_d_essai
        try:
            yield TestClient(application, headers={ENTETE_ANTI_FALSIFICATION: "1"})
        finally:
            application.dependency_overrides.pop(db.session)
            s.close()
            transaction.rollback()


def test_installation_une_seule_fois(base_sans_compte: TestClient) -> None:
    """Hérité : K20–K23, KR1 — le premier compte est la direction ; ensuite 409."""
    c = base_sans_compte
    assert c.get("/api/etat").json()["installe"] is False
    corps = {"societe": "", "identifiant": " MAZARI ", "nom": "Mohamed", "code": "court"}
    r = c.post("/api/installation", json=corps)
    assert (r.status_code, r.json()["detail"]) == (422, "Le code doit faire au moins 8 caractères.")
    r = c.post("/api/installation", json={**corps, "code": "direction-1"})
    assert r.status_code == 201
    assert (r.json()["identifiant"], r.json()["role"]) == ("mazari", "direction")
    assert c.get("/api/moi").json()["nom"] == "Mohamed"  # la session est ouverte
    assert c.get("/api/etat").json()["installe"] is True
    r = c.post("/api/installation", json={**corps, "identifiant": "autre", "code": "direction-2"})
    assert r.status_code == 409
    assert r.json() == {
        "detail": "Gestion MP PRO est déjà installé : connectez-vous.",
        "code": "deja_installe",
    }


def test_code_alimentation_exactement_4_chiffres(direction: TestClient) -> None:
    """Hérité : test_defauts_f::test_code_alimentation_exactement_4_chiffres (F-01, D10)."""
    for faux in ("12345", "12a4", "123", "abcd"):
        r = direction.post(
            "/api/utilisateurs",
            json={
                "identifiant": "c-atelier",
                "nom": "C atelier",
                "role": "alimentation",
                "code": faux,
            },
        )
        assert r.status_code == 422, faux
        assert r.json()["detail"] == "Le code de l'atelier est fait de 4 chiffres."
    r = direction.post(
        "/api/utilisateurs",
        json={
            "identifiant": "c-atelier",
            "nom": "C atelier",
            "role": "alimentation",
            "code": "4821",
        },
    )
    assert r.status_code == 201
    assert (
        direction.post(
            f"/api/utilisateurs/{r.json()['id']}/code", json={"code": "48210"}
        ).status_code
        == 422
    )
    r = direction.post(
        "/api/utilisateurs",
        json={
            "identifiant": "c-admin",
            "nom": "C admin",
            "role": "administrateur",
            "code": "onze-carac",
        },
    )
    assert r.json()["detail"] == "Le code doit faire au moins 12 caractères."


def test_promouvoir_sans_nouveau_code_refuse(application: FastAPI, direction: TestClient) -> None:
    """Hérité : test_defauts_f::test_promouvoir_sans_nouveau_code_refuse (F-01)."""
    uid = compte("alimentation", identifiant="c-promu", code="1357")
    corps = {"nom": "C PROMU", "role": "achats", "email": "", "actif": True, "version": 1}
    r = direction.put(f"/api/utilisateurs/{uid}", json=corps)
    assert r.status_code == 422
    assert (
        r.json()["detail"]
        == "Ce rôle demande un code de 8 caractères au moins : en donner un nouveau."
    )
    assert (
        direction.put(f"/api/utilisateurs/{uid}", json={**corps, "code": "1357"}).status_code == 422
    )
    r = direction.put(f"/api/utilisateurs/{uid}", json={**corps, "code": "achats-f-01"})
    assert r.status_code == 200 and r.json()["version"] == 2
    connecter(application, "c-promu", "achats-f-01")
    r = direction.put(f"/api/utilisateurs/{uid}", json={**corps, "role": "direction", "version": 2})
    assert r.status_code == 200  # même longueur : le code se garde
    r = direction.put(
        f"/api/utilisateurs/{uid}", json={**corps, "role": "alimentation", "version": 3}
    )
    assert r.json()["detail"] == "Ce rôle demande un code de 4 chiffres : en donner un nouveau."
    r = direction.put(
        f"/api/utilisateurs/{uid}", json={**corps, "role": "administrateur", "version": 3}
    )
    assert (
        r.json()["detail"]
        == "Ce rôle demande un code de 12 caractères au moins : en donner un nouveau."
    )


def test_son_propre_code(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_son_propre_code_d_atelier_fait_4_chiffres ; KR15, KR16."""
    compte("alimentation", identifiant="c-moi", code="2468")
    c = connecter(application, "c-moi", "2468")
    r = c.put("/api/moi/code", json={"ancien": "2468", "nouveau": "24680"})
    assert (r.status_code, r.json()["detail"]) == (
        422,
        "Le nouveau code de l'atelier est fait de 4 chiffres.",
    )
    r = c.put("/api/moi/code", json={"ancien": "0000", "nouveau": "8642"})
    assert (r.status_code, r.json()["detail"]) == (403, "Le code actuel ne correspond pas.")
    assert c.put("/api/moi/code", json={"ancien": "2468", "nouveau": "8642"}).status_code == 204
    compte("achats", identifiant="c-moi-2", code="c-moi-2-xx")
    r = connecter(application, "c-moi-2", "c-moi-2-xx").put(
        "/api/moi/code", json={"ancien": "c-moi-2-xx", "nouveau": "court"}
    )
    assert r.json()["detail"] == "Le nouveau code doit faire au moins 8 caractères."


def test_changer_le_code_ferme_les_autres_sessions(
    application: FastAPI, direction: TestClient
) -> None:
    """Hérité : test_defauts_f::test_changer_le_code_ferme_les_autres_sessions (F-03)."""
    uid = compte("achats", identifiant="c-sessions", code="sessions-f-03")
    bureau = connecter(application, "c-sessions", "sessions-f-03")
    telephone = connecter(application, "c-sessions", "sessions-f-03")
    assert (
        bureau.put(
            "/api/moi/code", json={"ancien": "sessions-f-03", "nouveau": "sessions-f-03b"}
        ).status_code
        == 204
    )
    assert bureau.get("/api/moi").status_code == 200
    assert telephone.get("/api/moi").status_code == 401
    assert (
        direction.post(f"/api/utilisateurs/{uid}/code", json={"code": "sessions-f-03c"}).status_code
        == 204
    )
    assert bureau.get("/api/moi").status_code == 401
    nouveau = connecter(application, "c-sessions", "sessions-f-03c")
    version = nouveau.get("/api/moi").json()["version"]
    corps = {
        "nom": "C SESSIONS",
        "role": "direction",
        "email": "",
        "actif": True,
        "version": version,
    }
    assert direction.put(f"/api/utilisateurs/{uid}", json=corps).status_code == 200
    assert nouveau.get("/api/moi").status_code == 401  # un nouveau rôle reconnecte


def test_ancien_code_faux_compte_un_echec(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_ancien_code_faux_compte_un_echec (F-03)."""
    compte("achats", identifiant="c-ancien", code="ancien-f-03")
    c = connecter(application, "c-ancien", "ancien-f-03")
    codes = [
        c.put("/api/moi/code", json={"ancien": f"faux-{i}", "nouveau": "ancien-f-03b"}).status_code
        for i in range(6)
    ]
    assert codes == [403] * 5 + [429]
    r = TestClient(application, headers={ENTETE_ANTI_FALSIFICATION: "1"}).post(
        "/api/connexion", json={"identifiant": "c-ancien", "code": "ancien-f-03"}
    )
    assert r.status_code == 429
    oublier_les_essais()


def test_desactiver_ferme_les_sessions(application: FastAPI, administrateur: TestClient) -> None:
    """ARCHITECTURE § 5.1 : désactiver ferme les sessions ; le compte ne se connecte plus."""
    uid = compte("achats", identifiant="c-desactive", code="desactive-12")
    c = connecter(application, "c-desactive", "desactive-12")
    corps = {"nom": "C DESACTIVE", "role": "achats", "email": "", "actif": False, "version": 1}
    r = administrateur.put(f"/api/utilisateurs/{uid}", json=corps)
    assert (r.status_code, r.json()["actif"], r.json()["sessions_ouvertes"]) == (200, False, 0)
    # H-09 : la session fermée dit pourquoi (et l'écran « Ce compte n'est plus actif : voyez
    # la direction. »), pas « Connectez-vous pour continuer. »
    refus = c.get("/api/moi")
    assert (refus.status_code, refus.json()) == (
        401,
        {"detail": "Ce compte n'est plus actif.", "code": "compte_inactif"},
    )
    r = administrateur.put(f"/api/utilisateurs/{uid}", json=corps)
    assert r.status_code == 409 and r.json()["code"] == "conflit_version"
    assert "a été modifié entre-temps par Administrateur" in r.json()["detail"]
    reactive = {**corps, "actif": True, "version": 2}
    assert administrateur.put(f"/api/utilisateurs/{uid}", json=reactive).status_code == 200
    assert c.get("/api/moi").json()["code"] == "non_connecte", "la session fermée ne revit pas"
    oublier_les_essais()


def test_refus_sur_les_comptes(direction: TestClient, comptes: dict[str, int]) -> None:
    """Hérité : KR20, KR21, KR23, KR24 (messages mot pour mot) ; D9 (soi-même)."""
    base = {"identifiant": "c-refus", "nom": "C refus", "role": "chef", "code": "chef-chef-12"}
    assert direction.post("/api/utilisateurs", json=base).json()["detail"] == "Rôle inconnu."
    assert direction.post("/api/utilisateurs", json={**base, "role": "achats"}).status_code == 201
    r = direction.post(
        "/api/utilisateurs", json={**base, "identifiant": "C-REFUS", "role": "achats"}
    )
    assert (r.status_code, r.json()["detail"]) == (409, "L'identifiant « c-refus » est déjà pris.")
    r = direction.put(
        "/api/utilisateurs/999999",
        json={"nom": "Xx", "role": "achats", "actif": True, "version": 1},
    )
    assert (r.status_code, r.json()["detail"]) == (404, "Compte introuvable.")
    moi = direction.get("/api/moi").json()
    soi = {
        "nom": moi["nom"],
        "role": "achats",
        "email": "",
        "actif": True,
        "version": moi["version"],
    }
    r = direction.put(f"/api/utilisateurs/{comptes['direction']}", json=soi)
    assert (r.status_code, r.json()["detail"]) == (
        409,
        "Vous ne pouvez pas retirer vos propres droits de direction.",
    )
    r = direction.put(
        f"/api/utilisateurs/{comptes['direction']}",
        json={**soi, "role": "direction", "actif": False},
    )
    assert r.status_code == 409


def test_toujours_une_direction_active(comptes: dict[str, int]) -> None:
    """MODELE-DONNEES § 3.1.1 : il reste toujours au moins une direction active."""
    with db.fabrique()() as s:
        s.execute(
            update(Utilisateur)
            .where(Utilisateur.role == Role.direction, Utilisateur.id != comptes["direction"])
            .values(actif=False)
        )
        admin = Acteur(
            comptes["administrateur"], "administrateur", "Administrateur", "administrateur"
        )
        u = s.get(Utilisateur, comptes["direction"])
        assert u is not None
        m = utilisateurs.Modification(
            nom=u.nom, role="direction", email="", actif=False, version=u.version
        )
        with pytest.raises(Refus) as refus:
            utilisateurs.modifier(s, admin, u.id, m)
        assert (refus.value.http, refus.value.code) == (409, "derniere_direction")
        with pytest.raises(Refus):
            utilisateurs.modifier(
                s,
                admin,
                u.id,
                utilisateurs.Modification(
                    nom=u.nom, role="achats", email="", actif=True, version=u.version
                ),
            )
        s.rollback()


def test_moi_et_son_courriel(achats: TestClient, alimentation: TestClient) -> None:
    moi = achats.get("/api/moi").json()
    assert moi["droits"] == ["liberer_quarantaine", "mettre_en_quarantaine", "voir_prix"]
    assert alimentation.get("/api/moi").json()["droits"] == ["mettre_en_quarantaine", "monter"]
    assert alimentation.get("/api/moi").json()["voit_prix"] is False
    r = achats.put("/api/moi", json={"email": "pas une adresse", "version": moi["version"]})
    assert (
        r.json()["detail"]
        == "Adresse de courriel illisible : pas une adresse (ex. direction@usine.ma)."
    )
    r = achats.put("/api/moi", json={"email": "achats@usine.ma", "version": moi["version"]})
    assert r.status_code == 200 and r.json()["email"] == "achats@usine.ma"
    r = achats.put("/api/moi", json={"email": "x@usine.ma", "version": moi["version"]})
    assert r.status_code == 409 and r.json()["detail"].startswith("Votre compte a été modifié")
    assert (
        achats.put("/api/moi", json={"email": "", "version": moi["version"] + 1}).status_code == 200
    )


def test_liste_des_comptes(administrateur: TestClient, achats: TestClient) -> None:
    """Hérité : K40 ; l'administrateur gère les comptes (D, T), les achats non."""
    liste = administrateur.get("/api/utilisateurs").json()
    assert [u["nom"].lower() for u in liste] == sorted(u["nom"].lower() for u in liste)
    assert {"Direction", "Administrateur technique"} <= {u["role_libelle"] for u in liste}
    assert all("empreinte_code" not in u for u in liste)
    assert achats.get("/api/utilisateurs").json()["detail"] == (
        "Cette action est réservée à : la direction, l'administrateur technique."
    )
