"""Journal d'audit et historique d'une fiche (lot S2 ; ARCHITECTURE § 5.5, héritage K50–K53, F-09).

Le journal s'écrit dans la transaction du geste, avec avant/après (les seuls champs changés),
sans secret ; il se lit filtré, sans accents ; l'historique d'une fiche est lu par qui lit la
fiche, prix retirés pour les rôles qui ne les voient pas.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fabrique import *  # noqa: F403
from fabrique import compte
from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.orm import Session

from gestion_mp_pro.api.erreurs import Refus
from gestion_mp_pro.db import fabrique as sessions_db
from gestion_mp_pro.modeles import Journal, Utilisateur
from gestion_mp_pro.services import audit
from gestion_mp_pro.services.comptes import Acteur


@pytest.fixture
def s() -> Iterator[Session]:
    """Une session annulée à la fin."""
    with sessions_db()() as session:
        yield session
        session.rollback()


def _qui(ident: int) -> Acteur:
    return Acteur(ident, "essai", "Essai Audit", "direction", requete="abcdef0123456789")


def test_creation_et_suivi_ne_gardent_que_les_changements(s: Session) -> None:
    u = Utilisateur(identifiant="audit-1", nom="Avant", role="achats", empreinte_code="x$y$z")
    s.add(u)
    ligne = audit.creation(s, None, "création de compte", u, detail="Avant (achats)")
    assert ligne.utilisateur_nom == "système" and ligne.objet_id == u.id
    assert ligne.apres is not None and ligne.apres["nom"] == "Avant"
    assert "empreinte_code" not in ligne.apres and "version" not in ligne.apres
    qui = _qui(u.id)
    with audit.suivre(s, qui, "modification de compte", u) as geste:
        u.nom, u.email = "Après", "a@usine.ma"
        u.empreinte_code = "secret$change$ici"
        geste.detail = "Après (achats)"
    j = geste.ligne
    assert j is not None
    assert (j.avant, j.apres) == (
        {"nom": "Avant", "email": ""},
        {"nom": "Après", "email": "a@usine.ma"},
    )
    assert (j.requete, j.role, j.utilisateur_nom) == (
        "abcdef0123456789",
        "direction",
        "Essai Audit",
    )
    sup = audit.suppression(s, qui, "suppression", u)
    assert sup.avant is not None and sup.avant["identifiant"] == "audit-1"
    s.flush()
    assert [x.action for x in audit.historique(s, "utilisateur", u.id)] == [
        "création de compte",
        "modification de compte",
        "suppression",
    ]


def test_journal_borne_les_textes(s: Session) -> None:
    """Hérité : K50 — le détail est tronqué à 2 000 caractères."""
    ligne = audit.journal(s, None, "a" * 120, "systeme", detail="x" * 3000, numero="N" * 50)
    s.flush()
    assert (len(ligne.action), len(ligne.detail), len(ligne.numero)) == (80, 2000, 40)


def test_version_perimee_nomme_l_auteur(s: Session) -> None:
    """API-PRO § 0.1 : 409 « modifiée entre-temps par {nom} ({heure}) »."""
    u = Utilisateur(identifiant="audit-2", nom="Compte", role="achats")
    s.add(u)
    s.flush()
    audit.creation(s, _qui(u.id), "création de compte", u)
    s.flush()
    audit.verifier_version(s, u, u.version, "Ce compte", feminin=False)
    with pytest.raises(Refus) as refus:
        audit.verifier_version(s, u, u.version + 1, "Ce compte", feminin=False)
    assert (refus.value.http, refus.value.code) == (409, "conflit_version")
    assert refus.value.detail == (
        "Ce compte a été modifié entre-temps par Essai Audit (08/10/2026 10:00) : rouvrez-le "
        "pour repartir de sa dernière version."
    )


def _lignes_de_prix(objet: str, ident: int) -> None:
    with sessions_db()() as session, session.begin():
        session.execute(
            insert(Journal).values(
                action="modification",
                objet=objet,
                objet_id=ident,
                utilisateur_nom="Achats",
                detail="prix changé",
                avant={"prix": 2.5, "designation": "POIL", "valeur_mad": 25.0},
                apres={"prix": 3.1, "designation": "POIL ROUGE", "valeur_mad": 31.0},
            )
        )


def test_historique_d_une_fiche_et_ses_prix(
    direction: TestClient, alimentation: TestClient, administrateur: TestClient
) -> None:
    """Route 51 : lu par qui lit la fiche ; prix retirés pour l'alimentation (D5)."""
    _lignes_de_prix("matiere", 987001)
    vu = direction.get("/api/historique/matiere/987001").json()
    assert vu[-1]["avant"] == {"prix": 2.5, "designation": "POIL", "valeur_mad": 25.0}
    lu = alimentation.get("/api/historique/matiere/987001")
    assert lu.status_code == 200
    assert lu.json()[-1]["avant"] == {"prix": None, "designation": "POIL", "valeur_mad": None}
    assert lu.json()[-1]["apres"]["designation"] == "POIL ROUGE"
    r = alimentation.get("/api/historique/commande/987001")
    assert r.status_code == 403
    assert r.json()["detail"] == "Cette action est réservée à : responsable achats."
    assert administrateur.get("/api/historique/matiere/987001").status_code == 403
    assert administrateur.get("/api/historique/utilisateur/1").status_code == 200
    assert direction.get("/api/historique/inconnu/1").status_code == 422


