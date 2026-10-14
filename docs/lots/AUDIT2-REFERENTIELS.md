# Audit n° 2 — RÉFÉRENTIELS / PRODUCTION-BESOINS / PILOTAGE / COMPTES / SOCLE (14/10/2026), avec modifications

Branche `audit2-referentiels` (depuis `main` 9b20443). Le passage n° 1 (`AUDIT-REFERENTIELS.md`)
n'avait trouvé ni CERTAIN ni PROBABLE : ce passage cherche du neuf (robustesse des formulaires,
messages, écrans à la taille du Mac, nombres, recherche), corrige ce qu'il prouve, et applique
la décision RÉFÉRENTIELS du coordinateur : **ne pas toucher aux Franges** (Mohamed créera la
matière), mais le contrôle C01 doit dire clairement « créer la matière Franges ».

Bases d'essai : `gestion_mp_pro_ref2_essai` (suite pytest) et `gestion_mp_pro_ref2copie_essai`
(copie `pg_dump | pg_restore` de `gestion_mp_pro`, référentiels seuls, révision 0008), serveur
d'essai sur le port 8150 pendant l'audit, arrêté ensuite ; les deux bases sont supprimées.
Aucune écriture dans `gestion_mp_pro`, `gestion_mp`, ni sur 8050/8030. Pas de révision Alembic
(0012 non consommée).

## Modifications

| # | Quoi | Pourquoi (preuve avant) | Preuve après | Risque |
|---|---|---|---|---|
| 1 | **C01 dit « créer la matière Franges »** (décision). `calcul/nomenclature.EcartRole.sans_matiere` (vrai quand nulle matière du catalogue ne porte le rôle) et `texte_ecart` ; la ligne de C01 devient « Franges (0 % : aucune matière Franges au catalogue — créer la matière Franges, puis la mettre dans la recette) » ; le « quoi faire » de C01 ajoute la phrase ; l'API rend `sans_matiere` sur chaque écart (`/qualites`, `/nomenclature`). | Sur la copie des vraies données, C01 nommait 6 qualités (8M, 8S, LP, MN, MP, SH) avec « Franges (0 %) » : un diagnostic obscur, alors que la cause est l'absence de toute matière Franges. | `GET /controles/C01` sur la copie : 6 lignes avec le texte ci-dessus ; `moteur/test_nomenclature` (Franges sans matière → `sans_matiere`, Cuir à 0 % avec une matière → texte inchangé). Fenêtre du contrôle lue à 1 440 × 900 : tout tient. | faible : forme seulement, même compte (voir parité, n° 7) |
| 2 | **Les refus et avertissements de recette disent aussi de créer la matière** : `services/recettes.roles_sans_matiere` + `message_oublies(…, sans_matiere)` ; `qualites.avertir_oublis`, `avertissement_arretee`, `ordres/prevu.oublis` passent la liste. « La recette oublie le rôle Franges (0,8 au m²) : aucune matière Franges n'existe au catalogue — créer d'abord la matière Franges (Matières, classification, fournisseurs : son rôle, sa densité en kg/ml, son fournisseur), puis la mettre dans la recette ; ou ramener son poids au m² à 0 dans la fiche. » Le début du message est inchangé (les essais hérités tiennent). | Le refus disait « y mettre ses matières » alors qu'aucune n'existe à y mettre. | `test_recettes::test_un_role_sans_matiere_au_catalogue_dit_de_creer_la_matiere` : rôle neuf sans matière → « créer d'abord la matière » ; une matière créée → l'ancien message ; avertissement et `sans_matiere` sur l'écart. | faible |
| 3 | **Écran** : badge de la liste des qualités « créer la matière Franges » (au lieu de « Franges 0,0 % · Franges sans matière ») ; onglet Recette : « Franges — aucune matière Franges n'existe au catalogue : créer la matière Franges (…), puis la mettre ici » ; aide (`aide.json`) complétée. | Le badge disait deux fois la même chose sans dire quoi faire ; et à 1 440 px (Mac), le tableau des qualités débordait de son cadre (1 180 px dans 1 142 : défilement horizontal invisible, dernière colonne coupée). | Mesuré sur la copie à 1 440 × 900 : tableau 1 142 / 1 142, badge entier ; `Qualites.test.tsx` (badge) ; `make verifier-ecran` vert. | faible |
| 4 | **Code de qualité unique sans tenir compte de la casse** (`services/qualites._code_libre`, 409 `doublon` qui nomme la qualité existante). | CERTAIN : `POST /qualites {"code": "qx-bvd-1"}` à côté de « Qx-BVD-1 » → 201 (deux qualités sur les ordres de fabrication) ; les matières, rôles, valeurs, magasins, unités refusaient déjà la casse (A-12). | `test_qualites::test_le_code_d_une_qualite_est_unique_sans_tenir_compte_de_la_casse` (création, modification, sa propre casse se corrige). | faible (les 18 codes réels sont distincts sans casse) |
| 5 | **Unité d'achat « Kg » / « KG » = le kilo** (`services/matieres._achat`). | CERTAIN : `unite_achat: "Kg"` (tableur, API) → 201 avec un conditionnement **déclaré** « Kg » de contenance 1, à côté de « kg » (palette/bobine déduites perdues). « ml » était déjà lu sans casse. | `test_matieres::test_l_unite_d_achat_kg_s_ecrit_en_minuscules`. | nul |
| 6 | **Référence coupée lisible au survol** : `stock/cellules.Double` pose `title` sur le texte principal (listes Besoins matière, Stock, Production). | À 1 440 px, 10 références de Besoins matière sont coupées par « … » (colonne de 260 px : « PES -1200 Deniers-Anty Bordeau 6104… ») sans aucun moyen de lire la fin. | Mesuré ; `make verifier-ecran` vert. | nul |
| 7 | **Parité / outils** : la forme nouvelle de C01 (n° 1) est une différence voulue, **neutralisée avec sa raison** : `tests/moteur/jeux_outils.CONSEIL_C01` / `sans_conseil_recette` (jeux figés, comparateur des bases), `essais/parite_api_formes.conseil_recette` (parité par l'API : `/controles` lignes et « quoi faire », `/nomenclature` écarts) ; `docs/COMPARAISON-GESTION-MP.md` § 2.3. | `test_parite_unitaire` et `test_donnees_moteur_jeu` échouaient (« sans_matiere : présent d'un seul côté », texte de C01). | Les 20 jeux figés et le jeu réel repassent ; même compte d'anomalies. | nul |

