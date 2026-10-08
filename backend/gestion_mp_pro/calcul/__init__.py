"""Moteur de calcul pur : aucune base, aucune date « du jour » implicite (ARCHITECTURE § 7).

Portage fonction par fonction du moteur de Gestion MP (`gestion_mp/calcul/`, `depot.py` et
les calculs logés dans ses routes), méthode « corrigée » seule (DECISIONS P17). Il reçoit des
`modele.Donnees` (construites par `services/donnees_moteur.py`, lot S4) et rend des
dataclasses ; la date de référence et la date du jour sont toujours des paramètres.

Carte des modules :

- `modele/`, `constantes`, `outils` : structures, constantes nommées, arrondi d'Excel, mois ;
- `a_la_date` : les données au soir d'une date ;
- `plan`, `nomenclature`, `besoins` : plan glissant et de l'époque, recettes, MRP ;
- `stock/` : `etat_stock` (une ligne par matière) et le fil monté sur les métiers ;
- `achats`, `plan_achat` : ce qu'un bon engage, le plan d'achat ;
- `valorisation` : CMUP glissant du journal, valeur du stock ;
- `prix`, `opportunites` : prix payés, coûts rendus, matrice, pistes d'économies ;
- `pilotage`, `pilotage_valeurs` : coût matière, Cockpit ;
- `fournisseurs`, `receptions`, `lots`, `production`, `importations` ;
- `classification` : lire et composer une référence de fil ;
- `chargement` : les calculs purs du chargeur (journal signé → journal du moteur…) ;
- `inventaire`, `suivi`, `analyse_revient` : les calculs que Gestion MP faisait dans ses routes ;
- `controles/` : les 38 contrôles C01…C38, en registre.

Voir `docs/lots/S3.md`.
"""
