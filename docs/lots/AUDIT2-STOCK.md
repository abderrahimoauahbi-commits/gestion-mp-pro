# Audit n° 2 — STOCK / OPÉRATIONS / SORTIES-RETOURS / MONTAGE / ÉCRAN ATELIER (14/10/2026)

Branche `audit2-stock` (depuis `main` @ 9b20443). Point de départ : `AUDIT-STOCK.md` (passage 1).
Bases d'essai : `gestion_mp_pro_stock2_essai` (suite pytest), `gestion_mp_pro_stock2b_essai`
(serveur d'essai sur 8150 + Vite 5197, vérification au téléphone 375 × 812). Aucune révision
Alembic : rien ne change au schéma, l'OpenAPI est inchangée (`scripts/generer_types.sh --verifier`
sur l'OpenAPI de la branche : « Types de l'API à jour »).

## Modifications

| # | Quoi | Pourquoi | Preuve | Risque |
|---|---|---|---|---|
| 1 | `calcul/lots.py:tracabilite` : un RETOUR_PRODUCTION **réduit le sorti** ; une écriture annulée et son annulation ne comptent pas ; un transfert non plus — comme `stock_par_lot` et la route 112 | Décision STOCK/ATELIER (constat 9 du passage 1 : les champs `entrees`/`sorties` du moteur divergeaient de la liste des lots) | `tests/moteur/test_lots.py::test_la_tracabilite_d_un_lot_et_d_un_ordre` : lot A entré 200, sorti 50 − 10 = 40 (avant : entré 230, sorti 70) ; `entrees − sorties` = stock du lot ; OF-2 a consommé 30 (l'écriture annulée 6/7 ne compte plus) | Nul à l'écran : la route 112 recalculait déjà ainsi. **Parité unitaire** : les 20 jeux figés portent les totaux de Gestion MP ; `tests/moteur/sorties_pro.py:tracabilite_comme_gestion_mp` ramène les totaux à la convention de Gestion MP, différence voulue nommée dans l'en-tête du module (aucun écart nouveau) |
| 2 | « Stock des fils » (`FilsTrouves.CarteLot`) : la quarantaine se dit **une fois** — la ligne du magasin « Quarantaine » porte le ton critique (`.critique`), le badge « X en quarantaine » ne reste que si aucune ligne de magasin ne la montre ; libellé unique par `libelleMagasin` (jamais « Quarantaine quarantaine ») | Décision STOCK/ATELIER (question Q1 du passage 1) | `Lots.test.tsx` « la quarantaine se dit une fois par lot » : lot partiel → une seule occurrence de « quarantaine », « Quarantaine 10,0 kg », pas de « en quarantaine » ; lot tout en quarantaine idem. Vu au téléphone (375 px) sur la base 2b : lot gris « Magasin principal 120 kg / Quarantaine 10,0 kg » (rouge), lot beige « Quarantaine 60,0 kg » | Faible : affichage seul |
| 3 | Origine du poids de bobine (`chargeur/referentiels.py:poids_bobine_mesures`) : le lot le plus récent est gardé **même ouvert ou ajusté** (inchangé) ; le mot dit désormais **comment le lot est entré** : « reçu », « ouvert », « ajusté », « revenu des machines », sinon « entré » — au lieu de « reçu » pour tout lot non sorti | Décision STOCK/ATELIER (Q2 du passage 1) ; le libellé « (reçu) » mentait pour un stock d'ouverture pesé | `test_metiers.py::test_poids_de_bobine_mesure` : lot d'ouverture pesé 2,3 kg → `source_poids` « lot … (ouvert) » (avant : « (reçu) ») ; au téléphone, carte du fil monté : « Poil acrylique beige · 2,5 kg / bobine · lot L-LRQ-4 (ouvert) » ; `source_poids` est bien affiché : atelier (`CarteFil`, `MonterEtage` via `origine_poids`), bureau (`OngletFils`), export des métiers (« Origine du poids ») | Faible : une requête de plus (première écriture positive de chaque lot), seulement s'il reste des matières sans lot sorti |
| 4 | Poids de bobine à l'écran : **2 décimales au plus** (`poidsBobine()` de `lib/format`) dans `CarteFil`, `OngletFils`, `AjoutFil` (au lieu de `nombre(…, 3)`) ; le « (catalogue X kg) » d'`OngletFils` aussi | ARCHITECTURE § formats : « Poids de bobine : jusqu'à 2 décimales sans zéros » ; la fiche du lot disait « 2,5 kg / bobine » et la carte du montage « 2,495 kg / bobine » pour la même bobine | Vu au téléphone : « 2,5 kg / bobine » dans la liste des fils à monter et sur la carte du fil ; 672 bobines × 2,4952 = « 1 677 kg » (le calcul garde le poids exact) | Nul |
| 5 | `deplacement.ts:lireDeplacement` : un magasin de départ choisi qui n'a plus de matière (tout déplacé, ou saisie gardée d'avant) **retombe sur le plus garni** | Trouvé par lecture : après « Tout ce qui est dans X » puis « Déplacer », `depuis` restait X (vidé) : disponible 0, sélecteur sur une valeur absente des choix, bouton grisé « Saisir la quantité » sans issue | `deplacement.test.ts` : `depuis: 999` → départ 1, disponible > 0 | Nul |

