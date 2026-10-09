"""Recettes et leurs versions (routes 85, 87–89 ; lot D2).

Héritage REGLES A § 1.7–1.8 (R-REF-55 à R-REF-69, X-REF-39 à X-REF-52) ; défauts de Gestion MP
D-01, D-03, D-04, D-05, D-18, D-19 ; ECRANS-PRO partie 7 (P7-5, P7-8).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.qualites import (
    corps_fiche,
    creer_qualite,
    lignes,
    lire_qualite,
    ok,
    poids,
    refus,
)
from fabriques.referentiels import matiere, role_id, unique
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Journal, Matiere


def _versions(client: TestClient, qid: int) -> list[dict]:
    return ok(client.get(f"/api/qualites/{qid}/versions"))  # type: ignore[no-any-return]


def test_chaque_recette_enregistree_garde_sa_version(direction: TestClient) -> None:
    """Hérité : test_suivi::test_chaque_recette_enregistree_garde_sa_version."""
    a = matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1}, parts={a: 100})
    v = _versions(direction, q["id"])
    reference = v[0]["lignes"][0]["reference"]
    assert v[0]["lignes"] == [
        {
            "matiere_id": a,
            "reference": reference,
            "role_id": role_id("Poil"),
            "role": "Poil",
            "pourcentage": 100,
        }
    ]
    assert v[0]["par"]["nom"] == "Direction" and v[0]["numero"] == 2


def test_d04_pas_de_version_sans_changement(direction: TestClient) -> None:
    """D-04 : la même recette renvoyée, un renommage, un arrêt ne créent pas de version."""
    a = matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1}, parts={a: 100})
    n = len(_versions(direction, q["id"]))
    q = ok(
        direction.put(
            f"/api/qualites/{q['id']}/recette",
            json={"lignes": lignes({a: "100.000"}), "version": q["version"]},
        )
    )
    q = ok(direction.put(f"/api/qualites/{q['id']}", json=corps_fiche(q, nom="Renommée")))
    assert len(_versions(direction, q["id"])) == n
    ok(direction.put(f"/api/qualites/{q['id']}", json=corps_fiche(q, poids=poids(Poil=2))))
    assert _versions(direction, q["id"])[0]["poids"][0]["poids"] == 2


def test_une_recette_fausse_ne_s_enregistre_pas(direction: TestClient) -> None:
    """Hérité : test_parcours::test_une_recette_fausse_ne_s_enregistre_pas."""
    a1, a2 = matiere(), matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1})
    r = direction.put(
        f"/api/qualites/{q['id']}/recette",
        json={"lignes": lignes({a1: 60, a2: 30}), "version": q["version"]},
    )
    corps = refus(r, 422, "Dans chaque rôle, la recette doit faire 100 % : Poil 90 %.")
    assert corps["code"] == "recette_incomplete"


def test_une_recette_acceptee_n_est_pas_bloquante_le_lendemain(direction: TestClient) -> None:
    """Hérité : test_audit2_atelier::test_une_recette_acceptee_n_est_pas_bloquante_le_lendemain."""
    a = matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1}, parts={a: "99.995"})
    controle = {x["qualite"]: x for x in ok(direction.get("/api/nomenclature"))["controle"]}
    assert controle[q["code"]]["conforme"] and controle[q["code"]]["qualite_id"] == q["id"]
    r = direction.put(
        f"/api/qualites/{q['id']}/recette",
        json={"lignes": lignes({a: "99.9"}), "version": q["version"]},
    )
    refus(r, 422, "Poil 99,9 %")


def test_lignes_inconnues_ou_en_double(direction: TestClient) -> None:
    """X-REF-45, X-REF-46."""
    a = matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1})
    url, v = f"/api/qualites/{q['id']}/recette", q["version"]
    refus(
        direction.put(url, json={"lignes": lignes({999999: 100}), "version": v}),
        422,
        "Matière inconnue dans la recette.",
    )
    deux = [{"matiere_id": a, "pourcentage": 50}] * 2
    refus(direction.put(url, json={"lignes": deux, "version": v}), 422, "figure deux fois")


def test_revenir_a_une_version_remet_parts_et_poids(direction: TestClient) -> None:
    """Hérité : test_audit2_atelier::test_revenir_a_une_version_remet_parts_et_poids."""
    poil, trame = matiere(), matiere(role="Trame")
    q = creer_qualite(
        direction, poids_m2={"Poil": 1.0, "Trame": 0.5}, parts={poil: 100, trame: 100}
    )
    avant = _versions(direction, q["id"])[0]
    q = ok(
        direction.put(
            f"/api/qualites/{q['id']}", json=corps_fiche(q, poids=poids(Poil=1.3, Trame=0.5))
        )
    )
    n = len(_versions(direction, q["id"]))
    url = f"/api/qualites/{q['id']}/versions/{avant['id']}/restaurer"
    refus(direction.post(url, json={"motif": " ", "version": q["version"]}), 422)
    r = ok(direction.post(url, json={"motif": "erreur de saisie", "version": q["version"]}))
    assert {p["role"]: p["poids"] for p in r["poids"]} == {"Poil": 1.0, "Trame": 0.5}
    apres = _versions(direction, q["id"])
    assert len(apres) == n + 1
    assert apres[0]["origine"] == "restauration" and apres[0]["motif"] == "erreur de saisie"
    assert apres[0]["restauree_de"] == avant["numero"]
    assert apres[0]["lignes"] == avant["lignes"] and apres[0]["poids"] == avant["poids"]
    with sessions()() as s:
        detail = s.scalars(
            select(Journal.detail)
            .where(Journal.objet_id == q["id"], Journal.action == "recette")
            .order_by(Journal.id.desc())
        ).first()
    assert (
        detail is not None
        and detail.endswith("— erreur de saisie")
        and "retour à la version" in detail
    )
    # Revenir à la version en vigueur : rien à restaurer ; une version inconnue : 404.
    refus(direction.post(url, json={"motif": "encore", "version": r["version"]}), 409, "déjà")
    refus(
        direction.post(
            f"/api/qualites/{q['id']}/versions/999999/restaurer",
            json={"motif": "x", "version": r["version"]},
        ),
        404,
        "Version introuvable.",
    )


def test_d05_fiche_poids_sans_matiere(direction: TestClient) -> None:
    """D-05 (Hérité : test_defauts_d::test_d05_fiche_poids_sans_matiere, partie serveur)."""
    poil = matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1}, parts={poil: 100})
    r = direction.put(
        f"/api/qualites/{q['id']}", json=corps_fiche(q, poids=poids(Poil=1, Franges=1))
    )
    refus(r, 422, "La recette oublie le rôle Franges (1 au m²)")
    # Une qualité neuve, sans recette : la fiche passe et avertit.
    neuve = creer_qualite(direction, poids_m2={"Poil": 1})
    neuve = ok(
        direction.put(
            f"/api/qualites/{neuve['id']}",
            json=corps_fiche(neuve, poids=poids(Poil=1, Trame="0.5")),
        )
    )
    assert "Trame" in neuve["avertissement"]
    # Arrêtée : sa recette incomplète s'enregistre, avec un avertissement…
    neuve = ok(direction.put(f"/api/qualites/{neuve['id']}", json=corps_fiche(neuve, actif=False)))
    r = ok(
        direction.put(
            f"/api/qualites/{neuve['id']}/recette",
            json={"lignes": lignes({poil: 100}), "version": neuve["version"]},
        )
    )
    assert r["avertissement"].startswith("Qualité arrêtée : recette enregistrée telle quelle.")
    assert "Trame" in r["avertissement"]
    # … et ne se remet pas en service ainsi.
    refus(
        direction.put(f"/api/qualites/{neuve['id']}", json=corps_fiche(r, actif=True)), 422, "Trame"
    )


def test_une_recette_qui_oublie_un_role_est_refusee(direction: TestClient) -> None:
    """Hérité : test_plan_besoins::test_une_recette_qui_oublie_un_role_est_refusee_et_l_atelier
    _est_prevenu (partie recette ; la proposition d'ordre est au lot D6)."""
    poil, frange = matiere(), matiere(role="Franges")
    q = creer_qualite(direction, poids_m2={"Poil": 1, "Franges": 2}, parts={poil: 100, frange: 100})
    r = direction.put(
        f"/api/qualites/{q['id']}/recette",
        json={"lignes": lignes({poil: 100}), "version": q["version"]},
    )
    refus(r, 422, "La recette oublie le rôle Franges (2 au m²)")
    r = direction.put(
        f"/api/qualites/{q['id']}", json=corps_fiche(q, poids=poids(Poil=1, Franges=2, Trame="0.5"))
    )
    refus(r, 422, "Trame")
    plusieurs = direction.put(
        f"/api/qualites/{q['id']}",
        json=corps_fiche(q, poids=poids(Poil=1, Franges=2, Trame=1, Colle=1)),
    )
    refus(plusieurs, 422, "La recette oublie les rôles Colle (1 au m²), Trame (1 au m²)")


def test_fiche_et_recette_en_une_transaction(direction: TestClient) -> None:
    """P7-8 : fiche + recette en une requête ; une recette refusée n'écrit pas la fiche."""
    poil, trame = matiere(), matiere(role="Trame")
    q = creer_qualite(direction, poids_m2={"Poil": 1})
    faux = corps_fiche(
        q, nom="Ne passe pas", poids=poids(Poil=1, Trame=1), recette=lignes({poil: 100, trame: 50})
    )
    refus(direction.put(f"/api/qualites/{q['id']}", json=faux), 422, "Trame 50 %")
    assert lire_qualite(direction, q["id"])["nom"] == "Essai D2"
    juste = corps_fiche(
        q,
        nom="Passe",
        poids=poids(Poil=1, Trame=1),
        recette=lignes({poil: 100, trame: 100}),
        motif="nouvelle trame",
    )
    r = ok(direction.put(f"/api/qualites/{q['id']}", json=juste))
    assert r["nom"] == "Passe" and len(r["recette"]) == 2 and r["avertissement"] == ""
    v = _versions(direction, q["id"])
    assert len(v) == 2 and v[0]["motif"] == "nouvelle trame"


def test_d03_renommer_une_matiere_garde_ses_versions(direction: TestClient) -> None:
    """D-03 : les versions désignent la matière par son id : un renommage la suit, et la
    version revient telle quelle."""
    a, b = matiere(), matiere()
    q = creer_qualite(direction, poids_m2={"Poil": 1}, parts={a: 100})
    q = ok(
        direction.put(
            f"/api/qualites/{q['id']}/recette",
            json={"lignes": lignes({b: 100}), "version": q["version"]},
        )
    )
    nouveau = unique("RENOMMEE")
    with sessions()() as s, s.begin():
        m = s.get(Matiere, a)
        assert m is not None
        m.reference = nouveau
    ancienne = _versions(direction, q["id"])[1]
    assert ancienne["lignes"][0]["reference"] == nouveau
    r = ok(
        direction.post(
            f"/api/qualites/{q['id']}/versions/{ancienne['id']}/restaurer",
            json={"motif": "essai", "version": q["version"]},
        )
    )
    assert [(x["matiere_id"], x["reference"]) for x in r["recette"]] == [(a, nouveau)]


def test_un_cuir_se_saisit_en_metres_dans_la_recette(direction: TestClient) -> None:
    """Hérité : test_referentiels_complets::test_un_cuir_se_saisit_en_metres_dans_la_recette."""
    cuir = matiere(role="Cuir", unite_prix="ml", prix="3", densite="0.05")
    q = creer_qualite(direction, poids_m2={"Cuir": 2})
    ok(
        direction.put(
            f"/api/qualites/{q['id']}/recette",
            json={
                "lignes": lignes({cuir: 100}),
                "motif": "essai du motif",
                "version": q["version"],
            },
        )
    )
    ligne = lire_qualite(direction, q["id"])["recette"][0]
    # 3 MAD le mètre, densité 0,05 kg/ml : 60 MAD le kilo, mais on l'achète au mètre.
    assert (ligne["prix"], ligne["unite_prix"]) == (3.0, "ml") and ligne[
        "prix_kg"
    ] == pytest.approx(60)
    # 2 ml/m² saisis, 0,1 kg/m² calculés : 6 MAD le m² (hors perte), 6,12 avec.
    assert ligne["ml_m2"] == pytest.approx(2) and ligne["kg_m2"] == pytest.approx(0.1)
    assert ligne["cout_m2_mad"] == pytest.approx(2 * 3.0 * 1.02) and ligne["lineaire"]
    with sessions()() as s:
        trace = s.scalars(
            select(Journal.detail)
            .where(Journal.action == "recette", Journal.objet_id == q["id"])
            .order_by(Journal.id.desc())
        ).first()
    assert trace is not None and trace.endswith("essai du motif")


def test_la_recette_se_saisit_en_metres_par_m2(achats: TestClient, direction: TestClient) -> None:
    """Hérité : test_matieres_au_metre::test_la_recette_se_saisit_en_metres_par_m2."""
    cuir = matiere(role="Cuir", unite_prix="ml", prix="0.5", densite="0.014")
    poil = matiere()
    q = creer_qualite(direction, poids_m2={"Cuir": 1, "Poil": 2}, parts={cuir: 100, poil: 100})
    recette = {x["matiere_id"]: x for x in lire_qualite(achats, q["id"])["recette"]}
    assert recette[cuir]["ml_m2"] == pytest.approx(1.0) and recette[cuir]["kg_m2"] == pytest.approx(
        0.014
    )
    assert recette[cuir]["densite"] == 0.014
    assert (recette[cuir]["prix"], recette[cuir]["unite_prix"]) == (0.5, "ml")
    assert recette[poil]["ml_m2"] is None and recette[poil]["kg_m2"] == pytest.approx(2.0)
