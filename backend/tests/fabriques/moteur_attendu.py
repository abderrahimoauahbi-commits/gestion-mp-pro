"""Les `Donnees` que le chargeur doit lire de la petite usine (`fabriques/moteur.py`), écrites à
la main champ par champ (CALCULS A § 4.6, § 4.7), et les outils pour les comparer à l'ordre
et au type près (lot S4)."""

from __future__ import annotations

from datetime import date, datetime

from fabriques.comparaison import flottants
from fabriques.moteur_base import Monde
from fabriques.moteur_journal import OUVERTURE, PRINCIPAL, QUARANTAINE, heure, journal
from sqlalchemy import select
from sqlalchemy.orm import Session

from gestion_mp_pro.calcul import modele as c
from gestion_mp_pro.modeles import Commande

AUJOURDHUI = date(2026, 10, 8)


def _parametres() -> c.Parametres:
    p = c.Parametres(seuil_alerte=95, toler_ecart_pesee=0.03, nom_entreprise="Tapis Essai")
    p.cours = {"EUR": 10.8, "MAD": 1.0, "USD": 10.0}
    p.taux_eur_mad, p.taux_usd_mad = 10.8, 10.0
    return p


def _articles() -> list[c.Article]:
    return [
        c.Article(
            reference="Cuir brun",
            role_bom="Cuir",
            titrage="",
            unite_prix="ml",
            fournisseur="LOCAL PLAST",
            prix_unite=0.0196,
            densite=0.014,
        ),
        c.Article(
            reference="Jute",
            role_bom="Trame",
            titrage="",
            fournisseur="LOCAL PLAST",
            prix_unite=12.0,
        ),
        c.Article(
            reference="PP Rouge",
            role_bom="Poil",
            nature="Polypropylène",
            designation="Rouge vif",
            titrage="2900",
            fournisseur="HASIRCI",
            prix_unite=2.5,
            devise="USD",
            stock_min=50,
            couv_min_mois=1.5,
            poids_bobine=2.5,
            bob_palette=40,
            unite_commande="Palette",
            contenance_commande=100,
            groupe_equiv="G1",
            priorite_equiv=1,
            composition="PP",
            type_fil="FRZ",
            couleur="Rouge",
            titrage_unite="Dtex",
        ),
    ]


def _referentiels() -> dict[str, object]:
    return {
        "fournisseurs": [
            c.Fournisseur(
                nom="HASIRCI",
                code="FRS-1",
                contact="ETHEM",
                pays="MAROC",
                delai_jours=65,
                devise="USD",
                delai_paiement_jours=180,
                couverture_commande_jours=60,
            ),
            c.Fournisseur(nom="LOCAL PLAST", pays="MAROC", delai_jours=60),
        ],
        "articles": _articles(),
        "magasins": [
            c.Magasin(code=PRINCIPAL, nom=PRINCIPAL, type="Stock courant"),
            c.Magasin(code=QUARANTAINE, nom=QUARANTAINE, type="Quarantaine"),
        ],
        "metiers": [
            c.Metier(
                code="CRM 1",
                nom="Métier 1",
                laize=4.2,
                densite=320,
                etages=6,
                fils=[
                    c.FilMonte(
                        reference="PP Rouge", etage=1, metres=4, pourcentage=60, poids_bobine=2.5
                    )
                ],
            ),
            c.Metier(code="CRM 2", nom="Métier 2", laize=4.2, actif=False),
        ],
    }


def _qualites() -> dict[str, object]:
    janvier = [1.2] + [1.0] * 11
    uns = [1.0] * 12
    return {
        "qualites": [
            c.Qualite(code="8F", nom="8F MOSQUEE", poids={"Poil": 1.53, "Trame": 0.4, "Cuir": 1.0}),
            c.Qualite(code="OLD", nom="Arrêtée"),
        ],
        "recettes": [c.LigneRecette("8F", ref, 100.0) for ref in ("PP Rouge", "Cuir brun", "Jute")],
        "plan": [
            c.PlanQualite("8F", 2500, janvier, True, date(2026, 3, 1)),
            c.PlanQualite("OLD", 300, uns, False, OUVERTURE),
        ],
        "versions_plan": {
            "8F": [
                c.VersionPlan(None, 2000, uns, True, OUVERTURE),
                c.VersionPlan(heure(2026, 3, 1, 10), 2500, janvier, True, date(2026, 3, 1)),
                c.VersionPlan(
                    heure(2026, 6, 1, 10), 2500, [1.3] + [1.0] * 11, True, date(2026, 3, 1)
                ),
            ],
            "OLD": [
                c.VersionPlan(None, 300, uns, True, OUVERTURE),
                c.VersionPlan(datetime.min, 300, uns, False, OUVERTURE),  # noqa: DTZ901
            ],
        },
        "versions_recette": {
            "8F": [
                c.VersionRecette(heure(2026, 2, 1, 10), [("PP Rouge", 100.0), ("Jute", 100.0)]),
                c.VersionRecette(
                    heure(2026, 5, 1, 10), [("PP Rouge", 100.0), ("Jute", 100.0)], {"Poil": 1.53}
                ),
            ]
        },
    }


