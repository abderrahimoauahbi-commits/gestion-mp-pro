"""Importations (lot D7) : un dossier = une facture = une livraison ; cours, frais au poids et à
la valeur, droits par code douanier, TVA attendue, clôture, second camion, réceptions sans
facture, fournisseurs marocains. Preuves héritées de `test_importations` (domaine 8).
"""

from __future__ import annotations

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
    ligne,
    ouvrir,
    poste,
)
from fabriques.receptions import ok
from fabriques.referentiels import code_douanier
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Matiere, PosteFrais


@pytest.fixture
def arrivees(application: FastAPI) -> dict[str, Any]:
    """Un fournisseur turc (devise à 10 MAD), trois fils, deux arrivées sous deux factures — à
    chaque essai les siennes (RESTES3 : chaque essai passe seul, dans n'importe quel ordre)."""
    achats = client_de(application, "achats")
    imp = Import.nouveau(cours="10")
    r1 = imp.recevoir(
        achats,
        "FAC-1",
        [
            ("FRISÉ ROUGE", "IR-1", 1000, 2.0),
            ("FRISÉ NOIR", "IN-1", 500, 4.0),
            ("JUTE", "IJ-1", 2000, 1.0),
        ],
    )
    r2 = imp.recevoir(achats, "FAC-2", [("FRISÉ ROUGE", "IR-2", 1000, 2.0)])
    return {"imp": imp, "r1": r1, "r2": r2}


def _premier(arrivees: dict[str, Any], achats: TestClient) -> dict[str, Any]:
    """Le dossier de la facture FAC-1 (trois fils, 6 000 en devise)."""
    return ouvrir(achats, arrivees["imp"].f("FAC-1"))  # type: ignore[no-any-return]


def _cours_et_fret(achats: TestClient, d: dict[str, Any]) -> dict[str, Any]:
    """Le cours de la banque (10) et un fret de 3 500 MAD à la valeur posés sur le dossier."""
    d = ok(
        achats.put(f"/api/dossiers/{d['id']}/cours", json={"version": d["version"], "cours": 10})
    )
    return frais(achats, d, "FRET", 3500, prestataire="CMA CGM", piece="F-88")  # type: ignore[no-any-return]


def _attente(client: TestClient, numero: str) -> dict[str, Any]:
    attente = ok(client.get("/api/dossiers/a-rattacher", params={"locaux": True}))
    return next(f for f in attente["factures"] if f["numero"] == numero)  # type: ignore[no-any-return]


def test_un_dossier_par_facture(arrivees: dict[str, Any], achats: TestClient) -> None:
    """Hérité : test_importations::test_un_dossier_par_facture — toute la facture entre ; une
    facture, un dossier ; rien d'autre n'entre ; aucune ligne reçue ne sort seule."""
    imp: Import = arrivees["imp"]
    f = _attente(achats, imp.f("FAC-1"))
    assert (
        f["dossier"] is None
        and f["lignes"] == 3
        and f["valeurs"] == [{"devise": imp.devise, "valeur": 6000.0}]
    )
    d = ouvrir(achats, imp.f("FAC-1"))
    assert d["nb_lignes"] == 3 and not d["a_la_main"]
    assert [f["numero"] for f in d["factures"]] == [imp.f("FAC-1")]
    assert d["pieces"] == [{"facture": imp.f("FAC-1"), "receptions": [arrivees["r1"]["numero"]]}]
    assert d["numero"].endswith("/26") and d["statut"] == "ouvert" and not d["repris"]
    r = achats.post("/api/dossiers", json={"facture_id": d["factures"][0]["id"]})
    assert r.status_code == 409 and d["numero"] in r.json()["detail"]
    assert r.json()["detail"].startswith("Cette facture a déjà son dossier")
    autre = facture_id(achats, imp.f("FAC-2"))
    r = geste(achats, d, "rattacher", 409, facture_id=autre)
    assert r["detail"] == (
        f"La facture {imp.f('FAC-2')} n'est pas dans le dossier {d['numero']} : l'y ajouter "
        "d'abord (« Ajouter une facture », toute sa marchandise entre), ou elle ouvre son propre "
        "dossier."
    )
    x = d["lignes"][0]
    r = achats.delete(f"/api/dossiers/{d['id']}/lignes/{x['id']}", params={"version": d["version"]})
    assert r.status_code == 409 and "« Détacher la réception »" in r.json()["detail"]
    corps = {"matiere_id": x["matiere_id"], "quantite_kg": 1, "valeur_devise": 1}
    r = geste(achats, d, "lignes", 409, **corps)
    assert r["detail"].startswith(f"Le dossier de la facture {imp.f('FAC-1')} porte ce")


