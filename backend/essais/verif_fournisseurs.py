"""Fournisseurs : OTIF par réception, moyennes, retours, score et classement (lot V1).

Formules de la documentation (CALCULS B § 4.3–4.5), écrites une seconde fois :

- seules les réceptions validées sont jugées ; conforme (In-Spec) = toutes leurs lignes
  conformes ; à l'heure = chacun de leurs bons livré au plus tard à la date promise (plus la
  tolérance), réputée à l'heure sans date promise ; OTIF = rien si la réception ne devait rien
  (In-Full vide), sinon à l'heure × complète × conforme ;
- moyennes d'un fournisseur sur ses réceptions **notées** (OTIF connu) seulement ;
- taux de retours = kilos renvoyés ÷ kilos reçus (lots du fournisseur, annulations comprises) ;
- score = OTIF × 60 + 20 × max(0, 1 − retours ÷ 5 %) + min(20, max(0, 20 − (délai − 15) ÷ 5)),
  arrondi à l'entier (demi au-dessus) ; classement par les seuils réglés ; sous-performant si
  l'OTIF est sous la cible.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from typing import Any

from verif_socle import RELATIF, Acces, Releve, ecart

CHAMPS = ("on_time", "in_full", "in_spec", "otif")


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Toutes les vérifications des fournisseurs."""
    perf = a.get("/fournisseurs/performance")
    _receptions(a, r, perf["receptions"])
    _fournisseurs(a, r, perf)


def _a_l_heure(a: Acces) -> dict[int, int | None]:
    """À l'heure de chaque réception validée, recompté depuis ses bons (date promise)."""
    tolerance = float(dict(a.sql("SELECT cle, valeur FROM parametre")).get("toler_retard_jours", 0))
    jugements: dict[int, list[int]] = defaultdict(list)
    validees = {rid for (rid,) in a.sql("SELECT id FROM reception WHERE statut = 'validee'")}
    for rid, recu_le, commande_le, promis in a.sql(
        "SELECT DISTINCT r.id, r.date, c.date_commande, c.date_livraison_prevue "
        "FROM reception r JOIN reception_ligne rl ON rl.reception_id = r.id "
        "JOIN commande_ligne cl ON cl.id = rl.commande_ligne_id "
        "JOIN commande c ON c.id = cl.commande_id WHERE r.statut = 'validee' "
        "AND c.date_livraison_prevue IS NOT NULL"
    ):
        reel = (recu_le - commande_le).days
        prevu = (promis - commande_le).days
        jugements[rid].append(1 if reel <= prevu + tolerance else 0)
    return {rid: (min(jugements[rid]) if jugements[rid] else None) for rid in validees}


def _receptions(a: Acces, r: Releve, receptions: list[dict[str, Any]]) -> None:
    """Chaque réception notée : à l'heure, conforme, OTIF."""
    nom = "OTIF de chaque réception (à l'heure, complète, conforme)"
    heure = _a_l_heure(a)
    conforme = {
        rid: int(ok)
        for rid, ok in a.sql(
            "SELECT reception_id, bool_and(qualite = 'conforme') FROM reception_ligne GROUP BY 1"
        )
    }
    vues = {x["reception_id"]: x for x in receptions}
    r.juger(
        nom,
        "réceptions jugées = réceptions validées",
        set(vues) == set(heure),
        f"écran {len(vues)}, base {len(heure)}",
    )
    for rid, x in sorted(vues.items()):
        sujet = x["numero"]
        r.juger(
            nom,
            sujet + " (à l'heure)",
            x["on_time"] == heure.get(rid),
            f"écran {x['on_time']}, recompté {heure.get(rid)}",
        )
        r.juger(
            nom,
            sujet + " (conforme)",
            x["in_spec"] == conforme.get(rid, 0),
            f"écran {x['in_spec']}, recompté {conforme.get(rid, 0)}",
        )
        if x["in_full"] is None:
            attendu = None
        else:
            attendu = (1 if x["on_time"] is None else x["on_time"]) * x["in_full"] * x["in_spec"]
        r.juger(
            nom, sujet + " (OTIF)", x["otif"] == attendu, f"écran {x['otif']}, attendu {attendu}"
        )


def _arrondi(x: float) -> float:
    """Arrondi à l'entier, demi au-dessus."""
    return float(math.floor(x + 0.5))


def points(otif: float, retours: float, delai: float) -> float:
    """Le score d'un fournisseur (CALCULS B § 4.4)."""
    p_retours = 20 * max(0.0, 1 - retours / 0.05)
    p_delai = min(20.0, max(0.0, 20 - (delai - 15) / 5))
    return otif * 60 + p_retours + p_delai


def _taux_retours(a: Acces) -> dict[int, float]:
    """Kilos renvoyés ÷ kilos reçus, par fournisseur du lot."""
    flux: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for fid, genre, q in a.sql(
        "SELECT l.fournisseur_id, m.type, SUM(m.quantite) FROM mouvement m JOIN lot l "
        "ON l.id = m.lot_id WHERE m.type IN ('RECEPTION', 'RETOUR_FOURNISSEUR') GROUP BY 1, 2"
    ):
        flux[fid][0 if genre == "RECEPTION" else 1] += float(q)
    return {f: (-sortie / entree if entree else 0.0) for f, (entree, sortie) in flux.items()}


def _fournisseurs(a: Acces, r: Releve, perf: dict[str, Any]) -> None:
    """Moyennes sur les réceptions notées, retours, score, classement."""
    nom = "Note de chaque fournisseur (moyennes des réceptions notées, retours, score)"
    par_f: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for x in perf["receptions"]:
        par_f[x["fournisseur_id"]].append(x)
    retours = _taux_retours(a)
    delais = dict(a.sql("SELECT id, delai_jours FROM fournisseur"))
    s = perf["seuils"]
    for f in perf["lignes"]:
        fid, sujet = f["fournisseur_id"], f["fournisseur"]
        notees = [x for x in par_f.get(fid, []) if x["otif"] is not None]
        r.juger(nom, sujet + " (réceptions)", f["receptions"] == len(par_f.get(fid, [])))
        for champ in CHAMPS:
            valeurs = [x[champ] for x in notees if x[champ] is not None]
            attendu = sum(valeurs) / len(notees) if valeurs else None
            juste = (f[champ] is None) == (attendu is None) and not ecart(
                f[champ], attendu, RELATIF
            )
            r.juger(nom, f"{sujet} ({champ})", juste, f"écran {f[champ]}, recompté {attendu}")
        r.comparer(nom, sujet + " (retours)", f["taux_retours"], retours.get(fid, 0.0), RELATIF)
        r.comparer(nom, sujet + " (délai)", f["delai_jours"], delais.get(fid), RELATIF)
        if f["otif"] is None:
            r.juger(nom, sujet + " (score)", f["score"] is None, f"score {f['score']} sans OTIF")
            continue
        score = _arrondi(points(f["otif"], f["taux_retours"], f["delai_jours"]))
        r.comparer(nom, sujet + " (score)", f["score"], score, 0.5)
        rang = (
            "Stratégique"
            if score >= s["strategique"]
            else "Standard"
            if score >= s["standard"]
            else "À surveiller"
            if score >= s["surveiller"]
            else "À challenger"
        )
        r.juger(
            nom,
            sujet + " (classement)",
            f["classement"] == rang,
            f"écran {f['classement']}, attendu {rang}",
        )
        r.juger(
            nom,
            sujet + " (sous la cible)",
            f["sous_performant"] == (f["otif"] < perf["cible_otif"]),
        )
