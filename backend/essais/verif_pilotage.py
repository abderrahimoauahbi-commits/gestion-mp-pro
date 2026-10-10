"""Pilotage : bilan du mois, Cockpit, plan d'achat (lot V1). Les contrôles : `verif_controles`.

- Bilan de chaque mois des 13 dates : kilos recomptés dans le journal (début, fin, entrées,
  sorties, retours, ajustements, ouvertures, annulations à part, réception annulée dans le
  mois nulle part) ; équation en kilos et en dirhams fermée ; valeurs de début et de fin =
  la Valorisation de la veille du mois et de la fin ; dirhams des flux = Σ du journal valorisé ;
  m², bons émis, réceptions, OTIF du mois (moyenne des réceptions notées du mois).
- Cockpit à chaque date : comptes des statuts de l'écran Stock (ruptures, critiques, urgents,
  attentions, OK ; alerte rouge = ruptures + critiques), bons actifs et leur reste, budget = Σ
  des montants à commander, dormants, ABC, sourcing, rotation et DIO, indicateurs (KPI).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

import verif_controles
from verif_socle import KG, MAD, RELATIF, Acces, Releve, fin_de_mois
from verif_valeur import journal_valorise

NOM_KG = "Bilan du mois : kilos recomptés, équation fermée"
NOM_MAD = "Bilan du mois : dirhams = Valorisation et journal valorisé, équation fermée"
NOM_ACT = "Bilan du mois : m², bons émis, réceptions, OTIF, ruptures"
NOM_COCKPIT = "Cockpit = écran Stock, Commandes, Valorisation (comptes, montants, ratios)"
STATUTS = {
    "ruptures": "RUPTURE",
    "critiques": "CRITIQUE",
    "urgents": "URGENT",
    "attentions": "ATTENTION",
    "ok": "OK",
}


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Bilans, Cockpit, plan d'achat, contrôles."""
    journal = journal_valorise(a)
    perf = a.get("/fournisseurs/performance")["receptions"]
    for d in dates:
        fin = min(fin_de_mois(d), dates[-1])
        _bilan(a, r, debut=d.replace(day=1), fin=fin, journal=journal, perf=perf)
        _cockpit(a, r, d, d == dates[-1])
    verif_controles.verifier(a, r, dates)


def _flux(a: Acces, debut: date, fin: date) -> tuple[dict[str, float], dict[str, float]]:
    """Kilos du mois par type (hors transferts), annulations à part, réceptions annulées dans
    le mois nulle part ; plus « debut » et « fin » (stock des magasins)."""
    flux: dict[str, float] = defaultdict(float)
    annulations: dict[str, float] = defaultdict(float)
    lignes = a.sql(
        "SELECT m.id, m.type, m.quantite, m.contrepasse_id, m.date_effet, "
        "(SELECT x.date_effet FROM mouvement x WHERE x.contrepasse_id = m.id) "
        "FROM mouvement m WHERE m.date_effet BETWEEN %s AND %s AND m.type <> 'TRANSFERT'",
        (debut, fin),
    )
    paires = {
        i
        for i, t, _, c, _, annule_le in lignes
        if t == "RECEPTION" and c is None and annule_le and debut <= annule_le <= fin
    }
    for i, t, q, c, _, _ in lignes:
        if i in paires or c in paires:
            continue
        (annulations if c is not None else flux)[t] += q
    (avant,) = a.sql(
        "SELECT COALESCE(SUM(quantite), 0) FROM mouvement WHERE date_effet < %s", (debut,)
    )[0]
    (apres,) = a.sql(
        "SELECT COALESCE(SUM(quantite), 0) FROM mouvement WHERE date_effet <= %s", (fin,)
    )[0]
    flux["debut"], flux["fin"] = avant, apres
    return flux, annulations


