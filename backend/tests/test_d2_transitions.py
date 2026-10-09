"""Tables de transitions du lot D2, rejouées exhaustivement ; version périmée sur chaque écriture ;
deux postes sur le même étage en même temps.

- Qualité : état (en service, arrêtée) × geste × rôle → code HTTP.
- Métier : état (en service, arrêté) × geste × rôle → code HTTP.
- Chaque écriture du lot reçoit une `version` : périmée → 409 `conflit_version`.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.qualites import (
    UN,
    corps_fiche,
    creer_metier,
    creer_qualite,
    lignes,
    lire_metier,
    lire_qualite,
    ok,
    version_etage,
)
from fabriques.referentiels import matiere
from fastapi.testclient import TestClient

Geste = Callable[[dict[str, Any], dict[str, int]], tuple[str, str, dict[str, Any]]]


def _qualite(direction: TestClient, etat: str) -> tuple[dict[str, Any], dict[str, int]]:
    """Une qualité en service (recette complète) ou arrêtée, et ses matières."""
    poil, trame = matiere(), matiere(role="Trame")
    q = creer_qualite(direction, poids_m2={"Poil": 1, "Trame": 1}, parts={poil: 100, trame: 100})
    if etat == "arretee":
        q = ok(direction.put(f"/api/qualites/{q['id']}", json=corps_fiche(q, actif=False)))
    return q, {"poil": poil, "trame": trame}


GESTES_QUALITE: dict[str, Geste] = {
    "plan_change": lambda q, m: (
        "PUT",
        f"/api/qualites/{q['id']}/plan",
        {"base_mensuelle": 700, "coefficients": UN, "version": q["version"]},
    ),
    "plan_renvoye": lambda q, m: (
        "PUT",
        f"/api/qualites/{q['id']}/plan",
        {"base_mensuelle": 0, "coefficients": UN, "version": q["version"]},
    ),
    "recette_incomplete": lambda q, m: (
        "PUT",
        f"/api/qualites/{q['id']}/recette",
        {"lignes": lignes({m["poil"]: 100}), "version": q["version"]},
    ),
    "recette_fausse": lambda q, m: (
        "PUT",
        f"/api/qualites/{q['id']}/recette",
        {"lignes": lignes({m["poil"]: 100, m["trame"]: 90}), "version": q["version"]},
    ),
    "renommer": lambda q, m: ("PUT", f"/api/qualites/{q['id']}", corps_fiche(q, nom="R")),
    "basculer": lambda q, m: (
        "PUT",
        f"/api/qualites/{q['id']}",
        corps_fiche(q, actif=not q["actif"]),
    ),
    "supprimer": lambda q, m: ("DELETE", f"/api/qualites/{q['id']}?version={q['version']}", {}),
}

ATTENDU_QUALITE: dict[tuple[str, str], int] = {
    ("en_service", "plan_change"): 200,
    ("arretee", "plan_change"): 409,
    ("en_service", "plan_renvoye"): 200,
    ("arretee", "plan_renvoye"): 200,
    ("en_service", "recette_incomplete"): 422,
    ("arretee", "recette_incomplete"): 200,
    ("en_service", "recette_fausse"): 422,
    ("arretee", "recette_fausse"): 422,
    ("en_service", "renommer"): 200,
    ("arretee", "renommer"): 200,
    ("en_service", "basculer"): 200,
    ("arretee", "basculer"): 200,
    ("en_service", "supprimer"): 204,
    ("arretee", "supprimer"): 204,
}
"""Pour la direction ; les achats et l'alimentation reçoivent 403 sur chaque geste."""


def _appel(client: TestClient, methode: str, url: str, corps: dict[str, Any]) -> int:
    if methode == "DELETE":
        return client.delete(url).status_code
    return client.request(methode, url, json=corps).status_code


