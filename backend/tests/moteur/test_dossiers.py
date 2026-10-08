"""Les dossiers d'importation (`calcul.importations`) : la marchandise en dirhams, les frais
répartis à la valeur ou au poids, la TVA et les droits attendus, la facture rapprochée.
"""

from __future__ import annotations

import pytest

from gestion_mp_pro.calcul.importations import (
    ecart_droits,
    ecart_facture,
    ecart_tva_tolere,
    lignes_aberrantes,
    lignes_negatives,
    revient_dossier,
    revient_par_reception,
    tva_attendue,
    valeur_ligne_import,
)
from gestion_mp_pro.calcul.modele import (
    ChargeImport,
    Donnees,
    DossierImport,
    LigneImport,
    Parametres,
)


def test_une_ligne_en_dirhams_n_a_pas_de_cours() -> None:
    """Hérité (partie moteur) : test_importations::test_une_ligne_en_dirhams_n_a_pas_de_cours.

    La partie `reprise.devise_ligne_dossier` (reprise des dossiers de Gestion MP) n'est pas au
    moteur : elle n'est pas portée ici."""
    p = Parametres()
    # Une ligne « MAD » au cours 9,58 (82/26 repris) : le cours est ignoré.
    ligne = LigneImport(
        id=1, reference="X", quantite=10, valeur_devise=1000, devise="MAD", cours=9.58
    )
    assert valeur_ligne_import(ligne, p) == pytest.approx(1000)
    # Un dossier sans marchandise n'attend aucune TVA, même avec des droits saisis.
    vide = DossierImport(numero="80/26", charges=[ChargeImport(poste="DD", montant=6_547_654)])
    assert tva_attendue(vide, p) == 0


def test_un_frais_au_poids_suit_les_kilos() -> None:
    """Hérité : test_parcours::test_un_frais_au_poids_suit_les_kilos.

    Le fret réglé « au poids » se répartit sur les kilos, pas sur la valeur."""
    d = DossierImport(
        numero="T",
        lignes=[
            LigneImport(id=1, reference="CHER", quantite=100, valeur_devise=9000, devise="MAD"),
            LigneImport(id=2, reference="LEGER", quantite=300, valeur_devise=1000, devise="MAD"),
        ],
        charges=[
            ChargeImport(poste="FRET", montant=400, cle="poids"),
            ChargeImport(poste="DD", montant=1000),
        ],
    )
    r = {x.reference: x for x in revient_dossier(d, Parametres())}
    assert r["CHER"].detail["FRET"] == 100 and r["LEGER"].detail["FRET"] == 300
    assert r["CHER"].detail["DD"] == 900 and r["LEGER"].detail["DD"] == 100


def test_un_dossier_pese_en_kilos() -> None:
    """Hérité (partie moteur) : test_importations_second_audit::test_un_dossier_pese_en_kilos.

    100 kg de fil à 2 USD et 100 kg de bande (2 000 ml à 0,1 USD, 0,05 kg/ml : 2 USD le kilo),
    au cours de 10 ; 2 000 MAD de manutention au poids : 1 000 MAD chacun ; la bande coûte
    2 000 + 1 000 MAD, 30 MAD le kilo."""
    d = DossierImport(
        numero="A2-MET",
        lignes=[
            LigneImport(1, "A2 FIL", 100, 200, devise="USD", cours=10.0),
            LigneImport(2, "A2 BANDE", 100, 200, devise="USD", cours=10.0),
        ],
        charges=[ChargeImport(poste="A2MAN", montant=2000, cle="poids")],
    )
    bande = next(x for x in revient_dossier(d, Parametres()) if x.reference == "A2 BANDE")
    assert sum(x.poids_kg for x in revient_dossier(d, Parametres())) == pytest.approx(200)
    assert bande.quantite == 100 and bande.poids_kg == pytest.approx(100)
    assert bande.revient_mad == pytest.approx(3000)
    assert bande.revient_unite == pytest.approx(30)


def test_droits_ecart_calcule_au_serveur() -> None:
    """Hérité (partie moteur) : test_defauts_b::test_droits_ecart_calcule_au_serveur.

    L'écart des droits (2 %, au moins 50 MAD)."""
    assert ecart_droits(1000, 1040) is None  # 40 MAD : sous les 50
    assert ecart_droits(10_000, 10_150) is None  # 1,5 %
    assert ecart_droits(10_000, 10_300) == pytest.approx(-300)
    assert ecart_droits(0, 10_300) is None and ecart_droits(500, None) is None


