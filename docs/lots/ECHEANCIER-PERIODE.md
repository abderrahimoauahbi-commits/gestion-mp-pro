# Lot ECHEANCIER-PERIODE — « Réglées » dit son plafond, et une période les rend toutes

Demande de Mohamed (15/10/2026) : la vue « Réglées » de l'échéancier (Analyse › Échéancier,
routes 228–230) ne montrait que les 300 règlements les plus récents **sans le dire** ; il veut
que l'écran et l'export le disent, et un choix de période (du / au, sur la date de règlement)
qui rend **toutes** les pièces réglées de la période, factures et frais.

## Ce qui existait

- `calcul/suivi.echeancier` : `reglees` triées par date de règlement décroissante, coupées à
  `REGLEES_AU_PLUS = 300` ; `du`/`au` ne bornaient que les échéances dues (par leur date).
- Le service appliquait ensuite la recherche et la nature **après** cette coupe : avec
  `nature=frais`, on voyait les frais parmi les 300 derniers règlements, pas les 300 derniers
  frais.
- `services.echeancier.ligne` (relecture après un règlement, route 229) cherchait la pièce dans
  ces 300 : régler une pièce à une date plus ancienne que les 300 derniers règlements rendait
  « Pièce introuvable » (404) après un règlement pourtant écrit.
- L'écran posait déjà « Du » / « Au » (« Échéances à partir de ce jour ») ; l'export suivait.

## Ce qui change

| Où | Quoi |
|---|---|
| `calcul/suivi.py` | `echeancier(…, reglees_au_plus=REGLEES_AU_PLUS)` ; `_reglees` : avec `du` ou `au`, les réglées sont bornées par leur **date de règlement** (bornes incluses), sans plafond ; sans période, les `reglees_au_plus` plus récentes (`None` : toutes). Les dues, l'échu, l'à-dater ne changent pas. |
| `services/echeancier.py` | `calculer(s, f, *, plafonner=True)` : le moteur rend toutes les réglées ; le service garde recherche et nature **puis** coupe aux 300 plus récentes (sans période seulement) ; la réponse porte `reglees_total` (avant la coupe) et `reglees_plafond` (300, ou nul avec une période). `ligne` relit sans plafond. |
| `api/suivi/schemas.py` | `Echeancier.reglees_total`, `Echeancier.reglees_plafond` (routes inchangées : matrice identique). |
| `exports/echeancier.py` | La feuille « Réglées » porte en titre `mention_reglees` : « Réglées : les 300 dernières sur 1 540. Pour toutes les voir, poser une période (du / au) : elle s'applique à la date de règlement. » / « Réglées : toutes (N). Au-delà de 300… » / « Réglées : toutes les pièces réglées du … au … (N, date de règlement). » |
| Écran `Echeancier.tsx` | Onglet « Réglées (les 300 dernières) » quand le plafond joue ; une `Note` (attention sans période au-delà de 300, info sinon) au-dessus du tableau, même phrase que l'export ; infobulles de Du / Au complétées (« vue Réglées : règlements à partir de ce jour » / « … jusqu'à ce jour inclus »). |
| Docs | API-PRO (228, 230), ECRANS-PRO (échéancier), aide.json → NOTICE (Mode d'emploi › Analyse › Échéancier). |

Rôle alimentation : toujours 403 (essai).

## Essais

- `tests/moteur/test_suivi.py::test_une_periode_rend_toutes_les_reglees_de_la_periode` :
  période sur `payee_le`, bornes incluses, frais compris, 306 > 300 sans plafond ; dues par
  leur échéance ; `reglees_au_plus=None`.
- `tests/test_echeancier.py::test_les_reglees_plafonnees_sans_periode_toutes_avec` (plafond
  simulé à 1 puis 2) : sans période, les 2 dernières + `reglees_total` 3 / `reglees_plafond` 2 ;
  avec période, toutes (facture et frais), plafond nul ; nature : les 2 dernières **factures** ;
  régler une pièce au-delà du plafond rend sa ligne (échouait avant : 404) ; classeur : titre de
  la feuille Réglées sans puis avec période, lignes qui suivent ; alimentation 403.
- Écran (`Analyse.test.tsx`) : onglet « Réglées (les 300 dernières) » et la phrase ; saisie de
  « Du » → `GET /echeancier?du=…` ; avec période : « toutes les pièces réglées du … au … (412,
  date de règlement) ».

## Vu sur la copie de la base « 3 ans » (1 540 règlements : 371 factures, 1 169 frais)

Serveur d'essai sur 8150, navigateur intégré à 1 440 × 900, compte direction :

- Sans période : note orange « Réglées : les 300 dernières sur 1 540. Pour toutes les voir,
  poser une période (Du / Au) : elle s'applique à la date de règlement. » au-dessus du tableau,
  onglet « Réglées (les 300 dernières) », compteur « 300 / 300 », lignes du 01/10/2029 au
  02/04/2029.
- Du 01/01/2027 au 31/12/2027 posés dans les champs : note bleue « Réglées : toutes les pièces
  réglées du 01/01/2027 au 31/12/2027 (356, date de règlement). », onglet « Réglées (356) »,
  compteur « 356 / 356 » — 356 = 80 factures + 276 frais en SQL. Les échéances dues passent à
  0 sur cette période (elles sont toutes en 2029 : comportement d'avant, inchangé).
- Par l'API : 3 ans entiers → 1 540 = SQL ; `nature=frais` → 1 169 = SQL ; un seul jour
  (01/02/2027) → 34 = SQL ; dues/échu/à dater identiques avec et sans période des réglées.
- Export : la feuille « Réglées » porte la mention, 300 lignes sans période, 356 sur 2027.
