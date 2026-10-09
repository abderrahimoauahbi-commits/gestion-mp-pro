"""Routes des ordres de fabrication (lot D6 ; API-PRO 134–144) et leur place dans « À valider »
(122, 123). Les données sont validées en base, à des noms uniques ; les ordres sont datés
d'aujourd'hui (aucun ordre laissé par un autre essai ne les refuse) et les brouillons qui
restent sont supprimés à la fin de chaque essai.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from io import BytesIO
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.ordres import JOUR, Atelier, atelier
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from test_prix_masques import fuites

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Ordre
from gestion_mp_pro.modeles.enums import StatutOrdre

HIER = JOUR - timedelta(days=1)


@pytest.fixture
def a(direction: TestClient) -> Iterator[Atelier]:
    """Le décor, validé en base ; ses brouillons d'ordres sont supprimés à la fin."""
    with fabrique()() as s:
        decor = atelier(s)
        s.commit()
    yield decor
    with fabrique()() as s:
        restes = s.execute(
            select(Ordre.id, Ordre.version).where(
                Ordre.statut == StatutOrdre.brouillon, Ordre.magasin_id == decor.m.courant.id
            )
        ).all()
    for ident, version in restes:
        direction.delete(f"/api/ordres/{ident}", params={"version": version})


def _ok(r: Any, code: int = 200) -> Any:
    assert r.status_code == code, r.text
    return r.json() if r.content else None


def _corps(a: Atelier, *lignes: tuple[str, float], qualites: list[tuple[int, float]] | None = None,
           le: object = JOUR, **champs: Any) -> dict[str, Any]:  # fmt: skip
    return {
        "date": str(le),
        "magasin_id": a.m.courant.id,
        "qualites": [{"qualite_id": q, "m2": m2} for q, m2 in qualites or []],
        "lignes": [{"lot_id": a.lot(n).id, "quantite": q} for n, q in lignes],
        **champs,
    }


def test_parcours_d_un_ordre_par_l_api(a: Atelier, alimentation: TestClient) -> None:
    """Proposer, garder en brouillon, modifier, valider, lire (liste, fiche, lots sortis,
    consommation, classeurs), annuler : la réponse dit ce qui a été fait."""
    p = _ok(alimentation.post("/api/ordres/proposition", json={
        "magasin_id": a.m.courant.id, "qualites": [{"qualite_id": a.e1, "m2": 100}]}))  # fmt: skip
    poil = next(x for x in p["lignes"] if x["matiere_id"] == a.m.a1.id)
    assert poil["prevu"] == 102 and p["taux_perte"] == 0.02 and p["blocages"] == []
    o = _ok(
        alimentation.post("/api/ordres", json=_corps(a, ("E-L1", 50), qualites=[(a.e1, 40)])), 201
    )
    assert o["numero"] is None and o["statut"] == "brouillon" and o["fabrication"].endswith("40 m²")
    corps = _corps(a, ("E-L1", 40), ("E-T1", 20), qualites=[(a.e1, 40)], commentaire="équipe B")
    o = _ok(alimentation.put(f"/api/ordres/{o['id']}", json={**corps, "version": o["version"]}))
    assert o["total"] == 60 and o["commentaire"] == "équipe B"
    o = _ok(alimentation.post(f"/api/ordres/{o['id']}/valider", json={"version": o["version"]}))
    assert o["numero"].startswith("OF-2026-") and o["message"].startswith(f"Ordre {o['numero']}")
    assert o["prevu"] == pytest.approx(40 * 1.5 * 1.02) and o["net"] == 60
    assert {x["reference"] for x in o["par_matiere"]} == {a.m.a1.reference, a.m.a2.reference}
    liste = _ok(alimentation.get("/api/ordres", params={"q": o["numero"]}))["elements"]
    assert [x["id"] for x in liste] == [o["id"]] and "lignes" not in liste[0]
    sortis = _ok(alimentation.get(f"/api/ordres/{o['id']}/lots-sortis"))
    assert sorted(x["sorti_net"] for x in sortis) == [20, 40]
    conso = _ok(alimentation.get("/api/ordres/consommation", params={"qualite": a.e1}))
    assert [x["numero"] for x in conso] == [o["numero"]] and conso[0]["net"] == 60
    for vue in ("ordres", "consommation"):
        r = alimentation.get(
            "/api/export/ordres", params={"q": o["numero"], "vue": vue, "qualite": a.e1}
        )
        lignes = list(load_workbook(BytesIO(r.content)).active.iter_rows(values_only=True))  # type: ignore[union-attr]
        assert r.status_code == 200 and any(o["numero"] in x for x in lignes)
    o = _ok(alimentation.post(f"/api/ordres/{o['id']}/annuler",
                              json={"version": o["version"], "motif": "erreur"}))  # fmt: skip
    assert o["statut"] == "annule" and "revenue en stock" in o["message"] and o["net"] == 0
    assert _ok(alimentation.get("/api/ordres/consommation", params={"qualite": a.e1})) == []


def test_droits_et_refus(a: Atelier, achats: TestClient, alimentation: TestClient) -> None:
    """Les achats lisent, n'écrivent pas (P44) ; 404 « Ordre introuvable. » ; un corps faux est
    un 422 traduit, jamais un 500 (NaN, quantité nulle, champ inconnu)."""
    assert achats.post("/api/ordres", json=_corps(a, ("E-L1", 1))).status_code == 403
    assert achats.get("/api/ordres", params={"statut": "valide"}).status_code == 200
    r = alimentation.get("/api/ordres/999999")
    assert r.status_code == 404 and r.json()["detail"] == "Ordre introuvable."
    assert alimentation.get("/api/ordres/999999/lots-sortis").status_code == 404
    for faux in ({"quantite": "NaN"}, {"quantite": 0}, {"inconnu": 1}):
        corps = _corps(a, ("E-L1", 1))
        corps["lignes"][0] |= faux
        assert alimentation.post("/api/ordres", json=corps).status_code == 422
    r = alimentation.get("/api/ordres", params={"du": str(JOUR), "au": str(HIER)})
    assert r.status_code == 422


