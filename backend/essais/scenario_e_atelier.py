"""Étapes 10 à 13 et 17 du scénario : l'atelier au téléphone (alimentation des machines).

Calculs à la main (perte 2 %, recettes à 100 %, CALCULS B § 1.3 et § 7) :
- OF1 (23 novembre) : Q1 300 m² + Q2 200 m² → prévu M1 (1,2 × 300 + 1,0 × 200) × 1,02 = 571,2 ;
  M2 (0,3 × 300 + 0,3 × 200) × 1,02 = 153 ; M3 (0,5 × 300 + 0,4 × 200) × 1,02 = 234,6 ;
  total 958,8 kg. Sorti : M1 116 bobines du lot IST-1101 (4,95 kg) = 574,2 ; M2 153 kg ;
  M3 0,6 palette du lot interne (100 bobines de 4 kg) = 240 kg ; net 967,2 ; écart + 8,4 kg.
- Montage (23 novembre, après l'OF1) : 0,3 m × 300 bobines/m × 100 % = 90 bobines × 4,95 kg
  (poids du dernier lot sorti) = 445,5 kg sur le métier, sans aucun mouvement.
- Retour de l'OF1 (24 novembre) : 10 bobines de IST-1101 = 49,5 kg (motif R1) ; net 917,7 ;
  écart − 41,1 kg (− 4,2866 %) ; il rentre au coût moyen (stock non vide).
- OF2 (24 novembre) : Q2 100 m² → prévu M1 102, M2 30,6, M3 40,8 ; sorti M1 20 bobines de
  IST-1102 (5 kg) = 100 kg, M3 10 bobines = 40 kg ; retour 2 bobines (10 kg) ; annulé le 27 :
  stock et coût moyen de M1 reviennent à ceux d'avant l'OF2.
"""

from __future__ import annotations

from typing import Any

from scenario_e_achats import numero_suivant
from scenario_e_import import CMUP_M1, CMUP_M2
from scenario_e_reception import photo, valorisation
from scenario_monde import Monde
from scenario_outils import KG, MAD, montants_visibles

PREVU_OF1 = {"M1": 571.2, "M2": 153.0, "M3": 234.6}
SORTI_OF1 = {"M1": 574.2, "M2": 153.0, "M3": 240.0}
MONTAGE_KG = 0.3 * 300 * 4.95  # 445,5 kg


def motif(m: Monde, libelle: str) -> int:
    """L'identifiant d'un motif d'opération par son libellé."""
    return int(next(x["id"] for x in m.L.get("/motifs")["motifs"] if x["libelle"] == libelle))


def _ordre(
    m: Monde,
    jour: str,
    qualites: dict[str, float],
    lignes: list[tuple[str, str, float, str]],
    magasin: int | None = None,
) -> Any:
    corps = {
        "date": jour,
        "magasin_id": magasin or m.ids["mag_courant"],
        "metier_id": m.ids["metier"],
        "qualites": [{"qualite_id": m.ids[q], "m2": x} for q, x in qualites.items()],
        "lignes": [
            {"lot_id": m.ids[lot], "quantite": q, "unite": u, "matiere_id": m.ids[cle]}
            for cle, lot, q, u in lignes
        ],
    }
    return m.L.appeler("POST", "/ordres", corps)


def _proposition(m: Monde, jour: str) -> None:
    """La proposition FIFO de l'OF1 : prévu perte comprise, premier lot entré."""
    v, atl = m.verif, m.L
    demande = {
        "date": jour,
        "magasin_id": m.ids["mag_courant"],
        "metier_id": m.ids["metier"],
        "qualites": [
            {"qualite_id": m.ids["Q1"], "m2": 300},
            {"qualite_id": m.ids["Q2"], "m2": 200},
        ],
    }
    p = atl.post("/ordres/proposition", demande)
    v.egal("proposition : taux de perte", p["taux_perte"], 0.02, 1e-9)
    v.egal("proposition : prévu (perte comprise)", p["prevu"], 958.8, KG)
    v.egal("proposition : rien ne manque", p["manque"], 0.0, KG)
    par = {x["matiere_id"]: x for x in p["lignes"]}
    for cle, prevu in PREVU_OF1.items():
        x = par[m.ids[cle]]
        v.egal(f"{cle} : prévu", x["prevu"], prevu, KG)
    v.egal(
        "M1 : FIFO, le premier lot entré (IST-1101)",
        par[m.ids["M1"]]["lots"][0]["lot_id"],
        m.ids["lot_1101"],
    )
    v.egal("M1 : poids de bobine du lot", par[m.ids["M1"]]["lots"][0]["poids_bobine"], 4.95, 1e-9)


