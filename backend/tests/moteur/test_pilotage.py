"""Le Cockpit (`calcul.pilotage`) : stock et consommation sur la même base (CMUP), le DPO
pondéré par le reçu des douze derniers mois, le coût matière annuel, l'exposition au change.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Donnees,
    Fournisseur,
    LigneCommande,
    LignePrix,
    LigneRecette,
    Parametres,
    PlanQualite,
    Qualite,
)
from gestion_mp_pro.calcul.outils import debut_de_mois
from gestion_mp_pro.calcul.pilotage import cockpit, concentration_devises, cout_matiere_annuel
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from moteur.fabrique import ecriture, journal

AUJOURDHUI = date(2026, 10, 8)
"""La date du jour de Gestion MP (`date.today()`) devient le jour des essais."""


def test_le_cockpit_compare_stock_et_consommation_sur_la_meme_base() -> None:
    """Hérité : test_valorisation::test_le_cockpit_compare_stock_et_consommation_sur_la_meme_base.

    Stock au CMUP face à ce qui a été consommé, au CMUP : 1 000 kg à 20 MAD face à 1 200 kg
    consommés à 20 MAD sur douze mois font 304 jours — que le catalogue dise 10 ou 100. La
    part dormante se lit sur la même valeur."""
    jour = date(2026, 6, 5)
    mouvements = [ecriture(1, debut_de_mois(jour, -13), "STOCK_INITIAL", 2_200, prix=20)]
    for i in range(1, 13):
        mouvements.append(
            ecriture(
                1 + i, debut_de_mois(jour, -i) + timedelta(days=9), "SORTIE_PROD", 100, of=f"OF-{i}"
            )
        )
    mouvements.append(
        ecriture(40, debut_de_mois(jour, -13), "STOCK_INITIAL", 500, prix=8, ref="DORT")
    )
    articles = [
        Article(reference="P50", prix_unite=10, fournisseur="F"),
        Article(reference="DORT", prix_unite=100, fournisseur="F"),
    ]
    d = journal(*mouvements, articles=articles)
    tableau = cockpit(d, jour, etat_stock(d, jour))
    finance = tableau.finance
    assert finance.base_rotation == "consommation"
    assert tableau.stock.valeur_mad == pytest.approx(1000 * 20 + 500 * 8)
    jours = (debut_de_mois(jour) - debut_de_mois(jour, -12)).days
    assert finance.cout_rotation_annuel_mad == pytest.approx(1200 * 20 / jours * 365)
    assert finance.dio_jours == pytest.approx(24_000 / (1200 * 20 / jours * 365) * 365)
    assert tableau.dormant.valeur_mad == pytest.approx(500 * 8)
    assert tableau.dormant.part_valeur == pytest.approx(4000 / 24000)


def test_dpo_pondere_par_le_recu_sur_douze_mois() -> None:
    """Hérité : test_defauts_e::test_dpo_pondere_par_le_recu_sur_douze_mois."""
    jour = AUJOURDHUI
    donnees = Donnees(
        articles=[Article("A", fournisseur="F")],
        fournisseurs=[
            Fournisseur("F", delai_paiement_jours=90),
            Fournisseur("G", delai_paiement_jours=30, actif=False),
        ],
        # Un gros bon chez G, soldé sans rien livrer : il ne pèse plus.
        commandes=[
            Commande(
                "BC-G",
                date_bc=jour - timedelta(days=30),
                fournisseur="G",
                statut="Soldée",
                lignes=[LigneCommande("BC-G", "A", quantite_commandee=10_000, prix_estime=10)],
            )
        ],
        historique_prix=[
            LignePrix(jour - timedelta(days=10), "A", "F", quantite=100, prix_achat=10),
            LignePrix(jour - timedelta(days=500), "A", "G", quantite=10_000, prix_achat=10),
        ],
    )
    tableau = cockpit(donnees, jour, etat_stock(donnees, jour))
    assert tableau.finance.dpo_jours == pytest.approx(90)
    assert tableau.achats.fournisseurs_actifs == 1


def test_le_cout_matiere_annuel_est_le_cout_au_m2_du_plan() -> None:
    """Nouveau (CALCULS B § 3, `Cockpit!J54`) : Σ coût/m² de la qualité × m² des douze mois du
    plan ; sans consommation, la rotation se lit sur le plan et le stock au catalogue."""
    donnees = Donnees(
        parametres=Parametres(taux_perte=0.02),
        articles=[
            Article(reference="POIL", role_bom="Poil", prix_unite=20),
            Article(reference="TRAME", role_bom="Trame", prix_unite=2, devise="EUR"),
        ],
        qualites=[Qualite(code="Q", poids={"Poil": 1.5, "Trame": 0.5})],
        recettes=[LigneRecette("Q", "POIL", 100), LigneRecette("Q", "TRAME", 100)],
        plan=[PlanQualite("Q", base_mensuelle=1000)],
    )
    cout_m2 = (1.5 * 20 + 0.5 * 2 * 11) * 1.02
    assert cout_matiere_annuel(donnees, AUJOURDHUI) == pytest.approx(cout_m2 * 12_000)
    tableau = cockpit(donnees, AUJOURDHUI, etat_stock(donnees, AUJOURDHUI))
    assert tableau.finance.base_rotation == "plan"
    assert tableau.finance.cout_matiere_mensuel_mad == pytest.approx(cout_m2 * 1000)
    assert tableau.finance.dio_jours == 0  # rien en stock


def test_l_exposition_au_change_du_budget_a_emettre() -> None:
    """Nouveau (CALCULS B § 3, zone 6) : le budget à émettre par devise, le plus gros d'abord ;
    une ligne sans rien à commander ne compte pas."""
    lignes = [
        LigneStock("A", devise="USD", quantite_a_commander=10, montant_a_commander_mad=3000),
        LigneStock("B", devise="MAD", quantite_a_commander=5, montant_a_commander_mad=1000),
        LigneStock("C", devise="USD", quantite_a_commander=1, montant_a_commander_mad=1000),
        LigneStock("D", devise="EUR", quantite_a_commander=0, montant_a_commander_mad=9000),
    ]
    expo = concentration_devises(lignes)
    assert [(x.devise, x.references, x.montant_mad) for x in expo] == [
        ("USD", 2, 4000),
        ("MAD", 1, 1000),
    ]
    assert [x.part for x in expo] == [pytest.approx(0.8), pytest.approx(0.2)]
    assert concentration_devises([]) == []
