"""Audit n° 2 (14/10/2026) — deux refus qui disaient mal pourquoi.

- Un frais sous le demi-centime (0,004 MAD) arrondit à zéro : la base le refusait par sa
  contrainte (« règle de la base… valeur hors limites »), le serveur le dit maintenant en clair.
- Changer « entre dans la valeur en douane » (ou la nature) d'un poste système : le refus disait
  « est un coût par nature » ; il dit maintenant que c'est un poste système, ce qui ne change
  pas, et pourquoi (les repères du dossier le lisent).
"""

from __future__ import annotations

from fabrique import *  # noqa: F403
from fabriques.importations import Import, ouvrir, poste
from fabriques.receptions import ok
from fastapi.testclient import TestClient


def test_un_frais_sous_le_centime_est_refuse_en_clair(achats: TestClient) -> None:
    """0,004 MAD vaut zéro au centime : 422 qui le dit, rien d'enregistré."""
    imp = Import.nouveau(cours="10")
    imp.recevoir(achats, "RC", [("ROUGE", "RC-R", 1000, 2.0)])
    d = ouvrir(achats, imp.f("RC"))
    r = achats.post(
        f"/api/dossiers/{d['id']}/frais",
        json={"version": d["version"], "poste_id": poste("TVA"), "montant": 0.004},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == (
        "Un frais a un montant d'au moins un centime (un avoir se saisit en négatif)."
    )
    assert ok(achats.get(f"/api/dossiers/{d['id']}"))["frais"] == []


def test_un_poste_systeme_dit_ce_qui_ne_change_pas(direction: TestClient) -> None:
    """FRET : décocher « entre dans la valeur en douane » est refusé par un message qui nomme le
    poste système, sa nature, et les repères qui la lisent."""
    fret = next(p for p in ok(direction.get("/api/postes-frais")) if p["code"] == "FRET")
    corps = {k: fret[k] for k in ("libelle", "recuperable", "nature", "cle", "ordre", "version")}
    corps["entre_valeur_douane"] = False
    r = direction.put(f"/api/postes-frais/{fret['id']}", json=corps)
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == (
        "« Fret » est un poste système : il reste un coût, de nature « fret » et entre dans la "
        "valeur en douane — les calculs du dossier (valeur en douane, droits et TVA attendus) le "
        "lisent ainsi. Une autre nature se crée comme un autre poste."
    )
    relu = next(p for p in ok(direction.get("/api/postes-frais")) if p["code"] == "FRET")
    assert relu["entre_valeur_douane"] is True and relu["version"] == fret["version"]
