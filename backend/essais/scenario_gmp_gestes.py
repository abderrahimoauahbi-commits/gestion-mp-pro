"""Le mois du scénario rejoué geste par geste dans Gestion MP (lot V2, parité dynamique § 7.4).

Mêmes jours, mêmes rôles, mêmes quantités et prix que les étapes de PRO ; les corps suivent
l'API de Gestion MP (`docs/heritage/API.md`). À chaque point de contrôle, la même photo que
celle prise dans PRO : stock, coût moyen et valeur des trois matières du scénario, plus les
numéros donnés, les refus et le bilan du mois. La comparaison est faite par
`scenario_e_parite`.
"""

from __future__ import annotations

from typing import Any

from scenario_outils import Horloge, Poste

JOURS = {
    "referentiels": "2026-11-02",
    "plan_revise": "2026-11-10",
    "confirmation_1": "2026-11-11",
    "cours_change": "2026-11-12",
    "camion": "2026-11-19",
    "liberation": "2026-11-20",
    "ordres": "2026-11-23",
    "retour_machine": "2026-11-24",
    "retour_fournisseur": "2026-11-25",
    "inventaire": "2026-11-26",
    "annulation_ordre": "2026-11-27",
    "cloture": "2026-12-01",
}
REFERENCES = {"M1": "SCN-POIL-PP-1200", "M2": "SCN-CHAINE-PES", "M3": "SCN-TRAME-JUTE"}


class Jeu:
    """L'état du rejeu dans Gestion MP : postes, identifiants, photos."""

    def __init__(self, postes: dict[str, Poste], horloge: Horloge) -> None:
        self.p = postes
        self.horloge = horloge
        self.ids: dict[str, int] = {}
        self.photos: dict[str, Any] = {}

    def jour(self, cle: str) -> str:
        """Avance l'horloge de Gestion MP."""
        from datetime import date

        self.horloge.aller(date.fromisoformat(JOURS[cle]))
        return JOURS[cle]

    def photo(self, nom: str) -> None:
        """Stock, coût moyen, valeur des matières du scénario (Valorisation de Gestion MP)."""
        valo = self.p["D"].get("/valorisation")
        par = {x["reference"]: x for x in valo["lignes"]}
        self.photos[nom] = {
            k: (par[r]["stock"], par[r]["cmup_mad"], par[r]["valeur_mad"])
            for k, r in REFERENCES.items()
            if r in par
        }


def referentiels(j: Jeu) -> None:
    """2 novembre : réglages, cours, code douanier, poste, fournisseur, matières, qualités."""
    d, a = j.p["D"], j.p["A"]
    j.jour("referentiels")
    d.put("/parametres", {"seuil_approbation": 200000, "nom_entreprise": "Tapis de l'Atlas"})
    for code, taux in (("USD", 10.0), ("EUR", 11.0)):
        a.put("/devises", {"code": code, "taux": taux})
    d.ok("POST", "/codes-douaniers", {"code": "5402.33.00", "taux_droits": 0.025})
    d.ok("POST", "/postes-frais", {"code": "ROUTE", "libelle": "Transport routier", "cle": "poids"})
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
        },
    )
    j.ids["F1"] = f["id"]
    commun = {"fournisseur_id": f["id"], "code_douanier": "5402.33.00"}
    for cle, corps in (
        (
            "M1",
            {
                "role": "Poil",
                "prix": 2.5,
                "devise": "USD",
                "unite_achat": "Palette",
                "contenance_achat": 500,
                "poids_bobine": 5,
                "bobines_palette": 100,
            },
        ),
        ("M2", {"role": "Chaîne", "prix": 3.2, "devise": "USD"}),
        (
            "M3",
            {
                "role": "Trame",
                "prix": 1.8,
                "devise": "EUR",
                "unite_achat": "Palette",
                "contenance_achat": 400,
                "poids_bobine": 4,
                "bobines_palette": 100,
            },
        ),
    ):
        fiche = a.ok("POST", "/articles", corps | commun | {"reference": REFERENCES[cle]})
        j.ids[cle] = fiche["id"]
    poids = {
        "Q1": {"Poil": 1.2, "Chaîne": 0.3, "Trame": 0.5},
        "Q2": {"Poil": 1.0, "Chaîne": 0.3, "Trame": 0.4},
    }
    for q, plan in (("Q1", 2000), ("Q2", 1500)):
        fiche = d.ok("POST", "/qualites", {"code": f"SCN-{q}", "poids": poids[q]})
        j.ids[q] = fiche["id"]
        d.put(
            f"/qualites/{fiche['id']}/recette",
            [{"article_id": j.ids[k], "pourcentage": 100} for k in ("M1", "M2", "M3")],
        )
        d.put(f"/qualites/{fiche['id']}/plan", {"base_mensuelle": plan, "saisonnalite": [1] * 12})
    metier = d.ok("POST", "/metiers", {"code": "SCN-MT1", "laize": 4, "densite": 300, "etages": 2})
    j.ids["metier"] = metier["id"]


