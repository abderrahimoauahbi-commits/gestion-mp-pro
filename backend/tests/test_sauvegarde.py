"""Sauvegardes de cette base : relues, avec leurs pièces, copiées, purgées, surveillées (lot D10).

Routes 1, 43, 44 ; décision X2 de Mohamed (sauvegarde relue, manuelles et « avant-* » jamais
purgées, copie purgée de même, échec en rouge à la direction) ; le calendrier et la rotation de
la décision X7 (22 h, 14 / 8 / 12) sont dans `test_sauvegarde_calendrier.py` ; défauts G-03, G-05,
G-06, G-09 de Gestion MP. Les restaurations réelles (base jetable, vrai serveur) sont dans
`test_restauration.py`. Dossiers temporaires seulement (`fabriques.exploitation.dossiers`).
"""

from __future__ import annotations

import tarfile
from datetime import datetime, timedelta

import pytest
from fabrique import *  # noqa: F403
from fabriques.exploitation import *  # noqa: F403
from fabriques.exploitation import Dossiers, avec_outils_pg, environnement
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from gestion_mp_pro.config import reglages
from gestion_mp_pro.db import fabrique, moteur
from gestion_mp_pro.modeles import Journal, Sauvegarde
from gestion_mp_pro.services import execution, horloge
from gestion_mp_pro.services import sauvegarde as service
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services.sauvegarde_etat import AUCUNE_RECENTE, etat


