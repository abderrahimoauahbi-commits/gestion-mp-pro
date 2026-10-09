"""Pagination par curseur de la liste des dossiers (route 187), son aperçu (250) et sa recherche
poussée en SQL : l'union des pages est exactement la liste entière (mêmes id, même ordre date
d'arrivée puis id, sans date à la fin, sans doublon ni saut), le total et les agrégats (indicateurs,
pied, non répartis) sont ceux de tout le filtre, et la recherche SQL rend **exactement** le même
ensemble que l'ancienne recherche Python (`recherche.trouve` sur les mêmes champs, ponctuation
comprise).
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.importations import Import, a_la_main, geste, ouvrir
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Dossier
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.services import recherche
from gestion_mp_pro.services.importations import lecture
from gestion_mp_pro.services.importations.lecture import FiltresDossiers


@pytest.fixture(scope="module")
def achats(application: FastAPI) -> TestClient:
    """Un poste des achats partagé par le module (les dossiers créés y restent)."""
    return client_de(application, Role.achats)


def _ok(r: Any, code: int = 200) -> Any:
    assert r.status_code == code, r.text
    return r.json() if r.content else None


def _page(c: TestClient, **params: object) -> dict:
    return _ok(c.get("/api/dossiers", params=params))


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
def jeu(achats: TestClient) -> dict:
    """Plusieurs dossiers : trois ouverts par facture (un clos), deux à la main (un sans date)."""
    imp = Import.nouveau(pays="TURKEY")
    imp.recevoir(achats, "PAG3/99/117", [("PP FRZ-2900 Rouge", "L-R-1", 100, 10)])
    imp.recevoir(achats, "PAG3/99/118", [("PP FRZ-2900 Bleu", "L-B-1", 200, 11)])
    imp.recevoir(achats, "PAG3/99/119", [("PA Lisse 1100 Vert", "L-V-1", 300, 12)])
    d1 = ouvrir(achats, imp.f("PAG3/99/117"), libelle="Camion janvier")
    d2 = ouvrir(achats, imp.f("PAG3/99/118"), libelle="Camion février")
    d3 = ouvrir(achats, imp.f("PAG3/99/119"), libelle="Camion mars")
    d3 = geste(achats, d3, "cloturer", alertes_lues=True)
    main = a_la_main(achats, libelle="Reprise ancienne", banque="BMCE")
    return {"imp": imp, "d1": d1, "d2": d2, "d3": d3, "main": main}


def test_union_des_pages_egale_la_liste_entiere(achats: TestClient, jeu: dict) -> None:
    """Union des pages (curseur) = la liste d'un coup : mêmes id, même ordre, sans doublon."""
    entiere = _page(achats, limite=5000)["elements"]
    ids = [x["id"] for x in entiere]
    union = [x["id"] for x in _toutes(achats)]
    assert union == ids
    assert len(union) == len(set(union))
    cles = [(x["date_arrivee"] is not None, x["date_arrivee"] or "", x["id"]) for x in entiere]
    assert cles == sorted(cles, reverse=True)  # date d'arrivée desc, sans date à la fin, puis id


def test_total_et_curseur(achats: TestClient, jeu: dict) -> None:
    """Le total est celui du filtre entier ; la dernière page n'a pas de `suivant`."""
    premiere = _page(achats, limite=2)
    assert premiere["total"] >= 4 and premiere["suivant"] and len(premiere["elements"]) == 2
    derniere = _page(achats, limite=5000)
    assert derniere["suivant"] is None and derniere["total"] == len(derniere["elements"])


def test_apercu_comptes_totaux_et_non_repartis(achats: TestClient, jeu: dict) -> None:
    """L'aperçu : comptes par statut, totaux (indicateurs/pied) et non répartis = la liste."""
    apercu = _ok(achats.get("/api/dossiers/apercu"))
    entiere = _page(achats, limite=5000)["elements"]
    assert apercu["nombre"] == len(entiere)
    assert apercu["ouvert"] == sum(1 for d in entiere if d["statut"] == "ouvert")
    assert apercu["clos"] == sum(1 for d in entiere if d["statut"] == "clos")
    assert apercu["marchandise_mad"] == pytest.approx(sum(d["marchandise_mad"] for d in entiere))
    assert apercu["revient_mad"] == pytest.approx(sum(d["revient_mad"] for d in entiere))
    attendus = {d["id"] for d in entiere if abs(d["charges_non_reparties_mad"]) > 0.005}
    assert {d["id"] for d in apercu["non_repartis"]} == attendus


def test_apercu_par_onglet(achats: TestClient, jeu: dict) -> None:
    """Le pied d'un onglet (clos) totalise les dossiers de cet onglet seulement."""
    clos = _page(achats, statut="clos", limite=5000)["elements"]
    apercu = _ok(achats.get("/api/dossiers/apercu", params={"statut": "clos"}))
    assert apercu["nombre"] == len(clos)
    assert apercu["revient_mad"] == pytest.approx(sum(d["revient_mad"] for d in clos))


def _vieux_match(r: Any, q: str) -> bool:
    """L'ancienne recherche Python (route 187 avant pagination) : `trouve` sur les mêmes champs."""
    morceaux = [r.numero, r.libelle, r.banque, r.commentaire, *r.factures, *r.fournisseurs]
    morceaux += [x.numero for x in r.receptions] + [x.famille for x in r.familles]
    return recherche.trouve(q, *morceaux)


def test_recherche_sql_identique_a_l_ancienne(jeu: dict) -> None:
    """La recherche SQL rend exactement le même ensemble que l'ancienne (tous les jetons des
    dossiers, et des variantes à la ponctuation près), ouvert+clos comme avant."""
    with sessions()() as s:
        resumes = lecture._resumes(s, lecture._charger(s, lecture.filtrer(FiltresDossiers())))
        jetons: set[str] = set()
        for r in resumes:
            for champ in [r.numero, r.libelle, r.banque, *r.factures, *r.fournisseurs]:
                jetons.update((champ or "").split())
            jetons.update(x.numero for x in r.receptions)
            jetons.update(x.famille for x in r.familles)
        # Des variantes à la ponctuation près d'un numéro de facture.
        requetes = {j for j in jetons if j} | {"pag399117", "PAG3 99 117", "camion", "frz-2900"}
        for q in requetes:
            attendu = {r.id for r in resumes if _vieux_match(r, q)}
            requete = lecture.filtrer(FiltresDossiers(q=q)).with_only_columns(Dossier.id)
            obtenu = {i for (i,) in s.execute(requete)}
            assert obtenu == attendu, f"recherche « {q} » : SQL {obtenu} ≠ ancien {attendu}"


def test_filtre_fournisseur_et_verifier(achats: TestClient, jeu: dict) -> None:
    """Le filtre fournisseur (de la facture) et « à vérifier » filtrent au serveur."""
    fid = jeu["imp"].fournisseur_id
    page = _page(achats, fournisseur=fid, limite=5000)["elements"]
    assert page and all(d["facture"] and d["facture"]["fournisseur_id"] == fid for d in page)
    a_verifier = _page(achats, verifier="oui", limite=5000)["elements"]
    assert all(d["a_verifier"] for d in a_verifier)
    sans = _page(achats, verifier="non", limite=5000)["elements"]
    assert all(not d["a_verifier"] for d in sans)
