"""Le coût d'un dossier (lot D7) : frais au poids et à la valeur, frais sans marchandise,
frais hors norme, avoirs, facture rapprochée, répartition figée, et le coût de revient d'un lot
au millionième jusque dans le coût moyen. Preuves héritées de `test_importations`,
`test_importations_second_audit`, `test_parcours`, `test_valeur_et_dates` (domaine 8).
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.importations import Import, a_la_main, fiche, frais, geste, ligne, ouvrir
from fabriques.receptions import camion, ok
from fabriques.receptions import facture as facture_reception
from fabriques.receptions import geste as geste_reception
from fabriques.referentiels import poste_frais, unique
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.calcul.valorisation import couts_du_journal
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import DossierFrais, Lot, Matiere, Mouvement, PosteFrais
from gestion_mp_pro.services import donnees_moteur, horloge


def _cours(client: TestClient, d: dict[str, Any], cours: float) -> dict[str, Any]:
    """Un cours pour toutes les marchandises en devise du dossier."""
    corps = {"version": fiche(client, d["id"])["version"], "cours": cours}
    return ok(client.put(f"/api/dossiers/{d['id']}/cours", json=corps))  # type: ignore[no-any-return]


def _poste(code: str, cle: str = "valeur") -> str:
    """Un poste de frais à soi (code unique), à la clé donnée ; rend son code."""
    vrai = unique(code)[-16:].replace("-", "_")
    poste_frais(code=vrai, cle=cle, libelle=f"{code} d'essai")
    return vrai


def _changer_cle(direction: TestClient, code: str, cle: str) -> Any:
    """La clé d'un poste changée par la direction (route 36, lot D1)."""
    p = next(x for x in ok(direction.get("/api/postes-frais")) if x["code"] == code)
    champs = ("libelle", "recuperable", "nature", "entre_valeur_douane", "ordre", "version")
    return ok(
        direction.put(
            f"/api/postes-frais/{p['id']}", json={**{k: p[k] for k in champs}, "cle": cle}
        )
    )


def _regler(frais_id: int, le: Any) -> None:
    """Le règlement d'un frais posé en base (la route 229 de l'échéancier est au lot D8)."""
    with sessions()() as s, s.begin():
        x = s.get(DossierFrais, frais_id)
        assert x is not None
        x.payee_le = le


def test_le_cout_d_un_lot_au_millionieme_jusqu_au_cout_moyen(achats: TestClient) -> None:
    """Le coût de revient complet d'un lot importé, au millionième, et son effet sur le coût
    moyen (VERIFICATION § 5, PLAN-DE-RECETTE étape 9 ; audit de Gestion MP : 32,747048 MAD/kg).

    Calcul à la main : A = 1 250 kg × 2,65 = 3 312,50 ; B = 750 kg × 3,10 = 2 325 (devise) ; au
    cours payé 9,8765 : A = 32 715,90625 MAD, B = 22 962,8625 MAD (total 55 678,76875). Fret
    4 200 et droits 3 500 à la valeur : A en porte 32 715,90625 / 55 678,76875 = 0,5875831…,
    soit 4 524,390244 ; manutention 1 000 au poids : 625 ; TVA 12 000 hors coût. Coût de A :
    32 715,90625 + 5 149,390244 = 37 865,296494 MAD, soit **30,292237 MAD/kg** ; B : 35,351296."""
    imp = Import.nouveau(cours="10")
    manut = _poste("MANUT", "poids")
    r = imp.recevoir(achats, "MIL", [("A", "MIL-A", 1250, 2.65), ("B", "MIL-B", 750, 3.10)])
    d = _cours(achats, ouvrir(achats, imp.f("MIL")), 9.8765)
    for code, montant in (("FRET", 4200), ("DD", 3500), (manut, 1000), ("TVA", 12_000)):
        d = frais(achats, d, code, montant)
    a, b = ligne(d, "IMP A"), ligne(d, "IMP B")
    assert a["valeur_mad"] == pytest.approx(32_715.90625, abs=1e-9)
    assert a["revient_kg"] == pytest.approx(30.292237, abs=5e-7)
    assert b["revient_kg"] == pytest.approx(35.351296, abs=5e-7)
    assert d["revient_mad"] == pytest.approx(55_678.76875 + 4200 + 3500 + 1000, abs=1e-6)
    assert d["decaisse_mad"] == pytest.approx(d["revient_mad"] + 12_000, abs=1e-6)
    d = geste(achats, d, "cloturer", alertes_lues=True)
    with sessions()() as s:
        lot_a = s.scalar(select(Lot.id).where(Lot.matiere_id == imp.matieres["A"]))
        entree = s.scalar(select(Mouvement.id).where(Mouvement.lot_id == lot_a))
        donnees_moteur.invalider()
        couts = couts_du_journal(donnees_moteur.charger(s))
    assert couts.unitaire[entree] == pytest.approx(30.292237, abs=5e-7)
    assert r["numero"] in d["receptions"][0]["numero"]