def test_cours_et_frais_au_poids_ou_a_la_valeur(
    arrivees: dict[str, Any], achats: TestClient, direction: TestClient
) -> None:
    """Hérité : test_importations::test_cours_commentaire_et_frais_au_poids_ou_a_la_valeur —
    6 000 × 10 = 60 000 MAD ; fret 3 500 à la valeur (le rouge : 20 000 / 60 000) puis au
    poids (1 000 / 3 500 kg) ; échéancier : la facture et le fret."""
    d = _premier(arrivees, achats)
    d = ok(
        achats.put(f"/api/dossiers/{d['id']}/cours", json={"version": d["version"], "cours": 10})
    )
    assert d["marchandise_mad"] == pytest.approx(60_000)
    rouge = ligne(d, "IMP FRISÉ ROUGE")
    corps = {"version": d["version"], "commentaire": "bobines abîmées"}
    d = ok(achats.put(f"/api/dossiers/{d['id']}/lignes/{rouge['id']}", json=corps))
    rouge = ligne(d, "IMP FRISÉ ROUGE")
    assert rouge["commentaire"] == "bobines abîmées" and rouge["cours"] == 10
    assert rouge["cours_origine"] == "banque"
    d = frais(achats, d, "FRET", 3500, prestataire="CMA CGM", piece="F-88", echeance="2026-01-30")
    fret = d["frais"][0]
    assert fret["prestataire"] == "CMA CGM" and fret["cle"] == "valeur" and fret["version"] == 1
    assert ligne(d, "IMP FRISÉ ROUGE")["charges_mad"] == pytest.approx(3500 / 3)
    assert {x["quoi"] for x in d["echeancier"]} == {f"Facture {d['factures'][0]['numero']}", "Fret"}
    p = ok(direction.get("/api/postes-frais"))
    fret_poste = next(x for x in p if x["code"] == "FRET")
    corps = {
        k: fret_poste[k]
        for k in ("libelle", "recuperable", "nature", "entre_valeur_douane", "ordre", "version")
    }
    assert (
        achats.put(
            f"/api/postes-frais/{fret_poste['id']}", json={**corps, "cle": "poids"}
        ).status_code
        == 403
    )
    try:
        ok(direction.put(f"/api/postes-frais/{fret_poste['id']}", json={**corps, "cle": "poids"}))
        d = fiche(achats, d["id"])
        assert ligne(d, "IMP FRISÉ ROUGE")["charges_mad"] == pytest.approx(1000)
        assert d["revient_mad"] == pytest.approx(63_500) and d["poids"] == pytest.approx(3500)
    finally:
        relu = next(x for x in ok(direction.get("/api/postes-frais")) if x["code"] == "FRET")
        corps["version"] = relu["version"]
        ok(direction.put(f"/api/postes-frais/{fret_poste['id']}", json={**corps, "cle": "valeur"}))


def _code_sur(matieres: list[int], code_id: int | None) -> None:
    with sessions()() as s, s.begin():
        for m in matieres:
            x = s.get(Matiere, m)
            assert x is not None
            x.code_douanier_id = code_id


