"""Étape 9 du scénario : la facture USD, son dossier d'importation, ses frais, sa clôture.

Vendredi 20 novembre. Marchandise du dossier (CALCULS § 9.3, 9.4) au cours de la banque
10,20 MAD/USD : IST-1101 990 kg × 3 = 2 970 USD → 30 294,00 MAD ; IST-1102 500 kg → 1 500 USD →
15 300,00 MAD ; IST-2201 1 000 kg × 3,2 = 3 200 USD → 32 640,00 MAD ; total 78 234,00 MAD,
2 490 kg. Le lot refusé n'entre pas (il n'est pas en stock).

Frais (MAD) : fret 4 200 (à la valeur, entre en valeur douane), transport routier 1 245 (au
poids), droits 2 060,85, TVA 16 940,19 (récupérable : hors coût), transitaire 1 500 (à la valeur).
- Valeur douane (CAF) = 78 234 + 4 200 = 82 434 ; droits attendus 2,5 % = 2 060,85 (écart 0).
- TPI non saisie → 82 434 × 0,25 % = 206,085 ; TVA attendue = (82 434 + 2 060,85 + 206,085)
  × 20 % = 16 940,187 (écart 0,003, toléré).
- Frais à la valeur 4 200 + 2 060,85 + 1 500 = 7 760,85 × part de valeur ; au poids 1 245 ×
  part de poids ; coût de revient = valeur + frais ; coût d'un lot au kilo au millionième ; coût
  moyen de M1 = (revient 1101 + revient 1102) / 1 490 ; de M2 = revient 2201 / 1 000.
- Écart de facture : 8 390 − 7 670 = 720 USD = 9,3872 % > 2 % (le lot refusé facturé : C36).
"""

from __future__ import annotations

from typing import Any

from scenario_e_reception import photo, valorisation
from scenario_monde import Monde
from scenario_outils import KG, MAD

COURS_BANQUE = 10.20
LIGNES = {"IST-1101": (990.0, 2970.0), "IST-1102": (500.0, 1500.0), "IST-2201": (1000.0, 3200.0)}
VALEUR = {lot: usd * COURS_BANQUE for lot, (_kg, usd) in LIGNES.items()}
MARCHANDISE = sum(VALEUR.values())  # 78 234,00
POIDS = sum(kg for kg, _usd in LIGNES.values())  # 2 490
FRAIS = {"FRET": 4200.00, "ROUTE": 1245.00, "DD": 2060.85, "TVA": 16940.19, "TRANSIT": 1500.00}
A_LA_VALEUR = FRAIS["FRET"] + FRAIS["DD"] + FRAIS["TRANSIT"]  # 7 760,85
CHARGES = {
    lot: A_LA_VALEUR * VALEUR[lot] / MARCHANDISE + FRAIS["ROUTE"] * kg / POIDS
    for lot, (kg, _usd) in LIGNES.items()
}
REVIENT = {lot: VALEUR[lot] + CHARGES[lot] for lot in LIGNES}
REVIENT_KG = {lot: REVIENT[lot] / LIGNES[lot][0] for lot in LIGNES}
CMUP_M1 = (REVIENT["IST-1101"] + REVIENT["IST-1102"]) / 1490
CMUP_M2 = REVIENT["IST-2201"] / 1000
DOUANE = MARCHANDISE + FRAIS["FRET"]  # 82 434
TVA_ATTENDUE = (DOUANE + FRAIS["DD"] + DOUANE * 0.0025) * 0.20  # 16 940,187


def _postes(m: Monde) -> dict[str, int]:
    return {x["code"]: x["id"] for x in m.A.get("/postes-frais")}


def _frais(m: Monde, did: int, postes: dict[str, int], code: str, **champs: Any) -> Any:
    version = m.A.get(f"/dossiers/{did}")["version"]
    corps = {"version": version, "poste_id": postes[code], "montant": FRAIS[code]} | champs
    return m.A.post(f"/dossiers/{did}/frais", corps)


def etape_dossier(m: Monde) -> None:
    """Étape 9 (20 novembre, achats) : facture, dossier, cours de la banque, frais, clôture."""
    v, a = m.verif, m.A
    m.jour("dossier")
    rec = a.get(f"/receptions/{m.ids['REC_USD']}")
    v.egal("facture USD : échéance = 18/11 + 60 j", rec["facture"]["echeance"], "2027-01-17")
    sans = a.get(f"/factures?sans_dossier=true&fournisseur={m.ids['F1']}")
    facture = next(f for f in sans if f["numero"] == "INV-2611-118")
    m.ids["facture_usd"] = facture["id"]
    m.ids["facture_eur"] = next(f["id"] for f in sans if f["numero"] == "INV-2611-119")
    v.egal("facture USD : estimée à la pesée × prix", facture["montant_estime"], 7670.0, MAD)
    v.refus("l'alimentation n'ouvre pas de dossier", m.L.appeler("GET", "/dossiers"), 403)
    d = a.ok(
        "POST",
        "/dossiers",
        {
            "facture_id": facture["id"],
            "libelle": "Camion TIR 34-SCN-2611",
            "date_arrivee": "2026-11-19",
            "banque": "BMCE Bank",
        },
        attendu=201,
    )
    did = m.ids["dossier_usd"] = d["id"]
    v.egal("dossier : trois marchandises", d["nb_lignes"], 3)
    v.egal("dossier : poids", d["poids"], POIDS, KG)
    d = a.put(
        f"/dossiers/{did}/cours", {"devise": "USD", "cours": COURS_BANQUE, "version": d["version"]}
    )
    v.egal("marchandise au cours de la banque", d["marchandise_mad"], MARCHANDISE, MAD)
    postes = _postes(m)
    piece = {"prestataire": "Trans-Atlas", "date_piece": "2026-11-20"}
    _frais(m, did, postes, "FRET", piece="FR-778", echeance="2026-11-30", **piece)
    _frais(m, did, postes, "ROUTE", piece="RT-12", echeance="2026-12-20", **piece)
    douane = {
        "piece": "DUM-2611-55",
        "prestataire": "Douane",
        "date_piece": "2026-11-19",
        "echeance": "2026-11-19",
    }
    _frais(m, did, postes, "DD", **douane)
    _frais(m, did, postes, "TVA", **douane)
    d = _frais(m, did, postes, "TRANSIT", piece="", prestataire="Transit Fès")
    _verifier_dossier(m, d)
    m.avant["faits"]["dossier_fiche"] = {
        k: d[k]
        for k in (
            "marchandise_mad",
            "charges_mad",
            "revient_mad",
            "tva_attendue_mad",
            "droits_attendus_mad",
        )
    }
    d = a.post(f"/dossiers/{did}/cloturer", {"version": d["version"], "alertes_lues": True})
    v.egal("dossier clos", d["statut"], "clos")
    _verifier_cmup(m)
    photo(m, "dossier")


