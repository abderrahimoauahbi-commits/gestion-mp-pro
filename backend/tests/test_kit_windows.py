"""Le kit du serveur Windows (deploiement/windows, docs/INSTALLATION-WINDOWS.md), vérifié sur le
Mac sans PowerShell : encodage lisible par PowerShell 5.1, syntaxe de 5.1 seulement, parenthèses
et accolades équilibrées, réglages connus de `config.py`, dépendances figées pour Windows, et
la comparaison des lignes d'un transfert (`poste.py comptes` / `comparer-comptes`)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

from gestion_mp_pro.config import RACINE, Reglages

KIT = RACINE / "deploiement" / "windows"
SCRIPTS = sorted(KIT.glob("*.ps1"))
BACKEND = RACINE / "backend"
BOM = b"\xef\xbb\xbf"

# --- un lecteur minimal de PowerShell : retire commentaires et chaînes ---------------------


def _sans_chaines_ni_commentaires(texte: str) -> str:
    """Le code sans commentaires (`#…`, `<#…#>`) ni chaînes ('…', "…", @'…'@, @"…"@)."""
    sortie: list[str] = []
    i, n = 0, len(texte)
    while i < n:
        c = texte[i]
        if texte.startswith("<#", i):
            i = texte.index("#>", i) + 2
        elif c == "#":
            i = texte.find("\n", i) if "\n" in texte[i:] else n
        elif texte.startswith(("@'\n", '@"\n'), i):
            fin = "\n" + texte[i + 1] + "@"
            i = texte.index(fin, i + 2) + len(fin)
            sortie.append("''")
        elif c == "'":
            i += 1
            while not (texte[i] == "'" and texte[i + 1 : i + 2] != "'"):
                i += 2 if texte[i] == "'" else 1
            i += 1
            sortie.append("''")
        elif c == '"':
            i += 1
            while texte[i] != '"' or texte[i + 1 : i + 2] == '"':
                i += 2 if texte[i] in '`"' else 1
            i += 1
            sortie.append("''")
        else:
            sortie.append(c)
            i += 1
    return "".join(sortie)


def test_le_lecteur_retire_chaines_et_commentaires() -> None:
    code = 'a = \'x\'\'(y\' # (\n<# { #>b = "q`"{" + """"\n@\'\n(\n\'@\nc'
    assert _sans_chaines_ni_commentaires(code) == "a = '' \nb = '' + ''\n''\nc"


def test_le_kit_est_complet() -> None:
    noms = {s.name for s in SCRIPTS}
    attendus = {"installer.ps1", "demarrer.ps1", "arreter.ps1", "etat.ps1", "sauvegarder.ps1"}
    attendus |= {"mettre-a-jour.ps1", "desinstaller.ps1", "recette.ps1", "restaurer.ps1"}
    attendus |= {"commun.ps1", "fonctions-admin.ps1", "lancer-serveur.ps1"}
    assert attendus <= noms


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda s: s.name)
def test_encodage_lisible_par_powershell_5(script: Path) -> None:
    """Sans BOM, PowerShell 5.1 lit un .ps1 en cp1252 : « — » (E2 80 94) y devient un
    guillemet (0x94) et casse les chaînes. UTF-8 avec BOM, donc, et rien d'autre."""
    brut = script.read_bytes()
    assert brut.startswith(BOM)
    brut.decode("utf-8")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda s: s.name)
def test_syntaxe_de_powershell_5_seulement(script: Path) -> None:
    texte = script.read_text(encoding="utf-8-sig")
    assert texte.startswith("#Requires -Version 5.1\n")
    code = _sans_chaines_ni_commentaires(texte)
    for paire in ("()", "{}", "[]"):
        assert code.count(paire[0]) == code.count(paire[1]), paire
    # Opérateurs de PowerShell 7 seulement ; Join-Path à trois morceaux ; ternaire.
    for interdit in ("&&", "||", "??", "?.", "-AdditionalChildPath", "-Parallel"):
        assert interdit not in code, interdit
    assert not re.search(r"\s\?\s[^:]*\s:\s", code)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda s: s.name)