Sonde de robustesse (non livrée, ~60 cas : codes blancs, casse, doublons, bornes, rôles, dates
hors bornes, tableur vide ou texte, recherche « % », « _ », ponctuation, 404, versions) : aucun
500, messages en français ; seuls n° 4 et n° 5 étaient des défauts.

## Vérifié sans changement

- Matrice des droits : `python -m gestion_mp_pro.securite matrice` = `tests/matrice_droits.csv`
  (0 écart, 257 routes). L'alimentation : fiche matière sans prix, export matières 403,
  contrôles 403, besoins sans conseil d'achat, nomenclature sans coût (sonde).
- Robustesse des formulaires matière (référence blanche, densité négative, prix au mètre sans
  densité, devise inconnue ou minuscule → capitales, unité d'achat « ML »), classification
  (liste inconnue, code blanc ou trop long, unité « Den », « DTEX » refusés), rôles (blanc,
  « cuir », « FRANGES » refusés), comptes (nom blanc, identifiant avec espace ou casse, rôle
  inconnu, code atelier à lettres, courriel illisible, version 0), appareils, recherche, dates.
- Plan de production : base et coefficients bornés (0–20, NaN refusé) ; export production :
  onglet inconnu → 422.
- Impression : gabarits inchangés depuis le passage 1 (`@page { margin: 0 }`, papier à en-tête).
- Nombres : `lib/format.ts` `kg()` à 2 décimales utiles ; rien de nouveau.
- Écrans à 1 440 × 900 sur les vraies données : Cockpit, Catalogue (3 onglets), Qualités (liste,
  fiche, nomenclature), Analyse › Contrôles (détail C01), Réglages, Administration : aucun
  débordement hors « masque-accessible » (lecteur d'écran) — sauf n° 3 (corrigé) et la limite
  ci-dessous.

## Ce qui reste (non corrigé, à trancher ou hors de ce passage)

1. **Franges** : à créer par Mohamed (matière, rôle Franges, densité kg/ml, fournisseur), puis à
   mettre dans les recettes de 8M, 8S, LP, MN, MP, SH ; C01 reste bloquant jusque-là — c'est
   voulu, et il dit maintenant quoi faire.
2. **Production › Plan de production et Besoins matière** : à 1 440 px les douze mois dépassent
   le cadre (1 552 et 2 269 px pour 1 142) ; le tableau défile dans son cadre (règle E4) mais la
   barre horizontale est invisible sur Mac tant qu'on ne fait pas glisser : les mois d'été
   sont hors de vue sans que rien ne le dise. Non changé (choix de présentation à trancher :
   mois en abrégé plus serrés, ou colonnes figées).
3. **Unité de titrage avec une lettre accentuée** (« Nè ») acceptée par `str.isalpha` ; sans
   effet connu (elle se lit dans une référence), laissé tel quel.
4. **Titrage créé par l'API** (pas par l'écran) avec un code « 150 Dtx » : l'unité « Dtx » est
   déduite du code sans être dans le référentiel des unités — l'écran, lui, propose la liste.
   QUESTION MÉTIER mineure : faut-il refuser une unité déduite inconnue ?
5. Les questions du passage 1 restent ouvertes : « Cm » dans les titrages, prix bande/cuir au
   kilo ou au mètre.
6. Le volet du navigateur d'essai était partagé avec un autre audit pendant le passage : les
   écrans ont été lus à la taille du Mac, pas rejoués geste par geste au-delà de la fiche qualité.

## Vérifications finales

- `make verifier` : **vert** — serveur (ruff, format, mypy strict, pytest 2 956 réussis / 5
  sautés, alembic check), écran (prettier, eslint, stylelint, tsc, vitest 856 réussis / 1 sauté),
  outils (routes de l'écran = OpenAPI, preuves héritées reprises).
- Matrice des droits régénérée = `tests/matrice_droits.csv` : 0 écart (257 routes).
- `essais/verification_chiffres.py --dates 13` sur la copie des vraies données (serveur propre
  sur un port > 8100) : **16 482 vérifications, 20 familles, 0 écart** — dont « Recettes à
  100 % par rôle (C01) » ×19, nomenclature ×957, contrôles C01–C38 recomptés en SQL ×41.
- Parité des jeux figés (20 jeux) et du jeu réel : repassent avec la neutralisation déclarée.
