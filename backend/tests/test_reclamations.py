"""Les réclamations aux fournisseurs (lot D4) : ce que le fournisseur a livré, bornées par le
reçu, la date et la validation, sur la ligne en cause (A-10), suivies jusqu'à leur issue qui ne
change plus sans réouverture (A-22). Preuves héritées de `test_suivi`, `test_audit2_achats`,
`test_commandes_receptions` (domaine 5). Les réclamations sont datées en 2025 (`JOUR`).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.receptions import (
    Quai,
    camion,
    j,
    menage,  # noqa: F401 — fixture du module
    ok,
    recevoir,
)
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("menage")


@pytest.fixture
def mad() -> Achat:
    """Une filature marocaine en dirhams."""
    return Achat.nouveau(devise="MAD", delai=30, pays="MAROC")


@pytest.fixture
def quai() -> Quai:
    """Un magasin de rangement à soi."""
    return Quai.nouveau()


def ouvrir(client: TestClient, code: int = 201, **corps: object) -> dict:
    """`POST /reclamations` (ouverte le `JOUR` par défaut)."""
    r = client.post("/api/reclamations", json={"ouverte_le": j(), **corps})
    assert r.status_code == code, r.text
    return r.json()  # type: ignore[no-any-return]


def action(client: TestClient, x: dict, nom: str, code: int = 200, **corps: object) -> dict:
    """Un geste sur la réclamation avec sa version lue."""
    version = ok(client.get(f"/api/reclamations/{x['id']}"))["version"]
    r = client.post(f"/api/reclamations/{x['id']}/{nom}", json={"version": version, **corps})
    assert r.status_code == code, r.text
    return r.json()  # type: ignore[no-any-return]


def completer(client: TestClient, x: dict, code: int = 200, **corps: object) -> dict:
    """`PUT /reclamations/{id}` avec la version lue."""
    version = ok(client.get(f"/api/reclamations/{x['id']}"))["version"]
    r = client.put(f"/api/reclamations/{x['id']}", json={"version": version, **corps})
    assert r.status_code == code, r.text
    return r.json()  # type: ignore[no-any-return]


def test_une_reclamation_se_suit_jusqu_a_sa_cloture(
    achats: TestClient, alimentation: TestClient, mad: Achat
) -> None:
    """Hérité : test_suivi::test_une_reclamation_se_suit_jusqu_a_sa_cloture — numéro RCL- à
    l'ouverture ; clore sans issue : 422 ; avoir de 250 : close ; l'alimentation : 403."""
    constat = "Bobines à 2,9 kg au lieu de 3,15"
    x = ouvrir(achats, fournisseur_id=mad.fournisseur_id, motif="Poids des bobines", quantite=120,
               montant_demande=300, devise="USD", description=constat)  # fmt: skip
    assert x["numero"].startswith("RCL-2025-") and x["statut"] == "ouverte"
    assert x["motif"] == "poids_bobines" and x["motif_libelle"] == "Poids des bobines"
    refus = action(achats, x, "clore", 422, reponse="ok")
    assert refus["detail"].startswith("Pour clore, dire comment elle s'est terminée")
    x = action(achats, x, "clore", reponse="Avoir accordé", issue="Avoir", montant_obtenu=250)
    assert x["statut"] == "close" and x["montant_obtenu"] == 250 and x["issue"] == "avoir"
    assert x["close_le"] == "2026-10-08" and x["jours"] == 281
    assert alimentation.get("/api/reclamations").status_code == 403


def test_une_reclamation_reste_dans_le_reel(achats: TestClient, mad: Achat, quai: Quai) -> None:
    """Hérité : test_audit2_achats::test_une_reclamation_reste_dans_le_reel — 5 000 kg sur 100
    reçus : 422 ; dans le futur : 422 ; sur un brouillon : refusée ; close, elle garde son
    issue."""
    m = mad.matiere("RCL")
    ligne = {
        "matiere_id": m,
        "lot_numero": "RCL-1",
        "quantite_pesee": 100,
        "magasin_id": quai.courant,
    }
    r = recevoir(achats, mad.fournisseur_id, [ligne])
    base = {"fournisseur_id": mad.fournisseur_id, "motif": "Autre", "description": "essai"}
    refus = ouvrir(achats, 422, **base, reception_id=r["id"], quantite=5000)
    assert (
        refus["detail"]
        == f"5 000,0 kg réclamés pour 100,0 kg livrés par la réception {r['numero']}."
    )
    refus = ouvrir(achats, 422, **base, reception_id=r["id"], ouverte_le="2026-10-09")
    assert refus["detail"] == "Une réclamation ne s'ouvre pas dans le futur."
    refus = ouvrir(achats, 422, **base, reception_id=r["id"], ouverte_le=j(-1))
    assert (
        refus["detail"] == "Une réclamation ne précède pas la réception qu'elle vise (31/12/2025)."
    )
    b = camion(achats, mad.fournisseur_id, [ligne | {"lot_numero": "RCL-2", "quantite_pesee": 10}])
    refus = ouvrir(achats, 409, **base, reception_id=b["id"])
    assert refus["detail"].endswith("cette réception n'est pas encore validée.")
    x = ouvrir(achats, **base, reception_id=r["id"], quantite=50)
    x = action(achats, x, "clore", issue="Avoir")
    refus = action(achats, x, "clore", 409, issue="Refusée")
    assert refus["detail"] == (
        "Cette réclamation est close avec l'issue « Avoir » : elle la garde. La rouvrir pour "
        "changer d'issue."
    )


def test_une_reclamation_vise_ce_que_le_fournisseur_a_livre(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """Hérité : test_commandes_receptions::test_une_reclamation_vise_ce_que_le_fournisseur_a_livre
    — un autre fournisseur : refusé (le bon est cité) ; un lot qu'il n'a pas livré : refusé ;
    devise inconnue : refusée ; compléter une close la laisse close ; rouvrir la rouvre."""
    autre = Achat.nouveau(devise="MAD")
    m = mad.matiere("VISE")
    ligne = {"matiere_id": m, "lot_numero": "V-1", "quantite_pesee": 20, "magasin_id": quai.courant}
    r = recevoir(achats, mad.fournisseur_id, [ligne])
    lot = r["lignes"][0]["lot_id"]
    base = {"motif": "Autre", "description": "essai"}
    refus = ouvrir(achats, 422, **base, fournisseur_id=autre.fournisseur_id, reception_id=r["id"])
    assert r["fournisseur"] in refus["detail"]
    refus = ouvrir(achats, 422, **base, fournisseur_id=autre.fournisseur_id, lot_id=lot)
    assert "n'a pas été livré par" in refus["detail"]
    refus = ouvrir(achats, 422, **base, fournisseur_id=mad.fournisseur_id, devise="XYZ")
    assert refus["detail"] == "Devise inconnue : XYZ."
    x = ouvrir(achats, **base, fournisseur_id=mad.fournisseur_id, reception_id=r["id"], lot_id=lot)
    assert x["lot"] == "V-1" and x["reference"] == r["lignes"][0]["reference"]
    x = action(achats, x, "clore", issue="avoir")
    x = completer(achats, x, reponse="avoir reçu", montant_obtenu=12)
    assert x["statut"] == "close" and x["reponse"] == "avoir reçu" and x["montant_obtenu"] == 12
    assert action(achats, x, "rouvrir", 422, motif="")["code"] == "saisie_invalide"
    x = action(achats, x, "rouvrir", motif="l'avoir n'est jamais arrivé")
    assert x["statut"] == "ouverte" and x["close_le"] is None and x["issue"] is None
    assert action(achats, x, "rouvrir", 409, motif="encore")["detail"] == (
        "Cette réclamation est déjà ouverte."
    )


def test_une_reclamation_sur_une_ligne_refusee_garde_sa_reference(
    achats: TestClient, mad: Achat, quai: Quai
) -> None:
    """A-10 (Gestion MP corrigé, test_defauts_a) : la ligne refusée n'a pas de lot, la
    réclamation garde sa ligne et sa référence ; sa pesée la borne ; sans ligne, une ligne
    refusée n'a rien livré ; le motif est dans la liste."""
    m1, m2 = mad.matiere("RECLAME"), mad.matiere("RECLAME 2")
    r = recevoir(achats, mad.fournisseur_id, [
        {"matiere_id": m1, "lot_numero": "RC-1", "quantite_pesee": 40, "magasin_id": quai.courant},
        {"matiere_id": m2, "lot_numero": "RC-2", "quantite_pesee": 60, "qualite": "refuse"},
    ])  # fmt: skip
    refusee = next(x for x in r["lignes"] if x["qualite"] == "refuse")
    base = {"fournisseur_id": mad.fournisseur_id, "motif": "Qualité (défaut du fil)"}
    trop = ouvrir(
        achats, 422, **base, reception_id=r["id"], reception_ligne_id=refusee["id"], quantite=61
    )
    assert "60,0 kg livrés" in trop["detail"]
    x = ouvrir(achats, **base, reception_id=r["id"], reception_ligne_id=refusee["id"], quantite=60)
    assert x["reference"] == refusee["reference"] and x["reception_ligne_id"] == refusee["id"]
    assert x["lot_id"] is None and x["pese"] == 60
    refus = ouvrir(achats, 422, **base, reception_id=r["id"], quantite=1200.5)
    assert "1 200,5 kg réclamés pour 40,0 kg" in refus["detail"]
    refus = ouvrir(achats, 422, **base | {"motif": "N'importe quoi"})
    assert refus["detail"].startswith("Motif : Qualité (défaut du fil), Quantité manquante")
    autre = recevoir(achats, mad.fournisseur_id, [
        {"matiere_id": m1, "lot_numero": "RC-3", "quantite_pesee": 5, "magasin_id": quai.courant}
    ])  # fmt: skip
    refus = ouvrir(achats, 422, **base, reception_id=autre["id"], reception_ligne_id=refusee["id"])
    assert refus["detail"] == "Cette ligne n'est pas dans la réception choisie."
    fiche = ok(achats.get(f"/api/receptions/{r['id']}"))
    assert [y["reference"] for y in fiche["reclamations"]] == [refusee["reference"]]
    assert fiche["reclamations"][0]["lot"] == ""
    liste = ok(achats.get("/api/reclamations", params={"reception": r["id"], "statut": "ouverte"}))
    assert [y["id"] for y in liste] == [x["id"]]


def test_une_reclamation_perimee_est_refusee(achats: TestClient, mad: Achat) -> None:
    """Version périmée → 409 sur chaque écriture d'une réclamation."""
    x = ouvrir(achats, fournisseur_id=mad.fournisseur_id, motif="retard")
    perime = {"version": x["version"]}
    completer(achats, x, reponse="relancé")
    for chemin, corps in (("", {"reponse": "x"}), ("/clore", {"issue": "avoir"}),
                          ("/rouvrir", {"motif": "test"})):  # fmt: skip
        methode = achats.put if not chemin else achats.post
        r = methode(f"/api/reclamations/{x['id']}{chemin}", json=perime | corps)
        assert r.status_code == 409 and r.json()["code"] == "conflit_version", chemin
