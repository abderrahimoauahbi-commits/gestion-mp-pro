"""Configuration (ARCHITECTURE § 16, § 14.1) : une seule lecture de l'environnement, valeurs par
défaut, coexistence avec Gestion MP sans rien partager (lot S0)."""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from gestion_mp_pro import config
from gestion_mp_pro.config import Reglages
from gestion_mp_pro.db import PLAGE_VERROUS, VERROUS

PAQUET = Path(config.__file__).parent
ACCUEIL = Path.home()

VARIABLES = """BASE FUSEAU PORT ECOUTE HTTPS ADRESSE PROCESSUS TACHES SESSION_JOURS SAUVEGARDES
SAUVEGARDES_COPIE PIECES PG_BIN ECRAN SMTP_HOTE SMTP_PORT SMTP_UTILISATEUR SMTP_MOT_DE_PASSE
SMTP_EXPEDITEUR JOURNAL_NIVEAU JOURNAL_FICHIER SOURCE_GESTION_MP PIECES_GESTION_MP
ESSAIS_COMPLETS""".split()


@pytest.fixture
def sans_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    for nom in VARIABLES:
        monkeypatch.delenv(f"GESTIONMPPRO_{nom}", raising=False)


def _lectures_environnement(fichier: Path) -> list[str]:
    """Les lectures de l'environnement d'un fichier (`os.environ`, `os.getenv`, `putenv`…)."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    trouvees: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Attribute) and noeud.attr in {
            "environ",
            "getenv",
            "putenv",
            "unsetenv",
            "environb",
            "tzset",
        }:
            trouvees.append(f"{fichier.name}:{noeud.lineno} {noeud.attr}")
        if isinstance(noeud, ast.ImportFrom) and noeud.module == "os":
            noms = {a.name for a in noeud.names}
            if noms & {"environ", "getenv", "putenv", "environb"}:
                trouvees.append(f"{fichier.name}:{noeud.lineno} from os import")
    return trouvees


def test_aucune_lecture_de_l_environnement_hors_config() -> None:
    fautes = [
        faute
        for fichier in sorted(PAQUET.rglob("*.py"))
        if fichier != Path(config.__file__)
        for faute in _lectures_environnement(fichier)
    ]
    assert fautes == []


def test_config_ne_touche_pas_au_fuseau_du_processus() -> None:
    assert _lectures_environnement(Path(config.__file__)) == []


def test_toutes_les_variables_de_l_architecture() -> None:
    assert {f"GESTIONMPPRO_{n}".lower() for n in VARIABLES} == {
        f"gestionmppro_{n}" for n in Reglages.model_fields
    }


def test_valeurs_par_defaut(sans_environnement: None) -> None:
    r = Reglages()
    assert r.base == "postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro"
    assert r.nom_base == "gestion_mp_pro"
    assert (r.fuseau, str(r.zone)) == ("Africa/Casablanca", "Africa/Casablanca")
    assert (r.port, r.ecoute, r.https, r.adresse) == (8050, "127.0.0.1", False, "")
    assert (r.processus, r.taches, r.session_jours) == (2, True, 30)
    assert r.sauvegardes == ACCUEIL / "gestion-mp-pro-sauvegardes"
    assert r.dossier_sauvegardes == ACCUEIL / "gestion-mp-pro-sauvegardes" / "gestion_mp_pro"
    assert r.dossier_pieces == ACCUEIL / "gestion-mp-pro-pieces" / "gestion_mp_pro"
    assert r.sauvegardes_copie is None and r.pg_bin is None and r.journal_fichier is None
    assert r.ecran == config.RACINE / "frontend" / "dist"
    assert (r.smtp_hote, r.smtp_port, r.smtp_utilisateur, r.expediteur) == ("", 587, "", "")
    assert r.smtp_mot_de_passe.get_secret_value() == ""
    assert r.journal_niveau == "INFO"
    assert r.source_gestion_mp == "postgresql+psycopg:///gestion_mp"
    assert r.pieces_gestion_mp == ACCUEIL / "gestion-mp-pieces"
    assert r.essais_complets is False


def test_lecture_de_l_environnement(
    monkeypatch: pytest.MonkeyPatch, sans_environnement: None
) -> None:
    monkeypatch.setenv("GESTIONMPPRO_PORT", "8051")
    monkeypatch.setenv("GESTIONMPPRO_HTTPS", "1")
    monkeypatch.setenv("GESTIONMPPRO_TACHES", "0")
    monkeypatch.setenv("GESTIONMPPRO_BASE", "postgresql+psycopg:///gestion_mp_pro_parite")
    monkeypatch.setenv("GESTIONMPPRO_SAUVEGARDES_COPIE", "")
    monkeypatch.setenv("GESTIONMPPRO_JOURNAL_NIVEAU", "debug")
    monkeypatch.setenv("GESTIONMPPRO_ADRESSE", "https://mp.usine.local/")
    monkeypatch.setenv("GESTIONMPPRO_SMTP_UTILISATEUR", "mp@usine.ma")
    r = Reglages()
    assert (r.port, r.https, r.taches, r.journal_niveau) == (8051, True, False, "DEBUG")
    assert r.dossier_sauvegardes.name == "gestion_mp_pro_parite"
    assert r.sauvegardes_copie is None
    assert r.adresse == "https://mp.usine.local"
    assert r.expediteur == "mp@usine.ma"
    assert "mp@usine.ma" not in repr(r.smtp_mot_de_passe)


@pytest.mark.parametrize(
    ("nom", "valeur"),
    [("FUSEAU", "Mars/Olympus"), ("PORT", "0"), ("PORT", "huit"), ("JOURNAL_NIVEAU", "BAVARD")],
)
def test_valeur_fausse_refusee_au_demarrage(
    monkeypatch: pytest.MonkeyPatch, sans_environnement: None, nom: str, valeur: str
) -> None:
    monkeypatch.setenv(f"GESTIONMPPRO_{nom}", valeur)
    with pytest.raises(ValidationError):
        Reglages()


def test_lue_une_seule_fois() -> None:
    assert config.reglages() is config.reglages()


GESTION_MP = {
    "ports": {8020, 8030, 8040},
    "bases": {"gestion_mp", "gestion_mp_comparaison", "gmao", "gmao_pro"},
    "cookies": {"gestion_mp_session"},
    "entetes": {"X-Gestion-MP"},
    "dossiers": {ACCUEIL / "gestion-mp-sauvegardes", ACCUEIL / "gestion-mp-pieces"},
    "verrous": set(range(7426101, 7426111)),
}


def test_coexistence_avec_gestion_mp(sans_environnement: None) -> None:
    r = Reglages()
    assert r.port == 8050 and r.port not in GESTION_MP["ports"]
    assert r.nom_base not in GESTION_MP["bases"]
    assert config.COOKIE_SESSION == "gestion_mp_pro_session"
    assert config.COOKIE_SESSION not in GESTION_MP["cookies"]
    assert config.COOKIE_APPAREIL not in GESTION_MP["cookies"]
    assert config.ENTETE_ANTI_FALSIFICATION == "X-Gestion-MP-PRO"
    assert config.ENTETE_ANTI_FALSIFICATION not in GESTION_MP["entetes"]
    for dossier in (r.dossier_sauvegardes, r.dossier_pieces):
        for autre in GESTION_MP["dossiers"]:
            assert not dossier.is_relative_to(autre), (dossier, autre)


def test_verrous_dans_leur_plage() -> None:
    cles = {int(v) for v in VERROUS}
    assert len(cles) == len(VERROUS)
    assert cles <= set(PLAGE_VERROUS)
    assert not cles & GESTION_MP["verrous"]


def test_les_essais_tournent_sur_une_base_d_essai() -> None:
    assert config.reglages().nom_base.endswith("_essai")


def test_essais_n_ecrivent_pas_dans_les_dossiers_reels() -> None:
    """G-03 (`test_defauts_g::test_essais_n_ecrivent_pas_dans_les_pieces_reelles`) : pour toute
    la séance, sauvegardes et pièces jointes vont dans un dossier temporaire (`conftest.py`) ;
    aucune copie de sécurité n'est réglée. Un essai qui oublierait ses propres dossiers
    n'atteint donc jamais `~/gestion-mp-pro-sauvegardes` ni `~/gestion-mp-pro-pieces`."""
    r = config.reglages()
    temporaire = Path(tempfile.gettempdir()).resolve()
    reels = (ACCUEIL / "gestion-mp-pro-sauvegardes", ACCUEIL / "gestion-mp-pro-pieces")
    for dossier in (r.sauvegardes, r.pieces, r.dossier_sauvegardes, r.dossier_pieces):
        assert dossier.resolve().is_relative_to(temporaire), dossier
        assert not any(dossier.resolve().is_relative_to(x) for x in reels), dossier
    assert r.sauvegardes_copie is None
