"""Les rendez-vous du calendrier : fin de mois (dossiers, règlements, inventaire tournant,
ajustement, brouillons de la période, clôture, lectures de la direction, invariants), fin de
trimestre (référentiels d'essai « (stress) » ajoutés, prix et recettes changés sur eux seuls,
cours des devises), fin d'année (plan des qualités d'essai refait, croissance, unité de titrage,
comptes, sauvegarde et restauration à part, exports et documents de l'année, contrôles lus).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from essais.stress import importations, verifications
from essais.stress.monde import SUFFIXE, Monde
from essais.stress.socle import CREE, SUPPRIME, EchecGeste, fin_de_mois

MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def fin_du_mois(m: Monde, mois: date, dates_v1: int) -> None:
    """Le premier jour ouvré du mois suivant : tout ce que l'usine fait pour clore `mois`."""
    dernier = fin_de_mois(mois)
    m.journal.note(f"\n### Clôture de {MOIS[mois.month - 1]} {mois.year} (jouée le {m.iso})")
    for geste in (
        importations.dossiers_du_mois,
        importations.regler_echeances,
        inventaire_tournant,
        ajustement,
    ):
        try:
            geste(m)
        except EchecGeste as e:
            m.journal.note(f"  · geste interrompu : {e}")
    cloture(m, dernier)
    lectures_de_direction(m, mois)
    verifications.controler(m, dates_v1)


def inventaire_tournant(m: Monde) -> None:
    """Les achats comptent deux à cinq matières d'un magasin (celles que l'ABC dit de recompter),
    recomptent ce qui dépasse la tolérance, la direction valide ; un comptage sur vingt est
    abandonné."""
    a, d = m.A, m.D
    magasin = m.choix(m.catalogue.courants)
    a_compter = a.get(f"/inventaires/a-compter?magasin={magasin}")
    choisies = [x["article_id"] for x in a_compter[: m.entier(2, 5)]]
    if not choisies:
        return
    inv = a.post(
        "/inventaires",
        {
            "date": m.iso,
            "magasin_id": magasin,
            "libelle": f"Tournant {m.jour:%m/%Y}",
            "criteres": {"matieres": choisies},
        },
        CREE,
        note="inventaire ouvert",
    )
    m.journal.geste("inventaires")
    if m.chance(0.05):
        a.post(
            f"/inventaires/{inv['id']}/abandonner",
            {"version": inv["version"], "motif": "comptage reporté"},
        )
        m.journal.geste("inventaires abandonnés")
        return
    lignes = []
    for x in inv["lignes"]:
        theorique = float(x["theorique"])
        compte = round(
            theorique * (1 + (m.entre(-0.015, 0.015) if m.chance(0.85) else m.entre(-0.06, 0.04))),
            1,
        )
        ligne: dict[str, Any] = {"ligne_id": x["id"], "compte": max(0.0, compte)}
        if abs(compte - theorique) > 0.5:
            ligne["justification"] = m.choix(
                ["bobines entamées", "une palette oubliée", "poussière de pesée"]
            )
        lignes.append(ligne)
    inv = a.put(
        f"/inventaires/{inv['id']}/comptages", {"version": inv["version"], "lignes": lignes}
    )
    seconds = [
        {
            "ligne_id": x["id"],
            "second_compte": round(float(x["theorique"]) * (1 + m.entre(-0.01, 0.01)), 1),
            "justification": "recompté à deux",
        }
        for x in inv["lignes"]
        if x["a_recompter"]
    ]
    if seconds:
        inv = d.put(
            f"/inventaires/{inv['id']}/comptages", {"version": inv["version"], "lignes": seconds}
        )
        m.journal.geste("recomptages")
    if m.chance(0.1) and inv["magasin_id"]:
        corps = {
            "version": inv["version"],
            "matiere_id": choisies[0],
            "lot_interne": True,
            "magasin_id": inv["magasin_id"],
            "compte": round(m.entre(5, 60), 1),
            "justification": "lot retrouvé sans étiquette",
        }
        r = a.appeler(
            "POST", f"/inventaires/{inv['id']}/lots-trouves", corps, (200, 201), note="lot trouvé"
        )
        if r.ok:
            inv = r.corps
            m.journal.geste("lots trouvés à l'inventaire")
    r = d.appeler(
        "POST",
        f"/inventaires/{inv['id']}/valider",
        {"version": inv["version"]},
        note="inventaire validé",
    )
    if r.ok:
        m.journal.geste("inventaires validés")
        m.journal.note(
            f"  · inventaire {inv['numero']} : écart {r.corps['ecart_total']} kg "
            f"sur {inv['nb_lignes']} lots"
        )


