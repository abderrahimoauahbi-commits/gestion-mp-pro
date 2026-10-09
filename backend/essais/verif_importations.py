"""Importations : coût hors TVA, TVA, répartition des frais, TVA attendue (lot V1).

Pour chaque dossier non annulé, recompté depuis la base avec la répartition refaite sans le
moteur (`verif_couts`) :

- marchandise = Σ valeur × cours (porté, sinon du jour) ; poids = Σ kilos ;
- frais hors TVA (postes non récupérables) et TVA (postes récupérables) : la part répartie sur
  les marchandises, et à part ce qui ne tombe sur aucune (dossier vide) ; droits = Σ frais de
  nature « droits » ;
- coût hors TVA = marchandise + frais répartis ; décaissé = coût + TVA répartie ;
- chaque marchandise : valeur, frais, TVA, coût, coût au kilo (clé du poste, frais affecté,
  répartition figée) ;
- TVA attendue = taux × (valeur en douane + droits + TPI), valeur en douane = marchandise +
  frais des postes qui y entrent, TPI = frais de nature « tpi », sinon taux TPI × douane ;
- écart de facture (C36) : Σ valeur en devise des marchandises, si toutes sont dans la devise
  de la facture.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from verif_couts import revient_des_dossiers
from verif_socle import KG, Acces, Releve, somme_par

NOM = "Coût hors TVA et TVA de chaque dossier"
NOM_LIGNES = "Répartition des frais : chaque marchandise de dossier (clé du poste)"
NOM_TVA = "TVA attendue et écart de facture de chaque dossier"


def verifier(a: Acces, r: Releve, dates: list[date]) -> None:
    """Toutes les vérifications des dossiers d'importation."""
    taux = {code: float(c) for code, c in a.sql("SELECT code, cours FROM devise")}
    lignes = revient_des_dossiers(a, taux)
    frais = a.sql(
        "SELECT f.dossier_id, p.recuperable, p.nature, p.entre_valeur_douane, f.montant "
        "FROM dossier_frais f JOIN poste_frais p ON p.id = f.poste_id"
    )
    reglages = dict(a.sql("SELECT cle, valeur FROM parametre"))
    for d in a.get("/dossiers", limite=5000)["elements"]:
        if d["statut"] == "annule":
            continue
        dossier = lignes.get(d["id"], [])
        siens = [x for x in frais if x[0] == d["id"]]
        _dossier(r, d, dossier, siens)
        _tva_attendue(r, d, dossier, siens, reglages)
        _marchandises(a, r, d, dossier)
    _ecarts_de_facture(a, r)
    _controles(a, r, lignes, frais, reglages)


def _dossier(r: Releve, d: dict[str, Any], dossier: list[dict[str, Any]], frais: list[Any]) -> None:
    """Les totaux du dossier."""
    sujet = d["numero"]
    marchandise = sum(x["mad"] for x in dossier)
    charges = sum(m for _, rec, _, _, m in frais if not rec)
    tva = sum(m for _, rec, _, _, m in frais if rec)
    reparties = sum(x["frais"] for x in dossier)
    tva_repartie = sum(x["tva"] for x in dossier)
    r.comparer(NOM, sujet + " (marchandise)", d["marchandise_mad"], marchandise)
    r.comparer(NOM, sujet + " (poids)", d["poids"], sum(x["kg"] for x in dossier), KG)
    r.comparer(NOM, sujet + " (frais hors TVA répartis)", d["charges_mad"], reparties)
    r.comparer(NOM, sujet + " (TVA répartie)", d["tva_mad"], tva_repartie)
    r.comparer(
        NOM,
        sujet + " (droits)",
        d["droits_mad"],
        sum(m for _, _, nature, _, m in frais if nature == "droits"),
    )
    r.comparer(
        NOM,
        sujet + " (frais non répartis)",
        d["charges_non_reparties_mad"],
        charges - reparties if abs(charges - reparties) > 0.005 else 0.0,
    )
    r.comparer(
        NOM,
        sujet + " (TVA non répartie)",
        d["tva_non_repartie_mad"],
        tva - tva_repartie if abs(tva - tva_repartie) > 0.005 else 0.0,
    )
    r.comparer(NOM, sujet + " (coût hors TVA)", d["revient_mad"], marchandise + reparties)
    r.comparer(
        NOM, sujet + " (décaissé)", d["decaisse_mad"], marchandise + reparties + tva_repartie
    )


def _attendue(dossier: list[dict[str, Any]], frais: list[Any], reglages: dict[str, Any]) -> float:
    """TVA attendue = taux × (valeur en douane + droits + TPI)."""
    douane = sum(x["mad"] for x in dossier)
    douane += sum(m for _, _, _, entre, m in frais if entre)
    droits = sum(m for _, _, nature, _, m in frais if nature == "droits")
    tpis = [m for _, _, nature, _, m in frais if nature == "tpi"]
    tpi = sum(tpis) if tpis else douane * float(reglages.get("taux_tpi_import", 0.0025))
    return (douane + droits + tpi) * float(reglages.get("taux_tva_import", 0.2))


