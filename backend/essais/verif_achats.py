"""Achats : reçu des commandes, échéancier, numéros sans trou (lot V1).

- Reçu net de chaque ligne de commande : lignes des réceptions **validées**, hors refus, moins
  les retours au fournisseur de leur lot, répartis au prorata des pesées du lot ; totaux du
  bon = Σ lignes ; montant = quantité × prix confirmé (estimé : prix confirmé, sinon estimé) ;
  reste = commandé − reçu (rien sous la tolérance) ; en MAD au cours figé du bon, sinon du jour.
- Échéancier : chaque facture due (réception validée) et chaque frais dû (dossier non annulé)
  y est une fois, au bon montant (saisi, sinon pesé × prix des lignes non refusées), à son
  échéance ; une réglée est dans les réglées ; totaux = Σ.
- Numéros sans trou par série et par année (le compteur n'est jamais en dessous) ; seuls les
  numéros retirés à la reprise (brouillons numérotés, rapport de reprise) peuvent manquer.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any

from verif_socle import KG, MAD, Acces, Releve, cours_de, somme_par

SERIES = {
    "commande": "numero",
    "reception": "numero",
    "ordre": "numero",
    "operation": "numero",
    "inventaire": "numero",
    "reclamation": "numero",
}
NUMERO = re.compile(r"^([A-Z]+)-(\d{4})-(\d+)$")


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Toutes les vérifications des achats."""
    taux = {code: float(c) for code, c in a.sql("SELECT code, cours FROM devise")}
    _recu_des_commandes(a, r, taux)
    _echeancier(a, r, taux, dates[-1])
    _numeros(a, r)


def recu_net(a: Acces) -> dict[int, float]:
    """Le reçu net de chaque ligne de commande, recompté en SQL."""
    return dict(
        a.sql(
            "WITH entrees AS (SELECT rl.commande_ligne_id, rl.lot_id, rl.quantite_pesee AS kg "
            "  FROM reception_ligne rl JOIN reception r ON r.id = rl.reception_id "
            "  WHERE r.statut = 'validee' AND rl.qualite <> 'refuse'), "
            "retours AS (SELECT lot_id, GREATEST(-SUM(quantite), 0) AS kg FROM mouvement "
            "  WHERE type = 'RETOUR_FOURNISSEUR' GROUP BY lot_id), "
            "pese AS (SELECT lot_id, SUM(kg) AS kg FROM entrees GROUP BY lot_id) "
            "SELECT e.commande_ligne_id, "
            "SUM(e.kg - LEAST(e.kg, COALESCE(rt.kg * e.kg / NULLIF(p.kg, 0), 0))) "
            "FROM entrees e LEFT JOIN retours rt ON rt.lot_id = e.lot_id "
            "LEFT JOIN pese p ON p.lot_id = e.lot_id "
            "WHERE e.commande_ligne_id IS NOT NULL GROUP BY 1"
        )
    )


def _lignes_du_bon(
    r: Releve,
    bon: tuple[str, bool],
    lignes: list[dict[str, Any]],
    base: dict[int, tuple[Any, ...]],
    tolerance: float,
) -> None:
    """Chaque ligne d'un bon : en base, montant (prix confirmé seulement), montant estimé,
    reste (commandé − reçu, rien sous la tolérance de livraison) et son estimation."""
    nom = "Chaque bon : quantité, reçu et montant = Σ de ses lignes"
    sujet, clos = bon
    for x in lignes:
        b = base.get(x["id"])
        s = f"{sujet} · ligne {x['id']}"
        r.juger(nom, s + " en base", b is not None and not abs(b[2] - x["quantite"]) > KG)
        prix = b[3] if b else 0.0
        r.comparer(nom, s + " (montant)", x["montant"], x["quantite"] * prix * x["prix_confirme"])
        r.comparer(
            nom,
            s + " (montant estimé)",
            x["montant_estime"],
            x["quantite"] * (prix if x["prix_confirme"] else x["prix_estime"]),
        )
        reste = 0.0 if clos else max(0.0, x["quantite"] - x["recu"])  # un bon clos : rien
        reste = reste if reste > x["quantite"] * tolerance else 0.0
        r.comparer(nom, s + " (reste)", x["reste"], reste, KG)
        r.comparer(nom, s + " (reste estimé)", x["reste_estime"], x["reste"] * x["prix_estime"])


