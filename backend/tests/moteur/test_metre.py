"""Le cuir, les franges et le ruban : stock en kilos, prix au kilo ou au mètre (décision de
Mohamed, 8 octobre 2026). Le prix au mètre se lit au kilo (÷ densité) ; la recette d'un rôle
au mètre dit des mètres par m², que la densité change en kilos.

Une qualité de 1 000 m² par mois : 1 ml de cuir et 0,6 ml de bande par m², 2 kg de poil. Le
cuir est facturé au mètre (0,5 MAD le mètre, 0,014 kg/ml : 35,71 MAD le kilo), la bande au
mètre aussi (2,5 USD le mètre, 0,005 kg/ml : 500 USD le kilo).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

import pytest

from gestion_mp_pro.calcul.besoins import besoins_mensuels
from gestion_mp_pro.calcul.importations import revient_dossier
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    Donnees,
    DossierImport,
    Fournisseur,
    LigneImport,
    LigneRecette,
    Mouvement,
    OrdreFabrication,
    Parametres,
    PlanQualite,
    Qualite,
)
from gestion_mp_pro.calcul.nomenclature import kg_par_m2, nomenclature
from gestion_mp_pro.calcul.plan_achat import plan_achat
from gestion_mp_pro.calcul.production import consommation_par_of
from gestion_mp_pro.calcul.stock import etat_stock
from gestion_mp_pro.calcul.valorisation import cmup_glissant, valorisation

JOUR = date(2026, 10, 15)
CUIR = Article(
    reference="CUIR NOIR",
    role_bom="Cuir",
    densite=0.014,
    prix_unite=0.5,
    unite_prix="ml",
    devise="MAD",
    fournisseur="TANNERIE",
)
BANDE = Article(
    reference="BANDE 30",
    role_bom="Ruban",
    densite=0.005,
    prix_unite=2.5,
    unite_prix="ml",
    devise="USD",
    fournisseur="RUBANS",
)
POIL = Article(
    reference="POIL BLEU", role_bom="Poil", prix_unite=20.0, devise="MAD", fournisseur="FILATURE"
)
# Le même cuir, son prix saisi au kilo.
CUIR_KG = Article(
    reference="CUIR AU KILO",
    role_bom="Cuir",
    densite=0.014,
    prix_unite=0.5 / 0.014,
    devise="MAD",
    fournisseur="TANNERIE",
)


def donnees(*, mouvements: Sequence[Mouvement] = (), cuir: Article = CUIR) -> Donnees:
    """La qualité 8S au cuir, à la bande et au poil."""
    return Donnees(
        parametres=Parametres(),
        fournisseurs=[
            Fournisseur(nom=n, delai_jours=30) for n in ("TANNERIE", "RUBANS", "FILATURE")
        ],
        articles=[cuir, BANDE, POIL],
        qualites=[Qualite(code="8S", poids={"Cuir": 1.0, "Ruban": 0.6, "Poil": 2.0})],
        recettes=[
            LigneRecette("8S", cuir.reference, 100),
            LigneRecette("8S", "BANDE 30", 100),
            LigneRecette("8S", "POIL BLEU", 100),
        ],
        plan=[PlanQualite("8S", base_mensuelle=1000)],
        mouvements=list(mouvements),
    )


def test_le_prix_au_metre_se_ramene_au_kilo() -> None:
    """Hérité : test_matieres_au_metre::test_le_prix_au_metre_se_ramene_au_kilo."""
    assert CUIR.prix_kg == pytest.approx(0.5 / 0.014)
    assert BANDE.prix_kg == pytest.approx(500)
    assert CUIR_KG.prix_kg == pytest.approx(0.5 / 0.014)  # saisi au kilo : tel quel
    assert POIL.prix_kg == 20.0
    # Un prix au mètre sans densité ne se ramène pas : 0, que le contrôle C15 signale.
    assert Article(reference="X", unite_prix="ml", prix_unite=3.0).prix_kg == 0.0
    # Les mètres indicatifs : la densité d'un rôle au mètre, rien pour un rôle au poids.
    assert CUIR.kg_par_ml == 0.014 and POIL.kg_par_ml == 0.0
    assert Article(reference="F", role_bom="Franges", densite=0.02).kg_par_ml == 0.02


def test_le_besoin_d_un_cuir_est_en_kilos() -> None:
    """Hérité : test_matieres_au_metre::test_le_besoin_d_un_cuir_est_en_kilos.

    1 ml/m² d'un cuir de 0,014 kg/ml : 0,014 kg/m², × la perte."""
    d = donnees()
    perte = 1 + d.parametres.taux_perte
    assert kg_par_m2(d, "8S", "CUIR NOIR", 100) == pytest.approx(0.014)
    besoins = besoins_mensuels(d, JOUR)
    assert besoins["CUIR NOIR"][0] == pytest.approx(1000 * 0.014 * perte)
    assert besoins["BANDE 30"][0] == pytest.approx(1000 * 0.6 * 0.005 * perte)
    assert besoins["POIL BLEU"][0] == pytest.approx(2000 * perte)
    # Prix au kilo ou au mètre : le besoin est le même.
    au_kilo = besoins_mensuels(donnees(cuir=CUIR_KG), JOUR)
    assert au_kilo["CUIR AU KILO"][0] == pytest.approx(besoins["CUIR NOIR"][0])


