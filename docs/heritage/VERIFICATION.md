# Héritage — comment Gestion MP prouve qu'il est juste (hors essais unitaires)

Les essais automatiques (`ESSAIS.md`) prouvent des règles sur de petites données. Gestion MP s'appuie
aussi sur six autres preuves, qui travaillent sur **l'année d'essai complète** :

| # | Preuve | Où | Question à laquelle elle répond |
|---|---|---|---|
| 1 | Vérificateur indépendant | `gestion_mp/verificateur.py` | Ce que l'écran affiche est-il ce que la base contient, recompté autrement ? |
| 2 | Comparaison avec l'ERP Fil | `outils/importer_erp_fil.py`, `outils/comparaison_calcul.py`, `outils/comparer_erp_fil.py` | Sur les mêmes données, les deux logiciels donnent-ils les mêmes nombres, et chaque écart est-il voulu ? |
| 3 | Mesure de performance | `outils/performance.py` → `docs/PERFORMANCE.md` | Les écrans répondent-ils vite sur un an d'activité ? |
| 4 | Recettes par rôle | `docs/recette/{achats,atelier,direction}.md` | Un utilisateur réel, par des clics, trouve-t-il des défauts ? |
| 5 | Audits | `docs/AUDIT-2026-10-08.md`, `docs/CONFORMITE.md`, `docs/conformite/` | Les formules sont-elles celles d'une usine, recalculées par un autre chemin ? |
| 6 | Contrôle des routes de l'écran | `outils/routes_ecran.py` | Chaque appel de l'écran vise-t-il une route qui existe, avec la bonne méthode ? |

---

## 1. Le vérificateur (`gestion_mp/verificateur.py`, 363 lignes)

### Principe

Les écrans passent par le moteur de calcul. Le vérificateur lit les **réponses HTTP des écrans**
(client connecté en direction) et les compare à la **base recomptée en SQL direct**, sans le moteur.
Un écart désigne un défaut du moteur ou du code qui l'alimente.

Pour la valeur du stock, il ne recopie pas les règles du moteur : une copie recopiait aussi ses
fautes. Le second audit l'a montré : la copie ne voyait ni l'annulation du jour rejouée trop tard, ni
la ré-entrée au catalogue, ni le coût nul pris pour « inconnu », ni la sortie datée avant son lot. Il
juge donc par des **invariants**.

Lancement : `python -m gestion_mp.verificateur` (sur `GESTION_MP_BASE`). Il crée un compte direction
interne `verificateur`, l'active le temps de la vérification puis le ferme. Il imprime ✅/❌ par
vérification, avec 10 écarts au plus, et rend le code 1 s'il trouve un écart. En essai :
`tests/test_zz_verificateur.py`, qui passe en dernier sur tout ce que la séance a écrit.

Tolérance : `_ecart(a, b)` = |a − b| > max(0,01 ; 1e-6 × max(|a|, |b|)). Les invariants de valeur
sont tenus à 1 MAD près ; l'ordre de grandeur, à 100 MAD et dans un rapport de 0,5 à 2.

Conversion : `_cours(devise, cours, taux)` donne 1 pour le MAD, même si un cours y est porté par
erreur. Sinon, le cours porté par la ligne ; à défaut, celui de la table `devise`.

### Les 11 vérifications

