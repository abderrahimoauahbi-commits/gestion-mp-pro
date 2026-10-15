# Confort : deux lenteurs du stress « 3 ans » (15/10/2026)

Demande : « lance si cela vaut vraiment la peine » — mesurer d'abord, corriger seulement si la
mesure confirme la gêne, par le plus petit changement juste. Points de départ : stress « 3 ans »
(docs/lots/STRESS-3-ANS.md), A4 (reste `GET /ordres/ouverts`) et A5 (`PUT /inventaires/{id}/comptages`).
`/bilan`, `/export/mouvements`, `/courriel/apercu` : non touchés (décidé, gestes rares).

Mesures sur une copie de la base « 3 ans » (`gestion_mp_pro_stress_essai` → `gestion_mp_pro_confort_essai`
et `gestion_mp_pro_confort2_essai`, migrées `head`), serveur d'essai à horloge figée au 15/10/2029
(`essais.stress.app_figee`), un processus, sans tâches de fond ; durée **serveur** lue dans le
journal des requêtes, 20 appels par mesure. Machine partagée : les chiffres bougent de ±30 %
d'une série à l'autre, les rapports avant/après sont pris dans la même série.

## 1. `GET /ordres/ouverts` sans filtre — corrigé (écran seulement, aucune route changée)

### Mesure avant

| Appel | Serveur p50 / p95 / max | Réponse |
|---|---|---|
| `/ordres/ouverts` (liste entière, 2 544 ordres) | **1 189 / 1 254 / 1 956 ms** | **3,15 Mo** |
| `/ordres/ouverts?statut=valide` (2 445 ordres) | 1 120 / 1 135 / 1 259 ms | 3,03 Mo |
| `/ordres/ouverts?statut=brouillon` | 43 / 73 / 76 ms | 1,6 Ko |
| `/ordres/ouverts?statut=valide&du=jour&au=jour` | 3 / 6 / 7 ms | — |

La taille et la durée croissent avec l'historique (tous les ordres depuis l'origine, plafond 5 000).
Qui l'appelait, et ce qu'il en utilisait vraiment :