def _tva_attendue(
    r: Releve,
    d: dict[str, Any],
    dossier: list[dict[str, Any]],
    frais: list[Any],
    reglages: dict[str, Any],
) -> None:
    """La TVA attendue de la fiche, recalculée."""
    if not dossier:
        r.juger(
            NOM_TVA,
            d["numero"] + " (sans marchandise)",
            not d["tva_attendue_mad"],
            f"TVA attendue {d['tva_attendue_mad']} sans marchandise",
        )
        return
    attendue = _attendue(dossier, frais, reglages)
    r.comparer(NOM_TVA, d["numero"] + " (TVA attendue)", d["tva_attendue_mad"], attendue)


def _marchandises(a: Acces, r: Releve, d: dict[str, Any], dossier: list[dict[str, Any]]) -> None:
    """Chaque marchandise du dossier : valeur, frais, TVA, coût, coût au kilo."""
    fiche = a.get(f"/dossiers/{d['id']}")
    miennes = {x["id"]: x for x in dossier}
    for x in fiche["lignes"]:
        sujet = f"{d['numero']} · ligne {x['id']}"
        m = miennes.get(x["id"])
        if not r.juger(NOM_LIGNES, sujet, m is not None, "absente de la base"):
            continue
        assert m is not None
        r.comparer(NOM_LIGNES, sujet + " (valeur)", x["valeur_mad"], m["mad"])
        r.comparer(NOM_LIGNES, sujet + " (frais)", x["charges_mad"], m["frais"])
        r.comparer(NOM_LIGNES, sujet + " (TVA)", x["tva_mad"], m["tva"])
        r.comparer(NOM_LIGNES, sujet + " (coût)", x["revient_mad"], m["mad"] + m["frais"])
        if m["kg"]:
            r.comparer(
                NOM_LIGNES,
                sujet + " (coût au kilo)",
                x["revient_kg"],
                (m["mad"] + m["frais"]) / m["kg"],
                1e-4,
            )
    r.juger(
        NOM_LIGNES, f"{d['numero']} (nombre de marchandises)", len(fiche["lignes"]) == len(dossier)
    )


def _ecarts_de_facture(a: Acces, r: Releve) -> None:
    """L'écart de facture : montant − Σ valeur en devise, si tout est dans sa devise."""
    recu = somme_par(
        a.sql(
            "SELECT l.dossier_id, l.valeur_devise FROM dossier_ligne l JOIN dossier d "
            "ON d.id = l.dossier_id JOIN facture f ON f.id = d.facture_id WHERE l.devise = f.devise"
        )
    )
    for d in a.get("/dossiers", limite=5000)["elements"]:
        e = d.get("ecart_facture")
        if d["statut"] == "annule" or not e:
            continue
        r.comparer(NOM_TVA, d["numero"] + " (reçu facturé)", e["recu"], recu.get(d["id"], 0.0))
        r.comparer(
            NOM_TVA,
            d["numero"] + " (écart de facture)",
            e["ecart"],
            e["montant"] - recu.get(d["id"], 0.0),
        )


def _controles(
    a: Acces,
    r: Releve,
    lignes: dict[int, list[dict[str, Any]]],
    frais: list[Any],
    reglages: dict[str, Any],
) -> None:
    """C29 (TVA saisie hors de la tolérance de l'attendue) et C36 (facture hors tolérance de
    la marchandise reçue ; une facture sans montant ou une marchandise dans une autre devise
    se disent aussi), recomptés sur les dossiers non annulés."""
    tol_tva = float(reglages.get("toler_tva_import", 0.05))
    tol_fac = float(reglages.get("toler_facture_import", 0.02))
    c29 = c36 = 0
    factures = {
        did: (m, dev)
        for did, m, dev in a.sql(
            "SELECT d.id, f.montant, f.devise FROM dossier d JOIN facture f ON f.id = d.facture_id "
            "WHERE d.statut <> 'annule'"
        )
    }
    devises: dict[int, list[tuple[str, float]]] = defaultdict(list)
    for did, dev, valeur in a.sql("SELECT dossier_id, devise, valeur_devise FROM dossier_ligne"):
        devises[did].append((dev, valeur))
    for (did,) in a.sql("SELECT id FROM dossier WHERE statut <> 'annule'"):
        dossier, siens = lignes.get(did, []), [x for x in frais if x[0] == did]
        saisie = sum(m for _, _, nature, _, m in siens if nature == "tva")
        if dossier and saisie:  # sans TVA saisie, rien à rapprocher
            attendue = _attendue(dossier, siens, reglages)
            c29 += abs(saisie - attendue) > abs(attendue) * tol_tva
        if did not in factures or not devises.get(did):
            continue
        montant, devise = factures[did]
        recues = devises[did]
        if not montant or any(d != devise for d, _ in recues):
            c36 += 1  # facture sans montant, marchandise dans une autre devise : à vérifier
            continue
        recu = sum(v for _, v in recues)
        ecart = montant - recu
        c36 += abs(ecart) > 0.005 and abs(ecart / recu if recu else 1.0) > tol_fac
    controles = {c["code"]: c["anomalies"] for c in a.get("/controles")["controles"]}
    nom = "Contrôles C01–C38 recomptés en SQL (nombre d'anomalies)"
    r.juger(
        nom, "C29", controles.get("C29") == c29, f"écran {controles.get('C29')}, recompté {c29}"
    )
    r.juger(
        nom, "C36", controles.get("C36") == c36, f"écran {controles.get('C36')}, recompté {c36}"
    )
