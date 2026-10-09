"""Réceptions, factures, inventaires et plan d'achat, recomptés (lot V1).

- Réception (route 169) : pesé = Σ des pesées de ses lignes hors refus ; réserves et refus
  comptés ; lots = lots créés par ses lignes.
- Facture (route 175) : poids = Σ pesé des lignes non refusées de ses réceptions validées ;
  montant estimé = Σ pesé × prix de ces lignes.
- Inventaire (routes 189–190) : retenu = second comptage, sinon premier ; écart = retenu −
  théorique (en % du théorique) ; valeur de l'écart = écart × CMUP ; totaux = Σ lignes ;
  un inventaire validé par PRO a écrit, pour chaque lot compté, un ajustement égal à son écart
  (annulé : l'ajustement est défait).
- Plan d'achat (route 156) : budget = Σ des lignes ; comptes par statut ; fournisseurs = Σ de
  leurs lignes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from verif_socle import KG, Acces, Releve, somme_par

NOM_REC = "Chaque réception et chaque facture : pesé, réserves, refus, montant estimé"
NOM_INV = "Chaque inventaire : retenu, écart, valeur, totaux, ajustements écrits"
NOM_PLAN = "Plan d'achat : budget et comptes = Σ de ses lignes"


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Réceptions, factures, inventaires, plan d'achat."""
    _receptions(a, r)
    _factures(a, r)
    _inventaires(a, r)
    _plan_achat(a, r)


def _receptions(a: Acces, r: Releve) -> None:
    """Pesé, réserves, refus, lots de chaque réception."""
    lignes: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for x in a.sql("SELECT reception_id, quantite_pesee, qualite, lot_id FROM reception_ligne"):
        lignes[x[0]].append(x)
    for x in a.get("/receptions", limite=5000)["elements"]:
        siennes = lignes.get(x["id"], [])
        s = x["numero"] or f"brouillon {x['id']}"
        r.comparer(
            NOM_REC,
            s + " (pesé hors refus)",
            x["pese"],
            sum(y[1] for y in siennes if y[2] != "refuse"),
            KG,
        )
        r.juger(NOM_REC, s + " (lignes)", x["nb_lignes"] == len(siennes))
        r.juger(
            NOM_REC, s + " (réserves)", x["nb_reserve"] == sum(y[2] == "reserve" for y in siennes)
        )
        r.juger(NOM_REC, s + " (refus)", x["nb_refus"] == sum(y[2] == "refuse" for y in siennes))
        r.juger(
            NOM_REC,
            s + " (lots)",
            set(x["lots"]) == {y[3] for y in siennes if y[3]},
            f"écran {sorted(x['lots'])}",
        )


def _factures(a: Acces, r: Releve) -> None:
    """Poids et montant estimé de chaque facture."""
    pese = a.sql(
        "SELECT x.facture_id, rl.quantite_pesee, rl.quantite_pesee * rl.prix FROM reception_ligne "
        "rl JOIN reception x ON x.id = rl.reception_id WHERE x.statut = 'validee' AND "
        "rl.qualite <> 'refuse' AND x.facture_id IS NOT NULL"
    )
    poids = somme_par((f, kg) for f, kg, _ in pese)
    montant = somme_par((f, m) for f, _, m in pese)
    for f in a.get("/factures"):
        s = f"facture {f['numero']} ({f['fournisseur']})"
        r.comparer(NOM_REC, s + " (poids)", f["poids"], poids.get(f["id"], 0.0), KG)
        # Σ pesée × prix des réceptions validées, hors refus (schéma de la route 175) : la
        # facture peut dire autre chose (lot refusé facturé : C36), l'estimation n'en dépend pas.
        attendu = montant.get(f["id"], 0.0)
        r.comparer(NOM_REC, s + " (montant estimé)", f["montant_estime"], attendu)


def _ajustements(a: Acces) -> dict[tuple[int, int, int], float]:
    """Σ des ajustements écrits par chaque inventaire, par (inventaire, lot, magasin)."""
    return somme_par(
        a.sql(
            "SELECT inventaire_id, lot_id, magasin_id, SUM(quantite) FROM mouvement "
            "WHERE inventaire_id IS NOT NULL GROUP BY 1, 2, 3"
        ),
        cle=lambda x: (x[0], x[1], x[2]),
    )


