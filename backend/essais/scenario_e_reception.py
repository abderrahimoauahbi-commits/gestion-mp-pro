"""Étapes 7 et 8 du scénario : le camion de deux bons en deux devises, la quarantaine libérée.

Jeudi 19 novembre, un camion apporte, du bon USD : M1 en trois lots (IST-1101 : BL 1 030 kg,
pesé 990 kg, 2 palettes ; IST-1102 : 500 kg, 1 palette ; IST-1103 : 200 kg **refusé**) et M2
(IST-2201 : 1 000 kg) ; du bon EUR : M3 entier (6 000 kg, 15 palettes) **sous réserve**, en
**lot interne**. Deux factures (une par devise) : INV-2611-118, 8 390 USD — le fournisseur a
facturé les poids du BL **et** le lot refusé : 1 730 × 3 + 1 000 × 3,2 —, INV-2611-119,
10 800 EUR.

Calculs à la main :
- reçu du bon USD : M1 990 + 500 = 1 490 (le refusé ne compte pas), reste 14 500 − 1 490
  = 13 010 ; M2 1 000, reste 3 718 − 1 000 = 2 718 ;
- poids de bobine mesuré : IST-1101 990 / (2 × 100) = 4,95 kg ; IST-1102 500 / 100 = 5 kg ;
  M3 6 000 / 1 500 = 4 kg ; écart de pesée IST-1101 (990 − 1 030) / 1 030 = −3,8835 % (au-delà
  des 2 % : contrôle C08) ;
- coût d'entrée au prix confirmé × cours figé du bon : M1 3 × 10 = 30 MAD/kg, M2 3,2 × 10 = 32,
  M3 1,8 × 11 = 19,80 ; valeur entrée 1 490 × 30 + 1 000 × 32 + 6 000 × 19,8 = 44 700
  + 32 000 + 118 800 = 195 500 MAD ;
- ponctualité : reçu le 19, promis le 25 → à l'heure (9 j ≤ 15 j) ; complétude : bon USD
  incomplet (1 490 < 14 500 − 2 %), bon EUR complet ; conformité : 0 (un refus, une réserve) ;
  OTIF 0 pour les deux réceptions.
"""

from __future__ import annotations

from typing import Any

from scenario_e_achats import numero_suivant
from scenario_monde import Monde
from scenario_outils import KG, MAD, UNITAIRE

COUT = {"M1": 30.0, "M2": 32.0, "M3": 19.8}
ENTREE = {"M1": 1490.0, "M2": 1000.0, "M3": 6000.0}
FACTURE_USD = 1730 * 3.0 + 1000 * 3.2  # 5 190 + 3 200 = 8 390 USD
FACTURE_EUR = 6000 * 1.8  # 10 800 EUR


def magasins(m: Monde) -> dict[str, int]:
    """Le premier magasin courant et le premier de quarantaine (par id)."""
    lus = sorted(m.D.get("/magasins"), key=lambda x: x["id"])
    courant = next(x["id"] for x in lus if x["type"] == "stock_courant" and x["actif"])
    quarantaine = next(x["id"] for x in lus if x["type"] == "quarantaine" and x["actif"])
    return {"courant": courant, "quarantaine": quarantaine}


def valorisation(m: Monde, jour: str = "") -> dict[str, Any]:
    """La valorisation (direction), avec les lignes du scénario indexées par clé."""
    lue = m.D.get("/valorisation" + (f"?date={jour}" if jour else ""))
    refs = {m.ids[k]: k for k in ("M1", "M2", "M3") if k in m.ids}
    lue["scn"] = {refs[x["matiere_id"]]: x for x in lue["lignes"] if x.get("matiere_id") in refs}
    return dict(lue)


def photo(m: Monde, nom: str, jour: str = "") -> None:
    """Stock, coût moyen et valeur des trois matières : la photo comparée à Gestion MP."""
    scn = valorisation(m, jour)["scn"]
    m.avant.setdefault("photos", {})[nom] = {
        k: (x["stock"], x["cmup_mad"], x["valeur_mad"]) for k, x in scn.items()
    }


