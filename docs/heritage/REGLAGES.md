# Héritage Gestion MP — les réglages (paramètres), les devises et les constantes

> Inventaire tiré du **code** de Gestion MP (`/Users/mohamed/gestion-mp`, état du 8 octobre 2026,
> commit `2d588b9`). Références `fichier:ligne` relatives à `gestion_mp/` sauf `ecran/src/...`.
> Source principale : `parametres.py` (189 lignes, liste `REGLAGES`), `calcul/modele.py:60-147`
> (classe `Parametres` du moteur), `api/comptes.py:273-446` (routes), puis un `grep` de chaque clé.

---

## 1. Stockage

### 1.1 Tables

| Table | Colonnes | Où |
|---|---|---|
| `parametre` | `cle` String(60) **PK** ; `valeur` Text NOT NULL défaut « » ; `modifie_le` DateTime NOT NULL (défaut maintenant, **à l'insertion seulement**) ; `modifie_par` String(80) | `modeles.py:123-129` |
| `parametre_historique` | `id` PK ; `cle` String(60) indexée ; `valeur` Text ; `quand` DateTime (défaut maintenant) ; `par` String(80) | `modeles.py:132-139` |
| `devise` | `code` String(3) PK ; `nom` String(40) ; `taux` Float NOT NULL (vers le dirham) ; `actif` bool ; `CHECK (taux > 0)` | `modeles.py:159-166` |

Toutes les valeurs sont du **texte** ; les nombres sont écrits `str(int(x))` s'ils sont entiers, sinon
`repr(float)` (`comptes.py:309`). Les taux affichés en % sont **rangés en fraction** (0,02 = 2 %) :
`echelle = 100` dit à l'écran de multiplier.

### 1.2 Installation (`parametres.installer`, `parametres.py:151-156`, appelé par `main.py:84`)

À chaque démarrage (`main.initialiser`), toute clé de `REGLAGES` absente de `parametre` est écrite
avec `str(defaut)` et `modifie_par = "installation"` ; une clé existante n'est **jamais** écrasée.
Docstring : « Chacun est écrit en base dès l'installation — un réglage qu'on ne voit pas n'existe
pas — et chaque changement est historisé (qui, quand, quelle valeur). » L'installation du premier
compte (`POST /installation`, `comptes.py:83-104`) recopie le champ « société » dans
`nom_entreprise`. Les devises par défaut sont créées au même moment (`main.py:45`, `:75-77`) :
**MAD « Dirham » 1,0 ; USD « Dollar américain » 10,0 ; EUR « Euro » 10,8**.

### 1.3 La déclaration d'un réglage (`Reglage`, `parametres.py:18-28`)

```text
@dataclass(frozen=True) Reglage
  cle: str           clé en base
  libelle: str       libellé affiché
  famille: str       onglet de l'écran
  defaut: float|str  défaut ; un défaut str = réglage texte
  bas, haut: float|None   bornes (dans l'unité RANGÉE, donc fraction pour un %)
  unite: str         « jours », « % », « MAD », « mois », « /100 », ou « »
  echelle: float     1, ou 100 pour un taux saisi en pourcent
  aide: str          texte d'aide (serveur)
PAR_CLE = {cle: Reglage}
```

### 1.4 Lecture

| Fonction | Où | Usage |
|---|---|---|
| `valeurs(s)` → `{cle: valeur texte}` | `parametres.py:159-160` | Fiche société (bons de commande), `GET /parametres` |
| `nombre(s, cle)` → float | `parametres.py:163-168` | Lecture directe hors moteur ; **valeur absente, vide ou illisible → défaut, sans erreur** |
| `pour_le_moteur(s)` → `Parametres` | `parametres.py:171-189` | Conversion pour le moteur de calcul (§ 5) |
| `s.get(m.Parametre, "cle")` | `securite.py:219,231`, `stock.py:335`, `courriel.py:52,76-77`, `suivi.py:856`, `comptes.py:57,92` | Lecture brute de textes |

### 1.5 Cache du moteur

`depot._signature` (`depot.py:673-685`) invalide les données du moteur au changement de : date du
jour, max(id du journal des actions), max(id de mouvement), **max(`parametre.modifie_le`)**, nombre de
mouvements, Σ des soldes. Un changement de réglage met à jour `modifie_le` (`comptes.py:326`) ; un
changement de cours de devise écrit au journal des actions → cache invalidé aussi.

---

## 2. Routes et droits

| Route | Droit | Effet | Où |
|---|---|---|---|
| `GET /api/parametres` | tout compte connecté (`acteur`) — **alimentation comprise** | `{"reglages": [{cle, libelle, famille, unite, echelle, aide, bas, haut, texte (bool : défaut str), defaut, valeur (texte, défaut si absente)}]}` dans l'ordre de `REGLAGES` | `comptes.py:276-289` |
| `PUT /api/parametres` | **direction** (`DIRECTION`) | Corps `{cle: valeur}` (str ou nombre) ; valide, écrit, historise, journalise ; renvoie la liste complète | `comptes.py:292-338` |
| `GET /api/parametres/historique` | **direction** | Les 500 derniers changements, du plus récent : `{cle, libelle (ou la clé si inconnue), valeur, avant, quand (minute), par}` | `comptes.py:369-387` |
| `GET /api/devises` | tout compte connecté | `[{code, nom, taux, actif, cours_le}]` (cours_le = dernier `cours_XXX` historisé) | `comptes.py:400-413` |
| `GET /api/devises/{code}/historique` | tout compte connecté | 500 derniers cours `{taux, quand, par}` | `comptes.py:416-427` |
| `PUT /api/devises` | **achats** (+ direction) | Crée ou modifie une devise ; historise `cours_XXX` ; journalise | `comptes.py:430-446` |

Écran (`ecran/src/pages/Reglages.tsx:83-98`) : la direction voit tous les onglets (Paramètres,
Devises, Magasins, Frais, Douane, Comptes, Sauvegardes, Journal, Courriel, Serveur, Téléphone) ; les
achats **seulement l'onglet Devises** (« le contrôle C11 les y envoie ») ; l'alimentation « Les
réglages sont réservés à la direction. »

### 2.1 Validation de `PUT /parametres` (`comptes.py:292-338`)

Dans l'ordre :
1. Clé inconnue → 422 « Paramètres inconnus : a, b. »
2. Pour chaque couple : `texte = str(valeur).strip()`.
   - **Réglage numérique** : `float(texte.replace(",", "."))` (virgule acceptée) sinon « « Libellé »
     attend un nombre. » ; hors `[bas, haut]` → « « Libellé » doit rester entre {bas×échelle} et
     {haut×échelle} {unité} — reçu {valeur×échelle}. » (la valeur reçue est attendue **dans l'unité
     rangée**, ex. 0.02 pour 2 %) ; puis normalisée (entier ou `repr`).
   - **`date_cloture`** non vide : date ISO `AAAA-MM-JJ` sinon « Date de clôture illisible
     (AAAA-MM-JJ). » ; date ≥ aujourd'hui → « On ne clôt qu'une période passée. » ; vide autorisé
     (réouverture).
   - **`adresse_publique`** non vide : doit commencer par `http://` ou `https://`, ≤ 200 caractères,
     sans espace, sinon « L'adresse commence par http:// ou https:// (ex. http://mac-usine:8030). »
   - **Autre texte** > 500 caractères → « « Libellé » : texte trop long. »
3. Valeur identique à celle en base → ignorée (ni historique ni journal).
4. Sinon : `valeur`, `modifie_le`, `modifie_par` mis à jour ; ligne `parametre_historique` ; journal
   des actions (action « paramètre », objet « parametre ») : « Libellé : avant → après » mis en forme
   par `_lisible` (`comptes.py:355-366` : virgule décimale, ×échelle, unité ; « — » si vide).
5. `flush`, puis **contrôle d'ordre** (`ORDRES_PARAMETRES`, `comptes.py:341-352`) : pour chaque
   couple (petit, grand), si `nombre(petit) >= nombre(grand)` → `rollback` de **tout** l'envoi et 422 :

| Plus petit | Plus grand | Message de refus exact |
|---|---|---|
| `seuil_critique` | `seuil_alerte` | « La couverture critique doit rester inférieure à la couverture d'ATTENTION : sinon plus aucune matière ne serait en ATTENTION. » |
| `seuil_abc_a` | `seuil_abc_b` | « La part cumulée de la classe A doit rester sous celle de la classe B. » |
| `seuil_xyz_x` | `seuil_xyz_y` | « Le CV maximum de la classe X doit rester sous celui de la classe Y. » |
| `score_surveiller` | `score_standard` | « Le score « ATTENTION » doit rester sous le score « standard ». » |
| `score_standard` | `score_strategique` | « Le score « standard » doit rester sous le score « stratégique ». » |

Égalité refusée (`>=`). L'écran fait les mêmes vérifications avant l'envoi (bouton « Enregistrer »
grisé avec la liste des refus en info-bulle) avec un texte plus court pour le premier : « La
couverture critique doit rester inférieure à la couverture d'ATTENTION. »
(`ReglagesParametres.tsx:126-133`, `:152-163`). Commit d'origine : `f85dabd` (« seuils refusés dans
le désordre »).

