"""Reprise (lot R1) : chaque traduction de MODELE-DONNEES § 10.3, le journal rangé en tables
(§ 4), les pièces copiées, les compteurs et séquences, le vidage de l'activité (G-01).

La petite usine est reprise **une fois** pour tout le module (`reprise`), puis lue.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import shutil
import sys
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fabriques.reprise import (
    FICHIERS,
    PETITE_USINE,
    cible_migree,
    source_gestion_mp,
    supprimer_base,
)
from test_reprise import CIBLE, SOURCE, lire, reprendre, un

from gestion_mp_pro.modeles import metadata, tables_d_activite
from gestion_mp_pro.reprise import vidage
from gestion_mp_pro.reprise.activite_importations import plus_forts_restes
from gestion_mp_pro.reprise.execution import Resultat

RACINE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def reprise(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Resultat, Path]]:
    """La petite usine reprise dans une cible neuve ; rend le résultat et le dossier des pièces."""
    racine = tmp_path_factory.mktemp("pieces_traductions")
    for chemin, contenu in FICHIERS.items():
        (racine / "source" / chemin).parent.mkdir(parents=True, exist_ok=True)
        (racine / "source" / chemin).write_bytes(contenu)
    source_gestion_mp(SOURCE, PETITE_USINE)
    cible_migree(CIBLE)
    r = reprendre((racine / "source", racine / "cible"))
    assert r.reussie, r.rapport
    yield r, racine / "cible"
    supprimer_base(SOURCE)
    supprimer_base(CIBLE)


def valeurs(sql: str) -> dict[Any, Any]:
    """Les deux premières colonnes d'une requête en dictionnaire."""
    return {a: b for a, b in lire(sql)}


def test_mouvements(reprise: tuple[Resultat, Path]) -> None:
    # Prix gardé sur les entrées seulement ; cours 0 ou MAD → NULL ; quantité au gramme.
    m = {
        r[0]: r
        for r in lire(
            "SELECT id, prix, cours, document, reception_id, ordre_id,"
            " operation_id, inventaire_id, motif_id, quantite FROM mouvement"
        )
    }
    assert m[4][1] == 0 and m[5][1] == 0 and m[7][1] == 0  # sortie, annulation, transfert
    assert m[2][1] == Decimal("2.500000") and m[2][2] == Decimal("9.500000")
    assert m[3][2] is None and m[1][2] is None
    assert m[2][9] == Decimal("1000.000")
    # Entrée sans document_id : sa réception retrouvée par (lot, date) ; sortie → ordre.
    assert m[2][3] == "reception" and m[2][4] == 1
    assert m[4][3] == "ordre" and m[4][5] == 1
    assert m[7][3] == "operation" and m[7][6] == 1 and m[11][7] == 1
    motifs = valeurs("SELECT id, libelle FROM motif")
    assert motifs[m[9][8]] == "Excédent de réception"
    assert motifs[m[10][8]] == "Reliquat de fin d'ordre"
    assert motifs[m[11][8]] == "Écart d'inventaire"
    assert un("SELECT paire_id FROM mouvement WHERE id = 8") == 7
    assert un("SELECT contrepasse_id FROM mouvement WHERE id = 5") == 4
    assert "prix de sorties, transferts ou retours machine non repris" in reprise[0].rapport


