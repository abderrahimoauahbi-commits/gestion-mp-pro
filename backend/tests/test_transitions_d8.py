"""Table de transitions des documents du lot D8, rejouée exhaustivement (LOTS § 2).

État × geste × rôle → code HTTP et état suivant, chaque cas sur un document neuf d'une usine
isolée : un besoin signalé (à traiter, traité) que l'on traite ; une pièce jointe (active,
retirée) que l'on relit ou retire ; une facture et un frais d'importation (dus, réglés) que l'on
règle ou dont on annule le règlement.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fabrique import *  # noqa: F403
from fabriques.pilotage import Usine, fixture_usine, jour, ok  # noqa: F401
from fastapi.testclient import TestClient

from gestion_mp_pro.modeles import DossierFrais

ROLES = ("direction", "achats", "alimentation", "administrateur")
PDF = b"%PDF-1.4 transition"

SIGNALEMENT = {
    # (état, rôle) → (code, état après)
    ("a_traiter", "direction"): (200, "traite"),
    ("a_traiter", "achats"): (200, "traite"),
    ("a_traiter", "alimentation"): (403, "a_traiter"),
    ("a_traiter", "administrateur"): (403, "a_traiter"),
    ("traite", "direction"): (409, "traite"),
    ("traite", "achats"): (409, "traite"),
    ("traite", "alimentation"): (403, "traite"),
    ("traite", "administrateur"): (403, "traite"),
}
PIECE = {
    # (état, geste, rôle) → code ; un retrait réussi rend la pièce retirée
    **{("active", g, r): c for r in ("direction", "achats")
       for g, c in (("lire", 200), ("retirer", 204))},
    **{("retiree", g, r): c for r in ("direction", "achats")
       for g, c in (("lire", 404), ("retirer", 409))},
    **{(e, g, r): 403 for e in ("active", "retiree") for g in ("lire", "retirer")
       for r in ("alimentation", "administrateur")},
}  # fmt: skip
REGLEMENT = {
    # (état, geste, rôle) → (code, état après)
    ("due", "regler", "direction"): (200, "reglee"),
    ("due", "regler", "achats"): (200, "reglee"),
    ("due", "annuler", "direction"): (409, "due"),
    ("due", "annuler", "achats"): (409, "due"),
    ("reglee", "regler", "direction"): (200, "reglee"),
    ("reglee", "regler", "achats"): (200, "reglee"),
    ("reglee", "annuler", "direction"): (200, "due"),
    ("reglee", "annuler", "achats"): (403, "reglee"),
    **{(e, g, r): (403, e) for e in ("due", "reglee") for g in ("regler", "annuler")
       for r in ("alimentation", "administrateur")},
}  # fmt: skip


def poste(u: Usine, role: str) -> TestClient:
    """Le client d'un rôle."""
    return getattr(u, role)  # type: ignore[no-any-return]


def test_transitions_d_un_besoin_signale(usine: Usine) -> None:
    """8 cas : traiter un besoin à traiter ou déjà traité, par chaque rôle."""
    u = usine
    for (etat, role), (code, apres) in SIGNALEMENT.items():
        x = ok(u.alimentation.post("/api/signalements", json={"texte": f"{etat} {role}"}), 201)
        if etat == "traite":
            ok(u.achats.post(f"/api/signalements/{x['id']}/traiter", json={"reponse": "vu"}))
        r = poste(u, role).post(f"/api/signalements/{x['id']}/traiter", json={"reponse": "ok"})
        assert r.status_code == code, (etat, role, r.text)
        lu = ok(u.achats.get("/api/signalements", params={"limite": 1}))["elements"][0]
        assert lu["id"] == x["id"] and ("traite" if lu["traite"] else "a_traiter") == apres


