"""Un dossier d'importation, plusieurs factures (lot PLUSIEURS-FACTURES, décision de Mohamed du
12/10/2026, qui amende I3) : ouvert depuis la facture A, il prend B (même fournisseur) puis C
(autre fournisseur, autre devise) ; marchandises des trois, échéancier à trois échéances de
marchandise, C36 facture par facture, coût de revient sans doublon ; une facture déjà dans un
dossier est refusée (et à deux postes, un 409 qui nomme le gagnant) ; retirer B (sa marchandise
attend, les frais se répartissent sur le reste) ; retrait refusé si un frais vise sa
marchandise ; détacher la dernière réception de C (C attend) ; annuler (A et C attendent).
"""

from __future__ import annotations

import io
import threading
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.importations import (
    Import,
    a_la_main,
    facture_id,
    fiche,
    frais,
    geste,
    invalider,
    ouvrir,
)
from fabriques.receptions import facture as corriger_facture
from fabriques.receptions import ok
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import load_workbook


def _attente(client: TestClient, numero: str) -> dict[str, Any] | None:
    """La facture `numero` dans « En attente de dossier » (ou rien)."""
    factures = ok(client.get("/api/dossiers/a-rattacher", params={"locaux": True}))["factures"]
    return next((f for f in factures if f["numero"] == numero), None)


def ajouter(
    client: TestClient, d: dict[str, Any], numero: str, code: int = 200, **corps: Any
) -> Any:
    """« Ajouter une facture » (route 253), à la version lue ; la fiche ou le refus."""
    return geste(client, d, "factures", code, facture_id=facture_id(client, numero), **corps)


def retirer(client: TestClient, d: dict[str, Any], fid: int, code: int = 200) -> Any:
    """« Retirer » une facture du dossier (route 254), à la version lue."""
    version = fiche(client, d["id"])["version"]
    r = client.delete(f"/api/dossiers/{d['id']}/factures/{fid}", params={"version": version})
    assert r.status_code == code, r.text
    return r.json()


def _de(d: dict[str, Any], numero: str) -> dict[str, Any]:
    """La facture `numero` du dossier."""
    return next(f for f in d["factures"] if f["numero"] == numero)


@pytest.fixture
def trois(achats: TestClient) -> dict[str, Any]:
    """Les factures A (deux fils, 400), B (même fournisseur, 100 reçus pour 120 facturés) et C
    (autre fournisseur, autre devise, 600), et le dossier ouvert depuis A."""
    a, c = Import.nouveau(cours="10"), Import.nouveau(cours="12")
    ra = a.recevoir(achats, "PF-A", [("ROUGE", "PFA-1", 100, 2), ("NOIR", "PFA-2", 50, 4)],
                    montant=400)  # fmt: skip
    rb = a.recevoir(achats, "PF-B", [("JUTE", "PFB-1", 100, 1)], montant=120)
    rc = c.recevoir(achats, "PF-C", [("FIL", "PFC-1", 200, 3)], montant=600)
    d = ouvrir(achats, a.f("PF-A"))
    return {"a": a, "c": c, "ra": ra, "rb": rb, "rc": rc, "d": d}


def _les_trois(achats: TestClient, t: dict[str, Any]) -> dict[str, Any]:
    """Le dossier de A, qui prend B puis C."""
    d = ajouter(achats, t["d"], t["a"].f("PF-B"))
    return ajouter(achats, d, t["c"].f("PF-C"))


