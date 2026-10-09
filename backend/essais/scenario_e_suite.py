"""Étapes 14, 15, 16 et 18 du scénario : retour au fournisseur, réclamation, inventaire,
règlements.

Calculs à la main :
- Retour au fournisseur (25 novembre) : 75 bobines du lot interne de M3 = 300 kg, au coût
  d'entrée du lot 1,8 × 11 = 19,80 MAD/kg → 5 940 MAD sortis ; le bon EUR reçu net 6 000 − 300
  = 5 700 < 98 % de 6 000 : il se rouvre ; taux de retours du fournisseur 300 / (990 + 500
  + 1 000 + 6 000) = 300 / 8 490.
- Inventaire de M2 au magasin courant (26 novembre) : théorique 1 000 − 153 (OF1) − 50
  (quarantaine) = 797 kg ; premier compte 770 (− 3,39 % : à recompter), second 780 ; écart
  − 17 kg × coût moyen de M2 ; ajustement − 17 kg.
- Réclamation : le lot IST-1103 refusé mais facturé, 200 kg × 3 USD = 600 USD demandés,
  ouverte le 25, close le 30 par un avoir de 600 USD (5 jours).
- Règlements (30 novembre) : facture USD 8 390 USD réglée ; fret 4 200 réglé ; droits et TVA
  réglés le 19 ; transport routier (échéance 20 décembre) à payer ; transitaire sans date : à
  dater ; facture EUR (échéance 17 janvier) à payer.
"""

from __future__ import annotations

from typing import Any

from scenario_e_atelier import motif
from scenario_e_import import CMUP_M2
from scenario_e_reception import photo, valorisation
from scenario_monde import Monde
from scenario_outils import KG, MAD, RATIO


def etape_retour_fournisseur(m: Monde) -> None:
    """Étape 14 (25 novembre, achats) : une partie du lot interne repart chez le fournisseur."""
    v, a = m.verif, m.A
    jour = m.jour("retour_fournisseur").isoformat()
    avant = valorisation(m)["scn"]["M3"]
    corps = {
        "type": "retour_fournisseur",
        "date": jour,
        "motif_id": motif(m, "Bobines endommagées"),
        "commentaire": "Bobines écrasées au déchargement.",
        "valider": True,
        "lignes": [
            {
                "matiere_id": m.ids["M3"],
                "lot_id": m.ids["lot_m3"],
                "magasin_id": m.ids["mag_courant"],
                "quantite": 75,
                "unite": "bobine",
            }
        ],
    }
    v.refus(
        "l'alimentation ne renvoie pas au fournisseur",
        m.L.appeler("POST", "/operations", corps),
        403,
    )
    op = a.ok("POST", "/operations", corps, attendu=201)
    v.egal("retour : 75 bobines × 4 kg", op["total"], 300.0, KG)
    apres = valorisation(m)["scn"]["M3"]
    v.egal("M3 : stock", apres["stock"], avant["stock"] - 300, KG)
    v.egal(
        "M3 : valeur sortie au coût du lot", avant["valeur_mad"] - apres["valeur_mad"], 5940.0, MAD
    )
    v.egal("M3 : coût moyen inchangé", apres["cmup_mad"], 19.8, 1e-6)
    bon = a.get(f"/commandes/{m.ids['BC_EUR']}")
    v.egal("bon EUR : rouvert", bon["statut"], "confirmee")
    v.egal("bon EUR : reçu net", bon["recu"], 5700.0, KG)
    v.egal("bon EUR : reste dû", bon["reste_kg"], 300.0, KG)
    photo(m, "retour_fournisseur")
    m.avant["faits"]["bon_eur_rouvert"] = bon["statut"]
    perf = a.get("/fournisseurs/performance")
    f = next(x for x in perf["lignes"] if x.get("fournisseur_id") == m.ids["F1"])
    v.egal("fournisseur : taux de retours", f["taux_retours"], 300 / 8490, RATIO)
    v.egal("fournisseur : deux réceptions", f["receptions"], 2)
    v.egal("fournisseur : OTIF", f["otif"], 0.0, RATIO)
    v.egal("fournisseur : à l'heure", f["on_time"], 1.0, RATIO)
    v.egal("fournisseur : complet (1 sur 2)", f["in_full"], 0.5, RATIO)


def _ligne_inventaire(fiche: dict[str, Any], lot: int) -> dict[str, Any]:
    return dict(next(x for x in fiche["lignes"] if x["lot_id"] == lot))