def test_la_tva_attendue_se_calcule_sur_la_valeur_en_douane() -> None:
    """Nouveau (CALCULS B § 9) : TVA = 20 % × (marchandise + fret + assurance + droits + TPI) ;
    la TPI se calcule à 0,25 % de la valeur en douane si elle n'est pas saisie ; 5 % d'écart
    tolérés ; la TVA ne fait jamais le coût."""
    p = Parametres()
    d = DossierImport(
        numero="TVA",
        lignes=[LigneImport(1, "P", 1000, 1000, devise="USD", cours=10.0)],
        charges=[
            ChargeImport(poste="FRET", montant=1500),
            ChargeImport(poste="ASSUR", montant=500),
            ChargeImport(poste="DD", montant=2500),
            ChargeImport(poste="TRANSIT", montant=700),
            ChargeImport(poste="TVA", montant=5000),
        ],
    )
    douane = 10_000 + 1500 + 500
    assert tva_attendue(d, p) == pytest.approx((douane + 2500 + douane * 0.0025) * 0.20)
    d.charges.append(ChargeImport(poste="TPI", montant=40))
    assert tva_attendue(d, p) == pytest.approx((douane + 2500 + 40) * 0.20)
    assert ecart_tva_tolere(-3000) == pytest.approx(150)
    (ligne,) = revient_dossier(d, p)
    assert ligne.tva_mad == pytest.approx(5000)
    assert ligne.charges_mad == pytest.approx(1500 + 500 + 2500 + 700 + 40)
    assert ligne.revient_unite == pytest.approx((10_000 + 5240) / 1000)
    assert ligne.decaisse_mad == pytest.approx(10_000 + 5240 + 5000)
    assert ligne.surcout == pytest.approx(0.524)
    # Un poste « TVA » que le référentiel dit non récupérable devient un coût.
    d.charges[4] = ChargeImport(poste="TVA", montant=5000, recuperable_poste=False)
    assert revient_dossier(d, p)[0].tva_mad == 0


def test_charges_directes_parts_figees_et_lignes_a_revoir() -> None:
    """Nouveau (CALCULS B § 9) : un frais visé sur une ligne lui revient ; une répartition
    figée garde ses parts tant qu'elle couvre le frais ; un avoir peut rendre une ligne
    négative ; au-delà du seuil de sa valeur, une ligne est aberrante."""
    p = Parametres()
    d = DossierImport(
        numero="DIR",
        lignes=[
            LigneImport(1, "A", 100, 1000),
            LigneImport(2, "B", 100, 3000),
        ],
        charges=[
            ChargeImport(poste="TRANSIT", montant=1200, ligne=1),
            ChargeImport(poste="PORT", montant=100, parts={1: 70.0, 2: 30.0}),
            ChargeImport(poste="TIMBRE", montant=100, parts={1: 70.0}),  # incomplète : à la valeur
            ChargeImport(poste="AUTRE", montant=-3500, ligne=2),
        ],
    )
    a, b = revient_dossier(d, p)
    assert a.detail == pytest.approx({"TIMBRE": 25.0, "TRANSIT": 1200.0, "PORT": 70.0})
    assert b.detail == pytest.approx({"TIMBRE": 75.0, "PORT": 30.0, "AUTRE": -3500.0})
    assert [x.reference for x in lignes_aberrantes([a, b], 1.0)] == ["A"]  # 1 295 > 1 000
    assert [x.reference for x in lignes_negatives([a, b])] == ["B"]  # 3 000 − 3 395 < 0


def test_la_facture_se_rapproche_de_la_marchandise_recue() -> None:
    """Nouveau (CALCULS B § 9) : facture − Σ valeurs en devise ; hors tolérance au-delà de 2 %
    et d'un demi-centime ; rien à rapprocher sans montant ou dans une autre devise."""
    p = Parametres()
    d = DossierImport(
        numero="FAC",
        lignes=[
            LigneImport(1, "A", 100, 1000, devise="USD"),
            LigneImport(2, "B", 50, 500, devise="USD"),
        ],
        facture="F-1",
        facture_montant=1550,
        facture_devise="USD",
    )
    ecart = ecart_facture(d, p)
    assert ecart is not None
    assert (ecart.recu, ecart.ecart, ecart.tolerance) == (1500, 50, 0.02)
    assert ecart.part == pytest.approx(50 / 1500) and ecart.hors_tolerance
    d.facture_montant = 1520
    moins = ecart_facture(d, p)
    assert moins is not None and not moins.hors_tolerance
    d.facture_devise = "EUR"
    assert ecart_facture(d, p) is None
    d.facture_montant = 0
    assert ecart_facture(d, p) is None


def test_le_revient_s_indexe_par_ligne_de_reception() -> None:
    """Nouveau (CALCULS B § 9) : seules les marchandises reçues (ligne de réception connue)
    s'indexent ; la valeur en devise passe au cours du dossier, sinon au taux des réglages."""
    d = Donnees(
        dossiers_import=[
            DossierImport(
                numero="D",
                lignes=[
                    LigneImport(1, "A", 100, 100, devise="EUR", ligne_reception_id=41),
                    LigneImport(2, "B", 100, 100, devise="EUR", cours=12.0),
                ],
                charges=[ChargeImport(poste="FRET", montant=230)],
            )
        ]
    )
    index = revient_par_reception(d)
    assert list(index) == [41]
    # 100 EUR × 11 (taux des réglages) = 1 100 ; fret 230 × 1 100 / 2 300 = 110.
    assert index[41].valeur_mad == pytest.approx(1100)
    assert index[41].revient_unite == pytest.approx((1100 + 110) / 100)
