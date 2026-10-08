"""Inventaire : écarts valorisés, recomptage, inventaire tournant (`calcul/inventaire.py`).

Les cas hérités reprennent les valeurs des essais de Gestion MP (partie calcul : la route lit
la base, ici les lignes sont écrites à la main).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gestion_mp_pro.calcul.inventaire import (
    CoutsInventaire,
    LigneInventaire,
    StockAuMagasin,
    a_compter,
    a_recompter,
    couts_inventaire,
    ecart_hors_tolerance,
    ecarts_inventaire,
    hors_tolerance,
    retenu,
)
from gestion_mp_pro.calcul.modele import Article, Donnees, Mouvement

AUJOURDHUI = date(2026, 10, 8)
TOLERANCE = 0.02


def _ouverture() -> Donnees:
    """Deux fils ouverts à 500 kg : l'un à 10 MAD, l'autre à 90 MAD."""
    return Donnees(
        articles=[
            Article(reference="VALO INVENTAIRE", prix_unite=10),
            Article(reference="VALO INVENTAIRE CHER", prix_unite=90),
        ],
        mouvements=[
            Mouvement(AUJOURDHUI, "STOCK_INITIAL", "VALO INVENTAIRE", 500, prix_unite=10, id=1),
            Mouvement(AUJOURDHUI, "STOCK_INITIAL", "VALO INVENTAIRE CHER", 500, 90, id=2),
        ],
    )


def _deux_lignes() -> list[LigneInventaire]:
    return [
        LigneInventaire(1, "VALO INVENTAIRE", 500, compte=550, lot_id=11, magasin_id=1),
        LigneInventaire(2, "VALO INVENTAIRE CHER", 500, compte=450, lot_id=12, magasin_id=1),
    ]


def test_zero_kilo_net_et_4000_mad_de_perte() -> None:
    """Hérité : test_valorisation.py::test_api_l_inventaire_valorise_ses_ecarts_et_ne_se_date_
    pas_avant_ce_qu_il_fige (partie calcul : écarts au CMUP, totaux)."""
    couts = couts_inventaire(_ouverture())
    assert couts.cmup == pytest.approx({"VALO INVENTAIRE": 10, "VALO INVENTAIRE CHER": 90})
    i = ecarts_inventaire(_deux_lignes(), statut="ouvert", tolerance=TOLERANCE, couts=couts)
    assert i.ecart_total == pytest.approx(0) and i.ecart_absolu == pytest.approx(100)
    assert i.ecart_valeur_mad == pytest.approx(50 * 10 - 50 * 90)
    assert i.ecart_valeur_absolue_mad == pytest.approx(50 * 10 + 50 * 90)
    assert (i.nb_lignes, i.nb_comptees, i.hors_tolerance, i.a_recompter) == (2, 2, 2, 2)
    assert [x.valeur_ecart_mad for x in i.lignes] == pytest.approx([500, -4500])


def test_valide_l_ecart_passe_au_cout_de_l_ajustement_ecrit() -> None:
    """Hérité : même essai, après validation (`ecart_valeur_mad` = −4 000) ; le coût vient
    de l'ajustement écrit (n° 21, 22), pas du CMUP d'aujourd'hui."""
    couts = CoutsInventaire(
        cmup={"VALO INVENTAIRE": 99.0, "VALO INVENTAIRE CHER": 99.0},
        unitaire={21: 10.0, 22: 90.0},
    )
    ajustements: dict[tuple[int | None, int | None], int] = {(11, 1): 21, (12, 1): 22}
    v = ecarts_inventaire(
        _deux_lignes(), statut="valide", tolerance=TOLERANCE, couts=couts, ajustements=ajustements
    )
    assert v.ecart_valeur_mad == pytest.approx(-4000)
    # Ouvert, les ajustements ne comptent pas encore : le CMUP du moment valorise.
    o = ecarts_inventaire(
        _deux_lignes(), statut="ouvert", tolerance=TOLERANCE, couts=couts, ajustements=ajustements
    )
    assert [x.cmup_mad for x in o.lignes] == [99.0, 99.0]
    # Un ajustement inconnu du journal, une matière sans CMUP : le CMUP, sinon 0.
    couts.unitaire = {}
    couts.cmup = {"VALO INVENTAIRE": 7.0}
    a = ecarts_inventaire(
        _deux_lignes(), statut="annule", tolerance=TOLERANCE, couts=couts, ajustements=ajustements
    )
    assert [x.cmup_mad for x in a.lignes] == [7.0, 0.0]


