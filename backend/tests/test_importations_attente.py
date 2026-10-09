"""Ce qui attend son dossier, le second camion, les dossiers repris (lot D7). Preuves héritées
de `test_importations` (domaine 8) : fournisseurs marocains, deux devises et cours du bon,
second camion, réception sans facture, dossier repris qui mêle deux factures, annulation d'une
réception portée par un dossier, cours figé tracé à la clôture.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, cours
from fabriques.importations import Import, facture_id, fiche, frais, geste, ouvrir
from fabriques.receptions import (
    Quai,
    camion,
    j,
    ligne_du_bon,
    menage,  # noqa: F401 — fixture du module
    ok,
    parti,
)
from fabriques.receptions import facture as facture_reception
from fabriques.receptions import geste as geste_reception
from fabriques.referentiels import unique
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Dossier, DossierLigne, Reception, ReceptionLigne
from gestion_mp_pro.modeles.enums import OrigineCours
from gestion_mp_pro.services import donnees_moteur

pytestmark = pytest.mark.usefixtures("menage")


def _attente(client: TestClient, **params: Any) -> dict[str, Any]:
    return ok(client.get("/api/dossiers/a-rattacher", params=params))  # type: ignore[no-any-return]


def _facture(client: TestClient, numero: str, **params: Any) -> dict[str, Any]:
    return next(f for f in _attente(client, **params)["factures"] if f["numero"] == numero)


def test_les_fournisseurs_marocains_n_ont_pas_de_dossier(achats: TestClient) -> None:
    """Hérité : test_importations::test_les_fournisseurs_marocains_n_ont_pas_de_dossier, et
    ::test_un_fournisseur_marocain_se_confirme — écartés de « En attente » (comptés), montrés à
    la demande ; ouvrir leur dossier se confirme. La seule définition : `est_local` (A-23)."""
    loc = Import.nouveau(code="MAD", pays="MAROC")
    loc.recevoir(achats, "LOC-1", [("PLASTIQUE", "PL", 500, 12)])
    numero = loc.f("LOC-1")
    a = _attente(achats)
    assert numero not in {f["numero"] for f in a["factures"]}
    assert a["locaux"]["factures"] >= 1 and a["locaux"]["lignes"] >= 1
    assert _facture(achats, numero, locaux=True)["local"] is True
    r = achats.post("/api/dossiers", json={"facture_id": facture_id(achats, numero)})
    assert r.status_code == 409 and "fournisseur marocain" in r.json()["detail"]
    assert r.json()["detail"].endswith("L'ouvrir quand même se confirme.")
    d = ouvrir(achats, numero, local_confirme=True)
    assert d["facture"]["numero"] == numero and d["local_confirme"]


def test_deux_devises_un_cours_chacune_et_cours_du_bon(achats: TestClient) -> None:
    """Hérité : test_importations::test_deux_devises_un_cours_chacune_et_cours_du_bon — une
    facture par devise, donc deux dossiers ; la ligne du bon entre au cours figé à la
    confirmation des prix (`cours_origine = bon`), l'autre sans cours ; un cours par devise ;
    « cours des bons » remet le cours figé."""
    a = Achat.nouveau(devise=Import.nouveau(cours="10").devise, pays="BELGIUM")
    pes = a.matiere("PES 20/2", prix="1.95")
    b = parti(achats, a, {pes: 1000}, prix=1.95)
    with cours(a.devise, "10.4"):
        quai = Quai.nouveau()
        e = Import.nouveau(cours="11")
        sbr = e.ligne("SBR", "S", 3000, 1.1)
        r_e = camion(achats, e.fournisseur_id, [sbr], factures={e.devise: {"numero": e.f("LOM-1")}})
        geste_reception(achats, r_e, "valider")
        lb = ligne_du_bon(b, pes, 1000, unique("P"), magasin_id=quai.courant, quantite_bl=1000)
        fu = unique("LOM-2")
        r_u = camion(achats, a.fournisseur_id, [lb], factures={a.devise: {"numero": fu}})
        geste_reception(achats, r_u, "valider")
        assert _facture(achats, e.f("LOM-1"))["valeurs"] == [{"devise": e.devise, "valeur": 3300}]
        assert _facture(achats, fu)["valeurs"] == [{"devise": a.devise, "valeur": 1950}]
        d_e, d_u = ouvrir(achats, e.f("LOM-1")), ouvrir(achats, fu)
        x_u, x_e = d_u["lignes"][0], d_e["lignes"][0]
        assert x_u["cours"] == 10 and x_u["cours_bon"] == 10 and x_u["cours_origine"] == "bon"
        assert x_u["cours_jour"] == pytest.approx(10.4) and d_u["lignes_cours_bon"] == 1
        assert x_e["cours"] is None and x_e["cours_bon"] is None and x_e["cours_applique"] == 11
        d_e = geste_put(achats, d_e, "cours", cours=10.95)
        assert d_e["lignes"][0]["cours"] == 10.95
        d_u = geste_put(achats, d_u, f"lignes/{x_u['id']}", cours=9.62)
        assert d_u["lignes"][0]["cours"] == 9.62 and d_u["lignes_cours_bon"] == 0
        d_u = geste(achats, d_u, "cours-des-bons")
        assert d_u["lignes"][0]["cours"] == 10 and d_u["lignes"][0]["cours_origine"] == "bon"
        refus = geste(achats, d_e, "cours-des-bons", 422)
        assert refus["detail"] == "Aucune ligne de ce dossier ne vient d'un bon au cours figé."


def geste_put(
    client: TestClient, d: dict[str, Any], chemin: str, code: int = 200, **corps: Any
) -> Any:
    """`PUT /dossiers/{id}/{chemin}` avec la version lue."""
    version = fiche(client, d["id"])["version"]
    r = client.put(f"/api/dossiers/{d['id']}/{chemin}", json={"version": version, **corps})
    assert r.status_code == code, r.text
    return r.json()


def test_un_second_camion_de_la_meme_facture_rejoint_son_dossier(achats: TestClient) -> None:
    """Hérité :
    test_importations::test_un_second_camion_de_la_meme_facture_rejoint_son_dossier
    — 300 kg puis 200 kg : un dossier, qui reçoit le second camion ; la facture dit le dossier
    qu'elle rejoint ; elle n'en ouvre pas un second. La fiche l'annonce (`a_rattacher`)."""
    imp = Import.nouveau()
    imp.recevoir(achats, "FAC-3", [("NOIR", "IN-3", 300, 4)])
    d = ouvrir(achats, imp.f("FAC-3"))
    second = imp.recevoir(achats, "FAC-3", [("NOIR", "IN-4", 200, 4)])
    f = _facture(achats, imp.f("FAC-3"))
    assert f["dossier_id"] == d["id"] and f["dossier"] == d["numero"] and f["lignes"] == 1
    assert [x["facture_id"] for x in fiche(achats, d["id"])["a_rattacher"]] == [f["facture_id"]]
    r = achats.post("/api/dossiers", json={"facture_id": f["facture_id"]})
    assert r.status_code == 409 and d["numero"] in r.json()["detail"]
    d = geste(achats, d, "rattacher", facture_id=f["facture_id"])
    assert d["nb_lignes"] == 2 and d["poids"] == pytest.approx(500) and d["a_rattacher"] == []
    assert second["numero"] in d["pieces"][0]["receptions"]
    assert imp.f("FAC-3") not in {x["numero"] for x in _attente(achats)["factures"]}


