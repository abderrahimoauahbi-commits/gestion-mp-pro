"""Les fournisseurs (`calcul.fournisseurs`) : OTIF par réception, un camion de plusieurs bons à
l'heure si chacun l'est, la complétude jugée sur les lignes dues, la moyenne sur les seules
réceptions notées, un score sur 100 qui ne se gagne plus d'office.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gestion_mp_pro.calcul.fournisseurs import (
    devises_pratiquees,
    performance_receptions,
    points_score,
    scorecard_fournisseurs,
)
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Donnees,
    Fournisseur,
    LigneCommande,
    LigneReception,
    Parametres,
    Reception,
)
from gestion_mp_pro.calcul.receptions import pesees


def _camion(arrivee: date) -> Donnees:
    bons = [
        Commande(numero="BC-1", date_bc=date(2026, 9, 1), date_livraison_prevue=date(2026, 9, 20)),
        Commande(numero="BC-2", date_bc=date(2026, 9, 1), date_livraison_prevue=date(2026, 9, 10)),
    ]
    reception = Reception(
        numero="REC-1",
        date_reception=arrivee,
        statut="Validée",
        lignes=[
            LigneReception(
                reference="A", quantite_commandee=100, quantite_pesee=100, numero_bc="BC-1"
            ),
            LigneReception(
                reference="B", quantite_commandee=50, quantite_pesee=50, numero_bc="BC-2"
            ),
        ],
    )
    return Donnees(commandes=bons, receptions=[reception])


def test_chaque_pesee_garde_son_bon() -> None:
    """Hérité : test_camion_plusieurs_bons::test_chaque_pesee_garde_son_bon."""
    assert [p.numero_bc for p in pesees(_camion(date(2026, 9, 5)))] == ["BC-1", "BC-2"]


def test_a_l_heure_si_chaque_bon_l_est() -> None:
    """Hérité : test_camion_plusieurs_bons::test_a_l_heure_si_chaque_bon_l_est."""
    assert performance_receptions(_camion(date(2026, 9, 5)))[0].on_time == 1
    # Le 15 : à l'heure pour BC-1 (prévu le 20), en retard pour BC-2 (prévu le 10).
    tolerance = int(Parametres().toler_retard_jours)
    assert performance_receptions(_camion(date(2026, 9, 11 + tolerance)))[0].on_time == 0


D0 = date(2026, 1, 5)


def _livre_et_hors_commande() -> Donnees:
    return Donnees(
        fournisseurs=[Fournisseur(nom="X", delai_jours=4)],
        articles=[Article(reference="R", fournisseur="X")],
        commandes=[
            Commande(
                numero="BC1",
                date_bc=D0,
                fournisseur="X",
                statut="Soldée",
                date_livraison_prevue=D0 + timedelta(days=10),
                lignes=[LigneCommande("BC1", "R", 100, 100)],
            )
        ],
        receptions=[
            Reception(
                "REC1",
                D0 + timedelta(days=5),
                "BC1",
                "X",
                statut="Validée",
                lignes=[
                    LigneReception("R", quantite_commandee=100, quantite_pesee=100, numero_bc="BC1")
                ],
            ),
            Reception(
                "REC2",
                D0 + timedelta(days=6),
                "",
                "X",
                statut="Validée",
                lignes=[LigneReception("R", quantite_pesee=50)],
            ),
        ],
    )


def test_l_otif_moyen_ne_compte_que_les_receptions_notees() -> None:
    """Hérité : test_commandes_receptions::test_l_otif_moyen_ne_compte_que_les_receptions_notees."""
    donnees = _livre_et_hors_commande()
    score = next(x for x in scorecard_fournisseurs(donnees) if x.fournisseur == "X")
    assert score.otif == 1 and score.in_full == 1 and score.receptions == 2
    # Délai de 4 jours : 20 points, pas 22,2.
    assert score.score == 100


def test_l_otif_moyen_n_a_qu_une_definition() -> None:
    """Hérité (partie moteur) : test_audit2_pilotage::test_l_otif_moyen_n_a_qu_une_definition.

    La moyenne des réceptions notées : celle d'Analyse › Fournisseurs. La photo du jour
    (`api/suivi.photographier_indicateurs` de Gestion MP) n'est pas au moteur ; elle devra
    prendre la même moyenne."""
    donnees = _livre_et_hors_commande()
    # Une troisième réception, en retard : notée 0.
    donnees.commandes.append(
        Commande(
            "BC2",
            date_bc=D0,
            fournisseur="X",
            statut="Soldée",
            date_livraison_prevue=D0 + timedelta(days=10),
            lignes=[LigneCommande("BC2", "R", 100, 100)],
        )
    )
    donnees.receptions.append(
        Reception(
            "REC3",
            D0 + timedelta(days=30),
            "BC2",
            "X",
            statut="Validée",
            lignes=[
                LigneReception("R", quantite_commandee=100, quantite_pesee=100, numero_bc="BC2")
            ],
        )
    )
    notes = [x.otif for x in performance_receptions(donnees) if x.otif is not None]
    assert sorted(notes) == [0, 1]
    score = next(x for x in scorecard_fournisseurs(donnees) if x.fournisseur == "X")
    assert score.otif == pytest.approx(sum(notes) / len(notes)) == pytest.approx(0.5)
    assert score.receptions == 3


def test_l_in_full_se_juge_sur_les_lignes_dues() -> None:
    """Hérité : test_commandes_receptions::test_l_in_full_se_juge_sur_les_lignes_dues."""
    lignes = [LigneCommande("BC1", f"R{i}", 100) for i in range(10)]
    donnees = Donnees(
        fournisseurs=[Fournisseur(nom="X", delai_jours=30)],
        articles=[Article(reference=f"R{i}", fournisseur="X") for i in range(10)],
        commandes=[
            Commande(
                numero="BC1",
                date_bc=D0,
                fournisseur="X",
                statut="Confirmée",
                date_livraison_prevue=D0 + timedelta(days=30),
                lignes=lignes,
            )
        ],
        receptions=[
            Reception(
                "REC1",
                D0 + timedelta(days=5),
                "BC1",
                "X",
                statut="Validée",
                lignes=[
                    LigneReception(
                        "R0", quantite_commandee=100, quantite_pesee=1000, numero_bc="BC1"
                    )
                ],
            )
        ],
    )
    p = performance_receptions(donnees)[0]
    assert p.in_full == 0 and p.otif == 0


def test_le_score_ne_se_gagne_plus_d_office() -> None:
    """Hérité : test_commandes_receptions::test_le_score_ne_se_gagne_plus_d_office.

    18 % de livraisons parfaites, aucun retour, délai de 4 jours : l'ancienne formule donnait
    7,2 + 40 + 22,2 = 69,4 (« Standard »)."""
    assert points_score(0.18, 0.0, 4) == pytest.approx(50.8)
    assert points_score(0.18, 0.0, 4) < Parametres().score_standard
    assert points_score(1, 0.0, 4) == pytest.approx(100)  # délai plafonné à 20
    assert points_score(1, 0.014, 15) == pytest.approx(60 + 20 * (1 - 0.014 / 0.05) + 20)
    assert points_score(1, 0.2, 200) == pytest.approx(60)


def test_le_classement_et_les_devises_pratiquees() -> None:
    """Nouveau (CALCULS B § 4) : 100 points font « Stratégique » ; un fournisseur sans
    réception notée n'a ni score ni classement ; un point de délai se perd par 5 jours au-delà
    de 15 ; les devises pratiquées se lisent au catalogue, matière par matière."""
    donnees = _livre_et_hors_commande()
    donnees.fournisseurs.append(Fournisseur(nom="Y", delai_jours=40))
    donnees.articles += [
        Article(reference="S", fournisseur="Y", devise="USD"),
        Article(reference="T", fournisseur="Y", devise="USD"),
        Article(reference="U", fournisseur="Y", devise="EUR"),
    ]
    donnees.reindexer()
    x, y = scorecard_fournisseurs(donnees)
    assert (x.fournisseur, x.classement) == ("X", "🟢 Stratégique")
    assert (y.score, y.classement, y.otif) == (None, "—", None) and not y.sous_performant
    # 20 points de délai perdus de moitié à 65 jours : 60 + 20 + 10 = 90.
    assert points_score(1, 0.0, 65) == pytest.approx(90)
    assert points_score(0.5, 0.025, 15) == pytest.approx(30 + 10 + 20)
    assert devises_pratiquees(donnees) == {"X": {"MAD": 1}, "Y": {"USD": 2, "EUR": 1}}
