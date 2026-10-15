"""Tâches de fond : un seul porteur, échecs isolés, courriel du lundi une fois, reprises (D10).

Routes 4, 46–48 ; ARCHITECTURE § 12 ; défauts E-15 (adresses vérifiées, photo et courriel
séparés), G-13 (adresse derrière HTTPS) de Gestion MP. Hérité :
test_direction::test_l_etat_du_serveur_est_reserve_a_la_direction.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import pytest
from fabrique import *  # noqa: F403
from fabriques.exploitation import *  # noqa: F403
from fabriques.exploitation import Dossiers, environnement
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from gestion_mp_pro.db import Verrou, fabrique, moteur
from gestion_mp_pro.modeles import Courriel, IndicateurJour, Notification
from gestion_mp_pro.modeles.enums import StatutCourriel
from gestion_mp_pro.services import courriel, execution, horloge
from gestion_mp_pro.taches import courriels, photo_du_jour, planificateur

LUNDI = datetime(2026, 10, 5, 8, 0, tzinfo=horloge.FUSEAU)
DOSSIER_SERVEUR = Path(__file__).resolve().parents[1]


@pytest.fixture
def boite(monkeypatch: pytest.MonkeyPatch, dossiers: Dossiers) -> list[EmailMessage]:
    """Un serveur d'envoi réglé, des destinataires, une boîte qui reçoit au lieu de SMTP."""
    envoyes: list[EmailMessage] = []
    monkeypatch.setattr(courriel, "envoyer_smtp", envoyes.append)
    with environnement({"GESTIONMPPRO_SMTP_HOTE": "smtp.usine.ma"}):
        _destinataires("direction@usine.ma, achats@usine.ma")
        yield envoyes


def _destinataires(valeur: str) -> None:
    with moteur().begin() as c:
        c.execute(
            text("UPDATE parametre SET valeur = :v WHERE cle = 'courriel_destinataires'"),
            {"v": valeur},
        )


def _file() -> list[Courriel]:
    with fabrique()() as s:
        return list(s.scalars(select(Courriel).order_by(Courriel.id)))


def test_le_courriel_du_lundi_part_une_fois(base_neuve: None, boite: list[EmailMessage]) -> None:
    """Base neuve (`base_neuve`) : le courriel compte toute la base (bons en retard, brouillons)."""
    horloge.fixer(LUNDI)
    courriels.executer()
    courriels.executer()  # deuxième passage du même lundi : rien de plus
    horloge.fixer(LUNDI + timedelta(days=1))
    courriels.executer()  # mardi : rien
    file = _file()
    assert [c.cle for c in file] == ["lundi:2026-10-05"] and len(boite) == 1
    assert file[0].statut == StatutCourriel.envoye and file[0].essais == 1
    message = boite[0]
    assert message["Subject"] == "Gestion MP PRO — la semaine du 05/10/2026"
    assert message["To"] == "direction@usine.ma, achats@usine.ma"
    corps = message.get_content()
    for ligne in (
        "Valeur du stock :",
        "Commandes en retard : 0",
        "Contrôles bloquants :",
        "Dernière sauvegarde : aucune",
        "Brouillons en attente : 0 réceptions",
    ):
        assert ligne in corps


def test_adresse_illisible_ecartee_et_dite(boite: list[EmailMessage]) -> None:
    """E-15 : une adresse illisible (base restaurée, reprise) est écartée et dite ; les autres
    reçoivent le courriel."""
    _destinataires("direction@usine.ma, pas une adresse")
    horloge.fixer(LUNDI)
    with pytest.raises(courriels.EchecCourriel, match="pas une adresse"):
        courriels.executer()
    assert [m["To"] for m in boite] == ["direction@usine.ma"]


def test_reprises_espacees_puis_abandon(
    boite: list[EmailMessage], monkeypatch: pytest.MonkeyPatch, administrateur: TestClient
) -> None:
    def refuse(_message: EmailMessage) -> None:
        raise OSError("serveur d'envoi injoignable")

    monkeypatch.setattr(courriel, "envoyer_smtp", refuse)
    horloge.fixer(LUNDI)
    ecarts = [0, 15, 30, 60, 120]  # minutes depuis l'essai précédent : 15 × 2ⁿ
    instant = LUNDI
    for n, ecart in enumerate(ecarts, start=1):
        instant += timedelta(minutes=ecart)
        horloge.fixer(instant - timedelta(minutes=1))
        if n > 1:
            courriel.envoyer_la_file()  # trop tôt : pas d'essai
            assert _file()[0].essais == n - 1
        horloge.fixer(instant)
        with pytest.raises(courriels.EchecCourriel):
            courriels.executer()
        assert _file()[0].essais == n
    c = _file()[0]
    assert c.statut == StatutCourriel.abandonne and "injoignable" in c.erreur
    page = administrateur.get("/api/courriels").json()
    assert page["total"] == 1 and page["elements"][0]["statut"] == "abandonne"
    assert "corps" not in page["elements"][0]  # des montants : jamais chez l'administrateur


def test_l_echec_d_une_tache_n_empeche_pas_les_autres(
    monkeypatch: pytest.MonkeyPatch, dossiers: Dossiers
) -> None:
    """E-15 : la photo en échec n'empêche ni le courriel ni les suivantes ; chacune notée."""
    vues: list[str] = []

    def photo_en_panne() -> None:
        raise RuntimeError("moteur indisponible")

    taches = (
        ("photo_indicateurs", photo_en_panne),
        ("courriel", lambda: vues.append("courriel")),
        ("purges", lambda: vues.append("purges")),
    )
    monkeypatch.setattr(planificateur, "TACHES", taches)
    monkeypatch.setattr(planificateur, "verrou_tenu", lambda _v: False)
    assert planificateur.passage() == {"photo_indicateurs": "moteur indisponible"}
    assert vues == ["courriel", "purges"]
    with fabrique()() as s:
        etats = {e.nom: e for e in execution.tous(s)}
    assert etats["photo_indicateurs"].erreur == "moteur indisponible"
    assert etats["courriel"].dernier_succes_le == horloge.maintenant()


