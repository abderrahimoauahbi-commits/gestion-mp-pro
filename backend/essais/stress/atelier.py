"""L'atelier au téléphone (alimentation) : deux à six ordres de sortie par jour vers les
machines (selon la recette, FIFO proposé puis repris à la main : bobines entières, plusieurs
lots, un excédent parfois ; hors recette parfois), retours des machines, annulations rares,
montages et démontages de fils sur les quatre métiers, transferts entre magasins, besoins
signalés (traités par les achats), scan de lot.
"""

from __future__ import annotations

import math
import re
from datetime import timedelta
from typing import Any

from essais.stress.monde import Monde
from essais.stress.socle import CREE, SUPPRIME, EchecGeste

_EFFET = re.compile(r"métiers ([+−-])\s*([\d\s  ]+(?:,\d+)?) kg au lieu de")


def ordres_du_jour(m: Monde, samedi: bool) -> None:
    """Les ordres de la journée, puis les brouillons d'hier, les retours, les annulations."""
    for _ in range(m.entier(1, 2) if samedi else m.entier(2, 6)):
        try:
            un_ordre(m)
        except EchecGeste:
            continue
    brouillons_d_ordres(m)
    retours_des_machines(m)
    annulations(m)


def _qualite_du_jour(m: Monde) -> dict[str, Any]:
    """Une qualité tirée au poids de son plan du mois (les grosses séries plus souvent)."""
    qualites = [
        q
        for q in m.catalogue.qualites.values()
        if float(q.get("base_mensuelle") or 0) > 0
        and (q.get("recette_conforme", True) or m.chance(0.05))
    ]
    poids = [
        float(q["base_mensuelle"])
        * float((q.get("saisonnalite") or [1] * 12)[m.jour.month - 1] or 0)
        for q in qualites
    ]
    if not qualites or sum(poids) <= 0:
        return m.choix(list(m.catalogue.qualites.values()))
    return m.hasard.choices(qualites, weights=poids, k=1)[0]


def _lignes_proposees(m: Monde, prop: dict[str, Any]) -> list[dict[str, Any]]:
    """La proposition FIFO reprise comme à l'écran : bobines entières, kilos arrondis."""
    lignes = []
    for lp in prop["lignes"]:
        poids_bobine = float(lp["poids_bobine"] or 0)
        for lot in lp["lots"]:
            propose, dispo = float(lot["propose"]), float(lot["disponible"])
            if propose <= 0:
                continue
            if poids_bobine > 0:
                bobines = min(
                    math.floor(dispo / poids_bobine), max(1, round(propose / poids_bobine))
                )
                if bobines < 1:
                    continue
                ligne = {"lot_id": lot["lot_id"], "quantite": bobines, "unite": "bobine"}
            else:
                kilos = round(min(propose, dispo), 3)
                if kilos <= 0:
                    continue
                ligne = {"lot_id": lot["lot_id"], "quantite": kilos, "unite": "kg"}
            lignes.append(ligne | {"matiere_id": lp["matiere_id"]})
    return lignes


def un_ordre(m: Monde) -> None:
    """Un ordre selon la recette (ou hors recette, une fois sur dix) : proposition, lignes,
    brouillon, validation (neuf fois sur dix)."""
    atl = m.L
    magasin = m.catalogue.courants[0] if m.chance(0.7) else m.choix(m.catalogue.courants)
    metier = m.choix(list(m.catalogue.metiers))
    if m.chance(0.1):
        _ordre_hors_recette(m, magasin, metier)
        return
    q = _qualite_du_jour(m)
    coef = float((q.get("saisonnalite") or [1] * 12)[m.jour.month - 1] or 1)
    m2 = max(10, round(float(q["base_mensuelle"]) * coef / 80 * m.entre(0.5, 1.5)))
    demande = {
        "date": m.iso,
        "magasin_id": magasin,
        "metier_id": metier,
        "qualites": [{"qualite_id": q["id"], "m2": m2}],
    }
    prop = atl.post("/ordres/proposition", demande)
    if float(prop["manque"]) > 0:
        couverture = (float(prop["prevu"]) - float(prop["manque"])) / max(
            float(prop["prevu"]), 1e-9
        )
        if couverture < 0.3:
            m.journal.geste("ordres non lancés (stock insuffisant)")
            return
        demande["qualites"][0]["m2"] = m2 = max(10, round(m2 * couverture * 0.9))
        prop = atl.post("/ordres/proposition", demande)
    lignes = _lignes_proposees(m, prop)
    if not lignes:
        m.journal.geste("ordres non lancés (stock insuffisant)")
        return
    if m.chance(0.1) and lignes[0]["unite"] == "kg":
        lignes[0]["quantite"] = round(float(lignes[0]["quantite"]) * 1.04, 1)  # un peu d'excédent
    corps = demande | {
        "commentaire": m.choix(["", "série du matin", "fin de rouleau"]),
        "lignes": lignes,
    }
    _creer_et_valider(m, corps)