def _inventaires(a: Acces, r: Releve) -> None:
    """Chaque inventaire : lignes et totaux ; ajustements écrits par PRO."""
    ecrits = _ajustements(a)
    repris = {
        i
        for (i,) in a.sql(
            "SELECT id_cible FROM reprise_correspondance WHERE table_cible = 'inventaire'"
        )
    }
    for resume in a.get("/inventaires"):
        f = a.get(f"/inventaires/{resume['id']}")
        s = f["numero"]
        comptees = [x for x in f["lignes"] if x["compte"] is not None]
        for x in comptees:
            retenu = x["second_compte"] if x["second_compte"] is not None else x["compte"]
            ecart = retenu - x["theorique"]
            r.comparer(NOM_INV, f"{s} · ligne {x['id']} (retenu)", x["retenu"], retenu, KG)
            r.comparer(NOM_INV, f"{s} · ligne {x['id']} (écart)", x["ecart"], ecart, KG)
            if x["cmup_mad"] is not None:
                r.comparer(
                    NOM_INV,
                    f"{s} · ligne {x['id']} (valeur)",
                    x["valeur_ecart_mad"],
                    ecart * x["cmup_mad"],
                )
            if f["statut"] in ("valide", "annule") and f["id"] not in repris and x["lot_id"]:
                attendu = ecart if f["statut"] == "valide" else 0.0
                r.comparer(
                    NOM_INV,
                    f"{s} · ligne {x['id']} (ajustement écrit)",
                    ecrits.get((f["id"], x["lot_id"], x["magasin_id"]), 0.0),
                    attendu,
                    KG,
                )
        r.comparer(
            NOM_INV,
            s + " (écart total)",
            f["ecart_total"],
            sum(x["ecart"] or 0.0 for x in comptees),
            KG,
        )
        r.comparer(
            NOM_INV,
            s + " (écart absolu)",
            f["ecart_absolu"],
            sum(abs(x["ecart"] or 0.0) for x in comptees),
            KG,
        )
        r.juger(NOM_INV, s + " (comptées)", f["nb_comptees"] == len(comptees))
        if f["ecart_valeur_mad"] is not None:
            r.comparer(
                NOM_INV,
                s + " (valeur de l'écart)",
                f["ecart_valeur_mad"],
                sum(x["valeur_ecart_mad"] or 0.0 for x in comptees),
            )


def _plan_achat(a: Acces, r: Releve) -> None:
    """Le plan d'achat : budget, comptes et fournisseurs = Σ de ses lignes."""
    p = a.get("/plan-achat")
    lignes, ind = p["lignes"], p["indicateurs"]
    r.comparer(NOM_PLAN, "budget", ind["budget_mad"], sum(x["montant_mad"] for x in lignes))
    r.comparer(
        NOM_PLAN, "quantité totale", ind["quantite_totale"], sum(x["quantite"] for x in lignes), KG
    )
    r.juger(NOM_PLAN, "références à commander", ind["references_a_commander"] == len(lignes))
    tiers = Counter(x["tier"] for x in lignes)
    r.juger(
        NOM_PLAN,
        "tiers",
        {k: v for k, v in ind["tiers"].items() if v} == dict(tiers),
        f"écran {ind['tiers']}, recompté {dict(tiers)}",
    )
    par_f = somme_par((x["fournisseur_id"], x["montant_mad"]) for x in lignes)
    for g in p["fournisseurs"]:
        r.comparer(
            NOM_PLAN,
            f"fournisseur {g['fournisseur']}",
            g["montant_mad"],
            par_f.get(g["fournisseur_id"], 0.0),
        )
        if ind["budget_mad"]:
            r.comparer(
                NOM_PLAN,
                f"fournisseur {g['fournisseur']} (part)",
                g["part_budget"],
                g["montant_mad"] / ind["budget_mad"],
                1e-6,
            )
