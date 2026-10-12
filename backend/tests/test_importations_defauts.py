"""Les défauts de Gestion MP (domaine B) qu'aucun dossier de PRO ne reproduit (lot D7) : frais
réglé intouchable (B-01), dossier annulé au lieu de supprimé (B-02), dossier à la main
d'avant la mise en service (B-03), TVA non répartie (B-04), écart des droits au serveur (B-05),
second camion local (B-06), échéancier qui garde sa facture (B-07), cours figé à la clôture
rendu vide (B-08), période close (E-02), montants à la française au journal.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import reglage
from fabriques.importations import (
    Import,
    a_la_main,
    facture_id,
    fiche,
    frais,
    geste,
    numero_ancien,
    ouvrir,
    poste,
)
from fabriques.receptions import JOUR, ok
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import DossierFrais, DossierLigne, Journal
from gestion_mp_pro.services import devises, horloge


def _regler(frais_id: int, le: object) -> None:
    """Le règlement d'un frais posé en base (la route 229 de l'échéancier est au lot D8)."""
    with sessions()() as s, s.begin():
        x = s.get(DossierFrais, frais_id)
        assert x is not None
        x.payee_le = le


def _modifier_frais(client: TestClient, d: dict, fid: int, code: int, **corps: object) -> dict:
    x = next(y for y in fiche(client, d["id"])["frais"] if y["id"] == fid)
    base = {"version": x["version"], "poste_id": x["poste_id"], "montant": x["montant"]}
    r = client.put(f"/api/dossiers/{d['id']}/frais/{fid}", json={**base, **corps})
    assert r.status_code == code, r.text
    return r.json()  # type: ignore[no-any-return]


def test_frais_regle_ne_se_modifie_ni_ne_se_retire(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_frais_regle_ne_se_modifie_ni_ne_se_retire (B-01, I20) —
    poste, montant, marchandise figés ; la pièce ne se date pas après le règlement ; le frais
    ne se retire pas ; il ne disparaît pas avec son dossier (annulé, il reste réglé)."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-REG", [("FIL", "DBR-1", 500, 2)])
    d = frais(achats, ouvrir(achats, imp.f("DB-REG")), "TRANSIT", 1500, piece="T-9")
    cid = d["frais"][0]["id"]
    _regler(cid, JOUR)
    assert fiche(achats, d["id"])["frais"][0]["blocage"].startswith("Frais réglé le 03/08/2026")
    for corps in (
        {"montant": 1200},
        {"poste_id": poste("PORT")},
        {"ligne_id": d["lignes"][0]["id"]},
    ):
        refus = _modifier_frais(achats, d, cid, 409, **corps)
        assert refus["detail"].startswith("Ce frais est réglé (le 03/08/2026, 1 500,00 MAD)")
    d = _modifier_frais(achats, d, cid, 200, piece="T-9", commentaire="facture du transitaire")
    assert d["frais"][0]["payee_le"] == JOUR.isoformat()
    refus = _modifier_frais(achats, d, cid, 422, date_piece=(JOUR + timedelta(days=1)).isoformat())
    assert "après son règlement" in refus["detail"]
    x = fiche(achats, d["id"])["frais"][0]
    r = achats.delete(f"/api/dossiers/{d['id']}/frais/{cid}", params={"version": x["version"]})
    assert r.status_code == 409 and r.json()["detail"].endswith(
        "Saisir un avoir (montant négatif)."
    )
    d = geste(achats, d, "annuler", motif="ouvert sur la mauvaise facture")
    assert d["frais"][0]["payee_le"] == JOUR.isoformat() and d["statut"] == "annule"


def test_un_dossier_s_annule_et_garde_son_numero(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_dossier_numerote_ne_se_supprime_pas (B-02, M65) — rien ne
    se supprime : le dossier s'annule (motif exigé), garde son numéro, libère sa facture et
    détache ses marchandises ; un nouveau dossier les reprend sous le numéro suivant ; annulé,
    il ne se touche plus et sort du coût."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-NUM", [("FIL", "DBN-1", 100, 2)])
    d = frais(achats, ouvrir(achats, imp.f("DB-NUM")), "DD", 90)
    assert achats.delete(f"/api/dossiers/{d['id']}").status_code == 405
    assert geste(achats, d, "annuler", 422, motif="x")["code"] == "motif_requis"
    d = geste(achats, d, "annuler", motif="mauvaise facture")
    assert d["statut"] == "annule" and d["annule_par"] == "Achats" and d["annule_le"]
    assert all(x["reception_ligne_id"] is None for x in d["lignes"]) and d["nb_frais"] == 1
    assert d["revient_mad"] == pytest.approx(200 * 10 + 90)
    actions = d["actions"]
    assert (
        actions["annuler"] == "Ce dossier est déjà annulé."
        and actions["frais"] == actions["modifier"]
    )
    assert actions["modifier"] == "Ce dossier est annulé : il ne se modifie plus."
    assert geste(achats, d, "rouvrir", 409)["detail"] == actions["modifier"]
    assert geste(achats, d, "annuler", 409, motif="encore")["code"] == "deja_annule"
    nouveau = ouvrir(achats, imp.f("DB-NUM"))
    assert nouveau["numero"] != d["numero"] and nouveau["nb_lignes"] == 1
    assert int(nouveau["numero"].split("/")[0]) > int(d["numero"].split("/")[0])
    assert d["id"] not in {x["id"] for x in ok(achats.get("/api/dossiers"))["elements"]}
    annules = ok(achats.get("/api/dossiers", params={"statut": "annule"}))["elements"]
    assert next(x for x in annules if x["id"] == d["id"])["numero"] == d["numero"]
    analyse = ok(achats.get("/api/analyse/revient", params={"q": d["numero"]}))
    assert d["numero"] not in analyse["ids_dossiers"]
    with sessions()() as s:
        detail = s.scalar(
            select(Journal.detail).where(
                Journal.action == "annulation dossier", Journal.objet_id == d["id"]
            )
        )
    assert detail == (
        f"{d['numero']} · mauvaise facture · facture {imp.f('DB-NUM')} libérée · "
        "1 frais (90,00 MAD) sortis du coût"
    )


def test_un_numero_choisi_seulement_pour_un_dossier_d_avant(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_un_numero_choisi_seulement_pour_un_dossier_d_avant — le
    dossier d'une facture prend le numéro suivant ; « 3/17 » est « 03/17 » ; un doublon → 409."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-CHOIX", [("FIL", "DBC-1", 100, 2)])
    corps = {"facture_id": facture_id(achats, imp.f("DB-CHOIX")), "numero": "99/26"}
    r = achats.post("/api/dossiers", json=corps)
    assert r.status_code == 422 and "numéro suivant" in r.json()["detail"]
    voulu = numero_ancien()
    court = f"{int(voulu.split('/')[0])}/{voulu.split('/')[1]}"
    d = a_la_main(achats, numero=court)
    assert d["numero"] == voulu and d["a_la_main"] and not d["repris"]
    r = achats.post("/api/dossiers", json={"numero": voulu, "date_arrivee": "2018-01-02"})
    assert r.status_code == 409 and r.json()["code"] == "numero_pris"
    r = achats.post("/api/dossiers", json={"numero": "A2/18", "date_arrivee": "2018-01-02"})
    assert r.status_code == 422 and "NN/AA" in r.json()["detail"]


def test_dossier_a_la_main_refuse_apres_mise_en_service(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_dossier_a_la_main_refuse_apres_mise_en_service et
    test_defauts_b::test_une_arrivee_ne_se_date_pas_dans_le_futur (B-03) — après la première
    réception validée, une création sans facture est refusée ; sans date aussi ; une date à venir
    se refuse ; la date d'arrivée ne bouge pas dans une période close."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-SERVICE", [("FIL", "DBS-1", 100, 2)])
    r = achats.post("/api/dossiers", json={"date_arrivee": horloge.aujourd_hui().isoformat()})
    assert r.status_code == 422 and "mise en service" in r.json()["detail"]
    r = achats.post("/api/dossiers", json={"numero": numero_ancien()})
    assert r.status_code == 422 and "mise en service" in r.json()["detail"]
    demain = (horloge.aujourd_hui() + timedelta(days=1)).isoformat()
    r = achats.post("/api/dossiers", json={"date_arrivee": demain})
    assert r.status_code == 422 and "futur" in r.json()["detail"]
    d = a_la_main(achats, date_arrivee="2018-05-02")
    entete = {"version": d["version"], "libelle": "", "banque": "", "commentaire": ""}
    r = achats.put(
        f"/api/dossiers/{d['id']}",
        json={**entete, "date_arrivee": horloge.aujourd_hui().isoformat()},
    )
    assert r.status_code == 422 and "mise en service" in r.json()["detail"]
    r = achats.put(f"/api/dossiers/{d['id']}", json={**entete, "date_arrivee": demain})
    assert r.status_code == 422 and "futur" in r.json()["detail"]
    corps = {
        "matiere_id": imp.matiere("FIL"),
        "lot_numero": f"DBA-{d['id']}",
        "quantite_kg": 50,
        "valeur_devise": 100,
    }
    d = geste(achats, d, "lignes", **corps)
    entete["version"] = d["version"]
    with reglage("date_cloture", "2019-12-31"):
        r = achats.put(f"/api/dossiers/{d['id']}", json={**entete, "date_arrivee": "2018-06-01"})
        assert r.status_code == 409 and r.json()["code"] == "cout_periode_close"
        assert "(date d'arrivée refusé)" in r.json()["detail"]
    d = ok(achats.put(f"/api/dossiers/{d['id']}", json={**entete, "date_arrivee": "2018-06-01"}))
    assert d["date_arrivee"] == "2018-06-01"
    entete["version"] = d["version"]
    d = ok(achats.put(f"/api/dossiers/{d['id']}", json={**entete, "date_arrivee": None}))
    assert d["date_arrivee"] is None
    r = achats.put(
        f"/api/dossiers/{d['id']}", json={**entete, "numero": "01/18", "date_arrivee": None}
    )
    assert r.status_code == 422


def test_cloture_refusee_tva_non_repartie(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_cloture_refusee_tva_non_repartie (B-04) — une marchandise à
    0 MAD : la TVA ne trouve où se poser, et bloque la clôture comme les autres frais."""
    imp = Import.nouveau(code="MAD", pays="")
    d = a_la_main(achats)
    corps = {
        "matiere_id": imp.matiere("FIL"),
        "lot_numero": f"DBT-{d['id']}",
        "quantite_kg": 10,
        "valeur_devise": 0,
    }
    d = frais(achats, geste(achats, d, "lignes", **corps), "TVA", 50)
    assert d["tva_non_repartie_mad"] == pytest.approx(50) and d["charges_non_reparties_mad"] == 0
    refus = geste(achats, d, "cloturer", 409, alertes_lues=True)
    assert refus["detail"] == d["actions"]["cloturer"]
    assert refus["detail"].startswith("Des frais ne trouvent pas de marchandise où se répartir")


