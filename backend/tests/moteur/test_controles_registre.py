"""Le registre des contrôles, transverse : 38 contrôles dans l'ordre numérique, gravités,
garantis, liens, textes, colonnes déclarées avec leur unité, synthèse, détail jamais tronqué."""

from __future__ import annotations

from datetime import date

import pytest

from gestion_mp_pro.calcul.controles import (
    COLONNES,
    REGISTRE,
    Contexte,
    Synthese,
    controler,
    synthese,
)
from gestion_mp_pro.calcul.controles.base import colonne, controle
from gestion_mp_pro.calcul.controles.textes import HORS_SAISIE, QUOI_FAIRE
from gestion_mp_pro.calcul.modele import Article, Donnees, LigneRecette, Mouvement, Qualite

JOUR = date(2026, 10, 8)
CODES = [f"C{n:02d}" for n in range(1, 39)]
BLOQUANTS = {"C01", "C05", "C09", "C10", "C11", "C12", "C16", "C20", "C21", "C27", "C37"}
INFORMATIONS = {"C07", "C17", "C18", "C19", "C30", "C32", "C33"}
GARANTIS_BASE = {"C09", "C10", "C11", "C16", "C21"}
GARANTIS_SAISIE = {"C02", "C04", "C14", "C24", "C26", "C31", "C32"}
LIENS = {
    "C01": "/qualites",
    "C02": "/sorties",
    "C03": "/operations?onglet=retour_machine",
    "C04": "/stock?onglet=mouvements",
    "C05": "/catalogue?onglet=matieres",
    "C06": "/commandes?filtre=retard",
    "C07": "/catalogue?onglet=matieres",
    "C08": "/receptions?onglet=pesees",
    "C09": "/catalogue?onglet=matieres",
    "C10": "/catalogue?onglet=fournisseurs",
    "C11": "/reglages?onglet=devises",
    "C12": "/stock?onglet=mouvements",
    "C13": "/plan-achat",
    "C14": "/stock?onglet=mouvements",
    "C15": "/catalogue?onglet=matieres",
    "C16": "/stock?onglet=mouvements",
    "C17": "/catalogue?onglet=matieres",
    "C18": "/stock",
    "C19": "/catalogue?onglet=fournisseurs",
    "C20": "/inventaire",
    "C21": "/catalogue?onglet=matieres",
    "C22": "/metiers",
    "C23": "/catalogue?onglet=matieres",
    "C24": "/metiers",
    "C25": "/sorties",
    "C26": "/stock?onglet=mouvements",
    "C27": "/stock?onglet=lots",
    "C28": "/importations",
    "C29": "/importations",
    "C30": "/receptions?onglet=bobines",
    "C31": "/sorties",
    "C32": "/sorties",
    "C33": "/catalogue?onglet=matieres",
    "C34": "/importations?onglet=rattacher",
    "C35": "/importations",
    "C36": "/importations",
    "C37": "/stock?onglet=mouvements",
    "C38": "/catalogue?onglet=matieres",
}


def test_trente_huit_controles_dans_l_ordre_numerique():
    resultats = controler(Donnees(), [], JOUR)
    assert [c.code for c in resultats] == CODES == sorted(REGISTRE)
    assert all(c.conforme and c.detail == [] for c in resultats)


def test_gravites_onze_bloquants_sept_informations():
    gravites = {code: d.gravite for code, d in REGISTRE.items()}
    assert {c for c, g in gravites.items() if g == "bloquant"} == BLOQUANTS
    assert {c for c, g in gravites.items() if g == "information"} == INFORMATIONS
    assert sum(1 for g in gravites.values() if g == "avertissement") == 20


def test_cinq_garantis_par_la_base_et_sept_par_la_saisie():
    resultats = controler(Donnees(), [], JOUR)
    assert {c.code for c in resultats if c.garanti} == GARANTIS_BASE | GARANTIS_SAISIE
    for c in resultats:
        if c.code in GARANTIS_SAISIE:
            assert c.garanti.endswith("(garanti par la saisie).")
        if c.code in GARANTIS_BASE:
            assert "base" in c.garanti or "clé" in c.garanti


def test_liens_vers_les_ecrans_pro():
    assert {code: d.lien for code, d in REGISTRE.items()} == LIENS
    assert {c.code: c.lien for c in controler(Donnees(), [], JOUR)} == LIENS


