# Lot UNITES-TITRAGE — les unités de titrage, un référentiel

Branche `lot-unites-titrage` (depuis main 4771263). Révision Alembic **0008** (réservée par le
coordinateur). Routes **255–257** (numéros pris à la suite de 254 : à confirmer par le
coordinateur si un autre lot les a pris entre-temps).

## La demande (Mohamed, 12 octobre 2026)
Les unités de titrage (Dtex, Deniers, Nm, Tex, Nec, lbs) étaient figées dans le code
(`calcul/classification.py` : `UNITES_TITRAGE`, `ECRITURE_UNITE`, la regex `_TITRAGE` ;
`ChampsValeur.tsx` : `UNITES_TITRAGE`) : il a fallu un développeur pour ajouter « lbs ». Mohamed
veut **un onglet pour ajouter lui-même une unité, sans intervention** (DECISIONS F29).

## Ce qui est fait
1. **Base** (révision 0008, `0008_unites_de_titrage.py`) : table `unite_titrage` (`id`, `code`
   VARCHAR(16) tel qu'écrit, `libelle`, `ordre`, `actif`, `version`) ; index unique
   `uq_unite_titrage_code` sur `lower(code)` ; CHECK `ck_unite_titrage_code_un_mot` (non vide,
   sans espace) et `ck_unite_titrage_ordre_positif`. Semée de Dtex, Deniers, Nm, Tex, Nec, lbs
   (ordre 10 à 60), **puis des unités déjà écrites sur des titrages** et absentes (un mot de
   lettres, deux au moins, « den » excepté ; l'écriture la plus employée) : la base en service
   garde toutes ses unités lisibles. `ObjetJournal` + `unite_titrage` (CHECK
   `ck_journal_objet_enum` remplacé). Retour arrière **refusé** si le journal cite une unité.
   Modèle `modeles/referentiels.UniteTitrage`.
2. **Service** `services/unites_titrage.py` : `actives(s)` (ce que lit la lecture des
   références), `lire`, `emploi`, `ajouter`, `modifier`, `supprimer`, `raison_de_garder`.
3. **API** (domaine classification, `api/classification/routes.py`, déclarées avant les routes
   `{liste}`) : route 57 porte `unites_titrage: [UniteFiche]` (ordre puis code, désactivées
   comprises) ; 255 `POST /classification/unites-titrage`, 256 `PUT …/{id}` (version, 409),
   257 `DELETE …/{id}?version=`. Droits : écriture D, A ; lecture par la route 57 (C, donc
   l'alimentation lit). `response_model`, `summary`, `responses` partout ; journal « ajout /
   modification / suppression unité de titrage ».
4. **Lecture des références** : `calcul.classification.decomposer(reference, nature, *,
   unites)` reçoit la liste (le moteur reste sans base). `lecture_unites(unites)` (`lru_cache`,
   clé = la liste) bâtit le motif : formes triées **de la plus longue à la plus courte**
   (« Deniers » avant « Den », « Nec » avant « Ne »), échappées, insensibles à la casse ;
   l'écriture rendue est celle de la liste (« LBS » → « lbs »). L'abréviation « den » → Deniers
   (`ABREVIATIONS_UNITE`) n'est lue que si Deniers est dans la liste ; les unités sous-entendues
   (« 20/2 » → Nm ; PP → Dtex ; PES → Deniers) ne sont posées que si elles sont actives.
   `services/classement.apercu` lit `unites_titrage.actives(s)` **à chaque appel** (une
   requête) : pas de cache en mémoire qu'un autre processus laisserait périmé.
5. **Écran** : Catalogue › Classification, vue **« Unités de titrage · N »** (après « Titrages »,
   `?liste=unites-titrage`) : `UnitesTitrage.tsx` (note, recherche, « Montrer les unités
   désactivées », « Ajouter une unité », colonnes Code · Libellé · Ordre · Titrages · Matières ·
   État, « Désactiver » confirmé, « Supprimer » grisé par `raison_garder`), `FenetreUnite.tsx`
   (ajout / modification, conflit de version gardé sur la fiche). Le champ « Unité » d'un titrage
   (`ChampsValeur.tsx`) lit `unites_titrage` de la route 57 (`unitesProposees` : actives + l'unité
   déjà posée, même désactivée) ; son aide les nomme et dit où les tenir.

## Choix
- **Renommer une unité employée : refusé** (409 `fiche_utilisee`, raison dite : « … son code ne
  se change pas. Ajouter l'unité « Nx », puis désactiver « Ne ». »). Propager le renommage
  réécrirait `titrage.unite` **et** les codes de titrage (« 20 Ne ») et les références déjà
  écrites, que la règle de la classification ne touche jamais. **La casse seule se corrige**
  (« NE » → « Ne ») : l'emploi se compte sans casse, rien ne se perd.
- **Supprimer** : seulement une unité qu'aucun titrage n'écrit (donc qu'aucune matière ne porte
  par son titrage) ; sinon 409 « … la désactiver plutôt que la supprimer. ».
- **Code** : lettres seules, 2 à 16 (la colonne `titrage.unite`) ; une lettre seule se
  confondrait avec le « x » de « 1750x2 », un « / » ou un espace ne se lirait pas dans une
  référence. « Den » est refusé : c'est l'abréviation de Deniers.
- **`titrage.unite` reste un texte** (pas de clé étrangère) : les titrages repris de Gestion MP
  ou créés par le classement gardent leur écriture ; l'emploi se compte par `lower(unite)`.
  Le serveur ne refuse pas un titrage dont l'unité n'est pas dans la liste (comportement
  inchangé : l'écran ne propose que la liste).
- **Bascule à six vues** : la règle « 2 à 5 vues, au-delà des onglets » (`Bascule.tsx`,
  ECRANS-PRO) passe à **2 à 6** — des onglets dans l'onglet Classification feraient deux rangées
  d'onglets, ce que la règle « jamais deux rangées » interdit ; la bascule passe à la ligne au
  téléphone (CSS existant).

## Essais
- Serveur : `tests/test_unites_titrage.py` (5) — semis des six unités et droits (alimentation
  lecture seule, 403 en écriture ; 404) ; « Ne » ajoutée lue par `decomposer('Coton 20 Ne')` et
  par l'aperçu du classement (route 76), journal ; casse (« LBS » refusé si « lbs » existe),
  code invalide, « Den » ; unité employée : suppression et renommage refusés, casse corrigée,
  désactivation avec avertissement, plus lue ni active mais gardée sur le titrage, unité libre
  supprimée ; 409 de version (PUT et DELETE). `tests/test_migrations_0008.py` (semis, unités
  déjà employées, unicité sans casse, retour arrière refusé puis permis).
  `tests/moteur/test_classification.py` : les unités viennent de l'appelant (ajout, longueur,
  abréviation, sous-entendue, liste vide, casse, cache).
- Écran : `pages/catalogue/UnitesTitrage.test.tsx` (4) — la vue liste les unités (désactivées
  cachées, « Supprimer » grisé par la raison), l'ajout (corps envoyé, l'unité rejoint la liste),
  le champ « Unité » d'un titrage propose l'unité ajoutée et pas la désactivée, l'unité posée
  reste proposée.
- `make verifier` vert (voir le rapport du lot) ; `make matrice` : trois lignes ajoutées
  (255–257 : D, A ok ; L, T 403) ; `make notice` régénérée.
- Parité : `decomposer` ne sert qu'au classement (routes 76–77), qu'aucune passe de
  `make parite` / `outils/comparer_avec_gestion_mp.py` ne compare ; avec les six unités semées,
  la lecture rend exactement ce que rendait la constante (essais du moteur inchangés). `make
  parite` n'a pas été lancé (il lit les bases `gestion_mp`, hors de ce lot).

## À savoir pour les lots suivants
- Toute lecture d'une référence passe `unites=unites_titrage.actives(s)` à `decomposer`.
- `tests/base_connue.SEMEES` compte `unite_titrage` (la base remise à neuf garde les six unités).
- MODELE-DONNEES : 73 tables (`outils/schema_contre_modele.py` lit désormais « Liste des N
  tables » quel que soit N).
- Écarts aux documents de conception (reportés ici) : Bascule 2 à 6 vues ; routes 255–257 ;
  `ObjetJournal` + `unite_titrage`.
