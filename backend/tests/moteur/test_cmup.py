"""La valeur du stock : le coût moyen (CMUP) rejoué sur le journal (`calcul.valorisation`).

Une annulation défait l'écriture annulée à son coût ; un retour au fournisseur sort au coût
de son lot ; une entrée dédouanée retrouve son dossier par sa ligne de réception ; une entrée
en devise garde le cours de sa validation ; un coût nul est un coût.
"""

from __future__ import annotations

import pytest

from gestion_mp_pro.calcul import valorisation
from gestion_mp_pro.calcul.importations import revient_par_lot
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    DossierImport,
    LigneImport,
    LignePrix,
)
from gestion_mp_pro.calcul.valorisation import (
    cmup_glissant,
    cmup_par_reference,
    couts_du_journal,
)
from moteur.fabrique import J1, J2, J3, ecriture, journal


def test_annuler_une_reception_retire_son_prix_du_cmup() -> None:
    """Hérité : test_valorisation::test_annuler_une_reception_retire_son_prix_du_cmup.

    L'exemple de l'audit : 125,7 kg à 26,89 ; 1 000 kg à 200 reçus puis annulés."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 125.7, prix=26.89),
        ecriture(2, J2, "ENTREE_RECEPTION", 1000, prix=200),
        ecriture(3, J2, "ENTREE_RECEPTION", -1000, prix=200, annule=2),
    )
    couts = couts_du_journal(d)
    assert couts.cmup()["P50"] == pytest.approx(26.89)
    assert couts.stock["P50"][1] == pytest.approx(125.7 * 26.89)  # 3 380, pas 22 710
    assert couts.unitaire[3] == pytest.approx(200)


def test_annuler_une_sortie_la_fait_rentrer_a_son_cout() -> None:
    """Hérité : test_valorisation::test_annuler_une_sortie_la_fait_rentrer_a_son_cout."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10),
        ecriture(2, J2, "SORTIE_PROD", 40, of="OF-1"),
        ecriture(3, J3, "ENTREE_RECEPTION", 100, prix=40),
        # L'annulation de la sortie, saisie après la réception mais datée comme elle.
        ecriture(4, J2, "SORTIE_PROD", -40, annule=2, of="OF-1"),
    )
    couts = couts_du_journal(d)
    assert couts.unitaire[4] == pytest.approx(10)
    assert couts.stock["P50"] == pytest.approx([200, 100 * 10 + 100 * 40])


