"""Le calendrier des sauvegardes automatiques (décision X7 de Mohamed, 15/10/2026).

Quotidienne chaque soir à 22:00, hebdomadaire le dimanche à 22:00, mensuelle le dernier jour du
mois à 22:00, à l'heure de l'**usine** (même si le système est en UTC) ; rattrapage au passage
suivant, une seule fois ; conservation 14 / 8 / 12, mensuelle de fin décembre gardée, manuelles
et « avant-* » jamais effacées. Horloge fixée par `horloge.fixer` ; dossiers temporaires
seulement (`fabriques.exploitation.dossiers`).
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from fabrique import *  # noqa: F403
from fabriques.exploitation import *  # noqa: F403
from fabriques.exploitation import Dossiers, avec_outils_pg
from fastapi.testclient import TestClient
from sqlalchemy import text

from gestion_mp_pro.db import moteur
from gestion_mp_pro.services import execution, horloge, installation
from gestion_mp_pro.services import sauvegarde as service
from gestion_mp_pro.services import sauvegarde_calendrier as cal
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services.sauvegarde_etat import AUCUNE_RECENTE


def _a(jour: str, heure: str = "22:00:00") -> datetime:
    """Un instant à l'heure de l'usine (« 2026-10-18 », « 21:59:59 »)."""
    return datetime.fromisoformat(f"{jour}T{heure}").replace(tzinfo=horloge.FUSEAU)


def _vide(d: Path, genre: str, instant: datetime) -> str:
    """Un faux fichier de sauvegarde (la purge et le calendrier ne lisent que les noms)."""
    d.mkdir(parents=True, exist_ok=True)
    nom = o.nom_de(genre, instant)
    (d / nom).write_bytes(b"x")
    o.archive_de(d / nom).write_bytes(b"x")
    return nom


def _genres(d: Path) -> list[str]:
    """Les genres des fichiers d'un dossier, triés."""
    return sorted(lu.genre for f in d.glob("*.dump") if (lu := o.lire_nom(f.name)) is not None)


def test_la_quotidienne_a_22_h_pas_avant_une_seule_par_soir() -> None:
    hier = {"quotidienne": [_a("2026-10-14", "22:05:00")]}
    assert "quotidienne" not in cal.dues(hier, _a("2026-10-15", "21:59:59"))
    assert "quotidienne" in cal.dues(hier, _a("2026-10-15", "22:00:00"))
    ce_soir = {"quotidienne": [_a("2026-10-15", "22:00:00")]}
    for heure in ("22:15:00", "23:59:59"):
        assert "quotidienne" not in cal.dues(ce_soir, _a("2026-10-15", heure))
    assert "quotidienne" not in cal.dues(ce_soir, _a("2026-10-16", "21:45:00"))


def test_soir_manque_rattrape_une_seule_fois_le_lendemain_matin() -> None:
    """Mac éteint deux soirs : une seule quotidienne au démarrage, puis la suivante à 22 h."""
    faites = {"quotidienne": [_a("2026-10-12", "22:05:00")]}
    matin = _a("2026-10-15", "08:00:00")
    assert cal.dues(faites, matin).count("quotidienne") == 1
    faites["quotidienne"].append(matin)
    assert "quotidienne" not in cal.dues(faites, _a("2026-10-15", "08:15:00"))
    assert "quotidienne" in cal.dues(faites, _a("2026-10-15", "22:00:00"))


def test_l_hebdomadaire_le_dimanche_a_22_h_rattrapee_le_lundi() -> None:
    faites = {"hebdomadaire": [_a("2026-10-11", "22:05:00")]}  # dimanche 11 octobre
    for jour in ("2026-10-12", "2026-10-15", "2026-10-17"):  # lundi, jeudi, samedi 22 h
        assert "hebdomadaire" not in cal.dues(faites, _a(jour, "22:30:00"))
    assert "hebdomadaire" not in cal.dues(faites, _a("2026-10-18", "21:59:59"))
    assert "hebdomadaire" in cal.dues(faites, _a("2026-10-18", "22:00:00"))
    assert "hebdomadaire" in cal.dues(faites, _a("2026-10-19", "08:00:00"))  # rattrapée lundi
    faites["hebdomadaire"].append(_a("2026-10-19", "08:00:00"))
    assert "hebdomadaire" not in cal.dues(faites, _a("2026-10-25", "21:00:00"))


@pytest.mark.parametrize(
    ("fin", "veille"),
    [
        ("2026-10-31", "2026-10-30"),
        ("2026-11-30", "2026-11-29"),
        ("2027-02-28", "2027-02-27"),
        ("2028-02-29", "2028-02-28"),
        ("2026-12-31", "2026-12-30"),
    ],
)
def test_la_mensuelle_le_dernier_jour_du_mois_a_22_h(fin: str, veille: str) -> None:
    faites = {"mensuelle": [_a(veille, "23:00:00") - timedelta(days=27)]}  # le mois d'avant
    assert "mensuelle" not in cal.dues(faites, _a(veille, "22:30:00"))
    assert "mensuelle" not in cal.dues(faites, _a(fin, "21:59:59"))
    assert "mensuelle" in cal.dues(faites, _a(fin, "22:00:00"))
    assert cal.derniere_echeance("mensuelle", _a(fin, "22:00:00") + timedelta(days=3)) == _a(fin)


