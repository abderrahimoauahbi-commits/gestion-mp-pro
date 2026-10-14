"""La nomenclature (`calcul.nomenclature`) : les kilos au m² de chaque matière, et le contrôle
des recettes (100 % par rôle, à 0,01 point).
"""

from __future__ import annotations

import pytest

from gestion_mp_pro.calcul.modele import Article, Donnees, LigneRecette, Parametres, Qualite
from gestion_mp_pro.calcul.nomenclature import (
    controle_recettes,
    kg_par_m2,
    metres_du_role,
    nomenclature,
    poids_du_role,
    texte_ecart,
)


def _qualite_z2b(pourcentage: float) -> Donnees:
    return Donnees(
        articles=[Article(reference="Z2 POIL", role_bom="Poil", prix_unite=10)],
        qualites=[Qualite(code="Z2B", nom="Z2 b", poids={"Poil": 1.0})],
        recettes=[LigneRecette("Z2B", "Z2 POIL", pourcentage)],
    )


def test_une_recette_acceptee_n_est_pas_bloquante_le_lendemain() -> None:
    """Hérité (partie moteur) :
    test_audit2_atelier::test_une_recette_acceptee_n_est_pas_bloquante_le_lendemain.

    99,995 % est à 0,01 point de 100 : la recette est conforme ; 99,9 ne l'est pas (la route
    la refuse à l'enregistrement)."""
    (controle,) = controle_recettes(_qualite_z2b(99.995))
    assert controle.conforme
    (refuse,) = controle_recettes(_qualite_z2b(99.9))
    assert not refuse.conforme and refuse.ecarts[0].somme == pytest.approx(99.9)


def test_le_controle_compte_les_roles_utilises() -> None:
    """Nouveau (CALCULS § 3.5, `Recettes!O6:R26`) : un rôle de poids nul n'est pas utilisé ;
    chaque rôle utilisé doit faire 100 % ; une ligne sans matière connue ne compte pas."""
    d = Donnees(
        articles=[
            Article(reference="P1", role_bom="Poil"),
            Article(reference="P2", role_bom="Poil"),
            Article(reference="T", role_bom="Trame"),
        ],
        qualites=[Qualite(code="Q", poids={"Poil": 1.2, "Trame": 0.4, "Colle": 0.0})],
        recettes=[
            LigneRecette("Q", "P1", 60),
            LigneRecette("Q", "P2", 40),
            LigneRecette("Q", "T", 90),
            LigneRecette("Q", "INCONNU", 10),
        ],
    )
    (q,) = controle_recettes(d)
    assert (q.roles_utilises, q.roles_conformes, q.conforme) == (2, 1, False)
    assert [(e.role, e.somme) for e in q.ecarts] == [("Trame", 90)]


def test_les_kilos_au_m2_d_un_role_au_poids_et_d_un_role_au_metre() -> None:
    """Nouveau (CALCULS § 3.5) : kg/m² = % × poids du rôle ; au mètre, × densité ; une matière
    ou une qualité inconnue ne demande rien ; le coût au m² compte la perte et le change."""
    franges = Article(reference="FR", role_bom="Franges", densite=0.02, prix_unite=50, devise="EUR")
    poil = Article(reference="PO", role_bom="Poil", prix_unite=20)
    d = Donnees(
        parametres=Parametres(taux_perte=0.02),
        articles=[franges, poil],
        qualites=[Qualite(code="Q", poids={"Franges": 0.5, "Poil": 2.0})],
        recettes=[
            LigneRecette("Q", "FR", 100),
            LigneRecette("Q", "PO", 75),
            LigneRecette("Q", "ABSENT", 25),
        ],
    )
    assert metres_du_role(d, "Q", franges) == 0.5 and metres_du_role(d, "Q", poil) == 0
    assert poids_du_role(d, "Q", franges) == pytest.approx(0.01)
    assert poids_du_role(d, "AUTRE", poil) == 0
    assert kg_par_m2(d, "Q", "PO", 75) == pytest.approx(1.5)
    assert kg_par_m2(d, "Q", "ABSENT", 25) == 0
    fr, po, absent = nomenclature(d)
    assert fr.kg_m2 == pytest.approx(0.01) and fr.ml_m2 == pytest.approx(0.5)
    assert fr.cout_m2_mad == pytest.approx(0.01 * 50 * 11 * 1.02)
    assert po.cout_m2_mad == pytest.approx(1.5 * 20 * 1.02) and po.poids_categorie == 2.0
    assert (absent.kg_m2, absent.cout_m2_mad, absent.role_bom) == (0, 0, "")


def test_un_role_pesant_sans_aucune_matiere_au_catalogue_dit_de_creer_la_matiere() -> None:
    """Audit n° 2 (décision Franges) : six qualités pèsent 0,8 ml/m² de Franges alors que nulle
    matière Franges n'existe ; l'écart le dit (« créer la matière Franges ») au lieu d'un
    « Franges (0 %) » obscur. Un rôle à 0 % dont une matière existe garde l'ancien texte."""
    d = Donnees(
        articles=[Article(reference="P", role_bom="Poil"), Article(reference="C", role_bom="Cuir")],
        qualites=[Qualite(code="8M", poids={"Poil": 1.0, "Franges": 0.8, "Cuir": 0.5})],
        recettes=[LigneRecette("8M", "P", 100)],
    )
    (q,) = controle_recettes(d)
    ecarts = {e.role: e for e in q.ecarts}
    assert ecarts["Franges"].sans_matiere and ecarts["Franges"].somme == 0
    assert not ecarts["Cuir"].sans_matiere
    assert texte_ecart(ecarts["Cuir"]) == "Cuir (0 %)"
    assert texte_ecart(ecarts["Franges"]) == (
        "Franges (0 % : aucune matière Franges au catalogue — créer la matière Franges, puis la "
        "mettre dans la recette)"
    )