def test_une_reception_sans_facture_attend_sa_facture(achats: TestClient) -> None:
    """Hérité : test_importations::test_une_reception_sans_facture_attend_sa_facture — elle
    attend (valeur par devise) ; sa facture saisie, la facture ouvre son dossier."""
    imp = Import.nouveau()
    r = imp.recevoir(achats, None, [("JUTE", "IJ-9", 100, 1)])
    attente = next(x for x in _attente(achats)["sans_facture"] if x["reception_id"] == r["id"])
    assert attente["lignes"] == 1 and attente["valeurs"] == [{"devise": imp.devise, "valeur": 100}]
    facture_reception(achats, r, numero=imp.f("FAC-9"))
    d = ouvrir(achats, imp.f("FAC-9"))
    assert d["nb_lignes"] == 1 and d["facture"]["numero"] == imp.f("FAC-9")


def _repris(receptions: list[int]) -> int:
    """Un dossier repris de l'ERP Fil : sans facture, ses marchandises écrites telles quelles."""
    with sessions()() as s, s.begin():
        d = Dossier(numero=unique("ANC-D7"), libelle="repris", saisi_a_la_main=True)
        s.add(d)
        s.flush()
        for rid in receptions:
            r = s.get(Reception, rid)
            assert r is not None
            for x in s.query(ReceptionLigne).filter(ReceptionLigne.reception_id == rid):
                s.add(
                    DossierLigne(
                        dossier_id=d.id,
                        reception_ligne_id=x.id,
                        matiere_id=x.matiere_id,
                        lot_id=x.lot_id,
                        fournisseur_id=r.fournisseur_id,
                        quantite_kg=x.quantite_pesee,
                        valeur_devise=x.quantite_pesee * x.prix,
                        devise=r.devise,
                        cours=Decimal(10),
                        cours_origine=OrigineCours.reprise,
                    )
                )
        donnees_moteur.invalider()
        return d.id


