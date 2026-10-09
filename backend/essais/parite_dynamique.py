"""Parité dynamique (PLAN-DE-RECETTE-PRO § 7.4), version réduite en attendant le scénario V2.

Une semaine d'usine jouée **geste par geste** dans les deux logiciels, par leurs API, sur les
deux copies de l'année d'essai (Gestion MP sur sa copie, PRO sur la base reprise) : réception
sur un bon confirmé (avec sa facture en dollars), ordre de fabrication, retour des machines,
sortie refusée (plus que le lot), inventaire avec un écart, dossier d'importation clos ; puis
les deux corrections déclarées qui changent une issue : K2 (un inventaire ne suspend que son
périmètre) et K4 (une réception toute refusée s'annule). Après chaque geste : même issue, même
numéro, même document, et le même changement du stock, de la valorisation et des lots.
Le scénario V2 (`essais/scenario_complet.py`, 23 étapes, chaque rôle avec son compte) l'étendra.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from parite_api import Route
from parite_api_formes import code
from parite_api_regles import REGLES
from parite_dynamique_outils import Journal, comparer_document, jouer
from parite_dynamique_scene import FACTURE, LOT, Scene, _liste
from parite_dynamique_suite import dossier, inventaire, perimetre, refusee
from parite_serveurs import Serveurs


def reception(sc: Scene) -> None:
    """Une réception sur le bon, pesée sous le BL, facturée en dollars, validée."""
    c, x = sc.ctx, sc.ctx["ligne"]
    q = 1000.0
    pese = next(  # pesé × prix au centime : l'arrondi K1 (MONTANT) est prouvé ailleurs
        (
            p
            for p in (990.0, 980.0, 995.0, 970.0)
            if (Decimal(str(p)) * Decimal(str(x["prix"])) * 100) % 1 == 0
        ),
        990.0,
    )
    facture = {"numero": FACTURE, "date": c["jour"], "montant": round(pese * x["prix"], 2)}
    ligne = {"commande_ligne_id": x["id"], "lot_numero": LOT, "quantite_bl": q,
             "quantite_pesee": pese, "nb_palettes": 2, "magasin_id": c["magasin"],
             "qualite": "conforme", "prix": x["prix"], "devise": "USD"}  # fmt: skip
    corps = {"date": c["jour"], "fournisseur_id": c["fournisseur"], "numero_bl": "BL-PARITE-1"}
    i = jouer(
        sc.s,
        sc.j,
        "réception : création",
        (
            "POST",
            "/api/receptions",
            corps
            | {
                "facture": facture | {"devise": "USD"},
                "lignes": [ligne | {"article_id": c["matiere"]}],
            },
        ),
        (
            "POST",
            "/api/receptions",
            corps
            | {"factures": {"USD": facture}, "lignes": [ligne | {"matiere_id": c["matiere"]}]},
        ),
    )
    rg, rp = i.reponse_gmp["id"], i.reponse_pro[0]["id"]
    sc.ids["reception"] = (rg, rp)
    jouer(
        sc.s,
        sc.j,
        "réception : validation",
        ("POST", f"/api/receptions/{rg}/valider", None),
        (
            "POST",
            f"/api/receptions/{rp}/valider",
            {"version": sc.version_pro(f"/api/receptions/{rp}")},
        ),
    )
    g = next(r for r in sc.s.gestion_mp["direction"].get("/api/receptions") if r["id"] == rg)
    p = sc.s.pro["direction"].get(f"/api/receptions/{rp}")
    comparer_document(sc.j, "réception : validation", _liste("receptions"), g, p)
    sc.lots |= {g["lignes"][0]["lot_id"], p["lignes"][0]["lot_id"]}
    sc.ids["lot"] = (g["lignes"][0]["lot_id"], p["lignes"][0]["lot_id"])
    sc.ids["facture"] = (g["facture"]["id"], p["facture"]["id"])
    _bon(sc)


def _bon(sc: Scene) -> None:
    """Le bon après la réception : reçu, reste, livraison, ligne par ligne."""
    bid = sc.ctx["bon"]["id"]
    g = next(c for c in sc.s.gestion_mp["direction"].get("/api/commandes") if c["id"] == bid)
    p = sc.s.pro["direction"].get(f"/api/commandes/{bid}")
    champs = ("recu", "reste_kg", "part_livree", "statut", "livraison")
    vue_g = {k: (code(g[k], p[k])[0] if k == "livraison" else g[k]) for k in champs}
    vue_g["lignes"] = {str(x["id"]): {k: x[k] for k in ("recu", "reste", "en_quarantaine")}
                       for x in g["lignes"]}  # fmt: skip
    vue_p = {k: p[k] for k in champs}
    vue_p["lignes"] = {str(x["id"]): {k: x[k] for k in ("recu", "reste", "en_quarantaine")}
                       for x in p["lignes"]}  # fmt: skip
    comparer_document(
        sc.j, "réception : le bon", _liste_simple(), vue_g | {"id": bid}, vue_p | {"id": bid}
    )


def _liste_simple() -> Any:
    from parite_api import Liste

    return Liste(("id",))


def ordre(sc: Scene) -> None:
    """Un ordre hors recette : 300 kg du lot reçu, 50 kg d'un autre fil ; validé."""
    c = sc.ctx
    lg, lp = sc.ids["lot"]
    autre = c["autre"]
    corps = {"date": c["jour"], "magasin_id": c["magasin"], "commentaire": "Parité : hors recette"}
    i = jouer(
        sc.s,
        sc.j,
        "ordre : création",
        (
            "POST",
            "/api/bons",
            corps
            | {
                "fabrications": [],
                "lignes": [
                    {"article_id": c["matiere"], "lot_id": lg, "quantite": 300},
                    {"article_id": autre["article_id"], "lot_id": autre["lot_id"], "quantite": 50},
                ],
            },
        ),
        (
            "POST",
            "/api/ordres",
            corps
            | {
                "qualites": [],
                "lignes": [
                    {"matiere_id": c["matiere"], "lot_id": lp, "quantite": 300},
                    {"matiere_id": autre["article_id"], "lot_id": autre["lot_id"], "quantite": 50},
                ],
            },
        ),
    )
    og, op = i.reponse_gmp["id"], i.reponse_pro["id"]
    sc.ids["ordre"] = (og, op)
    jouer(
        sc.s,
        sc.j,
        "ordre : validation",
        ("POST", f"/api/bons/{og}/valider", None),
        ("POST", f"/api/ordres/{op}/valider", {"version": sc.version_pro(f"/api/ordres/{op}")}),
    )
    _document_ordre(sc, "ordre : validation")


