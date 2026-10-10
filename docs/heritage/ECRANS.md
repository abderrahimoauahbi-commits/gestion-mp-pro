# Héritage de Gestion MP — inventaire exhaustif des écrans, des gestes et des documents

Établi le 8 octobre 2026, en lecture seule, pour la réécriture **Gestion MP PRO**. Il décrit
chaque page, onglet, fenêtre, tiroir (bureau et téléphone de l'atelier), document imprimable,
ce qu'on y voit (indicateurs et leur formule, colonnes et unités, filtres, recherches, tris,
pieds de tableau, cas vides), chaque geste (bouton, confirmation sur la ligne, message de succès
ou de refus, raison d'un bouton grisé) et chaque lien entre écrans — assez précis pour
reconstruire sans relire l'ancien code.

Références `fichier:ligne` relatives à `/Users/mohamed/gestion-mp/ecran/src` (écran) ou au dépôt
(`gestion_mp/…` pour le serveur). Les libellés entre guillemets sont exacts.

Compléments : `DECISIONS.md` (le pourquoi), `REGLES-ECRAN.md` (les règles transverses et ce que
les recettes ont corrigé), `AMELIORATIONS-PRO.md` (ce que PRO fait mieux).

## 0. La carte

### 0.1 Rôles et arrivée

| Rôle | Arrivée après connexion | Appareil |
|---|---|---|
| Direction | `/cockpit` (l'Accueil n'est pas dans son menu) | poste, tablette |
| Achats | `/accueil` (« Ma journée ») | poste |
| Alimentation des machines | téléphone (écran ≤ 700 px) : `/atelier` ; poste : `/accueil` (et `/` → `/sorties`) | téléphone, poste |

`App.tsx:88-98` (`accueilDe`, `surTelephone` = `matchMedia('(max-width: 700px)')`). Un écran
réservé à un autre rôle renvoie à l'accueil du rôle avec le bandeau « L'écran demandé (…) est
réservé à un autre rôle : vous êtes revenu à votre accueil. » (`App.tsx:206`). `/lot/:id` (QR) :
au téléphone → `/atelier/lot/:id` ; au bureau → page du lot.

### 0.2 Le menu du bureau (`App.tsx:41-86`)

La direction voit tout (`roles: []` = direction seule ; la direction passe toujours). Pastilles :
« Stock, lots & mouvements » = ruptures + critiques (`/api/cockpit`, relu toutes les 3 min) ;
« Analyse » = anomalies de contrôle, et le lien ouvre alors `/analyse?onglet=controles`.

| Groupe | Libellé du menu (infobulle) | Route | Rôles (en plus de la direction) |
|---|---|---|---|
| Tous les jours | Accueil | `/accueil` | achats, alimentation (pas la direction) |
| | Cockpit | `/cockpit` | direction seule |
| | Stock, lots & mouvements | `/stock` | achats, alimentation |
| | Sorties vers les machines | `/sorties` | achats, alimentation |
| | Production & besoins | `/production` | achats, alimentation |
| | Écran atelier (téléphone) | `/atelier` | alimentation |
| Achats | Plan d'achat | `/plan-achat` | achats |
| | Commandes | `/commandes` | achats |
| | Réceptions | `/receptions` | achats |
| | Importations & coût de revient | `/importations` | achats |
| Stock | Inventaire | `/inventaire` | achats |
| | Ouvertures, transferts, ajustements | `/operations` | achats |
| Référentiels | Matières, classification, fournisseurs | `/catalogue` | achats |
| | Qualités et recettes | `/qualites` | achats (lecture) |
| | Métiers à tisser | `/metiers` | achats (lecture), alimentation (fils montés) |
| Pilotage | Analyse (« Prix, fournisseurs, valorisation, contrôles ») | `/analyse` | achats |
| | Réglages (« Réglages, comptes, sauvegardes ») | `/reglages` | direction ; la route est ouverte aux achats (onglet Devises seul) mais absente de leur menu |
| Aide | Mode d'emploi | `/guide` | achats, alimentation |
| (pied) | nom, rôle, « Se déconnecter » | — | tous |

### 0.3 Les écrans et leurs onglets (adresse `?onglet=`)

| Écran | Onglets (clé → libellé) |
|---|---|
| Cockpit | `faire` « À faire et à valider » (défaut) · `alertes` « Matières en alerte » · `ensemble` « Vue d'ensemble » · `evolution` « Évolution » · `economies` « Opportunités d'économies » |
| Stock | `matieres` « Par matière » · `lots` « Lots » · `mouvements` « Mouvements de stock » · `ordres` « Ordres de fabrication » · `a-valider` « À valider » |
| Sorties | `valide` « Validées » · `brouillon` « Brouillons » · `annule` « Annulées » ; fiche d'ordre : « Lots à sortir / Lots sortis » · « Prévu par la recette et sorti net, par matière » |
| Production | `plan` « Plan de production » (compteur « N modifiée(s) ») · `glissant` « Plan glissant » · `realise` « Plan et réalisé » · `besoins` « Besoins matière » (compteur = lignes avec un besoin du plan ou retenu) |
| Plan d'achat | `fournisseurs` « Par fournisseur » · `references` « Références à commander » |
| Commandes | `brouillon` « Brouillons » · `a_approuver` « À approuver » · `envoyee` « Envoyées » · `confirmee` « Confirmées » · `clos` « Soldées / annulées » — à l'ouverture, le premier onglet non vide ; `?filtre=retard` |
| Réceptions | `brouillon` « Brouillons » · `validee` « Validées » · `annulee` « Annulées » · `reclamations` « Réclamations » · `bobines` « Poids des bobines » · `pesees` « Archive des pesées » |
| Importations | `ouverts` « Dossiers ouverts » · `clos` « Dossiers clos » · `rattacher` « En attente de dossier » |
| Inventaire | `cours` « En cours de comptage » · `passes` « Inventaires validés » ; fenêtre : « Lots à compter » · « Pièces jointes » |
| Opérations | `ouverture` « Ouverture de stock » · `transfert` « Transferts » (dont libérations de quarantaine) · `ajustement` « Ajustements » · `retour_fournisseur` « Retours fournisseur » · `retour_machine` « Retours machine » |
| Catalogue | `matieres` « Matières » · `classification` « Classification » · `fournisseurs` « Fournisseurs » |
| Qualités | `qualites` « Qualités » · `nomenclature` « Nomenclature » |
| Analyse | `valorisation` « Valorisation » (court « Valeur ») · `matrice` « Matrice » · `historique` « Prix payés » · `opportunites` « Opportunités d'économies » (court « Opportunités ») · `fournisseurs` « Fournisseurs » · `revient` « Coût de revient » · `echeancier` « Échéancier » · `controles` « Contrôles » · `production` « Production » — défaut : `valorisation` (direction), `matrice` (achats) |
| Réglages | `parametres` « Paramètres » (défaut, dix familles en liste verticale) · `devises` « Devises » (seul onglet des achats) · `magasins` « Magasins » · `postes` « Postes de frais » (court « Frais ») · `codes` « Codes douaniers » (court « Douane ») · `comptes` « Comptes » · `sauvegardes` « Sauvegardes » · `journal` « Journal des actions » · `courriel` « Courriel du lundi » (court « Courriel ») · `serveur` « Serveur » · `telephone` « Téléphone » |
| Mode d'emploi | `regles` « Les règles » · `roles` « Qui fait quoi » · `pas` « Pas à pas » · `calculs` « Les calculs » · `analyse` « L'analyse » · `ecrans` « Les écrans de l'ERP Fil » · `telephone` « Le téléphone » |
| Atelier (téléphone) | routes `/atelier` (tuiles), `/atelier/envoyer`, `/atelier/bons`, `/atelier/bons/:id`, `/atelier/retour`, `/atelier/chercher`, `/atelier/lot/:id`, `/atelier/deplacer`, `/atelier/montage`, `/atelier/signaler` ; barre du bas : Accueil, Envoyer, Retour, Lots |

Le détail de chacun suit, domaine par domaine.

---

## Partie 1 — Coque, composants partagés, connexion et installation, accueil, cockpit, mode d'emploi, page du lot

Source : `/Users/mohamed/gestion-mp/ecran` (lecture seule, code lu en entier). Références `fichier:ligne`
relatives à `ecran/src` sauf mention `gestion_mp/…` (serveur) ou `docs/…`.

Rappel des rôles (serveur `gestion_mp/modeles.py:42-49`) : `direction` (« Direction »), `achats`
(« Responsable achats »), `alimentation` (« Responsable alimentation machines »). Ces libellés
(`role_libelle`) s'affichent tels quels dans le menu et sur l'écran de connexion.

Dépendances de droits serveur (`gestion_mp/securite.py:104-122`) : `acteur` = toute personne connectée ;
`droit(*roles)` laisse toujours passer la direction ; `ACHATS` = achats + direction ; `DIRECTION` =
direction seule ; `STOCK` = achats + alimentation + direction ; `LECTURE` = tous.
Message de refus de rôle (403) : « Cette action est réservée à : responsable achats. » (liste des rôles
en minuscules, `securite.py:109-110`) ; pour `DIRECTION` : « Cette action est réservée à : la direction. »

---

### 0. Socle technique de l'écran

#### 0.1 `index.html` (racine de `ecran/`)
- `<title>Gestion MP</title>` (aucun titre par page), `lang="fr"`.
- `theme-color` `#17497f` ; `apple-mobile-web-app-capable=yes` ; barre d'état iOS `black-translucent` ;
  `apple-mobile-web-app-title` « Gestion MP » ; icône `/icone.svg`, icône iOS `/icone-180.png` ;
  `viewport … viewport-fit=cover` ; manifeste `/manifest.webmanifest`.

#### 0.2 `public/manifest.webmanifest` — installation sur l'écran d'accueil
| Clé | Valeur |
|---|---|
| name | « Gestion MP — matières premières » |
| short_name | « Gestion MP » |
| start_url | `/` |
| display | `standalone` (s'ouvre comme une application, sans barre d'adresse) |
| background_color | `#f4f6f8` |
| theme_color | `#17497f` |
| lang | `fr` |
| icônes | `/icone.svg` (any, svg), `/icone-192.png` (192×192), `/icone-512.png` (512×512) |

#### 0.3 `public/sw.js` — service worker minimal
- `install` → `skipWaiting()` ; `activate` → `clients.claim()` ; `fetch` → ne fait **rien** (aucun cache).
- Principe affiché en commentaire (sw.js:1-3) : « Les données passent toujours par le réseau — un stock
  d'hier affiché comme celui d'aujourd'hui serait pire qu'un message « pas de réseau ». »
- Enregistré par `main.tsx:32-34` **seulement si** `'serviceWorker' in navigator && window.isSecureContext`
  (erreur d'enregistrement ignorée). Le serveur sert `sw.js` et le manifeste avec `Cache-Control: no-cache`
  (`gestion_mp/main.py` route `ecran`).

#### 0.4 `main.tsx` — client de requêtes
- React Query, options par défaut (main.tsx:9-18) :
  - `refetchOnWindowFocus: true` (« Plusieurs personnes saisissent en même temps : on relit en revenant sur l'onglet ») ;
  - `staleTime: 15 000 ms` ;
  - `retry` : 1 nouvel essai, sauf si le **message** de l'erreur contient 401, 403 ou 404 (voir anomalies).
- `BrowserRouter` (adresses propres, sans `#`), `StrictMode`, feuilles `index.css` + `ajouts.css`.

#### 0.5 `lib/api.ts` — appels serveur et erreurs
- Tous les appels partent vers `/api{chemin}` avec `credentials: 'same-origin'` (cookie de session
  `gestion_mp_session`) et l'en-tête **`X-Gestion-MP: 1`** ; `Content-Type: application/json` si corps.
- Méthodes : `api.get`, `api.post(chemin, corps?)`, `api.put(chemin, corps)`, `api.supprimer(chemin)` (DELETE).
- Réseau injoignable → erreur (statut 0) : **« Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). »**
- Réponse non OK → message = `detail` du serveur s'il est texte ; si tableau, les `msg` joints par « · » ;
  sinon « Erreur {code} ». Classe `ErreurApi(message, statut)`.
- **Session perdue** : toute réponse 401 sur une route autre que `/connexion…` émet l'événement
  `gestion-mp:session-perdue` → l'application revient à l'écran de connexion (voir §1.4).
- Réponse 204 → `undefined`.
- Heure : chaque réponse porte `X-Heure-Serveur` ; `recalerHorloge` en tire le décalage (voir `heure.ts`).
- `heureServeur()` → « 13:20:46 » (heure de l'usine, `toLocaleTimeString('fr-FR')`).
- `qs(params)` → chaîne `?a=1&b=2` en sautant `''`, `null`, `undefined`, `false`.
- `ouvrir(chemin)` → `window.open('/api'+chemin, '_blank', 'noopener')` : pages imprimables du serveur
  (bon de commande, étiquettes, bilan).
- `messageErreur(e)` → `e.message` ou `String(e)`.
- Côté serveur (`gestion_mp/main.py`) : toute écriture `/api/` sans l'en-tête est refusée (403)
  « Requête refusée : elle ne vient pas de l'écran de Gestion MP. » (sauf `/api/connexion`,
  `/api/installation`, `/api/deconnexion`). Les refus de saisie (422) sont traduits en français et nomment
  le champ : « champ : message » joints par « ; » ; table de traduction : « Field required » → « à renseigner »,
  « Input should be a valid » → « valeur incorrecte », « should be greater than or equal to » → « doit être
  au moins », « should be greater than » → « doit être supérieur à », « should be less than or equal to » →
  « doit être au plus », « should be less than » → « doit être inférieur à », « should have at least » →
  « trop court : au moins », « should have at most » → « trop long : au plus », « characters » → « caractères »,
  « String » → « Texte », « Input » → « La valeur », « List » → « La liste », « items » → « éléments ».
- 401 serveur : « Connectez-vous pour continuer. » (pas de session) ; « Ce compte n'est plus actif. »

#### 0.6 `lib/session.tsx`
- `Role = 'direction' | 'achats' | 'alimentation'`.
- `Compte` : `id, identifiant, nom, role, role_libelle, email, actif, vu_le`.
- `Session` : `compte`, `peut(...roles)`, `deconnecter()`, `rafraichir()`.
- **Règle `peut`** (`peutAvec`, session.tsx:34-36) : la direction passe partout ; un autre rôle seulement
  s'il est nommé. `useSession()` hors contexte → erreur « useSession hors de la session ».

#### 0.7 `lib/heure.ts` — l'heure de l'usine
- Décalage = heure du serveur (`X-Heure-Serveur`, « 2026-10-08T13:20:46 », heure locale serveur) − horloge du poste.
- `maintenant()` = instant du poste + décalage ; `jourIso(d)` « AAAA-MM-JJ » en heure locale ;
  `jourDansN(n)` = date du jour à l'usine décalée de n jours (arrondi).
- Raison (commentaire) : en octobre 2026 Chrome compte le Maroc à +01 quand le Mac est à +00.

#### 0.8 `lib/format.ts` — formats (tout en français)
| Fonction | Rendu | Règle |
|---|---|---|
| `nombre(v, d=0)` | « 17 398 184 » | séparateur de milliers = espace insécable U+00A0 (remplace l'espace fine U+202F jugée invisible). d=0 entier ; d=1 exactement 1 décimale ; d=2 exactement 2 ; d≥3 **jusqu'à 4** décimales. Vide/NaN → « — ». |
| `montant(v, devise='MAD')` | « 1 234 MAD » | entier + espace insécable + devise ; « — » si vide |
| `montantCourt(v, devise)` | « 17,4 M MAD » | au-delà de 1 000 000 en valeur absolue : 1 décimale + « M » ; sinon `montant`. Pour les indicateurs (montant exact en infobulle). |
| `montants(parDevise)` | « 61 888 USD · 53 132 EUR » | une devise par terme, triées par valeur décroissante, séparées « · », **jamais additionnées** ; « — » si rien |
| `classementLisible(c)` | « ATTENTION » | remplace « À surveiller » (mot du classeur) par « ATTENTION » |
| `prixUnite(v)` | « 12,50 » / « 0,0011 » | 2 décimales ; jusqu'à 4 si 0 < |v| < 0,1 |
| `metres(kg, kgParMl)` | « ≈ 1 020 ml » | kg ÷ densité, entier ; vide si pas de densité (matières au poids) |
| `kgEtMetres(kg, kgParMl, d=1)` | « 14,3 kg ≈ 1 020 ml » | kilos + mètres indicatifs pour cuir/franges/ruban |
| `pourcent(v, d=1)` | « 12,5 % » | décimales fixes, espace insécable avant % |
| `part(v, d=1)` | « 25,0 % » | v × 100 puis `pourcent` |
| `jours(v)` | « 45 j » | entier + « j » |
| `date(v)` | « 08/10/2026 » | `toLocaleDateString('fr-FR')` ; texte non daté rendu tel quel ; vide → « — » |
| `horodatage(v)` | « 08/10/2026 13:20 » | date courte + heure courte |
| `aujourdhui()` | « 2026-10-08 » | date du jour à l'usine |
| `tonStatut(statut)` | classe CSS | contient RUPTURE → `rupture` ; CRITIQUE → `critique` ; URGENT → `urgent` ; ATTENTION → `attention` ; NON CONSOMM → `neutre` ; sinon `ok` |
| `tonTier(tier)` | classe CSS | « TIER 1 » → `rupture` ; « TIER 2 » → `critique` ; « TIER 3 » → `attention` ; sinon `neutre` |

Statuts de stock (serveur `gestion_mp/calcul/modele.py:41-57`) : « ⚫ RUPTURE », « 🔴 CRITIQUE », « 🟠 URGENT »,
« 🟡 ATTENTION », « 🟢 OK », « ⚪ NON CONSOMMÉE ». En alerte = RUPTURE, CRITIQUE, URGENT, ATTENTION
(« NON CONSOMMÉE » n'appelle pas d'achat).

Couleurs de ton (CSS `index.css`) : ok = vert `#146c44` ; attention = ambre `#8d5c07` ; urgent = orange
`#a1560b` ; critique = rouge `#a92c2c` ; rupture = gris très foncé `#2d3440` (étiquette) / rouge (indicateur) ;
neutre = gris ; accent = bleu `#1f5fa8`. Un indicateur coloré porte aussi un filet vertical de 3 px à gauche
(« la couleur ne fait pas seule le message »).

#### 0.9 `lib/recherche.ts` — recherche à la frappe
- `sansAccents` : décomposition NFD, retrait des diacritiques, minuscules.
- `correspond(texte, recherche)` : la recherche est découpée en mots (espaces) ; **chaque** mot doit se trouver
  quelque part dans le texte (ordre libre, sans accents, sans casse). Recherche vide → tout correspond.
  Exemple du code : « rouge 2900 hasi » trouve « PP FRZ-2900 Dtex- Red… » de HASIRCI.
- `filtrer(liste, recherche, champs)` : joint les champs non nuls d'une ligne par une espace puis applique `correspond`.

#### 0.10 `lib/donnees.ts` — référentiels partagés (une clé de cache par liste)
| Hook | Route | Clé | Fraîcheur |
|---|---|---|---|
| `useMagasins` | GET `/magasins` | `magasins` | 60 s |
| `useFournisseurs` | GET `/fournisseurs` | `fournisseurs` | 60 s |
| `useArticles` | GET `/articles` | `articles` | 60 s |
| `useDevises` | GET `/devises` | `devises` | 60 s |
| `useMetiers` | GET `/metiers` | `metiers` | 60 s |
| `useQualites` | GET `/qualites` | `qualites` | 60 s |

Structures (pour reconstruire) : `Magasin {id, code, nom, type, actif, stock}` ; `Fournisseur {id, nom, code,
pays, contact, telephone, email, devise, delai_jours, couverture_commande_jours, mode_paiement,
delai_paiement_jours, conditions_paiement, incoterm, notes, actif, local, devises{}, articles}` ; `Article`
(matière) `{id, version, reference, designation, role, composition, type_fil, titrage, couleur, couleur_code,
densite (kg/ml, obligatoire pour cuir/franges/ruban et pour un prix au mètre), kg_par_ml (densité si rôle au
mètre, 0 sinon), fournisseur_id, fournisseur, prix (tel que saisi), unite_prix ('kg' défaut ou 'ml'), prix_kg
(lu par tous les calculs), devise, unite_achat, contenance_achat, minimum_commande, poids_bobine,
bobines_palette, contenance_palette, stock_min, couv_min_mois, groupe_equiv, priorite_equiv, actif,
modifie_par, modifie_le, stock?}` ; `Devise {code, nom, taux, actif}` ; `Metier {id, code, nom, laize, densite,
etages, actif}` ; `QualiteResume {id, code, nom, actif}` ; `Solde` (un lot et ses magasins : `lot_id, lot,
article_id, reference, designation, role, kg_par_ml, fournisseur, entre_le, poids_bobine, quantite, disponible,
quarantaine, bobines, magasins[{magasin_id, magasin, type, quantite}]`).
- `ROLES_AU_METRE = ['Cuir', 'Franges', 'Ruban']` : rôles comptés au mètre dans la recette ; leurs matières ont
  une densité, ne se montent pas en bobines, montrent leurs mètres indicatifs.

#### 0.11 `lib/commandes.ts` — une seule définition pour Accueil et Cockpit
- **Hors suivi** : si le numéro n'est pas fourni (`numero === undefined`) → statut ∈ {brouillon, a_approuver,
  soldee, annulee} ; sinon → pas de numéro, ou soldée, ou annulée (un bon parti « à approuver » pour une hausse
  reste suivi).
- `enRetard(c)` : pas hors suivi **et** le statut de livraison calculé par le serveur contient « retard »
  (« 🔴 En retard », « 🟠 Partiel retard »). Date jugée : ETA, sinon livraison prévue.
- `prixAConfirmer(c)` : pas hors suivi et `prix_a_confirmer > 0` (au moins une ligne au prix non confirmé).
- `brouillon(c)` : statut `brouillon`. `aApprouver(c)` : statut `a_approuver` (au-delà du seuil d'approbation).
- `ongletCommande(c)` : `clos` si soldée/annulée, sinon le statut (`brouillon`, `a_approuver`, `envoyee`,
  `confirmee`) ; `envoyee` par défaut.
- `numeroOuBrouillon(numero, statut)` : le numéro ; sinon « À approuver » si statut `a_approuver`, sinon « Brouillon ».
- `montantMad(c)` : `montant_mad` (prix confirmés) s'il est > 0 ou s'il n'y a pas d'estimation ; sinon
  `montant_estime_mad` avec drapeau « estimé » (un bon part sans prix ; l'estimation au catalogue déclenche l'approbation).
- `versCommandes(liste, onglet?, filtre?)` : une seule commande → `/commandes?onglet={ongletCommande}&commande={id}` ;
  plusieurs → `/commandes?onglet={onglet ?? onglet de la première}` (+ `&filtre=retard` si demandé).
- Statuts commande (serveur) : « Brouillon », « À approuver », « Envoyée », « Confirmée », « Soldée », « Annulée ».

#### 0.12 `lib/teintes.ts` — la couleur d'un fil en couleur d'écran (exigence M86)
Le nom de couleur du catalogue (FR/EN, abrégé) est normalisé (minuscules, sans accents) et comparé dans
l'ordre (du plus précis au plus général) :

| Motif (regex) | Teinte |
|---|---|
| bleu marine / navy / marine | `#1b2f5e` |
| turk / turq | `#1295a8` |
| bleu / blue | `#2563b8` |
| vert fonce / d.green / dark green | `#1e5b3a` |
| olive / oilve / kaki / khaki | `#6b7a2a` |
| vert / green | `#2e8b57` |
| bordeau / bordo | `#7b1e2b` |
| brique / brick | `#b5532f` |
| rouge / red | `#c62828` |
| rose / pink | `#d6589a` |
| orange | `#e07b1a` |
| jaune / yellow | `#d4b400` |
| or (mot entier) / gold | `#c79a00` |
| camel | `#b8864b` |
| beige fonce / d.beige | `#a98f63` |
| l.beige | `#cdb891` |
| beige | `#bfa57a` |
| cream / creme / ivory / ivoire / ecru | `#d1c089` |
| l.brown | `#9a7354` |
| marron / brown | `#6d4c33` |
| khave / kahve / cafe / coffee | `#5c4033` |
| dk vison / dk vizon | `#5f4b3d` |
| vison / vizon | `#8a6f5a` |
| taupe | `#8b7d70` |
| noir / black | `#1f2933` |
| gris clair / l.grey / l.gris | `#a5aeb8` |
| dark grey / d.grey / gris fonce | `#4b5560` |
| gris / grris / grey / gray | `#7a8591` |
| violet / mauve / purple | `#7c3aed` |
| blanc / white | `#9fb0c2` (teintes claires volontairement assombries pour rester lisibles sur blanc) |

- Sans teinte reconnue : palette `#1f5fa8, #c2410c, #146c44, #7c3aed, #b45309, #0e7490` (dans l'ordre).
- Deux fils de même teinte se distinguent par le trait : plein, `8 5`, `2 4`, `12 4 2 4` (`stylesDesFils`).
- Autre palette de courbes (direction, `components/direction/commun.tsx:13-22`) : `#2a78d6, #eb6834, #1baf7a,
  #eda100, #e87ba4, #008300, #4a3aa7, #e34948` (huit au plus, toujours dans cet ordre).

---

### 1. La coque — `App.tsx`

#### 1.1 Démarrage, chargement, session
- **Fichiers** : `App.tsx`, `main.tsx`, `lib/session.tsx`, `lib/api.ts`.
- **Données** : GET `/moi` (clé `moi`, sans nouvel essai, fraîcheur 60 s) → `Compte` (route `acteur`).
- Pendant la lecture de `/moi` : « Un instant — chargement : Gestion MP… » (`Chargement quoi="Gestion MP"`).
- Pas de compte (401) **ou** session perdue → écran **Connexion** (§3). Après connexion réussie : la session
  perdue est levée, tout le cache est vidé, `/moi` relu.
- Pendant le chargement paresseux d'un écran : « Un instant — chargement : l'écran… ».

#### 1.2 Routage de premier niveau (App.tsx:157-176)
| Adresse | Condition | Résultat |
|---|---|---|
| `/atelier/*` | `peut('alimentation')` (alimentation ou direction) | écran atelier (téléphone) ; sinon redirection vers l'accueil du rôle (`replace`) |
| `/lot/:id` | **seulement si téléphone** au moment du rendu | redirection vers `/atelier/lot/:id` (l'étiquette QR ouvre la fiche atelier) |
| `/` | — | alimentation **au bureau** → `/sorties` ; sinon accueil du rôle |
| `*` | — | la coque de bureau (`Bureau`) |

**Accueil du rôle** (`accueilDe`, App.tsx:96-101) : direction → `/cockpit` ; alimentation → `/atelier` au
téléphone, `/accueil` au bureau ; achats → `/accueil`.
**Téléphone** (`surTelephone`, App.tsx:104-106) : `matchMedia('(max-width: 700px)')` (largeur seule ;
le commentaire dit « étroit et tactile »).

#### 1.3 La coque de bureau (`Bureau`, App.tsx:179-273)
- **Mise en page** : barre de menu à gauche (`nav`) + contenu (`main.contenu`). En dessous de 1080 px de large,
  le menu se replie derrière un bouton fixe en haut à gauche **« ☰ Menu »** (panneau de 290 px, 85 vw max) ;
  il se referme à chaque changement d'adresse.
- **Marque** : « **Gestion MP** » / « Matières premières ».
- **Bas du menu** : nom du compte (gras), `role_libelle` (note), bouton **« Se déconnecter »** (sans
  confirmation au bureau).

##### Menu par rôle (groupes et libellés exacts, App.tsx:45-94)
`roles: []` = direction seule. Le lien « Accueil » est masqué pour la direction (elle a le Cockpit).
Chaque lien a une infobulle = son `detail` s'il existe, sinon son libellé.

| Groupe | Libellé | Adresse | Direction | Achats | Alimentation | Infobulle |
|---|---|---|---|---|---|---|
| Tous les jours | Accueil | `/accueil` | — (masqué) | ✓ | ✓ | Accueil |
| Tous les jours | Cockpit | `/cockpit` | ✓ | — | — | Cockpit |
| Tous les jours | Stock, lots & mouvements | `/stock` | ✓ | ✓ | ✓ | idem + **pastille** |
| Tous les jours | Sorties vers les machines | `/sorties` | ✓ | ✓ | ✓ | |
| Tous les jours | Production & besoins | `/production` | ✓ | ✓ | ✓ | |
| Tous les jours | Écran atelier (téléphone) | `/atelier` | ✓ | — | ✓ | |
| Achats | Plan d'achat | `/plan-achat` | ✓ | ✓ | — | |
| Achats | Commandes | `/commandes` | ✓ | ✓ | — | |
| Achats | Réceptions | `/receptions` | ✓ | ✓ | — | |
| Achats | Importations & coût de revient | `/importations` | ✓ | ✓ | — | |
| Stock | Inventaire | `/inventaire` | ✓ | ✓ | — | |
| Stock | Ouvertures, transferts, ajustements | `/operations` | ✓ | ✓ | — | |
| Référentiels | Matières, classification, fournisseurs | `/catalogue` | ✓ | ✓ | — | |
| Référentiels | Qualités et recettes | `/qualites` | ✓ | ✓ | — | |
| Référentiels | Métiers à tisser | `/metiers` | ✓ | ✓ | ✓ | |
| Pilotage | Analyse | `/analyse` (ou `/analyse?onglet=controles`) | ✓ | ✓ | — | « Prix, fournisseurs, valorisation, contrôles » + **pastille** |
| Pilotage | Réglages | `/reglages` | ✓ | — | — | « Réglages, comptes, sauvegardes » |
| Aide | Mode d'emploi | `/guide` | ✓ | ✓ | ✓ | |

Un groupe sans lien visible n'est pas affiché (l'alimentation voit : Tous les jours, Référentiels [Métiers à
tisser seul], Aide). Le lien actif porte la classe `actif` (filet bleu à gauche). Le menu doit tenir sans
défiler en 1366 × 768 (commentaire App.tsx:81-82).

##### Pastilles d'alerte (App.tsx:185-192, 223-224)
- **Données** : GET `/cockpit` (clé `cockpit`, partagée avec le Cockpit et l'Accueil), relu toutes les **180 s** ;
  **non lu pour l'alimentation** (route serveur `ACHATS`).
- Pastille rouge sur « Stock, lots & mouvements » = `stock.ruptures + stock.critiques` (si > 0).
- Pastille rouge sur « Analyse » = `controles.anomalies` (si > 0) ; dans ce cas le lien mène directement à
  `/analyse?onglet=controles`.
- Style : fond rouge `#a92c2c`, texte blanc, arrondi, largeur mini 20 px, chiffres tabulaires, collée à droite.

##### Gardes de route (App.tsx:194-196, 247-268)
`garde(roles, écran)` : si `peut(roles)` faux → redirection (`replace`) vers l'accueil du rôle, avec en état
d'adresse `refuse = chemin demandé`.

| Adresse | Garde | Remarque |
|---|---|---|
| `/accueil` | aucune | la direction peut l'ouvrir par l'adresse (lien du Cockpit « Accueil des achats ») |
| `/cockpit` | direction | |
| `/stock` | aucune | tous |
| `/lot/:id` | aucune | page du lot au bureau (§7) |
| `/sorties` | achats, alimentation | |
| `/plan-achat`, `/commandes`, `/receptions`, `/importations`, `/inventaire`, `/operations`, `/catalogue`, `/qualites`, `/analyse` | achats | |
| `/reglages` | achats | « Les achats n'y voient que les devises ; le menu ne leur montre pas Réglages. » |
| `/production` | aucune | |
| `/metiers` | achats, alimentation | |
| `/guide` | aucune | |
| tout autre chemin | — | redirection vers l'accueil du rôle, **sans** message |

##### Message « écran réservé » (App.tsx:241-245)
En tête du contenu, cadre `message info` : **« L'écran demandé ({chemin}) est réservé à un autre rôle : vous
êtes revenu à votre accueil. »** Il reste affiché tant que l'état d'adresse le porte (jusqu'à la navigation suivante).

#### 1.4 Déconnexion et session perdue
| Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| « Se déconnecter » | bas du menu | tous | — | aucune au bureau (au téléphone, l'atelier confirme : « Se déconnecter ({nom}) ? » / « Oui, se déconnecter ») | POST `/deconnexion` (sans en-tête requis) | cache vidé, écran de connexion | quoi qu'il arrive (bloc `finally`), retour à la connexion |
| « ☰ Menu » | haut gauche (< 1080 px) | tous | — | — | — | ouvre/ferme le panneau | — |

- **Session perdue** : toute réponse 401 (session expirée, compte désactivé) d'un appel autre que `/connexion`
  bascule l'application sur l'écran de connexion, **sans message explicatif** (le 401 porte pourtant
  « Connectez-vous pour continuer. » ou « Ce compte n'est plus actif. »).

---

### 2. Composants partagés — `components/ui.tsx` et `components/PiecesJointes.tsx`

#### 2.1 `Page` (ui.tsx:15-38)
En-tête `page-tete` : `h1` = `titre` ; `p.sous-titre` = `sous_titre` (optionnel) ; à droite `div.actions`
(optionnel) ; puis le contenu.

#### 2.2 `Carte` (ui.tsx:40-62)
`section.carte` ; si `titre` : en-tête `carte-tete` avec `h2` = titre et à droite `extra` (liens, bascule,
boutons) ; corps `carte-corps`. Classe supplémentaire possible.

#### 2.3 `Indicateur` (ui.tsx:64-85)
Bloc : `libelle` (petit), `valeur` (grand), `detail` (sous-texte, optionnel). `ton` ∈ ok, attention, urgent,
critique, rupture, neutre (couleur de la valeur + filet gauche 3 px). `titre` = infobulle (valeur exacte quand
l'affichage abrège). Dans une carte, l'indicateur perd son ombre.

#### 2.4 `Etiquette` (ui.tsx:87-89)
Pastille arrondie `etiquette {ton}` ; tons : ok, attention, critique, urgent, rupture, neutre, accent.

#### 2.5 `Bouton` (ui.tsx:91-117)
Variantes `principal` (bleu plein), `neutre` (défaut), `danger` (rouge). `type` button (défaut) ou submit.
`titre` → infobulle `title`. `disabled`.

#### 2.6 `Champ` (ui.tsx:119-140)
`label.champ` : libellé (`champ-libelle`), le contrôle, aide (`champ-aide`, sous le champ). Options `large`
(pleine largeur) et `duo` (deux colonnes : champ + bouton).

#### 2.7 `ChampNombre` (ui.tsx:142-197)
- Hors saisie : texte avec séparateurs de milliers (jusqu'à 6 décimales, `fr-FR`) ; en saisie : `type=number`.
- À l'entrée : un champ à 0 ou vide s'ouvre **vide** (sinon « 139 » deviendrait « 0139 ») ; une valeur réelle est
  **toute sélectionnée** (taper remplace, comme un tableur) ; le premier relâcher de souris est ignoré pour ne
  pas défaire la sélection.
- Molette neutralisée (le champ perd le focus) : un défilement ne modifie jamais un prix.
- Effacer le champ → valeur 0. `echelle` (ex. 100) : saisir un taux en pourcent (0,25 s'affiche « 25 »).
  `pas` (step), `placeholder`, `disabled`, `style`.

#### 2.8 `Message` (ui.tsx:199-207)
`div.message {erreur|succes|info}` (rouge / vert / bleu).

#### 2.9 `Chargement` (ui.tsx:209-211)
Texte : **« Un instant — chargement : {quoi}… »** (`quoi` par défaut « les données »).

#### 2.10 `BarreRecherche` (ui.tsx:213-230)
Champ texte `entree recherche`, placeholder par défaut **« Rechercher… »**, mise à jour à chaque frappe.

#### 2.11 `Onglets` (ui.tsx:232-260)
Rangée de boutons `role=tab` ; l'onglet actif porte `actif` et `aria-selected`. Chaque onglet : libellé +
compteur optionnel (`onglet-compte`) affiché dès que `compte != null` (un 0 explicite s'affiche).

#### 2.12 `Dialogue` (ui.tsx:262-338) — fenêtre
- Fond sombre (`fond-dialogue`) ; boîte `dialogue` (+ `large` ou `tres-large`) ; en-tête `h2` = titre et
  bouton **« × »** (`aria-label="Fermer"`).
- Se ferme par : **Échap** (seulement la fenêtre du dessus quand deux sont empilées — compteur de profondeur),
  **clic sur le fond**, **×**. Un clic dans la boîte ne ferme pas.
- La page dessous ne défile pas pendant que la fenêtre est ouverte (`body overflow hidden`, restauré à la fermeture).
- **`sale`** (saisie non enregistrée) : fermer n'abandonne pas en silence ; un bandeau apparaît **dans la fenêtre** :
  « **Des modifications ne sont pas enregistrées. Les abandonner ?** » avec **« Non, continuer la saisie »**
  (neutre, ferme le bandeau) et **« Oui, abandonner »** (danger, ferme la fenêtre).

#### 2.13 `Confirmer` (ui.tsx:340-382) — geste irréversible confirmé sur place
- État fermé : un `Bouton` (variante, `disabled`, `titre` infobulle) au libellé `children`.
- Au clic : le bouton est remplacé, au même endroit, par `span.confirmer` = **question** (texte `question`) +
  bouton **« Non »** (neutre, revient à l'état fermé) + bouton **`oui`** (texte fourni, ex. « Oui, retirer »),
  de variante `principal` si le bouton d'origine était neutre, sinon même variante (danger reste danger).
- « Oui » referme la question puis exécute `onConfirme` (attendu). Jamais de `window.confirm`.

#### 2.14 `Bascule` (ui.tsx:384-404)
Groupe de 2 à 5 boutons (`role=group`, classe `bascule`) pour les vues **d'une même carte** (souvent dans son
en-tête) ; le bouton choisi porte `actif`. Ré-exportée par `components/direction/commun.tsx` (« Deux à quatre vues dans un même onglet »).

#### 2.15 `HAUT` et `Cadre` (ui.tsx:406-413, 543-596) — tableaux qui défilent dans leur cadre
| Taille | Valeur CSS | Usage |
|---|---|---|
| `page` | `max(320px, calc(100vh - 290px))` | sous le seul en-tête de page |
| `court` | `max(240px, calc(100vh - 470px))` | sous indicateurs, onglets et filtres |
| `dialogue` | `max(280px, calc(100vh - 420px))` | dans une fenêtre |

- `Cadre` = `div.table-enveloppe.fenetre` avec `max-height` ; en-tête de tableau fixe (CSS).
- Priorité : `haut` (explicite) > `taille="dialogue"` (valeur fixe) > **hauteur mesurée** > `HAUT[taille]`.
- **Hauteur mesurée** (hors fenêtre, sans `haut`) : à chaque rendu et à chaque redimensionnement, le cadre
  mesure tout ce qui suit sous lui (marges, rembourrages, bordures des parents, voisins placés dessous) et
  prend le reste jusqu'au bas de la fenêtre du navigateur, **au moins 200 px** : la page ne défile jamais.
- Dans une fenêtre (`.dialogue`) sans `taille` : pas de hauteur imposée.

#### 2.16 `useEnvoi` (ui.tsx:417-448) — un geste qui écrit
`envoyer(geste, messageSucces?)` : met `occupe`, efface les messages, exécute ; succès → message vert
(si fourni) et renvoie le résultat ; erreur → message rouge = message de l'erreur, renvoie `undefined`.
Expose `occupe, erreur, succes, effacer(), messages` (les deux `Message` prêts à afficher), `setErreur`, `setSucces`.

#### 2.17 `ChoixRecherche` (ui.tsx:450-541) — choisir dans une longue liste en tapant
- Champ ; placeholder par défaut **« Taper pour chercher… »** ; affiche le libellé du choix courant hors saisie.
- Au focus : texte vidé, liste ouverte ; filtre = chaque mot tapé dans le **libellé** (sans accents ni casse) ;
  **60 résultats au plus** ; chaque option = libellé + `detail` optionnel (à droite, `choix-detail`).
- **Entrée** choisit si un seul résultat ; **Échap** ferme ; quitter le champ ferme ; aucun résultat :
  « **Rien ne correspond.** »

#### 2.18 `Vide` (ui.tsx:598-600)
`div.vide` (texte gris centré) pour un cas vide.

#### 2.19 Briques direction (`components/direction/commun.tsx`)
- `HAUT_DIALOGUE` (déprécié, = `HAUT.dialogue`) ; `COULEURS_SERIES` (8 couleurs) ;
- `signe(v)` → « +4,2 % » (signe + `part`) ; `MOIS_NOMS`/abréviations « janv., févr., mars, avr., mai, juin,
  juil., août, sept., oct., nov., déc. » ; `moisLisible('2026-09-30' ou '2026-09')` → « sept. 2026 » ;
- `LigneVide({colonnes})` : ligne de tableau `td.vide` sur toutes les colonnes, qui dit pourquoi c'est vide ;
- `trier(liste, clé, descendant)` : nombres numériquement, textes `localeCompare('fr', numeric)` ;
- `pluriel(n, mot, pluriel?)` → « 1 référence » / « 3 références » (n en `fr-FR`, pluriel par « s » par défaut).

#### 2.20 `PiecesJointes` — pièces jointes d'un document (`components/PiecesJointes.tsx`)
- **Objets** : `dossier`, `reception`, `commande`, `reclamation`, `inventaire`, `fournisseur`, `article`
  (utilisé dans Réclamations, DetailReception, DetailCommande, DetailDossier [lecture seule si pas achats],
  CatalogueFournisseurs et CatalogueMatieres [lecture seule si non modifiable], Inventaire [lecture seule si pas achats]).
- **Rôles** : toutes les routes sont `ACHATS` (achats + direction) : l'alimentation ne voit jamais de pièces.
- **Données** : GET `/pieces/{objet}/{id}` (clé `['pieces', objet, id]`, partagée avec les compteurs d'onglets `NombrePieces`).
- **Mise en page** : rangée `filtres` (si pas lecture seule) : bouton **« Joindre un document… »** (principal ;
  « Envoi… » pendant l'envoi ; grisé pendant l'envoi) + note « **ou le glisser ici · PDF, image, tableur, texte ou
  document · 20 Mo au plus. Ouvrir un document le télécharge.** » ; messages ; erreur de lecture ; puis `Cadre`
  (taille `dialogue` par défaut, réglable).
- **Glisser-déposer** : toute la zone accepte le dépôt (contour pointillé bleu 2 px pendant le survol) ; ignoré en lecture seule.
- **Sélecteur de fichiers** : multiple ; types acceptés `.pdf, image/*, .txt, .csv, .xlsx, .xls, .ods, .docx, .doc, .odt, .zip`.
- **Tableau**
  | Colonne | Contenu | Format | Remarque |
  |---|---|---|---|
  | Document | nom du fichier, lien de **téléchargement** `/api/piece/{id}/fichier` (attribut download) | texte | infobulle « Télécharger le document » ; le fichier ne s'affiche jamais dans l'application |
  | Genre | PDF (`application/pdf`), Image (`image/*`), Tableur (sheet/excel/`text/csv`), Document (word/document), Archive (`application/zip`), sinon Texte | texte | |
  | Taille | « 512 o », « 34 Ko », « 2,4 Mo » (Ko sans décimale, Mo 1 décimale) | droite | |
  | Par | auteur | texte | |
  | Joint le | horodatage | « 08/10/2026 13:20 » | |
  | (sans titre) | bouton « Retirer » | — | absent en lecture seule |
  Ordre : celui du serveur (id croissant = plus ancien d'abord). Pas de recherche, filtre, tri, pagination.
  Vide : « **Aucun document joint.** » (affiché une fois la lecture terminée).
- **Gestes**
  | Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus / erreurs |
  |---|---|---|---|---|---|---|---|
  | « Joindre un document… » / glisser-déposer | rangée du haut / toute la zone | achats, direction (hors lecture seule) | grisé pendant un envoi ; chaque fichier ≤ 20 Mo vérifié **avant** envoi | — | POST `/pieces/{objet}/{id}` (multipart, champ `fichier`, en-tête `X-Gestion-MP`), un fichier après l'autre | « « {nom} » joint. » ou « {n} documents joints. » ; liste relue | avant envoi : « « {nom} » est trop lourd : 20 Mo au plus. » ; serveur : « Document inconnu. » (404), « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. », « Fichier trop lourd (20 Mo au plus). », refus de rôle |
  | « Retirer » | dernière colonne | achats, direction | grisé pendant un envoi ; infobulle « Retirer « {nom} » de la liste (le retrait est tracé) » | sur place : « Retirer ce document ? » · « Non » · « Oui, retirer » (danger) | DELETE `/piece/{id}` | « « {nom} » retiré. » ; liste relue | « Pièce introuvable. » |
  | clic sur le nom | colonne Document | achats, direction | — | — | GET `/piece/{id}/fichier` | téléchargement | « Pièce introuvable. » |
- **Notions** : types serveur permis = PDF, images « à points » (jpeg, png, gif, webp, heic, heif, tiff, bmp —
  **pas de SVG**, qui peut porter du script), `text/plain`, `text/csv`, `application/vnd.*`, `application/msword`,
  `application/zip` ; 20 Mo au plus ; un retrait garde le fichier sur le disque (« une pièce retirée par erreur se
  retrouve ») et est inscrit au journal (« pièce retirée ») ; un dépôt aussi (« pièce jointe ») ; fichiers rangés
  dans `~/gestion-mp-pieces/{objet}/{id}/`, recopiés à chaque sauvegarde.

---

### 3. Connexion et première installation — `pages/Connexion.tsx`

#### Connexion — (toute adresse, tant que personne n'est connecté)
- **Fichiers** : `pages/Connexion.tsx`, serveur `gestion_mp/api/comptes.py:54-138`, `securite.py:128-156`.
- **Rôles** : écran public.
- **Données** : GET `/etat` → `{installe, societe}` (public) ; si installé, GET `/visages` → comptes **actifs**
  `{identifiant, nom, role, role_libelle}` triés par nom (public).
- **Cas** :
  - lecture de `/etat` en cours : « Un instant — chargement : Gestion MP… » ;
  - `/etat` en erreur ou réponse sans booléen `installe` : message rouge **« Le serveur ne répond pas. Vérifiez le
    réseau, puis rechargez la page. »** (seule une réponse claire « aucun compte » mène à l'installation) ;
  - `installe = false` → **Installation** (ci-dessous) ;
  - sinon → carte de connexion.
- **Carte de connexion** : titre `h1` « **Gestion MP** » ; note « **{société, sinon « Matières premières »} —
  touchez votre nom, puis tapez votre code.** » ; une grille de **visages** (boutons : nom en gras, libellé de
  rôle dessous ; le choisi porte `actif`) ; une fois un nom choisi :
  - champ **« Code d’{nom} »** si le nom commence par une voyelle (a e i o u y é è ê à â î ô û) ou un h,
    sinon **« Code de {nom} »** ; type mot de passe ; `autocomplete=current-password` ; focus automatique ;
    clavier **numérique** pour l'alimentation, texte sinon ;
  - **entrée automatique au téléphone** : pour l'alimentation, dès que le champ contient exactement 4 chiffres, la
    connexion part sans toucher « Entrer » ;
  - message d'erreur rouge éventuel ;
  - bouton **« Entrer »** (submit, principal ; « Connexion… » pendant l'envoi ; grisé si code vide ou envoi en cours).
- Pied : note **« Code oublié : la direction le remet à zéro dans Réglages › Comptes. »**
- Changer de visage efface le code et l'erreur.

| Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| Toucher un nom | grille des visages | public | — | — | — | champ de code | — |
| « Entrer » (ou Entrée, ou 4 chiffres pour l'alimentation) | carte | public | nom choisi, code non vide, pas d'envoi en cours | — | POST `/connexion {identifiant, secret}` (identifiant mis en minuscules côté serveur) | cookie de session posé, cache vidé, `/moi` relu → accueil du rôle (adresse courante conservée) | « Identifiant ou code incorrect. » (401 ; le code est vidé) ; après **5** échecs : « Trop d'essais : patientez {n} secondes. » (429 ; attente 30 s, puis 1 min, 2 min… doublant jusqu'à 15 min) ; un succès remet le compteur à zéro |

#### Installation (premier lancement) — même adresse, quand aucun compte n'existe
- Titre `h1` « **Bienvenue dans Gestion MP** » ; note « **Premier lancement : créez le compte de la direction. Il ouvre
  tout, et crée ensuite les comptes des achats et de l'alimentation des machines (Réglages › Comptes).** »
- **Formulaire**
  | Champ (libellé) | Type | Obligatoire | Défaut / exemple | Contrôle |
  |---|---|---|---|---|
  | Société | texte | non | vide | ≤ 160 caractères (serveur) ; si rempli, devient le paramètre `nom_entreprise` |
  | Votre nom | texte | oui | exemple grisé « MAZARI » | ≥ 2 caractères (bouton grisé sinon), ≤ 80 |
  | Identifiant (aide « ce qui vous désigne à la connexion ») | texte | non | exemple grisé « mazari » ; vide → nom en minuscules, espaces remplacés par des points | 2 à 40 (serveur), mis en minuscules |
  | Code (aide « 8 caractères au moins ») | mot de passe | oui | — | ≥ 8 (bouton grisé sinon), ≤ 200 |
- Pas de garde « Abandonner les modifications ? » (ce n'est pas une fenêtre).

| Geste | Rôle | Conditions | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|
| « Créer le compte et entrer » | public | nom ≥ 2 et code ≥ 8 | POST `/installation {societe, nom, identifiant, secret}` | compte **direction** créé, session ouverte, entrée au Cockpit ; journal « installation » | « Gestion MP est déjà installé : connectez-vous. » (409) ; refus de saisie traduits, ex. « identifiant : Texte trop court : au moins 2 caractères » |

#### Installation et accès décrits côté écran (`README.md`, `docs/MISE-EN-SERVICE.md`)
- **Raccourci bureau** « Gestion MP » (`~/Desktop/Gestion MP.app`) : interroge `http://localhost:8030/api/sante` ;
  si le serveur ne répond pas, lance `scripts/demarrer.sh` en tâche de fond (journal `~/Library/Logs/Gestion MP.log`),
  attend jusqu'à 60 s, puis ouvre le navigateur sur **`http://localhost:8030`**. Alertes macOS : « Le dossier de
  Gestion MP est introuvable : {chemin} » ; « Gestion MP n'a pas démarré. Vérifiez que PostgreSQL tourne, puis
  consultez {journal} ». Arrêt : `scripts/arreter.sh`.
- Serveur : port **8030**, écoute tout le réseau local (`0.0.0.0`), sert les écrans construits (copie figée de la
  version enregistrée, refaite à chaque démarrage).
- **Premier lancement** : l'écran crée le compte de la direction (nom, identifiant, code ≥ 8). Puis
  Réglages › Comptes : responsable achats (rôle Achats, code ≥ 8) ; alimentation des machines (rôle Alimentation,
  code « de 4 chiffres » — le serveur exige seulement 4 caractères au moins).
- **Téléphone, Wi-Fi** : même réseau ; ouvrir `http://<adresse-du-Mac>:8030` (adresse lue dans Réglages système ›
  Wi-Fi › Détails, aujourd'hui `192.168.100.67`, et dans Gestion MP, Réglages › Téléphone) ; accepter les
  connexions entrantes pour Python ; *Partager › Sur l'écran d'accueil* (iPhone) ou *⋮ › Ajouter à l'écran
  d'accueil* (Android) → s'ouvre comme une application (manifeste `standalone`). Conseil : adresse fixe du Mac (réservation DHCP).
- **Téléphone, 4G/5G** : Tailscale sur le Mac et le téléphone, même compte ; ouvrir `http://<nom-du-Mac>:8030` ou `100.x.y.z`.
- **Étiquettes QR** : contiennent `{adresse pour téléphones}/lot/{id}` (réglage « Adresse du serveur pour les
  téléphones », Paramètres › Société ; sinon l'adresse d'appel, et jamais « localhost », remplacé par l'adresse réseau).
- Sauvegardes, courriel du lundi, remise à zéro : côté Réglages (hors de cet inventaire).

---

### 4. Accueil — `/accueil`

- **Fichiers** : `pages/Accueil.tsx`, `lib/commandes.ts`.
- **Rôles** : menu achats et alimentation (lien masqué pour la direction, mais l'adresse n'est pas gardée : la
  direction y voit la version achats). Le choix de la version se fait par `peut('achats')` (achats **ou direction**).
- Pas d'onglets, pas de paramètre d'adresse lu.

#### 4.1 Carte transversale « À valider » (les deux versions)
- Titre : **« À valider ({n}) »** avec n = sorties en brouillon + opérations en brouillon (+ réceptions en
  brouillon pour les achats).
- Liste de **tâches** (fiches cliquables, liens) défilant dans une hauteur `HAUT.court` :
  | Tâche | Visible pour | Titre | Détail | Lien |
  |---|---|---|---|---|
  | Réceptions en brouillon | achats | « {n} réception(s) en brouillon » | « La matière n'est pas encore en stock. » + jusqu'à 4 « {fournisseur} du {date} » séparés « — », puis « — … (+{reste}) » | 1 seule : `/receptions?onglet=brouillon&reception={id}` ; sinon `/receptions?onglet=brouillon` |
  | Sorties en brouillon | tous | « {n} sortie(s) vers les machines en brouillon » | « Le fil n'est pas encore sorti du stock. » + jusqu'à 4 « {métier ou magasin} du {date} » ; si un brouillon porte un numéro : « ({numéro} : numéro repris, sans doute à supprimer ou à redater) » | 1 seule : `/sorties?onglet=brouillon&ordre={id}` ; sinon `/sorties?onglet=brouillon` |
  | Opérations en brouillon | tous (alimentation : seulement types `retour_machine` et `transfert`) | « {n} opération(s) en brouillon » | jusqu'à 4 « {type_libelle} du {date} » | achats : `/operations?onglet={type de la première}` ; alimentation : `/atelier` |
- Vide : « **Aucun brouillon : tout ce qui a été saisi est validé.** »
- Données : GET `/bons` (acteur), GET `/operations` (acteur ; le serveur masque ce que le rôle ne doit pas voir),
  GET `/receptions` (ACHATS, seulement pour les achats).

#### 4.2 Accueil de l'alimentation (au bureau)
- **En-tête** : titre **« Bonjour {nom} »**, sous-titre **« Alimentation des machines »**.
- Grille à deux colonnes (min 340 px) : **tuiles** + carte « À valider ».
- **Tuiles** (grands boutons-liens) :
  | Icône | Libellé | Sous-texte | Lien |
  |---|---|---|---|
  | ⇢ | **Envoyer aux machines** (tuile principale, en couleur) | « Qualité et m² : les fils et les lots sont proposés. » | `/atelier/envoyer` |
  | ⇠ | **Retour des machines** | — | `/atelier/retour` |
  | ☰ | **Les ordres** | — | `/sorties` |
  | ▦ | **Métiers à tisser** | — | `/metiers` |
- Aucun prix, aucun indicateur. Note : au bureau, l'adresse `/` mène l'alimentation à `/sorties`, pas ici (voir anomalies).

#### 4.3 Accueil des achats (et de la direction par l'adresse)
- **En-tête** : titre **« Bonjour {nom} »**, sous-titre **« Ce qui attend une action aujourd'hui. »**
- **Données** (toutes `enabled` pour achats/direction) : GET `/commandes` (ACHATS), `/receptions` (ACHATS),
  `/cockpit` (ACHATS, clé partagée), `/bons`, `/operations`, `/dossiers-a-rattacher` (ACHATS → `{factures[], sans_facture[]}`),
  `/signalements` (acteur ; non traités seulement), `/reclamations` (ACHATS → `{reclamations[]}`), `/inventaires` (acteur).

##### En-tête et indicateurs
| Indicateur | Valeur affichée | Formule / détail tel qu'affiché | Clic mène à |
|---|---|---|---|
| Ruptures, critiques, urgentes | nombre | `stock.ruptures + stock.critiques + stock.urgents` (cockpit) ; détail « au plan d'achat » ; ton `critique` si > 0, sinon `ok` | — (non cliquable) |
| Arrivées dans les 7 jours | nombre | commandes avec numéro, ni soldées ni annulées, dont la date d'arrivée (ETA, sinon livraison prévue) est entre **hier et dans 7 jours** ; détail « ETA, sinon livraison prévue » | — |
| Commandes en retard | nombre | `enRetard` (lib/commandes) ; ton `urgent` si > 0, sinon `ok` | — |
| Anomalies de contrôle | nombre | `controles.anomalies` ; ton `critique` s'il y a des bloquants, `attention` si anomalies, sinon `ok` ; détail « voir les contrôles → » ; infobulle « Ouvrir Analyse › Contrôles » | `/analyse?onglet=controles` |

##### Carte « À faire ({n}) » — ordre exact des tâches
1. **Besoins signalés par l'atelier** (un par signalement non traité, les urgents d'abord) : fiche (rouge si urgent)
   « **Besoin signalé : {référence}** » (sans « : » si pas de référence) + étiquette rouge « urgent » si urgence
   `urgente` ; note « « {texte} » — {par}, le {date} » ; bouton **« Traiter »** (infobulle « Répondre à l'atelier et
   ranger ce besoin parmi les traités ») → fenêtre Traiter (§4.4).
2. si alertes > 0 : fiche rouge « **{n} matière(s) en rupture, critiques ou urgentes** », détail « Le plan d'achat dit
   quoi commander, à qui, combien. » → `/plan-achat`.
3. si retards : fiche rouge « **{n} commande(s) en retard** », détail « Relancer le fournisseur, noter l'ETA. » + jusqu'à
   4 « {n° ou Brouillon/À approuver} · {fournisseur} » → `versCommandes(retards, -, 'retard')`.
4. si prix à confirmer : « **{n} commande(s) attendent la confirmation des prix** », détail jusqu'à 4 « {n°} · {fournisseur} » → `versCommandes(aPrix)`.
5. si bons en brouillon : « **{n} bon(s) de commande en brouillon à envoyer** », détail jusqu'à 4 fournisseurs →
   `versCommandes(brouillons, 'brouillon')`.
6. si factures sans dossier : « **{n} facture(s) reçue(s) sans dossier d'importation** », détail « Un dossier par
   facture : l'ouvrir depuis la facture, puis saisir les frais. » → `/importations?onglet=rattacher`.
7. si réceptions importées sans facture : « **{n} réception(s) importée(s) sans facture** », détail « Saisir la
   facture sur la réception : sans elle, pas de dossier, donc pas de frais dans le coût. » → `/importations?onglet=rattacher`.
8. si un inventaire est ouvert (le **premier** trouvé) : « **Inventaire {numéro} en cours** », détail « {comptés} /
   {lignes} lots comptés — le magasin est suspendu jusqu'à la validation. » → `/inventaire?inventaire={id}`.
9. si réclamations ouvertes : « **{n} réclamation(s) ouverte(s) chez les fournisseurs** », détail « Relancer, noter la
   réponse, clore. » + jusqu'à 4 « {numéro ou « Réclamation »} · {fournisseur} · {motif} ({jours} j) » → `/receptions?onglet=reclamations`.
10. si anomalies de contrôle : « **{n} contrôle(s) en anomalie** » (rouge s'il y a des bloquants), détail « Chaque contrôle
    dit quoi faire et mène à l'écran où le corriger. » → `/analyse?onglet=controles`.
- Vide : « **Rien n'attend : tout est à jour.** »
- Liste « quelques » : 4 premiers éléments séparés « — », puis « — … (+{reste}) ».

##### Carte « À valider » (§4.1)

##### Carte « Arrivées attendues dans les 7 jours ({n}) »
- Liste triée par date d'arrivée croissante (« la plus proche d'abord : c'est elle qu'on prépare au quai ») ;
  chaque fiche : « {n° ou Brouillon} · {fournisseur} », détail « prévue le {date} · {statut de livraison} » →
  `/commandes?onglet={onglet}&commande={id}`.
- Vide : « **Aucune arrivée annoncée cette semaine.** »

#### 4.4 Fenêtre « Besoin signalé par {par} » (Traiter)
- **Rôles** : affichée dans l'accueil achats ; route POST `/signalements/{id}/traiter` = `ACHATS`.
- Contenu : « **{référence} :** « {texte} » ».
- **Formulaire** : « **Réponse à l'atelier** » (zone de texte 3 lignes, large, 500 caractères max, focus auto,
  facultative), aide « ce qui est fait : commandé, en route, remplacé par… — l'atelier la lit sur son téléphone ».
- **Garde** : `sale` dès que la réponse n'est pas vide → « Des modifications ne sont pas enregistrées. Les abandonner ? ».
| Geste | Rôle | Conditions | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|
| « Annuler » | achats/direction | — | (garde si réponse saisie… sauf que « Annuler » ferme directement) | — | ferme | — |
| « Marquer traité » (« Enregistrement… » pendant) | achats/direction | grisé pendant l'envoi | — | POST `/signalements/{id}/traiter {reponse}` | liste relue, fenêtre fermée (pas de message) ; journal « besoin traité » | « Signalement introuvable. » (404) ; refus de rôle |

#### 4.5 Notions métier (Accueil)
Brouillon (rien n'a bougé au stock), réception en brouillon (« la matière n'est pas encore en stock »),
numéro repris sur un brouillon, besoin signalé (urgent / normal), réponse à l'atelier, facture sans dossier
d'importation, réception importée sans facture, inventaire en cours = magasin suspendu, réclamation ouverte
(âge en jours), contrôles (anomalies, bloquants), ETA, livraison prévue, en retard, prix à confirmer.

---

### 5. Cockpit — `/cockpit` (`?onglet=faire|alertes|ensemble|evolution|economies`)

- **Fichiers** : `pages/Cockpit.tsx`, `components/direction/cockpit/{CockpitAFaire, CockpitAlertes, CockpitEnsemble,
  CockpitEconomies, CockpitEvolution, types}.tsx`, `components/direction/commun.tsx`, `components/direction/direction.css` ;
  serveur `gestion_mp/api/pilotage.py:242-253`, `gestion_mp/calcul/moteur.py:2374-…` (`cockpit`),
  `gestion_mp/calcul/controles.py:1128` (`synthese`).
- **Rôles** : menu et garde **direction seule** ; route serveur `/cockpit` = `ACHATS` (les achats la lisent pour leur
  accueil et la pastille du menu).
- **Données** : GET `/cockpit` (clé `cockpit`, relu toutes les 180 s ; paramètre serveur optionnel
  `date_reference`, non utilisé par l'écran) ; pour « À faire » : `/commandes`, `/receptions`, `/bons`,
  `/operations`, `/inventaires`, `/sauvegardes` (DIRECTION), `/signalements`, `/reclamations`.
- **Adresse** : `?onglet=` lu et écrit (`replace`) ; « faire » (défaut) efface le paramètre ; valeur inconnue → « faire ».
- Chargement : « Un instant — chargement : le cockpit… » ; erreur : page « Cockpit » + message rouge (message
  d'erreur, ou « **Le cockpit est indisponible.** »).

#### 5.1 En-tête
- Titre **« Cockpit »** ; sous-titre **« Situation au {date de référence}, recalculée à chaque ouverture depuis le
  journal des mouvements. »**
- Actions (à droite) : champ **mois** (`type=month`, 160 px, infobulle « Le mois du bilan », défaut = **mois
  précédent**, maximum = mois en cours) + bouton **« Bilan du mois »**.

| Geste | Rôle | Conditions | Appel | Résultat | Refus |
|---|---|---|---|---|---|
| « Bilan du mois » | direction (route `ACHATS`) | grisé si le mois n'a pas la forme AAAA-MM ; infobulle « Le bilan du mois choisi — entrées, sorties, stock de début et de fin, production, achats — dans une page à imprimer » | ouvre `/api/bilan?mois=AAAA-MM` dans un nouvel onglet | document imprimable (§5.8) | 422 si mois mal formé |

#### 5.2 Rangée de six indicateurs (`indicateurs dir-six`, six sur une rangée même en 1366 px)
| Indicateur | Valeur affichée | Formule (serveur) / infobulle telle qu'affichée | Détail | Ton |
|---|---|---|---|---|
| Valeur du stock | `montantCourt(stock.valeur_mad)` | Σ (stock détenu = disponible [magasins hors quarantaine **+ machines**] + quarantaine) × coût unitaire (CMUP de la Valorisation, sinon prix catalogue × cours). Infobulle : « {montant exact} — les magasins, au coût moyen pondéré[, dont {valeur machine} en machine (fil monté sur les métiers, pas encore tissé).] » | « {n} matière(s) » (matières détenues, sinon toutes) + « · + {valeur machine courte} sur les métiers (info) » si > 0 | — |
| Couverture pondérée | `jours(couverture_ponderee_jours)` | Σ stock projeté>0 × prix kg × cours ÷ (Σ conso mensuelle × prix kg × cours ÷ jours par mois). Infobulle « Couverture pondérée : le stock projeté valorisé, en jours de consommation valorisée » | « pondérée par la valeur » | — |
| À commander | `montantCourt(achats.budget_a_commander_mad)` | Σ montant à commander (MAD) des matières dont la quantité à commander > 0. Infobulle = montant exact | « selon le plan d'achat » | `attention` si > 0, sinon `ok` |
| Commandé | **nombre** de bons actifs (`bc_actifs` : bons partis, non annulés, avec un reste à livrer > 0) | infobulle « {montant reste à livrer} au prix confirmé, sinon du catalogue ; au cours figé, sinon du jour[ — dont {montant estimé} estimés] » | « en cours · {montant court} · {n} en retard » (retards = `enRetard` sur `/commandes`) | `urgent` s'il y a des retards |
| Rotation du stock | « {rotation, 2 décimales} × » | base « consommation » : consommé sur les 12 derniers mois clos au CMUP (annualisé si moins d'un an d'historique) ÷ valeur du stock au CMUP ; sinon base « plan » : coût matière annuel du plan au catalogue ÷ stock au catalogue. Infobulles : « Consommé sur douze mois, au coût moyen ({montant}) ÷ valeur du stock au coût moyen » / « Coût matière annuel du plan, au catalogue ({montant}) ÷ valeur du stock au catalogue » | « par an · cycle de trésorerie {CCC} j » (CCC = DIO + DSO − DPO) | — |
| Contrôles | « {conformes} / {total} » (total = contrôles vérifiés, hors ceux que la base garantit) | synthèse des 38 contrôles | bloquants : « {anomalies} anomalies · {bloquants} bloquant(s) » ; sinon anomalies : « {n} anomalie(s), 0 bloquant » ; sinon « tout est conforme » | `critique` si bloquants, `attention` si anomalies, sinon `ok` |

Aucun indicateur du Cockpit n'est cliquable.

#### 5.3 Onglets
| Clé | Libellé | Compteur |
|---|---|---|
| `faire` | « À faire et à valider » | total des actions (`aFaire.total`), masqué si 0 |
| `alertes` | « Matières en alerte » | `nb_alertes` (nombre réel, même si la liste s'arrête à 24) — affiché même à 0 |
| `ensemble` | « Vue d'ensemble » | — |
| `evolution` | « Évolution » | — |
| `economies` | « Opportunités d'économies » | `economies.nb_opportunites` (affiché même à 0) |

#### 5.4 Onglet « À faire et à valider » (`?onglet` absent)
**Bandeau** (au-dessus, seulement sur cet onglet) :
- s'il y a des ruptures ou critiques (fond rouge) : « **{n}** matière(s) en alerte rouge : {ruptures} en RUPTURE,
  {critiques} CRITIQUE(S) — et {urgents} URGENT, {attentions} en ATTENTION. **Voir le plan d'achat →** » (`/plan-achat`) ;
  (« matières » au pluriel si n > 1, « CRITIQUES » si critiques > 1) ;
- sinon (fond vert, `calme`) : « Aucune rupture ni matière critique — {urgents} URGENT, {attentions} en ATTENTION. »

Grille de deux cartes (`grille amples`) :

**Carte « Commandes à approuver ({n}) »**, lien d'en-tête « **Toutes les commandes →** » (`/commandes?onglet=a_approuver`).
Chargement : « Un instant — chargement : les commandes… ». `Cadre taille="court"`.
| Colonne | Contenu / unité | Alignement | Remarque |
|---|---|---|---|
| Bon | n° ou « À approuver » ; note « par {créé par ou —} » | gauche | |
| Fournisseur | nom | gauche | |
| Passée le | date de commande | gauche | |
| Montant | montant dans la devise du bon (confirmé, sinon estimé) ; note « estimé, prix du catalogue » si estimé | droite | |
| Montant MAD | `montantMad` | droite | |
| (sans titre) | bouton « Examiner » (principal, infobulle « Ouvrir le bon pour le relire, puis l'approuver ou le renvoyer aux achats ») | — | |
- Ligne cliquable (`cliquable`) → fenêtre **DetailCommande** (composant des achats, inventorié ailleurs) ; à sa
  fermeture, le cockpit est relu. Pas de recherche, filtre, tri, pied.
- Vide : « **Aucune commande n'attend votre approbation.** »

**Carte « Ce qui attend une action »** (liste défilante `HAUT.court`) : une ligne par action dont le compte > 0 :
grand compte coloré (rouge/orange) · titre gras + détail · lien « {lien} → ».
| Clé | Compte | Ton | Titre | Détail | Lien (libellé → adresse) |
|---|---|---|---|---|---|
| rouges | ruptures + critiques | rouge | Matières en rupture ou critiques | « À commander sans attendre : le plan d'achat dit quoi, à qui, combien. » | Plan d'achat → `/plan-achat` |
| approuver | commandes `a_approuver` | orange | Commandes à approuver | 3 premiers « {fournisseur}, {montant MAD}[ estimé] » séparés « , » puis « … (+n) » | Commandes → `versCommandes(…, 'a_approuver')` |
| retards | `enRetard` | orange | Commandes en retard de livraison | « {n°} ({fournisseur}) »… | Commandes → `versCommandes(…, -, 'retard')` |
| prix | `prixAConfirmer` | orange | Commandes dont les prix restent à confirmer | « {n°} ({fournisseur}) »… | Commandes → `versCommandes(…)` |
| receptions | réceptions brouillon | orange | Réceptions en brouillon | « Pesées non validées : la matière n'est pas encore en stock. {fournisseur} du {date}… » | Réceptions → 1 : `/receptions?onglet=brouillon&reception={id}`, sinon `/receptions?onglet=brouillon` |
| bons | sorties brouillon | orange | Sorties vers les machines en brouillon | « Fil préparé mais pas encore sorti du stock. {métier ou magasin} du {date}… » | Sorties → 1 : `/sorties?onglet=brouillon&ordre={id}`, sinon `/sorties?onglet=brouillon` |
| operations | opérations brouillon | orange | Ouvertures, transferts, ajustements ou retours en brouillon | « {type} du {date} »… | Opérations → `/operations?onglet={type de la première}` |
| inventaires | inventaires ouverts | **rouge** | « Inventaire ouvert : magasin à l’arrêt » / « Inventaires ouverts : magasins à l’arrêt » | par inventaire : « {n°} · {magasin ou « tous les magasins »} : {comptés} / {lignes} lots comptés — aucune réception, sortie ni transfert ne passe dans ce magasin avant sa validation ou son abandon », joints « · » | Inventaire → 1 : `/inventaire?inventaire={id}`, sinon `/inventaire` |
| besoins | signalements non traités | rouge si un urgent, sinon orange | Besoins signalés par l'atelier, non traités | « {réf} : {texte} »… | Accueil des achats → `/accueil` |
| reclamations | réclamations ouvertes | orange | Réclamations ouvertes chez les fournisseurs | « {fournisseur} · {motif} »… | Réclamations → `/receptions?onglet=reclamations` |
| controles | anomalies | rouge si bloquants, sinon orange | Contrôles en anomalie | bloquants : « {n} bloquant(s) : le pilotage en est faussé. » ; sinon « Chaque contrôle dit quoi faire. » | Contrôles → `/analyse?onglet=controles` |

**Ligne Sauvegarde** (toujours présente quand l'état est lu) :
- erreur de lecture : ligne rouge « ! » « **Sauvegardes : état illisible** » + message d'erreur ;
- sinon ligne rouge « ! » « **Sauvegarde à vérifier** » si en alerte, ou ligne neutre à compte vert « ✓ »
  « **Sauvegarde à jour** » ; note = alerte du serveur, sinon « Dernière sauvegarde le {horodatage} (il y a {n} h) ·
  {nb} conservée(s). », ou « Aucune sauvegarde n'a encore été faite. » ;
- lien « **Sauvegardes →** » `/reglages?onglet=sauvegardes`.
- **En alerte** si : erreur de lecture, ou texte d'alerte serveur (« Les sauvegardes sont arrêtées : pg_dump est
  introuvable sur le serveur. », « La sauvegarde automatique a échoué : {erreur} », « Aucune sauvegarde récente. »),
  ou âge inconnu, ou âge > **26 h**. Une sauvegarde en alerte compte **+1** dans le total de l'onglet.
- Rien d'autre : « **Rien d'autre n'attend : tout est à jour.** » (si aucune action et sauvegarde à jour).

#### 5.5 Onglet « Matières en alerte » (`?onglet=alertes`)
- Carte, titre : si total > 24 : « **Matières en alerte — les {24} plus pressées sur {total}** », sinon
  « **Matières en alerte, la plus pressée d'abord — {total}** ». Liens d'en-tête « Plan d'achat → » (`/plan-achat`),
  « Stock → » (`/stock`).
- Rangée `filtres` : recherche placeholder « **Référence, fournisseur, statut… plusieurs mots** » (à la frappe, sur
  référence, nature, désignation, titrage, fournisseur, statut, statut de couverture, action) ; bouton « **Effacer les
  filtres** » si une recherche est posée ; note « **Cliquer une matière l'ouvre dans le Stock.** »
- Ordre (serveur) : couverture en jours croissante (la plus pressée d'abord) ; statuts RUPTURE, CRITIQUE, URGENT, ATTENTION ;
  **24 lignes au plus**. Pas de tri cliquable, pas de pagination, pas de pied.
- `Cadre taille="court"`, tableau serré :
  | Colonne | Contenu / unité | Alignement | Remarque |
  |---|---|---|---|
  | Référence | référence ; note « {nature} · {titrage} · {désignation} » | gauche | infobulle = référence |
  | Fournisseur | nom ou « — » | gauche | |
  | Stock projeté | « {n} kg » ; note « dont {n} sur les métiers » si stock machine | droite | infobulle d'en-tête « Stock détenu (magasins et métiers) + commandé à temps − sorties prévues pendant le délai » |
  | Conso / mois | « {n} kg » | droite | |
  | Couverture | « {n} j » ou « — » | droite | |
  | Délai | « {n} j » | droite | délai fournisseur |
  | À commander | « {n} kg » ; note « ≈ {n} ml » pour cuir/franges/ruban | droite | |
  | Statut | étiquette colorée (`tonStatut`) avec le libellé emoji (« 🔴 CRITIQUE »…) | gauche | infobulle d'en-tête « Le stock projeté face au seuil d'alerte (délai du fournisseur, sécurité, stock minimum) » ; infobulle de cellule si le statut de couverture diffère : « Statut de couverture (jours face aux réglages critique et ATTENTION) : {statut} » |
  | Action | si fournisseur et quantité > 0 : bouton « **Préparer la commande** » (infobulle « {action lisible} : ouvrir la préparation de commande ») ; sinon note = action lisible ou « — » | gauche | le clic ne déclenche pas la ligne |
- **Action lisible** : sans emoji, « Créer BC - X » → « Commander chez X », « BC » → « commande ».
- Ligne cliquable (infobulle « Ouvrir cette matière dans le Stock ») → `/stock?onglet=matieres&q={référence}`.
- Vide : « **Aucune matière ne correspond à cette recherche.** » (si alertes mais recherche vide de résultats) ;
  « **Aucune matière en alerte.** »
- « Préparer la commande » ouvre la fenêtre **PreparationCommande** (composant achats, inventorié ailleurs) pour ce
  fournisseur ; à la création, fermeture et navigation vers `/commandes?onglet=brouillon&commande={id de la première}`.

#### 5.6 Onglet « Vue d'ensemble » (`?onglet=ensemble`)
Grille de deux cartes.

**Carte « Les matières par statut »** (lien « Stock → » `/stock`) :
- Histogramme (barres arrondies, 48 px max, grille pointillée horizontale, axe Y entier) :
  RUPTURE `#2d3440`, CRITIQUE `#a92c2c`, URGENT `#a1560b`, ATTENTION `#c99a2e`, OK `#146c44`,
  « Sans consommation » `#aab3c0` ; infobulle « {n} matière(s) » / « Nombre ».
- Liste :
  - « Classement par valeur consommée : {A} matière(s) en A (l'essentiel de la dépense), {B} en B, {C} en C. »
  - « {mono} matière(s) n'ont qu'un seul fournisseur possible ; {multi} en ont plusieurs. » (sourcing « 🔴 MONO-SOURCE » / « ✅… »)
  - « Stock dormant (ni sortie ni entrée depuis {seuil} jours) : {n} matière(s), {montant} immobilisés, soit {part}
    de la valeur du stock. » (valeur dormante = stock détenu × CMUP des matières dormantes ; part = ÷ valeur du stock)

**Carte « Le budget à commander, par devise »** (lien « Plan d'achat → ») :
| Colonne | Contenu | Alignement |
|---|---|---|
| Devise | code | gauche |
| Matières | nombre de matières à commander dans cette devise | droite |
| Montant MAD | Σ montant à commander MAD | droite |
| Part | montant ÷ total, % 1 décimale | droite |
Vide : « **Rien à commander.** » Puis liste :
- « Coût matière : {annuel} par an, {mensuel} par mois, au plan de production. »
- « Rotation du stock : {r} fois par an — le stock représente {DIO} j de consommation ({base}). » où base =
  « {montant} consommés par an sur les douze derniers mois, au coût moyen, face au stock au coût moyen » ou
  « pas encore de consommation : le plan au prix du catalogue, face au stock au catalogue ».
  DIO = valeur rotation ÷ (coût rotation ÷ 365).
- « Cycle de trésorerie : {CCC} = stock {DIO} + clients {DSO} − fournisseurs {DPO} (délai de paiement moyen, pondéré
  par les montants commandés). » DSO = paramètre ; DPO = Σ délai de paiement du fournisseur × montant des bons
  partis non annulés ÷ total (à défaut : moyenne des délais des fournisseurs).
- « {n} fournisseur(s) référencé(s). »

#### 5.7 Onglet « Évolution » (`?onglet=evolution`)
- **Données** : GET `/indicateurs/historique` (ACHATS) → une « photo » par jour : `jour, valeur_stock_mad,
  couverture_jours, ruptures, critiques, urgents, a_commander_mad, commandes_en_cours_mad, otif_moyen`.
- Chargement « Un instant — chargement : l'historique des indicateurs… » ; erreur → message rouge.
- **Carte 1** : en-tête = **Bascule** (sous-vues) + bouton direction **« Photographier aujourd'hui »**.
  | Sous-vue | Libellé | Séries (couleur) | Axe Y |
  |---|---|---|---|
  | argent | « Valeur et achats » | Valeur du stock `#2a78d6`, À commander `#c99a2e`, « Commandé, à livrer » `#1baf7a` | « {n} M » (millions, 1 décimale) |
  | alertes | « Alertes » | RUPTURE `#2d3440`, CRITIQUE `#a92c2c`, URGENT `#a1560b` | entiers |
  | couverture | « Couverture » | « Couverture pondérée (jours) » `#2a78d6` | entiers |
  | otif | « OTIF » | « OTIF moyen » `#1baf7a` | % sans décimale |
  Courbe linéaire, points de rayon 3, axe X = dates (échelle de temps), légende, infobulle (date ; valeur formatée :
  montant MAD / « n j » / % / nombre), trous reliés.
  - Moins de 2 photos : message bleu « L'évolution repose sur **une photo par jour** des indicateurs, prise par le
    serveur (tâches de fond) depuis sa mise en service — l'année reprise de l'ERP Fil n'en a pas. » + « Une seule photo
    pour l’instant : la courbe se dessinera dès la photo de demain. » ou « Aucune photo encore. » + (direction)
    « « Photographier aujourd'hui » prend celle du jour tout de suite. »
  - Aucune photo : pas de graphique.
- **Carte 2** « **Les photos, la plus récente d'abord ({n})** » (`Cadre court`) :
  | Colonne | Contenu | Align. |
  |---|---|---|
  | Jour | date | gauche |
  | Valeur du stock | montant MAD | droite |
  | Couverture | n j | droite |
  | Rupt. · crit. · urg. | « r · c · u » | droite |
  | À commander | montant MAD | droite |
  | OTIF | % sans décimale ou « — » | droite |
  Vide : « **Aucune photo.** »
| Geste | Rôle | Conditions | Appel | Succès | Refus |
|---|---|---|---|---|---|
| « Photographier aujourd'hui » | direction (bouton absent sinon ; route `DIRECTION`) | grisé pendant l'envoi ; infobulle « Prendre tout de suite la photo du jour (le serveur la prend aussi seul, chaque jour) » | POST `/indicateurs/photographier` | « La photo d'aujourd'hui est prise. » ; historique relu | refus de rôle |
| Bascule (4 vues) | tous ceux qui voient l'onglet | — | — | change les séries | — |

#### 5.8 Onglet « Opportunités d'économies » (`?onglet=economies`)
- Carte, titre « **Les plus fortes opportunités d'économies — {n} au total, {montant} par an** » ; lien
  « **Toutes les opportunités →** » (`/analyse?onglet=opportunites`).
- Note : « Un fil de même composition, même type et même titrage s'achète moins cher ailleurs, à la même époque, au coût
  rendu usine (droits, fret, transit compris quand le dossier d'importation est saisi). C'est une opportunité à négocier,
  pas une décision : la qualité réelle et la disponibilité ne se lisent pas ici. »
- Les **5** plus fortes (serveur `economies.top`, comparaison à **même couleur** `meme_couleur=True`). `Cadre court`.
  | Colonne | Contenu | Align. |
  |---|---|---|
  | Référence · fournisseur actuel | référence ; note fournisseur | gauche |
  | Composition × titrage | « {composition ou nature} · {type de fil} · {titrage} » ou « — » | gauche |
  | Prix actuel (MAD / kg) | 2 décimales ; note « {base} du {date} » (base = « coût rendu » ou « prix facture ») ou « catalogue, non daté » | droite |
  | Comparable moins cher · chez | référence alternative ou « — » ; note fournisseur | gauche |
  | Son prix (MAD / kg) | idem | droite |
  | Écart | étiquette ambre « −{x,x %} » | droite |
  | Conso / an (kg) | nombre | droite |
  | Économie / an | montant MAD en gras | droite |
  Lignes non cliquables. Vide : « **Aucune opportunité d'économie détectée.** »
- Formule : (prix actuel − prix du comparable le moins cher) × consommation annuelle ; coût rendu usine = coût hors TVA
  du dossier d'importation s'il existe, sinon prix facture × cours figé de la commande, sinon × cours du jour.

#### 5.9 Document imprimable « Bilan du mois » — GET `/api/bilan?mois=AAAA-MM` (ACHATS)
- Titre de page « Bilan {MM/AAAA} » ; bouton « Imprimer » (masqué à l'impression) ; `h1` « Bilan matières premières —
  {MM/AAAA} » ; nom de la société.
- « **Le mois en chiffres** » (cases) : Stock au début (kg, MAD) ; Stock à la fin (kg, MAD) ; [Stock d'ouverture saisi —
  « entré dans le mois », seulement s'il y en a] ; Entrées (réceptions) (kg ; « {MAD} MAD, hors réceptions annulées ») ;
  Sorties vers les machines (kg ; « dont {kg} revenus · coût net {MAD} MAD ») ; Tissé (m² ; « {n} ordre(s) ») ;
  Commandes émises (n ; « {n} réception(s) ») ; Livraisons parfaites (OTIF) (% ; « sur {n} réception(s) ») ;
  Ajustements (kg 1 déc. ; « retours fournisseur {kg} »).
- Paragraphe : valeurs au CMUP (celles de la Valorisation à ces dates) ; à une date passée le fil monté n'est pas compté ;
  « Stock à la fin = début + entrées + ouvertures − sorties + retours des machines − retours fournisseur + ajustements +
  annulations. **Annulations (contre-passations) datées du mois : {kg}** (détail par type) — elles défont des écritures,
  parfois d'un mois précédent, et ne comptent ni en sorties ni en entrées. »
- « **Fabrication, qualité par qualité** » : Qualité | m² tissés ; vide « Aucun ordre ce mois-ci. »
- « **Les plus grands écarts entre la recette et le réel** » : Ordre | Qualité | Prévu (kg) | Sorti net (kg) | Écart (%) ; vide « Aucun. »
- « **À la fin du mois** » : « {n} matière(s) en rupture, {n} critique(s). »

#### 5.10 Notions métier (Cockpit)
CMUP, valeur du stock (magasins + quarantaine + machines), stock en machine / sur les métiers, couverture pondérée,
budget à commander, bons actifs (reste à livrer > 0), montant estimé (prix catalogue) vs confirmé, cours figé, rotation
(base consommation / plan), DIO, DSO, DPO, cycle de trésorerie (CCC), classes ABC, mono-source / multi-source, stock
dormant (seuil en jours), exposition par devise, statut au seuil vs statut de couverture, stock projeté, action
conseillée, opportunité d'économies (même composition, type, titrage, couleur ; coût rendu usine), OTIF, photo
quotidienne des indicateurs, contrôles (conformes / vérifiés, garantis, anomalies, bloquants, score), sauvegarde
(26 h), inventaire ouvert = magasin à l'arrêt, approbation des commandes au-delà du seuil.

---

### 6. Mode d'emploi — `/guide` (`?onglet=regles|roles|pas|calculs|analyse|ecrans|telephone`)

- **Fichiers** : `pages/Guide.tsx`.
- **Rôles** : tous (menu « Aide › Mode d'emploi », pas de garde). Seule différence : l'onglet « L'analyse » n'a pas de
  liens et affiche une autre phrase pour l'alimentation. Les liens vers des écrans interdits ramènent à l'accueil avec
  le message « écran réservé ».
- **En-tête** : titre « **Mode d'emploi** », sous-titre « **Les règles, qui fait quoi, les gestes pas à pas, les calculs, et
  où est passé chaque écran de l'ERP Fil.** »
- **Adresse** : `?onglet=` lu et écrit (`replace`) ; « regles » (défaut) efface le paramètre.
- Le texte défile **dans sa carte** (`Defile` : `max-height = HAUT.dialogue` dans une carte, `HAUT.page` pour les grilles de cartes).
- Liens internes : texte bleu gras.

#### 6.1 Onglets
| Clé | Libellé | Présentation |
|---|---|---|
| regles | « Les règles » | carte « Les règles qui tiennent le stock juste », liste |
| roles | « Qui fait quoi » | trois cartes (Direction, Achats, Alimentation des machines) |
| pas | « Pas à pas » | une carte par procédure, lien « Ouvrir → » en en-tête, étapes numérotées |
| calculs | « Les calculs » | carte « Les calculs à connaître », tableau Grandeur / Comment elle est obtenue |
| analyse | « L'analyse » | carte « L'analyse : une question par onglet », tableau |
| ecrans | « Les écrans de l'ERP Fil » | carte « Où est passé chaque écran de l'ERP Fil », tableau 3 colonnes |
| telephone | « Le téléphone » | carte « Gestion MP sur le téléphone », liste numérotée |

#### 6.2 « Les règles » — 14 règles (titre en gras + explication)
1. **Le journal des mouvements est la seule écriture de stock.** Tout (stock détenu, couverture, valeur, plan) se
   recalcule depuis lui à chaque affichage ; soldes par lot/magasin = sa somme ; contrôle « Soldes et journal » (Analyse › Contrôles).
2. **Brouillon, puis validation.** Tout document (commande, réception, sortie, ouverture, transfert, ajustement, retour,
   inventaire) naît brouillon (modifiable, supprimable, sans effet sur le stock) ; la validation l'écrit ; le numéro
   (REC-…, OF-…, BC-…) n'est donné qu'à la validation ou à l'envoi (pas de trou) ; avant : « Brouillon » (au plus un n°
   interne de saisie), bon soumis à la direction : « À approuver ».
3. **Un document validé ne s'efface pas : il s'annule (contre-passation).** Écriture inverse datée comme l'original,
   signée par qui annule ; les deux restent ; les annulations reprises de l'ERP Fil portent la date de reprise (le Bilan
   du mois les compte à part, ligne « annulations »).
4. **Le stock se tient en kilos ; la commande se passe en conditionnements.** Unité d'achat et contenance (déduite :
   palette si kg/bobine et bobines/palette connus, sinon bobine, sinon kilo) ; la préparation parle palettes et conteneur ;
   le bon écrit « 12 × Palette de 900 kg » ; cuir, franges, ruban aussi en kilos.
5. **Le cuir, les franges, le ruban : des kilos en stock, des mètres dans la recette.** Pesés, sortis, comptés, commandés
   en kilos ; densité (kg/ml) obligatoire ; prix au kilo (défaut) ou au mètre, lu au kilo (prix au mètre ÷ densité) ;
   recette en mètres par m² → kilos par m² via la densité ; mètres indicatifs « 14,3 kg ≈ 1 020 ml » sur fiche, stock,
   sortie, besoins, plan, bon de commande.
6. **Le prix de la facture n'est pas le coût du fil.** Droits, fret, transit, port, banque : un dossier d'importation
   **par facture** (ouvert depuis la réception), frais répartis à la valeur ou au poids selon le poste ; TVA hors coût :
   **Coût hors TVA** (coût de revient) valorise le stock, **Coût TTC** = décaissé.
7. **Le lot sur toutes les écritures, l'ordre sur les sorties.** Lot = d'où vient ; ordre (OF-…) = dans quoi c'est
   parti ; « Lot interne » pour un fournisseur sans n° de lot.
8. **Une référence de fil se compose de quatre parties.** Composition, type de fil, titrage, couleur (lien
   « Classification » `/catalogue?onglet=classification`).
9. **Le stock est en magasin ou en machine.** Fil monté = mètres × densité × kg d'une bobine × pourcentage ; sorti par
   un ordre mais pas tissé = stock « en machine » ; stock et valeur = magasins + machines ; on ne rachète pas ce qui est
   dans le cantre ; détail sur fiche matière, Cockpit, Valorisation, Métiers ; retour au magasin par un retour des
   machines ; fil monté sans sortie = encore compté au magasin (contrôle C25).
10. **La devise appartient au prix, pas au fournisseur.** Jamais d'addition entre devises ; un bon par devise ; totaux en
    MAD ; cours figé à la confirmation des prix ; dossier au cours de la banque.
11. **Deux horloges.** Historique figé ; projection glissante sur 12 mois à partir d'aujourd'hui.
12. **Le stock ne passe jamais sous zéro.** À plusieurs sur la même palette, le second est refusé s'il ne reste pas
    assez ; la **quarantaine** est détenue mais pas disponible (ni proposée, ni dans la couverture) ; libération par
    transfert motivé.
13. **Les dates tiennent.** Pas d'écriture dans le futur ; période close (Réglages › Paramètres › Société) ; magasin
    compté figé pendant l'inventaire ; un ordre ne se valide pas avant le dernier ordre validé.
14. **Chaque geste est signé.** Colonne « Par » ; lien « Journal des actions » (`/reglages?onglet=journal`) ; le
    serveur refuse ce que le menu cache.

#### 6.3 « Qui fait quoi »
- **Direction** : voit et peut tout ; lien « Cockpit » (commandes à approuver, ruptures, retards, prix à confirmer,
  brouillons, contrôles, sauvegarde) ; approuve les commandes au-delà du seuil (le bon s'ouvre en entier, puis
  « Approuver ») ou les renvoie ; règle les « Réglages » (paramètres de calcul, devises, magasins, postes de frais, codes
  douaniers, comptes, sauvegardes, journal des actions, serveur, accès téléphone), règle les métiers (laize, étages,
  densité) et saisit le plan de production.
- **Achats** : plan d'achat, commandes, réceptions (poids des bobines, archive des pesées), importations et coût de
  revient, inventaire, ouvertures / transferts / ajustements / retours au fournisseur ; matières, classification,
  fournisseurs ; qualités et recettes en lecture ; production en lecture ; lien « Analyse » (prix, opportunités
  d'économies, fournisseurs, valorisation, coût de revient, contrôles) ; n'ont pas les réglages, les comptes, les
  sauvegardes, ni l'approbation des commandes.
- **Alimentation des machines** : au téléphone (lien « écran atelier ») : envoyer aux machines (qualité et m², fils et
  lots proposés), retour des machines, trouver un lot (mots ou QR), déplacer un lot ; au bureau : sorties vers les
  machines, transferts, stock et lots, métiers à tisser (monter les fils), production en lecture ; ne voit ni prix, ni
  budgets, ni pilotage des achats.

#### 6.4 « Pas à pas » — 9 procédures (titre · lien « Ouvrir → » · étapes)
1. **Passer une commande depuis le plan** (`/plan-achat`) : Plan d'achat › Par fournisseur (fournisseurs par budget,
   matières par urgence) ; « Préparer la commande » (quantité suggérée en kilos et en unité de commande, palettes par
   conteneur) ; créer le bon (sans prix, un par devise, en brouillon) ; Commandes › Brouillons : relire puis « Envoyer »
   (au-delà du seuil, la direction approuve d'abord) ; au retour du fournisseur « Saisir les prix » puis « Confirmer ces
   prix » (au bon et au catalogue, cours figé) ; suivre l'expédition (proforma, acompte, embarquement, ETA, port,
   dédouanement, arrivée usine ; l'ETA remplace la date prévue dans la projection).
2. **Commander sans passer par le plan** (`/commandes`) : « Nouvelle commande », fournisseur ; la préparation s'ouvre
   avec la suggestion (ajuster ou tout mettre à zéro) ; ajouter dans le brouillon les matières manquantes.
3. **Réceptionner une livraison** (`/receptions`) : Nouvelle réception (fournisseur ou n° de bon, cocher les bons du
   camion) ; par lot : numéro (ou « Lot interne »), Annoncé BL (kg), pesée (fait foi), palettes et bobines, magasin ;
   conforme → magasin, sous réserve → quarantaine, refusé → n'entre pas ; Enregistrer = brouillon (se remet à jour seul),
   Valider = entrée en stock + prix ; imprimer les étiquettes QR.
4. **Monter un fil sur un métier** (`/metiers`) : choisir le métier ; l'étage, le fil, mètres montés, pourcentage ;
   bobines = mètres × densité × pourcentage, poids = bobines × kg / bobine (« Sur les métiers », stock en machine) ; deux
   fils à 60/40 % n'occupent qu'une fois la laize ; le fil monté doit avoir été sorti (sinon contrôle C25).
5. **Sortir de la matière pour un ordre** (`/sorties`) : téléphone « Envoyer aux machines » / bureau « Nouvelle
   sortie » ; qualités en service et m² → fils et kilos des recettes, lots les plus anciens présents à la date de l'ordre ;
   corriger au réel (kg, bobines, palettes), fil hors recette ; Valider (stock baisse, n° OF) ; retour contre l'ordre,
   daté au plus tôt du jour de l'ordre ; annuler l'ordre annule ses retours (repris de l'ERP Fil compris).
6. **Savoir ce qu'un fil a coûté** (`/analyse?onglet=revient`) : Analyse › Coût de revient (ou Importations), recherche
   multicritère ; combinaisons « PES + 1500 », « + Ajouter cette combinaison », « PP + 1800 » ; lire Achat, Charges hors TVA,
   Coût hors TVA au kilo, TVA, Coût TTC ; Analyse › Matrice puis « Courbe ».
7. **Retrouver d'où vient un fil** (`/stock?onglet=lots`) : QR ou mots → fiche du lot ; Stock › Lots › « Suivre » ;
   Stock › Ordres de fabrication ; un tapis qui revient : ordre → lots → autres ordres.
8. **Faire l'inventaire** (`/inventaire`) : Ouvrir (théorique figé, mouvements du magasin suspendus) ; compter en
   palettes, bobines ou kilos, écart au-delà de la tolérance justifié ; Valider (un ajustement par écart).
9. **Le point hebdomadaire** (`/cockpit`) : Contrôles (aucun bloquant ?) ; Cockpit ou Accueil ; Matrice et
   Opportunités ; Plan d'achat et Échéancier ; Réglages › Sauvegardes (< 1 jour) ; début de mois : « Bilan du mois » et Évolution.

#### 6.5 « Les calculs » — 21 grandeurs (tableau « Grandeur | Comment elle est obtenue »)
Besoin matière du mois ; Prix au kilo ; Besoin retenu (coefficient réel / plan des 3 derniers mois clos, borné 0,5–1,5,
pas de baisse en rupture, fil remplaçant hérite du coefficient, fil hors recette prévu sur ses sorties sauf fil sorti des
recettes dans l'année) ; Stock détenu (magasin = courant + quarantaine, machine ; disponible = magasins sans quarantaine
+ machines) ; Stock projeté (disponible + commandé attendu dans le délai − demande pendant le délai ; brouillon / à
approuver exclus) ; Sorties prévues ; Seuil d'alerte (max de : stock minimum plafonné à N mois, couverture minimum ×
(1 + marge), jours de sécurité ABC ; délai déjà retiré) ; Statut (au seuil) ; Statut de couverture ; Couverture
(projeté ÷ conso journalière ; pondérée par la valeur au Cockpit) ; Quantité à commander (formule complète, minimum de
commande, arrondi au conditionnement, rien sous le gramme, pas de rachat d'une matière désactivée / d'un fournisseur
désactivé / non consommée) ; Classe ABC (80 % / 95 %, réglables) ; Classe XYZ (CV < 0,25 X, < 0,5 Y, sinon Z) ; Valeur du
stock (CMUP) ; Coût hors TVA d'une marchandise ; Opportunité d'économies ; OTIF (à l'heure sur la date promise, complète
à la tolérance, conforme ; score = OTIF × 60 + jusqu'à 20 points retours (0 dès 5 %) + jusqu'à 20 délai court) ;
Rotation du stock ; Cycle de trésorerie. Pied : « Les seuils, taux et tolérances se règlent dans Réglages › Paramètres
(direction) ; chaque changement est daté et recalcule tout le pilotage. »

#### 6.6 « L'analyse » — 9 lignes
Note : achats/direction « Menu « Analyse ». Chaque liste s’exporte en Excel ; chaque onglet a son adresse, à garder en
favori. » ; alimentation « L’analyse est réservée aux achats et à la direction. » (et noms sans lien).
Lignes (nom → `/analyse?onglet=…`) : Valorisation (`valorisation`), Matrice (`matrice`), Prix payés (`historique`),
Opportunités (d’économies) (`opportunites`), Fournisseurs (`fournisseurs`), Coût de revient (`revient`), Échéancier
(`echeancier`), Contrôles (`controles` — « Trente-huit vérifications de cohérence »), Production (`production`), chacune avec sa phrase.

#### 6.7 « Les écrans de l'ERP Fil » — 25 lignes (Écran de l'ERP Fil | Dans Gestion MP (lien) | Ce qui a changé)
Cockpit → Cockpit (direction) · Accueil (achats) ; Stock → Stock, lots & mouvements › Par matière ; Plan d'achat ;
Production & besoins ; Métiers à tisser ; Mouvements (journal) → Stock › Mouvements de stock ; Mouvements (saisie) →
Ouvertures, transferts, ajustements ; Bon de sortie → Sorties vers les machines · écran atelier ; Commandes ; Réceptions ;
Lots & traçabilité → Stock › Lots · Ordres de fabrication ; Importations ; Coût de revient → Analyse › Coût de revient ;
Inventaire ; Catalogue → … › Matières ; Classification des fils ; Fournisseurs ; Qualités & recettes ; Valorisation du
stock → Analyse › Valorisation ; Prix & matrice → Analyse › Matrice · Prix payés · Opportunités ; Contrôles ; Paramètres →
Réglages (Paramètres, Devises, Magasins, Frais, Douane, Comptes, Sauvegardes, Journal des actions, Courriel (du lundi),
Serveur, Téléphone) ; Guide → Mode d'emploi ; — (nouveau) → Réglages › Comptes · Journal des actions ; — (nouveau) → Écran
atelier (téléphone). Pied : « Un lien vers un écran que votre rôle ne voit pas vous ramène à votre accueil. »

#### 6.8 « Le téléphone » — 4 étapes
Wi-Fi : ouvrir l'adresse du serveur, ex. `http://192.168.1.20:8030` (« Réglages › Accès téléphone donne l'adresse exacte
et un QR ») ; 4G/5G : Tailscale sur serveur et téléphone, même compte, `http://nom-du-serveur:8030`, jamais exposé sur
Internet ; *Partager › Sur l'écran d'accueil* (iPhone) / *⋮ › Ajouter à l'écran d'accueil* (Android) ; l'appareil photo
lit les QR des palettes et ouvre la fiche du lot.

Gestes : changer d'onglet ; liens. Aucun geste d'écriture.

---

### 7. Page du lot au bureau — `/lot/:id`

- **Fichiers** : `pages/Lot.tsx` ; fiche `FicheLotBureau` et `Liberation` dans `pages/Stock.tsx:579-736` ;
  `useFicheLot`, `STATUTS_LOT` dans `pages/atelier/LotFiche.tsx` ; `quantite` dans `pages/atelier/commun.tsx:160`.
- **Accès** : l'étiquette QR mène à `/lot/{id}` ; **au téléphone** (≤ 700 px) l'adresse est redirigée vers
  `/atelier/lot/{id}` (fiche atelier, autre inventaire) ; **au bureau**, cette page. Lien « Page du lot » depuis la
  fenêtre de lot du Stock.
- **Rôles** : tous (pas de garde ; GET `/lots/{id}` = `acteur`). Le serveur masque les prix des mouvements pour
  l'alimentation. Le lien vers la réception et la libération de quarantaine : `peut('achats')`.
- **Données** : GET `/lots/{id}` (clé `['lot', id]`).
- Chargement « Un instant — chargement : le lot… » ; pas de données (404 **ou toute erreur**) : « **Lot introuvable.** »

#### En-tête
- Titre « **Lot {numéro}** » ; sous-titre « {référence} · {rôle} · {fournisseur} » + étiquette de statut ;
  action « **Imprimer l'étiquette** » → ouvre `/api/lots/etiquettes?ids={id}`.
- Statuts du lot (calculés sur les soldes) : `disponible` « Disponible » (vert), `partiel` « En partie en quarantaine »
  (ambre), `quarantaine` « En quarantaine » (rouge), `epuise` « Épuisé » (gris).

#### Indicateurs
| Indicateur | Valeur | Détail | Ton |
|---|---|---|---|
| Reste | `quantite(total)` « 12,5 kg » (2 décimales sous 10 kg ; « ≈ n ml » pour cuir/franges/ruban) | « {n} bobines » (arrondi total ÷ kg/bobine) si connu | `attention` si statut quarantaine |
| Disponible | quantité hors quarantaine | libellé du statut | — |
| Entré · sorti | « {entré, entier sans unité} · {sorti en kg, 0 décimale} » | « dernier mouvement le {date} » | — |
| kg / bobine | 2 décimales ou « — » | « {n} bobines / palette » | — |
| Entré le | date d'entrée | fournisseur | — |

#### Ligne réception, soldes, liens
- Si une réception validée a apporté le lot : note « Reçu par {n° REC, lien `/receptions?reception={id}` pour
  achats/direction, texte sinon} le {date}[ · BL {n°}][ · facture {n°}] · pesé {quantité} ».
- Rangée : chaque solde « **{code magasin}** {quantité} » (le magasin de quarantaine en étiquette rouge) ; « Ordres
  servis : » liens `OF-…` → `/sorties?ordre={id}` ; à droite bouton-lien « **Où ce lot est-il allé ?** » (infobulle « D'où
  vient ce lot, quels ordres de fabrication il a servis, et quand ») → `/stock?onglet=lots&lot_id={id}&lot={numéro}`.

#### Bloc « Libération de quarantaine » (achats/direction, si un solde en quarantaine > 0,0005 kg)
- Titre « **En quarantaine : {quantité} dans « {magasin} »** » ; liste « vers {code} » (magasins actifs hors
  quarantaine ; défaut : le premier) ; champ « Ce qui a été contrôlé (obligatoire) » (300 car. max, ≥ 3 caractères).
| Geste | Rôle | Conditions / infobulle | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|
| « Libérer » | achats, direction | grisé sans destination, commentaire < 3 caractères ou envoi en cours ; infobulle « Écrire d’abord ce qui a été contrôlé » ou « Transfert « Libération de quarantaine », validé tout de suite » | sur place : « Libérer {quantité} : la matière devient disponible pour les machines ? » · « Non » · « Oui, libérer » | POST `/operations` {type transfert, date du jour usine, motif « Libération de quarantaine », commentaire, une ligne : tout le solde du **premier** magasin de quarantaine → destination} puis POST `/operations/{id}/valider` ; si la validation échoue, DELETE `/operations/{id}` | « {n° TRF-…} : {quantité} libérés, disponibles pour les machines. » ; stock relu partout | « Libérer une quarantaine est une décision des achats, après contrôle de la matière. » (403) ; « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». » ; erreurs de date (période close, futur), d'inventaire ouvert… |

#### Tableau des mouvements (`Cadre taille="court"` sur la page ; `dialogue` dans la fenêtre du Stock)
| Colonne | Contenu | Align. | Remarque |
|---|---|---|---|
| Date | date d'effet | gauche | |
| Mouvement | libellé ; étiquette grise « annulation » si contre-passation ; « · {motif} » | gauche | |
| Document | n° du document, lien selon le rôle : sortie → `/sorties?ordre=`; opération → `/operations?operation=` (achats) ou l'ordre (`/sorties?ordre=`) pour l'alimentation ; réception → `/receptions?reception=` (achats) ; inventaire → `/inventaire?inventaire=` (achats) | gauche, chasse fixe | |
| Magasin | code | gauche | |
| Quantité | « +12,5 » / « −3,0 » (1 décimale, signe, vert/rouge) | droite | sans unité |
| Par | auteur | gauche | |
Ordre : le plus récent d'abord. Infobulle de ligne = commentaire. Pas de recherche, tri, pagination, pied, message vide.

#### Document imprimable « Étiquettes de lots » — GET `/api/lots/etiquettes?ids=…` (acteur)
Format **100 × 70 mm**, une page par lot, bouton « Imprimer » (masqué à l'impression) : QR (34 mm) de
`{adresse pour téléphones}/lot/{id}` ; référence (13 pt gras) ; « Lot {numéro} » (16 pt très gras) ; fournisseur ;
« Entré le {JJ/MM/AAAA} » ; « {kg[ ≈ ml]} à l'impression » ; « N° {id} » ; si quarantaine : cadre « **QUARANTAINE —
NE PAS SORTIR** ». Aucun lot valide : « Aucun lot à étiqueter. » (404).

#### Notions
Lot, reste, disponible, quarantaine (détenue, non disponible), épuisé, kg / bobine, bobines / palette, ordres servis,
traçabilité, libération de quarantaine (décision des achats, motif imposé, commentaire de contrôle), annulation
(contre-passation), étiquette QR.

---

### Incohérences et anomalies repérées

1. **Nouvel essai des requêtes inopérant** — `main.tsx:15` teste `/40[134]/` sur `e.message`, or le message est le
   `detail` français du serveur (« Cette action est réservée à… ») : un 403/404 est quand même retenté une fois ; il
   faudrait tester `e.statut` (`lib/api.ts:10-16`).
2. **Service worker jamais enregistré sur le téléphone** — `main.tsx:32` exige `window.isSecureContext` ; l'accès
   téléphone documenté est en `http://192.168.x.x:8030` ou `http://nom:8030` (pas sécurisé) : l'installation « comme une
   application » repose sur le seul manifeste (Android Chrome ne propose pas l'installation PWA sans SW).
3. **QR au téléphone pour les achats** — `App.tsx:167` redirige `/lot/:id` vers `/atelier/lot/:id` pour **tout** rôle au
   téléphone, mais `/atelier/*` est réservé à l'alimentation (`App.tsx:163`) : un acheteur qui scanne une étiquette avec
   son téléphone atterrit sur `/accueil`, sans la fiche ni message.
4. **Accueil de l'alimentation au bureau incohérent** — `App.tsx:170` envoie `/` vers `/sorties` alors que `accueilDe`
   (`App.tsx:99`) et son commentaire donnent `/accueil` (« ses grands boutons ») ; le comportement dépend de l'adresse d'entrée.
5. **Connexion automatique à 4 chiffres** — `pages/Connexion.tsx:100` soumet dès 4 chiffres pour l'alimentation, alors que
   le serveur accepte un code de 4 caractères **au moins**, chiffres ou non (`gestion_mp/securite.py:50-52`,
   `comptes.py` « au moins {n} caractères ») : un code de 5+ chiffres échoue toujours et compte un essai (blocage après 5).
6. **Session perdue sans explication** — `App.tsx:118-122, 145` : un 401 renvoie à la connexion sans dire « session
   expirée » ni « compte désactivé ».
7. **Libellé du bandeau d'abandon** — `REGLES-ECRAN.md:39` annonce « Abandonner les modifications ? » ; l'écran dit
   « Des modifications ne sont pas enregistrées. Les abandonner ? » (`components/ui.tsx:327`).
8. **« Valeur du stock » contradictoire** — infobulle « les magasins, au coût moyen pondéré, **dont** {x} en machine » et
   détail « **+** {x} sur les métiers (info) » (`pages/Cockpit.tsx:90-97`) ; le serveur **inclut** la machine dans
   `valeur_mad` (`stock_disponible` contient `stock_machine`, `gestion_mp/calcul/moteur.py:1188`, `2391-2401`). Le Mode
   d'emploi dit l'inverse (« appliqué au stock détenu (les magasins) … Le fil monté … valorisé à part »,
   `pages/Guide.tsx:282-285`).
9. **Trois comptes différents de « matières en alerte »** — pastille du menu Stock = ruptures + critiques
   (`App.tsx:191`), Accueil = ruptures + critiques + **urgentes** (`pages/Accueil.tsx:247`), Cockpit « alerte rouge » =
   ruptures + critiques, onglet « Matières en alerte » = ruptures + critiques + urgentes + attentions.
10. **Inventaires ouverts** — l'Accueil ne montre que le premier inventaire ouvert (`pages/Accueil.tsx:245`, `find`), le
    Cockpit les compte tous (`CockpitAFaire.tsx:59`).
11. **« En retard » redéfini dans Commandes** — `lib/commandes.ts` dit « une seule définition », mais `pages/Commandes.tsx:67`
    garde sa propre `estEnRetard` (sans exclure brouillons/annulées/hors suivi) pour le filtre `?filtre=retard` ouvert
    depuis l'Accueil et le Cockpit : le nombre de la liste peut différer du compteur qui y mène.
12. **Classe interdite** — `pages/Accueil.tsx:51` utilise `fiche clic` ; `REGLES-ECRAN.md:47-48` : « Plus de `dir-clic` ni de `clic` ».
13. **Recherche des alertes limitée à 24** — `CockpitAlertes.tsx:28` filtre seulement les 24 lignes envoyées par le serveur
    (`moteur.py` `alertes[:24]`) : « Aucune matière ne correspond à cette recherche » peut cacher une matière en alerte au-delà du 24e rang.
14. **Mètres indicatifs incomplets** — `CockpitAlertes.tsx:87-93` : Stock projeté, « dont … sur les métiers » (sans
    unité) et Conso / mois sans « ≈ ml » pour cuir/franges/ruban, contrairement à `REGLES-ECRAN.md:55-60` (seul « À commander » les montre).
15. **Unités manquantes page du lot** — « Entré · sorti » : entré sans « kg », sorti avec (`pages/Stock.tsx:589`) ;
    colonne « Quantité » sans unité (`pages/Stock.tsx:617`) ; « dont {n} sur les métiers » sans unité (Cockpit).
16. **Page du lot : toute erreur = « Lot introuvable. »** — `pages/Lot.tsx:13` (panne réseau ou refus confondus avec un lot inexistant).
17. **Libération partielle silencieuse** — `pages/Stock.tsx:653` ne libère que le **premier** magasin de quarantaine si un
    lot est en quarantaine dans deux magasins.
18. **Vocabulaire Réglages** — le Mode d'emploi (`pages/Guide.tsx:229, 572`) et `docs/MISE-EN-SERVICE.md:33` disent
    « Réglages › Accès téléphone », l'onglet s'appelle « Téléphone » (`pages/Reglages.tsx:76`). Menu « Qualités et
    recettes » (`App.tsx:77`) vs « Qualités & recettes » dans le Mode d'emploi (`Guide.tsx:376`).
19. **Mode d'emploi : transferts au bureau pour l'alimentation** — `Guide.tsx:250` (« Au bureau : … transferts ») et
    `REGLES-ECRAN.md:96` ; or `/operations` est gardé « achats » (`App.tsx:258`) : l'alimentation ne transfère qu'au
    téléphone (« Déplacer »). Le lien « Ouvrir → » du « point hebdomadaire » (`Guide.tsx:325`) mène au Cockpit, refusé aux achats.
20. **Pièces jointes : envoi multiple** — `PiecesJointes.tsx:103-108` : si le 3e fichier échoue, les deux premiers sont
    déposés mais la liste n'est pas relue (le geste renvoie `undefined`) ; le sélecteur accepte `image/*` (dont SVG) que
    le serveur refuse (`gestion_mp/api/suivi.py` `TYPES_PERMIS`) — refus découvert après clic.
21. **Confirmer sans filet** — `components/ui.tsx:373-376` : une exception de `onConfirme` n'est pas rattrapée (dépend de
    l'appelant) ; le bouton « Oui » n'est jamais grisé.
22. **« Annuler » contourne la garde** — fenêtre Traiter (`pages/Accueil.tsx:119`) : « Annuler » appelle `onFermer`
    directement, sans la question « Les abandonner ? » que posent ×, Échap et le fond.
23. **`nombre(v, 3)` donne jusqu'à 4 décimales** — `lib/format.ts:34` (toute précision ≥ 3 devient « jusqu'à 4 »).
24. **Code mort** — `HAUT_DIALOGUE` (déprécié, plus aucun usage, le commentaire cite Production à tort) et `MOIS_NOMS`
    (`components/direction/commun.tsx:10, 31`) ; `Session.rafraichir` jamais appelé ; la route serveur
    POST `/moi/code` (changer son propre code) n'a **aucun écran**.
25. **`Tableau` absent** — la consigne commune cite un composant `Tableau` dans `ui.tsx` : il n'existe pas (les tableaux
    sont des `<table>` dans un `Cadre`).
26. **Visages publics** — GET `/visages` (non authentifié) livre la liste des noms, identifiants et rôles actifs à tout
    poste du réseau (choix assumé « toucher son nom », à noter pour la réécriture).
27. **Indicateurs du Cockpit non cliquables** — aucun des six ne mène à son écran (Stock, Plan d'achat, Commandes,
    Analyse › Contrôles), alors que `REGLES-ECRAN.md:49-51` demande des raccourcis partout où c'est utile et que l'Accueil le fait pour « Anomalies de contrôle ».
28. **Garde Réglages pour les achats** — `/reglages` est ouvert aux achats par l'adresse (`App.tsx:263`, devises seules)
    alors que le menu ne le montre pas et que le Mode d'emploi dit qu'ils « n'ont pas les réglages ».

### Comptes

- **Écrans / pages** : 7 — coque de bureau (menu), Connexion, Installation (premier lancement), Accueil (2 versions :
  achats/direction et alimentation), Cockpit, Mode d'emploi, Page du lot.
- **Onglets / sous-vues** : 16 — Cockpit 5 onglets ; Mode d'emploi 7 onglets ; Bascule Évolution 4 vues.
- **Fenêtres / tiroirs** : 4 — « Besoin signalé par… » (Traiter) ; DetailCommande (depuis Cockpit, inventorié ailleurs) ;
  PreparationCommande (depuis Cockpit, inventorié ailleurs) ; bandeau d'abandon et question `Confirmer` (mécanismes
  partagés) — plus 1 panneau de menu replié (« ☰ Menu »).
- **Documents imprimables** : 2 — Bilan du mois ; Étiquettes de lots.
- **Composants partagés décrits** : 20 (`Page, Carte, Indicateur, Etiquette, Bouton, Champ, ChampNombre, Message,
  Chargement, BarreRecherche, Onglets, Dialogue, Confirmer, Bascule, HAUT/Cadre, useEnvoi, ChoixRecherche, Vide,
  briques direction, PiecesJointes`).
- **Gestes inventoriés** : 30 — ☰ Menu, Se déconnecter ; toucher un nom, Entrer (dont entrée auto 4 chiffres), Créer le
  compte et entrer ; Traiter, Marquer traité, Annuler ; Bilan du mois (+ choix du mois) ; Examiner / ligne à approuver ;
  Préparer la commande ; Effacer les filtres ; ligne d'alerte → Stock ; Photographier aujourd'hui ; Bascule Évolution ;
  Imprimer l'étiquette ; Où ce lot est-il allé ? ; Libérer (Non / Oui, libérer) ; Joindre un document… ; glisser-déposer ;
  télécharger ; Retirer (Non / Oui, retirer) ; Dialogue ×/Échap/fond, Non continuer la saisie, Oui abandonner ; Imprimer
  (bilan, étiquettes) ; changement d'onglet (Cockpit, Mode d'emploi).

---

## Partie 2 — Stock, sorties vers les machines, production & besoins

Périmètre : `ecran/src/pages/Stock.tsx`, `components/stock/{StockParMatiere,Tracabilite,AValider,commun}.tsx`
(+ `stock.css`, `stock-bureau.css`), `pages/Sorties.tsx`, `components/production/{SaisieSortie,RetourBureau}.tsx`,
`pages/Production.tsx`, `components/production/{VoletPlan,VoletBesoins,VoletGlissant,VoletRealise,types.ts,production.css}`.
Dépendances lues pour comprendre les règles : `pages/atelier/sortie.ts` (moteur de saisie d'un ordre, partagé
avec le téléphone), `pages/atelier/commun.tsx` (types `Bon`, unités, `Blocages`, `useSuspension`),
`pages/atelier/Envoyer.tsx:52-92` (`dateLisible`, `useEmpechements`, `EcartFil`, `parQualite`),
`pages/atelier/LotFiche.tsx:53-62` (`STATUTS_LOT`, `useFicheLot`), `components/direction/commun.tsx`
(`signe`, `moisLisible`, `LigneVide`, `trier`). Serveur : `gestion_mp/api/{stock,pilotage,production,
production_plan,brouillons,operations,exports,referentiels}.py`, `gestion_mp/securite.py`, `services/stock.py`.

Conventions communes (rappel utile à la reconstruction) :
- `nombre(v, d)` : 0 décimale par défaut ; `d=1` → exactement 1 décimale ; `d=2` → exactement 2 ; `d≥3` → jusqu'à 4.
  Séparateur de milliers = espace insécable. `null` → « — » (`lib/format.ts:29-35`).
- `quantite(v, kgParMl, d=1)` (atelier/commun.tsx:160-165) : « 12,5 kg » ; sous 10 kg (et ≠ 0) au moins 2 décimales ;
  pour cuir/franges/ruban (`kg_par_ml` > 0) suffixe « ≈ 1 020 ml » (mètres indicatifs = kg ÷ kg_par_ml, arrondi entier).
- `metres(kg, kgParMl)` → « ≈ N ml » ou vide ; `jours(v)` → « N j » ; `part(v)` → « 12,3 % » ; `signe(v)` → « +12,3 % » ;
  `montantCourt` → « 17,4 M MAD » au-delà du million ; `date()` → jj/mm/aaaa ; `horodatage()` → « jj/mm/aaaa hh:mm ».
- `Chargement quoi=X` affiche exactement « Un instant — chargement : X… » (ui.tsx:209-211).
- `Confirmer` : le bouton devient « question · [Non] · [oui] » sur place (ui.tsx:342-382).
- `Dialogue sale` : ×, Échap, clic sur le fond → bandeau « Des modifications ne sont pas enregistrées. Les abandonner ? »
  [Non, continuer la saisie] [Oui, abandonner] (ui.tsx:325-333).
- `useEnvoi` : messages d'erreur (rouge) / succès (vert) sous le geste ; erreur = texte `detail` du serveur.
- Recherche « à la frappe » = `filtrer` (`lib/recherche.ts`) : plusieurs mots, n'importe quel ordre, sans accents ni casse.
- Droits serveur (`securite.py:104-122`) : refus 403 « Cette action est réservée à : <rôles>. » ; libellés de rôles :
  « responsable achats », « responsable alimentation machines » ; DIRECTION seule → « Cette action est réservée à : la direction. »
  Sans session : 401 « Connectez-vous pour continuer. » ; compte inactif : 401 « Ce compte n'est plus actif. »
  `ALIMENTATION` = alimentation + direction ; `ACHATS` = achats + direction ; `STOCK` = achats + alimentation + direction.
- `date_permise` (securite.py:210-226), refus communs à toute écriture datée : « Date trop ancienne (jj/mm/aaaa) : vérifier
  l'année. » · « Date dans le futur (jj/mm/aaaa) : un mouvement se saisit le jour où il a lieu. » · « La période jusqu'au
  jj/mm/aaaa est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir. »
- Teintes globales : `Etiquette`/`Indicateur` tons `ok` (vert), `attention` (jaune-orangé `--warning`), `urgent` (orange
  `--urgent`), `critique` (rouge), `rupture` (gris foncé/noir `--dark` pour l'étiquette, rouge pour l'indicateur),
  `neutre` (gris) (index.css:420-456, 627-661).

---

### Menu, gardes de route et accès

| Écran | Menu (groupe « Tous les jours ») | Garde de route | Remarque |
|---|---|---|---|
| `/stock` « Stock, lots & mouvements » | achats, alimentation (+ direction) — App.tsx:51 | **aucune** (App.tsx:250) | pastille rouge = ruptures + critiques du cockpit, à côté du lien (App.tsx:223) — calculée seulement si rôle ≠ alimentation (requête `/cockpit` désactivée pour l'alimentation, App.tsx:186-191) |
| `/sorties` « Sorties vers les machines » | achats, alimentation (+ direction) — App.tsx:52 | `garde(['achats','alimentation'])` (App.tsx:252) | page d'accueil de l'alimentation au bureau : `/` → `/sorties` si rôle alimentation et pas sur téléphone (App.tsx:170) |
| `/production` « Production & besoins » | achats, alimentation (+ direction) — App.tsx:53 | **aucune** (App.tsx:264) | modification réservée à la direction |

Garde refusée → retour à l'accueil avec bandeau « L'écran demandé (/chemin) est réservé à un autre rôle : vous êtes revenu à votre accueil. » (App.tsx:236-240).

---

### 1. STOCK — `/stock`

#### Page « Stock, lots & mouvements » — `/stock` (?onglet=matieres|lots|mouvements|ordres|a-valider)
- **Fichiers** : `pages/Stock.tsx:111-177` ; CSS `components/stock/stock.css`, `stock-bureau.css`.
- **Titre** : « Stock, lots & mouvements ». **Sous-titre** : « Par matière, lot par lot, chaque mouvement de stock, les ordres de fabrication, et ce qui attend d'être validé. »
- **Paramètres d'adresse lus** (Stock.tsx:112-133) :
  - `?onglet=` (ou l'ancien `?volet=`) ; valeur `tracabilite` → onglet `ordres` ; inconnu/absent → `matieres`.
  - `?article=ID` → onglet Lots filtré sur la matière (le filtre « matière » prend la référence de l'article).
  - `?q=` → recherche initiale de l'onglet courant (Par matière, Lots, Mouvements).
  - `?lot_id=` (+ `?lot=` numéro pour le titre), `?ordre=` (n° OF-…), `?reference=` → ouvre la fenêtre de **suivi de traçabilité** par-dessus l'onglet.
- **Paramètres écrits** : changer d'onglet remplace toute l'adresse par `?onglet=X` (+ extra) — Stock.tsx:118 ; « Voir les lots → » écrit `?onglet=lots&article=ID` ; « Ses mouvements » écrit `?onglet=mouvements&q=REF` ; un suivi écrit `lot_id/lot/ordre/reference` + `onglet` courant en `replace` (Stock.tsx:124-133). Tout changement d'adresse ferme la fiche de lot ouverte (Stock.tsx:135-136).
- **Onglets** (Stock.tsx:141-151) : « Par matière » · « Lots » · « Mouvements de stock » · « Ordres de fabrication » · « À valider » (compteur = nombre total de brouillons, ordres + opérations, masqué si 0).
- **Rôles** : tous les rôles connectés (pas de garde). Différences par rôle détaillées dans chaque onglet : l'alimentation ne voit aucun prix ni montant ni « Action » d'achat ; les liens vers réceptions/opérations/inventaires n'existent que pour achats/direction ; « Libérer » une quarantaine : achats/direction.

---

#### Onglet « Par matière » — `/stock?onglet=matieres` (`?q=` recherche initiale)
- **Fichiers** : `components/stock/StockParMatiere.tsx:248-516` (+ fiche 539-768).
- **Rôles** : tous. `avecPrix = peut('achats')` (achats + direction) — StockParMatiere.tsx:318. L'alimentation : colonnes `montant`, `action`, `valeur` retirées (COLONNES_ACHATS, :173-177), indicateur « Budget à commander » absent, bouton « Exporter en Excel » absent. Le serveur `/stock` met à `null` pour l'alimentation : `prix_kg, prix_unite, montant_a_commander, montant_a_commander_mad, valeur_conso_annuelle, valeur_conso_annuelle_mad, valeur_machine_mad`, et vide `devise` et `action` (pilotage.py:37-62).
- **Données** : `GET /api/stock` (acteur, sans paramètre ; `date_reference` possible côté serveur) → `{date_reference, magasins[] (codes des magasins actifs), lignes[]}` ; `GET /api/articles` (rôle de chaque matière, id pour « Voir les lots ») ; `GET /api/magasins` (type « Quarantaine »).
- **Chargement / erreur** : « Un instant — chargement : le stock… » ; erreur serveur en message rouge.

**Indicateurs** (StockParMatiere.tsx:369-383)

| Indicateur | Valeur affichée | Formule / détail tel qu'affiché | Ton |
|---|---|---|---|
| Matières affichées | nb lignes visibles | « sur N » (N = toutes les lignes du stock) | — |
| Stock affiché | « X kg » | Σ `stock_net` des lignes visibles | — |
| Ruptures | nb lignes dont `statut` contient RUPTURE | « stock projeté à zéro » | `rupture` si > 0, sinon `ok` |
| Critiques | nb lignes dont `statut` contient CRITIQUE | « sous le seuil critique » | `critique` si > 0, sinon `ok` |
| Budget à commander (achats/direction seulement) | `montantCourt(Σ montant_a_commander_mad)` ; infobulle = montant exact | « N matière(s) » (celles dont quantité à commander > 0,0005) | `attention` si budget > 0, sinon `ok` |

Aucun indicateur n'est cliquable.

**Rangée de tête** (`.filtres.tete`) : Bascule de vues maison (`div.bascule role="tablist"`, :386-392) — « Approvisionnement » (infobulle « Couverture, commandes, ce qu'il faut commander »), « Classement et risque » (« ABC, XYZ, sourcing, dormants »), « Où se trouve la matière » (« Magasins, métiers, quarantaine, commandé ») ; vue par défaut : Approvisionnement (non mémorisée dans l'adresse). Recherche « Référence, couleur, fournisseur, titrage… plusieurs mots affinent ». Lien « Exporter en Excel » (achats/direction) → `/api/export/pilotage` (téléchargement ; infobulle « Stock par matière, plan d'achat, besoins mois par mois et contrôles, dans un classeur Excel » ; serveur `ACHATS`).

**Filtres liés** (`.filtres.lies`, :405-434) — 9 listes, chacune ne propose que les valeurs encore présentes compte tenu des autres filtres, de la recherche et des cases (et garde la valeur choisie) :

| Liste (option vide) | Valeur lue | Infobulle | Tri des choix |
|---|---|---|---|
| Tous les statuts | `statut` | — | par rang RUPTURE, CRITIQUE, URGENT, ATTENTION, OK, NON CONSOMMÉE |
| Tous les fournisseurs | `fournisseur` | — | alphabétique fr, numérique |
| Tous les rôles | rôle de l'article (`/articles`) | — | idem |
| Toutes compositions | `composition` | — | idem |
| Tous types de fil | `type_fil` | — | idem |
| Tous titrages | « titrage unité » | — | idem |
| Classe ABC (options « Classe A »…) | `classe_abc` | « A : l'essentiel de la valeur consommée » | idem |
| Classe XYZ (options « Classe X »…) | `classe_xyz` | « X : demande régulière, Z : erratique » | idem |
| Tous les magasins | magasins où la ligne a |stock| > 0,0005 | « Les matières qui ont du stock dans ce magasin » | idem |

Cases : « En stock » (stock_net > 0,0005) ; « À commander » (infobulle « Les matières pour lesquelles le calcul propose une commande » ; quantité à commander > 0,0005). Bouton « Effacer les filtres » visible dès qu'un filtre, la recherche ou une case est posé (remet tout à zéro).
Recherche à la frappe sur : référence, désignation, nature, fournisseur, composition, type de fil, couleur, titrage, groupe d'équivalence, rôle.

Note sous les filtres : « {aide de la vue}. Un clic sur une ligne ouvre la fiche de la matière et ses lots ; un clic sur un en-tête trie. Situation au jj/mm/aaaa. » (date_reference).

**Tableau** (`table.serre.matieres`, `Cadre taille="court"`). Colonnes fixes puis colonnes de la vue. Tous les en-têtes triables (`th.triable`, flèche ↑/↓, en-tête trié en couleur accent ; infobulle « {aide} — cliquer pour trier »). Premier clic : décroissant pour une colonne numérique, croissant sinon ; reclic inverse. **Tri par défaut** : Statut croissant (du plus grave au plus calme), puis couverture croissante.

Colonnes fixes :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Référence | **référence** ; dessous note « rôle · désignation » (désignation omise si = référence) | texte, `td.reference` max 180 px, infobulle = référence | tri alphabétique numérique |
| Fournisseur | nom ou « — » grisé | texte | tri fournisseur puis référence |
| Statut | Étiquette du statut appliqué (`⚫ RUPTURE`, `🔴 CRITIQUE`, `🟠 URGENT`, `🟡 ATTENTION`, `🟢 OK`, `⚪ NON CONSOMMÉE`) | ton par `tonStock` (:131-138) : RUPTURE→rupture, CRITIQUE→critique, URGENT→urgent, ATTENTION→attention, NON CONSOMM/DORMANT→neutre, sinon ok | infobulle d'en-tête « Du plus urgent au plus calme — cliquer pour trier » |

Rendu des quantités (`Kg`, :148-157) : `null` → « — » grisé ; |v| < 0,0005 → « 0 » grisé ; négatif en rouge ; sans unité (les en-têtes sont en kg) ; pour cuir/franges/ruban, note « ≈ N ml » dessous dans les colonnes qui passent `m` (Stock, Disponible, À commander).

Vue **Approvisionnement** (:180-194) :

| Colonne | Contenu / unité | Aide (infobulle d'en-tête) | Pied |
|---|---|---|---|
| Statut classeur | Étiquette `statut_couverture` (ou « — ») | « Statut de couverture : la couverture comparée aux seuils « critique » et « attention » des réglages » | — |
| Stock | `stock_net` kg (+ ml) | « Tout ce que détiennent les magasins, quarantaine comprise » | Σ |
| Sur les métiers | `stock_machine` kg | « Stock en machine : monté sur les métiers, pas encore tissé — compté dans le stock, sa valeur et le disponible » | Σ |
| Disponible | `stock_disponible` kg (+ ml) | « Les magasins hors quarantaine, plus le stock en machine (le fil monté sur les métiers) » | Σ |
| Commandé | `bc_en_cours` kg | « Attendu dans le délai du fournisseur » | Σ |
| Demande pendant le délai | `demande_delai` kg | « Ce que le plan consommera d'ici la livraison d'une commande passée aujourd'hui : Disponible + Commandé − cette demande = Projeté » | Σ |
| Projeté | `stock_projete` kg | « Ce qu'il restera à la livraison d'une commande passée aujourd'hui » | Σ |
| Conso / mois | `conso_mensuelle` kg | « Consommation d'un mois de la saison, en kg » | Σ |
| Couverture | `couverture_jours` « N j » ou « — » | (aucune) ; tri : sans valeur = 1e9 | — |
| À commander | `quantite_a_commander` kg (+ ml) | « En kg (les mètres d'un cuir, de franges, d'un ruban dessous, à titre indicatif) ; les unités de commande sont dans la fiche » | Σ |
| Montant MAD (achats/direction) | `montant_a_commander_mad` | — | Σ |
| Action (achats/direction) | texte du conseil (note, min 140 px, retour à la ligne) ou « — » | « Ce que le calcul conseille de faire » | — |

Vue **Classement et risque** (:195-209) :

| Colonne | Contenu | Aide | Pied |
|---|---|---|---|
| ABC | **classe** · note « rang N · X % » (infobulle « Rang et part cumulée de la valeur consommée ») | « Part de la valeur consommée : A = l'essentiel ; trié par rang » | — |
| Conso / an MAD (achats/direction) | `valeur_conso_annuelle_mad` | « Valeur de la consommation annuelle » | Σ |
| XYZ | **classe** · note « CV 0,00 » | « Régularité de la demande : X régulière, Z erratique (CV : coefficient de variation) » | — |
| Sourcing | texte ou « — » | — | — |
| Équivalences | groupe · note « N substitut(s) » ; infobulle = substituts « a · b » | « Groupe d'équivalence et substituts disponibles » | — |
| Dernière sortie | date · note « N j » · Étiquette neutre « dormant » | « Et depuis combien de jours sans sortie ni entrée ; « dormant » au-delà du seuil des réglages » | — |

Vue **Où se trouve la matière** (:210-231) :

| Colonne | Contenu | Aide | Pied |
|---|---|---|---|
| Stock | `stock_net` (+ ml) | « Tout ce que détiennent les magasins, quarantaine comprise » | Σ |
| *une colonne par magasin actif non quarantaine* (titre = code) | `par_magasin[code]` | « Magasin CODE » | Σ |
| Quarantaine | Étiquette rouge (critique) avec la quantité si > 0,0005, sinon « 0 » grisé | « Détenue mais pas disponible » | Σ |
| Sur les métiers | `stock_machine` | (même aide qu'en Approvisionnement) | Σ |
| Disponible | **en gras** (+ ml) | « Les magasins, hors quarantaine » | Σ |
| Commandé | `bc_en_cours` | « Attendu dans le délai du fournisseur » | Σ |
| Commandé au-delà | `bc_hors_horizon` | « Attendu après le délai : ne compte pas dans le projeté » | Σ |
| Projeté | `stock_projete` | — | Σ |

Règle des colonnes magasin : seulement les magasins actifs (liste du serveur), hors type Quarantaine, et ayant au moins une ligne visible ≠ 0 (« Un magasin vide pour toute la sélection n'a pas de colonne »).

**Pied de tableau** : « Total des N matière(s) » sur les 3 premières colonnes, puis Σ des colonnes marquées somme (entiers), cellules vides sinon (:476-496).
**Pagination** : aucune (toutes les matières). **Ligne cliquable** (`tr.cliquable`) → fenêtre « Fiche matière ».
**Vide** : « Aucune matière ne correspond à ces filtres. »

**Gestes**

| Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|---|
| Approvisionnement / Classement et risque / Où se trouve la matière | bascule de tête | tous | — | — | — | — | — |
| clic en-tête | tableau | tous | — | — | — | tri | — |
| Effacer les filtres | rangée des filtres | tous | visible si un filtre/recherche/case posé | — | — | — | — |
| Exporter en Excel | tête | achats, direction | — | — | `GET /api/export/pilotage` | fichier .xlsx | 403 « Cette action est réservée à : responsable achats. » |
| clic ligne | tableau | tous | — | — | — | ouvre la fiche | — |

##### Fenêtre « Fiche matière » (Dialogue `tresLarge`, titre = référence)
- **Fichier** : StockParMatiere.tsx:539-768. Pas de saisie (`sale` absent).
- **Tête** : Étiquette du statut ; note « rôle · désignation · composition · type de fil · couleur · titrage » ; boutons :

| Geste | Rôle | Conditions | Effet / adresse |
|---|---|---|---|
| « Voir les lots → » (variante principal si stock_net > 0,0005, sinon neutre ; infobulle « Les lots de cette matière, et ce qui leur reste (cocher « épuisés » pour l'historique) ») | tous | affiché seulement si l'article est connu de `/articles` | `/stock?onglet=lots&article=ID` |
| « Où cette matière est-elle allée ? » (infobulle « Tous les mouvements de cette matière, lot par lot : où elle est allée, et quand ») | tous | — | ouvre le suivi `?reference=REF` (fenêtre de suivi par-dessus la fiche) |
| « Ses mouvements » (infobulle « Le journal filtré sur cette matière ») | tous | — | `/stock?onglet=mouvements&q=REF` |

- **Indicateurs** (:584-621) :

| Indicateur | Valeur | Détail / infobulle | Ton |
|---|---|---|---|
| Stock net | `stock_net` | « kg en magasin » (+ « · ≈ N ml ») | — |
| Sur les métiers | `stock_machine` | détail « {valeur courte} · stock en machine » (achats) ou « stock en machine » ; infobulle « Stock en machine : le fil monté, pas encore tissé. Il compte dans le stock et sa valeur, dans le disponible et le stock projeté — donc avant de commander. » | — |
| Disponible | `stock_disponible` | « magasins, hors quarantaine » | — |
| Demande pendant le délai | `demande_delai` | « N j de délai ; puis X sur la période que couvre une commande » (X = `sorties_prevues`) | — |
| Stock projeté | `stock_projete` | « à la livraison d'une commande passée aujourd'hui » | ton du statut |
| Couverture | « N j » ou « — » | « sans consommation prévue » ou « après le délai ; seuil d'alerte : N j » (`couverture_cible_jours`) | ton du statut si couverture connue |
| À commander | `quantite_a_commander` | cuir/franges/ruban : « kg · ≈ N ml, à titre indicatif » ; sinon si unité de commande ≠ kg : « N,N {unité} de X kg » ; sinon « N,N palette(s) » | `attention` si > 0 |

- **Carte « Approvisionnement »** (paires libellé / valeur) : Fournisseur ; Délai (« N j ») ; **Prix** (achats/direction) « 0,000 DEV / kg » + note « au catalogue : 0,0000 DEV / ml » si l'unité d'achat est ml ; Stock minimum (catalogue) (note « retenu : X — ramené à ce que la consommation justifie » si `stock_min_plafonne` < `stock_min` − 0,5) ; Seuil d'alerte = `stock_min_recalcule` (note « sécurité et stock minimum, soit N j de consommation — comparé au stock projeté ») ; Consommation retenue / mois = `conso_mensuelle` (note si coefficient : « plan X · réel Y · plan corrigé × 0,00 » ou, coefficient hérité, « plan X · corrigé × 0,00, le taux de réalisation de REF qu'il remplace ») ; Besoin annuel retenu (note « le plan corrigé par le réel (× 0,00) ») ; Déjà en préparation (si > 0 ; note « brouillon n° N, BC-… : déduit de la quantité à commander, pas encore attendu ») ; **Montant à commander** (achats/direction) « X DEV » + note en MAD si devise ≠ MAD.
- **Carte « Classement et risque »** : Classe ABC (note « rang N, X % cumulés ») ; **Valeur consommée / an** (achats/direction) ; Classe XYZ (note « coefficient de variation 0,00 ») ; Sourcing (note « N fournisseur(s) dans le groupe ») ; Groupe d'équivalence ; Dernière sortie ; Sans mouvement depuis (« N j ») ; Dormant (Étiquette neutre « oui » / « non »).
- **Carte « Où se trouve la matière »** : une paire par magasin actif (quarantaine en Étiquette rouge) ; **Disponible** (ligne total) ; Sur les métiers (note « stock en machine, compté dans le disponible ») ; Commandé, attendu dans le délai ; Commandé, attendu au-delà (note « ne compte pas dans le projeté ») ; Demande pendant le délai (« − X », note « ce que le plan consommera en N j ») ; **Stock projeté à la livraison** (total ; note « disponible + commandé − demande pendant le délai »).
- **Messages** : (achats/direction) « Action : {action} » (bleu si à commander, vert sinon) ; « Rien ne se rachète pour cette matière ({sans_achat}), même sous son stock minimum. » ; « Substituts disponibles dans le même groupe : a · b ».
- **Carte « Besoins du plan, mois par mois (kg) »** (si `besoins` non vide) : une colonne par mois depuis le mois de la date de référence (libellé `toLocaleDateString` court « oct. 26 »), + « Total » en gras.

**Notions métier** : Stock (net) = magasins quarantaine comprise ; Sur les métiers (stock en machine, fil monté pas encore tissé) ; Disponible = magasins hors quarantaine + stock en machine ; Commandé (dans le délai) / Commandé au-delà ; Demande pendant le délai ; Projeté = Disponible + Commandé − Demande pendant le délai ; Couverture (jours) = projeté ÷ (conso/30) ; statut appliqué (serveur moteur.py:1287-1311) : conso nulle → NON CONSOMMÉE ; projeté ≤ 0 → RUPTURE ; projeté ≤ 50 % du seuil d'alerte → CRITIQUE ; ≤ seuil → URGENT ; ≤ 120 % du seuil → ATTENTION ; sinon OK (seuil d'alerte ≤ 0 sans demande → OK) ; « Statut classeur » = couverture comparée aux seuils critique/alerte des réglages ; ABC, XYZ (CV), sourcing, groupe d'équivalence, substituts, dormant ; coefficient de réalisation (plan corrigé par le réel) ; quantité à commander (kg, unités de commande, palettes) ; budget à commander ; stock minimum catalogue / plafonné / seuil d'alerte.

---

#### Onglet « Lots » — `/stock?onglet=lots` (`?article=ID`, `?q=`)
- **Fichiers** : Stock.tsx:179-404.
- **Rôles** : tous (aucune différence dans la liste ; la fiche de lot ouverte varie).
- **Données** : `GET /api/soldes?avec_historique=true&en_stock=true|false` (`en_stock=false` quand « Voir aussi les lots épuisés » est coché) — par lot : `lot, reference, designation, role, fournisseur, entre_le, kg_par_ml, poids_bobine, bobines (= arrondi reste ÷ kg/bobine), quantite (reste), disponible, quarantaine, magasins[{magasin, type, quantite}], statut, entre, sorti, dernier_mouvement, ordres[{id, numero}]` ; `GET /api/articles` (pour `?article=`).
- **Règles serveur du lot** (stock.py:50-57, 156-193) : statut `disponible` / `partiel` (« En partie en quarantaine ») / `quarantaine` / `epuise` (seuil 1 g) ; Entré = entrées hors transferts et hors annulations ; Sorti = sorties nettes des retours des machines ; Entré − Sorti = Reste ; ordres servis = ordres des sorties.
- **Comportement d'arrivée** : `?q=` (un lot cherché depuis un autre écran) coche d'office « Voir aussi les lots épuisés » ; `?article=` pose le filtre matière.

**Indicateurs** (Stock.tsx:259-269)

| Indicateur | Valeur | Détail | Ton |
|---|---|---|---|
| Lots affichés | nb lignes | « N en stock » (statut ≠ épuisé) | — |
| Reste | « X kg » (Σ reste) | « dans les lots affichés » | — |
| En quarantaine | nb lots avec quarantaine > 0,0005 | « X kg à libérer ou rendre » ou « aucun lot bloqué » | `attention` si > 0, sinon `ok` |
| Ordres servis | nb d'ordres distincts | « par les lots affichés » | — |

**Rangée de tête** : recherche « Lot, matière, couleur, fournisseur, ordre… plusieurs mots affinent » (sur lot, référence, désignation, fournisseur, rôle, n° d'ordres, magasins) ; liste de tri (infobulle « L'ordre des lignes ») : « Par matière, du plus ancien au plus récent » (défaut : référence puis date d'entrée), « Derniers mouvements d'abord », « Plus anciens d'abord » (date d'entrée), « Plus gros restes d'abord » ; bouton « Étiquettes (N) » (grisé si aucun lot coché, infobulle « Imprimer les étiquettes QR des lots cochés »).
**Filtres liés** : « Tous les fournisseurs (n) » (infobulle « Choisir un fournisseur ne propose plus que ses matières »), « Toutes les matières (n) » (« Une matière : tous ses lots », largeur max 300 px), « Tous les magasins (n) » (« Les lots qui ont du stock dans ce magasin »), « Tous les rôles (n) » (« Poil, trame, chaîne… ») — le nombre entre parenthèses = nombre de choix proposés ; case « Voir aussi les lots épuisés » ; « Effacer les filtres » (visible si filtre, recherche ou case épuisés ; remet tout, décoche épuisés).

**Tableau** (`Cadre taille="court"`, `table.serre`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| ☐ (case ; en-tête « Cocher tous les lots affichés ») | sélection pour étiquettes | centré | clic sur la case ne ouvre pas la ligne |
| Lot | **n° lot** (mono) + Étiquette statut si ≠ disponible (« En partie en quarantaine » attention, « En quarantaine » critique, « Épuisé » neutre) ; note « entré le jj/mm/aaaa » | sans retour à la ligne | — |
| Référence | référence ; note « rôle · fournisseur » | infobulle = désignation | — |
| Dernier mouvement | date | — | — |
| Entré | `quantite(entre, kg_par_ml, 0)` « X kg [≈ ml] » | droite | — |
| Sorti | idem | droite | — |
| Reste | **`quantite(reste, kg_par_ml, 1)`** | droite, gras | — |
| Bobines | nombre ou « — » | droite | — |
| Magasins | une ligne par magasin : code (Étiquette rouge si Quarantaine) + quantité | note | — |
| Ordres servis | ≤ 2 : « OF-… · OF-… » ou « — » ; > 2 : « N ordres » (infobulle = liste) | note | — |
| (sans titre) | bouton « Suivre » (infobulle « D'où vient ce lot, quels ordres il a servis, et quand ») | — | ouvre le suivi du lot (`?lot_id=&lot=`) |

Ligne cliquable → fenêtre « Fiche de lot ». Pas de pied, pas de pagination.
**Vide** : « Aucun lot ne correspond. » (lots existants) ; « Aucun lot : les lots naissent des réceptions et des stocks d'ouverture. »
**Chargement** : « Un instant — chargement : les lots… »

| Geste | Rôle | Conditions | Appel | Effet |
|---|---|---|---|---|
| Étiquettes (N) | tous | grisé si 0 coché (pas d'infobulle de raison distincte) | ouvre `/api/lots/etiquettes?ids=1,2,…` dans un nouvel onglet | document imprimable |
| Cocher / tout cocher | tous | — | — | sélection |
| Suivre | tous | — | `GET /api/tracabilite?lot_id=` | fenêtre de suivi |
| clic ligne | tous | — | `GET /api/lots/{id}` | fiche de lot |
| Effacer les filtres | tous | ≥ 1 filtre | — | — |

##### Document imprimable « Étiquettes de lots » — `GET /api/lots/etiquettes?ids=…`
- **Fichier serveur** : stock.py:361-415 (acteur). Une page par lot, format 100 × 70 mm (`@page`), bouton « Imprimer » (masqué à l'impression).
- Contenu : QR (adresse `{adresse publique}/lot/{id}`), **référence**, « Lot N° » en grand, fournisseur, « Entré le jj/mm/aaaa », « X kg [≈ ml] à l'impression », « N° {id} », et si quarantaine > 1 g : encadré « QUARANTAINE — NE PAS SORTIR ».
- Refus : 404 « Aucun lot à étiqueter. »

##### Fenêtre « Fiche de lot » (Dialogue `tresLarge`, titre « {référence} — lot {n°} », « Lot » pendant le chargement)
- **Fichiers** : Stock.tsx:579-670 (`FicheLotBureau`, réutilisée par la page `/lot/:id` avec `dansFenetre=false`), 674-741 (`Liberation`), 743-763 (`DialogueLot`).
- **Données** : `GET /api/lots/{id}` (acteur ; prix des mouvements masqués pour l'alimentation).
- **Chargement** : « Un instant — chargement : le lot… »
- **Indicateurs** :

| Indicateur | Valeur | Détail | Ton |
|---|---|---|---|
| Reste | `quantite(quantite)` | « N bobines » si connu | `attention` si statut quarantaine |
| Disponible | `quantite(disponible)` | libellé du statut (« Disponible », « En partie en quarantaine »…) | — |
| Entré · sorti | « {nombre(entre)} · {quantite(sorti,…,0)} » | « dernier mouvement le jj/mm/aaaa » | — |
| kg / bobine | `nombre(poids_bobine, 2)` ou « — » | « N bobines / palette » | — |
| Entré le | date d'entrée | fournisseur | — |

- **Ligne de réception** (si réception validée) : « Reçu par {REC-…} le jj/mm/aaaa · BL x · facture y · pesé X kg » — le n° est un lien `/receptions?reception=ID` pour achats/direction seulement.
- **Rangée des soldes** : par magasin, code (Étiquette rouge si Quarantaine, gras sinon) + `quantite` ; note « Ordres servis : » avec liens `/sorties?ordre=ID` ; lien-bouton « Où ce lot est-il allé ? » (infobulle « D'où vient ce lot, quels ordres de fabrication il a servis, et quand ») → `/stock?onglet=lots&lot_id=ID&lot=N` (`adresseSuivi`).
- **Bloc « Libérer »** (achats/direction, si une quarantaine > 0,0005) — voir Gestes.
- **Tableau des mouvements** (`Cadre taille="dialogue"`, le plus récent en haut) : Date · Mouvement (libellé + Étiquette neutre « annulation » si contre-passation + note « · motif ») · Document (n°, lien selon `lienDocument`) · Magasin · Quantité (droite, « + » si positive, vert si > 0 / rouge si < 0, 1 décimale) · Par. Infobulle de ligne = commentaire.
- **Pied** : « Page du lot » (lien `/lot/ID`) ; « Imprimer l'étiquette » (ouvre `/api/lots/etiquettes?ids=ID`).

`lienDocument` (Stock.tsx:96-109) : sortie → `/sorties?ordre=ID` ; opération → `/operations?operation=ID` (achats/direction) sinon, pour un retour rattaché à un ordre, `/sorties?ordre=ORDRE` sinon pas de lien ; réception → `/receptions?reception=ID` (achats/direction) ; inventaire → `/inventaire?inventaire=ID` (achats/direction) ; autre → pas de lien.

**Formulaire « Libérer »** (`.saisie-ligne`, Stock.tsx:706-740) : titre gras « En quarantaine : X kg dans « MAG » » ; liste « vers CODE » (magasins actifs non quarantaine ; défaut le premier ; infobulle « Vers le magasin ») ; champ texte (max 300) placeholder « Ce qui a été contrôlé (obligatoire) ». Pas de garde « Abandonner ».

| Geste | Rôle | Conditions / grisé + raison | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|
| Libérer | achats, direction | grisé si pas de destination, commentaire < 3 caractères (infobulle « Écrire d'abord ce qui a été contrôlé »), ou envoi en cours ; sinon infobulle « Transfert « Libération de quarantaine », validé tout de suite » | « Libérer X kg : la matière devient disponible pour les machines ? » [Non] [Oui, libérer] | `POST /api/operations` `{type:'transfert', date: aujourd'hui, motif:'Libération de quarantaine', commentaire, lignes:[{article_id, lot_id, magasin_id: quarantaine, magasin_destination_id, quantite: tout le solde}]}` puis `POST /api/operations/{id}/valider` ; si la validation échoue, le brouillon est supprimé (`DELETE`) | « TRF-… : X kg libérés, disponibles pour les machines. » | « Libérer une quarantaine est une décision des achats, après contrôle de la matière. » (403) · « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». » · « Un transfert va d'un magasin à un autre. » · inventaire : « L'inventaire INV-… est en cours sur « MAG » : les mouvements y sont suspendus jusqu'à sa validation. » · « Le lot « N » de « REF » ne porte que X kg dans « MAG », Y kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là. » · date close / future |

**Notions** : lot, statut de lot, quarantaine (magasin de type « Quarantaine », détenue mais pas disponible), libération de quarantaine (décision des achats, transfert validé), kg / bobine (pesé sur le lot sinon catalogue), bobines / palette, étiquette QR, réception / BL / facture / pesé.

---

#### Onglet « Mouvements de stock » — `/stock?onglet=mouvements` (`?q=` recherche initiale)
- **Fichiers** : Stock.tsx:406-575.
- **Rôles** : tous. `avecPrix = peut('achats')` : colonnes « Prix » et « Valeur MAD » et la phrase sur la valeur uniquement pour achats/direction. Le serveur masque `prix, cours, cout_mad, valeur_mad` et vide `devise` pour l'alimentation (stock.py:35-47, 147-148).
- **Données** : `GET /api/mouvements?q&type&magasin_id&du&au&limite=500&decalage=N&avec_valeur=true` (pages de 500, le plus récent d'abord ; `suivant` = décalage suivant ou null ; `types` = dictionnaire code → libellé) ; `GET /api/magasins`.
- **Recherche serveur** (stock.py:122-130) : chaque mot (ILIKE, insensible à la casse) doit se trouver dans référence, désignation, n° de lot, n° de document, motif, commentaire ou auteur. Saisie temporisée 300 ms.

**Filtres** (une rangée) : recherche « Référence, lot, n° de document, motif, personne… » ; « Tous les types » + types du serveur (« Stock d'ouverture », « Entrée de réception », « Sortie vers les machines », « Retour des machines », « Retour au fournisseur », « Ajustement d'inventaire », « Transfert entre magasins ») ; « Tous les magasins » + codes (tous les magasins, actifs ou non) ; « Du » date ; « Au » date ; « Effacer les filtres » (si l'un est posé) ; à droite lien « Exporter en Excel » → `/api/export/mouvements?q&type&magasin_id&du&au` (infobulle « Les mouvements de stock avec ces filtres, sans limite de lignes, dans un classeur Excel » ; serveur acteur, sans prix pour l'alimentation). Filtres non liés entre eux.

Note : « N mouvement(s) affiché(s)[, d'autres plus anciens suivent] — le plus récent d'abord.[ La valeur est au coût moyen du moment (une entrée d'achat, à son coût).] Le document s'ouvre d'un clic. »

**Tableau** (`Cadre taille="court"`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Date (infobulle « Date du mouvement ; dessous, quand il a été saisi ») | date d'effet ; note « saisi jj/mm/aaaa hh:mm » | — | — |
| Type | libellé + Étiquette neutre « annulation » si contre-passation | — | — |
| Document | n° (mono), lien selon `lienDocument` | — | — |
| Référence | référence (max 210 px, retour à la ligne) | infobulle = référence | — |
| Lot · magasin | n° de lot en bouton-lien (infobulle « La fiche du lot ») ; note code magasin | — | ouvre la fiche de lot |
| Quantité | « +X,X » / « −X,X » | droite ; vert si > 0, rouge si < 0 | sans unité (kg) |
| Prix (achats/direction) | « 0,000 DEV » ou « — » | droite | prix du mouvement |
| Valeur MAD (achats/direction) | `valeur_mad` entier ou « — » ; infobulle « X MAD / unité » (coût unitaire) | droite | coût moyen du moment (CMUP), entrée d'achat à son coût ; arrivée d'un transfert = coût de sa ligne de départ |
| Motif | motif ; note commentaire | max 200 px | — |
| Par | auteur | — | — |

Infobulle de ligne = commentaire. Pas de ligne cliquable. **Pagination** : bouton « Charger les 500 suivants » (« Lecture… » pendant le chargement, grisé alors). **Vide** : « Aucun mouvement ne correspond. » **Chargement** : « Un instant — chargement : les mouvements… »

**Notions** : Mouvements de stock (journal jamais effacé ; une annulation = ligne inverse signée et datée, étiquette « annulation ») ; date d'effet / date de saisie ; types de mouvement ; valeur au coût moyen (CMUP).

---

#### Onglet « Ordres de fabrication » — `/stock?onglet=ordres` (`?ordre=OF-…` ouvre le suivi)
- **Fichiers** : components/stock/Tracabilite.tsx:131-250 (`VueOrdres`).
- **Rôles** : tous (aucune donnée de prix).
- **Données** : `GET /api/ordres-fabrication` (acteur ; ordres annulés exclus ; tri serveur : plus récente date de fin d'abord) → lignes `{numero_of, consomme, retours, net, lots[], references[{reference, quantite, theorique, ecart, hors_recette}], debut, fin, fabrications[{qualite, m2}], m2, commentaire, theorique (perte comprise), ecart, ecart_relatif}`.
- **Chargement / erreur** : « Un instant — chargement : les ordres de fabrication… » ; message d'erreur rouge.

**Indicateurs** :

| Indicateur | Valeur | Détail |
|---|---|---|
| Ordres de fabrication | nb affichés | « sur N » |
| Sorti net | « X kg » (Σ net) | « X kg revenus, déduits » ou « aucun retour » |
| Prévu par la recette | « X kg » (Σ prévu des ordres avec recette) | « N ordre(s) selon recette » |
| Écart | Étiquette `EcartRecette` de (sorti net des ordres avec recette − prévu) ÷ prévu, ou « — » | « X kg sortis pour Y prévus » |

`EcartRecette` (:101-110) : |écart| ≤ 5 % → vert (ok) ; > +5 % → attention ; < −5 % → critique ; texte « +12,3 % » / « −12,3 % ».

**Filtres** : recherche « Un ordre, une qualité, une référence, un lot… plusieurs mots affinent » (n° d'ordre, commentaire, lots, références, qualités) ; « Du » / « Au » (un ordre passe si sa fin ≥ Du et son début ≤ Au) ; « Effacer les filtres » ; note à droite « le plus récent d'abord · « Suivre » : quelles matières et quels lots sont partis dans l'ordre ».

**Tableau** (`Cadre taille="court"`) :

| Colonne | Contenu | Format |
|---|---|---|
| Ordre | **OF-…** | — |
| Date | début ; note « → fin » si différente | — |
| Fabrication | par qualité : **code** + note « X m² » ; ou note « hors recette » (infobulle = commentaire) | — |
| Prévu par la recette | kg entier ou « — » | droite |
| Sorti net | **kg** ; note « dont X revenus » | droite |
| Écart | Étiquette `EcartRecette` | droite |
| Matières | `Liste` des références sorties (≤ 2 : « a · b », sinon « N matières » + infobulle ; vide « — ») | — |
| Lots | `Liste` des lots (vide : « — sans lot ») | — |
| (sans titre) | bouton « Suivre » (infobulle « Quelles matières et quels lots sont partis dans cet ordre ») | — |

Ligne cliquable → suivi de l'ordre. **Vide** : « Aucun ordre ne correspond. » / « Aucun ordre de fabrication au journal. »

##### Fenêtre « Suivi de traçabilité » (Dialogue `tresLarge`)
- **Fichier** : Tracabilite.tsx:260-476. Ouverte par `?lot_id=`, `?ordre=` ou `?reference=` sur n'importe quel onglet du stock.
- **Titre** : « Traçabilité du lot {n°} » / « Ordre de fabrication OF-… » / « Parcours de la matière {REF} ».
- **Données** : `GET /api/tracabilite?lot_id|ordre|reference` (acteur) ; `GET /api/ordres-fabrication` (pour la comparaison par matière d'un ordre). Refus serveur : 400 « préciser un lot, un ordre de fabrication ou un fil » ; 404 « Lot introuvable. »
- **Fil d'Ariane** (`.fil-suivi`) : après un clic de suivi, bouton « ← Revenir au {lot N | ordre OF-… | matière REF} » et « Chemin : a → b → c » (pile locale, perdue à la fermeture) ; à droite, liens-boutons « Ouvrir l'ordre » (si ordre ; `/sorties?ordre=OF-…` ; infobulle « L'ordre de fabrication, ses lots et ses retours ») et « Fiche du lot » (si lot ; `/lot/ID` ; infobulle « La fiche du lot »).
- **Indicateurs** : « Entré » (X kg) ; « Sorti » (X kg) ; « Ordres servis » (sauf suivi d'ordre ; détail = 3 premiers) ; « Lots consommés » (suivi d'ordre) ou « Lots » (suivi de matière) — absent pour un lot ; dernier : « Matières » (ordre, nb) ou « Reste » (X kg = entré − sorti ; détail = références pour un lot). Entré/sorti ne comptent ni les annulations, ni les écritures annulées, ni les transferts ; un retour des machines réduit le sorti (pilotage.py:680-688).
- **Bascule** (ordre avec fabrications seulement) : « Prévu et sorti, par matière (N) » (défaut) / « Mouvements (N) ».
- **Sous-vue « Prévu et sorti, par matière »** : note « Tissé sous cet ordre : QUALITÉ — X m² · … . Matière par matière, ce que prévoyaient les recettes et ce qui est sorti net. » ; tableau `Cadre dialogue` : Référence (lien « Suivre cette matière » ; notes « · hors recette », « · pas sorti ») · Prévu par la recette (kg) (1 déc. ou « — ») · Sorti net (kg) · Écart (kg) · Écart (Étiquette %) ; pied « Total » avec prévu, net, écart, écart %.
- **Sous-vue « Mouvements »** (ou seule vue pour un lot / une matière / un ordre hors recette) : note « Le plus récent en haut. Cliquer un lot, un ordre ou une matière suit la matière de l'autre côté. » ; colonnes Date · Mouvement (libellé local : « Stock d'ouverture », « Entrée de réception », « Sortie vers les machines », « Retour des machines », « Retour au fournisseur », « Ajustement », « Transfert entre magasins » ; pour une annulation le libellé serveur « Annulation — … » + Étiquette « annulation » ; écriture annulée : Étiquette « annulé ») · Document (n°, mono, pas de lien) · Référence (lien de suivi sauf la matière suivie) · Quantité (« + » vert / rouge ; transfert sans couleur ni signe +) · Lot (lien de suivi par identifiant, sauf le lot suivi ; « — » si aucun) · Ordre (lien de suivi sauf l'ordre suivi) · Magasin (« source → destination ») · Par. **Vide** : « Aucun mouvement. »
- **Chargement** : « Un instant — chargement : la traçabilité… »

**Notions** : traçabilité dans les deux sens (lot → ordres ; ordre → lots et matières : « qu'y a-t-il dans ce tapis ? ») ; ordre de fabrication (OF-AAAA-NNNN) ; hors recette ; Prévu par la recette (perte comprise, figé à la validation) ; Sorti net (sorti − retours) ; Écart (kg et %), tolérance ±5 %.

---

#### Onglet « À valider » — `/stock?onglet=a-valider`
- **Fichiers** : components/stock/AValider.tsx.
- **Rôles** : tous voient la liste ; « Tout valider » côté serveur `STOCK` (achats, alimentation, direction). Qui peut valider quoi (brouillons.py:28-34, operations.py:28-34) : ordre → alimentation (+ direction) ; ouverture, ajustement, retour fournisseur → achats ; transfert → achats et alimentation ; retour des machines → alimentation.
- **Données** : `GET /api/brouillons` → `{lignes[{genre ordre|operation, type, id, date, libelle, resume, quantite, cree_par, cree_le, blocages[], peut_valider, lien}], nombre, bloques, validables}` ; tri serveur : date, puis rang (ouverture, transfert, ajustement, ordre, retour des machines, retour fournisseur), puis id. Résumé d'un ordre : « QUAL 1200 m², … · N lot(s) » ou « hors recette · N lot(s) » ; d'une opération : « motif · REF1, REF2 + N ».
- **Chargement / erreur** : « Un instant — chargement : les brouillons… ».

**Indicateurs** :

| Indicateur | Valeur | Détail | Ton |
|---|---|---|---|
| Brouillons | nb total | « ordres et opérations, le stock n'a pas bougé » | — |
| Seraient refusés | nb avec blocages | « lot épuisé, stock insuffisant, date… » ou « aucun blocage annoncé » | `critique` si > 0, sinon `ok` |
| Que vous pouvez valider | nb `peut_valider` (blocages compris) | « selon votre rôle » | — |

**Filtres** : recherche « Type, matière, motif, personne, raison… » (libellé, résumé, auteur, date, blocages) ; case « Seulement ceux qui seraient refusés » ; « Effacer les filtres » (si l'un posé) ; bouton « Tout valider (N) » à droite.

**Tableau** (`Cadre court`) : Date · Document (**libellé** « Ordre de fabrication » / « Transfert »… ; note « Brouillon ») · Contenu (résumé) · Quantité (1 déc., droite) · Par (auteur ; note horodatage) · À la validation (liste rouge « sera refusé : {raison} » ou Étiquette verte « passera » ; note « validé par l'alimentation » (ordre) / « validé par les achats » (opération) si ce compte ne peut pas valider) · lien-bouton « Ouvrir » (infobulle « Ouvrir le brouillon pour le corriger ou le valider seul ») → `lien` serveur : ordre `/sorties?onglet=brouillon&ordre=ID`, opération `/operations?onglet=TYPE&operation=ID`. Ligne entière en rouge pâle (`ligne-alerte`) si blocages. **Vide** : « Aucun brouillon ne correspond. » / « Aucun brouillon : tout ce qui a été saisi est validé. »

| Geste | Rôle | Conditions | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|---|
| Tout valider (N) (infobulle « Valide chaque brouillon que votre rôle permet, dans l'ordre des dates ; le stock bouge pour chacun ») | achats, alimentation, direction | grisé si N = 0 ou envoi en cours | « Valider N brouillon(s), du plus ancien au plus récent ? Ceux qui sont refusés restent en brouillon. » [Non] [Oui, tout valider] | `POST /api/brouillons/valider {brouillons: []}` (vide = tout ce que ce compte peut valider ; chaque brouillon dans sa transaction) | message « N brouillon(s) validé(s) : OF-…, TRF-…. » (vert si aucun refus, bleu sinon) + « N refusé(s), restés en brouillon : » puis liste « {libellé} du jj/mm/aaaa » (lien) « — {raison serveur} » | raisons = mêmes textes qu'une validation unitaire ; panne : « erreur inattendue : … » |
| Ouvrir | tous | — | — | — | navigue | (alimentation sur une opération : écran /operations réservé → retour à l'accueil) |

**Blocages annoncés** (serveur) — ordre (production.py:290-354) : « aucune matière à sortir » ; textes de `date_permise` ; « un ordre daté du jj/mm/aaaa est déjà validé : dater ce bon au moins de ce jour » ; « « MAG » est un magasin de quarantaine » ; « l'inventaire INV-… est en cours sur « MAG » » ; « qualité arrêtée : A, B » ; « lot N de REF : épuisé[ au jj/mm/aaaa] dans « MAG », X kg demandés » / « … : entré le jj/mm/aaaa, après la date de l'ordre dans … » / « … : X kg seulement[ au …] dans … » ; opération : « aucune ligne », date, « l'inventaire INV-… est en cours (MAG | tous les magasins) », lot insuffisant.

---

### 2. SORTIES VERS LES MACHINES — `/sorties`

#### Page « Sorties vers les machines » — `/sorties` (?onglet=valide|brouillon|annule, ?ordre=ID ou OF-…)
- **Fichiers** : pages/Sorties.tsx:57-261.
- **Titre** : « Sorties vers les machines ». **Sous-titre** : « Chaque ordre de fabrication : la matière partie, les retours, et l'écart avec ce que prévoit la recette. »
- **Rôles** : garde achats + alimentation (+ direction). Bouton « Nouvelle sortie » (en-tête) : `peut('alimentation')` = alimentation + direction ; les achats lisent seulement. Aucun prix nulle part (le serveur n'en donne pas sur `/bons`).
- **Adresse** : `?onglet=` lu (`valide` par défaut, l'onglet Validées n'écrit pas de paramètre) ; `?ordre=` (id ou n° OF) ouvre le détail ; écrits en `replace` en gardant les autres paramètres (Sorties.tsx:72-79).
- **Données** : `GET /api/bons` (acteur ; tous les ordres, le plus récent d'abord ; chaque ordre : `numero` (null en brouillon), `statut`, `date`, `magasin`, `metier`, `commentaire`, `cree_par/le`, `valide_par/le`, `fabrications[{qualite, nom, m2}]`, `lignes[{reference, lot, quantite, kg_par_ml…}]`, `total`, `retours[]` (n°), `retours_detail[{numero, date, quantite}]`, `revenu`, `theorique`, `net`, `ecart`, `ecart_relatif`, `par_fil[]`, `blocages[]`).
- **Chargement** : « Un instant — chargement : les sorties… » (rendu sans l'en-tête de page).

**Indicateurs** (Sorties.tsx:110-129) — calculés sur les ordres affichés (onglet + période + recherche) :

| Indicateur | Valeur | Détail | Ton |
|---|---|---|---|
| Ordres affichés | nb | « du jj/mm/aaaa au … » (« … » si borne vide) ou « toute la période » | — |
| Sorti net (onglet Brouillons : « À sortir ») | `quantite(Σ net, -, 0)` | Brouillons : « rien n'a encore bougé au stock » ; sinon « retours déduits : X kg revenus » ou « aucun retour » | — |
| Écart à la recette | « +X,X % » / « −X,X % » = (Σ net des ordres avec recette − Σ prévu) ÷ Σ prévu, ou « — » | « X kg sortis pour Y kg prévus » ou « aucun ordre selon recette » | `ok` si ≤ 5 %, sinon `attention` |
| Brouillons | nb de brouillons de la période | « N seraient refusés » ou « à valider » | `critique` si un brouillon bloqué, `attention` s'il y a des brouillons, sinon `ok` |

**Onglets** : « Validées » (compte) · « Brouillons » (compte) · « Annulées » (compte) — comptes filtrés par la période (pas par la recherche).

**Filtres** : recherche « N° d'ordre, qualité, fil, lot, métier, commentaire… » (n° ou « brouillon », métier, magasin, auteurs, commentaire, « qualité nom », « référence lot ») ; « Du » / « Au » (date de l'ordre) ; « Effacer les filtres » ; à droite lien « Exporter en Excel » → `/api/export/sorties?statut={onglet}&du&au` (infobulle « Les ordres de cet onglet (et de ces dates) dans un classeur Excel : qualités, m², prévu, sorti net, écart, retours » ; serveur acteur ; colonnes du classeur : Ordre (« Brouillon » si pas de n°), Date, Fabrication, m², Métier, Magasin, Prévu par la recette (kg), Sorti net (kg), Écart (kg), Écart, Revenu (kg), Retours, Commentaire, Par) ; onglet Brouillons avec au moins un brouillon : lien-bouton « Tout valider… » → `/stock?onglet=a-valider` (infobulle « Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout valider » »).

Note : « N ordre(s) · X kg à sortir à la validation. » (Brouillons) ou « N ordre(s) · X kg sortis nets, retours déduits (dont Y kg revenus). »
Message de succès (vert) persistant après une saisie/un retour (voir gestes).

**Tableau** (`Cadre court`, `table` non serrée) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Ordre | n° OF (mono) ou note « sans n° » ; si blocages : note rouge « sera refusé » (infobulle = raisons « · ») | — | — |
| Date | date | — | — |
| Fabrication | « QUAL · X m², … » ou note « hors recette » ; note commentaire | — | — |
| Métier | nom (ou code) du métier | — | — |
| Prévu par la recette | 1 déc. ou « — » | droite | perte comprise |
| Sorti net | brouillon : `total` ; sinon `net` (1 déc.) ; note « dont X revenus » | droite | — |
| Écart | `EcartOrdre` (même règle que `EcartRecette` : ±5 % vert, + attention, − critique ; 0 sans signe) | droite | — |
| Retours | n° des retours « RET-…, … » (ou « retour repris de l'ERP Fil du jj/mm/aaaa ») | — | — |
| Par | validé par, sinon créé par | — | — |

Ligne cliquable (écrit `?ordre=ID`) ; fond rouge pâle si blocages. **Vide** : « Aucun ordre ici. »

**Gestes de page**

| Geste | Où | Rôle | Conditions | Effet |
|---|---|---|---|---|
| Nouvelle sortie | en-tête | alimentation, direction | — | fenêtre « Nouvelle sortie vers les machines — Brouillon » |
| Effacer les filtres | filtres | tous | ≥ 1 filtre | — |
| Exporter en Excel | filtres | tous | — | `GET /api/export/sorties` |
| Tout valider… | filtres (onglet Brouillons) | tous | ≥ 1 brouillon | `/stock?onglet=a-valider` |
| clic ligne | tableau | tous | — | fenêtre détail d'ordre |

##### Fenêtre « Détail d'un ordre » (Dialogue `tresLarge`)
- **Fichier** : Sorties.tsx:263-431. Affichée si `?ordre=` trouve l'ordre et qu'aucune saisie/retour n'est ouverte.
- **Titre** : « OF-… — jj/mm/aaaa » ou « Ordre du jj/mm/aaaa » + Étiquette statut (« Brouillon » attention, « Validé » ok, « Annulé » neutre).
- **Ligne d'info** : « Magasin X · métier Y · saisi par Z le jj/mm/aaaa hh:mm · validé par W le … · « commentaire » ».
- **Indicateurs** : « Fabrication » (« X m² » total ou « hors recette » ; détail « QUAL X m² · … » ou « échantillons, série spéciale ») ; « Prévu par la recette » (`quantite` ou « — ») ; « Sorti net » / « À sortir » (brouillon : total) (détail « X kg sortis, dont Y kg revenus » si retours) ; « Écart » (Étiquette `EcartOrdre` ; détail « +X kg »).
- **Bandeau de blocages** (rouge) : « **Sera refusé à la validation :** » + liste des raisons.
- **Bascule** : « Lots sortis (N) » / « Lots à sortir (N) » (brouillon) — défaut ; « Prévu par la recette et sorti net, par matière (N) ». À côté : note « Retours : RET-… du jj/mm/aaaa (X kg) · … ».
- **Sous-vue Lots** : Référence (infobulle désignation) · Lot (lien `/lot/ID`) · Sorti / À sortir (`quantite` avec ml).
- **Sous-vue par matière** : Référence (+ Étiquette attention « hors recette ») · Prévu par la recette · Sorti net · Écart (« +X,X ») · Écart % (Étiquette). Si vide : « Calculé à la validation. » (brouillon) ou « Ordre hors recette : rien à comparer. »
- **Pied** : lien « Traçabilité de l'ordre » (si n° ; `/stock?onglet=ordres&ordre=OF-…` ; infobulle « Quels fils et quels lots sont partis dans cet ordre, et d'où ils venaient ») ; boutons selon statut ; « Fermer ».

| Geste | Rôle (écran) | Droit serveur | Conditions / grisé | Confirmation | Appel | Succès | Refus (textes serveur) |
|---|---|---|---|---|---|---|---|
| Supprimer (danger ; infobulle « Supprimer le brouillon : rien n'a bougé au stock ») | alimentation, direction ; brouillon | ALIMENTATION | — | « Supprimer ce brouillon ? » [Non] [Oui, supprimer] | `DELETE /api/bons/{id}` | « Brouillon supprimé. » puis fermeture de la fenêtre | « Un bon validé ne se supprime pas : l'annuler. » (409) · « Bon introuvable. » (404) · 403 « Cette action est réservée à : responsable alimentation machines. » |
| Modifier (infobulle « Rouvrir la saisie : qualités, lots, quantités ») | alimentation, direction ; brouillon | — | — | — | ouvre la saisie pré-remplie | — | — |
| Valider la sortie (principal ; infobulle « Valider : le stock sort et l'ordre reçoit son numéro ») | alimentation, direction ; brouillon | ALIMENTATION | grisé si envoi en cours ou blocages (raison visible dans le bandeau, pas dans l'infobulle) | « Sortir X kg du stock ? » [Non] [Oui, valider] | `POST /api/bons/{id}/valider` | « Ordre validé : le stock est sorti. » (fenêtre reste ouverte) | « Ce bon est déjà validé. » · `date_permise` · « Qualité arrêtée (A) : elle ne se tisse plus. La retirer de l'ordre, ou demander à la direction de la remettre en service. » · « À la date de l'ordre, {lots manquants}. Choisir un autre lot, ou dater l'ordre du jour où la matière était là. » · « Un ordre daté du jj/mm/aaaa existe déjà : les numéros suivent les dates, un bon ne se valide pas à une date antérieure. » · inventaire en cours · lot insuffisant · « Au jj/mm/aaaa, il n'y avait que X kg du lot … Choisir un autre lot, ou dater l'écriture après l'entrée de la matière. » |
| Faire un retour (infobulle « Ce qui revient des machines, lot par lot ») | alimentation, direction ; validé | — | — | — | ouvre « Retour des machines » | — | — |
| Annuler (contre-passation) (danger ; infobulle « Annuler (contre-passation) : une écriture inverse remet la matière en stock ») | alimentation, direction ; validé | ALIMENTATION | — | sans retours : « Annuler l'ordre ? Toute sa matière revient en stock, à la date de l'ordre. » ; avec retours : « Annuler l'ordre et ses retours (RET-…, …) ? La matière sortie revient en stock, une seule fois, à la date de l'ordre. » [Non] [Oui, annuler (contre-passation)] | `POST /api/bons/{id}/annuler` (contre-passe l'ordre, ses retours validés et les retours repris de l'ERP Fil) | « Ordre annulé. » | « Seul un bon validé s'annule ; un brouillon se supprime. » · « Ce document a déjà été annulé. » · inventaire en cours · période close |
| Fermer | tous | — | — | — | retire `?ordre=` | — | — |

##### Fenêtre « Nouvelle sortie vers les machines — Brouillon » / « Modifier l'ordre — Brouillon »
- **Fichiers** : components/production/SaisieSortie.tsx ; logique `pages/atelier/sortie.ts:167-470` (partagée avec le téléphone).
- **Rôles** : alimentation, direction (bouton d'ouverture) ; serveur `ALIMENTATION` pour `POST/PUT /bons` et valider ; `POST /bons/proposition` : acteur.
- **Dialogue** `tresLarge`, `sale` = saisie touchée (garde « Abandonner les modifications ? » sur ×, Échap, fond).
- **Données** : `GET /api/magasins`, `/api/metiers`, `/api/qualites` ; `GET /api/soldes?magasin_id=` (lots du magasin, pour l'ajout à la main et le disponible d'un brouillon rouvert) ; `POST /api/bons/proposition {magasin_id, date, fabrications[{qualite_id, m2}]}` ; `GET /api/inventaires` (suspension) ; `GET /api/bons` (date du dernier ordre validé).
- **Bandeaux d'empêchement** (rouges, en tête ; `useEmpechements`, Envoyer.tsx:59-70) : inventaire ouvert sur le magasin (ou tous) : « L'inventaire INV-… (MAG, du jj/mm/aaaa) est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre. » ; date antérieure au dernier ordre validé : « Un ordre du jj/mm/aaaa est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du jj/mm/aaaa et écrire la vraie date dans le commentaire. »

**Formulaire (demande)** :

| Champ | Type | Défaut | Contrôle |
|---|---|---|---|
| Date | date, max = aujourd'hui (heure de l'usine) | aujourd'hui (ou date du brouillon) | serveur `date_permise` |
| Magasin de sortie | liste des magasins actifs non quarantaine (codes) | magasin courant actif le plus garni (`magasinParDefaut`) ou celui du brouillon | aide « changer de magasin efface les lots choisis » si des lots sont pris ; changer efface toutes les prises |
| Métier | liste « — » + métiers actifs (ou celui du brouillon) triés par nom puis code, libellé « CODE · Nom » | aucun | serveur « Métier inconnu. » |
| Commentaire | texte, max 300, placeholder « Équipe, consigne, incident… » | — | — |

**Section « 1 · Ce qu'on tisse »** : Bascule « Selon les recettes » (défaut) / « Ordre hors recette » ; note « Une qualité une seule fois ; un fil qui sert plusieurs qualités sort une fois, pour la somme de ses besoins. » ou « Échantillons, série spéciale : ajouter les fils à la main. ». Tableau de saisie (recettes) : Qualité (choix par recherche « Code ou nom de la qualité… », qualités actives non déjà choisies, libellé « CODE — Nom ») · m² à tisser (nombre) · « Retirer » (s'il y a plus d'une qualité). Boutons : « + Une autre qualité » ; « Proposer les fils à sortir » / « Recalculer les fils » (infobulle « Calcule les fils d'après les recettes et propose les lots les plus anciens » ; principal tant qu'aucune proposition ou si la demande a changé ; grisé si demande incomplète — magasin, date, chaque qualité choisie avec m² > 0 — ou envoi en cours). Note si la demande a changé : « La demande a changé : recalculer remplace les lots proposés (les fils ajoutés à la main restent). »

Proposition serveur (production.py:190-237) : par matière de la recette, besoin = kg/m² × m² × (1 + taux de perte) ; lots du magasin hors quarantaine, du plus ancien au plus récent, **tels qu'ils étaient à la date de l'ordre** ; `manque` = ce qui n'a pas pu être couvert ; `recettes_incompletes` : « QUAL : le rôle R pèse X au m², mais la recette ne nomme aucune matière pour lui : rien ne lui est proposé. La direction doit compléter la recette. » ou « QUAL : le rôle R fait X % dans la recette au lieu de 100 % : sa proposition est faussée. La direction doit corriger la recette. » Refus : « Qualité inconnue. » (404), « La qualité Q est arrêtée : elle ne se tisse plus. La direction la remet en service (Qualités) si une série doit encore partir. »

**Section « 2 · Les fils qui sortent »** : messages rouges « Recette incomplète — {texte} » ; message bleu si un manque > 0,05 kg : « Il manque dans ce magasin : REF (X kg) · … . Les transférer d'abord, ou sortir ce qu'il y a : l'écart restera visible sur l'ordre. »

Tableau (`table.saisie.serre`, `Cadre dialogue`) — un groupe de lignes par fil (rowSpan) :

| Colonne | Contenu | Remarque |
|---|---|---|
| Fil | **référence** ; note rôle ou « hors recette » ; liste « + un autre lot… » (autres lots disponibles : « LOT — X kg ») | infobulle désignation |
| Prévu par la recette | prévu (1 déc.) ; note « N qualités » si plusieurs ; infobulle « QUAL : X kg · … » | « — » hors recette |
| Lot | n° (mono) | — |
| Dans ce lot | disponible du lot dans le magasin (`quantite`) ou « … » (pas encore lu) | — |
| Unité | liste « kg » / « bobines (X,XX kg) » / « palettes (N bob.) » si possibles, sinon « kg » | changer d'unité convertit (bobine entière, palette au centième) et note « arrondi : X kg au lieu de Y kg » |
| Quantité | champ nombre | — |
| Sorti | kg de la ligne (quantité × contenance) ; « poids de bobine inconnu » en rouge ; note rouge « plus que le lot » si dépassement | — |
| Écart du fil | `EcartFil` : « conforme » (vert) si |écart| < 0,05 kg ou < 0,5 % ; sinon « +X kg (+Y %) » neutre si ≤ 5 %, attention si positif, critique si négatif | rowSpan |
| (sans titre) | lien « retirer » (infobulle « Ne pas prendre ce lot ») | — |

Ligne sans lot pris : « aucun lot pris[ — rien dans ce magasin] » (rouge pâle si manque). Ligne de prise en rouge pâle si quantité > disponible. Ligne vide du tableau : « Choisir ce qu'on tisse puis « Proposer les fils à sortir » — ou ajouter un fil à la main. » (recettes) / « Ajouter un fil ci-dessous. » (hors recette). **Pied** : « Total » · prévu total (1 déc. ou « — ») · … · sorti total (`quantite`) · écart total (`EcartFil`).
Sous le tableau : choix par recherche « + Ajouter un fil hors recette : référence ou lot… » (ou « + Ajouter un fil : référence ou lot… » hors recette) parmi les lots du magasin disponibles > 0 non encore pris, libellé « REF · lot N », détail « X kg ».

Un brouillon rouvert : les lignes reviennent en bobines si le poids tombe sur un nombre entier de bobines (sortie.ts:117-129) ; le prévu se relit par la proposition à la date de l'ordre.

**Pied de fenêtre** : note « N ligne(s) · X kg » ; boutons :

| Geste | Conditions / grisé | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|
| Fermer | — ; si saisie touchée : Confirmer « Abandonner cette saisie ? » [Non] [Oui, abandonner] (infobulle « Fermer sans enregistrer ») | voir à gauche | — | — | — |
| Garder en brouillon (infobulle « Enregistrer sans sortir le stock : l'ordre reste modifiable » ; « Enregistrement… » pendant) | grisé si aucune ligne > 0, une ligne sans contenance, ou envoi en cours (pas d'infobulle de raison) | — | `POST /api/bons` (nouveau) ou `PUT /api/bons/{id}` `{date, magasin_id, metier_id, commentaire, fabrications (vide hors recette), lignes[{article_id, lot_id, quantite, unite}]}` | fermeture ; message de page « Ordre gardé en brouillon : le stock n'a pas bougé. » ; onglet Brouillons + détail ouvert | « Magasin inconnu. » · « La matière en quarantaine ne part pas aux machines : la libérer d'abord (transfert « Libération de quarantaine », décidé par les achats). » · « Métier inconnu. » · `date_permise` · « Une qualité ne figure qu'une fois sur un ordre : additionner ses m². » · qualité arrêtée/inconnue · « Lot inconnu, ou d'une autre matière. » · « Unité : kg, bobine ou palette — le cuir, les franges et le ruban se comptent aussi en kilos. » · « « REF » : le nombre de bobines par palette n'est pas connu, saisir en bobines ou en kg. » · « « REF » : le poids de bobine n'est pas connu, saisir en kg. » · PUT d'un validé : « Un bon validé ne se modifie plus : l'annuler, puis en faire un autre. » (409) |
| Valider la sortie (principal ; « Enregistrement… » pendant) | grisé si aucune ligne, dépassement d'un lot, ligne sans contenance, envoi en cours ou empêchement ; infobulle « Validation impossible pour l'instant (voir le bandeau en tête) » si empêchement, sinon « Valider : le stock sort et l'ordre reçoit son numéro » | « Sortir X kg le jj/mm/aaaa (aujourd'hui|hier) · MAG · CODE · Métier ? Le stock est débité tout de suite. » [Non] [Oui, valider la sortie] | enregistre (POST/PUT) puis `POST /api/bons/{id}/valider` | fermeture ; « Ordre OF-… validé : X kg sortis. » ; onglet Validées + détail ouvert | refus d'enregistrement ci-dessus ; refus de validation suffixé « — l'ordre est gardé en brouillon, modifiable. » (la fenêtre reste ouverte, l'ordre existe désormais en brouillon) |

**Notions** : ordre de fabrication (n° OF-AAAA-NNNN donné à la validation, dans l'ordre des dates ; « un ordre sert une fois, un jour ») ; brouillon (le stock ne bouge pas) ; selon recette / hors recette ; qualité, m² ; prévu par la recette perte comprise ; FIFO (lots les plus anciens) à la date de l'ordre ; manque ; unités de saisie kg/bobine/palette (stock toujours en kg) ; contenance ; magasin de quarantaine exclu ; métier ; empêchements (inventaire, date) ; numéros qui suivent les dates.

##### Fenêtre « Retour des machines — OF-… »
- **Fichier** : components/production/RetourBureau.tsx.
- **Rôles** : bouton visible pour alimentation + direction sur un ordre validé ; serveur `POST /operations` (STOCK puis type `retour_machine` réservé à l'alimentation : « « Retour des machines » est réservé à : responsable alimentation machines. »).
- **Données** : `GET /api/bons/{id}/lots-sortis` (lot par lot, net des retours, > 1 g) ; `GET /api/operations/motifs` ; `GET /api/magasins` ; `GET /api/inventaires`.
- **Dialogue** `tresLarge`, `sale` si une quantité > 0 ou un commentaire.
- Bandeau rouge de suspension d'inventaire (même texte que la saisie de sortie).

**Formulaire** :

| Champ | Type | Défaut | Contrôle |
|---|---|---|---|
| Date du retour | date, min = date de l'ordre, max = aujourd'hui | aujourd'hui | serveur : « Ce retour est daté du jj/mm/aaaa, avant l'ordre OF-… du jj/mm/aaaa : la matière n'était pas encore partie. Dater le retour du jour où elle est revenue. » |
| Ranger dans le magasin | magasins actifs non quarantaine | magasin de l'ordre | — |
| Pourquoi revient-elle ? | liste : « R1 · Reliquat de fin d'ordre », « R2 · Changement de série / arrêt machine », « R4 · Erreur de prélèvement » | le premier | serveur « Choisir le motif : il dit pourquoi le stock bouge. » |
| Commentaire | texte max 300, placeholder « Bobines entamées, arrêt du métier… » | — | — |

Message bleu si rien n'est revenable : « Tout ce qui est parti sur cet ordre est déjà revenu. »
**Tableau** (`table.saisie.serre`, `Cadre dialogue`) : Référence · Lot (mono) · Parti (net) (`quantite`) · Unité (liste kg/bobines/palettes, conversion à la volée) · Revient (champ nombre) · Soit (kg ; note rouge « plus que ce qui est parti » ; ligne rouge pâle si dépassement) · lien « tout » (remplit en kg tout le net parti, arrondi vers le bas au gramme).
**Pied** : raison grise à gauche : « Un inventaire est en cours (voir le bandeau) » / « N lot(s) dépassent ce qui est parti » / « Saisir ce qui revient, lot par lot » ; « Fermer » ; bouton principal.

| Geste | Conditions | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|
| « Remettre X kg en stock » (« Enregistrement… » pendant ; infobulle « Le retour est validé tout de suite : le stock remonte ») | grisé si raison ci-dessus, pas de motif, envoi en cours | « Remettre X kg en stock (MAG) ? » [Non] [Oui, enregistrer le retour] | `POST /api/operations {type:'retour_machine', date, bon_id, motif, commentaire, lignes[{article_id, lot_id, magasin_id, quantite, unite}]}` puis `POST /api/operations/{id}/valider` ; échec → brouillon supprimé | fenêtre fermée ; message de page « RET-… enregistré : la matière est revenue en stock. » | « Un retour des machines se rattache à l'ordre d'où la matière revient. » · « Le lot « N » n'est sorti que de X kg pour cet ordre (Y kg rendus) : on ne rend pas plus que ce qui est parti. » (409) · date antérieure à l'ordre · inventaire · « Le magasin « X » est désactivé : il ne reçoit plus rien. » · `date_permise` · unités |
| tout | — | — | — | remplit la ligne | — |
| Fermer | — | — (ferme directement) | — | — | — |

**Notions** : retour des machines (RET-…), motifs codés R1/R2/R4 (codes de l'ERP Fil), net parti par lot, on ne rend jamais plus que ce qui est parti, retour validé tout de suite.

---

### 3. PRODUCTION & BESOINS — `/production`

#### Page « Production & besoins » — `/production` (?onglet=plan|glissant|realise|besoins ; ancien ?volet=)
- **Fichiers** : pages/Production.tsx ; components/production/* ; production.css.
- **Rôles** : tous (pas de garde ; menu achats + alimentation + direction). `direction = compte.role === 'direction'` : seule la direction modifie le plan (serveur `DIRECTION`). `versPlanAchat` = direction ou achats (boutons « Ouvrir le plan d'achat → »). Aucun prix dans cet écran.
- **Titre** : « Production & besoins ». **Sous-titre** : « Plan glissant sur douze mois dès {mois année} (base mensuelle × saisonnalité) ; les besoins matière en découlent par les recettes, perte comprise. » + « Lecture seule : seule la direction modifie le plan. » pour les autres rôles.
- **Adresse** : onglet lu ; écrit en `replace` : Plan → aucune adresse (`{}`), autres → `?onglet=X` seul.
- **Données** : `GET /api/production/plan` (acteur) ; `GET /api/production/realise` (acteur) ; `GET /api/production/besoins` (acteur ; chargé seulement à l'ouverture de l'onglet Besoins).
- **Chargement / erreurs** : « Un instant — chargement : le plan de production… » ; erreur → page avec message « {erreur} » ou « Le plan de production est indisponible. » ; réalisé : « Un instant — chargement : le réalisé… » / « Le réalisé est indisponible. » ; besoins : « Un instant — chargement : les besoins matière… » / « Les besoins sont indisponibles. »
- **Saisie non enregistrée** : le brouillon du plan (par qualité) survit au changement d'onglet ; fermer/recharger l'onglet du navigateur déclenche l'avertissement natif `beforeunload`.

**Indicateurs** (masqués sur l'onglet Besoins matière) — Production.tsx:96-131 :

| Indicateur | Valeur | Formule / détail | Ton |
|---|---|---|---|
| Plan des douze mois à venir | « X m² » = Σ `total_glissant` | « X m² par mois en moyenne · N qualité(s) » (qualités avec plan > 0) | — |
| Mois en cours | « X m² » tissés (Σ tissé du mois + tissé hors plan) | « tissés sur Y prévus (Z %) · W % du mois écoulé » ou « aucun plan ce mois-ci » | `attention` si plus de 20 % du mois écoulé et avancement < prorata − 15 points |
| Écart au plan, mois clos | `signe((tissé − prévu) ÷ prévu)` sur les mois clos depuis le premier ordre ; « … » en chargement ; « — » sans mois jugé | « X m² tissés pour Y prévus (N mois) » / « chargement » / « pas encore de mois clos depuis le premier ordre de fabrication » | `ok` si |écart| ≤ 10 %, sinon `attention` |
| Matière nécessaire sur douze mois (infobulle « Les fils, et le cuir, les franges, le ruban (leurs mètres × densité) : les mêmes kilos que les besoins matière ») | « X kg » = Σ total_glissant × kg/m² | « perte de X,X % comprise » | — |

**Onglets** : « Plan de production » (compteur « N modifiée(s) » si saisie en cours) · « Plan glissant » · « Plan et réalisé » · « Besoins matière » (compteur = nb de références avec besoin du plan > 0 ou retenu > 0, dès que les besoins ont été chargés).

---

#### Onglet « Plan de production » — `/production` (sans paramètre)
- **Fichier** : components/production/VoletPlan.tsx.
- **Rôles** : modifiable = direction ; autres : cellules en lecture (`nombre`), pas de boutons, note « Lecture seule : seule la direction modifie le plan. »
- **Carte** titre « Plan de production — m² par qualité » + Bascule « Coefficients » (défaut) / « m² par mois ». En-tête droit : recherche « Qualité, nom… » (code, nom) ; case « Inactives (N) » (si des qualités inactives) ; direction et saisie en cours : « Tout annuler », « Enregistrer tout (N) » (« Enregistrement… »).
- **Lignes affichées** : qualités actives, + inactives si la case est cochée, + toute qualité modifiée.

**Tableau** (`prod-table prod-plan`, première colonne figée, pied figé, `Cadre court`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Qualité | **code** ; note nom ; (direction, ligne modifiée) liens « Enregistrer » · « Annuler » | figée, infobulle nom | ligne modifiée : filet bleu à gauche ; inactive : texte grisé |
| Base / mois (sous-titre « m² » ou « moyenne » ; infobulle « Les m² d'un mois ordinaire (coefficient 1) » / « La moyenne des douze mois ») | champ nombre (direction, mode Coefficients ; ≥ 0) ; sinon valeur | droite | en mode m², la base est recalculée |
| Janv. … Déc. (sous-titre « coef. » ou « m² » ; mois civil courant surligné) | mode Coefficients : champ coefficient (pas 0,05, affiché arrondi à 3 déc.) ; mode m² : champ m² arrondi (pas 1) ; lecture : « 1,20 » ou « 1 234 » | droite ; infobulle « Mois : X m² » / « Mois : coefficient 1,234 » ; lecture : « X m² » / « coefficient 1,20 » | coefficient hors [0 ; 20] : cellule rouge, infobulle « Un coefficient reste entre 0 et 20 » |
| Total / an (« m² ») | **Σ base × coef.** ; note « coef. moyen 1,08 » si la moyenne des coefficients s'écarte de 1 de plus de 0,05 (infobulle « Les coefficients ne se compensent pas : l'année diffère de 12 × la base ») | droite | — |
| État | Étiquette « inactive, hors plan » (neutre) / « sans recette » (critique : base > 0 et aucune ligne de recette) / « recette incomplète » (attention) / « au plan » (ok, base > 0) / note « pas de plan » | — | — |

Saisie en m² (`depuisM2`, VoletPlan.tsx:48-53) : la base devient la moyenne des 12 mois (arrondie à 0,01) et chaque coefficient = m² du mois ÷ base (6 déc.) ; base ≤ 0 → base 0 et coefficients 1.
**Pied** : « Total (m²) » · Σ bases · Σ par mois · Σ annuel · note « qualités actives affichées » (seules les actives comptent).
**Vide** : « Aucune qualité ne correspond. » / « Aucune qualité : créez-les dans l'écran Qualités & recettes. »
**Note sous le tableau** : « Un coefficient de 1,2 en janvier veut dire « 20 % de plus que la base en janvier ». » (ou « En m² par mois, la base devient la moyenne des douze mois et les coefficients en découlent. ») + « Les colonnes sont les mois de l'année ; le plan glissant les lit dans l'ordre des mois à venir[, avec la croissance annuelle de X %]. » + « Une ligne modifiée est marquée d'un filet bleu tant qu'elle n'est pas enregistrée. » (direction).

| Geste | Rôle | Conditions | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|---|
| Coefficients / m² par mois | tous | — | — | — | — | — |
| Enregistrer (ligne) | direction | ligne modifiée ; grisé pendant l'envoi | aucune | `PUT /api/qualites/{id}/plan {base_mensuelle, saisonnalite[12]}` | « Plan de CODE enregistré : besoins en fil et plan d'achat sont recalculés. » ; tout se relit | « Un coefficient de saisonnalité reste entre 0 et 20. » · « Qualité introuvable. » (404) · 403 « Cette action est réservée à : la direction. » |
| Annuler (ligne) | direction | ligne modifiée | aucune | — | oublie la saisie de la ligne | — |
| Tout annuler | direction | saisie en cours ; grisé pendant l'envoi | aucune | — | vide le brouillon | — |
| Enregistrer tout (N) | direction | grisé pendant l'envoi ou si un coefficient est hors [0 ; 20] (pas d'infobulle) | aucune | `PUT /api/production/plan {lignes[{qualite_id, base_mensuelle, saisonnalite}]}` (tout ou rien) | « Plan enregistré pour N qualité(s) : besoins en fil et plan d'achat sont recalculés. » | « Une qualité apparaît deux fois dans le plan envoyé. » · « Qualité introuvable : le plan n'a pas été enregistré. » (404) · « CODE : un coefficient de saisonnalité reste entre 0 et 20. Rien n'a été enregistré. » |

Chaque enregistrement trace la version du plan (avant/après) au journal des actions : le passé reste jugé sur le plan en vigueur à son époque (production_plan.py:42-74).

**Notions** : base mensuelle (m² d'un mois ordinaire), coefficients de saisonnalité (0 à 20), total annuel, coefficient moyen, croissance annuelle, qualité active/inactive, recette (absente, incomplète, conforme).

---

#### Onglet « Plan glissant » — `/production?onglet=glissant`
- **Fichier** : VoletGlissant.tsx. **Rôles** : tous, lecture seule.
- **Carte** « Plan glissant — m² planifiés » + Bascule « Tableau » (défaut) / « Graphique » ; recherche « Qualité, nom… ».
- Message bleu si saisie non enregistrée : « N qualité(s) modifiée(s) dans le plan de production ne sont pas encore enregistrées : le plan glissant les montrera une fois enregistrées. »
- **Lignes** : qualités avec plan glissant > 0 ou déjà tissées ce mois.

**Tableau** (`prod-table`, `Cadre court`) : Qualité (figée ; **code** + note nom) · 12 mois à venir (libellé « oct. 2026 », sous-titre « en cours » pour M0 surligné, puis « M+1 »… ; valeur m² ou « — » ; pour M0 note « tissé X · Y % » avec infobulle « Déjà tissé ce mois-ci, d'après les ordres de fabrication ») · Total (« 12 mois », gras) · Fil (« kg/m² », infobulle « Fil consommé par m², perte comprise » ; 2 déc. ; « — » rouge avec infobulle « Aucune recette : ce plan ne tire aucun fil »).
**Pied** (figé) : « Total (m²) » par mois (+ note « tissé X » sous M0) et total ; « Matière nécessaire (kg) » (infobulle « Le poids de tout ce que ce plan consommera, perte comprise : les fils, et le cuir, les franges, le ruban (leurs mètres × densité) — les mêmes kilos que les besoins matière. ») par mois et total.
**Graphique** : barres empilées par mois, les 7 plus grosses qualités + « Autres » (gris), infobulle « X m² ».
**Vide** : « Aucune qualité ne correspond. » / « Aucune qualité au plan : saisissez une base mensuelle dans le plan de production. »
**Note** : « Base mensuelle × coefficient du mois[ × croissance annuelle de X % (comptée depuis la saisie de la base)], arrondi au m². Le fil nécessaire suit les recettes, perte de X % comprise.[ N qualité(s) sans plan ou inactive(s) ne sont pas affichées.][ Tissé ce mois-ci hors plan : QUAL (X m²), ….] »

---

#### Onglet « Plan et réalisé » — `/production?onglet=realise`
- **Fichier** : VoletRealise.tsx. **Rôles** : tous, lecture seule.
- **Données** : `/production/realise` → `{mois[12 écoulés, le dernier = mois en cours], mois_clos, lignes[{qualite, plan[], realise[], total_plan, total_realise, ecart}]}` ; chaque mois clos jugé sur le plan **en vigueur pendant ce mois**.
- **Carte** « Plan et réalisé — m², douze mois écoulés » + Bascule « Tableau » / « Graphique » ; en-tête : recherche « Qualité… » (tableau) ou liste « Toutes les qualités » + chaque qualité (graphique).

**Tableau** (`prod-table prod-realise`) — deux lignes par qualité (fond alterné par qualité) :

| Colonne | Contenu |
|---|---|
| Qualité (figée, rowSpan 2 ; infobulle « Cliquer pour voir son graphique ») | **code** |
| (libellé) | « prévu » / « tissé » |
| 12 mois | prévu (gris) / tissé (« — » si 0) ; en-tête « en cours » pour les mois non clos, « non compté » (infobulle « Avant le premier ordre de fabrication : hors écart ») avant le premier tissage |
| Total | total prévu / **total tissé** |
| Écart (« mois clos » ; infobulle « Tissé face au plan, sur les mois clos ») (rowSpan 2) | Étiquette `signe(écart)` : ≤ 10 % ok, > +10 % attention, < −10 % critique ; « — » (infobulle « Aucun mois clos depuis le premier ordre de fabrication ») ; note « hors plan » |

Teinte des cellules « tissé » des mois clos (depuis le premier tissage) : rouge gras si < −10 % du prévu, orange gras si > +10 %. Clic sur une des deux lignes → passe en Graphique, qualité choisie (ligne surlignée en bleu pâle).
**Graphique** : barres « Plan » (gris) et « Tissé » par mois, toutes qualités ou la qualité choisie.
**Vide** : « Aucune qualité ne correspond. » / « Aucune qualité au plan, et aucun ordre de fabrication. »
**Note** : « Tissé d'après les ordres de fabrication ; en rouge un mois clos à plus de 10 % sous le plan, en orange au-dessus ; un clic sur une qualité ouvre son graphique. Le prévu passé suit le plan actuel ; les mois d'avant le premier ordre ne comptent pas. Un écart durable dit qu'il faut revoir la base ou la saisonnalité de la qualité. »

**Notions** : mois clos, mois en cours, début de production (premier mois tissé), écart au plan (±10 %), tissé = m² des ordres de fabrication.

---

#### Onglet « Besoins matière » — `/production?onglet=besoins`
- **Fichier** : VoletBesoins.tsx. **Rôles** : tous ; « Ouvrir le plan d'achat → » pour direction et achats (`/plan-achat`, garde achats).
- **Données** : `GET /api/production/besoins` → `{mois[12], taux_perte, fenetre_realisation_jours, roles[], lignes[{reference, nature, designation, fournisseur, role, kg_par_ml, kg[12], total, retenu[12], total_retenu, coefficient_realisation, conso_reelle, stock_disponible, bc_en_cours, stock_projete, couverture_jours, statut, quantite_a_commander, unite_achat, quantite_a_commander_achat, qualites[{qualite, kg_m2, kg[], total}]}]}` (aucun prix).
- **Carte** titre « Besoins matière (MRP) » (infobulle « En kg, le cuir, les franges et le ruban compris (leurs mètres en infobulle). {explication} ») + Bascule « Besoin du plan » (défaut) / « Retenu par le plan d'achat ». En-tête droit : note « N référence(s)[ · M à commander] » (infobulle = explication) ; bouton « Ouvrir le plan d'achat → » (infobulle « Ce qu'il faut commander, regroupé par fournisseur »).
- Explication : « Besoin du plan : m² planifiés × kg/m² des recettes (pour le cuir, les franges, le ruban : leurs ml/m² × la densité), majorés de la perte de X %. » ou « Retenu par le plan d'achat : le besoin du plan corrigé par le rapport entre le consommé et le prévu des derniers mois clos (fenêtre de N jours, entre × 0,5 et × 1,5). » + « Cliquer sur une référence pour voir les qualités qui la tirent. »
- **Filtres** (non liés) : recherche « Référence, couleur, fournisseur, qualité… » (référence, nature, désignation, fournisseur, rôle, qualités) ; « Tous les rôles » (infobulle « Rôle dans la recette » ; rôles du référentiel présents) ; « Tous les fournisseurs » ; tri (infobulle « Ordre des lignes ») : « Les plus lourdes d'abord » (défaut, total de la lecture), « Couverture la plus courte », « Par référence », « Par fournisseur » ; case « Avec besoin seulement » (cochée par défaut). Pas de bouton « Effacer les filtres ».

**Tableau** (`prod-table`, `Cadre court`) :

| Colonne | Contenu | Format |
|---|---|---|
| Référence (figée) | référence ; note « nature · désignation » | infobulle référence |
| Rôle | rôle ou « — » | — |
| Fournisseur | nom ou « — » | — |
| 12 mois (« oct. 2026 », « en cours » / « M+i ») | kg (selon la lecture) ou « — » | droite |
| Total (« 12 mois ») | **kg** ; note « ≈ N ml » ; en lecture Retenu, note « × 0,00 » (infobulle « Réel ÷ plan sur les derniers mois clos ») | droite |
| Disponible (infobulle « Stock disponible aujourd'hui, hors quarantaine ») | kg | droite |
| Couverture (infobulle « Jours de consommation couverts par le stock projeté ») | Étiquette « N j » / « — », teinte selon le statut de stock (`tonStatut`) ; « — » sans statut | droite |
| À commander (infobulle « Ce que le plan d'achat propose de commander ») | **kg** ou « — » ; note « ≈ N ml » | droite |

Ligne cliquable (infobulle « Les qualités qui tirent cette matière ») → fenêtre détail. **Pied** : « Total (kg) » · Σ par mois · Σ total · Σ disponible · (vide) · Σ à commander. **Vide** : « Aucune référence ne correspond. » / « Aucun besoin : le plan de production est vide ou les recettes ne sont pas saisies. »

##### Fenêtre « {REF} — d'où vient le besoin » (Dialogue `tresLarge`)
- **Fichier** : VoletBesoins.tsx:252-379. Note « rôle · nature · désignation · fournisseur ».
- **Indicateurs** : « Besoin du plan » (« X kg » ; « douze mois, perte comprise[ · ≈ N ml] ») ; « Retenu par le plan d'achat » (« X kg » ; « corrigé par le réel : × 0,00 (+N %) » / « hors plan : la consommation réelle prolongée » / « pas encore de consommation pour corriger le plan » ; ton attention si |coef − 1| > 0,15) ; « Disponible » (`kgEtMetres` ; « X kg en commande · couverture N j ») ; « À commander » (« X kg » ou « rien » ; détail « ≈ N ml, à titre indicatif » ou statut ; ton du statut).
- **Tableau** (`Cadre dialogue`) : Qualité (figée) · kg/m² (3 déc. ; infobulle « Fil de cette référence par m² de la qualité, perte comprise ») · 12 mois · Total ; vide : « Aucune qualité au plan n'utilise cette référence. » ; pied « Besoin du plan » (mois, total) et « Retenu (achats) » si l'écart des totaux > 0,5 kg.
- Bouton « Ouvrir le plan d'achat → » (direction, achats) → `/plan-achat`.

**Notions** : MRP, besoin du plan (m² × kg/m² × (1 + perte)), retenu par le plan d'achat (corrigé par le coefficient de réalisation = réel ÷ plan sur la fenêtre, borné × 0,5 à × 1,5), hors plan (consommation réelle prolongée), rôle dans la recette, densité kg/ml (mètres indicatifs), couverture, à commander.

---

### Incohérences et anomalies repérées

1. **Vocabulaire « fil » en en-tête de colonne** (REGLES §3 : colonne « Référence ») : SaisieSortie « Fil » (components/production/SaisieSortie.tsx:163) et « Écart du fil » (:170) ; recherche Sorties « N° d'ordre, qualité, fil, lot… » (pages/Sorties.tsx:141) ; infobulle « Quels fils et quels lots… » (Sorties.tsx:382) ; Plan glissant colonne « Fil » (VoletGlissant.tsx:83-86).
2. **« Journal » employé pour les mouvements de stock** (réservé au Journal des actions) : infobulle « Le journal filtré sur cette matière » (StockParMatiere.tsx:580) ; vide « Aucun ordre de fabrication au journal. » (Tracabilite.tsx:184).
3. **Brouillon sans le mot « Brouillon »** : la colonne Ordre affiche « sans n° » (Sorties.tsx:203) au lieu de « Brouillon » (REGLES §2 Numéros) ; l'export, lui, écrit « Brouillon » (production.py:633).
4. **En-tête « Sorti net » sur l'onglet Brouillons** alors que rien n'est sorti (la cellule montre `total`) : Sorties.tsx:193, 214 ; l'indicateur dit pourtant « À sortir » (:113).
5. **Bascule maison au lieu du composant `Bascule`** (role="tablist", classes locales) : StockParMatiere.tsx:386-392 ; la vue n'est pas dans l'adresse.
6. **Définitions contradictoires de « Disponible » et « Stock »** : le serveur compte le stock en machine dans le disponible (moteur.py:1188) mais l'aide de la vue « Où se trouve la matière » dit « Les magasins, hors quarantaine » (StockParMatiere.tsx:227) et la fiche « magasins, hors quarantaine » (:592) ; l'aide « Sur les métiers » dit « compté dans le stock » (:184, 226, 589) alors que la colonne « Stock » (`stock_net`, magasins seulement) ne l'inclut pas.
7. **Indicateur « Critiques » : « sous le seuil critique »** (StockParMatiere.tsx:373) alors que le compte porte sur le statut appliqué (projeté ≤ 50 % du seuil d'alerte), pas sur le seuil critique de couverture des réglages (qui définit le « Statut classeur »). Libellé « Statut classeur » = jargon du tableur (:182).
8. **Code mort / doublons** : pied de tableau, deux branches identiques `if (!c.quantite)` (StockParMatiere.tsx:483-492) ; `tonStock` (StockParMatiere.tsx:131) double `tonStatut` (lib/format.ts:126) ; `EcartOrdre` (Sorties.tsx:42) double `EcartRecette` (Tracabilite.tsx:101) ; classe CSS `.ouvrable` jamais utilisée (stock-bureau.css:83-89) ; `CLIQUABLE` exporté mais inutilisé (components/stock/commun.tsx:139).
9. **Ligne cliquable avec l'ancienne classe `clic`** (REGLES : `cliquable`) : VoletRealise.tsx:128, 151 — aucune règle CSS `tr.clic` → pas de curseur ni de filet au survol.
10. **Saisie perdue sans question** : RetourBureau « Fermer » appelle `onFermer` directement (RetourBureau.tsx:184) alors que la fenêtre est `sale` ; Production : le brouillon du plan n'est protégé que par `beforeunload` (Production.tsx:50-57), un clic dans le menu le perd sans rien demander ; « Tout annuler » (VoletPlan.tsx:157) vide toute la saisie sans confirmation.
11. **Boutons grisés sans raison en infobulle** (REGLES §2) : « Valider la sortie » du détail grisé par des blocages garde l'infobulle générique (Sorties.tsx:397-400) ; « Garder en brouillon » (SaisieSortie.tsx:240) et « Valider la sortie » de la saisie hors empêchement (:251-254 : dépassement, ligne sans contenance, aucune ligne) ; « Proposer les fils à sortir » (:131) ; « Enregistrer tout (N) » grisé pour un coefficient hors bornes (VoletPlan.tsx:160) ; « Étiquettes (0) » (Stock.tsx:280-286).
12. **Écran qui laisse cliquer pour découvrir un refus** : l'« Enregistrer » d'une ligne du plan n'est pas grisé pour un coefficient hors [0 ; 20] (VoletPlan.tsx:207) → refus serveur ; « Tout valider (N) » compte aussi les brouillons bloqués (AValider.tsx:58, 100-101 ; le serveur expose pourtant `validables` sans les bloqués, brouillons.py:91) → la confirmation annonce des validations qui seront refusées.
13. **À valider — note de rôle fausse et lien inaccessible** : « validé par les achats » pour toute opération que le compte ne peut pas valider (AValider.tsx:171), faux pour un retour des machines (réservé à l'alimentation, operations.py:30) ; « Ouvrir » d'une opération mène à `/operations` gardé achats (brouillons.py:79, App.tsx) → l'alimentation est renvoyée à l'accueil pour un transfert qu'elle peut pourtant valider.
14. **Message de succès invisible** : « Brouillon supprimé. » est posé puis la fenêtre se ferme aussitôt (Sorties.tsx:267-272, 389) ; le message de page des Sorties n'est jamais effacé (Sorties.tsx:70, 180).
15. **Prix sans unité** : colonne « Prix » des mouvements « 0,000 USD » sans « / kg » (Stock.tsx:546) ; quantités sans unité dans les en-têtes « Quantité » (Stock.tsx:503, 635 ; Tracabilite.tsx:397 ; AValider.tsx:141).
16. **Indicateur « Entré · sorti » mal formé** : « 1 234 · 567 kg » (un nombre sans unité, l'autre avec) (Stock.tsx:591).
17. **Fil d'Ariane du suivi** : « ← Revenir au matière REF » (Tracabilite.tsx:286, 96-98 : « au » devant « matière ») ; libellé local « Ajustement » ≠ serveur « Ajustement d'inventaire » (Tracabilite.tsx:86 vs modeles.py:492).
18. **« Où ce lot est-il allé ? » change d'onglet** : le lien force `?onglet=lots` (Stock.tsx:622, adresseSuivi par défaut 'lots') même ouvert depuis Mouvements ou Ordres.
19. **Filtres de Besoins matière non liés et sans « Effacer les filtres »** alors qu'il y en a quatre (VoletBesoins.tsx:106-138) ; pas d'« Exporter en Excel » sur les besoins, le plan glissant ni le réalisé (REGLES §2 Export) ; Lots et Ordres de fabrication sans export non plus.
20. **Recherche serveur des mouvements sensible aux accents** (ILIKE, stock.py:125-130) alors que la règle exige « sans accents » côté serveur aussi ; l'export utilise la recherche temporisée (Stock.tsx:425, 478) — cohérent mais décalé de 300 ms.
21. **Mois écrits de deux façons** : « oct. 26 » dans la fiche matière (StockParMatiere.tsx:531-537) contre « oct. 2026 » dans Production (direction/commun.tsx:34-39).
22. **Nom d'écran faux** : « créez-les dans l'écran Qualités & recettes » (VoletPlan.tsx:301) ; le menu dit « Qualités et recettes ».
23. **Lot ajouté à la main dans la saisie de sortie** : sa quantité disponible est celle d'aujourd'hui (`/soldes`), pas celle à la date de l'ordre comme la proposition (SaisieSortie.tsx:208-214 vs production.py:156-163) → le dépassement n'est vu qu'au refus serveur pour un ordre antidaté.
24. **Ligne de réception ambiguë** : « Reçu par REC-2026-0012 le … » (Stock.tsx:597) — « par » suivi d'un numéro de document, alors que « Par » désigne l'auteur partout ailleurs.
25. **Écart des Sorties** : l'indicateur « Écart à la recette » passe en `attention` dans les deux sens (Sorties.tsx:121) alors que l'étiquette d'écart met un manque en `critique` (Sorties.tsx:44).

### Comptes

- **Pages / écrans** : 3 (`/stock`, `/sorties`, `/production`).
- **Onglets** : 12 (Stock 5 : Par matière, Lots, Mouvements de stock, Ordres de fabrication, À valider ; Sorties 3 : Validées, Brouillons, Annulées ; Production 4 : Plan de production, Plan glissant, Plan et réalisé, Besoins matière).
- **Sous-vues (bascules)** : 17 (Par matière ×3 ; Suivi ×2 ; Détail d'ordre ×2 ; Saisie de sortie ×2 recette/hors recette ; Plan ×2 coefficients/m² ; Glissant ×2 ; Réalisé ×2 ; Besoins ×2 lectures).
- **Fenêtres** : 7 (Fiche matière, Fiche de lot avec bloc Libérer, Suivi de traçabilité, Détail d'un ordre, Saisie de sortie nouvelle/modifier, Retour des machines, Détail d'un besoin) ; **documents imprimables** : 1 (étiquettes QR de lots) ; **exports Excel** : 3 (pilotage, mouvements, sorties).
- **Gestes inventoriés** : 72 (navigation par onglets non comptée).
  - Stock 32 — Par matière 8 (bascule de vues, tri par en-tête, Effacer les filtres, Exporter en Excel, clic ligne, Voir les lots →, Où cette matière est-elle allée ?, Ses mouvements) ; Lots 5 (Étiquettes (N), cocher, Suivre, clic ligne, Effacer) ; fiche de lot 4 (Où ce lot est-il allé ?, Libérer, Page du lot, Imprimer l'étiquette) ; Mouvements 5 (Effacer, Exporter, Charger les 500 suivants, ouvrir le lot, lien document) ; Ordres + suivi 7 (Effacer, clic/Suivre, ← Revenir, Ouvrir l'ordre, Fiche du lot, liens de suivi, bascule) ; À valider 3 (Effacer, Tout valider (N), Ouvrir).
  - Sorties 27 — page 5 (Nouvelle sortie, Effacer, Exporter, Tout valider…, clic ligne) ; détail 8 (Supprimer, Modifier, Valider la sortie, Faire un retour, Annuler (contre-passation), Fermer, Traçabilité de l'ordre, bascule) ; saisie 11 (bascule recette/hors recette, + Une autre qualité, Retirer, Proposer/Recalculer les fils, + un autre lot…, retirer, changer d'unité, + Ajouter un fil, Fermer, Garder en brouillon, Valider la sortie) ; retour 3 (tout, Fermer, Remettre X kg en stock).
  - Production 13 — Plan 6 (bascule, Enregistrer, Annuler, Tout annuler, Enregistrer tout (N), case Inactives) ; Glissant 1 (bascule) ; Réalisé 3 (bascule, clic qualité → graphique, choix de qualité) ; Besoins 3 (bascule de lecture, clic référence → détail, Ouvrir le plan d'achat →).

---

## Partie 3 — L'atelier au téléphone, les métiers à tisser, les étiquettes QR

Périmètre : `ecran/src/pages/atelier/*` (Atelier, Envoyer, sortie.ts, Retour, Deplacer, Chercher,
LotFiche, Montage, Signaler, Bons, commun), `pages/Metiers.tsx`, `components/referentiels/MetiersTisser.tsx`
(+ `components/referentiels/types.ts` pour les calculs du montage), le document imprimable
`GET /api/lots/etiquettes` (`gestion_mp/api/stock.py:361`). Droits et messages serveur relus dans
`gestion_mp/api/production.py`, `operations.py`, `stock.py`, `referentiels.py`, `suivi.py`,
`services/stock.py`, `securite.py`.

Références : `fichier:ligne` relatives à `ecran/src` ; côté serveur, relatives au dépôt.

---

### 0. Le cadre commun de l'atelier (s'applique à tous les écrans du § 1)

#### 0.1 Entrée, garde, redirections
- Route React `/atelier/*` déclarée **hors** du gabarit bureau (pas de menu latéral) : `App.tsx:161-164`.
  Garde : `peutAvec(compte, ['alimentation'])` → alimentation **et direction** (la direction passe partout,
  `lib/session.tsx:39-41`) ; tout autre rôle (achats) est renvoyé sans message vers son accueil
  (`accueilDe` : `/accueil` pour achats, `App.tsx:96-101`).
- Lien de menu bureau « Écran atelier (téléphone) » (`App.tsx:54`, groupe « Tous les jours », rôles
  `['alimentation']` → visible aussi par la direction).
- Arrivée automatique : `surTelephone()` = `matchMedia('(max-width: 700px)')` (`App.tsx:104-106`).
  L'alimentation au téléphone a pour accueil `/atelier` ; au bureau `/accueil`. La racine `/` mène
  l'alimentation au bureau vers `/sorties` (`App.tsx:168-171`).
- **QR des étiquettes** : elles encodent `<adresse>/lot/<id>` (§ 4). Au téléphone (largeur ≤ 700 px) la
  route `/lot/:id` est remplacée par `VersAtelierLot` qui redirige vers `/atelier/lot/:id`
  (`App.tsx:165-167`, `App.tsx:275-279`) ; au bureau `/lot/:id` ouvre la page bureau du lot (`pages/Lot.tsx`).
  Sans session : l'écran de connexion s'affiche à la place, et après connexion l'adresse `/lot/ID` est
  rejouée (`App.tsx:146-157`).
- Routes internes (`pages/atelier/Atelier.tsx:22-34`) : `index` → accueil (`Tableau`) ; `envoyer` ;
  `bons` ; `bons/:id` ; `retour` ; `chercher` ; `lot/:id` ; `deplacer` ; `montage` ; `signaler` ;
  `*` → accueil.

#### 0.2 Gabarit de chaque écran (`Ecran`, `pages/atelier/commun.tsx:214-240`)
- En-tête collant (`.atelier-tete`, `ajouts.css:175-200`) : fond `--accent-fort`, texte blanc, padding
  12 × 16 px. À gauche, si `retour` est donné, un bouton « ‹ » (`aria-label="Retour"`) : `retour === true`
  → page précédente de l'historique, sinon l'adresse donnée. Titre `h1` 18 px. Zone `droite` (jamais
  utilisée par les écrans actuels).
- Corps (`.atelier-corps`) : colonne flex, écart 12 px, padding 14 px, largeur max 720 px centrée.
- **Barre du bas fixe** (`Atelier.tsx:35-48`, `ajouts.css:209-238`) présente sur tous les écrans de
  l'atelier, 4 cases égales (grille 4 colonnes) : « ⌂ Accueil » (`/atelier`, actif seulement à l'exact),
  « ⇢ Envoyer » (`/atelier/envoyer`), « ⇠ Retour » (`/atelier/retour`), « ⌕ Lots »
  (`/atelier/chercher`). Icône 22 px au-dessus d'un libellé 12 px gras ; case active en couleur d'accent ;
  marge basse `safe-area-inset-bottom`. Le corps de page réserve 84 px en bas.

#### 0.3 Tailles de cible (le téléphone se tient en gants)
| Élément | Taille | Source |
|---|---|---|
| Tout `.bouton` de l'atelier | hauteur min 46 px (`ajouts.css:315-319`), et min 44 × 44 px (`ajouts.css:506-513`), police 15 px, padding 0 16 px | |
| `.bouton.large` | pleine largeur | `ajouts.css:320-322` |
| Bouton « ‹ » de l'en-tête | min 44 × 44 px, padding 8 × 12 | `ajouts.css:191-200`, `:506-513` |
| Champ `.entree` / `select.entree` | hauteur 46 px, **police 16 px** (sous 16 px le téléphone zoome) | `ajouts.css:310-314` |
| `Compteur` (− champ +) | grille 52 px · 1fr · 52 px, boutons 46 px de haut, symbole 22 px gras ; champ centré | `ajouts.css:326-342` |
| `Segments` | boutons égaux, padding 10 × 6, min 44 × 44 px ; actif = fond d'accent, texte blanc | `ajouts.css:343-361`, `:506-513` |
| Lien-geste (« Retirer ce lot », « Tout ce qui est parti ») | min-height 44 px, padding 0 12 px | `ajouts.css:514-520` |
| Tuile de l'accueil | 2 colonnes, padding 18 × 14, coins 14 px, icône 30 px, titre 16 px, sous-titre 12,5 px ; tuile principale sur toute la largeur, fond d'accent | `ajouts.css:239-277` |
| Bouton d'étage (montage) | min-height 56 px, grille auto-fill min 96 px | `components/referentiels/referentiels.css:95-126` |
| Confirmation sur place pleine largeur (`.confirmer-large`) | le bouton puis la question « question · Non · Oui » occupent toute la largeur, question centrée sur sa propre ligne | `components/stock/stock.css:135-147` |
| Carte `.fiche` | fond surface, bord 1 px, coins 12 px, padding 14 ; `.fiche.alerte` = bord et fond rouges pâles ; `.fiche.ok` = vert pâle ; `.fiche.clic` = curseur main | `ajouts.css:278-309` |
| `.grand-nombre` | 26 px, gras 800, chiffres tabulaires | `ajouts.css:367-371` |

#### 0.4 Briques partagées (`commun.tsx`)
- `Compteur` (`commun.tsx:243-275`) : « − » = `max(min, ceil(v/pas)·pas − pas)` ; « + » =
  `floor(v/pas)·pas + pas` (arrondis à 3 décimales) — le geste ramène d'abord sur un multiple du pas.
  Champ `inputMode="decimal"`, virgule affichée, virgule ou point acceptés, espaces ignorés, champ vidé = 0,
  tout sélectionné au focus. Le « − » ne descend pas sous `min` (0) ; la frappe directe accepte un nombre
  négatif.
- `pasPour(valeur, unité)` (`commun.tsx:169-173`) : bobine ou palette → 1 ; kg → 0,1 sous 10 kg, 1 sous
  100 kg, 10 au-delà.
- Unités de saisie (`commun.tsx:103-156`) : `kg` toujours ; `Bobine` si poids de bobine connu ; `Palette`
  si en plus bobines/palette connu. Libellés : « en kg », « en bobines (X,XX kg) », « en palettes (N bob.) »
  (les écrans retirent « en »). Contenance : bobine = poids de bobine (du lot pesé, sinon catalogue) ;
  palette = poids × bobines/palette. `convertir` : bobine arrondie à l'entier, palette au centième, kg au
  dixième. `toutRendre` : arrondi **vers le bas** (bobine entière, centième de palette, gramme) pour ne
  jamais dépasser.
- `quantite(v, kgParMl, déc)` (`commun.tsx:160-165`) : « 12,5 kg » ; sous 10 kg au moins 2 décimales ;
  pour cuir/franges/ruban, « 14,30 kg ≈ 1 021 ml » (mètres indicatifs).
- `bobines(kg, poids)` : « ≈ N bobines » (vide sans poids).
- `Bandeau` : message rouge (`message erreur`) s'il y a un texte.
- `Blocages` (`commun.tsx:298-310`) : « **Sera refusé à la validation :** » puis liste à puces des raisons
  du serveur.
- `STATUTS_BON` (`commun.tsx:80-84`) : brouillon → « Brouillon » (attention) ; valide → « Validé » (ok) ;
  annule → « Annulé » (neutre).
- `aujourdhuiLocal()` : le jour **à l'heure du serveur** (`lib/heure.ts` recale l'horloge sur l'en-tête
  `X-Heure-Serveur` de chaque réponse).
- `magasinParDefaut` (`commun.tsx:93-97`) : le magasin actif, non « Quarantaine », le plus garni (`stock`).
- `useSuspension(magasinId)` (`commun.tsx:177-189`) : lit `GET /inventaires` (frais 30 s) ; si un
  inventaire `ouvert` porte sur ce magasin ou sur tous : « L'inventaire {n°} ({magasin}, du {jj/mm/aaaa})
  est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre. »
- `useDernierOrdre()` (`commun.tsx:192-196`) : la date la plus récente des ordres non brouillons (validés
  **et annulés**) de `GET /bons`.

#### 0.5 Réseau, erreurs, hors ligne
- Tous les appels passent par `lib/api.ts` : préfixe `/api`, cookie de session, en-tête `X-Gestion-MP: 1`
  sur les écritures (sinon le serveur répond 403 « Requête refusée : elle ne vient pas de l'écran de
  Gestion MP. », `gestion_mp/main.py:140-149`).
- Serveur injoignable (Wi-Fi coupé, pas de 4G) : l'appel échoue avec le message **« Le serveur ne répond
  pas : vérifiez le réseau (Wi-Fi ou 4G/5G). »** (`lib/api.ts:31-33`). Les gestes (`useEnvoi`, `enregistrer`
  de la sortie) affichent ce message en bandeau rouge ; **les lectures, elles, ne l'affichent presque
  jamais** (voir anomalies) : la liste paraît vide.
- 401 (session expirée, compte désactivé : « Connectez-vous pour continuer. » / « Ce compte n'est plus
  actif. ») → l'application revient à l'écran de connexion (`App.tsx:116-120`).
- Erreurs de saisie Pydantic traduites en français : « champ : message » joints par « ; »
  (`gestion_mp/main.py:174-185`).
- Relecture : `refetchOnWindowFocus`, fraîcheur 15 s, **une** nouvelle tentative en cas d'échec
  (`main.tsx:9-17`).
- **Hors ligne** : le service worker (`public/sw.js`) ne met **rien** en cache (ni données, ni enveloppe) :
  sans réseau, l'application ne s'ouvre pas. Il ne sert qu'à rendre l'application installable
  (`manifest.webmanifest` : nom « Gestion MP — matières premières », court « Gestion MP », `display:
  standalone`, couleur `#17497f`). Enregistré seulement en contexte sécurisé (https), `main.tsx:32-34`.
- Seule saisie qui survit à une coupure ou un rechargement : la **sortie en cours** (Envoyer), gardée en
  `sessionStorage` sous `gestion-mp:sortie-en-cours` (§ 2.2). Les saisies de Retour, Déplacer, Monter,
  Signaler sont perdues si l'on quitte l'écran.

#### 0.6 Aucun prix pour l'alimentation (vérifié côté serveur)
| Route lue par l'atelier | Ce qui est masqué pour l'alimentation | Source |
|---|---|---|
| `GET /lots/{id}` | chaque mouvement passe par `masquer_prix` : `prix`, `cours`, `cout_mad`, `valeur_mad` → null, `devise` → « » | `gestion_mp/api/stock.py:300-303`, `:36-42` |
| `GET /articles` | `prix`, `prix_kg` → null (restent `devise`, `unite_prix`) | `gestion_mp/api/referentiels.py:560-562` |
| `GET /qualites` | `cout_m2_mad` et, par ligne de recette, `prix_kg`, `prix`, `unite_prix`, `cout_m2_mad` → null | `referentiels.py:819-822` |
| `GET /metiers` | `valeur_mad` du métier et de chaque fil → null ; le coût moyen n'est même pas calculé | `referentiels.py:1220-1244` |
| `GET /inventaires` | `sans_prix` | `gestion_mp/api/inventaires.py:166-169` |
| `GET /operations/{id}` | `prix`, `devise` des lignes | `operations.py:201-206` |
| `GET /bons`, `/bons/{id}`, `/bons/proposition`, `/bons/{id}/lots-sortis`, `/soldes`, `/lots/scan`, `/magasins`, `/montage/references`, `/signalements`, `/operations/motifs` | aucun prix dans la réponse | |
Aucun écran de l'atelier n'affiche de prix ni de montant.

---

### 1. L'atelier au téléphone

#### 1.1 Accueil de l'atelier — `/atelier`
- **Fichiers** : `pages/atelier/Atelier.tsx:53-127` (`Tableau`).
- **Rôles** : alimentation, direction (garde § 0.1).
- **Données** : `GET /bons` (clé `bons`) ; `GET /signalements?tous=true` (clé `signalements,tous`,
  relu toutes les **60 s**).
- **En-tête** : titre « Atelier », pas de bouton retour.
- **Texte d'ouverture** : « Bonjour {nom}. Aujourd'hui, pour tout l'atelier : {N} ordre(s) validé(s),
  {X kg} envoyés aux machines. » — N = ordres `valide` datés du jour (heure du serveur) ; X = somme de leur
  `total` (brut, retours non déduits), 0 décimale (`Atelier.tsx:56-72`). Pendant le chargement : 0.
- **Tuiles** (grille 2 colonnes, `Atelier.tsx:73-114`) :

| Tuile (icône · titre) | Sous-titre | Mène à |
|---|---|---|
| ⇢ « Envoyer aux machines » (principale, pleine largeur, fond d'accent) | « Qualité et m² à fabriquer : les fils et les lots à prendre sont proposés. » | `/atelier/envoyer` |
| ⇠ « Retour des machines » | « Ce qui revient d'un ordre, lot par lot. » | `/atelier/retour` |
| ⌕ « Trouver un lot » | « Chercher ou scanner une étiquette. » | `/atelier/chercher` |
| ⇄ « Déplacer » | « D'un magasin à un autre. » | `/atelier/deplacer` |
| ≣ « Monter les fils » | « Ce qui est monté sur chaque métier, étage par étage. » | `/atelier/montage` |
| ! « Signaler un besoin » | « {n} en attente · » si j'ai des signalements non traités, puis « {r} réponse(s) des achats » s'il y en a de traités, sinon « Un fil qui manque, une palette qui finit. » (« mes » = `par === compte.nom`) | `/atelier/signaler` |
| ☰ « Ordres » | « {n} brouillon(s) à finir » s'il existe des brouillons (de tout l'atelier), sinon « Les sorties récentes » | `/atelier/bons` |

- **Note** : « Astuce : dans le navigateur du téléphone, « Ajouter à l'écran d'accueil » installe Gestion MP
  comme une application. L'appareil photo lit les étiquettes QR des palettes : il ouvre la fiche du lot. »
- **Gestes** :

| Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|---|
| Toucher une tuile (7) | grille | tous | — | — | — | navigation | — |
| « Se déconnecter » | en bas, 24 px sous l'astuce, loin des tuiles | tous | — | sur place : « Se déconnecter ({nom}) ? » · « Non » · « Oui, se déconnecter » | `POST /deconnexion` | retour à l'écran de connexion (cache vidé) | — |
| Barre du bas (4 cases) | pied fixe | tous | — | — | — | navigation | — |

#### 1.2 Envoyer aux machines — étape 1 « la demande » — `/atelier/envoyer` (`?bon=ID` rouvre un brouillon)
- **Fichiers** : `Envoyer.tsx:34-49` (aiguillage), `:94-134` (`SaisieTelephone`), `:136-258` (`Demande`),
  logique `sortie.ts` (§ 2).
- **Rôles** : alimentation, direction. Serveur : `POST /bons/proposition` → tout connecté (`acteur`) ;
  `POST/PUT /bons` → `ALIMENTATION` (§ 5).
- **Adresse** : lit `?bon=` (ID). Chaque visite de l'onglet « Envoyer » recrée l'écran (`key` = bon +
  `location.key`), mais la sortie en cours non finie est reprise (stockage de session).
- **Aiguillage** (`Envoyer.tsx:38-48`) : `?bon=` en chargement → « Un instant — chargement : l'ordre… » ;
  `?bon=` d'un ordre non brouillon → écran § 1.5 ; sinon la saisie (étape 1 si nouvel ordre, étape 2 si
  brouillon rouvert).
- **Données** : `GET /magasins`, `GET /metiers`, `GET /qualites` (listes communes `lib/donnees.ts`),
  `GET /inventaires` (suspension), `GET /bons` (dernier ordre validé), `GET /bons/{id}` si `?bon=`.
- **Titre** : « Envoyer aux machines » (nouvel ordre) ou « Modifier l'ordre (brouillon) » (brouillon
  rouvert, `s.id`). Bouton « ‹ » vers `/atelier` **seulement s'il n'y a encore aucun lot choisi** (sinon
  pas de retour, pour ne pas perdre la saisie).
- **Bandeaux en tête** (`useEmpechements`, `Envoyer.tsx:59-70`), un par raison :
  1. la suspension d'inventaire du magasin choisi (§ 0.4) ;
  2. si la date choisie est antérieure au dernier ordre validé/annulé : « Un ordre du {jj/mm/aaaa} est déjà
     validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du
     {jj/mm/aaaa} et écrire la vraie date dans le commentaire. »
- Note si une saisie a été reprise (nouvel ordre avec lots déjà choisis) : « La sortie commencée tout à
  l'heure est reprise telle quelle ; « Abandonner cette sortie », en bas de l'écran des lots, repart à vide. »
- **Formulaire** :

| Champ (libellé exact) | Type | Défaut | Contrôle / remarque |
|---|---|---|---|
| « Date de la sortie » | date | aujourd'hui (heure serveur) ; celle du brouillon | `max` = aujourd'hui. Changer la date marque « demande changée ». |
| « Magasin d'où sort la matière » | `Segments` des codes si ≤ 3 magasins courants, sinon liste déroulante | `magasinParDefaut` (le plus garni) ; celui du brouillon | Affiché **seulement s'il y a plus d'un** magasin courant (actif, non Quarantaine). Aide quand des lots sont choisis : « changer de magasin efface les lots choisis » — et les efface. |
| « Métier (facultatif) » | liste | « — » | Métiers actifs (+ celui du brouillon même arrêté), triés par nom puis code (tri numérique fr), affichés « CODE · Nom » (`nomMetier`). Ne marque pas « demande changée ». |
| Bascule `Segments` « Selon les recettes » / « Ordre hors recette » | 2 segments | « Selon les recettes » ; brouillon sans qualité → hors recette | |
| Hors recette : note « Échantillons, série spéciale : pas de qualité ; les fils et les lots se choisissent à la main à l'étape suivante. » | | | |
| Par qualité (carte) : « Qualité à fabriquer » (ou « Qualité n° i » s'il y en a plusieurs) | `ChoixRecherche` (recherche à la frappe, plusieurs mots, sans accents, 60 premiers résultats, « Rien ne correspond. ») | vide | Options : qualités actives non encore choisies sur l'ordre (une qualité une seule fois). Libellé « CODE — Nom ». Placeholder « Taper le code ou le nom… ». Entrée choisit si un seul résultat. |
| « Mètres carrés » | `Compteur` pas **50** | 0 | doit être > 0 |
| « Retirer cette qualité » | bouton rouge | — | seulement s'il y a ≥ 2 qualités |
| « + Une autre qualité sur le même ordre » | bouton | — | ajoute une carte vide |
| « Commentaire (facultatif) » | texte, max 300 | « » | placeholder « Équipe, consigne, incident… » |

- **Boutons du bas** :
  - « Revenir aux lots » (principal, pleine largeur) — seulement si des lots sont choisis et que la demande
    n'a pas changé depuis le dernier calcul : retourne à l'étape 2 sans rien recalculer.
  - Bouton de calcul (pleine largeur ; principal, ou neutre si « Revenir aux lots » est présent). Libellé :
    « Calcul… » pendant l'appel ; « Choisir les fils et les lots » (hors recette) ; « Recalculer les fils et
    les lots » (des lots existent déjà) ; sinon « Voir les fils et les lots à prendre ». **Grisé** si la
    demande est incomplète ou si un envoi est en cours. Au téléphone pas d'infobulle : la raison s'écrit
    **sous** le bouton (centrée), dans l'ordre du remplissage : « Choisir le magasin d'où sort la matière » ·
    « Choisir la date » · « Ajouter une qualité à fabriquer » · « Choisir la qualité à fabriquer » · « Saisir
    les mètres carrés à fabriquer » (`Envoyer.tsx:139-149`, `:249-250`).
  - Note si la demande a changé et qu'il existe des lots (selon recettes) : « Recalculer remplace les lots
    proposés ; les fils ajoutés à la main sont gardés. »
- **Demande complète** = magasin + date + (hors recette, ou ≥ 1 qualité et chacune avec qualité et m² > 0)
  (`sortie.ts:210-211`).
- **Erreur** : le message du serveur en bandeau rouge (`s.erreur`), p. ex. « La qualité {code} est arrêtée :
  elle ne se tisse plus. La direction la remet en service (Qualités) si une série doit encore partir. » ou
  « Qualité inconnue. » (`production.py:166-174`), ou « Le serveur ne répond pas… ».
- **Gestes** :

| Geste | Conditions | API | Effet / succès | Refus |
|---|---|---|---|---|
| « ‹ » | seulement sans lot choisi | — | `/atelier` | — |
| Bascule recette / hors recette | — | — | marque la demande changée | — |
| « Retirer cette qualité » | ≥ 2 qualités | — | retire la carte | — |
| « + Une autre qualité sur le même ordre » | — | — | carte vide | — |
| « Revenir aux lots » | lots et demande inchangée | — | étape 2 | — |
| « Voir les fils et les lots à prendre » / « Recalculer… » / « Choisir les fils et les lots » | demande complète, rien en cours | selon recettes : `POST /bons/proposition` `{magasin_id, date, fabrications:[{qualite_id, m2}]}` ; hors recette : aucun appel | étape 2 (§ 1.3), lots proposés | message serveur en bandeau rouge |

#### 1.3 Envoyer aux machines — étape 2 « Lots à prendre »
- **Fichiers** : `Envoyer.tsx:260-386` (`Lots`), `:388-471` (`FilCarte`), règles `sortie.ts`.
- **Titre** : « Lots à prendre », **sans** bouton retour (on revient par « Modifier la demande »).
- **Données** : `GET /soldes?magasin_id={magasin}` (lots du magasin, pour l'ajout hors recette et le
  disponible d'un brouillon rouvert) ; pour un brouillon rouvert avec qualités : `POST /bons/proposition`
  (à la date de l'ordre) une fois, pour retrouver le prévu sans toucher aux lots (`sortie.ts:225-242`).
- **Bandeaux** : mêmes empêchements qu'en § 1.2.
- **Carte récapitulative** : en gras le résumé « {CODE} {m²} m² · {CODE} {m²} m² » (ou « Ordre hors
  recette ») ; dessous en note « Le {date lisible} · {code magasin} · {CODE · Nom du métier}{ · commentaire} »
  — date lisible = « jj/mm/aaaa (aujourd'hui) », « jj/mm/aaaa (hier) » ou « jj/mm/aaaa »
  (`Envoyer.tsx:52-56`). Bouton « Modifier la demande » (retour à l'étape 1, rien n'est perdu).
- **Recettes incomplètes** (renvoyées par le serveur, une alerte rouge chacune) : « Recette incomplète —
  {CODE} : le rôle {rôle} pèse {x} au m², mais la recette ne nomme aucune matière pour lui : rien ne lui est
  proposé. La direction doit compléter la recette. » ou « Recette incomplète — {CODE} : le rôle {rôle} fait
  {x} % dans la recette au lieu de 100 % : sa proposition est faussée. La direction doit corriger la
  recette. » (`production.py:93-114`).
- **Note** (selon recettes) : « Les quantités proposées suivent la recette, perte matière comprise (le taux
  des réglages, comme dans Production & besoins), et prennent les lots du plus ancien au plus récent.
  Corrigez au réel avant de valider. »
- **Une carte par fil** (`FilCarte`), triés comme le serveur les rend (rôle puis référence), puis les fils
  ajoutés à la main :
  - Titre : la référence. Carte rouge (`alerte`) si `manque > 0,05 kg`.
  - Fil de la recette : à gauche en note « {rôle} · prévu {quantité} » (+ ligne « {CODE} : {qté} · {CODE} :
    {qté} » si le fil sert plusieurs qualités ; même texte en infobulle) ; à droite « pris {quantité} » et
    l'étiquette d'écart `EcartFil`.
  - Fil hors recette : note « hors recette · pris {quantité} ».
  - Manque : « Il manque {quantité} dans ce magasin (la quarantaine ne compte pas). »
  - **Une ligne par lot pris** (séparées par un filet) :
    - « **Lot {n°}** » et en note « dispo {quantité} ≈ N bobines » (dispo inconnu tant qu'un brouillon rouvert
      n'a pas relu les soldes : rien).
    - `Segments` d'unité « kg » / « bobines (X,XX kg) » / « palettes (N bob.) » si plus d'une unité possible.
      Changer d'unité garde la quantité, arrondie, et l'écrit : « arrondi : {qté après} au lieu de {qté
      avant} » quand l'écart dépasse 0,01 kg (`sortie.ts:296-311`).
    - `Compteur` (pas selon `pasPour`).
    - En note : « = {kg} » (unité bobine/palette) ou « ≈ N ml, à titre indicatif » (cuir/franges/ruban en kg).
    - Lien-geste « Retirer ce lot », aligné à droite, à l'écart du compteur.
    - Alertes : « Plus que ce que porte le lot. » (kg > dispo + 0,001) ; « Le poids de bobine n'est pas
      connu : saisir en kg. » (contenance nulle).
  - Liste « + Prendre aussi un autre lot… » (si d'autres lots du magasin portent ce fil) : options
    « {n° lot} — {quantité} » ; ajoute une prise à 0.
- **Ajouter un fil** (carte) : libellé « Ajouter un fil » (hors recette) ou « Ajouter un fil hors recette » ;
  `ChoixRecherche` sur les lots du magasin au disponible > 0 non déjà pris ; libellé « {référence} · lot
  {n°} », détail à droite « {disponible} » (0 déc.) ; placeholder « Référence ou numéro de lot… ». Ajout à 0.
- **Totaux** (carte) : « Prévu par la recette » {qté} (si prévu) ; « Total à sortir » {qté} en grand ;
  « Écart » + `EcartFil(total − prévu)` (si prévu).
- **Étiquette d'écart `EcartFil`** (`Envoyer.tsx:73-84`) : « — » sans prévu ; « conforme » (vert) si
  |écart| < 0,05 kg ou |écart/prévu| < 0,5 % ; sinon « ±X kg (±Y %) » — gris si |relatif| ≤ 5 %, orange
  (attention) si au-dessus et en plus, rouge (critique) si au-dessus et en moins.
- **Gestes** :

| Geste | Conditions / grisé (raison affichée sous le bouton) | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|
| « Modifier la demande » | — | — | — | étape 1 | — |
| Segment d'unité | — | — | — | conversion arrondie | — |
| − / + / saisie | — | — | — | — | — |
| « Retirer ce lot » | — | — | — | prise retirée | — |
| « + Prendre aussi un autre lot… » | autres lots du fil disponibles | — | — | prise à 0 | — |
| Ajouter un fil (choix) | — | — | — | prise à 0 | — |
| « Valider la sortie » (« Enregistrement… » pendant) | grisé si : rien à sortir, un dépassement, un lot sans contenance, un envoi en cours, ou un empêchement. Raison sous le bouton (si au moins une quantité) : « Validation impossible pour l'instant (voir le bandeau en tête) » · « {n} lot(s) : plus que ce qu'ils portent » · « Un poids de bobine manque : saisir ces lots en kg ». Infobulle : « Valider : le stock sort et l'ordre reçoit son numéro » | sur place, pleine largeur : « Sortir {total} le {date lisible · magasin · métier} ? Le stock est débité tout de suite. » · « Non » · « Oui, valider la sortie » | `POST /bons` (ou `PUT /bons/{id}`) puis `POST /bons/{id}/valider` | écran § 1.4 « Ordre {OF-…} validé » | message du serveur ; si la validation seule échoue : « {message} — l'ordre est gardé en brouillon, modifiable. » |
| « Garder en brouillon (sans sortir le stock) » (« Enregistrement… ») | grisé si rien à sortir, lot sans contenance, envoi en cours (pas de raison visible) ; infobulle « Enregistrer sans sortir le stock : l'ordre reste modifiable » | — | `POST /bons` ou `PUT /bons/{id}` | écran § 1.4 « Ordre gardé en brouillon » | message du serveur |
| « Abandonner cette sortie » (rouge) | seulement nouvel ordre avec saisie | « Abandonner cette sortie ? Rien n'est enregistré. » · « Non » · « Oui, abandonner » | — | efface la saisie gardée, **rechargement complet** vers `/atelier` | — |

- **Corps envoyé** (`sortie.ts:367-374`) : `{date, magasin_id, metier_id, commentaire (rogné), fabrications:
  [{qualite_id, m2}] (vide hors recette), lignes: [{article_id, lot_id, quantite, unite: 'kg'|'Bobine'|'Palette'}]}`
  — seules les prises de quantité > 0. Après tout envoi, relecture des clés `bons, bon, soldes, brouillons,
  stock, mouvements, lots, lot, ordres-fabrication`.
- **Refus serveur possibles** (création/modification, `production.py:256-283`) : « Magasin inconnu. » ;
  « La matière en quarantaine ne part pas aux machines : la libérer d'abord (transfert « Libération de
  quarantaine », décidé par les achats). » ; « Métier inconnu. » ; dates (`securite.py:223-240`) : « Date
  trop ancienne ({jj/mm/aaaa}) : vérifier l'année. », « Date dans le futur ({jj/mm/aaaa}) : un mouvement se
  saisit le jour où il a lieu. », « La période jusqu'au {jj/mm/aaaa} est close : rien ne s'y écrit plus.
  Dater après la clôture, ou demander à la direction de la rouvrir. » ; « Une qualité ne figure qu'une fois
  sur un ordre : additionner ses m². » ; qualité arrêtée / inconnue ; « Lot inconnu, ou d'une autre
  matière. » ; unité : « Unité : kg, bobine ou palette — le cuir, les franges et le ruban se comptent aussi en
  kilos. », « « {réf} » : le nombre de bobines par palette n'est pas connu, saisir en bobines ou en kg. »,
  « « {réf} » : le poids de bobine n'est pas connu, saisir en kg. » ; « lignes : … » (au moins une ligne,
  quantité > 0) ; modification d'un validé : « Un bon validé ne se modifie plus : l'annuler, puis en faire un
  autre. » (409).
- **Refus à la validation** (`production.py:496-530`) : « Ce bon est déjà validé. » (409) ; dates ; « Qualité
  arrêtée ({codes}) : elle ne se tisse plus. La retirer de l'ordre, ou demander à la direction de la remettre
  en service. » (409) ; « À la date de l'ordre, lot {n°} de {réf} : {état} dans « {mag} », {x} kg demandés ;
  … . Choisir un autre lot, ou dater l'ordre du jour où la matière était là. » (409 ; état = « entré le
  jj/mm/aaaa, après la date de l'ordre », « épuisé[ au jj/mm/aaaa] » ou « {x} kg seulement[ au …] ») ; « Un
  ordre daté du {jj/mm/aaaa} existe déjà : les numéros suivent les dates, un bon ne se valide pas à une date
  antérieure. » (409) ; à l'écriture : « L'inventaire {n°} est en cours sur « {mag} » : les mouvements y sont
  suspendus jusqu'à sa validation. » (409) ; « Le lot « {n°} » de « {réf} » ne porte que {x} kg dans
  « {mag} », {y} kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est
  bien là. » (409) ; « Au {date}, il n'y avait que {x} kg du lot … » (`services/stock.py:77-119`).

#### 1.4 Sortie enregistrée (fin de l'envoi)
- **Fichier** : `Envoyer.tsx:99-130`. Titre « Sortie enregistrée », retour vers `/atelier`.
- Carte verte : titre « Ordre {OF-AAAA-NNNN} validé » ou « Ordre gardé en brouillon » ; lignes « Matière
  sortie » / « Matière à sortir » {total en grand} ; « Magasin » {code} ; « Métier » {nom} (s'il y en a un,
  tel que le serveur le nomme : nom, sinon code).
- **Gestes** : « Nouvel ordre » (principal, pleine largeur → `/atelier/envoyer`) ; « Voir l'ordre » (→
  `/atelier/bons/{id}`) ; « Revenir à l'accueil » (→ `/atelier`).

#### 1.5 Ordre déjà validé (ouverture de `?bon=` d'un ordre non brouillon)
- **Fichier** : `Envoyer.tsx:40-45`. Titre « Ordre validé », retour `/atelier/bons`. Message bleu : « Cet
  ordre est déjà validé : il ne se modifie plus (l'annuler, puis en refaire un). » (affiché aussi pour un
  ordre **annulé**). Geste : « ‹ ».

#### 1.6 Ordres — `/atelier/bons`
- **Fichier** : `Bons.tsx:11-43`. Titre « Ordres », retour `/atelier`.
- **Données** : `GET /bons` (tous les ordres, plus récent d'abord). Chargement : « Un instant — chargement :
  les ordres… ».
- **Liste** : brouillons en tête (tri stable, sinon l'ordre du serveur : date décroissante), **60 premiers**
  sans le dire. Chaque carte cliquable (→ `/atelier/bons/{id}`), rouge si le brouillon a des blocages :
  - « **{n° OF}** » ou « **Ordre du {jj/mm/aaaa}** » (brouillon) + étiquette de statut ;
  - note « {date} · {CODE m² m², …} ou « hors recette » · {métier} » ; à droite quantité (net si validé,
    total sinon ; 1 déc. sous 100 kg, sinon 0) et en note « sorti net » / « à sortir » / « annulé » ;
  - « ⚠ sera refusé : {première raison} » ; « Retours : {n°, n°} ».
- Vide : « Aucune sortie pour l'instant. ».
- **Geste** : toucher une carte.

#### 1.7 Détail d'un ordre — `/atelier/bons/:id`
- **Fichier** : `Bons.tsx:45-201`. Titre « {n° OF} » ou « Ordre du {jj/mm/aaaa} » ; retour `/atelier/bons`.
- **Données** : `GET /bons/{id}`. Chargement « l'ordre » ; introuvable : « Ordre introuvable. » (sans en-tête).
- **Carte d'identité** : « Statut » (étiquette) ; « Date » ; « Magasin » ; « Métier » (si) ; une ligne par
  qualité « {CODE} — {Nom} » / « {m²} m² » ou « Fabrication » / « hors recette » ; « Commentaire » (si) ;
  « Par » : {créé par} « le {jj/mm/aa hh:mm} » puis « validé par {nom} le … ».
- **Carte matière** : titre « Matière à sortir » (brouillon) ou « Matière sortie » ; une ligne par lot
  « {référence} / lot {n°} » → {quantité} ; « **Total** » en grand ; « dont revenu des machines » « − {kg} »
  si des retours.
- Note « Retours faits sur cet ordre : {n°, …} » (n° d'opération RET-… ou « retour repris de l'ERP Fil du
  jj/mm/aaaa »).
- `Blocages` (§ 0.4), puis les messages de geste.
- **Gestes** :

| Geste | Quand | Conditions | Confirmation (texte exact) | API | Succès | Refus |
|---|---|---|---|---|---|---|
| « Valider la sortie » (principal, pleine largeur) | brouillon | grisé si blocages ou envoi en cours ; infobulle « Valider : le stock sort et l'ordre reçoit son numéro » | « Sortir {total} du stock ? » · « Non » · « Oui, valider » | `POST /bons/{id}/valider` | « Sortie validée. » | messages § 1.3 |
| « Modifier le brouillon » | brouillon | — | — | — | → `/atelier/envoyer?bon={id}` | — |
| « Supprimer le brouillon » (rouge) | brouillon | infobulle « Supprimer le brouillon : rien n'a bougé au stock » | « Supprimer ce brouillon ? Rien n'est sorti du stock. » · « Non » · « Oui, supprimer » | `DELETE /bons/{id}` | retour à `/atelier/bons` | « Un bon validé ne se supprime pas : l'annuler. » (409), « Bon introuvable. » (404), droits |
| « Faire un retour sur cet ordre » (principal) | validé | — | — | — | → `/atelier/retour?bon={id}` | — |
| « Annuler l'ordre (erreur de saisie) » (rouge) | validé | infobulle « Annuler (contre-passation) : à ne faire que pour une erreur de saisie » | avec retours : « Annuler tout l'ordre et ses retours ({n°…}) ? La matière sortie revient en stock, une seule fois, à la date de l'ordre. » ; sans : « Annuler tout l'ordre ? Toute sa matière revient en stock, à la date de l'ordre. » · « Non » · « Oui, annuler (contre-passation) » | `POST /bons/{id}/annuler` | « Ordre annulé : la matière est revenue en stock. » | « Seul un bon validé s'annule ; un brouillon se supprime. » (409), « Ce document a déjà été annulé. » (409), période close, inventaire en cours |
| Ordre annulé | — | aucun geste | | | | |

- Annuler un ordre contre-passe aussi ses retours (documents RET validés passés « annulee ») et les retours
  repris de l'ERP Fil, datés comme les originaux (`production.py:557-580`).

#### 1.8 Retour des machines — choix de l'ordre — `/atelier/retour`
- **Fichier** : `Retour.tsx:61-115`. Titre « Retour des machines », retour `/atelier`.
- **Données** : `GET /bons`. Chargement « les ordres ».
- Note « De quel ordre revient la matière ? ».
- **Recherche** (champ `type=search`, à la frappe, `filtrer` : plusieurs mots, sans accents) — affichée
  seulement s'il y a plus de 10 ordres validés ; placeholder « N° d'ordre, qualité, métier… » ; porte sur
  n° d'ordre, date lisible, métier, codes qualité.
- **Liste** : ordres `valide` seulement ; sans recherche les **10** derniers, avec recherche les 30 premiers.
  Carte-bouton : « **{n° OF}** » ; à droite « {sorti net} » + note « sorti net » ; note « {date} · {CODE m² m²,
  …} ou « hors recette » · {métier} ». Toucher → `?bon={id}` (même écran, § 1.9).
- Pied : « {n} autre(s) : préciser la recherche » ou « les 10 derniers sur {total} : chercher un ordre plus
  ancien ».
- Vides : « Aucun ordre ne correspond. » / « Aucun ordre validé. ».

#### 1.9 Retour sur un ordre — `/atelier/retour?bon=ID`
- **Fichier** : `Retour.tsx:117-287`. Titre « Retour — {n° OF} » (« Retour — ordre » avant chargement) ;
  retour `/atelier/retour`.
- **Rôles** : écran alimentation/direction ; serveur : type `retour_machine` réservé à l'alimentation
  (direction passe) : « « Retour des machines » est réservé à : responsable alimentation machines. » (403,
  `operations.py:64-69`).
- **Données** : `GET /bons/{id}` ; `GET /bons/{id}/lots-sortis` (par lot : sorti net des retours, > 1 g) ;
  `GET /operations/motifs` (frais 10 min) ; `GET /magasins` ; `GET /inventaires`. Chargement « ce qui est
  parti ».
- Vide : « Tout ce qui est parti sur cet ordre est déjà revenu. » (aucun champ en dessous).
- **Une carte par lot parti** (rouge si dépassement) : titre référence ; « lot {n°} » ; « parti (net) :
  {quantité} » ; `Segments` d'unité (conversion de ce qui est saisi) ; `Compteur` ; « = {kg} » si bobines /
  palettes ; lien-geste « Tout ce qui est parti » (remplit `toutRendre` du net, dans l'unité choisie) ;
  alerte « On ne rend pas plus que ce qui est parti. ».
- **Formulaire** :

| Champ | Type | Défaut | Contrôle |
|---|---|---|---|
| « Ranger dans le magasin » | liste des codes des magasins courants | le magasin de l'ordre | affiché seulement s'il y a plus d'un magasin courant |
| « Pourquoi revient-elle ? » | liste | le premier motif | motifs serveur `retour_machine` avec leur code ERP Fil : « R1 · Reliquat de fin d'ordre », « R2 · Changement de série / arrêt machine », « R4 · Erreur de prélèvement » (`operations.py:37-55`) |
| « Date du retour » | date | aujourd'hui | `min` = date de l'ordre, `max` = aujourd'hui |
| « Commentaire (facultatif) » | texte, max 300 | « » | placeholder « Bobines entamées, arrêt du métier… » |

- Puis messages, `Bandeau` de suspension d'inventaire (magasin de rangement).
- **Gestes** :

| Geste | Conditions | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|
| Unité / − / + / saisie | — | — | — | — | — |
| « Tout ce qui est parti » | — | — | — | quantité = tout le net | — |
| « Remettre {X kg} en stock » (principal, pleine largeur ; « Enregistrement… ») | grisé si aucune quantité, un dépassement, pas de magasin, pas de motif, pas de date, envoi en cours, ou inventaire en cours. Note sous le bouton : « {n} lot(s) dépassent ce qui est parti : {réf} (lot {n°}), …. » ou « Saisir ce qui revient, lot par lot. ». Infobulle « Le retour est validé tout de suite : le stock remonte » | « Remettre {X kg} en stock ({code magasin}) ? » · « Non » · « Oui, enregistrer le retour » | `POST /operations` `{type:'retour_machine', date, bon_id, motif, commentaire, lignes:[{article_id, lot_id, magasin_id, quantite, unite}]}` puis `POST /operations/{id}/valider` ; si la validation échoue, `DELETE /operations/{id}` (le brouillon ne reste pas) | message vert « Retour enregistré — {RET-AAAA-NNNN} : {X kg} remis en stock. » + bouton « Revenir à l'accueil » ; quantités et commentaire remis à zéro ; défilement en haut | messages serveur ci-dessous |
| « Effacer les quantités » | — | — | — | quantités à 0 | — |

- **Refus serveur** : « Choisir le motif : il dit pourquoi le stock bouge. » ; « Un retour des machines se
  rattache à l'ordre d'où la matière revient. » ; « Ce retour est daté du {date}, avant l'ordre {n°} du
  {date} : la matière n'était pas encore partie. Dater le retour du jour où elle est revenue. » ; « « {réf} » :
  choisir le lot. » ; « La quantité est positive. » ; « Le lot « {n°} » n'est sorti que de {x} kg pour cet
  ordre ({y} kg rendus) : on ne rend pas plus que ce qui est parti. » (409) ; « Le magasin « {code} » est
  désactivé : il ne reçoit plus rien. » ; inventaire en cours ; dates (§ 1.3).

#### 1.10 Trouver un lot — `/atelier/chercher` (+ caméra)
- **Fichier** : `Chercher.tsx`. Titre « Trouver un lot », retour `/atelier`.
- **Recherche** : champ (focus automatique) placeholder « Référence, couleur, numéro de lot… » ; envoi
  **250 ms après la dernière frappe** à `GET /soldes?q=…` (sans `q` : tous les lots en stock). Côté serveur
  (`stock.py:196-257`) : chaque mot doit se trouver dans référence, désignation, n° de lot, rôle, code magasin
  ou nom du fournisseur (`ILIKE`, insensible à la casse, **pas aux accents**) ; lots au solde > 1 g, triés
  référence puis date d'entrée.
- **Caméra** : si le navigateur a `BarcodeDetector` : bouton « 📷 Scanner une étiquette » / « Fermer la
  caméra » ; sinon note « Pour scanner : ouvrez l'appareil photo du téléphone devant l'étiquette QR, puis
  touchez le lien. ».
  - `Scanner` (`Chercher.tsx:79-126`) : `getUserMedia({video:{facingMode:'environment'}})` (caméra arrière),
    vidéo pleine largeur coins 12 px fond noir ; détection QR toutes les 250 ms. Lecture contenant `/lot/{n}`
    → `/atelier/lot/{n}` ; sinon `GET /lots/scan?code={texte lu}` (adresse ou n° de lot exact, sans casse) :
    un seul lot → sa fiche ; zéro ou plusieurs → **on continue de scanner sans rien dire**.
  - Échec caméra : « La caméra n'est pas accessible ici (elle demande une adresse sécurisée https). Utilisez
    l'appareil photo du téléphone. »
- **Liste** : **80 premiers** sans le dire. Carte-bouton par lot : « **{référence}** » ; « lot {n°} · entré le
  {jj/mm/aaaa} » / {quantité totale} (0 déc.) ; {codes magasins} / « ≈ N bobines » ; étiquette rouge « {qté}
  en quarantaine » si une part y est. Toucher → `/atelier/lot/{id}`.
- Chargement « les lots » ; vide « Aucun lot en stock ne correspond. ».

#### 1.11 Fiche du lot — `/atelier/lot/:id` (arrivée par QR `/lot/ID`)
- **Fichier** : `LotFiche.tsx`. Titre « Lot {n°} », retour = page précédente.
- **Données** : `GET /lots/{id}` (tout connecté ; prix masqués pour l'alimentation, § 0.6).
- Chargement « le lot ». Introuvable (réponse en erreur, **quelle qu'elle soit**) : titre « Lot introuvable »,
  retour `/atelier/chercher`, texte « Ce lot n'existe pas (étiquette d'une autre installation, ou lot
  supprimé). » et bouton « Chercher un lot » (→ `/atelier/chercher`).
- **Carte du lot** (rouge si reste ≤ 1 g) : titre référence + étiquette de statut (`STATUTS_LOT`,
  `LotFiche.tsx:53-58`) : « Disponible » (ok), « En partie en quarantaine » (attention), « En quarantaine »
  (critique), « Épuisé » (neutre) — calculé par le serveur sur les soldes ; note « {rôle} · {fournisseur} ·
  entré le {date} » ; « En stock » {quantité en grand} ; « Bobines » « ≈ N bobines de X kg » (si poids) ; une
  ligne par magasin {code} / {quantité} — magasin de quarantaine : son code suivi de l'étiquette rouge
  « quarantaine », ou le code lui-même en étiquette rouge s'il contient déjà « quarantaine » ; « Ordres servis
  : » liens « {n° OF} » → `/atelier/bons/{id}`.
- **Gestes** :

| Geste | Conditions | API | Effet |
|---|---|---|---|
| « Déplacer ce lot » (principal, pleine largeur) | disponible hors quarantaine > 0 | — | → `/atelier/deplacer?lot={id}` |
| « Imprimer l'étiquette » | toujours | `GET /api/lots/etiquettes?ids={id}` dans un nouvel onglet (`ouvrir`, `noopener`) | document § 4 |
| Lien n° d'ordre | — | — | → `/atelier/bons/{id}` |

- **« Ce qu'il a vécu »** (carte) : « Reçu le {date} ({n° réception}{, BL {n°}}) — pesé {quantité} » ; puis
  les **30 derniers** mouvements, du plus récent : « {date} · {libellé du type} » / note « {n° document} ·
  {magasin} · {auteur} » ; à droite « +{qté} » en vert ou « −{qté} » en rouge. Libellés types :
  « Stock d'ouverture », « Entrée de réception », « Sortie vers les machines », « Retour des machines »,
  « Retour au fournisseur », « Ajustement d'inventaire », « Transfert entre magasins »
  (`gestion_mp/modeles.py:486-494`).

#### 1.12 Déplacer — choix du lot — `/atelier/deplacer`
- **Fichier** : `Deplacer.tsx:111-128`. Titre « Déplacer », retour `/atelier`.
- **Données** : `GET /soldes` (tous les lots en stock).
- Champ « Quel lot ? » : `ChoixRecherche` des lots au disponible > 0 ; libellé « {référence} · lot {n°} »,
  détail « {disponible} » ; placeholder « Référence ou numéro de lot… » → `?lot={id}`.
- Note « Ou scannez l'étiquette de la palette, puis « Déplacer ce lot ». ».

#### 1.13 Déplacer un lot — `/atelier/deplacer?lot=ID`
- **Fichier** : `Deplacer.tsx:37-110`, `:130-245`. Titre « Déplacer », retour = page précédente.
- **Rôles** : serveur `transfert` : achats et alimentation (« « Transfert entre magasins » est réservé à :
  responsable achats, responsable alimentation machines. »). **La quarantaine ne se libère pas d'ici** ; on
  peut y mettre un lot.
- **Données** : `GET /lots/{id}`, `GET /magasins`, `GET /operations/motifs`, `GET /inventaires`.
- Carte : référence, « lot {n°} ».
- Si rien de disponible hors quarantaine : « Ce lot n'a pas de matière disponible à déplacer » + « : il est en
  quarantaine, et seuls les achats le libèrent. » (s'il a un solde en quarantaine) ou « . ».
- **Formulaire** :

| Champ | Type | Défaut | Règle |
|---|---|---|---|
| « Depuis » | liste « {code} — {quantité} » des magasins non Quarantaine où le lot a du stock, le plus garni d'abord | le plus garni ; quantité = tout ce qu'il y porte (au gramme, vers le bas) | changer recalcule la quantité (tout, dans l'unité choisie) |
| « Vers » | liste « Choisir… » + magasins **actifs** autres que la source ; un magasin de quarantaine porte « (quarantaine : matière douteuse) » | vide | |
| Unité (`Segments`) | kg / bobines / palettes | kg | conversion plafonnée au disponible |
| « Quantité (disponible : {qté}) » | `Compteur` | tout | alerte « Plus que ce qui est là. » ; note « = {kg} » en bobines/palettes |
| « Pourquoi ? » | liste des motifs `transfert` **sauf** « Libération de quarantaine » et « Mise en quarantaine » → « Rangement », « Approvisionnement de l'atelier » ; vers une quarantaine : champ grisé « Mise en quarantaine » | « Rangement » | |
| « Date » | date, max aujourd'hui | aujourd'hui | |
| « Commentaire (facultatif) » ou, vers une quarantaine, « Commentaire (ce qui est douteux) » | texte max 300 | « » | vers quarantaine : 3 caractères au moins |

- Bandeau : suspension d'inventaire du magasin de départ **ou** d'arrivée.
- **Gestes** :

| Geste | Conditions (raison écrite sous le bouton) | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|
| « Tout le lot » | — | — | — | unité kg, quantité = tout le magasin de départ | — |
| « Déplacer {X kg} » (principal, pleine largeur) | grisé ; raison : « Un inventaire est en cours (voir le bandeau) » · « Choisir le magasin d'arrivée » · « Saisir la quantité » · « Plus que ce qui est là » · « Écrire ce qui est douteux, dans le commentaire » ; aussi sans date ou envoi en cours. Infobulle « Le transfert est validé tout de suite » | « Déplacer {X kg} de {code départ} vers {code arrivée} ? » · « Non » · « Oui, déplacer » | `POST /operations` `{type:'transfert', date, motif, commentaire, lignes:[{article_id, lot_id, magasin_id, magasin_destination_id, quantite, unite}]}` puis `/valider` ; échec → `DELETE` du brouillon | « Fait — {TRF-AAAA-NNNN} : {X kg} déplacés. » + bouton « Voir le lot » (→ `/atelier/lot/{id}`) | « Un transfert va d'un magasin à un autre. » ; « Magasin de destination inconnu. » ; « Libérer une quarantaine est une décision des achats, après contrôle de la matière. » (403) ; « Une entrée en quarantaine se fait avec le motif « Mise en quarantaine ». » ; « « {réf} » : choisir le lot. » ; « La quantité est positive. » ; « Le lot « {n°} » … ne porte que … » (409) ; magasin désactivé ; inventaire ; dates |

#### 1.14 Monter un fil — choix du métier — `/atelier/montage`
- **Fichier** : `Montage.tsx:28-65`. Titre « Monter un fil », retour `/atelier`.
- **Données** : `GET /metiers` (clé `metiers`, frais 30 s). Chargement « les métiers » ; erreur : message
  rouge **seul, sans en-tête**.
- Note « Sur quel métier ? ». Une carte-bouton par métier **en service** (rouge si étage trop large ou
  densité non saisie) : « **{CODE · Nom}** » / « {kg montés} » (0 déc.) ; note « {n} étage(s) garni(s) sur {N}
  · {f} fil(s) » + « · densité à saisir (direction) ». Toucher → `?metier={id}`.
- Vide : « Aucun métier en service. ».

#### 1.15 Monter un fil — choix de l'étage — `/atelier/montage?metier=ID`
- **Fichier** : `Montage.tsx:67-91`. Titre « {CODE · Nom} », retour `/atelier/montage`.
- Note « Laize {L} m par étage · {kg} montés · {n} bobines. Quel étage ? ».
- Grille de boutons d'étage (≥ 56 px) : « **Étage {n}** », « {m occupés} / {laize} m » ou « vide », « {f}
  fil(s) · {kg} » ; vert pâle si garni, rouge pâle si trop large. Toucher → `?metier={id}&etage={n}`.
- Commentaire du métier en note.
- Un étage hors bornes dans l'adresse ramène à cette grille.

#### 1.16 Monter un étage — `/atelier/montage?metier=ID&etage=N`
- **Fichier** : `Montage.tsx:96-374` (`MonterEtage`).
- **Rôles** : `monteur = peut('alimentation')` (alimentation, direction). Sinon « Lecture seule :
  l'alimentation monte les fils. » et champs figés (inatteignable : l'atelier n'est ouvert qu'à ces deux
  rôles). Serveur `PUT /metiers/{id}/etages/{n}` → `ALIMENTATION` (direction passe) : « Cette action est
  réservée à : responsable alimentation machines. » (403).
- **Données** : `GET /metiers`, `GET /articles` (catalogue, prix masqués), `GET /montage/references` (poids
  de bobine retenu, sorti ces 30 jours, déjà monté).
- Titre « {CODE} · étage {n} », retour `/atelier/montage?metier={id}`.
- **Carte de largeur** : « Largeur montée » « {m} / {laize} m » ; barre de remplissage (10 px, rouge si trop
  large, plafonnée à 100 %) ; « {n} bobines » / « {kg} » ; alertes « Plus large que la laize : {x} m de
  trop. » et « La densité de ce métier n'est pas saisie : le poids reste à zéro (direction). ».
- **Note d'aide** : « **Mètres montés** : la largeur de l'étage que ce fil garnit. **Part du fil** : quand
  deux fils se partagent les mêmes mètres (retors, mélange), la part de celui-ci ; 100 % sinon. Bobines =
  mètres × {densité} par mètre ; poids = bobines × kg par bobine pesé au lot × remplissage des bobines. »
- **Formules** : largeur occupée = Σ mètres ; bobines d'un fil = mètres × densité ; poids = bobines × kg/bobine × remplissage des bobines / 100 ;
  poids = bobines × kg/bobine retenu (pesé au lot — dernier sorti, sinon dernier reçu —, à défaut catalogue).
- Vide : « L'étage {n} est vide : monter un fil ci-dessous. »
- **Une carte par fil** (rouge si mètres ≤ 0) : titre référence ; note « {désignation} · {X,XXX} kg / bobine ·
  {source : « lot … (sorti) », « lot … (reçu) », « catalogue »} » ou « poids de bobine inconnu : ce fil ne pèse
  rien » ; « Mètres montés » (`Compteur` pas 0,1) ; « Part du fil (%) » (`Compteur` pas 5, plafonné à 100) ;
  « Commentaire » (texte max 300) ; « {n} bobines » / « {kg} » ; bouton rouge « Retirer ce fil ».
- **Ajout** : « Monter un fil à l'étage {n} » — `ChoixRecherche` des matières actives, hors rôles au mètre
  (Cuir, Franges, Ruban), pas déjà à l'étage ; libellé « {réf} — {désignation} » ; détail « {X,XX} kg /
  bobine » (poids retenu par le montage) ; placeholder « Taper : rouge 2900, beige… ». Le fil ajouté prend
  les mètres restants de la laize (≥ 0) et 100 %.
- **Garde** : fermer l'onglet ou recharger avec une saisie en cours déclenche l'alerte du navigateur
  (`beforeunload`) ; naviguer dans l'application (barre du bas, « ‹ ») **perd** la saisie sans rien demander.
- **Gestes** :

| Geste | Conditions | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|
| − / + / saisie (mètres, part), commentaire | monteur | — | — | — | — |
| « Retirer ce fil » | monteur | — | — | — | — |
| Choisir un fil à monter | monteur, catalogue chargé | — | — | carte ajoutée | — |
| « Enregistrer l'étage {n}… » (principal) ; libellé « Saisir les mètres de chaque fil » s'il manque des mètres | grisé si rien n'a changé, trop large, mètres manquants, envoi en cours | ouvre une **carte de confirmation sur place** (voir dessous) | — | — | — |
| « Oui, enregistrer » / « Oui, vider l'étage » (« Enregistrement… ») | carte ouverte | — | `PUT /metiers/{id}/etages/{n}` `{empreinte, fils:[{article_id, metres, pourcentage, commentaire}]}` | « Étage {n} enregistré : {f} fil(s), {kg} ; sur les métiers {±x,x} kg. » ; relecture des clés `metiers, stock, cockpit, plan-achat, besoins, controles, valorisation` | 409 (empreinte) → « L'étage a été modifié ailleurs entre-temps. » + bouton « Recharger l'étage » ; autres messages ci-dessous |
| « Non, revenir au montage » | carte ouverte | — | — | ferme la carte | — |
| « Annuler les modifications » | saisie modifiée | — | — | revient à l'état lu | — |
| « Recharger l'étage » | après conflit | — | relit `GET /metiers` | état frais, messages effacés | — |

- **Carte de confirmation** (rouge s'il y a des alertes) : « **Enregistrer l'étage {n} ?** » ou « **Vider
  l'étage {n} ?** » ; puis : métier en service et écart ≥ 0,05 kg : « Le poids « sur les métiers » {augmente |
  baisse} de {x kg} ({avant} → {après}). C'est une information : le fil est déjà sorti, le stock ne change
  pas. » ; écart nul : « Le poids « sur les métiers » ne change pas. » ; métier arrêté : « Métier arrêté :
  rien n'est compté sur lui. » ; alertes (`effetMontage`, `components/referentiels/types.ts:276-302`) pour
  chaque matière dont le monté (cet étage + ailleurs sur les métiers en service) dépasse **1,1 × sorti des
  30 derniers jours + 1 kg** : « {réf} : {x} kg sur les métiers pour {y} kg partis aux machines en 30 jours :
  vérifier qu'il est bien parti aux machines (Envoyer) avant de le monter. »
- **Refus serveur** (`referentiels.py:1352-1447`) : « L'étage {n} a été modifié(e) entre-temps sur un autre
  poste : rechargez pour repartir de sa dernière version, puis refaites la modification. » (409) ; « Étage
  {n} : ce métier n'en a que {N}. » (404) ; « Matière inconnue. » ; « « {réf} » ({rôle}) se pose au mètre
  linéaire : elle ne se monte pas en bobines sur un métier. » ; « « {réf} » est monté deux fois à l'étage
  {n}. » ; « « {réf} » à l'étage {n} : saisir les mètres montés. » ; « Étage {n} : {x} m montés (mètres de chaque fil
  de chaque fil) pour une laize de {L} m. » ; bornes Pydantic : mètres 0…1000, part 0…100, commentaire 300.
- Journal serveur : action « montage », détail « {CODE}, étage {n} : étage n {réf} {m} m ({p} %), … — sur
  les métiers {avant} → {après} kg ({±écart} kg) ».

#### 1.17 Signaler un besoin — `/atelier/signaler`
- **Fichier** : `Signaler.tsx`. Titre « Signaler un besoin », retour `/atelier`.
- **Rôles** : `POST /signalements` ouvert à tout connecté ; le traitement (`/signalements/{id}/traiter`) est
  réservé aux achats (`gestion_mp/api/suivi.py:198-224`).
- **Données** : `GET /articles` ; `GET /signalements?tous=true` (300 plus récents de tout le monde, relu
  toutes les 60 s).
- **Formulaire** (carte) : « Matière (facultatif) » — `ChoixRecherche` des matières actives, libellé
  « {réf} — {désignation} » (ou la référence seule), placeholder « Référence, couleur… » ; « Quel besoin ? » —
  zone de texte 96 px, max 500, placeholder « Plus que deux palettes de beige, la série 8F commence lundi… » ;
  `Segments` « Normal » / « Urgent » (défaut Normal).
- **Geste** « Signaler aux achats » (principal, pleine largeur ; « Envoi… ») : grisé si moins de 2 caractères
  (sans raison affichée) ou envoi en cours ; `POST /signalements` `{article_id|null, texte, urgence:
  'normale'|'urgente'}` ; succès « Signalé : les achats le voient sur leur accueil. » (formulaire remis à
  zéro) ; refus Pydantic « texte : trop court… », « urgence : … ».
- **« Mes signalements »** (filtrés sur `par === nom du compte`, 40 plus récents ; au-delà « Les 40 plus récents
  sont affichés. ») : carte (rouge si urgent non traité) : « **{réf}** » ou « **Sans matière précise** » ;
  étiquette « traité » (vert) / « urgent, en attente » (rouge) / « en attente » (orange) ; le texte ; « Signalé
  le {jj/mm/aa hh:mm} » ; si traité « **Réponse de {nom}** le {date} : {réponse ou « — »} ».
- Chargement « les signalements » ; vide « Aucun signalement pour l'instant. ».

---

### 2. La logique de l'envoi (`pages/atelier/sortie.ts`, partagée avec le bureau `components/production/SaisieSortie.tsx`)

#### 2.1 Les trois temps
1. **Demande** : date, magasin, métier, commentaire, et ce qu'on tisse — une ou plusieurs qualités (chacune
   une seule fois, `qualitesPour`) et leurs m² — ou un ordre **hors recette**.
2. **Lots** : pour chaque fil de la recette, les lots proposés du plus ancien au plus récent ; on corrige au
   réel (kg, bobines, palettes), on retire une prise, on prend un autre lot, on ajoute un fil hors recette.
3. **Brouillon** (modifiable, sans toucher au stock) ou **validation** (le stock sort, l'ordre prend son
   numéro OF-AAAA-NNNN, toutes les lignes ensemble ou aucune).

#### 2.2 Saisie gardée (téléphone seulement, `garder = true`)
- Nouvel ordre seulement (pas un brouillon rouvert) : chaque changement réécrit en `sessionStorage`
  (`gestion-mp:sortie-en-cours`) la date, le magasin, le métier, le commentaire, hors recette, les
  fabrications, les besoins, les prises, l'étape et « demande changée ». Revenir sur « Envoyer » (barre du bas,
  rechargement) reprend la saisie telle quelle. Effacée à l'enregistrement (brouillon ou validation) et par
  « Abandonner cette sortie ». Survit au rechargement, pas à la fermeture de l'onglet.

#### 2.3 Ce que le serveur propose (`POST /bons/proposition`, `production.py:190-237`)
- Qualités vérifiées « tissables » (connues, actives). Besoin d'un fil = Σ (kg/m² de la recette × m²) ×
  **(1 + taux de perte des réglages)** ; un fil commun à plusieurs qualités apparaît une fois (somme), avec le
  détail `par_qualite`.
- Lots : `stock.disponibles` (lots du magasin hors quarantaine, solde > 1 g, ordre d'entrée puis id), **tels
  qu'ils étaient à la date de l'ordre** si elle est passée (`presents_au` : un lot entré après ne donne rien ;
  on ne prend que le plus bas solde depuis cette date). FIFO : chaque lot donne `min(porté, reste)` →
  `proposee` (arrondi au gramme). `manque` = reste non couvert. `disponibles` = tous les lots présents (pour
  « Prendre aussi un autre lot »). Poids de bobine : celui pesé du lot, sinon catalogue.
- `recettes_incompletes` : rôles sans matière ou dont les parts ≠ 100 % (§ 1.3).
- Réponse : `theorique`, `manque`, `taux_perte`, `recettes_incompletes`, `lignes` triées par rôle puis
  référence.

#### 2.4 Règles de l'écran
- **Recalculer** remplace les prises des fils de la recette ; garde les prises des fils **ajoutés à la main**
  (ni dans la nouvelle proposition, ni dans l'ancienne) (`sortie.ts:270-278`). Hors recette : pas d'appel,
  besoins vidés, étape 2.
- Changer de **magasin** efface toutes les prises. Changer date, hors recette, qualités, m² → « demande
  changée » (le bouton devient « Recalculer… »). Métier et commentaire ne la changent pas.
- **Brouillon rouvert** : chaque ligne revient au gramme ; en **bobines** si son poids tombe sur un nombre
  entier de bobines (à 0,002 près, ≥ 1), sinon en kg ; « dispo » relu dans les soldes du magasin
  (`sortie.ts:117-129`, `:219-223`) ; le prévu relu par une proposition à la date de l'ordre.
- Une même prise (lot) ne peut figurer deux fois (`ajouterLot` ignore un lot déjà pris).
- Calculs : kg d'une prise = quantité × contenance ; `sorti` d'un fil = Σ ; `écart` = sorti − prévu ;
  `aEnvoyer` = prises de quantité > 0 ; `depassements` = kg > dispo + 0,001 (dispo connu) ;
  `sansContenance` = prises en bobine/palette sans poids ; `totalPrevu`, `totalSorti`.
- Enregistrer : création (`POST /bons`) ou mise à jour (`PUT /bons/{id}`) du brouillon, puis, si demandé,
  validation (`POST /bons/{id}/valider`). Un refus à la validation laisse le brouillon enregistré et le dit.

#### 2.5 Blocages calculés par le serveur (`blocages_bon`, `production.py:290-354`) — affichés avant de cliquer
« aucune matière à sortir » ; refus de date ; « un ordre daté du {jj/mm/aaaa} est déjà validé : dater ce
bon au moins de ce jour » ; « « {code} » est un magasin de quarantaine » ; « l'inventaire {n°} est en cours
sur « {code} » » ; « qualité arrêtée : {codes} » ; par lot « lot {n°} de {réf} : {entré le …, après la date
de l'ordre | épuisé[ au …] | {x} kg seulement[ au …]} dans « {mag} », {y} kg demandés » ou le refus de
`couvert_a_sa_date`.

---

### 3. Les métiers à tisser au bureau — `/metiers` (`?metier=ID` | `?metier=nouveau`)

#### 3.1 Page « Métiers à tisser »
- **Fichiers** : `pages/Metiers.tsx`, `components/referentiels/MetiersTisser.tsx:85-191`, types et calculs
  `components/referentiels/types.ts:196-302`.
- **Rôles** : menu « Référentiels › Métiers à tisser » pour achats et alimentation (+ direction)
  (`App.tsx:78`) ; garde `garde(['achats','alimentation'])` (`App.tsx:265`). Lecture `GET /metiers` : tout
  connecté. Création, réglage, suppression : **direction** ; montage des fils : **alimentation** (+
  direction). Les achats lisent.
- **Adresse** : lit et écrit `?metier=` (ID → la fiche s'ouvre ; `nouveau` → la fenêtre de création) ; écrit
  en `replace`. Fermer une fenêtre efface le paramètre. Pas de `?onglet=`.
- **En-tête** (`Page`) : titre « Métiers à tisser » ; sous-titre : « Chaque métier porte plusieurs étages, et
  chaque étage se garnit sur toute sa laize. Bobines = mètres × densité ; poids = bobines × kg / bobine × remplissage des bobines
  du fil. Ce poids, « Sur les métiers », est du stock en machine : il compte dans le stock de l'usine et sa
  valeur, et dans ce qu'on a avant de commander — ces bobines tisseront les prochains tapis. » + selon le rôle :
  alimentation « Vous montez les fils ; la direction règle les métiers. » ; achats « Lecture seule :
  l'alimentation monte les fils, la direction règle les métiers. » ; direction « L'alimentation monte les fils
  ; vous réglez les métiers. ».
- **Données** : `GET /metiers` (frais 30 s) ; dans la fiche : `GET /articles`, `GET /montage/references`.
  Chargement « Un instant — chargement : les métiers… » ; erreur : message rouge.
- **Indicateurs** (`IndicateursMetiers`, `MetiersTisser.tsx:60-83`) — sur les métiers **en service** :

| Indicateur | Valeur | Détail / infobulle | Clic |
|---|---|---|---|
| « Métiers en service » | nombre de métiers actifs | « {n} arrêté(s) » | — |
| « Poids monté » | « {Σ poids} kg » | détail : « {valeur} au coût moyen · stock en machine » (si le serveur donne `valeur_mad` : achats, direction) sinon « sur les métiers en service · stock en machine » ; infobulle « Stock en machine : ce fil, pas encore tissé, compte dans le stock de l'usine et sa valeur, et dans ce qu'on a avant de commander. » | — |
| « Étages garnis » | Σ étages garnis | « sur {Σ étages} disponibles » | — |
| « Bobines » | Σ bobines | « montées sur les métiers en service » | — |

- **Carte « Les métiers à tisser »** ; à droite (direction seulement) bouton principal « Nouveau métier »
  (→ `?metier=nouveau`).
- **Filtres** : `BarreRecherche` placeholder « Métier, fil monté, couleur… » (à la frappe, plusieurs mots,
  sans accents ; sur code, nom, commentaire, et « référence désignation » de chaque fil monté) ; case
  « montrer les métiers arrêtés » (décochée : seuls les métiers en service) ; à droite « {n} métier(s) ».
  Pas de bouton « Effacer les filtres » (un seul filtre + recherche).
- **Tableau** (`Cadre taille="court"`, classe `serre`), ordre du serveur (nom puis code), pas de tri au clic,
  pas de pagination, pas de pied :

| Colonne | Contenu | Format |
|---|---|---|
| « Métier » | **CODE · Nom** ; note « {commentaire} · monté par {nom} le {jj/mm/aa hh:mm} » (dernier montage du journal) | texte |
| « Laize (m) » | laize | droite, 2 déc. |
| « Densité (bobines/m) » | densité, « — » si 0 | droite, 1 déc. |
| « Étages garnis » | « {garnis} / {étages} » | droite |
| « Fils montés » | nombre de lignes de fil | droite |
| « Bobines » | Σ bobines | droite, entier |
| « Poids monté (kg) » | Σ poids | droite, entier |
| « À voir » | étiquettes `AlertesMetier` : « densité à saisir » (attention) ; « étage{s} {n, …} trop large{s} » (critique) ; « {n} fil(s) sans poids de bobine » (critique) ; « {n} bobine(s) mesurée(s) ≠ catalogue » (attention, écart pesé/catalogue au-delà de la tolérance de réception) | |
| « État » | « en service » (ok) / « arrêté » (neutre) | |

  Ligne cliquable (`cliquable`) → `?metier={id}` ; ligne d'un métier arrêté éteinte (`ligne-eteinte`).
  Vide : « Aucun métier ne correspond. » ou, sans aucun métier, « Aucun métier. La direction les crée ici. »
- Pas de bouton « Exporter en Excel ».

#### 3.2 Fenêtre « Nouveau métier » (`?metier=nouveau`)
- **Fichier** : `MetiersTisser.tsx:250-277` ; champs `ChampsMetier` `:215-248`. `Dialogue` large, garde
  « Abandonner les modifications ? » (sale = code, nom ou commentaire saisis) : bandeau « Des modifications ne
  sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner ».
- **Champs** :

| Libellé | Type | Défaut | Aide (texte exact) |
|---|---|---|---|
| « Code » | texte | « » | « le repère court, utilisé dans les ordres et les contrôles » |
| « Nom » (duo) | texte, placeholder « Métier du fond, Van de Wiele n° 2… » | « » | « celui qu'on emploie à l'atelier » |
| « Laize d'un étage (m) » | nombre | 4,2 | « largeur utile : les mètres montés d'un étage n'en dépassent pas » |
| « Densité (bobines par mètre) » | nombre | 0 | « 320 = 320 bobines par mètre de laize monté » |
| « Nombre d'étages » | nombre entier (arrondi) | 6 | « de 1 à 40 ; six ou huit selon la machine » |
| case « métier en service (un métier arrêté ne compte pas dans le stock) » | case | cochée | |
| « Commentaire » (large) | zone 2 lignes | « » | |

- Note « Une fois créé, le métier s'ouvre : l'alimentation y monte ensuite ses fils, étage par étage. »
- **Gestes** : « Abandonner » (si saisie) / « Annuler » → ferme ; « Créer le métier » (principal ;
  « Création… ») grisé si envoi en cours, code vide, étages < 1 ou > 40 (sans infobulle) → `POST /metiers`
  `{code (rogné), nom, laize, densite, etages, actif, commentaire}` ; succès : relecture, la fiche du nouveau
  métier s'ouvre (`?metier={id}`) ; refus : « Le métier « {code} » existe déjà. » (409), « Cette action est
  réservée à : la direction. » (403), bornes Pydantic (code 1…32, nom ≤ 120, laize 0…100, densité 0…100 000,
  étages 1…40, commentaire ≤ 2 000).

#### 3.3 Fenêtre « Métier {CODE · Nom} » — onglet « Fils montés » (`?metier=ID`)
- **Fichier** : `MetiersTisser.tsx:320-723` (`FicheMetier`). `Dialogue` **très large**, titre « Métier {CODE
  · Nom} » + étiquette « arrêté » si arrêté ; garde « Abandonner les modifications ? » si (monteur et fils
  modifiés) ou (direction et réglage modifié).
- **Rôles** : `monteur = peut('alimentation')` (alimentation, direction) ; `direction`. Ni l'un ni l'autre
  (achats) : « Lecture seule : l'alimentation monte les fils, la direction règle le métier. » et tout est figé,
  pas de pied d'actions.
- **Onglets** (dans la fenêtre, non portés par l'adresse) : « Fils montés » (« Fils montés • » si modifié),
  compteur = nombre de fils ; « Réglages du métier » (« Réglages du métier • »).
- **Note** : « Laize {L} m par étage · densité {d} bobines par mètre (ou « à saisir (réglages) ») · bobines
  d'un fil = mètres × densité ; poids = bobines × kg / bobine pesé au lot (à défaut, le
  catalogue). « Part du fil » : quand deux fils se partagent les mêmes mètres (retors, mélange), la part de
  celui-ci ; 100 % sinon. Monté : **{kg} kg**, {n} bobines. » + « Métier arrêté : ce poids ne compte pas dans le
  stock. » si décoché.
- « Dernier montage : {nom}, le {jj/mm/aa hh:mm} — {détail du journal} » (détail aussi en infobulle).
- Erreur de catalogue : message rouge.
- **Tableau de saisie** (`Cadre taille="dialogue"`, `table.saisie`), groupé par étage (tous les étages du
  réglage en cours, puis ceux « hors machine ») :

| Colonne | Ligne d'étage (`ref-groupe`, rouge si trop large ou hors machine) | Ligne de fil |
|---|---|---|
| « Fil » | « Étage {n} · {f} fil(s) » ou « vide », + « — au-delà du dernier étage » / « — plus large que la laize » | référence ; note « {désignation} · {X,XXX} kg / bobine · {source} » + « (catalogue X,XXX kg) » si la source n'est pas le catalogue ; étiquette critique « aucun poids de bobine (ni pesé, ni au catalogue) : ce fil ne pèse rien dans le stock » ou attention « pesé ±X % au catalogue : le catalogue est à revoir » ; lien « ouvrir la matière » (→ `/catalogue?matiere={article_id}`, achats/direction, seulement dans ces deux cas) |
| « Mètres » (110 px) | « {occupé} / {laize} m » (rouge si trop) | `ChampNombre` (figé hors monteur) |
| « Part (%) » (100 px) | — | `ChampNombre` (figé hors monteur ; **pas de plafond** côté écran) |
| « Bobines » | Σ | mètres × densité, entier |
| « Poids (kg) » | Σ, 1 déc. | bobines × kg/bobine retenu, 1 déc. |
| « Étage » | — | liste « Étage {n} » (option grisée « (déjà monté) » si ce fil est déjà à cet étage) + « Étage {n} (hors machine) » ; infobulle « Déplacer ce fil à un autre étage » |
| « Commentaire » | — | texte max 300 |
| (sans titre, monteur) | — | bouton rouge « Retirer » (infobulle « Retirer ce fil du métier ») |

  Ligne de fil rouge (`ligne-alerte`) si mètres ≤ 0. **Pied** « Toute la machine » : Σ mètres (bruts) « m »,
  Σ bobines, **Σ poids kg** en gras.
- **Ajout** (monteur) : liste « Monter à l'étage {n} ({occupé} / {laize} m) » + `ChoixRecherche` des matières
  actives hors rôles au mètre, pas déjà à cet étage ; libellé « {réf} — {désignation} · {fournisseur} » ;
  détail « {X,XX} kg / bobine » (poids **catalogue**) ou « poids de bobine inconnu » ; placeholder « Taper
  quelques mots : référence, couleur, fournisseur… ». Le fil prend les mètres restants de la laize, 100 %.
- Alertes : « Des fils sont montés au-delà du dernier étage : les déplacer ou les retirer. » ; « Saisir les
  mètres montés de : {réf, réf}. ».

#### 3.4 Même fenêtre — onglet « Réglages du métier »
- Les champs de § 3.2, **figés hors direction**.
- Note : « Changer la densité change le stock compté sur le métier. Réduire les étages ou la laize demande
  d'abord de retirer ou déplacer les fils qui dépasseraient. » + « Nommé par {n} ordre(s) de fabrication. »

#### 3.5 Pied de la fiche (monteur ou direction) et gestes
- Texte : « Étage(s) trop large(s) : {n, …}. » (rouge) sinon « Modifications non enregistrées. » / « Aucune
  modification. ».

| Geste | Rôle | Conditions | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|---|
| Onglets « Fils montés » / « Réglages du métier » | tous | — | — | — | — | — |
| Saisie mètres / part / étage / commentaire, « Retirer », ajout d'un fil | monteur | — | — | — | — | — |
| Champs du réglage | direction | — | — | — | — | — |
| « Supprimer » (rouge) | direction | grisé si envoi, fils montés, ou ordres le nommant ; infobulle : « Des fils y sont montés : les retirer d'abord » · « Nommé par {n} ordre(s) : l'arrêter plutôt (réglages) » · « Supprimer un métier sans fil ni ordre » | « Supprimer le métier {CODE} ? » · « Non » · « Oui, supprimer » | `DELETE /metiers/{id}` | fenêtre fermée, relecture | « « {code} » porte encore {n} fil(s) : les retirer d'abord. » (409) ; « « {code} » est nommé par {n} ordre(s) de fabrication : il appartient à l'historique. L'arrêter plutôt que le supprimer. » (409) |
| « Annuler les modifications » / « Fermer » | monteur/direction | « Annuler… » si modifié, sinon « Fermer » | — | — | état lu / fenêtre fermée | — |
| « Enregistrer » (principal ; « Enregistrement… ») | monteur/direction | grisé si envoi, rien de modifié, fils modifiés avec étage trop large / hors machine / sans mètres, code vide, étages hors 1…40 ; infobulle « Enregistrer, après avoir lu ce que le montage fait au stock » | sur place : « Le poids « sur les métiers » passe de {avant} à {après} kg ({±x} kg) — une information : ces kilos sont déjà sortis et consommés, ils ne changent ni le stock ni le plan d'achat. » (ou « Le poids « sur les métiers » ne change pas. ») + « **Attention : {alertes}.** » + « Enregistrer ? » · « Non » · « Oui, enregistrer » | fils : `PUT /metiers/{id}/fils?empreinte=…` (liste `[{article_id, etage, metres, pourcentage, commentaire}]`, ALIMENTATION) ; réglage : `PUT /metiers/{id}` `{code, nom, laize, densite, etages, actif, commentaire, empreinte}` (DIRECTION). Ordre : fils d'abord si on réduit étages ou laize, sinon réglage d'abord | « Enregistré : le stock sur les métiers est recalculé. » | conflit (409 contenant « entre-temps ») → bouton « Recharger le métier » + note « Il a été modifié sur un autre poste (ou au téléphone) : le recharger avant de refaire la modification. » ; messages : « Le montage de ce métier a été modifié(e) entre-temps sur un autre poste : rechargez… » / « Ce métier a été modifié(e) entre-temps… » ; « Le métier « {code} » existe déjà. » ; « Des fils sont montés à l'étage {n} : les retirer ou les déplacer avant de ramener le métier à {N} étage(s). » ; « Étage {n} : {x} m montés, plus que la laize de {L} m demandée. Retirer d'abord du fil. » ; refus de `_verifier_fils` (§ 1.16) |
| « Recharger le métier » | après conflit | — | — | (données courantes) | « Métier rechargé dans sa dernière version : refaire la modification. » | — |
| Fermer la fenêtre (×, Échap, fond) | tous | si modifié : « Abandonner les modifications ? » | | | | |

- **Notions** : laize (largeur utile d'un étage, m) ; densité (bobines par mètre de laize) ; étage ; part du
  fil ; largeur occupée = Σ mètres ; poids de bobine retenu (pesé au lot : dernier
  sorti, sinon dernier reçu ; à défaut catalogue — M43) ; tolérance de bobine (= tolérance de réception) ;
  métier en service / arrêté (un arrêté ne compte pas) ; « Sur les métiers » (stock en machine) ; empreinte
  (verrou optimiste) ; dernier montage (journal) ; « sorti récent » = 30 jours.

---

### 4. Le document imprimable « Étiquettes de lots » — `GET /api/lots/etiquettes?ids=1,2,3`

- **Fichier** : `gestion_mp/api/stock.py:361-415`.
- **Droits** : routeur protégé par `acteur` (tout connecté, les trois rôles) ; aucun prix dans le document.
- **Paramètre** : `ids` (≤ 4 000 caractères), liste séparée par des virgules ; un morceau non numérique ou un
  lot inconnu est **ignoré sans rien dire**. Aucun lot valide : réponse JSON 404 « Aucun lot à étiqueter. »
  (affichée brute dans l'onglet).
- **Adresse encodée dans le QR** : `{base}/lot/{id du lot}` (la route d'écran, pas `/api`) — `base` =
  réglage « Adresse du serveur pour les téléphones » (`adresse_publique`, `gestion_mp/parametres.py:143-146`,
  doit commencer par http:// ou https://, ≤ 200 car., sans espace) s'il est rempli ; sinon l'adresse par
  laquelle le poste a appelé, **« localhost » remplacé par l'IP du serveur sur le réseau de l'usine** et le
  même port (`stock.py:332-342`). QR `segno`, correction d'erreur **M**, SVG intégré.
- **Page HTML** (titre « Étiquettes de lots », `lang="fr"`) :
  - un bouton « Imprimer » (8 px de marge, `window.print()`), masqué à l'impression ;
  - une **page par étiquette** : `@page { size: 100mm 70mm; margin: 4mm }` ; bloc de 60 mm de haut, QR à
    gauche **34 × 34 mm**, texte à droite (10 pt, interligne 1,35), bordure pointillée grise à l'écran
    seulement ; saut de page après chaque étiquette.
- **Contenu d'une étiquette**, dans l'ordre :
  1. la **référence** de la matière (13 pt gras) ;
  2. « **Lot {n° du lot}** » (16 pt, gras 800) ;
  3. le nom du fournisseur (celui du lot, sinon celui de la matière) ;
  4. « Entré le {jj/mm/aaaa} » ;
  5. « {quantité} kg à l'impression » — somme de tous les soldes du lot (quarantaine comprise), 2 décimales
     à la française ; pour cuir/franges/ruban « {x} kg ≈ {y} ml » (`services/stock.py:27-32`) ;
  6. « N° {id du lot} » (9 pt gris) ;
  7. si une part est en quarantaine (> 1 g) : cadre noir épais « **QUARANTAINE — NE PAS SORTIR** » (11 pt).
- **Où on l'appelle** (`ouvrir()` → `window.open('/api/lots/etiquettes?ids=…', '_blank', 'noopener')`,
  `lib/api.ts:77-80`) :

| Écran | Bouton (libellé exact) | ids |
|---|---|---|
| Atelier, fiche du lot (`pages/atelier/LotFiche.tsx:133`) | « Imprimer l'étiquette » | le lot |
| Page bureau du lot (`pages/Lot.tsx:23`) | « Imprimer l'étiquette » (action d'en-tête) | le lot |
| Stock, fenêtre d'un lot (`pages/Stock.tsx:757`) | « Imprimer l'étiquette » | le lot |
| Stock, liste des lots (`pages/Stock.tsx:280-286`) | « Étiquettes ({n}) », infobulle « Imprimer les étiquettes QR des lots cochés », grisé sans case cochée | lots cochés |
| Réception validée — message de succès (`components/achats/DetailReception.tsx:316-323`) | lien « Imprimer les étiquettes QR à coller sur les palettes » | lots de la réception (`imprimerEtiquettes`, `DetailReception.tsx:54-57`) |
| Réception validée — pied de la fenêtre (`DetailReception.tsx:658-660`) | « Imprimer les étiquettes des lots » (grisé sans lot) | idem |
| Liste des réceptions (`pages/Receptions.tsx:221-228`) | « Étiquettes », infobulle « Les étiquettes QR des lots de cette réception », grisé sans lot | idem |

- **Lecture du QR** : appareil photo du téléphone → lien `/lot/{id}` → (téléphone ≤ 700 px) `/atelier/lot/{id}`
  (§ 1.11) ; ou scanner intégré (§ 1.10), qui reconnaît `/lot/{n}` dans le texte lu.
- Route voisine : `GET /api/acces/qr` (QR SVG de l'adresse de l'application, montré dans Réglages,
  `pages/Reglages.tsx:140`) et `GET /api/acces` (adresses réseau).

---

### 5. Droits serveur des routes appelées par l'atelier et les métiers

Refus de rôle générique (`securite.py:103-115`) : « Cette action est réservée à : {rôles en minuscules}. »
(403) — libellés des rôles : « responsable achats », « responsable alimentation machines », et « la direction »
pour une route réservée à la direction. Opérations : « « {type} » est réservé à : {rôles}. » (403).

| Route | Garde | Fichier |
|---|---|---|
| `GET /bons`, `GET /bons/{id}`, `GET /bons/{id}/lots-sortis`, `POST /bons/proposition` | `acteur` (tout connecté) | `production.py:190, 419, 583, 591` |
| `POST /bons`, `PUT /bons/{id}`, `DELETE /bons/{id}`, `POST /bons/{id}/valider`, `POST /bons/{id}/annuler` | `ALIMENTATION` (+ direction) | `production.py:436-580` |
| `GET /operations/motifs`, `GET /operations`, `GET /operations/{id}` | `acteur` | `operations.py:72, 209, 219` |
| `POST/PUT/DELETE /operations…`, `/valider`, `/annuler` | `STOCK` (achats, alimentation) puis `_autorise` par type : `retour_machine` alimentation ; `transfert` achats + alimentation ; libération de quarantaine achats/direction seulement | `operations.py:26-35, 345-457` |
| `GET /soldes`, `GET /lots/{id}`, `GET /lots/scan`, `GET /lots/etiquettes`, `GET /mouvements` | routeur `acteur` | `stock.py:27` |
| `GET /metiers`, `GET /montage/references`, `GET /magasins`, `GET /articles`, `GET /qualites` | `acteur` | `referentiels.py` |
| `POST /metiers`, `PUT /metiers/{id}`, `DELETE /metiers/{id}` | `DIRECTION` | `referentiels.py:1284-1336` |
| `PUT /metiers/{id}/fils`, `PUT /metiers/{id}/etages/{n}` | `ALIMENTATION` (+ direction) | `referentiels.py:1397-1447` |
| `GET /signalements`, `POST /signalements` | `acteur` | `suivi.py:190-211` |
| `POST /signalements/{id}/traiter` | `ACHATS` | `suivi.py:214` |
| `GET /inventaires` | `acteur` (prix masqués) | `inventaires.py:165` |

---

### Incohérences et anomalies repérées

1. **Le fil « sur les métiers » compte-t-il dans le stock ? L'écran se contredit.** Le sous-titre de page
   (`pages/Metiers.tsx:25-27`) et l'infobulle « Poids monté » (`MetiersTisser.tsx:68`) disent qu'il « compte
   dans le stock de l'usine et sa valeur, et dans ce qu'on a avant de commander » ; la note des réglages dit
   « Changer la densité change le stock compté sur le métier » (`MetiersTisser.tsx:648`) ; mais la
   confirmation d'enregistrement dit « ces kilos sont déjà sortis et consommés, ils ne changent ni le stock ni
   le plan d'achat » (`MetiersTisser.tsx:707`) et le téléphone « le fil est déjà sorti, le stock ne change
   pas » (`pages/atelier/Montage.tsx:340`). Le serveur (`referentiels.py:1201-1214`) dit qu'il compte dans le
   stock projeté et le plan d'achat.
2. **QR scanné au téléphone par un compte achats** : `/lot/:id` redirige vers `/atelier/lot/:id`
   (`App.tsx:167`) quel que soit le rôle ; la garde de `/atelier/*` (`App.tsx:161-164`) renvoie alors les
   achats sur `/accueil` sans dire pourquoi : le lot n'est jamais montré.
3. **Erreurs réseau affichées comme des listes vides ou des « introuvables »** : `LotFiche.tsx:68-76` (« Ce
   lot n'existe pas (étiquette d'une autre installation, ou lot supprimé). » même sur coupure réseau),
   `Bons.tsx:19` et `:52`, `Retour.tsx:89`, `Chercher.tsx:53`, `Atelier.tsx:56-72` (compteurs à 0). Pire :
   `Envoyer.tsx:38-48` — si `GET /bons/{id}` échoue, `?bon=ID` ouvre un **ordre vierge** (voire la sortie
   gardée) au lieu du brouillon. `Montage.tsx:35` montre l'erreur sans en-tête ni retour.
4. **Hors ligne** : `public/sw.js:6` ne met rien en cache, pas même l'enveloppe : l'application « installée »
   (astuce de `Atelier.tsx:115-118`) ne s'ouvre pas sans réseau. Les nouvelles tentatives de `main.tsx:15`
   testent `/40[134]/` sur le **texte** du message (le détail serveur en français), pas sur le statut.
5. **Vocabulaire « bon » dans les messages serveur montrés à l'atelier** (REGLES § 3 : « ordre ») :
   `production.py:303` « dater ce bon », `:452` « Bon introuvable. », `:461`, `:473`, `:501` « Ce bon est
   déjà validé. », `:519`, `:562`.
6. **Brouillon sans « Brouillon »** (REGLES § 2 Numéros) : `Bons.tsx:23` et `:59` affichent « Ordre du
   {date} ».
7. **Vocabulaire « en machine »** (REGLES § 3 l'interdit : employer « Sur les métiers ») : `Metiers.tsx:26`
   « stock en machine », `MetiersTisser.tsx:68`, `:71-72` ; l'indicateur s'appelle « Poids monté » et non
   « Sur les métiers ».
8. **« Fil » en en-tête de colonne** (REGLES § 3 : « Référence ») : `MetiersTisser.tsx:486`. **« Commentaire »**
   partout où REGLES demande « Observations » pour les remarques : `Envoyer.tsx:227`, `Retour.tsx:258`,
   `Deplacer.tsx:223`, `Montage.tsx:284`, `MetiersTisser.tsx:243`, `:496`, `Bons.tsx:96` (à arbitrer : REGLES
   interdit « Remarque », pas « Commentaire »).
9. **Boutons grisés sans raison visible au téléphone** (REGLES § 2) : « Garder en brouillon… »
   (`Envoyer.tsx:366-368`, raison seulement en infobulle, illisible au doigt) ; « Valider la sortie » sans
   quantité : la raison « Aucune quantité à sortir » n'est jamais affichée, car la note exige
   `s.aEnvoyer.length` (`Envoyer.tsx:277-278` et `:365`, code mort) ; « Signaler aux achats »
   (`Signaler.tsx:89`) ; « Enregistrer l'étage » sans modification (`Montage.tsx:359`) ; au bureau « Créer le
   métier » (`MetiersTisser.tsx:271`) et « Enregistrer » (`MetiersTisser.tsx:713-714`, l'infobulle ne
   change pas avec la raison).
10. **Ordre annulé présenté comme validé** : `Envoyer.tsx:40-44` titre « Ordre validé » / « Cet ordre est
    déjà validé » pour tout statut non brouillon, annulé compris.
11. **Poids de bobine annoncé dans la liste d'ajout** : le téléphone montre le poids que le montage
    comptera (`Montage.tsx:317-320`, et son commentaire le justifie), le bureau le poids **catalogue**
    (`MetiersTisser.tsx:635`) : deux chiffres différents pour le même fil.
12. **« Part (%) » sans plafond au bureau** (`MetiersTisser.tsx:563`) alors que le téléphone plafonne à 100
    (`Montage.tsx:278`) : le serveur refuse ensuite (« pourcentage : doit être au plus 100 »). Le `Compteur`
    accepte aussi un nombre négatif tapé (`commun.tsx:264-268`).
13. **Pied « Toute la machine »** : Σ mètres **bruts** (`MetiersTisser.tsx:350`, `:609`) alors que chaque
    étage compte la largeur pondérée par la part (`:343`) : deux fils à 60/40 % sur 4 m font 8 m au pied, 4 m
    à l'étage.
14. **Enregistrement non atomique au bureau** : fils puis réglage (ou l'inverse) en deux appels
    (`MetiersTisser.tsx:393-400`) ; si le second échoue, le premier reste écrit.
15. **`?metier=nouveau` ouvre la création pour tous les rôles** (`Metiers.tsx:18`, `MetiersTisser.tsx:187`) ;
    seul le bouton est réservé à la direction ; le serveur refuse ensuite.
16. **Code mort** : « Lecture seule : l'alimentation monte les fils. » (`Montage.tsx:233`) ne peut s'afficher
    (l'atelier n'est ouvert qu'à l'alimentation et à la direction, qui passent toutes deux `peut('alimentation')`) ;
    la zone `droite` d'`Ecran` (`commun.tsx:218`) n'est jamais utilisée.
17. **Saisies perdues en naviguant** (REGLES « Ne jamais perdre une saisie ») : Montage ne protège que la
    fermeture d'onglet (`Montage.tsx:147-153`) ; Retour, Déplacer, Signaler ne protègent rien — la barre du bas
    efface la saisie.
18. **Listes tronquées sans le dire** : 80 lots (`Chercher.tsx:34`), 60 ordres (`Bons.tsx:16`), 30 mouvements
    (`LotFiche.tsx:142`) ; la recherche de lots côté serveur (`ILIKE`, `stock.py:225-230`) n'ignore pas les
    accents, contrairement à la règle (REGLES § 2).
19. **Scanner muet** : un QR lu qui ne désigne aucun lot (ou plusieurs) ne produit aucun message
    (`Chercher.tsx:101-106`).
20. **Nom du métier différent selon l'endroit** : le choix affiche « CODE · Nom » (`nomMetier`,
    `Envoyer.tsx:183`), l'ordre enregistré affiche le nom seul, ou le code (`production.py:395`), dans
    `Bons.tsx:29`, `:76`, `Retour.tsx:100`, `Envoyer.tsx:115`. L'en-tête de montage d'un étage affiche le code
    seul (`Montage.tsx:231`). Titres : tuile « Monter les fils » (`Atelier.tsx:96`) / écran « Monter un fil »
    (`Montage.tsx:41`).
21. **« parti (net) »** (`Retour.tsx:209`) au lieu de « Sorti net » (REGLES § 3), alors que la liste des
    ordres du même écran écrit « sorti net » (`Retour.tsx:95`).
22. **Accueil atelier : « envoyés aux machines » = total brut** des ordres du jour (`Atelier.tsx:71`), retours
    non déduits.
23. **Fil hors recette : disponible du jour, pas de la date de l'ordre** (`Envoyer.tsx:315-321`,
    `sortie.ts:214-223`) alors que la proposition lit les lots à la date de l'ordre : pour un ordre antidaté,
    l'écran peut laisser passer ce que la validation refusera.
24. **Après un déplacement réussi**, la quantité saisie reste (`Deplacer.tsx:104-108`) et peut dépasser le
    nouveau disponible (« Plus que ce qui est là. ») ; « Tout le lot » ne prend que le magasin de départ, pas
    tout le lot (`Deplacer.tsx:201-208`). Au retour, changer d'unité peut arrondir au-dessus du net parti
    (`Retour.tsx:215`, `convertir` arrondit au plus près).
25. **« Mes signalements » filtrés sur le nom affiché** (`Signaler.tsx:42`, `Atelier.tsx:64`) et non sur
    l'identifiant : deux comptes de même nom se mélangent ; la lecture ne porte que sur les 300 derniers de tout
    le monde (`suivi.py:190-195`).
26. **« Abandonner cette sortie »** recharge toute l'application (`Envoyer.tsx:379`, `window.location.assign`).
27. **Prix : pas de montant pour l'alimentation, mais des résidus** : `GET /articles` lui laisse `devise` et
    `unite_prix` (`referentiels.py:560-562`), `GET /qualites` la `devise` des lignes de recette
    (`referentiels.py:819-822`) — aucun écran de l'atelier ne les affiche.
28. **Étiquettes** : ids invalides ignorés en silence ; erreur 404 en JSON brut dans l'onglet ouvert
    (`stock.py:397-398`) ; la quantité imprimée inclut la quarantaine (« à l'impression ») ; pas de nombre de
    bobines sur l'étiquette.
29. **Onglets de la fiche métier hors adresse** (`MetiersTisser.tsx:458-465`) : REGLES § 1 demande `?onglet=`
    pour les écrans à onglets (ici dans une fenêtre). Pas d'« Exporter en Excel » sur les métiers.

### Comptes
- **Écrans / pages** : 18 — atelier : accueil, demande, lots, sortie enregistrée, ordre déjà validé, liste
  des ordres, détail d'un ordre, retour (choix), retour sur un ordre, trouver un lot, fiche du lot (+ « lot
  introuvable »), déplacer (choix), déplacer un lot, montage (métier), montage (étage), montage d'un étage,
  signaler ; bureau : page Métiers à tisser.
- **Onglets / sous-vues** : 6 — fiche métier « Fils montés » / « Réglages du métier » (2) ; bascule
  « Selon les recettes » / « Ordre hors recette » (2) ; vue caméra (Scanner) ; carte de confirmation de
  montage.
- **Fenêtres / tiroirs** : 2 (« Nouveau métier », « Métier {CODE · Nom} ») + 1 document imprimable
  (« Étiquettes de lots », 7 points d'appel).
- **Gestes inventoriés** : ≈ 92 — accueil 12 (7 tuiles, déconnexion, 4 cases de barre) ; demande 6 ; lots 9 ;
  sortie enregistrée 3 ; ordre déjà validé 1 ; liste des ordres 1 ; détail 5 ; retour (choix) 2 ; retour sur
  ordre 6 ; trouver 3 ; fiche du lot 4 ; déplacer 6 ; montage 11 ; signaler 3 ; métiers bureau : page 4,
  nouveau métier 3, fiche 12 ; document étiquettes 1.

---

## Partie 4 — Achats : plan d'achat, préparation, commandes, réceptions, bon de commande fournisseur

Inventaire en lecture seule de `/Users/mohamed/gestion-mp`. Références `fichier:ligne` relatives à
`ecran/src` pour l'écran, au dépôt (`gestion_mp/...`) pour le serveur.

Rappels transverses utiles à la reconstruction :

- **Garde des routes** : `App.tsx:60-62` (menu, groupe « Achats ») et `App.tsx:253-255` (`garde(['achats'], …)`) :
  `/plan-achat`, `/commandes`, `/receptions` sont réservés à **achats** (et direction, qui passe partout).
  Un rôle refusé est renvoyé à son accueil (`App.tsx:194-195`, `Navigate … state={{ refuse }}`).
- **Droits serveur** (`gestion_mp/securite.py:104-123`) : `ACHATS = droit("achats")` (direction passe
  aussi), `DIRECTION = droit()` (direction seule). Refus 403 exact :
  « Cette action est réservée à : responsable achats. » (ou « … : la direction. » pour `DIRECTION`).
  Sans session : 401 « Connectez-vous pour continuer. » ; compte inactif : 401 « Ce compte n'est plus actif. »
- **Refus métier** : `erreur(message, code=422)` (`securite.py:28`) ; le message (champ `detail`) s'affiche tel
  quel dans le bandeau rouge de `useEnvoi` (`components/ui.tsx:418-448`).
- **`useEnvoi`** : pendant l'appel `occupe` (boutons grisés) ; succès → bandeau vert avec le texte passé
  (rien si texte vide) ; erreur → bandeau rouge avec le message du serveur.
- **`Confirmer`** (`ui.tsx:342-382`) : le bouton devient « question · Non · Oui… » sur place.
- **`Dialogue sale`** (`ui.tsx:270-338`) : Échap, clic sur le fond ou × demandent dans la fenêtre :
  « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » ·
  « Oui, abandonner ».
- **Chargement** générique : « Un instant — chargement : {quoi}… » (`ui.tsx:209-211`).
- **Formats** (`lib/format.ts`) : `nombre` (fr-FR, 0 décimale par défaut), `montant(v, devise)` = « 12 345 MAD »,
  `montantCourt` = « 17,4 M MAD » au-delà du million, `montants` = « 61 888 USD · 53 132 EUR » (jamais additionnés),
  `part` = pourcentage, `jours` = « 12 j », `date` = jj/mm/aaaa, `horodatage` = date + heure courtes,
  `metres(kg, kgParMl)` = « ≈ 1 020 ml ».
- **`signe(x, d)`** (`components/achats/commun.tsx:58-63`) : « +4,2 % », « −3 % », et « 0 % » quand l'écart
  s'arrondit à zéro (jamais « −0,0 % »).
- **`useOngletAdresse`** (`commun.tsx:11-21`) : lit/écrit `?onglet=` (remplace l'historique).
- **`useOuvrirDepuisAdresse`** (`commun.tsx:24-38`) : lit une seule des clés `?ouvrir=ID`, `?reception=ID`,
  `?commande=ID` (entier seulement), ouvre le document, puis efface la clé à la fermeture.
- **`BoutonExport`** (`commun.tsx:41-55`) : lien « Exporter en Excel » vers `/api{chemin}?{filtres}` (téléchargement),
  infobulle par défaut « La liste affichée (onglet et recherche) dans un classeur Excel ».
- **`CLES_ACHATS`** (`components/achats/types.ts:349-377`) : après toute écriture d'achat, 27 caches sont
  rafraîchis (commandes, réceptions, pesées, bobines, plan-achat, préparation, stock, soldes, lot, lots-sortis,
  traçabilité, besoins, production-besoins, cockpit, articles, mouvements, valorisation, contrôles,
  contrôles-soldes, prix-historique, prix-matrice, fournisseurs-performance, opportunités,
  dossiers-à-rattacher, dossiers, dossier, échéancier).
- **Recherche** : `filtrer` de `lib/recherche.ts` (plusieurs mots, tout ordre, sans accents), à la frappe ; les
  exports refont la même recherche côté serveur (`gestion_mp/api/exports_achats.py:52-62`).
- `gestion_mp/api/brouillons.py` (« Tout valider ») **ne couvre ni commandes ni réceptions** : seulement ordres
  de fabrication et opérations de stock (`brouillons.py:38-70`). Les brouillons de commande et de réception ne
  se valident qu'un par un depuis ces écrans.

---

### 1. PLAN D'ACHAT

#### Plan d'achat — `/plan-achat` (?onglet=fournisseurs|references)

- **Fichiers** : `pages/PlanAchat.tsx` (371 l.), `components/achats/TableFournisseurs.tsx`,
  `components/achats/PreparationCommande.tsx`, `components/achats/commun.tsx`, `components/achats/types.ts`.
- **Rôles** : menu + garde `['achats']` (direction aussi). Serveur : `GET /plan-achat` →
  `dependencies=[Depends(ACHATS)]` (`gestion_mp/api/pilotage.py:124`) ; `GET /stock` → `acteur` (tout connecté,
  `pilotage.py:44`). Rien ne change selon le rôle à l'écran (direction = achats ici).
- **Données** :
  - `GET /plan-achat` (option `date_reference`, non utilisée par l'écran → aujourd'hui) — `PlanAchat.tsx:92`.
    Renvoie `date_reference, references_a_commander, references_en_alerte, budget_mad, quantite_totale,
    references_classe_a, ruptures, critiques, urgents, attentions, ok, tiers{}, fournisseurs[], lignes[]`.
  - `GET /stock` (`PlanAchat.tsx:93-96`) : pour chaque référence `stock_disponible`, `bc_en_cours`,
    `couverture_jours`, `kg_par_ml` (colonnes Disponible / Commandé / Couverture / mètres).
- **Chargement / erreur** : « Un instant — chargement : le plan d'achat… » ; erreur : page « Plan d'achat » avec
  bandeau rouge = message, sinon « Le plan d’achat est indisponible. » (`PlanAchat.tsx:104-110`).
- **En-tête** : titre « Plan d'achat » ; sous-titre
  « Ce qu'il faut commander au {date de référence}, chez qui, et quand. « Préparer la commande » ouvre la
  proposition à arbitrer. » (`PlanAchat.tsx:131`).
  Actions : lien bouton « Besoins des mois à venir » → `/production?onglet=besoins`, infobulle « Les kilos que le
  plan de production consommera, mois par mois » ; `BoutonExport` chemin `/export/pilotage`, infobulle « Le stock,
  le plan d'achat, les fournisseurs, les besoins et les contrôles dans un classeur Excel » (`PlanAchat.tsx:134-144`).
- **Bandeau de succès après création** (`PlanAchat.tsx:148-161`) :
  - 1 bon : « Bon de commande créé en brouillon, sans numéro tant qu'il n'est pas envoyé. Relisez-le, imprimez-le
    et envoyez-le depuis l'écran Commandes. » + lien « Ouvrir le brouillon » → `/commandes?onglet=brouillon&ouvrir={id}`.
  - n bons : « {n} bons de commande créés en brouillon (un par devise : USD, EUR), sans numéro … » + lien
    « Ouvrir les brouillons » → `/commandes?onglet=brouillon`.
- **Indicateurs** (`PlanAchat.tsx:163-189`) :

| Indicateur | Valeur affichée | Formule / infobulle telle qu'affichée | Clic mène à |
|---|---|---|---|
| Références à commander | `nombre(references_a_commander)` ; détail « dont {n} en alerte » | serveur : nb de lignes de stock avec quantité à commander > 0 ; « en alerte » = celles dont le statut est dans `STATUTS_EN_ALERTE` (`calcul/moteur.py:1640-1646`) | — |
| Budget indicatif | `montantCourt(budget_mad)` ; détail « {kg} kg · prix catalogue » | infobulle = montant exact ; budget = Σ montant à commander en MAD (`moteur.py:1648`) | — |
| Références classe A | nombre ; détail « à commander » | Σ lignes à commander de classe A | — |
| Ruptures | nombre ; teinte `rupture` si > 0, sinon `ok` ; détail « {c} crit. · {u} urg. · {a} ATTENTION » | infobulle « {c} critiques · {u} urgentes · {a} en ATTENTION » ; comptés sur **toutes** les lignes de stock, pas seulement celles à commander (`moteur.py:1770-1773`) | — |
| À émettre cette semaine | nombre de lignes « 🔥 TIER 1 » ; teinte `critique` si > 0 ; détail « {n} sous 7 jours » (TIER 2) | voir règle des tiers ci-dessous | — |

- **Onglets** (`PlanAchat.tsx:191-198`) : « Par fournisseur » (compte = nb de fournisseurs), « Références à
  commander » (compte = nb de lignes). Défaut `fournisseurs`. Écrits dans `?onglet=`.
- **Carte** : titre
  - onglet fournisseurs : « Fournisseurs à solliciter, le plus gros budget d’abord » ;
  - onglet références : « Références à commander, triées par montant pondéré par la classe ABC (× 3 en A, × 2 en
    B) », infobulle « Toutes les références que le budget compte. Une ligne au statut OK est une commande de
    réapprovisionnement, pas une alerte. Tri : le montant à commander, en MAD, multiplié par 3 pour une matière de
    classe A et par 2 en classe B ».
  - Rangée `.filtres` : une seule `BarreRecherche` (partagée par les 2 onglets, valeur gardée en changeant d'onglet),
    placeholder « Fournisseur, pays, devise… » ou « Référence, couleur, fournisseur, priorité… ».
  - Recherche fournisseurs sur : nom, pays, contact, urgence, devises (`PlanAchat.tsx:115`). Recherche références
    sur : référence, nature, désignation, fournisseur, statut, tier, « classe A/B/C », risque, action (`:116-126`).
  - Aucun autre filtre, pas d'« Effacer les filtres », pas de tri cliquable, pas de pagination.

##### Onglet « Par fournisseur » — `TableFournisseurs` (`taille="court"`)
Voir la section *Table des fournisseurs* plus bas (partagée avec « Nouvelle commande »). Vide : « Aucun
fournisseur ne correspond. » (recherche) ou « Rien à commander aujourd’hui. ». Clic ligne ou bouton
« Préparer la commande » → fenêtre *Préparer une commande — {fournisseur}*.

##### Onglet « Références à commander » (`PlanAchat.tsx:230-355`, `Cadre taille="court"`, table `serre`)

| Colonne (libellé exact) | Contenu / unité | Alignement / format | Remarque |
|---|---|---|---|
| Référence | référence ; dessous (note) « nature · désignation » | texte, classe `reference`, max 155 px | infobulle = `relance` du serveur : « {statut} — {réf} ({fournisseur}) — Qté: {kg} kg — {montant} {devise} — Délai: {j}j » (`moteur.py:1698-1703`) |
| Fournisseur | bouton-lien = nom du fournisseur | texte | infobulle « Préparer la commande de ce fournisseur » ; clic → fenêtre de préparation |
| ABC (infobulle « Classe ABC : A, les matières qui pèsent le plus dans la consommation en valeur ») | A / B / C ou « — » | texte | |
| Statut | étiquette du statut (🔴 RUPTURE, CRITIQUE, URGENT, ATTENTION, 🟢 OK…) ; si « 🟢 OK » note « réapprovisionnement » | teinte `tonStatut` : RUPTURE→rupture, CRITIQUE→critique, URGENT→urgent, ATTENTION→attention, NON CONSOMM→neutre, sinon ok | |
| Disponible (kg) (infobulle « Stock disponible aujourd'hui (hors quarantaine), en kg ») | `stock_disponible` lu dans `/stock` | num | « — » si la référence n'est pas dans `/stock` |
| Commandé (kg) (infobulle « Déjà commandé, pas encore reçu, en kg ») | `bc_en_cours` de `/stock` | num | |
| Couverture (infobulle « Combien de jours le stock projeté couvre la consommation ») | `jours(couverture_jours)` | num | « — » si nul |
| À commander | « {kg} kg » ; notes : si contenance de commande > 1 « 3 palettes » (`quantiteEnUnites`) ; si l'unité d'achat est « ml » : « soit {n} ml » (infobulle « Le fournisseur facture au mètre : il lit les mètres »), sinon si densité « ≈ N ml » ; si `en_preparation` > 0 : « déjà en préparation : {kg} kg (brouillon n° 7, BC-…) » | num | infobulle de la note : « Un bon en brouillon ou à approuver porte déjà cette quantité : elle n'est pas reproposée (et ne compte pas comme commandée tant qu'il n'est pas envoyé) » ; `nomBonEnPreparation` traduit « BC-brouillon-7 » en « brouillon n° 7 » (`types.ts:380-383`) |
| Palettes (infobulle « Palettes entières à commander ») | nombre + note « entière(s) » | num | « — » si 0 ; infobulle « {n} palette(s) entière(s) » |
| Montant (infobulle « Au prix du catalogue ; en MAD au cours du jour ») | « {montant} {devise} » ; si devise ≠ MAD note « {n} MAD » | num | |
| Priorité · action | étiquette tier (« 🔥 TIER 1 »… teinte `tonTier` : T1 rupture, T2 critique, T3 attention, T4 neutre) ; note action (« Émettre cette semaine », « Émettre sous 7j », « Émettre sous 15j », « Regrouper sous 30j ») ; note risque (sourcing) | texte | |

- Ligne **non cliquable** (pas de classe `cliquable`) ; seul le nom du fournisseur est cliquable.
- Tri : imposé par le serveur (montant MAD × 3 en A, × 2 en B, départage par rang au catalogue) (`moteur.py:1650-1670`).
- Pas de pied de tableau.
- Vide : « Aucune référence ne correspond. » (recherche) ou « Rien à commander aujourd’hui. » (colSpan 11).

- **Notions métier** : quantité à commander (calcul de couverture), budget indicatif au prix catalogue, alerte vs
  réapprovisionnement (statut OK), classe ABC, tiers (règle `moteur.py:1605-1626` : RUPTURE → TIER 1 ; CRITIQUE →
  TIER 1 ; classe A et montant ≥ `seuil_tier1` (300 000 MAD) → TIER 1 ; montant ≥ `seuil_tier2` (200 000) → TIER 2 ;
  URGENT → TIER 2 ; montant ≥ `seuil_tier3` (100 000) → TIER 3 ; sinon TIER 4), « déjà en préparation » (bons en
  brouillon ou à approuver déduits de la suggestion et non comptés comme commandés), palettes entières, mètres
  indicatifs, facturation au mètre.

#### Table des fournisseurs (partagée) — `components/achats/TableFournisseurs.tsx`

Utilisée par l'onglet « Par fournisseur » du plan d'achat et par la fenêtre « Nouvelle commande ».

| Colonne (libellé exact) | Contenu / unité | Alignement / format | Remarque |
|---|---|---|---|
| Fournisseur | **nom** ; note contact ; note « {n} référence(s) en rupture » si ruptures | texte | |
| Pays | pays ou « — » | texte | |
| Devise(s) (infobulle « Un bon de commande par devise ») | devises séparées par « · » ; si > 1 note « un bon par devise » | texte | |
| Délai (infobulle « Délai de livraison déclaré du fournisseur ») | `jours(delai)` | num | |
| Références (infobulle « Matières que le calcul propose de commander chez lui ») | nb de références | num | « — » sans plan |
| Quantité (infobulle « En kilos, le cuir, les franges et le ruban compris ») | « {n} kg » | num | |
| Montant en devise (infobulle « Au prix du catalogue, avant confirmation par le fournisseur ») | une ligne par devise, `montant(v, d)`, triées par code | num | |
| Contre-valeur MAD (infobulle « Au cours du jour de chaque devise ») | `nombre(montant_mad)` | num | |
| Part (infobulle « Part de ce fournisseur dans le budget du plan d'achat ») | `part(part_budget)` | num | |
| Urgence | étiquette `libelleUrgence` : « 🚨 Urgent · 2 rupt. · 1 crit. · 3 urg. » (ou « 🚨 Urgent »), « 📋 À grouper », « 📝 Standard » ; sans plan : note « rien à commander » | teinte : URGENT → rupture, groupé → attention, sinon neutre | |
| (sans titre) | bouton « Préparer la commande » (principal si plan, neutre sinon), infobulle « Ouvre la proposition : vous cochez, ajustez, et le bon est créé en brouillon » | | `stopPropagation` |

- Ligne `cliquable`, infobulle « Préparer la commande », clic → préparer (`TableFournisseurs.tsx:111`).
- Pied (seulement si > 1 fournisseur avec plan) : « {n} fournisseurs à solliciter » · Σ références · « Σ kg kg » ·
  (vide) · Σ contre-valeur MAD (`:161-172`).
- Vide : texte passé par l'appelant.
- Règle d'urgence serveur (`moteur.py:1728-1738`) : « 🚨 BC URGENT » si une ligne est en rupture, critique ou
  urgente (jamais pour le seul montant hors mode classeur) ; sinon « 📋 BC groupé » si montant MAD ≥ `seuil_bc_groupe`
  (100 000) ; sinon « 📝 Standard » ; tri par budget MAD décroissant.

#### Fenêtre « Préparer une commande — {fournisseur} » — `components/achats/PreparationCommande.tsx`

Ouverte depuis le plan d'achat (deux onglets) et depuis Commandes › Nouvelle commande. `Dialogue tresLarge sale={modifie}`.

- **Rôles** : achats/direction. Serveur : `GET /plan-achat/fournisseur/{nom}` → `ACHATS` (`pilotage.py:138`) ;
  `POST /commandes` → `ACHATS` (`achats.py:452`).
- **Données** : `GET /plan-achat/fournisseur/{nom encodé}` (fournisseur, pays, contact, email, délai, devise par
  défaut, date de référence, lignes avec `quantite_suggeree`, `unite_commande`, `unites_suggerees`,
  `unites_possibles`, `minimum_commande`, `prix_indicatif`, `en_preparation`, `bons_en_preparation`…) ;
  `useFournisseurs`, `useArticles`, `useDevises` (référentiels de `lib/donnees.ts`). 404 serveur : « fournisseur
  inconnu : « {nom} » ».
- **Titre** : « Préparer une commande — {fournisseur} » + note « {pays} · {contact} · {email} · délai {n} j · calcul
  au {date} » ; infobulle de la note : « Les quantités proposées sont celles du calcul (couverture visée, minimum de
  commande, arrondi au conditionnement). Cochez les lignes à commander et ajustez-les dans l'unité où vous commandez :
  le bon est créé en brouillon, sans numéro ; il reçoit son numéro à l'envoi. »
- **Chargement** : « Un instant — chargement : les quantités suggérées… » ; erreur de lecture : bandeau rouge.
- **Départ** (une seule fois, `:159-204`) : une ligne par ligne suggérée dont la matière existe dans le catalogue ;
  unité = `unite_commande` du serveur si parmi les unités possibles, sinon la dernière unité possible, sinon kg ;
  quantité = suggestion (au kilo : **arrondie au kilo entier supérieur**) ; toutes cochées. Note « déjà en
  préparation : {kg} kg (brouillon n° 7), déduits ».
- **Indicateurs** (`:348-367`) :

| Indicateur | Valeur affichée | Formule / infobulle | Clic |
|---|---|---|---|
| Lignes retenues | « {retenues} / {total} » | retenue = cochée et quantité > 0 | — |
| Quantité totale | « {Σ kg} kg » | Σ quantités retenues | — |
| Palettes | `nombre(Σ quantité / contenance palette, 1)` ; détail « {n,nn} conteneur(s) » ou « palettes / conteneur ? » ; teinte `attention` s'il reste > 0,05 palette de place | conteneurs = palettes ÷ palettes par conteneur | — |
| Montant indicatif | `montants(par devise)` | infobulle « Au prix du catalogue : le fournisseur confirmera le sien » ; détail « ≈ {MAD} au cours du jour » si une devise étrangère, sinon « au prix du catalogue » ; MAD = Σ montant × taux du jour | — |

- **Formulaire (rangée)** :
  - « Livraison prévue » (date, min aujourd'hui, 170 px), aide « vide : date d’envoi + {délai} j (délai du
    fournisseur) ». Facultative.
  - « Palettes par conteneur » (nombre, placeholder « ex. 20 », 150 px) — ne marque pas la saisie comme modifiée,
    n'est pas envoyée au serveur (aide au remplissage seulement).
  - « Ajouter une matière de ce fournisseur » (`ChoixRecherche`, 340 px) : matières **actives** de ce fournisseur pas
    encore dans la liste ; libellé « {réf} — {désignation} », détail = devise ; placeholder « Référence, couleur,
    titrage… ». La ligne ajoutée : statut « ajoutée », unité = dernière unité possible (`unitesDe`), quantité = une
    unité si contenance > 1 sinon le minimum de commande, prix = prix catalogue au kg.
  - Pleine largeur : « Remarques au fournisseur » (textarea 2 lignes), aide « imprimées sur le bon, qui est en
    anglais : les écrire en anglais (ex. « Deliver in one shipment ») », placeholder « Deliver in one shipment, attach
    the certificate of origin… ». Envoyées comme `observations` (≤ 2000 car. serveur).
- **Message de remplissage** : « Il reste la place de **{n} palette(s)** dans le dernier conteneur ({N} au total). »
  (si > 0,05 palette manquante).
- **Tableau** (`table saisie serre`, `Cadre taille="dialogue"`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Cmd. (infobulle « Cocher pour commander la ligne ») | case à cocher | | ligne décochée à 50 % d'opacité |
| Référence | réf. ; note « nature · désignation · devise » | | |
| Statut · couverture | étiquette statut (ou étiquette neutre « ajoutée ») ; note « classe A · couvre 45 j » ou « — » | | |
| Stock projeté (kg) | nombre ou « — » | num | |
| Conso / mois (kg) | nombre ou « — » | num | |
| Suggéré (kg) (infobulle « La quantité que le calcul propose, et la même dans l'unité de commande ») | suggestion ou « — » ; note « 7 palettes » si unité ≠ kg ; note « déjà en préparation… » | num | |
| Commandé en | liste déroulante des unités : « kg », « Bobine (2,5 kg) », « Palette (862,4 kg) », « Fût (200 kg) »… (`libelleUnite`) | 150 px min | changer l'unité garde les kilos |
| Quantité | nombre d'unités (2 déc.), pas 1 (unité) ou 10 (kg) ; note = unité | num, 120 px | saisir → kilos = unités × contenance |
| Soit (kg) | kilos (1 déc.) ; note mètres ; note orange « sous le minimum ({min} kg) » ou « {unité} entamée » | num, 130 px | avertissement non bloquant |
| Écart (infobulle « Ce que vous commandez face à la suggestion du calcul ») | « non commandée » / étiquette « hors calcul » (ajoutée) / « — » / « suggestion » (|écart| < 0,5 %) / étiquette `signe(écart, 0)` | num | teinte ok si |écart| ≤ 10 %, attention si au-dessus, critique si en dessous |
| Montant indicatif (infobulle « Au prix du catalogue, avant confirmation par le fournisseur ») | « {kg × prix} {devise} » ; note « {prix} {devise} / kg » | num | « — » sans prix |
| (sans titre) | bouton danger « Retirer » (lignes ajoutées seulement) | | |

  Vide : « Rien à commander chez ce fournisseur selon le calcul. Ajoutez ci-dessous les matières que vous voulez
  commander quand même. »
- **Gestes** (pied `:602-658`) :

| Geste | Où | Rôle | Conditions / grisé | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| « Arrondir au conditionnement » (infobulle « Chaque quantité monte au conditionnement entier suivant ») | pied | achats | — | — | aucun (local) | quantités en unités entières | — |
| « Revenir à la suggestion » (infobulle « Retrouver les quantités calculées, sans les lignes ajoutées ») | pied | achats | — | — | aucun | retire les lignes ajoutées, recoche tout | — |
| Case « Envoyer sans les prix (le fournisseur les annonce) » / décochée « Envoyer avec nos prix du catalogue, « à confirmer » » | pied | achats | cochée par défaut | — | champ `sans_prix` | — | infobulles : « Le bon part sans prix : le fournisseur annonce les siens » / « Le bon part avec nos prix du catalogue, imprimés « à confirmer » » |
| « Annuler » | pied | | — | si saisie : « Abandonner la préparation ? » · « Oui, abandonner » | — | ferme | — |
| « Créer le bon en brouillon · {Σ kg} kg » ou « Créer {n} bons (un par devise : EUR, USD) · {Σ} kg » ; pendant l'envoi « Création… » | pied, principal | achats | grisé si aucune ligne retenue ou envoi en cours (infobulle fixe « Le bon est créé en brouillon, sans numéro : il se relit, s'imprime et s'envoie depuis l'écran Commandes ») | — | `POST /commandes` `{fournisseur_id, date_livraison_prevue|null, sans_prix, observations, lignes:[{article_id, quantite (kg, 3 déc.), unite_achat, contenance, prix:null}]}` | fenêtre fermée ; message de la page appelante (voir Plan d'achat / Commandes) | écran : « Fournisseur « {nom} » introuvable dans la liste des fournisseurs. » ; serveur : « Fournisseur inconnu. », « Matière inconnue dans la commande. », « « {réf} » n'est pas fournie par ce fournisseur. », « « {réf} » figure deux fois : regrouper les quantités. », « « {réf} » : commandée en kg, la contenance vaut 1. », « « {réf} » ne se commande pas en « {unité} » : kg, Bobine, Palette… (fiche de la matière). », « « {réf} » : une {unité} contient {x} kg, pas {y} (fiche de la matière). » ; quantité ≤ 0 refusée par validation (gt=0) |

- **Règles serveur de création** (`achats.py:452-486`) : un bon **par devise** de matière (ordre alphabétique),
  statut `brouillon`, `numero=None`, `date_commande` = aujourd'hui (provisoire), date prévue gardée si saisie, sinon
  vide (comptée à l'envoi) ; `sans_prix=true` → prix 0 ; sinon prix = prix catalogue au kg (non confirmé) ;
  journal « création commande ». Unités permises (`achats.py:396-408`) : kg (contenance 1), Bobine (= poids bobine),
  Palette (= poids bobine × bobines par palette), l'unité d'achat de la fiche (hors kg/ml) à sa contenance.
- **Notions** : on ne commande jamais sans arbitrer ; unités de commande (kilo, bobine, palette, fût, sac…) liées
  aux kilos ; minimum de commande ; conteneur rempli palette par palette ; un bon par devise ; bon sans prix ;
  date promise comptée à l'envoi.

---

### 2. COMMANDES

#### Commandes — `/commandes` (?onglet=brouillon|a_approuver|envoyee|confirmee|clos, ?filtre=retard, ?ouvrir=ID | ?commande=ID)

- **Fichiers** : `pages/Commandes.tsx` (408 l.), `components/achats/DetailCommande.tsx`,
  `ChoixFournisseurCommande.tsx`, `PreparationCommande.tsx`, `TableFournisseurs.tsx`, `commun.tsx`, `types.ts`,
  `lib/commandes.ts` (liens entrants).
- **Rôles** : menu + garde `['achats']`. Serveur `GET /commandes` → `ACHATS` (`achats.py:368`). Différence de rôle
  à l'écran : l'indicateur « Bons ouverts » prend la teinte `urgent` et l'infobulle « Votre accord est attendu » pour
  la **direction** quand des bons sont à approuver ; pour achats : « En attente de la direction »
  (`Commandes.tsx:155-167`). Dans la fiche, seuls les comptes direction voient « Approuver et envoyer » et
  « Renvoyer aux achats… ».
- **Données** : `GET /commandes` (liste complète, plus récent d'abord, `commande_dict` `achats.py:294-365`).
- **Chargement** : « Un instant — chargement : les commandes… » ; erreur : page « Commandes » + bandeau rouge.
- **En-tête** : titre « Commandes » ; sous-titre « Un bon part sans prix, le fournisseur les confirme, puis il est
  reçu. Tant que rien n’est reçu, il se modifie. » Actions : `BoutonExport` `/export/commandes?onglet={onglet}&q={recherche}` ;
  bouton principal « Nouvelle commande ».
- **Bandeau succès de page** : « {numéro ou Brouillon} supprimé. » après suppression ; après création :
  « Bon créé en brouillon, sans numéro tant qu'il n'est pas envoyé. » ou « {n} bons créés en brouillon (un par
  devise), sans numéro tant qu'il n'est pas envoyé. » (un seul bon → sa fiche s'ouvre sur « Lignes et livraison » et
  l'onglet passe à Brouillons). Le message s'efface en changeant d'onglet ou en ouvrant un bon.
- **Indicateurs** (portent sur **tous** les bons, quels que soient filtre et recherche ; `:126-196`) :

| Indicateur | Valeur | Formule / infobulle | Clic |
|---|---|---|---|
| Bons ouverts | nb de bons hors soldés/annulés ; détail « {b} brouillon(s) · {a} à approuver » | infobulle « Votre accord est attendu » (direction) / « En attente de la direction » (achats) si à approuver ; teinte urgent (direction seulement) | — |
| Montant engagé | `montantCourt(Σ montant_estime_mad des bons envoyés + confirmés)` ; détail « {n} bon(s) partis » | infobulle « {montant exact} — dont {k} bon(s) estimé(s) au prix du catalogue, prix à confirmer » ou montant exact | — |
| Reste à recevoir | `montantCourt(Σ reste_estime_mad des bons partis)` ; détail « pas encore arrivé » | infobulle montant exact ; reste estimé = reste kg × prix confirmé sinon catalogue, × cours figé sinon du jour | — |
| Prix à confirmer | nb de bons ouverts envoyés/confirmés ayant au moins un prix non confirmé ; teinte attention ; détail « bons partis » | | — |
| En retard | nb de bons ouverts dont l'état de livraison contient « retard » ; teinte critique sinon ok ; détail « date prévue dépassée » | | — |

- **Onglets** (`:37-66, 198-205`) — libellé (compte = bons trouvés par la recherche, tous onglets) ; aide = titre de
  la carte :
  - « Brouillons » — « Pas encore partis, sans numéro : relire, imprimer, envoyer »
  - « À approuver » — « Au-delà du seuil : la direction approuve ou renvoie »
  - « Envoyées » — « Partis, prix pas encore tous confirmés »
  - « Confirmées » — « Prix confirmés : suivre l’expédition et l’arrivée »
  - « Soldées / annulées » — « Reçus, soldés ou annulés : « Rouvrir » remet en attente »
  Onglet par défaut sans `?onglet=` : le premier onglet non vide (après filtre retard), sinon Brouillons.
- **Filtres (rangée de la carte)** : note « {n} bon(s) trouvé(s), tous onglets » quand une recherche est tapée ;
  case « en retard seulement » (infobulle « Livraison prévue ou ETA dépassée ») qui écrit/efface `?filtre=retard`
  (lien du Cockpit/Accueil) ; `BarreRecherche` placeholder « N°, fournisseur, référence, conteneur… », sur : n° (ou
  « Brouillon »), fournisseur, pays, devise, état de livraison, statut, créé par, observations, conteneur, navire,
  « réf. désignation » de chaque ligne. Pas de bouton « Effacer les filtres ».
- **Tableau** (`Cadre taille="court"`, table `serre`, `LigneListe` `:333-408`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| N° · date (infobulle « La date du bon est celle de son envoi ») | n° (ex. BC-2026-0012) ou étiquette neutre « Brouillon » ; note date du bon ou « daté à l’envoi » | mono, nowrap | |
| Fournisseur | **nom** ; note « {1re réf.} + {n−1} » | 200–260 px, ellipse | infobulle = toutes les références (une par ligne) |
| Quantité (infobulle « En kilos, le cuir, les franges et le ruban compris ») | Σ kg | num | |
| Montant | si tous les prix à confirmer : étiquette attention « prix à confirmer » + note « ≈ {montant estimé devise} » (infobulle « Au prix du catalogue ») ; sinon montant estimé en devise + note « {n} prix à confirmer » | num | |
| Montant MAD (infobulle « Au cours figé à la confirmation, sinon au cours du jour ; prix du catalogue tant que le prix n’est pas confirmé ») | `nombre(montant_estime_mad)` | num | |
| Livré | `part(part_livree, 0)` ou « — » si rien reçu | num | part = min(1, reçu ÷ commandé) |
| État de livraison (infobulle « Où en est la livraison du bon ») | étiquette du libellé serveur, ou note « pas envoyé » sans numéro ; note « livrée le {date} » ou « dernière arrivée le {date} » | teinte `tonLivraison` : Livré→ok, retard→critique, En cours/réserve→attention, Soldé/Annulé→neutre, sinon accent | |
| Livraison prévue / ETA | date de l'ETA si posée, sinon de la livraison prévue ; note « ETA · {conteneur} » | date | |
| Statut | étiquette (Brouillon neutre, À approuver urgent, Envoyée accent, Confirmée ok, Soldée/Annulée rupture) ; note « renvoyé par la direction » si renvoi | | |
| (sans titre) | bouton principal « Saisir les prix » (infobulle « Ouvre le bon sur les prix du fournisseur ») si bon envoyé/confirmé avec prix à confirmer ; sinon « Ouvrir » (principal si à approuver) | | |

  Ligne `cliquable` → fiche sur « Lignes et livraison ». Pas de pied, pas de tri cliquable (ordre serveur : id
  décroissant), pas de pagination.
  Vide : avec recherche « Aucun bon de cet onglet ne correspond (voir les autres onglets). » (parenthèse seulement si
  d'autres onglets ont des résultats) ; Brouillons : « Aucun brouillon. Préparez un bon depuis le plan d’achat ou avec
  « Nouvelle commande ». » ; autres : « Aucun bon ici. ».
- **États de livraison (serveur, `achats.py:78-100`)** : « » (pas parti) ; « 🟢 Livré » (chaque ligne reçue à
  `toler_in_full` près, net des retours, hors quarantaine) ; « ⚫ Soldé » / « ⚫ Soldé sans livraison » ; « ⚫ Annulé » ;
  « 🟡 Reçu sous réserve » (tout là mais une part en quarantaine) ; « 🟡 En cours » / « 🟠 Partiel retard » ; « ⚪ Attendu »
  / « 🔴 En retard » (date = ETA sinon livraison prévue, + `toler_retard_jours` de grâce).
- **Liens entrants** : `lib/commandes.ts:67-70` `versCommandes` → `/commandes?onglet={onglet}&commande={id}` ou
  `/commandes?onglet=…&filtre=retard` ; Plan d'achat → `?onglet=brouillon&ouvrir=ID` ; fiche réception →
  `/commandes?ouvrir={id}`. L'ouverture par adresse ouvre toujours le volet « Lignes et livraison ».
- **Export** `GET /export/commandes?onglet&q` (`exports_achats.py:84-143`, `ACHATS`) : classeur « commandes-AAAA-MM-JJ.xlsx »,
  titre « Bons de commande — exporté le jj/mm/aaaa », « Filtres : onglet « … » · recherche « … » » (ou « aucun »).
  Feuille « Commandes » : N°, Date du bon, Fournisseur, Pays, Statut, Livraison, Lignes, Commandé (kg), Reçu (kg),
  Reste à livrer (kg), Livré, Devise, Montant confirmé, Montant estimé, Montant MAD, Reste à recevoir MAD, Prix à
  confirmer, Cours figé, Livraison prévue, ETA, Livrée le, Dernière réception, Conteneur, Par, Approuvé par,
  Observations. Feuille « Lignes » : N°, Fournisseur, Statut, Référence, Désignation, Commandé en, Unités, Commandé
  (kg), Reçu (kg), Reste à livrer (kg), Prix / kg, Devise, Prix confirmé (« oui » / « non (prix du catalogue) »),
  Confirmé par, Confirmé le, Montant. Le filtre « en retard » n'est **pas** transmis.

#### Fenêtre « Nouvelle commande — chez quel fournisseur ? » — `ChoixFournisseurCommande.tsx`

- `Dialogue tresLarge` (pas de `sale`). Données : `useFournisseurs`, `GET /plan-achat`.
- Texte : « La préparation s'ouvre avec les quantités que le calcul suggère chez ce fournisseur (couverture visée,
  minimum de commande, conditionnement). Vous cochez, ajustez, ou ajoutez d'autres matières : on ne commande jamais
  sans arbitrer. »
- Filtres : recherche placeholder « Nom, pays, contact, devise… » (nom, pays, contact, devises, urgence) ; case
  « Montrer aussi les fournisseurs chez qui rien n'est à commander ». Par défaut : seuls les fournisseurs **actifs**
  ayant une suggestion au plan. Tri : contre-valeur MAD décroissante puis nom.
- Tableau = *Table des fournisseurs* (`taille="dialogue"`) ; devises = celles de la fiche fournisseur (sinon sa devise).
  Vide : « Aucun fournisseur ne correspond. » (recherche) ou « Rien n'est à commander aujourd'hui : cochez la case pour
  voir tous les fournisseurs. ».
- Chargement : « … chargement : les fournisseurs et le plan d'achat… » ; erreur du plan : bandeau rouge.
- Gestes : clic ligne / « Préparer la commande » → ferme et ouvre *Préparer une commande* ; « Fermer ».

#### Fiche « Bon de commande {n° | (brouillon)} — {fournisseur} » — `components/achats/DetailCommande.tsx` (1115 l.)

`Dialogue tresLarge sale={lignes, prix ou expédition en cours de saisie}`. Ouverte depuis la liste, l'adresse
(`?ouvrir=` / `?commande=`), la création. Un bon disparu : fenêtre « Bon de commande » « Chargement… » puis
« Ce bon n'existe plus. ».

- **Rôles** : `compte.role === 'direction'` → `direction` (`:125-126`). Droits serveur : tous les gestes `ACHATS`
  sauf `POST /commandes/{id}/approuver` et `/renvoyer` → `DIRECTION` (`achats.py:719-721, 764-766`).
- **Données** : la liste `GET /commandes` (cache partagé ; la fiche relit le bon dans la liste),
  `useArticles`, `GET /pieces/commande/{id}` (`usePieces`). Relecture du serveur : remplace l'affichage sauf ce qui est
  en cours de saisie (`:152-161`).
- **Titre** : « Bon de commande {numéro} — {fournisseur} » ou « Bon de commande (brouillon) — … » + étiquette statut +
  étiquette état de livraison (si parti) + note « {pays} · envoyé le {date} | pas encore envoyé · créé par {nom} le
  {horodatage} · {devise} · approuvé par {nom} le {horodatage} ».
- **Indicateurs** (`:356-402`) :

| Indicateur | Valeur | Détail / infobulle | Teinte |
|---|---|---|---|
| Commandé | « {Σ} kg » | « {n} ligne(s) » | |
| Reçu | « {reçu} kg » | « livré en entier le {date} » / « {x %} livré · dernière réception le {date} » / « {x %} livré » | ok si part ≥ 98 %, attention si reçu > 0 |
| Montant estimé (s'il reste des prix à confirmer) / Montant | montant estimé ou confirmé en devise | infobulle « Prix confirmés, et prix du catalogue pour ceux qui restent à confirmer » ; détail « {n} prix à confirmer » ou « prix confirmés » + « ≈ {MAD} » si devise étrangère | attention si prix à saisir |
| Arrivée prévue (ETA) / Livraison prévue | date ETA sinon livraison prévue | « conteneur {n°} » | |
| Cours figé (devise ≠ MAD seulement) | « 1 USD = {cours, 4 déc.} MAD » ou « — » | « à la confirmation du {date} » ou « pas encore : cours du jour {taux} » | |

- **Bandeaux** :
  - Renvoi : « **Renvoyé aux achats** par {nom} le {horodatage} : « {motif} ». » + (parti) « Le changement n’est pas
    accepté : le bon reste chez le fournisseur tel qu’il était parti. » / (brouillon) « Corrigez le bon, puis
    soumettez-le de nouveau — ou supprimez-le. » (renvoi visible pour statuts brouillon, envoyée, confirmée, tant
    qu'aucune soumission/envoi/approbation n'a suivi — `achats.py:133-146, 360`).
  - À approuver : (parti) « Ce bon, déjà chez le fournisseur, a changé de montant (≈ {MAD}, seuil {seuil}) : » /
    (brouillon) « Ce bon dépasse le seuil d’approbation ({seuil}) : » + direction « relisez-le, puis « Approuver et
    envoyer », ou « Renvoyer aux achats » avec un motif. » ; achats parti « il attend l’accord de la direction. Ne
    confirmez pas le changement au fournisseur avant. » ; achats brouillon « il attend l’accord de la direction avant
    de partir. ».
- **Volets (Onglets, état local, non écrits dans l'adresse)** : « Lignes et livraison » (compte lignes), « Prix du
  fournisseur » (compte « {n} à saisir »), « Suivi de l’expédition », « Réceptions » (compte), « Pièces jointes »
  (compte). Changer de volet efface les messages.

##### Volet « Lignes et livraison »
- Si `modifiable` (statut ni soldé ni annulé **et** aucune ligne nommée par une réception, même brouillon ou annulée —
  `achats.py:53-57, 362-363`) :
  - si parti : bandeau « Ce bon est déjà parti. Vous pouvez encore le corriger (rien n'est reçu) : pensez à renvoyer le
    bon réimprimé au fournisseur. »
  - « Livraison prévue » (date, 160 px) ; aide « figée avec les prix : une nouvelle date va dans l’ETA » (parti et cours
    figé → champ grisé), « promise par le fournisseur » (parti), « vide : date d’envoi + délai du fournisseur »
    (brouillon) ; min = date du bon si parti.
  - « Remarques au fournisseur (imprimées sur le bon, en anglais) » (texte une ligne, 280 px).
  - « Ajouter une matière ({devise}) » (`ChoixRecherche`, infobulle « Seules les matières de ce fournisseur, dans la
    devise du bon ») : matières actives du fournisseur, même devise, absentes du bon ; placeholder « Référence, couleur,
    titrage… ».
  - « Annuler les changements » (si saisie), « Enregistrer » (principal, grisé si rien n'a changé ou envoi en cours).
- Sinon bandeau : clos « Ce bon est clos : il ne se modifie plus. « Rouvrir » le remet en attente de livraison. » ;
  déjà livré « Ce bon a commencé à être livré : ses lignes sont figées. Pour un complément, préparez un autre bon ;
  s’il ne viendra rien de plus, soldez-le. » + « Observations : {remarques} ».
- **Tableau** (`table saisie serre`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Référence | réf. ; note désignation | | |
| Commandé en | liste d'unités (modifiable) ou libellé « Palette (862,4 kg) » | 170 px | une unité déjà sur le bon reste proposée même si la fiche a changé |
| Quantité | unités (2 déc.) ; note unité | num | |
| Soit (kg) | kilos (2 déc.) ; note mètres | num | |
| Reçu (kg) (infobulle « Pesé aux réceptions validées, moins ce qui est reparti chez le fournisseur ») | reçu ou « — » ; note « {x %} » ; note « dont {n} en quarantaine » (infobulle « Reçu sous réserve : le bon ne se solde qu'à sa libération ») | num | |
| Reste à livrer (kg) (infobulle « Commandé moins reçu ; un reliquat sous la tolérance compte pour complet ») | reste, ou étiquette ok « complet », ou la quantité si rien reçu ; « — » si clos | num | |
| Prix / kg | « {prix} {devise} » si confirmé ; note « {prix} à confirmer » (infobulle « Notre prix proposé, imprimé « à confirmer » ») ; ou note « à confirmer » | num | |
| Montant | kg × prix si confirmé, sinon « — » | num | |
| (si modifiable) | bouton danger « Retirer » ; grisé s'il ne reste qu'une ligne, infobulle « Un bon garde au moins une ligne : supprimez le bon » (sinon « Retirer cette matière du bon ») | | |

  Pied : « Total » · Σ kg (lignes éditées) · « {reçu} kg » · « {reste} kg » (vide si clos) · · montant des lignes
  confirmées ou « — ».
- **Geste « Enregistrer »** : contrôle écran « Chaque ligne doit avoir une quantité : retirez celles qu’on ne commande
  plus. » ; `PUT /commandes/{id}` `{date_livraison_prevue|null, observations, lignes:[{article_id, quantite, unite_achat,
  contenance, prix:null}]}`. Messages de succès selon le résultat (`:260-273`) :
  - à approuver → brouillon : « Bon modifié pendant que la direction le relisait : il revient en brouillon. Soumettez-le
    de nouveau quand il est prêt. »
  - à approuver (parti) → reparti : « Bon ramené à ce que la direction avait accepté : il n’a plus besoin d’elle et
    reprend sa route. »
  - devenu à approuver : « Bon modifié : il dépasse désormais le seuil d’approbation (≈ {MAD}) et repasse par la
    direction. Ne le renvoyez pas au fournisseur avant son accord. »
  - sinon « Bon modifié. Il est déjà parti : réimprimez-le et renvoyez-le au fournisseur. » ou « Bon modifié. ».
  Refus serveur (`achats.py:639-682, 614-636`) : « Ce bon est clos. » (409) ; « Ce bon a déjà des réceptions : ses
  lignes ne se modifient plus. Créer un autre bon pour le complément, ou le solder. » (409) ; « La livraison promise
  ({date}) est figée depuis la confirmation des prix : elle mesure la ponctualité. Noter la nouvelle date annoncée par
  le fournisseur dans l'arrivée prévue (ETA) du suivi d'expédition. » ; « La livraison était promise pour le {date},
  date passée : elle ne se repousse plus. {idem ETA} » ; « La livraison prévue ({date}) précède la date du bon
  ({date}). » ; « Ce bon est en {devise} : une matière d'une autre devise va sur un autre bon. » ; plus les refus de
  lignes/unités de la création. Règles : un prix confirmé inchangé garde sa confirmation (auteur, date) ; une ligne
  ajoutée attend son prix (un bon « Confirmée » repasse « Envoyée ») ; puis garde-fou d'approbation
  `_controler_montant` (`achats.py:246-291`).

##### Volet « Prix du fournisseur »
- Bon annulé : « Ce bon est annulé : ses prix ne se confirment plus. ».
- Texte : « Recopiez les prix que le fournisseur a confirmés (proforma, courriel), **au kilo, en {devise}** (un
  fournisseur qui facture au mètre : son prix au mètre ÷ la densité ; l'équivalent au mètre s'affiche sous la saisie).
  Ce sont eux que la réception retiendra comme prix payé. Quand tous les prix d'un bon envoyé sont confirmés, il passe
  à « Confirmée » ; le cours de la devise se fige à la première confirmation. »
- Tableau : Référence (+ désignation) · Quantité (kg) (+ mètres) · Prix catalogue / kg (« {prix} {devise catalogue} » +
  note « soit {x} / ml » si prix au mètre) · Prix confirmé / kg (saisie, placeholder « à saisir », + note « soit {x} /
  ml ») · Écart (« — » / « identique » si < 0,5 % / étiquette `signe`, attention si hausse, ok si baisse) · Montant
  (saisi × kg) · État (étiquette « confirmé » ok / « à confirmer » attention ; note « par {nom} le {horodatage} » sauf
  ligne reprise sans auteur).
- Case « Mettre aussi à jour le prix du catalogue (conseillé : c'est le prix du moment) » (cochée par défaut).
- « Reprendre les prix du catalogue » (infobulle « Remplit les prix vides avec ceux du catalogue — à vérifier avant de
  confirmer ») : seulement si la devise du catalogue = devise du bon.
- « Confirmer ces prix » (`Confirmer` principal ; grisé si aucun prix saisi ou envoi ; infobulle « Enregistre les prix
  comme confirmés par le fournisseur ») ; question « Confirmer {n} prix ? Le prix du catalogue changera pour : {réfs}. »
  / « Aucun prix du catalogue ne change. » / « Le catalogue garde ses prix. » ; « Oui, confirmer ». Contrôle écran
  « Saisissez au moins un prix. ». `POST /commandes/{id}/prix` `{prix:[{ligne_id, prix}], mettre_a_jour_catalogue}`.
  Succès : « {n} prix confirmé(s), {k} reporté(s) au catalogue. Il reste {r} prix à confirmer. ». Refus : « Ce bon est
  annulé. » (409), « Ligne étrangère à ce bon. », règles de date promise. Serveur (`achats.py:808-843`) : cours figé à
  la 1re confirmation ; statut envoyée → confirmée si tout confirmé ; catalogue mis à jour (prix × densité pour une
  fiche au mètre, version +1) ; hausse ≤ 5 % sans repasser par la direction (`tolerance=0.05`).

##### Volet « Suivi de l’expédition »
- Non parti : « Ce bon n'est pas encore parti : son expédition se suivra après l'envoi. ».
- Texte : « Les étapes du voyage, à remplir au fil des nouvelles du fournisseur ou du transitaire. Seule l'arrivée
  prévue (ETA) est une attente : elle remplace la livraison prévue dans le calcul du stock projeté. »
- Formulaire (dates, max aujourd'hui sauf ETA) : « Proforma reçue le » (aide « la facture provisoire du fournisseur »),
  « Acompte payé le » (« le virement d’avance, s’il y en a un »), « Embarquée le » (« date de départ (connaissement) »),
  « Arrivée prévue (ETA) » (« remplace la livraison prévue dans le calcul »), « Arrivée au port le » (« déchargement
  constaté »), « Dédouanée le » (« mainlevée de la douane »), « Arrivée à l’usine le » (« le camion à la bascule ») ;
  « N° de conteneur » (placeholder « ex. MSCU1234567 », ≤ 60), « Navire » (≤ 80).
- « Annuler les changements » ; message rouge « « {jalon} » ne se date pas dans le futur : seule l’ETA est une
  attente. » ; « Enregistrer le suivi » (grisé si rien changé, envoi, ou jalon futur). `PUT /commandes/{id}/expedition`.
  Succès : « Suivi enregistré. L'arrivée prévue (ETA) du {date} remplace la livraison prévue dans le calcul du stock. »
  ou « Suivi de l’expédition enregistré. ». Refus : « Ce bon n'est pas encore parti : son expédition se suit après
  l'envoi. » (409) ; « « {libellé} » ne se date pas dans le futur : c'est un fait constaté. Une date attendue va dans
  l'arrivée prévue (ETA). ».

##### Volet « Réceptions »
- Tableau : Réception (n° ou « Brouillon ») · Arrivée · Statut (Validée ok / Annulée rupture / Brouillon attention) ·
  lien « Ouvrir la réception ». Ligne cliquable → `/receptions?ouvrir={id}`. Vide : « Rien n'est encore arrivé sur ce
  bon. ».

##### Volet « Pièces jointes »
- `PiecesJointes objet="commande"` : bouton « Joindre un document… » (« Envoi… »), glisser-déposer, note « ou le
  glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; retrait
  confirmé. Routes `GET/POST /pieces/commande/{id}`, `GET /piece/{id}/fichier`, `DELETE /piece/{id}` (toutes `ACHATS`,
  `suivi.py:242-290`). Refus : « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. »,
  « Fichier trop lourd (20 Mo au plus). », « Document inconnu. » ; écran : « « {nom} » est trop lourd : 20 Mo au plus. ».

##### Gestes du pied de la fiche (`DetailCommande.tsx:923-1112`)

| Geste | Où | Rôle | Conditions / grisé (infobulle) | Confirmation | Appel API | Succès | Refus (serveur) |
|---|---|---|---|---|---|---|---|
| « Imprimer le bon » | pied, toujours | achats | infobulle « Ouvre le bon prêt à imprimer ou à enregistrer en PDF » | — | ouvre un onglet `/api/commandes/{id}/impression` | document A4 (§ 4) | « Commande introuvable. » 404 |
| « Excel pour le fournisseur » (lien) | pied, toujours | achats | infobulle « Le bon dans un classeur Excel, prêt à envoyer au fournisseur » | — | `GET /api/export/commandes/{id}/bon` (téléchargement) | fichier `{n°}.xlsx` ou `brouillon-{id}.xlsx` | « Bon de commande introuvable. » 404 |
| « Marquer comme envoyé » / « Envoyer, ou demander l’approbation » (si `approbation_requise`) | brouillon | achats | grisé si saisie non enregistrée (« Enregistrez d’abord vos modifications ») ou envoi ; infobulles « Le montant dépasse le seuil : le bon part d’abord à la direction » / « Le bon reçoit son numéro et sa date : il est parti chez le fournisseur » | sous le seuil : « Envoyé le [date, défaut aujourd'hui, max aujourd'hui] : le bon reçoit son numéro. » (ou « : le bon {n°} repart corrigé. ») · « Oui, il est envoyé » ; au-delà : « ≈ {MAD} : au-delà du seuil de {seuil}, le bon attendra l'accord de la direction. » · « Oui, demander l’approbation » | `POST /commandes/{id}/envoyer` `{date}` | « Bon envoyé : il porte désormais le n° {n°}, daté du {date}. Les prix seront à confirmer au retour du fournisseur. » ou « Bon soumis à la direction : il partira à son approbation. » | « Ce bon attend l'approbation de la direction. » 409 ; « Ce bon est déjà parti. » 409 ; « La livraison prévue ({date}) est déjà passée : la corriger, ou la vider (date d'envoi + délai du fournisseur). » ; « La livraison prévue ({date}) précède l'envoi du bon ({date}) : la corriger, ou la vider (…). » ; `date_permise` : « Date trop ancienne (…) : vérifier l'année. », « Date dans le futur (…) : un mouvement se saisit le jour où il a lieu. », « La période jusqu'au {date} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir. » |
| « Approuver et envoyer » | à approuver | **direction** | grisé si envoi ; infobulle « Le bon reçoit son numéro et part chez le fournisseur » | « Approuver {montant estimé devise} chez {fournisseur} ? » · « Oui, approuver et envoyer » | `POST /commandes/{id}/approuver` | « Bon approuvé : il a reçu son numéro et est marqué comme envoyé. Les achats l’impriment et le transmettent. » | « Ce bon n'attend pas d'approbation. » 409 ; 403 pour achats ; date close |
| « Renvoyer aux achats… » | à approuver | **direction** | infobulle « Le changement n’est pas accepté : le bon revient à sa version partie, avec votre motif » (parti) / « Le bon redevient un brouillon, avec votre motif » | rangée « Motif du renvoi aux achats » (aide « les achats le liront sur le bon », placeholder « ex. couper en deux livraisons, attendre la baisse annoncée… », 460 px) · « Non » · « Oui, renvoyer aux achats » (grisé si motif < 3 car.) | `POST /commandes/{id}/renvoyer` `{motif}` | « Changement refusé : le bon reste chez le fournisseur dans sa version partie, avec votre motif. » / « Bon renvoyé aux achats : il redevient un brouillon, avec votre motif. » | « Seul un bon qui attend l'approbation se renvoie aux achats. » 409 ; « Le bon {n°} est parti, mais sa version d'alors n'est pas connue : l'approuver, ou demander aux achats de le ramener à ce qui était accepté. » 409 ; motif 3–500 car. |
| « Supprimer le bon » | sans numéro et modifiable | achats | infobulle « Un bon qui n'est pas parti se supprime : il n'a pas encore de numéro » | « Supprimer définitivement ce brouillon ? » · « Oui, supprimer » | `DELETE /commandes/{id}` | fenêtre fermée ; page : « Brouillon supprimé. » | « Ce bon a des réceptions : le solder plutôt que le supprimer. » 409 ; « Le bon {n°} est parti chez le fournisseur : l'annuler plutôt que le supprimer (il garde son numéro, la série reste sans trou). » 409 |
| « Solder (ne plus attendre le reste) » / « Annuler la commande » | parti, non clos, non à approuver | achats | infobulle « Solder le bon : on n'attend plus le reste à livrer » (si reçu > 0) / « Annuler la commande : rien n’a été reçu, le bon garde son numéro » | « On n'attend plus le reste ({kg} kg) : il sort des quantités commandées. » · « Oui, solder » / « Rien n’a été reçu : le bon sera annulé (il garde son numéro). » · « Oui, annuler la commande » | `POST /commandes/{id}/solder` | « Bon soldé. » / « Commande annulée. » | « Ce bon est déjà clos. » 409 ; « Le bon {n°} attend l'approbation de la direction : elle l'approuve ou le renvoie aux achats (il revient à sa version partie) ; il se solde ensuite. » 409 ; « Ce bon n'est pas parti : il se supprime, il ne se solde pas. » 409 |
| « Rouvrir le bon » | soldé ou annulé | achats | infobulle « Le bon attend de nouveau ce qui reste à livrer » | « Rouvrir ce bon ? Le reste redevient attendu. » · « Oui, rouvrir » | `POST /commandes/{id}/rouvrir` | « Bon rouvert : le reste est de nouveau attendu. » | « Ce bon n'est pas clos. » 409 ; rouvert au-delà de l'approuvé → repasse à approuver |
| « Fermer » | pied | | si saisie : « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Oui, abandonner » | | | | |

- **Notions** : brouillon sans numéro (M65), numéro et date donnés à l'envoi (série BC, `numero(s,"BC",jour)`), date
  d'envoi passée permise jamais future ni en période close ; « parti » se lit au numéro (`achats.py:60-65`) ; seuil
  d'approbation (réglage `seuil_approbation`, MAD, 0 = jamais) mesuré au **cours figé** (sinon du jour) sur le montant
  estimé (confirmé sinon catalogue) ; montant approuvé (`montant_approuve`) et **version partie** (lignes + montant de
  référence, `achats.py:201-243`) : hausse mesurée à la version partie, baisse jamais soumise, tolérance 5 % aux prix
  confirmés ; bon parti qui repasse « à approuver » reste chez le fournisseur ; renvoi = retour à la version partie ;
  cours figé à la première confirmation des prix ; date promise fixée à l'envoi (date saisie ou envoi + délai),
  figée avec les prix, puis seule l'ETA bouge ; ETA remplace la livraison prévue dans la projection ; solde (camion
  venu) vs annulation (jamais livré) ; solde automatique quand chaque ligne est reçue (tolérance `toler_in_full`,
  rien en quarantaine) et réouverture automatique d'un bon soldé « tout reçu » qui ne l'est plus
  (`recaler_soldes`, `achats.py:572-605`) ; un bon soldé à la main reste soldé ; reste à livrer = 0 sous la tolérance.

---

### 3. RÉCEPTIONS

#### Réceptions — `/receptions` (?onglet=brouillon|validee|annulee|reclamations|bobines|pesees, ?ouvrir=ID | ?reception=ID)

- **Fichiers** : `pages/Receptions.tsx` (294 l.), `components/achats/SaisieReception.tsx`, `DetailReception.tsx`,
  `PoidsBobines.tsx`, `ArchivePesees.tsx`, `Reclamations.tsx`, `commun.tsx`, `types.ts`.
- **Rôles** : menu + garde `['achats']`. Serveur : `GET /receptions` `ACHATS` (`receptions.py:309`), `/receptions/pesees`
  et `/receptions/bobines` `ACHATS` (`pilotage.py:404, 426`), `/reclamations` `ACHATS` (`suivi.py:66`). Aucune
  différence d'écran direction/achats.
- **Données** : `GET /receptions` (brouillons **recalés à chaque lecture** : reste à livrer, prix confirmé du bon,
  sans rien écrire — `receptions.py:84-100, 309-319`) ; `GET /receptions/pesees` (compte de l'onglet) ;
  `GET /reclamations` (compte de l'onglet).
- **Chargement** : « … chargement : les réceptions… » ; erreur : page « Réceptions » + bandeau.
- **En-tête** : titre « Réceptions » ; sous-titre « Le poste de pesée. C'est le poids pesé qui entre en stock, à la
  validation. » ; action principale « Nouvelle réception ».
- **Bandeaux de page** : succès (après enregistrement, suppression, etc.) ; erreur
  « La réception {n°} vient d'être validée ou annulée : elle ne se corrige plus. » (geste Corriger sur un brouillon qui
  a changé entre-temps).
- **Onglets** (`:134-153`) : « Brouillons » (compte), « Validées » (compte), « Annulées » (compte), « Réclamations
  ouvertes » / « Réclamations » (compte = réclamations ouvertes), « Poids des bobines » (sans compte), « Archive des
  pesées » (compte = lignes pesées). Défaut : Brouillons s'il en existe, sinon Validées. Les comptes des 3 premiers
  suivent la recherche.
- Pas d'indicateurs sur les onglets de statut.

##### Onglets « Brouillons » / « Validées » / « Annulées »
- Titre de carte (avec infobulle) :
  - Brouillons : « Pas encore entrées en stock ni numérotées : corriger, puis valider » (infobulle « Saisies, pas encore
    entrées en stock ni numérotées : ouvrez-les pour les corriger ou les valider. »)
  - Validées : « Entrées en stock : étiquettes, facture, annulation » (infobulle « Entrées en stock. Réimprimez les
    étiquettes des lots, complétez la facture, ou annulez (contre-passation). »)
  - Annulées : « Annulées : leurs entrées ont été contre-passées » (infobulle « Réceptions annulées : leurs entrées ont
    été contre-passées. »)
- Filtres : note « {n} trouvée(s), tous onglets » ; recherche placeholder « N°, fournisseur, BL, facture, bon, lot… »
  sur : n° (ou « Brouillon »), fournisseur, n° BL, n° facture, créé par, contrôlé par, observations, n° des bons,
  « réf. désignation lot » des lignes ; `BoutonExport` `/export/receptions?onglet={statut}&q=`.
- **Tableau** :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| N° | n° REC-… ou étiquette neutre « Brouillon » | mono | |
| Arrivée | date | date | |
| Fournisseur | **nom** ; note « par {créé par} · contrôlé par {nom} » | | |
| Bon(s) de commande | n° des bons séparés par « , » ou note « hors commande » | mono | |
| N° du BL | n° ou « — » | | |
| Facture | n° ; validée sans facture : note « à compléter » ; sinon « — » | | |
| Lignes | nb de lignes | num | |
| Pesé (kg) | Σ pesé hors lignes refusées | num | |
| Statut | étiquette Brouillon (attention) / Validée (ok) / Annulée (rupture) ; brouillon bloqué : note rouge « {n} point(s) à régler » (infobulle = liste des blocages) | | |
| (sans titre) | brouillon : « Corriger » ; validée : « Étiquettes » (grisé si aucun lot ; infobulle « Les étiquettes QR des lots de cette réception ») ; « Ouvrir / valider » (principal, brouillon) ou « Ouvrir » | | |

  Ligne cliquable → fiche. Vide : recherche « Aucune réception de cet onglet ne correspond (voir les autres onglets). » ;
  brouillons « Aucun brouillon en attente. Un camion arrive ? « Nouvelle réception ». » ; autres « Aucune réception ici. ».
- « Corriger » relit d'abord la liste (`refetch`) ; si le brouillon n'en est plus un : bandeau d'erreur ci-dessus ;
  sinon ferme la fiche et ouvre la saisie sur ce brouillon (`Receptions.tsx:101-112`).
- « Étiquettes » ouvre `/api/lots/etiquettes?ids={ids des lots}` dans un nouvel onglet (`DetailReception.tsx:54-57`).
- **Export** `GET /export/receptions?onglet&q` (`exports_achats.py:149-205`) : feuille « Réceptions » (N°, Arrivée,
  Fournisseur, Bons de commande, N° du BL, Facture, Date facture, Montant facture, Devise facture, Échéance, Lignes,
  Pesé (kg), Statut, Par, Contrôlé par, Validée par, Observations) ; feuille « Lignes » (N°, Arrivée, Fournisseur, Bon de
  commande, Référence, Lot, Reste à livrer (kg), Annoncé BL (kg), Pesé (kg), Écart (kg), Écart (%), Palettes, Bobines,
  kg / bobine, Magasin, Qualité, Prix / kg, Devise, Observations).
- Après enregistrement d'une saisie : onglet Brouillons, fiche ouverte, message « Réception enregistrée en brouillon.
  Relisez-la puis validez-la : la marchandise entrera en stock et la réception recevra son numéro. » ou « Le camion
  portait {n} devises : {n} réceptions enregistrées en brouillon (EUR, USD), chacune avec sa facture. Relisez-les puis
  validez-les. ».

#### Fenêtre « Nouvelle réception » / « Corriger la réception — {n° | Brouillon} » — `SaisieReception.tsx` (1074 l.)

`Dialogue tresLarge sale={modifie}`. Données : `useFournisseurs`, `useArticles`, `useCommandes` (`GET /commandes`),
`useMagasins`, `useDevises`, `useTolerances` (`GET /parametres` : `toler_ecart_pesee` 2 %, `toler_poids_bobine` 5 %,
`toler_excedent` 10 %, `types.ts:251-268`).

- **Mode d'emploi** (`details` replié/ouvert ; ouvert la toute première fois, état retenu en `localStorage`
  « gestion-mp.aide-reception ») : 6 points — taper le n° du bon (ou le fournisseur), cocher les bons du camion ;
  recopier le n° du BL et la facture (complétable après) ; ligne par ligne lot (sinon « Lot interne »), quantité
  annoncée sur le BL, quantité pesée (c'est elle qui entre en stock), palettes complètes et bobines en plus ; ligne
  absente : la retirer (×), elle reste due ; Qualité : conforme / sous réserve (quarantaine, non utilisable) / refusé
  (n'entre pas, le fournisseur la doit toujours, motif en observations) ; Enregistrer crée un brouillon, la validation
  fait entrer la marchandise et donne le numéro.
- **En-tête de saisie** (rangée) :
  - « N° du bon de commande » (aide « le chauffeur l'apporte : il choisit le fournisseur et coche le bon ») —
    `ChoixRecherche` sur les **bons ouverts** non déjà dans le camion : numérotés, statut envoyée/confirmée/à approuver,
    une ligne avec reste > 0 (`:99-102`) ; libellé « {n°} — {fournisseur} », détail « {kg} kg à livrer », placeholder
    « ou taper le n° du bon… ». Choisir un bon d'un autre fournisseur alors que des lignes sont saisies demande :
    « Le bon {n°} est de {fournisseur} : passer à ce fournisseur efface les {n} ligne(s) déjà là, dont {k} saisie(s).
    Continuer ? » · « Non » · « Oui, changer de fournisseur ».
  - « Fournisseur » (fournisseurs actifs, ou l'actuel ; détail pays ; placeholder « Taper le nom du fournisseur… »).
    Changer avec des lignes saisies : « Changer de fournisseur efface les {n} ligne(s) de la réception, dont {k} déjà
    saisie(s) (lot, pesée). Continuer ? » · « Oui, changer de fournisseur ». Avec un seul bon ouvert chez lui, ses lignes
    se chargent seules.
  - « Date d'arrivée » (date, défaut aujourd'hui, max aujourd'hui).
  - « N° du BL » (aide « bon de livraison »).
  - « Contrôlé par » (aide « au quai », ≤ 80 car.).
  - « Observations » (aide « état du camion, retard… »).
- **Facture du fournisseur** (`details`, si fournisseur choisi ; ouvert si le brouillon a une facture) : résumé
  « n° {n} · {montant} {devise} · échéance {date} » ou « facultative ici : elle se complète aussi après la
  validation ». Champs : « N° de facture » ; « Date de facture » (grisé sans n°) ; « Montant de la facture » (grisé
  sans n°) ; « Devise de la facture » (aide « elle va à la réception de cette devise » si camion multi-devises, sinon
  « celle des lignes reçues » ; grisé sans n° ou si une seule devise) ; « Échéance » (min date de facture ; aide
  « proposée : date de facture + {n} j » ou « le délai de paiement du fournisseur n’est pas réglé » ; suit date + délai
  tant qu'elle n'a pas été saisie à la main).
- **Bons dans le camion** : « Bons de commande dans ce camion » — une case par bon ouvert du fournisseur
  « {n°} · {n} ligne(s) à livrer · {x %} déjà reçu » ; bons du camion qui n'attendent plus rien : étiquette « {n°} (plus
  rien à livrer) » ; aucun bon : note « Aucun bon envoyé n'attend de livraison chez ce fournisseur : ajoutez les matières
  hors commande. » (infobulle « Un bon encore en brouillon doit d'abord être marqué comme envoyé »). Décocher un bon
  saisi : « Décocher le bon {n°} retire ses {n} ligne(s), dont {k} déjà saisie(s). Continuer ? » · « Oui, retirer ce
  bon ». Avertissement orange : « Ce camion porte deux devises ({liste}) : deux réceptions seront enregistrées, une par
  devise, chacune avec sa facture. ».
  « Ajouter une matière hors commande » (infobulle « Une livraison sans bon, un échantillon, un complément ») : toutes
  les matières **actives**, celles du fournisseur d'abord ; détail = fournisseur habituel ; placeholder « Référence,
  couleur, titrage… ». Prix proposé = catalogue si la devise du fournisseur = devise de la fiche, sinon 0 ; devise =
  celle du fournisseur.
- **Tableau des lignes** (`table saisie saisie-reception`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Référence · bon | réf. ; note « bon {n°} » ou « hors commande » | max 200 px | infobulle « réf. — désignation » |
| Lot du fournisseur (infobulle « Le n° de lot imprimé sur l'étiquette du fournisseur ; à défaut, « Lot interne » ») | saisie (placeholder « n° de lot », 130 px) ; lien « Lot interne » (infobulle « L'étiquette ne porte pas de lot : en attribuer un à nous ») qui écrit « LOT INTERNE » | | le vrai n° (LOT-AAAA-NNNN) est donné à la validation |
| Reste à livrer (kg) (infobulle « Ce que la commande attend encore : commandé moins déjà reçu (réceptions validées) ») | reste du moment (relu sur la commande) ou « — » hors commande ; note « déjà reçu {kg} » ; note rouge « excédent refusé » (infobulle « Au-delà du reste à livrer plus {10 %} de la ligne : la validation sera refusée. Recevoir le surplus sur une ligne hors commande. ») | num | règle : pesé > max(0, commandé − reçu) + commandé × excédent |
| Annoncé BL (kg) (infobulle « La quantité écrite sur le bon de livraison ») | saisie | num, 110 px | |
| Pesé (kg) (infobulle « Le poids relevé à la bascule, en kilos — le cuir, les franges et le ruban aussi (leurs mètres s'affichent dessous, à titre indicatif) : c'est lui qui entre en stock. Dessous, l'écart à l'annonce (signalé au-delà de 2 %). ») | saisie ; note mètres ; note étiquette `signe(écart relatif)` (critique au-delà de la tolérance, sinon ok) + « ±{kg} kg » (infobulle « Pesé moins annoncé BL (à défaut, moins le reste à livrer) ») | num | attendu = BL, sinon reste à livrer **seulement** si pesé ≥ reste × (1 − tolérance) |
| Palettes (infobulle « Palettes complètes ; le catalogue sait combien de bobines porte une palette ») | saisie + note « × {n} bob. » ; sans bobines/palette au catalogue : « — » (infobulle « Le catalogue ne dit pas combien de bobines porte une palette : comptez tout en « bobines en plus » ») | num | |
| Bobines en plus · kg / bobine (infobulle « Bobines comptées en plus des palettes complètes (ou toutes, sans palette). Dessous : le total, et le poids d'une bobine (pesé ÷ bobines) face au catalogue. ») | saisie ; note « = {n} bobines » ; étiquette « {kg} kg » (attention si écart au catalogue > 5 %) + `signe` (infobulle « catalogue : {x} kg la bobine » / « pas de poids de bobine au catalogue ») ; ou note « catalogue {x} kg » | num | bobines = palettes × bobines/palette + en plus |
| Prix / kg (infobulle « Le prix payé au kilo (un prix au mètre ramené au kilo par la densité) : celui du bon s'il est confirmé (non modifiable), sinon à saisir — proposé au prix du catalogue ») | bon confirmé : « {prix} » + note « {devise} · confirmé » (infobulle « Le prix confirmé sur le bon : c'est lui qui sera payé ») ; sinon saisie (placeholder « prix ») + note « {devise} / kg » (commande) ou liste des devises actives + « / kg » (hors commande, infobulle « La devise du prix payé (hors commande) ») | num | |
| Magasin (infobulle « Où la marchandise est rangée. Une ligne sous réserve va d'office en quarantaine ; une ligne refusée n'entre pas. ») | liste « — choisir — » + magasins actifs hors type Quarantaine ; réserve : note = code du magasin de quarantaine (ou « quarantaine ») ; refusé : note « n'entre pas » | | défaut = 1er magasin de rangement actif |
| Qualité (infobulle « Conforme · Sous réserve (entre en quarantaine, non utilisable) · Refusé (n'entre pas en stock, le fournisseur la doit toujours) ») | liste Conforme / Sous réserve / Refusé | | |
| Observations (infobulle « À renseigner en cas de réserve ou de refus : le motif, ce qu'on a constaté ») | saisie (placeholder « motif… » hors conforme) | 120 px | |
| (sans titre) | bouton « × » (infobulle « Retirer cette ligne (absente du camion) ») | | ligne saisie : « Retirer « {réf} » (lot {n}) déjà saisie ? Elle reste due sur le bon. » · « Oui, retirer la ligne » |

  Vide : « Cochez un bon de commande ci-dessus, ou ajoutez une matière hors commande. ». Pied : « {n} ligne(s) » ·
  Σ annoncé BL · Σ pesé (hors refusées) · message rouge « {n} écart(s) de pesée au-delà de 2 % : vérifiez la bascule
  et le BL, notez-le en observation. ».
- **Pied de fenêtre** : note « Brouillon saisi par {nom}, arrivée du {date}. Enregistrer ne fait rien entrer en stock :
  la validation viendra ensuite. » ; « Annuler » (si saisie : « Abandonner la saisie ? » · « Oui, abandonner ») ;
  bouton principal « Enregistrer le brouillon » / « Enregistrer les corrections » (grisé sans fournisseur, sans ligne
  ou pendant l'envoi).
- **Geste Enregistrer** (`:415-479`) : contrôles écran « Choisissez d’abord le fournisseur, ou tapez le n° du bon. »,
  « Ajoutez au moins une ligne : cochez un bon de commande, ou ajoutez une matière hors commande. », « Une réception ne
  se date pas dans le futur. ». Les lignes sont groupées **par devise** ; une requête par devise, l'une après l'autre :
  correction → `PUT /receptions/{id}` pour la devise du brouillon puis `POST /receptions` pour les autres ; nouvelle →
  `POST` pour chacune. Corps : `{date, fournisseur_id, numero_bl, controle_par, facture (seulement sur la réception de
  la devise de la facture et si n° saisi), observations, lignes:[{commande_ligne_id, article_id, lot_numero,
  quantite_bl, quantite_pesee, nb_palettes, bobines_en_plus, magasin_id, qualite, observations, prix (null si bon
  confirmé ou vide → catalogue), devise ('' sur un bon)}]}`. Les réceptions renvoyées sont rangées dans le cache puis
  tout est rafraîchi.
  Refus serveur (`receptions.py:361-494`) : « Fournisseur inconnu. » ; « Une réception ne se date pas dans le futur. » ;
  « Matière inconnue dans la réception. » ; « Qualité : conforme, réserve ou refusé. » ; « Magasin inconnu. » ;
  « Ligne de commande inconnue. » ; « La commande {n°} n'est pas de {fournisseur} : une réception ne mêle pas deux
  fournisseurs. » ; « « {réf} » n'est pas sur la ligne choisie de {n°}. » ; problèmes du bon (`probleme_du_bon`) :
  « Le brouillon n° {id} n'est pas encore parti chez le fournisseur : le marquer comme envoyé (il reçoit son numéro), ou
  recevoir hors commande. », « Le bon {n°} est annulé : le rouvrir, ou recevoir hors commande. », « La réception du
  {date} précède l'envoi du bon {n°} ({date}) : la date de l'une ou de l'autre est fausse. » ; « Le bon {n°} est en
  {devise} : sa réception aussi. » ; « Devise inconnue : {code}. » ; « Une réception ne mêle pas deux devises (…) :
  chaque devise a sa facture. Enregistrer une réception par devise (même BL, même date). » ; facture : « Cette réception
  est en {devise} : sa facture aussi. Une facture en {autre} va sur la réception de cette devise. », « La facture {n°}
  est en {devise} ; cette réception est en {devise}. Une facture n'a qu'une devise : saisir la facture de cette
  devise. » ; correction d'une validée : « Une réception validée est entrée en stock : elle ne se modifie plus.
  L'annuler (elle se contre-passe), puis en saisir une nouvelle. » (409).
  Règles : un prix confirmé du bon l'emporte toujours ; hors commande, prix dans la devise du fournisseur, catalogue
  converti au cours du jour ; la facture (fournisseur + n°) est retrouvée ou créée, échéance = date + délai de paiement
  si non saisie.

#### Fiche « Réception — {n° | Brouillon} » — `DetailReception.tsx` (771 l.)

`Dialogue tresLarge sale={facture en saisie}`. **Se relit seule toutes les 30 s** (`useReceptions(true)`,
`:45-52`) ; le serveur recale le brouillon à chaque lecture. Réception disparue : « Chargement… » puis « Cette
réception n'existe plus. ».

- **Données** : `GET /receptions`, `useDevises`, `useTolerances`, `GET /reclamations`, `GET /pieces/reception/{id}`.
- **En-tête** : **fournisseur** ; note « arrivée du {date} · BL {n° | —} · bon(s) » + liens mono vers chaque bon
  (`/commandes?ouvrir={id}`, infobulle « Ouvrir le bon de commande ») ou « · hors commande » ; étiquette de statut.
  Ligne « Saisie par {nom} le {horodatage} · contrôlée au quai par {nom} · validée par {nom} le {horodatage} ».
- **Indicateurs** :

| Indicateur | Valeur | Détail / infobulle | Teinte |
|---|---|---|---|
| Pesé (entre en stock) | « {Σ pesé hors refus} kg » | « {n} ligne(s) » (lignes non refusées) | |
| Écarts de pesée | nb de lignes dont |écart relatif| > tolérance | « au-delà de 2 % de l'annonce » | critique sinon ok |
| Sous réserve / refusé | « {réserve} / {refus} » | « quarantaine / n'entre pas » | attention si l'un > 0 |
| Facture | n° ou « — » | « {montant} {devise} · réglée le {date} » / « · échéance {date} (dans N j) » / « · échéance {date}, dépassée de N j » / « · échéance aujourd'hui » / « · échéance non fixée » ; « montant non saisi » ; sans facture « pas encore reçue » ; infobulle « Échéance de paiement : {date} » | attention si validée sans facture ; ok si réglée ; critique si échéance dépassée |

- **Bandeaux** :
  - brouillon : « Brouillon : rien n'est encore entré en stock, pas encore de numéro. Il se remet à jour tout seul (reste
    à livrer, prix confirmés) si d'autres réceptions passent avant lui. »
  - blocages (rouge) : « **Avant de valider :** » + liste résumée (`resumerBlocages` : plus de 2 lignes sans pesée →
    « {n} lignes sans pesée : la saisir, ou marquer la ligne « refusé ». » ; plus de 2 sans lot → « {n} lignes sans
    numéro de lot (celui de l'étiquette, ou « Lot interne »). ») + « Le détail, ligne par ligne ({n}) » dépliable.
  - avertissements (info) : « **À savoir avant de valider :** » + liste.
  - annulée : « Réception annulée par {nom} le {horodatage} — motif : {motif}. Ses entrées en stock ont été
    contre-passées ; les bons concernés attendent de nouveau leur marchandise. » (motif omis si « sans motif »).
  - juste validée : « Réception validée sous le n° {n°} : {n} lot(s) créé(s) ou complété(s), la marchandise est en
    stock. » + lien « Imprimer les étiquettes QR à coller sur les palettes ».
- **Blocages serveur** (`receptions.py:122-179`, mêmes textes à l'écran et au refus de validation) : date
  (`date_permise`) ; problèmes du bon ; excédent « « {réf} » : {kg} kg reçus (tous lots ensemble) pour {kg} kg restant
  à livrer sur {n°} (excédent toléré : 10 % de la ligne). Recevoir le surplus sur une ligne hors commande, ou faire
  corriger le bon. » ; inventaire « L'inventaire {n°} est en cours : les entrées y sont suspendues jusqu'à sa
  validation. » ; « « {réf} » : la pesée est à zéro. La saisir, ou marquer la ligne « refusé ». » ; « « {réf} » : le
  numéro de lot manque (celui de l'étiquette, ou « Lot interne »). » ; « Une ligne sous réserve va en quarantaine :
  créer d'abord un magasin de type « Quarantaine » (Réglages › Magasins). » ; « « {réf} » : choisir le magasin de
  rangement. ». Les lignes refusées ne sont pas contrôlées (ni lot, ni pesée, ni magasin).
- **Avertissements serveur** (`receptions.py:182-198`) : « Le bon {n°} est soldé : il n'attend plus rien. Le rouvrir si
  le fournisseur le complète vraiment, sinon recevoir hors commande. » ; « Le bon {n°} est parti, mais une modification
  attend l'approbation de la direction : la réception s'impute à ses lignes d'aujourd'hui. Si elle la refuse, le bon
  revient à sa version partie. ».
- **Panneau « Facture du fournisseur »** (carte dans la fenêtre, ouvert par « Compléter / Corriger la facture ») :
  « N° de facture » (aide « vide : détache la facture » ; en dossier : grisé, aide « dans le dossier {n°} : pour le
  changer, l’en détacher d’abord (dossier › Marchandises) ») ; « Date de facture » (max aujourd'hui) ; « Montant » ;
  « Devise » (devises actives) ; « Échéance » (min date ; aide « proposée : date + {n} j » / « délai de paiement non
  réglé »). Note « La facture ne touche pas au stock : elle se complète ou se corrige même après la validation. » ;
  « Annuler » ; « Enregistrer la facture ». `PUT /receptions/{id}/facture`. Succès « Facture {n°} enregistrée. » ou
  « Facture détachée de la réception. ». Refus (`receptions.py:614-662`) : « Cette réception est annulée : sa facture
  ne se modifie plus. » ; « La date, le montant et l'échéance de la facture {n°} se corrigent ici ; son numéro, non.
  Cette réception est dans le dossier d'importation {n°} : pour changer le numéro, [le rouvrir (c'est tracé), puis]
  l'en détacher d'abord (dossier {n°} › Marchandises › « Détacher la réception ») — ses frais restent au dossier, et la
  marchandise y reviendra par sa facture. » ; « L'échéance ne précède pas la date de la facture. » ; « Cette réception
  est en {d} : sa facture aussi. … » ; « Devise inconnue : {d}. » ; « La facture {n°} est en {d} et porte d'autres
  réceptions : elle ne change pas de devise. ».
- **Volets** : « Lignes pesées » (compte), « Pièces jointes » (compte), « Réclamations » (compte des réclamations de
  ce camion). État local.
- **Volet « Lignes pesées »** :

| Colonne | Contenu | Remarque |
|---|---|---|
| Référence · bon | réf. ; note lien « bon {n°} » → `/commandes?ouvrir={id}` ou « hors commande » | |
| Lot | lien vers `/lot/{id}` (infobulle « La fiche du lot : où il est, où il est allé ») ; brouillon « LOT INTERNE » → note « lot interne » (infobulle « Un lot à nous sera donné à la validation ») ; vide → étiquette « à saisir » (« — » si refusé) | mono |
| Reste à livrer (kg) (brouillon, infobulle « Ce que la commande attend encore ») / Reste après (kg) (validée/annulée, infobulle « Ce qui reste à livrer sur le bon après cette réception ») | `quantite_attendue` ou `reste_apres` ; note « déjà reçu {kg} » | « — » hors commande |
| Annoncé BL (kg) | BL ou « — » | |
| Pesé (kg) | pesé ; note mètres | |
| Écart | étiquette `signe` (critique au-delà de la tolérance) + « ±{kg} kg » | « — » sans attendu |
| Bobines | total ou « — » ; note « {p} pal. + {n} » | |
| kg / bobine | étiquette poids moyen (attention si > 5 % du catalogue) ; note « catalogue {x} ({±%}) » | |
| Magasin | « n’entre pas » (refusé) / « quarantaine » (réserve en brouillon) / code / étiquette « à choisir » | |
| Qualité | étiquette Conforme ok / Sous réserve attention / Refusé critique ; note observations | |
| Prix / kg (infobulle « Le prix payé : celui du bon confirmé, sinon celui saisi (ou du catalogue) ») | prix (3 déc.) ; note « {devise} · du bon » | |

  Sous le tableau : « Observations : {texte} ».
- **Volet « Réclamations »** : N° · Ouverte le · Lot · référence (« toute la réception » sans lot) · Motif · Quantité
  (kg) · Issue (étiquette ok « {issue} » si close, attention « ouverte ») ; ligne cliquable → fiche réclamation. Vide :
  « Aucune réclamation sur cette réception. ».
- **Volet « Pièces jointes »** : `PiecesJointes objet="reception"`.
- **Gestes** :

| Geste | Où | Conditions / grisé | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|---|
| « Corriger » (infobulle « Rouvre la saisie de ce brouillon ») | brouillon | — | — | relecture puis saisie | | « La réception {n°} vient d'être validée ou annulée : elle ne se corrige plus. » |
| « Supprimer le brouillon » (infobulle « Rien n'est entré en stock : le brouillon s'efface ») | brouillon | grisé pendant l'envoi | « Supprimer ce brouillon ? » · « Oui, supprimer » | `DELETE /receptions/{id}` | fenêtre fermée ; page « Brouillon supprimé. » | « Une réception validée ne se supprime pas : l'annuler. » 409 |
| « Valider la réception » | brouillon, principal | grisé s'il y a des blocages (infobulle « Avant de valider : {1er blocage} ») ; sinon infobulle « Écrit les lots, les entrées en stock et les prix payés ; la réception reçoit son numéro » | « {résumé} Ensuite, elle ne se modifie plus. » où résumé = « {n} ligne(s) en stock disponible, {q} en quarantaine, {r} refusée(s) — {kg} kg. {e} écart(s) de pesée hors tolérance. » ou « Toutes les lignes sont refusées : rien n’entre en stock, la réception reste la trace du refus. » · « Oui, valider » | `POST /receptions/{id}/valider` | bandeau « Réception validée sous le n° … » | « Cette réception est déjà validée. » 409 ; date ; 1er blocage |
| « Imprimer les étiquettes des lots » | validée, principal | grisé sans lot (sans infobulle) | — | onglet `/api/lots/etiquettes?ids=` | | |
| « Compléter la facture » / « Corriger la facture » (infobulle « La facture se complète ou se corrige sans toucher au stock ») | validée, panneau fermé | | | ouvre le panneau | | |
| « Marquer réglée » (infobulle « La facture est payée : elle sort de l'échéancier et de l'« échu, non réglé » ») | validée avec facture non réglée | | « Réglée le [date, défaut aujourd'hui, max aujourd'hui] » · « Oui, réglée » | `PUT /echeancier/paiement` `{objet:'facture', id, payee_le}` (`suivi.py:412`, `ACHATS`) | « Facture {n°} réglée le {date}. » | « Un règlement ne se date pas dans le futur : c'est un fait constaté. » ; « Le règlement ({date}) précède la pièce qu'il règle ({date}). » ; « Pièce introuvable. » |
| « Annuler le règlement » (infobulle « La facture redevient due : elle revient dans l'échéancier ») | facture réglée | | « Annuler le règlement ? » · « Oui, annuler le règlement » | idem `payee_le:null` | « Règlement de la facture {n°} annulé. » | |
| « Réclamer au fournisseur » (infobulle « Un défaut constaté (qualité, manque, bobines, retard) : ouvrir une réclamation, lot et quantité préremplis ») | validée | | | ouvre *Réclamer au fournisseur* | volet Réclamations + fiche ouverte | |
| « Annuler (contre-passation) » | validée, danger | grisé si dans un dossier (infobulle « Elle est dans le dossier d’importation {n°} : [le rouvrir, puis ]l’en détacher d’abord (dossier › Marchandises › « Détacher la réception ») — ses frais restent au dossier ») ; sinon infobulle « Chaque entrée est contre-passée par un mouvement inverse, à la même date ; tout reste tracé » | « Annuler ? Les entrées seront contre-passées. Motif : [placeholder « ex. saisie en double »] » · « Oui, annuler (contre-passation) » | `POST /receptions/{id}/annuler` `{motif}` | aucun message ; la fiche passe en « Annulée » | « Seule une réception validée s'annule ; un brouillon se supprime. » 409 ; message dossier (409) ; refus de `contrepasser_document` (matière plus là) |
| « Fermer » | pied | si facture en saisie : « La facture saisie n'est pas enregistrée. L'abandonner ? » · « Oui, abandonner » | | | | |

- **Validation serveur** (`receptions.py:510-574`) : verrouille les bons touchés (deux postes ne franchissent pas
  l'excédent ensemble), recale, contrôle les blocages ; réserve → magasin de quarantaine ; « LOT INTERNE » → n°
  `LOT-AAAA-NNNN` (compteur rattrapant les lots repris) ; numéro REC donné à la validation ; pour chaque ligne non
  refusée : lot créé ou complété (poids moyen de bobine), mouvement RECEPTION au prix payé et au cours figé du bon si même
  devise (commentaire « sous réserve ») ; solde automatique des bons livrés ; journal « validation réception » (« tout
  refusé, rien n'entre en stock »).
- **Notions** : pesée qui fait foi, Annoncé BL, écart de pesée (tolérance `toler_ecart_pesee`), excédent toléré
  (`toler_excedent`), quarantaine (sous réserve), refus (n'entre pas, reste dû), lot interne, réception multi-devises,
  facture complétée après validation, échéance (délai de paiement), règlement, contre-passation, dossier d'importation
  bloquant l'annulation, recalage du brouillon.

#### Onglet « Réclamations » — `Reclamations.tsx` (`?onglet=reclamations`)

- **Indicateurs** : « Ouvertes » (teinte attention sinon ok ; détail « dont {n} depuis plus de 30 jours » ou « en
  attente du fournisseur ») ; « Closes » (détail « réponse obtenue ou abandon ») ; « Délai de réponse » (moyenne des
  `jours` des closes, « {n} j » ; détail « en moyenne, des closes ») ; « Obtenu » (`montants` par devise des montants
  obtenus des closes ; détail « avoirs et remises, par devise »).
- **Carte** : titre = **Bascule** « Ouvertes ({n}) » · « Closes ({n}) » · « Toutes » (défaut Ouvertes, non écrite dans
  l'adresse) ; recherche placeholder « Fournisseur, lot, motif, n°… » (n°, fournisseur, réception, lot, référence,
  motif, description, issue, réponse) ; bouton principal « Nouvelle réclamation » (infobulle « Une réclamation sans
  réception : un retard, une facture fausse… »).
- **Tableau** : N° (mono, RCL-…) · Ouverte le · Fournisseur · Réception · lot (n° réception ou note « sans
  réception » ; note « lot {n} · {réf} ») · Motif (+ note description tronquée à 80 car.) · Quantité (kg) · Demandé ·
  Obtenu · Issue (close : étiquette issue, neutre si « Refusée »/« Abandonnée », sinon ok ; ouverte : étiquette
  attention « ouverte ») · Durée (infobulle « Depuis l'ouverture (jusqu'à la clôture pour une close) » ; « {n} j »,
  étiquette critique si ouverte depuis > 30 j). Ligne cliquable → fiche. Vide : « Aucune réclamation ne correspond. » ou
  « Aucune réclamation. Un défaut à la réception ? Ouvrez la réception, puis « Réclamer au fournisseur ». ».
- Chargement « … chargement : les réclamations… » ; erreur : bandeau.
- Motifs (serveur `suivi.py:44-46`) : « Qualité (défaut du fil) », « Quantité manquante », « Poids des bobines »,
  « Bobines endommagées », « Retard de livraison », « Documents (facture, BL, certificat) », « Autre ». Issues :
  « Avoir », « Remplacement », « Remise sur la prochaine commande », « Refusée », « Abandonnée ».

#### Fenêtre « Nouvelle réclamation » / « Réclamer au fournisseur — {fournisseur} » — `NouvelleReclamation`

`Dialogue large sale`. Note : « Réception {n°} du {date} · BL {n°}. La réclamation reçoit son numéro tout de suite ;
joignez ensuite les photos et les documents. ».
- Champs : depuis une réception « Ligne en cause » (« — toute la réception — » + « {réf} · lot {n} · {qualité} » ;
  défaut = 1re ligne non conforme sinon 1re ; changer de ligne recopie quantité pesée, devise, observations) ; sans
  réception « Fournisseur » (actifs ; choisir pose sa devise) ; « Motif » (liste ; défaut « Qualité (défaut du fil) » si
  la ligne par défaut est non conforme, sinon 1er motif) ; « Ouverte le » (date, max aujourd'hui) ; « Quantité en cause
  (kg) » (aide « pesé : {kg} kg ») ; « Montant demandé » (aide « avoir ou remise attendue ; vide si on demande un
  remplacement ») ; « Devise » ; « Ce qui a été constaté » (textarea ≤ 4000, placeholder « ex. 12 bobines tachées
  d'huile sur la palette 4, photos jointes »).
- Gestes : « Annuler » (si saisie « Abandonner la réclamation ? » · « Oui, abandonner ») ; « Ouvrir la réclamation »
  (grisé sans fournisseur ou motif) → `POST /reclamations` `{fournisseur_id, reception_id, lot_id, motif, description,
  quantite, montant_demande, devise, ouverte_le}` (`suivi.py:85-136`, `ACHATS`). Contrôles écran « Choisissez le
  fournisseur. », « Choisissez le motif. ». Refus : « Fournisseur inconnu. » ; « Réception inconnue. » ; « La réception
  {n°} est de {f}, pas de {f}. » ; « On réclame sur ce que le fournisseur a livré : cette réception n'est pas encore
  validée. / est annulée. » ; « Lot inconnu. » ; « Le lot {n} n'a pas été livré par {f}. » ; « Le lot {n} n'est pas dans
  la réception {n°}. » ; « {q} réclamés pour {l} livrés par la réception {n°}. » ; « Devise inconnue : {d}. » ; « Une
  réclamation ne s'ouvre pas dans le futur. » ; « Une réclamation ne précède pas la réception qu'elle vise ({date}). ».
  Succès : fiche de la réclamation ouverte (numéro RCL donné à l'ouverture).

#### Fenêtre « Réclamation {n°} — {fournisseur} » — `DetailReclamation`

`Dialogue large sale={réponse en saisie}`. Titre + étiquette « close : {issue} » (ok) ou « ouverte » (attention).
Disparue : « Cette réclamation n'existe plus. ».
- Indicateurs : « Motif » (détail « ouverte le {date} par {nom} ») ; « En cause » (« {kg} kg » ; détail lien
  « réception {n°} · lot {n} » → `/receptions?ouvrir={id}` ou « sans réception ») ; « Demandé / obtenu » (montant
  demandé ; détail « obtenu {montant} » ou « rien obtenu pour l’instant ») ; « Durée » (« {n} j » ; détail « close le
  {date} » / « depuis l’ouverture » ; critique si ouverte > 30 j). Bandeau « Constaté : {description} ».
- Volets : « Réponse du fournisseur » (formulaire : « Issue » « — pas encore — » + issues, aide « obligatoire pour
  clore » ; « Montant obtenu ({devise}) » aide « avoir, remise » ; « Réponse du fournisseur » textarea ≤ 4000,
  placeholder « ce qu'il a répondu, ce qui est convenu (avoir n°, remplacement par le prochain conteneur…) ») ;
  « Pièces jointes » (compte).
- Gestes (`PUT /reclamations/{id}` `{reponse, issue, montant_obtenu, clore, rouvrir}`, `ACHATS`) : « Enregistrer la
  réponse » (grisé sans saisie) → « Réponse enregistrée. » ; « Clore la réclamation » (principal ; grisé sans issue,
  infobulle « Choisissez d’abord l’issue » / « La réclamation est terminée » ; « Clore avec l’issue « {issue} » ? » ·
  « Oui, clore ») → « Réclamation close : {issue}. » ; « Rouvrir » (close ; infobulle « La réclamation redevient
  ouverte : on attend de nouveau le fournisseur » ; « Rouvrir cette réclamation ? » · « Oui, rouvrir ») → « Réclamation
  rouverte. » ; « Fermer » (si saisie « La réponse n'est pas enregistrée. L'abandonner ? » · « Oui, abandonner »).
  Refus : « Réclamation introuvable. » 404 ; « Issue : Avoir, Remplacement, … » ; « Cette réclamation est close : elle
  garde son issue. La rouvrir pour la reprendre. » ; « Pour clore, dire comment elle s'est terminée (avoir,
  remplacement, refusée…). ». Clore pose `close_le` = aujourd'hui.

#### Onglet « Poids des bobines » — `PoidsBobines.tsx` (`?onglet=bobines`)

- Données `GET /receptions/bobines` (`tolerance` = `toler_poids_bobine`, lignes par matière, `hors_tolerance`).
  Chargement « … chargement : le poids des bobines… ».
- Indicateurs : « Matières suivies » (détail « bobines pesées et comptées ») ; « Hors catalogue » (attention sinon ok ;
  détail « dernière pesée à ±5 % et plus ») ; « Bobines qui s'alourdissent » (nb avec ≥ 2 réceptions et évolution >
  tolérance ; détail « hausse de plus de 5 % depuis la 1re réception ») ; « Bobines qui s'allègent » (idem baisse).
- Carte « Par matière » (infobulle « Poids pesé ÷ bobines comptées, à chaque réception validée. Un clic sur une ligne
  montre sa courbe. ») ; recherche « Référence, fournisseur… » ; case « écarts seulement » (hors tolérance au
  catalogue) ; `BoutonExport` `/export/receptions/bobines?q&ecarts`.
- Tableau : Référence · Fournisseur · Catalogue kg / bobine (infobulle « Le poids d'une bobine inscrit au catalogue » ;
  « — ») · Premier · Dernier (gras + note « le {date} ») · Évolution (infobulle « De la première à la dernière
  réception » ; « — » si 1 réception ; étiquette neutre < 0,5 %, attention > tolérance, sinon ok) · vs catalogue
  (infobulle « La dernière réception comparée au catalogue » ; étiquette critique si hors tolérance sinon ok) · Mini –
  maxi · Réceptions · bouton « Courbe » (infobulle « La courbe du poids et chaque réception »). Ligne cliquable →
  courbe. Vide : « Aucune matière ne correspond. » ou « Dès qu'une réception validée porte un nombre de bobines, le poids
  moyen de la bobine s'inscrit ici et se suit dans le temps. ».
- **Fenêtre « Poids de la bobine — {réf} »** (`Dialogue large`) : indicateurs « Catalogue » (« {x} kg » ; « poids
  inscrit au catalogue »), « Dernière réception » (« {x} kg » ; « {±%} du catalogue · {date} » ; attention si hors
  tolérance), « Évolution » (« de {a} à {b} kg »), « Moyenne » (« {n} réception(s) · {mini}–{maxi} ») ; courbe (axe du
  temps réel, ligne pointillée « catalogue », infobulle « Réception du {date} » / « {x} kg » « kg / bobine ») ; tableau
  Date · Réception · Fournisseur · Lot · Pesé (kg) · Bobines · kg / bobine · vs catalogue (plus récent d'abord) ; vide
  « Aucune mesure. ».
- Export (`exports_achats.py:274-318`) : feuilles « Par matière » et « Mesures ».

#### Onglet « Archive des pesées » — `ArchivePesees.tsx` (`?onglet=pesees`)

- Données `GET /receptions/pesees` (tolérances pesée et bobine, lignes, `hors_tolerance`, `non_conformes`) et
  `GET /receptions` (pour retrouver le bon de chaque ligne). Chargement « … chargement : l'archive des pesées… ».
- Indicateurs : « Lignes pesées » (détail « {kg} kg pesés ») ; « Écarts de pesée » (attention/ok ; « au-delà de ±2 % de
  l'annonce ») ; « Lignes non conformes » (« sous réserve ou refusées ») ; « Bobines hors catalogue » (« kg / bobine à
  ±5 % et plus »).
- Carte : titre « {n} ligne(s) · {kg} kg pesés » (infobulle « Chaque ligne reçue, lot par lot : {kg} kg pesés pour {kg}
  kg annoncés ») ; recherche « Référence, lot, fournisseur, réception, bon… » ; case « écarts seulement » (infobulle
  « Écart de pesée, de poids de bobine, ou ligne non conforme ») ; `BoutonExport` `/export/receptions/pesees?q&ecarts`.
- Tableau : Réception (n° ou étiquette « Brouillon » ; note date + statut si non validée) · Référence (note « bon
  {n°} » ou « hors commande ») · Lot · Magasin · Fournisseur · Annoncé BL (kg) (infobulle « Le bon de livraison ; à
  défaut, ce que la commande attendait ») · Pesé (kg) · Écart (étiquette critique/ok + note « ±{kg} kg ») · Bobines
  (note « {p} pal. ») · kg / bobine (infobulle « Poids pesé ÷ bobines comptées, face au poids du catalogue » ; étiquette
  attention/ok + note « cat. {x} ({±%}) ») · Qualité (étiquette Conforme ok, Refusé critique, autre attention + note
  observations). Non cliquable. Vide : « Aucune pesée ne correspond. » ou « Chaque pesée saisie viendra s’inscrire ici,
  avec son lot et son écart. ».
- Export (`exports_achats.py:227-271`) : feuille « Pesées » (Réception, Arrivée, Statut, Bon de commande, Fournisseur,
  Référence, Désignation, Lot, Magasin, Annoncé BL (kg), Pesé (kg), Écart (kg), Écart, Hors tolérance, Palettes,
  Bobines, kg / bobine, kg / bobine au catalogue, Écart bobine, Qualité, Observations) + ligne « Tolérance de pesée ±2 %
  · tolérance de bobine ±5 % ».

---

### 4. LE BON DE COMMANDE FOURNISSEUR (documents)

#### Bon de commande imprimable (HTML A4, en anglais) — `GET /api/commandes/{id}/impression`

- **Où est le bouton** : fiche d'un bon (`components/achats/DetailCommande.tsx:957-962`), pied de fenêtre, premier
  bouton « Imprimer le bon » (infobulle « Ouvre le bon prêt à imprimer ou à enregistrer en PDF »), visible **à tous les
  statuts** (brouillon compris). Il ouvre un nouvel onglet (`ouvrir()` de `lib/api.ts:79-81`, `window.open(… '_blank',
  'noopener')`). Aucun autre écran ne l'imprime.
- **Route** : `gestion_mp/api/achats.py:1035-1147`, `response_class=HTMLResponse`, droit `ACHATS`. 404 « Commande
  introuvable. ». C'est la route qu'utilise l'écran (et non `exporter_bon_de_commande`, voir plus bas).
- **Format** : page HTML autonome `lang=en`, `@page{size:A4;margin:12mm 13mm 16mm}` ; à l'écran une feuille A4 simulée
  (210 × 297 mm, ombre) sur fond gris, barre noire collante en haut avec le bouton « Imprimer / enregistrer en PDF
  (A4) » (`onclick=print()`), masquée à l'impression ; police Arial 10 pt ; `<title>` = « BC-2026-0012 » ou
  « brouillon n° 7 » (en français). Écran étroit (< 820 px) : feuille en largeur libre.
  **Aucun prix ni montant** (décision de Mohamed, `achats.py:1037-1041`, `lignes_du_bon` `achats.py:956-969`).
- **Avertissement écran seulement** (non imprimé, en français) si la raison sociale manque : « La raison sociale de
  l'usine n'est pas réglée (Réglages › Paramètres › Société) : elle manque en tête du bon. ».
- **Origine des données** : réglages de la famille « Société » (`gestion_mp/parametres.py:119-137`, lus par
  `reglages.valeurs(s)`, modifiables par la direction via `PUT /parametres`, écran Réglages › Paramètres) ; la fiche
  fournisseur (nom, pays, contact, téléphone, e-mail, incoterm) ; le bon et ses lignes ; la fiche matière (référence,
  désignation, densité `kg_par_ml`).

| Réglage (`cle`) | Libellé du réglage | Usage sur le bon |
|---|---|---|
| `nom_entreprise` | Raison sociale | 1re ligne de l'en-tête (rouge), « Deliver to », signature « For … » |
| `forme_juridique` | Forme juridique et capital (aide « SOCIETE ANONYME AU CAPITAL DE 20 000 000 DH ») | 2e ligne de l'en-tête |
| `adresse` | Siège social | en-tête « SIEGE SOCIAL  {adresse} » et adresse « Deliver to » |
| `ville` | Ville | en-tête et « Deliver to » |
| `telephone` | Téléphone | en-tête (si réglé) |
| `banques` | Banques (aide « ATTWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 001 82 », séparées par « · ») | pied « BANQUES » |
| `ice`, `rc`, `identifiant_fiscal`, `cnss`, `patente` | ICE, R.C, N.I.F (identifiant fiscal), C.N.S.S, Patente | pied : « ICE : … R.C : … N.I.F : … C.N.S.S : … PATENTE : … » (`IDENTIFIANTS_LEGAUX`, `achats.py:995-996`) |
| `secteur` | Secteur | **non utilisé** par ce bon |

- **Blocs, dans l'ordre (libellés exacts)** :
  1. **En-tête du papier de l'usine** (`en_tete_societe`, `achats.py:972-984`), centré, Times New Roman, filet fin
     dessous : raison sociale en **rouge #d40000, 19 pt, première lettre agrandie à 28 pt** (`::first-letter`) ; puis
     lignes 10 pt : forme juridique et capital ; « SIEGE SOCIAL » + espace + adresse ; ville ; téléphone. Lignes vides
     omises ; texte échappé.
  2. **Titre** (filet bleu #1f5fa8 dessous) : petit mot capitales bleu « Purchase order », numéro 17 pt gras = n° du bon
     ou « Draft — not sent » ; à droite une liste « Date » = « 08 Oct 2026 » (`date_en` : jj Mmm aaaa, mois anglais
     abrégés) ou « on sending » pour un bon sans numéro ; « Expected delivery » = date prévue ou « to be agreed ».
  3. **Deux cadres** : « Supplier » (nom gras 11 pt ; pays ; contact ; téléphone ; e-mail) et « Deliver to » (raison
     sociale ou « — » ; adresse ; ville ; « Expected date {date} » ; « Incoterm {incoterm} » si la fiche fournisseur en a
     un). Titres de cadre en petites capitales grises.
  4. **Tableau** (en-tête répété à chaque page, ligne insécable) : « No. » (rang 1, 2, …) · « Item » (référence en gras +
     désignation grise) · « Packing » (`conditionnement_en` : « By weight » pour kg/ml ; sinon nom traduit — palette →
     « Pallet », fût/fut → « Drum », bobine → « Bobbin », cône/cone → « Cone », sac → « Bag », rouleau → « Roll »,
     carton → « Carton », balle → « Bale », caisse → « Case », bidon → « Can », nom inconnu tel quel — suivi de « of
     {contenance} kg » si contenance ≠ 1) · « Qty » (nombre d'unités, format anglais « 1,234.5 », jusqu'à 3 déc. ; « — »
     au poids) · « Total weight » (« {kg} kg » en gras ; dessous « ≈ {m} m » pour un cuir, des franges, un ruban).
     Pied : « Total ordered » · « {Σ kg} kg ».
  5. **Remarques** (si `observations` non vides) : encadré gris « Remarks » + texte tel quel (retours à la ligne gardés).
     C'est la case « Remarques au fournisseur » de la préparation / de la fiche (même champ `observations`).
  6. **Phrase de confirmation** : « Please confirm this order by return — quantities and delivery date — and quote its
     number on your delivery note and on your invoice. »
  7. **Signatures** (2 colonnes, filet + 24 mm) : « For {raison sociale | the buyer} / Purchasing manager » et « Accepted
     by the supplier / Stamp and signature ».
  8. **Pied du papier** (Times New Roman 8,5 pt, filet au-dessus ; fixé en bas de chaque page imprimée) : « **BANQUES** »
     + banques séparées par de larges espaces ; puis ligne des identifiants légaux. Lignes omises si vides.

#### Excel pour le fournisseur — `GET /api/export/commandes/{id}/bon` (`exporter_bon_fournisseur`)

- **Bouton** : fiche du bon, pied, lien « Excel pour le fournisseur » (infobulle « Le bon dans un classeur Excel, prêt
  à envoyer au fournisseur »), `download` (`DetailCommande.tsx:963-970`). Route `gestion_mp/api/exports_achats.py:324-419`,
  droit `ACHATS`, 404 « Bon de commande introuvable. ». Fichier « {n°}.xlsx » ou « brouillon-{id}.xlsx ».
- Feuille « Purchase order » (en anglais, sans prix ni montant) :
  - En-tête usine : raison sociale (Times New Roman 18 pt, rouge D40000) ou, faute de réglage, « Raison sociale à régler
    (Réglages › Paramètres › Société) » ; puis (Times 11) forme juridique, « SIEGE SOCIAL  {adresse} », ville, téléphone.
  - « PURCHASE ORDER {n°} » ou « PURCHASE ORDER — draft, not sent » (gras 13) ; « Date » (« 08 Oct 2026 » / « on
    sending ») ; « Expected delivery » (date / « to be agreed »).
  - « Supplier » : Name, Country, Contact, Phone, Email (lignes vides omises).
  - « Deliver to » : Company, Address, City, Expected date, Incoterm.
  - Tableau : « No. », « Item », « Description », « Packing », « Qty » (seulement pour un conditionnement), « Total weight
    (kg) », « Length (m, indicative) » ; ligne « Total ordered » (Σ kg).
  - « Remarks » + observations (si présentes) ; « Please confirm this order by return (quantities and delivery date)
    and quote its number on your delivery note and on your invoice. » ; pied « BANQUES     {banques} » et identifiants
    légaux (Times 10). Largeurs de colonnes A–G : 16, 30, 36, 24, 12, 14, 14.

#### Doublon non relié : `GET /api/export/bon-de-commande/{id}` (`exporter_bon_de_commande`, `gestion_mp/api/exports.py:307-419`)

- Droit `ACHATS`. **Aucun écran ne l'appelle** (recherche dans `ecran/src` : seuls `/commandes/{id}/impression` et
  `/export/commandes/{id}/bon` sont utilisés).
- Ancienne version **en français et avec prix** : feuille « Bon de commande », en-tête société (raison sociale gras 14 ;
  « secteur · adresse · téléphone » ; « ICE … · RC … · IF … »), « Bon de commande {n°} » / « — brouillon, non envoyé »,
  lignes Date, « Livraison souhaitée » (« à convenir »), Fournisseur, Pays, Contact, Téléphone, Email, Conditions de
  paiement, Incoterm, Devise, « Prix : à confirmer par le fournisseur » si un prix n'est pas confirmé ; colonnes
  Référence, Désignation, Quantité, Unité (« Palette de 705,6 kg »), Soit (kg), [Soit (ml, indicatif)], Prix / kg (ou
  « à confirmer »), Montant ; Total ; « Observations » ; paysage, une page en largeur. Fichier « {n°}.xlsx » ou
  « BC-brouillon-{id}.xlsx ».

---

### Incohérences et anomalies repérées

1. **Impossible de « vider » la livraison prévue d'un bon** : la fiche envoie `date_livraison_prevue: null` quand on
   efface le champ (`DetailCommande.tsx:246`), mais `_changer_promesse` ignore `None` (`gestion_mp/api/achats.py:619-620`) :
   la date reste. Or l'aide de l'écran dit « vide : date d’envoi + délai du fournisseur » (`DetailCommande.tsx:458`) et les
   refus d'envoi conseillent « la corriger, ou la vider » (`achats.py:508-510, 703-705`).
2. **La case « Envoyer avec nos prix du catalogue, « à confirmer » » n'a aucun effet sur le document** : l'infobulle
   promet des prix « imprimés « à confirmer » » (`PreparationCommande.tsx:617-635`), mais l'impression et l'Excel
   fournisseur n'impriment **aucun prix** (`achats.py:1035-1041`, `exports_achats.py:324-331`). Seule la route morte
   `/export/bon-de-commande` les imprimait.
3. **Route morte et doublon** : `exporter_bon_de_commande` (`gestion_mp/api/exports.py:307-419`) n'est appelée par aucun
   écran ; elle est en français, avec prix, et emploie « Livraison souhaitée » (vocabulaire interdit, REGLES-ECRAN §3) et
   « Observations » là où le bon officiel dit « Remarks ».
4. **Solder / Annuler : règle différente entre l'infobulle et le geste** : l'infobulle se fonde sur `c.recu > 0`
   (reçu **net** des retours) (`DetailCommande.tsx:1063-1065`), la question et le libellé sur `dejaLivre` (une réception
   validée existe) (`:1068-1080`), comme le serveur (`_a_ete_livre`, `achats.py:538-547`). Bon livré puis tout renvoyé :
   le bouton dit « Solder… » mais l'infobulle « Annuler la commande : rien n’a été reçu ».
5. **Enregistrement multi-devises non atomique** : `SaisieReception` envoie une requête par devise l'une après l'autre
   (`SaisieReception.tsx:462-473`) ; si la 2e échoue, la 1re est déjà enregistrée et la fenêtre reste ouverte : un nouveau
   clic recrée la 1re réception (en mode nouvelle saisie) → doublon de brouillon.
6. **Excédent : l'écran le calcule ligne par ligne, le serveur tous lots ensemble** (`SaisieReception.tsx:819-822` contre
   `receptions.py:133-162`). L'écran ne permet d'ailleurs pas de recevoir deux lots sur la même ligne de bon (une ligne par
   ligne de commande, doublons filtrés `:310-312`) : un camion qui apporte deux lots d'une même référence commandée ne se
   saisit pas, sauf en ajoutant le second lot « hors commande ».
7. **Le fournisseur peut confirmer sa date avec ses prix côté serveur** (`ConfirmationPrix.date_livraison_prevue`,
   `achats.py:801-817`), mais le volet « Prix du fournisseur » ne propose aucun champ de date (`DetailCommande.tsx:667-803`).
8. **Confirmer des prix sur un brouillon fige le cours** (`achats.py:832-833`, le volet Prix est ouvert à tout statut sauf
   annulé, `DetailCommande.tsx:667-668`) : le cours de la devise peut se figer avant que le bon parte, et c'est lui qui
   mesure ensuite le seuil d'approbation.
9. **Boutons grisés sans raison en infobulle** (REGLES-ECRAN §2) : « Enregistrer » des lignes (`DetailCommande.tsx:508`),
   « Enregistrer le suivi » (`:869-875`, raison seulement pour un jalon futur), « Oui, renvoyer aux achats » (motif < 3
   car., `:939-942`), « Confirmer ces prix » sans prix saisi (infobulle fixe, `:782-785`), « Créer le bon… » sans ligne
   (infobulle fixe, `PreparationCommande.tsx:645-650`), « Enregistrer le brouillon » (`SaisieReception.tsx:1067`),
   « Imprimer les étiquettes des lots » (`DetailReception.tsx:658`), « Ouvrir la réclamation » (`Reclamations.tsx:443`),
   « Enregistrer la réponse » (`:587`).
10. **Refus découverts au clic, non annoncés** : envoi refusé si la livraison prévue est passée ou en période close
    (`achats.py:503-510, 703-705`) alors que « Marquer comme envoyé » reste actif ; promesse « date passée, ne se repousse
    plus » (`achats.py:630-632`) alors que le champ reste modifiable ; règlement antérieur à la facture (`suivi.py:424-427`).
11. **Vocabulaire** (REGLES-ECRAN §3) : « Remarques au fournisseur » (`PreparationCommande.tsx:409`,
    `DetailCommande.tsx:474`) alors que le mot officiel est « Observations » — et la même donnée s'affiche « Observations : »
    sur un bon figé (`DetailCommande.tsx:518`) et s'exporte « Observations » (`exports_achats.py:113`) ; « Reste à recevoir »
    (indicateur `Commandes.tsx:179`, colonne d'export `exports_achats.py:110`) à côté de « Reste à livrer » ; « Disponible
    (kg) » / « Commandé (kg) » corrects ; « Annoncé BL (kg) » de l'Archive des pesées montre en fait le reste attendu à
    défaut de BL (`ArchivePesees.tsx:154-162`) ; l'infobulle de « Fournisseur » dans le plan dit « Préparer la commande de
    ce fournisseur » (ok). Dans le document anglais, « BANQUES » et « SIEGE SOCIAL » restent en français
    (`achats.py:980, 1146`) ; « Length (m, indicative) » / « ≈ N m » alors que l'écran dit « ml ».
12. **Bon sans numéro « à approuver » affiché « Brouillon »** dans la liste (`Commandes.tsx:339`) et « (brouillon) » dans
    le titre de la fiche (`DetailCommande.tsx:340`), alors que `lib/commandes.ts:54-57` (`numeroOuBrouillon`) affiche
    « À approuver » pour ce cas ailleurs.
13. **Filtres sans « Effacer les filtres »** : Commandes (case « en retard seulement » + recherche, `Commandes.tsx:212-229`),
    Poids des bobines et Archive des pesées (case « écarts seulement » + recherche). Le filtre « en retard » n'est pas
    transmis à l'export (`Commandes.tsx:145`), qui exporte donc plus que la liste affichée.
14. **Plan d'achat** : la colonne « À commander » n'a pas d'unité dans son en-tête (`PlanAchat.tsx:263-266`) ; l'indicateur
    « Ruptures » compte toutes les matières (pas seulement celles à commander, `moteur.py:1770`) sans le dire ; le bouton
    d'export exporte tout le classeur de pilotage, pas la liste affichée (`PlanAchat.tsx:141-144`).
15. **Unités proposées / acceptées** : `unitesDe` (`types.ts:277-278`) propose l'unité d'achat de la fiche même « ml »,
    que le serveur refuse (« ne se commande pas en « ml » », `achats.py:406, 424-427`).
16. **Facture** : la date de facture n'a pas de maximum dans la saisie (`SaisieReception.tsx:628-636`) mais en a un dans la
    fiche (`DetailReception.tsx:353`). L'annulation d'une réception n'affiche aucun message de succès (texte vide,
    `DetailReception.tsx:730`).
17. **Réclamation sur une ligne refusée** : la ligne choisie n'a pas de lot (`lot_id` nul), la réclamation part « toute la
    réception » sans référence (`Reclamations.tsx:296`). Sur une réclamation close, choisir « — pas encore — » puis
    « Enregistrer la réponse » est refusé par le serveur (`suivi.py:157-159`) sans prévention à l'écran.
18. **Onglets de fenêtres non écrits dans l'adresse** : volets de la fiche commande (`DetailCommande.tsx:133`), de la fiche
    réception, Bascule des réclamations ; seul `?onglet=` de page et `?ouvrir=` existent (pas de lien direct vers « Prix du
    fournisseur », sauf par le bouton « Saisir les prix » de la liste).
19. **« Palettes par conteneur »** ne marque pas la fenêtre comme modifiée et n'est pas enregistré (`PreparationCommande.tsx:388`) :
    perdu à la fermeture (aide de calcul seulement).
20. `gestion_mp/api/brouillons.py` (« Tout valider ») ignore les brouillons de commandes et de réceptions : ils ne figurent
    pas dans la file commune des brouillons.
21. `DetailReception.tsx:59` : commentaire orphelin (« échéance le … ») au-dessus de `resumerBlocages` (code mort de doc).

### Comptes

- **Pages** : 3 (Plan d'achat, Commandes, Réceptions) + **3 documents** (bon de commande imprimable HTML A4 ; Excel pour
  le fournisseur ; Excel « bon-de-commande » non relié) + 6 exports Excel de listes (pilotage, commandes, réceptions,
  pesées, bobines — et le bon).
- **Onglets / sous-vues** : 26 — Plan d'achat 2 ; Commandes 5 ; fiche commande 5 volets ; Réceptions 6 ; fiche réception
  3 volets ; Réclamations 3 (Bascule) ; fiche réclamation 2 volets.
- **Fenêtres** : 8 — Préparer une commande ; Nouvelle commande (choix du fournisseur) ; Bon de commande (fiche) ; Nouvelle
  réception / Corriger la réception ; Réception (fiche) ; Poids de la bobine (courbe) ; Nouvelle réclamation / Réclamer au
  fournisseur ; Réclamation (fiche). Plus 3 panneaux en ligne : facture d'une réception, motif de renvoi aux achats,
  bandeau de question de la saisie.
- **Gestes inventoriés** : 77 (plan 4, préparation 7, choix du fournisseur 3, liste des commandes 4, fiche commande 19,
  pièces jointes 2, liste des réceptions 5, saisie 8, fiche réception 12, réclamations 7, poids des bobines 3, archive
  des pesées 2, document imprimable 1).

---

## Partie 5 — Importations & coût de revient (dont Réglages › Postes de frais et Codes douaniers)

Périmètre : `ecran/src/pages/Importations.tsx` (687 l.), `components/importations/DetailDossier.tsx` (1629 l.),
`AnalyseRevient.tsx` (759 l.), `ChoixFacture.tsx` (161 l.), `importations.ts` (306 l.),
`ReglagesPostesFrais.tsx` (210 l.), `ReglagesCodesDouaniers.tsx` (171 l., lu en plus : les codes douaniers
nourrissent les droits attendus), `importations.css` (98 l.), plus `components/PiecesJointes.tsx` (onglet
Documents). Serveur : `gestion_mp/api/importations.py` (1153 l.), `gestion_mp/api/analyse_import.py` (470 l.),
`gestion_mp/api/referentiels_import.py` (postes de frais, codes douaniers), `gestion_mp/calcul/moteur.py`
l. 3520-3730 (formules), `gestion_mp/securite.py` (droits, numérotation, période close),
`gestion_mp/parametres.py` l. 107-117 (réglages des importations).

Références `fichier:ligne` relatives à `ecran/src` pour l'écran, au dépôt pour le serveur.

---

### 0. Notions transversales (à garder telles quelles)

| Notion | Règle / formule | Source |
|---|---|---|
| **Dossier d'importation** | **Un dossier = une facture = une livraison.** C'est à chaque livraison qu'on paie droits, fret, transitaire ; le dossier suit la facture, pas la commande. Il s'ouvre **depuis la facture d'une réception validée** et en prend **toute** la marchandise libre. Une facture n'a qu'un dossier ; un **second camion** de la même facture **rejoint** le sien. Une réception sans facture attend qu'on saisisse la facture (sur la réception). Seul un **dossier d'avant la mise en service** se saisit à la main, sans facture. Un dossier **repris de l'ERP Fil** (sans facture) peut porter plusieurs factures ; la suite de celles qu'il porte le rejoint. | `api/importations.py:1-31`, `pages/Importations.tsx:1-11` |
| **Numéro** | Donné **dès l'ouverture** (pas de « Brouillon »). Série `DOS` au format **`NN/AA`** (compteur annuel sur 2 chiffres / année sur 2 chiffres), année = **année de la date d'arrivée** (la plus ancienne date des réceptions de la facture, sinon la date saisie, sinon aujourd'hui). Un dossier d'avant la mise en service peut garder son vrai numéro (saisi, ≤ 16 car., unique). Si le numéro calculé est déjà pris (numéro saisi à la main), on prend le suivant. | `securite.py:179-197`, `importations.py:560-570, 611-615` |
| **Statuts** | `ouvert` / `clos` (affichés « Ouvert » / « Clos le jj/mm/aaaa hh:mm »). Clore **fige le coût** ; rouvrir est tracé. | `importations.py:1028-1079` |
| **Entrée d'une marchandise** | À sa **pesée × son prix** (ce qui est entré en stock, au prix convenu), **pas** au montant de la facture (établie sur le poids du BL). Poids en kilos figé à l'entrée (`poids_kg = quantite_pesee`). Lignes prises : réception `validee`, ligne non `refuse`, `quantite_pesee > 0`, dans aucun dossier. | `importations.py:409-433, 532-546` |
| **Cours** | Chaque ligne en devise entre au **cours figé de son bon de commande** (cours des réglages le jour de la confirmation des prix) quand il existe et que la devise concorde ; sinon cours 0 = **cours du jour des réglages** (`parametres.taux(devise)`). Le **cours payé à la banque** le remplace (saisi ligne par ligne ou pour toute une devise). Une ligne en MAD n'a jamais de cours. À la clôture, un cours vide prend le cours du jour, écrit sur la ligne + commentaire « cours du jour X figé à la clôture du jj/mm/aaaa ». | `importations.py:532-546, 1051-1058` ; `moteur.py:3611-3621` |
| **Achat (marchandise MAD)** | `valeur_mad = valeur_devise` si MAD, sinon `valeur_devise × (cours or taux du jour)`. | `moteur.valeur_ligne_import` |
| **Postes de frais** | Référentiel (Réglages › Postes de frais). Postes d'origine : DD Droits de douane, TPI Taxe parafiscale à l'importation, **TVA** TVA à l'importation (**récupérable**), PORT Port Med, FRET Fret, ASSUR Assurance, TRANSIT Transitaire, TIMBRE Timbre, INT_OC Intérêts / ordre de change, TMSA TMSA, AUTRE Autre frais. Chaque poste : **récupérable** (hors coût) ou coût ; **clé de répartition** `valeur` (« à la valeur », défaut) ou `poids` (« au poids »). Postes « système » (lus par les calculs, indélébiles, nature figée) : DD, TPI, TVA, FRET, ASSUR. | `calcul/modele.py:518-533`, `referentiels_import.py:36-40` |
| **Répartition des frais** (clé) | Pour chaque ligne : `part = valeur_mad / Σ valeur_mad` ; `part_poids = poids_kg / Σ poids_kg`. Un frais **global** d'un poste à la valeur → `montant × part` ; au poids → `montant × part_poids`. Un frais **visé sur une ligne** (`ligne_id`) lui revient **entier**. Un frais à **répartition figée** (`parts`, dossier clos dont le poste a changé de clé) garde ses parts tant qu'elles couvrent tout le montant sur des lignes encore au dossier. Sans arrondi. | `moteur.revient_dossier` `moteur.py:3624-3686` |
| **Charges hors TVA** (ligne) | Σ des parts des postes **non récupérables**. **TVA** (ligne) = Σ des parts des postes récupérables. | idem |
| **Coût hors TVA (= coût de revient)** | `revient_mad = valeur_mad + charges_mad` ; nourrit le **coût moyen du stock** (CMUP) du lot. | `moteur.py:3549-3551` |
| **Coût TTC** (`decaisse_mad`) | `revient_mad + tva_mad`. | `moteur.py:3563-3565` |
| **Charges / achat** (`surcout`) | `charges_mad / valeur_mad` (0 si pas d'achat). | `moteur.py:3559-3561`, `importations.py:309` |
| **Coût hors TVA / kg** | dossier : `revient_mad / poids` ; ligne : `revient_unite = revient_mad / quantite` (quantité en kg) ; `revient_kg = revient_mad / poids_kg`. Famille : `(valeur+charges)/quantité kg`. Achat / kg = `valeur_mad / poids`. | `importations.py:277, 333-337` |
| **Frais non répartis** | `charges_non_reparties = Σ frais hors TVA saisis − Σ charges réparties` (si > 0,005) ; idem TVA. Frais sans marchandise où se poser (dossier vide) : **dans aucun coût**, montrés à part, le dossier **ne se clôt pas** ainsi. | `importations.py:204-207, 1042-1044` |
| **Valeur en douane (CAF)** | Par ligne : `valeur_mad + part FRET + part ASSUR` (`POSTES_VALEUR_EN_DOUANE = ("FRET","ASSUR")`). | `importations.py:243-244`, `moteur.py:3572` |
| **Droits attendus** | Par ligne : `valeur en douane × taux_droits` du **code douanier actif** de la matière. Dossier : Σ, **seulement si toutes** les matières ont un code actif (sinon `null` + liste `matieres_sans_code`, codes désactivés comptés « sans code » et listés à part). **Droits saisis** = Σ frais du poste `DD`. | `importations.py:245-254, 284, 305-307` |
| **Écart des droits** (écran seul) | Signalé si `|saisis − attendus| > max(50 MAD, 2 % des attendus)` et des droits saisis. | `DetailDossier.tsx:110-115` |
| **TVA attendue** | `taux_tva_import × (valeur en douane + droits DD + TPI)`, valeur en douane = Σ achat MAD + Σ frais FRET + ASSUR ; TPI = Σ frais poste `TPI` s'il y en a, sinon `valeur en douane × taux_tpi_import`. `null` sans marchandise. **TVA saisie** comparée = Σ du **seul poste `TVA`**. | `moteur.py:3580-3603`, `importations.py:199-201, 286` |
| **Écart TVA toléré** | `5 % × |TVA attendue|` (`TOLERANCE_TVA_IMPORT = 0.05`, constante serveur). L'écran signale si `tva_saisie > 0`, attendue > 0 et `|saisie − attendue| > toléré`. | `moteur.py:3577, 3606-3608`, `DetailDossier.tsx:142-149` |
| **Frais hors norme** (C35) | Dossier : `achat > 0` et `charges réparties > achat × seuil_surcout_import`. Ligne : `charges > 0,005` et (`valeur ≤ 0` ou `charges > valeur × seuil`). Seuil réglable « Frais d'un dossier d'importation à vérifier au-delà de », défaut **100 %**, de 5 % à 10 000 %. | `importations.py:311-316`, `moteur.py:3689-3694`, `parametres.py:110-113` |
| **Marchandise négative** | Ligne dont `revient_mad < −0,005` (un avoir trop gros). Le serveur **refuse** tout frais/modif/retrait qui en crée une. | `moteur.py:3697-3700`, `importations.py:956-968` |
| **Écart facture ↔ reçu** (C36) | Si la facture a un montant et toutes les lignes sont dans sa devise : `reçu = Σ valeur_devise` ; `écart = montant − reçu` ; `part = écart / reçu` ; **hors tolérance** si `|écart| > 0,005` et `|part| > toler_facture_import` (défaut **2 %**). Le coût reste à la pesée × prix. | `moteur.py:3703-3721`, `parametres.py:114-117` |
| **Cours éloigné** (écran) | `|cours / cours_du_jour − 1| > 5 %`. | `DetailDossier.tsx:887-891` |
| **Cours disparates** | Une devise du dossier a plusieurs cours (cours ou, à défaut, taux du jour, arrondis à 6 déc.). | `importations.py:257-258, 325-326` |
| **Lignes au cours du bon** | Lignes en devise dont `cours == cours_bon` (cours figé du bon) : pas le cours de la banque. | `importations.py:255-260` |
| **Fournisseur marocain (local)** | Pays MAROC/MOROCCO/MA, ou pays vide et devise MAD. Pas de dossier d'importation normalement ; ses factures sont écartées de « En attente » (comptées) ; ouvrir quand même un dossier se **confirme** (`local_confirme`). | `importations.py:109-113, 605-608` |
| **Période close** | Tout geste qui change le coût d'une marchandise entrée dans la période close (ouverture, rattachement, saisie à la main, cours, frais, retrait, détachement, réouverture, suppression, changement de clé/nature de poste) est refusé (voir message §8). **La clôture** reste permise. | `securite.py:235-275` |
| **Échéancier du dossier** | Les factures de marchandise (échéance saisie à la réception, montant = montant de la facture, sinon **estimé** = Σ pesée × prix apportée au dossier) + chaque frais (échéance saisie sur le frais, en MAD). Trié par échéance (sans échéance à la fin) puis « quoi ». Réglé = `payee_le` (le règlement se saisit dans Analyse › Échéancier, `PUT /api/echeancier/paiement`). | `importations.py:364-385` |
| **Famille de fil** | « composition + façon (libellé du type sans parenthèse) + titrage » (sans la couleur), à défaut libellé de composition ou référence. Ex. « PP Frisé 2900 Dtex ». | `importations.py:58-71` |
| **Pièces jointes** | Facture fournisseur, DUM, connaissement, certificat d'origine, factures de frais, quittances ; même dossier clos. | `DetailDossier.tsx:451-455` |
| **Journal** | Chaque geste écrit au journal des actions : « ouverture dossier », « modification dossier », « marchandises dossier », « marchandise saisie à la main », « cours », « commentaire marchandise », « marchandise retirée », « réception détachée », « frais », « frais modifié », « frais retiré », « clôture dossier », « réouverture dossier », « suppression dossier », « frais figés », « création/modification/suppression poste de frais », « création/modification/suppression code douanier ». | `importations.py`, `referentiels_import.py` |

**Droits serveur** : toutes les routes de dossiers, `dossiers-a-rattacher`, `export/dossiers`, analyse du coût
de revient et son export, `postes-frais/complet`, `codes-douaniers` (GET), pièces jointes : **`ACHATS`**
(achats + direction). Écritures postes de frais et codes douaniers : **`DIRECTION`**. Refus de rôle :
« Cette action est réservée à : responsable achats. » (403) ou « … réservée à : la direction. »
(`securite.py:104-114`). L'alimentation ne voit rien de ces écrans.

**Rafraîchissement après écriture** (`importations.ts:290-306`) : `dossiers`, `dossiers-a-rattacher`,
`analyse-revient`, `analyse-qualite`, `valorisation`, `stock`, `lots`, `lot`, `soldes`, `cockpit`, `prix`,
`controles`, `postes-frais` (le coût de revient nourrit le coût moyen, la valorisation, les contrôles).

**Teintes** (`importations.css`) : `tr.ligne-groupe` (tête de groupe, fond `--surface-alt`, 12,5 px) ;
`.entete-dossier` (rangée souple, 13 px, gris, `strong` en couleur texte) ; `.enregistre` (vert `--positive`,
600) ; `.controles-dossier` (grille de 2 encarts ≥ 320 px) ; `.controle-dossier` (bordure, fond
`--surface-alt`) et `.controle-dossier.ecart` (bordure `--negative`, fond `--negative-soft` = rouge) ;
`table.saisie.frais` (select 130-190 px, textes 90-120 px, dates 132 px) ; `tr.nouvelle` (ligne d'ajout fond
`--accent-soft` = « la ligne bleue ») ; `.reunion` (bandeau des puces de l'analyse) ; `button.lien.dossier`
(gras) ; `.indicateurs.serres` (indicateurs bas dans une fenêtre) ; `.filtres.etroits select` (104-140 px).
Classe `ecart-moins` (rouge) pour les alertes ; `Etiquette` tons `urgent` (rouge), `attention`, `ok`,
`accent`, `neutre`.

---

### 1. Importations & coût de revient — `/importations` (`?onglet=ouverts|clos|rattacher`, `?dossier=ID`)

- **Fichiers** : `pages/Importations.tsx` ; composants `ChoixFacture.tsx`, `DetailDossier.tsx`, `importations.ts`.
- **Rôles** : menu « Importations & coût de revient » rôles `['achats']` (`App.tsx:63`), garde de route
  `garde(['achats'])` (`App.tsx:256`) → achats + direction ; alimentation redirigée vers son accueil. Dans
  l'écran, `peut('achats')` conditionne « Nouveau dossier » (`Importations.tsx:91`) et `interdit` (grise les
  boutons de la vue « En attente », `:423, 466`) — toujours vrai/faux de fait (garde). Serveur `ACHATS`.
- **Adresse** : `onglet` absent = `ouverts` ; valeurs hors liste → `ouverts`. `dossier=ID` ouvre la fenêtre du
  dossier par-dessus la liste ; fermer la fenêtre retire `dossier`. Écriture en `replace` (`:63-68`).
  Liens entrants : Accueil, tâches « N facture(s) reçue(s) sans dossier d'importation » et « N réception(s)
  importée(s) sans facture » → `/importations?onglet=rattacher` (`pages/Accueil.tsx:290-305`) ; Analyse ›
  Contrôles, colonne dossier → `/importations?dossier=ID` (`components/direction/AnalyseControles.tsx:255-258`) ;
  Mode d'emploi (`pages/Guide.tsx:419`).
- **Données** : `GET /api/dossiers` (résumés de tous les dossiers, sans lignes/frais/échéancier, triés date
  d'arrivée décroissante nulls en dernier, puis id décroissant) ; `GET /api/dossiers-a-rattacher[?locaux=true]`.
- **En-tête** : titre « Importations & coût de revient » ; sous-titre « Une facture, un dossier : la livraison
  et ses frais, répartis à la valeur ou au poids. La TVA reste hors du coût. » ; actions : lien
  « Analyse du coût de revient », bouton « Nouveau dossier ».

#### Indicateurs (sur **tous** les dossiers, ouverts et clos, indépendamment de l'onglet et de la recherche)

| Indicateur | Valeur affichée | Formule / infobulle | Clic |
|---|---|---|---|
| Dossiers | nombre de dossiers | détail « dont N ouvert(s) » | — |
| Achat | `montantCourt(Σ marchandise_mad)` (« 17,4 M MAD » au-delà du million) | infobulle = montant exact ; détail « marchandise, en MAD » | — |
| Charges hors TVA (ton attention) | `montantCourt(Σ charges_mad)` (charges réparties) | infobulle montant exact ; détail « x,x % de l'achat » (= charges/achat) ou « toutes les charges sauf la TVA » si achat nul ; + en rouge « · + N non répartis » (Σ `charges_non_reparties_mad`) avec infobulle « Frais sans marchandise, dans aucun coût : 01/26 (1 234 MAD), … » | — |
| Coût hors TVA (ton ok) | `montantCourt(Σ revient_mad)` | infobulle exact ; détail « achat + charges, rendu usine » | — |

#### Onglets

`Dossiers ouverts` (compte = nb ouverts) · `Dossiers clos` (compte) · `En attente de dossier` (compte =
nb factures en attente + nb réceptions sans facture). Erreur de chargement : message rouge (texte de
l'erreur) ; chargement : « Un instant — chargement : les dossiers… ».

#### 1.a Onglets « Dossiers ouverts » / « Dossiers clos » (`ListeDossiers`, `Importations.tsx:185-370`)

Carte titrée « Dossiers ouverts » / « Dossiers clos ». En-tête de carte : (onglet ouverts seulement, s'il y a
des arrivées en attente) lien « N arrivée(s) attendent leur dossier » → onglet `rattacher` ; bouton-lien
« Exporter en Excel » (`/api/export/dossiers?statut=ouvert|clos`, infobulle « Ces dossiers, leurs
marchandises, leurs frais et leur échéancier dans un classeur »).

**Recherche** (rangée `.filtres`) : à la frappe, plusieurs mots, tout ordre, sans accents, sur numéro, libellé,
banque, commentaire, factures, réceptions, familles. Placeholder « Numéro, libellé, facture, réception,
famille de fil (« frisé 2900 »)… ». Compteur « N dossier(s) » (singulier/pluriel). Aucun filtre, pas de tri
cliquable (ordre serveur), pas de pagination. Cadre `court`.

| Colonne (libellé exact) | Contenu / unité | Format | Remarque |
|---|---|---|---|
| Dossier | **numéro** en gras + étiquette rouge « à vérifier » (infobulle = raisons jointes par « · ») ; dessous, note : libellé ou « — » | min 150 px | raisons possibles : « frais non répartis », « droits ≠ attendus » (règle 2 %/50 MAD), « TVA ≠ attendue », « facture ≠ marchandise reçue », « frais hors norme sur une marchandise », « marchandise négative (avoir) » |
| Arrivée | date d'arrivée | jj/mm/aaaa, sans retour | |
| Clos le | (onglet clos seulement) date-heure de clôture | court | |
| Facture · réceptions | dossier à facture : **n° facture** + note « REC-… · REC-… » ; dossier repris : pour chaque pièce, **facture** ou note « sans facture » + réceptions ; sinon note « saisi à la main » (s'il a des lignes) ou « — » | | |
| Familles de fil | les 3 premières « famille · N kg » ; « + N autre(s) » ; « aucune marchandise » | cellule `familles-cellule` | familles triées par poids décroissant |
| Poids | `N kg` | droite | |
| Achat MAD | marchandise MAD | droite, entier | |
| Charges hors TVA (infobulle d'en-tête « toutes les charges sauf la TVA ») | charges réparties ; note « x,x % de l'achat » (+ « — à vérifier » en rouge si frais hors norme, infobulle « Au-delà de 100 % de l'achat : des frais à vérifier ») ; note rouge « + N non répartis » (infobulle « Frais saisis sans marchandise où se répartir : dans aucun coût ») | droite | |
| Coût hors TVA | **revient** en gras ; note « x,xx MAD / kg » | droite | |
| Coût TTC | décaissé ; note « dont TVA N » | droite | |

- Ligne `cliquable`, infobulle « Ouvrir le dossier » → `?dossier=ID` (fenêtre §2).
- **Pied** (si > 1 ligne visible) : « Total des N dossiers » ; Poids Σ kg ; Achat Σ ; Charges Σ + « x % de
  l'achat » ; Coût hors TVA Σ + « x MAD / kg » (Σ revient / Σ poids) ; Coût TTC Σ + « dont TVA Σ ».
  Totaux = lignes **visibles** (suivent la recherche).
- **Vide** : recherche sans résultat « Aucun dossier ne correspond à la recherche. » ; sinon ouverts
  « Aucun dossier ouvert. « Nouveau dossier » en ouvre un depuis une facture. » ; clos « Aucun dossier clos. »

#### 1.b Onglet « En attente de dossier » (`VueARattacher`, `:405-476`)

Carte titrée « En attente de dossier » (infobulle « Tant qu'une arrivée n'est dans aucun dossier, son coût est
le seul prix de la facture : ses frais (droits, fret, transitaire…) manquent au coût moyen du stock. »).
Chargement : « Un instant — chargement : ce qui attend un dossier… ».

En-tête de carte :
- **Bascule** « Factures reçues (N) » / « Réceptions sans facture (N) » ; par défaut « Factures », sauf s'il
  n'y a aucune facture et des réceptions sans facture.
- **Case** (affichée s'il existe des factures/lignes locales écartées, ou si cochée) : « Fournisseurs marocains
  (N) » / cochée « Fournisseurs marocains montrés », infobulle « Un fournisseur marocain facture en dirhams,
  sans douane ni fret international : il n'a pas de dossier d'importation ». Cochée → relit
  `?locaux=true`.

**Sous-vue Factures reçues** : note « Un dossier, une facture : c'est à chaque livraison qu'on paie les droits,
le fret et le transitaire. La facture ouvre son dossier avec toute la marchandise qu'elle a apportée ; un second
camion de la même facture rejoint son dossier. » puis `ChoixFacture` (§1.d) en cadre `court`, bouton par
facture « Ouvrir son dossier » ou, pour un second camion, « Ajouter au dossier 12/26 ».

**Sous-vue Réceptions sans facture** (`ReceptionsSansFacture`, `:479-537`) : note « Pas de dossier sans
facture : saisir le numéro de la facture sur la réception (il se complète même après la validation), puis la
facture ouvre son dossier ci-dessus. »

| Colonne | Contenu | Format |
|---|---|---|
| Réception | n° en gras | |
| Fournisseur | nom | |
| Reçue le | date | sans retour |
| BL | n° de BL ou « — » | |
| Lots | nombre de lignes libres | droite |
| Poids | `N kg` (Σ pesée) | droite |
| Valeur | une ligne par devise « 12 345,67 USD » (Σ pesée × prix ; jamais deux devises additionnées) | droite |
| (sans titre) | lien-bouton « Saisir la facture » → `/receptions?reception=ID` | |

Lignes non cliquables ; pas de recherche ; vide : « Toutes les réceptions de l'étranger ont leur facture. »
Tri serveur : date décroissante.

#### 1.c Gestes de la page

| Geste | Où | Rôle | Conditions / grisé | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| « Analyse du coût de revient » (lien, infobulle « Par matière, titrage, fournisseur, qualité… dans la page Analyse ») | en-tête | achats | — | — | → `/analyse?onglet=revient` | — | — |
| « Nouveau dossier » | en-tête | achats (`peut`) | — | — | ouvre §1.e | — | — |
| « Exporter en Excel » | carte liste | achats | — | — | `GET /api/export/dossiers?statut=ouvert|clos` → `dossiers-importation-AAAA-MM-JJ.xlsx` | — | — |
| Clic ligne | liste | achats | — | — | `?dossier=ID` | — | — |
| « N arrivée(s) attendent leur dossier » | carte Dossiers ouverts | | si > 0 | — | onglet `rattacher` | — | — |
| « Ouvrir son dossier » | En attente › Factures | achats | grisé pendant un envoi (ou si pas achats) | fournisseur marocain sans dossier : « {fournisseur} est un fournisseur marocain : ni douane, ni fret international. Ouvrir quand même un dossier d'importation ? » · « Non » · « Oui, l'ouvrir » (infobulle du bouton « Un fournisseur marocain n'a normalement pas de dossier d'importation ») | `POST /api/dossiers {facture_id, local_confirme}` | « Facture {n°} : dossier {NN/AA} ouvert. » puis la fenêtre du dossier s'ouvre | voir §8 (création) |
| « Ajouter au dossier {NN/AA} » | En attente › Factures (second camion) | achats | idem | — | `POST /api/dossiers/{id}/rattacher {facture_id}` | « Facture {n°} : le second camion rejoint le dossier {NN/AA}. » + si cours disparates « Ses marchandises n'ont pas le même cours que les premières (USD, …) : vérifier l'avis de la banque. » ; ouvre le dossier | voir §8 (rattacher) |
| Case « Fournisseurs marocains » | En attente | | — | — | `GET /api/dossiers-a-rattacher?locaux=true` | — | — |
| « Saisir la facture » | Réceptions sans facture | | — | — | → `/receptions?reception=ID` | — | — |

#### 1.d Choisir une facture (`ChoixFacture.tsx`, utilisé 3 fois)

- **Filtres** (rangée `.filtres`) : liste « Tous les fournisseurs (N) » puis « {nom} ({nb factures}) » triés
  alphabétiquement (infobulle « Fournisseur ») ; champ texte (placeholder « Numéro de facture — la liste se
  réduit à mesure qu'on écrit », `autoFocus` dans la fenêtre de création) : correspond si le numéro, **sans
  ponctuation ni casse**, contient le texte tapé (« FA-2026/117 » = « fa 2026 117 »), **ou** si tous les mots
  (sans accents) se trouvent dans « numéro + réceptions + familles » (« frisé 2900 », « REC-… »). Compteur
  « N facture(s) ». Pas de bouton « Effacer les filtres ».

| Colonne | Contenu | Format |
|---|---|---|
| Facture | **n°** + note réceptions « · » | sans retour |
| Fournisseur | nom ; note « fournisseur marocain » (infobulle « Un fournisseur marocain n'a pas de dossier d'importation ») | |
| Reçue le | plus ancienne date de réception | |
| Lots | nb de lignes libres | droite |
| Poids | `N kg` | droite |
| Valeur facture | une ligne par devise (pesée × prix) `nombre(v,2) DEV` | droite |
| Familles de fil arrivées | « famille · N kg » | |
| (bouton) | libellé de l'action ; `Confirmer` si fournisseur local **sans** dossier ; sinon bouton principal | |

- Vide total : note « Aucune facture n'attend de dossier. Le numéro de facture se saisit sur la réception ;
  une facture dont toute la marchandise est dans son dossier n'apparaît plus ici, ni une réception pas encore
  validée. » ; vide filtré : « Aucune facture en attente ne correspond. Vérifier le numéro saisi sur la
  réception — ou la facture a déjà son dossier. »
- Tri : factures par date décroissante (serveur).

#### 1.e Fenêtre « Nouveau dossier d'importation » (`CreationDossier`, `:541-687`)

`Dialogue` très large ; garde « Abandonner les modifications ? » active seulement en mode « main » si numéro,
libellé, banque ou commentaire saisi. **Onglets** dans la fenêtre :

1. **« Depuis la facture reçue »** (compte = factures **sans** dossier). Note : « Un dossier, une facture.
   Choisir le fournisseur, taper le numéro de facture : toute la marchandise qu'elle a apportée entre au
   dossier, le libellé et la date d'arrivée se remplissent seuls. Il ne restera qu'à saisir les frais. » ;
   `ChoixFacture` (action « Ouvrir son dossier ») ; si des réceptions sans facture : message info « N
   réception(s) attendent leur facture : elle se saisit sur la réception (onglet « En attente de dossier »),
   puis elle ouvre son dossier ici. »
   → `POST /api/dossiers {facture_id, local_confirme}` ; succès : fenêtre fermée, onglet `ouverts`,
   `?dossier=ID`. Libellé auto serveur : « {fournisseur} — facture {n°} » ; date d'arrivée = plus ancienne
   date de réception.
2. **« Dossier d'avant la mise en service »**. Note : « Pour un dossier d'avant la mise en service seulement :
   il garde son vrai numéro, et ses marchandises se saisissent à la main. Toute arrivée depuis la mise en
   service a sa réception, donc sa facture : elle s'ouvre « Depuis la facture reçue ». »

| Champ | Type | Défaut | Contrôle |
|---|---|---|---|
| Numéro (aide « vide : le suivant (NN/AA) ; un ancien dossier garde le sien ») | texte, max 16, placeholder « automatique » | vide | serveur : unicité « Le dossier « X » existe déjà. » (409) |
| Libellé (`duo`, autoFocus) | texte, placeholder « Fournisseur, n° de facture, conteneur… » | vide | serveur ≤ 160 |
| Date d'arrivée | date | aujourd'hui | serveur : année 2000-2100 (« date d'arrivée hors période », 422) ; vide → aujourd'hui |
| Banque | texte, placeholder « AWB, BMCI… » | | serveur ≤ 32 |
| Commentaire (`large`) | texte, placeholder « Transitaire, n° de DUM, observations… » | | serveur ≤ 2000 |

Boutons : « Annuler » ; « Ouvrir le dossier à saisir à la main » (grisé pendant l'envoi) →
`POST /api/dossiers {numero, libelle, date_arrivee, banque, commentaire}` (champs `trim`).

---

### 2. Fenêtre « Dossier {NN/AA} » (`DetailDossier.tsx`)

Ouverte depuis `/importations?dossier=ID` et depuis l'analyse du coût de revient (§3). `Dialogue` très large ;
`sale` = brouillon de frais **ou** brouillon de saisie à la main non vide (« Abandonner les modifications ? »).

- **Rôles** : `modifiable = statut ouvert && peut('achats')` ; les gestes Clôturer/Rouvrir exigent
  `peut('achats')` ; Documents en lecture seule sans `achats`. Dossier clos : tout en lecture (cours, commentaires,
  frais affichés en texte, pas d'ajout). Serveur : `_ouvert()` refuse toute écriture sur un clos : « Ce dossier
  est clos : le rouvrir pour y toucher (c'est tracé). » (409).
- **Données** : `GET /api/dossiers/{id}` (détail complet) ; `GET /api/postes-frais/complet` ;
  `GET /api/pieces/dossier/{id}` ; `GET /api/dossiers-a-rattacher` (sans locaux) pour repérer un second camion
  (`factures` dont `dossier_id == id`). Chargement : fenêtre « Dossier d'importation » avec « Un instant —
  chargement : le dossier… », ou message rouge d'erreur (« Dossier introuvable. » 404).
- **Enregistrement** : tout champ existant s'enregistre **en quittant le champ** (ou Entrée) ; le dossier rendu
  par le serveur remplace l'affichage ; sans message de succès, on affiche « Enregistré à HH:MM » (heure du
  serveur) en vert pendant 4 s. Seuls les ajouts (frais, ligne à la main) ont un bouton.

#### 2.1 Titre et en-tête

Titre : « Dossier {numéro} » + note « — {libellé} » + étiquette « Ouvert » (attention) ou « Clos le jj/mm/aa
hh:mm » (ok).

Rangée d'en-tête (`.entete-dossier`) hors édition :
- « Arrivée le **jj/mm/aaaa** » ; « Banque : **{banque ou —}** » ;
- dossier à facture : « Facture **{n°}** du {date} · {montant 2 déc.} {devise} · échéance {date} (REC-…, REC-…) »
  (morceaux absents si vides) ; dossier repris : pour chaque pièce « Facture **X** (réceptions) » ou
  « Sans facture (…) » séparés par « · » ; sinon « Saisi à la main (avant la mise en service) » ;
- commentaire entre « » (infobulle = commentaire complet) ;
- bouton « Modifier l'en-tête » (si modifiable ; infobulle « Libellé, date d'arrivée, banque, commentaire — et
  supprimer le dossier ») ;
- « Enregistré à … » ; à droite : « Clôturer le dossier » (ouvert) ou « Rouvrir pour corriger » (clos).

**Édition de l'en-tête** (`EnTete`, `:469-532`), formulaire au-dessus :

| Champ | Type | Placeholder / aide | Enregistrement |
|---|---|---|---|
| Libellé (`duo`) | texte | « Conteneur Izmir, camion Globaltex… » | au blur si changé (comparaison `trim`) |
| Date d'arrivée | date | | au blur ; vide → rien envoyé |
| Banque | texte | « AWB, BMCI… » | au blur |
| Commentaire | texte | aide « transitaire, n° de DUM, remarques… » | au blur |

`PUT /api/dossiers/{id}` avec les 4 champs (le numéro ne se modifie jamais). Boutons « Terminé » (infobulle
« Chaque champ s'enregistre en le quittant ») et « Supprimer le dossier » (ici, loin de « Clôturer »).

#### 2.2 Indicateurs de la fenêtre (`indicateurs serres`)

| Indicateur | Valeur | Détail / infobulle | Clic |
|---|---|---|---|
| Poids | `N kg` | « N lot(s) » (= nb lignes) | — |
| Coût hors TVA (ok) | montantCourt(revient) | infobulle exact ; « x,xx MAD / kg » ou « achat + charges » | — |
| Achat | montantCourt(marchandise) | « marchandise, en MAD » | — |
| Charges hors TVA (attention) | montantCourt(charges réparties) | « x,x % de l'achat » ou « toutes les charges sauf la TVA » | — |
| Coût TTC (urgent si écart droits ou TVA) | montantCourt(décaissé) | sans écart « dont TVA N MAD » ; avec écart, lien « droits ≠ attendu : voir les frais » / « TVA ≠ attendu : … » / « droits et TVA ≠ attendus : voir les frais » (infobulle « Voir les contrôles de l'onglet Frais ») | → onglet Frais |

#### 2.3 Bandeaux d'alerte (sous les indicateurs)

| Condition | Ton | Texte exact |
|---|---|---|
| frais ou TVA non répartis | erreur | « Frais non répartis : {N MAD} hors TVA[ et {N MAD} de TVA] ne trouvent pas de marchandise où se répartir (dossier vide). Ils n'entrent dans aucun coût, ni ici ni dans l'analyse : ajouter la marchandise, ou corriger les frais. Le dossier ne se clôt pas ainsi. » |
| `surcout_aberrant` | erreur | « Frais hors norme : {charges} de frais pour {marchandise} de marchandise, soit {x %} de l'achat (au-delà de {seuil %}, réglable dans Réglages › Prix). Un zéro de trop, ou les frais d'un autre dossier ? Tant qu'ils restent, ils entrent dans le coût moyen du stock : » + lien « les vérifier sur leurs pièces » (→ Frais) « . » |
| lignes négatives / aberrantes | erreur | « Coût sous zéro : {réf., …} — un avoir dépasse ce que la marchandise a coûté. » + « Frais hors norme sur une seule marchandise : {réf.} (au-delà de {seuil %} de sa valeur). » + « Un frais visé sur une seule ligne nourrit le coût moyen de ce lot : » lien « le vérifier » (→ Frais) |
| écart facture hors tolérance | info | « Facture {n°} : {montant} {devise} facturés pour {reçu} {devise} reçus (pesée × prix), soit {x,x %} d'écart (tolérance {x,x %}, Réglages › Prix). Un manque de poids se réclame au fournisseur, une facture mal saisie se corrige sur sa réception. Le coût reste à la pesée × le prix (contrôle C36). » |

Puis les messages de succès / d'erreur du dernier geste.

#### 2.4 Onglets de la fenêtre (un seul niveau)

| Clé | Libellé | Compte | Présence |
|---|---|---|---|
| familles | « Par famille de fil » | nb familles | toujours |
| marchandises | « Marchandises » | nb lignes | toujours |
| frais | « Frais » / « Frais ● » si brouillon en cours | nb frais | toujours |
| echeancier | « Échéancier » | nb échéances | toujours |
| documents | « Documents » | nb pièces jointes | toujours |
| facture | « Second camion de la facture » | nb factures à rejoindre | si modifiable et un second camion attend |
| main | « Saisie à la main » / « Saisie à la main ● » | — | si modifiable et dossier sans facture (`a_la_main`) |

Onglet par défaut : « Saisie à la main » si le dossier est vide, modifiable et à la main ; sinon « Par famille
de fil ». Un onglet d'ajout devenu impossible retombe sur « Par famille de fil ». Les brouillons (frais,
saisie à la main) survivent au changement d'onglet. **L'onglet de la fenêtre n'est pas dans l'adresse.**

##### 2.4.1 Par famille de fil

Vide : « Le dossier n'a pas encore de marchandise. » + (si modifiable) lien « Ajouter une facture » (→ onglet
facture) « , des lignes de réception, ou une saisie à la main. »

| Colonne | Contenu | Format |
|---|---|---|
| Famille de fil | nom en gras | |
| Références | nb de matières distinctes | droite |
| Lots | nb de lignes | droite |
| Poids | `N kg` | droite |
| Achat MAD | Σ valeur MAD | droite |
| Charges hors TVA (infobulle « toutes les charges sauf la TVA ») | Σ charges | droite |
| Coût hors TVA | **Σ revient** | droite, gras |
| Achat / kg | valeur / kg (2 déc.) | droite |
| Coût hors TVA / kg | **revient / kg** (2 déc.) | droite, gras |
| Charges / achat | % ou « — » | droite |

Tri : poids décroissant. Pied « Tout le dossier » : Références vide, Lots = nb lignes, Poids, Achat, Charges,
Coût, Achat/kg (achat/poids), Coût/kg, Charges/achat (`surcout`). Lignes non cliquables. Cadre `dialogue`.

##### 2.4.2 Marchandises

Rangée `.filtres` : recherche à la frappe (placeholder « Référence, lot, famille, facture, réception,
commentaire… » ; champs : référence, lot, fournisseur, famille, facture, réception, commentaire) ; à droite, si
modifiable, **pour chaque devise ≠ MAD** du dossier : « 1 USD = [saisie, placeholder = cours du jour 4 déc.]
MAD [Appliquer aux USD] » (infobulle « Le cours payé à la banque pour toutes les marchandises en USD du
dossier ») ; bouton « Cours des bons (N) » si des lignes ont un cours de bon différent de leur cours.

Notes (dans l'ordre) :
- (rouge) « N ligne(s) à un cours éloigné de plus de 5 % du cours du jour : vérifier la devise et l'avis de la
  banque avant de clore. »
- « N marchandise(s) en devise sans cours payé : elles sont comptées au cours du jour des réglages (*). La
  clôture l'écrira sur la ligne, pour que le coût ne bouge plus. »
- « N marchandise(s) au cours de leur bon : c'est le cours des réglages le jour de la confirmation des prix,
  pas celui payé à la banque. Saisir le cours de la banque ; sinon la clôture garde celui du bon. »
- (rouge, par devise) « Les marchandises en USD n'ont pas toutes le même cours (10,1 et 10,2 MAD) — un second
  camion arrivé après une clôture ? Vérifier l'avis de la banque, ou appliquer un cours à toutes. »
- « Chaque marchandise entre à sa **pesée × son prix** : ce qui est entré en stock, au prix convenu. La facture
  du fournisseur, établie sur le poids de son bon de livraison, se rapproche de ce total [(X DEV facturés, Y
  reçus, écart z %)] : un écart au-delà de la tolérance réglée se signale (manque de poids à réclamer, facture
  mal saisie, camion pas encore rattaché) mais ne change pas le coût. »

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Référence | référence (infobulle) ; note « famille · facture F · REC-… » ou « famille · saisie à la main » | classe `reference` | |
| Lot | n° de lot ou « — » | mono | |
| Poids | `N kg` | droite | |
| Valeur facture | `valeur_devise` 2 déc. + devise ; note « x,xxxx DEV / kg » | droite | |
| Cours payé | MAD : « — » ; sinon `CoursLigne` (ci-dessous) | droite | |
| Achat MAD | valeur MAD ; infobulle « x % de la valeur du dossier » | droite | |
| Charges hors TVA (infobulle d'en-tête « toutes les charges sauf la TVA ; le détail par poste en infobulle ») | charges ; note « x % de l'achat » ; infobulle de cellule = détail par poste « Fret : 1 234,56 MAD » une ligne par poste, ou « aucun frais » | droite | |
| Coût hors TVA | **revient** | droite | |
| Coût hors TVA / kg (infobulle « Au kilo, le cuir, les franges et le ruban compris ») | **revient / quantité** 2 déc. ; note « achat x,xx » ; étiquette rouge « négatif : un avoir de trop » ou « frais hors norme » | droite | |
| Commentaire | modifiable : champ (max 300, placeholder « bobines abîmées, écart de poids… »), sinon texte ou « — » | | blur → enregistre |
| (geste) | modifiable seulement : « Détacher la réception » (1re ligne de chaque réception), note « avec REC-… » (autres lignes, infobulle « Une marchandise reçue sort avec toute sa réception »), ou « Retirer » (ligne saisie à la main) | | |

**Cours payé (`CoursLigne`)** : lecture seule → cours appliqué 4 déc. + « * » si cours du jour (infobulle
« cours payé » / « cours du jour (réglages) »). Modifiable → saisie (placeholder = cours appliqué) + note :
« cours du jour * » (pas de cours), « cours du bon BC-… » (cours = cours du bon), « +7 % / cours du jour »
(rouge si écart > 5 %), sinon « 1 USD = 10,1234 MAD » ; infobulle de la note : « cours du jour : X MAD » /
« cours figé du bon BC-… : X MAD » / « cours retenu : X MAD ». Quitter le champ envoie le cours (vide → 0 = retour
au cours du jour).

Pied (si lignes) : « Tout le dossier » · Poids · (vide) · (vide) · Achat · Charges · Coût · Coût/kg. Vide :
« Aucune marchandise ne correspond. » / « Aucune marchandise dans ce dossier. »

##### 2.4.3 Frais

**Deux encarts de contrôle** (`.controles-dossier`) :

1. **Droits de douane** (cadre rouge si écart ; infobulle « Droits attendus = taux du code douanier de chaque
   matière × sa valeur en douane (achat + fret). Le code se porte sur la fiche matière. ») : « saisis {N MAD} ·
   attendus **{N MAD}** » (attendus arrondis, « — » si null) ; si écart, rouge « écart {±N MAD} » (infobulle
   « Vérifier la quittance, la valeur déclarée ou le code douanier des matières ») ; si matières sans code,
   note « rien d'attendu : N matière(s) sans code actif » (infobulle « Les droits attendus ne se comparent aux
   droits payés que si toutes les matières du dossier ont un code douanier actif (fiche matière). Il manque :
   » + une référence par ligne, suffixée « (code désactivé) ») ; bouton « Proposer les droits » (si attendus
   connus, aucun droit saisi, modifiable ; infobulle « Pré-remplir un frais « Droits de douane » au montant
   attendu, à vérifier sur la quittance ») → remplit la ligne d'ajout : poste DD, montant attendu arrondi au
   centime, commentaire « proposé par les codes douaniers ».
2. **TVA à l'importation** (cadre rouge si écart ; infobulle « Attendue = 20 % (taux réglé) × (valeur en douane
   + droits + TPI), la valeur en douane étant l'achat, le fret et l'assurance (CAF), la TPI 0,25 % de celle-ci
   (ou son frais « TPI »). Écart toléré : 5 % (cours de la douane, assurance non saisie). Récupérable : la TVA
   n'entre pas dans le coût. ») : « saisie {Σ frais récupérables} · attendue **{N}** » (« — » si pas de
   marchandise, infobulle « Sans marchandise, pas de valeur en douane : rien n'est attendu ») ; si écart, rouge
   « écart {±N MAD} » (infobulle « Au-delà de l'écart toléré : vérifier la quittance de douane »).

**Tableau des frais** (`table.saisie.frais`, cadre `dialogue`) :

| Colonne | Modifiable | Lecture seule (clos) |
|---|---|---|
| Poste | liste « {libellé} — {hors coût | à la valeur | au poids} » ; changement → enregistré aussitôt | libellé + étiquette « récupérable » |
| Montant (MAD) | saisie nombre (classe `manque` si vide) ; enregistré au blur | 2 déc. |
| Porte sur | liste « Tout le dossier » / « {réf.} · lot {lot} » pour chaque ligne ; enregistré aussitôt | « Tout le dossier » ou « réf. · lot » (« ? » si ligne introuvable) |
| Répartition | texte calculé : « hors coût (récupérable) » / « sur cette marchandise » / « figée (clé d'avant son changement) » / « à la valeur » / « au poids » | idem |
| Prestataire | texte (blur) | texte ou « — » |
| Pièce | texte (blur) | texte ou « — » |
| Date de la pièce | date (blur) | date |
| Échéance | date (blur) | date + note « réglé le jj/mm/aaaa » si payé |
| Commentaire | texte (blur) | note |
| (geste) | « Retirer » | — |

Une valeur modifiée qu'on n'est pas en train de taper est remplacée par celle du serveur ; le champ en cours
n'est pas écrasé (`LigneFrais` `:1246-1261`). Montant vidé → **rien n'est envoyé**.

**Ligne d'ajout** (« la ligne bleue », `tr.nouvelle`, si modifiable) : Poste (défaut : premier poste par ordre),
Montant (placeholder « avoir : négatif »), Porte sur (défaut « Tout le dossier »), Répartition (texte),
Prestataire (placeholder « transitaire, transporteur… »), Pièce (placeholder « n° de facture, quittance »),
Date de la pièce, Échéance, Commentaire ; boutons « Ajouter » (grisé si montant nul/vide, pas de poste, ou
envoi) et « Effacer » (si brouillon non vide ; infobulle « Vider la ligne d'ajout »).

Pied (si frais) : « Charges hors TVA » · Σ frais non récupérables saisis (2 déc.) · note « dans le coût · TVA
récupérable, hors coût : {Σ récupérables} MAD ». Vide (lecture seule) : « Aucun frais saisi : le coût hors TVA
est celui de la facture. » ; vide (modifiable), sous le tableau : « Aucun frais encore : le coût hors TVA est
celui de la facture. Saisir droits, fret, transitaire, banque… dès que les pièces arrivent, sur la ligne
bleue. »

##### 2.4.4 Échéancier

Vide : « Ni facture de marchandise, ni frais dans ce dossier : rien à payer encore. » Tableau (infobulle du
tableau : « Ce que le dossier engage à payer, mois par mois : la facture du fournisseur (échéance saisie à la
réception) et chaque frais (échéance saisie sur sa ligne). Ce qui est réglé le dit (Analyse › Échéancier) ; les
totaux ne comptent que ce qui reste à payer. Les devises ne s'additionnent pas. »).

Groupes par mois d'échéance (ligne `ligne-groupe`) : « **octobre 2026** » ou « **Sans échéance** · lien « la
saisir sur le frais » (→ onglet Frais) (celle d'une facture de marchandise se saisit à la réception) » ; à
droite total du mois « à payer 12 345,00 USD · 3 000,00 MAD » (non réglé seulement, par devise) ou « tout est
réglé ».

| Colonne | Contenu |
|---|---|
| Échéance | date |
| Nature | étiquette « marchandise » (accent) ou « frais » (neutre) |
| Quoi | « Facture {n°} » ou libellé du poste |
| Tiers | fournisseur / prestataire ou « — » |
| Pièce | n° ou « — » + note « du {date} » |
| Montant | 2 déc. + note « estimé » (infobulle « La facture n'a pas de montant saisi : ce que sa marchandise au dossier a apporté, pesée × prix ») |
| Devise | devise (frais toujours MAD) |
| Règlement | étiquette ok « réglé le jj/mm/aaaa » ou note « à payer » |

Aucun geste de règlement ici (il se fait dans Analyse › Échéancier).

##### 2.4.5 Documents (pièces jointes)

Note : « La facture du fournisseur, la déclaration en douane (DUM), le connaissement, le certificat d'origine,
les factures de frais et les quittances : tout ce qui justifie le coût du dossier, même clos. » puis
`PiecesJointes objet="dossier"` (lecture seule sans `achats` ; **modifiable même sur un dossier clos**).
Bouton « Joindre un document… » (« Envoi… » pendant l'envoi) + note « ou le glisser ici · PDF, image, tableur,
texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; formats `.pdf, image/*, .txt, .csv,
.xlsx, .xls, .ods, .docx, .doc, .odt, .zip` ; glisser-déposer (contour pointillé). Colonnes : Document (lien de
téléchargement `/api/piece/{id}/fichier`, infobulle « Télécharger le document »), Genre (PDF / Image /
Tableur / Document / Archive / Texte), Taille (o / Ko / Mo), Par, Joint le, (Retirer). Vide « Aucun document
joint. » Trop lourd : « « {nom} » est trop lourd : 20 Mo au plus. » Succès « « {nom} » joint. » / « N documents
joints. » / « « {nom} » retiré. » Routes `GET|POST /api/pieces/dossier/{id}`, `DELETE /api/piece/{id}` (ACHATS).

##### 2.4.6 Second camion de la facture

Note « La facture {n°} est arrivée en plus d'un camion : ce qui est reçu depuis rejoint son dossier. » puis
`ChoixFacture` (cadre `dialogue`), action « Ajouter au dossier ».

##### 2.4.7 Saisie à la main (dossier d'avant la mise en service)

Note « Pour un dossier d'avant la mise en service : la marchandise n'a pas de réception dans Gestion MP. Un
numéro de lot inconnu est créé (sans stock) : un stock d'ouverture saisi sous le même numéro prendra le coût de
ce dossier. »

| Champ | Type | Défaut / calcul en direct | Contrôle |
|---|---|---|---|
| Matière (`duo`) | recherche (matières **actives**), « réf. — désignation », détail fournisseur, placeholder « Quelques mots de la référence ou de la désignation… » | choisir → devise = devise de la matière (ou MAD), prix = prix de la matière, valeur = prix × poids (2 déc.) | obligatoire ; serveur « Matière inconnue. » |
| Numéro de lot (aide « facultatif ») | texte | | serveur : lot déjà reçu → refus (§8) ; ≤ 80 |
| Fournisseur (aide « par défaut, celui de la matière ») | liste : « {fournisseur} (matière) » / « Celui de la matière » puis fournisseurs actifs | | « Fournisseur inconnu. » |
| Poids (kg) | nombre | change → valeur = prix × poids | obligatoire > 0 |
| Prix ({DEV} / kg) | nombre | change → valeur = prix × poids | |
| Valeur facture ({DEV}) (aide « le total de la ligne ») | nombre | change → prix = valeur / poids (4 déc.) | obligatoire (≥ 0) |
| Devise | liste des devises actives (+ celle en cours) « USD — Dollar » | MAD | « Devise inconnue : « X ». » |
| Cours payé (MAD pour 1 {DEV}) (aide « vide : le cours du jour des réglages ») | nombre, seulement si devise ≠ MAD | | 0-1000 |
| Commentaire (`large`) | texte max 300 | | |

Bouton « Ajouter au dossier » (grisé sans matière, sans poids, sans valeur, ou pendant l'envoi). Après succès,
le brouillon se vide mais garde fournisseur, devise et cours.

#### 2.5 Gestes de la fenêtre

| Geste | Où | Rôle | Conditions / grisé (infobulle) | Confirmation (texte exact) | Appel API | Succès | Refus serveur (exacts) |
|---|---|---|---|---|---|---|---|
| « Modifier l'en-tête » | en-tête | achats, ouvert | — | — | — | — | — |
| Champ d'en-tête quitté | édition en-tête | achats | changé seulement | — | `PUT /api/dossiers/{id}` | « Enregistré à HH:MM » | clos ; 422 « date d'arrivée hors période » |
| « Terminé » | édition en-tête | | — | — | — | — | — |
| « Supprimer le dossier » (danger) | édition en-tête | achats, ouvert | grisé pendant un envoi ; infobulle « Supprimer le dossier : sa facture attend de nouveau son dossier[, ses N frais sont perdus] » | « Supprimer le dossier {n°} ? La facture {F} attendra de nouveau son dossier. » (ou « Ses marchandises attendront de nouveau un dossier. ») + « N frais saisi(s), {montant}, seront perdus — pour les garder, détacher plutôt la réception (onglet Marchandises). » ou « Aucun frais n'est saisi. » · « Non » · « Oui, supprimer » | `DELETE /api/dossiers/{id}` | fenêtre fermée (pas de message) | clos ; période close « (suppression refusé) » |
| « Clôturer le dossier » (principal) | en-tête | achats, ouvert | grisé sans marchandise ou pendant l'envoi ; infobulle « Figer le coût hors TVA : un dossier clos ne se modifie plus (il se rouvre si une facture de frais arrive en retard, c'est tracé) » | « Clore ? » + avertissements, sinon « Le coût hors TVA devient celui des lots en stock. » · « Non » · « Oui, clôturer » | `POST /api/dossiers/{id}/cloturer` | « Dossier clôturé : son coût est figé. » | « Un dossier sans marchandise n'a rien à clore. » ; « Des frais ne trouvent pas de marchandise où se répartir : les affecter à tout le dossier, ou les retirer, avant de clore. » (409) |
| « Rouvrir pour corriger » | en-tête | achats, clos | grisé pendant l'envoi ; infobulle « Rouvrir le dossier pour y ajouter un frais arrivé en retard, ou corriger » | « Rouvrir pour corriger ? La réouverture est tracée. » · « Non » · « Oui, rouvrir » | `POST /api/dossiers/{id}/rouvrir` | « Dossier rouvert : il se modifie de nouveau. » | « Ce dossier est déjà ouvert. » (409) ; période close « (réouverture refusé) » |
| Liens « voir les frais », « les vérifier sur leurs pièces », « le vérifier » | indicateur / bandeaux | | — | — | onglet Frais | — | — |
| Lien « Ajouter une facture » | Par famille (vide) | modifiable | — | — | onglet Second camion | — | — |
| « Appliquer aux {DEV} » | Marchandises | achats, ouvert | grisé sans cours saisi ou pendant l'envoi (sans raison) | — | `PUT /api/dossiers/{id}/cours {cours, devise}` | « Cours {x,xxxx} MAD appliqué à toutes les marchandises en {DEV}. » (champ vidé) | « Le dossier mêle EUR, USD : donner le cours de chaque devise à part. » ; « Aucune marchandise en devise dans ce dossier. » ; « Aucune marchandise en {DEV} dans ce dossier. » ; période close « (cours refusé) » ; 422 si > 1000 |
| « Cours des bons (N) » | Marchandises | achats, ouvert | visible si des lignes ont cours ≠ cours du bon ; infobulle « Remettre sur chaque ligne le cours figé de son bon de commande à la confirmation des prix » | — | `POST /api/dossiers/{id}/cours-des-bons` | « Cours figés des bons remis sur les lignes. » | « Aucune ligne de ce dossier ne vient d'un bon au cours figé. » ; période close |
| Cours d'une ligne (blur) | Marchandises | achats, ouvert | lignes en devise | — | `PUT /api/dossiers/{id}/lignes/{lid} {cours}` | « Enregistré à … » | « Marchandise introuvable dans ce dossier. » (404) ; « Une marchandise facturée en MAD n'a pas de cours. » ; période close (si cours changé) |
| Commentaire d'une ligne (blur) | Marchandises | achats, ouvert | changé | — | `PUT …/lignes/{lid} {commentaire}` | « Enregistré à … » | ≤ 300 |
| « Détacher la réception » (danger) | Marchandises, 1re ligne d'une réception | achats, ouvert | grisé pendant l'envoi ; infobulle « Une marchandise reçue sort du dossier avec toute sa réception — pour annuler la réception ou corriger le numéro de sa facture. Les frais payés restent au dossier. » | « Détacher la réception {REC} (N ligne(s)) ? Sa marchandise attendra de nouveau son dossier ; les frais restent à celui-ci. » · « Non » · « Oui, détacher » | `POST /api/dossiers/{id}/detacher {reception_id}` | « Réception {REC} détachée : sa marchandise attend de nouveau son dossier, les frais restent ici. » | « Réception inconnue. » (404) ; « La réception {REC} n'est pas dans le dossier {n°}. » (404) ; « N frais porte(nt) sur une marchandise de la réception {REC} : les affecter à tout le dossier (onglet Frais, « Porte sur ») avant de la détacher — sinon ils sortiraient avec elle. » (409) ; période close. Effet : un frais à répartition figée qui avait une part sur une ligne sortie perd ses parts (se répartit de nouveau à la clé du poste). |
| « Retirer » (ligne à la main, danger) | Marchandises | achats, ouvert | grisé pendant l'envoi ; infobulle « Retirer cette marchandise du dossier » | « Retirer cette ligne ? » · « Non » · « Oui, retirer » | `DELETE /api/dossiers/{id}/lignes/{lid}` | « {réf.} retirée du dossier. » | ligne reçue : « Une marchandise reçue ne sort pas seule du dossier : elle sort avec toute sa réception {REC} (« Détacher la réception »), et les frais restent au dossier. » ; « N frais porte(nt) sur cette seule marchandise : les affecter à tout le dossier, ou les retirer, avant de la retirer. » (409) ; période close |
| « Proposer les droits » | Frais, encart droits | achats, ouvert | droits attendus connus et aucun DD saisi | — | (remplit le brouillon) | — | — |
| « Ajouter » (frais) | Frais, ligne bleue | achats, ouvert | grisé si montant nul, pas de poste, envoi (sans raison) | — | `POST /api/dossiers/{id}/charges {poste, montant, ligne_id, prestataire, piece, date_piece, echeance, commentaire}` | « Frais « {libellé du poste} » ajouté. » (brouillon vidé) | « Poste de frais inconnu : « X » (attendu : DD, TPI, …). » ; « Un frais a un montant (un avoir se saisit en négatif). » ; « La marchandise visée n'appartient pas à ce dossier. » ; « Ce frais rendrait {réf.} négatif ({N} MAD) : un avoir ne dépasse pas ce que la marchandise a coûté. Le porter sur tout le dossier, ou revoir son montant. » (409) ; période close « (frais refusé) » ; 422 : montant hors ±1e9, pièce > 64, prestataire > 120, commentaire > 300, « date hors période » |
| « Effacer » | Frais, ligne bleue | | brouillon non vide | — | — | — | — |
| Modifier un frais (poste, porte sur : aussitôt ; montant, textes, dates : au blur) | Frais | achats, ouvert | montant non vide ; changé | — | `PUT /api/dossiers/{id}/charges/{cid}` (tous les champs) | « Enregistré à … » | « Frais introuvable dans ce dossier. » (404) + mêmes contrôles que l'ajout. Un autre montant ou une autre ligne efface la répartition figée. |
| « Retirer » (frais, danger) | Frais | achats, ouvert | grisé pendant l'envoi ; infobulle « Retirer le frais « {libellé} » de {N,NN} MAD » | « Retirer ce frais ? » · « Non » · « Oui, retirer » | `DELETE /api/dossiers/{id}/charges/{cid}` | « Frais « {libellé} » retiré. » | rendrait une ligne négative (même message) ; période close |
| Lien « la saisir sur le frais » | Échéancier | | — | — | onglet Frais | — | — |
| « Joindre un document… », glisser, télécharger, « Retirer » (« Retirer ce document ? » · « Oui, retirer », infobulle « Retirer « {nom} » de la liste (le retrait est tracé) ») | Documents | achats | lecture seule sinon | | `/api/pieces…` | voir §2.4.5 | |
| « Ajouter au dossier » (second camion) | Second camion | achats, ouvert | grisé pendant l'envoi | (Confirmer si facture locale **sans** dossier — n'arrive pas ici) | `POST /api/dossiers/{id}/rattacher {facture_id}` | « Second camion de la facture {F} ajouté : N lot(s), N kg. » | voir §8 (rattacher) |
| « Ajouter au dossier » (saisie à la main) | Saisie à la main | achats, ouvert, dossier sans facture | grisé sans matière/poids/valeur (sans raison) | — | `POST /api/dossiers/{id}/ligne-manuelle {article_id, lot_numero, fournisseur_id, quantite, valeur_devise, devise, cours, commentaire}` | « {réf.} ajoutée au dossier[, lot {lot}]. » | « Le dossier de la facture {F} porte ce qu'elle a apporté, tel que reçu : la saisie à la main est réservée aux dossiers d'avant la mise en service. » ; « Le dossier {n°} porte des réceptions : sa marchandise entre par ses factures, telle que reçue. La saisie à la main est réservée aux dossiers d'avant la mise en service. » ; « Le lot « {lot} » de {réf.} est arrivé par la réception {REC} : son coût vient du dossier de sa facture. La saisie à la main ne vaut que pour un lot d'avant la mise en service. » ; « Matière inconnue. » ; « Devise inconnue : « X ». » ; « Fournisseur inconnu. » ; période close « (marchandise saisie à la main refusé) » |

**Avertissements de la clôture** (dans la question, `avertissementsCloture` `:118-138`), dans l'ordre :
1. « Les cours vides prendront le cours du jour (écrit sur chaque ligne). » (ligne en devise sans cours)
2. « N ligne(s) gardent le cours du bon — celui des réglages le jour de la confirmation des prix, pas celui payé
   à la banque : saisir le cours de la banque (onglet Marchandises) avant de clore, sinon ce cours est figé. »
3. par devise « Les marchandises en {DEV} ont plusieurs cours (a et b) : un second camion ? Vérifier l'avis de
   la banque. »
4. « Les frais dépassent {seuil %} de l'achat : les vérifier. »
5. « Frais hors norme sur {réf., …}. »
6. « La facture s'écarte de {x,x %} de la marchandise reçue. »
7. « Un cours s'écarte de plus de 5 % du cours du jour. »
8. « Le dossier mêle N fournisseurs. »
9. « Aucun droit de douane saisi. » (marchandise en devise, aucun DD)
10. « Droits ≠ attendus. »
11. « Aucune TVA saisie. » (marchandise en devise, TVA douane nulle) sinon « TVA ≠ attendue. »

Effets serveur de la clôture : `poids_kg` vide ← quantité ; cours vides ← taux du jour + note dans le
commentaire ; statut `clos`, `clos_le` ; journal (cours figés, lignes au cours du bon). Non soumise à la période
close.

---

### 3. Coût de revient — onglet de `/analyse?onglet=revient` (`AnalyseRevient.tsx`)

- **Fichiers** : `components/importations/AnalyseRevient.tsx`, accueilli par `pages/Analyse.tsx:146` (onglet
  « Coût de revient », sous-titre « Ce que chaque fil a coûté rendu usine, frais d'importation répartis. »).
- **Rôles** : menu Analyse `['achats']`, garde `/analyse` `['achats']` ; serveur `analyse_import.py` routeur
  entier `ACHATS`. Rien ne change selon le rôle.
- **Adresse** : seul `?onglet=revient` ; la vue, l'axe, les filtres ne sont **pas** dans l'adresse.
- **Données** : `GET /api/importations/analyse/revient?axe&q&debut&fin&statut&qualite&references&(composition&type_fil&titrage&couleur&fournisseur | selection)&detail`
  (`detail=true` en vue « Lot par lot », axe forcé `reference`) ; `GET /api/importations/analyse/qualite/{code}?debut&fin` ;
  articles, classification, qualités. Les résultats précédents restent affichés pendant le rechargement.
- Carte « Ce que la matière importée a coûté, rendue usine ». En-tête : **Bascule** « Regroupé » / « Lot par
  lot » / « Recette d'une qualité » ; « Exporter en Excel » (hors vue qualité ; `GET /api/export/revient?…`,
  infobulle « Le regroupement et le détail lot par lot dans un classeur » → `cout-de-revient-AAAA-MM-JJ.xlsx`,
  feuilles « Par {axe} » avec Charges / achat et ligne Total, et « Lot par lot »).

#### 3.1 Filtres (vues Regroupé et Lot par lot)

Rangée 1 (`.filtres.etroits`) :
- texte (placeholder « Dossier, référence, lot, fournisseur, couleur… »), envoyé au serveur **300 ms** après la
  dernière frappe ; serveur : tous les mots, sans accents, dans numéro et libellé du dossier, référence, lot,
  fournisseur, nature, composition, type de fil (code et libellé : « frisé » trouve FRZ), titrage + unité,
  couleur, désignation ;
- « + Ajouter une matière… » (recherche parmi les matières non déjà choisies, infobulle « Ajouter une matière :
  l'analyse ne garde que les matières choisies ») → puces ;
- (Regroupé) « Regrouper par » : « Par référence », « Par titrage » (défaut), « Par composition », « Par type de
  fil », « Par couleur », « Par fournisseur », « Par dossier », « Par lot », « Par rôle » ;
- statut (infobulle « Statut du dossier ») : « Ouverts et clos » / « Dossiers clos » / « Dossiers ouverts » ;
- période « Du [date] au [date] » (infobulle de « Du » : « Date d'arrivée du dossier ») ; un dossier sans date
  d'arrivée n'est jamais exclu par la période.

Rangée 2 : qualité « Toutes qualités » / « CODE — nom » (infobulle « Ne garder que les fils de la recette d'une
qualité ») ; 5 listes **liées** « Toutes compositions », « Tous titrages », « Tous types de fil », « Toutes
couleurs », « Tous fournisseurs » (chaque liste ne propose que les valeurs compatibles avec les autres choix,
tri naturel) ; bouton « + Combinaison » (grisé tant qu'aucun critère ; infobulle « + Ajouter cette
combinaison : la retenir, puis en composer une autre ; le résultat les réunit ») ; lien « Effacer les filtres »
dès 2 filtres actifs (remet tout à vide, y compris qualité, période, texte, statut, matières, combinaisons).

Bandeau `.reunion` : « Matières : » puces (× infobulle « Retirer cette matière ») ; « Réunion de : » puces
« PES · 1500 » (× « Retirer cette combinaison ») ; « + en cours : … ».

Règles serveur : les critères d'une combinaison se cumulent (ET), les combinaisons se réunissent (OU) ; qualité
∩ matières choisies (vide si aucune commune) ; erreurs 400 « axe inconnu : « X » (attendu : …) », « sélection
illisible : … », « la sélection doit être une liste de combinaisons », « critère inconnu dans la sélection :
… » ; 404 « qualité inconnue ou sans recette : « X » ».

#### 3.2 Indicateurs (Regroupé / Lot par lot)

| Indicateur | Valeur | Détail | Clic |
|---|---|---|---|
| Poids | `N kg` | « N lot(s) » | — |
| Coût hors TVA (ok) | montantCourt(Σ revient) | infobulle exact ; « x,xx MAD / kg · achat + charges » | — |
| Achat | montantCourt | « marchandise, en MAD » | — |
| Charges hors TVA (attention) | montantCourt | « x % de l'achat » + lien rouge « + N non répartis » (infobulle « Frais saisis sans marchandise où se répartir, dans aucun coût : 03/26 (1 200 MAD), …. Cliquer pour ouvrir le dossier. ») | ouvre la fenêtre du **premier** dossier listé |
| Coût TTC | montantCourt | « dont TVA N MAD » | — |

Frais non répartis comptés pour un dossier seulement s'il répond aux critères (une de ses marchandises est
retenue, ou, vide, son numéro/libellé répond au seul texte) — `analyse_import.py:264-273`.

#### 3.3 Vue « Regroupé »

| Colonne | Contenu | Format |
|---|---|---|
| {libellé de l'axe} | valeur en gras (« — » si vide ; titrage = « valeur unité ») | `reference` si axe référence |
| Lots | nb de lignes | droite |
| Poids | `N kg` | droite |
| Achat MAD | Σ | droite |
| Charges hors TVA | Σ ; infobulle « x % de l'achat » | droite |
| Coût hors TVA | **Σ** | droite |
| Coût hors TVA / kg | **revient / poids** ; note « achat x,xx » (achat/kg) | droite |
| TVA | Σ | note |
| Coût TTC | Σ | note |
| Dossiers | 4 premiers n° (boutons → fenêtre du dossier §2) « · » + « +N » (infobulle liste complète) | note |

Tri : coût hors TVA décroissant. Ligne `cliquable` (infobulle « Voir ses références une à une ») seulement si
l'axe est composition, titrage, type de fil, couleur ou fournisseur : pose ce filtre (titrage = premier mot) et
passe l'axe à « Référence ». Pied « Total » si > 1 ligne : Lots, Poids, Achat, Charges, Coût, Coût/kg
(recalculé), TVA, TTC. Vide : « Aucune marchandise importée ne répond à ces critères. »

#### 3.4 Vue « Lot par lot »

Colonnes : Dossier (lien → fenêtre ; étiquette « ouvert » si dossier ouvert), Arrivée, Référence, Lot (mono ou
« — »), Fournisseur, Titrage (note ou « — »), Poids (kg), Achat MAD, Charges hors TVA (infobulle « x % de
l'achat »), Coût hors TVA (gras), Coût hors TVA / kg (`revient_kg` gras + note « achat x,xx » =
`valeur_unite`), TVA, Coût TTC. Tri : date d'arrivée puis dossier, décroissants. Pied « Total » (sur 6
colonnes) puis Poids…TTC. Vide : « Aucune marchandise importée ne répond à ces critères. » Lignes non
cliquables.

#### 3.5 Vue « Recette d'une qualité »

Filtres : qualité « Choisir une qualité… » / « CODE — nom » (infobulle « Qualité de tapis ») ; période ; note
« N matière(s) importée(s) sur M dans la recette ». Sans qualité : « Choisir une qualité : on croise sa recette
(quels fils, dans quelle proportion) avec ce que ces fils ont coûté, rendus usine, dans les dossiers
d'importation. »

Indicateurs : « Coût matière / m² » (ok) `cout_m2_estime` MAD, détail « recette × coût hors TVA de chaque fil ·
x,xxx kg / m² » ; « Coût / kg de tapis » `cout_kg_tapis` MAD, détail « pondéré par la recette · sans {rôles} » ou
« pondéré par la recette (rôles en kilos) » ; « Recette couverte » `couverture` % (attention si < 99,9 %),
détail « du poids : N fil(s) importé(s) sur M » ; « Poids importé » kg, détail « N lot(s) · {coût} hors TVA ».

Tableau : Référence, Rôle, Part du rôle (infobulle « La part de ce fil dans son rôle : les parts d'un rôle font
100 % ») `x,x %`, kg / m² (infobulle « Poids du rôle au m² × part du fil ») 4 déc., Lots, Poids, Achat MAD,
Charges hors TVA, Coût hors TVA, Coût hors TVA / kg, Coût / m² (infobulle « kg au m² (un cuir, des franges, un
ruban : leurs ml/m² × la densité) × coût hors TVA au kilo »), Dossiers. Pied : une ligne par rôle « Rôle X » ·
« N fil(s) importé(s) sur M » · kg/m² du rôle · note « aucun fil importé : rôle hors du coût calculé » / « coût
connu sur x % du rôle, étendu au reste » / « coût connu pour tout le rôle » + « · rôle au mètre (ml/m²), hors du
poids au m² » · coût/m² du rôle `cout_m2 / connu_m2 × poids_m2` ; dernière ligne « Coût matière de la
qualité » · poids_m2 · `cout_m2_estime`. Vide : « Aucun fil de cette recette n'a encore été importé dans un
dossier. »

Formules serveur (`analyse_import.py:325-415`) : par fil de recette, `poids_m2 = poids du rôle × % / 100` ;
rôle : `connu_m2 = Σ poids_m2 des fils importés`, `cout_m2 = Σ kg_par_m2 × coût hors TVA / kg` ;
`cout_m2_estime = Σ_rôles connus (cout_m2 / connu_m2 × poids_m2)` ; `couverture = Σ connu / Σ poids` (rôles en
kilos seulement) ; `cout_kg_tapis = Σ_rôles kg connus (cout_m2/connu_m2 × poids_m2) / Σ poids_m2 de ces rôles` ;
`roles_sans_cout` = rôles sans fil importé.

#### 3.6 Gestes de l'analyse

| Geste | Rôle | Conditions | Appel | Effet |
|---|---|---|---|---|
| Bascule de vue | achats | — | relit | — |
| « Exporter en Excel » | achats | hors vue qualité | `GET /api/export/revient` | classeur |
| « + Ajouter une matière… » / × | | | relit | puces |
| « + Combinaison » / × | | grisé sans critère | relit (`selection` JSON) | |
| « Effacer les filtres » | | ≥ 2 filtres | | tout vidé |
| Clic ligne (Regroupé) | | axe combinable | | filtre + axe Référence |
| n° de dossier | | dossier connu (`ids_dossiers`) | `GET /api/dossiers/{id}` | fenêtre §2 (tous ses gestes) |
| « + N non répartis » | | s'il y en a | | fenêtre du 1er dossier |

---

### 4. Réglages › Postes de frais — `/reglages?onglet=postes` (`ReglagesPostesFrais.tsx`)

- **Rôles** : onglet « Postes de frais » (court « Frais ») réservé à la **direction** (`pages/Reglages.tsx:86`,
  les achats ne voient que « Devises ») ; serveur GET `ACHATS`, écritures `DIRECTION`. Sous-titre « Les frais
  d'un dossier d'importation : récupérables ou non, répartis à la valeur ou au poids. »
- **Où les postes s'affichent ailleurs** : liste « Poste » et ligne d'ajout de l'onglet Frais du dossier
  (« {libellé} — hors coût / à la valeur / au poids ») ; infobulle détail par poste de la colonne Charges
  (Marchandises) ; « Quoi » de l'échéancier ; feuille « Frais » de l'export ; `GET /api/postes-frais` (liste
  simple, tout acteur).
- **Données** : `GET /api/postes-frais/complet` (avec usage). Chargement « Un instant — chargement : les postes
  de frais… » ; erreur en rouge.
- Carte « Postes de frais d'importation », bouton « Nouveau poste ». Note : « Un frais global d'un dossier se
  répartit entre ses marchandises **à la valeur** (au prorata de ce que vaut chaque marchandise) ou **au poids**
  (au prorata de ses kilos), selon le réglage de son poste. Un poste récupérable (la TVA) reste hors du coût.
  Changer une clé recalcule les dossiers ouverts ; les dossiers clos gardent leur répartition. Cliquer sur un
  poste pour le modifier. »

| Colonne | Contenu | Format |
|---|---|---|
| Ordre | ordre | droite |
| Code | **code** + étiquette « calculs » (postes système ; infobulle « Lu par les calculs du dossier (TVA attendue) : il ne se supprime pas et garde sa nature ») | mono |
| Libellé | libellé | |
| Répartition | récupérable : « — » ; sinon étiquette « au poids » (accent) / « à la valeur » (neutre) | |
| Nature | étiquette « récupérable, hors coût » (attention) ou « coût » | |
| Frais saisis | nb de frais | droite |
| Dossiers ouverts | nb | droite |
| Dossiers clos | nb | droite |

Tri : ordre puis code. Ligne cliquable (infobulle « Modifier le poste »). Pas de recherche, pas de vide prévu.

**Fenêtre « Poste {CODE} — {libellé} » / « Nouveau poste de frais »** (`sale` → « Abandonner les
modifications ? ») :

| Champ | Type | Aide | Contrôle |
|---|---|---|---|
| Code | texte mono, majuscules, max 16 ; figé en modification | « le code ne change pas : les frais le portent » / « lettres, chiffres ou « _ » (ex. MANUT) » | serveur `[A-Z0-9_]{1,16}` : « Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT). » ; « Le poste « X » existe déjà. » (409) |
| Libellé | texte max 80 | | obligatoire (« le libellé est obligatoire ») |
| Répartition | « à la valeur » / « au poids » | « au prorata de la valeur de chaque marchandise, ou de ses kilos » | |
| Ordre | nombre 0-999 | « place dans les listes ; vide : à la fin » | vide → max + 1 |
| case « récupérable : hors du coût (comme la TVA) » | case | grisée si poste système ou porté par un dossier clos (infobulle = raison) ; note « Nature figée : les calculs du dossier lisent ce poste ainsi. » / « Nature figée : il porte des frais dans N dossier(s) clos : créer un autre poste. » | serveur : « « {libellé} » est récupérable/un coût par nature : les calculs du dossier (TVA attendue) le lisent ainsi. » ; « Ce poste porte des frais dans N dossier(s) clos : changer sa nature changerait leur coût. Créer un autre poste. » (409) |

Changement de clé en modification → message info « Les N dossier(s) ouvert(s) seront recalculés {au poids}. Les
N dossier(s) clos gardent leur coût : leurs frais de ce poste seront éclatés sur leurs marchandises, {à la
valeur} (c'est tracé). » Serveur : dans chaque dossier clos (≥ 2 lignes), chaque frais global non figé reçoit
ses parts à l'ancienne clé (valeur MAD au cours de la ligne, ou kilos), sans arrondi ; journal « frais figés » ;
refus période close pour un dossier **ouvert** touché (« (changement du poste « X » refusé) »).

| Geste | Rôle | Conditions | Confirmation | API | Succès | Refus |
|---|---|---|---|---|---|---|
| « Nouveau poste » | direction | — | — | — | fenêtre | — |
| clic ligne | direction | — | — | — | fenêtre | — |
| « Supprimer » (danger) | direction | grisé si système (« Ce poste sert aux calculs du dossier : il ne se supprime pas ») ou porte des frais (« Ce poste porte N frais dans des dossiers : il ne se supprime pas ») ; sinon infobulle « Supprimer ce poste, qui ne porte aucun frais » | « Supprimer ce poste ? » · « Non » · « Oui, supprimer » | `DELETE /api/postes-frais/{code}` | fenêtre fermée | « « X » sert aux calculs du dossier : il ne se supprime pas. » ; « Ce poste porte des frais dans des dossiers : il ne se supprime pas. » (409) ; « Poste de frais introuvable. » |
| « Annuler » | | | | | | |
| « Enregistrer » / « Créer le poste » | direction | grisé si libellé ou code vide, envoi, ou (modif) rien changé | — | `PUT /api/postes-frais/{code}` / `POST /api/postes-frais` | fenêtre fermée, dossiers rechargés | ci-dessus |

### 5. Réglages › Codes douaniers — `/reglages?onglet=codes` (`ReglagesCodesDouaniers.tsx`)

Direction seule (onglet court « Douane », sous-titre « Les positions du tarif douanier et leur taux de droits :
de quoi prévoir et vérifier les droits d'un dossier. ») ; serveur GET `ACHATS`, écritures `DIRECTION`.
Carte « Codes douaniers », bouton « Nouveau code », note « La position du tarif douanier et son taux de droits.
Chaque matière porte son code (fiche matière, au catalogue) : un dossier d'importation en déduit les droits
attendus — taux × valeur en douane (achat + fret) — et signale l'écart avec la quittance. » Recherche à la
frappe (code, libellé ; placeholder « Code, libellé… »), compteur « N code(s) ». Colonnes : Code (mono gras),
Libellé (ou « — »), Taux de droits (% 1 déc.), Matières (nb), État (« actif » ok / « désactivé » neutre). Ligne
cliquable (« Modifier le code »). Vide : « Aucun code ne correspond. » / « Aucun code douanier. « Nouveau code » :
5402.47.00.00 (fils de polypropylène), son taux de droits… »

Fenêtre « Code douanier {code} » / « Nouveau code douanier » (`sale`) : Code (max 20 ; aide « N matière(s) le
portent : elles suivront la correction » ou « chiffres et points (ex. 5402.47.00.00) » ; serveur « un code
douanier s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00) », ≥ 2 car., unicité « Le
code douanier « X » existe déjà. ») ; Libellé (`duo`, max 160, placeholder « Fils de polypropylène… ») ; Taux de
droits (%) (saisi en %, stocké 0-1, pas 0,1, placeholder « ex. 10 », aide « sur la valeur en douane : achat +
fret » ; message rouge « Un taux de droits va de 0 à 100 %. ») ; case « code actif (proposé dans la fiche
matière) ». Gestes : « Supprimer » (grisé si des matières le portent, infobulle « N matière(s) portent ce code :
le leur retirer, ou le désactiver » / « Supprimer ce code, qu'aucune matière ne porte » ; « Supprimer ce code ? »
· « Oui, supprimer » ; serveur « N matière(s) portent ce code : le leur retirer d'abord, ou le désactiver. ») ;
« Annuler » ; « Enregistrer » / « Créer le code » (grisé si code vide, taux vide ou hors 0-100 %, ou rien changé).
Un code désactivé compte « sans code » pour les droits attendus.

---

### 6. Liens sortants (récapitulatif)

| Depuis | Vers |
|---|---|
| en-tête Importations « Analyse du coût de revient » | `/analyse?onglet=revient` |
| liste des dossiers (ligne) | `/importations?dossier=ID` (même page) |
| « N arrivée(s) attendent leur dossier » | `/importations?onglet=rattacher` |
| « Saisir la facture » | `/receptions?reception=ID` |
| succès d'ouverture / rattachement | `/importations?dossier=ID` (onglet ouverts) |
| analyse : n° de dossier, « + N non répartis » | fenêtre du dossier en place (pas d'adresse) |
| Exports | `/api/export/dossiers?statut=…`, `/api/export/revient?…`, `/api/piece/{id}/fichier` |

Aucun lien depuis le dossier vers la réception, la commande (bon), la matière ou le lot.

### 7. Cas vides et chargements (récapitulatif des textes)

« Un instant — chargement : les dossiers… » · « … : ce qui attend un dossier… » · « … : le dossier… » ·
« … : l'analyse… » · « … : les postes de frais… » · « … : les codes douaniers… » ; et tous les textes de vide
cités aux §1-5.

### 8. Refus serveur des créations / rattachements (exacts)

- `POST /api/dossiers` : « Facture inconnue. » (404) ; « Cette facture a déjà son dossier, {NN/AA} : un dossier
  par facture. Ce qui en reste à rattacher (un second camion) s'y ajoute. » (409) ; « La facture {F} est déjà dans
  le dossier {NN/AA} (repris de l'ancien ERP) : une facture ne se partage pas entre deux dossiers. Ce qui en reste
  à rattacher s'y ajoute. » ; « {fournisseur} est un fournisseur marocain : ni douane, ni fret international, sa
  facture {F} n'a normalement pas de dossier d'importation. L'ouvrir quand même se confirme. » (409) ; « La
  facture « {F} » n'a plus de marchandise à rattacher : elle est déjà dans un dossier, ou ses réceptions ne sont
  pas validées. » (409) ; « Le dossier « X » existe déjà. » ; concurrence : « Un autre poste vient d'enregistrer
  cette facture dans le dossier {NN/AA} : l'ouvrir pour la suite (rien n'est perdu). » ou « Un autre poste vient
  d'enregistrer la même chose (même numéro de dossier, ou même marchandise) : recharger la page, puis
  reprendre. » ; période close : « La marchandise rattachée est entrée le jj/mm/aaaa, dans la période close
  jusqu'au jj/mm/aaaa : son coût a été rendu avec le mois et ne change plus (ouverture du dossier refusé). Pour
  corriger ce mois, la direction rouvre la période (Réglages › Période close jusqu'au — c'est tracé), on saisit,
  puis elle la referme. » (409 ; pour un dossier existant : « La marchandise du dossier {NN/AA} est entrée… »).
- `POST /api/dossiers/{id}/rattacher` : clos ; « Ce dossier est saisi à la main (d'avant la mise en service) :
  une marchandise reçue entre par sa facture, dans le dossier de cette facture. » ; « Un dossier, une facture :
  {NN/AA} est celui de la facture {F}. La facture {G} ouvre son propre dossier. » ; « Le dossier {NN/AA}, repris de
  l'ancien ERP, ne prend que la suite des factures qu'il porte déjà. La facture {G} ouvre son propre dossier. » ;
  (lignes, non utilisées par l'écran) « Une des lignes choisies est déjà dans un dossier, ou n'est pas une
  réception validée. », « Un dossier, une facture : cette ligne n'est pas de la facture {F}. », « Le dossier
  {NN/AA} ne prend que la suite des factures qu'il porte déjà : cette ligne n'en est pas. » ; « Rien à
  rattacher. » ; facture épuisée ; concurrence ; période close « (rattachement refusé) ». Un second camion entre
  au cours de son bon (ou sans cours) ; le journal note « plusieurs cours : … ».

---

### Incohérences et anomalies repérées

1. **Lien mort dans « Par famille de fil »** : « Ajouter une facture » envoie à l'onglet `facture`, qui n'existe
   que s'il y a un second camion ; sinon on retombe sur « Par famille de fil » sans rien voir. Le même texte
   propose « des lignes de réception », qui n'existent plus comme onglet (`DetailDossier.tsx:543-546` ; le
   commentaire d'en-tête `:5-6` parle encore de « des lignes (une partie d'une facture) »).
2. **TVA saisie : deux définitions.** L'encart TVA affiche « saisie » = Σ de **tous** les postes récupérables et
   calcule l'« écart » avec cette somme (`DetailDossier.tsx:1005, 1067, 1076`), alors que le cadre rouge, la
   liste et le serveur comparent le **seul poste TVA** (`tva_saisie_mad`, `importations.py:201` ;
   `ecartTva` `:142-149`). Avec un autre poste récupérable, on peut avoir un écart affiché sans cadre rouge, ou
   l'inverse.
3. **Valeur en douane mal décrite** : le serveur la calcule sur achat + fret + **assurance** (`importations.py:244`,
   `moteur.py:3572`), mais les infobulles et notes disent « achat + fret » (`DetailDossier.tsx:1023`,
   `ReglagesCodesDouaniers.tsx:4, 35, 134`).
4. **Taux figés dans le texte** : l'infobulle TVA écrit « la TPI 0,25 % » et « 20 % » vient du réglage, mais la TPI
   est un réglage (`parametres.py:108`) : le texte ment si on la change (`DetailDossier.tsx:1063`). Le seuil de
   l'écart des droits (2 %, au moins 50 MAD) n'existe **que dans l'écran** (`DetailDossier.tsx:110-115`), aucun
   contrôle serveur ne lui correspond, contrairement à la TVA (tolérance du serveur).
5. **Frais réglés modifiables sans le voir** : sur un dossier ouvert, la ligne de frais modifiable n'affiche pas
   « réglé le » (seulement en lecture, `DetailDossier.tsx:1283`), et le serveur accepte de modifier ou de
   retirer un frais déjà payé (`importations.py:991-1025`) : l'échéancier général perd alors son règlement.
6. **Montant de frais vidé = silence** : `enregistrer` ne fait rien si le montant est vide (`DetailDossier.tsx:1264`),
   sans message ; le champ reste vide (classe `manque`) alors que le serveur garde l'ancien montant.
7. **Boutons grisés sans raison** (règle §2 « ne pas laisser cliquer… grisé avec la raison ») : « Clôturer le
   dossier » sans marchandise (infobulle générique, `:316-317`) ; « Ajouter » d'un frais (`:1152`) ; « Ajouter
   au dossier » de la saisie à la main (`:1623`) ; « Appliquer aux {DEV} » (`:665`). Inversement, « Clôturer »
   n'est **pas** grisé quand il reste des frais non répartis (refus serveur `importations.py:1042`), même si le
   bandeau rouge le dit.
8. **Étiquette « à vérifier » incomplète** dans la liste : elle ignore les frais hors norme du dossier entier
   (`surcout_aberrant`, montré seulement en note dans la colonne Charges), les cours disparates et les cours
   éloignés (`Importations.tsx:263-270`), alors que l'avertissement de clôture les cite.
9. **Indicateurs ≠ totaux** sur la page : les indicateurs portent sur **tous** les dossiers (ouverts et clos,
   sans recherche, `Importations.tsx:75-80`), le pied de tableau sur les dossiers visibles de l'onglet : deux
   « Coût hors TVA » différents à l'écran, sans le dire.
10. **Second camion d'un fournisseur marocain introuvable depuis le dossier** : la fenêtre lit
    `dossiers-a-rattacher` sans `locaux` (`DetailDossier.tsx:166`), donc l'onglet « Second camion » n'apparaît
    jamais pour lui ; il faut passer par la page, case « Fournisseurs marocains » cochée.
11. **Texte vide pour un dossier repris** : « La facture {d.facture?.numero} est arrivée en plus d'un camion… »
    affiche « La facture  est arrivée… » quand le dossier n'a pas de facture (`DetailDossier.tsx:1486`).
12. **Retours du serveur perdus** : suppression d'un dossier sans message de succès (la fenêtre se ferme ;
    `frais_perdus` non utilisé, `DetailDossier.tsx:220-227`) ; changement de clé d'un poste sans message, le
    nombre de dossiers clos figés (`dossiers_figes`) n'est pas montré (`ReglagesPostesFrais.tsx:117-125`).
13. **Code mort / chemins inutilisés** : `voletInitial` jamais passé (`DetailDossier.tsx:154`) ; `interdit` et
    les tests `peut('achats')` de la page toujours vrais à cause de la garde (`Importations.tsx:91, 423`) ;
    rattachement par `reception_lignes` accepté par le serveur mais proposé par aucun écran
    (`importations.py:653-693`) ; champ `lignes` de `ARattacher` lu par aucun écran de ce périmètre ;
    `numero` et `facture_id` reçus par `PUT /dossiers/{id}` mais ignorés.
14. **Vocabulaire** (REGLES-ECRAN §3) : colonnes et champs « Commentaire » pour des remarques (règle :
    « Observations ») et aide « transitaire, n° de DUM, **remarques**… » (`DetailDossier.tsx:521`) ; la note de
    création dit pourtant « observations » (`Importations.tsx:659`). Libellé de répartition figée différent
    entre l'écran « figée (clé d'avant son changement) » (`DetailDossier.tsx:106`) et l'export « figée à la
    clôture » (`importations.py:1143`). Colonne « Lots » qui compte des lignes de réception
    (`Importations.tsx:494`).
15. **Filtres sans « Effacer les filtres »** : `ChoixFacture` a deux filtres (fournisseur + numéro), sans bouton
    d'effacement et sans liaison (la liste des fournisseurs ne suit pas le texte) — règle §2
    (`ChoixFacture.tsx:59-78`).
16. **État de l'analyse hors de l'adresse** : vue, axe, filtres, qualité de `AnalyseRevient` ne sont pas dans
    l'adresse : aucun raccourci ne peut ouvrir l'analyse « filtre posé » (M74) ; l'onglet de la fenêtre du
    dossier non plus.
17. **Longueurs non bornées à l'écran** : l'en-tête (libellé, banque, commentaire) n'a pas de `maxLength` alors
    que le serveur borne à 160 / 32 / 2000 → erreur 422 technique (`DetailDossier.tsx:501-513`).
18. **colSpan faux** : ligne vide de la vue Regroupé `colSpan={11}` pour 10 colonnes (`AnalyseRevient.tsx:666`).
19. **Échéancier incomplet après détachement** : l'échéancier ne prend que les factures des lignes présentes
    (`importations.py:241, 354`) ; un dossier dont toutes les réceptions ont été détachées perd sa facture
    marchandise de l'échéancier alors que l'en-tête la montre encore.
20. **Pièces jointes d'un dossier clos** modifiables (dépôt et retrait) alors que tout le reste du dossier clos est
    figé — voulu par le texte (« même clos ») mais à signaler pour la réécriture.

### Comptes

- **Écrans / pages** : 4 — la page `/importations`, et trois écrans logés dans d'autres pages : Coût de revient
  (`/analyse?onglet=revient`), Postes de frais (`/reglages?onglet=postes`), Codes douaniers
  (`/reglages?onglet=codes`).
- **Onglets / sous-vues** : 17 — 3 onglets de page (Dossiers ouverts, Dossiers clos, En attente de dossier) ;
  2 vues en bascule dans « En attente » ; 2 onglets dans la fenêtre de création ; 7 onglets dans la fenêtre du
  dossier ; 3 vues en bascule dans l'analyse.
- **Fenêtres / tiroirs** : 4 fenêtres (Nouveau dossier d'importation, Dossier {NN/AA} — ouverte depuis la page ou
  depuis l'analyse —, Poste de frais, Code douanier), plus un panneau d'édition en place (en-tête du dossier) et
  14 confirmations sur place.
- **Gestes inventoriés** : 59 (page 9, création 3, fenêtre du dossier 27 dont Documents 3, analyse 10, postes de
  frais 5, codes douaniers 5).

---

## Partie 6 — Inventaire et opérations de stock (ouvertures, transferts, ajustements, retours, libérations)

Sources lues en entier : `ecran/src/pages/Inventaire.tsx` (1247 l.), `ecran/src/pages/Operations.tsx` (1121 l.),
`gestion_mp/api/inventaires.py` (504 l.), `gestion_mp/api/operations.py` (457 l.), `gestion_mp/api/brouillons.py` (125 l.).
Consultés : `gestion_mp/securite.py` (droits, `date_permise`, `numero`), `gestion_mp/services/stock.py` (`ecrire`,
`transferer`, `couvert_a_sa_date`, `contrepasser_document`, `lot_ou_creer`), `gestion_mp/api/suivi.py` (pièces jointes),
`gestion_mp/api/production.py` (unités), `gestion_mp/main.py` (traduction des refus de saisie), `ecran/src/App.tsx` (menu,
gardes), `components/ui.tsx`, `components/PiecesJointes.tsx`, `components/stock/commun.tsx` + `stock.css`,
`pages/atelier/commun.tsx` (`Blocages`, unités, `quantite`), `pages/atelier/Retour.tsx` (`libelleMotif`), `lib/format.ts`, `lib/api.ts`.

Conventions communes aux deux écrans (rappel des composants, utile à la reconstruction) :

- `Dialogue … sale` : fermer (Échap, clic sur le fond, ×) une fenêtre « sale » affiche dans la fenêtre le bandeau
  « Des modifications ne sont pas enregistrées. Les abandonner ? » avec « Non, continuer la saisie » et « Oui, abandonner »
  (`components/ui.tsx:310-318`).
- `Confirmer` : le bouton se change sur place en « question · Non · Oui, … » (`ui.tsx:342-384`).
- `useEnvoi` : pendant l'appel `occupe` = vrai ; l'erreur serveur (champ `detail`) s'affiche en `Message ton="erreur"`,
  le succès en `Message ton="succes"` ; chaque nouvel envoi efface le message précédent (`ui.tsx:418-449`).
- Les refus de saisie Pydantic (422) sont traduits et préfixés du champ : « champ : texte » joints par « ; »
  (`gestion_mp/main.py:177-187`). Serveur injoignable : « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). »
  (`lib/api.ts:31`).
- Chargement : « Un instant — chargement : {quoi}… » (`ui.tsx:209-211`).
- Refus de droit générique (dépendance `ACHATS`) : « Cette action est réservée à : responsable achats. » (403,
  `securite.py:108-111`). La direction passe partout.
- Contrôle de date commun (`securite.py:210-225`, appelé partout où une date s'écrit) :
  - « Date trop ancienne ({jj/mm/aaaa}) : vérifier l'année. » (avant le 01/01/2000) ;
  - « Date dans le futur ({jj/mm/aaaa}) : un mouvement se saisit le jour où il a lieu. » ;
  - « La période jusqu'au {jj/mm/aaaa} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la
    direction de la rouvrir. » (réglage `date_cloture`, date ≤ limite refusée).
- Refus du moteur de stock (`services/stock.py`), pouvant tomber sur toute validation / annulation :
  - « Une écriture de stock ne peut pas être nulle. »
  - « Magasin inconnu. »
  - « Le magasin « {code} » est désactivé : il ne reçoit plus rien. » (seulement pour une entrée, quantité > 0)
  - **Suspension par inventaire** : « L'inventaire {numéro} est en cours sur « {code} » : les mouvements y sont suspendus
    jusqu'à sa validation. » (409 ; tout mouvement sauf ceux du document « inventaire » lui-même, sur le magasin compté ou
    sur tous si l'inventaire porte sur tous les magasins) (`stock.py:157-169`).
  - **Stock insuffisant** : « Le lot « {lot} » de « {référence} » ne porte que {x,xxx} kg dans « {code} », {y,yyy} kg
    demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là. » (409)
  - **Écriture antidatée** (`couvert_a_sa_date`, `stock.py:77-119`, pour toute sortie) :
    « Le lot « {lot} » de « {réf} » n'est entré dans « {code} » que le {jj/mm/aaaa} : une écriture datée du {jj/mm/aaaa}
    ne peut pas le prendre. La dater au jour où la matière était là, ou choisir un lot présent à cette date. »
    (variante « n'est jamais entré dans « {code} » ») ; ou « Au {date}, il n'y avait que {x} kg du lot « {lot} » de
    « {réf} » dans « {code} », {y} kg demandés au {date}[ : la matière est sortie depuis par d'autres écritures.|.]
    Choisir un autre lot, ou dater l'écriture après l'entrée de la matière. » (409)
  - « Un transfert va d'un magasin à un autre. »
  - « Ce document a déjà été annulé. » (409, contre-passation)
  - « Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne ». » (création de lot)

---

### PARTIE 1 — INVENTAIRE

#### Inventaire (page) — `/inventaire` (`?onglet=passes`, `?inventaire=ID`)

- **Fichiers** : `ecran/src/pages/Inventaire.tsx` (page `InventairePage` l.147-341) ; CSS `components/stock/stock.css` ;
  serveur `gestion_mp/api/inventaires.py`.
- **Rôles** :
  - Menu « Stock › Inventaire », rôles `['achats']` (+ direction) (`App.tsx:69`) ; garde de route `garde(['achats'])`
    (`App.tsx:257`) : un autre rôle est renvoyé à son accueil avec le bandeau « L'écran demandé (/inventaire) est réservé à
    un autre rôle : vous êtes revenu à votre accueil. » (`App.tsx:244-247`).
  - Bouton « Ouvrir un inventaire » affiché si `peut('achats')` (l.182).
  - Serveur : `GET /inventaires` ouvert à tout compte connecté (`acteur`) ; pour l'alimentation les valeurs en MAD sont
    `null` (`inventaires.py:123-127, 161-162`). Toutes les écritures (ouvrir, compter, valider, abandonner) : `ACHATS`.
- **Paramètres d'adresse** (l.153-165) : `?onglet=passes` (absent = « cours », l'onglet par défaut n'est pas écrit) ;
  `?inventaire=ID` ouvre la fenêtre de comptage par-dessus n'importe quel onglet ; écriture en `replace`. Après création
  d'un inventaire : `onglet` retiré, `inventaire=ID` posé (l.332-335).
- **Données** : `GET /api/inventaires` (liste, sans les lignes, du plus récent au plus ancien par id ; clé `['inventaires']`).
- **En-tête** : titre « Inventaire » ; sous-titre « On fige le stock théorique, on compte lot par lot, on valide : chaque
  écart devient un ajustement de stock tracé. Au-delà de la tolérance, un écart se justifie. » ; action « Ouvrir un
  inventaire » (principal). Pas d'indicateurs.
- **Onglets** (l.189-196) : « En cours de comptage » (compteur = nombre d'inventaires `statut = ouvert`) ; « Inventaires
  validés » (compteur = total − en cours).
- Erreur de lecture : `Message erreur` avec le texte serveur ; chargement : « Un instant — chargement : les inventaires… ».

##### Onglet « En cours de comptage » (`onglet` absent)

Carte « Inventaires en cours ». S'il y a au moins un inventaire ouvert, message info : « Tant qu'un inventaire est ouvert,
aucun mouvement ne s'écrit sur le magasin compté (réceptions, sorties, transferts, retours) — sur tous les magasins s'il
porte sur tout le stock. Valider ou abandonner l'inventaire rend la main. » Tableau dans `Cadre taille="court"`.

| Colonne | Contenu / unité | Alignement / format | Remarque |
|---|---|---|---|
| Inventaire | **numéro** (gras, ex. INV-2026-0003) + libellé en note dessous | texte | |
| Date | date du comptage | jj/mm/aaaa | |
| Magasin | code du magasin, ou « Tous les magasins » | texte | |
| Tolérance | tolérance | `num`, pourcentage 0 décimale (« 2 % ») | |
| Lots comptés | « nb_comptées / nb_lignes » | `num`, entiers | compté = un comptage retenu (premier ou second) |
| Hors tolérance | nombre de lignes hors tolérance | `num` ; Etiquette **critique** (rouge) si > 0, sinon « 0 » | |
| Écart à ce stade | écart net en kg « +12,3 kg » / « −4,0 kg » / « 0 kg » | `num`, 1 décimale, signe explicite (signe moins typographique « − ») | sans couleur ici |
| Valeur de l'écart (infobulle d'en-tête « Au coût moyen (CMUP) de chaque matière ; en dessous, la somme des écarts sans leur signe ») | valeur nette en MAD + note « {montant absolu} sans signe » si non nul | `num`, MAD entiers (« 1 234 MAD ») ; « — » si null | valorisé au CMUP du moment |
| Ouvert par | nom de qui a ouvert | texte | |

- Pas de recherche ni de filtre, pas de tri cliquable (ordre serveur : id décroissant), pas de pagination, pas de pied.
- Ligne cliquable (`cliquable`, infobulle « Ouvrir le comptage ») → pose `?inventaire=ID` (fenêtre Comptage).
- Vide : « Aucun inventaire en cours. « Ouvrir un inventaire » fige le stock d'un magasin (ou de tout le stock) pour le
  compter. »

##### Onglet « Inventaires validés » (`?onglet=passes`)

Carte « Inventaires validés ». Rangée `.filtres` : `BarreRecherche` placeholder « Numéro, libellé, magasin, personne… »,
filtre à la frappe (multi-mots, sans accents, `filtrer`) sur : numéro, libellé, magasin, ouvert par, validé par, date
formatée (l.171-175). La recherche n'est pas dans l'adresse ; elle survit au changement d'onglet. Tableau `Cadre court`.

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Inventaire | numéro gras + libellé en note | | |
| Date | date du comptage | jj/mm/aaaa | |
| Magasin | code ou « Tous les magasins » | | |
| Lots comptés | « comptées / lignes » | `num` | |
| Hors tolérance | nombre | Etiquette **attention** (orange) si > 0, sinon « 0 » | ton différent de l'onglet en cours |
| Écart total | écart net kg signé | `num` ; classe `ecart-moins` (rouge gras) si < −0,001, `ecart-plus` (vert gras) si > 0,001 | |
| Valeur de l'écart (infobulle « Au coût de chaque ajustement écrit ; en dessous, la somme des écarts sans leur signe ») | MAD net + note « {absolu} sans signe » | `num`, MAD | valorisé au coût unitaire de l'ajustement écrit (sinon CMUP) |
| Ouvert par | nom | | |
| Validé par | nom + note date-heure de validation (jj/mm/aaaa hh:mm) | | |

- Ligne cliquable (infobulle « Voir les écarts ») → `?inventaire=ID`.
- Vide : « Aucun inventaire validé. » ou, recherche saisie, « Aucun inventaire validé ne correspond. »
- Pas de bouton Effacer (un seul filtre), pas d'export, pas de tri.

##### Gestes de la page

| Geste | Où | Rôle | Conditions | Confirmation | Appel API | Succès | Refus |
|---|---|---|---|---|---|---|---|
| « Ouvrir un inventaire » | en-tête de page | achats, direction | toujours actif | — | — | ouvre la fenêtre « Ouvrir un inventaire » | — |
| Clic sur une ligne | les deux tableaux | idem | — | — | `GET /inventaires/{id}` | fenêtre Comptage | « Inventaire introuvable. » (404) dans la fenêtre |

---

#### Fenêtre « Ouvrir un inventaire » (Dialogue `tresLarge`, `sale={modifie}`)

- **Fichiers** : `Inventaire.tsx:347-640` (`OuvrirInventaire`).
- **Rôles** : achats / direction (bouton de page) ; `POST /inventaires` = `ACHATS`.
- **Données** : `GET /inventaires/defauts` (tolérance réglée, rôles et compositions qui portent du stock, cadences) ;
  `GET /magasins` ; `GET /articles` ; `GET /soldes?magasin_id=` (soldes en stock du magasin choisi, ou de tous) ;
  `GET /inventaires/a-compter?magasin_id=` (seulement si périmètre « tournant »).

**Formulaire** (rangée `formulaire`) :

| Champ | Type | Défaut | Contrôle / remarque |
|---|---|---|---|
| « Libellé » (duo) | texte | vide ; placeholder « Inventaire {code} » si un magasin est choisi, sinon « Inventaire de fin de mois, tournant… » | max 120 car. au serveur. Vide → libellé automatique : « Inventaire tournant » (périmètre tournant), sinon « Inventaire {code magasin} », sinon « Inventaire de tout le stock » (l.417-419) |
| « Date du comptage » | date | aujourd'hui | `max` = aujourd'hui ; obligatoire (bouton grisé si vide) ; serveur `date_permise` + contrôle « a bougé après » |
| « Magasin compté » | liste | « Tous les magasins » (valeur vide) | magasins actifs : « {code}[ (quarantaine)] — {stock} kg » |
| « Tolérance (%) » (aide « au-delà, l'écart se justifie ; proposée par les réglages ») | nombre (`SaisieNombre`, peut rester vide) | réglage `tolerance_inventaire` × 100 arrondi à 2 décimales (réglage d'usine 2 %) | vide → bouton grisé ; envoyée /100 ; serveur 0 ≤ tolérance ≤ 1 (sinon refus Pydantic « tolerance : … ») |

**Périmètre** — rangée « **Ce qu'on compte :** » (boutons radio) :
1. « Tout le stock » (+ « de ce magasin » si un magasin est choisi) — défaut.
2. « Par rôle, composition ou classe ABC » → bloc :
   - « Rôles » : cases à cocher (rôles des matières en stock, triés) ; « — » si aucun ;
   - « Compositions » : cases (compositions des matières en stock) ;
   - « Classes ABC » (aide « A : l'essentiel de la valeur consommée ») : cases « Classe A », « Classe B », « Classe C » ;
   - note « Une matière est comptée si elle passe tous les critères cochés. » (ET entre familles de critères, OU à
     l'intérieur d'une famille). Aucun critère coché → bouton grisé.
3. « Certaines matières » → champ « Ajouter une matière à compter » : recherche à la frappe (`ChoixRecherche`, placeholder
   « Taper quelques mots de la référence… ») parmi les matières de stock global > 0 non encore choisies ; libellé
   « RÉF — désignation » ; détail « {kg} kg[ ≈ N ml] en stock ». Les choisies en puces « RÉF × » (bouton × aria
   « Retirer RÉF ») ; vide : « Aucune matière choisie. » (bouton grisé).
4. « Inventaire tournant (matières dues) » → note « Les matières en stock dont le dernier comptage validé est plus vieux que
   la cadence de leur classe : A tous les 30 jours, B tous les 90 jours, C tous les 365 jours. Décocher celles qu'on ne
   compte pas cette fois. » puis :
   - chargement « Un instant — chargement : les matières dues… » ;
   - vide : message succès « Aucune matière n'est due : toutes ont été comptées à temps. » (bouton grisé) ;
   - sinon tableau `Cadre dialogue`, `table.serre` :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| (case) | case cochée = retenue | | décocher → ligne éteinte (`ligne-eteinte`, gris) |
| Référence | référence | `reference` | |
| Rôle | rôle de la matière | | |
| Classe | classe ABC en gras | | classe inconnue → C |
| Stock | stock dû (somme des magasins dus) « kg[ ≈ ml] » | `num`, 0 décimale | |
| Dernier comptage | « jj/mm/aaaa (il y a N j) » ou « jamais compté » + note des magasins dus joints par « · » (infobulle « Un comptage vaut pour le magasin compté : la matière est due dans ces magasins ») | | le plus ancien des magasins dus (jamais compté l'emporte) |

   Tri serveur : classe A→C, puis dernier comptage (jamais d'abord), puis référence. Règle serveur (`inventaires.py:194-244`) :
   une matière est due dans un magasin si elle y a > 0,001 kg et que son dernier comptage **validé avec quantité** dans
   ce magasin date de ≥ cadence (A 30 j, B 90 j, C 365 j) ou n'existe pas.

**Message d'information calculé en direct** (l.601-610) : « Calcul… » pendant la lecture des soldes, sinon :
- famille avec classes cochées : « Les lots des matières retenues seront figés au théorique (la classe ABC se calcule à
  l'ouverture). »
- sinon « {N} lot(s) en stock seront figés au théorique. » (N = soldes retenus ; par magasin choisi 1 par lot, sinon un par
  magasin du lot)

suivi de « Pendant le comptage, les mouvements sont **suspendus** sur {le magasin CODE | tous les magasins} : réceptions,
sorties vers les machines, transferts et retours attendront la validation (ou l'abandon) de l'inventaire. Ouvrir
l'inventaire au moment de compter, pas avant. »

**Conflit** (l.400, 611-616) : si un inventaire ouvert porte sur le même magasin, ou sur tous, ou si on ouvre sur tous alors
qu'un inventaire est ouvert : message erreur « L'inventaire {numéro} ({magasin}) est déjà ouvert sur ce périmètre : le
valider ou l'abandonner d'abord. » et bouton grisé.

**Gestes**

| Geste | Où | Rôle | Conditions / grisé | Confirmation | Appel API | Succès | Refus (serveur) |
|---|---|---|---|---|---|---|---|
| « Annuler » | pied | — | — | si saisie modifiée : « Abandonner cette saisie ? » / « Oui, abandonner » (infobulle « Fermer sans ouvrir l'inventaire ») | — | ferme | — |
| « Ouvrir et figer le stock » (principal) | pied | achats | grisé si envoi en cours, conflit, date vide, ou incomplet (Certaines matières sans matière, tournant sans matière retenue, famille sans critère, tolérance vide) ; infobulle fixe « Ouvre l'inventaire : le théorique est figé, les mouvements du magasin attendent » | « Figer le stock {de CODE \| de tous les magasins} et suspendre ses mouvements ? » / « Oui, ouvrir l'inventaire » | `POST /inventaires` {libelle, date, magasin_id, tolerance, articles[], roles[], compositions[], classes_abc[]} | ferme la fenêtre, ouvre le Comptage du nouvel inventaire (`?inventaire=ID`) | « Cette action est réservée à : responsable achats. » ; contrôles de date ; « Magasin inconnu. » ; « L'inventaire {numéro} est déjà ouvert sur ce magasin. » (409) ; « Matière inconnue : n° x, y. » ; « Classe ABC : A, B ou C. » ; « L'inventaire est daté du {date}, mais des lots qu'il fige ont bougé depuis : « RÉF », lot X (le jj/mm/aaaa), … [ …]. Un comptage porte sur le stock d'aujourd'hui : le dater au plus tôt du dernier mouvement. » (409, 5 lots cités au plus) |

**Serveur à l'ouverture** (`inventaires.py:268-317`) : numéro `INV-{année de la date}-{NNNN}` donné **dès l'ouverture** ;
libellé vide → « Inventaire » ; une ligne par solde (lot × magasin) > 0 du périmètre, `théorique` = solde (verrouillé
pendant la lecture) ; journal « ouverture inventaire » « {numéro} · N lot(s) figés ».

---

#### Fenêtre « Comptage » d'un inventaire (Dialogue `tresLarge`, `sale={lignes modifiées > 0}`) — `?inventaire=ID`

- **Fichiers** : `Inventaire.tsx:654-1115` (`Comptage`).
- **Rôles** : lecture pour tous ceux qui ouvrent la page ; **saisie** (`saisie`) seulement si inventaire ouvert ET
  `peut('achats')` (l.681). Inventaire validé = lecture seule (aucun bouton d'écriture).
- **Données** : `GET /inventaires/{id}` (avec lignes) ; `GET /pieces/inventaire/{id}` (compteur des pièces).
- Avant réception : fenêtre « Inventaire » avec « Un instant — chargement : l'inventaire… » ou le message d'erreur
  (« Inventaire introuvable. »).
- **Titre** : « {numéro} · {libellé} » + Etiquette « Comptage en cours » (attention) ou « Validé par {nom} » (ok).
- **Barre** (`barre-dialogue`) : note « {magasin} · compté le {jj/mm/aaaa} · tolérance {N %} · ouvert par {nom}[ · validé le
  {jj/mm/aaaa hh:mm}] », puis les boutons (à place fixe, libellés constants).

**Indicateurs** (l.898-919, recalculés en direct avec les saisies non enregistrées) :

| Indicateur | Valeur affichée | Détail / formule | Ton | Clic |
|---|---|---|---|---|
| « Lots figés » | nombre de lignes (lots trouvés compris) | — | — | — |
| « Comptés » | « c / n » | « {c/n en %, 0 déc.} du comptage » | ok si tout est compté | — |
| « Hors tolérance » | nombre de lignes hors tolérance (sur le comptage retenu) | « N sans justification » sinon « tous justifiés » si > 0 | rupture s'il en manque, attention s'il y en a, ok sinon | — |
| « À recompter » | lignes dont le **premier** comptage est hors tolérance et sans recomptage | « {N} recompté(s) · le recomptage ajuste » | attention si > 0, sinon ok | — |
| « Écart total » | « ±x,x kg » | « retenu − théorique, lots comptés » | — | — |

Note de saisie (si `saisie`) : « Saisir le poids compté en kg (le cuir, les franges et le ruban aussi), ou les palettes et
bobines : le poids se calcule avec le poids de bobine du lot. Une ligne laissée vide n'est pas comptée et ne sera pas
ajustée. Un écart hors tolérance en rouge demande une justification. » (« en rouge » en classe `ecart-moins`).

**Bascule** (l.948-960) : « Lots à compter ({nb lignes}) » | « Pièces jointes[ ({nb})] ». Sur « Pièces jointes », note
« La feuille de comptage signée, scannée ; une photo d'un lot trouvé ou abîmé. » et le composant `PiecesJointes`
(voir plus bas). La bascule n'est pas dans l'adresse.

##### Sous-vue « Lots à compter »

Rangée `.filtres` : `BarreRecherche` placeholder « Référence, lot, magasin… » (à la frappe, sur référence, désignation,
lot, magasin) ; liste de vues (l.967-975) avec compteurs en direct :
« Tous les lots (n) » (`toutes`, défaut si ouvert) · « À compter (n) » (compté vide) · « Comptés (n) » · « Avec un écart (n) »
(|écart| ≥ 0,001 ; **défaut si validé**) · « Hors tolérance (n) » · « À recompter (n) » · « Non enregistrés (n) » (seulement
en saisie : lignes modifiées localement). Puis note « {N} ligne(s) ». Pas de bouton « Effacer les filtres ».

Tableau `Cadre dialogue`, `table.serre.saisie` :

| Colonne | Contenu / unité | Format | Remarque |
|---|---|---|---|
| Référence | référence + désignation en note ; infobulle « RÉF — désignation » | `reference` | |
| Lot | numéro de lot (mono) + note « trouvé, non prévu » si théorique = 0 | mono | |
| Magasin | code | | **seulement** si l'inventaire porte sur tous les magasins |
| Théorique (kg) | théorique figé | `num`, 1 déc. ; notes « ≈ N ml » (cuir, franges, ruban) et « ≈ N bobines » (si poids de bobine connu) | |
| Palettes | saisie nombre (classe court) + note « × {bobines/palette} bob. » | `num` | seulement en saisie ; champ si poids de bobine > 0 ET bobines/palette > 0, sinon « — » |
| Bobines | saisie nombre + note « × {poids bobine, 4 déc.} kg » (infobulle « Le poids de bobine du lot, tel qu'il sert au calcul ») | `num` | seulement en saisie ; champ si poids de bobine > 0, sinon « — » |
| Compté (kg) | saisie (placeholder « non compté », classe moyen) ; en lecture : valeur 1 déc. ou note « non compté » | `num` | |
| Recompté (kg) (infobulle d'en-tête « Un écart hors tolérance se recompte, par une autre personne : ce second comptage ajuste ») | saisie (placeholder « à recompter ») si saisie ET compté renseigné ET (à recompter OU déjà recompté) ; sinon valeur ou « — » ; note « par {nom} » (+ « — la personne qui a ouvert l'inventaire : un recomptage se fait à quatre yeux » si c'est l'ouvreur), masquée si le recomptage vient d'être modifié localement | `num` | |
| Écart (kg) | retenu − théorique, signé (« +x,x », « −x,x », « 0 », « — ») | `num` ; rouge `ecart-moins` / vert `ecart-plus` **seulement si hors tolérance** | |
| Écart | Etiquette : « juste » (ok) si |écart| < 0,001 ; sinon % de l'écart sur le théorique (1 déc.) ou « non prévu » si théorique 0 — ton critique si hors tolérance, neutre sinon ; « — » si non compté | `num` | |
| Justification | saisie texte (placeholder « Obligatoire : ce qui a été constaté » si hors tolérance ; classe `manque` rouge si obligatoire et < 3 caractères) ; en lecture : note texte ou « — » | | |

- Teintes de ligne : `ligne-alerte` (fond rouge pâle) si hors tolérance sans justification ; sinon `ligne-modifiee` (fond
  orangé) si modifiée localement et non enregistrée.
- Vide : « Aucune ligne dans cette vue. » ; inventaire sans aucune ligne : « Aucun lot en stock dans ce périmètre : ajouter
  les lots trouvés. »
- Pas de tri, pas de pagination, pas de pied de tableau. Les valeurs en MAD par ligne (`cmup_mad`, `valeur_ecart_mad`)
  ne sont **pas** affichées.

**Calcul en direct à la saisie** (l.686-756) :
- Brouillon local par ligne {compté, justification, palettes, bobines, recompté}. Saisir palettes ou bobines recalcule
  **Compté = arrondi 2 déc. de (palettes × bobines/palette + bobines) × poids de bobine du lot** (si les deux sont vides, le
  compté précédent reste) ; saisir directement le compté efface palettes et bobines. Une ligne revenue aux valeurs du
  serveur n'est plus « modifiée ».
- **Retenu** = recompté s'il existe, sinon compté. **Écart** = retenu − théorique.
- **Hors tolérance** : compté renseigné, |écart| ≥ 0,001 kg, et (théorique ≤ 0 ou |écart| / théorique > tolérance) —
  même règle qu'au serveur (`inventaires.py:40-46`).
- **À recompter** : pas de recomptage et le **premier** comptage est hors tolérance.
- **Justification manquante** : hors tolérance (sur le retenu) et justification de moins de 3 caractères.

##### Gestes de la fenêtre Comptage

| Geste | Où | Rôle | Conditions / grisé (infobulle) | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| « Feuille de comptage » | barre | tous | toujours (même validé) ; infobulle « La feuille à imprimer pour compter sur place, sans le théorique (comptage à l'aveugle) » | — | ouvre un onglet `GET /api/inventaires/{id}/feuille` | document imprimable | « Inventaire introuvable. » |
| « Feuille de recomptage » | barre | tous | grisé si aucune ligne à recompter (infobulle « Aucun lot à recompter ») ; sinon infobulle « {N} lot(s) hors tolérance à recompter, avec le théorique : pour la personne qui recompte » | — | onglet `GET /api/inventaires/{id}/feuille?recomptage=true` | document | idem |
| « Lot trouvé… » | barre | saisie | bascule l'encart ; infobulle « Refermer la saisie du lot trouvé » / « Un lot trouvé sur place, absent du théorique » | — | — | encart « Lot trouvé » | — |
| « Abandonner » (danger) | barre | saisie | grisé pendant l'envoi ; infobulle « Abandonner l'inventaire sans rien ajuster » | « Abandonner ? Rien n'est ajusté, les comptages sont perdus, les mouvements reprennent. » / « Oui, abandonner » | `DELETE /inventaires/{id}` | fenêtre fermée, liste rafraîchie (aucun message) | « Un inventaire validé reste : ses ajustements sont au journal. » (409) ; « Inventaire introuvable. » ; droit achats |
| « Enregistrer le comptage » | barre | saisie | grisé si rien de modifié ou envoi ; infobulle « {N} ligne(s) à enregistrer » / « Rien à enregistrer » | — | `POST /inventaires/{id}/comptage` [{ligne_id, compte, palettes, bobines, second_compte, justification}] (lignes modifiées seulement) | « {N} comptage(s) enregistré(s). » ; brouillons vidés | « Cet inventaire est déjà validé. » (409) ; « Ligne étrangère à cet inventaire. » ; « « RÉF », lot X : un recomptage suit un premier comptage. » ; Pydantic (compté ≥ 0 et ≤ 1e9, palettes ≤ 1e5, bobines ≤ 1e6, justification ≤ 300 car.) |
| « Valider l'inventaire » (principal) | barre | saisie | grisé si envoi, aucun lot compté, ou justification manquante ; infobulle « {N} écart(s) hors tolérance sans justification : écrire d'abord ce qui a été constaté (lignes en rouge) » / « Aucun lot compté » / « Chaque écart devient un ajustement de stock ; les mouvements reprennent » | « Valider ? {c} lot(s) comptés, {a} écart(s) ajusté(s) ({±x,x kg})[, {n} non comptés restent au théorique]. Ne se défait pas. » / « Oui, valider l'inventaire » | enregistre d'abord les modifications (sans message), puis `POST /inventaires/{id}/valider` | « Inventaire validé : {a} ajustement(s) écrit(s) au stock. » ; tout le stock rafraîchi ; vue « Avec un écart » | côté écran (garde-fous) : « {N} écart(s) hors tolérance sans justification (en rouge) : écrire ce qui a été constaté avant de valider. » (+ vue Hors tolérance) ; « Aucun lot compté : saisir les comptages avant de valider. » — serveur : « Cet inventaire est déjà validé. » (409) ; « Aucun lot compté : saisir les comptages avant de valider. » ; « Écart hors tolérance sans justification : RÉF1, RÉF2… » (8 au plus) ; contrôles de date / période close ; « L'inventaire est daté du …, mais des lots qu'il fige ont bougé depuis : … » (409, lots dont l'écart est non nul) ; refus du moteur de stock (couvert à sa date…) |
| Saisies de cellule (palettes, bobines, compté, recompté, justification) | tableau | saisie | — | — | local jusqu'à « Enregistrer » | ligne teintée « modifiée » | — |
| Bascule « Lots à compter » / « Pièces jointes » | sous la barre | tous | — | — | — | — | — |

**Serveur à la validation** (`inventaires.py:381-415`) : pour chaque ligne comptée dont |retenu − théorique| ≥ 0,001,
écriture `AJUSTEMENT` datée du jour de l'inventaire, document « inventaire » + numéro, motif « Écart d'inventaire »,
commentaire « {justification} · recompté par {nom} » (300 car.) ; statut → `valide`, validé par/le ; les mouvements
reprennent. Un inventaire validé ne s'annule pas depuis cet écran (aucune route d'annulation). Les lignes non comptées
restent au théorique (non ajustées).

**Enregistrement du recomptage** (`inventaires.py:349-359`) : le client envoie toujours `second_compte` ; s'il change, le
serveur pose `second_par` = nom de l'utilisateur qui enregistre (vide si effacé). Pas de contrôle « quatre yeux » au serveur.

---

#### Encart « Lot trouvé » (dans la fenêtre Comptage, `saisie-ligne`)

- **Fichiers** : `Inventaire.tsx:1118-1247` (`LotTrouve`). Visible si « Lot trouvé… » enfoncé et saisie permise.
- Titre gras : « Un lot trouvé sur place, que le stock théorique ne connaissait pas ».
- **Données** : `GET /articles`, `GET /magasins`.

| Champ | Type | Défaut | Contrôle |
|---|---|---|---|
| « Matière » (duo) | recherche à la frappe sur toutes les matières ; libellé « RÉF — désignation », détail = fournisseur ; placeholder « Taper quelques mots de la référence… » | vide | obligatoire |
| « Numéro de lot » (duo) | texte, placeholder « Celui de l'étiquette » + bouton « Lot interne » (infobulle « Le lot n'a pas d'étiquette lisible ») | vide | obligatoire (non vide) |
| « Magasin » | si l'inventaire porte sur un magasin : champ grisé portant son code ; sinon liste « Choisir… » + magasins actifs (codes) | magasin de l'inventaire | obligatoire si tous magasins |
| « Bobines » (aide « × {poids bobine catalogue, 2 déc.} kg ») | nombre | vide | seulement si la matière a un poids de bobine ; calcule Compté = arrondi 2 déc. (bobines × poids) |
| « Compté (kg) » (aide « ≈ N ml, à titre indicatif » pour cuir/franges/ruban) | nombre | vide | obligatoire ; saisir efface les bobines |
| « Justification » (large ; aide « obligatoire : un lot hors du théorique est toujours un écart à expliquer ») | texte, placeholder « Palette retrouvée derrière le rayonnage B, étiquette arrachée… » ; classe `manque` si < 3 car. | vide | ≥ 3 caractères |

| Geste | Rôle | Conditions | Appel | Succès | Refus |
|---|---|---|---|---|---|
| « Lot interne » | achats | grisé pendant l'envoi | `POST /lots/numero-interne` (ACHATS) | numéro posé dans le champ | droit |
| « Ajouter le lot au comptage » (principal) | achats | grisé si envoi, pas de matière, lot vide, magasin manquant (tous magasins), compté vide, justification < 3 | `POST /inventaires/{id}/comptage` [{article_id, lot_numero, magasin_id, compte, justification}] | « Lot trouvé ajouté au comptage. » ; encart refermé ; ligne ajoutée au théorique 0 | « Un lot trouvé se décrit : matière, numéro de lot, magasin. » ; « Matière inconnue. » ; « Magasin inconnu. » ; « Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé. » ; « Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne. » ; « Un lot doit avoir un numéro : … » ; « Cet inventaire est déjà validé. » |

Notion : le lot trouvé est **créé tout de suite** dans le référentiel des lots (date d'entrée = date de l'inventaire) s'il
n'existe pas (`inventaires.py:369`), avec une ligne de théorique 0 ; son écart = tout le compté, toujours hors tolérance
(théorique ≤ 0), d'où la justification obligatoire.

---

#### Sous-vue « Pièces jointes » de l'inventaire (`PiecesJointes objet="inventaire"`)

- **Fichiers** : `components/PiecesJointes.tsx` (partagé) ; serveur `gestion_mp/api/suivi.py:242-290` (toutes routes `ACHATS`).
- `lectureSeule = !peut('achats')` (donc jamais en lecture seule sur cette page). Dépôt possible aussi sur un inventaire validé.
- Rangée : bouton « Joindre un document… » (« Envoi… » pendant l'envoi) + note « ou le glisser ici · PDF, image, tableur,
  texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; glisser-déposer sur la zone (contour pointillé).
- Tableau : « Document » (lien de téléchargement, infobulle « Télécharger le document ») · « Genre » (PDF / Image / Tableur /
  Document / Archive / Texte) · « Taille » (`num`, o / Ko / Mo) · « Par » · « Joint le » (jj/mm/aaaa hh:mm) · bouton
  « Retirer » (danger, confirmer « Retirer ce document ? » / « Oui, retirer », infobulle « Retirer « nom » de la liste (le
  retrait est tracé) »). Vide : « Aucun document joint. »
- Messages : « « nom » joint. » / « N documents joints. » / « « nom » retiré. » ; refus écran « « nom » est trop lourd : 20 Mo
  au plus. » ; serveur « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. », « Fichier trop lourd
  (20 Mo au plus). », « Document inconnu. » (404), « Pièce introuvable. » (404).

---

#### Document imprimable « Feuille de comptage » / « Feuille de recomptage » — `GET /api/inventaires/{id}/feuille[?recomptage=true][&theorique=true]`

- **Fichiers** : `gestion_mp/api/inventaires.py:433-504` (HTML produit par le serveur), ouvert dans un nouvel onglet
  (`lib/api.ts:79-81`).
- **Rôles** : tout compte connecté (`acteur`).
- Une page A4 **paysage** par magasin (triés par code), saut de page entre magasins ; bouton « Imprimer » en tête
  (masqué à l'impression) ; titre d'onglet « Feuille de comptage {numéro} » (même pour un recomptage).
- En-tête de page : h1 « Feuille de comptage — {numéro} » ou « Feuille de recomptage — {numéro} » ; dessous « {libellé} ·
  compté le jj/mm/aaaa · magasin **{code}** · N lot(s)[ · avec le théorique] » ; à droite « Compté par :
  ______________________ » / « Contrôlé par : ____________________ ».
- Colonnes : « N° » (rang) · « Référence » (gras + désignation en petit si différente) · « Lot » (gras mono) ·
  « Conditionnement » (« {poids} kg / bobine · {n} bob. / palette ») · [« Théorique » (kg) si recomptage ou
  `theorique=true`] · « Palettes » · « Bobines » · « Compté (kg) » · « Observations » (cases vides à remplir, la dernière large).
- Tri : référence, date d'entrée du lot, numéro de lot.
- Recomptage : seulement les lignes « à recompter » **enregistrées** (premier comptage hors tolérance, pas de second) et
  avec le théorique.
- Pied : « Un lot trouvé sur place et absent de la liste : l'écrire au dos (référence, lot, quantité). Un écart se justifie
  à la saisie, au-delà de la tolérance de {N} %. »
- Vide : « Aucun lot figé dans cet inventaire. »
- Le comptage normal est **à l'aveugle** (sans théorique) ; `theorique=true` existe au serveur mais n'est pas proposé à l'écran.

---

#### Notions métier — Inventaire

- **Inventaire** : document numéroté **dès l'ouverture** (`INV-AAAA-NNNN`, série par année de la date), statuts
  `ouvert` (« Comptage en cours ») → `valide` ; un inventaire ouvert peut être **abandonné** (supprimé, rien d'ajusté) ;
  validé, il « reste » (ne s'annule pas).
- **Figer le théorique** : à l'ouverture, chaque solde lot × magasin > 0 du périmètre devient une ligne avec son théorique.
- **Suspension des mouvements** : tant qu'il est ouvert, aucun mouvement (réception, sortie vers les machines, transfert,
  retour, opération, contre-passation) ne s'écrit sur le magasin compté — sur tous les magasins si l'inventaire porte sur
  tous —, même pour les matières hors périmètre. Un seul inventaire ouvert par magasin ; un inventaire « tous magasins »
  exclut tout autre.
- **Périmètre** : tout le stock (d'un magasin ou de tous), par famille (rôle, composition, classe ABC — critères cumulés),
  matières choisies, **inventaire tournant** (matières dues selon la cadence ABC : A 30 j, B 90 j, C 365 j, par magasin).
- **Classe ABC** : calculée à l'ouverture par le moteur de stock (A = l'essentiel de la valeur consommée).
- **Tolérance** : pourcentage d'écart relatif au théorique au-delà duquel l'écart est **hors tolérance** (réglage
  « Tolérance d'écart d'inventaire », défaut 2 %, modifiable à l'ouverture). Seuil de poussière : 0,001 kg (écart nul en
  dessous). Théorique nul + compté > 0 = toujours hors tolérance.
- **Justification** : obligatoire (≥ 3 caractères) pour un écart hors tolérance, contrôlée à l'écran et au serveur.
- **Comptage à l'aveugle** : la feuille de comptage ne montre pas le théorique.
- **Recomptage (second comptage)** : pour un premier comptage hors tolérance, « par une autre personne » (quatre yeux,
  seulement signalé) ; s'il existe c'est lui qui est **retenu** et qui ajuste ; l'auteur est noté (« par … »).
- **Retenu**, **Écart** (= retenu − théorique), **Écart net** (kg) et **valeur de l'écart** (MAD) : au CMUP du moment tant
  que l'inventaire est ouvert, au coût de l'ajustement écrit une fois validé ; « sans signe » = somme des valeurs absolues
  (ampleur de la correction). L'alimentation ne reçoit pas les montants.
- **Lot trouvé, non prévu** : lot absent du théorique, ajouté avec théorique 0.
- **Ajustement d'inventaire** : un mouvement `AJUSTEMENT` par écart non nul, motif « Écart d'inventaire », daté du jour de
  l'inventaire. Lignes non comptées = non ajustées.
- **Contrôle d'antidate** : un inventaire ne se date pas avant le dernier mouvement d'un lot qu'il fige (à l'ouverture),
  ni d'un lot ajusté (à la validation).
- Saisie en **palettes / bobines** convertie au poids de bobine **du lot** (sinon du catalogue).
- Mètres indicatifs (« ≈ N ml ») pour cuir, franges, ruban (`kg_par_ml`).

---

### PARTIE 2 — OPÉRATIONS DE STOCK

#### Opérations (page) — `/operations` (`?onglet=ouverture|transfert|ajustement|retour_fournisseur|retour_machine`, `?operation=ID`)

- **Fichiers** : `ecran/src/pages/Operations.tsx` (page `Operations` l.179-366) ; serveur `gestion_mp/api/operations.py`,
  `gestion_mp/api/brouillons.py` (pour « Tout valider »).
- **Rôles** :
  - Menu « Stock › Ouvertures, transferts, ajustements », rôles `['achats']` (`App.tsx:70`) ; garde `['achats']`
    (`App.tsx:258`) — l'alimentation est renvoyée à son accueil.
  - Droits par type, lus au serveur (`GET /operations/motifs` → `droits`) et appliqués par `droit(type) = peut(...rôles)` :
    | Type | Libellé serveur | Série | Rôles serveur (`QUI`, `operations.py:29-35`) |
    |---|---|---|---|
    | `ouverture` | « Stock d'ouverture » | OUV | achats |
    | `transfert` | « Transfert entre magasins » | TRF | achats, alimentation |
    | `ajustement` | « Ajustement justifié » | AJU | achats |
    | `retour_fournisseur` | « Retour au fournisseur » | RFO | achats |
    | `retour_machine` | « Retour des machines » | RET | alimentation |
    (direction : tout). Refus serveur : « « {libellé du type} » est réservé à : {rôles en minuscules}. » (403), par ex.
    « « Retour des machines » est réservé à : responsable alimentation machines. » ; « Type d'opération inconnu. »
  - Conséquence à l'écran pour les achats : bouton « Nouveau … » sur 4 onglets ; onglet « Retours machine » en lecture
    seule (pas de bouton nouveau, fenêtre sans aucun geste d'écriture). Pour la direction : tout, y compris supprimer /
    valider / annuler un retour machine (mais pas le modifier).
  - Lecture : `GET /operations` et `GET /operations/{id}` ouverts à tout compte connecté ; prix et devise masqués (null / vide)
    pour l'alimentation (`operations.py:201-206`).
- **Paramètres d'adresse** (l.193-209, 240-243) : `?onglet=` (type ; inconnu ou absent → « ouverture ») ; `?operation=ID`
  ouvre la fenêtre de l'opération **si elle figure dans la liste chargée** et force l'onglet sur son type. Changer d'onglet
  pose `onglet` et retire `operation`, et vide la recherche. Fermer la fenêtre retire `operation`. La création (« Nouveau … »)
  n'écrit rien dans l'adresse.
- **Liens entrants** : Stock › Mouvements (`/operations?operation=ID`, `Stock.tsx:103`), Cockpit et Accueil
  (`/operations?onglet={type}`), À valider (`/operations?onglet={type}&operation={id}`, `brouillons.py:67`).
- **Données** : `GET /api/operations/motifs` (types, motifs par type, codes R1…R6, droits ; cache 10 min) ;
  `GET /api/operations` (toutes, tri date ↓ puis id ↓, **1000 au plus**, chaque opération avec lignes, total et
  `blocages`).
- **En-tête** : titre « Ouvertures, transferts, ajustements » ; sous-titre « Chaque geste de stock a son document : on
  l'enregistre en brouillon (il se corrige), puis on le valide — c'est là que le stock bouge. Une opération validée ne
  s'efface pas : elle s'annule par une écriture inverse. » ; action (principal) selon l'onglet, si droit : « Nouveau stock
  d'ouverture » · « Nouveau transfert » · « Nouvel ajustement » · « Nouveau retour au fournisseur » (rien pour Retours machine).
- Pas d'indicateurs.
- **Onglets** (l.233-244), compteur = « N brouillon(s) » (« 1 brouillon », « 2 brouillons ») du type, absent s'il n'y en a pas :
  « Ouverture de stock » · « Transferts » · « Ajustements » · « Retours fournisseur » · « Retours machine ».
- Erreur de lecture : `Message erreur` ; chargement « Un instant — chargement : les opérations… ».

##### Carte de l'onglet (titre = libellé de l'onglet)

Note explicative par onglet (l.133-169) :
- Ouverture : « Le stock réel de départ, compté sur place à la mise en service : un lot par palette ou lot fournisseur,
  avec son prix d'achat (qui devient le coût moyen de départ). Le lot se crée à la validation. »
- Transferts : « Déplacer un lot d'un magasin à un autre — dont la libération d'une quarantaine : du magasin de quarantaine
  vers le stock courant, la matière devient disponible pour les machines. »
- Ajustements : « Corriger le stock d'un lot hors inventaire : perte, casse, matière retrouvée, erreur de saisie. Un motif
  et un commentaire disent toujours pourquoi le stock bouge. »
- Retours fournisseur : « Rendre de la matière au fournisseur (non-conformité, excédent, bobines endommagées). Un retour ne
  mêle pas deux fournisseurs : le fournisseur est celui des lots rendus. »
- Retours machine : « Ce qui revient des machines au magasin, rattaché à l'ordre d'où la matière était sortie. Ces retours
  se saisissent surtout depuis l'écran atelier, au téléphone ; ils se consultent ici. »

Rangée `.filtres` :
- `BarreRecherche` placeholder « Numéro, référence, lot, magasin, motif, personne… » — à la frappe sur : numéro (ou
  « Brouillon »), motif, code motif, commentaire, fournisseur, ordre, créé par, validé par, et pour chaque ligne référence,
  lot, magasin, magasin de destination.
- Liste d'état : « Tous les états (n) » · « Brouillons (n) » · « Validées (n) » · « Annulées (n) » (compteurs du type).
  Non écrit dans l'adresse ; conservé au changement d'onglet.
- « Effacer les filtres » (si recherche ou état posé) → vide les deux.
- Note « {N} opération(s) ».
- À droite, s'il existe au moins un brouillon (tous types) : lien-bouton « Tout valider… ({N}) » vers
  `/stock?onglet=a-valider` (infobulle « Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout
  valider » »).

Tableau `Cadre court`, `table.serre` :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Numéro | numéro gras (OUV-/TRF-/AJU-/RFO-/RET-AAAA-NNNN) ou « Brouillon » ; si blocages : note rouge « sera refusée » (infobulle = blocages joints par « · ») | | |
| Date | date de l'opération | jj/mm/aaaa | |
| Motif / Fournisseur / Ordre (selon onglet) | Ouverture, Transferts, Ajustements : motif « R? · motif » ou « — » ; Retours fournisseur : fournisseur (ou « — ») + motif en note ; Retours machine : lien numéro d'ordre → `/sorties?ordre={bon_id}` (ou « — ») + motif en note ; dans tous les cas commentaire en note | | le lien d'ordre n'ouvre pas la ligne |
| Lots | 2 premières lignes : « RÉF · lot X · MAG » (transfert : « · DE → VERS ») ; puis « + N autre(s) » | | |
| Quantité | total des lignes « x,x kg » ; ajustement positif préfixé « + » | `num` | net pour un ajustement |
| Valeur | (onglet Ouverture seulement) Σ quantité × prix, **par devise** (« 61 888 USD · 53 132 EUR », jamais additionnées) ou « — » | `num` | |
| État | Etiquette « Brouillon » (attention), « Validée » (ok), « Annulée » (neutre) | | |
| Par | « {créé par}[ · validée par {nom}] » | note | |

- Teintes : `ligne-eteinte` (gris) si annulée ; sinon `ligne-alerte` (rouge pâle) si le brouillon a des blocages.
- Ligne cliquable → fenêtre de l'opération (pose `?operation=ID`).
- Vide : « Aucune opération ne correspond. » (filtres) ou « Aucune opération de ce type pour l'instant. »
- Pas de tri cliquable, pas de pagination, pas de pied de tableau, pas d'export.

**Blocages** (calculés au serveur sans rien écrire, `operations.py:78-138`, sur les brouillons seulement) :
« aucune ligne » ; le message de date (futur, trop ancienne, période close) ; « l'inventaire {numéro} est en cours ({code |
tous les magasins}) » ; « lot {lot} de {réf} : épuisé dans « {code} », {q} demandés » ou « … : {x} seulement dans « {code} »,
{q} demandés » (transfert, retour fournisseur, ajustement négatif, cumulé par lot × magasin) ; messages de
`couvert_a_sa_date` (antidate) ; « le magasin « {code} » est désactivé » (magasin cible, sauf retour fournisseur) ; retour
machine : « daté du {date}, avant l'ordre {numéro} du {date} », « lot {lot} : seulement {x} kg partis pour cet ordre, {y} kg
rendus ».

---

#### Fenêtre d'une opération (Dialogue `tresLarge`, `sale={modifiable && changé}`) — nouvelle ou `?operation=ID`

- **Fichiers** : `Operations.tsx:376-748` (`EditeurOperation`), `750-771` (`versSaisie`).
- **Rôles** : `droit` = droit du type ; **modifiable** = droit ET statut brouillon ET type ≠ retour_machine (l.401).
- **Titre** : « {libellé serveur du type} — {numéro | Brouillon} » ou « {libellé} — nouveau brouillon », + Etiquette d'état
  (Brouillon / Validée / Annulée). Ex. « Stock d'ouverture — nouveau brouillon », « Transfert entre magasins — TRF-2026-0012 ».
- **Note** (opération existante) : « Saisie par {nom}[ le {jj/mm/aaaa hh:mm}][ · validée par {nom}[ le …]][ · ordre
  {numéro}][ · fournisseur {nom}][ · le numéro est donné à la validation] ».
- **Blocages** (brouillon enregistré et non modifié) : encadré rouge « **Sera refusé à la validation :** » + liste à puces
  (`atelier/commun.tsx:298-310`).

**Formulaire d'en-tête**

| Champ | Type | Défaut | Contrôle / remarque |
|---|---|---|---|
| « Date » | date, `max` aujourd'hui, grisé si non modifiable | aujourd'hui | date future → manque « une date qui ne soit pas dans le futur » ; serveur `date_permise` à l'enregistrement (futur, < 2000, période close) |
| « Motif (obligatoire) » / « Motif » | liste ; absent pour une ouverture | vide | obligatoire pour retour machine, retour fournisseur, ajustement (classe `manque` si vide) ; première option « Choisir le motif… » ou « Sans motif particulier » (transfert) ; options = motifs du type (+ le motif courant s'il n'y figure plus), libellés « R1 · Reliquat de fin d'ordre » quand un code existe |
| « Commentaire (obligatoire) » / « Commentaire » | texte (large pour une ouverture, duo sinon) ; aide « ce qui a été constaté, en quelques mots » (ajustement) | vide | ajustement : ≥ 5 caractères (classe `manque`) ; placeholders « Bobines écrasées au déchargement, palette retrouvée… » (ajustement), « Comptage du magasin principal, mise en service… » (ouverture) ; 300 car. au serveur |

Motifs par type (`operations.py:36-45`) :
- Retour machine : « Reliquat de fin d'ordre » (R1), « Changement de série / arrêt machine » (R2), « Erreur de prélèvement » (R4).
- Retour fournisseur : « Non-conformité qualité » (R3), « Excédent de réception » (R5), « Bobines endommagées » (R6),
  « Refus après quarantaine » (R3).
- Ajustement : « Écart constaté au comptage », « Matière retrouvée », « Perte / casse », « Correction de saisie ».
- Transfert : « Rangement », « Libération de quarantaine », « Mise en quarantaine », « Approvisionnement de l'atelier ».

Message info si transfert + motif « Libération de quarantaine » + modifiable : « Libération de quarantaine (décision des
achats, après contrôle) : choisir un lot dans le magasin de quarantaine ; il part vers le stock courant et devient
disponible pour les machines. Dire dans le commentaire ce qui a été contrôlé. »

Si modifiable : encart « Nouvelle ligne » (ouvert d'office pour une nouvelle opération) ou bouton « + Ajouter une ligne ».

**Tableau des lignes** (`Cadre dialogue`, `table.serre`)

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| Référence | référence (infobulle idem) | `reference` | |
| Lot | numéro (mono) ou « — » ; note « lot créé à la validation » si pas encore de lot (ouverture, matière retrouvée) | mono | |
| De / Magasin | magasin (de départ pour un transfert) | | en-tête « De » pour un transfert |
| Vers | magasin de destination | | transfert seulement |
| Ajustement / Quantité | « x,xx kg[ ≈ N ml] » ; ajustement : « + » si positif, rouge si négatif / vert si positif ; note « N bobine(s) » / « N palette(s) » si saisi ainsi ; note rouge « plus que les {x kg} du lot » si la quantité dépasse le disponible connu (hors ouverture / ajustement) | `num` | en-tête « Ajustement » pour un ajustement |
| Prix / unité | « {prix, 4 déc.} {devise} » | `num` | ouverture seulement |
| Valeur | « {quantité × prix, 2 déc.} {devise} » | `num` | ouverture seulement |
| (actions) | « Modifier » · « Retirer » (danger, sans confirmation, local) | | si modifiable |

- Ligne en cours de modification teintée `ligne-modifiee`.
- Pied (si > 1 ligne) : « {n} lignes » · total des quantités « x,xx kg » (net, sans mètres) · (ouverture) valeur par devise.
- Vide : « Aucune ligne. Remplir le formulaire au-dessus, puis « Ajouter la ligne ». »
- Note sous le tableau si modifiable et incomplet : « Pour enregistrer, il manque : {liste}. » parmi « au moins une
  ligne », « le motif », « le commentaire (ce qui a été constaté) », « une date qui ne soit pas dans le futur ».

**Gestes de la fenêtre**

| Geste | Où | Rôle | Conditions / grisé (infobulle) | Confirmation | Appel API | Succès | Refus / erreurs (serveur) |
|---|---|---|---|---|---|---|---|
| « + Ajouter une ligne » | sous l'en-tête | modifiable | visible si l'encart est fermé | — | — | ouvre l'encart « Nouvelle ligne » | — |
| « Modifier » (ligne) | tableau | modifiable | — | — | — | encart « Modifier la ligne RÉF » prérempli | — |
| « Retirer » (ligne) | tableau | modifiable | — | aucune | — (local) | ligne retirée, fenêtre « sale » | — |
| « Supprimer le brouillon » (danger) | pied gauche | droit, brouillon enregistré | grisé pendant l'envoi ; infobulle « Supprimer le brouillon : rien n'a bougé au stock » | « Supprimer ce brouillon ? Rien n'a encore bougé au stock. » / « Oui, supprimer » | `DELETE /operations/{id}` | fenêtre fermée (aucun message) | « Une opération validée ne se supprime pas : l'annuler. » (409) ; « Opération introuvable. » (404) ; droit du type |
| « Annuler (contre-passation) » (danger) | pied gauche | droit, opération validée | grisé pendant l'envoi ; infobulle « Annuler (contre-passation) : une écriture inverse, datée comme l'opération » | « Annuler ? Une écriture inverse remet le stock comme avant ; les deux restent aux mouvements, et l'annulation ne se défait pas. » / « Oui, annuler (contre-passation) » | `POST /operations/{id}/annuler` | « {numéro} annulée. » ; état « Annulée » ; tout le stock rafraîchi | « Seule une opération validée s'annule ; un brouillon se supprime. » (409) ; « Ce document a déjà été annulé. » (409) ; refus du moteur sur l'écriture inverse (période close à la date d'origine, inventaire en cours, stock insuffisant — matière déjà consommée —, antidate, magasin désactivé) |
| « Fermer » | pied droit | tous | si modifiable et modifié : Confirmer « Abandonner les modifications ? » / « Oui, abandonner » (infobulle « Fermer sans enregistrer ») | — | — | ferme | — |
| « Enregistrer le brouillon » | pied droit | modifiable | grisé si envoi, s'il manque quelque chose, ou opération enregistrée non modifiée ; infobulle fixe « Le stock ne bouge qu'à la validation » | — | nouvelle : `POST /operations` ; existante : `PUT /operations/{id}` — corps {type, date, bon_id, motif, commentaire, lignes[{article_id, lot_id, lot_numero, magasin_id, magasin_destination_id, quantite (dans l'unité saisie, signée pour un ajustement), unite, prix, devise}]} | « Brouillon enregistré : le stock ne bouge qu'à la validation. » ; blocages affichés | voir liste « Refus à l'enregistrement » ci-dessous |
| « Valider : le stock bouge » (principal) | pied droit | droit, statut brouillon (y compris nouvelle non enregistrée) | grisé si envoi, s'il manque quelque chose, ou une ligne en cours de modification ; infobulle fixe « Valider : le stock bouge et l'opération reçoit son numéro » ; **non grisé** en cas de blocages | « Valider ? Le stock bouge maintenant ({n} ligne(s)) ; ensuite l'opération ne se modifie plus. » / « Oui, valider » | enregistre d'abord si nouveau ou modifié (sans message), puis `POST /operations/{id}/valider` | « {numéro} validée : le stock est à jour. » ; fenêtre reste ouverte en lecture ; tout le stock rafraîchi | voir « Refus à la validation » |

**Refus à l'enregistrement** (`operations.py:250-332`, + `modifier` l.366-378) :
« Une opération validée ne se modifie plus : l'annuler. » (409) · « Le type d'une opération ne change pas. » · contrôles de
date · « Choisir le motif : il dit pourquoi le stock bouge. » · « Un ajustement se justifie : écrire en quelques mots ce qui a
été constaté. » · « Un retour des machines se rattache à l'ordre d'où la matière revient. » · « Ce retour est daté du {date},
avant l'ordre {numéro} du {date} : la matière n'était pas encore partie. Dater le retour du jour où elle est revenue. » ·
« Matière inconnue. » · « Magasin inconnu. » · « Ce lot est d'une autre matière. » · « Unité : kg, bobine ou palette — le
cuir, les franges et le ruban se comptent aussi en kilos. » · « Un stock d'ouverture se saisit en kg : il fixe le prix au
kilo. » · « « RÉF » : le nombre de bobines par palette n'est pas connu, saisir en bobines ou en kg. » · « « RÉF » : le poids
de bobine n'est pas connu, saisir en kg. » · « « RÉF » : devise inconnue (« XXX »). L'ajouter d'abord dans Réglages ›
Devises, avec son cours. » · « « RÉF » : le numéro de lot du stock d'ouverture manque. » · « Un stock d'ouverture est
positif. » · « Désigner le lot ajusté (ou en nommer un, pour une matière retrouvée). » · « Un ajustement ne peut pas être
nul. » · « « RÉF » : choisir le lot. » · « La quantité est positive. » · « Un transfert va d'un magasin à un autre. » ·
« Magasin de destination inconnu. » · « Libérer une quarantaine est une décision des achats, après contrôle de la
matière. » (403) · « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». » · « Une entrée en
quarantaine se fait avec le motif « Mise en quarantaine ». » · « Un retour au fournisseur ne mêle pas deux fournisseurs. » ·
Pydantic : lignes ≥ 1, motif ≤ 80, commentaire ≤ 300, lot ≤ 80, prix 0…1e7, devise 3 car.

**Refus à la validation** (`operations.py:395-442`) : « Cette opération est déjà validée. » (409) · contrôles de date ·
« Libérer une quarantaine est une décision des achats, après contrôle de la matière. » (403, si un non-achats valide une
sortie de quarantaine) · retour machine : « Ce retour est daté du … » ; « Le lot « X » n'est sorti que de {x} kg pour cet
ordre ({y} kg rendus) : on ne rend pas plus que ce qui est parti. » (409) · tous les refus du moteur de stock (inventaire en
cours, stock insuffisant, antidate, magasin désactivé, lot sans numéro).

**Effets de la validation** : numéro `{SÉRIE}-{année}-{NNNN}` donné **à la validation** (brouillon supprimé = pas de trou) ;
transfert = deux mouvements `TRANSFERT` appariés (sortie puis entrée) ; ouverture et matière retrouvée = le lot est créé
(date d'entrée = date de l'opération) puis mouvement `OUVERTURE` / `AJUSTEMENT` avec prix et devise (ouverture) ; retour
fournisseur = mouvement `RETOUR_FOURNISSEUR` négatif ; retour machine = `RETOUR_MACHINE` rattaché à l'ordre ; motif et
commentaire recopiés sur les mouvements. Un retour fournisseur rouvre le solde de la commande qu'il dégarnit ; une sortie
de quarantaine solde la commande qui n'attendait plus qu'elle (et l'inverse à l'annulation) (`_recaler_bons`).
**Annulation** = contre-passation de chaque mouvement non encore contre-passé, **datée comme l'original**, sorties
d'abord ; commentaire « Annulation du mouvement n°{id} » ; une seule fois.

---

#### Encart « Nouvelle ligne » / « Modifier la ligne RÉF » (dans la fenêtre d'opération, `saisie-ligne`)

- **Fichiers** : `Operations.tsx:775-1121` (`FormeLigne`).
- **Données** : `GET /articles`, `GET /magasins`, `GET /devises`, `GET /soldes?article_id=` (sauf ouverture, une fois la
  matière choisie).

| Champ | Visible | Type / options | Défaut | Contrôle (« Il manque : … ») |
|---|---|---|---|---|
| « Matière » (duo) | toujours | recherche à la frappe ; ouverture et ajustement : matières **actives** ; autres : matières avec stock > 0 ; libellé « RÉF — désignation », détail « {x} kg[ ≈ ml] en stock » ; placeholder « Taper quelques mots de la référence… » | vide | « la matière » ; changer de matière vide le lot et remet l'unité à kg ; ouverture : préremplit le prix (prix catalogue au kg) et la devise |
| « Lot et magasin de départ » (transfert) / « Lot » | sauf ouverture | liste grisée tant que pas de matière (« Choisir d'abord la matière ») ; « Choisir le lot… » ; options « Lot {lot} · {magasin}[ (quarantaine)] · {x} kg[ ≈ ml][ · entré le jj/mm/aaaa] » ; ajustement : option finale « Un lot qui n'est pas en stock (matière retrouvée)… » ; aide « Lecture des lots… » / « Aucun lot de cette matière n'est en quarantaine » / « Tous les lots de cette matière sont déjà en quarantaine » / « Aucun lot en stock pour cette matière » | vide | « le lot » |
| filtrage des lots (transfert) | | motif « Libération de quarantaine » → lots en quarantaine seulement ; « Mise en quarantaine » → hors quarantaine seulement ; autres motifs → tous | | une ligne rouverte dont le lot n'est plus en stock reste proposée (quantité 0) |
| « Numéro de lot » (duo) + « Lot interne » | ouverture, ou ajustement « matière retrouvée » | texte placeholder « Celui de l'étiquette » ; bouton « Lot interne » (infobulle « Le lot n'a pas d'étiquette lisible ») → `POST /lots/numero-interne` | vide | « le numéro de lot » |
| « Magasin » | idem | « Choisir… » + magasins actifs « CODE[ (quarantaine)] » | vide | « le magasin » |
| « Vers le magasin » | transfert | « Choisir… » + magasins actifs sauf celui de départ | proposé automatiquement au choix du lot : si le lot est en quarantaine → premier magasin actif hors quarantaine ; si motif « Mise en quarantaine » → premier magasin de quarantaine | « le magasin de destination » (vide ou égal au départ) |
| « Sens » | ajustement | « Retirer du stock (−) » / « Ajouter au stock (+) » | **Retirer (−)** (nouvelle ligne) ; ligne existante : selon son signe | — |
| « Unité » | si plus d'une unité possible (jamais pour une ouverture) | « kg », « bobines ({poids} kg) » (si poids de bobine > 0), « palettes ({n} bob.) » (si en plus bobines/palette > 0) ; aide « = {x} kg » en bobines/palettes | kg | poids de bobine = celui mesuré du lot, sinon catalogue |
| « Quantité ({kg \| bobines \| palettes}) » | toujours | nombre ; aide selon le cas : rouge « plus que les {x} kg du lot » (dépassement, hors ouverture/ajustement) ; ajustement : « stock du lot après : {x} kg » ; lot choisi : lien « tout le lot : {x} kg » (met l'unité en kg et la quantité = tout le lot) ; cuir/franges/ruban : « ≈ N ml, à titre indicatif » | vide | « la quantité » (> 0) |
| « Prix d'achat / kg » | ouverture | nombre ; aide « catalogue : {prix_kg 4 déc.} {devise} / kg[ ({prix} / ml)] » | prix catalogue au kg | « le prix » |
| « Devise » | ouverture | devises actives (+ la courante) ; MAD si la liste n'est pas chargée | devise de la matière, sinon MAD | — |

- **Calculs en direct** : quantité en kg = quantité × contenance (1 ; poids de bobine ; poids de bobine × bobines/palette) ;
  ajustement « − » → quantité négative ; « stock du lot après » = disponible du lot ± quantité ; dépassement = quantité kg >
  disponible + 0,001 (avertissement seulement).
- Pied de l'encart : « Il manque : {liste}. » ; « Annuler » (ferme l'encart, sans confirmation) ; « Ajouter la ligne » /
  « Enregistrer la ligne » (principal, grisé s'il manque quelque chose — sans infobulle, la note dit quoi). Le prix est mis
  à 0 et la devise à MAD pour tout type autre qu'ouverture.
- Erreur de « Lot interne » affichée dans l'encart.

---

#### Notions métier — Opérations

- **Opération de stock** : un document par geste — stock d'ouverture, transfert entre magasins (dont libération / mise en
  quarantaine), ajustement justifié, retour au fournisseur, retour des machines. Cycle **brouillon** (sans numéro, affiché
  « Brouillon », corrigeable, supprimable, le stock ne bouge pas) → **validée** (numéro, le stock bouge, plus modifiable) →
  **annulée** (contre-passation, une fois, définitive).
- **Numéro à la validation** (M65) : séries OUV / TRF / AJU / RFO / RET, `{SÉRIE}-{année de la date}-{NNNN}`.
- **Blocages** (« sera refusée ») : ce qui ferait refuser la validation, annoncé d'avance sur le brouillon et dans « Tout
  valider » (`/stock?onglet=a-valider`).
- **Tout valider** (`POST /brouillons/valider`, rôle STOCK) : valide les brouillons permis au compte, dans l'ordre des dates,
  à date égale ouverture < transfert < ajustement < ordre < retour machine < retour fournisseur, chacun dans sa transaction.
- **Motif** et **code motif** (R1…R6, repris de l'ERP Fil, lus par le contrôle « retour sans motif » et la traçabilité) ;
  motif obligatoire pour ajustement, retours ; **commentaire** obligatoire (≥ 5 car.) pour un ajustement.
- **Stock d'ouverture** : stock réel de départ, un lot par palette ou lot fournisseur, saisi **en kg**, avec prix d'achat et
  devise (devient le coût moyen de départ) ; le lot se crée à la validation.
- **Quarantaine** : magasin de type « Quarantaine » ; **libération** = transfert quarantaine → stock courant, motif imposé
  « Libération de quarantaine », décision des achats (refusée à l'alimentation) ; **mise en quarantaine** = l'inverse, motif
  imposé « Mise en quarantaine ».
- **Matière retrouvée** : ajustement sur un lot qui n'est pas en stock, nommé à la saisie, créé à la validation.
- **Retour fournisseur** : un seul fournisseur par retour (celui des lots) ; rouvre le solde de la commande.
- **Retour des machines** : rattaché à un ordre validé, pas avant sa date, jamais plus que le net sorti par lot pour cet ordre.
- **Unités de saisie** : kg, bobine (au poids mesuré du lot), palette ; le stock est toujours en kg ; mètres indicatifs.
- **Contre-passation** : écriture inverse datée comme l'original ; les deux restent aux mouvements.
- **Suspension par inventaire** : aucune validation / annulation sur un magasin en cours d'inventaire.
- Valeur d'une ouverture : par devise, jamais additionnée entre devises.

---

### Incohérences et anomalies repérées

1. **Opérations interdites à l'alimentation alors que le serveur et les règles les lui donnent** : menu et garde
   `/operations` = achats seulement (`ecran/src/App.tsx:70`, `App.tsx:258`) alors que les transferts sont permis à
   l'alimentation au serveur (`gestion_mp/api/operations.py:32`) et que `docs/REGLES-ECRAN.md` §4 lui attribue
   « transferts ». « Tout valider » fabrique pour elle des liens `/operations?onglet=transfert&operation=ID`
   (`gestion_mp/api/brouillons.py:67`) qui la renvoient à son accueil. Toute la logique `droit(type)` de la page
   (`Operations.tsx:211`) ne sert donc qu'à distinguer achats et direction.
2. **Sortie de quarantaine sans le bon motif, découverte seulement à l'enregistrement** : avec un motif vide ou « Rangement »,
   l'encart propose aussi les lots en quarantaine et choisit d'office une destination hors quarantaine
   (`Operations.tsx:846-854, 885-889`) ; le serveur refuse ensuite « Une sortie de quarantaine se fait avec le motif
   « Libération de quarantaine ». » (`operations.py:314-315`). Changer le motif après avoir ajouté des lignes ne refiltre
   rien.
3. **Matière retrouvée avec Sens « Retirer (−) »** : rien ne l'empêche à l'écran (`Operations.tsx:898, 945-946`) ni à
   l'enregistrement (`operations.py:292-296`) ; les blocages ignorent les lignes sans lot (`operations.py:100`) ; refus
   seulement à la validation (« ne porte que 0,000 kg »). De plus le sens par défaut d'un nouvel ajustement est « Retirer »
   (`Operations.tsx:822`), même pour le motif « Matière retrouvée ».
4. **Retour fournisseur : le fournisseur du lot n'est pas montré au choix du lot** (`Emplacement.fournisseur` lu mais
   jamais affiché, `Operations.tsx:784, 841, 993-997`) ; mêler deux fournisseurs n'est refusé qu'à l'enregistrement
   (`operations.py:330-331`).
5. **Boutons grisés sans la raison** (REGLES §2) : « Valider : le stock bouge » grisé quand une ligne est en cours de
   modification, infobulle fixe (`Operations.tsx:736-740`) ; « Enregistrer le brouillon » grisé (rien de modifié), infobulle
   fixe (`Operations.tsx:729`) ; « Ouvrir et figer le stock » grisé pour périmètre incomplet ou tolérance vide, infobulle
   fixe (`Inventaire.tsx:629-632`) ; « Ajouter la ligne » / « Ajouter le lot au comptage » sans infobulle
   (`Operations.tsx:1115`, `Inventaire.tsx:1219-1223`, la note « Il manque » compense pour la première seulement).
6. **On peut cliquer « Valider » pour découvrir un refus** : la validation d'une opération n'est pas grisée quand le serveur
   annonce des blocages (`Operations.tsx:736` ; seul l'encadré « Sera refusé à la validation » prévient). Valider pendant que
   l'encart « Nouvelle ligne » est rempli mais non ajouté perd la ligne en silence (`editee` seul est testé).
7. **Recomptage « à quatre yeux » non garanti** : le serveur accepte un recomptage par la personne qui a ouvert
   l'inventaire (ou qui a fait le premier comptage) (`inventaires.py:355-357`) ; l'écran se contente d'une note
   (`Inventaire.tsx:1069`). Le premier compteur n'est d'ailleurs pas enregistré.
8. **« Feuille de recomptage » calculée sur des saisies non enregistrées** : le bouton s'active d'après les brouillons locaux
   (`Inventaire.tsx:846-853`), mais la feuille ne contient que les lignes enregistrées (`inventaires.py:447-449`) → feuille
   vide ou incomplète possible.
9. **Fenêtre Comptage : deux filtres (recherche + vue) sans « Effacer les filtres »** (`Inventaire.tsx:965-976`, REGLES §2).
10. **Pas d'« Exporter en Excel »** sur la liste des inventaires, le comptage, ni la liste des opérations (REGLES §2) ; aucune
    route `/export/inventaires` ou `/export/operations` n'existe (`gestion_mp/api/exports*.py`).
11. **Vocabulaire** : en-têtes « Ouvert par », « Validé par » (`Inventaire.tsx:223, 282-283`) au lieu de « Par » ; en-tête
    « Prix / unité » (`Operations.tsx:603`) qui ne dit pas l'unité (le prix est au kg : « Prix / kg » ou « MAD / kg ») ;
    « Théorique » (`Inventaire.tsx:986`) figure dans la colonne « à ne plus employer » de REGLES §3 (pour un autre sens,
    mais à trancher) ; deux colonnes « Écart (kg) » et « Écart » côte à côte (`Inventaire.tsx:993-994`) ; onglet « Ouverture
    de stock » (`Operations.tsx:136`) contre « Stock d'ouverture » dans le titre de la fenêtre (`gestion_mp/modeles.py:764-770`) ;
    titre de page « Ouvertures, transferts, ajustements » qui omet les retours fournisseur et machine.
12. **Raccourcis manquants** (REGLES §2) : aucun lot n'ouvre sa fiche `/lot/ID` (ni dans le comptage, ni dans les lignes
    d'opération) ; dans la fenêtre d'opération, l'ordre (« ordre RET… ») et le fournisseur sont du texte, pas des liens
    (`Operations.tsx:504-505`).
13. **Fermer une opération ouverte par lien `/operations?operation=ID`** (lien de Stock › Mouvements, `Stock.tsx:103`, sans
    `onglet`) ramène à l'onglet « Ouverture de stock » au lieu de rester sur le type de l'opération
    (`Operations.tsx:196, 208`).
14. **Liste tronquée en silence** : `GET /operations` limité à 1000 (`operations.py:216`), sans pagination ni avertissement ;
    un `?operation=ID` plus ancien n'ouvre rien (`Operations.tsx:194`).
15. **Données reçues mais non montrées / code mort** : valeur de l'écart par ligne et CMUP (`cmup_mad`, `valeur_ecart_mad`)
    jamais affichés dans le comptage (ni en indicateur) ; champs `retenu`, `hors_tolerance`, `a_recompter`, `recomptees`
    recalculés côté écran au lieu d'être lus ; constante `unites = 'kg'` résiduelle (`Inventaire.tsx:706`) ; garde-fous de
    `valider()` (`Inventaire.tsx:789-799`) inatteignables puisque le bouton est grisé dans ces cas ; remise à zéro du
    formulaire « Lot trouvé » après succès inutile (l'encart se ferme, `Inventaire.tsx:1233-1239`) ; paramètre serveur
    `theorique=true` de la feuille jamais proposé.
16. **Libellé et confirmation trompeurs pour un inventaire partiel** : sans magasin, un périmètre « famille » ou « matières »
    reçoit le libellé « Inventaire de tout le stock » (`Inventaire.tsx:419`) et la question « Figer le stock de tous les
    magasins… » (`Inventaire.tsx:630`).
17. **Périmètre « Certaines matières »** : propose les matières à stock global > 0, même absentes du magasin choisi
    (`Inventaire.tsx:508`) → 0 lot figé possible ; retirer une matière choisie ne marque pas la saisie comme modifiée
    (`Inventaire.tsx:526`).
18. **Tolérance non bornée à l'écran** (`Inventaire.tsx:474-476`) : > 100 % ou négative → refus Pydantic brut
    « tolerance : … » (`inventaires.py:259`). La période close n'est pas anticipée à l'ouverture (seule la date future l'est).
19. **Lot trouvé créé immédiatement** (`inventaires.py:369`) : abandonner l'inventaire laisse un lot vide au référentiel ;
    le calcul Bobines → kg de l'encart utilise le poids de bobine du **catalogue** (`Inventaire.tsx:1187-1193`) et non
    celui du lot, contrairement au tableau.
20. **Avertissement de suspension absent des opérations** : la page Opérations n'utilise pas `useSuspension`
    (`pages/atelier/commun.tsx:177`) ; un inventaire en cours n'est signalé qu'après enregistrement (blocages).
21. **Annulation non tracée à l'écran** : ni l'auteur ni la date de l'annulation d'une opération ne sont renvoyés ni
    affichés (`operations.py:173-198`, `Operations.tsx:499-508`).
22. **Création non reflétée dans l'adresse** : après le premier « Enregistrer le brouillon » d'une nouvelle opération,
    `?operation=` n'est pas posé (`Operations.tsx:416-421`).
23. **Incohérences de présentation** : « Hors tolérance » en Etiquette critique dans « En cours » mais attention dans
    « Validés », et « Écart à ce stade » non coloré quand « Écart total » l'est (`Inventaire.tsx:240-242` vs `299-302`) ;
    message vide « Aucune ligne. Remplir le formulaire au-dessus… » affiché aussi sur une opération en lecture seule
    (`Operations.tsx:671`) ; filtre d'état des opérations conservé d'un onglet à l'autre alors que la recherche est vidée
    (`Operations.tsx:241-242`) et absent de l'adresse.
24. **Retours machine** : la direction peut supprimer, valider ou annuler un retour machine depuis cette page mais pas le
    modifier (`Operations.tsx:401` vs `696-744`) ; aucun lien vers l'écran atelier où il se saisit.
25. **Ajout de ligne sans confirmation** : « Retirer » une ligne d'opération et « Annuler » l'encart de ligne ne demandent
    rien (choix assumé, local), mais l'encart rempli puis « Annuler » perd la saisie de la ligne sans garde.

### Comptes

- **Écrans / pages** : 2 (`/inventaire`, `/operations`).
- **Onglets / sous-vues** : 9 — Inventaire : 2 onglets (En cours de comptage, Inventaires validés) + 1 Bascule à 2 volets
  dans le comptage (Lots à compter, Pièces jointes) ; Opérations : 5 onglets (Ouverture de stock, Transferts, Ajustements,
  Retours fournisseur, Retours machine). (+ 7 vues de filtre du comptage et 4 périmètres d'ouverture, non comptés.)
- **Fenêtres / encarts / documents** : 7 — fenêtres « Ouvrir un inventaire », « Comptage » d'un inventaire, « Opération »
  (5 variantes de type) ; encarts « Lot trouvé », « Nouvelle ligne / Modifier la ligne » ; document imprimable « Feuille de
  comptage / de recomptage » ; panneau « Pièces jointes » (partagé).
- **Gestes inventoriés** : 36 — Inventaire 19 (Ouvrir un inventaire, clic ligne ×2, Annuler, Ouvrir et figer le stock,
  Feuille de comptage, Feuille de recomptage, Lot trouvé…, Abandonner, Enregistrer le comptage, Valider l'inventaire, saisie
  de cellule, Bascule, Lot interne, Ajouter le lot au comptage, Joindre un document…, Retirer une pièce, télécharger une
  pièce, Imprimer) ; Opérations 17 (Nouveau … ×4 variantes = 1, Effacer les filtres, Tout valider…, clic ligne, lien
  d'ordre, + Ajouter une ligne, Modifier, Retirer, Supprimer le brouillon, Annuler (contre-passation), Fermer, Enregistrer
  le brouillon, Valider : le stock bouge, Lot interne, « tout le lot », Annuler l'encart, Ajouter / Enregistrer la ligne).

---

## Partie 7 — Catalogue (matières, classification, fournisseurs, import tableur), qualités et recettes

Inventaire en lecture seule de `/Users/mohamed/gestion-mp`. Références `fichier:ligne` relatives à
`ecran/src` (écran) ou au dépôt (`gestion_mp/...`, serveur).

Fichiers lus en entier : `pages/Catalogue.tsx`, `components/referentiels/CatalogueMatieres.tsx`,
`CatalogueClassification.tsx`, `CatalogueFournisseurs.tsx`, `TableurMatieres.tsx`, `ChoixClasse.tsx`,
`NombrePieces.tsx`, `types.ts`, `referentiels.css`, `components/importations/ReglagesCodesDouaniers.tsx`,
`pages/Qualites.tsx`, `components/referentiels/QualiteDetail.tsx`, `components/PiecesJointes.tsx` (partagé) ;
serveur : `gestion_mp/api/referentiels.py` (classification, fournisseurs, articles, qualités, exports),
`gestion_mp/api/referentiels_import.py` (codes douaniers et postes de frais — **l'import tableur n'y est pas** :
il est dans `gestion_mp/api/suivi.py:678-838`, de même que `GET /qualites/{qid}/versions` `suivi.py:479`
et le versionnage automatique des recettes `suivi.py:440-476`), `gestion_mp/api/pilotage.py:110`
(`/nomenclature`), `gestion_mp/securite.py:104-122` (droits).

Règles de droits côté serveur (`gestion_mp/securite.py:104-122`) : `droit(*roles)` — la direction passe
partout ; `ACHATS` = achats + direction ; `DIRECTION` = direction seule ; `acteur` = toute personne connectée.
Refus de rôle : **« Cette action est réservée à : achats. »** (ou « … réservée à : la direction. »), code 403.
Sans session : « Connectez-vous pour continuer. » (401).

Garde des routes écran (`App.tsx:76-77, 259-260`) : `/catalogue` et `/qualites` → `garde(['achats'])` ⇒
achats et direction ; l'alimentation est renvoyée vers son accueil (`/atelier` au téléphone, `/accueil` au
bureau). Menu : groupe « Référentiels » → « Matières, classification, fournisseurs » (`/catalogue`) et
« Qualités et recettes » (`/qualites`), rôles `['achats']`.

`peut('achats')` (`lib/session.tsx:34`) est vrai pour achats **et** direction. Comme la page n'est ouverte
qu'à ces deux rôles, toutes les branches « lecture seule » du catalogue (`!modifiable`, `lectureSeule`)
sont **inatteignables** en pratique (voir anomalies). Seuls deux endroits distinguent vraiment la direction :
l'onglet Rôles de la classification (`compte.role === 'direction'`) et toute la page Qualités.

---

### 1. CATALOGUE

#### 1.0 Page « Matières, classification, fournisseurs » — `/catalogue` (`?onglet=matieres|classification|fournisseurs`)

- **Fichiers** : `pages/Catalogue.tsx`.
- **Rôles** : achats, direction (garde de route). Alimentation : pas de menu, route refusée.
- **Paramètres d'adresse lus / écrits** (`pages/Catalogue.tsx:9-11, 33-91`) :
  | Paramètre | Valeurs | Effet |
  |---|---|---|
  | `onglet` | `matieres` (défaut, absent de l'adresse), `classification`, `fournisseurs` ; toute autre valeur → `matieres` | onglet affiché ; changer d'onglet **remplace** toute l'adresse (`{}` ou `{onglet}`), donc efface `matiere`, `fournisseur`, `liste`, `fournisseur_filtre` (`:72`) |
  | `matiere` | entier > 0 ou `nouvelle` | ouvre la fiche matière (ou la création) ; écrit à l'ouverture/fermeture (`replace`) |
  | `fournisseur_filtre` | id de fournisseur | pré-pose le filtre « Fournisseur » de la liste des matières (`:38-42`) |
  | `liste` | `composition` (défaut, absent), `type_fil`, `titrage`, `couleur`, `roles` | sous-vue (Bascule) de la classification |
  | `fournisseur` | entier > 0 ou `nouveau` | ouvre la fiche fournisseur (ou la création) |
  `lireId` (`:27-31`) : « 12 » → 12, `nouvelle`/`nouveau` gardé, tout le reste → rien d'ouvert.
- **En-tête** : titre « Matières, classification, fournisseurs » ; sous-titre : « Le référentiel des achats : une nouvelle matière se crée ici, sa référence composée à partir de la classification. On ne supprime pas ce qui a un historique : on le désactive. » Pas d'indicateurs.
- **Onglets** (`:65-73`) :
  | Onglet | Libellé | Compteur |
  |---|---|---|
  | matieres | « Matières » | nombre de matières **actives** |
  | classification | « Classification » | nombre total de valeurs (compositions + types + titrages + couleurs, **actives et désactivées**, rôles exclus) |
  | fournisseurs | « Fournisseurs » | nombre de fournisseurs **actifs** |
- **Données** : `GET /api/articles` (acteur ; le catalogue entier avec stock, `historique`, `historique_raison`, `conditionnement`, `kg_par_ml`, `titrage_unite` — prix retirés pour l'alimentation `referentiels.py:544-563`), `GET /api/fournisseurs` (acteur), `GET /api/classification` (acteur).
- **Liens entrants connus** : `?onglet=matieres&matiere=12`, `?onglet=matieres&fournisseur_filtre=3`, `?onglet=classification&liste=couleur`, `?onglet=fournisseurs&fournisseur=3` (commentaire `:9-11`).

---

#### 1.1 Onglet Matières — `/catalogue` (`?onglet` absent, `?matiere=`, `?fournisseur_filtre=`)

- **Fichiers** : `components/referentiels/CatalogueMatieres.tsx:115-358`.
- **Rôles** : achats, direction. Boutons « Tableur » et « Nouvelle matière » sous `peut('achats')` (toujours vrais ici).
- **Données** : `useCatalogue` (`GET /articles`), `useFournisseursComplets` (`GET /fournisseurs`), `useClassification` (`GET /classification`).
- **Chargement** : « Un instant — chargement : le catalogue… » (tant que catalogue ou classification chargent). Erreur de lecture du catalogue : bandeau d'erreur avec le message.
- **En-tête de carte** : titre « Matières » ; à droite : « Exporter en Excel » (lien), « Tableur », « Nouvelle matière » (principal).
- **Rangée de recherche** (`:210-221`) : `BarreRecherche` placeholder « Plusieurs mots, dans n'importe quel ordre : « rouge 2900 frisé »… » ; à la frappe, plusieurs mots, tout ordre, sans accents. Champs cherchés : référence, désignation, fournisseur, rôle, composition (« code — libellé »), type de fil (« code — libellé »), titrage, couleur (« code — libellé »), code couleur, groupe d'équivalence, code douanier. À droite : « **N** matière(s) · K critère(s) · X kg en stock » (critère(s) seulement si au moins un ; stock = somme des stocks des matières visibles, en kg).
- **Rangée de filtres** (`:222-256`) — 7 listes **liées** + 1 liste d'état :
  | Filtre | Option vide | Options |
  |---|---|---|
  | Rôle | « Rôle : tous » | rôles présents, « Poil (12) » |
  | Fournisseur | « Fournisseur : tous » | nom du fournisseur (valeur = id) |
  | Composition | « Composition : tous » | « PP — Polypropylène (n) » |
  | Type de fil | « Type de fil : tous » | « FRZ — Frisé (n) » |
  | Couleur | « Couleur : tous » | « code — libellé (n) » |
  | Titrage | « Titrage : tous » | code titrage |
  | Unité du titrage | « Unité du titrage : tous » | Dtex, Deniers… |
  | État | — | « Actives » (défaut), « Actives et désactivées », « Désactivées » |
  Filtres liés : chaque liste ne propose que les valeurs que la recherche et les **autres** filtres laissent (`:162-172`), avec le nombre de matières entre parenthèses ; une valeur choisie qui n'a plus de matière reste proposée avec (0). Tri des options : alphabétique français, numérique. Un filtre posé est teinté (`select.modifie` : bordure et fond couleur accent, `referentiels.css:149-152`). Bouton « **Effacer les filtres** » affiché dès qu'il y a un critère (texte ou filtre) : vide le texte et les 7 filtres (**pas** l'état).
- **Tableau** (`Cadre taille="court"`, `table.serre.ref-catalogue`, `:257-337`) :
  | Colonne (libellé exact) | Contenu / unité | Alignement / format | Remarque |
  |---|---|---|---|
  | Référence | référence ; dessous (note) la désignation | gauche, retour à la ligne (max 160 px, `referentiels.css:155-159`), infobulle = référence | |
  | Rôle | code du rôle | gauche | |
  | Fournisseur | nom ; sinon badge « aucun » (ton attention) | gauche | |
  | Composition | code ou « — » ; dessous le libellé s'il diffère du code | gauche | |
  | Type (infobulle « Type de fil, et titrage dessous ») | code type de fil ou « — » ; dessous le titrage | gauche | |
  | Couleur | code couleur de classification ou « — » ; dessous le code couleur fournisseur | gauche | |
  | Prix | `prixUnitaire` : « 12,50 USD/kg » ou « 3,20 MAD/ml » ; « — » si prix nul ; si prix au mètre : dessous le prix ramené au kilo « X MAD/kg » | droite, 2 décimales | |
  | Stock min. + note « couv. min » (infobulle « Stock minimum, et couverture minimum en mois ») | « 500 kg » ou « — » ; dessous « 1,5 mois » | droite | |
  | Conditionnement | voir ci-dessous | gauche | |
  | Groupe | groupe d'équivalence ou « — » ; dessous « priorité N » | gauche | |
  | En stock | « 1 234 kg » ; badge neutre « désactivée » si matière désactivée ; badge **attention** avec les kilos si stock < stock minimum (et stock mini > 0) ; dessous, pour cuir/franges/ruban actifs avec stock : « ≈ 1 020 ml » | droite, entier | |
  **Conditionnement** (`:91-113`) : si unité « kg » et contenance 1 → note « au kilo » ; sinon badge « Palette · 1 080 kg » (ton **accent** si l'unité est déclarée, **neutre** si déduite). Dessous : « bobine 12,50 kg × 96 · mini 500 kg · déduit » (chaque morceau seulement s'il existe ; « déduit » si non déclarée).
  - Tri : celui du serveur (référence croissante), non cliquable. Pas de pagination, pas de pied de tableau.
  - Ligne cliquable (`cliquable`) → ouvre la fiche (`?matiere=ID`). Ligne d'une matière désactivée : `ligne-eteinte` (grisée).
  - Vide : « Aucune matière ne correspond à la recherche et aux filtres. » si le catalogue a des matières dans l'état choisi, sinon « Le catalogue est vide. »
- **Gestes** :
  | Geste | Où | Rôle | Conditions / grisé | Confirmation | Appel API | Succès | Refus |
  |---|---|---|---|---|---|---|---|
  | « Exporter en Excel » (infobulle « Toutes les matières, avec leur classification et leur stock, dans un classeur Excel ») | en-tête carte | tous (lien) | — | — | `GET /api/export/matieres` (ACHATS) → `matieres-AAAA-MM-JJ.xlsx`, feuille « Matières » | téléchargement | 403 si autre rôle |
  | « Tableur » (infobulle « Télécharger le catalogue en tableur, le corriger, le réimporter avec aperçu ») | en-tête carte | achats/direction | — | — | ouvre la fenêtre Tableur (§1.3) | | |
  | « Nouvelle matière » | en-tête carte | achats/direction | — | — | ouvre la fiche vide (`?matiere=nouvelle`) | | |
  | « Effacer les filtres » | rangée de filtres | tous | visible si ≥ 1 critère | — | — | | |
  | clic sur une ligne | tableau | tous | — | — | ouvre la fiche (`?matiere=ID`) | | |
  - Colonnes de l'export matières (`referentiels.py:1486-1495`) : Référence, Désignation, Rôle, Composition, Type de fil, Titrage, Couleur, Code couleur, Fournisseur, Prix, Devise, Unité du prix, Prix / kg, Densité (kg/ml), Unité d'achat, Contenance, « Unité d’achat déclarée ou déduite », Minimum de commande, kg / bobine, Bobines / palette, Stock minimum, Couverture minimum (mois), Groupe, Code douanier, En stock, Active (oui/non) ; titre « Matières — exporté le JJ/MM/AAAA ».

---

#### 1.2 Fenêtre « Fiche matière » (création / modification) — `/catalogue?matiere=ID` ou `?matiere=nouvelle`

- **Fichiers** : `CatalogueMatieres.tsx:360-1121` (`FicheMatiere`), `ChoixClasse.tsx`, `NombrePieces.tsx`, `PiecesJointes.tsx`.
- **Rôles** : `modifiable = peut('achats')` (achats, direction). Non modifiable (inatteignable) : tous les champs grisés, pas de pied, pas de liste « il manque ».
- **Fenêtre** : `Dialogue large`, titre = référence (ou « Nouvelle matière ») + badge neutre « désactivée » si inactive. `sale = change && modifiable` → Échap, fond, × demandent « Des modifications ne sont pas enregistrées. Les abandonner ? » [« Non, continuer la saisie »] [« Oui, abandonner »] (`ui.tsx:325-330`).
- **Données** : `useDevises` (devises), `useCodesDouaniers` (`GET /codes-douaniers`, ACHATS, `retry:false`), `useCatalogue`, `usePieces('article', id)` (`GET /pieces/article/ID`, ACHATS), `POST /articles/composer` (acteur) à chaque changement de classification (temporisé 250 ms).
- **Bandeau du haut** :
  - Matière existante : note « 1 234,0 kg ≈ 1 020 ml en stock · modifiée le 08/10/2026 14:20 par Nadia » (mètres seulement pour cuir/franges/ruban ; 0 décimale) ; liens « **Voir ses lots** » → `/stock?onglet=lots&volet=lots&article=ID` ; « **Ses mouvements de stock** » → `/stock?onglet=mouvements&volet=mouvements&q=<référence encodée>`.
  - Création : note « Choisir d'abord la classification : la référence et la désignation s'écrivent seules, à la manière du catalogue. Une valeur qui manque s'ajoute sur place. On peut ensuite retoucher la référence. »
- **Volets (Onglets dans la fenêtre)** (`:477-483, 669-684`) : « Classification et référence », « Achat », « Conditionnement et stock », « Pièces jointes » (ce dernier seulement pour une matière existante ; compteur = nombre de pièces, « … » pendant la lecture). Un volet où il manque un champ obligatoire affiche le compteur « ! » (si modifiable).
- **Valeurs par défaut d'une création** (`:403-431, 508-523`) : rôle = premier rôle de la classification ; devise MAD ; prix au kg ; actif ; unité d'achat vide (= déduite). Si des filtres étaient posés dans la liste, la création reprend rôle, composition, type de fil, titrage, couleur et fournisseur filtrés (et la devise par défaut de ce fournisseur).

##### Volet « Classification et référence » (`:686-822`)
| Champ (libellé) | Type | Unité | Obligatoire | Défaut | Contrôle / aide |
|---|---|---|---|---|---|
| Composition | `ChoixClasse` (recherche + ajout sur place) | — | non | vide | placeholder « Taper : PP, polyester… » |
| Type de fil | `ChoixClasse` | — | non | vide | « Taper : FRZ, shrink… » |
| Titrage | `ChoixClasse` | — | non | vide | « Taper : 2900 Dtex… » |
| Couleur | `ChoixClasse` | — | non | vide | « Taper : rouge, beige… » |
| Code couleur | texte | — | non | vide | aide « celui du fournisseur : 7612, A-304… » ; max 32 (serveur) |
| Suffixe fournisseur | texte | — | non | vide (**non enregistré** : ne sert qu'à composer la référence) | aide « la marque de fin du fournisseur : Hs, Oz, Tat… » |
| Référence | texte, police mono, large | — | oui (≥ 2 caractères) | composée | encadré rouge (`manque`) + message « Une autre matière porte déjà cette référence. » si une autre matière du catalogue a la même ; aides : « composée à partir de la classification » (référence non retouchée) ou « La classification compose : `<réf>` (déjà au catalogue) [la reprendre] » quand la composée diffère de la saisie |
| Désignation | texte (duo) | — | non | composée (couleur atelier + code couleur) | max 160 |
| Rôle dans le tapis | liste des rôles (ordre de la classification) ; « Cuir (au mètre) » pour un rôle au mètre | — | oui | 1er rôle | |
| Densité (kg / ml) | nombre (pas libre) — **affiché seulement si le rôle est au mètre** | kg par mètre linéaire | oui pour cuir, franges, ruban | 0 | aide « obligatoire pour le cuir, les franges, le ruban : le stock est en kilos, la recette dit des mètres par m² — la densité en fait des kilos, ramène un prix au mètre au kilo, et montre les mètres à titre indicatif » |

**Référence composée** (`:537-561`) : à chaque changement de composition / type / titrage / couleur / code couleur / suffixe, `POST /articles/composer {composition, type_fil, titrage, couleur, couleur_code, suffixe}` → `{reference, existe, designation}` (serveur `referentiels.py:744-757` : `classification.composer(...)` avec la valeur et l'unité du titrage, le libellé de la couleur). Tant que la référence n'a pas été retouchée à la main (création), elle et la désignation sont remplacées ; dès qu'on tape dans « Référence », elle devient libre ; « la reprendre » la réimpose. Une matière existante part en référence libre.

**ChoixClasse** (`ChoixClasse.tsx`) — sous-composant de saisie :
- Champ qui affiche « code — libellé » de la valeur choisie ; au focus il se vide pour chercher ; liste déroulante des valeurs **actives** (+ la valeur actuelle même désactivée), filtrées sur code, libellé, famille, composition détaillée ; 60 premières, puis « 60 premières sur N : affiner la recherche. » ; chaque option montre « code — libellé » et en détail « famille · composition détaillée ». Vide sans texte : « Aucune valeur. » ; rien trouvé et pas le droit d'ajouter : « Rien ne correspond. »
- Entrée : choisit la valeur dont le code est tapé en entier, sinon la seule trouvée, sinon propose l'ajout ; Échap ferme.
- Option « **+ Ajouter « XYZ » »** (détail « nouvelle valeur de la classification (Entrée) ») si le texte ne correspond à aucun code exact. Code proposé en MAJUSCULES pour composition et type de fil ; pour le titrage, « 2900 dtex » est éclaté en valeur 2900 et unité normalisée (Dtex, Deniers, Nm, Tex, Nec).
- Bouton « × » (infobulle « Retirer cette valeur ») vide le choix.
- Panneau d'ajout en ligne (`saisie-ligne`) : titre « Ajouter une composition à la classification » (un type de fil / un titrage / une couleur) ; champs « Code » (aide « valeur et unité : « 2900 Dtex » » pour un titrage, sinon « tel qu’il s’écrit dans la référence ») + champs propres à la liste (voir §1.4 `CHAMPS_AJOUT`) ; note « Elle rejoint la classification et se choisit aussitôt pour cette matière. » ; boutons « Annuler » et « Ajouter « CODE » » (grisé si code vide ou envoi en cours) → `POST /classification/{liste}` (ACHATS) ; la valeur créée est aussitôt choisie. Refus : « « X » existe déjà. » (409).

##### Volet « Achat » (`:824-979`)
| Champ | Type | Unité | Obligatoire | Défaut | Contrôle / aide |
|---|---|---|---|---|---|
| Fournisseur | liste « — aucun — » + fournisseurs **actifs** (+ l'actuel même désactivé), « Nom (PAYS) » | — | oui si la matière est en service (encadré rouge sinon) | vide ou fournisseur filtré | aide : « PAYS · délai 60 j · devise par défaut USD » (pays vide → « Maroc ») ; sans fournisseur et active : « obligatoire pour une matière en service : le plan d’achat sait ainsi à qui la commander ». En **création**, choisir un fournisseur reprend sa devise par défaut (pas en modification). |
| Prix d'achat | nombre + « DEVISE / » + liste d'unité `kg`/`ml` (infobulle « L'unité du prix : au kilo, ou au mètre pour un fournisseur qui facture au mètre. Le stock reste en kilos. ») | devise / kg ou ml | non | 0 | aide : prix au mètre avec densité → « soit 4,10 MAD/kg — le stock et tous les calculs sont au kilo » (prix ÷ densité) ; prix au mètre sans densité → « au mètre : saisir la densité pour le ramener au kilo » ; au kilo → « le dernier prix confirmé d’une commande s’y inscrit » |
| Densité (kg / ml) | nombre — **seulement si prix au mètre et rôle non linéaire** | kg/ml | oui dans ce cas | 0 | aide « obligatoire pour un prix au mètre : il se ramène au kilo par elle » |
| Devise | liste des devises actives (+ l'actuelle) « USD — Dollar » ; repli MAD si la liste ne charge pas | — | oui | MAD | aide « celle du prix ; un bon de commande par devise » |
| Unité d'achat | texte avec suggestions : Fût, Sac, Big-bag, Palette, Bobine, Carton, Rouleau ; placeholder « déduite : Palette » | — | non | vide = déduite | aide : déclarée → « déclarée : le plan d’achat commande dans cette unité » ; vide → « vide = déduite : Palette (1 080 kg) — palette si la bobine et les bobines par palette sont connues, sinon bobine, sinon kilo » |
| Contenance (kg par <unité>) | nombre — seulement si unité déclarée | kg | oui si unité déclarée | 0 | aide « obligatoire pour une unité déclarée : une colle en fûts de 200 kg se déclare, elle ne se devine pas » |
| Minimum de commande (kg) | nombre | kg | non | 0 | aide « Le plan d'achat ne proposera jamais moins » |
| Code douanier | liste « — aucun — » + codes actifs (+ l'actuel) « 5402.47.00.00 — Fils de PP (10,0 %) » ; si la liste est en erreur : champ texte libre | — | non | vide | aide : code choisi → « libellé (ou « sans libellé ») · droits 10,0 % » ; liste en erreur → « liste des codes douaniers indisponible : taper le code » ; sinon « sert à prévoir et vérifier les droits de douane d’un dossier d’importation » |

Unité déduite (`:464-469`, même règle que le serveur `referentiels.py:456-468`) : bobine et bobines/palette connues → « Palette » de (kg/bobine × bobines) kg ; bobine seule → « Bobine » ; sinon « kg » (1). Envoi : unité vide → `unite_achat="kg"`, `contenance_achat=1`.

##### Volet « Conditionnement et stock » (`:981-1025`)
| Champ | Unité | Défaut | Aide |
|---|---|---|---|
| kg / bobine | kg | 0 | « au catalogue ; le poids mesuré du lot sert aux sorties en bobines » |
| Bobines par palette | nombre | 0 | si bobine et bobines connues : « une palette ≈ 1 080 kg » ; sinon « avec le poids d’une bobine : la palette devient l’unité d’achat déduite » |
| Stock minimum (kg) | kg | 0 | « sous ce seuil, la matière est signalée » |
| Couverture minimum (mois) | mois | 0 | « mois de consommation à garder d'avance » (serveur : ≤ 60) |
| Groupe d'équivalence | texte + suggestions (groupes existants, triés) | vide | « des matières interchangeables portent le même groupe » |
| Priorité dans le groupe | entier (pas 1) ; **grisé tant que le groupe est vide** | vide | « la plus petite passe en premier » (serveur : 0 à 100 ; envoyée `null` sans groupe) |

##### Volet « Pièces jointes » (matière existante) (`:1027-1034`)
Note « Fiche technique, certificat, photo d'un échantillon : ce qui décrit la matière, rangé avec elle. » puis composant `PiecesJointes objet="article"` :
- Bouton « Joindre un document… » (« Envoi… » pendant l'envoi) + note « ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; glisser-déposer (cadre pointillé au survol) ; plusieurs fichiers ; types acceptés `.pdf,image/*,.txt,.csv,.xlsx,.xls,.ods,.docx,.doc,.odt,.zip`.
- Tableau (Cadre dialogue) : Document (lien de téléchargement, infobulle « Télécharger le document »), Genre (PDF / Image / Tableur / Document / Archive / Texte), Taille (o, Ko, Mo, droite), Par, Joint le (horodatage), [Retirer]. Vide : « Aucun document joint. »
- Messages : « « nom » est trop lourd : 20 Mo au plus. » (écran) ; succès « « nom » joint. » / « N documents joints. » / « « nom » retiré. » ; serveur : « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. », « Fichier trop lourd (20 Mo au plus). », « Document inconnu. » (404), « Pièce introuvable. » (404). Routes : `GET/POST /pieces/article/ID`, `GET /piece/ID/fichier`, `DELETE /piece/ID` (toutes ACHATS) ; le retrait garde le fichier sur disque et se trace au journal.
- « Retirer » : Confirmer « Retirer ce document ? » / « Oui, retirer », infobulle « Retirer « nom » de la liste (le retrait est tracé) ».

##### Liste « Pour enregistrer, il manque » (`:620-631, 1045-1060`)
Note « Pour enregistrer, il manque : la référence (onglet Classification et référence), … . » — chaque « onglet X » est un lien qui ouvre ce volet. Cas :
- « la référence » (< 2 caractères) → Classification ;
- « le rôle » → Classification ;
- « la densité (kg par mètre linéaire) » si rôle au mètre **ou** prix au mètre et densité nulle → Classification (rôle au mètre) ou Achat ;
- « le fournisseur » si active sans fournisseur → Achat ;
- « la contenance d'une unité d'achat (Fût) » si unité déclarée sans contenance → Achat.

##### Gestes de la fiche
| Geste | Où | Rôle | Conditions / grisé (infobulle exacte) | Confirmation | Appel API | Succès | Refus / erreurs |
|---|---|---|---|---|---|---|---|
| « Créer la matière » | pied | achats/direction | grisé si envoi, s'il manque quelque chose, ou si la référence existe déjà | — | `POST /articles` (ACHATS) | « Matière créée : elle se commande dès maintenant. » ; la fenêtre reste ouverte sur la matière créée (l'adresse prend `?matiere=ID`) | voir messages serveur ci-dessous |
| « Enregistrer » | pied (matière existante) | idem | grisé si envoi, manque, référence en double, **ou rien de changé** | — | `PUT /articles/ID` avec `version` lue | « Fiche enregistrée. » | 409 conflit → bandeau « Recharger la fiche » |
| « Recharger la fiche » | sous les messages, après un conflit | | — | — | relit `GET /articles` | « Fiche rechargée dans sa dernière version : refaire la modification. » ; texte à côté du bouton : « La fiche affichée n'est plus la dernière : la recharger avant de modifier. » | |
| « Désactiver » | pied (matière active) | | grisé si envoi ou **changements non enregistrés** ; infobulle « Enregistrer d'abord les changements » sinon « Ne plus la proposer aux commandes ni aux recettes » | Confirmer (danger) : « Désactiver « REF » ? Elle ne sera plus proposée aux commandes ni aux recettes ; son historique et son stock restent. » / « Oui, désactiver » | `PUT /articles/ID` avec `actif:false` (toute la fiche revalidée) | « Matière désactivée. » | mêmes contrôles qu'un enregistrement |
| « Réactiver » | pied (matière désactivée) | | grisé si envoi, changements, ou pas de fournisseur ; infobulle « Choisir d’abord son fournisseur (onglet Achat) » sinon « La remettre en service » | aucune | `PUT /articles/ID` `actif:true` | « Matière réactivée. » | |
| « Supprimer » | pied (matière existante) | | grisé si envoi, `historique` (trace) ou pièces jointes ; infobulles : pièces → « Elle a des pièces jointes : les retirer d’abord (onglet Pièces jointes), ou la désactiver. » ; trace dans recettes/métiers → « Elle figure dans des recettes : l’en retirer d’abord, ou la désactiver. » ; autre trace → « Elle figure dans des mouvements de stock : elle appartient à l’historique, la désactiver plutôt. » ; sinon « Supprimer du catalogue une matière qui n’a jamais servi » | Confirmer (danger) « Supprimer définitivement « REF » ? » / « Oui, supprimer » | `DELETE /articles/ID` (ACHATS) | ferme la fenêtre (pas de message) | « « REF » figure dans … » (voir ci-dessous) |
| « Fermer » / « Abandonner les modifications » | pied | | libellé selon changement ; infobulle si changé « Fermer sans enregistrer : les modifications sont perdues » | **aucune** (ferme directement, contrairement au ×) | — | | |
| « la reprendre » | aide de Référence | | si la composée diffère | — | — | | |
| « Voir ses lots », « Ses mouvements de stock » | bandeau | | matière existante | — | navigation | | |

**Traces qui interdisent la suppression** (`referentiels.py:501-528`) et raison affichée (`historique_raison`) : « des mouvements de stock », « des lots en stock ou passés », « des commandes », « des réceptions », « des ordres de fabrication », « des opérations (brouillons compris) », « des dossiers d'importation », « des recettes », « des fils montés sur les métiers », « des pièces jointes ».
Message serveur (`:531-536`) : recettes / fils montés / pièces jointes → « « REF » figure dans des recettes : l'en retirer d'abord, ou désactiver la matière. » ; autres → « « REF » figure dans des commandes : elle appartient à l'historique. La désactiver plutôt que la supprimer. » (409).

**Contrôles et refus serveur à l'enregistrement** (`referentiels.py:427-454, 566-668`) :
- Pydantic : référence 2-160 car. ; désignation ≤ 160 ; rôle ≤ 32 ; composition/type ≤ 32 ; titrage ≤ 48 ; couleur ≤ 64 ; code couleur ≤ 32 ; densité 0-1000 ; prix 0-10 000 000 ; devise ≤ 3 ; unité d'achat ≤ 32 ; contenance 0-1e7 ; minimum 0-1e9 ; kg/bobine 0-1000 ; bobines/palette 0-10 000 ; stock min 0-1e9 ; couverture 0-60 mois ; groupe ≤ 64 ; priorité 0-100 ; code douanier ≤ 20 (messages pydantic en anglais, joints par « · »).
- « Rôle inconnu : « X ». »
- « Composition inconnue : « X ». L'ajouter d'abord dans la classification. » (de même « Type de fil inconnue », « Titrage inconnue », « Couleur inconnue »).
- « Unité du prix : au kilo (kg) ou au mètre (ml). »
- « Une matière du rôle Cuir (cuir, franges, ruban : comptés au mètre dans les recettes) a besoin de sa densité (kg/ml) : le stock est en kilos. »
- « Un prix au mètre a besoin de la densité (kg/ml) pour se ramener au kilo. »
- « Une matière en service a un fournisseur : sans lui, le plan d'achat ne sait pas à qui la commander (contrôle C05). »
- « Fournisseur inconnu. »
- « Devise inconnue : « XXX ». L'ajouter d'abord (Réglages › Devises). »
- « La commande se compte en kilos (ou en palettes, fûts… de tant de kilos). Un fournisseur qui facture au mètre : choisir le prix « au mètre ». » (unité d'achat « ml »)
- « Une unité d'achat autre que le kilo a besoin de sa contenance (kg par unité). »
- « Code douanier inconnu : « X ». L'ajouter d'abord (Réglages › Codes douaniers). »
- 409 « La matière « REF » existe déjà. »
- 409 « Cette fiche a été modifiée entre-temps par Nadia : rechargez-la pour repartir de sa dernière version, puis refaites la modification. » (l'écran reconnaît « entre-temps » et propose « Recharger la fiche »).
- 404 « Matière introuvable. »
- Chaque création / modification / suppression est tracée au journal (« création matière », « modification matière » avec « ancienne → nouvelle » référence, « suppression matière ») ; `version` +1, `modifie_le`, `modifie_par`.
- Après écriture, l'écran relit : articles, classification, fournisseurs, stock, soldes, plan-achat, besoins, cockpit, contrôles, valorisation, nomenclature, qualités, codes-douaniers (`types.ts:313-314`).

---

#### 1.3 Fenêtre « Le catalogue par tableur » — (ouverte par « Tableur », pas d'adresse)

- **Fichiers** : `TableurMatieres.tsx` ; serveur `gestion_mp/api/suivi.py:678-838`.
- **Rôles** : achats, direction (bouton) ; routes `GET /import/matieres/modele` et `POST /import/matieres` : ACHATS.
- **Fenêtre** : `Dialogue large`, titre « Le catalogue par tableur » ; `sale` = un aperçu lu, non appliqué, avec au moins une matière à écrire.
- **Mode d'emploi en tête** (liste numérotée) :
  1. « Télécharger le modèle : c'est le catalogue actuel, une matière par ligne. » + lien « **Télécharger le modèle (.xlsx)** » → `/api/import/matieres/modele` (fichier `matieres.xlsx`, feuille « Matières »).
  2. « Le corriger ou le compléter dans Excel. Une valeur de classification, un rôle, une devise ou un fournisseur doit déjà exister ; une matière nouvelle a besoin de son rôle et de son fournisseur. »
  3. « Le relire ici : rien n'est écrit tant qu'on n'a pas vu ce qui changera et cliqué « Appliquer ». »
- **Format attendu** (`suivi.py:680-698`) — colonnes du modèle, dans cet ordre (intitulés exacts de la 1re ligne) :
  « Référence », « Désignation », « Rôle », « Composition », « Type de fil », « Titrage », « Couleur », « Code couleur », « Densité », « Fournisseur » (nom), « Prix », « Unité du prix » (kg/ml), « Devise », « Unité d'achat », « Contenance », « Minimum de commande », « kg / bobine », « Bobines par palette », « Stock minimum », « Couverture minimum (mois) », « Groupe d'équivalence », « Code douanier », « En service » (oui/non) ; plus une colonne d'information jamais relue « Se commande en (lecture seule) » (« Palette de 1080 kg (déduit) », « kg »…).
  - Seule « Référence » est obligatoire ; les autres colonnes peuvent manquer ou être dans un autre ordre (lues par intitulé). Ancien intitulé encore lu : « Poids d'une bobine » = « kg / bobine ». L'ancienne colonne « Unité » (unité de stock) n'est plus lue.
  - Une ligne sans référence est sautée. **Une case vide ne change rien** (on ne peut pas vider un champ par le tableur). Nombres : virgule ou point. « En service » vrai si « oui », « 1 », « vrai », « true », « x ». Fournisseur : par nom, sans casse. Une matière absente du tableur n'est jamais supprimée.
- **Contrôles ligne par ligne** (messages exacts, `suivi.py:770-808`) :
  - « densite n'est pas un nombre » (nom de champ technique : densite, prix, contenance_achat, minimum_commande, poids_bobine, bobines_palette, stock_min, couv_min_mois)
  - « fournisseur inconnu « X » »
  - « composition inconnu « X » (l'ajouter d'abord à la classification) » (de même type_fil, titrage, couleur, role, devise, code_douanier)
  - « unité du prix : kg ou ml »
  - « une matière en service a un fournisseur » (matière existante)
  - « un prix au mètre a besoin de la densité (kg par mètre) »
  - « une matière du rôle Cuir a besoin de sa densité (kg par mètre) : la recette la compte en mètres, le stock en kilos »
  - « la commande se compte en kilos : un prix au mètre se dit dans « Unité du prix » »
  - « une matière nouvelle a besoin de son rôle »
  - « une matière nouvelle a besoin de son fournisseur »
  Erreurs de fichier : « Tableur illisible : <détail technique> » ; « La colonne « Référence » est obligatoire (télécharger le modèle). » ; à l'application avec erreurs : « N ligne(s) en erreur : corriger le tableur d'abord, rien n'a été écrit. »
- **Choix du fichier** : bouton-étiquette « Choisir le tableur à relire… » (puis « Choisir un autre tableur… »), `.xlsx` ; nom du fichier affiché ; « Lecture… » pendant l'envoi. Le choix lance aussitôt l'aperçu `POST /import/matieres?appliquer=false` (multipart, champ `fichier`).
- **Indicateurs de l'aperçu** :
  | Indicateur | Valeur | Détail | Ton |
  |---|---|---|---|
  | Créées | nb | « matières nouvelles » | ok si > 0 |
  | Modifiées | nb | « au moins un champ change » | — |
  | Inchangées | nb | « rien à faire » | — |
  | Erreurs | nb | « à corriger dans le tableur » / « tableur juste » | critique si > 0, sinon ok |
- **Volets** (Onglets) : « Erreurs (n) », « Modifiées (n) », « Créées (n) » ; volet ouvert d'office : Erreurs s'il y en a, sinon Modifiées, sinon Créées.
  | Volet | Colonnes | Remarque |
  |---|---|---|
  | Erreurs | Ligne (n° Excel, droite) · Référence · Ce qui ne va pas (problèmes joints par « ; ») | lignes `ligne-alerte` |
  | Modifiées | Référence · Champs qui changent (noms traduits : Désignation, Rôle, Composition, Type de fil, Titrage, Couleur, Code couleur, Densité, Fournisseur, Prix, Devise, Unité d'achat, Contenance, Minimum de commande, kg / bobine, Bobines par palette, Stock minimum, Couverture minimum, Groupe d'équivalence, En service) | les valeurs avant/après (renvoyées par le serveur, `detail`) ne sont **pas** montrées |
  | Créées | Référence créée | |
  Vide : « Rien ici. »
- **Pied** : note — erreurs : « Corriger les erreurs dans le tableur, puis le relire : un tableur en erreur n’écrit rien. » ; sinon « N matière(s) seront écrites. » ; rien : « Rien à écrire : le tableur dit la même chose que le catalogue. »
- **Gestes** :
  | Geste | Conditions / grisé | Confirmation | Appel | Succès | Refus |
  |---|---|---|---|---|---|
  | « Télécharger le modèle (.xlsx) » | — | — | `GET /import/matieres/modele` | téléchargement | |
  | « Choisir le tableur à relire… » | — | — | `POST /import/matieres?appliquer=false` | aperçu affiché | messages ci-dessus |
  | « Appliquer » (visible si aperçu non appliqué) | grisé si envoi, erreurs, ou rien à écrire ; infobulle « Des lignes sont en erreur : corriger le tableur d’abord » sinon « Créer et modifier les matières lues » | Confirmer (principal) « Écrire N matière(s) au catalogue ? » / « Oui, appliquer » | `POST /import/matieres?appliquer=true` (même fichier) | « Tableur appliqué : le catalogue est à jour, chaque changement est au journal. » ; le bouton disparaît | « N ligne(s) en erreur… » |
  | « Fermer » | — | aucune (le × et Échap demandent « Les abandonner ? » si `sale`) | | | |
  À l'application : création avec `modifie_par`, modification champ par champ avec `version` +1 ; journal « import des matières » « N créée(s), M modifiée(s) ».

---

#### 1.4 Onglet Classification — `/catalogue?onglet=classification` (`&liste=composition|type_fil|titrage|couleur|roles`)

- **Fichiers** : `CatalogueClassification.tsx`, `ChoixClasse.tsx` (`CHAMPS_AJOUT`, `NOMS_LISTES`, `UNITES_TITRAGE`).
- **Rôles** : achats et direction tiennent compositions, types, titrages, couleurs (écran `peut('achats')`, serveur ACHATS) ; **seule la direction** tient les rôles (écran `compte.role === 'direction'`, serveur DIRECTION).
- **Données** : `GET /classification` → 4 listes de valeurs avec `articles` (nombre de matières qui la portent) + `roles` (avec `articles`, `qualites` = qualités où le rôle a un poids > 0, `de_base`).
- **Chargement / erreur** : « Un instant — chargement : la classification… » ; erreur : bandeau avec le message.
- **Carte** : titre « Classification des matières » suivi d'une **Bascule** de 5 vues : « Compositions · N », « Types de fil · N », « Titrages · N », « Couleurs · N » (N = valeurs **actives**), « Rôles · N » (tous). Écrit `?liste=` (rien pour composition). À droite (achats/direction, pas sur la vue Rôles) : bouton « Relire les références » (§1.6).

##### 1.4.a Sous-vues Compositions / Types de fil / Titrages / Couleurs (`Liste`, `:124-283`)
- **Texte d'explication** (note) :
  - Compositions : « La matière du fil : PP (polypropylène), PES (polyester), PA (polyamide)… Le code ouvre la référence. »
  - Types de fil : « La façon du fil : frisé, shrink, BCF, filé… Il suit la composition dans la référence. »
  - Titrages : « La grosseur du fil, avec son unité : « 2900 Dtex ». Sans valeur ni unité saisies, elles se lisent dans le code. »
  - Couleurs : « Les couleurs du catalogue, telles que l’atelier les nomme, regroupées par famille (rouges, beiges…). »
- **Rangée** : recherche à la frappe, placeholder « Chercher dans les compositions… » (types de fil / titrages / couleurs), sur code, libellé, famille, valeur, unité, composition détaillée, commentaire ; case « Montrer les valeurs désactivées (N) » (défaut décochée) ; « N valeur(s) » ; bouton principal « Ajouter une composition » / « Ajouter un type de fil » / « Ajouter un titrage » / « Ajouter une couleur ».
- **Tableau** (`Cadre court`) :
  | Colonne | Composition | Type de fil | Titrage | Couleur | Format |
  |---|---|---|---|---|---|
  | Code | ✓ | ✓ | ✓ | ✓ | mono gras |
  | Libellé | ✓ | ✓ | | ✓ | « — » si vide |
  | Famille | ✓ | | | ✓ | |
  | Composition détaillée | ✓ | | | | |
  | Valeur | | | ✓ | | |
  | Unité | | | ✓ | | |
  | Commentaire | ✓ | ✓ | ✓ | ✓ | coupé à 260 px avec « … », infobulle = texte entier ; « — » si vide |
  | Matières | ✓ | ✓ | ✓ | ✓ | droite, nombre de matières qui portent la valeur |
  | État | badge « active » (ok) / « désactivée » (neutre) | | | | |
  | (actions) | « Désactiver »/« Réactiver », « Supprimer » | | | | droite |
  - Tri : par code (serveur). Ligne cliquable (si modifiable) → fenêtre d'édition ; désactivée → `ligne-eteinte`.
  - Vide : « Aucune valeur ne correspond. » ; liste vide : « Aucune valeur. « Relire les références » propose de les déduire des références du catalogue. »
- **Gestes de ligne** :
  | Geste | Conditions / grisé (infobulle) | Confirmation | Appel | Succès | Refus |
  |---|---|---|---|---|---|
  | « Désactiver » / « Réactiver » | grisé pendant un envoi ; infobulle « Ne plus la proposer pour une nouvelle matière ; celles qui la portent la gardent » / « La proposer de nouveau » | aucune | `PUT /classification/{liste}/{code}` (toute la valeur, `actif` inversé) | « « PP » désactivé : il n'est plus proposé pour une nouvelle matière. » / « « PP » réactivé. » | |
  | « Supprimer » | grisé si envoi ou portée par ≥ 1 matière ; infobulle « Portée par N matière(s) : la reclasser d'abord, ou la désactiver » sinon « Supprimer cette valeur, qu’aucune matière ne porte » | Confirmer « Supprimer « PP » ? » / « Oui, supprimer » | `DELETE /classification/{liste}/{code}` | « « PP » supprimé. » | 409 « « PP » est porté par N matière(s) : les reclasser d'abord, ou désactiver la valeur. » ; 404 « Valeur introuvable. » ; « Liste inconnue. » |

##### 1.4.b Fenêtre « Ajouter / modifier une valeur » (`EditionValeur`, `:285-383`)
- `Dialogue` (taille normale), titre « Composition « PP » » (Type de fil / Titrage / Couleur) ou « Ajouter une composition ». `sale` = formulaire modifié.
- Note : modification → « Portée par N matière(s) du catalogue. » + si N > 0 « Désactivée, elle ne sera plus proposée pour une nouvelle matière ; celles qui la portent la gardent. » ; ajout → explication de la liste + « Exemple : « PP » » (« FRZ », « 2900 Dtex », « Rouge »).
- **Champs** :
  | Champ | Listes | Aide | Serveur |
  |---|---|---|---|
  | Code | toutes | — | 1-64 car., obligatoire |
  | Libellé | composition, type de fil, couleur | « Polypropylène, Polyester… » / « Frisé, Shrink, Filament… » / « comme l’atelier la nomme » | ≤ 120 |
  | Famille | composition, couleur (suggestions = familles existantes) | « Synthétique, Naturel, Intrant » / « Rouges, Beiges, Gris… » | ≤ 64 |
  | Composition détaillée | composition | « « 100 % polypropylène » » | ≤ 160 |
  | Valeur | titrage | « lue dans le code si vide » | ≤ 32 ; si vide à l'ajout, le serveur coupe le code « 2900 Dtex » en valeur/unité |
  | Unité | titrage (suggestions Dtex, Deniers, Nm, Tex, Nec) | « Dtex, Deniers, Nm, Tex, Nec » | ≤ 16 |
  | Commentaire | toutes (zone 3 lignes, large) | — | ≤ 500 |
  | case « Active (proposée pour une nouvelle matière) » | toutes | — | défaut cochée |
- Renommer une valeur portée : message info « Changer le code renomme la valeur sur les N matière(s) qui la portent ; leurs références déjà écrites ne changent pas. » (les matières suivent par cascade).
- **Gestes** : « Supprimer » (modification seulement ; grisé si portée, infobulle « Portée par N matière(s) : la reclasser d'abord, ou la désactiver », pas d'infobulle sinon ; Confirmer « Supprimer « CODE » ? » / « Oui, supprimer ») ; « Fermer » / « Abandonner les modifications » (sans confirmation) ; « Ajouter » / « Enregistrer » (grisé si envoi, code vide ou rien modifié) → `POST /classification/{liste}` ou `PUT /classification/{liste}/{ancien code}` ; succès : la fenêtre se ferme (aucun message). Refus : « « X » existe déjà. » (409), « Valeur introuvable. » (404). Journal : « ajout composition », « modification type de fil » (« ancien → nouveau »), « suppression couleur »…

##### 1.4.c Sous-vue Rôles (`Roles`, `:387-537`) — `?liste=roles`
- Note : « Le rôle d'une matière dans le tapis. Chaque qualité donne un poids au m² par rôle, et la recette répartit ce poids entre les fils du rôle. Cuir, franges et ruban se comptent au mètre linéaire dans la recette (ml/m² ; la densité de la matière en fait des kilos, et le stock est en kilos) ; les autres au kilo. L'ordre est celui des listes et des colonnes. » + pour les achats : « Seule la direction ajoute ou modifie un rôle. »
- **Rangée d'ajout (direction)** : champ placeholder « Nouveau rôle (compté au kilo) : Velours… », « ordre » (nombre entier, défaut dernier ordre + 1), bouton « Ajouter le rôle » (grisé si vide ou envoi) → `POST /classification/roles {code, lineaire:false, ordre}` ; succès « Rôle « X » ajouté : il se choisit pour une matière et reçoit un poids dans chaque qualité. » Un nouveau rôle est **toujours au kilo**.
- **Tableau** (pas de recherche) :
  | Colonne | Contenu | Format |
  |---|---|---|
  | Rôle | code gras (ou champ de saisie en renommage) ; « · rôle du calcul » pour les 8 rôles de base | |
  | Compté | badge accent « au mètre (ml) » ou « au kilo » | |
  | Ordre | nombre (champ en modification) | droite |
  | Matières | nb de matières du rôle | droite |
  | Qualités | nb de qualités où il pèse (poids > 0) | droite |
  | (direction) | « Modifier » / « Annuler » + « Enregistrer », « Supprimer » | droite |
  Tri : ordre puis code. Lignes non cliquables. Pas de message vide.
- **Gestes (direction)** :
  | Geste | Conditions / infobulle | Confirmation | Appel | Succès | Refus serveur |
  |---|---|---|---|---|---|
  | « Modifier » | infobulle « Changer l’ordre (le nom reste : rôle du calcul ou déjà porté) » si rôle de base ou porté, sinon « Renommer ou changer l’ordre » ; le nom n'est éditable que pour un rôle ni de base ni porté | — | passe la ligne en édition | | |
  | « Annuler » | en édition | — | — | | |
  | « Enregistrer » | grisé si envoi ou nom vide | — | `PUT /classification/roles/{code} {code, lineaire (inchangé), ordre}` | « Rôle enregistré. » | « « X » est un rôle de base du calcul : il garde son nom. » (409) ; « « X » est porté par des matières ou des qualités : il garde son nom. » (409) ; « Le rôle « Y » existe déjà. » (409) ; « Rôle introuvable. » (404) ; contrôle linéaire ci-dessous |
  | « Supprimer » | grisé si envoi, rôle de base ou porté ; infobulles « Rôle du calcul : il ne se supprime pas » / « Porté par N matière(s) et M qualité(s) : les changer d'abord » / « Supprimer ce rôle, qu’aucune matière ni qualité ne porte » | Confirmer « Supprimer le rôle « X » ? » / « Oui, supprimer » | `DELETE /classification/roles/{code}` | « Rôle « X » supprimé. » | « « X » est un rôle de base du calcul : il ne se supprime pas. » ; « « X » est porté par N matière(s) et M qualité(s) : les changer d'abord. » (409) — les poids à zéro de ce rôle dans les qualités sont effacés |
  Contrôle linéaire (`referentiels.py:112-119`) : « Le calcul compte au mètre Cuir, Franges, Ruban, et eux seuls : « X » se compte au poids. » (ou « au mètre »). Création : « Le rôle « X » existe déjà. » (409, sans casse). Pydantic : code 1-32, ordre 0-999.
  - **Rôles de base du calcul** (`gestion_mp/calcul/modele.py:23-24`) : Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique ; **au mètre** : Cuir, Franges, Ruban.

---

#### 1.5 Fenêtre « Classer le catalogue d'après les références » (bouton « Relire les références »)

- **Fichiers** : `CatalogueClassification.tsx:539-641` ; serveur `referentiels.py:680-741` (ACHATS).
- Bouton « Relire les références » (infobulle « Lire les références et montrer ce qui serait complété, sans rien écrire ») → `POST /catalogue/classer?appliquer=false`.
- `Dialogue tresLarge`, sans garde de saisie. Note : « Chaque référence dit sa composition, son type, son titrage et sa couleur. Les cases vides sont complétées d'après elle ; ce qui est déjà renseigné n'est jamais remplacé. »
- Rien à faire : message succès « Toutes les matières sont déjà classées : rien à compléter. »
- Sinon tableau (`Cadre dialogue`) : Référence · Composition · Type · Titrage · Couleur · Code couleur (seulement les cases qui seraient complétées) ; puis note « Valeurs nouvelles qui seront ajoutées à la classification : Compositions : PP, PES · Types de fil : FRZ · … ».
- Règles serveur : décompose la référence (`classification.decomposer`) ; la couleur prise de la désignation (sans parenthèses, ≤ 40 car.) plutôt que de la référence (« on garde l'atelier ») ; composition et type en majuscules ; valeurs nouvelles créées avec libellé/famille connus.
- Gestes : « Fermer » ; « Classer le catalogue (N matière(s)) » (si propositions et pas encore appliqué ; grisé pendant l'envoi ; infobulle « Écrire la classification déduite dans les cases vides ») → Confirmer « Compléter N matière(s) ? » / « Oui, classer » → `POST /catalogue/classer?appliquer=true` → « Catalogue classé. » ; chaque matière complétée prend version +1 ; journal « classement du catalogue » « N matière(s) complétée(s) ».

---

#### 1.6 Onglet Fournisseurs — `/catalogue?onglet=fournisseurs` (`&fournisseur=ID|nouveau`)

- **Fichiers** : `CatalogueFournisseurs.tsx:113-307`.
- **Rôles** : achats, direction ; « Nouveau fournisseur » sous `peut('achats')`.
- **Données** : `GET /fournisseurs` (acteur) : fiche + `local` (pays vide, MAROC ou MOROCCO), `devises` (nb de matières par devise), `articles`, `commandes`, `receptions`, `pieces`, `delai_mesure_jours` (moyenne commande → réception **validée**, 12 mois glissants, en jours), `livraisons_mesurees`, `empreinte` ; `GET /fournisseurs/performance` (ACHATS, `pilotage.py:497`) → OTIF et score par **nom** de fournisseur.
- **Chargement** : « Un instant — chargement : les fournisseurs… ». Erreur : bandeau.
- **Carte** : titre « Fournisseurs » + note « le délai et la couverture règlent le plan d'achat » ; à droite « Exporter en Excel » (infobulle « Les fiches des fournisseurs dans un classeur Excel », `GET /api/export/fournisseurs/fiches`, ACHATS → `fournisseurs-fiches-AAAA-MM-JJ.xlsx`) et « Nouveau fournisseur ».
- **Filtres** (une rangée) : recherche placeholder « Nom, pays, contact, devise, incoterm, port, banque… » (sur nom, code, pays, contact, téléphone, e-mail, devise, incoterm, mode de paiement, conditions, port, banque, observations) ; origine « Locaux et étrangers » / « Locaux (Maroc) » / « Étrangers (importation) » ; devise « Toutes les devises » + devises vues (par défaut ou pratiquées) — un fournisseur correspond si c'est sa devise par défaut **ou** une devise de ses matières ; état « Fournisseurs actifs » (défaut) / « Actifs et désactivés » / « Désactivés seulement » ; « Effacer les filtres » dès qu'un filtre (texte, origine, devise, état ≠ actifs) est posé (remet tout, état compris) ; « N fournisseur(s) ». Filtres non liés entre eux.
- **Tableau** (`Cadre court`) :
  | Colonne | Contenu | Format | Remarque |
  |---|---|---|---|
  | Fournisseur | nom gras + badge « désactivé » ; dessous le code | | |
  | Pays | pays ou « Maroc » | | |
  | Devises | badges « USD · 12 » par devise pratiquée (triés par nombre décroissant ; la devise par défaut en ton accent) ; plusieurs → note « un bon de commande par devise » ; aucune matière → note « MAD (par défaut) » | | |
  | Délai | « 60 j » ; dessous « mesuré 72 j » (infobulle « Moyenne commande → réception validée, sur N livraison(s) en douze mois ») | droite | |
  | Couverture | « 90 j » ou note « — (réglage général) » si 0 | droite | |
  | Paiement | « Virement à 60 j » (mode + délai) ou « — » ; dessous les conditions | | |
  | Incoterm | incoterm ou « — » ; dessous le port de chargement | | |
  | OTIF (infobulle « Livraisons à l'heure, complètes et conformes ») | badge « 92 % · 12 réc. » ton **critique** si sous-performant, sinon **ok** ; « — » sans note | droite | |
  | Matières | nb de matières du catalogue | droite | |
  | Contact | nom du contact ou « — » ; dessous « téléphone · e-mail » | | |
  - Tri : nom (serveur). Ligne cliquable → fiche (`?fournisseur=ID`) ; désactivé : `ligne-eteinte`.
  - Vide : « Aucun fournisseur ne correspond. » / « Aucun fournisseur pour le moment. »
- Export fiches (`referentiels.py:1499-1517`) : Fournisseur, Code, Pays, Contact, Téléphone, E-mail, Devise par défaut, Devises, Délai déclaré (j), Délai mesuré (j), Couverture (j), Mode de paiement, Paiement à (j), Conditions, Incoterm, Port de chargement, Banque, Matières, Actif.

#### 1.7 Fenêtre « Fiche fournisseur » — `/catalogue?onglet=fournisseurs&fournisseur=ID|nouveau`

- **Fichiers** : `CatalogueFournisseurs.tsx:309-696`.
- **Rôles** : `modifiable = peut('achats')` ; serveur POST/PUT/DELETE `/fournisseurs` : ACHATS.
- `Dialogue large`, titre = nom (ou « Nouveau fournisseur ») + badge « désactivé » ; `sale = change && modifiable`.
- **Indicateurs (fournisseur existant)** :
  | Indicateur | Valeur | Détail | Ton |
  |---|---|---|---|
  | Matières | nb de matières | « 12 en USD, 3 en MAD » ou « aucune au catalogue » | — |
  | Délai | délai déclaré « 60 j » | « mesuré 72 j sur 5 livraison(s) » ou « déclaré ; pas encore de livraison mesurée » | **attention** si mesuré > 1,2 × déclaré avec ≥ 3 livraisons (aucune infobulle ne le dit) |
  | Livraisons parfaites (OTIF) | « 92 % » ou « — » | « N réception(s) notée(s) » / « aucune réception notée » | critique si sous-performant, ok sinon |
  | Score | « 78 / 100 » ou « — » | badge du classement (premier mot — l'emoji — retiré ; « À surveiller » affiché « ATTENTION ») + action conseillée ; sinon « se calcule dès la première réception » | badge : Stratégique → ok, Standard → neutre, surveiller → attention, challenger → critique |
- Rangée : « N commande(s) · M réception(s) » ; liens « **Voir ses matières** » (si ≥ 1 matière) → `/catalogue?onglet=matieres&fournisseur_filtre=ID` (empile l'historique) ; « **Voir l'analyse des fournisseurs** » → `/analyse?onglet=fournisseurs`.
- **Volets** (fournisseur existant) : « Fiche » (« Fiche • » si modifié) et « Pièces jointes (n) » (même composant que §1.2, objet `fournisseur`, note « Contrat, coordonnées bancaires (RIB), certificats, catalogue du fournisseur : rangés avec sa fiche. »).
- **Formulaire « Fiche »** (trois intertitres) :
  | Section | Champ | Type | Défaut création | Aide / contrôle |
  |---|---|---|---|---|
  | Identité et contact | Nom (duo) | texte | vide | obligatoire ≥ 2 car. (≤ 160) ; unique sans casse |
  | | Code | texte | vide | « abréviation interne, facultative » (≤ 32) |
  | | Pays | liste « — (MAROC) », pays connus (ceux des fournisseurs en majuscules + MAROC, TURKEY, CHINA, INDE, BELGIUM, SPAIN, ITALY, EGYPT, PORTUGAL, FRANCE, GERMANY, triés), « Autre pays… » → champ libre en majuscules + bouton « Liste » (infobulle « Revenir à la liste des pays ») | vide | aide « MAROC ou vide : fournisseur local » / « un pays absent de la liste, écrit en majuscules » ; serveur : majuscules, espaces réduits |
  | | Contact | texte | | ≤ 120 |
  | | Téléphone | texte | | ≤ 60 |
  | | E-mail (duo) | e-mail | | ≤ 160 (aucune vérification de forme) |
  | Approvisionnement | Délai (jours) | entier | **60** | « de la commande à l'arrivée à l'usine : il règle le stock projeté » ; > 0 et ≤ 730 |
  | | Couverture (jours) | entier | 0 | « consommation qu'une commande doit couvrir ; 0 = le réglage général » ; ≤ 730 |
  | | Devise par défaut | liste devises actives (+ actuelle), repli MAD | MAD | « pré-remplit une nouvelle matière ; chaque prix garde la sienne » |
  | | Incoterm | liste « — », EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU, DDP (+ valeur actuelle hors liste) | vide | ≤ 20 |
  | | Port de chargement | texte | | « d'où part la marchandise : Mersin, Ningbo… » |
  | Paiement | Mode de paiement | texte + suggestions : Virement, Crédit documentaire (LC), Remise documentaire, Traite / LCN, Chèque, Espèces, Open account | | ≤ 40 |
  | | Délai de paiement (jours) | entier | 0 | « sert au calcul du crédit fournisseur » ; ≤ 730 |
  | | Banque (duo) | texte | | « la domiciliation du paiement » |
  | | Conditions de paiement (large) | texte, placeholder « 30 % à la commande, solde à l'expédition… » | | ≤ 160 |
  | | Observations (large) | zone 3 lignes | | ≤ 2000 |
- « Pour enregistrer, il manque : le nom, le délai d'approvisionnement, un délai de deux ans au plus, une couverture de deux ans au plus, un délai de paiement de deux ans au plus. » (selon les cas).
- **Gestes** :
  | Geste | Conditions / infobulle | Confirmation | Appel | Succès | Refus |
  |---|---|---|---|---|---|
  | « Créer le fournisseur » | grisé si envoi ou manque | — | `POST /fournisseurs` | « Fournisseur créé : ses matières peuvent maintenant le désigner. » ; la fenêtre reste ouverte (adresse `?fournisseur=ID`) | « Le fournisseur « X » existe déjà. » (409) ; « Devise inconnue : « XXX ». L'ajouter d'abord (Réglages › Devises). » |
  | « Enregistrer » | grisé si envoi, manque ou rien changé | — | `PUT /fournisseurs/ID` + `empreinte` | « Fiche enregistrée. » | 409 « Ce fournisseur a été modifié(e) entre-temps sur un autre poste : rechargez pour repartir de sa dernière version, puis refaites la modification. » → « Recharger la fiche » (texte « La fiche affichée n'est plus la dernière : la recharger avant de modifier. », succès « Fiche rechargée dans sa dernière version : refaire la modification. ») ; nom en double ; « Fournisseur introuvable. » |
  | « Désactiver » | grisé si envoi ou changements ; infobulle « Enregistrer d'abord les changements » / « Ne plus le proposer » | Confirmer « Désactiver « NOM » ? Il ne sera plus proposé pour une commande ni une matière ; son historique reste. » / « Oui, désactiver » | `PUT` `actif:false` | « Fournisseur désactivé. » | |
  | « Réactiver » | grisé si envoi ou changements ; **pas d'infobulle** | aucune | `PUT` `actif:true` | « Fournisseur réactivé. » | |
  | « Supprimer » | grisé si envoi ou historique (matières, commandes, réceptions, pièces jointes) ; infobulle « Il a 3 matière(s), 2 commande(s), 1 réception(s), 1 pièce(s) jointe(s) à retirer d'abord : le désactiver plutôt » ou « Supprimer un fournisseur qui n’a jamais servi » | Confirmer « Supprimer définitivement « NOM » ? » / « Oui, supprimer » | `DELETE /fournisseurs/ID` | ferme la fenêtre | « « NOM » a des matières du catalogue : le désactiver plutôt que le supprimer. » (de même « des commandes », « des réceptions », « des lots », « des opérations », « des factures ») ; « « NOM » a des pièces jointes : les retirer d'abord, ou le désactiver. » (409) |
  | « Fermer » / « Abandonner les modifications » | infobulle si changé « Fermer sans enregistrer : les modifications sont perdues » | aucune | | | |
  Journal : « création fournisseur », « modification fournisseur », « suppression fournisseur ». Relecture après écriture : fournisseurs, articles, plan-achat, cockpit, contrôles, performance.

---

#### 1.8 Codes douaniers — **pas dans le catalogue** : `/reglages?onglet=codes` (onglet « Codes douaniers », libellé court « Douane »)

- **Où** : page Réglages (`pages/Reglages.tsx:51-55, 86, 122`), sous-titre « Les positions du tarif douanier et leur taux de droits : de quoi prévoir et vérifier les droits d'un dossier. » Le catalogue n'en a que la **liste de choix** dans la fiche matière (volet Achat, §1.2).
- **Fichiers** : `components/importations/ReglagesCodesDouaniers.tsx` ; serveur `referentiels_import.py:200-278`.
- **Rôles** : onglet visible **direction seule** (les achats ne voient que l'onglet Devises des Réglages). Serveur : `GET /codes-douaniers` ACHATS (lecture pour la fiche matière) ; POST/PUT/DELETE **DIRECTION**.
- **Chargement / erreur** : « Un instant — chargement : les codes douaniers… » ; erreur : bandeau.
- **Carte** « Codes douaniers », bouton principal « Nouveau code ». Note : « La position du tarif douanier et son taux de droits. Chaque matière porte son code (fiche matière, au catalogue) : un dossier d'importation en déduit les droits attendus — taux × valeur en douane (achat + fret) — et signale l'écart avec la quittance. »
- Recherche à la frappe placeholder « Code, libellé… » ; « N code(s) ». Pas de filtre d'état (actifs et désactivés mêlés).
- **Tableau** : Code (mono gras) · Libellé (« — ») · Taux de droits (« 10,0 % », droite) · Matières (droite) · État (badge « actif » ok / « désactivé » neutre). Tri par code. Ligne cliquable (infobulle « Modifier le code »). Vide : « Aucun code ne correspond. » / « Aucun code douanier. « Nouveau code » : 5402.47.00.00 (fils de polypropylène), son taux de droits… »
- **Fenêtre** « Code douanier X » / « Nouveau code douanier » (`sale` gardé) :
  | Champ | Type | Contrôle / aide |
  |---|---|---|
  | Code | mono, max 20, focus en création | aide « N matière(s) le portent : elles suivront la correction » ou « chiffres et points (ex. 5402.47.00.00) » ; serveur : espaces retirés, `\d[\d.]{1,19}`, sinon « Value error, un code douanier s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00) » |
  | Libellé (duo) | max 160, placeholder « Fils de polypropylène… » | |
  | Taux de droits (%) | nombre saisi en % (×100), pas 0,1, placeholder « ex. 10 » | aide « sur la valeur en douane : achat + fret » ; hors 0-100 % : « Un taux de droits va de 0 à 100 %. » |
  | case « code actif (proposé dans la fiche matière) » | défaut cochée | |
- **Gestes** : « Supprimer » (modification ; grisé si porté par des matières ; infobulle « N matière(s) portent ce code : le leur retirer, ou le désactiver » / « Supprimer ce code, qu’aucune matière ne porte » ; Confirmer « Supprimer ce code ? » / « Oui, supprimer » ; `DELETE /codes-douaniers/{code}` ; refus « N matière(s) portent ce code : le leur retirer d'abord, ou le désactiver. ») ; « Annuler » (sans confirmation) ; « Créer le code » / « Enregistrer » (grisé si envoi, code vide, taux vide ou hors bornes, ou rien changé ; `POST` / `PUT /codes-douaniers/{code}` ; refus « Le code douanier « X » existe déjà. » 409, « Code douanier introuvable. » 404). Succès : fermeture sans message ; relit importations, codes, dossiers, articles. Journal « création / modification / suppression code douanier » (« ancien · 10,00 % → nouveau · 12,00 % · désactivé »).

---

### 2. QUALITÉS ET RECETTES

#### 2.0 Page « Qualités et recettes » — `/qualites` (`?onglet=nomenclature`, `?qualite=ID`)

- **Fichiers** : `pages/Qualites.tsx`.
- **Rôles** : achats et direction (garde). `direction = compte.role === 'direction'` : la **direction seule** modifie ; les achats **lisent** (confirmé côté serveur : toutes les écritures `/qualites…` sont `DIRECTION`, `referentiels.py:846-1046`). Alimentation : pas d'accès (et le serveur lui retire prix et coûts de `/qualites` et `/nomenclature`).
- **Paramètres d'adresse** : `onglet` = `nomenclature` (sinon onglet Qualités, paramètre absent) ; `qualite` = id de la qualité ouverte (écrit en `replace`) ; changer d'onglet remplace l'adresse par `{}` ou `{onglet}` et ferme donc la qualité ouverte.
- **Données** : `GET /qualites` (acteur ; par qualité : `base_mensuelle`, `poids` par rôle, `saisonnalite` [12], `recette` (lignes du moteur : id, article_id, référence, rôle, nature, désignation, fournisseur, pourcentage, kg_m2, ml_m2, densité, prix_kg, prix, unite_prix, devise, cout_m2_mad), `controle` {roles_utilises, roles_conformes, ecarts[{role, somme}], conforme}, `cout_m2_mad`, `kg_m2`, `fabrications` (nb d'ordres), `empreinte`) ; `GET /classification` (rôles) ; `GET /articles` ; `GET /qualites/facteurs-cout` (ACHATS : `perte` = 1 + taux de perte, ou 1 en mode classeur ; `taux` par devise) ; `GET /nomenclature` (acteur).
- **Chargement** : « Un instant — chargement : les qualités… » ; erreur : page « Qualités et recettes » avec bandeau d'erreur.
- **En-tête** : titre « Qualités et recettes » ; sous-titre direction : « Chaque qualité : son poids au m², la recette de ses fils, ce qu’elle coûte. Le plan se saisit dans la page Production. » ; achats : « Chaque qualité : son poids au m², la recette de ses fils, ce qu’elle coûte. Lecture seule : la direction les modifie. » Actions : « Exporter en Excel » (infobulle « Les qualités et leurs recettes, fil par fil, dans un classeur Excel », `GET /api/export/qualites` ACHATS → `qualites-AAAA-MM-JJ.xlsx`, colonnes Qualité, Nom, Fabriquée, Rôle, Référence, Fournisseur, Part du rôle (%), kg / m², Prix d'achat, Unité du prix (« USD / kg »), Coût / m² (MAD), Coût de la qualité / m² (MAD)) ; « Nouvelle qualité » (direction).
- **Indicateurs** (`:140-158`) :
  | Indicateur | Valeur affichée | Formule / détail | Clic |
  |---|---|---|---|
  | Qualités fabriquées | nb de qualités actives | détail « N arrêtée(s) » | — |
  | Recettes incomplètes | nb de qualités **actives** dont `controle.conforme === false` | détail = codes fautifs joints par « , » ou « chaque rôle fait 100 % » ; ton critique si > 0, ok sinon | — |
  | Plan mensuel | « 12 345 m² » = Σ base mensuelle des actives | détail « avant saisonnalité · le saisir » (lien → `/production?onglet=plan&volet=plan`) | lien dans le détail |
  | Coût matière moyen | « 54,21 MAD/m² » = Σ(coût/m² × base) / Σ base (actives) | « pondéré par le plan » | — |
- **Onglets** : « Qualités (N) » (toutes), « Nomenclature (N lignes) ».

##### 2.1 Onglet « Qualités »
- Carte « Les qualités » ; à droite (dans l'en-tête de carte) : « N qualité(s) », case « avec les arrêtées » (défaut décochée), recherche placeholder « Code, nom, fil de la recette… » (sur code, nom, références de la recette ; à la frappe).
- **Tableau** (`Cadre court`) :
  | Colonne | Contenu | Format |
  |---|---|---|
  | Qualité | code gras + badge « arrêtée » ; dessous le nom | |
  | une colonne **par rôle utilisé** (rôles où au moins une qualité a un poids > 0, dans l'ordre des rôles) : libellé = code du rôle, dessous « kg/m² » ou « ml/m² » ; infobulle « Poil en kg/m² » | poids au m² du rôle ou « — » | droite, 4 décimales |
  | Poids recette + « kg/m² » (infobulle « Ce que pèsent les fils de la recette pour un m² ») | Σ kg/m² des lignes | droite, 4 déc. |
  | Coût + « MAD/m² » | coût matière au m² | droite, 2 déc. |
  | Plan + « m²/mois » | base mensuelle | droite, entier |
  | Recette | badge **critique** « Poil 98,0 % · Ruban 0,0 % » (rôles en écart) ; sinon badge **ok** « juste · N fil(s) » ; sans ligne : badge **attention** « aucun fil » | |
  Tri : code (serveur). Ligne cliquable → `?qualite=ID` ; arrêtée → `ligne-eteinte`. Vide : « Aucune qualité ne correspond. » / « Aucune qualité pour le moment. »

##### 2.2 Onglet « Nomenclature » — `/qualites?onglet=nomenclature`
- Carte « Nomenclature : chaque fil de chaque qualité » ; à droite note (infobulle « Coût au m² = kg/m² × prix au kilo × cours de la devise, perte matière comprise. Cliquer sur une ligne ouvre sa qualité. ») « N ligne(s) · recettes à corriger : A, B » ou « · toutes les recettes sont justes » (toutes qualités, arrêtées comprises) ; recherche « Qualité, fil, rôle, fournisseur… » (qualité, référence, rôle, nature, désignation, fournisseur).
- Chargement « Un instant — chargement : la nomenclature… » ; erreur : bandeau.
- **Tableau** : Qualité (gras ; dessous en rouge « recette à corriger ») · Rôle (ou note « matière inconnue ») · Référence (dessous « nature · désignation ») · Fournisseur · Part (%) (2 déc.) · kg / m² (4 déc. ; dessous « 0,1234 ml / m² » pour un rôle au mètre) · Prix d'achat (« 12,50 USD / kg », 4 déc. sous 0,1 ; « — » si absent ; infobulle pour un prix au mètre « soit 4,10 USD / kg par la densité ») · Coût (MAD/m²) (2 déc.). Ordre du moteur (pas de tri). Ligne cliquable → ouvre la qualité (`?qualite=ID` en gardant `onglet=nomenclature`). Vide : « Rien ne correspond. » / « Aucune recette saisie. »

##### 2.3 Fenêtre « Nouvelle qualité » (direction)
- `Dialogue large`, titre « Nouvelle qualité », `sale` si code, nom ou un poids saisi.
- Champs : « Code » (aide « tel qu'il figure sur les ordres de fabrication », focus ; obligatoire ; serveur 1-32, unique) ; « Nom » (duo, ≤ 120) ; intertitre « Poids d'un m² de tapis, rôle par rôle (laisser à zéro les rôles qui n'entrent pas) » ; `ChampsPoids` : un champ par rôle (libellé = code ; aide « mètres linéaires par m² de tapis » ou « kilos par m² de tapis » ; unité « ml/m² » / « kg/m² »). Note : « Une fois créée, la qualité s'ouvre sur sa recette. Son plan se saisit ensuite dans la page Production. »
- Gestes : « Annuler » / « Abandonner » (selon saisie ; sans confirmation) ; « Créer la qualité » (« Création… » ; grisé si code vide ou envoi) → `POST /qualites {code, nom, actif:true, poids}` → ouvre la qualité créée. Refus : « La qualité « X » existe déjà. » (409) ; « Rôle inconnu : « X ». » ; « Un poids au m² ne peut pas être négatif. » Journal « création qualité ».

##### 2.4 Fenêtre « Qualité X — nom » (détail) — `/qualites?qualite=ID`
- **Fichiers** : `components/referentiels/QualiteDetail.tsx`.
- **Rôles** : `modifiable` = direction. Achats : bandeau info « Lecture seule : seule la direction modifie les qualités et les recettes. », champs grisés, pas de bouton Retirer ni d'ajout, **pas de pied du tout** (fermeture par × ou Échap seulement).
- `Dialogue tresLarge`, titre « Qualité CODE — nom » + badge « arrêtée ». `sale` = direction et (fiche ou parts modifiées). Toute la saisie (fiche + recette) est tenue au-dessus des volets : changer de volet ne perd rien ; **un seul « Enregistrer »** écrit la fiche puis la recette.
- **Données supplémentaires** : `GET /qualites/{id}/versions` (acteur, `suivi.py:479`).
- **Indicateurs** (recalculés à la frappe) :
  | Indicateur | Valeur | Détail / formule | Ton |
  |---|---|---|---|
  | Coût matière | « 54,21 MAD/m² » = Σ coût/m² des lignes | « selon la saisie, perte matière comprise » si modifié, sinon « perte matière comprise » | — |
  | Poids de la recette | « 1,2345 kg/m² » = Σ kg/m² | « ce que pèsent les fils d'un m² » | — |
  | Recette | « N rôle(s) faux » / « N rôle(s) sans fil » / « Juste » | « N fil(s) · M rôle(s) » | critique / attention / ok |
  | Plan | « 1 200 m²/mois » (base mensuelle) | « coût d'un mois : 65 052 MAD » (= coût × base) | — |
- **Formules à la frappe** (`:144-168`) : rôle au mètre : ml/m² = part/100 × poids du rôle (ml/m²) ; kg/m² = ml/m² × densité de la matière ; rôle au kilo : kg/m² = part/100 × poids du rôle ; coût/m² = kg/m² × prix au kilo (prix au mètre ÷ densité, 0 sans densité) × cours de la devise (1 si inconnu) × perte ; rôle « juste » si |Σ parts − 100| ≤ 0,01 ; rôles affichés = rôles avec poids > 0 ou au moins une ligne ; **fautif** = rôle avec au moins une part > 0 et total ≠ 100 ; **sans fil** = rôle avec poids > 0 sans aucune part > 0 ; **bloquant** = sans fil, seulement si la qualité est active.
- **Volets** : « Recette (N lignes) », « Fiche et poids au m² » (« … • » si modifiée), « Plan de production », « Versions (N) ».

###### Volet « Recette »
- Note : « Dans chaque rôle utilisé, les parts des fils totalisent 100 %. Le total, les kilos et le coût se mettent à jour à la frappe ; en rouge, le rôle n'y est pas encore. »
- Lignes visant une matière disparue : bandeau erreur « N ligne(s) de la recette visent une matière disparue du catalogue (REF1, REF2) : elles seront retirées à l'enregistrement. » (et la recette compte alors comme modifiée).
- **Tableau de saisie** (`table.saisie`, `Cadre dialogue`) groupé par rôle :
  | Colonne | Ligne de rôle (`ref-groupe`, fond rouge si faux) | Ligne de fil |
  |---|---|---|
  | Fil | « Poil · 0,8000 kg/m² » (colspan 2 avec Fournisseur) | référence ; dessous « nature · désignation » |
  | Fournisseur | | fournisseur ou « — » |
  | Part du rôle (%) | total « 100,00 % » vert (`bon`) / rouge (`faux`) | champ nombre (pas libre) |
  | ml / m² (infobulle « Cuir, franges, ruban : les mètres par m² saisis (poids du rôle × part) ») | Σ pour un rôle au mètre | 4 déc. ou « — » |
  | kg / m² (infobulle « Les kilos par m² : saisis, ou les mètres × la densité de la matière ») | Σ | 4 déc. ; infobulle « 0,1200 ml/m² × 0,0500 kg/ml » ; note « densité manquante » si rôle au mètre sans densité |
  | Prix d'achat (infobulle « Le prix comme on l'achète : au kilo, ou au mètre — ramené au kilo pour le coût ») | | « 12,50 USD / kg » (4 déc. sous 0,1) ; dessous « 4,10 / kg » si au mètre |
  | Coût / m² | « 12,34 MAD » | « 1,23 MAD » |
  | Sert aussi à | état du rôle : « le rôle est complet » / « aucun fil : en ajouter un ci-dessous » / « 2,00 % de trop » / « il manque 2,00 % » | codes des autres qualités qui utilisent la matière, ou « — » |
  | (direction) | | bouton danger « Retirer » (infobulle « Retirer ce fil de la recette ») — sans confirmation |
  Pied de tableau (si au moins une ligne) : « Toute la recette » · Σ kg/m² (gras) · Σ coût « X MAD » (gras). Vide (aucun rôle) : « Aucun rôle n'a de poids : renseigner d'abord les poids au m² (onglet Fiche et poids au m²). »
- **Ajout (direction, s'il y a des rôles affichés)** : « Ajouter un fil (il rejoint son rôle) : » + `ChoixRecherche` placeholder « Taper quelques mots : référence, couleur, rôle, fournisseur… » ; options = matières **actives** dont le rôle est affiché et pas déjà dans la recette ; libellé « REF — désignation · rôle · fournisseur », détail « rôle · 12,50 USD / kg ». La nouvelle ligne prend d'office le reste du rôle (100 − total, ≥ 0, arrondi 2 déc.).
- Bandeau erreur si rôles sans fil : « Rôle(s) avec un poids au m² mais sans matière : Ruban. Leurs kilos manqueraient aux besoins, au coût et à la sortie vers les machines : y mettre leurs matières, ou ramener leur poids à 0 dans la fiche, avant d'enregistrer. »

###### Volet « Fiche et poids au m² »
- « Code » (aide « tel qu'il figure sur les ordres de fabrication » ; obligatoire), « Nom » (duo), case « qualité fabriquée (active) » (décocher = arrêter la qualité).
- Intertitre « Poids d'un m² de tapis, rôle par rôle » ; note « Un rôle à zéro n'entre pas dans la qualité. Pour le cuir, les franges et le ruban, on compte des mètres linéaires : le poids se déduit de la densité de chaque matière. Une qualité arrêtée ne compte plus dans le plan. » ; `ChampsPoids` (tous les rôles, grille `ref-poids`).

###### Volet « Plan de production » (lecture)
- Bandeau info « Le plan de production (base mensuelle et saisonnalité) se saisit dans la page Production, toutes qualités ensemble. » + lien « **Ouvrir le plan de production** » → `/production?onglet=plan&volet=plan`.
- « Base mensuelle » : « **1 200 m²** par mois ordinaire (coefficient 1) » ; « Sur l'année » : « **14 400 m²** » (= Σ coefficient × base) + « — qualité arrêtée : elle ne compte pas dans les besoins » si arrêtée.
- Grille 12 mois (`ref-saisons`) : « janv. … déc. » puis m² prévus = coefficient × base (infobulle « coefficient 1,20 »).
- Note « m² prévus chaque mois (base × coefficient de saisonnalité). La croissance annuelle réglée s'y ajoute pour les mois à venir. »

###### Volet « Versions » (historique de la recette)
- Une version naît **automatiquement** à chaque validation qui touche les lignes de recette ou les poids au m² d'une qualité (écran, restauration, tout autre chemin) : photo des lignes (référence, rôle, part) **et** des poids au m², signée de l'auteur du journal (`suivi.py:440-476`). Il n'y a **pas de date d'effet saisie** : la version vaut à partir de son horodatage (« Enregistrée le »).
- Chargement « Lecture des versions… » ; aucune : info « Aucune version enregistrée : la recette n'a pas été modifiée depuis la mise en service du suivi des versions. »
- À gauche, tableau : Enregistrée le (horodatage ; « en vigueur » sous la première) · Par (ou « reprise ERP Fil » pour la plus ancienne sans auteur, sinon « — ») · Fils (nb de lignes, droite). Lignes cliquables ; la choisie est surlignée (`ligne-modifiee`). Choix par défaut : la **deuxième** (la précédente), sinon la seule.
- À droite : « Version du JJ/MM/AA HH:MM par X, comparée à la recette en vigueur : N différence(s). » (ou « identique. ») ; « Poids au m² : Poil 0,800 (en vigueur : 0,750) · Trame 0,300 » ou « non gardés avec cette version (les plus anciennes ne retenaient que les parts). »
- Tableau comparatif : Rôle · Référence · Part dans cette version · Part en vigueur · Écart (badge accent « ajouté depuis », badge attention « retiré depuis », « +2,00 pt », ou « — ») ; lignes changées surlignées ; tri rôle puis référence.
- **Revenir à cette version** (direction, sans saisie en cours, version ≠ en vigueur, avec différences) : champ « Pourquoi revenir à cette version ? (obligatoire) » (≤ 300) + Confirmer danger « Revenir à cette version » ; grisé sans motif (infobulle « Écrire d'abord le motif ») ; infobulle sinon « La recette reprend les parts et les poids au m² de cette version ; une nouvelle version est signée » ou « La recette reprend les parts de cette version, avec les poids au m² de la version suivante qui les a gardés ; une nouvelle version est signée » ; question « Remplacer la recette en vigueur par cette version ? » / « Oui, revenir à cette version » → contrôle écran des matières disparues (« Ces matières n'existent plus au catalogue : X, Y. La version ne peut pas revenir telle quelle. ») puis `POST /qualites/{id}/versions/{vid}/restaurer?empreinte=…&motif=…` (DIRECTION) → « Recette revenue à cette version, parts et poids au m² : une nouvelle version, signée et motivée, est enregistrée. » Achats / saisie en cours : note « Pour revenir à cette version : la direction, sans autre modification en cours dans la fenêtre. »
  Serveur : poids de la version (ou de la suivante qui les a, à défaut ceux d'aujourd'hui ; un rôle ajouté depuis revient à 0), recette revérifiée (100 %, rôles oubliés) ; refus « Qualité introuvable. », « Version introuvable. » (404), « Ces matières n'existent plus au catalogue : … » (409), conflit d'empreinte ; journal « recette » « CODE : retour à la version du JJ/MM/AAAA HH:MM — motif ».

###### Bas de fenêtre (tous volets)
- Note « Contrôle enregistré : Poil 98,0 % · Ruban 0,0 %. » si le contrôle serveur a des écarts et que la recette n'est pas modifiée.
- Messages d'envoi ; conflit → bouton « Recharger la qualité » + « Elle a été modifiée sur un autre poste : la recharger avant de refaire la modification. » ; succès du rechargement « Qualité rechargée dans sa dernière version : refaire la modification. »
- **Pied (direction)** :
  | Geste | Conditions / infobulle | Confirmation | Appel | Succès | Refus |
  |---|---|---|---|---|---|
  | « Supprimer » | grisé si envoi ou `fabrications > 0` ; infobulle « Fabriquée par N ordre(s) : elle appartient à l'historique. La désactiver plutôt (fiche). » / « Supprimer une qualité qui n’a jamais été fabriquée » | Confirmer « Supprimer la qualité CODE, sa recette et son plan ? » / « Oui, supprimer » | `DELETE /qualites/ID` | ferme | « « CODE » a été fabriquée par N ordre(s) : elle appartient à l'historique. La désactiver plutôt que la supprimer. » (409) |
  | (état) | note rouge « À corriger avant d'enregistrer : Poil, Ruban. » ou « Non enregistré : la fiche et la recette. » ou « Aucune modification. » | | | | |
  | « Annuler les modifications » (si saisie) / « Fermer » | remet fiche et lignes à l'enregistré (sans confirmation) | | | | |
  | « Enregistrer » (« Enregistrement… ») | grisé si envoi, rôle faux, rôle bloquant, code vide, ou rien modifié | — | fiche modifiée → `PUT /qualites/ID {code, nom, actif, poids, empreinte}` ; puis recette modifiée → `PUT /qualites/ID/recette?empreinte=…` [{article_id, pourcentage}] | « Qualité enregistrée : les besoins, les coûts et le plan d’achat sont recalculés. » | « La qualité « X » existe déjà. » ; « Rôle inconnu » ; poids négatif ; « Matière inconnue dans la recette. » ; « « REF » figure deux fois dans la recette. » ; « Dans chaque rôle, la recette doit faire 100 % : Poil 98 %. » ; « La recette oublie le rôle Ruban (0.12 au m²) : y mettre ses matières, ou ramener son poids au m² à 0 dans la fiche. » (pluriel : « les rôles … : y mettre leurs matières, ou ramener leur poids au m² à 0 dans la fiche. ») ; conflit « Cette qualité a été modifié(e) entre-temps sur un autre poste : rechargez pour repartir de sa dernière version, puis refaites la modification. » (409) |
  Serveur `PUT /qualites/ID` : arrêter / remettre en service note une version du plan (« CODE : arrêtée » / « remise en service ») — l'arrêt retire le plan des mois à venir, pas du passé ; renvoie un `avertissement` « Rôle(s) avec un poids au m² mais sans matière dans la recette : … Les besoins et la sortie vers les machines ne les comptent pas tant que la recette ne les nomme pas. » (**non affiché** par l'écran). Tolérance recette serveur = 0,01 (même que C01). Relecture après écriture : qualités, versions, nomenclature, besoins, plan d'achat, cockpit, contrôles, plan de production, besoins de production, stock.

---

### Notions métier apparues

- **Matière** (article du catalogue) ; colonne **Référence** ; **désignation** (couleur telle que l'atelier la nomme + code couleur) ; référence **composée** à partir de la classification : composition + type de fil + titrage (valeur unité) + couleur + code couleur + **suffixe fournisseur** (Hs, Oz, Tat…).
- **Classification** : 4 listes (composition avec libellé / famille Synthétique-Naturel-Intrant / composition détaillée ; type de fil ; titrage = valeur + unité Dtex, Deniers, Nm, Tex, Nec ; couleur avec famille) ; valeur active / désactivée (désactivée : plus proposée pour une nouvelle matière, gardée par celles qui la portent) ; une valeur portée ne se supprime pas ; renommer un code renomme sur les matières (références déjà écrites inchangées) ; « Relire les références » comble les vides sans jamais écraser.
- **Rôle (de nomenclature)** dans le tapis : 8 rôles de base du calcul (Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique) qui gardent leur nom et ne se suppriment pas ; **Cuir, Franges, Ruban comptés au mètre** (ml/m²), les autres au kilo (kg/m²) ; ordre des rôles = ordre des listes et colonnes ; direction seule.
- **Stock toujours en kilos** (cuir, franges, ruban compris) ; **densité (kg / ml)** obligatoire pour un rôle au mètre ou un prix au mètre ; mètres affichés **à titre indicatif** (« ≈ 1 020 ml ») ; `kg_par_ml` = densité si rôle au mètre.
- **Unité du prix** : kg ou ml ; prix au kilo = prix ÷ densité si au mètre ; « le dernier prix confirmé d’une commande s’y inscrit ». Devise du prix ; **un bon de commande par devise**.
- **Unité d'achat** déclarée (Fût, Sac, Big-bag, Palette, Bobine, Carton, Rouleau + **contenance** en kg) ou **déduite** (palette = kg/bobine × bobines/palette, sinon bobine, sinon kilo) ; jamais « ml ». **Minimum de commande** (kg).
- **kg / bobine** (catalogue ; le poids pesé du lot sert aux sorties en bobines) ; **bobines par palette**.
- **Stock minimum** (kg ; sous ce seuil la matière est signalée — badge attention dans « En stock ») ; **couverture minimum** (mois de consommation d'avance, ≤ 60).
- **Groupe d'équivalence** (matières interchangeables) et **priorité** (la plus petite passe en premier).
- **Code douanier** : position du tarif + taux de droits ; droits attendus d'un dossier = taux × valeur en douane (achat + fret), comparés à la quittance (M53).
- **Historique d'une matière** (mouvements, lots, commandes, réceptions, ordres, opérations brouillons compris, dossiers, recettes, fils montés, pièces jointes) : on **désactive** au lieu de supprimer. Matière en service ⇒ fournisseur obligatoire (contrôle **C05**).
- **Version / empreinte** : modification refusée si la fiche a changé entre-temps sur un autre poste (« Recharger la fiche / la qualité »).
- **Fournisseur** : local (pays vide / MAROC / MOROCCO) ou étranger (importation) ; devise par défaut (pré-remplit une matière) vs devises pratiquées ; **délai** déclaré (commande → arrivée usine, règle le stock projeté) vs **délai mesuré** (commande → réception validée, 12 mois) ; **couverture** (jours de consommation par commande ; 0 = réglage général) ; mode, délai (crédit fournisseur) et conditions de paiement ; **incoterm** ; port de chargement ; banque ; **OTIF** (« Livraisons parfaites » : à l'heure, complètes, conformes ; sous-performant) ; **score / 100** et **classement** (Stratégique, Standard, ATTENTION, À challenger) avec action.
- **Qualité** (code des ordres de fabrication) : active (« fabriquée ») / **arrêtée** (ne compte plus dans le plan des mois à venir) ; **poids au m² par rôle** ; **recette** = parts (%) des matières dans chaque rôle, **100 % par rôle** (tolérance 0,01) ; rôle avec poids mais **sans matière** interdit ; **kg/m²**, **ml/m²** ; **coût matière / m²** = kg/m² × prix au kilo × cours × (1 + taux de perte) ; **coût matière moyen pondéré par le plan** ; « Sert aussi à » (autres qualités utilisant la matière) ; qualité fabriquée par des ordres = historique (on l'arrête).
- **Plan** : base mensuelle (m²/mois ordinaire), coefficients de saisonnalité (12 mois, 0-20), croissance annuelle ajoutée aux mois à venir ; saisi dans Production.
- **Versions de recette** : datées, signées, avec les poids au m² (les plus anciennes sans) ; « reprise ERP Fil » ; revenir à une version = nouvelle version motivée.
- **Nomenclature** : chaque fil de chaque qualité (rôle, part, kg/m², prix, coût) ; « matière inconnue » ; « recette à corriger ».
- **Pièces jointes** (matière : fiche technique, certificat, photo ; fournisseur : contrat, RIB, certificats, catalogue) ; 20 Mo ; retrait tracé, fichier gardé.
- **Journal des actions** : chaque écriture des référentiels y est tracée.

---

### Incohérences et anomalies repérées

1. **Vocabulaire « Fil » en en-tête de colonne** (interdit par REGLES-ECRAN §3) : `components/referentiels/QualiteDetail.tsx:334` (« Fil » dans la recette) ; aussi « Fils » `QualiteDetail.tsx:696`, titre « Nomenclature : chaque fil de chaque qualité » `pages/Qualites.tsx:347`, placeholder « Code, nom, fil de la recette… » `Qualites.tsx:179`.
2. **Unités de prix sans espaces** : `prixUnitaire` produit « 12,50 USD/kg » (`types.ts:327-329`, utilisé `CatalogueMatieres.tsx:301-302, 862`) alors que la règle écrit « USD / kg » et que Qualités/Nomenclature écrivent « USD / kg » (`Qualites.tsx:391`, `QualiteDetail.tsx:413`) : deux graphies.
3. **« Commentaire »** (classification, `CatalogueClassification.tsx:204, 337`) au lieu de **« Observations »** (§3, Remarques → Observations) — le fournisseur, lui, dit « Observations ».
4. **Suppression d'un fournisseur cliquable puis refusée** : l'écran ne grise que pour matières, commandes, réceptions, pièces jointes (`CatalogueFournisseurs.tsx:393-400, 673`), le serveur refuse aussi pour **lots, opérations, factures** (`referentiels.py:405-414`) → refus découvert au clic (§2 « ne pas laisser cliquer pour découvrir un refus »).
5. **Renommer un rôle** : l'écran propose le renommage si `articles == 0 && qualites == 0`, où `qualites` ne compte que les poids **> 0** (`referentiels.py:71-73`, écran `CatalogueClassification.tsx:454-459`) ; le serveur refuse dès qu'**une ligne de poids existe, même à 0** (`referentiels.py:146-149`) — or `ChampsPoids`/la fiche enregistrent des poids à 0 → « « X » est porté par des matières ou des qualités : il garde son nom. » au clic.
6. **Recette d'une qualité arrêtée** : l'écran ne bloque les rôles sans fil que si la qualité est active (`QualiteDetail.tsx:166`), mais `PUT /qualites/{id}/recette` refuse toujours un rôle oublié (`referentiels.py:973-981`) → enregistrer la recette d'une qualité arrêtée incomplète échoue au clic (et des lignes de matière disparue forcent `recetteModifiee`, `QualiteDetail.tsx:141`).
7. **Avertissement serveur ignoré** : `PUT /qualites/{id}` renvoie `avertissement` (rôles sans matière, `referentiels.py:895-899`) ; `QualiteDetail.tsx:195-204` ne l'affiche jamais.
8. **Enregistrement en deux temps non atomique** (`QualiteDetail.tsx:188-222`) : la fiche peut être écrite et la recette refusée ; le message d'erreur ne dit pas que la fiche, elle, est enregistrée.
9. **Import tableur — contrôles moins stricts que la fiche** (`gestion_mp/api/suivi.py:770-808` vs `referentiels.py:566-604`) : pas de contrôle « unité d'achat déclarée sans contenance », pas de bornes (nombres négatifs, couverture > 60…), « Densité »/« Prix » acceptés négatifs ; à l'inverse une matière nouvelle **désactivée** exige quand même un fournisseur (« une matière nouvelle a besoin de son fournisseur »).
10. **Import tableur — messages techniques** : noms de champs bruts (« densite n'est pas un nombre », « code_douanier inconnu… », « devise inconnu « X » (l'ajouter d'abord à la classification) » — faux pour une devise, un rôle ou un code douanier, et accord « inconnu » au masculin) (`suivi.py:777, 792`).
11. **Import tableur — libellés de champs** : `NOMS_CHAMPS` contient `unite` (« Unité », colonne abandonnée, code mort) mais pas `unite_prix` ni `code_douanier` → affichés en clair « unite_prix », « code_douanier » dans « Champs qui changent » (`TableurMatieres.tsx:22-44`). L'aperçu « champ par champ » annoncé (en-tête du fichier `:1-4`) ne montre que les noms, pas les valeurs avant/après pourtant renvoyées (`suivi.py:816-818`).
12. **Import tableur — on ne peut pas vider un champ** (case vide ignorée, `suivi.py:772-773`) sans que l'écran le dise ; la priorité dans le groupe n'est pas importable.
13. **Accord « inconnue »** : « Type de fil inconnue », « Titrage inconnue » (`referentiels.py:578`, libellés masculins + « inconnue »).
14. **Message « Cette qualité a été modifié(e) »** / « Ce fournisseur a été modifié(e) » : accord générique « (e) » (`referentiels.py:57`).
15. **Codes douaniers : renvoi vers un écran inaccessible aux achats** : « Code douanier inconnu : « X ». L'ajouter d'abord (Réglages › Codes douaniers). » (`referentiels.py:603-604`) — l'onglet est réservé à la direction (`Reglages.tsx:86`) et l'écriture aussi (`referentiels_import.py:236-278`).
16. **Codes douaniers : format non contrôlé à l'écran** (`ReglagesCodesDouaniers.tsx:119-130, 164`) → refus pydantic au clic avec préfixe technique « Value error, … » (`referentiels_import.py:226-233`). Bouton « Annuler » au lieu de « Fermer » / « Abandonner les modifications » (`:160`). Pas de filtre actifs/désactivés.
17. **Doublon de hook** : `useCodesDouaniers` existe dans `components/referentiels/types.ts:125-131` (type sans `matieres`, `staleTime` 300 s, `retry:false`) et dans `components/importations/importations.ts:275-280` (60 s) sur la **même clé** `['codes-douaniers']`.
18. **Branches lecture seule mortes** : `peut('achats')` est toujours vrai sur `/catalogue` (garde `['achats']` laisse passer direction et achats seulement) → `modifiable=false`, `lectureSeule`, lignes non cliquables de la classification jamais atteintes (`CatalogueMatieres.tsx:196, 530`, `CatalogueClassification.tsx:115, 131`, `CatalogueFournisseurs.tsx:125, 167, 335`).
19. **Longueurs incohérentes** : un code de classification accepte 64 caractères (`referentiels.py:185`) mais une matière n'en accepte que 32 pour composition / type de fil et 48 pour le titrage (`referentiels.py:432-434`) → valeur créable mais inutilisable (message pydantic anglais). Le code proposé est mis en MAJUSCULES par `ChoixClasse` (`ChoixClasse.tsx:72`) mais pas par la fenêtre « Ajouter une composition » (`CatalogueClassification.tsx:374`).
20. **Unité d'achat « ml »** tapable à l'écran (champ libre, `CatalogueMatieres.tsx:911-918`) puis refusée par le serveur (`referentiels.py:594-596`) ; idem bornes (couverture > 60 mois, priorité > 100, densité > 1000, kg/bobine > 1000) non contrôlées à l'écran → refus pydantic en anglais.
21. **Désactiver une matière revalide toute la fiche** (`CatalogueMatieres.tsx:1073` → `PUT` complet) : une ancienne matière incomplète (p. ex. sans densité) ne peut pas être désactivée sans être d'abord complétée.
22. **Fermer sans confirmation** : les boutons « Abandonner les modifications » (fiche matière `:1107`, fiche fournisseur `:682`, valeur de classification `:366`), « Abandonner » (nouvelle qualité `Qualites.tsx:323`) et « Annuler les modifications » (qualité `QualiteDetail.tsx:607-615`) ferment / annulent sans la question « Les abandonner ? » que posent ×, Échap et le fond.
23. **Gestes sans infobulle** (§2 « le geste dit ce qu'il fait dans une infobulle ») : « Réactiver » fournisseur (`CatalogueFournisseurs.tsx:665`), « Supprimer » d'une valeur non portée dans la fenêtre d'édition (`CatalogueClassification.tsx:359`), « Retirer » un fil sans confirmation (`QualiteDetail.tsx:422-428`, réversible tant qu'on n'enregistre pas), « Désactiver/Réactiver » une valeur sans confirmation (`CatalogueClassification.tsx:231-237`).
24. **Indicateur « Délai » en ton attention sans raison affichée** (`CatalogueFournisseurs.tsx:436-440`) : la règle (mesuré > 120 % du déclaré, ≥ 3 livraisons) n'est dite nulle part.
25. **OTIF et score rapprochés par le nom** du fournisseur (`CatalogueFournisseurs.tsx:135, 231, 292`) et non par l'id : un renommage ou deux noms proches cassent le lien.
26. **Recherche et filtres hors de la rangée `.filtres` sous le titre** dans l'onglet Qualités et la Nomenclature (placés dans `extra` de la carte, `Qualites.tsx:172-181, 348-355`) — écart à §2 « placée dans la rangée .filtres sous le titre ».
27. **Compteurs incohérents** : onglet « Classification » = toutes les valeurs (désactivées comprises, `Catalogue.tsx:58`) alors que la Bascule compte les **actives** (`CatalogueClassification.tsx:103`) ; « Recettes incomplètes » ne compte que les qualités actives (`Qualites.tsx:112`) quand la Nomenclature liste « recettes à corriger » toutes qualités (`Qualites.tsx:343`).
28. **`?fournisseur_filtre=` reste dans l'adresse** après « Effacer les filtres » (`CatalogueMatieres.tsx:246-255`) : un rechargement remet le filtre.
29. **Changer d'onglet sur Qualités ferme la qualité ouverte** (`Qualites.tsx:166` remplace l'adresse) alors que cliquer une ligne de Nomenclature ouvre la qualité en gardant l'onglet.
30. **Achats en lecture seule sur une qualité : aucun bouton « Fermer »** (pied absent si `!modifiable`, `QualiteDetail.tsx:581`).
31. **« Effacer les filtres » des matières n'efface pas l'état** (Actives / Désactivées) alors que celui des fournisseurs le remet (`CatalogueMatieres.tsx:248-251` vs `CatalogueFournisseurs.tsx:198-203`).
32. **« Dates d'effet » de recette** : il n'en existe pas à l'écran ; une version vaut à son horodatage d'enregistrement (rien ne permet de dater une recette dans le futur ou le passé).
33. **`PUT /qualites/{qid}/plan`** (`referentiels.py:1034`) n'est pas appelé par ces écrans (le plan est lecture seule ici) ; il l'est par `components/production/VoletPlan.tsx:102` — pas du code mort, mais à savoir.

---

### Comptes

- **Écrans / pages** : 3 — Catalogue (`/catalogue`), Qualités et recettes (`/qualites`), Réglages › Codes douaniers (`/reglages?onglet=codes`, onglet d'une autre page).
- **Onglets / sous-vues** : 23 — Catalogue : 3 onglets (Matières, Classification, Fournisseurs) ; Bascule Classification : 5 (Compositions, Types de fil, Titrages, Couleurs, Rôles) ; fiche matière : 4 volets ; fiche fournisseur : 2 volets ; Tableur : 3 volets ; Qualités : 2 onglets (Qualités, Nomenclature) ; détail qualité : 4 volets (Recette, Fiche et poids au m², Plan de production, Versions).
- **Fenêtres / tiroirs** : 8 fenêtres — Fiche matière, Le catalogue par tableur, Ajouter/modifier une valeur de classification, Classer le catalogue d'après les références, Fiche fournisseur, Code douanier, Nouvelle qualité, Détail d'une qualité — plus 1 panneau d'ajout en ligne (ChoixClasse « Ajouter … à la classification »). Aucun document imprimable ; 4 exports Excel (matières, fiches fournisseurs, qualités, modèle d'import).
- **Gestes inventoriés** : 71 — Matières 5 ; fiche matière 13 (+ ChoixClasse 4 : choisir, « + Ajouter « X » », « × », « Annuler » / « Ajouter « X » ») ; pièces jointes 3 (joindre, ouvrir, retirer) ; tableur 4 ; classification valeurs 6 ; rôles 5 ; classer le catalogue 3 ; fournisseurs 4 ; fiche fournisseur 9 ; codes douaniers 5 ; qualités page 4 ; nouvelle qualité 2 ; détail qualité 9 (ajouter un fil, retirer, enregistrer, annuler les modifications/fermer, supprimer, recharger, ouvrir le plan, choisir une version, revenir à cette version).

---

## Partie 8 — Analyse, Réglages, Bilan du mois

Inventaire en lecture seule de `/Users/mohamed/gestion-mp`. Références `fichier:ligne` relatives à
`ecran/src` pour l'écran, au dépôt (`gestion_mp/…`) pour le serveur.

Rappels communs utiles à la reconstruction (lus dans `components/ui.tsx`, `lib/format.ts`, `lib/api.ts`,
`gestion_mp/securite.py`) :

- **Droits serveur** (`gestion_mp/securite.py:104-122`) : `ACHATS` = achats + direction ; `DIRECTION` =
  direction seule ; `acteur` = tout compte connecté ; la direction passe partout. Refus 403, texte exact :
  « Cette action est réservée à : responsable achats. » (dépendance ACHATS) ou « Cette action est réservée
  à : la direction. » (dépendance DIRECTION). Sans session : 401 « Connectez-vous pour continuer. » ; compte
  désactivé : 401 « Ce compte n'est plus actif. ».
- **Refus de saisie** (`gestion_mp/main.py:177-187`) : les erreurs de validation pydantic sont traduites
  (« should have at least » → « trop court : au moins »…) et préfixées du champ : « champ : texte ».
- **Garde de route écran** (`App.tsx:200-201`) : un rôle non permis est renvoyé à son accueil, avec le
  bandeau « L'écran demandé ({chemin}) est réservé à un autre rôle : vous êtes revenu à votre accueil. »
- **Erreur réseau** (`lib/api.ts:33`) : « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). » ;
  réponse sans JSON : « Erreur {code} ».
- **`qs()`** (`lib/api.ts:68`) saute les valeurs vides, nulles **et `false`**.
- **Chargement** (`ui.tsx:209`) : « Un instant — chargement : {quoi}… ».
- **Formats** : `montant` = entier + « MAD » ; `montantCourt` = « 17,4 M MAD » au-delà du million (montant
  exact en infobulle) ; `part(x)` = x × 100 avec « % » (1 décimale par défaut) ; `prixUnite` = 2 décimales,
  jusqu'à 4 sous 0,1 ; `signe()` = « +4,2 % » ; `jours()` = « 60 j » ; `horodatage` = date + heure courtes ;
  `moisLisible('2026-09')` = « sept. 2026 ».
- **Confirmer** (`ui.tsx:342`) : le bouton devient « {question} · Non · {oui} » sur place.
- **Dialogue** (`ui.tsx:270`) : Échap / fond / × ; avec `sale`, bandeau « Des modifications ne sont pas
  enregistrées. Les abandonner ? » + « Non, continuer la saisie » / « Oui, abandonner ».
- **LigneVide** (`components/direction/commun.tsx:45`) : une ligne `td.vide` sur toutes les colonnes.

---

### 1. ANALYSE — `/analyse` (`?onglet=` lu et écrit ; `?fournisseur=` lu)

#### 1.0 Cadre de la page

- **Fichiers** : `pages/Analyse.tsx` (152 l.), composants `components/direction/Analyse*.tsx`,
  `ComparaisonPrix.tsx`, `components/importations/AnalyseRevient.tsx`, `components/direction/commun.tsx`,
  `direction.css`.
- **Rôles** :
  - Menu « Pilotage › Analyse », infobulle « Prix, fournisseurs, valorisation, contrôles »
    (`App.tsx:86`) : rôles `['achats']` → **direction + achats**. Alimentation : absent du menu, la route
    `garde(['achats'])` (`App.tsx:261`) la renvoie à son accueil avec le bandeau ci-dessus.
  - Aucun onglet n'est filtré par rôle dans l'écran : achats et direction voient les **neuf** onglets.
  - Onglet par défaut selon le rôle (`Analyse.tsx:95`) : direction → `valorisation` ; achats → `matrice`
    (« Les achats viennent d'abord chercher les prix ; la direction, la valeur du stock »).
  - Serveur : toutes les routes lues sont `ACHATS` (sauf `/ordres-fabrication`, `acteur` seul).
- **Adresse** : `?onglet=` (valorisation, matrice, historique, opportunites, fournisseurs, revient,
  echeancier, controles, production). Alias historique : `?onglet=prix` → `matrice` (`Analyse.tsx:87`).
  Valeur inconnue → onglet par défaut du rôle. Choisir l'onglet par défaut **efface** le paramètre
  (adresse nue), sinon écrit `?onglet=cle` en `replace` (`Analyse.tsx:97`). `?fournisseur=` est lu et passé
  à l'onglet Fournisseurs comme recherche initiale (`Analyse.tsx:145`).
- **Pastille du menu** (`App.tsx:218-224`) : si `/cockpit` (lu toutes les 180 s pour direction et achats)
  rapporte `controles.anomalies > 0`, le lien Analyse mène à `/analyse?onglet=controles` et porte une
  pastille avec ce nombre.
- **En-tête** : titre « Analyse » ; sous-titre = phrase de l'onglet actif, suivie de la note
  « · Réceptions : bobines · pesées » où « bobines » → `/receptions?onglet=bobines` (infobulle « Le poids
  moyen des bobines, fil par fil, au fil des réceptions ») et « pesées » → `/receptions?onglet=pesees`
  (infobulle « Chaque pesée face au bon de livraison ») (`Analyse.tsx:115-128`).
- **Onglets** (un seul niveau, `Analyse.tsx:36-84`) — libellé court affiché quand il existe, libellé long en
  infobulle (« Neuf onglets sur une ligne à 1366 px ») :

| Clé | Libellé affiché | Infobulle | Compteur | Sous-titre de page (exact) |
|---|---|---|---|---|
| valorisation | « Valeur » | « Valorisation » | — | « La matière détenue au coût moyen pondéré des achats (à défaut, au prix catalogue). » |
| matrice | « Matrice » | — | nb de lignes de `/prix/matrice` | « Prix par mois, en devise de facture ; s'alimente seul à chaque réception validée. » |
| historique | « Prix payés » | — | nb de lignes de `/prix/historique` | « Chaque prix payé face au précédent ; s'alimente seul à chaque réception validée. » |
| opportunites | « Opportunités » | « Opportunités d'économies » | nb de lignes de `/opportunites?meme_couleur=true&autre_fournisseur=true` | « Fils comparables moins chers ailleurs, à la même époque, au coût rendu usine. » |
| fournisseurs | « Fournisseurs » | — | — | « Livraisons à l'heure, complètes, conformes : score et classement. » |
| revient | « Coût de revient » | — | — | « Ce que chaque fil a coûté rendu usine, frais d'importation répartis. » |
| echeancier | « Échéancier » | — | — | « Ce qu'il faudra payer, et quand : factures des fournisseurs et frais d'importation. » |
| controles | « Contrôles » | — | `synthese.anomalies` (nombre de **contrôles** en anomalie, pas de lignes) | « La cohérence des données ; chaque contrôle dit quoi faire. » |
| production | « Production » | — | — | « Ce que chaque ordre a sorti, face au prévu par la recette. » |

- **Données chargées par la page elle-même** (pour les compteurs, quel que soit l'onglet) : `GET /prix/matrice`,
  `GET /prix/historique`, `GET /opportunites?meme_couleur=true&autre_fournisseur=true`, `GET /controles`
  (`Analyse.tsx:101-110`).

---

#### 1.1 Onglet Valorisation — `/analyse` (défaut direction) ou `?onglet=valorisation`

- **Fichier** : `components/direction/AnalyseValorisation.tsx` (225 l.).
- **Rôles** : direction, achats (`GET /valorisation` ACHATS, `pilotage.py:256`).
- **Données** : `GET /valorisation?date_reference=AAAA-MM-JJ` (absent = aujourd'hui) ; résultat précédent
  gardé pendant le rechargement. Serveur : date hors 2000–2100 → 400 « date de référence hors période :
  {date} » (`pilotage.py:28-36`). Journal rejoué jusqu'au soir de la date.
- **Calcul serveur** (`moteur.py:2009-2047`) : pour chaque matière du catalogue : `stock = magasins
  (stock_net, quarantaine comprise) + machine (fil monté sur les métiers)` ; `valeur = CMUP × stock` ;
  `écart = valeur − stock × prix catalogue au kilo × cours du jour de sa devise`. CMUP = coût moyen pondéré
  des achats réels recalculé à chaque entrée, à défaut prix catalogue (au kilo, un prix au mètre ramené par
  la densité).
- **Indicateurs** :

| Indicateur | Valeur affichée | Détail / infobulle (exacts) | Teinte |
|---|---|---|---|
| « Valeur du stock détenu » | `montantCourt(total_mad)` | détail « {total_kg} kg » ; infobulle « {montant} au {date_reference} » | — |
| « Dans les magasins » | `montantCourt(total_magasin_mad)` | détail « {kg magasins} kg » ; infobulle montant exact | — |
| « Sur les métiers (info) » | `montantCourt(total_machine_mad)` | détail « {kg} kg montés, hors stock » ; infobulle « {montant} en machine : le fil monté sur les métiers, pas encore tissé, compris dans la valeur du stock » | — |
| « Matières en stock » | « {n avec stock} sur {n lignes} » | « avec stock ou fil monté » | — |
| « Écart avec le catalogue » | `montantCourt(ecart_mad)` | détail « coût payé − catalogue » ; infobulle « {montant} — positif : le stock a coûté plus que le prix du catalogue ne le dit (frais d'approche, hausse non reportée). » | `attention` si \|écart\| > 2 % de max(total, 1) |

  Aucun indicateur n'est cliquable.
- **Carte** : titre « Valeur par matière, la plus lourde d'abord — {n} matière(s), {montant total affiché} »
  (total = somme des lignes **filtrées**). Extra : lien-bouton « Exporter en Excel » →
  `/api/export/valorisation?date_reference=…`, infobulle « La valorisation au {date ou « jour »}, matière
  par matière, dans un classeur ».
- **Filtres** (rangée `.filtres`) :
  - « Au » (infobulle « La valeur au soir de ce jour : le journal rejoué jusque-là ») : liste
    « aujourd'hui » + les 12 dernières fins de mois « fin {mois année} ({jj/mm/aaaa}) » (du plus récent au
    plus ancien) + « autre date… ». « autre date… » pose la date du jour et fait apparaître un champ date
    (max = aujourd'hui).
  - Recherche à la frappe, placeholder « Référence, fournisseur, devise… plusieurs mots » (champs :
    référence, nature, fournisseur, devise ; plusieurs mots, sans accents).
  - Case « montrer aussi les matières sans stock » (défaut : décochée → seules |stock| > 1e-6).
  - « Effacer les filtres » dès qu'un filtre est posé (recherche, case ou date) : remet tout à vide.
- **Note** (si date passée) : « Au {date} au soir : le stock et le coût moyen rejoués sur le journal jusqu'à
  ce jour-là. Le fil monté sur les métiers n'y est pas compté — le montage n'a pas d'historique, seul celui
  d'aujourd'hui est connu. »
- **Tableau** (`Cadre taille="court"`, `table.serre`) — tri fixe par valeur décroissante, non cliquable,
  pas de pagination, pas de pied :

| Colonne | Contenu | Format | Remarque / infobulle d'en-tête |
|---|---|---|---|
| « Référence » | référence ; dessous, note = nature | texte | infobulle = référence |
| « Fournisseur » | fournisseur | texte | |
| « Magasins » | stock magasins « {n} kg » | num | « En kg, le cuir, les franges et le ruban compris » |
| « Sur les métiers (info) » | « {n} kg » ou « — » | num | « Stock en machine : le fil monté sur les métiers, pas encore tissé — compris dans le stock et sa valeur » |
| « Stock détenu » | **« {n} kg »** ; dessous « ≈ {m} ml » pour cuir/franges/ruban | num | |
| « Coût moyen (MAD) » | « {prixUnite} / kg » | num | « Coût moyen pondéré des achats réels, recalculé à chaque entrée ; à défaut d'achat, prix du catalogue — au kilo (un prix au mètre y est ramené par la densité) » |
| « Prix catalogue » | « {prixUnite} {devise} / kg » | num | |
| « Valeur (MAD) » | **entier** | num | |
| « Écart catalogue » | entier ou « — » si 0 | num | |

- **Vide** : « Aucune matière ne correspond à cette recherche. » (recherche posée) sinon « Aucun stock à
  valoriser. ». Chargement : « …la valorisation… ». Erreur : message serveur.
- **Gestes** :

| Geste | Où | Rôle | Conditions | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|---|---|
| « Exporter en Excel » | en-tête de carte | dir., achats | toujours | — | `GET /api/export/valorisation?date_reference=` (ACHATS) | fichier `valorisation-AAAA-MM-JJ.xlsx` | 403 droit |
| « Effacer les filtres » | rangée de filtres | idem | ≥ 1 filtre | — | — | — | — |

- **Notions** : coût moyen pondéré (CMUP), prix catalogue, écart catalogue (frais d'approche, hausse non
  reportée), stock magasins / sur les métiers (info), « Stock détenu », valorisation à une date (journal
  rejoué), mètres indicatifs.

---

#### 1.2 Onglet Matrice — `?onglet=matrice` (défaut achats)

- **Fichiers** : `components/direction/AnalysePrix.tsx` (vue `matrice`, l. 120-311),
  `ComparaisonPrix.tsx` (hooks).
- **Rôles** : direction, achats (`GET /prix/matrice`, `/prix/historique`, `/opportunites` : ACHATS).
- **Données** : `GET /prix/historique`, `GET /prix/matrice`, `GET /opportunites?meme_couleur=true&autre_fournisseur=true`.
  Matrice serveur (`pilotage.py:444-494`) : pour chaque référence et chaque mois (date du bon) :
  prix moyen **pondéré par les quantités** (moyenne simple si quantité nulle), en devise de facture, au kilo ;
  au plus les **36 derniers mois** vus ; seuils `stable = 0,005` et `forte = seuil_hausse_forte` (réglage,
  défaut 5 %).
- **Indicateurs** (communs aux onglets Matrice et Prix payés, `AnalysePrix.tsx:73-94`) :

| Indicateur | Valeur | Détail / infobulle | Teinte |
|---|---|---|---|
| « Achats enregistrés » | nb de prix payés | « {montantCourt total} au total · {n} mois d'historique » ; infobulle montant exact | — |
| « Hausses de prix » | nb d'évolutions > 0,5 % | « dont {n} forte(s), au-delà de {seuil forte, 0 déc.} » | `critique` si fortes, `attention` si hausses, sinon `ok` |
| « Baisses obtenues » | nb d'évolutions < −0,5 % | « face au prix précédent du même fil » | `ok` |
| « Opportunités d'économies » | `montantCourt(total_mad)` ou « … » | « par an · {n} opportunité(s), onglet « Opportunités » » ou « calcul en cours » ; infobulle « {montant} par an » | `attention` si > 0, sinon `ok` |

- **Légende** (`AnalysePrix.tsx:105-118`) : cinq étiquettes « Premier prix » (accent), « Stable » (neutre),
  « Baisse » (ok), « Légère hausse » (attention), « Forte hausse » (critique) ; note « prix moyen pondéré du
  mois · stable à ±0,5 % près · forte hausse au-delà de {5 %} ».
- **Règle de teinte d'une case** (`AnalysePrix.tsx:24-30`) : variation = (prix − dernier prix connu
  **avant** dans le temps) / dernier prix ; aucun précédent → Premier prix ; < −0,5 % → Baisse ; > forte →
  Forte hausse ; > 0,5 % → Légère hausse ; sinon Stable.
- **Carte** : titre « Matrice des prix — {n} fil(s) ». Extra (rangée de boutons, voir Gestes).
- **Filtres** : recherche à la frappe « Référence, fournisseur, couleur… plusieurs mots » (champs :
  référence, fournisseur, nature, composition, type de fil, couleur, titrage, devise) ; cinq listes
  **liées** (chacune ne propose que ce que les autres laissent) : « Toutes compositions », « Tous types de
  fil », « Tous titrages » (titrage + unité), « Toutes couleurs », « Tous fournisseurs » ; « Effacer les
  filtres » dès 1 filtre.
- **Tableau** (`table.matrice`, `Cadre court`) :

| Colonne | Contenu | Format | Remarque |
|---|---|---|---|
| « Référence » | case à cocher + référence ; note « composition · type · titrage · couleur » | | infobulle d'en-tête : « Prix moyen du mois, pondéré par les quantités, dans la devise de la facture ; le mois le plus récent à gauche » ; case grisée quand 8 fils déjà cochés (sans infobulle) |
| « Fournisseur » | fournisseur | | |
| « Prix en » | « {devise} / kg » | | infobulle « La monnaie de la facture ; le prix est au kilo, le cuir, les franges et le ruban compris » |
| (sans titre) | bouton « Courbe » | | |
| un par mois (« sept. 2026 »…) | étiquette colorée du prix (`prixUnite`), « · » si aucun achat | num | **mois le plus récent à gauche** ; infobulle de case « {Mouvement} : {+x,x %} ({avant} → {prix} {devise} / kg) » ou « {Mouvement} : {prix} {devise} / kg » |

  Lignes triées par référence (serveur), pas de tri cliquable, pas de pied, pas de ligne cliquable.
- **Vide** : « Aucun fil ne correspond à ces filtres. » ou, sans données, « La matrice se remplira à la
  première réception validée : une colonne par mois, jusqu'à trente-six mois. ». Chargement : « …les prix… ».
- **Gestes** :

| Geste | Rôle | Conditions / grisé (infobulle) | Effet |
|---|---|---|---|
| « Comparer les {n} fils affichés » (ou « Comparer les fils affichés ») | dir., achats | grisé si 0 ou > 8 fils affichés ; infobulle « Filtrer jusqu'à 8 fils au plus pour les comparer tous » (> 8) sinon « Tous les fils du tableau sur une même courbe » | ouvre la fenêtre §1.4 |
| « Comparer les {n} fils cochés » / « Cocher des fils à comparer » (principal) | idem | grisé sans case cochée ; infobulle « Cocher des fils dans le tableau, puis voir leurs prix sur une même courbe » | fenêtre §1.4 |
| « Tout décocher » | idem | visible si ≥ 1 coché | vide les cases |
| case à cocher de ligne | idem | 8 au plus (`MAX_FILS`) | |
| « Courbe » (ligne) | idem | infobulle « La courbe des prix de {réf} » | fenêtre §1.4 pour ce fil |
| « Exporter en Excel » | idem | infobulle « L'historique des achats et la matrice, dans un classeur » | `GET /api/export/prix` (ACHATS) → `prix-AAAA-MM-JJ.xlsx` |
| « Effacer les filtres » | idem | ≥ 1 filtre | |

---

#### 1.3 Onglet Prix payés — `?onglet=historique`

- **Fichier** : `AnalysePrix.tsx` (vue `historique`, l. 313-409). Mêmes indicateurs et légende que §1.2.
- **Données** : `GET /prix/historique` (`pilotage.py:380-401`, calcul `moteur.py:2969-3008`) : chaque prix
  payé (historique alimenté à la validation des réceptions), **précédent = dernier prix du même triplet
  (référence, fournisseur, devise)** ; évolution = (prix − précédent)/précédent ; `prix_mad` et
  `montant_mad = quantité × prix × cours` **au cours du jour** de la devise (pas celui de l'achat) ; liste
  du plus récent au plus ancien.
- **Carte** : titre « Historique des achats — {n} prix payé(s) » ; extra : note « le plus récent d'abord ·
  cliquer un achat montre la courbe de ce fil » + « Exporter en Excel » (`/api/export/prix`).
- **Filtres** : recherche « Référence, fournisseur, n° de bon… plusieurs mots » (référence, fournisseur,
  n° de bon, nature, désignation, devise) ; case « seulement les hausses » (évolution > 0,5 %) ;
  « Effacer les filtres » si l'un est posé.
- **Tableau** (`table.serre`) — ligne **cliquable** → fenêtre §1.4 sur ce fil :

| Colonne | Contenu | Format |
|---|---|---|
| « Date » | date du bon | |
| « Bon » | n° du bon ou « — » | |
| « Référence » | référence ; note « nature · désignation » | |
| « Fournisseur » | | |
| « Quantité (kg) » | « {n} kg » | num |
| « Prix payé » | « {prix} {devise} / kg » | num |
| « Prix précédent » | « {prix} {devise} » ou « — » | num |
| « Évolution » | étiquette teintée (règle §1.2) : « 1er prix » ou « +x,x % » | num |
| « Montant (MAD) » | entier | num |

- **Vide** : « Aucun achat ne correspond. » ou « L'historique se remplira à la première réception
  validée. ».

---

#### 1.4 Fenêtre « Évolution des prix payés, fil par fil » (ComparaisonPrix)

- **Fichier** : `components/direction/ComparaisonPrix.tsx` (307 l.) ; ouverte depuis Matrice, Prix payés,
  Opportunités. `Dialogue tresLarge`, sans garde de saisie.
- **Données** : `/prix/historique` et `/prix/matrice` (cache partagé). Au plus **8 fils** ; au-delà, message
  info « 8 fils au plus sur une même courbe : les {n} suivants sont laissés de côté. ». Fil jamais acheté :
  « Jamais acheté, donc sans courbe : {réf · réf}. Seul un prix de catalogue existe pour {ce fil|ces fils},
  et il n'a pas de date. ».
- **Graphique** (Recharts, hauteur 320 px, `.dir-graphique.haut`) : axe X = vrai calendrier (dates en UTC),
  une **échelle Y par monnaie** (1re à gauche, 2e à droite, au-delà masquées), bornes ×0,95 / ×1,05 ;
  infobulle « Achat du {date} » puis « {prix} {devise} / kg · {n° bon} » ; légende « {réf} — {fournisseur} » ;
  **couleur de courbe = teinte du fil** (`lib/teintes.ts` : nom de couleur FR/EN → teinte, claires
  assombries ; à défaut palette `#1f5fa8, #c2410c, #146c44, #7c3aed, #b45309, #0e7490`) ; deux fils de même
  teinte se distinguent par le trait (plein, « 8 5 », « 2 4 », « 12 4 2 4 »).
- **Bascule** (2 vues) : « Résumé par fil » | « Chaque achat ({n}) » ; note « Prix payés, au kilo, dans la
  monnaie de la facture. » + si 2 monnaies « Deux monnaies : l'échelle de gauche est en {D1}, celle de droite
  en {D2} — les courbes se comparent en tendance, pas en hauteur. ».
- **Vue Résumé par fil** (`Cadre dialogue`) : « Référence » (pastille du trait coloré + réf) ·
  « Fournisseur » · « Achats » (nb ou note « jamais acheté ») · « Premier prix » « {p} {devise} / kg » ·
  « Le » · « Dernier prix » (gras) · « Le » · « Évolution » (dernier/premier − 1 ; étiquette `critique`
  > 5 % **en dur**, `attention` > 0,5 %, `ok` < −0,5 %, sinon neutre) · « Mini – maxi » (2 déc.).
- **Vue Chaque achat** : « Date » · « Référence » · « Fournisseur » · « Bon » · « Quantité (kg) » ·
  « Prix payé » (« {p} {devise} / kg ») · « Contre-valeur (MAD) » ; tri date décroissante ; vide « Aucun
  achat pour ces fils. ».

---

#### 1.5 Onglet Opportunités d'économies — `?onglet=opportunites`

- **Fichier** : `components/direction/AnalyseOpportunites.tsx` (252 l.).
- **Rôles** : direction, achats (`GET /opportunites`, ACHATS, `pilotage.py:280`).
- **Données** : `GET /opportunites?meme_couleur=&autre_fournisseur=&prix_catalogue=&fenetre_jours=`
  (booléens envoyés en « true »/« false » ; fenêtre vide = réglage `fenetre_prix_jours`, borne serveur
  1–3650).
- **Règle serveur** (`moteur.py:2181-2337`) : pour chaque matière **consommée** (conso annuelle = conso
  mensuelle × 12 > 0), prix actuel = **dernier prix payé** (coût rendu usine du dossier d'importation quand
  il existe — droits, fret, transit, hors TVA —, sinon prix facture × cours de la commande), à défaut prix
  catalogue × cours ; rivaux = matières actives de **même composition, même type de fil, même titrage
  (et unité)**, + même couleur si coché, + autre fournisseur si coché ; prix du rival = son achat le plus
  proche de la date du nôtre **dans la fenêtre** ; hors fenêtre → écartée « hors_fenetre » ; prix non daté
  (catalogue) → écartée « sans_date » sauf case « prix de catalogue aussi ». Retient le rival le moins cher ;
  `écart = (actuel − mini)/actuel` ; **économie/an = (actuel − mini) × conso annuelle** ; tri par économie
  décroissante.
- **Indicateurs** :

| Indicateur | Valeur | Détail / infobulle | Teinte |
|---|---|---|---|
| « Économie possible » | `montantCourt(total)` | « par an, au rythme de consommation actuel » ; infobulle montant exact | attention si > 0 |
| « Opportunités » | nb | « dont {n} à plus de {forte} d'écart » | |
| « La plus forte » | économie de la 1re ligne ou « — » | réf. ou « aucune » | |
| « Écartées » | sans_date + hors_fenetre | « {n} sans date · {n} à plus de {fenêtre} j d'écart » ; infobulle « Une opportunité écartée n'est pas comptée : un des deux prix n'a pas de date (prix de catalogue), ou les deux prix sont trop éloignés dans le temps pour se comparer. » | |

- **Carte** : titre « Opportunités d'économies — {n} affichée(s) » ; « Exporter en Excel » →
  `/api/export/opportunites?…mêmes critères` (infobulle « Les opportunités affichées, avec ces critères,
  dans un classeur »).
- **Filtres** : recherche « Fil, fournisseur, couleur… plusieurs mots » (réf., réf. alternative,
  fournisseurs actuel et alternatif, nature, composition, type, couleur, titrage) ; note « Comparé à : »
  (infobulle « Un fil de même composition, même type et même titrage ; et, selon les cases : ») ; cases
  « même couleur » (défaut **cochée**, infobulle « De la même couleur que le nôtre »), « autre fournisseur »
  (défaut cochée, « Chez un autre fournisseur que le nôtre »), « prix de catalogue aussi » (défaut
  décochée, « Y compris les prix de catalogue, non datés : on ne sait pas s'ils sont d'avant ou d'après une
  hausse ») ; liste fenêtre « à {N} j au plus (réglage) », « à 30 / 45 / 60 / 90 / 180 j au plus »
  (infobulle « L'écart maximal entre les dates des deux prix comparés : plus il est court, plus la
  comparaison est juste quand les prix bougent ») ; note « mise à jour… » pendant le rechargement.
  **Pas de bouton « Effacer les filtres ».**
- **Avertissement** (une ligne, texte complet en infobulle) : « {n} opportunité(s) reposent sur au moins un
  coût rendu usine. » + texte serveur : « Comparaison entre fils de même composition, même type et même
  titrage[, de même couleur][, chez un autre fournisseur], sur des prix payés à moins de {N} jours l'un de
  l'autre[ — ou des prix de catalogue, non datés]. Chaque prix est un coût rendu usine quand l'achat est
  passé par un dossier d'importation (droits, fret, transit compris, hors TVA), sinon le prix de la facture
  au cours de la commande. Ni la qualité réelle du fil ni la disponibilité ne se lisent ici : c'est une
  opportunité à négocier, pas une décision. »
- **Tableau** :

| Colonne | Contenu | Format | Infobulle |
|---|---|---|---|
| « Fil · fournisseur actuel » | réf. ; note **fournisseur** · composition · type · titrage · couleur | | |
| « Prix actuel (MAD / kg) » | 2 déc. ; note « {base} du {date} » (base = « coût rendu » ou « prix facture ») ou « catalogue, non daté » | num | « Dernier coût payé pour ce fil, en dirhams le kilo » |
| « Comparable le moins cher · chez » | réf. alternative ; note **fournisseur alternatif** · couleur | | |
| « Son prix (MAD / kg) » | 2 déc. ; note base + date | num | « Le coût payé au concurrent à la date la plus proche du nôtre » |
| « Écart » | étiquette « −x,x % » (`critique` > forte, sinon `attention`) ; note « à {n} j d'écart » | num | |
| « Conso / an (kg) » | entier | num | |
| « Économie / an » | **montant MAD** | num | |
| (sans titre) | bouton « Courbes » (infobulle « Les prix des deux fils dans le temps, sur une même courbe ») | | |

- **Vide** : « Aucune opportunité ne correspond à cette recherche. » / « Aucun fil comparable ne s'achète
  moins cher avec ces critères. ».
- **Gestes** : « Exporter en Excel » (`GET /api/export/opportunites`, ACHATS, `opportunites-AAAA-MM-JJ.xlsx`) ;
  « Courbes » → fenêtre §1.4 avec [réf., réf. alternative].

---

#### 1.6 Onglet Fournisseurs — `?onglet=fournisseurs` (`&fournisseur=` lu)

- **Fichier** : `components/direction/AnalyseFournisseurs.tsx` (278 l.).
- **Rôles** : direction, achats (`GET /fournisseurs/performance`, ACHATS, `pilotage.py:497`).
- **Données** : `GET /fournisseurs/performance` → `cible_otif`, seuils de score, `lignes` (scorecard),
  `receptions` (réceptions notées).
- **Règles serveur** (`moteur.py` `scorecard_fournisseurs`) : OTIF d'une réception = à l'heure × complète ×
  conforme ; à l'heure = arrivée ≤ date promise du bon + retard toléré (l'ETA ne repousse pas) ; complète =
  toutes les lignes que le bon attendait encore livrées (tolérance de livraison complète) ; conforme = ni
  réserve ni refus. Moyennes sur les seules réceptions notées. `taux_retours = kg retournés / kg reçus` ;
  score /100 = OTIF × 60 + retours (20 sans retour, 0 dès 5 %) + délai (20 jusqu'à 15 j, −1 par 5 j au-delà) ;
  classement : ≥ score_strategique (85) « 🟢 Stratégique » / action « Fidéliser + négocier volume » ;
  ≥ score_standard (65) « 🟡 Standard » / « Maintenir relation » ; ≥ score_surveiller (45) « 🟠 À
  surveiller » (affiché **ATTENTION** par `classementLisible`) / « Audit qualité + relance » ; sinon
  « 🔴 À challenger » / « Chercher alternative » ; sans OTIF : « — ». Sous-performant = OTIF < cible
  (95 %). Montant acheté = commandes non annulées, en MAD.
- **Indicateurs** :

| Indicateur | Valeur | Détail | Teinte |
|---|---|---|---|
| « Livraisons parfaites (OTIF) » | moyenne des OTIF **des réceptions notées** (une réception = une voix) | « à l'heure, complètes et conformes · cible {95 %} » | ok si ≥ cible, attention sinon |
| « Sous la cible » | nb de fournisseurs sous-performants | 3 premiers noms (OTIF croissant) ou « aucun fournisseur » | attention si > 0 |
| « Réceptions notées » | nb | « sur {n} réception(s) validée(s) » | |
| « Fournisseurs notés » | « {notés} / {tous} » | « stratégique dès {85}/100 » | |

- **Carte** : titre « Le classement des fournisseurs — {n} affiché(s) » ; « Exporter en Excel » →
  `/api/export/fournisseurs` (infobulle « Le classement et les réceptions notées, dans un classeur »).
- **Filtres** : recherche (initialisée avec `?fournisseur=`) « Fournisseur, pays, classement… plusieurs
  mots » (fournisseur, pays, devise, classement lisible, action) ; case « montrer aussi ceux sans commande »
  (défaut : seuls les fournisseurs avec réception ou commande) ; « Effacer les filtres ».
- **Note** (exacte) : « Score sur 100 : livraisons parfaites (OTIF) × 60 ; retours au fournisseur jusqu'à 20
  points (20 sans retour, 0 dès 5 % de la matière reçue renvoyée) ; délai jusqu'à 20 points (20 jusqu'à 15
  jours, un de moins par 5 jours au-delà). Une livraison est à l'heure si elle arrive à la date promise du bon
  (l'ETA ne la repousse pas), complète si toutes les lignes que le bon attendait encore sont livrées. Cliquer
  sur un fournisseur montre ses réceptions une à une. »
- **Tableau** — tri par score décroissant (sans score en dernier), ligne **cliquable** → fenêtre :

| Colonne | Contenu | Infobulle |
|---|---|---|
| « Fournisseur » | **nom** ; note « pays · devise » | |
| « Délai » | « {n} j » | |
| « Commandes » | nb | |
| « Acheté (MAD) » | entier | |
| « Réceptions » | nb | |
| « À l'heure » | % 0 déc. | « Livrées à la date promise » |
| « Complètes » | % | « Chaque ligne livrée en entier » |
| « Conformes » | % | « Toutes les lignes jugées conformes (ni réserve ni refus) » |
| « OTIF » | étiquette % (`attention` si sous la cible, sinon `ok`) ou « — » | |
| « Retours » | % 1 déc. ou « — » | |
| « Écart de pesée » | « +x,x % » signé | |
| « Score » | **entier** ou « — » | |
| « Classement » | étiquette (Stratégique ok / Standard neutre / surveiller attention / challenger critique) + note action ; « pas encore noté » | |

  Vide : « Aucun fournisseur ne correspond. ».
- **Fenêtre « {fournisseur} — ses réceptions »** (`Dialogue large`) : indicateurs « Score » (« {n} / 100 »,
  détail classement), « OTIF », « Acheté » (détail « {n} commande(s) »), « Action conseillée » ; tableau
  (tri date décroissante) « Réception » · « Date » · « À l'heure » · « Complète » · « Conforme » (Oui/Non/—)
  · « Parfaite » (étiquette Oui ok / Non attention / —) · « Lignes hors tolérance » · « Écart de pesée » ;
  vide « Aucune réception validée pour ce fournisseur. » ; note : « « — » dans « À l'heure » : la commande ne
  portait pas de date de livraison promise ; la réception compte alors comme à l'heure. « — » dans
  « Complète » : la réception ne devait rien (hors commande, ou bon déjà livré) ; elle n'entre pas dans
  l'OTIF. »
- **Gestes** : « Exporter en Excel » (`/api/export/fournisseurs`, 2 feuilles) ; clic ligne → fenêtre ;
  « Effacer les filtres ».

---

#### 1.7 Onglet Coût de revient — `?onglet=revient`

- **Fichier** : `components/importations/AnalyseRevient.tsx` (759 l.) — composant des importations accueilli
  ici (voir aussi l'inventaire des Importations).
- **Rôles** : direction, achats (routeur `analyse_import.py:24`, ACHATS).
- **Données** : `GET /importations/analyse/revient?axe=&q=&debut=&fin=&statut=&qualite=&references=a;b&
  (selection=[JSON] | composition=&type_fil=&titrage=&couleur=&fournisseur=)&detail=true|…` ; vue qualité :
  `GET /importations/analyse/qualite/{code}?debut=&fin=`. Référentiels : `useArticles`, `useClassification`,
  `useQualites`. Refus serveur : 400 « axe inconnu : « x » (attendu : …) », 400 « sélection illisible : … »,
  400 « la sélection doit être une liste de combinaisons », 400 « critère inconnu dans la sélection : … »,
  404 « qualité inconnue ou sans recette : « X » ».
- **Carte** « Ce que la matière importée a coûté, rendue usine » ; **Bascule** (3 vues) « Regroupé » | « Lot
  par lot » | « Recette d'une qualité » ; « Exporter en Excel » → `/api/export/revient?…` (hors vue qualité ;
  infobulle « Le regroupement et le détail lot par lot dans un classeur »).
- **Filtres (vues Regroupé et Lot par lot)** : texte (envoyé au serveur 300 ms après la frappe, sans
  accents, plusieurs mots) « Dossier, référence, lot, fournisseur, couleur… » ; choix-recherche « + Ajouter
  une matière… » (infobulle « Ajouter une matière : l'analyse ne garde que les matières choisies ») ;
  « Par {axe} » (Référence, Titrage — défaut —, Composition, Type de fil, Couleur, Fournisseur, Dossier, Lot,
  Rôle) en vue Regroupé ; statut « Ouverts et clos » / « Dossiers clos » / « Dossiers ouverts » ; période
  « Du … au … » (date d'arrivée du dossier) ; 2e rangée : « Toutes qualités » (ne garder que les fils de la
  recette) + 5 listes **liées** (compositions, titrages, types, couleurs, fournisseurs) ; bouton
  « + Combinaison » (infobulle « + Ajouter cette combinaison : la retenir, puis en composer une autre ; le
  résultat les réunit », grisé sans critère) ; lien « Effacer les filtres » dès 2 filtres actifs. Puces
  « Matières : » et « Réunion de : » (× pour retirer, « + en cours : … »).
- **Indicateurs (Regroupé / Lot par lot)** : « Poids » (« {kg} kg », « {n} lot(s) ») ; « Coût hors TVA »
  (détail « {coût/kg} MAD / kg · achat + charges ») ; « Achat » (« marchandise, en MAD ») ; « Charges hors
  TVA » (« {charges/achat} de l'achat » + lien « + {montant} non répartis » si des frais sont sans
  marchandise, infobulle listant les dossiers, clic ouvre le 1er dossier) ; « Coût TTC » (« dont TVA … »).
- **Tableau Regroupé** : {axe} · « Lots » · « Poids » · « Achat MAD » · « Charges hors TVA » (infobulle
  « toutes les charges sauf la TVA » ; cellule : « {surcoût} de l'achat ») · « Coût hors TVA » · « Coût hors
  TVA / kg » (note « achat {prix/kg} ») · « TVA » · « Coût TTC » · « Dossiers » (4 liens + « +n ») ; ligne
  cliquable si l'axe est un critère (infobulle « Voir ses références une à une » : pose le filtre et passe
  à l'axe Référence) ; pied « Total » (coût/kg recalculé = total coût / total poids) si > 1 ligne ; vide
  « Aucune marchandise importée ne répond à ces critères. ».
- **Tableau Lot par lot** : « Dossier » (lien + étiquette « ouvert ») · « Arrivée » · « Référence » · « Lot » ·
  « Fournisseur » · « Titrage » · « Poids » · « Achat MAD » · « Charges hors TVA » · « Coût hors TVA » · « Coût
  hors TVA / kg » · « TVA » · « Coût TTC » + pied Total.
- **Vue Recette d'une qualité** : liste « Choisir une qualité… » + période ; texte vide « Choisir une
  qualité : on croise sa recette (quels fils, dans quelle proportion) avec ce que ces fils ont coûté, rendus
  usine, dans les dossiers d'importation. » ; indicateurs « Coût matière / m² » (« recette × coût hors TVA de
  chaque fil · {kg/m²} kg / m² »), « Coût / kg de tapis » (« pondéré par la recette … »), « Recette
  couverte » (% du poids, attention < 99,9 %), « Poids importé » ; colonnes supplémentaires « Rôle », « Part
  du rôle » (%), « kg / m² » (poids du rôle au m² × part), « Coût / m² » ; pied par rôle (« {n} fil(s)
  importé(s) sur {n} », « aucun fil importé : rôle hors du coût calculé » / « coût connu sur {x %} du rôle,
  étendu au reste » / « coût connu pour tout le rôle », « · rôle au mètre (ml/m²), hors du poids au m² ») et
  ligne « Coût matière de la qualité ».
- **Notions** : Achat, Charges hors TVA, Coût hors TVA (= coût de revient), TVA (récupérable), Coût TTC,
  surcoût (charges / achat), combinaison de critères (réunion), frais non répartis.
- **Lien** : n° de dossier → fenêtre `DetailDossier` (inventaire Importations).

---

#### 1.8 Onglet Échéancier — `?onglet=echeancier`

- **Fichier** : `components/direction/AnalyseEcheancier.tsx` (368 l.).
- **Rôles** : direction, achats (`GET /echeancier` et `PUT /echeancier/paiement` : ACHATS, `suivi.py:320`,
  `412`).
- **Données** : `GET /echeancier?du=&au=`. Règles serveur (`suivi.py:293-395`) :
  - **Facture fournisseur** : montant = montant saisi, **à défaut Σ pesée × prix** des lignes non refusées de
    ses réceptions validées (« estimé ») ; facture dont toutes les réceptions sont annulées → **écartée**
    (« réception annulée : plus due », ou si déjà réglée « réglée, réception annulée : avoir à demander ») ;
    facture qui ne porte que des brouillons de réception → pas encore due (absente) ; réglée → « Réglées » ;
    avec échéance → « Échéances » ; sans échéance et montant > 0 → « À dater ».
  - **Frais d'importation** (genre « Frais d'importation ({poste}) », tiers = prestataire ou « — », pièce
    « {n° dossier} · {pièce} », en MAD) : mêmes règles (même dossier clos).
  - Conversion MAD au **cours du jour** de la devise ; `du`/`au` ne filtrent que les échéances datées ;
    `echu_mad` = Σ échéances < aujourd'hui ; `par_mois` = Σ par mois d'échéance ; réglées limitées à 300.
- **Indicateurs** :

| Indicateur | Valeur | Détail | Teinte |
|---|---|---|---|
| « À payer » | `montantCourt(total_mad)` | « {n} échéance(s) connue(s) » | |
| « Échu, non réglé » | `montantCourt(echu_mad)` | « {n} échéance(s) dépassée(s) » | critique si > 0, sinon ok |
| « Dans les 30 jours » | Σ échéances entre aujourd'hui et J+30 | « {n} échéance(s) » | attention si ≥ 1 |
| « À dater » | Σ à dater | « {n} facture(s) ou frais sans échéance » | attention si ≥ 1 |

- **Message info** si écartées : « {n} facture(s) de réceptions annulées ne sont plus dues et ne comptent
  pas : {pièce (tiers)}, … (6 au plus, puis « … »). Les détacher de la réception, ou faire établir un
  avoir. »
- **Carte** : titre = **Bascule** (4 vues) « Échéances ({n} · {total}) » | « Par mois » | « À dater ({n}) » |
  « Réglées ({n}) » ; « Exporter en Excel » → `/api/export/echeancier?du=&au=` (infobulle « L'échéancier ligne
  par ligne, par mois, et ce qui est à dater, dans un classeur »).
- **Filtres** : recherche « Fournisseur, prestataire, n° de pièce… » (nature, tiers, pièce, devise) ; liste
  « Toutes les échéances » + natures (« Facture fournisseur », « Frais d'importation » regroupant tous les
  postes) ; « Du » (infobulle « Échéances à partir de ce jour », max = Au) ; « Au » (« Échéances jusqu'à ce
  jour inclus », min = Du) ; « Effacer les filtres » dès 1 filtre.
- **Vue Échéances** : « Échéance » (rouge gras si en retard) · « Nature » · « Fournisseur ou prestataire » ·
  « Pièce » · « Montant » (« {montant} {devise} » + note « estimé », infobulle « Montant non saisi sur la
  facture : la pesée × le prix de ses réceptions ») · « Montant MAD » · étiquette « en retard » (critique) ·
  geste « Réglée… ». Tri par échéance croissante (serveur). Vide : « Aucune échéance ne correspond. » ou
  « Aucune échéance connue : elles viennent de l'échéance des factures (réceptions) et des frais
  d'importation. ».
- **Vue Par mois** : « Mois » · « À payer (MAD) » ; mois passés en rouge ; vide « Rien à payer. ».
- **Vue À dater** : « Nature » · « Fournisseur ou prestataire » · « Pièce » · « Montant » · « Montant MAD » ·
  « Réglée… » ; vide « Toutes les factures et tous les frais connus ont leur échéance. ».
- **Vue Réglées** : « Réglée le » · « Échéance » · « Nature » · « Fournisseur ou prestataire » · « Pièce » ·
  « Montant » · « Montant MAD » · « Annuler le règlement » ; vide « Aucun règlement noté : « Réglée… » sur une
  échéance le note. ».
- **Gestes** :

| Geste | Rôle | Conditions | Confirmation (sur place) | Appel | Succès | Refus serveur |
|---|---|---|---|---|---|---|
| « Réglée… » (infobulle « Payée : elle sort de l'échéancier et de l'« échu, non réglé » ») | dir., achats | grisé pendant un envoi | « Réglée le [date, défaut aujourd'hui, max aujourd'hui] · Non · Oui, réglée » | `PUT /echeancier/paiement {objet, id, payee_le}` | « {pièce} réglée le {date}. » | 404 « Pièce introuvable. » ; « Un règlement ne se date pas dans le futur : c'est un fait constaté. » ; « Le règlement ({jj/mm/aaaa}) précède la pièce qu'il règle ({jj/mm/aaaa}). » (début = date de facture, sinon 1re réception ; date de pièce pour un frais) |
| « Annuler le règlement » (infobulle « La pièce redevient due : elle revient dans l'échéancier ») | idem | idem | « Annuler le règlement ? · Non · Oui, annuler » | `PUT /echeancier/paiement {…, payee_le: null}` | « Règlement de {pièce} annulé : elle redevient due. » | 404 |
| « Exporter en Excel » | idem | | | `GET /api/export/echeancier` | `echeancier-AAAA-MM-JJ.xlsx` (feuilles Échéances, À dater, Par mois) | |
| « Effacer les filtres » | | ≥ 1 filtre | | | | |

  Journal serveur : action « règlement » / « règlement annulé », détail « facture {n°} · {fournisseur} · réglé
  le {date} » ou « frais {poste} · dossier {n°} ». Après succès, rafraîchit échéancier, réceptions, dossiers.

---

#### 1.9 Onglet Contrôles — `?onglet=controles`

- **Fichier** : `components/direction/AnalyseControles.tsx` (350 l.) ; règles `gestion_mp/calcul/controles.py`
  (1142 l.).
- **Rôles** : direction, achats (`GET /controles` ACHATS `pilotage.py:349` ; `GET /controles/soldes` ACHATS
  `stock.py:418`). Les liens du détail lisent aussi `/commandes`, `/dossiers`, `/receptions`, qualités,
  fournisseurs.
- **Données** : `GET /controles` → `date_reference`, `synthese {total, conformes, garantis, anomalies,
  bloquants, score}`, `controles[] {code, libelle, anomalies, conforme, garanti, gravite, quoi_faire, vers,
  detail[]}`, `colonnes` (libellés des clés du détail). Les contrôles d'intégrité (C12, C14, C27, C37) tournent
  sur **toutes** les données ; les autres sur les données à la date. `GET /controles/soldes` → soldes tenus
  vs Σ journal par (lot, magasin).
- **Synthèse** (`controles.py:1128-1142`) : `anomalies` = nb de contrôles non conformes ; `bloquants` = nb de
  contrôles bloquants non conformes ; les contrôles **garantis par la base** (conformes ET listés dans
  GARANTIS) ne comptent ni dans `total` ni dans `conformes` ; `score = conformes / total` (1 si total nul).
- **Indicateurs** :

| Indicateur | Valeur | Détail / infobulle | Teinte |
|---|---|---|---|
| « Score » | % 0 déc. | « {conformes} conformes sur {total} vérifiés[ · {g} garantis par la base] » ; infobulle « Au {date} » | critique si bloquants, attention si anomalies, sinon ok |
| « Anomalies » | nb | « contrôles à revoir » | attention / ok |
| « Bloquants » | nb | « le pilotage en est faussé » ou « aucun » | critique / ok |
| « Soldes et journal » | « Concordants » / « Écart ! » / « … » / « — » | « {n} soldes = journal » ou « {n} écart(s), {n} solde(s) négatif(s) » ou message d'erreur | ok / critique |

- **Message d'erreur** si soldes non conformes : « Le stock tenu ne retombe pas sur le journal des mouvements
  ({n} lot(s) en écart, {n} solde(s) négatif(s)). Une écriture a contourné le chemin normal : prévenir la
  personne qui entretient le serveur avant toute nouvelle saisie. » + 8 lignes « lot n° {id}, magasin n° {id} :
  journal {x} kg, solde {y} kg ».
- **Carte** : titre « Les contrôles — {n} affiché(s) » ; « Exporter en Excel » → `/api/export/controles`
  (infobulle « Les contrôles, quoi faire, et les lignes fautives de chacun »).
- **Filtres** : recherche « Code, libellé, gravité… plusieurs mots » (code, libellé, gravité lisible, quoi
  faire) ; case « seulement les anomalies » (**défaut cochée**) ; bandeau rouge dans la rangée si bloquants :
  « {n} bloquant(s) : le pilotage est faussé tant que {C01, C05…} n'{a|ont} pas été corrigé(s). » ;
  « Effacer les filtres » (si recherche ou case décochée) → remet la case cochée.
- **Tableau** — tri : non conformes d'abord, puis gravité (bloquant, avertissement, information) ; ligne
  **cliquable seulement si non conforme** → fenêtre détail :

| Colonne | Contenu |
|---|---|
| « Code » | `<code>C08</code>` |
| « Ce qui est vérifié » | libellé |
| « Gravité » | « Bloquant » / « À corriger » / « Pour information » |
| « Anomalies » | étiquette : « garanti par la base » (neutre) / « OK » (ok) / nombre (critique si bloquant, neutre si information, attention sinon) |
| « Quoi faire » | « Ne peut pas sonner : {raison} » (garanti) / « — » (conforme) / texte quoi faire |

  Vide : « Aucune anomalie : tous les contrôles sont conformes. » (case cochée, sans recherche) sinon « Aucun
  contrôle ne correspond. ».
- **Fenêtre « {code} — {libellé} »** (`Dialogue tresLarge`) : message (erreur si bloquant, info sinon)
  « **Quoi faire :** {texte} » + lien « Ouvrir l'écran → » (vers l'écran du contrôle, ferme la fenêtre) ;
  étiquette de gravité ; note « {n} ligne(s) à examiner[ (les {k} premières affichées)]. » (détail limité à
  200 lignes) ; recherche « Chercher dans les lignes… » ; tableau aux **colonnes dynamiques** (clés du
  détail, libellées par `COLONNES`, sinon clé capitalisée) ; nombres entiers « 1 234 », décimaux 2 déc. ;
  dates AAAA-MM-JJ → jj/mm/aaaa ; booléens Oui/Non ; colonne `ecart` numérique affichée en % (`part`).
  **Liens de cellules** (« Ouvrir pour corriger », fermant la fenêtre) : `reference` → `/stock?onglet=matieres&q={réf}` ;
  `numero_of` → `/sorties?ordre={n°}` ; `lot` → `/stock?onglet=lots&q={lot}` ; `metier` → `/metiers` ;
  `numero` → `/commandes?commande={id}` ; `dossier` → `/importations?dossier={id}` ; `reception` →
  `/receptions?reception={id}` ; `qualite` → `/qualites?qualite={id}` ; `fournisseur` →
  `/catalogue?onglet=fournisseurs&fournisseur={id}`. Vide : « Rien ne correspond. » ou « Ce contrôle ne
  détaille pas ses lignes. ».

##### Liste complète des contrôles (`calcul/controles.py`, ordre de calcul ; valeurs des réglages par défaut)

Libellé de quoi faire `_HORS_SAISIE` (C02, C04, C14, C16, C26, C31, C32) : « Gestion MP refuse déjà cette
saisie : la ligne vient d'une reprise de données ou d'une écriture faite hors de l'écran. Prévenir la personne
qui entretient le serveur, puis annuler le document fautif (contre-passation) et le ressaisir. »

| Code | Libellé exact | Gravité | Règle (sonne quand…) | Colonnes du détail | Écran « Ouvrir » | Quoi faire (exact) |
|---|---|---|---|---|---|---|
| C01 | « Recette dont un rôle ne fait pas 100 % » | bloquant | dans une qualité, un rôle utilisé ne somme pas à 100 % | Qualité, Rôles (« rôle (somme %) ») | /qualites | « La direction ouvre la qualité (Qualités & recettes › Recette) et corrige les pourcentages du rôle signalé jusqu'à 100 % (les achats, qui la lisent seulement, le lui signalent) : tant que ce n'est pas fait, le besoin en fil de cette qualité est faux, et le plan d'achat avec lui. » |
| C02 | « Sortie vers les machines sans ordre (n° OF) » | avertissement | mouvement SORTIE_PROD sans n° OF | Date, Référence | /sorties | _HORS_SAISIE |
| C03 | « Retour sans motif, ou avec le motif d'une autre famille » | avertissement | retour des machines hors R1/R2/R4, retour fournisseur hors R3/R5/R6 | Date, Référence, Type, Motif | /operations | « Ouvrir le retour et vérifier son motif : un retour des machines porte R1, R2 ou R4, un retour au fournisseur R3, R5 ou R6. S'il manque, annuler le retour (contre-passation) et le ressaisir avec son motif. » |
| C04 | « Mouvement de stock sans auteur » | avertissement | mouvement sans utilisateur | Date, Référence | /stock?onglet=mouvements | _HORS_SAISIE |
| C05 | « Matière sans fournisseur » | bloquant | matière du catalogue sans fournisseur | Référence | /catalogue | « Ouvrir la matière (Matières, classification, fournisseurs) et lui donner son fournisseur — ou la désactiver si elle ne s'achète plus. Sans fournisseur, le plan d'achat ne sait pas à qui la commander. » |
| C06 | « Commande non livrée à sa date prévue (ou 60 jours après la commande) » | avertissement | commande partie, date du jour > (arrivée attendue — ETA sinon date promise — ou date du bon + 60 j) + retard toléré, et une ligne a encore un reste à livrer | N°, Fournisseur, Date de la commande, Jours, Retard (j) | /commandes | « Relancer le fournisseur et noter la nouvelle date d'arrivée (ETA) dans le suivi d'expédition de la commande. S'il ne livrera pas le reste, solder la commande : elle ne comptera plus dans le stock projeté. » |
| C07 | « Matière jamais utilisée (ni recette, ni mouvement) » | information | référence ni en recette ni en mouvement | Référence | /catalogue | « Si la matière ne sert plus, la désactiver dans sa fiche ; si elle doit servir, l'ajouter à la recette d'une qualité. Pour information seulement. » |
| C08 | « Écart de pesée supérieur à 2% » (toler_ecart_pesee) | avertissement | \|écart relatif pesée / attendu\| > tolérance ; une ligne non pesée d'une réception non validée est ignorée | Réception, Référence, Attendu, Pesé, Écart (%) | /receptions?onglet=pesees | « Comparer la pesée au bon de livraison avec le fournisseur. Écart confirmé : le réclamer (avoir ou complément). Pesée fausse : corriger le stock par un ajustement motivé. » |
| C09 | « Prix négatif au catalogue » | bloquant · **garanti** (« La base refuse un prix négatif (contrainte article_prix_check). ») | prix < 0 | Référence, Prix | /catalogue | « Corriger le prix d'achat dans la fiche matière. » |
| C10 | « Délai fournisseur nul ou négatif » | avertissement · **garanti** (« La base refuse un délai fournisseur nul ou négatif (fournisseur_delai_jours_check). ») | délai ≤ 0 | Fournisseur, Délai (j) | /catalogue?onglet=fournisseurs | « Corriger le délai (en jours, au moins 1) dans la fiche fournisseur. » |
| C11 | « Cours de change à zéro » | bloquant · **garanti** (« La base refuse un cours de change nul ou négatif (devise_taux_check). ») | cours EUR ou USD ≤ 0 | Cours, Valeur (MAD) | /reglages?onglet=devises | « Saisir le cours de la devise dans Réglages › Devises (ouvert à la direction et aux achats). » |
| C12 | « Stock tenu (soldes des lots) différent du journal des mouvements » (repli : « Stock par magasin différent du stock net des mouvements ») | bloquant | solde tenu ≠ Σ journal par (référence, lot, magasin) au-delà de la poussière | Référence, Lot, Magasin, Stock, Attendu | /stock?onglet=mouvements | « Bloquant : le stock tenu ne retombe plus sur le journal des mouvements. Ne plus rien saisir sur ces matières et prévenir la personne qui entretient le serveur : une écriture a contourné le chemin normal. » |
| C13 | « Stock projeté négatif pendant le délai d'approvisionnement » | avertissement | stock projeté < 0 | Référence, Stock net, Stock projeté, Manque (tri manque décroissant) | /plan-achat | « Commander tout de suite (Plan d'achat), ou faire avancer une livraison déjà commandée : la matière manquera avant que la commande n'arrive. » |
| C14 | « Mouvement de stock à une date future » | avertissement | mouvement daté après aujourd'hui | Date, Référence | /stock?onglet=mouvements | _HORS_SAISIE |
| C15 | « Matière d'une recette sans prix d'achat » | avertissement | composant à % > 0 dont le prix au kilo est nul | Qualité, Référence | /catalogue | « Saisir le prix d'achat dans la fiche matière : sans lui, le coût au m² de la qualité et le budget d'achat sont sous-évalués. » |
| C16 | « Intégrité référentielle des mouvements » | bloquant · **garanti** (« Les mouvements pointent leur matière et leur fournisseur (par le lot) par des clés étrangères : un mouvement orphelin ne peut pas s'écrire. ») | mouvement d'une référence ou d'un fournisseur inconnu | Référence/Fournisseur, Date | /stock?onglet=mouvements | _HORS_SAISIE |
| C19 | « Fournisseur qui facture en plusieurs devises » | information | > 1 devise parmi les prix de ses matières | Fournisseur, Devises (« EUR (n matière(s)) · USD (…) »), Devise par défaut | /catalogue | « Normal si le fournisseur facture vraiment en deux monnaies : un bon de commande part par devise. Sinon, corriger la devise de la matière dans sa fiche. » |
| C21 | « Prix au catalogue sans devise » | bloquant · **garanti** (« La devise d'un prix est une clé étrangère vers les devises : un prix sans devise connue ne peut pas s'écrire. ») | prix non nul sans devise | Référence, Prix, Fournisseur | /catalogue | « Choisir la devise du prix dans la fiche matière. » |
| C20 | « Stock négatif sur une matière sans consommation » | bloquant | stock net < 0 et conso mensuelle = 0 | Référence, Stock net | /inventaire | « Faire compter la matière (Inventaire) et corriger le stock par un ajustement motivé. » |
| C22 | « Étage monté plus large que la laize du métier » | avertissement | métier actif : Σ(mètres × % / 100) d'un étage > laize | Métier, Étage, Laize (m), Mètres montés, Fils | /metiers | « Ouvrir le métier (Métiers à tisser) et ramener les mètres montés à cet étage à la laize du métier. » |
| C24 | « Fil monté à un étage que le métier n'a pas » | avertissement | étage du fil > nb d'étages | Métier, Étage, Étages du métier, Référence | /metiers | « Retirer le fil de cet étage, ou augmenter le nombre d'étages du métier. » |
| C25 | « Fil monté sans sortie de magasin enregistrée (le magasin le compte encore) » | avertissement | fil monté pesant, sans aucune SORTIE_PROD de sa référence | Métier, Étage, Référence, Poids (kg) | /sorties | « Enregistrer la sortie vers les machines de ce fil (Sorties vers les machines) : sans elle, le magasin le compte encore en stock alors qu'il est monté. » |
| C23 | « Fil monté sans poids de bobine au catalogue » | bloquant | fil monté dont la matière n'a pas de kg / bobine | Métier, Étage, Référence, Mètres | /catalogue | « Saisir le poids d'une bobine (kg / bobine) dans la fiche matière : sans lui, le fil monté pèse zéro et manque au stock. » |
| C26 | « Sortie de stock sans numéro de lot » | avertissement | SORTIE_PROD ou RETOUR_FOURNISSEUR sans lot (200 dernières) | Date, Référence, Quantité, Ordre (n° OF), Par | /stock?onglet=mouvements | _HORS_SAISIE |
| C27 | « Lot dont il est sorti plus qu'il n'est entré » | bloquant | solde final d'un lot < 0 | Référence, Lot, Stock, Entré, Sorti | /stock?onglet=lots | « Bloquant : ouvrir le lot (son numéro mène à Stock › Lots, lots épuisés compris) et cliquer « Suivre » pour trouver la sortie de trop ; l'annuler (contre-passation), ou enregistrer l'entrée oubliée. » |
| C37 | « Lot sous zéro à une date passée (écriture datée avant l'entrée de la matière) » | bloquant | cumul jour par jour d'un (référence, lot, magasin) < 0 un soir passé | Référence, Lot, Magasin, Date (1er jour), Manque (creux) | /stock?onglet=mouvements | « Bloquant : une écriture est datée avant l'entrée de son lot, ou a pris plus que ce que le lot portait ce jour-là — elle est partie à coût nul. Ouvrir le journal du lot, annuler l'écriture fautive (contre-passation) et la ressaisir à une date où la matière était là, ou sur un autre lot. » |
| C28 | « Dossier d'importation arrivé depuis plus de 30 jours et sans frais » | avertissement | dossier ouvert avec marchandises, sans frais non récupérable, arrivé > 30 j | Dossier, Arrivée, Marchandises, Jours | /importations | « Saisir les frais du dossier (droits, fret, transit…) dans Importations : sans eux, le coût de revient n'est que le prix de la facture. » |
| C34 | « Dossier d'importation avec des frais mais sans marchandise » | avertissement | frais saisis, aucune marchandise | Dossier, Frais (MAD) | /importations | « Rattacher les marchandises au dossier (Importations › À rattacher), ou retirer les frais saisis par erreur. » |
| C29 | « TVA d'importation éloignée de 20 % de la valeur en douane » (taux_tva_import) | avertissement | \|TVA saisie (poste TVA) − TVA attendue\| > écart toléré (≈ 5 %) ; attendue = taux × (valeur en douane + droits + TPI) | Dossier, TVA saisie (MAD), TVA attendue (MAD), Écart (MAD) | /importations | « Comparer la TVA saisie dans les frais du dossier à la quittance de la douane ; corriger le frais, ou la valeur en douane des marchandises. » |
| C35 | « Dossier d'importation (ou une de ses marchandises) dont les frais dépassent 100 % de la marchandise » (seuil_surcout_import) | avertissement | frais hors TVA > seuil × marchandise, au dossier ou sur une ligne | Dossier, Référence (« (tout le dossier) »), Marchandise (MAD), Frais hors TVA (MAD), Frais / marchandise (%) | /importations | « Reprendre les frais du dossier sur leurs pièces (quittance, facture du transitaire) : un zéro de trop, ou les frais d'un autre dossier. Tant qu'ils restent, ils entrent dans le coût moyen du stock. » |
| C36 | « Facture d'un dossier d'importation éloignée de plus de 2 % de la marchandise reçue » (toler_facture_import) | avertissement | facture vs pesée × prix hors tolérance | Dossier, Facture, Facture (devise), Reçu, pesée × prix (devise), Devise, Écart (%) | /importations | « Rapprocher la facture du bon de livraison et de la pesée : un manque de poids se réclame au fournisseur (avoir), une facture mal saisie se corrige sur sa réception, un camion pas encore rattaché rejoint le dossier. Le coût, lui, reste à la pesée × le prix. » |
| C31 | « Ordre de fabrication servi à plusieurs dates » | avertissement | un n° OF a des sorties à > 1 date | Ordre (n° OF), Dates, Jours | /sorties | _HORS_SAISIE |
| C32 | « Ordre de fabrication daté avant un ordre de numéro inférieur » | information | n° « OF-AAAA-NNNN » plus grand daté avant un plus petit | Ordre (n° OF), Date, Après, Date de l'ordre suivant | /sorties | _HORS_SAISIE |
| C30 | « Poids de bobine reçu éloigné du catalogue de plus de 5% » (toler_poids_bobine) | information | dernière réception du fil : kg / bobine constaté hors tolérance | Référence, Fournisseur, Catalogue (kg / bobine), Constaté (kg / bobine), Écart (%), Réception | /receptions?onglet=bobines | « Vérifier le poids de bobine avec le fournisseur ; si le nouveau poids est le bon, le reporter dans la fiche matière (kg / bobine). » |
| C33 | « Stock minimum du catalogue supérieur à 3 mois de consommation » (plafond_stock_min_mois) | information | stock min > plafond × conso de l'horizon | Référence, Stock minimum, Conso / mois, Mois, Retenu | /catalogue | « Baisser le stock minimum dans la fiche matière : il immobilise plus de mois de consommation que le plafond réglé (le plan d'achat le plafonne déjà). » |
| C38 | « Prix du catalogue à plus de 3 fois (ou moins d'un 3e) du dernier prix payé » | avertissement | matière active : prix catalogue (MAD/kg) / dernier payé (MAD/kg) > 3 ou < 1/3 | Référence, Fournisseur, Prix du catalogue, Dernier prix payé, Date, Catalogue / payé | /catalogue | « Comparer le prix de la fiche matière au dernier achat (tous deux lus au kilo — un prix au mètre l'est par la densité ; unité du prix, densité, devise) et le corriger s'il est faux — ou confirmer le dernier prix payé avec le fournisseur. C'est au responsable du référentiel de trancher : le contrôle ne corrige rien. » |
| C17 | « Matière en alerte sans second fournisseur » | information | sourcing « MONO-SOURCE » et statut en alerte | Référence, Fournisseur, À commander (MAD) | /catalogue | « Chercher un second fournisseur pour cette matière, ou un fil équivalent : elle est en alerte et ne dépend que d'un seul. » |
| C18 | « Stock dormant depuis plus de 180 jours » (seuil_dormant) | information | stock détenu sans sortie ni entrée depuis le seuil | Référence, Stock, Jours sans mouvement | /stock | « Voir si la matière peut servir une autre qualité, se rendre au fournisseur ou se vendre ; sinon, la déclasser. Pour information seulement. » |

Total : **38 contrôles** (C01–C38), dont 5 garantis par la base (C09, C10, C11, C16, C21) ; 11 bloquants
(C01, C05, C09, C11, C12, C16, C20, C21, C23, C27, C37), 7 « pour information » (C07, C17, C18, C19, C30, C32,
C33), 20 « à corriger » (avertissement). Disparus
du classeur (en-tête de `controles.py`) : T05, T06 (clés étrangères), T17–T19 (transaction unique), T20
(tableur).

- **Gestes** : « Exporter en Excel » (`GET /api/export/controles` ACHATS → `controles-AAAA-MM-JJ.xlsx` : feuille
  « Contrôles » [Code, Ce qui est vérifié, Gravité, Anomalies, État (« garanti par la base » / « conforme » /
  « à corriger »), Quoi faire] avec ligne « {c} conformes sur {t} vérifiés (et {g} garantis par la base) ·
  {b} bloquant(s) · score {s} », puis une feuille par contrôle en anomalie) ; clic ligne → fenêtre ;
  « Ouvrir l'écran → » ; liens de cellules ; « Effacer les filtres ».

---

#### 1.10 Onglet Production — `?onglet=production`

- **Fichier** : `components/direction/AnalyseProduction.tsx` (221 l.).
- **Rôles** : direction, achats (écran) ; `GET /ordres-fabrication` n'exige qu'une session (`pilotage.py:690`).
- **Données** : ordres (hors ordres annulés) lus comme dans Sorties : sorti, retours, **sorti net**, prévu
  par la recette **perte comprise** (taux de perte), écart = net − prévu, écart relatif = écart / prévu ;
  totaux : `total_consomme` = Σ net ; `total_theorique` et `total_consomme_avec_recette` sur les seuls ordres
  qui disent leur qualité.
- **Indicateurs** : « Sorti net par les ordres » (« {kg} kg », « {n} ordre(s) de fabrication, retours
  déduits ») ; « Sorti face à la recette » (signe de (sorti avec recette − prévu)/prévu ; ok ≤ 5 %, attention
  au-delà ; « {kg} kg sortis pour {kg} kg prévus par la recette ») ; « Ordres au-delà de 5 % d'écart »
  (« {n} sur {n} », « parmi les ordres qui disent leur qualité »). Seuil 5 % **en dur**.
- **Carte** « Rendement par ordre — {n} ordre(s) » ; lien-bouton « Plan et réalisé par qualité → » →
  `/production?onglet=realise`.
- **Filtres** : recherche « Ordre, qualité, lot, référence… plusieurs mots » (n° OF, qualité, commentaire,
  lots, références) ; case « seulement les écarts de plus de 5 % » ; « Effacer les filtres ».
- **Tableau** (ligne cliquable → fenêtre) : « Ordre » (**n°** + note commentaire) · « Période » (début[ →
  fin]) · « Qualité » (ou note « hors recette ») · « Surface (m²) » · « Sorti net (kg) » · « Prévu par la
  recette (kg) » · « Écart » (étiquette signée, attention > 5 %) · « Lots » (nombre). Note sous le tableau :
  « Cliquer un ordre montre, fil par fil, le sorti net face au prévu par la recette. » Vide : « Aucun ordre ne
  correspond. » / « Aucune sortie n'a encore été rattachée à un ordre de fabrication. ».
- **Fenêtre « Ordre de fabrication {n°} »** (`Dialogue large`) : indicateurs « Sorti » (« {kg} kg rendus » ou
  « aucun retour »), « Sorti net » (« sorti moins les retours »), « Prévu par la recette » (« {qualité} : {m²}
  m² · … » ou « qualité non précisée »), « Écart » (« +{kg} kg ») ; tableau « Référence » · « Sorti net (kg) » ·
  « Prévu par la recette (kg) » · « Écart (kg) » · étiquettes « hors recette » / « pas sorti » ; note « Lots
  utilisés : {…} » ou « aucun lot nommé » ; lien « Traçabilité de l'ordre → » →
  `/stock?onglet=tracabilite&ordre={n°}`.

---

### 2. RÉGLAGES — `/reglages` (`?onglet=` lu et écrit)

#### 2.0 Cadre de la page

- **Fichiers** : `pages/Reglages.tsx` (215 l.), `components/direction/Reglages*.tsx`,
  `components/importations/ReglagesPostesFrais.tsx`, `ReglagesCodesDouaniers.tsx`.
- **Rôles** :
  - Menu « Pilotage › Réglages », infobulle « Réglages, comptes, sauvegardes » : rôles `[]` → **direction
    seule** dans le menu (`App.tsx:87`).
  - Route `garde(['achats'])` (`App.tsx:263`) : direction **et achats** entrent ; alimentation renvoyée à
    son accueil.
  - Dans l'écran (`Reglages.tsx:86`) : direction → 11 onglets ; achats → **le seul onglet Devises** (le
    contrôle C11 les y envoie, `/reglages?onglet=devises`) ; autre rôle → message info « Les réglages sont
    réservés à la direction. » (inatteignable, la garde le renvoie avant).
  - Bouton d'en-tête « Métiers à tisser → » (lien `/metiers`, infobulle « Les métiers à tisser, leurs réglages
    et les fils montés : une page à part ») : direction seule.
- **Adresse** : `?onglet=` ∈ parametres, devises, magasins, postes, codes, comptes, sauvegardes, journal,
  courriel, serveur, telephone ; inconnu ou non permis → 1er onglet permis. Choisir « parametres » efface le
  paramètre ; les autres l'écrivent (`replace`).
- **Onglets** (libellé court affiché, long en infobulle ; pas de compteur) :

| Clé | Affiché | Infobulle | Sous-titre (exact) |
|---|---|---|---|
| parametres | « Paramètres » | | « Les seuils et règles de calcul. Chaque changement est historisé et recalcule tout le pilotage. » |
| devises | « Devises » | | « Les devises d'achat, leur cours en MAD, depuis quand il vaut et ses valeurs passées. » |
| magasins | « Magasins » | | « Où la matière est rangée — stock courant et quarantaine — et ce que chacun contient. » |
| postes | « Frais » | « Postes de frais » | « Les frais d'un dossier d'importation : récupérables ou non, répartis à la valeur ou au poids. » |
| codes | « Douane » | « Codes douaniers » | « Les positions du tarif douanier et leur taux de droits : de quoi prévoir et vérifier les droits d'un dossier. » |
| comptes | « Comptes » | | « Qui se connecte, avec quel rôle et quel code. » |
| sauvegardes | « Sauvegardes » | | « Les copies de la base : leur état, leur conservation, en faire une, revenir à l'une d'elles. » |
| journal | « Journal des actions » | | « Qui a fait quoi, sur quoi, et quand — filtré et exportable. » |
| courriel | « Courriel » | « Courriel du lundi » | « La synthèse de la semaine envoyée chaque lundi : à qui, et ce qu'elle dirait aujourd'hui. » |
| serveur | « Serveur » | | « La version, la base, les sauvegardes, l'adresse sur le réseau et qui est connecté. » |
| telephone | « Téléphone » | | « Ouvrir Gestion MP sur un téléphone, dans l'usine ou en dehors. » |

---

#### 2.1 Onglet Paramètres — `/reglages` ou `?onglet=parametres`

- **Fichiers** : `components/direction/ReglagesParametres.tsx` (352 l.), `gestion_mp/parametres.py` (liste,
  défauts, bornes), `gestion_mp/api/comptes.py:276-387`.
- **Rôles** : direction (onglet). `GET /parametres` : toute session ; `PUT /parametres` et
  `GET /parametres/historique` : DIRECTION.
- **Données** : `GET /parametres` → `reglages[] {cle, libelle, famille, unite, echelle, aide, bas, haut,
  texte, defaut, valeur}` (valeur texte stockée ; un taux est rangé en fraction et saisi en %, `echelle` 100).
- **Mise en page** : une carte dont le **titre = la famille active** ; à gauche la liste des familles
  (`nav.dir-familles`, 200 px ; chaque bouton porte un compteur des modifications non enregistrées, infobulle
  « {n} modification(s) pas encore enregistrée(s) ») ; à droite, dans un `Cadre`, la phrase d'aide de la
  famille puis les champs en grille (`.dir-reglages`, colonnes ≥ 300 px). Sous 900 px, familles en ligne.
- **Familles (10, dans cet ordre)** et phrase d'aide exacte (`AIDES_FAMILLE`) :
  1. « Couverture et statuts » — « Les couvertures critique et d'ATTENTION ne règlent que le « statut
     classeur », gardé pour comparaison (colonne « Statut classeur » du stock, info-bulle du Cockpit) : la
     couverture — les jours de consommation que le stock tient encore après le délai — comparée à ces deux
     seuils, les mêmes pour un fournisseur à 4 jours et pour un import à 90 jours. Le statut qui décide —
     Cockpit, plan d'achat, courriel du lundi, quantités à commander — compare le stock projeté à son seuil
     d'alerte (sécurité de sa classe ABC, couverture minimum et stock minimum du catalogue, réglés dans
     Approvisionnement) : CRITIQUE sous la moitié du seuil, URGENT sous le seuil, ATTENTION jusqu'à 120 %. Le
     stock dormant compte les jours sans sortie ni entrée. »
  2. « Approvisionnement » — « La fenêtre de réapprovisionnement et les marges appliquées au calcul des
     quantités à commander : délai, couverture d'une commande, sécurité par classe, pertes, croissance du
     plan. La sécurité par classe et le stock minimum font le seuil d'alerte, qui décide du statut. »
  3. « Classification ABC / XYZ » — « ABC classe les matières par valeur consommée : A pour l'essentiel de la
     dépense, puis B, puis C. XYZ les classe par régularité de la demande mensuelle, mesurée par le
     coefficient de variation (CV = écart-type ÷ moyenne) : X régulière, Y variable, Z erratique. »
  4. « Politique d'achat » — « Les montants qui classent un bon de commande (groupé ou standard), les tiers de
     priorité du plan d'achat, et le seuil au-delà duquel la direction approuve une commande avant l'envoi.
     L'urgence ne vient jamais du montant : un fournisseur est « urgent » quand une de ses matières est en
     rupture, critique ou urgente ; une ligne CRITIQUE est en Tier 1, une ligne URGENTE en Tier 2 au moins —
     les montants ne font que remonter les autres. »
  5. « Réceptions et fournisseurs » — « Les tolérances de réception (pesée, poids de bobine, livraison
     complète) et la notation des fournisseurs : OTIF = à l'heure × complète × conforme, et les scores qui
     classent. »
  6. « Stock et inventaire » — (aucune phrase).
  7. « Prix » — « Ce qui colore la matrice des prix (forte hausse), borne la comparaison des opportunités
     (deux prix de la même époque) et calcule la TVA attendue d'un dossier d'importation. »
  8. « Trésorerie » — « Le délai client moyen entre dans le cycle de trésorerie du Cockpit (stock + clients −
     fournisseurs). »
  9. « Société » — « Ce qui s'imprime sur les bons de commande, la période close (rien ne s'écrit plus avant)
     et l'adresse que portent les QR des étiquettes. »
  10. « Méthode de calcul » (famille d'écran, sans champ) — texte : « Gestion MP calcule toujours avec la
      **méthode corrigée** de l'ERP Fil : les sept corrections apportées au classeur après son audit. Le mode
      « classeur », qui reproduisait le tableur à l'identique pour comparer, n'existe plus — il n'y a donc rien
      à régler ici. » + liste : (1) « Le seuil d'alerte tient compte du délai du fournisseur : on commande à
      temps pour être livré avant la rupture. » (2) « Une seule devise par matière : celle de son prix ; les
      montants ne s'additionnent jamais entre devises. » (3) « Le taux de perte entre dans le besoin et dans le
      coût matière. » (4) « Le plan d'achat se trie en dirhams, pondéré par la classe ABC (× 3 en A, × 2 en
      B). » (5) « Le mois en cours est compté au prorata des jours qui restent. » (6) « Seules les commandes
      attendues dans le délai comptent dans le stock projeté. » (7) « Les quantités à commander sont arrondies
      au conditionnement (palette, fût, sac…) et au minimum de commande. »
- **Un champ** = `Champ` libellé (infobulle « {libellé} ({unité})[ — modifié, pas encore enregistré] ») ;
  aide sous le champ = « {aide serveur ou aide d'écran} · entre {bas} et {haut} {unité} · par défaut : {défaut
  lisible}[ · avant : {valeur enregistrée}] » ; numérique : `ChampNombre` (séparateurs hors saisie, molette
  neutralisée, % saisi en pourcent) + unité à droite ; texte : `input` (type date pour « Période close
  jusqu'au »). Champ modifié : bordure accent + libellé coloré ; hors bornes : bordure rouge.
- **Tous les paramètres (55)** — unité affichée ; défaut affiché (× échelle) ; bornes ; effet :

| Famille | Clé | Libellé exact | Unité | Défaut | Bornes | Effet / aide affichée |
|---|---|---|---|---|---|---|
| Couverture | seuil_critique | « Couverture critique » | jours | 60 | 1–3650 | « Statut classeur seulement, pour comparaison : sous cette couverture, une matière y est « critique ». Le statut du Cockpit, du plan d'achat et du courriel compare le stock projeté au seuil d'alerte. » |
| Couverture | seuil_alerte | « Couverture d'attention » | jours | 90 | 1–3650 | « Statut classeur seulement, pour comparaison : sous cette couverture, une matière y est en ATTENTION. » |
| Couverture | seuil_dormant | « Stock dormant » | jours | 180 | 1–3650 | « Sans sortie ni entrée depuis ce nombre de jours, un stock détenu dort. » (C18) |
| Appro | delai_defaut | « Délai par défaut » | jours | 60 | 1–730 | « Délai pris pour une matière sans fournisseur (ou d'un fournisseur inconnu) ; un fournisseur a toujours son propre délai, saisi dans sa fiche. » |
| Appro | marge_jours | « Couverture de commande » | jours | 30 | 0–730 | « Ce qu'une commande couvre, à défaut du pas du fournisseur. » |
| Appro | marge_securite | « Marge de sécurité » | % | 20 % | 0–500 % | (écran) « Majore la couverture minimum que porte la fiche d'une matière (en mois) : à 20 %, une couverture minimum de 2 mois en demande 2,4. Elle entre dans le seuil d'alerte, qui est le plus grand du stock minimum, de cette couverture et de la sécurité de la classe. Sans couverture minimum dans la fiche, elle ne change rien. » |
| Appro | taux_perte | « Taux de perte matière » | % | 2 % | 0–50 % | « Ajouté aux besoins et au coût de la matière. » (prévu des ordres perte comprise) |
| Appro | securite_a | « Sécurité classe A » | jours | 30 | 0–365 | (écran) « Jours de consommation à venir gardés en sécurité pour une matière de classe A. Le seuil d'alerte est le plus grand de cette sécurité, du stock minimum et de la couverture minimum : elle ne s'y ajoute pas. » |
| Appro | securite_b | « Sécurité classe B » | jours | 30 | 0–365 | (écran) « Jours de sécurité pour une matière de classe B (le seuil d'alerte en prend le plus grand, comme pour A). » |
| Appro | securite_c | « Sécurité classe C » | jours | 30 | 0–365 | (écran) idem classe C |
| Appro | fenetre_realisation_jours | « Prévision — fenêtre du réalisé » | jours | 90 | 0–730 | « Sorties réelles comparées au plan, par mois entiers clos (les jours ramenés en mois au plus près, un demi arrondi au-dessus : 75 j = 3 mois). 0 = plan seul. » |
| Appro | plafond_stock_min_mois | « Stock minimum — plafond » | mois | 3 | 0–60 | « Le stock minimum du catalogue ne vaut pas plus de N mois de la consommation à venir (celle de l'horizon de commande). 0 = pas de plafond : le stock minimum du catalogue vaut tel quel. Une matière non consommée n'en a aucun. » (C33) |
| Appro | croissance_annuelle | « Croissance annuelle du plan » | % | 0 % | −90 %–1000 % | (écran) « Ajoutée au plan de production à partir du jour où la base a été saisie : à 5 %, une base saisie en janvier vaut 5 % de plus en janvier suivant. Un mois garde la même prévision, qu'on le regarde six mois avant ou le mois même. » |
| ABC/XYZ | seuil_abc_a | « Classe A — valeur cumulée » | % | 80 % | 0–100 % | (écran) « Les matières qui font ensemble cette part de la valeur consommée sont en classe A. » |
| ABC/XYZ | seuil_abc_b | « Classe B — valeur cumulée » | % | 95 % | 0–100 % | (écran) « Jusqu'à cette part cumulée, classe B ; au-delà, classe C. » |
| ABC/XYZ | seuil_xyz_x | « Classe X — CV maximum » | (aucune) | 0,25 | 0–10 | (écran) « Sous ce coefficient de variation (écart-type ÷ moyenne mensuelle), la demande est régulière : classe X. » |
| ABC/XYZ | seuil_xyz_y | « Classe Y — CV maximum » | (aucune) | 0,5 | 0–10 | (écran) « Sous ce coefficient de variation, la demande est variable : classe Y. Au-delà, erratique : classe Z. » |
| Achat | seuil_bc_urgent | « BC urgent » | MAD | 300 000 | 0–1e12 | (écran) « Ne sert plus qu'à la méthode du classeur (comparaison). Au plan d'achat, un fournisseur est « urgent » quand une de ses matières est en rupture, critique ou urgente — pas pour le montant de sa commande. » |
| Achat | seuil_bc_groupe | « BC groupé » | MAD | 100 000 | 0–1e12 | (écran) « Au plan d'achat, ce qu'il faut commander à un fournisseur sans urgence, à partir de ce montant, se passe en un bon groupé ; en deçà, c'est un bon standard. » |
| Achat | seuil_tier1 | « Tier 1 (classe A) » | MAD | 300 000 | 0–1e12 | (écran) « Une matière de classe A dont la commande atteint ce montant passe en Tier 1 (émettre cette semaine), comme toute rupture ou matière CRITIQUE. » |
| Achat | seuil_tier2 | « Tier 2 » | MAD | 200 000 | 0–1e12 | (écran) « À partir de ce montant, Tier 2 (sous 7 jours). Une matière URGENTE y est de toute façon, quel que soit son montant. » |
| Achat | seuil_tier3 | « Tier 3 » | MAD | 100 000 | 0–1e12 | (écran) « À partir de ce montant, Tier 3 (sous 15 jours) ; en deçà, Tier 4 (regrouper sous 30 jours) — sauf urgence. » |
| Achat | seuil_approbation | « Approbation des commandes au-delà de » | MAD | 0 | 0–1e12 | « Une commande plus chère attend l'approbation de la direction. 0 = jamais. » |
| Réception | toler_in_full | « Tolérance de livraison complète » | % | 2 % | 0–20 % | « Une ligne reçue à cette part près de la quantité commandée compte comme livrée en entier (elle n'attend plus rien). Au plus 20 % : au-delà, un bon à peine entamé passerait pour livré. » |
| Réception | toler_ecart_pesee | « Tolérance d'écart de pesée » | % | 2 % | 0–100 % | (écran) « Un écart entre la pesée et le bon de livraison au-delà de ce taux est signalé (contrôle C08). Sans bon de livraison, une pesée franchement sous le reste à livrer est une livraison partielle, pas un écart. » |
| Réception | toler_excedent | « Excédent de livraison toléré » | % | 10 % | 0–1000 % | « Une ligne de bon reçoit au plus son reste à livrer plus cette part de la ligne ; au-delà, la réception est refusée (le surplus se reçoit hors commande). » |
| Réception | toler_poids_bobine | « Tolérance du poids de bobine » | % | 5 % | 0–100 % | (écran) « Un poids de bobine reçu éloigné du catalogue de plus de ce taux est signalé (contrôle C30). » |
| Réception | toler_retard_jours | « Retard toléré dans la ponctualité » | jours | 0 | 0–60 | « Une livraison en retard de N jours ou moins reste « à l'heure ». » (C06, écran des commandes, courriel) |
| Réception | cible_otif | « Cible OTIF » | % | 95 % | 0–100 % | (écran) « Sous cette part de livraisons parfaites, un fournisseur est signalé « sous la cible ». » |
| Réception | score_strategique | « Score — Stratégique » | /100 | 85 | 0–100 | classement Stratégique |
| Réception | score_standard | « Score — Standard » | /100 | 65 | 0–100 | classement Standard |
| Réception | score_surveiller | « Score — ATTENTION » | /100 | 45 | 0–100 | classement ATTENTION (« À surveiller ») ; en deçà « À challenger » |
| Stock et inventaire | tolerance_inventaire | « Tolérance d'écart d'inventaire » | % | 2 % | 0–100 % | « Proposée à l'ouverture d'un inventaire : au-delà, un écart de comptage se justifie avant la validation. » |
| Prix | seuil_hausse_forte | « Forte hausse de prix à partir de » | % | 5 % | 0,5 %–1000 % | colore la matrice, compte les fortes hausses, seuil « forte » des opportunités |
| Prix | fenetre_prix_jours | « Écart maximal entre deux prix comparés » | jours | 90 | 1–3650 | « Deux prix ne se comparent qu'à la même époque. » |
| Prix | taux_tva_import | « TVA à l'importation » | % | 20 % | 0–100 % | (écran) « Le taux appliqué à la valeur en douane (marchandise, fret, assurance) augmentée des droits et de la TPI, pour la TVA attendue d'un dossier (contrôle C29). » |
| Prix | taux_tpi_import | « Taxe parafiscale à l'importation (TPI) » | % | 0,25 % | 0–10 % | « Sur la valeur en douane ; elle entre dans la base de la TVA attendue. » |
| Prix | seuil_surcout_import | « Frais d'un dossier d'importation à vérifier au-delà de » | % | 100 % | 5 %–10 000 % | « Des frais hors TVA plus lourds que cette part de la marchandise sont signalés sur le dossier et dans les contrôles : ils fausseraient le coût moyen du stock. » (C35) |
| Prix | toler_facture_import | « Facture d'un dossier à rapprocher au-delà de » | % | 2 % | 0–100 % | « Une facture qui s'éloigne de plus de cette part de la marchandise reçue (pesée × prix) est signalée sur le dossier et dans les contrôles. » (C36) |
| Trésorerie | dso | « Délai client moyen (DSO) » | jours | 60 | 0–3650 | cycle de trésorerie du Cockpit |
| Société | nom_entreprise | « Raison sociale » | texte | (vide) | ≤ 500 car. | en-tête des bons, écran de connexion, bilan du mois, courriel |
| Société | forme_juridique | « Forme juridique et capital » | texte | | | « Sous la raison sociale, en tête des bons : « SOCIETE ANONYME AU CAPITAL DE 20 000 000 DH ». » |
| Société | secteur | « Secteur » | texte | « Fabrication de tapis mécaniques » | | « L'activité de l'usine (fiche de la société) ; l'en-tête des bons suit le papier à en-tête : raison sociale, forme et capital, siège, ville. » |
| Société | adresse | « Siège social » | texte | | | « En tête des bons (« SIEGE SOCIAL … ») et adresse de livraison. » |
| Société | ville | « Ville » | texte | | | |
| Société | telephone | « Téléphone » | texte | | | |
| Société | banques | « Banques » | texte | | | « En pied des bons, par exemple « ATTWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 001 82 » (séparer les banques par « · »). » |
| Société | ice | « ICE » | texte | | | |
| Société | rc | « R.C » | texte | | | |
| Société | identifiant_fiscal | « N.I.F (identifiant fiscal) » | texte | | | |
| Société | cnss | « C.N.S.S » | texte | | | |
| Société | patente | « Patente » | texte | | | |
| Société | date_cloture | « Période close jusqu'au » | date | (vide) | passée | « Rien ne s'écrit plus à cette date ni avant. » — **clôture de période** (voir §2.12) |
| Société | courriel_destinataires | « Courriel du lundi : à qui » | texte | | | « Adresses séparées par des virgules. Vide : pas de courriel. Il part le lundi matin, dès que le serveur d'envoi est réglé (voir la notice). » |
| Société | adresse_publique | « Adresse du serveur pour les téléphones » | texte | | http(s)://, ≤ 200, sans espace | « Ce que contiennent les QR des étiquettes, par exemple http://mac-usine:8030 (nom Tailscale, qui marche en Wi-Fi comme en 4G/5G). Vide : l'adresse du serveur sur le réseau de l'usine. » |

- **Contrôles faits à l'écran avant l'envoi** (`ReglagesParametres.tsx:146-163`) : hors bornes →
  « « {libellé} » doit rester entre {bas} et {haut} {unité}. » ; ordres (`ORDRES`) : « La couverture critique
  doit rester inférieure à la couverture d'ATTENTION. » ; « La part cumulée de la classe A doit rester sous
  celle de la classe B. » ; « Le CV maximum de la classe X doit rester sous celui de la classe Y. » ; « Le score
  « ATTENTION » doit rester sous le score « standard ». » ; « Le score « standard » doit rester sous le score
  « stratégique ». » — affichés en message d'erreur au-dessus et en infobulle du bouton grisé.
- **Refus serveur** (`comptes.py:292-352`) : « Paramètres inconnus : {clés}. » ; « « {libellé} » attend un
  nombre. » ; « « {libellé} » doit rester entre {bas} et {haut} {unité} — reçu {x}. » ; date de clôture :
  « On ne clôt qu'une période passée. » / « Date de clôture illisible (AAAA-MM-JJ). » ; adresse publique :
  « L'adresse commence par http:// ou https:// (ex. http://mac-usine:8030). » ; texte > 500 : « « {libellé} » :
  texte trop long. » ; ordres (rollback) : « La couverture critique doit rester inférieure à la couverture
  d'ATTENTION : sinon plus aucune matière ne serait en ATTENTION. » + les quatre autres phrases identiques à
  l'écran. Chaque changement réel : historique (`ParametreHistorique`) + journal « paramètre », détail
  « {libellé} : {avant} → {après} » (valeurs lisibles « 20 % », « 9,5 »).
- **Gestes** :

| Geste | Où | Conditions / grisé | Appel | Succès | Remarques |
|---|---|---|---|---|---|
| choisir une famille | liste de gauche | | | | garde le brouillon des autres familles |
| « Historique des changements » | en-tête carte | toujours | `GET /parametres/historique` (DIRECTION) | ouvre la fenêtre | |
| « Annuler » | en-tête | visible si ≥ 1 modification | | vide le brouillon | sans confirmation |
| « Enregistrer {n} modification(s) » / « Aucune modification » / « Enregistrement… » (principal) | en-tête | grisé si envoi, aucune modif, ou refus (infobulle = textes des refus) | `PUT /parametres` (corps = clé → valeur) | « {n} paramètre(s) enregistré(s) : tout le pilotage est recalculé. » ; invalide **toutes** les requêtes | pas de confirmation, même pour la clôture |

- **Fenêtre « Historique des paramètres et des cours de change »** (`Dialogue large`) : note « Les 500
  derniers changements, le plus récent d'abord. » ; recherche « Paramètre, personne… » (libellé, clé, valeur,
  par) ; tableau « Quand » (horodatage) · « Paramètre » (libellé, ou « Cours {XXX} → MAD » pour un cours) ·
  « Avant » (valeur lisible, défaut pour le 1er changement, « — » pour un 1er cours) · « Nouvelle valeur » ·
  « Par » ; vide « Aucun changement. ».

---

#### 2.2 Onglet Devises — `?onglet=devises` (direction **et achats**)

- **Fichier** : `components/direction/ReglagesDevises.tsx` (219 l.) ; serveur `comptes.py:393-446`.
- **Rôles** : `GET /devises`, `GET /devises/{code}/historique` : toute session ; `PUT /devises` : ACHATS
  (achats + direction).
- **Carte « Cours de change »** : note « Le cours dit combien de dirhams vaut une unité de la devise (1 EUR =
  10,8 MAD, par exemple). Il sert à comparer et valoriser tout ce qui s'achète en devises. Le dirham reste à 1.
  Chaque nouveau cours est daté et gardé : une commande garde le cours figé à la confirmation de ses prix, un
  dossier d'importation celui de la banque. » ; tableau de saisie (`table.saisie`, tri par code) :

| Colonne | Contenu |
|---|---|
| « Code » | **code** |
| « Nom » | champ texte éditable |
| « Cours (MAD) » (170 px) | `ChampNombre` ; grisé pour MAD |
| « Depuis le » | « référence » (MAD) / horodatage du dernier cours saisi / note « cours de la reprise » (infobulle « Aucun changement depuis la mise en service : c'est le cours repris ») |
| « Utilisée » | case « active » (grisée pour MAD) |
| (actions) | « Historique » (ligne non modifiée, hors MAD ; infobulle « Les cours successifs de cette devise, qui les a saisis et quand ») ; ligne modifiée : « Enregistrer » (grisé si cours ≤ 0) + « Annuler » |

  Vide : « Aucune devise. ».
- **Carte « Ajouter une devise »** : « Code (3 lettres) » (aide « GBP, CNY, TRY… », majuscules, 3 car. max) ;
  « Nom » ; « Cours en dirhams » ; bouton « Ajouter la devise » grisé si code ≠ 3 lettres, cours ≤ 0 ou code
  déjà existant (sans infobulle).
- **Gestes** :

| Geste | Rôle | Appel | Succès | Refus serveur |
|---|---|---|---|---|
| « Enregistrer » (ligne) | dir., achats | `PUT /devises {code, nom, taux, actif}` | « Cours {CODE} enregistré : {cours 4 déc.} MAD. » ; invalide toutes les requêtes | « Le dirham est la devise de référence : son cours reste 1. » ; validation « taux : … » (> 0, ≤ 10 000), « code : … » (3 car.) ; 403 droit |
| « Annuler » (ligne) | | | retire la ligne du brouillon | |
| « Historique » | | `GET /devises/{code}/historique` | fenêtre | |
| « Ajouter la devise » | dir., achats | `PUT /devises` (création si code inconnu) | « Devise {CODE} ajoutée. » ; formulaire vidé | idem |

  Serveur : chaque enregistrement (même un simple renommage ou (dés)activation) écrit un historique
  « cours_{CODE} » et le journal « cours de change », détail « {CODE} : {cours} MAD ».
- **Fenêtre « Les cours du {nom ou code} ({CODE} → MAD) »** (`Dialogue large`) : « Saisi le » · « Cours (MAD) »
  (4 déc.) · « Variation » (« +x,xx % » face au cours précédent) · « Par » ; vide « Aucun cours saisi depuis la
  mise en service. » ; note « Le plus récent d'abord. Le cours en vigueur est le premier de la liste. ».

---

#### 2.3 Onglet Magasins — `?onglet=magasins`

- **Fichier** : `components/direction/ReglagesMagasins.tsx` (156 l.) ; serveur `referentiels.py:1050-1108`.
- **Rôles** : direction (onglet) ; `GET /magasins` toute session ; `POST`/`PUT` DIRECTION.
- **Carte « Les magasins »** + bouton « Nouveau magasin » ; note « « Stock courant » : la matière disponible
  pour les machines. « Quarantaine » : la matière reçue sous réserve, qui attend une décision avant de servir
  (ni proposée aux machines, ni comptée dans la couverture). Le contenu dit ce qu'on y range. Cliquer sur un
  magasin pour le modifier. »
- **Tableau** (tri serveur par type puis code — la quarantaine d'abord ; ligne cliquable → fiche) :
  « Code » (gras) · « Nom » · « Type » (étiquette attention pour Quarantaine, neutre sinon) · « Contenu » (ou
  note « Tout ») · « Stock détenu (kg) » (Σ soldes) · « État » (actif / désactivé). Vide « Aucun magasin. ».
- **Fenêtre « Magasin {code} » / « Nouveau magasin »** (`Dialogue`, `sale`) : « Code » (texte, obligatoire,
  ≤ 64) ; « Nom » ; « Type » (« Stock courant » / « Quarantaine », grisé si le magasin détient > 0,001 kg,
  aide « il détient de la matière : son type ne change plus ») ; « Contenu » (≤ 120, suggestions : Tout, Fils,
  Fils PP, Fils PES, Chaîne et trame, Colles et intrants, Franges et cuir ; aide « ce qu'on y range : « Tout »,
  « Fils PP », « Colles et intrants »… ; vide = Tout ») ; case « magasin actif ». Message si on décoche un
  magasin qui détient : « Ce magasin détient encore {n} kg : transférer la matière avant de le désactiver. »
- **Gestes** : « Nouveau magasin » ; clic ligne ; « Annuler » ; « Enregistrer » / « Créer le magasin » /
  « Enregistrement… » (grisé si code vide) → `PUT /magasins/{id}` ou `POST /magasins` ; succès : fenêtre fermée,
  liste rafraîchie (pas de message). Refus : « Type de magasin : « Stock courant » ou « Quarantaine ». » ; « Le
  magasin « X » existe déjà. » (409) ; « « X » détient encore {n} kg : transférer le stock avant de désactiver
  le magasin. » (409) ; « Un magasin qui détient de la matière ne change pas de type. » (409) ; « Magasin
  introuvable. » (404). Journal : « création magasin » / « modification magasin ».

---

#### 2.4 Onglet Postes de frais — `?onglet=postes`

- **Fichier** : `components/importations/ReglagesPostesFrais.tsx` (210 l.) ; serveur
  `referentiels_import.py:37-211`.
- **Rôles** : `GET /postes-frais/complet` ACHATS ; `POST`/`PUT`/`DELETE /postes-frais` DIRECTION.
- **Carte « Postes de frais d'importation »** + « Nouveau poste » ; note « Un frais global d'un dossier se
  répartit entre ses marchandises **à la valeur** (au prorata de ce que vaut chaque marchandise) ou **au
  poids** (au prorata de ses kilos), selon le réglage de son poste. Un poste récupérable (la TVA) reste hors du
  coût. Changer une clé recalcule les dossiers ouverts ; les dossiers clos gardent leur répartition. Cliquer
  sur un poste pour le modifier. »
- **Tableau** (tri ordre, code ; ligne cliquable, infobulle « Modifier le poste ») : « Ordre » · « Code »
  (+ étiquette « calculs » pour DD, TPI, TVA, FRET, ASSUR, infobulle « Lu par les calculs du dossier (TVA
  attendue) : il ne se supprime pas et garde sa nature ») · « Libellé » · « Répartition » (« à la valeur » /
  « au poids » accent ; « — » si récupérable) · « Nature » (« récupérable, hors coût » attention / « coût ») ·
  « Frais saisis » · « Dossiers ouverts » · « Dossiers clos ».
- **Fenêtre « Poste {code} — {libellé} » / « Nouveau poste de frais »** (`sale`) : « Code » (≤ 16,
  majuscules, figé en modification ; aides « le code ne change pas : les frais le portent » / « lettres,
  chiffres ou « _ » (ex. MANUT) ») ; « Libellé » (≤ 80) ; « Répartition » (« à la valeur » / « au poids »,
  aide « au prorata de la valeur de chaque marchandise, ou de ses kilos ») ; « Ordre » (0–999, aide « place
  dans les listes ; vide : à la fin ») ; case « récupérable : hors du coût (comme la TVA) » grisée si poste
  système ou s'il porte des frais dans un dossier clos (note « Nature figée : les calculs du dossier lisent ce
  poste ainsi. » / « … il porte des frais dans {n} dossier(s) clos : créer un autre poste. ») ; message si la
  clé change : « Les {n} dossier(s) ouvert(s) seront recalculés {à la valeur|au poids}.[ Les {n} dossier(s)
  clos gardent leur coût : leurs frais de ce poste seront éclatés sur leurs marchandises, {ancienne clé}
  (c'est tracé).] ».
- **Gestes** : « Supprimer » (danger, `Confirmer` « Supprimer ce poste ? · Non · Oui, supprimer » ; grisé avec
  infobulle « Ce poste sert aux calculs du dossier : il ne se supprime pas » / « Ce poste porte {n} frais dans
  des dossiers : il ne se supprime pas » ; sinon infobulle « Supprimer ce poste, qui ne porte aucun frais »)
  → `DELETE /postes-frais/{code}` ; « Annuler » ; « Enregistrer » / « Créer le poste » (grisé si libellé ou
  code vide, ou rien modifié) → `PUT /postes-frais/{code}` / `POST /postes-frais`. Succès : fermeture et
  rafraîchissement (pas de message). Refus : « Le code d'un poste : lettres, chiffres ou « _ », sans espace
  (ex. MANUT). » ; « Le poste « X » existe déjà. » (409) ; « « {libellé} » est {récupérable|un coût} par
  nature : les calculs du dossier (TVA attendue) le lisent ainsi. » (409) ; « Ce poste porte des frais dans {n}
  dossier(s) clos : changer sa nature changerait leur coût. Créer un autre poste. » (409) ; refus de période
  close (`cout_hors_periode_close`, geste « changement du poste « … » ») ; « « {libellé} » sert aux calculs du
  dossier : il ne se supprime pas. » (409) ; « Ce poste porte des frais dans des dossiers : il ne se supprime
  pas. » (409) ; « Poste de frais introuvable. » (404) ; « libellé : … le libellé est obligatoire ».
  Changement de clé : les frais globaux des dossiers clos sont **figés** à l'ancienne clé (journal « frais
  figés »).

---

#### 2.5 Onglet Codes douaniers — `?onglet=codes`

- **Fichier** : `components/importations/ReglagesCodesDouaniers.tsx` (171 l.) ; serveur
  `referentiels_import.py:214-278`.
- **Rôles** : `GET /codes-douaniers` ACHATS ; écritures DIRECTION.
- **Carte « Codes douaniers »** + « Nouveau code » ; note « La position du tarif douanier et son taux de
  droits. Chaque matière porte son code (fiche matière, au catalogue) : un dossier d'importation en déduit les
  droits attendus — taux × valeur en douane (achat + fret) — et signale l'écart avec la quittance. » ;
  recherche « Code, libellé… » + note « {n} code(s) ».
- **Tableau** (ligne cliquable « Modifier le code ») : « Code » · « Libellé » · « Taux de droits » (%) ·
  « Matières » (nb de matières qui le portent) · « État ». Vide : « Aucun code ne correspond. » / « Aucun code
  douanier. « Nouveau code » : 5402.47.00.00 (fils de polypropylène), son taux de droits… ».
- **Fenêtre « Code douanier {code} » / « Nouveau code douanier »** (`sale`) : « Code » (≤ 20 ; aide « {n}
  matière(s) le portent : elles suivront la correction » ou « chiffres et points (ex. 5402.47.00.00) ») ;
  « Libellé » (≤ 160, placeholder « Fils de polypropylène… ») ; « Taux de droits (%) » (aide « sur la valeur
  en douane : achat + fret ») ; case « code actif (proposé dans la fiche matière) » ; message « Un taux de
  droits va de 0 à 100 %. ».
- **Gestes** : « Supprimer » (`Confirmer` « Supprimer ce code ? · Non · Oui, supprimer », grisé si des
  matières le portent, infobulle « {n} matière(s) portent ce code : le leur retirer, ou le désactiver » /
  « Supprimer ce code, qu'aucune matière ne porte ») ; « Annuler » ; « Enregistrer » / « Créer le code »
  (grisé si code vide, taux absent ou hors 0–100 %, ou rien modifié). Refus : « code : … un code douanier
  s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00) » ; « Le code douanier « X » existe
  déjà. » (409) ; « Code douanier introuvable. » (404) ; « {n} matière(s) portent ce code : le leur retirer
  d'abord, ou le désactiver. » (409).

---

#### 2.6 Onglet Comptes — `?onglet=comptes`

- **Fichier** : `components/direction/ReglagesComptes.tsx` (263 l.) ; serveur `comptes.py:155-210`.
- **Rôles** : DIRECTION pour `GET/POST /utilisateurs` et `PUT /utilisateurs/{id}`.
- **Carte « Les comptes »** ; extra : recherche « Nom, identifiant, rôle… » (nom, identifiant, rôle,
  courriel) + « Nouveau compte » (principal) ; note « Chacun a son compte : tout ce qui s'enregistre porte son
  nom. Un compte désactivé ne se connecte plus, et ses sessions ouvertes sont fermées. Cliquer sur un compte pour
  le modifier ou lui remettre un code. »
- **Tableau** (tri serveur par nom ; ligne cliquable) : « Nom » (gras) · « Identifiant » (mono) · « Rôle »
  (« Direction » / « Responsable achats » / « Responsable alimentation machines ») · « Courriel » (ou « — ») ·
  « Dernière activité » (horodatage ou note « jamais connecté ») · « État » (« actif » ok / « désactivé »
  neutre). Vide : « Aucun compte ne correspond. ». Message de succès sous le tableau.
- **Fenêtre « Compte de {nom} » / « Nouveau compte »** (`Dialogue large`, `sale` dès qu'un champ change) :
  - « Nom affiché » (aide « tel qu'il apparaît à la connexion et dans le journal ») ;
  - « Identifiant » (mono ; minuscules, espaces retirés à la frappe ; figé en modification, aide
    « l'identifiant ne change pas » ; création : « en minuscules, sans espace : il sera « {x} » » ou « en
    minuscules, sans espace (ex. : sara) — les espaces tapés sont retirés ») ;
  - « Rôle » (Direction — « voit et peut tout : approbations, réglages, comptes, sauvegardes » ; Responsable
    achats — « commandes, réceptions, inventaire, importations, matières » ; Responsable alimentation machines
    — « sorties vers les métiers, au téléphone ») ; grisé pour son propre compte ; défaut « achats » ;
  - « Courriel (facultatif) » (type email) ;
  - « Code » (création, ou passage de l'alimentation à un autre rôle) / « Nouveau code (laisser vide pour le
    garder) » ; aide « 4 chiffres au moins (saisi au téléphone) » (alimentation, clavier numérique) ou « 8
    caractères au moins » ; en changement de rôle : « nouveau rôle : un nouveau code est nécessaire, … » ;
  - « Retaper le code » (aide « les deux saisies diffèrent ») ;
  - case « compte actif dès maintenant » (création seulement, défaut cochée).
  Messages : « C'est votre compte : vous ne pouvez ni changer votre rôle ni vous désactiver. » ; « Ce compte est
  désactivé : il ne peut plus se connecter. ».
- **Gestes** :

| Geste | Conditions | Confirmation | Appel | Succès | Refus serveur |
|---|---|---|---|---|---|
| « Nouveau compte » | | | | ouvre la fiche | |
| « Désactiver le compte » (danger) | compte existant actif, pas soi-même ; infobulle « Le compte ne pourra plus se connecter et ses sessions ouvertes sont fermées ; il se réactive plus tard » | « Désactiver {nom} ? · Non · Oui, désactiver » | `PUT /utilisateurs/{id}` (actif false + champs du formulaire) | « Compte de {nom} désactivé : ses sessions sont fermées. » | « Vous ne pouvez pas retirer vos propres droits de direction. » (409) |
| « Réactiver le compte » | compte désactivé, pas soi | | `PUT` (actif true) | « Compte de {nom} réactivé. » | |
| « Annuler » | | (ferme sans demander) | | | |
| « Créer le compte » / « Enregistrer » / « Enregistrer et remettre le code » / « Enregistrement… » | grisé si nom < 2, identifiant < 2, code trop court (infobulle « Le code doit faire au moins {n} caractères »), codes différents | | `POST /utilisateurs` ou `PUT /utilisateurs/{id}` | « Compte créé : {nom} (identifiant « {id} »). » / « Compte de {nom} enregistré, nouveau code remis. » / « Compte de {nom} enregistré. » | « Rôle inconnu. » ; « L'identifiant « x » est déjà pris. » (409) ; « Le code doit faire au moins {4|8} caractères. » ; « Compte introuvable. » (404) ; validation nom/identifiant trop courts |

  Journal : « création de compte » / « modification de compte » (« {nom} ({rôle}) »). Désactiver supprime
  les sessions ouvertes.

---

#### 2.7 Onglet Sauvegardes — `?onglet=sauvegardes`

- **Fichiers** : `components/direction/ReglagesSauvegardes.tsx` (247 l.) ; `comptes.py:449-580` ;
  `gestion_mp/services/sauvegarde.py`.
- **Rôles** : DIRECTION (`GET/POST /sauvegardes`, `POST /sauvegardes/{nom}/restaurer`).
- **Règles serveur** : `pg_dump -Fc`, relue par `pg_restore --list` (au moins une « TABLE DATA ») avant
  d'être déclarée bonne ; quotidienne `gestion-mp-AAAA-MM-JJ.dump`, manuelle
  `gestion-mp-AAAA-MM-JJ-HHMMSS-manuelle.dump`, `…-avant-restauration.dump` ; pièces jointes copiées en miroir
  ; copie de sécurité si `GESTION_MP_SAUVEGARDES_COPIE` ; purge : 14 dernières quotidiennes + 1re de chaque mois
  sur 12 mois, manuelles et avant-restauration jamais effacées. Alerte : « Les sauvegardes sont arrêtées :
  pg_dump est introuvable sur le serveur. » / « La sauvegarde automatique a échoué : … » / « Aucune
  sauvegarde récente. » (> 26 h) / « Aucune sauvegarde de la base « {base} » : le dossier ne contient que
  d'autres bases. ». Fichiers d'**autres bases** (lu dans l'en-tête dbname) listés mais non comptés.
- **Indicateurs** : « Dernière sauvegarde » (horodatage ou « aucune » ; « il y a {40 min | 3 h | 2 jours} » ;
  critique si alerte ou > 26 h) ; « Sauvegardes conservées » (nb de cette base ; « 14 jours, puis une par mois
  sur 12 mois » ; infobulle « Une sauvegarde automatique par jour, gardée 14 jours ; puis la première de chaque
  mois, gardée 12 mois. Les sauvegardes manuelles et « avant restauration » ne s'effacent jamais seules. ») ;
  « Copie de sécurité » (Oui/Non ; chemin ou « aucun second emplacement réglé sur le serveur »).
- **Carte « Les sauvegardes »** + « Sauvegarder maintenant » ; note : « La base est sauvegardée chaque jour
  sur le serveur, dans {dossier}[, et recopiée dans {copie}]. **Conservation :** une sauvegarde automatique par
  jour, gardée 14 jours ; puis la première de chaque mois, gardée 12 mois. Les sauvegardes manuelles et « avant
  restauration » ne s'effacent jamais seules. Avant une opération délicate, faire une sauvegarde manuelle.
  Restaurer remplace toute la base, pour tous les postes, par l'état de la sauvegarde choisie — l'état actuel est
  d'abord sauvegardé : la restauration se défait. »
- **Tableau** (30 au plus, tri date décroissante) : « Faite le » · « Nature » (étiquette « automatique » neutre
  / « manuelle » / « avant une restauration » accent, lue dans le nom) · « Fichier » (mono) · « Base » (note
  « cette base » ou étiquette attention avec le nom d'une autre base) · « Taille » (Ko/Mo) · « Restaurer… ».
  Vide : « Aucune sauvegarde pour le moment. ». Notes : « {n} fichier(s) du dossier sont des sauvegardes
  d'autres bases (essais, démonstrations) : ils ne comptent pas pour celle-ci et ne s'y restaurent pas. » ;
  « Les {n} plus récentes sont listées, sur {nb}. ».
- **Fenêtre « Restaurer la sauvegarde du {date} »** (`Dialogue`, non fermable pendant l'envoi), 2 étapes :
  1. Message erreur « Tout ce qui a été saisi depuis le {date} — réceptions, sorties, commandes, réglages —
     disparaîtra de la base, pour tous les postes. » ; puces « L'état actuel est d'abord sauvegardé (« avant
     restauration ») : on pourra y revenir. » / « Prévenir les autres utilisateurs : ce qu'ils sont en train de
     saisir sera perdu. » / « L'opération peut prendre quelques minutes ; ne pas fermer la fenêtre. » ; case
     « J'ai compris : la base va revenir en arrière. » ; « Annuler » / « Continuer » (danger, grisé sans la
     case).
  2. « Dernière confirmation : taper **RESTAURER** pour remplacer la base par la sauvegarde {fichier}. » ;
     champ « Taper RESTAURER » (casse indifférente) ; « Annuler » / « Restaurer maintenant » (« Restauration en
     cours… »).
  Succès : « La base est revenue à l'état du {date}. Les autres postes doivent rouvrir leur écran ; si la session
  est perdue, se reconnecter. » + « Fermer ».
- **Gestes** :

| Geste | Conditions | Confirmation | Appel | Succès | Refus |
|---|---|---|---|---|---|
| « Sauvegarder maintenant » / « Sauvegarde en cours… » | | — | `POST /sauvegardes` | « Sauvegarde faite. » | erreur pg_dump (RuntimeError non gérée → « Erreur 500 ») |
| « Restaurer… » (danger) | grisé si envoi ou autre base (infobulle « Sauvegarde de la base « {b} », pas de celle-ci (« {base} ») : elle ne se restaure pas ici ») ; sinon infobulle « Remplacer toute la base par cette sauvegarde (l'état actuel est d'abord sauvegardé) » | « Revenir à l'état du {date} ? · Non · Oui, continuer… » | ouvre la fenêtre | | |
| « Continuer » | case cochée | | | étape 2 | |
| « Restaurer maintenant » | mot = RESTAURER | | `POST /sauvegardes/{nom}/restaurer` | message ci-dessus ; invalide tout | « Cette sauvegarde est celle de la base « X », pas de « Y » : la restaurer remplacerait toutes les données par celles d'une autre base. » (409) ; « Sauvegarde introuvable. » (404) ; « pg_restore est introuvable sur le serveur. » (500) ; « La restauration a échoué : … » (500) |
| « Annuler » (×2), « Fermer » | | | | | |

  Serveur : coupe les connexions des autres postes, `pg_restore --clean --if-exists --no-owner`, puis journal
  « restauration » / « sauvegarde » ; une sauvegarde manuelle est journalisée « sauvegarde ».

---

#### 2.8 Onglet Journal des actions — `?onglet=journal`

- **Fichier** : `components/direction/ReglagesJournal.tsx` (154 l.) ; `comptes.py:213-270`.
- **Rôles** : DIRECTION (`GET /journal`, `/journal/valeurs`, `/export/journal`).
- **Données** : `GET /journal/valeurs` (personnes, actions, objets distincts) ; `GET /journal?q=&utilisateur=&
  action=&objet=&du=&au=&limite=1000` (tri id décroissant ; `q` : jusqu'à 6 mots, chacun cherché en `ILIKE`
  dans utilisateur, action, objet, détail — jokers échappés ; envoi 250 ms après la frappe).
- **Carte** : titre « Journal des actions — {n} entrée(s) » ou « … — les 1 000 plus récentes » ; note
  « recherche… » pendant le chargement ; « Exporter en Excel » → `/api/export/journal?…` (infobulle « Toutes les
  entrées qui répondent à ces filtres (sans limite), dans un classeur » ; serveur : 100 000 au plus, ligne
  « Filtres — par : … · action : … » ; `q` ≤ 120 car.).
- **Filtres** : « Mots cherchés partout… » ; « Tout le monde » (infobulle « Qui ») ; « Toutes les actions »
  (« Quoi ») ; « Sur tout » (« Sur quoi », trié) ; « Du » (« À partir de ce jour ») ; « Au » (« Jusqu'à ce jour
  inclus ») ; « Effacer les filtres » dès 1 filtre.
- **Note** : « Chaque connexion, création, validation, annulation, modification de réglage s'inscrit ici et ne
  s'efface pas. Les 1 000 entrées les plus récentes qui répondent aux filtres sont affichées ; l'export les
  prend toutes. »
- **Tableau** : « Quand » (horodatage, sans retour à la ligne) · « Par » (nom + note rôle Direction / Achats /
  Alimentation) · « Action » · « Sur » (objet + note « n° {id} ») · « Détail ». Vide : « Rien ne correspond à ces
  filtres. » / « Le journal est vide. ». Chargement : « …le journal des actions… ».

---

#### 2.9 Onglet Courriel du lundi — `?onglet=courriel`

- **Fichiers** : `components/direction/ReglagesCourriel.tsx` (106 l.) ; `suivi.py:850-858` ;
  `gestion_mp/services/courriel.py`.
- **Rôles** : `GET /courriel/apercu` DIRECTION ; enregistrement par `PUT /parametres` (DIRECTION).
- **Carte « À qui, et comment »** : champ « Destinataires » (large ; placeholder « direction@usine.ma,
  achats@usine.ma » ; aide « Adresses séparées par des virgules. Vide : pas de courriel. Il part chaque lundi
  matin. » ou, si une adresse ne passe pas `x@y.z`, « Adresse(s) illisible(s) : … ») ; étiquette « serveur d'envoi
  réglé » (ok) ou « serveur d'envoi non réglé » (attention) + note « Le serveur sait envoyer : le courriel partira
  lundi aux adresses ci-dessus. » / « Le serveur ne sait pas encore envoyer de courriel : la personne qui
  l'entretient règle GESTION_MP_SMTP_HOTE (et l'expéditeur) dans son fichier de lancement. » ; « Annuler »
  (si modifié) ; « Enregistrer les destinataires » (grisé si envoi, rien modifié ou adresse illisible, sans
  infobulle). Succès : « Le courriel du lundi partira à {n} adresse(s). » ou « Plus de courriel du lundi. ».
- **Carte « Ce qu'il dirait aujourd'hui »** : « **Objet :** Gestion MP — la semaine du {jj/mm/aaaa} » ; texte
  (pré-formaté, défile) :
  « Gestion MP — la semaine du {date}[ — {raison sociale}] / Valeur du stock : {n} MAD · couverture pondérée {n}
  jours / Matières en rupture : {n} · critiques : {n} · urgentes : {n} / À commander selon le plan : {n} MAD /
  Commandes en retard : {n}[ — n° (8 au plus)] / Commandes à approuver : {n} / Brouillons en attente : {n}
  réceptions, {n} ordres de fabrication, {n} opérations / Besoins signalés par l'atelier, non traités : {n} /
  Réclamations fournisseurs ouvertes : {n} / Le détail : ouvrir Gestion MP (Cockpit). »
- **Envoi réel** : boucle de fond, un lundi, une fois (paramètre caché `courriel_dernier_envoi`), si
  `GESTION_MP_SMTP_HOTE` et destinataires ; SMTP STARTTLS (port 587 par défaut).

---

#### 2.10 Onglet Serveur — `?onglet=serveur`

- **Fichier** : `components/direction/ReglagesServeur.tsx` (160 l.) ; `comptes.py:505-560`.
- **Rôles** : DIRECTION (`GET /etat-serveur`, relu toutes les 60 s).
- **Indicateurs** : « Gestion MP » (« version {v} », « schéma de base n° {n} · Python {v} ») ; « Base de
  données » (nom ; infobulle « hôte:port » ; « PostgreSQL {v} · {taille Ko/Mo/Go} ») ; « Adresse sur le
  réseau » (« http://ip:port » ; « {machine} · {système} ») ; « Sauvegardes » (« {n} conservée(s) » ok ou
  « arrêtées » critique si pg_dump ou pg_restore manquent ; « dernière le … » / « aucune encore ») ;
  « Connectés » (nb ; « comptes avec une session ouverte »).
- **Carte « L'installation »** (infobulle du titre « Ces réglages se changent dans le fichier de lancement du
  serveur (variables GESTION_MP_…), pas ici : ils décident où vivent les données. ») — tableau clé/valeur :
  « Base » (« {nom} sur {hôte | « ce serveur (connexion locale) »}, port {p} ») ; « Serveur » (« {machine}, port
  {p} · liaison chiffrée (HTTPS) | réseau de l'usine, sans chiffrement ») ; « Tâches de fond » (« sauvegarde
  automatique quotidienne en marche » / « arrêtées sur ce processus (un autre les porte, ou essai) ») ; « Durée
  d'une session » (« {30} jours sans se reconnecter ») ; « Dossier des sauvegardes » ; « Copie de sécurité » (ou
  étiquette « aucun second emplacement ») ; « Outils PostgreSQL » (chemins ou étiquette critique « pg_dump ou
  pg_restore introuvable : les sauvegardes ne se font pas ») ; « Conservation » (« une par jour gardée 14 jours,
  puis la première de chaque mois gardée 12 mois ; les manuelles et « avant restauration » ne s'effacent jamais
  seules »).
- **Carte « Sessions ouvertes ({n}) »** : « Compte » · « Rôle » · « Dernière activité » · « Appareils » (nb de
  sessions) · « Expire le » ; vide « Personne n'est connecté. » ; note « Une session par appareil (ordinateur,
  téléphone). Désactiver un compte (onglet Comptes) ferme toutes ses sessions. ».
- **Gestes** : aucun.

---

#### 2.11 Onglet Téléphone — `?onglet=telephone`

- **Fichier** : `pages/Reglages.tsx:133-215` (`AccesTelephone`) ; serveur `stock.py:332-358`.
- **Rôles** : direction (onglet) ; `GET /acces` et `GET /acces/qr` : toute session.
- **Carte « Dans l'usine, sur le Wi-Fi »** : « Adresse de Gestion MP sur le réseau de l'usine : » +
  adresse en grand (`.dir-adresse`) ; message d'erreur si l'adresse des QR contient localhost/127.0.0.1 :
  « Le QR et les étiquettes mènent à {adresse}, qu'un téléphone ne joint pas. Régler « Adresse du serveur pour les
  téléphones » (Paramètres › Société), par exemple {adresse}. » ; **QR** SVG (150 px) + note « Visez ce QR avec
  l'appareil photo du téléphone : Gestion MP s'ouvre à l'adresse {adresse_qr} (celle que portent aussi les
  étiquettes des lots). Pour la changer — par exemple pour l'adresse Tailscale — Paramètres › Société ›
  « Adresse du serveur pour les téléphones ». » ; étapes : 1 « Connecter le téléphone au Wi-Fi de l'usine. »
  2 « Ouvrir le navigateur (Chrome sur Android, Safari sur iPhone) et taper l'adresse ci-dessus : {adresse}. »
  3 « Choisir son nom et taper son code. » 4 « Dans le menu du navigateur, choisir **« Ajouter à l'écran
  d'accueil »** : Gestion MP s'ouvre ensuite d'un geste, comme une application. »
- **Carte « En dehors de l'usine, en 4G ou 5G »** : « Hors du Wi-Fi de l'usine, le serveur n'est pas visible
  d'Internet — c'est voulu. On passe par **Tailscale**, un réseau privé chiffré entre vos appareils, gratuit pour
  un petit nombre d'appareils. » ; étapes (installer Tailscale sur le serveur ; sur le téléphone avec **le même
  compte** ; relever le nom du serveur — « ici probablement {nom machine} » ; taper
  `http://<nom-tailscale-du-serveur>:{port}`, ex. `http://serveur-usine:{port}` ; « Comme au Wi-Fi : choisir son
  nom, taper son code, puis « Ajouter à l'écran d'accueil ». ») ; note « Tailscale doit rester allumé sur le
  serveur. Un téléphone perdu se retire depuis la console Tailscale, et son compte Gestion MP se désactive dans
  l'onglet « Comptes ». ». Port par défaut lu dans l'adresse, sinon 8030.
- **Adresse des QR** (serveur) : réglage `adresse_publique` s'il est rempli, sinon l'adresse d'appel (localhost
  remplacé par l'adresse réseau).

---

#### 2.12 Clôture de période et en-tête de l'usine (où ils se règlent)

- **Clôture** : il n'y a **pas d'écran de clôture de mois dédié**. La période close se règle dans
  Réglages › Paramètres › Société › « Période close jusqu'au » (`date_cloture`, champ date, direction seule,
  sans confirmation). Serveur : date strictement passée (« On ne clôt qu'une période passée. »), vide = période
  rouverte. Effets (`securite.py:210-276`) : toute écriture datée à cette date ou avant est refusée « La période
  jusqu'au {jj/mm/aaaa} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de
  la rouvrir. » ; tout geste changeant le coût d'une marchandise importée entrée dans la période close est refusé
  (409) : « La marchandise {du dossier X | rattachée} est entrée le {date}, dans la période close jusqu'au
  {date} : son coût a été rendu avec le mois et ne change plus ({geste} refusé). Pour corriger ce mois, la
  direction rouvre la période (Réglages › Période close jusqu'au — c'est tracé), on saisit, puis elle la
  referme. » Rouvrir = vider le champ (tracé au journal « paramètre »).
- **En-tête de l'usine (papier à en-tête des bons)** : Paramètres › Société : Raison sociale, Forme juridique
  et capital, Secteur, Siège social, Ville, Téléphone, Banques (séparées par « · », en pied), ICE, R.C, N.I.F,
  C.N.S.S, Patente. Le bilan du mois n'en reprend que la raison sociale.

---

### 3. DOCUMENT IMPRIMABLE « BILAN DU MOIS » — `GET /api/bilan?mois=AAAA-MM`

- **Fichiers** : `gestion_mp/api/suivi.py:528-614` (`bilan`) et `617-698` (`bilan_imprimable`) ; appel écran
  `pages/Cockpit.tsx:64-81` ; `lib/api.ts:79` (`ouvrir`).
- **D'où on l'appelle** : en-tête du **Cockpit** (direction seule à l'écran) : champ mois (`type=month`, 160 px,
  infobulle « Le mois du bilan », défaut = **mois précédent**, max = mois en cours) + bouton « Bilan du mois »
  (grisé si le mois n'est pas AAAA-MM ; infobulle « Le bilan du mois choisi — entrées, sorties, stock de début et
  de fin, production, achats — dans une page à imprimer ») → `window.open('/api/bilan?mois=AAAA-MM', '_blank',
  'noopener')`. Aucun autre écran ne l'appelle.
- **Droits** : `ACHATS` (achats et direction ; l'écran ne l'offre qu'à la direction). Paramètre `mois` validé
  par motif `^\d{4}-\d{2}$` (refus 422 traduit sinon).
- **Format** : page HTML autonome (pas de PDF), titre d'onglet « Bilan MM/AAAA », police système 13 px, marge
  28 px ; bouton « Imprimer » (`print()`, masqué à l'impression) ; grille de cases 4 colonnes ; tableaux pleine
  largeur ; nombres « 1 234 » (espace) et décimales à virgule ; un « -0 » s'écrit « 0 ».
- **Calculs** (`bilan()`), mois = [1er du mois ; 1er du mois suivant[ :
  - **Mouvements** lus en kilos (tous types, tous magasins dont quarantaine) par `date_effet` ; `stock_debut_kg` =
    Σ quantités signées datées avant le 1er ; `stock_fin_kg` = Σ datées avant le 1er du mois suivant (les
    transferts s'annulent : deux lignes).
  - **Flux du mois** par type (hors TRANSFERT) : une écriture qui est elle-même une **contre-passation**
    (`contrepasse_id` non nul) va dans **annulations** (par type) ; les autres dans les flux.
  - `entrees_kg` = flux RECEPTION ; `valeur_entrees_mad` = Σ quantité × prix × (1 si MAD, sinon **cours figé de
    l'écriture**, à défaut cours du jour) sur les réceptions **non annulées**.
  - `sorties_kg` = −flux SORTIE ; `retours_machine_kg` = flux RETOUR_MACHINE ; `retours_fournisseur_kg` = −flux
    RETOUR_FOURNISSEUR ; `ajustements_kg` = flux AJUSTEMENT ; `ouvertures_kg` = flux OUVERTURE ; `annulations_kg`
    = Σ annulations (et détail par type).
  - **Valeurs** : `valeur_debut_mad` = valorisation CMUP au soir de la **veille** du 1er (journal rejoué) ;
    `valeur_fin_mad` = valorisation au soir du **min(dernier jour du mois, aujourd'hui)** ; `consommation_mad` =
    coût des sorties nettes du mois au coût du journal (`couts_du_journal(...).consommation`).
  - **Fabrication** : m² par qualité = Σ `BonFabrication.m2` des ordres (bons de sortie) **validés** datés du mois ;
    `m2_total`.
  - **Ordres** : consommations (comme Sorties : prévu perte comprise, retours déduits) des ordres validés dont la
    **date de début** est dans le mois ; `ecarts_ordres` = les **8** plus grands |écart relatif|.
  - **Achats** : `commandes` = nb de commandes **numérotées** dont la date de commande est dans le mois (statut
    non filtré) ; `receptions` = nb de réceptions validées datées du mois ; `otif` = moyenne des OTIF des
    réceptions notées du mois ; `receptions_notees`.
  - **Fin de mois** : `ruptures` / `critiques` = nb de matières au statut RUPTURE / CRITIQUE à la date de calcul.
- **Contenu exact de la page** :
  1. `<h1>` « Bilan matières premières — {MM/AAAA} » ; dessous la **raison sociale** (`nom_entreprise`).
  2. `<h2>` « Le mois en chiffres » — cases :
     - « Stock au début » **{kg} kg** · « {valeur début} MAD »
     - « Stock à la fin » **{kg} kg** · « {valeur fin} MAD »
     - (si ouvertures ≠ 0) « Stock d'ouverture saisi » **{kg} kg** · « entré dans le mois »
     - « Entrées (réceptions) » **{kg} kg** · « {valeur} MAD, hors réceptions annulées »
     - « Sorties vers les machines » **{kg} kg** · « dont {kg} kg revenus · coût net {consommation} MAD »
     - « Tissé » **{m²} m²** · « {n} ordre(s) »
     - « Commandes émises » **{n}** · « {n} réception(s) »
     - « Livraisons parfaites (OTIF) » **{x} %** (ou « — % ») · « sur {n} réception(s) »
     - « Ajustements » **{kg, 1 déc.} kg** · « retours fournisseur {kg} kg »
  3. Paragraphe : « Valeurs au coût moyen pondéré (celles de la page Valorisation à ces dates) ; à une date
     passée, le fil monté sur les métiers n'est pas compté (son montage n'a pas d'historique). Stock à la fin =
     début + entrées + ouvertures − sorties + retours des machines − retours fournisseur + ajustements +
     annulations. **Annulations (contre-passations) datées du mois : {kg} kg** [({libellé type} {kg} kg, …)] — elles
     défont des écritures, parfois d'un mois précédent, et ne comptent ni en sorties ni en entrées. »
  4. `<h2>` « Fabrication, qualité par qualité » — tableau « Qualité » · « m² tissés » ; vide « Aucun ordre ce
     mois-ci. ».
  5. `<h2>` « Les plus grands écarts entre la recette et le réel » — tableau « Ordre » · « Qualité » · « Prévu
     (kg) » · « Sorti net (kg) » · « Écart » (« {x,x} % ») ; vide « Aucun. ».
  6. `<h2>` « À la fin du mois » — « {n} matière(s) en rupture, {n} critique(s). ».
- **Gestes** : « Bilan du mois » (Cockpit) ; « Imprimer » (page).
- **Libellés des types** (annulations) : Stock d'ouverture, Entrée de réception, Sortie vers les machines,
  Retour des machines, Retour au fournisseur, Ajustement d'inventaire, Transfert entre magasins.

---

### 4. Exports Excel de cette partie (`gestion_mp/api/exports_analyse.py`, `analyse_import.py`)

| Bouton (onglet) | Route | Droit | Fichier | Feuilles / colonnes |
|---|---|---|---|---|
| Valorisation | `/api/export/valorisation?date_reference=` | ACHATS | `valorisation-AAAA-MM-JJ.xlsx` | « Valorisation » : Référence, Composition, Fournisseur, Magasins (kg), En machine (kg), Stock détenu (kg), Coût moyen (MAD / kg), Prix catalogue (/ kg), Devise, Valeur (MAD), Écart catalogue (MAD) ; en-tête « Valorisation du stock détenu au {date} », « Valeur du stock : {n} MAD, dont en machine … », « Coût moyen pondéré des achats réels ; à défaut d'achat, prix du catalogue. » |
| Matrice / Prix payés | `/api/export/prix` | ACHATS | `prix-…xlsx` | « Historique des achats » (Date, Bon, Référence, Composition, Fournisseur, Quantité (kg), Prix payé (/ kg), Devise, Prix précédent, Évolution, Montant (MAD)) ; « Matrice des prix » (Référence, Composition, Type de fil, Titrage, Couleur, Fournisseur, Devise, puis les mois, récent à gauche) |
| Opportunités | `/api/export/opportunites?…` | ACHATS | `opportunites-…xlsx` | Référence, Fournisseur actuel, Composition, Type de fil, Titrage, Couleur, Prix actuel (MAD / kg), Payé le, Base, Comparable, Chez, Son prix (MAD / kg), Payé le, Base, Écart, Conso / an, Économie / an (MAD) ; + avertissement |
| Fournisseurs | `/api/export/fournisseurs` | ACHATS | `fournisseurs-…xlsx` | « Fournisseurs » (…, Score / 100, Classement, Action ; « Cible OTIF : 95% ») ; « Réceptions notées » |
| Coût de revient | `/api/export/revient?…` | ACHATS | | regroupement + détail lot par lot |
| Échéancier | `/api/export/echeancier?du=&au=` | ACHATS | `echeancier-…xlsx` | « Échéances » (+ En retard, Montant estimé), « À dater », « Par mois » ; pas les réglées |
| Contrôles | `/api/export/controles` | ACHATS | `controles-…xlsx` | synthèse + une feuille par contrôle en anomalie (titre ≤ 31 car.) |
| Journal des actions | `/api/export/journal?…` | DIRECTION | `journal-des-actions-…xlsx` | Quand, Par, Rôle, Action, Sur, N°, Détail |

---

### Incohérences et anomalies repérées

1. **Paramètre de page mort** : `Analyse.tsx:145` lit `?fournisseur=` pour poser la recherche des Fournisseurs,
   mais le seul lien entrant (`components/referentiels/CatalogueFournisseurs.tsx:472`) mène à
   `/analyse?onglet=fournisseurs` sans `&fournisseur=` : la recherche n'est jamais posée.
2. **Contradiction de texte (Valorisation)** : `AnalyseValorisation.tsx:99-100` — l'infobulle dit « compris dans
   la valeur du stock », le détail dit « {kg} montés, **hors stock** ». Le calcul (`moteur.py:2028`) les compte
   bien dans le stock et sa valeur.
3. **Écart affiché ×100 (C36)** : `AnalyseControles.tsx:324` affiche toute colonne `ecart` numérique avec
   `part()` (×100) ; or C36 envoie un écart **déjà en pourcent** (`controles.py`, `round(ecart["part"] * 100, 1)`)
   → 3,5 % s'affiche « 350,0 % ». (C08 et C30 envoient une fraction, correctes.)
4. **Seuils en dur au lieu du réglage** : `ComparaisonPrix.tsx:257` colore l'évolution à 5 % fixe (au lieu de
   `seuil_hausse_forte`) ; `AnalyseProduction.tsx:46,65,87,105` tolérance de 5 % fixe ; `AnalyseValorisation.tsx:111`
   alerte d'écart à 2 % fixe.
5. **Opportunités sans « Effacer les filtres »** (`AnalyseOpportunites.tsx:132-164`) alors qu'il y a cinq filtres
   (recherche, 3 cases, fenêtre) — règle REGLES-ECRAN §2.
6. **Boutons grisés sans raison en infobulle** (règle §2) : case de la Matrice au-delà de 8 fils
   (`AnalysePrix.tsx:255`) ; « Ajouter la devise » (`ReglagesDevises.tsx:158-165`) ; « Enregistrer » d'une devise à
   cours ≤ 0 (`:108-110`) ; « Enregistrer les destinataires » (`ReglagesCourriel.tsx:86`) ; « Créer le compte » quand
   les deux codes diffèrent ou nom trop court (`ReglagesComptes.tsx:252-256`, infobulle seulement pour le code trop
   court) ; « Enregistrer » d'un magasin, code vide (`ReglagesMagasins.tsx:150`) ; « Enregistrer N modification(s) »
   sans modification (`ReglagesParametres.tsx:195-199`).
7. **On laisse cliquer pour découvrir un refus** : magasin qui détient de la matière, case « magasin actif »
   décochée → message rouge mais « Enregistrer » reste actif ; le serveur refuse en 409
   (`ReglagesMagasins.tsx:141-151` / `referentiels.py:1094-1096`). Même chose pour la date de clôture
   future (« On ne clôt qu'une période passée. » non vérifié à l'écran, `ReglagesParametres.tsx:276-282`).
8. **Saisie perdue sans question** : le brouillon des Paramètres (`ReglagesParametres.tsx:136`) et celui des
   Devises (`ReglagesDevises.tsx:29`) disparaissent en changeant d'onglet de Réglages ; les boutons « Annuler » des
   fenêtres Comptes, Magasins, Postes, Codes appellent `onFermer` directement et **contournent** le bandeau
   « Abandonner les modifications ? » (`ReglagesComptes.tsx:251`, `ReglagesMagasins.tsx:149`,
   `ReglagesPostesFrais.tsx:203`, `ReglagesCodesDouaniers.tsx:160`).
9. **Geste lourd sans confirmation** : poser « Période close jusqu'au » (clôture comptable du mois) part avec
   « Enregistrer N modification(s) » sans `Confirmer` ni avertissement (`ReglagesParametres.tsx:177-186`).
10. **Désactiver / Réactiver un compte envoie aussi le reste du formulaire** (nom, rôle, courriel, code saisis) :
    `ReglagesComptes.tsx:127-138` — un changement non voulu part avec la désactivation.
11. **Règle d'écran non tenue par le serveur** : passer un compte « alimentation » à un autre rôle exige un
    nouveau code à l'écran (`ReglagesComptes.tsx:116`) mais `PUT /utilisateurs/{id}` accepte un secret vide
    (`comptes.py:202-205`) : un code de 4 chiffres reste valable pour un compte achats/direction.
12. **Historique des cours faussé** : `PUT /devises` écrit un nouveau « cours » à chaque enregistrement, même
    un simple renommage ou une (dés)activation (`comptes.py:441-444`) → « Depuis le » change sans que le cours ait
    changé, et l'historique montre des variations à 0 %.
13. **Valeur brute non localisée** : dans « Historique des paramètres et des cours de change », un cours
    s'affiche « 10.85 » (point) car `lisible(undefined, …)` rend le texte brut (`ReglagesParametres.tsx:110-111,
    341-342`).
14. **Format anglais dans un refus** : « « X » détient encore {detenu:,.0f} kg » → « 1,234 kg »
    (`referentiels.py:1095`) ; C08/C30 libellés « 2% » / « 5% » sans espace (`{:.0%}`, `controles.py` C08, C30).
15. **Libellé trompeur C29** : « TVA d'importation éloignée de 20 % de la valeur en douane » — il s'agit d'un écart
    à la TVA attendue (au taux de 20 %), pas d'un écart de 20 %.
16. **Erreurs 500 brutes** : `POST /sauvegardes` laisse remonter `RuntimeError` (pg_dump absent ou en échec) →
    l'écran affiche « Erreur 500 » au lieu du message (`services/sauvegarde.py:65-77`, `comptes.py:497-502`) ;
    `GET /bilan?mois=2026-13` → `date(2026, 13, 1)` lève → 500 (`suivi.py:529-530`).
17. **Code mort / réglage mort** : `seuil_bc_urgent` (« BC urgent ») n'est plus lu que si `mode_classeur`, qui est
    toujours faux (`parametres.py:185` force `methode = "corrigee"` ; `moteur.py:1724`) — un réglage affiché qui
    ne règle rien ; branches `mode_classeur` restantes (`pilotage.py:297-304`, `controles.py` C06, C30, C33, C38,
    `moteur.py` scorecard). Message « Les réglages sont réservés à la direction. » (`Reglages.tsx:92-98`)
    inatteignable (la garde renvoie l'alimentation avant). `HAUT_DIALOGUE` déprécié (`commun.tsx:8-10`).
18. **Famille sans aide** : « Stock et inventaire » n'a pas de phrase dans `AIDES_FAMILLE`
    (`ReglagesParametres.tsx:36-50`) : paragraphe vide.
19. **Doublon d'édition** : les destinataires du courriel se règlent à deux endroits (Paramètres › Société
    « Courriel du lundi : à qui », sans contrôle d'adresse, et onglet Courriel, avec contrôle) ; le serveur ne
    vérifie pas les adresses (`comptes.py:318-322`).
20. **Promesse non tenue (Courriel)** : l'en-tête de `ReglagesCourriel.tsx:1-2` annonce « contrôles bloquants,
    sauvegarde… », que le texte du courriel ne contient pas (`services/courriel.py:53-69`).
21. **Échéancier** : la vue « Par mois » et les indicateurs ignorent les filtres de nature et de recherche (seuls
    Du/Au sont envoyés au serveur), alors que les autres vues les appliquent (`AnalyseEcheancier.tsx:118-131`,
    `354-360`) ; la vue « Par mois » n'a pas de total ; l'export n'inclut pas les réglées.
22. **Recherche du journal non conforme** : côté serveur `ILIKE` sans retrait des accents
    (`comptes.py:227-236`) — contraire à la règle « sans accents » (« frise » ne trouve pas « frisé »), alors
    que la recherche du Coût de revient retire les accents côté serveur (`analyse_import.py`, `_sans_accents`).
23. **Vocabulaire** : bilan « Les plus grands écarts entre la recette et le **réel** » et colonne « Prévu (kg) »
    (`suivi.py:695`) au lieu de « Prévu par la recette » ; case « Sorties vers les machines … **dont** {kg}
    revenus » (`suivi.py:683`) : les retours ne sont pas compris dans les sorties (formule écrite juste dessous) ;
    « DH » dans l'aide de « Forme juridique et capital » (exemple du papier à en-tête, `parametres.py:121`) ;
    `classement` serveur « À surveiller » (traduit par l'écran mais pas dans l'export Fournisseurs,
    `exports_analyse.py:207`).
24. **Bilan** : « Commandes émises » compte aussi les commandes annulées (pas de filtre de statut,
    `suivi.py:569-571`) ; pour le mois en cours, la valeur de fin est calculée à aujourd'hui (fil monté compris)
    alors que les kilos de fin viennent du seul journal ; aucun en-tête d'usine (seule la raison sociale) ;
    le serveur accepte un mois futur ; l'écran ne l'offre qu'à la direction alors que la route est ouverte aux
    achats.
25. **Rôles vs REGLES-ECRAN §4** : les achats voient aussi Coût de revient, Échéancier (et peuvent noter un
    règlement, `PUT /echeancier/paiement` ACHATS) et Production, que la règle ne cite pas dans « analyse (prix,
    fournisseurs, valorisation, contrôles) ».
26. **Page Analyse** : l'en-tête affirme « Chacun ne charge ses chiffres qu'à son ouverture » mais la page
    charge toujours matrice, historique, opportunités et contrôles pour les compteurs (`Analyse.tsx:4-5, 101-104`).
27. **Selects sans classe `entree`** (alignement / règle §1) : `ReglagesPostesFrais.tsx:154`,
    `AnalyseRevient.tsx:276,308,316,323,330`.
28. **Sauvegardes** : la note « Les {n} plus récentes sont listées, sur {nb} » compare la liste (toutes bases,
    30 au plus) au nombre de cette seule base (`ReglagesSauvegardes.tsx:164-166`, `comptes.py:488-489`).

### Comptes

- **Écrans / pages** : 2 pages (`/analyse`, `/reglages`) + 1 document imprimable (Bilan du mois) = **3**.
- **Onglets** : Analyse 9 + Réglages 11 = **20** ; **sous-vues** : Bascule ComparaisonPrix 2, Bascule Coût de
  revient 3, Bascule Échéancier 4, familles de Paramètres 10 = **19**.
- **Fenêtres (Dialogue)** : Évolution des prix payés, Réceptions d'un fournisseur, Détail d'un contrôle, Ordre de
  fabrication, Historique des paramètres, Cours d'une devise, Fiche magasin, Fiche poste de frais, Fiche code
  douanier, Fiche compte, Restauration (2 étapes) = **11** (+ `DetailDossier` ouvert depuis Coût de revient,
  inventorié avec les Importations).
- **Contrôles listés** : 38 ; **paramètres listés** : 55.
- **Gestes inventoriés** : Analyse **41** (Valorisation 2, Matrice 7, Prix payés 3, Opportunités 2,
  Fournisseurs 3, Coût de revient 9, Échéancier 4, Contrôles 5, Production 4, liens d'en-tête 2) ; Réglages
  **39** (en-tête 1, Paramètres 4, Devises 4, Magasins 4, Postes 5, Codes 5, Comptes 6, Sauvegardes 6, Journal 2,
  Courriel 2) ; Bilan **2** — total **82**.

---

## Synthèse — comptes et incohérences transverses

### Comptes (toutes parties)

| Partie | Écrans / pages | Onglets et sous-vues | Fenêtres, tiroirs, panneaux | Documents imprimables | Gestes | Anomalies relevées |
|---|---|---|---|---|---|---|
| 1 Coque, connexion, accueil, cockpit, mode d'emploi, lot | 7 | 16 | 4 | (bilan, étiquettes : décrits en 3 et 8) | 30 | 28 |
| 2 Stock, sorties, production | 3 | 29 (12 onglets + 17 bascules) | 7 | étiquettes QR (appel) | 72 | 25 |
| 3 Atelier au téléphone, métiers | 18 (17 téléphone + 1 bureau) | 6 | 2 | Étiquettes de lots (100 × 70 mm, 7 points d'appel) | ≈ 92 | 29 |
| 4 Achats | 3 | 26 | 8 + 3 panneaux | Bon de commande A4 anglais sans prix ; Excel fournisseur | 77 | 21 |
| 5 Importations | 1 (+ 3 logés dans Analyse et Réglages) | 17 | 4 + 1 panneau | — | 59 | 20 |
| 6 Inventaire, opérations | 2 | 9 | 7 | Feuille de comptage / de recomptage | 36 | 25 |
| 7 Catalogue, qualités | 2 (+ Codes douaniers, logé dans Réglages) | 23 | 8 + 1 panneau | — (4 exports Excel) | 71 | 33 |
| 8 Analyse, réglages | 2 | 39 (20 onglets + 19 sous-vues) | 11 | Bilan du mois | 82 | 28 |
| **Total** | **38 écrans distincts** (21 de bureau, 17 au téléphone) | **≈ 160** (doublons Coût de revient / Codes douaniers retirés) | **≈ 48** | **4 documents** (+ ≈ 20 exports Excel) | **≈ 500** (≈ 520 inventoriés, dont une vingtaine décrits deux fois) | **209** |

Référentiels décrits en entier : 38 contrôles (C01–C38, partie 8), 55 paramètres (partie 8), motifs
R1–R6 (parties 3 et 6), 20 composants partagés (partie 1), 7 sections du Mode d'emploi (partie 1).

### Incohérences transverses (les plus importantes pour PRO)

1. **Le fil monté sur les métiers est décrit de trois façons contradictoires.** Le serveur le compte
   (décision de Mohamed du 8 octobre, 18:20) dans le stock, sa valeur, le disponible et le projeté
   (`calcul/moteur.py` `valorisation`, `cockpit`). Mais la confirmation de montage dit encore « une
   information : ces kilos sont déjà sortis et consommés, ils ne changent ni le stock ni le plan
   d'achat » (`components/referentiels/MetiersTisser.tsx:707`) et au téléphone « le fil est déjà
   sorti, le stock ne change pas » (`pages/atelier/Montage.tsx:340`) ; les infobulles du Disponible
   disent « magasins, hors quarantaine » (`components/stock/StockParMatiere.tsx:227, 592`) ; le
   détail de Valorisation le dit « hors stock » ; l'infobulle du Cockpit dit « dont X en machine »,
   son détail « + X sur les métiers ». Ce sont les restes des trois revirements du 8 octobre
   (`DECISIONS.md` § 14 R2). Le montage n'ayant pas d'écriture au journal ni d'historique, PRO doit
   trancher le modèle (voir `DECISIONS.md` § 16.1) et n'avoir **qu'un texte**.
2. **Boutons cliquables qui seront refusés** (contraire à la règle « ne pas laisser cliquer pour
   découvrir un refus ») : supprimer un fournisseur qui a des lots, opérations ou factures
   (`CatalogueFournisseurs.tsx:393-400` contre `referentiels.py:405-414`) ; renommer un rôle porté
   par un poids à 0 ; recette d'une qualité arrêtée ; sortie de quarantaine sans le motif imposé
   (`Operations.tsx:846-889` contre `operations.py:314`) ; matière retrouvée en « Retirer » ; deux
   fournisseurs dans un retour ; « Valider » d'une opération malgré des blocages ; désactiver un
   magasin qui détient de la matière (409) ; « Tout valider (N) » qui compte les brouillons refusés
   (`AValider.tsx:58, 100`) ; « Clôturer le dossier », « Ajouter », « Appliquer aux {devise} »,
   « Ouvrir et figer le stock » grisés sans raison.
3. **Saisies perdues sans question** : « Fermer » du retour des machines au bureau
   (`RetourBureau.tsx:184`), plan de production (protégé seulement à la fermeture du navigateur,
   `Production.tsx:50-57`), « Tout annuler » du plan (`VoletPlan.tsx:157`), brouillons de Paramètres et
   de Devises au changement d'onglet, boutons « Annuler » des fiches de Réglages qui contournent
   « Abandonner les modifications ? ».
4. **Droits de l'écran ≠ droits du serveur** : `/lot/:id` au téléphone envoie tout rôle vers
   `/atelier/lot/:id`, réservé à l'alimentation — un acheteur qui scanne un QR arrive sur l'accueil
   sans message (`App.tsx:163, 167`) ; les **transferts** sont permis à l'alimentation par le serveur
   (`operations.py:32`, cahier § 4) mais `/operations` lui est fermé (`App.tsx:70, 258`) : « Ouvrir »
   depuis « À valider » la renvoie à son accueil ; les codes douaniers ne sont visibles que de la
   direction alors que le message de refus du serveur y renvoie les achats ; la route `/moi/code`
   (changer son propre code) n'a aucun écran.
5. **Vocabulaire hors règle** (`REGLES-ECRAN.md` § 5) encore présent : « Fil » en en-tête de colonne
   (`QualiteDetail.tsx:334` et ailleurs), « bon » dans des messages du serveur, « en machine »,
   « journal » pour les mouvements, « sans n° » et « Ordre du {date} » au lieu de « Brouillon »,
   « Commentaire » au lieu d'« Observations », « Ouvert par » / « Validé par » au lieu de « Par »,
   « USD/kg » (catalogue) contre « USD / kg » (qualités).
6. **Chiffres affichés faux ou contradictoires** : écart de C36 multiplié deux fois par 100 (« 350,0 % »
   pour 3,5 %, `AnalyseControles.tsx:324` alors que `controles.py:888` l'envoie déjà en %) ; deux
   définitions de la TVA saisie dans un dossier (`DetailDossier.tsx:1005, 1067, 1076` contre
   `importations.py:201`) ; valeur en douane dite « achat + fret » à l'écran, « achat + fret +
   assurance » au serveur, TPI « 0,25 % » écrit en dur alors qu'il se règle ; trois comptes différents
   des « matières en alerte » (pastille du menu, Accueil, Cockpit) ; valeur des écarts d'inventaire
   renvoyée par le serveur mais jamais affichée.
7. **Gestes sans effet ou code mort** : la case « Envoyer avec nos prix du catalogue, « à confirmer » »
   ne change rien au bon (`PreparationCommande.tsx:617-635`) ; « Livraison prévue » ne se vide pas
   (l'écran envoie `null`, le serveur l'ignore, `achats.py:619`) alors que les messages disent « la
   vider » ; route `exporter_bon_de_commande` (`exports.py:307`) jamais appelée, en français, avec prix
   et « Livraison souhaitée » ; réglage « BC urgent » affiché mais inerte ; `?fournisseur=` de l'Analyse
   jamais rempli par le lien du catalogue.
8. **Réseau et téléphone** : une coupure se lit comme une liste vide ou « Ce lot n'existe pas » ;
   `?bon=ID` ouvre un ordre vierge au lieu du brouillon (`Envoyer.tsx:38-48`) ; le service worker n'est
   enregistré qu'en contexte sécurisé alors que l'accès documenté est en http (`main.tsx`) et ne met
   rien en cache ; la connexion part automatiquement à 4 chiffres alors que le serveur accepte un code
   de 4 caractères **au moins** (`Connexion.tsx:100`) ; la relance des requêtes teste le texte de
   l'erreur au lieu du statut (`main.tsx:15`).
9. **Atomicité** : un camion en deux devises s'enregistre en plusieurs requêtes (doublon possible en
   cas d'échec à mi-chemin) ; fils et réglages d'un métier s'enregistrent séparément ; le contrôle
   d'excédent de l'écran est par ligne, celui du serveur additionne les lots.
10. **Contrôles faibles** : recomptage « à quatre yeux » seulement signalé (`inventaires.py:355-357`) ;
    « Feuille de recomptage » active sur des saisies non enregistrées (`Inventaire.tsx:846`) ; import
    par tableur moins exigeant que la fiche matière (contenance, bornes, négatifs ; une case vide ne
    vide pas ; noms de champs bruts dans les messages ; `NOMS_CHAMPS` sans `unite_prix` ni
    `code_douanier`, `TableurMatieres.tsx:22-44`) ; clôture de période sans confirmation ; liste des
    opérations coupée à 1 000 sans avertissement ; un frais déjà réglé se modifie sans que l'écran le
    montre.
11. **Documents d'exploitation en retard sur l'écran** : `MISE-EN-SERVICE.md` parle de « Stock › Lots
    en stock » (onglet « Lots ») et de « Réglages › Accès téléphone » (onglet « Téléphone ») ;
    `/` de l'alimentation au bureau mène à `/sorties` alors que son accueil est `/accueil`.

Le détail de chaque anomalie, avec `fichier:ligne`, est à la fin de chaque partie.
