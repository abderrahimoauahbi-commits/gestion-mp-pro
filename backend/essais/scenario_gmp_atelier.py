"""Suite du rejeu dans Gestion MP (lot V2) : le camion, le dossier, l'atelier, la fin du mois.

Mêmes gestes que les étapes 7 à 17 de PRO (voir `scenario_gmp_gestes`).
"""

from __future__ import annotations

from typing import Any

from scenario_gmp_gestes import REFERENCES, Jeu, bon_de


def _lignes_camion(j: Jeu) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    usd, eur = bon_de(j, "BC_USD"), bon_de(j, "BC_EUR")
    lu = {x["article_id"]: x["id"] for x in usd["lignes"]}
    le = {x["article_id"]: x["id"] for x in eur["lignes"]}
    c = {"magasin_id": j.ids["mag_courant"], "qualite": "conforme"}
    m1, m2, m3 = j.ids["M1"], j.ids["M2"], j.ids["M3"]
    lignes_usd = [
        {
            "commande_ligne_id": lu[m1],
            "article_id": m1,
            "lot_numero": "IST-1101",
            "quantite_bl": 1030,
            "quantite_pesee": 990,
            "nb_palettes": 2,
        }
        | c,
        {
            "commande_ligne_id": lu[m1],
            "article_id": m1,
            "lot_numero": "IST-1102",
            "quantite_bl": 500,
            "quantite_pesee": 500,
            "nb_palettes": 1,
        }
        | c,
        {
            "commande_ligne_id": lu[m1],
            "article_id": m1,
            "lot_numero": "IST-1103",
            "quantite_bl": 200,
            "quantite_pesee": 200,
            "qualite": "refuse",
        },
        {
            "commande_ligne_id": lu[m2],
            "article_id": m2,
            "lot_numero": "IST-2201",
            "quantite_bl": 1000,
            "quantite_pesee": 1000,
        }
        | c,
    ]
    lignes_eur = [
        {
            "commande_ligne_id": le[m3],
            "article_id": m3,
            "lot_numero": "LOT INTERNE",
            "quantite_bl": 6000,
            "quantite_pesee": 6000,
            "nb_palettes": 15,
            "magasin_id": j.ids["mag_quarantaine"],
            "qualite": "reserve",
        }
    ]
    return lignes_usd, lignes_eur


def lots(j: Jeu) -> None:
    """Les lots du scénario (Gestion MP les retrouve par leur numéro : `/lots/scan`)."""
    d = j.p["D"]
    interne = next(x["lot"] for x in d.get("/lots")["lignes"] if x["reference"] == REFERENCES["M3"])
    for cle, numero in (
        ("lot_1101", "IST-1101"),
        ("lot_1102", "IST-1102"),
        ("lot_2201", "IST-2201"),
        ("lot_m3", interne),
    ):
        j.ids[cle] = d.get(f"/lots/scan?code={numero}")[0]["lot_id"]


def camion(j: Jeu) -> None:
    """19–20 novembre : le camion en deux devises, la quarantaine levée, le dossier USD."""
    a = j.p["A"]
    mags = {x["type"]: x["id"] for x in sorted(j.p["D"].get("/magasins"), key=lambda x: -x["id"])}
    j.ids["mag_courant"], j.ids["mag_quarantaine"] = mags["Stock courant"], mags["Quarantaine"]
    jour = j.jour("camion")
    lignes_usd, lignes_eur = _lignes_camion(j)
    commun = {"date": jour, "fournisseur_id": j.ids["F1"], "numero_bl": "IRS-2611-07"}
    recues = a.ok(
        "POST",
        "/receptions/par-devise",
        [
            commun
            | {
                "facture": {
                    "numero": "INV-2611-118",
                    "date": "2026-11-18",
                    "montant": 8390,
                    "devise": "USD",
                },
                "lignes": lignes_usd,
            },
            commun
            | {
                "facture": {
                    "numero": "INV-2611-119",
                    "date": "2026-11-18",
                    "montant": 10800,
                    "devise": "EUR",
                },
                "lignes": lignes_eur,
            },
        ],
    )
    numeros = [a.post(f"/receptions/{r['id']}/valider", {}).get("numero") for r in recues]
    j.photos["receptions"] = numeros
    lots(j)
    j.photo("camion")
    jour = j.jour("liberation")
    op = a.ok(
        "POST",
        "/operations",
        {
            "type": "transfert",
            "date": jour,
            "motif": "Libération de quarantaine",
            "commentaire": "Contrôle d'humidité conforme.",
            "lignes": [
                {
                    "article_id": j.ids["M3"],
                    "lot_id": j.ids["lot_m3"],
                    "magasin_id": j.ids["mag_quarantaine"],
                    "magasin_destination_id": j.ids["mag_courant"],
                    "quantite": 6000,
                }
            ],
        },
    )
    a.post(f"/operations/{op['id']}/valider", {})
    j.photos["bon_eur"] = bon_de(j, "BC_EUR")["statut"]
    _dossier(j)
    j.photo("dossier")