def test_droits_ecart_calcule_au_serveur(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_droits_ecart_calcule_au_serveur (B-05, partie API) — le
    taux de TPI et l'écart des droits viennent du serveur."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-DROITS", [("FIL", "DBDR-1", 100, 2)])
    d = ouvrir(achats, imp.f("DB-DROITS"))
    assert d["taux_tpi_import"] == pytest.approx(0.0025) and d["droits_ecart_mad"] is None
    assert "Aucun droit de douane saisi." in d["alertes"] and "Aucune TVA saisie." in d["alertes"]


def test_second_camion_local_visible_pour_son_dossier(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_second_camion_local_visible_pour_son_dossier (B-06)."""
    loc = Import.nouveau(code="MAD", pays="MAROC")
    loc.recevoir(achats, "DB-LOC", [("FIL", "DBLO-1", 100, 2)])
    d = ouvrir(achats, loc.f("DB-LOC"), local_confirme=True)
    loc.recevoir(achats, "DB-LOC", [("FIL", "DBLO-2", 50, 2)])
    attente = ok(achats.get("/api/dossiers/a-rattacher"))
    suite = [x for x in attente["factures"] if x["numero"] == loc.f("DB-LOC")]
    assert suite and suite[0]["dossier"] == d["numero"] and suite[0]["lignes"] == 1
    loc.recevoir(achats, "DB-LOC-2", [("FIL", "DBLO-3", 10, 2)])
    assert loc.f("DB-LOC-2") not in {
        x["numero"] for x in ok(achats.get("/api/dossiers/a-rattacher"))["factures"]
    }


def test_echeancier_dossier_garde_sa_facture_apres_detachement(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_echeancier_dossier_garde_sa_facture_apres_detachement (B-07)
    — amendé par la décision de Mohamed du 12/10/2026 (lot PLUSIEURS-FACTURES) : la facture dont
    on détache la dernière réception **quitte** le dossier et attend de nouveau son dossier ; elle
    ne se perd pas pour autant : elle reste à payer dans l'échéancier général, et revient dans
    « En attente de dossier »."""
    imp = Import.nouveau()
    rec = imp.recevoir(achats, "DB-DET", [("FIL", "DBD-1", 300, 2)], montant=600)
    d = ouvrir(achats, imp.f("DB-DET"))
    assert [x["quoi"] for x in d["echeancier"]] == [f"Facture {imp.f('DB-DET')}"]
    d = geste(achats, d, "detacher", reception_id=rec["id"])
    assert d["nb_lignes"] == 0 and d["factures"] == [] and d["echeancier"] == []
    attente = ok(achats.get("/api/dossiers/a-rattacher"))["factures"]
    (f,) = [x for x in attente if x["numero"] == imp.f("DB-DET")]
    assert f["dossier_id"] is None and f["lignes"] == 1
    assert imp.f("DB-DET") in str(ok(achats.get("/api/echeancier")))


def test_rouvrir_journalise_les_cours_figes_retires(achats: TestClient) -> None:
    """Hérité : test_defauts_b::test_rouvrir_signale_cours_figes (B-08, partie journal) — le
    cours saisi (banque) reste ; le cours figé d'office se retire, et le journal le dit."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "DB-ROUV", [("FIL", "DBRO-1", 100, 2), ("FIL", "DBRO-2", 100, 2)])
    d = ouvrir(achats, imp.f("DB-ROUV"))
    saisie = d["lignes"][1]["id"]
    corps = {"version": d["version"], "cours": 9.5, "commentaire": "banque"}
    ok(achats.put(f"/api/dossiers/{d['id']}/lignes/{saisie}", json=corps))
    d = geste(achats, d, "cloturer", alertes_lues=True)
    d = geste(achats, d, "rouvrir", motif="facture tardive")
    lignes = {x["id"]: x for x in d["lignes"]}
    assert lignes[saisie]["cours"] == 9.5 and lignes[saisie]["cours_origine"] == "banque"
    assert [x["cours"] for i, x in lignes.items() if i != saisie] == [None]
    with sessions()() as s:
        detail = s.scalar(
            select(Journal.detail).where(
                Journal.action == "réouverture dossier", Journal.objet_id == d["id"]
            )
        )
    assert detail is not None and detail.startswith(f"{d['numero']} · facture tardive")
    assert "cours du jour figé à la clôture retiré" in detail


def test_une_periode_close_fige_et_garde_ses_cours(achats: TestClient) -> None:
    """E-02 avec le lot D1 : une marchandise sans cours entrée en période close prend le cours
    du jour (`periode_close`) ; le coût de ce mois ne bouge plus (frais refusé) ; la clôture du
    dossier reste permise et garde ce cours ; la réouverture ne le retire pas."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "DB-PER", [("FIL", "DBP-1", 100, 2)])
    d = ouvrir(achats, imp.f("DB-PER"))
    with reglage("date_cloture", JOUR.isoformat()):
        with sessions()() as s, s.begin():
            devises.figer_cours_periode_close(s, None, jusqu_au=JOUR)
        d = fiche(achats, d["id"])
        assert d["lignes"][0]["cours"] == 10 and d["lignes"][0]["cours_origine"] == "periode_close"
        refus = frais(achats, d, "DD", 100, 409)
        assert refus["code"] == "cout_periode_close" and "(frais refusé)" in refus["detail"]
        d = geste(achats, d, "cloturer", alertes_lues=True)
        assert d["lignes"][0]["cours_origine"] == "periode_close"
        assert geste(achats, d, "rouvrir", 409)["code"] == "cout_periode_close"
    d = geste(achats, d, "rouvrir")
    assert d["lignes"][0]["cours"] == 10 and d["lignes"][0]["cours_origine"] == "periode_close"


def test_le_journal_ecrit_les_montants_a_la_francaise(
    achats: TestClient, direction: TestClient
) -> None:
    """Hérité : test_defauts_b::test_le_journal_ecrit_les_montants_a_la_francaise — « DD 1 234,50
    MAD » ; l'historique du dossier porte chaque geste."""
    imp = Import.nouveau()
    imp.recevoir(achats, "DB-FR", [("FIL", "DBFR-1", 100, 2)])
    d = frais(achats, ouvrir(achats, imp.f("DB-FR")), "DD", 1234.5)
    with sessions()() as s:
        detail = s.scalar(
            select(Journal.detail).where(Journal.action == "frais", Journal.objet_id == d["id"])
        )
    assert detail == f"{d['numero']} · DD 1 234,50 MAD"
    historique = ok(direction.get(f"/api/historique/dossier/{d['id']}"))
    assert [x["action"] for x in historique][:2] in (
        ["ouverture dossier", "frais"],
        ["frais", "ouverture dossier"],
    )
    with sessions()() as s:
        assert (
            s.scalar(select(DossierLigne.cours).where(DossierLigne.dossier_id == d["id"])) is None
        )


def test_l_ecart_de_tva_tolere_se_lit_dans_son_reglage(achats: TestClient) -> None:
    """E-10 (C29 et la fiche, Gestion MP 26459d4) : l'écart de TVA toléré de la fiche est
    |TVA attendue| × `toler_tva_import` — le même réglage que le contrôle C29."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "DB-TOL", [("FIL", "DBTO-1", 100, 2)])
    d = ouvrir(achats, imp.f("DB-TOL"))
    attendue = d["tva_attendue_mad"]
    assert d["tva_ecart_tolere_mad"] == pytest.approx(attendue * 0.05)
    with reglage("toler_tva_import", "0.1"):
        d = fiche(achats, d["id"])
        assert d["toler_tva_import"] == pytest.approx(0.1)
        assert d["tva_ecart_tolere_mad"] == pytest.approx(attendue * 0.1)
        d = frais(achats, d, "TVA", round(attendue * 1.08, 2))
        assert d["tva_ecart_mad"] is None and "TVA ≠ attendue" not in d["a_verifier"]
    d = fiche(achats, d["id"])
    assert d["tva_ecart_mad"] == pytest.approx(attendue * 0.08, abs=0.01)
    assert "TVA ≠ attendue" in d["a_verifier"] and "TVA ≠ attendue." in d["alertes"]
