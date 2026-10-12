"""La classification d'un fil (`calcul.classification`) : lire une référence (composition,
type, titrage, couleur, suffixe du fournisseur) et l'écrire à partir de ses parties.

Les unités de titrage sont passées par l'appelant (le référentiel `unite_titrage`, révision
0008) : ces essais lisent avec les six unités semées.
"""

from __future__ import annotations

from gestion_mp_pro.calcul import classification
from gestion_mp_pro.calcul.classification import (
    Classification,
    code_composition,
    composer,
    designation,
    libelle_composition,
)

SEMEES = ("Dtex", "Deniers", "Nm", "Tex", "Nec", "lbs")
"""Les unités semées par la révision 0008, dans leur ordre."""


def decomposer(reference: str, nature: str = "") -> Classification:
    """La lecture d'une référence avec les six unités semées."""
    return classification.decomposer(reference, nature, unites=SEMEES)


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


def test_les_unites_viennent_de_l_appelant() -> None:
    """Lot UNITES-TITRAGE (Mohamed, 12/10/2026) : une unité ajoutée se lit, la plus longue
    d'abord (« Nec » avant « Ne ») ; « Den » abrège Deniers tant que Deniers est dans la liste ;
    une unité retirée (désactivée) ne se lit plus, ni comme unité sous-entendue ; la casse de la
    référence ne compte pas, l'écriture est celle de la liste."""
    avec_ne = (*SEMEES, "Ne")
    coton = classification.decomposer("Coton 20 Ne Blanc", unites=avec_ne)
    assert (coton.titrage, coton.titrage_unite, coton.couleur) == ("20", "Ne", "Blanc")
    assert classification.decomposer("Coton 20 NEC", unites=avec_ne).titrage_unite == "Nec"
    assert decomposer("Coton 20 Ne Blanc").titrage_unite == ""
    pes = decomposer("PES 1500 den Noir")
    assert (pes.titrage, pes.titrage_unite, pes.couleur) == ("1500", "Deniers", "Noir")
    sans_deniers = tuple(u for u in SEMEES if u != "Deniers")
    assert classification.decomposer("PES 1500 den", unites=sans_deniers).titrage_unite == ""
    assert classification.decomposer("PES 1500", unites=sans_deniers).titrage_unite == ""
    assert decomposer("PES 1500").titrage_unite == "Deniers"
    sans_nm = tuple(u for u in SEMEES if u != "Nm")
    assert classification.decomposer("Jute 12/1", unites=sans_nm).titrage_unite == ""
    vide = classification.decomposer("PP FRZ-2900 Dtex-Gold", unites=())
    assert (vide.titrage, vide.titrage_unite) == ("2900", "")
    assert classification.decomposer("PP 2900 DTEX", unites=("dtex",)).titrage_unite == "dtex"
    assert classification.lecture_unites(avec_ne) is classification.lecture_unites(avec_ne)
