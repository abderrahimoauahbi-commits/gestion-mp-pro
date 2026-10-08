# Gestion MP PRO — lots de travail

Le découpage de la réalisation en lots confiables à des équipes parallèles. Pour chaque lot :
ce qu'il fait, les **fichiers qu'il possède** (seul à les écrire), ses dépendances, ses critères
de fin (essais qui doivent passer), sa vague. Les documents de conception font foi :
`ARCHITECTURE.md` (structure, conventions), `MODELE-DONNEES.md` (schéma), `API-PRO.md` (routes),
`ECRANS-PRO.md` (écrans), `heritage/*` (métier, messages, calculs, essais à porter),
`heritage/PLAN-DE-RECETTE-PRO.md` (vérification).

---

## 0. Règles communes à tous les lots

1. **Propriété des fichiers** : un fichier n'a qu'un lot propriétaire. Un lot qui a besoin d'un
   changement dans le fichier d'un autre le demande au propriétaire (ou au coordinateur) ; il
   ne l'écrit pas. Les fichiers partagés par construction ont une règle (§ 0.3).
2. **Contrats gelés tôt** : les noms de tables et colonnes (MODELE-DONNEES), de routes et de
   schémas (API-PRO), de composants et de routes d'écran (ECRANS-PRO) ne changent qu'en
   changeant d'abord le document, par le coordinateur.
3. **Définition de « fini »** pour tout lot : `make verifier` vert sur sa partie (ruff, ruff
   format, mypy strict pour `services/` et `calcul/`, pytest ; ou prettier, eslint, tsc, vitest) ;
   plafonds 400 lignes/fichier, 60 lignes/fonction ; docstrings ; chaque preuve héritée de son
   domaine portée avec son identifiant d'origine (`Hérité : test_x::test_y`) ; messages de refus
   de `heritage/REGLES.md` repris mot pour mot ; aucun `print` ; un commit = un changement, titre
   ≤ 72 caractères à l'impératif.
4. **Bases** : chaque lot travaille sur `gestion_mp_pro_essai` (pytest) ou une base à son nom
   finissant par `_essai`. Jamais `gestion_mp`, `gestion_mp_comparaison`, ni `~/gestion-mp`,
   `~/erp-fil`, `~/gmao*` en écriture.
5. **Horloge fixe** dans les essais (2026-10-08) via `services/horloge.py`.

### 0.1 Vagues

```
Vague 0  S0 socle serveur ─────────────── E0 socle écran
Vague 1  S1 modèle+migrations   S3 moteur (pur)   E1 composants
Vague 2  S2 sécurité+socle métier   S4 stock+chargeur   E2 coque+navigation   R1 reprise
Vague 3  D1 … D10 domaines serveur (parallèles)                F1 … F8 écrans (dès que le schéma
                                                                d'API de leur domaine est fusionné)
Vague 4  R2 parité   C1 comparaison   X1 serveur   X2 poste Mac   V1 chiffres   V2 scénario
Vague 5  V3 recette navigateur   V4 charge et concurrence   X3 documentation d'exploitation
Vague 6  V5 recette finale, documents, livraison
```

### 0.2 Graphe des dépendances

| Lot | Dépend de |
|---|---|
| S0 | — |
| E0 | — |
| S1 | S0 |
| S3 | S0 (aucune base : peut avancer en même temps que S1) |
| E1 | E0 |
| S2 | S1 |
| S4 | S1, S3 |
| E2 | E1, contrat des routes 1–22, 53–56 (S2) |
| R1 | S1 (écriture directe des tables, sans les services), S2 (`audit` neutralisé pendant la reprise) |
| D1–D10 | S2, S4 (D1 en premier pour les fabriques de référentiels, voir § 0.3) |
| F1–F8 | E2 + schémas d'API de leur domaine (OpenAPI fusionné) ; les essais d'intégration attendent le domaine serveur |
| R2 | R1, D1–D8 |
| C1 | R1, R2, D1–D9, X2 (les deux serveurs sur le Mac) |
| X1, X2 | S0, E2 ; finalisés après D10 |
| V1 | D1–D8 (`/donnees/{table}`) |
| V2 | D1–D10, F1–F8 |
| V3 | F1–F8, X1 |
| V4 | D1–D10, X1 |
| X3 | X1, X2, D10 |
| V5 | tous |

### 0.3 Fichiers partagés par construction