def _ligne_bon(m: Monde, bon: str, cle: str) -> dict[str, Any]:
    fiche = m.A.get(f"/commandes/{m.ids[bon]}")
    return dict(next(x for x in fiche["lignes"] if x["matiere_id"] == m.ids[cle]))


def _lignes(m: Monde, mag: dict[str, int]) -> list[dict[str, Any]]:
    l_m1, l_m2 = _ligne_bon(m, "BC_USD", "M1")["id"], _ligne_bon(m, "BC_USD", "M2")["id"]
    l_m3 = _ligne_bon(m, "BC_EUR", "M3")["id"]
    c = {"magasin_id": mag["courant"], "qualite": "conforme"}
    return [
        {
            "commande_ligne_id": l_m1,
            "matiere_id": m.ids["M1"],
            "lot_numero": "IST-1101",
            "quantite_bl": 1030,
            "quantite_pesee": 990,
            "nb_palettes": 2,
        }
        | c,
        {
            "commande_ligne_id": l_m1,
            "matiere_id": m.ids["M1"],
            "lot_numero": "IST-1102",
            "quantite_bl": 500,
            "quantite_pesee": 500,
            "nb_palettes": 1,
        }
        | c,
        {
            "commande_ligne_id": l_m1,
            "matiere_id": m.ids["M1"],
            "lot_numero": "IST-1103",
            "quantite_bl": 200,
            "quantite_pesee": 200,
            "qualite": "refuse",
            "observations": "bobines tachées d'huile",
        },
        {
            "commande_ligne_id": l_m2,
            "matiere_id": m.ids["M2"],
            "lot_numero": "IST-2201",
            "quantite_bl": 1000,
            "quantite_pesee": 1000,
        }
        | c,
        {
            "commande_ligne_id": l_m3,
            "matiere_id": m.ids["M3"],
            "lot_interne": True,
            "quantite_bl": 6000,
            "quantite_pesee": 6000,
            "nb_palettes": 15,
            "magasin_id": mag["quarantaine"],
            "qualite": "reserve",
            "observations": "humidité à contrôler",
        },
    ]


def etape_camion(m: Monde) -> None:
    """Étape 7 (19 novembre, achats) : un camion, deux bons, deux devises, une requête."""
    v, a = m.verif, m.A
    m.jour("camion")
    mag = magasins(m)
    m.ids |= {f"mag_{k}": x for k, x in mag.items()}
    m.avant["valo_19"] = valorisation(m)
    existants = a.get("/receptions")
    corps = {
        "date": "2026-11-19",
        "fournisseur_id": m.ids["F1"],
        "numero_bl": "IRS-2611-07",
        "controle_par": "Amine",
        "observations": "Camion TIR 34-SCN-2611",
        "factures": {
            "USD": {"numero": "INV-2611-118", "date": "2026-11-18", "montant": FACTURE_USD},
            "EUR": {"numero": "INV-2611-119", "date": "2026-11-18", "montant": FACTURE_EUR},
        },
        "lignes": _lignes(m, mag),
    }
    v.refus("l'alimentation ne reçoit pas", m.L.appeler("POST", "/receptions", corps), 403)
    recues = a.ok("POST", "/receptions", corps, attendu=201)
    v.egal("une réception par devise", sorted(r["devise"] for r in recues), ["EUR", "USD"])
    par = {r["devise"]: r for r in recues}
    m.ids["REC_USD"], m.ids["REC_EUR"] = par["USD"]["id"], par["EUR"]["id"]
    for devise in ("USD", "EUR"):
        v.egal(f"réception {devise} : brouillon sans numéro", par[devise]["numero"], None)
    attendu = numero_suivant(m, "REC", existants)
    fiches = {
        d: a.post(f"/receptions/{par[d]['id']}/valider", {"version": par[d]["version"]})
        for d in ("USD", "EUR")
    }
    n_usd, n_eur = fiches["USD"]["numero"] or "", fiches["EUR"]["numero"] or ""
    v.vrai("numéro REC au moins le suivant", n_usd >= attendu, f"({n_usd} ≥ {attendu})")
    v.egal("deux numéros sans trou", int(n_eur[-4:]), int(n_usd[-4:]) + 1)
    _verifier_fiches(m, fiches)
    _verifier_stock(m)
    photo(m, "camion")
    m.avant["faits"]["receptions"] = [n_usd, n_eur]


