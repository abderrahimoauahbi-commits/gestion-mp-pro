"""Les calculs purs du chargeur (`calcul.chargement`) : statut d'un bon, motif de retour,
répartition au prorata d'un lot, histoire du plan, appariement des entrées de réception,
journal de la base traduit en journal du moteur.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest

from gestion_mp_pro.calcul.chargement import (
    EcritureLue,
    EntreeLue,
    LigneDeReception,
    LigneRecue,
    arret_sans_histoire,
    au_prorata,
    code_motif,
    journal_du_moteur,
    lignes_des_receptions,
    recu_par_ligne,
    statut_moteur,
    versions_du_plan,
)
from gestion_mp_pro.calcul.modele import VersionPlan
from moteur.fabrique import instant

UN = [1.0] * 12


def test_un_coefficient_de_saisonnalite_ne_remet_pas_la_croissance_a_zero() -> None:
    """Hérité :
    test_audit2_achat::test_un_coefficient_de_saisonnalite_ne_remet_pas_la_croissance_a_zero.
    """
    saison = [1.0] * 12
    decembre = [*saison[:11], 1.3]
    brut: list[tuple[datetime, dict[str, object], dict[str, object]]] = [
        (instant(2026, 1, 10), {"b": 1000, "c": saison}, {"b": 1000, "c": decembre}),
        (instant(2026, 3, 10), {"b": 1000, "c": decembre}, {"b": 1200, "c": decembre}),
    ]
    versions = versions_du_plan(brut, date(2025, 10, 1))
    assert versions[1].depuis == date(2025, 10, 1)  # la saison seule : la croissance continue
    assert versions[2].depuis == date(2026, 3, 10)  # une nouvelle base : elle repart


def test_l_histoire_du_plan_et_l_arret_sans_histoire() -> None:
    """Nouveau (CALCULS A § 4) : le plan d'avant le premier changement vaut depuis toujours ;
    une qualité arrêtée sans trace l'est au mois qui suit son dernier ordre, ou au premier
    changement s'il vient avant."""
    brut: list[tuple[datetime, dict[str, object], dict[str, object]]] = [
        (instant(2026, 5, 2, 9), {"b": 800}, {"b": 900, "a": False}),
    ]
    avant, apres = versions_du_plan(brut, None)
    assert (avant.quand, avant.base_mensuelle, avant.saisonnalite, avant.actif) == (
        None,
        800,
        UN,
        True,
    )
    assert (apres.quand, apres.base_mensuelle, apres.actif) == (instant(2026, 5, 2, 9), 900, False)
    assert versions_du_plan([], date(2025, 1, 1)) == []
    arret = arret_sans_histoire([VersionPlan(None, 1000, UN, actif=False)], date(2026, 12, 3))
    assert [(v.quand, v.actif) for v in arret] == [(None, True), (instant(2027, 1, 1), False)]
    tot = arret_sans_histoire(
        [VersionPlan(None, 1000, UN), VersionPlan(instant(2026, 9, 1), 500, UN)], date(2026, 12, 3)
    )
    assert [v.quand for v in tot] == [None, instant(2026, 9, 1), instant(2026, 9, 1)]
    assert [v.actif for v in tot] == [True, False, True]


def test_le_statut_d_un_bon_et_le_code_d_un_motif() -> None:
    """Nouveau (CALCULS A § 4) : un bon parti qui repasse par la direction ne redevient pas
    brouillon ; un motif se lit à son libellé ou à son code écrit."""
    assert statut_moteur("brouillon", None, []) == "Brouillon"
    assert statut_moteur("a_approuver", "BC-7", [True, True]) == "Confirmée"
    assert statut_moteur("a_approuver", "BC-7", [True, False]) == "Envoyée"
    assert statut_moteur("brouillon", "BC-7", []) == "Envoyée"
    assert statut_moteur("soldee", "BC-7", [False]) == "Soldée"
    assert code_motif("Refus après quarantaine") == "R3"
    assert code_motif("  Excédent de réception ") == "R5"
    assert code_motif("R2 — arrêt") == "R2"
    assert code_motif("autre chose") == "" and code_motif(None) == ""


