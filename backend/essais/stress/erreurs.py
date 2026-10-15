"""Les erreurs humaines, chaque semaine : une date dans le futur, une date trop ancienne, une
écriture dans la période close, un bon envoyé deux fois (version périmée), une réception
validée deux fois, une sortie plus grande que le stock, un lot inconnu, un rôle qui sort de ses
droits, deux postes qui modifient la même fiche, un second inventaire sur un magasin déjà compté.

Chacune **doit** être refusée (4xx clair) : un 2xx est un refus manquant, un 5xx une erreur.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from essais.stress.achats_commandes import bons_ouverts
from essais.stress.monde import Monde
from essais.stress.socle import EchecGeste


def erreurs_humaines(m: Monde) -> None:
    """Deux ou trois erreurs tirées au hasard parmi celles de la semaine."""
    gestes = [
        date_future,
        date_ancienne,
        periode_close,
        version_perimee,
        double_validation,
        plus_que_le_stock,
        lot_inconnu,
        hors_droits,
        deux_postes,
        inventaire_en_double,
    ]
    for geste in m.echantillon(gestes, m.entier(2, 3)):
        try:
            geste(m)
            m.journal.geste("erreurs humaines jouées")
        except EchecGeste as e:
            m.journal.note(f"  · erreur humaine non jouable : {e}")


def _un_lot(m: Monde) -> dict[str, Any] | None:
    lots = [x for x in m.L.get("/lots?non_nuls=true") if float(x["disponible"]) > 0]
    return m.choix(lots) if lots else None


def _magasin_du_lot(lot: dict[str, Any]) -> int:
    return next(
        x["magasin_id"]
        for x in lot["magasins"]
        if x["type"] == "stock_courant" and float(x["quantite"]) > 0
    )


def date_future(m: Monde) -> None:
    """Un ordre daté de demain : refusé (une sortie se saisit le jour où elle a lieu)."""
    lot = _un_lot(m)
    if lot is None:
        return
    corps = {
        "date": (m.jour + timedelta(days=1)).isoformat(),
        "magasin_id": _magasin_du_lot(lot),
        "lignes": [
            {"lot_id": lot["lot_id"], "quantite": 1, "unite": "kg", "matiere_id": lot["matiere_id"]}
        ],
    }
    r = m.L.refus("POST", "/ordres", corps, 422, 201, note="erreur : date future")
    if r.statut == 201:  # le brouillon peut s'enregistrer ; c'est la validation qui refuse
        r2 = m.L.refus(
            "POST",
            f"/ordres/{r.corps['id']}/valider",
            {"version": r.corps["version"]},
            409,
            422,
            note="erreur : date future (validation)",
        )
        version = (
            r2.corps.get("version", r.corps["version"])
            if isinstance(r2.corps, dict)
            else r.corps["version"]
        )
        m.L.appeler("DELETE", f"/ordres/{r.corps['id']}?version={version}", None, (200, 204, 409))


def date_ancienne(m: Monde) -> None:
    """Une opération datée de 2006 (faute de frappe) : refusée."""
    lot = _un_lot(m)
    if lot is None:
        return
    corps = {
        "type": "ajustement",
        "date": "2006-03-01",
        "motif_id": m.catalogue.motifs["Perte / casse"],
        "valider": True,
        "lignes": [
            {
                "matiere_id": lot["matiere_id"],
                "lot_id": lot["lot_id"],
                "magasin_id": _magasin_du_lot(lot),
                "quantite": -1,
                "unite": "kg",
            }
        ],
    }
    m.A.refus("POST", "/operations", corps, 422, 409, note="erreur : date 2006")


def periode_close(m: Monde) -> None:
    """Un transfert daté dans la période close : refusé."""
    limite = m.A.get("/contexte")["date_cloture"]
    lot = _un_lot(m)
    if not limite or lot is None or len(m.catalogue.courants) < 2:
        return
    depart = _magasin_du_lot(lot)
    arrivee = next(c for c in m.catalogue.courants if c != depart)
    corps = {
        "type": "transfert",
        "date": limite,
        "motif_id": m.catalogue.motifs["Rangement"],
        "valider": True,
        "lignes": [
            {
                "matiere_id": lot["matiere_id"],
                "lot_id": lot["lot_id"],
                "magasin_id": depart,
                "magasin_destination_id": arrivee,
                "quantite": 1,
                "unite": "kg",
            }
        ],
    }
    m.L.refus("POST", "/operations", corps, 409, 422, note="erreur : période close")


def version_perimee(m: Monde) -> None:
    """Le bon est modifié sur un poste, puis un autre poste renvoie l'ancienne version : 409."""
    bons = [b for b in bons_ouverts(m) if b["statut"] in ("envoyee", "confirmee")]
    if not bons:
        return
    bon = m.A.get(f"/commandes/{m.choix(bons)['id']}")
    corps = (
        {"version": bon["version"]}
        | {k: bon["expedition"][k] for k in ("conteneur",)}
        | {"navire": "MSC Essai"}
    )
    m.A.put(f"/commandes/{bon['id']}/expedition", corps)
    m.A.refus(
        "PUT",
        f"/commandes/{bon['id']}/expedition",
        corps | {"navire": "Autre"},
        409,
        note="erreur : version périmée",
    )


