"""La liste des étapes du scénario (PLAN-DE-RECETTE-PRO § 8), dans l'ordre du calendrier."""

from __future__ import annotations

from collections.abc import Callable

from scenario_e_achats import (
    etape_approbation,
    etape_bon_imprime,
    etape_expedition,
    etape_plan,
    etape_plan_achat,
    etape_prix,
)
from scenario_e_atelier import (
    etape_annulation_ordre,
    etape_montage,
    etape_refus_atelier,
    etape_retour_machine,
    etape_sortie,
)
from scenario_e_cloture import (
    etape_bilan,
    etape_cloture,
    etape_controles,
    etape_sauvegarde,
    etape_verification,
)
from scenario_e_import import etape_dossier
from scenario_e_parite import etape_parite
from scenario_e_reception import etape_camion, etape_liberation
from scenario_e_referentiels import etape_referentiels
from scenario_e_suite import (
    etape_inventaire,
    etape_reclamation,
    etape_reglements,
    etape_retour_fournisseur,
)
from scenario_monde import Monde

Etape = tuple[str, str, Callable[[Monde], None]]

ETAPES: list[Etape] = [
    ("0", "Direction, achats — comptes, réglages, cours, fiches du mois", etape_referentiels),
    ("1", "Direction — révise le plan d'une qualité au 10 du mois", etape_plan),
    ("2", "Achats — lit le plan d'achat, prépare le bon depuis la proposition", etape_plan_achat),
    ("3", "Achats, direction — bon au-dessus du seuil : renvoyé, approuvé", etape_approbation),
    ("4", "Achats — imprime le bon fournisseur (A4, anglais, sans prix)", etape_bon_imprime),
    ("5", "Achats, direction — prix confirmés en deux fois, cours changé", etape_prix),
    ("6", "Achats — jalons d'expédition", etape_expedition),
    ("7", "Achats — un camion de deux bons en deux devises", etape_camion),
    ("8", "Achats — libère la quarantaine", etape_liberation),
    ("9", "Achats — facture, dossier d'importation, frais, clôture", etape_dossier),
    ("11", "Alimentation — ordre de deux qualités (FIFO, bobines, palette)", etape_sortie),
    ("10", "Alimentation — monte un fil sur le métier", etape_montage),
    ("12", "Alimentation — retour des machines (bobines)", etape_retour_machine),
    (
        "13",
        "Alimentation — sorties refusées : quarantaine, date d'avant le lot",
        etape_refus_atelier,
    ),
    ("14", "Achats — retour au fournisseur d'une partie d'un lot", etape_retour_fournisseur),
    ("16", "Achats, direction — inventaire d'un magasin avec recomptage", etape_inventaire),
    ("17", "Alimentation — annule un ordre qui a eu un retour", etape_annulation_ordre),
    ("15", "Achats — réclamation, de l'ouverture à l'avoir", etape_reclamation),
    ("18", "Achats — règle des factures et des frais", etape_reglements),
    ("19", "Direction — clôt la période à la fin du mois", etape_cloture),
    ("20", "Direction — bilan du mois, Cockpit, photo, courriel", etape_bilan),
    ("21", "Direction — contrôles", etape_controles),
    ("22b", "Administrateur — sauvegarde et restauration", etape_sauvegarde),
    ("22", "Vérification indépendante des chiffres (V1) : 0 écart", etape_verification),
    ("23", "Parité dynamique — le même mois rejoué dans Gestion MP", etape_parite),
]
"""Le scénario complet."""

ETAPES_COURTES: list[Etape] = [e for e in ETAPES if e[0] != "23"]
"""La version courte (essai pytest, base neuve) : tout sauf la parité, qui joue l'année d'essai."""
