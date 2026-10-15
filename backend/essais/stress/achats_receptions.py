"""Les achats, côté réceptions : les camions des bons arrivés (un bon ou deux du même
fournisseur), lignes non livrées laissées vides (second camion plus tard), lots du fournisseur ou
internes, pesées avec écarts dans et hors tolérance, lignes sous réserve (quarantaine) et refusées,
factures saisies avec la réception ou complétées après validation ; brouillons repris, modifiés ou
supprimés ; réclamations ouvertes puis closes ; quarantaines libérées ou renvoyées au fournisseur.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from essais.stress.achats_commandes import bons_ouverts
from essais.stress.monde import Monde
from essais.stress.socle import CREE, SUPPRIME, EchecGeste


def _due(bon: dict[str, Any]) -> date | None:
    eta = bon["expedition"]["eta"] if bon.get("expedition") else None
    texte = eta or bon.get("date_livraison_prevue")
    return date.fromisoformat(texte[:10]) if texte else None


def camions_de_la_semaine(m: Monde) -> None:
    """Un à trois camions : chacun apporte un bon (ou deux du même fournisseur) dont l'arrivée
    est due — en retard parfois, en avance rarement."""
    dus: dict[int, list[dict[str, Any]]] = {}
    for b in bons_ouverts(m):
        due = _due(b)
        if b["statut"] != "confirmee" or float(b["reste_kg"]) <= 0 or due is None:
            continue
        retard = (m.jour - due).days
        if retard >= 0 or (retard >= -4 and m.chance(0.2)):
            dus.setdefault(b["fournisseur_id"], []).append(b)
    camions = list(dus.values())
    m.hasard.shuffle(camions)
    for bons in camions[: m.entier(1, 3)]:
        try:
            receptionner(m, bons[:2])
        except EchecGeste:
            continue


def _prefixe(nom: str) -> str:
    return "".join(x[0] for x in nom.split()[:2]).upper() or "LOT"


def _ligne_livree(m: Monde, bon: dict[str, Any], lg: dict[str, Any]) -> list[dict[str, Any]]:
    """Une ligne de bon livrée, en un à trois lots pesés ; qualité et magasin décidés au quai."""
    fiche = m.matiere(lg["matiere_id"])
    reste = float(lg["reste"])
    part = m.choix([1.0, 1.0, 1.0, 1.0, 1.0, m.entre(0.5, 0.95), 1.0 + m.entre(0.0, 0.03)])
    total = round(reste * part, 1)
    nb_lots = 1 if total < 2000 or m.chance(0.5) else m.entier(2, 3)
    poids_bobine = float(fiche.get("poids_bobine") or 0)
    par_palette = float(fiche.get("bobines_palette") or 0)
    lignes = []
    for _ in range(nb_lots):
        bl = round(total / nb_lots, 1)
        ecart = m.entre(-0.02, 0.015) if m.chance(0.9) else m.entre(-0.06, -0.03)
        pesee = round(bl * (1 + ecart), 1)
        if poids_bobine > 0 and par_palette > 0:
            bobines = round(pesee / poids_bobine)
            palettes, en_plus = divmod(bobines, int(par_palette))
        else:
            palettes, en_plus = 0, 0
        tirage = m.hasard.random()
        qualite = "conforme" if tirage < 0.9 else ("reserve" if tirage < 0.96 else "refuse")
        magasin = m.catalogue.quarantaine if qualite == "reserve" else _magasin_courant(m)
        m.journal.geste("lots reçus")
        interne = m.chance(0.1)
        numero = (
            f"{_prefixe(bon['fournisseur'])}-{m.jour:%y%m%d}-{m.journal.volumes['lots reçus']:04d}"
        )
        lignes.append(
            {
                "commande_ligne_id": lg["id"],
                "matiere_id": lg["matiere_id"],
                "lot_numero": "" if interne else numero,
                "lot_interne": interne,
                "quantite_bl": bl,
                "quantite_pesee": pesee,
                "nb_palettes": palettes,
                "bobines_en_plus": en_plus,
                "magasin_id": magasin,
                "qualite": qualite,
                "observations": {
                    "reserve": "humidité à contrôler",
                    "refuse": "bobines tachées",
                }.get(qualite, ""),
            }
        )
    return lignes


def _magasin_courant(m: Monde) -> int:
    courants = m.catalogue.courants
    return courants[0] if m.chance(0.7) or len(courants) == 1 else courants[1]


def receptionner(m: Monde, bons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Un camion : les lignes des bons (livrées ou laissées vides), les factures par devise,
    une réception par devise ; validée tout de suite le plus souvent, brouillon sinon."""
    a = m.A
    lignes: list[dict[str, Any]] = []
    factures: dict[str, dict[str, Any]] = {}
    for resume in bons:
        bon = a.get(f"/commandes/{resume['id']}")
        premier_camion = float(bon["recu"]) == 0
        du_bon = [x for x in bon["lignes"] if float(x["reste"]) > 0]
        montant = 0.0
        for lg in du_bon:
            if premier_camion and len(du_bon) > 1 and m.chance(0.3):
                lignes.append({"commande_ligne_id": lg["id"], "matiere_id": lg["matiere_id"]})
                continue
            nouvelles = _ligne_livree(m, bon, lg)
            lignes += nouvelles
            montant += sum(float(x["quantite_bl"]) * float(lg["prix"]) for x in nouvelles)
        if montant > 0 and m.chance(0.7):
            factures[bon["devise"]] = {
                "numero": f"INV-{m.jour:%y%m}-{bon['id']}{m.entier(10, 99)}",
                "date": (m.jour - timedelta(days=m.entier(1, 5))).isoformat(),
                "montant": round(montant * m.entre(0.995, 1.01), 2),
            }
    if not lignes:
        return []
    corps = {
        "date": m.iso,
        "fournisseur_id": bons[0]["fournisseur_id"],
        "numero_bl": f"BL-{m.jour:%y%m%d}-{m.entier(100, 999)}",
        "controle_par": m.choix(["Rachid", "Hamid", "Soumia"]),
        "observations": m.choix(["", "Camion complet.", "Deux palettes abîmées en haut."]),
        "factures": factures,
        "lignes": lignes,
    }
    recues = a.post("/receptions", corps, CREE, note="camion")
    m.journal.geste("réceptions", len(recues))
    for rec in recues:
        if m.chance(0.85):
            valider_reception(m, rec["id"])
    return list(recues)


