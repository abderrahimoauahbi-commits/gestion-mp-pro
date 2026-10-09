# Restes à reprendre (tenu par le coordinateur)

Points relevés par un lot pour un autre, à traiter avant la recette finale.

| Origine | Pour | Point |
|---|---|---|
| R1 | Mohamed (à la livraison) | 4 réceptions de Gestion MP payées en deux devises (LOMAT, USD et EUR) : reprises en une réception (devise de la facture en en-tête, prix des lignes intacts), signalé. À proposer : garder ou scinder. |
| D9 | X1 | Caddy ne doit pas remplacer la CSP posée par l'application (le bouton « Imprimer » est autorisé par son empreinte sha256). |
| F6 | E0 | `lib/statuts.ts` : statuts d'inventaire « Annulé » et « Comptage en cours » (F6 tient sa table dans la page en attendant). |
| F3 | F3 (écran, RESTES4) | Signalements : la forme provisoire `SignalementFiche` de `pages/atelier/types.ts` est à remplacer par `Schema<…>` (routes 221–223 servies, `?mes=true` filtre par le compte). |
| F3 | E1 | `ScanQR` : rendre aussi le texte lu (QR à numéro → `GET /lots/scan`, messages « aucun lot » / « plusieurs lots ») ; `SelecteurLot` : suivre la forme de la route des lots disponibles ; `BoutonImprimer` 44 px en atelier ; 7 tuiles de l'accueil atelier à 360 × 640 (la page défile, sans débordement — textes à raccourcir ?). |
| D7 | F1 | Pastille « factures sans dossier » si l'écran en a besoin (à déclarer). |
| F2 | F2/F3 (unification) | Deux moteurs de saisie d'ordre : `pages/sorties/ordre.ts` + `useSaisieOrdre.ts` (F2) et `pages/atelier/sortie.ts` (F3), mêmes règles et textes : n'en garder qu'un (ECRANS-PRO le veut unique). |
| F2 | E1 | `Bascule` déborde de sa carte sur téléphone ; `Barres` ne sait pas empiler (plan glissant côte à côte au lieu d'« empilées »). |
| F2 | F6 | Déclarer l'adresse d'écran `/operations/:id` (numéros de transferts et retours en liens). |
| D8 | R2, C1 (correction déclarée K7) | PRO compte le fil monté à TOUTE date (rejeu de `montage_evenement`) dans la valorisation, le cockpit, les contrôles et le bilan ; Gestion MP ne le compte qu'au jour même (bilan : à part, mois en cours). Écart voulu (décision de Mohamed : le fil monté est du stock) : à déclarer et prouver dans la parité et la comparaison. |
| F4 | E1 | `Confirmer` : longueur minimale du motif (F4 a écrit `ConfirmerMotif` en attendant). |
| F4 | F4 | Remplacer le `Paiement` provisoire de `receptions/Reglement.tsx` par `Schema<'Paiement'>` (types régénérés après le lot NOMS). |
| NOMS | F1, F5, F8 | Schémas homonymes renommés (champs et routes inchangés), `types.gen.ts` régénéré (il prend aussi les routes de D8 : bilan, cockpit, contrôles, échéancier, pièces, signalements…) : après `git merge main`, citer `Schema<'…'>` par le nouveau nom, jamais par `gestion_mp_pro__api__…`. Importations (F5) : `AnnulationDossier`, `ClotureDossier`, `ReouvertureDossier`, `ValeurDeviseDossier` ; réceptions : `AnnulationReception` ; opérations : `AnnulationOperation`, `ValeurDeviseOperation` ; réclamations : `ClotureReclamation`, `ReouvertureReclamation` ; commandes : `LigneVersionBon` ; qualités : `LigneVersionRecette`, `RestaurationVersionRecette` ; exploitation (F8, sauvegardes) : `RestaurationSauvegarde`. `tests/test_noms_openapi.py` refuse désormais tout nom de schéma à `__` et deux classes exposées homonymes. |
| X2 | C1 | « Administration › Reprise » (routes 243–244) attendue par le poste : à faire dans C1. |
| F5 | E1 | `Interrupteur` sans `manque`/`blocages` ; `PiecesJointes` sans mode « joindre seulement » (dossier clos) ; `LienDocument` sans `state` ; `DataTable` : texte de liste vide filtrée générique, pas de lignes de groupe. |
| F1 | F4 | Fermer une fiche commande ouverte depuis le Cockpit ramène à `/commandes` au lieu du Cockpit (passer `state.retour`). |
| F1 | E1 | `.masque-accessible` (position absolue) allonge le document au téléphone quand `<main>` défile (F1 contourne par `position: relative`). |
| F1 | V3 | Recette navigateur : un profil de navigateur à part par passage (cookies de session partagés entre serveurs `localhost`). |
| F8 | E1 | `FenetreConfirmation` sans étapes (F8 a construit la restauration sur `Fenetre`) ; `Onglets` sans garde de saisie. |
| F8 | F5 | En-tête de `pages/importations/ecrans.ts` : retirer la mention des pages provisoires supprimées. |
| V1 | écran (RESTES4) | Bon reçu sous réserve : la fiche du bon et sa ligne disent « dont X kg reçus sous réserve, en quarantaine : attendus jusqu'à leur libération » (`CommandeFiche.kg_en_quarantaine`, ligne `en_quarantaine`, servis par RESTES3), et l'aide de l'indicateur du Cockpit l'explique ; le reste à livrer garde sa règle. |
| V1 | V2/V5 | Vérification sur la 3e base (copie après le scénario V2) ; familles non recomptées (stock sur les métiers, plan et besoins, projeté, statuts, XYZ, dormants, prévu des ordres non figés, coût d'une qualité, photo du jour, contrôles C06, C08, C13, C15, C17, C18, C20, C22–C25, C30, C32, C33, C35, C38) : à étendre si possible avant la recette. |
| RESTES3 | écran (RESTES4) | `make types` après la fusion de RESTES3, puis s'adapter aux changements de forme listés dans `docs/lots/RESTES3.md` § 1 (statuts en codes, ids des liens, devise nulle pour L, champs des bons, route 246, filtres du classeur du plan d'achat) ; retirer les contournements devenus inutiles (`administration/qr.ts` : `xmlns` ajouté à l'écran ; filtre des retards et arrivées à 7 jours de Ma journée ; reconstitution de « CODE · Nom » ; lien de la cloche filtré). |
