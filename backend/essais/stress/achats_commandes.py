"""Les achats, côté commandes : plan d'achat lu, bons tirés de la proposition (une à trois
fois par semaine), envoi, approbation de la direction au-delà du seuil (renvoi parfois),
confirmation des prix (au mètre pour le cuir, en deux fois parfois), jalons d'expédition.

Le catalogue de Mohamed n'est jamais réécrit : `mettre_a_jour_catalogue` n'est vrai que pour
une matière « (stress) ».
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from essais.stress.monde import Monde
from essais.stress.socle import CREE, EchecGeste

STATUTS_OUVERTS = ("envoyee", "a_approuver", "confirmee")


def commandes_de_la_semaine(m: Monde) -> None:
    """Les achats lisent le plan d'achat et passent un à trois bons (fournisseurs les plus
    presses d'abord), chacun envoyé, approuvé s'il le faut."""
    a = m.A
    plan = a.get("/plan-achat")
    fournisseurs = [f for f in plan["fournisseurs"] if f["nb_references"] > 0]
    fournisseurs.sort(key=lambda f: (-f["ruptures"], -f["critiques"], -f["montant_mad"]))
    presses = fournisseurs[:6]
    for f in m.echantillon(presses, m.entier(1, 3)):
        try:
            bons = bon_depuis_le_plan(m, f["fournisseur_id"])
        except EchecGeste:
            continue
        for bon in bons:
            envoyer_et_approuver(m, bon["id"])


def bon_depuis_le_plan(m: Monde, fid: int) -> list[dict[str, Any]]:
    """Un bon (un par devise) tiré de la proposition du fournisseur : 2 à 8 lignes, quantités
    de départ arrondies à la main, parfois réduites ou un peu augmentées."""
    a = m.A
    prep = a.get(f"/plan-achat/fournisseurs/{fid}")
    candidates = [x for x in prep["lignes"] if float(x["depart"]["quantite"]) > 0]
    candidates.sort(key=lambda x: float(x["stock_projete"]))
    choisies = candidates[: m.entier(2, 8)]
    if not choisies:
        return []
    lignes = []
    for x in choisies:
        d = x["depart"]
        quantite = float(d["quantite"])
        if m.chance(0.3):
            quantite = max(float(d["contenance"]), round(quantite * m.entre(0.7, 1.15)))
        if d["unite"] != "kg":
            contenance = float(d["contenance"])
            quantite = max(contenance, round(quantite / contenance) * contenance)
        lignes.append(
            {
                "matiere_id": x["matiere_id"],
                "quantite": quantite,
                "unite_achat": d["unite"],
                "contenance": d["contenance"],
            }
        )
    delai = int(prep["delai_jours"] or 60)
    promesse = m.jour + timedelta(days=delai + m.entier(-5, 10))
    corps = {
        "fournisseur_id": fid,
        "date_livraison_prevue": promesse.isoformat(),
        "observations": m.choix(["", "Livraison groupée si possible.", "Urgent : rupture."]),
        "lignes": lignes,
    }
    bons = a.post("/commandes", corps, CREE, note="bon tiré du plan")
    m.journal.geste("commandes", len(bons))
    return list(bons)


def envoyer_et_approuver(m: Monde, cid: int) -> dict[str, Any]:
    """Les achats envoient ; au-delà du seuil la direction approuve (après un renvoi, parfois)."""
    a, d = m.A, m.D
    bon = a.get(f"/commandes/{cid}")
    bon = a.post(f"/commandes/{cid}/envoyer", {"version": bon["version"], "date": m.iso})
    if bon["statut"] != "a_approuver":
        return dict(bon)
    m.journal.geste("approbations demandées")
    if m.chance(0.15):
        motif = m.choix(["Revoir la teinte avec l'atelier", "Trop tôt : stock suffisant ce mois"])
        bon = d.post(f"/commandes/{cid}/renvoyer", {"version": bon["version"], "motif": motif})
        m.journal.geste("renvois de la direction")
        bon = a.post(f"/commandes/{cid}/envoyer", {"version": bon["version"], "date": m.iso})
    bon = d.post(f"/commandes/{cid}/approuver", {"version": bon["version"], "date": m.iso})
    m.journal.geste("approbations")
    return dict(bon)


def bons_ouverts(m: Monde) -> list[dict[str, Any]]:
    """Les bons envoyés, à approuver ou confirmés (ce qui attend encore quelque chose)."""
    ouverts: list[dict[str, Any]] = []
    for statut in STATUTS_OUVERTS:
        ouverts += m.A.get(f"/commandes?statut={statut}&limite=200")["elements"]
    return ouverts


def confirmer_les_prix(m: Monde) -> None:
    """Les achats confirment les prix des bons partis depuis un ou deux jours : tout d'un coup
    le plus souvent, en deux fois parfois ; au mètre pour une matière au mètre ; une hausse
    forte repasse par la direction."""
    a, d = m.A, m.D
    for resume in bons_ouverts(m):
        if resume["statut"] != "envoyee" or resume["prix_a_confirmer"] == 0:
            continue
        age = (m.jour - _date(resume["date_commande"])).days
        if age < 1 or (age < 4 and m.chance(0.5)):
            continue
        bon = a.get(f"/commandes/{resume['id']}")
        a_faire = [x for x in bon["lignes"] if not x["prix_confirme"]]
        if len(a_faire) > 1 and m.chance(0.3):
            a_faire = a_faire[: len(a_faire) // 2]
        lignes = []
        catalogue_a_jour = False
        for x in a_faire:
            fiche = m.matiere(x["matiere_id"])
            prix = round(float(x["prix_catalogue"] or x["prix"] or 1) * m.entre(0.97, 1.08), 4)
            if m.chance(0.03):
                prix = round(prix * 1.25, 4)  # une vraie hausse : la direction revoit le bon
            unite = "ml" if fiche.get("unite_prix") == "ml" else "kg"
            lignes.append({"ligne_id": x["id"], "prix": prix, "unite": unite})
            catalogue_a_jour = catalogue_a_jour or m.catalogue.de_stress(fiche)
        corps = {
            "version": bon["version"],
            "lignes": lignes,
            "mettre_a_jour_catalogue": catalogue_a_jour,
        }
        if bon["date_livraison_prevue"] is None:
            corps["date_livraison_prevue"] = (m.jour + timedelta(days=60)).isoformat()
        r = a.appeler("POST", f"/commandes/{bon['id']}/prix", corps, note="prix confirmés")
        m.journal.geste("confirmations de prix")
        if r.ok and r.corps["statut"] == "a_approuver":
            d.post(
                f"/commandes/{bon['id']}/approuver", {"version": r.corps["version"], "date": None}
            )
            m.journal.geste("approbations")


def jalons_d_expedition(m: Monde) -> None:
    """Une semaine après la confirmation, les achats notent la proforma, l'embarquement, l'ETA
    et le conteneur ; plus tard l'arrivée au port et le dédouanement."""
    a = m.A
    for resume in bons_ouverts(m):
        if resume["statut"] != "confirmee" or resume["pays"] in ("MAROC", "Maroc"):
            continue
        exp = resume["expedition"]
        promesse = (
            _date(resume["date_livraison_prevue"]) if resume["date_livraison_prevue"] else None
        )
        if promesse is None:
            continue
        corps: dict[str, Any] = {"version": resume["version"]}
        if not exp["embarquee_le"] and (promesse - m.jour).days <= 35:
            corps |= {
                "proforma_le": (m.jour - timedelta(days=m.entier(5, 12))).isoformat(),
                "embarquee_le": m.iso,
                "eta": (promesse + timedelta(days=m.entier(-3, 6))).isoformat(),
                "conteneur": f"{m.choix(['MSKU', 'TGHU', 'CMAU'])}{m.entier(1000000, 9999999)}",
                "navire": m.choix(["", "MSC Tanger", "Maersk Cadiz"]),
            }
        elif (
            exp["embarquee_le"]
            and not exp["au_port_le"]
            and exp["eta"]
            and m.jour >= _date(exp["eta"])
        ):
            corps |= {"au_port_le": m.iso}
        elif exp["au_port_le"] and not exp["dedouanee_le"] and m.chance(0.5):
            corps |= {"dedouanee_le": m.iso}
        else:
            continue
        a.appeler("PUT", f"/commandes/{resume['id']}/expedition", corps, note="jalon")
        m.journal.geste("jalons d'expédition")


def _date(texte: str) -> Any:
    from datetime import date

    return date.fromisoformat(texte[:10])