def test_la_recette_dit_ses_metres_et_ses_kilos_et_le_cout_au_m2() -> None:
    """Hérité :
    test_matieres_au_metre::test_la_recette_dit_ses_metres_et_ses_kilos_et_le_cout_au_m2.
    """
    lignes = {x.reference: x for x in nomenclature(donnees())}
    perte = 1 + Parametres().taux_perte
    cuir = lignes["CUIR NOIR"]
    assert cuir.ml_m2 == pytest.approx(1.0) and cuir.kg_m2 == pytest.approx(0.014)
    assert (cuir.prix, cuir.unite_prix) == (0.5, "ml")
    assert cuir.prix_kg == pytest.approx(0.5 / 0.014)
    # kg/m² × prix au kilo = ml/m² × prix au mètre.
    assert cuir.cout_m2_mad == pytest.approx(1.0 * 0.5 * perte)
    bande = lignes["BANDE 30"]
    assert bande.ml_m2 == pytest.approx(0.6)
    assert bande.cout_m2_mad == pytest.approx(0.6 * 2.5 * 9.5 * perte)
    assert lignes["POIL BLEU"].ml_m2 == 0.0
    au_kilo = {x.reference: x for x in nomenclature(donnees(cuir=CUIR_KG))}["CUIR AU KILO"]
    assert au_kilo.cout_m2_mad == pytest.approx(cuir.cout_m2_mad)


def test_un_cuir_se_saisit_en_metres_dans_la_recette() -> None:
    """Hérité (partie calcul) :
    test_referentiels_complets::test_un_cuir_se_saisit_en_metres_dans_la_recette.

    3 MAD le mètre, densité 0,05 kg/ml : 60 MAD le kilo ; 2 ml/m² saisis, 0,1 kg/m²."""
    cuir = Article(
        reference="REF CUIR",
        role_bom="Cuir",
        prix_unite=3.0,
        devise="MAD",
        unite_prix="ml",
        densite=0.05,
    )
    d = Donnees(
        articles=[cuir],
        qualites=[Qualite(code="QML", poids={"Cuir": 2})],
        recettes=[LigneRecette("QML", "REF CUIR", 100)],
    )
    (ligne,) = nomenclature(d)
    assert (ligne.prix, ligne.unite_prix) == (3.0, "ml") and ligne.prix_kg == pytest.approx(60)
    assert ligne.ml_m2 == pytest.approx(2) and ligne.kg_m2 == pytest.approx(0.1)
    assert ligne.cout_m2_mad == pytest.approx(2 * 3.0 * 1.02)


def _entree(
    reference: str, quantite: float, prix: float, devise: str = "MAD", lot: str = "L1"
) -> Mouvement:
    return Mouvement(
        date=JOUR - timedelta(days=40),
        type="ENTREE_RECEPTION",
        reference=reference,
        quantite=quantite,
        prix_unite=prix,
        devise=devise,
        lot_fournisseur=lot,
        magasin_destination="MP",
    )


