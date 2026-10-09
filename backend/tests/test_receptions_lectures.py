"""Lectures et classeurs des réceptions (lot D4) : la liste filtrée au serveur, l'archive des
pesées paginée (A-20 : BL seul), le poids des bobines, les classeurs aux mêmes filtres que
l'écran, la pastille du menu, « À valider » (registre du lot D5), le journal et l'historique.
Preuve héritée de `test_achats::test_les_listes_s_exportent_comme_a_l_ecran` (partie
réceptions).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.documents import classeur
from fabriques.receptions import (
    Quai,
    camion,
    geste,
    j,
    ok,
    recevoir,
)
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def decor() -> dict:
    """Un fournisseur, deux matières (bobines de 2 kg au catalogue), un magasin."""
    a = Achat.nouveau(devise="MAD", nom="Filature Écrue de Fès")
    bleu = a.matiere("LECT BLEU", poids_bobine="2", bobines_palette="10")
    vert = a.matiere("LECT VERT")
    return {"a": a, "bleu": bleu, "vert": vert, "quai": Quai.nouveau()}


def _ligne(d: dict, m: str, lot: str, kg: float, **x: object) -> dict:
    return {"matiere_id": d[m], "lot_numero": lot, "quantite_pesee": kg,
            "magasin_id": d["quai"].courant, **x}  # fmt: skip


def test_la_liste_se_filtre_au_serveur(achats: TestClient, decor: dict) -> None:
    """Statut, fournisseur, dates, recherche multi-mots sans accents (n°, fournisseur, lot…)."""
    a = decor["a"]
    v = recevoir(
        achats, a.fournisseur_id, [_ligne(decor, "bleu", "LI-ECRU-1", 20)], numero_bl="BL-ÉCRU"
    )
    b = camion(achats, a.fournisseur_id, [_ligne(decor, "vert", "LI-2", 0)], date=j(-3))
    filtre = {"fournisseur": a.fournisseur_id}
    tous = ok(achats.get("/api/receptions", params=filtre))["elements"]
    assert {v["id"], b["id"]} <= {x["id"] for x in tous}
    brouillons = ok(achats.get("/api/receptions", params=filtre | {"statut": "brouillon"}))[
        "elements"
    ]
    assert b["id"] in {x["id"] for x in brouillons} and v["id"] not in {x["id"] for x in brouillons}
    assert next(x for x in brouillons if x["id"] == b["id"])["blocages"]
    trouves = ok(achats.get("/api/receptions", params={"q": "ecrue fes li-ecru"}))["elements"]
    assert [x["id"] for x in trouves] == [v["id"]]
    assert (
        ok(achats.get("/api/receptions", params={"q": "bl-ecru"}))["elements"][0]["id"] == v["id"]
    )
    du = ok(achats.get("/api/receptions", params=filtre | {"du": j(-1)}))["elements"]
    assert b["id"] not in {x["id"] for x in du}
    assert achats.get("/api/receptions", params={"statut": "perdue"}).status_code == 422


def test_l_archive_des_pesees_se_pagine_et_dit_ses_ecarts(achats: TestClient, decor: dict) -> None:
    """A-20 (Gestion MP corrigé) : « Annoncé BL » est le BL seul, l'écart dit à quoi il se
    compare ; poids de bobine face au catalogue ; curseur, total et indicateurs sur toutes les
    lignes filtrées ; un curseur illisible : 422."""
    a = decor["a"]
    r = recevoir(achats, a.fournisseur_id, [
        _ligne(decor, "bleu", "PE-1", 25, quantite_bl=20, nb_palettes=1),
        _ligne(decor, "vert", "PE-2", 10, qualite="reserve"),
        _ligne(decor, "vert", "PE-3", 0, qualite="refuse"),
    ])  # fmt: skip
    page = ok(achats.get("/api/receptions/pesees", params={"q": r["numero"], "limite": 2}))
    assert page["total"] == 3 and len(page["elements"]) == 2 and page["suivant"]
    suite = ok(
        achats.get(
            "/api/receptions/pesees",
            params={"q": r["numero"], "limite": 2, "apres": page["suivant"]},
        )
    )
    assert len(suite["elements"]) == 1 and suite["suivant"] is None
    lignes = {x["lot"]: x for x in page["elements"] + suite["elements"]}
    bleu = lignes["PE-1"]
    assert bleu["quantite_bl"] == 20 and bleu["compare_au"] == "bl"
    assert bleu["ecart"] == pytest.approx(5) and bleu["ecart_relatif"] == pytest.approx(0.25)
    assert bleu["poids_moyen_bobine"] == pytest.approx(2.5) and bleu["bobine_hors_tolerance"]
    assert page["non_conformes"] == 2 and page["hors_tolerance"] == 1
    assert page["kg_pesees"] == 35
    ecarts = ok(
        achats.get(
            "/api/receptions/pesees",
            params={"q": r["numero"], "ecarts": True, "qualite": "reserve"},
        )
    )
    assert [x["lot"] for x in ecarts["elements"]] == ["PE-2"]
    refus = achats.get("/api/receptions/pesees", params={"apres": "WyJ4Il0"})
    assert refus.status_code == 422 and refus.json()["code"] == "curseur_invalide"


def test_la_pesee_d_un_brouillon_dit_brouillon(achats: TestClient, decor: dict) -> None:
    """RESTES3 (F4) : un brouillon n'a pas de numéro ; sa pesée dit « Brouillon » (le
    vocabulaire « brouillon n° 6 » est retiré de l'écran)."""
    a = decor["a"]
    b = camion(achats, a.fournisseur_id, [_ligne(decor, "bleu", "PB-BROUILLON", 12)])
    page = ok(achats.get("/api/receptions/pesees", params={"q": "PB-BROUILLON"}))
    (ligne,) = page["elements"]
    assert ligne["reception_id"] == b["id"] and ligne["numero"] == "Brouillon"
    assert ligne["statut_reception"] == "brouillon"


