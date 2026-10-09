# ruff: noqa: S603, S607, S608  (outils PostgreSQL ; requêtes d'essai sur nos propres tables)
"""Restaurations réelles : vrai serveur uvicorn, base jetable (lot D10, route 45).

Critères D10 : comptes et empreintes identiques à l'instant de la sauvegarde, moins de 30 s,
autres sessions coupées, pièces jointes revenues et gardées, sauvegarde d'une autre base
refusée ; défauts G-02 (tout ou rien, migration, version plus récente refusée), G-05 (pas de
500 brute), G-08 (le verrou des tâches survit). Hérité :
test_zz_restauration::test_restaurer_depuis_l_ecran_ne_se_bloque_pas (avec l'empreinte avant /
après que Gestion MP ne vérifiait pas, ESSAIS § 15).
"""

from __future__ import annotations

import time

import pytest
from fabriques.exploitation import avec_outils_pg
from fabriques.serveur_jetable import *  # noqa: F403
from fabriques.serveur_jetable import BASE, URL, Serveur, sql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

from gestion_mp_pro.db import Verrou
from gestion_mp_pro.services.installation import revision_attendue

pytestmark = avec_outils_pg

CHANGENT = ("journal", "session", "sauvegarde", "tache_execution")
"""Tables que la restauration réécrit à dessein (journal + 1 ligne, sessions fermées…)."""

CORPS = {"confirmation": "restaurer", "motif": "essai de restauration"}

VERROU_TACHES = (
    "SELECT count(*) FROM pg_locks l JOIN pg_database d ON d.oid = l.database "
    f"WHERE l.locktype = 'advisory' AND l.objid = {int(Verrou.TACHES)} AND d.datname = '{BASE}'"
)


def empreintes() -> dict[str, str]:
    """Nombre de lignes et empreinte du contenu de chaque table (hors `CHANGENT`)."""
    tables = sql("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1").split()
    resultat = {}
    for t in tables:
        if t in CHANGENT:
            continue
        requete = (
            "SELECT count(*) || ' ' || "
            "md5(coalesce(string_agg(x::text, '|' ORDER BY x::text), ''))"
            f" FROM {t} x"
        )
        resultat[t] = sql(requete)
    return resultat


def _sauvegarde_manuelle(s: Serveur) -> str:
    r = s.direction.post("/api/sauvegardes")
    assert r.status_code == 200, r.text
    return str(r.json()["fichiers"][0]["nom"])


def _restaurer(s: Serveur, nom: str) -> dict[str, object]:
    debut = time.monotonic()
    r = s.direction.post(f"/api/sauvegardes/{nom}/restaurer", json=CORPS)
    assert r.status_code == 202, r.text
    assert r.json()["avant"].endswith("-avant-restauration.dump")
    sante = s.attendre("ok")
    assert time.monotonic() - debut < 30
    return sante


def test_restauration_reelle_identique_rapide_sessions_coupees_pieces(serveur: Serveur) -> None:
    s = serveur
    achats = s.client("achats")  # sa session est dans la sauvegarde : elle sera fermée quand même
    (s.pieces / "fournisseur" / "1").mkdir(parents=True)
    (s.pieces / "fournisseur" / "1" / "a.pdf").write_bytes(b"%PDF a")
    nom = _sauvegarde_manuelle(s)
    avant = empreintes()
    # Après la sauvegarde : des écritures, une table tardive, une pièce perdue, une pièce neuve.
    sql("UPDATE parametre SET valeur = 'Autre société' WHERE cle = 'nom_entreprise'")
    sql(
        "INSERT INTO journal (quand, utilisateur_nom, role, action, objet, numero, detail, requete,"
        " adresse) VALUES (now(), 'essai', '', 'repère', 'systeme', '', '', '', '')"
    )
    sql("CREATE TABLE essai_tardive (cle varchar(40) REFERENCES parametre(cle))")
    (s.pieces / "fournisseur" / "1" / "a.pdf").unlink()
    (s.pieces / "fournisseur" / "1" / "b.pdf").write_bytes(b"%PDF b")
    autre_poste = create_engine(URL, poolclass=NullPool).connect()
    autre_poste.execute(text("SELECT 1"))

    sante = _restaurer(s, nom)

    assert empreintes() == avant  # comptes et contenus identiques, table par table
    assert sql("SELECT to_regclass('essai_tardive') IS NULL") == "t"  # rien de mêlé (G-02)
    assert sql("SELECT count(*) FROM journal WHERE action = 'repère'") == "0"
    assert sql("SELECT count(*) FROM journal WHERE action = 'restauration'") == "1"
    assert sante["schema"] == revision_attendue() and sante["etat"] == "ok"
    with pytest.raises(OperationalError):  # l'autre poste a été coupé
        autre_poste.execute(text("SELECT 1"))
    autre_poste.close()
    assert achats.get("/api/moi").status_code == 401  # sa session est fermée
    assert s.direction.get("/api/moi").status_code == 200  # qui restaure reste connecté
    assert (s.pieces / "fournisseur" / "1" / "a.pdf").read_bytes() == b"%PDF a"  # revenue
    assert (s.pieces / "fournisseur" / "1" / "b.pdf").exists()  # gardée
    noms = [f["nom"] for f in s.direction.get("/api/sauvegardes").json()["fichiers"]]
    assert nom in noms and any(n.endswith("avant-restauration.dump") for n in noms)
    assert sql("SELECT count(*) FROM sauvegarde") == str(len(noms))  # registre recalé


