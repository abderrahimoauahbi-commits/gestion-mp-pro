"""Les unités de titrage, un référentiel (routes 57 et 255–257 ; lot UNITES-TITRAGE).

Décision de Mohamed du 12/10/2026 (DECISIONS F29) : ajouter lui-même une unité, sans
intervention. Semis, ajout lu aussitôt dans les références, casse, unité employée (ni supprimée
ni renommée : désactivée), unité désactivée (ni proposée ni lue, gardée sur ses titrages),
droits, version périmée, journal.
"""

from __future__ import annotations

from typing import Any

from fabrique import *  # noqa: F403
from fabriques.referentiels import matiere
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.calcul.classification import decomposer
from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Journal
from gestion_mp_pro.services import unites_titrage

SEMEES = ["Dtex", "Deniers", "Nm", "Tex", "Nec", "lbs"]
URL = "/api/classification/unites-titrage"


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def refus(r: Any, statut: int) -> str:
    """Le message d'un refus attendu."""
    assert r.status_code == statut, r.text
    return str(r.json()["detail"])


def unites(client: TestClient) -> dict[str, dict[str, Any]]:
    """Les unités lues par la route 57, par code."""
    return {u["code"]: u for u in ok(client.get("/api/classification"))["unites_titrage"]}


def lue(reference: str) -> tuple[str, str]:
    """Le titrage et l'unité qu'une référence donne avec les unités actives de la base."""
    with sessions()() as s:
        c = decomposer(reference, unites=unites_titrage.actives(s))
    return c.titrage, c.titrage_unite


def test_les_six_unites_semees_et_les_droits(
    base_neuve: None, alimentation: TestClient, achats: TestClient
) -> None:
    """Semis de la révision 0008 dans l'ordre ; l'alimentation lit, n'écrit pas."""
    lues = ok(alimentation.get("/api/classification"))["unites_titrage"]
    assert [u["code"] for u in lues] == SEMEES
    assert [u["ordre"] for u in lues] == [10, 20, 30, 40, 50, 60]
    assert all(u["actif"] and u["version"] == 1 for u in lues)
    dtex = lues[0]
    assert alimentation.post(URL, json={"code": "Ne"}).status_code == 403
    corps = {"code": "Dtex", "version": 1}
    assert alimentation.put(f"{URL}/{dtex['id']}", json=corps).status_code == 403
    assert alimentation.delete(f"{URL}/{dtex['id']}").status_code == 403
    assert achats.put(f"{URL}/999999", json=corps).status_code == 404


def test_une_unite_ajoutee_se_lit_dans_les_references(
    base_neuve: None, achats: TestClient, direction: TestClient
) -> None:
    """« Ne » ajoutée par les achats : rangée après « lbs », lue aussitôt (« Coton 20 Ne ») par
    la lecture des références et par l'aperçu du classement (route 76) ; journalisée."""
    assert lue("Coton 20 Ne") == ("20", "")
    ne = ok(achats.post(URL, json={"code": " Ne ", "libelle": "numéro anglais"}), 201)
    assert (ne["code"], ne["ordre"], ne["nb_titrages"], ne["raison_garder"]) == ("Ne", 70, 0, None)
    assert lue("Coton 20 Ne") == ("20", "Ne") and lue("Coton 20 NEC") == ("20", "Nec")
    m = matiere("Coton 20 Ne Blanc")
    apercu = ok(direction.get("/api/matieres/classement"))
    proposee = next(p for p in apercu["propositions"] if p["matiere_id"] == m)
    assert proposee["changements"]["titrage"] == "20 Ne"
    assert "20 Ne" in apercu["a_creer"]["titrage"]
    with sessions()() as s:
        j = s.scalars(
            select(Journal).where(Journal.objet == "unite_titrage", Journal.objet_id == ne["id"])
        ).one()
    assert (j.action, j.numero, j.apres["code"]) == ("ajout unité de titrage", "Ne", "Ne")