| Écran | Appel | Ce qu'il en tirait |
|---|---|---|
| Atelier « Ordres » (`Ordres.tsx`) | sans filtre | les 50 premières cartes (brouillons d'abord), puis +50, et le total « 50 sur N » |
| Atelier « Envoyer » (`useEmpechements`) | sans filtre | **une date** : celle du dernier ordre validé ou annulé (bandeau M67) |
| Bureau « Nouvelle sortie » (`SaisieOrdre`, `useSaisieOrdre`) | sans filtre | la même date (borne du champ Date, blocage) |
| Atelier « Retour des machines » (`Retour.tsx`) | `statut=valide` (+ `q`) | les 10 derniers (30 en recherche), puis +10 / +30, et le total |
| Atelier « Accueil » | `statut=brouillon` ; `statut=valide` du jour | petits par nature — inchangé |
| Bureau « Nouveau retour » (`NouveauRetour.tsx`) | `statut=valide` | tableau avec recherche locale — **inchangé** (voir § 3) |

### Changement (écran ; serveur, schémas, OpenAPI inchangés)

- `lib/dernierOrdre.ts` : `useDernierOrdre(sauf)` lit les **deux** plus récents validés et les
  deux plus récents annulés (route 135, `/ordres?statut=…&limite=2`) et leur applique le même
  `dernierOrdre` : deux suffisent même en écartant l'ordre regardé (`sauf`). Utilisé par Envoyer,
  la saisie du bureau (`SaisieOrdre`, `useSaisieOrdre`) ; `useOrdres` (liste entière) supprimé.
- Atelier « Ordres » : les brouillons (`/ordres/ouverts?statut=brouillon`) + la page des `nb`
  plus récents (`/ordres?limite=nb`, qui donne le total) ; `premiersOrdres` les fusionne comme
  `trierOrdres` le faisait sur la liste entière. « Charger les suivants » relit `limite=nb+50`
  en gardant les cartes affichées (`keepPreviousData`).
- Atelier « Retour » : `/ordres?statut=valide&limite=10+nb` (et `q=…&limite=30+nb` en recherche) ;
  total et pied « les 10 derniers sur N » lus dans la page. Les résultats d'une recherche ne
  restent affichés que pour les mêmes mots (`motsDe`).

### Mesure après (même série, base « 3 ans » + 2 brouillons d'essai)

| Écran | Appels | Serveur p50 / p95 | Réponse |
|---|---|---|---|
| Atelier « Ordres » | brouillons + `/ordres?limite=50` (en parallèle) | 212 / 227 et 215 / 396 ms ; avec 1 brouillon (base d'origine) : 86 / 102 et 156 / 213 ms | 5 Ko + 61 Ko |
| Envoyer, saisie du bureau | `statut=valide&limite=2` + `statut=annule&limite=2` | 70 / 106 et 60 / 128 ms | 2,6 + 1,8 Ko |
| Retour | `statut=valide&limite=10` | 72 / 142 ms | 12 Ko |
| Retour, recherche « CRM 2 » | `statut=valide&q=…&limite=30` | 236 / 291 ms | 34 Ko |

Avant : 1,2 s et 3,15 Mo à chaque ouverture d'Ordres, d'Envoyer et de la saisie du bureau, 1,1 s
et 3 Mo pour Retour ; après : 0,06–0,22 s et quelques dizaines de Ko, **indépendants de
l'historique** (la page ne dépend que de `nb`). Les brouillons coûtent ~60 ms chacun (blocages
recalculés), comme avant : ils étaient déjà dans la liste entière.

### Preuve d'égalité (même base, réponses utiles comparées octet pour octet, JSON trié)

`preuve_ordres.py` (copie « 3 ans », 2 546 ordres dont 3 brouillons, un daté du 01/10 derrière
des validés) : **107 comparaisons, 0 écart** —
- « Ordres » : pour `nb` = 50, 100, … 2 550 (51 étapes) : les cartes (objets `OrdreResume`
  entiers), « montrés » et le total, liste entière triée par `trierOrdres` ↔ brouillons + page ;
- « Retour » : 20 étapes de 10 (10 à 200) et 9 recherches (`OF-2029`, `OF-2027-01`, `CRM 2`,
  `morocco`, `hors recette`, `FB`, `PES`, `L-2703`, `zzz`) × 3 étapes de 30 : cartes et total ;
- date du dernier ordre (2029-10-12) : 9 cas de `sauf` (aucun, chaque brouillon, chacun des
  quatre lus, le plus ancien ordre) ;
- aucune clé monétaire dans `OrdreResume` (rôle `alimentation`).

Gestes rejoués dans l'écran (copie, 375×812 puis 1440×900) : Ordres (3 brouillons en tête,
« 50 sur 2 546 », « charger les suivants » → 100 cartes, position gardée), Retour (« les 10 derniers
sur 2 445 », recherche `OF-2027-01` → « 30 sur 94 », « 64 autre(s) »), Envoyer au 05/10/2029 →
bandeau « Un ordre du 12/10/2029 est déjà validé… », Nouvelle sortie du bureau → Date `min`
2029-10-12. Plus aucun appel `/ordres/ouverts` sans filtre.

Essais : `lib/dernierOrdre.test.ts` (300 listes tirées, chaque `sauf` : même date), `Ordres.test.tsx`
(`premiersOrdres` = `trierOrdres(tous).slice(0, nb)` pour nb = 1…45 ; l'écran ne lit que
`?statut=brouillon`, `/ordres?limite=50` puis `100`), `Retour.test.tsx` (25 validés : 10 derniers,
« 10 sur 25 », suite, recherche au serveur, jamais `/ordres/ouverts`).

## 2. `PUT /inventaires/{id}/comptages` — corrigé (signature du cache)

### Fréquence et mesure avant

L'écran ne l'appelle **pas** à chaque ligne : les saisies restent locales jusqu'à « Enregistrer le
comptage » (lignes modifiées seulement), et « Valider » enregistre d'abord ce qui reste. Une
personne qui compte enregistre donc quelques fois par inventaire (par rayon), et **attend** à
chaque fois : `useEcriture` relit toutes les lectures ouvertes avant de rendre la main (fiche,
liste des inventaires, contexte du menu, notifications).

Inventaire tournant réaliste ouvert sur la copie (5 matières, Morocco : 46 puis 70 lots),
enregistrements par 5 lignes :