def test_le_dossier_d_importation_depuis_la_facture(achats: TestClient) -> None:
    """Hérité : test_parcours::test_le_dossier_d_importation_depuis_la_facture — numéro
    `NN/AA` ; (998 + 600 + 805) × 2,6 × 10 ; droits 6 000 dans le coût, TVA 13 000 hors coût ;
    double ouverture 409 ; réception en dossier non annulable ; clos : frais 409."""
    imp = Import.nouveau(cours="10")
    lots = [("POIL", "PA", 998, 2.6), ("POIL", "PB", 600, 2.6), ("POIL", "PC", 805, 2.6)]
    rec = imp.recevoir(achats, "PARC", lots)
    d = _cours(achats, ouvrir(achats, imp.f("PARC")), 10)
    assert d["numero"].split("/")[1] == "26"
    marchandise = (998 + 600 + 805) * 2.6 * 10
    d = frais(achats, frais(achats, d, "DD", 6000), "TVA", 13_000)
    assert d["marchandise_mad"] == pytest.approx(marchandise)
    assert d["revient_mad"] == pytest.approx(marchandise + 6000)
    assert d["decaisse_mad"] == pytest.approx(marchandise + 19_000)
    assert sum(x["charges_mad"] for x in d["lignes"]) == pytest.approx(6000)
    r = achats.post("/api/dossiers", json={"facture_id": d["facture"]["id"]})
    assert r.status_code == 409
    assert geste_reception(achats, rec, "annuler", 409, motif="erreur")["code"] == "documents_lies"
    d = geste(achats, d, "cloturer", alertes_lues=True)
    assert frais(achats, d, "DD", 1, 409)["code"] == "dossier_clos"


def test_frais_sans_marchandise_a_part_partout(achats: TestClient) -> None:
    """Hérité : test_importations::test_frais_sans_marchandise_a_part_partout — un dossier vide
    à 6 547 654 MAD de droits : dans aucun coût, à part dans la liste et dans l'analyse, et
    les deux s'accordent."""
    d = a_la_main(achats, date_arrivee="2019-06-01")
    d = frais(achats, d, "DD", 6_547_654)
    assert d["charges_mad"] == 0 and d["revient_mad"] == 0
    assert d["charges_non_reparties_mad"] == pytest.approx(6_547_654)
    assert "frais non répartis" in d["a_verifier"]
    liste = ok(achats.get("/api/dossiers"))
    r = ok(achats.get("/api/analyse/revient"))
    assert r["total_charges_mad"] == pytest.approx(sum(x["charges_mad"] for x in liste))
    assert {"dossier": d["numero"], "montant": pytest.approx(6_547_654)} in r[
        "dossiers_non_repartis"
    ]
    assert r["ids_dossiers"][d["numero"]] == d["id"]


