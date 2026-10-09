"""Étape 0 du scénario : comptes, réglages et référentiels du mois (direction, achats).

Lundi 2 novembre 2026. La direction se connecte (compte posé comme par l'installation), crée les
trois autres comptes, règle la société et le seuil d'approbation ; les achats fixent les cours,
créent le fournisseur et les matières ; la direction crée le code douanier, le poste de frais
au poids, les deux qualités (poids, recettes, plan) et le métier. Les refus de rôle sont
vérifiés au passage (un par rôle), et les prix masqués pour l'alimentation.
"""

from __future__ import annotations

from typing import Any

from scenario_monde import COMPTES, Monde
from scenario_outils import MAD

USD, EUR = 10.0, 11.0
"""Cours posés par les achats le 2 novembre (dirhams pour une unité)."""
SEUIL_APPROBATION = 200000
PLAN = {"Q1": 2000, "Q2": 1500}
"""Plans mensuels (m²), saisonnalité plate."""
POIDS = {
    "Q1": {"Poil": 1.2, "Chaîne": 0.3, "Trame": 0.5},
    "Q2": {"Poil": 1.0, "Chaîne": 0.3, "Trame": 0.4},
}
SOCIETE = {
    "nom_entreprise": "Tapis de l'Atlas (scénario)",
    "adresse": "Zone industrielle Sidi Brahim, lot 12",
    "ville": "Fès",
    "telephone": "+212 5 35 00 00 00",
    "banques": "BMCE Bank · Attijariwafa bank",
    "ice": "001234567000089",
}


def comptes(m: Monde) -> None:
    """La direction se connecte et crée les trois autres comptes ; chacun se connecte."""
    v, d = m.verif, m.connecter("D")
    r = m.poste("anonyme").appeler(
        "POST",
        "/installation",
        {"societe": "Autre", "identifiant": "intrus", "nom": "Intrus", "code": "Intrus-2026"},
    )
    v.refus("installation d'une base reprise", r, 409, "deja_installe", "déjà installé")
    for role in ("A", "L", "T"):
        identifiant, nom, libelle, code = COMPTES[role]
        corps = {"identifiant": identifiant, "nom": nom, "role": libelle, "code": code}
        fiche = d.ok("POST", "/utilisateurs", corps, attendu=201)
        v.egal(f"compte {role} : rôle", fiche["role"], libelle)
        v.egal(f"compte {role} : actif", fiche["actif"], True)
        moi = m.connecter(role).get("/moi")
        v.egal(f"compte {role} : voit les prix", moi["voit_prix"], role == "A")
    r = m.A.appeler(
        "POST",
        "/utilisateurs",
        {"identifiant": "z", "nom": "Z", "role": "achats", "code": "Zzzzzzzz1"},
    )
    v.refus("les achats ne créent pas de compte", r, 403, "droit_refuse")


def reglages(m: Monde) -> None:
    """Société (papier à en-tête du bon) et seuil d'approbation, par la direction."""
    v = m.verif
    lus = {r["cle"]: r for r in m.D.get("/parametres")}
    m.avant["reglages"] = {k: r["valeur"] for k, r in lus.items()}
    valeurs: dict[str, Any] = dict(SOCIETE)
    valeurs["seuil_approbation"] = SEUIL_APPROBATION
    corps = {"valeurs": valeurs, "version_globale": next(iter(lus.values()))["version_globale"]}
    r = m.A.appeler("PUT", "/parametres", corps)
    v.refus("les achats ne règlent rien", r, 403, "droit_refuse", "la direction")
    apres = {x["cle"]: x["valeur"] for x in m.D.put("/parametres", corps)}
    v.egal("seuil d'approbation", apres["seuil_approbation"], str(SEUIL_APPROBATION))
    v.egal("raison sociale", apres["nom_entreprise"], SOCIETE["nom_entreprise"])
    r = m.L.appeler("GET", "/parametres")
    v.refus("l'alimentation ne lit aucun réglage", r, 403, "droit_refuse")
    for cle, attendu in (
        ("taux_perte", "0.02"),
        ("taux_tva_import", "0.2"),
        ("taux_tpi_import", "0.0025"),
        ("toler_ecart_pesee", "0.02"),
        ("toler_facture_import", "0.02"),
        ("tolerance_inventaire", "0.02"),
    ):
        v.egal(f"réglage {cle} (calculs du scénario)", apres[cle], attendu)


