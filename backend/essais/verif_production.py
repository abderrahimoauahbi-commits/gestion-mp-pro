"""Production : sorti net de chaque ordre, prévu figé, recettes à 100 % par rôle (lot V1).

- Ordre validé : total = Σ de ses lignes ; revenu = Σ de ses retours des machines (journal) ;
  net = −Σ de son journal (sorties − retours, annulations comprises) ; m² = Σ de ses
  qualités ; prévu figé = Σ kilos hors perte × (1 + perte figée) ; écart = net − prévu
  (relatif : ÷ prévu).
  Ordre annulé : net nul, et son journal s'annule. Brouillon : net = Σ de ses lignes.
- Consommation par ordre (écran Sorties) : mêmes kilos, et par matière.
- Nomenclature (route 43) : kg/m² = poids du rôle × part (un rôle au mètre : ml/m² × densité) ;
  coût au m² = kg/m² × prix au kilo × cours du jour × (1 + taux de perte).
- Recettes : pour chaque qualité, chaque rôle pesé au m² doit faire 100 % (0,01 point) ; les
  qualités fautives sont exactement celles que C01 nomme.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from verif_socle import KG, RELATIF, Acces, Releve, somme_par

TOLERANCE_RECETTE = 0.01


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Toutes les vérifications de la production."""
    _ordres(a, r)
    _consommation(a, r)
    _recettes(a, r)
    _nomenclature(a, r)


def journal_des_ordres(a: Acces) -> tuple[dict[int, float], dict[int, float]]:
    """(sorti, revenu) de chaque ordre, en kilos, recomptés dans le journal."""
    lignes = a.sql(
        "SELECT ordre_id, type, SUM(quantite) FROM mouvement WHERE ordre_id IS NOT NULL "
        "GROUP BY 1, 2"
    )
    sorti = {o: -q for o, t, q in lignes if t == "SORTIE"}
    revenu = {o: q for o, t, q in lignes if t == "RETOUR_MACHINE"}
    return sorti, revenu


def prevu_fige(a: Acces) -> dict[int, float]:
    """Le prévu figé de chaque ordre : Σ kilos hors perte × (1 + perte figée)."""
    return somme_par(
        a.sql(
            "SELECT o.id, p.kg_hors_perte * (1 + o.taux_perte_fige) FROM ordre o "
            "JOIN ordre_prevu p ON p.ordre_id = o.id WHERE o.prevu_fige"
        )
    )


def _ordres(a: Acces, r: Releve) -> None:
    """Chaque ordre de la liste (route 128)."""
    nom = "Sorti net de chaque ordre (sorties − retours), prévu figé, écart"
    sorti, revenu = journal_des_ordres(a)
    prevu = prevu_fige(a)
    m2 = somme_par(a.sql("SELECT ordre_id, m2 FROM ordre_qualite"))
    lignes = somme_par(a.sql("SELECT ordre_id, quantite FROM ordre_ligne"))
    figes = {o for (o,) in a.sql("SELECT id FROM ordre WHERE prevu_fige")}
    for o in a.get("/ordres"):
        oid, sujet = o["id"], o["numero"] or f"brouillon {o['id']}"
        net = sorti.get(oid, 0.0) - revenu.get(oid, 0.0)
        if o["statut"] == "brouillon":
            r.comparer(nom, sujet + " (net du brouillon)", o["net"], lignes.get(oid, 0.0), KG)
            continue
        r.comparer(nom, sujet + " (m²)", o["m2"], m2.get(oid, 0.0), KG)
        if o["statut"] == "annule":
            r.comparer(nom, sujet + " (annulé : journal)", net, 0.0, KG)
            r.comparer(nom, sujet + " (annulé : net)", o["net"], 0.0, KG)
            continue
        r.comparer(nom, sujet + " (lignes)", o["total"], lignes.get(oid, 0.0), KG)
        r.comparer(nom, sujet + " (revenu)", o["revenu"], revenu.get(oid, 0.0), KG)
        r.comparer(nom, sujet + " (net)", o["net"], net, KG)
        if oid in figes:
            r.comparer(nom, sujet + " (prévu figé)", o["prevu"], prevu.get(oid, 0.0), KG)
        if o["prevu"]:
            r.comparer(nom, sujet + " (écart)", o["ecart"], o["net"] - o["prevu"], KG)
            r.comparer(
                nom,
                sujet + " (écart relatif)",
                o["ecart_relatif"],
                (o["net"] - o["prevu"]) / o["prevu"],
                RELATIF,
            )


