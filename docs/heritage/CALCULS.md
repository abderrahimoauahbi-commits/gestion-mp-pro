# CALCULS — partie A : modèle, classification, plan, besoins, stock, plan d'achat, dépôt, écriture du stock

> Inventaire de **Gestion MP** (`/Users/mohamed/gestion-mp`, commit `2d588b9` du 2026-10-08) pour la
> réécriture **Gestion MP PRO**. Source de vérité : le code. Toutes les références sont
> `chemin:ligne` relatives à `gestion_mp/`.
> Périmètre : `calcul/modele.py` (entier), `calcul/classification.py` (entier),
> `calcul/moteur.py` lignes 1 à 1780 (jusqu'au plan d'achat inclus ; la valorisation/CMUP, le
> cockpit, le DIO et la suite sont dans la partie B), `depot.py` (entier), `services/stock.py`
> (entier).
> Objectif : qu'une équipe puisse reconstruire ces calculs **à l'identique** sans relire
> l'ancien code (une parité de calcul sera testée).

---

## 0. À lire d'abord

### 0.1 Deux méthodes : « corrigée » (la seule en service) et « classeur » (parité tableur)

Le moteur porte un interrupteur `Parametres.methode` (`calcul/modele.py:131`) :

- `"corrigee"` (défaut) : les corrections décidées après l'audit du classeur Excel d'origine
  (et de l'ERP Fil, qui le reproduisait). **Gestion MP force toujours cette méthode** :
  `parametres.pour_le_moteur` écrit `p.methode = "corrigee"` quoi que dise la base
  (`parametres.py:185`). Le réglage « méthode » est déclaré ABANDONNÉ
  (`docs/INVENTAIRE-ERP-FIL.md:986`, `:1329`).
- `"classeur"` (`Parametres.mode_classeur`, `calcul/modele.py:135-137`) : reproduit le tableur à
  l'identique. Il ne sert plus qu'aux tests de parité avec le classeur et à la comparaison
  « moteur à interrupteurs » avec l'ERP Fil (`docs/AUDIT-2026-10-08.md`, `docs/COMPARAISON-ERP-FIL.md`).

**Pour la parité PRO ↔ Gestion MP, la cible est la méthode corrigée.** Les branches « classeur »
sont documentées ci-dessous (repérées **[classeur]**) pour que rien ne se perde et pour
expliquer d'où vient chaque correction ; PRO peut décider de ne pas les reprendre.

Ce qui relève du « mode classeur » au sens large (approximations héritées du tableur, présentes
**aussi** en méthode corrigée) :

| Héritage du classeur | Où | Pourquoi il reste |
|---|---|---|
| Mois de **30 jours** (`JOURS_PAR_MOIS = 30`) dans toutes les fenêtres de demande, la couverture en jours, les jours de sécurité, les jours restants du mois | `moteur.py:44`, `:605-608`, `:852`, `:1160-1164`, `:1233-1234`, `:1262`, `:1266`, `:1323` | Le classeur raisonne en mois de 30 j ; le plan est mensuel. Seule exception : `m2_passe` proratise sur la vraie durée du mois (secondes). |
| `arrondi` = ARRONDI d'Excel (demi vers l'extérieur), pas l'arrondi bancaire de Python | `moteur.py:52-60` | Sans lui le plan de production décalait d'un m² sur les demis exacts. |
| Plan glissant de **12 mois** (`MOIS = 12`), M0 = mois en cours | `moteur.py:43`, `:77-79` | Feuille `Production_Plan`. |
| Classe ABC au cumul « ≥ la mienne », seuils 80/95 %, RANG d'Excel | `moteur.py:1495-1528` | Formule `Stock!AA10`. |
| XYZ = coefficient de variation population (÷ 12) | `moteur.py:1446-1461` | `Stock!AF10`. |
| Tiers, montants seuils, libellés emoji des statuts et actions | `moteur.py:1605-1634`, `modele.py:41-57` | `Plan_Achat`. |
| Délai par défaut seulement pour un fournisseur **inconnu** (un fournisseur connu à 0 j reste à 0) | `modele.py:741-750` | `IFERROR` du classeur. |
| Taux de perte appliqué aux besoins (dans les deux modes) | `moteur.py:469` | `Production_Besoins!U6`. |

### 0.2 Décisions structurantes (à reprendre telles quelles)

| Décision | Traduction dans le calcul | Source |
|---|---|---|
| **Le stock est toujours en kilos**, cuir, franges et ruban compris | `Mouvement.quantite` en kg (`modele.py:328`) ; aucun total en ml | Décision de Mohamed du 8 oct. 2026, commit `d2e1e39` |
| **Le prix se saisit au kilo (défaut) ou au mètre** ; tous les calculs le lisent au kilo | `Article.prix_kg = prix_unite / densite` si `unite_prix == "ml"` (`modele.py:242-249`) | `d2e1e39` |
| **La recette des rôles au mètre (Cuir, Franges, Ruban) est en ml/m²**, ramenée en kg/m² par la densité (kg/ml) | `poids_du_role` × `article.densite` (`moteur.py:318-332`) | `d2e1e39` |
| Les mètres ne sont qu'**indicatifs** (kilos ÷ densité) | `Article.kg_par_ml`, `LigneStock.kg_par_ml`, `quantite_a_commander_achat`, `services/stock.kg_et_metres` | `d2e1e39`, `b75bc24` |
| **Stock en magasin ou en machine** : le fil monté sur les métiers, pas encore tissé, est compté dans le disponible, le stock projeté (donc les achats) **et** valorisé | `stock_disponible = stock_net − quarantaine + stock_machine` (`moteur.py:1188`), `stock_projete` (`:1157`) ; valeur : partie B | Décision de Mohamed, commits `f33a428` puis `169dfdc` (le second a ajouté la valeur ; `202d1a0` l'avait d'abord exclu) |
| **La quarantaine est en stock (et valorisée) mais hors du disponible et hors des achats** | `bloque` retiré du disponible et du projeté (`moteur.py:1154-1157`) ; les magasins de type `"Quarantaine"` (`modele.py:646`) | Ajout de Gestion MP (`docs/conformite/2-regles-calculs-api.md` constat d'ensemble) |
| **Le passé se juge sur le plan et les recettes de son époque** | `versions_plan`, `versions_recette`, `m2_passe`, `besoins_passes` | commit `db25831` |
| Le réel corrige le plan (coefficient de réalisation borné 0,5–1,5 sur les mois clos) | `etat_stock` `moteur.py:859-1090` | ERP Fil, puis `db25831`, `30b31c3` |
| Un bon en brouillon / à approuver **n'engage rien** (ni stock attendu, ni retard) mais **n'est pas reproposé** | `pas_partie` (`modele.py:400-405`), `bc_en_preparation` (`moteur.py:1358`) | `30b31c3`, `9ed7831` |
| Ce qui ne se consomme plus (matière ou fournisseur désactivé, ni recette ni sortie) **ne se rachète pas** | `sans_achat` (`moteur.py:1359-1368`) | `30b31c3` |
| Une annulation est une **contre-passation** datée comme l'original | `services/stock.contrepasser_document` (`:230-270`) | `61027e4`, `673c02c` |
| Le **cours de la devise est figé sur chaque mouvement** à l'écriture | `services/stock.ecrire` (`:181-186`) | `eb7546e` |
| Aucune écriture ne fait passer un lot sous zéro **à sa date ni après** | `services/stock.couvert_a_sa_date` (`:77-119`) | audit 2-G B1, `61027e4` |
| « Sous le gramme, c'est zéro » (`POUSSIERE = 1e-3` kg) | `moteur.py:732`, `services/stock.py:20` | — |

### 0.3 Conventions de ce document

- `Σ` somme, `max/min` usuels, `⌈x⌉` plafond, `clamp(x, a, b) = min(b, max(a, x))`.
- « mois de plan i » : i = 0 pour le mois de `date_ref` (M0), … 11.
- Les quantités sont en **kg** sauf mention ; les montants en devise de la matière, `_mad` = en dirhams.
- `taux(devise)` = `Parametres.taux` (§1.2).

---

## 1. `calcul/modele.py` — les structures du moteur

Le module ne contient que des structures, indépendantes de la base (`modele.py:1-12`). Le
moteur les reçoit telles quelles : depuis PostgreSQL via `depot.py` (Gestion MP), ou depuis le
classeur (tests de parité). Les types de mouvement sont des **codes stables**, pas les libellés
emoji (une comparaison de chaîne emoji ratée casse un total sans prévenir).

### 1.1 Constantes

| Constante | Valeur | Ligne | Rôle |
|---|---|---|---|
| `ROLES` | `("Poil", "Chaîne", "Trame", "Colle", "Cuir", "Franges", "Ruban", "Plastique")` | `:23` | Les 8 rôles de nomenclature. |
| `ROLES_LINEAIRES` | `("Cuir", "Franges", "Ruban")` | `:24` | Rôles dont la qualité dit des **ml/m²** ; × densité (kg/ml) = kg/m². |
| `TYPES_MOUVEMENT` | code → (libellé classeur, signe) | `:28-37` | voir tableau ci-dessous |
| `LIBELLE_VERS_CODE` | libellé → code | `:39` | Lecture du classeur. |
| `STATUTS` | `RUPTURE "⚫ RUPTURE"`, `CRITIQUE "🔴 CRITIQUE"`, `URGENT "🟠 URGENT"`, `ATTENTION "🟡 ATTENTION"`, `OK "🟢 OK"`, `SANS_CONSO "⚪ NON CONSOMMÉE"` | `:41-48` | Statut d'une matière. **Les libellés emoji sont les valeurs** (comparées telles quelles). |
| `STATUTS_EN_ALERTE` | RUPTURE, CRITIQUE, URGENT, ATTENTION | `:52-57` | « NON CONSOMMÉE » n'est pas une alerte. |
| `STATUTS_BC_CLOS` | `("Soldée", "Annulée")` | `:397` | Un bon clos n'attend plus rien. |
| `POSTES_IMPORT` | code → (libellé, récupérable) | `:518-534` | voir §1.17 |
| `TAUX_TVA_IMPORT` | `0.20` | `:536` | Doublon historique du réglage `taux_tva_import`. |
| `QUARANTAINE` | `"Quarantaine"` | `:646` | Le **type** de magasin qui retient la marchandise sous réserve. |

Types de mouvement du moteur et correspondance avec Gestion MP (`modeles.py:486-494`) :

| Code moteur | Libellé classeur | Signe | Type Gestion MP |
|---|---|---|---|
| `STOCK_INITIAL` | 📥 Stock Initial | +1 | `OUVERTURE` |
| `ENTREE_RECEPTION` | 📦 Entrée Réception | +1 | `RECEPTION` |
| `SORTIE_PROD` | 📤 Sortie Prod | −1 | `SORTIE` (vers les machines) |
| `RETOUR_PRODUCTION` | 🔄 Retour Production | +1 | `RETOUR_MACHINE` |
| `RETOUR_FOURNISSEUR` | ↩️ Retour Fournisseur | −1 | `RETOUR_FOURNISSEUR` |
| `AJUSTEMENT_INVENTAIRE` | ⚖️ Ajustement Inventaire | +1 | `AJUSTEMENT` |
| `TRANSFERT_MAGASIN` | 🔀 Transfert Magasin | 0 | `TRANSFERT` (deux lignes appariées en base, une seule pour le moteur) |
| `QUARANTAINE` | 🚫 Quarantaine | 0 | **jamais produit par Gestion MP** : la mise en quarantaine est un transfert vers un magasin de type `Quarantaine` |

Signe inconnu → +1 (`Mouvement.signe`, `modele.py:349-351`).

### 1.2 `Parametres` (`modele.py:60-148`)

« Les 43 cellules nommées `P_*` du classeur » (le docstring ; la classe compte en fait 45 champs
avec `methode` et `cours`). Chargé par `parametres.pour_le_moteur` (`parametres.py:171-189`) :
pour chaque champ qui a un réglage en base (`PAR_CLE`), la valeur stockée en texte est convertie
en `float` (ou laissée en texte si le défaut du réglage est un texte) ; une valeur non
convertible (ex. `""`) **garde le défaut de la dataclass** ; puis `methode = "corrigee"`,
`cours = {code devise: taux}` de la table `devise`, `taux_eur_mad = cours.get("EUR", 11.0)`,
`taux_usd_mad = cours.get("USD", 9.5)`.

| Champ | Défaut | Réglage (bornes, unité) | Utilisé dans la partie A |
|---|---|---|---|
| `seuil_alerte` | 90 | 1–3650 j | `statut_couverture` (ATTENTION) |
| `seuil_critique` | 60 | 1–3650 j | `statut_couverture` (CRITIQUE) |
| `delai_defaut` | 60 | 1–730 j | `Donnees.delai_fournisseur` (fournisseur inconnu) |
| `marge_securite` | 0,20 | 0–5 (saisi en %) | `stock_min_recalcule` (× couv_min) |
| `marge_jours` | 30 | 0–730 j | `Donnees.couverture_commande` (à défaut du pas du fournisseur) |
| `taux_perte` | 0,02 | 0–0,5 | besoins, besoins passés, coût au m² (corrigé) |
| `securite_a`, `securite_b`, `securite_c` | 30, 30, 30 | 0–365 j | `_jours_securite` |
| `seuil_dormant` | 180 | 1–3650 j | dormants |
| `seuil_abc_a`, `seuil_abc_b` | 0,80, 0,95 | 0–1 | `_classer_abc` |
| `seuil_xyz_x`, `seuil_xyz_y` | 0,25, 0,50 | 0–10 | classe XYZ |
| `seuil_bc_urgent` | 300 000 | MAD | urgence fournisseur **[classeur]** |
| `seuil_bc_groupe` | 100 000 | MAD | « BC groupé » |
| `seuil_tier1`, `seuil_tier2`, `seuil_tier3` | 300 000, 200 000, 100 000 | MAD | `_tier` |
| `toler_in_full` | 0,02 | 0–0,2 | `reste_a_livrer` |
| `toler_ecart_pesee` | 0,02 | 0–1 | `LigneReception.tolerance_partielle` (via le dépôt) |
| `toler_poids_bobine` | 0,05 | 0–1 | (partie B : pesées) |
| `seuil_hausse_forte` | 0,05 | 0,005–10 | (partie B) |
| `fenetre_realisation_jours` | 90 | 0–730 j | fenêtre du coefficient de réalisation ; 0 = plan seul |
| `plafond_stock_min_mois` | 3 | 0–60 mois | plafond du stock minimum ; 0 = pas de plafond |
| `fenetre_prix_jours` | 90 | 1–3650 j | (partie B) |
| `cible_otif` | 0,95 | 0–1 | (partie B) |
| `toler_retard_jours` | 0 | 0–60 j | (partie B, OTIF) |
| `taux_tva_import` | 0,20 | 0–1 | (partie B) |
| `taux_tpi_import` | 0,0025 | 0–0,1 | (partie B) |
| `seuil_surcout_import` | 1,0 | 0,05–100 | (partie B) |
| `toler_facture_import` | 0,02 | 0–1 | (partie B) |
| `taux_eur_mad` | 11,0 | — (remplacé par `cours["EUR"]`) | `taux("EUR")` à défaut de `cours` |
| `taux_usd_mad` | 9,5 | — (remplacé par `cours["USD"]`) | `taux("USD")` à défaut de `cours` |
| `devise` | `"MAD"` | non chargé (`reprise.py:37`) | inutilisé ici |
| `dso` | 60 | 0–3650 j | (partie B, cycle de trésorerie) |
| `date_saisie` | `None` | non chargé | inutilisé |
| `croissance_annuelle` | 0,0 | **−0,9**–10 | `plan_mensuel`, `m2_du_mois` (bornée à −0,9 dans le calcul) |
| `score_strategique`, `score_standard`, `score_surveiller` | 85, 65, 45 | /100 | (partie B) |
| `nom_entreprise` | `""` | texte | — |
| `secteur` | `""` | texte (défaut du réglage : « Fabrication de tapis mécaniques ») | — |
| `methode` | `"corrigee"` | forcé | `mode_classeur` |
| `cours` | `{}` | table `devise` | `taux()` |

Réglages qui **n'entrent pas** dans `Parametres` (lus ailleurs, pas par le moteur) :
`seuil_approbation`, `toler_excedent`, `tolerance_inventaire`, `date_cloture`, les champs société
(`forme_juridique`, `adresse`, `ville`, `telephone`, `banques`, `ice`, `rc`, `identifiant_fiscal`,
`cnss`, `patente`), `courriel_destinataires`, `adresse_publique` (`parametres.py:42-160`).

**`Parametres.taux(devise)`** (`modele.py:139-148`) — change vers le dirham :

```
si devise non vide et devise ∈ cours : cours[devise]
sinon si devise == "EUR" : taux_eur_mad
sinon si devise == "USD" : taux_usd_mad
sinon : 1.0          (MAD, vide, ou devise inconnue)
```

### 1.3 `Fournisseur` (`modele.py:151-164`)

Champs : `nom` (clé de rapprochement partout dans le moteur), `code`, `contact`, `telephone`,
`email`, `pays`, `delai_jours` (0), `conditions_paiement`, `devise` ("MAD"),
`delai_paiement_jours` (0), `couverture_commande_jours` (0 = « à défaut, la marge générale »),
`actif` (True).

### 1.4 `Article` (`modele.py:167-255`)

Une ligne du catalogue ; l'identifiant de tout le système est `reference`.

| Champ | Défaut | Sens |
|---|---|---|
| `reference` | — | identifiant |
| `role_bom` | `""` | un des `ROLES` |
| `nature` | `""` | libellé de la composition (le dépôt y met `Composition.libelle`) |
| `designation` | `""` | |
| `titrage` | `None` | valeur du titrage (texte ou nombre) |
| `fournisseur` | `""` | **nom** du fournisseur |
| `prix_unite` | 0,0 | prix du catalogue **dans son unité** |
| `unite_prix` | `"kg"` | `"kg"` ou `"ml"` |
| `devise` | `"MAD"` | devise du prix |
| `stock_min` | 0,0 | stock minimum du catalogue (kg) |
| `couv_min_mois` | 0,0 | couverture minimale en mois |
| `poids_bobine` | 0,0 | kg par bobine (catalogue) |
| `bob_palette` | 0,0 | bobines par palette |
| `unite_commande` | `""` | unité d'achat déclarée (palette, fût, sac…) |
| `contenance_commande` | 0,0 | kg par unité d'achat déclarée |
| `minimum_commande` | 0,0 | minimum de commande (kg) |
| `actif` | True | |
| `densite` | 0,0 | **kg par mètre linéaire** (obligatoire pour un rôle au mètre ou un prix au mètre, contrôlé à la saisie) |
| `groupe_equiv` | `""` | groupe d'équivalence (substituts, sourcing) |
| `priorite_equiv` | `None` | priorité dans le groupe (0–100) — **non utilisée par le moteur** |
| `composition`, `type_fil`, `couleur`, `couleur_code`, `titrage_unite` | `""` | classification (recherche) |

Propriétés dérivées :

- **`contenance_palette`** (`:206-209`) = `(poids_bobine or 0) × (bob_palette or 0)` ; 0 si non renseigné.
- **`conditionnement`** (`:211-226`) → `(unité, kg par unité)` :
  1. si `unite_commande` non vide **et** `contenance_commande > 0` → `(unite_commande, contenance_commande)` ;
  2. sinon si `contenance_palette` ≠ 0 → `("Palette", contenance_palette)` ;
  3. sinon si `poids_bobine` ≠ 0 → `("Bobine", poids_bobine)` ;
  4. sinon `("kg", 1.0)`.
  (Une colle en fûts de 200 kg se **déclare**, elle ne se devine pas.)
- **`unites_de_commande()`** (`:228-240`) : liste dédoublonnée par nom d'unité, dans l'ordre
  `kg (1)`, `Bobine (poids_bobine)` si connu, `Palette (contenance_palette)` si connue, l'unité
  déclarée si `contenance_commande > 0` ; un nom répété garde **la dernière** contenance mais
  **la première position** (dict Python).
- **`prix_kg`** (`:242-249`) — le prix de **tous** les calculs :
  `prix_kg = prix_unite / densite` si `unite_prix == "ml"` (0 si `densite` = 0), sinon `prix_unite`.
  Exemple : 0,5 USD/m d'un cuir de 0,014 kg/ml → 0,5 / 0,014 = **35,71 USD/kg**.
- **`kg_par_ml`** (`:251-255`) = `densite` (ou 0) si `role_bom ∈ ROLES_LINEAIRES`, sinon 0. Sert
  aux mètres **indicatifs** (kg ÷ kg_par_ml). Attention : un prix au mètre sur un rôle **non**
  linéaire utilise `densite` pour `prix_kg`, mais `kg_par_ml` vaut 0.

### 1.5 `Qualite`, `LigneRecette` (`modele.py:258-271`)

- `Qualite(code, nom, poids: dict[rôle → valeur])` : **kg/m²** pour les rôles au poids, **ml/m²**
  pour Cuir, Franges, Ruban.
- `LigneRecette(qualite, reference, pourcentage)` : part (en %, 0–100) de la référence dans **son
  rôle** pour cette qualité.

### 1.6 `PlanQualite` (`modele.py:274-287`)

`qualite`, `base_mensuelle` (m²/mois), `saisonnalite` (12 coefficients janvier → décembre, défaut
1,0), `actif` (une qualité arrêtée garde sa base mais ne compte plus pour les mois à venir),
`depuis` (jour de saisie de la base : origine de la croissance).

### 1.7 `VersionPlan` (`modele.py:290-303`)

Le plan d'une qualité en vigueur **à partir de** `quand` (datetime ; `None` = « depuis toujours »,
le plan d'avant le premier changement enregistré) : `base_mensuelle`, `saisonnalite`, `actif`,
`depuis`.

### 1.8 `VersionRecette` (`modele.py:306-314`)

Recette d'une qualité enregistrée à `quand` : `lignes = [(référence, %)]`, `poids` = poids au m²
des rôles relevés avec elle, ou `None` (versions anciennes qui ne les gardaient pas).

### 1.9 `Mouvement` (`modele.py:317-355`, `slots=True` pour 300 000 écritures)

| Champ | Sens |
|---|---|
| `date` | date d'effet |
| `type` | code de `TYPES_MOUVEMENT` |
| `reference` | article |
| `quantite` | **kg**, normalement positive, le signe porté par le type ; **une contre-passation a une quantité négative** (voir §4.6) |
| `prix_unite`, `devise`, `total_devise` | prix d'entrée dans sa devise ; `total_devise = quantite × prix` (dépôt) |
| `reference_doc` | numéro du document |
| `lot_fournisseur` | numéro de lot (le moteur range les mouvements sans lot sous `SANS_LOT = "(sans lot)"`, `moteur.py:49`) |
| `magasin_source`, `magasin_destination` | codes de magasin |
| `numero_of` | numéro d'ordre de fabrication |
| `motif_retour` | code R1…R6 |
| `utilisateur`, `fournisseur` | auteur ; fournisseur du lot |
| `id` | identifiant base |
| `contrepasse_id` | l'écriture qu'annule celle-ci (elle la défait **au même coût**) |
| `cours` | cours de la devise figé à la validation (0 : inconnu, celui du jour s'applique) |
| `ligne_reception_id` | ligne de réception qui a écrit cette entrée (sert aux dossiers d'importation) |

`signe` = signe du type (+1 si inconnu) ; `quantite_signee = quantite × signe`.

### 1.10 `LigneCommande`, `Commande` (`modele.py:358-394`)

`LigneCommande` : `numero_bc`, `reference`, `quantite_commandee`, `quantite_recue` (le dépôt y met
le **reçu net** des retours, §4.4), `prix_unite`, `devise`, `prix_confirme`, `unite_commande`
("kg"), `contenance_commande` (1,0), `prix_estime` (prix confirmé, sinon catalogue converti dans
la devise du bon), `cours` (cours figé du bon, 0 = du jour).

`Commande` : `numero`, `date_bc`, `fournisseur`, `date_livraison_prevue` (date **promise**, juge la
ponctualité), `statut`, `observations`, `lignes`, `eta` (arrivée attendue, déplace la prévision
et l'alerte « en retard », jamais la note du fournisseur), `solde_a_la_main_le`.
**`arrivee_attendue`** = `eta or date_livraison_prevue` (`:392-394`).

### 1.11 `pas_partie(commande, parametres)` (`modele.py:400-405`)

```
pas_partie = (commande.statut == "Brouillon") ET NON mode_classeur
```

Un brouillon (ou un bon sans numéro qui attend l'approbation — le dépôt le traduit en
« Brouillon ») n'est pas chez le fournisseur : il n'engage ni stock attendu, ni retard, ni montant
à payer. Un bon **parti** (il a un numéro) qui repasse par la direction reste parti (§4.1).
**[classeur]** un brouillon comptait comme commandé.

### 1.12 `reste_a_livrer(commande, ligne, parametres)` (`modele.py:408-424`)

```
reste = quantite_commandee − quantite_recue
[classeur] → max(0, reste)
si commande.statut ∈ {"Soldée", "Annulée"} → 0
si reste ≤ quantite_commandee × toler_in_full → 0      (livré « in full » ; couvre aussi le sur-livré, reste < 0)
sinon → reste
```

Exemple : 10 000 kg commandés, 9 954 kg pesés, tolérance 2 % → reste 46 ≤ 200 → **0** (livré).
Note : `toler_in_full` est borné à 20 % côté réglage (au-delà un bon entamé passerait pour livré).

### 1.13 `LignePrix` (`modele.py:427-437`)

Un prix d'achat réellement pratiqué : `date_bc` (le dépôt y met la **date de réception**),
`reference`, `fournisseur`, `numero_bc`, `quantite` (pesée), `prix_achat`, `devise`.

### 1.14 `LigneReception` (`modele.py:440-497`)

Une pesée : **la quantité pesée fait foi**, pas le BL. Champs : `reference`, `lot_fournisseur`,
`quantite_commandee` (le dépôt y met `quantite_attendue` de la ligne = le reste à livrer
attendu), `quantite_bl`, `quantite_pesee`, `nb_bobines` (total de la ligne), `nb_palettes` (pour
mémoire), `magasin`, `statut_qualite` ("Conforme" | "Réserve" | "Refusé"), `observations`,
`numero_bc` (le bon de la ligne : un camion peut livrer plusieurs bons), `tolerance_partielle`
(le dépôt y met le réglage `toler_ecart_pesee` ; `None` = règle du classeur).

- **`quantite_attendue`** (`:461-479`) :
  ```
  si quantite_bl ≠ 0 → quantite_bl
  si tolerance_partielle n'est pas None ET quantite_pesee < quantite_commandee × (1 − tolerance_partielle)
        → 0            (livraison partielle sans BL : rien à quoi se comparer)
  sinon → quantite_commandee
  ```
  Règle partagée par l'écran de réception, le contrôle C08 et l'archive des pesées.
- **`ecart`** (`:481-485`) : si `quantite_attendue == 0` et `tolerance_partielle` non `None` → 0 ;
  sinon `quantite_pesee − quantite_attendue` (avec la règle classeur et rien d'attendu :
  `ecart = pesée`).
- **`ecart_relatif`** (`:487-491`) : `None` si rien d'attendu, sinon `ecart / quantite_attendue`.
- **`poids_moyen_bobine`** (`:493-497`) : `None` si `nb_bobines` = 0, sinon `quantite_pesee / nb_bobines`.

Exemple : commandé 5 000, pas de BL, pesé 2 000, tolérance 2 % → 2 000 < 4 900 → attendu 0, écart 0
(partielle). Pesé 4 950 → attendu 5 000, écart −50, relatif −1 %.

### 1.15 `Reception` (`modele.py:500-512`)

`numero`, `date_reception`, `numero_bc` (le dépôt ne le remplit que si toutes les lignes sont du
même bon), `fournisseur`, `numero_bl`, `numero_facture`, `receptionnaire`, `controleur_qualite`,
`statut` ("Brouillon" | "Validée"), `lignes`, `validee_le`.

### 1.16 `POSTES_IMPORT`, `ChargeImport`, `LigneImport`, `DossierImport` (`modele.py:515-603`)

Postes (ordre du classeur « IMPORTATION 2026 ») — code : libellé, récupérable :
`DD` Droits de douane (non) · `TPI` Taxe parafiscale à l'importation (non ; 0,25 % de la valeur en
douane, entre dans la base de la TVA attendue) · `TVA` TVA à l'importation (**oui** : pèse sur la
trésorerie, jamais sur le coût de revient) · `PORT` Port Med · `FRET` Fret · `ASSUR` Assurance
(entre dans la valeur en douane CAF) · `TRANSIT` Transitaire · `TIMBRE` Timbre · `INT_OC` Intérêts /
ordre de change · `TMSA` TMSA · `AUTRE` Autre frais (tous non récupérables).

- `ChargeImport` : `poste`, `montant`, `ligne` (rattache le frais à une seule marchandise),
  `piece`, `commentaire`, `recuperable_poste` (référentiel des postes, l'emporte), `cle`
  (`"valeur"` ou `"poids"`), `parts` (répartition figée ligne → montant, l'emporte tant qu'elle
  couvre tout le frais). **`recuperable`** = `recuperable_poste` s'il est renseigné, sinon la
  colonne de `POSTES_IMPORT`, sinon False.
- `LigneImport` : `id`, `reference`, `quantite`, `valeur_devise`, `devise`, `cours`,
  `lot_fournisseur`, `fournisseur`, `ligne_reception_id`, `commentaire` ; **`poids_kg`** = `quantite`.
- `DossierImport` : `numero`, `libelle`, `date_arrivee`, `banque`, `statut` ("Ouvert"/"Clos"),
  `commentaire`, `lignes`, `charges`, `facture`, `facture_montant` (0 = pas saisi),
  `facture_devise` ; **`ouvert`** = `statut != "Clos"`.
  (Les calculs de revient sont dans la partie B.)

### 1.17 `FilMonte`, `Metier` (`modele.py:606-642`)

- `FilMonte` : `reference`, `etage` (1), `metres` (largeur garnie de ce fil, m), `pourcentage`
  (part du poil, 100), `commentaire`, `poids_bobine` (pesé au lot ; 0 → celui du catalogue, M43).
- `Metier` : `code`, `nom`, `laize` (largeur d'un étage, m), `densite` (**bobines par mètre de
  laize**, ex. 320), `etages` (6), `actif`, `commentaire`, `fils`. `laize` et `etages` ne servent
  pas au calcul du poids monté.

### 1.18 `Magasin` (`modele.py:649-655`)

`code`, `nom`, `type` ("Stock courant" ; `"Quarantaine"` = sous réserve), `contenu` ("Tout" ;
non tenu par Gestion MP), `actif`.

### 1.19 `OrdreFabrication` (`modele.py:658-675`)

`numero`, `date`, `fabrications = [(qualité, m²)]`, `commentaire`, `theorique` (kg par fil, perte
**non** comprise, figé à la validation ; `None` = ordre d'avant le figeage, recalculé avec la
recette en vigueur à sa validation), `perte` (taux figé), `valide_le`. **`m2`** = Σ m² des
fabrications.

### 1.20 `Donnees` (`modele.py:678-756`)

L'instantané complet : `parametres`, `fournisseurs`, `articles`, `qualites`, `recettes`, `plan`,
`mouvements`, `commandes`, `historique_prix`, `receptions`, `magasins`, `metiers`,
`dossiers_import`, `ordres`, `versions_plan: {qualité: [VersionPlan…]}` (dans l'ordre),
`versions_recette: {qualité: [VersionRecette…]}`, `soldes: {(référence, lot, magasin): kg} | None`
(None : inconnus — classeur, date passée), `montage_connu` (True ; False à une date passée : le
montage n'a pas d'historique).

Index (`reindexer`, appelé par `__post_init__`) : `article(reference)`, `fournisseur(nom)`,
`qualite(code)` (dict : en cas de doublon, **le dernier** gagne).

- **`devise_article(article)`** (`:726-739`) : `article.devise or "MAD"` ; **[classeur]** la devise
  du **fournisseur** (MAD s'il est inconnu). Raison : sur `SBR 821` (catalogue EUR, fournisseur
  LOMAT en USD) l'écart atteignait 16 % (50 643 MAD sur une ligne d'achat).
- **`delai_fournisseur(nom)`** (`:741-750`) : fournisseur inconnu (dont nom vide) →
  `delai_defaut` ; sinon `fournisseur.delai_jours` **même s'il vaut 0** (règle `IFERROR` du classeur).
- **`couverture_commande(nom)`** (`:752-756`) : `couverture_commande_jours` du fournisseur s'il est
  connu **et non nul**, sinon `marge_jours`.

---

## 2. `calcul/classification.py` — lire et écrire une référence de fil

Une référence n'est pas un code opaque (`classification.py:1-22`) :

```
PP FRZ-2900 Dtex-Gold 3423-Hs
│  │    │    │    │    │    └ suffixe du fournisseur
│  │    │    │    │    └ code couleur du fournisseur
│  │    │    │    └ libellé de la couleur
│  │    │    └ unité du titrage
│  │    └ titrage
│  └ type de fil (frisé)
└ composition (polypropylène)
```

### 2.1 Référentiels en dur

| Constante | Contenu | Ligne |
|---|---|---|
| `UNITES_TITRAGE` | `("Dtex", "Deniers", "Den", "Tex", "Nm", "Nec")` — l'ordre compte (« Deniers » avant « Den ») | `:31` |
| `UNITE_PAR_DEFAUT` | `PP → Dtex`, `PES → Deniers`, `MICRO PES → Deniers` | `:32-36` |
| `SUFFIXES_FOURNISSEUR` | `HS, OZ, TAT, SUJ, SF, GZM, TURK, TEXT` | `:41` |
| `TYPES_CONNUS` | `FRZ`/`FRIZE` Frisé, `SH` Shrink (rétractable), `FDY` Filament continu (FDY), `BCF` Bouclé continu (BCF), `VER` Vériné, `HS` Heat-set, `CB` Câblé, `MN` Monofilament, `NYLON` Nylon, `SSL` Ssl | `:44-56` |
| `COMPOSITIONS` | `PP` Polypropylène/Synthétique, `PES` Polyester/Synthétique, `MICRO PES` Micro polyester/Synthétique, `PA` Polyamide/Synthétique, `JUTE` Jute/Naturel, `LAINE` Laine/Naturel, `COTON` Coton/Naturel, `SBR` SBR (latex)/Intrant, `PLASTIQUE` Plastique/Intrant, `SIMILI CUIR` Simili cuir/Intrant, `BANDE` Bande/Intrant | `:59-71` |
| `MOTS_COULEUR` | vocabulaire FR/EN des couleurs (beige, black, bleu, blue, blanc, bordeau(x), brique, brown, camel, cream, creme, dark, ecru, fonce, gold, green, grey, gris, ivory, jaune, khave, light, marine, marron, moucheté, mouchte, multi, navy, noir, olive, or, orange, pink, red, rose, rouge, seker, taupe, terra, turkoise, turquoise, vert, vison, vizon, white, yellow, antrasit, anty, claire, clair) | `:78-130` |

### 2.2 Fonctions

- **`_sans_accent(texte)`** (`:157-158`) : normalisation NFKD puis suppression des non-ASCII.
- **`_mot_couleur(mot)`** (`:133-137`) : `propre = sans_accent(mot).lower().strip(".")`, retire un
  préfixe de nuance `^(d|l|dk|lt)\.` ; vrai si `propre ∈ MOTS_COULEUR` (« D.Green », « Dk.Vison »).
  Note : « moucheté » est dans la liste avec accent, mais le mot testé est désaccentué —
  « Moucheté » se lit « mouchete », absent (seul « mouchte » est reconnu).
- **`Classification`** (`:140-154`) : `composition`, `type_fil`, `titrage`, `titrage_unite`,
  `couleur`, `couleur_code`, `suffixe` ; `titrage_complet` = titrage et unité joints par une espace.
- **`code_composition(nature)`** (`:161-174`) : `propre = sans_accent(nature).strip().lower()` ;
  1) premier code dont le **libellé** désaccentué en minuscules préfixe `propre`
  (« Polyester Fil Shrink » → `PES`) ; 2) sinon premier code qui préfixe `propre` ; 3) sinon le
  premier mot en majuscules ; `""` si vide. L'ordre de parcours est celui du dict (PP, PES, MICRO
  PES…) : « micro polyester » ne commence pas par « polyester », donc donne bien `MICRO PES`.