def test_lots_soldes_et_documents(reprise: tuple[Resultat, Path]) -> None:
    lots = valeurs("SELECT numero, interne FROM lot")
    assert lots == {
        "L_001": False,
        "LOT-2026-0001": True,
        "J-1": False,
        "L-004": False,
        "L-005": False,
        "L-006": False,
    }
    assert un("SELECT poids_bobine_le FROM lot WHERE id = 1") == dt.date(2026, 9, 3)
    soldes = {(a, b): q for a, b, q in lire("SELECT lot_id, magasin_id, quantite FROM solde")}
    assert soldes == {
        (1, 1): Decimal("810.000"),
        (2, 1): Decimal("100.000"),
        (3, 1): Decimal("130.000"),
        (3, 2): Decimal("45.000"),
        (4, 1): Decimal("40.000"),
        (5, 1): Decimal("30.000"),
        (6, 1): Decimal("20.000"),
    }
    # Brouillons numérotés : numéro retiré, gardé au compteur.
    assert un("SELECT numero FROM commande WHERE id = 3") is None
    assert un("SELECT numero FROM reception WHERE id = 3") is None
    assert un("SELECT numero FROM ordre WHERE id = 2") is None
    compteurs = {(s, a): n for s, a, n in lire("SELECT serie, annee, dernier FROM compteur")}
    assert compteurs[("BC", 2026)] == 3 and compteurs[("OF", 2026)] == 2
    assert compteurs[("LOT", 2026)] == 1 and compteurs[("DOS", 2026)] == 1
    # Ordre validé sans date : la fin de son jour ; prévu figé par matière.
    valide = un("SELECT valide_le AT TIME ZONE 'Africa/Casablanca' FROM ordre WHERE id = 1")
    assert valide.date() == dt.date(2026, 9, 10) and valide.hour == 23
    assert lire("SELECT matiere_id, kg_hors_perte FROM ordre_prevu") == [(1, Decimal("300.000"))]
    assert un("SELECT taux_perte_fige FROM ordre WHERE id = 1") == Decimal("0.020000")
    assert un("SELECT m2 FROM ordre_qualite") == Decimal("150.000")


def test_achats_et_receptions(reprise: tuple[Resultat, Path]) -> None:
    c1 = lire("SELECT cours, montant_approuve, solde_origine FROM commande WHERE id = 1")[0]
    assert c1 == (None, Decimal("23750.00"), None)
    assert un("SELECT solde_origine FROM commande WHERE id = 2") == "manuel"
    assert un("SELECT confirme_le IS NOT NULL FROM commande_ligne WHERE id = 1")
    assert un("SELECT montant_reference FROM commande_version") == Decimal("2500.00")
    assert un("SELECT count(*) FROM commande_version_ligne") == 1
    decisions = lire(
        "SELECT decision, motif, montant_avant, montant_apres FROM commande_decision ORDER BY quand"
    )
    assert decisions[0][:2] == ("renvoi", "trop cher, renégocier")
    assert decisions[1][2:] == (Decimal("20000.00"), Decimal("23750.00"))
    assert decisions[2] == ("approbation", "23 750 MAD approuvés", None, Decimal("23750.00"))
    assert un("SELECT montant FROM facture WHERE id = 2") is None
    r2 = lire("SELECT annulation_motif, annulee_le IS NOT NULL FROM reception WHERE id = 2")[0]
    assert r2 == ("camion refusé", True)
    rl = lire("SELECT lot_interne, lot_numero FROM reception_ligne WHERE id = 2")[0]
    assert rl == (True, "")
    assert lire("SELECT motif, issue FROM reclamation ORDER BY id") == [
        ("quantite_manquante", "avoir"),
        ("qualite", None),
    ]


def test_importations(reprise: tuple[Resultat, Path]) -> None:
    d = {r[0]: r[1:] for r in lire("SELECT numero, annee, rang, saisi_a_la_main FROM dossier")}
    assert d == {"01/26": (2026, 1, False), "ANC-X-OLD": (None, None, True)}
    lignes = lire("SELECT id, cours, cours_origine FROM dossier_ligne ORDER BY id")
    assert lignes == [(1, Decimal("9.500000"), "clos_au_jour"), (2, None, None)]
    assert un("SELECT count(*) FROM dossier_frais") == 2  # frais nul écarté
    parts = [p for (p,) in lire("SELECT montant FROM dossier_frais_part ORDER BY ligne_id")]
    assert sum(parts) == un("SELECT montant FROM dossier_frais WHERE id = 1") == Decimal("1000.01")
    assert plus_forts_restes(Decimal("1.00"), [1.0, 1.0, 1.0]) == [
        Decimal("0.34"),
        Decimal("0.33"),
        Decimal("0.33"),
    ]
    assert sum(plus_forts_restes(Decimal("-10.01"), [3.0, 7.0])) == Decimal("-10.01")