def test_version_perimee_sur_chaque_ecriture(a: Atelier, alimentation: TestClient) -> None:
    """Modifier, supprimer, valider, annuler à une version périmée : 409 `conflit_version`."""
    o = _ok(alimentation.post("/api/ordres", json=_corps(a, ("E-L1", 1))), 201)
    vieux = o["version"]
    o = _ok(
        alimentation.put(
            f"/api/ordres/{o['id']}", json={**_corps(a, ("E-L1", 2)), "version": vieux}
        )
    )
    gestes = [
        ("PUT", f"/api/ordres/{o['id']}", {"json": {**_corps(a, ("E-L1", 3)), "version": vieux}}),
        ("DELETE", f"/api/ordres/{o['id']}", {"params": {"version": vieux}}),
        ("POST", f"/api/ordres/{o['id']}/valider", {"json": {"version": vieux}}),
    ]
    for methode, url, options in gestes:
        r = alimentation.request(methode, url, **options)
        assert r.status_code == 409 and r.json()["code"] == "conflit_version", (methode, url)
    o = _ok(alimentation.post(f"/api/ordres/{o['id']}/valider", json={"version": o["version"]}))
    r = alimentation.post(f"/api/ordres/{o['id']}/annuler", json={"version": vieux})
    assert r.json()["code"] == "conflit_version"
    _ok(alimentation.post(f"/api/ordres/{o['id']}/annuler", json={"version": o["version"]}))


def test_aucun_prix_pour_l_alimentation(a: Atelier, alimentation: TestClient) -> None:
    """Balayage des routes GET du lot (et de la proposition) en rôle alimentation : aucune clé
    monétaire ne porte de valeur."""
    o = _ok(
        alimentation.post("/api/ordres", json=_corps(a, ("E-L1", 2), qualites=[(a.e1, 1)])), 201
    )
    o = _ok(alimentation.post(f"/api/ordres/{o['id']}/valider", json={"version": o["version"]}))
    reponses = [
        alimentation.get("/api/ordres"),
        alimentation.get(f"/api/ordres/{o['id']}"),
        alimentation.get(f"/api/ordres/{o['id']}/lots-sortis"),
        alimentation.get("/api/ordres/consommation"),
        alimentation.post("/api/ordres/proposition", json={
            "magasin_id": a.m.courant.id, "qualites": [{"qualite_id": a.e1, "m2": 5}]}),
    ]  # fmt: skip
    lus = [_ok(r) for r in reponses]
    assert fuites(lus) == []


def test_brouillons_a_valider_et_tout_valider(
    a: Atelier, achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : test_stock_atelier::test_brouillons_a_valider_et_tout_valider (partie ordres) —
    les ordres en brouillon sont dans « À valider » avec leurs blocages ; les achats ne les
    valident pas (`ignores`, raison) ; « Tout valider » : l'ordre d'hier est refusé (« date
    antérieure »), l'ordre trop grand aussi (« seulement »), le bon passe ; les refusés restent
    brouillons."""
    du_jour = _ok(alimentation.post("/api/ordres", json=_corps(a, ("E-T1", 1))), 201)
    _ok(
        alimentation.post(
            f"/api/ordres/{du_jour['id']}/valider", json={"version": du_jour["version"]}
        )
    )
    hier = _ok(alimentation.post("/api/ordres", json=_corps(a, ("E-T1", 1), le=HIER)), 201)
    trop = _ok(alimentation.post("/api/ordres", json=_corps(a, ("E-T1", 100000))), 201)
    bon = _ok(
        alimentation.post("/api/ordres", json=_corps(a, ("E-L1", 3), qualites=[(a.e1, 2)])), 201
    )
    liste = _ok(achats.get("/api/brouillons"))
    vus = {x["id"]: x for x in liste["ordres"]}
    assert {hier["id"], trop["id"], bon["id"]} <= set(vus)
    assert any("est déjà validé" in x for x in vus[hier["id"]]["blocages"])
    assert any("seulement" in x for x in vus[trop["id"]]["blocages"])
    assert not vus[bon["id"]]["peut_valider"] and vus[bon["id"]]["lien"] == f"/ordres/{bon['id']}"
    choix = [{"genre": "ordre", "id": x["id"]} for x in (hier, trop, bon)]
    r = _ok(achats.post("/api/brouillons/valider", json={"documents": choix}))
    assert sorted(x["id"] for x in r["ignores"]) == sorted(x["id"] for x in (hier, trop, bon))
    r = _ok(alimentation.post("/api/brouillons/valider", json={"documents": choix}))
    assert [x["id"] for x in r["valides"]] == [bon["id"]] and r["valides"][0]["numero"].startswith(
        "OF-"
    )
    raisons = {x["id"]: x["raison"] for x in r["refuses"]}
    assert "date antérieure" in raisons[hier["id"]] and "seulement" in raisons[trop["id"]]
    for x in (hier, trop):
        assert _ok(alimentation.get(f"/api/ordres/{x['id']}"))["statut"] == "brouillon"