def test_le_poids_des_bobines_suit_les_receptions(achats: TestClient, decor: dict) -> None:
    """Route 177 : le calcul du moteur (premier, dernier, évolution, écart au catalogue),
    avec les identifiants de la matière, des réceptions et des lots."""
    a = decor["a"]
    r1 = recevoir(achats, a.fournisseur_id, [_ligne(decor, "bleu", "BO-1", 40, nb_palettes=2)],
                  date=j(-5))  # fmt: skip
    r2 = recevoir(achats, a.fournisseur_id, [_ligne(decor, "bleu", "BO-2", 44, nb_palettes=2)])
    vue = ok(achats.get("/api/receptions/bobines", params={"matiere": decor["bleu"]}))
    x = vue["lignes"][0]
    assert x["matiere_id"] == decor["bleu"] and x["poids_catalogue"] == 2
    assert x["dernier"] == pytest.approx(2.2) and x["receptions"] >= 2
    assert x["ecart_catalogue"] == pytest.approx(0.1) and x["hors_tolerance"]
    mesures = {m["reception"]: m for m in x["historique"]}
    assert mesures[r2["numero"]]["reception_id"] == r2["id"] and mesures[r2["numero"]]["lot_id"]
    assert mesures[r1["numero"]]["poids_bobine"] == pytest.approx(2.0)
    assert vue["tolerance"] == 0.05


