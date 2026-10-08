"""Contrôles C13 à C25 : chacun sonne sur une donnée fautive, avec le nombre exact d'anomalies,
et se tait une fois la donnée corrigée (PLAN-DE-RECETTE-PRO § 4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from gestion_mp_pro.calcul.constantes import MONO_SOURCE, STATUTS
from gestion_mp_pro.calcul.controles import Controle, controler
from gestion_mp_pro.calcul.modele import (
    Article,
    FilMonte,
    Fournisseur,
    LigneRecette,
    Metier,
    Mouvement,
    Parametres,
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


def test_c13_stock_projete_negatif_plus_gros_manque_d_abord():
    lignes = [
        LigneStock("A", stock_net=5, stock_projete=-20),
        LigneStock("B", stock_projete=-50),
        LigneStock("C", stock_projete=-30, sans_achat="matière désactivée"),
        LigneStock("D", stock_projete=-0.0005),
    ]
    c13 = _sonne("C13", D(), 2, lignes)
    assert c13.detail == [
        {"reference": "B", "stock_net": 0.0, "stock_projete": -50, "manque": 50},
        {"reference": "A", "stock_net": 5, "stock_projete": -20, "manque": 20},
    ]
    assert c13.gravite == "avertissement" and c13.lien == "/plan-achat"
    for ligne in lignes:
        ligne.stock_projete = 10
    _conforme("C13", D(), lignes)


def test_c14_mouvement_futur_sur_toutes_les_donnees():
    futur = Mouvement(date(2026, 10, 9), "STOCK_INITIAL", "A", 5, utilisateur="u")
    complet = D(mouvements=[Mouvement(VEILLE, "STOCK_INITIAL", "A", 5, utilisateur="u"), futur])
    c14 = _sonne("C14", D(), 1, complet=complet)
    assert c14.detail == [{"date": "2026-10-09", "reference": "A"}]
    assert c14.gravite == "avertissement" and c14.lien == "/stock?onglet=mouvements"
    # Jugé au jour d'aujourd'hui (jamais avant la date de référence) : le 10, il est passé.
    assert _conforme("C14", D(), complet=complet, aujourdhui=date(2026, 10, 10)).garanti
    _sonne("C14", D(), 1, complet=complet, aujourdhui=date(2026, 9, 1))


def test_c15_matiere_d_une_recette_sans_prix_ou_desactivee():
    donnees = D(
        articles=[
            Article("A"),
            Article("B", prix_unite=5, actif=False),
            Article("C"),
            Article("D", prix_unite=2),
        ],
        recettes=[
            LigneRecette("Q", "A", 50),
            LigneRecette("Q", "B", 50),
            LigneRecette("Q", "C", 0),
            LigneRecette("Q", "D", 50),
            LigneRecette("Q", "INCONNUE", 50),
        ],
    )
    c15 = _sonne("C15", donnees, 2)
    assert c15.detail == [
        {"qualite": "Q", "reference": "A", "motif": "sans prix d'achat"},
        {"qualite": "Q", "reference": "B", "motif": "matière désactivée encore dans la recette"},
    ]
    assert c15.gravite == "avertissement" and c15.lien == "/catalogue?onglet=matieres"
    donnees.articles[0].prix_unite = 3
    donnees.articles[1].actif = True
    _conforme("C15", donnees)


def test_c16_integrite_referentielle():
    mouvements = [
        Mouvement(VEILLE, "STOCK_INITIAL", "A", 5, fournisseur="G", utilisateur="u"),
        Mouvement(VEILLE, "STOCK_INITIAL", "X", 5, fournisseur="F", utilisateur="u"),
    ]
    donnees = D(articles=[Article("A")], fournisseurs=[Fournisseur("F")], mouvements=mouvements)
    c16 = _sonne("C16", donnees, 2)
    assert c16.detail == [
        {"reference": "X", "date": "2026-10-07"},
        {"fournisseur": "G", "date": "2026-10-07"},
    ]
    assert c16.gravite == "bloquant" and c16.lien == "/stock?onglet=mouvements"
    mouvements[0].fournisseur = "F"
    mouvements[1].reference = "A"
    assert "clés étrangères" in _conforme("C16", donnees).garanti


def test_c17_matiere_en_alerte_sans_second_fournisseur():
    lignes = [
        LigneStock(
            "A",
            fournisseur="F",
            statut=STATUTS["RUPTURE"],
            sourcing=MONO_SOURCE,
            groupe_equiv="G1",
            montant_a_commander_mad=100,
        ),
        LigneStock("B", fournisseur="F", statut=STATUTS["CRITIQUE"], montant_a_commander_mad=500),
        LigneStock("C", statut=STATUTS["OK"], sourcing=MONO_SOURCE, groupe_equiv="G1"),
        LigneStock("D", statut=STATUTS["URGENT"], sourcing="🟢 MULTI", groupe_equiv="G2"),
    ]
    c17 = _sonne("C17", D(), 2, lignes)
    assert c17.detail == [
        {"reference": "B", "fournisseur": "F", "montant_a_commander_mad": 500},
        {"reference": "A", "fournisseur": "F", "montant_a_commander_mad": 100},
    ]
    assert c17.gravite == "information" and c17.lien == "/catalogue?onglet=matieres"
    lignes[0].statut = lignes[1].statut = STATUTS["OK"]
    _conforme("C17", D(), lignes)


def test_c18_stock_dormant():
    lignes = [
        LigneStock("A", stock_net=40, stock_projete=90, jours_sans_mouvement=200, dormant=True),
        LigneStock("B", stock_net=10),
    ]
    c18 = _sonne("C18", D(), 1, lignes)
    assert c18.detail == [{"reference": "A", "stock": 40, "jours_sans_mouvement": 200}]
    assert c18.libelle == "Stock dormant depuis plus de 180 jours"
    assert c18.gravite == "information" and c18.lien == "/stock"
    autre_seuil = D(parametres=Parametres(seuil_dormant=90.4))
    assert _controle("C18", autre_seuil, lignes).libelle == "Stock dormant depuis plus de 90 jours"
    lignes[0].dormant = False
    _conforme("C18", D(), lignes)


def test_c19_fournisseur_qui_facture_en_plusieurs_devises():
    articles = [
        Article("A", fournisseur="F", devise="USD"),
        Article("B", fournisseur="F", devise="EUR"),
        Article("C", fournisseur="F", devise="EUR"),
        Article("D", fournisseur="F", devise="MAD", actif=False),
        Article("E", fournisseur="G", devise="USD"),
    ]
    donnees = D(articles=articles, fournisseurs=[Fournisseur("F", devise="USD")])
    c19 = _sonne("C19", donnees, 1)
    assert c19.detail == [
        {
            "fournisseur": "F",
            "devises": "EUR (2 matière(s)) · USD (1 matière(s))",
            "devise_par_defaut": "USD",
        }
    ]
    assert c19.gravite == "information" and c19.lien == "/catalogue?onglet=fournisseurs"
    articles[1].devise = articles[2].devise = "USD"
    _conforme("C19", donnees)


def test_c20_stock_negatif_sans_consommation():
    lignes = [
        LigneStock("A", stock_net=-5),
        LigneStock("B", stock_net=-5, conso_mensuelle=10),
        LigneStock("C", stock_net=-1e-7),
    ]
    c20 = _sonne("C20", D(), 1, lignes)
    assert c20.detail == [{"reference": "A", "stock_net": -5}]
    assert c20.gravite == "bloquant" and c20.lien == "/inventaire"
    lignes[0].stock_net = 0
    _conforme("C20", D(), lignes)


def test_c21_prix_sans_devise():
    donnees = D(
        articles=[Article("A", prix_unite=5, devise="", fournisseur="F"), Article("B", devise="")]
    )
    c21 = _sonne("C21", donnees, 1)
    assert c21.detail == [{"reference": "A", "prix": 5, "fournisseur": "F"}]
    assert c21.gravite == "bloquant" and c21.lien == "/catalogue?onglet=matieres"
    donnees.articles[0].devise = "MAD"
    assert "clé étrangère" in _conforme("C21", donnees).garanti


def test_c22_etage_plus_large_que_la_laize():
    fils = [
        FilMonte("A", etage=1, metres=3),
        FilMonte("B", etage=1, metres=2),
        FilMonte("C", etage=2, metres=3, pourcentage=60),
        FilMonte("D", etage=2, metres=3, pourcentage=40),
    ]
    arrete = Metier("M2", laize=1, actif=False, fils=[FilMonte("A", metres=9)])
    donnees = D(metiers=[Metier("M1", laize=4, fils=fils), arrete])
    c22 = _sonne("C22", donnees, 1)
    assert c22.detail == [{"metier": "M1", "etage": 1, "laize": 4, "metres_montes": 5.0, "fils": 2}]
    assert c22.gravite == "avertissement" and c22.lien == "/metiers"
    assert next(c.libelle for c in c22.colonnes if c.cle == "fils") == "Matières"
    fils[1].metres = 1
    _conforme("C22", donnees)


def test_c23_fil_monte_sans_poids_de_bobine():
    fils = [FilMonte("A", metres=1.5), FilMonte("B", etage=2, metres=1)]
    donnees = D(
        articles=[Article("A"), Article("B", poids_bobine=2)],
        metiers=[Metier("M1", laize=4, densite=100, fils=fils)],
    )
    c23 = _sonne("C23", donnees, 1)
    assert c23.detail == [{"metier": "M1", "etage": 1, "reference": "A", "metres": 1.5}]
    assert c23.gravite == "avertissement" and c23.lien == "/catalogue?onglet=matieres"
    fils[0].poids_bobine = 2.5
    _conforme("C23", donnees)


def test_c24_fil_monte_a_un_etage_inexistant():
    metier = Metier("M1", etages=2, fils=[FilMonte("A", etage=3), FilMonte("B", etage=2)])
    donnees = D(metiers=[metier])
    c24 = _sonne("C24", donnees, 1)
    assert c24.detail == [{"metier": "M1", "etage": 3, "etages": 2, "reference": "A"}]
    assert c24.gravite == "avertissement" and c24.lien == "/metiers"
    metier.etages = 3
    assert "étage" in _conforme("C24", donnees).garanti


def test_c25_fil_monte_plus_lourd_que_le_sorti_net():
    metier = Metier("M1", laize=4, densite=100, fils=[FilMonte("A", metres=1, poids_bobine=2)])
    journal = [
        Mouvement(VEILLE, "SORTIE_PROD", "A", 150, numero_of="OF-1", utilisateur="u"),
        Mouvement(VEILLE, "RETOUR_PRODUCTION", "A", 20, motif_retour="R1", utilisateur="u"),
    ]
    donnees = D(articles=[Article("A")], metiers=[metier], mouvements=journal)
    c25 = _sonne("C25", donnees, 1)
    assert c25.detail == [
        {
            "metier": "M1",
            "etage": 1,
            "reference": "A",
            "poids": 200.0,
            "monte": 200.0,
            "sorties": 130.0,
        }
    ]
    assert c25.gravite == "avertissement" and c25.lien == "/sorties"
    # Le sorti net se lit sur toutes les données (une sortie datée après la date comprise).
    apres = Mouvement(JOUR, "SORTIE_PROD", "A", 100, numero_of="OF-2", utilisateur="u")
    _conforme("C25", donnees, complet=D(mouvements=[*journal, apres]))
