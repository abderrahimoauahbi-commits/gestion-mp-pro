"""C35 et C36 par l'API, sur de vrais dossiers d'importation (lots D7 et D4 ; restes de D7).

Base partagée : les dossiers sont ouverts par les services de D7 depuis la facture d'une vraie
réception, et chaque contrôle est lu par son détail cherché sur le numéro du dossier.
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques import importations as imp
from fabriques.receptions import facture as corriger_facture
from fastapi.testclient import TestClient


def detail(client: TestClient, code: str, numero: str) -> list[dict[str, Any]]:
    """Les lignes d'un contrôle qui nomment ce dossier."""
    imp.invalider()
    r = client.get(f"/api/controles/{code}", params={"q": numero})
    assert r.status_code == 200, r.text
    return [x for x in r.json()["elements"] if x["dossier"] == numero]


def test_des_frais_aberrants_se_signalent(achats: TestClient) -> None:
    """Hérité : test_importations::test_des_frais_aberrants_se_signalent (C35 par l'API, laissé
    par D7) — 3 000 000 MAD de transit sur 2 000 MAD de marchandise : C35 le dit (rapport en
    fraction, id du dossier) ; le frais retiré, il se tait."""
    i = imp.Import.nouveau(code="USD")
    i.recevoir(achats, "C35-D8", [("FIL", "C35-1", 100, 2.0)], montant=200)
    d = imp.ouvrir(achats, i.f("C35-D8"), local_confirme=True)
    assert detail(achats, "C35", d["numero"]) == []
    d = imp.frais(achats, d, "TRANSIT", 3_000_000)
    lignes = detail(achats, "C35", d["numero"])
    assert lignes and lignes[0]["dossier_id"] == d["id"]
    assert any((x["surcout"] or 0) > 50 for x in lignes)
    frais = next(x for x in d["frais"] if x["montant"] == 3_000_000)
    r = achats.delete(f"/api/dossiers/{d['id']}/frais/{frais['id']}",
                      params={"version": frais["version"]})  # fmt: skip
    assert r.status_code == 200, r.text
    assert detail(achats, "C35", d["numero"]) == []


def test_la_facture_se_rapproche_de_la_marchandise_recue(achats: TestClient) -> None:
    """Hérité : test_importations_second_audit::test_la_facture_se_rapproche_de_la_marchandise_recue
    (C36 par l'API, laissé par D7) — 4 598 facturés pour 5 083,82 reçus : C36 le dit (écart en
    fraction) ; facture corrigée à 5 100, dans la tolérance de 2 % : il se tait."""
    i = imp.Import.nouveau(code="USD")
    r = i.recevoir(achats, "C36-D8", [("FIL", "C36-1", 2541.91, 2.0)], montant=4598)
    d = imp.ouvrir(achats, i.f("C36-D8"), local_confirme=True)
    lignes = detail(achats, "C36", d["numero"])
    assert len(lignes) == 1 and lignes[0]["dossier_id"] == d["id"]
    assert lignes[0]["ecart"] == pytest.approx((4598 - 5083.82) / 5083.82, abs=1e-4)
    corriger_facture(achats, r, montant=5100)
    assert detail(achats, "C36", d["numero"]) == []
