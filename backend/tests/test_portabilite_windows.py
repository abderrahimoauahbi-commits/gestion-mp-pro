"""Portabilité du serveur vers Windows (docs/lots/WINDOWS-SERVEUR.md) : chaque correction est
éprouvée ici, sur le Mac, en simulant ce que Windows ferait (`pg_dump.exe`, lecteur `C:`, partage
`\\\\hôte\\…`, profil avec espace, page de code de la console, absence d'uvloop)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from gestion_mp_pro import config
from gestion_mp_pro.config import Reglages, dossier_par_defaut
from gestion_mp_pro.main import creer_application
from gestion_mp_pro.services import sauvegarde_outils as o
from gestion_mp_pro.services.chemins import relatif_sur
from gestion_mp_pro.services.sauvegarde_pieces import _sur

# --- dossiers par défaut -------------------------------------------------------------------


def test_dossiers_par_defaut_sous_programdata_sous_windows() -> None:
    assert str(dossier_par_defaut("sauvegardes", "win32")) == (
        r"C:\ProgramData\Gestion MP PRO\sauvegardes"
    )
    assert str(dossier_par_defaut("pieces", "win32")) == r"C:\ProgramData\Gestion MP PRO\pieces"


def test_dossiers_par_defaut_inchanges_sur_le_mac() -> None:
    assert dossier_par_defaut("sauvegardes", "darwin") == Path("~/gestion-mp-pro-sauvegardes")
    assert dossier_par_defaut("pieces", "linux") == Path("~/gestion-mp-pro-pieces")


# --- outils de PostgreSQL ------------------------------------------------------------------


def _reglages_pg_bin(monkeypatch: pytest.MonkeyPatch, dossier: Path | None) -> None:
    monkeypatch.setattr(o, "reglages", lambda: SimpleNamespace(pg_bin=dossier))


def test_pg_bin_trouve_pg_dump_exe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """GESTIONMPPRO_PG_BIN=C:\\Program Files\\PostgreSQL\\16\\bin : `pg_dump.exe`, pas `pg_dump`."""
    (tmp_path / "pg_dump.exe").write_bytes(b"MZ")
    _reglages_pg_bin(monkeypatch, tmp_path)
    monkeypatch.setattr(o, "SUFFIXES", (".exe", ""))
    assert o.outil("pg_dump") == tmp_path / "pg_dump.exe"
    assert o.outil("psql") is None


def test_suffixes_du_systeme() -> None:
    assert o.SUFFIXES == ((".exe", "") if sys.platform == "win32" else ("",))


def test_pg_bin_sur_le_mac_inchange(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "pg_dump").write_bytes(b"#!")
    (tmp_path / "pg_restore.exe").write_bytes(b"MZ")
    _reglages_pg_bin(monkeypatch, tmp_path)
    monkeypatch.setattr(o, "SUFFIXES", ("",))
    assert o.outil("pg_dump") == tmp_path / "pg_dump"
    assert o.outil("pg_restore") is None


def test_dossiers_connus_de_windows_et_version_la_plus_haute_d_abord(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert "C:/Program Files/PostgreSQL/*/bin" in o.DOSSIERS
    for version in ("9.6", "16", "17"):
        (tmp_path / version / "bin").mkdir(parents=True)
        (tmp_path / version / "bin" / "pg_dump.exe").write_bytes(b"MZ")
    _reglages_pg_bin(monkeypatch, None)
    monkeypatch.setattr(o, "SUFFIXES", (".exe", ""))
    monkeypatch.setattr(o.shutil, "which", lambda _nom: None)
    monkeypatch.setattr(o, "DOSSIERS", (f"{tmp_path}/*/bin",))
    assert o.outil("pg_dump") == tmp_path / "17" / "bin" / "pg_dump.exe"


def test_passfile_dans_un_dossier_avec_espaces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Profil Windows « Jean Dupont » : libpq refusait l'espace du chemin non encodé."""
    profil = tmp_path / "Jean Dupont %20 & co"
    profil.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(profil))
    with o.adresse_base("postgresql+psycopg://gestion_mp_pro:s3cret@localhost/x_essai") as a:
        lu = conninfo_to_dict(a)
        fichier = Path(str(lu["passfile"]))
        assert fichier.parent.parent == profil
        assert fichier.read_text(encoding="utf-8") == "*:*:*:*:s3cret\n"
        assert "s3cret" not in a
        assert lu["dbname"] == "x_essai"
    assert not fichier.exists()