6. `commit` ; renvoie `lire_parametres`. Message écran : « N paramètre(s) enregistré(s) : tout le
   pilotage est recalculé. » puis invalidation de toutes les requêtes de l'écran.

### 2.2 Historique (`GET /parametres/historique`)

Calcule « avant » en relisant **tout** l'historique dans l'ordre : la valeur précédente du même
réglage, sinon son défaut (`None` si la clé n'est pas un réglage déclaré). Rend les 500 dernières
lignes. Les lignes `cours_EUR`, `cours_USD`… écrites par `PUT /devises` sont **aussi** rendues (même
table), avec la clé brute pour libellé et `avant = None` pour la première.

### 2.3 Écran Réglages › Paramètres (`ecran/src/components/direction/ReglagesParametres.tsx`)

- Onglets = familles dans l'ordre de première apparition + « Méthode de calcul ».
- Aide d'un réglage = `aide serveur || AIDES_REGLAGE[cle]` (`:119-125`), puis « entre X et Y unité »,
  « par défaut : … », « avant : … » si modifié. **L'aide serveur gagne** : les textes écran de
  `toler_in_full`, `toler_excedent`, `toler_retard_jours`, `taux_tpi_import`, `seuil_surcout_import`,
  `toler_facture_import` ne s'affichent jamais.
- Une phrase par famille (`AIDES_FAMILLE`, `:36-51`) — textes exacts reproduits au § 3.
- Onglet « Méthode de calcul » (`:95-108`) : « Gestion MP calcule toujours avec la méthode corrigée de
  l'ERP Fil : les sept corrections apportées au classeur après son audit. Le mode « classeur », qui
  reproduisait le tableur à l'identique pour comparer, n'existe plus — il n'y a donc rien à régler
  ici. » puis la liste `CORRECTIONS` (`:93-101`) :
  1. « Le seuil d'alerte tient compte du délai du fournisseur : on commande à temps pour être livré avant la rupture. »
  2. « Une seule devise par matière : celle de son prix ; les montants ne s'additionnent jamais entre devises. »
  3. « Le taux de perte entre dans le besoin et dans le coût matière. »
  4. « Le plan d'achat se trie en dirhams, pondéré par la classe ABC (× 3 en A, × 2 en B). »
  5. « Le mois en cours est compté au prorata des jours qui restent. »
  6. « Seules les commandes attendues dans le délai comptent dans le stock projeté. »
  7. « Les quantités à commander sont arrondies au conditionnement (palette, fût, sac…) et au minimum de commande. »
- Bouton « Historique des changements » (fenêtre), « Annuler », « Enregistrer ».

---

## 3. Les 55 réglages, famille par famille

Colonnes : **Clé** — **Libellé exact** — **Type / défaut / bornes / unité** (bornes dans l'unité
affichée) — **Aide** (serveur, exacte ; « écran : » si elle vient de `AIDES_REGLAGE`) — **Où il agit**.
Ligne de déclaration : `parametres.py:<n>`.

### 3.1 Couverture et statuts (`COUVERTURE`)

Aide de famille (écran) : « Les couvertures critique et d'ATTENTION ne règlent que le « statut
classeur », gardé pour comparaison (colonne « Statut classeur » du stock, info-bulle du Cockpit) : la
couverture — les jours de consommation que le stock tient encore après le délai — comparée à ces deux
seuils, les mêmes pour un fournisseur à 4 jours et pour un import à 90 jours. Le statut qui décide —
Cockpit, plan d'achat, courriel du lundi, quantités à commander — compare le stock projeté à son seuil
d'alerte (sécurité de sa classe ABC, couverture minimum et stock minimum du catalogue, réglés dans
Approvisionnement) : CRITIQUE sous la moitié du seuil, URGENT sous le seuil, ATTENTION jusqu'à 120 %.
Le stock dormant compte les jours sans sortie ni entrée. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `seuil_critique` (42) | Couverture critique | nombre ; 60 ; 1–3650 ; jours | « Statut classeur seulement, pour comparaison : sous cette couverture, une matière y est « critique ». Le statut du Cockpit, du plan d'achat et du courriel compare le stock projeté au seuil d'alerte. » | `moteur.py:1277` : `statut_couverture` = CRITIQUE si couverture (jours) < seuil. Affiché seulement (stock, info-bulle Cockpit `CockpitAlertes.tsx:103-104`, `moteur.py:2592`). Ordre : < `seuil_alerte`. |
| `seuil_alerte` (46) | Couverture d'attention | nombre ; 90 ; 1–3650 ; jours | « Statut classeur seulement, pour comparaison : sous cette couverture, une matière y est en ATTENTION. » | `moteur.py:1279` : `statut_couverture` = ATTENTION si couverture < seuil (sinon OK). Même portée. |
| `seuil_dormant` (49) | Stock dormant | nombre ; 180 ; 1–3650 ; jours | « Sans sortie ni entrée depuis ce nombre de jours, un stock détenu dort. » | `moteur.py:1431,1443` : `dormant` si stock net > 0 et jours sans mouvement (max dernière sortie, dernière entrée) > seuil ; `moteur.py:2567` Cockpit (`dormant.seuil_jours`, nombre et valeur dormants) ; C18 (`controles.py:1090` libellé). |

