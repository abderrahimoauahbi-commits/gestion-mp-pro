"""Pagination par curseur de la liste des ordres (route 135), son aperçu (135bis) et l'accès
borné (135ter) : l'union des pages est exactement la liste entière (mêmes id, même ordre date
puis n° d'entrée, sans doublon ni saut), le total est celui de tout le filtre, les comptes par
onglet suivent la période, les agrégats du moteur (sorti net, revenu, prévu, sorti selon recette)
sont exacts, et la recherche et les filtres (statut, qualité) sont poussés au serveur.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.ordres import JOUR, Atelier, atelier
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles.enums import Role

HIER = JOUR - timedelta(days=1)
MARQUE = "PAG3MARQUE"


@pytest.fixture(scope="module")
def alimentation(application: FastAPI) -> TestClient:
    """Un poste d'alimentation partagé par le module (les ordres créés y restent)."""
    return client_de(application, Role.alimentation)


@pytest.fixture(scope="module")
def a() -> Atelier:
    """Le décor (matières, qualités, magasin propre), validé en base une fois."""
    with fabrique()() as s:
        decor = atelier(s)
        s.commit()
    return decor


def _ok(r: Any, code: int = 200) -> Any:
    assert r.status_code == code, r.text
    return r.json() if r.content else None


def _corps(a: Atelier, kg: float, qualites: list[tuple[int, float]], le: object) -> dict:
    return {
        "date": str(le),
        "magasin_id": a.m.courant.id,
        "commentaire": MARQUE,
        "qualites": [{"qualite_id": q, "m2": m2} for q, m2 in qualites],
        "lignes": [{"lot_id": a.lot("E-L1").id, "quantite": kg}],
    }


def _creer(c: TestClient, a: Atelier, kg: float, qualites: list, le: object) -> dict:
    return _ok(c.post("/api/ordres", json=_corps(a, kg, qualites, le)), 201)


def _valider(c: TestClient, o: dict) -> dict:
    return _ok(c.post(f"/api/ordres/{o['id']}/valider", json={"version": o["version"]}))


def _page(c: TestClient, **params: object) -> dict:
    return _ok(c.get("/api/ordres", params=params))


def _toutes(c: TestClient, **filtres: object) -> list[dict]:
    """L'union des pages, curseur suivi, limite 2 pour forcer plusieurs pages."""
    elements: list[dict] = []
    apres: str | None = None
    while True:
        page = _page(c, limite=2, apres=apres, **filtres)
        elements += page["elements"]
        apres = page["suivant"]
        if not apres:
            return elements


@pytest.fixture(scope="module")
def jeu(a: Atelier, alimentation: TestClient) -> dict:
    """Trois ordres validés (aujourd'hui) et un brouillon (hier), tous marqués."""
    v1 = _valider(alimentation, _creer(alimentation, a, 50, [(a.e1, 40)], JOUR))
    v2 = _valider(alimentation, _creer(alimentation, a, 30, [(a.e1, 20)], JOUR))
    v3 = _valider(alimentation, _creer(alimentation, a, 10, [(a.e1, 5)], JOUR))
    b1 = _creer(alimentation, a, 5, [(a.e1, 2)], HIER)
    return {"v1": v1, "v2": v2, "v3": v3, "b1": b1}


def test_union_des_pages_egale_la_liste_entiere(alimentation: TestClient, jeu: dict) -> None:
    """Union des pages (curseur) = la liste d'un coup : mêmes id, même ordre, sans doublon."""
    entiere = _page(alimentation, q=MARQUE, limite=5000)["elements"]
    ids = [x["id"] for x in entiere]
    union = [x["id"] for x in _toutes(alimentation, q=MARQUE)]
    assert union == ids
    assert len(union) == len(set(union))
    cles = [(x["date"], x["id"]) for x in entiere]
    assert cles == sorted(cles, reverse=True)  # date puis n° d'entrée décroissants


def test_total_et_curseur(alimentation: TestClient, jeu: dict) -> None:
    """Le total est celui du filtre entier ; la dernière page n'a pas de `suivant`."""
    premiere = _page(alimentation, q=MARQUE, limite=2)
    assert premiere["total"] == 4 and premiere["suivant"] and len(premiere["elements"]) == 2
    derniere = _page(alimentation, q=MARQUE, limite=5000)
    assert derniere["suivant"] is None and derniere["total"] == 4


def test_comptes_par_onglet(alimentation: TestClient, jeu: dict) -> None:
    """Les comptes d'onglet de l'aperçu (sur la période) égalent les totaux des pages par statut."""
    apercu = _ok(alimentation.get("/api/ordres/apercu"))
    assert apercu["valide"] == _page(alimentation, statut="valide", limite=5000)["total"]
    assert apercu["brouillon"] == _page(alimentation, statut="brouillon", limite=5000)["total"]
    assert apercu["annule"] == _page(alimentation, statut="annule", limite=5000)["total"]


def test_agregats_du_moteur(alimentation: TestClient, jeu: dict) -> None:
    """Les agrégats de l'aperçu (net, revenu, prévu, sorti) somment les ordres affichés."""
    valides = _page(alimentation, statut="valide", q=MARQUE, limite=5000)["elements"]
    apercu = _ok(alimentation.get("/api/ordres/apercu", params={"statut": "valide", "q": MARQUE}))
    assert apercu["net"] == pytest.approx(sum(x["net"] for x in valides))
    assert apercu["revenu"] == pytest.approx(sum(x["revenu"] for x in valides))
    avec = [x for x in valides if x["prevu"]]
    assert apercu["prevu"] == pytest.approx(sum(x["prevu"] for x in avec))
    assert apercu["sorti"] == pytest.approx(sum(x["net"] for x in avec))
    brouillons = _page(alimentation, statut="brouillon", q=MARQUE, limite=5000)["elements"]
    apercu_b = _ok(
        alimentation.get("/api/ordres/apercu", params={"statut": "brouillon", "q": MARQUE})
    )
    assert apercu_b["net"] == pytest.approx(sum(x["total"] for x in brouillons))


def test_recherche_et_filtres_au_serveur(alimentation: TestClient, jeu: dict) -> None:
    """La recherche (commentaire marqué) et les filtres (statut, qualité) filtrent au serveur."""
    marques = _page(alimentation, q=MARQUE, limite=5000)["elements"]
    assert {x["id"] for x in marques} == {jeu[k]["id"] for k in ("v1", "v2", "v3", "b1")}
    valides = _page(alimentation, statut="valide", q=MARQUE, limite=5000)["elements"]
    assert all(x["statut"] == "valide" for x in valides) and len(valides) == 3
    qid = jeu["v1"]["qualites"][0]["qualite_id"]
    par_qualite = _page(alimentation, qualite=qid, q=MARQUE, limite=5000)["elements"]
    assert all(any(q["qualite_id"] == qid for q in x["qualites"]) for x in par_qualite)


def test_acces_borne_ouverts(alimentation: TestClient, jeu: dict) -> None:
    """L'accès borné 135ter rend la liste entière d'un statut (ici les validés marqués)."""
    ouverts = _ok(alimentation.get("/api/ordres/ouverts", params={"statut": "valide", "q": MARQUE}))
    assert isinstance(ouverts, list)
    assert {jeu[k]["id"] for k in ("v1", "v2", "v3")} <= {x["id"] for x in ouverts}