def _consommation(a: Acces, r: Releve) -> None:
    """La consommation par ordre (route 147) : kilos et matières, recomptés."""
    nom = "Consommation par ordre (écran Sorties) : sorti, retours, net, par matière"
    sorti, revenu = journal_des_ordres(a)
    par_matiere: dict[tuple[int, int], float] = defaultdict(float)
    for o, m, q in a.sql(
        "SELECT ordre_id, matiere_id, SUM(quantite) FROM mouvement WHERE ordre_id IS NOT NULL "
        "GROUP BY 1, 2"
    ):
        par_matiere[(o, m)] = -q
    valides = {
        o
        for (o,) in a.sql(
            "SELECT id FROM ordre o WHERE statut = 'valide' AND EXISTS (SELECT 1 FROM mouvement m "
            "WHERE m.ordre_id = o.id)"
        )
    }
    vus = a.get("/ordres/consommation")
    r.juger(
        nom,
        "ordres validés qui ont un journal",
        {x["ordre_id"] for x in vus} == valides,
        f"écran {len(vus)}, base {len(valides)}",
    )
    for x in vus:
        oid, sujet = x["ordre_id"], x["numero"]
        r.comparer(nom, sujet + " (sorti)", x["consomme"], sorti.get(oid, 0.0), KG)
        r.comparer(nom, sujet + " (retours)", x["retours"], revenu.get(oid, 0.0), KG)
        r.comparer(nom, sujet + " (net)", x["net"], sorti.get(oid, 0.0) - revenu.get(oid, 0.0), KG)
        for m in x["references"]:
            if m["matiere_id"] is not None:
                r.comparer(
                    nom,
                    f"{sujet} · matière {m['matiere_id']}",
                    m["quantite"],
                    par_matiere.get((oid, m["matiere_id"]), 0.0),
                    KG,
                )


def recettes_fausses(a: Acces) -> dict[int, list[tuple[Any, float]]]:
    """Les qualités dont un rôle pesé au m² ne fait pas 100 % : {qualité : [(rôle, Σ %)]}."""
    fausses: dict[int, list[tuple[Any, float]]] = defaultdict(list)
    for qid, role, total in a.sql(
        "SELECT p.qualite_id, p.role_id, COALESCE(SUM(r.pourcentage), 0) FROM qualite_poids p "
        "LEFT JOIN recette r ON r.qualite_id = p.qualite_id AND r.matiere_id IN "
        "(SELECT id FROM matiere m WHERE m.role_id = p.role_id) WHERE p.poids <> 0 "
        "GROUP BY 1, 2"
    ):
        if abs(total - 100) > TOLERANCE_RECETTE:
            fausses[qid].append((role, total))
    return fausses


def _recettes(a: Acces, r: Releve) -> None:
    """Recettes à 100 % par rôle : C01 nomme exactement les qualités fautives."""
    nom = "Recettes à 100 % par rôle (C01)"
    fausses = recettes_fausses(a)
    c01 = next(c for c in a.get("/controles")["controles"] if c["code"] == "C01")
    detail = a.get("/controles/C01", limite=5000)
    nommees = {x.get("qualite_id") for x in detail["elements"]}
    (n,) = a.sql("SELECT count(DISTINCT qualite_id) FROM qualite_poids WHERE poids <> 0")[0]
    for qid in sorted(fausses):
        r.juger(
            nom,
            f"qualité {qid}",
            qid in nommees,
            f"rôles {fausses[qid]} hors de 100 %, absente de C01",
        )
    for qid in sorted(nommees - set(fausses)):
        r.juger(nom, f"qualité {qid}", False, "nommée par C01 alors que chaque rôle fait 100 %")
    r.famille(nom).cas += max(int(n) - len(fausses), 0)
    r.juger(
        nom,
        "nombre d'anomalies de C01",
        c01["anomalies"] == len(fausses),
        f"écran {c01['anomalies']}, recompté {len(fausses)}",
    )


def _nomenclature(a: Acces, r: Releve) -> None:
    """Chaque ligne de recette : kg/m², ml/m², coût au m²."""
    nom = "Nomenclature : kg/m² et coût au m² de chaque ligne de recette"
    poids = {
        (q, role): p for q, role, p in a.sql("SELECT qualite_id, role_id, poids FROM qualite_poids")
    }
    lineaire = dict(a.sql("SELECT id, lineaire FROM role_nomenclature"))
    matieres = {
        m: x
        for m, *x in a.sql("SELECT id, role_id, densite, prix, unite_prix, devise FROM matiere")
    }
    taux = {code: float(c) for code, c in a.sql("SELECT code, cours FROM devise")}
    perte = float(dict(a.sql("SELECT cle, valeur FROM parametre")).get("taux_perte", 0.0))
    parts = {
        (q, m): p for q, m, p in a.sql("SELECT qualite_id, matiere_id, pourcentage FROM recette")
    }
    for x in a.get("/nomenclature")["lignes"]:
        q, m = x["qualite_id"], x["matiere_id"]
        role, densite, prix, unite, devise = matieres[m]
        quantite = poids.get((q, role), 0.0) * parts.get((q, m), 0.0) / 100
        kg = quantite * densite if lineaire.get(role) else quantite
        prix_kg = prix / densite if unite == "ml" and densite else prix
        s = f"qualité {q} · matière {m}"
        r.comparer(nom, s + " (part)", x["pourcentage"], parts.get((q, m), 0.0), 1e-6)
        r.comparer(nom, s + " (kg/m²)", x["kg_m2"], kg, 1e-6)
        cout = kg * prix_kg * (1.0 if devise == "MAD" else taux.get(devise, 1.0)) * (1 + perte)
        r.comparer(nom, s + " (coût au m²)", x["cout_m2_mad"], cout, 1e-4)