def _ordre_hors_recette(m: Monde, magasin: int, metier: int) -> None:
    """Un ordre hors recette : un ou deux lots pris en magasin, sans qualité."""
    lots = [
        x for x in m.L.get(f"/lots?magasin={magasin}&non_nuls=true") if float(x["disponible"]) > 0
    ]
    if not lots:
        return
    lignes = []
    for lot in m.echantillon(lots, m.entier(1, 2)):
        en_magasin = next(
            (float(x["quantite"]) for x in lot["magasins"] if x["magasin_id"] == magasin), 0.0
        )
        kilos = round(min(en_magasin, float(lot["disponible"])) * m.entre(0.05, 0.3), 1)
        if kilos <= 0:
            continue
        lignes.append(
            {
                "lot_id": lot["lot_id"],
                "quantite": kilos,
                "unite": "kg",
                "matiere_id": lot["matiere_id"],
            }
        )
    if lignes:
        corps = {
            "date": m.iso,
            "magasin_id": magasin,
            "metier_id": metier,
            "commentaire": "hors recette : essai",
            "lignes": lignes,
        }
        _creer_et_valider(m, corps)
        m.journal.geste("ordres hors recette")


def _creer_et_valider(m: Monde, corps: dict[str, Any]) -> None:
    atl = m.L
    o = atl.post("/ordres", corps, CREE, note="ordre")
    m.journal.geste("ordres")
    if o["blocages"]:
        _consigner_blocage(m, o)
        atl.appeler("DELETE", f"/ordres/{o['id']}?version={o['version']}", None, SUPPRIME)
        return
    if m.chance(0.9):
        r = atl.appeler(
            "POST", f"/ordres/{o['id']}/valider", {"version": o["version"]}, note="ordre validé"
        )
        if r.ok:
            m.journal.geste("ordres validés")


def _consigner_blocage(m: Monde, o: dict[str, Any]) -> None:
    """Un ordre bloqué à la saisie : une recette de Mohamed qui oublie un rôle (C01) se consigne
    une fois comme question métier, jamais corrigée par une donnée ; le reste est noté."""
    texte = " | ".join(o["blocages"][:2])
    if "aucune matière" in texte and m.journal.volumes["blocages recette (C01) consignés"] == 0:
        m.journal.anomalie(
            "QUESTION METIER",
            "controle_referentiel",
            texte,
            route="POST /ordres",
            role="alimentation",
            statut=201,
        )
    if "aucune matière" in texte:
        m.journal.geste("blocages recette (C01) consignés")
        return
    m.journal.note(f"  · ordre {o['id']} bloqué à la saisie : {texte[:200]} — supprimé")
    m.journal.geste("ordres bloqués à la saisie")


def brouillons_d_ordres(m: Monde) -> None:
    """Les brouillons d'ordres d'hier : validés par l'atelier, ou supprimés."""
    for x in m.L.get("/brouillons")["ordres"]:
        if x.get("date") == m.iso and m.chance(0.7):
            continue
        if m.chance(0.2) or x.get("blocages"):
            m.L.appeler("DELETE", f"/ordres/{x['id']}?version={x['version']}", None, SUPPRIME)
            m.journal.geste("brouillons d'ordres supprimés")
            continue
        fiche = m.L.get(f"/ordres/{x['id']}")
        r = m.L.appeler(
            "POST",
            f"/ordres/{x['id']}/valider",
            {"version": fiche["version"]},
            (200, 409),
            note="brouillon validé",
        )
        if r.ok:
            m.journal.geste("ordres validés")
        elif r.statut == 409:
            m.L.appeler("DELETE", f"/ordres/{x['id']}?version={fiche['version']}", None, SUPPRIME)
            m.journal.geste("brouillons d'ordres abandonnés (lot épuisé entre-temps)")


