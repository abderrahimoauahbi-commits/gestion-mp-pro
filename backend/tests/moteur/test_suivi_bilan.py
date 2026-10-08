"""Bilan matières du mois (`calcul/suivi_bilan.py`).

Le journal de la base (quantités signées, types de la base) et celui du moteur (même n°,
quantité au signe du type, comme `depot._journal`) sont écrits côte à côte.
"""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.modele import (
    Article,
    Commande,
    Donnees,
    Fournisseur,
    LigneCommande,
    LigneReception,
    LigneRecette,
    Mouvement,
    OrdreFabrication,
    PlanQualite,
    Qualite,
    Reception,
)
from gestion_mp_pro.calcul.production import ConsommationOrdre
from gestion_mp_pro.calcul.suivi_bilan import (
    BilanMois,
    CommandeBase,
    FabricationBase,
    MouvementBase,
    ReceptionBase,
    bilan,
    mois_du_bilan,
)

AUJOURDHUI = date(2026, 10, 8)
MOTEUR = {
    "OUVERTURE": ("STOCK_INITIAL", 1),
    "RECEPTION": ("ENTREE_RECEPTION", 1),
    "SORTIE": ("SORTIE_PROD", -1),
    "RETOUR_MACHINE": ("RETOUR_PRODUCTION", 1),
    "RETOUR_FOURNISSEUR": ("RETOUR_FOURNISSEUR", -1),
    "AJUSTEMENT": ("AJUSTEMENT_INVENTAIRE", 1),
    "TRANSFERT": ("TRANSFERT_MAGASIN", 0),
}
Ecriture = tuple[int, str, float, date, int | None, float]
"""(n°, type de la base, quantité signée, date, n° annulé, prix MAD)."""

JOURNAL: list[Ecriture] = [
    (1, "OUVERTURE", 1000, date(2026, 8, 10), None, 10),
    (2, "RECEPTION", 500, date(2026, 9, 5), None, 12),
    (3, "SORTIE", -300, date(2026, 9, 10), None, 0),
    (4, "RETOUR_MACHINE", 50, date(2026, 9, 12), None, 0),
    (5, "RECEPTION", 200, date(2026, 9, 15), None, 20),  # reçue puis annulée dans le mois
    (6, "RECEPTION", -200, date(2026, 9, 15), 5, 20),
    (7, "SORTIE", -100, date(2026, 9, 20), None, 0),  # sortie annulée
    (8, "SORTIE", 100, date(2026, 9, 20), 7, 0),
    (9, "AJUSTEMENT", -20, date(2026, 9, 25), None, 0),
    (10, "TRANSFERT", -100, date(2026, 9, 26), None, 0),
    (11, "TRANSFERT", 100, date(2026, 9, 26), None, 0),
    (12, "RETOUR_FOURNISSEUR", -50, date(2026, 9, 28), None, 0),
    (13, "SORTIE", -10, date(2026, 10, 2), None, 0),  # le mois suivant
]


def _base(journal: list[Ecriture]) -> list[MouvementBase]:
    return [MouvementBase(i, t, q, j, a) for i, t, q, j, a, _ in journal]


def _moteur(journal: list[Ecriture], reference: str) -> list[Mouvement]:
    """Le journal du moteur : un transfert (une paire en base) n'est qu'une écriture."""
    resultat = []
    for i, t, q, j, a, prix in journal:
        code, signe = MOTEUR[t]
        if t == "TRANSFERT" and q > 0:
            continue
        quantite = abs(q) if signe == 0 else q * signe
        resultat.append(Mouvement(j, code, reference, quantite, prix, id=i, contrepasse_id=a))
    return resultat


def _bilan(donnees: Donnees, journal: list[Ecriture], mois: int = 9, **autres: object) -> BilanMois:
    entrees: dict[str, object] = {
        "fabrications": [],
        "commandes": [],
        "receptions": [],
        "ordres": [],
    } | autres
    return bilan(
        donnees,
        annee=2026,
        mois=mois,
        aujourdhui=AUJOURDHUI,
        mouvements=_base(journal),
        **entrees,
    )


def _donnees(journal: list[Ecriture] = JOURNAL) -> Donnees:
    return Donnees(
        articles=[Article(reference="B FIL", prix_unite=10)],
        mouvements=_moteur(journal, "B FIL"),
    )