def test_les_listes_s_exportent_comme_a_l_ecran(achats: TestClient, decor: dict) -> None:
    """Hérité : test_achats::test_les_listes_s_exportent_comme_a_l_ecran (partie réceptions) —
    feuilles « Réceptions » / « Lignes », « Pesées », « Par matière » / « Mesures » ; mêmes
    filtres que la liste."""
    a = decor["a"]
    r = recevoir(
        achats,
        a.fournisseur_id,
        [_ligne(decor, "bleu", "EX-1", 12), _ligne(decor, "vert", "EX-2", 8, qualite="reserve")],
    )
    filtres = {"statut": "validee", "fournisseur": a.fournisseur_id}
    wb = classeur(achats.get("/api/export/receptions", params=filtres).content)
    assert wb.sheetnames == ["Réceptions", "Lignes"]
    lignes = list(wb["Réceptions"].iter_rows(values_only=True))
    assert "onglet : Validées" in str(lignes[1][0])
    numeros = {x[0] for x in lignes[4:]}
    liste = ok(achats.get("/api/receptions", params=filtres))["elements"]
    assert numeros == {x["numero"] for x in liste} and r["numero"] in numeros
    lots = {x[5] for x in wb["Lignes"].iter_rows(min_row=5, values_only=True)}
    assert {"EX-1", "EX-2"} <= lots
    wb = classeur(achats.get("/api/export/receptions/pesees",
                             params={"ecarts": True, "q": r["numero"]}).content)  # fmt: skip
    qualites = {x[20] for x in wb["Pesées"].iter_rows(min_row=6, values_only=True)}
    assert qualites == {"Sous réserve"}
    wb = classeur(achats.get("/api/export/receptions/bobines", params={"q": "lect bleu"}).content)
    assert wb.sheetnames == ["Par matière", "Mesures"]
    refs = {x[0] for x in wb["Par matière"].iter_rows(min_row=6, values_only=True)}
    assert any(str(x).startswith("LECT BLEU") for x in refs)


def test_la_pastille_et_a_valider_montrent_les_brouillons(
    achats: TestClient, alimentation: TestClient, decor: dict
) -> None:
    """`contexte.COMPTEURS["receptions_brouillon"]` (pastille du menu, D et A) ; « À valider »
    (lot D5) montre les réceptions en brouillon au rang 0 et les valide comme à l'unité."""
    a = decor["a"]
    r = camion(achats, a.fournisseur_id, [_ligne(decor, "bleu", "AV-1", 3)])
    compte = ok(achats.get("/api/contexte"))["compteurs"]["receptions_brouillon"]
    assert compte >= 1
    assert ok(alimentation.get("/api/contexte"))["compteurs"].get("receptions_brouillon") is None
    vue = ok(achats.get("/api/brouillons"))
    x = next(y for y in vue["receptions"] if y["id"] == r["id"])
    assert (
        x["genre"] == "reception" and x["lien"] == f"/receptions/{r['id']}" and x["blocages"] == []
    )
    assert all(y["genre"] != "reception" for y in ok(alimentation.get("/api/brouillons"))["lignes"])
    corps = {"documents": [{"genre": "reception", "id": r["id"], "version": r["version"]}]}
    resultat = ok(achats.post("/api/brouillons/valider", json=corps))
    assert [y["id"] for y in resultat["valides"]] == [r["id"]]
    assert ok(achats.get(f"/api/receptions/{r['id']}"))["statut"] == "validee"


def test_chaque_geste_laisse_son_historique(
    achats: TestClient, direction: TestClient, decor: dict
) -> None:
    """Journal avant/après : création, modification, validation, facture, annulation."""
    a = decor["a"]
    r = camion(achats, a.fournisseur_id, [_ligne(decor, "vert", "H-1", 4)])
    corps = {"date": j(), "fournisseur_id": a.fournisseur_id,
             "lignes": [_ligne(decor, "vert", "H-1", 5)], "version": r["version"]}  # fmt: skip
    ok(achats.put(f"/api/receptions/{r['id']}", json=corps))
    r = geste(achats, r, "valider")
    v = ok(achats.get(f"/api/receptions/{r['id']}"))["version"]
    ok(achats.put(f"/api/receptions/{r['id']}/facture", json={"version": v, "numero": "F-H"}))
    geste(achats, r, "annuler", motif="essai d'historique")
    histoire = ok(direction.get(f"/api/historique/reception/{r['id']}"))
    actions = [x["action"] for x in histoire]
    assert actions == [
        "création réception",
        "modification réception",
        "validation réception",
        "facture complétée",
        "annulation réception",
    ]
    validation = histoire[2]
    assert (
        validation["apres"]["statut"] == "validee" and validation["apres"]["numero"] == r["numero"]
    )
