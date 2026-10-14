"""Audit n° 2 du domaine achats (14/10/2026) : ce que l'audit a corrigé, prouvé par l'essai qui
échouait avant.

- Les mètres indicatifs (fiche du bon, bon fournisseur) suivent le drapeau `lineaire` du rôle,
  pas la seule présence d'une densité (P1).
- Un prix au mètre se confirme au mètre (`unite: 'ml'`) et se ramène au kilo par la densité (U2) ;
  un prix qui vaut 0 au kilo une fois arrondi est refusé, pas enregistré.
- Le cours du jour d'un bon (`taux_du_jour`) est une clé monétaire (P3).
"""

from __future__ import annotations

import pytest
from fabrique import *  # noqa: F403
from fabriques.achats import Achat, bon, geste, ok
from fabriques.documents import reglages
from fastapi.testclient import TestClient

from gestion_mp_pro.securite.prix import est_monetaire

SOCIETE = {"nom_entreprise": "TAPIS ESSAI SARL", "ice": "001122334455667"}


def test_les_metres_indicatifs_suivent_le_role_pas_la_densite(achats: TestClient) -> None:
    """Un poil à qui l'on a donné une densité n'a pas de mètres : ni dans la fiche, ni dans le
    bon fournisseur (colonne « Length » absente) ; un cuir les garde."""
    a = Achat.nouveau(devise="MAD")
    poil = a.matiere("POIL DENSE", role="Poil", densite="0.5", prix="2")
    cuir = a.matiere("CUIR", role="Cuir", densite="0.25", unite_prix="ml", prix="2.5")
    b = geste(achats, bon(achats, a, {poil: 300}), "envoyer")
    (ligne,) = b["lignes"]
    assert ligne["kg_par_ml"] == 0 and ligne["metres"] is None
    with reglages(SOCIETE):
        page = achats.get(f"/api/documents/commandes/{b['id']}/bon").text
    assert "Length (m, indicative)" not in page and "≈" not in page
    b2 = geste(achats, bon(achats, a, {cuir: 300}), "envoyer")
    (ligne,) = b2["lignes"]
    assert ligne["kg_par_ml"] == pytest.approx(0.25) and ligne["metres"] == pytest.approx(1200)


def test_un_prix_au_metre_se_confirme_au_metre(achats: TestClient) -> None:
    """U2 : 0,074 MAD / ml avec une densité de 0,014 kg/ml → 5,285714 MAD / kg sur la ligne ;
    le catalogue d'une fiche au mètre reprend 0,074 / ml."""
    a = Achat.nouveau(devise="MAD")
    cuir = a.matiere("CUIR ML", role="Cuir", densite="0.014", unite_prix="ml", prix="0.05")
    b = geste(achats, bon(achats, a, {cuir: 14}), "envoyer")
    lid = b["lignes"][0]["id"]
    b = geste(achats, b, "prix", lignes=[{"ligne_id": lid, "prix": 0.074, "unite": "ml"}])
    (ligne,) = b["lignes"]
    assert ligne["prix"] == pytest.approx(5.285714) and ligne["prix_confirme"]
    assert ligne["prix_catalogue"] == pytest.approx(0.074 / 0.014, rel=1e-6)
    assert ok(achats.get(f"/api/matieres/{cuir}"))["prix"] == pytest.approx(0.074)
    poil = a.matiere("POIL", prix="2")
    b2 = geste(achats, bon(achats, a, {poil: 10}), "envoyer")
    r = geste(achats, b2, "prix", 422,
              lignes=[{"ligne_id": b2["lignes"][0]["id"], "prix": 1, "unite": "ml"}])  # fmt: skip
    assert "n'a pas de densité : son prix se confirme au kilo" in r["detail"]


def test_un_prix_nul_une_fois_arrondi_est_refuse(achats: TestClient) -> None:
    """Un prix de 0,0000001 passe la borne (> 0) mais vaut 0 au millionième : refusé en clair,
    jamais un prix confirmé à zéro."""
    a = Achat.nouveau(devise="MAD")
    m = a.matiere("POIL", prix="2")
    b = geste(achats, bon(achats, a, {m: 10}), "envoyer")
    lid = b["lignes"][0]["id"]
    r = geste(achats, b, "prix", 422, lignes=[{"ligne_id": lid, "prix": 0.0000001}])
    assert "vaut 0 au kilo" in r["detail"] and "POIL" in r["detail"]
    relu = ok(achats.get(f"/api/commandes/{b['id']}"))
    assert relu["lignes"][0]["prix_confirme"] is False and relu["statut"] == "envoyee"


def test_le_cours_du_jour_d_un_bon_est_monetaire() -> None:
    """P3 : `taux_du_jour` (cours de change de la liste des bons) est masqué comme `cours`."""
    assert est_monetaire("taux_du_jour") and est_monetaire("cours")
    assert not est_monetaire("taux_perte")


def test_une_quantite_nulle_au_gramme_est_refusee_en_clair(achats: TestClient) -> None:
    """0,0001 kg passe la borne (> 0) mais vaut 0 au gramme : avant, la base refusait avec un
    409 « règle de la base » obscur ; la saisie est refusée en clair, à la création comme à la
    modification."""
    a = Achat.nouveau(devise="MAD")
    m = a.matiere("POIL", prix="2")
    corps = {"fournisseur_id": a.fournisseur_id, "lignes": [{"matiere_id": m, "quantite": 0.0001}]}
    r = achats.post("/api/commandes", json=corps)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "quantite_invalide" and "vaut 0 au gramme" in r.json()["detail"]
    b = bon(achats, a, {m: 10})
    corps = {"version": b["version"], "lignes": [{"matiere_id": m, "quantite": 0.0004}]}
    r = achats.put(f"/api/commandes/{b['id']}", json=corps)
    assert r.status_code == 422, r.text
    assert "POIL" in r.json()["detail"] and "0,0004" in r.json()["detail"]
