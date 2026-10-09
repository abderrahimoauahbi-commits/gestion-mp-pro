"""Réglages : registre des 57 clés, lecture par rôle, écriture tout ou rien (routes 23–25, D1).

Héritage K60–K66, KR30–KR41 (REGLES B.5.7), REGLAGES § 2 ; défauts E-01, E-15, E-16.
Chaque essai remet les réglages comme il les a trouvés.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from gestion_mp_pro.db import fabrique as sessions
from gestion_mp_pro.modeles import CLES_REGLAGES, Journal, Parametre, ParametreHistorique
from gestion_mp_pro.services.registre_reglages import ORDRES_STRICTS, PAR_CLE, REGLAGES


@pytest.fixture(autouse=True)
def reglages_remis() -> Iterator[None]:
    """Les valeurs des réglages, remises à la fin de l'essai."""
    with sessions()() as s:
        avant = dict(s.execute(select(Parametre.cle, Parametre.valeur)).all())
    yield
    with sessions()() as s, s.begin():
        for cle, valeur in avant.items():
            s.execute(update(Parametre).where(Parametre.cle == cle).values(valeur=valeur))


def ok(r: Any, statut: int = 200) -> Any:
    """La réponse JSON d'un appel qui doit réussir."""
    assert r.status_code == statut, r.text
    return r.json()


def lire(client: TestClient) -> dict[str, dict[str, Any]]:
    """Les réglages lus, par clé."""
    return {x["cle"]: x for x in ok(client.get("/api/parametres"))}


def ecrire(client: TestClient, valeurs: dict[str, Any], version: int | None = None) -> Any:
    """`PUT /parametres` à la version globale lue."""
    if version is None:
        version = next(iter(lire(client).values()))["version_globale"]
    return client.put("/api/parametres", json={"valeurs": valeurs, "version_globale": version})


def test_le_registre_declare_exactement_les_57_cles() -> None:
    """Hérité : K60 — liste fermée, toutes en base dès l'installation ; 0003 : toler_tva_import."""
    assert len(REGLAGES) == 57 and set(PAR_CLE) == set(CLES_REGLAGES)
    with sessions()() as s:
        semes = dict(s.execute(select(Parametre.cle, Parametre.valeur)).all())
    assert set(semes) == set(CLES_REGLAGES)
    for r in REGLAGES:
        if not r.texte:
            assert r.bas is not None and r.haut is not None and r.bas <= float(r.defaut) <= r.haut
    assert PAR_CLE["toler_tva_import"].defaut == 0.05 and PAR_CLE["toler_tva_import"].haut == 1
    assert PAR_CLE["delai_frais_import_jours"].bas == 1


def test_lecture_par_role(
    direction: TestClient, achats: TestClient, alimentation: TestClient, administrateur: TestClient
) -> None:
    """Hérité : test_defauts_f::test_alimentation_ne_lit_ni_parametres_ni_devises (E-01) ;
    K62 (forme) ; l'administrateur ne lit que la famille technique, valeurs comprises."""
    d = lire(direction)
    assert len(d) == 57 and lire(achats).keys() == d.keys()
    assert d["taux_perte"]["echelle"] == 100 and d["taux_perte"]["valeur"] == "0.02"
    assert d["secteur"]["texte"] and d["secteur"]["defaut"] == "Fabrication de tapis mécaniques"
    assert not d["seuil_bc_urgent"]["modifiable"] and not d["date_cloture"]["modifiable"]
    t = lire(administrateur)
    assert set(t) == {"courriel_destinataires", "adresse_publique"}
    assert t["adresse_publique"]["valeur"] == d["adresse_publique"]["valeur"]
    assert alimentation.get("/api/parametres").status_code == 403
    assert alimentation.get("/api/parametres/historique").status_code == 403


def test_ecrire_normalise_historise_et_journalise(direction: TestClient) -> None:
    """Hérité : K64 — virgule acceptée, texte normalisé, historique et journal lisibles ;
    valeur inchangée : ni historique ni journal."""
    with sessions()() as s:
        avant = s.scalar(select(ParametreHistorique.id).order_by(ParametreHistorique.id.desc()))
    lu = ok(ecrire(direction, {"taux_perte": "0,035", "dso": 45.0, "seuil_dormant": 180}))
    regles = {x["cle"]: x for x in lu}
    assert regles["taux_perte"]["valeur"] == "0.035" and regles["dso"]["valeur"] == "45"
    with sessions()() as s:
        nouveaux = s.scalars(
            select(ParametreHistorique).where(ParametreHistorique.id > (avant or 0))
        ).all()
        assert {h.cle: (h.avant, h.apres) for h in nouveaux} == {
            "taux_perte": ("0.02", "0.035"),
            "dso": ("60", "45"),
        }
        details = s.scalars(
            select(Journal.detail).where(Journal.action == "paramètre").order_by(Journal.id.desc())
        ).all()[:2]
    assert "Taux de perte matière : 2 % → 3,5 %" in details
    assert "Délai client moyen (DSO) : 60 jours → 45 jours" in details