def test_le_second_comptage_ajuste() -> None:
    """Hérité : test_stock_atelier.py::test_inventaire_second_comptage (partie calcul)."""
    theorique = 500.0
    ligne = LigneInventaire(1, "F", theorique, compte=theorique - 40)
    couts = CoutsInventaire({"F": 10.0}, {})
    i = ecarts_inventaire([ligne], statut="ouvert", tolerance=TOLERANCE, couts=couts)
    assert i.a_recompter == 1 and i.lignes[0].a_recompter and i.recomptees == 0
    ligne.second_compte = theorique - 1
    i = ecarts_inventaire([ligne], statut="ouvert", tolerance=TOLERANCE, couts=couts)
    vue = i.lignes[0]
    assert vue.retenu == theorique - 1 and not vue.hors_tolerance
    assert i.a_recompter == 0 and i.recomptees == 1
    assert i.ecart_total == pytest.approx(-1)


def test_une_ligne_pas_comptee_ne_fait_pas_d_ecart() -> None:
    lignes = [LigneInventaire(1, "F", 100), LigneInventaire(2, "F", 100, compte=100)]
    i = ecarts_inventaire(
        lignes, statut="ouvert", tolerance=TOLERANCE, couts=CoutsInventaire({"F": 5.0}, {})
    )
    assert (i.nb_lignes, i.nb_comptees) == (2, 1)
    assert i.lignes[0].ecart is None and i.lignes[0].valeur_ecart_mad is None
    assert i.lignes[0].cmup_mad == 5.0 and i.ecart_total == 0 and i.hors_tolerance == 0


@pytest.mark.parametrize(
    ("theorique", "compte", "attendu"),
    [
        (100, None, False),  # pas compté
        (100, 100.0005, False),  # sous le gramme
        (0, 0.5, True),  # un théorique nul : tout écart compte
        (-3, -2, True),  # un théorique négatif aussi
        (100, 102, False),  # 2 % : à la tolérance, pas au-delà
        (100, 97.9, True),  # 2,1 %
    ],
)
def test_hors_tolerance(theorique: float, compte: float | None, attendu: bool) -> None:
    assert hors_tolerance(theorique, compte, TOLERANCE) is attendu


def test_retenu_et_a_recompter() -> None:
    ligne = LigneInventaire(1, "F", 100, compte=80)
    assert retenu(ligne) == 80 and a_recompter(ligne, TOLERANCE)
    assert ecart_hors_tolerance(ligne, TOLERANCE)
    ligne.second_compte = 99.5
    assert retenu(ligne) == 99.5 and not a_recompter(ligne, TOLERANCE)
    assert not ecart_hors_tolerance(ligne, TOLERANCE)
    ligne.second_compte = 0.0  # un second comptage à zéro est un comptage
    assert retenu(ligne) == 0.0 and ecart_hors_tolerance(ligne, TOLERANCE)


# ── Inventaire tournant ──────────────────────────────────────────────────────

MAGASINS = {1: "COURANT", 2: "MOROCCO", 3: "QUAR"}


def test_une_matiere_comptee_sort_du_tournant() -> None:
    """Hérité : test_stock_atelier.py::test_inventaire_tolerance_perimetre_et_feuille (partie
    calcul : la matière comptée aujourd'hui sort, l'autre reste due)."""
    stocks = [StockAuMagasin(1, "E FRANGE", 1, 30), StockAuMagasin(2, "E POIL BLEU", 1, 400)]
    dues = a_compter(
        stocks, classes={}, derniers={(1, 1): AUJOURDHUI}, magasins=MAGASINS, aujourdhui=AUJOURDHUI
    )
    assert [x.reference for x in dues] == ["E POIL BLEU"]
    assert dues[0].classe_abc == "C" and dues[0].dernier_comptage is None and dues[0].jours is None