def _commandes(w: Monde, brouillon: str) -> list[c.Commande]:
    bc = "BC-2026-0001"
    return [
        c.Commande(
            bc,
            date(2026, 9, 1),
            "HASIRCI",
            date(2026, 9, 20),
            "Envoyée",
            "Urgent",
            [
                c.LigneCommande(
                    bc, "PP Rouge", 1000, 850, 200, 2.4, "USD", True, "Palette", 100, 2.4, 9.8
                ),
                c.LigneCommande(bc, "Jute", 500, 0, 0, 0, "USD", False, "kg", 1, 12.0 / 10.0, 9.8),
            ],
            eta=date(2026, 9, 25),
        ),
        c.Commande(
            brouillon,
            date(2026, 9, 3),
            "LOCAL PLAST",
            None,
            "Brouillon",
            "",
            [
                c.LigneCommande(brouillon, "Cuir brun", 20, prix_estime=0.0196 / 0.014),
            ],
        ),
        c.Commande(
            "BC-2026-0002",
            date(2026, 8, 1),
            "LOCAL PLAST",
            None,
            "Soldée",
            "",
            [
                c.LigneCommande(
                    "BC-2026-0002", "Jute", 100, prix_unite=11, prix_confirme=True, prix_estime=11
                )
            ],
            solde_a_la_main_le=heure(2026, 9, 15, 10),
        ),
        c.Commande(
            "BC-2026-0003",
            date(2026, 8, 1),
            "LOCAL PLAST",
            None,
            "Annulée",
            "",
            [
                c.LigneCommande(
                    "BC-2026-0003", "Jute", 100, prix_unite=11, prix_confirme=True, prix_estime=11
                )
            ],
            annulee_le=heure(2026, 9, 15, 10),
        ),
    ]


def _receptions(w: Monde) -> dict[str, object]:
    bc, rec = "BC-2026-0001", "REC-2026-0001"
    lignes = [
        c.LigneReception(
            "PP Rouge", "L-PP1", 600, 600, 600, 240, 6, PRINCIPAL, "Conforme", "RAS", bc, 0.03
        ),
        c.LigneReception(
            "PP Rouge", "L-PP2", 300, 300, 300, 120, 3, QUARANTAINE, "Réserve", "RAS", bc, 0.03
        ),
        c.LigneReception("Jute", "", 0, 0, 50, 0, 0, "", "Refusé", "", bc, 0.03),
    ]
    return {
        "receptions": [
            c.Reception(
                rec,
                date(2026, 9, 22),
                bc,
                "HASIRCI",
                "BL-9",
                "F-1",
                "Karim — magasin",
                "Sara",
                "Validée",
                lignes,
                heure(2026, 9, 22, 15),
            ),
            c.Reception(
                f"brouillon n° {w.ids['rec_brouillon']}",
                date(2026, 9, 30),
                "",
                "LOCAL PLAST",
                controleur_qualite="Nadia",
                lignes=[c.LigneReception("Cuir brun", "C-9", 12, 0, 10, tolerance_partielle=0.03)],
            ),
        ],
        "historique_prix": [
            c.LignePrix(date(2026, 9, 22), "PP Rouge", "HASIRCI", bc, 600, 2.4, "USD"),
            c.LignePrix(date(2026, 9, 22), "PP Rouge", "HASIRCI", bc, 300, 2.4, "USD"),
        ],
    }


def _production(w: Monde) -> dict[str, object]:
    ligne = w.ids["dossier_ligne"]
    return {
        "dossiers_import": [
            c.DossierImport(
                "01/26",
                "Fil turc",
                date(2026, 9, 21),
                "BMCE",
                "Ouvert",
                "Premier",
                [
                    c.LigneImport(
                        ligne,
                        "PP Rouge",
                        600,
                        1440,
                        "USD",
                        9.8,
                        "L-PP1",
                        "HASIRCI",
                        w.ids["ligne_ppa"],
                    )
                ],
                [
                    c.ChargeImport("DD", 3000, None, "DD-1", "", False, "valeur", {ligne: 3000}),
                    c.ChargeImport("FRET", 1200, ligne, "", "Camion", False, "valeur"),
                ],
                [c.FactureImport("F-1", 2160, "USD", [ligne])],
            ),
        ],
        "ordres": [
            c.OrdreFabrication(
                "OF-2026-0001",
                date(2026, 9, 25),
                [("8F", 100.0)],
                "",
                {"PP Rouge": 153.0, "Jute": 40.0},
                0.02,
                heure(2026, 9, 25, 8),
            ),
        ],
    }


def attendu(s: Session, w: Monde) -> c.Donnees:
    """Les `Donnees` que le chargeur doit rendre, écrites à la main."""
    brouillon = s.scalars(select(Commande.id).where(Commande.numero.is_(None))).one()
    donnees = c.Donnees(
        parametres=_parametres(),
        **_referentiels(),  # type: ignore[arg-type]
        **_qualites(),  # type: ignore[arg-type]
        mouvements=journal(w),
        commandes=_commandes(w, f"BC-brouillon-{brouillon}"),
        **_receptions(w),  # type: ignore[arg-type]
        **_production(w),  # type: ignore[arg-type]
        soldes={
            ("PP Rouge", "L-PP1", PRINCIPAL): 460.0,
            ("PP Rouge", "L-PP2", PRINCIPAL): 100.0,
            ("PP Rouge", "L-PP2", QUARANTAINE): 200.0,
            ("Jute", "J-1", PRINCIPAL): 960.0,
        },
    )
    flottants(donnees, c.Donnees)
    donnees.parametres.dso = 60  # réglage illisible : le défaut tel quel (`pour_le_moteur`)
    return donnees