@pytest.fixture
def reprise(achats: TestClient) -> dict[str, Any]:
    """Un dossier repris qui mêle deux factures (FA en deux camions, FB), et une facture FC
    que rien ne porte."""
    imp = Import.nouveau()
    ra1 = imp.recevoir(achats, "REP-FA", [("ROUGE", "RA-1", 100, 2)])
    ra2 = imp.recevoir(achats, "REP-FA", [("JUTE", "RA-2", 200, 1)])
    rb = imp.recevoir(achats, "REP-FB", [("ROUGE", "RB-1", 300, 2)])
    rc = imp.recevoir(achats, "REP-FC", [("JUTE", "RC-1", 50, 1)])
    did = _repris([ra1["id"], ra2["id"], rb["id"]])
    frais(achats, fiche(achats, did), "FRET", 1200)
    return {"imp": imp, "dossier": did, "ra1": ra1, "ra2": ra2, "rb": rb, "rc": rc}


def test_une_facture_d_un_dossier_repris_n_ouvre_pas_un_second_dossier(
    reprise: dict[str, Any], achats: TestClient
) -> None:
    """Hérité :
    test_importations::test_une_facture_d_un_dossier_repris_n_ouvre_pas_un_second_dossier,
    test_defauts_b::test_dossier_repris_n_est_pas_a_la_main (B-11),
    test_importations_second_audit::test_la_saisie_a_la_main_est_reservee_aux_dossiers_d_avant
    (dossier repris)."""
    imp: Import = reprise["imp"]
    d = fiche(achats, reprise["dossier"])
    assert d["repris"] and not d["a_la_main"]
    assert d["factures"] == sorted([imp.f("REP-FA"), imp.f("REP-FB")])
    assert d["actions"]["saisir"].startswith(f"Le dossier {d['numero']} porte des réceptions")
    corps = {"matiere_id": imp.matiere("ROUGE"), "lot_numero": unique("NEUF"), "quantite_kg": 1}
    refus = geste(achats, d, "lignes", 409, **corps, valeur_devise=1)
    assert refus["detail"] == d["actions"]["saisir"]
    x = next(y for y in d["lignes"] if y["reception"] == reprise["ra1"]["numero"])
    assert x["reception_id"] == reprise["ra1"]["id"]
    r = achats.delete(f"/api/dossiers/{d['id']}/lignes/{x['id']}", params={"version": d["version"]})
    assert r.status_code == 409 and "Détacher la réception" in r.json()["detail"]
    d = geste(achats, d, "detacher", reception_id=reprise["ra1"]["id"])
    assert d["nb_lignes"] == 2 and d["nb_frais"] == 1 and d["statut"] == "ouvert"
    fa = _facture(achats, imp.f("REP-FA"))
    assert fa["dossier_id"] == d["id"] and fa["dossier"] == d["numero"]
    r = achats.post("/api/dossiers", json={"facture_id": fa["facture_id"]})
    assert r.status_code == 409 and d["numero"] in r.json()["detail"]
    assert "(repris de l'ancien ERP)" in r.json()["detail"]
    fc = _facture(achats, imp.f("REP-FC"))
    refus = geste(achats, d, "rattacher", 409, facture_id=fc["facture_id"])
    assert "ne prend que la suite des factures qu'il porte déjà" in refus["detail"]
    d = geste(achats, d, "rattacher", facture_id=fa["facture_id"])
    assert d["nb_lignes"] == 3
    for rec in (reprise["ra1"], reprise["ra2"]):
        d = geste(achats, d, "detacher", reception_id=rec["id"])
    assert d["factures"] == [imp.f("REP-FB")] and d["nb_frais"] == 1
    nouveau = ouvrir(achats, imp.f("REP-FA"))
    assert nouveau["nb_lignes"] == 2 and nouveau["facture"]["numero"] == imp.f("REP-FA")
    refus = geste(achats, d, "detacher", 404, reception_id=reprise["rc"]["id"])
    assert (
        refus["detail"]
        == f"La réception {reprise['rc']['numero']} n'est pas dans le dossier {d['numero']}."
    )
    assert (
        geste(achats, d, "detacher", 404, reception_id=999_999)["detail"] == "Réception inconnue."
    )