def ajustement(m: Monde) -> None:
    """Une perte ou casse justifiée sur un lot, par les achats."""
    lots = [x for x in m.A.get("/lots?non_nuls=true") if float(x["disponible"]) > 5]
    if not lots or m.chance(0.3):
        return
    lot = m.choix(lots)
    mag = next(
        (x for x in lot["magasins"] if x["type"] == "stock_courant" and float(x["quantite"]) > 5),
        None,
    )
    if mag is None:
        return
    corps = {
        "type": "ajustement",
        "date": m.iso,
        "motif_id": m.catalogue.motifs["Perte / casse"],
        "commentaire": "Bobine tombée du chariot.",
        "valider": True,
        "lignes": [
            {
                "matiere_id": lot["matiere_id"],
                "lot_id": lot["lot_id"],
                "magasin_id": mag["magasin_id"],
                "quantite": -round(min(float(mag["quantite"]) * 0.01 + 1, 20), 1),
                "unite": "kg",
            }
        ],
    }
    r = m.A.appeler("POST", "/operations", corps, CREE, note="ajustement")
    if r.ok:
        m.journal.geste("ajustements")


def cloture(m: Monde, dernier: date) -> None:
    """La direction clôt la période : les brouillons datés de la période sont d'abord validés
    (« Tout valider ») ou supprimés par leur rôle ; un refus 409 est repris une fois."""
    d = m.D
    attente = d.get(f"/periode-close/brouillons?date={dernier.isoformat()}")
    if attente["total"]:
        d.appeler("POST", "/brouillons/valider", {"tous": True}, (200,), note="tout valider")
        _supprimer_brouillons(m)
    version = next(x["version"] for x in d.get("/parametres") if x["cle"] == "date_cloture")
    corps = {
        "date_cloture": dernier.isoformat(),
        "motif": f"Clôture de {MOIS[dernier.month - 1]}",
        "version": version,
    }
    r = d.appeler("PUT", "/periode-close", corps, (200, 409), note="clôture")
    if r.statut == 409:
        _supprimer_brouillons(m)
        version = next(x["version"] for x in d.get("/parametres") if x["cle"] == "date_cloture")
        r = d.appeler(
            "PUT", "/periode-close", corps | {"version": version}, note="clôture (2e essai)"
        )
    if r.ok:
        m.journal.geste("clôtures de période")
        m.journal.note(f"  ✓ période close jusqu'au {dernier:%d/%m/%Y}")


def _supprimer_brouillons(m: Monde) -> None:
    b = m.D.get("/brouillons")
    for x in b["receptions"]:
        m.A.appeler("DELETE", f"/receptions/{x['id']}?version={x['version']}", None, SUPPRIME)
    for x in b["ordres"]:
        m.L.appeler("DELETE", f"/ordres/{x['id']}?version={x['version']}", None, SUPPRIME)
    for x in b["operations"]:
        m.D.appeler("DELETE", f"/operations/{x['id']}?version={x['version']}", None, SUPPRIME)
    n = len(b["receptions"]) + len(b["ordres"]) + len(b["operations"])
    if n:
        m.journal.geste("brouillons supprimés avant clôture", n)


def lectures_de_direction(m: Monde, mois: date) -> None:
    """Ce que la direction et les achats regardent en début de mois (durées mesurées)."""
    d, a = m.D, m.A
    cle = f"{mois.year}-{mois.month:02d}"
    for chemin in (
        f"/bilan?mois={cle}",
        "/cockpit",
        f"/documents/bilan?mois={cle}",
        "/controles",
        "/valorisation",
        "/stock",
        "/plan-achat",
        "/production/realise",
        "/production/besoins",
        "/opportunites",
        "/prix/matrice",
        "/analyse/revient",
    ):
        d.appeler("GET", chemin, None, (200,), note="lecture du mois")
    d.appeler("POST", "/indicateurs/photographier", {}, (200, 201), note="photo")
    d.appeler("GET", "/courriel/apercu", None, (200,), note="courriel")
    notes = d.get("/notifications?non_lues=true&limite=200")
    if notes["elements"]:
        d.appeler("POST", "/notifications/lues", {}, (200, 204), note="notifications lues")
    a.appeler("GET", "/fournisseurs/performance", None, (200,), note="performance")
    a.appeler(
        "GET",
        f"/export/receptions?du={mois.isoformat()}&au={fin_de_mois(mois).isoformat()}",
        None,
        (200,),
        note="export Excel",
    )
    m.journal.geste("lectures de fin de mois")


# --- trimestre ---------------------------------------------------------------------------------