def test_referentiels(reprise: tuple[Resultat, Path]) -> None:
    f = valeurs("SELECT id, pays FROM fournisseur")
    assert f == {1: "TURQUIE", 2: "MAROC"}
    assert un("SELECT delai_jours FROM fournisseur WHERE id = 2") == 30
    assert valeurs("SELECT code, type FROM magasin") == {
        "Principal": "stock_courant",
        "Morocco": "stock_courant",
        "Quarantaine": "quarantaine",
    }
    assert lire("SELECT unite_achat, contenance_achat FROM matiere WHERE id = 2") == [
        ("kg", Decimal("1.000"))
    ]
    assert un("SELECT bobines_par_metre FROM metier") == Decimal("320.000")
    assert un("SELECT count(*) FROM metier_etage") == 2
    assert valeurs("SELECT code, cours FROM devise")["USD"] == Decimal("9.500000")
    assert un("SELECT count(*) FROM devise_cours") == 1
    assert valeurs("SELECT cle, valeur FROM parametre")["seuil_critique"] == "60"
    assert lire("SELECT avant, apres FROM parametre_historique ORDER BY quand") == [
        (None, "45"),
        ("45", "60"),
    ]
    assert "courriel_dernier_envoi" in reprise[0].rapport
    assert un("SELECT texte_recherche FROM matiere WHERE id = 1").startswith("pes rouge")


def test_versions_recette_et_plan(reprise: tuple[Resultat, Path]) -> None:
    v = {
        r[0]: r[1:]
        for r in lire("SELECT id, numero, origine, poids_connus, par_id FROM recette_version")
    }
    assert v == {2: (1, "reprise", False, None), 1: (2, "saisie", True, 1)}
    assert un("SELECT count(*) FROM recette_version_ligne WHERE version_id = 2") == 1
    assert un("SELECT count(*) FROM recette_version_poids WHERE version_id = 1") == 2
    plans = lire(
        "SELECT base_mensuelle, origine, valide_depuis, journal_id IS NOT NULL"
        " FROM plan_version ORDER BY valide_depuis"
    )
    assert [p[:2] for p in plans] == [
        (Decimal("1000.000"), "reprise"),
        (Decimal("1200.000"), "saisie"),
    ]
    assert plans[0][2].year == 2000 and all(p[3] for p in plans)
    decembre = lire(
        "SELECT s.coefficient FROM plan_version_saison s JOIN plan_version v"
        " ON v.id = s.version_id WHERE s.mois = 12 ORDER BY v.valide_depuis"
    )
    assert [c for (c,) in decembre] == [Decimal("1.0000"), Decimal("1.2000")]
    assert un("SELECT count(*) FROM montage_evenement") == 1
    assert un("SELECT count(*) FROM metier_etage WHERE monte_le IS NOT NULL") == 2


def test_journal_repris(reprise: tuple[Resultat, Path]) -> None:
    j = lire(
        "SELECT objet, objet_id, numero, utilisateur_nom FROM journal WHERE action = 'statut BC'"
    )
    assert j == [("commande", 2, "BC-2026-0002", "Démonstration")]
    assert un("SELECT count(*) FROM journal WHERE objet = 'reprise'") == 1


def test_pieces_copiees(reprise: tuple[Resultat, Path]) -> None:
    pieces = {r[0]: r[1:] for r in lire("SELECT id, chemin, empreinte, taille FROM piece_jointe")}
    assert set(pieces) == {1, 2}  # la 3ᵉ manque : signalée
    for chemin, empreinte, taille in pieces.values():
        fichier = reprise[1] / chemin
        assert hashlib.sha256(fichier.read_bytes()).hexdigest() == empreinte
        assert fichier.stat().st_size == taille
    assert "introuvable ou vide" in reprise[0].rapport


