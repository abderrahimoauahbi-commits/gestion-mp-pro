"""Les importations, chaque mois : dossiers ouverts depuis les factures étrangères reçues (une ou
deux factures du même fournisseur par dossier), cours payé à la douane, frais au taux (droits
2,5 %, TPI 0,25 %, TVA 20 %) avec le montant arrondi à la main comme la douane, fret et assurance
au montant, parfois un frais porté sur une seule marchandise, clôture ; et les règlements de
l'échéancier (factures et frais échus).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from essais.stress.monde import SUFFIXE, Monde
from essais.stress.socle import CREE, EchecGeste

BANQUES = ["Attijariwafa Bank", "BMCI", "BMCE Bank", "CIH"]


def dossiers_du_mois(m: Monde) -> None:
    """Un à quatre dossiers pour les factures étrangères sans dossier ; les dossiers restés
    ouverts le mois d'avant sont clos."""
    a = m.A
    groupes: dict[int, list[dict[str, Any]]] = {}
    for f in a.get("/factures?sans_dossier=true"):
        if f["devise"] == "MAD" or not f["receptions"]:
            continue
        if any(r["statut"] != "validee" for r in f["receptions"]):
            continue
        groupes.setdefault(f["fournisseur_id"], []).append(f)
    candidats = sorted(groupes.values(), key=lambda g: g[0]["recue_le"] or "")
    for groupe in candidats:
        reste = list(groupe)
        while reste:
            taille = 2 if len(reste) > 1 and m.chance(0.4) else 1
            factures, reste = reste[:taille], reste[taille:]
            try:
                ouvrir_dossier(m, factures)
            except EchecGeste:
                continue
    for d in a.get("/dossiers?statut=ouvert&limite=50")["elements"]:
        fiche = a.get(f"/dossiers/{d['id']}")
        if fiche["nb_frais"] > 0 and m.chance(0.7):
            _cloturer(m, fiche)


def ouvrir_dossier(m: Monde, factures: list[dict[str, Any]]) -> dict[str, Any]:
    """Le dossier d'un arrivage : factures, cours payé, frais, clôture (le plus souvent)."""
    a = m.A
    premiere = factures[0]
    arrivee = premiere["recue_le"] or m.iso
    corps = {
        "facture_id": premiere["id"],
        "libelle": f"Arrivage {premiere['fournisseur']} {date.fromisoformat(arrivee):%m/%Y}",
        "date_arrivee": arrivee,
        "banque": m.choix(BANQUES),
        "commentaire": "",
    }
    r = a.appeler("POST", "/dossiers", corps, (201, 409), note="dossier ouvert")
    if r.statut == 409 and r.code == "cout_periode_close":
        rouvrir_la_periode(m, factures)
        r = a.appeler("POST", "/dossiers", corps, CREE, note="dossier ouvert (période rouverte)")
    if not r.ok:
        raise EchecGeste(r, f"dossier refusé : {r.detail}")
    d = r.corps
    m.journal.geste("dossiers d'importation")
    for f in factures[1:]:
        r = a.appeler(
            "POST",
            f"/dossiers/{d['id']}/factures",
            {"version": d["version"], "facture_id": f["id"]},
            (200, 201, 409),
            note="seconde facture",
        )
        if r.ok:
            d = r.corps
            m.journal.geste("factures ajoutées à un dossier")
        else:  # période close d'un autre mois : elle aura son propre dossier le mois prochain
            m.journal.geste("secondes factures laissées pour un autre dossier")
    d = _cours_payes(m, d)
    d = _frais(m, d)
    if m.chance(0.8):
        d = _cloturer(m, d) or d
    return dict(d)


def rouvrir_la_periode(m: Monde, factures: list[dict[str, Any]]) -> None:
    """La facture est arrivée après la clôture du mois de son camion : la direction rouvre la
    période jusqu'à la veille de l'entrée (c'est tracé), le dossier se fait, la clôture du mois
    en cours la refermera."""
    entrees = [r["date"] for f in factures for r in f["receptions"] if r.get("date")]
    if not entrees:
        return
    veille = (date.fromisoformat(min(entrees)) - timedelta(days=1)).isoformat()
    version = next(x["version"] for x in m.D.get("/parametres") if x["cle"] == "date_cloture")
    corps = {
        "date_cloture": veille,
        "motif": "Facture arrivée après la clôture : dossier",
        "version": version,
    }
    r = m.D.appeler("PUT", "/periode-close", corps, (200,), note="période rouverte")
    if r.ok:
        m.journal.geste("périodes rouvertes pour un dossier")