def test_quoi_faire_aux_titres_pro():
    assert set(QUOI_FAIRE) == set(CODES)
    assert all(texte.strip() for texte in QUOI_FAIRE.values())
    hors_saisie = {code for code, texte in QUOI_FAIRE.items() if texte == HORS_SAISIE}
    assert hors_saisie == {"C02", "C04", "C14", "C16", "C26", "C31", "C32"}
    assert not any("personne qui entretient" in t for t in QUOI_FAIRE.values())
    assert "l'administrateur technique" in QUOI_FAIRE["C12"]
    assert "l'administrateur technique" in HORS_SAISIE
    assert "Qualités et recettes › Recette" in QUOI_FAIRE["C01"]
    assert "« Suivre »" in QUOI_FAIRE["C27"] and "Traçabilité" not in QUOI_FAIRE["C27"]


def test_colonnes_libellees_et_typees():
    unites = {"kg", "m", "MAD", "%", "j", "date", "texte", "nombre"}
    for definition in REGISTRE.values():
        assert definition.colonnes, definition.code
        cles = [c.cle for c in definition.colonnes]
        assert len(cles) == len(set(cles))
        for c in definition.colonnes:
            assert c.libelle == COLONNES[c.cle] and c.unite in unites
    # Une seule échelle (P8-3) : tout écart relatif est une fraction, d'unité « % ».
    pourcents = {
        (code, c.cle) for code, d in REGISTRE.items() for c in d.colonnes if c.unite == "%"
    }
    assert pourcents == {("C08", "ecart"), ("C30", "ecart"), ("C35", "surcout"), ("C36", "ecart")}
    assert COLONNES["surcout"] == "Frais / marchandise (%)" and "surcout_pct" not in COLONNES
    assert "devise" in COLONNES and "unite" not in COLONNES


def test_un_code_ne_se_declare_qu_une_fois():
    with pytest.raises(ValueError, match="C01 déjà déclaré"):
        controle("C01", gravite="bloquant", lien="/", colonnes=(colonne("date", "date"),))(
            lambda ctx: ("", [])
        )


def test_contexte_juge_le_futur_jamais_avant_la_date():
    donnees = Donnees()
    ctx = Contexte.preparer(donnees, [], JOUR, aujourdhui=date(2026, 1, 1))
    assert ctx.aujourdhui == JOUR and ctx.complet is donnees
    autre = Donnees()
    ctx = Contexte.preparer(donnees, [], JOUR, autre, date(2026, 12, 1))
    assert ctx.aujourdhui == date(2026, 12, 1) and ctx.complet is autre


def test_synthese_chiffree():
    """C01 (bloquant), C07 (information) et C09 (garanti, bloquant) sonnent : C09 sonnant
    n'est plus garanti, il compte dans le total."""
    donnees = Donnees(
        articles=[
            Article("A", role_bom="Poil", fournisseur="F", prix_unite=5),
            Article("P", role_bom="Poil", fournisseur="F", prix_unite=-1),
        ],
        qualites=[Qualite("Q", poids={"Poil": 1.0})],
        recettes=[LigneRecette("Q", "A", 50)],
    )
    resultats = controler(donnees, [], JOUR)
    assert [c.code for c in resultats if not c.conforme] == ["C01", "C07", "C09"]
    assert synthese(resultats) == Synthese(
        total=27,
        conformes=24,
        garantis=11,
        anomalies=3,
        a_corriger=2,
        bloquants=2,
        score=24 / 27,
    )


def test_synthese_vide_score_un():
    assert synthese([]) == Synthese(0, 0, 0, 0, 0, 0, 1.0)


def test_detail_jamais_tronque():
    """Gestion MP coupait à 200 (C26 gardait les 200 dernières) : tout est rendu, dans
    l'ordre du journal."""
    mouvements = [
        Mouvement(date(2026, 1, 1 + n % 28), "SORTIE_PROD", f"R{n:03d}", 1) for n in range(250)
    ]
    resultats = {c.code: c for c in controler(Donnees(mouvements=mouvements), [], JOUR)}
    for code in ("C02", "C04", "C16", "C26"):
        assert resultats[code].anomalies == len(resultats[code].detail) == 250
    assert [x["reference"] for x in resultats["C26"].detail] == [m.reference for m in mouvements]
    assert resultats["C02"].detail[-1] == {"date": "2026-01-26", "reference": "R249"}