def valider_reception(m: Monde, rid: int) -> dict[str, Any] | None:
    """Les achats valident ; un blocage annoncé (excédent, pesée à zéro) se corrige d'abord."""
    a = m.A
    fiche = a.get(f"/receptions/{rid}")
    if fiche["blocages"]:
        fiche = _corriger_brouillon(m, fiche)
        if fiche is None:
            return None
    r = a.appeler(
        "POST", f"/receptions/{rid}/valider", {"version": fiche["version"]}, note="validée"
    )
    if r.ok:
        m.journal.geste("réceptions validées")
        return dict(r.corps)
    return None


def _corriger_brouillon(m: Monde, fiche: dict[str, Any]) -> dict[str, Any] | None:
    """Le blocage lu sur le brouillon : les quantités sont ramenées au bon (excédent), sinon le
    brouillon est supprimé (consigné comme geste humain, pas comme anomalie)."""
    a = m.A
    corps = _corps_de(fiche)
    for lg in corps["lignes"]:
        lg["quantite_bl"] = round(float(lg["quantite_bl"]) * 0.93, 1)
        lg["quantite_pesee"] = round(float(lg["quantite_pesee"]) * 0.93, 1)
    r = a.appeler("PUT", f"/receptions/{fiche['id']}", corps, note="brouillon corrigé")
    if r.ok and not r.corps["blocages"]:
        m.journal.geste("brouillons de réception corrigés")
        return dict(r.corps)
    version = r.corps["version"] if r.ok else fiche["version"]
    a.appeler(
        "DELETE", f"/receptions/{fiche['id']}?version={version}", None, SUPPRIME, note="abandon"
    )
    m.journal.geste("brouillons de réception supprimés")
    m.journal.note(f"  · brouillon de réception {fiche['id']} abandonné : {fiche['blocages'][:2]}")
    return None