def _verifier_fiches(m: Monde, fiches: dict[str, dict[str, Any]]) -> None:
    v = m.verif
    usd, eur = fiches["USD"], fiches["EUR"]
    v.egal("USD : validée", usd["statut"], "validee")
    v.egal("USD : une ligne refusée", usd["nb_refus"], 1)
    v.egal("EUR : une ligne sous réserve", eur["nb_reserve"], 1)
    v.egal("USD : facture", (usd["facture"] or {}).get("montant"), FACTURE_USD, MAD)
    v.egal("EUR : facture", (eur["facture"] or {}).get("montant"), FACTURE_EUR, MAD)
    lots = {x["lot_numero"]: x for x in usd["lignes"]}
    v.egal("IST-1101 : poids de bobine mesuré", lots["IST-1101"]["poids_moyen_bobine"], 4.95, 1e-6)
    v.egal("IST-1101 : 200 bobines", lots["IST-1101"]["nb_bobines"], 200, 1e-9)
    v.egal(
        "IST-1101 : écart de pesée", lots["IST-1101"]["ecart_relatif"], (990 - 1030) / 1030, 1e-9
    )
    v.egal("IST-1101 : hors tolérance", lots["IST-1101"]["hors_tolerance"], True)
    v.egal("IST-1102 : poids de bobine", lots["IST-1102"]["poids_moyen_bobine"], 5.0, 1e-6)
    v.egal("IST-1102 : prix du bon confirmé", lots["IST-1102"]["prix"], 3.0, 1e-9)
    v.egal("IST-1103 refusé : sans lot", lots["IST-1103"]["lot_id"], None)
    ligne_m3 = eur["lignes"][0]
    v.vrai(
        "M3 : lot interne numéroté",
        (ligne_m3["lot_numero"] or "").startswith("LOT-2026-"),
        f"({ligne_m3['lot_numero']})",
    )
    v.egal("M3 : poids de bobine", ligne_m3["poids_moyen_bobine"], 4.0, 1e-6)
    m.ids["lot_1101"], m.ids["lot_1102"] = lots["IST-1101"]["lot_id"], lots["IST-1102"]["lot_id"]
    m.ids["lot_2201"] = lots["IST-2201"]["lot_id"]
    m.ids["lot_m3"] = ligne_m3["lot_id"]
    m.avant["lot_m3"] = ligne_m3["lot_numero"]


