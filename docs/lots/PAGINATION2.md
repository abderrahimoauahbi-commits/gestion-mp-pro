# Lot PAGINATION2 — paginer les grandes listes : ce qui est fait, ce qui reste

Branche `lot-PAGINATION2`, sur `main`. Suite coordonnée du lot PAGINATION (qui avait livré
l'export en flux et laissé la pagination des quatre listes à planifier, `PAGINATION.md § 2`).
Objet (V4 § 6) : faire tenir à ×10/×30 les listes qui reconstruisaient tout l'historique à
chaque appel (`/ordres` 135, `/commandes` 152, `/receptions` 167, `/dossiers` 187), **sans
changer un seul chiffre au volume de service réel** (règle d'or).

## 1. Fait : pagination par curseur de `GET /receptions` (167), sur le modèle de `/operations`

`GET /receptions` passe de `list[ReceptionResume]` à **`PageReceptions = Page[ReceptionResume]`**,
par curseur, recherche et filtres poussés en SQL, à l'identique de ce que l'écran F4 calculait
sur la liste entière.

- **`services/receptions_liste.py` (nouveau)** : `filtrer(f)` pousse en SQL le statut, les dates,
  le fournisseur **et les filtres liés** (`origine` bon/hors, `facture` avec/sans, `qualite`
  refus/reserve/conforme — mêmes règles que l'écran, par `EXISTS`/sous-requête) ; `_texte_sql()`
  reproduit la recherche sans accents sur **tout** ce que l'écran lisait (n°, fournisseur, BL,
  facture, personnes, bons, lignes = référence/désignation/lot, **et** devise, motif
  d'annulation, statut libellé — l'union que l'écran faisait entre la recherche serveur et sa
  recherche locale). `lister(s, f, apres, limite)` = `COUNT` + curseur `id < apres` +
  `limite + 1`, ne construit le `resume` que pour la page ; `apercu(s, q)` donne les comptes par
  onglet (recherche seule, tous onglets) et les fournisseurs du filtre lié. `liste`/`detailler`
  (classeur 178, brouillons de « Ma journée ») y restent, **non paginés**.
- **`services/receptions_lecture.py`** : `FiltresReceptions` gagne `origine`/`facture`/`qualite` ;
  l'ancienne recherche Python (`_passe`, `_texte`, `liste`) est retirée (déplacée en SQL).
- **`api/receptions/`** : route 167 → `response_model=PageReceptions`, `PaginationDep`, curseur
  `encoder_curseur([id])` ; nouvelle route `GET /receptions/apercu` (167 bis) ; `routeur`
  accepte `origine`/`facture`/`qualite` ; `PageReceptions` (+ `pese_total`) et `ApercuReceptions`
  dans `schemas.py`.
- **Écran F4** (`pages/receptions/`) : la liste se branche sur `useListePaginee` + `DataTable
  serveur/total/chargerPlus` (modèle `pages/operations/Operations.tsx`). Les **comptes d'onglets**,
  le compte « tous onglets » et les **options du filtre fournisseur** viennent de
  `/receptions/apercu` ; le **pied de totaux** (kg pesés) vient de `pese_total` (lu par un appel
  `?limite=1`, comme `OngletPesees`) et suit la recherche et les filtres. Les filtres liés
  portent désormais des **codes** (`bon`, `avec`, `refus`, id du fournisseur) affichés par
  `libelleValeur` : mêmes libellés à l'écran, mêmes valeurs envoyées à la route **et** à l'export
  (178). Plus de double appel `/receptions?q=` ni de recherche recalculée au client.

Preuves : `tests/test_receptions_pagination.py` (nouveau — union des pages = liste entière, sans
doublon ni saut, ordre stable ; total et `pese_total` sur tout le filtre ; comptes par onglet =
aperçu ; filtres liés et recherche au serveur). Les essais existants de la liste
(`test_receptions_lectures.py`, `test_receptions_regles.py`) sont adaptés à `Page.elements`.
`Receptions.test.tsx` rend la forme paginée + l'aperçu.

### Parité et convention

- La passe de parité **n'itère pas** `GET /api/receptions` côté PRO (le dynamique compare la
  liste de Gestion MP à la **fiche** `/receptions/{id}` de PRO, pas à sa liste ; aucune passe
  statique/alimentation ne porte la liste 167). Le changement de forme (list → Page) est donc
  **invisible à `make parite`** : rien à traduire, « à corriger 0 » conservé. Le harnais sait
  déjà lire une route PRO paginée (`parite_api_passe._pages_pro`, `page_pro`/`champ_pro`) si une
  passe doit un jour comparer cette liste.
- **Convention** (déjà celle d'`/operations`, admise sans écart à la règle d'or) : pour une liste
  paginée au serveur, les options du filtre lié sont fixées côté serveur et n'affichent plus le
  `(n)` par option (le compte global reste exact : total et comptes d'onglets). La recherche sur
  les colonnes **numériques** (nombre de lignes, kg pesés) et la **date** affichée n'est plus
  reproduite (comme `/operations` ne cherche pas ses colonnes numériques) ; toute la recherche
  **texte** est conservée à l'identique.

## 2. Reste à faire : `/ordres` (135), `/commandes` (152), `/dossiers` (187)

> **Suite (lot PAGINATION3)** : `/ordres` (135) et `/dossiers` (187) sont **paginés** —
> voir `PAGINATION3.md`. `/commandes` (152) reste non paginé : sa recherche porte sur l'état de
> livraison **calculé par le moteur**, impossible à reproduire en SQL sans réécrire le calcul
> (`PAGINATION3.md § 3`).

Le patron de `receptions` se reprend tel quel (`filtrer` SQL + curseur + `apercu`), mais chacune
a un verrou spécifique, hors du périmètre tenable d'une seule passe sûre :

- **`/ordres` (135)** — l'**atelier F3** (téléphone) lit la liste **entière** des ordres ouverts
  (`pages/atelier/*`, `pages/sorties`, `pages/operations/NouveauRetour`) et la pagine lui-même ;
  il lui faut un accès **borné** « tous les ordres d'un statut » (ex. `?statut=valide&tout=1`
  plafonné, ou un endpoint dédié) avant de paginer 135, sinon on le casse. Le pied de Sorties F2
  somme `net`/`total` (chiffres du moteur `consommation`, par ordre) : agrégat serveur à ajouter.
  Recherche **plate** (comme receptions), donc SQL-reproductible.
- **`/commandes` (152)** — le filtre et l'onglet « en retard » se calculent **par bon** dans
  `resume()` (échéance ETA/promesse/délai vs reçu : moteur `suivi_livraison`), **non poussable en
  SQL** sans réécrire le calcul → compteur/agrégat dédié (ou colonne dérivée). Lu **hors** de son
  écran : `pages/receptions` (`useBons`), `pages/plan-achat/PiedPreparation`, et F1
  (`accueil/taches.ts`, `cockpit/aFaire.ts`) qui comptent retard/à-approuver sur **toute** la
  liste → leur donner les compteurs serveur. Les indicateurs F4 somment `montant_estime_mad` /
  `reste_estime_mad` par bon (agrégats serveur).
- **`/dossiers` (187)** — recherche **tolérante à la ponctuation** (`services.recherche.trouve`,
  « FA-2026/117 » = « FA-2026-117 »), à reproduire en SQL (compaction `regexp_replace`) ; le pied
  F5 somme `marchandise_mad`/`charges_mad`/`revient_mad`, qui sont le **coût de revient calculé
  par dossier** (`calcul.revient_dossier`) : agrégat O(N) à exposer, et la vue « non répartis »
  (`NonRepartis.tsx`) veut la **liste** des dossiers à charges non réparties (endpoint borné).

Recette commune pour chacune : (a) `filtrer` SQL + `_texte_sql` ; (b) `response_model=Page[...]`,
`PaginationDep`, curseur `(date desc, id desc)` ; (c) un `/<domaine>/apercu` (comptes d'onglets,
options de filtres liés, totaux par unité, compte « en retard »/« non répartis ») ; (d) brancher
F2/F4/F5 et les appelants (atelier, plan-achat, F1) sur `useListePaginee` + compteurs serveur ;
(e) adapter la passe de parité **seulement** si elle itère la liste côté PRO (celle de `commandes`
l'itère dans le dynamique : il faudra y lire `.elements`) ; (f) rejouer la charge V4.

## 3. Mesure (V4 § 6)

Au volume réel, `/receptions` ne régresse pas (mêmes chiffres, essais verts). Le gain à ×10/×30
tient à ce que la route ne construit plus que la page (≤ 500 `resume`) au lieu de tout
l'historique, et calcule total/comptes/pesé par agrégats SQL : voir
`backend/essais/resultat-charge.txt`, section pagination.

## 4. Fichiers du lot

| Fichier | Rôle |
|---|---|
| `backend/gestion_mp_pro/services/receptions_liste.py` | **nouveau** : filtre SQL, recherche SQL, `lister` (curseur), `apercu`, `liste`/`detailler` |
| `backend/gestion_mp_pro/services/receptions_lecture.py` | `FiltresReceptions` (+ filtres liés) ; recherche Python retirée |
| `backend/gestion_mp_pro/api/receptions/{routes,routeur,schemas}.py` | route 167 paginée, route 167 bis, schémas `PageReceptions`/`ApercuReceptions` |
| `backend/tests/test_receptions_pagination.py` | **nouveau** : pagination, agrégats, filtres, recherche |
| `frontend/src/pages/receptions/{Receptions,OngletReceptions,colonnesReceptions,donnees,types}.{ts,tsx}` | écran F4 branché sur la liste paginée + compteurs serveur |