def _sortie_valorisee(m: Monde) -> None:
    """La sortie part au coût moyen, qui ne bouge pas."""
    v = m.verif
    valo, avant = valorisation(m), m.avant["valo_23"]
    for cle, cmup in (("M1", CMUP_M1), ("M2", CMUP_M2), ("M3", 19.8)):
        x = valo["scn"][cle]
        reste = avant["scn"][cle]["stock"] - SORTI_OF1[cle]
        v.egal(f"{cle} : stock après la sortie", x["stock"], reste, KG)
        v.egal(f"{cle} : coût moyen inchangé par la sortie", x["cmup_mad"], cmup, 1e-6)
        v.egal(
            f"{cle} : sortie au coût moyen",
            avant["scn"][cle]["valeur_mad"] - x["valeur_mad"],
            SORTI_OF1[cle] * cmup,
            MAD,
        )


def etape_sortie(m: Monde) -> None:
    """Étape 11 (23 novembre, alimentation) : proposition FIFO, OF de deux qualités, validé."""
    v, atl = m.verif, m.L
    jour = m.jour("ordres").isoformat()
    m.avant["valo_23"] = valorisation(m)
    _proposition(m, jour)
    existants = atl.get("/ordres")
    r = _ordre(
        m,
        jour,
        {"Q1": 300, "Q2": 200},
        [
            ("M1", "lot_1101", 116, "bobine"),
            ("M2", "lot_2201", 153, "kg"),
            ("M3", "lot_m3", 0.6, "palette"),
        ],
    )
    v.egal("OF1 : brouillon créé", r.statut, 201)
    o = r.corps
    m.ids["OF1"] = o["id"]
    v.egal("OF1 : net = total des lignes", o["net"], sum(SORTI_OF1.values()), KG)
    o = atl.post(f"/ordres/{o['id']}/valider", {"version": o["version"]})
    attendu = numero_suivant(m, "OF", existants)
    v.vrai("OF1 : numéroté après le dernier", (o["numero"] or "") >= attendu, f"({o['numero']})")
    v.egal("OF1 : validé", o["statut"], "valide")
    v.egal("OF1 : prévu figé", o["prevu"], 958.8, KG)
    v.egal("OF1 : écart", o["ecart"], 967.2 - 958.8, KG)
    v.egal("OF1 : écart relatif", o["ecart_relatif"], 8.4 / 958.8, 1e-9)
    v.egal("OF1 : m²", o["m2"], 500.0, 1e-9)
    pm = {x["matiere_id"]: x for x in o["par_matiere"]}
    for cle, sorti in SORTI_OF1.items():
        v.egal(f"OF1 {cle} : sorti", pm[m.ids[cle]]["quantite"], sorti, KG)
        v.egal(f"OF1 {cle} : prévu", pm[m.ids[cle]]["prevu"], PREVU_OF1[cle], KG)
    _sortie_valorisee(m)
    photo(m, "of1")
    m.avant["faits"]["of1_numero"] = o["numero"]
    vue = atl.get(f"/ordres/{o['id']}")
    v.egal("OF1 : aucun montant pour l'alimentation", montants_visibles(vue), [])