def _verifier_stock(m: Monde) -> None:
    v, a = m.verif, m.A
    for bon, cle, recu, reste in (
        ("BC_USD", "M1", 1490.0, 13010.0),
        ("BC_USD", "M2", 1000.0, 2718.0),
        ("BC_EUR", "M3", 6000.0, 0.0),
    ):
        x = _ligne_bon(m, bon, cle)
        v.egal(f"{cle} : reçu sur le bon", x["recu"], recu, KG)
        v.egal(f"{cle} : reste", x["reste"], reste, KG)
    v.egal(
        "M3 : en quarantaine sur le bon",
        _ligne_bon(m, "BC_EUR", "M3")["en_quarantaine"],
        6000.0,
        KG,
    )
    eur = a.get(f"/commandes/{m.ids['BC_EUR']}")
    v.egal("bon EUR : pas soldé tant que la réserve tient", eur["statut"], "confirmee")
    v.egal("bon EUR : livré sous réserve", eur["livraison"], "sous_reserve")
    valo, avant = valorisation(m), m.avant["valo_19"]
    for cle in ("M1", "M2", "M3"):
        x = valo["scn"][cle]
        v.egal(f"{cle} : stock", x["stock"], ENTREE[cle], KG)
        v.proche(f"{cle} : coût moyen", x["cmup_mad"], COUT[cle], UNITAIRE)
        v.egal(f"{cle} : valeur", x["valeur_mad"], ENTREE[cle] * COUT[cle], MAD)
    v.egal(
        "valeur du stock de l'usine : + 195 500 MAD",
        valo["total_mad"],
        avant["total_mad"] + 195500.0,
        MAD,
    )
    lu = a.get(f"/stock/{m.ids['M3']}")["ligne"]
    v.egal("M3 : quarantaine hors du disponible", lu["stock_disponible"], 0.0, KG)
    v.egal("M3 : quarantaine en stock", lu["stock_net"], 6000.0, KG)
    perf = a.get("/fournisseurs/performance?du=2026-11-19&au=2026-11-19")
    notees = {r.get("reception_id") or r.get("id"): r for r in perf["receptions"]}
    m.avant["perf_19"] = perf
    for cle, plein in (("REC_USD", 0), ("REC_EUR", 1)):
        r = notees.get(m.ids[cle])
        if v.vrai(f"{cle} : notée", r is not None):
            assert r is not None
            v.egal(f"{cle} : à l'heure", r.get("on_time"), 1)
            v.egal(f"{cle} : complète", r.get("in_full"), plein)
            v.egal(f"{cle} : conforme", r.get("in_spec"), 0)
            v.egal(f"{cle} : OTIF", r.get("otif"), 0)
    v.refus("l'alimentation ne lit pas la valorisation", m.L.appeler("GET", "/valorisation"), 403)


def etape_liberation(m: Monde) -> None:
    """Étape 8 (20 novembre, achats) : la réserve levée, le bon EUR se solde de lui-même."""
    v, a = m.verif, m.A
    jour = m.jour("liberation")
    motifs = a.get("/motifs")["motifs"]
    liberation = next(x["id"] for x in motifs if x["libelle"] == "Libération de quarantaine")
    corps = {
        "type": "transfert",
        "date": jour.isoformat(),
        "motif_id": liberation,
        "commentaire": "Contrôle d'humidité conforme (7,8 %).",
        "valider": True,
        "lignes": [
            {
                "matiere_id": m.ids["M3"],
                "lot_id": m.ids["lot_m3"],
                "magasin_id": m.ids["mag_quarantaine"],
                "magasin_destination_id": m.ids["mag_courant"],
                "quantite": 6000,
            }
        ],
    }
    r = m.L.appeler("POST", "/operations", corps)
    v.refus("l'alimentation ne libère pas", r, 403, None, "décision des achats")
    op = a.ok("POST", "/operations", corps, attendu=201)
    v.vrai("libération : TRF numéroté", (op.get("numero") or "").startswith("TRF-2026-"))
    eur = a.get(f"/commandes/{m.ids['BC_EUR']}")
    m.avant["faits"]["bon_eur"] = eur["statut"]
    v.egal("bon EUR : soldé de lui-même", eur["statut"], "soldee")
    v.egal("bon EUR : solde automatique", eur["solde_origine"], "automatique")
    v.egal("bon EUR : livré", eur["livraison"], "livre")
    v.egal("bon EUR : livré le 19 (le camion)", (eur["livree_le"] or "")[:10], "2026-11-19")
    v.egal("bon EUR : soldé le 20 (la libération)", (eur["solde_le"] or "")[:10], "2026-11-20")
    lu = a.get(f"/stock/{m.ids['M3']}")["ligne"]
    v.egal("M3 : disponible après libération", lu["stock_disponible"], 6000.0, KG)
    v.egal("M3 : plus en quarantaine", lu["stock_quarantaine"], 0.0, KG)
    v.egal(
        "M3 : valeur inchangée par un transfert",
        valorisation(m)["scn"]["M3"]["valeur_mad"],
        118800.0,
        MAD,
    )