def test_droits_attendus_par_code_douanier_et_tva(
    arrivees: dict[str, Any], achats: TestClient, direction: TestClient
) -> None:
    """Hérité : test_importations::test_droits_attendus_par_code_douanier_et_tva — droits
    attendus seulement si toutes les matières ont un code actif ; valeur en douane = achat +
    fret + assurance ; TVA attendue = taux × (douane + droits + TPI) ; seule la TVA de la douane
    se compare ; l'écart toléré vient du réglage `toler_tva_import` (C29)."""
    imp: Import = arrivees["imp"]
    d = _cours_et_fret(achats, _premier(arrivees, achats))
    rouge, noir, jute = (imp.matieres[k] for k in ("FRISÉ ROUGE", "FRISÉ NOIR", "JUTE"))
    pp, jt = code_douanier(taux="0.10"), code_douanier(taux="0.025")
    _code_sur([rouge, noir], pp)
    d = fiche(achats, d["id"])
    assert [x["reference"] for x in d["matieres_sans_code"]] == [ligne(d, "IMP JUTE")["reference"]]
    assert d["droits_attendus_mad"] is None and d["droits_ecart_mad"] is None
    _code_sur([jute], jt)
    d = fiche(achats, d["id"])
    # Fret 3 500 à la valeur : 20 000 + 1 166,67 par fil (rouge, noir, jute).
    attendus = (2 * (20_000 + 3500 / 3)) * 0.10 + (20_000 + 3500 / 3) * 0.025
    assert d["matieres_sans_code"] == [] and d["droits_attendus_mad"] == pytest.approx(attendus)
    assert ligne(d, "IMP JUTE")["valeur_douane_mad"] == pytest.approx(20_000 + 3500 / 3)
    with sessions()() as s, s.begin():
        from gestion_mp_pro.modeles import CodeDouanier

        code = s.get(CodeDouanier, jt)
        assert code is not None
        code.actif = False
    d = fiche(achats, d["id"])
    assert d["droits_attendus_mad"] is None
    assert [x["id"] for x in d["matieres_code_inactif"]] == [jute]
    _code_sur([jute], None)
    d = frais(achats, d, "DD", 4150)
    douane = 60_000 + 3500
    assert d["droits_mad"] == 4150 and d["taux_tpi_import"] == pytest.approx(0.0025)
    tva = (douane * 1.0025 + 4150) * d["taux_tva_import"]
    assert d["tva_attendue_mad"] == pytest.approx(tva)
    assert d["tva_ecart_tolere_mad"] == pytest.approx(tva * d["toler_tva_import"])
    d = frais(achats, d, "TPI", 200)
    assert d["tva_attendue_mad"] == pytest.approx((douane + 4150 + 200) * d["taux_tva_import"])
    tpi = next(x for x in d["frais"] if x["poste"] == "TPI")
    ok(
        achats.delete(
            f"/api/dossiers/{d['id']}/frais/{tpi['id']}", params={"version": tpi["version"]}
        )
    )
    with sessions()() as s, s.begin():
        s.add(PosteFrais(code="TVA_TR7", libelle="TVA transitaire", recuperable=True, ordre=990))
    d = frais(achats, d, "TVA", 13_560)
    d = frais(achats, d, "TVA_TR7", 1000)
    assert d["tva_saisie_mad"] == 13_560 and d["tva_mad"] == pytest.approx(14_560)
    assert d["tva_ecart_mad"] is None or abs(d["tva_ecart_mad"]) > d["tva_ecart_tolere_mad"]
    for x in fiche(achats, d["id"])["frais"]:
        if x["poste"] in ("TVA", "TVA_TR7"):
            ok(
                achats.delete(
                    f"/api/dossiers/{d['id']}/frais/{x['id']}", params={"version": x["version"]}
                )
            )