def etape_montage(m: Monde) -> None:
    """Étape 10 (23 novembre, après l'OF1, alimentation) : un fil monté sur le métier."""
    v, atl = m.verif, m.L
    m.horloge.aller(m.horloge.jour or m.jour("montage"), 10)
    mm = next(x for x in atl.get("/montage/matieres") if x["matiere_id"] == m.ids["M1"])
    v.egal("M1 : poids de bobine retenu (dernier lot sorti)", mm["poids_bobine_compte"], 4.95, 1e-9)
    v.egal("M1 : sorti en 30 jours", mm["sorti_30_j"], 574.2, KG)
    metier = atl.get(f"/metiers/{m.ids['metier']}")
    etage = metier["etages_detail"][0]
    corps = {
        "version": etage["version"],
        "confirme_effet_kg": 999,
        "fils": [{"matiere_id": m.ids["M1"], "metres": 0.3, "pourcentage": 100}],
    }
    r = atl.appeler("PUT", f"/metiers/{m.ids['metier']}/etages/1", corps)
    v.refus("effet annoncé faux : refusé", r, 409, "effet_change")
    mouvements = m.D.get(f"/mouvements?matiere={m.ids['M1']}&limite=5000")["total"]
    res = atl.put(f"/metiers/{m.ids['metier']}/etages/1", corps | {"confirme_effet_kg": MONTAGE_KG})
    v.egal("montage : effet", res["effet_kg"], MONTAGE_KG, KG)
    v.egal("montage : sur le métier", res["metier"]["sur_les_metiers"], MONTAGE_KG, KG)
    v.egal("montage : aucune alerte (445,5 ≤ 1,1 × 574,2 + 1)", res["alertes"], [])
    v.egal(
        "montage : aucun mouvement écrit",
        m.D.get(f"/mouvements?matiere={m.ids['M1']}&limite=5000")["total"],
        mouvements,
    )
    lu = atl.get(f"/stock/{m.ids['M1']}")["ligne"]
    v.egal("M1 : stock en machine", lu["stock_machine"], MONTAGE_KG, KG)
    v.egal(
        "M1 : disponible = magasin + machine", lu["stock_disponible"], 1490 - 574.2 + MONTAGE_KG, KG
    )
    v.egal("M1 : valeur machine masquée", lu.get("valeur_machine_mad"), None)
    valo = valorisation(m)["scn"]["M1"]
    v.egal("M1 : valeur sur le métier", valo["valeur_machine_mad"], MONTAGE_KG * CMUP_M1, MAD)
    v.egal("M1 : stock valorisé magasin + machine", valo["stock"], 915.8 + MONTAGE_KG, KG)
    photo(m, "montage")


def etape_retour_machine(m: Monde) -> None:
    """Étape 12 (24 novembre, alimentation) : reliquat de l'OF1 rendu en bobines."""
    v, atl = m.verif, m.L
    jour = m.jour("retour_machine").isoformat()
    corps = {
        "type": "retour_machine",
        "date": jour,
        "ordre_id": m.ids["OF1"],
        "motif_id": motif(m, "Reliquat de fin d'ordre"),
        "valider": True,
        "lignes": [
            {
                "matiere_id": m.ids["M1"],
                "lot_id": m.ids["lot_1101"],
                "magasin_id": m.ids["mag_courant"],
                "quantite": 10,
                "unite": "bobine",
            }
        ],
    }
    op = atl.ok("POST", "/operations", corps, attendu=201)
    v.egal("retour : 10 bobines × 4,95 kg", op["total"], 49.5, KG)
    v.egal("retour : motif R1", op["code_motif"], "R1")
    v.vrai("retour : numéroté", bool(op["numero"]))
    o = atl.get(f"/ordres/{m.ids['OF1']}")
    v.egal("OF1 : revenu", o["revenu"], 49.5, KG)
    v.egal("OF1 : net", o["net"], 917.7, KG)
    v.egal("OF1 : écart", o["ecart"], 917.7 - 958.8, KG)
    v.egal("OF1 : écart en %", o["ecart_relatif"], (917.7 - 958.8) / 958.8, 1e-9)
    v.egal(
        "M1 : coût moyen inchangé (retour au coût moyen)",
        valorisation(m)["scn"]["M1"]["cmup_mad"],
        CMUP_M1,
        1e-6,
    )
    m.avant["valo_avant_of2"] = valorisation(m)
    _of2(m, jour)


def _of2(m: Monde, jour: str) -> None:
    """L'OF2 du même jour et son retour (il sera annulé le 27)."""
    v, atl = m.verif, m.L
    r = _ordre(
        m, jour, {"Q2": 100}, [("M1", "lot_1102", 20, "bobine"), ("M3", "lot_m3", 10, "bobine")]
    )
    o = atl.post(f"/ordres/{r.corps['id']}/valider", {"version": r.corps["version"]})
    m.ids["OF2"] = o["id"]
    v.egal("OF2 : prévu (Q2 100 m²)", o["prevu"], 102 + 30.6 + 40.8, KG)
    v.egal("OF2 : net", o["net"], 140.0, KG)
    corps = {
        "type": "retour_machine",
        "date": jour,
        "ordre_id": o["id"],
        "motif_id": motif(m, "Changement de série / arrêt machine"),
        "valider": True,
        "lignes": [
            {
                "matiere_id": m.ids["M1"],
                "lot_id": m.ids["lot_1102"],
                "magasin_id": m.ids["mag_courant"],
                "quantite": 2,
                "unite": "bobine",
            }
        ],
    }
    atl.ok("POST", "/operations", corps, attendu=201)
    v.egal("OF2 : net après retour", atl.get(f"/ordres/{o['id']}")["net"], 130.0, KG)
    photo(m, "of2")