@pytest.mark.parametrize(
    ("valeurs", "message"),
    [
        ({"inconnu": 1, "autre": 2}, "Paramètres inconnus : autre, inconnu."),
        ({"taux_perte": "beaucoup"}, "« Taux de perte matière » attend un nombre."),
        ({"taux_perte": "nan"}, "« Taux de perte matière » attend un nombre."),
        ({"taux_perte": "inf"}, "« Taux de perte matière » attend un nombre."),
        (
            {"taux_perte": 0.6},
            "« Taux de perte matière » doit rester entre 0 et 50 % — reçu 60.",
        ),
        (
            {"seuil_dormant": 0},
            "« Stock dormant » doit rester entre 1 et 3650 jours — reçu 0.",
        ),
        ({"nom_entreprise": "x" * 501}, "« Raison sociale » : texte trop long."),
        (
            {"adresse_publique": "mac-usine:8050"},
            "L'adresse commence par http:// ou https:// (ex. http://mac-usine:8050).",
        ),
        (
            {"courriel_destinataires": "direction@usine.ma, nadia"},
            "Adresse de courriel illisible : nadia (ex. direction@usine.ma, séparées par des "
            "virgules).",
        ),
        (
            {"date_cloture": "2026-09-30"},
            "« Période close jusqu'au » se règle par la clôture de période (Réglages › Période "
            "close), avec un motif.",
        ),
        (
            {"seuil_bc_urgent": 1},
            "« BC urgent » est sans effet, gardé pour mémoire : il ne se modifie plus.",
        ),
    ],
)
def test_refus_de_saisie(direction: TestClient, valeurs: dict[str, Any], message: str) -> None:
    """Hérité : KR30–KR36 mot pour mot ; E-15 (courriels) ; E-16 (BC urgent sans effet)."""
    r = ecrire(direction, valeurs)
    assert (r.status_code, r.json()["detail"]) == (422, message)


@pytest.mark.parametrize(("bas", "haut", "message"), ORDRES_STRICTS)
def test_seuils_dans_l_ordre_sinon_rien(
    direction: TestClient, bas: str, haut: str, message: str
) -> None:
    """Hérité : KR37–KR41, commit f85dabd (recette direction 23) — égalité refusée, et rien
    n'est écrit du lot envoyé (tout ou rien)."""
    d = lire(direction)
    r = ecrire(direction, {"dso": 30, bas: d[haut]["valeur"]})
    assert (r.status_code, r.json()["detail"]) == (422, message)
    assert lire(direction)["dso"]["valeur"] == d["dso"]["valeur"]


def test_tier_1_ne_descend_pas_sous_le_tier_2(direction: TestClient) -> None:
    """Hérité : test_defauts_e::test_parametres_tiers_desordonnes_refuses (E-16)."""
    r = ecrire(direction, {"seuil_tier1": 150000})
    assert r.json()["detail"] == (
        "Le montant du Tier 1 (classe A) ne peut pas être inférieur à celui du Tier 2."
    )
    ok(ecrire(direction, {"seuil_tier1": 200000}))


def test_version_globale_perimee(direction: TestClient) -> None:
    """Deux postes : le second parti d'une lecture ancienne reçoit 409 (API-PRO § 0.1)."""
    version = next(iter(lire(direction).values()))["version_globale"]
    ok(ecrire(direction, {"dso": 61}, version))
    r = ecrire(direction, {"dso": 62}, version)
    assert r.status_code == 409 and r.json()["code"] == "conflit_version"
    assert "modifiés entre-temps par Direction" in r.json()["detail"]


def test_administrateur_ecrit_la_famille_technique_seule(administrateur: TestClient) -> None:
    """ECRANS-PRO P8 : `courriel_destinataires`, `adresse_publique` (D, T) ; le reste : 403."""
    lu = ok(ecrire(administrateur, {"adresse_publique": "https://mac-usine:8050"}))
    assert {x["cle"]: x["valeur"] for x in lu}["adresse_publique"] == "https://mac-usine:8050"
    r = ecrire(administrateur, {"dso": 40})
    assert r.status_code == 403
    assert r.json()["detail"] == "Cette action est réservée à : la direction."
    page = ok(administrateur.get("/api/parametres/historique"))
    assert {x["cle"] for x in page["elements"]} <= {"courriel_destinataires", "adresse_publique"}


def test_historique_pagine_et_filtre(direction: TestClient) -> None:
    """Hérité : K66 — le plus récent d'abord, avant et après, qui ; paginé sans plafond muet."""
    ok(ecrire(direction, {"dso": 50}))
    ok(ecrire(direction, {"dso": 51}))
    page = ok(direction.get("/api/parametres/historique?cle=dso&limite=1"))
    assert page["total"] >= 2 and page["suivant"]
    premier = page["elements"][0]
    assert (premier["avant"], premier["apres"], premier["par"]) == ("50", "51", "Direction")
    assert premier["apres_lisible"] == "51 jours"
    suite = ok(direction.get(f"/api/parametres/historique?cle=dso&apres={page['suivant']}"))
    assert suite["elements"][0]["apres"] == "50"
    assert direction.get("/api/parametres/historique?cle=zz").status_code == 422