def test_sequences_recalees(reprise: tuple[Resultat, Path]) -> None:
    for table in ("mouvement", "matiere", "commande", "journal", "lot"):
        prochain = un(f"SELECT nextval(pg_get_serial_sequence('{table}', 'id'))")
        assert prochain > un(f"SELECT max(id) FROM {table}")  # noqa: S608


def test_chaque_table_est_activite_referentiel_ou_gardee() -> None:
    activite = set(tables_d_activite())
    referentiels = set(vidage.referentiels())
    assert not activite & referentiels
    assert activite | referentiels | vidage.GARDEES >= set(metadata.tables)
    assert "piece_jointe" in vidage.GARDEES and "journal" not in referentiels


def _outil() -> Any:
    """`outils/vider_activite.py` chargé comme module."""
    spec = importlib.util.spec_from_file_location(
        "vider_activite", RACINE / "outils" / "vider_activite.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["vider_activite"] = module
    spec.loader.exec_module(module)
    return module


def test_vider_l_activite_garde_les_referentiels(reprise: tuple[Resultat, Path]) -> None:
    outil = _outil()
    assert outil.main(["--base", CIBLE]) == 2  # sans confirmation, rien
    assert un("SELECT count(*) FROM mouvement") == 14
    matieres = lire("SELECT * FROM matiere ORDER BY id")
    retirees = outil.vider_la_base(CIBLE, sauvegarder=False)
    assert retirees["mouvement"] == 14 and retirees["piece_jointe"] == 1
    for table in tables_d_activite():
        assert un(f"SELECT count(*) FROM {table}") == 0  # noqa: S608
    assert lire("SELECT * FROM matiere ORDER BY id") == matieres
    assert un("SELECT count(*) FROM piece_jointe") == 1  # celle de la matière
    assert un("SELECT count(*) FROM plan_version") == 2
    assert un("SELECT count(*) FROM journal WHERE action = 'activité vidée'") == 1
    prochain = un("SELECT nextval(pg_get_serial_sequence('mouvement', 'id'))")
    assert prochain > 14  # les identifiants ne repartent pas à 1


def test_vider_sauvegarde_avant_vidage_puis_la_base_vide(
    reprise: tuple[Resultat, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Révision 0004 : la sauvegarde d'avant le vidage a son genre (« avant vidage », jamais
    purgée), celle d'après est la base vide de référence ; les deux vont au registre."""
    from gestion_mp_pro.modeles.enums import GenreSauvegarde

    outil = _outil()
    faites: list[GenreSauvegarde] = []
    inscrites: list[GenreSauvegarde] = []
    monkeypatch.setattr(
        outil.sauvegarde, "sauvegarder", lambda url, genre: faites.append(genre) or genre
    )
    monkeypatch.setattr(
        outil.sauvegarde, "inscrire", lambda c, fichier, genre, base: inscrites.append(genre)
    )
    outil.vider_la_base(CIBLE)
    attendu = [GenreSauvegarde.avant_vidage, GenreSauvegarde.reference_vide]
    assert faites == attendu and inscrites == attendu


@pytest.mark.skipif(shutil.which("pg_dump") is None, reason="outils PostgreSQL absents")
def test_sauvegarde_avant_reprise(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from gestion_mp_pro.config import reglages
    from gestion_mp_pro.modeles.enums import GenreSauvegarde
    from gestion_mp_pro.reprise import sauvegarde

    cible_migree(CIBLE)
    monkeypatch.setenv("GESTIONMPPRO_SAUVEGARDES", str(tmp_path))
    reglages.cache_clear()
    try:
        fichier = sauvegarde.sauvegarder(CIBLE, GenreSauvegarde.avant_reprise)
    finally:
        reglages.cache_clear()
    assert fichier.chemin.is_file() and fichier.tables > 0
    assert "avant-reprise" in fichier.chemin.name