def test_stock_valeur_et_cmup_en_kilos() -> None:
    """Hérité : test_matieres_au_metre::test_stock_valeur_et_cmup_en_kilos."""
    d = donnees(
        mouvements=[
            _entree("CUIR NOIR", 28, 30.0, lot="C1"),
            _entree("CUIR NOIR", 14, 45.0, lot="C2"),
            _entree("BANDE 30", 2.5, 500.0, devise="USD"),
            Mouvement(
                date=JOUR - timedelta(days=10),
                type="SORTIE_PROD",
                reference="CUIR NOIR",
                quantite=8.4,
                lot_fournisseur="C1",
                magasin_source="MP",
                numero_of="OF-1",
            ),
        ]
    )
    lignes = {x.reference: x for x in etat_stock(d, JOUR)}
    cuir = lignes["CUIR NOIR"]
    assert cuir.stock_net == pytest.approx(33.6) and cuir.kg_par_ml == 0.014
    # Le prix est au kilo (le mètre ramené par la densité) : la valeur consommée aussi.
    assert cuir.prix_kg == pytest.approx(0.5 / 0.014)
    assert cuir.prix_unite == 0.5 and cuir.unite_achat == "ml"
    assert cuir.valeur_conso_annuelle == pytest.approx(cuir.conso_mensuelle * 12 * 0.5 / 0.014)
    # CMUP : (28 × 30 + 14 × 45) / 42 = 35 MAD le kilo ; la sortie ne le déplace pas.
    cmup = cmup_glissant(d)
    assert cmup["CUIR NOIR"] == pytest.approx(35.0)
    assert cmup["BANDE 30"] == pytest.approx(500 * 9.5)
    valeurs = {x.reference: x for x in valorisation(d, list(lignes.values()))}
    assert valeurs["CUIR NOIR"].valeur_mad == pytest.approx(33.6 * 35.0)
    assert valeurs["CUIR NOIR"].prix_catalogue == pytest.approx(0.5 / 0.014)
    assert valeurs["CUIR NOIR"].ecart_mad == pytest.approx(33.6 * (35.0 - 0.5 / 0.014))
    assert valeurs["BANDE 30"].valeur_mad == pytest.approx(2.5 * 500 * 9.5)


def test_plan_d_achat_en_kilos_et_au_metre_pour_le_fournisseur() -> None:
    """Hérité :
    test_matieres_au_metre::test_plan_d_achat_en_kilos_et_au_metre_pour_le_fournisseur.
    """
    d = donnees()
    plan = plan_achat(d, etat_stock(d, JOUR))
    bande = next(x for x in plan.lignes if x.reference == "BANDE 30")
    # Une bande sans stock se commande en kilos ; le fournisseur, qui facture au mètre, lit
    # les mètres (kilos ÷ densité) — et le montant est le même dans les deux lectures.
    assert bande.quantite > 3 and bande.unite_commande == "kg"
    assert bande.unite_achat == "ml"
    assert bande.quantite_achat == pytest.approx(bande.quantite / 0.005)
    assert bande.montant_devise == pytest.approx(bande.quantite * 500)
    assert bande.montant_devise == pytest.approx(bande.quantite_achat * 2.5)
    assert bande.montant_mad == pytest.approx(bande.quantite * 500 * 9.5)
    assert " kg " in bande.relance
    rubans = next(g for g in plan.fournisseurs if g.fournisseur == "RUBANS")
    assert rubans.quantite == pytest.approx(bande.quantite)
    assert plan.quantite_totale == pytest.approx(sum(x.quantite for x in plan.lignes))


def test_repartition_au_poids_d_un_dossier() -> None:
    """Hérité : test_matieres_au_metre::test_repartition_au_poids_d_un_dossier."""
    dossier = DossierImport(
        numero="DI-1",
        lignes=[
            LigneImport(id=1, reference="POIL BLEU", quantite=1000, valeur_devise=20_000),
            LigneImport(id=2, reference="BANDE 30", quantite=100, valeur_devise=50_000),
        ],
        charges=[ChargeImport(poste="FRET", montant=1100, cle="poids")],
    )
    revient = {x.reference: x for x in revient_dossier(dossier, Parametres())}
    assert revient["POIL BLEU"].charges_mad == pytest.approx(1000)
    assert revient["BANDE 30"].charges_mad == pytest.approx(100)
    assert revient["BANDE 30"].revient_unite == pytest.approx((50_000 + 100) / 100)


def test_consommation_d_un_ordre_en_kilos() -> None:
    """Hérité : test_matieres_au_metre::test_consommation_d_un_ordre_en_kilos."""
    d = donnees(
        mouvements=[
            _entree("CUIR NOIR", 28, 35.0),
            _entree("POIL BLEU", 5000, 20.0),
            Mouvement(
                date=JOUR,
                type="SORTIE_PROD",
                reference="CUIR NOIR",
                quantite=1.5,
                lot_fournisseur="L1",
                magasin_source="MP",
                numero_of="OF-9",
            ),
            Mouvement(
                date=JOUR,
                type="SORTIE_PROD",
                reference="POIL BLEU",
                quantite=210,
                lot_fournisseur="L1",
                magasin_source="MP",
                numero_of="OF-9",
            ),
        ]
    )
    d.ordres = [OrdreFabrication(numero="OF-9", date=JOUR, fabrications=[("8S", 100)])]
    ordre = next(x for x in consommation_par_of(d) if x.numero_of == "OF-9")
    assert ordre.net == pytest.approx(211.5)
    assert ordre.theorique == pytest.approx(100 * (2.0 + 0.014 + 0.6 * 0.005))
    cuir = next(r for r in ordre.references if r.reference == "CUIR NOIR")
    assert cuir.theorique == pytest.approx(1.4) and cuir.ecart == pytest.approx(0.1)
