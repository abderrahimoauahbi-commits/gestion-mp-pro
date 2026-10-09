# Lot RESTES3 — restes côté serveur : ce que les lots suivants doivent savoir

Branche `lot-RESTES3`. Lignes « serveur » et « docs » de `docs/lots/RESTES.md` traitées et
retirées. Ce fichier est écrit **tôt** (demande du coordinateur) : la section 1 est la liste
exacte des changements de forme de l'API, pour RESTES4 (écran), R2 (parité) et C1
(comparaison). `frontend/` n'est pas touché : **`make types` est à relancer** par le lot écran
après la fusion (`types.gen.ts` ne connaît pas les champs ci-dessous).

## 1. Changements de forme de l'API

### 1.1 Codes du stock (S3) — même valeur logique, autre forme

| Champ | Avant (Gestion MP) | Après (PRO) |
|---|---|---|
| `statut`, `statut_couverture` (lignes de stock 103/104, alertes du Cockpit 209, besoins 145, lignes du plan d'achat 149/150) | « ⚫ RUPTURE », « 🔴 CRITIQUE », « 🟠 URGENT », « 🟡 ATTENTION », « 🟢 OK », « ⚪ NON CONSOMMÉE » | `RUPTURE`, `CRITIQUE`, `URGENT`, `ATTENTION`, `OK`, `NON_CONSOMMEE` |
| `action` d'une ligne de stock (103/104 ; `null` pour l'alimentation) | « 📝 Créer BC - <fournisseur> » / « — » | `CREER_BC` / `AUCUNE` |
| `relance` d'une ligne du plan d'achat | « 🔴 CRITIQUE — REF (Fournisseur) — … » | « CRITIQUE — REF (Fournisseur) — … » (« NON CONSOMMÉE » en clair) |

Inchangés (hors de la ligne RESTES) : `tier` (« 🔥 TIER 1 »…), `risque`/`sourcing`
(« 🔴 MONO-SOURCE »), statut de livraison des bons, classement des fournisseurs.
`lib/statuts.ts › cleStock` accepte déjà les codes (`RUPTURE`… et `NON_CONSOMMEE` par
`NON_CONSOMM`) : **rien à changer à l'écran** ; les jeux d'essai de l'écran (`pages/*/essais/*.json`,
`plan-achat/donneesEssai.ts`) portent encore les émojis (lus par `cleStock`, sans effet).
Classeurs : statut écrit en clair (`calcul.constantes.LIBELLES_STATUT`).
**R2 / C1** : comparer par `calcul.constantes.LIBELLES_GESTION_MP` (code → libellé de Gestion
MP) ; la parité unitaire le fait par `tests/moteur/jeux_outils.comme_gestion_mp`.

### 1.2 Stock, lots, traçabilité (S4)

- **103/104** `/stock?date=` passé : `stock_machine`, `valeur_machine_mad`, `sur_les_metiers`
  comptent le fil monté **de ce soir-là** (même chiffre que la Valorisation 210 ; avant : 0) ;
  chaque ligne + `role_id`, `fournisseur_id` ; `EtatStock.magasin_ids` {code → id}
  (`par_magasin` reste indexé par code).
- **105, 108** `MouvementLigne.devise` : `string | null` — `null` hors direction et achats.
- **112** `Tracabilite` + `matiere_id`, `ordre_id` ; `EtapeTracee` + `matiere_id`, `ordre_id`,
  `document_type` (`reception`, `ordre`, `operation`, `inventaire`, `reprise`), `document_id`
  (`null` pour la reprise). La « comparaison par matière » d'un ordre n'est **pas** ajoutée à 112 :
  elle est servie par la consommation de l'ordre (143), une seule source.

### 1.3 Autres routes