### 3.2 Approvisionnement (`APPRO`)

Aide de famille : « La fenêtre de réapprovisionnement et les marges appliquées au calcul des quantités
à commander : délai, couverture d'une commande, sécurité par classe, pertes, croissance du plan. La
sécurité par classe et le stock minimum font le seuil d'alerte, qui décide du statut. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `delai_defaut` (51) | Délai par défaut | nombre ; 60 ; 1–730 ; jours | « Délai pris pour une matière sans fournisseur (ou d'un fournisseur inconnu) ; un fournisseur a toujours son propre délai, saisi dans sa fiche. » | `modele.py:741-749` `Donnees.delai_fournisseur` → délai de la matière dans `etat_stock` (`moteur.py:1121`) : fenêtre de demande du délai, commandes « à temps », horizon, stock projeté. |
| `marge_jours` (54) | Couverture de commande | nombre ; 30 ; 0–730 ; jours | « Ce qu'une commande couvre, à défaut du pas du fournisseur. » | `modele.py:751-756` `couverture_commande` si le fournisseur n'a pas de `couverture_commande_jours` (0 ou absent) → `moteur.py:1122-1160` (sorties prévues de la période couverte, commandes dans la couverture, horizon = délai + couverture + 30 j), `:1327-1331` (sécurité de la quantité). |
| `marge_securite` (56) | Marge de sécurité | nombre ; 0,2 ; 0–500 ; % (×100) | écran : « Majore la couverture minimum que porte la fiche d'une matière (en mois) : à 20 %, une couverture minimum de 2 mois en demande 2,4. Elle entre dans le seuil d'alerte, qui est le plus grand du stock minimum, de cette couverture et de la sécurité de la classe. Sans couverture minimum dans la fiche, elle ne change rien. » | `moteur.py:1261` : seuil d'alerte (`stock_min_recalcule`) = max(stock min plafonné, `couv_min_mois × conso_horizon × (1 + marge)`, sécurité de classe) ; `:1232` (classeur). |
| `taux_perte` (57) | Taux de perte matière | nombre ; 0,02 ; 0–50 ; % (×100) | « Ajouté aux besoins et au coût de la matière. » | Besoins × (1+perte) : `moteur.py:469` (besoins mensuels), `:562` (besoins passés) ; coût au m² : `moteur.py:369` (nomenclature) et `referentiels.py:833` (facteurs de coût à la frappe) ; production : `production.py:89` (consommation par OF), `:201` (proposition de bon), **figé dans l'ordre à sa validation** `production.py:492` ; écrans plan/besoins `production_plan.py:95,139,220,282`. |
| `securite_a` (59) | Sécurité classe A | nombre ; 30 ; 0–365 ; jours | écran : « Jours de consommation à venir gardés en sécurité pour une matière de classe A. Le seuil d'alerte est le plus grand de cette sécurité, du stock minimum et de la couverture minimum : elle ne s'y ajoute pas. » | `moteur.py:1487-1492` `_jours_securite` → `:1262` seuil d'alerte (conso_horizon × jours / 30) et `:1329` sécurité de la quantité à commander (jours × sorties prévues / couverture). |
| `securite_b` (60) | Sécurité classe B | idem ; 30 | écran : « Jours de sécurité pour une matière de classe B (le seuil d'alerte en prend le plus grand, comme pour A). » | idem, classe B |
| `securite_c` (61) | Sécurité classe C | idem ; 30 | écran : « Jours de sécurité pour une matière de classe C (le seuil d'alerte en prend le plus grand, comme pour A). » | idem, classe C (et toute classe ≠ A, B) |
| `fenetre_realisation_jours` (62) | Prévision — fenêtre du réalisé | nombre ; 90 ; 0–730 ; jours | « Sorties réelles comparées au plan, par mois entiers clos (les jours ramenés en mois au plus près, un demi arrondi au-dessus : 75 j = 3 mois). 0 = plan seul. » | `moteur.py:868-881` : nombre de mois clos = arrondi(j / 30) (≥ 1), raccourci tant que l'atelier ne sortait pas encore (première sortie > début de mois + 7 j) ; coefficient de réalisation = réel / prévu borné [0,5 ; 1,5] (`:1046`) ; 0 → ancienne règle max(historique, plan). Renvoyé à l'écran `production_plan.py:283`. |
| `plafond_stock_min_mois` (66) | Stock minimum — plafond | nombre ; 3 ; 0–60 ; mois | « Le stock minimum du catalogue ne vaut pas plus de N mois de la consommation à venir (celle de l'horizon de commande). 0 = pas de plafond : le stock minimum du catalogue vaut tel quel. Une matière non consommée n'en a aucun. » | `moteur.py:1249-1257` : `stock_min_plafonne = min(stock_min, N × conso_horizon)` (0 si conso nulle) ; C33 (`controles.py:997`). |
| `croissance_annuelle` (71) | Croissance annuelle du plan | nombre ; 0 ; −90–1000 ; % (×100) | écran : « Ajoutée au plan de production à partir du jour où la base a été saisie : à 5 %, une base saisie en janvier vaut 5 % de plus en janvier suivant. Un mois garde la même prévision, qu'on le regarde six mois avant ou le mois même. » | `moteur.py:211` : m² du mois = arrondi(base × saisonnalité × (1+c)^(mois depuis l'ancre / 12)), c ≥ −0,9 (`CROISSANCE_MINIMUM`) ; `:225` (classeur, depuis le mois en cours) ; affiché `production_plan.py:138`. Commentaire : « Au-dessus de −100 % : à −100 %, la production s'annule et un mois passé se divise par zéro. » |

### 3.3 Classification ABC / XYZ (`CLASSES`)

Aide de famille : « ABC classe les matières par valeur consommée : A pour l'essentiel de la dépense,
puis B, puis C. XYZ les classe par régularité de la demande mensuelle, mesurée par le coefficient de
variation (CV = écart-type ÷ moyenne) : X régulière, Y variable, Z erratique. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `seuil_abc_a` (72) | Classe A — valeur cumulée | nombre ; 0,8 ; 0–100 ; % (×100) | écran : « Les matières qui font ensemble cette part de la valeur consommée sont en classe A. » | `moteur.py:1523` : classe A si % cumulé (Σ valeurs ≥ la sienne / total, en MAD) ≤ seuil. Ordre : < `seuil_abc_b`. Influence la sécurité par classe, le Tier 1, le tri du plan d'achat (×3), l'inventaire tournant. |
| `seuil_abc_b` (73) | Classe B — valeur cumulée | nombre ; 0,95 ; 0–100 ; % | écran : « Jusqu'à cette part cumulée, classe B ; au-delà, classe C. » | `moteur.py:1525` |
| `seuil_xyz_x` (74) | Classe X — CV maximum | nombre ; 0,25 ; 0–10 ; (sans unité) | écran : « Sous ce coefficient de variation (écart-type ÷ moyenne mensuelle), la demande est régulière : classe X. » | `moteur.py:1456` : X si 0 < CV ≤ seuil (CV sur 12 mois clos, sorties nettes) ; CV nul → « — ». Ordre : < `seuil_xyz_y`. Affiché seulement (stock, Cockpit). |
| `seuil_xyz_y` (75) | Classe Y — CV maximum | nombre ; 0,5 ; 0–10 | écran : « Sous ce coefficient de variation, la demande est variable : classe Y. Au-delà, erratique : classe Z. » | `moteur.py:1458` |

### 3.4 Politique d'achat (`ACHAT`)

Aide de famille : « Les montants qui classent un bon de commande (groupé ou standard), les tiers de
priorité du plan d'achat, et le seuil au-delà duquel la direction approuve une commande avant l'envoi.
L'urgence ne vient jamais du montant : un fournisseur est « urgent » quand une de ses matières est en
rupture, critique ou urgente ; une ligne CRITIQUE est en Tier 1, une ligne URGENTE en Tier 2 au moins
— les montants ne font que remonter les autres. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `seuil_bc_urgent` (76) | BC urgent | nombre ; 300 000 ; 0–1e12 ; MAD | écran : « Ne sert plus qu'à la méthode du classeur (comparaison). Au plan d'achat, un fournisseur est « urgent » quand une de ses matières est en rupture, critique ou urgente — pas pour le montant de sa commande. » | `moteur.py:1725` — **mode classeur seulement** : « 🚨 BC URGENT » si rupture ou montant ≥ seuil. **Inerte en service.** |
| `seuil_bc_groupe` (77) | BC groupé | nombre ; 100 000 ; 0–1e12 ; MAD | écran : « Au plan d'achat, ce qu'il faut commander à un fournisseur sans urgence, à partir de ce montant, se passe en un bon groupé ; en deçà, c'est un bon standard. » | `moteur.py:1733` : groupe fournisseur non urgent → « 📋 BC groupé » si montant MAD ≥ seuil, sinon « 📝 Standard » (« — » si 0). |
| `seuil_tier1` (78) | Tier 1 (classe A) | nombre ; 300 000 ; 0–1e12 ; MAD | écran : « Une matière de classe A dont la commande atteint ce montant passe en Tier 1 (émettre cette semaine), comme toute rupture ou matière CRITIQUE. » | `moteur.py:1618` (`_tier`) : classe A et montant MAD ≥ seuil → « 🔥 TIER 1 » (« Émettre cette semaine »). |
| `seuil_tier2` (79) | Tier 2 | nombre ; 200 000 ; 0–1e12 ; MAD | écran : « À partir de ce montant, Tier 2 (sous 7 jours). Une matière URGENTE y est de toute façon, quel que soit son montant. » | `moteur.py:1620` : montant ≥ seuil → « 🟠 TIER 2 » (« Émettre sous 7j »). |
| `seuil_tier3` (80) | Tier 3 | nombre ; 100 000 ; 0–1e12 ; MAD | écran : « À partir de ce montant, Tier 3 (sous 15 jours) ; en deçà, Tier 4 (regrouper sous 30 jours) — sauf urgence. » | `moteur.py:1624` : → « 🟡 TIER 3 » (« Émettre sous 15j ») ; sinon « ⚪ TIER 4 » (« Regrouper sous 30j »). |
| `seuil_approbation` (81) | Approbation des commandes au-delà de | nombre ; 0 ; 0–1e12 ; MAD | « Une commande plus chère attend l'approbation de la direction. 0 = jamais. » | Lu par `parametres.nombre` : `achats.py:700-707` (`envoyer` : montant MAD > seuil et non approuvé → statut « a_approuver » ; refus si livraison prévue déjà passée) ; `achats.py:262-288` (`_controler_montant` : un bon parti dont le nouveau montant au cours figé dépasse le seuil et son montant de référence × (1 + tolérance) repasse « à approuver » ; tolérance 0,05 en dur pour la confirmation des prix, `achats.py:841`) ; `achats.py:116,331,354` (liste : `approbation_requise`). |

### 3.5 Réceptions et fournisseurs (`RECEPTION`)

Aide de famille : « Les tolérances de réception (pesée, poids de bobine, livraison complète) et la
notation des fournisseurs : OTIF = à l'heure × complète × conforme, et les scores qui classent. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `toler_in_full` (85) | Tolérance de livraison complète | nombre ; 0,02 ; 0–20 ; % | « Une ligne reçue à cette part près de la quantité commandée compte comme livrée en entier (elle n'attend plus rien). Au plus 20 % : au-delà, un bon à peine entamé passerait pour livré. » (commentaire : « à 100 %, aucun bon ») | `modele.py:422` `reste_a_livrer` = 0 si reste ≤ commandé × tol (stock projeté, C06) ; `moteur.py:2690` In-Full de l'OTIF ; `achats.py:68-75` `livre()` (statut de livraison des bons, `achats.py:114`) ; `achats.py:587-596` **solde automatique** d'un bon livré (et réouverture si plus livré) ; `receptions.py:89-95` reste attendu d'un brouillon de réception remis à 0. |
| `toler_ecart_pesee` (89) | Tolérance d'écart de pesée | nombre ; 0,02 ; 0–100 ; % | écran : « Un écart entre la pesée et le bon de livraison au-delà de ce taux est signalé (contrôle C08). Sans bon de livraison, une pesée franchement sous le reste à livrer est une livraison partielle, pas un écart. » | Deux rôles : **seuil d'écart** (C08 `controles.py:389`, archive des pesées `moteur.py:3059` « hors tolérance », performance `moteur.py:2799` lignes hors tolérance, `pilotage.py:410`) et **tolérance de livraison partielle** (pesé < attendu × (1 − tol) sans BL → pas d'attendu : `depot.py:376,406`, `modele.py:478-482`, `receptions.py:209,223-224`). |
| `toler_excedent` (90) | Excédent de livraison toléré | nombre ; 0,1 ; 0–1000 ; % | « Une ligne de bon reçoit au plus son reste à livrer plus cette part de la ligne ; au-delà, la réception est refusée (le surplus se reçoit hors commande). » | `receptions.py:131-163` (`blocages`) : Σ pesé (tous lots) sur une ligne de bon > reste + commandé × tol + 1e-6 → blocage « … kg reçus pour … kg restant à livrer sur … (excédent toléré : x % de la ligne). Recevoir le surplus sur une … ». |
| `toler_poids_bobine` (93) | Tolérance du poids de bobine | nombre ; 0,05 ; 0–100 ; % | écran : « Un poids de bobine reçu éloigné du catalogue de plus de ce taux est signalé (contrôle C30). » | `moteur.py:3115` (évolution des bobines, hors tolérance → C30 `controles.py:985`) ; `moteur.py:3060` (archive des pesées, `bobine_hors_tolerance`) ; `referentiels.py:1213` (`GET /metiers` : écart pesé/catalogue signalé) ; `pilotage.py:411,438`. |
| `toler_retard_jours` (97) | Retard toléré dans la ponctualité | nombre ; 0 ; 0–60 ; jours | « Une livraison en retard de N jours ou moins reste « à l'heure ». » (écran, jamais affiché : « … et un bon n'est dit « en retard » (écran, contrôle C06, courriel du lundi) qu'au-delà de ces N jours. ») | `moteur.py:2738` On-Time (réception − date BC ≤ date promise − date BC + N) ; C06 `controles.py:333` ; `achats.py:115` → `_statut_livraison` (`achats.py:96-97` : « En retard » / « Partiel retard » au-delà de date prévue + N) ; courriel du lundi `courriel.py:39-43`. |
| `cible_otif` (99) | Cible OTIF | nombre ; 0,95 ; 0–100 ; % | écran : « Sous cette part de livraisons parfaites, un fournisseur est signalé « sous la cible ». » | `moteur.py:2928` `sous_performant` ; `pilotage.py:507` ; export fournisseurs « Cible OTIF : x% » `exports_analyse.py:210`. |
| `score_strategique` (100) | Score — Stratégique | nombre ; 85 ; 0–100 ; /100 | — | `moteur.py:2890` : score ≥ seuil → « 🟢 Stratégique », action « Fidéliser + négocier volume » ; `pilotage.py:509`. Ordre : > `score_standard`. |
| `score_standard` (101) | Score — Standard | nombre ; 65 ; 0–100 ; /100 | — | `moteur.py:2892` : → « 🟡 Standard », « Maintenir relation ». |
| `score_surveiller` (102) | Score — ATTENTION | nombre ; 45 ; 0–100 ; /100 | — | `moteur.py:2894` : → « 🟠 À surveiller », « Audit qualité + relance » ; en dessous « 🔴 À challenger », « Chercher alternative ». Ordre : < `score_standard`. |

### 3.6 Stock et inventaire (`INVENTAIRE`)

Pas d'aide de famille à l'écran (`AIDES_FAMILLE` n'a pas d'entrée « Stock et inventaire »).

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `seuil_rebut` (**PRO**, révision 0009) | Seuil de rebut | nombre ; 0,1 ; 0–1000 ; kg | « Sous ce poids (100 g par défaut), ce qui reste d'un lot dans un magasin est un « fond de lot » : la proposition « Envoyer aux machines » ne le propose plus (il reste en stock, compté et valorisé), il est marqué dans le Stock et sur le téléphone, et « Mettre au rebut » le sort du stock par un ajustement au motif « Rebut ». 0 = désactivé : aucun fond de lot. » | **Absent de Gestion MP** (décision de Mohamed du 15/10/2026, DECISIONS U22). `services/fonds_de_lot.seuil` ; lu par `lots.lister` (107, marque), `lots_lecture.disponibles` (111), `ordres/proposition` (134, saute le fond), `operations/rebut` (258, refus au-dessus du seuil hors direction). |
| `tolerance_inventaire` (94) | Tolérance d'écart d'inventaire | nombre ; 0,02 ; 0–100 ; % | « Proposée à l'ouverture d'un inventaire : au-delà, un écart de comptage se justifie avant la validation. » | `inventaires.py:182` (`GET /inventaires/defauts`) ; `inventaires.py:289` : défaut de la tolérance d'un inventaire ouvert (`POST /inventaires`), **chaque inventaire peut en porter une autre** et la garde. |

### 3.7 Prix (`PRIX`)

Aide de famille : « Ce qui colore la matrice des prix (forte hausse), borne la comparaison des
opportunités (deux prix de la même époque) et calcule la TVA attendue d'un dossier d'importation. »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `seuil_hausse_forte` (103) | Forte hausse de prix à partir de | nombre ; 0,05 ; 0,5–1000 ; % | — | `pilotage.py:397` (nombre de fortes hausses de l'historique des prix), `:333,399,493` (seuils renvoyés aux écrans opportunités, historique, matrice : `{"stable": 0.005, "forte": seuil}`). Borne basse 0,5 % = seuil « stable » en dur. |
| `fenetre_prix_jours` (105) | Écart maximal entre deux prix comparés | nombre ; 90 ; 1–3650 ; jours | « Deux prix ne se comparent qu'à la même époque. » | `moteur.py:2216` (`comparer_les_prix` : le prix rival doit être à ≤ N jours du dernier prix payé) ; `pilotage.py:294` (`GET /opportunites`, **surchargeable par `?fenetre_jours=`**). |
| `taux_tva_import` (107) | TVA à l'importation | nombre ; 0,2 ; 0–100 ; % | écran : « Le taux appliqué à la valeur en douane (marchandise, fret, assurance) augmentée des droits et de la TPI, pour la TVA attendue d'un dossier (contrôle C29). » | `moteur.py:3603` `tva_attendue` → C29 (`controles.py:810,823`) et fiche dossier `importations.py:298-300`. |
| `taux_tpi_import` (108) | Taxe parafiscale à l'importation (TPI) | nombre ; 0,0025 ; 0–10 ; % | « Sur la valeur en douane ; elle entre dans la base de la TVA attendue. » | `moteur.py:3602` : TPI = Σ frais « TPI » saisis, sinon valeur en douane × taux. |
| `seuil_surcout_import` (110) | Frais d'un dossier d'importation à vérifier au-delà de | nombre ; 1,0 ; 5–10 000 ; % | « Des frais hors TVA plus lourds que cette part de la marchandise sont signalés sur le dossier et dans les contrôles : ils fausseraient le coût moyen du stock. » | C35 (`controles.py:835-872`) ; fiche dossier `importations.py:222-223` (lignes aberrantes). |
| `toler_facture_import` (114) | Facture d'un dossier à rapprocher au-delà de | nombre ; 0,02 ; 0–100 ; % | « Une facture qui s'éloigne de plus de cette part de la marchandise reçue (pesée × prix) est signalée sur le dossier et dans les contrôles. » | `moteur.py:3720-3721` `ecart_facture` → C36 (`controles.py:879-895`) et fiche dossier. |

### 3.8 Trésorerie (`TRESO`)

Aide de famille : « Le délai client moyen entre dans le cycle de trésorerie du Cockpit (stock +
clients − fournisseurs). »

| Clé (ligne) | Libellé | Type / défaut / bornes / unité | Aide | Où il agit |
|---|---|---|---|---|
| `dso` (118) | Délai client moyen (DSO) | nombre ; 60 ; 0–3650 ; jours | — | `moteur.py:2554-2556` : Cockpit `finance.dso_jours` et `ccc_jours = DIO + DSO − DPO`. |

### 3.9 Société (`SOCIETE`) — tous texte, sans bornes (≤ 500 caractères)

Aide de famille : « Ce qui s'imprime sur les bons de commande, la période close (rien ne s'écrit plus
avant) et l'adresse que portent les QR des étiquettes. »

| Clé (ligne) | Libellé | Défaut | Aide | Où il agit |
|---|---|---|---|---|
| `nom_entreprise` (119) | Raison sociale | « » | — | Écran de connexion `GET /etat` (`comptes.py:57`) ; installation (`:92`) ; en-tête du bon HTML (`achats.py:976`, `:1058`) ; bon Excel FR (`exports.py:325`) ; bon fournisseur anglais Excel (`exports_achats.py:342`, repli « Raison sociale à régler (Réglages › Paramètres › Société) », « Deliver to / Company » `:372`) ; bilan du mois (`suivi.py:654`) ; sujet du courriel (`courriel.py:52`). |
| `forme_juridique` (120) | Forme juridique et capital | « » | « Sous la raison sociale, en tête des bons : « SOCIETE ANONYME AU CAPITAL DE 20 000 000 DH ». » | `achats.py:977-978`, `exports_achats.py:345`. |
| `secteur` (123) | Secteur | « Fabrication de tapis mécaniques » | « L'activité de l'usine (fiche de la société) ; l'en-tête des bons suit le papier à en-tête : raison sociale, forme et capital, siège, ville. » | `exports.py:326` (coordonnées du bon Excel FR). |
| `adresse` (126) | Siège social | « » | « En tête des bons (« SIEGE SOCIAL … ») et adresse de livraison. » | `achats.py:979-980,1134` ; `exports.py:326` ; `exports_achats.py:346,372` (« Address »). |
| `ville` (128) | Ville | « » | — | `achats.py:981,1134` ; `exports_achats.py:347,373` (« City »). |
| `telephone` (129) | Téléphone | « » | — | `achats.py:981` ; `exports.py:326` ; `exports_achats.py:347`. |
| `banques` (130) | Banques | « » | « En pied des bons, par exemple « ATTWAFA BANK : 90D012433 · B.M.C.I : 01063 000619 001 82 » (séparer les banques par « · »). » | `achats.py:990` (pied HTML), `exports_achats.py:409` (pied Excel) ; découpées sur « · ». |
| `ice` (133) | ICE | « » | — | Pied des bons `achats.py:995` (« ICE ») ; `exports.py:328` (« ICE »). |
| `rc` (134) | R.C | « » | — | `achats.py:995` (« R.C ») ; `exports.py:328` (« RC »). |
| `identifiant_fiscal` (135) | N.I.F (identifiant fiscal) | « » | — | `achats.py:995` (« N.I.F ») ; `exports.py:328` (« IF »). |
| `cnss` (136) | C.N.S.S | « » | — | `achats.py:995` (« C.N.S.S »). |
| `patente` (137) | Patente | « » | — | `achats.py:996` (« PATENTE »). |
| `date_cloture` (138) | Période close jusqu'au | « » | « Rien ne s'écrit plus à cette date ni avant. » | `securite.py:210-226` `date_permise` : refus « La période jusqu'au JJ/MM/AAAA est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir. » (appelée par achats, inventaires, opérations, production, réceptions, `services/stock.py`) ; `securite.py:229-232` `fin_de_periode_close` → `cout_hors_periode_close` (`:235+`) : un dossier d'import ou un poste de frais qui changerait la valeur d'un mois clos est refusé. |
| `courriel_destinataires` (140) | Courriel du lundi : à qui | « » | « Adresses séparées par des virgules. Vide : pas de courriel. Il part le lundi matin, dès que le serveur d'envoi est réglé (voir la notice). » | `courriel.py:73-99` `envoyer_si_lundi` (lundi, `GESTION_MP_SMTP_HOTE` réglé, liste non vide, pas déjà envoyé ce jour) ; aperçu `GET /courriel/apercu` (`suivi.py:850-859`). Aucune validation de format. |
| `adresse_publique` (143) | Adresse du serveur pour les téléphones | « » | « Ce que contiennent les QR des étiquettes, par exemple http://mac-usine:8030 (nom Tailscale, qui marche en Wi-Fi comme en 4G/5G). Vide : l'adresse du serveur sur le réseau de l'usine. » | `stock.py:332-345` `adresse_pour_telephone` (QR des étiquettes de lots, accès téléphone) ; validée `comptes.py:318-320`. |

**Total : 55 réglages** (3 + 10 + 4 + 6 + 9 + 1 + 6 + 1 + 15) : 40 numériques, 15 textes.

---

## 4. Clés hors déclaration dans la table `parametre` / `parametre_historique`

| Clé | Écrite par | Lue par | Remarque |
|---|---|---|---|
| `courriel_dernier_envoi` | `courriel.py:94-97` (date ISO, `modifie_par = "système"`) | `courriel.py:77-81` | Pas dans `REGLAGES` : absente de `GET /parametres`, refusée par `PUT` (« Paramètres inconnus ») ; sa mise à jour ne change pas `modifie_le` |
| `cours_<CODE>` (historique seulement) | `PUT /devises` (`comptes.py:442`) | `GET /devises` (`cours_le`), `GET /devises/{code}/historique`, et **aussi** `GET /parametres/historique` | Historique des cours de change dans la table des réglages |

---

## 5. Conversion vers le moteur (`pour_le_moteur`, `parametres.py:171-189`)

```text
p = Parametres()                          # défauts du moteur (modele.py:60-147)
pour chaque champ f de Parametres :
    si f.name est en base ET déclaré dans REGLAGES :
        défaut str → texte brut ; sinon float(texte), une valeur illisible est IGNORÉE (défaut du moteur)
p.methode = "corrigee"                    # le mode classeur n'est jamais actif en service
p.cours = {devise.code: devise.taux}      # toute la table devise (actives et inactives)
p.taux_eur_mad = cours["EUR"] si présent, sinon 11.0
p.taux_usd_mad = cours["USD"] si présent, sinon 9.5
```
`Parametres.taux(devise)` (`modele.py:139-147`) : `cours[devise]` si connu ; sinon EUR →
`taux_eur_mad`, USD → `taux_usd_mad` ; **toute autre devise (ou vide) → 1,0**. Appelé par
`depot.charger` (`depot.py:519`) et `importations.dossier_dict`.

### 5.1 Champs de `Parametres` (docstring : « Les 43 cellules nommées `P_*` du classeur »)

| Champ moteur | Défaut moteur | Réglage ? | Remarque |
|---|---|---|---|
| seuil_alerte, seuil_critique, delai_defaut, marge_securite, marge_jours, taux_perte, securite_a/b/c, seuil_dormant, seuil_abc_a/b, seuil_xyz_x/y, seuil_bc_urgent, seuil_bc_groupe, seuil_tier1/2/3, toler_in_full, toler_ecart_pesee, toler_poids_bobine, seuil_hausse_forte, fenetre_realisation_jours, plafond_stock_min_mois, fenetre_prix_jours, cible_otif, toler_retard_jours, taux_tva_import, taux_tpi_import, seuil_surcout_import, toler_facture_import, dso, croissance_annuelle, score_strategique/standard/surveiller | = défaut du réglage | oui | 36 champs remplis depuis la base |
| nom_entreprise | « » | oui | Rempli, **jamais lu** par le moteur |
| secteur | « » (réglage : « Fabrication de tapis mécaniques ») | oui | Rempli, **jamais lu** par le moteur |
| taux_eur_mad, taux_usd_mad | 11,0 ; 9,5 | non (table devise) | Lus par C11 et `taux()` |
| devise | « MAD » | non | **Jamais lu** |
| date_saisie | None | non | **Jamais lu** (`P_DateSaisie` du classeur) |
| methode | « corrigee » | non | Forcé « corrigee » ; « classeur » = parité de tests |
| cours | {} | non (table devise) | |

Réglages **non** présents dans `Parametres` (lus directement par `parametres.nombre` ou
`s.get(Parametre)`) : `seuil_approbation`, `toler_excedent`, `tolerance_inventaire`, et tous les
textes de la société sauf `nom_entreprise`/`secteur`, `date_cloture`, `courriel_destinataires`,
`adresse_publique`. `toler_in_full`, `toler_ecart_pesee` et `toler_retard_jours` sont lus **des deux
façons** (moteur et `nombre`).

---

## 6. Devises et cours

- Table `devise` (§ 1.1) ; défauts installés MAD 1,0 / USD 10,0 / EUR 10,8 (`main.py:45`).
- `PUT /devises` (`comptes.py:393-446`) : corps `{code (3 lettres, mis en majuscules), nom (≤ 40),
  taux (> 0, ≤ 10 000), actif}` ; crée la devise si absente ; si présente : **MAD doit rester à 1**
  (« Le dirham est la devise de référence : son cours reste 1. ») ; nom gardé si vide ; historise
  `cours_<CODE>` ; journal « cours de change » « CODE : x MAD ». Droit : achats + direction.
- Un **seul cours courant** par devise (pas de cours daté) ; mais le cours est **figé** sur chaque
  mouvement d'entrée (`mouvement.cours`), sur la commande à la première confirmation des prix
  (`achats.py:832`), et saisi par ligne de dossier d'import (`valeur_ligne_import`, `moteur.py:3611-3621`).
- Partout ailleurs (stock, ABC, plan d'achat, C38, montants), conversion au cours du jour
  (`Parametres.taux`).
- Contrôle : C11 (voir CONTROLES.md).

---

## 7. Réglages hors écran : variables d'environnement (`config.py`)

| Variable | Défaut | Effet |
|---|---|---|
| `GESTION_MP_FUSEAU` | Africa/Casablanca | Fuseau de toutes les dates (`TZ`) |
| `GESTION_MP_BASE` | `postgresql+psycopg:///gestion_mp` | Base ; son nom range sauvegardes et pièces dans un sous-dossier si ≠ gestion_mp |
| `GESTION_MP_PORT` | 8030 | Port |
| `GESTION_MP_HTTPS` | 0 | Cookie de session « secure » |
| `GESTION_MP_TACHES` | 1 | Tâches de fond (sauvegarde quotidienne, courriel) dans ce processus |
| `GESTION_MP_SAUVEGARDES` | `~/gestion-mp-sauvegardes[/<base>]` | Dossier des sauvegardes |
| `GESTION_MP_SAUVEGARDES_COPIE` | « » | Second dossier (disque externe) |
| `GESTION_MP_PG_BIN` | « » | Dossier de `pg_dump`/`psql` |
| `GESTION_MP_ECRAN` | `ecran/dist` | Écrans servis |
| `GESTION_MP_SESSION_JOURS` | 30 | Durée d'une session |
| `GESTION_MP_ERP_FIL` | `~/Library/Application Support/ERP Fil/gestion-fil.db` | Base de reprise (lecture seule) |
| `GESTION_MP_PIECES` | `~/gestion-mp-pieces[/<base>]` | Pièces jointes |
| `GESTION_MP_SMTP_HOTE`, `_PORT` (587), `_UTILISATEUR`, `_MOT_DE_PASSE`, `_EXPEDITEUR` | — | Serveur d'envoi du courriel du lundi (`courriel.py:27-28,84-93`) |

---

## 8. Constantes en dur qui mériteraient d'être des réglages (ou au moins documentées)

| Constante | Valeur | Où | Effet |
|---|---|---|---|
| `JOURS_PAR_MOIS` | 30 | `moteur.py:44` | Mois de 30 j dans toutes les fenêtres (prorata du mois en cours, horizon, couverture, sécurité) |
| `MOIS` | 12 | `moteur.py:43` | Horizon du plan glissant, fenêtre XYZ |
| `CROISSANCE_MINIMUM` | −0,9 | `moteur.py:45` | Double la borne basse du réglage `croissance_annuelle` |
| `TOLERANCE_RECETTE` | 0,01 point | `moteur.py:424` | Recette « à 100 % » (C01 et enregistrement) |
| `REALISATION_MINI`, `REALISATION_MAXI` | 0,5 ; 1,5 | `moteur.py:727` | Bornes du coefficient de réalisation (réel / plan) |
| `RECUL_DEBUT_JOURS` | 7 | `moteur.py:729` | Un mois ne juge le plan que si l'atelier sortait déjà du fil dans sa première semaine |
| `POUSSIERE` | 1e-3 kg | `moteur.py:732`, `services/stock.py:20` | Sous le gramme, un stock est nul |
| Seuils de statut | × 0,5 (CRITIQUE), × 1 (URGENT), × 1,2 (ATTENTION) du seuil d'alerte | `moteur.py:1302-1310` | Le statut qui décide de tout |
| Pondération du tri du plan d'achat | A × 3, B × 2 | `moteur.py:1652` | Ordre des lignes à commander |
| `POINTS_OTIF`, `POINTS_RETOURS`, `POINTS_DELAI` | 60 ; 20 ; 20 | `moteur.py:2808-2810` | Score fournisseur sur 100 |
| `RETOURS_SANS_POINT` | 5 % | `moteur.py:2812` | Part renvoyée à partir de laquelle les 20 points de retours tombent à 0 |
| Délai du score | 20 points jusqu'à 15 j, −1 point par 5 j au-delà | `moteur.py:2825` | Points de délai |
| Formule classeur du score | OTIF × 40 + (1 − retours) × 40 + délai | `moteur.py:2882-2884` | Mode classeur |
| `TOLERANCE_TVA_IMPORT` | 5 % | `moteur.py:3577` | Écart TVA saisie / attendue (C29, fiche dossier) |
| `POSTES_VALEUR_EN_DOUANE` | FRET, ASSUR | `moteur.py:3572` | Valeur en douane CAF |
| `TAUX_TVA_IMPORT` | 0,20 | `modele.py:536` | **Constante morte** (plus utilisée depuis `08c6df7`) |
| `RAPPORT_PRIX_ELOIGNE` | 3 | `controles.py:188` | C38 |
| Échéance par défaut d'un bon | 60 j après la commande | `controles.py:331` | C06 |
| Dossier « sans frais » | 30 j après l'arrivée | `controles.py:770` | C28 |
| Prix « stable » | ± 0,5 % | `pilotage.py:333,395,399,493` | Hausses / baisses de prix |
| Tolérance de confirmation des prix | 5 % | `achats.py:841` | Une confirmation de prix qui augmente de ≤ 5 % ne repasse pas en approbation |
| `ECHECS_TOLERES` | 5 | `securite.py:25,144-146` | Échecs de connexion avant blocage (30 s × 2^n, max 15 min) |
| `COEFFICIENT_MAXI` | 20 | `production_plan.py:38` | Coefficient de saisonnalité maximal |
| `JOURS_SORTIES` | 30 | `referentiels.py:1148` | « Sorti récemment » |
| `TAILLE_MAX` | 20 Mo | `suivi.py:234` | Pièce jointe |
| Largeur des numéros | 4 chiffres (lots internes « LOT-AAAA-NNNN » compris) | `securite.py:179,197`, `receptions.py:50-67` | « SERIE-AAAA-NNNN » |
| `ck_solde_positif` | −0,0005 | `modeles.py:479` | Solde jamais sous zéro |
| Dates permises | ≥ 2000-01-01, ≤ aujourd'hui ; date de référence 2000–2100 | `securite.py:213-218`, `pilotage.py:34` | |
| Devises installées | USD 10,0 ; EUR 10,8 | `main.py:45` | Cours de départ |
| Motifs et codes R1–R6 | listes en dur | `operations.py:36-53` | C03, traçabilité |
| Tolérance du vérificateur | 0,01 | `verificateur.py:35` | Vérification indépendante |

---

## 9. Points incohérents ou ambigus

1. **`seuil_critique` / `seuil_alerte` presque inertes** : ils ne règlent que le « statut classeur »
   (affiché pour comparaison), mais restent validés dans l'ordre et présentés en tête des réglages.
   Leur aide parle du « seuil d'alerte » (= `stock_min_recalcule`, une quantité calculée) alors que
   la clé du second réglage s'appelle justement `seuil_alerte` (une couverture en jours) : deux
   notions sous le même nom.
2. **`seuil_bc_urgent` inerte en service** (mode classeur seulement) ; l'écran le dit, le serveur le
   garde réglable.
3. **Pas de contrôle d'ordre** pour `seuil_tier1 ≥ seuil_tier2 ≥ seuil_tier3`, ni `seuil_bc_groupe`,
   ni entre tolérances ; `seuil_tier1` ne joue que pour la classe A (un montant ≥ tier1 d'une classe
   B tombe en Tier 2).
4. **Champs de `Parametres` jamais lus** : `devise`, `date_saisie`, et dans le moteur `nom_entreprise`,
   `secteur`. Docstring « 43 cellules » fausse. `TAUX_TVA_IMPORT` mort (`modele.py:536`).
5. **Défauts divergents** : `Parametres.secteur` « » contre « Fabrication de tapis mécaniques » ;
   taux EUR/USD 11,0/9,5 (moteur) contre 10,8/10,0 (devises installées).
6. **Valeurs illisibles avalées en silence** : `nombre()` rend le défaut, `pour_le_moteur` garde le
   défaut du moteur — une valeur corrompue en base n'est signalée nulle part.
7. **Droit de lecture large** : `GET /parametres` est ouvert à l'alimentation (société, seuils), alors
   que l'écran et le cahier des charges (`CAHIER-DES-CHARGES.md:116`, « — » pour l'alimentation) la
   tiennent à l'écart ; `GET /devises` aussi (des cours, pas des prix).
8. **Deux sources d'aide** (serveur et `AIDES_REGLAGE` de l'écran) : la plus riche (écran) est
   masquée pour 6 réglages ; 4 réglages n'ont d'aide nulle part (`score_*`, `seuil_hausse_forte`,
   `dso`) ; la famille « Stock et inventaire » n'a pas d'aide de famille ; les messages d'ordre de
   l'écran et du serveur diffèrent.