def etape_refus_atelier(m: Monde) -> None:
    """Étape 13 (24 novembre, alimentation) : sortie depuis la quarantaine, puis antidatée."""
    v, atl = m.verif, m.L
    jour = m.horloge.jour.isoformat() if m.horloge.jour else "2026-11-24"
    corps = {
        "type": "transfert",
        "date": jour,
        "motif_id": motif(m, "Mise en quarantaine"),
        "commentaire": "Bobines humides au toucher.",
        "valider": True,
        "lignes": [
            {
                "matiere_id": m.ids["M2"],
                "lot_id": m.ids["lot_2201"],
                "magasin_id": m.ids["mag_courant"],
                "magasin_destination_id": m.ids["mag_quarantaine"],
                "quantite": 50,
            }
        ],
    }
    op = atl.ok("POST", "/operations", corps, attendu=201)
    v.egal("l'alimentation met en quarantaine", op["mise_en_quarantaine"], True)
    demande = {
        "date": jour,
        "magasin_id": m.ids["mag_quarantaine"],
        "qualites": [{"qualite_id": m.ids["Q1"], "m2": 10}],
    }
    v.refus(
        "proposition depuis la quarantaine",
        atl.appeler("POST", "/ordres/proposition", demande),
        422,
        None,
        "quarantaine",
    )
    r = _ordre(m, jour, {"Q1": 10}, [("M2", "lot_2201", 5, "kg")], magasin=m.ids["mag_quarantaine"])
    v.refus("ordre depuis la quarantaine", r, 422, None, "quarantaine")
    r = _ordre(m, "2026-11-18", {"Q1": 10}, [("M1", "lot_1101", 2, "bobine")])
    v.egal("ordre antidaté : le brouillon s'enregistre", r.statut, 201)
    brouillon = r.corps
    v.vrai(
        "ordre antidaté : le brouillon annonce le refus",
        bool(brouillon["blocages"]),
        f": {brouillon['blocages']}",
    )
    r = atl.appeler("POST", f"/ordres/{brouillon['id']}/valider", {"version": brouillon["version"]})
    m.avant["faits"]["antidate"] = r.statut
    v.egal("ordre daté avant l'entrée du lot : refusé", r.statut, 409)
    v.vrai("refus clair : il cite le lot", "IST-1101" in r.detail, f": « {r.detail} »")
    atl.ok("DELETE", f"/ordres/{brouillon['id']}?version={brouillon['version']}")
    lu = m.A.get(f"/stock/{m.ids['M2']}")["ligne"]
    v.egal("M2 : 50 kg en quarantaine", lu["stock_quarantaine"], 50.0, KG)
    photo(m, "quarantaine")


def etape_annulation_ordre(m: Monde) -> None:
    """Étape 17 (27 novembre, alimentation) : l'OF2 et son retour annulés ensemble."""
    v, atl = m.verif, m.L
    m.jour("annulation_ordre")
    o = atl.get(f"/ordres/{m.ids['OF2']}")
    o = atl.post(f"/ordres/{o['id']}/annuler", {"version": o["version"], "motif": "série arrêtée"})
    v.egal("OF2 : annulé", o["statut"], "annule")
    v.egal("OF2 : numéro gardé", bool(o["numero"]), True)
    v.egal("OF2 : net nul", o["net"], 0.0, KG)
    avant, apres = m.avant["valo_avant_of2"]["scn"]["M1"], valorisation(m)["scn"]["M1"]
    v.egal("M1 : stock d'avant l'OF2", apres["stock"], avant["stock"], KG)
    v.egal("M1 : coût moyen d'avant l'OF2", apres["cmup_mad"], avant["cmup_mad"], 1e-6)
    v.egal("M1 : valeur d'avant l'OF2", apres["valeur_mad"], avant["valeur_mad"], MAD)
    lot = atl.get(f"/lots/{m.ids['lot_1102']}")
    v.egal("IST-1102 : entier de nouveau", lot["quantite"], 500.0, KG)
    photo(m, "annulation")
    retours = [
        x
        for x in m.D.get("/operations?type=retour_machine")["elements"]
        if x.get("ordre_id") == m.ids["OF2"]
    ]
    v.egal("le retour de l'OF2 est annulé avec lui", [x["statut"] for x in retours], ["annulee"])
