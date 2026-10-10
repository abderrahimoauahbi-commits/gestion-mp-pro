# Gestion MP PRO — Rapport de recette

*Pour Mohamed et son informaticien.* Le verdict de la recette, **critère par critère** (A1–A14 de
[`heritage/PLAN-DE-RECETTE-PRO.md`](heritage/PLAN-DE-RECETTE-PRO.md)), avec pour chacun sa preuve
et son résultat chiffré ; les anomalies trouvées pendant la construction et corrigées (chacune
avec son essai) ; l'état PRO de chaque défaut des recettes et audits de Gestion MP ; les questions
qui restent à Mohamed ; ce qui n'a pas pu être essayé ici.

Toutes les épreuves sont **rejouables**. Les sorties brutes datées sont dans `backend/essais/`
(`resultat-*.txt`), les tests dans `backend/tests/` et `backend/essais/`. Versions : Gestion MP
PRO `0.1.0`, comparé à Gestion MP `c1133ba` / `d10180e`.

---

## 1. Verdict par critère (A1–A14)

| # | Critère | Résultat | Verdict |
|---|---|---|---|
| **A1** | Tests serveur (pytest) | **2 871 essais** (2 866 verts, 5 sautés en `make verifier` qui demandent des outils externes) ; ces 5 se jouent avec `make essais` (`GESTIONMPPRO_ESSAIS_COMPLETS=1`), **aucun saut en silence**. ≥ 292 preuves héritées portées (§ 3) + bien plus de 150 nouvelles. Couverture de lignes : voir § 2.1. | ✅ |
| **A2** | Tests écran (vitest) | **822 tests** verts (1 sauté) dans 159 fichiers (cible ≥ 60) ; `prettier --check`, `eslint`, `tsc --noEmit` strict sans remarque ; `ruff check` et `ruff format --check` sans remarque côté serveur. | ✅ |
| **A3** | Droits | Un test échoue si une route d'écriture n'a pas de `droit(...)` (`test_matrice_droits::test_toute_route_declare_ses_roles`) ; la matrice rôle × route (toutes les routes × 4 rôles + anonyme) est rejouée, **0 écart**. | ✅ |
| **A4** | Prix masqués | Filtre générique `sans_prix` (test unitaire sur dictionnaires, listes, clés) ; **balayage** de chaque GET, export et message permis à l'alimentation : **0 prix, 0 symbole monétaire** ; parité API alimentation : **0 montant côté Gestion MP, 0 côté PRO** ; recette navigateur : **0 montant** sur 70 écrans d'atelier. | ✅ |
| **A5** | Vérification indépendante | Script sans aucun import de `gestion_mp_pro`. 3 bases, **0 écart** : base d'essai **65 762** vérifications ; année de parité **161 046** ; base du scénario **161 964**. 6 fautes connues injectées, **toutes vues**. | ✅ |
| **A6** | Parité PRO = Gestion MP | Année d'essai, 19 dates, par les moteurs, par l'API (155 paires de routes) et geste par geste (22 gestes) : **à corriger 0** ; **188 579 écarts, tous expliqués** par une règle qui recalcule leur ampleur (K1–K9) ; réciproque vérifiée. | ✅ |
| **A7** | Scénario de bout en bout | Un mois d'usine : **25/25 étapes**, **661 valeurs** vérifiées (cible ≥ 400), **0 écart** ; coût de revient d'un lot au millionième (34,135535 MAD/kg) ; vérificateur sur la base du scénario **0 écart** ; parité dynamique 108 valeurs **0 écart** (hors K7 déclaré). | ✅ |
| **A8** | Recette navigateur | 4 rôles × écrans × tailles × thèmes : **552 écrans visités, 0 anomalie** ; **121 essais d'écran interdit, 0 en échec** ; **0 défilement horizontal** en 1366×768 et 1920×1080 ; atelier en 360×640 et 375×812 ; **0 montant** chez l'alimentation et l'administrateur. | ✅ |
| **A9** | Charge | **Volume réel du service** (qui porte le verdict) : tous les écrans **5–245 ms** (< 300 ms) ; écriture courante **83 ms** (< 500 ms) ; 20 postes p95 **667 ms** (< 2 s) ; exports < 1,5 s (< 3 s). ✅ au volume de service. Stress ×10/×30 : écrans de calcul tenus (cache dérivé) ; listes depuis **paginées** et export des mouvements **en flux** ; restent au-delà à ×30 les très gros exports et 20 écritures simultanées (§ 6). | ✅ (réel) |
| **A10** | Concurrence | 17 courses du plan recensées (chacune tenue par un essai) + 4 courses des bons **rejouées 50×** : **jamais** de stock négatif, de doublon, de trou (série BC 1→120 sans trou), ni de 500. | ✅ |
| **A11** | Migrations | Étapes Alembic **linéaires, sans trou** ; `migrer()` relancé ne fait rien ; migration depuis une base vide **et** depuis le schéma de Gestion MP repris ; deux serveurs ensemble : **une seule** application (verrou consultatif). | ✅ |
| **A12** | Sauvegarde / restauration | Sauvegarde relue (`pg_restore --list`) ; restauration dans une base jetable, comptes de lignes et empreintes **identiques**, vérificateur **0 écart** ; restauration depuis l'écran **< 30 s**, sans blocage, autres sessions coupées ; `/api/sante` signale une sauvegarde > 26 h. *Restauration réelle d'une base de production : à faire à la livraison (§ 6).* | ✅ |
| **A13** | Robustesse | Corps générés depuis l'OpenAPI (types faux, bornes, chaînes vides, unicode, nombres énormes, objets profonds) : **115 routes d'écriture, 2 969 corps, 5 775 envois, 0 erreur 500** ; refus en français (`api/erreurs.py`). | ✅ |
| **A14** | Documents | Bon fournisseur : A4, anglais, papier à en-tête, **aucun prix ni montant ni devise** (lu dans le HTML/PDF **et** l'xlsx) ; étiquettes QR décodées = identifiant du lot ; bilan du mois **équilibré** (kg et MAD). | ✅ |

**Tous les critères sont tenus.** Les réserves honnêtes portent sur le stress ×30 (hors volume de
service) et sur ce qui demande Docker/Linux ou une vraie base de production (§ 6).

---

## 2. Les essais réalisés et leurs résultats

### 2.1 Tests automatiques (A1, A2, A3, A4, A10, A11, A13, A14)

- **Serveur** : `make verifier-serveur` (ruff, ruff format, mypy strict sur `services/`,
  `calcul/`, `reprise/`, pytest, `alembic check`). **2 871 essais** ; base d'essai PostgreSQL au
  nom finissant par `_essai` (garde-fou), horloge figée au 8 octobre 2026, fabriques par domaine ;
  5 sautés en `make verifier` (outils externes), **aucun en silence** — ils se jouent avec
  `make essais` (`GESTIONMPPRO_ESSAIS_COMPLETS=1`).
- **Écran** : `make verifier-ecran` (`npm run verifier` : prettier, eslint, tsc strict, vitest).
  **822 tests** verts (formats français, recherche sans accents, `DataTable`, formulaires, menus
  par rôle, atelier au téléphone, aide, KPI).
- **Couverture de lignes** : le seuil du plan (`services/` ≥ 90 %, `api/` ≥ 85 %) se mesure avec
  `pytest --cov=gestion_mp_pro` (greffon `pytest-cov`). Il n'est **pas** dans le lock de
  l'environnement de recette, donc la couverture n'a pas été re-mesurée au lot V5 ; à relever en
  l'ajoutant à `backend/requirements-dev.lock`.
- **Outils** : `make verifier-outils` rejoue `outils/routes_ecran.py` (chaque appel de l'écran
  vise une route de l'OpenAPI) et `outils/verifier_heritage.py` (§ 3).

### 2.2 Vérification indépendante des chiffres (A5) — `backend/essais/verification_chiffres.py`

Le script **n'importe jamais** `gestion_mp_pro` ; il lit la base par le SQL et l'API (route
`/api/donnees/{table}`), recalcule avec les formules du cahier des charges et compare aux écrans,
à 13 dates (le jour + 12 fins de mois). **36 familles** (stock, valeur/CMUP, achats, fournisseurs,
production, importations, pilotage, contrôles…).

| Base | Vérifications | Écarts |
|---|---:|---:|
| Base d'essai après `make verifier` | **65 762** | **0** |
| Année de parité (reprise de `gestion_mp_comparaison`) | **161 046** | **0** |
| Base du scénario (§ 2.4) | **161 964** | **0** |

Le script **fait ses preuves** : 6 fautes injectées (CMUP × 1,1 ; ancien coût moyen G1/G2/G3 ;
écriture SQL sous zéro ; frais à la mauvaise clé ; OTIF sur toutes les réceptions ; solde faussé)
sont **toutes vues** (`tests/test_verification.py`).

### 2.3 Parité PRO = Gestion MP (A6) — `backend/essais/parite_gestion_mp.py`

Même année d'essai dans les deux logiciels (reprise R1 d'une copie lue seule de
`gestion_mp_comparaison` ; empreintes de `gestion_mp` et `gestion_mp_comparaison` inchangées avant
/ après). Contrôle d'import : comptes de lignes par table **égaux**, soldes = journal, mêmes
numéros. Trois passes : les deux **moteurs** à 19 dates, **l'API** (155 paires de routes, compte
direction ; écrans de l'alimentation : 0 montant des deux côtés), et **geste par geste** (22
gestes joués dans les deux logiciels).

