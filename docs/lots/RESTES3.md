# Lot RESTES3 — restes côté serveur : ce que les lots suivants doivent savoir

Branche `lot-RESTES3`. Lignes « serveur » et « docs » de `docs/lots/RESTES.md` traitées et
retirées. Ce fichier est écrit **tôt** (demande du coordinateur) : la section 1 est la liste
exacte des changements de forme de l'API, pour RESTES4 (écran), R2 (parité) et C1
(comparaison). `frontend/` n'est pas touché : **`make types` est à relancer** par le lot écran
après la fusion (`types.gen.ts` ne connaît pas les champs ci-dessous).

## 1. Changements de forme de l'API

### 1.1 Codes du stock (S3) — même valeur logique, autre forme

| Champ | Avant (Gestion MP) | Après (PRO) |
|---|---|---|
| `statut`, `statut_couverture` (lignes de stock 103/104, alertes du Cockpit 209, besoins 145, lignes du plan d'achat 149/150) | « ⚫ RUPTURE », « 🔴 CRITIQUE », « 🟠 URGENT », « 🟡 ATTENTION », « 🟢 OK », « ⚪ NON CONSOMMÉE » | `RUPTURE`, `CRITIQUE`, `URGENT`, `ATTENTION`, `OK`, `NON_CONSOMMEE` |
| `action` d'une ligne de stock (103/104 ; `null` pour l'alimentation) | « 📝 Créer BC - <fournisseur> » / « — » | `CREER_BC` / `AUCUNE` |
| `relance` d'une ligne du plan d'achat | « 🔴 CRITIQUE — REF (Fournisseur) — … » | « CRITIQUE — REF (Fournisseur) — … » (« NON CONSOMMÉE » en clair) |

Inchangés (hors de la ligne RESTES) : `tier` (« 🔥 TIER 1 »…), `risque`/`sourcing`
(« 🔴 MONO-SOURCE »), statut de livraison des bons, classement des fournisseurs.
`lib/statuts.ts › cleStock` accepte déjà les codes (`RUPTURE`… et `NON_CONSOMMEE` par
`NON_CONSOMM`) : **rien à changer à l'écran** ; les jeux d'essai de l'écran (`pages/*/essais/*.json`,
`plan-achat/donneesEssai.ts`) portent encore les émojis (lus par `cleStock`, sans effet).
Classeurs : statut écrit en clair (`calcul.constantes.LIBELLES_STATUT`).
**R2 / C1** : comparer par `calcul.constantes.LIBELLES_GESTION_MP` (code → libellé de Gestion
MP) ; la parité unitaire le fait par `tests/moteur/jeux_outils.comme_gestion_mp`.

### 1.2 Stock, lots, traçabilité (S4)

(complété au fil du lot)

## 2. Isolation des essais (D4, D5 → S0/S2)

- `tests/base_connue.py` : `photographier(c)` (les semences, une fois après la migration,
  `conftest.schema`) et `remettre(c)` : **toutes** les tables vidées sauf les comptes
  (utilisateurs, sessions, appareils, tentatives), semences et réglages réécrits à leur défaut.
  Dans une transaction annulée (monde de S1, `fabriques.stock.vider`,
  `fabriques.pilotage.usine`) ou validée (fixture **`base_neuve`** de `conftest.py`, pour un
  essai dont le code ouvre ses propres sessions : tâches de fond, clôture par l'API).
- `tests/modele_monde.batir(c)` commence par `remettre(c)` : `test_periode`, `test_modele`,
  `test_modele_contraintes` ne voient plus rien des autres essais (compteur `BC 2026`,
  `REC-2026-0001`, `INV-2026-0001`, brouillons comptés par la clôture).
- Contournements retirés : réceptions des essais datées du 3 août 2026 (`fabriques.receptions.JOUR`,
  avant 31/12/2025), inventaires validés du 30/09/2026 (`JOUR_DES_INVENTAIRES`), fixture
  `menage` (écrivait sans journal) supprimée de 17 modules.
- Ordre aléatoire : `pytest --melanger=GRAINE` (ou `GESTIONMPPRO_MELANGE=GRAINE`) mélange les
  modules puis les essais de chaque module (crochet de `conftest.py` ; ni `pytest-randomly` ni
  `pytest-random-order` ne sont dans les dépendances).