- **`libelle_composition(code)`** (`:177-179`) : `COMPOSITIONS[code.upper()]`, sinon `(code, "Autre")`.
- **`_TITRAGE`** (`:182-186`) : regex insensible à la casse
  `(?<![\w/])(\d+(?:[.,]\d+)?(?:\s*[*x]\s*\d+)?(?:\s*/\s*\d+)?)\s*(Dtex|Deniers|Den|Tex|Nm|Nec)?\b`.
- **`decomposer(reference, nature="")`** (`:189-255`) — rien n'est inventé, un champ illisible
  reste vide :
  1. `brut` = référence aux espaces normalisés ; vide → classification vide.
  2. **Composition** : `code_composition(nature)` si une nature est donnée ; sinon (ou si vide) le
     plus long code de `COMPOSITIONS` qui préfixe `sans_accent(brut).upper()`.
  3. **Suffixe** : dernier segment (séparateurs espaces/tirets) ; s'il est dans
     `SUFFIXES_FOURNISSEUR` (désaccentué, majuscules) → `suffixe`, et le `corps` est `brut` coupé à
     la **dernière** occurrence de ce segment, puis `rstrip(" -")`.
  4. **Type** : premier marqueur de `TYPES_CONNUS` (du plus long au plus court) trouvé dans le corps
     en majuscules, non entouré de lettres (`(?<![A-Z])M(?![A-Z])`).
  5. **Titrage** : première correspondance de `_TITRAGE` dans le corps ; titrage = groupe 1 sans
     espaces autour de `*`, `x`, `/`, et `x` → `*`. Unité : si présente, « Deniers » si elle commence
     par « den », sinon la forme `title()` ramenée à `Dtex`/`Nm`/`Tex`/`Nec` ; sinon `Nm` si le
     titrage contient `/` (20/2) ; sinon `UNITE_PAR_DEFAUT[composition]` ou `""`.
  6. **Couleur** : `reste` = ce qui suit le titrage (ou le corps entier), sans tirets/espaces de
     tête, découpé en mots ; on saute le mot égal au type ; un mot **avec chiffre**, ou un mot
     **non-couleur après un libellé déjà commencé**, va au code ; sinon, tant qu'aucun code n'a
     commencé, au libellé. `couleur` = libellé joint, `couleur_code` = codes joints.
  Exemple : « PP FRZ-2900 Dtex-Gold 3423-Hs » → PP, FRZ, 2900, Dtex, « Gold », « 3423 », « Hs ».
- **`composer(composition, type_fil, titrage, titrage_unite, couleur, couleur_code, suffixe)`**
  (`:258-276`) : `tete` = composition et type en majuscules joints par espace ; `grosseur` = titrage
  + unité ; `teinte` = couleur + code ; segments non vides joints par **`-`** :
  `PP FRZ` + `2900 Dtex` + `Gold 3423` + `Hs` → « PP FRZ-2900 Dtex-Gold 3423-Hs ».
- **`designation(couleur, couleur_code)`** (`:279-281`) : « Couleur (code) », chaque partie omise si vide.

---

## 3. `calcul/moteur.py` lignes 1–1780

### 3.1 Constantes (`moteur.py:43-49`, `:725-732`)

| Constante | Valeur | Sens |
|---|---|---|
| `MOIS` | 12 | horizon du plan glissant |
| `JOURS_PAR_MOIS` | 30 | **[classeur]** mois approximé à 30 j dans les fenêtres |
| `CROISSANCE_MINIMUM` | −0,9 | borne basse de la croissance (à −100 % un mois passé se diviserait par zéro) |
| `SANS_LOT` | `"(sans lot)"` | étiquette des mouvements sans lot |
| `REALISATION_MINI`, `REALISATION_MAXI` | 0,5 ; 1,5 | bornes du coefficient de réalisation |
| `RECUL_DEBUT_JOURS` | 7 | un mois ne juge le plan que si l'atelier sortait déjà du fil dans sa première semaine |
| `POUSSIERE` | 1e-3 | sous le gramme, un stock (ou une quantité à commander) est nul |

Tous les calculs sont en pleine précision (pas d'arrondi intermédiaire, le classeur n'ayant pas
« précision au format affiché »), sauf l'arrondi explicite du plan de production (`moteur.py:9-11`).

### 3.2 Outils de date et d'arrondi

- **`arrondi(valeur, decimales=0)`** (`:52-60`) — ARRONDI d'Excel :
  `signe(valeur) × ⌊|valeur × 10^d| + 0,5⌋ / 10^d` (signe = +1 si valeur ≥ 0). 2,5 → 3 ; −2,5 → −3 ;
  `round()` de Python donnerait 2. (Flottants : 2,675 × 100 = 267,4999… → 2,67, comme tout calcul binaire.)
