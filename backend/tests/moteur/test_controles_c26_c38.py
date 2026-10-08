"""Contrôles C26 à C38 : chacun sonne sur une donnée fautive, avec le nombre exact d'anomalies,
et se tait une fois la donnée corrigée (PLAN-DE-RECETTE-PRO § 4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import pytest

from gestion_mp_pro.calcul.controles import Controle, controler
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    DossierImport,
    LigneImport,
    LignePrix,
    LigneReception,
    Mouvement,
    Reception,
)
from gestion_mp_pro.calcul.modele import Donnees as D
from gestion_mp_pro.calcul.stock import LigneStock

JOUR = date(2026, 10, 8)
VEILLE = date(2026, 10, 7)
FORMES_VARIABLES = {"C11", "C12", "C16", "C36"}


def _controle(
    code: str,
    donnees: D,
    lignes: Sequence[LigneStock] = (),
    complet: D | None = None,
    aujourdhui: date | None = None,
) -> Controle:
    tous = controler(donnees, list(lignes), JOUR, complet, aujourdhui)
    resultat = next(c for c in tous if c.code == code)
    cles = [colonne.cle for colonne in resultat.colonnes]
    for ligne in resultat.detail:
        assert list(ligne) == [k for k in cles if k in ligne]
        if code not in FORMES_VARIABLES:
            assert list(ligne) == cles
    assert resultat.quoi_faire
    return resultat


def _sonne(code: str, donnees: D, nombre: int, *args, **autres) -> Controle:
    resultat = _controle(code, donnees, *args, **autres)
    assert resultat.anomalies == nombre == len(resultat.detail)
    assert not resultat.conforme and resultat.garanti == ""
    return resultat


def _conforme(code: str, donnees: D, *args, **autres) -> Controle:
    resultat = _controle(code, donnees, *args, **autres)
    assert resultat.anomalies == 0 and resultat.detail == [] and resultat.conforme
    return resultat


def test_c26_sortie_sans_numero_de_lot():
    mouvements = [
        Mouvement(VEILLE, "SORTIE_PROD", "A", 10, numero_of="OF-1", utilisateur="u"),
        Mouvement(VEILLE, "RETOUR_FOURNISSEUR", "B", 5, motif_retour="R5", utilisateur="u"),
        Mouvement(VEILLE, "SORTIE_PROD", "C", 5, lot_fournisseur="L1", numero_of="OF-1"),
        Mouvement(VEILLE, "STOCK_INITIAL", "D", 5),
    ]
    donnees = D(mouvements=mouvements)
    c26 = _sonne("C26", donnees, 2)
    assert c26.detail[0] == {
        "date": "2026-10-07",
        "reference": "A",
        "quantite": 10,
        "numero_of": "OF-1",
        "utilisateur": "u",
    }
    assert c26.gravite == "avertissement" and c26.lien == "/stock?onglet=mouvements"
    mouvements[0].lot_fournisseur = mouvements[1].lot_fournisseur = "L1"
    assert "lot" in _conforme("C26", donnees).garanti


def test_c27_lot_dont_il_est_sorti_plus_qu_il_n_est_entre():
    journal = [
        Mouvement(VEILLE, "STOCK_INITIAL", "A", 10, lot_fournisseur="L1", magasin_destination="M"),
        Mouvement(JOUR, "SORTIE_PROD", "A", 15, lot_fournisseur="L1", magasin_source="M"),
    ]
    complet = D(mouvements=journal)
    c27 = _sonne("C27", D(), 1, complet=complet)
    assert c27.detail == [
        {"reference": "A", "lot": "L1", "stock": -5, "entrees": 10, "sorties": 15}
    ]
    assert c27.gravite == "bloquant" and c27.lien == "/stock?onglet=lots"
    assert "Suivre" in c27.quoi_faire
    journal[1].quantite = 10
    _conforme("C27", D(), complet=complet)


def test_c28_dossier_arrive_sans_frais_hors_tva():
    marchandises = [LigneImport(1, "A", valeur_devise=100), LigneImport(2, "B", valeur_devise=50)]
    dossier = DossierImport(
        "D1",
        date_arrivee=JOUR - timedelta(days=40),
        lignes=marchandises,
        charges=[ChargeImport("TVA", 100)],
    )
    clos = DossierImport(
        "D2", date_arrivee=JOUR - timedelta(days=90), statut="Clos", lignes=list(marchandises)
    )
    recent = DossierImport("D3", date_arrivee=JOUR - timedelta(days=10), lignes=list(marchandises))
    donnees = D(dossiers_import=[dossier, clos, recent])
    c28 = _sonne("C28", donnees, 1)
    assert c28.detail == [
        {"dossier": "D1", "arrivee": "2026-08-29", "marchandises": 2, "jours_arrivee": 40}
    ]
    assert c28.libelle == (
        "Dossier d'importation arrivé depuis plus de 30 jours et sans frais hors TVA"
    )
    assert c28.gravite == "avertissement" and c28.lien == "/importations"
    dossier.charges.append(ChargeImport("DD", 50))
    _conforme("C28", donnees)


def test_c29_tva_eloignee_de_l_attendue():
    tva = ChargeImport("TVA", 300)
    dossier = DossierImport(
        "D1",
        lignes=[LigneImport(1, "A", valeur_devise=1000)],
        charges=[ChargeImport("DD", 100), ChargeImport("TPI", 2.75), tva],
    )
    donnees = D(dossiers_import=[dossier, DossierImport("D2", charges=[ChargeImport("TVA", 5)])])
    c29 = _sonne("C29", donnees, 1)
    ligne = c29.detail[0]
    assert ligne["dossier"] == "D1" and ligne["tva_saisie"] == 300
    assert ligne["tva_attendue"] == pytest.approx(220.55)
    assert ligne["ecart_mad"] == pytest.approx(79.45)
    assert c29.libelle == (
        "TVA d'importation à plus de 5 % de la TVA attendue (20 % de la valeur en douane, "
        "droits et TPI compris)"
    )
    assert c29.gravite == "avertissement" and c29.lien == "/importations"
    tva.montant = 210  # 10,55 d'écart : sous les 5 % (11,03)
    _conforme("C29", donnees)


def test_c30_poids_de_bobine_eloigne_du_catalogue():
    pesee = LigneReception("A", quantite_bl=100, quantite_pesee=100, nb_bobines=10)
    reception = Reception(
        "R-1", date_reception=VEILLE, fournisseur="F", statut="Validée", lignes=[pesee]
    )
    article = Article("A", fournisseur="F", poids_bobine=8)
    donnees = D(articles=[article], receptions=[reception])
    c30 = _sonne("C30", donnees, 1)
    assert c30.detail == [
        {
            "reference": "A",
            "fournisseur": "F",
            "catalogue": 8,
            "constate": 10.0,
            "ecart": 0.25,
            "reception": "R-1",
        }
    ]
    assert c30.libelle == "Poids de bobine reçu éloigné du catalogue de plus de 5 %"
    assert c30.gravite == "information" and c30.lien == "/receptions?onglet=bobines"
    article.poids_bobine = 10.2
    _conforme("C30", donnees)


def _sortie(jour: date, ordre: str) -> Mouvement:
    return Mouvement(jour, "SORTIE_PROD", "A", 5, numero_of=ordre, lot_fournisseur="L")


def test_c31_ordre_servi_a_plusieurs_dates():
    mouvements = [
        _sortie(date(2026, 10, 5), "OF-2026-0001"),
        _sortie(date(2026, 10, 1), "OF-2026-0001"),
    ]
    donnees = D(mouvements=mouvements)
    c31 = _sonne("C31", donnees, 1)
    assert c31.detail == [
        {"numero_of": "OF-2026-0001", "dates": "01/10/2026 · 05/10/2026", "nb_dates": 2}
    ]
    assert c31.gravite == "avertissement" and c31.lien == "/sorties"
    mouvements[1].date = date(2026, 10, 5)
    assert "une seule date" in _conforme("C31", donnees).garanti


def test_c32_ordre_date_avant_un_numero_inferieur():
    mouvements = [
        _sortie(date(2026, 10, 5), "OF-2026-0001"),
        _sortie(date(2026, 10, 1), "OF-2026-0002"),
        _sortie(date(2026, 9, 1), "LIBRE"),
    ]
    donnees = D(mouvements=mouvements)
    c32 = _sonne("C32", donnees, 1)
    assert c32.detail == [
        {
            "numero_of": "OF-2026-0002",
            "date": "01/10/2026",
            "apres": "OF-2026-0001",
            "date_apres": "05/10/2026",
        }
    ]
    assert c32.gravite == "information" and c32.lien == "/sorties"
    mouvements[1].date = date(2026, 10, 6)
    assert "suivent les dates" in _conforme("C32", donnees).garanti


def test_c33_stock_minimum_au_dela_du_plafond_plus_long_d_abord():
    lignes = [
        LigneStock(
            "B", stock_min=600, conso_mensuelle=100, conso_horizon=100, stock_min_plafonne=300
        ),
        LigneStock(
            "A", stock_min=1000, conso_mensuelle=90, conso_horizon=100.04, stock_min_plafonne=300.4
        ),
        LigneStock(
            "C", stock_min=600, conso_mensuelle=0, conso_horizon=100, stock_min_plafonne=300
        ),
    ]
    c33 = _sonne("C33", D(), 2, lignes)
    assert c33.detail[0] == {
        "reference": "A",
        "stock_min_catalogue": 1000,
        "conso_mensuelle": 100.0,
        "mois": 10.0,
        "retenu": 300,
    }
    assert c33.detail[1]["reference"] == "B"
    assert c33.libelle == "Stock minimum du catalogue supérieur à 3 mois de consommation"
    assert c33.gravite == "information" and c33.lien == "/catalogue?onglet=matieres"
    for ligne in lignes:
        ligne.stock_min_plafonne = ligne.stock_min
    _conforme("C33", D(), lignes)


def test_c34_frais_sans_marchandise():
    dossier = DossierImport("D1", charges=[ChargeImport("DD", 100), ChargeImport("TVA", 50)])
    donnees = D(dossiers_import=[dossier, DossierImport("D2")])
    c34 = _sonne("C34", donnees, 1)
    assert c34.detail == [{"dossier": "D1", "frais": 100, "tva": 50}]
    assert c34.gravite == "avertissement" and c34.lien == "/importations?onglet=rattacher"
    dossier.lignes.append(LigneImport(1, "A", valeur_devise=1000))
    _conforme("C34", donnees)


def test_c35_frais_aberrants_en_fraction():
    entier = DossierImport(
        "D1", lignes=[LigneImport(1, "A", valeur_devise=1000)], charges=[ChargeImport("DD", 1500)]
    )
    une_ligne = DossierImport(
        "D2",
        lignes=[
            LigneImport(1, "A", valeur_devise=10000),
            LigneImport(2, "B", valeur_devise=220),
            LigneImport(3, "C", valeur_devise=0),
        ],
        charges=[ChargeImport("DD", 5000, ligne=2), ChargeImport("FRET", 100, ligne=3)],
    )
    donnees = D(dossiers_import=[entier, une_ligne])
    c35 = _sonne("C35", donnees, 3)
    assert c35.detail[0] == {
        "dossier": "D1",
        "reference": "(tout le dossier)",
        "marchandise_mad": 1000.0,
        "frais_mad": 1500.0,
        "surcout": 1.5,
    }
    assert c35.detail[1]["reference"] == "B"
    assert c35.detail[1]["surcout"] == 5000 / 220  # la fraction, non arrondie
    assert c35.detail[2]["reference"] == "C" and c35.detail[2]["surcout"] is None
    assert c35.libelle.endswith("dont les frais dépassent 100 % de la marchandise")
    assert c35.gravite == "avertissement" and c35.lien == "/importations"
    assert next(c.unite for c in c35.colonnes if c.cle == "surcout") == "%"
    entier.charges.clear()
    une_ligne.charges.clear()
    _conforme("C35", donnees)


def test_c36_facture_eloignee_de_la_marchandise_recue():
    ecartee = DossierImport(
        "D1",
        facture="FAC-1",
        facture_montant=1100,
        facture_devise="MAD",
        lignes=[LigneImport(1, "A", valeur_devise=1000)],
    )
    autre_devise = DossierImport(
        "D2",
        facture="FAC-2",
        facture_montant=500,
        facture_devise="MAD",
        lignes=[LigneImport(1, "A", valeur_devise=50, devise="USD")],
    )
    donnees = D(dossiers_import=[ecartee, autre_devise])
    c36 = _sonne("C36", donnees, 2)
    assert c36.detail == [
        {
            "dossier": "D1",
            "facture": "FAC-1",
            "facture_montant": 1100,
            "recu": 1000,
            "devise": "MAD",
            "ecart": 0.1,
        },
        {
            "dossier": "D2",
            "facture": "FAC-2",
            "devise": "MAD",
            "motif": "marchandise en USD : ne se rapproche pas",
        },
    ]
    assert c36.libelle.endswith("éloignée de plus de 2 % de la marchandise reçue")
    assert c36.gravite == "avertissement" and c36.lien == "/importations"
    ecartee.facture_montant = 1010
    autre_devise.facture_devise = "USD"
    autre_devise.facture_montant = 50
    _conforme("C36", donnees)


def test_c37_lot_sous_zero_a_une_date_passee():
    entree = Mouvement(
        date(2026, 10, 3), "STOCK_INITIAL", "A", 10, lot_fournisseur="L1", magasin_destination="M"
    )
    sortie = Mouvement(
        date(2026, 10, 1), "SORTIE_PROD", "A", 10, lot_fournisseur="L1", magasin_source="M"
    )
    complet = D(mouvements=[entree, sortie])
    c37 = _sonne("C37", D(), 1, complet=complet)
    assert c37.detail == [
        {"reference": "A", "lot": "L1", "magasin": "M", "date": "2026-10-01", "manque": 10}
    ]
    assert _controle("C27", D(), complet=complet).anomalies == 0  # le solde final est juste
    assert c37.gravite == "bloquant" and c37.lien == "/stock?onglet=mouvements"
    entree.date = date(2026, 9, 30)
    _conforme("C37", D(), complet=complet)


def test_c38_prix_du_catalogue_loin_du_dernier_paye():
    articles = [
        Article("A", fournisseur="F", prix_unite=10),
        Article("B", fournisseur="F", prix_unite=1, unite_prix="ml", densite=0.1),
        Article("C", fournisseur="F", prix_unite=10, actif=False),
    ]
    prix = [
        LignePrix(date(2026, 8, 1), "A", fournisseur="F", prix_achat=9),
        LignePrix(date(2026, 9, 1), "A", fournisseur="G", prix_achat=2),
        LignePrix(date(2026, 10, 9), "A", fournisseur="F", prix_achat=10),
        LignePrix(date(2026, 9, 1), "B", prix_achat=100),
        LignePrix(date(2026, 9, 1), "C", prix_achat=1),
    ]
    donnees = D(articles=articles, historique_prix=prix)
    c38 = _sonne("C38", donnees, 2)
    assert c38.detail[0]["reference"] == "B"  # 10 fois loin, avant 5 fois
    assert c38.detail[0]["prix_catalogue"] == "10 MAD / kg (1 MAD / ml)"
    assert c38.detail[0]["fournisseur"] == "F" and c38.detail[0]["rapport"] == 0.1
    assert c38.detail[1] == {
        "reference": "A",
        "fournisseur": "G",
        "prix_catalogue": "10 MAD / kg",
        "prix_paye": "2 MAD / kg",
        "date": "2026-09-01",
        "rapport": 5.0,
    }
    assert c38.gravite == "avertissement" and c38.lien == "/catalogue?onglet=matieres"
    prix[1].prix_achat = 9
    prix[3].prix_achat = 12
    _conforme("C38", donnees)