def _cours_payes(m: Monde, d: dict[str, Any]) -> dict[str, Any]:
    """Le cours payé à la banque pour chaque devise du dossier (proche du cours du jour)."""
    cours_jour = {x["code"]: float(x["cours"]) for x in m.A.get("/devises")}
    for devise in sorted({x["devise"] for x in d["lignes"] if x["devise"] != "MAD"}):
        cours = round(cours_jour.get(devise, 10.0) * m.entre(0.985, 1.02), 4)
        d = m.A.put(
            f"/dossiers/{d['id']}/cours",
            {"devise": devise, "cours": cours, "version": d["version"]},
            note="cours payé",
        )
    return dict(d)


def _un_frais(
    m: Monde, d: dict[str, Any], code: str, montant: float, **champs: Any
) -> dict[str, Any]:
    poste = m.catalogue.postes_frais.get(code)
    if poste is None:
        return d
    corps = {"version": d["version"], "poste_id": poste["id"], "montant": montant} | champs
    r = m.A.appeler("POST", f"/dossiers/{d['id']}/frais", corps, (200, 201), note=f"frais {code}")
    if r.ok:
        m.journal.geste("frais de dossier")
        return dict(r.corps)
    return d


def _frais(m: Monde, d: dict[str, Any]) -> dict[str, Any]:
    """Fret et assurance au montant ; droits, TPI et TVA au taux, montant arrondi comme la douane
    (au dirham) ; un frais « (stress) » parfois, porté sur une marchandise parfois."""
    marchandise = float(d["marchandise_mad"])
    if marchandise <= 0:
        return d
    piece = {
        "prestataire": "Transit Tanger Med",
        "date_piece": m.iso,
        "echeance": (m.jour + timedelta(days=30)).isoformat(),
    }
    fret = round(marchandise * m.entre(0.02, 0.045), 2)
    assurance = round(marchandise * 0.003, 2)
    d = _un_frais(m, d, "FRET", fret, piece=f"FR-{m.entier(1000, 9999)}", **piece)
    if m.chance(0.7):
        d = _un_frais(m, d, "ASSUR", assurance, piece=f"AS-{m.entier(100, 999)}", **piece)
    else:
        assurance = 0.0
    douane = marchandise + fret + assurance
    droits = float(round(douane * 0.025))
    tpi = round(douane * 0.0025, 2)
    tva = float(round((douane + droits + tpi) * 0.20))
    dum = {
        "piece": f"DUM-{m.jour:%y}-{m.entier(10000, 99999)}",
        "prestataire": "Douane",
        "date_piece": m.iso,
        "echeance": m.iso,
    }
    d = _un_frais(m, d, "DD", droits, taux=2.5, **dum)
    d = _un_frais(m, d, "TPI", tpi, taux=0.25, **dum)
    d = _un_frais(m, d, "TVA", tva, taux=20, **dum)
    stress = [
        c for c, p in m.catalogue.postes_frais.items() if SUFFIXE in str(p.get("libelle", ""))
    ]
    if stress and m.chance(0.5):
        ligne = d["lignes"][0]["id"] if d["lignes"] and m.chance(0.5) else None
        d = _un_frais(
            m, d, stress[0], round(m.entre(300, 2500), 2), ligne_id=ligne, prestataire="Divers"
        )
    return d


def _cloturer(m: Monde, d: dict[str, Any]) -> dict[str, Any] | None:
    r = m.A.appeler(
        "POST",
        f"/dossiers/{d['id']}/cloturer",
        {"version": d["version"], "alertes_lues": True},
        note="dossier clos",
    )
    if r.ok:
        m.journal.geste("dossiers clos")
        return dict(r.corps)
    return None


def regler_echeances(m: Monde) -> None:
    """Les achats règlent la plupart des échéances échues (factures et frais) ; quelques-unes
    attendent (retard réel), celles sans date sont datées à l'occasion."""
    a = m.A
    du = (m.jour - timedelta(days=400)).isoformat()
    ech = a.get(f"/echeancier?du={du}&au={m.iso}")
    for x in ech["lignes"]:
        if x.get("payee_le") or not x.get("date") or x["date"] > m.iso or not m.chance(0.7):
            continue
        genre = x["objet"] if x["objet"] in ("facture", "frais") else x["genre"]
        corps = {"genre": genre, "id": x["id"], "payee_le": m.iso, "version": x["version"]}
        r = a.appeler("PUT", "/echeancier/paiement", corps, note="règlement")
        if r.ok:
            m.journal.geste("règlements")
