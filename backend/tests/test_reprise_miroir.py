"""Le miroir de Gestion MP depuis l'écran (lot C1, routes 243–244 ; ARCHITECTURE § 14.2).

Une petite usine au schéma de Gestion MP (`fabriques/reprise.py`) est la source ; une base PRO
neuve est la cible (`services.miroir.cible` et `source` remplacés : la base des essais n'est
pas touchée). Direction : rafraîchir (202, sauvegarde « avant reprise » d'abord, journal),
état à jour, rapport ; administrateur : l'état sans le rapport, aucun geste ; activité saisie
dans PRO : refus clair sans « remplacer » confirmé par REMPLACER ; source illisible : 503 ;
reprise déjà en cours : 409.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabriques.exploitation import avec_outils_pg
from fabriques.reprise import (
    FICHIERS,
    PETITE_USINE,
    cible_migree,
    executer_sql,
    source_gestion_mp,
    supprimer_base,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from gestion_mp_pro.reprise import source as src
from gestion_mp_pro.services import miroir

pytestmark = avec_outils_pg

ESSAI = (make_url(os.environ["GESTIONMPPRO_BASE"]).database or "gestion_mp_pro_essai").removesuffix(
    "_essai"
)
SOURCE = f"postgresql+psycopg:///{ESSAI}_msource_essai"
CIBLE = f"postgresql+psycopg:///{ESSAI}_mcible_essai"


@pytest.fixture
def bases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Source (petite usine) et cible neuves ; le miroir les vise ; supprimées après."""
    for chemin, contenu in FICHIERS.items():
        (tmp_path / "source" / chemin).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "source" / chemin).write_bytes(contenu)
    source_gestion_mp(SOURCE, PETITE_USINE)
    cible_migree(CIBLE)
    monkeypatch.setattr(miroir, "source", lambda: SOURCE)
    monkeypatch.setattr(miroir, "cible", lambda: CIBLE)
    monkeypatch.setattr(
        miroir, "dossiers_pieces", lambda: (tmp_path / "source", tmp_path / "cible")
    )
    yield
    supprimer_base(SOURCE)
    supprimer_base(CIBLE)


def un(sql: str, url: str = CIBLE) -> Any:
    """La première valeur d'une requête."""
    moteur = create_engine(url, poolclass=NullPool)
    with moteur.connect() as c:
        valeur = c.execute(text(sql)).scalar()
    moteur.dispose()
    return valeur


def rafraichir(client: TestClient, **corps: Any) -> Any:
    """POST /api/reprise (la tâche de fond est finie quand le client rend la réponse)."""
    return client.post("/api/reprise", json=corps)


def test_la_direction_rafraichit_le_miroir(bases: None, direction: TestClient) -> None:
    avant = direction.get("/api/reprise").json()
    assert avant["executions"] == [] and avant["derniere_reussie"] is None
    assert avant["source_lisible"] and not avant["a_jour"] and not avant["activite_propre"]
    assert avant["signature_source"] == src.empreinte_actuelle(SOURCE)
    r = rafraichir(direction)
    assert r.status_code == 202, r.text
    assert r.json()["etat"] == "en_cours" and "avant reprise" in r.json()["message"]
    apres = direction.get("/api/reprise").json()
    assert apres["a_jour"] and not apres["en_cours"] and not apres["activite_propre"]
    derniere = apres["derniere_reussie"]
    assert derniere["statut"] == "reussie" and derniere["base_source"].endswith("_msource_essai")
    assert derniere["empreinte_source"] == apres["signature_source"]
    assert "CONTRÔLES" in derniere["rapport"] and derniere["creees"] > 0
    assert derniere["tables"]["matiere"]["creees"] >= 1
    assert un("SELECT count(*) FROM sauvegarde WHERE genre = 'avant_reprise'") == 1
    assert un("SELECT count(*) FROM journal WHERE action = 'reprise de Gestion MP'") == 1


def test_rejouee_sans_changement_reste_a_jour(bases: None, direction: TestClient) -> None:
    assert rafraichir(direction).status_code == 202
    assert rafraichir(direction).status_code == 202
    etat = direction.get("/api/reprise").json()
    assert etat["a_jour"] and len(etat["executions"]) == 2
    assert etat["executions"][0]["creees"] == 0


def test_le_miroir_en_retard_se_voit(bases: None, direction: TestClient) -> None:
    rafraichir(direction)
    executer_sql(SOURCE, "UPDATE article SET designation = designation || ' bis' WHERE id = 1")
    assert not direction.get("/api/reprise").json()["a_jour"]
    rafraichir(direction)
    assert direction.get("/api/reprise").json()["a_jour"]


def test_activite_saisie_dans_pro_refus_clair(bases: None, direction: TestClient) -> None:
    rafraichir(direction)
    executer_sql(CIBLE, "UPDATE commande SET observations = 'saisi dans PRO' WHERE id = 1")
    assert direction.get("/api/reprise").json()["activite_propre"]
    refus = rafraichir(direction)
    assert refus.status_code == 409 and refus.json()["code"] == "activite_presente"
    assert "REMPLACER" in refus.json()["detail"]
    sans_mot = rafraichir(direction, remplacer_activite=True, confirmation="oui")
    assert sans_mot.status_code == 422 and sans_mot.json()["code"] == "confirmation_requise"
    assert un("SELECT observations FROM commande WHERE id = 1") == "saisi dans PRO"
    r = rafraichir(direction, remplacer_activite=True, confirmation="remplacer")
    assert r.status_code == 202, r.text
    assert un("SELECT observations FROM commande WHERE id = 1") == ""
    assert not direction.get("/api/reprise").json()["activite_propre"]
    assert un("SELECT count(*) FROM sauvegarde WHERE genre = 'avant_reprise'") == 2


def test_administrateur_lit_l_etat_sans_le_rapport(
    bases: None, direction: TestClient, administrateur: TestClient
) -> None:
    rafraichir(direction)
    etat = administrateur.get("/api/reprise")
    assert etat.status_code == 200
    assert etat.json()["derniere_reussie"]["rapport"] is None
    assert all(e["rapport"] is None for e in etat.json()["executions"])
    assert rafraichir(administrateur).status_code == 403


def test_les_autres_roles_n_y_ont_pas_droit(
    bases: None, achats: TestClient, alimentation: TestClient
) -> None:
    for client in (achats, alimentation):
        assert client.get("/api/reprise").status_code == 403
        assert rafraichir(client).status_code == 403


def test_source_illisible(
    bases: None, direction: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(miroir, "source", lambda: f"postgresql+psycopg:///{ESSAI}_absente_essai")
    etat = direction.get("/api/reprise").json()
    assert not etat["source_lisible"] and "illisible" in etat["message_source"]
    r = rafraichir(direction)
    assert r.status_code == 503 and r.json()["code"] == "base_indisponible"
    assert un("SELECT count(*) FROM reprise_execution") == 0


def test_une_seule_reprise_a_la_fois(bases: None, direction: TestClient) -> None:
    assert miroir._EN_COURS.acquire(blocking=False)  # noqa: SLF001 — une reprise en cours
    try:
        assert direction.get("/api/reprise").json()["en_cours"]
        r = rafraichir(direction)
        assert r.status_code == 409 and r.json()["code"] == "tache_en_cours"
    finally:
        miroir._EN_COURS.release()  # noqa: SLF001
    assert rafraichir(direction).status_code == 202
