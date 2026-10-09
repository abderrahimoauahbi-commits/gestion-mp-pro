# Lot PAGINATION3 — paginer les trois dernières grandes listes : fait, et ce qui reste

Branche `lot-PAGINATION3`, sur `main`. Suite coordonnée des lots PAGINATION et PAGINATION2, qui
avaient paginé `/operations` (115) et `/receptions` (167) et laissé `/ordres` (135), `/commandes`
(152) et `/dossiers` (187) avec leur verrou documenté (`PAGINATION2.md § 2`). Objet (V4 § 6) :
faire tenir ces listes à ×10/×30 **sans changer un seul chiffre au volume de service réel** (règle
d'or : comptes par onglet, filtres liés, pied de totaux qui suit la recherche, recherche tous
onglets, filtre « en retard »/« à vérifier » — tous EXACTS après pagination).

**Livré : `/ordres` (135) et `/dossiers` (187).** `/commandes` (152) est **gardé**, non paginé : sa
recherche porte sur un libellé calculé par le moteur, impossible à reproduire en SQL sans réécrire
le calcul — paginer changerait en silence le résultat d'une recherche (§ 3).

## 1. Fait : pagination par curseur de `GET /ordres` (135)

`GET /ordres` passe de `list[OrdreResume]` à **`PageOrdres = Page[OrdreResume]`**, par curseur
`(date, n° d'entrée)`, filtres et recherche poussés en SQL (patron de `/operations`).

- **`services/ordres/liste.py` (nouveau)** : `filtrer(f)` pousse en SQL le statut, les dates, le
  métier, le magasin, la **qualité** (par `EXISTS`) et la **recherche** sans accents (`_texte_sql`
  reproduit à l'identique ce que l'écran cherchait : numéro, métier `code · nom`, magasin,
  commentaire, lots, matières, qualités). `lister(s, f, apres, limite)` = `COUNT` + curseur + `limite
  + 1`, ne construit le résumé (moteur + blocages) que pour la page. `toutes(s, f)` (classeur 144,
  non paginé) ; `ouverts(s, f, limite)` (accès **borné** « tous les ordres d'un statut », plafonné à
  5 000) ; `apercu(s, f)` (comptes par onglet sur la période, agrégats du moteur des indicateurs,
  brouillons bloqués, options des filtres liés). Les blocages (une requête par ordre) ne sont faits
  que pour la page et les brouillons de la période — c'est là le gain principal.
- **`services/ordres/lecture.py`** : garde `fiche`, `contexte`, `lire_un`, `FiltresOrdres` ;
  l'ancienne `lister`/`_texte` Python est retirée (déplacée en SQL dans `liste.py`).
- **`api/ordres/{routes,schemas}.py`** : route 135 → `PageOrdres` (`PaginationDep`,
  `encoder_curseur([date, id])`) ; routes neuves **248 `/ordres/apercu`** et **249
  `/ordres/ouverts`** ; schémas `PageOrdres`, `ApercuOrdres`, `OptionOrdres`. Le classeur 144 lit
  `service.toutes`.
