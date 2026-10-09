"""Étapes 19 à 22 du scénario : clôture de novembre, bilan et Cockpit, contrôles, sauvegarde et
restauration (1er décembre).

Bilan de novembre calculé à la main (l'année d'essai s'arrête le 2 octobre : tout novembre est
le scénario) ; C1, C2 = coûts moyens de M1, M2 après le dossier (étape 9) :
- entrées 990 + 500 + 1 000 + 6 000 = 8 490 kg, au coût de revient : 87 239,85 (dossier USD)
  + 6 000 × 19,80 = 206 039,85 MAD ;
- sorties nettes des retours (l'OF2 annulé ne compte pas) : M1 574,2 − 49,5 = 524,7 ; M2 153 ;
  M3 240 → consommation 524,7 C1 + 153 C2 + 240 × 19,8 ;
- autres : retour au fournisseur − 300 × 19,8 = − 5 940 ; inventaire − 17 × C2 ;
- magasins : début + entrées − consommation + autres = fin (kilos : + 8 490 − 917,7 − 300 − 17
  = + 7 255,3) ; métiers : + 445,5 kg, + 445,5 × C1 MAD.
- Plan de novembre de Q1, mois clos, au prorata des jours (CALCULS § 3.4, `m2_passe`) :
  2 000 du 2 novembre à la révision du 10, 3 000 ensuite, sur 30 jours ; réalisé 300 m².
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from scenario_e_atelier import motif
from scenario_e_import import CMUP_M1, CMUP_M2, REVIENT
from scenario_e_reception import photo, valorisation
from scenario_e_referentiels import IDS_LIGNE, cle_ligne
from scenario_monde import Monde
from scenario_outils import KG, MAD

ENTREES_MAD = sum(REVIENT.values()) + 6000 * 19.8
CONSOMMATION = 524.7 * CMUP_M1 + 153 * CMUP_M2 + 240 * 19.8
AUTRES = -300 * 19.8 - 17 * CMUP_M2
MACHINE_MAD = 445.5 * CMUP_M1


def etape_cloture(m: Monde) -> None:
    """Étape 19 (1er décembre, direction) : novembre clos ; ce qui le toucherait est refusé."""
    v, d, a = m.verif, m.D, m.A
    jour = m.jour("cloture").isoformat()
    m.avant["valo_30"] = valorisation(m, "2026-11-30")
    version = next(x["version"] for x in d.get("/parametres") if x["cle"] == "date_cloture")
    corps = {"date_cloture": "2026-11-30", "motif": "Clôture de novembre", "version": version}
    v.refus("les achats ne clôturent pas", a.appeler("PUT", "/periode-close", corps), 403)
    r = d.appeler("PUT", "/periode-close", corps)
    if r.statut == 409:
        v.refus(
            "brouillons datés de novembre ou avant : clôture refusée",
            r,
            409,
            None,
            "Des brouillons sont datés de la période à clore",
        )
        _supprimer_brouillons(m)
        r.corps = d.put("/periode-close", corps)
    p = r.corps
    v.egal("période close au 30 novembre", p["date_cloture"], "2026-11-30")
    v.egal("contexte : date de clôture", a.get("/contexte")["date_cloture"], "2026-11-30")
    op = {
        "type": "transfert",
        "date": "2026-11-30",
        "valider": True,
        "motif_id": motif(m, "Mise en quarantaine"),
        "commentaire": "Bobine à contrôler.",
        "lignes": [
            {
                "matiere_id": m.ids["M1"],
                "lot_id": m.ids["lot_1102"],
                "magasin_id": m.ids["mag_courant"],
                "magasin_destination_id": m.ids["mag_quarantaine"],
                "quantite": 1,
            }
        ],
    }
    v.refus(
        "écriture datée de novembre", a.appeler("POST", "/operations", op), 409, "periode_close"
    )
    _dossier_novembre(m)
    fiche = next(x for x in a.get("/devises") if x["code"] == "USD")
    a.put(
        "/devises/USD",
        {"nom": fiche["nom"], "cours": 10.6, "actif": True, "version": fiche["version"]},
    )
    op["date"], op["lignes"][0]["quantite"] = jour, 1
    a.ok("POST", "/operations", op, attendu=201)
    apres = valorisation(m, "2026-11-30")
    v.egal(
        "valorisation du 30 novembre figée (cours et geste de décembre)",
        apres["total_mad"],
        m.avant["valo_30"]["total_mad"],
        MAD,
    )


def _dossier_novembre(m: Monde) -> None:
    """La facture EUR (camion du 19) : son coût ne se touche plus une fois novembre clos."""
    v, a = m.verif, m.A
    dossier = a.appeler(
        "POST",
        "/dossiers",
        {
            "facture_id": m.ids["facture_eur"],
            "libelle": "Camion du 19 (EUR)",
            "date_arrivee": "2026-11-19",
        },
    )
    if dossier.statut == 201:
        m.noter("Dossier de la facture EUR ouvert après la clôture : frais et cours refusés.")
        did = dossier.corps["id"]
        frais = {
            "version": dossier.corps["version"],
            "poste_id": _poste(m, "TRANSIT"),
            "montant": 800,
        }
        r = a.appeler("POST", f"/dossiers/{did}/frais", frais)
        v.refus("frais sur une marchandise entrée en novembre", r, 409, "cout_periode_close")
        r = a.appeler(
            "PUT",
            f"/dossiers/{did}/cours",
            {"devise": "EUR", "cours": 11.4, "version": dossier.corps["version"]},
        )
        v.refus("cours d'une marchandise entrée en novembre", r, 409, "cout_periode_close")
    else:
        v.refus("dossier sur une facture de novembre", dossier, 409, "cout_periode_close")


def _supprimer_brouillons(m: Monde) -> None:
    """Les brouillons laissés par l'année d'essai sont supprimés par leur rôle."""
    b = m.D.get("/brouillons")
    for x in b["receptions"]:
        m.A.ok("DELETE", f"/receptions/{x['id']}?version={x['version']}")
        m.noter(f"Brouillon de réception {x['id']} de l'année d'essai supprimé avant la clôture.")
    for x in b["ordres"]:
        m.L.ok("DELETE", f"/ordres/{x['id']}?version={x['version']}")
        m.noter(f"Brouillon d'ordre {x['id']} de l'année d'essai supprimé avant la clôture.")
    for x in b["operations"]:
        m.D.ok("DELETE", f"/operations/{x['id']}?version={x['version']}")


def _poste(m: Monde, code: str) -> int:
    return int(next(x["id"] for x in m.A.get("/postes-frais") if x["code"] == code))


def _prorata_q1(m: Monde) -> float:
    """Le plan de Q1 en novembre : 0 jusqu'au plan de départ, 2 000 jusqu'à la révision, 3 000."""
    debut, fin = (
        datetime.fromisoformat("2026-11-01T00:00:00+00:00"),
        datetime.fromisoformat("2026-12-01T00:00:00+00:00"),
    )
    depart = datetime.fromisoformat(m.avant["plan_q1_depart"].replace("Z", "+00:00"))
    revision = datetime.fromisoformat(m.avant["revision_q1"].replace("Z", "+00:00"))
    duree = (fin - debut).total_seconds()
    return (
        2000 * (revision - depart).total_seconds() + 3000 * (fin - revision).total_seconds()
    ) / duree


def etape_bilan(m: Monde) -> None:
    """Étape 20 (1er décembre, direction) : bilan de novembre équilibré ; une valeur partout."""
    v, d = m.verif, m.D
    b = d.get("/bilan?mois=2026-11")
    v.egal("entrées (kg)", b["entrees_kg"], 8490.0, KG)
    v.egal("entrées au coût de revient", b["valeur_entrees_mad"], ENTREES_MAD, MAD)
    v.egal("consommation", b["consommation_mad"], CONSOMMATION, MAD)
    v.egal("autres (retour fournisseur, inventaire)", b["valeur_autres_mad"], AUTRES, MAD)
    v.egal("sorties nettes", b["sorties_nettes_kg"], 1107.2 - 59.5, KG)
    v.egal("annulations (OF2 et son retour)", b["annulations_kg"], 140 - 10, KG)
    v.egal("retours au fournisseur", b["retours_fournisseur_kg"], 300.0, KG)
    v.egal("ajustements", b["ajustements_kg"], -17.0, KG)
    v.egal(
        "magasins : variation en kg",
        b["stock_fin_magasins_kg"] - b["stock_debut_magasins_kg"],
        8490 - 917.7 - 300 - 17,
        KG,
    )
    v.egal(
        "magasins : équilibre en MAD",
        b["valeur_fin_magasins_mad"],
        b["valeur_debut_magasins_mad"] + ENTREES_MAD - CONSOMMATION + AUTRES,
        MAD,
    )
    v.egal("métiers : + 445,5 kg", b["variation_metiers_kg"], 445.5, KG)
    v.egal("métiers : valeur", b["variation_metiers_mad"], MACHINE_MAD, MAD)
    v.egal(
        "équilibre total",
        b["valeur_fin_mad"],
        b["valeur_debut_mad"] + ENTREES_MAD - CONSOMMATION + AUTRES + MACHINE_MAD,
        MAD,
    )
    v.egal("écart de valorisation", b["ecart_valorisation_mad"], 0.0, MAD)
    v.egal("m² par qualité", b["m2_par_qualite"], {"SCN-Q1": 300.0, "SCN-Q2": 200.0})
    v.egal("bons émis", b["commandes"], 2)
    v.egal("réceptions", b["receptions"], 2)
    v.egal("OTIF du mois", b["otif"], 0.0, 1e-9)
    v.egal("ordres", b["ordres"], 1)
    of1 = b["ecarts_ordres"][0]
    v.egal("écart de l'OF1", of1["ecart"], 917.7 - 958.8, KG)
    debut = valorisation(m, "2026-10-31")["total_mad"]
    v.egal("début du mois = Valorisation au 31 octobre", b["valeur_debut_mad"], debut, MAD)
    fin = valorisation(m, "2026-11-30")["total_mad"]
    photo(m, "fin_novembre", "2026-11-30")
    v.egal("fin du mois = Valorisation au 30 novembre", b["valeur_fin_mad"], fin, MAD)
    _une_valeur(m)
    realise = d.get("/production/realise?date=2026-11-30")
    clos = d.get("/production/realise")
    q1 = next(x for x in clos["lignes"] if x["qualite_id"] == m.ids["Q1"])
    v.egal("Q1 : réalisé de novembre", q1["realise"][-2], 300.0, 1e-6)
    v.egal("Q1 : plan de novembre au prorata des jours", q1["plan"][-2], _prorata_q1(m), 1e-3)
    q2 = next(x for x in realise["lignes"] if x["qualite_id"] == m.ids["Q2"])
    v.egal("Q2 : réalisé de novembre", q2["realise"][-1], 200.0, 1e-6)


def _une_valeur(m: Monde) -> None:
    """Valorisation = Cockpit = photo du jour = courriel du lundi (E-06)."""
    v, d = m.verif, m.D
    valeur = valorisation(m)["total_mad"]
    cockpit = d.get("/cockpit")
    v.egal("Cockpit = Valorisation", cockpit["stock"]["valeur_mad"], valeur, MAD)
    kpi = next(x for x in cockpit["kpi"] if x["cle"] == "valeur")
    v.egal("indicateur « valeur du stock »", kpi["valeur"], valeur, MAD)
    v.egal(
        "Cockpit : valeur sur les métiers",
        cockpit["stock"]["valeur_machine_mad"] >= MACHINE_MAD - MAD,
        True,
    )
    photo = d.post("/indicateurs/photographier")
    v.egal("photo du jour = Valorisation", photo["valeur_stock_mad"], valeur, MAD)
    texte = d.get("/courriel/apercu")["texte"]
    lu = re.search(r"Valeur du stock : ([\d\s  ]+) MAD", texte)
    chiffre = int(re.sub(r"\D", "", lu.group(1))) if lu else None
    v.egal("courriel du lundi = Valorisation (au dirham)", chiffre, round(valeur))
    v.refus("l'alimentation ne lit pas le Cockpit", m.L.appeler("GET", "/cockpit"), 403)


def _mes_lignes(c: dict[str, Any], cle: str, ident: int) -> int:
    return sum(1 for x in c["lignes"] if x.get(cle) == ident)


def etape_controles(m: Monde) -> None:
    """Étape 21 (direction) : aucune nouvelle anomalie bloquante ; C06, C08, C36 sonnent."""
    v, d = m.verif, m.D
    avant = m.avant["controles_0"]
    apres = {c["code"]: c for c in d.get("/controles")["controles"]}
    for code, c in apres.items():
        if c["gravite"] == "bloquant":
            v.egal(f"{code} (bloquant) : pas d'anomalie nouvelle", c["anomalies"], avant[code])
    v.egal(
        "C06 : le bon USD en retard (reste dû, promis le 25)",
        _mes_lignes(apres["C06"], "commande_id", m.ids["BC_USD"]),
        1,
    )
    v.egal(
        "C08 : l'écart de pesée de IST-1101",
        _mes_lignes(apres["C08"], "reception_id", m.ids["REC_USD"]),
        1,
    )
    v.egal(
        "C36 : la facture USD (+ 9,39 %)",
        _mes_lignes(apres["C36"], "dossier_id", m.ids["dossier_usd"]),
        1,
    )
    v.egal("C08 : une anomalie de plus", apres["C08"]["anomalies"], avant["C08"] + 1)
    v.egal("C36 : une anomalie de plus", apres["C36"]["anomalies"], avant["C36"] + 1)
    v.egal(
        "C19 : le fournisseur du scénario facture en USD et en EUR",
        _mes_lignes(apres["C19"], "fournisseur_id", m.ids["F1"]),
        1,
    )
    _nouvelles_expliquees(m, apres)


def _nouvelles_expliquees(m: Monde, apres: dict[str, Any]) -> None:
    """Toute ligne nouvelle d'un contrôle nomme une fiche du scénario, ou c'est un bon de
    l'année d'essai devenu en retard pendant le mois (sa date promise ou son ETA est passée)."""
    v, a = m.verif, m.A
    miens = {m.ids[k] for k in m.ids}
    for code, c in apres.items():
        avant = set(m.avant["controles_0_lignes"][code])
        nouvelles = [x for x in c["lignes"] if cle_ligne(x) not in avant]
        for x in nouvelles:
            if any(x.get(k) in miens for k in IDS_LIGNE if x.get(k) is not None):
                continue
            if code == "C06" and x.get("commande_id"):
                bon = a.get(f"/commandes/{x['commande_id']}")
                due = bon["expedition"]["eta"] or bon["date_livraison_prevue"] or ""
                v.vrai(
                    f"C06 : {bon['numero']} attendu pendant le mois ({due})",
                    "2026-11-01" <= due < "2026-12-01",
                )
                continue
            v.vrai(f"{code} : ligne nouvelle expliquée", False, f": {x}")
        if c["anomalies"] != m.avant["controles_0"][code]:
            m.noter(
                f"Contrôle {code} ({c['gravite']}) : {m.avant['controles_0'][code]} → "
                f"{c['anomalies']} ({len(nouvelles)} lignes nouvelles)"
            )


def etape_sauvegarde(m: Monde) -> None:
    """Étape 22 (administrateur) : sauvegarde, geste, restauration ; le geste a disparu."""
    v, t = m.verif, m.T
    v.refus("l'administrateur ne lit aucun bon", t.appeler("GET", "/commandes"), 403)
    etat = t.post("/sauvegardes")
    nom = etat["fichiers"][0]["nom"]
    v.vrai("sauvegarde relue (tables)", etat["fichiers"][0]["tables"] > 0)
    valeur = valorisation(m)["total_mad"]
    nb = m.D.get("/operations?limite=5000")["total"]
    fiche = next(x for x in m.A.get("/devises") if x["code"] == "EUR")
    m.A.put(
        "/devises/EUR",
        {"nom": fiche["nom"], "cours": 11.9, "actif": True, "version": fiche["version"]},
    )
    r = t.appeler(
        "POST",
        f"/sauvegardes/{nom}/restaurer",
        {"confirmation": "RESTAURER", "motif": "essai de restauration du scénario"},
    )
    v.egal("restauration acceptée", r.statut, 202)
    fin = time.monotonic() + 180
    etat_r = ""
    while time.monotonic() < fin:
        etat_r = str(t.get("/sante")["taches"].get("restauration", ""))
        if etat_r.startswith(("ok", "échec")):
            break
        time.sleep(0.5)
    v.egal("restauration terminée", etat_r, "ok")
    for role in ("D", "A", "L"):
        m.connecter(role)
    v.egal(
        "le cours d'après la sauvegarde a disparu",
        next(x for x in m.A.get("/devises") if x["code"] == "EUR")["cours"],
        11.0,
        1e-9,
    )
    v.egal("valeur du stock identique", valorisation(m)["total_mad"], valeur, MAD)
    v.egal("opérations identiques", m.D.get("/operations?limite=5000")["total"], nb)


def etape_verification(m: Monde) -> None:
    """Étape 22 : le vérificateur indépendant (lot V1) sur la base du scénario : 0 écart.

    Il lit la base en SQL et l'application par HTTP — ici le serveur du scénario, à son heure
    (1er décembre 2026), avec le compte de direction du scénario : il n'écrit rien."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    from scenario_monde import COMPTES

    script = Path(__file__).resolve().parent / "verification_chiffres.py"
    if not script.exists():
        m.noter("Étape 22 : verification_chiffres.py (lot V1) absent : vérification non jouée.")
        return
    identifiant, _nom, _role, code = COMPTES["D"]
    env = dict(os.environ) | {"GESTIONMPPRO_BASE": str(m.avant["base"])}
    r = subprocess.run(  # noqa: S603 — l'interpréteur des essais, un script du dépôt
        [
            sys.executable,
            str(script),
            "--serveur",
            m.adresse,
            "--identifiant",
            identifiant,
            "--code",
            code,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=1800,
        check=False,
    )
    total = next((x for x in r.stdout.splitlines() if x.startswith("Total")), r.stderr[-300:])
    m.noter(f"Vérificateur (V1) sur la base du scénario : {total}")
    m.avant["verification"] = r.stdout
    m.verif.egal("vérificateur indépendant : code de sortie (0 = aucun écart)", r.returncode, 0)
    lignes = r.stdout.splitlines()
    for i, ligne in enumerate(lignes):
        if ligne.startswith("✗"):
            detail = " / ".join(x.strip() for x in lignes[i + 1 : i + 4] if x.startswith(" "))
            m.verif.vrai("vérificateur : famille juste", False, f": {ligne} — {detail}")
