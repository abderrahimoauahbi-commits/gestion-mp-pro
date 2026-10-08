"""Convention d'erreur unique (API-PRO § 0.3) : 422 traduit, 404, 409, 500 tracé, jamais de 500
pour un corps faux ; transaction annulée par un refus (lot S0)."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import APIRouter, FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import Field
from sqlalchemy import text

from gestion_mp_pro.api.communs import Entree, Page, decoder_curseur, encoder_curseur
from gestion_mp_pro.api.dependances import DateReferenceDep, PaginationDep, SessionDep
from gestion_mp_pro.api.erreurs import CODES, Refus, reponses
from gestion_mp_pro.api.traduction import REMPLACEMENTS, traduire_validation
from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION
from gestion_mp_pro.db import moteur
from gestion_mp_pro.main import creer_application

ENTETE_ECRAN = {ENTETE_ANTI_FALSIFICATION: "1"}


class Ligne(Entree):
    quantite: float = Field(gt=0)
    lot: str = Field(min_length=2, max_length=5)


class Corps(Entree):
    nom: str = Field(min_length=3)
    nombre: int = Field(ge=0, le=10)
    lignes: list[Ligne] = Field(default_factory=list)


essai = APIRouter(prefix="/essai", tags=["Essai"])


@essai.post("/saisie", responses=reponses(422))
def saisie(corps: Corps) -> dict[str, int]:
    return {"nombre": corps.nombre}


@essai.get("/objet/{oid}")
def objet(oid: int) -> dict[str, int]:
    raise Refus.introuvable("Commande introuvable.")


@essai.post("/clos")
def clos() -> None:
    raise Refus.etat("Ce bon est clos.", code="bon_clos")


@essai.get("/panne")
def panne() -> None:
    raise RuntimeError("panne imprévue")


@essai.post("/ecrire")
def ecrire(s: SessionDep, refuser: Annotated[bool, Query()] = False) -> dict[str, bool]:
    s.execute(text("INSERT INTO essai_s0 (valeur) VALUES ('ecrit')"))
    if refuser:
        raise Refus.saisie("Refusé après écriture.")
    return {"ok": True}


@essai.get("/date")
def lire_date(jour: DateReferenceDep) -> dict[str, str]:
    return {"date": jour.isoformat()}


@essai.get("/page")
def lire_page(p: PaginationDep) -> Page[int]:
    return Page[int](elements=list(range(p.limite)), total=p.limite, suivant=None)


@pytest.fixture(scope="module")
def app_essai() -> FastAPI:
    return creer_application(routeurs_en_plus=[essai])


@pytest.fixture
def poste(app_essai: FastAPI) -> Iterator[TestClient]:
    with TestClient(app_essai, headers=ENTETE_ECRAN, raise_server_exceptions=False) as c:
        yield c


def test_saisie_traduite_en_francais_champ_par_champ(poste: TestClient) -> None:
    r = poste.post(
        "/api/essai/saisie",
        json={"nom": "ab", "nombre": 11, "lignes": [{"quantite": 0, "lot": "x"}], "pirate": 1},
    )
    assert r.status_code == 422
    corps = r.json()
    assert corps["code"] == "saisie_invalide"
    assert corps["champs"] == {
        "nom": "Texte trop court : au moins 3 caractères",
        "nombre": "La valeur doit être au plus 10",
        "lignes.0.quantite": "La valeur doit être supérieur à 0",
        "lignes.0.lot": "Texte trop court : au moins 2 caractères",
        "pirate": "champ inconnu",
    }
    assert corps["detail"].startswith("nom : Texte trop court : au moins 3 caractères ; ")
    assert re.search(r"[A-Za-z]+ should|Input|Field required", corps["detail"]) is None


def test_champ_manquant_et_types(poste: TestClient) -> None:
    r = poste.post("/api/essai/saisie", json={"nombre": "douze"})
    assert r.status_code == 422
    assert r.json()["champs"] == {"nom": "à renseigner", "nombre": "nombre entier attendu"}


def test_remplacements_de_gestion_mp_dans_leur_ordre() -> None:
    assert REMPLACEMENTS[0] == ("Field required", "à renseigner")
    detail, _ = traduire_validation(
        [{"type": "x", "loc": ("query", "q"), "msg": "String should have at most 5 characters"}]
    )
    assert detail == "q : Texte trop long : au plus 5 caractères"
    detail, _ = traduire_validation(
        [{"type": "value_error", "loc": (), "msg": "Value error, Non."}]
    )
    assert detail == "Non."


CORPS_FAUX = [
    b"",
    b"{",
    b"null",
    b"[]",
    b'"texte"',
    b"12",
    b'{"nom": null, "nombre": null}',
    b'{"nom": ["a"], "nombre": {"x": 1}}',
    b'{"nom": "abcd", "nombre": 1e400}',
    b'{"nom": "abcd", "nombre": 99999999999999999999999999}',
    b'{"nom": "abcd", "nombre": 1, "lignes": "pas une liste"}',
    b'{"nom": "abcd", "nombre": 1, "lignes": [null, 3, {"quantite": "NaN"}]}',
    b"\xff\xfe\x00 pas de l'utf-8",
]


@pytest.mark.parametrize("brut", CORPS_FAUX)
def test_jamais_de_500_pour_un_corps_faux(poste: TestClient, brut: bytes) -> None:
    r = poste.post("/api/essai/saisie", content=brut, headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "saisie_invalide"
    assert r.json()["detail"]


def test_parametre_de_chemin_faux_422(poste: TestClient) -> None:
    r = poste.get("/api/essai/objet/abc")
    assert r.status_code == 422
    assert r.json()["champs"] == {"oid": "nombre entier attendu"}


def test_introuvable_404(poste: TestClient) -> None:
    r = poste.get("/api/essai/objet/12")
    assert r.status_code == 404
    assert r.json() == {"detail": "Commande introuvable.", "code": "introuvable"}


def test_route_inconnue_404(poste: TestClient) -> None:
    r = poste.get("/api/rien/ici")
    assert r.status_code == 404
    assert r.json() == {"detail": "Route inconnue.", "code": "route_inconnue"}


def test_methode_non_permise(poste: TestClient) -> None:
    r = poste.delete("/api/essai/clos")
    assert r.status_code == 405
    assert r.json()["code"] == "methode_non_permise"


def test_etat_409(poste: TestClient) -> None:
    r = poste.post("/api/essai/clos")
    assert r.status_code == 409
    assert r.json() == {"detail": "Ce bon est clos.", "code": "bon_clos"}


def test_500_trace_avec_reference(poste: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="gestion_mp_pro"):
        r = poste.get("/api/essai/panne")
    assert r.status_code == 500
    assert r.json()["code"] == "erreur_serveur"
    reference = r.headers["X-Requete"][:8]
    assert r.json()["detail"] == f"Erreur du serveur (réf. {reference})."
    trace = [x for x in caplog.records if x.levelno == logging.ERROR]
    assert len(trace) == 1
    assert f"ref={reference}" in trace[0].getMessage()
    assert trace[0].exc_info is not None
    assert "panne imprévue" not in r.text
    assert r.headers["X-Content-Type-Options"] == "nosniff"


@pytest.fixture
def table_essai() -> Iterator[None]:
    with moteur().begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS essai_s0 (valeur text)"))
        c.execute(text("DELETE FROM essai_s0"))
    yield
    with moteur().begin() as c:
        c.execute(text("DROP TABLE essai_s0"))


def _lignes() -> int:
    with moteur().connect() as c:
        return int(c.execute(text("SELECT count(*) FROM essai_s0")).scalar_one())


def test_session_validee_si_la_route_aboutit(poste: TestClient, table_essai: None) -> None:
    assert poste.post("/api/essai/ecrire").status_code == 200
    assert _lignes() == 1


def test_un_refus_annule_toute_la_transaction(poste: TestClient, table_essai: None) -> None:
    r = poste.post("/api/essai/ecrire", params={"refuser": True})
    assert r.status_code == 422
    assert _lignes() == 0


def test_date_de_reference_bornee(poste: TestClient) -> None:
    assert poste.get("/api/essai/date").json() == {"date": "2026-10-08"}
    assert poste.get("/api/essai/date?date=2026-10-08").status_code == 200
    futur = poste.get("/api/essai/date?date=2026-10-09")
    assert futur.status_code == 422
    assert futur.json()["code"] == "date_future"
    ancienne = poste.get("/api/essai/date?date=1999-12-31")
    assert ancienne.json() == {
        "detail": "Date trop ancienne (31/12/1999) : vérifier l'année.",
        "code": "date_trop_ancienne",
        "champs": {"date": "date trop ancienne"},
    }
    assert poste.get("/api/essai/date?date=2026-13-01").status_code == 422


def test_pagination(poste: TestClient) -> None:
    assert poste.get("/api/essai/page?limite=3").json() == {
        "elements": [0, 1, 2],
        "total": 3,
        "suivant": None,
    }
    assert poste.get("/api/essai/page?limite=5001").status_code == 422
    r = poste.get("/api/essai/page?apres=%%%")
    assert r.status_code == 422
    assert r.json()["code"] == "curseur_invalide"
    assert decoder_curseur(encoder_curseur(["2026-10-08", 42])) == ["2026-10-08", 42]


CODES_API_PRO = """saisie_invalide introuvable conflit_version etat_incompatible periode_close
date_future date_trop_ancienne stock_insuffisant lot_absent_a_la_date inventaire_en_cours
numero_pris deja_annule approbation_requise droit_refuse non_connecte compte_inactif
trop_d_essais entete_absente erreur_serveur""".split()


def test_codes_declares() -> None:
    assert set(CODES_API_PRO) <= set(CODES)
    assert len(CODES) >= 60
    for nom, code in CODES.items():
        assert re.fullmatch(r"[a-z][a-z_]+[a-z]", nom), nom
        assert code.http in {401, 403, 404, 405, 409, 422, 429, 500, 503}, nom
        assert code.sens


def test_refus_mal_forme_est_une_faute_de_programmation() -> None:
    with pytest.raises(ValueError, match="non déclaré"):
        Refus("code_qui_n_existe_pas", "x")
    with pytest.raises(ValueError, match="409"):
        Refus.saisie("x", code="bon_clos")
