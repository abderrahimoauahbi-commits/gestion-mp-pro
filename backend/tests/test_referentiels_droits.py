"""Référentiels : aucun prix chez l'alimentation ni l'administrateur, version périmée → 409 sur
chaque écriture de fiche (lot D1 ; API-PRO § 0.1, § 0.4 ; LOTS § 2 critères communs)."""

from __future__ import annotations

import random
from typing import Any

import pytest
from fabrique import *  # noqa: F403
from fabrique import client_de
from fabriques.referentiels import (
    code_douanier,
    devise,
    fournisseur,
    magasin,
    matiere,
    poste_frais,
    unique,
    valeur_classification,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_prix_masques import balayer

from gestion_mp_pro.modeles.enums import Role


def test_aucun_prix_des_referentiels_chez_l_alimentation(application: FastAPI) -> None:
    """Hérité : test_defauts_f::test_alimentation_ne_recoit_aucun_montant (F-05), sur une base
    qui porte des prix, des cours, des taux de droits et des banques."""
    usd = devise(cours="10.5")
    f = fournisseur(devise=usd, banque="Ziraat")
    m = matiere(
        fournisseur_id=f, prix="2.5", devise=usd, code_douanier_id=code_douanier(taux="0.1")
    )
    valeurs = {"ident": str(m), "id": str(m), "code": usd, "objet": "matiere", "q": "poil"}
    for role in (Role.alimentation, Role.administrateur):
        lu = balayer(application, client_de(application, role), valeurs)
        assert {url: x for url, x in lu.items() if x} == {}, role
    vu = balayer(application, client_de(application, Role.achats), valeurs)
    assert vu["/api/matieres"] and vu["/api/devises"] and vu["/api/codes-douaniers"]


def _ecritures() -> list[tuple[str, Any]]:
    """(chemin, corps sans version) d'une fiche de chaque référentiel."""
    return [
        (f"/api/magasins/{magasin()}", {"code": unique("MAG"), "nom": "x"}),
        (f"/api/postes-frais/{poste_frais()}", {"libelle": "x"}),
        (
            f"/api/codes-douaniers/{code_douanier()}",
            {"code": f"5402.{random.randint(1000, 9999)}", "taux_droits": 0},
        ),
        (f"/api/classification/couleurs/{valeur_classification('couleur')}", {"code": unique("C")}),
        (f"/api/fournisseurs/{fournisseur()}", {"nom": unique("F")}),
        (f"/api/devises/{devise()}", {"cours": 3}),
    ]


@pytest.mark.parametrize("rang", range(6))
def test_version_perimee_409_sur_chaque_ecriture(direction: TestClient, rang: int) -> None:
    """API-PRO § 0.1 : une version périmée → 409 `conflit_version`, rien n'est écrit."""
    chemin, corps = _ecritures()[rang]
    r = direction.put(chemin, json={**corps, "version": 99})
    assert (r.status_code, r.json()["code"]) == (409, "conflit_version"), chemin
    assert "entre-temps" in r.json()["detail"]
    assert direction.put(chemin, json={**corps, "version": 1}).status_code == 200, chemin