def test_des_frais_aberrants_se_signalent(achats: TestClient) -> None:
    """Hérité : test_importations::test_des_frais_aberrants_se_signalent — 3 300 au cours
    10,95 = 36 135 MAD ; 3 millions de transit : au-delà du seuil réglé (100 %), à vérifier."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "ABR", [("SBR", "S-1", 3000, 1.1)])
    d = _cours(achats, ouvrir(achats, imp.f("ABR")), 10.95)
    assert not d["surcout_aberrant"] and d["seuil_surcout"] == pytest.approx(1.0)
    assert d["marchandise_mad"] == pytest.approx(36_135)
    d = frais(achats, d, "TRANSIT", 3_000_000)
    assert d["surcout_aberrant"] and d["surcout"] > 50
    assert "Les frais dépassent 100\u00a0% de l'achat : les vérifier." in d["alertes"]
    assert "frais au-delà de 100\u00a0% de l'achat" in d["a_verifier"]
    x = d["frais"][0]
    r = achats.delete(f"/api/dossiers/{d['id']}/frais/{x['id']}", params={"version": x["version"]})
    assert not ok(r)["surcout_aberrant"]


def test_un_dossier_pese_en_kilos(achats: TestClient, direction: TestClient) -> None:
    """Hérité :
    test_importations_second_audit::test_un_dossier_pese_en_kilos,
    test_importations_second_audit::test_corriger_la_densite_ne_bouge_pas_un_dossier_clos,
    test_valeur_et_dates::test_corriger_la_densite_ne_bouge_pas_un_dossier_clos —
    100 kg de fil et 100 kg de bande (prix au mètre, 0,05 kg/ml) : la manutention au poids fait 1
    000 chacun, la bande revient à 3 000 MAD, 30 MAD/kg ; corriger la densité ne bouge pas un
    dossier clos."""
    imp = Import.nouveau(cours="10")
    imp.matiere("BANDE", role="Ruban", unite_prix="ml", densite="0.05")
    manut = _poste("A2MAN", "poids")
    imp.recevoir(achats, "A2-MET", [("FIL", "A2F", 100, 2), ("BANDE", "A2B", 100, 2)], montant=400)
    d = frais(achats, _cours(achats, ouvrir(achats, imp.f("A2-MET")), 10), manut, 2000)
    bande = ligne(d, "IMP BANDE")
    assert d["poids"] == pytest.approx(200) and bande["quantite_kg"] == 100
    assert bande["revient_mad"] == pytest.approx(3000) and bande["revient_kg"] == pytest.approx(30)
    avant = {
        x["id"]: x["revient_mad"] for x in geste(achats, d, "cloturer", alertes_lues=True)["lignes"]
    }
    with sessions()() as s, s.begin():
        m = s.get(Matiere, imp.matieres["BANDE"])
        assert m is not None
        m.densite = m.densite * 10
    d = fiche(achats, d["id"])
    assert {x["id"]: x["revient_mad"] for x in d["lignes"]} == pytest.approx(avant)
    assert d["poids"] == pytest.approx(200) and direction


def test_changer_la_cle_garde_une_piece_et_son_reglement(
    achats: TestClient, direction: TestClient
) -> None:
    """Hérité :
    test_importations_second_audit::test_changer_la_cle_garde_une_piece_et_son_reglement —
    24 000 et 12 000 MAD, transit 3 000 à la valeur : 26 000 / 13 000 ; clos, le poste passe au
    poids : rien ne bouge, une seule pièce, réglée, parts 2 000 / 1 000 ; rouvert et son règlement
    annulé, un autre montant efface la répartition figée (1 000 / 100)."""
    imp = Import.nouveau(cours="12")
    transit = _poste("A2TR", "valeur")
    imp.recevoir(achats, "A2-CLE", [("FIL", "A2F-2", 1000, 2), ("FIL", "A2F-3", 100, 10)])
    d = frais(achats, ouvrir(achats, imp.f("A2-CLE")), transit, 3000, piece="T-1")
    cid = d["frais"][0]["id"]
    _regler(cid, horloge.aujourd_hui())
    d = geste(achats, d, "cloturer", alertes_lues=True)
    avant = {x["lot"]: x["revient_mad"] for x in d["lignes"]}
    assert sorted(avant.values()) == pytest.approx([13_000, 26_000])
    assert _changer_cle(direction, transit, "poids")["parts_figees"] >= 1
    d = fiche(achats, d["id"])
    assert {x["lot"]: x["revient_mad"] for x in d["lignes"]} == pytest.approx(avant)
    (x,) = d["frais"]
    assert x["id"] == cid and x["payee_le"] == horloge.aujourd_hui().isoformat()
    assert sorted(p["montant"] for p in x["parts"]) == pytest.approx([1000, 2000])
    assert [e["payee_le"] for e in d["echeancier"] if e["frais_id"] == cid] == [x["payee_le"]]
    d = geste(achats, d, "rouvrir")
    corps = {"version": x["version"], "poste_id": x["poste_id"], "montant": 1100}
    refus = achats.put(f"/api/dossiers/{d['id']}/frais/{cid}", json=corps)
    assert refus.status_code == 409 and "Ce frais est réglé" in refus.json()["detail"]
    _regler(cid, None)
    corps["version"] = fiche(achats, d["id"])["frais"][0]["version"]
    d = ok(achats.put(f"/api/dossiers/{d['id']}/frais/{cid}", json=corps))
    assert d["frais"][0]["parts"] == []
    assert sorted(y["charges_mad"] for y in d["lignes"]) == pytest.approx([100, 1000])


def test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception(achats: TestClient) -> None:
    """Hérité :
    test_importations_second_audit::test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception,
    test_importations_second_audit::test_la_saisie_a_la_main_est_reservee_aux_dossiers_d_avant — la
    réception d'un lot déjà saisi à la main entre à son prix (2 × 10), pas à 1 000 MAD/kg ; une
    ligne à la main ne se saisit plus sur un lot reçu ; ni dans le dossier d'une facture."""
    imp = Import.nouveau(cours="10")
    lot = unique("A2L")
    d = a_la_main(achats, date_arrivee="2019-03-01")
    corps = {
        "matiere_id": imp.matiere("BANDE"),
        "lot_numero": lot,
        "quantite_kg": 10,
        "valeur_devise": 10_000,
    }
    d = geste(achats, d, "lignes", **corps)
    ligne_recue = {**imp.ligne("BANDE", "X", 100, 2), "lot_numero": lot}
    rec = geste_reception(achats, camion(achats, imp.fournisseur_id, [ligne_recue]), "valider")
    with sessions()() as s:
        lot_id = s.scalar(select(Lot.id).where(Lot.numero == lot))
        entree = s.scalar(select(Mouvement.id).where(Mouvement.lot_id == lot_id))
        donnees_moteur.invalider()
        couts = couts_du_journal(donnees_moteur.charger(s))
    assert couts.unitaire[entree] == pytest.approx(2.0 * 10)
    refus = geste(achats, d, "lignes", 409, **{**corps, "quantite_kg": 1, "valeur_devise": 1})
    assert refus["detail"].startswith(f"Le lot « {lot} » de ") and rec["numero"] in refus["detail"]