def _bilan(
    a: Acces,
    r: Releve,
    *,
    debut: date,
    fin: date,
    journal: list[dict[str, Any]],
    perf: list[dict[str, Any]],
) -> None:
    """Le bilan d'un mois, recompté."""
    b = a.get("/bilan", mois=debut.strftime("%Y-%m"))
    m = debut.strftime("%Y-%m")
    flux, annulations = _flux(a, debut, fin)
    attendus = {
        "stock_debut_magasins_kg": flux["debut"],
        "stock_fin_magasins_kg": flux["fin"],
        "entrees_kg": flux["RECEPTION"],
        "sorties_kg": -flux["SORTIE"],
        "retours_machine_kg": flux["RETOUR_MACHINE"],
        "retours_fournisseur_kg": -flux["RETOUR_FOURNISSEUR"],
        "ajustements_kg": flux["AJUSTEMENT"],
        "ouvertures_kg": flux["OUVERTURE"],
        "annulations_kg": sum(annulations.values()),
    }
    for champ, valeur in attendus.items():
        r.comparer(NOM_KG, f"{m} ({champ})", b[champ], valeur, KG)
    equation = (
        b["stock_debut_kg"]
        + b["entrees_kg"]
        + b["ouvertures_kg"]
        - b["sorties_kg"]
        + b["retours_machine_kg"]
        - b["retours_fournisseur_kg"]
        + b["ajustements_kg"]
        + b["annulations_kg"]
        + b["variation_metiers_kg"]
    )
    r.comparer(NOM_KG, f"{m} (équation)", b["stock_fin_kg"], equation, KG)
    r.comparer(
        NOM_KG,
        f"{m} (début = magasins + métiers)",
        b["stock_debut_kg"],
        b["stock_debut_magasins_kg"] + b["metiers_debut_kg"],
        KG,
    )
    r.comparer(
        NOM_KG,
        f"{m} (fin = magasins + métiers)",
        b["stock_fin_kg"],
        b["stock_fin_magasins_kg"] + b["metiers_fin_kg"],
        KG,
    )
    _bilan_mad(a, r, b, (debut, fin), journal)
    _bilan_activite(a, r, b, (debut, fin), perf)


def _bilan_mad(
    a: Acces, r: Releve, b: dict[str, Any], mois: tuple[date, date], journal: list[dict[str, Any]]
) -> None:
    """Les dirhams du bilan : valeurs de la Valorisation, flux du journal valorisé."""
    debut, fin = mois
    m = debut.strftime("%Y-%m")
    veille = a.get("/valorisation", date=(debut - timedelta(days=1)).isoformat())
    au_fin = a.get("/valorisation", date=fin.isoformat())
    r.comparer(
        NOM_MAD,
        f"{m} (valeur de début)",
        b["valeur_debut_magasins_mad"],
        sum(x["valeur_magasin_mad"] for x in veille["lignes"] if x["stock_magasin"] > 0),
    )
    r.comparer(
        NOM_MAD,
        f"{m} (valeur de fin)",
        b["valeur_fin_magasins_mad"],
        sum(x["valeur_magasin_mad"] for x in au_fin["lignes"] if x["stock_magasin"] > 0),
    )
    du, au = debut.isoformat(), fin.isoformat()
    du_mois = [x for x in journal if du <= x["date"] <= au and x["type"] != "TRANSFERT"]
    paires = {
        x["id"]
        for x in du_mois
        if x["type"] == "RECEPTION"
        and x["contrepasse_id"] is None
        and any(y["contrepasse_id"] == x["id"] for y in du_mois)
    }
    gardes = [x for x in du_mois if x["id"] not in paires and x["contrepasse_id"] not in paires]
    entrees = sum(
        x["valeur_mad"] or 0.0
        for x in gardes
        if x["type"] == "RECEPTION" and x["contrepasse_id"] is None
    )
    conso = -sum(
        x["valeur_mad"] or 0.0 for x in gardes if x["type"] in ("SORTIE", "RETOUR_MACHINE")
    )
    total = sum(x["valeur_mad"] or 0.0 for x in gardes)
    r.comparer(NOM_MAD, f"{m} (entrées)", b["valeur_entrees_mad"], entrees)
    r.comparer(NOM_MAD, f"{m} (consommation)", b["consommation_mad"], conso)
    r.comparer(NOM_MAD, f"{m} (autres mouvements)", b["valeur_autres_mad"], total - entrees + conso)
    equation = (
        b["valeur_debut_mad"]
        + b["valeur_entrees_mad"]
        - b["consommation_mad"]
        + b["valeur_autres_mad"]
        + b["variation_metiers_mad"]
    )
    r.comparer(NOM_MAD, f"{m} (équation sans reste)", b["valeur_fin_mad"], equation, 1.0)
    r.comparer(
        NOM_MAD,
        f"{m} (variation sur les métiers)",
        b["variation_metiers_mad"],
        b["metiers_fin_mad"] - b["metiers_debut_mad"],
        MAD,
    )


