"""Suivi : factures dues, échéancier, photo du jour, état de livraison d'un bon
(`calcul/suivi.py`, `calcul/suivi_livraison.py`).

Les cas hérités reprennent les valeurs des essais de Gestion MP (partie calcul : la route lit
la base, ici les lignes sont écrites à la main).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

import pytest

from gestion_mp_pro.calcul.fournisseurs import PerformanceReception
from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Donnees,
    Fournisseur,
    LigneCommande,
    LigneReception,
    Reception,
)
from gestion_mp_pro.calcul.pilotage import cockpit
from gestion_mp_pro.calcul.suivi import (
    RAISON_AVOIR,
    RAISON_PLUS_DUE,
    Echeancier,
    FactureAPayer,
    FraisAPayer,
    PeseeFacturee,
    echeancier,
    en_mad,
    factures_dues,
    indicateurs_du_cockpit,
    photographier_indicateurs,
)
from gestion_mp_pro.calcul.suivi_livraison import (
    BonALivrer,
    LigneBon,
    commandes_en_retard,
    livre,
    statut_livraison,
)

AUJOURDHUI = date(2026, 10, 8)
TAUX = {"USD": 10.0, "EUR": 11.0}


def jour(decalage: int = 0) -> date:
    return AUJOURDHUI + timedelta(days=decalage)


def _echeancier(
    factures: list[FactureAPayer],
    pesees: list[PeseeFacturee] | None = None,
    frais: list[FraisAPayer] | None = None,
    **periode: Any,
) -> Echeancier:
    return echeancier(
        factures,
        frais or [],
        factures_dues(pesees or []),
        taux=TAUX,
        aujourdhui=AUJOURDHUI,
        **periode,
    )


# ── Factures dues ────────────────────────────────────────────────────────────


def test_factures_dues() -> None:
    dues = factures_dues(
        [
            PeseeFacturee(1, "validee", 200, 10),
            PeseeFacturee(1, "validee", 30, 10, qualite="refuse"),  # refusée : pas apportée
            PeseeFacturee(1, "brouillon", 50, 10),
            PeseeFacturee(2, "brouillon", 50, 10),  # que des brouillons : en attente
            PeseeFacturee(3, "annulee", 40, 10),  # toutes annulées : plus due
            PeseeFacturee(4, "annulee", 40, 10),
            PeseeFacturee(4, "brouillon", 40, 10),  # un brouillon reste : ni l'un ni l'autre
        ]
    )
    assert dues.apporte == {1: pytest.approx(2000)}
    assert dues.annulees == {3} and dues.en_attente == {2, 4}


def test_en_mad() -> None:
    assert en_mad(100, "MAD", TAUX) == 100 and en_mad(100, "USD", TAUX) == 1000
    assert en_mad(100, "GBP", TAUX) == 100  # devise inconnue : 1


# ── Échéancier ───────────────────────────────────────────────────────────────


def test_l_echeancier_suit_les_paiements() -> None:
    """Hérité : test_commandes_receptions.py::test_l_echeancier_suit_les_paiements (partie
    calcul : 200 kg × 10 MAD estimés, en retard ; réglée, elle sort de l'échu)."""
    f = FactureAPayer(1, "FOURN", "CR-F1", "MAD", echeance=jour(-10))
    pesees = [PeseeFacturee(1, "validee", 200, 10)]
    e = _echeancier([f], pesees)
    x = next(x for x in e.lignes if x.piece == "CR-F1")
    assert x.montant == pytest.approx(2000) and x.estime and x.en_retard
    echu = e.echu_mad
    f.payee_le = AUJOURDHUI
    e = _echeancier([f], pesees)
    assert "CR-F1" not in {x.piece for x in e.lignes}
    assert e.echu_mad == pytest.approx(echu - 2000)
    reglee = next(x for x in e.reglees if x.piece == "CR-F1")
    assert reglee.payee_le == AUJOURDHUI and reglee.date == jour(-10)
    f.payee_le = None  # le règlement s'annule : la facture redevient due
    assert "CR-F1" in {x.piece for x in _echeancier([f], pesees).lignes}


def test_une_facture_sans_date_est_a_dater() -> None:
    """Hérité : test_commandes_receptions.py::test_une_facture_sans_date_est_a_dater_et_s_exporte
    (partie calcul : 30 kg × 10 MAD, estimée, à dater)."""
    e = _echeancier(
        [FactureAPayer(1, "F", "CR-F-AD", "MAD")], [PeseeFacturee(1, "validee", 30, 10)]
    )
    x = next(x for x in e.a_dater if x.piece == "CR-F-AD")
    assert x.montant == pytest.approx(300) and x.estime and e.a_dater_mad == pytest.approx(300)
    # Rien d'apporté, rien de saisi : rien à dater.
    assert _echeancier([FactureAPayer(2, "F", "VIDE", "MAD")]).a_dater == []


def test_la_facture_d_une_reception_annulee_n_est_plus_due() -> None:
    """Hérité : test_commandes_receptions.py::test_la_facture_d_une_reception_annulee_n_est_plus
    _due (partie calcul)."""
    f = FactureAPayer(1, "F", "CR-F-AN", "MAD", montant=400, echeance=AUJOURDHUI)
    assert "CR-F-AN" in {
        x.piece for x in _echeancier([f], [PeseeFacturee(1, "validee", 40, 10)]).lignes
    }
    e = _echeancier([f], [PeseeFacturee(1, "annulee", 40, 10)])
    assert "CR-F-AN" not in {x.piece for x in e.lignes}
    x = next(x for x in e.ecartees if x.piece == "CR-F-AN")
    assert x.raison == RAISON_PLUS_DUE == "réception annulée : plus due"
    # Annulée sans montant (rien d'apporté) : elle n'apparaît nulle part.
    f.montant = None
    assert _echeancier([f], [PeseeFacturee(1, "annulee", 40, 10)]).ecartees == []


def test_une_facture_reglee_dont_la_reception_est_annulee_reste_visible() -> None:
    """Hérité : test_audit2_achats.py::test_une_facture_reglee_dont_la_reception_est_annulee
    _reste_visible (partie calcul : avoir à demander ; un brouillon n'est pas encore dû)."""
    reglee = FactureAPayer(1, "F", "A2-F-G7", "MAD", montant=6300, payee_le=AUJOURDHUI)
    brouillon = FactureAPayer(2, "F", "A2-F-G7B", "MAD", echeance=AUJOURDHUI)
    pesees = [PeseeFacturee(1, "annulee", 630, 10), PeseeFacturee(2, "brouillon", 50, 10)]
    e = _echeancier([reglee, brouillon], pesees)
    x = next(x for x in e.ecartees if x.piece == "A2-F-G7")
    assert "avoir" in (x.raison or "") and x.payee_le == AUJOURDHUI
    assert x.raison == RAISON_AVOIR == "réglée, réception annulée : avoir à demander"
    pieces = {x.piece for x in e.lignes + e.a_dater + e.ecartees + e.reglees}
    assert "A2-F-G7B" not in pieces


def test_l_echu_ne_depend_pas_du_filtre_de_dates() -> None:
    """Hérité : test_defauts_a.py::test_l_echu_ne_depend_pas_du_filtre_de_dates (partie calcul :
    500 MAD échus il y a 30 jours ; filtrés à partir d'aujourd'hui, toujours échus)."""
    f = FactureAPayer(1, "F", "DA-FAC-ECHU", "MAD", montant=500, echeance=jour(-30))
    tout = _echeancier([f])
    filtre = _echeancier([f], du=AUJOURDHUI)
    assert tout.echu_mad == 500 and filtre.echu_mad == pytest.approx(tout.echu_mad)
    assert filtre.echues == tout.echues == 1
    assert filtre.lignes == [] and filtre.total_mad == 0 and filtre.par_mois == {}


def test_les_frais_d_importation() -> None:
    """Hérité : test_defauts_b.py::test_frais_regle_ne_se_modifie_ni_ne_se_retire et
    test_importations_second_audit (frais du transitaire à dater, dossier clos) — partie
    calcul : un frais réglé reste réglé à son montant, un frais sans date est à dater."""
    frais = [
        FraisAPayer(1, "TRANSIT", "26/01", 1500, "TRANSIT DB", "T-9", payee_le=AUJOURDHUI),
        FraisAPayer(2, "TRANSIT", "26/02", 700, "TRANSIT OUBLIÉ"),
        FraisAPayer(3, "DD", "26/03", 1200, echeance=jour(5)),
        FraisAPayer(4, "PORT", "26/04", 0),  # rien à payer, rien à dater
    ]
    e = _echeancier([], frais=frais)
    assert [x.montant for x in e.reglees if x.tiers == "TRANSIT DB"] == [1500]
    assert [x.montant for x in e.a_dater if x.tiers == "TRANSIT OUBLIÉ"] == [700]
    x = e.lignes[0]
    assert (x.genre, x.tiers, x.piece, x.devise) == (
        "Frais d'importation (DD)",
        "—",
        "26/03",
        "MAD",
    )
    assert e.reglees[0].piece == "26/01 · T-9" and not x.estime and not x.en_retard
    assert e.total_mad == 1200 and e.a_dater_mad == 700


def test_tri_periode_par_mois_et_devises() -> None:
    factures = [
        FactureAPayer(1, "F", "USD-NOV", "USD", montant=100, echeance=date(2026, 11, 20)),
        FactureAPayer(2, "F", "MAD-OCT", "MAD", montant=50, echeance=date(2026, 10, 20)),
        FactureAPayer(3, "F", "EUR-NOV", "EUR", montant=10, echeance=date(2026, 11, 2)),
        FactureAPayer(4, "F", "MAD-DEC", "MAD", montant=1, echeance=date(2026, 12, 1)),
    ]
    e = _echeancier(factures)
    assert [x.piece for x in e.lignes] == ["MAD-OCT", "EUR-NOV", "USD-NOV", "MAD-DEC"]
    assert e.par_mois == {"2026-10": 50, "2026-11": 110 + 1000, "2026-12": 1}
    assert list(e.par_mois) == ["2026-10", "2026-11", "2026-12"]
    assert e.total_mad == pytest.approx(1161) and e.lignes[2].montant == 100
    e = _echeancier(factures, du=date(2026, 11, 1), au=date(2026, 11, 30))
    assert [x.piece for x in e.lignes] == ["EUR-NOV", "USD-NOV"] and e.total_mad == 1110


def test_les_reglees_par_date_decroissante_300_au_plus() -> None:
    factures = [
        FactureAPayer(i, "F", f"R{i}", "MAD", montant=1, payee_le=date(2026, 1, 1) + timedelta(i))
        for i in range(305)
    ]
    e = _echeancier(factures)
    assert len(e.reglees) == 300 and e.reglees[0].piece == "R304" and e.reglees[-1].piece == "R5"


def test_une_periode_rend_toutes_les_reglees_de_la_periode() -> None:
    """La période (`du`/`au`) borne les réglées par leur date de règlement, bornes incluses,
    sans plafond ; `reglees_au_plus=None` les rend toutes sans période. Les dues suivent toujours
    leur échéance, pas la période des réglées."""
    factures = [
        FactureAPayer(i, "F", f"R{i}", "MAD", montant=1, payee_le=date(2026, 1, 1) + timedelta(i))
        for i in range(305)
    ]
    frais = [FraisAPayer(1, "TRANSIT", "26/01", 50, piece="T", payee_le=date(2026, 1, 3))]
    due = FactureAPayer(900, "F", "DUE", "MAD", montant=7, echeance=date(2026, 1, 2))
    e = _echeancier([*factures, due], frais=frais, du=date(2026, 1, 2), au=date(2026, 1, 4))
    assert [x.piece for x in e.reglees] == ["R3", "R2", "26/01 · T", "R1"]
    assert [x.piece for x in e.lignes] == ["DUE"]
    tout = _echeancier(factures, frais=frais, du=date(2026, 1, 1))
    assert len(tout.reglees) == 306 and tout.reglees[-1].piece == "R0"
    assert len(_echeancier(factures, frais=frais, au=date(2026, 1, 1)).reglees) == 1
    assert len(_echeancier(factures, reglees_au_plus=None).reglees) == 305


# ── Photo du jour ────────────────────────────────────────────────────────────


def _perf(numero: str, jour_reception: date | None, otif: int | None) -> PerformanceReception:
    return PerformanceReception(numero, "X", jour_reception, otif, otif, 1, otif, 0, None)


def test_les_indicateurs_viennent_du_cockpit() -> None:
    """Hérité : test_audit2_pilotage.py::test_l_otif_moyen_n_a_qu_une_definition (partie
    calcul : la moyenne des réceptions notées, une réception une voix), sur douze mois."""
    c = cockpit(Donnees(), AUJOURDHUI, [])
    c.stock = replace(
        c.stock,
        valeur_mad=123.5,
        couverture_ponderee_jours=45.0,
        ruptures=1,
        critiques=2,
        urgents=3,
    )
    c.achats = replace(c.achats, budget_a_commander_mad=900.0, montant_bc_en_cours_mad=700.0)
    performances = [
        _perf("R1", jour(-10), 1),
        _perf("R2", jour(-20), 0),
        _perf("R3", jour(-30), 1),
        _perf("SANS NOTE", jour(-5), None),
        _perf("SANS DATE", None, 0),
        _perf("TROP VIEILLE", jour(-365), 0),
        _perf("DEMAIN", jour(1), 0),
    ]
    p = indicateurs_du_cockpit(c, performances, AUJOURDHUI)
    assert (p.valeur_stock_mad, p.couverture_jours) == (123.5, 45.0)
    assert (p.ruptures, p.critiques, p.urgents) == (1, 2, 3)
    assert (p.a_commander_mad, p.commandes_en_cours_mad) == (900.0, 700.0)
    assert p.otif_moyen == pytest.approx(2 / 3)
    assert indicateurs_du_cockpit(c, [], AUJOURDHUI).otif_moyen is None


def test_l_otif_moyen_ne_compte_que_les_receptions_notees() -> None:
    """Hérité : test_commandes_receptions.py::test_l_otif_moyen_ne_compte_que_les_receptions
    _notees (une réception hors commande n'est pas notée : l'OTIF moyen vaut 1)."""
    d0 = date(2026, 9, 5)
    donnees = Donnees(
        fournisseurs=[Fournisseur(nom="X", delai_jours=4)],
        articles=[Article(reference="R", fournisseur="X")],
        commandes=[
            Commande(
                numero="BC1",
                date_bc=d0,
                fournisseur="X",
                statut="Soldée",
                date_livraison_prevue=d0 + timedelta(days=10),
                lignes=[LigneCommande("BC1", "R", 100, 100)],
            )
        ],
        receptions=[
            Reception(
                "REC1",
                d0 + timedelta(days=5),
                "BC1",
                "X",
                statut="Validée",
                lignes=[
                    LigneReception("R", quantite_commandee=100, quantite_pesee=100, numero_bc="BC1")
                ],
            ),
            Reception(
                "REC2",
                d0 + timedelta(days=6),
                "",
                "X",
                statut="Validée",
                lignes=[LigneReception("R", quantite_pesee=50)],
            ),
        ],
    )
    p = photographier_indicateurs(donnees, AUJOURDHUI)
    assert p.otif_moyen == 1
    c = cockpit(donnees, AUJOURDHUI, [])
    assert p.a_commander_mad == c.achats.budget_a_commander_mad


# ── État de livraison d'un bon ───────────────────────────────────────────────


def _bon(statut: str = "envoyee", numero: str | None = "BC-1", **dates: date) -> BonALivrer:
    return BonALivrer(numero, statut, [LigneBon(1, 100), LigneBon(2, 50)], **dates)


@pytest.mark.parametrize(
    ("bon", "recu", "bloque", "attendu"),
    [
        (_bon(numero=None), {}, {}, ""),
        (_bon(), {1: 98, 2: 49}, {}, "🟢 Livré"),  # à 2 % près, ligne par ligne
        (_bon("soldee"), {1: 10}, {}, "⚫ Soldé"),
        (_bon("soldee"), {}, {}, "⚫ Soldé sans livraison"),
        (_bon("annulee"), {}, {}, "⚫ Annulé"),
        (_bon(), {1: 100, 2: 50}, {2: 10}, "🟡 Reçu sous réserve"),
        (_bon(eta=jour(-1)), {1: 10}, {}, "🟠 Partiel retard"),
        (_bon(eta=jour(-1)), {}, {}, "🔴 En retard"),
        (_bon(date_livraison_prevue=jour()), {1: 10}, {}, "🟡 En cours"),
        (_bon(), {}, {}, "⚪ Attendu"),  # aucune échéance connue
        (_bon(eta=jour(), date_livraison_prevue=jour(-9)), {}, {}, "⚪ Attendu"),  # l'ETA d'abord
    ],
)
def test_statut_livraison(
    bon: BonALivrer, recu: dict[int, float], bloque: dict[int, float], attendu: str
) -> None:
    assert statut_livraison(bon, recu, bloque, 0.02, jour=AUJOURDHUI) == attendu


def test_le_retard_tolere_et_le_delai_du_fournisseur() -> None:
    bon = _bon(date_commande=jour(-12))
    bon.delai_fournisseur = 10  # attendu il y a deux jours
    assert statut_livraison(bon, {}, {}, 0.02, jour=AUJOURDHUI) == "🔴 En retard"
    assert statut_livraison(bon, {}, {}, 0.02, jour=AUJOURDHUI, retard_tolere=2) == "⚪ Attendu"
    assert not livre(BonALivrer("V", "envoyee"), {}, 0.02)  # un bon sans ligne n'est pas livré


def test_commandes_en_retard_du_courriel() -> None:
    en_retard = _bon(eta=jour(-1))
    reserve = replace(_bon(eta=jour(-1)), numero="BC-2")
    brouillon = replace(_bon(eta=jour(-1)), numero=None, statut="brouillon")
    soldee = replace(_bon("soldee", eta=jour(-1)), numero="BC-3")
    a_approuver = replace(_bon("a_approuver", eta=jour(-1)), numero="BC-4")
    bons = [en_retard, reserve, brouillon, soldee, a_approuver]
    retards = commandes_en_retard(bons, {}, {}, 0.02, jour=AUJOURDHUI)
    assert [x.numero for x in retards] == ["BC-1", "BC-2", "BC-4"]
    # Tout est là, une part en quarantaine : « reçu sous réserve » n'est pas un retard.
    retards = commandes_en_retard([reserve], {1: 100, 2: 50}, {1: 5}, 0.02, jour=AUJOURDHUI)
    assert retards == []
