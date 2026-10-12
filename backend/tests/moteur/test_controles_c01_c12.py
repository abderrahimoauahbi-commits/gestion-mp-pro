"""Contrôles C01 à C12 : chacun sonne sur une donnée fautive, avec le nombre exact d'anomalies,
et se tait une fois la donnée corrigée (PLAN-DE-RECETTE-PRO § 4)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from gestion_mp_pro.calcul.controles import Controle, controler
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    DossierImport,
    FactureImport,
    Fournisseur,
    LigneCommande,
    LigneReception,
    LigneRecette,
    Mouvement,
    Parametres,
    Qualite,
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


def test_c01_recette_dont_un_role_ne_fait_pas_cent():
    donnees = D(
        articles=[Article("A", role_bom="Poil"), Article("B", role_bom="Chaîne")],
        qualites=[Qualite("Q", poids={"Poil": 1.0, "Chaîne": 0.5, "Trame": 0.0})],
        recettes=[LigneRecette("Q", "A", 60), LigneRecette("Q", "B", 100)],
    )
    c01 = _sonne("C01", donnees, 1)
    assert c01.detail == [{"qualite": "Q", "roles": "Poil (60 %)"}]
    assert c01.gravite == "bloquant" and c01.lien == "/qualites"
    assert "Qualités et recettes" in c01.quoi_faire
    donnees.recettes[0].pourcentage = 100
    _conforme("C01", donnees)


def test_c02_sortie_sans_ordre():
    mouvements = [
        Mouvement(VEILLE, "SORTIE_PROD", "A", 5, utilisateur="u"),
        Mouvement(JOUR, "SORTIE_PROD", "B", 5, utilisateur="u"),
        Mouvement(JOUR, "SORTIE_PROD", "C", 5, utilisateur="u", numero_of="OF-1"),
    ]
    donnees = D(mouvements=mouvements)
    c02 = _sonne("C02", donnees, 2)
    assert c02.detail[0] == {"date": "2026-10-07", "reference": "A"}
    assert c02.gravite == "avertissement" and c02.lien == "/sorties"
    assert "administrateur technique" in c02.quoi_faire
    for m in mouvements:
        m.numero_of = "OF-1"
    assert "garanti par la saisie" in _conforme("C02", donnees).garanti


def test_c03_retour_avec_le_motif_d_une_autre_famille():
    retour = Mouvement(VEILLE, "RETOUR_PRODUCTION", "A", 5, motif_retour="R3", utilisateur="u")
    donnees = D(mouvements=[retour])
    c03 = _sonne("C03", donnees, 1)
    assert c03.detail == [
        {"date": "2026-10-07", "reference": "A", "type": "🔄 Retour Production", "motif": "R3"}
    ]
    assert c03.gravite == "avertissement" and c03.lien == "/operations?onglet=retour_machine"
    retour.motif_retour = "R1"
    assert _conforme("C03", donnees).garanti == ""


def test_c04_mouvement_sans_auteur():
    mouvement = Mouvement(VEILLE, "STOCK_INITIAL", "A", 5)
    donnees = D(mouvements=[mouvement, Mouvement(VEILLE, "STOCK_INITIAL", "B", 5, utilisateur="u")])
    c04 = _sonne("C04", donnees, 1)
    assert c04.detail == [{"date": "2026-10-07", "reference": "A"}]
    assert c04.gravite == "avertissement" and c04.lien == "/stock?onglet=mouvements"
    mouvement.utilisateur = "u"
    assert _conforme("C04", donnees).garanti


def test_c05_matiere_sans_fournisseur():
    donnees = D(articles=[Article("A"), Article("B", fournisseur="F")])
    c05 = _sonne("C05", donnees, 1)
    assert c05.detail == [{"reference": "A"}]
    assert c05.gravite == "bloquant" and c05.lien == "/catalogue?onglet=matieres"
    donnees.articles[0].fournisseur = "F"
    _conforme("C05", donnees)


def _bon(numero: str, statut: str = "Envoyée", **autres) -> Commande:
    ligne = LigneCommande(numero, "A", quantite_commandee=10)
    return Commande(numero, fournisseur="F", statut=statut, lignes=[ligne], **autres)


def test_c06_commande_en_retard_triee_par_echeance():
    bons = [
        _bon("BC-1", date_bc=JOUR - timedelta(days=45)),
        _bon("BC-2", date_bc=JOUR - timedelta(days=10), eta=date(2026, 9, 1)),
        _bon("BC-3", statut="Brouillon", date_bc=JOUR - timedelta(days=90)),
        _bon("BC-4", date_bc=JOUR - timedelta(days=20)),
    ]
    donnees = D(fournisseurs=[Fournisseur("F", delai_jours=30)], commandes=bons)
    c06 = _sonne("C06", donnees, 2)
    assert [x["numero"] for x in c06.detail] == ["BC-2", "BC-1"]
    assert c06.detail[1] == {
        "numero": "BC-1",
        "fournisseur": "F",
        "date_bc": "2026-08-24",
        "jours_commande": 45,
        "echeance": "2026-09-23",
        "retard_jours": 15,
    }
    assert c06.gravite == "avertissement" and c06.lien == "/commandes?filtre=retard"
    for bon in bons:
        bon.lignes[0].quantite_recue = 10
    _conforme("C06", donnees)


def test_c06_retard_tolere():
    donnees = D(
        parametres=Parametres(toler_retard_jours=20),
        fournisseurs=[Fournisseur("F", delai_jours=30)],
        commandes=[_bon("BC-1", date_bc=JOUR - timedelta(days=45))],
    )
    _conforme("C06", donnees)


def test_c07_matiere_jamais_utilisee():
    donnees = D(
        articles=[Article("A", fournisseur="F"), Article("B"), Article("C", actif=False)],
        recettes=[LigneRecette("Q", "B", 100)],
    )
    c07 = _sonne("C07", donnees, 1)
    assert c07.detail == [{"reference": "A"}]
    assert c07.gravite == "information" and c07.lien == "/catalogue?onglet=matieres"
    donnees.mouvements.append(Mouvement(VEILLE, "STOCK_INITIAL", "A", 1, utilisateur="u"))
    _conforme("C07", donnees)


def test_c08_ecart_de_pesee():
    fautive = LigneReception("A", quantite_bl=100, quantite_pesee=95)
    receptions = [
        Reception(
            "R-1",
            statut="Validée",
            lignes=[fautive, LigneReception("B", quantite_bl=100, quantite_pesee=99)],
        ),
        Reception("R-2", lignes=[LigneReception("C", quantite_bl=100)]),
    ]
    donnees = D(receptions=receptions)
    c08 = _sonne("C08", donnees, 1)
    assert c08.detail == [
        {"reception": "R-1", "reference": "A", "attendu": 100, "pesee": 95, "ecart": -0.05}
    ]
    assert c08.libelle == "Écart de pesée supérieur à 2 %"
    assert c08.gravite == "avertissement" and c08.lien == "/receptions?onglet=pesees"
    fautive.quantite_pesee = 99
    _conforme("C08", donnees)


def test_c09_prix_negatif():
    donnees = D(articles=[Article("A", prix_unite=-1, fournisseur="F")])
    c09 = _sonne("C09", donnees, 1)
    assert c09.detail == [{"reference": "A", "prix": -1}]
    assert c09.gravite == "bloquant" and c09.lien == "/catalogue?onglet=matieres"
    donnees.articles[0].prix_unite = 1
    assert "article_prix_check" in _conforme("C09", donnees).garanti


def test_c10_delai_fournisseur_nul():
    donnees = D(fournisseurs=[Fournisseur("F", delai_jours=0), Fournisseur("G", delai_jours=5)])
    c10 = _sonne("C10", donnees, 1)
    assert c10.detail == [{"fournisseur": "F", "delai": 0}]
    assert c10.gravite == "bloquant" and c10.lien == "/catalogue?onglet=fournisseurs"
    donnees.fournisseurs[0].delai_jours = 30
    assert "délai" in _conforme("C10", donnees).garanti


def test_c11_devises_employees_sans_cours():
    cours = {"MAD": 1.0, "USD": 10.0, "EUR": 0.0}
    commande = Commande("BC-1", lignes=[LigneCommande("BC-1", "A", devise="GBP")])
    dossier = DossierImport("D1", factures=[FactureImport("F-1", devise="EUR")])
    donnees = D(
        parametres=Parametres(cours=cours),
        articles=[Article("A", devise="CNY"), Article("B", devise="JPY", actif=False)],
        commandes=[commande],
        dossiers_import=[dossier],
    )
    c11 = _sonne("C11", donnees, 3)
    assert [x["taux"] for x in c11.detail] == ["CNY", "EUR", "GBP"]
    assert c11.detail[0] == {"taux": "CNY", "valeur": 0.0, "type": "employée par : matière A"}
    assert c11.detail[1]["type"] == "employée par : dossier D1"
    assert c11.gravite == "bloquant" and c11.lien == "/reglages?onglet=devises"
    cours.update(CNY=1.4, EUR=10.8, GBP=12.5)
    assert "devise_taux_check" in _conforme("C11", donnees).garanti


def test_c11_sans_table_des_devises_les_deux_taux():
    donnees = D(parametres=Parametres(taux_eur_mad=0, taux_usd_mad=9.5))
    c11 = _sonne("C11", donnees, 1)
    assert c11.detail == [{"taux": "EUR → MAD", "valeur": 0}]


def test_c12_soldes_tenus_differents_du_journal():
    journal = [
        Mouvement(VEILLE, "STOCK_INITIAL", "A", 90, lot_fournisseur="L1", magasin_destination="M"),
        Mouvement(
            JOUR,
            "TRANSFERT_MAGASIN",
            "A",
            30,
            lot_fournisseur="L1",
            magasin_source="M",
            magasin_destination="M2",
        ),
    ]
    soldes = {("A", "L1", "M"): 70.0, ("A", "L1", "M2"): 30.0}
    complet = D(mouvements=journal, soldes=soldes)
    c12 = _sonne("C12", D(), 1, complet=complet)
    assert c12.detail == [
        {"reference": "A", "lot": "L1", "magasin": "M", "stock": 70.0, "attendu": 60.0}
    ]
    assert c12.libelle == "Stock tenu (soldes des lots) différent du journal des mouvements"
    assert c12.gravite == "bloquant" and c12.lien == "/stock?onglet=mouvements"
    assert "administrateur technique" in c12.quoi_faire
    soldes[("A", "L1", "M")] = 60.0
    _conforme("C12", D(), complet=complet)


def test_c12_sans_soldes_la_somme_des_magasins():
    lignes = [LigneStock("A", stock_net=10, par_magasin={"M": 8}), LigneStock("B", stock_net=1)]
    c12 = _sonne("C12", D(), 2, lignes)
    assert c12.detail[0] == {"reference": "A", "somme_magasins": 8, "stock_net": 10}
    assert c12.libelle == "Stock par magasin différent du stock net des mouvements"
    lignes = [LigneStock("A", stock_net=10, par_magasin={"M": 9.995})]
    _conforme("C12", D(), lignes)