def test_transitions_d_une_piece_jointe(usine: Usine) -> None:
    """16 cas : relire ou retirer une pièce active ou retirée, par chaque rôle."""
    u = usine
    f = u.fournisseur()
    for (etat, geste, role), code in PIECE.items():
        fichier = {"fichier": ("t.pdf", PDF, "application/pdf")}
        cible = {"objet": "fournisseur", "id": str(f)}
        p = ok(u.achats.post("/api/pieces", data=cible, files=fichier), 201)
        if etat == "retiree":
            assert u.achats.delete(f"/api/pieces/{p['id']}").status_code == 204
        client = poste(u, role)
        r = (
            client.get(f"/api/pieces/{p['id']}/fichier")
            if geste == "lire"
            else client.delete(f"/api/pieces/{p['id']}")
        )
        assert r.status_code == code, (etat, geste, role, r.text)
        actives = {
            x["id"]
            for x in ok(u.achats.get("/api/pieces", params={"objet": "fournisseur", "id": f}))
        }
        assert (p["id"] in actives) is (
            etat == "active" and not (geste == "retirer" and code == 204)
        )


def _facture(u: Usine, n: int) -> dict[str, Any]:
    f = u.fournisseur()
    m = u.matiere(fournisseur_id=f)
    corps = {
        "date": jour().isoformat(), "fournisseur_id": f,
        "lignes": [{"matiere_id": m, "lot_numero": f"TR-{n}", "quantite_pesee": 10,
                    "magasin_id": u.courant, "prix": 10}],
        "factures": {"MAD": {"numero": f"TR-F-{n}", "date": jour(-1).isoformat(),
                             "echeance": jour(20).isoformat()}},
    }  # fmt: skip
    r = ok(u.achats.post("/api/receptions", json=corps), 201)[0]
    ok(u.achats.post(f"/api/receptions/{r['id']}/valider", json={"version": r["version"]}))
    e = ok(u.achats.get("/api/echeancier", params={"q": f"TR-F-{n}"}))
    return e["lignes"][0]  # type: ignore[no-any-return]


def _frais(u: Usine, n: int) -> dict[str, Any]:
    d = u.dossier(frais={"TRANSIT": 100})
    ch = u.s.query(DossierFrais).filter_by(dossier_id=d.id).one()
    ch.echeance, ch.piece = jour(20), f"TRF-{n}"
    u.s.flush()
    return ok(u.achats.get("/api/echeancier", params={"q": f"TRF-{n}"}))["lignes"][0]  # type: ignore[no-any-return]


def _etat(u: Usine, x: dict[str, Any]) -> tuple[str, int]:
    e = ok(u.achats.get("/api/echeancier", params={"q": x["piece"]}))
    for vue, nom in (("lignes", "due"), ("reglees", "reglee")):
        for y in e[vue]:
            if y["id"] == x["id"] and y["objet"] == x["objet"]:
                return nom, y["version"]
    raise AssertionError(x)


def _rejouer(u: Usine, fabriquer: Callable[[Usine, int], dict[str, Any]]) -> None:
    for n, ((etat, geste, role), (code, apres)) in enumerate(REGLEMENT.items()):
        x = fabriquer(u, n)
        genre = "facture" if x["objet"] == "facture" else "frais"
        corps = {
            "genre": genre,
            "id": x["id"],
            "payee_le": jour().isoformat(),
            "version": x["version"],
        }
        if etat == "reglee":
            x = ok(u.direction.put("/api/echeancier/paiement", json=corps))
        corps |= {"version": x["version"]}
        if geste == "annuler":
            corps |= {"payee_le": None, "motif": "erreur de saisie"}
        r = poste(u, role).put("/api/echeancier/paiement", json=corps)
        assert r.status_code == code, (etat, geste, role, r.text)
        assert _etat(u, x)[0] == apres, (etat, geste, role)


def test_transitions_d_un_reglement_de_facture(usine: Usine) -> None:
    """16 cas : régler une facture due ou réglée, annuler son règlement, par chaque rôle."""
    _rejouer(usine, _facture)


def test_transitions_d_un_reglement_de_frais(usine: Usine) -> None:
    """16 cas : les mêmes gestes sur un frais d'importation."""
    _rejouer(usine, _frais)
