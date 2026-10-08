"""Matrice des droits (lot S2 ; API-PRO § 4, ARCHITECTURE § 5.2, héritage D3, K2, F-04).

- La matrice versionnée (`tests/matrice_droits.csv`) est celle des routes (`make matrice`).
- Elle est **rejouée** entièrement : chaque route × {anonyme, D, A, L, T} donne le code attendu
  (401, 403, ou ni l'un ni l'autre). Les identifiants absents (999999) et les corps vides
  évitent tout effet ; `SANS_REJEU` liste les routes qu'un rôle permis ne doit pas appeler à
  vide (un lot D y ajoute par exemple la sauvegarde manuelle).
- Les rôles de chaque garde sont ceux du catalogue API-PRO ; l'administrateur n'est nommé que
  dans les routes techniques.
"""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

import pytest
from api_pro import TECHNIQUES, catalogue, gabarit
from fabrique import *  # noqa: F403
from fabrique import CODES, compte, connecter
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gestion_mp_pro.config import ENTETE_ANTI_FALSIFICATION
from gestion_mp_pro.modeles.enums import Role
from gestion_mp_pro.securite import PUBLIQUES
from gestion_mp_pro.securite.matrice import LigneMatrice, en_csv, matrice, sans_garde

CSV = Path(__file__).with_name("matrice_droits.csv")
ROLES = (None, *Role)
SANS_REJEU: frozenset[tuple[str, str]] = frozenset()
"""(méthode, chemin) qu'un rôle permis n'appelle pas à vide pendant le rejeu."""
EN_DERNIER = ("/api/deconnexion",)


def test_matrice_versionnee_a_jour(application: FastAPI) -> None:
    """`tests/matrice_droits.csv` n'est jamais édité à la main : `make matrice` le régénère."""
    attendu = en_csv(matrice(application))
    assert CSV.read_text(encoding="utf-8") == attendu, "matrice périmée : lancer `make matrice`"


def test_toute_route_declare_ses_roles(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_chaque_route_declare_ses_roles (F-04, D3)."""
    assert sans_garde(application) == []
    servies = {(x.methode, x.chemin) for x in matrice(application)}
    assert len(PUBLIQUES) == 6 and servies >= PUBLIQUES


def _url(chemin: str) -> str:
    """Le chemin avec des paramètres qui ne désignent rien (aucun effet) ."""
    return re.sub(r"\{[^}]*\}", lambda g: "zz" if "code" in g.group(0) else "999999", chemin)


def _clients(app: FastAPI) -> dict[str | None, TestClient]:
    """Un client par rôle, sur des comptes à soi (la déconnexion rejouée ne gêne personne)."""
    clients: dict[str | None, TestClient] = {
        None: TestClient(app, headers={ENTETE_ANTI_FALSIFICATION: "1"})
    }
    for role in Role:
        ident = f"matrice-{role.value}-{uuid4().hex[:8]}"
        compte(role, identifiant=ident)
        clients[role.value] = connecter(app, ident, CODES[role])
    return clients


def _ordre(x: LigneMatrice) -> tuple[bool, str, str]:
    return (x.chemin in EN_DERNIER, x.chemin, x.methode)


def test_matrice_rejouee_route_par_route(application: FastAPI) -> None:
    """Hérité : test_parcours::test_tout_est_ferme_sans_connexion (401 hors routes publiques),
    étendu à toutes les méthodes et à chaque rôle (P-11 « balayage générique des droits »)."""
    clients = _clients(application)
    ecarts = []
    for x in sorted(matrice(application), key=_ordre):
        for role in ROLES:
            attendu = x.attendu(role)
            if attendu == "ok" and (x.methode, x.chemin) in SANS_REJEU:
                continue
            client = clients[role]
            options = {} if x.methode == "GET" else {"json": {}}
            r = client.request(x.methode, _url(x.chemin), **options)  # type: ignore[arg-type]
            vu = str(r.status_code) if r.status_code in (401, 403) else "ok"
            if vu != attendu or r.status_code >= 500:
                ecarts.append(f"{x.methode} {x.chemin} {role}: {r.status_code} ≠ {attendu}")
    assert ecarts == []


def test_roles_conformes_au_catalogue(application: FastAPI) -> None:
    """La garde de chaque route servie dit les rôles de API-PRO § 1 (contrat gelé)."""
    ecarts = []
    for x in matrice(application):
        entree = catalogue().get((x.methode, gabarit(x.chemin)))
        if entree is None:
            ecarts.append(f"{x.methode} {x.chemin} : absente du catalogue")
        elif entree.publique != x.publique:
            ecarts.append(f"{x.methode} {x.chemin} : publique {x.publique} ≠ {entree.publique}")
        elif entree.roles is not None and not x.publique and entree.roles != x.roles:
            ecarts.append(f"{x.methode} {x.chemin} : {sorted(x.roles)} ≠ {sorted(entree.roles)}")
    assert ecarts == []


def test_administrateur_refuse_sur_toute_route_metier(application: FastAPI) -> None:
    """C8 : l'administrateur n'est nommé que dans les routes techniques (vérifié à chaque lot)."""
    metier = []
    for x in matrice(application):
        entree = catalogue().get((x.methode, gabarit(x.chemin)))
        if entree is None or x.publique:
            continue
        if Role.administrateur in x.roles and entree.numero not in TECHNIQUES | {51}:
            metier.append(f"{x.methode} {x.chemin}")
    assert metier == []
    for entree in catalogue().values():
        if entree.roles and Role.administrateur in entree.roles:
            assert entree.numero in TECHNIQUES, entree


@pytest.mark.parametrize("role", list(Role))
def test_matrice_par_role_coherente(application: FastAPI, role: Role) -> None:
    """Chaque ligne dit 401 pour l'anonyme hors routes publiques, `ok`/403 pour un rôle."""
    for x in matrice(application):
        assert x.attendu(None) == ("ok" if x.publique else "401")
        assert x.attendu(role) in {"ok", "403"}