def test_premier_demarrage_au_plus_une_de_chaque_genre() -> None:
    assert cal.dues({}, _a("2026-10-15", "15:00:00")) == list(cal.AUTOMATIQUES)
    # la quotidienne de l'ancienne règle (après minuit) couvre l'échéance de la veille au soir
    apres_minuit = {"quotidienne": [_a("2026-10-15", "00:05:28")]}
    assert cal.dues(apres_minuit, _a("2026-10-15", "18:00:00")) == ["hebdomadaire", "mensuelle"]


_SOUS_UTC = """
import json, sys
from datetime import datetime
from zoneinfo import ZoneInfo
from gestion_mp_pro.services import horloge, sauvegarde_calendrier as cal, sauvegarde_outils as o
instant = datetime.fromtimestamp(float(sys.argv[1]), horloge.FUSEAU)
print(json.dumps({
    "fuseau": str(horloge.FUSEAU),
    "maintenant": abs((horloge.maintenant().replace(tzinfo=None)
                       - datetime.now(ZoneInfo(sys.argv[2])).replace(tzinfo=None)).total_seconds()),
    "dues": cal.dues({"quotidienne": [], "hebdomadaire": [], "mensuelle": []}, instant),
    "echeances": [cal.derniere_echeance(g, instant).isoformat() for g in cal.AUTOMATIQUES],
    "nom": o.nom_de("quotidienne", instant),
}))
"""


@pytest.mark.parametrize("tz", ["UTC", "Asia/Tokyo", "America/New_York"])
@pytest.mark.parametrize("fuseau", ["Africa/Casablanca", "Europe/Paris"])
def test_22_h_dimanche_et_fin_de_mois_a_l_heure_de_l_usine_meme_si_le_systeme_est_en_utc(
    tz: str, fuseau: str
) -> None:
    """Serveur loué ou conteneur au fuseau UTC (ou autre) : l'heure de l'usine décide."""
    import json
    from zoneinfo import ZoneInfo

    usine = ZoneInfo(fuseau)
    instant = datetime(2027, 1, 31, 22, 0, 30, tzinfo=usine)  # dimanche 31 janvier, 22 h
    env = {**os.environ, "TZ": tz, "GESTIONMPPRO_FUSEAU": fuseau}
    sortie = subprocess.run(  # noqa: S603 — notre interpréteur, notre script
        [sys.executable, "-c", _SOUS_UTC, str(instant.timestamp()), fuseau],
        capture_output=True, text=True, env=env, check=True, timeout=60,
    )  # fmt: skip
    lu = json.loads(sortie.stdout)
    assert lu["fuseau"] == fuseau and lu["maintenant"] < 60  # l'horloge à l'heure de l'usine
    attendue = datetime(2027, 1, 31, 22, 0, tzinfo=usine).isoformat()
    assert lu["echeances"] == [attendue] * 3
    assert lu["dues"] == ["quotidienne", "hebdomadaire", "mensuelle"]
    assert lu["nom"] == "gestion-mp-pro-2027-01-31-220030-quotidienne.dump"


def test_purge_14_8_12_fin_decembre_gardee_manuelles_jamais(dossiers: Dossiers) -> None:
    """G-09 : même rotation dans la copie ; manuelles et « avant-* » jamais purgées ; les
    anciennes quotidiennes « après minuit » suivent la règle des 14."""
    jamais = ["manuelle", "avant-restauration", "avant-vidage", "avant-mise-a-jour"]
    jamais += ["avant-reprise", "reference-vide"]
    debut = _a("2024-06-01")
    for d in (dossiers.sauvegardes, dossiers.copie):
        for i in range(40):
            _vide(d, "quotidienne", debut + timedelta(days=i))
        _vide(d, "quotidienne", _a("2024-05-01", "00:05:28"))  # gardée par l'ancienne règle
        for i in range(12):
            _vide(d, "hebdomadaire", _a("2024-06-02") + timedelta(weeks=i))
        for a, m, j in [(2023, 11, 30), (2023, 12, 31), (2024, 1, 2)]:  # 2 jan. : rattrapage
            _vide(d, "mensuelle", _a(f"{a}-{m:02d}-{j:02d}", "22:10:00"))
        for m in range(2, 14):  # février 2024 à janvier 2025
            fin = cal._fin_de_mois(date(2024 + (m > 12), (m - 1) % 12 + 1, 1))
            _vide(d, "mensuelle", _a(fin.isoformat(), "22:10:00"))
        for i, genre in enumerate(jamais):
            _vide(d, genre, _a("2023-01-01") + timedelta(days=i))
    effaces = service.purger()
    assert len(effaces) == 41 - 14 + 12 - 8 + 15 - 12 - 2
    for d in (dossiers.sauvegardes, dossiers.copie):
        restants = _genres(d)
        assert restants.count("quotidienne") == 14 and restants.count("hebdomadaire") == 8
        mensuelles = sorted(lu.instant.date().isoformat() for f in d.glob("*mensuelle.dump")
                            if (lu := o.lire_nom(f.name)))  # fmt: skip
        assert mensuelles[:2] == ["2023-12-31", "2024-01-02"]  # fin décembre 2023, deux fois
        assert len(mensuelles) == 14 and mensuelles[-1] == "2025-01-31"
        assert all(restants.count(g) == 1 for g in jamais)
        archives = {f.name.removesuffix(o.SUFFIXE_PIECES) for f in d.glob("*" + o.SUFFIXE_PIECES)}
        assert archives == {f.name for f in d.glob("*.dump")}