def test_la_casse_ne_fait_pas_une_autre_unite(base_neuve: None, achats: TestClient) -> None:
    """« LBS » refusé si « lbs » existe (A-12) ; un code d'un mot de lettres ; « Den » abrège
    Deniers ; un ordre se choisit."""
    assert refus(achats.post(URL, json={"code": "LBS"}), 409) == (
        "L'unité « lbs » existe déjà (« LBS »)."
    )
    assert refus(achats.post(URL, json={"code": "dtex"}), 409).startswith("L'unité « Dtex »")
    message = refus(achats.post(URL, json={"code": "g/km"}), 422)
    assert message == (
        "Une unité de titrage s'écrit en lettres seules, de 2 à 16 (« g/km » ne se lirait pas "
        "dans une référence)."
    )
    assert achats.post(URL, json={"code": "x"}).status_code == 422
    assert achats.post(URL, json={"code": "A" * 17}).status_code == 422
    assert refus(achats.post(URL, json={"code": "Den"}), 409) == (
        "« Den » abrège « Deniers » dans les références : ce n'est pas une unité à part."
    )
    tex = ok(achats.post(URL, json={"code": "kTex", "ordre": 45}), 201)
    assert list(unites(achats))[4] == "kTex" and tex["ordre"] == 45


def test_une_unite_employee_se_desactive_sans_disparaitre(
    base_neuve: None, achats: TestClient
) -> None:
    """Employée par un titrage (et sa matière) : ni supprimée ni renommée (raison dite), sa
    casse se corrige ; désactivée, elle n'est plus lue dans une nouvelle référence ni comptée
    parmi les actives, mais reste sur le titrage qui l'écrit ; jamais employée, elle part."""
    ne = ok(achats.post(URL, json={"code": "Ne"}), 201)
    titrage = ok(achats.post("/api/classification/titrages", json={"code": "20 Ne"}), 201)
    matiere("Coton 20 Ne Rouge", titrage_id=titrage["id"])
    fiche = unites(achats)["Ne"]
    assert (fiche["nb_titrages"], fiche["nb_matieres"]) == (1, 1)
    raison = "Écrite sur 1 titrage(s) (1 matière(s)) : la désactiver plutôt que la supprimer"
    assert fiche["raison_garder"] == raison
    assert refus(achats.delete(f"{URL}/{ne['id']}"), 409) == (
        "« Ne » est écrite sur 1 titrage(s) (1 matière(s)) : la désactiver plutôt que la supprimer."
    )
    renomme = achats.put(f"{URL}/{ne['id']}", json={"code": "Nx", "version": 1})
    assert refus(renomme, 409) == (
        "« Ne » est écrite sur 1 titrage(s) (1 matière(s)) : son code ne se change pas. "
        "Ajouter l'unité « Nx », puis désactiver « Ne »."
    )
    casse = ok(achats.put(f"{URL}/{ne['id']}", json={"code": "NE", "version": 1}))
    assert (casse["code"], casse["version"], casse["nb_titrages"]) == ("NE", 2, 1)
    eteinte = ok(achats.put(f"{URL}/{ne['id']}", json={"code": "Ne", "actif": False, "version": 2}))
    assert eteinte["avertissement"] == (
        "« Ne » reste écrite sur 1 titrage(s) (1 matière(s)) : elle ne se propose plus et ne se "
        "lit plus dans une nouvelle référence ; ces titrages la gardent."
    )
    with sessions()() as s:
        assert "Ne" not in unites_titrage.actives(s)
    assert lue("Coton 30 Ne") == ("30", "")
    lus = ok(achats.get("/api/classification"))
    assert next(t for t in lus["titrages"] if t["id"] == titrage["id"])["unite"] == "Ne"
    assert unites(achats)["Ne"]["actif"] is False
    libre = ok(achats.post(URL, json={"code": "Ktex"}), 201)
    assert achats.delete(f"{URL}/{libre['id']}?version=1").status_code == 204
    assert "Ktex" not in unites(achats)


def test_une_unite_modifiee_entre_temps_est_refusee(base_neuve: None, achats: TestClient) -> None:
    """Version périmée → 409 `conflit_version` qui nomme l'auteur, en modification comme en
    suppression ; rien n'est écrit ; sans version, 422."""
    u = ok(achats.post(URL, json={"code": "Ne"}), 201)
    ok(achats.put(f"{URL}/{u['id']}", json={"code": "Ne", "libelle": "anglais", "version": 1}))
    perime = achats.put(f"{URL}/{u['id']}", json={"code": "Ne", "ordre": 5, "version": 1})
    assert perime.status_code == 409 and perime.json()["code"] == "conflit_version"
    assert perime.json()["detail"].startswith("Cette unité de titrage a été modifiée entre-temps")
    assert achats.delete(f"{URL}/{u['id']}?version=1").json()["code"] == "conflit_version"
    assert achats.put(f"{URL}/{u['id']}", json={"code": "Ne"}).status_code == 422
    relue = unites(achats)["Ne"]
    assert (relue["libelle"], relue["ordre"], relue["version"]) == ("anglais", 70, 2)