def test_aucun_secret_ni_binaire(script: Path) -> None:
    texte = script.read_text(encoding="utf-8-sig")
    assert not re.search(r"MOT_DE_PASSE=[^\s'\"]", texte)
    assert not re.search(r"(Invoke-WebRequest|curl|wget|Start-BitsTransfer)\s+\S*https?://", texte)
    assert "-AsPlainText" not in texte  # jamais un mot de passe tapé en clair


def test_reglages_ecrits_connus_de_config() -> None:
    connus = {f"GESTIONMPPRO_{n}".upper() for n in Reglages.model_fields}
    ecrits: set[str] = set()
    for s in SCRIPTS:
        ecrits |= set(re.findall(r"GESTIONMPPRO_[A-Z_]+", s.read_text(encoding="utf-8-sig")))
    assert ecrits - {"GESTIONMPPRO_", "GESTIONMPPRO_NOM"} <= connus


def test_le_lanceur_sert_un_seul_processus_sans_shell() -> None:
    """Un processus (journal tournant non partagé sous Windows), pas de --reload, pas de shell."""
    texte = (KIT / "lancer-serveur.ps1").read_text(encoding="utf-8-sig")
    assert "--workers" not in texte and "--reload" not in texte
    assert "cmd.exe" not in texte and "Invoke-Expression" not in texte


# --- dépendances figées ---------------------------------------------------------------------


def _epingles(fichier: Path) -> dict[str, str]:
    lignes = fichier.read_text(encoding="utf-8").splitlines()
    return dict(ligne.split("==", 1) for ligne in lignes if "==" in ligne)


def test_requirements_windows_memes_versions_sans_uvloop() -> None:
    mac = _epingles(BACKEND / "requirements.lock")
    windows = _epingles(BACKEND / "requirements-windows.lock")
    assert "uvloop" in mac and "uvloop" not in windows
    assert "tzdata" in windows
    communs = set(mac) & set(windows)
    assert {k: mac[k] for k in communs} == {k: windows[k] for k in communs}
    assert set(windows) - set(mac) == {"tzdata"}
    assert set(mac) - set(windows) == {"uvloop"}


def test_tzdata_dependance_sous_windows() -> None:
    texte = (BACKEND / "pyproject.toml").read_text(encoding="utf-8")
    assert "\"tzdata>=2024.1; sys_platform == 'win32'\"" in texte


# --- comptes d'un transfert (poste.py) ------------------------------------------------------


@pytest.fixture(scope="module")
def poste() -> ModuleType:
    chemin = RACINE / "deploiement" / "mac" / "poste.py"
    spec = importlib.util.spec_from_file_location("poste_du_kit", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ecarts_tables_metier_et_d_exploitation(poste: ModuleType) -> None:
    mac = {"revision": "0010", "tables": {"lot": 5, "journal": 9, "session": 2, "mouvement": 7}}
    ici = {"revision": "0010", "tables": {"lot": 5, "journal": 10, "session": 0, "mouvement": 7}}
    fautes, remarques = poste.ecarts(mac, ici)
    assert fautes == []
    assert len(remarques) == 2
    ici["tables"]["mouvement"] = 6
    ici["tables"]["ordre"] = 1
    fautes, _ = poste.ecarts(mac, ici)
    assert fautes == ["mouvement : 7 là-bas, 6 ici", "ordre : absente là-bas, 1 ici"]


def test_comptes_puis_comparaison_sur_la_base_d_essai(
    poste: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    assert poste.main(["comptes"]) == 0
    lu = json.loads(capsys.readouterr().out)
    assert lu["base"].endswith("_essai") and lu["revision"] and "lot" in lu["tables"]
    fichier = tmp_path / "comptes-mac.json"
    fichier.write_bytes(BOM + json.dumps(lu).encode())  # comme l'écrirait PowerShell 5.1
    assert poste.main(["--qui", "serveur Windows (scripts)", "comparer-comptes", str(fichier)]) == 0
    assert "Mêmes lignes" in capsys.readouterr().out
    lu["tables"]["lot"] += 1
    fichier.write_text(json.dumps(lu), encoding="utf-8")
    assert poste.main(["comparer-comptes", str(fichier)]) == 1
    assert "ÉCART — lot" in capsys.readouterr().err