- **`fin_de_mois(jour, decalage=0)`** (`:63-68`) — FIN.MOIS : dernier jour du mois décalé
  (`rang = mois−1+decalage`, division entière par 12 pour l'année, accepte les négatifs).
- **`debut_de_mois(jour, decalage=0)`** (`:71-74`) : 1er du mois décalé.
- **`mois_du_plan(date_ref)`** (`:77-79`) : `[fin_de_mois(date_ref, i) for i in 0..11]` — M0 = mois
  en cours (`Production_Plan!B5`).
- **`_mois_entre(debut, fin)`** (`:191-193`) : `(an_fin − an_debut) × 12 + mois_fin − mois_debut`
  (0 = même mois ; négatif si `fin` avant `debut`).
- **`_mois_ecoules(depuis, jusqu_a)`** (`:830-835`) — DATEDIF(…;"m") + 1, au minimum 1 :
  `m = (Δannées)×12 + Δmois ; si jour(jusqu_a) < jour(depuis) : m −= 1 ; résultat = max(1, m + 1)`.
  Ex. 15/03 → 08/10 : 7 − 1 = 6 → **7 mois**.

### 3.3 `a_la_date(donnees, date_ref, aujourdhui=None)` — rejouer les données au soir d'une date (`:85-188`)

Sans elle, une date de référence passée ne changeait que le calendrier du plan (stock, valeur,
ruptures d'aujourd'hui sous une date d'hier). Appelée par `depot.charger_au` avec
`aujourdhui = date.today()`.

1. Si `aujourdhui` est donné, `date_ref < aujourdhui` et `montage_connu` → copie avec
   `montage_connu = False` (le montage des métiers n'a pas d'historique : ne compte pas dans le
   stock d'une date passée).
2. `derniere` = max des dates de mouvements, de réception, de `date_bc` des commandes, de
   `date_bc` de l'historique des prix, des dates d'ordres (mise en cache sur l'objet,
   `_derniere_date`). **Si `derniere ≤ date_ref` → données rendues telles quelles** (soldes
   compris).
3. Réceptions gardées : date vide ou `≤ date_ref` (brouillons compris).
4. **Reçu après la date** : pour chaque réception **validée** datée `> date_ref`, chaque ligne
   non « Refusé » qui a un bon (`ligne.numero_bc or reception.numero_bc`) :
   `recu_apres[(bon, référence)] += quantite_pesee` ; le bon entre dans `bons_livres_apres`.
5. **Rendu au fournisseur après la date** : `rendu_apres[(référence, lot)] −= quantite_signee`
   pour chaque `RETOUR_FOURNISSEUR` daté `> date_ref` (donc + kg rendus, − les annulations). S'il y
   en a (|q| > 1e-9) : pour chaque (référence, lot) concerné, les pesées de **toutes** les
   réceptions validées (quelle que soit leur date), lignes non refusées avec un bon :
   `recu_apres[(bon, réf)] −= rendu_apres[(réf, lot)] × pesée_ligne / Σ pesées du lot` (si total > 0),
   et le bon entre dans `bons_livres_apres`. (Le reçu d'aujourd'hui est **net** des retours : ce qui
   est reparti après la date était encore reçu ce jour-là.) Pas de plafonnement ici, contrairement
   à `depot._au_prorata` (min avec la pesée).
6. **Commandes** : on retire celles dont `date_bc > date_ref` (une date vide est gardée). Pour un
   bon de `bons_livres_apres` : statut « Soldée » → « Confirmée » (sinon inchangé) et chaque ligne
   `quantite_recue = max(0, quantite_recue − recu_apres[(bon, réf)])`.
7. Copie : mouvements `date ≤ date_ref` ; réceptions (3) ; commandes (6) ; historique des prix
   `date_bc` vide ou `≤ date_ref` ; ordres `date` vide ou `≤ date_ref` ; **`soldes = None`** ;
   `_derniere_date = date_ref`.
8. Restent **tels qu'aujourd'hui** : catalogue (prix, stock min, délais…), réglages, fournisseurs,
   magasins, qualités, recettes et plan actuels (et leurs versions), dossiers d'importation (le coût
   d'une marchandise est celui qu'on lui connaît), métiers.

`etat_stock` ne filtre pas lui-même les mouvements par date : sans `a_la_date`, un mouvement
postérieur à `date_ref` serait compté.

### 3.4 Plan de production

#### `m2_du_mois(donnees, base, saisonnalite, fin, ancre)` (`:196-212`)

```
coef        = saisonnalite[mois(fin) − 1]   (1,0 si la liste est vide)
croissance  = max(croissance_annuelle, −0,9)
m2          = arrondi( base × coef × (1 + croissance) ^ (_mois_entre(ancre, fin) / 12) , 0 )
```

L'ancre est le jour où la base a été saisie : un mois donné a **la même prévision d'où qu'on le
regarde** (le classeur comptait la croissance depuis le mois en cours : septembre valait
base × 1,05^(8/12) vu de janvier et base × 1 vu de septembre). Un mois avant l'ancre a un exposant
négatif (division). Exemple : base 10 000, coef sept. 1,1, croissance 5 %, ancre 15/01/2026,
fin 30/09/2026 → 8 mois → 10 000 × 1,1 × 1,05^(8/12) = 11 000 × 1,033062 = 11 363,7 → **11 364 m²**.

#### `plan_mensuel(donnees, date_ref)` → `{qualité: [m² × 12]}` (`:215-245`)

Pour chaque `PlanQualite` :
- `actif` faux → `[0] × 12` (dans les deux modes) ;
- **[classeur]** `arrondi(base × saisonnalite[mois] × (1 + croissance)^(rang/12))`, `rang` = 0…11
  (croissance non bornée) ;
- **corrigé** : `m2_du_mois(base, saisonnalite, fin_i, ancre = ligne.depuis or date_ref)`.

C'est le plan **d'aujourd'hui** pour les mois à venir.

#### `plan_en_vigueur(donnees, ligne, fin)` → `VersionPlan` (`:248-262`)

- Sans versions pour la qualité : `VersionPlan(quand=None, base, saisonnalite, actif=True, depuis=ligne.depuis)`
  (**l'arrêt éventuel est ignoré** : sans histoire, on ne sait pas depuis quand ; le passé garde sa base).
- Sinon : `retenue = versions[0]`, puis la **dernière** version dont `quand` n'est pas vide et
  `≤ fin à 23:59:59.999999`.

#### `m2_passe(donnees, ligne, fin, jusqu_a=None)` — m² prévus **par le plan de l'époque** (`:265-302`)

- Sans versions : `v = plan_en_vigueur(...)` ; `0` si `v.actif` est faux (ne peut pas arriver ici,
  `actif=True`) ; sinon `m2_du_mois(v.base, v.saisonnalite, fin, ancre = v.depuis or fin)`.
- Avec versions — **prorata des jours de vigueur** :
  ```
  debut  = 1er du mois de fin, 00:00
  borne  = min(fin, jusqu_a) si jusqu_a sinon fin
  limite = (borne + 1 jour) à 00:00          ; si limite ≤ debut → 0
  en_vigueur = dernière version avec quand vide ou ≤ debut  (à défaut versions[0])
  changements = versions avec debut < quand < limite (dans l'ordre)
  instants = [debut, quand des changements…, limite] ; durée = limite − debut (secondes)
  total = Σ sur chaque tranche [de, a[ de la version v en vigueur :
            si v.actif et a > de : m2_du_mois(v.base, v.saisonnalite, fin, v.depuis or fin) × (a − de)/durée
  ```
  La durée est celle du **vrai** mois civil (pas 30 j), à la seconde près (un changement à 10 h
  compte à 10 h). Chaque tranche arrondit son m² mensuel **avant** le prorata : le total n'est pas
  un entier. Une qualité arrêtée en cours de mois compte de même pour ses jours actifs.
  Exemple (docstring) : plan à 35 000 révisé à 52 500 le 20 septembre à 00:00 → 35 000 × 19/30 +
  52 500 × 11/30 = **41 416,67 m²** (et non 52 500, qui jugeait sur 52 500 les 14 245 m² tissés
  avant le 20).

### 3.5 Nomenclature

- **`metres_du_role(donnees, qualite, article)`** (`:308-315`) : 0 si le rôle n'est pas linéaire ;
  sinon `qualite.poids[rôle]` (ml/m², 0 si absent ou si la qualité est inconnue).
- **`poids_du_role(donnees, qualite, article)`** (`:318-332`) — `Recettes!M5` :
  `valeur = qualite.poids[rôle de l'article]` (0 si qualité inconnue ou rôle absent) ; si rôle
  linéaire, `valeur × (article.densite or 0)`. En **kg/m²**. Ex. 1,02 ml/m² × 0,014 kg/ml =
  0,01428 kg/m².
- **`kg_par_m2(donnees, qualite, reference, pourcentage)`** (`:335-340`) — `Recettes!F5` :
  0 si l'article est inconnu ; sinon `pourcentage / 100 × poids_du_role`. Lit le rôle et la densité
  **actuels** de l'article.

#### `LigneNomenclature` et `nomenclature(donnees)` (`:343-418`)

Une ligne par `LigneRecette` (ordre des recettes). Article inconnu → ligne vide (rôle, nature…
`""`, `kg_m2 = prix_kg = cout_m2_mad = poids_categorie = 0`, devise `""`). Sinon :

| Champ | Formule |
|---|---|
| `role_bom`, `nature`, `designation`, `fournisseur` | de l'article |
| `poids_categorie` | `poids_du_role` (kg/m², densité appliquée) |
| `kg_m2` | `pourcentage/100 × poids_categorie` (**perte non comprise**) |
| `ml_m2` | `pourcentage/100 × metres_du_role` (0 pour un rôle au poids) |
| `prix_kg` | `article.prix_kg` |
| `prix`, `unite_prix` | prix du catalogue dans son unité |
| `devise` | `devise_article` |
| `cout_m2_mad` | `kg_m2 × prix_kg × taux(devise) × perte`, avec `perte = 1 + taux_perte` (corrigé) ou **1 [classeur]** |

Le classeur ignorait la perte dans le coût : coût matière annuel sous-estimé de 2 % (884 663 MAD).

#### `TOLERANCE_RECETTE = 0.01` et `controle_recettes(donnees)` (`:421-456`) — `Recettes!O6:R26`

Pour chaque qualité, chaque rôle de `qualite.poids` **de poids non nul** :
`somme = Σ pourcentage` des lignes de recette de la qualité dont l'article (connu) a ce rôle ;
écart si `|somme − 100| > tolérance` (`0,01` point, **1e-6 [classeur]**). Rend par qualité :
`{qualite, roles_utilises, roles_conformes, ecarts: [{role, somme}], conforme}`.
Une seule tolérance pour l'enregistrement et le contrôle C01 (0,01 point d'un fil à 1 kg/m² = 0,1 g/m²).

### 3.6 Besoins (MRP)

#### `besoins_mensuels(donnees, date_ref)` → `{référence: [kg × 12]}` (`:462-485`) — `Production_Besoins!U6#`

```
plan = plan_mensuel(date_ref)
pour chaque ligne de recette avec une référence :
    si la qualité n'a pas de ligne de plan → la référence existe, besoins nuls
    kg = kg_par_m2(qualité, référence, %) ; si 0 → existe, nuls
    besoins[réf][i] += kg × plan[qualité][i]
résultat = besoins × (1 + taux_perte)          (dans les deux modes)
```

Une référence absente de toute recette n'a pas d'entrée (le stock la prend à zéro).

### 3.7 Le plan et les recettes de l'époque

- **`versions_recette_pendant(donnees, qualite, debut, fin)`** (`:491-506`) : `[None]` si la qualité
  n'a pas d'histoire (= recette d'aujourd'hui). Sinon `en_vigueur = [versions[0]]` (avant la
  première version connue, c'est elle qui vaut), puis pour chaque version dans l'ordre :
  `quand ≤ debut` → `en_vigueur = [version]` ; sinon `quand ≤ fin` → ajoutée. Rend les versions en
  vigueur à un moment de `[debut ; fin]`.
- **`kg_m2_version(donnees, qualite, version, cache)`** (`:509-548`) → `{référence: kg/m²}` (sans
  perte, valeurs nulles retirées), cache par `(qualité, id(version))` :
  - `version is None` : Σ `kg_par_m2` des lignes de recette **actuelles** de la qualité ;
  - sinon : poids au m² = `version.poids`, à défaut ceux de la **première version suivante** qui en
    a, à défaut ceux de la qualité aujourd'hui (`{}` si inconnue) ; on calcule `kg_par_m2` sur une
    copie des données où la qualité porte ces poids, pour chaque `(référence, %)` de la version.
    Les **articles** (rôle, densité) restent ceux d'aujourd'hui.
- **`besoins_passes(donnees, fins)`** → `(prevus, stables)` (`:551-580`) — `fins` = derniers jours
  de mois clos :
  ```
  pour chaque ligne de plan (actives ou non), chaque mois i (fin_i) :
      versions = versions_recette_pendant(qualité, 1er du mois 00:00, fin_i 23:59:59.999999)
      kgs = [kg_m2_version(v) for v in versions]
      m2  = m2_passe(ligne, fin_i)
      pour chaque référence présente dans au moins un kgs :
          valeurs = [k.get(réf, 0) for k in kgs]
          si max(valeurs) − min(valeurs) > 1e-9 × max(1, max(valeurs)) : stables[réf][i] = False
          prevus[réf][i] += valeurs[-1] × m2 × (1 + taux_perte)    (la DERNIÈRE version du mois)
  ```
  Un mois où la recette d'un fil a changé « ne dit rien » : il ne juge pas son plan.
- **`fils_remplaces(donnees, debut, fin)`** → `{(qualité, entrant): [sortants]}` (`:623-646`) :
  pour chaque qualité de la recette actuelle (`aujourd_hui` = références de part > 0), avec les
  versions **non None** en vigueur sur la période : `au_debut` = références (part > 0) de la
  première ; `vus` = celles de toutes ; `sortants = vus − aujourd_hui` ; pour chaque
  `entrant ∈ aujourd_hui − au_debut`, les sortants de **même rôle** (rôle actuel du catalogue ;
  deux références inconnues ont le même rôle `None`), triés.
- **`sortis_des_recettes(donnees, debut, fin)`** (`:649-657`) : références (part > 0) d'une
  version en vigueur sur la période, pour les qualités qui ont une histoire, **moins** celles d'une
  recette actuelle (part > 0) : remplacés ou abandonnés.

#### `besoin_sur_fenetre(besoins, debut_jours, fin_jours, jours_restants_du_mois=None)` (`:583-620`) — `Stock!G10`, `Stock!H10`

La demande est une courbe en paliers de 12 segments :

```
segment 1 : si jours_restants_du_mois n'est pas None :
                durée = clamp(jours_restants, 0, 30) ; quantité = besoin[0] × durée / 30
            sinon : durée 30, quantité besoin[0]                  [classeur]
segments 2..12 : durée 30, quantité besoin[i]
total = Σ sur les segments de durée > 0 : quantité × longueur([curseur ; curseur+durée] ∩ [debut ; fin]) / durée
```

Au-delà du 12ᵉ segment, la demande est **nulle** (fenêtre tronquée). Le classeur facturait le mois
en cours en entier : au 18 juillet, 12 jours restants comptés 30 → 20 845 kg de trop sur une
référence.

Exemple : besoins `[3 000, 3 000, …]`, 22 jours restants, fenêtre `[0 ; 30]` → segment 1 (22 j,
2 200 kg) entier = 2 200 + segment 2 (30 j, 3 000) sur `[22 ; 30]` = 8/30 × 3 000 = 800 → **3 000**.

### 3.8 Stock monté sur les métiers

- **`FilEnMachine`** (`:663-675`) : `metier, etage, reference, metres, pourcentage, densite, bobines, poids_bobine, poids`.
- **`fils_en_machine(donnees)`** (`:678-708`) : pour chaque métier **actif**, chaque fil monté :
  ```
  poids_bobine = fil.poids_bobine (pesé au lot) or article.poids_bobine (catalogue) or 0
  bobines      = fil.metres × metier.densite × fil.pourcentage / 100
  poids        = bobines × poids_bobine          (kg)
  ```
  Ex. 2 m sur un métier à 320 bobines/m, 50 % du poil, bobine de 4,5 kg → 320 bobines → **1 440 kg**.
- **`stock_en_machine(donnees)`** (`:711-719`) : `{}` si `montage_connu` est faux ; sinon Σ `poids`
  par référence.

### 3.9 `LigneStock` — tous les champs (`:735-827`)

Une ligne par article du catalogue (ordre du catalogue). Les champs ci-dessous sont calculés par
`etat_stock` (§3.10) ; « corr. » = méthode corrigée.

| Champ | Valeur |
|---|---|
| `reference`, `nature`, `designation`, `fournisseur`, `composition`, `type_fil`, `couleur`, `titrage_unite`, `groupe_equiv` | de l'article |
| `titrage` | `str(article.titrage or "")` |
| `unite_achat` | `article.unite_prix` (kg / ml) |
| `prix_unite` | `article.prix_unite` |
| `kg_par_ml` | `article.kg_par_ml` |
| `stock_initial` | Σ `quantite` des `STOCK_INITIAL` |
| `entrees` | Σ `quantite_signee` des `ENTREE_RECEPTION` et `RETOUR_PRODUCTION` (nettes des annulations) |
| `stock_net` | `stock_initial + entrees + sorties + ajustements + retours_fournisseur` (sorties et retours fournisseur négatifs) ; corr. : `|net| < 1e-3 → 0`. **Magasins, quarantaine comprise.** |
| `stock_machine` | `stock_en_machine[réf]` (0 [classeur]) |
| `stock_quarantaine` | Σ des soldes par magasin des magasins de type `Quarantaine` (`bloque`) |
| `stock_disponible` | `stock_net − stock_quarantaine + stock_machine` |
| `bc_en_cours` | reste à livrer attendu à temps (voir 3.10-F) |
| `bc_hors_horizon` | reste attendu après le délai (0 [classeur]) |
| `bc_dans_couverture` | reste attendu après le délai mais avant la fin de couverture (0 [classeur]) |
| `bc_en_preparation`, `bons_en_preparation` | Σ des restes des bons « pas partis » ; numéros triés |
| `demande_delai` | `besoin_sur_fenetre(besoin, 0, délai, restant)` |
| `sorties_prevues` | `besoin_sur_fenetre(besoin, délai, délai + couverture_commande, restant)` |
| `stock_projete` | `stock_net − quarantaine + stock_machine + bc_en_cours − demande_delai` |
| `stock_min` | `article.stock_min` |
| `stock_min_plafonne`, `stock_min_recalcule` | voir 3.10-J |
| `statut`, `statut_couverture` | voir 3.10-K |
| `couverture_jours` | `stock_projete / (conso / 30)` si conso ≠ 0, sinon `None` |
| `couverture_cible_jours` | corr. `stock_min_recalcule / (conso/30)` (0 si conso nulle) ; [classeur] `délai + couverture_commande` |
| `conso_mensuelle` | voir 3.10-G |
| `besoin_annuel` | Σ du besoin corrigé sur 12 mois |
| `conso_plan` | Σ besoin **du plan** (non corrigé) / 12 |
| `conso_reelle` | réel moyen par mois retenu de la fenêtre (ou `None`) |
| `coefficient_realisation` | voir 3.10-E (ou `None`) |
| `conso_horizon` | corr. `besoin_sur_fenetre(besoin, 0, H, restant) / H × 30`, H = délai + couverture + 30 ; [classeur] = conso |
| `realisation_heritee` | fils dont le coefficient est hérité |
| `delai_jours` | `delai_fournisseur` |
| `sans_achat` | raison de ne rien proposer (corr.) |
| `quantite_theorique` | besoin net avant minimum et conditionnement |
| `quantite_a_commander` | voir 3.10-L |
| `palettes_a_commander` | `_palettes(quantité, contenance_palette)` |
| `unite_commande`, `contenance_commande` | `article.conditionnement` |
| `unites_a_commander` | `quantite_a_commander / contenance_commande` (0 si contenance nulle) |
| `quantite_a_commander_achat` | `quantite / densite` si `unite_achat == "ml"` et densité ≠ 0, sinon la quantité (kg) |
| `prix_kg` | `article.prix_kg` (prix du **catalogue** au kilo) |
| `devise` | `devise_article` |
| `montant_a_commander` | `quantite_a_commander × prix_kg` |
| `montant_a_commander_mad` | `× taux(devise)` |
| `valeur_conso_annuelle` | `conso_mensuelle × 12 × prix_kg` |
| `valeur_conso_annuelle_mad` | `× taux(devise)` |
| `classe_abc`, `rang`, `pourcentage_cumule` | `_classer_abc` (3.11) |
| `cv_demande`, `classe_xyz` | voir 3.10-O (défaut `0` et `"—"`) |
| `sourcing`, `nb_fournisseurs_groupe` | voir 3.10-M |
| `substituts` | voir 3.10-P |
| `date_derniere_sortie` | dernière `SORTIE_PROD` réelle (ni annulée ni annulation) |
| `jours_sans_mouvement`, `dormant` | voir 3.10-N |
| `par_magasin` | `{code: solde}` pour chaque magasin **actif** |
| `besoins` | les 12 besoins mensuels **corrigés** |
| `action` | `"📝 Créer BC - {fournisseur}"` si quantité > 0, sinon `"—"` |

### 3.10 `etat_stock(donnees, date_ref)` → `list[LigneStock]` (`:838-1477`) — `Tbl_Stock`

Écart assumé avec le classeur : seules les références réelles (pas les 176 lignes vides de la
table Excel, qui polluaient ABC et compteurs).

**A. Préparation (`:845-857`)**

```
besoins = besoins_mensuels(date_ref)                          # plan d'aujourd'hui, perte comprise
magasins = codes des magasins actifs                         # pour par_magasin
quarantaines = codes des magasins de type "Quarantaine"      # actifs ou non ; calculé même [classeur]
jours_restants_du_mois = max(0, 30 − jour(date_ref))         # 30 et 31 → 0
monte = {} [classeur] sinon stock_en_machine(donnees)
```

**B. Fenêtre de réalisation (`:868-893`)**

```
fenetre = 0 [classeur] sinon int(fenetre_realisation_jours)
mois_fenetre = max(1, int(arrondi(fenetre / 30))) si fenetre sinon 0     # 75 j → 2,5 → 3 mois ; 10 j → 1
debut_fenetre = debut_de_mois(date_ref, −mois_fenetre)
si fenetre :
    premiere = min des dates des SORTIE_PROD datées ≤ date_ref (toutes références, annulations comprises)
    tant que mois_fenetre > 0 et (premiere absente ou premiere > debut_fenetre + 7 jours) :
        mois_fenetre −= 1 ; debut_fenetre = debut_de_mois(date_ref, −mois_fenetre)
    si mois_fenetre == 0 : fenetre = 0          # → retour à la règle « FIX P1 » (G)
fins_fenetre = [fin_de_mois(date_ref, −k) pour k = mois_fenetre … 1]     # mois CLOS, chronologiques
prevus_passes, mois_stables = besoins_passes(fins_fenetre)
```

Exemple : 08/10/2026, 90 j → juillet, août, septembre (début 01/07). Première sortie de l'usine le
05/07 ≤ 08/07 → 3 mois ; le 10/07 → 2 mois (août, septembre).
On compare des **mois entiers clos** : l'atelier sort son fil par ordres, un mois entamé au prorata
ne dirait que si les ordres sont tombés avant ou après le 10.

**C. Agrégats du journal, en une passe (`:895-978`)**

```
decalage_xyz = 0 [classeur] sinon 1       # XYZ sur 12 mois CLOS (corr.), mois en cours inclus [classeur]
fin_periode = [fin_de_mois(date_ref, −i − decalage_xyz) pour i = 11 … 0]  → index 0..11
annulees = { contrepasse_id de tous les mouvements }
pour chaque mouvement m (réf r), s = m.quantite_signee :
  # dernière entrée (dormants)
  si m.type ∈ {STOCK_INITIAL, ENTREE_RECEPTION, RETOUR_PRODUCTION} et s > 0
     et m.contrepasse_id vide et m.id ∉ annulees : derniere_entree = max(…, m.date)
  STOCK_INITIAL      : stock_initial += m.quantite
  ENTREE_RECEPTION / RETOUR_PRODUCTION : entrees += s
       si fenetre et RETOUR_PRODUCTION dans un mois de la fenêtre : reel[rang] −= s   (un reliquat rendu n'a pas été consommé)
       si RETOUR_PRODUCTION et corr. et dans les 12 mois XYZ : sorties_par_mois[idx] −= s
  SORTIE_PROD        : sorties += s   (négatif)
       réelle = contrepasse_id vide et id ∉ annulees
       si réelle : derniere_sortie = max, premiere_sortie = min
       si dans les 12 mois XYZ : sorties_par_mois[idx] += |s| [classeur] ou −s (corr., nettes : une annulation se retranche)
       si fenetre et dans la fenêtre : reel[rang] −= s
  AJUSTEMENT_INVENTAIRE : ajustements += s
  RETOUR_FOURNISSEUR    : retours_fournisseur += s
  # ventilation par magasin
  TRANSFERT_MAGASIN : magasins[destination] += m.quantite ; magasins[source] −= m.quantite
  autre             : si destination : magasins[destination] += s ; sinon si source : magasins[source] += s
```

Le type `QUARANTAINE` (signe 0) ne change rien. Les contre-passations ont une quantité négative
(§4.6) : `s` est de signe opposé à l'original, elles se retranchent naturellement.

**D. Commandes attendues et en préparation (`:984-1000`)**

```
pour chaque commande, sauf statut "Annulée" :
    si pas_partie(commande) :                        # brouillon (corr.)
        pour chaque ligne : reste = commandée − reçue ; si reste > 1e-3 : en_preparation[réf] += (reste, numéro)
    sinon pour chaque ligne : reste = reste_a_livrer(...) ; si reste > 0 : en_commande[réf] += (reste, arrivee_attendue)
fournisseurs_du_groupe[groupe_equiv] = ensemble des noms de fournisseurs des articles du groupe (tous articles)
```

**E. Coefficient de réalisation (si `fenetre`) (`:1019-1090`)**

```
sortis = ∅ [classeur] sinon sortis_des_recettes(1er du mois de date_ref − 12 mois, date_ref 23:59:59)
pour chaque article :
    conso_plan = Σ besoins[réf] / 12
    prevus, stables = prevus_passes[réf] (zéros), mois_stables[réf] (vrais)
    retenus = indices i de la fenêtre où stables[i]
    coefficient, conso_reelle, hors_recette = None, None, False
    si retenus :
        reel = max(0, Σ reel[i] pour i ∈ retenus)
        conso_reelle = reel / |retenus|
        prevu = Σ prevus[i] pour i ∈ retenus
        si prevu > 0 :
            coefficient = clamp(reel / prevu, 0,5, 1,5)
            si coefficient < 1 et stock_net ≤ 1e-3 : coefficient = 1     # en rupture, il n'a pas pu sortir
        sinon si reel > 0 et conso_plan == 0 et tous prevus nuls et réf ∉ sortis :
            hors_recette = True                                          # consommé hors recette
```

**Héritage (corr. seulement)** : un fil entré dans une recette à la place d'un autre prend son taux.

```
plan = plan_mensuel(date_ref) ; remplaces = fils_remplaces(debut_fenetre 00:00, date_ref 23:59:59)
pour chaque ligne de recette (qualité q, réf r) dont le coefficient est None :
    poids = kg_par_m2(q, r, %) × Σ plan[q] (12 mois) ; ignorée si ≤ 0
    anciens = remplaces[(q, r)] qui ont un coefficient
    si anciens :
        w_x = max(Σ prevus_passes[x], 1e-9)        (tous les mois de la fenêtre, stables ou non)
        herite = Σ coef_x × w_x / Σ w_x ; parts[r] += (poids, herite, anciens)
    sinon parts[r] += (poids, None, [])
pour chaque r dont au moins une part a un héritage :
    coefficient = Σ poids × (herite ou 1) / Σ poids            # une qualité sans fil remplacé compte 1
    realisations[r] = (coefficient, conso_reelle d'avant, hors_recette = False)
    realisation_heritee = noms triés
```

**F. Par article : besoin corrigé, consommation, demande (`:1092-1166`)**

```
besoin = besoins[réf] (12 zéros si absente)
si coefficient : besoin = besoin × coefficient
sinon si hors_recette : besoin = [conso_reelle] × 12
besoin_annuel = Σ besoin
G. conso_mensuelle :
   si fenetre : besoin_annuel / 12
   sinon (fenêtre 0, [classeur] ou pas d'historique) — « FIX P1 » de mai 2026 (Notice B65) :
       conso_historique = |sorties| / _mois_ecoules(premiere_sortie, date_ref)  (0 sans sortie réelle)
       conso = max(conso_historique, besoin_annuel / 12)
delai = delai_fournisseur(fournisseur) ; couverture = couverture_commande(fournisseur)
restant = None [classeur] sinon jours_restants_du_mois
demande_delai  = besoin_sur_fenetre(besoin, 0, delai, restant)
sorties_prevues = besoin_sur_fenetre(besoin, delai, delai + couverture, restant)
stock_machine = monte[réf]
commandes attendues (en_commande[réf]) :
   [classeur] bc_en_cours = Σ restes ; bc_hors_horizon = 0
   corr. : limite = date_ref + int(delai) jours ; fin_couverture = date_ref + int(delai + couverture) jours
           bc_en_cours        = Σ restes dont la date est vide ou ≤ limite   (sans date annoncée : on fait confiance)
           bc_hors_horizon    = Σ restes dont la date > limite
           bc_dans_couverture = Σ restes avec limite < date ≤ fin_couverture   (arrivent trop tard pour le délai, mais servent la même période)
bloque = Σ magasins[q] pour q ∈ quarantaines
stock_projete = stock_net − bloque + stock_machine + bc_en_cours − demande_delai
conso_horizon = conso [classeur] ; corr. besoin_sur_fenetre(besoin, 0, H, restant) / H × 30, H = delai + couverture + 30
prix = prix_kg ; valeur_conso = conso × 12 × prix ; valeur_conso_mad = × taux(devise_article)
```

**I. Classement ABC** : `_classer_abc(lignes)` sur toutes les lignes (3.11), **avant** la seconde passe.

**J. Stock minimum (`:1222-1263`)** — `js = _jours_securite(classe)`, `couv_min = article.couv_min_mois or 0` :

```
[classeur] (Stock!W10) : plafonne = stock_min
           recalcule = max(stock_min, couv_min × conso × (1 + marge_securite), conso × delai / 30, conso × js / 30)
corr. :    saison = conso_horizon
           plafonne = 0                                    si conso ≤ 0  (fil non consommé : aucun minimum)
                    = min(stock_min, plafond × saison)     si plafond_stock_min_mois > 0
                    = stock_min                            sinon
           recalcule = max(plafonne, couv_min × saison × (1 + marge_securite), saison × js / 30)
```

En corrigé, **plus de terme « délai »** : le seuil se compare au stock projeté, qui a déjà retiré
la demande du délai (un fil à 65 j de délai devait détenir quatre mois d'avance pour être « OK »).
Le plafond évite qu'un stock minimum du catalogue démesuré (onze mois d'avance, plein stock hors
saison) fasse sonner l'alerte et acheter du fil qui dormira ; le contrôle C33 liste les plafonnés.

**K. Couverture et statuts (`:1265-1324`)**

```
couverture_jours = stock_projete / (conso / 30)            si conso ≠ 0
statut_couverture (Stock!J10, gardé pour comparaison) :
   projete ≤ 0 et conso == 0 → OK ; projete ≤ 0 → RUPTURE ; conso == 0 → OK
   couverture < seuil_critique → CRITIQUE ; < seuil_alerte → ATTENTION ; sinon OK
statut (Notice §6 : stock projeté contre stock minimum recalculé) :
   conso == 0                                           → NON CONSOMMÉE
   corr. et recalcule ≤ 0 et projete > −1e-3            → OK     (rien demandé d'ici l'horizon : fil de saison hors saison)
   projete ≤ 0                                          → RUPTURE
   recalcule ≤ 0                                        → OK
   projete ≤ 0,5 × recalcule                            → CRITIQUE
   projete ≤ recalcule                                  → URGENT
   projete ≤ 1,2 × recalcule                            → ATTENTION
   sinon                                                → OK
[classeur] : statut = statut_couverture (écrase le précédent) ; couverture_cible = délai + couverture_commande
corr.      : couverture_cible = recalcule / (conso/30) (0 si conso nulle)   ⇔ couverture ≥ cible ⇔ projeté ≥ seuil
```

**L. Quantité à commander (`:1326-1410`)** — `Stock!K10`

```
couverture = couverture_commande(fournisseur)
securite = js × sorties_prevues / couverture        (0 si couverture nulle)
reliquat = max(0, stock_projete)
[classeur] besoin_net = max(0, sorties_prevues + securite − reliquat, stock_min − reliquat)
corr.      besoin_net = max(0, sorties_prevues + max(securite, recalcule) − stock_projete − bc_dans_couverture)
              (le projeté NÉGATIF se prend tel quel : le manque du délai est du retard à rattraper)
           besoin_net = max(0, besoin_net − bc_en_preparation)        # un brouillon n'est pas reproposé
           sans_achat = "matière désactivée"                          si article inactif
                      = "fournisseur désactivé"                       sinon si fournisseur connu et inactif
                      = "non consommée : ni dans une recette du plan, ni sortie"  sinon si conso ≤ 0
           si sans_achat ou besoin_net < 1e-3 : besoin_net = 0
quantite_theorique = besoin_net
(unite_commande, contenance_commande) = article.conditionnement
si [classeur] ou besoin_net ≤ 0 :
    quantite = besoin_net ; palettes = _palettes(besoin_net, contenance_palette) si besoin_net ≠ 0 sinon 0
sinon :
    quantite = max(besoin_net, minimum_commande)
    si contenance_commande > 1 : unites = _palettes(quantite, contenance) ; quantite = unites × contenance
    palettes = _palettes(quantite, contenance_palette) si contenance_palette sinon 0
unites_a_commander = quantite / contenance_commande
quantite_a_commander_achat = quantite / densite si unite_achat == "ml" et densite sinon quantite
montant = quantite × prix_kg ; montant_mad = montant × taux(devise)
```

Le nombre d'unités fait foi et la quantité en découle (recalculer l'arrondi ferait basculer
6 036,8 / 862,4 d'un cheveu au-dessus de 7). 109 kg d'un ruban facturé au mètre à
0,00498 kg/ml → 21 879 m pour le fournisseur.

**M. Sourcing (`Stock!Y10`)** : `nb = |fournisseurs_du_groupe[groupe]|` ; sans groupe →
« ❓ Hors catalogue » ; `nb ≤ 1` → « 🔴 MONO-SOURCE » ; sinon « ✅ Multi-source (nb) ».

**N. Dormants (`Stock!AC10:AE10`)**

```
[classeur] : jours = date_ref − derniere_sortie (si elle existe)
             dormant = faux si projete ≤ 0 ; vrai si aucune sortie ; sinon jours > seuil_dormant
corr. :      dernier = max(derniere_sortie, derniere_entree) (dates connues)
             jours = date_ref − dernier (None sans date)
             dormant = stock_net > 1e-3 et (dernier absent ou jours > seuil_dormant)
```

Dort ce qui est **là** (le stock des magasins, pas le projeté : un bon en cours ne dort pas) et
n'a ni servi ni été reçu depuis le seuil (audits 2-A M1, 2-F G5, 2-G M3). Une sortie annulée et son
annulation ne comptent pas comme dernière sortie.

**O. Classe XYZ (`Stock!AF10`)**

```
serie = [max(0, sorties_par_mois[i]) pour i = 0..11]
moyenne = Σ serie / 12 ; si moyenne ≠ 0 : cv = √(Σ (v − moyenne)² / 12) / moyenne    (écart-type de population)
cv == 0 (ou pas de sortie) → "—" ; cv ≤ seuil_xyz_x → X ; cv ≤ seuil_xyz_y → Y ; sinon Z
```

Corr. : sorties nettes des annulations **et** des retours des machines, sur 12 mois clos.
Exemple : 11 mois à 1 000 kg et un à 0 → moyenne 916,7 ; σ = √((11 × 83,3² + 916,7²)/12) = 276,4 →
cv = 0,30 → **Y**.

**P. Substituts (`Stock!AL10`)** : pour une ligne en **RUPTURE** avec un groupe, les autres
références du groupe dont `stock_projete > 0`, dans l'ordre du catalogue.

#### Exemple complet (méthode corrigée)

Date 08/10/2026 (22 jours restants), fournisseur délai 30 j, couverture 30 j ; classe A
(sécurité 30 j) ; `marge_securite` 0,2, `couv_min` 0, `stock_min` 1 000, plafond 3 mois ; besoin
corrigé 3 000 kg/mois ; stock net 4 600 (dont 500 en quarantaine) ; 300 kg en machine ; un bon de
2 000 kg attendu le 20/10 ; palette de 1 000 kg ; prix 20 USD/kg, USD à 9,5.

- `demande_delai` = [0 ; 30] = 2 200 + 800 = 3 000 ; `sorties_prevues` = [30 ; 60] = 2 200 + 800 = 3 000.
- `stock_projete` = 4 600 − 500 + 300 + 2 000 − 3 000 = **3 400**.
- `conso` = 3 000 ; H = 90 → [0 ; 90] = 2 200 + 3 000 + 3 000 + 800 = 9 000 → `conso_horizon` = 3 000.
- `stock_min_plafonne` = min(1 000, 9 000) = 1 000 ; `stock_min_recalcule` = max(1 000, 0, 3 000) = **3 000**.
- `couverture_jours` = 3 400 / 100 = 34 ; cible = 30 ; statut : 3 400 ≤ 1,2 × 3 000 = 3 600 → **ATTENTION**.
- `securite` = 30 × 3 000 / 30 = 3 000 ; `besoin_net` = 3 000 + max(3 000, 3 000) − 3 400 − 0 = **2 600** →
  3 palettes → **3 000 kg** ; montant 60 000 USD = 570 000 MAD → Tier 1 (A et ≥ 300 000).

### 3.11 Petites fonctions du stock

- **`_palettes(quantite, contenance)`** (`:1480-1484`) : 0 si contenance nulle ; sinon
  `⌈quantite / contenance − 1e-9⌉` (à l'epsilon flottant près).
- **`_jours_securite(classe, p)`** (`:1487-1492`) : A → `securite_a`, B → `securite_b`, sinon (C, vide) → `securite_c`.
- **`_classer_abc(lignes, p)`** (`:1495-1528`) — `Stock!AA10` :
  ```
  total = Σ max(0, valeur_conso_annuelle_mad)
  ordre = tri décroissant par valeur (stable : ordre du catalogue entre ex æquo)
  cumul courant ; cumul_par_valeur[v] = cumul après le DERNIER ex æquo de valeur v
  rang = position du PREMIER ex æquo (RANG d'Excel : les suivants sautent d'autant)
  si total == 0 : pourcentage_cumule = 0, classe C pour tous
  sinon : pct = cumul_par_valeur[v] / total ; pct ≤ seuil_abc_a → A ; ≤ seuil_abc_b → B ; sinon C
  ```
  Le cumul se lit « part de la valeur portée par les références au moins aussi grosses que moi ».
  Exemple : 500, 300, 300, 100 (total 1 200) → 500 : 41,7 % A, rang 1 ; les deux 300 : 1 100/1 200 =
  91,7 % B, rang 2 ; 100 : 100 % C, rang 4. Une matière à 0 tombe à 100 % → C.

### 3.12 Plan d'achat (`:1531-1774`)

**`LignePlanAchat`** (`:1534-1559`) : `reference, nature, designation, fournisseur, classe_abc,
statut, quantite (kg), unite_achat, quantite_achat, unite_commande, unites_commande,
contenance_commande, prix (prix_kg), devise, montant_devise, montant_mad, palettes, tier, risque
(= sourcing), action, relance, en_preparation, bons_en_preparation`.

**`GroupeFournisseur`** (`:1562-1585`) : montants tenus **par devise** (LOMAT vend la colle en EUR
et la chaîne en USD ; les additionner n'a pas de sens), le dirham sert de comparateur.

**`PlanAchat`** (`:1588-1602`) : `references_a_commander, references_en_alerte, budget_mad,
quantite_totale, references_classe_a, ruptures, critiques, urgents, attentions, ok, tiers,
fournisseurs, lignes`.

**`_tier(ligne, p)`** (`:1605-1626`) — `Plan_Achat!M29`, dans l'ordre :

```
statut RUPTURE                                   → 🔥 TIER 1
corr. et statut CRITIQUE                         → 🔥 TIER 1
classe A et montant_mad ≥ seuil_tier1            → 🔥 TIER 1
montant_mad ≥ seuil_tier2                        → 🟠 TIER 2
corr. et statut URGENT                           → 🟠 TIER 2
montant_mad ≥ seuil_tier3                        → 🟡 TIER 3
sinon                                            → ⚪ TIER 4
```

**`ACTIONS_TIER`** (`:1629-1634`) : Tier 1 « Émettre cette semaine », Tier 2 « Émettre sous 7j »,
Tier 3 « Émettre sous 15j », Tier 4 « Regrouper sous 30j ».

**`plan_achat(donnees, lignes_stock)`** (`:1637-1774`) — feuille 📈 Plan_Achat :

```
a_commander = lignes avec quantite_a_commander > 0
en_alerte   = celles de a_commander dont statut ∈ STATUTS_EN_ALERTE
budget      = Σ montant_a_commander_mad de a_commander
détail      = en_alerte [classeur] | a_commander (corr. : tout ce que le budget compte, OK compris)
tri         = clé croissante de −( M × poids_classe + position / 10 000 000 )
              M = montant_a_commander (en DEVISE) [classeur] | montant_a_commander_mad (corr.)
              poids_classe : A → 3, B → 2, sinon 1 ; position = rang 1-based dans lignes_stock
pour chaque ligne triée : tier = _tier ; tiers[tier] += 1 ; LignePlanAchat avec
    relance = f"{statut} — {réf} ({fournisseur}) — Qté: {arrondi(qté):.0f} kg — {arrondi(montant):.0f} {devise} — Délai: {arrondi(délai):.0f}j"
par fournisseur (sur a_commander) :
    montant_mad = Σ ; montants_par_devise = Σ montant par devise ; ruptures / critiques / urgents = comptes
    presse = [classeur] ruptures > 0 ou montant_mad ≥ seuil_bc_urgent
             corr.      ruptures > 0 ou critiques > 0 ou urgents > 0     (le pire statut, pas le montant)
    urgence = « 🚨 BC URGENT » si presse ; « 📋 BC groupé » si montant_mad ≥ seuil_bc_groupe ;
              « 📝 Standard » si montant_mad > 0 ; « — » sinon
    pays, devise_par_defaut (MAD si inconnu), devises (triées), delai_jours (fournisseur.delai_jours, 0 si inconnu),
    contact, nb_references, quantite (Σ kg), part_budget = montant_mad / budget (0 si budget nul)
groupes triés par montant_mad décroissant (stable)
compteurs ruptures / critiques / urgents / attentions / ok : sur TOUTES les lignes de stock
references_classe_a : sur a_commander ; quantite_totale = Σ kg de a_commander
```

Le classeur affichait 119 « références en alerte » car son `COUNTIFS(Statut;"<>🟢 OK")` ne filtrait
rien (comparaison d'emoji toujours vraie) ; il pondérait le montant **en devise** (100 000 USD
pesaient comme 100 000 MAD : 14 des 83 lignes changent de rang une fois ramenées au dirham).

---

## 4. `depot.py` — la base traduite en `Donnees`

Le moteur ne connaît pas la base ; `depot.py` fabrique l'instantané (articles par référence, lots
par numéro, magasins par code) (`depot.py:1-7`).

### 4.1 Statuts (`depot.py:23-40`)

`STATUTS_MOTEUR` : brouillon → « Brouillon », a_approuver → « Brouillon », envoyee → « Envoyée »,
confirmee → « Confirmée », soldee → « Soldée », annulee → « Annulée ».
`QUALITE_MOTEUR` : conforme → « Conforme », reserve → « Réserve », refuse → « Refusé ».

**`statut_moteur(cmd)`** : un bon **qui a un numéro** (déjà parti) et dont le statut est
`brouillon` ou `a_approuver` (il repasse par la direction, ex. une hausse à approuver) se lit
« Confirmée » si toutes ses lignes ont un prix confirmé (et qu'il en a), sinon « Envoyée » : sa
quantité reste attendue, son retard reste un retard. Sinon la table ci-dessus.

### 4.2 `soldes_a_la_main(s)` (`:43-52`)

Pour chaque commande, la **dernière** action « commande soldée » du journal des actions (ordre
d'id) ; gardée si son détail **ne finit pas** par « tout reçu » (solde automatique). Rend
`{commande_id: quand}`. Le moteur ne l'utilise que pour `solde_a_la_main_le` des bons `soldee`.

### 4.3 Lignes reçues, retours, quarantaine (`:55-128`)

- **`_lignes_recues(s)`** : `(id, ligne de commande, lot, pesée, qualité)` des lignes de
  réceptions **validées**, qualité ≠ `refuse`.
- **`_au_prorata(par_lot, lignes)`** : répartit une quantité connue au lot entre les lignes de
  réception de ce lot, au prorata de leur pesée, **plafonnée** à la pesée de la ligne :
  `part[ligne] = min(pesée, q_lot × pesée / Σ pesées du lot)`.
- **`retours_par_ligne_reception(s, lignes)`** : `retours[lot] = −Σ quantite` des mouvements
  `RETOUR_FOURNISSEUR` du lot (en base les quantités sont signées : un retour est négatif, son
  annulation positive), gardé si > 1e-9 ; réparti par `_au_prorata`.
- **`recu_par_ligne(s, net=True)`** : par ligne de commande, `Σ (pesée − retour réparti)` des
  lignes reçues ; `net=False` : pesée seule. **Le reçu est net des retours** : une matière renvoyée
  est due à nouveau par le fournisseur (le bon n'est pas livré tant qu'il ne l'a pas remplacée ou
  qu'on ne l'a pas soldé). Les lignes « réserve » (quarantaine) **comptent** comme reçues.
- **`en_quarantaine_par_ligne(s)`** : pour les lignes reçues en `reserve` avec un lot, le solde
  actuel du lot dans les magasins de type « Quarantaine » (> 1e-9), réparti par `_au_prorata`, puis
  sommé par ligne de commande. **Non utilisé par `_charger`** (donc invisible du moteur) ; sert à
  l'écran des achats pour ne solder un bon qu'à la libération (`api/achats.py:113`, `:589`).

### 4.4 `poids_bobine_mesures(s)` (`:131-149`) — M43

Par article : le `poids_bobine` (> 0) du lot **sorti le plus récemment vers les machines**
(mouvements `SORTIE` de quantité < 0, par `date_effet` puis id décroissants) → `(kg, lot, "sorti")` ;
à défaut celui du dernier lot reçu (par `entre_le` puis id décroissants) → `(kg, lot, "reçu")`.
Une sortie ensuite annulée compte encore (son mouvement d'origine reste < 0).

### 4.5 Versions du plan (`:152-223`)

- **`MARQUE_PLAN = "plan="`**. **`versions_plan(s)`** : actions du journal `action = "plan de
  production"`, `objet = "qualite"`, dont le détail contient `plan=` ; on lit le JSON après la
  marque : `{"avant": {...}, "apres": {...}}`, chaque plan `{b: base, c: [12 coefficients], a:
  en service}` (`a` absent = en service). Les détails illisibles sont ignorés. Rend par qualité la
  liste ordonnée par `(quand, id)` de `(quand, avant, après)`.
- **`_versions_du_plan(brut, ouverture)`** :
  ```
  versions[0] = VersionPlan(quand=None, plan "avant" du PREMIER changement, depuis = ouverture)
  pour chaque changement (quand, _, apres) :
      v = VersionPlan(quand, apres, depuis = quand.date())
      si v.base == base de la version précédente : v.depuis = depuis précédent
  ```
  Seule une **nouvelle base** déplace l'origine de la croissance (retoucher la saisonnalité de
  décembre 1,2 → 1,3 retirait 4,8 % aux onze autres mois). Défauts : `b` 0, `c` 12 × 1,0, `a` vrai.
- **`_arret_sans_histoire(versions, dernier)`** — qualité arrêtée **avant** que l'arrêt ne soit
  tracé (`versions[0].actif` faux) : elle l'a été après son dernier tissage.
  ```
  arret = datetime.min                       si jamais tissée
        = 1er du mois qui suit le dernier tissage, 00:00   sinon
  si une version tracée suit : arret = min(arret, versions[1].quand)
  rend [ (None, base d'avant, actif=True), (arret, base d'avant, actif=False), *versions[1:] ]
  ```
  Ni « arrêtée depuis toujours » (effaçait le passé), ni « jamais arrêtée » (prévoyait ses fils sur
  des mois où on ne la tissait plus).

### 4.6 `_charger(s, avec_journal=True)` (`:236-547`)

| Partie | Traduction |
|---|---|
| Articles (triés par `reference`, **ordre de la base**) | `role_bom = role` ; `nature = Composition.libelle` ; `titrage = Titrage.valeur` ; `titrage_unite = Titrage.unite` ; `unite_prix = unite_prix or "kg"` ; `fournisseur = nom` ; `prix_unite = prix` ; `bob_palette = bobines_palette` ; `unite_commande = "" si unite_achat == "kg" sinon unite_achat` ; `contenance_commande = 0 si kg sinon contenance_achat` ; `couleur = Couleur.libelle or code` ; le reste tel quel. |
| Ouverture | `ouverture = min(Mouvement.date_effet)` (None sans mouvement) : origine de la croissance d'un plan jamais changé. |
| Dernier tissage | par qualité, `max(BonSortie.date)` des bons de sortie **validés** qui la fabriquent. |
| Qualités | `Qualite(code, nom, poids = {rôle: poids})` ; saisonnalité = coefficients 1..12 (1,0 par défaut). |
| Versions du plan | `_versions_du_plan(journal, ouverture)` ; si aucune et qualité inactive : `[VersionPlan(None, base, saisons, actif=False, depuis=ouverture)]` ; si `versions[0]` inactive → `_arret_sans_histoire(versions, dernier tissage)`. |
| Plan | `PlanQualite(code, base_mensuelle, saisonnalite, actif, depuis = versions[-1].depuis si versions sinon ouverture)` ; une qualité arrêtée **garde sa base**. |
| Versions de recette | `RecetteVersion` triées `(quand, id)`, qualités connues ; `contenu` JSON `[{reference, pourcentage}]`, `poids` JSON ou None ; illisibles ignorées. |
| Recettes | `LigneRecette(code qualité, référence, pourcentage)`. |
| Commandes (par id) | `numero = numero or "BC-brouillon-{id}"` ; `date_bc = date_commande` ; `statut = statut_moteur` ; `solde_a_la_main_le` si `soldee` ; lignes : `quantite_commandee = quantite`, `quantite_recue = recu_par_ligne (net)`, `prix_unite = prix`, `devise = devise du bon`, `prix_confirme`, `unite_commande = unite_achat`, `contenance_commande = contenance`, `prix_estime` (confirmé, sinon prix catalogue converti : `prix × taux[devise article] / taux[devise bon]`, `api/achats.py:153-166`), `cours = cours figé du bon`. |
| Réceptions (non annulées, par date puis id) | `numero = numero or "REC-brouillon-{id}"` ; `numero_bc` = le bon commun si toutes les lignes rattachées sont du même bon, sinon `""` ; `statut = "Validée"` si validée, sinon « Brouillon » ; lignes : `quantite_commandee = quantite_attendue`, `tolerance_partielle = toler_ecart_pesee`, `magasin = code`, `statut_qualite`, `numero_bc` de la ligne. |
| Historique des prix | pour chaque réception **validée**, ligne non refusée, pesée ≠ 0 et prix ≠ 0 : `LignePrix(date = date de réception, réf, fournisseur, bon (sinon n° de réception), pesée, prix, devise de la ligne)`. |
| Journal | `_journal(...)` si `avec_journal`, sinon `[]` ; soldes `_soldes` sinon `None`. |
| Dossiers d'import | statut `Clos`/`Ouvert` ; lignes (id, réf, quantité, valeur, devise, cours, lot, fournisseur, ligne de réception) ; charges (`recuperable_poste` et `cle` du référentiel `PosteFrais` s'il connaît le poste, sinon None / « valeur » ; `parts` figées) ; facture (numéro, montant, devise). |
| Ordres | bons de sortie **validés** : `theorique = JSON["fils"]`, `perte = JSON["perte"]` si figés, sinon None. |
| Métiers (par code) | fils : `poids_bobine = poids_bobine_mesures[article][0]` (0 sinon). |
| Paramètres | `parametres.pour_le_moteur(s)` (§1.2). |
| Magasins | `Magasin(code, nom, type, actif)` (`contenu` non tenu). |

### 4.7 `_journal` et `_traduire` — le journal signé devient le journal du moteur (`:601-660`)

En base, une ligne par lot et par magasin, **quantité signée** ; pour le moteur, quantité
« positive » et signe porté par le type.

```
mouvements triés par (date_effet, id)
TRANSFERT : accumulés par paire (x.paire, sinon −x.id) ; quand la paire a 2 lignes :
            source = celle de quantité < 0 ; UN mouvement TRANSFERT_MAGASIN :
            quantite = |source.quantite|, source → destination, identité (id, contrepasse) de la source
            (une jambe sans partenaire n'est jamais émise)
autre type, signe = signe du type moteur :
   signe < 0 (SORTIE, RETOUR_FOURNISSEUR) : quantite = −x.quantite, magasin_source = magasin
   sinon                                  : quantite =  x.quantite, magasin_destination = magasin
```

Conséquences : une sortie normale (−100 en base) → +100 ; son **annulation** (+100 en base) →
**−100** de type SORTIE_PROD ; une réception annulée → −q de type ENTREE_RECEPTION ; un ajustement
négatif → quantité négative de type AJUSTEMENT. Les contre-passations se retranchent donc d'elles-mêmes
dans les sommes signées.

`_traduire` : `date = date_effet`, `type` moteur, `prix_unite = prix`, `devise = devise or "MAD"`,
`total_devise = quantite (traduite) × prix`, `reference_doc = document_numero`, `lot_fournisseur`
= numéro du lot, `numero_of` = numéro du bon de sortie (`ordre_id`), `motif_retour = _code_motif`,
`utilisateur = auteur`, `fournisseur` = fournisseur **du lot**, `id`, `contrepasse_id`,
`cours = cours or 0`, `ligne_reception_id`.

**`_code_motif(motif)`** (`:226-233`) : si le texte commence par « R » + chiffre → ses 2 premiers
caractères ; sinon `CODES_MOTIF` (`api/operations.py:49-53`) : Reliquat de fin d'ordre → R1 ;
Changement de série / arrêt machine → R2 ; Non-conformité qualité → R3 ; Refus après quarantaine
→ R3 ; Erreur de prélèvement → R4 ; Excédent de réception → R5 ; Bobines endommagées → R6 ; inconnu → `""`.

**`_lignes_des_receptions(s)`** (`:562-598`) — {mouvement : ligne de réception} : pour chaque
mouvement `RECEPTION` de document « reception », dans l'ordre des id : une annulation reprend la
ligne de l'entrée qu'elle défait ; sinon les candidates sont les lignes (non refusées, avec lot) de
**sa** réception sur ce lot, dans l'ordre des lignes, ou, pour une entrée reprise de l'ERP Fil sans
réception, les lignes de même `(lot, date de réception, pesée arrondie à 6 décimales)` ; on prend
la première non encore prise.

**`_soldes(s)`** (`:550-559`) : `{(référence, numéro de lot, code magasin): quantité}` de la table
`solde` (C12 les confronte au journal).

### 4.8 Cache, chargement à une date, contrôles (`:663-712`)

- **`_signature(s)`** = `(date du jour, max id du journal des actions, max id des mouvements, max
  modifie_le des réglages, nombre de mouvements, Σ quantités des soldes)`. Toute écriture (geste
  au journal, mouvement, réglage) ou un solde modifié hors du chemin normal, ou le changement de
  jour, invalide le cache.
- **`charger(s, avec_journal)`** : sous verrou, rend l'instantané en cache (un par valeur de
  `avec_journal`) si la signature n'a pas changé, sinon relit (`_charger`). L'objet est **partagé**
  entre les requêtes : le moteur ne doit pas le modifier.
- **`charger_au(s, jour)`** = `moteur.a_la_date(charger(s), jour, aujourdhui=date.today())`.
- **`controler(s, donnees, lignes, jour)`** = `controles.controler(donnees, lignes, jour,
  complet=charger(s), aujourdhui=date.today())` : stock et plan sur les données du jour,
  intégrité (soldes contre journal, écritures futures, lots sous zéro) sur **toutes** les données.

Usage courant : `donnees = depot.charger_au(s, jour)` puis `moteur.etat_stock(donnees, jour)`
(`api/pilotage.py:51`, `api/exports.py:134`, `api/production_plan.py:219`…).

---

## 5. `services/stock.py` — l'écriture du stock (calculs à l'écriture)

Un seul chemin d'écriture, sous verrou de ligne (`services/stock.py:1-7`). **Aucun coût moyen
(CMUP) n'est calculé à l'écriture** : on écrit le prix d'entrée et le **cours figé** ; le CMUP est
recalculé depuis le journal par le moteur (partie B).

- **`POUSSIERE = 1e-3`** (`:20`).
- **`kg(valeur, decimales=2)`** (`:23-24`) : format français (espace des milliers, virgule décimale).
- **`kg_et_metres(valeur, article)`** (`:27-32`) : « 14,30 kg », et pour un rôle linéaire de
  densité connue « 14,30 kg ≈ 1 021 ml » (`valeur / densite`, 0 décimale).
- **`lot_ou_creer(s, article_id, numero, entre_le, fournisseur_id, poids_bobine)`** (`:35-60`) :
  numéro obligatoire (sinon refus « … ou « Lot interne » ») ; crée le lot (insert « on conflict do
  nothing » sur (article, numéro)) ; s'il existe : complète le fournisseur s'il manquait, **remplace**
  le poids de bobine si un nouveau est donné.
- **`_solde_verrouille(s, lot, magasin)`** (`:63-74`) : crée le solde à 0 au besoin, puis le lit
  `FOR UPDATE`.
- **`couvert_a_sa_date(s, lot, magasin, quantite, jour)`** (`:77-119`) — une sortie datée `jour`
  doit trouver la matière ce jour-là **et ne pas faire manquer ensuite** :
  ```
  par_jour = Σ quantités du lot dans ce magasin par date_effet, triées
  cumul = 0 ; manque = None
  pour chaque (d, q) : cumul += q ; si d ≥ jour et cumul + quantite < −1e-3 et pas de manque : manque = (d, cumul)
  au_jour = Σ q des dates ≤ jour ; si au_jour + quantite < −1e-3 : manque = (jour, au_jour)
  ```
  S'il y a manque : si le lot n'est **jamais** entré dans le magasin, ou n'y est entré qu'après
  `jour` → refus 409 « … ne peut pas le prendre » ; sinon refus 409 « Au {date}, il n'y avait que
  {max(disponible, 0)} kg … » (avec « la matière est sortie depuis par d'autres écritures » si le
  manque est postérieur). Le contrôle est **par jour** (l'ordre dans la journée n'est pas regardé).
  Raison : une sortie datée d'hier prenait un lot arrivé ce matin, stock négatif hier, sortie à coût
  nul (audit 2-G B1).
- **`ecrire(...)`** (`:122-212`) :
  1. quantité `|q| < 1e-9` → refus ; `date_permise(jour)` : refus avant le 01/01/2000, dans le
     futur, ou ≤ `date_cloture` (période close) (`securite.py:210-226`) ;
  2. magasin inconnu → refus ; magasin **désactivé** et quantité > 0 → refus ;
  3. verrou du solde **avant** de regarder l'inventaire ; hors document « inventaire », un
     inventaire **ouvert** sur ce magasin ou sur tous → refus 409 ;
  4. `solde + quantite < −1e-3` → refus 409 (au gramme) ;
  5. si `quantite < 0` → `couvert_a_sa_date` ;
  6. **cours** : `devise = (devise or "MAD").upper()` ; si MAD ou prix nul → `cours = cours or 0` ;
     sinon si pas de cours fourni → `Devise.taux` du jour (0 si inconnue) ; sinon le cours fourni
     (celui que la commande a figé) ;
  7. `solde = round(solde + quantite, 6)`, ramené à 0 si `|solde| < 1e-3` ;
  8. ajoute le mouvement (date d'effet, type, article, lot, magasin, quantité signée, prix, devise,
     cours, document, numéro, ordre, paire, motif, commentaire, auteur, contre-passation).
- **`transferer(...)`** (`:215-227`) : refus si source = destination ; écrit `−q` dans la source
  (sa `paire` = son propre id), puis `+q` dans la destination avec la même `paire`. Le transfert
  porte prix 0.
- **`contrepasser_document(s, document, document_id, auteur)`** (`:230-270`) : annule un document
  en écrivant l'**inverse** de chacune de ses lignes non encore contre-passées (et qui ne sont pas
  elles-mêmes des contre-passations), **datée comme l'original**, au **même prix, devise et cours**,
  commentaire « Annulation du mouvement n°{id} », `contrepasse_id = id` ; refus 409 si tout est déjà
  annulé. Ordre : d'abord l'inverse des **sorties** (quantité < 0 → on remet ce qui est sorti),
  ensuite celui des entrées, chacun par id croissant. Les paires de transfert sont recréées (la
  première inverse d'une paire devient la paire de l'autre). Chaque inverse repasse par `ecrire`
  (solde, inventaire ouvert, `couvert_a_sa_date`, période close).
- **`disponibles(s, article_id, magasin_id=None)`** (`:273-300`) : lots de l'article avec un solde
  > 1e-3 dans un magasin **qui n'est pas de type Quarantaine**, triés par `entre_le` puis id (FIFO :
  l'ordre où le magasin doit les sortir) ; filtrable par magasin.
- **`solde_article(s, article_id)`** (`:303-310`) : Σ des soldes de tous les lots, **tous magasins,
  quarantaine comprise**.

---

## 6. Points incohérents ou ambigus

1. **Tri du plan d'achat entre ex æquo** (`moteur.py:1649-1669`) : le commentaire dit « par rang
   dans le catalogue, le plus bas d'abord », mais la clé `−(M × poids + position/10⁷)` place, à
   montant égal, la **position la plus haute** en premier (et deux montants qui diffèrent de moins
   de position/10⁷ peuvent s'inverser). À trancher pour la parité : reproduire le code.
2. **Ordre du catalogue = ordre SQL** (`depot.py:245`, `ORDER BY reference` sous la collation
   PostgreSQL) : il fixe la position du tri du plan d'achat, l'ordre ABC des ex æquo et l'ordre des
   substituts. Un tri Python (`sorted`) peut différer (casse, accents, espaces).
3. **Retour à la règle « FIX P1 » en méthode corrigée** (`moteur.py:1110-1119`) : si la fenêtre
   tombe à 0 mois (pas de sortie de l'usine assez tôt, ou réglage à 0), la consommation redevient
   `max(historique, plan/12)`, où l'historique = **toutes** les sorties depuis la première
   ÷ mois écoulés — une règle classeur qui survit en corrigé, avec une autre sémantique que la
   fenêtre (pas de coefficient, pas d'héritage, pas de hors recette).
4. **Fil monté compté deux fois ?** La sortie vers les machines compte comme **consommée** (réel
   du coefficient de réalisation, XYZ, historique) **et** le fil monté revient dans le disponible, le
   projeté et la valeur (`moteur.py:1157`, `:1188` ; partie B). Le montage est déclaré (mètres ×
   densité du métier × poids de bobine × remplissage des bobines / 100), sans lien avec les sorties du journal : il peut
   excéder ce qui est réellement sorti. Historique de la décision contradictoire dans les commits :
   `202d1a0` « hors du disponible… et de la valeur », `f33a428` « dans le disponible, valeur à
   part », `169dfdc` « compté et valorisé » (état actuel).
5. **Quarantaine** : retirée du projeté → la matière en quarantaine **déclenche un rachat**, alors
   que la ligne de bon reçue « sous réserve » compte comme **reçue** pour le moteur (le reste à livrer
   baisse) ; `en_quarantaine_par_ligne` n'est pas transmis au moteur. Elle est aussi retirée en mode
   [classeur] (le classeur ne la connaissait pas : parité seulement sans magasin de quarantaine).
6. **Mois de 30 jours contre mois civil** : les fenêtres de demande comptent 30 j (`jours_restants
   = max(0, 30 − jour)` : le 30 et le 31 → 0 ; en février, le 28 laisse 2 jours) alors que
   `m2_passe` proratise sur la vraie durée du mois (à la seconde).
7. **Horizon tronqué à 12 mois** (`besoin_sur_fenetre`) : un délai + couverture + 30 j au-delà
   d'environ 360 j voit une demande nulle au-delà, et `conso_horizon` est divisé par tout l'horizon
   (dilué).
8. **`int(delai)`** tronque les délais fractionnaires pour les dates limites des commandes, alors
   que `besoin_sur_fenetre` utilise le délai exact.
9. **`a_la_date`** : (a) un bon livré après la date repasse « Confirmée » même s'il était
   « Envoyée » ; (b) un bon soldé **à la main** ou **annulé** après la date reste clos à la date
   passée ; (c) le plan, les recettes, le catalogue (prix, stock min, délais, actif) et les réglages
   sont ceux d'aujourd'hui ; (d) le retour fournisseur au prorata n'y est pas plafonné, contrairement
   à `depot._au_prorata` ; (e) si rien n'a été écrit après la date, les **soldes** d'aujourd'hui sont
   gardés (alors qu'ils sont mis à `None` sinon).
10. **Ancre de croissance** : `plan_mensuel` prend `ligne.depuis or date_ref`, `m2_passe` sans
    versions prend `version.depuis or fin` ; sans aucun mouvement (`ouverture` None), les deux
    diffèrent.
11. **Versions de recette partielles** : seules la part des références et les poids au m² sont
    versionnés ; le rôle et la densité des articles sont lus **aujourd'hui** (`kg_m2_version`) — un
    changement de densité réécrit le passé.
12. **`besoins_passes`** retient la **dernière** version du mois pour le prévu (non proratisée) ; le
    mois est alors « instable » et exclu du coefficient, mais ce prévu entre dans les poids de
    l'héritage (`Σ prevus_passes`, mois instables compris).
13. **`fils_remplaces`** apparie par rôle actuel : deux références hors catalogue (rôle `None`) se
    « remplacent ».
14. **Fenêtre de réalisation au niveau usine** : la première sortie qui raccourcit la fenêtre est
    celle de **toutes** les références (pas celle de l'article).
15. **Coefficient non abaissé en rupture** : la condition regarde `stock_net` (magasins), pas le
    stock en machine.
16. **XYZ** : une série parfaitement régulière (cv = 0) est classée « — » comme une matière sans
    sortie, au lieu de X.
17. **Délai d'un fournisseur inconnu** : les lignes de stock prennent `delai_defaut`, le groupe
    fournisseur du plan d'achat affiche `0`.
18. **Statut [classeur]** : jamais « NON CONSOMMÉE » (le statut de couverture écrase tout, conso nulle → OK).
19. **Conditionnement** : l'arrondi ne joue que si la contenance est **> 1** kg ; une unité déclarée
    de 0,5 kg (ou exactement 1) n'arrondit pas. Le minimum de commande s'applique avant l'arrondi.
20. **Montants à commander au prix du catalogue** (`prix_kg`), pas au dernier prix payé ni au CMUP ;
    la classe ABC aussi.
21. **`Parametres`** : docstring « 43 cellules » (45 champs) ; `secteur` par défaut `""` contre
    « Fabrication de tapis mécaniques » dans les réglages ; `devise`, `date_saisie` inutilisés ;
    `TAUX_TVA_IMPORT` doublonne `taux_tva_import` ; `priorite_equiv` et `Magasin.contenu` sans effet.
22. **`_mot_couleur`** : « moucheté » (avec accent) ne peut jamais être reconnu, le mot testé étant
    désaccentué.
23. **Journal** : une jambe de transfert sans partenaire est **silencieusement ignorée**
    (`depot.py:613-616`), le journal du moteur s'écarte alors des soldes.
24. **`poids_bobine_mesures`** retient le lot d'une sortie qui a pu être annulée depuis ; le poids
    pesé s'applique à **tous** les fils montés de l'article (pas par métier).
25. **`couvert_a_sa_date`** contrôle par jour : l'ordre des écritures dans une même journée est
    ignoré (une sortie et l'entrée du même jour s'équilibrent).
26. **Dormants** : la « dernière entrée » inclut le stock d'ouverture et les retours des machines ;
    un fil seulement monté (en machine) n'entre pas dans le stock qui « dort ».
27. **Compteurs du plan d'achat** : ruptures/critiques/urgents/attentions/ok sur **toutes** les
    lignes, `references_classe_a` sur les lignes à commander seulement.
28. **`_classer_abc`** : le total ignore les valeurs négatives (`max(0, v)`) mais le cumul les
    additionne (cas théorique d'un prix négatif).


# CALCULS — partie B : valeur, prix, cockpit, fournisseurs, lots, ordres, importations, suivi

> Source de vérité : le code de Gestion MP (`/Users/mohamed/gestion-mp`, lu le 8 octobre 2026,
> dernier commit `2d588b9`). Références `fichier:ligne` relatives à `gestion_mp/`.
> Périmètre : `calcul/moteur.py` lignes 1777 à 3760, et les calculs faits dans les routes
> (`api/pilotage.py`, `api/analyse_import.py`, `api/suivi.py`, `api/production_plan.py`,
> `api/production.py` pour `consommations`/`ajuster_ordre`, `api/inventaires.py`,
> `services/courriel.py`). Ce qui relève de `moteur.py` 1–1780 (plan, besoins, nomenclature,
> `etat_stock`, ABC/XYZ, tier, plan d'achat, `a_la_date`), de `modele.py`, de `depot.py` et de
> `services/stock.py` est dans la partie A : on y renvoie par le nom du champ.

---

## 0. Conventions communes à toute la partie B

### 0.1 Le « mode classeur »

`Parametres.methode` vaut `"corrigee"` (défaut) ou `"classeur"` ; `Parametres.mode_classeur`
est vrai pour `"classeur"` (`calcul/modele.py:131-137`).

- **En production, le mode est toujours « corrigée »** : `parametres.pour_le_moteur` écrase la
  valeur (`parametres.py:185`, `p.methode = "corrigee"`). Le mode classeur n'est vivant que
  dans les essais de parité (`tests/test_parite.py`), qui vérifient que le moteur retrouve les
  valeurs mises en cache par Excel dans le classeur d'origine (celui que l'ERP Fil avait
  repris). Le moteur de Gestion MP est celui de l'ERP Fil, plus des corrections ; l'ERP Fil
  lui-même tournait en « corrigée ». La comparaison avec l'ERP Fil (`docs/COMPARAISON-ERP-FIL.md`)
  est un **autre** exercice : mêmes données, chaque logiciel calcule, chaque écart est
  expliqué (0 à corriger).
- Pour la réécriture : **la parité testée est celle du mode « corrigée »** (c'est ce que
  l'année d'essai produit). Le mode classeur est documenté ici pour être complet : chaque
  branche `if parametres.mode_classeur` est signalée « [classeur] ».

### 0.2 Change

`Parametres.taux(devise)` (`modele.py:139-148`) : la table `devise` (cours courant vers le
dirham, `Parametres.cours`) si la devise y est ; sinon `taux_eur_mad` pour EUR, `taux_usd_mad`
pour USD ; **toute autre devise (MAD compris, ou vide) vaut 1**. Les cours ne sont pas datés :
« le cours du jour » = le cours courant de la table.

Cours figés (lus par les calculs ci-dessous) :

| Où | Champ | Sens |
|---|---|---|
| Mouvement du journal | `Mouvement.cours` (`modele.py:344`) | cours figé à la validation de l'écriture (celui du bon s'il l'a figé, sinon celui du jour) ; 0 = inconnu → cours du jour |
| Ligne de bon | `LigneCommande.cours` (= `Commande.cours` en base) | cours figé du bon à la confirmation des prix ; 0 → cours du jour |
| Ligne de dossier d'importation | `LigneImport.cours` | cours de la banque saisi par dossier (figé à la clôture) ; 0 → cours du jour ; **ignoré si la ligne est en MAD** |

### 0.3 Journal du moteur (rappel de la traduction `depot._journal`, partie A)

- Quantité du moteur **positive**, signe porté par le type (`TYPES_MOUVEMENT`, `modele.py:28-37`) :
  `STOCK_INITIAL` +1, `ENTREE_RECEPTION` +1, `SORTIE_PROD` −1, `RETOUR_PRODUCTION` +1,
  `RETOUR_FOURNISSEUR` −1, `AJUSTEMENT_INVENTAIRE` +1, `TRANSFERT_MAGASIN` 0, `QUARANTAINE` 0.
- Une **annulation (contre-passation)** garde le type de l'écriture annulée, porte
  `contrepasse_id = id de l'original`, et une quantité **négative** dans le moteur (la base
  stocke des quantités signées : `depot.py:601-670`). Donc `quantite_signee = quantite × signe`
  est de signe opposé à celle de l'original. Un ajustement d'inventaire négatif est un
  `AJUSTEMENT_INVENTAIRE` de quantité négative (pas une annulation).
- Un transfert = une seule ligne moteur (source → destination), quantité = |q|.
- `Mouvement.fournisseur` = le fournisseur **du lot** ; `ligne_reception_id` = la ligne de
  réception qui a écrit l'entrée (appariement `depot._lignes_des_receptions`).
- Une annulation est **datée comme l'écriture qu'elle défait** (règle de Gestion MP, et de la
  reprise ERP Fil depuis `673c02c`).

### 0.4 Dates de référence

`depot.charger_au(s, jour)` = `moteur.a_la_date(charger(s), jour, aujourdhui=date.today())`
(`depot.py:686-691`, partie A) : à une date passée, journal, réceptions, commandes (reçu
recalculé), prix payés et ordres sont tronqués au soir de `jour` ; **les dossiers
d'importation, le catalogue et les réglages restent ceux d'aujourd'hui** ; le fil monté sur
les métiers ne compte pas (`montage_connu = False`).

### 0.5 Constantes

`MOIS = 12`, `JOURS_PAR_MOIS = 30`, `SANS_LOT = "(sans lot)"`, `POUSSIERE = 1e-3` (moteur et
`services/stock.py:20`), seuil « vide » `1e-9` partout dans le CMUP. `arrondi(v, d)` =
ARRONDI d'Excel (demi au-dessus en valeur absolue, `moteur.py:52-60`), à ne pas confondre avec
`round()` de Python (au pair).

---

## 1. Valorisation au coût moyen (CMUP)

### 1.1 `LigneValorisation` (`moteur.py:1780-1796`)

| Champ | Contenu |
|---|---|
| `reference`, `nature`, `fournisseur`, `devise` | du catalogue (`devise` = `article.devise`) |
| `prix_catalogue` | `article.prix_kg` (prix au kilo, voir partie A) |
| `cmup_mad` | coût unitaire retenu (`cmup_par_reference`) |
| `stock_magasin` | `LigneStock.stock_net` : tous les magasins, **quarantaine comprise** |
| `stock_machine` | `LigneStock.stock_machine` : fil monté sur les métiers, pas encore tissé |
| `stock` | `stock_magasin + stock_machine` |
| `valeur_magasin_mad` | `cmup × stock_magasin` |
| `valeur_machine_mad` | `cmup × stock_machine` |
| `valeur_mad` | `cmup × stock` (magasin **et** machine — le commentaire du code « les magasins seuls » est périmé, voir § 12) |
| `ecart_mad` | `valeur_mad − stock × article.prix_kg × taux(article.devise)` (écart au catalogue) |

### 1.2 `CoutsDuJournal` (`moteur.py:1799-1814`)

Résultat du rejeu du journal ; **seule source du CMUP** (Valorisation, Cockpit, journal
valorisé `api/stock.py:60-71`, inventaire, valeur des fils montés `api/referentiels.py:1220`,
bilan du mois). Champs :

- `unitaire: {id du mouvement → coût unitaire MAD au moment de l'écriture}` ;
- `stock: {référence → [quantité, valeur MAD]}` (après tout le journal) ;
- `consommation: [(date, valeur MAD)]` : pour chaque `SORTIE_PROD` et `RETOUR_PRODUCTION`
  (annulations comprises), la baisse de valeur du stock qu'elle a provoquée
  (`avant − après`, négative pour un retour ou une annulation de sortie).
- `cmup()` = `{ref : valeur / quantité}` pour les seules références dont `quantité > 1e-9`.
  **Une matière sans stock n'a pas de CMUP** (absente du dictionnaire) ; un CMUP nul est un
  vrai coût (`61027e4`).

`ACHATS_JOURNAL = ("STOCK_INITIAL", "ENTREE_RECEPTION")` (`moteur.py:1817`) : les seules
écritures qui « achètent » (entrent à leur coût d'entrée et déplacent la moyenne).

### 1.3 `couts_du_journal(donnees) → CoutsDuJournal` (`moteur.py:1820-1970`)

CMUP **glissant comptable** : la moyenne se recalcule à chaque entrée, les sorties partent au
coût moyen du moment. (Le classeur moyennait tous les achats depuis toujours : 100 kg à 10
consommés puis 10 kg à 20 → il affichait 10,90 ; ici 20.)

**Préalables.**
`revient_ligne = revient_par_reception(donnees)` (§ 9.10), `revient_lot = revient_par_lot(donnees)`
(§ 9.11), `taux = parametres.taux`. États :
- `etat[ref] = [q, v]` (défaut `[0, 0]`) ;
- `entrees_lot[(ref, lot)] = [q, v]` : ce que chaque lot a coûté **à l'achat** (types
  `ACHATS_JOURNAL`), net des annulations d'achats ;
- `sortie_ordre[(OF, ref, lot)]` et `sortie_ordre[(OF, ref)]` : coût de la **dernière**
  `SORTIE_PROD` non annulée de cet ordre ;
- `dernier_moyen[ref]` : dernier CMUP connu tant que la matière avait du stock.

**Ordre de rejeu** (`ordre`, `moteur.py:1897-1904`) — clé de tri :
- écriture ordinaire : `(date, id, 0, 0)` ;
- annulation : `(date, contrepasse_id, 1, id)` → elle se rejoue **juste après son original**
  (si même date), avant toute autre écriture du même jour de numéro supérieur. Sinon une
  sortie du même jour partait au coût moyen d'un stock où l'écriture annulée pesait encore
  (audit 2-A G1, commit `61027e4`).
- `id None` vaut 0.

**Pour chaque mouvement, dans cet ordre :**

1. Article inconnu du catalogue → ignoré (aucun coût, aucun `unitaire`).
2. `bloc = etat[ref]` ; `moyen = bloc.v / bloc.q si bloc.q > 1e-9 sinon 0`.
3. `signe == 0` (transfert) → `unitaire[id] = moyen` ; rien ne bouge ; suivant.
4. `signee = quantite × signe` (> 0 entre, < 0 sort).
5. `annule = contrepasse_id ≠ None et contrepasse_id ∈ unitaire` (l'original a déjà un coût,
   **même 0**).
6. Choix du coût unitaire `cout` :

| Cas | Condition | `cout` | Effet de bord |
|---|---|---|---|
| Annulation | `annule` | `unitaire[contrepasse_id]` (coût de l'original) | si type ∈ `ACHATS_JOURNAL` : `entrees_lot[(ref,lot)] += (signee, signee × cout)` (l'entrée annulée ne compte plus pour son lot) |
| Achat | `signee > 0`, type ∈ `ACHATS_JOURNAL`, `quantite > 0` | `cout_d_entree` | `entrees_lot[(ref,lot)] += (signee, signee × cout)` |
| Ré-entrée sur stock non vide | `signee > 0`, pas un achat, `bloc.q > 1e-9` | `moyen` (ne déplace pas la moyenne) | — |
| Ré-entrée sur stock vide | `signee > 0`, pas un achat, `bloc.q ≤ 1e-9` | `cout_de_reentree` | — |
| Sortie | `signee ≤ 0`, pas une annulation | `moyen` ; **si** `RETOUR_FOURNISSEUR` et `entrees_lot[(ref,lot)].q > 1e-9` : coût d'entrée du lot `v/q` | si `SORTIE_PROD` avec n° d'OF : `sortie_ordre[(OF,ref,lot)] = sortie_ordre[(OF,ref)] = cout` |

`cout_d_entree(mouvement, article)` (`moteur.py:1860-1876`) :
1. si `ligne_reception_id` non vide : `r = revient_ligne.get(ligne_reception_id)` ; si
   `r` existe et `r.revient_unite > 0` → **`r.revient_unite`** (coût de revient hors TVA du
   dossier d'importation, frais compris) ;
2. sinon, **seulement si `ligne_reception_id` est vide** (stock d'ouverture, reprise) :
   `revient_lot.get((ref, lot))` s'il est « vrai » (≠ 0) → ce coût ;
3. sinon si `prix_unite` non nul : `prix_unite × (mouvement.cours or taux(mouvement.devise or article.devise))` — **cours figé sur le mouvement** ;
4. sinon : `article.prix_kg × taux(article.devise)` (catalogue, dans la devise du catalogue).

> Conséquence à reproduire : une entrée **à prix 0** prend le prix du catalogue (étape 3
> sautée car `0` est faux). Le « coût nul est un coût » ne vaut que pour une annulation et pour
> le CMUP (voir § 12).

`cout_de_reentree(mouvement, article)` (`moteur.py:1878-1895`) — matière qu'on n'achète pas
(retour des machines, excédent d'inventaire, lot retrouvé) entrant dans un stock vide :
1. `RETOUR_PRODUCTION` avec n° d'OF : `sortie_ordre[(OF, ref, lot)]`, sinon
   `sortie_ordre[(OF, ref)]` (le coût de la sortie qu'elle rend) ;
2. sinon le coût d'entrée de son lot `entrees_lot[(ref,lot)]` si `q > 1e-9` **et** `v > 0` ;
3. sinon `dernier_moyen[ref]` ;
4. sinon le catalogue `article.prix_kg × taux(article.devise)`.
(Avant `61027e4` le catalogue venait d'abord : un reliquat sorti à 10 rentrait à 50.)

7. Mise à jour du bloc (`avant = bloc.v`) :
   - entrée (`signee > 0`) : `q += signee ; v += signee × cout` ;
   - sortie : `sortie = min(−signee, bloc.q) si bloc.q > 0 sinon 0` ; `q −= sortie ;
     v −= sortie × cout` ; puis **plancher** : si `q ≤ 1e-9` → `q = max(q, 0), v = 0` ; sinon si
     `v < 0` → `v = 0`. (Une sortie au-delà du stock n'est valorisée que jusqu'au stock : le
     CMUP ne connaît pas de stock négatif.)
8. si `q > 1e-9` : `dernier_moyen[ref] = v / q`.
9. `unitaire[id] = cout` (si `id` non vide).
10. si type ∈ {`SORTIE_PROD`, `RETOUR_PRODUCTION`} : `consommation.append((date, avant − v))`.

À la fin : `stock = dict(etat)`.

**Ce qui ne passe pas par ici** : la période close (`securite.date_permise`, `cout_hors_periode_close`,
`securite.py:210-276`) n'est pas un calcul mais un **refus d'écrire** : rien ne se date dans la
période close, et tout geste qui changerait le coût d'une marchandise entrée dans la période
close (frais, cours, rattachement, réouverture de dossier, clé de poste) est refusé (409). Le
CMUP est donc recalculé à chaque fois depuis le journal, mais ses entrées ne peuvent plus
bouger (`f6f3acc`, `f216509`).

**Exemples chiffrés (essais `tests/test_valorisation.py`).**

*Annulation d'une réception* — 125,7 kg à 26,89 ; 1 000 kg reçus à 200 puis annulés le même jour :

| # | Écriture | q | v | CMUP |
|---|---|---|---|---|
| 1 | ouverture 125,7 × 26,89 | 125,7 | 3 380,07 | 26,89 |
| 2 | réception 1 000 × 200 | 1 125,7 | 203 380,07 | 180,67 |
| 3 | annulation de 2 (coût de l'original 200) | 125,7 | 3 380,07 | **26,89** |

Un CMUP classique (sortie au moyen 180,67) laisserait 125,7 × 180,67 = 22 710.

*Annulation du jour rejouée après son original* — J1 : lot J1 100 kg à 10 (id 1). J2 : lot J2
100 kg à 30 (id 2), sortie 50 kg (id 3), annulation de l'id 2 (id 4, datée J2). Ordre :
1, 2, **4**, 3 → la sortie part à 10, le stock vaut 50 kg / 500 MAD.

*Ré-entrée sur stock vide* — 100 kg à 10 (catalogue 30), sortie de 100 (OF-1), retour de
20 (OF-1) → rentre à 10 (coût de la sortie), stock 20 kg / 200, consommation totale
1 000 − 200 = 800. Un lot inconnu après épuisement de A (100×10) et B (100×20) rentre au
dernier moyen 15. Rien de connu → catalogue.

*Retour au fournisseur* — lot A 100 à 10, lot B 100 à 50, retour de 100 du lot B → sort à 50
(et non au moyen 30) ; CMUP restant 10.

*Cours figé* — 100 kg à 2 USD, cours figé 10, cours du jour 12 → CMUP 20 ; sans cours figé
(écriture reprise) → 24.

### 1.4 `cmup_glissant(donnees)` (`moteur.py:1973-1975`)

`couts_du_journal(donnees).cmup()`.

### 1.5 `cmup_par_reference(donnees, glissant=None) → {ref: MAD}` (`moteur.py:1978-2006`)

Le coût unitaire de **chaque** référence du catalogue, tel que la Valorisation le retient :

1. `glissant` par défaut : `{}` [classeur] sinon `cmup_glissant(donnees)`.
2. Moyenne des prix payés, par référence, sur `donnees.historique_prix` (lignes de
   réception validées non refusées, pesée > 0, prix > 0 — `depot.py:419-436`) :
   `Q = Σ quantite`, `M = Σ quantite × prix_achat × taux(prix.devise)` (**cours du jour**,
   chaque prix dans **sa** devise) ; [classeur] `M = Σ quantite × prix_achat × taux(article.devise)`
   (« le classeur additionne les prix tels quels, puis convertit au taux du catalogue »).
3. Pour chaque article : si `ref ∈ glissant` → `glissant[ref]` (même 0) ; sinon `M / Q` si
   `Q ≠ 0` ; sinon `article.prix_kg × taux(article.devise)`.

Exemple : sans stock, achats 100 kg à 2 EUR (EUR = 11) et 100 kg à 20 MAD → (2 200 + 2 000) / 200 = **21**
(et non (200 + 2 000)/200 × 11 = 121).

### 1.6 `valorisation(donnees, lignes_stock) → [LigneValorisation]` (`moteur.py:2009-2047`)

Pour chaque article du catalogue (ordre du catalogue) : `magasin = stock_net`, `machine =
stock_machine` (0 si la référence n'a pas de ligne de stock), `cmup = cmup_par_reference[ref]`,
champs du § 1.1. **Décision de Mohamed (8 oct. 2026, `169dfdc`)** : le stock de l'usine est en
magasin (quarantaine comprise) ou en machine ; les deux sont valorisés et additionnés. Le
vérificateur ne confronte au journal que la part des magasins (le montage n'a pas d'écriture).
Les stocks négatifs ne sont pas écartés (valeur négative possible).

**Route `GET /valorisation?date_reference=`** (`api/pilotage.py:256-277`, droit ACHATS) :
`charger_au(jour)` → `etat_stock` → `valorisation`. Totaux : `total_mad = Σ valeur_mad`,
`total_magasin_mad`, `total_machine_mad`, `total_kg = Σ stock`, `total_kg_magasin`,
`total_kg_machine`, `ecart_mad = Σ ecart_mad` ; chaque ligne reçoit `kg_par_ml` (densité d'un
rôle au mètre, 0 sinon). À une date passée, `stock_machine = 0` (montage sans historique).

**Route `GET /stock`** (`api/pilotage.py:44-67`) : ajoute à chaque ligne
`valeur_machine_mad = stock_machine × cmup_par_reference[ref]` (0 si absent ; calculé
seulement s'il y a du fil monté). Rôle « alimentation » : `prix_kg, prix_unite,
montant_a_commander, montant_a_commander_mad, valeur_conso_annuelle,
valeur_conso_annuelle_mad, valeur_machine_mad` → `None`, `devise` et `action` → `""`.

---

## 2. Prix payés, opportunités d'économies

### 2.1 `Opportunite` (`moteur.py:2053-2080`)

`reference, nature, titrage, fournisseur_actuel, prix_actuel_mad, prix_minimum_mad,
fournisseur_alternatif, conso_annuelle, economie_mad`, puis (Gestion MP) `composition,
type_fil, couleur, reference_alternative, couleur_alternative, origine_prix` (« payé » |
« catalogue », défaut « catalogue »), `origine_prix_minimum`, `ecart = (actuel − minimum)/actuel`,
`date_prix`, `date_prix_minimum`, `ecart_jours`, `base_prix` / `base_prix_minimum`
(« coût rendu » | « prix facture » | « catalogue », défaut « prix facture »).

### 2.2 `prix_constates(donnees) → {ref: (prix MAD, origine, date)}` (`moteur.py:2083-2105`)

Catalogue `prix_kg × taux(devise)` (« catalogue », None), écrasé par chaque achat
`prix_achat > 0` trié par `(date_bc or date.min, numero_bc)` : le dernier gagne,
`prix_achat × taux(achat.devise)`, « payé », `date_bc`. **Code mort** : appelé nulle part.

### 2.3 `_opportunites_du_classeur(donnees, lignes_stock)` [classeur] (`moteur.py:2108-2146`)

`_Opp_Calc` du classeur. `conso[ref] = conso_mensuelle × 12`. `prix[ref] = prix_kg ×
taux(article.devise)`. Minimum par clé `(nature, titrage)` sur **tout** le catalogue (actif ou
non) : premier article au prix strictement plus bas gagne. Pour chaque article :
`economie = (prix − prix_min) × conso` si `prix > prix_min` et `conso > 0`, sinon 0 ; gardé si
`economie > 0`. Tri par économie décroissante.

### 2.4 `CoutDate` et `achats_dates(donnees, couts=None)` (`moteur.py:2149-2178`)

`CoutDate = (date, prix MAD/kg, base)`.
- Avec `couts` (coût rendu usine, exigence M84) : `{ref: sorted((jour, prix) pour prix > 0)}`
  pour les références ayant au moins un prix > 0. Tri sur le **tuple** (date, prix) : à date
  égale, le prix le plus élevé est le dernier.
- Sans `couts` : pour chaque `historique_prix` avec `prix_achat > 0` et `date_bc` non vide :
  `(date_bc, prix_achat × taux(devise))` (cours du jour), trié.
  (`LignePrix.date_bc` est en réalité **la date de la réception**, `depot.py:426`.)

### 2.5 `couts_rendus(session, donnees)` — route (`api/pilotage.py:207-239`)

Le coût rendu usine de chaque achat, MAD/kg :
lignes de réception **validées**, qualité ≠ refusé, `quantite_pesee > 0`, `prix > 0` ; pour
chacune, `revient = revient_par_reception(donnees).get(id)` :
- `revient.revient_unite > 0` → `(date réception, revient_unite, "coût rendu")` ;
- sinon si le bon a un cours figé **et** `devise de la ligne == devise du bon` →
  `prix × cours du bon`, « prix facture » ;
- sinon `prix × taux(devise)` (cours du jour), « prix facture ».

(Le cours figé **du mouvement** n'est pas utilisé ici, voir § 12.)

### 2.6 `comparer_les_prix(donnees, lignes_stock, *, meme_couleur=False, autre_fournisseur=True, prix_catalogue=False, fenetre_jours=None, couts=None) → (opportunités, écartées)` (`moteur.py:2181-2337`)

Le classeur comparait sur nature + titrage au prix du catalogue ; ici on compare ce qui se
compare, à la même époque.

1. `fenetre = fenetre_jours` sinon `parametres.fenetre_prix_jours` (défaut 90).
2. `conso[ref] = conso_mensuelle × 12` ; `achats = achats_dates(donnees, couts)`.
3. `bases[(ref, jour)]` : base de chaque prix daté ; « coût rendu » l'emporte sur « prix
   facture » le même jour.
4. `catalogue[ref] = prix_kg × taux(article.devise)`.
5. **Famille** : `(composition or nature, type_fil, str(titrage), titrage_unite)`, chacun
   `strip().lower()` ; avec `meme_couleur`, `+ (couleur or designation)`.
6. **Rivaux possibles** : articles **actifs** ayant des achats ou un catalogue > 0, rangés par
   famille.
7. `offre(rival, jour)` :
   - rival avec achats et `jour` (date du dernier prix de l'article) non vide : `proche =
     min(serie, clé = (|Δ jours|, −date))` (à égalité, le plus récent) ; si `|Δ| ≤ fenetre` →
     `(prix proche, "payé", date, "")` ; sinon → `(dernier prix, "payé", dernière date,
     "hors_fenetre")` ;
   - rival avec achats mais `jour` vide : `(dernier prix, "payé", dernière date, "" si
     prix_catalogue sinon "sans_date")` ;
   - rival sans achat, catalogue > 0 : `(catalogue, "catalogue", None, "" si prix_catalogue
     sinon "sans_date")` ;
   - sinon `None`.
8. Pour chaque article du catalogue (actif ou non) avec `conso > 0` :
   - prix actuel : dernier achat `(jour, actuel) = serie[-1]`, origine « payé » ; sans achat :
     `catalogue`, origine « catalogue », `jour = None`, et `propre_sans_date = not prix_catalogue` ;
   - ignoré si `actuel ≤ 0` ;
   - pour chaque rival de la même famille, ≠ lui-même, et (si `autre_fournisseur`) d'un autre
     fournisseur : `proposition = offre(rival, jour)` ; ignorée si `None` ou `prix ≥ actuel` ;
     motif forcé à « sans_date » si `propre_sans_date` ; une proposition avec motif est
     **écartée** (motif noté) ; sinon on retient le prix le plus bas ;
   - rien de retenu : si un motif « sans_date » a été noté → `ecartees.sans_date += 1`, sinon
     si un motif quelconque → `ecartees.hors_fenetre += 1` ;
   - retenu : `economie_mad = (actuel − minimum) × conso`, `ecart = (actuel − minimum)/actuel`,
     `ecart_jours = |jour − jour_minimum|` si les deux dates existent, bases via `base_de`
     (« catalogue » si origine catalogue ou date vide, sinon `bases.get((ref, jour), "prix facture")`).
9. Tri par économie décroissante. Rend `(liste, {"sans_date": n, "hors_fenetre": n})`.

Subtilité : un rival « hors fenêtre » n'est compté que si **son dernier prix** est inférieur au
prix actuel (le test `prix ≥ actuel` porte sur le prix rendu par `offre`).

### 2.7 `opportunites(donnees, lignes_stock, *, meme_couleur=False, autre_fournisseur=True, prix_catalogue=False, couts=None)` (`moteur.py:2340-2359`)

[classeur] → `_opportunites_du_classeur` ; sinon `comparer_les_prix(...)[0]` (fenêtre des
réglages).

**Route `GET /opportunites`** (`api/pilotage.py:280-346`) : paramètres `meme_couleur`
(**défaut vrai** à l'écran, faux dans le moteur), `autre_fournisseur` (vrai), `prix_catalogue`
(faux), `fenetre_jours` (1…3650, défaut réglage). Données à la date (`charger_au`). En
corrigée : `comparer_les_prix(..., couts=couts_rendus(...))`. Rend `avertissement` (texte
composé selon les critères), `criteres`, `fenetre_jours`, `seuils = {stable: 0,005, forte:
seuil_hausse_forte}`, `ecartees`, `total_mad = Σ economie_mad`, lignes avec dates ISO.

### 2.8 `LigneHistoriquePrix` et `historique_prix(donnees)` (`moteur.py:2950-3009`)

Tri des `historique_prix` par `(date_bc or date.min, reference, numero_bc)`. « Précédent » à
**fournisseur et devise constants** : clé `(ref, fournisseur, devise)` (règle du classeur
`Tbl_HistoriquePrix[Prix précédent]`). Pour chaque prix : `prix_mad = prix_achat ×
taux(devise)` (cours du jour), `montant_mad = quantite × prix_achat × taux`, `prix_precedent`
(dans la devise), `evolution = (prix − précédent)/précédent` si précédent non nul sinon None,
`origine = ""` (le champ n'existe pas sur `LignePrix` : toujours vide). Liste **inversée**
(le plus récent d'abord).

**Route `GET /prix/historique`** (`api/pilotage.py:380-401`) : `total_achats_mad = Σ
montant_mad` ; `hausses` = nb `evolution > 0,005` ; `fortes_hausses` = nb `evolution >
seuil_hausse_forte` (défaut 0,05) ; `baisses` = nb `evolution < −0,005` ; `seuils`.

### 2.9 Matrice des prix — route `GET /prix/matrice` (`api/pilotage.py:444-494`)

Pour chaque prix daté : mois `AAAA-MM` de `date_bc` ; par (référence, mois) la liste
`(quantite, prix_achat)`. Mois retenus : les **36 derniers mois vus** (toutes références
confondues). Valeur d'une case : `Σ q × p / Σ q` (prix moyen pondéré, **dans la devise
d'achat, non converti**) ; si `Σ q = 0` : moyenne simple ; case vide → `None`. Champs
descriptifs : nature, désignation, titrage, unité, composition (ou nature), type, couleur (ou
désignation), fournisseur, devise du catalogue. `seuils` comme ci-dessus.

---

## 3. Cockpit

### 3.1 `cout_matiere_annuel(donnees, date_ref)` (`moteur.py:2365-2371`)

`Cockpit!J54` : `Σ_q coût_m²(q) × Σ_{12 mois} m²_plan(q, mois)` où
`coût_m²(q) = Σ_{lignes de nomenclature de q} cout_m2_mad` (partie A :
`kg_m2 × prix_kg × taux(devise_article) × (1 + taux_perte)` en corrigée, sans perte
[classeur]) et `plan = plan_mensuel(donnees, date_ref)` (qualités arrêtées à 0).

### 3.2 `cockpit(donnees, date_ref, lignes_stock, couts=None, meme_couleur=False) → dict` (`moteur.py:2374-2601`)

Définitions locales :
- `detenu(x) = stock_disponible + stock_quarantaine` = `stock_net + stock_machine`
  (car `stock_disponible = stock_net − quarantaine + machine`, partie A) ;
- `physique = [x ∈ lignes_stock | detenu(x) > 0]` ;
- `journal = None` [classeur] sinon `couts_du_journal(donnees)` ;
- `cout = {}` [classeur] sinon `cmup_par_reference(donnees, journal.cmup())` ;
- `catalogue(x) = x.prix_kg × taux(x.devise)` (`x.devise` = `devise_article`, partie A) ;
- `unitaire(x) = cout.get(ref) or catalogue(x)` (**un CMUP de 0 retombe sur le catalogue**,
  voir § 12).

Chaque indicateur :

| Clé | Formule |
|---|---|
| `date_reference` | `date_ref` ISO |
| `stock.valeur_mad` | `Σ_{x∈physique} detenu(x) × unitaire(x)` (magasins + quarantaine + machine, au CMUP) |
| `stock.valeur_machine_mad` | `Σ_{stock_machine>0} stock_machine × unitaire(x)` (information, déjà incluse ci-dessus) |
| `stock.nb_references` | `len(lignes_stock)` (tout le catalogue) |
| `stock.nb_detenues` | `len(physique)` |
| `stock.nb_sur_metiers` | nb de lignes `stock_machine > 0` |
| `stock.couverture_ponderee_jours` | `stock_valorise / (conso_valorisee / 30)` si `conso_valorisee ≠ 0` sinon 0, avec `conso_valorisee = Σ conso_mensuelle × prix_kg × taux(devise)` (toutes lignes) et `stock_valorise = Σ_{stock_projete>0} stock_projete × prix_kg × taux(devise)` — **au catalogue** |
| `stock.ruptures` / `critiques` / `urgents` / `attentions` / `ok` / `sans_consommation` | nb de lignes par `statut` (`STATUTS`) |
| `achats.bc_actifs` | [classeur] `len(commandes)` ; sinon nb de bons (non brouillon, non annulés) ayant au moins une ligne avec `reste_a_livrer > 0` |
| `achats.montant_bc_en_cours_mad` | [classeur] `total_bc` ; sinon `Σ_{bons, lignes} montant_ligne_mad(ligne, reste_a_livrer)` |
| `achats.montant_bc_estime_mad` | part du précédent sur les lignes `prix_confirme = faux` (0 en classeur) |
| `achats.fournisseurs_actifs` | `len(donnees.fournisseurs)` (**tous**, actifs ou non) |
| `achats.budget_a_commander_mad` | `Σ_{quantite_a_commander>0} montant_a_commander_mad` |
| `finance.cout_matiere_annuel_mad` | `cout_matiere_annuel(donnees, date_ref)` |
| `finance.cout_matiere_mensuel_mad` | `cout_annuel / 12` |
| `finance.rotation_stock` | `cout_rotation / valeur_rotation` (0 si `valeur_rotation = 0`) |
| `finance.dio_jours` | `valeur_rotation / (cout_rotation / 365)` (0 si `cout_rotation = 0`) |
| `finance.cout_rotation_annuel_mad` | `cout_rotation` |
| `finance.base_rotation` | « consommation » ou « plan » |
| `finance.dso_jours` | `parametres.dso` (réglage, défaut 60) |
| `finance.dpo_jours` | voir DPO |
| `finance.ccc_jours` | `dio + dso − dpo` |
| `abc.A` / `B` / `C` | nb de lignes par `classe_abc` |
| `dormant.nb_references` | nb de lignes `dormant` |
| `dormant.valeur_mad` | [classeur] `Σ_{dormantes} stock_projete × catalogue(x)` ; sinon `Σ_{dormantes, detenu>0} detenu × unitaire` |
| `dormant.part_valeur` | `valeur_dormante / stock.valeur_mad` (0 si nul) |
| `dormant.seuil_jours` | `seuil_dormant` |
| `sourcing.mono_source` | nb `sourcing == "🔴 MONO-SOURCE"` |
| `sourcing.multi_source` | nb `sourcing` commençant par « ✅ » |
| `economies.total_mad` | `Σ economie_mad` de `opportunites(donnees, lignes, meme_couleur, couts=couts)` |
| `economies.nb_opportunites` | leur nombre |
| `economies.top` | les 5 premières (dictionnaires) |
| `nb_alertes` | nb de lignes au statut ∈ `STATUTS_EN_ALERTE` (rupture, critique, urgent, attention) |
| `alertes` | les 24 premières, triées par `couverture_jours` croissante (`None` → 0, donc en tête) ; champs : reference, nature, designation, fournisseur, `stock = stock_projete`, conso_mensuelle, couverture_jours, delai_jours, quantite_a_commander, statut, statut_couverture, action, `titrage = "titrage unité"`, kg_par_ml, stock_machine |
| `devises` | `_concentration_devises` |

**Rotation / DIO** (`moteur.py:2409-2433`, `5ca0960`) :
- [classeur] : base « plan », `valeur_rotation = valeur_stock`, `cout_rotation = cout_annuel`.
- corrigée : `fin_conso = 1er du mois de date_ref − 1 jour` ; `debut_conso = 1er du mois
  12 mois plus tôt` ; `consomme = Σ journal.consommation` sur `[debut_conso ; fin_conso]` ;
  `premiere = min(date des mouvements)` ;
  - si `consomme > 0` et `premiere ≤ fin_conso` : base « consommation »,
    `jours = (fin_conso − max(debut_conso, premiere)).days + 1`,
    `cout_rotation = consomme / jours × 365` (annualisé si moins d'un an d'historique),
    `valeur_rotation = valeur_stock` (CMUP) ;
  - sinon base « plan » : `valeur_rotation = Σ_{physique} detenu × catalogue`,
    `cout_rotation = cout_annuel` (les deux au catalogue).
  Raison : le classeur divisait un stock au coût réel par un coût annuel au catalogue (un
  dossier à +15 % de frais ajoutait 15 % de jours de stock).

Exemple : date 5 juin 2026 ; stock détenu 1 000 kg à CMUP 20 + 500 kg à 8 → 24 000 MAD ;
sorties de 100 kg/mois à 20 sur juin 2025–mai 2026 (365 jours) → `cout_rotation = 24 000 /
365 × 365 = 24 000` → rotation 1, DIO 365 j ; avec DSO 60 et DPO 90 → CCC 335 j.

**DPO** (`moteur.py:2455-2506`) :
- `commandes` = toutes sauf brouillons (`pas_partie` : statut « Brouillon » hors classeur ;
  « À approuver » non parti est aussi « Brouillon » côté moteur, `depot.STATUTS_MOTEUR`) ;
  en corrigée on retire aussi les « Annulée ».
- `montants[fournisseur] += Σ_lignes` : [classeur] `quantite_commandee × prix_unite ×
  taux(ligne.devise)` ; sinon `montant_ligne_mad(ligne, quantite_commandee)`. Tout l'historique
  des bons, sans fenêtre de dates.
- `total_bc = Σ montants` ; si `total_bc ≠ 0` : `DPO = Σ delai_paiement_jours(f) × montant(f) /
  total_bc` (fournisseur inconnu : 0 jour) ; sinon moyenne simple des `delai_paiement_jours > 0`
  des fournisseurs (0 si aucun).

**Route `GET /cockpit`** (`api/pilotage.py:242-253`, ACHATS) : `charger_au(jour)`,
`cockpit(..., couts_rendus(...), meme_couleur=True)` + `controles` (synthèse des contrôles,
hors périmètre). Le courriel et la photo du jour appellent `cockpit` **sans** `couts` et avec
`meme_couleur = False` (le bloc `economies` n'y est pas lu).

### 3.3 `_concentration_devises(donnees, lignes_stock)` (`moteur.py:2604-2623`)

Zone 6 du Cockpit, exposition au change du budget à émettre : pour chaque ligne
`quantite_a_commander > 0`, par `ligne.devise` : `references += 1`, `montant_mad +=
montant_a_commander_mad` ; `part = montant / total`. Tri par montant décroissant.

---

## 4. Fournisseurs : OTIF et score

### 4.1 Structures (`moteur.py:2629-2660`)

`PerformanceReception` : `numero, fournisseur, date_reception, on_time (0/1/None), in_full
(0/1/None — None : la réception ne devait rien), in_spec (0/1), otif (0/1/None),
lignes_hors_tolerance, ecart_pesee (moyenne ou None)`.

`ScoreFournisseur` : `fournisseur, pays, devise, delai_jours, nb_commandes, montant_mad,
receptions, on_time, in_full, in_spec, otif (moyennes ou None), taux_retours,
ecart_pesee_moyen, score, classement, action, sous_performant`.

### 4.2 `montant_ligne_mad(ligne, quantite, parametres)` (`moteur.py:2663-2668`)

`prix = prix_unite si prix_confirme sinon (prix_estime or prix_unite)` ;
`montant = quantite × prix × (ligne.cours or taux(ligne.devise))`.
`prix_estime` (`api/achats.py:163-166`) = prix confirmé, sinon prix catalogue au kilo converti
dans la devise du bon au cours du jour (`prix_catalogue_en`) — « un bon part sans prix ».
`ligne.devise` = devise du bon, `ligne.cours` = cours figé du bon. Même chiffre que l'écran
Commandes.

### 4.3 `performance_receptions(donnees)` (`moteur.py:2671-2804`)

Réceptions traitées **dans l'ordre de `donnees.receptions`** (base : par date puis id, les
annulées exclues au chargement, `depot.py:384-385`) ; seules les `Validée` sont jugées (un
brouillon ne compte pas et n'alimente pas `deja`).

**Bons du camion** : `{reception.numero_bc}` si la réception porte un seul bon (le dépôt ne
remplit `numero_bc` que si toutes ses lignes sont du même bon), sinon l'ensemble des
`numero_bc` de ses lignes (camion de plusieurs bons, `6143421`).

**À l'heure (On-Time)** — pour chaque bon (ordre trié) connu, avec `date_bc`,
`date_livraison_prevue` (date **promise**, jamais l'ETA) et date de réception :
`réel = (date_réception − date_bc).days`, `prévu = (date_promise − date_bc).days`,
jugement `1 si réel ≤ prévu + toler_retard_jours sinon 0`. `on_time = min(jugements)` (le
camion n'est à l'heure que si **chacun** de ses bons l'est), `None` si aucun bon jugeable.

**Complète (In-Full)** :
- [classeur] : `commandé = Σ quantite_commandee` des lignes du camion (dans Gestion MP :
  `quantite_attendue` de la ligne), `pesé = Σ quantite_pesee` ; `in_full = 1` si `commandé ≠ 0`
  et `pesé ≥ commandé × (1 − toler_in_full)`, sinon 0 (une réception hors commande compte
  incomplète).
- corrigée (`9ed7831`, `1b0a62f`) :
  1. `livre[(bc, ref)] = Σ quantite_pesee` des lignes du camion **non refusées**
     (`bc = ligne.numero_bc or reception.numero_bc`, ignorée sans bon).
  2. Pour chaque bon du camion : ignoré s'il est inconnu, ou **soldé à la main avant ce
     camion** (`commande.solde_a_la_main_le` et `reception.validee_le > solde_a_la_main_le`).
     Un bon **annulé** que le camion sert reste jugé.
  3. Pour **chaque ligne du bon** (même absente du camion) : `cle = (bc, ref)`,
     `marge = commandée × toler_in_full`,
     `reste = commandée − (deja[cle] − reparti_avant(cle, date_réception))` ;
     si `reste > marge`, la ligne est **due**, et complète si `livre[cle] ≥ reste − marge`.
  4. `in_full = 1` si toutes les lignes dues sont complètes, 0 sinon, **`None` s'il n'y a
     aucune ligne due** (hors commande, bon déjà livré, bon soldé avant) : la réception n'est
     pas jugée.
  5. Puis `deja[cle] += livre[cle]` ; et pour chaque ligne non refusée avec lot :
     `lots_de_ligne[(bc,ref)][lot] += pesée`, `apporte_du_lot[(ref,lot)] += pesée`.
- `reparti_avant(cle, jour)` : ce que la ligne de bon a reçu et qui est reparti chez le
  fournisseur **avant ou le jour même** du camion (« on renvoie, puis le remplacement
  arrive ») : `Σ_{lot de la ligne} min(kg_ligne_lot, renvoyé_lot × kg_ligne_lot /
  apporté_lot)` où `renvoyé_lot = Σ quantite des RETOUR_FOURNISSEUR de (ref, lot) datés ≤ jour`
  (annulations de retour comprises, négatives) ; lots sans apport ignorés.

**Conforme (In-Spec)** : `1` si la réception a des lignes et que **toutes** ont un
`statut_qualite` se terminant par « Conforme » (« Réserve » et « Refusé » → 0).

**OTIF** : `None` si `in_full` est `None` ; sinon `(1 si on_time est None sinon on_time) ×
in_full × in_spec` (une réception sans date promise est réputée à l'heure).

**Pesée** : `ecarts = [ecart_relatif des lignes, non None]` (toutes lignes, refusées
comprises ; règle de `quantite_attendue`, partie A : BL, sinon commandé si la pesée atteint
le reste à la tolérance près, sinon pas d'écart) ;
`lignes_hors_tolerance = nb |e| > toler_ecart_pesee` ; `ecart_pesee = moyenne(ecarts)` ou None.

### 4.4 Score : constantes et `points_score` (`moteur.py:2807-2826`)

`POINTS_OTIF = 60`, `POINTS_RETOURS = 20`, `POINTS_DELAI = 20`, `RETOURS_SANS_POINT = 0,05`.

```
points_retours = 20 × max(0, 1 − taux_retours / 0,05)
points_delai   = min(20, max(0, 20 − (délai − 15) / 5))
score          = otif × 60 + points_retours + points_delai
```

L'ancienne formule (OTIF × 40 + (1 − retours) × 40 + délai) donnait 40 points d'office pour
0 à 1,4 % de retours et plus de 20 points à un délai court : un fournisseur à 18 % d'OTIF
restait « Standard ».

Exemples (essais) : `points_score(0,18 ; 0 ; 4) = 10,8 + 20 + 20 = 50,8` (< 65, plus
« Standard ») ; `(1 ; 0 ; 4) = 100` (délai plafonné à 20) ; `(1 ; 0,014 ; 15) = 60 + 20 × (1 −
0,28) + 20 = 94,4` ; `(1 ; 0,2 ; 200) = 60` ; délai 45 j → 20 − 6 = 14 points.

### 4.5 `scorecard_fournisseurs(donnees)` (`moteur.py:2829-2931`)

1. `performances = performance_receptions(donnees)`, regroupées par fournisseur.
2. Sur **tout le journal** : `entrees[f] = Σ quantite` des `ENTREE_RECEPTION`,
   `retours[f] = Σ quantite` des `RETOUR_FOURNISSEUR` (f = fournisseur du lot ; annulations
   comprises, négatives ; les ouvertures ne comptent pas).
3. Bons retenus : non brouillons, et (corrigée) non « Annulée ».
4. Pour chaque fournisseur (tri par nom) :
   - `moyenne(champ)` : corrigée → sur les réceptions **notées** (`otif ≠ None`), valeurs non
     None, divisé par leur nombre ; [classeur] → sur toutes les réceptions, valeurs non None,
     divisé par **le nombre total de réceptions** ; None s'il n'y a aucune valeur ;
   - `otif = moyenne("otif")` ; `taux_retours = retours / entrees` (0 si rien reçu) ;
   - `score` : None si `otif` None ; [classeur] `arrondi(otif × 40 + (1 − taux_retours) × 40 +
     max(0 ; 20 − (délai − 15)/5))` (sans plafond à 20) ; corrigée
     `arrondi(points_score(otif, taux_retours, delai_jours))` — `arrondi` à l'entier, demi
     au-dessus ;
   - classement : `None` → « — » ; `≥ score_strategique` (85) « 🟢 Stratégique » / « Fidéliser
     + négocier volume » ; `≥ score_standard` (65) « 🟡 Standard » / « Maintenir relation » ;
     `≥ score_surveiller` (45) « 🟠 À surveiller » / « Audit qualité + relance » ; sinon « 🔴 À
     challenger » / « Chercher alternative » ;
   - `montant_mad` : [classeur] `Σ_bons (Σ_lignes q × prix_unite) × taux(devise de la 1re
     ligne, à défaut du fournisseur)` ; sinon `Σ montant_ligne_mad(ligne, commandée)` ;
   - `nb_commandes` = nb de bons retenus ; `receptions` = nb de réceptions jugées (notées ou
     non) ; `on_time`, `in_full`, `in_spec` par `moyenne` ;
   - `ecart_pesee_moyen` = moyenne des `ecart_pesee` non None de **toutes** ses réceptions ;
   - `sous_performant = otif ≠ None et otif < cible_otif` (0,95).

Exemple : 10 réceptions notées dont 8 parfaites → OTIF 0,8 ; 30 000 kg reçus, 450 renvoyés →
1,5 % → 20 × (1 − 0,3) = 14 ; délai 30 j → 20 − 3 = 17 ; score = 48 + 14 + 17 = 79 → « Standard ».

**Route `GET /fournisseurs/performance`** (`api/pilotage.py:497-521`) : `cible_otif`, `seuils`,
`lignes` (scorecard), `receptions` (performances, dates ISO).

### 4.6 `devises_pratiquees(donnees)` (`moteur.py:2934-2944`)

`{fournisseur: {devise: nb d'articles}}` sur le catalogue (articles avec fournisseur et
devise, actifs ou non). La devise appartient au prix, pas au fournisseur (sert au contrôle
C19 et à la liste des fournisseurs).

---

## 5. Réceptions : pesées et bobines

### 5.1 `Pesee`, `ecart_bobine`, `pesees` (`moteur.py:3012-3100`)

`ecart_bobine(constaté, catalogue) = (constaté − catalogue)/catalogue`, `None` si l'un est
nul ou vide.

`pesees(donnees)` : une ligne par ligne de réception, **toutes réceptions chargées**
(validées et brouillons ; annulées exclues au chargement), lignes refusées comprises.
Champs : n°, date, `numero_bc = ligne.numero_bc or reception.numero_bc`, fournisseur,
réceptionnaire (qui a saisi), contrôleur (qui a validé), référence, nature, désignation, lot,
`quantite_commandee` (= quantité attendue de la ligne en base), `quantite_bl`,
`quantite_attendue`, `quantite_pesee`, `ecart`, `ecart_relatif` (propriétés, partie A),
`hors_tolerance = ecart_relatif ≠ None et |ecart_relatif| > toler_ecart_pesee`, `nb_bobines`,
`poids_moyen_bobine = pesée / nb_bobines` (None sans bobines), magasin, statut qualité,
observations, statut de la réception, `nb_palettes`, `poids_bobine_catalogue`,
`ecart_bobine`, `bobine_hors_tolerance = |ecart_bobine| > toler_poids_bobine`. Tri par
`(date, numéro)` décroissant.

**Route `GET /receptions/pesees`** (`api/pilotage.py:404-423`) : `tolerance`,
`tolerance_bobine`, lignes, `hors_tolerance` = nb, `non_conformes` = nb `statut_qualite ≠ "Conforme"`.

### 5.2 `evolution_bobines(donnees)` (`moteur.py:3103-3165`)

Mesures : lignes des réceptions **validées**, `poids_moyen_bobine` non nul, statut ≠
« Refusé ». Par référence, triées par `(date, n° de réception)` :
`premier`, `dernier` (poids de la première et de la dernière mesure), `derniere_date`,
`receptions` = nb de mesures, `moyenne = Σ pesée / Σ bobines` (moyenne **des bobines**, pas
des réceptions ; 0 si aucune bobine), `mini`, `maxi`, `evolution = (dernier − premier)/premier`
(0 si premier nul), `ecart_catalogue = ecart_bobine(dernier, poids_bobine du catalogue)`,
`hors_tolerance = |ecart_catalogue| > toler_poids_bobine`, `historique` (les mesures),
`fournisseur` du catalogue (sinon celui de la dernière mesure). Tri par `|evolution|`
décroissante. Route `GET /receptions/bobines` : `hors_tolerance` = nb.

---

## 6. Lots et traçabilité

> **Règle nouvelle de PRO (lot FOND-DE-LOT, décision de Mohamed du 15/10/2026, DECISIONS U22, O14) —
> absente de Gestion MP.** Un *fond de lot* est un solde (lot, magasin) `0 < q < seuil_rebut`
> (réglage, 0,100 kg par défaut ; 0 = jamais). Il ne change **aucun chiffre** du moteur (stock,
> valeur, disponible, projeté, bilan : le fond reste compté et valorisé) ; il change **la
> proposition FIFO** de `POST /ordres/proposition` (`services/ordres/proposition._servir`) : le lot
> est sauté dans `lots` (le lot suivant est servi), gardé dans `disponibles` avec `fond_de_lot:
> true`, nommé dans `fonds_de_lot`. Le rebut (`POST /lots/{id}/rebut`) est un **ajustement
> ordinaire** en moins (motif « Rebut »), valorisé au coût moyen comme tout ajustement (§ B.1) ;
> le bilan le compte dans « ajustements ». La parité avec Gestion MP ne compare pas la proposition ;
> sur les données de l'année d'essai aucun chiffre comparé ne change.

### 6.1 `LigneLot` (`moteur.py:3176-3199`)

`reference, lot, entrees, sorties, stock, premiere_entree, dernier_mouvement, fournisseur,
par_magasin {code: kg}, ordres [OF servis, ordre d'apparition], mouvements (nb)` ;
`epuise = |stock| < 1e-9` ; `negatif = stock < −1e-9`.

### 6.2 `stock_par_lot(donnees, reference="")` (`moteur.py:3202-3271`)

Pour chaque mouvement (filtré par référence si donnée), clé `(ref, lot or "(sans lot)")` —
un mouvement sans lot n'est pas ignoré : la somme des lots retombe toujours sur le stock.
`fournisseur` = celui du premier mouvement du lot, sinon celui du catalogue.
`annulees` = ensemble des `contrepasse_id`.

- `stock += quantite_signee` (toujours, brut) ; `mouvements += 1` ;
- entrées / sorties :
  - corrigée : une annulation **ou** une écriture annulée → ni entrée ni sortie ; un
    transfert → rien ; un `RETOUR_PRODUCTION` → `sorties −= signee` (réduit le sorti) ;
  - sinon `signee > 0` → `entrees += signee` et `premiere_entree = min` ; `signee < 0` →
    `sorties += −signee` ;
  - [classeur] : tout compte brut (signe seul).
  Donc en corrigée `entrees − sorties = stock`.
- `dernier_mouvement = max(date)` (tous mouvements) ;
- `par_magasin` : transfert → `destination += quantite`, `source −= quantite` ; sinon si
  destination → `+= signee`, sinon si source → `+= signee` ;
- `ordres` : n° d'OF ajoutés une fois.
Tri par `(référence, lot)`.

**Route `GET /lots`** (`api/pilotage.py:527-565`) : `lot_id` → la référence du lot puis filtre
sur son numéro (un n° de lot peut servir à deux matières) ; `seulement_en_stock` → `stock >
1e-9` ; `sans_lot = Σ stock du lot « (sans lot) »`, `total = Σ stock`.

### 6.3 `lots_disponibles(donnees, reference)` (`moteur.py:3274-3292`)

Pour la saisie d'une sortie : lots de la référence, hors « (sans lot) » ; `par_magasin`
réduit aux magasins **non quarantaine** avec `q > 1e-9` ; `stock = Σ` ; gardé si `> 1e-3`
(POUSSIERE) ; tri **FIFO** par `(premiere_entree or date.max, lot)`.

### 6.4 `tracabilite(donnees, *, lot="", ordre="", reference="")` (`moteur.py:3295-3323`)

Mouvements où `(lot_fournisseur or "(sans lot)") == lot` **ou** `numero_of == ordre` **ou**
`reference == reference`. Rend `mouvements`, `references`, `ordres`, `lots` (triés, non vides),
`entrees = Σ quantite_signee > 0`, `sorties = −Σ quantite_signee < 0` (brut).

**Route `GET /tracabilite`** (`api/pilotage.py:620-687`) recompte « comme la liste des lots » :
- `lot_id` → `tracabilite(lot=numéro)` puis filtre sur la référence du lot ;
- chaque ligne : `quantite` = |q| pour un transfert, sinon signée ; `annulation` (a un
  `contrepasse_id`), `annule` (est annulée) ; libellé « Annulation — … » ; `reference_doc` =
  n° du document en base ;
- `comptes` = lignes ni annulation, ni annulée, ni transfert ;
  `entrees = Σ q > 0` hors `RETOUR_PRODUCTION` ; `sorties = −Σ (q < 0 ou RETOUR_PRODUCTION)`
  (un retour des machines réduit le sorti) ; `ordres` recalculés sur `comptes`.
- Refus 400 si ni lot, ni ordre, ni fil, ni `lot_id`.

---

## 7. Ordres de fabrication : prévu figé, réalisé

### 7.1 `consommation_par_of(donnees)` (`moteur.py:3326-3445`)

Par n° d'OF (mouvements portant un `numero_of`) :
- `premier = min(date)` de tous ses mouvements (annulations comprises) ;
- les annulations **et** les écritures annulées sont **ignorées** (elles ne sont ni parties
  au métier ni revenues ; avant, elles gonflaient le consommé, les retours et repoussaient la
  fin) ;
- `signee < 0` → `consomme += −signee`, `debut = min`, `fin = max` (dates des **sorties**
  seulement) ; sinon `retours += signee` ;
- `references[ref] += −signee` (net : sorties positives, retours négatifs) ; `lots` ← lot.
- sans sortie : `debut = fin = premier`.

**Prévu** `prevu_de(ordre)` :
- `ordre.theorique` non None (figé à la validation, kg **sans** perte) → tel quel ;
- sinon (ordre validé avant le figeage) : `instant = valide_le`, sinon fin du jour de l'ordre,
  sinon `datetime.max` ; pour chaque fabrication `(qualité, m²)` :
  `version = versions_recette_pendant(qualité, instant, instant)[-1]` (la recette **en vigueur
  ce jour-là**, celle d'aujourd'hui sans historique), `prevu[ref] += kg_m2_version(...)[ref] × m²`
  pour les quantités > 0 (fonctions de la partie A).

Pour chaque fiche (OF inconnu de `donnees.ordres` — non validé ou annulé — : prévu vide,
m² 0) : `net = consomme − retours`, `theorique = Σ prevu`, `ecart = net − theorique` et
`ecart_relatif = ecart / theorique` si `theorique ≠ 0` (sinon None), `fabrications`,
`qualite = " · ".join(qualités)`, `m2`, `commentaire`, `taux_perte_fige = ordre.perte`,
`references` = pour chaque fil sorti `{quantite, theorique = prevu.get(ref, 0), ecart =
quantite − prevu[ref] si ref ∈ prevu sinon None, hors_recette = prevu non vide et ref ∉ prevu}`
+ pour chaque fil de la recette non sorti `{quantite 0, theorique kg, ecart −kg,
hors_recette faux}`. Tri par `(fin, n°)` décroissant.

### 7.2 `ajuster_ordre` et `consommations` (`api/production.py:64-90`)

L'écran lit le prévu **perte comprise** :
`perte = taux_perte_fige` si non None, sinon `parametres.taux_perte` (actuel) ; `k = 1 +
perte` ; pour chaque référence `theorique ← theorique × k`, `ecart ← quantite − theorique`
(si l'écart n'était pas None), `kg_par_ml` ajouté ; `theorique = Σ`, `net = Σ quantite`,
`ecart`, `ecart_relatif` recalculés ; `taux_perte = perte`.
`consommations(s, donnees) = {OF: ajuster_ordre(fiche, taux_perte, densités)}`.

**Route `GET /ordres-fabrication`** (`api/pilotage.py:690-720`) : exclut les OF dont le bon
est « annulé » ; `total_consomme = Σ net` ; `total_theorique = Σ theorique` des ordres avec
recette (théorique ≠ 0) ; `total_consomme_avec_recette = Σ net` de ces mêmes ordres.

### 7.3 `realise_par_qualite(donnees, date_ref, aujourd_hui=None)` (`moteur.py:3448-3510`)

Douze mois **écoulés** : `debut = fin_de_mois(date_ref, −11)`, `mois = [fin_de_mois(debut, i)
pour i = 0…11]` (le dernier est le mois de `date_ref`). `passe = aujourd_hui ≠ None et
date_ref < aujourd_hui`.

Plan :
- [classeur] `plan = plan_mensuel(donnees, 1er jour du mois de debut)` (le plan glissant
  vu d'il y a onze mois).
- corrigée : `service = 1er du mois du premier mouvement du journal` ; `courant =
  plan_mensuel(donnees, date_ref)` ; pour chaque ligne du plan et chaque mois `fin` :
  - `0` si `fin < service` (mois d'avant la mise en service) ;
  - sinon si `fin < date_ref` : `m2_passe(donnees, ligne, fin)` (plan **de l'époque**, au
    prorata des jours de chaque version, partie A) ;
  - sinon si `passe` : `m2_passe(donnees, ligne, fin, jusqu_a=date_ref)` (mois entamé vu à
    une date passée) ;
  - sinon `courant[q][_mois_entre(date_ref, fin)]` (= M0 du plan d'aujourd'hui, mois entier).

Réalisé : ordres (validés) avec `date ≤ date_ref`, rangés au mois de leur date s'il est dans
la fenêtre ; `realise[q][rang] += m²` par fabrication.

`clos = nb de mois avec fin < date_ref` : toujours 11 (le douzième, `fin_de_mois(date_ref)`,
n'est jamais antérieur à `date_ref`). Par qualité (union plan ∪ réalisé, triée) : `plan`, `realise` (12 valeurs),
`total_plan`, `total_realise`, `ecart = (Σ fait des mois clos − Σ prévu des mois clos) / Σ
prévu des mois clos` (None si 0 : le mois en cours n'a pas fini de produire).
Rend `{mois (ISO), mois_clos, lignes, debut_service}`.

**Routes** (`api/production_plan.py`) :
- `GET /production/realise` (`:186-198`) : `realise_par_qualite(charger(s), date, today)` +
  `plan_fige = True`.
- `GET /production/plan` (`:87-143`) : `glissant = plan_mensuel(date)` ; `tisse_m0[q] =
  realise[-1]` (mois en cours) ; `hors_plan` = qualités tissées absentes du plan ;
  `kg_m2[q] = Σ_{recette d'aujourd'hui} kg_par_m2 × (1 + taux_perte)` ; `lignes_recette` ;
  `recette_conforme` (contrôle C01) ; par qualité : `total_annuel = Σ base × coefficient`
  (**sans croissance**, même arrêtée), `glissant`, `total_glissant`, `tisse_mois_en_cours` ;
  `tisse_hors_plan` (m² > 0).
- `GET /production/besoins` (`:204-286`) : `charger_au(date)` ; `kg = besoins_mensuels`
  (plan × recettes × (1 + perte)) ; détail par qualité `kg_m2 = kg_par_m2 × (1+perte)`,
  `kg[i] = kg_par_m2 × m²[i] × (1+perte)`, triées par total décroissant ; `retenu =
  LigneStock.besoins` (corrigé par le coefficient de réalisation, partie A) sinon `kg` ;
  plus `coefficient_realisation`, `conso_reelle`, `stock_disponible`, `bc_en_cours`,
  `stock_projete`, `couverture_jours`, `statut`, `quantite_a_commander`, `unite_achat`,
  `quantite_a_commander_achat`, `kg_par_ml`, `role` ; liste des rôles ; `fenetre_realisation_jours`.

---

## 8. Autres routes de pilotage (calculs légers)

| Route | Calcul (`api/pilotage.py`) |
|---|---|
| `_date` (`:28-36`) | date de référence = aujourd'hui sauf paramètre ; refus 400 hors années 2000–2100 |
| `GET /besoins` (`:78-107`) | `plan_mensuel`, `besoins_mensuels` (données sans journal) ; `total = Σ` des 12 mois, par qualité et par référence |
| `GET /nomenclature` (`:110-121`) | `nomenclature` + `controle_recettes` ; alimentation : `prix, devise, prix_kg, cout_m2_mad` masqués |
| `GET /plan-achat` (`:124-135`) | `plan_achat(charger_au(jour), etat_stock)` (partie A) |
| `GET /plan-achat/fournisseur/{nom}` (`:138-204`) | lignes du fournisseur avec `quantite_a_commander > 0`, triées par `montant_a_commander_mad` décroissant ; `contenance_palette = poids_bobine × bobines_palette` ; `prix_indicatif = prix_kg` ; `montant_indicatif_mad` ; `en_preparation = bc_en_preparation` ; 404 si fournisseur inconnu |
| `GET /controles` (`:349-377`) | contrôles (hors périmètre) |

---

## 9. Coût de revient à l'importation

Règle du métier et du classeur « IMPORTATION 2026 » : les frais d'un dossier se répartissent
sur ses marchandises **à la valeur** (ou au poids pour un poste réglé ainsi) ; la TVA en est
exclue (récupérable : elle pèse sur la trésorerie, pas sur le coût). Un dossier = une facture
= une livraison (décision structurante).

### 9.1 Postes (`modele.py:518-534`)

| Code | Libellé | Récupérable |
|---|---|---|
| DD | Droits de douane | non |
| TPI | Taxe parafiscale à l'importation | non |
| TVA | TVA à l'importation | **oui** |
| PORT | Port Med | non |
| FRET | Fret | non |
| ASSUR | Assurance | non |
| TRANSIT | Transitaire | non |
| TIMBRE | Timbre | non |
| INT_OC | Intérêts / ordre de change | non |
| TMSA | TMSA | non |
| AUTRE | Autre frais | non |

Le référentiel `poste_frais` (Réglages) l'emporte : `ChargeImport.recuperable_poste` (si non
None) et `ChargeImport.cle` (« valeur » | « poids ») sont lus depuis lui par le dépôt.
`RECUPERABLES = {"TVA"}` (`moteur.py:3525`, dérivé de `POSTES_IMPORT`).

### 9.2 `LigneRevient` (`moteur.py:3528-3566`)

`dossier, ligne_id, reference, lot_fournisseur, fournisseur, quantite (kg), valeur_mad, part,
charges_mad (frais non récupérables), tva_mad (récupérables), detail {poste: montant},
poids_kg`. Propriétés :
`revient_mad = valeur_mad + charges_mad` ; `revient_unite = revient_mad / quantite` (0 si
quantité nulle) ; `valeur_unite = valeur_mad / quantite` ; `surcout = charges_mad /
valeur_mad` (0 si nulle) ; `decaisse_mad = revient_mad + tva_mad`.
`poids_kg` = `LigneImport.poids_kg` = **la quantité** (`modele.py:577-580`) — la colonne
`dossier_ligne.poids_kg` de la base n'est pas lue par le moteur (voir § 12).

### 9.3 `valeur_ligne_import(ligne, parametres)` (`moteur.py:3611-3621`)

`devise (ou MAD si vide) == MAD` → `valeur_devise` (un cours porté par erreur est ignoré,
`6f3a340`) ; sinon `valeur_devise × (ligne.cours or taux(devise))` — cours de la banque saisi
par dossier, à défaut cours du jour.

### 9.4 `revient_dossier(dossier, parametres) → [LigneRevient]` (`moteur.py:3624-3686`)

1. `valeur[l] = valeur_ligne_import(l)`, `total = Σ valeur` ; `poids[l] = l.poids_kg`,
   `poids_total = Σ poids`.
2. Postes récupérables du dossier : `{c.poste | c.recuperable}` ∪ `{p ∈ RECUPERABLES | aucune
   charge du poste p n'a recuperable_poste = False}`. Un **poste** entier est récupérable ou
   non.
3. Classement de chaque charge :
   - **directe** si `c.ligne` désigne une marchandise du dossier → `directes[ligne][poste] +=
     montant` (elle lui revient entière) ;
   - **parts figées** si `c.parts` non vide, toutes ses lignes au dossier, et
     `|Σ parts − montant| < 0,005` → chaque part va à sa ligne (un dossier clos dont le poste a
     changé de clé garde son ancienne répartition, `58f507c`) ;
   - sinon **globale** : `globales[(poste, "poids" si c.cle == "poids" sinon "valeur")] += montant`.
4. Pour chaque ligne : `part = valeur / total` (0 si `total = 0`), `part_poids = poids /
   poids_total` (0 si nul) ; `detail[poste] = Σ globales × (part_poids si clé poids sinon
   part) + Σ directes` ; `charges_mad = Σ detail des postes non récupérables` ; `tva_mad =
   Σ detail des postes récupérables`.
5. Aucun arrondi : `Σ revient` retombe sur le total du dossier (au flottant près). Une charge
   globale d'un dossier sans valeur (ou sans poids pour la clé poids) ne va à **aucune** ligne :
   « frais non répartis », montrés à part par les écrans.

**Exemple chiffré.** Ligne A : 6 000 USD × 10 = 60 000 MAD, 1 000 kg ; ligne B : 40 000 MAD,
3 000 kg. Charges : DD 10 000 (valeur), FRET 8 000 (clé poids), TRANSIT 2 000 affecté à B, TVA
21 000 (valeur).
`part A = 0,6`, `part B = 0,4` ; `part_poids A = 0,25`, `B = 0,75`.

| | DD | FRET | TRANSIT | TVA | charges | revient | revient/kg | surcoût |
|---|---|---|---|---|---|---|---|---|
| A | 6 000 | 2 000 | 0 | 12 600 | 8 000 | 68 000 | 68,00 | 13,3 % |
| B | 4 000 | 6 000 | 2 000 | 8 400 | 12 000 | 52 000 | 17,33 | 30,0 % |

Σ revient = 120 000 = 100 000 + 20 000 ; TVA 21 000 à part (décaissé 141 000).

### 9.5 `tva_attendue(dossier, parametres)` (`moteur.py:3580-3603`)

Code général des impôts (TVA à l'importation) :
```
si aucune marchandise : 0
douane = Σ valeur_ligne_import + Σ charges des postes FRET et ASSUR      (valeur CAF)
droits = Σ charges du poste DD
tpi    = Σ charges du poste TPI s'il en existe au moins une, sinon douane × taux_tpi_import (0,0025)
TVA    = (douane + droits + tpi) × taux_tva_import (0,20)
```
Transitaire, banque, port n'entrent pas dans la base (`6f3a340`).

`TOLERANCE_TVA_IMPORT = 0,05` ; `ecart_tva_tolere(attendue) = |attendue| × 0,05` (au-delà de
5 % : erreur de saisie ; en deçà : cours BAM de la déclaration, assurance non saisie).
Utilisé par la fiche dossier (`api/importations.py:286-300`, TVA saisie = poste « TVA »
seul) et le contrôle C29.

**Exemple.** Marchandise 10 000 USD × 10 = 100 000 ; FRET 5 000 ; pas d'ASSUR ; DD 2 500 ;
pas de poste TPI → TPI = 105 000 × 0,0025 = 262,50 ; TVA attendue = (105 000 + 2 500 + 262,50)
× 0,20 = **21 552,50** ; tolérance 1 077,63 : une TVA saisie de 21 000 passe (écart 552,50),
une de 20 000 est signalée.

### 9.6 `lignes_aberrantes(repartis, seuil)` (`moteur.py:3689-3694`)

`charges_mad > 0,005` et (`valeur_mad ≤ 0` ou `charges_mad > valeur_mad × seuil`), `seuil =
seuil_surcout_import` (défaut 1,0 = 100 %). Contrôle C35, alerte du dossier.

### 9.7 `lignes_negatives(repartis)` (`moteur.py:3697-3700`)

`revient_mad < −0,005` (un avoir rend la marchandise négative).

### 9.8 `ecart_facture(dossier, parametres)` (`moteur.py:3703-3721`)

None si pas de montant de facture ou pas de ligne, ou si une ligne n'est pas dans la devise
de la facture (`(x.devise or "MAD") ≠ (facture_devise or "MAD")`). Sinon `recu = Σ
valeur_devise` (pesée × prix), `ecart = montant − recu`, `part = ecart / recu` (1,0 si recu
nul), `hors_tolerance = |ecart| > 0,005 et |part| > toler_facture_import` (0,02). La
valorisation reste à la pesée × le prix ; l'écart se dit (C36).

### 9.9 Fiche dossier (`api/importations.py:190-330`, pour mémoire)

`marchandise = Σ valeur_mad`, `charges` (non récupérables, selon le référentiel),
`reparties = Σ charges_mad`, `non_reparties = charges − reparties` si > 0,005 (idem TVA),
`poids = Σ poids_kg`, `revient = marchandise + reparties`, `decaisse = + tva_repartie`,
`surcout = reparties / marchandise`, `surcout_aberrant = marchandise > 0 et reparties >
marchandise × seuil` ; par ligne : `valeur_douane = valeur_mad + detail[FRET] +
detail[ASSUR]`, `droits_attendus = valeur_douane × taux_droits` du code douanier **actif**
(total rendu seulement si toutes les matières ont un code actif) ; `cours_applique = 1 si MAD
sinon cours or taux` ; `cours_disparates` (une devise à plusieurs cours) ; `lignes_cours_bon`.

### 9.10 `revient_par_reception(donnees) → {ligne_reception_id: LigneRevient}` (`moteur.py:3724-3737`)

Pour chaque dossier, chaque ligne répartie ayant une `ligne_reception_id` : indexée par elle.
C'est **par la ligne de réception** qu'une entrée retrouve son coût (jamais par son lot : un
n° de lot qui revient d'une livraison à l'autre ferait prendre à l'une le coût de l'autre,
`5ca0960`).

### 9.11 `revient_par_lot(donnees) → {(ref, lot): MAD/kg}` (`moteur.py:3740-3760`)

Seulement les marchandises **saisies à la main** (sans ligne de réception : reprise, stock
d'ouverture), avec un lot et un `revient_unite` non nul : `Σ revient_mad / Σ quantite` par
(référence, lot) (moyenne au poids de deux lignes du même lot), si `Σ quantite > 0`. Utilisé
par `cout_d_entree` pour une entrée **sans** ligne de réception (`58f507c` : un dossier saisi à
la main ne donne plus son coût à une réception hors dossier du même lot).

### 9.12 Analyse du coût de revient — `GET /importations/analyse/revient` (`api/analyse_import.py:80-322`)

Paramètres : `axe` ∈ {reference, composition, type_fil, titrage, couleur, fournisseur,
role_bom, dossier, lot} (400 sinon) ; `q` (texte) ; `debut`, `fin` (sur `date_arrivee` ; un
dossier sans date passe) ; `composition`, `type_fil`, `titrage`, `couleur`, `fournisseur`
(égalités exactes ; composition = `composition or nature`, couleur = `couleur or designation`,
fournisseur = celui de la ligne sinon du catalogue, titrage = `str(titrage)`) ; `qualite`
(fils de sa recette ; 404 si inconnue) ; `statut` (« Ouvert » / « Clos ») ; `references`
(liste « ; ») ; `selection` (JSON : liste de combinaisons de critères parmi composition,
type_fil, titrage, couleur, fournisseur ; une ligne est retenue si **une** combinaison est
entièrement satisfaite ; 400 si illisible ou critère inconnu) ; `detail`.

- Qualité + références : `choisies = (choisies ∩ recette)`, ou, si l'intersection est vide,
  rien du tout si des références étaient données (`{"\0"}`), sinon la recette.
- Texte : chaque mot (sans accents, minuscules — `_sans_accents` NFD) doit se trouver dans la
  concaténation : n° et libellé du dossier, référence, lot, fournisseur, nature, composition,
  type, **libellé du type** (« frisé » trouve FRZ), « titrage unité », couleur, désignation.
- Pour chaque dossier filtré : `repartis = revient_dossier` ; `hors_tva = Σ charges non
  récupérables` (propriété `recuperable` de chaque charge) ; `ecart = hors_tva − Σ charges_mad`.
- Groupement par la valeur de l'axe (« — » si vide) : `quantite`, `poids`,
  `marchandise_mad`, `charges_mad`, `tva_mad`, `lignes`, `dossiers`, `detail` par poste.
- Frais non répartis (`|ecart| > 0,005`) comptés pour le dossier si : aucun filtre, ou au moins
  une ligne retenue, ou (dossier vide, pas de filtre matière, et tous les mots dans « n°
  libellé »).
- Par groupe : `unite = "kg"`, `revient_mad = marchandise + charges`, `decaisse_mad = +
  tva`, `marchandise_unite = marchandise / quantite`, `revient_unite = revient / quantite`,
  `marchandise_kg = marchandise / poids`, `revient_kg = revient / poids` (0 si poids nul),
  `surcout = charges / marchandise`. Tri par `revient_mad` décroissant.
- Totaux : `total_lignes`, `total_poids`, `total_marchandise_mad`, `total_charges_mad`,
  `total_revient_mad`, `total_tva_mad`, `total_decaisse_mad`, `frais_non_repartis_mad`,
  `dossiers_non_repartis`, `ids_dossiers`.
- `detail` : lignes une à une (`revient_kg = revient / poids`, `decaisse`, `surcout`…) triées
  par (date d'arrivée, dossier) décroissants.

`GET /export/revient` (`:418-470`) : la même analyse en classeur ; ligne Total avec
`charges / achat` et `revient / poids`.

### 9.13 Coût d'une qualité pondéré par la recette — `GET /importations/analyse/qualite/{code}` (`api/analyse_import.py:325-415`)

1. `analyse = analyse_revient(axe="reference", references = fils de la recette, debut, fin)` ;
   `couts[ref] = revient_kg` (coût hors TVA au kilo, sur la période).
2. Par ligne de recette, rôle `r = role_bom` : `poids_m2_ligne = poids du rôle (qualité) ×
   pct / 100` (en kg/m², ou **ml/m²** pour un rôle au mètre). Bloc par rôle : `poids_m2` =
   poids du rôle, `lineaire`, `fils += 1` ; si le fil a un coût : `importes += 1`,
   `connu_m2 += poids_m2_ligne`, `cout_m2 += kg_par_m2(code, ref, pct) × couts[ref]`
   (kg/m² — ml/m² × densité pour un rôle au mètre — × MAD/kg).
3. Chaque ligne d'analyse reçoit `role`, `part_recette`, `poids_m2`, `cout_m2`.
4. Synthèse :
   - `poids_m2 = Σ poids des rôles au kilo` (rôles linéaires exclus) ;
   - `couverture = Σ connu_m2 (rôles au kilo) / poids_m2` ;
   - `cout_m2 = Σ cout_m2 de tous les rôles` (ce qui est connu) ;
   - `cout_m2_estime = Σ_{rôles avec connu} cout_m2 / connu_m2 × poids_m2` (extrapolation au
     rôle entier) ;
   - `cout_kg_tapis = Σ_{rôles au kilo connus} (cout_m2 / connu_m2 × poids_m2) / Σ_{mêmes}
     poids_m2` ;
   - `roles_sans_cout`, `references_de_la_recette`, `references_importees`.

---

## 10. Suivi : échéancier, photo du jour, bilan, courriel

### 10.1 `_factures_dues(s)` (`api/suivi.py:296-317`)

Parcourt les lignes des réceptions portant une facture :
- `apporte[facture] += pesée × prix` pour les réceptions **validées**, lignes non refusées
  (montant estimé d'une facture sans montant saisi, dans la devise des lignes, sans
  conversion) ;
- `annulees = toutes − validées − brouillons` (toutes ses réceptions annulées : plus due) ;
- `en_attente = brouillons − validées` (que des brouillons : pas encore due).

### 10.2 `GET /echeancier?du=&au=` (`api/suivi.py:320-392`)

`en_mad(montant, devise) = montant × (1 si MAD sinon taux courant de la table devise, 1 par
défaut)`.

Factures : `montant = facture.montant or apporte` ; `estime = montant saisi nul et montant >
0` ; puis, dans l'ordre :
1. en attente → ignorée ;
2. annulée : réglée → `ecartees` (« réglée, réception annulée : avoir à demander ») ; sinon
   si montant > 0 → `ecartees` (« réception annulée : plus due ») ;
3. réglée (`payee_le`) → `reglees` ;
4. avec échéance → `lignes` (date = échéance) ;
5. sans échéance, montant > 0 → `a_dater`.

Frais d'importation (montant en MAD) : réglé → `reglees` ; avec échéance → `lignes` ; sans
échéance et montant > 0 → `a_dater` (même d'un dossier clos : clore fige le coût, pas le
paiement).

Filtre `du`/`au` appliqué **aux seules lignes datées**. `lignes` triées par date ;
`reglees` par date de règlement décroissante, 300 au plus. `par_mois[AAAA-MM] = Σ
montant_mad` ; `echu_mad = Σ montant_mad des lignes de date < aujourd'hui` ; `en_retard`
par ligne ; `a_dater_mad` ; `total_mad = Σ lignes`.

`PUT /echeancier/paiement` (`:412-435`) : `payee_le` ni futur, ni antérieur au début de la
pièce (`_debut_de_la_piece` : date de la facture, sinon la première réception qui la porte ;
pour un frais, sa `date_piece`) ; `None` annule le règlement.

### 10.3 Photo quotidienne des indicateurs — `photographier_indicateurs(s, jour=None)` (`api/suivi.py:490-513`)

Données d'aujourd'hui (`depot.charger`), `etat_stock(jour)`, `cockpit(donnees, jour, lignes)`
(sans coûts rendus). **Indicateurs photographiés** (JSON dans `indicateur_jour`, une ligne
par jour, la dernière l'emporte) :

| Clé | Source |
|---|---|
| `valeur_stock_mad` | `cockpit.stock.valeur_mad` |
| `couverture_jours` | `cockpit.stock.couverture_ponderee_jours` |
| `ruptures`, `critiques`, `urgents` | `cockpit.stock.*` |
| `a_commander_mad` | `cockpit.achats.budget_a_commander_mad` |
| `commandes_en_cours_mad` | `cockpit.achats.montant_bc_en_cours_mad` |
| `otif_moyen` | moyenne des `otif` non None de **toutes** les réceptions (une réception, une voix ; pas la moyenne des fournisseurs — `96db9ea`) ; None si aucune |

Déclenchée par la boucle de fond (`taches_du_jour`, `:841-847`) s'il n'y a pas de photo du
jour, ou à la demande de la direction (`POST /indicateurs/photographier`, réécrit).
`GET /indicateurs/historique` : les photos par jour croissant.

### 10.4 Bilan du mois — `bilan(s, annee, mois)` (`api/suivi.py:528-614`)

`debut = 1er du mois`, `fin = 1er du mois suivant` (exclu). Lecture **directe de la table
mouvement** (quantités signées de la base, types de la base : OUVERTURE, RECEPTION, SORTIE,
RETOUR_MACHINE, RETOUR_FOURNISSEUR, AJUSTEMENT, TRANSFERT) :
- `stock_debut_kg = Σ q` des mouvements datés `< debut` (tout type, annulations comprises) ;
  `stock_fin_kg = Σ q` datés `< fin` ;
- pour les mouvements du mois, **hors TRANSFERT** : une annulation (`contrepasse_id`) →
  `annulations[type] += q` (ligne à part : une sortie annulée en octobre ne fait pas de
  « sorties » négatives en octobre, `f85dabd`) ; sinon `flux[type] += q` ; et si c'est une
  `RECEPTION` **non annulée** : `valeur_entrees += q × prix × (1 si MAD sinon cours figé du
  mouvement or taux courant)` — prix de la facture, pas le coût de revient ;
- `m2_par_qualite` : Σ m² des fabrications des bons de sortie **validés** datés dans le mois ;
  `m2_total` ;
- `commandes` : nb de bons numérotés dont la date de commande est dans le mois (annulés
  compris) ; `receptions` : nb de réceptions validées datées dans le mois ;
- `otif` = moyenne des `otif` non None des performances des réceptions datées dans le mois ;
  `receptions_notees` ;
- `ordres` : consommations (§ 7.2) des OF validés dont la **première sortie** (`debut`) est
  dans le mois ; `ecarts_ordres` = les 8 plus grands `|ecart_relatif|` ;
- `jour_calcul = min(dernier jour du mois, aujourd'hui)` ; `au_fin = a_la_date(données,
  jour_calcul, aujourdhui = aujourd'hui)` ; `lignes = etat_stock(au_fin, jour_calcul)` ;
  `ruptures` / `critiques` = nb de statuts contenant « RUPTURE » / « CRITIQUE » à la fin du
  mois ;
- `valeur_debut_mad = Σ valorisation(au_debut, etat_stock(au_debut, veille)).valeur_mad` avec
  `veille = debut − 1 jour` ; `valeur_fin_mad` idem à `jour_calcul` ;
- `consommation_mad = Σ couts_du_journal(au_fin).consommation` datées dans le mois (coût net
  des sorties et retours des machines) ;
- quantités : `entrees_kg = flux[RECEPTION]`, `sorties_kg = −flux[SORTIE]`,
  `retours_machine_kg = flux[RETOUR_MACHINE]`, `retours_fournisseur_kg =
  −flux[RETOUR_FOURNISSEUR]`, `ajustements_kg = flux[AJUSTEMENT]`, `ouvertures_kg =
  flux[OUVERTURE]`, `annulations_kg = Σ annulations`, `annulations` (|q| > 1e-9).

Équation affichée (vraie par construction) :
`stock_fin = stock_debut + entrées + ouvertures − sorties + retours machines − retours
fournisseur + ajustements + annulations`.

`GET /bilan?mois=AAAA-MM` (`:617-674`) : page HTML imprimable ; nombres `round(x, d) + 0,0`
(pas de « −0 »), espace des milliers, virgule décimale ; la case « Stock d'ouverture saisi »
n'apparaît que si `|ouvertures| > 1e-9` ; OTIF en % entier.

### 10.5 Courriel du lundi — `services/courriel.py`

`contenu(s, jour)` (`:31-71`) : données d'aujourd'hui, `cockpit(donnees, jour, lignes)`, puis :
- valeur du stock (`stock.valeur_mad`, arrondie à l'unité, espace des milliers) et
  couverture pondérée (jours, sans décimale) ;
- ruptures, critiques, urgentes ;
- « À commander selon le plan » = `achats.budget_a_commander_mad` ;
- commandes en retard : bons numérotés au statut envoyée, confirmée ou à approuver dont
  `_statut_livraison(...)` contient « retard » (`api/achats.py:78-101`) : livré si chaque ligne
  a reçu (net des retours, hors quarantaine) `≥ quantité × (1 − toler_in_full)` ; sinon
  `prevue = ETA or date promise` ; à l'heure si `prevue + toler_retard_jours ≥ jour` ; avec du
  reçu → « 🟠 Partiel retard » sinon « 🔴 En retard » ; « 🟡 Reçu sous réserve » (tout est là,
  une part en quarantaine) n'est pas un retard. Les 8 premiers n° cités ;
- nb de bons à approuver ; brouillons (réceptions, ordres, opérations) ; besoins signalés non
  traités ; réclamations ouvertes.
`envoyer_si_lundi` : seulement un lundi (`weekday() == 0`), serveur SMTP configuré,
destinataires non vides, et pas déjà envoyé ce jour (`courriel_dernier_envoi`).

---

## 11. Inventaire : écarts valorisés

`api/inventaires.py`. Tout est en **kilos** (décision du 8 octobre 2026, `d2e1e39` ; les
écarts « kg et ml séparés » de `8b9c2ef`/`a536296` ont disparu avec les matières au mètre ;
`kg_par_ml` reste donné pour lire des mètres indicatifs).

- `retenu(x) = second_compte si non None sinon compte` (`:35-37`).
- `_hors(theorique, compte, tolerance)` (`:40-46`) : faux si `compte` None ; faux si `|compte −
  theorique| < 0,001` ; vrai si `theorique ≤ 0` ; sinon `|écart| / theorique > tolérance`.
- `_ecart_hors_tolerance(x, tol) = _hors(theorique, retenu)` ; `a_recompter(x, tol) =
  second_compte None et _hors(theorique, compte)`.
- `couts_inventaire(s)` (`:58-64`) : `(cmup_par_reference(donnees, journal.cmup()),
  journal.unitaire)` sur les données d'aujourd'hui.
- `inventaire_dict` (`:67-128`) : coût d'une ligne = coût unitaire de **l'ajustement qu'elle a
  écrit** (inventaire validé : mouvement `document = inventaire`, même lot et magasin, non
  annulation) s'il est dans `unitaire`, sinon CMUP actuel de la matière (avec les replis de
  `cmup_par_reference`). Par ligne : `ecart = retenu − theorique` (None si non compté),
  `cmup_mad`, `valeur_ecart_mad = ecart × coût`, `hors_tolerance`, `a_recompter`. Totaux sur
  les lignes comptées : `ecart_total = Σ ecart` (net kg), `ecart_absolu = Σ |ecart|`,
  `ecart_valeur_mad = Σ valeur`, `ecart_valeur_absolue_mad = Σ |valeur|` (50 kg de trop à 10 et
  50 kg de moins à 90 font 0 kg net et 4 000 MAD de perte) ; compteurs `nb_lignes`,
  `nb_comptees`, `hors_tolerance`, `a_recompter`, `recomptees`. Alimentation : montants masqués.
- Théorique figé à l'ouverture = soldes `> 0` du périmètre (magasin, matières, rôles,
  compositions, classes ABC du jour) ; tolérance = celle saisie ou le réglage
  `tolerance_inventaire` (0,02).
- Validation (`:381-415`) : écart hors tolérance sans justification (< 3 caractères) refusé ;
  pour chaque ligne comptée avec `|écart| ≥ 0,001` : un `AJUSTEMENT` de quantité `écart` à la
  date de l'inventaire (passera au CMUP du moment dans `couts_du_journal`, ou au coût de
  ré-entrée si le stock est vide). Refus si un lot figé a bougé après la date (`_bouge_apres`).
- Inventaire tournant `GET /inventaires/a-compter` (`:194-244`) : cadence `A 30 j, B 90 j,
  C 365 j` (classe ABC du jour ; vide → C) ; par (matière, magasin) détenant `> 0,001` kg :
  dernier comptage = date max des inventaires **validés** où la ligne a été comptée ; dû si
  jamais compté ou `jours ≥ cadence` ; regroupé par matière (stock des magasins dus, magasins,
  plus ancien comptage — « jamais » l'emporte) ; tri `(classe, dernier comptage — jamais en
  tête —, référence)`. Un comptage ne vaut que pour le magasin compté (audit 2-G M2).

---

## 12. Points incohérents ou ambigus

Constats faits en lisant le code (aucun n'a été corrigé ; à trancher pour Gestion MP PRO, la
parité imposant de reproduire le comportement actuel sauf décision contraire).

1. **Cockpit : un CMUP nul retombe sur le catalogue** (`moteur.py:2402-2403`,
   `cout.get(ref) or catalogue(ligne)`), alors que la Valorisation garde 0 (« un coût moyen nul
   est un vrai coût », `moteur.py:1999`, `61027e4`). Une matière détenue à coût nul vaut 0 dans
   Valorisation et le prix du catalogue au Cockpit : deux pages, deux chiffres.
2. **Cockpit vs Valorisation sur les stocks négatifs** : le Cockpit ne valorise que
   `detenu > 0` ; la Valorisation additionne aussi les stocks négatifs (valeur négative).
3. **Entrée à prix 0** : `cout_d_entree` teste `if mouvement.prix_unite:` (`moteur.py:1872`) ; une
   ouverture ou une réception à 0 MAD entre au **prix du catalogue**, contrairement à l'esprit
   « un coût nul est un coût » (les essais l'évitent avec un article à prix catalogue nul).
4. **Revient négatif accepté par le lot, refusé par la ligne de réception** : la ligne de
   réception exige `revient_unite > 0` (`:1863`), le lot seulement une valeur non nulle
   (`:1870`, et `revient_par_lot` garde les `revient_unite` négatifs). La docstring de
   `lignes_negatives` (« le coût moyen les ignore ») n'est vraie que pour la première voie.
5. **Cours du jour qui réécrit le passé malgré « cours figé »** :
   - `cmup_par_reference` (repli sans stock) convertit les prix payés au cours **courant**
     (`:1996`) ;
   - `historique_prix`, `achats_dates` sans coûts, la matrice (non convertie du tout),
     `couts_rendus` (cours du **bon**, pas celui figé sur le mouvement) ;
   - `valeur_ligne_import` d'un dossier **ouvert** sans cours → cours du jour : changer le cours
     d'une devise change le coût de revient, donc le CMUP, de marchandises déjà sorties
     (bloqué seulement pour la période close) ;
   - l'échéancier convertit au cours courant.
6. **Matrice des prix en devises mélangées** (`api/pilotage.py:455-473`) : `prix_achat` moyenné
   sans conversion ; une référence achetée en USD puis en EUR le même mois mélange les deux.
7. **Commentaire périmé** : `LigneValorisation.valeur_mad` dit « les magasins seuls »
   (`moteur.py:1795`) alors que le code vaut magasin + machine (`169dfdc`) ; le commit
   `f33a428` disait « sa valeur reste à part », renversé le même jour par `169dfdc`.
8. **Double comptage possible du fil monté** : le fil sur les métiers a été sorti
   (`SORTIE_PROD`) donc compté consommé dans `CoutsDuJournal.consommation` (DIO, bilan), et il
   est aussi ajouté à la valeur du stock (Valorisation, Cockpit). Voulu par la décision du
   8 octobre, mais le DIO compare alors un stock qui contient une part déjà consommée.
9. **Bilan du mois en cours incohérent** : `valeur_fin_mad` est calculée à `min(fin−1,
   aujourd'hui)` ; pour le mois en cours c'est aujourd'hui, donc **avec** le fil monté
   (`montage_connu`), alors que `stock_fin_kg` (journal) et `valeur_debut_mad` (date passée)
   l'excluent. Par ailleurs `entrees_kg` compte les réceptions annulées (compensées sur la
   ligne « annulations ») mais `valeur_entrees_mad` les exclut ; et `valeur_entrees_mad` est au
   prix de la facture alors que `valeur_debut/fin` et `consommation` sont au coût de revient :
   `valeur_debut + entrées − consommation ≠ valeur_fin` en général.
10. **`commandes` du bilan** comptent les bons annulés (seul `numero` non nul est exigé).
11. **`fournisseurs_actifs` du Cockpit** = tous les fournisseurs, actifs ou non
    (`moteur.py:2540`) ; `nb_references` = tout le catalogue.
12. **DPO sur tout l'historique** : aucune fenêtre de dates ; un bon soldé pèse à sa quantité
    commandée, pas livrée.
13. **Dernier prix d'un jour à plusieurs achats** : `achats_dates` trie les tuples (date, prix) :
    le « dernier prix payé » d'un jour à deux achats est le **plus élevé**, pas le dernier saisi.
14. **`LignePrix.date_bc` est la date de réception** (`depot.py:426`) : le nom trompe (matrice
    « par mois de BC », historique « date BC »).
15. **`LigneHistoriquePrix.origine`** toujours vide (`getattr(prix, "origine", "")`, champ
    inexistant) ; **`prix_constates`** est du code mort.
16. **Opportunités : article inactif comparé** — les rivaux doivent être actifs, mais l'article
    lui-même peut être inactif s'il a une consommation ; et le défaut `meme_couleur` diffère
    (faux dans le moteur, vrai sur les routes Cockpit et Opportunités, faux pour la photo et le
    courriel, où le bloc n'est pas lu).
17. **Un rival « hors fenêtre »** n'est compté écarté que si son **dernier** prix est sous le prix
    actuel, même si le prix proche ne l'est pas (et inversement).
18. **`m2_passe(..., jusqu_a)` ignore `jusqu_a` sans historique du plan** (`moteur.py:276-282`,
    partie A) : dans `realise_par_qualite` vu à une date passée, le mois entamé vaut le mois
    entier pour une qualité sans version, mais un prorata pour une qualité versionnée.
19. **Prévu d'un ordre non figé** : la recette est celle de l'époque, mais la perte appliquée
    par `ajuster_ordre` est le `taux_perte` **actuel** (`taux_perte_fige` None) — changer le
    réglage réécrit l'écart des anciens ordres.
20. **`ScoreFournisseur.ecart_pesee_moyen`** se moyenne sur toutes les réceptions, alors que
    `on_time`/`in_full`/`in_spec` ne le sont que sur les réceptions notées.
21. **Clé `(bc, référence)` de l'In-Full** : deux lignes d'un même bon sur la même référence
    partagent `deja` et `livre` ; chacune est jugée sur le total.
22. **Taux de retours** : entrées = `ENTREE_RECEPTION` seules (les stocks d'ouverture ne comptent
    pas) et fournisseur = celui **du lot** ; une matière renvoyée d'un lot d'ouverture pèse sur
    le fournisseur sans entrée correspondante.
23. **Postes récupérables mêlés** : si un même poste porte une charge `recuperable_poste = True`
    et une autre `False`, `revient_dossier` classe tout le poste récupérable, alors que
    `analyse_revient` (`hors_tva` par charge) compte la seconde hors TVA : `ecart` (frais « non
    répartis ») non nul fantôme. Cas théorique (le référentiel donne une valeur par poste).
24. **`poids_kg` des lignes de dossier** : la colonne `dossier_ligne.poids_kg` (« figée à
    l'entrée », `58f507c`) n'est lue ni par `depot` ni par `importations._vue` ; le moteur prend
    la quantité (`modele.py:577-580`). Équivalent depuis que tout est en kilos (`d2e1e39`), mais
    le commentaire de `LigneRevient.poids_kg` parle encore de mètres.
25. **Frais globaux perdus** : clé « poids » avec poids total nul, ou clé « valeur » avec valeur
    totale nulle → la charge ne va à aucune ligne (les écrans la montrent « non répartie », le
    CMUP l'ignore).
26. **Échéancier** : `echu_mad` est calculé après le filtre `du`/`au` (l'échu dépend de la
    période affichée) ; le montant estimé d'une facture (`apporte`) additionne pesée × prix
    dans la devise des lignes sans vérifier qu'elle est celle de la facture.
27. **`hors_plan` de `/production/plan`** est pratiquement toujours vide (toute qualité a une
    ligne de plan, arrêtée ou non) ; `total_annuel` ignore la croissance et l'arrêt, à la
    différence de `total_glissant`.
28. **Photo du jour** : `photographier_indicateurs(s, jour)` lit les données d'aujourd'hui sous
    une date `jour` éventuellement différente (paramètre jamais utilisé autrement qu'à None) ;
    `otif_moyen` porte sur toutes les réceptions depuis toujours, pas sur une période.
29. **Sortie au-delà du stock dans le CMUP** : seule la part couverte est valorisée et retirée ;
    la quantité du CMUP (`CoutsDuJournal.stock`) peut alors différer du stock du journal
    (`etat_stock`), et la Valorisation multiplie la quantité du journal par le CMUP.
30. **Arrondi d'affichage du bilan** : `round()` de Python (au pair) et non l'ARRONDI d'Excel
    utilisé ailleurs (`arrondi`) — sans effet sur les calculs, visible sur des demis exacts.
