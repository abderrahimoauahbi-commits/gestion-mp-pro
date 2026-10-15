# Fiche d'ordre légère — la validation d'un ordre ne recharge plus le moteur entier (15/10/2026)

Demande de Mohamed : « alléger la validation d'ordre, si possible sans tracas ». Point de départ :
l'anomalie **A4** du stress « 3 ans » (docs/lots/STRESS-3-ANS.md).

## 1. Cause (profil `cProfile` sur une copie de la base « 3 ans », 38 266 écritures, 2 544 ordres)

`POST /ordres/{id}/valider` rend la fiche de l'ordre (`services/ordres/lecture.fiche`). La fiche
passe par `contexte(s, [o])`, qui appelait `consommation.consommations(s)` : **tout le moteur**
(`donnees_moteur.charger`, cache périmé par la validation elle-même) puis la consommation de
**tous** les ordres (`calcul.production.consommation_par_of`).

| Étape (fiche d'un ordre, cache froid = juste après une validation) | Temps |
|---|---|
| `donnees_moteur.lire` : journal (`chargeur.journal.journal`, 38 000 lignes traduites) | 450–590 ms |
| `donnees_moteur.lire` : le reste (ordres, métiers et pesées, bons, réceptions, dossiers…) | 250–300 ms |
| `consommation_par_of` sur 2 543 ordres | 160 ms |
| le reste de la fiche (lignes, lots, retours, blocages) | ~10 ms |
| **Total** | **0,8–1,1 s** (0,15 s à cache chaud : les 2 543 ordres restaient recalculés) |

Même cause pour `GET /ordres` (page de 50 : `contexte` sur la page → `consommations(s)`), et pour
la réponse de `POST /ordres/{id}/annuler`, `POST /ordres`, `PUT /ordres/{id}`.

## 2. Changement (le plus petit : un chargement ciblé par ordre, pas de nouveau cache)

- `services/chargeur/journal.journal(s, noms, ordres=None)` : avec `ordres`, seules les écritures
  de ces ordres **et celles qui en annulent une** (`contrepasse_id`), traduites par le même code,
  dans le même ordre (date d'effet, n°).
- `services/chargeur/production.ordres(s, noms, ids=None)` : avec `ids`, ces ordres seulement.
- `services/donnees_moteur.charger_ordres(s, ids)` : des `Donnees` **réduites** à ces ordres —
  catalogue, qualités, recettes et leur histoire, réglages (ce que `prevu_de` lit), leur journal,
  eux seuls s'ils sont validés. Sans cache (33 ms), rien d'autre dedans.
- `services/ordres/consommation.consommations_de(s, ordres)` : les mêmes chiffres que
  `consommations(s)` pour ces ordres (même `_ajustees` : taux de perte à la validation D-07,
  densités). `consommations(s)` est inchangé (bilan, aperçu des Sorties, route 143).
- `services/ordres/lecture.contexte` : jusqu'à `CIBLES_MAX = 300` ordres numérotés, lecture
  ciblée ; au-delà (liste entière de l'atelier, classeur), moteur entier en cache comme avant.
  Seuil mesuré : ciblé ≈ 30 ms + 0,3 ms/ordre (1 : 33 ms, 50 : 46, 200 : 79, 500 : 191,
  2 543 : 868) ; entier 852 ms froid, 144 ms chaud → croisement vers 350 ordres.

Aucune route, aucun schéma, aucun chiffre, aucune décision touchée ; OpenAPI identique
(`scripts/generer_types.sh --verifier` sur l'OpenAPI de la branche : types à jour).

## 3. Preuve d'égalité (base « 3 ans », copie `gestion_mp_pro_ordre_essai`, horloge au 13/10/2029)

- **Chaque** ordre numéroté (2 543) : `consommations_de(s, [o])[n]` == `consommations(s)[n]`
  (`dataclasses.asdict`, égalité stricte des flottants) : **0 écart** ; idem par paquets de 50.
- Journal réduit (`charger_ordres` sur les 2 543 ordres) : 36 116 écritures, **identiques** une à
  une au sous-ensemble du journal entier (37 912) portant un ordre ; ordres réduits identiques.
- Réponses JSON (schémas de l'API : `OrdreFiche`, `OrdreResume`, `PageOrdres`, `ApercuOrdres`,
  `ConsommationOrdre`) : fiche de 50 ordres (20 derniers, 20 répartis sur 3 ans, les annulés, le
  brouillon), 3 pages de 50 de `GET /ordres`, `GET /ordres/ouverts` (2 445 validés, brouillons),
  l'aperçu, la route 143 : 15 Mo de JSON **octet pour octet identiques** avant/après (`cmp`).
- Essais : `tests/test_ordres_fiche_legere.py` (5 essais : égalité ciblé/entier sur validé avec
  retour d'opération, repris avec retour sans document, hors recette, annulé ; la fiche et la
  page ne relisent pas le moteur après une validation — `donnees_moteur.lire` interdit par
  monkeypatch ; au-delà du seuil le moteur entier reprend ; journal réduit = sous-ensemble exact ;
  taux de perte à la validation sans prévu figé).

## 4. Temps avant / après (même machine, même base, 100 fiches des 100 derniers ordres validés)

| Mesure | Avant | Après |
|---|---|---|
| Fiche d'un ordre, cache froid (= la réponse de `POST valider`) | p50 811 ms · p95 864 · max 875 | **p50 33 ms · p95 56 · max 83** |
| Fiche d'un ordre, cache chaud | p50 151 · p95 198 | p50 33 · p95 55 |
| `GET /ordres` page de 50, cache froid | p50 888 · p95 922 | **p50 70 · p95 94** |
| `GET /ordres` page de 50, cache chaud | p50 201 · p95 248 | p50 83 · p95 111 |
| Aperçu des Sorties (moteur entier, inchangé) | 217 | 201 |
| `GET /ordres/ouverts?statut=valide` (2 445 ordres), chaud / froid | 810 / 1 388 | 788 / 1 387 (inchangé, voulu) |

La validation elle-même (écritures, verrous, journal d'audit : ~0,3 s dans le stress) n'est pas
touchée ; la réponse qui suivait passe de ~1 s à ~0,05 s, et ne croît plus avec les années.

## 5. Ce qui reste (décrit, non corrigé)

- **`GET /ordres/ouverts` sans filtre de date** (écrans atelier « Ordres », « Nouvelle sortie »
  via `useEmpechements`, « Retour des machines ») : 0,8 s à chaud, 1,4 s à froid à 3 ans. Ce
  n'est pas le moteur (au-delà du seuil il reste en cache, 0,15 s) : c'est le **volume** —
  2 445 ordres et 32 806 lignes chargés en objets ORM (0,5 s) puis lus un à un (0,3 s), pour
  que l'écran n'en affiche que les plus récents (`PAGE_ATELIER`, « charger les suivants ») ou n'en
  tire qu'une date (`dernierOrdre`). Correctif propre, hors « sans tracas » car il touche l'écran et
  l'API : un paramètre `limite` (défaut 5 000 inchangé) passé par les écrans, ou `/ordres` paginé ;
  `useEmpechements` n'a besoin que de la date du dernier ordre (une requête). À dix ans : ~3 s.
- Le reste de A5 (bilan, export des mouvements, comptages) : inchangé.