def test_mois_invalide() -> None:
    """Hérité : test_defauts_e.py::test_bilan_mois_invalide_422 (partie calcul)."""
    for annee, mois in ((2026, 13), (0, 0), (2026, 11), (2101, 1)):
        with pytest.raises(ValueError, match="Mois invalide : AAAA-MM, pas dans le futur."):
            mois_du_bilan(annee, mois, AUJOURDHUI)
    assert mois_du_bilan(2026, 10, AUJOURDHUI) == date(2026, 10, 1)


def test_les_flux_du_mois_en_kilos() -> None:
    """Hérité : test_defauts_e.py::test_bilan_reception_annulee_hors_kilos et
    test_audit2_pilotage.py::test_le_bilan_detaille_les_annulations_en_kilos (partie calcul :
    une réception annulée dans le mois n'est ni une entrée ni une annulation ; une sortie
    annulée a sa ligne à part, pas des sorties négatives ; les transferts ne sont pas des
    flux)."""
    b = _bilan(_donnees(), JOURNAL)
    assert b.mois == "09/2026"
    assert (b.stock_debut_kg, b.stock_fin_kg) == (1000, 1180)
    assert (b.entrees_kg, b.sorties_kg, b.retours_machine_kg) == (500, 400, 50)
    assert (b.retours_fournisseur_kg, b.ajustements_kg, b.ouvertures_kg) == (50, -20, 0)
    assert b.annulations_kg == 100 and b.annulations == {"SORTIE": 100}
    # L'équation affichée, vraie par construction.
    assert b.stock_fin_kg == (
        b.stock_debut_kg
        + b.entrees_kg
        + b.ouvertures_kg
        - b.sorties_kg
        + b.retours_machine_kg
        - b.retours_fournisseur_kg
        + b.ajustements_kg
        + b.annulations_kg
    )
    # Sans la réception annulée, rien ne change.
    sans = [x for x in JOURNAL if x[0] not in (5, 6)]
    a = _bilan(_donnees(sans), sans)
    assert (a.entrees_kg, a.annulations_kg, a.stock_fin_kg) == (500, 100, 1180)


def test_le_bilan_du_mois_est_en_kilos() -> None:
    """Hérité : test_matieres_au_metre.py::test_le_bilan_du_mois_est_en_kilos (partie calcul :
    le stock de fin du mois en cours = Σ de toutes les quantités du journal)."""
    b = _bilan(_donnees(), JOURNAL, mois=10)
    assert b.stock_fin_kg == pytest.approx(sum(x[2] for x in JOURNAL))
    assert b.sorties_kg == 10 and b.stock_debut_kg == 1180


def test_le_bilan_s_equilibre_en_valeur() -> None:
    """Hérité : test_defauts_e.py::test_bilan_equilibre_en_valeur (partie calcul : début +
    entrées − consommation + autres = fin, l'entrée à son coût d'écriture)."""
    b = _bilan(_donnees(), JOURNAL)
    assert b.valeur_debut_mad == pytest.approx(10_000)
    assert b.valeur_entrees_mad == pytest.approx(500 * 12)
    moyen = 16_000 / 1500
    assert b.consommation_mad == pytest.approx(300 * moyen - 50 * moyen)
    assert b.valeur_autres_mad == pytest.approx(-20 * moyen - 50 * moyen)
    calcule = b.valeur_debut_mad + b.valeur_entrees_mad - b.consommation_mad + b.valeur_autres_mad
    assert calcule == pytest.approx(b.valeur_fin_mad, abs=1)
    assert b.ecart_valorisation_mad == pytest.approx(b.valeur_fin_mad - calcule)
    # Un mois passé : le montage des métiers n'a pas d'historique.
    assert (b.stock_machine_kg, b.valeur_machine_mad) == (0.0, 0.0)


