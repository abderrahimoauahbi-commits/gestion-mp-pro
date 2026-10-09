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