def test_annuler_une_reception_d_un_dossier_passe_par_detacher(achats: TestClient) -> None:
    """Hérité : test_importations::test_annuler_une_reception_d_un_dossier_passe_par_detacher —
    le refus donne le chemin ; détachée, le dossier vide garde ses frais (non répartis, rien
    d'attendu) ; la réception s'annule ensuite ; le dossier ne se supprime pas, il s'annule et
    garde son numéro (B-02)."""
    imp = Import.nouveau()
    rc = imp.recevoir(achats, "REP-FC", [("JUTE", "RC-1", 50, 1)])
    d = ouvrir(achats, imp.f("REP-FC"))
    d = frais(achats, d, "DD", 90)
    refus = geste_reception(achats, rc, "annuler", 409, motif="saisie en double")
    assert "Détacher la réception" in refus["detail"] and d["numero"] in refus["detail"]
    refus = facture_reception(achats, rc, 409, numero=unique("REP-FC-BIS"))
    assert "Détacher la réception" in refus["detail"]
    d = geste(achats, d, "detacher", reception_id=rc["id"])
    assert d["nb_lignes"] == 0 and d["charges_non_reparties_mad"] == pytest.approx(90)
    assert d["tva_attendue_mad"] is None and d["droits_attendus_mad"] is None
    assert d["actions"]["cloturer"] == "Un dossier sans marchandise n'a rien à clore."
    geste_reception(achats, rc, "annuler", motif="saisie en double")
    assert achats.delete(f"/api/dossiers/{d['id']}").status_code == 405
    d = geste(achats, d, "annuler", motif="réception annulée")
    assert d["statut"] == "annule" and d["numero"] and d["annulation_motif"] == "réception annulée"


def test_la_cloture_dit_le_cours_du_bon_et_trace_le_cours_fige(achats: TestClient) -> None:
    """Hérité : test_importations::test_la_cloture_dit_le_cours_du_bon_et_trace_le_cours_fige,
    et test_defauts_b::test_rouvrir_signale_cours_figes (B-08) — la clôture fige le cours du jour
    (`clos_au_jour`, au journal) ; rouvert, il redevient vide ; un second camion arrivé après
    un changement de cours fait deux cours pour une devise (dit au journal)."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "COURS-1", [("NOIR", "C-1", 10, 4)])
    d = ouvrir(achats, imp.f("COURS-1"))
    x = d["lignes"][0]
    d = geste_put(achats, d, f"lignes/{x['id']}", commentaire="palette")
    d = geste(achats, d, "cloturer", alertes_lues=True)
    fige = d["lignes"][0]
    assert fige["cours"] == 10 and fige["cours_origine"] == "clos_au_jour"
    assert fige["commentaire"] == "palette"
    d = geste(achats, d, "rouvrir")
    assert d["lignes"][0]["cours"] is None and d["lignes"][0]["cours_origine"] is None
    assert d["alertes"][0].startswith("Les cours vides")
    d = geste_put(achats, d, f"lignes/{x['id']}", cours=10)
    with cours(imp.devise, "10.5"):
        imp.recevoir(achats, "COURS-1", [("NOIR", "C-2", 10, 4)])
        d = geste(achats, d, "rattacher", facture_id=d["facture"]["id"])
        assert d["cours_disparates"] == [{"devise": imp.devise, "cours": [10, 10.5]}]
        assert f"plusieurs cours en {imp.devise}" in d["a_verifier"]
    assert j()
