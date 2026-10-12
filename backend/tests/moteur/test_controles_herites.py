"""Les essais de Gestion MP qui portent sur les contrôles, portés sur le moteur PRO avec leurs
valeurs. Chacun dit d'où il vient (« Hérité : fichier::essai ») ; la date du jour de Gestion MP
(`date.today()`) devient le jour des essais, le 8 octobre 2026."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from gestion_mp_pro.calcul import controles
from gestion_mp_pro.calcul.constantes import STATUTS
from gestion_mp_pro.calcul.controles import Controle, controler, synthese
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    Commande,
    Donnees,
    DossierImport,
    FactureImport,
    FilMonte,
    Fournisseur,
    LigneCommande,
    LigneImport,
    LigneRecette,
    Metier,
    Mouvement,
    Parametres,
    PlanQualite,
    Qualite,
)
from gestion_mp_pro.calcul.stock import LigneStock

AUJOURDHUI = date(2026, 10, 8)


def _controle(
    code: str, donnees: Donnees, lignes: Sequence[LigneStock] = (), jour: date = AUJOURDHUI
) -> Controle:
    return next(x for x in controler(donnees, list(lignes), jour) if x.code == code)


def test_c03_verifie_la_famille_du_motif():
    """Hérité : test_audit2_pilotage.py::test_C03_verifie_la_famille_du_motif.

    Un retour des machines marqué R3 (motif d'un retour au fournisseur) sonne."""
    jour = date(2026, 9, 1)
    donnees = Donnees(
        articles=[Article(reference="F")],
        mouvements=[
            Mouvement(jour, "RETOUR_PRODUCTION", "F", 5, motif_retour="R1", utilisateur="x"),
            Mouvement(jour, "RETOUR_PRODUCTION", "F", 5, motif_retour="R3", utilisateur="x"),
            Mouvement(jour, "RETOUR_FOURNISSEUR", "F", -5, motif_retour="R5", utilisateur="x"),
            Mouvement(jour, "RETOUR_FOURNISSEUR", "F", -5, motif_retour="R2", utilisateur="x"),
            Mouvement(jour, "RETOUR_FOURNISSEUR", "F", -5, utilisateur="x"),
        ],
    )
    c03 = _controle("C03", donnees, jour=jour)
    assert c03.anomalies == 3
    assert sorted(str(x["motif"]) for x in c03.detail) == ["R2", "R3", "—"]


def test_matiere_inactive_hors_c05_c07_c13_c19():
    """Hérité : test_defauts_e.py::test_matiere_inactive_hors_C05_C07_C13_C19."""
    articles = [
        Article("ACTIVE", fournisseur="", devise="USD"),
        Article("ARRETEE", fournisseur="", actif=False),
        Article("F1 USD", fournisseur="F", devise="USD"),
        Article("F1 EUR", fournisseur="F", devise="EUR", actif=False),
    ]
    donnees = Donnees(articles=articles)
    assert [x["reference"] for x in _controle("C05", donnees).detail] == ["ACTIVE"]
    assert {x["reference"] for x in _controle("C07", donnees).detail} == {"ACTIVE", "F1 USD"}
    assert _controle("C19", donnees).anomalies == 0
    lignes = [
        LigneStock("ARRETEE", stock_projete=-5, sans_achat="matière désactivée"),
        LigneStock("ACTIVE", stock_projete=-5),
    ]
    assert [x["reference"] for x in _controle("C13", donnees, lignes).detail] == ["ACTIVE"]


def test_c15_signale_une_matiere_desactivee_dans_une_recette():
    """Hérité : test_defauts_e.py::test_C15_signale_une_matiere_desactivee_dans_une_recette."""
    donnees = Donnees(
        articles=[Article("ARRETEE", prix_unite=5, actif=False)],
        recettes=[LigneRecette("Q", "ARRETEE", 100)],
    )
    c15 = _controle("C15", donnees)
    assert c15.anomalies == 1 and "désactivée" in str(c15.detail[0]["motif"])


def test_retard_meme_verdict_c06():
    """Hérité : test_defauts_e.py::test_retard_meme_verdict_ecran_courriel_c06 (partie moteur ;
    l'écran et le courriel relèvent des services)."""
    jour = AUJOURDHUI
    commande = Commande(
        "BC-1",
        date_bc=jour - timedelta(days=45),
        fournisseur="F",
        statut="Envoyée",
        lignes=[LigneCommande("BC-1", "A", quantite_commandee=10)],
    )
    donnees = Donnees(
        articles=[Article("A", fournisseur="F")],
        commandes=[commande],
        fournisseurs=[Fournisseur("F", delai_jours=30)],
    )
    c06 = _controle("C06", donnees, jour=jour)
    assert c06.anomalies == 1 and c06.detail[0]["retard_jours"] == 15
    # À vingt jours, pas de retard.
    commande.date_bc = jour - timedelta(days=20)
    assert _controle("C06", donnees, jour=jour).anomalies == 0


def test_synthese_ne_compte_pas_les_garantis_de_saisie():
    """Hérité : test_defauts_e.py::test_synthese_ne_compte_pas_les_garantis_de_saisie."""
    resultats = controler(Donnees(), [], AUJOURDHUI)
    garantis = {x.code for x in resultats if x.garanti}
    assert {"C02", "C04", "C14", "C24", "C26", "C31", "C32"} <= garantis
    s = synthese(resultats)
    assert s.total == len(resultats) - len(garantis)
    assert next(x for x in resultats if x.code == "C10").gravite == "bloquant"


def test_pastille_ignore_information():
    """Hérité : test_defauts_e.py::test_pastille_ignore_information."""
    donnees = Donnees(articles=[Article("JAMAIS", fournisseur="F")])  # C07 : information
    resultats = controler(donnees, [], AUJOURDHUI)
    s = synthese(resultats)
    assert s.anomalies >= 1 and s.a_corriger == s.anomalies - sum(
        1 for x in resultats if not x.conforme and x.gravite == "information"
    )
    assert s.a_corriger < s.anomalies


def test_c20_ignore_un_reste_de_calcul():
    """Hérité : test_defauts_e.py::test_C20_ignore_un_reste_de_calcul."""
    lignes = [LigneStock("A", stock_net=-1e-7)]
    assert _controle("C20", Donnees(articles=[Article("A")]), lignes).anomalies == 0


def test_colonnes_controles_toutes_libellees():
    """Hérité : test_defauts_e.py::test_colonnes_controles_toutes_libellees (partie sans base ;
    les clés de chaque détail sont vérifiées contre les colonnes déclarées par les essais
    C01 à C38)."""
    assert "devise" in controles.COLONNES and "unite" not in controles.COLONNES
    assert controles.__doc__ is not None and "Six contrôles du classeur" in controles.__doc__


def test_libelles_pourcent_avec_espace_et_c29_dit_la_tolerance():
    """Hérité : test_defauts_e.py::test_libelles_pourcent_avec_espace_et_C29_dit_la_tolerance."""
    resultats = {x.code: x for x in controler(Donnees(), [], AUJOURDHUI)}
    assert resultats["C08"].libelle.endswith("2 %")
    assert resultats["C30"].libelle.endswith("5 %")
    assert "5 % de la TVA attendue" in resultats["C29"].libelle
    assert "hors TVA" in resultats["C28"].libelle
    assert "ni pesé au lot" in resultats["C23"].libelle
    assert resultats["C23"].gravite == "avertissement"


def test_c34_tva_a_part():
    """Hérité : test_defauts_e.py::test_C34_tva_a_part."""
    dossier = DossierImport("D1", charges=[ChargeImport("DD", 100), ChargeImport("TVA", 50)])
    detail = _controle("C34", Donnees(dossiers_import=[dossier])).detail
    assert detail == [{"dossier": "D1", "frais": 100, "tva": 50}]


def test_c11_devise_sans_cours():
    """Hérité : test_defauts_e.py::test_C11_devise_sans_cours."""
    p = Parametres(cours={"MAD": 1.0, "USD": 10.0})
    donnees = Donnees(parametres=p, articles=[Article("A", devise="CNY", prix_unite=3)])
    c11 = _controle("C11", donnees)
    assert c11.anomalies == 1 and c11.detail[0]["taux"] == "CNY"


def test_c25_sortie_annulee_ne_suffit_pas():
    """Hérité : test_defauts_e.py::test_C25_sortie_annulee_ne_suffit_pas."""
    jour = AUJOURDHUI
    fil = FilMonte("A", etage=1, metres=1, poids_bobine=2)
    metier = Metier("M1", laize=4, densite=100, fils=[fil])
    mouvements = [
        Mouvement(jour, "SORTIE_PROD", "A", 300, utilisateur="x", numero_of="OF-1"),
        Mouvement(jour, "SORTIE_PROD", "A", -300, utilisateur="x", numero_of="OF-1"),
    ]
    donnees = Donnees(articles=[Article("A")], metiers=[metier], mouvements=mouvements)
    assert _controle("C25", donnees).anomalies == 1
    donnees.mouvements.append(
        Mouvement(jour, "SORTIE_PROD", "A", 250, utilisateur="x", numero_of="OF-2")
    )
    assert _controle("C25", donnees).anomalies == 0


def test_c24_ne_regarde_que_les_metiers_actifs():
    """Hérité : test_defauts_e.py::test_C24_ne_regarde_que_les_metiers_actifs."""
    metier = Metier("M1", etages=2, actif=False, fils=[FilMonte("A", etage=5)])
    assert _controle("C24", Donnees(metiers=[metier])).anomalies == 0


def test_c17_matiere_sans_groupe_mono_source():
    """Hérité : test_defauts_e.py::test_C17_matiere_sans_groupe_mono_source."""
    lignes = [
        LigneStock("A", statut=STATUTS["RUPTURE"], groupe_equiv="", sourcing="❓ Hors catalogue")
    ]
    assert _controle("C17", Donnees(articles=[Article("A")]), lignes).anomalies == 1


def test_dossier_facture_sans_montant_signale():
    """Hérité : test_defauts_e.py::test_dossier_facture_sans_montant_signale."""
    dossier = DossierImport(
        "D2",
        factures=[FactureImport("FAC-9", 0, "MAD", [1])],
        lignes=[LigneImport(1, "A", quantite=10, valeur_devise=20)],
    )
    c36 = _controle("C36", Donnees(dossiers_import=[dossier]))
    assert c36.anomalies == 1 and "non saisi" in str(c36.detail[0]["motif"])


def test_c33_ne_liste_que_ce_que_le_calcul_plafonne():
    """Hérité : test_audit2_achat.py::test_c33_ne_liste_que_ce_que_le_calcul_plafonne.

    Demande `etat_stock` (lot S3, coordinateur) : importé dans l'essai, pour que le reste du
    fichier tourne sans lui."""
    from gestion_mp_pro.calcul.stock import etat_stock

    jour = date(2026, 10, 8)
    d = Donnees(
        parametres=Parametres(
            taux_perte=0.0, fenetre_realisation_jours=90, plafond_stock_min_mois=3
        ),
        fournisseurs=[Fournisseur(nom="F", delai_jours=30, couverture_commande_jours=30)],
        articles=[
            Article(
                reference="FIL A", role_bom="Poil", fournisseur="F", prix_unite=1, stock_min=20_000
            )
        ],
        qualites=[Qualite(code="Q", poids={"Poil": 1.0})],
        recettes=[LigneRecette("Q", "FIL A", 100)],
        plan=[PlanQualite("Q", base_mensuelle=1000, saisonnalite=[1.0] * 12)],
        mouvements=[
            Mouvement(date(2026, 6, 1), "STOCK_INITIAL", r, 100) for r in ("FIL A", "FIL B")
        ],
    )
    lignes = etat_stock(d, jour)
    a = lignes[0]
    assert a.stock_min_plafonne < a.stock_min
    c33 = _controle("C33", d, lignes, jour)
    assert [x["reference"] for x in c33.detail] == ["FIL A"]
    assert c33.detail[0]["retenu"] == round(a.stock_min_plafonne)
