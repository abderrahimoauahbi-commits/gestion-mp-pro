"""Classification et rôles de nomenclature (routes 57–63) — lot D1.

Héritage R-REF-05…15, X-REF-02…13 (REGLES § 1.2–1.4) ; défauts A-06, A-12, A-13, A-24.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fabrique import *  # noqa: F403
from fabriques.referentiels import matiere, qualite, role_id, unique, valeur_classification
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.calcul.classification import decomposer
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Journal, QualitePoids, RoleNomenclature


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def test_valeurs_completes_desactivees_supprimees(
    achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : test_referentiels_complets::test_composition_detaillee_et_commentaire ;
    R-REF-12 (un titrage se lit dans son code) ; X-REF-13."""
    code = unique("PPX")
    c = ok(achats.post("/api/classification/compositions", json={
        "code": code, "libelle": "Polypropylène X", "famille": "Synthétique",
        "composition_detaillee": "100 % polypropylène", "commentaire": "essai", "valeur": "ignoré",
    }), 201)  # fmt: skip
    assert (c["composition_detaillee"], c["commentaire"], c["valeur"]) == (
        "100 % polypropylène",
        "essai",
        None,
    )
    t = ok(achats.post("/api/classification/titrages", json={"code": f"29{len(code)}0 Dtex"}), 201)
    assert (t["valeur"], t["unite"]) == (f"29{len(code)}0", "Dtex")
    corps = {"code": code, "actif": False, "commentaire": "garder", "version": c["version"]}
    lu = ok(achats.put(f"/api/classification/compositions/{c['id']}", json=corps))
    assert (lu["actif"], lu["commentaire"], lu["avertissement"]) == (False, "garder", None)
    classification = ok(alimentation.get("/api/classification"))
    vue = next(x for x in classification["compositions"] if x["code"] == code)
    assert vue["actif"] is False and vue["nb_matieres"] == 0
    assert (
        next(x for x in classification["titrages"] if x["id"] == t["id"])["valeur"] == t["valeur"]
    )
    assert achats.delete(f"/api/classification/compositions/{c['id']}").status_code == 204
    assert (
        achats.post("/api/classification/inconnue", json={"code": "x"}).json()["detail"]
        == "Liste inconnue."
    )
    assert alimentation.post("/api/classification/couleurs", json={"code": "x"}).status_code == 403


def test_un_code_trop_long_est_refuse(achats: TestClient) -> None:
    """Hérité : test_defauts_a::test_un_code_de_composition_trop_long_est_refuse (A-06)."""
    r = achats.post("/api/classification/compositions", json={"code": "C" * 33})
    assert (r.status_code, r.json()["detail"]) == (
        422,
        f"Composition : le code tient en 32 caractères au plus (« {'C' * 33} » en a 33).",
    )
    assert achats.post("/api/classification/couleurs", json={"code": "C" * 64}).status_code == 201


def test_pp_et_PP_ne_coexistent_pas(achats: TestClient) -> None:  # noqa: N802
    """Hérité : test_defauts_a::test_pp_et_PP_ne_coexistent_pas (A-12)."""
    code = unique("PP")
    ok(achats.post("/api/classification/compositions", json={"code": code}), 201)
    r = achats.post("/api/classification/compositions", json={"code": code.lower()})
    assert (r.status_code, r.json()["detail"]) == (
        409,
        f"« {code} » existe déjà (« {code.lower()} »).",
    )


def test_modifier_une_valeur_sans_la_renommer_ne_journalise_pas_de_fleche(
    achats: TestClient,
) -> None:
    """Hérité :
    test_defauts_a::test_modifier_une_valeur_sans_la_renommer_ne_journalise_pas_de_fleche
    (A-24) — et l'écran est averti des matières qui gardent une valeur désactivée."""
    v = valeur_classification("couleur", unique("Rouge"))
    matiere(couleur_id=v)
    lue = next(x for x in ok(achats.get("/api/classification"))["couleurs"] if x["id"] == v)
    corps = {
        "code": f"  {lue['code']} ",
        "libelle": "Rouge vif",
        "actif": False,
        "version": lue["version"],
    }
    fiche = ok(achats.put(f"/api/classification/couleurs/{v}", json=corps))
    assert fiche["avertissement"] == (
        f"« {lue['code']} » reste porté par 1 matière(s) : elle ne se choisit plus, ces matières "
        "la gardent."
    )
    with sessions()() as s:
        j = s.scalars(
            select(Journal).where(Journal.objet == "couleur", Journal.objet_id == v)
        ).all()[-1]
    assert j.detail == lue["code"] and j.apres == {"libelle": "Rouge vif", "actif": False}
    r = achats.delete(f"/api/classification/couleurs/{v}")
    assert r.json()["detail"] == (
        f"« {lue['code']} » est porté par 1 matière(s) : les reclasser d'abord, ou désactiver "
        "la valeur."
    )
    corps = {"code": "Bleu", "version": lue["version"]}
    assert achats.put(f"/api/classification/couleurs/{v}", json=corps).status_code == 409


