# Héritage Gestion MP — les contrôles de cohérence (C01 → C38)

> Inventaire tiré du **code** de Gestion MP (`/Users/mohamed/gestion-mp`, état du 8 octobre 2026,
> dernier commit `2d588b9`), complété par `docs/ETAT-DES-LIEUX.md`, `docs/AUDIT-2026-10-08.md`,
> `docs/conformite/*` et l'historique git. Les références `fichier:ligne` pointent dans l'ancien
> code (chemins relatifs à `gestion_mp/` sauf mention `ecran/src/...`).
> But : qu'une équipe puisse reconstruire les 38 contrôles **sans relire l'ancien code**.

---

## 1. Vue d'ensemble

| Élément | Où | Rôle |
|---|---|---|
| Moteur des contrôles | `calcul/controles.py` (1142 lignes) | `controler()` rend 38 objets `Controle` ; `synthese()` en fait la note ; `stock_negatif_passe()` sert C37 |
| Appel côté serveur | `depot.py:706-712` (`depot.controler`) | Passe les données « à la date » **et** toutes les données (`complet`) |
| Route de l'écran | `GET /api/controles` — `api/pilotage.py:349-375` | La liste complète, la synthèse, les libellés de colonnes |
| Synthèse au Cockpit | `GET /api/cockpit` — `api/pilotage.py:242-253` | `tableau["controles"] = synthese(...)` (pastille du menu, Accueil, Cockpit) |
| Contrôle des soldes (hors des 38) | `GET /api/controles/soldes` — `api/stock.py:418-433` | Soldes tenus = somme du journal, en SQL brut |
| Export Excel dédié | `GET /api/export/controles` — `api/exports_analyse.py:44-82` | Feuille « Contrôles » + une feuille par contrôle en anomalie |
| Export Excel du pilotage | `GET /api/export/pilotage` — `api/exports.py:139`, `:228-234` | Une feuille « Contrôles » résumée |
| Écran | `ecran/src/components/direction/AnalyseControles.tsx` (Analyse › Contrôles, `/analyse?onglet=controles`) | Indicateurs, tableau, fenêtre de détail avec liens |
| Guide | `ecran/src/pages/Guide.tsx:401` | « Trente-huit vérifications de cohérence, chacune avec ses lignes fautives et ce qu'il faut faire. » ; `:327` « Analyse › Contrôles : aucun bloquant ? Chaque anomalie dit quoi faire. » ; `:44-45` soldes et journal |
| Vérificateur indépendant | `verificateur.py:130-139` | Recalcule en SQL les recettes ≠ 100 % et vérifie que C01 (lu par `/api/controles`) les voit toutes |

### 1.1 Origine : les contrôles du classeur

