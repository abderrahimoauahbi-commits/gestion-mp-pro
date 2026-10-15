"""La facture saisie avec un brouillon de réception ne survit pas au brouillon (stress 10 ans).

Trouvé par le simulateur « 10 ans d'exploitation » (essais/stress) : un brouillon créé avec sa
facture puis **supprimé** laissait la facture en base, sans aucune réception ; l'échéancier la
comptait **due** (le moteur `calcul.suivi.factures_dues` ne connaît que les factures portées par
une réception : une facture que rien ne porte n'était ni « pas encore due » ni « écartée »). Le
vérificateur indépendant (V1) le disait aussi : « dans l'échéancier sans être due ». Même chose
quand le brouillon est **corrigé** avec un autre numéro de facture : l'ancienne restait due.
"""

from __future__ import annotations

from typing import Any

from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from sqlalchemy import select

from gestion_mp_pro.modeles import Facture


def _brouillon(u: Usine, f: int, numero: str, lot: str) -> dict[str, Any]:
    m = u.matiere(fournisseur_id=f)
    corps: dict[str, Any] = {
        "date": jour().isoformat(),
        "fournisseur_id": f,
        "lignes": [
            {
                "matiere_id": m,
                "lot_numero": lot,
                "quantite_pesee": 100,
                "magasin_id": u.courant,
                "prix": 10,
            }
        ],
        "factures": {
            "MAD": {
                "numero": numero,
                "date": jour(-5).isoformat(),
                "montant": 1000,
                "echeance": jour(25).isoformat(),
            }  # fmt: skip
        },
    }
    return ok(u.achats.post("/api/receptions", json=corps), 201)[0]  # type: ignore[no-any-return]


def _pieces(u: Usine) -> set[str]:
    e = u.get(u.achats, "/api/echeancier")
    return {x["piece"] for liste in ("lignes", "a_dater", "reglees", "ecartees") for x in e[liste]}


def test_la_facture_d_un_brouillon_supprime_disparait(usine: Usine) -> None:
    """Brouillon saisi avec sa facture, puis supprimé : la facture n'est plus due (ni en base)."""
    u = usine
    r = _brouillon(u, u.fournisseur("BR FILATURE"), "BR-F1", "L-BR-1")
    assert "BR-F1" not in _pieces(u)  # un brouillon ne rend pas sa facture due
    ok(u.achats.delete(f"/api/receptions/{r['id']}?version={r['version']}"), 204)
    assert "BR-F1" not in _pieces(u)
    assert u.s.scalar(select(Facture).where(Facture.numero == "BR-F1")) is None


def test_la_facture_remplacee_sur_un_brouillon_disparait(usine: Usine) -> None:
    """Brouillon corrigé avec un autre numéro de facture : l'ancienne, que rien ne porte plus,
    n'est plus due ; la nouvelle suit le brouillon."""
    u = usine
    r = _brouillon(u, u.fournisseur("BR FILATURE 2"), "BR-F2", "L-BR-2")
    fiche = u.get(u.achats, f"/api/receptions/{r['id']}")
    corps = {
        "date": fiche["date"],
        "fournisseur_id": fiche["fournisseur_id"],
        "version": fiche["version"],
        "factures": {"MAD": {"numero": "BR-F3", "date": jour(-5).isoformat(), "montant": 900}},
        "lignes": [
            {
                "matiere_id": x["matiere_id"],
                "lot_numero": x["lot_numero"],
                "quantite_pesee": x["quantite_pesee"],
                "magasin_id": x["magasin_id"],
                "prix": x["prix"],
            }
            for x in fiche["lignes"]
        ],
    }
    apres = ok(u.achats.put(f"/api/receptions/{r['id']}", json=corps))
    assert u.s.scalar(select(Facture).where(Facture.numero == "BR-F2")) is None
    ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": apres["version"]}))
    pieces = _pieces(u)
    assert "BR-F3" in pieces and "BR-F2" not in pieces


def test_la_facture_detachee_d_une_reception_validee_disparait(usine: Usine) -> None:
    """Après validation, un numéro vide détache la facture (R-RCP-33) : que rien ne porte plus,
    elle n'est plus due ; renumérotée, l'ancienne disparaît de même."""
    u = usine
    r = _brouillon(u, u.fournisseur("BR FILATURE 3"), "BR-F4", "L-BR-4")
    r = ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    assert "BR-F4" in _pieces(u)
    corps = {"version": r["version"], "numero": "BR-F5"}
    ok(u.achats.put(f"/api/receptions/{r['id']}/facture", json=corps))
    pieces = _pieces(u)
    assert "BR-F5" in pieces and "BR-F4" not in pieces
    assert u.s.scalar(select(Facture).where(Facture.numero == "BR-F4")) is None
    fiche = u.get(u.achats, f"/api/receptions/{r['id']}")
    corps = {"version": fiche["version"], "numero": ""}
    ok(u.achats.put(f"/api/receptions/{r['id']}/facture", json=corps))
    assert "BR-F5" not in _pieces(u)
    assert u.s.scalar(select(Facture).where(Facture.numero == "BR-F5")) is None
