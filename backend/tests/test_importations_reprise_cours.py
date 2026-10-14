"""Audit n° 2 (14/10/2026) — une marchandise qui revient au dossier n'y revient plus en silence.

Retirer une facture (ou détacher sa réception, ou annuler le dossier) emporte le cours payé de
sa marchandise ; la ré-ajouter la fait rentrer **au cours figé de son bon** (sans bon : sans
cours, au cours du jour), comme à l'ouverture. La réponse (`avis`), le journal et l'écran le
disent, et le dernier cours payé, retrouvé dans le journal (`avant.cours_payes`), est proposé.
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat
from fabriques.importations import Import, facture_id, fiche, geste, ouvrir
from fabriques.receptions import Quai, camion, ligne_du_bon, ok, parti
from fabriques.receptions import geste as geste_reception
from fabriques.referentiels import unique
from fastapi.testclient import TestClient

ONGLET = "le cours payé à la banque se ressaisit dans l'onglet Marchandises"


def _historique(achats: TestClient, d: dict[str, Any], action: str) -> list[dict[str, Any]]:
    """Les lignes du journal du dossier pour cette action, la plus récente d'abord."""
    lignes = ok(achats.get(f"/api/historique/dossier/{d['id']}"))
    return [x for x in lignes if x["action"] == action]


def _cours_paye(achats: TestClient, d: dict[str, Any], cours: float) -> dict[str, Any]:
    """Le cours payé à la banque, posé sur la première marchandise du dossier."""
    x = d["lignes"][0]
    return ok(  # type: ignore[no-any-return]
        achats.put(
            f"/api/dossiers/{d['id']}/lignes/{x['id']}",
            json={"version": d["version"], "cours": cours},
        )
    )


def _retirer(achats: TestClient, d: dict[str, Any]) -> dict[str, Any]:
    """La première facture du dossier retirée (route 254)."""
    fid = d["factures"][0]["id"]
    r = achats.delete(f"/api/dossiers/{d['id']}/factures/{fid}", params={"version": d["version"]})
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def _ajouter(achats: TestClient, d: dict[str, Any], numero: str) -> dict[str, Any]:
    """La facture `numero`, en attente, ajoutée au dossier (route 253)."""
    return geste(achats, d, "factures", facture_id=facture_id(achats, numero))  # type: ignore[no-any-return]


@pytest.fixture
def du_bon(achats: TestClient) -> dict[str, Any]:
    """Une facture d'une ligne livrée sur un bon dont le prix a été confirmé au cours de 10 :
    son dossier, ouvert, où la marchandise entre au cours du bon."""
    a = Achat.nouveau(devise=Import.nouveau(cours="10").devise, pays="BELGIUM")
    pes = a.matiere("PES 20/2", prix="1.95")
    b = parti(achats, a, {pes: 1000}, prix=1.95)
    quai = Quai.nouveau()
    lb = ligne_du_bon(b, pes, 1000, unique("P"), magasin_id=quai.courant, quantite_bl=1000)
    numero = unique("REP")
    r = camion(achats, a.fournisseur_id, [lb], factures={a.devise: {"numero": numero}})
    geste_reception(achats, r, "valider")
    d = ouvrir(achats, numero)
    assert d["lignes"][0]["cours"] == 10 and d["lignes"][0]["cours_origine"] == "bon"
    return {"d": d, "numero": numero, "bon": b["numero"], "devise": a.devise, "reception": r}


def test_la_premiere_entree_dit_le_cours_du_bon(achats: TestClient, du_bon: dict[str, Any]) -> None:
    """À l'ouverture, la réponse dit que la marchandise entre au cours du bon (celui des
    réglages à la confirmation des prix) et où saisir le cours payé ; ce n'est pas une
    reprise ; une lecture de la fiche n'a pas d'avis."""
    d, bon, devise = du_bon["d"], du_bon["bon"], du_bon["devise"]
    (avis,) = d["avis"]
    assert avis.startswith(f"Facture {du_bon['numero']} : 1 marchandise au cours du bon {bon} ")
    assert f"(10 MAD pour 1 {devise})" in avis and ONGLET in avis
    assert "reprise" not in avis
    assert fiche(achats, d["id"])["avis"] == []


