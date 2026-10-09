# Restes à reprendre (tenu par le coordinateur)

Points relevés par un lot pour un autre, à traiter avant la recette finale.

| Origine | Pour | Point |
|---|---|---|
| E2 | S2 | Les `lien` des notifications et de la recherche globale doivent être des adresses d'écran déclarées dans `frontend/src/routes.ts`. |
| E2 | D4 | Déclarer `contexte.COMPTEURS["a_approuver"]` et `["receptions_brouillon"]` (pastilles Commandes et Réceptions). |
| E2 | D8 | Déclarer `alerte_rouge` et `anomalies` dans les compteurs du contexte. |
| E2 | D10 | `alerte_serveur` est une phrase affichée telle quelle en rouge pour D et T. |
| S4 | tous les lots D | Toute écriture passe par `services/audit` (journal) : c'est aussi ce qui invalide le cache du moteur. Champs `Numeric` en sortie : type `api.communs.Nombre`. |
| R1 | Mohamed (à la livraison) | 4 réceptions de Gestion MP payées en deux devises (LOMAT, USD et EUR) : reprises en une réception (devise de la facture en en-tête, prix des lignes intacts), signalé. À proposer : garder ou scinder. |
| D9 | X1 | Caddy ne doit pas remplacer la CSP posée par l'application (le bouton « Imprimer » est autorisé par son empreinte sha256). |
| D10 | D8 | Exposer `services.indicateurs.photographier(s) -> IndicateurJour` : la tâche `photo_indicateurs` l'appelle s'il existe (sinon repli sur `calcul.suivi`). |
| D2 | docs | Écarts de D2 à API-PRO/ECRANS-PRO/MODELE-DONNEES : routes 82 (`facteurs_cout`), 84/85 (`poids` en liste `{role_id, poids}`), 90/146 (`coefficients` → `saisonnalite`, `modifiees`), 92 (`?date=` sans effet), 97 (`MetierModifie`, `bobines_par_metre`), corps du montage selon API-PRO, origine du montage déduite, étage hors bornes 404 (docs/lots/D2.md § 4). Routes 147, 237, 238 faites par D2. |
| D2 | D8 | Valeur du fil monté dans `/valorisation` et `/cockpit` (moitié valorisation de `test_le_stock_est_en_magasin_ou_en_machine`). |
| D2 | D6 | Réutiliser `recettes.oublies` et `recettes.message_oublies` pour les blocages d'ordre ; remplacer la fabrique `ordre_valide` de D2 par celle de D6. |
| D3 | D4, D5 | Appeler `services.commandes.recaler_soldes(s, qui, {bons}, raison)` après validation/annulation d'une réception (D4), après un retour au fournisseur ou une libération de quarantaine (D5, via `commandes_des_lots`). D4 : avertir sans bloquer pour une réception sur un bon numéroté en attente d'approbation. Remplacer la fabrique `fabriques/achats.recevoir` par les vraies réceptions. |
| D3 | docs | Écarts de D3 (docs/lots/D3.md § 4) : schémas 149, 150, 152, 153 plus riches ; route 160 reçoit `lignes` ; `?statut=clos` ; champ `observations` (ECRANS-PRO : `remarques_fournisseur`) ; ECRANS-PRO 4.30 : Excel du bon sans raison sociale → 409 ; route 164 dans `api/commandes/routes_documents.py`. |
| D5 | S1 | Colonne `inventaire.abandon_motif` (aujourd'hui rangé dans `annulation_motif`). |
| D5 | S1/S2 | Essais dépendants de l'ordre : le monde de `tests/modele_monde.py` pose à la main le compteur `BC 2026` et `INV-2026-0001` ; un bon ou un inventaire validé par un essai passé après `test_migrations` fait échouer `test_periode`. Rendre `test_periode` et le monde indépendants des données laissées par les autres essais (les lots datent aujourd'hui au 31/12/2025 pour l'éviter). |
| D5 | docs | API-PRO 122–123 (`Brouillons.lignes`, réponse `valides`/`refuses`/`ignores`), champs ajoutés à `OperationFiche`, `InventaireFiche`, `DefautsInventaire` en `{id, code}` ; ECRANS-PRO P6 : un inventaire ouvert par magasin (index unique), message OR24 de REGLES (docs/lots/D5.md § 4). |
| D5 | D4, D6 | Définir `GENRE_BROUILLON` (protocole `services.brouillons.Genre` : rang 0 réceptions, rang 3 ordres) pour qu'« À valider » montre leurs brouillons ; D6 : partie « ordres » de `test_stock_atelier::test_brouillons_a_valider…`. |
| F7 | D8 | `GET /pieces` (pièces jointes) répond 404 : onglet Pièces jointes des fiches en erreur ; route 215 `/fournisseurs/performance` absente (lue en forme provisoire `catalogue/performance.ts`). |
| D6 | D8 | Moitié « bilan » de `test_plan_besoins::test_le_prevu_d_un_ordre_est_fige…` : lire `services.ordres.consommation.consommations`. |
| D6 | D5 | Remplacer la fabrique décor `ordre_valide` de D5 par `fabriques.ordres.valide`. |
| D6 | docs | Écarts de D6 (docs/lots/D6.md § 4) : `prevu`/`par_matiere`, filtres de la liste 135 non paginée, champ `blocage` (142), `vue=ordres|consommation` (144), `services/ordres/` en paquet. |
| D4, D5 | S0/S2 (priorité) | **Isolation des essais** : plusieurs essais dépendent des données laissées par d'autres (test_periode, test_taches::test_le_courriel_du_lundi_part_une_fois ; numéros posés à la main par tests/modele_monde.py). Les lots contournent (données datées au 31/12/2025, fixture `menage` de fabriques/receptions.py qui écrit sans journal). Rendre chaque essai sensible indépendant (base remise à un état connu par module, ou essai qui ne regarde que ses propres données), puis retirer les contournements. |
| D4 | D8 | Route 229 : appeler `services/factures.regler` (annulation par la direction seule, motif exigé) ; réutiliser `verifier_annulation_reglement` et `verifier_date_reglement` pour les frais ; porter les preuves de l'échéancier (domaine 7) et `test_suivi::test_l_atelier_signale_un_besoin_que_les_achats_traitent`. |
| D4 | docs | Écarts de D4 (docs/lots/D4.md § 4) : 169 `factures` par devise et `devise` sur les lignes (ECRANS-PRO 4.16 : liste) ; 170 une devise, rend la fiche ; 173 motif exigé ; 174 version de la réception ; 175–177, 181 plus riches ; 184 permise sur close ; 229 `motif` ; modules ajoutés (ARCHITECTURE § 3) ; refus de validation en 409 (essai hérité « deux postes » → [200, 409]). |
| F6 | D5 | Refus de libération de quarantaine : REGLES dit « achats » alors que la règle est « direction ou achats » — aligner le message. Historique d'une opération : sa place dans la fenêtre d'opération (ECRANS-PRO le cite sans la placer). |
| F6 | V3 | `outils/routes_ecran.py` (tout appel de l'écran a sa route) n'existe pas encore. |
| F3 | D8 | Routes 221–222 (signalements) : l'écran appelle `GET /signalements?mes=true` (filtrer par le compte) ; forme provisoire `SignalementFiche` dans `pages/atelier/types.ts` à remplacer par `Schema<…>`. |
| F3 | D6 | `OrdreResume.metier` : rendre « CODE · Nom » (l'écran le reconstitue depuis /metiers). |
| F3 | S4 | `GET /lots/{id}` rend `mouvements[].devise = "MAD"` à l'alimentation : retirer la devise pour elle. |
| F3 | D2 | Un montage d'un seul étage fait au bureau (route 99) est rangé « téléphone » dans l'historique : poser l'origine réelle. |
| D7 | D8 | Partie « échéancier général » de `test_echeanciers_regle_estime_et_clos_a_dater` ; C35, C36 par l'API ; `test_documents_du_dossier` (pièces jointes) ; écarter de l'échéancier les frais dus d'un dossier annulé (un frais réglé reste réglé). |
| D7 | R1 | Preuves de reprise du domaine 8 : `test_la_reprise_relie_les_dossiers_a_leur_facture`, `test_les_morceaux_d_un_ancien_eclatement_redeviennent_une_piece`. |
| D7 | docs | Écarts de D7 (docs/lots/D7.md § 4) : 188 `{factures, sans_facture, locaux}` ; 189 enrichie ; `commentaire` (ECRANS-PRO : `observations`) ; 192 sans `reception_ligne_ids` (rattacher par facture seulement) ; 200–204, 206 précisés ; dossiers annulés, jamais supprimés ; REGLES X-IMP-17 sans objet. |
| F2 | S4 | `LigneStock` sans id de rôle ni de fournisseur ; `par_magasin` indexé par code ; `Tracabilite` sans ids ni comparaison par matière ; `EtapeTracee.document` sans id (pas de lien). |
| F2 | S3 | `statut`, `statut_couverture`, `action` du moteur portent encore des émojis (l'écran les traduit par `cleStock`) : rendre des codes. |
| D8 | R2, C1 (correction déclarée K7) | PRO compte le fil monté à TOUTE date (rejeu de `montage_evenement`) dans la valorisation, le cockpit, les contrôles et le bilan ; Gestion MP ne le compte qu'au jour même (bilan : à part, mois en cours). Écart voulu (décision de Mohamed : le fil monté est du stock) : à déclarer et prouver dans la parité et la comparaison. |
| D8 | docs | Écarts de D8 (docs/lots/D8.md § 4) : routes 7, 209, 212, 213, 215, 221–229, 233, 235 ; ECRANS-PRO Valorisation (« à une date passée, le fil monté n'est pas compté » devenu faux) ; ARCHITECTURE § 3 (modules `pilotage_*`, `pieces_types`, `donnees_brutes`). |
| F4 | D4 | `Pesee.numero` vaut « brouillon n° 6 » (vocabulaire retiré) : rendre « Brouillon ». |
| F4 | D3 | `/export/plan-achat` ignore les filtres liés de l'écran ; la fiche ne dit pas pourquoi la date promise est figée. |
| NOMS | F1, F5, F8 | Schémas homonymes renommés (champs et routes inchangés), `types.gen.ts` régénéré (il prend aussi les routes de D8 : bilan, cockpit, contrôles, échéancier, pièces, signalements…) : après `git merge main`, citer `Schema<'…'>` par le nouveau nom, jamais par `gestion_mp_pro__api__…`. Importations (F5) : `AnnulationDossier`, `ClotureDossier`, `ReouvertureDossier`, `ValeurDeviseDossier` ; réceptions : `AnnulationReception` ; opérations : `AnnulationOperation`, `ValeurDeviseOperation` ; réclamations : `ClotureReclamation`, `ReouvertureReclamation` ; commandes : `LigneVersionBon` ; qualités : `LigneVersionRecette`, `RestaurationVersionRecette` ; exploitation (F8, sauvegardes) : `RestaurationSauvegarde`. `tests/test_noms_openapi.py` refuse désormais tout nom de schéma à `__` et deux classes exposées homonymes. |
| X2 | docs | ARCHITECTURE § 13.2 et critères X2 : `installer.sh` n'installe le LaunchAgent qu'avec `--demarrage-automatique` (décision : réglage du Mac laissé à Mohamed). |
| X2 | S0 | Cibles Makefile `poste-installer` et `coexistence`. |
| X2 | C1 | « Administration › Reprise » (routes 243–244) attendue par le poste : à faire dans C1. |
| F5 | docs | ECRANS-PRO 5.20 : `dossiers_ouverts` et `parts_figees` (et non `dossiers_recalcules`, `dossiers_figes`) ; `commentaire` à l'API, « Observations » à l'écran. |
| F5 | D7/S2 | Recherche de facture : « FA-2026/117 » ne trouve pas « FA-2026-117 » (ponctuation différente) — normaliser la ponctuation dans la recherche. |
| F1 | D8 | Notification « besoin signalé » : lien `/accueil?signalement=ID` pour tous, or la direction n'a pas `/accueil` → `/cockpit?signalement=ID` pour elle. |
| F1 | D3 | Champ `en_retard` (P1-11) ou compte serveur des retards et des arrivées à 7 jours (l'écran filtre lui-même). |
| F1 | V3 | Recette navigateur : un profil de navigateur à part par passage (cookies de session partagés entre serveurs `localhost`). |
| F8 | S2/D10 | QR en SVG (routes 6 et 20) sans `xmlns` : ne s'affiche pas dans une `<img>` (l'écran l'ajoute dans `administration/qr.ts`) — produire le SVG avec l'espace de noms (segno `svgns`), puis retirer le contournement. |
| F8 | D8/D1 | Nombre de brouillons datés de la période à clore : une route (ou un champ) pour l'annoncer avant la fenêtre de clôture. |
| F8 | docs | ECRANS-PRO : 7 ordres de seuils et non 5 ; note de la Valorisation sur le fil monté à une date passée (fausse depuis D8). |
| V1 | S0 | Cible `make verifier-chiffres`. |
| V1 | V2/V5 | Vérification sur la 3e base (copie après le scénario V2) ; familles non recomptées (stock sur les métiers, plan et besoins, projeté, statuts, XYZ, dormants, prévu des ordres non figés, coût d'une qualité, photo du jour, contrôles C06, C08, C13, C15, C17, C18, C20, C22–C25, C30, C32, C33, C35, C38) : à étendre si possible avant la recette. |
| R2 | docs | MODELE-DONNEES § 10.5 : corrections déclarées K7, K8a–h, K9 (K4 et K6 « identiques depuis Gestion MP corrigé ») ; ARCHITECTURE T1 dépassée par K7 ; docs/heritage/DECISIONS.md : ajouter K9 (prix connus à la date) en note de PRO. Voir docs/lots/R2.md. |
| R2 | Mohamed (livraison) | K8b : 4 réceptions payées en deux devises — PRO affiche 5 prix payés en USD comme des EUR (historique, matrice, Cockpit). Garder tel quel ou scinder ces réceptions. |
| R2 | V2 | La dynamique réduite joue tous les gestes en direction : V2 prend chaque rôle. |
| V2 | R2, DECISIONS | Correction voulue à déclarer : un changement de cours dans PRO ne revalorise jamais le passé (les entrées reprises sans cours reçoivent le cours du jour de la reprise, V3), alors que Gestion MP valorise ces entrées au cours du jour. K7 couvre aussi `/stock?date=` et le plan d'achat passés : rejouer `parite_k7` (GESTIONMPPRO_ESSAIS_COMPLETS=1). |