def test_un_dossier_prend_trois_factures(achats: TestClient, trois: dict[str, Any]) -> None:
    """A, puis B (même fournisseur), puis C (autre fournisseur, autre devise) : leurs quatre
    marchandises, chacune dans sa devise ; trois factures, dans l'ordre de leur ajout ; une
    échéance de marchandise par facture ; aucune n'attend plus ; le journal le dit."""
    a, c = trois["a"], trois["c"]
    d = _les_trois(achats, trois)
    assert [f["numero"] for f in d["factures"]] == [a.f("PF-A"), a.f("PF-B"), c.f("PF-C")]
    assert d["nb_lignes"] == 4 and {x["devise"] for x in d["lignes"]} == {a.devise, c.devise}
    assert [(f["lignes"], f["devise"]) for f in d["factures"]] == [
        (2, a.devise), (1, a.devise), (1, c.devise)
    ]  # fmt: skip
    assert _de(d, c.f("PF-C"))["receptions"] == [
        {"id": trois["rc"]["id"], "numero": trois["rc"]["numero"]}
    ]
    assert all(f["retrait"] is None and f["liberee_le"] is None for f in d["factures"])
    marchandise = [e for e in d["echeancier"] if e["nature"] == "marchandise"]
    assert sorted((e["quoi"], e["devise"], e["montant"]) for e in marchandise) == sorted(
        [
            (f"Facture {a.f('PF-A')}", a.devise, 400),
            (f"Facture {a.f('PF-B')}", a.devise, 120),
            (f"Facture {c.f('PF-C')}", c.devise, 600),
        ]
    )
    assert d["fournisseurs"] == sorted(
        {d["factures"][0]["fournisseur"], _de(d, c.f("PF-C"))["fournisseur"]}
    )
    for numero in (a.f("PF-A"), a.f("PF-B"), c.f("PF-C")):
        assert _attente(achats, numero) is None
    assert d["actions"]["ajouter_facture"] is None
    journal = ok(achats.get(f"/api/historique/dossier/{d['id']}"))
    assert sum(1 for x in journal if x["action"] == "facture ajoutée") == 2


def test_c36_se_lit_facture_par_facture(achats: TestClient, trois: dict[str, Any]) -> None:
    """Chaque facture se rapproche de ce qu'elle a apporté : A (400 pour 400) et C (600 pour
    600, en sa devise) conformes, B (120 pour 100) hors tolérance — la fiche, ses alertes et le
    contrôle C36 le disent pour B seule ; jamais d'addition entre devises."""
    a, c = trois["a"], trois["c"]
    d = _les_trois(achats, trois)
    ecarts = {f["numero"]: f["ecart"] for f in d["factures"]}
    assert ecarts[a.f("PF-A")]["recu"] == pytest.approx(400)
    assert not ecarts[a.f("PF-A")]["hors_tolerance"]
    assert ecarts[a.f("PF-B")]["recu"] == pytest.approx(100)
    assert ecarts[a.f("PF-B")]["hors_tolerance"] and ecarts[a.f("PF-B")]["part"] == pytest.approx(
        0.2
    )
    assert ecarts[c.f("PF-C")]["devise"] == c.devise and not ecarts[c.f("PF-C")]["hors_tolerance"]
    assert "facture ≠ marchandise reçue" in d["a_verifier"]
    (alerte,) = [x for x in d["alertes"] if "s'écarte" in x]
    assert alerte.startswith(f"La facture {a.f('PF-B')} s'écarte de 20,0")
    assert alerte.endswith("de la marchandise qu'elle a apportée.")
    invalider()
    r = ok(achats.get("/api/controles/C36", params={"q": d["numero"]}))
    lignes = [x for x in r["elements"] if x["dossier"] == d["numero"]]
    assert [(x["facture"], x["recu"]) for x in lignes] == [(a.f("PF-B"), 100)]