def test_un_retour_fournisseur_sort_au_cout_de_son_lot() -> None:
    """Hérité : test_valorisation::test_un_retour_fournisseur_sort_au_cout_de_son_lot."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10, lot="A"),
        ecriture(2, J1, "ENTREE_RECEPTION", 100, prix=50, lot="B"),
        ecriture(3, J2, "RETOUR_FOURNISSEUR", 100, lot="B"),
    )
    couts = couts_du_journal(d)
    # Au coût moyen (30), le stock restant aurait gardé 2 000 MAD de la marchandise rendue.
    assert couts.unitaire[3] == pytest.approx(50)
    assert couts.cmup()["P50"] == pytest.approx(10)


def test_le_cout_d_une_entree_importee_se_trouve_par_sa_ligne_de_reception() -> None:
    """Hérité :
    test_valorisation::test_le_cout_d_une_entree_importee_se_trouve_par_sa_ligne_de_reception.

    Deux livraisons sur le même n° de lot, deux dossiers : chacune garde son coût. Une
    marchandise saisie à la main dans un dossier se retrouve, elle, par son lot."""
    dossiers = [
        DossierImport(
            numero="D1",
            lignes=[LigneImport(1, "P50", 100, 1000, lot_fournisseur="L", ligne_reception_id=11)],
            charges=[ChargeImport(poste="FRET", montant=100)],
        ),
        DossierImport(
            numero="D2",
            lignes=[LigneImport(2, "P50", 100, 3000, lot_fournisseur="L", ligne_reception_id=12)],
            charges=[ChargeImport(poste="FRET", montant=300)],
        ),
        DossierImport(
            numero="D3",
            lignes=[LigneImport(3, "P50", 50, 500, lot_fournisseur="M")],
            charges=[ChargeImport(poste="TRANSIT", montant=50)],
        ),
    ]
    d = journal(
        ecriture(1, J1, "ENTREE_RECEPTION", 100, prix=10, lot="L", ligne=11),
        ecriture(2, J2, "ENTREE_RECEPTION", 100, prix=30, lot="L", ligne=12),
        ecriture(3, J2, "STOCK_INITIAL", 50, prix=10, lot="M"),
        dossiers_import=dossiers,
    )
    couts = couts_du_journal(d)
    assert couts.unitaire[1] == pytest.approx(11)
    assert couts.unitaire[2] == pytest.approx(33)  # avant : 33 pour les deux (le dernier dossier)
    assert couts.unitaire[3] == pytest.approx(11)
    assert revient_par_lot(d) == {("P50", "M"): pytest.approx(11)}


def test_une_entree_en_devise_garde_le_cours_de_sa_validation() -> None:
    """Hérité : test_valorisation::test_une_entree_en_devise_garde_le_cours_de_sa_validation."""
    articles = [Article(reference="P50", prix_unite=2, devise="USD")]
    figee = journal(
        ecriture(1, J1, "ENTREE_RECEPTION", 100, prix=2, devise="USD", cours=10),
        articles=articles,
    )
    figee.parametres.taux_usd_mad = 12
    assert cmup_glissant(figee)["P50"] == pytest.approx(20)
    # Sans cours figé (une écriture reprise d'avant), le cours du jour s'applique encore.
    ancienne = journal(
        ecriture(1, J1, "ENTREE_RECEPTION", 100, prix=2, devise="USD"), articles=articles
    )
    ancienne.parametres.taux_usd_mad = 12
    assert cmup_glissant(ancienne)["P50"] == pytest.approx(24)


def test_sans_stock_le_cmup_moyenne_les_achats_chacun_dans_sa_devise() -> None:
    """Hérité :
    test_valorisation::test_sans_stock_le_cmup_moyenne_les_achats_chacun_dans_sa_devise.
    """
    d = journal(
        articles=[Article(reference="P50", prix_unite=2, devise="EUR")],
        historique_prix=[
            LignePrix(date_bc=J1, reference="P50", quantite=100, prix_achat=2, devise="EUR"),
            LignePrix(date_bc=J2, reference="P50", quantite=100, prix_achat=20, devise="MAD"),
        ],
    )
    # (100 × 2 × 11 + 100 × 20) / 200 = 21 — et non (200 + 2 000) / 200 × 11 = 121.
    assert cmup_par_reference(d)["P50"] == pytest.approx(21)


def test_une_annulation_du_jour_ne_pese_pas_sur_les_sorties_du_jour() -> None:
    """Hérité : test_valorisation::test_une_annulation_du_jour_ne_pese_pas_sur_les_sorties_du_jour.

    Un lot saisi à 30 par erreur et annulé dans la journée, après une sortie du même jour.
    La sortie part à 10 (le seul lot vrai), le stock vaut 500."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10, lot="J1"),
        ecriture(2, J2, "ENTREE_RECEPTION", 100, prix=30, lot="J2"),
        ecriture(3, J2, "SORTIE_PROD", 50, lot="J1", of="OF-1"),
        ecriture(4, J2, "ENTREE_RECEPTION", -100, prix=30, lot="J2", annule=2),
    )
    couts = couts_du_journal(d)
    assert couts.unitaire[4] == pytest.approx(30)
    assert couts.unitaire[3] == pytest.approx(10)  # avant : 20, puis 750 MAD au catalogue
    assert couts.stock["P50"] == pytest.approx([50, 500])


