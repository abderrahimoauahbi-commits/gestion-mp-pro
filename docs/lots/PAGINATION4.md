# Lot PAGINATION4 — paginer la dernière grande liste : GET /commandes (152)

Branche `lot-PAGINATION4`, sur `main`. Dernier des lots de pagination (PAGINATION, 2, 3) : il
pagine `/commandes` (152), la seule grande liste restée non bornée, gardée par PAGINATION3 § 3 à
cause de sa recherche sur l'état de livraison calculé par le moteur. Objet (V4 § 6) : faire tenir
`/commandes` à ×10/×30 **sans changer un seul chiffre au volume de service réel** (règle d'or :
comptes par onglet, filtre « à approuver », filtre « en retard », pied de totaux, filtres liés —
tous EXACTS après pagination).

## 1. Décision (option 1 de PAGINATION3 § 3) : convention de recherche

Le seul verrou de `/commandes` était que sa recherche libre portait sur **`livraison_libelle`** —
l'état de livraison calculé par le moteur (`suivi_livraison` : « en retard », « livré »,
« attendu »…), qui dépend des quantités reçues et de la date du jour, **non reproductible en SQL**
sans réécrire le moteur. Tranché par le coordinateur : on **sort de la recherche libre ce seul
champ**. Tout le RESTE de la recherche texte (n° de bon, fournisseur, pays, devise, statut libellé,
créateur, remarques, conteneur, navire, références **et désignations** des lignes) est conservé à
l'identique et poussé en SQL, comme `/receptions`. L'état de livraison reste accessible :

- en **colonne** de la liste (calculé pour la page affichée) ;
- par le **filtre « En retard seulement »** (`?filtre=retard`) ;
- par les **onglets** (brouillon, à approuver, envoyée, confirmée, soldées/annulées).