def test_les_ruptures_d_un_mois_passe_se_lisent_a_la_fin_du_mois() -> None:
    """Hérité : test_valorisation.py::test_api_le_bilan_d_un_mois_passe_compte_ses_ruptures_a_la
    _fin_du_mois (partie calcul : le stock ouvert aujourd'hui n'y change rien)."""
    planifie = Donnees(
        articles=[Article(reference="VALO BILAN", role_bom="Poil", prix_unite=10)],
        qualites=[Qualite("VALOB", poids={"Poil": 1.0})],
        recettes=[LigneRecette("VALOB", "VALO BILAN", 100)],
        plan=[PlanQualite("VALOB", 1000)],
    )
    avant = _bilan(planifie, []).ruptures
    assert avant == 1
    ouverture: list[Ecriture] = [(1, "OUVERTURE", 1_000_000, AUJOURDHUI, None, 10)]
    planifie.mouvements = _moteur(ouverture, "VALO BILAN")
    assert _bilan(planifie, ouverture).ruptures == avant
    assert _bilan(planifie, ouverture, mois=10).ruptures == 0


def _ordre(numero: str, debut: date, ecart_relatif: float | None) -> ConsommationOrdre:
    return ConsommationOrdre(
        numero, 0, 0, [], [], debut, debut, 0, [], "", 0, "", 0, None, None, ecart_relatif
    )


SEPT = date(2026, 9, 10)


def _donnees_du_mois() -> Donnees:
    """Une réception notée parfaite (BC1) et une hors commande ; dix ordres validés."""
    sept = SEPT
    return Donnees(
        fournisseurs=[Fournisseur(nom="X", delai_jours=4)],
        articles=[Article(reference="R", fournisseur="X")],
        commandes=[
            Commande(
                numero="BC1",
                date_bc=date(2026, 9, 1),
                fournisseur="X",
                statut="Soldée",
                date_livraison_prevue=date(2026, 9, 11),
                lignes=[LigneCommande("BC1", "R", 100, 100)],
            )
        ],
        receptions=[
            Reception(
                "REC1",
                sept,
                "BC1",
                "X",
                statut="Validée",
                lignes=[
                    LigneReception("R", quantite_commandee=100, quantite_pesee=100, numero_bc="BC1")
                ],
            ),
            Reception(
                "REC2",
                sept,
                "",
                "X",
                statut="Validée",
                lignes=[LigneReception("R", quantite_pesee=50)],
            ),
        ],
        ordres=[OrdreFabrication(f"OF{i}", sept) for i in range(10)],
    )


def test_l_activite_du_mois() -> None:
    """Hérité : test_defauts_e.py::test_bilan_commandes_hors_annulees (partie calcul : un bon
    annulé n'engage rien) ; m², réceptions, OTIF et les 8 plus grands écarts d'ordres."""
    sept = SEPT
    donnees = _donnees_du_mois()
    ecarts = [0.01, -0.5, 0.2, -0.03, 0.4, 0.05, -0.06, 0.07, 0.9]
    ordres = [_ordre(f"OF{i}", sept, e) for i, e in enumerate(ecarts)]
    ordres += [
        _ordre("OF9", sept, None),  # sans prévu : compté, pas classé
        _ordre("NON VALIDE", sept, 5.0),
        _ordre("OF8", date(2026, 10, 1), 9.0),  # première sortie le mois suivant
    ]
    b = _bilan(
        donnees,
        [],
        fabrications=[
            FabricationBase("Q2", 30, "valide", sept),
            FabricationBase("Q1", 10, "valide", sept),
            FabricationBase("Q1", 5, "valide", sept),
            FabricationBase("Q1", 99, "brouillon", sept),
            FabricationBase("Q1", 99, "valide", date(2026, 10, 1)),
        ],
        commandes=[
            CommandeBase("BC1", sept, "envoyee"),
            CommandeBase("BC2", sept, "annulee"),
            CommandeBase(None, sept, "brouillon"),
            CommandeBase("BC3", None, "envoyee"),
            CommandeBase("BC4", date(2026, 8, 31), "soldee"),
        ],
        receptions=[
            ReceptionBase("validee", sept),
            ReceptionBase("brouillon", sept),
            ReceptionBase("validee", date(2026, 10, 1)),
        ],
        ordres=ordres,
    )
    assert b.m2_par_qualite == {"Q1": 15, "Q2": 30} and list(b.m2_par_qualite) == ["Q1", "Q2"]
    assert b.m2_total == 45 and b.commandes == 1 and b.receptions == 1
    assert b.otif == 1 and b.receptions_notees == 1
    assert b.ordres == 10
    assert [x.numero_of for x in b.ecarts_ordres] == [
        "OF8",
        "OF1",
        "OF4",
        "OF2",
        "OF7",
        "OF6",
        "OF5",
        "OF3",
    ]