def test_les_roles_se_tiennent_par_la_direction(direction: TestClient, achats: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_les_roles_se_tiennent_par_la_direction —
    direction seule, doublon insensible à la casse, rôle de base intouchable, rôle porté
    insupprimable ; seuls Cuir, Franges et Ruban se comptent au mètre (X-REF-01)."""
    code = unique("Velours")
    assert achats.post("/api/classification/roles", json={"code": code}).status_code == 403
    r = ok(direction.post("/api/classification/roles", json={"code": code, "ordre": 20}), 201)
    assert (r["lineaire"], r["de_base"]) == (False, False)
    doublon = direction.post("/api/classification/roles", json={"code": code.upper()})
    assert (doublon.status_code, doublon.json()["detail"]) == (
        409,
        f"Le rôle « {code.upper()} » existe déjà.",
    )
    assert direction.post("/api/classification/roles", json={"code": "cuir"}).status_code == 409
    poil = role_id("Poil")
    lu_poil = next(x for x in ok(direction.get("/api/classification"))["roles"] if x["id"] == poil)
    corps_poil = {"code": "Poils", "ordre": 0, "version": lu_poil["version"]}
    renomme = direction.put(f"/api/classification/roles/{poil}", json=corps_poil)
    assert renomme.json()["detail"] == "« Poil » est un rôle de base du calcul : il garde son nom."
    supprime = direction.delete(f"/api/classification/roles/{poil}")
    assert (
        supprime.json()["detail"]
        == "« Poil » est un rôle de base du calcul : il ne se supprime pas."
    )
    matiere(role=code)
    porte = direction.delete(f"/api/classification/roles/{r['id']}")
    assert (
        porte.json()["detail"]
        == f"« {code} » est porté par 1 matière(s) et 0 qualité(s) : les changer d'abord."
    )
    roles = ok(direction.get("/api/classification"))["roles"]
    assert [x["code"] for x in roles if x["lineaire"]] == ["Cuir", "Franges", "Ruban"]


def test_un_role_aux_poids_nuls_se_renomme_et_se_supprime(direction: TestClient) -> None:
    """Hérité : test_defauts_a::test_un_role_aux_poids_nuls_se_renomme (A-13) ; R-REF-10 —
    les poids nuls partent avec le rôle."""
    code = unique("Galon")
    r = ok(direction.post("/api/classification/roles", json={"code": code}), 201)
    q = qualite(poids={"Poil": "1.2"})
    with sessions()() as s, s.begin():
        s.add(QualitePoids(qualite_id=q, role_id=r["id"], poids=Decimal(0)))
    nouveau = f"{code}-bis"
    lu = ok(
        direction.put(
            f"/api/classification/roles/{r['id']}",
            json={"code": nouveau, "ordre": 3, "version": r["version"]},
        )
    )
    assert (lu["code"], lu["ordre"], lu["nb_qualites"], lu["version"]) == (nouveau, 3, 0, 2)
    assert direction.delete(f"/api/classification/roles/{r['id']}").status_code == 204
    with sessions()() as s:
        assert s.get(RoleNomenclature, r["id"]) is None
        assert s.scalars(select(QualitePoids).where(QualitePoids.role_id == r["id"])).all() == []


def test_un_role_modifie_entre_temps_est_refuse(direction: TestClient) -> None:
    """Route 59 (révision 0004) : la version lue est contrôlée ; périmée → 409 qui nomme
    l'auteur, et rien n'est écrit."""
    code = unique("Chenille")
    r = ok(direction.post("/api/classification/roles", json={"code": code}), 201)
    assert r["version"] == 1
    url = f"/api/classification/roles/{r['id']}"
    ok(direction.put(url, json={"code": code, "ordre": 5, "version": 1}))
    perime = direction.put(url, json={"code": f"{code}-x", "ordre": 6, "version": 1})
    assert perime.status_code == 409 and perime.json()["code"] == "conflit_version"
    assert perime.json()["detail"].startswith("Ce rôle a été modifié entre-temps par ")
    sans = direction.put(url, json={"code": code, "ordre": 6})
    assert sans.status_code == 422
    with sessions()() as s:
        lu = s.get(RoleNomenclature, r["id"])
        assert lu is not None and (lu.code, lu.ordre, lu.version) == (code, 5, 2)


def test_le_titrage_en_livres_du_jute() -> None:
    """« lbs » : le titrage du jute en livres, lu dans la référence (Mohamed, 12/10/2026)."""
    for reference, titrage in (("Jute 8 lbs", "8"), ("JUTE 10LBS Naturel", "10")):
        c = decomposer(reference)
        assert (c.titrage, c.titrage_unite) == (titrage, "lbs")
    assert decomposer("Jute 12/1").titrage_unite == "Nm"