def devises(m: Monde) -> None:
    """Les achats posent les cours du mois ; l'alimentation n'y a pas accès."""
    v = m.verif
    for code, cours in (("USD", USD), ("EUR", EUR)):
        fiche = next(x for x in m.A.get("/devises") if x["code"] == code)
        corps = {"nom": fiche["nom"], "cours": cours, "actif": True, "version": fiche["version"]}
        apres = m.A.put(f"/devises/{code}", corps)
        v.egal(f"cours {code}", apres["cours"], cours, MAD)
    v.refus("l'alimentation ne lit pas les cours", m.L.appeler("GET", "/devises"), 403)


def _role(m: Monde, code: str) -> int:
    roles = m.D.get("/classification")["roles"]
    return int(next(r["id"] for r in roles if r["code"] == code))


def fournisseur_et_matieres(m: Monde) -> None:
    """Le fournisseur turc (USD et EUR), ses trois matières ; le code douanier, le poste."""
    v, d, a = m.verif, m.D, m.A
    code = d.ok(
        "POST",
        "/codes-douaniers",
        {"code": "5402.33.00", "libelle": "Fils de polyester", "taux_droits": 0.025},
        attendu=201,
    )
    m.ids["code_douanier"] = code["id"]
    v.egal("code douanier : taux", code["taux_droits"], 0.025, 1e-9)
    poste = d.ok(
        "POST",
        "/postes-frais",
        {"code": "ROUTE", "libelle": "Transport routier", "cle": "poids", "nature": "autre"},
        attendu=201,
    )
    m.ids["poste_route"] = poste["id"]
    v.egal("poste routier : clé", poste["cle"], "poids")
    f = a.ok(
        "POST",
        "/fournisseurs",
        {
            "nom": "SCN Iplik Sanayi",
            "pays": "Turkey",
            "devise": "USD",
            "delai_jours": 21,
            "couverture_commande_jours": 30,
            "delai_paiement_jours": 60,
            "incoterm": "FOB",
        },
        attendu=201,
    )
    m.ids["F1"] = f["id"]
    v.egal("fournisseur étranger", f["local"], False)
    matieres = _matieres(m)
    for cle, corps in matieres.items():
        corps |= {
            "fournisseur_id": f["id"],
            "unite_prix": "kg",
            "code_douanier_id": code["id"],
            "actif": True,
        }
        fiche = a.ok("POST", "/matieres", corps, attendu=201)
        m.ids[cle] = fiche["id"]
        v.egal(f"{cle} : prix au kilo", fiche["prix_kg"], corps["prix"], 1e-9)
        v.egal(
            f"{cle} : conditionnement",
            fiche["conditionnement"]["contenance"],
            corps.get("contenance_achat", 1),
            1e-9,
        )
    _vues_restreintes(m, matieres["M2"], f["id"])


def _matieres(m: Monde) -> dict[str, dict[str, Any]]:
    """Les trois matières du scénario (corps de création)."""
    return {
        "M1": {
            "reference": "SCN-POIL-PP-1200",
            "designation": "Poil polypropylène 1200 dtex",
            "role_id": _role(m, "Poil"),
            "prix": 2.5,
            "devise": "USD",
            "unite_achat": "Palette",
            "contenance_achat": 500,
            "poids_bobine": 5,
            "bobines_palette": 100,
        },
        "M2": {
            "reference": "SCN-CHAINE-PES",
            "designation": "Chaîne polyester",
            "role_id": _role(m, "Chaîne"),
            "prix": 3.2,
            "devise": "USD",
        },
        "M3": {
            "reference": "SCN-TRAME-JUTE",
            "designation": "Trame jute",
            "role_id": _role(m, "Trame"),
            "prix": 1.8,
            "devise": "EUR",
            "unite_achat": "Palette",
            "contenance_achat": 400,
            "poids_bobine": 4,
            "bobines_palette": 100,
        },
    }


def _vues_restreintes(m: Monde, corps: dict[str, Any], fournisseur: int) -> None:
    """Ce que l'alimentation et l'administrateur voient (et ne voient pas)."""
    v = m.verif
    v.egal("M1 : palette (5 kg × 100 bobines)", _fiche(m, "M1")["contenance_palette"], 500, 1e-9)
    r = m.L.appeler("POST", "/matieres", corps | {"reference": "SCN-X"})
    v.refus("l'alimentation ne crée pas de matière", r, 403, "droit_refuse")
    vue_l = m.L.get(f"/matieres/{m.ids['M1']}")
    v.egal("alimentation : prix masqué", vue_l["prix"], None)
    v.egal("alimentation : prix au kilo masqué", vue_l["prix_kg"], None)
    v.egal(
        "alimentation : fournisseur réduit au nom et au pays",
        sorted(next(x for x in m.L.get("/fournisseurs") if x["id"] == fournisseur)),
        ["actif", "id", "nom", "pays"],
    )
    v.refus("l'administrateur ne lit pas les matières", m.T.appeler("GET", "/matieres"), 403)


