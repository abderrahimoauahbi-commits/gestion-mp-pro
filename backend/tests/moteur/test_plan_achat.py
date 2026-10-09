"""Le plan d'achat (`calcul.plan_achat`) : ce qui est désactivé ne se rachète pas, le budget
est la somme des lignes affichées, un brouillon n'est pas reproposé, les urgences d'abord, le
rang du catalogue départage, le délai d'un fournisseur inconnu est le délai par défaut.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.constantes import STATUTS
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Fournisseur,
    LigneCommande,
    Mouvement,
    Parametres,
)
from gestion_mp_pro.calcul.plan_achat import plan_achat, tier
from gestion_mp_pro.calcul.stock import LigneStock, etat_stock
from moteur.fabrique import JOUR, ligne_de, usine


@pytest.mark.parametrize("inactif", ["matiere", "fournisseur"])
def test_une_matiere_ou_un_fournisseur_desactive_ne_se_rachete_pas(inactif: str) -> None:
    """Hérité :
    test_audit2_achat::test_une_matiere_ou_un_fournisseur_desactive_ne_se_rachete_pas.
    """
    d = usine(100)
    assert ligne_de(d, "FIL A").quantite_a_commander > 0  # en recette, sans stock : à commander
    if inactif == "matiere":
        d.articles[0].actif = False
    else:
        d.fournisseurs[0].actif = False
    a = ligne_de(d, "FIL A")
    assert a.quantite_a_commander == 0 and "désactivé" in a.sans_achat
    assert plan_achat(d, etat_stock(d, JOUR)).budget_mad == 0


def test_le_budget_est_la_somme_des_lignes_affichees() -> None:
    """Hérité : test_audit2_achat::test_le_budget_est_la_somme_des_lignes_affichees.

    Une commande de réapprovisionnement au statut OK compte au budget : elle est dans le
    détail, comme une alerte."""
    d = usine(100, mouvements=[Mouvement(date(2026, 6, 1), "STOCK_INITIAL", "FIL A", 2500)])
    lignes = etat_stock(d, JOUR)
    a = next(x for x in lignes if x.reference == "FIL A")
    assert a.quantite_a_commander > 0 and a.statut == "OK"
    plan = plan_achat(d, lignes)
    assert [x.reference for x in plan.lignes] == ["FIL A"]
    assert plan.budget_mad == pytest.approx(sum(x.montant_mad for x in plan.lignes))
    assert plan.budget_mad == pytest.approx(sum(g.montant_mad for g in plan.fournisseurs))


def test_un_brouillon_n_est_pas_repropose_mais_n_est_pas_attendu() -> None:
    """Hérité : test_audit2_achat::test_un_brouillon_n_est_pas_repropose_mais_n_est_pas_attendu."""
    d = usine(100)
    avant = ligne_de(d, "FIL A")
    brouillon = Commande(
        "BC-brouillon-7",
        fournisseur="F",
        statut="Brouillon",
        lignes=[LigneCommande("BC-brouillon-7", "FIL A", quantite_commandee=300)],
    )
    d.commandes = [brouillon]
    apres = ligne_de(d, "FIL A")
    assert apres.bc_en_preparation == 300 and apres.bons_en_preparation == ["BC-brouillon-7"]
    assert apres.quantite_a_commander == pytest.approx(avant.quantite_a_commander - 300)
    # Pas parti : le stock projeté et le statut ne le comptent pas.
    assert apres.stock_projete == avant.stock_projete and apres.statut == avant.statut
    plan = plan_achat(d, etat_stock(d, JOUR))
    assert plan.lignes[0].bons_en_preparation == ["BC-brouillon-7"]
    # Le brouillon couvre tout, à un cheveu près : plus rien à proposer, pas 1e-10 kg.
    brouillon.lignes[0].quantite_commandee = avant.quantite_a_commander - 1e-10
    assert ligne_de(d, "FIL A").quantite_a_commander == 0


def test_d15_le_groupe_d_un_fournisseur_inconnu_prend_le_delai_par_defaut() -> None:
    """Hérité :
    test_defauts_d::test_d15_le_groupe_d_un_fournisseur_inconnu_prend_le_delai_par_defaut.
    """
    d = usine(
        references=("FIL A",),
        articles=[Article(reference="FIL A", role_bom="Poil", fournisseur="INCONNU", prix_unite=1)],
        mouvements=[],
        fournisseurs=[],
    )
    lignes = etat_stock(d, date(2026, 10, 8))
    plan = plan_achat(d, lignes)
    groupe = next(g for g in plan.fournisseurs if g.fournisseur == "INCONNU")
    assert groupe.delai_jours == d.parametres.delai_defaut == lignes[0].delai_jours


def test_d20_a_montant_egal_le_rang_du_catalogue_departage() -> None:
    """Hérité : test_defauts_d::test_d20_a_montant_egal_le_rang_du_catalogue_departage."""
    d = usine(references=("FIL A",))
    lignes = [
        LigneStock(
            reference=r,
            fournisseur="F",
            quantite_a_commander=10,
            montant_a_commander_mad=100,
            classe_abc="C",
        )
        for r in ("PREMIER", "SECOND")
    ]
    plan = plan_achat(d, lignes)
    assert [x.reference for x in plan.lignes] == ["PREMIER", "SECOND"]


def _ligne(
    reference: str, statut: str, montant: float, fournisseur: str = "F", classe: str = "C"
) -> LigneStock:
    return LigneStock(
        reference=reference,
        fournisseur=fournisseur,
        statut=statut,
        classe_abc=classe,
        quantite_a_commander=10,
        montant_a_commander=montant,
        montant_a_commander_mad=montant,
    )


def test_le_tier_et_l_urgence_suivent_le_statut_avant_le_montant() -> None:
    """Hérité : test_plan_besoins::test_le_tier_et_l_urgence_suivent_le_statut_avant_le_montant."""
    p = Parametres()
    assert tier(_ligne("a", STATUTS["CRITIQUE"], 500), p) == "🔥 TIER 1"
    assert tier(_ligne("b", STATUTS["URGENT"], 500), p) == "🟠 TIER 2"
    assert tier(_ligne("c", STATUTS["URGENT"], 400_000, classe="A"), p) == "🔥 TIER 1"
    assert tier(_ligne("d", STATUTS["ATTENTION"], 500), p) == "⚪ TIER 4"

    d = usine(fournisseurs=[Fournisseur(nom="F"), Fournisseur(nom="G"), Fournisseur(nom="H")])
    lignes = [
        _ligne("a", STATUTS["URGENT"], 3000),
        _ligne("b", STATUTS["OK"], 900_000, "G"),
        _ligne("c", STATUTS["ATTENTION"], 50_000, "H"),
    ]
    groupes = {g.fournisseur: g for g in plan_achat(d, lignes).fournisseurs}
    assert groupes["F"].urgence == "🚨 BC URGENT" and groupes["F"].urgents == 1
    assert groupes["G"].urgence == "📋 BC groupé"  # un gros montant n'est pas une urgence
    assert groupes["H"].urgence == "📝 Standard"


def test_le_tier_suit_les_seuils_de_montant_et_le_plan_les_compte() -> None:
    """Nouveau (CALCULS A § 3.12) : 300 000 MAD en classe A ou rupture → Tier 1 ; ≥ 200 000 →
    Tier 2 ; ≥ 100 000 → Tier 3 ; sinon Tier 4 ; le plan pondère × 3 la classe A, × 2 la B."""
    p = Parametres()
    assert tier(_ligne("a", STATUTS["RUPTURE"], 1), p) == "🔥 TIER 1"
    assert tier(_ligne("b", STATUTS["OK"], 300_000, classe="B"), p) == "🟠 TIER 2"
    assert tier(_ligne("c", STATUTS["OK"], 200_000), p) == "🟠 TIER 2"
    assert tier(_ligne("d", STATUTS["OK"], 199_999.99), p) == "🟡 TIER 3"
    assert tier(_ligne("e", STATUTS["OK"], 100_000), p) == "🟡 TIER 3"
    assert tier(_ligne("f", STATUTS["OK"], 99_999), p) == "⚪ TIER 4"
    d = usine(references=("FIL A",))
    lignes = [
        _ligne("C 400", STATUTS["OK"], 400, classe="C"),
        _ligne("B 250", STATUTS["OK"], 250, classe="B"),
        _ligne("A 150", STATUTS["OK"], 150, classe="A"),
    ]
    plan = plan_achat(d, lignes)
    # Pondérés : 250 × 2 = 500, puis 150 × 3 = 450, puis 400 × 1.
    assert [x.reference for x in plan.lignes] == ["B 250", "A 150", "C 400"]
    assert plan.budget_mad == pytest.approx(800) and plan.tiers["⚪ TIER 4"] == 3