def _document_ordre(sc: Scene, nom: str) -> None:
    og, op = sc.ids["ordre"]
    g = next(b for b in sc.s.gestion_mp["direction"].get("/api/bons") if b["id"] == og)
    p = sc.s.pro["direction"].get(f"/api/ordres/{op}")
    comparer_document(sc.j, nom, _liste("ordres"), g, p)


def retour(sc: Scene) -> None:
    """40 kg du lot reçu reviennent des machines (reliquat de fin d'ordre) ; validé."""
    c = sc.ctx
    (lg, lp), (og, op) = sc.ids["lot"], sc.ids["ordre"]
    corps = {"type": "retour_machine", "date": c["jour"]}
    ligne = {"magasin_id": c["magasin"], "quantite": 40, "matiere_id": c["matiere"]}
    i = jouer(
        sc.s,
        sc.j,
        "retour des machines : création",
        (
            "POST",
            "/api/operations",
            corps
            | {
                "bon_id": og,
                "motif": "Reliquat de fin d'ordre",
                "lignes": [ligne | {"article_id": c["matiere"], "lot_id": lg}],
            },
        ),
        (
            "POST",
            "/api/operations",
            corps | {"ordre_id": op, "motif_id": c["motif"], "lignes": [ligne | {"lot_id": lp}]},
        ),
    )
    rg, rp = i.reponse_gmp["id"], i.reponse_pro["id"]
    jouer(
        sc.s,
        sc.j,
        "retour des machines : validation",
        ("POST", f"/api/operations/{rg}/valider", None),
        (
            "POST",
            f"/api/operations/{rp}/valider",
            {"version": sc.version_pro(f"/api/operations/{rp}")},
        ),
    )
    _document_ordre(sc, "retour des machines : l'ordre")


def refus(sc: Scene) -> None:
    """Une sortie de plus que le lot n'en a : refusée des deux côtés (création ou validation)."""
    c = sc.ctx
    lg, lp = sc.ids["lot"]
    corps = {"date": c["jour"], "magasin_id": c["magasin"], "commentaire": "Parité : refus"}
    i = jouer(
        sc.s,
        sc.j,
        "sortie de trop : création",
        (
            "POST",
            "/api/bons",
            corps
            | {
                "fabrications": [],
                "lignes": [{"article_id": c["matiere"], "lot_id": lg, "quantite": 100000}],
            },
        ),
        (
            "POST",
            "/api/ordres",
            corps
            | {
                "qualites": [],
                "lignes": [{"matiere_id": c["matiere"], "lot_id": lp, "quantite": 100000}],
            },
        ),
    )
    if i.statut_gmp < 300 and i.statut_pro < 300:  # noqa: PLR2004 — brouillon accepté : la validation refuse
        og, op = i.reponse_gmp["id"], i.reponse_pro["id"]
        jouer(
            sc.s,
            sc.j,
            "sortie de trop : validation",
            ("POST", f"/api/bons/{og}/valider", None),
            ("POST", f"/api/ordres/{op}/valider", {"version": sc.version_pro(f"/api/ordres/{op}")}),
        )
        jouer(
            sc.s,
            sc.j,
            "sortie de trop : brouillon retiré",
            ("DELETE", f"/api/bons/{og}", None),
            ("DELETE", f"/api/ordres/{op}?version={sc.version_pro(f'/api/ordres/{op}')}", None),
        )


def passe(s: Serveurs) -> Journal:
    """Le scénario entier ; chaque geste comparé, ce qu'il change comparé."""
    sc = Scene(s)
    for nom, geste in (("réception", reception), ("ordre", ordre), ("retour", retour),
                       ("refus", refus), ("inventaire", inventaire), ("dossier", dossier),
                       ("réception refusée", refusee)):  # fmt: skip
        sc.geste(nom, lambda g=geste: g(sc))
    perimetre(sc)
    neutre = Route("", "", "")
    for r in sc.j.resultats:
        for e in r.ecarts:
            e.classe = e.classe or next((c for c in (g(neutre, e) for g in REGLES) if c), None)
    return sc.j