| # | Nom affiché | Côté écran | Recalcul indépendant (SQL) |
|---|---|---|---|
| 1 | Stock de chaque matière | `/api/stock` → `stock_net` | `Σ solde.quantite` des lots de l'article (LEFT JOIN, 0 si aucun) |
| 2 | Soldes égaux au journal, jamais négatifs | — (base contre base) | Par (lot, magasin) : `solde.quantite` = `Σ mouvement.quantite` ; et `count(solde < −0,0005)` = 0 |
| 3 | Reçu de chaque ligne de commande | `/api/commandes` → `lignes[].recu` | CTE `entrees` : lignes de réceptions **validées**, qualité ≠ `refuse`. CTE `retours` : `GREATEST(−Σ quantite, 0)` des mouvements `RETOUR_FOURNISSEUR` du lot. CTE `pese_du_lot` : Σ pesé du lot. Reçu net = Σ (kg − min(kg, retours × kg / pesé du lot)) : chaque retour est réparti **au prorata des pesées du lot** |
| 4 | Sorti net de chaque ordre de fabrication | `/api/bons` (validés) → `net` | `−Σ mouvement.quantite` par `ordre_id` (sorties moins retours, annulations comprises) |
| 5 | Coût hors TVA et TVA de chaque dossier | `/api/dossiers` → `revient_mad`, `tva_mad` | Marchandise = Σ `valeur_devise × cours` ; frais groupés par `poste_frais.recuperable` : coût = marchandise + frais non récupérables ; TVA = frais récupérables. Le coût n'est jugé que si le dossier a de la marchandise |
| 6 | Recettes à 100 % par rôle | `/api/controles` → C01 | `Σ pourcentage` par (qualité, rôle de l'article) : un total ≠ 100 à 0,01 près doit figurer dans C01. C01 peut en dire plus (un rôle pesé sans fil), pas moins |
| 7a | Valeur conservée : entrées − sorties = valeur du stock | Journal valorisé `/api/mouvements?avec_valeur` (lu en entier, par pages de 5 000) et `/api/valorisation` → `valeur_magasin_mad` | Par matière, Σ `valeur_mad` des lignes du journal = valeur en magasin, à 1 MAD près |
| 7b | Aucun lot sous zéro à une date passée | — | Fonction de fenêtre SQL : cumul par (lot, magasin) trié par `date_effet` ; premier jour où le reste < −0,0005 |
| 7c | Aucune écriture à coût nul sans raison | Journal valorisé | Ligne à `cout_mad` 0 pour une matière dont `article.prix > 0` (transferts exclus) |
| 7d | Une annulation rend le coût de ce qu'elle annule | Journal valorisé | `cout_mad(annulation)` = `cout_mad(contrepasse_id)` à 1e-6 près (transferts exclus) |
| 7e | Ordre de grandeur : chaque lot à son coût d'entrée | `/api/valorisation` | Second modèle : chaque lot qui reste (Σ soldes > 0,0005) × son **coût d'entrée** ; écart signalé si |écran − modèle| > 100 MAD **et** rapport hors [0,5 ; 2]. Matières dont un lot est sans coût connu : ignorées |

Le coût d'entrée d'un lot (`_cout_d_entree_des_lots`) se calcule ainsi :

1. `_revient_des_dossiers` refait la répartition des frais **sans le moteur** : clé du poste (poids ou
   valeur), frais affecté à une ligne, répartition figée (`dossier_charge_part`) si elle couvre les
   lignes et somme au montant. Il en tire un coût unitaire par ligne de réception, et par (article,
   lot) pour les lignes saisies à la main.
2. Pour les mouvements `OUVERTURE` ou `RECEPTION` positifs, ni annulés ni annulations : le coût du
   dossier par la ligne de réception du lot. Sinon, pour une ouverture seulement, le coût manuel par
   (article, n° de lot). Sinon, le prix × le cours figé. Sinon (prix nul), le lot est ignoré.

### Ce qu'il voit prouvablement

Trois essais injectent une faute pour vérifier que le vérificateur la voit :

- CMUP × 1,1 (`test_api_le_verificateur_voit_une_valeur_fausse`) ;
- l'ancien moteur du coût moyen réinjecté (`test_le_verificateur_voit_les_fautes_du_moteur_d_avant`) :
  G1 → 7a, G2 → 7e, G3 → 7d ;
- une écriture SQL hors chemin (`test_c37_et_le_verificateur…`) → 7b et 7c.

### Ce qu'il ne vérifie pas

Ces sujets ne sont couverts que par la parité ERP Fil, qui part du **même code de moteur** :

- les besoins, le plan d'achat, les statuts et la couverture ;
- les OTIF et les scores ;
- les indicateurs du Cockpit (DIO, rotation, dormants) ;
- le bilan mensuel ;
- l'échéancier ;
- les écarts d'inventaire ;
- le coût au m² des qualités ;
- la valeur en machine (7a ne regarde que `valeur_magasin_mad`) ;
- les dates passées (il ne juge qu'aujourd'hui) ;
- les droits.

---

## 2. La comparaison avec l'ERP Fil (exigence M03)

### Chaîne

```
gestion-fil.db (ERP Fil, SQLite, jamais modifiée : copie + empreinte avant/après)
   │  outils/importer_erp_fil.py      (base gestion_mp_comparaison, recréée)
   ▼
gestion_mp_comparaison (PostgreSQL)
   │
   ├── comparaison_calcul.py fil <copie.db> <date> fil.json   (virtualenv de l'ERP Fil, son moteur)
   └── comparaison_calcul.py mp  <url>      <date> mp.json    (virtualenv de Gestion MP, son moteur)
   ▼
comparer_erp_fil.py : différences champ par champ → règles d'explication → docs/COMPARAISON-ERP-FIL.md
```

Commande : `.venv/bin/python outils/comparer_erp_fil.py [date_de_reference]` (par défaut
aujourd'hui). Code de sortie 0 seulement s'il n'y a aucun écart inexpliqué. Le rapport finit par
« Écarts à corriger : N ». `tests/test_parite.py` lance l'outil et exige « écarts à corriger : 0 ».
Avec `GESTION_MP_COMPARAISON_JSON=<dossier>`, les deux JSON bruts sont gardés pour un audit.

### L'import (`importer_erp_fil.py`)

- Garde-fou : la base doit finir par `_comparaison`, et l'import s'arrête si elle a déjà des
  mouvements. Il vérifie l'empreinte de la base de l'ERP Fil avant et après.
- Étapes :
  1. `migrer()` ;
  2. magasins ;
  3. `initialiser()` ;
  4. `reprendre()` : les référentiels, comme la reprise réelle ;
  5. l'activité : lots, commandes, factures, réceptions, ordres, journal, dossiers, inventaires
     validés, journal des actions ;
  6. remise des compteurs après le plus grand numéro de chaque série (`[A-Z]+-AAAA-N`).
- Choix de traduction, à reprendre tels quels dans PRO :
  - **une écriture signée par lot et par magasin** ; un transfert donne deux écritures liées par
    `paire` ; les soldes sont la somme du journal ;
  - une **annulation est datée du jour de ce qu'elle annule** (l'ERP Fil la datait de sa saisie, ce
    qui creusait des lots dans le passé) ;
  - une ligne « Réserve » garde le magasin de l'ERP Fil (il n'avait pas de quarantaine) ;
  - un **inventaire en cours n'est pas repris** (il suspendrait tout : c'était un défaut bloquant de
    la recette du 4 octobre) ; les inventaires comptés par référence sont rattachés à un lot
    « (compté par référence) », sans stock ;
  - facture : montant = Σ pesé × prix des lignes non refusées ; échéance = date + délai de paiement
    du fournisseur ;
  - une marchandise de dossier en « MAD » au cours ≠ 0 reprend la devise de sa réception
    (`devise_ligne_dossier`), sinon passe en MAD au montant converti ;
  - `relier_dossiers_aux_factures` : un dossier dont toute la marchandise vient d'une facture la
    prend ;
  - les sorties en attente de l'ERP Fil deviennent des lignes d'ordres en brouillon ;
  - les lignes d'ordres = sorties nettes par lot.