def double_validation(m: Monde) -> None:
    """Une réception déjà validée, validée de nouveau avec son ancienne version : refusée."""
    page = m.A.get("/receptions?statut=validee&limite=20")
    if not page["elements"]:
        return
    rec = m.choix(page["elements"])
    m.A.refus(
        "POST",
        f"/receptions/{rec['id']}/valider",
        {"version": max(1, rec["version"] - 1)},
        409,
        422,
        note="erreur : double validation",
    )


def plus_que_le_stock(m: Monde) -> None:
    """Une sortie plus grande que ce que le lot a : le brouillon l'annonce, la validation refuse."""
    lot = _un_lot(m)
    if lot is None:
        return
    corps = {
        "date": m.iso,
        "magasin_id": _magasin_du_lot(lot),
        "lignes": [
            {
                "lot_id": lot["lot_id"],
                "quantite": round(float(lot["disponible"]) * 3 + 10, 1),
                "unite": "kg",
                "matiere_id": lot["matiere_id"],
            }
        ],
    }
    r = m.L.appeler("POST", "/ordres", corps, (201, 422), note="erreur : plus que le stock")
    if r.statut == 201:
        if not r.corps["blocages"]:
            m.journal.anomalie(
                "PROBABLE",
                "refus_manquant",
                "brouillon d'ordre au-delà du stock sans blocage annoncé",
                route="POST /ordres",
                role="alimentation",
                statut=201,
            )
        r2 = m.L.refus(
            "POST",
            f"/ordres/{r.corps['id']}/valider",
            {"version": r.corps["version"]},
            409,
            422,
            note="erreur : plus que le stock (validation)",
        )
        version = (
            r2.corps.get("version", r.corps["version"])
            if isinstance(r2.corps, dict)
            else r.corps["version"]
        )
        m.L.appeler("DELETE", f"/ordres/{r.corps['id']}?version={version}", None, (200, 204, 409))


def lot_inconnu(m: Monde) -> None:
    """Un lot qui n'existe pas dans un ordre : refusé clairement."""
    corps = {
        "date": m.iso,
        "magasin_id": m.catalogue.courants[0],
        "lignes": [{"lot_id": 999999, "quantite": 5, "unite": "kg"}],
    }
    m.L.refus("POST", "/ordres", corps, 422, 404, note="erreur : lot inconnu")


def hors_droits(m: Monde) -> None:
    """L'alimentation lit la valorisation, les achats approuvent, l'atelier passe un bon : 403."""
    m.L.refus("GET", "/valorisation", None, 403, note="droits : alimentation → valorisation")
    m.L.refus("GET", "/plan-achat", None, 403, note="droits : alimentation → plan d'achat")
    bons = [b for b in bons_ouverts(m) if b["statut"] == "a_approuver"]
    if bons:
        m.A.refus(
            "POST",
            f"/commandes/{bons[0]['id']}/approuver",
            {"version": bons[0]["version"]},
            403,
            note="droits : achats approuvent",
        )
    m.L.refus(
        "POST",
        "/commandes",
        {"fournisseur_id": 1, "lignes": [{"matiere_id": 1, "quantite": 10}]},
        403,
        note="droits : alimentation commande",
    )


def deux_postes(m: Monde) -> None:
    """Deux postes modifient la même réclamation : le second, avec la version lue avant, est
    refusé."""
    ouvertes = m.A.get("/reclamations?statut=ouverte")
    if not ouvertes:
        return
    rc = ouvertes[0]
    m.A.put(
        f"/reclamations/{rc['id']}",
        {"version": rc["version"], "reponse": f"Relance envoyée le {m.iso}."},
    )
    m.D.refus(
        "PUT",
        f"/reclamations/{rc['id']}",
        {"version": rc["version"], "reponse": "Autre réponse."},
        409,
        note="erreur : deux postes",
    )


def inventaire_en_double(m: Monde) -> None:
    """Un second inventaire ouvert sur un magasin déjà en comptage : refusé ; le premier est
    abandonné ensuite (il n'était là que pour l'essai)."""
    a = m.A
    magasin = m.catalogue.courants[0]
    premier = a.appeler(
        "POST",
        "/inventaires",
        {"date": m.iso, "magasin_id": magasin, "libelle": "comptage éclair"},
        (201, 409),
        note="inventaire (essai doublon)",
    )
    if premier.statut != 201:
        return
    a.refus(
        "POST",
        "/inventaires",
        {"date": m.iso, "magasin_id": magasin, "libelle": "doublon"},
        409,
        note="erreur : inventaire en double",
    )
    a.appeler(
        "POST",
        f"/inventaires/{premier.corps['id']}/abandonner",
        {"version": premier.corps["version"], "motif": "essai"},
        (200,),
        note="abandon",
    )