| Fichier | Propriétaire | Règle pour les autres lots |
|---|---|---|
| `backend/gestion_mp_pro/api/__init__.py` (liste des routeurs) | S0 | pré-rempli par S0 avec **tous** les domaines (modules vides) ; personne d'autre ne l'édite |
| `backend/gestion_mp_pro/modeles/*` | S1 | un domaine qui veut une colonne la demande à S1 (changement de MODELE-DONNEES + révision Alembic par S1) |
| `backend/gestion_mp_pro/migrations/versions/*` | S1 puis le coordinateur | une seule file de révisions ; numéro réservé auprès du coordinateur (jamais deux révisions de même numéro : leçon des étapes 10 et 12) |
| `backend/gestion_mp_pro/api/erreurs.py` (codes) | S0 | codes de tous les domaines pré-déclarés par S0 depuis API-PRO § 0.3 ; ajout sur demande |
| `backend/tests/fabrique.py` | S2 (comptes, sessions) ; `tests/fabriques/<domaine>.py` par chaque lot D | chaque lot D écrit ses fabriques dans son fichier |
| `backend/tests/matrice_droits.csv` | **généré** (`make matrice`) | jamais édité à la main ; régénéré et relu dans chaque lot D |
| `frontend/src/routes.ts` | E2 | agrège `pages/<domaine>/ecrans.ts` (un fichier par lot F) |
| `frontend/src/aide.json` | E2 (structure, sections communes, Mode d'emploi) | chaque lot F n'écrit que les clés de ses écrans (`ecran.<cle>`) et les formules de ses KPI (`formule.<cle>`) ; clés triées pour limiter les conflits |
| `frontend/src/lib/types.gen.ts` | **généré** (`scripts/generer_types.sh`) | jamais édité |
| `frontend/src/styles/jetons.css` | E1 | ajout de jeton sur demande |
| `docs/*` de conception | coordinateur | |

---

## 1. Fondations serveur

### S0 — Socle du dépôt et du serveur

- **Fait** : dépôt, `pyproject.toml` (bornes minimales, `[build-system]`, paquets, ruff, mypy,
  pytest), `requirements.lock`, `Makefile` (installer, verifier, essais, matrice, types, parite,
  comparer, construire, docker), `.pre-commit-config.yaml`, `.editorconfig`, `.gitignore` ;
  `config.py` (toutes les `GESTIONMPPRO_*` de ARCHITECTURE § 16), `journalisation.py`,
  `main.py` (application, cycle de vie, middlewares `trace` et `protections`, en-têtes,
  `X-Heure-Serveur`, service de l'écran, refus 503 si schéma en retard), `db.py` (moteur,
  sessions, verrous nommés), `api/__init__.py`, `api/erreurs.py` (convention unique, traduction
  française des erreurs Pydantic reprise de Gestion MP, 500 tracé), `api/dependances.py`,
  `api/communs.py` (`Page[T]`), `services/horloge.py`, squelettes vides des domaines.
- **Possède** : les fichiers cités, `README.md` (première version), `backend/tests/conftest.py`
  (garde-fou `_essai`, horloge fixe, client avec en-tête, schéma recréé par Alembic).
- **Fini quand** : `make verifier` passe sur un dépôt vide de métier ; `test_erreurs.py` (422
  traduit, 404, 409, 500 tracé avec référence, jamais de 500 pour un corps faux) ;
  `test_config.py` (aucune lecture de `os.environ` hors `config.py`, valeurs par défaut,
  coexistence : port 8050, cookie, base, dossiers ≠ Gestion MP) ; `test_entetes.py`
  (anti-falsification sur toute écriture y compris la déconnexion, en-têtes de sécurité même sur
  les refus du middleware, `X-Heure-Serveur`, `X-Requete`) ; journal serveur d'une ligne par requête.

### S1 — Modèle de données et migrations

- **Fait** : `modeles/` complet (71 tables, 32 énumérations, contraintes, index, triggers,
  FK composites, colonnes `texte_recherche` et leur écouteur), `migrations/` (`env.py`,
  `0001_schema_initial`, `0002_semences`), `services/installation.migrer()` (Alembic sous verrou
  `MIGRATION`).
- **Possède** : `backend/gestion_mp_pro/modeles/**`, `backend/gestion_mp_pro/migrations/**`,
  `backend/alembic.ini`, `services/installation.py`, `tests/test_migrations.py`,
  `tests/test_modele.py`.
- **Dépend de** : S0.
- **Fini quand** : `test_migrations.py` (identifiants contigus 0001…N ; `upgrade head` sur base
  vide puis relancé = rien ; `downgrade base` + `upgrade head` ; `alembic check` vide ; deux
  processus simultanés : une application ; aucune révision n'importe `gestion_mp_pro`) ;
  `test_modele.py` (chaque CHECK de MODELE-DONNEES refuse sa valeur interdite : un cas par
  contrainte ; FK composites ; immuabilité de `mouvement` ; défauts serveur = défauts ORM ;
  semences : 8 rôles, 11 postes, 3 devises, 2 magasins, motifs R1–R6, 55 réglages) ; schéma
  comparé à MODELE-DONNEES par un script qui liste tables et colonnes.

### S2 — Sécurité, audit et socle métier transverse

- **Fait** : `securite.py` (sessions, appareils, `acteur`, `droit()`, matrice générée,
  `sans_prix` générique et `CLES_MONETAIRES`, `journal()`), `services/audit.py` (avant/après,
  historique), `services/numerotation.py`, `services/periode.py`, `services/notifications.py`,
  `services/recherche.py` (normalisation, recherche globale extensible par domaine),
  `services/comptes.py`, `services/appareils.py` ; routes 1–22, 49–56 et leurs schémas.
- **Possède** : `securite.py`, `services/{audit,numerotation,periode,notifications,recherche,comptes,appareils}.py`,
  `api/{systeme,comptes,journal,notifications}/**`, `tests/fabrique.py`,
  `tests/test_securite.py`, `test_matrice_droits.py`, `test_prix_masques.py` (le balayage, nourri
  ensuite par les domaines), `test_comptes.py`, `test_audit.py`, `test_numerotation.py`, `test_periode.py`.
- **Dépend de** : S1.
- **Fini quand** : essais repris de Gestion MP domaine 1 (12 preuves) ; installation une fois ;
  connexion, blocage après 5 échecs, 429 ; changement de code ferme les autres sessions ; compte
  désactivé ; toujours une direction ; code de l'alimentation à 4 chiffres ; visages réservés au
  poste local ou à un appareil enrôlé ; enrôlement à usage unique ; `test_toute_route_declare_ses_roles` ;
  `sans_prix` (dictionnaires imbriqués, listes, toutes les clés de la liste) ; numéros sans trou
  sous 20 validations parallèles ; `date_permise` et `cout_hors_periode_close` (messages exacts) ;
  journal avec avant/après ; historique d'une fiche ; administrateur refusé sur toute route
  métier (vérifié sur la matrice dès qu'elle grossit).

### S3 — Moteur de calcul (pur)

- **Fait** : `calcul/` complet (ARCHITECTURE § 3) : portage **fonction par fonction** de
  `gestion_mp/calcul/moteur.py`, `modele.py`, `classification.py`, `controles.py`, et des
  calculs logés dans `depot.py` et les routes (`heritage/CALCULS.md` parties A et B), méthode
  « corrigée » seule, fonctions ≤ 60 lignes, contrôles en registre.
- **Possède** : `backend/gestion_mp_pro/calcul/**`, `backend/tests/moteur/**`.
- **Dépend de** : S0 (aucune base).
- **Fini quand** : tous les essais « moteur » de `heritage/ESSAIS.md` portés (valeurs attendues
  à l'identique : 12 800, 1 438, 482, 26,89…) ; un essai par contrôle C01–C38 (donnée qui le fait
  sonner, nombre exact, gravité, `quoi_faire`, lien) ; essais de propriétés (hypothesis) : soldes =
  journal, aucun lot sous zéro, valeur conservée, annulation au coût de l'original, état à une
  date passée indépendant des écritures postérieures ; **parité unitaire** : sur 20 jeux de
  `Donnees` tirés de la base de comparaison et figés en JSON (`tests/moteur/jeux/`), les sorties
  sont égales à celles du moteur de Gestion MP (fichiers produits une fois par
  `backend/essais/gestion_mp_calcul.py`).

### S4 — Chargeur du moteur, écriture du stock, lots

- **Fait** : `services/donnees_moteur.py` (requêtes groupées, traduction en `Donnees`, cache par
  signature lue en base, `charger_au`), `services/stock.py` (seul chemin d'écriture :
  `lot_ou_creer`, `ecrire`, `transferer`, `contrepasser`, `couvert_a_sa_date`, suspension par
  inventaire **limitée au périmètre**), `services/conversions.py`, `services/lots.py` ; routes
  103–114 et 236.
- **Possède** : ces fichiers, `api/stock/**`, `exports/stock.py`, `tests/test_stock.py`,
  `tests/test_ecriture_stock.py`, `tests/test_donnees_moteur.py`, `tests/fabriques/stock.py`.
- **Dépend de** : S1, S3 (S2 pour les routes).
- **Fini quand** : essais hérités du domaine 9 (partie stock, 36 preuves avec le lot D5) ; refus
  de `ecrire` mot pour mot (SR3–SR9) ; écriture sous verrou, deux sorties de 70 % d'un même lot
  (50 répétitions : jamais de négatif) ; contre-passation unique, datée comme l'original ; cours
  figé ; seul chemin (essai qui cherche `Mouvement(` hors `services/stock.py` et `reprise/`) ;
  cache jamais périmé (écriture puis lecture immédiate, deux processus) ; `charger_au` égal au
  moteur de Gestion MP sur les jeux figés ; aucune requête par ligne (compteur de requêtes).

---

## 2. Domaines serveur (vague 3, parallèles)

Chaque lot D possède `services/<domaine>.py`, `api/<domaine>/{routes,schemas}.py`, ses exports
et gabarits s'il en a, `tests/test_<domaine>.py`, `tests/fabriques/<domaine>.py`. Critères
communs : les preuves héritées du domaine portées ; une **table de transitions** (statut × geste
× rôle → code et statut suivant) rejouée exhaustivement pour ses documents ; `version` périmée →
409 sur chaque écriture ; chaque route listée dans API-PRO avec son `response_model`, `summary`
et ses `responses` (`test_catalogue_api.py` compare OpenAPI et API-PRO) ; balayage « aucun prix »
de ses routes GET en rôle L ; matrice régénérée sans écart.

| Lot | Domaine | Routes (API-PRO) | Possède en plus | Preuves héritées (ESSAIS.md) et essais propres |
|---|---|---|---|---|
| **D1** | Référentiels et réglages : classification, fournisseurs, matières (fiche, composition, classement, tableur), devises, magasins, postes de frais, codes douaniers, motifs, réglages (registre des 55 + techniques), période close | 23–42, 57–81 | `services/{reglages,registre_reglages,devises,classification,fournisseurs,matieres,tableur_matieres}.py`, `exports/referentiels.py` | domaine 2 (26), domaine 3 partie fiche (19 avec D2) ; tableur : doublons, bornes, longueurs, version, aperçu = application ; ordres des réglages ; période close (motif, journal) ; L refusé sur réglages et devises |
| **D2** | Qualités, recettes et versions, plan (versions), nomenclature, métiers, étages, montage (effet, alerte 30 j, événements) | 82–102, 145–148 (avec D6 pour le réalisé) | `services/{qualites,metiers,production}.py` (plan et besoins), `exports/` qualités, métiers, production | domaine 3 (recettes au mètre), domaine 11 (plan, versions, passé jugé sur son époque) ; 100 % par rôle à 0,01 ; restauration avec motif ; montage de deux téléphones (version d'étage) ; texte unique « sur les métiers » |
| **D3** | Plan d'achat, préparation, commandes, approbation (garde-fou, versions parties, décisions), bon fournisseur (document + Excel) | 149–166, 242 | `services/{plan_achat,commandes,approbation}.py`, `documents/gabarits/bon_commande.html`, `documents/anglais.py`, `exports/{achats,bon_fournisseur}.py` | domaine 4 (23) + domaine 11 (plan d'achat) ; table de transitions des bons (6 statuts × 10 gestes × 4 rôles) ; double envoi, double approbation, approbation contre modification ; bon : A4, anglais, papier à en-tête, **aucun prix, montant ni devise** dans le HTML et l'xlsx |
| **D4** | Réceptions (deux devises en une requête), factures, lot interne à la validation, quarantaine, réclamations, pesées, bobines | 167–186 | `services/{receptions,factures,reclamations}.py`, `exports/receptions.py` | domaines 5 (31), 6 (13, avec D8), 7 (5) ; excédent sous verrou (tous lots) ; réception toute refusée annulable ; recalage calculé sans écriture à la lecture ; solder contre recevoir |
| **D5** | Opérations (droits par type, `valider: true`), brouillons et « Tout valider », inventaires (périmètre, comptages, lots trouvés, abandon, tournant), feuille de comptage | 115–133, 239–241 | `services/{operations,brouillons,inventaires}.py`, `documents/gabarits/feuille_comptage.html`, `exports/` opérations et inventaires | domaine 9 (36, avec S4) ; validation d'inventaire contre sortie ; suspension limitée au périmètre (K2) ; abandon conservé (K3) ; libération réservée D, A ; mise en quarantaine par L |
| **D6** | Ordres de fabrication (proposition FIFO, brouillons, validation sous verrou, annulation avec retours), consommation, réalisé | 134–144, 147 | `services/ordres.py`, `exports/ordres.py` | domaine 9 (ordres), 11 (réalisé) ; numéros d'OF dans l'ordre des dates (courses) ; prévu figé ; deux retours de 70 % ; annuler un ordre annule ses retours et supprime ses brouillons de retour |
| **D7** | Importations (dossiers, rattachement, lignes, cours, frais, parts figées, clôture, réouverture, annulation), coût de revient, coût d'une qualité | 187–208 | `services/{importations,analyse_revient}.py`, `exports/importations.py` | domaine 8 (39) ; les deux courses (ouverture contre annulation de réception, facture corrigée) ; clôture contre ajout de frais ; coût de revient d'un lot au millionième (32,747048 MAD/kg) |
| **D8** | Pilotage et suivi : cockpit, valorisation, prix, opportunités, contrôles (et détail), performance, signalements, pièces jointes, échéancier, indicateurs, bilan (données et document), données brutes | 7, 209–235 (sauf ceux d'autres lots) | `services/{pilotage,suivi,pieces,echeancier,indicateurs,bilan}.py`, `documents/gabarits/bilan.html`, `exports/{pilotage,echeancier}.py` | domaines 10 (27), 12 (27) ; un essai par contrôle par l'API ; écart (%) sur une échelle ; bilan équilibré (kg et MAD) ; pièces : types, taille, traversée de chemin, `attachment`, retrait logique |
| **D9** | Documents et exports communs : `documents/rendu.py` (papier à en-tête), `qr.py`, étiquettes, `exports/classeur.py` (conventions), journal (export) | 52, 114 (rendu), 133/164/234 (environnement commun) | `documents/{rendu,qr}.py`, `documents/gabarits/{_papier_a_en_tete,_impression.css,etiquettes}.html`, `exports/{classeur,journal}.py` | `test_documents.py` (A4, en-tête : ICE, R.C, N.I.F, C.N.S.S, patente, banques ; QR décodé = adresse du lot ; « QUARANTAINE — NE PAS SORTIR ») ; `test_exports.py` (formats, vraies dates, `=` en texte, filtres = écran) |
| **D10** | Exploitation applicative : sauvegardes (pièces comprises), restauration (migre, garde les pièces), tâches de fond, courriels (file), santé, serveur, purges, alertes | 1, 4, 43–48 | `services/{sauvegarde,courriel,indicateurs (photo)}.py` (photo partagée avec D8 : D10 possède la tâche, D8 le calcul), `taches/**`, `api/exploitation/**` | `test_sauvegarde.py` (relue, copie, purge 14 + 12, restauration réelle dans une base jetable : comptes et empreintes identiques, < 30 s, autres sessions coupées, sauvegarde d'une autre base refusée) ; `test_taches.py` (un seul porteur à deux processus, isolement des échecs, courriel du lundi une fois, reprises) ; `/sante` (version, schéma, âge **de cette base**, 26 h) |

Ordre conseillé dans la vague : D1 d'abord (fabriques de référentiels utilisées par tous), puis
D2–D10 en parallèle.

---

## 3. Fondations écran

### E0 — Socle de l'écran

- **Fait** : `frontend/` (Vite 7, React 19, TS strict, React Router 7, TanStack Query 5),
  `eslint.config.js`, `.prettierrc.json`, stylelint, vitest + Testing Library + jsdom,
  `npm run verifier`, `lib/` (api, requetes, heure, format, recherche, unites, teintes, adresse,
  statuts), `scripts/generer_types.sh`, `public/` (manifeste, `sw.js`, icônes), `styles/base.css`.
- **Possède** : `frontend/` sauf `composants/`, `pages/`, `routes.ts`, `aide.json`.
- **Fini quand** : `npm run verifier` vert ; essais `format` (toute la table de ARCHITECTURE § 9.3,
  jamais « -0 », arrondi d'Excel), `recherche` (« frise rouge » → « IMP FRISÉ ROUGE », `%` et `_`
  littéraux), `unites` (kg ↔ bobines ↔ palettes, arrondi dit), `heure` (décalage serveur), `api`
  (en-tête, `{detail, code}`, relance sur statut seulement) ; types générés depuis l'OpenAPI.

### E1 — Système de composants

- **Fait** : tous les composants de ECRANS-PRO § 3 (`coque/` excepté), `styles/jetons.css`.
- **Possède** : `frontend/src/composants/{mise-en-page,tableaux,saisie,retour,graphiques,documents,atelier}/**`,
  `styles/jetons.css`.
- **Fini quand** : un fichier d'essai par composant (≥ 40 essais) : `DataTable` (tri numérique et
  naturel, recherche multi-mots sur champs cachés, filtres liés, « Effacer les filtres », export
  avec filtres, totaux sans mélange d'unités) ; `Cadre` (hauteur restante) ; `Fenetre` (garde
  `sale`, pile, Échap) ; `Confirmer` (sur place, motif exigé) ; `Bouton` (raison obligatoire si
  grisé, texte sous le bouton en mode atelier) ; `Selecteur` (clavier) ; `Quantite` ; `Kpi`
  (formule obligatoire) ; `Badge` (table complète des statuts) ; cibles ≥ 44 px des composants
  d'atelier ; aucune couleur hors `jetons.css` (stylelint).

### E2 — Coque, navigation, connexion, aide

- **Fait** : `composants/coque/**`, `App.tsx`, `routes.ts` (agrégation des `pages/*/ecrans.ts`),
  `lib/session.tsx`, `lib/droits.ts`, `pages/connexion/` (connexion par visages ou identifiant,
  installation), `pages/aide/` (Mode d'emploi à 7 onglets depuis `aide.json`),
  `pages/compte/`, `aide.json` (structure et sections communes), `scripts/generer_notice.py`.
- **Possède** : ces fichiers.
- **Dépend de** : E1 ; routes 1–22, 49–56 (S2).
- **Fini quand** : menu de chaque rôle (tableau de ECRANS-PRO § 2.1) ; chaque entrée permise ;
  écran interdit → accueil + bandeau ; arrivée par rôle et par appareil ; `/lot/:id` selon
  appareil et rôle ; recherche globale au clavier, filtrée ; cloche ; menu du compte ;
  déconnexion confirmée ; chaque écran a son aide ; `docs/NOTICE.md` généré ; menu tient en
  1366 × 768.

---

## 4. Domaines écran (vague 3–4, parallèles)

Chaque lot F possède `frontend/src/pages/<domaine>/**` (dont `ecrans.ts`, ses hooks de
formulaire `useX.ts`, ses essais) et ses clés de `aide.json`. Critères communs : chaque geste
de sa partie de ECRANS-PRO a sa réalisation et sa route ; chaque anomalie de sa partie est
traitée ; aucune page ne défile à 1366 × 768 (essai de mesure par la recette V3, et vitest pour
les cadres) ; tout bouton grisé a sa raison ; aucune saisie perdue ; vocabulaire unique ;
aucun prix dans le DOM pour L ; `outils/routes_ecran.py` sans route manquante ; fichiers ≤ 400
lignes (une liste, une fiche, des sous-composants).

| Lot | Écrans (ECRANS-PRO § 6) | Dépend des lots serveur | Essais propres (en plus des communs) |
|---|---|---|---|
| **F1** | Ma journée, Cockpit (5 onglets, six KPI avec formule), bilan (bouton) — partie 1 | D3, D4, D8 | ordre exact des tâches de Ma journée ; chaque tâche ouvre le document s'il est seul, la liste filtrée sinon ; KPI = valeurs reçues sans recalcul |
| **F2** | Stock (5 onglets, fiche matière, fiche de lot, traçabilité, À valider), Sorties (3 onglets, fiche, saisie, retour au bureau), Production (4 onglets, d'où vient le besoin) — partie 2 | S4, D5, D6, D2 | « Demande pendant le délai » : l'addition affichée tombe juste ; « Tout valider » ne compte que ce qui sera validé ; saisie d'ordre et retour : blocages annoncés |
| **F3** | Atelier au téléphone (17 écrans), Métiers à tisser (bureau), étiquettes — partie 3 | D5, D6, D2, S4 | 360 × 640 et 375 × 812 sans débordement ; cibles ≥ 44 px ; saisie gardée ; « Pas de réseau » ; conversions ; montage : effet annoncé, texte unique |
| **F4** | Plan d'achat, préparation, Commandes (fiche à 7 onglets), Réceptions (saisie, fiche, réclamations, bobines, pesées), bon fournisseur — partie 4 | D3, D4 | préparation en kg **et** palettes ; « Envoyer, ou demander l'approbation » ; camion en deux devises en une requête ; bon imprimé ouvert dans un nouvel onglet |
| **F5** | Importations (3 onglets, choix de facture, nouveau dossier, fiche à 8 onglets), Coût de revient (3 vues), Postes de frais, Codes douaniers — partie 5 | D7, D1 | alertes de clôture énumérées dans la `FenetreConfirmation` ; frais non répartis à part partout ; état de l'analyse dans l'adresse |
| **F6** | Inventaire (ouverture avec périmètre, comptage, lot trouvé, feuille), Opérations (5 onglets, fiche, ligne) — partie 6 | D5 | justification exigée au-delà de la tolérance ; recomptage par la même personne signalé ; feuille à l'aveugle / recomptage |
| **F7** | Catalogue (matières, fiche, tableur, classification, classement, fournisseurs, fiche), Qualités (liste, nomenclature, fiche à 4 onglets) — partie 7 | D1, D2 | 409 « modifiée entre-temps par X » avec « Recharger » ; référence composée semi-automatique ; aperçu du tableur = application |
| **F8** | Analyse (9 onglets), Réglages (6 onglets), Administration (8 onglets), Bilan du mois — partie 8 | D8, D1, D10, S2 | 55 réglages : bornes et ordres contrôlés à la frappe ; clôture de période en fenêtre avec motif ; restauration : confirmation puis fenêtre « J'ai compris » ; journal avec avant/après |

---

## 5. Reprise, parité, comparaison

### R1 — Reprise rejouable depuis `gestion_mp`

- **Fait** : `backend/gestion_mp_pro/reprise/**` (MODELE-DONNEES § 10) : photo lecture seule de
  la source, normalisation, personnes, référentiels, activité (ids et numéros gardés), journal en
  tables (plan, soldes à la main, décisions, annulations, montages), pièces jointes copiées,
  compteurs et séquences, contrôle et rapport ; modes `referentiels`, `activite`, `tout`,
  `--remplacer-activite`, `--essai` ; `outils/vider_activite.py` (base vide de référence).
- **Possède** : ces fichiers, `tests/test_reprise.py`, `essais/resultat-reprise.txt`.
- **Dépend de** : S1 (écrit les tables directement ; neutralise l'écouteur d'audit et le trigger
  d'immuabilité sous le rôle propriétaire, dans sa transaction).
- **Fini quand** : sur une copie de `gestion_mp` et sur une copie de `gestion_mp_comparaison` :
  comptes de lignes par table égaux ; Σ quantités et Σ quantité × prix par matière égaux (à
  l'arrondi déclaré près, rapporté) ; soldes = journal ; mêmes numéros ; mêmes recettes et plans
  versionnés ; rejouée sans changement = rien créé ; rejouée après des gestes dans Gestion MP =
  activité remplacée, référentiels mis à jour ; refus d'écraser une activité saisie dans PRO sans
  `--remplacer-activite` ; empreinte de la source identique avant et après ; **aucune écriture
  dans `gestion_mp`** (transaction `READ ONLY`, vérifiée) ; < 1 minute au volume réel.

### R2 — Parité de calcul PRO = Gestion MP sur l'année d'essai

- **Fait** : `backend/essais/parite_gestion_mp.py` et `backend/essais/gestion_mp_calcul.py`
  (PLAN-DE-RECETTE § 7) : copie normalisée de `gestion_mp_comparaison`, deux calculs, JSON
  canoniques, 13 dates (+ 6 au milieu d'un mois), parité statique, par l'API, dynamique (le
  scénario V2 joué geste par geste dans les deux) ; règles d'explication K1–K6 ; réciproque.
- **Possède** : ces fichiers, `essais/resultat-parite.txt`.
- **Dépend de** : R1, D1–D8 (dynamique : V2).
- **Fini quand** : critère A6 : **0 écart à corriger**, explications limitées aux champs ajoutés
  et aux corrections déclarées, chacune vérifiée en forme et en ampleur.

### C1 — Comparaison avec Gestion MP en service

- **Fait** : `outils/comparer_avec_gestion_mp.py` et `outils/gestion_mp_extraire.py`
  (ARCHITECTURE § 14.3) : même base (signature de la dernière reprise, `--resynchroniser`),
  modes `api` et `moteurs`, sections (stocks, lots, valeurs, CMUP, journal valorisé, besoins,
  plan d'achat, contrôles, cockpit, coût de revient des dossiers, commandes, performance,
  ordres, échéancier, bilan), dates multiples, tolérances, règles d'explication, rapport
  Markdown ; onglet Administration › Reprise (routes 243–244 : état du miroir, « Rafraîchir le miroir » par la direction) qui lance R1 ;
  **`docs/COMPARAISON-GESTION-MP.md`** : (1) chiffres identiques prouvés (rapports datés,
  versions des deux logiciels) ; (2) tableau des différences d'écran, de structure, de sécurité
  et d'exploitation, chacune expliquée (exigence, décision, fichier).
- **Possède** : `backend/gestion_mp_pro/api/reprise/**` (routes 243–244), `outils/comparer_avec_gestion_mp.py`, `outils/gestion_mp_extraire.py`,
  `docs/COMPARAISON-GESTION-MP.md`, `essais/resultat-comparaison-*.md`,
  `tests/test_comparateur.py`.
- **Dépend de** : R1, R2, D1–D9, X2.
- **Fini quand** : sur le Mac, Gestion MP (8030) et PRO (8050) en service côte à côte, miroir
  rafraîchi : rapport à la date du jour et aux 12 fins de mois avec « à corriger : 0 » ; le
  comparateur **voit** les fautes injectées par son essai (CMUP × 1,1 côté PRO, un contrôle
  muet, un stock décalé d'1 kg, un coût de revient faux) ; il refuse de comparer deux bases
  désynchronisées ; aucune écriture dans `gestion_mp` ni dans `~/gestion-mp` ; le document
  liste toutes les différences de ECRANS-PRO § 5, ARCHITECTURE § 2 et § 17, API-PRO § 2 et
  MODELE-DONNEES § 10.5, chacune avec sa raison. Une différence qui vient d'une **correction faite
  depuis dans Gestion MP** est soit reportée dans PRO (demande au lot du domaine), soit déclarée.

---

## 6. Exploitation

### X1 — Serveur : Docker Compose, Caddy, systemd

- **Possède** : `deploiement/{Dockerfile,docker-compose.yml,Caddyfile,exemple.env,gestion-mp-pro.service}`,
  `.dockerignore`.
- **Dépend de** : S0, E2 (finalisé après D10).
- **Fini quand** : image **construite** ; `docker compose up` sur une machine propre : base,
  application (2 processus, non root, `HEALTHCHECK` vert), Caddy HTTPS (`tls internal`) ;
  migration au démarrage ; sauvegarde quotidienne écrite dans le volume, copie externe montée ;
  `docker compose down && up` sans perte ; service systemd essayé sur une VM Linux ; CSP sans
  erreur dans la console (recette V3 à travers Caddy).

### X2 — Poste Mac : launchd, copie figée, coexistence

- **Possède** : `deploiement/mac/**`, `scripts/{demarrer,arreter,sauvegarder,restaurer}.sh`.
- **Dépend de** : S0, E2, D10.
- **Fini quand** : `installer.sh` idempotent (base et rôle `gestion_mp_pro`, venv, écran construit,
  LaunchAgent, raccourci « Gestion MP PRO ») ; démarrage automatique à l'ouverture de session et
  relance après `kill` ; copie figée (`VERSION` lu par `/api/sante`) ; **coexistence** : Gestion
  MP (8030) et PRO (8050) tournent ensemble, deux raccourcis, deux bases, aucun port, dossier,
  cookie ni verrou partagé (tableau ARCHITECTURE § 14.1 vérifié point par point par
  `essais/coexistence.sh`) ; arrêter PRO n'arrête pas Gestion MP et inversement ;
  `restaurer.sh` tout ou rien, pièces comprises, migration à `head`.

### X3 — Documentation d'exploitation

- **Possède** : `docs/EXPLOITATION.md`, section « Avant d'ouvrir au réseau » du README.
- **Fini quand** : installation (Mac, serveur), variables, démarrage et arrêt, coexistence,
  sauvegardes (où, combien, comment vérifier), essai de restauration mensuel, restauration,
  reprise et miroir, comparaison, appareils de l'atelier (enrôlement, HTTPS, Tailscale),
  surveillance (`/api/sante`), journaux, mise à jour de version, base vide de référence ; chaque
  procédure **jouée** une fois et datée.

---

## 7. Vérification

| Lot | Fait | Possède | Fini quand (critères de PLAN-DE-RECETTE § 0) |
|---|---|---|---|
| **V1** | Vérification indépendante des chiffres (lit `/donnees/{table}` et les écrans, n'importe pas le paquet) | `backend/essais/verification_chiffres.py`, `tests/test_verification.py` | A5 : 0 écart sur 3 bases, ≥ 150 vérifications par base, 13 dates ; voit les fautes injectées (CMUP × 1,1, ancien coût moyen, écriture sous zéro, mauvaise clé, OTIF sur toutes les réceptions, solde faussé) |
| **V2** | Scénario de bout en bout (un mois d'usine, 23 étapes, chaque rôle avec son compte) | `essais/scenario_complet.py` | A7 : toutes les étapes, ≥ 400 valeurs vérifiées, calculées à la main d'avance ; rejoué dans Gestion MP pour la parité dynamique (R2) |
| **V3** | Recette navigateur par rôle et par écran ; parcours par vrais clics des trois recettes de Gestion MP | `essais/recette_navigateur.js`, `essais/resultat-recette-ecran.txt` | A8 : 0 anomalie ; aucune page ne défile en 1366 × 768 ; atelier en 360 × 640 ; aucun montant chez L ; chaque défaut des recettes de Gestion MP absent |
| **V4** | Charge (réel, ×10, ×30, vrai serveur) et concurrence (courses, 50 répétitions) | `backend/essais/{charge,concurrence}.py`, `tests/test_concurrence.py` | A9, A10 |
| **V5** | Recette finale et livraison : `outils/verifier_heritage.py` (292 preuves citées), robustesse (corps générés depuis l'OpenAPI : 0 erreur 500), `docs/RECETTE.md`, `docs/CAHIER-DES-CHARGES.md`, README final | ces fichiers | A1–A14 tous tenus ; RECETTE.md donne le verdict par critère, les anomalies corrigées (chacune avec son essai), l'état PRO de chaque défaut des recettes et audits de Gestion MP, ce qui n'a pas pu être essayé, et les questions restant à Mohamed (ARCHITECTURE T14, ECRANS-PRO E4, E7) |

---

## 8. Ordre et jalons

| Jalon | Contenu | Preuve |
|---|---|---|
| J1 | Vague 0–1 : socles, modèle migré, moteur porté | `make verifier` ; essais moteur et migrations verts ; parité unitaire du moteur sur les jeux figés |
| J2 | Vague 2 : sécurité, stock, coque, reprise | connexion par rôle dans la coque ; reprise de `gestion_mp` dans `gestion_mp_pro_essai` contrôlée |
| J3 | Vague 3 : domaines serveur | matrice complète, balayage des prix, 292 preuves portées |
| J4 | Vague 3–4 : écrans | `routes_ecran` sans manque ; vitest ≥ 60 essais |
| J5 | Vague 4 : parité, comparaison, exploitation | `resultat-parite.txt` et `resultat-comparaison-*.md` : 0 à corriger ; Docker et Mac en service côte à côte avec Gestion MP |
| J6 | Vague 5–6 : recette | `docs/RECETTE.md` : A1–A14 tenus ; `docs/COMPARAISON-GESTION-MP.md` livré |

Nombre de lots : **37** — fondations serveur 5 (S0–S4), domaines serveur 10 (D1–D10),
fondations écran 3 (E0–E2), domaines écran 8 (F1–F8), reprise et comparaison 3 (R1, R2, C1),
exploitation 3 (X1–X3), vérification 5 (V1–V5). Neuf équipes suffisent en vague 3 (D1 puis
D2–D10 ; F1–F8 démarrent dès que les schémas de leur domaine sont fusionnés).