def _dossier(j: Jeu) -> None:
    a = j.p["A"]
    facture = next(f["id"] for f in a.get("/factures") if f["numero"] == "INV-2611-118")
    d = a.ok(
        "POST",
        "/dossiers",
        {
            "facture_id": facture,
            "libelle": "Camion TIR",
            "date_arrivee": "2026-11-19",
            "banque": "BMCE Bank",
        },
    )
    did = j.ids["dossier"] = d["id"]
    a.put(f"/dossiers/{did}/cours", {"cours": 10.2, "devise": "USD"})
    for poste, montant in (
        ("FRET", 4200),
        ("ROUTE", 1245),
        ("DD", 2060.85),
        ("TVA", 16940.19),
        ("TRANSIT", 1500),
    ):
        a.ok("POST", f"/dossiers/{did}/charges", {"poste": poste, "montant": montant})
    fiche = a.get(f"/dossiers/{did}")
    j.photos["dossier_fiche"] = {
        k: fiche.get(k)
        for k in (
            "marchandise_mad",
            "charges_mad",
            "revient_mad",
            "tva_attendue_mad",
            "droits_attendus_mad",
        )
    }
    a.post(f"/dossiers/{did}/cloturer", {})


def _bon_fabrication(
    j: Jeu, jour: str, qualites: dict[str, float], lignes: list[tuple[str, str, float, str]]
) -> Any:
    return j.p["L"].appeler(
        "POST",
        "/bons",
        {
            "date": jour,
            "magasin_id": j.ids["mag_courant"],
            "metier_id": j.ids["metier"],
            "fabrications": [{"qualite_id": j.ids[q], "m2": x} for q, x in qualites.items()],
            "lignes": [
                {"article_id": j.ids[k], "lot_id": j.ids[lot], "quantite": q, "unite": u}
                for k, lot, q, u in lignes
            ],
        },
    )


def _retour(j: Jeu, jour: str, bon: str, lot: str, bobines: float, *, motif: str) -> None:
    op = j.p["L"].ok(
        "POST",
        "/operations",
        {
            "type": "retour_machine",
            "date": jour,
            "bon_id": j.ids[bon],
            "motif": motif,
            "lignes": [
                {
                    "article_id": j.ids["M1"],
                    "lot_id": j.ids[lot],
                    "magasin_id": j.ids["mag_courant"],
                    "quantite": bobines,
                    "unite": "Bobine",
                }
            ],
        },
    )
    j.p["L"].post(f"/operations/{op['id']}/valider", {})


