"""Parité par l'API : les paires de routes du pilotage et du stock (calculs du moteur).

Chaque route nomme aussi la fonction de Gestion MP qui la sert (`fonction`) : le recalcul
de Gestion MP sur les jeux traduits (`gestion_mp_parite.py routes`) l'appelle telle quelle,
son chargeur remplacé par les données du jeu, pour expliquer un écart dans sa forme et son
ampleur. Les traductions de forme viennent des notes des lots (§ 4) et de RESTES « docs ».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import parite_api_formes as f
from parite_api import Liste, Route

PLAN_ACHAT_TETE = (
    "references_a_commander references_en_alerte budget_mad quantite_totale references_classe_a "
    "ruptures critiques urgents attentions ok tiers"
).split()
"""Les indicateurs du plan d'achat : rangés par PRO dans `indicateurs` (API-PRO 150)."""
CONTROLE = Liste(
    ("code",),
    renommes={"vers": "lien", "detail": "lignes"},
    formes={
        "vers": f.adresse_ecran,
        "quoi_faire": f.suite(f.texte_aide, f.conseil_recette),
        "detail": f.suite(f.surcout_en_pourcent, f.conseil_recette),
    },
)


@dataclass(frozen=True)
class Appel:
    """La fonction de Gestion MP qui sert la route, et ses paramètres de requête."""

    module: str
    fonction: str
    parametres: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteMoteur:
    """Une route du pilotage : la paire, et l'appel de Gestion MP à rejouer sur les jeux."""

    route: Route
    appel: Appel


def _date(jour: str, nom: str = "date") -> str:
    return f"?{nom}={jour}" if jour else ""


def _pilotage_1(jour: str = "") -> list[RouteMoteur]:
    """Partie 1 de `pilotage`."""
    dr = {"date_reference": jour} if jour else {}
    suffixe = f" ({jour})" if jour else ""
    pg = "gestion_mp.api.pilotage"
    return [
        RouteMoteur(
            Route(
                f"stock{suffixe}",
                f"/api/stock{_date(jour, 'date_reference')}",
                f"/api/stock{_date(jour)}",
                liste=Liste(("reference",)),
                jour=jour,
            ),
            Appel(pg, "etat_stock", dr),
        ),
        RouteMoteur(
            Route(
                f"valorisation{suffixe}",
                f"/api/valorisation{_date(jour, 'date_reference')}",
                f"/api/valorisation{_date(jour)}",
                liste=Liste(("reference",)),
                jour=jour,
            ),
            Appel(pg, "valorisation", dr),
        ),
        RouteMoteur(
            Route(
                f"cockpit{suffixe}",
                f"/api/cockpit{_date(jour, 'date_reference')}",
                f"/api/cockpit{_date(jour)}",
                entete=_cockpit(),
                jour=jour,
            ),
            Appel(pg, "cockpit", dr),
        ),
    ]


def _pilotage_2(jour: str = "") -> list[RouteMoteur]:
    """Partie 2 de `pilotage`."""
    dr = {"date_reference": jour} if jour else {}
    suffixe = f" ({jour})" if jour else ""
    pg = "gestion_mp.api.pilotage"
    return [
        RouteMoteur(
            Route(
                f"controles{suffixe}",
                f"/api/controles{_date(jour, 'date_reference')}",
                f"/api/controles{_date(jour)}",
                liste=CONTROLE,
                champ_gmp="controles",
                champ_pro="controles",
                entete=Liste((), deplaces={"colonnes": COLONNES_DEPLACEES}),
                jour=jour,
            ),
            Appel(pg, "controles", dr),
        ),
        RouteMoteur(
            Route(
                f"plan-achat{suffixe}",
                f"/api/plan-achat{_date(jour, 'date_reference')}",
                f"/api/plan-achat{_date(jour)}",
                liste=Liste(("reference",)),
                entete=Liste(
                    (),
                    renommes={c: f"indicateurs.{c}" for c in PLAN_ACHAT_TETE},
                    sous={"fournisseurs": Liste(("fournisseur",))},
                ),
                jour=jour,
            ),
            Appel(pg, "plan_achat", dr),
        ),
        RouteMoteur(
            Route(
                f"opportunites{suffixe}",
                f"/api/opportunites{_date(jour, 'date_reference')}",
                f"/api/opportunites{_date(jour)}",
                liste=Liste(("reference", "fournisseur_alternatif", "reference_alternative")),
                jour=jour,
            ),
            Appel(
                pg,
                "opportunites",
                dr
                | {
                    "meme_couleur": True,
                    "autre_fournisseur": True,
                    "prix_catalogue": False,
                    "fenetre_jours": None,
                },
            ),
        ),
    ]


def pilotage(jour: str = "") -> list[RouteMoteur]:
    """Les routes du pilotage, à une date (vide : aujourd'hui)."""
    return _pilotage_1(jour) + _pilotage_2(jour)


COLONNES_DEPLACEES = (
    "libellés des colonnes de tous les contrôles : PRO les rend dans chaque contrôle "
    "(`controles[].colonnes`, {cle, libelle, unite}), D8 § 4"
)


def _cockpit() -> Liste:
    return Liste(
        (),
        sous={
            "alertes": Liste(("reference",), formes={"statut": f.sans_emoji}),
            "devises": Liste(("devise",)),
        },
    )


