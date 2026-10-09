"""Deux postes sur les mêmes dossiers (lot D7) : trois ouvertures d'une même facture (un seul
dossier, les autres un 409 qui nomme le gagnant), l'ouverture contre l'annulation de la
réception, l'ouverture contre la correction du numéro de sa facture, la clôture contre l'ajout
d'un frais. Rejoués plusieurs fois (ESSAIS § 15 : boucles répétées et invariants).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.importations import Import, facture_id, fiche, ouvrir, poste
from fabriques.receptions import menage, ok  # noqa: F401 — fixture du module
from fabriques.referentiels import unique
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Dossier, DossierFrais
from gestion_mp_pro.services import factures
from gestion_mp_pro.services.importations import etats, ouverture

REPETITIONS = 3

pytestmark = pytest.mark.usefixtures("menage")


def _ensemble(appels: list[Callable[[], int]]) -> list[int]:
    """Lance les appels au même instant ; rend leurs codes, triés."""
    depart = threading.Barrier(len(appels))
    codes: list[int] = []

    def courir(appel: Callable[[], int]) -> None:
        depart.wait()
        codes.append(appel())

    fils = [threading.Thread(target=courir, args=(a,)) for a in appels]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    return sorted(codes)


def _en_parallele(appel: Callable[[], Any]) -> tuple[threading.Thread, dict[str, Any]]:
    resultat: dict[str, Any] = {}
    fil = threading.Thread(target=lambda: resultat.setdefault("r", appel()))
    fil.start()
    return fil, resultat


def _ralenti(
    vrai: Callable[..., Any],
) -> tuple[Callable[..., Any], threading.Event, threading.Event]:
    """`vrai`, qui attend le feu avant de s'exécuter (et dit qu'il est prêt)."""
    pret, feu = threading.Event(), threading.Event()

    def lent(*args: Any, **kwargs: Any) -> Any:
        pret.set()
        feu.wait(10)
        return vrai(*args, **kwargs)

    return lent, pret, feu


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_trois_creations_simultanees_un_seul_dossier(
    application: FastAPI, achats: TestClient, tour: int
) -> None:
    """Hérité : test_importations::test_trois_creations_simultanees_un_seul_dossier — trois
    postes, une facture : [201, 409, 409], un seul dossier, jamais d'erreur du serveur."""
    imp = Import.nouveau()
    imp.recevoir(achats, f"SIMUL-{tour}", [("NOIR", "S", 10, 4)])
    fid = facture_id(achats, imp.f(f"SIMUL-{tour}"))
    postes = [client_de(application, "achats") for _ in range(3)]
    appels = [
        lambda p=p: p.post("/api/dossiers", json={"facture_id": fid}).status_code for p in postes
    ]
    assert _ensemble(appels) == [201, 409, 409]
    with sessions()() as s:
        assert s.scalar(select(func.count()).where(Dossier.facture_id == fid)) == 1