C'est le même compromis que `/operations` (colonnes numériques hors recherche) et que la date et
les colonnes numériques de `/receptions` (PAGINATION2). **Écart assumé** (à reporter) : le
**filtre lié « État de livraison »** (menu déroulant d'un état quelconque) de l'ancien écran
disparaît — il aurait exigé le même calcul moteur sur tout l'historique clos (O(N)), contraire au
bornage ×30 ; l'accès à l'état passe désormais par la colonne, l'onglet et « en retard ».
Documenté dans API-PRO (152, § 0), l'aide de l'écran (`aide.json` → NOTICE) et ici.

## 2. Fait : pagination par curseur de `GET /commandes` (152)

`GET /commandes` passe de `list[CommandeResume]` à **`PageCommandes = Page[CommandeResume]`**, par
curseur `(date du bon desc, n° d'entrée desc)`, filtres et recherche poussés en SQL (patron de
`/receptions` et `/ordres`).

- **`services/commandes_liste.py` (nouveau)** : `filtrer(f)` pousse en SQL l'onglet (statut, ou
  « clos » = soldées + annulées), le fournisseur, la **devise** (nouveau filtre lié SQL) et la
  recherche (`_texte_sql`, sans l'état de livraison). `lister(s, f, apres, limite)` = `COUNT` +
  curseur + `limite + 1`, ne construit le résumé (moteur + état de livraison) que pour la page.
  Le filtre **« en retard »** (`_en_retard`) : pré-filtre SQL grossier (`_candidats_retard` :
  bons partis, ni soldés ni annulés, échéance ETA/promesse/date+délai dépassée au retard toléré
  près — sur-ensemble des vrais retards, borné) puis affinage par le moteur ; la page est
  découpée par curseur sur cet ensemble borné. `ouverts(s)` (route 252) : tous les bons non clos,
  plafonnés. `detailler(s, f)` (classeur 166) y est repris, non paginé, même filtre que la liste.
- **`services/commandes_fiche.py`** : garde `resume`, `fiche`, `CommandeResume`, `FiltresCommandes`
  (+ champ **`devise`**), `BonDetaille`, `_retard` ; l'ancienne recherche Python (`_texte`) et les
  `liste`/`detailler` Python sont retirées (déplacées en SQL dans `commandes_liste`).
- **`api/commandes/`** : route 152 → `PageCommandes` (`PaginationDep`, `encoder_curseur([date,
  id])`) ; routes neuves **251 `/commandes/apercu`** et **252 `/commandes/ouverts`** ; `routeur`
  gagne `devise` ; schémas `PageCommandes`, `ApercuCommandes`, `IndicateursCommandes`,
  `TotalDevise`, `OptionFournisseur`. `routes_documents` (166) lit `commandes_liste.detailler`.

### L'aperçu (251) — ce que l'écran calculait sur la liste entière

`/commandes/apercu` sert, **sans envoyer toute la liste** : comptes par onglet (suivant la
recherche, les filtres liés et « en retard », tous onglets) ; `indicateurs` (ouverts, brouillons,
à approuver, engagé, partis, partis estimés, reste, à confirmer, en retard — sur **tous les bons
ouverts**, hors recherche et filtres, identiques à l'ancien `liste.indicateurs` de l'écran) ; le
**pied** de l'onglet (Σ kg, Σ MAD, Σ montant estimé **par devise**, jamais additionnées) ; les
options des filtres liés (fournisseurs, devises). **Chaque appel ne calcule que ce qu'il sert** :
l'écran l'appelle sans onglet pour les indicateurs et le défaut d'onglet (le pied est alors nul),
et avec onglet pour le pied de cet onglet (les indicateurs sont alors nuls) — un seul passage
borné par appel.

## 3. Écrans

- **Commandes F4** (`pages/commandes/`) : `Commandes.tsx` se branche sur `useListePaginee` +
  `DataTable serveur` ; les comptes d'onglets, les indicateurs (`IndicateursCommandes` prend
  désormais les nombres du serveur), le **pied** (`PiedServeur`) et les options des filtres
  (fournisseur, devise — par l'aperçu) viennent de `/commandes/apercu`. La recherche, les filtres
  liés et « En retard seulement » partent au serveur ; l'export (166) garde le même chemin propre,
  non paginé. `donnees.ts` : `useListeCommandes`, `useApercuCommandes`, `useCommandesOuvertes`,
  `useCommande`. `liste.ts` garde `ongletDe`, `enRetard`, `prixAConfirmer`, `estClos`,
  `LIBELLES_ONGLETS` (encore lus par Ma journée/Cockpit) ; `indicateurs`/`premierOnglet` client
  retirés (comptés au serveur). Le filtre lié « État de livraison » de `colonnesCommandes` est
  retiré (convention § 1).
- **Lecteurs hors écran** branchés sur `/commandes/ouverts` (borné) au lieu de toute la liste :
  `pages/receptions/donnees.ts` (`useBons` — la saisie des réceptions cherche les bons ouverts
  d'un fournisseur), `pages/accueil/donnees.ts` (`useCommandesToutes` — **Ma journée** et le
  **Cockpit** comptent retards, arrivées à 7 jours, à approuver, prix à confirmer, brouillons sur
  les bons ouverts). Leurs prédicats (`retardsDe`, `arriveesSemaine`, `aApprouver`,
  `prixAConfirmer`) ne retiennent que des bons non clos : l'ensemble borné « ouverts » donne
  exactement les mêmes listes et comptes (comme l'atelier lit `/ordres/ouverts`). Les bons clos,
  qui s'accumulent, ne sont plus lus hors de l'écran Commandes.

## 4. Parité

La passe de parité **n'a rien demandé** : `parite_api_passe._liste_ou_pages` traduit déjà
`Page[T] → liste` (curseur suivi), et la route 152 est comparée **par fiche**
(`parite_api_documents` : `fiche_pro="/api/commandes/{id}"`, fiche 153 inchangée). La passe
d'alimentation ne porte pas `/commandes` (routes D, A seulement). `make parite` reste
« à corriger 0 ». Les scripts d'essai qui itéraient la liste PRO lisent désormais `["elements"]`
(`test_restes3`, `essais/verif_achats`, `verif_pilotage`, `scenario_e_achats`) ; la lecture GMP
(`parite_dynamique`, `parite_dynamique_scene`) est inchangée (liste côté Gestion MP).

## 5. Mesure (V4 § 6)

Micro-mesure ×30 (9 000 bons), `backend/essais/resultat-charge.txt` § PAGINATION4 :
`GET /commandes` passe de **730 ms** (tous les résumés, O(N)) à **48 ms** (une page ≤ 500, borné,
~×15). L'aperçu (251) fait l'agrégat O(N) dédié, appelé une fois par changement de filtre (≈ 411 ms
sans onglet, 173–293 ms avec onglet, selon l'onglet), chaque appel ne calculant que ce qu'il sert.
Au volume de service réel, les chiffres sont identiques (essais verts) : aucune régression.

## 6. Essais

- `backend/tests/test_commandes_pagination.py` (nouveau) : union des pages = liste entière (mêmes
  id, ordre date puis n°, sans doublon) ; total ; comptes par onglet, « à approuver », « en
  retard » et indicateurs = aperçu ; pied (Σ kg, Σ MAD, Σ par devise) = somme sur l'onglet ;
  **équivalence de recherche** : pour chaque jeton des champs cherchés, la recherche SQL rend
  exactement le même ensemble que l'ancienne recherche Python SANS le libellé de livraison ; un mot
  qui n'est que dans l'état de livraison (« retard ») ne trouve plus rien, mais le filtre
  « en retard » le rend ; `ouverts` exclut les clos.
- Essais existants adaptés à `Page.elements` (`test_restes3`). Écran : `Commandes.test.tsx` rend la
  forme paginée + l'aperçu ; `liste.test.ts` allégé (indicateurs comptés au serveur) ; les faux
  serveurs de `Receptions`, `PlanAchat`, `accueil/essaisServeur` (Ma journée, Cockpit) servent
  `/commandes/ouverts` et `/commandes/apercu`.

## 7. Fichiers du lot

| Fichier | Rôle |
|---|---|
| `backend/gestion_mp_pro/services/commandes_liste.py` | **nouveau** : filtre+recherche SQL, `lister` (curseur), `_en_retard` (borné), `ouverts`, `detailler`, `apercu` |
| `backend/gestion_mp_pro/services/commandes_fiche.py` | `_texte`/`liste`/`detailler` Python retirés ; `FiltresCommandes` + `devise` |
| `backend/gestion_mp_pro/api/commandes/{routes,routeur,routes_documents,schemas}.py` | route 152 paginée, 251, 252 ; filtre `devise` ; schémas `PageCommandes`/`ApercuCommandes`/… |
| `backend/tests/test_commandes_pagination.py` | **nouveau** : pagination, agrégats, filtres, équivalence de recherche |
| `backend/tests/test_restes3.py` | liste PRO lue en `["elements"]` |
| `backend/essais/{verif_achats,verif_pilotage,scenario_e_achats}.py` | listes PRO lues en `["elements"]` |
| `frontend/src/pages/commandes/{Commandes,donnees,types,IndicateursCommandes,colonnesCommandes,liste}.{ts,tsx}` | écran F4 paginé + aperçu |
| `frontend/src/pages/{receptions/donnees.ts,accueil/donnees.ts,accueil/essaisServeur.ts}` | lecteurs sur `/commandes/ouverts` |

Fichiers partagés touchés (à signaler, §0.3) : `tests/matrice_droits.csv` régénérée (`make matrice`,
routes 251/252) ; `docs/API-PRO.md` (152 mise à jour ; 251, 252 ajoutées ; § 0 convention) ;
`frontend/src/aide.json` + `docs/NOTICE.md` régénéré (`make notice`) ; `frontend/src/lib/types.gen.ts`
régénéré (`make types`). Aucune colonne de modèle ni révision Alembic ajoutée.
