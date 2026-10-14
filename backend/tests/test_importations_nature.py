"""Audit n° 2 (14/10/2026) — les repères du dossier suivent la **nature** des postes.

« Droits attendus », « TVA attendue » et « valeur en douane » lisent `nature` (`droits`, `tpi`,
`tva`, `fret`, `assurance`) et `entre_valeur_douane` du référentiel des postes, comme l'écran
(base du taux) et le vérificateur indépendant — plus les codes DD / TPI / TVA / FRET / ASSUR en
dur. Un poste sur mesure de même nature compte désormais ; sur les cinq postes système le
résultat ne change pas (parité conservée).
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.importations import Import, frais, geste, invalider, ouvrir
from fabriques.receptions import ok
from fabriques.referentiels import unique
from fastapi.testclient import TestClient

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.calcul.importations import tva_attendue

MARCHANDISE = 60_000.0
"""Deux fils (2 000 et 4 000 en devise) au cours payé de 10."""


def _dossier(achats: TestClient, nom: str) -> dict[str, Any]:
    """Un dossier de 60 000 MAD de marchandise, au cours payé de 10."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, nom, [("ROUGE", f"{nom}-R", 1000, 2.0), ("NOIR", f"{nom}-N", 1000, 4.0)])
    d = ouvrir(achats, imp.f(nom))
    return ok(  # type: ignore[no-any-return]
        achats.put(f"/api/dossiers/{d['id']}/cours", json={"version": d["version"], "cours": 10})
    )


def _poste(direction: TestClient, prefixe: str, nature: str, **champs: Any) -> str:
    """Un poste neuf (non système) de cette nature, créé par la direction ; son code."""
    code = unique(prefixe).replace("-", "_").upper()[:16]
    corps = {"code": code, "libelle": f"Poste {code}", "nature": nature, **champs}
    assert ok(direction.post("/api/postes-frais", json=corps), 201)["nature"] == nature
    return code


def _attendue(d: dict[str, Any], douane: float, droits: float, tpi: float | None = None) -> float:
    """TVA attendue = taux × (valeur en douane + droits + TPI saisie, sinon taux TPI × douane)."""
    tpi = douane * d["taux_tpi_import"] if tpi is None else tpi
    return float((douane + droits + tpi) * d["taux_tva_import"])


def test_un_poste_neuf_de_nature_droits_compte_dans_les_droits(
    achats: TestClient, direction: TestClient
) -> None:
    """DD 1 000 + un poste sur mesure « droits » de 10 000 : les droits saisis font 11 000 et la
    TVA attendue les compte (avant l'audit n° 2 : 1 000, et une TVA attendue sans les 10 000)."""
    ddx = _poste(direction, "DDX", "droits")
    d = frais(achats, _dossier(achats, "NAT-DD"), "DD", 1000)
    assert d["droits_mad"] == pytest.approx(1000)
    assert d["tva_attendue_mad"] == pytest.approx(_attendue(d, MARCHANDISE, 1000))
    d = frais(achats, d, ddx, 10_000)
    assert d["droits_mad"] == pytest.approx(11_000)
    assert d["tva_attendue_mad"] == pytest.approx(_attendue(d, MARCHANDISE, 11_000))
    assert d["revient_mad"] == pytest.approx(MARCHANDISE + 11_000)


def test_un_poste_neuf_de_nature_tva_est_la_tva_de_la_douane(
    achats: TestClient, direction: TestClient
) -> None:
    """Une TVA saisie sur un poste sur mesure de nature « tva » (récupérable) est la TVA de la
    douane : comparée à l'attendue (ni « Aucune TVA saisie », ni C29 quand elle est juste), hors
    du coût."""
    tvax = _poste(direction, "TVAX", "tva", recuperable=True)
    d = frais(achats, _dossier(achats, "NAT-TVA"), "DD", 1000)
    attendue = _attendue(d, MARCHANDISE, 1000)
    d = frais(achats, d, tvax, round(attendue, 2))
    assert d["tva_saisie_mad"] == pytest.approx(attendue, abs=0.01)
    assert d["tva_ecart_mad"] is None and "TVA ≠ attendue" not in d["a_verifier"]
    assert "Aucune TVA saisie." not in d["alertes"]
    assert d["revient_mad"] == pytest.approx(MARCHANDISE + 1000)
    assert d["tva_mad"] == pytest.approx(attendue, abs=0.01)
    invalider()
    c29 = ok(achats.get("/api/controles/C29", params={"q": d["numero"]}))["elements"]
    assert [x for x in c29 if x["dossier"] == d["numero"]] == []
    d = frais(achats, d, tvax, 5000)  # 5 000 de plus : la TVA saisie s'éloigne de l'attendue
    assert d["tva_ecart_mad"] == pytest.approx(5000, abs=0.01)
    assert "TVA ≠ attendue" in d["a_verifier"]
    invalider()
    c29 = ok(achats.get("/api/controles/C29", params={"q": d["numero"]}))["elements"]
    assert [x["dossier"] for x in c29 if x["dossier"] == d["numero"]] == [d["numero"]]