def test_un_lot_recu_en_deux_camions_se_repartit_au_prorata() -> None:
    """Nouveau (CALCULS A § 4) : 60 kg rendus d'un lot pesé 100 + 300 kg : 15 et 45 ; la part
    d'une ligne ne dépasse pas ce qu'elle a apporté ; le reçu d'une ligne de bon est net."""
    lignes = [
        LigneRecue(1, commande_ligne_id=10, lot_id=7, quantite_pesee=100, qualite="Conforme"),
        LigneRecue(2, commande_ligne_id=11, lot_id=7, quantite_pesee=300, qualite="Conforme"),
        LigneRecue(3, commande_ligne_id=11, lot_id=8, quantite_pesee=50, qualite="Conforme"),
        LigneRecue(4, commande_ligne_id=None, lot_id=7, quantite_pesee=0, qualite="Conforme"),
    ]
    retours = au_prorata({7: 60.0}, lignes)
    assert retours == {1: pytest.approx(15), 2: pytest.approx(45), 4: 0.0}
    assert au_prorata({8: 80.0}, lignes) == {3: 50}
    assert recu_par_ligne(lignes, retours) == {10: pytest.approx(85), 11: pytest.approx(305)}


def test_les_entrees_s_apparient_a_leurs_lignes_de_reception() -> None:
    """Nouveau (CALCULS A § 4) : dans l'ordre, par réception et lot ; une entrée reprise sans
    réception par lot, date et poids ; une annulation reprend la ligne qu'elle défait."""
    jour = date(2026, 9, 1)
    lignes = [
        LigneDeReception(100, reception_id=1, lot_id=7, jour=jour, quantite_pesee=40),
        LigneDeReception(101, reception_id=1, lot_id=7, jour=jour, quantite_pesee=60),
        LigneDeReception(102, reception_id=2, lot_id=8, jour=jour, quantite_pesee=12.5),
    ]
    entrees = [
        EntreeLue(1, reception_id=1, lot_id=7, contrepasse_id=None, jour=jour, quantite=40),
        EntreeLue(2, reception_id=1, lot_id=7, contrepasse_id=None, jour=jour, quantite=60),
        EntreeLue(3, reception_id=None, lot_id=8, contrepasse_id=None, jour=jour, quantite=12.5),
        EntreeLue(4, reception_id=None, lot_id=8, contrepasse_id=None, jour=jour, quantite=12.5),
        EntreeLue(5, reception_id=1, lot_id=7, contrepasse_id=2, jour=jour, quantite=-60),
        EntreeLue(6, reception_id=1, lot_id=7, contrepasse_id=99, jour=jour, quantite=-1),
    ]
    assert lignes_des_receptions(lignes, entrees) == {1: 100, 2: 101, 3: 102, 5: 101}


def _ecriture(n: int, type_: str, quantite: float, magasin: str, **autres: Any) -> EcritureLue:
    return EcritureLue(n, type_, date(2026, 9, 1), "P", quantite, magasin, **autres)


def test_le_journal_de_la_base_devient_celui_du_moteur() -> None:
    """Nouveau (CALCULS A § 4) : quantité positive, signe porté par le type ; un transfert
    (deux écritures appariées) devient une ligne, de la source vers la destination."""
    ecritures = [
        _ecriture(1, "RECEPTION", 100, "MAG", prix=2.0, devise="", lot="L", cours=10.5),
        _ecriture(2, "TRANSFERT", 30, "QUA", paire=9),
        _ecriture(3, "SORTIE", -20, "MAG", numero_of="OF-1"),
        _ecriture(4, "TRANSFERT", -30, "MAG", paire=9),
        _ecriture(5, "RETOUR_FOURNISSEUR", -5, "MAG", motif="Bobines endommagées"),
        _ecriture(6, "SORTIE", 20, "MAG", contrepasse_id=3),
    ]
    journal = journal_du_moteur(ecritures)
    assert [
        (m.id, m.type, m.quantite, m.magasin_source, m.magasin_destination) for m in journal
    ] == [
        (1, "ENTREE_RECEPTION", 100, "", "MAG"),
        (3, "SORTIE_PROD", 20, "MAG", ""),
        (4, "TRANSFERT_MAGASIN", 30, "MAG", "QUA"),
        (5, "RETOUR_FOURNISSEUR", 5, "MAG", ""),
        (6, "SORTIE_PROD", -20, "MAG", ""),
    ]
    entree = journal[0]
    assert (entree.devise, entree.total_devise, entree.cours, entree.lot_fournisseur) == (
        "MAD",
        200,
        10.5,
        "L",
    )
    assert journal[3].motif_retour == "R6" and journal[4].contrepasse_id == 3
    assert journal[4].quantite_signee == 20  # l'annulation d'une sortie rend la matière