| Mesure | Avant |
|---|---|
| `PUT …/comptages` seul | p50 71 ms (le PUT relit le cache d'avant son écriture) |
| la fiche relue juste après | **p50 852 · p95 887 · max 911 ms** |
| **ce que la personne attend** (PUT puis fiche + liste + contexte en parallèle) | **p50 1 432 · p95 1 484 ms** (achats), 1 435 / 1 450 (direction) |
| chaque lecture seule juste après un comptage (froid / chaud) | contexte 902–1 013 / 13–22 ms ; liste 1 115–1 166 / 366–481 ; fiche 820–922 / 64–71 |

Le 2,26 s du stress (01/01/2027) est le même effet, sur une journée chargée.

### Cause (`cProfile`, PUT puis fiche relue, en mémoire)

Fiche relue 1 088 ms dont `donnees_moteur.charger` → `lire` **953 ms** (journal du stock 728 ms) :
le moteur entier est relu pour le seul CMUP (`couts_inventaire`). Il était relu parce que la
signature du cache contient `max(journal.id)`, et que le comptage écrit sa ligne de journal
« comptage ». Or un comptage n'écrit que les lignes de l'inventaire, sa version et cette ligne :
rien de ce que lisent le moteur (`Donnees` n'a pas d'inventaire), les contrôles, le Cockpit ou la
lecture du stock (`deriver`). Le contexte et la liste payaient la même relecture.

### Changement

`services/donnees_moteur.py` : `SANS_EFFET = (inventaire, "comptage")` ; la signature lit
`max(journal.id)` **hors** ces lignes (balayage arrière de la clé primaire : 0,09 ms).
`services/inventaires/comptage.py` écrit son action par cette constante. Tout autre geste — ouvrir,
lot trouvé, valider (mouvements), abandonner, ou une ligne « comptage » d'un autre objet — change
toujours la signature. Aucune route, aucun schéma, aucune révision Alembic.

### Mesure après (même série, même inventaire de 70 lots)

| Mesure | Avant | Après |
|---|---|---|
| fiche relue juste après le PUT | p50 852 · p95 887 | **p50 66 · p95 69** |
| attente « Enregistrer » (PUT + relectures) | p50 1 432 · p95 1 484 | **p50 494 · p95 575** (achats) ; 499 / 581 (direction) |
| profil : fiche relue | 1 088 ms (moteur 953) | 130 ms (pas de moteur) |
| dans l'écran (1440×900, direction, 1 ligne) | — | 594 ms : PUT 103, fiche 162, contexte 159, **liste 490** |

Ce qui reste dans l'attente est la liste des inventaires (≈ 0,4–0,5 s, toutes les lignes de tous
les inventaires pour leurs totaux) : sous la seconde, non touchée.

### Preuve d'égalité

Le même scénario rejoué sur deux copies identiques, code d'avant (`main`, 33a1451) et d'après :
ouverture d'un tournant (46 lots), 10 enregistrements par 5 lignes + une correction, recomptage
« à quatre yeux » par la direction des lignes à recompter, validation ; second tournant (16 lots)
ouvert, compté, lu par l'alimentation, validé ; puis les 80 fiches d'inventaire (direction, avec
valeurs), la liste, `/stock` (direction et alimentation), `/controles/soldes` : **103 réponses
JSON identiques** (`diff -r`), et les tables `mouvement` (38 320 lignes), `solde`, `inventaire`,
`inventaire_ligne`, `journal` **identiques** (`cmp`, 70 846 lignes). Écarts validés :
INV-2029-0019 −104,303 kg / −2 540,05 MAD (9 recomptés), INV-2029-0020 −54,313 kg / −1 544,56 MAD.

Essais : `tests/test_inventaire_comptage_leger.py` — un comptage puis un recomptage ne changent
pas la signature, la fiche se relit sans `donnees_moteur.lire` (interdit par monkeypatch) et
égale celle d'un moteur relu (échoue sur l'ancien code) ; ouvrir, lot trouvé, valider et une ligne
« comptage » d'un autre objet changent chacun la signature.

## 3. Ce qui n'a pas changé, et pourquoi

- La route 249 `/ordres/ouverts` elle-même (plafond 5 000, OpenAPI identique) : elle sert encore
  l'accueil de l'atelier (brouillons, sorties du jour) et les brouillons d'« Ordres ».
- Bureau « Nouveau retour des machines » (`NouveauRetour.tsx`) lit encore tous les validés
  (1,1 s, 3 Mo) : poste du bureau sur le réseau local, geste rare (les retours se font au
  téléphone), et son tableau cherche localement ; le passer en recherche au serveur est possible
  si Mohamed le souhaite.
- Liste des inventaires (`GET /inventaires`, ≈ 0,4 s, croît avec les inventaires) : relue après
  chaque enregistrement, sous la seconde.
