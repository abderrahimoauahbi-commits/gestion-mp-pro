"""Le comparateur avec Gestion MP en service (lot C1 ; ARCHITECTURE § 14.3).

Rapides (sans base) : le développement des dates, le refus de deux bases désynchronisées, le
saboteur qui pose ses quatre fautes et le fait qu'une faute posée **se voit** (aucune règle de
R2 ne l'excuse). Complet (`GESTIONMPPRO_ESSAIS_COMPLETS=1`, outils PostgreSQL et interpréteur
de Gestion MP) : la comparaison entière sur une copie de `gestion_mp` et de
`gestion_mp_comparaison`, « à corriger : 0 », et la même comparaison avec les fautes injectées
qui remonte « à corriger > 0 ». Aucune écriture dans les bases ni les dossiers de Gestion MP.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fabriques.exploitation import avec_outils_pg
from sqlalchemy.engine import make_url

from gestion_mp_pro.config import reglages

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend" / "essais"))
sys.path.insert(0, str(RACINE / "outils"))

import comparaison as comp  # noqa: E402
import comparaison_bases as cb  # noqa: E402
import comparer_avec_gestion_mp as outil  # noqa: E402
import parite_comparer as pc  # noqa: E402

AUJOURDHUI = "2026-10-08"


def test_developpe_les_dates() -> None:
    dates = outil.dates_de("aujourd-hui,fins-de-mois")
    assert dates[0] == AUJOURDHUI
    assert "2025-10-31" in dates and "2026-10-08" in dates
    assert len(dates) == len(set(dates))  # pas de doublon
    assert outil.dates_de("2026-01-31,2026-01-31") == ["2026-01-31"]
    assert outil.mois_de(["2026-01-31", "2026-02-28"]) == ["2026-01", "2026-02"]


def test_refuse_deux_bases_desynchronisees() -> None:
    with pytest.raises(cb.Desynchronisees, match="aucune reprise"):
        cb.verifier_synchronisation("abc", None)
    with pytest.raises(cb.Desynchronisees, match="désynchronisées"):
        cb.verifier_synchronisation("abc", "def")
    cb.verifier_synchronisation("abc", "abc")  # synchronisées : passe


def _sorties_fictives() -> dict[str, object]:
    """Des sorties de moteur minuscules portant une valeur de chaque section sabotée."""
    return {
        "cmup_par_reference": {"Bande": 10.0},
        "stock": [{"reference": "Bande", "stock_net": 100.0}],
        "controles": [{"code": "C01", "anomalies": 3, "detail": [{"x": 1}]}],
        "revient": {"01/25": [{"revient_mad": 500.0}]},
    }


def test_le_saboteur_pose_ses_quatre_fautes_et_elles_se_voient() -> None:
    avant = _sorties_fictives()
    apres = _sorties_fictives()
    fautes = comp.saboteur_essai(apres)
    assert len(fautes) == 4
    assert apres["cmup_par_reference"]["Bande"] == pytest.approx(11.0)  # ×1,1
    assert apres["stock"][0]["stock_net"] == 101.0  # +1 kg
    assert apres["controles"][0]["anomalies"] == 0  # muet
    assert apres["revient"]["01/25"][0]["revient_mad"] == 1500.0  # +1000
    # chaque faute est un écart que la comparaison voit (aucune tolérance ne l'absorbe)
    assert pc.comparer(avant, apres).ecarts


def test_le_saboteur_ne_pose_rien_sur_une_base_sans_activite() -> None:
    vide = {"cmup_par_reference": {}, "stock": [], "controles": [], "revient": {}}
    assert comp.saboteur_essai(vide) == []


# ── Complet : des copies de Gestion MP ─────────────────────────────────────────────────


def _args(source: str, prefixe: str, sensibilite: bool) -> object:
    return outil.analyser(
        [
            "--source",
            source,
            "--mode",
            "moteurs",
            "--dates",
            AUJOURDHUI,
            "--prefixe",
            prefixe,
            *(["--prouver-sensibilite"] if sensibilite else []),
        ]  # fmt: skip
    )


@pytest.mark.complet
@avec_outils_pg
@pytest.mark.skipif(not reglages().essais_complets, reason="GESTIONMPPRO_ESSAIS_COMPLETS=1")
@pytest.mark.parametrize("source", ["gestion_mp", "gestion_mp_comparaison"])
def test_comparaison_reelle_zero_ecart(source: str, tmp_path: Path) -> None:
    """Sur une copie de la base de Gestion MP, à corriger 0 ; avec les fautes injectées, > 0."""
    import parite_bases as pb

    nom = (make_url(os.environ["GESTIONMPPRO_BASE"]).database or "").removesuffix("_essai")
    prefixe = f"{nom}_cmp"
    bases = pb.Bases(prefixe=prefixe)
    try:
        r = outil.comparer(_args(source, prefixe, sensibilite=False), tmp_path / "net")
        assert r.a_corriger == 0, r.details[:10]
        assert r.comparees > 0 and r.prep.source_intacte
        if source == "gestion_mp_comparaison":
            sabote = outil.comparer(_args(source, prefixe, sensibilite=True), tmp_path / "faute")
            assert sabote.fautes and sabote.a_corriger >= len(sabote.fautes)
    finally:
        pb.nettoyer(bases)
