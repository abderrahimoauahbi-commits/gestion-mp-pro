# API de Gestion MP — partie A : référentiels, achats, réceptions, brouillons, importations

> Inventaire tiré du **code** de `~/gestion-mp` (serveur `gestion_mp/`), relu ligne à ligne.
> Périmètre : `api/referentiels.py` (39 routes), `api/referentiels_import.py` (8),
> `api/achats.py` (12), `api/receptions.py` (9), `api/brouillons.py` (2),
> `api/importations.py` (19), `api/analyse_import.py` (3), `api/exports_achats.py` (5) —
> **97 routes**, dont **10 exports Excel** et **1 document HTML imprimable**.
> Références `fichier:ligne` relatives à `gestion_mp/`.

## A.0 Conventions communes à toutes ces routes

### Préfixe et enregistrement

- Chaque module expose un `APIRouter` ; `main.py:131-134` les inclut tous avec `prefix="/api"`,
  dans l'ordre : comptes, **referentiels**, stock, **achats**, **receptions**, production,
  production_plan, operations, inventaires, exports, **exports_achats**, exports_analyse,
  **brouillons**, **importations**, **referentiels_import**, **analyse_import**, suivi, pilotage.
  L'ordre compte quand deux routes se recouvrent (ex. `GET /api/postes-frais` de
  `referentiels` et `GET /api/postes-frais/complet` de `referentiels_import`).
- Tags OpenAPI : « Référentiels », « Postes de frais et codes douaniers », « Achats »,
  « Réceptions », « Brouillons », « Importations », « Coût de revient », « Exports achats ».
  OpenAPI servi sur `/api/openapi.json`, documentation sur `/api/docs` (`main.py:126-129`).

### Authentification et droits (`securite.py`)

| Dépendance | Définition | Qui passe | Refus |
|---|---|---|---|
| `acteur` | `securite.py:92-101` | toute personne connectée, compte actif | 401 « Connectez-vous pour continuer. » (pas de cookie `gestion_mp_session`, session inconnue ou expirée) ; 401 « Ce compte n'est plus actif. » |
| `DIRECTION` = `droit()` | `securite.py:119` | direction seule | 403 « Cette action est réservée à : la direction. » |
| `ACHATS` = `droit(ACHATS)` | `securite.py:120` | achats **et direction** | 403 « Cette action est réservée à : responsable achats. » |
| `ALIMENTATION` = `droit(ALIMENTATION)` | `securite.py:121` | alimentation **et direction** | 403 « Cette action est réservée à : responsable alimentation machines. » |
| `STOCK` = `droit(ACHATS, ALIMENTATION)` | `securite.py:122` | les trois rôles | 403 « Cette action est réservée à : responsable achats, responsable alimentation machines. » |
| `LECTURE` = `droit(*TOUS)` | `securite.py:118` | les trois rôles | (non utilisée dans le périmètre A : les lectures « tout rôle » y passent par `acteur`) |

- **La direction passe partout** (`securite.py:108`). Les libellés de rôle viennent de
  `modeles.py:45-49` : direction « Direction », achats « Responsable achats », alimentation
  « Responsable alimentation machines » (mis en minuscules dans le message).
- Dans les tableaux ci-dessous, « **tout rôle** » = `acteur` (direction, achats, alimentation).
  « **Achats** » = achats + direction. « **Direction** » = direction seule. « **Alimentation** »
  = alimentation + direction.
- Toute dépendance de droit passe d'abord par `acteur` : sans session, c'est **401** avant le 403.

### Protection CSRF et en-têtes (`main.py:139-161`)

- Toute requête **non GET/HEAD/OPTIONS** sous `/api/` (hors `/api/connexion`,
  `/api/installation`, `/api/deconnexion`) doit porter l'en-tête **`X-Gestion-MP: 1`**, sinon
  **403** `{"detail": "Requête refusée : elle ne vient pas de l'écran de Gestion MP."}` — avant
  tout contrôle de droits. S'applique donc à **tous les POST/PUT/DELETE** de ce document.
- Réponses `/api/` : `Cache-Control: no-store`, `X-Heure-Serveur: AAAA-MM-JJTHH:MM:SS` (heure du
  serveur), plus `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: same-origin`.

### Erreurs

- `erreur(message, code=422)` (`securite.py:28-29`) → `HTTPException(code, message)` ; corps
  JSON `{"detail": "<message>"}`. **Sans code explicite, un refus métier est un 422.**
- Validation Pydantic (types, `Field`, `pattern`, validateurs) → **422**, corps
  `{"detail": "champ : message ; champ : message"}` en français : traduction par
  remplacements (`main.py:164-187`) — « Field required » → « à renseigner », « should be
  greater than or equal to » → « doit être au moins », « should be less than or equal to » →
  « doit être au plus », « should have at least » → « trop court : au moins », « should have at
  most » → « trop long : au plus », etc. Le nom du champ est le chemin `loc` sans `body`/`query`/`path`
  (ex. `lignes.0.quantite : doit être supérieur à 0`). Les messages des `field_validator` sont
  préfixés « Value error, » par Pydantic.
- `analyse_import.py` lève directement `HTTPException(400|404, …)` (pas `erreur`) : ses refus sont
  des **400**, pas des 422.
- `PUT /api/metiers/{mid}/etages/{etage}` renvoie **404** pour un étage hors du métier.

### Journal d'audit

`journal(s, u, action, objet, objet_id, detail)` (`securite.py:159-176`) ajoute une ligne
`Journal(utilisateur=nom, role, action, objet, objet_id, detail[:2000])`, horodatée par la base.
Chaque route d'écriture ci-dessous indique **action / objet / détail** écrits. Le journal est
aussi **lu** comme donnée métier : dernier montage d'un métier (`action="montage"`), renvoi
d'un bon par la direction, origine d'un solde de commande, motif d'annulation de réception,
versions du plan (`action="plan de production"`).

### Effet de bord implicite : versions de recette

Un écouteur SQLAlchemy global (`api/suivi.py:441-476`) : à **chaque commit** d'une session
qui a créé/modifié/supprimé une `Recette` ou un `QualitePoids` (ou modifié la collection
`poids` d'une `Qualite`), une ligne `RecetteVersion(qualite_id, par=<auteur de la dernière
ligne de journal ajoutée>, contenu=JSON [{reference, role, pourcentage}], poids=JSON {rôle: kg/m²})`
est ajoutée. Routes concernées ici : `POST/PUT /qualites`, `PUT /qualites/{qid}/recette`,
`POST /qualites/{qid}/versions/{vid}/restaurer`, `DELETE /classification/roles/{code}`
(poids supprimés), `DELETE /qualites/{qid}` (qualité supprimée → ignorée).
La lecture des versions est `GET /api/qualites/{qid}/versions` (dans `suivi.py`, partie B).

### Concurrence

- **Champ `version`** (matières) : `PUT /articles/{aid}` refuse 409 si `version` lu ≠ actuel.
- **Empreinte** (`referentiels.py:48-59`) : condensé SHA-1 (16 premiers caractères hex) de
  `json.dumps(parties, sort_keys=True, default=str, ensure_ascii=False)`. Renvoyée par les
  lectures (fournisseur, qualité, métier, fils, étages) ; si une écriture la renvoie et qu'elle
  diffère de l'actuelle → **409** « {Qui} a été modifié(e) entre-temps sur un autre poste :
  rechargez pour repartir de sa dernière version, puis refaites la modification. » (`{Qui}` :
  « Ce fournisseur », « Cette qualité », « Ce métier », « Le montage de ce métier »,
  « L'étage N »). Empreinte absente ou vide → pas de contrôle.
- Verrous de ligne `SELECT … FOR UPDATE` sur fournisseur, matière, qualité, métier, commande,
  réception, dossier, poste de frais, code douanier ; compteurs de numérotation sous verrou
  (`securite.py:179-197`).

### Numérotation (`securite.py:179-197`)

`numero(s, serie, jour, largeur=4)` : compteur `(serie, année de la pièce)`, verrouillé.
Format `SERIE-AAAA-NNNN` (ex. `BC-2026-0001`, `REC-2026-0012`, `LOT-2026-0042`) ; série `DOS` :
`NN/AA` (ex. `07/26`). Séries utilisées ici : **BC** (bon de commande, à l'envoi/approbation),
**REC** (réception, à la validation), **LOT** (lot interne), **DOS** (dossier d'importation).

### Dates

`date_permise(s, jour)` (`securite.py:210-226`) refuse (422) : avant 2000 « Date trop ancienne
(JJ/MM/AAAA) : vérifier l'année. » ; après aujourd'hui « Date dans le futur (JJ/MM/AAAA) : un
mouvement se saisit le jour où il a lieu. » ; à ou avant la clôture (réglage `date_cloture`)
« La période jusqu'au JJ/MM/AAAA est close : rien ne s'y écrit plus. Dater après la clôture,
ou demander à la direction de la rouvrir. »

`cout_hors_periode_close(s, dossier, geste, entrees_en_plus)` (`securite.py:235-276`) : refuse
**409** tout geste qui change le coût d'une marchandise **entrée** (date de réception, ou
`Lot.entre_le` pour une ligne saisie à la main) à ou avant la clôture : « La marchandise du
dossier {numéro} | rattachée est entrée le JJ/MM/AAAA, dans la période close jusqu'au
JJ/MM/AAAA : son coût a été rendu avec le mois et ne change plus ({geste} refusé). Pour
corriger ce mois, la direction rouvre la période (Réglages › Période close jusqu'au — c'est
tracé), on saisit, puis elle la referme. »

### Masquage des prix pour l'alimentation

`_sans_prix(qui)` (`referentiels.py:539-541`) vrai si le rôle est `alimentation` ; appliqué à la
main, route par route (pas de filtre générique) :

| Route | Champs mis à `null` pour l'alimentation |
|---|---|
| `GET /api/articles` | `prix`, `prix_kg` (restent : `devise`, `unite_prix`, `densite`…) |
| `GET /api/qualites` | qualité : `cout_m2_mad` ; chaque ligne de recette : `prix_kg`, `prix`, `unite_prix`, `cout_m2_mad` (restent `devise`, `kg_m2`, `densite`) |
| `GET /api/metiers` | métier : `valeur_mad` ; chaque fil : `valeur_mad` (le coût moyen n'est même pas calculé) |

Toutes les autres routes du périmètre qui exposent un prix ou un montant (commandes,
réceptions, factures, dossiers, analyses, **tous les exports Excel**, bon imprimable) sont
réservées **Achats** (donc refusées 403 à l'alimentation) — c'est ainsi que les prix sont
protégés. Le bon de commande (HTML et Excel) ne porte de toute façon **aucun prix**.

### Formats Excel communs (`api/exports.py:34-119`)

- Type MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, réponse
  `StreamingResponse` avec `Content-Disposition: attachment; filename="<nom>"` ; le nom est
  assaini : tout caractère hors `[A-Za-z0-9._-]` devient `-` (`exports.py:107-113`).
- Formats de nombre : `KG = "#,##0.0"`, `ENTIER = "#,##0"`, `PRIX = "#,##0.000"`,
  `MONTANT = "#,##0.00"`, `POURCENT = "0.0%"` (`exports.py:38-42`).
- `_feuille(classeur, titre, colonnes, lignes, entete=…)` (`exports.py:71-104`) : nom de
  feuille = titre sans `[]:*?/\`, tronqué à 31 caractères ; lignes de titre éventuelles (1re
  cellule en gras) puis une ligne vide ; **ligne d'en-tête** en gras, fond `#E8ECF3`, trait bas
  fin `#B8C0CC`, retour à la ligne ; format numérique appliqué aux seules cellules
  numériques de chaque colonne ; **largeur** de colonne = min(50, max(0,9 × longueur du
  titre, longueur max des 300 premières valeurs, 8) + 2) ; **volets figés** sous l'en-tête
  (et après la 1re colonne si plus de 4 colonnes) ; **filtre automatique** sur l'en-tête s'il
  y a des lignes.
- Sécurité : caractères de contrôle retirés ; une chaîne qui commence par `=` est forcée en
  texte (jamais une formule) (`exports.py:56-68`).
- Dates : dans `exports_achats.py`, les colonnes date reçoivent de vraies dates Excel au format
  `DD/MM/YYYY` (`exports_achats.py:65-78`) ; ailleurs (dossiers, coût de revient), les dates
  sont des **textes ISO** `AAAA-MM-JJ`.

## A.1 Récapitulatif des 97 routes

| # | Méthode | Chemin | Rôles | Fonction (fichier:ligne) | Sens |
|---|---|---|---|---|---|
| 1 | GET | `/api/classification` | tout rôle | `classification_complete` referentiels.py:83 | Les 4 listes de classification + les rôles de nomenclature, avec leurs comptes d'usage |
| 2 | POST | `/api/classification/roles` | Direction | `ajouter_role` referentiels.py:122 | Ajouter un rôle de nomenclature |
| 3 | PUT | `/api/classification/roles/{code}` | Direction | `modifier_role` referentiels.py:135 | Renommer / régler un rôle |
| 4 | DELETE | `/api/classification/roles/{code}` | Direction | `supprimer_role` referentiels.py:165 | Supprimer un rôle inutilisé |
| 5 | POST | `/api/classification/{nom}` | Achats | `ajouter_valeur` referentiels.py:201 | Ajouter une composition / un type de fil / un titrage / une couleur |
| 6 | PUT | `/api/classification/{nom}/{code}` | Achats | `modifier_valeur` referentiels.py:218 | Modifier (et renommer) une valeur |
| 7 | DELETE | `/api/classification/{nom}/{code}` | Achats | `supprimer_valeur` referentiels.py:237 | Supprimer une valeur non portée |
| 8 | GET | `/api/fournisseurs` | tout rôle | `fournisseurs` referentiels.py:344 | Fiches fournisseurs + comptes et délai mesuré |
| 9 | POST | `/api/fournisseurs` | Achats | `creer_fournisseur` referentiels.py:368 | Créer un fournisseur |
| 10 | PUT | `/api/fournisseurs/{fid}` | Achats | `modifier_fournisseur` referentiels.py:381 | Modifier une fiche (empreinte) |
| 11 | DELETE | `/api/fournisseurs/{fid}` | Achats | `supprimer_fournisseur` referentiels.py:399 | Supprimer un fournisseur sans historique |
| 12 | GET | `/api/articles` | tout rôle (prix masqués alimentation) | `articles` referentiels.py:544 | Catalogue entier des matières, stock compris |
| 13 | POST | `/api/articles` | Achats | `creer_article` referentiels.py:607 | Créer une matière |
| 14 | PUT | `/api/articles/{aid}` | Achats | `modifier_article` referentiels.py:623 | Modifier une matière (version) |
| 15 | DELETE | `/api/articles/{aid}` | Achats | `supprimer_article` referentiels.py:656 | Supprimer une matière sans trace |
| 16 | POST | `/api/catalogue/classer?appliquer=` | Achats | `classer_catalogue` referentiels.py:680 | Déduire la classification depuis les références (aperçu ou application) |
| 17 | POST | `/api/articles/composer` | tout rôle | `composer` referentiels.py:744 | Composer une référence à partir de ses parties (sans écrire) |
| 18 | GET | `/api/qualites` | tout rôle (prix masqués alimentation) | `qualites` referentiels.py:783 | Qualités, poids, plan, recette calculée, contrôle |
| 19 | GET | `/api/qualites/facteurs-cout` | Achats | `facteurs_cout` referentiels.py:827 | Perte et cours pour recalculer un coût au m² à l'écran |
| 20 | POST | `/api/qualites` | Direction | `creer_qualite` referentiels.py:846 | Créer une qualité |
| 21 | PUT | `/api/qualites/{qid}` | Direction | `modifier_qualite` referentiels.py:875 | Modifier code/nom/actif/poids d'une qualité |
| 22 | DELETE | `/api/qualites/{qid}` | Direction | `supprimer_qualite` referentiels.py:910 | Supprimer une qualité jamais fabriquée |
| 23 | PUT | `/api/qualites/{qid}/recette?empreinte=&motif=` | Direction | `ecrire_recette` referentiels.py:933 | Remplacer la recette |
| 24 | POST | `/api/qualites/{qid}/versions/{vid}/restaurer?motif=&empreinte=` | Direction | `restaurer_version` referentiels.py:987 | Revenir à une version de recette (parts + poids) |
| 25 | PUT | `/api/qualites/{qid}/plan` | Direction | `ecrire_plan` referentiels.py:1034 | Base mensuelle et saisonnalité d'une qualité |
| 26 | GET | `/api/magasins` | tout rôle | `magasins` referentiels.py:1060 | Magasins et kilos détenus |
| 27 | POST | `/api/magasins` | Direction | `creer_magasin` referentiels.py:1069 | Créer un magasin |
| 28 | PUT | `/api/magasins/{gid}` | Direction | `modifier_magasin` referentiels.py:1083 | Modifier un magasin |
| 29 | GET | `/api/metiers` | tout rôle (valeur masquée alimentation) | `metiers` referentiels.py:1198 | Métiers à tisser, fils montés étage par étage, poids et valeur |
| 30 | GET | `/api/montage/references` | tout rôle | `montage_references` referentiels.py:1262 | Par matière au poids : poids de bobine compté, sorti récent, déjà monté |
| 31 | POST | `/api/metiers` | Direction | `creer_metier` referentiels.py:1284 | Créer un métier |
| 32 | PUT | `/api/metiers/{mid}` | Direction | `modifier_metier` referentiels.py:1297 | Régler un métier (empreinte) |
| 33 | DELETE | `/api/metiers/{mid}` | Direction | `supprimer_metier` referentiels.py:1325 | Supprimer un métier vide et sans ordre |
| 34 | PUT | `/api/metiers/{mid}/fils?empreinte=` | Alimentation | `monter_fils` referentiels.py:1397 | Remplacer tout le montage d'un métier |
| 35 | PUT | `/api/metiers/{mid}/etages/{etage}` | Alimentation | `monter_etage` referentiels.py:1420 | Remplacer le montage d'un seul étage |
| 36 | GET | `/api/postes-frais` | tout rôle | `postes_frais` referentiels.py:1450 | Postes de frais (liste courte) |
| 37 | GET | `/api/export/matieres` | Achats | `exporter_matieres` referentiels.py:1471 | Excel du catalogue |
| 38 | GET | `/api/export/fournisseurs/fiches` | Achats | `exporter_fiches_fournisseurs` referentiels.py:1499 | Excel des fiches fournisseurs |
| 39 | GET | `/api/export/qualites` | Achats | `exporter_qualites` referentiels.py:1520 | Excel des qualités et recettes avec coûts |
| 40 | GET | `/api/postes-frais/complet` | Achats | `postes_complets` referentiels_import.py:67 | Postes avec clé et usage dans les dossiers |
| 41 | POST | `/api/postes-frais` | Direction | `creer_poste` referentiels_import.py:90 | Créer un poste de frais |
| 42 | PUT | `/api/postes-frais/{code}` | Direction | `modifier_poste` referentiels_import.py:145 | Modifier un poste (clé, nature) ; fige les dossiers clos |
| 43 | DELETE | `/api/postes-frais/{code}` | Direction | `supprimer_poste` referentiels_import.py:184 | Supprimer un poste inutilisé non système |
| 44 | GET | `/api/codes-douaniers` | Achats | `codes_douaniers` referentiels_import.py:214 | Codes douaniers et nombre de matières |
| 45 | POST | `/api/codes-douaniers` | Direction | `creer_code` referentiels_import.py:236 | Créer un code douanier |
| 46 | PUT | `/api/codes-douaniers/{code}` | Direction | `modifier_code` referentiels_import.py:249 | Modifier (et renuméroter) un code |
| 47 | DELETE | `/api/codes-douaniers/{code}` | Direction | `supprimer_code` referentiels_import.py:266 | Supprimer un code non porté |
| 48 | GET | `/api/commandes` | Achats | `commandes` achats.py:368 | Tous les bons de commande, détaillés |
| 49 | POST | `/api/commandes` | Achats | `creer_commandes` achats.py:452 | Créer le(s) brouillon(s), un par devise |
| 50 | PUT | `/api/commandes/{cid}` | Achats | `modifier_commande` achats.py:639 | Modifier lignes/observations/date promise |
| 51 | POST | `/api/commandes/{cid}/envoyer` | Achats | `envoyer` achats.py:691 | Envoyer (numéroter) ou soumettre à la direction |
| 52 | POST | `/api/commandes/{cid}/approuver` | Direction | `approuver` achats.py:719 | Approuver un bon au-delà du seuil |
| 53 | POST | `/api/commandes/{cid}/renvoyer` | Direction | `renvoyer` achats.py:764 | Renvoyer aux achats avec motif |
| 54 | POST | `/api/commandes/{cid}/prix` | Achats | `confirmer_prix` achats.py:808 | Prix confirmés par le fournisseur (+ catalogue) |
| 55 | PUT | `/api/commandes/{cid}/expedition` | Achats | `expedition` achats.py:865 | Jalons d'expédition, conteneur, navire |
| 56 | POST | `/api/commandes/{cid}/solder` | Achats | `solder` achats.py:887 | Solder (ou annuler si jamais livré) |
| 57 | POST | `/api/commandes/{cid}/rouvrir` | Achats | `rouvrir` achats.py:909 | Rouvrir un bon soldé/annulé |
| 58 | DELETE | `/api/commandes/{cid}` | Achats | `supprimer` achats.py:924 | Supprimer un brouillon jamais parti |
| 59 | GET | `/api/commandes/{cid}/impression` | Achats | `impression` achats.py:1035 | **Bon de commande HTML A4 en anglais, sans prix** |
| 60 | GET | `/api/receptions` | Achats | `receptions` receptions.py:309 | Toutes les réceptions (brouillons recalés) |
| 61 | POST | `/api/receptions` | Achats | `creer` receptions.py:441 | Créer une réception brouillon |
| 62 | PUT | `/api/receptions/{rid}` | Achats | `modifier` receptions.py:470 | Modifier un brouillon (remplace tout) |
| 63 | DELETE | `/api/receptions/{rid}` | Achats | `supprimer` receptions.py:497 | Supprimer un brouillon |
| 64 | POST | `/api/receptions/{rid}/valider` | Achats | `valider` receptions.py:510 | Valider : numéro, lots, entrées en stock |
| 65 | POST | `/api/receptions/{rid}/annuler` | Achats | `annuler` receptions.py:581 | Annuler une réception validée (contre-passation) |
| 66 | PUT | `/api/receptions/{rid}/facture` | Achats | `completer_facture` receptions.py:614 | Compléter / corriger / détacher la facture |
| 67 | POST | `/api/lots/numero-interne` | Achats | `lot_interne` receptions.py:665 | Prendre un numéro de lot interne |
| 68 | GET | `/api/factures` | Achats | `factures` receptions.py:673 | Liste des factures fournisseurs |
| 69 | GET | `/api/brouillons` | tout rôle | `brouillons` brouillons.py:73 | Ordres et opérations en brouillon, blocages, droit de valider |
| 70 | POST | `/api/brouillons/valider` | tout rôle (`STOCK`) | `tout_valider` brouillons.py:96 | « Tout valider » (ou une sélection) |
| 71 | GET | `/api/dossiers` | Achats | `dossiers` importations.py:396 | Tous les dossiers d'importation (résumé) |
| 72 | GET | `/api/dossiers/{did}` | Achats | `dossier` importations.py:401 | Un dossier en détail (lignes, frais, échéancier) |
| 73 | GET | `/api/dossiers-a-rattacher?locaux=` | Achats | `a_rattacher` importations.py:436 | Marchandise reçue hors dossier, par facture |
| 74 | POST | `/api/dossiers` | Achats | `creer` importations.py:593 | Ouvrir un dossier (depuis une facture, ou à la main) |
| 75 | PUT | `/api/dossiers/{did}` | Achats | `modifier` importations.py:641 | Libellé, banque, commentaire, date d'arrivée |
| 76 | POST | `/api/dossiers/{did}/rattacher` | Achats | `rattacher` importations.py:658 | Rattacher la suite d'une facture / des lignes |
| 77 | POST | `/api/dossiers/{did}/ligne-manuelle` | Achats | `ligne_manuelle` importations.py:727 | Marchandise saisie à la main (dossier d'avant mise en service) |
| 78 | PUT | `/api/dossiers/{did}/lignes/{lid}` | Achats | `modifier_ligne` importations.py:786 | Cours payé et commentaire d'une marchandise |
| 79 | PUT | `/api/dossiers/{did}/cours` | Achats | `cours_pour_tout` importations.py:814 | Un cours pour toutes les lignes d'une devise |
| 80 | POST | `/api/dossiers/{did}/cours-des-bons` | Achats | `cours_des_bons` importations.py:835 | Remettre le cours figé du bon sur chaque ligne |
| 81 | DELETE | `/api/dossiers/{did}/lignes/{lid}` | Achats | `retirer_ligne` importations.py:853 | Retirer une marchandise saisie à la main |
| 82 | POST | `/api/dossiers/{did}/detacher` | Achats | `detacher` importations.py:887 | Détacher toute une réception du dossier |
| 83 | POST | `/api/dossiers/{did}/charges` | Achats | `ajouter_charge` importations.py:978 | Ajouter un frais |
| 84 | PUT | `/api/dossiers/{did}/charges/{cid}` | Achats | `modifier_charge` importations.py:991 | Modifier un frais |
| 85 | DELETE | `/api/dossiers/{did}/charges/{cid}` | Achats | `retirer_charge` importations.py:1013 | Retirer un frais |
| 86 | POST | `/api/dossiers/{did}/cloturer` | Achats | `cloturer` importations.py:1028 | Clore (figer cours et poids) |
| 87 | POST | `/api/dossiers/{did}/rouvrir` | Achats | `rouvrir` importations.py:1068 | Rouvrir un dossier clos |
| 88 | DELETE | `/api/dossiers/{did}` | Achats | `supprimer` importations.py:1082 | Supprimer un dossier ouvert (frais perdus) |
| 89 | GET | `/api/export/dossiers?statut=` | Achats | `export_dossiers` importations.py:1099 | Excel des dossiers (4 feuilles) |
| 90 | GET | `/api/importations/analyse/revient` | Achats | `analyse_revient` analyse_import.py:80 | Coût de revient importé regroupé par axe, filtres |
| 91 | GET | `/api/importations/analyse/qualite/{code}` | Achats | `analyse_qualite` analyse_import.py:325 | Coût matière importée d'une qualité (au m², au kg) |
| 92 | GET | `/api/export/revient` | Achats | `export_revient` analyse_import.py:418 | Excel du coût de revient (2 feuilles) |
| 93 | GET | `/api/export/commandes?onglet=&q=` | Achats | `exporter_commandes` exports_achats.py:84 | Excel des bons et de leurs lignes |
| 94 | GET | `/api/export/receptions?onglet=&q=` | Achats | `exporter_receptions` exports_achats.py:149 | Excel des réceptions et de leurs lignes |
| 95 | GET | `/api/export/receptions/pesees?q=&ecarts=` | Achats | `exporter_pesees` exports_achats.py:227 | Excel de l'archive des pesées |
| 96 | GET | `/api/export/receptions/bobines?q=&ecarts=` | Achats | `exporter_bobines` exports_achats.py:274 | Excel du poids des bobines |
| 97 | GET | `/api/export/commandes/{cid}/bon` | Achats | `exporter_bon_fournisseur` exports_achats.py:324 | **Bon de commande Excel en anglais, sans prix** |

Les trois routes de `analyse_import.py` portent la dépendance au niveau du routeur
(`APIRouter(dependencies=[Depends(ACHATS)])`, `analyse_import.py:24`).

## A.2 Référentiels (`api/referentiels.py`)

Doctrine du module (`referentiels.py:1-12`) : les achats créent et tiennent les matières, la
classification et les fournisseurs ; la direction tient les rôles de nomenclature, les
qualités, les recettes, le plan, les magasins et le réglage des métiers ; l'alimentation monte
les fils sur les métiers. Données réelles : chaque changement est tracé au journal.

### A.2.1 Classification

Tables (`referentiels.py:37-42`) : `nom` ∈ `composition` (table `Composition`, colonne article
`composition`, libellé « Composition »), `type_fil` (« Type de fil »), `titrage` (« Titrage »),
`couleur` (« Couleur »). Champs lus (`CHAMPS_CLASSIFICATION`, l.44) : `code, libelle, famille,
valeur, unite, actif, composition_detaillee, commentaire` — chaque table n'a que certains de
ces champs (seuls ceux qu'elle porte sont renvoyés/écrits, via `hasattr`).

#### GET `/api/classification` — tout rôle — `referentiels.py:83`

Réponse 200 :
```
{
  "composition": [ {code, libelle?, famille?, valeur?, unite?, actif?, composition_detaillee?, commentaire?, articles} ],
  "type_fil":    [ … idem … ],
  "titrage":     [ … idem … ],
  "couleur":     [ … idem … ],
  "roles": [ {code, lineaire, ordre, articles, qualites, de_base} ]
}
```
- Chaque liste triée par `code` ; `articles` = nombre de matières qui portent la valeur.
- `roles` (`_roles`, l.69-80), triés par `ordre` puis `code` : `lineaire` (compté au mètre),
  `ordre`, `articles` (matières de ce rôle), `qualites` (qualités dont le poids au m² de ce
  rôle est > 0), `de_base` (vrai pour les 8 rôles du calcul : Poil, Chaîne, Trame, Colle,
  Cuir, Franges, Ruban, Plastique — `calcul/modele.py:23`).

#### POST `/api/classification/roles` — Direction — `referentiels.py:122` — 201

Corps `RoleEntree` (l.106-109) :

| Champ | Type | Défaut | Contraintes |
|---|---|---|---|
| `code` | str | requis | 1–32 car. (espaces de bord retirés) |
| `lineaire` | bool | `false` | doit valoir vrai **si et seulement si** code ∈ {Cuir, Franges, Ruban} |
| `ordre` | int | 0 | 0–999 |

Refus : 409 « Le rôle « X » existe déjà. » (comparaison insensible à la casse) ; 422
`_verifier_lineaire` (l.112-119) « Le calcul compte au mètre Cuir, Franges, Ruban, et eux
seuls : « X » se compte au mètre | au poids. »
Effets : crée `RoleNomenclature` ; journal `ajout rôle de nomenclature` / `role` / code.
Réponse : la classification complète (même forme que le GET).

#### PUT `/api/classification/roles/{code}` — Direction — `referentiels.py:135`

Corps `RoleEntree`. Refus : 404 « Rôle introuvable. » ; si renommage (`code` du corps ≠ chemin) :
409 « « X » est un rôle de base du calcul : il garde son nom. » ; 409 « « X » est porté par des
matières ou des qualités : il garde son nom. » (porté = matières du rôle, ou **toute** ligne
`QualitePoids` du rôle, même à 0) ; 409 « Le rôle « Y » existe déjà. » ; 422 linéaire (voir
ci-dessus, appliqué au nouveau code).
Effets : renommage = suppression puis recréation du rôle ; sinon mise à jour `lineaire`,
`ordre`. Journal `modification rôle de nomenclature` / `role` / `code` ou `ancien → nouveau`.
Réponse : classification complète.

#### DELETE `/api/classification/roles/{code}` — Direction — `referentiels.py:165`

Refus : 404 « Rôle introuvable. » ; 409 « « X » est un rôle de base du calcul : il ne se
supprime pas. » ; 409 « « X » est porté par N matière(s) et M qualité(s) : les changer d'abord. »
(qualités comptées si poids > 0).
Effets : supprime les `QualitePoids` du rôle (poids à 0 restants), puis le rôle ; journal
`suppression rôle de nomenclature` ; **une version de recette** par qualité touchée.
Réponse : classification complète.

#### POST `/api/classification/{nom}` — Achats — `referentiels.py:201` — 201

Corps `ValeurClassification` (l.184-192) :

| Champ | Type | Défaut | Contraintes |
|---|---|---|---|
| `code` | str | requis | 1–64 car. |
| `libelle` | str | "" | ≤ 120 |
| `famille` | str | "" | ≤ 64 |
| `valeur` | str | "" | ≤ 32 |
| `unite` | str | "" | ≤ 16 |
| `composition_detaillee` | str | "" | ≤ 160 |
| `commentaire` | str | "" | ≤ 500 |
| `actif` | bool | `true` | |

Règle : pour `titrage` sans `valeur`, le code est coupé au premier espace : « 2900 Dtex » →
valeur « 2900 », unité « Dtex » (l.206-207). Refus : 404 « Liste inconnue. » (`nom` hors des 4) ;
409 « « X » existe déjà. ». Effets : crée la valeur (seuls les champs que la table porte) ;
journal `ajout <libellé en minuscules>` / objet = `nom` / code. Réponse : classification complète.

#### PUT `/api/classification/{nom}/{code}` — Achats — `referentiels.py:218`

Corps `ValeurClassification`. Copie tous les champs (sauf `code`) ; si `code` change :
409 « « X » existe déjà. » sinon renommage — les matières suivent par `ON UPDATE CASCADE`
(`modeles.py:286-290`). Refus : 404 « Liste inconnue. », 404 « Valeur introuvable. ».
Journal `modification <libellé>` / `nom` / `ancien → nouveau` (même si inchangé).
Réponse : classification complète.

#### DELETE `/api/classification/{nom}/{code}` — Achats — `referentiels.py:237`

Refus : 404 « Liste inconnue. » / « Valeur introuvable. » ; 409 « « X » est porté par N
matière(s) : les reclasser d'abord, ou désactiver la valeur. » Journal `suppression <libellé>`.
Réponse : classification complète.

### A.2.2 Fournisseurs

Corps `FournisseurEntree` (`referentiels.py:261-279`) :

| Champ | Type | Défaut | Contraintes / traitement |
|---|---|---|---|
| `nom` | str | requis | 2–160 ; espaces de bord retirés ; unique sans casse |
| `code` | str | "" | ≤ 32 ; retiré des espaces |
| `pays` | str | "" | ≤ 80 ; mis en MAJUSCULES, espaces multiples réduits (« TURKEY », « MAROC ») |
| `contact` | str | "" | ≤ 120 |
| `telephone` | str | "" | ≤ 60 |
| `email` | str | "" | ≤ 160 (pas de validation de format) |
| `devise` | str | "MAD" | ≤ 3 ; mise en majuscules ; doit exister (table `Devise`) |
| `delai_jours` | float | 60 | > 0, ≤ 730 — délai de livraison déclaré |
| `couverture_commande_jours` | float | 0 | 0–730 |
| `mode_paiement` | str | "" | ≤ 40 |
| `delai_paiement_jours` | float | 0 | 0–730 — sert à l'échéance des factures |
| `conditions_paiement` | str | "" | ≤ 160 |
| `incoterm` | str | "" | ≤ 20 — imprimé sur le bon |
| `port_chargement` | str | "" | ≤ 80 |
| `banque` | str | "" | ≤ 120 |
| `notes` | str | "" | ≤ 2000 |
| `actif` | bool | `true` | |
| `empreinte` | str ∣ null | null | contrôle de concurrence (PUT) ; non stocké |

Forme d'un fournisseur renvoyé (`_fournisseur`, l.323-341) : tous les champs ci-dessus (sauf
`empreinte` d'entrée) + `id`, `local` (pays ∈ {MAROC, MOROCCO, ""}), `devises` (objet
`{devise: nombre de matières}`), `articles` (nombre de matières), `commandes`, `receptions`
(nombres), `pieces` (pièces jointes), `delai_mesure_jours` (moyenne, arrondie à 0,1, des jours
entre `date_commande` du bon et `date` de la réception **validée**, sur les 365 derniers jours,
couples réception/bon distincts, négatifs ramenés à 0 ; `null` sans mesure),
`livraisons_mesurees` (nombre de mesures), `empreinte` (condensé des 17 champs saisis).

#### GET `/api/fournisseurs` — tout rôle — `referentiels.py:344`
Liste triée par `nom`. Aucun prix (mais banque, conditions de paiement visibles de tous).

#### POST `/api/fournisseurs` — Achats — `referentiels.py:368` — 201
Refus : 409 « Le fournisseur « X » existe déjà. » ; 422 « Devise inconnue : « XXX ». L'ajouter
d'abord (Réglages › Devises). » Journal `création fournisseur` / `fournisseur` / id / nom.
Réponse : la fiche.

#### PUT `/api/fournisseurs/{fid}` — Achats — `referentiels.py:381`
Verrou de ligne. Refus : 404 « Fournisseur introuvable. » ; 409 empreinte (« Ce fournisseur… ») ;
409 nom déjà pris par un autre ; 422 devise. Journal `modification fournisseur`. Réponse : la fiche.

#### DELETE `/api/fournisseurs/{fid}` — Achats — `referentiels.py:399`
Refus : 404 ; 409 « « Nom » a {des matières du catalogue | des commandes | des réceptions |
des lots | des opérations | des factures} : le désactiver plutôt que le supprimer. » (premier
usage trouvé, dans cet ordre) ; 409 « « Nom » a des pièces jointes : les retirer d'abord, ou le
désactiver. » Journal `suppression fournisseur`. Réponse `{"ok": true}`.

### A.2.3 Matières (catalogue)

Corps `ArticleEntree` (`referentiels.py:427-453`) :

| Champ | Type | Défaut | Contraintes / traitement |
|---|---|---|---|
| `version` | int ∣ null | null | PUT : doit égaler la version en base, sinon 409 |
| `reference` | str | requis | 2–160 ; espaces de bord retirés ; unique (sensible à la casse) |
| `designation` | str | "" | ≤ 160 |
| `role` | str | requis | ≤ 32 ; doit exister (`RoleNomenclature`) |
| `composition` | str ∣ null | null | ≤ 32 ; vide → null ; sinon doit exister |
| `type_fil` | str ∣ null | null | ≤ 32 ; idem |
| `titrage` | str ∣ null | null | ≤ 48 ; idem |
| `couleur` | str ∣ null | null | ≤ 64 ; idem |
| `couleur_code` | str | "" | ≤ 32 |
| `unite_prix` | str | "kg" | ≤ 4 ; `kg` ou `ml` |
| `densite` | float | 0 | 0–1000 (kg par mètre linéaire) |
| `fournisseur_id` | int ∣ null | null | requis si `actif` ; doit exister |
| `prix` | float | 0 | 0–1e7 ; dans `unite_prix` et `devise` |
| `devise` | str | "MAD" | ≤ 3 ; majuscules ; doit exister |
| `unite_achat` | str | "kg" | ≤ 32 ; vide → `kg` ; `ml` interdit |
| `contenance_achat` | float | 1 | 0–1e7 ; requise (> 0) si `unite_achat` ≠ kg ; forcée à 1 si kg |
| `minimum_commande` | float | 0 | 0–1e9 (kg) |
| `poids_bobine` | float | 0 | 0–1000 (kg) |
| `bobines_palette` | float | 0 | 0–10000 |
| `stock_min` | float | 0 | 0–1e9 (kg) |
| `couv_min_mois` | float | 0 | 0–60 |
| `groupe_equiv` | str | "" | ≤ 64 — groupe d'équivalence |
| `priorite_equiv` | float ∣ null | null | 0–100 |
| `code_douanier` | str ∣ null | null | ≤ 20 ; vide → null ; sinon doit exister |
| `actif` | bool | `true` | |

Refus de `_verifier_article` (l.566-604), tous 422, dans l'ordre :
« Rôle inconnu : « X ». » ; « {Composition|Type de fil|Titrage|Couleur} inconnue : « X ».
L'ajouter d'abord dans la classification. » ; « Unité du prix : au kilo (kg) ou au mètre (ml). » ;
« Une matière du rôle {rôle} (cuir, franges, ruban : comptés au mètre dans les recettes) a besoin
de sa densité (kg/ml) : le stock est en kilos. » ; « Un prix au mètre a besoin de la densité
(kg/ml) pour se ramener au kilo. » ; « Une matière en service a un fournisseur : sans lui, le plan
d'achat ne sait pas à qui la commander (contrôle C05). » ; « Fournisseur inconnu. » ; devise
inconnue ; « La commande se compte en kilos (ou en palettes, fûts… de tant de kilos). Un
fournisseur qui facture au mètre : choisir le prix « au mètre ». » ; « Une unité d'achat autre
que le kilo a besoin de sa contenance (kg par unité). » ; « Code douanier inconnu : « X ».
L'ajouter d'abord (Réglages › Codes douaniers). »

Forme d'une matière renvoyée (`article_dict`, l.471-497) : `id, version, reference,
designation, role, composition, type_fil, titrage, titrage_unite` (unité du titrage lue dans
la table Titrage), `couleur, couleur_code, densite, fournisseur_id, kg_par_ml` (= densité si
rôle linéaire, sinon 0), `fournisseur` (nom), `prix, unite_prix, prix_kg` (prix ramené au kilo :
prix/densité si au mètre, `modeles.py:316-321`), `devise, unite_achat, contenance_achat,
minimum_commande, poids_bobine, bobines_palette, contenance_palette` (= poids bobine × bobines
par palette), `conditionnement` {`unite`, `contenance`, `declare`} (voir ci-dessous),
`stock_min, couv_min_mois, groupe_equiv, priorite_equiv, code_douanier, actif, modifie_par,
modifie_le` (ISO à la minute), et selon la route : `historique` (bool) + `historique_raison`
(texte de ce qui empêche la suppression, "" sinon), `stock` (kg, somme des soldes de tous ses
lots, tous magasins).

`conditionnement` (l.456-468) : unité d'achat déclarée (≠ kg, contenance > 0) → `declare=true` ;
sinon déduite : Palette (poids bobine × bobines/palette) si connue, sinon Bobine (poids
bobine), sinon `kg` (contenance 1) — `declare=false`.

Usages qui interdisent la suppression (`USAGES_ARTICLE`, l.501-511, puis pièces jointes) :
mouvements de stock, lots, commandes, réceptions, ordres de fabrication, opérations (brouillons
compris), dossiers d'importation, recettes, fils montés, pièces jointes.

#### GET `/api/articles` — tout rôle — `referentiels.py:544`
Toutes les matières, triées par `reference`, avec `stock`, `historique`, `historique_raison`.
Alimentation : `prix` et `prix_kg` à `null`.

#### POST `/api/articles` — Achats — `referentiels.py:607` — 201
Refus : 422 ci-dessus ; 409 « La matière « X » existe déjà. ». Effets : crée la matière
(`version` initiale de la base), `modifie_le`=maintenant, `modifie_par`=nom ; journal
`création matière` / `article` / id / référence. Réponse : la matière, `stock` 0,
`historique` false.

#### PUT `/api/articles/{aid}` — Achats — `referentiels.py:623`
Verrou. Refus : 404 « Matière introuvable. » ; 409 « Cette fiche a été modifiée entre-temps par
{modifie_par | un autre poste} : rechargez-la pour repartir de sa dernière version, puis refaites
la modification. » ; 422 ci-dessus ; 409 référence prise. Effets : tous les champs remplacés,
`version` + 1, `modifie_le/par` ; journal `modification matière` / référence ou `ancienne →
nouvelle`. Réponse : la matière avec `stock`, `historique`, `titrage_unite`.

#### DELETE `/api/articles/{aid}` — Achats — `referentiels.py:656`
Refus : 404 ; 409 `_message_usage` (l.531-536) : pour recettes, fils montés, pièces jointes :
« « Réf » figure dans {quoi} : l'en retirer d'abord, ou désactiver la matière. » ; sinon « « Réf »
figure dans {quoi} : elle appartient à l'historique. La désactiver plutôt que la supprimer. »
Journal `suppression matière`. Réponse `{"ok": true}`.

#### POST `/api/catalogue/classer` — Achats — `referentiels.py:680`
Paramètre de requête `appliquer` (bool, défaut `false`). Pas de corps.
Pour chaque matière (ordre de référence) : `classification.decomposer(reference, libellé de sa
composition)` lit composition, type de fil, titrage (+ unité), couleur, code couleur ; la
désignation, sans parenthèses et si ≤ 40 caractères, remplace la couleur lue. **Seuls les
champs vides** sont proposés (composition et type en MAJUSCULES, titrage complet « 2900 Dtex »).
Les valeurs inconnues de la classification sont listées à créer (composition : libellé et
famille déduits ; type : libellé connu `TYPES_CONNUS` ou le code ; titrage : valeur + unité ;
couleur : libellé = code).
Réponse : `{"appliquer": bool, "propositions": [{article_id, reference, <champs proposés>}],
"a_creer": {composition: [codes triés], type_fil: […], titrage: […], couleur: […]}}`.
Avec `appliquer=true` : écrit les champs, `version`+1, `modifie_le/par` sur chaque matière,
crée les valeurs manquantes, journal **unique** `classement du catalogue` / `article` / « N
matière(s) complétée(s) ». Sans : rien n'est écrit.

#### POST `/api/articles/composer` — tout rôle — `referentiels.py:744`
Corps `Composition` (l.671-677) : `composition`, `type_fil` (≤ 32), `titrage` (≤ 48), `couleur`
(≤ 64), `couleur_code` (≤ 32), `suffixe` (≤ 16), tous str défaut "". N'écrit rien.
Réponse : `{"reference": <référence composée par classification.composer(...)>, "existe":
bool (une matière porte déjà cette référence), "designation": <couleur (libellé ou code) +
code couleur>}`. Le titrage connu fournit valeur et unité ; la couleur connue fournit son libellé.

### A.2.4 Qualités, recettes, plan

Forme d'une qualité (`_qualite`, l.770-780, complétée l.813-823) :
`id, code, nom, base_mensuelle` (m²/mois), `actif`, `poids` ({rôle: kg ou ml au m²}),
`saisonnalite` (12 coefficients, 1,0 par défaut), `recette` (lignes ci-dessous),
`fabrications` (nombre d'ordres `BonFabrication` qui l'ont tissée), `empreinte` (condensé de
code, nom, actif, poids triés, recette triée (article_id, %)), `controle`
(`moteur.controle_recettes` : `{qualite, roles_utilises, roles_conformes, ecarts: [{role,
somme}], conforme}` — somme des % par rôle de poids non nul, tolérance 0,01 point ou 1e-6 en
mode classeur), `cout_m2_mad` (somme des coûts des lignes), `kg_m2` (somme des kg/m²).

Ligne de recette (calculée par `moteur.nomenclature`, l.794-808) : `id` (id de la ligne
`Recette`), `article_id, reference, role` (rôle BOM), `nature, designation, fournisseur,
pourcentage` (part dans le rôle), `kg_m2` (kilos au m² = part × poids du rôle, **sans** la perte),
`prix_kg, ml_m2` (mètres au m² pour Cuir/Franges/Ruban, sinon null), `densite, prix` (prix du
catalogue dans son unité), `unite_prix, devise, cout_m2_mad` (coût au m² en dirhams = kg/m² ×
prix au kilo × cours de la devise × (1 + taux de perte), perte ignorée en mode classeur).

#### GET `/api/qualites` — tout rôle — `referentiels.py:783`
Toutes les qualités triées par code. Alimentation : `cout_m2_mad` de la qualité et `prix_kg`,
`prix`, `unite_prix`, `cout_m2_mad` de chaque ligne à `null`.

#### GET `/api/qualites/facteurs-cout` — Achats — `referentiels.py:827`
Réponse `{"perte": 1 (mode classeur) ou 1 + taux_perte, "taux": {devise: cours en MAD}}`.
Formule rappelée : coût/m² = kg/m² × prix au kilo × cours × perte.

#### POST `/api/qualites` — Direction — `referentiels.py:846` — 201
Corps `QualiteEntree` (l.838-843) : `code` str 1–32 requis ; `nom` str ≤ 120 ""; `actif` bool
true ; `poids` objet {rôle: float} {} ; `empreinte` str∣null (ignorée à la création).
Refus : 409 « La qualité « X » existe déjà. » ; 422 « Rôle inconnu : « X ». » ; 422 « Un poids au
m² ne peut pas être négatif. » Effets : crée la qualité et ses poids ; journal `création
qualité` / `qualite` ; version de recette. Réponse `{"id", "empreinte"}`.

#### PUT `/api/qualites/{qid}` — Direction — `referentiels.py:875`
Corps `QualiteEntree`. Verrou. Refus : 404 « Qualité introuvable. » ; 409 empreinte (« Cette
qualité… ») ; 409 code pris ; 422 poids. Effets : code, nom, actif ; poids **fusionnés** (un rôle
absent du corps garde son poids) ; journal `modification qualité` ; si `actif` a changé →
journal `plan de production` (« CODE : remise en service | arrêtée » + JSON avant/après du
plan, via `noter_plan`) ; version de recette.
Réponse `{"id", "empreinte", "avertissement"}` — avertissement non vide si des rôles ont un poids
> 0 sans matière à part > 0 dans la recette : « Rôle(s) avec un poids au m² mais sans matière
dans la recette : X, Y. Les besoins et la sortie vers les machines ne les comptent pas tant que
la recette ne les nomme pas. »

#### DELETE `/api/qualites/{qid}` — Direction — `referentiels.py:910`
Refus : 404 ; 409 « « X » a été fabriquée par N ordre(s) : elle appartient à l'historique. La
désactiver plutôt que la supprimer. » Effets : supprime la recette, la qualité (poids et
saisonnalité en cascade) ; journal `suppression qualité`. Réponse `{"ok": true}`.

#### PUT `/api/qualites/{qid}/recette` — Direction — `referentiels.py:933`
Corps : **tableau** de `LigneRecetteEntree` {`article_id` int requis, `pourcentage` float 0–100
requis}. Requête : `empreinte` (str, facultatif), `motif` (str ≤ 300, défaut "").
Refus : 404 ; 409 empreinte ; `remplacer_recette` (l.951-984), 422 : « Matière inconnue dans la
recette. » ; « « Réf » figure deux fois dans la recette. » ; « Dans chaque rôle, la recette doit
faire 100 % : Rôle T %, … » (somme des % > 0 par rôle de la matière, écart > 0,01 point) ;
« La recette oublie le rôle R (P au m²) : y mettre ses matières, ou ramener son poids au m² à 0
dans la fiche. » (ou « les rôles … leurs matières … leur poids … »). Une liste vide est
acceptée seulement si aucun rôle n'a de poids > 0.
Effets : recette remplacée ; journal `recette` / `qualite` / « CODE : N ligne(s) — motif » ;
version de recette. Réponse `{"ok": true, "empreinte"}`.

#### POST `/api/qualites/{qid}/versions/{vid}/restaurer` — Direction — `referentiels.py:987`
Requête : `motif` str **requis** 1–300 ; `empreinte` facultatif. Refus : 404 « Qualité
introuvable. » ; 404 « Version introuvable. » (inconnue ou d'une autre qualité) ; 409 empreinte ;
409 « Ces matières n'existent plus au catalogue : A, B. La version ne peut pas revenir telle
quelle. » ; refus de `remplacer_recette`.
Effets : poids de la version (sinon ceux de la première version **suivante** qui en a, sinon
inchangés) ; les rôles absents de la version reviennent à 0 ; parts de la version ; journal
`recette` « CODE : retour à la version du JJ/MM/AAAA HH:MM — motif » ; nouvelle version de
recette. Réponse `{"ok": true, "empreinte", "poids": {rôle: poids}}`.

#### PUT `/api/qualites/{qid}/plan` — Direction — `referentiels.py:1034`
Corps `PlanEntree` : `base_mensuelle` float 0–1e9 requis ; `saisonnalite` liste de float, **exactement
12**. Refus : 404 ; 422 « Un coefficient de saisonnalité reste entre 0 et 20. »
Effets (`production_plan.enregistrer_plan`) : base et 12 coefficients écrits ; si changement,
journal `plan de production` / `qualite` / « CODE : B m²/mois » + ligne marquée du JSON
{avant, après} — le passé est jugé sur le plan de son époque. Réponse `{"ok": true}`.

### A.2.5 Magasins

Corps `MagasinEntree` (l.1052-1057) : `code` str 1–64 requis ; `nom` str ≤ 120 "" ; `type` str
« Stock courant » (seules valeurs : « Stock courant », « Quarantaine ») ; `contenu` str ≤ 120 "" ;
`actif` bool true.
Forme renvoyée : `{id, code, nom, type, actif, contenu, stock}` (`stock` = kg détenus, tous
lots), liste triée par type puis code.

- **GET `/api/magasins`** — tout rôle — l.1060.
- **POST `/api/magasins`** — Direction — l.1069 — 201. Refus : 422 « Type de magasin : « Stock
  courant » ou « Quarantaine ». » ; 409 « Le magasin « X » existe déjà. » Journal `création
  magasin` (objet_id vide). Réponse : la liste entière.
- **PUT `/api/magasins/{gid}`** — Direction — l.1083. Refus : 404 « Magasin introuvable. » ;
  422 type ; 409 code pris ; 409 « « X » détient encore N kg : transférer le stock avant de
  désactiver le magasin. » (détenu > 0,001 kg) ; 409 « Un magasin qui détient de la matière ne
  change pas de type. » Journal `modification magasin`. Réponse : la liste.
- Pas de suppression de magasin. Au démarrage, un « Magasin principal » (Stock courant) et une
  « Quarantaine » sont créés s'il n'en existe pas de ce type (`main.py:78-82`).

### A.2.6 Métiers à tisser et montage

Corps `MetierEntree` (l.1118-1126) : `code` 1–32 requis ; `nom` ≤ 120 "" ; `laize` float 0–100
défaut 4,2 (m) ; `densite` float 0–100000 défaut 0 (bobines par mètre de laize) ; `etages` int
1–40 défaut 6 ; `actif` bool true ; `commentaire` ≤ 2000 "" ; `empreinte` str∣null.
Corps `FilEntree` (l.1110-1115) : `article_id` int requis ; `etage` int 1–40 défaut 1 ; `metres`
float 0–1000 défaut 0 ; `pourcentage` float 0–100 défaut 100 (part du fil quand deux fils se
partagent les mêmes mètres) ; `commentaire` ≤ 300 "".
Corps `EtageEntree` (l.1129-1134) : `fils` liste de `FilEntree` (défaut []) ; `empreinte`.

Calculs : bobines d'un fil = mètres × densité du métier × part/100 ; poids = bobines × poids de
bobine **utilisé** (`_bobine_utilisee`, l.1160-1166 : poids du lot pesé — dernier lot sorti
vers les machines, sinon dernier reçu, `depot.poids_bobine_mesures` — sinon catalogue, M43) ;
`source_poids` = « lot N (sorti|reçu) », « catalogue » ou "". Écart mesuré = pesé/catalogue − 1
(si source ≠ catalogue) ; hors tolérance si |écart| > réglage `toler_poids_bobine`.

#### GET `/api/metiers` — tout rôle — `referentiels.py:1198`
Liste triée par nom puis code. Pour chaque métier : `id, code, nom, laize, densite, etages,
actif, commentaire`, `fils` (chacun : `id, article_id, reference, designation, fournisseur,
etage, metres, pourcentage, commentaire, bobines, poids_bobine` (catalogue)`,
poids_bobine_utilise, source_poids, ecart_mesure, ecart_hors_tolerance, poids` (kg)`,
valeur_mad` (poids × coût moyen pondéré de la référence, `moteur.cmup_par_reference` ; null
pour l'alimentation)), `poids` (total kg), `valeur_mad` (total ; null alimentation),
`bobines, metres` (totaux), `etages_detail` (pour chaque étage 1..N : `etage, fils` (nombre),
`metres` (Σ mètres × part), `bobines, poids, trop_large` (mètres > laize)),
`etages_garnis`, `etages_trop_larges` (numéros), `densite_a_saisir` (densité nulle),
`fils_sans_poids` (fils sans poids de bobine), `bons` (bons de sortie qui nomment le métier),
`tolerance_bobine`, `dernier_montage` ({par, quand, detail} — dernière ligne de journal
`montage` parmi les 500 plus récentes, ou null), `empreinte` (réglage du métier),
`empreinte_fils` (tout le montage), `empreintes_etages` ({n° étage: empreinte}).
Le poids des fils est du stock « en machine » (compté dans le stock, sa valeur et le plan
d'achat — partie stock). Un métier arrêté pèse quand même ici (le stock « en machine » le
compte à 0 : voir `_pese`).

#### GET `/api/montage/references` — tout rôle — `referentiels.py:1262`
Pour chaque matière **non linéaire** : `{article_id, poids_bobine_utilise, source_poids,
sorti_recent` (kg partis aux machines les 30 derniers jours, retours déduits : −Σ mouvements
SORTIE + RETOUR_MACHINE), `monte` (kg montés sur les métiers **actifs**), `jours`: 30}`.

#### POST `/api/metiers` — Direction — l.1284 — 201
Refus 409 « Le métier « X » existe déjà. » Journal `création métier`. Réponse `{"id"}`.

#### PUT `/api/metiers/{mid}` — Direction — l.1297
Verrou. Refus : 404 « Métier introuvable. » ; 409 empreinte « Ce métier » ; 409 code pris ; 422
« Des fils sont montés à l'étage N : les retirer ou les déplacer avant de ramener le métier à E
étage(s). » ; 422 « Étage N : M m montés, plus que la laize de L m demandée. Retirer d'abord du
fil. » Journal `réglage métier`. Réponse `{"id", "empreinte"}`.

#### DELETE `/api/metiers/{mid}` — Direction — l.1325
Refus : 404 ; 409 « « X » porte encore N fil(s) : les retirer d'abord. » ; 409 « « X » est nommé par
N ordre(s) de fabrication : il appartient à l'historique. L'arrêter plutôt que le supprimer. »
Journal `suppression métier`. Réponse `{"ok": true}`.

#### PUT `/api/metiers/{mid}/fils` — Alimentation — l.1397
Corps : tableau de `FilEntree`. Requête `empreinte` (facultatif ; empreinte de tout le montage).
Refus : 404 ; 409 « Le montage de ce métier a été modifié(e) entre-temps… » ; `_verifier_fils`
(l.1343-1368), 422 : « Matière inconnue. » ; « « Réf » (Rôle) se pose au mètre linéaire : elle ne se
monte pas en bobines sur un métier. » ; « Étage N : ce métier n'en a que E. » ; « « Réf » est monté
deux fois à l'étage N. » ; « « Réf » à l'étage N : saisir les mètres montés. » (mètres ≤ 0) ;
« Étage N : M m montés (mètres × part de chaque fil) pour une laize de L m. »
Effets : montage entier remplacé ; journal `montage` / `metier` / détail « CODE : étage 1 REF 4,2 m
(60 %), … — sur les métiers A → B kg (+C kg) » (kilos à la française, une décimale).
**Aucun mouvement de stock** : le stock « en machine » se lit du montage.
Réponse `{"ok": true, "empreinte_fils", "stock": {"avant", "apres", "ecart" (kg, 1 déc.),
"detail"}}` — avant/après = poids des fils comptés par le stock (0 si métier arrêté).

#### PUT `/api/metiers/{mid}/etages/{etage}` — Alimentation — l.1420
Corps `EtageEntree` (l'`etage` de chaque fil est forcé à celui du chemin). Refus : 404 métier ;
**404** « Étage N : ce métier n'en a que E. » ; 409 « L'étage N a été modifié(e) entre-temps… » ;
`_verifier_fils` sur l'ensemble (autres étages + celui-ci). Effets : seul cet étage est remplacé ;
journal `montage` (« CODE, étage N : … »). Réponse `{"ok": true, "empreinte"` (de l'étage)`,
"stock": {…}}`.

### A.2.7 Postes de frais (liste courte)

**GET `/api/postes-frais`** — tout rôle — l.1450. Liste triée par `ordre` :
`{code, libelle, recuperable, cle ("valeur"|"poids"), ordre}`.

### A.2.8 Exports des référentiels
Décrits en A.9 (routes 37-39).

## A.3 Postes de frais et codes douaniers (`api/referentiels_import.py`)

Postes **système** (`POSTES_SYSTEME`, l.40) : `DD` (droits, coût), `TPI` (coût), `TVA`
(récupérable), `FRET` (coût), `ASSUR` (coût) — ne se suppriment pas, ne changent pas de nature.
Clés de répartition (`CLES`, l.41) : `valeur` « à la valeur », `poids` « au poids ».
Les postes d'origine sont créés au démarrage depuis `calcul.modele.POSTES_IMPORT`
(`main.py:59-73`).

Forme d'un poste (`_poste_dict`, l.61-64) : `{code, libelle, recuperable, cle, ordre, systeme,
frais` (nombre de frais du poste dans tous les dossiers)`, dossiers_ouverts, dossiers_clos}`
(dossiers distincts qui portent un frais du poste, selon leur statut).

#### GET `/api/postes-frais/complet` — Achats — l.67
Liste triée par `ordre` puis `code`.

#### POST `/api/postes-frais` — Direction — l.90 — 201
Corps `PosteEntree` (l.75-87) :

| Champ | Type | Défaut | Contraintes |
|---|---|---|---|
| `code` | str | "" | ≤ 16 ; mis en majuscules ; doit correspondre à `[A-Z0-9_]{1,16}` |
| `libelle` | str | requis | 1–80 ; validateur : non vide après retrait des espaces (« le libellé est obligatoire »), stocké sans espaces de bord |
| `recuperable` | bool | false | |
| `cle` | str | "valeur" | pattern `^(valeur|poids)$` |
| `ordre` | int ∣ null | null | 0–999 ; null → (ordre max) + 1 |

Refus : 422 « Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT). » ;
409 « Le poste « X » existe déjà. » Journal `création poste de frais` / `poste_frais` /
« CODE · Libellé · à la valeur[ · récupérable] ». Réponse : le poste.

#### PUT `/api/postes-frais/{code}` — Direction — l.145
Corps `PosteEntree` (son `code` est ignoré : le code ne se renomme pas). Verrou.
Refus : 404 « Poste de frais introuvable. » ; si la nature change : 409 « « Libellé » est
{récupérable | un coût} par nature : les calculs du dossier (TVA attendue) le lisent ainsi. »
(poste système) ; 409 « Ce poste porte des frais dans N dossier(s) clos : changer sa nature
changerait leur coût. Créer un autre poste. » ; si la clé ou la nature change, pour chaque
dossier **non clos** qui porte un frais concerné (frais global non figé pour la clé ; tout frais
pour la nature) : 409 `cout_hors_periode_close` (geste « changement du poste « Libellé » »).
Effets : si la clé change, `_figer_clos` (l.107-142) : dans chaque dossier **clos** (verrouillé)
ayant ≥ 2 marchandises, chaque frais global de ce poste encore non figé reçoit ses **parts**
(`DossierChargePart(ligne_id, montant)`) calculées à l'ancienne clé — au poids : kilos
(`x.kilos`) ; à la valeur : valeur en devise × cours de la ligne (ou du jour), MAD tel quel —
sans arrondi ; journal `frais figés` / `dossier` / « NUM · POSTE à la valeur : dossier clos, sa
répartition est gardée (N frais, une pièce chacun) ». Puis libellé, nature, clé, ordre (si
fourni) écrits ; journal `modification poste de frais` « CODE : ancien libellé · ancienne clé →
nouveau · nouvelle clé[ · N dossier(s) clos figé(s)] ».
Réponse : le poste + `dossiers_figes` (nombre).

#### DELETE `/api/postes-frais/{code}` — Direction — l.184
Refus : 404 ; 409 « « Libellé » sert aux calculs du dossier : il ne se supprime pas. » ; 409
« Ce poste porte des frais dans des dossiers : il ne se supprime pas. » Journal `suppression poste
de frais`. Réponse `{"ok": true}`.

#### GET `/api/codes-douaniers` — Achats — l.214
Liste triée par code : `{code, libelle, taux_droits` (fraction : 0,10 = 10 %)`, actif, matieres}`
(nombre de matières qui le portent).

Corps `CodeEntree` (l.220-233) : `code` str 2–20 requis, espaces retirés, validateur
`^\d[\d.]{1,19}$` (« un code douanier s'écrit en chiffres, éventuellement séparés de points (ex.
5402.47.00.00) ») ; `libelle` ≤ 160 "" ; `taux_droits` float 0–1 **requis** ; `actif` bool true.

#### POST `/api/codes-douaniers` — Direction — l.236 — 201
Refus 409 « Le code douanier « X » existe déjà. » Journal `création code douanier` « CODE ·
10.00% ». Réponse : le code.

#### PUT `/api/codes-douaniers/{code}` — Direction — l.249
Le code se renomme (les matières suivent : `ON UPDATE CASCADE`, `modeles.py:311`). Verrou.
Refus : 404 « Code douanier introuvable. » ; 409 nouveau code existant. Journal `modification
code douanier` « ancien · taux → nouveau · taux[ · désactivé] ». Réponse : le code.
Un code désactivé n'annonce plus de droits attendus (les matières comptent « sans code »).

#### DELETE `/api/codes-douaniers/{code}` — Direction — l.266
Refus : 404 ; 409 « N matière(s) portent ce code : le leur retirer d'abord, ou le désactiver. »
Journal `suppression code douanier`. Réponse `{"ok": true}`.

## A.4 Commandes (`api/achats.py`)

Règles du module (`achats.py:1-17`) : préparation obligatoire depuis le plan d'achat ; **un bon
par devise** ; il part **sans prix** ; un brouillon n'a **pas de numéro** (numéro et date le jour
de l'envoi, M65 ; date d'envoi passée permise, jamais future ni en période close) ; au-delà du
**seuil d'approbation** (réglage `seuil_approbation`, MAD, 0 = jamais), la direction approuve
ou renvoie ; l'approbation se mesure **au cours figé** ; le cours se fige à la **première
confirmation des prix** ; la date promise se fixe à l'envoi et se fige avec les prix ; un bon se
modifie tant que rien n'est reçu.

Statuts (`modeles.py:542-549`) : `brouillon` « Brouillon », `a_approuver` « À approuver »,
`envoyee` « Envoyée », `confirmee` « Confirmée », `soldee` « Soldée », `annulee` « Annulée ».
**Parti** = a un `numero` (`est_parti`, l.60-65), quel que soit le statut.
Statut « parti » d'un bon (`_statut_parti`, l.197-198) : `confirmee` si toutes les lignes ont un
prix confirmé, sinon `envoyee`.

### A.4.1 Forme d'un bon (`commande_dict`, `achats.py:294-365`)

| Champ | Sens |
|---|---|
| `id`, `numero` (null si brouillon), `fournisseur_id`, `fournisseur`, `pays`, `contact`, `email` | identité ; les quatre derniers lus sur la fiche fournisseur |
| `date_commande` | ISO ; date de création pour un brouillon, date d'envoi ensuite |
| `date_livraison_prevue` | ISO ou null — date promise |
| `statut`, `statut_libelle` | code et libellé |
| `livraison` | état de livraison (`_statut_livraison`, l.78-100), "" si pas parti ; sinon « 🟢 Livré » (chaque ligne reçue à la tolérance `toler_in_full` près, net des retours, hors quarantaine), « ⚫ Soldé » / « ⚫ Soldé sans livraison », « ⚫ Annulé », « 🟡 Reçu sous réserve » (complet en comptant la quarantaine), « 🟡 En cours » / « 🟠 Partiel retard » (déjà reçu), « ⚪ Attendu » / « 🔴 En retard » (rien reçu). Retard = ETA, sinon date promise, + `toler_retard_jours` < aujourd'hui |
| `livree_le` | date de la dernière réception validée si « 🟢 Livré », sinon null |
| `derniere_reception_le` | date de la dernière réception validée |
| `devise`, `cours` (figé, 0/null avant confirmation), `taux_du_jour` | |
| `observations` | remarques au fournisseur (imprimées sur le bon) |
| `montant`, `montant_mad` | Σ quantité × prix des lignes **confirmées** ; × cours (figé sinon du jour) |
| `montant_estime`, `montant_estime_mad` | Σ quantité × prix estimé (confirmé, sinon catalogue converti dans la devise du bon) |
| `reste_kg`, `reste_estime_mad` | reste à livrer (0 si soldé/annulé ou ≤ tolérance) et sa valeur estimée en MAD |
| `quantite`, `recu`, `part_livree` | kg commandés, reçus nets, min(1, reçu/commandé) |
| `prix_a_confirmer` | nombre de lignes sans prix confirmé |
| `confirme_le` | plus récente confirmation de ligne |
| `seuil_approbation`, `approbation_requise` | seuil ; vrai si montant estimé MAD > seuil et pas encore approuvé |
| `expedition` | `{proforma_le, acompte_le, embarquee_le, eta, au_port_le, dedouanee_le, arrivee_usine_le, conteneur, navire}` |
| `cree_par`, `cree_le`, `approuvee_par`, `approuvee_le` | |
| `renvoi` | si statut brouillon/envoyée/confirmée et dernier geste de journal = « renvoi aux achats » : `{par, le, motif}` ; sinon null |
| `receptions` | `[{id, numero, date, statut}]` des réceptions (tous statuts) qui touchent le bon |
| `modifiable` | ni soldé/annulé, ni ligne déjà nommée par une réception (même brouillon/annulée) |
| `lignes` | voir ci-dessous |

Ligne : `id, article_id, reference, designation, kg_par_ml, unite_prix, quantite` (kg)`,
unite_achat, contenance, unites` (quantité / contenance)`, prix, prix_confirme, prix_catalogue`
(prix au kilo de la fiche, dans sa devise)`, devise_catalogue, montant` (si confirmé)`,
montant_estime, recu, en_quarantaine, reste, reste_estime, confirme_par, confirme_le`.

### A.4.2 Garde-fou du montant (`_controler_montant`, `achats.py:246-291`)

Après tout geste qui change le montant d'un bon :
- brouillon `a_approuver` sans numéro → redevient `brouillon` ; journal `retour en brouillon`
  « brouillon n° N · modifié pendant l'approbation (geste) · A MAD → B MAD » ;
- bon parti (`envoyee`/`confirmee`/`a_approuver` avec numéro) : approbation **requise** si
  seuil > 0, montant MAD (cours figé) > seuil, **et** montant > montant de référence × (1 +
  marge) + 0,005 — référence = montant de la **version partie** (`version_approuvee`, JSON
  `{montant, lignes:[{article_id, quantite, unite_achat, contenance, prix, prix_confirme,
  confirme_par, confirme_le}]}`), sinon montant approuvé MAD / cours, sinon montant d'avant ;
  marge = tolérance du geste (5 % pour les prix confirmés) sauf si le bon était parti sous le
  seuil (marge 0). Requise → statut `a_approuver`, approbation effacée, journal `commande à
  approuver` ; non requise → la version partie devient l'état actuel (montant de référence
  inchangé) ; un bon `a_approuver` qui n'en a plus besoin reprend son statut parti, journal
  `approbation plus nécessaire`. Une baisse ne repasse jamais par la direction.

### A.4.3 Routes

#### GET `/api/commandes` — Achats — l.368
Tous les bons, du plus récent (id décroissant).

#### POST `/api/commandes` — Achats — l.452 — 201
Corps `CommandeEntree` (l.387-393) : `fournisseur_id` int requis ; `date_livraison_prevue` date∣null
(vide : date d'envoi + délai fournisseur, comptée à l'envoi) ; `sans_prix` bool **true** ;
`observations` ≤ 2000 "" ; `lignes` ≥ 1 `LigneCommandeEntree` (l.379-384) : `article_id` int ;
`quantite` float > 0 ≤ 1e9 (kg) ; `unite_achat` ≤ 32 "kg" ; `contenance` float > 0 ≤ 1e9 défaut 1 ;
`prix` float∣null 0–1e7.
Contrôles (`_verifier_lignes`, `_verifier_unite`, l.411-449), 422 : « Fournisseur inconnu. » ;
« Matière inconnue dans la commande. » ; « « Réf » n'est pas fournie par ce fournisseur. »
(fournisseur de la fiche) ; « « Réf » figure deux fois : regrouper les quantités. » ; « « Réf » :
commandée en kg, la contenance vaut 1. » ; « « Réf » ne se commande pas en « U » : kg, Bobine,
Palette, … (fiche de la matière). » ; « « Réf » : une U contient X kg, pas Y (fiche de la
matière). » (tolérance 1e-6 relative). Unités permises (`unites_permises`, l.396-408) : `kg`
(1) ; `Bobine` (poids bobine) ; `Palette` (poids bobine × bobines/palette) ; l'unité d'achat
déclarée (≠ kg/ml) à sa contenance.
Effets : les lignes sont groupées par **devise de la matière** → un brouillon par devise (ordre
alphabétique), `numero` null, `date_commande` = aujourd'hui, statut `brouillon`, `cree_par`.
Prix des lignes : 0 si `sans_prix` ; sinon prix saisi, ou prix au kilo du catalogue. Journal
`création commande` « brouillon n° N · Fournisseur · K ligne(s) » par bon.
Réponse : **liste** des bons créés.

#### PUT `/api/commandes/{cid}` — Achats — l.639
Corps `ModificationCommande` (l.608-611) : `date_livraison_prevue` date∣null ; `observations`
≤ 2000 "" ; `lignes` ≥ 1 (`LigneCommandeEntree`). Verrou.
Refus : 404 « Commande introuvable. » ; 409 « Ce bon est clos. » (soldé/annulé) ; 409 « Ce bon a
déjà des réceptions : ses lignes ne se modifient plus. Créer un autre bon pour le complément, ou
le solder. » ; date promise (`_changer_promesse`, l.614-636, seulement si bon parti et date
différente non nulle) : 422 « La livraison promise (JJ/MM/AAAA) est figée depuis la confirmation
des prix : elle mesure la ponctualité. Noter la nouvelle date annoncée par le fournisseur dans
l'arrivée prévue (ETA) du suivi d'expédition. » ; 422 « La livraison était promise pour le …,
date passée : elle ne se repousse plus. … » ; 422 « La livraison prévue (…) précède la date du bon
(…). » ; contrôles de lignes ci-dessus (une ligne existante garde son conditionnement même si la
fiche a changé) ; 422 « Ce bon est en XXX : une matière d'une autre devise va sur un autre bon. »
Effets : lignes remplacées ; un prix confirmé n'est gardé confirmé que si le prix envoyé est
absent ou identique ; prix non fourni → ancien prix (0 pour une ligne nouvelle) ; statut parti
recalculé (une ligne nouvelle sans prix rend « envoyée ») ; journal `modification commande`
« NUM · A MAD → B MAD » ; garde-fou du montant (geste « lignes modifiées », tolérance 0).
Réponse : le bon.

#### POST `/api/commandes/{cid}/envoyer` — Achats — l.691
Corps facultatif `Envoi` {`date`: date∣null — jour réel du départ ; vide = aujourd'hui}.
Refus : 404 ; 409 « Ce bon attend l'approbation de la direction. » ; 409 « Ce bon est déjà
parti. » (statut ≠ brouillon). Si seuil > 0 et montant estimé MAD (cours figé, sinon du jour) >
seuil et non approuvé : 422 « La livraison prévue (…) est déjà passée : la corriger, ou la vider
(date d'envoi + délai du fournisseur). » sinon statut `a_approuver`, journal `commande à
approuver` « NUM · X MAD » — **sans numéro**. Sinon envoi (`_numeroter`, l.493-515) :
`date_permise(date d'envoi)` (422) ; promesse antérieure à l'envoi → 422 « La livraison prévue
(…) précède l'envoi du bon (…) : la corriger, ou la vider (date d'envoi + délai du
fournisseur). » ; promesse vide → envoi + `delai_jours` du fournisseur ; `date_commande` = jour
d'envoi ; numéro `BC-AAAA-NNNN` (année du jour d'envoi) ; statut parti ; `montant_approuve` =
montant MAD ; version partie figée (montant de référence) ; journal `envoi commande`.
Réponse : le bon.

#### POST `/api/commandes/{cid}/approuver` — Direction — l.719
Pas de corps. Refus : 404 ; 409 « Ce bon n'attend pas d'approbation. » ; si le bon n'a pas
encore de numéro, `date_permise(aujourd'hui)` (422, période close).
Effets : numérote à **aujourd'hui** si pas encore numéroté (une promesse déjà dépassée est
recomptée : aujourd'hui + délai) ; statut parti ; `approuvee_par`, `approuvee_le` ;
`montant_approuve` = montant MAD ; version partie figée ; journal `approbation commande` « NUM ·
X MAD approuvés » ; recalage du solde (un bon parti a pu être livré entre-temps → soldé, journal
`commande soldée` « NUM · tout reçu »). Réponse : le bon.

#### POST `/api/commandes/{cid}/renvoyer` — Direction — l.764
Corps `Renvoi` {`motif` str 3–500 requis}. Refus : 404 ; 409 « Seul un bon qui attend
l'approbation se renvoie aux achats. » ; 409 « Le bon NUM est parti, mais sa version d'alors
n'est pas connue : l'approuver, ou demander aux achats de le ramener à ce qui était accepté. »
Effets : brouillon → `brouillon`, journal `renvoi aux achats` « NUM · motif ». Bon parti →
lignes rétablies à la version partie (`_retablir`, l.743-761 : une ligne déjà reçue reste, avec
quantité et prix d'alors), statut parti, journaux `renvoi aux achats` et `version partie
rétablie` « NUM · X MAD : le bon reste chez le fournisseur tel qu'il était parti », recalage
du solde. Réponse : le bon (avec `renvoi`).

#### POST `/api/commandes/{cid}/prix` — Achats — l.808
Corps `ConfirmationPrix` (l.801-805) : `prix` liste ≥ 1 de {`ligne_id` int, `prix` float > 0 ≤ 1e7
(au kilo, devise du bon)} ; `mettre_a_jour_catalogue` bool **true** ; `date_livraison_prevue`
date∣null (date confirmée par le fournisseur).
Refus : 404 ; 409 « Ce bon est annulé. » ; refus de date promise (ci-dessus) ; 422 « Ligne
étrangère à ce bon. »
Effets : chaque ligne : prix, confirmé, `confirme_le`, `confirme_par` ; si catalogue : prix de
la fiche = prix × densité pour une fiche au mètre (sinon prix), `version`+1, `modifie_le/par` ;
**cours figé** au cours du jour à la première confirmation ; `envoyee` → `confirmee` si toutes
confirmées ; journal `prix confirmés` « NUM · N prix · A MAD → B MAD » ; garde-fou (geste
« prix confirmés », tolérance 5 %) — sauf pour un brouillon `a_approuver` sans numéro.
Possible aussi sur un brouillon, un bon soldé. Réponse : le bon.

#### PUT `/api/commandes/{cid}/expedition` — Achats — l.865
Corps `Expedition` (l.846-855) : `proforma_le, acompte_le, embarquee_le, eta, au_port_le,
dedouanee_le, arrivee_usine_le` (date∣null) ; `conteneur` ≤ 60 "" ; `navire` ≤ 80 "".
**Tous les champs sont remplacés** (absent = effacé). Refus : 404 ; 409 « Ce bon n'est pas encore
parti : son expédition se suit après l'envoi. » ; 422 « « Proforma reçue le | Acompte payé le |
Embarquée le | Arrivée au port le | Dédouanée le | Arrivée à l'usine le » ne se date pas dans le
futur : c'est un fait constaté. Une date attendue va dans l'arrivée prévue (ETA). » (l'ETA seule
peut être future). L'ETA remplace la date promise dans la prévision et le jugement de retard.
Journal `expédition` « NUM · ETA JJ/MM/AAAA » ou « NUM ». Réponse : le bon.

#### POST `/api/commandes/{cid}/solder` — Achats — l.887
Refus : 404 ; 409 « Ce bon est déjà clos. » ; 409 « Le bon NUM attend l'approbation de la
direction : elle l'approuve ou le renvoie aux achats (il revient à sa version partie) ; il se
solde ensuite. » ; 409 « Ce bon n'est pas parti : il se supprime, il ne se solde pas. »
Effets : `soldee` si une réception **validée** l'a servi (même renvoyée depuis), sinon
`annulee` ; journal `commande soldée` ou `commande annulée` « NUM » (sans « tout reçu » : solde
« à la main », qui ne se rouvre jamais seul). Réponse : le bon.

#### POST `/api/commandes/{cid}/rouvrir` — Achats — l.909
Refus : 404 ; 409 « Ce bon n'est pas clos. » Effets : statut parti (numéroté) ou `brouillon` ;
journal `commande rouverte` ; garde-fou du montant (geste « réouverture ») pour un bon parti.
Réponse : le bon.

#### DELETE `/api/commandes/{cid}` — Achats — l.924
Refus : 404 ; 409 « Ce bon a des réceptions : le solder plutôt que le supprimer. » ; 409 « Le bon
NUM est parti chez le fournisseur : l'annuler plutôt que le supprimer (il garde son numéro, la
série reste sans trou). » Journal `suppression commande` « brouillon n° N ». Réponse `{"ok": true}`.

#### GET `/api/commandes/{cid}/impression` — Achats — l.1035
Document HTML décrit en A.10. Refus 404 « Commande introuvable. »

### A.4.4 Recalage automatique des soldes (`recaler_soldes`, `achats.py:572-605`)

Appelé par approuver, renvoyer, valider/annuler une réception (et, hors périmètre, retours
fournisseur et sorties de quarantaine) : un bon `envoyee`/`confirmee` livré ligne par ligne
(tolérance, net des retours, hors quarantaine) → `soldee`, journal `commande soldée` « NUM · tout
reçu » ; un bon `soldee` qui n'est plus livré se rouvre (journal `commande rouverte` « NUM ·
raison : le reçu net ne couvre plus le bon ») seulement si son dernier solde était « tout reçu »,
ou, sans trace (bon repris), si la pesée brute le couvrait (ce sont des retours qui l'ont
dégarni). Un bon soldé à la main reste soldé ; un bon `a_approuver` ne bouge pas.

## A.5 Réceptions (`api/receptions.py`)

Doctrine (`receptions.py:1-17`) : un camion = une réception, une ou plusieurs commandes du
même fournisseur et de la même devise. Un brouillon se corrige, se supprime, et se **recale** à
chaque lecture (reste à livrer, prix confirmé). La validation écrit tout d'un coup : numéro,
lots, entrées en stock, prix payés. Qualités de ligne (`QUALITES`, l.44) : `conforme`
« Conforme », `reserve` « Sous réserve » (entre en **quarantaine** : en stock, pas disponible),
`refuse` « Refusé » (n'entre pas ; le fournisseur la doit). Une réception entièrement refusée
se valide quand même (trace du camion renvoyé). On ne reçoit que sur un bon **parti**, non
annulé, et pas avant sa date d'envoi ; sinon hors commande. La facture se complète même après
validation (sans toucher au stock).

### A.5.1 Corps

`ReceptionEntree` (l.351-358) :

| Champ | Type | Défaut | Contraintes |
|---|---|---|---|
| `date` | date | requis | pas dans le futur (422 « Une réception ne se date pas dans le futur. ») ; période close contrôlée à la validation |
| `fournisseur_id` | int | requis | doit exister (422 « Fournisseur inconnu. ») |
| `numero_bl` | str | "" | ≤ 64 |
| `controle_par` | str | "" | ≤ 80 (contrôleur qualité, texte libre) |
| `facture` | `FactureEntree` ∣ null | null | voir ci-dessous |
| `observations` | str | "" | ≤ 2000 |
| `lignes` | liste de `LigneEntree` | requis | ≥ 1 |

`LigneEntree` (l.330-348) :

| Champ | Type | Défaut | Contraintes / sens |
|---|---|---|---|
| `id` | int ∣ null | null | **ignoré** (les lignes sont toujours recréées) |
| `commande_ligne_id` | int ∣ null | null | ligne de bon imputée ; null = hors commande |
| `article_id` | int | requis | doit exister |
| `lot_numero` | str | "" | ≤ 80 ; lot de l'étiquette, ou « LOT INTERNE » (numéro donné à la validation) |
| `quantite_bl` | float | 0 | 0–1e9 ; kg annoncés par le bon de livraison |
| `quantite_pesee` | float | 0 | 0–1e9 ; kg pesés (> 0 exigé à la validation, sauf refus) |
| `nb_palettes` | float | 0 | 0–1e5 |
| `bobines_en_plus` | float | 0 | 0–1e6 ; bobines hors palettes complètes |
| `magasin_id` | int ∣ null | null | magasin de rangement (forcé à la quarantaine pour `reserve`) |
| `qualite` | str | "conforme" | `conforme` / `reserve` / `refuse` |
| `observations` | str | "" | ≤ 300 |
| `prix` | float ∣ null | null | 0–1e7 ; prix payé **au kilo** dans la devise de la ligne (l'écran ramène un prix au mètre au kilo ; le commentaire du code, l.342-344, dit « dans l'unité de la matière », mais rien ne convertit côté serveur) quand le bon n'en confirme pas ; null = catalogue au kilo |
| `devise` | str | "" | ≤ 3 ; hors commande : devise du prix (défaut : celle du fournisseur) ; sur un bon : doit être celle du bon |

`FactureEntree` (l.322-327) : `numero` ≤ 64 "" (vide = pas de facture), `date` date∣null,
`montant` float 0–1e10, `devise` ≤ 3 "", `echeance` date∣null.

Construction des lignes (`_lignes`, l.390-438), refus 422 : « Matière inconnue dans la
réception. » ; « Qualité : conforme, réserve ou refusé. » ; « Magasin inconnu. » ; « Ligne de
commande inconnue. » ; « La commande NUM n'est pas de Fournisseur : une réception ne mêle pas deux
fournisseurs. » ; « « Réf » n'est pas sur la ligne choisie de NUM. » ; problème du bon
(`probleme_du_bon`, l.108-119) : « Le brouillon n° N n'est pas encore parti chez le fournisseur :
le marquer comme envoyé (il reçoit son numéro), ou recevoir hors commande. » / « Le bon NUM est
annulé : le rouvrir, ou recevoir hors commande. » / « La réception du JJ/MM/AAAA précède l'envoi
du bon NUM (JJ/MM/AAAA) : la date de l'une ou de l'autre est fausse. » ; « Le bon NUM est en XXX :
sa réception aussi. » ; « Devise inconnue : XXX. » (hors commande).
Prix d'une ligne : sur un bon, prix saisi sinon catalogue **converti dans la devise du bon**
(`prix_catalogue_en`, `achats.py:153-160`, au cours du jour), et le **prix confirmé du bon
l'emporte toujours** ; hors commande, prix saisi sinon catalogue converti dans la devise choisie.
`nb_bobines` = palettes × bobines/palette (fiche) + bobines en plus.
Devise de la réception (`devise_des_lignes`, l.70-77) : une seule ; sinon 422 « Une réception ne
mêle pas deux devises (A, B) : chaque devise a sa facture. Enregistrer une réception par devise
(même BL, même date). »

Facture à la création/modification (`_facture`, l.361-387) : si numéro non vide, la facture
`(fournisseur, numéro)` est reprise ou créée ; 422 « Cette réception est en XXX : sa facture aussi.
Une facture en YYY va sur la réception de cette devise. » ; 422 « La facture N est en XXX ; cette
réception est en YYY. Une facture n'a qu'une devise : saisir la facture de cette devise. » ;
devise = celle des lignes ; date, montant, échéance écrits **seulement s'ils sont fournis non
nuls** ; échéance par défaut = date + `delai_paiement_jours` du fournisseur.

### A.5.2 Forme d'une réception (`reception_dict`, l.201-289)

`id, numero` (null en brouillon)`, statut` (`brouillon`/`validee`/`annulee`)`, date,
fournisseur_id, fournisseur, delai_paiement_jours, devise_fournisseur, numero_bl, devise` (des
lignes, sinon du fournisseur)`, annulation` ({par, le, motif} pour une annulée, d'après le journal)`,
facture` ({id, numero, date, montant, devise, echeance, payee_le} ou null)`, observations,
commandes` (numéros des bons touchés)`, commandes_ids, cree_par, cree_le, controle_par,
validee_par, validee_le, pese` (Σ kg pesés hors refus)`, en_dossier` (bool)`, dossier` ({id,
numero, statut} du dossier d'importation qui la porte, ou null)`, blocages` (brouillon : liste des
refus de validation annoncés, sinon [])`, avertissements` (brouillon), `lignes`.

Ligne : `id, commande_ligne_id, commande` (numéro)`, commande_id, quantite_commandee,
deja_recu` (reçu net du bon par d'autres réceptions)`, prix_confirme` (bool)`, article_id,
reference, designation, kg_par_ml, poids_bobine_catalogue, bobines_palette, lot_numero,
quantite_attendue` (reste à livrer recalé)`, quantite_bl, reste_apres, quantite_pesee,
nb_palettes, bobines_en_plus, nb_bobines, poids_moyen_bobine, ecart, ecart_relatif` (pesé
− attendu ; attendu = BL, sinon reste à livrer **si** la pesée atteint ce reste à la tolérance
`toler_ecart_pesee` près ; sinon pas d'écart)`, magasin_id, magasin` (code)`, qualite,
qualite_libelle, observations, prix, devise, lot_id, retourne` (kg repartis chez le fournisseur,
au prorata)`.

Blocages (`blocages`, l.122-179) — la même liste annonce et refuse : refus de `date_permise` ;
problème du bon ; excédent : Σ pesé (tous lots) d'une ligne de bon > reste + `toler_excedent` ×
quantité de la ligne → « « Réf » : X kg reçus [(tous lots ensemble) ]pour Y kg restant à livrer sur
NUM (excédent toléré : Z % de la ligne). Recevoir le surplus sur une ligne hors commande, ou faire
corriger le bon. » ; inventaire ouvert sur le magasin cible (ou global) « L'inventaire N est en
cours : les entrées y sont suspendues jusqu'à sa validation. » ; « « Réf » : la pesée est à zéro.
La saisir, ou marquer la ligne « refusé ». » ; « « Réf » : le numéro de lot manque (celui de
l'étiquette, ou « Lot interne »). » ; « Une ligne sous réserve va en quarantaine : créer d'abord un
magasin de type « Quarantaine » (Réglages › Magasins). » ; « « Réf » : choisir le magasin de
rangement. » (les lignes refusées ne sont contrôlées que sur le bon).
Avertissements (`avertissements`, l.182-198) : bon soldé « Le bon NUM est soldé : il n'attend plus
rien. Le rouvrir si le fournisseur le complète vraiment, sinon recevoir hors commande. » ; bon
parti repassé par la direction « Le bon NUM est parti, mais une modification attend
l'approbation de la direction : la réception s'impute à ses lignes d'aujourd'hui. Si elle la
refuse, le bon revient à sa version partie. »

### A.5.3 Routes

#### GET `/api/receptions` — Achats — l.309
Toutes, id décroissant ; les brouillons sont recalés **en mémoire** (rien n'est enregistré).

#### POST `/api/receptions` — Achats — l.441 — 201
Effets : réception brouillon (`numero` null), facture éventuelle, recalage, journal `création
réception` « brouillon n° N · Fournisseur · K ligne(s) ». Réponse : la réception.

#### PUT `/api/receptions/{rid}` — Achats — l.470
Verrou. Refus : 404 « Réception introuvable. » ; 409 « Une réception validée est entrée en stock :
elle ne se modifie plus. L'annuler (elle se contre-passe), puis en saisir une nouvelle. » ;
mêmes contrôles qu'à la création. Effets : tout remplacé (lignes recréées) ; journal
`modification réception`. Réponse : la réception.

#### DELETE `/api/receptions/{rid}` — Achats — l.497
Refus : 404 ; 409 « Une réception validée ne se supprime pas : l'annuler. » Journal `suppression
réception`. Réponse `{"ok": true}`.

#### POST `/api/receptions/{rid}/valider` — Achats — l.510
Refus : 404 ; 409 « Cette réception est déjà validée. » (tout statut ≠ brouillon) ; 422
`date_permise` ; 422 **premier** blocage.
Séquence : verrou des bons puis des lignes de bon touchés (ordre d'id) et relecture ; recalage ;
blocages ; lignes `reserve` → magasin Quarantaine (le premier actif, par id) ; `LOT INTERNE`
(casse ignorée) → `numero_lot_interne` (série LOT, rattrape d'abord le plus grand `LOT-AAAA-NNNN`
existant) ; numéro `REC-AAAA-NNNN` (année de la réception) ; pour chaque ligne non refusée :
lot `(article, numéro)` repris ou créé (`entre_le` = date, fournisseur, poids de bobine = pesé /
bobines) et **mouvement de stock** `RECEPTION` (+ pesé, magasin, date de la réception, prix et
devise de la ligne, **cours** = cours figé du bon s'il est dans la même devise, sinon du jour ;
document `reception`, commentaire « sous réserve » le cas échéant) — refus possibles de
`stock.ecrire` (magasin désactivé, inventaire ouvert 409…) ; statut `validee`, `validee_par/le` ;
recalage des soldes des bons ; journal `validation réception` « REC-… · N entrée(s) » ou « … · tout
refusé, rien n'entre en stock ». Réponse : la réception.

#### POST `/api/receptions/{rid}/annuler` — Achats — l.581
Corps facultatif `Annulation` {`motif` ≤ 300 ""}. Refus : 404 ; 409 « Seule une réception validée
s'annule ; un brouillon se supprime. » ; 409 si un dossier d'importation la porte : « Cette
réception est dans le dossier d'importation NUM : pour l'annuler, [le rouvrir (c'est tracé),
puis ]l'en détacher d'abord (dossier NUM › Marchandises › « Détacher la réception ») — ses frais
restent au dossier, et la marchandise y reviendra par sa facture. » ; refus de la
contre-passation (matière déjà sortie : 409 « Le lot … ne porte que … », période close 422,
inventaire ouvert 409, « Ce document a déjà été annulé. » 409).
Effets : **contre-passation** de chaque mouvement de la réception, datée comme l'original
(`stock.contrepasser_document`) ; statut `annulee` ; recalage des soldes (raison « réception
annulée ») ; journal `annulation réception` « REC-… · motif » (« sans motif » par défaut).
Le numéro REC est conservé. Réponse : la réception.

#### PUT `/api/receptions/{rid}/facture` — Achats — l.614
Corps `FactureComplete` (l.604-611) : `numero` ≤ 64 "" ; `date` date∣null ; `montant` 0–1e10 ;
`devise` ≤ 3 "" ; `echeance` date∣null — **chaque champ remplace l'ancien** (montant 0 efface).
Refus : 404 ; 409 « Cette réception est annulée : sa facture ne se modifie plus. » ; 409 si le
numéro change alors qu'un dossier la porte : « La date, le montant et l'échéance de la facture N
se corrigent ici ; son numéro, non. » + chemin de détachement ; 422 « L'échéance ne précède pas la
date de la facture. » ; 422 devise ≠ devise unique des lignes ; 422 « Devise inconnue : XXX. » ; 409
« La facture N est en XXX et porte d'autres réceptions : elle ne change pas de devise. »
Effets : numéro vide → facture détachée (journal `facture détachée`) ; sinon facture
`(fournisseur, numéro)` reprise ou créée, date/montant/devise écrits, échéance = saisie, sinon
date + délai de paiement du fournisseur, sinon vide ; journal `facture complétée` « REC-… ·
facture N[ · 12 345.00 XXX] ». Permis aussi sur un brouillon. Réponse : la réception.

#### POST `/api/lots/numero-interne` — Achats — l.665
Pas de corps. Prend **tout de suite** le numéro suivant de la série LOT de l'année en cours
(`LOT-AAAA-NNNN`) et l'enregistre. Réponse `{"numero": "LOT-2026-0043"}`. Utilisée par les
écrans Opérations et Inventaire (bouton « Lot interne »).

#### GET `/api/factures` — Achats — l.673
Toutes les factures, id décroissant : `{id, fournisseur_id, fournisseur, numero, date, montant,
devise, echeance, payee_le}`. (Non appelée par l'écran ; utilisée par les essais.)

## A.6 Brouillons (`api/brouillons.py`)

Vue transversale des **ordres de fabrication** (`BonSortie` statut `brouillon`) et des
**opérations de stock** (`Operation` statut `brouillon`) en attente de validation.

#### GET `/api/brouillons` — tout rôle — l.73
Réponse `{"lignes": [...], "nombre", "bloques" (lignes avec blocages), "validables" (lignes que
ce compte peut valider et sans blocage)}`. Ligne :
- ordre : `{genre: "ordre", type: "ordre", id, date, libelle: "Ordre de fabrication", resume:
  "QUALITE 120 m², … · N lot(s)" (ou « hors recette »), quantite (Σ kg), cree_par, cree_le,
  blocages (production.blocages_bon), peut_valider, lien: "/sorties?onglet=brouillon&ordre=ID"}` ;
- opération : `{genre: "operation", type: <ouverture|retour_machine|transfert|ajustement|
  retour_fournisseur>, id, date, libelle (TYPES_OPERATION : « Stock d'ouverture », « Retour des
  machines », « Transfert entre magasins », « Ajustement justifié », « Retour au fournisseur »),
  resume ("motif · REF1, REF2 + n"), quantite, cree_par, cree_le, blocages
  (operations.blocages_operation), peut_valider, lien: "/operations?onglet=TYPE&operation=ID"}`.
Tri : date, puis rang du type le même jour (ouverture 0, transfert 1, ajustement 2, ordre 3,
retour_machine 4, retour_fournisseur 5), puis id.
`peut_valider` (`_peut`, l.30-35) : direction toujours ; un ordre : alimentation seule ; une
opération : rôles de `operations.QUI` (ouverture, ajustement, retour fournisseur : achats ;
retour machine : alimentation ; transfert : achats et alimentation).

#### POST `/api/brouillons/valider` — tout rôle (`STOCK`) — l.96
Corps facultatif `Selection` {`brouillons`: liste ≤ 1000 de `Choix` {`genre` pattern
`^(ordre|operation)$`, `id` int}} — vide/absent : **tout ce que ce compte peut valider**.
Effets : dans l'ordre de la liste, chaque brouillon validé par la même fonction que la
validation à l'unité (`production.valider_bon`, `operations.valider`), chacun dans sa
transaction ; un refus (`HTTPException`) ou une panne → `rollback` et passage au suivant.
Réponse `{"valides": [{genre, type, id, date, libelle, resume, lien, numero}], "refuses":
[{…, raison}] (« erreur inattendue : … » pour une panne), "ignores": (nombre demandé − nombre
retenu ; 0 sans sélection)}`. Les ids demandés que ce compte ne peut pas valider sont ignorés
en silence (comptés dans `ignores`).

## A.7 Dossiers d'importation (`api/importations.py`)

Doctrine (`importations.py:1-31`) : **un dossier = une facture = une livraison**. Le dossier
s'ouvre depuis la facture d'une réception validée et prend toute sa marchandise ; une facture
n'a qu'un dossier (un second camion de la même facture le rejoint). Seul un dossier d'avant la
mise en service se saisit à la main, sans facture. Un dossier repris de l'ERP Fil peut mêler
plusieurs factures. Une marchandise reçue ne sort qu'avec toute sa réception (« détacher ») ;
les frais restent au dossier. Frais répartis selon la **clé du poste** (valeur par défaut,
poids pour le fret/la manutention) ; la TVA récupérable reste hors coût. La marchandise entre à
**pesée × prix** (pas au montant de la facture). Quatre contrôles : TVA attendue, droits
attendus, frais aberrants, facture rapprochée. Statuts : `ouvert`, `clos`.
Fournisseur **local** (`_local`, l.109-113) : pays MAROC/MOROCCO/MA, ou pays vide et devise MAD.

### A.7.1 Forme d'un dossier (`dossier_dict`, l.190-355)

Calcul par `moteur.revient_dossier` (partie calculs) sur une vue du dossier (lignes : quantité,
valeur en devise, devise, cours ; frais : poste, montant, ligne visée, clé et nature du poste,
parts figées ; facture et son montant).

| Champ | Sens |
|---|---|
| `id, numero, libelle, date_arrivee, banque, statut, commentaire` | en-tête |
| `facture` | `{id, numero, fournisseur, date, montant, devise, echeance}` ou null |
| `a_la_main` | dossier sans facture (d'avant mise en service ou repris) |
| `clos_le` | ISO minute |
| `nb_lignes, nb_charges` | |
| `poids` | Σ kg des marchandises |
| `marchandise_mad` | Σ valeur MAD (valeur devise × cours de la ligne, sinon du jour ; MAD tel quel) |
| `charges_mad` | frais hors TVA **répartis** |
| `tva_mad` | TVA (récupérable) répartie ; `tva_saisie_mad` = Σ frais du poste `TVA` |
| `taux_tva_import` | réglage |
| `tva_attendue_mad`, `tva_ecart_tolere_mad` | TVA attendue (taux × (valeur en douane + droits + TPI)), null sans marchandise ; écart toléré |
| `droits_mad` | Σ frais du poste `DD` |
| `droits_attendus_mad` | Σ valeur en douane (marchandise + FRET + ASSUR répartis) × taux du code douanier — **seulement si toutes** les matières ont un code actif, sinon null |
| `matieres_sans_code`, `matieres_code_inactif` | références |
| `revient_mad` | marchandise + frais hors TVA |
| `decaisse_mad` | revient + TVA |
| `surcout` | frais / marchandise |
| `seuil_surcout`, `surcout_aberrant` | réglage `seuil_surcout_import` ; frais > marchandise × seuil (C35) |
| `lignes_aberrantes`, `lignes_negatives` | références dont les frais passent le seuil ; dont le coût est négatif |
| `ecart_facture` | `{facture, montant, recu (Σ valeur devise), devise, ecart, part, tolerance, hors_tolerance}` ou null (sans montant, sans marchandise, ou devises différentes) |
| `lignes_cours_bon` | lignes au cours figé de leur bon |
| `cours_disparates` | `[{devise, cours: [...]}]` quand une devise a plusieurs cours |
| `charges_non_reparties_mad`, `tva_non_repartie_mad` | frais sans marchandise où se poser |
| `fournisseurs, factures, receptions` | listes triées |
| `pieces` | `[{facture, receptions: [...]}]` |
| `familles` | par famille (« composition type titrage », sans couleur) : `{famille, references (nombre), lots, quantite (kg), valeur_mad, charges_mad, revient_mad, valeur_unite, revient_unite}`, triées par kg décroissant |
| `lignes` (détail) | voir ci-dessous |
| `charges` (détail) | `{id, poste, libelle, recuperable, cle, montant, ligne_id, piece, commentaire, prestataire, date_piece, echeance, payee_le, parts: [{ligne_id, montant}]}` |
| `echeancier` (détail) | factures de marchandise `{echeance, nature: "marchandise", quoi: "Facture N", tiers, piece, date_piece, montant (saisi, sinon apporté = Σ valeur devise, alors estime=true), estime, payee_le, devise}` et frais `{…, nature: "frais", quoi: libellé du poste, tiers: prestataire, montant, estime: false, devise: "MAD", charge_id}`, triés par échéance (sans échéance en dernier) |

Ligne (détail) : `id, reception_ligne_id, famille, article_id, reference, lot, fournisseur,
reception, reception_id, facture, quantite, poids_kg, valeur_devise, devise, cours` (saisi ;
0/null = cours du jour)`, cours_applique` (1 pour MAD)`, cours_jour, cours_bon` (cours figé du bon
si même devise)`, bon` (numéro)`, valeur_mad, part, charges_mad, tva_mad, revient_mad,
valeur_unite, revient_unite, surcout, detail` ({poste: MAD})`, revient_kg, aberrante,
negative, commentaire, code_douanier, taux_droits, valeur_douane_mad, droits_attendus_mad`.

### A.7.2 Routes

#### GET `/api/dossiers` — Achats — l.396
Tous les dossiers (sans `lignes`, `charges`, `echeancier`), triés par date d'arrivée
décroissante (vides en dernier) puis id décroissant.

#### GET `/api/dossiers/{did}` — Achats — l.401
Un dossier complet. 404 « Dossier introuvable. »

#### GET `/api/dossiers-a-rattacher` — Achats — l.436
Requête `locaux` bool (défaut false : écarter les fournisseurs marocains).
Marchandise libre = lignes de réceptions **validées**, non refusées, pesée > 0, dans aucun
dossier (`_lignes_libres`, l.409-433). Réponse :
- `factures` : par facture `{facture_id, numero, fournisseur, date (plus ancienne réception),
  receptions: [numéros], lignes, quantite (kg), valeurs: {devise: Σ pesé × prix}, devises,
  familles: [{famille, quantite}], detail: [lignes], local, dossier_id, dossier}` (dossier qui
  porte déjà la facture : la suite le rejoint), triées par date décroissante ;
- `sans_facture` : par réception sans facture `{reception_id, reception, date, fournisseur,
  numero_bl, local, lignes, quantite, valeurs}` ;
- `lignes` : toutes les lignes libres `{local, reception_ligne_id, reception_id, reception, date,
  fournisseur, facture_id, facture, reference, famille, lot, quantite, prix, valeur_devise,
  devise}` ;
- `locaux` : `{factures, lignes}` écartées.

Corps `DossierEntree` (l.512-529) : `numero` ≤ 16 "" (vide → `NN/AA` de la série DOS de
l'année d'arrivée ; saisi → doit être libre) ; `libelle` ≤ 160 "" ; `date_arrivee` date∣null
(validateur : année 2000–2100, « date d'arrivée hors période ») ; `banque` ≤ 32 "" ;
`commentaire` ≤ 2000 "" ; `facture_id` int∣null ; `local_confirme` bool false.

#### POST `/api/dossiers` — Achats — l.593 — 201
Refus : 404 « Facture inconnue. » ; 409 facture déjà portée (`_deja_porte`, l.180-187) : « Cette
facture a déjà son dossier, NUM : un dossier par facture. Ce qui en reste à rattacher (un second
camion) s'y ajoute. » ou « La facture N est déjà dans le dossier NUM (repris de l'ancien ERP) : une
facture ne se partage pas entre deux dossiers. Ce qui en reste à rattacher s'y ajoute. » ; 409
« Fournisseur est un fournisseur marocain : ni douane, ni fret international, sa facture N n'a
normalement pas de dossier d'importation. L'ouvrir quand même se confirme. » (sans
`local_confirme`) ; 409 « La facture « N » n'a plus de marchandise à rattacher : elle est déjà dans
un dossier, ou ses réceptions ne sont pas validées. » ; 409 période close (« ouverture du
dossier ») ; 409 « Le dossier « X » existe déjà. » ; 409 concurrence (`_refus_concurrent`) : « Un
autre poste vient d'enregistrer cette facture dans le dossier NUM : l'ouvrir pour la suite (rien
n'est perdu). » ou « Un autre poste vient d'enregistrer la même chose (même numéro de dossier, ou
même marchandise) : recharger la page, puis reprendre. »
Effets : dossier `ouvert` ; date d'arrivée = saisie, sinon plus ancienne réception, sinon
aujourd'hui ; libellé par défaut « Fournisseur — facture N » ; chaque ligne libre de la facture
entre (`_rattacher`, l.532-546) avec `quantite` = `poids_kg` = pesé, `valeur_devise` = pesé ×
prix, devise, **cours = cours figé du bon** (même devise, hors MAD) sinon 0, lot, fournisseur ;
journal `ouverture dossier` « NUM · N ligne(s) · facture F | saisi à la main[ · fournisseur
marocain, confirmé] ». Réponse : le dossier complet.

#### PUT `/api/dossiers/{did}` — Achats — l.641
Corps `DossierEntree` (seuls `libelle`, `banque`, `commentaire` et `date_arrivee` non nulle sont
pris ; `numero`, `facture_id`, `local_confirme` ignorés). Refus : 404 ; 409 « Ce dossier est clos :
le rouvrir pour y toucher (c'est tracé). » Journal `modification dossier`. Réponse : le dossier.

#### POST `/api/dossiers/{did}/rattacher` — Achats — l.658
Corps `Rattachement` {`facture_id` int∣null ; `reception_lignes` liste d'int (défaut [])}.
Factures acceptées : celle du dossier ; pour un dossier repris sans facture, celles qu'il porte
déjà. Refus : 404 / 409 clos ; 409 « Ce dossier est saisi à la main (d'avant la mise en service) :
une marchandise reçue entre par sa facture, dans le dossier de cette facture. » ; 409 « Un
dossier, une facture : NUM est celui de la facture F. La facture G ouvre son propre dossier. » ;
409 « Le dossier NUM, repris de l'ancien ERP, ne prend que la suite des factures qu'il porte déjà.
La facture G ouvre son propre dossier. » ; 409 facture sans marchandise libre ; 409 « Une des
lignes choisies est déjà dans un dossier, ou n'est pas une réception validée. » ; 409 ligne d'une
autre facture ; 422 « Rien à rattacher. » ; 409 période close (« rattachement ») ; 409
concurrence. Effets : lignes entrées comme à l'ouverture ; journal `marchandises dossier` « NUM ·
N ligne(s)[ · plusieurs cours : USD à 10 et 10.2] ». Réponse : le dossier.

#### POST `/api/dossiers/{did}/ligne-manuelle` — Achats — l.727
Corps `LigneManuelle` (l.714-724) : `article_id` int ; `lot_numero` ≤ 80 "" ; `fournisseur_id`
int∣null (défaut : celui de la matière) ; `quantite` float > 0 ≤ 1e9 (kg) ; `valeur_devise` float
0–1e10 requis ; `devise` ≤ 3 "MAD" ; `cours` 0–1000 défaut 0 ; `commentaire` ≤ 300 "".
Refus : 404 / 409 clos ; 409 « Le dossier de la facture F porte ce qu'elle a apporté, tel que reçu :
la saisie à la main est réservée aux dossiers d'avant la mise en service. » ; 409 « Le dossier NUM
porte des réceptions : … » ; 422 « Matière inconnue. » ; 409 « Le lot « L » de REF est arrivé par la
réception REC : son coût vient du dossier de sa facture. La saisie à la main ne vaut que pour un
lot d'avant la mise en service. » ; 422 « Devise inconnue : « X ». » ; 422 « Fournisseur inconnu. » ;
409 période close (« marchandise saisie à la main », date d'entrée du lot).
Effets : lot créé s'il est inconnu (sans stock ; `entre_le` = arrivée ou aujourd'hui) ; ligne
(cours forcé à 0 en MAD) ; journal `marchandise saisie à la main` « NUM · REF[ · lot L] ».
Réponse : le dossier.

#### PUT `/api/dossiers/{did}/lignes/{lid}` — Achats — l.786
Corps `LigneModif` : `cours` float∣null 0–1000 ; `commentaire` str∣null ≤ 300 (null = inchangé).
Refus : 404 / 409 clos ; 404 « Marchandise introuvable dans ce dossier. » ; 422 « Une marchandise
facturée en MAD n'a pas de cours. » ; 409 période close (« cours ») si le cours change.
Journal `cours` « NUM · REF · cours » et/ou `commentaire marchandise`. Réponse : le dossier.

#### PUT `/api/dossiers/{did}/cours` — Achats — l.814
Corps `CoursEntree` : `cours` float 0–1000 requis ; `devise` ≤ 3 ∣ null (défaut : l'unique devise
étrangère du dossier). Refus : 404 / 409 clos ; 422 « Le dossier mêle EUR, USD : donner le cours
de chaque devise à part. » ; 422 « Aucune marchandise en devise dans ce dossier. » ; 422 « Aucune
marchandise en XXX dans ce dossier. » ; 409 période close. Effets : cours écrit sur toutes les
lignes de la devise ; journal `cours` « NUM · USD à 10.2 ». Réponse : le dossier.

#### POST `/api/dossiers/{did}/cours-des-bons` — Achats — l.835
Refus : 404 / 409 clos ; 409 période close ; 422 « Aucune ligne de ce dossier ne vient d'un bon
au cours figé. » Effets : chaque ligne venue d'un bon au cours figé (même devise, hors MAD) reprend
ce cours ; journal `cours` « NUM · cours des bons sur N ligne(s) ». Réponse : le dossier.

#### DELETE `/api/dossiers/{did}/lignes/{lid}` — Achats — l.853
Seulement une marchandise **saisie à la main**. Refus : 404 / 409 clos ; 404 marchandise ; 409
« Une marchandise reçue ne sort pas seule du dossier : elle sort avec toute sa réception REC
(« Détacher la réception »), et les frais restent au dossier. » ; 409 « N frais porte(nt) sur
cette seule marchandise : les affecter à tout le dossier, ou les retirer, avant de la retirer. » ;
409 période close. Journal `marchandise retirée`. Réponse : le dossier.

#### POST `/api/dossiers/{did}/detacher` — Achats — l.887
Corps `Detachement` {`reception_id` int}. Refus : 404 / 409 clos ; 404 « Réception inconnue. » ;
404 « La réception REC n'est pas dans le dossier NUM. » ; 409 « N frais porte(nt) sur une
marchandise de la réception REC : les affecter à tout le dossier (onglet Frais, « Porte sur »)
avant de la détacher — sinon ils sortiraient avec elle. » ; 409 période close.
Effets : toutes les lignes de la réception sortent ; les parts figées de tout frais qui en avait
une sont effacées (le frais se répartit de nouveau à la clé de son poste) ; journal `réception
détachée` « NUM · REC · N ligne(s) · K frais gardés (X MAD) ». Le dossier reste ouvert.
Réponse : le dossier.

Corps `ChargeEntree` (l.928-943) : `poste` ≤ 16 requis (doit exister) ; `montant` float
−1e9…1e9 requis, non nul (avoir en négatif) ; `ligne_id` int∣null (frais visé sur une seule
marchandise du dossier ; null = tout le dossier) ; `piece` ≤ 64 "" ; `commentaire` ≤ 300 "" ;
`prestataire` ≤ 120 "" ; `date_piece`, `echeance` date∣null (validateur 2000–2100 « date hors
période »). Refus communs (`_verifier_charge`, l.946-953), 422 : « Poste de frais inconnu : « X »
(attendu : DD, TPI, …). » ; « Un frais a un montant (un avoir se saisit en négatif). » ; « La
marchandise visée n'appartient pas à ce dossier. » ; après écriture (`_refuser_negatif`) 409 « Ce
frais rendrait REF négatif (X MAD) : un avoir ne dépasse pas ce que la marchandise a coûté. Le
porter sur tout le dossier, ou revoir son montant. »

#### POST `/api/dossiers/{did}/charges` — Achats — l.978
Refus : 404 / 409 clos ; ci-dessus ; 409 période close (« frais »). Journal `frais` « NUM · POSTE
1,234.56 ». Réponse : le dossier.

#### PUT `/api/dossiers/{did}/charges/{cid}` — Achats — l.991
Refus : 404 « Frais introuvable dans ce dossier. » ; ci-dessus ; période close si poste, montant
ou ligne visée changent. Effet : un frais à parts figées dont le montant (> 0,005) ou la ligne
visée change perd ses parts. Journal `frais modifié`. Réponse : le dossier.

#### DELETE `/api/dossiers/{did}/charges/{cid}` — Achats — l.1013
Refus : 404 ; 409 clos ; 409 période close ; 409 négatif. Journal `frais retiré`. Réponse : le dossier.

#### POST `/api/dossiers/{did}/cloturer` — Achats — l.1028
Refus : 404 / 409 clos ; 422 « Un dossier sans marchandise n'a rien à clore. » ; 409 « Des frais ne
trouvent pas de marchandise où se répartir : les affecter à tout le dossier, ou les retirer,
avant de clore. » (pas de contrôle de période close : la clôture ne revalorise rien).
Effets : `poids_kg` vide → quantité ; chaque ligne en devise sans cours reçoit le **cours du
jour** et son commentaire « … · cours du jour X figé à la clôture du JJ/MM/AAAA » (tronqué pour
tenir en 300) ; statut `clos`, `clos_le` = maintenant ; journal `clôture dossier` « NUM[ · cours
du jour figé : REF à X, …][ · N ligne(s) au cours du bon] ». Réponse : le dossier.

#### POST `/api/dossiers/{did}/rouvrir` — Achats — l.1068
Verrou. Refus : 404 ; 409 « Ce dossier est déjà ouvert. » ; 409 période close (« réouverture »).
Effets : `ouvert`, `clos_le` null (les cours figés restent) ; journal `réouverture dossier`.
Réponse : le dossier.

#### DELETE `/api/dossiers/{did}` — Achats — l.1082
Dossier ouvert seulement. Refus : 404 ; 409 clos ; 409 période close (« suppression »).
Effets : suppression du dossier, de ses lignes et frais (sa facture attend de nouveau son
dossier) ; journal `suppression dossier` « NUM[ · N frais perdus (X MAD)] ».
Réponse `{"ok": true, "frais_perdus": N, "frais_perdus_mad": X}`.

#### GET `/api/export/dossiers` — Achats — l.1099
Voir A.9.4. Requête `statut` pattern `^(|ouvert|clos)$` (422 sinon).

## A.8 Coût de revient des importations (`api/analyse_import.py`)

Routeur entier réservé **Achats**. Calcul repris de l'ERP Fil (vérifié au centime) : pour chaque
dossier, `moteur.revient_dossier` donne par marchandise valeur MAD, frais hors TVA, TVA, coût de
revient.

#### GET `/api/importations/analyse/revient` — Achats — l.80

Paramètres de requête (tous facultatifs) :

| Paramètre | Type | Défaut | Sens |
|---|---|---|---|
| `axe` | str | `reference` | regroupement : `reference`, `composition` (ou nature), `type_fil`, `titrage` (« 2900 Dtex »), `couleur` (ou désignation), `fournisseur` (de la ligne, sinon de la matière), `role_bom`, `dossier`, `lot` ; autre → **400** « axe inconnu : « X » (attendu : reference, composition, …) » |
| `q` | str | "" | mots (tous requis, ordre libre, sans accents ni casse) cherchés dans : n° et libellé du dossier, référence, lot, fournisseur, nature, composition, type de fil (code **et libellé**), titrage + unité, couleur, désignation |
| `debut`, `fin` | date | null | date d'arrivée du dossier dans [début, fin] (dossier sans date : gardé) |
| `composition`, `type_fil`, `titrage`, `couleur`, `fournisseur` | str | "" | égalité exacte (composition ou nature ; couleur ou désignation) |
| `qualite` | str | "" | ne garder que les matières de la recette de cette qualité ; recette vide/inconnue → **404** « qualité inconnue ou sans recette : « X » » ; combinée à `references` : intersection |
| `statut` | str | "" | **« Ouvert » ou « Clos »** (libellés du moteur, majuscule) |
| `references` | str | "" | références séparées par `;` |
| `selection` | str (JSON) | "" | liste d'objets {critère: valeur} sur `composition, type_fil, titrage, couleur, fournisseur` ; une ligne est retenue si elle satisfait **une** des combinaisons (chaque combinaison cumule ses critères). 400 « sélection illisible : … », « la sélection doit être une liste de combinaisons », « critère inconnu dans la sélection : … » |
| `detail` | bool | false | rendre aussi les lignes une à une |

Réponse :
- `axe`, `libelle_axe` (« Référence », « Composition », « Type de fil », « Titrage », « Couleur »,
  « Fournisseur », « Rôle », « Dossier », « Lot ») ;
- `lignes` (groupes, triés par coût de revient décroissant) : `{valeur, quantite (kg), unites:
  ["kg"], unite: "kg", poids, marchandise_mad, charges_mad, tva_mad, lignes (nombre), dossiers
  [numéros triés], detail {poste: MAD}, revient_mad, decaisse_mad, marchandise_unite,
  revient_unite, marchandise_kg, revient_kg, surcout}` ;
- `detail_lignes` (si `detail`) : `{dossier, date_arrivee, statut, reference, lot_fournisseur,
  fournisseur, composition, type_fil, titrage, couleur, role_bom, quantite, unite: "kg", poids,
  marchandise_mad, charges_mad, revient_mad, tva_mad, decaisse_mad, valeur_unite, revient_unite,
  revient_kg, surcout}`, triées par date d'arrivée puis dossier, décroissant ;
- `ids_dossiers` : {numéro: id} (pour ouvrir la fenêtre du dossier) ;
- `frais_non_repartis_mad`, `dossiers_non_repartis: [{dossier, montant}]` — frais hors TVA d'un
  dossier qui ne trouvent pas de marchandise, comptés si aucun filtre matière/texte, ou si une
  marchandise du dossier est retenue, ou (dossier vide) si le texte cherché est dans son n°/libellé ;
- totaux : `total_lignes, total_poids, total_marchandise_mad, total_charges_mad,
  total_revient_mad, total_tva_mad, total_decaisse_mad`.

#### GET `/api/importations/analyse/qualite/{code}` — Achats — l.325
Requête : `debut`, `fin` (date). Refus **404** « qualité inconnue ou sans recette : « X » ».
Analyse par référence restreinte aux références de la recette, puis :
- chaque ligne de l'analyse reçoit `role`, `part_recette` (%), `poids_m2` (poids du rôle × part),
  `cout_m2` (kg/m² de la référence × coût de revient au kg) ;
- `roles` : par rôle `{role, poids_m2, lineaire, connu_m2 (poids au m² des fils importés), cout_m2,
  fils, importes}`, triés par poids décroissant ;
- `qualite`, `nom`, `references_de_la_recette`, `references_importees`, `poids_m2` (Σ rôles au
  poids), `couverture` (part du poids au m² connue), `cout_m2`, `cout_m2_estime` (extrapolé par
  rôle sur ce qui est connu), `cout_kg_tapis` (au kilo de tapis, rôles au poids connus),
  `roles_sans_cout` ;
- plus tous les champs de l'analyse (`lignes`, totaux…).

#### GET `/api/export/revient` — Achats — l.418
Mêmes paramètres que l'analyse (sauf `detail`, forcé à vrai). Voir A.9.5.

## A.9 Exports Excel (10 fichiers)

Tous en `GET`, tous réservés **Achats** (achats + direction) : l'alimentation reçoit 403 — c'est
le seul filtrage des prix des exports ; à l'intérieur, aucun champ n'est masqué. Mise en forme
commune : voir A.0 « Formats Excel communs ». « date » = vraie date Excel `DD/MM/YYYY` ;
« texte ISO » = chaîne `AAAA-MM-JJ`. Colonnes sans format = texte ou nombre brut.
`AAAA-MM-JJ` dans les noms de fichiers = date du jour.

### A.9.1 `GET /api/export/matieres` — `referentiels.py:1471`

- Fichier `matieres-AAAA-MM-JJ.xlsx` ; une feuille **« Matières »**.
- Lignes de titre : « Matières — exporté le JJ/MM/AAAA », puis une ligne vide.
- Une ligne par matière (ordre de référence), d'après `GET /api/articles` sans masquage.

| # | En-tête | Contenu | Format |
|---|---|---|---|
| 1 | Référence | `reference` | |
| 2 | Désignation | | |
| 3 | Rôle | | |
| 4 | Composition | | |
| 5 | Type de fil | | |
| 6 | Titrage | | |
| 7 | Couleur | | |
| 8 | Code couleur | | |
| 9 | Fournisseur | nom | |
| 10 | Prix | prix dans son unité | `#,##0.000` |
| 11 | Devise | | |
| 12 | Unité du prix | `kg` / `ml` | |
| 13 | Prix / kg | `prix_kg` | `#,##0.000` |
| 14 | Densité (kg/ml) | vide si 0 | `0.00000` |
| 15 | Unité d'achat | conditionnement : unité | |
| 16 | Contenance | kg par unité | `#,##0.0` |
| 17 | Unité d’achat déclarée ou déduite | « déclarée » / « déduite » | |
| 18 | Minimum de commande | kg | `#,##0.0` |
| 19 | kg / bobine | | `#,##0.000` |
| 20 | Bobines / palette | | `#,##0` |
| 21 | Stock minimum | kg | `#,##0.0` |
| 22 | Couverture minimum (mois) | | `#,##0.0` |
| 23 | Groupe | groupe d'équivalence | |
| 24 | Code douanier | "" si aucun | |
| 25 | En stock | kg | `#,##0.0` |
| 26 | Active | « oui » / « non » | |

### A.9.2 `GET /api/export/fournisseurs/fiches` — `referentiels.py:1499`

- Fichier `fournisseurs-fiches-AAAA-MM-JJ.xlsx` ; feuille **« Fournisseurs »** ; titre
  « Fournisseurs — exporté le JJ/MM/AAAA ». Une ligne par fournisseur (ordre de nom).

| # | En-tête | Contenu | Format |
|---|---|---|---|
| 1 | Fournisseur | nom | |
| 2 | Code | | |
| 3 | Pays | | |
| 4 | Contact | | |
| 5 | Téléphone | | |
| 6 | E-mail | | |
| 7 | Devise par défaut | | |
| 8 | Devises | « USD 3 · EUR 1 » (devise et nombre de matières) | |
| 9 | Délai déclaré (j) | `delai_jours` | `#,##0` |
| 10 | Délai mesuré (j) | moyenne 12 mois glissants | `#,##0.0` |
| 11 | Couverture (j) | vide si 0 | `#,##0` |
| 12 | Mode de paiement | | |
| 13 | Paiement à (j) | `delai_paiement_jours` | `#,##0` |
| 14 | Conditions | | |
| 15 | Incoterm | | |
| 16 | Port de chargement | | |
| 17 | Banque | | |
| 18 | Matières | nombre | `#,##0` |
| 19 | Actif | oui / non | |

### A.9.3 `GET /api/export/qualites` — `referentiels.py:1520`

- Fichier `qualites-AAAA-MM-JJ.xlsx` ; feuille **« Qualités et recettes »** ; titre « Qualités et
  recettes — exporté le JJ/MM/AAAA ». Une ligne par ligne de recette ; une qualité sans recette
  donne une ligne avec ses seules colonnes 1-3 et 12.

| # | En-tête | Contenu | Format |
|---|---|---|---|
| 1 | Qualité | code | |
| 2 | Nom | | |
| 3 | Fabriquée | « oui » si **active**, « non » sinon | |
| 4 | Rôle | | |
| 5 | Référence | | |
| 6 | Fournisseur | | |
| 7 | Part du rôle (%) | pourcentage | `#,##0.00` |
| 8 | kg / m² | | `#,##0.0000` |
| 9 | Prix d'achat | prix du catalogue dans son unité | `#,##0.000` |
| 10 | Unité du prix | « USD / kg », « MAD / ml » | |
| 11 | Coût / m² (MAD) | de la ligne | `#,##0.00` |
| 12 | Coût de la qualité / m² (MAD) | total de la qualité, répété sur chaque ligne | `#,##0.00` |

### A.9.4 `GET /api/export/dossiers?statut=` — `importations.py:1099`

- Paramètre `statut` : "" (tous), `ouvert`, `clos` (pattern `^(|ouvert|clos)$`).
- Fichier `dossiers-importation-AAAA-MM-JJ.xlsx` ; quatre feuilles, dossiers triés par arrivée
  décroissante puis id décroissant. Dates en **texte ISO**.

Feuille **« Dossiers »** — titres : « Dossiers d'importation[ — ouverts | — closs] » (le pluriel
est formé en ajoutant « s » au statut) puis « Édité le JJ/MM/AAAA ».

| # | En-tête | Contenu | Format |
|---|---|---|---|
| 1 | Dossier | numéro | |
| 2 | Libellé | | |
| 3 | Arrivée | texte ISO | |
| 4 | Statut | `ouvert` / `clos` | |
| 5 | Clos le | texte ISO minute | |
| 6 | Factures | « F1 · F2 » | |
| 7 | Réceptions | « REC-… · REC-… » | |
| 8 | Poids (kg) | | `#,##0.0` |
| 9 | Achat MAD | `marchandise_mad` | `#,##0.00` |
| 10 | Charges hors TVA | `charges_mad` (réparties) | `#,##0.00` |
| 11 | Charges / achat | `surcout` | `0.0%` |
| 12 | Coût hors TVA | `revient_mad` | `#,##0.00` |
| 13 | Coût hors TVA / kg | revient / poids | `#,##0.000` |
| 14 | TVA | `tva_mad` | `#,##0.00` |
| 15 | Coût TTC | `decaisse_mad` | `#,##0.00` |
| 16 | Frais non répartis | frais + TVA non répartis | `#,##0.00` |
| 17 | Droits saisis | `droits_mad` | `#,##0.00` |
| 18 | Droits attendus | null si un code manque | `#,##0.00` |
| 19 | Banque | | |
| 20 | Commentaire | | |

Feuille **« Marchandises »** (sans titre) — une ligne par marchandise :
Dossier · Référence · Lot · Fournisseur · Facture · Réception · Quantité (kg) `#,##0.0` ·
Valeur facture (`valeur_devise`) `#,##0.00` · Devise · Cours (`cours_applique`) `#,##0.000` ·
Achat MAD `#,##0.00` · Charges hors TVA `#,##0.00` · Coût hors TVA `#,##0.00` · Coût hors TVA / kg
`#,##0.000` · TVA `#,##0.00` · Code douanier · Droits attendus `#,##0.00` · Commentaire.

Feuille **« Frais »** (sans titre) — une ligne par frais : Dossier · Poste (libellé) · Montant MAD
`#,##0.00` · Récupérable (oui/non) · Répartition (référence de la marchandise visée, « ? » si
introuvable ; sinon « figée à la clôture » si le frais a des parts ; sinon « à la valeur » / « au
poids ») · Prestataire · Pièce · Date de la pièce · Échéance · Réglé le · Commentaire.

Feuille **« Échéancier »** (sans titre) — une ligne par échéance de chaque dossier : Échéance ·
Dossier · Quoi (« Facture N » ou libellé du poste) · Tiers · Pièce · Montant `#,##0.00` · Devise ·
Estimé (« oui » si montant de facture estimé, sinon vide) · Réglé le.

### A.9.5 `GET /api/export/revient` — `analyse_import.py:418`

- Paramètres : ceux de l'analyse (A.8) sauf `detail`.
- Fichier `cout-de-revient-AAAA-MM-JJ.xlsx`.

Feuille **« Par {axe en minuscules} »** (ex. « Par référence », « Par type de fil ») — titres
« Coût de revient des matières importées » puis « Édité le JJ/MM/AAAA[ · recherche « q »] » :
{Libellé de l'axe} · Lots (nombre de lignes) · Poids (kg) `#,##0.0` · Achat MAD `#,##0.00` ·
Charges hors TVA `#,##0.00` · Charges / achat `0.0%` · Coût hors TVA `#,##0.00` · Coût hors TVA /
kg `#,##0.000` · TVA `#,##0.00` · Coût TTC `#,##0.00` · Dossiers (« 07/26 · 08/26 »). Dernière
ligne **« Total »** (lots, poids, montants, ratios recalculés sur les totaux ; les frais non
répartis n'y sont pas).

Feuille **« Lot par lot »** (sans titre) : Dossier · Arrivée (texte ISO) · Statut (« Ouvert » /
« Clos ») · Référence · Lot · Fournisseur · Titrage · Poids (kg) `#,##0.0` · Achat MAD · Charges hors
TVA · Coût hors TVA (`#,##0.00`) · Coût hors TVA / kg `#,##0.000` · TVA · Coût TTC (`#,##0.00`).

### A.9.6 `GET /api/export/commandes?onglet=&q=` — `exports_achats.py:84`

- `onglet` (≤ 20) : `brouillon` « Brouillons », `a_approuver` « À approuver », `envoyee`
  « Envoyées », `confirmee` « Confirmées », `clos` « Soldées / annulées » (soldée + annulée) ;
  autre valeur ou vide : tout. `q` (≤ 120) : recherche de l'écran (chaque mot, sans accents ni
  casse) dans n° (ou « brouillon »), fournisseur, pays, devise, livraison, statut, créé par,
  observations, conteneur, navire, « référence désignation » de chaque ligne.
- Fichier `commandes-AAAA-MM-JJ.xlsx`. Deux feuilles, chacune avec les titres « Bons de commande
  — exporté le JJ/MM/AAAA » et « Filtres : onglet « … » · recherche « … » » (ou « Filtres :
  aucun »).

Feuille **« Commandes »** (ordre : id décroissant) :

| # | En-tête | Contenu | Format |
|---|---|---|---|
| 1 | N° | numéro ou « Brouillon » | |
| 2 | Date du bon | date d'envoi (vide pour un brouillon) | date |
| 3 | Fournisseur | | |
| 4 | Pays | | |
| 5 | Statut | libellé | |
| 6 | Livraison | état (« 🟢 Livré »…) | |
| 7 | Lignes | nombre | |
| 8 | Commandé (kg) | | `#,##0.0` |
| 9 | Reçu (kg) | net | `#,##0.0` |
| 10 | Reste à livrer (kg) | | `#,##0.0` |
| 11 | Livré | `part_livree` | `0.0%` |
| 12 | Devise | | |
| 13 | Montant confirmé | lignes confirmées | `#,##0.00` |
| 14 | Montant estimé | | `#,##0.00` |
| 15 | Montant MAD | `montant_estime_mad` | `#,##0.00` |
| 16 | Reste à recevoir MAD | | `#,##0.00` |
| 17 | Prix à confirmer | nombre, vide si 0 | |
| 18 | Cours figé | vide si non figé | `#,##0.000` |
| 19 | Livraison prévue | | date |
| 20 | ETA | | date |
| 21 | Livrée le | | date |
| 22 | Dernière réception | | date |
| 23 | Conteneur | | |
| 24 | Par | créé par | |
| 25 | Approuvé par | | |
| 26 | Observations | | |

Feuille **« Lignes »** : N° (ou « Brouillon ») · Fournisseur · Statut · Référence · Désignation ·
Commandé en (unité d'achat) · Unités `#,##0.00` · Commandé (kg) · Reçu (kg) · Reste à livrer (kg)
(`#,##0.0`) · Prix / kg `#,##0.000` (confirmé, sinon catalogue) · Devise (du bon) · Prix confirmé
(« oui » / « non (prix du catalogue) ») · Confirmé par · Confirmé le (date) · Montant
(`montant_estime`) `#,##0.00`.

### A.9.7 `GET /api/export/receptions?onglet=&q=` — `exports_achats.py:149`

- `onglet` : `brouillon` « Brouillons », `validee` « Validées », `annulee` « Annulées ». `q` cherché
  dans n° (ou « brouillon »), fournisseur, n° BL, n° facture, créé par, contrôlé par,
  observations, bons, « référence désignation lot » des lignes.
- Fichier `receptions-AAAA-MM-JJ.xlsx`. Titres « Réceptions — exporté le JJ/MM/AAAA » + filtres.

Feuille **« Réceptions »** : N° (ou « Brouillon ») · Arrivée (date) · Fournisseur · Bons de
commande (« BC-…, BC-… » ou « hors commande ») · N° du BL · Facture · Date facture (date) ·
Montant facture `#,##0.00` (vide si 0) · Devise facture · Échéance (date) · Lignes · Pesé (kg)
`#,##0.0` · Statut (Brouillon / Validée / Annulée) · Par · Contrôlé par · Validée par ·
Observations.

Feuille **« Lignes »** : N° · Arrivée (date) · Fournisseur · Bon de commande (ou « hors
commande ») · Référence · Lot · Reste à livrer (kg) (`quantite_attendue`, lignes de bon
seulement) · Annoncé BL (kg) (`quantite_bl`, vide si 0) · Pesé (kg) · Écart (kg) (`#,##0.0`) ·
Écart (%) `0.0%` · Palettes · Bobines (vides si 0) · kg / bobine `#,##0.000` · Magasin · Qualité
(libellé) · Prix / kg `#,##0.000` · Devise · Observations.

### A.9.8 `GET /api/export/receptions/pesees?q=&ecarts=` — `exports_achats.py:227`

- Source : l'archive des pesées (`pilotage.archive_des_pesees` → `moteur.pesees`) : réceptions
  **validées et brouillons** (annulées exclues ; brouillons numérotés « REC-brouillon-ID »).
  `ecarts=true` : seulement les lignes hors tolérance de pesée, de bobine, ou non conformes.
  `q` cherché dans réception, bon, fournisseur, référence, nature, désignation, lot, magasin,
  qualité. Le bon de chaque ligne est repris de la base par (réception, référence, lot).
- Fichier `archive-des-pesees-AAAA-MM-JJ.xlsx`. Titres : « Archive des pesées — exporté le … »,
  « Filtres : … », « Tolérance de pesée ±2% · tolérance de bobine ±5% » (réglages
  `toler_ecart_pesee`, `toler_poids_bobine` — 2 % et 5 % par défaut — format `.0%`).

Feuille **« Pesées »** : Réception · Arrivée (date) · Statut (« Validée » / « Brouillon ») · Bon de
commande · Fournisseur · Référence · Désignation · Lot · Magasin · Annoncé BL (kg) (=
`quantite_attendue` du moteur : BL, sinon reste à livrer si la pesée l'atteint) · Pesé (kg) ·
Écart (kg) (`#,##0.0`) · Écart `0.0%` · Hors tolérance (« oui » / vide) · Palettes · Bobines (vides
si 0) · kg / bobine · kg / bobine au catalogue (`#,##0.000`) · Écart bobine `0.0%` · Qualité
(Conforme / Sous réserve / Refusé) · Observations.

### A.9.9 `GET /api/export/receptions/bobines?q=&ecarts=` — `exports_achats.py:274`

- Source `moteur.evolution_bobines` : lignes pesées et comptées, non refusées, des réceptions
  **validées**. `ecarts=true` : matières hors tolérance au catalogue. `q` : référence, fournisseur.
- Fichier `poids-des-bobines-AAAA-MM-JJ.xlsx`. Titres : « Poids des bobines — exporté le … »,
  « Filtres : … », « Tolérance au catalogue ±5% » (réglage `toler_poids_bobine`).

Feuille **« Par matière »** : Référence · Fournisseur · kg / bobine au catalogue (vide si 0) ·
Réceptions (nombre) · Premier · Dernier (`#,##0.000`) · Dernière pesée (date) · Évolution
(dernier/premier − 1, vide s'il n'y a qu'une réception) `0.0%` · Moyenne (Σ kg / Σ bobines) · Mini ·
Maxi (`#,##0.000`) · Écart au catalogue `0.0%` · Hors tolérance (oui / vide).

Feuille **« Mesures »** : Référence · Date (date) · Réception · Fournisseur · Lot · Pesé (kg)
`#,##0.0` · Bobines · kg / bobine `#,##0.000` · Écart au catalogue `0.0%`.

### A.9.10 `GET /api/export/commandes/{cid}/bon` — bon de commande Excel — `exports_achats.py:324`

Le bon tel que le fournisseur le lit : **en anglais, sans aucun prix ni montant**, avec l'en-tête
et le pied du papier de l'usine. 404 « Bon de commande introuvable. » Disponible aussi pour un
brouillon.
- Fichier `{numéro}.xlsx` (ex. `BC-2026-0007.xlsx`) ou `brouillon-{id}.xlsx`.
- Une feuille **« Purchase order »**, mise en page à la main (pas `_feuille`), de haut en bas :
  1. Raison sociale (`nom_entreprise`, ou à défaut le texte français « Raison sociale à régler
     (Réglages › Paramètres › Société) ») en **Times New Roman 18, rouge `#D40000`** ;
  2. une ligne par valeur non vide, Times New Roman 11 : forme juridique et capital, « SIEGE
     SOCIAL  {adresse} », ville, téléphone ;
  3. ligne vide ; « PURCHASE ORDER {numéro} » ou « PURCHASE ORDER — draft, not sent » (gras 13) ;
  4. « Date » | date d'envoi au format `08 Oct 2026` (ou « on sending » pour un brouillon) ;
     « Expected delivery » | date promise `08 Oct 2026` ou « to be agreed » (libellés en gras) ;
  5. ligne vide ; « Supplier » (gras 12) puis, si renseignés : Name, Country, Contact, Phone,
     Email (libellé gras | valeur) ;
  6. ligne vide ; « Deliver to » (gras 12) puis, si renseignés : Company (raison sociale),
     Address, City, Expected date, Incoterm (du fournisseur) ;
  7. ligne vide ; en-tête du tableau (gras, fond `#E8ECF3`, trait bas, hauteur 22) : **No. ·
     Item · Description · Packing · Qty · Total weight (kg) · Length (m, indicative)** ;
  8. une ligne par ligne du bon (hauteur 20) : rang ; référence ; désignation ; conditionnement
     en anglais (voir A.10) ; nombre d'unités arrondi à 3 décimales (vide pour une commande au
     poids) format `#,##0.###` ; kg arrondis à 3 décimales format `#,##0.0` ; mètres indicatifs
     arrondis à l'unité (kg ÷ densité, seulement cuir/franges/ruban) format `#,##0` ;
  9. ligne « Total ordered » (colonne B) avec le total des kg (colonne F, `#,##0.0`), gras, trait
     haut ;
  10. si observations : ligne vide puis « Remarks » | texte (gras) ;
  11. ligne vide ; « Please confirm this order by return (quantities and delivery date) and quote
      its number on your delivery note and on your invoice. » ;
  12. si banques ou identifiants : ligne vide, « BANQUES     {banque 1}     {banque 2} » puis
      « ICE : …     R.C : …     N.I.F : …     C.N.S.S : …     PATENTE : … » (Times New Roman 10,
      seuls les identifiants renseignés ; séparateur 5 espaces).
- Largeurs de colonnes A–G : 16, 30, 36, 24, 12, 14, 14.

## A.10 Document HTML imprimable : bon de commande fournisseur

**`GET /api/commandes/{cid}/impression`** — Achats — `achats.py:1035-1147`. Réponse **200
`text/html`** (page complète `<!doctype html><html lang=en>`, `<title>` = numéro ou « brouillon
n° N »), à imprimer ou enregistrer en PDF depuis le navigateur. 404 « Commande introuvable. »
Disponible pour un brouillon (il s'imprime alors comme brouillon).

### Décisions portées par le document
- **En anglais** (fournisseurs étrangers), **sans aucun prix ni montant** (décision de Mohamed),
  **une feuille A4** sur le **papier à en-tête de l'usine**.

### Origine des données
- En-tête et pied : **réglages de la section « Société »** (`parametres.py:119-137`, lus par
  `reglages.valeurs(s)`) : `nom_entreprise` (Raison sociale), `forme_juridique` (« SOCIETE
  ANONYME AU CAPITAL DE 20 000 000 DH »), `adresse` (Siège social, aussi adresse de livraison),
  `ville`, `telephone`, `banques` (« ATTWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 001 82 »,
  banques séparées par « · »), `ice`, `rc`, `identifiant_fiscal` (N.I.F), `cnss`, `patente`.
  Tous vides par défaut. Le réglage `secteur` n'est **pas** imprimé.
- Fournisseur : fiche (`nom`, `pays`, `contact`, `telephone`, `email`, `incoterm`).
- Bon : `numero`, `date_commande`, `date_livraison_prevue`, `observations`, lignes (matière :
  `reference`, `designation`, `kg_par_ml` ; ligne : `unite_achat`, `contenance`, `quantite`).
- Tout texte variable est échappé HTML.

### Formats
- Dates `date_en` (`achats.py:1029-1032`) : `JJ Mmm AAAA` avec mois anglais abrégés `Jan Feb Mar
  Apr May Jun Jul Aug Sep Oct Nov Dec` — ex. **« 08 Oct 2026 »** (sans ambiguïté jour/mois).
- Nombres `nombre_en` (`achats.py:1011-1016`) : séparateur de milliers « , », point décimal,
  zéros inutiles retirés — « 1,234.5 » ; kg à 1 décimale, unités et contenances à 3 décimales,
  mètres à 0.
- Conditionnement `conditionnement_en` (`achats.py:1019-1026`) : commande au poids (`kg` ou `ml`)
  → « **By weight** » ; sinon nom traduit (`CONDITIONNEMENTS_EN`, l.1006-1008, clé en minuscules) :
  palette → **Pallet**, fût/fut → **Drum**, bobine → **Bobbin**, cône/cone → **Cone**, sac →
  **Bag**, rouleau → **Roll**, carton → **Carton**, balle → **Bale**, caisse → **Case**, bidon →
  **Can** ; nom inconnu laissé tel quel ; suivi de « of {contenance} kg » si contenance ≠ 1
  (« Pallet of 756 kg », « Drum of 1,000 kg »).

### Blocs, de haut en bas
1. **Barre d'écran** (collante, fond encre `#1d2733`) avec le bouton « Imprimer / enregistrer en
   PDF (A4) » (`onclick=print()`) — masquée à l'impression.
2. **Avertissement d'écran** si la raison sociale n'est pas réglée (fond `#fff4e5`, texte
   `#8a3b00`) : « La raison sociale de l'usine n'est pas réglée (Réglages › Paramètres › Société) :
   elle manque en tête du bon. » — masqué à l'impression.
3. **Feuille** (`.page`, 210 × 297 mm à l'écran, marges 12/13/16 mm, ombre) contenant :
   - **En-tête société** (centré, Times New Roman, trait bas 0,5 pt `#d9dee5`) : raison sociale
     **19 pt rouge `#d40000`** (première lettre 28 pt, interlettrage 0,02 em) ; puis lignes 10 pt :
     forme juridique, « SIEGE SOCIAL » + adresse, ville, téléphone (chacune si réglée).
   - **Titre** (trait bas 1,5 pt bleu `#1f5fa8`) : à gauche « **Purchase order** » (8 pt, majuscules,
     interlettrage 0,18 em, bleu, gras) au-dessus du numéro (17 pt gras) ou « **Draft — not
     sent** » ; à droite une liste « **Date** » = date d'envoi ou « **on sending** » (brouillon),
     « **Expected delivery** » = date promise ou « **to be agreed** » (9,5 pt ; libellés gris
     `#5b6675`, valeurs grasses).
   - **Deux cadres** côte à côte (bordure 0,75 pt, coins 2 mm, 9,5 pt), titres en petites
     capitales 7,5 pt gris : « **Supplier** » — nom (11 pt gras), pays, contact, téléphone, e-mail
     (chacun si renseigné) ; « **Deliver to** » — raison sociale (ou « — »), adresse, ville,
     « **Expected date** » + date promise, « **Incoterm** » + incoterm du fournisseur (si renseigné).
   - **Tableau** (9,5 pt ; en-tête répété sur chaque page imprimée ; une ligne ne se coupe pas) ;
     en-têtes 7,5 pt majuscules gris sur fond `#f3f5f8` : « **No.** » · « **Item** » · « **Packing** »
     · « **Qty** » (droite) · « **Total weight** » (droite). Chaque ligne : rang ; référence en gras
     et, dessous, désignation (8,5 pt gris) ; conditionnement anglais ; nombre d'unités (3 déc.,
     « — » pour une commande au poids) ; « **N kg** » en gras et, pour cuir/franges/ruban,
     « ≈ N m » dessous (8,5 pt gris). Pied du tableau (trait haut 1,2 pt) : « **Total ordered** » ·
     total « N kg ».
   - **Remarques** (si observations) : encadré fond `#f3f5f8`, titre « **Remarks** », texte avec
     retours à la ligne conservés.
   - **Confirmation** : « Please confirm this order by return — quantities and delivery date — and
     quote its number on your delivery note and on your invoice. »
   - **Signatures** (deux colonnes, filet haut, 24 mm de haut, 9 pt gris) : « For {raison sociale
     | the buyer} / Purchasing manager » et « Accepted by the supplier / Stamp and signature ».
   - **Pied** (Times New Roman 8,5 pt, filet haut 0,5 pt ; **fixé en bas de page** à
     l'impression) : « **BANQUES** » + les banques séparées par des cadratins doubles (si réglées) ;
     ligne des identifiants légaux « ICE : … R.C : … N.I.F : … C.N.S.S : … PATENTE : … » (seuls
     ceux renseignés).
- Page : `@page { size: A4; margin: 12mm 13mm 16mm }` ; police Arial/Helvetica 10 pt, interligne
  1,45 ; sous 820 px de large, la feuille prend toute la largeur (téléphone).

## A.11 Réglages lus par ces routes (valeur par défaut)

| Clé | Défaut | Lu par |
|---|---|---|
| `seuil_approbation` | 0 MAD (= jamais) | envoi, garde-fou, `commande_dict` |
| `toler_in_full` | 2 % | livré / reste à livrer, soldes, recalage des brouillons de réception |
| `toler_retard_jours` | 0 j | état « En retard » d'un bon |
| `toler_ecart_pesee` | 2 % | écart de pesée (réception, archive) |
| `toler_excedent` | 10 % | blocage d'excédent à la réception |
| `toler_poids_bobine` | 5 % | métiers (écart pesé/catalogue), archive, bobines |
| `seuil_surcout_import` | 100 % | frais aberrants d'un dossier (C35) |
| `toler_facture_import` | 2 % | rapprochement facture / marchandise |
| `taux_tva_import`, `taux_tpi_import` | 20 %, 0,25 % | TVA attendue |
| `taux_perte`, `mode_classeur` | (partie calculs) | kg/m² des recettes, facteurs de coût |
| `date_cloture` | vide | `date_permise`, `cout_hors_periode_close` |
| Société : `nom_entreprise`, `forme_juridique`, `adresse`, `ville`, `telephone`, `banques`, `ice`, `rc`, `identifiant_fiscal`, `cnss`, `patente` | vides | bon HTML et bon Excel |
| Cours des devises (table `Devise`, MAD 1 · USD 10 · EUR 10,8 à l'installation) | | prix convertis, cours figés, dossiers |

## A.12 Points incohérents ou ambigus

Constatés dans le code ; à trancher pour la réécriture (sans changer ce que l'utilisateur voit
sans le décider).

**Droits et masquage**
1. **Lectures « tout rôle » par `acteur`, pas par `LECTURE`** : `securite.py` définit `LECTURE`
   mais aucune route du périmètre ne l'utilise ; `GET /classification`, `/fournisseurs`,
   `/articles`, `/qualites`, `/magasins`, `/metiers`, `/montage/references`, `/postes-frais`,
   `/brouillons` et **`POST /articles/composer`** (un POST sans `droit(...)`, qui n'écrit rien)
   reposent sur `acteur`. Même effet aujourd'hui (3 rôles), mais un 4e rôle (administrateur
   technique de GMAO PRO) y passerait d'office.
2. **Masquage des prix fait à la main et inégal** : `GET /articles` masque `prix`, `prix_kg` mais
   laisse `unite_prix` et `devise` ; `GET /qualites` masque aussi `unite_prix` des lignes mais
   laisse `devise`. `GET /fournisseurs` montre à l'alimentation banque, conditions et mode de
   paiement. Rien de générique : un champ de prix ajouté à une route « tout rôle » fuirait.
3. **Droits voisins dissymétriques** : `GET /postes-frais` (tout rôle, `referentiels.py`) et
   `GET /postes-frais/complet` (Achats, `referentiels_import.py`) pour la même table, dans deux
   modules ; `GET /qualites` tout rôle mais `GET /qualites/facteurs-cout` Achats (l'écran des
   qualités, ouvert à l'alimentation, reçoit un 403 sur ce second appel) ; `GET /codes-douaniers`
   Achats alors que leur écriture est Direction ; les postes et codes sont tenus par la direction
   mais **utilisés** par les achats (dossiers, matières) qui ne peuvent pas en créer.
4. **Ordres de fabrication : seule l'alimentation (et la direction) les valide** dans
   `/brouillons` (`_peut`), alors que `POST /brouillons/valider` est ouverte à `STOCK` (achats
   compris) : un compte achats appelle la route, mais ses ordres sont ignorés en silence (compte
   dans `ignores` seulement s'il les a nommés).

**Codes et formes de réponse**
5. **Codes d'erreur hétérogènes** : 422 par défaut (`erreur`), mais **400** dans
   `analyse_import.py` (axe, sélection) et 404 pour une qualité sans recette ; « Étage N : ce
   métier n'en a que E. » est **404** dans `PUT /metiers/{mid}/etages/{etage}` et **422** dans
   `PUT /metiers/{mid}/fils` (même message).
6. **Formes de réponse des écritures variables** : classification → toute la classification ;
   magasins → toute la liste ; fournisseur, matière, poste, code → la fiche ; qualité →
   `{id, empreinte[, avertissement]}` ; métier → `{id}` ou `{id, empreinte}` ; montage →
   `{ok, empreinte_fils|empreinte, stock}` ; suppressions → `{ok: true}` (dossier : + frais perdus) ;
   `POST /commandes` → **liste** de bons ; recette → `{ok, empreinte}` ; plan → `{ok}`.
7. **Conventions de paramètres mêlées** : l'empreinte passe dans le **corps** (fournisseur,
   qualité, métier, étage) ou en **requête** (recette, restauration, montage complet) ; le
   corps de `PUT /qualites/{qid}/recette` et `PUT /metiers/{mid}/fils` est un **tableau nu** ;
   `motif` est en requête (recette, restauration) mais dans le corps (renvoi d'un bon, annulation
   de réception).
8. **Statut de dossier en deux casses** : l'analyse et l'export du coût de revient filtrent
   `statut` = « Ouvert » / « Clos » (libellés du moteur, valeur non contrôlée : une autre valeur
   rend un résultat vide), l'export des dossiers `ouvert` / `clos` (contrôlé par motif) ; la
   feuille « Lot par lot » écrit « Ouvert/Clos », la feuille « Dossiers » « ouvert/clos ».
9. **Titre d'export fautif** : `GET /export/dossiers?statut=clos` titre « Dossiers d'importation
   — **closs** » (`importations.py:1123`, pluriel formé par « s »).
10. **Dates d'export hétérogènes** : vraies dates `DD/MM/YYYY` dans `exports_achats.py`, textes
    ISO dans les exports des dossiers et du coût de revient.

**Règles métier en tension**
11. **Lot interne pris d'avance** : `POST /lots/numero-interne` consomme immédiatement un numéro
    LOT, alors que la doctrine des réceptions (`receptions.py:45-46`, M65) est de ne le donner
    qu'à la validation « pour ne pas laisser de trou ». Un numéro demandé puis abandonné laisse
    un trou. (Les réceptions, elles, utilisent « LOT INTERNE » remplacé à la validation.)
12. **Réception entièrement refusée impossible à annuler** : sa validation n'écrit aucun
    mouvement ; `POST /receptions/{rid}/annuler` appelle la contre-passation, qui ne trouve rien
    et répond **409 « Ce document a déjà été annulé. »** — message faux, et la réception reste
    « validée » pour toujours.
13. **Prix de réception : unité ambiguë** : le commentaire du modèle (`receptions.py:342-344`)
    dit « dans l'unité de la matière (au kilo, ou au mètre) », mais le serveur ne convertit rien
    et le traite comme un prix **au kilo** (défaut catalogue au kilo, écran qui ramène au kilo).
14. **Confirmation des prix trop permissive** : `POST /commandes/{cid}/prix` n'est refusée que
    pour un bon **annulé** — permise sur un brouillon (fige alors le cours avant l'envoi) et sur
    un bon soldé. Et pour un brouillon `a_approuver` (sans numéro) le garde-fou est sauté : changer
    ses lignes le renvoie en brouillon (`PUT`), changer ses prix non.
15. **Approbation datée du jour** : `POST /commandes/{cid}/approuver` numérote à la date du jour,
    sans possibilité de saisir la date réelle d'envoi (que `envoyer` accepte).
16. **`PUT /commandes/{cid}/expedition` remplace tout** (un jalon absent du corps est effacé) et
    reste permis sur un bon soldé ou annulé.
17. **Facture : deux sémantiques** : à la création/modification d'une réception, date, montant
    et échéance ne sont écrits que s'ils sont non nuls (`_facture`) ; `PUT
    /receptions/{rid}/facture` remplace chaque champ (un montant 0 efface). La route est aussi
    permise sur un brouillon.
18. **`LigneEntree.id` de réception accepté mais ignoré** (les lignes sont toujours recréées).
19. **`PUT /dossiers/{did}` prend `DossierEntree`** : `numero`, `facture_id`, `local_confirme`
    sont acceptés et ignorés ; `date_arrivee` ne peut pas être vidée.
20. **Libellé « figée à la clôture »** (feuille Frais de l'export des dossiers) : les parts d'un
    frais ne se figent pas à la clôture mais au **changement de clé du poste** sur un dossier clos
    (`_figer_clos`).
21. **« Annoncé BL (kg) » n'a pas le même contenu dans deux exports** : `quantite_bl` dans
    l'export des réceptions, `quantite_attendue` du moteur (BL, sinon reste à livrer) dans
    l'archive des pesées.
22. **Archive des pesées, brouillons** : le moteur nomme un brouillon « REC-brouillon-ID », si bien
    que la valeur de repli « Brouillon » de la colonne Réception n'apparaît jamais, et la
    reprise du bon par (réception, référence, lot) ne trouve pas les brouillons (repli sur le bon
    du moteur).
23. **Prix des lignes dans l'export des commandes** : « Prix / kg » prend le prix catalogue
    (dans la devise de la **fiche**) quand le prix n'est pas confirmé, mais « Devise » affiche
    celle du **bon** ; si la fiche a changé de devise, la colonne mélange deux devises.
24. **Export des qualités, colonne « Fabriquée »** : contient en fait « actif » (oui/non), pas « a
    été fabriquée » (champ `fabrications` disponible mais non exporté).
25. **Bon Excel et bon HTML divergent** : brouillon « PURCHASE ORDER — draft, not sent » contre
    « Draft — not sent » ; colonne « Description » et « Length (m, indicative) » séparées dans
    l'Excel, sous la référence dans le HTML ; sans raison sociale, l'Excel imprime un texte
    **français** en tête d'un document anglais, le HTML n'avertit qu'à l'écran ; séparateurs du
    pied (5 espaces / cadratins). Les deux sont accessibles pour un **brouillon**.
26. **Renommage d'un rôle de nomenclature** = suppression puis recréation, refusé dès qu'une
    ligne `QualitePoids` existe (même à 0) alors que la suppression, elle, ne compte que les
    poids > 0 et efface les lignes à 0.
27. **Recalage des réceptions à la lecture** : `GET /receptions` modifie les objets en mémoire
    (`recaler`) et compte sur l'absence de commit — une lecture qui « n'écrit rien » par
    convention, pas par construction.
28. **Routes non appelées par l'écran** : `GET /api/factures` (seulement par les essais). Pas de
    route de suppression de magasin (désactivation seulement).
29. **`modifier_valeur` de classification** journalise « code → code » même sans renommage ; une
    valeur portée par des matières peut être désactivée sans avertissement.
30. **Ordre de déclaration significatif** : `/classification/roles…` doit précéder
    `/classification/{nom}…` (`referentiels.py:102-103`) — sinon « roles » serait pris pour une
    liste. À garder en tête si les routes sont réorganisées.


# API de Gestion MP — partie B

> Comptes et réglages, stock, opérations de stock, inventaires, alimentation des machines,
> production et besoins, pilotage, suivi (réclamations, signalements, pièces jointes,
> échéancier, versions de recettes, indicateurs, bilan, import des matières), exports Excel
> du stock et de l'analyse — plus le socle commun (`main.py`, `securite.py`).
>
> Source : le code de `~/gestion-mp` (commit `2d588b9`, lu le 8 octobre 2026). Références
> `fichier:ligne` relatives à `gestion_mp/`. Rien ici n'a été déduit de l'écran ou de la
> documentation : quand le code et un commentaire divergent, le code fait foi et l'écart est
> signalé en fin de document.
>
> Périmètre : 108 routes dans 10 modules + `/api/sante` (main) + la route attrape-tout de
> l'écran ; 12 fichiers Excel (11 exports + le modèle d'import) ; 4 documents HTML
> imprimables.

---

## 0. Socle commun

### 0.1 Application (`main.py`)

| Élément | Valeur exacte | Réf. |
|---|---|---|
| Titre / version OpenAPI | `Gestion MP` / `1.0.0` ; description « Matières premières : achats, réceptions, alimentation des machines, stock, importations, pilotage. » | `main.py:126-129` |
| Documentation | Swagger sur `/api/docs`, schéma sur `/api/openapi.json`, ReDoc désactivé | `main.py:126-127` |
| Préfixe | **Tous** les routeurs sont montés sous `/api` (les chemins des décorateurs n'ont pas le préfixe) | `main.py:131-134` |
| Ordre d'enregistrement des routeurs | comptes, referentiels, stock, achats, receptions, production, production_plan, operations, inventaires, exports, exports_achats, exports_analyse, brouillons, importations, referentiels_import, analyse_import, suivi, pilotage. L'ordre compte en cas de chemins identiques (le premier gagne) : aujourd'hui aucun chemin de la partie B n'est masqué (vérifié : `/lots/{lid:int}` ne capte pas `/lots/scan` grâce au convertisseur `int`, aucun `GET /receptions/{id}` ni `GET /fournisseurs/{id}` n'existe). | `main.py:131-133` |
| Tags OpenAPI (partie B) | « Comptes et réglages » (comptes), « Stock » (stock), « Opérations de stock » (operations), « Inventaire » (inventaires), « Alimentation des machines » (production), « Production » (production_plan), « Pilotage » (pilotage), « Suivi » (suivi), « Exports » (exports), « Exports analyse » (exports_analyse), « Exploitation » (`/api/sante`) | chaque `APIRouter(tags=…)` |

#### Cycle de vie (`vie`, `main.py:118-123`)

Au démarrage, `initialiser()` (`main.py:50-85`), une seule fois et sans jamais écraser l'existant :
1. `migrer()` — schéma à jour (migrations numérotées, table `schema_version`).
2. Rôles de nomenclature : ajoute ceux de `calcul.modele.ROLES` absents — `Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique` — avec `lineaire = rôle ∈ (Cuir, Franges, Ruban)` et `ordre` = rang dans la liste.
3. Postes de frais d'importation : ajoute ceux de `calcul.modele.POSTES_IMPORT` absents (libellé, récupérable). Un poste ajouté à une base déjà remplie prend `ordre = ordre du précédent + 1` et décale les suivants d'un cran.
4. Devises absentes : `MAD` « Dirham » 1,0 ; `USD` « Dollar américain » 10,0 ; `EUR` « Euro » 10,8 (`main.py:45`).
5. Magasins : s'il n'existe aucun magasin de type `Stock courant` (et aucun de code `Magasin principal`), crée `Magasin principal` (type `Stock courant`) ; idem `Quarantaine` (type `Quarantaine`) (`main.py:46,78-82`).
6. `reglages.installer(s)` : écrit chaque réglage absent avec sa valeur par défaut (`modifie_par = "installation"`).

Puis, si `GESTION_MP_TACHES=1` (défaut), `demarrer_taches()` (`main.py:88-115`) : un seul processus prend le verrou consultatif PostgreSQL `pg_try_advisory_lock(7426102)` (connexion gardée ouverte) ; les autres ne lancent rien. Le gagnant lance un fil « taches » qui, **toutes les 15 minutes** :
- `suivi.taches_du_jour()` (`suivi.py:841-847`) : prend la photo des indicateurs du jour si elle n'existe pas encore (voir `POST /api/indicateurs/photographier`), puis `courriel.envoyer_si_lundi(s)` (le courriel hebdomadaire) ; une erreur est écrite sur la sortie d'erreur préfixée `[indicateurs]` ;
- `sauvegarde.du_jour()` : si `gestion-mp-AAAA-MM-JJ.dump` du jour n'existe pas, `pg_dump -Fc`, relecture (`pg_restore --list`), renommage atomique, miroir des pièces jointes, copie externe si `GESTION_MP_SAUVEGARDES_COPIE`, puis purge (14 quotidiennes + la première de chaque mois sur 12 mois ; manuelles et « avant-restauration » jamais purgées) ; en cas d'échec, `ETAT["erreur"]` = message (300 car.) et ligne `[sauvegarde] échec : …` ; `ETAT["essai"]` = maintenant.

#### Service de l'écran (`main.py:203-214`)

Seulement si le dossier `config.ECRAN` (défaut `ecran/dist`, variable `GESTION_MP_ECRAN`) existe :
- `/assets` est servi en fichiers statiques (`ecran/dist/assets`) ;
- `GET /{chemin:path}` (hors schéma OpenAPI) : un chemin commençant par `api/` → **404 « Route inconnue »** ; un fichier existant sous `ECRAN` (contrôle anti-évasion `is_relative_to`) est renvoyé tel quel, avec `Cache-Control: no-cache` pour `sw.js` et `manifest.webmanifest` seulement ; tout autre chemin renvoie `index.html` avec `Cache-Control: no-cache` (application monopage : `/lot/123`, `/stock?onglet=…` sont des routes de l'écran).

### 0.2 Protections communes (middleware `protections`, `main.py:136-161`)

| Règle | Détail exact |
|---|---|
| En-tête anti-falsification | Toute requête dont la méthode n'est **pas** `GET`, `HEAD` ou `OPTIONS`, dont le chemin commence par `/api/` et n'est pas l'un de `/api/connexion`, `/api/installation`, `/api/deconnexion`, doit porter `X-Gestion-MP: 1`. Sinon **403** `{"detail": "Requête refusée : elle ne vient pas de l'écran de Gestion MP."}` — avant toute authentification et avant la validation du corps. |
| En-têtes sur toutes les réponses (si absents) | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`. |
| En-têtes sur les réponses `/api/…` | `Cache-Control: no-store` (si absent) ; `X-Heure-Serveur: AAAA-MM-JJTHH:MM:SS` (heure locale du serveur, toujours posé) — l'écran affiche cette heure plutôt que celle du poste. |

### 0.3 Format des erreurs

- Toutes les erreurs métier sont des `HTTPException` : corps `{"detail": "<message en français>"}`. `securite.erreur(message, code=422)` (`securite.py:28-29`) : **le code par défaut est 422**, 404 pour « introuvable », 409 pour un conflit d'état, 403 pour un droit.
- Erreurs de validation Pydantic/FastAPI (`main.py:164-187`) : **422** `{"detail": "champ : message ; champ : message"}`. Le champ est le chemin `loc` sans `body`/`query`/`path`, joint par des points (ex. `lignes.0.quantite`). Le message anglais est traduit par remplacements successifs, dans cet ordre : `Field required`→`à renseigner` ; `Input should be a valid`→`valeur incorrecte` ; `should be greater than or equal to`→`doit être au moins` ; `should be greater than`→`doit être supérieur à` ; `should be less than or equal to`→`doit être au plus` ; `should be less than`→`doit être inférieur à` ; `should have at least`→`trop court : au moins` ; `should have at most`→`trop long : au plus` ; `characters`→`caractères` ; `character`→`caractère` ; `String`→`Texte` ; `Input`→`La valeur` ; `List`→`La liste` ; `item after validation`→`élément` ; `items`→`éléments`. Sans champ, le message seul.
- Quelques routes lèvent directement `HTTPException(400, …)` ou `HTTPException(404, …)` avec des messages en minuscules (pilotage, production_plan, exports) — signalés route par route.

### 0.4 Authentification et session (`securite.py`)

| Élément | Détail exact | Réf. |
|---|---|---|
| Cookie | `gestion_mp_session` ; valeur = jeton aléatoire `secrets.token_urlsafe(32)` ; `HttpOnly`, `SameSite=Lax`, `Secure` si `GESTION_MP_HTTPS=1`, `Path=/`, `Max-Age = SESSION_JOURS × 86400` (défaut 30 jours, `GESTION_MP_SESSION_JOURS`). | `securite.py:24,62-80` |
| Stockage | Table `SessionOuverte` : clé = **SHA-256 du jeton** (le jeton n'est jamais stocké), `utilisateur_id`, `expire_le = maintenant + SESSION_JOURS`. L'ouverture met aussi `Utilisateur.vu_le = maintenant`. | `securite.py:55-71` |
| Fermeture | supprime la ligne `SessionOuverte` du jeton présenté (s'il y en a un) et efface le cookie. | `securite.py:83-89` |
| `acteur` | Dépendance « personne connectée » : pas de cookie, session inconnue ou expirée → **401 « Connectez-vous pour continuer. »** ; utilisateur supprimé ou inactif → **401 « Ce compte n'est plus actif. »**. Pas de prolongation glissante : la session expire à date fixe. | `securite.py:92-101` |
| `droit(*roles)` | Passe si `role == direction` **ou** `role ∈ roles`. Sinon **403 « Cette action est réservée à : {libellés en minuscules séparés par « , »}. »** (ex. « responsable achats », « responsable achats, responsable alimentation machines ») ; sans rôle : « la direction ». L'attribut `.roles` sert à un essai qui vérifie que toute route d'écriture est gardée. | `securite.py:104-114` |
| Alias | `DIRECTION = droit()` (direction seule) ; `ACHATS = droit("achats")` (achats + direction) ; `ALIMENTATION = droit("alimentation")` (alimentation + direction) ; `STOCK = droit("achats","alimentation")` (les trois rôles) ; `LECTURE = droit(achats, alimentation)` (les trois rôles). | `securite.py:117-122` |
| Rôles | `direction` « Direction », `achats` « Responsable achats », `alimentation` « Responsable alimentation machines ». | `modeles.py:42-49` |
| Codes secrets | Empreinte `scrypt$<sel hex 16 o>$<hash hex 32 o>` (n=2¹⁴, r=8, p=1). Longueur minimale : **4** pour l'alimentation (téléphone d'atelier), **8** pour les autres rôles. | `securite.py:35-52` |
| Anti-force brute | Par identifiant (table `Tentative`) : chaque échec incrémente `echecs` (insertion atomique `ON CONFLICT`) ; à partir du **5ᵉ** échec, blocage de `min(900, 30 × 2^(échecs−5))` secondes (30 s, 1 min, 2 min… plafonné à 15 min). L'échec est commité immédiatement. Un succès supprime le compteur. | `securite.py:25,128-153` |

Dans ce document, les rôles admis sont écrits ainsi :
- **Public** : aucune session requise ;
- **Connecté** : `acteur` — direction, achats, alimentation ;
- **Direction** : `DIRECTION` ;
- **Achats** : `ACHATS` — achats **et** direction ;
- **Alimentation** : `ALIMENTATION` — alimentation **et** direction ;
- **Stock** : `STOCK` — les trois rôles (puis contrôle fin par type d'opération).

Quand un routeur porte `dependencies=[Depends(acteur)]` (stock, pilotage) et qu'une route y ajoute `ACHATS`, le 401 passe avant le 403.

### 0.5 Masquage des prix pour l'alimentation (« sans prix »)

**Il n'existe pas de filtre générique.** Chaque route qui peut renvoyer un prix à l'alimentation le retire elle-même, au premier niveau des dictionnaires de lignes (aucune descente récursive). Les routes de pilotage financières (plan d'achat, cockpit, valorisation, prix, opportunités, contrôles, performance), les exports chiffrés et l'échéancier sont simplement **interdits** à l'alimentation (`ACHATS`).

| Route | Test | Champs mis à `null` | Champs vidés (`""`) | Réf. |
|---|---|---|---|---|
| `GET /api/mouvements` (et `GET /api/export/mouvements`) | `stock.sans_prix(qui)` : `role == "alimentation"` | `prix`, `cours`, `cout_mad`, `valeur_mad` (s'ils existent) | `devise` | `stock.py:35-47,147-148` |
| `GET /api/lots/{lid}` | idem, appliqué à chaque élément de `mouvements` | idem | idem | `stock.py:302-304` |
| `GET /api/export/mouvements` | idem | colonnes « Prix / kg » et « Devise » **supprimées** du classeur | — | `exports.py:256,286,292` |
| `GET /api/operations`, `GET /api/operations/{oid}` | `_pour(qui, …)` : `role == "alimentation"` | `lignes[].prix` | `lignes[].devise` | `operations.py:201-206` |
| `GET /api/inventaires`, `GET /api/inventaires/{iid}` | `_sans_prix(qui)` | `ecart_valeur_mad`, `ecart_valeur_absolue_mad`, `lignes[].cmup_mad`, `lignes[].valeur_ecart_mad` | — | `inventaires.py:123-128,161-169,252` |
| `GET /api/stock` | `qui.role == ALIMENTATION` | `prix_kg`, `prix_unite`, `montant_a_commander`, `montant_a_commander_mad`, `valeur_conso_annuelle`, `valeur_conso_annuelle_mad`, `valeur_machine_mad` | `devise`, `action` | `pilotage.py:40-41,58-62` |
| `GET /api/nomenclature` | idem | `prix`, `prix_kg`, `cout_m2_mad` | `devise` | `pilotage.py:115-117` |

Toutes les autres routes ouvertes à l'alimentation ne contiennent aucun prix ni montant par construction (vérifié champ par champ ci-dessous), à l'exception des réglages (`GET /api/parametres`) et des cours (`GET /api/devises`), voir « Points incohérents ».

### 0.6 Journal d'audit, numéros, dates (`securite.py`)

- `journal(s, u, action, objet="", objet_id=None, detail="")` ajoute une ligne `Journal` : `utilisateur` = nom de la personne (ou « système »), `role` = code du rôle (ou vide), `action`, `objet`, `objet_id`, `detail` tronqué à **2 000** caractères, `quand` = maintenant (défaut de la table). Écrit dans la même transaction que le geste (`securite.py:159-176`). Chaque route ci-dessous indique l'action, l'objet et le détail exacts.
- `numero(s, serie, jour, largeur=4)` : compteur par (série, **année de la pièce**) sous verrou de ligne (`SELECT … FOR UPDATE`, créé par `INSERT … ON CONFLICT DO NOTHING`) ; format `SERIE-AAAA-NNNN` (ex. `OF-2026-0042`) ; exception : la série `DOS` donne `NN/AA`. Séries de la partie B : `OUV`, `RET`, `TRF`, `AJU`, `RFO` (opérations), `OF` (ordres), `INV` (inventaires), `RCL` (réclamations). Le numéro est pris dans la transaction : un refus ultérieur l'annule (pas de trou) (`securite.py:179-207`).
- `date_permise(s, jour)` (`securite.py:210-226`), appelée avant toute écriture datée — trois refus 422 :
  - avant le 01/01/2000 : « Date trop ancienne (JJ/MM/AAAA) : vérifier l'année. »
  - après aujourd'hui : « Date dans le futur (JJ/MM/AAAA) : un mouvement se saisit le jour où il a lieu. »
  - ≤ réglage `date_cloture` : « La période jusqu'au JJ/MM/AAAA est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir. »

### 0.7 Écriture du stock (chemin unique, `services/stock.py`)

Toutes les routes de la partie B qui bougent le stock passent par `stock.ecrire` (ou `transferer` / `contrepasser_document`, qui l'appellent). Ses refus apparaissent donc dans les routes concernées ; un collègue les détaille, en voici la liste exacte :

| Refus | Code | Réf. |
|---|---|---|
| « Une écriture de stock ne peut pas être nulle. » | 422 | `services/stock.py:147` |
| les trois refus de `date_permise` | 422 | |
| « Magasin inconnu. » | 422 | `:151` |
| « Le magasin « X » est désactivé : il ne reçoit plus rien. » (entrée seulement) | 422 | `:153` |
| « L'inventaire INV-… est en cours sur « X » : les mouvements y sont suspendus jusqu'à sa validation. » (sauf écritures de l'inventaire lui-même) | 409 | `:165-168` |
| « Le lot « L » de « R » ne porte que N kg dans « X », M kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là. » | 409 | `:171-178` |
| (sortie) « Le lot « L » de « R » n'est entré dans « X » que le JJ/MM/AAAA : une écriture datée du JJ/MM/AAAA ne peut pas le prendre. La dater au jour où la matière était là, ou choisir un lot présent à cette date. » (ou « n'est jamais entré dans « X » ») | 409 | `:104-111` |
| (sortie) « Au JJ/MM/AAAA, il n'y avait que N kg du lot « L » de « R » dans « X », M kg demandés au JJ/MM/AAAA[ : la matière est sortie depuis par d'autres écritures.|.] Choisir un autre lot, ou dater l'écriture après l'entrée de la matière. » | 409 | `:113-119` |
| « Un transfert va d'un magasin à un autre. » | 422 | `:219` |
| « Ce document a déjà été annulé. » (contre-passation) | 409 | `:251` |
| « Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne ». » (création de lot) | 422 | `:45` |

Une contre-passation écrit, pour chaque mouvement non encore annulé du document, l'inverse **daté comme l'original** (sorties défaites avant les entrées), avec `contrepasse_id` = l'original et le commentaire « Annulation du mouvement n°ID » ; elle est donc refusée si l'original est dans la période close.

### 0.8 Effet de bord global : versions des recettes (`suivi.py:441-476`)

Deux écouteurs SQLAlchemy posés sur **toutes** les sessions : `before_flush` note les qualités dont une `Recette` ou un `QualitePoids` est créé, modifié ou supprimé (ou dont la collection `poids` change) ainsi que l'auteur du dernier `Journal` ajouté ; `before_commit` écrit pour chacune une `RecetteVersion` (`qualite_id`, `par`, `contenu` = JSON `[{reference, role, pourcentage}]` trié par rôle, `poids` = JSON `{role: poids}`). Toute route qui modifie une recette, quel que soit son module, produit donc une version (lue par `GET /api/qualites/{qid}/versions`).

---

## 1. Récapitulatif des routes de la partie B

Rôles : voir § 0.4. « Stock* » : `STOCK` puis contrôle par type d'opération (§ 4).

| # | Méthode | Chemin | Rôles | Sens |
|---|---|---|---|---|
| 1 | GET | `/api/sante` | Public | Surveillance : base, schéma, version, fraîcheur des sauvegardes |
| 2 | GET | `/api/etat` | Public | L'ERP est-il installé ? nom de la société |
| 3 | GET | `/api/visages` | Public | Comptes actifs pour choisir son nom à la connexion |
| 4 | POST | `/api/installation` | Public (une seule fois) | Crée le premier compte (direction) et ouvre sa session |
| 5 | POST | `/api/connexion` | Public | Ouvre une session (cookie) |
| 6 | POST | `/api/deconnexion` | Public | Ferme la session |
| 7 | GET | `/api/moi` | Connecté | Le compte connecté |
| 8 | POST | `/api/moi/code` | Connecté | Changer son propre code |
| 9 | GET | `/api/utilisateurs` | Direction | Liste des comptes |
| 10 | POST | `/api/utilisateurs` | Direction | Créer un compte |
| 11 | PUT | `/api/utilisateurs/{uid}` | Direction | Modifier un compte (nom, rôle, courriel, actif, code) |
| 12 | GET | `/api/journal` | Direction | Journal des actions filtré |
| 13 | GET | `/api/journal/valeurs` | Direction | Valeurs proposées par les filtres du journal |
| 14 | GET | `/api/parametres` | Connecté | Tous les réglages et leurs valeurs |
| 15 | PUT | `/api/parametres` | Direction | Modifier des réglages |
| 16 | GET | `/api/parametres/historique` | Direction | Historique des réglages (avant → après) |
| 17 | GET | `/api/devises` | Connecté | Devises, cours, date du dernier cours |
| 18 | GET | `/api/devises/{code}/historique` | Connecté | Cours successifs d'une devise |
| 19 | PUT | `/api/devises` | Achats | Créer une devise ou changer son cours |
| 20 | GET | `/api/sauvegardes` | Direction | État et liste des sauvegardes |
| 21 | POST | `/api/sauvegardes` | Direction | Sauvegarde manuelle immédiate |
| 22 | GET | `/api/etat-serveur` | Direction | Installation vue par la direction (versions, base, réseau, sessions) |
| 23 | POST | `/api/sauvegardes/{nom}/restaurer` | Direction | Remplacer la base par une sauvegarde |
| 24 | GET | `/api/mouvements` | Connecté (prix masqués alim.) | Journal du stock filtré, paginé, valorisable |
| 25 | GET | `/api/soldes` | Connecté | Lots et soldes par magasin, statut, historique |
| 26 | GET | `/api/lots/{lid}` | Connecté (prix masqués alim.) | Fiche complète d'un lot |
| 27 | GET | `/api/lots/scan` | Connecté | Trouver un lot à partir d'un QR ou d'un numéro |
| 28 | GET | `/api/acces` | Connecté | Adresses pour joindre l'ERP depuis un téléphone |
| 29 | GET | `/api/acces/qr` | Connecté | QR (SVG) de l'adresse pour téléphones |
| 30 | GET | `/api/lots/etiquettes` | Connecté | Étiquettes QR imprimables (HTML) |
| 31 | GET | `/api/controles/soldes` | Achats | Soldes tenus = somme du journal ? |
| 32 | GET | `/api/operations/motifs` | Connecté | Types, motifs, codes R1…R6, droits par type |
| 33 | GET | `/api/operations` | Connecté (prix masqués alim.) | Liste des opérations de stock |
| 34 | GET | `/api/operations/{oid}` | Connecté (prix masqués alim.) | Une opération |
| 35 | POST | `/api/operations` | Stock* | Créer un brouillon d'opération |
| 36 | PUT | `/api/operations/{oid}` | Stock* | Modifier un brouillon |
| 37 | DELETE | `/api/operations/{oid}` | Stock* | Supprimer un brouillon |
| 38 | POST | `/api/operations/{oid}/valider` | Stock* | Valider : numéro + mouvements |
| 39 | POST | `/api/operations/{oid}/annuler` | Stock* | Annuler une opération validée (contre-passation) |
| 40 | GET | `/api/inventaires` | Connecté (montants masqués alim.) | Liste des inventaires (sans lignes) |
| 41 | GET | `/api/inventaires/defauts` | Connecté | Valeurs proposées à l'ouverture |
| 42 | GET | `/api/inventaires/a-compter` | Connecté | Inventaire tournant : matières dues |
| 43 | GET | `/api/inventaires/{iid}` | Connecté (montants masqués alim.) | Un inventaire avec ses lignes |
| 44 | POST | `/api/inventaires` | Achats | Ouvrir un inventaire (fige le théorique) |
| 45 | POST | `/api/inventaires/{iid}/comptage` | Achats | Saisir des comptages / lots trouvés |
| 46 | POST | `/api/inventaires/{iid}/valider` | Achats | Valider : ajustements |
| 47 | DELETE | `/api/inventaires/{iid}` | Achats | Abandonner un inventaire ouvert |
| 48 | GET | `/api/inventaires/{iid}/feuille` | Connecté | Feuille de comptage imprimable (HTML) |
| 49 | POST | `/api/bons/proposition` | Connecté | Proposition de sortie (recettes + FIFO) |
| 50 | GET | `/api/bons` | Connecté | Ordres de fabrication (bons de sortie) |
| 51 | POST | `/api/bons` | Alimentation | Créer un brouillon d'ordre |
| 52 | PUT | `/api/bons/{bid}` | Alimentation | Modifier un brouillon d'ordre |
| 53 | DELETE | `/api/bons/{bid}` | Alimentation | Supprimer un brouillon d'ordre |
| 54 | POST | `/api/bons/{bid}/valider` | Alimentation | Valider : numéro OF + sorties |
| 55 | POST | `/api/bons/{bid}/annuler` | Alimentation | Annuler un ordre validé (et ses retours) |
| 56 | GET | `/api/bons/{bid}` | Connecté | Un ordre |
| 57 | GET | `/api/bons/{bid}/lots-sortis` | Connecté | Ce que l'ordre a emporté, net des retours, par lot |
| 58 | GET | `/api/export/sorties` | Connecté | Excel des ordres |
| 59 | GET | `/api/production/plan` | Connecté | Plan de toutes les qualités, glissant, tissé du mois |
| 60 | PUT | `/api/production/plan` | Direction | Enregistrer le plan de plusieurs qualités |
| 61 | GET | `/api/production/realise` | Connecté | Plan face au réalisé, plan figé par mois |
| 62 | GET | `/api/production/besoins` | Connecté | MRP détaillé par référence et par mois |
| 63 | GET | `/api/stock` | Connecté (montants masqués alim.) | État du stock par matière (moteur) |
| 64 | GET | `/api/besoins` | Connecté | MRP simple (plan + besoins) |
| 65 | GET | `/api/nomenclature` | Connecté (prix masqués alim.) | Nomenclature (recettes) et contrôle |
| 66 | GET | `/api/plan-achat` | Achats | Plan d'achat |
| 67 | GET | `/api/plan-achat/fournisseur/{nom}` | Achats | Préparation de commande pour un fournisseur |
| 68 | GET | `/api/cockpit` | Achats | Tableau de bord |
| 69 | GET | `/api/valorisation` | Achats | Valorisation du stock au CMUP |
| 70 | GET | `/api/opportunites` | Achats | Opportunités d'économies |
| 71 | GET | `/api/controles` | Achats | Contrôles de cohérence |
| 72 | GET | `/api/prix/historique` | Achats | Historique des prix payés |
| 73 | GET | `/api/receptions/pesees` | Achats | Archive des pesées (qualité) |
| 74 | GET | `/api/receptions/bobines` | Achats | Évolution du poids des bobines |
| 75 | GET | `/api/prix/matrice` | Achats | Prix moyen pondéré par mois et par référence |
| 76 | GET | `/api/fournisseurs/performance` | Achats | Scorecard fournisseurs, réceptions notées |
| 77 | GET | `/api/lots` | Connecté | Stock lot par lot (moteur) |
| 78 | GET | `/api/lots/disponibles` | Connecté | Lots d'une référence qui ont du stock |
| 79 | GET | `/api/tracabilite` | Connecté | Chemin de la matière (lot, ordre, fil) |
| 80 | GET | `/api/ordres-fabrication` | Connecté | Consommation par ordre |
| 81 | GET | `/api/reclamations` | Achats | Réclamations fournisseurs |
| 82 | POST | `/api/reclamations` | Achats | Ouvrir une réclamation |
| 83 | PUT | `/api/reclamations/{rid}` | Achats | Répondre, clore, rouvrir |
| 84 | GET | `/api/signalements` | Connecté | Besoins signalés par l'atelier |
| 85 | POST | `/api/signalements` | Connecté | Signaler un besoin |
| 86 | POST | `/api/signalements/{sid}/traiter` | Achats | Traiter un signalement |
| 87 | GET | `/api/pieces/{objet}/{oid}` | Achats | Pièces jointes d'un document |
| 88 | POST | `/api/pieces/{objet}/{oid}` | Achats | Joindre un fichier |
| 89 | GET | `/api/piece/{pid}/fichier` | Achats | Télécharger une pièce |
| 90 | DELETE | `/api/piece/{pid}` | Achats | Retirer une pièce |
| 91 | GET | `/api/echeancier` | Achats | Échéancier des paiements |
| 92 | PUT | `/api/echeancier/paiement` | Achats | Marquer réglée (ou annuler le règlement) |
| 93 | GET | `/api/qualites/{qid}/versions` | Connecté | Versions successives d'une recette |
| 94 | GET | `/api/indicateurs/historique` | Achats | Photos quotidiennes des indicateurs |
| 95 | GET | `/api/bilan` | Achats | Bilan du mois imprimable (HTML) |
| 96 | GET | `/api/import/matieres/modele` | Achats | Catalogue des matières en tableur (modèle d'import) |
| 97 | POST | `/api/import/matieres` | Achats | Import du tableur des matières (aperçu ou application) |
| 98 | GET | `/api/courriel/apercu` | Direction | Aperçu du courriel du lundi |
| 99 | POST | `/api/indicateurs/photographier` | Direction | Photographier les indicateurs maintenant |
| 100 | GET | `/api/export/pilotage` | Achats | Excel : stock, plan d'achat, fournisseurs, besoins, contrôles |
| 101 | GET | `/api/export/mouvements` | Connecté (colonnes prix retirées alim.) | Excel : journal des mouvements filtré |
| 102 | GET | `/api/export/bon-de-commande/{cid}` | Achats | Excel : bon de commande (français, prix si confirmés) |
| 103 | GET | `/api/export/controles` | Achats | Excel : contrôles + une feuille par contrôle en anomalie |
| 104 | GET | `/api/export/valorisation` | Achats | Excel : valorisation |
| 105 | GET | `/api/export/prix` | Achats | Excel : historique et matrice des prix |
| 106 | GET | `/api/export/opportunites` | Achats | Excel : opportunités |
| 107 | GET | `/api/export/fournisseurs` | Achats | Excel : performance fournisseurs + réceptions notées |
| 108 | GET | `/api/export/journal` | Direction | Excel : journal des actions |
| 109 | GET | `/api/export/echeancier` | Achats | Excel : échéancier |
| — | GET | `/{chemin}` (hors API) | Public | Fichiers de l'écran, sinon `index.html` |

Comptage par module : comptes 22, stock 8, operations 8, inventaires 9, production 10, production_plan 4, pilotage 18, suivi 19, exports 3, exports_analyse 7 → **108**, + `/api/sante` = **109**.

---

## 2. Exploitation et comptes (`main.py`, `api/comptes.py`)

### 2.1 `GET /api/sante` — `sante`, `main.py:190-200`
- **Rôles** : Public. Aucun paramètre.
- **Réponse 200** : `{etat: "ok", schema: int (MAX(schema_version.numero)), version: str (contenu du fichier VERSION à la racine du projet, copie figée de scripts/demarrer.sh ; « projet » s'il est absent), sauvegarde_age_h: float|null (âge en heures du fichier de sauvegarde le plus récent du dossier), sauvegarde_alerte: str ("" si tout va bien)}`.
- `sauvegarde_alerte` (`services/sauvegarde.py:129-144`) : vide si les tâches sont désactivées ; « Les sauvegardes sont arrêtées : pg_dump est introuvable sur le serveur. » ; « La sauvegarde automatique a échoué : <erreur> » ; « Aucune sauvegarde récente. » (au moins un essai fait et dernière > 26 h ou aucune).
- **Refus** : base injoignable → 500 brut.
- **Effets** : aucun.

### 2.2 `GET /api/etat` — `etat`, `comptes.py:54-61`
- **Rôles** : Public.
- **Réponse** : `{installe: bool (au moins un utilisateur existe), societe: str (réglage nom_entreprise, "" sinon)}`.

### 2.3 `GET /api/visages` — `visages`, `comptes.py:64-73`
- **Rôles** : Public.
- **Réponse** : liste des comptes **actifs** triés par nom : `[{identifiant, nom, role (code), role_libelle}]`. Rien d'autre (ni courriel, ni date).

### 2.4 `POST /api/installation` — `installer`, `comptes.py:76-99`
- **Rôles** : Public ; exempté de l'en-tête `X-Gestion-MP`. Ne sert qu'une fois.
- **Corps `Installation`** : `societe: str = ""` (max 160) ; `identifiant: str` (2–40) ; `nom: str` (2–80) ; `secret: str` (8–200).
- **Réponse 201** : le compte créé (forme `_compte`, ci-dessous).
- **Refus** : 409 « Gestion MP est déjà installé : connectez-vous. » (dès qu'un utilisateur existe).
- **Effets** : crée l'utilisateur (`identifiant` minuscule et sans espaces aux bords, `nom` sans espaces aux bords, rôle `direction`, empreinte du secret) ; si `societe` non vide et le réglage `nom_entreprise` existe, le remplace ; journal `installation` / `utilisateur` / id ; ouvre une session (cookie posé).

**Forme `_compte`** (`comptes.py:41-51`) : `{id, identifiant, nom, role, role_libelle, email, actif, vu_le (ISO date-heure ou null)}`.

### 2.5 `POST /api/connexion` — `connexion`, `comptes.py:102-121`
- **Rôles** : Public ; exempté de l'en-tête.
- **Corps `Connexion`** : `identifiant: str` (max 40) ; `secret: str` (max 200). L'identifiant est mis en minuscules et sans espaces aux bords.
- **Réponse 200** : `_compte`.
- **Refus** : 429 « Trop d'essais : patientez N secondes. » (blocage en cours) ; 401 « Identifiant ou code incorrect. » (inconnu, inactif ou mauvais code — même message dans les trois cas ; l'échec est compté et commité).
- **Effets** : supprime le compteur d'échecs ; ouvre une session (cookie, `vu_le`) ; journal `connexion` / `utilisateur` / id.

### 2.6 `POST /api/deconnexion` — `deconnexion`, `comptes.py:124-128`
- **Rôles** : Public ; exempté de l'en-tête. **Réponse** : `{ok: true}`. **Effets** : supprime la session du cookie présenté, efface le cookie. Pas de journal.

### 2.7 `GET /api/moi` — `moi`, `comptes.py:131-133`
- **Rôles** : Connecté. **Réponse** : `_compte` de la personne connectée.

### 2.8 `POST /api/moi/code` — `changer_mon_code`, `comptes.py:136-152`
- **Rôles** : Connecté.
- **Corps `ChangementCode`** : `ancien: str` (max 200) ; `nouveau: str` (max 200).
- **Réponse** : `{ok: true}`.
- **Refus** : 403 « Le code actuel ne correspond pas. » ; 422 « Le nouveau code doit faire au moins N caractères. » (4 alimentation, 8 sinon).
- **Effets** : nouvelle empreinte ; journal `changement de code` / `utilisateur` / id. Les sessions ouvertes restent valides.

### 2.9 `GET /api/utilisateurs` — `comptes`, `comptes.py:167-169`
- **Rôles** : Direction. **Réponse** : tous les comptes (actifs et inactifs), triés par nom, forme `_compte`.

### 2.10 `POST /api/utilisateurs` — `creer_compte`, `comptes.py:158-188`
- **Rôles** : Direction.
- **Corps `CompteEntree`** : `identifiant: str` (2–40) ; `nom: str` (2–80) ; `role: str` (requis) ; `email: str = ""` (max 120, non vérifié) ; `secret: str = ""` (max 200) ; `actif: bool = true`.
- **Réponse 201** : `_compte`.
- **Refus** : 422 « Rôle inconnu. » ; 409 « L'identifiant « x » est déjà pris. » ; 422 « Le code doit faire au moins N caractères. ».
- **Effets** : crée le compte ; journal `création de compte` / `utilisateur` / id / « Nom (Libellé du rôle) ».

### 2.11 `PUT /api/utilisateurs/{uid}` — `modifier_compte`, `comptes.py:191-210`
- **Rôles** : Direction. **Chemin** : `uid: int`.
- **Corps** : `CompteEntree` (même modèle ; `identifiant` est exigé mais **ignoré** — un identifiant ne change pas) ; `secret` vide = code inchangé.
- **Réponse** : `_compte`.
- **Refus** : 404 « Compte introuvable. » ; 422 « Rôle inconnu. » ; 409 « Vous ne pouvez pas retirer vos propres droits de direction. » (sur soi-même : rôle ≠ direction ou actif = faux) ; 422 « Le code doit faire au moins N caractères. » (selon le **nouveau** rôle).
- **Effets** : met à jour nom, rôle, courriel, actif (+ empreinte si secret) ; un compte désactivé perd **toutes ses sessions** ; journal `modification de compte` / `utilisateur` / id / « Nom (Libellé) ».

### 2.12 `GET /api/journal` — `lire_journal`, `comptes.py:213-259`
- **Rôles** : Direction.
- **Requête** : `q: str = ""` (mots, 6 premiers, chacun doit apparaître — insensible à la casse — dans utilisateur, action, objet **ou** détail ; `%`, `_`, `\` échappés) ; `utilisateur: str = ""` (égalité exacte sur le nom) ; `action: str = ""` (égalité) ; `objet: str = ""` (égalité) ; `du: date|null` (quand ≥ du 00:00) ; `au: date|null` (quand < au+1 j) ; `limite: int = 300` (ramené entre 1 et 5 000).
- **Réponse** : du plus récent au plus ancien (id décroissant) : `[{id, quand (ISO à la seconde), utilisateur, role (code), action, objet, objet_id, detail}]`.

### 2.13 `GET /api/journal/valeurs` — `valeurs_du_journal`, `comptes.py:262-270`
- **Rôles** : Direction. **Réponse** : `{utilisateurs: [str], actions: [str], objets: [str]}` — valeurs distinctes non vides, triées.

### 2.14 `GET /api/parametres` — `lire_parametres`, `comptes.py:276-289`
- **Rôles** : Connecté (y compris l'alimentation).
- **Réponse** : `{reglages: [{cle, libelle, famille, unite, echelle (1, ou 100 pour un taux saisi en %), aide, bas, haut (bornes en valeur stockée, null si texte), texte (bool : réglage textuel), defaut, valeur (str stockée ; défaut en texte si absente)}]}` dans l'ordre de `parametres.REGLAGES`. La liste complète des réglages (clés, familles, bornes, défauts) est décrite dans la partie « Réglages » de l'héritage ; les clés lues par la partie B sont : `nom_entreprise`, `secteur`, `adresse`, `telephone`, `ice`, `rc`, `identifiant_fiscal`, `date_cloture`, `adresse_publique`, `courriel_destinataires`, `tolerance_inventaire`, `taux_perte`, `toler_in_full`, `seuil_hausse_forte`, `fenetre_prix_jours`, `cible_otif`, `score_*`, `toler_ecart_pesee`, `toler_poids_bobine`.

### 2.15 `PUT /api/parametres` — `ecrire_parametres`, `comptes.py:292-338`
- **Rôles** : Direction.
- **Corps** : objet JSON libre `{cle: valeur}` où valeur est `str` ou nombre. Les nombres sont envoyés **dans l'unité stockée** (une fraction pour un taux : 0,2 pour 20 %) ; la virgule décimale est acceptée.
- **Traitement par clé** : réglage numérique → `float`, borné `[bas, haut]`, réécrit sans `.0` si entier ; `date_cloture` non vide → date ISO strictement passée ; `adresse_publique` non vide → commence par `http://` ou `https://`, ≤ 200 car., sans espace ; tout autre texte ≤ 500 car. Une valeur identique à l'existante est ignorée.
- **Contrôle d'ordre après écriture** (`ORDRES_PARAMETRES`, `comptes.py:342-352`) — sinon tout est annulé : `seuil_critique < seuil_alerte` ; `seuil_abc_a < seuil_abc_b` ; `seuil_xyz_x < seuil_xyz_y` ; `score_surveiller < score_standard` ; `score_standard < score_strategique`.
- **Réponse** : comme `GET /api/parametres`.
- **Refus (422)** : « Paramètres inconnus : a, b. » ; « « Libellé » attend un nombre. » ; « « Libellé » doit rester entre B et H unité — reçu V. » (bornes et valeur multipliées par l'échelle) ; « On ne clôt qu'une période passée. » ; « Date de clôture illisible (AAAA-MM-JJ). » ; « L'adresse commence par http:// ou https:// (ex. http://mac-usine:8030). » ; « « Libellé » : texte trop long. » ; et les cinq messages d'ordre : « La couverture critique doit rester inférieure à la couverture d'ATTENTION : sinon plus aucune matière ne serait en ATTENTION. », « La part cumulée de la classe A doit rester sous celle de la classe B. », « Le CV maximum de la classe X doit rester sous celui de la classe Y. », « Le score « ATTENTION » doit rester sous le score « standard ». », « Le score « standard » doit rester sous le score « stratégique ». ».
- **Effets** par réglage changé : `Parametre.valeur`, `modifie_le`, `modifie_par` ; une ligne `ParametreHistorique(cle, valeur, par)` ; journal `paramètre` / `parametre` / null / « Libellé : avant → après » (valeurs lisibles : virgule décimale, taux en %, unité ; « — » pour vide — `_lisible`, `comptes.py:355-366`). Rouvrir/fermer la période close passe par ici (`date_cloture`).

### 2.16 `GET /api/parametres/historique` — `historique_parametres`, `comptes.py:369-387`
- **Rôles** : Direction.
- **Réponse** : les 500 derniers changements, du plus récent : `[{cle, libelle (ou la clé si réglage disparu), valeur, avant (valeur précédente du même réglage, sinon son défaut ; null si réglage inconnu), quand (ISO à la minute), par}]`. Contient aussi les cours de devise (clés `cours_XXX`).

### 2.17 `GET /api/devises` — `devises`, `comptes.py:400-413`
- **Rôles** : Connecté.
- **Réponse** : triées par code : `[{code, nom, taux (MAD pour 1 unité), actif, cours_le (ISO minute du dernier changement de cours historisé, null sinon)}]`.

### 2.18 `GET /api/devises/{code}/historique` — `historique_devise`, `comptes.py:416-427`
- **Rôles** : Connecté. **Chemin** : `code` (mis en majuscules, 3 premiers caractères).
- **Réponse** : 500 derniers cours, du plus récent : `[{taux: float, quand, par}]`.

### 2.19 `PUT /api/devises` — `ecrire_devise`, `comptes.py:393-446`
- **Rôles** : Achats.
- **Corps `DeviseEntree`** : `code: str` (exactement 3 car., mis en majuscules) ; `nom: str = ""` (max 40) ; `taux: float` (> 0, ≤ 10 000) ; `actif: bool = true`.
- **Réponse** : la liste des devises (forme `GET /api/devises`).
- **Refus** : 422 « Le dirham est la devise de référence : son cours reste 1. » (MAD avec taux ≠ 1).
- **Effets** : crée la devise ou met à jour `taux`, `actif`, `nom` (un nom vide garde l'ancien) ; **toujours** une ligne `ParametreHistorique(cle="cours_CODE", valeur=taux, par)` même si rien n'a changé ; journal `cours de change` / `devise` / null / « CODE : 10,8 MAD ». Le cours figé sur les commandes et mouvements passés ne change pas.

### 2.20 `GET /api/sauvegardes` — `lister_sauvegardes`, `comptes.py:473-494`
- **Rôles** : Direction.
- **Réponse** (`etat_sauvegardes`) : `{derniere (date-heure de la plus récente de **cette** base), age_h, nb (fichiers de cette base), alerte, dossier, copie, base (nom de la base courante), autres (nombre de fichiers d'autres bases), fichiers: [{nom, taille (octets), quand, base (lue dans l'en-tête du fichier par pg_restore --list, "" si illisible), autre_base: bool}] (30 premiers, du plus récent)}`. Alerte supplémentaire : « Aucune sauvegarde de la base « X » : le dossier ne contient que d'autres bases. ». Le nom de base d'un fichier est mis en cache (chemin + date de modification).

### 2.21 `POST /api/sauvegardes` — `sauvegarder`, `comptes.py:497-502`
- **Rôles** : Direction. Pas de corps.
- **Réponse** : `etat_sauvegardes()`.
- **Effets** : fichier `gestion-mp-AAAA-MM-JJ-HHMMSS-manuelle.dump` (pg_dump -Fc, relu, copie externe, miroir des pièces jointes) ; journal `sauvegarde` / `sauvegarde` / null / nom du fichier.
- **Refus** : pg_dump absent ou en échec → `RuntimeError` non traduite : **500** générique (messages internes « pg_dump est introuvable : installez les outils de PostgreSQL ou indiquez leur dossier dans GESTION_MP_PG_BIN. », « pg_dump a échoué : … », « Sauvegarde illisible : … »).

### 2.22 `GET /api/etat-serveur` — `etat_serveur`, `comptes.py:505-560`
- **Rôles** : Direction.
- **Réponse** : `{version (app.version = "1.0.0"), schema, python, systeme ("Darwin 25.6.0"…), machine (nom court de l'hôte), base: {nom, hote ("ce serveur (connexion locale)" si vide), port (5432 par défaut), version (SHOW server_version), taille (octets)}, adresse_reseau ("http://IP:port"), port, https, taches, duree_session_jours, sauvegardes: {dossier, copie, pg_dump (chemin ou ""), pg_restore, nb, derniere, politique: "une par jour gardée 14 jours, puis la première de chaque mois gardée 12 mois ; les manuelles et « avant restauration » ne s'effacent jamais seules"}, sessions: [{nom, role (libellé), vu_le, nb (sessions non expirées), expire_le (la plus lointaine, ISO minute)}]}`.
- L'IP réseau est obtenue par un « connect » UDP fictif vers 10.255.255.255 (aucun paquet), 127.0.0.1 à défaut (`stock.py:322-329`).

### 2.23 `POST /api/sauvegardes/{nom}/restaurer` — `restaurer`, `comptes.py:563-580`
- **Rôles** : Direction. **Chemin** : `nom` (seul le nom de fichier est gardé : pas de chemin).
- **Réponse** : `etat_sauvegardes()`.
- **Refus** : 409 « Cette sauvegarde est celle de la base « A », pas de « B » : la restaurer remplacerait toutes les données par celles d'une autre base. » ; 404 « Sauvegarde introuvable. » (fichier absent ou ne commençant pas par `gestion-mp-`) ; 500 « pg_restore est introuvable sur le serveur. » ; 500 « La restauration a échoué : … » ; fichier illisible → 500 générique.
- **Effets** (`services/sauvegarde.py:163-197`) : commit et fermeture de la session de la requête ; relecture du fichier ; **sauvegarde « avant-restauration »** de l'état actuel ; fermeture du pool et **coupure de toutes les autres connexions** à la base (`pg_terminate_backend`) ; `pg_restore --clean --if-exists --no-owner` ; journal (dans la base restaurée) `restauration` / `sauvegarde` / « nom du fichier », utilisateur = auteur, rôle `direction`. Toutes les sessions sont celles de la sauvegarde.

---

## 3. Stock (`api/stock.py`)

Routeur avec `dependencies=[Depends(acteur)]` : toutes les routes exigent une session.

Statut d'un lot (calculé, jamais stocké — `stock.py:31-57`), avec `POUSSIERE = 0,001 kg` : `partiel` « En partie en quarantaine » (quarantaine > 0 et disponible > 0) ; `quarantaine` « En quarantaine » ; `disponible` « Disponible » ; `epuise` « Épuisé ». « Quarantaine » = magasin de type `Quarantaine` ; tout autre magasin compte en disponible.

Types de mouvement (codes Gestion MP, `modeles.py:486-494`) : `OUVERTURE` « Stock d'ouverture », `RECEPTION` « Entrée de réception », `SORTIE` « Sortie vers les machines », `RETOUR_MACHINE` « Retour des machines », `RETOUR_FOURNISSEUR` « Retour au fournisseur », `AJUSTEMENT` « Ajustement d'inventaire », `TRANSFERT` « Transfert entre magasins ». Documents : `reception`, `sortie` (ordre), `operation`, `inventaire` (vide pour la reprise de l'ERP Fil).

### 3.1 `GET /api/mouvements` — `mouvements`, `stock.py:90-153`
- **Rôles** : Connecté ; prix masqués pour l'alimentation (§ 0.5).
- **Requête** : `article_id: int|null` ; `lot_id: int|null` ; `magasin_id: int|null` ; `type: str = ""` (code exact) ; `document: str = ""` (exact) ; `du`, `au: date|null` (bornes incluses sur `date_effet`) ; `q: str = ""` (max 80 ; chaque mot, `ILIKE %mot%`, doit apparaître dans la référence, la désignation, le n° de lot, le n° de document, le motif, le commentaire ou l'auteur ; non échappé) ; `limite: int = 1000` (1–5 000) ; `decalage: int = 0` ; `avec_valeur: bool = false`.
- **Tri** : `date_effet` décroissante puis id décroissant.
- **Réponse** : `{lignes: [Mouvement], tronque: bool (il reste des lignes), decalage, suivant: int|null (decalage + limite s'il reste), types: {code: libellé}}`.
- **Mouvement** (`_mouvement_dict`, `stock.py:74-87`) : `id, date (date d'effet ISO), saisi_le (ISO minute), type, libelle, article_id, reference, lot_id, lot (numéro), magasin_id, magasin (code), quantite (kg signés), prix (prix d'achat de l'entrée dans sa devise), devise, cours (MAD par unité, figé), document, document_id, document_numero, ordre_id (ordre servi ou d'où revient la matière), paire (id commun aux deux lignes d'un transfert), motif, commentaire, auteur, contrepasse_id (mouvement que celui-ci annule)`. Avec `avec_valeur` : `cout_mad` (coût unitaire du mouvement au moment où il a eu lieu, calcul identique à la Valorisation — `moteur.couts_du_journal` ; la ligne d'arrivée d'un transfert prend le coût de sa ligne de départ ; à défaut, le CMUP actuel de la référence ; sinon 0) et `valeur_mad = quantite × cout_mad`.
- **Refus** : 422 « Décalage négatif. » ; 422 validation (`limite`, `q`).

### 3.2 `GET /api/soldes` — `soldes`, `stock.py:196-257`
- **Rôles** : Connecté.
- **Requête** : `q: str = ""` (max 80 ; chaque mot dans référence, désignation, n° de lot, rôle, code magasin ou nom du fournisseur du lot — à défaut celui de la matière) ; `article_id`, `fournisseur_id` (fournisseur du lot **ou** de la matière), `magasin_id` : `int|null` ; `en_stock: bool = true` (soldes > 0,001 seulement) ; `avec_historique: bool = false`.
- **Tri** : référence, date d'entrée du lot, id.
- **Réponse** : une entrée par lot : `{lot_id, lot, article_id, reference, designation, role, kg_par_ml (densité si rôle linéaire, 0 sinon), fournisseur, entre_le, poids_bobine (du lot, sinon du catalogue), bobines_palette, quantite (Σ des soldes retenus), disponible (hors quarantaine), quarantaine, magasins: [{magasin_id, magasin, type, quantite}] (soldes non nuls), bobines (arrondi quantite / poids_bobine, null sans poids), statut}`. Avec `avec_historique` : `entre` (kg reçus, hors transferts et annulations), `sorti` (net : un retour des machines le diminue), `dernier_mouvement` (ISO), `ordres: [{id, numero}]` (ordres servis par des sorties non annulées) — `historique_lots`, `stock.py:156-193`.
- Attention : avec `magasin_id` ou `en_stock`, `quantite`/`disponible`/`quarantaine` ne portent que sur les soldes retenus par le filtre.

### 3.3 `GET /api/lots/{lid}` — `lot`, `stock.py:260-305`
- **Rôles** : Connecté ; prix des mouvements masqués pour l'alimentation. **Chemin** : `lid: int` (convertisseur `int`).
- **Réponse** : `{lot_id, lot, entre_le, article_id, reference, designation, role, kg_par_ml, poids_bobine, bobines_palette, commentaire (du lot), fournisseur, quantite (total tous magasins), bobines, disponible, statut, entre, sorti, dernier_mouvement, ordres: [{id, numero}], soldes: [{magasin_id, magasin, type, quantite}], reception: {id, numero, date, bl (n° de BL), facture (n° ou ""), pesee (quantite_pesee), qualite} | null (première réception **validée** qui a fait entrer le lot), mouvements: [Mouvement] (ordre chronologique)}`.
- **Refus** : 404 « Lot introuvable. ».

### 3.4 `GET /api/lots/scan` — `scan`, `stock.py:308-319`
- **Rôles** : Connecté.
- **Requête** : `code: str` (1–300, requis) — l'adresse lue dans un QR (`…/lot/123`) ou un numéro de lot.
- **Réponse** : `[{lot_id, lot, reference, quantite (Σ des soldes, quarantaine comprise)}]` — un seul lot si l'adresse contient `/lot/<id>` (vide si l'id n'existe pas), sinon tous les lots dont le numéro est égal (insensible à la casse, espaces aux bords retirés) — un même numéro peut exister pour plusieurs matières.

### 3.5 `GET /api/acces` — `acces`, `stock.py:345-351`
- **Rôles** : Connecté.
- **Réponse** : `{adresse_reseau: "http://<IP du serveur>:<port>", nom_machine: "http://<nom d'hôte court en minuscules>:<port>", adresse_qr: <adresse que contiennent les QR>}` — port = celui de la requête, 80 à défaut.
- **Adresse des QR** (`adresse_pour_telephone`, `stock.py:332-342`) : le réglage `adresse_publique` s'il est rempli (sans `/` final) ; sinon l'URL de base de la requête ; si l'hôte est `localhost`, `127.0.0.1`, `::1` ou `*.localhost`, il est remplacé par l'IP réseau (`<schéma>://<IP>:<port ou 80>`).

### 3.6 `GET /api/acces/qr` — `acces_qr`, `stock.py:354-358` (document, § 12.4)
- **Rôles** : Connecté. **Réponse** : `text/html` contenant **uniquement** un élément `<svg>` (QR de l'adresse des QR, correction M, échelle 6, marge 2 modules).

### 3.7 `GET /api/lots/etiquettes` — `etiquettes`, `stock.py:361-415` (document, § 12.3)
- **Rôles** : Connecté. **Requête** : `ids: str` (requis, max 4 000) — ids de lots séparés par des virgules ; les éléments non numériques et les ids inconnus sont ignorés.
- **Réponse** : page HTML d'étiquettes.
- **Refus** : 404 « Aucun lot à étiqueter. ».

### 3.8 `GET /api/controles/soldes` — `controle_soldes`, `stock.py:418-433`
- **Rôles** : Achats.
- **Réponse** : `{conforme: bool (aucun écart et aucun solde négatif), ecarts: [{lot_id, magasin_id, journal (Σ des mouvements), solde (solde tenu)}] (écart > 0,001), negatifs: int (soldes < −0,001), lots: int (nombre de soldes tenus)}`.

---

## 4. Opérations de stock (`api/operations.py`)

Une opération est un document : brouillon (corrigeable, supprimable, sans numéro, sans effet sur le stock) → validée (numéro, mouvements) → annulée (contre-passation, une fois). Statuts : `brouillon`, `validee`, `annulee`.

| Type | Libellé | Série | Mouvement écrit | Qui (en plus de la direction) |
|---|---|---|---|---|
| `ouverture` | Stock d'ouverture | `OUV` | `OUVERTURE` (+) | achats |
| `retour_machine` | Retour des machines | `RET` | `RETOUR_MACHINE` (+), `ordre_id` = l'ordre | alimentation |
| `transfert` | Transfert entre magasins | `TRF` | 2 × `TRANSFERT` (−source, +destination, même `paire`) | achats, alimentation |
| `ajustement` | Ajustement justifié | `AJU` | `AJUSTEMENT` (signé) | achats |
| `retour_fournisseur` | Retour au fournisseur | `RFO` | `RETOUR_FOURNISSEUR` (−) | achats |

Motifs proposés (`MOTIFS`, `operations.py:36-45`) et codes ERP Fil (`CODES_MOTIF`, `:49-53`) :
- `retour_machine` : « Reliquat de fin d'ordre » (R1), « Changement de série / arrêt machine » (R2), « Erreur de prélèvement » (R4) ;
- `retour_fournisseur` : « Non-conformité qualité » (R3), « Excédent de réception » (R5), « Bobines endommagées » (R6), « Refus après quarantaine » (R3) ;
- `ajustement` : « Écart constaté au comptage », « Matière retrouvée », « Perte / casse », « Correction de saisie » (sans code) ;
- `transfert` : « Rangement », « Libération de quarantaine », « Mise en quarantaine », « Approvisionnement de l'atelier ».
Le motif n'est pas restreint à cette liste côté serveur (texte libre ≤ 80), sauf les deux motifs de quarantaine imposés.

**Contrôle par type** (`_autorise`, `operations.py:64-69`), appliqué après `STOCK` à toutes les écritures : 422 « Type d'opération inconnu. » ; 403 « « Libellé du type » est réservé à : responsable achats[, responsable alimentation machines]. ».

**Forme `operation_dict`** (`operations.py:173-198`) : `{id, numero (null en brouillon), type, type_libelle, statut, date, bon_id, bon (n° de l'ordre ou ""), fournisseur_id, fournisseur, motif, code_motif (R1…R6 ou ""), commentaire, cree_par, validee_par, cree_le, validee_le (ISO minute), lignes: [{id, article_id, reference, kg_par_ml, lot_id, lot (numéro du lot ou numéro saisi), magasin_id, magasin, magasin_destination_id, magasin_destination, quantite (kg, signée pour un ajustement), prix, devise}], total (Σ quantités), blocages: [str]}`.

**Blocages** (`blocages_operation`, `operations.py:78-138`), calculés sans rien écrire, seulement pour un brouillon (sinon `[]`), sans doublons : « aucune ligne » ; les refus de `date_permise` ; « l'inventaire INV-… est en cours (CODE | tous les magasins) » pour tout inventaire ouvert sur un magasin touché ou sur tous ; pour transfert/retour fournisseur (et ajustement négatif), par lot et magasin : « lot L de R : épuisé | N seulement dans « X », M demandés » puis la règle de présence à la date (`couvert_a_sa_date`) ; « le magasin « X » est désactivé » (destination d'un transfert, magasin d'une autre opération, sauf retour fournisseur) ; retour des machines : « daté du JJ/MM/AAAA, avant l'ordre OF-… du JJ/MM/AAAA » et « lot L : seulement N kg partis pour cet ordre, M kg rendus ».

### 4.1 `GET /api/operations/motifs` — `motifs`, `operations.py:72-75`
- **Rôles** : Connecté. **Réponse** : `{types: {code: libellé}, motifs: {type: [motifs]}, codes: {motif: code R}, droits: {type: [rôles]}}`.

### 4.2 `GET /api/operations` — `operations`, `operations.py:209-216`
- **Rôles** : Connecté ; `prix`/`devise` des lignes masqués pour l'alimentation.
- **Requête** : `type: str = ""` (filtre exact). **Réponse** : au plus **1 000** opérations, date décroissante puis id décroissant, forme `operation_dict`.

### 4.3 `GET /api/operations/{oid}` — `operation`, `operations.py:219-224`
- **Rôles** : Connecté (masquage idem). **Refus** : 404 « Opération introuvable. ».

### 4.4 Corps commun `OperationEntree` (`operations.py:227-247`)
- `type: str` (requis) ; `date: date` (requise) ; `bon_id: int|null` ; `motif: str = ""` (max 80) ; `commentaire: str = ""` (max 300) ; `lignes: [LigneOperation]` (au moins 1).
- `LigneOperation` : `article_id: int` ; `lot_id: int|null` ; `lot_numero: str = ""` (max 80) ; `magasin_id: int` ; `magasin_destination_id: int|null` ; `quantite: float` (−1e9 à 1e9) ; `unite: str = ""` (max 10 ; vide = kg ; `kg`, `Bobine`, `Palette`) ; `prix: float = 0` (0 à 1e7, ouverture seulement) ; `devise: str = "MAD"` (max 3, ouverture seulement).

**Remplissage** (`_remplir`, `operations.py:250-332`) — refus 422 sauf mention :
1. `date_permise(date)`.
2. Retour machine, retour fournisseur, ajustement sans motif : « Choisir le motif : il dit pourquoi le stock bouge. »
3. Ajustement avec un commentaire de moins de 5 caractères (espaces retirés) : « Un ajustement se justifie : écrire en quelques mots ce qui a été constaté. »
4. Retour machine : l'ordre `bon_id` doit exister et être **validé** : « Un retour des machines se rattache à l'ordre d'où la matière revient. » ; date ≥ date de l'ordre : « Ce retour est daté du JJ/MM/AAAA, avant l'ordre OF-… du JJ/MM/AAAA : la matière n'était pas encore partie. Dater le retour du jour où elle est revenue. ». Pour les autres types, `bon_id` est mis à null.
5. Les lignes existantes sont **toutes remplacées**. Par ligne : « Matière inconnue. » ; « Magasin inconnu. » ; « Ce lot est d'une autre matière. » ; unité hors liste : « Unité : kg, bobine ou palette — le cuir, les franges et le ruban se comptent aussi en kilos. » ; ouverture en Bobine/Palette : « Un stock d'ouverture se saisit en kg : il fixe le prix au kilo. » ; conversion en kg (`en_unite_de_stock`, arrondi 3 décimales, bobine = poids du lot sinon du catalogue, palette = bobine × bobines/palette ; refus « « R » : le nombre de bobines par palette n'est pas connu, saisir en bobines ou en kg. » ou « « R » : le poids de bobine n'est pas connu, saisir en kg. »), le signe saisi est conservé.
6. Ouverture : devise ≠ MAD inconnue : « « R » : devise inconnue (« X »). L'ajouter d'abord dans Réglages › Devises, avec son cours. » ; numéro de lot vide : « « R » : le numéro de lot du stock d'ouverture manque. » ; quantité ≤ 0 : « Un stock d'ouverture est positif. ».
7. Ajustement : ni lot ni numéro : « Désigner le lot ajusté (ou en nommer un, pour une matière retrouvée). » ; quantité nulle : « Un ajustement ne peut pas être nul. ».
8. Autres types : lot obligatoire : « « R » : choisir le lot. » ; quantité ≤ 0 : « La quantité est positive. ».
9. Transfert : « Un transfert va d'un magasin à un autre. » ; « Magasin de destination inconnu. » ; sortie de quarantaine vers un magasin non-quarantaine par un rôle autre qu'achats/direction : **403** « Libérer une quarantaine est une décision des achats, après contrôle de la matière. » ; motif ≠ « Libération de quarantaine » : « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». » ; entrée en quarantaine depuis un magasin non-quarantaine avec un motif ≠ « Mise en quarantaine » : « Une entrée en quarantaine se fait avec le motif « Mise en quarantaine ». ».
10. Retour fournisseur : les lots doivent venir d'un seul fournisseur (`lot.fournisseur_id`) : « Un retour au fournisseur ne mêle pas deux fournisseurs. » ; `fournisseur_id` de l'opération = ce fournisseur.
11. Ligne enregistrée : `lot_numero` = saisi ou numéro du lot ; destination seulement pour un transfert ; `prix` et `devise` (majuscules) seulement pour une ouverture (sinon 0 et MAD).

### 4.5 `POST /api/operations` — `creer`, `operations.py:345-356`
- **Rôles** : Stock*. **Corps** : `OperationEntree`. **Réponse 201** : `operation_dict` (non masqué).
- **Effets** : opération `brouillon`, `cree_par` ; journal `<libellé du type en minuscules> (brouillon)` / `operation` / id / « brouillon n° ID ». Aucun mouvement.

### 4.6 `PUT /api/operations/{oid}` — `modifier`, `operations.py:366-378`
- **Rôles** : Stock* (contrôle sur le type existant). Opération verrouillée (`FOR UPDATE`).
- **Refus** : 404 « Opération introuvable. » ; 409 « Une opération validée ne se modifie plus : l'annuler. » ; 422 « Le type d'une opération ne change pas. » ; + remplissage.
- **Effets** : lignes remplacées ; journal `modification opération` / `operation` / id / nom.

### 4.7 `DELETE /api/operations/{oid}` — `supprimer`, `operations.py:381-392`
- **Rôles** : Stock*. **Réponse** : `{ok: true}`.
- **Refus** : 404 ; 409 « Une opération validée ne se supprime pas : l'annuler. ».
- **Effets** : suppression (lignes comprises) ; journal `suppression opération` / `operation` / id / « brouillon n° ID ».

### 4.8 `POST /api/operations/{oid}/valider` — `valider`, `operations.py:395-442`
- **Rôles** : Stock*. Pas de corps.
- **Refus** : 404 ; 409 « Cette opération est déjà validée. » ; `date_permise` ; transfert d'un magasin de quarantaine vers un non-quarantaine par l'alimentation : 403 « Libérer une quarantaine est une décision des achats, après contrôle de la matière. » ; retour machine : refus de date avant l'ordre (422) et 409 « Le lot « L » n'est sorti que de N kg pour cet ordre (M kg rendus) : on ne rend pas plus que ce qui est parti. » (rendu = Σ des lignes du lot ; sorti = −Σ des mouvements de l'ordre sur ce lot, retours déjà validés déduits ; tolérance 0,001) ; tous les refus de l'écriture du stock (§ 0.7).
- **Effets** : numéro pris à la validation (`SERIE-AAAA-NNNN`, année de la date de l'opération) ; ordre verrouillé pour un retour machine ; mouvements (communs : date = date de l'opération, `document="operation"`, `document_id`, `document_numero`, `auteur`, `motif`, `commentaire`) : transfert → `transferer` ; sinon, si la ligne n'a pas de lot (ouverture, matière retrouvée), **création du lot** (`lot_ou_creer` : numéro saisi, entré le = date de l'opération) ; quantité négative pour un retour fournisseur ; prix/devise pour l'ouverture ; `ordre_id` pour un retour machine. Statut `validee`, `validee_par`, `validee_le`. Journal `validation — <libellé en minuscules>` / `operation` / id / numéro. Pour un retour fournisseur ou un transfert : recalage du statut des bons de commande dont une réception validée a fait entrer ces lots (`achats.recaler_soldes` : un bon envoyé/confirmé entièrement reçu net des retours et sans reste en quarantaine se solde, journal `commande soldée` ; un bon soldé automatiquement que le retour dégarnit se rouvre).

### 4.9 `POST /api/operations/{oid}/annuler` — `annuler`, `operations.py:445-457`
- **Rôles** : Stock*.
- **Refus** : 404 ; 409 « Seule une opération validée s'annule ; un brouillon se supprime. » ; refus de la contre-passation (§ 0.7, dont la période close et les quantités : on ne peut annuler un transfert si la matière est déjà repartie de la destination).
- **Effets** : contre-passation de tous les mouvements du document ; statut `annulee` ; journal `annulation opération` / `operation` / id / numéro ; recalage des bons (raison « RET-… annulé »).

---

## 5. Inventaires (`api/inventaires.py`)

Principe : à l'ouverture, le stock théorique de chaque lot du périmètre est **figé** ; tant que l'inventaire est ouvert, aucun mouvement n'est accepté sur les magasins concernés (sauf les siens) ; un premier comptage hors tolérance peut être recompté par une autre personne (le second l'emporte) ; la validation écrit un `AJUSTEMENT` par écart. Statuts : `ouvert`, `valide`. Cadence de l'inventaire tournant : A 30 j, B 90 j, C 365 j (`CADENCE_JOURS`).

Hors tolérance (`_hors`, `inventaires.py:40-46`) : écart `|compté − théorique| ≥ 0,001` **et** (théorique ≤ 0 **ou** `|écart| / théorique > tolérance`). `retenu` = second comptage s'il existe, sinon premier. `a_recompter` = pas de second comptage et premier comptage hors tolérance.

**Forme `inventaire_dict`** (`inventaires.py:67-128`) : `{id, numero, libelle, statut, date, magasin_id (null = tous), magasin (code ou « Tous les magasins »), tolerance (fraction), cree_par, valide_par, valide_le, nb_lignes, nb_comptees (lignes dont le retenu existe), hors_tolerance (nombre), a_recompter (nombre), recomptees (nombre), ecart_total (Σ écarts signés, kg), ecart_absolu (Σ |écarts|), ecart_valeur_mad (Σ écarts × coût), ecart_valeur_absolue_mad, lignes?}` — `lignes` seulement pour le détail : `[{id, lot_id, lot, article_id, reference, designation, kg_par_ml, poids_bobine, bobines_palette, magasin_id, magasin, theorique, compte (premier comptage), justification, palettes, bobines (nombres comptés, information), second_compte, second_par, retenu, ecart, cmup_mad, valeur_ecart_mad, hors_tolerance: bool, a_recompter: bool}]`. Coût d'un écart : celui de l'ajustement qu'il a écrit (inventaire validé, mouvement non annulé), sinon le CMUP actuel de la référence (calcul de la Valorisation).

### 5.1 `GET /api/inventaires` — `inventaires`, `inventaires.py:165-169`
- **Rôles** : Connecté ; montants masqués pour l'alimentation. **Réponse** : tous les inventaires, id décroissant, sans `lignes`.

### 5.2 `GET /api/inventaires/defauts` — `defauts`, `inventaires.py:172-186`
- **Rôles** : Connecté. **Réponse** : `{tolerance (réglage tolerance_inventaire), roles: [rôles des matières qui ont du stock], compositions: [idem], cadence_jours: {"A":30,"B":90,"C":365}}`.

### 5.3 `GET /api/inventaires/a-compter` — `a_compter`, `inventaires.py:194-244`
- **Rôles** : Connecté. **Requête** : `magasin_id: int|null`.
- **Réponse** : matières dues, triées par classe (A, B, C), date du dernier comptage (jamais compté d'abord), référence : `[{article_id, reference, role, classe_abc (du moteur ; « C » à défaut), stock (Σ des magasins dus), kg_par_ml, dernier_comptage (ISO ou null : le plus ancien des magasins dus), jours (ancienneté), magasins: [codes]}]`. Une matière est due dans un magasin où elle a du stock si elle n'y a jamais été comptée (inventaire **validé**, ligne comptée) ou si le dernier comptage date d'au moins la cadence de sa classe.

### 5.4 `GET /api/inventaires/{iid}` — `inventaire`, `inventaires.py:247-252`
- **Rôles** : Connecté ; montants masqués pour l'alimentation. **Refus** : 404 « Inventaire introuvable. ».

### 5.5 `POST /api/inventaires` — `ouvrir`, `inventaires.py:255-317`
- **Rôles** : Achats.
- **Corps `InventaireEntree`** : `libelle: str = ""` (max 120 ; « Inventaire » si vide) ; `date: date` ; `magasin_id: int|null` (null = tous les magasins) ; `tolerance: float|null` (0–1 ; null = réglage) ; `articles: [int] = []` ; `roles: [str] = []` ; `compositions: [str] = []` ; `classes_abc: [str] = []`. Le périmètre = soldes > 0 du magasin qui passent **tous** les critères donnés.
- **Refus** : `date_permise` ; 422 « Magasin inconnu. » ; 409 « L'inventaire INV-… est déjà ouvert sur ce magasin. » (un inventaire ouvert sur ce magasin ou sur tous ; si l'on ouvre « tous les magasins », n'importe quel inventaire ouvert) ; 422 « Matière inconnue : n° 1, 2. » (5 premiers) ; 422 « Classe ABC : A, B ou C. » ; 409 « L'inventaire est daté du JJ/MM/AAAA, mais des lots qu'il fige ont bougé depuis : « R », lot L (le JJ/MM/AAAA), … [ …]. Un comptage porte sur le stock d'aujourd'hui : le dater au plus tôt du dernier mouvement. » (5 premiers).
- **Effets** : numéro `INV-AAAA-NNNN` ; soldes du périmètre verrouillés (`FOR UPDATE`) et figés en lignes (`theorique` = solde) ; journal `ouverture inventaire` / `inventaire` / id / « INV-… · N lot(s) figés ». Les mouvements sont dès lors suspendus sur ces magasins.
- **Réponse 201** : `inventaire_dict` complet.

### 5.6 `POST /api/inventaires/{iid}/comptage` — `compter`, `inventaires.py:320-378`
- **Rôles** : Achats.
- **Corps** : **tableau** `[Comptage]` ; `Comptage` : `ligne_id: int|null` ; `article_id: int|null` ; `lot_numero: str = ""` (max 80) ; `magasin_id: int|null` ; `compte: float|null` (0–1e9) ; `palettes: float|null` (0–1e5) ; `bobines: float|null` (0–1e6) ; `justification: str = ""` (max 300) ; `second_compte: float|null` (0–1e9 ; **absent** = inchangé, `null` explicite = effacé).
- **Comportement** : avec `ligne_id`, la ligne reçoit `compte`, `justification`, `palettes`, `bobines` **tels qu'envoyés** (un champ absent vaut null : il efface) ; `second_compte` présent → enregistré avec `second_par` = la personne (vide s'il est effacé) ; si `second_compte` absent et `compte` null → le second comptage est effacé. Sans `ligne_id` : un **lot trouvé** — ligne ajoutée avec `theorique = 0` ; le lot est créé s'il n'existe pas (`lot_ou_creer`, entré le = date de l'inventaire).
- **Refus** : 404 « Inventaire introuvable. » ; 409 « Cet inventaire est déjà validé. » ; 422 « Ligne étrangère à cet inventaire. » ; 422 « « R », lot L : un recomptage suit un premier comptage. » ; 422 « Un lot trouvé se décrit : matière, numéro de lot, magasin. » ; 422 « Matière inconnue. » ; 422 « Magasin inconnu. » ; 422 « Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé. » ; 422 « Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne. ».
- **Effets** : journal `comptage` / `inventaire` / id / « INV-… · N ligne(s) ». **Réponse** : `inventaire_dict` complet.

### 5.7 `POST /api/inventaires/{iid}/valider` — `valider`, `inventaires.py:381-415`
- **Rôles** : Achats.
- **Refus** : 404 ; 409 « Cet inventaire est déjà validé. » ; 422 « Aucun lot compté : saisir les comptages avant de valider. » ; 422 « Écart hors tolérance sans justification : R1, R2. » (justification < 3 caractères ; 8 premières) ; `date_permise` ; 409 « L'inventaire est daté du … ont bougé depuis … » (lots avec écart seulement) ; refus de l'écriture du stock.
- **Effets** : pour chaque ligne comptée dont l'écart (retenu − théorique) ≥ 0,001 en valeur absolue : mouvement `AJUSTEMENT` de l'écart, daté de l'inventaire, `document="inventaire"`, motif « Écart d'inventaire », commentaire « justification · recompté par X » (300 car.) ; statut `valide` ; journal `validation inventaire` / `inventaire` / id / « INV-… · N lot(s) comptés · M ajustement(s) ». Les lignes non comptées n'ajustent rien.

### 5.8 `DELETE /api/inventaires/{iid}` — `abandonner`, `inventaires.py:418-430`
- **Rôles** : Achats. **Réponse** : `{ok: true}`.
- **Refus** : 404 ; 409 « Un inventaire validé reste : ses ajustements sont au journal. ».
- **Effets** : suppression de l'inventaire et de ses lignes ; les mouvements reprennent ; journal `abandon inventaire` / `inventaire` / id / numéro. Les lots créés par « lot trouvé » restent.

### 5.9 `GET /api/inventaires/{iid}/feuille` — `feuille`, `inventaires.py:433-504` (document, § 12.2)
- **Rôles** : Connecté. **Requête** : `theorique: bool = false` ; `recomptage: bool = false` (implique le théorique ; seulement les lignes « à recompter »).
- **Refus** : 404 « Inventaire introuvable. ».

---

## 6. Alimentation des machines : ordres de fabrication (`api/production.py`)

Un « bon de sortie » = un **ordre de fabrication** (OF) : une ou plusieurs qualités et leurs m² (`fabrications`), un magasin d'origine, un métier facultatif, des lignes lot par lot. Statuts : `brouillon` → `valide` (numéro `OF-AAAA-NNNN`, sorties écrites ensemble) → `annule` (contre-passation, avec ses retours). Les numéros suivent les dates : on ne valide pas un ordre daté avant le dernier ordre non-brouillon. Unités de saisie : `kg` (défaut), `Bobine`, `Palette` (`UNITES`, `production.py:30`).

**Forme `bon_dict`** (`production.py:385-416`) : `{id, numero (null en brouillon), statut, date, magasin_id, magasin (code), metier_id, metier (nom, sinon code, "" sans métier), commentaire, cree_par, valide_par, cree_le, valide_le (ISO minute), fabrications: [{qualite_id, qualite (code), nom, m2}], lignes: [{id, article_id, reference, designation, kg_par_ml, lot_id, lot, quantite (kg), poids_bobine (lot, sinon catalogue), bobines_palette}], total (Σ kg des lignes), retours: [numéros des retours], retours_detail: [{id (opération, null pour une reprise), numero (n° RET-… ou « retour repris de l'ERP Fil du JJ/MM/AAAA »), date, quantite (kg)}], revenu (Σ des retours), theorique (prévu par la recette, perte comprise, kg ; 0 sans calcul), net (sorti − revenu ; Σ des lignes à défaut), ecart (net − théorique, null sans théorique), ecart_relatif, par_fil: [{reference, quantite (net), theorique (perte comprise), ecart, hors_recette, kg_par_ml}], blocages: [str]}`. Pas de prix.
- `retours` (`retours_par_ordre`, `production.py:357-382`) : lus au journal (mouvements `RETOUR_MACHINE` portant l'ordre), hors retours annulés et leurs annulations ; un retour par document et par jour ; ceux de la reprise de l'ERP Fil sont regroupés par jour.
- `theorique`/`net`/`par_fil` viennent de `consommations()` (`production.py:87-90`, `moteur.consommation_par_of` ajusté par `ajuster_ordre` `:65-84`) : prévu = kg/m² de la recette × m² × (1 + taux de perte) ; le taux de perte et le prévu par fil sont **ceux figés à la validation** de l'ordre (sinon la recette en vigueur ce jour-là). Les ordres annulés sont lus mais leurs mouvements s'annulent.
- `blocages` (`blocages_bon`, `production.py:290-318`), brouillon seulement : « aucune matière à sortir » ; refus de `date_permise` ; « un ordre daté du JJ/MM/AAAA est déjà validé : dater ce bon au moins de ce jour » ; « « X » est un magasin de quarantaine » ; « l'inventaire INV-… est en cours sur « X » » ; « qualité arrêtée : Q1, Q2 » ; et `lots_manquants` (`:321-354`) : « lot L de R : entré le JJ/MM/AAAA, après la date de l'ordre | épuisé[ au JJ/MM/AAAA] | N kg seulement[ au JJ/MM/AAAA] dans « X », M kg demandés » ou la règle de présence à la date de l'écriture du stock (« lot L de R : <message> »).

Disponibilité à une date (`presents_au`, `production.py:117-153`) : ce qu'un lot peut donner dans un magasin le soir du jour J = le plus bas des soldes de J à aujourd'hui (on remonte le journal depuis le solde actuel), jamais négatif ; un lot entré après J ne donne rien. Une date absente ou ≥ aujourd'hui → soldes actuels.

### 6.1 `POST /api/bons/proposition` — `proposition`, `production.py:177-237`
- **Rôles** : Connecté (lecture : n'écrit rien, mais c'est un POST → en-tête `X-Gestion-MP` exigé).
- **Corps `Demande`** : `fabrications: [{qualite_id: int, m2: float (> 0, ≤ 1e8)}]` (au moins 1 ; une même qualité peut revenir, ses m² s'additionnent) ; `magasin_id: int` ; `date: date|null` (date de l'ordre ; null = aujourd'hui).
- **Réponse** : `{theorique (Σ kg à sortir, perte comprise), manque (Σ kg non couverts), taux_perte, recettes_incompletes: [str], lignes: [{article_id, reference, designation, role, theorique (kg perte comprise), par_qualite: {code: kg}, kg_par_ml, poids_bobine (catalogue), bobines_palette, lots: [{lot_id, lot, magasin_id, magasin, quantite (disponible à la date), entre_le, poids_bobine (lot, sinon catalogue), proposee (kg pris, arrondi 3 déc.)}], manque, disponibles: [mêmes champs sans proposee : tous les lots présents]}]}` triées par rôle puis référence. Un fil commun à plusieurs qualités n'apparaît qu'une fois.
- **Règles** : besoin = `kg_m2 × m² × (1 + taux_perte)` pour chaque ligne de nomenclature à `kg_m2 > 0` ; lots pris du plus ancien au plus récent (date d'entrée, id), **hors quarantaine**, dans le magasin demandé, tels qu'ils étaient à la date.
- `recettes_incompletes` : « Q : le rôle R pèse P au m², mais la recette ne nomme aucune matière pour lui : rien ne lui est proposé. La direction doit compléter la recette. » ou « Q : le rôle R fait S % dans la recette au lieu de 100 % : sa proposition est faussée. La direction doit corriger la recette. ».
- **Refus** : 404 « Qualité inconnue. » ; 422 « La qualité Q est arrêtée : elle ne se tisse plus. La direction la remet en service (Qualités) si une série doit encore partir. ». Un `magasin_id` inconnu donne simplement aucun lot.

### 6.2 `GET /api/bons` — `bons`, `production.py:419-433`
- **Rôles** : Connecté. **Requête** : `du`, `au: date|null` (bornes incluses sur la date de l'ordre).
- **Réponse** : tous les ordres (tous statuts), date décroissante puis id décroissant, forme `bon_dict`.

### 6.3 Corps commun `BonEntree` (`production.py:240-253`)
- `date: date` ; `magasin_id: int` ; `metier_id: int|null` ; `commentaire: str = ""` (max 300) ; `fabrications: [Fabrication] = []` (peut être vide : ordre « hors recette ») ; `lignes: [LigneBon]` (au moins 1).
- `LigneBon` : `article_id: int` ; `lot_id: int` ; `quantite: float` (> 0, ≤ 1e9) ; `unite: str = ""` (kg, Bobine, Palette).
- **Remplissage** (`_remplir`, `:256-283`) — refus 422 : « Magasin inconnu. » ; « La matière en quarantaine ne part pas aux machines : la libérer d'abord (transfert « Libération de quarantaine », décidé par les achats). » ; « Métier inconnu. » ; `date_permise` ; « Une qualité ne figure qu'une fois sur un ordre : additionner ses m². » ; qualité inconnue (404) ou arrêtée (422, voir 6.1) ; « Lot inconnu, ou d'une autre matière. » ; refus d'unité et de conversion (§ 4.4, point 5). Fabrications et lignes sont remplacées en entier ; les quantités sont converties en kg (3 décimales). La disponibilité n'est **pas** refusée ici (elle apparaît dans `blocages`).

### 6.4 `POST /api/bons` — `creer_bon`, `production.py:436-446`
- **Rôles** : Alimentation. **Réponse 201** : `bon_dict`.
- **Effets** : ordre `brouillon` ; journal `bon de sortie (brouillon)` / `bon` / id / « N fil(s), M kg » (M au format `1,234.5` anglais).

### 6.5 `PUT /api/bons/{bid}` — `modifier_bon`, `production.py:456-465`
- **Rôles** : Alimentation. Ordre verrouillé.
- **Refus** : 404 « Bon introuvable. » ; 409 « Un bon validé ne se modifie plus : l'annuler, puis en faire un autre. » ; remplissage.
- **Effets** : journal `modification bon de sortie` / `bon` / id / "".

### 6.6 `DELETE /api/bons/{bid}` — `supprimer_bon`, `production.py:468-477`
- **Rôles** : Alimentation. **Réponse** : `{ok: true}`.
- **Refus** : 404 ; 409 « Un bon validé ne se supprime pas : l'annuler. ».
- **Effets** : suppression ; journal `suppression bon de sortie` / `bon` / id / "".

### 6.7 `POST /api/bons/{bid}/valider` — `valider_bon`, `production.py:496-530`
- **Rôles** : Alimentation.
- **Refus** : 404 ; 409 « Ce bon est déjà validé. » ; `date_permise` ; 409 « Qualité arrêtée (Q1, Q2) : elle ne se tisse plus. La retirer de l'ordre, ou demander à la direction de la remettre en service. » ; 409 « À la date de l'ordre, <manquants joints par « ; »>. Choisir un autre lot, ou dater l'ordre du jour où la matière était là. » ; 409 « Un ordre daté du JJ/MM/AAAA existe déjà : les numéros suivent les dates, un bon ne se valide pas à une date antérieure. » (dernier ordre **non brouillon**, annulés compris, lu sous le verrou consultatif de transaction `7426110`) ; refus de l'écriture du stock.
- **Effets** : numéro `OF-AAAA-NNNN` ; `theorique` figé = JSON `{"perte": taux_perte, "fils": {référence: kg hors perte}}` (`theorique_fige`, `:480-493`) ; un mouvement `SORTIE` par ligne (quantité négative, date de l'ordre, `document="sortie"`, `ordre_id` = l'ordre) ; statut `valide`, `valide_par`, `valide_le` ; journal `validation bon de sortie` / `bon` / id / « OF-… · N fil(s) · M kg ».

### 6.8 `POST /api/bons/{bid}/annuler` — `annuler_bon`, `production.py:557-580`
- **Rôles** : Alimentation.
- **Refus** : 404 ; 409 « Seul un bon validé s'annule ; un brouillon se supprime. » ; refus de contre-passation (période close, matière revenue déjà repartie…).
- **Effets** (tout ou rien) : contre-passation des sorties de l'ordre ; pour chaque opération « retour des machines » **validée** rattachée : contre-passation, statut `annulee`, journal `annulation opération` / `operation` / id / « RET-… (avec OF-…) » ; contre-passation, ligne par ligne, des retours de la reprise de l'ERP Fil sans document (commentaire « Annulation du mouvement n°ID (avec OF-…) ») ; statut `annule` ; journal `annulation bon de sortie` / `bon` / id / « OF-…[ et N retour(s)] ».

### 6.9 `GET /api/bons/{bid}` — `bon`, `production.py:583-588`
- **Rôles** : Connecté. **Refus** : 404 « Bon introuvable. ». Le calcul de consommation n'est fait que pour un ordre numéroté.

### 6.10 `GET /api/bons/{bid}/lots-sortis` — `lots_sortis`, `production.py:591-607`
- **Rôles** : Connecté. **Réponse** : lots dont le net emporté par l'ordre (−Σ des mouvements portant l'ordre : sorties, retours, annulations) dépasse 0,001 kg : `[{lot_id, lot, article_id, reference, sorti_net, kg_par_ml, bobines_palette, poids_bobine}]` — ce qui peut encore revenir. Ordre inconnu → liste vide.

### 6.11 `GET /api/export/sorties` — `exporter_sorties`, `production.py:610-644` (Excel, § 11.4)
- **Rôles** : Connecté. **Requête** : `statut: str = "valide"` (`valide`, `brouillon`, `annule`) ; `du`, `au: date|null`.
- **Refus** : 422 « Statut : valide, brouillon ou annule. ».

---

## 7. Production et besoins (`api/production_plan.py`)

Le plan d'une qualité = une base mensuelle (m²) et douze coefficients de saisonnalité (mois 1 à 12, 1,0 par défaut) ; le plan glissant n'est pas stocké (base × coefficient du mois × croissance annuelle). Date de référence : `date_reference` (simulation) ou aujourd'hui ; année hors 2000–2100 → **400** « date de référence hors période : AAAA-MM-JJ » (`_date`, `:77-81`).

### 7.1 `GET /api/production/plan` — `plan_de_production`, `production_plan.py:87-143`
- **Rôles** : Connecté. **Requête** : `date_reference: date|null`.
- **Réponse** : `{date_reference, mois: [fins de mois ISO des 12 mois du plan, M0 = mois en cours], croissance_annuelle, taux_perte, qualites: [{id, code, nom, actif, base_mensuelle, saisonnalite: [12 coefficients], total_annuel (Σ base × coef), glissant: [12 m²], total_glissant, kg_m2 (Σ des kg/m² de sa recette, perte comprise), lignes_recette (nombre), recette_conforme (bool ; vrai si absente du contrôle), tisse_mois_en_cours (m² des ordres validés du mois)}] (par code), tisse_hors_plan: [{qualite, m2}] (qualités tissées ce mois sans être au plan, m² > 0)}`.

### 7.2 `PUT /api/production/plan` — `ecrire_plan_global`, `production_plan.py:146-183`
- **Rôles** : Direction.
- **Corps `PlanGlobal`** : `lignes: [LignePlan]` (1 à 1 000) ; `LignePlan` : `qualite_id: int` ; `base_mensuelle: float` (0 à 1e9) ; `saisonnalite: [float]` (**exactement 12**).
- **Refus** (rien n'est écrit) : 422 « Une qualité apparaît deux fois dans le plan envoyé. » ; 404 « Qualité introuvable : le plan n'a pas été enregistré. » ; 422 « Q : un coefficient de saisonnalité reste entre 0 et 20. Rien n'a été enregistré. ».
- **Réponse** : `{ok: true, modifiees: int}` (qualités dont le plan a réellement changé).
- **Effets** : base et coefficients écrits (création des mois manquants) ; pour chaque qualité changée, journal `plan de production` / `qualite` / id / « CODE : B m²/mois\nplan={"avant": {"b": base, "c": [12], "a": actif}, "apres": {…}} » — cette trace versionnée est relue par le moteur pour juger un mois passé sur le plan **en vigueur à l'époque** (`noter_plan`, `:49-60` ; marque `plan=` = `depot.MARQUE_PLAN`). Les qualités arrêtées peuvent recevoir un plan.

### 7.3 `GET /api/production/realise` — `plan_et_realise_fige`, `production_plan.py:186-198`
- **Rôles** : Connecté. **Requête** : `date_reference`.
- **Réponse** (`moteur.realise_par_qualite`) : `{mois: [12 fins de mois écoulés, le dernier = mois en cours], mois_clos: int (mois antérieurs à la date), lignes: [{qualite, plan: [12 m²], realise: [12 m²], total_plan, total_realise, ecart ((réalisé − plan)/plan sur les mois clos, null si plan nul)}], debut_service (ISO ou null), plan_fige: true}`. Chaque mois clos est jugé sur le plan en vigueur pendant ce mois.

### 7.4 `GET /api/production/besoins` — `besoins_detailles`, `production_plan.py:204-286`
- **Rôles** : Connecté. **Requête** : `date_reference` (à une date passée : stock, commandes, sorties de ce jour-là — `depot.charger_au`).
- **Réponse** : `{date_reference, mois: [12], taux_perte, fenetre_realisation_jours, roles: [codes des rôles par ordre], lignes: [{reference, nature, designation, fournisseur, role, kg_par_ml, kg: [12 besoins bruts, perte comprise], total, retenu: [12 besoins du plan d'achat, corrigés par le coefficient de réalisation], total_retenu, coefficient_realisation, conso_reelle, stock_disponible, bc_en_cours, stock_projete, couverture_jours, statut, quantite_a_commander (kg), unite_achat, quantite_a_commander_achat, qualites: [{qualite, kg_m2 (perte comprise), kg: [12], total}] (triées par total décroissant)}]}` (lignes triées par référence). Pas de prix.

---

## 8. Pilotage (`api/pilotage.py`)

Routeur avec `dependencies=[Depends(acteur)]`. Tout est recalculé à la demande depuis le journal (`depot.charger` / `depot.charger_au` puis `calcul.moteur`) ; rien n'est stocké. `date_reference` : même règle que § 7 (400 « date de référence hors période : … »). Les définitions de calcul (statuts, couverture, ABC/XYZ, CMUP, OTIF, score…) sont décrites dans la partie « Calculs » de l'héritage ; ici, la forme exacte des réponses.

### 8.1 `GET /api/stock` — `etat_stock`, `pilotage.py:44-75`
- **Rôles** : Connecté ; montants masqués pour l'alimentation (§ 0.5). **Requête** : `date_reference`.
- **Réponse** : `{date_reference, magasins: [codes des magasins actifs], lignes: [LigneStock]}`. `LigneStock` (`moteur.py:735-827`), une par matière : `reference, nature, designation, fournisseur, composition, type_fil, couleur, titrage, titrage_unite, unite_achat (unité du prix : kg|ml), quantite_a_commander_achat, prix_unite (prix catalogue dans son unité), kg_par_ml, stock_initial, entrees, stock_net (magasins, quarantaine comprise), stock_machine (fil monté sur les métiers), stock_quarantaine, stock_disponible, bc_en_cours, bc_hors_horizon, bc_dans_couverture, bc_en_preparation (bons brouillon/à approuver), bons_en_preparation: [n°], sorties_prevues, demande_delai, stock_projete, stock_min, stock_min_recalcule, stock_min_plafonne, statut, statut_couverture, couverture_jours, couverture_cible_jours, conso_mensuelle, besoin_annuel, conso_plan, conso_reelle, coefficient_realisation, conso_horizon, realisation_heritee: [réf.], delai_jours, sans_achat (pourquoi rien n'est proposé), quantite_a_commander, quantite_theorique, palettes_a_commander, unite_commande, contenance_commande, unites_a_commander, prix_kg, devise, montant_a_commander, montant_a_commander_mad, valeur_conso_annuelle, valeur_conso_annuelle_mad, classe_abc, rang, pourcentage_cumule, cv_demande, classe_xyz, groupe_equiv, sourcing, nb_fournisseurs_groupe, substituts: [réf.], date_derniere_sortie (ISO|null), jours_sans_mouvement, dormant, par_magasin: {code: kg}, besoins: [12], action` + `valeur_machine_mad` (stock en machine × CMUP, 0 si rien n'est monté).

### 8.2 `GET /api/besoins` — `besoins`, `pilotage.py:78-107`
- **Rôles** : Connecté. **Requête** : `date_reference`.
- **Réponse** : `{date_reference, mois: [12], plan: [{qualite, m2: [12], total}], besoins: [{reference, nature, designation, fournisseur, kg: [12], total}]}`. (Version simple de 7.4 ; non appelée par l'écran actuel.)

### 8.3 `GET /api/nomenclature` — `nomenclature`, `pilotage.py:110-121`
- **Rôles** : Connecté ; prix masqués pour l'alimentation.
- **Réponse** : `{lignes: [{qualite, reference, pourcentage, role_bom, nature, designation, fournisseur, kg_m2, prix_kg, devise, cout_m2_mad, poids_categorie, ml_m2, prix, unite_prix}], controle: [{qualite, roles_utilises, roles_conformes, ecarts: [{role, somme}], conforme}]}` (une recette est conforme si chaque rôle pesé fait 100 %).

### 8.4 `GET /api/plan-achat` — `plan_achat`, `pilotage.py:124-135`
- **Rôles** : Achats. **Requête** : `date_reference`.
- **Réponse** : `{references_a_commander, references_en_alerte, budget_mad, quantite_totale (kg), references_classe_a, ruptures, critiques, urgents, attentions, ok, tiers: {tier: nombre}, fournisseurs: [{fournisseur, pays, devise_par_defaut, devises: [..], delai_jours, contact, nb_references, quantite, montants_par_devise: {devise: montant}, montant_mad, part_budget, urgence, ruptures, critiques, urgents}], lignes: [{reference, nature, designation, fournisseur, classe_abc, statut, quantite (kg), unite_achat, quantite_achat, unite_commande, unites_commande, contenance_commande, prix, devise, montant_devise, montant_mad, palettes, tier, risque, action, relance, en_preparation, bons_en_preparation: [n°]}], date_reference}`.

### 8.5 `GET /api/plan-achat/fournisseur/{nom}` — `preparation_commande`, `pilotage.py:138-204`
- **Rôles** : Achats. **Chemin** : `nom` (convertisseur `path` : peut contenir `/` ; égalité exacte avec le nom du fournisseur). **Requête** : `date_reference`.
- **Réponse** : `{fournisseur, pays, contact, email, delai_jours, devise_par_defaut, date_reference, lignes: [{reference, nature, designation, statut, classe_abc, kg_par_ml, unite_achat, stock_projete, conso_mensuelle, couverture_jours, quantite_suggeree (kg), palettes_suggerees, contenance_palette, unite_commande, contenance_commande, unites_suggerees, unites_possibles: [{unite, contenance}] (kg, Bobine, Palette, unité déclarée), poids_bobine, bob_palette, minimum_commande, prix_indicatif (prix_kg), devise, montant_indicatif_mad, en_preparation, bons_en_preparation}]}` — seulement les matières de ce fournisseur avec `quantite_a_commander > 0`, triées par montant décroissant.
- **Refus** : **404** « fournisseur inconnu : « nom » » (minuscule, levé après le calcul).

### 8.6 `GET /api/cockpit` — `cockpit`, `pilotage.py:242-253`
- **Rôles** : Achats. **Requête** : `date_reference`.
- **Réponse** (`moteur.cockpit` avec les coûts rendus usine et `meme_couleur=True`) : `{date_reference, stock: {valeur_mad, valeur_machine_mad, nb_references, nb_detenues, nb_sur_metiers, couverture_ponderee_jours, ruptures, critiques, urgents, attentions, ok, sans_consommation}, achats: {bc_actifs, montant_bc_en_cours_mad, montant_bc_estime_mad, fournisseurs_actifs, budget_a_commander_mad}, finance: {cout_matiere_annuel_mad, cout_matiere_mensuel_mad, rotation_stock, dio_jours, cout_rotation_annuel_mad, base_rotation ("consommation"|"plan"), dso_jours, dpo_jours, ccc_jours}, abc: {A, B, C}, dormant: {nb_references, valeur_mad, part_valeur, seuil_jours}, sourcing: {mono_source, multi_source}, economies: {total_mad, nb_opportunites, top: [5 opportunités]}, nb_alertes, alertes: [24 au plus : {reference, nature, designation, fournisseur, stock (projeté), conso_mensuelle, couverture_jours, delai_jours, quantite_a_commander, statut, statut_couverture, action, titrage, kg_par_ml, stock_machine}], devises: [{devise, references, montant_mad, part}], controles: {total, conformes, garantis, anomalies, bloquants, score}}`.
- **Coût rendu usine** (`couts_rendus`, `:207-239`) : pour chaque ligne de réception validée, non refusée, pesée > 0 et prix > 0 : coût hors TVA du dossier d'importation (base « coût rendu ») ; sinon prix × cours figé de la commande si même devise (« prix facture ») ; sinon prix × cours du jour (« prix facture »).

### 8.7 `GET /api/valorisation` — `valorisation`, `pilotage.py:256-277`
- **Rôles** : Achats. **Requête** : `date_reference` (n'importe quelle date, pas forcément une fin de mois).
- **Réponse** : `{date_reference, total_mad, total_magasin_mad, total_machine_mad, total_kg, total_kg_magasin, total_kg_machine, ecart_mad, lignes: [{reference, nature, fournisseur, devise, prix_catalogue (par kg, devise de la matière), cmup_mad, stock_magasin, stock_machine, stock (magasin + machine), valeur_magasin_mad, valeur_machine_mad, valeur_mad (= CMUP × stock, machine comprise), ecart_mad (valeur − stock × prix catalogue × cours), kg_par_ml}]}` — une ligne par matière du catalogue.

### 8.8 `GET /api/opportunites` — `opportunites`, `pilotage.py:280-346`
- **Rôles** : Achats.
- **Requête** : `date_reference` ; `meme_couleur: bool = true` ; `autre_fournisseur: bool = true` ; `prix_catalogue: bool = false` ; `fenetre_jours: int|null` (1–3650 ; null = réglage `fenetre_prix_jours`).
- **Réponse** : `{avertissement (texte construit selon les critères, voir code `:313-323`), criteres: {meme_couleur, autre_fournisseur, prix_catalogue}, fenetre_jours, seuils: {stable: 0.005, forte: seuil_hausse_forte}, ecartees: {sans_date, hors_fenetre}, total_mad, lignes: [{reference, nature, titrage, fournisseur_actuel, prix_actuel_mad, prix_minimum_mad, fournisseur_alternatif, conso_annuelle, economie_mad, composition, type_fil, couleur, reference_alternative, couleur_alternative, origine_prix, origine_prix_minimum, ecart, date_prix (ISO|null), date_prix_minimum, ecart_jours, base_prix, base_prix_minimum}]}`. En « mode classeur » (paramètre moteur), comparaison historique sur nature et titrage seuls, critères ignorés, `ecartees` à zéro et avertissement fixe.

### 8.9 `GET /api/controles` — `controles`, `pilotage.py:349-377`
- **Rôles** : Achats. **Requête** : `date_reference`.
- **Réponse** : `{date_reference, synthese: {total (vérifiés, garantis exclus), conformes, garantis, anomalies, bloquants, score}, controles: [{code, libelle, anomalies, conforme, garanti (raison pour laquelle la base empêche ce contrôle de sonner, "" sinon), gravite ("bloquant"|"avertissement"|"information"), quoi_faire, vers (écran de correction), detail: [lignes fautives, clés libres]}], colonnes: {clé: libellé de colonne}}`.

### 8.10 `GET /api/prix/historique` — `historique_des_prix`, `pilotage.py:380-401`
- **Rôles** : Achats.
- **Réponse** : `{lignes: [{date_bc (ISO|null), numero_bc, reference, nature, designation, fournisseur, quantite, prix_achat (devise, par kg), devise, prix_mad, montant_mad, prix_precedent, evolution, origine}], total_achats_mad, hausses (évolution > 0,5 %), fortes_hausses (> seuil_hausse_forte), seuils: {stable, forte}, baisses (< −0,5 %)}`.

### 8.11 `GET /api/receptions/pesees` — `archive_des_pesees`, `pilotage.py:404-423`
- **Rôles** : Achats.
- **Réponse** : `{tolerance (toler_ecart_pesee), tolerance_bobine, lignes: [{numero, date_reception, numero_bc, fournisseur, receptionnaire, controleur_qualite, reference, nature, designation, lot_fournisseur, quantite_commandee, quantite_bl, quantite_pesee, ecart, ecart_relatif, hors_tolerance, nb_bobines, poids_moyen_bobine, magasin, statut_qualite, observations, statut_reception, quantite_attendue, nb_palettes, poids_bobine_catalogue, ecart_bobine, bobine_hors_tolerance}], hors_tolerance (nombre), non_conformes (statut qualité ≠ « Conforme »)}`.

### 8.12 `GET /api/receptions/bobines` — `evolution_du_poids_des_bobines`, `pilotage.py:426-441`
- **Rôles** : Achats.
- **Réponse** : `{tolerance (toler_poids_bobine), lignes: [{reference, fournisseur, poids_catalogue, receptions, premier, dernier, derniere_date, moyenne (Σ pesé / Σ bobines), mini, maxi, evolution ((dernier − premier)/premier), ecart_catalogue, hors_tolerance, historique: [{date, reception, fournisseur, lot, quantite_pesee, nb_bobines, poids_bobine}]}] (triées par |évolution| décroissante), hors_tolerance (nombre)}`.

### 8.13 `GET /api/prix/matrice` — `matrice_prix`, `pilotage.py:444-494`
- **Rôles** : Achats.
- **Réponse** : `{mois: ["AAAA-MM"] (36 derniers mois ayant un achat, ordre croissant), lignes: [{reference, nature, designation, titrage, titrage_unite, composition (ou nature), type_fil, couleur (ou désignation), fournisseur, devise, prix: [moyenne pondérée par les quantités du mois, ou moyenne simple si quantités nulles, null sans achat]}], seuils}`. Les achats sans date sont ignorés.

### 8.14 `GET /api/fournisseurs/performance` — `performance_fournisseurs`, `pilotage.py:497-521`
- **Rôles** : Achats.
- **Réponse** : `{cible_otif, seuils: {strategique, standard, surveiller}, lignes: [{fournisseur, pays, devise, delai_jours, nb_commandes, montant_mad, receptions, on_time, in_full, in_spec, otif, taux_retours, ecart_pesee_moyen, score, classement, action, sous_performant}], receptions: [{numero, fournisseur, date_reception, on_time, in_full (null : rien n'était dû), in_spec, otif, lignes_hors_tolerance, ecart_pesee}]}`.

### 8.15 `GET /api/lots` — `lots`, `pilotage.py:527-565`
- **Rôles** : Connecté.
- **Requête** : `reference: str = ""` ; `seulement_en_stock: bool = false` ; `lot_id: int|null` (un seul lot : sa référence, puis filtre sur son numéro).
- **Réponse** : `{lignes: [{reference, lot, entrees, sorties, stock, premiere_entree, dernier_mouvement, fournisseur, par_magasin, ordres: [n° OF], mouvements (nombre), epuise, negatif}], sans_lot (stock des mouvements sans lot, rangés sous « (sans lot) »), total}`.
- **Refus** : 404 « Lot introuvable. ». (Non appelée par l'écran actuel.)

### 8.16 `GET /api/lots/disponibles` — `lots_disponibles`, `pilotage.py:568-587`
- **Rôles** : Connecté. **Requête** : `reference: str` (requise).
- **Réponse** : `[{lot, stock, fournisseur, premiere_entree, par_magasin}]`. (Non appelée par l'écran actuel.)

### 8.17 `GET /api/tracabilite` — `tracabilite`, `pilotage.py:620-687`
- **Rôles** : Connecté.
- **Requête** : `lot: str = ""` (numéro, toutes matières confondues) ; `ordre: str = ""` (n° OF) ; `reference: str = ""` (un fil, tous ses lots) ; `lot_id: int|null` (exactement ce lot-là ; prioritaire).
- **Refus** : **400** « préciser un lot, un ordre de fabrication ou un fil » ; 404 « Lot introuvable. ».
- **Réponse** : `{lot, ordre, reference, [lot_id], references: [..], lots: [..], ordres: [n° OF des mouvements comptés], entrees (kg, hors annulations, annulées, transferts et retours des machines), sorties (kg nets : retours des machines déduits), mouvements: [{id, date, type (code ERP Fil : STOCK_INITIAL, ENTREE_RECEPTION, SORTIE_PROD, RETOUR_PRODUCTION, RETOUR_FOURNISSEUR, AJUSTEMENT_INVENTAIRE, TRANSFERT_MAGASIN), libelle (« 📦 Entrée Réception »… ; préfixé « Annulation — » pour une contre-passation), reference, quantite (signée ; quantité brute pour un transfert), lot_fournisseur, numero_of, magasin_source, magasin_destination, utilisateur, reference_doc (n° du document : la réception REC-…), lot_id, annulation: bool, annule: bool}]}`.

### 8.18 `GET /api/ordres-fabrication` — `ordres_fabrication`, `pilotage.py:690-720`
- **Rôles** : Connecté.
- **Réponse** : `{lignes: [{numero_of, consomme, retours, net, references: [{reference, quantite, theorique, ecart, hors_recette, kg_par_ml}], lots: [..], debut, fin (ISO : jours de sortie), fabrications: [{qualite, m2}], qualite ("Q1 · Q2"), m2, commentaire, theorique (perte comprise), taux_perte_fige, ecart, ecart_relatif, taux_perte}], total_consomme, total_theorique (ordres avec recette), total_consomme_avec_recette}` — ordres annulés exclus, triés par fin décroissante.

---

## 9. Suivi (`api/suivi.py`)

### 9.1 Réclamations aux fournisseurs

Motifs (`MOTIFS_RECLAMATION`, `suivi.py:44-46`) : « Qualité (défaut du fil) », « Quantité manquante », « Poids des bobines », « Bobines endommagées », « Retard de livraison », « Documents (facture, BL, certificat) », « Autre ». Issues (`ISSUES`, `:47`) : « Avoir », « Remplacement », « Remise sur la prochaine commande », « Refusée », « Abandonnée ». Statuts : `ouverte`, `close`. Le motif n'est pas contrôlé contre la liste (texte ≤ 80).

**Forme `reclamation_dict`** (`suivi.py:50-63`) : `{id, numero (RCL-AAAA-NNNN), fournisseur_id, fournisseur, reception_id, reception (n°), lot_id, lot, reference (matière du lot), motif, description, quantite (kg), montant_demande, devise, reponse, issue, montant_obtenu, statut, ouverte_le, close_le (ISO date), cree_par, jours (de l'ouverture à la clôture, ou à aujourd'hui)}`. (Montants visibles : route réservée aux achats.)

#### `GET /api/reclamations` — `reclamations`, `suivi.py:66-70`
- **Rôles** : Achats. **Réponse** : `{motifs: [..], issues: [..], reclamations: [reclamation_dict]}` (id décroissant).

#### `POST /api/reclamations` — `ouvrir_reclamation`, `suivi.py:73-136`
- **Rôles** : Achats.
- **Corps `ReclamationEntree`** : `fournisseur_id: int` ; `reception_id: int|null` ; `lot_id: int|null` ; `motif: str` (max 80, requis) ; `description: str = ""` (max 4 000) ; `quantite: float = 0` (0–1e9) ; `montant_demande: float = 0` (0–1e10) ; `devise: str = "MAD"` (max 3, mise en majuscules ; vide = MAD) ; `ouverte_le: date|null` (null = aujourd'hui).
- **Refus (422)** : « Fournisseur inconnu. » ; « Réception inconnue. » ; « La réception REC-… est de F1, pas de F2. » ; « On réclame sur ce que le fournisseur a livré : cette réception n'est pas encore validée. | est annulée. » ; « Lot inconnu. » ; « Le lot L n'a pas été livré par F. » (fournisseurs des réceptions du lot + fournisseur du lot, si connus) ; « Le lot L n'est pas dans la réception REC-…. » ; « Q réclamés pour P livrés par la réception REC-…. » (quantité > Σ pesée des lignes de la réception, ou du lot dans la réception ; contrôlé seulement si une réception est donnée ; nombres à 1 décimale, séparateur de milliers = espace) ; « Devise inconnue : XXX. » ; « Une réclamation ne s'ouvre pas dans le futur. » ; « Une réclamation ne précède pas la réception qu'elle vise (JJ/MM/AAAA). ».
- **Réponse 201** : `reclamation_dict`.
- **Effets** : numéro `RCL-AAAA-NNNN` (année de `ouverte_le`) ; statut `ouverte` ; journal `réclamation ouverte` / `reclamation` / id / « RCL-… · motif ».

#### `PUT /api/reclamations/{rid}` — `repondre_reclamation`, `suivi.py:139-169`
- **Rôles** : Achats.
- **Corps `ReponseReclamation`** : `reponse: str = ""` (max 4 000) ; `issue: str = ""` (max 40) ; `montant_obtenu: float = 0` (0–1e10) ; `clore: bool = false` ; `rouvrir: bool = false`.
- **Refus (422 sauf mention)** : 404 « Réclamation introuvable. » ; « Issue : Avoir, Remplacement, Remise sur la prochaine commande, Refusée, Abandonnée. » ; « Cette réclamation est close : elle garde son issue. La rouvrir pour la reprendre. » (close, sans `rouvrir` et sans issue) ; « Pour clore, dire comment elle s'est terminée (avoir, remplacement, refusée…). ».
- **Effets** : `reponse`, `issue`, `montant_obtenu` **toujours** remplacés ; `clore` sur une ouverte → `close`, `close_le` = aujourd'hui ; `rouvrir` sur une close → `ouverte`, `close_le` = null ; journal `réclamation` / `reclamation` / id / « RCL-… · statut · issue ». **Réponse** : `reclamation_dict`.

### 9.2 Besoins signalés par l'atelier

**Forme `signalement_dict`** (`suivi.py:181-187`) : `{id, quand (ISO minute), par, article_id, reference, texte, urgence ("normale"|"urgente"), traite: bool, traite_par, traite_le, reponse}`.

#### `GET /api/signalements` — `signalements`, `suivi.py:190-195`
- **Rôles** : Connecté. **Requête** : `tous: bool = false` (faux : non traités seulement). **Réponse** : 300 au plus, id décroissant.

#### `POST /api/signalements` — `signaler`, `suivi.py:198-207`
- **Rôles** : Connecté (l'atelier d'abord).
- **Corps `SignalementEntree`** : `article_id: int|null` (non vérifié) ; `texte: str` (2–500) ; `urgence: str = "normale"` (motif `^(normale|urgente)$`).
- **Réponse 201** : `signalement_dict`. **Effets** : `par` = nom ; journal `besoin signalé` / `signalement` / id / texte (120 car.).

#### `POST /api/signalements/{sid}/traiter` — `traiter`, `suivi.py:210-223`
- **Rôles** : Achats. **Corps `Traitement`** : `reponse: str = ""` (max 500).
- **Refus** : 404 « Signalement introuvable. ». Un signalement déjà traité peut être retraité (écrase).
- **Effets** : `traite_par`, `traite_le` = maintenant, `reponse` ; journal `besoin traité` / `signalement` / id / réponse (120 car.).

### 9.3 Pièces jointes

Objets admis (`OBJETS`, `suivi.py:228-230`) : `dossier`, `reception`, `commande`, `reclamation`, `inventaire`, `fournisseur`, `article`. Types MIME admis (`TYPES_PERMIS`) : `application/pdf` ; `image/jpeg|png|gif|webp|heic|heif|tiff|bmp` (pas de SVG : il peut porter du script) ; `text/plain` ; `text/csv` ; `application/vnd.*` (bureautique) ; `application/msword` ; `application/zip`. Taille maximale : 20 Mo. Stockage : `config.PIECES/<objet>/<id>/<uuid hex><extension>` (extension : 9 premiers caractères du suffixe, alphanumériques et points). **Forme `piece_dict`** : `{id, objet, objet_id, nom (nom d'origine, 200 car.), type, taille, par, quand}`.

#### `GET /api/pieces/{objet}/{oid}` — `pieces`, `suivi.py:242-245`
- **Rôles** : Achats. **Réponse** : les pièces de ce document, par id croissant (objet non contrôlé : liste vide pour un objet inconnu).

#### `POST /api/pieces/{objet}/{oid}` — `joindre`, `suivi.py:248-270`
- **Rôles** : Achats. **Corps** : `multipart/form-data`, champ `fichier` (requis). Type = celui annoncé, sinon deviné par le nom.
- **Refus** : 404 « Document inconnu. » (objet hors liste ou id inexistant) ; 422 « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. » ; 422 « Fichier trop lourd (20 Mo au plus). ».
- **Réponse 201** : `piece_dict`. **Effets** : fichier écrit sur disque ; ligne `PieceJointe` ; journal `pièce jointe` / `<objet>` / oid / nom du fichier. Le miroir des pièces jointes suit à la prochaine sauvegarde.

#### `GET /api/piece/{pid}/fichier` — `fichier`, `suivi.py:273-278`
- **Rôles** : Achats. **Réponse** : le fichier, type d'origine, `Content-Disposition: attachment; filename=<nom d'origine>`. **Refus** : 404 « Pièce introuvable. ».

#### `DELETE /api/piece/{pid}` — `retirer_piece`, `suivi.py:281-290`
- **Rôles** : Achats. **Réponse** : `{ok: true}`. **Refus** : 404 « Pièce introuvable. ».
- **Effets** : supprime la ligne ; **le fichier reste sur le disque** (et dans le miroir) ; journal `pièce retirée` / `<objet>` / oid / nom.

### 9.4 Échéancier des paiements

#### `GET /api/echeancier` — `echeancier`, `suivi.py:296-392`
- **Rôles** : Achats. **Requête** : `du`, `au: date|null` (bornes incluses ; ne filtrent que `lignes`).
- **Règles** : pour chaque facture fournisseur : montant = montant saisi, sinon Σ (pesée × prix) des lignes non refusées de ses réceptions **validées** (`estime` = vrai) ; facture dont toutes les réceptions sont annulées → `ecartees` (« réglée, réception annulée : avoir à demander » si payée, sinon « réception annulée : plus due » si montant > 0) ; facture ne portant que des brouillons de réception → ignorée (pas encore due) ; payée → `reglees` ; avec échéance → `lignes` ; sans échéance et montant > 0 → `a_dater`. Pour chaque frais d'importation (`DossierCharge`, toujours en MAD) : payé → `reglees` ; avec échéance → `lignes` ; sinon montant > 0 → `a_dater` (même dossier clos). Conversion en MAD au **cours actuel** de la devise (1 pour MAD ou devise inconnue).
- **Réponse** : `{lignes: [{id, objet ("facture"|"frais"), genre ("Facture fournisseur" | "Frais d'importation (<poste>)"), tiers (fournisseur, ou prestataire, « — » à défaut), piece (n° facture, ou « DOS · pièce »), montant, estime, devise, montant_mad, date (échéance ISO), en_retard (échéance < aujourd'hui)}] (par échéance), par_mois: {"AAAA-MM": MAD}, echu_mad (Σ des lignes en retard), a_dater: [mêmes champs sans date], a_dater_mad, reglees: [… + date (échéance ou null), payee_le] (300 plus récentes), ecartees: [… + raison (+ payee_le)], total_mad (Σ lignes)}`.

#### `PUT /api/echeancier/paiement` — `regler`, `suivi.py:395-435`
- **Rôles** : Achats.
- **Corps `Paiement`** : `objet: str` (motif `^(facture|frais)$`) ; `id: int` ; `payee_le: date|null` (null = règlement annulé).
- **Refus** : 404 « Pièce introuvable. » ; 422 « Un règlement ne se date pas dans le futur : c'est un fait constaté. » ; 422 « Le règlement (JJ/MM/AAAA) précède la pièce qu'il règle (JJ/MM/AAAA). » (facture : sa date, sinon la première réception qui la porte ; frais : `date_piece`).
- **Réponse** : `{objet, id, payee_le (ISO|null)}`.
- **Effets** : `payee_le` ; journal `règlement` ou `règlement annulé` / `facture`|`frais` / id / « facture N · Fournisseur[ · réglé le JJ/MM/AAAA] » ou « frais <poste> · dossier DOS[ · …] ».

### 9.5 `GET /api/qualites/{qid}/versions` — `versions_recette`, `suivi.py:479-484`
- **Rôles** : Connecté. **Réponse** : versions de la recette de la qualité, de la plus récente : `[{id, quand (ISO minute), par, lignes: [{reference, role, pourcentage}], poids: {role: kg/m² ou ml/m²} | null}]`. Qualité inconnue → liste vide. (Écrites automatiquement, § 0.8.)

### 9.6 Indicateurs

#### `GET /api/indicateurs/historique` — `historique_indicateurs`, `suivi.py:516-519`
- **Rôles** : Achats. **Réponse** : une photo par jour, ordre chronologique : `[{jour, valeur_stock_mad, couverture_jours, ruptures, critiques, urgents, a_commander_mad, commandes_en_cours_mad, otif_moyen}]`.

#### `POST /api/indicateurs/photographier` — `photographier`, `suivi.py:861-863`
- **Rôles** : Direction. Pas de corps.
- **Réponse** : `{valeur_stock_mad (cockpit.stock.valeur_mad), couverture_jours (couverture pondérée), ruptures, critiques, urgents, a_commander_mad (budget à commander), commandes_en_cours_mad, otif_moyen (part des réceptions notées parfaites, toutes dates ; null sans note)}`.
- **Effets** : crée ou **remplace** la photo `IndicateurJour` d'aujourd'hui (une par jour, la dernière l'emporte) ; commit ; pas de journal. Même calcul que la photo automatique de la boucle de fond.

### 9.7 `GET /api/bilan` — `bilan_imprimable`, `suivi.py:528-674` (document, § 12.1)
- **Rôles** : Achats. **Requête** : `mois: str` (requis, motif `^\d{4}-\d{2}$`, ex. `2026-09`).
- **Calcul** (`bilan`, `:528-614`), mois = [1ᵉʳ du mois, 1ᵉʳ du mois suivant[ :
  - `stock_debut_kg` / `stock_fin_kg` : Σ de **tous** les mouvements datés avant le début / avant la fin (magasins, quarantaine comprise ; transferts neutres) ;
  - flux du mois par type, hors transferts : les contre-passations vont dans `annulations` (par type), les autres dans `flux` ; `entrees_kg` = flux `RECEPTION` (réceptions annulées comprises, leur annulation étant dans `annulations`) ; `valeur_entrees_mad` = Σ quantité × prix × cours (figé, sinon cours du jour ; 1 en MAD) des réceptions **non annulées** ; `sorties_kg` = −flux `SORTIE` ; `retours_machine_kg` ; `retours_fournisseur_kg` (positif) ; `ajustements_kg` ; `ouvertures_kg` ; `annulations_kg` (Σ) et `annulations` {type: kg} non nuls ;
  - `m2_par_qualite` / `m2_total` : m² des ordres **validés** datés du mois ;
  - `commandes` : bons numérotés dont la date de commande est dans le mois ; `receptions` : réceptions validées du mois ;
  - `otif` : moyenne des notes OTIF des réceptions du mois, `receptions_notees` ;
  - `ordres` : ordres validés dont le premier jour de sortie est dans le mois ; `ecarts_ordres` : les 8 plus grands |écart relatif| (forme `consommations`) ;
  - `valeur_debut_mad` / `valeur_fin_mad` : valorisation au CMUP (comme la page Valorisation) la veille du mois et le soir du dernier jour (ou aujourd'hui pour le mois en cours), journal rejoué à ces dates ; `consommation_mad` : coût net des sorties vers les machines du mois ;
  - `ruptures` / `critiques` : matières dont le statut contient « RUPTURE » / « CRITIQUE » à la fin du mois.
- **Réponse** : page HTML. **Refus** : 422 si le motif n'est pas respecté ; un mois `13` passe le motif et provoque une erreur 500.

### 9.8 `GET /api/courriel/apercu` — `apercu_courriel`, `suivi.py:850-858`
- **Rôles** : Direction.
- **Réponse** : `{sujet: "Gestion MP — la semaine du JJ/MM/AAAA", texte (corps en texte brut), serveur_configure: bool (variable d'environnement GESTION_MP_SMTP_HOTE définie), destinataires: str (réglage courriel_destinataires)}`.
- **Corps du courriel** (`services/courriel.py:31-70`), une ligne chacun : titre « Gestion MP — la semaine du JJ/MM/AAAA[ — <société>] » ; « Valeur du stock : N MAD · couverture pondérée J jours » ; « Matières en rupture : a · critiques : b · urgentes : c » ; « À commander selon le plan : N MAD » ; « Commandes en retard : n[ — n° (8 premiers)] » ; « Commandes à approuver : n » ; « Brouillons en attente : n réceptions, n ordres de fabrication, n opérations » ; « Besoins signalés par l'atelier, non traités : n » ; « Réclamations fournisseurs ouvertes : n » ; « Le détail : ouvrir Gestion MP (Cockpit). ».

### 9.9 Import des matières : voir § 10.

---

## 10. Import du tableur des matières (`suivi.py:677-835`)

### 10.1 `GET /api/import/matieres/modele` — `modele_matieres`, `suivi.py:701-731`
- **Rôles** : Achats.
- **Fichier** : `matieres.xlsx` (`Content-Disposition: attachment; filename="matieres.xlsx"`), une feuille **« Matières »** : ligne 1 = en-têtes, puis une ligne par matière (toutes, actives ou non), triées par référence. Aucun format, aucun gel, aucun filtre (contrairement aux exports).
- **Colonnes, dans l'ordre** (`COLONNES_ARTICLE`, `:679-689`) — en-tête exact → champ de la fiche :

| # | En-tête | Champ | Valeur écrite | Relue à l'import |
|---|---|---|---|---|
| 1 | Référence | `reference` | texte | clé (obligatoire) |
| 2 | Désignation | `designation` | texte | texte |
| 3 | Rôle | `role` | code du rôle | doit exister dans les rôles de nomenclature |
| 4 | Composition | `composition` | code | doit exister (classification) |
| 5 | Type de fil | `type_fil` | code | doit exister |
| 6 | Titrage | `titrage` | code | doit exister |
| 7 | Couleur | `couleur` | code | doit exister |
| 8 | Code couleur | `couleur_code` | texte | texte |
| 9 | Densité | `densite` | nombre (kg / mètre) | nombre |
| 10 | Fournisseur | `fournisseur` → `fournisseur_id` | **nom** du fournisseur | nom, insensible à la casse, doit exister |
| 11 | Prix | `prix` | nombre (dans l'unité du prix) | nombre |
| 12 | Unité du prix | `unite_prix` | `kg` ou `ml` | `kg` ou `ml` (mis en minuscules) |
| 13 | Devise | `devise` | code | doit exister |
| 14 | Unité d'achat | `unite_achat` | texte (kg, Palette, Fût…) | texte libre, sauf `ml` refusé |
| 15 | Contenance | `contenance_achat` | nombre (kg par unité d'achat) | nombre |
| 16 | Minimum de commande | `minimum_commande` | nombre | nombre |
| 17 | kg / bobine | `poids_bobine` | nombre | nombre (ancien intitulé « Poids d'une bobine » accepté) |
| 18 | Bobines par palette | `bobines_palette` | nombre | nombre |
| 19 | Stock minimum | `stock_min` | nombre (kg) | nombre |
| 20 | Couverture minimum (mois) | `couv_min_mois` | nombre | nombre |
| 21 | Groupe d'équivalence | `groupe_equiv` | texte | texte |
| 22 | Code douanier | `code_douanier` | code | doit exister |
| 23 | En service | `actif` | `oui` / `non` | vrai si `oui`, `1`, `vrai`, `true` ou `x` (casse ignorée), faux sinon |
| 24 | Se commande en (lecture seule) | — | conditionnement : `Palette de 705,6 kg`… | **jamais relue** |

- Colonne 24 (`COLONNE_SE_COMMANDE`, `:696`) : « comment chaque matière se commande », déclaré ou déduit comme le plan d'achat (`referentiels.conditionnement`) : unité d'achat déclarée (≠ kg avec contenance > 0) → « <unité> de <contenance> kg » ; sinon palette si poids de bobine et bobines/palette connus → « Palette de <poids × nb> kg (déduit) » ; sinon « Bobine de <poids> kg (déduit) » ; sinon « kg ». La contenance est écrite au format `:g` (point décimal).
- L'ancienne colonne « Unité » (unité de stock) n'est plus écrite ni lue : le stock est toujours en kg (décision du 8 octobre 2026).

### 10.2 `POST /api/import/matieres` — `importer_matieres`, `suivi.py:734-835`
- **Rôles** : Achats. **Requête** : `appliquer: bool = false` (faux = **simulation** : rien n'est écrit). **Corps** : `multipart/form-data`, champ `fichier` (classeur .xlsx ; la feuille **active** est lue, valeurs calculées des formules).
- **Lecture** : ligne 1 = en-têtes (espaces retirés ; « Poids d'une bobine » → « kg / bobine ») ; seules les colonnes reconnues sont lues (ordre libre ; colonnes inconnues ignorées ; en cas de doublon, la première) ; à partir de la ligne 2, une ligne sans référence est ignorée ; **une cellule vide ne change rien** (aucun champ ne peut être vidé par import) ; une matière absente du tableur n'est jamais supprimée.
- **Contrôles ligne par ligne** (`problemes`, messages exacts) :
  - nombre illisible : « <champ> n'est pas un nombre » (nom technique : `densite`, `prix`, `contenance_achat`, `minimum_commande`, `poids_bobine`, `bobines_palette`, `stock_min`, `couv_min_mois`) ;
  - « fournisseur inconnu « X » » ;
  - « <champ> inconnu « X » (l'ajouter d'abord à la classification) » pour `composition`, `type_fil`, `titrage`, `couleur`, `role`, `devise`, `code_douanier` ;
  - « unité du prix : kg ou ml » ;
  - sur la fiche **telle qu'elle serait après l'import** (valeurs actuelles complétées par la ligne) : « une matière en service a un fournisseur » (matière existante, active, sans fournisseur) ; « un prix au mètre a besoin de la densité (kg par mètre) » ; « une matière du rôle R a besoin de sa densité (kg par mètre) : la recette la compte en mètres, le stock en kilos » (rôles Cuir, Franges, Ruban) ; « la commande se compte en kilos : un prix au mètre se dit dans « Unité du prix » » (unité d'achat `ml`) ;
  - matière nouvelle : « une matière nouvelle a besoin de son rôle » ; « une matière nouvelle a besoin de son fournisseur ».
- **Réponse 200** : `{appliquer: bool, creees: [références], modifiees: [{reference, champs: [noms techniques triés], detail: [{champ, avant, apres}]}], inchangees: int, erreurs: [{ligne (n° de ligne Excel), reference, problemes: [str]}]}`. Le champ fournisseur apparaît sous le nom `fournisseur_id` (identifiants avant/après). Une ligne en erreur n'entre ni dans `creees` ni dans `modifiees`.
- **Mode appliquer** : s'il y a la moindre erreur → **422** « N ligne(s) en erreur : corriger le tableur d'abord, rien n'a été écrit. » (tout ou rien). Sinon : création des nouvelles matières (`modifie_par`, `modifie_le`) ; pour les modifiées, seuls les champs différents sont écrits, `version + 1`, `modifie_le`, `modifie_par` ; journal `import des matières` / `article` / null / « N créée(s), M modifiée(s) » ; commit (les versions de recette ne sont pas concernées).
- **Refus** : 422 « Tableur illisible : <exception> » ; 422 « La colonne « Référence » est obligatoire (télécharger le modèle). ».

---

## 11. Exports Excel

### 11.0 Conventions communes (`exports.py:34-119`)

- Type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` ; `Content-Disposition: attachment; filename="<nom>"` ; le nom est assaini (tout caractère hors `A-Za-z0-9._-` → `-`, tirets de bord retirés ; `export.xlsx` à défaut).
- Classeur créé sans feuille par défaut (`_nouveau`) ; chaque feuille par `_feuille(classeur, titre, colonnes, lignes, entete=…)` :
  - titre de feuille : `[ ] : * ? / \` remplacés par une espace, 31 caractères au plus ;
  - lignes de titre (`entete`) en gras (1ʳᵉ cellule), puis **une ligne vide**, puis la ligne d'en-têtes ; sans `entete`, les en-têtes sont en ligne 1 ;
  - en-têtes : gras, fond `#E8ECF3`, filet inférieur fin `#B8C0CC`, centrés verticalement, retour à la ligne ;
  - formats de nombre par colonne, appliqués aux seules cellules numériques : `KG = #,##0.0`, `ENTIER = #,##0`, `PRIX = #,##0.000`, `MONTANT = #,##0.00`, `POURCENT = 0.0%` ; les dates `date` Python sont écrites en dates Excel (format par défaut d'openpyxl `yyyy-mm-dd`, sauf mention) ;
  - largeur = min(50, max(0,9 × longueur de l'en-tête, longueur des valeurs des 300 premières lignes, 8) + 2) ;
  - volet figé sous l'en-tête, et sur la colonne A si plus de 4 colonnes (cellule B) ;
  - filtre automatique sur l'en-tête et les données (s'il y a des lignes) ;
  - sécurité : caractères de contrôle interdits retirés ; un texte commençant par `=` est forcé en texte (jamais une formule).
- Toutes les dates d'export et noms de fichier utilisent la date du serveur.

### 11.1 `GET /api/export/pilotage` — `exporter_pilotage`, `exports.py:125-236`
- **Rôles** : Achats. **Requête** : `date_reference: date|null` (400 « date de référence hors période : … » hors 2000–2100). Mêmes chiffres que l'écran à cette date (`charger_au`).
- **Fichier** : `pilotage-mp-AAAA-MM-JJ.xlsx` (date de référence). Titre de chaque feuille : « Pilotage des matières premières au JJ/MM/AAAA ».
- **Feuille « Stock »** (une ligne par matière) : Référence ; Désignation ; Rôle ; Fournisseur ; Composition ; Type de fil ; Couleur ; Titrage ; Statut ; Stock net [KG] ; Sur les métiers [KG] ; Quarantaine [KG] ; Disponible [KG] ; Commandé dans le délai [KG] (`bc_en_cours`) ; Commandé au-delà du délai [KG] (`bc_hors_horizon`) ; Sorties prévues [KG] ; Stock projeté [KG] ; Stock minimum [KG] (`stock_min_plafonne`) ; Seuil d'alerte [KG] (`stock_min_recalcule`) ; Conso / mois [KG] ; Couverture (j) [ENTIER] ; Seuil d'alerte (j) [ENTIER] (`couverture_cible_jours`) ; Délai (j) [ENTIER] ; À commander [KG] ; Palettes [MONTANT] ; Prix / kg [PRIX] ; Devise ; Montant devise [MONTANT] ; Montant MAD [MONTANT] ; Classe ABC ; Rang [ENTIER] ; % cumulé [POURCENT] ; Classe XYZ ; CV demande [MONTANT] ; Sourcing ; Groupe d'équivalence ; Dernière sortie (date) ; Dormant (« oui » ou vide) ; puis une colonne « Magasin <CODE> » [KG] par magasin **actif** (0 si rien).
- **Feuille « Plan d'achat »** (titre + « Budget : N MAD », milliers séparés par une espace) : Référence ; Fournisseur ; Classe ; Statut ; Quantité (kg) [KG] ; Soit (ml, indicatif) [ENTIER] (kg ÷ densité, vide sans densité) ; Unité de commande (« kg » à défaut) ; Unités [MONTANT] ; Prix / kg [PRIX] ; Prix catalogue [PRIX] (dans l'unité du prix) ; Unité du prix ; Devise ; Montant devise [MONTANT] ; Montant MAD [MONTANT] ; Palettes [MONTANT] ; Priorité (tier) ; Risque ; Action ; Relance.
- **Feuille « Par fournisseur »** : Fournisseur ; Pays ; Devises (jointes par « · ») ; Délai (j) [ENTIER] ; Références [ENTIER] ; Quantité (kg) [KG] ; Montants par devise (« 12 000 USD · 5 000 EUR ») ; Montant MAD [MONTANT] ; Part du budget [POURCENT] ; Urgence ; Ruptures [ENTIER] ; Contact.
- **Feuille « Besoins »** (titre + « Kilos à consommer selon le plan de production, mois par mois. ») : Référence ; Rôle ; Fournisseur ; 12 colonnes « MM/AAAA » [KG] ; Total [KG].
- **Feuille « Contrôles »** : Code ; Contrôle ; Anomalies [ENTIER] ; Gravité (code brut : bloquant, avertissement, information) ; État (« conforme » ou « à corriger »).
- Prix et montants présents (route interdite à l'alimentation).

### 11.2 `GET /api/export/mouvements` — `exporter_mouvements`, `exports.py:242-301`
- **Rôles** : Connecté. **Requête** : celle de `GET /api/mouvements` (`article_id`, `lot_id`, `magasin_id`, `type`, `document`, `du`, `au`, `q` ≤ 80), avec `limite: int = 100 000` (1–200 000) ; ni `decalage` ni `avec_valeur`.
- **Fichier** : `mouvements-AAAA-MM-JJ.xlsx` (aujourd'hui). Feuille **« Mouvements »**. Titre : « Journal des mouvements — exporté le JJ/MM/AAAA » ; « Filtres : matière R · lot L · magasin M · type « libellé » · document D · du JJ/MM/AAAA · au JJ/MM/AAAA · recherche « q » » ou « Filtres : aucun (tout le journal) » ; si tronqué : « Attention : seuls les N plus récents sont exportés. ».
- **Colonnes** : Date (date, format `DD/MM/YYYY`) ; Saisi le (texte « AAAA-MM-JJ HH:MM ») ; Type (libellé) ; Document (« Réception », « Bon de sortie », « Opération », « Inventaire », sinon valeur brute) ; N° de document ; Référence ; Lot ; Magasin ; Quantité [KG] (signée) ; **Prix / kg** [PRIX] (vide si 0) et **Devise** (vide sans prix) — **ces deux colonnes n'existent pas pour l'alimentation** ; Motif ; Commentaire ; Par ; Annule le mouvement (id du mouvement contre-passé, sinon vide). Ordre : le plus récent d'abord.

### 11.3 `GET /api/export/bon-de-commande/{cid}` — `exporter_bon_de_commande`, `exports.py:307-419`
- **Rôles** : Achats. **Chemin** : `cid: int`. **Refus** : 404 « Bon de commande introuvable. ». Non appelé par l'écran actuel (l'écran utilise le bon de la partie A).
- **Fichier** : `<n° du bon>.xlsx` ou `BC-brouillon-<id>.xlsx`. Une feuille **« Bon de commande »**, en **français**, mise en page paysage, une page en largeur, ligne d'en-têtes répétée à l'impression. Pas de `_feuille` : mise en forme propre.
- **Contenu, de haut en bas** : (si renseigné) raison sociale (gras, 14) ; « secteur · adresse · téléphone » ; « ICE x · RC y · IF z » ; une ligne vide ; « Bon de commande <n°> » ou « Bon de commande — brouillon, non envoyé » (gras, 13) ; paires libellé (gras) / valeur, seulement si la valeur existe : Date (JJ/MM/AAAA) ; Livraison souhaitée (date ou « à convenir ») ; Fournisseur ; Pays ; Contact ; Téléphone ; Email ; Conditions de paiement ; Incoterm ; Devise ; si un prix au moins n'est pas confirmé : « Prix » / « à confirmer par le fournisseur » ; ligne vide ; en-têtes : Référence ; Désignation ; Quantité (unités de commande, `#,##0.##`) ; Unité (« kg », « Palette de 705,6 kg »…) ; Soit (kg) [KG] ; *Soit (ml, indicatif)* (`#,##0`, seulement si une ligne a une densité) ; Prix / kg (prix confirmé au format `#,##0.000 "DEV"`, sinon « à confirmer ») ; Montant (`#,##0.00 "DEV"`, vide si non confirmé) ; ligne « Total » (kg totaux ; montant total seulement si **tous** les prix sont confirmés) ; « Observations » si présentes. Largeurs fixes 34, 40, 12, 24, 14, (14), 16, 18.

### 11.4 `GET /api/export/sorties` — `exporter_sorties`, `production.py:610-644`
- **Rôles** : Connecté (aucun prix). **Requête** : `statut` (`valide` par défaut, `brouillon`, `annule`), `du`, `au`.
- **Fichier** : `sorties-<statut>-AAAA-MM-JJ.xlsx`. Feuille **« Sorties »**. Titre : « Sorties vers les machines (validées|brouillons|annulées) — exporté le JJ/MM/AAAA » ; « Période : du JJ/MM/AAAA au JJ/MM/AAAA » (bornes présentes seulement) ou « Période : tout ».
- **Colonnes** : Ordre (n°, ou « Brouillon ») ; Date (date, format `DD/MM/YYYY`) ; Fabrication (« Q1 1 000 m² · Q2 … », ou « hors recette ») ; m² [ENTIER] (vide si 0) ; Métier ; Magasin ; Prévu par la recette (kg) [KG] (perte comprise, vide si 0) ; Sorti net (kg) [KG] (arrondi 3) ; Écart (kg) [KG] ; Écart [POURCENT] (relatif) ; Revenu (kg) [KG] (vide si 0) ; Retours (n° joints par « , ») ; Commentaire ; Par (validé par, sinon créé par). Ordre : date décroissante.

### 11.5 `GET /api/export/controles` — `exporter_controles`, `exports_analyse.py:44-92`
- **Rôles** : Achats. **Requête** : `date_reference`.
- **Fichier** : `controles-AAAA-MM-JJ.xlsx`. Contrôles triés : non conformes d'abord, puis gravité (bloquant, avertissement, information), puis code.
- **Feuille « Contrôles »** : titre « Contrôles au JJ/MM/AAAA » ; « C conformes sur T vérifiés (et G garantis par la base) · B bloquant(s) · score NN% » ; colonnes : Code ; Ce qui est vérifié ; Gravité (« Bloquant », « À corriger », « Pour information ») ; Anomalies [ENTIER] ; État (« garanti par la base », « conforme » ou « à corriger ») ; Quoi faire (la raison de la garantie, sinon le conseil).
- **Une feuille par contrôle en anomalie ayant un détail**, titrée « <code> <libellé> » (31 car.) : titre « <code> — <libellé> » et « Quoi faire : … » ; colonnes = toutes les clés rencontrées dans le détail, dans leur ordre d'apparition, libellées par `controles.COLONNES` (sinon clé avec `_` → espace, capitalisée) ; valeurs : listes jointes par « , », dictionnaires « k : v, … », booléens « oui »/« non ». Pas de format numérique.

### 11.6 `GET /api/export/valorisation` — `exporter_valorisation`, `exports_analyse.py:95-123`
- **Rôles** : Achats. **Requête** : `date_reference` (date quelconque ; l'écran envoie la date « au » choisie, souvent une fin de mois ; aucune contrainte de fin de mois côté serveur).
- **Fichier** : `valorisation-AAAA-MM-JJ.xlsx`. Feuille **« Valorisation »**. Titre : « Valorisation du stock détenu au JJ/MM/AAAA » ; « Valeur du stock : N MAD, dont en machine (fil monté sur les métiers) M MAD » ; « Coût moyen pondéré des achats réels ; à défaut d'achat, prix du catalogue. ».
- **Lignes** : matières dont |stock| > 1e-6 ou stock en machine > 1e-6, par valeur décroissante. **Colonnes** : Référence ; Composition (`nature`) ; Fournisseur ; Magasins (kg) [KG] ; En machine (kg) [KG] ; Stock détenu (kg) [KG] ; Coût moyen (MAD / kg) [PRIX] ; Prix catalogue (/ kg) [PRIX] (devise de la matière) ; Devise ; Valeur (MAD) [MONTANT] ; Écart catalogue (MAD) [MONTANT].

### 11.7 `GET /api/export/prix` — `exporter_prix`, `exports_analyse.py:126-157`
- **Rôles** : Achats. Aucun paramètre. **Fichier** : `prix-AAAA-MM-JJ.xlsx`.
- **Feuille « Historique des achats »** (titre « Historique des prix payés au JJ/MM/AAAA ») : Date (texte ISO) ; Bon ; Référence ; Composition (`nature`) ; Fournisseur ; Quantité (kg) [KG] ; Prix payé (/ kg) [PRIX] ; Devise ; Prix précédent [PRIX] ; Évolution [POURCENT] ; Montant (MAD) [MONTANT].
- **Feuille « Matrice des prix »** (titre « Matrice des prix (prix moyen pondéré du mois au kilo, dans la devise de la facture, le mois récent à gauche) au JJ/MM/AAAA ») : Référence ; Composition ; Type de fil ; Titrage (« valeur unité ») ; Couleur ; Fournisseur ; Devise ; puis une colonne par mois « AAAA-MM » [PRIX], **du plus récent au plus ancien** (36 mois au plus).

### 11.8 `GET /api/export/opportunites` — `exporter_opportunites`, `exports_analyse.py:160-189`
- **Rôles** : Achats. **Requête** : `meme_couleur: bool = true`, `autre_fournisseur: bool = true`, `prix_catalogue: bool = false`, `fenetre_jours: int|null` (sans bornes ici) ; **pas** de `date_reference` (aujourd'hui).
- **Fichier** : `opportunites-AAAA-MM-JJ.xlsx`. Feuille **« Opportunités »** : titre « Opportunités d'économies au JJ/MM/AAAA » puis l'avertissement de la route.
- **Colonnes** : Référence ; Fournisseur actuel ; Composition ; Type de fil ; Titrage ; Couleur ; Prix actuel (MAD / kg) [PRIX] ; Payé le (texte ISO) ; Base ; Comparable (référence alternative) ; Chez (fournisseur alternatif) ; Son prix (MAD / kg) [PRIX] ; « Payé le  » (avec une espace finale, pour distinguer l'en-tête) ; « Base  » (idem) ; Écart [POURCENT] ; Conso / an [KG] ; Économie / an (MAD) [MONTANT].

### 11.9 `GET /api/export/fournisseurs` — `exporter_fournisseurs`, `exports_analyse.py:192-222`
- **Rôles** : Achats. **Fichier** : `fournisseurs-AAAA-MM-JJ.xlsx`.
- **Feuille « Fournisseurs »** (titre « Performance des fournisseurs au JJ/MM/AAAA » ; « Cible OTIF : NN% ») triée par score décroissant (sans score en dernier) : Fournisseur ; Pays ; Devise ; Délai (j) [ENTIER] ; Commandes [ENTIER] ; Acheté (MAD) [MONTANT] ; Réceptions [ENTIER] ; À l'heure [POURCENT] ; Complètes [POURCENT] ; Conformes [POURCENT] ; OTIF [POURCENT] ; Retours [POURCENT] ; Écart de pesée [POURCENT] ; Score / 100 [ENTIER] ; Classement ; Action.
- **Feuille « Réceptions notées »** (titre « Réceptions notées au JJ/MM/AAAA ») : Réception ; Fournisseur ; Date (texte ISO) ; À l'heure ; Complète ; Conforme ; Parfaite (OTIF) (« oui », « non » ou « — ») ; Lignes hors tolérance [ENTIER] ; Écart de pesée [POURCENT].

### 11.10 `GET /api/export/journal` — `exporter_journal`, `exports_analyse.py:229-259`
- **Rôles** : Direction. **Requête** : `q: str = ""` (max 120), `utilisateur`, `action`, `objet`, `du`, `au` (mêmes règles que `GET /api/journal`) ; limite fixe 100 000 lignes.
- **Fichier** : `journal-des-actions-AAAA-MM-JJ.xlsx`. Feuille **« Journal des actions »** : titre « Journal des actions au JJ/MM/AAAA » ; si filtres : « Filtres — par : X · action : Y · sur : Z · du : JJ/MM/AAAA · au : JJ/MM/AAAA · mots : q ». Colonnes : Quand (date-heure à la seconde) ; Par ; Rôle (libellé) ; Action ; Sur (objet) ; N° [ENTIER] (objet_id) ; Détail. Du plus récent au plus ancien.

### 11.11 `GET /api/export/echeancier` — `exporter_echeancier`, `exports_analyse.py:262-301`
- **Rôles** : Achats. **Requête** : `du`, `au`. **Fichier** : `echeancier-AAAA-MM-JJ.xlsx`.
- **Feuille « Échéances »** (titre « Échéancier des paiements au JJ/MM/AAAA » ; « À payer : N MAD · échu : N MAD · à dater : N MAD ») : Échéance (texte ISO) ; Nature (genre) ; Fournisseur ou prestataire ; Pièce ; Montant [MONTANT] ; Devise ; Montant MAD [MONTANT] ; En retard (« oui » ou vide) ; Montant estimé (« estimé » ou vide).
- **Feuille « À dater »** (titre « Dû sans échéance connue au JJ/MM/AAAA ») : Nature ; Fournisseur ou prestataire ; Pièce ; Montant [MONTANT] ; Devise ; Montant MAD [MONTANT] ; Montant estimé (« estimé (pesée × prix) » ou vide).
- **Feuille « Par mois »** (titre « Échéancier par mois au JJ/MM/AAAA ») : Mois (« AAAA-MM ») ; À payer (MAD) [MONTANT].
- Les factures réglées et écartées ne sont pas exportées.

---

## 12. Documents HTML imprimables

Tous : `text/html`, police système (`-apple-system, Segoe UI, Roboto, sans-serif`), un bouton « Imprimer » (`window.print()`) masqué à l'impression. Aucun ne porte le papier à en-tête de l'usine.

### 12.1 Bilan du mois — `GET /api/bilan?mois=AAAA-MM` (`suivi.py:617-674`)
- `<title>` : « Bilan MM/AAAA ». Marges 28 px, corps 13 px ; grille de 4 cases.
- **Blocs dans l'ordre** :
  1. Titre « Bilan matières premières — MM/AAAA » ; sous-titre : raison sociale (réglage `nom_entreprise`).
  2. **« Le mois en chiffres »** — cases (libellé, valeur en gros, commentaire) :
     - « Stock au début » — `N kg` — `N MAD` (valeur au début) ;
     - « Stock à la fin » — `N kg` — `N MAD` ;
     - « Stock d'ouverture saisi » — `N kg` — « entré dans le mois » (seulement si des ouvertures existent dans le mois) ;
     - « Entrées (réceptions) » — `N kg` — « N MAD, hors réceptions annulées » ;
     - « Sorties vers les machines » — `N kg` — « dont N kg revenus · coût net N MAD » ;
     - « Tissé » — `N m²` — « N ordre(s) » ;
     - « Commandes émises » — nombre — « N réception(s) » ;
     - « Livraisons parfaites (OTIF) » — `NN %` (ou « — % ») — « sur N réception(s) » ;
     - « Ajustements » — `N,N kg` — « retours fournisseur N kg ».
  3. Paragraphe : « Valeurs au coût moyen pondéré (celles de la page Valorisation à ces dates) ; à une date passée, le fil monté sur les métiers n'est pas compté (son montage n'a pas d'historique). Stock à la fin = début + entrées + ouvertures − sorties + retours des machines − retours fournisseur + ajustements + annulations. **Annulations (contre-passations) datées du mois : N,N kg** (libellé du type N,N kg, …) — elles défont des écritures, parfois d'un mois précédent, et ne comptent ni en sorties ni en entrées. »
  4. **« Fabrication, qualité par qualité »** — tableau Qualité | m² tissés ; « Aucun ordre ce mois-ci. » si vide.
  5. **« Les plus grands écarts entre la recette et le réel »** — tableau Ordre | Qualité | Prévu (kg) | Sorti net (kg) | Écart (%, 1 décimale) ; 8 lignes au plus ; « Aucun. » si vide.
  6. **« À la fin du mois »** — « N matière(s) en rupture, N critique(s). ».
- Nombres : séparateur de milliers = espace, virgule décimale, « — » pour une valeur absente, jamais « -0 ».

### 12.2 Feuille de comptage — `GET /api/inventaires/{iid}/feuille` (`inventaires.py:433-504`)
- `<title>` « Feuille de comptage INV-… » ; page **A4 paysage**, marges 10 mm ; corps 10 pt.
- **Une page par magasin** (magasins triés par code) ; lignes triées par référence, date d'entrée du lot, numéro de lot. Avec `recomptage=true` : seulement les lignes « à recompter » (premier comptage hors tolérance, pas encore recompté), théorique affiché.
- **En-tête de page** : à gauche « Feuille de comptage — INV-… » (ou « Feuille de recomptage — INV-… ») et « <libellé> · compté le JJ/MM/AAAA · magasin **CODE** · N lot(s)[ · avec le théorique] » ; à droite, zone de signatures « Compté par : ______________________ » / « Contrôlé par : ____________________ ».
- **Tableau** (en-tête répété à chaque page, lignes insécables) : N° (rang) ; Référence (en gras, désignation en petit si différente) ; Lot (gras, chasse fixe) ; Conditionnement (« 2,5 kg / bobine · 288 bob. / palette », poids sans zéros inutiles) ; *Théorique* (kg, seulement si `theorique` ou `recomptage`) ; Palettes (case vide, 22 mm) ; Bobines (case vide) ; Compté (kg) (case vide) ; Observations (case vide, 55 mm).
- **Pied** : « Un lot trouvé sur place et absent de la liste : l'écrire au dos (référence, lot, quantité). Un écart se justifie à la saisie, au-delà de la tolérance de N %. ».
- Inventaire sans ligne : « Aucun lot figé dans cet inventaire. ».
- Par défaut le théorique n'est **pas** montré (comptage « à l'aveugle »).

### 12.3 Étiquettes de lots — `GET /api/lots/etiquettes?ids=…` (`stock.py:361-415`)
- `<title>` « Étiquettes de lots » ; format de page **100 × 70 mm**, marge 4 mm ; **une étiquette par page** (60 mm de haut, cadre pointillé à l'écran seulement).
- **Contenu d'une étiquette** : à gauche le **QR** (34 × 34 mm ; contenu `<adresse des QR>/lot/<id>`, correction M, sans marge) — lu par le téléphone, il ouvre la fiche du lot (route `/lot/:id` de l'écran) ; à droite, de haut en bas : la **référence** (13 pt gras) ; « **Lot <numéro>** » (16 pt, très gras) ; le **fournisseur** (du lot, sinon de la matière) ; « Entré le JJ/MM/AAAA » ; « <quantité> à l'impression » (`kg_et_metres` : « 14,30 kg », et « ≈ 1 021 ml » pour un cuir, des franges, un ruban ; quantité = Σ des soldes, quarantaine comprise) ; « N° <id> » (gris, 9 pt).
- **Étiquette de quarantaine** : si une partie du lot est dans un magasin de type Quarantaine, un bandeau encadré en gras « **QUARANTAINE — NE PAS SORTIR** » s'ajoute sous le n°.

### 12.4 QR d'accès — `GET /api/acces/qr` (`stock.py:354-358`)
- Pas une page : un fragment `<svg>` (servi en `text/html`) que l'écran insère dans Réglages. QR de l'adresse que les téléphones doivent ouvrir (réglage `adresse_publique`, sinon l'adresse de la requête avec l'IP réseau à la place de `localhost`), correction M, échelle 6, marge de 2 modules. Aucun libellé.

---

## 13. Points incohérents ou ambigus

1. **Pas de filtre de prix générique.** Le masquage pour l'alimentation est écrit route par route, au premier niveau des lignes, avec des listes de champs différentes (`stock.masquer_prix`, `operations._pour`, `inventaires._sans_prix`, `pilotage.MONTANTS_STOCK`, `pilotage.nomenclature`). `docs/PLAN.md` exige un filtre `sans_prix` générique à toute profondeur : à concevoir, il n'existe pas.
2. **Réponses d'écriture des opérations non masquées** : `POST/PUT /api/operations`, `/valider`, `/annuler` renvoient `operation_dict` sans `_pour` (`operations.py:356,378,442,457`). Pas de fuite aujourd'hui (seule l'ouverture porte un prix et elle est interdite à l'alimentation), mais la règle n'est pas tenue structurellement.
3. **Ce que l'alimentation voit encore** : `GET /api/parametres` (seuils en MAD — `seuil_approbation`, `seuil_bc_urgent`, `seuil_tier1..3`… —, banques, ICE, période close) ; `GET /api/devises` et l'historique des cours ; dans `GET /api/stock`, le conseil d'achat chiffré en quantités (`quantite_a_commander`, `palettes_a_commander`, `unites_a_commander`, `quantite_a_commander_achat`, `bons_en_preparation`, `sans_achat`, `classe_abc`) alors que le commentaire (`pilotage.py:39`) annonce « ni prix ni montant, ni le conseil d'achat » (seuls les montants et `action` sont retirés).
4. **Deux bons de commande Excel** : `GET /api/export/bon-de-commande/{cid}` (ici) est en **français et porte les prix confirmés** ; la décision de Mohamed (bon fournisseur en anglais, sans prix — `achats.lignes_du_bon`, `achats.py:956-959`) est appliquée par la route de la partie A (`/api/export/commandes/{cid}/bon`). Celle-ci n'est appelée par aucun écran : à supprimer ou à aligner.
5. **Routes orphelines** (aucun appel dans `ecran/src`) : `GET /api/besoins`, `GET /api/lots` (pilotage), `GET /api/lots/disponibles`, `GET /api/export/bon-de-commande/{cid}`.
6. **Deux vocabulaires de mouvements** : `/api/mouvements`, `/api/lots/{lid}`, le bilan utilisent les codes de la base (`OUVERTURE`, `RECEPTION`, `SORTIE`…, libellés français sobres) ; `/api/tracabilite` renvoie les codes de l'ERP Fil (`STOCK_INITIAL`, `ENTREE_RECEPTION`, `SORTIE_PROD`…, libellés avec émojis « 📦 Entrée Réception »). De même deux vues des lots : `/api/soldes` (base, par magasin, statut) et `/api/lots` (moteur, « (sans lot) », `negatif`).
7. **Commentaires périmés** : `production_plan.py:194` dit que `/production/realise` « remplace la vue de pilotage.py du même chemin » — elle n'existe plus dans pilotage ; `suivi.py:3` annonce l'« import … du plan par tableur » — aucune route ne l'implémente ; `calcul/moteur.py:1795` dit `valeur_mad` = « les magasins seuls » alors que le calcul (`calcul/moteur.py:2025-2043`) et l'export l'additionnent au stock en machine.
8. **Deux mesures de l'âge des sauvegardes** : `/api/sante` (`sauvegarde.etat()`) compte tous les fichiers du dossier, y compris ceux d'autres bases ; `/api/sauvegardes` et `/api/etat-serveur` ne comptent que la base courante. Une sauvegarde récente d'une base d'essai peut faire dire « à jour » à la surveillance.
9. **Erreurs 500 non traduites** : `POST /api/sauvegardes` (pg_dump absent ou en échec : `RuntimeError`) ; `GET /api/bilan?mois=2026-13` (le motif `^\d{4}-\d{2}$` laisse passer un mois invalide) ; `GET /api/piece/{pid}/fichier` si le fichier a disparu du disque ; import des matières appliqué avec des valeurs qui violent les contraintes de la base (voir 14).
10. **Codes et style d'erreur hétérogènes** : `HTTPException(400, "date de référence hors période : …")`, `404 "fournisseur inconnu : « … »"`, `400 "préciser un lot, un ordre de fabrication ou un fil"` (minuscules, sans point, 400) contre la convention `erreur()` (422/404/409, phrase complète). La traduction des erreurs de validation est partielle (« valeur incorrecte integer, unable to parse string as an integer »).
11. **Bilan** : les kilos d'entrées incluent les réceptions annulées (leur annulation est dans « Annulations ») alors que la valeur en MAD les exclut ; la case « Entrées » mêle les deux bases. Le stock début/fin en kg ne compte pas le fil en machine. Un mois futur est accepté. Pas de papier à en-tête (seule la raison sociale), comme la feuille de comptage et les étiquettes (aucun en-tête) — le PLAN exige l'en-tête de l'usine sur les documents A4.
12. **Ordre des numéros d'OF** : la date du « dernier ordre » qui bloque une validation antérieure compte les ordres **annulés** (`statut != "brouillon"`, `production.py:287,516`) : un ordre annulé daté plus tard empêche de valider un ordre plus ancien. Choix ou oubli ?
13. **Retours en brouillon d'un ordre annulé** : `annuler_bon` n'annule que les retours **validés** ; un brouillon de retour rattaché reste et ne pourra être validé (sorti net = 0 → refus « n'est sorti que de 0 kg »), sans message dédié.
14. **Import des matières** : (a) pas de contrôle des références en double dans le fichier (deux lignes « nouvelles » identiques → erreur d'unicité 500 à l'application) ; (b) pas de contrôle de signe ni de longueur (prix ou poids de bobine négatifs, désignation > 160, code couleur > 32, groupe > 64, unité d'achat > 32 car.) : l'aperçu passe, l'application échoue en 500 ; (c) une cellule vide ne vide jamais un champ ; (d) `unite_achat` libre (seul `ml` refusé) et `contenance_achat` non contrôlée par rapport à l'unité ; (e) l'aperçu montre `fournisseur_id` (identifiants) au lieu des noms ; (f) aucune vérification de `version` (une fiche modifiée entre l'aperçu et l'application est écrasée) ; (g) « les mêmes règles qu'à l'écran » n'est que partiellement vrai (à confronter aux règles de `referentiels.py`) ; (h) la feuille lue est la feuille active, pas « Matières » par son nom.
15. **Comptage d'inventaire** : pour une ligne existante, un champ absent (`compte`, `palettes`, `bobines`, `justification`) est **effacé**, alors que `second_compte` absent est **conservé** — deux sémantiques dans le même corps. Justification minimale : 3 caractères pour un écart d'inventaire, 5 pour un ajustement justifié. Les lots créés par un « lot trouvé » restent si l'inventaire est abandonné. Les classes ABC du périmètre et de l'inventaire tournant sont celles d'aujourd'hui, pas de la date de l'inventaire.
16. **Comptes** : `PUT /api/utilisateurs/{uid}` exige `identifiant` puis l'ignore ; un changement de code (par la direction ou soi-même) ne ferme pas les sessions ouvertes (seule la désactivation le fait) ; `PUT /api/devises` écrit une ligne d'historique et de journal même sans changement, accepte `actif=false` sur MAD et un code non alphabétique.
17. **Lecture exposée sans session** : `GET /api/visages` donne les noms et rôles de tous les comptes actifs à quiconque joint le serveur (voulu pour l'écran de connexion, à confirmer) ; `POST /api/deconnexion` est exempté de l'en-tête anti-falsification (une page tierce peut déconnecter) ; la réponse 403 « Requête refusée » du middleware part sans les en-têtes de sécurité.
18. **Exports hétérogènes** : dates tantôt vraies dates Excel (mouvements, sorties — format JJ/MM/AAAA —, pilotage « Dernière sortie », journal), tantôt texte ISO (prix « Date », opportunités « Payé le », fournisseurs « Date », échéancier « Échéance ») ; « Gravité » brute dans l'export de pilotage mais traduite dans l'export des contrôles ; `/export/opportunites` n'accepte pas `date_reference` (alors que la route d'écran oui) et ne borne pas `fenetre_jours` ; `/export/journal` limite `q` à 120 car. contre aucune limite pour `/journal` ; `/export/mouvements` n'offre pas la valeur (CMUP) que l'écran peut afficher ; le modèle d'import n'a aucune des conventions d'export (ni gel, ni filtre, ni formats).
19. **Listes tronquées sans le dire** : `GET /api/operations` (1 000), `GET /api/signalements` (300), réglées de l'échéancier (300), historique des paramètres et des cours (500) ; `GET /api/bons` n'a ni limite ni pagination et recalcule la consommation de tous les ordres à chaque appel.
20. **Échéancier** : conversion au cours **du jour** (pas figé) ; le montant estimé d'une facture additionne pesée × prix des lignes en supposant qu'elles sont dans la devise de la facture ; `du`/`au` ne filtrent que les lignes datées.
21. **Réclamations** : une réclamation close peut voir son issue changée sans être rouverte (il suffit d'envoyer une issue) ; la quantité réclamée n'est bornée que si une réception est donnée ; le motif n'est pas restreint à la liste proposée.
22. **Divers** : `POST /api/bons/proposition` est une lecture en POST (en-tête exigé) ouverte à tous les rôles ; `GET /api/acces` suppose le port 80 quand la requête n'en porte pas, même en HTTPS ; `GET /api/pieces/{objet}/{oid}` ne contrôle pas `objet` ; une pièce retirée reste sur le disque (voulu) ; `PUT /api/production/plan` accepte des qualités arrêtées et contrôle les coefficients (0–20) dans le code et non dans le modèle ; `POST /api/indicateurs/photographier` remplace la photo du jour sans journal.