def retours_des_machines(m: Monde) -> None:
    """Un ordre sur quatre rend quelque chose le lendemain : des bobines entières, ou des kilos."""
    atl = m.L
    hier = (m.jour - timedelta(days=2)).isoformat()
    page = atl.get(f"/ordres?statut=valide&du={hier}&au={m.iso}&limite=50")
    for o in page["elements"]:
        if o["retours"] or not m.chance(0.1):
            continue
        sortis = [
            x
            for x in atl.get(f"/ordres/{o['id']}/lots-sortis")
            if float(x["sorti_net"]) > 0 and not x["blocage"]
        ]
        if not sortis:
            continue
        x = m.choix(sortis)
        poids_bobine = float(x["poids_bobine"] or 0)
        if poids_bobine > 0 and float(x["sorti_net"]) >= 2 * poids_bobine:
            ligne = {
                "quantite": m.entier(1, min(3, int(float(x["sorti_net"]) // poids_bobine))),
                "unite": "bobine",
            }
        else:
            ligne = {
                "quantite": round(float(x["sorti_net"]) * m.entre(0.02, 0.08), 1),
                "unite": "kg",
            }
        if float(ligne["quantite"]) <= 0:
            continue
        corps = {
            "type": "retour_machine",
            "date": m.iso,
            "ordre_id": o["id"],
            "motif_id": m.catalogue.motifs[
                m.choix(["Reliquat de fin d'ordre", "Changement de série / arrêt machine"])
            ],
            "valider": True,
            "lignes": [
                ligne
                | {
                    "matiere_id": x["matiere_id"],
                    "lot_id": x["lot_id"],
                    "magasin_id": o["magasin_id"],
                }
            ],
        }
        r = atl.appeler("POST", "/operations", corps, CREE, note="retour machine")
        if r.ok:
            m.journal.geste("retours des machines")


def annulations(m: Monde) -> None:
    """Un ordre sur cinquante est annulé le jour même ou le lendemain (série arrêtée)."""
    hier = (m.jour - timedelta(days=1)).isoformat()
    for o in m.L.get(f"/ordres?statut=valide&du={hier}&au={m.iso}&limite=50")["elements"]:
        if m.chance(0.02):
            r = m.L.appeler(
                "POST",
                f"/ordres/{o['id']}/annuler",
                {"version": o["version"], "motif": "série arrêtée"},
                note="ordre annulé",
            )
            if r.ok:
                m.journal.geste("ordres annulés")


def _effet_annonce(detail: str) -> float | None:
    trouve = _EFFET.search(detail)
    if not trouve:
        return None
    nombre = float(re.sub(r"[\s  ]", "", trouve.group(2)).replace(",", "."))
    return -nombre if trouve.group(1) in "−-" else nombre


def montage(m: Monde) -> None:
    """Un étage d'un métier : démonté (deux fois sur cinq s'il est garni), ou garni de un à trois
    fils de poil (mètres ≤ laize, remplissage 50–100 %) ; l'effet est calculé comme l'écran."""
    atl = m.L
    metier_id = m.choix(list(m.catalogue.metiers))
    fiche = atl.get(f"/metiers/{metier_id}")
    etage = m.entier(1, int(fiche["etages"]))
    detail = fiche["etages_detail"][etage - 1]
    actuels = [f for f in fiche["fils"] if f["etage"] == etage]
    fils: list[dict[str, Any]] = []
    if not (actuels and m.chance(0.4)):
        refs = {
            x["matiere_id"]: x
            for x in atl.get("/montage/matieres")
            if float(x["poids_bobine_compte"] or 0) > 0
        }
        poils = [
            mid
            for mid, x in refs.items()
            if m.matiere(mid).get("role") == "Poil" and float(x["sorti_30_j"]) > 0
        ]
        if not poils:
            poils = [mid for mid in refs if m.matiere(mid).get("role") == "Poil"]
        reste = float(fiche["laize"])
        for mid in m.echantillon(poils, m.entier(1, 3)):
            metres = round(min(reste, m.entre(0.3, 1.6)), 2)
            if metres <= 0:
                break
            reste -= metres
            fils.append(
                {"matiere_id": mid, "metres": metres, "pourcentage": m.choix([100, 100, 80, 50])}
            )
    densite = float(fiche["bobines_par_metre"])
    comptes = {
        x["matiere_id"]: float(x["poids_bobine_compte"] or 0) for x in atl.get("/montage/matieres")
    }
    nouveau = sum(
        f["metres"] * densite * comptes.get(f["matiere_id"], 0) * f["pourcentage"] / 100
        for f in fils
    )
    effet = round(nouveau - float(detail["poids"]), 3)
    corps = {"version": detail["version"], "fils": fils, "confirme_effet_kg": effet}
    r = atl.appeler(
        "PUT", f"/metiers/{metier_id}/etages/{etage}", corps, (200, 409), note="montage"
    )
    if r.statut == 409 and r.code == "effet_change":
        annonce = _effet_annonce(r.detail)
        if annonce is not None:
            r = atl.appeler(
                "PUT",
                f"/metiers/{metier_id}/etages/{etage}",
                corps | {"confirme_effet_kg": annonce},
                note="montage reconfirmé",
            )
            m.journal.geste("montages reconfirmés après effet changé")
    if r.ok:
        m.journal.geste("démontages" if not fils else "montages")


def transferts(m: Monde) -> None:
    """Un lot change de magasin (rangement) : par l'atelier le plus souvent, les achats parfois."""
    courants = m.catalogue.courants
    if len(courants) < 2:
        return
    depart = m.choix(courants)
    arrivee = m.choix([c for c in courants if c != depart])
    lots = [
        x for x in m.L.get(f"/lots?magasin={depart}&non_nuls=true") if float(x["disponible"]) > 0
    ]
    if not lots:
        return
    lot = m.choix(lots)
    en_magasin = next(
        (float(x["quantite"]) for x in lot["magasins"] if x["magasin_id"] == depart), 0.0
    )
    quantite = math.floor(en_magasin * m.choix([1.0, 0.5, 0.25]) * 1000) / 1000
    if quantite <= 0:
        return
    corps = {
        "type": "transfert",
        "date": m.iso,
        "motif_id": m.catalogue.motifs["Rangement"],
        "commentaire": "",
        "valider": m.chance(0.9),
        "lignes": [
            {
                "matiere_id": lot["matiere_id"],
                "lot_id": lot["lot_id"],
                "magasin_id": depart,
                "magasin_destination_id": arrivee,
                "quantite": quantite,
                "unite": "kg",
            }
        ],
    }
    poste = m.L if m.chance(0.7) else m.A
    r = poste.appeler("POST", "/operations", corps, CREE, note="transfert")
    if r.ok:
        m.journal.geste("transferts")


def signalement(m: Monde) -> None:
    """L'atelier signale un besoin ; les achats ou la direction traitent ceux d'hier."""
    poils = [mid for mid, x in m.catalogue.matieres.items() if x.get("role") == "Poil"]
    corps = {
        "matiere_id": m.choix(poils) if poils and m.chance(0.8) else None,
        "texte": m.choix(
            [
                "Il manque du rouge 2900 pour demain",
                "Plus de jute 30/1 au magasin 2",
                "Bobines humides, lot à contrôler",
            ]
        ),
        "urgence": m.choix(["normale", "normale", "urgente"]),
    }
    r = m.L.appeler("POST", "/signalements", corps, CREE, note="besoin signalé")
    if r.ok:
        m.journal.geste("besoins signalés")


def traiter_signalements(m: Monde) -> None:
    """Les achats (ou la direction) répondent aux besoins signalés de la veille."""
    for x in m.A.get("/signalements?a_traiter=true&limite=50")["elements"]:
        if x["quand"][:10] == m.iso and m.chance(0.6):
            continue
        poste = m.A if m.chance(0.8) else m.D
        r = poste.appeler(
            "POST",
            f"/signalements/{x['id']}/traiter",
            {"reponse": m.choix(["Commandé, arrive jeudi.", "Pris sur le magasin 2.", "Vu."])},
            note="besoin traité",
        )
        if r.ok:
            m.journal.geste("besoins traités")


def scan(m: Monde) -> None:
    """L'atelier scanne l'étiquette d'un lot (connu, ou inconnu une fois sur dix)."""
    lots = m.L.get("/lots?non_nuls=true")
    if lots and not m.chance(0.1):
        code = m.choix(lots)["lot"]
        m.L.appeler("GET", f"/lots/scan?code={code}", None, (200,), note="scan")
    else:
        m.L.appeler("GET", "/lots/scan?code=INCONNU-000", None, (200, 404), note="scan inconnu")
    m.journal.geste("scans de lot")
