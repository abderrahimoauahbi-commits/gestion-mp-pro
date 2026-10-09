# Restes à reprendre (tenu par le coordinateur)

Points relevés par un lot pour un autre, à traiter avant la recette finale.

| Origine | Pour | Point |
|---|---|---|
| R1 | Mohamed (à la livraison) | 4 réceptions de Gestion MP payées en deux devises (LOMAT, USD et EUR) : reprises en une réception (devise de la facture en en-tête, prix des lignes intacts), signalé. À proposer : garder ou scinder. |
| D9 | X1 | Caddy ne doit pas remplacer la CSP posée par l'application (le bouton « Imprimer » est autorisé par son empreinte sha256). |
| D8 | R2, C1 (correction déclarée K7) | PRO compte le fil monté à TOUTE date (rejeu de `montage_evenement`) dans la valorisation, le cockpit, les contrôles et le bilan ; Gestion MP ne le compte qu'au jour même (bilan : à part, mois en cours). Écart voulu (décision de Mohamed : le fil monté est du stock) : à déclarer et prouver dans la parité et la comparaison. |
| D8 | docs | Écarts de D8 (docs/lots/D8.md § 4) : routes 7, 209, 212, 213, 215, 221–229, 233, 235 ; ECRANS-PRO Valorisation (« à une date passée, le fil monté n'est pas compté » devenu faux) ; ARCHITECTURE § 3 (modules `pilotage_*`, `pieces_types`, `donnees_brutes`). |
| F4 | D4 | `Pesee.numero` vaut « brouillon n° 6 » (vocabulaire retiré) : rendre « Brouillon ». |
| F4 | D3 | `/export/plan-achat` ignore les filtres liés de l'écran ; la fiche ne dit pas pourquoi la date promise est figée. |
| NOMS | F1, F5, F8 | Schémas homonymes renommés (champs et routes inchangés), `types.gen.ts` régénéré (il prend aussi les routes de D8 : bilan, cockpit, contrôles, échéancier, pièces, signalements…) : après `git merge main`, citer `Schema<'…'>` par le nouveau nom, jamais par `gestion_mp_pro__api__…`. Importations (F5) : `AnnulationDossier`, `ClotureDossier`, `ReouvertureDossier`, `ValeurDeviseDossier` ; réceptions : `AnnulationReception` ; opérations : `AnnulationOperation`, `ValeurDeviseOperation` ; réclamations : `ClotureReclamation`, `ReouvertureReclamation` ; commandes : `LigneVersionBon` ; qualités : `LigneVersionRecette`, `RestaurationVersionRecette` ; exploitation (F8, sauvegardes) : `RestaurationSauvegarde`. `tests/test_noms_openapi.py` refuse désormais tout nom de schéma à `__` et deux classes exposées homonymes. |
| X2 | C1 | « Administration › Reprise » (routes 243–244) attendue par le poste : à faire dans C1. |
| F1 | V3 | Recette navigateur : un profil de navigateur à part par passage (cookies de session partagés entre serveurs `localhost`). |
| V1 | V2/V5 | Vérification sur la 3e base (copie après le scénario V2) ; familles non recomptées (stock sur les métiers, plan et besoins, projeté, statuts, XYZ, dormants, prévu des ordres non figés, coût d'une qualité, photo du jour, contrôles C06, C08, C13, C15, C17, C18, C20, C22–C25, C30, C32, C33, C35, C38) : à étendre si possible avant la recette. |
| R2 | docs | MODELE-DONNEES § 10.5 : corrections déclarées K7, K8a–h, K9 (K4 et K6 « identiques depuis Gestion MP corrigé ») ; ARCHITECTURE T1 dépassée par K7 ; docs/heritage/DECISIONS.md : ajouter K9 (prix connus à la date) en note de PRO. Voir docs/lots/R2.md. |
| R2 | Mohamed (livraison) | K8b : 4 réceptions payées en deux devises — PRO affiche 5 prix payés en USD comme des EUR (historique, matrice, Cockpit). Garder tel quel ou scinder ces réceptions. |
| R2 | V2 | La dynamique réduite joue tous les gestes en direction : V2 prend chaque rôle. |
| V2 | R2, DECISIONS | Correction voulue à déclarer : un changement de cours dans PRO ne revalorise jamais le passé (les entrées reprises sans cours reçoivent le cours du jour de la reprise, V3), alors que Gestion MP valorise ces entrées au cours du jour. K7 couvre aussi `/stock?date=` et le plan d'achat passés : rejouer `parite_k7` (GESTIONMPPRO_ESSAIS_COMPLETS=1). |