| Route | Changement |
|---|---|
| 6, 20 | QR en SVG avec `xmlns="http://www.w3.org/2000/svg"` (s'affiche dans une `<img>`) : le contournement de `administration/qr.ts` peut partir. |
| 101 | `origine` « bureau » pour tout montage des routes 97 et 99, même d'un seul étage (`etage` nul) ; « téléphone » pour la route 100 seulement. |
| 124–127 | `InventaireFiche.abandon_motif` (nouveau) ; `annulation_motif` ne porte plus que le motif d'une annulation. |
| 135–137 | `OrdreResume.metier` = « CODE · Nom » (le code seul quand le nom est vide ou égal). |
| 152, 153 | `CommandeResume` + `en_retard` (la règle de `?filtre=retard`), `arrivee_attendue` (ETA sinon promesse, bon parti ni soldé ni annulé), `arrivee_sous_7_jours` (d'hier à J+7), `kg_en_quarantaine` (Σ des lignes) ; `CommandeFiche` + `promesse_figee` (phrase X-CMD-12/13 ou `null`). Les lignes gardent `en_quarantaine`. |
| 176 | `Pesee.numero` d'un brouillon : « Brouillon ». |
| 175, 187, 228 | `q` trouve un numéro à la ponctuation près (« FA-2026/117 » = « FA-2026-117 »), `services.recherche.trouve`. |
| 222, 223 | Lien de la notification d'un besoin : `/cockpit?signalement=ID` (direction), `/accueil?signalement=ID` (achats), `/atelier` (alimentation). |
| 242 | `/export/plan-achat` accepte les filtres liés de l'écran, **valeurs affichées** : `statut`, `priorite`, `abc`, `fournisseur` (onglet références) ; `urgence`, `devise`, `pays` (onglet fournisseurs). |
| **246** (nouvelle) | `GET /periode-close/brouillons?date=AAAA-MM-JJ` (direction) → `BrouillonsPeriode {jusqu_au, total, genres: [{genre, libelle, nombre}], message}` : ce qui empêcherait de clore jusqu'à cette date (`message` = le refus de la route 26, ou `null`). |
| OR24/OR33 | Refus de libération : « Libérer une quarantaine est une décision de la direction ou des achats, après contrôle de la matière. » (et « … une libération de quarantaine est une décision de la direction ou des achats. », « … c'est une décision de la direction ou des achats, après contrôle. »). |

Révision Alembic **0005** (`0005_motif_d_abandon`) : `inventaire.abandon_motif` (VARCHAR 300,
défaut ''), le motif des inventaires abandonnés y est déplacé ; retour arrière rendu. 686 colonnes.
`tests/matrice_droits.csv` régénéré (route 246).

## 2. Isolation des essais (D4, D5 → S0/S2)

- `tests/base_connue.py` : `photographier(c)` (les semences, une fois après la migration,
  `conftest.schema`) et `remettre(c)` : **toutes** les tables vidées sauf les comptes
  (utilisateurs, sessions, appareils, tentatives), semences et réglages réécrits à leur défaut.
  Dans une transaction annulée (monde de S1, `fabriques.stock.vider`,
  `fabriques.pilotage.usine`) ou validée (fixture **`base_neuve`** de `conftest.py`, pour un
  essai dont le code ouvre ses propres sessions : tâches de fond, clôture par l'API).
- `tests/modele_monde.batir(c)` commence par `remettre(c)` : `test_periode`, `test_modele`,
  `test_modele_contraintes` ne voient plus rien des autres essais (compteur `BC 2026`,
  `REC-2026-0001`, `INV-2026-0001`, brouillons comptés par la clôture).
- Contournements retirés : réceptions des essais datées du 3 août 2026 (`fabriques.receptions.JOUR`,
  avant 31/12/2025), inventaires validés du 30/09/2026 (`JOUR_DES_INVENTAIRES`), fixture
  `menage` (écrivait sans journal) supprimée de 17 modules.
- Essais enchaînés rendus indépendants (le mélange les a trouvés) : `test_importations` (chaque
  essai ses arrivées et son dossier : `_premier`, `_cours_et_fret`), `test_reprise_traductions`
  (`puis_reprendre` : la reprise est refaite après un essai qui vide ou recrée la cible),
  `test_magasins_postes::test_toujours_une_quarantaine_en_service` (`base_neuve`).
- Ordre aléatoire : `pytest --melanger=GRAINE` (ou `GESTIONMPPRO_MELANGE=GRAINE`) mélange les
  modules puis les essais de chaque module (crochet de `conftest.py` ; ni `pytest-randomly` ni
  `pytest-random-order` ne sont dans les dépendances). Vert dans l'ordre normal, en ordre inversé
  des modules et avec les graines 7 et 31 (2 623 essais).

## 3. Outils et Makefile (S0)

- `outils/routes_ecran.py` (branché dans `make verifier-outils`, lecture seule du front) : chaque
  appel écrit `api.get|post|put|supprimer|envoyerFichier`, `useLecture`, `adresseApi` et chaque
  `route: '…'` / `route="…"` de `frontend/src` (essais exclus) doit répondre à une route de
  l'OpenAPI ; les chemins en variable sont comptés et dits (`--detail`), pas vérifiés.
- `tests/test_liens_ecran.py` (reste E2 → S2) : chaque lien écrit par le serveur (services,
  tâches, contrôles ; hors `api/`, `reprise/`) est une adresse d'écran déclarée
  (`pages/*/ecrans.ts`, `App.tsx`).
- Cibles : `make poste-installer` (`deploiement/mac/installer.sh $(ARGS)`), `make coexistence`
  (`essais/coexistence.sh`), `make verifier-chiffres` (`backend/essais/verification_chiffres.py
  $(ARGS)` sur `GESTIONMPPRO_BASE`).

## 4. Essais ajoutés ou complétés (chacun échoue sans sa correction)

- `test_restes3_stock.py` : codes du moteur (stock, plan d'achat, Cockpit, alimentation), fil monté
  d'un soir passé = Valorisation, ids des lignes de stock, ids de la traçabilité, journal sans
  devise pour L, **`test_valorisation::test_api_les_lots_comptent_comme_les_soldes`** (hérité).
- `test_restes3.py` : origine « bureau », retard et arrivées à 7 jours, promesse figée, filtres du
  classeur du plan d'achat, « CODE · Nom », route 246, **`test_direction::test_les_cours_sont_dates`**
  (hérité).
- `test_reprise_traductions.py` : **`test_importations::test_la_reprise_relie_les_dossiers_a_leur_facture`**,
  **`test_importations_second_audit::test_les_morceaux_d_un_ancien_eclatement_redeviennent_une_piece`**
  (héritées, domaine 8, pour R1).
- Complétés : `test_receptions` (kg en quarantaine, promesse figée), `test_receptions_lectures`
  (pesée « Brouillon »), `test_suivi` (liens selon le rôle), `test_factures` (ponctuation),
  `test_inventaires`, `test_inventaires_api` (`abandon_motif`), `test_migrations` (0005 aller-retour),
  `test_operations` (message OR24), `test_appareils` (`xmlns`), `test_liens_ecran`.
- `fabriques.operations.ordre_valide` passe par le service des ordres (`fabriques.ordres.valide`,
  reste D6 → D5) au lieu d'écrire l'ordre à la main.

## 5. Décisions

1. Statuts : les **valeurs** de `calcul.constantes.STATUTS` deviennent les codes ; la logique du
   moteur est inchangée (mêmes comparaisons). Les libellés de Gestion MP restent dans
   `LIBELLES_GESTION_MP` (parité), ceux des classeurs dans `LIBELLES_STATUT`.
2. Origine du montage : pas de colonne (aucune révision de plus) ; `etage` n'est posé que par la
   route 100 (`metiers.monter(..., au_telephone=True)`). Le rejeu du fil monté lit les lignes
   `avant`/`apres`, il ne dépend pas de `etage`.
3. Isolation : remise **à l'état d'installation** (pas de vidage partiel) ; les essais qui comptent
   toute la base passent par elle ; les autres ne regardent que leurs données (`test_erreurs` :
   devises `QQ…` réservées ; `test_appareils`, `test_modele_orm` : leurs seules lignes).
4. Route 246 plutôt qu'un champ de `GET /parametres` : la date à clore est celle que la direction
   choisit dans la fenêtre.

## 6. Ce qui reste

- Écran (RESTES4) : `make types`, puis les adaptations listées au § 1 et dans RESTES.md.
- R2 / C1 : déclarer la nouvelle forme des statuts (§ 1.1) dans la parité et la comparaison.
- LOTS-DE-TRAVAIL § 2 (modules en plus de D2, D6, D8, RESTES3) et critères X2 : non reportés
  (hors des documents confiés).
