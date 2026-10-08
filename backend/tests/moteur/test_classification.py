"""La classification d'un fil (`calcul.classification`) : lire une référence (composition,
type, titrage, couleur, suffixe du fournisseur) et l'écrire à partir de ses parties.
"""

from __future__ import annotations

from gestion_mp_pro.calcul import classification
from gestion_mp_pro.calcul.classification import (
    code_composition,
    composer,
    decomposer,
    designation,
    libelle_composition,
)


def test_classer_le_catalogue_lit_les_references() -> None:
    """Hérité (partie moteur) : test_referentiels::test_classer_le_catalogue_lit_les_references.

    La référence se lit ; la couleur « Rouge » de l'essai d'origine vient de la désignation,
    que la route de classement (pas le moteur) préfère au libellé lu (« Red »)."""
    lu = decomposer("PP FRZ-2900 Dtex-Red 7612-Hs")
    assert lu.composition == "PP" and lu.type_fil == "FRZ" and lu.titrage_complet == "2900 Dtex"
    assert (lu.couleur, lu.couleur_code, lu.suffixe) == ("Red", "7612", "Hs")


def test_mot_couleur_mouchete() -> None:
    """Hérité : test_defauts_e::test_mot_couleur_mouchete."""
    assert classification._mot_couleur("Moucheté")


def test_decomposer_et_composer_font_le_chemin_inverse() -> None:
    """Nouveau (CALCULS A § 2) : le suffixe se retire avant le type (« -Hs » n'est pas du
    heat-set), un titrage « 20/2 » est métrique, une nuance « D.Green » est une couleur ; rien
    n'est inventé ; `composer` écrit la référence sans tiret orphelin."""
    gold = decomposer("PP FRZ-2900 Dtex-Gold 3423-Hs")
    assert (gold.type_fil, gold.suffixe, gold.couleur, gold.couleur_code) == (
        "FRZ",
        "Hs",
        "Gold",
        "3423",
    )
    assert (
        composer(
            gold.composition,
            type_fil=gold.type_fil,
            titrage=gold.titrage,
            titrage_unite=gold.titrage_unite,
            couleur=gold.couleur,
            couleur_code=gold.couleur_code,
            suffixe=gold.suffixe,
        )
        == "PP FRZ-2900 Dtex-Gold 3423-Hs"
    )
    pes = decomposer("PES SH 20/2 Beige Cp-1432")
    assert (pes.composition, pes.type_fil, pes.titrage, pes.titrage_unite) == (
        "PES",
        "SH",
        "20/2",
        "Nm",
    )
    assert (pes.couleur, pes.couleur_code) == ("Beige", "Cp 1432")
    vert = decomposer("PP 1750x2 D.Green L.Beige 77")
    assert (vert.titrage, vert.titrage_unite) == ("1750*2", "Dtex")  # unité par défaut du PP
    assert (vert.couleur, vert.couleur_code) == ("D.Green L.Beige", "77")
    assert decomposer("   ").composition == "" and decomposer("XYZ").titrage == ""
    assert composer("pp", couleur="Rouge") == "PP-Rouge"
    assert composer("", titrage="2900", titrage_unite="Dtex", suffixe="Hs") == "2900 Dtex-Hs"


def test_la_nature_dit_la_composition_et_la_designation_la_couleur() -> None:
    """Nouveau (CALCULS A § 2) : la nature en toutes lettres donne le code (« Polyester Fil
    Shrink » → PES), le code donne libellé et famille ; la désignation met le code entre
    parenthèses."""
    assert code_composition("Polyester Fil Shrink") == "PES"
    assert code_composition("Micro polyester") == "MICRO PES"
    assert code_composition("jute naturel") == "JUTE"
    assert code_composition("Viscose brillante") == "VISCOSE" and code_composition("") == ""
    assert libelle_composition("pp") == ("Polypropylène", "Synthétique")
    assert libelle_composition("VISCOSE") == ("VISCOSE", "Autre")
    assert decomposer("FIL 2900 Rouge", "Polypropylène").composition == "PP"
    assert designation("Gris Claire", "3423") == "Gris Claire (3423)"
    assert designation(" Or ") == "Or" and designation("", "12") == "(12)"