def test_retirer_puis_rajouter_une_facture_n_est_plus_silencieux(
    achats: TestClient, du_bon: dict[str, Any]
) -> None:
    """Cours payé 10,05 saisi, facture retirée, puis ré-ajoutée : la marchandise revient au cours
    du bon (10), la réponse dit la reprise et propose 10,05, le journal garde le cours payé au
    retrait et marque la reprise à l'ajout."""
    d, numero = _cours_paye(achats, du_bon["d"], 10.05), du_bon["numero"]
    assert d["lignes"][0]["cours"] == 10.05 and d["lignes"][0]["cours_origine"] == "banque"
    ligne_recue = d["lignes"][0]["reception_ligne_id"]
    d = _retirer(achats, d)
    assert d["lignes"] == [] and d["factures"] == []
    (retrait,) = _historique(achats, d, "facture retirée")
    assert retrait["avant"]["cours_payes"] == {str(ligne_recue): 10.05}
    d = _ajouter(achats, d, numero)
    x = d["lignes"][0]
    assert (
        x["cours"] == 10 and x["cours_origine"] == "bon" and x["reception_ligne_id"] == ligne_recue
    )
    (avis,) = d["avis"]
    assert avis.startswith(
        f"Facture {numero} : reprise de 1 marchandise au cours du bon {du_bon['bon']} "
    )
    assert ONGLET in avis
    assert avis.endswith(f"Dernier cours payé saisi : {du_bon['devise']} à 10,05.")
    (ajout,) = _historique(achats, d, "facture ajoutée")
    assert ajout["detail"].endswith(" · reprise : le cours payé d'avant la sortie ne revient pas")
    assert fiche(achats, d["id"])["avis"] == []


def test_detacher_puis_rattacher_la_reception(achats: TestClient, du_bon: dict[str, Any]) -> None:
    """Détacher la réception (la facture sort avec elle) après un cours payé de 9,9, puis la
    ré-ajouter : même reprise, même proposition du dernier cours payé."""
    d, numero = _cours_paye(achats, du_bon["d"], 9.9), du_bon["numero"]
    d = geste(achats, d, "detacher", reception_id=du_bon["reception"]["id"])
    assert d["lignes"] == [] and d["factures"] == []
    (detache,) = _historique(achats, d, "réception détachée")
    assert list(detache["avant"]["cours_payes"].values()) == [9.9]
    d = _ajouter(achats, d, numero)
    (avis,) = d["avis"]
    assert " : reprise de 1 marchandise au cours du bon " in avis
    assert avis.endswith(f"Dernier cours payé saisi : {du_bon['devise']} à 9,9.")
    assert d["lignes"][0]["cours"] == 10 and d["lignes"][0]["cours_origine"] == "bon"


def test_annuler_le_dossier_puis_rouvrir_la_facture(
    achats: TestClient, du_bon: dict[str, Any]
) -> None:
    """Un dossier annulé libère sa facture : le dossier neuf ouvert depuis elle dit la reprise au
    cours du bon et propose le cours payé saisi avant l'annulation."""
    d = _cours_paye(achats, du_bon["d"], 10.2)
    d = geste(achats, d, "annuler", motif="mauvaise facture")
    (annulation,) = _historique(achats, d, "annulation dossier")
    assert list(annulation["avant"]["cours_payes"].values()) == [10.2]
    neuf = ouvrir(achats, du_bon["numero"])
    assert neuf["id"] != d["id"] and neuf["lignes"][0]["cours"] == 10
    (avis,) = neuf["avis"]
    assert " : reprise de 1 marchandise au cours du bon " in avis
    assert avis.endswith(f"Dernier cours payé saisi : {du_bon['devise']} à 10,2.")


def test_sans_bon_la_marchandise_revient_sans_cours(achats: TestClient) -> None:
    """Une marchandise hors commande n'a pas de cours du bon : elle revient sans cours (au
    cours du jour) ; la réponse le dit et propose le cours payé d'avant le retrait. Une ligne
    restée au cours du bon (ou sans cours) n'est pas un cours payé : rien n'est gardé."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "SB", [("ROUGE", "SB-R", 1000, 2.0), ("NOIR", "SB-N", 500, 4.0)])
    d = ouvrir(achats, imp.f("SB"))
    assert all(x["cours"] is None for x in d["lignes"])
    (avis,) = d["avis"]
    assert avis.startswith(f"Facture {imp.f('SB')} : 2 marchandises sans cours payé (comptée")
    d = _retirer(achats, d)
    (retrait,) = _historique(achats, d, "facture retirée")
    assert "cours_payes" not in retrait["avant"]
    d = _ajouter(achats, d, imp.f("SB"))
    assert "reprise" not in d["avis"][0]
    d = _cours_paye(achats, d, 10.5)
    d = _retirer(achats, d)
    d = _ajouter(achats, d, imp.f("SB"))
    (avis,) = d["avis"]
    assert avis.startswith(f"Facture {imp.f('SB')} : reprise de 2 marchandises sans cours payé")
    assert avis.endswith(f"Dernier cours payé saisi : {imp.devise} à 10,5.")
    assert all(x["cours"] is None for x in d["lignes"])