def _fiche(m: Monde, cle: str) -> dict[str, Any]:
    return dict(m.A.get(f"/matieres/{m.ids[cle]}"))


COUT_M2 = {
    # Σ kg/m² × prix au kilo × cours × (1 + perte 2 %)
    "Q1": (1.2 * 2.5 * USD + 0.3 * 3.2 * USD + 0.5 * 1.8 * EUR) * 1.02,  # 49,5 × 1,02 = 50,49
    "Q2": (1.0 * 2.5 * USD + 0.3 * 3.2 * USD + 0.4 * 1.8 * EUR) * 1.02,  # 42,52 × 1,02 = 43,3704
}


def qualites_et_metier(m: Monde) -> None:
    """La direction crée les deux qualités (poids, recette, plan) et le métier."""
    v, d = m.verif, m.D
    for q, poids in POIDS.items():
        corps = {
            "code": f"SCN-{q}",
            "nom": f"Qualité scénario {q}",
            "actif": True,
            "poids": [{"role_id": _role(m, r), "poids": p} for r, p in poids.items()],
        }
        r = m.A.appeler("POST", "/qualites", corps)
        v.refus(
            f"{q} : les achats ne créent pas de qualité", r, 403, "droit_refuse", "la direction"
        )
        fiche = d.ok("POST", "/qualites", corps, attendu=201)
        m.ids[q] = fiche["id"]
        recette = [{"matiere_id": m.ids[x], "pourcentage": 100} for x in ("M1", "M2", "M3")]
        fiche = d.put(
            f"/qualites/{fiche['id']}/recette",
            {"lignes": recette, "motif": "recette de départ", "version": fiche["version"]},
        )
        v.egal(
            f"{q} : kg/m² (Σ poids, perte non comprise)", fiche["kg_m2"], sum(poids.values()), 1e-9
        )
        v.egal(f"{q} : coût au m²", fiche["cout_m2_mad"], COUT_M2[q], 1e-4)
        v.egal(f"{q} : recette conforme", fiche["controle"]["conforme"], True)
        fiche = d.put(
            f"/qualites/{fiche['id']}/plan",
            {
                "base_mensuelle": PLAN[q],
                "coefficients": [1] * 12,
                "motif": "plan de départ",
                "version": fiche["version"],
            },
        )
        v.egal(f"{q} : plan mensuel", fiche["base_mensuelle"], PLAN[q], 1e-9)
        vue_l = m.L.get(f"/qualites/{fiche['id']}")
        v.egal(f"{q} : coût au m² masqué pour l'alimentation", vue_l["cout_m2_mad"], None)
    metier = d.ok(
        "POST",
        "/metiers",
        {
            "code": "SCN-MT1",
            "nom": "Métier du scénario",
            "laize": 4,
            "bobines_par_metre": 300,
            "etages": 2,
            "actif": True,
        },
        attendu=201,
    )
    m.ids["metier"] = metier["id"]
    v.egal("métier : rien de monté", metier["sur_les_metiers"], 0, 1e-9)


IDS_LIGNE = (
    "matiere_id",
    "lot_id",
    "ordre_id",
    "metier_id",
    "commande_id",
    "dossier_id",
    "reception_id",
    "qualite_id",
    "fournisseur_id",
)


def cle_ligne(x: dict[str, Any]) -> str:
    """Une ligne de contrôle reconnue par les fiches qu'elle nomme."""
    return "|".join(str(x.get(k)) for k in IDS_LIGNE)


def etape_referentiels(m: Monde) -> None:
    """Étape 0 (2 novembre) : comptes, réglages, cours, fiches du mois."""
    m.jour("referentiels")
    comptes(m)
    lus = m.D.get("/controles")["controles"]
    m.avant["controles_0"] = {c["code"]: c["anomalies"] for c in lus}
    m.avant["controles_0_lignes"] = {c["code"]: [cle_ligne(x) for x in c["lignes"]] for c in lus}
    reglages(m)
    devises(m)
    fournisseur_et_matieres(m)
    qualites_et_metier(m)