def test_ligne_a_la_main_lot_inconnu_numero_saisi(
    arrivees: dict[str, Any], achats: TestClient
) -> None:
    """Hérité : test_importations::test_ligne_a_la_main_lot_inconnu_numero_saisi — numéro
    déjà pris (409) ; 100 kg, 400 USD au cours 9,5 = 3 800 MAD ; lot inconnu créé sans stock ;
    un frais visé empêche le retrait ; un poste inconnu liste les postes."""
    imp: Import = arrivees["imp"]
    d = a_la_main(achats)
    r = achats.post("/api/dossiers", json={"numero": d["numero"], "date_arrivee": "2018-03-02"})
    assert (
        r.status_code == 409 and r.json()["detail"] == f"Le dossier « {d['numero']} » existe déjà."
    )
    corps = {
        "matiere_id": imp.matieres["FRISÉ NOIR"],
        "lot_numero": "ANCIEN-7-D7",
        "quantite_kg": 100,
        "valeur_devise": 400,
        "devise": imp.devise,
        "cours": 9.5,
        "commentaire": "conteneur 2018",
    }
    d = geste(achats, d, "lignes", **corps)
    x = d["lignes"][0]
    assert x["lot"] == "ANCIEN-7-D7" and x["commentaire"] == "conteneur 2018"
    assert x["valeur_mad"] == pytest.approx(3800) and x["cours_origine"] == "saisi"
    assert d["a_la_main"] and d["actions"]["saisir"] is None and d["actions"]["rattacher"]
    d = frais(achats, d, "TRANSIT", 200, ligne_id=x["id"])
    r = achats.delete(f"/api/dossiers/{d['id']}/lignes/{x['id']}", params={"version": d["version"]})
    assert r.status_code == 409 and r.json()["detail"].startswith("1 frais porte(nt)")
    r = achats.post(
        f"/api/dossiers/{d['id']}/frais",
        json={"version": d["version"], "poste_id": 999_999, "montant": 1},
    )
    assert r.status_code == 422 and "TRANSIT" in r.json()["detail"]


def test_cloture_fige_cours_et_cle(
    arrivees: dict[str, Any], achats: TestClient, direction: TestClient
) -> None:
    """Hérité : test_importations::test_cloture_fige_cours_et_cle — la clôture écrit le cours
    du jour (`clos_au_jour`) ; un frais sur un clos est refusé ; repasser une clé ne change pas
    un dossier clos (répartition figée) ; rouvrir le rend modifiable."""
    imp: Import = arrivees["imp"]
    d = ouvrir(achats, imp.f("FAC-2"))
    assert d["lignes"][0]["cours"] is None and d["actions"]["cloturer"] is None
    assert "Les cours vides prendront le cours du jour" in d["alertes"][0]
    refus = geste(achats, d, "cloturer", 422)
    assert refus["code"] == "confirmation_requise" and "cours vides" in refus["detail"]
    d = geste(achats, d, "cloturer", alertes_lues=True)
    assert d["statut"] == "clos" and d["lignes"][0]["cours"] == 10
    assert d["lignes"][0]["cours_origine"] == "clos_au_jour" and d["actions"]["frais"]
    premier = _cours_et_fret(achats, _premier(arrivees, achats))
    premier = geste(achats, premier, "cloturer", alertes_lues=True)
    refus = frais(achats, premier, "FRET", 1, 409)
    assert refus["detail"] == "Ce dossier est clos : le rouvrir pour y toucher (c'est tracé)."
    assert refus["code"] == "dossier_clos"
    postes = {x["code"]: x for x in ok(direction.get("/api/postes-frais"))}
    fret = postes["FRET"]
    corps = {
        k: fret[k] for k in ("libelle", "recuperable", "nature", "entre_valeur_douane", "ordre")
    }
    r = ok(
        direction.put(
            f"/api/postes-frais/{fret['id']}",
            json={**corps, "cle": "poids", "version": fret["version"]},
        )
    )
    assert r["parts_figees"] >= 1
    try:
        apres = fiche(achats, premier["id"])
        avant = {x["id"]: x["revient_mad"] for x in premier["lignes"]}
        for x in apres["lignes"]:
            assert x["revient_mad"] == pytest.approx(avant[x["id"]], abs=0.01)
        fr = next(x for x in apres["frais"] if x["poste"] == "FRET")
        assert fr["repartition"] == "figée (clé d'avant son changement)"
        assert sum(p["montant"] for p in fr["parts"]) == pytest.approx(3500)
    finally:
        fret = next(x for x in ok(direction.get("/api/postes-frais")) if x["code"] == "FRET")
        ok(
            direction.put(
                f"/api/postes-frais/{fret['id']}",
                json={**corps, "cle": "valeur", "version": fret["version"]},
            )
        )
    d = geste(achats, premier, "rouvrir", motif="facture de frais en retard")
    assert d["statut"] == "ouvert" and d["actions"]["frais"] is None
    assert poste("DD")
