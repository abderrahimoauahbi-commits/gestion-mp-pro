"""Période close (route 26) et devises (routes 27–30) — lot D1.

Héritage KR33, K70–K73, KR50 ; défauts E-02 (un mois clos ne se revalorise pas), E-13, E-14.
La période est rouverte et les décors retirés à la fin de chaque essai.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.referentiels import devise, fournisseur, matiere
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import (
    Devise,
    DeviseCours,
    Dossier,
    DossierLigne,
    Journal,
    Parametre,
    ParametreHistorique,
    Reception,
)
from gestion_mp_pro.modeles.enums import StatutDocument


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def version_cloture() -> int:
    """La version du réglage de clôture."""
    with sessions()() as s:
        return s.scalars(select(Parametre.version).where(Parametre.cle == "date_cloture")).one()


def clore(client: TestClient, jour: str | None, motif: str = "Clôture de septembre") -> Any:
    """`PUT /periode-close` à la version lue."""
    corps = {"date_cloture": jour, "motif": motif, "version": version_cloture()}
    return client.put("/api/periode-close", json=corps)


@pytest.fixture(autouse=True)
def periode_rouverte() -> Iterator[None]:
    """Aucune période close avant ni après l'essai."""
    with sessions()() as s, s.begin():
        s.execute(update(Parametre).where(Parametre.cle == "date_cloture").values(valeur=""))
    yield
    with sessions()() as s, s.begin():
        s.execute(update(Parametre).where(Parametre.cle == "date_cloture").values(valeur=""))


def test_clore_avec_motif_trace_et_rouvrir(direction: TestClient, achats: TestClient) -> None:
    """Hérité : test_parcours::test_une_periode_close_ne_bouge_plus ; KR33 ; REGLAGES § 9
    n° 13 — motif obligatoire, période passée, historique avec motif, journal avant/après."""
    r = clore(direction, "2026-09-30", "ok")
    assert r.json()["detail"] == "Le motif est obligatoire : 3 caractères au moins."
    r = clore(direction, "2026-10-08")
    assert (r.status_code, r.json()["detail"]) == (422, "On ne clôt qu'une période passée.")
    assert clore(achats, "2026-09-30").status_code == 403
    p = ok(clore(direction, "2026-09-30"))
    assert (p["date_cloture"], p["par"]) == ("2026-09-30", "Direction")
    with sessions()() as s:
        h = s.scalars(select(ParametreHistorique).order_by(ParametreHistorique.id.desc())).first()
        assert h is not None and (h.cle, h.apres, h.motif) == (
            "date_cloture",
            "2026-09-30",
            "Clôture de septembre",
        )
        j = s.scalars(select(Journal).order_by(Journal.id.desc())).first()
        assert j is not None and j.objet == "periode" and j.apres == {"date_cloture": "2026-09-30"}
    perime = {"date_cloture": None, "motif": "Correction", "version": p["version"] - 1}
    assert direction.put("/api/periode-close", json=perime).status_code == 409
    assert ok(clore(direction, None, "Correction du mois"))["date_cloture"] is None


def test_cloture_refusee_si_brouillon_dans_periode(direction: TestClient) -> None:
    """Hérité : test_defauts_e::test_cloture_refusee_si_brouillon_dans_periode (E-14)."""
    f = fournisseur()
    with sessions()() as s, s.begin():
        r = Reception(date=date(2026, 9, 15), fournisseur_id=f, devise="MAD")
        r.statut = StatutDocument.brouillon
        s.add(r)
        s.flush()
        rid = r.id
    try:
        refus = clore(direction, "2026-09-30")
        assert refus.status_code == 409
        assert refus.json()["detail"] == (
            "Des brouillons sont datés de la période à clore : 1 réception(s). Les valider, "
            "les supprimer ou les redater d'abord : après la clôture, ils ne pourraient plus "
            "se valider."
        )
        ok(clore(direction, "2026-09-14"))
    finally:
        with sessions()() as s, s.begin():
            s.execute(delete(Reception).where(Reception.id == rid))


def _dossier_ouvert(code: str, arrivee: date) -> int:
    """Un dossier ouvert, saisi à la main, et une marchandise en devise sans cours."""
    m = matiere(devise=code)
    with sessions()() as s, s.begin():
        d = Dossier(numero=f"ANC-{code}-{m}", saisi_a_la_main=True, date_arrivee=arrivee)
        s.add(d)
        s.flush()
        ligne = DossierLigne(dossier_id=d.id, matiere_id=m, devise=code)
        ligne.valeur_devise, ligne.quantite_kg = Decimal(1000), Decimal(100)
        s.add(ligne)
        s.flush()
        return ligne.id


def _ligne(ident: int) -> DossierLigne:
    """Une marchandise de dossier relue."""
    with sessions()() as s:
        return s.get_one(DossierLigne, ident)


