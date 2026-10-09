# Lot PAGINATION — tenir à très gros volume : ce qui est fait, ce qui reste

Branche `lot-PAGINATION`, sur `main`. Objet (V4 § 6) : faire tenir PRO à 5–10 ans d'historique en
ligne sans régresser au volume de service. V4 avait chiffré les dépassements à ×10/×30 : les
**grandes listes non paginées** (ordres 135, commandes 152, réceptions 167, dossiers 187) et les
**exports massifs** (surtout `/export/mouvements`).

## 1. Fait : l'export du journal du stock en flux (route 106)

`GET /api/export/mouvements` est passé **en flux**, mémoire bornée, contenu identique :

- `services/mouvements.py` : `tous_en_flux(s, f, avec_valeur)` rend les lignes **une à une**
  depuis un curseur (`yield_per`), au lieu de `tous(...)` qui bâtissait la liste entière.
  La valorisation lit son coût de ligne au passage (`_couts`/`_valoriser_une` ; le calcul des
  coûts est fait une seule fois). `tous` et `valoriser` existent toujours (inchangés d'effet).
- `exports/flux.py` (**nouveau fichier**) : `classeur_en_flux(titre, colonnes, lignes, voit_prix,
  prefixe)` écrit le classeur en `openpyxl` **write_only** (cellules écrites au fil de l'eau),
  l'enregistre dans un fichier temporaire, puis le rend par morceaux (`StreamingResponse`, le
  fichier effacé à la fin, même en cas de coupure). Conventions gardées : en-tête gras sur fond
  gris, volet figé, filtre automatique, vraies dates, formats des grandeurs, texte « dangereux »
  gardé en texte, et **aucun prix** pour qui ne les voit pas (`colonnes_permises`, barrière 4).
- `api/stock/routes.py` : la route 106 appelle `classeur_en_flux` (contrat inchangé : même
  chemin, mêmes filtres, même type xlsx en réponse → ni API-PRO ni parité ne changent).

Preuve : `tests/test_export_flux.py` (contenu identique à l'ancien classeur, prix masqués pour
l'alimentation, lignes rendues par un générateur). Les essais hérités du stock
(`test_stock.py::test_classeurs_des_mouvements_et_des_lots`, `…texte_dangereux`) passent sur le
nouveau chemin. Mesure dans `backend/essais/resultat-export-flux.txt` : à 60 000 lignes, pic
mémoire **337 Mo → 0,4 Mo** (~810× moindre), sortie identique.

**Limite dite au coordinateur** : le flux supprime la mémoire, pas le coût d'écriture du xlsx
(~1 900 lignes/s). Un export de **tout** l'historique à ×30 (313 000 lignes) reste ~2–3 min : le
seuil A9 de 3 s n'est pas tenable en xlsx quel que soit le rendu. La route accepte déjà des
filtres (`du`/`au`, matière, lot, magasin, type, document) : l'écran devrait **borner** l'export,
ou le passer en CSV pour « tout, dix ans ». Décision d'usage/format laissée au coordinateur.

## 2. NON fait : pagination des quatre grandes listes — pourquoi, et le dessin à suivre

Les quatre listes dépassent à ×30 parce qu'elles **reconstruisent tout l'historique à chaque
appel** (V4 § 6). Le modèle de pagination par curseur existe et est éprouvé : **route 115
`/operations`** (`services/operations/lecture.py`) le fait déjà — recherche poussée en SQL
(`_texte` en `string_agg`/sous-requêtes), filtres en SQL, `Page[T]` = COUNT + curseur
`(date, id) < apres` + `limite+1`, et `lire(s, page)` ne reconstruit que la page. C'est le patron
exact à reprendre pour 135/152/167/187 (dataclass `Page*`, `response_model=Page[...]`,
`PaginationDep`, `encoder_curseur`).

**Ce lot ne l'a pas livré** : ce n'est pas réalisable proprement dans son périmètre de fichiers
sans casser des usages essentiels ni toucher des écrans d'autres lots. À garder tel quel et à
planifier comme un changement **coordonné** (contrats figés + écrans + parité). Constats :

1. **Contrat de liste `list[T]` consommé hors des écrans de ce lot.** Passer une route à `Page[T]`
   (`{elements,total,suivant}`) casse tous les appelants qui attendent un tableau nu :
   - `/ordres` (135) : l'**atelier (F3)** le lit en entier (`pages/atelier/*` :
     `useLecture<OrdreResume[]>('/ordres')`, `empechements.ts`, `Retour.tsx`, `Ordres.tsx`), plus
     `pages/sorties`, `pages/operations/NouveauRetour`. L'atelier a besoin de la liste complète
     (filtrée `statut=valide`), pas d'une page. **Hors des fichiers de ce lot.**
   - `/commandes` (152) : lu comme tableau par **F4 réceptions** (`pages/receptions/donnees.ts
     useBons`) et par `pages/plan-achat/PiedPreparation`. Cross-écran.
   - `/dossiers` (187) : lu par son seul écran (F5 importations).
   - `/receptions` (167) : lu par son seul écran (F4).
2. **Les écrans F2/F4/F5 calculent côté client, sur la liste entière :** comptes par onglet dans
   les onglets (commandes, réceptions), options et comptes des **filtres liés**, **pied de
   totaux** qui suit la recherche (« Total des N dossiers affichés »), recherche **tous onglets**.
   La pagination serveur (page de 500, E1 décision 3) rend ces agrégats **faux au-delà de la
   première page**. Les garder demande des **compteurs/agrégats serveur** (compte par onglet,
   compte « en retard », totaux par unité, options de filtre) — endpoints neufs à ajouter, par
   écran.
3. **Filtre « en retard » des commandes** : calculé par bon (échéance ETA/promesse/délai, reçu vs
   commandé) dans `resume()` — pas poussable en SQL sans réécrire le calcul. Le Cockpit (F1), lui,
   **ne dépend pas** de la liste : il compte ses retards à part (`courriel_contenu.retards`), donc
   paginer `/commandes` ne le casse pas ; mais l'onglet « en retard » de l'écran, si.

Chemin recommandé (par domaine, coordonné) : (a) pousser recherche + filtres en SQL comme
`operations` ; (b) `response_model=Page[...]`, `PaginationDep`, curseur `(date desc, id desc)` ou
l'ordre métier actuel ; (c) ajouter les **compteurs serveur** dont l'écran a besoin (onglets,
retard, totaux par unité, options de filtre liées) ; (d) migrer les appelants tableau (atelier
compris) vers `useListePaginee`/`.elements` ou vers un compteur selon le besoin ; (e) mettre à
jour API-PRO, `make parite` (ces routes entrent dans la comparaison), les essais de liste, et
rejouer l'épreuve de charge V4 aux trois volumes. Pour `/ordres`, trancher d'abord l'usage
atelier (il lui faut la liste des ordres ouverts, pas dix ans d'ordres).

## 3. Fichiers du lot

| Fichier | Rôle |
|---|---|
| `backend/gestion_mp_pro/exports/flux.py` | **nouveau** : classeur en flux (write_only + StreamingResponse) |
| `backend/gestion_mp_pro/services/mouvements.py` | `tous_en_flux`, `_couts`, `_valoriser_une` (ajouts) |
| `backend/gestion_mp_pro/api/stock/routes.py` | route 106 rendue en flux |
| `backend/tests/test_export_flux.py` | **nouveau** : parité de contenu + rendu paresseux |
| `backend/essais/resultat-export-flux.txt` | **nouveau** : mesure mémoire avant/après |

Fichiers partagés touchés (à signaler, §0.3) : `services/mouvements.py` (domaine S4) et
`api/stock/routes.py` (S4) — ajouts pour l'export que le lot avait en charge ; aucune fonction
existante changée dans son effet. `exports/flux.py` est neuf et réutilisable par toute liste qui
passera au flux.
