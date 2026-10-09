"""Parité dynamique : inventaire, dossier d'importation, puis les gestes des corrections
déclarées qui changent une issue (K4, K2, K3)."""

from __future__ import annotations

from typing import Any

from parite_dynamique_outils import comparer_document, jouer
from parite_dynamique_scene import LOT, Scene, _liste


def inventaire(sc: Scene) -> None:
    """Un inventaire de la matière reçue dans le magasin : le lot reçu compté 5 kg de moins,
    le reste juste ; validé (ajustement)."""
    c = sc.ctx
    corps = {"date": c["jour"], "magasin_id": c["magasin"], "libelle": "Parité : inventaire"}
    i = jouer(
        sc.s,
        sc.j,
        "inventaire : ouverture",
        ("POST", "/api/inventaires", corps | {"articles": [c["matiere"]]}),
        ("POST", "/api/inventaires", corps | {"criteres": {"matieres": [c["matiere"]]}}),
    )
    ig, ip = i.reponse_gmp["id"], i.reponse_pro["id"]
    g = sc.s.gestion_mp["direction"].get(f"/api/inventaires/{ig}")
    p = sc.s.pro["direction"].get(f"/api/inventaires/{ip}")
    lot = c["lot_numero"] = LOT

    def comptes(fiche: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"ligne_id": x["id"], "compte": x["theorique"] - (5 if x["lot"] == lot else 0),
                 "justification": "Parité : écart compté"} for x in fiche["lignes"]]  # fmt: skip

    jouer(
        sc.s,
        sc.j,
        "inventaire : comptage",
        ("POST", f"/api/inventaires/{ig}/comptage", comptes(g)),
        (
            "PUT",
            f"/api/inventaires/{ip}/comptages",
            {"version": p["version"], "lignes": comptes(p)},
        ),
    )
    jouer(
        sc.s,
        sc.j,
        "inventaire : validation",
        ("POST", f"/api/inventaires/{ig}/valider", None),
        (
            "POST",
            f"/api/inventaires/{ip}/valider",
            {"version": sc.version_pro(f"/api/inventaires/{ip}")},
        ),
    )
    comparer_document(
        sc.j,
        "inventaire : validation",
        _liste("inventaires"),
        sc.s.gestion_mp["direction"].get(f"/api/inventaires/{ig}"),
        sc.s.pro["direction"].get(f"/api/inventaires/{ip}"),
    )


def dossier(sc: Scene) -> None:
    """Un dossier d'importation sur la facture de la réception : fret de 1 500 MAD, clos."""
    c = sc.ctx
    fg, fp = sc.ids["facture"]
    corps = {"libelle": "Parité : dossier", "banque": "Banque"}
    i = jouer(
        sc.s,
        sc.j,
        "dossier : ouverture",
        ("POST", "/api/dossiers", corps | {"facture_id": fg}),
        ("POST", "/api/dossiers", corps | {"facture_id": fp}),
    )
    dg, dp = i.reponse_gmp["id"], i.reponse_pro["id"]
    frais = {"montant": 1500, "piece": "FRET-PARITE"}
    jouer(
        sc.s,
        sc.j,
        "dossier : fret",
        ("POST", f"/api/dossiers/{dg}/charges", frais | {"poste": "FRET"}),
        (
            "POST",
            f"/api/dossiers/{dp}/frais",
            frais | {"poste_id": c["poste"], "version": sc.version_pro(f"/api/dossiers/{dp}")},
        ),
    )
    jouer(
        sc.s,
        sc.j,
        "dossier : clôture",
        ("POST", f"/api/dossiers/{dg}/cloturer", None),
        (
            "POST",
            f"/api/dossiers/{dp}/cloturer",
            {"version": sc.version_pro(f"/api/dossiers/{dp}"), "alertes_lues": True},
        ),
    )
    comparer_document(
        sc.j,
        "dossier : clôture",
        _liste("dossiers"),
        sc.s.gestion_mp["direction"].get(f"/api/dossiers/{dg}"),
        sc.s.pro["direction"].get(f"/api/dossiers/{dp}"),
    )