def test_une_sauvegarde_ancienne_est_migree(serveur: Serveur) -> None:
    """G-02. Hérité : test_zz_restauration::
    test_restaurer_une_sauvegarde_ancienne_remet_le_schema_a_jour."""
    s = serveur
    s.python(
        "from alembic import command\n"
        "from gestion_mp_pro.services.installation import configuration\n"
        "command.downgrade(configuration(), '0002')\n"
    )
    assert sql("SELECT count(*) FROM parametre WHERE cle = 'toler_tva_import'") == "0"
    nom = _sauvegarde_manuelle(s)
    s.python("from gestion_mp_pro.services.installation import migrer\nmigrer()\n")
    sql("CREATE TABLE essai_tardive (cle varchar(40) REFERENCES parametre(cle))")
    _restaurer(s, nom)
    assert sql("SELECT version_num FROM alembic_version") == revision_attendue()
    assert sql("SELECT count(*) FROM parametre WHERE cle = 'toler_tva_import'") == "1"
    assert sql("SELECT to_regclass('essai_tardive') IS NULL") == "t"


def _attendre_la_fin_du_verrou(s: Serveur) -> None:
    """Le contrôle de disponibilité est relu toutes les 2 s : attendre que l'API rouvre."""
    for _ in range(50):
        if s.direction.get("/api/sauvegardes").status_code == 200:
            return
        time.sleep(0.2)
    raise AssertionError("l'API ne rouvre pas après un refus de restauration")


def test_ce_qui_ne_se_restaure_pas_est_refuse_sans_rien_toucher(serveur: Serveur) -> None:
    """Version plus récente (G-02), autre base (X11), illisible (G-05), introuvable, mot."""
    s = serveur
    sql("UPDATE alembic_version SET version_num = '9999'")
    futur = _sauvegarde_manuelle(s)
    sql(f"UPDATE alembic_version SET version_num = '{revision_attendue()}'")
    sql(
        "INSERT INTO journal (quand, utilisateur_nom, role, action, objet, numero, detail, requete,"
        " adresse) VALUES (now(), 'essai', '', 'repère', 'systeme', '', '', '', '')"
    )
    r = s.direction.post(f"/api/sauvegardes/{futur}/restaurer", json=CORPS)
    assert r.status_code == 409 and "plus récente" in r.json()["detail"], r.text
    _attendre_la_fin_du_verrou(s)
    voisine = s.sauvegardes / "gestion-mp-pro-2026-10-01-120000-manuelle.dump"
    subprocess_dump(voisine)
    r = s.direction.post(f"/api/sauvegardes/{voisine.name}/restaurer", json=CORPS)
    assert r.status_code == 409 and r.json()["code"] == "sauvegarde_autre_base", r.text
    assert f"pas de « {BASE} »" in r.json()["detail"]
    _attendre_la_fin_du_verrou(s)
    illisible = s.sauvegardes / "gestion-mp-pro-2026-10-02-120000-manuelle.dump"
    illisible.write_bytes(b"ceci n'est pas une sauvegarde")
    r = s.direction.post(f"/api/sauvegardes/{illisible.name}/restaurer", json=CORPS)
    assert r.status_code == 422 and "illisible" in r.json()["detail"]
    assert "rien n'a été restauré" in r.json()["detail"]
    _attendre_la_fin_du_verrou(s)
    assert s.direction.post(
        "/api/sauvegardes/..%2F..%2Fx.dump/restaurer", json=CORPS
    ).status_code in (
        404,
        422,
    )
    r = s.direction.post(
        f"/api/sauvegardes/{futur}/restaurer", json={**CORPS, "confirmation": "oui"}
    )
    assert r.status_code == 422 and r.json()["code"] == "confirmation_requise"
    assert sql("SELECT count(*) FROM journal WHERE action = 'repère'") == "1"  # rien n'a bougé
    assert sql("SELECT count(*) FROM journal WHERE action = 'restauration'") == "0"
    assert not list(s.sauvegardes.glob("*avant-restauration*"))  # refusée avant d'agir


def subprocess_dump(cible: object) -> None:
    """Une sauvegarde de la base d'essai commune (une autre base que celle du serveur)."""
    import subprocess

    from gestion_mp_pro.config import reglages

    subprocess.run(["pg_dump", "-Fc", "-f", str(cible), reglages().nom_base], check=True)


@pytest.mark.parametrize("serveur", [True], indirect=True)
def test_la_restauration_garde_le_verrou_des_taches(serveur: Serveur) -> None:
    """G-08 (`test_zz_restauration::test_restauration_garde_le_verrou_des_taches`)."""
    s = serveur
    for _ in range(100):
        if sql(VERROU_TACHES) == "1" and list(s.sauvegardes.glob("*-quotidienne.dump")):
            break
        time.sleep(0.1)
    assert sql(VERROU_TACHES) == "1"
    assert list(s.sauvegardes.glob("*-quotidienne.dump"))  # la quotidienne, dès le démarrage
    _restaurer(s, _sauvegarde_manuelle(s))
    assert sql(VERROU_TACHES) == "1"  # toujours un porteur, et un seul
