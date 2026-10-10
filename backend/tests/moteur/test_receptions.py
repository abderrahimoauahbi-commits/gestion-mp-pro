"""Les pesées et le poids des bobines (`calcul.receptions`, `calcul.stock.machine`) : la bobine
pesée face au catalogue, le fil monté compté au poids mesuré du lot, l'évolution d'un fil.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.modele import (
    Article,
    Donnees,
    FilMonte,
    LigneReception,
    Metier,
    Reception,
)
from gestion_mp_pro.calcul.receptions import ecart_bobine, evolution_bobines, pesees
from gestion_mp_pro.calcul.stock import fils_en_machine, stock_en_machine

POIL = Article(
    reference="REF POIL BLEU",
    role_bom="Poil",
    prix_unite=2.5,
    devise="USD",
    poids_bobine=2.0,
    bob_palette=100,
)


def _reception(
    numero: str, jour: date, kg: float, bobines: float, qualite: str = "Conforme"
) -> Reception:
    ligne = LigneReception(
        reference="REF POIL BLEU",
        lot_fournisseur=numero,
        quantite_pesee=kg,
        nb_bobines=bobines,
        nb_palettes=1,
        statut_qualite=qualite,
    )
    return Reception(numero=numero, date_reception=jour, statut="Validée", lignes=[ligne])


def test_poids_de_bobine_mesure() -> None:
    """Hérité (partie calcul) : test_referentiels_complets::test_poids_de_bobine_mesure.

    Une réception de 230 kg, 1 palette de 100 bobines : 2,3 kg la bobine, 15 % au-dessus du
    catalogue (2 kg), hors tolérance (5 %). Le fil monté se compte à ce poids (M43)."""
    d = Donnees(
        articles=[POIL],
        receptions=[_reception("MES-1", date(2026, 10, 8), 230, 100)],
    )
    (pesee,) = pesees(d)
    assert pesee.poids_moyen_bobine == pytest.approx(2.3)
    assert pesee.ecart_bobine == pytest.approx(0.15) and pesee.bobine_hors_tolerance is True
    assert ecart_bobine(2.3, 2.0) == pytest.approx(0.15)
    # Le métier MREF (10 bobines par mètre de laize) : 2 m à l'étage 1, 1,5 m à 50 % à l'étage 2.
    d.metiers = [
        Metier(
            code="MREF",
            laize=4.0,
            densite=10,
            etages=3,
            fils=[
                FilMonte("REF POIL BLEU", etage=1, metres=2, poids_bobine=2.3),
                FilMonte("REF POIL BLEU", etage=2, metres=1.5, pourcentage=50, poids_bobine=2.3),
            ],
        )
    ]
    premier, second = fils_en_machine(d)
    # Le remplissage des bobines (second : 50 %) n'entre pas dans le nombre de bobines :
    # second = 1,5 m × 10 = 15. Il agit sur le poids (× 50 %).
    assert premier.poids_bobine == 2.3 and premier.poids == pytest.approx(premier.bobines * 2.3)
    assert (premier.bobines, second.bobines) == (20, 15)
    assert stock_en_machine(d) == {"REF POIL BLEU": pytest.approx(20 * 2.3 + 15 * 2.3 * 0.5)}
    # Sans pesée connue, le poids du catalogue.
    d.metiers[0].fils[1].poids_bobine = 0
    assert stock_en_machine(d) == {"REF POIL BLEU": pytest.approx(20 * 2.3 + 15 * 2.0 * 0.5)}


def test_l_evolution_du_poids_des_bobines() -> None:
    """Nouveau (CALCULS B § 5) : la série des réceptions validées, comptées et non refusées ;
    la moyenne est celle des bobines (pas des réceptions) ; l'écart au catalogue se lit sur la
    dernière ; un métier arrêté ne compte pas."""
    d = Donnees(
        articles=[POIL],
        receptions=[
            _reception("R1", date(2026, 7, 1), 200, 100),
            _reception("R3", date(2026, 9, 1), 104, 50),
            _reception("R2", date(2026, 8, 1), 2200, 1000),
            _reception("R4", date(2026, 9, 15), 300, 100, qualite="Refusé"),
            _reception("R5", date(2026, 9, 20), 300, 0),
        ],
        metiers=[
            Metier(
                code="ARRET", densite=10, actif=False, fils=[FilMonte("REF POIL BLEU", metres=1)]
            )
        ],
    )
    d.receptions.append(
        Reception(
            "R6",
            date(2026, 9, 30),
            statut="Brouillon",
            lignes=[LigneReception("REF POIL BLEU", quantite_pesee=9, nb_bobines=1)],
        )
    )
    (fil,) = evolution_bobines(d)
    assert [m.reception for m in fil.historique] == ["R1", "R2", "R3"]
    assert (fil.premier, fil.dernier, fil.mini, fil.maxi) == (2.0, 2.08, 2.0, 2.2)
    assert fil.moyenne == pytest.approx(2504 / 1150)
    assert fil.evolution == pytest.approx(0.04) and fil.ecart_catalogue == pytest.approx(0.04)
    assert fil.hors_tolerance is False and fil.derniere_date == date(2026, 9, 1)
    assert stock_en_machine(d) == {}
    assert ecart_bobine(None, 2.0) is None and ecart_bobine(2.0, 0) is None