def _sortie_suspendue(m: Monde, jour: str) -> None:
    """Pendant le comptage, un ordre qui prend M2 ne se valide pas (K2)."""
    v, atl = m.verif, m.L
    corps = {
        "date": jour,
        "magasin_id": m.ids["mag_courant"],
        "metier_id": m.ids["metier"],
        "qualites": [{"qualite_id": m.ids["Q1"], "m2": 10}],
        "lignes": [{"lot_id": m.ids["lot_2201"], "quantite": 5, "unite": "kg"}],
    }
    o = atl.ok("POST", "/ordres", corps, attendu=201)
    r = atl.appeler("POST", f"/ordres/{o['id']}/valider", {"version": o["version"]})
    v.refus("sortie de M2 suspendue pendant le comptage", r, 409, "inventaire_en_cours")
    atl.ok("DELETE", f"/ordres/{o['id']}?version={o['version']}")


def etape_inventaire(m: Monde) -> None:
    """Étape 16 (26 novembre, achats et direction) : comptage de M2, recompte, ajustement."""
    v, a, d = m.verif, m.A, m.D
    jour = m.jour("inventaire").isoformat()
    inv = a.ok(
        "POST",
        "/inventaires",
        {
            "date": jour,
            "magasin_id": m.ids["mag_courant"],
            "libelle": "Comptage de la chaîne",
            "criteres": {"matieres": [m.ids["M2"]]},
        },
        attendu=201,
    )
    m.ids["inventaire"] = inv["id"]
    v.vrai("inventaire numéroté", inv["numero"].startswith("INV-2026-"), f"({inv['numero']})")
    v.egal("une matière suspendue", inv["nb_matieres_suspendues"], 1)
    x = _ligne_inventaire(inv, m.ids["lot_2201"])
    v.egal("IST-2201 : théorique", x["theorique"], 797.0, KG)
    _sortie_suspendue(m, jour)
    inv = a.put(
        f"/inventaires/{inv['id']}/comptages",
        {
            "version": inv["version"],
            "lignes": [{"ligne_id": x["id"], "compte": 770, "justification": "bobines entamées"}],
        },
    )
    x = _ligne_inventaire(inv, m.ids["lot_2201"])
    v.egal("premier compte : écart", x["ecart"], -27.0, KG)
    v.egal("premier compte : à recompter (− 3,39 % > 2 %)", x["a_recompter"], True)
    inv = d.put(
        f"/inventaires/{inv['id']}/comptages",
        {
            "version": inv["version"],
            "lignes": [
                {
                    "ligne_id": x["id"],
                    "second_compte": 780,
                    "justification": "une bobine abîmée jetée sans saisie",
                }
            ],
        },
    )
    x = _ligne_inventaire(inv, m.ids["lot_2201"])
    v.egal("recompte : retenu", x["retenu"], 780.0, KG)
    v.egal("recompte : écart", x["ecart"], -17.0, KG)
    v.egal("recompte : écart en MAD", x["valeur_ecart_mad"], -17 * CMUP_M2, MAD)
    v.egal("inventaire : écart total", inv["ecart_total"], -17.0, KG)
    v.egal("inventaire : écart en MAD", inv["ecart_valeur_mad"], -17 * CMUP_M2, MAD)
    m.avant["faits"]["inventaire_ecart"] = (inv["ecart_total"], inv["ecart_valeur_mad"])
    inv = a.post(f"/inventaires/{inv['id']}/valider", {"version": inv["version"]})
    v.egal("inventaire validé", inv["statut"], "valide")
    valo = valorisation(m)["scn"]["M2"]
    v.egal("M2 : stock ajusté (780 + 50 en quarantaine)", valo["stock"], 830.0, KG)
    v.egal("M2 : valeur", valo["valeur_mad"], 830 * CMUP_M2, MAD)
    v.egal("M2 : coût moyen inchangé", valo["cmup_mad"], CMUP_M2, 1e-6)
    photo(m, "inventaire")


def etape_reclamation(m: Monde) -> None:
    """Étape 15 (ouverte le 25, close le 30 novembre, achats) : le lot refusé mais facturé."""
    v, a = m.verif, m.A
    m.jour("reglements")
    corps = {
        "fournisseur_id": m.ids["F1"],
        "reception_id": m.ids["REC_USD"],
        "motif": "documents",
        "description": "Lot IST-1103 refusé (taches d'huile) mais facturé sur INV-2611-118.",
        "quantite": 200,
        "montant_demande": 600,
        "devise": "USD",
        "ouverte_le": "2026-11-25",
    }
    v.refus("l'alimentation ne réclame pas", m.L.appeler("POST", "/reclamations", corps), 403)
    r = a.ok("POST", "/reclamations", corps, attendu=201)
    v.vrai("réclamation numérotée", r["numero"].startswith("RCL-2026-"), f"({r['numero']})")
    v.egal("réclamation ouverte", r["statut"], "ouverte")
    v.egal("réclamation : montant demandé", r["montant_demande"], 600.0, MAD)
    r = a.put(
        f"/reclamations/{r['id']}",
        {"version": r["version"], "reponse": "Avoir n° CN-2611 accordé par le fournisseur."},
    )
    r = a.post(
        f"/reclamations/{r['id']}/clore",
        {
            "version": r["version"],
            "issue": "avoir",
            "montant_obtenu": 600,
            "close_le": "2026-11-30",
        },
    )
    v.egal("réclamation close", r["statut"], "close")
    v.egal("issue : avoir", r["issue"], "avoir")
    v.egal("montant obtenu", r["montant_obtenu"], 600.0, MAD)
    v.egal("durée : 5 jours", r["jours"], 5)
    fiche = a.get(f"/receptions/{m.ids['REC_USD']}")
    v.egal("la réception cite sa réclamation", len(fiche["reclamations"]), 1)