@pytest.mark.parametrize(("etat", "geste"), sorted(ATTENDU_QUALITE))
@pytest.mark.parametrize("role", ["direction", "achats", "alimentation"])
def test_table_des_transitions_d_une_qualite(
    etat: str, geste: str, role: str, request: pytest.FixtureRequest, direction: TestClient
) -> None:
    """État × geste × rôle → code, rejoué pour chaque case."""
    q, m = _qualite(direction, etat)
    client: TestClient = request.getfixturevalue(role)
    attendu = ATTENDU_QUALITE[(etat, geste)] if role == "direction" else 403
    assert _appel(client, *GESTES_QUALITE[geste](q, m)) == attendu
    if attendu >= 400:  # un refus n'a rien écrit
        assert lire_qualite(direction, q["id"])["version"] == q["version"]


def _metier(direction: TestClient, alimentation: TestClient, etat: str) -> tuple[dict, int]:
    """Un métier dont l'étage 1 porte 2 m de fil (1 kg/bobine, 10 bobines/m), en service ou
    arrêté."""
    poil = matiere(poids_bobine="1")
    x = creer_metier(direction)
    x = ok(
        alimentation.put(
            f"/api/metiers/{x['id']}/etages/1",
            json={
                "version": 1,
                "fils": [{"matiere_id": poil, "metres": 2}],
                "confirme_effet_kg": 20,
            },
        )
    )["metier"]
    if etat == "arrete":
        cles = ("code", "nom", "laize", "bobines_par_metre", "etages", "commentaire", "version")
        x = ok(
            direction.put(
                f"/api/metiers/{x['id']}", json={k: x[k] for k in cles} | {"actif": False}
            )
        )
    return x, poil


def _monter(x: dict, poil: int, metres: float, effet: float) -> tuple[str, str, dict]:
    return (
        "PUT",
        f"/api/metiers/{x['id']}/etages/1",
        {
            "version": version_etage(x, 1),
            "fils": [{"matiere_id": poil, "metres": metres}],
            "confirme_effet_kg": effet,
        },
    )


GESTES_METIER: dict[str, Callable[[dict, int], tuple[str, str, dict]]] = {
    "monter_plus": lambda x, p: _monter(x, p, 3, 10 if x["actif"] else 0),
    "demonter": lambda x, p: _monter(x, p, 1, -10 if x["actif"] else 0),
    "regler": lambda x, p: (
        "PUT",
        f"/api/metiers/{x['id']}",
        {
            k: x[k]
            for k in ("code", "nom", "laize", "bobines_par_metre", "etages", "actif", "version")
        }
        | {"commentaire": "r"},
    ),
    "supprimer": lambda x, p: ("DELETE", f"/api/metiers/{x['id']}?version={x['version']}", {}),
}

ATTENDU_METIER: dict[tuple[str, str, str], int] = {
    **{
        (e, "monter_plus", r): c
        for e, r, c in (
            ("en_service", "direction", 200),
            ("en_service", "alimentation", 200),
            ("arrete", "direction", 409),
            ("arrete", "alimentation", 409),
        )
    },
    **{
        (e, "demonter", r): 200
        for e in ("en_service", "arrete")
        for r in ("direction", "alimentation")
    },
    **{(e, "regler", "direction"): 200 for e in ("en_service", "arrete")},
    **{(e, "supprimer", "direction"): 409 for e in ("en_service", "arrete")},
}
"""Les cases absentes valent 403 (achats partout ; alimentation sur le réglage)."""


@pytest.mark.parametrize("etat", ["en_service", "arrete"])
@pytest.mark.parametrize("geste", sorted(GESTES_METIER))
@pytest.mark.parametrize("role", ["direction", "achats", "alimentation"])
def test_table_des_transitions_d_un_metier(
    etat: str,
    geste: str,
    role: str,
    *,
    request: pytest.FixtureRequest,
    direction: TestClient,
    alimentation: TestClient,
) -> None:
    """État × geste × rôle → code, rejoué pour chaque case."""
    x, poil = _metier(direction, alimentation, etat)
    client: TestClient = request.getfixturevalue(role)
    assert _appel(client, *GESTES_METIER[geste](x, poil)) == ATTENDU_METIER.get(
        (etat, geste, role), 403
    )


def _toutes_perimees(client: TestClient, ecritures: list[tuple[str, str, dict]]) -> None:
    """Chaque écriture, à une version périmée, reçoit 409 `conflit_version`."""
    for methode, url, corps in ecritures:
        if methode == "DELETE":
            r = client.delete(url)
        else:
            r = client.request(methode, url, json=corps)
        assert r.status_code == 409 and r.json()["code"] == "conflit_version", (url, r.text)