def fin_du_trimestre(m: Monde) -> None:
    """Référentiels d'essai : une matière (au mètre un trimestre sur deux), une qualité et sa
    recette, une version de recette et un prix changés sur les éléments d'essai, une
    désactivation d'essai, un poste de frais, les cours."""
    m.journal.note(f"\n### Trimestre — référentiels d'essai (le {m.iso})")
    n = m.journal.volumes["trimestres"] + 1
    m.journal.geste("trimestres")
    for geste in (
        lambda: nouvelle_matiere(m, n),
        lambda: nouvelle_qualite(m, n),
        lambda: retouches_des_essais(m),
        lambda: nouveau_poste(m, n),
        lambda: cours_des_devises(m),
    ):
        try:
            geste()
        except EchecGeste as e:
            m.journal.note(f"  · geste interrompu : {e}")
    m.lire_catalogue()


def nouvelle_matiere(m: Monde, n: int) -> None:
    """Une matière d'essai : un poil (kg) ou, un trimestre sur deux, un ruban au mètre linéaire."""
    au_metre = n % 2 == 0
    fournisseur = m.choix([f for f in m.catalogue.fournisseurs.values() if f["devise"] == "USD"])
    corps: dict[str, Any] = {
        "reference": (
            f"Ruban PES 25 mm{SUFFIXE} {n}" if au_metre else f"PP FRZ-2900 Dtex-Essai {n}{SUFFIXE}"
        ),
        "designation": "Matière d'essai du simulateur",
        "role_id": m.catalogue.roles["Ruban" if au_metre else "Poil"],
        "unite_prix": "ml" if au_metre else "kg",
        "densite": 0.006 if au_metre else 0,
        "fournisseur_id": fournisseur["id"],
        "prix": 0.05 if au_metre else round(m.entre(1.9, 3.2), 3),
        "devise": "USD",
        "unite_achat": "kg",
        "contenance_achat": 1,
        "poids_bobine": 0 if au_metre else 3.0,
        "bobines_palette": 0 if au_metre else 240,
        "actif": True,
    }
    fiche = m.A.post("/matieres", corps, CREE, note="matière (stress)")
    m.journal.geste("matières (stress) créées")
    m.journal.note(f"  · matière créée : {fiche['reference']}")


def nouvelle_qualite(m: Monde, n: int) -> None:
    """Une qualité d'essai : poids au m², recette sur les matières existantes (une par rôle) et
    les matières d'essai, plan modeste."""
    d = m.D
    roles = m.catalogue.roles
    poids = {"Poil": 1.2, "Trame": 0.6, "Chaîne": 0.2, "Colle": 0.2, "Plastique": 0.03}
    corps = {
        "code": f"ST{n}",
        "nom": f"Qualité essai {n}{SUFFIXE}",
        "actif": True,
        "poids": [{"role_id": roles[r], "poids": p} for r, p in poids.items()],
    }
    q = d.post("/qualites", corps, CREE, note="qualité (stress)")
    lignes = []
    for role in poids:
        candidates = [x for x in m.catalogue.matieres.values() if x.get("role") == role]
        de_stress = [x for x in candidates if m.catalogue.de_stress(x)]
        if role == "Poil" and de_stress:
            lignes += [
                {"matiere_id": de_stress[-1]["id"], "pourcentage": 40},
                {"matiere_id": m.choix(candidates)["id"], "pourcentage": 60},
            ]
        elif candidates:
            lignes.append({"matiere_id": m.choix(candidates)["id"], "pourcentage": 100})
    q = d.put(
        f"/qualites/{q['id']}/recette",
        {"lignes": lignes, "motif": "recette de départ", "version": q["version"]},
    )
    d.put(
        f"/qualites/{q['id']}/plan",
        {
            "base_mensuelle": m.entier(200, 600),
            "coefficients": [1] * 12,
            "motif": "plan de départ",
            "version": q["version"],
        },
    )
    m.journal.geste("qualités (stress) créées")
    m.journal.note(
        f"  · qualité créée : {q['code']} (recette conforme : {q['controle']['conforme']})"
    )