def _echeancier(m: Monde) -> dict[str, Any]:
    """L'échéancier de novembre à janvier ; `scn` : les pièces du scénario, par (objet, id)."""
    ech = dict(m.A.get("/echeancier?du=2026-11-01&au=2027-01-31"))
    ech["scn"] = {
        (x["objet"], x["id"]): (cle, x)
        for cle in ("lignes", "reglees", "a_dater", "ecartees")
        for x in ech[cle]
        if x.get("dossier_id") == m.ids["dossier_usd"] or x.get("fournisseur_id") == m.ids["F1"]
    }
    return ech


def etape_reglements(m: Monde) -> None:
    """Étape 18 (30 novembre, achats) : la facture USD et les frais réglés ; l'échéancier."""
    v, a = m.verif, m.A
    frais = {x["poste"]: x for x in a.get(f"/dossiers/{m.ids['dossier_usd']}")["frais"]}
    fid = {k: x["id"] for k, x in frais.items()}
    avant = _echeancier(m)
    fusd, feur = ("facture", m.ids["facture_usd"]), ("facture", m.ids["facture_eur"])
    if not v.vrai("facture USD à l'échéancier", fusd in avant["scn"]):
        return
    x = avant["scn"][fusd][1]
    v.egal("facture USD : montant", x["montant"], 8390.0, MAD)
    v.egal("facture USD : au cours du jour (10,5)", x["montant_mad"], 8390 * 10.5, MAD)
    v.egal("facture USD : échéance", x["date"], "2027-01-17")
    v.egal("facture EUR : en dirhams", avant["scn"][feur][1]["montant_mad"], 118800.0, MAD)
    for poste, retard in (("DD", True), ("TVA", True), ("FRET", False), ("ROUTE", False)):
        v.egal(
            f"{poste} : échu avant règlement",
            avant["scn"][("frais", fid[poste])][1]["en_retard"],
            retard,
        )
    v.egal("transitaire sans date : à dater", avant["scn"][("frais", fid["TRANSIT"])][0], "a_dater")
    payer = [
        (fusd, "2026-11-30"),
        (("frais", fid["FRET"]), "2026-11-30"),
        (("frais", fid["DD"]), "2026-11-19"),
        (("frais", fid["TVA"]), "2026-11-19"),
    ]
    for (objet, ident), quand in payer:
        corps = {
            "genre": objet,
            "id": ident,
            "payee_le": quand,
            "version": avant["scn"][(objet, ident)][1]["version"],
        }
        if objet == "facture":
            v.refus(
                "l'alimentation ne règle rien",
                m.L.appeler("PUT", "/echeancier/paiement", corps),
                403,
            )
        r = a.put("/echeancier/paiement", corps)
        v.egal(f"{objet} {ident} : réglé", r.get("etat"), "reglee")
        v.egal(f"{objet} {ident} : réglé le", r.get("payee_le"), quand)
    apres = _echeancier(m)
    for cle in (fusd, ("frais", fid["FRET"]), ("frais", fid["DD"]), ("frais", fid["TVA"])):
        v.egal(f"{cle} : parmi les réglés", apres["scn"][cle][0], "reglees")
    for cle in (feur, ("frais", fid["ROUTE"])):
        v.egal(
            f"{cle} : à payer, pas en retard",
            (apres["scn"][cle][0], apres["scn"][cle][1]["en_retard"]),
            ("lignes", False),
        )
    v.egal("transitaire : toujours à dater", apres["scn"][("frais", fid["TRANSIT"])][0], "a_dater")
    v.egal(
        "échu de l'usine : − droits et TVA réglés",
        apres["echu_mad"],
        avant["echu_mad"] - 2060.85 - 16940.19,
        MAD,
    )
    v.egal("échéances échues : − 2", apres["echues"], avant["echues"] - 2)