def _bilan_activite(
    a: Acces, r: Releve, b: dict[str, Any], mois: tuple[date, date], perf: list[dict[str, Any]]
) -> None:
    """m² fabriqués, bons émis, réceptions validées, OTIF du mois ; ruptures et critiques au
    soir du dernier jour = l'écran Stock à cette date."""
    debut, fin = mois
    m = debut.strftime("%Y-%m")
    (m2,) = a.sql(
        "SELECT COALESCE(SUM(q.m2), 0) FROM ordre_qualite q JOIN ordre o ON o.id = "
        "q.ordre_id WHERE o.statut = 'valide' AND o.date BETWEEN %s AND %s",
        (debut, fin),
    )[0]
    (bons,) = a.sql(
        "SELECT count(*) FROM commande WHERE numero IS NOT NULL AND statut <> "
        "'annulee' AND date_commande BETWEEN %s AND %s",
        (debut, fin),
    )[0]
    (recues,) = a.sql(
        "SELECT count(*) FROM reception WHERE statut = 'validee' AND date BETWEEN %s AND %s",
        (debut, fin),
    )[0]
    notes = [
        x["otif"]
        for x in perf
        if x["date_reception"]
        and debut.isoformat() <= x["date_reception"] <= fin.isoformat()
        and x["otif"] is not None
    ]
    r.comparer(NOM_ACT, f"{m} (m²)", b["m2_total"], m2, KG)
    r.juger(NOM_ACT, f"{m} (bons émis)", b["commandes"] == bons, f"écran {b['commandes']}, {bons}")
    r.juger(
        NOM_ACT,
        f"{m} (réceptions)",
        b["receptions"] == recues,
        f"écran {b['receptions']}, recompté {recues}",
    )
    r.juger(NOM_ACT, f"{m} (réceptions notées)", b["receptions_notees"] == len(notes))
    statuts = [x["statut"] or "" for x in a.get("/stock", date=fin.isoformat())["lignes"]]
    for champ, mot in (("ruptures", "RUPTURE"), ("critiques", "CRITIQUE")):
        n = sum(mot in x for x in statuts)
        r.juger(
            NOM_ACT,
            f"{m} ({champ} au soir du {fin})",
            b[champ] == n,
            f"écran {b[champ]}, écran Stock {n}",
        )
    otif = sum(notes) / len(notes) if notes else None
    r.juger(
        NOM_ACT,
        f"{m} (OTIF)",
        (b["otif"] is None) == (otif is None) and abs((b["otif"] or 0) - (otif or 0)) <= RELATIF,
        f"écran {b['otif']}, {otif}",
    )