def retouches_des_essais(m: Monde) -> None:
    """Sur les éléments d'essai seulement : un prix catalogue changé, une version de recette, une
    désactivation (la plus ancienne matière d'essai sans recette)."""
    a, d = m.A, m.D
    matieres = [x for x in m.catalogue.matieres.values() if m.catalogue.de_stress(x)]
    if matieres:
        fiche = a.get(f"/matieres/{m.choix(matieres)['id']}")
        corps = {
            k: fiche[k]
            for k in (
                "reference",
                "designation",
                "role_id",
                "composition_id",
                "type_fil_id",
                "titrage_id",
                "couleur_id",
                "couleur_code",
                "unite_prix",
                "densite",
                "fournisseur_id",
                "devise",
                "unite_achat",
                "contenance_achat",
                "minimum_commande",
                "poids_bobine",
                "bobines_palette",
                "stock_min",
                "couv_min_mois",
                "groupe_equiv",
                "priorite_equiv",
                "code_douanier_id",
                "version",
            )
        }
        corps |= {"prix": round(float(fiche["prix"]) * m.entre(0.95, 1.1), 4), "actif": True}
        r = a.appeler("PUT", f"/matieres/{fiche['id']}", corps, note="prix catalogue (stress)")
        if r.ok:
            m.journal.geste("prix catalogue changés (stress)")
        if len(matieres) > 2:
            vieille = a.get(f"/matieres/{matieres[0]['id']}")
            corps = {k: vieille[k] for k in corps if k != "prix"} | {
                "prix": vieille["prix"],
                "actif": False,
                "version": vieille["version"],
            }
            r = a.appeler(
                "PUT",
                f"/matieres/{vieille['id']}",
                corps,
                (200, 409, 422),
                note="désactivation (stress)",
            )
            m.journal.geste(
                "désactivations (stress)" if r.ok else "désactivations refusées (recette)"
            )
    qualites = [q for q in m.catalogue.qualites.values() if m.catalogue.de_stress(q)]
    if qualites:
        q = d.get(f"/qualites/{m.choix(qualites)['id']}")
        lignes = [
            {"matiere_id": x["matiere_id"], "pourcentage": x["pourcentage"]} for x in q["recette"]
        ]
        poils = [x for x in lignes if m.matiere(x["matiere_id"]).get("role") == "Poil"]
        if len(poils) == 2:
            poils[0]["pourcentage"], poils[1]["pourcentage"] = 50, 50
        r = d.appeler(
            "PUT",
            f"/qualites/{q['id']}/recette",
            {"lignes": lignes, "motif": "nouvelle version", "version": q["version"]},
            note="version de recette",
        )
        if r.ok:
            m.journal.geste("versions de recette (stress)")


def nouveau_poste(m: Monde, n: int) -> None:
    """Un poste de frais d'essai (au poids), par la direction."""
    corps = {
        "code": f"STR{n}",
        "libelle": f"Manutention{SUFFIXE} {n}",
        "cle": "poids",
        "nature": "autre",
    }
    r = m.D.appeler("POST", "/postes-frais", corps, CREE, note="poste de frais (stress)")
    if r.ok:
        m.journal.geste("postes de frais (stress)")


def cours_des_devises(m: Monde) -> None:
    """Les achats mettent les cours du trimestre (±3 %)."""
    for fiche in m.A.get("/devises"):
        if fiche["code"] == "MAD":
            continue
        corps = {
            "nom": fiche["nom"],
            "cours": round(float(fiche["cours"]) * m.entre(0.97, 1.03), 4),
            "actif": True,
            "version": fiche["version"],
        }
        m.A.appeler("PUT", f"/devises/{fiche['code']}", corps, note="cours")
        m.journal.geste("cours changés")


# --- année -------------------------------------------------------------------------------------


def fin_d_annee(m: Monde, annee: int) -> None:
    """Janvier : plan des qualités d'essai refait, croissance, unité de titrage, comptes,
    sauvegarde puis restauration à part, exports et documents de l'année passée, contrôles lus."""
    m.journal.note(f"\n### Passage d'année {annee - 1} → {annee} (le {m.iso})")
    for geste in (
        lambda: plan_refait(m),
        lambda: unite_de_titrage(m, annee),
        lambda: comptes(m, annee),
        lambda: sauvegarde(m),
        lambda: exports_de_l_annee(m, annee - 1),
        lambda: controles_lus(m),
    ):
        try:
            geste()
        except EchecGeste as e:
            m.journal.note(f"  · geste interrompu : {e}")


def plan_refait(m: Monde) -> None:
    """Le plan des qualités d'essai : base + 5 %, saisonnalité ; croissance annuelle réglée."""
    d = m.D
    for q in [x for x in m.catalogue.qualites.values() if m.catalogue.de_stress(x)]:
        fiche = d.get(f"/qualites/{q['id']}")
        coefficients = [round(m.entre(0.6, 1.4), 2) for _ in range(12)]
        corps = {
            "base_mensuelle": round(float(fiche["base_mensuelle"]) * 1.05),
            "coefficients": coefficients,
            "motif": "plan de l'année",
            "version": fiche["version"],
        }
        r = d.appeler("PUT", f"/qualites/{q['id']}/plan", corps, note="plan refait")
        if r.ok:
            m.journal.geste("plans refaits (stress)")
    lus = d.get("/parametres")
    version = lus[0]["version_globale"]
    r = d.appeler(
        "PUT",
        "/parametres",
        {"valeurs": {"croissance_annuelle": 0.03}, "version_globale": version},
        note="croissance",
    )
    if r.ok:
        m.journal.geste("réglages changés")