def test_journal_des_actions_filtre_et_cherche_sans_accent(
    direction: TestClient, achats: TestClient, administrateur: TestClient
) -> None:
    """Hérité : test_defauts_f::test_journal_trouve_sans_accent (F-09) ;
    test_audit2_pilotage::test_le_journal_ecrit_les_taux_en_pourcent_et_cherche_les_jokers ;
    test_direction::test_le_journal_des_actions_se_filtre_et_s_exporte (filtres, droits)."""
    corps = {
        "identifiant": "f-accent",
        "nom": "Fé Accentuée",
        "role": "achats",
        "code": "accent-f-09x",
    }
    assert direction.post("/api/utilisateurs", json=corps).status_code == 201
    trouve = direction.get("/api/journal", params={"q": "creation FE ACCENTUEE"}).json()
    assert [x["action"] for x in trouve["elements"]] == ["création de compte"]
    ligne = trouve["elements"][0]
    assert (
        ligne["apres"]["identifiant"] == "f-accent"
        and ligne["detail"] == "Fé Accentuée (Responsable achats)"
    )
    assert direction.get("/api/journal", params={"q": "% f-accent"}).json()["total"] == 0
    assert direction.get("/api/journal", params={"q": "f_accent"}).json()["total"] == 0
    par_objet = direction.get(
        "/api/journal", params={"objet": "utilisateur", "objet_id": ligne["objet_id"]}
    ).json()
    assert par_objet["total"] == 1
    assert direction.get("/api/journal", params={"au": "2001-01-01"}).json()["total"] == 0
    assert (
        direction.get("/api/journal", params={"du": "2026-10-08", "au": "2026-10-01"}).status_code
        == 422
    )
    assert achats.get("/api/journal").status_code == 403
    assert administrateur.get("/api/journal").status_code == 200
    valeurs = direction.get("/api/journal/valeurs").json()
    assert "création de compte" in valeurs["actions"] and "utilisateur" in valeurs["objets"]
    assert any(p["nom"] == "Direction" for p in valeurs["utilisateurs"])


def test_journal_pagine_par_curseur(direction: TestClient) -> None:
    for i in range(3):
        compte("achats", identifiant=f"page-{i}")
        direction.put("/api/moi", json={"email": f"d{i}@usine.ma", "version": _version(direction)})
    page = direction.get("/api/journal", params={"limite": 2, "action": "modification de compte"})
    corps = page.json()
    assert len(corps["elements"]) == 2 and corps["total"] >= 3 and corps["suivant"]
    suite = direction.get(
        "/api/journal",
        params={"limite": 2, "action": "modification de compte", "apres": corps["suivant"]},
    ).json()
    ids = [x["id"] for x in corps["elements"] + suite["elements"]]
    assert ids == sorted(ids, reverse=True) and len(set(ids)) == len(ids)
    assert direction.get("/api/journal", params={"apres": "!!!"}).status_code == 422
    direction.put("/api/moi", json={"email": "", "version": _version(direction)})


def _version(client: TestClient) -> int:
    return int(client.get("/api/moi").json()["version"])


def test_journal_de_connexion_porte_requete_et_adresse(direction: TestClient) -> None:
    lignes = direction.get("/api/journal", params={"action": "connexion"}).json()["elements"]
    assert lignes and lignes[0]["role"] in {"direction", "achats", "alimentation", "administrateur"}
    with sessions_db()() as session:
        j = session.get(Journal, lignes[0]["id"])
        assert j is not None and j.adresse == "testclient" and j.quand.date() == date(2026, 10, 8)