- Contrôle final : nombre de (lot, magasin) dont le solde ≠ Σ journal à 0,001 près, imprimé
  « Soldes égaux au journal : oui ».
- Volumes de l'année d'essai (rapport du 8 octobre) : 124 matières, 18 qualités, 319 lignes de
  recette, 12 fournisseurs, 4 métiers ; 1 684 lots, 330 commandes, 316 factures, 317 réceptions
  (1 508 lignes), 320 ordres, 10 411 mouvements (34 annulations), 90 dossiers (984 marchandises,
  25 reliés à leur facture), 12 inventaires (2 en cours non repris), 3 823 actions de journal.

### Ce qui est calculé (`comparaison_calcul.calculer`)

Les deux côtés appellent les mêmes fonctions du moteur, à la même date de référence. Le côté ERP Fil
passe `methode = "corrigee"`. Chaque valeur est rendue comparable par `propre()` : flottants arrondis
à 4 décimales, dates en ISO, dataclasses aplaties. Les listes sont indexées par clé métier.

| Section | Fonction | Clé |
|---|---|---|
| `stock` | `etat_stock` | référence |
| `besoins` | `besoins_mensuels` | référence → 12 mois |
| `nomenclature` | `nomenclature` | qualité \| référence |
| `plan_achat_lignes`, `plan_achat_fournisseurs` | `plan_achat` | référence ; fournisseur |
| `valorisation` | `valorisation` | référence |
| `cockpit` | `cockpit` | arbre |
| `controles` | `controler` | code → {libellé, anomalies} |
| `lots` | `stock_par_lot` | référence \| lot |
| `ordres` | `consommation_par_of` | n° d'OF |
| `performance_receptions` | `performance_receptions` | n° de réception |
| `fournisseurs` | `scorecard_fournisseurs` | fournisseur |
| `historique_prix`, `pesees`, `opportunites` | nombres d'éléments | — |
| `bobines` | `evolution_bobines` | référence \| fournisseur |
| `revient_dossiers` | `revient_dossier` | n° → valeur, frais, TVA (arrondis à 0,01) |
| `realise` | `realise_par_qualite` | arbre |
| `cout_matiere_annuel` | `cout_matiere_annuel` | nombre |
| `plan_m2` | Σ `plan_mensuel` | qualité |
| `volumes` | décomptes | articles, mouvements, commandes, réceptions, dossiers, ordres, qualités, recettes |