def _cockpit(a: Acces, r: Releve, d: date, du_jour: bool) -> None:
    """Le Cockpit d'une date contre les écrans Stock, Commandes et Valorisation."""
    c = a.get("/cockpit", date=d.isoformat())
    lignes = a.get("/stock", date=d.isoformat())["lignes"]
    valo = {x["matiere_id"]: x for x in a.get("/valorisation", date=d.isoformat())["lignes"]}
    taux = {code: float(t) for code, t in a.sql("SELECT code, cours FROM devise")}
    s = f"au {d}"
    for champ, mot in STATUTS.items():
        n = sum(1 for x in lignes if mot in (x["statut"] or ""))
        r.juger(
            NOM_COCKPIT,
            f"{champ} {s}",
            c["stock"][champ] == n,
            f"écran {c['stock'][champ]}, recompté {n}",
        )
    rouge = c["stock"]["ruptures"] + c["stock"]["critiques"]
    r.juger(NOM_COCKPIT, f"alerte rouge {s}", c["alerte_rouge"] == rouge)
    r.juger(NOM_COCKPIT, f"références {s}", c["stock"]["nb_references"] == len(lignes))
    r.comparer(
        NOM_COCKPIT,
        f"budget à commander {s}",
        c["achats"]["budget_a_commander_mad"],
        sum(x["montant_a_commander_mad"] or 0.0 for x in lignes),
    )
    dormants = [x for x in lignes if x["dormant"]]
    r.juger(NOM_COCKPIT, f"dormants {s}", c["dormant"]["nb_references"] == len(dormants))
    valeur = sum(valo[x["matiere_id"]]["valeur_mad"] for x in dormants if x["matiere_id"] in valo)
    r.comparer(NOM_COCKPIT, f"valeur dormante {s}", c["dormant"]["valeur_mad"], valeur)
    abc = Counter(x["classe_abc"] for x in lignes if x["classe_abc"])
    r.juger(
        NOM_COCKPIT,
        f"ABC {s}",
        {k: v for k, v in c["abc"].items() if v} == dict(abc),
        f"écran {c['abc']}, recompté {dict(abc)}",
    )
    f = c["finance"]
    # Rotation : le stock au coût moyen face à la consommation réelle ; sans historique, le
    # stock au catalogue face au coût matière du plan (CALCULS B § 3.2).
    stock_rotation = (
        c["stock"]["valeur_mad"]
        if f["base_rotation"] == "consommation"
        else sum(
            x["stock"] * x["prix_catalogue"] * taux.get(x["devise"], 1.0)
            for x in valo.values()
            if x["stock"] > 0
        )
    )
    if f["cout_rotation_annuel_mad"] and stock_rotation:
        r.comparer(
            NOM_COCKPIT,
            f"rotation {s}",
            f["rotation_stock"],
            f["cout_rotation_annuel_mad"] / stock_rotation,
            RELATIF,
        )
        r.comparer(
            NOM_COCKPIT,
            f"DIO {s}",
            f["dio_jours"],
            stock_rotation / f["cout_rotation_annuel_mad"] * 365,
            RELATIF,
        )
    if du_jour:
        _cockpit_achats(a, r, c, s)
    kpi = {k["cle"]: k["valeur"] for k in c["kpi"]}
    for cle, valeur in (
        ("valeur", c["stock"]["valeur_mad"]),
        ("rotation", f["rotation_stock"]),
        ("a_commander", c["achats"]["budget_a_commander_mad"]),
    ):
        r.comparer(NOM_COCKPIT, f"indicateur « {cle} » {s}", kpi.get(cle), valeur)


def _cockpit_achats(a: Acces, r: Releve, c: dict[str, Any], s: str) -> None:
    """Bons actifs et leur reste (aujourd'hui : l'écran Commandes n'a pas de date). Le reste
    d'une ligne = commandé − reçu accepté : ce qui attend en quarantaine reste attendu (R11r,
    D-02) ; rien sous la tolérance de livraison ; au prix confirmé, sinon estimé ; au cours
    figé du bon, sinon du jour."""
    reglages = dict(a.sql("SELECT cle, valeur FROM parametre"))
    tolerance = float(reglages.get("toler_in_full", 0.02))
    taux = {code: float(t) for code, t in a.sql("SELECT code, cours FROM devise")}
    actifs, montant = 0, 0.0
    for bon in a.get("/commandes")["elements"]:
        if not bon["parti"] or bon["statut"] in ("soldee", "annulee"):
            continue
        cours = bon["cours"] or (1.0 if bon["devise"] == "MAD" else taux.get(bon["devise"], 1.0))
        restes = []
        for x in a.get(f"/commandes/{bon['id']}")["lignes"]:
            reste = x["quantite"] - max(0.0, x["recu"] - max(0.0, x["en_quarantaine"]))
            reste = reste if reste > x["quantite"] * tolerance else 0.0
            restes.append(reste)
            montant += reste * (x["prix"] if x["prix_confirme"] else x["prix_estime"]) * cours
        actifs += any(reste > 0 for reste in restes)
    r.juger(
        NOM_COCKPIT,
        f"bons actifs {s}",
        c["achats"]["bc_actifs"] == actifs,
        f"écran {c['achats']['bc_actifs']}, recompté {actifs}",
    )
    r.comparer(
        NOM_COCKPIT, f"reste des bons actifs {s}", c["achats"]["montant_bc_en_cours_mad"], montant
    )
