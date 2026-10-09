"""Parité unitaire du moteur (lot S3, PLAN-DE-RECETTE-PRO § 7) : sur 20 jeux de `Donnees`
réels figés en JSON (`jeux/`), le moteur PRO rend exactement les sorties que le moteur de
Gestion MP a produites une fois (`essais/gestion_mp_calcul.py`, commit inscrit dans chaque
fichier attendu). Égalité exacte des nombres : aucune tolérance.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from moteur import jeux_outils as jeux
from moteur.sorties_pro import sorties_du_moteur

JEUX = jeux.noms_des_jeux()
COMMIT_GESTION_MP = "f18b445c7a641e2b614a8b9cb229fc64f00281ee"


def _par_code(controles: list[dict[str, Any]]) -> dict[str, Any]:
    """Les contrôles par code : Gestion MP les rangeait dans son ordre, PRO de C01 à C38."""
    return {c["code"]: c for c in controles}


def test_vingt_jeux_figes() -> None:
    assert len(JEUX) == 20
    assert JEUX[0].startswith("01-") and JEUX[-1].startswith("20-")


@pytest.mark.parametrize("nom", JEUX)
def test_le_moteur_pro_rend_les_sorties_de_gestion_mp(nom: str) -> None:
    entete, complet = jeux.relire_jeu(nom)
    attendu = jeux.attendu(nom)
    assert attendu["commit_gestion_mp"] == entete["commit_gestion_mp"] == COMMIT_GESTION_MP
    jour = date.fromisoformat(entete["jour"])
    aujourdhui = date.fromisoformat(entete["aujourdhui"])
    obtenu = jeux.comme_gestion_mp(jeux.propre(sorties_du_moteur(complet, jour, aujourdhui)))
    gestion_mp = attendu["sorties"]
    assert set(obtenu) == set(gestion_mp)
    gestion_mp["controles"] = _par_code(gestion_mp["controles"])
    obtenu["controles"] = _par_code(obtenu["controles"])
    ecarts = {
        section: jeux.differences(gestion_mp[section], obtenu[section])
        for section in sorted(gestion_mp)
    }
    assert {s: e for s, e in ecarts.items() if e} == {}


def test_une_difference_d_un_cheveu_se_voit() -> None:
    """Le comparateur ne tolère rien : 1e-12 d'écart, un booléen pour un entier, une clé de
    trop se voient."""
    assert jeux.differences({"x": 1.0}, {"x": 1.0 + 1e-12}) != []
    assert jeux.differences({"x": 1}, {"x": True}) != []
    assert jeux.differences({"x": 1}, {"x": 1, "y": 2}) != []
    assert jeux.differences([1.5, {"a": "b"}], [1.5, {"a": "b"}]) == []
