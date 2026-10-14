# Audit du domaine STOCK / OPÉRATIONS / SORTIES-RETOURS / MONTAGE / ÉCRAN ATELIER (14/10/2026)

Branche `audit-stock` (depuis `main` @ 1443f33). Base d'essai : copie `pg_dump -Fc` de
`gestion_mp_pro` restaurée dans `gestion_mp_pro_stock_essai` (alembic 0008, = ma branche),
recalculs par un autre chemin (SQL + appel direct des deux moteurs). Aucune révision Alembic.

## Méthode et portée réelle
Activité réelle copiée : 9 mouvements, 7 lots, 8 soldes, 4 montages (28 étages, 4 métiers),
2 opérations (1 ouverture + 1 transfert), **0 ordre** (donc aucune SORTIE ni RETOUR_MACHINE réels
— ces règles vérifiées par le code, les deux moteurs et la suite d'essais, pas par la donnée).

## Constats

| # | Gravité | Classe | Objet | Preuve | Corrigé |
|---|---|---|---|---|---|
| 1 | — | CERTAIN-OK | Montage : bobines = mètres × bobines/mètre (remplissage **hors** bobines) ; poids = bobines × poids bobine × remplissage/100 ; largeur = Σ mètres | Recalcul SQL/main = `services/montage.peser` = `calcul/stock/machine.fils_en_machine` = `calculMontage.ts`, au gramme (ex. mat 61 : 2,1×320=672 bob → 672×3,1×0,88 = 1833,216 kg) | n/a |
| 2 | — | CERTAIN-OK | Soldes par (lot, magasin) = journal | `Σ quantité` SQL par (lot_id, magasin_id) = table `solde` à l'unité ; `controler_soldes` → conforme, 0 négatif, 8 lots | n/a |
| 3 | — | CERTAIN-OK | Fil monté compté dans global/disponible/projeté, jamais retiré | `etat_stock` : mat 61/51/27/41 ont net=0, machine>0 → disponible=machine, projeté inclut machine | n/a |
| 4 | — | CERTAIN-OK | Quarantaine en stock (global, valeur) mais hors disponible/projeté | `projete.py` : disponible = net − quarantaine + machine ; projeté idem ; invariant vérifié sur toutes les lignes | n/a |
| 5 | — | CERTAIN-OK | Entré − Sorti = Reste ; retour machine réduit le sorti | `calcul/lots._compter`, `services/lots.historique`, `services/tracabilite` : RETOUR_MACHINE réduit `sorti` | n/a |
| 6 | — | CERTAIN-OK | RÈGLE ABSOLUE : alimentation ne voit aucun prix (routes, écran, exports, documents) | Filtre générique `RouteSansPrix` sur les 27 routeurs (null à toute profondeur) ; essai de balayage de toutes les routes GET (alimentation + administrateur) ; exports passent `voit_prix` (ordres : aucune colonne monétaire ; feuille de comptage : kg seuls) ; aucun composant atelier ne lit un champ monétaire | n/a |
| 7 | — | CERTAIN-OK | « Stock des fils » (atelier) : par lot, magasin par magasin, kg par métier, sans prix ; fil seulement monté apparaît | `FilsTrouves.tsx` + `LotSolde` (quantité = total dont quarantaine, U9) ; 68 essais atelier verts | n/a |
| 8 | — | CERTAIN-OK | Stock d'ouverture en kg/bobines/palettes | `ChampsOuverture.tsx` réutilise `Quantite` (conversion → kg, `vers_kg`) ; prix toujours au kg (U1) ; ouverture = achats/direction | n/a |
| 9 | Très faible | PROBABLE | `calcul/lots.py:tracabilite` compte un RETOUR_PRODUCTION en **entrée** (ses champs `entrees`/`sorties` divergent de `stock_par_lot`/`historique`) | Non montré à l'utilisateur : la route 112 (`services/tracabilite`) **recalcule** entrées/sorties correctement et n'utilise de `tracer` que la liste des mouvements. Incohérence latente de code, pas d'effet écran | non |
| 10 | Très faible | QUESTION | `CarteLot` affiche la quarantaine à la fois comme ligne de magasin **et** comme badge « X en quarantaine » | `FilsTrouves.CarteLot` : le magasin Quarantaine est dans `magasins` et re-signalé par le badge | non |

## Essais
Aucune correction (rien de CERTAIN-faux). Suite verte sur base d'essai dédiée :
`test_stock`, `test_stock_lots`, `moteur/test_stock`, `moteur/test_lots`, `test_operations`,
`test_ordres(+annulation)`, `test_inventaires`, `test_metiers`, `test_scenario_montage_passe`,
`test_prix_masques`, `test_stock_concurrence`, `test_operations_concurrence` ; 68 essais atelier (vitest).

## Questions métier pour Mohamed
- **Q1 (double affichage quarantaine).** Dans « Stock des fils », un lot en quarantaine se voit
  deux fois : une ligne « Quarantaine : 50 kg » et un badge « 50 en quarantaine ». Garder les
  deux, ou n'afficher que le badge ?
- **Q2 (poids de bobine retenu).** Si une matière n'a été que *ouverte* ou *ajustée* (pas reçue)
  avec un poids de bobine saisi, le montage retient ce poids (lot le plus récent par date
  d'entrée). C'est bien l'intention, ou faut-il n'accepter que le poids d'un lot *reçu* ?