def test_frais_aberrant_sur_une_ligne_et_avoir_negatif(achats: TestClient) -> None:
    """Hérité :
    test_importations_second_audit::test_frais_aberrant_sur_une_ligne_et_avoir_negatif —
    5 000 MAD sur une ligne de 220 : hors norme sur cette ligne seule ; un avoir qui la rendrait
    négative est refusé, à l'ajout comme à la modification."""
    imp = Import.nouveau(cours="10")
    transit = _poste("A2TR", "valeur")
    imp.recevoir(achats, "A2-ABR", [("FIL", "A2F-7", 1000, 2), ("FIL", "A2F-8", 11, 2)])
    d = ouvrir(achats, imp.f("A2-ABR"))
    petite = next(x for x in d["lignes"] if x["valeur_mad"] == pytest.approx(220))
    d = frais(achats, d, transit, 5000, ligne_id=petite["id"])
    assert not d["surcout_aberrant"] and d["lignes_aberrantes"] == [petite["reference"]]
    assert next(x for x in d["lignes"] if x["id"] == petite["id"])["aberrante"]
    refus = frais(achats, d, transit, -6000, 409, ligne_id=petite["id"])
    assert refus["detail"].startswith(f"Ce frais rendrait {petite['reference']} négatif (")
    x = d["frais"][0]
    corps = {
        "version": x["version"],
        "poste_id": x["poste_id"],
        "montant": -300,
        "ligne_id": petite["id"],
    }
    assert achats.put(f"/api/dossiers/{d['id']}/frais/{x['id']}", json=corps).status_code == 409
    d = fiche(achats, d["id"])
    assert len(d["frais"]) == 1 and d["frais"][0]["montant"] == 5000