9. **`toler_ecart_pesee` a deux rôles** (seuil d'écart et seuil de « livraison partielle »), ce que le
   libellé ne dit pas.
10. **`tolerance_inventaire`** est déclarée famille « Stock et inventaire » mais placée au milieu des
    réglages de réception dans la liste.
11. **Bornes très larges** pour des % : `toler_excedent` jusqu'à 1000 %, `seuil_surcout_import`
    jusqu'à 10 000 %, `marge_securite` 500 %, `croissance_annuelle` 1000 %.
12. **Historique mêlé** : `/parametres/historique` rend aussi les cours de devises (`cours_XXX`) sous
    leur clé brute ; la valeur « avant » se recalcule en relisant tout l'historique (O(n)) mais seuls
    les 500 derniers sont rendus.
13. **`date_cloture`** : la réouverture (valeur vidée) ou le recul de la date est permis sans autre
    garde que le droit direction (historisé) ; pas de vérification « nouvelle date ≥ ancienne ».
14. **`courriel_destinataires`** sans validation d'adresses ; **`courriel_dernier_envoi`** clé cachée
    dans la même table.
15. **Devises** : MAD n'est forcé à 1 que s'il existe déjà (une base sans MAD l'accepterait à un autre
    cours) ; pas de suppression ; un seul cours courant (non daté), ce que
    `conformite/2-regles-calculs-api.md` signale comme manque.
16. **`fenetre_prix_jours` surchargeable** par la requête (`?fenetre_jours=`) : l'écran peut donc
    afficher une comparaison qui ne suit pas le réglage.
17. **`seuil_approbation`** compare un montant en MAD au cours figé du bon, mais la hausse se mesure
    dans la devise du bon (tolérance 5 % en dur à la confirmation des prix) : deux unités dans la
    même règle.
18. **Méthode « classeur »** : l'écran affirme qu'elle « n'existe plus » alors que tout le moteur
    garde ses branches (`mode_classeur`) ; `pour_le_moteur` force « corrigee ». À décider pour la
    réécriture : garder une parité de tests ou supprimer.
19. **`croissance_annuelle`** : la borne −90 % est dupliquée (réglage et `CROISSANCE_MINIMUM`) ; la
    branche classeur (`moteur.py:225`) n'applique pas le plancher.
20. **`seuil_hausse_forte`** a une borne basse (0,5 %) égale au seuil « stable » codé en dur : la
    relation est implicite.