def test_photo_du_jour_une_fois(dossiers: Dossiers) -> None:
    jour = horloge.aujourd_hui()
    with moteur().begin() as c:
        c.execute(text("DELETE FROM indicateur_jour WHERE jour = :j"), {"j": jour})
    photo_du_jour.executer()
    photo_du_jour.executer()
    with fabrique()() as s:
        photos = s.scalars(select(IndicateurJour).where(IndicateurJour.jour == jour)).all()
        assert len(photos) == 1 and photos[0].pris_par_id is None


def test_alerte_de_sauvegarde_a_la_cloche_une_fois(dossiers: Dossiers) -> None:
    from gestion_mp_pro.taches import alertes

    execution.noter("sauvegarde", horloge.maintenant(), "disque plein")
    assert alertes.executer() is True
    execution.noter("notifications", horloge.maintenant())
    assert alertes.executer() is False  # déjà faites aujourd'hui
    with fabrique()() as s:
        cles = set(s.scalars(select(Notification.cle).where(Notification.cle.like("sauvegarde:%"))))
    jour = horloge.aujourd_hui()
    assert cles == {f"sauvegarde:{jour}:direction", f"sauvegarde:{jour}:administrateur"}


SCRIPT = """
import sys, time
from gestion_mp_pro.taches import planificateur
planificateur.TACHES = ()
planificateur.PERIODE_S = 0.1
planificateur.demarrer()
while True:
    sys.stdout.write(("1" if planificateur.porteur() else "0") + "\\n")
    sys.stdout.flush()
    time.sleep(0.1)
"""


def _processus(sortie: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(  # noqa: S603 — l'interpréteur des essais, un script à nous
        [sys.executable, "-c", SCRIPT],
        cwd=DOSSIER_SERVEUR,
        stdout=sortie.open("w", encoding="utf-8"),
    )


def _dernier(sortie: Path) -> str:
    lignes = sortie.read_text(encoding="utf-8").split()
    return lignes[-1] if lignes else ""


def _attendre(sortie: Path, valeur: str, delai: float = 15) -> None:
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        if _dernier(sortie) == valeur:
            return
        time.sleep(0.05)
    raise AssertionError(f"{sortie.name} : jamais {valeur}")


def _porteurs() -> int:
    requete = (
        "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND objid = :cle AND granted"
        " AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
    )
    with moteur().connect() as c:
        return int(c.scalar(text(requete), {"cle": int(Verrou.TACHES)}) or 0)


def test_un_seul_porteur_a_deux_processus_puis_la_releve(tmp_path: Path) -> None:
    un, deux = tmp_path / "un.txt", tmp_path / "deux.txt"
    premier = _processus(un)
    try:
        _attendre(un, "1")
        second = _processus(deux)
        try:
            _attendre(deux, "0")
            time.sleep(0.5)  # plusieurs tours : le second ne prend toujours pas
            assert _dernier(deux) == "0" and _porteurs() == 1
            premier.kill()
            premier.wait(10)
            _attendre(deux, "1")  # la relève, au tour suivant
            assert _porteurs() == 1
        finally:
            second.kill()
            second.wait(10)
    finally:
        premier.kill()
        premier.wait(10)


def test_l_etat_du_serveur_est_reserve_a_la_direction_et_a_l_administrateur(
    direction: TestClient, administrateur: TestClient, achats: TestClient, dossiers: Dossiers
) -> None:
    """Hérité : test_direction::test_l_etat_du_serveur_est_reserve_a_la_direction."""
    e = direction.get("/api/serveur").json()
    assert e["base"]["nom"].endswith("_essai") and e["base"]["taille_octets"] > 0
    assert e["base"]["schema"] == e["base"]["schema_attendu"] and e["application"]
    assert e["sauvegardes"]["dossier"] == str(dossiers.sauvegardes)
    assert "Direction" in [x["nom"] for x in e["sessions"]]
    assert [t["nom"] for t in e["taches"]] == list(execution.TACHES)
    assert administrateur.get("/api/serveur").status_code == 200
    assert achats.get("/api/serveur").status_code == 403
    assert administrateur.get("/api/taches").status_code == 200
    assert achats.get("/api/taches").status_code == 403


def test_adresse_du_serveur_derriere_https(application: object) -> None:
    """G-13 (`test_defauts_g::test_acces_https_sans_port`) : schéma et port de la requête."""
    from gestion_mp_pro.services.appareils import ip_reseau
    from gestion_mp_pro.services.serveur import adresse_de

    assert adresse_de("https://localhost/") == f"https://{ip_reseau()}"
    assert adresse_de("http://localhost:8050/") == f"http://{ip_reseau()}:8050"
    assert (
        adresse_de("https://mac-usine.tail1234.ts.net:443/") == "https://mac-usine.tail1234.ts.net"
    )


def test_l_apercu_du_courriel_est_a_la_direction(
    direction: TestClient, administrateur: TestClient, dossiers: Dossiers
) -> None:
    _destinataires("direction@usine.ma")
    a = direction.get("/api/courriel/apercu").json()
    assert a["sujet"].startswith("Gestion MP PRO — la semaine du ")
    assert "Contrôles bloquants :" in a["texte"] and "Dernière sauvegarde :" in a["texte"]
    assert a["serveur_configure"] is False and a["destinataires"] == ["direction@usine.ma"]
    assert administrateur.get("/api/courriel/apercu").status_code == 403