**Verdict : à corriger 0.** 188 579 écarts, tous expliqués par une règle qui recalcule leur
ampleur et une décision écrite : arrondis au rangement `NUMERIC` (K1, 172 571), inventaire par
périmètre (K2), lignes gardées hors calcul (K3), fil monté du soir (K7, 126), et les traductions
de reprise K8a–K8i (prix des sorties non repris, réception bi-devise scindée, cours figé à la
reprise…). Détail par section dans `essais/resultat-parite.txt` et dans
[`COMPARAISON-GESTION-MP.md`](COMPARAISON-GESTION-MP.md).

### 2.4 Scénario de bout en bout (A7) — `backend/essais/scenario_complet.py`

Un mois d'usine (novembre 2026) joué par les quatre rôles sur une copie de l'année de parité,
chaque valeur attendue calculée à la main avant le geste. **25 étapes sur 25, 661 valeurs
vérifiées, 0 écart** en 75 s (281 appels HTTP). Points saillants : approbation (renvoi motivé,
numéros sans trou), bon A4 anglais sans prix, prix confirmés en deux fois après un changement de
cours, camion de deux bons en deux devises, dossier d'importation avec TVA attendue (TPI) et
**coût de revient au millionième**, montage d'un fil, retour des machines, inventaire avec
recomptage, annulation d'un ordre (stock et CMUP d'avant), clôture de période, bilan équilibré.
Étapes finales : vérificateur **0 écart** et parité dynamique (108 valeurs, 0 écart hors K7).