Docstring `calcul/controles.py:1-19` : les contrôles rejouent les feuilles « 🧪 Tests » (codes T01…T20)
et « 🔍 Audit » (codes C05, C06, C14 de l'audit) du classeur Excel d'origine, repris par l'ERP Fil
puis par Gestion MP. Correspondances données en commentaire :

| Gestion MP | Classeur | Ligne |
|---|---|---|
| C01 | T01 | `controles.py:244` |
| C02 | T02 | `:262` |
| C03 | T03 | `:273` |
| C04 | T04 | `:295` |
| C05 | T07 | `:309` |
| C06 | T08 | `:321` |
| C07 | T09 | `:367` |
| C08 | T10 | `:380` |
| C09, C10, C11 | T11 / T12 / T13 / T14 | `:408` |
| C12 | T15 | `:443` |
| C13 | Audit C05 | `:493` |
| C14 | Audit C06 | `:513` |
| C15 | Audit C14 | `:524` |
| C16…C38 | « Nouveau » (ERP Fil / Gestion MP) | — |

Contrôles du classeur **disparus volontairement** (docstring `:7-18`) :
- T05, T06 (références et fournisseurs orphelins dans les mouvements) → devenus clés étrangères ;
- T17, T18, T19 (pesées non recopiées vers mouvement / archive / historique de prix) → la
  validation d'une réception écrit tout dans la même transaction ;
- T20 (formules non propagées dans les lignes de BC) → problème de tableur.
Ils sont « remplacés par `INTEGRITE` » (en pratique : C16 et le contrôle des soldes).

### 1.2 Historique (git)

| Commit | Date | Effet sur les contrôles |
|---|---|---|
| `ad52be7` | 2026-10-03 | Naissance du serveur : C01 → C34 repris de l'ERP Fil |
| `af3924a` | 2026-10-03 | `MOTIFS_PERMIS` (C03 par famille de motifs), `QUOI_FAIRE` + `_HORS_SAISIE` |
| `08c6df7` | 2026-10-03 | C29 : taux de TVA réglé + `tva_attendue` unique (avant : 20 % en dur, `TAUX_TVA_IMPORT`) |
| `f85dabd` | 2026-10-08 | Texte C01 (direction corrige, achats signalent), lien C27 vers `/stock?onglet=lots` |
| `bcb14b5` | 2026-10-08 | C06 : échéance = ETA sinon date promise, + retard toléré, brouillons exclus |
| `5ca0960` | 2026-10-08 | C12 : soldes tenus contre journal, lot × magasin (avant : somme des magasins contre stock net) |
| `6f3a340` | 2026-10-08 | **C35 créé** (frais aberrants d'un dossier) |
| `58f507c` | 2026-10-08 | **C36 créé** (facture ≠ marchandise reçue) ; C35 étendu aux lignes (`lignes_aberrantes`) |
| `61027e4` | 2026-10-08 | **« Lot sous zéro à une date passée » créé sous le code C36** (branche valorisation) ; contrôles d'intégrité sur toutes les données (`complet`) |
| `91448ce` | 2026-10-08 | **« Prix catalogue loin du dernier prix payé » créé sous le code C36** (autre branche) |
| `96db9ea` | 2026-10-08 | `GARANTIS` + propriété `garanti` (« garanti par la base »), score qui ne les compte pas ; texte C11, C27 |
| `202d1a0` | 2026-10-08 | C22 au prorata du % de chaque fil ; C25 reformulé (« le magasin le compte encore ») |
| `f216509` | 2026-10-08 | **Renumérotation : « lot sous zéro à une date passée » C36 → C37** (fusion) ; Guide : 37 vérifications |
| `93fd464` | 2026-10-08 | **Renumérotation : « prix catalogue » C36 → C38** (fusion) ; Guide : 38 vérifications |
| `30b31c3` | 2026-10-08 | C33 jugé sur la consommation de l'horizon et `stock_min_plafonne` |
| `d2e1e39` | 2026-10-08 | Tout en kg : C15 et C38 lisent `prix_kg` ; suppression de la colonne « Unité » ajoutée aux détails (`QUANTITES`, `_unites`) |

Le code **C36 a donc désigné trois contrôles différents** le même jour ; seul celui des factures
d'importation l'a gardé.

---

## 2. Structure commune

### 2.1 L'objet `Controle` (`calcul/controles.py:50-74`)

```text
@dataclass Controle
  code: str            « C01 » … « C38 »
  libelle: str         le titre affiché (parfois calculé avec la valeur d'un réglage)
  anomalies: int       le nombre TOTAL de lignes fautives (pas tronqué)
  detail: list[dict]   les lignes fautives (souvent tronquées à 200)
  gravite: str         « bloquant » | « avertissement » (défaut) | « information »
  conforme   (propriété) = anomalies == 0
  garanti    (propriété) = GARANTIS[code] si conforme, sinon ""   (texte : pourquoi il ne peut pas sonner)
  quoi_faire (propriété) = QUOI_FAIRE[code][0]
  vers       (propriété) = QUOI_FAIRE[code][1]  (route de l'écran où corriger)
```

### 2.2 Gravités

| Clé | Libellé écran / Excel (`AnalyseControles.tsx:45-49`, `exports_analyse.py:37`) | Sens | Couleur écran (`tonControle`, `AnalyseControles.tsx:51-56`) |
|---|---|---|---|
| `bloquant` | Bloquant | Le pilotage est faussé tant que ce n'est pas corrigé ; bandeau rouge « le pilotage est faussé tant que Cxx n'a pas été corrigé » ; compté dans `synthese.bloquants` ; détail en message « erreur » | critique (rouge) |
| `avertissement` | À corriger | Une saisie à revoir | attention (orange) |
| `information` | Pour information | Un fait à connaître, pas une faute | neutre |
| (conforme) | OK | — | ok (vert) |
| (garanti) | « garanti par la base » | La base empêche ce contrôle de sonner | neutre |

Répartition : **11 bloquants** (C01, C05, C09, C11, C12, C16, C20, C21, C23, C27, C37), **20
avertissements** (C02, C03, C04, C06, C08, C10, C13, C14, C15, C22, C24, C25, C26, C28, C29, C31,
C34, C35, C36, C38), **7 informations** (C07, C17, C18, C19, C30, C32, C33).

### 2.3 « Garanti par la base » (`GARANTIS`, `controles.py:172-184`)

Contrôles que la base rend impossibles (contrainte ou structure). Ils sont **toujours rejoués** (une
reprise ou une contrainte retirée les ferait sonner) mais, s'ils sont à zéro, l'écran affiche
« garanti par la base » et la note ne les compte pas.

| Code | Texte exact | Contrainte réelle (`modeles.py`) |
|---|---|---|
| C09 | « La base refuse un prix négatif (contrainte article_prix_check). » | `CheckConstraint("prix >= 0")` table `article` (`modeles.py:271`) |
| C10 | « La base refuse un délai fournisseur nul ou négatif (fournisseur_delai_jours_check). » | `CheckConstraint("delai_jours > 0")` table `fournisseur` (`:228`) |
| C11 | « La base refuse un cours de change nul ou négatif (devise_taux_check). » | `CheckConstraint("taux > 0")` table `devise` (`:161`) |
| C16 | « Les mouvements pointent leur matière et leur fournisseur (par le lot) par des clés étrangères : un mouvement orphelin ne peut pas s'écrire. » | `mouvement.article_id`, `lot_id` NOT NULL FK ; `lot.fournisseur_id` FK |
| C21 | « La devise d'un prix est une clé étrangère vers les devises : un prix sans devise connue ne peut pas s'écrire. » | `article.devise` FK `devise.code` NOT NULL (`:296`) |

Les noms de contraintes cités sont les noms automatiques de PostgreSQL (contraintes non nommées).

### 2.4 « Ne peut pas venir de la saisie » (`_HORS_SAISIE`, `controles.py:81-85`)

Texte « quoi faire » commun à C02, C04, C14, C16, C26, C31, C32 :

> « Gestion MP refuse déjà cette saisie : la ligne vient d'une reprise de données ou d'une écriture
> faite hors de l'écran. Prévenir la personne qui entretient le serveur, puis annuler le document
> fautif (contre-passation) et le ressaisir. »

Ces contrôles **ne sont pas** dans `GARANTIS` (sauf C16) : leur zéro compte comme « conforme » dans
la note (voir § 6).

### 2.5 Données lues : `donnees` et `complet` (`controles.py:229-242`, `depot.py:706-712`)

`controler(donnees, lignes_stock, date_ref, complet=None, aujourdhui=None)` :
- `donnees` = `depot.charger_au(s, jour)` : les données **telles qu'au soir de `jour`**
  (`moteur.a_la_date`, `moteur.py:85-189`) — journal, réceptions, commandes (reçu recalculé),
  historique de prix et ordres datés ≤ jour ; catalogue, réglages, dossiers d'import tels
  qu'aujourd'hui ; `soldes=None` ; montage des métiers ignoré si `jour` < aujourd'hui.
- `lignes_stock` = `moteur.etat_stock(donnees, jour)`.
- `complet` = `depot.charger(s)` : **toutes** les données, soldes tenus compris. Utilisé par les
  contrôles d'intégrité **C12, C14, C27, C37** (audit 2-F, G7 : rejoués à une date, ils perdaient
  les écritures datées après elle).
- `aujourdhui` = `max(date_ref, date.today())` : la date à laquelle C14 juge le futur.
- `parametres = donnees.parametres` (réglages convertis, voir REGLAGES.md).
- `references` = toutes les références du catalogue (actives **et** inactives) ; `fournisseurs` =
  tous les noms de fournisseurs.

La date de référence vient de `?date_reference=AAAA-MM-JJ` (défaut aujourd'hui), refusée hors
2000–2100 (`pilotage.py:28-36`, `exports.py:50-53`, HTTP 400).

### 2.6 Ordre de la liste rendue

`controler()` rend les contrôles dans cet ordre (pas numérique) :
C01, C02, C03, C04, C05, C06, C07, C08, C09, C10, C11, C12, C13, C14, C15, C16, C19, C21, C20, C22,
C24, C25, C23, C26, C27, C37, C28, C34, C29, C35, C36, C31, C32, C30, C33, C38, C17, C18.
- L'API le rend tel quel.
- L'écran trie : non conformes d'abord, puis bloquant < avertissement < information (tri stable,
  donc dans l'ordre ci-dessus à égalité) — `AnalyseControles.tsx:80-84`.
- L'export dédié trie par `(conforme, gravité, code)` — `exports_analyse.py:56-57`.

### 2.7 Troncature du détail

`anomalies` est toujours le compte complet ; `detail` est souvent limité :
- 200 **premières** lignes : C02, C03, C04, C05, C06 (après tri par échéance), C08, C12, C13 (tri
  par manque décroissant), C14, C15, C16, C37, C31, C32, C30 (tri), C33 (tri), C38 (tri), C17
  (tri), C18 ;
- 200 **dernières** lignes : C26 (`sorties_sans_lot[-200:]`) ;
- **non tronqué** : C01, C07, C09, C10, C11, C19, C21, C20, C22, C24, C25, C23, C27, C28, C34, C29,
  C35, C36.
L'écran l'annonce : « N ligne(s) à examiner (les k premières affichées) » (`AnalyseControles.tsx:303-304`).

### 2.8 La synthèse (`synthese()`, `controles.py:1128-1142`)

```text
bloquants = contrôles gravite == bloquant ET non conformes
garantis  = nombre de contrôles dont `garanti` est non vide (donc conformes ET dans GARANTIS)
verifies  = 38 − garantis
conformes = conformes ET non garantis
renvoie {
  total:     verifies,
  conformes: conformes,
  garantis:  garantis,
  anomalies: nombre de contrôles NON conformes (pas de lignes !),
  bloquants: len(bloquants),
  score:     conformes / verifies (1.0 si verifies == 0)
}
```

Affichages : écran « Score » = `score` en %, détail « X conformes sur Y vérifiés · Z garantis par la
base » (`AnalyseControles.tsx:96-98`) ; Cockpit `conformes / total` (`Cockpit.tsx:134`) ; pastille du
menu = `controles.anomalies` de `/cockpit` (`App.tsx:187-218`) ; Accueil (`Accueil.tsx:248-346`)
rouge si bloquants, orange si anomalies.

### 2.9 Ce que renvoie `GET /api/controles` (`api/pilotage.py:349-375`)

Droit : `ACHATS` (= direction + achats ; l'alimentation reçoit 403 « Cette action est réservée à :
achats. » — `securite.py:104-112`). Aucun prix n'est masqué : l'alimentation n'y a pas accès.

```json
{
  "date_reference": "AAAA-MM-JJ",
  "synthese": { "total", "conformes", "garantis", "anomalies", "bloquants", "score" },
  "controles": [ { "code", "libelle", "anomalies", "conforme", "garanti", "gravite",
                   "quoi_faire", "vers", "detail": [ {clé: valeur, …} ] } ],
  "colonnes": { clé technique → libellé français }   // COLONNES, controles.py:192-219
}
```

### 2.10 Les colonnes du détail (`COLONNES`, `controles.py:190-219`)

« La clé technique ne s'affiche jamais. Une quantité de matière est toujours en kilos, cuir, franges
et ruban compris. » Une clé absente du dictionnaire s'affiche avec sa première lettre en majuscule et
les `_` en espaces (écran `AnalyseControles.tsx:288`, export `exports_analyse.py:77`).

| Clé | Libellé | Clé | Libellé |
|---|---|---|---|
| anomalies | Anomalies | metier | Métier |
| apres | Après | metres | Mètres |
| arrivee | Arrivée | metres_montes | Mètres montés |
| attendu | Attendu | mois | Mois |
| bloquants | Bloquants | montant_a_commander_mad | À commander (MAD) |
| catalogue | Catalogue (kg / bobine) | numero | N° |
| conformes | Conformes | numero_of | Ordre (n° OF) |
| conso_mensuelle | Conso / mois | pesee | Pesé |
| constate | Constaté (kg / bobine) | poids | Poids (kg) |
| date | Date | prix | Prix |
| date_apres | Date de l'ordre suivant | qualite | Qualité |
| date_bc | Date de la commande | prix_catalogue | Prix du catalogue |
| dates | Dates | prix_paye | Dernier prix payé |
| delai | Délai (j) | rapport | Catalogue / payé |
| devise_par_defaut | Devise par défaut | quantite | Quantité |
| devises | Devises | reception | Réception |
| dossier | Dossier | reference | Référence |
| ecart | Écart (%) | retard_jours | Retard (j) |
| ecart_mad | Écart (MAD) | retenu | Retenu |
| entrees | Entré | roles | Rôles |
| etage | Étage | score | Score |
| etages | Étages du métier | somme_magasins | Somme des magasins |
| fils | Fils | sorties | Sorti |
| fournisseur | Fournisseur | stock | Stock |
| frais | Frais (MAD) | stock_min_catalogue | Stock minimum |
| jours | Jours | stock_net | Stock net |
| jours_sans_mouvement | Jours sans mouvement | stock_projete | Stock projeté |
| laize | Laize (m) | unite | Unité |
| lot | Lot | taux | Cours |
| magasin | Magasin | total | Total |
| manque | Manque | marchandise_mad | Marchandise (MAD) |
| marchandises | Marchandises | frais_mad | Frais hors TVA (MAD) |
| motif | Motif | surcout_pct | Frais / marchandise (%) |
| facture | Facture | facture_montant | Facture (devise) |
| recu | Reçu, pesée × prix (devise) | tva_attendue | TVA attendue (MAD) |
| tva_saisie | TVA saisie (MAD) | type | Type |
| utilisateur | Par | valeur | Valeur (MAD) |

Formatage des cellules à l'écran (`AnalyseControles.tsx:58-68`) : vide → « — » ; entier → séparateurs
fr-FR ; décimal → 2 décimales ; booléen → Oui/Non ; date ISO `AAAA-MM-JJ` → date française ; liste
jointe par « , ».

### 2.11 Liens dans le détail (`AnalyseControles.tsx:225-273`)

| Colonne | Lien ouvert |
|---|---|
| reference | `/stock?onglet=matieres&q=<référence>` |
| numero_of | `/sorties?ordre=<n° OF>` |
| lot | `/stock?onglet=lots&q=<lot>` |
| metier | `/metiers` |
| numero (commande) | `/commandes?commande=<id>` (id retrouvé par le numéro via `/commandes`) |
| dossier | `/importations?dossier=<id>` |
| reception | `/receptions?reception=<id>` |
| qualite | `/qualites?qualite=<id>` |
| fournisseur | `/catalogue?onglet=fournisseurs&fournisseur=<id>` |

Plus le lien général `vers` (QUOI_FAIRE) affiché après le texte « quoi faire » dans la fenêtre de détail.

### 2.12 L'écran Analyse › Contrôles (`AnalyseControles.tsx`)

- Indicateurs : Score (`part(score)`), Anomalies (« contrôles à revoir »), Bloquants (« le pilotage
  en est faussé » / « aucun »), **Soldes et journal** (« Concordants » / « Écart ! », détail « N
  soldes = journal » ou « k écart(s), n solde(s) négatif(s) »).
- Si les soldes divergent : message d'erreur « Le stock tenu ne retombe pas sur le journal des
  mouvements (… lot(s) en écart, … solde(s) négatif(s)). Une écriture a contourné le chemin normal :
  prévenir la personne qui entretient le serveur avant toute nouvelle saisie. » + 8 premiers écarts
  « lot n° {id}, magasin n° {id} : journal X kg, solde Y kg ».
- Tableau : Code, Ce qui est vérifié, Gravité, Anomalies (« garanti par la base » / « OK » / nombre),
  Quoi faire (« Ne peut pas sonner : <texte GARANTIS> » / « — » / quoi_faire). Filtre « seulement les
  anomalies » (coché par défaut), recherche multi-mots sur code, libellé, gravité, quoi faire, bouton
  « Effacer les filtres », bouton « Exporter en Excel » (`/api/export/controles`).
- Fenêtre de détail : titre « Cxx — libellé », message (erreur si bloquant) « quoi faire » + lien,
  étiquette de gravité, recherche dans les lignes, tableau des colonnes (union des clés des lignes).

### 2.13 Export Excel `GET /api/export/controles` (`exports_analyse.py:44-82`)

Droit `ACHATS`. Fichier `controles-AAAA-MM-JJ.xlsx`.
- Feuille « Contrôles » : titre « Contrôles au JJ/MM/AAAA », ligne « X conformes sur Y vérifiés (et
  Z garantis par la base) · B bloquant(s) · score S% » ; colonnes Code, Ce qui est vérifié, Gravité
  (Bloquant / À corriger / Pour information), Anomalies, État (« garanti par la base » / « conforme »
  / « à corriger »), Quoi faire (texte GARANTIS si garanti, sinon quoi_faire).
- Une feuille par contrôle non conforme ayant un détail, nommée « Cxx libellé » tronqué à 31
  caractères, en-tête « Cxx — libellé » et « Quoi faire : … », colonnes = union des clés.

L'export du pilotage (`exports.py:228-234`) a une feuille « Contrôles » plus pauvre : Code, Contrôle,
Anomalies, Gravité (clé brute), État (« conforme » / « à corriger » — ignore « garanti »).

### 2.14 Le contrôle des soldes `GET /api/controles/soldes` (`api/stock.py:418-433`)

Docstring : « Les soldes tenus à jour égalent-ils la somme du journal ? Ils le doivent toujours : un
écart dirait qu'une écriture a contourné le chemin unique. »

Règle exacte, en SQL direct sur les tables (pas sur le moteur) :
1. `journal[(lot_id, magasin_id)] = SUM(mouvement.quantite)` (quantité **signée** du journal brut ;
   un transfert = deux lignes).
2. `tenus[(lot_id, magasin_id)] = solde.quantite`.
3. Écart sur l'union des clés si `|journal − solde| > POUSSIERE` (1e-3 kg, `services/stock.py:20`).
4. `negatifs` = nombre de soldes `< −POUSSIERE`.
5. Rend `{"conforme": aucun écart et aucun négatif, "ecarts": [{lot_id, magasin_id, journal,
   solde}], "negatifs": n, "lots": nombre de soldes}`.

Droit `ACHATS`. Il n'entre **ni** dans les 38, **ni** dans la note, **ni** dans l'export ; seul
l'indicateur « Soldes et journal » de l'écran l'affiche. La table `solde` a en outre
`CHECK (quantite >= -0.0005)` (`ck_solde_positif`, `modeles.py:479`). C12 vérifie le même invariant
côté moteur (voir C12).

---

## 3. Les 38 contrôles

Conventions : « mvts » = mouvements du journal traduits pour le moteur (`depot._journal`,
`depot.py:601-670`) — quantité positive, signe porté par le type ; un transfert = une seule ligne
source → destination ; type moteur : `STOCK_INITIAL`, `ENTREE_RECEPTION`, `SORTIE_PROD`,
`RETOUR_PRODUCTION`, `RETOUR_FOURNISSEUR`, `AJUSTEMENT_INVENTAIRE`, `TRANSFERT_MAGASIN`.
`POUSSIERE` = 1e-3 kg (`moteur.py:732`).

### C01 — Recette dont un rôle ne fait pas 100 %

| | |
|---|---|
| Libellé exact | « Recette dont un rôle ne fait pas 100 % » |
| Gravité | bloquant |
| Domaine | Qualités & recettes |
| Code | `controles.py:244-260` ; règle `moteur.controle_recettes`, `moteur.py:424-459` |
| Règle | Pour chaque qualité, pour chaque rôle dont le **poids au m² est non nul** (`qualite.poids[role]`) : somme des `pourcentage` des lignes de recette de la qualité dont l'article a ce `role_bom`. Écart si `|somme − 100| > TOLERANCE_RECETTE` (0,01 point ; 1e-6 en mode classeur). Une qualité est fautive si au moins un rôle est en écart. Un rôle pesé sans aucun fil donne somme 0 → écart. |
| Données | `donnees.qualites` (poids par rôle), `donnees.recettes`, articles (rôle) |
| Détail | `qualite` (code qualité) ; `roles` = « Rôle (somme %) » séparés par « , » (format `:.4g`) |
| Quoi faire | « La direction ouvre la qualité (Qualités & recettes › Recette) et corrige les pourcentages du rôle signalé jusqu'à 100 % (les achats, qui la lisent seulement, le lui signalent) : tant que ce n'est pas fait, le besoin en fil de cette qualité est faux, et le plan d'achat avec lui. » |
| Lien | `/qualites` |
| Garanti | Non (l'enregistrement d'une recette fausse est refusé, `referentiels.py`, même tolérance) |
| Historique | `ad52be7` ; texte révisé `f85dabd` |
| Ailleurs | Même fonction : `production.py:98-111` (alertes « recette incomplète » à la proposition d'ordre), `production_plan.py:111`, `referentiels.py:809-816` ; vérificateur `verificateur.py:130-139` |

### C02 — Sortie vers les machines sans ordre (n° OF)

| | |
|---|---|
| Libellé | « Sortie vers les machines sans ordre (n° OF) » |
| Gravité | avertissement |
| Domaine | Atelier / sorties |
| Code | `controles.py:262-271` |
| Règle | mvts de type `SORTIE_PROD` sans `numero_of` (numéro du bon de sortie lié par `mouvement.ordre_id`, `depot.py:655`). Contre-passations comprises (elles recopient `ordre_id`, `services/stock.py:260`). |
| Données | `donnees.mouvements` (à la date) |
| Détail | `date`, `reference` ; 200 premières |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/sorties` |
| Garanti | Non déclaré ; en pratique une sortie ne s'écrit que par un bon validé qui porte l'ordre |
| Historique | `ad52be7` |

### C03 — Retour sans motif, ou avec le motif d'une autre famille

| | |
|---|---|
| Libellé | « Retour sans motif, ou avec le motif d'une autre famille » |
| Gravité | avertissement |
| Domaine | Opérations de stock |
| Code | `controles.py:222-226` (`MOTIFS_PERMIS`), `:273-293` |
| Règle | mvts `RETOUR_PRODUCTION` dont `motif_retour ∉ {R1, R2, R4}` ; mvts `RETOUR_FOURNISSEUR` dont `motif_retour ∉ {R3, R5, R6}`. Le code motif vient de `depot._code_motif` (`depot.py:226-233`) : texte commençant par « R » + chiffre → ses 2 premiers caractères, sinon `CODES_MOTIF[libellé]` (`api/operations.py:49-53`) : Reliquat de fin d'ordre R1, Changement de série / arrêt machine R2, Erreur de prélèvement R4, Non-conformité qualité R3, Excédent de réception R5, Bobines endommagées R6, Refus après quarantaine R3 ; autre → « ». Un retour des machines marqué R3 se lit comme un retour fournisseur → signalé. |
| Données | `donnees.mouvements` |
| Détail | `date`, `reference`, `type` (libellé classeur du type, ex. « 🔄 Retour Production »), `motif` (code ou « — ») ; 200 premières |
| Quoi faire | « Ouvrir le retour et vérifier son motif : un retour des machines porte R1, R2 ou R4, un retour au fournisseur R3, R5 ou R6. S'il manque, annuler le retour (contre-passation) et le ressaisir avec son motif. » |
| Lien | `/operations` |
| Garanti | Non (motif obligatoire à la saisie, `operations.py`) |
| Historique | `ad52be7` ; familles `af3924a` ; le défaut « motif[:2] » signalé par `docs/conformite/2-regles-calculs-api.md:23,178` est corrigé (`CODES_MOTIF`) |

### C04 — Mouvement de stock sans auteur

| | |
|---|---|
| Libellé | « Mouvement de stock sans auteur » |
| Gravité | avertissement |
| Domaine | Traçabilité |
| Code | `controles.py:295-307` |
| Règle | mvts dont `utilisateur` (= `mouvement.auteur`) est vide |
| Données | `donnees.mouvements` (à la date) |
| Détail | `date`, `reference` ; 200 premières |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/stock?onglet=mouvements` |
| Garanti | Non déclaré ; toute écriture vient d'un compte connecté |
| Historique | `ad52be7` |

### C05 — Matière sans fournisseur

| | |
|---|---|
| Libellé | « Matière sans fournisseur » |
| Gravité | bloquant |
| Domaine | Référentiel matières |
| Code | `controles.py:309-319` |
| Règle | Articles (actifs **et inactifs**) dont `fournisseur` est vide (`article.fournisseur_id` NULL) |
| Données | `donnees.articles` |
| Détail | `reference` ; 200 premières |
| Quoi faire | « Ouvrir la matière (Matières, classification, fournisseurs) et lui donner son fournisseur — ou la désactiver si elle ne s'achète plus. Sans fournisseur, le plan d'achat ne sait pas à qui la commander. » |
| Lien | `/catalogue` |
| Garanti | Non (`fournisseur_id` facultatif) |
| Historique | `ad52be7` |

### C06 — Commande non livrée à sa date prévue

| | |
|---|---|
| Libellé | Mode corrigé : « Commande non livrée à sa date prévue (ou 60 jours après la commande) » ; mode classeur : « BC non livré depuis plus de 60 jours » |
| Gravité | avertissement |
| Domaine | Achats |
| Code | `controles.py:321-365` |
| Règle (corrigée) | Pour chaque commande avec `date_bc` (= `date_commande`) : exclue si brouillon non parti (`pas_partie` : statut moteur « Brouillon » — un bon `a_approuver` **sans numéro** ; un bon numéroté repassé en approbation reste « Envoyée/Confirmée », `depot.py:34-40`) ; échéance = `arrivee_attendue` (ETA, sinon date de livraison prévue), à défaut `date_bc + 60 j` ; en retard si `date_ref > échéance + toler_retard_jours` **et** au moins une ligne a `reste_a_livrer > 0` (`modele.py:409-425` : 0 si bon Soldé/Annulé, 0 si reste ≤ commandé × `toler_in_full`). |
| Règle (classeur) | échéance = date_bc + 60 j, sans tolérance ; en retard si Σ reçu < Σ commandé |
| Réglages | `toler_retard_jours`, `toler_in_full` |
| Données | `donnees.commandes` (à la date : reçu recalculé, bon soldé après la date rouvert) |
| Détail | `numero`, `fournisseur`, `date_bc`, `jours` (jours depuis la commande), `retard_jours` (jours depuis l'échéance, sans retirer la tolérance) ; trié par échéance croissante ; 200 premières |
| Quoi faire | « Relancer le fournisseur et noter la nouvelle date d'arrivée (ETA) dans le suivi d'expédition de la commande. S'il ne livrera pas le reste, solder la commande : elle ne comptera plus dans le stock projeté. » |
| Lien | `/commandes` |
| Historique | `ad52be7` (60 j fixes du classeur) ; date promise puis ETA + tolérance + brouillons `bcb14b5` |

### C07 — Matière jamais utilisée (ni recette, ni mouvement)

| | |
|---|---|
| Libellé | « Matière jamais utilisée (ni recette, ni mouvement) » |
| Gravité | information |
| Domaine | Référentiel |
| Code | `controles.py:367-378` |
| Règle | Références du catalogue (actives et inactives) absentes de toute ligne de recette **et** de tout mvt (à la date) |
| Détail | `reference` ; tri alphabétique ; non tronqué |
| Quoi faire | « Si la matière ne sert plus, la désactiver dans sa fiche ; si elle doit servir, l'ajouter à la recette d'une qualité. Pour information seulement. » |
| Lien | `/catalogue` |
| Historique | `ad52be7` |

### C08 — Écart de pesée supérieur à la tolérance

| | |
|---|---|
| Libellé | f« Écart de pesée supérieur à {toler_ecart_pesee:.0%} » → « Écart de pesée supérieur à 2% » |
| Gravité | avertissement |
| Domaine | Réceptions |
| Code | `controles.py:380-406` ; `modele.LigneReception.quantite_attendue/ecart/ecart_relatif`, `modele.py:461-498` |
| Règle | Réceptions non annulées (`depot.py:378-379`). Ligne d'un brouillon **sans pesée** → ignorée (« ce qui n'est pas encore passé sur la bascule n'est pas un écart de 100 %, c'est une ligne qui attend »). Attendu = quantité du BL si saisie ; sinon, si pesé < `quantite_attendue de la ligne` (= reste à livrer figé) × (1 − `toler_ecart_pesee`) → attendu 0 (livraison partielle, pas d'écart) ; sinon le reste à livrer. `ecart_relatif = (pesé − attendu) / attendu` (None si attendu 0). Anomalie si `|ecart_relatif| > toler_ecart_pesee`. |
| Réglages | `toler_ecart_pesee` (seuil **et** tolérance de livraison partielle, `depot.py:376,406`) |
| Détail | `reception` (numéro, ou « REC-brouillon-{id} »), `reference`, `attendu`, `pesee`, `ecart` (**fraction**, ex. 0,034) ; 200 premières |
| Quoi faire | « Comparer la pesée au bon de livraison avec le fournisseur. Écart confirmé : le réclamer (avoir ou complément). Pesée fausse : corriger le stock par un ajustement motivé. » |
| Lien | `/receptions?onglet=pesees` |
| Historique | `ad52be7` (le saut des lignes non pesées y est déjà) |

### C09 — Prix négatif au catalogue

| | |
|---|---|
| Libellé | « Prix négatif au catalogue » |
| Gravité | bloquant |
| Domaine | Référentiel matières |
| Code | `controles.py:409-418` |
| Règle | Articles avec `prix_unite < 0` (prix saisi, dans son unité kg ou ml) |
| Détail | `reference`, `prix` ; non tronqué |
| Quoi faire | « Corriger le prix d'achat dans la fiche matière. » |
| Lien | `/catalogue` |
| Garanti | **Oui** — `CHECK (prix >= 0)` |
| Historique | `ad52be7` ; garanti `96db9ea` |

### C10 — Délai fournisseur nul ou négatif

| | |
|---|---|
| Libellé | « Délai fournisseur nul ou négatif » |
| Gravité | avertissement |
| Domaine | Référentiel fournisseurs |
| Code | `controles.py:419-427` |
| Règle | Fournisseurs avec `delai_jours <= 0` |
| Détail | `fournisseur`, `delai` ; non tronqué |
| Quoi faire | « Corriger le délai (en jours, au moins 1) dans la fiche fournisseur. » |
| Lien | `/catalogue?onglet=fournisseurs` |
| Garanti | **Oui** — `CHECK (delai_jours > 0)` |
| Historique | `ad52be7` ; garanti `96db9ea` |

### C11 — Cours de change à zéro

| | |
|---|---|
| Libellé | « Cours de change à zéro » |
| Gravité | bloquant |
| Domaine | Devises |
| Code | `controles.py:428-441` |
| Règle | `parametres.taux_eur_mad <= 0` → ligne « EUR → MAD » ; `taux_usd_mad <= 0` → « USD → MAD ». Ces taux viennent de la table `devise` (EUR, USD) ou, à défaut, des défauts 11,0 / 9,5 (`parametres.py:186-188`). Les autres devises ne sont pas regardées. |
| Détail | `taux` (« EUR → MAD »), `valeur` ; non tronqué |
| Quoi faire | « Saisir le cours de la devise dans Réglages › Devises (ouvert à la direction et aux achats). » |
| Lien | `/reglages?onglet=devises` |
| Garanti | **Oui** — `CHECK (taux > 0)` ; `PUT /devises` exige 0 < taux ≤ 10 000 |
| Historique | `ad52be7` ; texte et garanti `96db9ea` |

### C12 — Stock tenu (soldes des lots) différent du journal des mouvements

| | |
|---|---|
| Libellé | Avec soldes : « Stock tenu (soldes des lots) différent du journal des mouvements » ; sans soldes (classeur) : « Stock par magasin différent du stock net des mouvements » |
| Gravité | bloquant |
| Domaine | Intégrité du stock |
| Code | `controles.py:443-491` ; soldes `depot._soldes`, `depot.py:550-559` |
| Règle | Sur `complet` (toutes les données). Pour chaque mvt : transfert → +q à la destination, −q à la source ; autre → `quantite_signee` au magasin (destination, sinon source). Cumul par clé (référence, n° de lot, code magasin). Anomalie pour chaque clé de l'union {journal} ∪ {soldes} si `|solde − journal| > POUSSIERE`. Repli (si `complet.soldes` est None — jamais en service) : par référence, `|Σ par_magasin − stock_net| > 0,01`. |
| Données | `complet.mouvements`, `complet.soldes` (table `solde` × `lot`), `lignes_stock` (repli) |
| Détail | `reference`, `lot`, `magasin`, `stock` (solde tenu), `attendu` (journal) ; repli : `reference`, `somme_magasins`, `stock_net` ; 200 premières, clés triées |
| Quoi faire | « Bloquant : le stock tenu ne retombe plus sur le journal des mouvements. Ne plus rien saisir sur ces matières et prévenir la personne qui entretient le serveur : une écriture a contourné le chemin normal. » |
| Lien | `/stock?onglet=mouvements` |
| Garanti | Non ; la somme des soldes entre dans la signature du cache (`depot.py:682-684`) pour qu'un solde touché à la main se voie |
| Historique | `ad52be7` (règle classeur) ; soldes lot × magasin `5ca0960` ; sur toutes les données `61027e4` |

### C13 — Stock projeté négatif pendant le délai d'approvisionnement

| | |
|---|---|
| Libellé | « Stock projeté négatif pendant le délai d'approvisionnement » |
| Gravité | avertissement |
| Domaine | Prévision / achats |
| Code | `controles.py:493-511` |
| Règle | Lignes de stock (toutes, inactives comprises) avec `stock_projete < −POUSSIERE`. `stock_projete = stock_net − quarantaine + stock en machine + commandes attendues dans le délai − demande pendant le délai` (`moteur.py:1157`). |
| Détail | `reference`, `stock_net`, `stock_projete`, `manque` (= −stock_projete) ; trié par manque décroissant ; 200 premières |
| Quoi faire | « Commander tout de suite (Plan d'achat), ou faire avancer une livraison déjà commandée : la matière manquera avant que la commande n'arrive. » |
| Lien | `/plan-achat` |
| Historique | `ad52be7` (Audit C05) |

### C14 — Mouvement de stock à une date future

| | |
|---|---|
| Libellé | « Mouvement de stock à une date future » |
| Gravité | avertissement |
| Domaine | Intégrité du journal |
| Code | `controles.py:513-522` |
| Règle | Sur `complet` : mvts dont `date > aujourdhui` (= max(date de référence, date du jour)) |
| Détail | `date`, `reference` ; 200 premières |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/stock?onglet=mouvements` |
| Garanti | Non déclaré ; `securite.date_permise` refuse toute date future, avant 2000 ou dans la période close |
| Historique | `ad52be7` (Audit C06) ; sur toutes les données `61027e4` |

### C15 — Matière d'une recette sans prix d'achat

| | |
|---|---|
| Libellé | « Matière d'une recette sans prix d'achat » |
| Gravité | avertissement |
| Domaine | Coûts |
| Code | `controles.py:524-539` |
| Règle | Lignes de recette avec `pourcentage > 0` dont l'article existe et a `prix_kg` nul (prix au kg, ou prix au mètre ÷ densité ; 0 si densité absente) — toutes qualités, actives ou non |
| Détail | `qualite`, `reference` ; 200 premières |
| Quoi faire | « Saisir le prix d'achat dans la fiche matière : sans lui, le coût au m² de la qualité et le budget d'achat sont sous-évalués. » |
| Lien | `/catalogue` |
| Historique | `ad52be7` (Audit C14) ; `prix_unite` (`45c3d2c`) puis `prix_kg` (`d2e1e39`) |

### C16 — Intégrité référentielle des mouvements

| | |
|---|---|
| Libellé | « Intégrité référentielle des mouvements » |
| Gravité | bloquant |
| Domaine | Intégrité |
| Code | `controles.py:541-559` |
| Règle | mvts dont la référence n'est pas au catalogue ; + mvts dont le fournisseur (celui du lot) est renseigné mais inconnu |
| Détail | `reference`, `date` — ou `fournisseur`, `date` ; 200 premières |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/stock?onglet=mouvements` |
| Garanti | **Oui** — clés étrangères |
| Historique | `ad52be7` (« Nouveau ») ; garanti `96db9ea` |

### C17 — Matière en alerte sans second fournisseur

| | |
|---|---|
| Libellé | « Matière en alerte sans second fournisseur » |
| Gravité | information |
| Domaine | Pilotage / sourcing |
| Code | `controles.py:1058-1076` ; sourcing `moteur.py:1412-1420` |
| Règle | Lignes de stock dont `sourcing == "🔴 MONO-SOURCE"` (la matière a un groupe d'équivalence et ce groupe a ≤ 1 fournisseur distinct) **et** statut ∈ {RUPTURE, CRITIQUE, URGENT, ATTENTION} (`STATUTS_EN_ALERTE`). Une matière sans groupe d'équivalence a le sourcing « ❓ Hors catalogue » et n'est jamais signalée. |
| Détail | `reference`, `fournisseur`, `montant_a_commander_mad` ; trié par montant décroissant ; 200 premières |
| Quoi faire | « Chercher un second fournisseur pour cette matière, ou un fil équivalent : elle est en alerte et ne dépend que d'un seul. » |
| Lien | `/catalogue` |
| Historique | `ad52be7` (« remontés du Cockpit ») |

### C18 — Stock dormant depuis plus de N jours

| | |
|---|---|
| Libellé | f« Stock dormant depuis plus de {seuil_dormant:.0f} jours » → « … plus de 180 jours » |
| Gravité | information |
| Domaine | Pilotage / stock |
| Code | `controles.py:1077-1095` ; dormance `moteur.py:1422-1444` |
| Règle (corrigée) | `dormant = stock_net > POUSSIERE` et (aucune date ou `jours_sans_mouvement > seuil_dormant`), où le dernier mouvement = max(dernière sortie réelle, dernière entrée réelle — stock initial, réception, retour des machines), annulations et contre-passations exclues |
| Règle (classeur) | sur la dernière sortie seule, stock projeté > 0 |
| Réglages | `seuil_dormant` |
| Détail | `reference`, `stock` (stock net ; projeté en classeur), `jours_sans_mouvement` ; 200 premières |
| Quoi faire | « Voir si la matière peut servir une autre qualité, se rendre au fournisseur ou se vendre ; sinon, la déclasser. Pour information seulement. » |
| Lien | `/stock` |
| Historique | `ad52be7` ; règle des dormants corrigée (audits 2-A M1, 2-F G5, 2-G M3), `61027e4` |

### C19 — Fournisseur qui facture en plusieurs devises

| | |
|---|---|
| Libellé | « Fournisseur qui facture en plusieurs devises » |
| Gravité | information |
| Domaine | Référentiel / achats |
| Code | `controles.py:561-585` ; `moteur.devises_pratiquees`, `moteur.py:2934-2945` |
| Règle | Par fournisseur, devises des prix des articles qui le nomment (actifs et inactifs) ; signalé si > 1 devise. « La devise du prix fait foi partout ; celle de la fiche fournisseur ne sert qu'à pré-remplir. » Exemple du code : LOMAT, colle en euros, chaîne en dollars. |
| Détail | `fournisseur`, `devises` (« EUR (n matière(s)) · USD (m matière(s)) »), `devise_par_defaut` (celle de la fiche) ; trié par nom ; non tronqué |
| Quoi faire | « Normal si le fournisseur facture vraiment en deux monnaies : un bon de commande part par devise. Sinon, corriger la devise de la matière dans sa fiche. » |
| Lien | `/catalogue` |
| Historique | `ad52be7` |

### C20 — Stock négatif sur une matière sans consommation

| | |
|---|---|
| Libellé | « Stock négatif sur une matière sans consommation » |
| Gravité | bloquant |
| Domaine | Stock |
| Code | `controles.py:603-617` |
| Règle | Lignes de stock avec `stock_net < 0` et `conso_mensuelle == 0` (le moteur ramène à 0 tout stock net de valeur absolue < POUSSIERE, `moteur.py:1008-1018`) |
| Détail | `reference`, `stock_net` ; non tronqué |
| Quoi faire | « Faire compter la matière (Inventaire) et corriger le stock par un ajustement motivé. » |
| Lien | `/inventaire` |
| Garanti | Non déclaré ; en pratique `ck_solde_positif` (solde ≥ −0,0005) l'empêche tant que soldes = journal |
| Historique | `ad52be7` (« Nouveau ») |

### C21 — Prix au catalogue sans devise

| | |
|---|---|
| Libellé | « Prix au catalogue sans devise » |
| Gravité | bloquant |
| Code | `controles.py:587-601` |
| Règle | Articles avec `prix_unite` non nul et `devise` vide |
| Détail | `reference`, `prix`, `fournisseur` ; non tronqué |
| Quoi faire | « Choisir la devise du prix dans la fiche matière. » |
| Lien | `/catalogue` |
| Garanti | **Oui** — `article.devise` NOT NULL, clé étrangère |
| Historique | `ad52be7` ; garanti `96db9ea` |

### C22 — Étage monté plus large que la laize du métier

| | |
|---|---|
| Libellé | « Étage monté plus large que la laize du métier » |
| Gravité | avertissement |
| Domaine | Métiers à tisser |
| Code | `controles.py:619-648` |
| Règle | Métiers **actifs** à laize > 0 ; par étage : `largeur = Σ (mètres × pourcentage / 100)` des fils de l'étage (deux fils à 60/40 % sur les mêmes mètres les occupent une fois) ; anomalie si `largeur > laize + 1e-9` |
| Détail | `metier`, `etage`, `laize`, `metres_montes`, `fils` (nombre de fils) ; non tronqué |
| Quoi faire | « Ouvrir le métier (Métiers à tisser) et ramener les mètres montés à cet étage à la laize du métier. » |
| Lien | `/metiers` |
| Garanti | Non (le montage est aussi refusé à la saisie) |
| Historique | `ad52be7` ; prorata `202d1a0` |

### C23 — Fil monté sans poids de bobine au catalogue

| | |
|---|---|
| Libellé | « Fil monté sans poids de bobine au catalogue » |
| Gravité | bloquant |
| Domaine | Métiers / stock en machine |
| Code | `controles.py:684-697` ; `moteur.fils_en_machine`, `moteur.py:678-708` |
| Règle | Fils montés sur un métier **actif** dont `poids_bobine` est nul ; ce poids = celui pesé au lot (dernier lot sorti vers les machines, sinon dernier reçu — `depot.poids_bobine_mesures`) sinon celui du catalogue |
| Détail | `metier`, `etage`, `reference`, `metres` ; non tronqué |
| Quoi faire | « Saisir le poids d'une bobine (kg / bobine) dans la fiche matière : sans lui, le fil monté pèse zéro et manque au stock. » |
| Lien | `/catalogue` |
| Historique | `ad52be7` |

### C24 — Fil monté à un étage que le métier n'a pas

| | |
|---|---|
| Libellé | « Fil monté à un étage que le métier n'a pas » |
| Gravité | avertissement |
| Code | `controles.py:650-664` |
| Règle | Tous les métiers (actifs **et** inactifs) : fils dont `etage > etages` du métier |
| Détail | `metier`, `etage`, `etages`, `reference` ; non tronqué |
| Quoi faire | « Retirer le fil de cet étage, ou augmenter le nombre d'étages du métier. » |
| Lien | `/metiers` |
| Garanti | Non (refusé à la saisie ; `CHECK etages BETWEEN 1 AND 40`) |
| Historique | `ad52be7` |

### C25 — Fil monté sans sortie de magasin enregistrée

| | |
|---|---|
| Libellé | « Fil monté sans sortie de magasin enregistrée (le magasin le compte encore) » |
| Gravité | avertissement |
| Code | `controles.py:666-682` |
| Règle | Fils en machine (métiers actifs) de poids non nul dont la référence n'apparaît dans **aucun** mvt `SORTIE_PROD` (à la date, n'importe quand, annulées comprises) |
| Détail | `metier`, `etage`, `reference`, `poids` ; non tronqué |
| Quoi faire | « Enregistrer la sortie vers les machines de ce fil (Sorties vers les machines) : sans elle, le magasin le compte encore en stock alors qu'il est monté. » |
| Lien | `/sorties` |
| Historique | `ad52be7` (« risque de double compte ») ; reformulé `202d1a0` ; cité par le Guide `Guide.tsx:138,282` |

### C26 — Sortie de stock sans numéro de lot

| | |
|---|---|
| Libellé | « Sortie de stock sans numéro de lot » |
| Gravité | avertissement |
| Domaine | Traçabilité |
| Code | `controles.py:699-720` |
| Règle | mvts `SORTIE_PROD` ou `RETOUR_FOURNISSEUR` dont `lot_fournisseur` (numéro du lot) est vide |
| Détail | `date`, `reference`, `quantite`, `numero_of`, `utilisateur` ; **200 dernières** |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/stock?onglet=mouvements` |
| Garanti | Non déclaré ; `mouvement.lot_id` NOT NULL — seul un lot au numéro vide le ferait sonner |
| Historique | `ad52be7` |

### C27 — Lot dont il est sorti plus qu'il n'est entré

| | |
|---|---|
| Libellé | « Lot dont il est sorti plus qu'il n'est entré » |
| Gravité | bloquant |
| Domaine | Intégrité du stock |
| Code | `controles.py:722-741` ; `moteur.stock_par_lot`, `moteur.py:3202-3271` ; `LigneLot.negatif` `:3196-3199` |
| Règle | Sur `complet`. Par (référence, lot — « (sans lot) » si vide), tous magasins confondus : `stock = Σ quantite_signee` ; anomalie si `stock < −1e-9`. `entrees`/`sorties` affichés : annulations et leurs originaux exclus, transferts exclus, retours des machines retranchés des sorties. |
| Détail | `reference`, `lot`, `stock`, `entrees`, `sorties` ; non tronqué |
| Quoi faire | « Bloquant : ouvrir le lot (son numéro mène à Stock › Lots, lots épuisés compris) et cliquer « Suivre » pour trouver la sortie de trop ; l'annuler (contre-passation), ou enregistrer l'entrée oubliée. » |
| Lien | `/stock?onglet=lots` |
| Garanti | Non déclaré ; `ck_solde_positif` + écriture sous verrou |
| Historique | `ad52be7` ; lien Lots `f85dabd`/`96db9ea` ; sur toutes les données `61027e4` |

### C28 — Dossier d'importation arrivé depuis plus de 30 jours et sans frais

| | |
|---|---|
| Libellé | « Dossier d'importation arrivé depuis plus de 30 jours et sans frais » |
| Gravité | avertissement |
| Domaine | Importations |
| Code | `controles.py:757-780` |
| Règle | Dossiers **ouverts**, avec au moins une marchandise, **aucun frais non récupérable** (seule la TVA ne compte pas comme frais), une date d'arrivée, et `(date_ref − arrivée) > 30` jours (30 en dur) |
| Détail | `dossier`, `arrivee`, `marchandises` (nombre de lignes), `jours` (depuis l'arrivée) ; non tronqué |
| Quoi faire | « Saisir les frais du dossier (droits, fret, transit…) dans Importations : sans eux, le coût de revient n'est que le prix de la facture. » |
| Lien | `/importations` |
| Historique | `ad52be7` |

### C29 — TVA d'importation éloignée de la valeur attendue

| | |
|---|---|
| Libellé | f« TVA d'importation éloignée de {taux_tva_import×100:g} % de la valeur en douane » → « … éloignée de 20 % de la valeur en douane » |
| Gravité | avertissement |
| Domaine | Importations |
| Code | `controles.py:799-828` ; `moteur.tva_attendue` `moteur.py:3580-3603`, `ecart_tva_tolere` `:3606-3608`, `TOLERANCE_TVA_IMPORT = 0.05` `:3577` |
| Règle | Par dossier : `tva` = Σ des frais de poste **« TVA »** seulement (une autre taxe récupérable, ex. TVA du transitaire, n'entre pas) ; ignoré si 0. `attendue = taux_tva_import × (valeur en douane + droits DD + TPI)`, valeur en douane = Σ marchandises en MAD (cours de la ligne, sinon cours du jour ; ligne en MAD sans cours) + frais FRET + ASSUR ; TPI = Σ frais « TPI » si saisis, sinon valeur en douane × `taux_tpi_import`. Dossier sans marchandise : attendue 0 → ignoré. Anomalie si `|tva − attendue| > 5 % × |attendue|`. |
| Réglages | `taux_tva_import`, `taux_tpi_import` ; tolérance 5 % en dur |
| Détail | `dossier`, `tva_saisie`, `tva_attendue`, `ecart_mad` (saisie − attendue) ; non tronqué |
| Quoi faire | « Comparer la TVA saisie dans les frais du dossier à la quittance de la douane ; corriger le frais, ou la valeur en douane des marchandises. » |
| Lien | `/importations` |
| Historique | `ad52be7` (20 % et 5 % en dur) ; taux réglé `08c6df7` ; CAF + TPI `6f3a340` |
| Ailleurs | Même calcul sur la fiche du dossier (`importations.py:292-300` : `taux_tva_import`, `tva_attendue_mad`, `tva_ecart_tolere_mad`) |

### C30 — Poids de bobine reçu éloigné du catalogue

| | |
|---|---|
| Libellé | f« Poids de bobine reçu éloigné du catalogue de plus de {toler_poids_bobine:.0%} » → « … de plus de 5% » |
| Gravité | information |
| Domaine | Réceptions / référentiel |
| Code | `controles.py:965-990` ; `moteur.evolution_bobines` `moteur.py:3103-3168` |
| Règle | Hors mode classeur. Par référence : série des poids moyens de bobine (pesé ÷ nombre de bobines) des lignes **non refusées** de réceptions **validées**, triée par date ; anomalie si l'écart de la **dernière** mesure au poids catalogue `(dernier − catalogue)/catalogue` dépasse `toler_poids_bobine` en valeur absolue (pas d'écart si l'un des deux est nul) |
| Réglages | `toler_poids_bobine` |
| Détail | `reference`, `fournisseur`, `catalogue`, `constate`, `ecart` (**fraction**), `reception` (dernière) ; trié par |écart| décroissant ; 200 premières |
| Quoi faire | « Vérifier le poids de bobine avec le fournisseur ; si le nouveau poids est le bon, le reporter dans la fiche matière (kg / bobine). » |
| Lien | `/receptions?onglet=bobines` |
| Historique | `ad52be7` |

### C31 — Ordre de fabrication servi à plusieurs dates

| | |
|---|---|
| Libellé | « Ordre de fabrication servi à plusieurs dates » |
| Gravité | avertissement |
| Domaine | Atelier |
| Code | `controles.py:902-927` |
| Règle | mvts `SORTIE_PROD` avec `numero_of` et quantité moteur > 0 (les contre-passations, de quantité négative, sont exclues) ; par n° d'OF, ensemble des dates ; anomalie si > 1 date |
| Détail | `numero_of`, `dates` (« JJ/MM/AAAA · … »), `jours` (nombre de dates) ; trié par numéro ; 200 premiers |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/sorties` |
| Garanti | Non déclaré ; un bon = une date |
| Historique | `ad52be7` |

### C32 — Ordre de fabrication daté avant un ordre de numéro inférieur

| | |
|---|---|
| Libellé | « Ordre de fabrication daté avant un ordre de numéro inférieur » |
| Gravité | information |
| Code | `controles.py:929-963` |
| Règle | Numéros de forme « SERIE-AAAA-NNNN » (3 parties, les 2 dernières numériques) → rang (année, n°) ; autres numéros ignorés. Triés par (rang, première date). On garde la date la plus tardive vue parmi les numéros inférieurs ; un ordre dont la première date est **antérieure** à elle est signalé. |
| Détail | `numero_of`, `date`, `apres` (numéro inférieur daté plus tard), `date_apres` ; 200 premiers |
| Quoi faire | `_HORS_SAISIE` |
| Lien | `/sorties` |
| Garanti | Non déclaré ; numéro donné à la validation, dans l'ordre |
| Historique | `ad52be7` |

### C33 — Stock minimum du catalogue supérieur à N mois de consommation

| | |
|---|---|
| Libellé | f« Stock minimum du catalogue supérieur à {plafond_stock_min_mois:g} mois de consommation » → « … supérieur à 3 mois … » |
| Gravité | information |
| Domaine | Référentiel / prévision |
| Code | `controles.py:992-1021` ; plafonnement `moteur.py:1238-1260` |
| Règle | Hors classeur, si `plafond > 0` : lignes avec `conso_mensuelle > 0`, `conso_horizon > 0` (consommation mensuelle moyenne sur délai + couverture de commande + 30 j) et `stock_min_plafonne < stock_min − POUSSIERE` (= le stock minimum du catalogue a été plafonné à `plafond × conso_horizon`) |
| Réglages | `plafond_stock_min_mois` |
| Détail | `reference`, `stock_min_catalogue`, `conso_mensuelle` (= conso de l'horizon, 1 déc.), `mois` (stock_min ÷ conso_horizon), `retenu` (plafonné, arrondi) ; trié par mois décroissant ; 200 premières |
| Quoi faire | « Baisser le stock minimum dans la fiche matière : il immobilise plus de mois de consommation que le plafond réglé (le plan d'achat le plafonne déjà). » |
| Lien | `/catalogue` |
| Historique | `ad52be7` ; consommation de l'horizon `30b31c3` |

### C34 — Dossier d'importation avec des frais mais sans marchandise

| | |
|---|---|
| Libellé | « Dossier d'importation avec des frais mais sans marchandise » |
| Gravité | avertissement |
| Code | `controles.py:782-797` |
| Règle | Dossiers (ouverts ou clos) ayant au moins un frais et aucune ligne de marchandise : leurs frais ne se répartissent sur rien |
| Détail | `dossier`, `frais` (Σ de tous les frais, TVA comprise) ; non tronqué |
| Quoi faire | « Rattacher les marchandises au dossier (Importations › À rattacher), ou retirer les frais saisis par erreur. » |
| Lien | `/importations` |
| Historique | `ad52be7` |

### C35 — Frais d'un dossier (ou d'une marchandise) au-delà du seuil

| | |
|---|---|
| Libellé | f« Dossier d'importation (ou une de ses marchandises) dont les frais dépassent {seuil_surcout_import×100:g} % de la marchandise » → « … dépassent 100 % de la marchandise » |
| Gravité | avertissement |
| Domaine | Importations / coût de revient |
| Code | `controles.py:830-872` ; `moteur.revient_dossier` `:3624-3686`, `lignes_aberrantes` `:3689-3694` |
| Règle | Par dossier, frais non récupérables répartis (`revient_dossier` : frais affectés à une ligne → à elle ; parts figées ; sinon au prorata de la valeur ou des kilos selon la clé du poste). `marchandise = Σ valeur_mad`, `frais = Σ charges_mad`. Si `marchandise > 0` et `frais > marchandise × seuil` → une ligne « (tout le dossier) ». Sinon, chaque marchandise avec `charges_mad > 0,005` et (`valeur_mad ≤ 0` ou `charges_mad > valeur_mad × seuil`). |
| Réglages | `seuil_surcout_import` |
| Détail | `dossier`, `reference` (« (tout le dossier) » ou la matière), `marchandise_mad`, `frais_mad`, `surcout_pct` (**pour cent**, 1 déc. ; None si valeur ≤ 0) ; non tronqué |
| Quoi faire | « Reprendre les frais du dossier sur leurs pièces (quittance, facture du transitaire) : un zéro de trop, ou les frais d'un autre dossier. Tant qu'ils restent, ils entrent dans le coût moyen du stock. » |
| Lien | `/importations` |
| Historique | **Créé `6f3a340`** (exemple : 836 000 MAD de frais sur 6 000 MAD de fil) ; par ligne `58f507c` (5 000 MAD sur 220) |
| Ailleurs | Même seuil sur la fiche du dossier, `importations.py:222-224` |

### C36 — Facture d'un dossier éloignée de la marchandise reçue

| | |
|---|---|
| Libellé | f« Facture d'un dossier d'importation éloignée de plus de {toler_facture_import×100:g} % de la marchandise reçue » → « … de plus de 2 % … » |
| Gravité | avertissement |
| Code | `controles.py:874-900` ; `moteur.ecart_facture` `:3703-3721` |
| Règle | Ignoré si le dossier n'a pas de montant de facture, pas de marchandise, ou une marchandise dans une autre devise que la facture. `recu = Σ valeur_devise` (pesée × prix, dans la devise) ; `ecart = facture − recu` ; `part = ecart / recu` (1,0 si recu = 0). Anomalie si `|ecart| > 0,005` et `|part| > toler_facture_import`. La valorisation reste à la pesée × prix. |
| Réglages | `toler_facture_import` |
| Détail | `dossier`, `facture` (numéro), `facture_montant`, `recu`, `devise` (absente de COLONNES), `ecart` (**pour cent**, 1 déc.) ; non tronqué |
| Quoi faire | « Rapprocher la facture du bon de livraison et de la pesée : un manque de poids se réclame au fournisseur (avoir), une facture mal saisie se corrige sur sa réception, un camion pas encore rattaché rejoint le dossier. Le coût, lui, reste à la pesée × le prix. » |
| Lien | `/importations` |
| Historique | **Créé `58f507c`** (« Importations, second audit »), garde le code C36 |

### C37 — Lot sous zéro à une date passée

| | |
|---|---|
| Libellé | « Lot sous zéro à une date passée (écriture datée avant l'entrée de la matière) » |
| Gravité | bloquant |
| Domaine | Intégrité du stock / coût |
| Code | `controles.py:743-755` ; `stock_negatif_passe` `:1100-1125` |
| Règle | Sur `complet`. Par (référence, lot, magasin), flux comme C12, cumulés **par jour** (l'ordre dans la journée ne compte pas) ; on parcourt les jours dans l'ordre ; si le cumul du soir passe sous `−POUSSIERE` : premier jour fautif et creux (minimum). C27 ne regarde que le solde final : une sortie datée avant l'entrée de son lot passait inaperçue (le lot remonte à zéro le jour de l'entrée) et partait à coût nul. |
| Détail | `reference`, `lot`, `magasin`, `date` (premier jour sous zéro), `manque` (−creux) ; 200 premières |
| Quoi faire | « Bloquant : une écriture est datée avant l'entrée de son lot, ou a pris plus que ce que le lot portait ce jour-là — elle est partie à coût nul. Ouvrir le journal du lot, annuler l'écriture fautive (contre-passation) et la ressaisir à une date où la matière était là, ou sur un autre lot. » |
| Lien | `/stock?onglet=mouvements` |
| Garanti | Non ; la saisie refuse toute écriture qui ferait passer un lot sous zéro à sa date (AUDIT-2026-10-08.md:37) |
| Historique | **Créé sous le code C36 dans `61027e4`**, **renuméroté C37 dans `f216509`** |

### C38 — Prix du catalogue loin du dernier prix payé

| | |
|---|---|
| Libellé | f« Prix du catalogue à plus de {3:g} fois (ou moins d'un {3:g}e) du dernier prix payé » → « Prix du catalogue à plus de 3 fois (ou moins d'un 3e) du dernier prix payé » |
| Gravité | avertissement (par défaut — non précisée) |
| Domaine | Référentiel / prix |
| Code | `controles.py:186-188` (`RAPPORT_PRIX_ELOIGNE = 3.0`), `:1023-1056` |
| Règle | Hors classeur. Dernier prix payé par référence = ligne de l'historique de prix (lignes non refusées, pesées, à prix > 0 des réceptions **validées**, `depot.py:419-435`) avec `prix_achat > 0`, `date ≤ date_ref`, la plus récente (à égalité, la dernière lue). Pour chaque article **actif** à `prix_kg > 0` ayant un dernier prix : `catalogue = prix_kg × cours du jour(devise article)`, `payé = prix_achat × cours du jour(devise payée)`, `rapport = catalogue / payé` ; anomalie si `rapport > 3` ou `0 < rapport < 1/3`. |
| Détail | `reference`, `fournisseur` (du prix payé, sinon de la fiche), `prix_catalogue` (texte « 35,7 USD / kg (0,5 USD / ml) »), `prix_paye` (« x USD / kg »), `date`, `rapport` (3 déc.) ; trié par max(r, 1/r) décroissant ; 200 premières |
| Quoi faire | « Comparer le prix de la fiche matière au dernier achat (tous deux lus au kilo — un prix au mètre l'est par la densité ; unité du prix, densité, devise) et le corriger s'il est faux — ou confirmer le dernier prix payé avec le fournisseur. C'est au responsable du référentiel de trancher : le contrôle ne corrige rien. » |
| Lien | `/catalogue` |
| Historique | **Créé sous le code C36 dans `91448ce`**, **renuméroté C38 dans `93fd464`** ; passé au kilo `d2e1e39` |

---

## 4. Tableau récapitulatif

| Code | Libellé (court) | Gravité | Sur | Réglages lus | Lien | Garanti |
|---|---|---|---|---|---|---|
| C01 | Recette ≠ 100 % par rôle | bloquant | à la date | (TOLERANCE_RECETTE) | /qualites | |
| C02 | Sortie sans OF | avert. | à la date | | /sorties | (hors saisie) |
| C03 | Retour sans motif / mauvaise famille | avert. | à la date | | /operations | |
| C04 | Mouvement sans auteur | avert. | à la date | | /stock?onglet=mouvements | (hors saisie) |
| C05 | Matière sans fournisseur | bloquant | catalogue | | /catalogue | |
| C06 | Commande en retard | avert. | à la date | toler_retard_jours, toler_in_full | /commandes | |
| C07 | Matière jamais utilisée | info | à la date | | /catalogue | |
| C08 | Écart de pesée | avert. | à la date | toler_ecart_pesee | /receptions?onglet=pesees | |
| C09 | Prix négatif | bloquant | catalogue | | /catalogue | oui |
| C10 | Délai ≤ 0 | avert. | catalogue | | /catalogue?onglet=fournisseurs | oui |
| C11 | Cours EUR/USD ≤ 0 | bloquant | devises | (taux) | /reglages?onglet=devises | oui |
| C12 | Soldes ≠ journal | bloquant | complet | | /stock?onglet=mouvements | |
| C13 | Stock projeté négatif | avert. | à la date | (tous ceux du stock) | /plan-achat | |
| C14 | Mouvement futur | avert. | complet | | /stock?onglet=mouvements | (hors saisie) |
| C15 | Recette sans prix | avert. | catalogue | | /catalogue | |
| C16 | Intégrité référentielle | bloquant | à la date | | /stock?onglet=mouvements | oui |
| C17 | Alerte mono-source | info | à la date | (statut) | /catalogue | |
| C18 | Stock dormant | info | à la date | seuil_dormant | /stock | |
| C19 | Fournisseur multi-devises | info | catalogue | | /catalogue | |
| C20 | Stock négatif sans conso | bloquant | à la date | | /inventaire | |
| C21 | Prix sans devise | bloquant | catalogue | | /catalogue | oui |
| C22 | Étage > laize | avert. | métiers | | /metiers | |
| C23 | Fil monté sans poids de bobine | bloquant | métiers | | /catalogue | |
| C24 | Étage inexistant | avert. | métiers | | /metiers | |
| C25 | Fil monté jamais sorti | avert. | à la date | | /sorties | |
| C26 | Sortie sans lot | avert. | à la date | | /stock?onglet=mouvements | (hors saisie) |
| C27 | Lot négatif (solde final) | bloquant | complet | | /stock?onglet=lots | |
| C28 | Dossier > 30 j sans frais | avert. | dossiers | | /importations | |
| C29 | TVA d'import ≠ attendue | avert. | dossiers | taux_tva_import, taux_tpi_import | /importations | |
| C30 | Poids de bobine ≠ catalogue | info | à la date | toler_poids_bobine | /receptions?onglet=bobines | |
| C31 | OF à plusieurs dates | avert. | à la date | | /sorties | (hors saisie) |
| C32 | OF dans le désordre | info | à la date | | /sorties | (hors saisie) |
| C33 | Stock min > N mois | info | à la date | plafond_stock_min_mois | /catalogue | |
| C34 | Frais sans marchandise | avert. | dossiers | | /importations | |
| C35 | Frais aberrants | avert. | dossiers | seuil_surcout_import | /importations | |
| C36 | Facture ≠ reçu | avert. | dossiers | toler_facture_import | /importations | |
| C37 | Lot sous zéro dans le passé | bloquant | complet | | /stock?onglet=mouvements | |
| C38 | Prix catalogue ≠ dernier payé | avert. | à la date | (cours) | /catalogue | |

---

## 5. Exigences pour la réécriture (ce qu'il faut reproduire)

1. Un contrôle = code, libellé (éventuellement paramétré par la valeur du réglage), gravité, nombre
   d'anomalies **complet**, détail (lignes fautives, colonnes à libellé français), texte « quoi
   faire », lien de correction, mention « garanti par la base » avec sa raison.
2. Contrôles d'intégrité (C12, C14, C27, C37) sur **toutes** les données, les autres sur les données
   à la date de référence.
3. La note exclut les contrôles garantis à zéro ; un garanti qui sonne compte normalement.
4. Le contrôle des soldes (journal brut = soldes, pas de solde négatif) reste disponible à part.
5. Liens cliquables par type de colonne (référence, lot, OF, commande, dossier, réception,
   qualité, fournisseur, métier).
6. Export Excel : synthèse + une feuille par contrôle en anomalie.
7. Réservé à direction + achats ; l'alimentation ne voit rien des contrôles.

---

## 6. Points incohérents ou ambigus

1. **Colonne « Écart (%) » à deux échelles** : C08 et C30 mettent une **fraction** (0,034), C36 un
   **pourcentage** (3,4) ; l'écran affiche donc « 0,03 » sous « Écart (%) » pour C08/C30.
2. **Colonne « Jours » à trois sens** : jours depuis la commande (C06), depuis l'arrivée (C28),
   nombre de dates distinctes (C31).
3. **C36 : clé `devise` absente de `COLONNES`** (s'affiche « Devise » par repli) ; à l'inverse
   `unite`, `anomalies`, `bloquants`, `conformes`, `score`, `total` sont déclarées mais jamais
   produites (reste de l'ancienne colonne « Unité » retirée en `d2e1e39`).
4. **Matières inactives comptées** par C05, C07, C19 (et C13, C15) alors que leur « quoi faire »
   propose de « désactiver » la matière : la désactiver ne fait pas disparaître l'anomalie. C38, lui,
   ignore les inactives. C13 dit « Commander tout de suite » même pour une matière désactivée ou
   sans achat (`sans_achat`), que le plan d'achat ne proposera jamais.
5. **C06 contre l'écran des commandes** : sans date promise ni ETA, C06 juge à `date_bc + 60 j`
   (60 en dur) alors que la liste des commandes et le courriel du lundi (`achats._statut_livraison`,
   `achats.py:78-100` ; `courriel.py:36-43`) ne déclarent jamais un tel bon « en retard » : les
   comptes de retards diffèrent.
6. **Score gonflé par les « hors saisie »** : C02, C04, C14, C20, C24, C26, C27, C31, C32 ne peuvent
   pratiquement pas sonner (contraintes, verrous, `date_permise`, `lot_id` NOT NULL,
   `ck_solde_positif`) mais ne sont pas dans `GARANTIS` : leur zéro compte comme « conforme », à
   rebours de la règle « un zéro qui ne peut pas être autre chose ne dit rien ».
   `docs/conformite/2-regles-calculs-api.md:177-200` les classe d'ailleurs « devenus contrainte ».
7. **C10 garanti mais « avertissement »**, alors que les autres garantis sont bloquants.
8. **C11 ne peut jamais sonner** et ne regarde que EUR et USD : les taux viennent de la table
   `devise` (CHECK > 0) ou des défauts 11,0 / 9,5 ; une autre devise (CNY, GBP…) sans cours ne
   serait vue nulle part. Défauts incohérents : `Parametres` 11,0 / 9,5 contre devises installées
   EUR 10,8 / USD 10,0 (`main.py:45`).
9. **Epsilons différents** pour le même invariant : C27 `−1e-9` (par lot, tous magasins), C37 et
   C12 `POUSSIERE` 1e-3 (par lot × magasin), C12 repli 0,01, `ck_solde_positif` −0,0005, soldes
   `POUSSIERE`. Un résidu flottant peut faire sonner C27 sans C37.
10. **Deux contrôles du même invariant** : C12 (moteur, clés référence/n° de lot/code magasin,
    journal traduit — un transfert orphelin est silencieusement écarté par `_journal`) et
    `/controles/soldes` (SQL brut, `lot_id`/`magasin_id`, + soldes négatifs). Le second n'est ni
    dans la note, ni dans l'export, et affiche des identifiants techniques (« lot n° 412 »).
11. **C12 : branche de repli morte** en service (`complet = charger(s)` a toujours des soldes) ; de
    même tout le « mode classeur » (libellé C06, C30/C33/C38 coupés, règles C18…) alors que
    `pour_le_moteur` force `methode = "corrigee"` (`parametres.py:185`) et que l'écran dit que ce
    mode « n'existe plus ».
12. **C25 trop faible** : il suffit qu'une sortie de la référence ait existé un jour (même annulée,
    même il y a un an) pour qu'un fil monté aujourd'hui passe. Et C25/C23/C22 ne regardent que les
    métiers actifs, C24 tous les métiers.
13. **C23 : libellé « au catalogue »** alors qu'un poids pesé au lot suffit ; gravité « bloquant »
    alors que le commit `202d1a0` dit « le fil monté devient une information ».
14. **C29 : libellé trompeur** (« TVA … éloignée de 20 % de la valeur en douane ») ; la règle est
    « TVA saisie à plus de 5 % de la TVA attendue (20 % × (CAF + droits + TPI)) ». La tolérance 5 %
    est en dur (`TOLERANCE_TVA_IMPORT`), pas un réglage, contrairement à C35/C36.
15. **C36 muet** quand une marchandise du dossier n'est pas dans la devise de la facture ou quand le
    montant de facture manque : aucun signalement de ce non-contrôle.
16. **C28 : « sans frais » = sans frais non récupérable** (un dossier avec seulement la TVA est « sans
    frais ») ; 30 jours en dur ; seuls les dossiers ouverts. C34 compte tous les dossiers et somme
    la TVA dans « Frais (MAD) ».
17. **C38 au cours du jour** (pas au cours figé de l'achat), seuil 3 en dur ; le prix payé vient de
    `reception_ligne.prix` dont le commentaire d'API dit « dans l'unité de la matière (au kilo, ou au
    mètre) » (`receptions.py:342`) alors que C38 l'affiche « / kg » : à trancher pour les matières
    au mètre.
18. **C17 aveugle** aux matières sans groupe d'équivalence (sourcing « ❓ Hors catalogue »), qui sont
    pourtant mono-source par construction.
19. **Format des libellés** : C08/C30 « 2% » (`:.0%`, sans espace) contre C29/C35/C36 « 2 % ».
20. **Ordre de la liste** non numérique (C19, C21, C20, C22, C24, C25, C23…, C37 entre C27 et C28,
    C17/C18 en dernier) ; l'API le rend tel quel.
21. **Troncatures hétérogènes** (200 premières, 200 dernières pour C26, ou rien).
22. **Docstring** `controles.py:7` : « Quatre contrôles du classeur ont disparu » puis en liste six
    (T05, T06, T17, T18, T19, T20).
23. **Documentation périmée** : `ETAT-DES-LIEUX.md:576-613` donne C12 « Σ stock par magasin ≠ stock
    net » (règle remplacée), C25 « double compte », C30 « avertissement » (code : information), C38
    « dans l'unité de la matière » (code : au kilo) ; `conformite/2-regles-calculs-api.md` dit C29
    à 20 % en dur, C03 faussé, et « manque le quoi faire » pour une vingtaine de contrôles — tout
    cela est corrigé dans le code.
24. **Export du pilotage** : sa feuille « Contrôles » montre la gravité en clé brute et « conforme »
    pour un contrôle garanti, contrairement à l'export dédié et à l'écran.
25. **C14 vs C04/C16** : C14 regarde toutes les données, C04 et C16 seulement celles à la date ; un
    mouvement sans auteur daté après la date de référence échappe à C04 sur une date passée.
26. **C03** : un motif écrit à la main hors liste (reprise) ne commençant pas par « R » + chiffre
    donne « » et sonne ; c'est voulu mais dépend d'une table de libellés en dur
    (`operations.CODES_MOTIF`) qui n'est pas un référentiel.
27. **Synthèse `anomalies`** = nombre de **contrôles** non conformes, pas de lignes : la pastille du
    menu affiche « 3 » même s'il y a 400 lignes fautives.
