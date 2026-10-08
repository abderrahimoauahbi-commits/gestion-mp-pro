"""Analyse du coût de revient et coût d'une qualité pondéré par sa recette
(`calcul/analyse_revient.py`, `analyse_revient_lignes.py`, `analyse_revient_qualite.py`).

Les cas hérités reprennent les valeurs des essais de Gestion MP (partie calcul : la route lit
la base, ici les dossiers sont écrits à la main).
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.analyse_revient import (
    FiltresRevient,
    QualiteInconnue,
    analyse_revient,
    combinaisons,
    sans_accents,
)
from gestion_mp_pro.calcul.analyse_revient_qualite import analyse_qualite
from gestion_mp_pro.calcul.modele import (
    Article,
    ChargeImport,
    Donnees,
    DossierImport,
    LigneImport,
    LigneRecette,
    Qualite,
)

ROUGE, NOIR, JUTE = "IMP FRISÉ ROUGE", "IMP FRISÉ NOIR", "IMP JUTE"


def _article(reference: str, **champs: object) -> Article:
    return Article(reference=reference, role_bom="Poil", fournisseur="IMPORT ESSAI", **champs)  # type: ignore[arg-type]


def _arrivees() -> Donnees:
    """test_importations.py::arrivees : trois fils en USD, deux factures ; cours 10, un fret
    de 3 500 MAD au poids sur la première."""
    lignes = [
        LigneImport(1, ROUGE, 1000, 2000, "USD", 10, "IR-1", "IMPORT ESSAI"),
        LigneImport(2, NOIR, 500, 2000, "USD", 10, "IN-1", "IMPORT ESSAI"),
        LigneImport(3, JUTE, 2000, 2000, "USD", 10, "IJ-1", "IMPORT ESSAI"),
    ]
    return Donnees(
        articles=[
            _article(ROUGE, type_fil="FRZ", couleur="ROUGE", composition="PES", titrage=2900),
            _article(NOIR, type_fil="FRZ", couleur="NOIR", composition="PES", titrage=2900),
            _article(JUTE, type_fil="HS", composition="JUTE", titrage=1500),
        ],
        qualites=[Qualite("IMPQ", "Essai import", {"Poil": 1})],
        recettes=[LigneRecette("IMPQ", ROUGE, 60), LigneRecette("IMPQ", NOIR, 40)],
        dossiers_import=[
            DossierImport(
                "26/01",
                "Facture IMP-FAC-1",
                date(2026, 9, 1),
                lignes=lignes,
                charges=[ChargeImport("FRET", 3500, cle="poids")],
            ),
            DossierImport(
                "26/02",
                date_arrivee=date(2026, 9, 20),
                statut="Clos",
                lignes=[LigneImport(4, ROUGE, 1000, 2000, "USD", 10, "IR-2", "IMPORT ESSAI")],
            ),
        ],
    )


IDS = {"26/01": 1, "26/02": 2, "80/19": 3, "A2/VIDE": 4}


def test_combinaisons_qualite_et_recherche() -> None:
    """Hérité : test_importations.py::test_analyse_combinaisons_qualite_et_recherche (partie
    calcul : sans accents, mots dans le désordre ; références ; qualité ∩ références)."""
    donnees = _arrivees()
    r = analyse_revient(donnees, FiltresRevient(q="frise rouge", detail=True), ids_dossiers=IDS)
    assert {x.valeur for x in r.lignes} == {ROUGE}
    assert r.ids_dossiers == {"26/01": 1, "26/02": 2}
    assert r.total_poids == pytest.approx(sum(x.poids for x in r.detail_lignes))
    r = analyse_revient(donnees, FiltresRevient(references=f"{JUTE};{NOIR}"))
    assert {x.valeur for x in r.lignes} == {JUTE, NOIR}
    r = analyse_revient(donnees, FiltresRevient(qualite="IMPQ", references=f"{JUTE};{NOIR}"))
    assert {x.valeur for x in r.lignes} == {NOIR}
    # Aucune des références choisies dans la recette : rien, et non toute la recette.
    assert analyse_revient(donnees, FiltresRevient(qualite="IMPQ", references=JUTE)).lignes == []
    assert {x.valeur for x in analyse_revient(donnees, FiltresRevient(qualite="IMPQ")).lignes} == {
        ROUGE,
        NOIR,
    }
    # « frisé » trouve FRZ par le libellé du type ; un mot absent ne trouve rien.
    assert {x.valeur for x in analyse_revient(donnees, FiltresRevient(q="Frisé")).lignes} == {
        ROUGE,
        NOIR,
    }
    assert {x.valeur for x in analyse_revient(donnees, FiltresRevient(q="heat")).lignes} == {JUTE}
    assert analyse_revient(donnees, FiltresRevient(q="heat"), types_fil={}).lignes == []


def test_groupes_totaux_et_detail() -> None:
    """Le fret au poids (3 500 MAD sur 3 500 kg) : 1 000 MAD au rouge du premier dossier ;
    le rouge des deux dossiers fait 2 000 kg, 43 500 MAD (CALCULS B § 9.4)."""
    r = analyse_revient(_arrivees(), FiltresRevient(detail=True))
    rouge = next(x for x in r.lignes if x.valeur == ROUGE)
    assert rouge.quantite == 2000 and rouge.unite == "kg" and rouge.unites == ["kg"]
    assert rouge.marchandise_mad == pytest.approx(40_000) and rouge.charges_mad == pytest.approx(
        1000
    )
    assert rouge.revient_mad == pytest.approx(41_000) and rouge.revient_kg == pytest.approx(20.5)
    assert rouge.dossiers == ["26/01", "26/02"] and rouge.lignes == 2
    assert rouge.detail == {"FRET": pytest.approx(1000)} and rouge.surcout == pytest.approx(0.025)
    assert [x.valeur for x in r.lignes] == [ROUGE, JUTE, NOIR]  # revient décroissant
    assert r.total_lignes == 4 and r.total_charges_mad == pytest.approx(3500)
    assert r.total_revient_mad == pytest.approx(83_500) and r.libelle_axe == "Référence"
    # Le détail : date d'arrivée puis dossier, décroissants.
    assert [x.dossier for x in r.detail_lignes] == ["26/02", "26/01", "26/01", "26/01"]
    noir = next(x for x in r.detail_lignes if x.reference == NOIR)
    assert noir.revient_kg == pytest.approx((20_000 + 500) / 500) and noir.titrage == "2900"
    par_dossier = analyse_revient(_arrivees(), FiltresRevient(axe="dossier"))
    assert [x.valeur for x in par_dossier.lignes] == ["26/01", "26/02"]


def test_l_analyse_additionne_des_kilos() -> None:
    """Hérité : test_importations_second_audit.py::test_l_analyse_additionne_des_kilos (partie
    calcul : 200 kg, 6 000 MAD de revient, 30 MAD le kilo ; la bande à 30 MAD/kg)."""
    donnees = Donnees(
        articles=[Article(reference="A2 FIL"), Article(reference="A2 BANDE", role_bom="Ruban")],
        dossiers_import=[
            DossierImport(
                "A2/1",
                lignes=[
                    LigneImport(1, "A2 FIL", 100, 2000, fournisseur="A2 FOURN"),
                    LigneImport(2, "A2 BANDE", 100, 2000, fournisseur="A2 FOURN"),
                ],
                charges=[ChargeImport("MANUT", 2000, cle="poids")],
            )
        ],
    )
    r = analyse_revient(donnees, FiltresRevient(axe="fournisseur", fournisseur="A2 FOURN"))
    g = r.lignes[0]
    assert g.poids == pytest.approx(200) and r.total_poids == pytest.approx(200)
    assert g.quantite == pytest.approx(200) and g.unite == "kg" and g.unites == ["kg"]
    assert g.revient_kg == pytest.approx(6000 / 200)
    r = analyse_revient(donnees, FiltresRevient(fournisseur="A2 FOURN"))
    bande = next(x for x in r.lignes if x.valeur == "A2 BANDE")
    assert bande.quantite == pytest.approx(100) and bande.revient_unite == pytest.approx(30)
    assert bande.revient_kg == pytest.approx(30)
    par_lot = analyse_revient(donnees, FiltresRevient(axe="lot"))
    assert [x.valeur for x in par_lot.lignes] == ["—"]  # sans lot : « — »


def _vides(donnees: Donnees) -> Donnees:
    donnees.dossiers_import += [
        DossierImport(
            "80/19", date_arrivee=date(2019, 6, 1), charges=[ChargeImport("DD", 6_547_654)]
        ),
        DossierImport("A2/VIDE", date_arrivee=date(2019, 4, 1), charges=[ChargeImport("DD", 1234)]),
        DossierImport("TVA/SEULE", charges=[ChargeImport("TVA", 999)]),  # récupérable : rien
    ]
    return donnees


def test_frais_sans_marchandise_a_part() -> None:
    """Hérité : test_importations.py::test_frais_sans_marchandise_a_part_partout et
    test_importations_second_audit.py::test_les_frais_non_repartis_suivent_les_filtres (partie
    calcul : à part, hors des charges ; filtrés comme les marchandises)."""
    donnees = _vides(_arrivees())
    r = analyse_revient(donnees, ids_dossiers=IDS)
    assert r.total_charges_mad == pytest.approx(3500)
    assert [(x.dossier, x.montant) for x in r.dossiers_non_repartis] == [
        ("80/19", 6_547_654),
        ("A2/VIDE", 1234),
    ]
    assert r.frais_non_repartis_mad == 6_547_654 + 1234 and r.ids_dossiers["80/19"] == 3
    r = analyse_revient(donnees, FiltresRevient(fournisseur="IMPORT ESSAI"))
    assert "A2/VIDE" not in {x.dossier for x in r.dossiers_non_repartis}
    r = analyse_revient(donnees, FiltresRevient(q="a2/vide"))
    assert [x.dossier for x in r.dossiers_non_repartis] == ["A2/VIDE"] and r.lignes == []
    # Un dossier aux frais globaux sans valeur à répartir : non réparti s'il a une ligne retenue.
    donnees.dossiers_import.append(
        DossierImport(
            "SANS VALEUR",
            lignes=[LigneImport(9, JUTE, 10, 0)],
            charges=[ChargeImport("DD", 50)],
        )
    )
    r = analyse_revient(donnees, FiltresRevient(references=JUTE))
    assert [(x.dossier, x.montant) for x in r.dossiers_non_repartis] == [("SANS VALEUR", 50)]


def test_periode_et_statut() -> None:
    """Hérité : test_defauts_b.py::test_analyse_statut_insensible_a_la_casse (partie calcul)."""
    donnees = _vides(_arrivees())
    clos = analyse_revient(donnees, FiltresRevient(statut="Clos"))
    assert analyse_revient(donnees, FiltresRevient(statut="clos")).total_revient_mad == (
        pytest.approx(clos.total_revient_mad)
    )
    assert clos.total_revient_mad == pytest.approx(20_000)
    with pytest.raises(ValueError, match="Statut de dossier inconnu : « fermé »"):
        analyse_revient(donnees, FiltresRevient(statut="fermé"))
    # La période porte sur la date d'arrivée ; un dossier sans date passe.
    r = analyse_revient(donnees, FiltresRevient(debut=date(2026, 9, 10)))
    assert [x.dossier for x in r.dossiers_non_repartis] == []
    assert {n for x in r.lignes for n in x.dossiers} == {"26/02"}
    r = analyse_revient(donnees, FiltresRevient(fin=date(2026, 9, 10)))
    assert {n for x in r.lignes for n in x.dossiers} == {"26/01"}
    assert len(r.dossiers_non_repartis) == 2


def test_criteres_et_selection() -> None:
    donnees = _arrivees()

    def valeurs(**filtres: object) -> set[str]:
        return {x.valeur for x in analyse_revient(donnees, FiltresRevient(**filtres)).lignes}  # type: ignore[arg-type]

    assert valeurs(composition="PES") == {ROUGE, NOIR}
    assert valeurs(type_fil="FRZ", couleur="NOIR") == {NOIR}
    assert valeurs(titrage="1500") == {JUTE}
    selection = '[{"composition":"PES","couleur":"ROUGE"},{"titrage":"1500","couleur":""}]'
    assert valeurs(selection=selection) == {ROUGE, JUTE}
    assert valeurs(selection=" ") == {ROUGE, NOIR, JUTE}
    assert valeurs(axe="composition") == {"PES", "JUTE"}
    assert valeurs(axe="couleur") == {"ROUGE", "NOIR", "—"}  # ni couleur ni désignation : « — »
    assert valeurs(axe="type_fil") == {"FRZ", "HS"}


@pytest.mark.parametrize(
    ("selection", "message"),
    [
        ("[{", "sélection illisible : "),
        ('{"composition":"PES"}', "la sélection doit être une liste de combinaisons"),
        ('["PES"]', "la sélection doit être une liste de combinaisons"),
        ('[{"qualite":"X"}]', "critère inconnu dans la sélection : qualite"),
    ],
)
def test_selection_refusee(selection: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        combinaisons(selection)


def test_axe_et_qualite_inconnus() -> None:
    with pytest.raises(ValueError, match="axe inconnu : « x » \\(attendu : reference, compo"):
        analyse_revient(_arrivees(), FiltresRevient(axe="x"))
    with pytest.raises(QualiteInconnue, match="qualité inconnue ou sans recette : « NULLE »"):
        analyse_revient(_arrivees(), FiltresRevient(qualite="NULLE"))
    with pytest.raises(QualiteInconnue, match="« NULLE »"):
        analyse_qualite(_arrivees(), "NULLE")
    assert sans_accents("Frisé ÉCRU") == "frise ecru" and combinaisons("") == []


def test_cout_d_une_qualite_pondere_par_la_recette() -> None:
    """Hérité : test_importations.py::test_cout_d_une_qualite_pondere_par_la_recette (partie
    calcul : 1 kg de poil au m², 60 % rouge et 40 % noir) et
    test_analyse_combinaisons_qualite_et_recherche (`references_importees` = 2)."""
    r = analyse_qualite(_arrivees(), "IMPQ")
    cout = {x.valeur: x.revient_unite or 0.0 for x in r.lignes}
    attendu = 0.6 * cout[ROUGE] + 0.4 * cout[NOIR]
    assert r.cout_m2 == pytest.approx(attendu) and r.couverture == pytest.approx(1)
    assert r.cout_kg_tapis == pytest.approx(attendu) and r.cout_m2_estime == pytest.approx(attendu)
    assert sum(x.part_recette or 0.0 for x in r.lignes) == pytest.approx(100)
    assert r.references_importees == 2 and r.references_de_la_recette == 2
    assert (r.qualite, r.nom, r.poids_m2, r.roles_sans_cout) == ("IMPQ", "Essai import", 1, [])
    rouge = next(x for x in r.lignes if x.valeur == ROUGE)
    assert (rouge.role, rouge.poids_m2) == ("Poil", pytest.approx(0.6))
    assert rouge.cout_m2 == pytest.approx(0.6 * 20.5)
    assert r.roles[0].fils == 2 and r.roles[0].importes == 2


def test_une_qualite_aux_roles_inconnus_et_au_metre() -> None:
    """Un rôle à moitié importé s'extrapole ; un rôle sans aucun fil importé est sans coût ;
    un rôle au mètre (franges : ml/m² × densité) compte au m², pas au kilo de tapis."""
    donnees = _arrivees()
    donnees.articles += [
        Article(reference="TRAME X", role_bom="Trame"),
        Article(reference="FRANGE", role_bom="Franges", densite=0.05),
        Article(reference="POIL JAMAIS", role_bom="Poil"),
    ]
    donnees.qualites = [Qualite("Q", "Mixte", {"Poil": 2.0, "Trame": 0.5, "Franges": 0.4})]
    donnees.recettes = [
        LigneRecette("Q", ROUGE, 50),
        LigneRecette("Q", "POIL JAMAIS", 50),
        LigneRecette("Q", "TRAME X", 100),
        LigneRecette("Q", "FRANGE", 100),
    ]
    donnees.reindexer()
    donnees.dossiers_import[1].lignes.append(LigneImport(5, "FRANGE", 10, 300, "MAD"))
    r = analyse_qualite(donnees, "Q")
    roles = {b.role: b for b in r.roles}
    assert [b.role for b in r.roles] == ["Poil", "Trame", "Franges"]  # poids au m² décroissant
    assert roles["Poil"].connu_m2 == pytest.approx(1.0) and roles["Poil"].importes == 1
    assert roles["Franges"].lineaire and r.roles_sans_cout == ["Trame"]
    poil = 2.0 * 0.5 * 20.5  # kg/m² connus × MAD/kg
    frange = 0.4 * 0.05 * 30.0  # ml/m² × kg/ml × MAD/kg
    assert r.cout_m2 == pytest.approx(poil + frange)
    assert r.poids_m2 == pytest.approx(2.5) and r.couverture == pytest.approx(1.0 / 2.5)
    assert r.cout_m2_estime == pytest.approx(poil / 1.0 * 2.0 + frange / 0.4 * 0.4)
    assert r.cout_kg_tapis == pytest.approx(poil / 1.0 * 2.0 / 2.0)
    assert r.references_importees == 2