def test_le_cout_de_revient_ne_se_dedouble_pas(achats: TestClient, trois: dict[str, Any]) -> None:
    """Trois factures, quatre marchandises : l'analyse les compte une fois chacune (poids et
    coût égaux à ceux du dossier), le classeur nomme les trois factures."""
    a, c = trois["a"], trois["c"]
    d = frais(achats, _les_trois(achats, trois), "FRET", 1000)
    corps = {"version": d["version"], "devise": c.devise, "cours": 12}
    d = ok(achats.put(f"/api/dossiers/{d['id']}/cours", json=corps))
    ids = [*a.matieres.values(), *c.matieres.values()]
    r = ok(achats.get("/api/analyse/revient", params={"matieres": ids, "detail": True}))
    assert len(r["detail_lignes"]) == 4
    assert r["total_poids"] == pytest.approx(d["poids"]) == pytest.approx(450)
    revient = sum(x["revient_mad"] for x in r["detail_lignes"])
    assert revient == pytest.approx(d["revient_mad"])
    classeur = load_workbook(
        io.BytesIO(achats.get("/api/export/dossiers", params={"q": d["numero"]}).content)
    )
    lignes = list(classeur["Dossiers"].iter_rows(values_only=True))
    entetes = next(x for x in lignes if "Factures" in x)
    rang = next(x for x in lignes if x[0] == d["numero"])
    assert rang[entetes.index("Factures")] == " · ".join([a.f("PF-A"), a.f("PF-B"), c.f("PF-C")])