def test_un_poste_neuf_qui_entre_dans_la_valeur_en_douane(
    achats: TestClient, direction: TestClient
) -> None:
    """Un poste sur mesure de nature « fret », réglé « entre dans la valeur en douane » : la
    valeur en douane de chaque marchandise (base du taux à l'écran) et la TVA attendue le
    comptent, comme FRET ; un poste « autre » hors valeur en douane ne compte pas."""
    fretx = _poste(direction, "FRETX", "fret", entre_valeur_douane=True)
    autre = _poste(direction, "MANUT", "autre")
    d = frais(achats, _dossier(achats, "NAT-FRET"), fretx, 6000)
    d = frais(achats, d, autre, 900)
    assert sum(x["valeur_douane_mad"] for x in d["lignes"]) == pytest.approx(MARCHANDISE + 6000)
    assert d["tva_attendue_mad"] == pytest.approx(_attendue(d, MARCHANDISE + 6000, 0))
    assert d["revient_mad"] == pytest.approx(MARCHANDISE + 6900)


def test_tpi_sur_mesure_remplace_la_tpi_calculee(achats: TestClient, direction: TestClient) -> None:
    """Une TPI saisie sur un poste de nature « tpi » se prend telle quelle dans la TVA attendue
    (sinon elle se calcule au taux réglé)."""
    tpix = _poste(direction, "TPIX", "tpi")
    d = frais(achats, _dossier(achats, "NAT-TPI"), tpix, 99)
    assert d["tva_attendue_mad"] == pytest.approx(_attendue(d, MARCHANDISE, 0, tpi=99))


def test_les_cinq_postes_systeme_donnent_le_meme_resultat_par_le_code_ou_la_nature() -> None:
    """Parité : le moteur, nourri par les codes seuls (jeux d'origine) ou par la nature des
    cinq postes système, calcule la même TVA attendue au centime."""
    p = c.Parametres()
    lignes = [c.LigneImport(1, "A", 1000, 6000, "USD", 10)]
    codes = [
        c.ChargeImport("DD", 1500),
        c.ChargeImport("TPI", 150),
        c.ChargeImport("TVA", 14_000, recuperable_poste=True),
        c.ChargeImport("FRET", 3000),
        c.ChargeImport("ASSUR", 300),
        c.ChargeImport("TRANSIT", 800),
    ]
    natures = {
        "DD": ("droits", False),
        "TPI": ("tpi", False),
        "TVA": ("tva", False),
        "FRET": ("fret", True),
        "ASSUR": ("assurance", True),
        "TRANSIT": ("autre", False),
    }
    avec = [
        c.ChargeImport(
            x.poste,
            x.montant,
            recuperable_poste=x.recuperable_poste,
            nature=natures[x.poste][0],
            entre_valeur_douane=natures[x.poste][1],
        )
        for x in codes
    ]
    par_code = tva_attendue(c.DossierImport("01/26", lignes=lignes, charges=codes), p)
    par_nature = tva_attendue(c.DossierImport("01/26", lignes=lignes, charges=avec), p)
    assert par_code == pytest.approx((60_000 + 3000 + 300 + 1500 + 150) * 0.2)
    assert par_nature == pytest.approx(par_code, abs=0.005)
    assert all(x.est_droits == y.est_droits for x, y in zip(codes, avec, strict=True))
    assert all(
        x.dans_valeur_douane == y.dans_valeur_douane for x, y in zip(codes, avec, strict=True)
    )


def test_le_classeur_et_la_fiche_disent_le_poste_sur_mesure(
    achats: TestClient, direction: TestClient
) -> None:
    """Le frais du poste sur mesure se lit dans la fiche avec sa répartition, comme un poste
    semé (rien de spécial à l'écran) ; le dossier se clôt."""
    ddx = _poste(direction, "DDY", "droits")
    d = frais(achats, _dossier(achats, "NAT-CLO"), ddx, 2000)
    x = next(f for f in d["frais"] if f["poste"] == ddx)
    assert x["repartition"] == "à la valeur" and not x["recuperable"]
    d = geste(achats, d, "cloturer", alertes_lues=True)
    assert d["statut"] == "clos" and d["droits_mad"] == pytest.approx(2000)