def test_version_perimee_sur_chaque_ecriture_d_une_qualite(direction: TestClient) -> None:
    """Routes 85, 86, 87, 89, 90, 146 : une version périmée est refusée (409)."""
    q, m = _qualite(direction, "en_service")
    v0, qid = q["version"], q["id"]
    ok(direction.put(f"/api/qualites/{qid}", json=corps_fiche(q, nom="Avance")))
    vid = ok(direction.get(f"/api/qualites/{qid}/versions"))[-1]["id"]
    plan = {"base_mensuelle": 1, "coefficients": UN, "version": v0}
    _toutes_perimees(
        direction,
        [
            ("PUT", f"/api/qualites/{qid}", corps_fiche(q, version=v0)),
            ("PUT", f"/api/qualites/{qid}/recette",
             {"lignes": lignes({m["poil"]: 100, m["trame"]: 100}), "version": v0}),
            ("POST", f"/api/qualites/{qid}/versions/{vid}/restaurer",
             {"motif": "x", "version": v0}),
            ("PUT", f"/api/qualites/{qid}/plan", plan),
            ("PUT", "/api/production/plan", {"qualites": [plan | {"qualite_id": qid}]}),
            ("DELETE", f"/api/qualites/{qid}?version={v0}", {}),
        ],
    )  # fmt: skip
    assert lire_qualite(direction, qid)["nom"] == "Avance"


def test_version_perimee_sur_chaque_ecriture_d_un_metier(
    direction: TestClient, alimentation: TestClient
) -> None:
    """Routes 97–100 : une version de métier ou d'étage périmée est refusée (409)."""
    x, poil = _metier(direction, alimentation, "en_service")
    cles = ("code", "nom", "laize", "bobines_par_metre", "etages", "actif", "commentaire")
    reglage = {k: x[k] for k in cles} | {"version": x["version"]}
    ok(direction.put(f"/api/metiers/{x['id']}", json=reglage | {"commentaire": "avance"}))
    fil = [{"matiere_id": poil, "metres": 1}]
    etage = {"version": 1, "fils": fil, "confirme_effet_kg": 10}
    ok(alimentation.put(f"/api/metiers/{x['id']}/etages/2", json=etage))
    _toutes_perimees(
        direction,
        [
            ("PUT", f"/api/metiers/{x['id']}", reglage),
            ("DELETE", f"/api/metiers/{x['id']}?version={x['version']}", {}),
            ("PUT", f"/api/metiers/{x['id']}/etages/2", etage | {"confirme_effet_kg": 0}),
            ("PUT", f"/api/metiers/{x['id']}/montage",
             {"etages": [{"etage": 2, "version": 1, "fils": fil}], "confirme_effet_kg": 0}),
        ],
    )  # fmt: skip
    assert lire_metier(direction, x["id"])["poids"] == 30


def test_deux_postes_en_meme_temps_sur_le_meme_etage(
    direction: TestClient, alimentation: TestClient
) -> None:
    """Deux postes qui montent le même étage au même instant, à la même version lue : un seul
    passe, l'autre reçoit 409 ; rejoué 10 fois."""
    poil = matiere(poids_bobine="1")
    x = creer_metier(direction)
    for i in range(10):
        lu = lire_metier(direction, x["id"])
        version, avant = version_etage(lu, 1), lu["poids"]
        depart = threading.Barrier(2)
        codes: list[int] = []
        metres = 1 + i % 3

        corps = {
            "version": version,
            "fils": [{"matiere_id": poil, "metres": metres}],
            "confirme_effet_kg": metres * 10 - avant,
        }

        def monter(
            client: TestClient,
            corps: dict[str, Any] = corps,
            depart: threading.Barrier = depart,
            codes: list[int] = codes,
        ) -> None:
            depart.wait()
            codes.append(client.put(f"/api/metiers/{x['id']}/etages/1", json=corps).status_code)

        fils = [threading.Thread(target=monter, args=(c,)) for c in (direction, alimentation)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        assert sorted(codes) == [200, 409], codes
        assert lire_metier(direction, x["id"])["poids"] == metres * 10