def _tout_le_reste_1() -> list[RouteMoteur]:
    """Partie 1 de `tout_le_reste`."""
    pg = "gestion_mp.api.pilotage"
    return [
        RouteMoteur(
            Route(
                "performance",
                "/api/fournisseurs/performance",
                "/api/fournisseurs/performance",
                liste=Liste(("fournisseur",), formes={"classement": f.sans_emoji}),
                entete=Liste((), sous={"receptions": Liste(("numero",))}),
            ),
            Appel(pg, "performance_fournisseurs"),
        ),
        RouteMoteur(
            Route(
                "prix (historique)",
                "/api/prix/historique",
                "/api/prix/historique",
                liste=Liste(("date_bc", "numero_bc", "reference", "quantite")),
            ),
            Appel(pg, "historique_des_prix"),
        ),
        RouteMoteur(
            Route(
                "prix (matrice)",
                "/api/prix/matrice",
                "/api/prix/matrice",
                liste=Liste(("reference", "devise")),
            ),
            Appel(pg, "matrice_prix"),
        ),
        RouteMoteur(
            Route(
                "nomenclature",
                "/api/nomenclature",
                "/api/nomenclature",
                liste=Liste(
                    ("qualite", "reference"),
                    renommes={"role_bom": "role", "devise": "devise_prix"},
                    formes={"ml_m2": f.nul},
                    deplaces={"poids_categorie": POIDS},
                ),
                entete=Liste(
                    (), sous={"controle": Liste(("qualite",), formes={"ecarts": f.conseil_recette})}
                ),
            ),
            Appel(pg, "nomenclature"),
        ),
    ]


def _tout_le_reste_2() -> list[RouteMoteur]:
    """Partie 2 de `tout_le_reste`."""
    pg = "gestion_mp.api.pilotage"
    pp = "gestion_mp.api.production_plan"
    return [
        RouteMoteur(
            Route(
                "production (réalisé)",
                "/api/production/realise",
                "/api/production/realise",
                liste=Liste(("qualite",)),
            ),
            Appel(pp, "plan_et_realise_fige"),
        ),
        RouteMoteur(
            Route(
                "production (besoins)",
                "/api/production/besoins",
                "/api/production/besoins",
                liste=Liste(("reference",)),
            ),
            Appel(pp, "besoins_detailles"),
        ),
        RouteMoteur(
            Route(
                "production (plan)",
                "/api/production/plan",
                "/api/production/plan",
                entete=Liste((), sous={"qualites": Liste(("code",))}),
            ),
            Appel(pp, "plan_de_production"),
        ),
        RouteMoteur(
            Route(
                "besoins",
                "/api/besoins",
                "/api/production/besoins",
                liste=Liste(("reference",)),
                champ_gmp="besoins",
                entete=Liste((), deplaces={"plan": PLAN_DEPLACE}),
            ),
            Appel(pg, "besoins"),
        ),
    ]


def _tout_le_reste_3() -> list[RouteMoteur]:
    """Partie 3 de `tout_le_reste`."""
    pg = "gestion_mp.api.pilotage"
    return [
        RouteMoteur(
            Route(
                "bobines",
                "/api/receptions/bobines",
                "/api/receptions/bobines",
                liste=Liste(
                    ("reference", "fournisseur"), sous={"historique": Liste(("reception", "lot"))}
                ),
            ),
            Appel(pg, "evolution_du_poids_des_bobines"),
        ),
        RouteMoteur(
            Route(
                "analyse du revient",
                "/api/importations/analyse/revient",
                "/api/analyse/revient",
                liste=Liste(("valeur",)),
            ),
            Appel("gestion_mp.api.analyse_import", "analyse_revient"),
        ),
        RouteMoteur(
            Route(
                "ordres (consommation)",
                "/api/ordres-fabrication",
                "/api/ordres/consommation",
                liste=Liste(
                    ("numero_of",),
                    cle_pro=("numero",),
                    renommes={
                        "numero_of": "numero",
                        "theorique": "prevu",
                        "fabrications": "qualites",
                    },
                    deplaces=ORDRE_DEPLACES,
                    sous={
                        "fabrications": Liste(("qualite",)),
                        "references": Liste(("reference",), renommes={"theorique": "prevu"}),
                    },
                ),
            ),
            Appel(pg, "ordres_fabrication"),
        ),
    ]


def tout_le_reste() -> list[RouteMoteur]:
    """Les routes du moteur sans date."""
    return _tout_le_reste_1() + _tout_le_reste_2() + _tout_le_reste_3()


PLAN_DEPLACE = (
    "m² du plan par qualité : PRO les rend dans `/production/plan` (`qualites[].glissant`), "
    "comparés par la route « production (plan) »"
)
POIDS = (
    "poids du rôle dans la qualité : PRO le rend sur la fiche de la qualité (route 84, `poids`), "
    "pas sur chaque ligne de la nomenclature"
)
ORDRE_DEPLACES = {
    "qualite": "qualité tissée : PRO rend la liste `qualites` (un ordre peut en tisser "
    "plusieurs) et `fabrication` (texte), comparées par `fabrications`",
    "taux_perte_fige": "taux de perte figé : PRO dit `prevu_fige` sur l'ordre (route 135) et "
    "`taux_perte` appliqué ici",
}
