# Gestion MP PRO — plan de vérification et de recette

Ce plan répond à la consigne de Mohamed : *« fais des tests à la fin pour vérifier les résultats, la
structure, la justesse des calculs »*. Il suit le standard de GMAO PRO (`~/gmao-pro/docs/RECETTE.md`,
`backend/tests/`, `backend/essais/`, `essais/`). Il reprend **chaque** preuve de Gestion MP
(`ESSAIS.md`, `VERIFICATION.md`) et comble ses trous.

Il est rédigé avant le code. Les noms de routes et de modules sont ceux que PLAN.md prévoit. Si
l'implémentation les change, ce plan est mis à jour **avant** la recette, pas après.

---

## 0. Critères d'acceptation chiffrés

Ils seront repris en tête de `docs/RECETTE.md`, avec le résultat obtenu en face de chacun. La
livraison n'a lieu que si **tous** sont tenus.

| # | Critère | Seuil d'acceptation |
|---|---|---|
| A1 | Tests serveur (pytest) | 100 % verts, **0 sauté** sur le poste de livraison ; ≥ 292 preuves héritées portées (table § 3) + ≥ 150 nouvelles ; couverture de lignes `services/` ≥ 90 %, `api/` ≥ 85 % |
| A2 | Tests écran (vitest) | 100 % verts ; ≥ 60 tests ; `prettier --check`, `eslint`, `tsc --noEmit` (strict) sans remarque ; `ruff check` et `ruff format --check` sans remarque côté serveur |
| A3 | Droits | Un test échoue si une route d'écriture n'a pas de `droit(...)` ; la matrice rôle × route (toutes les routes de l'OpenAPI × 4 rôles + anonyme) est rejouée, **0 écart** avec la matrice attendue versionnée |
| A4 | Prix | Balayage récursif de toutes les réponses GET et de tous les exports (xlsx, HTML, PDF) lus par l'alimentation : **0 champ de prix ou de montant non nul, 0 symbole monétaire** |
| A5 | Vérification indépendante des chiffres | Sur 3 bases (essai après pytest, année de parité, copie après scénario) : **0 écart**, ≥ 150 vérifications par base, aucun import du paquet `gestion_mp_pro` dans le script |
| A6 | Parité PRO = Gestion MP | Sur l'année d'essai, à **13 dates** (fin de chaque mois + jour J) : **0 écart à corriger** ; écarts expliqués limités aux champs ajoutés par PRO et aux corrections déclarées (§ 7.6), chacun vérifié en forme et en ampleur |
| A7 | Scénario de bout en bout (un mois d'usine) | Toutes les étapes réussies ; chaque valeur attendue calculée à la main d'avance ; contrôle de cohérence : aucune nouvelle anomalie bloquante ; vérificateur 0 écart à la fin |
| A8 | Recette navigateur | 4 rôles × chacune de leurs entrées de menu + fiches + impressions : **0 anomalie** (4xx/5xx inattendu, erreur JS, page vide, chargement bloqué, montant chez l'alimentation) ; écran interdit → renvoyé à l'accueil ; bureau sans défilement horizontal en 1366 × 768 ; atelier utilisable en 360 × 640 |
| A9 | Charge | Volume réel : médiane **< 0,3 s** sur chaque écran courant (exigence M16) ; ×10 : < 1 s ; ×30 : < 2 s, exports < 3 s ; 20 postes simultanés : p95 < 2 s ; validations (réception 20 lignes, ordre 15 lignes, clôture de dossier 50 lignes) < 0,5 s au volume réel |
| A10 | Concurrence | Chaque course du § 10.3 rejouée **50 fois** : jamais de stock négatif, de doublon, de trou de numérotation, ni d'erreur 500 |
| A11 | Migrations | Étapes numérotées sans trou ; `migrer()` relancé ne fait rien ; migration réussie depuis une base vide **et** depuis une copie du schéma de Gestion MP reprise ; deux serveurs démarrés ensemble : une seule application des étapes |
| A12 | Sauvegarde / restauration | Sauvegarde relue (`pg_restore --list`) ; restauration dans une base jetable, comptes de lignes et empreintes des tables métier **identiques**, vérificateur 0 écart ; restauration depuis l'écran < 30 s, sans blocage ; `/api/sante` signale une sauvegarde de plus de 26 h |
| A13 | Robustesse des entrées | Toutes les routes d'écriture reçoivent des corps générés depuis l'OpenAPI (types faux, bornes, chaînes vides, unicode, nombres énormes) : **0 erreur 500** ; refus en français |
| A14 | Documents | Bon fournisseur : A4, anglais, papier à en-tête, aucun prix ni montant ni devise (lu dans le PDF/HTML **et** l'xlsx) ; étiquettes QR décodées = identifiant du lot ; bilan du mois équilibré |

---

## 1. Organisation des fichiers

Elle suit celle de GMAO PRO.

```
gestion-mp-pro/
  backend/
    tests/                      pytest, base jetable gestion_mp_pro_essai
      conftest.py               garde-fou « _essai », horloge fixe, comptes, fabriques de données
      test_securite.py          droits structurels, matrice, sessions, CSRF, installation
      test_prix_masques.py      balayage générique de l'alimentation
      test_referentiels.py  test_matieres_metre.py  test_commandes.py  test_receptions.py
      test_performance_fournisseurs.py  test_echeancier.py  test_importations.py
      test_stock_atelier.py  test_inventaires.py  test_valorisation.py  test_plan_besoins.py
      test_production.py  test_controles.py  test_pilotage.py  test_documents.py
      test_concurrence.py  test_migrations.py  test_sauvegarde.py  test_robustesse.py
      moteur/                   essais du moteur seul (Donnees écrites à la main), un fichier par domaine
    essais/
      verification_chiffres.py  recalcul indépendant (§ 6)
      parite_gestion_mp.py      PRO = Gestion MP (§ 7)
      charge.py                 remplir | mesurer (§ 10)
      concurrence.py            courses répétées (§ 11.3)
  frontend/src/**/*.test.tsx    vitest (§ 5)
  essais/
    scenario_complet.py         un mois d'usine (§ 8)
    recette_navigateur.js       ouverture de chaque écran par rôle (§ 9)
    comptes-essai.md
    resultat-*.txt              sorties brutes datées de chaque épreuve
  docs/RECETTE.md               verdict par critère (§ 0), essais réalisés, anomalies corrigées
```

Commandes de recette, toutes rejouables :

```bash
cd backend && .venv/bin/python -m pytest -q --cov=gestion_mp_pro       # A1, A3, A4, A10-A13
cd frontend && npm run verifier                                       # A2 (prettier, eslint, tsc, vitest)
.venv/bin/python essais/verification_chiffres.py   > ../essais/resultat-verification-chiffres.txt
.venv/bin/python essais/parite_gestion_mp.py 2026-10-08 > ../essais/resultat-parite.txt
.venv/bin/python essais/charge.py remplir x10 && essais/charge.py mesurer > ../essais/resultat-charge.txt
.venv/bin/python ../essais/scenario_complet.py      > ../essais/resultat-scenario.txt
```

## 2. Bases et isolement

| Base | Usage | Garde-fou |
|---|---|---|
| `gestion_mp_pro_essai` | pytest, schéma recréé à chaque séance | `conftest` refuse tout nom qui ne finit pas par `_essai` |
| `gestion_mp_pro_parite` | Année d'essai reprise dans PRO | Nom finissant par `_parite` exigé par la reprise d'essai |
| `gestion_mp_parite_source` | Copie (`pg_dump` → `pg_restore`) de `gestion_mp_comparaison` | Lue seulement ; `gestion_mp` et `gestion_mp_comparaison` ne sont jamais ouvertes en écriture |
| `gestion_mp_pro_charge_x10`, `_x30` | Épreuve de charge | Nom finissant par `_charge_*` |
| `gestion_mp_pro_scenario` | Copie de la parité pour le scénario | — |
| `gestion_mp_pro_restauration_essai` | Restauration réelle | Détruite après |

Règles :

- **Horloge injectable.** `services/horloge.py` fournit `aujourd_hui()` et `maintenant()`, et pytest
  fixe la date au 2026-10-08. Les essais de Gestion MP dépendent de `date.today()` et changent
  d'issue en fin de mois ; c'est fini. Un essai paramétré rejoue les dates sensibles : 1ᵉʳ du mois,
  dernier jour, 29 février, passage d'année.
- **Pas d'état partagé caché.** Chaque module crée ses données par des fabriques
  (`fabrique.fournisseur()`, `fabrique.bon_parti()`, `fabrique.reception_validee()`…). On n'utilise
  plus `pytest.dossier` comme variable globale. Les réglages modifiés sont rendus par une fixture
  `reglage(cle, valeur)`, qui les restaure dans un `finally`.
- Les essais qui demandent un vrai serveur ou les outils PostgreSQL **ne se sautent pas en
  silence** sur le poste de livraison. Ils échouent avec la raison (`GESTIONMPPRO_ESSAIS_COMPLETS=1`).

## 3. Tests serveur à porter (les 292 preuves de Gestion MP)

### Règles de portage

1. **Une preuve héritée = au moins un test PRO** qui porte l'identifiant d'origine dans sa docstring
   (`Hérité : test_achats::test_le_cours_se_fige…`). Un script (`essais/heritage.py`) vérifie que
   les 292 identifiants de `ESSAIS.md` sont tous cités.
2. On garde le niveau d'origine : un essai du moteur reste un essai du moteur (`tests/moteur/`) ; un
   essai par l'API reste par l'API. Quand un calcul n'est prouvé qu'à un niveau, on ajoute l'autre.
3. Les **valeurs attendues** de `ESSAIS.md` sont reprises à l'identique : 12 800, 1 438, 482, 26,89,
   3 380, 63 500, 4 700, 50,8, 30 MAD/kg, 0,014 kg/m², 13 000…
4. On renforce les essais faibles de `ESSAIS.md` § 15 : un seul code attendu, pas d'assertion
   conditionnelle, des valeurs au lieu de « répond 200 ».
5. On fusionne les redondances de `ESSAIS.md` § 16 en essais paramétrés. Chaque cas d'origine reste
   un cas.
6. On tranche la contradiction de `ESSAIS.md` § 17. La route « fournisseur » ne porte aucun prix ;
   un export interne chiffré, s'il est gardé, est nommé tel et réservé aux achats et à la direction.

### Correspondance

| Domaine (ESSAIS.md) | Héritées | Fichier PRO | Points d'attention |
|---|---|---|---|
| 1. Sécurité, prix | 12 | `test_securite.py`, `test_prix_masques.py` | Remplacer les 3 essais « aucun prix » par le balayage générique (§ 11.2), en gardant leurs assertions précises |
| 2. Référentiels | 26 | `test_referentiels.py` | L'empreinte devient le champ `version` (409 sur version périmée) ; ajouter le journal avant/après et l'historique de la fiche |
| 3. Au mètre, kg | 19 | `test_matieres_metre.py`, `moteur/test_metre.py` | La migration 14 de Gestion MP n'existe pas dans PRO. Sa preuve devient : « la reprise d'une base Gestion MP aux unités historiques donne des kg, des montants et une valeur de stock identiques » |
| 4. Commandes | 23 | `test_commandes.py` | Toutes les transitions brouillon / à approuver / envoyée / confirmée / soldée / annulée en une **table de transitions** testée exhaustivement (§ 4) |
| 5. Réceptions | 31 | `test_receptions.py` | Excédent tous lots ensemble et sous verrou |
| 6. Performance fournisseurs | 13 | `moteur/test_otif.py`, `test_performance_fournisseurs.py` | Formule du score figée par des cas chiffrés |
| 7. Échéancier | 5 | `test_echeancier.py` | Remplacer le test de présence de clé par des montants |
| 8. Importations | 39 | `test_importations.py`, `moteur/test_dossiers.py` | Garder les 2 courses (ouverture contre annulation, facture corrigée) |
| 9. Stock, atelier | 36 | `test_stock_atelier.py`, `test_inventaires.py` | Le verrou consultatif des ordres, et ses preuves |
| 10. Valorisation | 27 | `moteur/test_cmup.py`, `test_valorisation.py` | Les 9 cas du CMUP au centime, au niveau du moteur **et** de l'API |
| 11. Plan, besoins, production | 28 | `moteur/test_plan.py`, `test_production.py` | Les dates passées, les versions du plan et des recettes |
| 12. Pilotage | 27 | `test_pilotage.py`, `test_controles.py` | Un test par contrôle (§ 4) |
| 13. Vérification | 6 | `test_verification.py`, `essais/*` | Le vérificateur PRO voit les 3 fautes du 2ᵉ audit et le CMUP × 1,1 |

## 4. Tests serveur à ajouter (ce que Gestion MP ne prouve pas)

| Sujet | Tests à écrire |
|---|---|
| Routes jamais exercées | Installation (une seule fois, 409 ensuite) ; déconnexion ; changement de code (déconnecte les autres appareils) ; création, modification, désactivation des comptes (la session tombe) ; « il reste toujours une direction » ; codes trop courts refusés pour qui valide ou paie ; `PUT dossiers/{id}` ; suppression d'un inventaire ; modification d'une opération en brouillon ; composition d'une référence ; photographie des indicateurs et son historique ; historique des paramètres ; motifs ; plan d'achat d'un fournisseur ; archive des bobines ; accès et QR d'accès ; aperçu du courriel |
| Contrôles | Un test **par contrôle**, C01 à C38. Pour chacun : une donnée qui le fait sonner, avec le nombre d'anomalies exact ; sa correction le rend conforme ; sa gravité ; `quoi_faire` et `vers`. Les 19 contrôles jamais exercés dans Gestion MP sont en priorité : C02, C04, C05, C07, C13, C15, C17, C19, C20, C22 à C26, C28, C30, C31, C32, C34 |
| Table de transitions des bons | Chaque statut × chaque geste (modifier, envoyer, approuver, renvoyer, confirmer les prix, recevoir, solder, rouvrir, annuler, supprimer) × chaque rôle : code attendu et statut suivant, dans une table versionnée |
| Table de transitions des réceptions, ordres, opérations, inventaires, dossiers | Même principe : brouillon / validé / annulé, clos / ouvert, période close |
| Verrou optimiste | Sur chaque fiche modifiable : une version périmée donne 409 « modifiée entre-temps par X » ; deux enregistrements simultanés : un seul passe |
| Journal d'audit | Chaque écriture laisse une entrée avec l'**avant/après** (champs changés) ; une recherche avec `%` ou `_` est littérale ; les taux s'écrivent en pourcent ; la direction seule le lit et l'exporte |
| Historique par fiche | Fournisseur, matière, qualité (versions de recette avec les parts et les poids), métier, bon, dossier : chaque version est datée, avec son auteur |
| Dates | Écriture antidatée dans une période close refusée ; date future refusée ; une écriture ne précède pas l'entrée de son lot ; mêmes règles sur chaque type de mouvement (paramétré sur les 7 types) |
| Propriétés du moteur | Essais par génération de séquences aléatoires (hypothesis) de gestes valides (entrées, sorties, retours, annulations, transferts, ajustements). Invariants : soldes = journal ; jamais de lot sous zéro à aucune date ; valeur conservée (Σ flux valorisés = valeur du stock) ; une annulation coûte ce qu'elle annule ; une sortie puis son annulation remettent stock et CMUP à l'état d'avant ; l'état à une date passée ne dépend pas des écritures postérieures |
| Courriel | Le contenu du lundi égale l'écran (retards, alertes, échéances), et l'envoi en attente est rejoué |
| `/api/sante` | Version, numéro de schéma, âge de la dernière sauvegarde et taille de la base ; publique, sans aucune donnée métier |
| Documents | Bon fournisseur PDF/HTML : A4, en anglais, papier à en-tête (ICE, RC, NIF, CNSS, patente, banques), conditionnement, kg et mètres indicatifs, **aucun prix** ; étiquettes QR décodées ; fiches imprimables ; bilan du mois : ouverture + entrées − sorties ± ajustements − annulations = fin, en kg et en MAD |
| Exports | Chaque export rend les colonnes et les filtres de l'écran ; cellule `=…` stockée en texte ; une date hors période donne 400 ; un filtre vide donne un classeur vide |
| Reprise | La reprise depuis la base de Gestion MP est idempotente (rejouée, elle ne refait rien) ; les comptes de lignes par table sont égaux à la source ; aucun inventaire ouvert n'est repris ; les compteurs repartent après le plus grand numéro |

## 5. Tests d'écran (vitest + Testing Library)

Il y en a **0** dans Gestion MP. Cible : ≥ 60 tests, sur le modèle de `gmao-pro/frontend/src/ui.test.tsx`.

| Groupe | Ce qui est prouvé |
|---|---|
| Formats | kg avec 3 décimales au plus et l'espace des milliers ; MAD et devises à la française ; « ≈ 120 m » indicatif à côté des kg pour Cuir, Franges et Ruban ; pourcentages ; dates JJ/MM/AAAA ; « — » pour une valeur nulle ; jamais « -0 » |
| Recherche | Sans accents ni casse, mots dans le désordre (« frise rouge » trouve « IMP FRISÉ ROUGE ») ; « % » et « _ » littéraux |
| `DataTable` | Tri numérique (2 < 10) et naturel (OF-2 < OF-10) ; filtres ; pagination ; export avec les filtres ; tableau tenu dans son cadre (préférence de Mohamed) ; recherche à la frappe |
| `Form` | Le bouton dit ce qui manque (« Il manque : lot, magasin ») ; sélecteur au clavier ; Échap demande confirmation si la saisie a changé ; aucune saisie perdue (défaut n° 3 de la recette atelier) |
| Menus et droits | Chaque rôle a son menu, et peut ouvrir chacune de ses entrées (`permis`) ; un écran interdit renvoie à l'accueil ; l'alimentation n'a ni Cockpit, ni Plan d'achat, ni Commandes, ni Analyse, ni Réglages ; aucun bouton ou colonne de prix pour elle (rendu avec des données qui contiennent `null`) |
| Cohérence écran / serveur | Chaque appel `api.get/post/put/supprimer` de l'écran vise une route de l'OpenAPI, avec la bonne méthode (reprise de `outils/routes_ecran.py`, en test) ; chaque action visible pour un rôle correspond à une route que le serveur lui accorde (matrice A3) |
| Atelier au téléphone | Envoyer : proposition, conversion bobines et palettes en kg, blocage annoncé avant de valider (inventaire en cours, lot arrivé après la date) ; Retour : pas plus que le sorti ; « Nouvel ordre » après confirmation |
| Aide | Chaque écran a sa section dans `aide.json` ; aucun lien d'aide ne mène à une page inexistante |
| KPI | Chaque carte affiche sa formule (infobulle) et la valeur reçue sans la recalculer |

## 6. Vérification indépendante des chiffres (`backend/essais/verification_chiffres.py`)

### Principe

On reprend celui de GMAO PRO et du vérificateur de Gestion MP :

- **ne jamais importer `gestion_mp_pro`** ;
- lire les données brutes par une route d'export réservée à la direction (`/api/donnees/{table}.json`
  : mouvements, soldes, lots, articles, fournisseurs, devises, commandes et lignes, réceptions et
  lignes, factures, dossiers, lignes et frais, postes, ordres et lignes, qualités, recettes et
  versions, plan et versions, métiers et fils, inventaires, paramètres) ;
- recalculer avec les **formules de la documentation** (`docs/CAHIER-DES-CHARGES.md`), écrites une
  seconde fois dans le script ;
- comparer à ce que renvoient les écrans.

Tolérance : 0,001 kg ; 0,01 MAD ; 1e-6 en relatif sur les ratios et les prix unitaires.

### Ce qui est recalculé

Chaque ligne est une famille de vérifications. Elles sont faites pour chaque matière, lot, bon,
réception, ordre ou dossier, **à la date du jour et aux 13 dates de référence**.

| Domaine | Indicateurs recalculés depuis la base brute |
|---|---|
| Stock | Stock par lot et magasin = Σ journal ; par matière (magasin + machine) ; quarantaine à part ; disponible ; stock en machine = Σ mètres × bobines/m × poids de bobine mesuré du lot (sinon le catalogue) × remplissage des bobines / 100 ; aucun lot sous zéro à aucune date |
| Valeur | CMUP rejoué depuis le journal, avec ses règles : annulation à son coût, retour au fournisseur au coût du lot, ré-entrée au dernier coût connu, coût nul = 0, cours figé du mouvement, entrée importée au coût de revient de sa ligne de réception. Valeur magasin + machine. Les 5 invariants du vérificateur (7a à 7e). Écart au catalogue. Valeur à une date passée |
| Achats | Reçu net de chaque ligne (retours au prorata des pesées du lot) ; reste ; part livrée ; statut de livraison (Attendu, En retard selon la tolérance, Reçu sous réserve, Livré) ; montant estimé au cours figé ; montant à approuver ; engagé du Cockpit |
| Fournisseurs | Ponctualité (date promise, camion de plusieurs bons), complétude (lignes dues, tolérance), OTIF par réception, moyennes sur les réceptions notées, taux de retours, délai mesuré, score = OTIF × 60 + retours (20 → 0 entre 0 et 5 %) + délai (20 jusqu'à 15 j), classement et action |
| Échéancier | Montant (saisi, sinon pesé × prix), échéance (date + délai), échu, à dater, réglé, écarté (réception annulée), frais de dossier |
| Importations | Marchandise (valeur × cours, MAD sans cours) ; répartition de chaque frais (poids en kg ou valeur, frais affectés à une ligne, répartition figée) ; coût hors TVA, TVA, décaissé ; droits attendus par code douanier ; TVA attendue = taux × (valeur en douane + droits + TPI 0,25 %) ; écart de facture (C36) ; frais aberrants (C35) ; coût d'une qualité pondéré par la recette |
| Recettes | 100 % par rôle ; kg/m² (ml/m² × densité pour un rôle au mètre) ; coût au m² = Σ kg/m² × prix au kg × taux × (1 + perte) |
| Production | Prévu figé de chaque ordre ; net = sorties − retours, annulations exclues ; écart en kg et en % ; réalisé par qualité contre le plan de son époque (prorata des jours) |
| Plan et besoins | Plan mensuel (base × saisonnalité × croissance ancrée) ; besoins ; coefficient de réalisation (fenêtre en mois arrondis au demi supérieur, taux hérité d'un fil remplacé) ; conso mensuelle ; stock min recalculé et plafonné ; stock projeté ; commandes dans le délai et dans la couverture ; quantité à commander (moins les brouillons) ; statut ; tier ; urgence ; budget = Σ lignes |
| Classements | ABC (valeur de conso, 80/95 %), XYZ (CV sur les sorties nettes des 12 mois clos), dormants (stock net > 0, sans entrée ni sortie depuis le seuil) |
| Inventaires | Théorique à la date, écarts en kg et en MAD, retenu (second comptage), à recompter, inventaire tournant par magasin |
| Pilotage | Cockpit (valeur du stock, engagé, alertes, DIO = valeur ÷ coût de rotation × 365, part dormante, couverture pondérée) ; bilan du mois équilibré ; nombre d'anomalies de chaque contrôle ; photo du jour = écrans |

Bases sur lesquelles le script tourne :

1. la base d'essai après pytest ;
2. `gestion_mp_pro_parite` (l'année) ;
3. la copie après le scénario.

Sortie : une ligne ✓/✗ par vérification, le total, les écarts. Code 1 s'il y a un écart.

Le script doit lui-même faire ses preuves. `tests/test_verification.py` injecte les fautes connues :

- CMUP × 1,1 ;
- l'ancien moteur du coût moyen (G1, G2, G3) ;
- une écriture SQL sous zéro ;
- une répartition de frais à la mauvaise clé ;
- un OTIF compté sur toutes les réceptions ;
- un solde faussé.

Il exige que chacune soit vue.

## 7. Parité de calcul PRO = Gestion MP sur l'année d'essai (`backend/essais/parite_gestion_mp.py`)

### 7.1 Les mêmes données dans les deux

1. **Source unique** : la base `gestion_mp_comparaison` de Gestion MP. Elle contient l'année d'essai
   de l'ERP Fil, importée par `outils/importer_erp_fil.py`, avec 0 écart à corriger face à l'ERP
   Fil. Si elle n'existe pas, on la recrée par cet outil, en lecture seule sur l'ERP Fil.
2. `pg_dump gestion_mp_comparaison | pg_restore -d gestion_mp_parite_source` : Gestion MP ne
   calculera que sur cette copie. Les empreintes de `gestion_mp` et de `gestion_mp_comparaison` sont
   relevées avant et après : elles doivent être égales.
3. **Reprise PRO** (`gestion_mp_pro.reprise.depuis_gestion_mp`) de `gestion_mp_parite_source` vers
   `gestion_mp_pro_parite`. Ce sont les mêmes règles que la mise en service : toutes les tables,
   les numéros gardés, les annulations à la date de ce qu'elles annulent, les compteurs repartis.
4. **Contrôle d'import** :
   - comptes de lignes par table métier égaux ;
   - Σ des quantités et Σ quantité × prix du journal égaux par matière ;
   - soldes = journal ;
   - mêmes numéros de documents ;
   - mêmes empreintes de recettes et de plans versionnés.

   Le rapport commence par ce tableau, comme celui de l'ERP Fil.

### 7.2 Les sorties comparées

Chaque logiciel produit un JSON canonique, chacun dans son environnement. Côté Gestion MP, on étend
`outils/comparaison_calcul.py` (lancé depuis le virtualenv de Gestion MP, sans modifier son dépôt :
une copie du script dans `backend/essais/`). Côté PRO, un calcul symétrique par ses `services/`.

| Section | Clé | Contenu |
|---|---|---|
| `stock` | référence | toutes les colonnes de l'état du stock : stocks, conso, besoins sur 12 mois, couverture, stock min, projeté, à commander, statut, ABC/XYZ, dormant, en machine |
| `besoins`, `mrp` | référence (× qualité) | 12 mois |
| `nomenclature` | qualité \| référence | parts, kg/m², ml/m², prix au kg, coût au m² |
| `plan_achat_lignes`, `plan_achat_fournisseurs` | référence ; fournisseur | quantités, unités, montants, tier, urgence, budget |
| `valorisation` | référence | stock, magasin, machine, CMUP, valeurs, écart au catalogue |
| `journal_valorise` | id du mouvement | coût unitaire et valeur de **chaque** mouvement (10 411) |
| `lots` | référence \| lot | entrées, sorties, stock par magasin, statut, dates |
| `commandes` | n° | statut, livraison, reçu, reste par ligne, montants estimés, cours figé |
| `receptions` | n° | pesé, refusé, quarantaine, écarts de pesée |
| `performance_receptions`, `fournisseurs` | n° ; nom | ponctualité, complétude, OTIF, moyennes, score, classement |
| `echeancier` | pièce | montant, échéance, état |
| `dossiers` | n° | marchandise, frais par ligne, coût hors TVA, TVA, TVA attendue, droits attendus, écart de facture |
| `ordres` | n° | prévu, consommé, retours, net, écart, lots, dates |
| `realise` | qualité × mois | plan, réalisé |
| `inventaires` | n° | écarts en kg et en MAD |
| `controles` | code | nombre d'anomalies **et** liste des éléments signalés |
| `cockpit`, `bilan` (14 mois) | arbre | tous les indicateurs |
| `volumes` | — | décomptes |

**Dates de référence** : la fin de chacun des 12 mois de l'année d'essai, plus le 2026-10-08, soit
13 calculs par logiciel. L'audit de Gestion MP avait jugé les besoins à 19 dates ; on ajoute 6 dates
au milieu d'un mois quand une version de plan ou de recette y change.

### 7.3 Parité par l'API (seconde passe)

Les mêmes sections sont relues par les routes HTTP des deux serveurs, avec le compte direction. On
vérifie ainsi la couche `api/` (filtres, arrondis d'affichage, masquage) en plus des `services/`. Les
écrans de l'alimentation sont comparés entre eux : quantités égales, prix absents des deux côtés.

### 7.4 Parité dynamique (troisième passe)

Le scénario du § 8 est joué **geste par geste dans les deux logiciels**, sur deux copies de la même
base, par leurs API. Après chaque geste, on compare le stock, la valorisation et les sections
touchées. On prouve ainsi que les **règles d'écriture** (refus, blocages, statuts suivants, numéros)
sont les mêmes, et pas seulement les calculs sur un état figé. Un refus d'un côté et une acceptation
de l'autre est un écart à corriger.

### 7.5 Tolérances

Les valeurs brutes sont comparées **avant l'arrondi d'affichage**.

| Grandeur | Tolérance |
|---|---|
| Quantités (kg) | 0,001 kg absolu |
| Montants (MAD, devise) | 0,01 absolu ou 1e-6 relatif (le plus grand) |
| Prix et coûts unitaires, CMUP | 1e-6 relatif |
| Ratios (OTIF, parts, taux, CV) | 1e-6 absolu |
| Jours, nombres d'éléments, rangs | exact |
| Statuts, classes, tiers, libellés codés | exact, après une table de correspondance déclarée si PRO change un libellé (par exemple l'émoji) |
| Dates | exact |

Si PRO calcule en `Decimal` et Gestion MP en `float`, la tolérance des montants couvre l'écart de
représentation. Un écart au-delà est un défaut, pas un arrondi.

### 7.6 Règles d'explication

Même discipline que `comparer_erp_fil.py` : **forme et ampleur**.

- Un **champ ajouté** par PRO est excusé. Un **élément entier** en plus ou en moins (ligne, lot,
  bon) ne l'est jamais sans règle qui le prouve.
- Une **correction voulue** de PRO (défaut de Gestion MP découvert pendant la réécriture) n'est
  admise que si les trois conditions sont réunies :
  1. elle est inscrite dans `docs/heritage/DECISIONS.md`, avec l'accord écrit de Mohamed ou la
     justification « pratique d'usine » ;
  2. elle a sa règle dans `parite_gestion_mp.py`, qui recalcule l'écart attendu et ne l'excuse que
     s'il correspond ;
  3. elle a son test PRO.
- Il n'y a **pas de dictionnaire libre d'excuses par clé**. Toute excuse est une fonction qui
  vérifie une valeur.
- Cible : **0 écart à corriger**. Le nombre d'écarts expliqués hors champs ajoutés est publié par
  section dans `essais/resultat-parite.txt` et dans `docs/RECETTE.md`, chacun avec sa décision.

### 7.7 Réciproque

PRO ne doit rien perdre. Le script vérifie aussi que chaque champ produit par Gestion MP existe dans
PRO, sous son nom ou par une correspondance déclarée. Un champ de Gestion MP absent de PRO est un
écart à corriger.

## 8. Scénario de bout en bout : un mois d'usine (`essais/scenario_complet.py`)

Il est joué sur `gestion_mp_pro_scenario`, une copie de l'année de parité avec ses référentiels
réels. Chaque rôle joue avec son compte. Toutes les valeurs attendues sont **calculées à la main
dans le script, avant le geste**, et comparées au centime. Il reprend le « mois joué geste par
geste » de l'audit de Gestion MP, qui a fait 418 vérifications, et le met dans le dépôt.

| # | Rôle | Geste | Attendus vérifiés |
|---|---|---|---|
| 1 | Direction | Révise le plan d'une qualité au 10 du mois | Version du plan ; besoins = prorata des jours ; mois clos inchangés |
| 2 | Achats | Lit le plan d'achat et prépare un bon depuis la proposition | Quantités, unités (palettes), montants ; brouillon déduit de la proposition, pas du projeté |
| 3 | Achats | Envoie un bon au-dessus du seuil | `a_approuver`, sans numéro ; la direction le renvoie avec un motif, puis l'approuve : numéro sans trou |
| 4 | Achats | Imprime le bon fournisseur | A4, anglais, papier à en-tête, conditionnement, **aucun prix** |
| 5 | Achats | Confirme les prix en deux fois, après un changement du cours | Cours figé à la 1ʳᵉ confirmation ; date promise figée ; une hausse de 20 % repasse par la direction |
| 6 | Achats | Saisit les jalons d'expédition | ETA ; la date promise ne bouge pas |
| 7 | Achats | Reçoit un camion de deux bons : partiel, une ligne sous réserve, une refusée, un lot interne | Reçu, reste, quarantaine, poids de bobine mesuré, numéros REC et LOT ; ponctualité et complétude par bon |
| 8 | Achats | Libère la quarantaine | Bon soldé de lui-même, « Livré », note de livraison |
| 9 | Achats | Saisit la facture, ouvre le dossier d'importation, ajoute fret, droits, TVA, transit, clôt | Marchandise, répartition au poids et à la valeur, coût hors TVA, TVA attendue (TPI), droits attendus, écart de facture ; **coût de revient d'un lot au millionième** (l'audit : 32,747048 MAD/kg) et nouveau CMUP |
| 10 | Alimentation (téléphone) | Monte des fils sur un métier | Stock en machine, poids mesuré, laize |
| 11 | Alimentation | Envoie aux machines deux qualités (proposition FIFO, bobines, palettes) | Prévu (perte comprise), lots pris, CMUP de sortie, numéro OF après la date du précédent |
| 12 | Alimentation | Retour des machines (bobines) | Net de l'ordre, écart en %, motif R1 |
| 13 | Alimentation | Tente une sortie depuis la quarantaine, puis datée avant l'entrée du lot | Refusées, message clair |
| 14 | Achats | Retour au fournisseur d'une partie d'un lot | Coût du lot ; bon rouvert, reçu net ; taux de retours du fournisseur |
| 15 | Achats | Réclamation, de l'ouverture à la clôture avec avoir | Issue, montant obtenu |
| 16 | Achats | Inventaire d'un magasin avec recomptage | Sorties suspendues pendant le comptage ; écarts en kg et en MAD ; ajustement |
| 17 | Alimentation | Annule un ordre qui a eu un retour | Stock et CMUP à l'état d'avant |
| 18 | Achats | Règle des factures et des frais | Échéancier : échu, réglé, à dater |
| 19 | Direction | Clôt la période à la fin du mois | Toute écriture, tout frais, tout cours antérieurs refusés ; valorisation de fin de mois figée |
| 20 | Direction | Lit le bilan du mois et le Cockpit | Bilan équilibré (kg et MAD) ; valeur = Valorisation = Cockpit = photo = courriel |
| 21 | Direction | Contrôles | Aucune nouvelle anomalie bloquante ; les contrôles déclenchés exprès (C06 retard, C08 écart de pesée, C36 facture) sonnent avec le bon nombre |
| 22 | — | `verification_chiffres.py` sur la base du scénario | 0 écart |
| 23 | — | Parité dynamique (§ 7.4) | Mêmes résultats et mêmes refus que Gestion MP à chaque geste |

Sortie : `essais/resultat-scenario.txt`, une ligne ✓ par étape et le nombre de valeurs vérifiées
(cible ≥ 400).

## 9. Recette navigateur, par rôle et par écran

### 9.1 Automatique (`essais/recette_navigateur.js`)

C'est le script de GMAO PRO, adapté. Collé dans la console, connecté avec un rôle, il ouvre chaque
entrée du menu, plus les fiches, les impressions, le QR, le profil et l'aide. Il relève :

- les réponses 4xx et 5xx ;
- les erreurs JavaScript ;
- les notes d'erreur ;
- les pages vides ;
- les chargements bloqués.

Pour l'alimentation, il relève **aussi tout texte qui ressemble à un montant** (`MAD`, `USD`, `EUR`,
`Prix`, `Montant`, `Valeur`, `Budget`).

| Rôle | Écrans à ouvrir (au moins) | Écran interdit à essayer |
|---|---|---|
| Direction | Accueil, Cockpit (5 onglets), Stock (matière, lots, mouvements, fiche de lot), Sorties, Plan d'achat, Commandes, Réceptions, Importations, Inventaire, Opérations, Catalogue (matières, fournisseurs, classification), Qualités et recettes (versions), Production et besoins (plan, réalisé, MRP), Métiers, Analyse (valorisation, matrice, prix payés, opportunités, fournisseurs, coût de revient, échéancier, contrôles, production), Réglages (paramètres, devises, magasins, frais, codes douaniers, comptes, sauvegardes, journal, courriel, serveur), Guide, impressions (bon, étiquettes, bilan, feuille d'inventaire) | — |
| Achats | Les mêmes, sauf l'approbation, les comptes et le journal | Réglages › Comptes, approbation |
| Alimentation, au bureau | Accueil, Stock (sans prix), Sorties, Production (plan), Métiers, Guide | `/cockpit`, `/plan-achat`, `/commandes`, `/analyse`, `/reglages` |
| Alimentation, au téléphone | Atelier : Envoyer, Mes ordres, Retour, Chercher un lot (adresse `/lot/{id}` comme le QR), Déplacer, Signaler, Monter les fils, fiche de lot | `/cockpit` |
| Administrateur technique | Réglages techniques, sauvegardes, serveur, comptes, journal | Écrans métier qui écrivent |

Résolutions :

- bureau en 1366 × 768 (mesure `scrollWidth ≤ clientWidth` et hauteur des tableaux dans leur cadre),
  puis en 1920 × 1080 ;
- téléphone en 375 × 812 et 360 × 640.

Le résultat va dans `essais/resultat-recette-ecran.txt`, avec le même tableau que GMAO PRO.

### 9.2 Parcours par de vrais clics

On rejoue les parcours des trois recettes de Gestion MP (`docs/recette/*.md` § « Parcours joués »)
sur PRO, avec leurs « chiffres refaits à la main ». Par exemple :

- préparation TURKAN : 5 028,8 kg et 12 273,9 USD ;
- MF 200 m² : 117,3 kg sans perte, 119,6 avec ;
- reste du lot : 11 836,794 ;
- dossier : SBR 13,60 et PES 19,84 MAD/kg.

On vérifie aussi que chacun des **défauts relevés** dans ces recettes (2 + 2 + 3 bloquants,
19 + 11 + 24 gênants, 22 + 25 + 12 mineurs) est absent de PRO. Le tableau défaut → état PRO va dans
`docs/RECETTE.md`.

## 10. Épreuve de charge (`backend/essais/charge.py`)

Mode `remplir` : une base synthétique tirée au sort avec une graine fixe (42), à partir des
référentiels réels et des proportions de l'année d'essai. Mode `mesurer` : un **vrai serveur
uvicorn** (pas `TestClient`), appels HTTP.

| Volume | Matières | Lots | Mouvements | Commandes | Réceptions | Ordres | Dossiers | Années |
|---|---|---|---|---|---|---|---|---|
| Réel (parité) | 124 | 1 684 | 10 411 | 330 | 317 | 320 | 90 | 1 |
| ×10 | 300 | 17 000 | 105 000 | 3 300 | 3 200 | 3 200 | 900 | 5 |
| ×30 | 600 | 50 000 | 315 000 | 10 000 | 9 500 | 9 600 | 2 700 | 10 |

Mesures :

- chaque écran du § 9.1, avec ses onglets, en médiane et pire de 5 appels ;
- les exports complets ;
- les écritures : valider une réception de 20 lignes, valider un ordre de 15 lignes, clôturer un
  dossier de 50 lignes, valider un inventaire de 200 lignes ;
- les dates de référence passées ;
- 20 postes qui ouvrent le stock ensemble, puis 20 postes mêlant lectures et écritures pendant 60 s
  (p50, p95, aucune erreur) ;
- 10 000 tentatives de connexion parallèles (verrouillage, aucune erreur 500).

Seuils : critère A9. Si un écran dépasse son seuil, le calcul optimisé doit redonner **les mêmes
chiffres octet pour octet** (méthode de GMAO PRO). Le résultat va dans `essais/resultat-charge.txt`.

## 11. Sécurité

### 11.1 Droits, route par route

- **Test structurel** (repris de GMAO PRO `test_toute_route_qui_ecrit_nomme_ses_roles`) : toute
  route d'écriture porte une dépendance `droit(...)`, sauf la connexion, la déconnexion et
  l'installation. Le test échoue s'il voit moins de routes que prévu.
- **Matrice versionnée** `tests/matrice_droits.csv` : chaque route de l'OpenAPI × anonyme,
  alimentation, achats, direction, administrateur → code attendu (200/201, 401, 403). Un test la
  rejoue entièrement, paramètres remplis par des fabriques. Une route nouvelle absente de la matrice
  fait échouer le test.
- Les refus métier propres à chaque rôle, repris de Gestion MP :
  - approuver ou renvoyer : direction seule ;
  - libérer la quarantaine : achats seuls ;
  - valider un ordre : alimentation et direction ;
  - plan, recettes, rôles, postes de frais, codes douaniers, réglages d'un métier : direction ;
  - monter des fils : alimentation ;
  - journal et état du serveur : direction.

### 11.2 Prix jamais exposés à l'alimentation

- Filtre serveur générique `sans_prix`, appliqué à toute profondeur de la réponse. Un **test
  unitaire du filtre** couvre les dictionnaires imbriqués, les listes et les noms de clés
  (`prix*`, `montant*`, `valeur*`, `cout*`, `cmup*`, `budget*`, `taux`, `cours`, `devise` d'un prix,
  `economie*`, `revient*`, `tva*`, `droits*`, `frais*`).
- **Balayage** : pour **chaque route GET** permise à l'alimentation, sur une base peuplée (cas de
  chaque type), on parcourt récursivement la réponse. On exige qu'aucune clé de la liste n'ait une
  valeur non nulle, et qu'aucune chaîne ne contienne un symbole monétaire.
- On fait de même pour **chaque export** (cellules xlsx), **chaque impression** (HTML/PDF) et
  **chaque message d'erreur** renvoyé à l'alimentation. Exemple : un refus « il n'y avait que
  20,00 kg » est permis, « 200 MAD » ne l'est pas.
- Les quantités restent visibles : stock, statut, besoins.

### 11.3 Concurrence (`test_concurrence.py` et `essais/concurrence.py`, 50 répétitions)

Les 9 courses de Gestion MP sont reprises :

1. deux sorties de 70 % d'un même lot ;
2. deux retours de 70 % d'un même ordre ;
3. deux réceptions qui franchissent l'excédent ;
4. trois créations d'un même dossier (et la course rattrapée par l'index unique) ;
5. ouverture de dossier contre annulation de réception ;
6. correction de facture contre ouverture ;
7. validations d'ordres sous verrou (les numéros suivent les dates) ;
8. connexions ratées simultanées ;
9. (restauration avec sessions ouvertes).

Elles sont ajoutées :

- double envoi d'un bon (un seul numéro, sans trou) ;
- 20 validations parallèles de documents de la même série (numéros consécutifs, sans doublon) ;
- double approbation ;
- approbation contre modification du bon ;
- solder contre recevoir ;
- validation d'inventaire contre sortie ;
- clôture de dossier contre ajout de frais ;
- clôture de période contre écriture antidatée ;
- deux enregistrements d'une même fiche (verrou de version) ;
- montage d'un même étage depuis deux téléphones ;
- changement de cours pendant une confirmation de prix.

Invariant vérifié après chaque course : soldes = journal ; aucun lot négatif ; vérificateur 0 écart.

### 11.4 Migrations

- `ETAPES` numérotées de 1 à N **sans trou** (Gestion MP en a : 10 et 12 manquent), une étape par
  changement, jamais modifiée après livraison.
- `migrer()` sur une base vide, puis relancé : rien n'est refait.
- Depuis la base de la version précédente de PRO (fixture versionnée) : aucune perte. Comptes de
  lignes, empreintes, vérificateur à 0.
- Deux processus démarrés ensemble : une seule application des étapes (verrou consultatif).
- Une étape qui échoue : transaction annulée, schéma inchangé, `/api/sante` le dit.

### 11.5 Sauvegarde et restauration

- La sauvegarde quotidienne et la sauvegarde manuelle produisent un fichier relu
  (`pg_restore --list`). Un échec est signalé : journal, `/api/sante`, Cockpit.
- La copie externe est faite, ainsi que celle des pièces jointes.
- **Restauration réelle** dans `gestion_mp_pro_restauration_essai` : comptes de lignes et empreintes
  par table identiques à la source, vérificateur 0 écart.
- Restauration depuis l'écran sur un vrai serveur : moins de 30 s, sans attente sur sa propre
  connexion (défaut de Gestion MP), autres sessions coupées, inscrite au journal.
- La base vide de référence se restaure.

### 11.6 Le reste

- Sessions : expiration, déconnexion, changement de code, compte désactivé.
- Limitation des essais (429).
- En-tête anti-CSRF.
- Pièces jointes :
  - types permis seulement : ni `.exe` ni SVG ;
  - taille maximale ;
  - nom de fichier sans chemin (traversée de répertoire) ;
  - servies en `attachment`.
- Recherche : `%` et `_` littéraux, aucune injection.
- Cellules d'export commençant par `=`, `+`, `-`, `@` : stockées en texte.
- Robustesse (critère A13) : génération depuis l'OpenAPI, refus en français, jamais de 500.

## 12. Livrables de la recette

- `docs/RECETTE.md` :
  - le verdict par critère (§ 0) ;
  - les essais réalisés et leurs résultats ;
  - les anomalies trouvées et corrigées, chacune avec son test ;
  - l'état PRO de chacun des défauts des recettes et des audits de Gestion MP ;
  - les points à traiter par l'usine (données de référentiel à corriger, signalées sans être
    corrigées en silence, exigence M11) ;
  - ce qui n'a pas pu être essayé.
- `essais/resultat-*.txt` : sorties brutes datées.
- `essais/comptes-essai.md` : comptes créés pour la recette (désactivés à la fin).
- `essais/heritage.py` : contrôle que les 292 preuves de Gestion MP sont toutes citées par un test
  PRO.

## 13. Ce que PRO ajoute à ce que Gestion MP prouvait (résumé)

| Trou de Gestion MP | Réponse de PRO |
|---|---|
| Aucun test d'écran | vitest, ≥ 60 tests (§ 5) |
| Droits prouvés pour les GET anonymes seulement ; balayage de l'alimentation fait à la main | Test structurel + matrice complète + balayage automatique (§ 11.1-11.2) |
| 19 contrôles sur 38 jamais exercés | Un test par contrôle (§ 4) |
| 10 routes d'écriture et 9 de lecture jamais appelées (comptes, installation, déconnexion…) | Tests dédiés (§ 4) |
| Vérificateur limité au stock, aux soldes, au reçu, au net des ordres, aux dossiers, aux recettes et à la valeur ; muet sur les besoins, l'OTIF, le Cockpit, le bilan, l'échéancier, les dates passées | Vérification indépendante sur tous les indicateurs, à 13 dates (§ 6) |
| Parité contre un moteur de même lignée (l'ERP Fil) | Parité PRO = Gestion MP sur deux moteurs distincts, statique, par l'API et dynamique (§ 7) |
| Mois geste par geste, moteur à interrupteurs, scripts d'audit restés hors du dépôt | Scénario et vérifications dans le dépôt, rejouables (§ 8) |
| Performance jugée à 1 s (M16 exige 0,3 s), sur 1 an, en `TestClient`, sans écritures | Charge réelle / ×10 / ×30 sur un vrai serveur, écritures comprises (§ 10) |
| Migrations : étapes 10 et 12 absentes, idempotence et multi-serveurs non testées | § 11.4 |
| Restauration : non-blocage seulement, contenu non comparé | § 11.5 |
| Essais dépendants de la date du jour et de l'ordre d'exécution, sautés en silence | Horloge injectable, fabriques, aucun saut sur le poste de livraison (§ 2) |
| Contradiction sur le bon fournisseur (deux exports, l'un avec prix) | Une seule route fournisseur, sans prix (§ 3, règle 6) |