def test_la_course_se_rattrape_par_l_index_unique(
    achats: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hérité (la course elle-même) :
    test_importations::test_trois_creations_simultanees_un_seul_dossier
    — le perdant qui a passé les vérifications avant que le gagnant n'écrive : l'index unique
    refuse, et le refus devient un 409 qui nomme le dossier gagnant."""
    imp = Import.nouveau()
    imp.recevoir(achats, "SIMUL", [("NOIR", "S", 10, 4)])
    gagnant = ouvrir(achats, imp.f("SIMUL"))
    vrais, appels = ouverture.porteurs, []

    def pas_encore_vus(s: Any, f: Any = None) -> Any:
        appels.append(f)
        return {} if len(appels) == 1 else vrais(s, f)

    monkeypatch.setattr(ouverture, "porteurs", pas_encore_vus)
    monkeypatch.setattr(ouverture, "de_la_facture", lambda s, f: [])
    r = achats.post("/api/dossiers", json={"facture_id": gagnant["facture"]["id"]})
    assert r.status_code == 409 and r.json()["detail"].startswith("Un autre poste vient")
    assert gagnant["numero"] in r.json()["detail"]


def test_ouvrir_pendant_qu_on_annule_la_reception(
    application: FastAPI, achats: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hérité : test_importations_second_audit::test_ouvrir_pendant_qu_on_annule_la_reception —
    l'ouverture tient la réception : l'annulation attend, voit le dossier et refuse."""
    imp = Import.nouveau()
    rec = imp.recevoir(achats, "COURSE1", [("FIL", "C1", 300, 2)])
    fid = facture_id(achats, imp.f("COURSE1"))
    lent, pret, feu = _ralenti(ouverture.journaliser)
    monkeypatch.setattr(ouverture, "journaliser", lent)
    a, b = client_de(application, "achats"), client_de(application, "achats")
    fil_o, r_o = _en_parallele(lambda: a.post("/api/dossiers", json={"facture_id": fid}))
    assert pret.wait(10)
    corps = {"version": rec["version"], "motif": "en double"}
    fil_a, r_a = _en_parallele(lambda: b.post(f"/api/receptions/{rec['id']}/annuler", json=corps))
    time.sleep(0.5)
    assert fil_a.is_alive()
    feu.set()
    fil_o.join(10)
    fil_a.join(10)
    assert r_o["r"].status_code == 201, r_o["r"].text
    assert r_a["r"].status_code == 409 and "Détacher la réception" in r_a["r"].json()["detail"]
    assert ok(achats.get(f"/api/receptions/{rec['id']}"))["statut"] == "validee"


def test_corriger_la_facture_pendant_qu_on_ouvre_le_dossier(
    application: FastAPI, achats: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hérité :
    test_importations_second_audit::test_corriger_la_facture_pendant_qu_on_ouvre_le_dossier
    — la correction du numéro passe d'abord ; l'ouverture attend, relit la réception (elle n'est
    plus de cette facture) et refuse : jamais un dossier « de F » qui porte la marchandise de G."""
    imp = Import.nouveau()
    rec = imp.recevoir(achats, "COURSE3", [("FIL", "C3", 300, 2)])
    fid = facture_id(achats, imp.f("COURSE3"))
    lent, pret, feu = _ralenti(factures.corriger)
    monkeypatch.setattr(factures, "corriger", lent)
    a, b = client_de(application, "achats"), client_de(application, "achats")
    autre = unique("COURSE3-G")
    corps = {"version": rec["version"], "numero": autre}
    fil_c, r_c = _en_parallele(lambda: b.put(f"/api/receptions/{rec['id']}/facture", json=corps))
    assert pret.wait(10)
    fil_o, r_o = _en_parallele(lambda: a.post("/api/dossiers", json={"facture_id": fid}))
    time.sleep(0.5)
    assert fil_o.is_alive()
    feu.set()
    fil_c.join(10)
    fil_o.join(10)
    monkeypatch.undo()
    assert r_c["r"].status_code == 200, r_c["r"].text
    assert r_o["r"].status_code == 409 and "n'a plus de marchandise" in r_o["r"].json()["detail"]
    attente = ok(achats.get("/api/dossiers/a-rattacher"))
    assert next(f for f in attente["factures"] if f["numero"] == autre)["lignes"] == 1


def test_la_cloture_contre_l_ajout_d_un_frais(
    application: FastAPI, achats: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La clôture tient le dossier : un frais ajouté pendant ce temps attend, voit le dossier clos
    et refuse — jamais un frais dans un dossier clos dont le coût est figé."""
    imp = Import.nouveau()
    imp.recevoir(achats, "CLOT", [("FIL", "CL", 300, 2)])
    d = ouvrir(achats, imp.f("CLOT"))
    lent, pret, feu = _ralenti(etats.noter)
    monkeypatch.setattr(etats, "noter", lent)
    a, b = client_de(application, "achats"), client_de(application, "achats")
    corps_c = {"version": d["version"], "alertes_lues": True}
    fil_c, r_c = _en_parallele(lambda: a.post(f"/api/dossiers/{d['id']}/cloturer", json=corps_c))
    assert pret.wait(10)
    corps_f = {"version": d["version"], "poste_id": poste("DD"), "montant": 500}
    fil_f, r_f = _en_parallele(lambda: b.post(f"/api/dossiers/{d['id']}/frais", json=corps_f))
    time.sleep(0.5)
    assert fil_f.is_alive()
    feu.set()
    fil_c.join(10)
    fil_f.join(10)
    assert r_c["r"].status_code == 200 and r_c["r"].json()["statut"] == "clos"
    assert r_f["r"].status_code == 409
    with sessions()() as s:
        assert s.scalar(select(func.count()).where(DossierFrais.dossier_id == d["id"])) == 0


@pytest.mark.parametrize("tour", range(REPETITIONS))
def test_cloture_et_frais_ensemble(application: FastAPI, achats: TestClient, tour: int) -> None:
    """Lancés au même instant : soit le frais passe d'abord et la clôture le compte, soit la
    clôture passe et le frais est refusé — le coût figé contient toujours tous les frais."""
    imp = Import.nouveau()
    imp.recevoir(achats, f"ENS-{tour}", [("FIL", "EN", 300, 2)])
    d = ouvrir(achats, imp.f(f"ENS-{tour}"))
    a, b = client_de(application, "achats"), client_de(application, "achats")
    corps_f = {"version": d["version"], "poste_id": poste("DD"), "montant": 500}
    appels = [
        lambda: (
            a.post(
                f"/api/dossiers/{d['id']}/cloturer",
                json={"version": d["version"], "alertes_lues": True},
            ).status_code
        ),
        lambda: b.post(f"/api/dossiers/{d['id']}/frais", json=corps_f).status_code,
    ]
    codes = _ensemble(appels)
    d = fiche(achats, d["id"])
    assert codes == [200, 409]
    assert d["statut"] in ("clos", "ouvert")
    if d["statut"] == "ouvert":
        assert d["nb_frais"] == 1 and d["revient_mad"] == pytest.approx(300 * 2 * 10 + 500)
    else:
        assert d["nb_frais"] == 0