def atelier(j: Jeu) -> None:
    """23–24 novembre : OF1, montage, retour, OF2 et son retour, quarantaine, OF antidaté."""
    atl = j.p["L"]
    jour = j.jour("ordres")
    r = _bon_fabrication(
        j,
        jour,
        {"Q1": 300, "Q2": 200},
        [
            ("M1", "lot_1101", 116, "Bobine"),
            ("M2", "lot_2201", 153, "kg"),
            ("M3", "lot_m3", 0.6, "Palette"),
        ],
    )
    j.ids["OF1"] = r.corps["id"]
    of1 = atl.post(f"/bons/{j.ids['OF1']}/valider", {})
    j.photos["of1_numero"] = of1.get("numero")
    j.photo("of1")
    atl.put(
        f"/metiers/{j.ids['metier']}/etages/1",
        {"fils": [{"article_id": j.ids["M1"], "etage": 1, "metres": 0.3, "pourcentage": 100}]},
    )
    j.photo("montage")
    jour = j.jour("retour_machine")
    _retour(j, jour, "OF1", "lot_1101", 10, motif="Reliquat de fin d'ordre")
    r = _bon_fabrication(
        j, jour, {"Q2": 100}, [("M1", "lot_1102", 20, "Bobine"), ("M3", "lot_m3", 10, "Bobine")]
    )
    j.ids["OF2"] = r.corps["id"]
    atl.post(f"/bons/{j.ids['OF2']}/valider", {})
    _retour(j, jour, "OF2", "lot_1102", 2, motif="Changement de série / arrêt machine")
    j.photo("of2")
    op = atl.ok(
        "POST",
        "/operations",
        {
            "type": "transfert",
            "date": jour,
            "motif": "Mise en quarantaine",
            "commentaire": "Bobines humides au toucher.",
            "lignes": [
                {
                    "article_id": j.ids["M2"],
                    "lot_id": j.ids["lot_2201"],
                    "magasin_id": j.ids["mag_courant"],
                    "magasin_destination_id": j.ids["mag_quarantaine"],
                    "quantite": 50,
                }
            ],
        },
    )
    atl.post(f"/operations/{op['id']}/valider", {})
    r = _bon_fabrication(j, "2026-11-18", {"Q1": 10}, [("M1", "lot_1101", 2, "Bobine")])
    if r.statut in (200, 201):
        r = atl.appeler("POST", f"/bons/{r.corps['id']}/valider", {})
    j.photos["antidate"] = r.statut
    j.photo("quarantaine")


def fin_du_mois(j: Jeu) -> None:
    """25–27 novembre : retour au fournisseur, inventaire de M2, OF2 annulé."""
    a, d = j.p["A"], j.p["D"]
    jour = j.jour("retour_fournisseur")
    op = a.ok(
        "POST",
        "/operations",
        {
            "type": "retour_fournisseur",
            "date": jour,
            "motif": "Bobines endommagées",
            "lignes": [
                {
                    "article_id": j.ids["M3"],
                    "lot_id": j.ids["lot_m3"],
                    "magasin_id": j.ids["mag_courant"],
                    "quantite": 75,
                    "unite": "Bobine",
                }
            ],
        },
    )
    a.post(f"/operations/{op['id']}/valider", {})
    j.photos["bon_eur_rouvert"] = bon_de(j, "BC_EUR")["statut"]
    j.photo("retour_fournisseur")
    jour = j.jour("inventaire")
    inv = a.ok(
        "POST",
        "/inventaires",
        {"date": jour, "magasin_id": j.ids["mag_courant"], "articles": [j.ids["M2"]]},
    )
    ligne = next(
        x["id"]
        for x in a.get(f"/inventaires/{inv['id']}")["lignes"]
        if x["lot_id"] == j.ids["lot_2201"]
    )
    a.post(
        f"/inventaires/{inv['id']}/comptage",
        [{"ligne_id": ligne, "compte": 770, "justification": "bobines entamées"}],
    )
    d.post(
        f"/inventaires/{inv['id']}/comptage",
        [{"ligne_id": ligne, "second_compte": 780, "justification": "une bobine jetée"}],
    )
    fiche = a.get(f"/inventaires/{inv['id']}")
    j.photos["inventaire_ecart"] = (fiche["ecart_total"], fiche["ecart_valeur_mad"])
    a.post(f"/inventaires/{inv['id']}/valider", {})
    j.photo("inventaire")
    j.jour("annulation_ordre")
    j.p["L"].post(f"/bons/{j.ids['OF2']}/annuler", {})
    j.photo("annulation")
    j.jour("cloture")
    valo = d.get("/valorisation?date_reference=2026-11-30")
    par = {x["reference"]: x for x in valo["lignes"]}
    j.photos["fin_novembre"] = {
        k: (par[r]["stock"], par[r]["cmup_mad"], par[r]["valeur_mad"])
        for k, r in REFERENCES.items()
    }