def test_cadences_a_b_c() -> None:
    def du(classe: str, jours: int) -> bool:
        dues = a_compter(
            [StockAuMagasin(1, "F", 1, 10)],
            classes={"F": classe},
            derniers={(1, 1): AUJOURDHUI - timedelta(days=jours)},
            magasins=MAGASINS,
            aujourdhui=AUJOURDHUI,
        )
        return bool(dues)

    assert not du("A", 29) and du("A", 30)
    assert not du("B", 89) and du("B", 90)
    assert not du("C", 364) and du("C", 365)
    assert not du("", 364) and du("", 365)  # classe vide : C
    assert not du("Z", 364) and du("Z", 365)  # classe inconnue : 365 jours


def test_un_comptage_ne_vaut_que_pour_son_magasin() -> None:
    """Audit 2-G M2 : compté à Morocco, le fil reste dû pour ses kilos jamais comptés ailleurs ;
    regroupé par matière, « jamais » l'emporte sur la date, magasins triés."""
    vieux = AUJOURDHUI - timedelta(days=400)
    stocks = [
        StockAuMagasin(1, "F", 2, 100, role="Poil", kg_par_ml=0.0),
        StockAuMagasin(1, "F", 3, 50),
        StockAuMagasin(1, "F", 1, 1288),
    ]
    derniers = {(1, 2): vieux, (1, 1): AUJOURDHUI - timedelta(days=10)}
    dues = a_compter(
        stocks, classes={"F": "C"}, derniers=derniers, magasins=MAGASINS, aujourdhui=AUJOURDHUI
    )
    assert len(dues) == 1
    x = dues[0]
    # Le courant, compté il y a 10 jours, n'est pas dû ; Morocco (400 j) et la quarantaine
    # (jamais) le sont.
    assert x.stock == pytest.approx(150) and x.magasins == ["MOROCCO", "QUAR"]
    assert x.dernier_comptage is None and x.jours is None and x.role == "Poil"
    # Sans la quarantaine : le plus ancien comptage des magasins dus.
    dues = a_compter(
        stocks[:1], classes={"F": "C"}, derniers=derniers, magasins=MAGASINS, aujourdhui=AUJOURDHUI
    )
    assert dues[0].dernier_comptage == vieux and dues[0].jours == 400


def test_le_plus_ancien_comptage_l_emporte() -> None:
    a, b = AUJOURDHUI - timedelta(days=500), AUJOURDHUI - timedelta(days=400)
    stocks = [StockAuMagasin(1, "F", 2, 10), StockAuMagasin(1, "F", 1, 10)]
    dues = a_compter(
        stocks,
        classes={},
        derniers={(1, 2): b, (1, 1): a},
        magasins=MAGASINS,
        aujourdhui=AUJOURDHUI,
    )
    assert dues[0].dernier_comptage == a and dues[0].jours == 500


def test_poussiere_magasin_et_tri() -> None:
    stocks = [
        StockAuMagasin(1, "C-JAMAIS", 1, 10),
        StockAuMagasin(2, "A-VIEUX", 1, 10),
        StockAuMagasin(3, "A-JAMAIS", 1, 10),
        StockAuMagasin(4, "B-ZED", 1, 10),
        StockAuMagasin(5, "B-ABC", 1, 10),
        StockAuMagasin(6, "POUSSIERE", 1, 0.001),
        StockAuMagasin(7, "AILLEURS", 2, 10),
    ]
    classes = {"A-VIEUX": "A", "A-JAMAIS": "A", "B-ZED": "B", "B-ABC": "B"}
    derniers = {(2, 1): AUJOURDHUI - timedelta(days=60)}
    dues = a_compter(
        stocks, classes=classes, derniers=derniers, magasins=MAGASINS, aujourdhui=AUJOURDHUI
    )
    # Classe, puis jamais compté en tête, puis référence ; sous le gramme, rien n'est détenu.
    assert [x.reference for x in dues] == [
        "A-JAMAIS",
        "A-VIEUX",
        "B-ABC",
        "B-ZED",
        "AILLEURS",
        "C-JAMAIS",
    ]
    seul = a_compter(
        stocks,
        classes=classes,
        derniers=derniers,
        magasins=MAGASINS,
        aujourdhui=AUJOURDHUI,
        magasin_id=2,
    )
    assert [x.reference for x in seul] == ["AILLEURS"] and seul[0].magasins == ["MOROCCO"]
