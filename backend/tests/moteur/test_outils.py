"""Les outils du moteur (`calcul.outils`) et ce qu'un bon de commande engage (`calcul.achats`)."""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.achats import (
    echeance_commande,
    montant_ligne_mad,
    pas_partie,
    reste_a_livrer,
)
from gestion_mp_pro.calcul.modele import Commande, LigneCommande, Parametres
from gestion_mp_pro.calcul.outils import (
    arrondi,
    debut_de_mois,
    fin_de_mois,
    jour_plus,
    mois_du_plan,
    mois_ecoules,
    mois_entre,
    palettes,
    pourcentage,
)
from moteur.fabrique import instant


def test_arrondi_envoie_les_demis_vers_l_exterieur() -> None:
    """Nouveau (CALCULS § 2, ARRONDI d'Excel) : 2,5 → 3 et −2,5 → −3, là où `round` de Python
    donne 2 et −2 ; les décimales aussi."""
    assert [arrondi(x) for x in (0.5, 1.5, 2.5, -2.5, 2.4999, 1002.5)] == [1, 2, 3, -3, 2, 1003]
    assert round(2.5) == 2  # la raison d'être d'`arrondi`
    assert arrondi(1.25, 1) == 1.3 and arrondi(-1.25, 1) == -1.3
    assert arrondi(1234.5678, 2) == pytest.approx(1234.57) and arrondi(0.0) == 0


def test_fins_et_debuts_de_mois_et_mois_ecoules() -> None:
    """Nouveau (CALCULS § 2) : FIN.MOIS, le plan glissant de douze fins de mois, DATEDIF + 1."""
    assert fin_de_mois(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert fin_de_mois(date(2028, 1, 15), 1) == date(2028, 2, 29)
    assert fin_de_mois(date(2026, 10, 8), -10) == date(2025, 12, 31)
    assert debut_de_mois(date(2026, 1, 15), -1) == date(2025, 12, 1)
    assert debut_de_mois(date(2026, 12, 31), 1) == date(2027, 1, 1)
    plan = mois_du_plan(date(2026, 10, 8))
    assert len(plan) == 12 and plan[0] == date(2026, 10, 31) and plan[-1] == date(2027, 9, 30)
    assert mois_entre(date(2026, 1, 15), date(2026, 9, 30)) == 8
    assert mois_entre(date(2026, 9, 30), date(2026, 1, 1)) == -8
    assert mois_ecoules(date(2026, 1, 15), date(2026, 3, 14)) == 2
    assert mois_ecoules(date(2026, 1, 15), date(2026, 3, 15)) == 3
    assert mois_ecoules(date(2026, 3, 15), date(2026, 1, 1)) == 1  # au minimum 1


def test_palettes_pourcentage_et_jour_suivant() -> None:
    """Nouveau (CALCULS § 2) : des unités entières à l'epsilon flottant près ; « 2 % » avec une
    espace ; 4,5 jours livrent le cinquième."""
    assert palettes(82.85, 1) == 83 and palettes(0.1 * 3 * 1000, 300) == 1
    assert palettes(1001, 500) == 3 and palettes(10, 0) == 0
    assert pourcentage(0.02) == "2 %" and pourcentage(0.1234) == "12.34 %"
    assert jour_plus(date(2026, 10, 8), 4.5) == date(2026, 10, 13)
    assert jour_plus(date(2026, 10, 8), 0) == date(2026, 10, 8)


def _bon(statut: str, commandee: float, recue: float, quarantaine: float = 0.0) -> Commande:
    ligne = LigneCommande("BC", "P", commandee, recue, quarantaine)
    return Commande("BC", statut=statut, lignes=[ligne])


def test_ce_qu_un_bon_engage() -> None:
    """Nouveau (CALCULS § 1.11-1.12) : l'échéance est l'ETA, sinon la date promise, sinon la
    date du bon + le délai ; un brouillon n'est pas parti ; le reste à livrer compte la
    quarantaine comme attendue, rien sous la tolérance (2 %) ni pour un bon clos."""
    jour = date(2026, 9, 1)
    assert echeance_commande(date(2026, 9, 9), date(2026, 9, 20), jour, 30) == date(2026, 9, 9)
    assert echeance_commande(None, date(2026, 9, 20), jour, 30) == date(2026, 9, 20)
    assert echeance_commande(None, None, jour, 30.7) == date(2026, 10, 1)
    assert echeance_commande(None, None, None, 30) is None
    assert pas_partie(_bon("Brouillon", 1, 0)) and not pas_partie(_bon("Envoyée", 1, 0))
    p = Parametres()
    bon = _bon("Confirmée", 1000, 600, 100)
    assert reste_a_livrer(bon, bon.lignes[0], p) == 500
    bon = _bon("Confirmée", 1000, 985)
    assert reste_a_livrer(bon, bon.lignes[0], p) == 0  # 15 kg : sous les 2 %
    bon = _bon("Soldée", 1000, 0)
    assert reste_a_livrer(bon, bon.lignes[0], p) == 0
    assert Commande("X", eta=None, date_livraison_prevue=jour).arrivee_attendue == jour
    assert Commande("X", solde_a_la_main_le=instant(2026, 9, 2)).annulee_le is None


def test_le_montant_d_une_ligne_de_bon_en_dirhams() -> None:
    """Nouveau (CALCULS B § 4.2) : au prix confirmé, sinon estimé ; au cours figé du bon, sinon
    au cours du jour."""
    p = Parametres(cours={"USD": 10.0})
    ligne = LigneCommande("BC", "P", 100, prix_unite=2.0, devise="USD", prix_estime=2.5)
    assert montant_ligne_mad(ligne, 100, p) == pytest.approx(100 * 2.5 * 10)
    ligne.prix_confirme = True
    assert montant_ligne_mad(ligne, 100, p) == pytest.approx(100 * 2.0 * 10)
    ligne.cours = 9.2
    assert montant_ligne_mad(ligne, 50, p) == pytest.approx(50 * 2.0 * 9.2)
    sans_estime = LigneCommande("BC", "P", 100, prix_unite=3.0, devise="EUR")
    assert montant_ligne_mad(sans_estime, 10, p) == pytest.approx(10 * 3.0 * 11.0)
    assert p.taux("XOF") == 1.0 and p.taux(None) == 1.0