def _corps_de(fiche: dict[str, Any]) -> dict[str, Any]:
    """Le brouillon tel que l'écran le renverrait (modification)."""
    lignes = [
        {
            "commande_ligne_id": x["commande_ligne_id"],
            "matiere_id": x["matiere_id"],
            "lot_numero": x["lot_numero"] if not x["lot_interne"] else "",
            "lot_interne": x["lot_interne"],
            "quantite_bl": x["quantite_bl"],
            "quantite_pesee": x["quantite_pesee"],
            "nb_palettes": x["nb_palettes"],
            "bobines_en_plus": x["bobines_en_plus"],
            "magasin_id": x["magasin_id"],
            "qualite": x["qualite"],
            "observations": x["observations"],
        }
        for x in fiche["lignes"]
    ]
    factures = {}
    if fiche["facture"]:
        f = fiche["facture"]
        factures[fiche["devise"]] = {
            "numero": f["numero"],
            "date": f["date"],
            "montant": f["montant"],
        }
    return {
        "date": fiche["date"],
        "fournisseur_id": fiche["fournisseur_id"],
        "numero_bl": fiche["numero_bl"],
        "controle_par": fiche["controle_par"],
        "observations": fiche["observations"],
        "factures": factures,
        "lignes": lignes,
        "version": fiche["version"],
    }


def suites_des_receptions(m: Monde) -> None:
    """Chaque jour : brouillons repris, factures complétées, réclamations, quarantaines."""
    _brouillons(m)
    _factures_completees(m)
    _reclamations(m)
    _quarantaines(m)


def _brouillons(m: Monde) -> None:
    for x in m.D.get("/brouillons")["receptions"]:
        age = (m.jour - date.fromisoformat(x["date"][:10])).days if x.get("date") else 1
        if age < 1 or m.chance(0.4):
            continue
        if m.chance(0.15):
            m.A.appeler("DELETE", f"/receptions/{x['id']}?version={x['version']}", None, SUPPRIME)
            m.journal.geste("brouillons de réception supprimés")
            continue
        fiche = m.A.get(f"/receptions/{x['id']}")
        corps = _corps_de(fiche)
        corps["controle_par"] = "Soumia"
        corps["date"] = m.iso
        r = m.A.appeler("PUT", f"/receptions/{x['id']}", corps, note="brouillon repris")
        if r.ok:
            m.journal.geste("brouillons de réception modifiés")
            valider_reception(m, x["id"])


def _factures_completees(m: Monde) -> None:
    du = (m.jour - timedelta(days=12)).isoformat()
    page = m.A.get(f"/receptions?statut=validee&facture=sans&du={du}&au={m.iso}&limite=50")
    for x in page["elements"]:
        if not m.chance(0.4):
            continue
        fiche = m.A.get(f"/receptions/{x['id']}")
        montant = sum(float(lg["quantite_bl"]) * float(lg["prix"]) for lg in fiche["lignes"])
        if montant <= 0:
            continue
        corps = {
            "version": fiche["version"],
            "numero": f"INV-{m.jour:%y%m}-{x['id']}",
            "date": (m.jour - timedelta(days=m.entier(0, 6))).isoformat(),
            "montant": round(montant * m.entre(0.99, 1.02), 2),
        }
        m.A.appeler("PUT", f"/receptions/{x['id']}/facture", corps, note="facture complétée")
        m.journal.geste("factures complétées après validation")