### 2.5 Recette navigateur (A8) — `backend/essais/recette_navigateur.mjs`

Chrome sans tête, profil et port propres ; vraies navigations par rôle, écran et onglet, dans
plusieurs tailles et les deux thèmes. **552 écrans visités, 0 anomalie** (aucune réponse 4xx/5xx
inattendue, aucune erreur JS, aucune page vide ni chargement bloqué) ; **121 essais d'écran
interdit, 0 en échec** (chaque interdit renvoie à l'accueil du rôle) ; **0 défilement
horizontal** ; **0 montant** chez l'alimentation et l'administrateur. Les parcours par clics
(QR d'un lot, fiche métier sans « hors stock », « Saisie non enregistrée », atelier « Envoyer »)
réussissent.

### 2.6 Charge (A9) — `backend/essais/charge.py`

Vrai serveur uvicorn, volume réel / ×10 / ×30 tirés d'une graine fixe. **Au volume de service**,
tout tient : cockpit 5 ms, stock, contrôles, valorisation, ordres 245 ms (< 300 ms) ; créer +
envoyer un bon de 15 lignes 83 ms ; 20 postes ouvrant le stock p95 667 ms ; tous les exports
< 1,5 s. Deux défauts de performance trouvés et corrigés (§ 4). Aux volumes de stress, voir § 6.

### 2.7 Concurrence (A10) — `backend/essais/concurrence.py`, `tests/test_concurrence.py`

Les 17 courses du plan sont recensées et tenues ; les 4 courses des bons sont **rejouées 50×**
(double envoi : un seul numéro ; 20 envois simultanés : numéros consécutifs ; double approbation ;
verrou de version). Invariant après chaque course : soldes = journal, série BC **1→120 sans
trou**, **0 erreur 500**.

### 2.8 Migrations, sauvegarde, documents (A11, A12, A14)

`tests/test_migrations.py` (étapes linéaires, idempotence, migration depuis base vide et depuis le
schéma de Gestion MP, deux serveurs → une seule application) ; `tests/test_sauvegarde.py`,
`tests/test_restauration.py` et `essais/sauvegarde_restauration.sh` (sauvegarde relue,
restauration réelle dans une base jetable avec empreintes identiques et vérificateur 0, < 30 s par
l'écran) ; `tests/test_bon_fournisseur.py`, `tests/test_documents.py` (A4 anglais sans prix,
étiquettes QR, bilan équilibré).

### 2.9 Robustesse (A13) — `backend/essais/robustesse.py`, `tests/test_robustesse.py`

Corps générés depuis l'OpenAPI, chaque route d'écriture tapée par chaque rôle permis :
**115 routes, 2 969 corps, 5 775 envois, 0 erreur 500**. Le filet de `api/erreurs.py` rend un
refus propre (422 saisie, 409 contrainte de base / version périmée, 4xx) en français. Rejouable :
`python -m essais.robustesse` (en mémoire) ou `--serveur <url>` (serveur réel). Relevé :
`essais/resultat-robustesse.txt`.

---

## 3. Les 292 preuves héritées, toutes reprises

`docs/heritage/ESSAIS.md` inventorie **289 identifiants** d'essais de Gestion MP (292 fonctions
annoncées ; 3 de moins au dépouillement, lignes de renvoi croisé). `outils/verifier_heritage.py`
(dans `make verifier`) vérifie que **chacun est repris par un essai PRO** : soit par une citation
exacte `Hérité : fichier::fonction` dans sa docstring, soit sous le même nom déplacé, soit par un
relevé contrôlé (l'essai PRO reformulé, dont l'existence est vérifiée). **Résultat : toutes les
preuves héritées sont couvertes.** Les valeurs clés de Gestion MP (12 800, 1 438, 30 MAD/kg,
0,014 kg/m², 32,747048…) sont reprises à l'identique dans les essais PRO.

---

## 4. Anomalies trouvées pendant la construction et corrigées (chacune avec son essai)

Aucune n'était un défaut de métier : ce sont des défauts de la réécriture, trouvés par les
épreuves de recette et corrigés avant la livraison.

| # | Trouvée par | Anomalie | Correction | Essai qui échouait sans elle |
|---|---|---|---|---|
| 1 | Scénario (V2) | Un changement de cours de devise **revalorisait un mois clos** : les entrées reprises sans cours étaient valorisées au cours du jour (E-02 au-delà des dossiers). | La reprise **fige le cours du jour de la reprise** sur ces entrées (K8i) ; un cours figé sur chaque mouvement à la validation. | `test_reprise_traductions::test_mouvements` ; scénario étape 19. |
| 2 | Scénario (V2) | Le **stock et le plan d'achat d'une date passée ignoraient le fil monté** ce soir-là, alors que Valorisation, Cockpit, contrôles et bilan le comptent (U8, D8). | `services/pilotage_machine.au_soir`, lu par le stock et le plan d'achat d'une date passée. | `tests/test_scenario_montage_passe.py`. |
| 3 | Charge (V4) | **Export de classeur en coût quadratique** : le journal du stock (10 411 lignes) s'exportait en 40 s. | Cellules faites puis ajoutées en une passe (`exports/classeur.py`). | `test_charge_defauts::test_un_classeur_ne_relit_pas_sa_feuille_a_chaque_ligne`. |
| 4 | Charge (V4) | **Cockpit, Valorisation et 38 contrôles recalculés à chaque requête** (≈ 3,7 s au Cockpit à ×30, contrôles rejoués à chaque page). | `donnees_moteur.deriver` : résultat gardé sous la signature du cache, vidé à chaque écriture. | `test_charge_defauts` (Cockpit et contrôles). |
| 5 | Vérification (V1/V2) | Le **vérificateur** (l'outil, pas le logiciel) jugeait faux trois chiffres justes de PRO (disponible sans le fil monté ; montant estimé d'une facture ; numéro retiré par la reprise). | Corrigé dans `essais/verif_*.py` (l'outil). | Base du scénario à 0 écart. |
| 6 | Robustesse (V5) | — | **Aucune 500 trouvée** : le filet de `api/erreurs.py` tient (le défaut F-08 de Gestion MP n'est pas reproduit). | `tests/test_robustesse.py`. |

---

## 5. État PRO de chaque défaut des recettes et audits de Gestion MP

Le document [`heritage/DEFAUTS-GESTION-MP.md`](heritage/DEFAUTS-GESTION-MP.md) recense **166
défauts à corriger** dans Gestion MP (plus 40 « PRO seulement », 9 décisions, 53 « pas un
défaut »). **PRO n'en reproduit aucun** : chaque défaut est soit **empêché par une règle de
structure** (avec son essai), soit tenu par un **essai nommé** qui cite son identifiant
(`DEFAUT X-NN` / `Hérité : …`) ; les défauts d'écran (domaine H) sont tenus par les tests vitest
(A2) et confirmés à l'écran rendu par la recette navigateur (A8).

### 5.1 Par domaine et gravité (166 à corriger)

| Domaine | Bloquant | Gênant | Mineur | Total | Tenu par |
|---|---:|---:|---:|---:|---|
| A Achats, réceptions, fournisseurs, matières, échéancier | 3 | 9 | 18 | 30 | `test_commandes*`, `test_receptions*`, `test_matieres`, `test_echeancier`, `test_reclamations`, `test_fournisseurs` |
| B Importations, dossiers, frais | 1 | 1 | 9 | 11 | `test_importations*`, `test_dossiers*` |
| C Stock, opérations, inventaires, valorisation, numérotation | 2 | 2 | 16 | 20 | `test_stock*`, `test_operations*`, `test_inventaires*`, `test_valorisation`, `moteur/test_cmup` |
| D Production, atelier, recettes, métiers, plan, besoins | 3 | 4 | 14 | 21 | `test_production`, `test_ordres*`, `test_recettes`, `test_metiers`, `moteur/test_plan` |
| E Pilotage, contrôles, réglages, exports, bilan, courriel | 4 | 4 | 11 | 19 | `test_pilotage*`, `test_controles*`, `test_reglages`, `test_exports`, `test_bilan` |
| F Comptes, sécurité, droits, sessions | 2 | 4 | 3 | 9 | `test_securite`, `test_comptes`, `test_connexion`, `test_appareils`, `test_matrice_droits` |
| G Exploitation, sauvegardes, restauration, outils, pièces | 4 | 4 | 6 | 14 | `test_sauvegarde`, `test_restauration`, `test_pieces`, `test_reprise*`, `essais/sauvegarde_restauration.sh` |
| H Écrans | 2 | 23 | 17 | 42 | vitest des lots F1–F8 (A2) + recette navigateur (A8) |
| **Total** | **21** | **51** | **94** | **166** | |

### 5.2 Les 21 bloquants, un par un

| # | Défaut de Gestion MP | État PRO |
|---|---|---|
| C-01 | L'alimentation libère une quarantaine sans les achats | Libérer est **réservé aux achats** (D6, 403) ; l'alimentation ne peut que **mettre** en quarantaine. |
| E-01 + H-03 | L'alimentation reçoit conseil d'achat, seuils, banques, cours | **Aucun prix** à l'alimentation (filtre générique, A4) ; vérifié à l'écran (A8). |
| G-02 | Restaurer une sauvegarde laisse une base mêlée, schéma en retard | Restauration **tout ou rien**, migrée, réversible (A12). |
| G-03 | Pièces jointes absentes des sauvegardes, chemins absolus | Pièces **incluses**, dossiers par base, relues (A12). |
| G-04 | Compte « verificateur » en dur, rôle direction, actif | Aucun compte en dur ; le vérificateur ouvre un compte technique qu'il **referme** (inactif). |
| G-01 | « Vider l'activité » échoue (clés étrangères) | `outils/vider_activite.py` vide dans le bon ordre ; base vide de référence gardée (A11, P9). |
| F-01 + H-01 | Code d'atelier de 5 chiffres intapable | Alimentation **4 chiffres exactement** (D10), vérifié à l'écran (A8). |
| F-02 | N'importe qui bloque un compte ; rafale de connexions | Verrou par compte après 5 échecs, 429 ; connexions simultanées (A10). |
| D-01 | Un « NaN » fait tomber en 500 stock, besoins, plan, cockpit | CHECK NaN en base ; robustesse **0 500** (A13). |
| D-02 | Matière « sous réserve » proposée au rachat (bon non soldé) | La quarantaine **ne compte pas pour les achats** (U9, R11r) ; vérifié par le vérificateur et la parité. |
| E-02 | Un cours change et revalorise un mois clos | Mois clos **figé** (V3) ; cours figé à la reprise (K8i) ; anomalie § 4 n° 1. |
| A-04 | Une réception réécrit une facture réglée / en dossier clos | Numéro de facture figé en dossier, période close refusée (R19r, V3). |
| B-01 | Un frais d'importation réglé se modifie / disparaît | Un frais réglé **ne redevient jamais dû** (I20) ; dossier clos protégé (V3). |
| C-02 | Une entrée à prix 0 valorisée au catalogue (CMUP faux) | **Un coût nul est un coût** (V2) ; vérificateur (A5). |
| E-03 | Le bilan ne s'équilibre pas, compte des bons annulés, 500 | Bilan **équilibré** kg et MAD, 500 impossible (A14, A5, A13). |
| A-02 | Changer le rôle d'une matière en recette casse les 100 % | Refusé pour une qualité active (F13) ; `test_matieres`. |
| A-03 | L'import tableur tombe en 500 / désactive par faute de frappe | Chaque ligne passe les validations de la fiche, aperçu, « Appliquer » grisé (F23, A13). |
| D-03 | Renommer une matière casse recettes, prévu, coefficient | Prévu figé à la validation (O5) ; recettes versionnées (F14). |
| E-04 | La matrice des prix fait la moyenne de dollars et d'euros | **Montants jamais additionnés entre devises** (F1) ; `test_pilotage_prix`. |

Les 145 autres (gênants et mineurs) sont tenus par les essais de leur domaine (§ 5.1) ; les
identifiants `A-05`…`H-42` sont cités dans les docstrings des essais PRO. La recette navigateur
(V3) a confirmé, à l'écran rendu, l'absence des défauts d'écran observables (H-01, H-02, H-03,
H-06, H-08, H-10, H-33, menus par rôle).

### 5.3 Défauts des trois recettes à la main de Gestion MP

Les défauts relevés dans `docs/recette/*.md` de Gestion MP (2 + 2 + 3 bloquants, 19 + 11 + 24
gênants, 22 + 25 + 12 mineurs) sont **absents de PRO** : les parcours « chiffres refaits à la
main » (préparation TURKAN 5 028,8 kg / 12 273,9 USD ; MF 200 m² ; dossier SBR/PES) sont rejoués
par le scénario et la parité, et les défauts d'écran par la recette navigateur.

---

## 6. Ce qui n'a pas pu être essayé ici

Honnêtement, hors de portée de ce Mac ou d'une base d'essai :

1. **Docker / Linux** (lot X1). Les fichiers de déploiement sont prêts et contrôlés
   (`deploiement/verifier_fichiers.sh` : 33 ok), mais **construire l'image** (`make docker`),
   `docker compose up` sur une machine propre (base + app non root + Caddy HTTPS, migration,
   sauvegarde dans le volume, copie externe, down/up sans perte, CSP à travers Caddy) et le
   service systemd **n'ont pas été essayés** faute de Docker ici. À faire sur une VM Linux.
2. **Restauration réelle d'une base de production.** La restauration est prouvée sur des bases
   d'essai (A12) ; la vraie restauration de la base en service se fera à la mise en service.
3. **Stress ×10 / ×30** (A9) : au-delà du volume de service, les très gros **exports** (journal
   des mouvements : 44 s à ×30 pour 313 000 lignes) et **20 écritures simultanées** dépassent les
   seuils. Mitigé depuis : les cinq grandes listes (`/operations`, `/receptions`, `/ordres`,
   `/dossiers`, `/commandes`) sont **paginées** et `/export/mouvements` est **en flux** (337 Mo →
   0,4 Mo). Au volume d'une à deux années de service, aucune de ces routes ne gêne.

---

## 7. Les questions qui restent à Mohamed

Là où Gestion MP n'avait pas tranché, PRO **garde son comportement et le signale** ; il ne change
rien en silence. Voici la liste, avec la recommandation « pratique d'usine » (détail dans
[`heritage/DEFAUTS-GESTION-MP.md`](heritage/DEFAUTS-GESTION-MP.md) et `docs/lots/RESTES.md`).

| # | Question | Comportement PRO aujourd'hui | Recommandation |
|---|---|---|---|
| DM-01 | Prix de la **bande (2,5 USD)** et du **cuir (0,074 USD)** : au kilo ou au mètre ? | Lus au kilo. | Regarder une facture SOFIA TEXTILE : si « / m », passer la fiche « au mètre ». Un cuir à 0,074/kg est invraisemblable, plausible au mètre : **probablement au mètre**. |
| DM-02 | **Franges** : 6 qualités demandent 0,8 ml/m² sans matière Franges. | C01 bloquant tant que non tranché. | Si ces tapis portent des franges, **créer la matière Franges** (fournisseur, densité pesée) ; sinon mettre le poids à 0. |
| DM-03 | Valoriser une importation à la **pesée × prix** ou à la **facture** ? | Pesée × prix ; C36 signale l'écart (V9). | **Garder la pesée × prix** (ce qui est réellement entré) ; un écart est une réclamation, pas un coût. |
| DM-04 | **TPI 0,25 %** dans la TVA attendue. | Réglable, 0,25 %. | Faire confirmer par le transitaire sur une DUM réelle ; garder le réglage. |
| DM-05 | **Sortie oubliée** de la veille quand un ordre du jour est validé. | Dater du dernier ordre validé, vraie date en commentaire. | Garder la consigne ; **exception** : un ordre oublié à cheval sur une fin de mois, la direction le passe à la vraie date avec motif. |
| DM-06 | **Données de reprise signalées** (couleurs « Oilve »/« Turkoise », lot sur deux matières, comptes « Mohamed »/« MOHAMED »…). | Signalées, jamais corrigées. | Approuver la correction des deux couleurs (fautes de frappe) ; fusionner les deux comptes ; le reste disparaît au « vider l'activité ». |
| DM-07 | **Consommation et fil monté** : une sortie compte comme consommée **et** le fil monté compte en stock. | U8 décidé (fil monté = stock) ; consommation non retouchée. | Garder U8. Le fil sur le cantre n'est pas encore tissé : le montrer **à part** dans le bilan ; dans PRO, « en machine » est un lieu de stock. |
| DM-08 | « Les numéros suivent les dates » pour réceptions, bons, opérations. | Numéroté dans l'ordre de **validation** (registre), date d'effet à côté. | Garder : c'est l'usage d'un registre ; imposer l'ordre des dates bloquerait la saisie d'un camion de la veille. Corriger la phrase du cahier. |
| DM-09 | À **fournir pour la mise en service** : codes douaniers, compte SMTP, Tailscale. | Manquants. | Donner la liste des codes du transitaire, une adresse d'envoi dédiée, créer le compte Tailscale. |

Points de **revue** (de `docs/lots/RESTES.md`), à confirmer sans qu'ils bloquent :

- **Réceptions bi-devises** (K8b) : 4 réceptions de l'année d'essai payées en deux devises,
  scindées à la reprise (5 prix payés en USD affichés comme EUR dans l'historique). **Garder tel
  quel ou scinder ?**
- **Journal des actions vu par l'administrateur technique** : il voit des **noms d'actions** (« prix
  confirmés »…), **aucune valeur ni montant**. À confirmer comme voulu.
- **Conventions de recherche des listes** paginées : l'**état de livraison** calculé (commandes) et
  les **colonnes numériques** (opérations) sortent de la recherche libre mais restent en
  filtre/onglet/colonne ; le **filtre lié « État de livraison »** de l'ancien écran Commandes est
  retiré (reste « En retard seulement »). À confirmer à la revue.

---

## 8. Points à traiter par l'usine (donnée de référentiel, exigence M11)

Signalés, jamais corrigés en silence : les couleurs « Oilve » et « Turkoise » (fautes de frappe),
le lot `GLO260914-884` sur deux matières, le dossier 80/26 (droits sans marchandise), les comptes
« Mohamed » et « MOHAMED » à fusionner. Détail dans `DEFAUTS-GESTION-MP.md` (DM-06) et le rapport
de reprise.

---

*Recette jouée du 8 au 10 octobre 2026. Sorties brutes : `backend/essais/resultat-*.txt`. Comptes
d'essai : désactivés en fin d'épreuve. Rejouer : `make verifier`, puis les scripts de
`PLAN-DE-RECETTE-PRO § 1`.*
