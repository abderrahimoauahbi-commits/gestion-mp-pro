"""Horloge de l'usine et base (verrous, fuseau, délai) : le socle des autres lots (lot S0)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import text

from gestion_mp_pro import db
from gestion_mp_pro.services import horloge


def test_horloge_figee_par_les_essais() -> None:
    assert horloge.est_figee()
    assert horloge.aujourd_hui() == date(2026, 10, 8)
    assert horloge.maintenant().utcoffset() is not None
    assert str(horloge.maintenant().tzinfo) == "Africa/Casablanca"


def test_horloge_figee_le_temps_d_un_bloc() -> None:
    with horloge.figee(date(2026, 12, 31)) as instant:
        assert instant == datetime(2026, 12, 31, 12, 0, tzinfo=horloge.FUSEAU)
        assert horloge.aujourd_hui() == date(2026, 12, 31)
    assert horloge.aujourd_hui() == date(2026, 10, 8)
    with horloge.figee(datetime(2027, 1, 1, 0, 30)):  # noqa: DTZ001 — instant sans fuseau voulu
        assert horloge.maintenant().tzinfo == horloge.FUSEAU


def test_horloge_reelle() -> None:
    horloge.fixer(None)
    assert not horloge.est_figee()
    assert horloge.maintenant().tzinfo == horloge.FUSEAU


def test_connexion_a_l_heure_de_l_usine_et_delai() -> None:
    with db.moteur().connect() as c:
        assert c.execute(text("SHOW timezone")).scalar() == "Africa/Casablanca"
        assert c.execute(text("SHOW statement_timeout")).scalar() == "30s"
        assert str(c.execute(text("SELECT current_database()")).scalar()).endswith("_essai")


def test_verrou_consultatif_vu_dans_pg_locks() -> None:
    assert not db.verrou_tenu(db.Verrou.RESTAURATION)
    with db.moteur().connect() as tenant:
        assert db.essayer_verrou(tenant, db.Verrou.RESTAURATION)
        assert db.verrou_tenu(db.Verrou.RESTAURATION)
        with db.moteur().connect() as autre:
            assert not db.essayer_verrou(autre, db.Verrou.RESTAURATION)
        db.DISPONIBILITE.controle_le = 0.0
        assert db.motif_indisponibilite() == "restauration_en_cours"
        db.liberer(tenant, db.Verrou.RESTAURATION)
    db.DISPONIBILITE.controle_le = 0.0
    assert db.motif_indisponibilite() is None


def test_verrou_de_transaction() -> None:
    with db.fabrique()() as s:
        db.verrouiller(s, db.Verrou.ORDRES)
        assert db.verrou_tenu(db.Verrou.ORDRES)
        s.rollback()
    assert not db.verrou_tenu(db.Verrou.ORDRES)


def test_make_notice_regenere_la_notice() -> None:
    """ARCHITECTURE § 10.2 (A7) : `make notice` régénère docs/NOTICE.md par
    scripts/generer_notice.py (l'essai de l'écran vérifie qu'elle est à jour)."""
    import shutil
    import subprocess
    from pathlib import Path

    racine = Path(__file__).resolve().parents[2]
    make = shutil.which("make")
    assert make is not None
    sortie = subprocess.run(  # noqa: S603 — make du poste, cible à nous, rien n'est exécuté (-n)
        [make, "-n", "notice"], cwd=racine, capture_output=True, text=True, check=True
    ).stdout
    assert "scripts/generer_notice.py" in sortie and "--verifier" not in sortie
    aide = subprocess.run(  # noqa: S603
        [make, "aide"], cwd=racine, capture_output=True, text=True, check=True
    ).stdout
    assert any(ligne.startswith("notice") for ligne in aide.splitlines())