def achats(j: Jeu) -> None:
    """10–12 novembre : plan révisé, plan d'achat, bons, approbation, prix en deux fois."""
    d, a = j.p["D"], j.p["A"]
    jour = j.jour("plan_revise")
    d.put(f"/qualites/{j.ids['Q1']}/plan", {"base_mensuelle": 3000, "saisonnalite": [1] * 12})
    plan = a.get("/plan-achat")
    j.photos["plan_achat"] = {
        k: next((x["quantite"] for x in plan["lignes"] if x["reference"] == r), None)
        for k, r in REFERENCES.items()
    }
    lignes = [
        {"article_id": j.ids["M1"], "quantite": 14500, "unite_achat": "Palette", "contenance": 500},
        {"article_id": j.ids["M2"], "quantite": 3718, "unite_achat": "kg", "contenance": 1},
        {"article_id": j.ids["M3"], "quantite": 6000, "unite_achat": "Palette", "contenance": 400},
    ]
    bons = a.ok(
        "POST",
        "/commandes",
        {"fournisseur_id": j.ids["F1"], "date_livraison_prevue": "2026-12-01", "lignes": lignes},
    )
    par = {b["devise"]: b for b in bons}
    j.ids["BC_USD"], j.ids["BC_EUR"] = par["USD"]["id"], par["EUR"]["id"]
    eur = a.post(f"/commandes/{j.ids['BC_EUR']}/envoyer", {"date": jour})
    usd = a.post(f"/commandes/{j.ids['BC_USD']}/envoyer", {"date": jour})
    j.photos["envoi"] = (eur["statut"], eur["numero"], usd["statut"], usd["numero"])
    d.post(f"/commandes/{j.ids['BC_USD']}/renvoyer", {"motif": "Chaîne : confirmer la teinte"})
    a.post(f"/commandes/{j.ids['BC_USD']}/envoyer", {"date": jour})
    usd = d.post(f"/commandes/{j.ids['BC_USD']}/approuver", {"date": jour})
    j.photos["approbation"] = (usd["statut"], usd["numero"])
    j.jour("confirmation_1")
    _prix(j, "BC_EUR", {"M3": 1.8}, "2026-11-25")
    _prix(j, "BC_USD", {"M2": 3.2}, "2026-11-25")
    j.jour("cours_change")
    a.put("/devises", {"code": "USD", "taux": 10.5})
    usd = _prix(j, "BC_USD", {"M1": 3.0}, None)
    j.photos["hausse"] = (usd["statut"], usd.get("cours"))
    d.post(f"/commandes/{j.ids['BC_USD']}/approuver", {})


def _prix(j: Jeu, bon: str, prix: dict[str, float], promesse: str | None) -> Any:
    a = j.p["A"]
    fiche = bon_de(j, bon)
    lignes = {x["article_id"]: x["id"] for x in fiche["lignes"]}
    corps: dict[str, Any] = {
        "prix": [{"ligne_id": lignes[j.ids[k]], "prix": p} for k, p in prix.items()],
        "mettre_a_jour_catalogue": False,
    }
    if promesse:
        corps["date_livraison_prevue"] = promesse
    return a.post(f"/commandes/{j.ids[bon]}/prix", corps)


def bon_de(j: Jeu, bon: str) -> Any:
    """Un bon par son id (Gestion MP n'a pas de route de fiche : la liste le contient)."""
    return next(x for x in j.p["A"].get("/commandes") if x["id"] == j.ids[bon])
