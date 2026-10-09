# Restes à reprendre (tenu par le coordinateur)

Points relevés par un lot pour un autre, à traiter avant la recette finale.

| Origine | Pour | Point |
|---|---|---|
| E2 | S2 | Désactiver un compte ferme ses sessions : la requête suivante reçoit « Connectez-vous pour continuer. » et l'écran dit « Votre session a expiré ». Rendre `compte_inactif` (« Ce compte n'est plus actif. », H-09) en gardant la raison de fermeture des sessions. |
| E2 | S2 | Les `lien` des notifications et de la recherche globale doivent être des adresses d'écran déclarées dans `frontend/src/routes.ts`. |
| E2 | D4 | Déclarer `contexte.COMPTEURS["a_approuver"]` et `["receptions_brouillon"]` (pastilles Commandes et Réceptions). |
| E2 | D8 | Déclarer `alerte_rouge` et `anomalies` dans les compteurs du contexte. |
| E2 | D10 | `alerte_serveur` est une phrase affichée telle quelle en rouge pour D et T. |
| E2 | S0 | Cible `make notice` (un essai vitest vérifie déjà que docs/NOTICE.md est à jour). |
| S2 | docs | Reporter dans API-PRO les champs ajoutés par S2 (Connexion.compte, Visage.role_libelle, Moi.vu_le/version, UtilisateurModification.code, ValeursJournal, Contexte.compteurs/base_essai/roles_au_metre, Acces.adresse_qr) ; ARCHITECTURE : `securite/` est un paquet. |
| S4 | D9 | Route 114 `GET /documents/etiquettes` : les données sont prêtes dans `services.lots_lecture.etiquettes` ; brancher la route (`api/documents/`) et le gabarit. |
| S4 | docs | API-PRO : `/lots/scan` (110) rend une liste (un numéro peut exister pour deux matières), 404 si vide ; ARCHITECTURE § 7 : le chargeur fait ~60 requêtes groupées (nombre fixe), pas « une dizaine ». |
| S4 | tous les lots D | Toute écriture passe par `services/audit` (journal) : c'est aussi ce qui invalide le cache du moteur. Champs `Numeric` en sortie : type `api.communs.Nombre`. |
| D1 | S1 (révision 0004) | `role_nomenclature.version` (la route 59 accepte une version sans la contrôler) ; valeur `periode_close` dans `OrigineCours` (cours figé par la clôture, aujourd'hui rangé en `saisi` avec une note). |
| D1 | D9 | Les classeurs des référentiels passent par `exports/referentiels.classeur` en attendant `exports/classeur.py`. |
| D1 | docs | Schémas enrichis (routes 24, 26, 27, 28, 34, 38, 42, 57, 62, 64, 70–71, 77, 79–80 : voir docs/lots/D1.md § 4) ; ECRANS-PRO P7 « Désactiver » à corps partiel contre API-PRO § 1.24 (fiche entière, suivi) ; `?version=` facultatif sur les suppressions 41, 63, 68, 74. |
| D1 | tous | `test_catalogue_api.py` (OpenAPI = API-PRO) n'existe pas encore : à écrire avant la recette (V5). |
| R1 | Mohamed (à la livraison) | 4 réceptions de Gestion MP payées en deux devises (LOMAT, USD et EUR) : reprises en une réception (devise de la facture en en-tête, prix des lignes intacts), signalé. À proposer : garder ou scinder. |
| R1 | docs | MODELE-DONNEES § 10 : `--date-limite` non fait ; options `--cible`, `--pieces-source`, `--rapport`, `--genre` ; correspondances des tables enfants par parent ; le vidage garde les fichiers des pièces jointes. |
| R1 | D10 | `reprise/sauvegarde.py` est un `pg_dump` minimal : le remplacer par le service de sauvegarde de D10. |
| D9 | docs | API-PRO 114 « HTML A4 » : fait en étiquettes 100 × 70 mm, une par page (comme Gestion MP et ECRANS-PRO). ECRANS-PRO 4.29 : le bon fournisseur est en anglais jusque dans l'en-tête (« HEAD OFFICE », « BANKS », décision du 8 octobre) — corriger le document. |
| D9 | X1 | Caddy ne doit pas remplacer la CSP posée par l'application (le bouton « Imprimer » est autorisé par son empreinte sha256). |
| D9 | S4 | Étiquettes (`lots_lecture.etiquettes`) : kilos selon la règle § 9.3 (espace insécable, décimales) ; champ « ≈ N bobines » manquant. |
| D10 | S1 | `GenreSauvegarde` : ajouter `avant_vidage` et `avant_mise_a_jour` (décision X2) ; le registre les ignore en attendant (`services/sauvegarde_registre.GENRES_DU_REGISTRE`). |
| D10 | S0 | `tests/conftest.py` : `GESTIONMPPRO_SAUVEGARDES` et `GESTIONMPPRO_PIECES` vers un dossier temporaire pour toute la séance (G-03). Code `sauvegarde_impossible` (503) ajouté à `api/erreurs.py`. |
| D10 | S2 | G-13 : `services.appareils.acces()` garde `:8050` derrière HTTPS ; reprendre `services.serveur.adresse_de()` (schéma et port de la requête). |
| D10 | D8 | Exposer `services.indicateurs.photographier(s) -> IndicateurJour` : la tâche `photo_indicateurs` l'appelle s'il existe (sinon repli sur `calcul.suivi`). |
| D10 | docs | API-PRO routes 43, 45, 48 et `Sante.taches` : formes de `docs/lots/D10.md` § 3. |
| D2 | docs | Écarts de D2 à API-PRO/ECRANS-PRO/MODELE-DONNEES : routes 82 (`facteurs_cout`), 84/85 (`poids` en liste `{role_id, poids}`), 90/146 (`coefficients` → `saisonnalite`, `modifiees`), 92 (`?date=` sans effet), 97 (`MetierModifie`, `bobines_par_metre`), corps du montage selon API-PRO, origine du montage déduite, étage hors bornes 404 (docs/lots/D2.md § 4). Routes 147, 237, 238 faites par D2. |
| D2 | D8 | Valeur du fil monté dans `/valorisation` et `/cockpit` (moitié valorisation de `test_le_stock_est_en_magasin_ou_en_machine`). |
| D2 | D6 | Réutiliser `recettes.oublies` et `recettes.message_oublies` pour les blocages d'ordre ; remplacer la fabrique `ordre_valide` de D2 par celle de D6. |
| D3 | S4 | La signature du cache du moteur ne voit pas un réglage changé quand l'horloge ne bouge pas (essais à horloge figée ; en production, deux écritures dans la même microseconde) : y faire entrer les `version` (ou un compteur) et pas seulement `modifie_le`. Les essais contournent par `donnees_moteur.invalider()`. |
| D3 | D4, D5 | Appeler `services.commandes.recaler_soldes(s, qui, {bons}, raison)` après validation/annulation d'une réception (D4), après un retour au fournisseur ou une libération de quarantaine (D5, via `commandes_des_lots`). D4 : avertir sans bloquer pour une réception sur un bon numéroté en attente d'approbation. Remplacer la fabrique `fabriques/achats.recevoir` par les vraies réceptions. |
| D3 | docs | Écarts de D3 (docs/lots/D3.md § 4) : schémas 149, 150, 152, 153 plus riches ; route 160 reçoit `lignes` ; `?statut=clos` ; champ `observations` (ECRANS-PRO : `remarques_fournisseur`) ; ECRANS-PRO 4.30 : Excel du bon sans raison sociale → 409 ; route 164 dans `api/commandes/routes_documents.py`. |
| D5 | S1 | Colonne `inventaire.abandon_motif` (aujourd'hui rangé dans `annulation_motif`). |
| D5 | S1/S2 | Essais dépendants de l'ordre : le monde de `tests/modele_monde.py` pose à la main le compteur `BC 2026` et `INV-2026-0001` ; un bon ou un inventaire validé par un essai passé après `test_migrations` fait échouer `test_periode`. Rendre `test_periode` et le monde indépendants des données laissées par les autres essais (les lots datent aujourd'hui au 31/12/2025 pour l'éviter). |
| D5 | docs | API-PRO 122–123 (`Brouillons.lignes`, réponse `valides`/`refuses`/`ignores`), champs ajoutés à `OperationFiche`, `InventaireFiche`, `DefautsInventaire` en `{id, code}` ; ECRANS-PRO P6 : un inventaire ouvert par magasin (index unique), message OR24 de REGLES (docs/lots/D5.md § 4). |
| D5 | D4, D6 | Définir `GENRE_BROUILLON` (protocole `services.brouillons.Genre` : rang 0 réceptions, rang 3 ordres) pour qu'« À valider » montre leurs brouillons ; D6 : partie « ordres » de `test_stock_atelier::test_brouillons_a_valider…`. |
