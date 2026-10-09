"""Coûts d'entrée et coût de revient des dossiers, refaits sans le moteur (lot V1).

Formules de la documentation (CALCULS B § 9.3–9.4, § 9.10–9.11, § 1.3 `cout_d_entree`),
écrites une seconde fois :

- valeur d'une marchandise = valeur en devise × (cours porté, sinon cours du jour) ; en MAD,
  la valeur telle quelle ;
- un frais affecté à une marchandise lui revient entier ; une répartition figée (parts dont
  la somme fait le montant) est gardée ; sinon le frais se répartit à la valeur, ou au poids
  si la clé de son poste est « poids » ; la TVA (poste récupérable) n'est pas un coût ;
- dossier annulé : hors calcul ;
- coût d'entrée d'un achat (ouverture, réception) : le coût de revient unitaire de la
  marchandise de dossier de **sa** ligne de réception ; pour une entrée sans ligne de
  réception, celui des marchandises saisies à la main pour son lot ; sinon prix × cours figé
  du mouvement (à défaut, cours du jour) — un prix nul saisi est un coût nul (V2, C-02).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from verif_socle import Acces, cours_de

Ligne = dict[str, Any]


def lignes_de_dossier(a: Acces, taux: dict[str, float]) -> dict[int, list[Ligne]]:
    """Les marchandises des dossiers non annulés, valorisées en MAD, par dossier."""
    par_dossier: dict[int, list[Ligne]] = defaultdict(list)
    for lid, did, rl, mid, lot, kg, valeur, devise, cours in a.sql(
        "SELECT l.id, l.dossier_id, l.reception_ligne_id, l.matiere_id, l.lot_id, l.quantite_kg, "
        "l.valeur_devise, l.devise, l.cours FROM dossier_ligne l JOIN dossier d "
        "ON d.id = l.dossier_id WHERE d.statut <> 'annule' ORDER BY l.id"
    ):
        par_dossier[did].append(
            {
                "id": lid,
                "rl": rl,
                "matiere": mid,
                "lot": lot,
                "kg": float(kg or 0.0),
                "mad": float(valeur or 0.0) * cours_de(devise, cours, taux),
                "frais": 0.0,
                "tva": 0.0,
            }
        )
    return par_dossier


def repartir(a: Acces, par_dossier: dict[int, list[Ligne]]) -> dict[int, list[Ligne]]:
    """Les frais de chaque dossier répartis sur ses marchandises (en place) ; rend le dict."""
    parts: dict[int, dict[int, float]] = defaultdict(dict)
    for frais, ligne, montant in a.sql(
        "SELECT frais_id, ligne_id, montant FROM dossier_frais_part"
    ):
        parts[frais][ligne] = float(montant)
    for fid, did, montant_base, ligne_id, recuperable, cle in a.sql(
        "SELECT f.id, f.dossier_id, f.montant, f.ligne_id, p.recuperable, p.cle "
        "FROM dossier_frais f JOIN poste_frais p ON p.id = f.poste_id"
    ):
        dossier = par_dossier.get(did, [])
        champ = "tva" if recuperable else "frais"
        montant = float(montant_base)
        cible = [x for x in dossier if x["id"] == ligne_id]
        if cible:
            cible[0][champ] += montant
            continue
        figee = parts.get(fid, {})
        ids = {x["id"] for x in dossier}
        if figee and set(figee) <= ids and abs(sum(figee.values()) - montant) < 0.005:
            for x in dossier:
                x[champ] += figee.get(x["id"], 0.0)
            continue
        poids = "kg" if cle == "poids" else "mad"
        total = sum(x[poids] for x in dossier)
        for x in dossier:
            x[champ] += montant * x[poids] / total if total else 0.0
    return par_dossier


def revient_des_dossiers(a: Acces, taux: dict[str, float]) -> dict[int, list[Ligne]]:
    """Les marchandises de chaque dossier avec leurs frais (hors TVA) et leur TVA."""
    return repartir(a, lignes_de_dossier(a, taux))


def _unitaires(
    a: Acces, taux: dict[str, float]
) -> tuple[dict[int, float], dict[tuple[int, int], list[float]]]:
    """Coût de revient unitaire par ligne de réception, et (kg, MAD) par (matière, lot) des
    marchandises saisies à la main."""
    par_rl: dict[int, float] = {}
    a_la_main: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for dossier in revient_des_dossiers(a, taux).values():
        for x in dossier:
            revient = x["mad"] + x["frais"]
            if not x["kg"] or not revient:
                continue
            if x["rl"] is not None:
                par_rl[x["rl"]] = revient / x["kg"]
            elif x["lot"] is not None:
                bloc = a_la_main[(x["matiere"], x["lot"])]
                bloc[0] += x["kg"]
                bloc[1] += revient
    return par_rl, a_la_main


def _ligne_de_reception(a: Acces) -> dict[int, int]:
    """La ligne de réception de chaque entrée de réception (même réception, même lot ; à
    défaut même lot, même date et même pesée — entrées reprises sans réception)."""
    rangs: dict[int, int] = {}
    for mid, rl in a.sql(
        "SELECT DISTINCT ON (m.id) m.id, rl.id FROM mouvement m JOIN reception_ligne rl "
        "ON rl.lot_id = m.lot_id JOIN reception r ON r.id = rl.reception_id "
        "WHERE m.type = 'RECEPTION' AND m.quantite > 0 AND m.contrepasse_id IS NULL "
        "AND (rl.reception_id = m.reception_id OR (m.reception_id IS NULL "
        "  AND r.date = m.date_effet AND rl.quantite_pesee = m.quantite)) "
        "ORDER BY m.id, (rl.quantite_pesee = m.quantite) DESC, rl.id"
    ):
        rangs[mid] = rl
    return rangs


def couts_d_entree(a: Acces, taux: dict[str, float]) -> dict[int, float]:
    """Le coût d'entrée (MAD/kg) de chaque achat : {mouvement : coût}."""
    par_rl, a_la_main = _unitaires(a, taux)
    ligne_de = _ligne_de_reception(a)
    couts: dict[int, float] = {}
    for mid, matiere, lot, prix, devise, cours in a.sql(
        "SELECT id, matiere_id, lot_id, prix, devise, cours FROM mouvement "
        "WHERE type IN ('OUVERTURE', 'RECEPTION') AND quantite > 0 AND contrepasse_id IS NULL"
    ):
        rl = ligne_de.get(mid)
        main = a_la_main.get((matiere, lot)) if rl is None else None
        if rl is not None and rl in par_rl:
            couts[mid] = par_rl[rl]
        elif main and main[0]:
            couts[mid] = main[1] / main[0]
        else:  # le prix saisi, même nul : un coût nul est un coût (V2, C-02)
            couts[mid] = float(prix or 0.0) * cours_de(devise, cours, taux)
    return couts


def cout_d_entree_des_lots(a: Acces, taux: dict[str, float]) -> dict[int, float]:
    """Le coût d'entrée moyen de chaque lot : ses achats non annulés, à leur coût d'entrée."""
    couts = couts_d_entree(a, taux)
    entrees: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for mid, lot, quantite in a.sql(
        "SELECT m.id, m.lot_id, m.quantite FROM mouvement m WHERE m.type IN ('OUVERTURE', "
        "'RECEPTION') AND m.quantite > 0 AND m.contrepasse_id IS NULL AND NOT EXISTS "
        "(SELECT 1 FROM mouvement x WHERE x.contrepasse_id = m.id)"
    ):
        if mid in couts:
            entrees[lot][0] += float(quantite)
            entrees[lot][1] += float(quantite) * couts[mid]
    return {lot: v / q for lot, (q, v) in entrees.items() if q > 1e-9}