def _tables_en_base() -> int:
    with moteur().connect() as c:
        return int(c.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")))


def _vide(chemin: object, nom: str) -> None:
    """Un faux fichier de sauvegarde (nom seulement : la purge ne lit que les noms)."""
    from pathlib import Path

    d = Path(str(chemin))
    d.mkdir(parents=True, exist_ok=True)
    (d / nom).write_bytes(b"x")
    o.archive_de(d / nom).write_bytes(b"x")


@avec_outils_pg
def test_sauvegarde_manuelle_relue_avec_pieces_copie_et_journal(
    direction: TestClient, dossiers: Dossiers
) -> None:
    """G-03 : les pièces de cette base, chemins relatifs, dans l'archive ; copie vérifiée."""
    (dossiers.pieces / "fournisseur" / "7").mkdir(parents=True)
    (dossiers.pieces / "fournisseur" / "7" / "contrat.pdf").write_bytes(b"%PDF-1.4 contrat")
    autre = dossiers.racine / "pieces" / "une_autre_base_essai" / "dossier"
    autre.mkdir(parents=True)
    (autre / "x.pdf").write_bytes(b"%PDF autre base")
    r = direction.post("/api/sauvegardes")
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["nb"] == 1 and e["alerte"] is None and e["base"] == reglages().nom_base
    f = e["fichiers"][0]
    assert f["genre"] == "manuelle" and f["nature"] == "manuelle" and f["pieces"] and f["copie"]
    assert f["tables"] == _tables_en_base() and not f["autre_base"]
    fichier = dossiers.sauvegardes / f["nom"]
    with tarfile.open(o.archive_de(fichier)) as archive:
        assert archive.getnames() == ["fournisseur/7/contrat.pdf"]  # pas l'autre base
    for nom in (f["nom"], f["nom"] + o.SUFFIXE_PIECES):
        assert (dossiers.copie / nom).stat().st_size == (dossiers.sauvegardes / nom).stat().st_size
    assert o.relire(fichier).base == reglages().nom_base
    with fabrique()() as s:
        ligne = s.scalar(
            select(Journal).where(Journal.action == "sauvegarde").order_by(Journal.id.desc())
        )
        assert ligne is not None and ligne.detail == f["nom"]
        assert (
            s.scalar(select(Sauvegarde.tables).where(Sauvegarde.fichier == f["nom"])) == f["tables"]
        )
    assert not list(dossiers.sauvegardes.glob(".*partiel"))


def test_sauvegarde_sans_pg_dump_503_lisible(direction: TestClient, dossiers: Dossiers) -> None:
    """Défaut G-05 (`test_defauts_g::test_sauvegarde_sans_pg_dump_message_clair`) : 503, pas 500."""
    with environnement({"GESTIONMPPRO_PG_BIN": str(dossiers.racine / "rien")}):
        r = direction.post("/api/sauvegardes")
    assert r.status_code == 503
    assert r.json()["code"] == "sauvegarde_impossible"
    assert "pg_dump est introuvable" in r.json()["detail"]


def test_les_sauvegardes_sont_a_la_direction_et_a_l_administrateur(
    direction: TestClient,
    administrateur: TestClient,
    achats: TestClient,
    alimentation: TestClient,
    dossiers: Dossiers,
) -> None:
    for client in (direction, administrateur):
        assert client.get("/api/sauvegardes").status_code == 200
    for client in (achats, alimentation):
        assert client.get("/api/sauvegardes").status_code == 403
        assert client.post("/api/sauvegardes").status_code == 403
        corps = {"confirmation": "RESTAURER", "motif": "essai"}
        assert client.post("/api/sauvegardes/x.dump/restaurer", json=corps).status_code == 403


def _sauvegarde_datee(dossiers: Dossiers, il_y_a_h: float) -> None:
    """Une vraie sauvegarde de cette base, renommée comme si elle avait `il_y_a_h` heures."""
    f = service.sauvegarder("manuelle")
    instant = horloge.maintenant() - timedelta(hours=il_y_a_h)
    cible = dossiers.sauvegardes / o.nom_de("manuelle", instant)
    (dossiers.sauvegardes / f.nom).rename(cible)


@avec_outils_pg
@pytest.mark.parametrize(("heures", "alerte"), [(25.5, None), (26.5, AUCUNE_RECENTE)])
def test_alerte_a_26_heures(
    heures: float, alerte: str | None, dossiers: Dossiers, anonyme: TestClient
) -> None:
    _sauvegarde_datee(dossiers, heures)
    execution.noter("sauvegarde", horloge.maintenant())  # la tâche a tourné
    sante = anonyme.get("/api/sante").json()
    assert sante["sauvegarde_age_h"] == pytest.approx(heures, abs=0.01)
    assert (sante["sauvegarde_alerte"] or None) == alerte


@avec_outils_pg
def test_l_echec_se_dit_en_rouge_a_la_direction_et_a_l_administrateur(
    direction: TestClient, administrateur: TestClient, achats: TestClient, dossiers: Dossiers
) -> None:
    execution.noter("sauvegarde", horloge.maintenant(), "pg_dump a échoué : disque plein")
    attendu = "La sauvegarde automatique a échoué : pg_dump a échoué : disque plein"
    assert direction.get("/api/contexte").json()["alerte_serveur"] == attendu
    assert administrateur.get("/api/contexte").json()["alerte_serveur"] == attendu
    assert achats.get("/api/contexte").json()["alerte_serveur"] is None
    assert direction.get("/api/sauvegardes").json()["alerte"] == attendu


@avec_outils_pg
def test_sante_ignore_les_sauvegardes_d_une_autre_base(
    anonyme: TestClient, dossiers: Dossiers, base_voisine: str
) -> None:
    """G-06 (`test_defauts_g::test_sante_ignore_les_sauvegardes_d_une_autre_base`)."""
    dossiers.sauvegardes.mkdir(parents=True)
    cible = dossiers.sauvegardes / o.nom_de("manuelle")
    o.lancer(["pg_dump", "-Fc", "-f", str(cible), base_voisine])
    execution.noter("sauvegarde", horloge.maintenant())
    sante = anonyme.get("/api/sante").json()
    assert sante["sauvegarde_age_h"] is None
    assert sante["sauvegarde_alerte"] == AUCUNE_RECENTE
    with fabrique()() as s:
        e = etat(s)
    assert e.nb == 0 and e.autres == 1 and e.fichiers[0].autre_base
    assert e.fichiers[0].base == base_voisine


def test_sante_complete(anonyme: TestClient, dossiers: Dossiers) -> None:
    """Route 1 : version, schéma (= attendu), base, sauvegarde de cette base, tâches, courriels."""
    from gestion_mp_pro.services.installation import revision_attendue

    execution.noter("courriel", horloge.maintenant(), "SMTPException : refusé")
    s = anonyme.get("/api/sante").json()
    assert s["etat"] == "ok" and s["version"]
    assert s["schema"] == s["schema_attendu"] == revision_attendue()
    assert s["base_ms"] is not None and s["base_ms"] >= 0
    assert s["sauvegarde_age_h"] is None and s["courriels_en_attente"] == 0
    assert set(s["taches"]) == set(execution.TACHES)
    assert s["taches"]["courriel"] == "échec : SMTPException : refusé"
    assert s["taches"]["sauvegarde"] == "jamais"


@pytest.fixture(scope="module")
def base_voisine() -> object:
    """Une autre base, minuscule, dont on fait une sauvegarde (créée puis détruite)."""
    nom = "gestion_mp_pro_d10_voisine_essai"
    o.lancer(["dropdb", "--if-exists", "--force", nom])
    o.lancer(["createdb", nom])
    o.lancer(
        ["psql", "-X", "-q", "-d", nom, "-c", "CREATE TABLE t (id int); INSERT INTO t VALUES (1)"]
    )
    yield nom
    o.lancer(["dropdb", "--if-exists", "--force", nom])


def test_un_nom_se_lit_a_l_heure_de_l_usine() -> None:
    instant = datetime(2026, 10, 8, 2, 0, 5, tzinfo=horloge.FUSEAU)
    nom = o.nom_de("quotidienne", instant)
    assert nom == "gestion-mp-pro-2026-10-08-020005-quotidienne.dump"
    lu = o.lire_nom(nom)
    assert lu is not None and lu.instant == instant and lu.genre == "quotidienne"
    assert o.lire_nom("gestion-mp-pro-2026-13-08-020005-quotidienne.dump") is None
    assert o.lire_nom("gestion-mp-2026-10-08.dump") is None  # Gestion MP : pas les siennes


def test_le_registre_inscrit_tous_les_genres_du_disque() -> None:
    """Révision 0004 (décision X2) : « avant vidage » et « avant mise à jour » vont au registre
    comme les autres ; la photographie d'une restauration les rend tels quels."""
    from gestion_mp_pro.services import sauvegarde_registre as registre

    assert set(registre.GENRES_DU_REGISTRE) == set(o.GENRES)
    instant = datetime(2026, 10, 8, 2, 0, tzinfo=horloge.FUSEAU)
    with fabrique()() as s:
        for genre in o.GENRES:
            nom = o.nom_de(genre, instant).replace(".dump", f"-registre-{genre}.dump")
            registre.enregistrer(
                s, registre.Entree(nom, genre, reglages().nom_base, 1, 1, True, False, instant)
            )
        lus = {x.fichier: x.genre for x in registre.photographier(s) if "-registre-" in x.fichier}
        assert sorted(lus.values()) == sorted(o.GENRES)
        a_moi = Sauvegarde.fichier.contains("-registre-")
        en_base = s.scalars(select(Sauvegarde.genre).where(a_moi))
        assert {str(g) for g in en_base} >= {"avant_vidage", "avant_mise_a_jour"}
        s.rollback()