def test_une_reentree_sur_stock_vide_reprend_ce_qu_elle_a_coute() -> None:
    """Hérité : test_valorisation::test_une_reentree_sur_stock_vide_reprend_ce_qu_elle_a_coute.

    100 kg à 10 (catalogue 30) sortent en entier ; 20 kg reviennent des machines, 5 kg sont
    retrouvés à l'inventaire. Ils rentrent à 10, pas au catalogue."""
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10),
        ecriture(2, J2, "SORTIE_PROD", 100, of="OF-1"),
        ecriture(3, J3, "RETOUR_PRODUCTION", 20, of="OF-1"),
    )
    couts = couts_du_journal(d)
    assert couts.unitaire[3] == pytest.approx(10)
    assert couts.stock["P50"] == pytest.approx([20, 200])
    assert sum(v for _, v in couts.consommation) == pytest.approx(800)  # 80 kg consommés
    # Un lot retrouvé : le coût d'entrée de son lot.
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10),
        ecriture(2, J2, "SORTIE_PROD", 100, of="OF-1"),
        ecriture(3, J3, "AJUSTEMENT_INVENTAIRE", 5),
    )
    assert couts_du_journal(d).unitaire[3] == pytest.approx(10)
    # Un lot inconnu : le dernier coût moyen de la matière (ici (100×10 + 100×20) / 200).
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10, lot="A"),
        ecriture(2, J1, "STOCK_INITIAL", 100, prix=20, lot="B"),
        ecriture(3, J2, "SORTIE_PROD", 200, lot="A", of="OF-1"),
        ecriture(4, J3, "AJUSTEMENT_INVENTAIRE", 5, lot="X"),
    )
    assert couts_du_journal(d).unitaire[4] == pytest.approx(15)
    # Rien de connu : le catalogue, en dernier recours.
    d = journal(ecriture(1, J1, "AJUSTEMENT_INVENTAIRE", 5, lot="X"))
    assert couts_du_journal(d).unitaire[1] == pytest.approx(30)


def test_un_cout_nul_est_un_cout() -> None:
    """Hérité : test_valorisation::test_un_cout_nul_est_un_cout.

    Une ouverture à 0 MAD, annulée, sort à 0 — pas au coût moyen. Et un stock qui ne vaut
    rien a un coût moyen de 0, pas celui des achats ni du catalogue."""
    sans_prix = [Article(reference="P50", prix_unite=0.0, fournisseur="F")]
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=10, lot="B1"),
        ecriture(2, J1, "STOCK_INITIAL", 100, prix=0, lot="B2"),
        ecriture(3, J2, "STOCK_INITIAL", -100, prix=0, lot="B2", annule=2),
        articles=sans_prix,
    )
    couts = couts_du_journal(d)
    assert couts.unitaire[3] == 0
    assert couts.stock["P50"] == pytest.approx([100, 1000])  # avant : 500
    d = journal(
        ecriture(1, J1, "STOCK_INITIAL", 100, prix=0),
        articles=sans_prix,
        historique_prix=[LignePrix(date_bc=J1, reference="P50", quantite=10, prix_achat=20)],
    )
    assert cmup_par_reference(d)["P50"] == 0  # avant : 20


def test_un_revient_negatif_par_le_lot_ne_fait_pas_le_cout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hérité : test_defauts_c::test_un_revient_negatif_par_le_lot_ne_fait_pas_le_cout."""
    monkeypatch.setattr(valorisation, "revient_par_lot", lambda d: {("P50", "L1"): -5.0})
    d = journal(ecriture(1, J1, "STOCK_INITIAL", 100, prix=10))
    assert couts_du_journal(d).unitaire[1] == pytest.approx(10)


def test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception() -> None:
    """Hérité (partie moteur) :
    test_importations_second_audit::test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception.

    Un dossier saisi à la main sur le lot A2L-1 (10 kg pour 10 000 MAD), puis une réception
    hors dossier sur ce même lot : elle entre à son prix (2 USD × 10), pas à 1 000 MAD."""
    dossier = DossierImport(
        numero="A2/19",
        lignes=[LigneImport(1, "P50", 10, 10_000, devise="MAD", lot_fournisseur="A2L-1")],
    )
    d = journal(
        ecriture(1, J1, "ENTREE_RECEPTION", 100, prix=2.0, devise="USD", lot="A2L-1", ligne=7),
        dossiers_import=[dossier],
    )
    d.parametres.taux_usd_mad = 10
    assert revient_par_lot(d) == {("P50", "A2L-1"): pytest.approx(1000)}
    assert couts_du_journal(d).unitaire[1] == pytest.approx(2.0 * 10)
    # Sans ligne de réception (une entrée reprise d'avant), le lot du dossier fait le coût.
    d.mouvements = [ecriture(1, J1, "STOCK_INITIAL", 10, prix=2.0, devise="USD", lot="A2L-1")]
    assert couts_du_journal(d).unitaire[1] == pytest.approx(1000)