def test_changer_un_cours_ne_revalorise_pas_un_mois_clos(direction: TestClient) -> None:
    """Hérité : test_defauts_e::test_changer_cours_ne_revalorise_pas_un_mois_clos (E-02, V3) ;
    test_valorisation::test_un_mois_clos_ne_se_revalorise_pas (cours)."""
    code = devise(cours="10")
    avant_cloture = _dossier_ouvert(code, date(2026, 9, 10))
    ok(clore(direction, "2026-09-30"))
    figee = _ligne(avant_cloture)
    assert (figee.cours, figee.cours_origine) == (Decimal(10), "saisi")
    assert "cours figé à la clôture" in figee.commentaire
    apres_cloture = _dossier_ouvert(code, date(2026, 9, 20))
    ouverte = _dossier_ouvert(code, date(2026, 10, 2))
    with sessions()() as s:
        version = s.get_one(Devise, code).version
    ok(direction.put(f"/api/devises/{code}", json={"cours": 12, "version": version}))
    assert _ligne(apres_cloture).cours == Decimal(10)
    assert _ligne(ouverte).cours is None
    assert _ligne(avant_cloture).cours == Decimal(10)


def test_devises_lecture_creation(
    direction: TestClient, achats: TestClient, alimentation: TestClient
) -> None:
    """Hérité : K70–K72 ; test_defauts_f::test_alimentation_ne_lit_ni_parametres_ni_devises."""
    assert alimentation.get("/api/devises").status_code == 403
    assert alimentation.get("/api/devises/USD/cours").status_code == 403
    mad = next(x for x in ok(achats.get("/api/devises")) if x["code"] == "MAD")
    assert (mad["cours"], mad["actif"]) == (1.0, True)
    with sessions()() as s:
        libre = next(
            c for c in ("QXA", "QXB", "QXC", "QXD", "QXE", "QXF") if s.get(Devise, c) is None
        )
    cree = ok(
        achats.post("/api/devises", json={"code": libre.lower(), "nom": "Essai", "cours": 3.5}), 201
    )
    assert (cree["code"], cree["cours"], cree["cours_repris"]) == (libre, 3.5, False)
    r = achats.post("/api/devises", json={"code": libre, "cours": 1})
    assert (r.status_code, r.json()["detail"]) == (409, f"La devise « {libre} » existe déjà.")
    r = achats.post("/api/devises", json={"code": "G1P", "cours": 1})
    assert r.json()["detail"] == "Le code d'une devise s'écrit en trois lettres (EUR, USD, CNY…)."
    assert achats.post("/api/devises", json={"code": "GBP", "cours": 0}).status_code == 422


def test_le_dirham_reste_a_1_et_en_service(direction: TestClient) -> None:
    """Hérité : KR50 ; test_defauts_e::test_mad_ne_se_desactive_pas (E-13)."""
    v = next(x for x in ok(direction.get("/api/devises")) if x["code"] == "MAD")["version"]
    r = direction.put("/api/devises/MAD", json={"cours": 2, "version": v})
    assert r.json()["detail"] == "Le dirham est la devise de référence : son cours reste 1."
    r = direction.put("/api/devises/MAD", json={"cours": 1, "actif": False, "version": v})
    assert r.json()["detail"] == "Le dirham est la devise de référence : il reste en service."


def test_un_cours_n_est_historise_que_s_il_change(achats: TestClient) -> None:
    """Hérité : test_defauts_e::test_devise_renommage_sans_ligne_de_cours (E-13) ; K71."""
    code = devise(cours="10")

    def cours() -> int:
        with sessions()() as s:
            return s.scalar(select(func.count()).where(DeviseCours.devise == code)) or 0

    def version() -> int:
        return next(x for x in ok(achats.get("/api/devises")) if x["code"] == code)["version"]

    n = cours()
    ok(
        achats.put(
            f"/api/devises/{code}", json={"nom": "Renommée", "cours": 10, "version": version()}
        )
    )
    assert cours() == n
    lu = ok(achats.put(f"/api/devises/{code}", json={"cours": 10.85, "version": version()}))
    assert (lu["nom"], lu["cours"], cours()) == ("Renommée", 10.85, n + 1)
    page = ok(achats.get(f"/api/devises/{code}/cours"))
    assert page["elements"][0]["cours"] == 10.85 and page["elements"][0]["par"] == "Achats"
    assert page["elements"][0]["variation"] == pytest.approx(0.085)
    perime = achats.put(f"/api/devises/{code}", json={"cours": 11, "version": 1})
    assert perime.status_code == 409 and perime.json()["code"] == "conflit_version"
    assert achats.get("/api/devises/ZZZ/cours").status_code == 404