def refusee(sc: Scene) -> None:
    """K4 : une réception toute refusée (le camion renvoyé), validée puis annulée — PRO l'a
    toujours permis (K4) ; Gestion MP corrigé le permet aussi : même issue attendue."""
    c, x = sc.ctx, sc.ctx["ligne"]
    ligne = {
        "lot_numero": "PARITE-REFUS",
        "quantite_bl": 100,
        "quantite_pesee": 100,
        "magasin_id": c["magasin"],
        "qualite": "refuse",
        "prix": x["prix"],
        "devise": "USD",
    }
    corps = {"date": c["jour"], "fournisseur_id": c["fournisseur"], "numero_bl": "BL-PARITE-2"}
    i = jouer(
        sc.s,
        sc.j,
        "réception refusée : création",
        ("POST", "/api/receptions", corps | {"lignes": [ligne | {"article_id": c["matiere"]}]}),
        ("POST", "/api/receptions", corps | {"lignes": [ligne | {"matiere_id": c["matiere"]}]}),
    )
    rg, rp = i.reponse_gmp["id"], i.reponse_pro[0]["id"]
    jouer(
        sc.s,
        sc.j,
        "réception refusée : validation",
        ("POST", f"/api/receptions/{rg}/valider", None),
        (
            "POST",
            f"/api/receptions/{rp}/valider",
            {"version": sc.version_pro(f"/api/receptions/{rp}")},
        ),
    )
    motif = {"motif": "Parité : camion renvoyé"}
    jouer(
        sc.s,
        sc.j,
        "réception refusée : annulation (K4)",
        ("POST", f"/api/receptions/{rg}/annuler", motif),
        (
            "POST",
            f"/api/receptions/{rp}/annuler",
            motif | {"version": sc.version_pro(f"/api/receptions/{rp}")},
        ),
        attendu="K4",
    )
    g = next(r for r in sc.s.gestion_mp["direction"].get("/api/receptions") if r["id"] == rg)
    comparer_document(
        sc.j,
        "réception refusée : annulation (K4)",
        _liste("receptions"),
        g,
        sc.s.pro["direction"].get(f"/api/receptions/{rp}"),
    )


def perimetre(sc: Scene) -> None:
    """K2 puis K3 : un inventaire ouvert sur la seule matière reçue ; une sortie d'un autre fil
    du même magasin est refusée par Gestion MP (tout le magasin est suspendu), acceptée par PRO
    (K2 : seul le périmètre l'est). L'inventaire est ensuite abandonné (K3 : gardé, numéroté).
    Joué en dernier : après K2, les deux bases ne portent plus le même stock."""
    c = sc.ctx
    corps = {"date": c["jour"], "magasin_id": c["magasin"], "libelle": "Parité : périmètre"}
    i = jouer(
        sc.s,
        sc.j,
        "inventaire du périmètre : ouverture",
        ("POST", "/api/inventaires", corps | {"articles": [c["matiere"]]}),
        ("POST", "/api/inventaires", corps | {"criteres": {"matieres": [c["matiere"]]}}),
    )
    ig, ip = i.reponse_gmp["id"], i.reponse_pro["id"]
    _sortie_hors_perimetre(sc)
    _abandon(sc, ig, ip)


def _sortie_hors_perimetre(sc: Scene) -> None:
    """K2 : 10 kg d'un autre fil du même magasin, pendant l'inventaire."""
    c, autre = sc.ctx, sc.ctx["autre"]
    sortie = {"date": c["jour"], "magasin_id": c["magasin"], "commentaire": "Parité : K2"}
    o = jouer(
        sc.s,
        sc.j,
        "sortie hors périmètre : création",
        (
            "POST",
            "/api/bons",
            sortie
            | {
                "fabrications": [],
                "lignes": [
                    {"article_id": autre["article_id"], "lot_id": autre["lot_id"], "quantite": 10}
                ],
            },
        ),
        (
            "POST",
            "/api/ordres",
            sortie
            | {
                "qualites": [],
                "lignes": [
                    {"matiere_id": autre["article_id"], "lot_id": autre["lot_id"], "quantite": 10}
                ],
            },
        ),
    )
    og, op = o.reponse_gmp["id"], o.reponse_pro["id"]
    k2 = jouer(
        sc.s,
        sc.j,
        "sortie hors périmètre : validation (K2)",
        ("POST", f"/api/bons/{og}/valider", None),
        ("POST", f"/api/ordres/{op}/valider", {"version": sc.version_pro(f"/api/ordres/{op}")}),
        attendu="K2",
    )
    sc.k2 = k2
    attendu = "est en cours sur"  # K2 vérifiée : Gestion MP refuse pour la suspension du magasin
    for e in sc.j.resultat("sortie hors périmètre : validation (K2)").ecarts:
        if e.classe == "K2" and attendu not in str(k2.reponse_gmp):
            e.classe = None


def _abandon(sc: Scene, ig: int, ip: int) -> None:
    """K3 : l'inventaire abandonné des deux côtés, puis comparé."""
    motif = {"motif": "Parité : abandon"}
    jouer(
        sc.s,
        sc.j,
        "inventaire du périmètre : abandon (K3)",
        ("DELETE", f"/api/inventaires/{ig}", None),
        (
            "POST",
            f"/api/inventaires/{ip}/abandonner",
            motif | {"version": sc.version_pro(f"/api/inventaires/{ip}")},
        ),
    )
    comparer_document(
        sc.j,
        "inventaire du périmètre : abandon (K3)",
        _liste("inventaires"),
        sc.s.gestion_mp["direction"].get(f"/api/inventaires/{ig}"),
        sc.s.pro["direction"].get(f"/api/inventaires/{ip}"),
    )
