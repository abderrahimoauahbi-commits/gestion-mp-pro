"""Les lots et la traçabilité (`calcul.lots`) : les lots disponibles hors quarantaine, du plus
ancien au plus récent ; le stock lot par lot retombe sur le journal ; le chemin d'un lot.
"""

from __future__ import annotations

import pytest

from gestion_mp_pro.calcul.lots import lots_disponibles, stock_par_lot, tracabilite
from gestion_mp_pro.calcul.modele import Donnees, Mouvement
from moteur.fabrique import J1, J2, J3, ecriture, journal


def test_les_lots_disponibles_ne_proposent_pas_la_quarantaine() -> None:
    """Hérité : test_valorisation::test_les_lots_disponibles_ne_proposent_pas_la_quarantaine."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10, lot="A"),
        Mouvement(
            date=J1,
            type="STOCK_INITIAL",
            reference="P50",
            quantite=50,
            lot_fournisseur="Q",
            magasin_destination="QUA",
            id=2,
        ),
        Mouvement(
            date=J2,
            type="TRANSFERT_MAGASIN",
            reference="P50",
            quantite=30,
            lot_fournisseur="A",
            magasin_source="MAG",
            magasin_destination="QUA",
            id=3,
        ),
    )
    proposes = lots_disponibles(d, "P50")
    assert [(x.lot, x.stock) for x in proposes] == [("A", 70)]
    assert proposes[0].par_magasin == {"MAG": 70}


def _journal_de_lots() -> Donnees:
    return journal(
        ecriture(1, J2, "STOCK_INITIAL", 100, prix=10, lot="B"),
        ecriture(2, J1, "ENTREE_RECEPTION", 200, prix=10, lot="A"),
        ecriture(3, J2, "SORTIE_PROD", 50, lot="A", of="OF-1"),
        ecriture(4, J3, "RETOUR_PRODUCTION", 10, lot="A", of="OF-1"),
        ecriture(5, J3, "SORTIE_PROD", 30, lot="B", of="OF-2"),
        ecriture(6, J3, "SORTIE_PROD", 20, lot="A", of="OF-2"),
        ecriture(7, J3, "SORTIE_PROD", -20, lot="A", of="OF-2", annule=6),
        ecriture(8, J3, "AJUSTEMENT_INVENTAIRE", 5, lot=""),
    )


def test_le_stock_lot_par_lot_retombe_sur_le_journal() -> None:
    """Nouveau (CALCULS B § 6) : entré, sorti (net des retours des machines), une écriture
    annulée et son annulation ne comptent pas ; un mouvement sans lot va sous « (sans lot) » ;
    les lots disponibles se proposent du plus ancien au plus récent."""
    d = _journal_de_lots()
    lots = {x.lot: x for x in stock_par_lot(d, "P50")}
    assert list(lots) == ["(sans lot)", "A", "B"]
    a = lots["A"]
    assert (a.entrees, a.sorties, a.stock) == (200, 40, 160)
    assert a.ordres == ["OF-1", "OF-2"] and a.mouvements == 5
    assert (a.premiere_entree, a.dernier_mouvement) == (J1, J3)
    assert a.par_magasin == {"MAG": pytest.approx(160)} and not a.epuise
    assert lots["B"].stock == 70 and lots["(sans lot)"].stock == 5
    assert sum(x.stock for x in lots.values()) == pytest.approx(235)
    assert [x.lot for x in lots_disponibles(d, "P50")] == ["A", "B"]
    assert stock_par_lot(d, "AUTRE") == []


def test_la_tracabilite_d_un_lot_et_d_un_ordre() -> None:
    """Nouveau (CALCULS B § 6) : d'où vient un lot et où il est parti ; ce qu'un ordre a
    consommé, tous lots."""
    d = _journal_de_lots()
    lot = tracabilite(d, lot="A")
    assert [m.id for m in lot.mouvements] == [2, 3, 4, 6, 7]
    assert lot.ordres == ["OF-1", "OF-2"] and lot.references == ["P50"]
    assert lot.entrees == pytest.approx(200 + 10 + 20) and lot.sorties == pytest.approx(50 + 20)
    ordre = tracabilite(d, ordre="OF-2")
    assert ordre.lots == ["A", "B"] and ordre.sorties == pytest.approx(50)
    assert [m.id for m in tracabilite(d, lot="(sans lot)").mouvements] == [8]