def unite_de_titrage(m: Monde, annee: int) -> None:
    """Une unité de titrage d'essai (achats)."""
    r = m.A.appeler(
        "POST",
        "/classification/unites-titrage",
        {"code": f"Ustr{chr(64 + annee % 26)}", "libelle": f"unité d'essai{SUFFIXE}"},
        CREE,
        note="unité (stress)",
    )
    if r.ok:
        m.journal.geste("unités de titrage (stress)")


def comptes(m: Monde, annee: int) -> None:
    """Un nouveau compte d'atelier ; le code de l'alimentation remis à zéro, puis reconnexion."""
    d = m.D
    r = d.appeler(
        "POST",
        "/utilisateurs",
        {
            "identifiant": f"stress-atelier-{annee}",
            "nom": f"Atelier {annee}{SUFFIXE}",
            "role": "alimentation",
            "code": "2468",
        },
        CREE,
        note="compte atelier",
    )
    if r.ok:
        m.journal.geste("comptes créés")
    ident = next(u["id"] for u in d.get("/utilisateurs") if u["identifiant"] == m.L.identifiant)
    nouveau = f"12{annee % 100:02d}"
    r = d.appeler(
        "POST",
        f"/utilisateurs/{ident}/code",
        {"code": nouveau},
        (200, 204),
        note="code remis à zéro",
    )
    if r.ok:
        m.journal.geste("codes remis à zéro")
        m.L.connecter(nouveau)


def sauvegarde(m: Monde) -> None:
    """La direction sauvegarde ; la sauvegarde est restaurée sur une base à part et comparée."""
    from pathlib import Path

    etat = m.D.post("/sauvegardes", {}, (200, 201), note="sauvegarde")
    m.journal.geste("sauvegardes")
    fichiers = sorted(
        (f for f in etat["fichiers"] if not f["autre_base"]), key=lambda f: f["quand"]
    )
    if not fichiers:
        return
    dernier = fichiers[-1]
    chemin = Path(etat["dossier"]) / dernier["nom"]
    m.journal.note(
        f"  · sauvegarde {dernier['nom']} ({dernier['taille']} o, {dernier['tables']} tables)"
    )
    if chemin.exists():
        verifications.restauration_a_part(m, chemin)


def exports_de_l_annee(m: Monde, annee: int) -> None:
    """Les exports Excel et documents de l'année écoulée (durées mesurées)."""
    du, au = f"{annee}-01-01", f"{annee}-12-31"
    a, d = m.A, m.D
    for chemin in (
        "/export/commandes?statut=clos",
        f"/export/receptions?du={du}&au={au}",
        f"/export/mouvements?du={du}&au={au}&avec_valeur=true",
        f"/export/ordres?du={du}&au={au}",
        "/export/lots",
        f"/export/valorisation?date={au}",
        "/export/dossiers",
        f"/export/echeancier?du={du}&au={au}",
        f"/export/fournisseurs?du={du}&au={au}",
        "/export/inventaires",
        "/export/matieres",
        "/export/plan-achat",
        f"/export/pilotage?date={au}",
        "/export/controles",
        f"/export/prix?du={du}&au={au}",
    ):
        a.appeler("GET", chemin, None, (200,), note="export de l'année")
    d.appeler("GET", f"/export/journal?du={du}&au={au}", None, (200,), note="export du journal")
    for mois in range(1, 13):
        d.appeler(
            "GET", f"/documents/bilan?mois={annee}-{mois:02d}", None, (200,), note="document bilan"
        )
    m.journal.geste("exports de l'année")


def controles_lus(m: Monde) -> None:
    """La direction lit chaque contrôle C01–C38 (liste complète)."""
    d = m.D
    lus = d.get("/controles")
    anomalies = {c["code"]: c["anomalies"] for c in lus["controles"] if c["anomalies"]}
    for c in lus["controles"]:
        d.appeler("GET", f"/controles/{c['code']}?limite=200", None, (200,), note="contrôle lu")
    m.journal.note(
        f"  · contrôles : {lus['synthese']['anomalies']} anomalie(s), "
        f"bloquants {lus['synthese']['bloquants']} — {anomalies}"
    )
    m.journal.geste("contrôles lus", len(lus["controles"]))