def test_liste_et_recherche_montrent_toutes_les_factures(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """La liste trouve le dossier par le numéro de chacune de ses factures et par le
    fournisseur de chacune ; « Facture · réceptions » (pièces) les cite toutes."""
    a, c = trois["a"], trois["c"]
    d = _les_trois(achats, trois)
    for q in (a.f("PF-B"), c.f("PF-C")):
        page = ok(achats.get("/api/dossiers", params={"q": q}))["elements"]
        assert [x["id"] for x in page] == [d["id"]]
    fournisseur_c = _de(d, c.f("PF-C"))["fournisseur_id"]
    page = ok(achats.get("/api/dossiers", params={"fournisseur": fournisseur_c}))["elements"]
    assert d["id"] in {x["id"] for x in page}
    apercu = ok(achats.get("/api/dossiers/apercu", params={"q": d["numero"]}))
    assert fournisseur_c in {x["id"] for x in apercu["fournisseurs"]}
    assert {p["facture"] for p in d["pieces"]} == {a.f("PF-A"), a.f("PF-B"), c.f("PF-C")}


def test_une_facture_n_est_que_dans_un_seul_dossier(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """B, déjà dans le dossier de A, ne s'ajoute pas à un autre dossier (409 qui le nomme), ni
    une seconde fois ; un dossier saisi à la main ne prend pas de facture ; une version
    périmée est refusée."""
    a, c = trois["a"], trois["c"]
    d = ajouter(achats, trois["d"], a.f("PF-B"))
    autre = ouvrir(achats, c.f("PF-C"))
    fb = _de(d, a.f("PF-B"))["id"]
    r = achats.post(
        f"/api/dossiers/{autre['id']}/factures",
        json={"version": autre["version"], "facture_id": fb},
    )
    assert r.status_code == 409 and r.json()["code"] == "doublon"
    assert d["numero"] in r.json()["detail"]
    r = achats.post(
        f"/api/dossiers/{d['id']}/factures", json={"version": d["version"], "facture_id": fb}
    )
    assert r.status_code == 409 and d["numero"] in r.json()["detail"]
    a.recevoir(achats, "PF-D", [("ROUGE", "PFD-1", 10, 2)])
    r = achats.post(
        f"/api/dossiers/{d['id']}/factures",
        json={"version": d["version"] - 1, "facture_id": facture_id(achats, a.f("PF-D"))},
    )
    assert r.status_code == 409 and r.json()["code"] == "conflit_version"


def test_deux_postes_prennent_la_meme_facture(
    application: FastAPI, achats: TestClient, trois: dict[str, Any]
) -> None:
    """Deux postes ajoutent la même facture à deux dossiers au même instant : l'un gagne, l'autre
    reçoit un 409 qui nomme le dossier gagnant (l'index unique départage)."""
    a, c = trois["a"], trois["c"]
    d1 = trois["d"]
    d2 = ouvrir(achats, c.f("PF-C"))
    fb = facture_id(achats, a.f("PF-B"))
    postes = [client_de(application, "achats") for _ in range(2)]
    depart, reponses = threading.Barrier(2), {}

    def courir(i: int, d: dict[str, Any]) -> None:
        corps = {"version": d["version"], "facture_id": fb}
        depart.wait()
        reponses[i] = postes[i].post(f"/api/dossiers/{d['id']}/factures", json=corps)

    fils = [threading.Thread(target=courir, args=(i, x)) for i, x in enumerate((d1, d2))]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    codes = sorted(r.status_code for r in reponses.values())
    assert codes == [200, 409]
    gagnant = next(r.json() for r in reponses.values() if r.status_code == 200)
    perdant = next(r.json() for r in reponses.values() if r.status_code == 409)
    assert gagnant["numero"] in perdant["detail"] and perdant["code"] == "doublon"
    assert a.f("PF-B") in {f["numero"] for f in gagnant["factures"]}


def test_retirer_b_sa_marchandise_attend_les_frais_se_repartissent(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Retirer B : sa marchandise sort et attend de nouveau son dossier ; le fret (1 000 MAD, à la
    valeur) reste au dossier et se répartit sur les marchandises qui restent."""
    a = trois["a"]
    d = frais(achats, _les_trois(achats, trois), "FRET", 1000)
    fb = _de(d, a.f("PF-B"))
    jute = next(x for x in d["lignes"] if x["reception_id"] == trois["rb"]["id"])
    assert jute["charges_mad"] > 0
    avant = {x["id"]: x["charges_mad"] for x in d["lignes"]}
    d = retirer(achats, d, fb["id"])
    assert a.f("PF-B") not in {f["numero"] for f in d["factures"]} and d["nb_lignes"] == 3
    assert d["nb_frais"] == 1 and sum(x["charges_mad"] for x in d["lignes"]) == pytest.approx(1000)
    assert all(x["charges_mad"] > avant[x["id"]] for x in d["lignes"])
    attend = _attente(achats, a.f("PF-B"))
    assert attend is not None and attend["dossier_id"] is None and attend["lignes"] == 1
    assert len([e for e in d["echeancier"] if e["nature"] == "marchandise"]) == 2
    journal = ok(achats.get(f"/api/historique/dossier/{d['id']}"))
    assert any(x["action"] == "facture retirée" for x in journal)
    assert ajouter(achats, d, a.f("PF-B"))["nb_lignes"] == 4  # elle peut revenir


def test_retirer_une_facture_dont_un_frais_vise_la_marchandise(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Un frais visé sur une marchandise de C : « Retirer » est annoncé impossible, avec sa
    raison, et refusé (409) avec cette même raison ; rien ne bouge."""
    c = trois["c"]
    d = _les_trois(achats, trois)
    fil = next(x for x in d["lignes"] if x["reception_id"] == trois["rc"]["id"])
    d = frais(achats, d, "TRANSIT", 300, ligne_id=fil["id"])
    raison = _de(d, c.f("PF-C"))["retrait"]
    assert raison is not None and raison.startswith(
        f"1 frais porte(nt) sur une marchandise de la facture {c.f('PF-C')}"
    )
    refus = retirer(achats, d, _de(d, c.f("PF-C"))["id"], 409)
    assert refus["detail"] == raison
    assert fiche(achats, d["id"])["nb_lignes"] == 4
    assert retirer(achats, d, 999_999, 404)["detail"].startswith("Cette facture n'est pas")


def test_detacher_la_derniere_reception_de_c_c_attend(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Détacher la seule réception de C : C quitte le dossier et attend de nouveau son dossier ;
    A et B restent."""
    a, c = trois["a"], trois["c"]
    d = _les_trois(achats, trois)
    d = geste(achats, d, "detacher", reception_id=trois["rc"]["id"])
    assert [f["numero"] for f in d["factures"]] == [a.f("PF-A"), a.f("PF-B")]
    attend = _attente(achats, c.f("PF-C"))
    assert attend is not None and attend["dossier_id"] is None
    journal = ok(achats.get(f"/api/historique/dossier/{d['id']}"))
    assert any("sortie du dossier" in (x["detail"] or "") for x in journal)


def test_annuler_le_dossier_ses_factures_attendent(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Annuler le dossier de A et C : les deux attendent de nouveau leur dossier ; la fiche
    annulée garde leur trace (libérées) ; A rouvre un dossier neuf."""
    a, c = trois["a"], trois["c"]
    d = ajouter(achats, trois["d"], c.f("PF-C"))
    d = geste(achats, d, "annuler", motif="mauvais conteneur")
    assert d["statut"] == "annule" and all(f["liberee_le"] for f in d["factures"])
    assert all(f["retrait"] == d["actions"]["modifier"] for f in d["factures"])
    for numero in (a.f("PF-A"), c.f("PF-C")):
        attend = _attente(achats, numero)
        assert attend is not None and attend["dossier_id"] is None
    neuf = ouvrir(achats, a.f("PF-A"))
    assert neuf["id"] != d["id"] and neuf["nb_lignes"] == 2
    journal = ok(achats.get(f"/api/historique/dossier/{d['id']}"))
    assert any(f"factures {a.f('PF-A')}, {c.f('PF-C')} libérées" in (x["detail"] or "")
               for x in journal)  # fmt: skip


def test_second_camion_d_une_facture_ajoutee(achats: TestClient, trois: dict[str, Any]) -> None:
    """Le second camion de C (ajoutée au dossier de A) rejoint le dossier : « En attente » le
    propose pour ce dossier, le volet du dossier aussi."""
    c = trois["c"]
    d = _les_trois(achats, trois)
    c.recevoir(achats, "PF-C", [("FIL", "PFC-2", 50, 3)])
    attend = _attente(achats, c.f("PF-C"))
    assert attend is not None and attend["dossier_id"] == d["id"]
    d = fiche(achats, d["id"])
    assert [f["numero"] for f in d["a_rattacher"]] == [c.f("PF-C")]
    d = geste(achats, d, "rattacher", facture_id=attend["facture_id"])
    assert _de(d, c.f("PF-C"))["lignes"] == 2


def test_la_reception_d_une_facture_ajoutee_mene_au_dossier(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Panneau « Facture du fournisseur » d'une réception de B : son dossier est celui de A ; le
    numéro de la facture n'y change plus (en détacher la réception d'abord) ; la liste des
    factures dit son dossier."""
    a = trois["a"]
    d = ajouter(achats, trois["d"], a.f("PF-B"))
    r = ok(achats.get(f"/api/receptions/{trois['rb']['id']}"))
    assert r["dossier"]["id"] == d["id"]
    refus = corriger_facture(achats, r, 409, numero="AUTRE-NUMERO")
    assert "l'en détacher d'abord" in refus["detail"]
    factures = ok(achats.get("/api/factures", params={"fournisseur": a.fournisseur_id}))
    portees = {f["numero"]: f["dossier"] for f in factures}
    assert portees[a.f("PF-B")]["numero"] == d["numero"]


def test_un_fournisseur_marocain_s_ajoute_sur_confirmation(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """La facture d'un fournisseur marocain s'ajoute seulement confirmée (I16) ; le dossier le
    garde (`local_confirme`)."""
    loc = Import.nouveau(code="MAD", pays="MAROC")
    loc.recevoir(achats, "PF-LOC", [("FIL", "PFL-1", 10, 2)])
    refus = ajouter(achats, trois["d"], loc.f("PF-LOC"), 409)
    assert "L'ajouter quand même se confirme." in refus["detail"]
    d = ajouter(achats, trois["d"], loc.f("PF-LOC"), local_confirme=True)
    assert d["local_confirme"] and len(d["factures"]) == 2


def test_un_dossier_saisi_a_la_main_ne_prend_pas_de_facture(
    achats: TestClient, trois: dict[str, Any]
) -> None:
    """Un dossier d'avant la mise en service ne prend pas de facture reçue : le geste est
    annoncé impossible, avec sa raison, et refusé."""
    a = trois["a"]
    main = a_la_main(achats)
    assert main["actions"]["ajouter_facture"] is not None
    refus = ajouter(achats, main, a.f("PF-B"), 409)
    assert refus["detail"] == main["actions"]["ajouter_facture"]
