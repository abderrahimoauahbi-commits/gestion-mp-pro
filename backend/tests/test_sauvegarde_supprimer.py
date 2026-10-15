"""Supprimer une sauvegarde (demande de Mohamed, 15/10/2026, route 259) : le fichier et ses
pièces s'effacent, la ligne au journal est écrite ; la plus récente de cette base se garde ;
un nom inconnu ou hors du dossier est introuvable ; l'achat et l'atelier n'y ont pas droit.
Dossiers temporaires seulement (`fabriques.exploitation.dossiers`).
"""

from __future__ import annotations

from pathlib import Path

from fabrique import *  # noqa: F403
from fabriques.exploitation import *  # noqa: F403
from fabriques.exploitation import Dossiers
from fastapi.testclient import TestClient
from sqlalchemy import select

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique
from gestion_mp_pro.modeles import Journal
from gestion_mp_pro.services import sauvegarde_outils as o

ANCIENNE = "gestion-mp-pro-2026-10-01-000500-quotidienne.dump"
RECENTE = "gestion-mp-pro-2026-10-14-000500-quotidienne.dump"


def _fichier(d: Path, nom: str) -> Path:
    """Un faux fichier de sauvegarde de cette base, avec son archive de pièces."""
    d.mkdir(parents=True, exist_ok=True)
    f = d / nom
    f.write_bytes(f"dbname: {reglages().nom_base}".encode())
    o.archive_de(f).write_bytes(b"x")
    return f


def _deux(dossiers: Dossiers) -> tuple[Path, Path]:
    return _fichier(dossiers.sauvegardes, ANCIENNE), _fichier(dossiers.sauvegardes, RECENTE)


def test_supprimer_efface_le_fichier_et_ses_pieces_et_journalise(
    direction: TestClient, dossiers: Dossiers
) -> None:
    ancienne, recente = _deux(dossiers)
    r = direction.delete(f"/api/sauvegardes/{ANCIENNE}")
    assert r.status_code == 200, r.text
    assert not ancienne.exists() and not o.archive_de(ancienne).exists()
    assert recente.exists() and o.archive_de(recente).exists()
    assert ANCIENNE not in [f["nom"] for f in r.json()["fichiers"]]
    with fabrique()() as s:
        lignes = s.scalars(select(Journal).where(Journal.action == "sauvegarde supprimée")).all()
    assert [x.detail for x in lignes][-1] == ANCIENNE


def test_la_plus_recente_se_garde(direction: TestClient, dossiers: Dossiers) -> None:
    _, recente = _deux(dossiers)
    r = direction.delete(f"/api/sauvegardes/{RECENTE}")
    assert r.status_code == 409 and "plus récente" in r.json()["detail"]
    assert recente.exists()


def test_inconnue_ou_hors_du_dossier_introuvable(direction: TestClient, dossiers: Dossiers) -> None:
    _deux(dossiers)
    assert direction.delete("/api/sauvegardes/inconnue.dump").status_code == 404
    assert direction.delete("/api/sauvegardes/..%2F..%2Fx.dump").status_code == 404


def test_achats_et_atelier_n_y_ont_pas_droit(
    achats: TestClient, alimentation: TestClient, dossiers: Dossiers
) -> None:
    ancienne, _ = _deux(dossiers)
    for client in (achats, alimentation):
        assert client.delete(f"/api/sauvegardes/{ANCIENNE}").status_code == 403
    assert ancienne.exists()