def test_le_mot_de_passe_ne_passe_jamais_sur_la_ligne_de_commande() -> None:
    """Défaut trouvé par ce lot : `URL.set(password=None)` gardait le mot de passe dans
    l'adresse donnée à pg_dump (lisible des autres comptes dans la liste des processus)."""
    base = "postgresql+psycopg://gestion_mp_pro:s3cret@srv:5433/x_essai?sslmode=require"
    with o.adresse_base(base) as adresse:
        assert adresse.startswith("postgresql://gestion_mp_pro@srv:5433/x_essai?sslmode=require&")
        assert "s3cret" not in adresse
        assert conninfo_to_dict(adresse)["sslmode"] == "require"
    with o.adresse_base("postgresql+psycopg:///x_essai") as adresse:
        assert adresse == "postgresql:///x_essai"


def test_sortie_d_un_outil_dans_une_autre_page_de_code() -> None:
    """Un message de pg_restore en cp850/cp1252 ne fait jamais tomber la sauvegarde."""
    script = "import sys; sys.stdout.buffer.write(b'\\xe9chec \\x82'); sys.exit(3)"
    sortie = o.lancer([sys.executable, "-c", script])
    assert sortie.returncode == 3
    assert sortie.stdout == "\ufffdchec \ufffd"
    assert o.raison(sortie).endswith("chec \ufffd")


# --- noms venus de l'extérieur -------------------------------------------------------------

DANGEREUX = [
    r"\\hote\partage\x",
    "//hote/partage/x",
    r"C:\Windows\win.ini",
    "C:/Windows/win.ini",
    "C:win.ini",
    "/etc/passwd",
    r"\Windows\win.ini",
    "index.html:Zone.Identifier",
    "",
]


@pytest.mark.parametrize("nom", DANGEREUX)
def test_noms_ancres_refuses(nom: str) -> None:
    assert not relatif_sur(nom)


@pytest.mark.parametrize("nom", ["index.html", "assets/app-1a2b.js", "commande/3/ab12.pdf"])
def test_noms_relatifs_acceptes(nom: str) -> None:
    assert relatif_sur(nom)


@pytest.mark.parametrize("nom", DANGEREUX)
def test_archive_de_pieces_sans_lecteur_ni_partage(nom: str, tmp_path: Path) -> None:
    assert _sur(tmp_path, nom) is None
    assert _sur(tmp_path, "commande/3/ab12.pdf") == (tmp_path / "commande/3/ab12.pdf").resolve()


@pytest.fixture
def ecran(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<p>accueil</p>", encoding="utf-8")
    (tmp_path / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize(
    "adresse",
    ["/%5C%5Chote%5Cpartage%5Cx", "/C:/Windows/win.ini", "/C:%5CWindows%5Cwin.ini"],
)
def test_ecran_n_interroge_jamais_un_partage(
    adresse: str, ecran: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sous Windows, `racine / "\\\\hôte\\partage"` sortirait de la racine : jamais touché."""
    vus: list[Path] = []
    vrai_is_file = Path.is_file

    def espion(chemin: Path) -> bool:
        vus.append(chemin)
        return vrai_is_file(chemin)

    app = creer_application(Reglages(ecran=ecran))
    monkeypatch.setattr(Path, "is_file", espion)
    reponse = TestClient(app).get(adresse)
    assert reponse.status_code == 200
    assert reponse.text == "<p>accueil</p>"
    assert vus == []  # avant la correction : `is_file` sur le chemin joint (partage compris)


def test_ecran_sert_toujours_ses_fichiers(ecran: Path) -> None:
    client = TestClient(creer_application(Reglages(ecran=ecran)))
    assert client.get("/manifest.webmanifest").text == "{}"
    assert client.get("/achats/commandes").text == "<p>accueil</p>"
    assert client.get("/../../etc/passwd").text == "<p>accueil</p>"


# --- démarrage sans uvloop -----------------------------------------------------------------


def test_uvicorn_demarre_sans_uvloop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows n'a pas uvloop (absent de requirements-windows.lock) : boucle asyncio."""
    import asyncio

    from uvicorn.loops.auto import auto_loop_factory

    monkeypatch.setitem(sys.modules, "uvloop", None)
    boucle = auto_loop_factory()()
    try:
        assert type(boucle).__module__.startswith("asyncio")
    finally:
        boucle.close()
    assert isinstance(boucle, asyncio.AbstractEventLoop)


def test_le_fuseau_de_l_usine_est_connu() -> None:
    """Sous Windows, zoneinfo lit le paquet tzdata (dépendance du serveur Windows)."""
    assert str(config.reglages().zone) == config.reglages().fuseau