- **Écrans** : **Sorties F2** (`pages/sorties/Sorties.tsx`) se branche sur `useListePaginee` +
  `DataTable serveur` ; comptes d'onglet, indicateurs (sorti net, revenu, écart), **pied** (Σ prévu
  et Σ net) et options des filtres (qualité, métier, magasin — par **id**, options de l'aperçu)
  viennent de `/ordres/apercu`. L'**atelier F3** (`pages/atelier/*`), **Sorties/NouveauRetour** et la
  **saisie** (`useOrdres`, `NouveauRetour`) lisent la liste bornée **`/ordres/ouverts`** (filtrée par
  statut) au lieu de toute la liste : l'atelier garde sa liste complète d'ordres ouverts (petite), et
  ne lit plus dix ans d'ordres.

Preuves : `tests/test_ordres_pagination.py` (union des pages = liste entière, ordre date puis n°,
sans doublon ; total ; comptes d'onglet = aperçu ; agrégats net/revenu/prévu/sorti exacts ; recherche
et filtres au serveur ; accès borné `ouverts`). Essais de liste adaptés à `Page.elements`
(`test_ordres_api`, `test_restes3`, `test_ordres_annulation`). `Sorties.test.tsx` rend la forme
paginée + l'aperçu ; essais de l'atelier branchés sur `/ordres/ouverts`.

## 2. Fait : pagination par curseur de `GET /dossiers` (187)

`GET /dossiers` passe de `list[DossierResume]` à **`PageDossiers = Page[DossierResume]`**, par
curseur `(date d'arrivée desc nulls last, id desc)`.

- **`services/importations/lecture.py`** : `filtrer(f)` pousse en SQL le statut, le **fournisseur de
  la facture** (comme l'écran : `Dossier.facture_id → Facture.fournisseur_id`) et la **recherche**.
  `_texte_sql` reproduit, par sous-requête `string_agg`, tout ce que l'écran cherchait : numéro,
  libellé, banque, commentaire, et, par ligne, réceptions, factures, **familles de fil** (code
  composition + libellé du type tronqué au «  ( » + code titrage, sinon référence — à l'identique de
  `socle.famille`) et fournisseurs. La recherche est **tolérante à la ponctuation**
  (`recherche.conditions_tolerantes`, nouvelle : « FA-2026/117 » trouve « FA-2026-117 »), portée en
  SQL par `compacter_sql` (`regexp_replace`). `lister(s, f, apres, limite)` = `COUNT` + curseur +
  `limite + 1`, résumé de la page seule. `apercu(s, f)` : comptes par statut, totaux (indicateurs et
  **pied** : poids, marchandise, charges, revient, décaissé), **dossiers aux frais non répartis**
  (vue « non répartis ») et fournisseurs du filtre lié. `detailler` (classeur 205) conservé.
- **Filtre « à vérifier »** : `parties.a_verifier` est un calcul par dossier (écart de facture,
  surcoût, cours éloignés…), **non poussable en SQL**. Quand `verifier=oui|non` est demandé, la liste
  est calculée puis **bornée** (rendue d'un coup — peu de dossiers concernés) ; sans ce filtre, c'est
  la pagination SQL par curseur. Comportement d'écran identique.
- **`api/importations/`** : route 187 → `PageDossiers` ; route neuve **250 `/dossiers/apercu`** ;
  `filtres_dossiers` gagne `verifier` ; schémas `PageDossiers`, `ApercuDossiers`, `ApercuNonReparti`,
  `ApercuFournisseurDossier` (noms distincts de `schemas_analyse.DossierNonReparti`).
- **Écran F5** (`pages/importations/`) : `Importations.tsx` lit `/dossiers/apercu` (indicateurs,
  comptes d'onglet, non répartis) ; `ListeDossiers.tsx` se branche sur `useListePaginee` +
  `DataTable serveur`, le **pied** et les options du filtre fournisseur venant de l'aperçu du périmètre
  de l'onglet. Le statut du dossier d'un lien collé se lit sur sa fiche ; l'ensemble borné des
  dossiers clos (`useClosIds`) sert à bloquer un second camion sur un dossier clos.

Preuves : `tests/test_dossiers_pagination.py`. En particulier **`test_recherche_sql_identique_a_l_ancienne`** :
pour tous les jetons des dossiers (et des variantes à la ponctuation près), l'ensemble rendu par la
recherche SQL est **exactement** celui de l'ancienne recherche Python (`recherche.trouve` sur les
mêmes champs) — garantie de non-régression de la recherche. Essais de liste adaptés à
`Page.elements` (`test_importations_couts`, `test_importations_defauts`) ; aperçu, totaux, non
répartis et filtres vérifiés ; `Importations.test.tsx`/`FicheDossier.test.tsx` rendent la forme
paginée.

### Écart aux documents (à reporter)

- Le filtre **fournisseur** de la liste des dossiers est désormais, au serveur comme à l'écran, celui
  de la **facture du dossier** (l'ancien `_retenu` prenait aussi les fournisseurs des lignes). Au
  volume réel, la facture d'un dossier couvre les fournisseurs de ses lignes : même résultat. Noté
  dans API-PRO (`fournisseur = celui de la facture`).

## 3. Non fait : `/commandes` (152) — pourquoi, et ce qu'il faudrait

Le patron (filtrer SQL + curseur + aperçu) s'applique à `/commandes`, et son verrou « en retard »
était prévu (compteur dédié + liste bornée des bons en retard, lecteurs hors écran sur compteurs).
**Mais** la recherche de la liste (`commandes_fiche._texte`) porte, entre autres champs texte, sur
`livraison_libelle` — l'état de livraison **calculé par le moteur** (`suivi_livraison` :
« En retard », « Reçu sous réserve », « Livré »… selon l'échéance ETA/promesse/délai et le reçu du
jour). Ce libellé n'est **pas une colonne** : il dépend de quantités reçues et de la date du jour, et
ne se reproduit pas en SQL sans réécrire le moteur (ce que la règle d'or interdit). Or paginer impose
de pousser **toute** la recherche en SQL : on changerait alors en silence le résultat d'une recherche
qui tape un état de livraison (« retard », « livré »…) — une régression de la recherche, contraire à
la règle d'or (« recherche tous onglets EXACTS », et PAGINATION2 : « toute la recherche texte est
conservée à l'identique »).

Chemins possibles pour un prochain lot, à **trancher avec le propriétaire** (changement de
comportement assumé) :

1. **Convention documentée** : sortir `livraison_libelle` de la recherche texte (comme PAGINATION2 a
   sorti les colonnes numériques et la date) — l'état de livraison reste accessible par l'onglet et le
   filtre « en retard », mais plus en tapant son libellé. Alors `/commandes` se pagine comme `/ordres`
   (recherche SQL sur les autres champs ; retard = compteur `/commandes/apercu` + liste bornée ;
   `useBons`/plan-achat/F1 sur `/commandes/ouverts` et compteurs).
2. **Colonne dérivée** maintenue (coût et complexité : réécrire le moteur de retard en base, recalculé
   à chaque réception et chaque jour) — déconseillé.

En l'état, `/commandes` reste `list[CommandeResume]`, non paginé. À ×30 c'est la dernière grande
liste non bornée (resultat-charge.txt, section pagination).

## 4. Mesure (V4 § 6)

Au volume réel, `/ordres` et `/dossiers` ne régressent pas (mêmes chiffres, essais verts). Le gain à
×30 tient à ce que la route ne construit plus que la page (≤ 500 résumés) au lieu de tout l'historique
— pour `/ordres`, surtout, les blocages (une requête par ordre) ne sont plus calculés que pour la page
et les brouillons de la période ; pour `/dossiers`, le coût de revient par dossier n'est plus assemblé
que pour la page, les sommes du pied/indicateurs étant un agrégat `O(N)` dédié (aperçu). Les comptes,
totaux et agrégats passent par `/<domaine>/apercu`. Détail dans `backend/essais/resultat-charge.txt`,
section pagination.

## 5. Parité

La passe de parité n'a **rien demandé** : `parite_api_passe._liste_ou_pages` traduit déjà
`Page[T] → liste` (curseur suivi), et les routes 135/187 sont comparées **par fiche**
(`parite_api_documents` : `fiche_pro="/api/ordres|dossiers/{id}"`, fiches inchangées). `make parite`
reste « à corriger 0 ». Les scripts d'essai qui itéraient ces listes (`verif_production`,
`verif_importations`, `scenario_e_atelier`) lisent désormais `["elements"]` (ou `/ordres/ouverts`).

## 6. Fichiers du lot

| Fichier | Rôle |
|---|---|
| `backend/gestion_mp_pro/services/ordres/liste.py` | **nouveau** : filtre SQL, recherche SQL, `lister` (curseur), `toutes`, `ouverts`, `apercu` |
| `backend/gestion_mp_pro/services/ordres/lecture.py` | `lister`/`_texte` Python retirés (déplacés en SQL) |
| `backend/gestion_mp_pro/api/ordres/{routes,schemas}.py` | routes 135 (paginée), 248, 249 ; schémas `PageOrdres`/`ApercuOrdres`/`OptionOrdres` |
| `backend/gestion_mp_pro/services/importations/lecture.py` | filtre + recherche SQL (ponctuation, familles), `lister` (curseur), `apercu`, `verifier` borné |
| `backend/gestion_mp_pro/services/recherche.py` | **ajout** : `compacter_sql`, `conditions_tolerantes` (recherche SQL tolérante à la ponctuation) |
| `backend/gestion_mp_pro/api/importations/{routes,routeur,schemas_fiche}.py` | route 187 (paginée), 250 ; filtre `verifier` ; schémas `PageDossiers`/`ApercuDossiers` |
| `backend/tests/test_{ordres,dossiers}_pagination.py` | **nouveaux** : pagination, agrégats, filtres, équivalence de recherche |
| `frontend/src/pages/sorties/{Sorties,donnees,IndicateursSorties}.{ts,tsx}` | écran Sorties branché sur la liste paginée + aperçu |
| `frontend/src/pages/atelier/*`, `pages/operations/NouveauRetour.tsx` | lecteurs sur `/ordres/ouverts` |
| `frontend/src/pages/importations/{Importations,ListeDossiers,donnees}.{ts,tsx}` | écran F5 branché sur la liste paginée + aperçu |

Fichiers partagés touchés (à signaler, §0.3) : `services/recherche.py` (ajouts purs, aucun effet sur
les fonctions existantes) ; `tests/matrice_droits.csv` régénérée (`make matrice`, routes 248/249/250) ;
`docs/API-PRO.md` (routes 135, 187 mises à jour ; 248, 249, 250 ajoutées).