def _reclamations(m: Monde) -> None:
    a = m.A
    du = (m.jour - timedelta(days=20)).isoformat()
    page = a.get(f"/receptions?statut=validee&qualite=refus&du={du}&au={m.iso}&limite=50")
    for x in page["elements"]:
        if x["nb_refus"] == 0 or not m.chance(0.5):
            continue
        fiche = a.get(f"/receptions/{x['id']}")
        if fiche["reclamations"]:
            continue
        refusee = next(lg for lg in fiche["lignes"] if lg["qualite"] == "refuse")
        corps = {
            "fournisseur_id": fiche["fournisseur_id"],
            "reception_id": fiche["id"],
            "reception_ligne_id": refusee["id"],
            "motif": m.choix(m.catalogue.reclamation_motifs),
            "description": f"Lot {refusee['lot_numero'] or 'interne'} refusé au quai "
            "(taches, bobines écrasées).",
            "quantite": refusee["quantite_pesee"],
            "montant_demande": round(float(refusee["quantite_pesee"]) * float(refusee["prix"]), 2),
            "devise": fiche["devise"],
            "ouverte_le": m.iso,
        }
        a.appeler("POST", "/reclamations", corps, CREE, note="réclamation")
        m.journal.geste("réclamations ouvertes")
    for ouverte in a.get("/reclamations?statut=ouverte"):
        if (m.jour - date.fromisoformat(ouverte["ouverte_le"])).days < 5 or not m.chance(0.3):
            continue
        rc = a.put(
            f"/reclamations/{ouverte['id']}",
            {"version": ouverte["version"], "reponse": "Avoir accordé."},
        )
        issue = m.choix(m.catalogue.reclamation_issues)
        corps = {
            "version": rc["version"],
            "issue": issue,
            "montant_obtenu": round(
                float(rc["montant_demande"]) * m.choix([1.0, 1.0, 0.5, 0.0]), 2
            ),
            "close_le": m.iso,
        }
        a.appeler("POST", f"/reclamations/{rc['id']}/clore", corps, note="réclamation close")
        m.journal.geste("réclamations closes")


def _quarantaines(m: Monde) -> None:
    """Les lots en quarantaine depuis trois jours : libérés (achats) ou renvoyés au fournisseur."""
    a = m.A
    quarantaine = m.catalogue.quarantaine
    for lot in a.get(f"/lots?magasin={quarantaine}&non_nuls=true"):
        age = (m.jour - date.fromisoformat(lot["entre_le"])).days
        if age < 3 or not m.chance(0.35):
            continue
        en_quarantaine = next(
            (float(x["quantite"]) for x in lot["magasins"] if x["magasin_id"] == quarantaine), 0.0
        )
        if en_quarantaine <= 0:
            continue
        ligne = {
            "matiere_id": lot["matiere_id"],
            "lot_id": lot["lot_id"],
            "magasin_id": quarantaine,
            "quantite": en_quarantaine,
            "unite": "kg",
        }
        if m.chance(0.75):
            corps = {
                "type": "transfert",
                "date": m.iso,
                "motif_id": m.catalogue.motifs["Libération de quarantaine"],
                "commentaire": "Contrôle d'humidité conforme.",
                "valider": True,
                "lignes": [ligne | {"magasin_destination_id": _magasin_courant(m)}],
            }
            a.appeler("POST", "/operations", corps, CREE, note="libération")
            m.journal.geste("libérations de quarantaine")
        else:
            corps = {
                "type": "retour_fournisseur",
                "date": m.iso,
                "fournisseur_id": lot.get("fournisseur_id"),
                "motif_id": m.catalogue.motifs["Refus après quarantaine"],
                "commentaire": "Humidité hors norme : renvoyé.",
                "valider": True,
                "lignes": [
                    ligne
                    | {"quantite": math.floor(en_quarantaine * m.choix([1.0, 0.5]) * 1000) / 1000}
                ],
            }
            a.appeler("POST", "/operations", corps, CREE, note="retour fournisseur")
            m.journal.geste("retours au fournisseur")