### Comparaison et règles d'explication strictes

- `differences()` descend dans les dictionnaires et les listes de même longueur. Deux nombres sont
  égaux si |x − y| ≤ max(0,011 ; 1e-6 × max) ; sinon on compare l'égalité stricte. Une clé absente
  d'un côté est un écart.
- `explication(section, chemin, x, y)` rend le texte qui excuse l'écart, ou None (écart **à
  corriger**). Ordre des tests :
  1. **champ ajouté** par Gestion MP (absent de l'ERP Fil) : excusé, sauf un **élément entier** en
     plus (une ligne, un lot) dans une section par élément. Celui-ci doit se prouver
     (`regle_element` : une ligne du plan d'achat à commander dont le statut n'est pas une alerte) ;
  2. 13 règles **qui vérifient la forme et l'ampleur** de la correction (voir le tableau) ;
  3. le dictionnaire `EXPLIQUES` : libellés, champs nouveaux et totaux qui ne se vérifient pas valeur
     par valeur. Il est restreint à des couples (section, clé) précis.
- Principe écrit en tête du code : *« un écart n'est excusé que s'il a la FORME et l'AMPLEUR de sa
  correction […] Un écart de la même famille dont l'ampleur ne correspond pas reste à
  corriger »*.

| Règle | Écart excusé si… |
|---|---|
| `regle_unite` | `unite` = « kg » côté ERP Fil et absent côté Gestion MP |
| `regle_prix_au_kilo` | Bande et Cuir (densité lue dans la copie de l'ERP Fil, `unite='ml'`) : la valeur de Gestion MP = ERP Fil × densité (tolérance 1e-4) sur les champs qui suivent le prix ; unité d'achat ml → kg ; rang, part cumulée et classe ABC égaux au classement **recalculé de chaque côté** (seuils 80/95 %) ; comptes ABC du Cockpit ; coût matière annuel : écart = Σ (coût/m² ERP Fil − Gestion MP) × m² de l'année des seules lignes Bande et Cuir, toutes les autres lignes de nomenclature étant égales |
| `regle_redate` | La matière a une sortie annulée dont l'annulation, redatée, sort de la fenêtre des 3 mois clos, et `conso_reelle` baisse exactement de la quantité ÷ 3 (à 0,05) ; alors les dérivés de la conso suivent (24 champs) ; rangs ABC recalculés |
| `regle_dormants` | `dormant` = stock net > 0 et (jours inconnus ou > 180) ; `jours_sans_mouvement` = jour − max(dernière sortie, premières entrées des lots) ; dormants du Cockpit et C18 = nombre et valeur des lignes dormantes ; C33 = nombre de lignes plafonnées |
| `regle_totaux` | Totaux par fournisseur et devise, budget, couverture pondérée : égaux, **de chaque côté**, à la somme des lignes de ce côté ; opportunités : même nombre, chaque piste = conso annuelle × écart de prix, total borné par la variation de conso × l'écart maximal |
| `regle_lot_redate` | `dernier_mouvement` du lot = date de saisie d'une annulation de l'ERP Fil, et la nouvelle date est antérieure |
| `regle_stock` | `couverture_cible_jours` = `stock_min_recalcule` ÷ (conso mensuelle ÷ 30) à 0,01 |
| `regle_valorisation` | Valeur, CMUP : même stock des deux côtés ; `ecart_mad` bouge exactement comme la valeur |
| `regle_lots` | Entrées, sorties, première entrée d'un lot (annulations et transferts exclus) |
| `regle_ordres` | Consommé et retours : le **net est conservé** à 0,05 ; date de fin antérieure ; lots ⊆ |
| `regle_plan_achat` | Tier 1 si CRITIQUE, au moins Tier 2 si URGENT, action = `ACTIONS_TIER[tier]` ; urgence « 🚨 BC URGENT » ⇔ ruptures + critiques + urgents > 0 |
| `regle_receptions` | In-full 1 → 0/None ; on_time None → 0/1 (camion de plusieurs bons) ; OTIF 1 → 0 si on_time ou in_full vaut 0 ; moyennes du fournisseur = moyenne des réceptions notées (1e-3) ; score = `points_score(otif, retours, délai)` à 1 point ; classement → action |
| `regle_cockpit` | Valeur du stock : écart = Σ des écarts de valeur de la Valorisation sur les matières détenues (1 MAD) |

### Comment on obtient « 0 écart à corriger »

On ne retouche pas le rapport : on corrige l'une des trois causes.

1. Le défaut est dans Gestion MP : on corrige le moteur ou l'import.
2. C'est une correction voulue : on écrit une **règle qui recalcule** l'ampleur attendue, avec son
   texte.
3. C'est une traduction de donnée de la reprise (annulation redatée, quarantaine absente…) : on écrit
   une règle qui la recalcule depuis la copie de l'ERP Fil.

Le rapport (`docs/COMPARAISON-ERP-FIL.md`, date de référence 2026-10-08) :

| Section | Éléments | Identiques | Écarts expliqués | À corriger |
|---|---|---|---|---|
| stock | 124 | 0 | 2 184 | 0 |
| besoins | 89 | 89 | 0 | 0 |
| nomenclature | 319 | 0 | 1 108 | 0 |
| plan_achat_lignes / fournisseurs | 15 / 11 | 0 / 0 | 103 / 35 | 0 |
| valorisation | 124 | 63 | 172 | 0 |
| cockpit | 10 | 1 | 130 | 0 |
| controles | 34 | 13 | 21 | 0 |
| lots | 1 567 | 1 467 | 232 | 0 |
| ordres | 319 | 0 | 385 | 0 |
| performance_receptions | 316 | 286 | 35 | 0 |
| fournisseurs | 12 | 0 | 45 | 0 |
| bobines, revient_dossiers, plan_m2, historique_prix, pesees, opportunites | 94, 90, 18, 1, 1, 1 | tous | 0 | 0 |
| realise, cout_matiere_annuel | 3, 1 | 2, 0 | 1, 1 | 0 |

**Limite à connaître pour PRO.** `comparaison_calcul.py` le dit : *« Les deux moteurs sont le même
code »*. Le moteur de Gestion MP descend de celui de l'ERP Fil. La parité prouve donc la fidélité de
la reprise et l'ampleur exacte de chaque correction. Elle **ne prouve pas** la justesse d'une formule
commune aux deux. Pour PRO, dont le moteur sera réécrit, la parité PRO = Gestion MP devient une
vraie contre-épreuve. Elle ne dispense pas du recalcul indépendant.

---

## 3. La performance (`outils/performance.py`, exigence M10)

- Base `gestion_mp_comparaison` : l'année réelle importée, jamais la base en service. Compte
  direction `mesure` créé au besoin.
- 18 écrans, chacun appelé 5 fois, temps côté serveur (`TestClient`, sans réseau) : médiane et pire.
  Puis **20 postes** ouvrent `/api/stock` en même temps (20 fils, 20 connexions).
- Seuil codé : médiane > **1 s** = « lent ». Rapport réécrit dans `docs/PERFORMANCE.md`.
- Résultat du 03/10/2026 (10 438 mouvements, 1 691 lots, 330 commandes, 317 réceptions, 320 ordres,
  90 dossiers) : tout sous 1 s. Les plus lents : Réceptions 528 ms (pire 761), Dossiers 455 ms,
  Ordres 306 ms, Cockpit 85 ms ; 20 postes servis en 1,9 s.
- **Écart avec l'exigence M16** (« temps de réponse < 0,3 s ») : l'outil juge à 1 s, et trois écrans
  dépassent 0,3 s. Les volumes ne valent qu'**une** année réelle, sans projection ; aucun essai ne
  l'exige ; les écritures ne sont pas mesurées.

---

## 4. Les recettes par rôle (`docs/recette/`, 4 octobre 2026)

**Méthode commune.**

- Un recetteur indépendant par rôle, qui n'a pas écrit le code et ne le modifie pas.
- Un serveur de recette par rôle : `achats.localhost`, `atelier.localhost`, `direction.localhost`.
  La base est partagée, `gestion_mp_recette_comparaison` : référentiels réels et année reprise.
- Le navigateur intégré, par de vrais clics.
- Les résolutions :
  - bureau en 1366 × 768 puis 1920 × 1080 ;
  - atelier au téléphone en 375 × 812 et 360 × 640.
- Le rapport suit un plan fixe :
  1. les défauts, du plus grave au moins grave, avec l'écran, les étapes, le constaté et l'attendu ;
  2. les suggestions ;
  3. ce qui marche ;
  4. les parcours joués ;
  5. les **chiffres refaits à la main** ;
  6. les **traces laissées dans la base**.

| Rôle | Défauts | Parcours | Chiffres refaits à la main |
|---|---|---|---|
| Achats | 2 bloquants, 19 gênants, 22 mineurs | 12 : accueil, plan d'achat (préparation TURKAN, deux devises LOMAT), commandes (seuil, prix confirmés, jalons), réceptions (partielle sur 2 bons, lot interne, réserve, refus, bobines, facture, annulation, réclamation), importations (dossier, frais, cours payés, clôture, analyse), inventaire (quarantaine, recomptage), opérations, référentiels, stock, analyse, droits | 10 : préparation 5 028,8 kg / 12 273,9 USD ; BC 6 720 EUR × 11 ; réception 4 033 kg, 2,495 kg/bobine ; échéance + 120 j ; dossier 85/26 (SBR 13,60 / PES 19,84 MAD/kg, TVA 12 082) ; écarts trouvés : fiche SBR 61 504 au lieu de 88 981 |
| Atelier (alimentation) | 2 bloquants, 11 gênants, 25 mineurs | 11 : connexion, envoyer aux machines (bobines, palettes, lot hors recette, ordre daté d'hier), mes ordres, retour, trouver un lot (QR), déplacer, signaler, monter les fils, bureau, droits | 10 : MF 200 m² (117,3 kg, sans la perte : défaut), 40 bobines × 3,1173, reste de lot 11 836,794, OF net 487,8 et −3,4 %, montage 4 233,6 kg |
| Direction | 3 bloquants, 24 gênants, 12 mineurs | 12 : cockpit, approbation de bout en bout, chaîne prix → réception → facture → dossier → sortie → retour → inventaire, cohérence entre écrans, analyse, qualités, production, réglages (sauvegarde, comptes), mode d'emploi, hauteur des pages, comparaison avec le code de l'ERP Fil | Tableau « Incohérences de chiffres entre écrans » : 18 chiffres relevés sur 2 ou 3 écrans. Valeur du stock identique (Cockpit, Valorisation, Excel) ; stock projeté faux ; 2 définitions de l'OTIF ; charges d'importation 8,4 M contre 1,9 M ; montant des bons à approuver absent du Cockpit… |

Défauts bloquants trouvés par ces recettes, tous corrigés depuis :

- un bon parti modifiable au-delà du seuil sans approbation ;
- **les prix visibles par l'alimentation par l'API** ;
- deux inventaires repris ouverts qui suspendaient toute l'usine ;
- `POST /api/sauvegardes` en erreur 500.

Les contre-épreuves sont décrites dans `CONFORMITE.md` § 7 : chaque route lue avec le compte de
l'alimentation, chaque page tenue dans 1366 × 768, l'atelier rejoué au téléphone. Elles ont été
faites **à la main** : aucun script n'est dans le dépôt.

---

## 5. Les audits et leurs méthodes

### Conformité (3–8 octobre, `CONFORMITE.md`, `conformite/1…5`, `final-A…E`)

Environ 900 éléments de l'ERP Fil ont été comparés au code, ainsi que les 86 exigences de Mohamed :
tables, champs, formulaires, paramètres, codes, grandeurs, contrôles, refus, routes, écrans. Chaque
point est repris avec sa preuve (`fichier:ligne` ou essai).

### Audit complet du 8 octobre (`AUDIT-2026-10-08.md`)

- Deux passes : 6 auditeurs, puis 10, indépendants, chacun sur **sa copie** de l'année d'essai.
- La méthode imposée :
  1. lire chaque formule ;
  2. dire ce qu'elle vaut dans la pratique d'une usine ;
  3. **la recalculer par un autre chemin** (SQL direct, Python sans le moteur) sur de nombreux cas
     réels ;
  4. l'**attaquer** :
     - cas limites ;
     - saisir → valider → annuler ;
     - dates passées ;
     - devises, kg/ml ;
     - plusieurs postes en même temps.
- Chaque constat est reproductible par un script ; chaque correction est prouvée par un essai
  automatique. Résultat : 12 défauts bloquants (3 + 9), plusieurs dizaines de gênants.

Les trois méthodes à retenir pour PRO :

1. **Recalcul indépendant à grande échelle**, sur l'année entière :
   - le stock des 124 matières et des 1 583 lots ;
   - le coût moyen de 10 438 mouvements au centime ;
   - la valeur du stock de 18,77 M MAD, identique au Cockpit, à la Valorisation, à la photo et au
     courriel ;
   - la nomenclature des 18 qualités ;
   - le prévu et le net des 319 ordres ;
   - le plan et les besoins des 89 matières **à 19 dates** ;
   - le reçu et le reste des 1 604 lignes de bons ;
   - l'OTIF des 316 réceptions ;
   - la répartition des frais d'environ 1 000 lignes de dossier ;
   - un bilan équilibré sur 14 mois.
2. **Un mois réel joué geste par geste** : septembre, sur les vrais référentiels. Chaque saisie
   (commande, réception, dossier, sortie, retour, inventaire) est suivie de ses effets attendus,
   calculés à la main. Il en est sorti **418 vérifications justes au centime**, dont le coût de
   revient complet d'un lot importé (32,747048 MAD/kg) et son effet sur le coût moyen. Les 5 erreurs
   trouvées ont été corrigées.
3. **Neutralisation par interrupteurs** (« moteur à interrupteurs ») : chaque correction voulue de
   Gestion MP est rendue désactivable. Toutes ramenées à la règle de l'ERP Fil, Gestion MP **redonne
   exactement les nombres de l'ERP Fil**. Chaque écart expliqué de la parité est ainsi attribué à
   une correction précise, et à rien d'autre. Dans le code livré, il ne reste qu'un interrupteur
   global : `Parametres.methode` (« corrigee » ou « classeur »), utilisé par
   `test_la_croissance_d_un_mois…`.

Côté sûreté, l'audit a passé :

- les 204 routes avec chaque rôle : 0 anomalie de droit ;
- 10 000 essais de connexion en parallèle : verrouillage tenu ;
- deux postes sur le même lot, la même réception, le même dossier : ni stock négatif ni doublon ;
- les numéros : sans trou ;
- les migrations depuis l'état de la production, avec plusieurs serveurs au démarrage.

**Ce qui manque au dépôt.** Les scripts des auditeurs, le mois geste par geste, le moteur à
interrupteurs et la sûreté à grande échelle sont restés dans le dossier de travail de la session. Ils
ne sont **ni dans le dépôt ni rejouables**. Seules leurs corrections, et les essais qui les
prouvent, le sont.

---

## 6. Ce que PRO doit reprendre, et rendre rejouable

| Preuve de Gestion MP | Dans PRO |
|---|---|
| Vérificateur, 11 vérifications | `backend/essais/verification_chiffres.py` : les mêmes, plus les sujets non couverts (§ 1), sans aucun import du paquet PRO |
| Parité ERP Fil, règles strictes | `backend/essais/parite_gestion_mp.py` : PRO contre Gestion MP, même principe forme + ampleur, cible 0 écart à corriger **et** 0 écart expliqué hors champs ajoutés |
| Import de l'année d'essai | Reprise PRO depuis la base de Gestion MP, sur une copie, avec les mêmes choix de traduction |
| Performance sur 1 an | `backend/essais/charge.py` : 1 an réel **et** base synthétique ×10–×30, seuils de M16 |
| Recettes par rôle à la main | `essais/recette_navigateur.js` + tableau par rôle, comme GMAO PRO ; balayage des prix automatisé |
| Mois joué geste par geste | `essais/scenario_complet.py` (un mois d'usine) dans le dépôt |
| Neutralisation par interrupteurs | Pas d'interrupteur dans le code de PRO : les écarts PRO = Gestion MP doivent être nuls ; si une correction PRO est voulue, elle est déclarée, et sa règle recalcule son ampleur |
| Contrôle des routes de l'écran | Repris : `outils/routes_ecran.py` → essai vitest/pytest contre l'OpenAPI |