def _recu_des_commandes(a: Acces, r: Releve, taux: dict[str, float]) -> None:
    """Reçu de chaque ligne ; lignes, totaux et montants de chaque bon."""
    nom = "Reçu de chaque ligne de commande (net des refus et des retours)"
    nom_bon = "Chaque bon : quantité, reçu et montant = Σ de ses lignes"
    recu = recu_net(a)
    base = {x[0]: x for x in a.sql("SELECT id, commande_id, quantite, prix FROM commande_ligne")}
    tolerance = float(dict(a.sql("SELECT cle, valeur FROM parametre")).get("toler_in_full", 0.02))
    for c in a.get("/commandes"):
        lignes = a.get(f"/commandes/{c['id']}")["lignes"]
        sujet = c["numero"] or f"brouillon {c['id']}"
        for x in lignes:
            r.comparer(nom, f"{sujet} · {x['reference']}", x["recu"], recu.get(x["id"], 0.0), KG)
        clos = c["statut"] in ("soldee", "annulee")
        _lignes_du_bon(r, (sujet, clos), lignes, base, tolerance)
        cours = cours_de(c["devise"], c["cours"], taux)
        for total, champ, unite in (
            ("quantite", "quantite", KG),
            ("recu", "recu", KG),
            ("reste_kg", "reste", KG),
            ("montant", "montant", MAD),
            ("montant_estime", "montant_estime", MAD),
        ):
            r.comparer(
                nom_bon, f"{sujet} ({total})", c[total], sum(x[champ] for x in lignes), unite
            )
        r.comparer(nom_bon, f"{sujet} (montant en MAD)", c["montant_mad"], c["montant"] * cours)
        r.comparer(
            nom_bon,
            f"{sujet} (reste estimé en MAD)",
            c["reste_estime_mad"],
            sum(x["reste_estime"] for x in lignes) * cours,
        )


def factures_dues(a: Acces) -> dict[int, dict[str, Any]]:
    """Chaque facture d'au moins une réception validée : montant (saisi, sinon pesé × prix),
    devise, échéance, règlement."""
    apporte = somme_par(
        a.sql(
            "SELECT rl_r.facture_id, rl.quantite_pesee * rl.prix FROM reception_ligne rl "
            "JOIN reception rl_r ON rl_r.id = rl.reception_id WHERE rl_r.statut = 'validee' "
            "AND rl.qualite <> 'refuse' AND rl_r.facture_id IS NOT NULL"
        )
    )
    dues = {}
    for fid, montant, devise, echeance, payee_le in a.sql(
        "SELECT f.id, f.montant, f.devise, f.echeance, f.payee_le FROM facture f WHERE EXISTS "
        "(SELECT 1 FROM reception x WHERE x.facture_id = f.id AND x.statut = 'validee')"
    ):
        dues[fid] = {
            "montant": montant if montant else apporte.get(fid, 0.0),
            "devise": devise,
            "echeance": echeance,
            "payee_le": payee_le,
        }
    return dues


