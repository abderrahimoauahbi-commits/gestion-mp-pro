"""Pagination par curseur de la liste des réceptions (route 167) et son aperçu (181b) : l'union
des pages est exactement l'ancienne liste complète (mêmes id, même ordre, sans doublon ni saut),
le total et le pesé de l'onglet sont ceux de tout le filtre, les comptes par onglet suivent la
recherche, et les filtres liés (fournisseur, origine, facture, qualité) filtrent au serveur.
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.achats import Achat
from fabriques.receptions import Quai, camion, geste, ok, recevoir
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.modeles.enums import Role


@pytest.fixture(scope="module")
def poste(application: FastAPI) -> TestClient:
    """Un poste des achats partagé par le module (les réceptions créées y restent)."""
    return client_de(application, Role.achats)


@pytest.fixture(scope="module")
def decor() -> dict:
    """Deux fournisseurs et deux matières, un quai."""
    a = Achat.nouveau(devise="MAD", nom="Filature du Nord")
    autre = Achat.nouveau(devise="MAD", nom="Comptoir du Sud")
    m1 = a.matiere("PAG BLEU")
    m2 = a.matiere("PAG VERT")
    return {"a": a, "autre": autre, "m1": m1, "m2": m2, "quai": Quai.nouveau()}


def _ligne(d: dict, m: str, lot: str, kg: float, **x: object) -> dict:
    return {"matiere_id": d[m], "lot_numero": lot, "quantite_pesee": kg,
            "magasin_id": d["quai"].courant, **x}  # fmt: skip


def _page(c: TestClient, **params: object) -> dict:
    return ok(c.get("/api/receptions", params=params))  # type: ignore[no-any-return]


def _toutes(c: TestClient, **filtres: object) -> list[dict]:
    """L'union des pages, en suivant le curseur (limite petite pour forcer plusieurs pages)."""
    elements: list[dict] = []
    apres: str | None = None
    while True:
        page = _page(c, limite=2, apres=apres, **filtres)
        elements += page["elements"]
        apres = page["suivant"]
        if not apres:
            return elements


@pytest.fixture(scope="module")
def jeu(poste: TestClient, decor: dict) -> dict:
    """Sept réceptions variées (validées, brouillons, une annulée, deux fournisseurs)."""
    a, autre = decor["a"], decor["autre"]
    v1 = recevoir(poste, a.fournisseur_id, [_ligne(decor, "m1", "PA-1", 10)], numero_bl="BL-A1")
    v2 = recevoir(poste, a.fournisseur_id, [_ligne(decor, "m2", "PA-2", 20)])
    v3 = recevoir(poste, autre.fournisseur_id, [_ligne(decor, "m1", "PA-3", 30)])
    an = recevoir(poste, a.fournisseur_id, [_ligne(decor, "m1", "PA-4", 5)])
    geste(poste, an, "annuler", motif="erreur de saisie")
    b1 = camion(poste, a.fournisseur_id, [_ligne(decor, "m2", "PA-5", 7)])
    b2 = camion(poste, autre.fournisseur_id, [_ligne(decor, "m1", "PA-6", 8)])
    res = recevoir(poste, a.fournisseur_id, [_ligne(decor, "m2", "PA-7", 9, qualite="reserve")])
    return {"v1": v1, "v2": v2, "v3": v3, "an": an, "b1": b1, "b2": b2, "res": res}


def test_union_des_pages_egale_la_liste_entiere(poste: TestClient, jeu: dict) -> None:
    """Union des pages (curseur) = la liste d'un seul coup : mêmes id, même ordre, sans doublon."""
    entiere = _page(poste, limite=5000)["elements"]
    ids_entiers = [x["id"] for x in entiere]
    union = [x["id"] for x in _toutes(poste)]
    assert union == ids_entiers
    assert len(union) == len(set(union))  # aucun doublon, aucun saut
    assert ids_entiers == sorted(ids_entiers, reverse=True)  # la plus récente d'abord


def test_total_et_curseur(poste: TestClient, jeu: dict) -> None:
    """Le total est celui de tout le filtre ; la dernière page n'a pas de `suivant`."""
    premiere = _page(poste, limite=2)
    assert premiere["total"] >= 7
    assert premiere["suivant"] and len(premiere["elements"]) == 2
    derniere = _page(poste, limite=5000)
    assert derniere["suivant"] is None
    assert derniere["total"] == len(derniere["elements"])


def test_comptes_par_onglet_et_pese_total(poste: TestClient, jeu: dict) -> None:
    """Les pages par statut totalisent l'aperçu ; le pesé de l'onglet suit tout le filtre."""
    apercu = ok(poste.get("/api/receptions/apercu"))
    val = _page(poste, statut="validee", limite=5000)
    assert apercu["validee"] == val["total"]
    assert apercu["brouillon"] == _page(poste, statut="brouillon", limite=5000)["total"]
    assert apercu["annulee"] == _page(poste, statut="annulee", limite=5000)["total"]
    assert apercu["total"] == apercu["validee"] + apercu["brouillon"] + apercu["annulee"]
    assert val["pese_total"] == pytest.approx(sum(x["pese"] for x in val["elements"]))


def test_filtres_lies_au_serveur(poste: TestClient, decor: dict, jeu: dict) -> None:
    """Fournisseur, origine (bon), facture et qualité filtrent au serveur, comme à l'écran."""
    sud = decor["autre"].fournisseur_id
    page = _page(poste, fournisseur=sud, limite=5000)
    assert {x["fournisseur_id"] for x in page["elements"]} == {sud}
    reserve = _page(poste, qualite="reserve", statut="validee", limite=5000)["elements"]
    assert jeu["res"]["id"] in {x["id"] for x in reserve}
    assert all(x["nb_reserve"] and not x["nb_refus"] for x in reserve)
    hors = _page(poste, origine="hors", limite=5000)["elements"]
    assert all(not x["commandes"] for x in hors)


def test_recherche_suit_tous_les_champs(poste: TestClient, jeu: dict) -> None:
    """La recherche porte sur le n°, le BL, le lot et le motif d'annulation (tous onglets)."""
    par_lot = _page(poste, q="PA-3", limite=5000)["elements"]
    assert [x["id"] for x in par_lot] == [jeu["v3"]["id"]]
    par_bl = _page(poste, q="bl-a1", limite=5000)["elements"]
    assert [x["id"] for x in par_bl] == [jeu["v1"]["id"]]
    par_motif = _page(poste, q="erreur de saisie", limite=5000)["elements"]
    assert jeu["an"]["id"] in {x["id"] for x in par_motif}
    apercu = ok(poste.get("/api/receptions/apercu", params={"q": "PA-3"}))
    assert apercu["total"] == 1
