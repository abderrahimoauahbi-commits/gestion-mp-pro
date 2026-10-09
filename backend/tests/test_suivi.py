"""Le suivi par l'API (lot D8) : besoins signalés (221–223), photo du jour des indicateurs
(231, 232 ; tâche de D10), données brutes pour la vérification (route 7).
"""

from __future__ import annotations

from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from fastapi.testclient import TestClient

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import Journal, Notification
from gestion_mp_pro.services import indicateurs
from gestion_mp_pro.taches import photo_du_jour


def test_l_atelier_signale_un_besoin_que_les_achats_traitent(
    alimentation: TestClient, achats: TestClient, administrateur: TestClient
) -> None:
    """Hérité : test_suivi::test_l_atelier_signale_un_besoin_que_les_achats_traitent — l'atelier
    signale (urgent), les achats le voient et le traitent, une fois ; l'atelier lit la réponse
    parmi les siens (`mes`) et en est prévenu ; l'alimentation ne traite pas."""
    corps = {"texte": "Plus de rouge 2900 pour demain", "urgence": "urgente"}
    x = ok(alimentation.post("/api/signalements", json=corps), 201)
    assert (x["par"], x["urgence"], x["traite"]) == ("Alimentation", "urgente", False)
    a_traiter = ok(achats.get("/api/signalements", params={"a_traiter": True}))
    assert x["id"] in {s["id"] for s in a_traiter["elements"]}
    assert alimentation.post(f"/api/signalements/{x['id']}/traiter", json={}).status_code == 403
    t = ok(achats.post(f"/api/signalements/{x['id']}/traiter",
                       json={"reponse": "Commandé, arrive jeudi"}))  # fmt: skip
    assert (t["traite"], t["traite_par"], t["reponse"]) == (
        True,
        "Achats",
        "Commandé, arrive jeudi",
    )
    a_traiter = ok(achats.get("/api/signalements", params={"a_traiter": True}))
    assert x["id"] not in {s["id"] for s in a_traiter["elements"]}
    encore = achats.post(f"/api/signalements/{x['id']}/traiter", json={"reponse": "autre"})
    assert encore.status_code == 409 and "déjà été traité par Achats" in encore.json()["detail"]
    mes = ok(alimentation.get("/api/signalements", params={"mes": True}))["elements"]
    assert next(s for s in mes if s["id"] == x["id"])["reponse"] == "Commandé, arrive jeudi"
    with sessions()() as s:
        actions = {
            j.action for j in s.query(Journal).filter_by(objet="signalement", objet_id=x["id"])
        }
        assert actions == {"besoin signalé", "besoin traité"}
        avis = s.query(Notification).filter_by(objet="signalement", objet_id=x["id"]).all()
        assert {n.role for n in avis if n.role} == {"direction", "achats"}
        assert any(n.lien == "/atelier" for n in avis if n.utilisateur_id)
    assert administrateur.get("/api/signalements").status_code == 403


def test_un_signalement_refuse_ce_qui_ne_se_comprend_pas(alimentation: TestClient) -> None:
    """Matière inconnue : 404 ; texte d'un caractère, urgence inconnue : 422 ; jamais de 500."""
    r = alimentation.post("/api/signalements", json={"matiere_id": 999999, "texte": "manque"})
    assert r.status_code == 404 and r.json()["detail"].startswith("Matière inconnue")
    for corps in ({"texte": "x"}, {"texte": "manque", "urgence": "demain"}, {"texte": "a" * 501}):
        assert alimentation.post("/api/signalements", json=corps).status_code == 422


def test_les_signalements_se_lisent_page_par_page(alimentation: TestClient) -> None:
    """`Page` : le plus récent d'abord, `suivant` jusqu'au bout, `total` dit."""
    ids = [ok(alimentation.post("/api/signalements", json={"texte": f"page {n}"}), 201)["id"]
           for n in range(3)]  # fmt: skip
    p = ok(alimentation.get("/api/signalements", params={"mes": True, "limite": 2}))
    assert [s["id"] for s in p["elements"]][:2] == ids[::-1][:2] and p["suivant"]
    params = {"mes": True, "limite": 2, "apres": p["suivant"]}
    suite = ok(alimentation.get("/api/signalements", params=params))
    assert ids[0] in {s["id"] for s in suite["elements"]}
    assert p["total"] >= 3


def test_photographier_trace_au_journal(usine: Usine) -> None:
    """Hérité : test_defauts_e::test_photographier_trace_au_journal (E-17) — la photo est
    journalisée, sa valeur du stock est celle de la Valorisation ; reprise, elle remplace la
    première (une par jour) ; la direction seule photographie ; la tâche de D10 prend la
    fonction de ce lot."""
    u = usine
    u.ouvrir(u.matiere(), 100, 12)
    p = ok(u.direction.post("/api/indicateurs/photographier"))
    assert p["jour"] == jour().isoformat() and p["valeur_stock_mad"] == 1200
    assert p["valeur_stock_mad"] == u.get(u.achats, "/api/valorisation")["total_mad"]
    u.ouvrir(u.matiere(), 10, 10)
    ok(u.direction.post("/api/indicateurs/photographier"))
    historique = u.get(u.achats, "/api/indicateurs/historique")
    assert [x["valeur_stock_mad"] for x in historique] == [1300]
    assert u.get(u.achats, "/api/indicateurs/historique", du=jour(-5).isoformat(),
                 au=jour(-1).isoformat()) == []  # fmt: skip
    lignes = u.s.query(Journal).filter_by(action="photo des indicateurs").all()
    assert [j.utilisateur_nom for j in lignes] == ["Direction", "Direction"]
    assert "reprise" in lignes[-1].detail
    assert u.achats.post("/api/indicateurs/photographier").status_code == 403
    assert photo_du_jour._photographe() is indicateurs.photographier


@pytest.mark.parametrize("client", ["achats", "alimentation", "administrateur"])
def test_les_donnees_brutes_sont_a_la_direction(usine: Usine, client: str) -> None:
    """Route 7 : direction seule."""
    assert getattr(usine, client).get("/api/donnees/mouvement").status_code == 403


def test_les_donnees_brutes_d_une_table(usine: Usine) -> None:
    """Route 7 : une table de la liste fermée, ligne à ligne (nombres JSON), bornée par `date` ;
    une table hors liste (comptes, sessions, journal) : 404."""
    u = usine
    m = u.matiere("BRUTE")
    u.ouvrir(m, 100, 12, le=jour(-10))
    u.ouvrir(m, 5, 12)
    r: dict[str, Any] = u.get(u.direction, "/api/donnees/mouvement")
    assert "quantite" in r["colonnes"] and len(r["lignes"]) == 2
    assert {x["quantite"] for x in r["lignes"]} == {100.0, 5.0}
    passe = u.get(u.direction, "/api/donnees/mouvement", date=jour(-5).isoformat())
    assert [x["quantite"] for x in passe["lignes"]] == [100.0]
    matieres = u.get(u.direction, "/api/donnees/matiere")
    assert "texte_recherche" not in matieres["colonnes"]
    for table in ("utilisateur", "session", "journal", "inconnue"):
        assert u.direction.get(f"/api/donnees/{table}").status_code == 404