def _echeancier(a: Acces, r: Releve, taux: dict[str, float], jour: date) -> None:
    """L'échéancier = les factures et les frais dus, à leur montant et à leur échéance."""
    nom = "Échéancier = factures et frais dus (montant, échéance, totaux)"
    e = a.get("/echeancier", du="2000-01-01", au="2100-12-31")
    vus: dict[tuple[str, int], list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for liste in ("lignes", "a_dater", "reglees", "ecartees"):
        for x in e[liste]:
            vus[(x["objet"], x["id"])].append((liste, x))
    dues = factures_dues(a)
    frais = {
        fid: {"montant": m, "devise": "MAD", "echeance": ech, "payee_le": p}
        for fid, m, ech, p in a.sql(
            "SELECT f.id, f.montant, f.echeance, f.payee_le FROM dossier_frais f "
            "JOIN dossier d ON d.id = f.dossier_id WHERE d.statut <> 'annule' OR "
            "f.payee_le IS NOT NULL"
        )
    }
    for objet, attendus in (("facture", dues), ("frais", frais)):
        for ident, b in attendus.items():
            liste = "reglees" if b["payee_le"] else ("lignes" if b["echeance"] else "a_dater")
            trouves = vus.get((objet, ident), [])
            sujet = f"{objet} {ident}"
            if not r.juger(
                nom,
                sujet,
                [t[0] for t in trouves] == [liste],
                f"attendu une fois dans « {liste} », vu {[t[0] for t in trouves]}",
            ):
                continue
            x = trouves[0][1]
            r.comparer(nom, sujet + " (montant)", x["montant"], b["montant"])
            r.comparer(
                nom,
                sujet + " (MAD)",
                x["montant_mad"],
                b["montant"] * cours_de(b["devise"], None, taux),
            )
            if liste == "lignes":
                r.juger(
                    nom,
                    sujet + " (échéance)",
                    x["date"] == b["echeance"].isoformat(),
                    f"écran {x['date']}, base {b['echeance']}",
                )
    for (objet, ident), trouves in vus.items():
        attendus = dues if objet == "facture" else frais
        r.juger(
            nom,
            f"{objet} {ident} due",
            ident in attendus or trouves[0][0] == "ecartees",
            "dans l'échéancier sans être due",
        )
    total = sum(x["montant_mad"] for x in e["lignes"])
    echu = sum(x["montant_mad"] for x in e["lignes"] if x["date"] < jour.isoformat())
    r.comparer(nom, "total", e["total_mad"], total)
    r.comparer(nom, "échu", e["echu_mad"], echu)
    r.comparer(nom, "à dater", e["a_dater_mad"], sum(x["montant_mad"] for x in e["a_dater"]))
    par_mois = somme_par((x["date"][:7], x["montant_mad"]) for x in e["lignes"])
    for mois, montant in par_mois.items():
        r.comparer(nom, f"mois {mois}", e["par_mois"].get(mois), montant)


def _numeros_pris(a: Acces) -> dict[tuple[str, int], dict[int, str]]:
    """Par (série, année) : chaque numéro et son origine — « repris » (de Gestion MP), « donné »
    (par PRO), « occupé » (porté par un lot du fournisseur au motif LOT-AAAA-NNNN : la série
    interne le saute)."""
    pris: dict[tuple[str, int], dict[int, str]] = defaultdict(dict)
    repris = (
        "EXISTS (SELECT 1 FROM reprise_correspondance c WHERE c.table_cible = '{t}' "
        "AND c.id_cible = x.id)"
    )
    # Noms de tables et de colonnes fixés dans ce fichier : aucune saisie dans le SQL.
    requetes = [
        f"SELECT x.{c}, {repris.format(t=t)} FROM {t} x WHERE x.{c} IS NOT NULL"  # noqa: S608
        for t, c in SERIES.items()
    ]
    requetes.append(f"SELECT x.numero, {repris.format(t='lot')} FROM lot x WHERE x.interne")  # noqa: S608
    for requete in requetes:
        for numero, vient in a.sql(requete):
            if m := NUMERO.match(numero):
                pris[(m[1], int(m[2]))][int(m[3])] = "repris" if vient else "donné"
    for annee, rang, vient in a.sql(
        f"SELECT x.annee, x.rang, {repris.format(t='dossier')} FROM dossier x "  # noqa: S608
        "WHERE x.rang IS NOT NULL"
    ):
        pris[("DOS", int(annee))][int(rang)] = "repris" if vient else "donné"
    for (numero,) in a.sql("SELECT numero FROM lot WHERE NOT interne"):
        if (m := NUMERO.match(numero)) and (m[1], int(m[2])) in pris:
            pris[(m[1], int(m[2]))].setdefault(int(m[3]), "occupé")
    return pris


RETIRE = re.compile(r"brouillon numéroté ([A-Z]+)-(\d{4})-(\d+) : numéro retiré")


def _retires_a_la_reprise(a: Acces) -> set[tuple[str, int, int]]:
    """Les numéros que la reprise a retirés aux brouillons numérotés de Gestion MP et gardés
    au compteur (R1, décision 4) : jamais redonnés, ils manquent à bon droit — même si le
    brouillon est ensuite supprimé (lot V2 : le scénario le fait avant de clore novembre)."""
    retires: set[tuple[str, int, int]] = set()
    for (rapport,) in a.sql("SELECT rapport FROM reprise_execution WHERE statut = 'reussie'"):
        for m in RETIRE.finditer(rapport or ""):
            retires.add((m[1], int(m[2]), int(m[3])))
    return retires


def _numeros(a: Acces, r: Releve) -> None:
    """Chaque série, chaque année : 1…N sans trou ; le compteur au moins à N. Un trou n'est
    permis que sous le plus grand numéro repris de Gestion MP (numéros gardés tels quels)."""
    nom = "Numéros sans trou, par série et par année"
    compteurs = {
        (s, int(an)): int(n) for s, an, n in a.sql("SELECT serie, annee, dernier FROM compteur")
    }
    retires = _retires_a_la_reprise(a)
    for (serie, annee), numeros in sorted(_numeros_pris(a).items()):
        repris = max((n for n, v in numeros.items() if v == "repris"), default=0)
        plus_grand = max((n for n, v in numeros.items() if v != "occupé"), default=0)
        trous = [
            n
            for n in range(repris + 1, plus_grand + 1)
            if n not in numeros and (serie, annee, n) not in retires
        ]
        r.juger(nom, f"{serie} {annee}", not trous, f"trous {trous[:10]}")
        r.juger(
            nom,
            f"{serie} {annee} (compteur)",
            compteurs.get((serie, annee), 0) >= plus_grand,
            f"compteur {compteurs.get((serie, annee))}, plus grand numéro {plus_grand}",
        )