## Sonde de robustesse (serveur) — aucun 500

Deux sondes temporaires (supprimées) ont balayé les routes du domaine avec des valeurs limites :
ordres (lignes vides, quantité 1e9 / 1e-9, dates fausses / futures / 1999, lot 0 / inconnu /
d'un autre magasin, quarantaine, métier inconnu, lot deux fois, qualité deux fois, unités
bobine entamée / palette / inconnue, commentaire 301 car. / `\x0` , versions 0 / 99, ids `0`,
`-1`, `abc`, 10^20, `q` de 3 000 caractères / `%_'"\`, `limite` 0 / −1 / 10^6, curseurs bidon,
du > au, proposition m² 10^8 / qualité inconnue / dates), opérations (quantité 0 / négative /
1e9, unité `xyz` / bobine / palette / ml, devise `XXX` / vide, lot avec espace / vide / 80
caractères unicode, lot d'une autre matière, transfert même magasin / sans destination /
sans lot / négatif / trop, retours sans fournisseur / sans ordre, ajustement 0 / trop,
suppression deux fois), lots (`scan` vide / 5 000 car. / URL / id 10^20, `statut` xx, `non_nuls`
xx, PUT version 99 / 301 car.), stock, mouvements, traçabilité (sans paramètre, lot 0, lot +
ordre inconnu), étiquettes (`lots` vide / `abc` / `0` / `,,,` / 1 000 ids / 10^20), signalements
(texte vide / blancs / 501 car., urgence xx, matière 0), inventaires (date, magasin 0 /
inconnu, tolérance −1 / 10^9, critères 0 / bidon / Z, comptages ligne 0 / étrangère / négatif /
10^12 / bobine 0,5 / vide / ligne deux fois, lot trouvé sans numéro / avec espace / déjà
compté / magasin autre, abandon sans motif), métiers (étage 0 / 99 / −1, mètres −1 / 0 / 10^9 /
nan / abc, pourcentage 150 / −5 / 0, matière inconnue / inactive / deux fois, effet 10^12 /
nan / faux, montage étages vides / 99 / deux fois, laize 0, étages 0, code vide / blancs, droits
de l'alimentation sur PUT/DELETE métier).

Résultat : **0 réponse 500** ; chaque refus porte un message français et un code stable ; l'ordre
qui prend deux fois le même lot est **additionné** avant la vérification du stock (« 500 kg
seulement, 700 kg demandés ») et, s'il tient, ses deux lignes se regroupent dans les lots sortis ;
`devise` vide d'une ouverture vaut MAD ; `lot_id` l'emporte sur `lot_numero`.

## Vérifications

- Prix (règle absolue) : `test_prix_masques`, balayage `fuites()` des essais API, exports
  `operations` / `lots` / `mouvements?avec_valeur` / `metiers` lus par l'alimentation : aucune clé
  monétaire ; feuille de comptage en kg seuls ; l'export des inventaires est refusé (403) à
  l'alimentation, comme la modification d'un lot.
- `make verifier` : serveur (ruff, format, mypy strict, pytest 2 952 verts dont 5 sautés —
  `test_scenario_court` a échoué une fois pendant que trois audits tournaient ensemble (« Une
  restauration de sauvegarde est en cours », 503 de timing du serveur jetable), rejoué seul :
  vert), écran (prettier, eslint, stylelint, tsc, vitest), outils (`routes_ecran`,
  `verifier_heritage`) — relancé en entier après `git merge main`, voir le rapport.
- Parité unitaire (20 jeux) : verte, avec la différence voulue n° 1 nommée.

## Ce qui reste (non corrigé, hors CERTAIN/PROBABLE)

- Un identifiant hors `int64` dans l'URL (`/ordres/99999999999999999999`) rend 409
  `regle_de_la_base` « … Rien n'a été enregistré. » sur une lecture : vrai mais mal dit (socle,
  toutes les routes). Un caractère nul dans un commentaire : même 409 obscur (socle Pydantic).
- « Déplacer › Quel lot ? » charge tous les lots non nuls d'un coup dans un sélecteur (pas de
  pagination) : correct avec les volumes de l'usine, à surveiller au-delà de quelques milliers.
- Un métier dont on réduit le nombre d'étages garde ses fils au-delà du dernier étage (le bureau
  les montre « hors machine », ils pèsent toujours dans le stock sur les métiers) : comportement
  déjà prévu, pas une anomalie.
- Les comptages d'inventaire se saisissent et se lisent à 3 décimales (le gramme de la balance,
  échelle de la colonne `quantité`) ; la règle « kg ≤ 2 décimales » vaut pour les kilos affichés
  (`kg()`, `kgTelephone()`), pas pour une pesée saisie.

## Bases et serveurs d'essai

`gestion_mp_pro_stock2_essai` et `gestion_mp_pro_stock2b_essai` supprimées, serveur 8150 et Vite
5197 arrêtés, dossier `~/gestion-mp-pro-sauvegardes/gestion_mp_pro_stock2b_essai` (sauvegarde
quotidienne écrite par le serveur d'essai) supprimé. Note : un premier lancement de la semence
visuelle, par `conftest`, a créé deux matières d'essai dans `gestion_mp_pro_essai` (base d'essai
partagée, schéma recréé à chaque lancement de pytest) — sans effet.