def test_un_fichier_ouvert_ailleurs_ne_fait_pas_echouer_la_purge(
    dossiers: Dossiers, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows : un fichier à purger tenu ouvert (antivirus, copie) refuse l'effacement ; il
    reste, n'est pas annoncé effacé, et les autres s'effacent quand même."""
    noms = [_vide(dossiers.sauvegardes, "quotidienne", _a("2024-06-01") + timedelta(days=i))
            for i in range(16)]  # fmt: skip
    tenu = dossiers.sauvegardes / noms[0]
    efface = Path.unlink

    def unlink(self: Path, missing_ok: bool = False) -> None:
        if self == tenu:
            raise PermissionError(32, "fichier utilisé par un autre processus")
        efface(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)
    assert service.purger() == [noms[1]]
    assert tenu.exists() and not (dossiers.sauvegardes / noms[1]).exists()


@avec_outils_pg
def test_trois_fichiers_le_dimanche_31_puis_rien_puis_copie_refaite(dossiers: Dossiers) -> None:
    from gestion_mp_pro.taches import sauvegarde_du_jour

    _vide(dossiers.sauvegardes, "quotidienne", _a("2027-01-30", "22:05:00"))
    _vide(dossiers.sauvegardes, "hebdomadaire", _a("2027-01-24", "22:05:00"))
    _vide(dossiers.sauvegardes, "mensuelle", _a("2026-12-31", "22:05:00"))
    with horloge.figee(_a("2027-01-31", "21:59:00")):
        assert service.automatiques() == []
    with horloge.figee(_a("2027-01-31", "22:05:00")):
        faites = service.automatiques()
        assert [f.genre for f in faites] == ["quotidienne", "hebdomadaire", "mensuelle"]
        assert [f.nature for f in faites] == ["quotidienne", "hebdomadaire", "mensuelle"]
        assert all(f.copie and f.quand == horloge.maintenant() for f in faites)
    with horloge.figee(_a("2027-01-31", "22:20:00")):
        assert service.automatiques() == []  # une seule par soir
        for f in dossiers.copie.iterdir():
            f.unlink()
        sauvegarde_du_jour.executer()
    assert _genres(dossiers.copie) == ["hebdomadaire", "mensuelle", "quotidienne"]


@avec_outils_pg
@pytest.mark.parametrize(("hier", "alerte"), [("22:14:00", None), ("19:00:00", AUCUNE_RECENTE)])
def test_l_alerte_ne_sonne_pas_d_un_soir_a_l_autre(
    hier: str, alerte: str | None, dossiers: Dossiers, anonyme: TestClient
) -> None:
    """22:14 la veille, 22:13 ce soir (avant le passage) : 24 h, pas d'alerte ; 27 h : alerte."""
    _vide(dossiers.sauvegardes, "quotidienne", _a("2026-10-07", hier))
    with horloge.figee(_a("2026-10-08", "22:13:00")):
        execution.noter("sauvegarde", horloge.maintenant())
        assert (anonyme.get("/api/sante").json()["sauvegarde_alerte"] or None) == alerte


def test_0010_hebdomadaire_et_mensuelle_aller_retour() -> None:
    """0010 : les deux genres admis au registre ; le retour arrière les retire du registre."""
    cfg = installation.configuration()
    permis = "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"
    with moteur().connect() as c, c.begin():
        genres = str(c.execute(text(permis), {"n": "ck_sauvegarde_genre_enum"}).scalar())
        assert "'hebdomadaire'" in genres and "'mensuelle'" in genres
        c.execute(
            text(
                "INSERT INTO sauvegarde (fichier, genre, base) VALUES"
                " ('h.dump', 'hebdomadaire', 'b'), ('m.dump', 'mensuelle', 'b'),"
                " ('q.dump', 'quotidienne', 'b')"
            )
        )
        cfg.attributes["connection"] = c
        command.downgrade(cfg, "0009")
        assert "'mensuelle'" not in str(
            c.execute(text(permis), {"n": "ck_sauvegarde_genre_enum"}).scalar()
        )
        assert list(c.execute(text("SELECT fichier FROM sauvegarde")).scalars()) == ["q.dump"]
        command.upgrade(cfg, "head")
        c.execute(text("DELETE FROM sauvegarde"))
    assert not installation.schema_en_retard()