def test_la_facture_se_rapproche_de_la_marchandise_recue(achats: TestClient) -> None:
    """Hérité :
    test_importations_second_audit::test_la_facture_se_rapproche_de_la_marchandise_recue —
    4 598 facturés pour 2 541,91 × 2 = 5 083,82 reçus : écart −485,82, hors tolérance (2 %) ; le
    coût reste à la pesée × prix (50 838,20 MAD) ; à 5 100, dans la tolérance."""
    imp = Import.nouveau(cours="10")
    rec = imp.recevoir(achats, "A2-FAC", [("FIL", "A2F-9", 2541.91, 2)], montant=4598)
    d = ouvrir(achats, imp.f("A2-FAC"))
    e = d["ecart_facture"]
    assert e["hors_tolerance"] and e["recu"] == pytest.approx(5083.82)
    assert e["ecart"] == pytest.approx(4598 - 5083.82) and e["part"] == pytest.approx(
        -485.82 / 5083.82
    )
    assert d["marchandise_mad"] == pytest.approx(50_838.2)
    assert "facture ≠ marchandise reçue" in d["a_verifier"]
    assert any(x.startswith("La facture s'écarte de −9,6") for x in d["alertes"])
    facture_reception(achats, rec, montant=5100)
    assert not fiche(achats, d["id"])["ecart_facture"]["hors_tolerance"]


def test_echeancier_du_dossier_regle_et_estime(achats: TestClient) -> None:
    """Hérité (partie dossier) :
    test_importations_second_audit::test_echeanciers_regle_estime_et_clos_a_dater —
    la facture sans montant vaut ce que sa marchandise a apporté (50 × 2 = 100, « estimé ») ; un
    frais sans échéance vient après ; ce qui est réglé le dit."""
    imp = Import.nouveau(cours="10")
    transit = _poste("A2TR", "valeur")
    imp.recevoir(achats, "A2-ECH", [("FIL", "A2F-10", 50, 2)])
    d = frais(achats, ouvrir(achats, imp.f("A2-ECH")), transit, 700, prestataire="TRANSIT OUBLIÉ")
    marchandise = next(x for x in d["echeancier"] if x["nature"] == "marchandise")
    frais_ = next(x for x in d["echeancier"] if x["nature"] == "frais")
    assert marchandise["nature"] == "marchandise" and marchandise["montant"] == pytest.approx(100)
    assert marchandise["estime"] and marchandise["payee_le"] is None and not marchandise["detachee"]
    assert frais_["tiers"] == "TRANSIT OUBLIÉ" and frais_["echeance"] is None


def test_une_ligne_en_dirhams_se_fige_a_sa_valeur(
    achats: TestClient, direction: TestClient
) -> None:
    """Hérité : test_importations_second_audit::test_une_ligne_en_dirhams_se_fige_a_sa_valeur,
    et (partie API) test_importations::test_une_ligne_en_dirhams_n_a_pas_de_cours —
    1 000 et 3 000 MAD, transit 400 à la valeur : 1 100 / 3 300, inchangés après un changement
    de clé (répartition figée) ; une marchandise en MAD n'a jamais de cours (contrainte)."""
    imp = Import.nouveau(code="MAD", pays="")
    transit = _poste("A2TR", "valeur")
    d = a_la_main(achats, date_arrivee="2018-03-01")
    for lot, valeur in (("A2M-1", 1000), ("A2M-2", 3000)):
        corps = {
            "matiere_id": imp.matiere("FIL"),
            "lot_numero": unique(lot),
            "quantite_kg": 100,
            "valeur_devise": valeur,
        }
        d = geste(achats, d, "lignes", **corps)
    r = achats.put(
        f"/api/dossiers/{d['id']}/lignes/{d['lignes'][0]['id']}",
        json={"version": d["version"], "cours": 9.58},
    )
    assert (
        r.status_code == 422
        and r.json()["detail"] == "Une marchandise facturée en MAD n'a pas de cours."
    )
    d = frais(achats, d, transit, 400)
    avant = {
        x["valeur_mad"]: x["revient_mad"]
        for x in geste(achats, d, "cloturer", alertes_lues=True)["lignes"]
    }
    assert avant == pytest.approx({1000: 1100, 3000: 3300})
    _changer_cle(direction, transit, "poids")
    apres = {x["valeur_mad"]: x["revient_mad"] for x in fiche(achats, d["id"])["lignes"]}
    assert apres == pytest.approx(avant)
    with sessions()() as s:
        assert s.scalar(select(PosteFrais.cle).where(PosteFrais.code == transit)) == "poids"