def _verifier_dossier(m: Monde, d: dict[str, Any]) -> None:
    v = m.verif
    v.egal("marchandise", d["marchandise_mad"], MARCHANDISE, MAD)
    v.egal("frais hors TVA répartis", d["charges_mad"], A_LA_VALEUR + FRAIS["ROUTE"], MAD)
    v.egal("TVA saisie", d["tva_mad"], FRAIS["TVA"], MAD)
    v.egal("coût hors TVA", d["revient_mad"], MARCHANDISE + A_LA_VALEUR + FRAIS["ROUTE"], MAD)
    v.egal(
        "décaissé",
        d["decaisse_mad"],
        MARCHANDISE + A_LA_VALEUR + FRAIS["ROUTE"] + FRAIS["TVA"],
        MAD,
    )
    v.egal("coût au kilo du dossier", d["revient_kg"], sum(REVIENT.values()) / POIDS, 1e-6)
    v.egal("surcoût", d["surcout"], (A_LA_VALEUR + FRAIS["ROUTE"]) / MARCHANDISE, 1e-9)
    v.egal("TVA attendue (avec TPI)", d["tva_attendue_mad"], TVA_ATTENDUE, MAD)
    v.egal("écart de TVA toléré (5 %)", d["tva_ecart_tolere_mad"], TVA_ATTENDUE * 0.05, MAD)
    v.egal(
        "droits attendus (2,5 % de la valeur douane)", d["droits_attendus_mad"], DOUANE * 0.025, MAD
    )
    v.egal("droits : pas d'écart (rendu nul)", d["droits_ecart_mad"], None)
    e = d["ecart_facture"] or {}
    v.egal("écart de facture (USD)", e.get("ecart"), 720.0, MAD)
    v.egal("écart de facture (part)", e.get("part"), 720 / 7670, 1e-9)
    v.egal("écart de facture hors tolérance", e.get("hors_tolerance"), True)
    lignes = {x["lot"]: x for x in d["lignes"]}
    for lot, (kg, _usd) in LIGNES.items():
        x = lignes[lot]
        v.egal(f"{lot} : valeur", x["valeur_mad"], VALEUR[lot], MAD)
        v.egal(f"{lot} : part de valeur", x["part"], VALEUR[lot] / MARCHANDISE, 1e-9)
        v.egal(f"{lot} : frais répartis", x["charges_mad"], CHARGES[lot], MAD)
        v.egal(
            f"{lot} : transport au poids",
            x["frais_par_poste"].get("ROUTE"),
            FRAIS["ROUTE"] * kg / POIDS,
            MAD,
        )
        v.egal(f"{lot} : TVA répartie", x["tva_mad"], FRAIS["TVA"] * VALEUR[lot] / MARCHANDISE, MAD)
        v.egal(f"{lot} : coût de revient", x["revient_mad"], REVIENT[lot], MAD)
        v.egal(f"{lot} : coût au kilo (millionième)", x["revient_kg"], REVIENT_KG[lot], 1e-6)
        v.egal(
            f"{lot} : valeur douane",
            x["valeur_douane_mad"],
            VALEUR[lot] + FRAIS["FRET"] * VALEUR[lot] / MARCHANDISE,
            MAD,
        )
    v.vrai(
        "alerte de clôture : la facture",
        any("facture" in x.lower() for x in d["alertes"]),
        f": {d['alertes']}",
    )
    m.noter(
        "Coût de revient au kilo (dossier USD) : "
        + ", ".join(f"{lot} {REVIENT_KG[lot]:.6f} MAD/kg" for lot in LIGNES)
    )


def _verifier_cmup(m: Monde) -> None:
    """Le coût moyen prend le coût de revient du dossier (et non plus prix × cours du bon)."""
    v = m.verif
    valo = valorisation(m)
    v.egal("M1 : coût moyen = revient des deux lots", valo["scn"]["M1"]["cmup_mad"], CMUP_M1, 1e-6)
    v.egal("M2 : coût moyen = revient du lot", valo["scn"]["M2"]["cmup_mad"], CMUP_M2, 1e-6)
    v.egal("M1 : valeur", valo["scn"]["M1"]["valeur_mad"], CMUP_M1 * 1490, MAD)
    v.egal(
        "valeur de l'usine : + frais hors TVA et cours de la banque",
        valo["total_mad"],
        m.avant["valo_19"]["total_mad"] + 118800 + sum(REVIENT.values()),
        MAD,
    )
    lot = m.A.get(f"/lots/{m.ids['lot_1101']}")
    v.vrai("lot IST-1101 : réception citée", lot["reception"] is not None)
