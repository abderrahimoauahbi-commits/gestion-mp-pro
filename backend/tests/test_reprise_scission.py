"""Reprise (lot K8B) : une réception de Gestion MP payée en deux devises devient une réception
par devise (R1 n° 2, D4), sans rien changer aux stocks, aux quantités ni aux valeurs.

La petite usine en a deux : REC-2026-0001 (facture en USD, une ligne en EUR, son mouvement
désigné par `document_id`) et REC-2026-0004 (sans facture, deux lignes en USD, une en EUR
retrouvée par (lot, date), avec une réclamation sur la ligne en EUR).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_reprise import SOURCE, lire, un
from test_reprise_traductions import reprise  # noqa: F401

from gestion_mp_pro.reprise.execution import Resultat
from gestion_mp_pro.reprise.scission import numero_scinde


def source(sql: str) -> list[Any]:
    """Les lignes d'une requête sur la source (Gestion MP)."""
    moteur = create_engine(SOURCE, poolclass=NullPool)
    with moteur.connect() as c:
        lignes = [tuple(r) for r in c.execute(text(sql))]
    moteur.dispose()
    return lignes


def test_une_reception_par_devise(reprise: tuple[Resultat, Path]) -> None:  # noqa: F811
    r = {
        x[0]: x[1:]
        for x in lire(
            "SELECT id, numero, devise, facture_id, statut, date::text, fournisseur_id, numero_bl"
            " FROM reception WHERE id IN (1, 4, 5, 6)"
        )
    }
    assert r[1][:3] == ("REC-2026-0001", "USD", 1)
    assert r[5][:3] == ("REC-2026-0001-2", "EUR", None)
    assert r[5][3:] == r[1][3:]
    assert r[4][:3] == ("REC-2026-0004", "USD", None)  # sans facture : la plupart des lignes
    assert r[6][:3] == ("REC-2026-0004-2", "EUR", None)
    lignes = dict(lire("SELECT id, reception_id FROM reception_ligne ORDER BY id"))
    assert lignes == {1: 1, 2: 5, 3: 2, 4: 4, 5: 4, 6: 6}


def test_les_mouvements_et_reclamations_suivent(reprise: tuple[Resultat, Path]) -> None:  # noqa: F811
    m = dict(lire("SELECT id, reception_id FROM mouvement WHERE document = 'reception'"))
    assert m == {2: 1, 3: 5, 12: 4, 13: 4, 14: 6}
    c = lire("SELECT id, reception_id, reception_ligne_id FROM reclamation ORDER BY id")
    assert c == [(1, 1, 1), (2, 6, 6)]


def test_prix_dans_leur_vraie_devise(reprise: tuple[Resultat, Path]) -> None:  # noqa: F811
    vraies = dict(source("SELECT id, devise FROM reception_ligne"))
    lues = dict(
        lire(
            "SELECT l.id, r.devise FROM reception_ligne l JOIN reception r ON r.id = l.reception_id"
        )
    )
    assert lues == vraies


def test_stocks_quantites_et_valeurs_inchanges(reprise: tuple[Resultat, Path]) -> None:  # noqa: F811
    entrees = (
        "SELECT id, quantite, prix, devise FROM mouvement WHERE type = 'RECEPTION' ORDER BY id"
    )
    gmp = [(i, round(Decimal(repr(q)), 3), Decimal(repr(p)), d) for i, q, p, d in source(entrees)]
    pro = [(i, q, p.normalize(), d) for i, q, p, d in lire(entrees)]
    assert pro == [(i, q, p.normalize(), d) for i, q, p, d in gmp]
    pese = "SELECT id, quantite_pesee, prix, lot_id FROM reception_ligne ORDER BY id"
    assert [(i, float(q), float(p), lot) for i, q, p, lot in lire(pese)] == source(pese)
    assert un("SELECT count(*) FROM lot") == 6


def test_rapport_compteur_et_correspondances(reprise: tuple[Resultat, Path]) -> None:  # noqa: F811
    rapport = reprise[0].rapport
    assert "NON TENU" not in rapport
    assert "scindée — REC-2026-0001 (USD, sa facture) et REC-2026-0001-2 (id 5, EUR" in rapport
    assert "scindée — REC-2026-0004 (USD, sans facture) et REC-2026-0004-2 (id 6, EUR" in rapport
    assert "(dont 2 nées d'une scission, signalées)" in rapport
    assert reprise[0].comptes["tables"]["reception"]["scindees"] == 2
    assert un("SELECT dernier FROM compteur WHERE serie = 'REC' AND annee = 2026") == 4
    notes = lire(
        "SELECT id_source, id_cible FROM reprise_correspondance"
        " WHERE table_source = 'reception:scindee' ORDER BY 1"
    )
    assert notes == [(5, 5), (6, 6)]
    assert un("SELECT count(*) FROM reprise_correspondance WHERE table_source = 'reception'") == 4


def test_numero_trop_long_refuse() -> None:
    assert numero_scinde(None, 2) is None
    assert numero_scinde("REC-2026-0042", 2) == "REC-2026-0042-2"
    with pytest.raises(ValueError, match="trop long"):
        numero_scinde("X" * 31, 2)
