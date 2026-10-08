# Règles de gestion et refus — partie A : référentiels, commandes, réceptions, importations

Inventaire tiré du **code** de Gestion MP (`~/gestion-mp`, état du 8 octobre 2026, dernier
commit `b925e81`), complété par les documents (`docs/CAHIER-DES-CHARGES.md`,
`docs/EXIGENCES-MOHAMED.md`, `docs/AUDIT-2026-10-08.md`, `docs/conformite/final-A/B/C`),
les essais (`tests/*.py`) et les messages de commit (décisions de Mohamed, avec leur hash).
Objectif : qu'une autre équipe reconstruise ces quatre domaines **sans relire l'ancien code**.
La sécurité elle-même (sessions, mots de passe, matrice générale) est dans la partie B ; ici
on dit seulement **quel rôle** chaque route admet.

## 0. Conventions communes

### 0.1 Abréviations des fichiers cités

| Abrév. | Fichier |
|---|---|
| `REF` | `gestion_mp/api/referentiels.py` |
| `RIM` | `gestion_mp/api/referentiels_import.py` (postes de frais, codes douaniers) |
| `CLA` | `gestion_mp/calcul/classification.py` |
| `SUI` | `gestion_mp/api/suivi.py` (versions de recette, import tableur des matières) |
| `ACH` | `gestion_mp/api/achats.py` |
| `DEP` | `gestion_mp/depot.py` |
| `REC` | `gestion_mp/api/receptions.py` |
| `BRO` | `gestion_mp/api/brouillons.py` |
| `STK` | `gestion_mp/services/stock.py` |
| `IMP` | `gestion_mp/api/importations.py` |
| `ANA` | `gestion_mp/api/analyse_import.py` |
| `SEC` | `gestion_mp/securite.py` |
| `MOD` | `gestion_mp/modeles.py` |
| `MOT` | `gestion_mp/calcul/moteur.py` |
| `CMO` | `gestion_mp/calcul/modele.py` |
| `PAR` | `gestion_mp/parametres.py` |
| `PPL` | `gestion_mp/api/production_plan.py` |
| `MAIN` | `gestion_mp/main.py` |
| `EXA` | `gestion_mp/api/exports_achats.py` |

Toutes les routes sont servies sous le préfixe `/api` (`MAIN:134`).

### 0.2 Forme des refus

| Règle | Référence |
|---|---|
| Un refus métier est `erreur(message, code)` = `HTTPException(code, message)` ; **code par défaut 422**. Le corps JSON est `{"detail": "<message>"}`. | `SEC:28-29` |
| Une entrée qui viole un schéma Pydantic (`Field(min_length…, ge…, le…, pattern…)`) reçoit le 422 standard de FastAPI (liste d'erreurs, message anglais), **pas** un message français, sauf les validateurs personnalisés cités ci-dessous (`field_validator`), dont le texte apparaît dans le détail. | FastAPI |
| `401` « Connectez-vous pour continuer. » sans session valide, quelle que soit la route. | `SEC:92-97` |
| `403` « Cette action est réservée à : {permis}. » où `permis` = les libellés en minuscules des rôles admis (ou « la direction »). **La direction passe partout.** | `SEC:104-110` |
| Dépendances de rôle : `acteur` = toute personne connectée ; `DIRECTION = droit()` (direction seule) ; `ACHATS = droit(achats)` (achats + direction) ; `ALIMENTATION = droit(alimentation)` (alimentation + direction) ; `STOCK = droit(achats, alimentation)` (tous) ; `LECTURE = droit(achats, alimentation)`. | `SEC:117-122` |

### 0.3 Journal d'audit

| Règle | Référence |
|---|---|
| `journal(s, qui, action, objet, objet_id, detail)` ajoute une ligne `Journal` : `utilisateur` = nom de la personne (« système » sans personne), `role`, `action`, `objet`, `objet_id`, `detail` **tronqué à 2 000 caractères** ; `quand` = `maintenant()` (heure locale du serveur, Maroc). Écrite dans la même transaction que le geste. | `SEC:159-176`, `MOD:108-120`, `MOD:52-53` |
| Le journal n'est pas seulement une trace : plusieurs règles le **relisent** — renvoi de la direction (`ACH:136-146`), origine d'un solde (« tout reçu » ou à la main, `ACH:550-558`, `DEP:43-52`), dernier montage d'un métier (`REF:1188-1195`), motif d'annulation d'une réception (`REC:253-259`), versions du plan (`PPL:49-60`, marque `plan=`), auteur d'une version de recette (`SUI:452-453`). Le texte des actions et des détails cités dans ce document est donc **contractuel**. | idem |

### 0.4 Numérotation

| Règle | Référence |
|---|---|
| `numero(s, serie, jour, largeur=4)` : numéro suivant de la série **pour l'année de la pièce** (`jour.year`), compteur `Compteur(serie, annee)` lu **sous verrou de ligne** (`with_for_update`) et créé au besoin par `INSERT … ON CONFLICT DO NOTHING` ; deux validations simultanées obtiennent N et N+1. | `SEC:179-207`, `MOD:146` |
| Format : `{serie}-{AAAA}-{NNNN}` (4 chiffres) → `BC-2026-0001`, `REC-2026-0001`, `LOT-2026-0001` ; **sauf** la série `DOS` : `{NN:02d}/{AA:02d}` → `01/26`. | `SEC:196-198` |
| Un document reçoit son numéro **quand il devient réel** (exigence M65) : bon de commande à l'envoi/approbation, réception à la validation, lot interne à la validation ; un brouillon supprimé ne laisse pas de trou. Le dossier d'importation, lui, est numéroté **à l'ouverture**. | `MOD:559-561`, `MOD:640-642`, `ACH:493-515`, `REC:543`, `IMP:560-570` |

### 0.5 Dates permises et période close (règles transverses utilisées ici)

Refus de `date_permise(s, jour)` (`SEC:210-226`) :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| D1 | `jour < date(2000, 1, 1)` | 422 | `f"Date trop ancienne ({jour:%d/%m/%Y}) : vérifier l'année."` | `SEC:213-214` |
| D2 | `jour > date.today()` | 422 | `f"Date dans le futur ({jour:%d/%m/%Y}) : un mouvement se saisit le jour où il a lieu."` | `SEC:215-218` |
| D3 | paramètre `date_cloture` renseigné et `jour <= limite` | 422 | `f"La période jusqu'au {limite:%d/%m/%Y} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir."` | `SEC:219-226` |

Refus de `cout_hors_periode_close(s, dossier, geste, entrees_en_plus)` (`SEC:235-276`) — le
**coût** d'une marchandise entrée dans un mois clos ne change plus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| D4 | `date_cloture` renseignée et au moins une date d'entrée `<= limite` parmi : `entrees_en_plus` (ce qu'un rattachement ferait entrer), les dates des **réceptions** des lignes du dossier, les `entre_le` des **lots** des lignes saisies à la main (sans ligne de réception) | 409 | `f"La marchandise {nom} est entrée le {min(entrees):%d/%m/%Y}, dans la période close jusqu'au {limite:%d/%m/%Y} : son coût a été rendu avec le mois et ne change plus ({geste} refusé). Pour corriger ce mois, la direction rouvre la période (Réglages › Période close jusqu'au — c'est tracé), on saisit, puis elle la referme."` avec `nom` = `f"du dossier {dossier.numero}"` si le dossier a un numéro, sinon `"rattachée"` | `SEC:259-276` |

Décision (commit `f6f3acc`, audit 2-A G5 / 2-G B2) : corriger un mois clos reste possible mais
c'est une décision de la direction, visible : rouvrir la période (tracé), saisir, refermer. Pas
de report « en douce » sur le mois suivant (deux chiffres pour un même mois).

### 0.6 Verrou optimiste par « empreinte »

| Règle | Référence |
|---|---|
| Les fiches **sans colonne `version`** (fournisseur, qualité, réglage d'un métier, montage d'un métier ou d'un étage) portent une **empreinte** : `sha1(json.dumps(parties, sort_keys=True, default=str, ensure_ascii=False))[:16]` (16 caractères hexadécimaux). Le `GET` la renvoie ; une modification qui la renvoie est refusée si la fiche a changé. | `REF:48-51` |
| **Facultative** : sans empreinte envoyée (`None` ou vide), aucun contrôle (le dernier qui écrit gagne). | `REF:54-55` |
| Refus : `lue and lue != actuelle` → **409** `f"{qui} a été modifié(e) entre-temps sur un autre poste : rechargez pour repartir de sa dernière version, puis refaites la modification."` (`qui` ∈ « Ce fournisseur », « Cette qualité », « Ce métier », « Le montage de ce métier », `f"L'étage {etage}"`). | `REF:54-59` |
| La matière (`Article`) a une vraie colonne `version` (voir § 1.5). | `MOD:310` |

### 0.7 Paramètres (réglages) lus par ces quatre domaines

| Clé | Libellé | Défaut | Bornes | Usage | Réf. |
|---|---|---|---|---|---|
| `seuil_approbation` | Approbation des commandes au-delà de | 0 MAD (= jamais) | 0 – 1e12 | garde-fou d'approbation | `PAR:81-82` |
| `toler_in_full` | Tolérance de livraison complète | 2 % | 0 – 20 % | ligne « livrée », reste à livrer nul, solde auto | `PAR:85-88` |
| `toler_ecart_pesee` | Tolérance d'écart de pesée | 2 % | 0 – 100 % | écart affiché sans BL | `PAR:89` |
| `toler_excedent` | Excédent de livraison toléré | 10 % | 0 – 1000 % | borne d'une ligne de bon à la réception | `PAR:90-92` |
| `toler_poids_bobine` | Tolérance du poids de bobine | 5 % | 0 – 100 % | écart pesé/catalogue des fils montés | `PAR:93` |
| `toler_retard_jours` | Retard toléré dans la ponctualité | 0 j | 0 – 60 | état « en retard » d'un bon | `PAR:97-98` |
| `taux_perte` | Taux de perte matière | 2 % | 0 – 50 % | coût au m² (`facteurs-cout`) | `PAR:57-58` |
| `taux_tva_import` | TVA à l'importation | 20 % | 0 – 100 % | TVA attendue | `PAR:107` |
| `taux_tpi_import` | Taxe parafiscale à l'importation (TPI) | 0,25 % | 0 – 10 % | TVA attendue (si pas de poste TPI saisi) | `PAR:108-109` |
| `seuil_surcout_import` | Frais d'un dossier à vérifier au-delà de | 100 % | 5 % – 10 000 % | frais aberrants (C35) | `PAR:110-113` |
| `toler_facture_import` | Facture d'un dossier à rapprocher au-delà de | 2 % | 0 – 100 % | écart facture / marchandise (C36) | `PAR:114-117` |
| `date_cloture` | Période close jusqu'au | vide | — | § 0.5 | `PAR:138-139` |
| `nom_entreprise`, `forme_juridique`, `adresse`, `ville`, `telephone`, `banques`, `ice`, `rc`, `identifiant_fiscal`, `cnss`, `patente`, `secteur` | Société | vides (secteur « Fabrication de tapis mécaniques ») | — | en-tête et pied du bon de commande | `PAR:119-137` |

### 0.8 Mode « classeur » (parité ERP Fil) — règle générale

| Règle | Référence |
|---|---|
| Le moteur garde deux méthodes : `"corrigee"` (Gestion MP) et `"classeur"` (reproduit le tableur / l'ERP Fil à l'identique, pour les essais de parité). Dans Gestion MP en service, **la méthode est forcée à `"corrigee"`** à chaque chargement des réglages : le mode classeur n'est activable que par les essais et l'outil de comparaison. | `CMO:125-137`, `PAR:185` |
| Les branches « classeur » qui touchent la partie A sont relevées domaine par domaine et récapitulées au § 5. | — |

---

## 1. Référentiels

Principe (docstring `REF:1-12`) : ce sont des **données réelles** (exigence M11 : catalogue,
classification, fournisseurs, qualités et recettes sont vrais ; jamais supprimés par un essai) ;
chaque changement est tracé au journal. Qui écrit : la responsable **achats** tient les
matières, la classification et les fournisseurs ; la **direction** tient les rôles de
nomenclature, les qualités, les recettes, le plan, les magasins, le réglage des métiers, les
postes de frais et les codes douaniers ; l'**alimentation** monte les fils sur les métiers.

### 1.1 Données créées d'office au démarrage

| # | Règle | Référence |
|---|---|---|
| R-REF-01 | À chaque démarrage (`initialiser`), ce qui manque est créé, **jamais écrasé** : les 8 rôles de base `ROLES = ("Poil", "Chaîne", "Trame", "Colle", "Cuir", "Franges", "Ruban", "Plastique")`, avec `lineaire = rôle ∈ ROLES_LINEAIRES = ("Cuir", "Franges", "Ruban")` et `ordre` = rang (0…7). | `MAIN:50-58`, `CMO:23-24` |
| R-REF-02 | Les postes de frais de `POSTES_IMPORT` (code : libellé, récupérable) : `DD` Droits de douane (non) ; `TPI` Taxe parafiscale à l'importation (non) ; `TVA` TVA à l'importation (**oui**) ; `PORT` Port Med ; `FRET` Fret ; `ASSUR` Assurance ; `TRANSIT` Transitaire ; `TIMBRE` Timbre ; `INT_OC` Intérêts / ordre de change ; `TMSA` TMSA ; `AUTRE` Autre frais (tous non récupérables). Clé de répartition par défaut : `valeur` (colonne). Un poste ajouté à une base déjà remplie (TPI, ASSUR) **prend sa place** juste après celui qui le précède dans la liste ; les suivants descendent d'un rang. | `MAIN:59-73`, `CMO:518-534`, `MOD:439-450` |
| R-REF-03 | Les devises `MAD` (Dirham, 1,0), `USD` (Dollar américain, 10,0), `EUR` (Euro, 10,8) si absentes. | `MAIN:45`, `MAIN:74-77` |
| R-REF-04 | Un magasin « Magasin principal » (type Stock courant) et un « Quarantaine » (type Quarantaine) : **toujours** un de chaque type — créé si aucun magasin de ce type n'existe (actif ou non) et si le code n'est pas pris. | `MAIN:46`, `MAIN:78-82` |

### 1.2 Classification : lecture

| # | Règle | Référence |
|---|---|---|
| R-REF-05 | Quatre listes : `composition` (table `Composition` : code ≤ 32, libellé, famille, actif, composition détaillée ≤ 160, commentaire), `type_fil` (code ≤ 32, libellé, actif, commentaire), `titrage` (code ≤ 48, valeur ≤ 32, unité ≤ 16, actif, commentaire), `couleur` (code ≤ 64, libellé, famille, actif, commentaire). Le **code est la clé primaire** ; les matières le référencent par clé étrangère `ON UPDATE CASCADE`. | `REF:37-42`, `MOD:168-212`, `MOD:286-292` |
| R-REF-06 | `GET /classification` (tout connecté) : chaque liste triée par code, chaque valeur avec le nombre de matières qui la portent (`articles`), et `roles` : chaque rôle (trié par ordre puis code) avec `lineaire`, `ordre`, le nombre de matières (`articles`), le nombre de qualités qui lui donnent un **poids > 0** (`qualites`), et `de_base` (rôle ∈ ROLES). | `REF:69-99` |

### 1.3 Rôles de nomenclature (direction)

Entrée `RoleEntree` : `code` 1–32 caractères, `lineaire` (défaut faux), `ordre` 0–999 (défaut 0) (`REF:106-109`).

| # | Règle | Référence |
|---|---|---|
| R-REF-07 | Le calcul compte **au mètre linéaire** Cuir, Franges et Ruban, **et eux seuls** (constante du moteur, pas le champ `lineaire`) : un rôle ne peut être déclaré linéaire que s'il est l'un d'eux, et ces trois-là doivent l'être. | `REF:112-119` ; décision écrite `docs/conformite/final-C-referentiels.md` (C6, « linéaire modifiable » ⛔) |
| R-REF-08 | Ajout (`POST /classification/roles`, direction) : code **sans espaces autour** (strip) ; doublon contrôlé **sans tenir compte de la casse**. Journal « ajout rôle de nomenclature », objet `role`, détail = code. Renvoie toute la classification. | `REF:122-132` |
| R-REF-09 | Modification (`PUT /classification/roles/{code}`, direction) : change `lineaire` et `ordre` ; un **renommage** n'est permis que pour un rôle ajouté (pas de base) que ni une matière ni une ligne `QualitePoids` (même à poids 0) ne porte ; il se fait par suppression puis recréation. Journal « modification rôle de nomenclature », détail = code ou `"{ancien} → {nouveau}"`. | `REF:135-162` |
| R-REF-10 | Suppression (`DELETE /classification/roles/{code}`, direction) : pas un rôle de base ; ni matière ni qualité (poids > 0) ne le porte ; les lignes `QualitePoids` à poids 0 de ce rôle sont supprimées avec lui. Journal « suppression rôle de nomenclature ». | `REF:165-181` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-01 | `lineaire != (code in ROLES_LINEAIRES)` (ajout ou modification) | 422 | `f"Le calcul compte au mètre {', '.join(ROLES_LINEAIRES)}, et eux seuls : « {code} » se compte {'au mètre' if code in ROLES_LINEAIRES else 'au poids'}."` | `REF:115-119` |
| X-REF-02 | ajout : un rôle de même code existe (comparaison `lower()`) | 409 | `f"Le rôle « {code} » existe déjà."` | `REF:126-127` |
| X-REF-03 | modification/suppression : rôle inconnu | 404 | `"Rôle introuvable."` | `REF:139-140`, `REF:169-170` |
| X-REF-04 | renommage d'un rôle de base | 409 | `f"« {code} » est un rôle de base du calcul : il garde son nom."` | `REF:143-144` |
| X-REF-05 | renommage d'un rôle porté par une matière ou par une ligne `QualitePoids` (quel que soit le poids) | 409 | `f"« {code} » est porté par des matières ou des qualités : il garde son nom."` | `REF:145-149` |
| X-REF-06 | renommage vers un code existant (comparaison **exacte**, sensible à la casse) | 409 | `f"Le rôle « {nouveau} » existe déjà."` | `REF:150-151` |
| X-REF-07 | suppression d'un rôle de base | 409 | `f"« {code} » est un rôle de base du calcul : il ne se supprime pas."` | `REF:171-172` |
| X-REF-08 | suppression d'un rôle porté (matières > 0 ou qualités à poids > 0) | 409 | `f"« {code} » est porté par {usage['articles']} matière(s) et {usage['qualites']} qualité(s) : les changer d'abord."` | `REF:173-176` |

### 1.4 Valeurs de classification (achats)

Entrée `ValeurClassification` : `code` 1–64, `libelle` ≤ 120, `famille` ≤ 64, `valeur` ≤ 32,
`unite` ≤ 16, `composition_detaillee` ≤ 160, `commentaire` ≤ 500, `actif` (défaut vrai) ;
seuls les champs que la table possède sont écrits (`REF:184-192`, `REF:210`).

| # | Règle | Référence |
|---|---|---|
| R-REF-11 | `{nom}` ∈ {`composition`, `type_fil`, `titrage`, `couleur`} ; sinon 404 (X-REF-09). Les routes des rôles sont déclarées **avant** ces routes génériques (sinon `roles` serait pris pour une liste). | `REF:102-103`, `REF:195-198` |
| R-REF-12 | Ajout (`POST /classification/{nom}`) : code strip ; **titrage** : si `valeur` est vide, le code se coupe au premier espace en `valeur` et `unite` (« 2900 Dtex » → 2900 / Dtex ; l'unité envoyée est alors écrasée). Doublon = clé primaire **exacte** (sensible à la casse). Journal `f"ajout {libellé en minuscules}"` (« ajout composition », « ajout type de fil »…), objet = nom de la liste, détail = code. | `REF:201-215` |
| R-REF-13 | Modification (`PUT /classification/{nom}/{code}`) : **remplace** tous les champs (un champ absent reprend sa valeur par défaut, p. ex. commentaire vidé) ; le **code lui-même se corrige** : les matières suivent (`ON UPDATE CASCADE`). Journal `f"modification {libellé}"`, détail `f"{code} → {x.code}"` (même si inchangé). | `REF:218-234` |
| R-REF-14 | Suppression (`DELETE /classification/{nom}/{code}`) : seulement si **aucune matière** ne porte la valeur ; sinon on reclasse ou on **désactive** (exigence M23). Journal `f"suppression {libellé}"`. | `REF:237-255`, `docs/EXIGENCES-MOHAMED.md` M23 |
| R-REF-15 | Une valeur **désactivée** reste utilisable par une matière : `_verifier_article` ne contrôle que l'existence, pas `actif` (l'écran seul en tient compte). | `REF:574-579` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-09 | `nom` hors des quatre listes | 404 | `"Liste inconnue."` | `REF:196-197` |
| X-REF-10 | ajout : le code existe | 409 | `f"« {code} » existe déjà."` | `REF:208-209` |
| X-REF-11 | modification/suppression : valeur inconnue | 404 | `"Valeur introuvable."` | `REF:223-224`, `REF:242-243` |
| X-REF-12 | modification : le nouveau code (strip) existe déjà | 409 | `f"« {e.code} » existe déjà."` (code **non** nettoyé dans le message) | `REF:228-230` |
| X-REF-13 | suppression d'une valeur portée par `portes` matières | 409 | `f"« {code} » est porté par {portes} matière(s) : les reclasser d'abord, ou désactiver la valeur."` | `REF:244-251` |

### 1.5 Fournisseurs (achats)

Entrée `FournisseurEntree` (`REF:261-279`) : `nom` 2–160 (obligatoire) ; `code` ≤ 32 ; `pays` ≤ 80 ;
`contact` ≤ 120 ; `telephone` ≤ 60 ; `email` ≤ 160 (aucun contrôle de forme) ; `devise` ≤ 3
(défaut MAD) ; `delai_jours` > 0 et ≤ 730 (défaut **60**) ; `couverture_commande_jours` 0–730
(défaut 0 = réglage général) ; `mode_paiement` ≤ 40 ; `delai_paiement_jours` 0–730 (défaut 0) ;
`conditions_paiement` ≤ 160 ; `incoterm` ≤ 20 ; `port_chargement` ≤ 80 ; `banque` ≤ 120 ;
`notes` ≤ 2000 ; `actif` (défaut vrai) ; `empreinte`. Base : `nom` unique ; contraintes
`delai_jours > 0`, `couverture_commande_jours >= 0`, `delai_paiement_jours >= 0` (`MOD:225-249`).

| # | Règle | Référence |
|---|---|---|
| R-REF-16 | Normalisation : `devise` en **majuscules**, doit exister dans la table des devises ; `nom`, `code`, `pays`, `contact`, `telephone`, `email`, `port_chargement`, `banque` **strip** ; `pays` en **MAJUSCULES, espaces multiples réduits à un** (« un pays s'écrit d'une seule façon, comme la reprise l'a écrit : TURKEY, MAROC, INDE… »). | `REF:351-365` ; commit `2010f4f` (« pays en liste ») ; essai `test_un_pays_s_ecrit_d_une_seule_facon` |
| R-REF-17 | Unicité du nom **sans tenir compte de la casse** (après strip), à la création comme à la modification (hors la fiche elle-même). | `REF:371-372`, `REF:388-391` |
| R-REF-18 | Création (`POST /fournisseurs`) : journal « création fournisseur », objet `fournisseur`, détail = nom. Modification (`PUT /fournisseurs/{fid}`) : **sous verrou de ligne** (`with_for_update`), empreinte contrôlée (§ 0.6, sur les 19 champs de `CHAMPS_FOURNISSEUR`), remplacement de tous les champs ; journal « modification fournisseur ». | `REF:282-286`, `REF:368-396` |
| R-REF-19 | Suppression (`DELETE /fournisseurs/{fid}`) : refusée dès qu'il a des matières, des commandes, des réceptions, des lots, des opérations, des factures (« le désactiver plutôt ») ou des **pièces jointes** (« les retirer d'abord »). Journal « suppression fournisseur ». | `REF:399-421` |
| R-REF-20 | Lecture (`GET /fournisseurs`, tout connecté), triée par nom. Calculés : `local` = pays (strip, majuscules) ∈ {« MAROC », « MOROCCO », « » } ; `devises` = nombre de matières par devise ; `articles`, `commandes`, `receptions`, `pieces` (comptes) ; **délai mesuré** `delai_mesure_jours` = moyenne, arrondie au dixième, de `max(0, date de réception − date de commande)` en jours, sur les réceptions **validées** des **365 derniers jours** liées à une ligne de bon (un couple réception/bon distinct compte une fois) ; `livraisons_mesurees` = nombre de mesures ; `None` sans mesure. | `REF:289-348` ; essai `test_delai_mesure` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-14 | devise (majuscules) absente de la table | 422 | `f"Devise inconnue : « {code} ». L'ajouter d'abord (Réglages › Devises)."` | `REF:352-354` |
| X-REF-15 | un autre fournisseur porte ce nom (casse ignorée) | 409 | `f"Le fournisseur « {e.nom.strip()} » existe déjà."` | `REF:371-372`, `REF:390-391` |
| X-REF-16 | modification/suppression : fournisseur inconnu | 404 | `"Fournisseur introuvable."` | `REF:385-386`, `REF:403-404` |
| X-REF-17 | modification : empreinte périmée | 409 | § 0.6 avec `qui = "Ce fournisseur"` | `REF:387` |
| X-REF-18 | suppression : au moins une ligne dans `Article`, `Commande`, `Reception`, `Lot`, `Operation` ou `Facture` pour ce fournisseur (testés dans cet ordre) | 409 | `f"« {f.nom} » a {quoi} : le désactiver plutôt que le supprimer."` avec `quoi` ∈ « des matières du catalogue », « des commandes », « des réceptions », « des lots », « des opérations », « des factures » | `REF:405-414` |
| X-REF-19 | suppression : pièces jointes (`objet = "fournisseur"`) | 409 | `f"« {f.nom} » a des pièces jointes : les retirer d'abord, ou le désactiver."` | `REF:415-417` |

### 1.6 Matières (catalogue)

#### 1.6.1 Le modèle et ses notions

| # | Règle | Référence |
|---|---|---|
| R-REF-21 | Champs (`Article`) : `reference` (unique, ≤ 160, le nom lisible), `designation`, `role` (FK rôle, obligatoire), `composition` / `type_fil` / `titrage` / `couleur` (FK facultatives `ON UPDATE CASCADE`), `couleur_code` (code teinturier), `unite` (**toujours « kg »**, contrainte `ck_article_unite_kg`), `unite_prix` (« kg » ou « ml », défaut kg), `densite` (kg par mètre linéaire, défaut 0), `fournisseur_id`, `prix` (≥ 0), `devise` (FK, défaut MAD), `unite_achat` (défaut « kg »), `contenance_achat` (kg par unité, défaut 1), `minimum_commande`, `poids_bobine` (kg/bobine du catalogue), `bobines_palette`, `stock_min`, `couv_min_mois`, `groupe_equiv`, `priorite_equiv` (facultatif), `actif`, `version` (défaut 1), `modifie_le`, `modifie_par`, `code_douanier` (FK `ON UPDATE CASCADE`). Contraintes base : `prix >= 0` ; `unite_prix IN ('kg','ml')` ; `unite_prix = 'kg' OR densite > 0` ; `stock_min, poids_bobine, bobines_palette >= 0` ; `contenance_achat, minimum_commande >= 0`. | `MOD:266-313` |
| R-REF-22 | **Stock toujours en kilos**, cuir, franges et ruban compris (décision de Mohamed du 8 octobre 2026) ; le **prix** se saisit au kilo (défaut) ou **au mètre** (`unite_prix = "ml"`) et se ramène au kilo par la densité : `prix_kg = prix / densite` si `ml` (0 si densité nulle), sinon `prix`. C'est `prix_kg` que lisent valeur du stock, coût au m², budget, commandes et réceptions. | `MOD:314-321` ; commits `d2e1e39`, `b75bc24` ; `docs/AUDIT-2026-10-08.md` (bloquant n° 1) |
| R-REF-23 | `kg_par_ml` = densité si le rôle est linéaire (Cuir, Franges, Ruban), 0 sinon : les kilos d'un cuir, de franges, d'un ruban se lisent **aussi en mètres, à titre indicatif** (kilos ÷ densité). | `MOD:323-327`, `REF:480` |
| R-REF-24 | **Unité de stock figée** : notion **abandonnée**. Elle avait été figée dès le premier mouvement (commit `f6f3acc`), puis supprimée quand le stock est passé tout en kilos (commit `d2e1e39` : « L'unité de stock ne se fige plus » ; étape de schéma 14 convertit les matières tenues en « ml » : quantités × densité, prix ÷ densité, montants inchangés). L'ancienne colonne « Unité » du tableur n'est plus lue. | `MOD:272-274`, `SUI:690-692` |
| R-REF-25 | **Conditionnement** (unité dans laquelle la matière se commande) : si `unite_achat` ≠ « kg » et `contenance_achat` > 0 → cette unité, **déclarée** ; sinon **déduit** comme le plan d'achat : « Palette » de `poids_bobine × bobines_palette` kg si les deux sont connus, sinon « Bobine » de `poids_bobine` kg, sinon « kg » (contenance 1). | `REF:456-468` ; décision « unité d'achat vide = déduite » (`final-C`) |

#### 1.6.2 Lecture

| # | Règle | Référence |
|---|---|---|
| R-REF-26 | `GET /articles` (tout connecté) : **tout le catalogue** (l'écran filtre et cherche à la frappe, sans aller-retour), trié par référence ; chaque matière avec son stock (somme des soldes de ses lots, **tous magasins dont la quarantaine**), `titrage_unite`, `kg_par_ml`, `fournisseur` (nom), `prix_kg`, `conditionnement`, `contenance_palette`, `historique` / `historique_raison` (ce qui empêche la suppression, § 1.6.5), `modifie_par`, `modifie_le` (à la minute). | `REF:471-497`, `REF:544-563` |
| R-REF-27 | **Sans prix pour l'alimentation** : `prix` et `prix_kg` à `null` — le serveur les retire, pas seulement le menu. | `REF:539-541`, `REF:560-562` ; commit `2010f4f` ; essai `test_l_alimentation_ne_voit_aucun_prix` |

#### 1.6.3 Vérifications communes à la création et à la modification (`_verifier_article`)

Entrée `ArticleEntree` (`REF:427-453`) : `version` ; `reference` 2–160 ; `designation` ≤ 160 ;
`role` ≤ 32 ; `composition` ≤ 32 ; `type_fil` ≤ 32 ; `titrage` ≤ 48 ; `couleur` ≤ 64 ;
`couleur_code` ≤ 32 ; `unite_prix` ≤ 4 (défaut kg) ; `densite` 0–1000 ; `fournisseur_id` ;
`prix` 0–1e7 ; `devise` (défaut MAD) ; `unite_achat` ≤ 32 (défaut kg) ; `contenance_achat`
0–1e7 (défaut 1) ; `minimum_commande` 0–1e9 ; `poids_bobine` 0–1000 ; `bobines_palette`
0–10 000 ; `stock_min` 0–1e9 ; `couv_min_mois` 0–60 ; `groupe_equiv` ≤ 64 ; `priorite_equiv`
0–100 ou vide ; `code_douanier` ≤ 20 ; `actif` (défaut vrai).

| # | Règle | Référence |
|---|---|---|
| R-REF-28 | Une liste de classification laissée sur « — » envoie un texte vide : c'est « **aucune valeur** » (`None`), pas une valeur inconnue. | `REF:567-571` ; commit `d8882d4` |
| R-REF-29 | Ordre des contrôles : rôle connu → chaque valeur de classification connue → `unite_prix` ∈ {kg, ml} → densité obligatoire pour un rôle linéaire → densité obligatoire pour un prix au mètre → **matière en service ⇒ fournisseur** (contrôle C05) → fournisseur existant → devise (majuscules, connue) → `unite_achat` (strip, vide ⇒ « kg ») ≠ « ml » → unité ≠ kg ⇒ contenance > 0 → unité kg ⇒ **contenance forcée à 1** → code douanier (strip, vide ⇒ `None`) connu. | `REF:566-604` |
| R-REF-30 | Un cuir, des franges, un ruban (rôle linéaire) **ont besoin de leur densité** (kg/ml) : la recette les compte au mètre, le stock en kilos. Un prix au mètre aussi. « ml » n'est **plus** une unité d'achat : la commande se compte en kilos (ou en palettes, fûts… de tant de kilos) ; un fournisseur qui facture au mètre se règle par « prix au mètre ». | `REF:582-596` ; commit `d2e1e39` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-20 | rôle absent de `RoleNomenclature` | 422 | `f"Rôle inconnu : « {e.role} »."` | `REF:572-573` |
| X-REF-21 | composition / type de fil / titrage / couleur non vide et absente de sa table | 422 | `f"{TABLES_CLASSIFICATION[nom][2]} inconnue : « {valeur} ». L'ajouter d'abord dans la classification."` (libellé : « Composition », « Type de fil », « Titrage », « Couleur » — donc « Type de fil inconnue », « Titrage inconnue » tels quels) | `REF:574-579` |
| X-REF-22 | `unite_prix` ∉ {kg, ml} | 422 | `"Unité du prix : au kilo (kg) ou au mètre (ml)."` | `REF:580-581` |
| X-REF-23 | rôle linéaire et densité nulle | 422 | `f"Une matière du rôle {e.role} (cuir, franges, ruban : comptés au mètre dans les recettes) a besoin de sa densité (kg/ml) : le stock est en kilos."` | `REF:582-584` |
| X-REF-24 | `unite_prix == "ml"` et densité nulle | 422 | `"Un prix au mètre a besoin de la densité (kg/ml) pour se ramener au kilo."` | `REF:585-586` |
| X-REF-25 | `actif` et pas de fournisseur | 422 | `"Une matière en service a un fournisseur : sans lui, le plan d'achat ne sait pas à qui la commander (contrôle C05)."` | `REF:587-589` |
| X-REF-26 | `fournisseur_id` inconnu | 422 | `"Fournisseur inconnu."` | `REF:590-591` |
| X-REF-27 | devise inconnue | 422 | voir X-REF-14 | `REF:592` |
| X-REF-28 | `unite_achat == "ml"` | 422 | `"La commande se compte en kilos (ou en palettes, fûts… de tant de kilos). Un fournisseur qui facture au mètre : choisir le prix « au mètre »."` | `REF:594-596` |
| X-REF-29 | `unite_achat != "kg"` et `contenance_achat` nulle | 422 | `"Une unité d'achat autre que le kilo a besoin de sa contenance (kg par unité)."` | `REF:597-598` |
| X-REF-30 | code douanier non vide et absent | 422 | `f"Code douanier inconnu : « {e.code_douanier} ». L'ajouter d'abord (Réglages › Codes douaniers)."` | `REF:601-604` |

#### 1.6.4 Création et modification

| # | Règle | Référence |
|---|---|---|
| R-REF-31 | Création (`POST /articles`, achats) : référence **strip**, unique **exacte** (sensible à la casse) ; `modifie_le = maintenant`, `modifie_par = nom`, `version = 1` ; journal « création matière », objet `article`, détail = référence ; renvoie la fiche avec stock 0. La désignation n'est pas nettoyée. | `REF:607-620` |
| R-REF-32 | Modification (`PUT /articles/{aid}`, achats) : **verrou de ligne** sur l'article ; **verrou optimiste** : si `version` est envoyée et diffère → refus ; tous les champs sont **remplacés** (PUT complet) ; `version += 1` ; `modifie_le`, `modifie_par` ; journal « modification matière », détail = référence ou `"{avant} → {après}"` si renommée. | `REF:623-653` |
| R-REF-33 | Aucun garde sur l'**historique** à la modification : rôle, devise, fournisseur, unité du prix, densité, `actif` se changent même si la matière a du stock, des bons ouverts, des recettes ou des fils montés (voir § 6). | `REF:623-653` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-31 | création/modification : une autre matière a la même référence (strip) | 409 | `f"La matière « {e.reference.strip()} » existe déjà."` | `REF:611-612`, `REF:636-639` |
| X-REF-32 | modification/suppression : matière inconnue | 404 | `"Matière introuvable."` | `REF:627-628`, `REF:660-661` |
| X-REF-33 | modification : `version` envoyée ≠ version en base | 409 | `f"Cette fiche a été modifiée entre-temps par {a.modifie_par or 'un autre poste'} : rechargez-la pour repartir de sa dernière version, puis refaites la modification."` | `REF:629-634` |

#### 1.6.5 Suppression d'une matière

| # | Règle | Référence |
|---|---|---|
| R-REF-34 | Une matière ne se supprime que si elle n'a **aucune trace** : mouvements de stock, lots (en stock ou passés), lignes de commande, de réception, d'ordre de fabrication (`BonLigne`), d'opération (brouillons compris), de dossier d'importation, recettes, fils montés, **pièces jointes** (`objet = "article"`). La première trace trouvée (dans cet ordre) fait la raison. Journal « suppression matière ». | `REF:501-528`, `REF:656-668` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-34 | trace dans les recettes, les fils montés ou les pièces jointes | 409 | `f"« {reference} » figure dans {quoi} : l'en retirer d'abord, ou désactiver la matière."` (`quoi` ∈ « des recettes », « des fils montés sur les métiers », « des pièces jointes ») | `REF:531-534` |
| X-REF-35 | toute autre trace | 409 | `f"« {reference} » figure dans {quoi} : elle appartient à l'historique. La désactiver plutôt que la supprimer."` (`quoi` ∈ « des mouvements de stock », « des lots en stock ou passés », « des commandes », « des réceptions », « des ordres de fabrication », « des opérations (brouillons compris) », « des dossiers d'importation ») | `REF:535-536` |

#### 1.6.6 Classement automatique du catalogue (`POST /catalogue/classer?appliquer=`, achats)

| # | Règle | Référence |
|---|---|---|
| R-REF-35 | Lit chaque référence et **en déduit** composition, type de fil, titrage, couleur, code couleur (`classification.decomposer`, § 1.6.7). Sans `appliquer` (défaut faux) : **rien n'est écrit**, l'écran montre d'abord ce qui serait déduit. | `REF:680-686` |
| R-REF-36 | **Une valeur déjà renseignée n'est jamais écrasée** : la lecture comble les vides, elle ne corrige pas un choix humain. | `REF:685-686`, `REF:702-711` |
| R-REF-37 | La « nature » passée au décodeur est le **libellé** de la composition déjà portée par la matière (s'il y en a une). | `REF:694-695` |
| R-REF-38 | La couleur se prend de la **désignation** quand elle existe : désignation sans ce qui est entre parenthèses, strip, si non vide et ≤ 40 caractères (« la désignation dit la couleur comme l'atelier la nomme — Gris Claire —, la référence comme le fournisseur l'écrit — Grey — : on garde l'atelier »). | `REF:696-700` |
| R-REF-39 | Normalisation des valeurs proposées : composition et type en **MAJUSCULES** ; titrage = `titrage_complet` (« 2900 Dtex ») ; couleur et code couleur tels quels. | `REF:702-711` |
| R-REF-40 | Les valeurs de classification inconnues sont **à créer** : composition → libellé et famille de la table `COMPOSITIONS` (à défaut libellé = code, famille « Autre ») ; type → libellé de `TYPES_CONNUS` (à défaut le code) ; titrage → `valeur` et `unite` lues ; couleur → libellé = code. | `REF:715-726`, `CLA:177-179` |
| R-REF-41 | Avec `appliquer` : chaque matière complétée prend les valeurs, `version + 1`, `modifie_le`, `modifie_par` ; les valeurs à créer sont créées ; **un seul** journal « classement du catalogue », objet `article`, détail `f"{n} matière(s) complétée(s)"`. Réponse : `appliquer`, `propositions` (id, référence, champs changés), `a_creer` (codes triés par liste). | `REF:727-741` ; essai `test_classer_le_catalogue_lit_les_references` |

#### 1.6.7 Décodage et composition d'une référence (`CLA`)

Forme d'une référence : `PP FRZ-2900 Dtex-Gold 3423-Hs` = composition, type, titrage, unité,
libellé de couleur, code couleur du fournisseur, suffixe du fournisseur (`CLA:6-13`).
Exigences M21, M22 : référence = composition + type + titrage + couleur, saisie semi-automatique
qui reste modifiable (« la règle n'est pas la loi, un fournisseur peut imposer son propre code »).

| # | Règle | Référence |
|---|---|---|
| R-REF-42 | Unités de titrage connues, dans cet ordre (« Deniers » avant « Den ») : Dtex, Deniers, Den, Tex, Nm, Nec. Unité par défaut selon la composition : PP → Dtex ; PES et MICRO PES → Deniers. | `CLA:30-36` |
| R-REF-43 | Suffixes du fournisseur (retirés **d'abord**, sinon « …-Hs » passerait pour du heat-set) : HS, OZ, TAT, SUJ, SF, GZM, TURK, TEXT. | `CLA:38-41`, `CLA:210-216` |
| R-REF-44 | Types connus (marqueur → libellé) : FRZ et FRIZE → Frisé ; SH → Shrink (rétractable) ; FDY → Filament continu (FDY) ; BCF → Bouclé continu (BCF) ; VER → Vériné ; HS → Heat-set ; CB → Câblé ; MN → Monofilament ; NYLON → Nylon ; SSL → Ssl. Le type est le **premier marqueur trouvé, du plus long au plus court**, comme mot entier (sans lettre collée) dans le corps en majuscules sans accents. | `CLA:43-56`, `CLA:218-223` |
| R-REF-45 | Compositions (préfixe → libellé, famille) : PP Polypropylène / Synthétique ; PES Polyester / Synthétique ; MICRO PES Micro polyester / Synthétique ; PA Polyamide / Synthétique ; JUTE Jute / Naturel ; LAINE Laine / Naturel ; COTON Coton / Naturel ; SBR SBR (latex) / Intrant ; PLASTIQUE Plastique / Intrant ; SIMILI CUIR Simili cuir / Intrant ; BANDE Bande / Intrant. Composition = d'après la **nature** si elle est donnée (commence par un libellé, sinon par un code, sinon premier mot en majuscules), sinon le **plus long code** par lequel commence la référence (sans accents, majuscules). | `CLA:58-71`, `CLA:161-174`, `CLA:201-208` |
| R-REF-46 | Titrage : premier nombre (décimales `.`/`,`, facteur `*n` ou `xn`, fraction `/n`) suivi ou non d'une unité connue ; espaces retirés autour de `*`, `x`, `/`, et `x` → `*` (« 1750 x 2 » → « 1750*2 ») ; unité : « den… » → **Deniers**, sinon casse titre (Dtex, Nm, Tex, Nec) ; sans unité : « / » présent → **Nm** (20/2, 12/1 : numéro métrique), sinon l'unité par défaut de la composition. | `CLA:182-186`, `CLA:225-238` |
| R-REF-47 | Couleur : ce qui suit le titrage (type et suffixe retirés), découpé sur espaces et tirets ; le mot égal au type est sauté ; un mot **avec chiffre** — ou, une fois le libellé commencé, un mot qui n'est pas du vocabulaire des couleurs — va au **code** ; sinon, tant qu'aucun code n'a commencé, au **libellé**. Vocabulaire des couleurs : 51 mots FR/EN (beige, black, bleu… claire, clair), préfixes de nuance « D. », « L. », « Dk. », « Lt. » ignorés. **Rien n'est inventé** : ce qui ne se lit pas reste vide. | `CLA:74-137`, `CLA:240-255` |
| R-REF-48 | Composer (`POST /articles/composer`, tout connecté) : référence = segments non vides joints par « - » : `"COMPOSITION TYPE"` (majuscules) ; `"titrage unité"` (titrage et unité de la table si le titrage existe, sinon le texte saisi) ; `"couleur code"` (libellé de la couleur, à défaut son code) ; suffixe — sans tiret orphelin. Réponse : `reference`, `existe` (une matière porte déjà cette référence exacte), `designation` = `"couleur (code)"`. | `REF:744-757`, `CLA:258-281` |

#### 1.6.8 Import du tableur des matières (`SUI`)

| # | Règle | Référence |
|---|---|---|
| R-REF-49 | `GET /import/matieres/modele` (achats) : le **catalogue actuel** en tableur (feuille « Matières », fichier `matieres.xlsx`), colonnes dans l'ordre : Référence, Désignation, Rôle, Composition, Type de fil, Titrage, Couleur, Code couleur, Densité, Fournisseur (nom), Prix, Unité du prix, Devise, Unité d'achat, Contenance, Minimum de commande, kg / bobine, Bobines par palette, Stock minimum, Couverture minimum (mois), Groupe d'équivalence, Code douanier, En service (« oui »/« non »), puis la colonne **« Se commande en (lecture seule) »** (jamais relue) : unité seule si contenance 1, sinon `f"{unité} de {contenance:g} kg"` + « (déduit) » si déduite. | `SUI:679-699`, `SUI:701-731` ; commit `71ad13e` |
| R-REF-50 | `POST /import/matieres?appliquer=` (achats, fichier `multipart`) : sans `appliquer`, **aperçu** (rien n'est écrit) ; avec, tout ou rien. Une matière **absente du tableur n'est jamais supprimée**. | `SUI:734-738` ; cahier § 10 |
| R-REF-51 | En-têtes : lus sur la 1re ligne (strip) ; l'ancien intitulé « Poids d'une bobine » est lu comme « kg / bobine » (un tableur téléchargé avant reste importable) ; l'ancienne colonne « Unité » (unité de stock) n'est plus lue ; colonnes facultatives sauf « Référence ». | `SUI:690-693`, `SUI:745-749` |
| R-REF-52 | Par ligne (à partir de la 2e ; une ligne sans référence est ignorée) : cellule vide ou `None` = **inchangé** ; numériques (densité, prix, contenance, minimum, kg/bobine, bobines/palette, stock min, couverture) lus avec la virgule décimale acceptée ; fournisseur par **nom, casse ignorée** ; « En service » vrai si `oui`, `1`, `vrai`, `true` ou `x` (casse ignorée), faux sinon ; composition, type, titrage, couleur, rôle, devise, code douanier : texte (strip) qui doit exister **exactement** ; unité du prix en minuscules ∈ {kg, ml} ; autres champs : texte strip. | `SUI:752-791` |
| R-REF-53 | Contrôles sur la fiche **telle qu'elle serait après l'import** (fiche existante + valeurs du tableur, pour actif, fournisseur, unité du prix, densité, rôle, unité d'achat) — « les mêmes règles qu'à l'écran » : en service ⇒ fournisseur (matière existante) ; prix au mètre ⇒ densité ; rôle linéaire ⇒ densité ; unité d'achat ≠ « ml » ; matière **nouvelle** ⇒ rôle **et** fournisseur (même désactivée). | `SUI:792-808` |
| R-REF-54 | Rapport : `creees` (références), `modifiees` (référence, champs triés, détail `{champ, avant, apres}`), `inchangees` (nombre), `erreurs` (n° de ligne, référence, problèmes). Avec `appliquer` et sans erreur : création (`modifie_par`, `modifie_le`), modification des seuls champs changés (`version + 1`, `modifie_le`, `modifie_par`), **un** journal « import des matières », objet `article`, détail `f"{n} créée(s), {m} modifiée(s)"`. | `SUI:809-835` |

Refus et problèmes signalés :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-36 | le fichier ne s'ouvre pas avec openpyxl | 422 | `f"Tableur illisible : {exc}"` | `SUI:741-744` |
| X-REF-37 | pas de colonne « Référence » | 422 | `"La colonne « Référence » est obligatoire (télécharger le modèle)."` | `SUI:748-749` |
| X-REF-38 | `appliquer` et au moins une ligne en erreur (rien n'est écrit) | 422 | `f"{len(rapport['erreurs'])} ligne(s) en erreur : corriger le tableur d'abord, rien n'a été écrit."` | `SUI:829-831` |
| P-REF-01 | problème de ligne : nombre illisible | (rapport) | `f"{champ} n'est pas un nombre"` (nom technique du champ) | `SUI:768-771` |
| P-REF-02 | fournisseur inconnu | (rapport) | `f"fournisseur inconnu « {v} »"` | `SUI:772-776` |
| P-REF-03 | valeur de classification / rôle / devise / code douanier inconnu | (rapport) | `f"{champ} inconnu « {texte} » (l'ajouter d'abord à la classification)"` | `SUI:779-783` |
| P-REF-04 | unité du prix ∉ {kg, ml} | (rapport) | `"unité du prix : kg ou ml"` | `SUI:784-788` |
| P-REF-05 | matière existante en service sans fournisseur | (rapport) | `"une matière en service a un fournisseur"` | `SUI:796-797` |
| P-REF-06 | prix au mètre sans densité | (rapport) | `"un prix au mètre a besoin de la densité (kg par mètre)"` | `SUI:798-799` |
| P-REF-07 | rôle linéaire sans densité | (rapport) | `f"une matière du rôle {apres['role']} a besoin de sa densité (kg par mètre) : la recette la compte en mètres, le stock en kilos"` | `SUI:800-802` |
| P-REF-08 | unité d'achat « ml » | (rapport) | `"la commande se compte en kilos : un prix au mètre se dit dans « Unité du prix »"` | `SUI:803-804` |
| P-REF-09 | matière nouvelle sans rôle | (rapport) | `"une matière nouvelle a besoin de son rôle"` | `SUI:805-806` |
| P-REF-10 | matière nouvelle sans fournisseur | (rapport) | `"une matière nouvelle a besoin de son fournisseur"` | `SUI:807-808` |

### 1.7 Qualités (direction)

Modèle : `Qualite` (code unique ≤ 32, nom, `base_mensuelle` m²/mois, actif), `QualitePoids`
(une ligne par (qualité, rôle), `poids >= 0` : **kg/m²**, ou **ml/m²** pour un rôle linéaire),
`QualiteSaison` (mois 1–12 unique, coefficient ≥ 0, défaut 1) (`MOD:330-368`).

| # | Règle | Référence |
|---|---|---|
| R-REF-55 | `GET /qualites` (tout connecté), triée par code : poids par rôle, **saisonnalité sur 12 mois** (1,0 pour un mois sans ligne), recette (nomenclature du moteur : id de la ligne, matière, rôle, nature, désignation, fournisseur, pourcentage, `kg_m2`, `prix_kg`, `ml_m2` pour un rôle linéaire = poids du rôle en ml/m² × part, `densite`, `prix` et `unite_prix` **comme on l'achète**, devise, `cout_m2_mad`), `fabrications` (nombre d'ordres de fabrication), `controle` (contrôle 100 % du moteur), `cout_m2_mad` et `kg_m2` (sommes de la recette), `empreinte`. | `REF:770-824` |
| R-REF-56 | **Sans prix pour l'alimentation** : `cout_m2_mad` de la qualité, et `prix_kg`, `prix`, `unite_prix`, `cout_m2_mad` de chaque ligne à `null`. | `REF:819-822` ; commit `ac615a6` |
| R-REF-57 | `GET /qualites/facteurs-cout` (**achats** ; direction) : de quoi recalculer à la frappe le coût d'une recette en saisie, exactement comme le serveur : coût/m² = kg/m² × prix au kilo × cours de la devise × perte, avec `perte = 1 + taux_perte` (**1,0 en mode classeur**) et `taux` = cours de chaque devise. | `REF:827-835` |
| R-REF-58 | Empreinte d'une qualité = (code, nom, actif, poids triés par rôle, recette triée (article, pourcentage)) — **ni la base mensuelle ni la saisonnalité**. | `REF:763-767` |
| R-REF-59 | Création (`POST /qualites`) : code et nom **strip** ; code unique exact ; poids écrits (`_poids`) ; journal « création qualité », objet `qualite`, détail = code ; renvoie `id` et `empreinte`. Base mensuelle 0, pas de saisonnalité (1,0 lu partout). | `REF:838-857` |
| R-REF-60 | `_poids` : chaque rôle cité doit exister, chaque poids ≥ 0 ; un rôle existant est mis à jour, un nouveau créé ; **un rôle non cité garde son poids** (rien n'est supprimé). | `REF:860-872` |
| R-REF-61 | Modification (`PUT /qualites/{qid}`) : **verrou de ligne** ; empreinte ; code unique ; code et nom strip, actif ; poids ; journal « modification qualité » ; puis **version du plan** notée si le plan (base, saisonnalité, **en service**) a changé : journal « plan de production », détail `f"{code} : remise en service"` ou `f"{code} : arrêtée"` + ligne `plan=` JSON `{"avant":…, "apres":…}` (« arrêter une qualité retire son plan des mois à venir, pas du passé »). | `REF:875-892`, `PPL:42-60` ; commit `db25831` |
| R-REF-62 | Après modification, **avertissement** (pas un refus) si des rôles ont un poids > 0 sans aucune matière de la recette (à pourcentage > 0) : `"Rôle(s) avec un poids au m² mais sans matière dans la recette : " + rôles + ". Les besoins et la sortie vers les machines ne les comptent pas tant que la recette ne les nomme pas."` | `REF:893-907` |
| R-REF-63 | Suppression (`DELETE /qualites/{qid}`) : refusée si un **ordre de fabrication** l'a tissée (« elle appartient à l'historique ») ; sinon ses lignes de recette sont supprimées, puis la qualité (poids, saisonnalité et versions suivent en cascade). Journal « suppression qualité ». | `REF:910-925`, `MOD:1031` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-39 | création/modification : code déjà pris (strip, exact) | 409 | `f"La qualité « {e.code.strip()} » existe déjà."` | `REF:849-850`, `REF:882-883` |
| X-REF-40 | qualité inconnue (modification, suppression, recette, version, plan) | 404 | `"Qualité introuvable."` | `REF:879-880`, `REF:914-915`, `REF:941-942`, `REF:997-998`, `REF:1038-1039` |
| X-REF-41 | empreinte périmée (modification, recette, restauration) | 409 | § 0.6 avec `qui = "Cette qualité"` | `REF:881`, `REF:943`, `REF:1002` |
| X-REF-42 | poids d'un rôle inconnu | 422 | `f"Rôle inconnu : « {role} »."` | `REF:863-864` |
| X-REF-43 | poids négatif | 422 | `"Un poids au m² ne peut pas être négatif."` | `REF:865-866` |
| X-REF-44 | suppression d'une qualité tissée par `n` ordres | 409 | `f"« {q.code} » a été fabriquée par {n} ordre(s) : elle appartient à l'historique. La désactiver plutôt que la supprimer."` | `REF:916-920` |

### 1.8 Recettes et versions de recette (direction)

| # | Règle | Référence |
|---|---|---|
| R-REF-64 | `PUT /qualites/{qid}/recette?empreinte=&motif=` (corps : liste `{article_id, pourcentage 0–100}`) : **verrou de ligne** sur la qualité, empreinte, puis **remplace** toute la recette. Journal « recette », objet `qualite`, détail `f"{code} : {n} ligne(s)"` + `f" — {motif}"` si un motif (≤ 300) est donné. | `REF:928-948` |
| R-REF-65 | Vérifications (`remplacer_recette`) : chaque matière existe ; une matière **une seule fois** ; dans **chaque rôle utilisé** (lignes à pourcentage > 0), la somme fait **100 % à 0,01 point près** (`TOLERANCE_RECETTE = 0.01`, la même que le contrôle C01 : « une recette que l'enregistrement accepte, le contrôle ne la déclare pas bloquante le lendemain ») ; **aucun rôle qui pèse dans le m² (poids > 0) sans matière** (« ses kilos disparaîtraient des besoins, du coût et de la sortie vers les machines, sans que rien ne le dise »). Une ligne à 0 % est gardée mais ne compte pas. | `REF:951-984`, `MOT:421-424` ; cahier § 5.1 (« la règle des 100 % bloque l'enregistrement ») ; commits `202d1a0`, `db25831`, `e44613f` |
| R-REF-66 | Un fil sert **plusieurs qualités** (exigence M25) : unicité (qualité, matière) seulement. | `MOD:375-379` |
| R-REF-67 | **Version automatique** : à chaque validation de transaction (`before_commit`), toute qualité dont une ligne `Recette` ou `QualitePoids` a été créée, modifiée ou supprimée — ou dont la collection de poids a changé — reçoit une `RecetteVersion` : `quand` (maintenant), `par` (auteur de la dernière ligne de journal de la transaction), `contenu` = JSON `[{reference, role, pourcentage}]` trié par rôle, `poids` = JSON `{rôle: poids}`. Une qualité supprimée n'en reçoit pas. Vaut pour **tous** les chemins (recette, fiche, restauration, import…). | `SUI:441-476`, `MOD:1025-1038` ; commit `db25831` (« un poids au m² changé crée une version de recette, poids compris ») |
| R-REF-68 | `GET /qualites/{qid}/versions` (tout connecté) : versions de la plus récente à la plus ancienne (`id`, `quand` à la minute, `par`, `lignes`, `poids` ou `null` pour une version d'avant qu'on garde les poids). | `SUI:479-486` |
| R-REF-69 | **Restaurer une version** (`POST /qualites/{qid}/versions/{vid}/restaurer?motif=&empreinte=`, direction) : **motif obligatoire** (1–300) ; revient **d'un bloc** aux parts **et** aux poids au m² de la version (« remettre les parts d'alors sur les poids d'aujourd'hui donnait une recette qui n'a jamais existé ») ; une version sans poids prend ceux de la **version suivante** qui les a, à défaut ceux d'aujourd'hui ; un rôle ajouté depuis revient à **0** ; les mêmes vérifications que R-REF-65 s'appliquent ; une **seule** version nouvelle naît, signée. Journal « recette », détail `f"{code} : retour à la version du {quand:%d/%m/%Y %H:%M} — {motif}"`. Renvoie l'empreinte et les poids. | `REF:987-1026` ; commits `202d1a0`, `2010f4f` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-45 | une ligne vise une matière inconnue | 422 | `"Matière inconnue dans la recette."` | `REF:958-959` |
| X-REF-46 | la même matière deux fois | 422 | `f"« {a.reference} » figure deux fois dans la recette."` | `REF:960-961` |
| X-REF-47 | un rôle dont la somme s'écarte de 100 de plus de 0,01 | 422 | `"Dans chaque rôle, la recette doit faire 100 % : " + ", ".join(f"{r} {t:g} %" …) + "."` (rôles triés) | `REF:967-970` |
| X-REF-48 | un ou plusieurs rôles à poids > 0 sans matière | 422 | un rôle : `"La recette oublie le rôle {r} ({poids:g} au m²) : y mettre ses matières, ou ramener son poids au m² à 0 dans la fiche."` ; plusieurs : `"La recette oublie les rôles {r1} ({p1:g} au m²), {r2} (…) : y mettre leurs matières, ou ramener leur poids au m² à 0 dans la fiche."` | `REF:973-981` |
| X-REF-49 | restauration : version inconnue ou d'une autre qualité | 404 | `"Version introuvable."` | `REF:999-1001` |
| X-REF-50 | restauration : des matières de la version n'existent plus | 409 | `"Ces matières n'existent plus au catalogue : " + ", ".join(manquantes) + ". La version ne peut pas revenir telle quelle."` | `REF:1013-1016` |
| X-REF-51 | restauration : un rôle de la version n'existe plus | 422 | X-REF-42 | `REF:1019` |
| X-REF-52 | restauration sans motif | 422 | Pydantic (`min_length=1`) | `REF:988` |

### 1.9 Plan d'une qualité (direction)

| # | Règle | Référence |
|---|---|---|
| R-REF-70 | `PUT /qualites/{qid}/plan` : `base_mensuelle` 0–1e9 m²/mois, `saisonnalite` **exactement 12** coefficients, chacun **entre 0 et 20** (`COEFFICIENT_MAXI = 20`). Même chemin que le plan de toutes les qualités (`PUT /production/plan`) : base et coefficients écrits, **version du plan tracée** au journal (« plan de production », détail `f"{code} : {base:g} m²/mois"` + `plan=` JSON avant/après) **seulement si quelque chose change** — « le passé reste jugé sur le plan de son époque ». Pas d'empreinte, pas de verrou. | `REF:1029-1046`, `PPL:38-85` ; commit `db25831` |
| X-REF-53 | un coefficient < 0 ou > 20 → **422** `"Un coefficient de saisonnalité reste entre 0 et 20."` | `REF:1040-1041` |

### 1.10 Magasins (direction)

Entrée `MagasinEntree` : `code` 1–64, `nom` ≤ 120, `type` (défaut « Stock courant »),
`contenu` ≤ 120 (ce qu'on y range : « Tout », « Fils PP »…), `actif` (`REF:1052-1057`, `MOD:387-397`).

| # | Règle | Référence |
|---|---|---|
| R-REF-71 | Deux types seulement : « Stock courant » et « Quarantaine » (contrainte base). La quarantaine est **du stock** (comptée, valorisée) mais **non disponible**. | `REF:1072-1073`, `MOD:390`, cahier § 6.6 |
| R-REF-72 | `GET /magasins` (tout connecté) triés par type puis code, avec le stock détenu (somme des soldes). | `REF:1060-1066` |
| R-REF-73 | Création : code strip, unique ; `contenu` strip ; `nom` **non** nettoyé ; journal « création magasin », détail = code tel que saisi. Modification : mêmes règles ; **on ne désactive pas** un magasin qui détient plus d'un gramme (« transférer le stock avant ») ; **on ne change pas le type** d'un magasin qui détient de la matière ; journal « modification magasin ». **Aucune route de suppression.** | `REF:1069-1104` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-54 | type hors des deux | 422 | `"Type de magasin : « Stock courant » ou « Quarantaine »."` | `REF:1072-1073`, `REF:1089-1090` |
| X-REF-55 | code déjà pris | 409 | `f"Le magasin « {e.code.strip()} » existe déjà."` | `REF:1074-1075`, `REF:1091-1092` |
| X-REF-56 | magasin inconnu | 404 | `"Magasin introuvable."` | `REF:1087-1088` |
| X-REF-57 | désactivation (actif → inactif) avec stock > 0,001 kg | 409 | `f"« {g.code} » détient encore {detenu:,.0f} kg : transférer le stock avant de désactiver le magasin."` (séparateur de milliers « , » à l'anglaise) | `REF:1095-1097` |
| X-REF-58 | changement de type avec stock > 0,001 kg | 409 | `"Un magasin qui détient de la matière ne change pas de type."` | `REF:1098-1099` |

### 1.11 Métiers à tisser et montage

Modèle (`MOD:400-431`) : `Metier` (code unique ≤ 32, nom, `laize` m d'un étage — défaut **4,2**,
`densite` **bobines par mètre de laize** — défaut 0, `etages` 1–40 — défaut **6**, actif,
commentaire) ; `FilMonte` (métier, étage ≥ 1, matière, `metres`, `pourcentage` 0–100 — défaut
100, commentaire ≤ 300 ; unique (métier, étage, matière)). Exigences M60, M61 : quatre métiers,
6 ou 8 étages de 4,20 m, poids = mètres × densité × poids de bobine × %.

| # | Règle | Référence |
|---|---|---|
| R-REF-74 | Réglage d'un métier : création et modification (`POST/PUT /metiers`, **direction**) ; code strip, unique ; empreinte sur (code, nom, laize, densité, étages, actif, commentaire) ; journal « création métier » / « réglage métier ». | `REF:1118-1126`, `REF:1144-1145`, `REF:1284-1322` |
| R-REF-75 | On ne ramène pas un métier à moins d'étages que l'étage le plus haut monté ; on ne réduit pas la laize sous la largeur déjà montée d'un étage (largeur = Σ mètres × part / 100 ; laize 0 = pas de limite ; tolérance 1e-6). | `REF:1306-1316` |
| R-REF-76 | Suppression (`DELETE /metiers/{mid}`, direction) : pas de fil monté ; pas nommé par un ordre de fabrication (« L'arrêter plutôt »). Journal « suppression métier ». | `REF:1325-1340` |
| R-REF-77 | Montage complet (`PUT /metiers/{mid}/fils?empreinte=`, **alimentation** ; direction) : **remplace** tout le montage, sous verrou de ligne du métier, empreinte du montage (tous les étages : (étage, matière, mètres arrondis 4 déc., part arrondie 4 déc., commentaire) triés). Commentaires strip. | `REF:1137-1141`, `REF:1397-1417` |
| R-REF-78 | Montage d'**un seul étage** (`PUT /metiers/{mid}/etages/{etage}`, alimentation ; corps `{fils, empreinte}`) : les autres étages ne sont pas touchés ; empreinte **de l'étage** — deux téléphones (ou le téléphone et le bureau) ne s'écrasent pas ; l'étage des fils envoyés est forcé à `{etage}` ; la vérification porte sur les autres étages + le nouveau. | `REF:1129-1134`, `REF:1420-1447` ; décision « montage au téléphone étage par étage » (`final-C`) |
| R-REF-79 | Règles d'un montage (`_verifier_fils`) : matière existante ; **pas de matière d'un rôle linéaire** (cuir, franges, ruban se posent au mètre) ; étage ≤ nombre d'étages ; pas deux fois la même matière au même étage ; mètres > 0 ; largeur d'un étage = **Σ mètres × part / 100** ≤ laize (deux fils à 60 et 40 % sur les mêmes 4 m en occupent 4). Une part de 0 % est permise. Ni l'activité du métier ni celle de la matière ne sont contrôlées. | `REF:1343-1368` ; commit `202d1a0` |
| R-REF-80 | **Poids d'un fil monté** = bobines × poids d'une bobine, avec bobines = mètres × densité du métier × part / 100, et poids d'une bobine = celui **pesé au lot** — le dernier lot **sorti vers les machines** (mouvement SORTIE négatif, lot à poids > 0, le plus récent par date d'effet puis id), sinon le dernier lot **reçu** (par date d'entrée puis id) — à défaut celui du **catalogue** (exigence M43). Un métier **arrêté** pèse 0. Le même chiffre partout (API, moteur, stock). | `REF:1160-1185`, `REF:1371-1379`, `DEP:131-150` ; commit `2010f4f` ; `final-C` (Atelier 11) |
| R-REF-81 | Effet du montage sur le stock, dit avant et après : la trace `{avant, apres, ecart}` (arrondis au dixième) et le **journal** « montage », objet `metier`, détail `f"{code}{quoi} : {lignes} — sur les métiers {avant} → {après} kg ({écart signé} kg)"` où `quoi` = « » ou `f", étage {n}"`, chaque ligne `f"étage {n} {référence} {mètres} m"` (virgule décimale) + `f" ({part:g} %)"` si part ≠ 100, « vide » sans fil, kilos à la française (« 1 395,8 »). | `REF:1382-1394`, `REF:1414-1415`, `REF:1443-1445` |
| R-REF-82 | **Le fil monté est du stock « en machine »** : il compte dans le stock de l'usine, sa valeur (`valeur_mad` = poids × CMUP, pas pour l'alimentation) dans la valeur du stock, et dans le disponible et le stock projeté, donc dans le plan d'achat (« les bobines du cantre tisseront les prochains tapis »). | `REF:1198-1211` ; décisions de Mohamed, commits `f33a428`, `169dfdc` (après un passage « information seulement », commit `202d1a0`) ; exigences M62, M63 |
| R-REF-83 | `GET /metiers` (tout connecté) rangés **par nom puis code** (même ordre partout où l'on choisit un métier) ; par fil : bobines, poids, poids catalogue / utilisé / source (« lot N (sorti) » ou « lot N (reçu) », « catalogue », « »), `ecart_mesure` = pesé / catalogue − 1 (si pesé), `ecart_hors_tolerance` (> `toler_poids_bobine`) ; par étage : fils, mètres occupés, bobines, poids, `trop_large` ; par métier : poids, valeur (null pour l'alimentation), bobines, mètres, `etages_garnis`, `etages_trop_larges`, `densite_a_saisir` (densité nulle), `fils_sans_poids`, `bons` (ordres qui le nomment), `tolerance_bobine`, `dernier_montage` (par, quand, détail — lu au journal parmi les 500 derniers montages), empreintes du réglage, du montage et de chaque étage. | `REF:1188-1259` ; commit `2010f4f` (« CRM 1 · Métier 1 ») |
| R-REF-84 | `GET /montage/references` (tout connecté) : pour chaque matière **non linéaire**, le poids de bobine que le montage comptera et sa source, ce qui est parti aux machines ces **30 derniers jours** (`SORTIE` + `RETOUR_MACHINE`, retours déduits, `JOURS_SORTIES = 30`) et ce qui est déjà monté sur les métiers **en service** — l'écran prévient quand le monté dépasse le sorti récent. | `REF:1148-1157`, `REF:1262-1281` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-59 | code de métier déjà pris | 409 | `f"Le métier « {e.code.strip()} » existe déjà."` | `REF:1287-1288`, `REF:1304-1305` |
| X-REF-60 | métier inconnu | 404 | `"Métier introuvable."` | `REF:1301-1302`, `REF:1329-1330`, `REF:1404-1405`, `REF:1425-1426` |
| X-REF-61 | empreinte du réglage périmée | 409 | § 0.6, `"Ce métier"` | `REF:1303` |
| X-REF-62 | moins d'étages que l'étage le plus haut monté | 422 | `f"Des fils sont montés à l'étage {trop_haut[-1]} : les retirer ou les déplacer avant de ramener le métier à {e.etages} étage(s)."` | `REF:1306-1309` |
| X-REF-63 | laize réduite sous la largeur montée | 422 | `f"Étage {n} : {metres:g} m montés, plus que la laize de {e.laize:g} m demandée. Retirer d'abord du fil."` | `REF:1310-1316` |
| X-REF-64 | suppression avec fils montés | 409 | `f"« {x.code} » porte encore {len(x.fils)} fil(s) : les retirer d'abord."` | `REF:1331-1332` |
| X-REF-65 | suppression d'un métier nommé par `n` ordres | 409 | `f"« {x.code} » est nommé par {n} ordre(s) de fabrication : il appartient à l'historique. L'arrêter plutôt que le supprimer."` | `REF:1333-1336` |
| X-REF-66 | montage : empreinte périmée | 409 | § 0.6, `"Le montage de ce métier"` ou `f"L'étage {etage}"` | `REF:1406`, `REF:1429` |
| X-REF-67 | étage hors de 1…`etages` (montage d'un étage) | **404** | `f"Étage {etage} : ce métier n'en a que {x.etages}."` | `REF:1427-1428` |
| X-REF-68 | matière inconnue | 422 | `"Matière inconnue."` | `REF:1350-1351` |
| X-REF-69 | matière d'un rôle linéaire | 422 | `f"« {a.reference} » ({a.role}) se pose au mètre linéaire : elle ne se monte pas en bobines sur un métier."` | `REF:1352-1354` |
| X-REF-70 | fil à un étage > `etages` | 422 | `f"Étage {f.etage} : ce métier n'en a que {x.etages}."` | `REF:1355-1356` |
| X-REF-71 | même matière deux fois au même étage | 422 | `f"« {a.reference} » est monté deux fois à l'étage {f.etage}."` | `REF:1357-1358` |
| X-REF-72 | mètres ≤ 0 | 422 | `f"« {a.reference} » à l'étage {f.etage} : saisir les mètres montés."` | `REF:1359-1360` |
| X-REF-73 | largeur d'un étage > laize | 422 | `f"Étage {n} : {largeur:g} m montés (mètres × part de chaque fil) pour une laize de {x.laize:g} m."` | `REF:1365-1368` |

### 1.12 Postes de frais (direction ; lecture achats)

| # | Règle | Référence |
|---|---|---|
| R-REF-85 | `GET /postes-frais` (tout connecté) : code, libellé, récupérable, clé, ordre, triés par ordre. `GET /postes-frais/complet` (achats) : en plus, `systeme` et l'usage (`frais`, `dossiers_ouverts`, `dossiers_clos`). | `REF:1450-1454`, `RIM:47-72` |
| R-REF-86 | Un poste dit s'il est **récupérable** (la TVA : hors du coût, comptée à part dans la trésorerie) et sa **clé de répartition** : `valeur` (défaut, « l'usage de la maison », exigence M51) ou `poids` (le fret, la manutention suivent les kilos). | `RIM:1-12`, `RIM:41` ; cahier § 2.7 |
| R-REF-87 | **Postes système** `DD`, `TPI`, `TVA` (récupérable), `FRET`, `ASSUR` : lus par les calculs (TVA attendue), ils **gardent leur nature** et **ne se suppriment pas**. | `RIM:37-40` |
| R-REF-88 | Création (`POST /postes-frais`) : code **strip + MAJUSCULES**, motif `[A-Z0-9_]{1,16}` ; libellé obligatoire (strip, 1–80) ; clé `valeur` ou `poids` ; ordre 0–999, à défaut **max + 1**. Journal « création poste de frais », détail `f"{code} · {libellé} · {CLES[cle]}"` (CLES : « à la valeur », « au poids ») + « · récupérable ». | `RIM:75-104` |
| R-REF-89 | Modification (`PUT /postes-frais/{code}`, **verrou de ligne**) : le code ne change pas ; changer la **nature** (récupérable) est refusé pour un poste système et pour un poste qui porte des frais dans un **dossier clos** (« changer sa nature changerait leur coût ; créer un autre poste ») ; pour chaque dossier **non clos** dont la répartition changerait (nature changée, ou clé changée sur un frais global non figé), contrôle de la période close (§ 0.5, geste `f"changement du poste « {libellé} »"`). | `RIM:145-169` ; commit `f216509` |
| R-REF-90 | **Changer la clé recalcule les dossiers ouverts, jamais les clos** : avant le changement, dans chaque dossier **clos** à au moins 2 lignes, chaque frais **global** (sans ligne visée, pas déjà figé) de ce poste **garde sa répartition à l'ancienne clé**, marchandise par marchandise (`DossierChargePart`, montants **sans arrondi**, lignes de poids nul exclues) ; le frais reste **une seule pièce** (un montant, un règlement, une échéance). Poids = kilos de la ligne ; valeur = valeur en devise (MAD) ou × cours de la ligne (à défaut cours du jour). Dossiers clos **verrouillés** pendant le changement. Journal « frais figés » par dossier, détail `f"{numéro} · {poste} {ancienne clé} : dossier clos, sa répartition est gardée ({n} frais, une pièce chacun)"`. | `RIM:107-142`, `RIM:170-172` ; commit `58f507c` ; essai `test_changer_la_cle_garde_une_piece_et_son_reglement` |
| R-REF-91 | Journal « modification poste de frais », détail `f"{code} : {libellé avant} · {clé avant} → {libellé} · {clé}"` + `f" · {n} dossier(s) clos figé(s)"`. Réponse avec `dossiers_figes`. | `RIM:173-181` |
| R-REF-92 | Suppression (`DELETE /postes-frais/{code}`) : ni poste système, ni poste qui porte un frais (dans n'importe quel dossier). Journal « suppression poste de frais ». | `RIM:184-197` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-74 | code invalide (après strip + majuscules) | 422 | `"Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT)."` | `RIM:93-95` |
| X-REF-75 | libellé vide après strip | 422 | Pydantic, texte `"le libellé est obligatoire"` | `RIM:82-87` |
| X-REF-76 | code existant | 409 | `f"Le poste « {code} » existe déjà."` | `RIM:96-97` |
| X-REF-77 | poste inconnu | 404 | `"Poste de frais introuvable."` | `RIM:149-150`, `RIM:188-189` |
| X-REF-78 | changement de nature d'un poste système | 409 | `f"« {p.libelle} » est {'récupérable' if p.recuperable else 'un coût'} par nature : les calculs du dossier (TVA attendue) le lisent ainsi."` | `RIM:153-155` |
| X-REF-79 | changement de nature avec frais dans `n` dossiers clos | 409 | `f"Ce poste porte des frais dans {usage['dossiers_clos']} dossier(s) clos : changer sa nature changerait leur coût. Créer un autre poste."` | `RIM:156-158` |
| X-REF-80 | changement de clé/nature touchant un dossier ouvert dont la marchandise est entrée en période close | 409 | D4 (§ 0.5) | `RIM:162-169` |
| X-REF-81 | suppression d'un poste système | 409 | `f"« {p.libelle} » sert aux calculs du dossier : il ne se supprime pas."` | `RIM:190-191` |
| X-REF-82 | suppression d'un poste qui porte des frais | 409 | `"Ce poste porte des frais dans des dossiers : il ne se supprime pas."` | `RIM:192-193` |

### 1.13 Codes douaniers (direction ; lecture achats)

| # | Règle | Référence |
|---|---|---|
| R-REF-93 | Un code douanier = position du tarif (clé, ≤ 20), libellé ≤ 160, **taux de droits** 0–1 (0,10 = 10 %), actif. Porté par chaque matière, il donne les **droits attendus** d'un dossier, comparés à la quittance (exigence M53). | `RIM:17-18`, `MOD:252-263` |
| R-REF-94 | Saisie : espaces retirés partout ; motif `\d[\d.]{1,19}` (chiffres éventuellement séparés de points, ex. 5402.47.00.00). | `RIM:220-233` |
| R-REF-95 | `GET /codes-douaniers` (achats) trié par code, avec le nombre de matières qui le portent. Création, modification, suppression : direction. Le **code lui-même se corrige** (les matières suivent, `ON UPDATE CASCADE`). Un code porté ne se supprime pas (le désactiver). Un code **désactivé** ne dit plus le taux : la matière compte comme sans code dans le dossier. Journaux « création / modification / suppression code douanier », détail `f"{code} · {taux:.2%}"`, `f"{avant} → {code} · {taux:.2%}"` + « · désactivé ». | `RIM:203-278`, `IMP:245-249` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-REF-83 | code mal formé | 422 | Pydantic, texte `"un code douanier s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00)"` | `RIM:226-233` |
| X-REF-84 | code existant (création, ou renommage vers un code pris) | 409 | `f"Le code douanier « {e.code} » existe déjà."` | `RIM:239-240`, `RIM:256-257` |
| X-REF-85 | code inconnu | 404 | `"Code douanier introuvable."` | `RIM:254-255`, `RIM:270-271` |
| X-REF-86 | suppression d'un code porté par `n` matières | 409 | `f"{n} matière(s) portent ce code : le leur retirer d'abord, ou le désactiver."` | `RIM:272-274` |

### 1.14 Exports Excel des référentiels (achats)

| # | Règle | Référence |
|---|---|---|
| R-REF-96 | `GET /export/matieres` (`matieres-AAAA-MM-JJ.xlsx`) : référence, désignation, rôle, composition, type, titrage, couleur, code couleur, fournisseur, prix, devise, unité du prix, prix/kg, densité, unité d'achat, contenance, « déclarée/déduite », minimum, kg/bobine, bobines/palette, stock min, couverture min, groupe, code douanier, en stock, active. `GET /export/fournisseurs/fiches` : fiche complète + délai déclaré et mesuré + devises. `GET /export/qualites` : une ligne par fil de recette (rôle, part, kg/m², prix d'achat, « devise / unité », coût/m²) et le coût de la qualité. Titre de feuille + « exporté le JJ/MM/AAAA ». | `REF:1460-1537` |

---

## 2. Commandes (bons de commande fournisseur)

Rôle : toutes les routes de `ACH` exigent **achats** (direction comprise), sauf `approuver` et
`renvoyer` (**direction seule**). L'alimentation ne lit ni commandes ni réceptions (essai
`test_l_atelier_ne_lit_ni_commandes_ni_receptions`).

Principes (docstring `ACH:1-17`) : on ne commande jamais sans arbitrer les quantités (la
préparation est obligatoire à l'écran, exigence M30 — le serveur ne peut pas le distinguer,
`final-A` « M30 ⛔ ») ; **un bon par devise** ; le bon **part sans prix**, le fournisseur les
confirme (M31) ; un brouillon n'a pas de numéro ; au-delà du seuil la direction approuve ou
renvoie ; l'approbation se mesure au **cours figé** ; le cours se fige à la **première**
confirmation des prix ; la date promise se fixe à l'envoi, se confirme au plus tard avec les
prix, puis se fige ; un bon se modifie tant que rien n'est reçu.

### 2.1 Modèle et statuts

| # | Règle | Référence |
|---|---|---|
| R-CMD-01 | `Commande` : `numero` (unique, **nul** tant que le bon n'est pas parti), fournisseur, `date_commande` (date du bon = date d'envoi une fois parti), `date_livraison_prevue` (la **date promise**), `statut`, `devise`, `cours` (0 = pas encore figé), `observations`, jalons `proforma_le`, `acompte_le`, `embarquee_le`, `eta`, `au_port_le`, `dedouanee_le`, `arrivee_usine_le`, `conteneur` ≤ 60, `navire` ≤ 80, `cree_par`, `cree_le`, `approuvee_par`, `approuvee_le`, `montant_approuve` (MAD ; 0 = inconnu), `version_approuvee` (JSON de la **version partie** ; vide = inconnue). | `MOD:552-591` |
| R-CMD-02 | `CommandeLigne` : matière (**une seule fois par bon**), `quantite` **en kg** (> 0), `unite_achat` (défaut kg), `contenance` (> 0, kg par unité, défaut 1), `prix` (≥ 0, dans la devise du bon, **au kilo**), `prix_confirme`, `confirme_le`, `confirme_par`. | `MOD:594-613` |
| R-CMD-03 | Statuts et libellés : `brouillon` « Brouillon », `a_approuver` « À approuver », `envoyee` « Envoyée », `confirmee` « Confirmée », `soldee` « Soldée », `annulee` « Annulée ». Pas d'état « Approuvée » distinct (l'approbation donne le numéro et le bon part). | `MOD:542-549` ; `final-A` rapport 1 n° 7 |
| R-CMD-04 | **Un bon est parti s'il a un numéro**, quel que soit son statut : un bon parti que les achats font grossir repasse « à approuver » mais le fournisseur l'a toujours — sa quantité reste attendue, son camion se reçoit, il ne se supprime pas ; soldé ou annulé, il reste un bon parti. | `ACH:60-65` ; commit `d68dbb2` |
| R-CMD-05 | Statut « parti » d'un bon : `confirmee` si **toutes** ses lignes ont un prix confirmé (et qu'il en a), sinon `envoyee`. | `ACH:197-198` |
| R-CMD-06 | Statut transmis au moteur : un bon numéroté au statut brouillon ou à approuver est lu « Confirmée » (toutes lignes confirmées) ou « Envoyée » ; sinon correspondance `brouillon`/`a_approuver` → « Brouillon », `envoyee` → « Envoyée », `confirmee` → « Confirmée », `soldee` → « Soldée », `annulee` → « Annulée ». Un brouillon n'engage rien (ni stock attendu, ni retard, ni montant). | `DEP:23-40`, `CMO:398-405` |
| R-CMD-07 | `nom_commande` = numéro, sinon `f"brouillon n° {id}"` (dans les messages et le journal). Numéro moteur d'un brouillon : `f"BC-brouillon-{id}"`. | `ACH:489-490`, `DEP:340` |

### 2.2 Prix, montants et cours

| # | Règle | Référence |
|---|---|---|
| R-CMD-08 | Prix du catalogue d'une ligne = `prix_kg` de la matière (un prix au mètre ramené au kilo : « 1,68 kg de ruban à 0,014 kg/ml et 2,50 le mètre font 300, comme 120 ml à 2,50 »). | `ACH:46-50` |
| R-CMD-09 | Prix du catalogue **dans la devise voulue** (celle du bon ou de la réception) : si la fiche est dans une autre devise, conversion au **cours du jour** `prix × taux(devise fiche) / taux(devise voulue)` (« une fiche passée d'USD à EUR ne fait pas lire 1,60 EUR comme 1,60 USD » ; c'est une estimation). | `ACH:153-160` ; essai `test_une_fiche_qui_change_de_devise_ne_fausse_pas_le_prix_du_bon` |
| R-CMD-10 | Prix estimé d'une ligne = prix confirmé s'il l'est, sinon prix du catalogue dans la devise du bon (un bon part sans prix : compté à 0, il disparaîtrait des montants). **Montant estimé** du bon (devise du bon) = Σ quantité × prix estimé. C'est ce montant qui décide de l'approbation. | `ACH:163-178` ; commit `f85dabd` |
| R-CMD-11 | Cours du bon = `cours` figé s'il l'est, sinon cours du jour de la devise (table des devises ; 1,0 si inconnue). Montant MAD de l'approbation = montant estimé × cours du bon (« le dollar qui monte ne fait pas repasser par la direction un bon qu'on réduit »). | `ACH:41-43`, `ACH:181-190` ; essai `test_reduire_un_bon_usd_quand_le_dollar_monte_ne_repasse_pas_par_la_direction` |
| R-CMD-12 | Formatage MAD des journaux : `f"{x:,.0f}".replace(",", " ") + " MAD"` (« 98 923 MAD »). | `ACH:193-194` |

### 2.3 La version partie et le garde-fou de l'approbation

| # | Règle | Référence |
|---|---|---|
| R-CMD-13 | **Version partie** = ce que le fournisseur a entre les mains : les lignes du bon tel qu'il est parti (ou tel que la direction, ou le seuil, l'a accepté depuis) — par ligne `article_id`, `quantite`, `unite_achat`, `contenance`, `prix`, `prix_confirme`, `confirme_par`, `confirme_le` — et le **montant de référence** (devise du bon) pour lequel il est parti. Toute hausse se mesure à lui. Un JSON illisible ou sans liste de lignes vaut « inconnue ». | `ACH:201-217` |
| R-CMD-14 | `figer_version(montant=True)` (envoi, approbation) fixe aussi le montant de référence = montant estimé actuel ; `montant=False` (geste accepté **sans** la direction : sous le seuil, dans la tolérance) **garde** l'ancien montant de référence — « vingt hausses de 4,9 % ne passent pas une à une ». | `ACH:220-231` ; essai `test_l_approbation_ne_se_contourne_pas_par_paliers` |
| R-CMD-15 | Montant de référence : celui de la version partie ; à défaut (bon d'avant), `montant_approuve / cours du bon` ; sinon le montant d'avant le geste. | `ACH:234-243` |
| R-CMD-16 | **Garde-fou** après tout changement de montant (`_controler_montant(avant, geste, tolerance)`) : (a) un **brouillon « à approuver » sans numéro** modifié revient en **brouillon** (journal « retour en brouillon », détail `f"{bon} · modifié pendant l'approbation ({geste}) · {avant MAD} → {après MAD}"`) — la direction ne relit pas un bon qui bouge sous ses yeux ; (b) sans numéro ou statut hors {envoyee, confirmee, a_approuver} : rien ; (c) sinon l'approbation est **requise** si `seuil > 0` **et** `après × cours > seuil` **et** `après > référence × (1 + marge) + 0,005`, où `marge = 0` si le bon est **parti sous le seuil** (`montant_approuve <= seuil` et non nul), sinon `tolerance` (0, ou 5 % pour une confirmation de prix) ; (d) un bon **à approuver numéroté** que les achats ramènent sous ce qui était accepté reprend sa route (statut parti, version figée sans relever la référence, journal « approbation plus nécessaire », détail `f"{bon} · {geste} · ramené à {MAD}"`) ; (e) un bon parti dont la hausse est requise repasse **« à approuver »** (approbation effacée : `approuvee_par = ""`, `approuvee_le = None` ; numéro conservé), journal « commande à approuver », détail `f"{bon} · {geste} · {avant MAD} → {après MAD} (seuil {seuil MAD})"` ; (f) sinon le geste est accepté : il devient la version partie (`montant=False`). **Une baisse ne repasse jamais par la direction.** | `ACH:246-291` ; commits `b6b751c`, `d68dbb2` ; `docs/AUDIT-2026-10-08.md` (bloquant « contourner l'approbation ») |

### 2.4 Lecture des bons (`GET /commandes`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-17 | Liste des bons du plus récent (id décroissant) au plus ancien ; reçu, quarantaine, tolérances, seuil, taux, réceptions et renvois lus une fois (`Contexte`). | `ACH:107-146`, `ACH:368-372` |
| R-CMD-18 | **Reçu d'une ligne** (net) = Σ pesées des lignes de réception **validées**, **non refusées**, qui la nomment, **moins** ce qui est reparti chez le fournisseur (retours au fournisseur du lot, nets de leurs annulations, répartis entre les lignes de réception du lot **au prorata de leur pesée**, sans dépasser ce que chacune a apporté). Une matière renvoyée est due de nouveau. | `DEP:59-108` ; commit `bcb14b5` |
| R-CMD-19 | **En quarantaine** d'une ligne = part du solde en magasin « Quarantaine » des lots reçus **sous réserve** pour elle (prorata des pesées). | `DEP:111-128` |
| R-CMD-20 | **Reste** d'une ligne = 0 si le bon est soldé ou annulé ; sinon `max(0, quantité − reçu)`, ramené à **0** s'il est ≤ quantité × `toler_in_full`. | `ACH:301-304` |
| R-CMD-21 | **Livré** = le bon a des lignes et **chaque ligne** a reçu (net, hors quarantaine si demandé) ≥ quantité × (1 − tolérance) — ligne par ligne, « sur le total, une ligne livrée dix fois cacherait les neuf autres ». | `ACH:68-75` ; essai `test_une_ligne_sur_dix_livree_dix_fois_n_est_ni_complete_ni_livree` |
| R-CMD-22 | **État de livraison** (`livraison`) : « » si le bon n'est pas parti ; « 🟢 Livré » si livré hors quarantaine ; sinon « ⚫ Soldé » (reçu > 0) / « ⚫ Soldé sans livraison » si soldé ; « ⚫ Annulé » si annulé ; « 🟡 Reçu sous réserve » si livré en comptant la quarantaine ; sinon, avec date prévue = ETA à défaut date promise, à l'heure si pas de date ou `prévue + retard toléré (jours) >= aujourd'hui` : « 🟡 En cours » / « 🟠 Partiel retard » (reçu > 0) ou « ⚪ Attendu » / « 🔴 En retard ». | `ACH:78-100` |
| R-CMD-23 | Champs calculés : par ligne `unites` = quantité ÷ contenance, `prix_catalogue`, `devise_catalogue`, `montant` (si confirmé), `montant_estime`, `recu`, `en_quarantaine`, `reste`, `reste_estime`, `kg_par_ml`, `unite_prix` ; par bon `montant`, `montant_mad`, `montant_estime(_mad)`, `reste_kg`, `reste_estime_mad`, `quantite`, `recu`, `part_livree` (≤ 1), `prix_a_confirmer`, `confirme_le` (le plus récent), `seuil_approbation`, `approbation_requise` (= seuil > 0 et estimé × cours > seuil et pas d'`approuvee_par`), `expedition` (jalons, conteneur, navire), `livree_le` (dernière réception validée **seulement si** « 🟢 Livré »), `derniere_reception_le`, `receptions` (une fois par réception), `renvoi` (dernier renvoi de la direction, si le statut est brouillon/envoyée/confirmée et qu'aucune soumission, envoi ou approbation ne l'a suivi : par, le, motif = détail après le premier « · »), `modifiable` (= pas soldé/annulé et aucune ligne nommée par une réception). Les montants en MAD utilisent le cours figé, sinon du jour. | `ACH:294-365` |

### 2.5 Création (`POST /commandes`)

Entrée `CommandeEntree` : `fournisseur_id`, `date_livraison_prevue` (facultative), `sans_prix`
(défaut **vrai**), `observations` ≤ 2000, `lignes` ≥ 1 de `{article_id, quantite > 0 (kg) ≤ 1e9,
unite_achat ≤ 32 (défaut kg), contenance > 0 (défaut 1), prix ≥ 0 facultatif}` (`ACH:379-393`).

| # | Règle | Référence |
|---|---|---|
| R-CMD-24 | Chaque matière doit exister, être **fournie par ce fournisseur** (`article.fournisseur_id`), et n'apparaître **qu'une fois** (« regrouper les quantités »). Ni l'activité de la matière ni celle du fournisseur ne sont contrôlées. | `ACH:434-449` |
| R-CMD-25 | **Unités de commande permises** (la même règle que l'écran) : `kg` (contenance **exactement 1**) ; `Bobine` (contenance = kg/bobine du catalogue) si connu ; `Palette` (= kg/bobine × bobines/palette) si les deux sont connus ; l'unité d'achat déclarée de la fiche (≠ kg, ≠ ml, contenance > 0) à sa contenance. Contenance comparée à 1e-6 relatif près. Une ligne **déjà sur le bon** garde son conditionnement même si la fiche a changé depuis. « ml » n'est jamais une unité de commande. | `ACH:396-431` ; essai `test_l_unite_de_commande_est_celle_de_la_fiche` |
| R-CMD-26 | **Un bon par devise** : les lignes sont regroupées par devise **de la fiche matière** ; un bon par groupe, dans l'ordre alphabétique des devises ; tous en `brouillon`, **sans numéro**, `date_commande` = aujourd'hui, date promise = celle saisie (vide : elle se comptera à l'envoi — « un brouillon qui attend trois semaines ne part pas avec une promesse déjà passée »). | `ACH:452-486` |
| R-CMD-27 | Prix des lignes : `sans_prix` (défaut) → **0** ; sinon prix saisi, à défaut prix du catalogue au kilo. Journal « création commande » par bon, détail `f"{bon} · {fournisseur} · {n} ligne(s)"`. Renvoie la liste des bons créés. | `ACH:473-486` |

### 2.6 Modification (`PUT /commandes/{cid}`)

Entrée : `date_livraison_prevue`, `observations`, `lignes` ≥ 1 (`ACH:608-611`).

| # | Règle | Référence |
|---|---|---|
| R-CMD-28 | Bon **verrouillé** (`with_for_update`). Refusé s'il est soldé ou annulé, ou si **une réception** (brouillon, validée ou annulée) nomme une de ses lignes — « créer un autre bon pour le complément, ou le solder ». | `ACH:642-647`, `ACH:531-535`, `ACH:53-57` |
| R-CMD-29 | **Date promise** (`_changer_promesse`) : vide ou inchangée → rien. Sur un bon **parti** : figée dès que le cours est figé (confirmation des prix) ; une promesse **passée** ne se repousse plus ; jamais avant la date du bon. Une nouvelle annonce du fournisseur va dans l'**ETA**. Sur un brouillon, ce n'est qu'une date souhaitée (libre). | `ACH:614-636` ; commits `bcb14b5`, `d68dbb2` ; essais `test_la_date_promise_se_compte_a_l_envoi`, `test_la_promesse_se_confirme_avec_les_prix_puis_se_fige` |
| R-CMD-30 | Lignes **remplacées** : mêmes contrôles qu'à la création (R-CMD-24, 25, une ligne déjà sur le bon garde son conditionnement) ; toutes les matières doivent être de la **devise du bon**. Prix : saisi, sinon l'ancien prix de la ligne, sinon 0. Un **prix confirmé que l'on change** n'est plus celui du fournisseur : il redemande confirmation (auteur et date effacés) ; un prix non envoyé ou identique (1e-9) garde sa confirmation. | `ACH:649-669` ; essai `test_un_prix_confirme_change_par_la_modification_redemande_confirmation` |
| R-CMD-31 | Un bon envoyé/confirmé reprend le statut parti calculé (une ligne ajoutée attend son prix : un bon « confirmé » ne l'est plus tout à fait). Journal « modification commande », détail `f"{bon} · {avant MAD} → {après MAD}"` (au cours du bon), puis garde-fou (R-CMD-16, geste « lignes modifiées », tolérance 0). | `ACH:670-682` ; essai `test_un_bon_confirme_modifie_attend_le_prix_de_sa_nouvelle_ligne` |

### 2.7 Envoi (`POST /commandes/{cid}/envoyer`, corps facultatif `{date}`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-32 | Seul un **brouillon** s'envoie. Bon verrouillé. | `ACH:695-699` |
| R-CMD-33 | Si `seuil > 0` et montant MAD (estimé × cours du bon) > seuil et pas d'`approuvee_par` : le bon est **soumis** à la direction (statut `a_approuver`, **sans numéro**) ; refusé si la date promise saisie précède la date d'envoi voulue (ou aujourd'hui). Journal « commande à approuver », détail `f"{bon} · {MAD}"`. | `ACH:700-708` |
| R-CMD-34 | Sinon le bon **part** (`_numeroter`) : date d'envoi = celle saisie (passée permise — « un bon parti la semaine dernière par téléphone se date du jour réel de l'envoi ») sinon aujourd'hui, contrôlée par `date_permise` (D1–D3) ; la date promise saisie ne peut précéder l'envoi ; vide → **date d'envoi + délai du fournisseur** (jours, partie entière) ; `date_commande` = date d'envoi ; numéro `BC-AAAA-NNNN` (année de l'envoi). Statut parti (R-CMD-05), `montant_approuve` = montant MAD, version figée **avec** montant. Journal « envoi commande », détail `f"{bon} · {MAD}"`. | `ACH:493-515`, `ACH:709-716` ; essai `test_un_brouillon_n_a_pas_de_numero_et_se_date_a_l_envoi` |

### 2.8 Approbation (`POST /commandes/{cid}/approuver`, direction)

| # | Règle | Référence |
|---|---|---|
| R-CMD-35 | Seul un bon **à approuver** s'approuve. Sans numéro, il **part** : numérotation à la date du **jour** (pas de date d'envoi saisie à ce stade) ; une promesse antérieure au départ (l'attente de la direction l'a dépassée) est **recomptée** (envoi + délai) au lieu d'être refusée. Un bon déjà numéroté garde numéro et date. | `ACH:493-515`, `ACH:719-727` |
| R-CMD-36 | Statut parti, `approuvee_par` = nom, `approuvee_le` = maintenant, `montant_approuve` = montant MAD (au cours du bon), version figée avec montant. Journal « approbation commande », détail `f"{bon} · {MAD} approuvés"`. Puis **recalage des soldes** (un bon parti a pu être livré pendant qu'il attendait). | `ACH:728-736` |

### 2.9 Renvoi aux achats (`POST /commandes/{cid}/renvoyer`, direction, `{motif}` 3–500)

| # | Règle | Référence |
|---|---|---|
| R-CMD-37 | Seul un bon à approuver se renvoie. Un **brouillon** (sans numéro) redevient **brouillon** : les achats le corrigent et le soumettent de nouveau, ou le suppriment. Journal « renvoi aux achats », détail `f"{bon} · {motif}"` (le motif se relit sur le bon). | `ACH:764-778` |
| R-CMD-38 | Un bon **parti** reste parti : il **revient à sa version partie** (la direction n'a pas accepté le changement, le fournisseur attend ce qu'il a reçu) : lignes absentes de la version retirées **sauf si une réception les nomme** ; lignes de la version recréées ou remises à leurs quantité, unité, contenance, prix, confirmation d'alors ; statut parti recalculé ; journaux « renvoi aux achats » et « version partie rétablie » (`f"{bon} · {MAD} : le bon reste chez le fournisseur tel qu'il était parti"`) ; recalage des soldes. | `ACH:743-761`, `ACH:779-793` ; commit `d68dbb2` ; essai `test_un_bon_parti_qui_attend_la_direction_reste_attendu_et_se_recoit` |

### 2.10 Confirmation des prix (`POST /commandes/{cid}/prix`)

Entrée `ConfirmationPrix` : `prix` ≥ 1 de `{ligne_id, prix > 0 ≤ 1e7}`, `mettre_a_jour_catalogue`
(défaut **vrai**), `date_livraison_prevue` (facultative : la date que le fournisseur confirme)
(`ACH:796-805`).

| # | Règle | Référence |
|---|---|---|
| R-CMD-39 | Refusée sur un bon **annulé** seulement (permise sur brouillon, à approuver, soldé). Bon verrouillé. La date promise suit R-CMD-29 **avant** que le cours ne se fige : la première confirmation peut donc encore la changer. | `ACH:814-817` |
| R-CMD-40 | Chaque ligne citée : `prix`, `prix_confirme = vrai`, `confirme_le = maintenant`, `confirme_par = nom`. Avec `mettre_a_jour_catalogue` : le prix passe **au catalogue** (« c'est le geste qui fait vivre la matrice des prix », M31) — au mètre (× densité) si la fiche est au prix au mètre —, `version + 1`, `modifie_le`, `modifie_par` de la matière. | `ACH:820-831` ; commit `d2e1e39` |
| R-CMD-41 | Le **cours se fige à la première confirmation** (cours du jour de la devise du bon), pas à chaque correction. Un bon `envoyee` dont toutes les lignes sont confirmées passe `confirmee`. Journal « prix confirmés », détail `f"{bon} · {n} prix · {avant MAD} → {après MAD}"`. | `ACH:832-837` ; essai `test_le_cours_se_fige_a_la_premiere_confirmation` |
| R-CMD-42 | Garde-fou (R-CMD-16, geste « prix confirmés », **tolérance 5 %**) — sauf pour un brouillon à approuver sans numéro : « un prix confirmé plus cher de quelques pour cent ne rouvre pas l'approbation ; un bon qui franchit le seuil, ou qui s'envole, si ». | `ACH:838-841` ; essai `test_un_prix_confirme_un_peu_plus_cher_ne_rouvre_pas_l_approbation` |

### 2.11 Expédition (`PUT /commandes/{cid}/expedition`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-43 | Jalons : proforma reçue, acompte payé, embarquée, **ETA**, arrivée au port, dédouanée, arrivée à l'usine ; conteneur, navire. Seulement **après l'envoi** (bon numéroté). Un jalon **constaté** ne se date pas dans le futur ; seule l'ETA est une attente. **Tous** les champs sont remplacés (un champ absent est vidé). L'ETA remplace la date promise dans la prévision et le « en retard », **pas** dans la ponctualité (qui se juge sur la date promise). Journal « expédition », détail `f"{bon} · ETA {eta:%d/%m/%Y}"` ou le bon seul. | `ACH:846-884`, `DEP:345-348` ; cahier § 2.5 ; essais `test_les_jalons_de_l_expedition`, `test_l_eta_saisie_apres_coup_n_efface_pas_le_retard` |

### 2.12 Solder (`POST /commandes/{cid}/solder`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-44 | « On n'attend plus le reste ». Refusé sur un bon déjà clos, sur un bon **à approuver numéroté** (la direction l'approuve ou le renvoie d'abord — sinon solder puis rouvrir passerait outre), sur un bon **non parti** (il se supprime). Un bon qu'un camion a servi (au moins une réception **validée**, même entièrement renvoyée ou refusée depuis) devient **soldé** (sa livraison garde sa note) ; un bon jamais livré devient **annulé**. Journal « commande soldée » (détail = bon, **sans** « tout reçu » : c'est un solde **à la main**) ou « commande annulée ». | `ACH:538-547`, `ACH:887-906` ; commit `d68dbb2` ; essais `test_solder_un_bon_a_approuver_est_refuse…`, `test_solder_un_bon_tout_renvoye_le_solde_et_garde_sa_note` |

### 2.13 Rouvrir (`POST /commandes/{cid}/rouvrir`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-45 | Seul un bon soldé ou annulé se rouvre : statut parti s'il a un numéro, sinon brouillon. Journal « commande rouverte ». Un bon parti **repasse par le garde-fou** (geste « réouverture ») : rouvert au-delà de ce que la direction a accepté, il retourne chez elle. | `ACH:909-921` ; `docs/AUDIT-2026-10-08.md` |

### 2.14 Supprimer (`DELETE /commandes/{cid}`)

| # | Règle | Référence |
|---|---|---|
| R-CMD-46 | Seul un bon **sans réception** (de quelque statut que ce soit) et **jamais parti** (sans numéro) se supprime ; un bon parti s'annule et garde son numéro (« la série reste sans trou »). Lignes supprimées en cascade. Journal « suppression commande », détail = nom du bon. | `ACH:924-936` ; M33 ; essai `test_un_brouillon_se_supprime_il_ne_se_solde_pas` |

### 2.15 Soldes automatiques et réouverture automatique (`recaler_soldes`)

Appelé après une validation ou annulation de réception, une approbation, un renvoi, un retour
au fournisseur, une sortie de quarantaine (et leurs annulations) (`ACH:572-605`, `REC:567`, `REC:596`).

| # | Règle | Référence |
|---|---|---|
| R-CMD-47 | Un bon `envoyee`/`confirmee` **livré** (chaque ligne à la tolérance près, net des retours, **rien en quarantaine**) se **solde de lui-même** : journal « commande soldée », détail `f"{bon} · tout reçu"`. Une ligne sous réserve ne le solde qu'à sa libération. | `ACH:595-597` ; commit `bcb14b5` |
| R-CMD-48 | Un bon soldé qui **n'est plus livré** se rouvre (statut parti, journal « commande rouverte », détail `f"{bon} · {raison} : le reçu net ne couvre plus le bon"`) **seulement** si son dernier solde vient d'une réception (« tout reçu »), ou — bon soldé sans trace, repris de l'ancien ERP — si c'est un **retour** qui l'a dégarni (livré sur la pesée brute, retours compris). Un bon **soldé à la main reste soldé**, quoi qu'il arrive. Un bon à approuver garde son statut. | `ACH:550-558`, `ACH:598-605` ; essais `test_un_retour_au_fournisseur_rouvre_le_bon_solde_de_lui_meme`, `test_un_bon_solde_a_la_main_le_reste_apres_un_retour`, `test_annuler_une_reception_ne_rouvre_pas_un_bon_solde_a_la_main` |
| R-CMD-49 | « Soldé à la main » (lu par le moteur : `solde_a_la_main_le`) = dernier journal « commande soldée » du bon dont le détail **ne finit pas** par « tout reçu » ; transmis au moteur seulement si le bon est soldé. | `DEP:43-52`, `DEP:352` |

### 2.16 Bon imprimé et Excel du fournisseur

| # | Règle | Référence |
|---|---|---|
| R-CMD-50 | `GET /commandes/{cid}/impression` (achats) : page HTML A4 (`@page size A4`, marges 12/13/16 mm), **en anglais** (fournisseurs étrangers), **sans aucun prix ni montant** (décision de Mohamed), sur le **papier à en-tête** de l'usine : raison sociale (rouge, Times), forme et capital, « SIEGE SOCIAL » + adresse, ville, téléphone ; pied : banques (séparées par « · » dans le réglage) puis ICE, R.C, N.I.F, C.N.S.S, PATENTE. Tout texte échappé HTML. | `ACH:972-996`, `ACH:1035-1147` ; commits `dbabfc8`, `2d588b9` |
| R-CMD-51 | Contenu : « Purchase order » + numéro, ou « Draft — not sent » ; Date (`date_en` « 08 Oct 2026 ») ou « on sending » ; Expected delivery ou « to be agreed » ; cadre Supplier (nom, pays, contact, téléphone, courriel) ; cadre Deliver to (usine, adresse, ville, date, Incoterm du fournisseur) ; tableau No. / Item (référence, désignation) / Packing / Qty / Total weight ; « Total ordered » en kg ; Remarks (observations, case à part) ; phrase de confirmation attendue ; signatures (acheteur, fournisseur). Avertissement à l'écran (non imprimé) si la raison sociale n'est pas réglée. | `ACH:1042-1147` |
| R-CMD-52 | Packing : « By weight » pour kg/ml ; sinon le conditionnement traduit (`palette` Pallet, `fût`/`fut` Drum, `bobine` Bobbin, `cône`/`cone` Cone, `sac` Bag, `rouleau` Roll, `carton` Carton, `balle` Bale, `caisse` Case, `bidon` Can ; inconnu tel quel) + « of {contenance} kg » si contenance ≠ 1. Qty = quantité ÷ contenance (3 décimales max) ou « — » au poids. Nombres à l'anglaise (« 1,234.5 », zéros inutiles retirés). Pour un cuir, des franges, un ruban : « ≈ N m » indicatif (kg ÷ densité). | `ACH:999-1032`, `ACH:1046-1056` |
| R-CMD-53 | `GET /export/commandes/{cid}/bon` (achats) : le même bon dans un classeur (feuille « Purchase order »), mêmes règles (anglais, sans prix, en-tête de l'usine ; « Raison sociale à régler (Réglages › Paramètres › Société) » si absente). Refus 404 `"Bon de commande introuvable."`. | `EXA:324-334` |
| R-CMD-54 | Lignes « telles que le fournisseur les lit » (impression, Excel) : référence, désignation, unités, unité lisible (« Bobine de 2,5 kg », « Palette de 705,6 kg », « kg »), quantité en kg, mètres indicatifs pour un rôle linéaire. | `ACH:939-969` |

### 2.17 Refus des commandes

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-CMD-01 | ligne commandée en kg avec contenance ≠ 1 | 422 | `f"« {a.reference} » : commandée en kg, la contenance vaut 1."` | `ACH:416-418` |
| X-CMD-02 | unité de commande non permise par la fiche | 422 | `f"« {a.reference} » ne se commande pas en « {ligne.unite_achat} » : {', '.join(permises)} (fiche de la matière)."` | `ACH:423-427` |
| X-CMD-03 | contenance ≠ celle de la fiche pour cette unité | 422 | `f"« {a.reference} » : une {ligne.unite_achat} contient {nombre_fr(voulue, 3)} kg, pas {nombre_fr(ligne.contenance, 3)} (fiche de la matière)."` | `ACH:428-431` |
| X-CMD-04 | matière inconnue | 422 | `"Matière inconnue dans la commande."` | `ACH:440-441` |
| X-CMD-05 | matière d'un autre fournisseur | 422 | `f"« {a.reference} » n'est pas fournie par ce fournisseur."` | `ACH:442-443` |
| X-CMD-06 | matière deux fois | 422 | `f"« {a.reference} » figure deux fois : regrouper les quantités."` | `ACH:444-445` |
| X-CMD-07 | création : fournisseur inconnu | 422 | `"Fournisseur inconnu."` | `ACH:459-460` |
| X-CMD-08 | bon inconnu (toute route) | 404 | `"Commande introuvable."` | `ACH:518-523` |
| X-CMD-09 | modification d'un bon soldé/annulé | 409 | `"Ce bon est clos."` | `ACH:643-644` |
| X-CMD-10 | modification d'un bon qui a une réception (même brouillon/annulée) | 409 | `"Ce bon a déjà des réceptions : ses lignes ne se modifient plus. Créer un autre bon pour le complément, ou le solder."` | `ACH:645-647` |
| X-CMD-11 | modification : une matière d'une autre devise | 422 | `f"Ce bon est en {c.devise} : une matière d'une autre devise va sur un autre bon."` | `ACH:652-653` |
| X-CMD-12 | date promise d'un bon parti, cours déjà figé | 422 | si une date existait : `f"La livraison promise ({ancienne:%d/%m/%Y}) est figée depuis la confirmation des prix : elle mesure la ponctualité. {eta}"` ; sinon `f"La date promise est figée depuis la confirmation des prix. {eta}"` — avec `eta = "Noter la nouvelle date annoncée par le fournisseur dans l'arrivée prévue (ETA) du suivi d'expédition."` | `ACH:621-629` |
| X-CMD-13 | date promise passée qu'on repousse | 422 | `f"La livraison était promise pour le {ancienne:%d/%m/%Y}, date passée : elle ne se repousse plus. {eta}"` | `ACH:630-632` |
| X-CMD-14 | date promise avant la date du bon (bon parti) | 422 | `f"La livraison prévue ({nouvelle:%d/%m/%Y}) précède la date du bon ({c.date_commande:%d/%m/%Y})."` | `ACH:633-635` |
| X-CMD-15 | envoi d'un bon à approuver | 409 | `"Ce bon attend l'approbation de la direction."` | `ACH:696-697` |
| X-CMD-16 | envoi d'un bon qui n'est pas brouillon | 409 | `"Ce bon est déjà parti."` | `ACH:698-699` |
| X-CMD-17 | soumission à la direction avec une date promise déjà passée | 422 | `f"La livraison prévue ({c.date_livraison_prevue:%d/%m/%Y}) est déjà passée : la corriger, ou la vider (date d'envoi + délai du fournisseur)."` | `ACH:703-705` |
| X-CMD-18 | envoi : date promise antérieure à la date d'envoi | 422 | `f"La livraison prévue ({prevue:%d/%m/%Y}) précède l'envoi du bon ({jour:%d/%m/%Y}) : la corriger, ou la vider (date d'envoi + délai du fournisseur)."` | `ACH:506-510` |
| X-CMD-19 | envoi : date d'envoi interdite | 422 | D1, D2, D3 (§ 0.5) | `ACH:504` |
| X-CMD-20 | approbation d'un bon qui n'est pas à approuver | 409 | `"Ce bon n'attend pas d'approbation."` | `ACH:725-726` |
| X-CMD-21 | renvoi d'un bon qui n'est pas à approuver | 409 | `"Seul un bon qui attend l'approbation se renvoie aux achats."` | `ACH:772-773` |
| X-CMD-22 | renvoi d'un bon parti dont la version partie est inconnue | 409 | `f"Le bon {c.numero} est parti, mais sa version d'alors n'est pas connue : l'approuver, ou demander aux achats de le ramener à ce qui était accepté."` | `ACH:779-783` |
| X-CMD-23 | renvoi : motif de moins de 3 caractères | 422 | Pydantic | `ACH:739-740` |
| X-CMD-24 | confirmation des prix d'un bon annulé | 409 | `"Ce bon est annulé."` | `ACH:815-816` |
| X-CMD-25 | confirmation : ligne d'un autre bon | 422 | `"Ligne étrangère à ce bon."` | `ACH:822-824` |
| X-CMD-26 | expédition d'un bon non parti | 409 | `"Ce bon n'est pas encore parti : son expédition se suit après l'envoi."` | `ACH:872-873` |
| X-CMD-27 | jalon constaté dans le futur | 422 | `f"« {libelle} » ne se date pas dans le futur : c'est un fait constaté. Une date attendue va dans l'arrivée prévue (ETA)."` avec `libelle` ∈ « Proforma reçue le », « Acompte payé le », « Embarquée le », « Arrivée au port le », « Dédouanée le », « Arrivée à l'usine le » | `ACH:858-878` |
| X-CMD-28 | solder un bon déjà clos | 409 | `"Ce bon est déjà clos."` | `ACH:894-895` |
| X-CMD-29 | solder un bon à approuver numéroté | 409 | `f"Le bon {c.numero} attend l'approbation de la direction : elle l'approuve ou le renvoie aux achats (il revient à sa version partie) ; il se solde ensuite."` | `ACH:896-899` |
| X-CMD-30 | solder un bon non parti | 409 | `"Ce bon n'est pas parti : il se supprime, il ne se solde pas."` | `ACH:900-901` |
| X-CMD-31 | rouvrir un bon non clos | 409 | `"Ce bon n'est pas clos."` | `ACH:914-915` |
| X-CMD-32 | supprimer un bon qui a des réceptions | 409 | `"Ce bon a des réceptions : le solder plutôt que le supprimer."` | `ACH:927-928` |
| X-CMD-33 | supprimer un bon parti | 409 | `f"Le bon {c.numero} est parti chez le fournisseur : l'annuler plutôt que le supprimer (il garde son numéro, la série reste sans trou)."` | `ACH:929-931` |

### 2.18 Décisions de Mohamed et des audits (commits)

| Hash | Décision |
|---|---|
| `b6b751c` | Un bon envoyé qui grossit redemande l'approbation ; une réception par devise pour un camion mixte ; bon imprimé complet ; pesées rattachées à leur bon ; lot interne numéroté à la validation ; annulation avec motif. |
| `bcb14b5` | Reçu net des retours ; un retour rouvre un bon soldé de lui-même ; ligne sous réserve ne solde qu'à sa libération ; brouillon attendu de personne ; ponctualité sur la date promise ; « Livré » ligne par ligne ; excédent bloquant ; approbation au montant approuvé mémorisé ; devise de facture refusée plutôt que changée. |
| `d68dbb2` | Un bon parti se lit à son numéro ; approbation au cours figé ; excédent par ligne de bon et sous verrou ; solder un bon à approuver refusé, rouvrir repasse par le garde-fou ; bon parti renvoyé → version partie (étape de schéma 11) ; date promise comptée à l'envoi et figée avec les prix ; réception refusée sur bon annulé ou avant son envoi ; hors commande, la devise se choisit ; annuler une réception recale les soldes. |
| `f85dabd` | Bons à approuver au montant confirmé ou estimé. |
| `dbabfc8`, `2d588b9` | Bon au fournisseur : A4, papier à en-tête, **sans aucun prix ni montant** (écran et Excel), **en anglais**, dates « 08 Oct 2026 », conditionnements traduits, remarques à part. |
| `d2e1e39` | Tout en kilos ; un prix confirmé passe au catalogue au mètre (× densité) si la fiche est au mètre. |
| `final-A` § « Décisions » | On ne reçoit que sur un bon parti ; jalons constatés jamais futurs ; montant engagé = bons partis au prix confirmé, sinon catalogue ; un bon parti ne se supprime plus ; création groupée de bons depuis le plan **abandonnée** (l'acheteur arbitre chaque bon). |

---

## 3. Réceptions

Rôle : toutes les routes de `REC` exigent **achats** (direction comprise).

Principes (docstring `REC:1-17`) : un camion, une ou plusieurs commandes, entières ou
partielles (M40) ; un brouillon se corrige et se supprime (M46) et se **recale** à chaque
lecture (M47) ; la validation écrit tout d'un coup (lots, entrées en stock, prix payés) ; une
ligne « sous réserve » entre en **quarantaine** (en stock, pas disponible) ; une ligne refusée
n'entre pas (le fournisseur la doit toujours) ; une réception **entièrement refusée se valide
quand même** (trace du camion renvoyé : performance, litige) ; on ne reçoit que sur un bon
**parti**, jamais sur un bon annulé, ni avant son envoi — sinon hors commande ; ce qu'une ligne
de bon reçoit se borne au reste à livrer plus l'excédent toléré, **toutes les lignes de la
réception ensemble**, sous verrou ; la facture se complète ou se corrige même après validation.

### 3.1 Modèle

| # | Règle | Référence |
|---|---|---|
| R-RCP-01 | `Reception` : `numero` (unique, **nul** jusqu'à la validation), `statut` ∈ {brouillon, validee, annulee}, `date`, fournisseur, `numero_bl` ≤ 64, `facture_id`, `observations`, `cree_par`, `cree_le`, `validee_par`, `validee_le`, `controle_par` ≤ 80 (qui a contrôlé la qualité au quai). | `MOD:635-656` |
| R-RCP-02 | `ReceptionLigne` : `commande_ligne_id` (facultatif : hors commande sinon), matière, `lot_numero` ≤ 80, `quantite_attendue` (reste à livrer, **recalé**), `quantite_bl`, `quantite_pesee` (kg — **le poids pesé fait foi**), `nb_palettes`, `bobines_en_plus`, `nb_bobines` (= palettes × bobines/palette de la fiche + bobines en plus, exigence M42), `magasin_id`, `qualite` ∈ {conforme, reserve, refuse} (libellés « Conforme », « Sous réserve », « Refusé »), `observations` ≤ 300, `prix`, `devise`, `lot_id` (posé à la validation). Contraintes : pesée, BL, palettes, bobines ≥ 0. | `MOD:659-688`, `REC:44` |
| R-RCP-03 | `Facture` : unique par (fournisseur, numéro) ; date, `montant` ≥ 0, devise (défaut MAD), échéance, `payee_le`. Une facture n'a **qu'une devise**. | `MOD:617-632` |
| R-RCP-04 | **Une réception = une devise** : la devise d'une réception est celle de ses lignes ; un camion qui apporte des bons en deux devises fait **deux réceptions** (même BL, même date), chacune avec **sa** facture (décision « Achats B2 »). | `REC:70-77` ; `final-A` ; commit `b6b751c` ; essai `test_une_reception_ne_mele_pas_deux_devises` |

### 3.2 Lignes : vérifications à la saisie (`_lignes`, création et modification)

Entrée `LigneEntree` : `id`, `commande_ligne_id`, `article_id`, `lot_numero` ≤ 80, `quantite_bl`
0–1e9, `quantite_pesee` 0–1e9, `nb_palettes` 0–1e5, `bobines_en_plus` 0–1e6, `magasin_id`,
`qualite` (défaut conforme), `observations` ≤ 300, `prix` 0–1e7 facultatif (dans l'unité de la
matière), `devise` ≤ 3 (`REC:330-348`).

| # | Règle | Référence |
|---|---|---|
| R-RCP-05 | Matière existante ; qualité ∈ {conforme, reserve, refuse} ; magasin existant s'il est donné. | `REC:395-401` |
| R-RCP-06 | **Sur un bon** : la ligne de bon existe ; le bon est **du fournisseur** de la réception (« une réception ne mêle pas deux fournisseurs ») ; la matière est **celle de la ligne** ; le bon passe `probleme_du_bon` (parti, non annulé, envoyé au plus tard le jour de la réception) ; une devise saisie doit être celle du bon ; devise = **celle du bon** ; prix = celui saisi, sinon le catalogue dans la devise du bon ; **un prix confirmé du bon l'emporte toujours** (s'il est non nul). | `REC:402-420` |
| R-RCP-07 | **Hors commande** : devise = celle saisie, à défaut **celle du fournisseur** de la réception (pas celle de la fiche — « un fil LOMAT en USD acheté chez un fournisseur marocain se paie en MAD »), à défaut MAD ; elle doit exister ; prix = saisi, sinon le catalogue converti dans cette devise. Une matière peut venir d'un autre fournisseur que l'habituel. | `REC:421-429` ; essais `test_hors_commande_la_devise_se_choisit_sur_la_reception`, `test_le_prix_paye_hors_commande_est_retenu` |
| R-RCP-08 | `lot_numero` strip ; `nb_bobines = nb_palettes × bobines_palette (fiche) + bobines_en_plus`. | `REC:430-437` |
| R-RCP-09 | `probleme_du_bon(c, jour)` → texte (vide = imputable) : bon non parti → « le marquer comme envoyé… ou recevoir hors commande » ; bon annulé → « le rouvrir, ou recevoir hors commande » ; réception antérieure à l'envoi du bon → « la date de l'une ou de l'autre est fausse ». Un bon **à approuver numéroté** se reçoit (avertissement, R-RCP-19). | `REC:108-119` ; essais `test_on_ne_recoit_pas_sur_un_bon_qui_n_est_pas_parti`, `test_une_reception_ne_precede_pas_l_envoi_de_son_bon` |

### 3.3 Facture saisie avec la réception (`_facture`)

| # | Règle | Référence |
|---|---|---|
| R-RCP-10 | Sans numéro de facture (vide après strip) : pas de facture. Sinon la facture est **retrouvée** par (fournisseur, numéro) ou **créée**, dans la devise des lignes (à défaut celle saisie, à défaut celle du fournisseur), en majuscules. Date, montant, échéance ne sont écrits **que s'ils sont donnés** (rien n'est effacé) ; sans échéance mais avec une date et un délai de paiement fournisseur > 0 : **échéance = date + délai de paiement** (jours). | `REC:361-387` |

### 3.4 Création, modification, suppression d'un brouillon

Entrée `ReceptionEntree` : `date`, `fournisseur_id`, `numero_bl` ≤ 64, `controle_par` ≤ 80,
`facture` (numéro ≤ 64, date, montant 0–1e10, devise ≤ 3, échéance), `observations` ≤ 2000,
`lignes` ≥ 1 (`REC:322-358`).

| # | Règle | Référence |
|---|---|---|
| R-RCP-11 | Création (`POST /receptions`) : fournisseur existant ; **date pas dans le futur** (la période close n'est contrôlée qu'à la validation — annoncée parmi les blocages) ; lignes vérifiées ; devise unique ; `controle_par` strip ; brouillon **sans numéro** ; recalage ; journal « création réception », détail `f"{réception} · {fournisseur} · {n} ligne(s)"`. | `REC:441-460` |
| R-RCP-12 | Modification (`PUT /receptions/{rid}`) : réception **verrouillée** ; seulement un **brouillon** (une réception validée est entrée en stock : l'annuler puis en saisir une nouvelle) ; mêmes contrôles ; **toutes les lignes remplacées** ; recalage ; journal « modification réception ». | `REC:463-494` ; M46 |
| R-RCP-13 | Suppression (`DELETE /receptions/{rid}`) : seulement un brouillon (une validée s'annule). Journal « suppression réception », détail = « brouillon n° {id} ». | `REC:497-507` |
| R-RCP-14 | `nom_reception` = numéro, sinon `f"brouillon n° {id}"`. | `REC:80-81` |

### 3.5 Recalage d'un brouillon et lecture

| # | Règle | Référence |
|---|---|---|
| R-RCP-15 | **Recalage** (brouillon seulement) : pour chaque ligne sur un bon, `quantite_attendue` = reste à livrer **du moment** = `max(0, quantité − reçu net)`, ramené à 0 si le bon est soldé/annulé ou si le reste ≤ quantité × `toler_in_full` ; si la ligne de bon a un prix confirmé non nul, la ligne prend **ce prix et la devise du bon**. | `REC:84-100` ; M47 |
| R-RCP-16 | `GET /receptions` (achats) : la liste (id décroissant), brouillons recalés **pour l'affichage seulement** — une lecture n'écrit rien (la session se referme sans enregistrer ; la validation recale de nouveau). | `REC:309-319` ; essai `test_lire_les_receptions_n_ecrit_rien` |
| R-RCP-17 | Champs calculés par ligne : bon (nom, id), `quantite_commandee`, `deja_recu` (reçu net par **d'autres** réceptions validées, ≥ 0), `prix_confirme` (bon), `kg_par_ml`, `poids_bobine_catalogue`, `bobines_palette`, `reste_apres` (= attendu − pesée non refusée, ≥ 0), `poids_moyen_bobine` (= pesée ÷ bobines), **écart de pesée** : comparée au **BL** ; sans BL, au reste à livrer **seulement si** la pesée ≥ reste × (1 − `toler_ecart_pesee`) (« une livraison partielle sans BL n'est pas un écart ») ; `ecart` et `ecart_relatif` ; `retourne` (repartis chez le fournisseur). Par réception : devise (de ses lignes, à défaut celle du fournisseur), `delai_paiement_jours`, facture (y compris `payee_le`), `pese` (kg non refusés), `dossier` qui la porte (id, numéro, statut), `annulation` (par, le, motif — lu au journal), `blocages` et `avertissements` (brouillon seulement). | `REC:201-289` ; commit `bcb14b5` ; essai `test_une_livraison_partielle_sans_bl_n_est_pas_un_ecart` |

### 3.6 Ce qui bloque la validation (`blocages`) et ce qui avertit

La **même liste** sert à l'écran (annoncée sur le brouillon) et à la validation (refus avec
**le premier** message, code 422) ; doublons retirés (`REC:122-179`, `REC:535-537`).

| # | Condition (pour chaque ligne, sauf mention) | Message exact | Réf. |
|---|---|---|---|
| X-RCP-B1 | date de la réception refusée par `date_permise` | D1/D2/D3 (§ 0.5) | `REC:126-129` |
| X-RCP-B2 | ligne sur un bon qui a un problème (R-RCP-09) | non parti : `f"Le {nom_commande(c)} n'est pas encore parti chez le fournisseur : le marquer comme envoyé (il reçoit son numéro), ou recevoir hors commande."` ; annulé : `f"Le bon {nom_commande(c)} est annulé : le rouvrir, ou recevoir hors commande."` ; antérieure : `f"La réception du {jour:%d/%m/%Y} précède l'envoi du bon {nom_commande(c)} ({c.date_commande:%d/%m/%Y}) : la date de l'une ou de l'autre est fausse."` | `REC:108-119`, `REC:139-146` |
| X-RCP-B3 | ligne non refusée sur un bon sans problème, et **total apporté à cette ligne de bon par toutes les lignes non refusées de la réception** > reste (net, `max(0, quantité − reçu)` — un bon soldé, même à la main, n'en reçoit pas davantage) + quantité × `toler_excedent` + 1e-6 | `f"« {x.article.reference} » : {stock.kg(total)} kg reçus {'(tous lots ensemble) ' if plusieurs else ''}pour {stock.kg(reste)} kg restant à livrer sur {nom_commande(c)} (excédent toléré : {excedent:.0%} de la ligne). Recevoir le surplus sur une ligne hors commande, ou faire corriger le bon."` (kilos à la française, 2 décimales) | `REC:133-162` ; essais `test_deux_lots_sur_une_ligne_de_bon_ne_depassent_pas_l_excedent`, `test_un_excedent_dans_la_tolerance_passe` |
| X-RCP-B4 | un inventaire **ouvert** sur le magasin cible (quarantaine pour une ligne sous réserve) ou sur tous les magasins | `f"L'inventaire {inv.numero} est en cours : les entrées y sont suspendues jusqu'à sa validation."` | `REC:163-168` |
| X-RCP-B5 | ligne non refusée à pesée ≤ 0 | `f"« {ref} » : la pesée est à zéro. La saisir, ou marquer la ligne « refusé »."` | `REC:169-170` |
| X-RCP-B6 | ligne non refusée sans numéro de lot | `f"« {ref} » : le numéro de lot manque (celui de l'étiquette, ou « Lot interne »)."` | `REC:171-172` |
| X-RCP-B7 | ligne sous réserve et **aucun magasin Quarantaine actif** | `"Une ligne sous réserve va en quarantaine : créer d'abord un magasin de type « Quarantaine » (Réglages › Magasins)."` | `REC:173-176` |
| X-RCP-B8 | ligne conforme sans magasin | `f"« {ref} » : choisir le magasin de rangement."` | `REC:177-178` |

Les lignes **refusées** ne sont soumises qu'à X-RCP-B1/B2 (pas de pesée, de lot ni de magasin
exigés). Avertissements (non bloquants, `REC:182-198`) :

| # | Condition | Message exact | Réf. |
|---|---|---|---|
| A-RCP-01 | ligne sur un bon **soldé** (il n'attend plus rien : la livraison n'entre ni dans sa complétude ni dans l'OTIF) | `f"Le bon {nom_commande(c)} est soldé : il n'attend plus rien. Le rouvrir si le fournisseur le complète vraiment, sinon recevoir hors commande."` | `REC:191-193` ; essai `test_recevoir_sur_un_bon_solde_avertit` |
| A-RCP-02 | ligne sur un bon numéroté au statut à approuver (ou brouillon) | `f"Le bon {nom_commande(c)} est parti, mais une modification attend l'approbation de la direction : la réception s'impute à ses lignes d'aujourd'hui. Si elle la refuse, le bon revient à sa version partie."` | `REC:194-197` |

### 3.7 Validation (`POST /receptions/{rid}/valider`)

| # | Règle | Référence |
|---|---|---|
| R-RCP-18 | Réception verrouillée ; seul un brouillon se valide ; `date_permise(date)`. | `REC:514-517` |
| R-RCP-19 | **Verrous des bons** : les bons touchés puis leurs lignes sont verrouillés **dans l'ordre des id** (pas d'étreinte entre deux postes), puis relus — deux réceptions validées ensemble sur la même ligne passent l'une après l'autre et la seconde voit la première (« deux postes ne franchissent pas la borne à deux »). | `REC:518-532` ; commit `d68dbb2` ; essai `test_deux_postes_ne_franchissent_pas_l_excedent_a_deux` |
| R-RCP-20 | Recalage, puis `blocages` : le premier est renvoyé (422). | `REC:533-537` |
| R-RCP-21 | Lignes **sous réserve** → magasin = la **quarantaine** (premier magasin actif de type Quarantaine, par id). | `REC:103-105`, `REC:538-540` |
| R-RCP-22 | **Lot interne** : une ligne non refusée dont le lot (strip, majuscules) vaut « LOT INTERNE » reçoit à la validation le numéro `LOT-AAAA-NNNN` (année de la **date de réception**) : le compteur `LOT` **rattrape d'abord le plus grand numéro `LOT-AAAA-…` déjà en base** (reprise de l'ERP Fil), sous verrou ; « pas avant : un brouillon supprimé ou une ligne refusée ne laisse pas de trou ». | `REC:45-67`, `REC:541-542` ; commit `b6b751c` ; essai `test_le_lot_interne_est_numerote_a_la_validation` |
| R-RCP-23 | Numéro de réception `REC-AAAA-NNNN` (année de la date de réception), donné **à la validation** (M65). | `REC:543` |
| R-RCP-24 | Pour chaque ligne **non refusée** : lot trouvé ou créé par (matière, numéro) — `lot_ou_creer` (numéro strip, création `INSERT … ON CONFLICT DO NOTHING`, date d'entrée = date de réception, fournisseur ; un lot existant prend le fournisseur s'il n'en avait pas et le **poids de bobine mesuré** = pesée ÷ bobines s'il est connu) ; **mouvement** `RECEPTION` (magasin, quantité pesée, date de réception, document `reception`, id, numéro, auteur, prix et devise de la ligne, commentaire « sous réserve » s'il y a lieu) avec le **cours figé du bon** si le bon est dans la devise de la ligne et a un cours, sinon le cours du jour, **figé sur le mouvement** ; `lot_id` posé sur la ligne. | `REC:544-562`, `STK:35-60`, `STK:122-212` ; commit `5ca0960` |
| R-RCP-25 | Statut `validee`, `validee_par`, `validee_le` ; **soldes des bons recalés** (raison « réception ») ; journal « validation réception », détail `f"{numéro} · {n} entrée(s)"` ou `f"{numéro} · tout refusé, rien n'entre en stock"`. Une réception **toute refusée** est numérotée et validée sans écriture de stock. | `REC:563-574` ; essai `test_une_reception_toute_refusee_reste_une_trace` |
| R-RCP-26 | Refus portés par l'écriture de stock (`ecrire`, § 3.11) : quantité nulle, date, magasin inconnu ou **désactivé** (il ne reçoit plus rien), inventaire ouvert. | `STK:146-168` |

### 3.8 Annulation (`POST /receptions/{rid}/annuler`, corps facultatif `{motif ≤ 300}`)

| # | Règle | Référence |
|---|---|---|
| R-RCP-27 | Seule une réception **validée** s'annule (un brouillon se supprime). Si une de ses lignes est dans un **dossier d'importation**, refus : il faut d'abord **l'en détacher** (après avoir rouvert le dossier s'il est clos) — ses frais restent au dossier. | `REC:292-306`, `REC:586-591` ; commit `6f3a340` ; essai `test_annuler_une_reception_d_un_dossier_passe_par_detacher` |
| R-RCP-28 | **Contre-passation** de chacun de ses mouvements non encore annulés : écriture inverse **datée comme l'original** (date d'effet d'origine), même prix, devise et **cours**, commentaire `f"Annulation du mouvement n°{id}"`, `contrepasse_id` ; les sorties d'abord, les entrées en dernier ; une seule fois. Si la matière n'est plus là, l'écriture négative est refusée (§ 3.11). | `STK:230-270` ; cahier § 5.2 |
| R-RCP-29 | Statut `annulee` ; soldes des bons **recalés** (raison « réception annulée » : un bon soldé de lui-même et plus livré se rouvre ; soldé à la main, il le reste) ; journal « annulation réception », détail `f"{réception} · {motif}"`, motif « sans motif » par défaut — relu pour afficher « annulée par … le … — motif ». Une réception annulée n'a rien livré : ni pesée, ni OTIF, ni prix pour le moteur. | `REC:592-601`, `DEP:375-377` ; essais `test_l_annulation_dit_qui_quand_et_pourquoi`, `test_annuler_une_reception_recale_le_bon_sans_le_contredire` |

### 3.9 Facture complétée après coup (`PUT /receptions/{rid}/facture`)

Entrée `FactureComplete` : numéro ≤ 64, date, montant 0–1e10, devise ≤ 3, échéance — « chaque
champ **remplace** l'ancien » (`REC:604-611`).

| # | Règle | Référence |
|---|---|---|
| R-RCP-30 | La facture arrive souvent après la marchandise : elle se complète ou se corrige sur une réception (brouillon ou validée), **sans toucher au stock** ; refusé sur une réception annulée. Réception verrouillée. | `REC:614-621` ; essai `test_la_facture_se_complete_apres_la_validation` |
| R-RCP-31 | Si la réception a déjà une facture et que le **numéro change** (y compris vidé) alors qu'une de ses lignes est dans un dossier d'importation : refus — « la date, le montant et l'échéance se corrigent ici ; son numéro, non » (détacher d'abord). | `REC:622-627` |
| R-RCP-32 | L'échéance ne précède pas la date de la facture. Numéro vide ⇒ **facture détachée** de la réception (journal « facture détachée »). | `REC:628-634` |
| R-RCP-33 | Sinon : facture retrouvée par (fournisseur, numéro) ou créée ; devise = saisie, sinon celle de la facture, sinon celle du fournisseur, en majuscules ; elle doit égaler la devise **unique** des lignes et exister ; une facture qui **porte d'autres réceptions** ne change pas de devise. Date et montant **remplacés** (peuvent être vidés) ; échéance = saisie, sinon date + délai de paiement du fournisseur, sinon vide. Journal « facture complétée », détail `f"{réception} · facture {numéro}"` + `f" · {montant:,.2f} {devise}"` (milliers séparés par une espace) si montant. | `REC:635-662` ; commit `bcb14b5` (« devise de facture refusée plutôt que changée ») |

### 3.10 Autres routes

| # | Règle | Référence |
|---|---|---|
| R-RCP-34 | `POST /lots/numero-interne` (achats) : réserve et **renvoie immédiatement** un numéro de lot interne (année du jour) — route antérieure à la règle « numéroté à la validation » (voir § 6). | `REC:665-670` |
| R-RCP-35 | `GET /factures` (achats) : toutes les factures (id décroissant) : fournisseur, numéro, date, montant, devise, échéance, réglée le. | `REC:673-682` |
| R-RCP-36 | « Tout valider » (`POST /brouillons/valider`, rôle `STOCK`) et la liste `GET /brouillons` ne portent **que** sur les ordres de fabrication et les opérations de stock en brouillon (ouverture, transfert, ajustement, retour machine, retour fournisseur), **pas sur les réceptions**. Ordre : par date, puis rang (ouverture 0, transfert 1, ajustement 2, ordre 3, retour machine 4, retour fournisseur 5), puis id ; chacun dans **sa propre transaction** (un refus n'empêche pas les autres ; la raison est celle d'une validation à l'unité ; une panne inattendue devient « erreur inattendue : … ») ; seulement ce que le compte peut valider (direction tout ; ordre : alimentation ; opérations : `operations.QUI`). | `BRO:1-125`, `gestion_mp/api/operations.py:29-35` |

### 3.11 Écriture du stock : refus du service `STK` rencontrés par réceptions et dossiers

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-STK-01 | numéro de lot vide | 422 | `"Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne »."` | `STK:43-45` |
| X-STK-02 | quantité nulle (< 1e-9) | 422 | `"Une écriture de stock ne peut pas être nulle."` | `STK:146-147` |
| X-STK-03 | date interdite | 422 | D1/D2/D3 | `STK:148` |
| X-STK-04 | magasin inconnu | 422 | `"Magasin inconnu."` | `STK:149-151` |
| X-STK-05 | entrée dans un magasin désactivé | 422 | `f"Le magasin « {magasin.code} » est désactivé : il ne reçoit plus rien."` | `STK:152-153` |
| X-STK-06 | inventaire ouvert sur ce magasin ou sur tous (sauf écriture d'inventaire) | 409 | `f"L'inventaire {ouvert.numero} est en cours sur « {magasin.code} » : les mouvements y sont suspendus jusqu'à sa validation."` | `STK:157-168` |
| X-STK-07 | le solde (verrouillé) passerait sous −0,001 kg | 409 | `f"Le lot « {lot.numero} » de « {lot.article.reference} » ne porte que {kg(solde.quantite, 3)} kg dans « {magasin.code} », {kg(-quantite, 3)} kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là."` | `STK:169-178` |
| X-STK-08 | sortie datée avant l'entrée du lot dans ce magasin (ou lot jamais entré) | 409 | `f"Le lot {ref} {quand} : une écriture datée du {jour:%d/%m/%Y} ne peut pas le prendre. La dater au jour où la matière était là, ou choisir un lot présent à cette date."` avec `ref = f"« {lot.numero} » de « {référence} »"`, `quand` = `f"n'est entré dans « {code} » que le {entree:%d/%m/%Y}"` ou `f"n'est jamais entré dans « {code} »"` | `STK:77-111` |
| X-STK-09 | le stock du lot passerait sous zéro à une date ≥ la date de l'écriture | 409 | `f"Au {date_manque:%d/%m/%Y}, il n'y avait que {kg(max(disponible, 0.0))} kg du lot {ref} dans « {magasin.code} », {kg(-quantite)} kg demandés au {jour:%d/%m/%Y}"` + `" : la matière est sortie depuis par d'autres écritures."` (si manque postérieur) ou `"."` + `" Choisir un autre lot, ou dater l'écriture après l'entrée de la matière."` | `STK:112-119` |
| X-STK-10 | contre-passation d'un document dont tous les mouvements sont déjà annulés (ou qui n'en a aucun) | 409 | `"Ce document a déjà été annulé."` | `STK:249-251` |

Effets : solde verrouillé par `SELECT … FOR UPDATE` (créé à 0 au besoin), arrondi à 1e-6, ramené à
0 sous 1 g ; cours écrit sur le mouvement (MAD ou prix nul → cours 0 ; sinon cours fourni, à
défaut celui du jour) (`STK:63-74`, `STK:181-212`).

### 3.12 Refus des réceptions (hors blocages)

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-RCP-01 | lignes en deux devises | 422 | `f"Une réception ne mêle pas deux devises ({', '.join(devises)}) : chaque devise a sa facture. Enregistrer une réception par devise (même BL, même date)."` | `REC:73-76` |
| X-RCP-02 | facture saisie dans une autre devise que les lignes | 422 | `f"Cette réception est en {devise} : sa facture aussi. Une facture en {e.devise.upper()} va sur la réception de cette devise."` | `REC:367-369` |
| X-RCP-03 | facture existante d'une autre devise | 422 | `f"La facture {f.numero} est en {f.devise} ; cette réception est en {devise}. Une facture n'a qu'une devise : saisir la facture de cette devise."` | `REC:374-376` |
| X-RCP-04 | matière inconnue | 422 | `"Matière inconnue dans la réception."` | `REC:396-397` |
| X-RCP-05 | qualité invalide | 422 | `"Qualité : conforme, réserve ou refusé."` | `REC:398-399` |
| X-RCP-06 | magasin inconnu | 422 | `"Magasin inconnu."` | `REC:400-401` |
| X-RCP-07 | ligne de bon inconnue | 422 | `"Ligne de commande inconnue."` | `REC:403-405` |
| X-RCP-08 | bon d'un autre fournisseur | 422 | `f"La commande {nom_commande(c)} n'est pas de {f.nom} : une réception ne mêle pas deux fournisseurs."` | `REC:407-409` |
| X-RCP-09 | matière différente de celle de la ligne de bon | 422 | `f"« {a.reference} » n'est pas sur la ligne choisie de {nom_commande(c)}."` | `REC:410-411` |
| X-RCP-10 | bon non imputable (R-RCP-09) — **dès la saisie** | 422 | message de X-RCP-B2 | `REC:412-414` |
| X-RCP-11 | devise saisie ≠ devise du bon | 422 | `f"Le bon {nom_commande(c)} est en {c.devise} : sa réception aussi."` | `REC:415-416` |
| X-RCP-12 | hors commande, devise inconnue | 422 | `f"Devise inconnue : {devise}."` | `REC:426-427` |
| X-RCP-13 | création/modification : fournisseur inconnu | 422 | `"Fournisseur inconnu."` | `REC:445-446`, `REC:478-479` |
| X-RCP-14 | création/modification : date future | 422 | `"Une réception ne se date pas dans le futur."` | `REC:447-448`, `REC:480-481` |
| X-RCP-15 | réception inconnue | 404 | `"Réception introuvable."` | `REC:463-467` |
| X-RCP-16 | modification d'une réception non brouillon | 409 | `"Une réception validée est entrée en stock : elle ne se modifie plus. L'annuler (elle se contre-passe), puis en saisir une nouvelle."` | `REC:474-476` |
| X-RCP-17 | suppression d'une réception non brouillon | 409 | `"Une réception validée ne se supprime pas : l'annuler."` | `REC:501-502` |
| X-RCP-18 | validation d'une réception non brouillon | 409 | `"Cette réception est déjà validée."` | `REC:515-516` |
| X-RCP-19 | validation : date interdite | 422 | D1/D2/D3 | `REC:517` |
| X-RCP-20 | validation : au moins un blocage | 422 | le **premier** message de § 3.6 | `REC:535-537` |
| X-RCP-21 | annulation d'une réception non validée | 409 | `"Seule une réception validée s'annule ; un brouillon se supprime."` | `REC:587-588` |
| X-RCP-22 | annulation d'une réception portée par un dossier | 409 | `f"Cette réception est dans le dossier d'importation {d.numero} : pour l'annuler, {rouvrir}l'en détacher d'abord (dossier {d.numero} › Marchandises › « Détacher la réception ») — ses frais restent au dossier, et la marchandise y reviendra par sa facture."` avec `rouvrir = "le rouvrir (c'est tracé), puis "` si le dossier est clos, sinon « » | `REC:300-306`, `REC:589-591` |
| X-RCP-23 | facture d'une réception annulée | 409 | `"Cette réception est annulée : sa facture ne se modifie plus."` | `REC:620-621` |
| X-RCP-24 | changement du numéro de facture d'une réception en dossier | 409 | `f"La date, le montant et l'échéance de la facture {r.facture.numero} se corrigent ici ; son numéro, non. " + _detacher_d_abord(dossier, "changer le numéro")` | `REC:623-627` |
| X-RCP-25 | échéance avant la date | 422 | `"L'échéance ne précède pas la date de la facture."` | `REC:628-629` |
| X-RCP-26 | devise de facture ≠ devise unique des lignes | 422 | `f"Cette réception est en {devise_lignes[0]} : sa facture aussi. Une facture en {devise} va sur la réception de cette devise."` | `REC:641-644` |
| X-RCP-27 | devise de facture inconnue | 422 | `f"Devise inconnue : {devise}."` | `REC:645-646` |
| X-RCP-28 | changer la devise d'une facture qui porte d'autres réceptions | 409 | `f"La facture {f.numero} est en {f.devise} et porte d'autres réceptions : elle ne change pas de devise."` | `REC:647-651` |

### 3.13 Décisions (commits et conformité)

| Hash / source | Décision |
|---|---|
| `b6b751c` | Une réception par devise pour un camion mixte ; pesées rattachées à leur bon ; lot interne numéroté à la validation ; annulation avec motif. |
| `6143421` | Camion de plusieurs bons : **chaque pesée garde son bon** ; la réception n'est **à l'heure que si chacun de ses bons l'est** (moteur `performance_receptions`, `MOT:2671-2700` ; essais `tests/test_camion_plusieurs_bons.py`). |
| `bcb14b5` | Excédent au-delà de la tolérance bloquant ; livraison partielle sans BL pas un écart ; réception qui ne devait rien hors de l'OTIF ; recevoir sur un bon soldé avertit. |
| `d68dbb2` | Excédent par ligne de bon, toutes lignes ensemble, sous verrou ; refus sur bon annulé ou avant envoi ; devise hors commande choisie ; annulation qui recale les soldes. |
| `6f3a340` | Une réception dans un dossier ne s'annule pas et ne change pas de n° de facture : on la **détache** d'abord (frais gardés). |
| `final-A` | On ne reçoit que sur un bon parti ; réception entièrement refusée validée comme trace ; pesée palette par palette (brut/tare/net) **non retenue** (cahier § 10) ; statut du lot **calculé**, pas saisi. |

---

## 4. Importations (dossiers d'importation et coût de revient)

Rôle : toutes les routes de `IMP` et de `ANA` exigent **achats** (direction comprise) ;
l'alimentation reçoit 403 (`final-B` « Rôles »). Les postes de frais et codes douaniers sont au
§ 1.12-1.13.

Principes (docstring `IMP:1-31`, `MOD:870-876`) : **un dossier = une facture** (décision de
Mohamed, 8 octobre 2026, cahier § 5.5) — une commande arrive souvent en plusieurs fois et c'est à
chaque livraison qu'on paie droits, fret, transitaire ; le dossier s'ouvre **depuis la facture
d'une réception validée** et en prend **toute** la marchandise ; une facture n'a qu'un dossier
(un second camion de la même facture **rejoint** le sien) ; une réception sans facture attend
qu'on la saisisse ; seul un dossier **d'avant la mise en service** se saisit à la main, sans
facture ; un dossier repris de l'ERP Fil peut mêler plusieurs factures et garde chacune.
Une marchandise reçue ne sort d'un dossier qu'avec **toute sa réception** (« détacher ») et ses
frais **restent** au dossier. Les frais se répartissent selon la clé de leur poste (valeur par
défaut, poids en option) ; la TVA, récupérable, reste **hors du coût** ; le coût hors TVA de
chaque lot nourrit le coût moyen du stock. La marchandise entre au dossier à sa **pesée × son
prix** (ce qui est entré en stock, au prix convenu), pas au montant de la facture ; son poids se
fige à l'entrée.

### 4.1 Modèle

| # | Règle | Référence |
|---|---|---|
| R-IMP-01 | `Dossier` : `numero` unique ≤ 16 (« NN/AA »), `libelle` ≤ 160, `date_arrivee`, `banque` ≤ 32, `statut` ∈ {ouvert, clos}, `clos_le`, `commentaire`, `facture_id` (**unique** : une facture, un dossier ; nul pour un dossier saisi à la main ou repris). | `MOD:870-895` |
| R-IMP-02 | `DossierLigne` (une marchandise) : `reception_ligne_id` (**unique** : une ligne de réception n'est que dans un dossier ; nul pour une saisie à la main), matière, lot, fournisseur, `quantite` (kg), `valeur_devise` (≥ 0), `devise`, `cours` (≥ 0 ; **0 = cours du jour** de la devise), commentaire ≤ 300, `poids_kg` (figé ; vide = la quantité). | `MOD:898-925` |
| R-IMP-03 | `DossierCharge` (un frais, en **dirhams**) : poste, `montant` (négatif = **avoir**), `ligne_id` (frais visé sur une seule marchandise ; nul = global), `piece` ≤ 64, `commentaire` ≤ 300, `prestataire` ≤ 120, `date_piece`, `echeance`, `payee_le` ; `parts` = répartition **figée** (`DossierChargePart` : (frais, ligne) → montant). | `MOD:928-962` |

### 4.2 Lecture d'un dossier (`GET /dossiers`, `GET /dossiers/{did}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-04 | Liste triée par date d'arrivée décroissante (vides en dernier) puis id décroissant, sans le détail ; fiche complète avec lignes, frais et échéancier. | `IMP:388-406` |
| R-IMP-05 | **Coût de revient** de chaque marchandise par le moteur (§ 4.13) ; totaux du dossier : `marchandise_mad` (Σ valeur MAD), `charges_mad` = Σ frais hors TVA **répartis**, `tva_mad` = Σ TVA répartie, `tva_saisie_mad` = Σ du seul poste **TVA** (celui comparé à l'attendue : une TVA sur la facture du transitaire n'est pas celle de la douane), `revient_mad` = marchandise + charges, `decaisse_mad` = + TVA, `surcout` = charges ÷ marchandise, `poids` (Σ kg). | `IMP:190-209`, `IMP:287-309` |
| R-IMP-06 | **Frais non répartis** : un frais qui ne trouve pas de marchandise (dossier vide, repris tel quel) n'entre dans **aucun coût** : il se montre à part (`charges_non_reparties_mad`, `tva_non_repartie_mad`, au-delà de 0,005) pour que les totaux s'accordent avec l'analyse. | `IMP:204-207` ; commit `bb1109d` ; essai `test_frais_sans_marchandise_a_part_partout` |
| R-IMP-07 | Par ligne : famille de fil (« PP Frisé 2900 Dtex » : composition, libellé du type sans parenthèse, titrage — **sans la couleur** ; à défaut libellé de la composition ou la référence ; exigence M56), lot, fournisseur, réception, facture, quantité, poids, valeur devise, devise, `cours`, `cours_applique` (1 pour MAD, sinon cours de la ligne ou du jour), `cours_jour`, `cours_bon` (cours figé du bon de la ligne, s'il est dans la même devise), `bon`, valeur MAD, part, charges, TVA, revient, revient/kg, `aberrante`, `negative`, commentaire, code douanier et taux, **valeur en douane** (marchandise + sa part de FRET et ASSUR), **droits attendus** (valeur en douane × taux). | `IMP:58-71`, `IMP:225-283` |
| R-IMP-08 | **Droits attendus** du dossier : seulement si **toutes** les matières ont un code douanier **actif** (des droits partiels ne se comparent pas aux droits payés pour tout le dossier) ; sinon `null` et la liste `matieres_sans_code` (+ `matieres_code_inactif`). `droits_mad` = Σ du poste DD. | `IMP:245-254`, `IMP:284`, `IMP:302-307` ; commit `6f3a340` |
| R-IMP-09 | **TVA attendue** (contrôle C29) : `null` sans marchandise ; sinon `taux_tva_import × (valeur en douane + droits DD + TPI)` où valeur en douane = Σ marchandises en MAD + FRET + ASSUR, et TPI = Σ du poste TPI s'il est saisi, sinon valeur en douane × `taux_tpi_import`. Écart toléré = 5 % de l'attendue (`TOLERANCE_TVA_IMPORT`, « au-delà, une erreur de saisie ; en deçà, les écarts de cours de la douane »). | `IMP:286`, `IMP:298-300`, `MOT:3572-3608` ; commit `6f3a340` |
| R-IMP-10 | **Frais aberrants** (contrôle C35) : dossier aberrant si marchandise > 0 et charges réparties > marchandise × `seuil_surcout_import` ; **ligne** aberrante si ses charges > 0,005 et (valeur ≤ 0 ou charges > valeur × seuil) — un frais visé sur une seule ligne peut la rendre aberrante sans que le dossier le paraisse. **Ligne négative** : revient < −0,005 (un avoir). | `IMP:222-224`, `IMP:310-316`, `MOT:3689-3700` ; commit `58f507c` |
| R-IMP-11 | **Écart facture** (contrôle C36) : la facture du dossier rapprochée de la marchandise reçue (Σ `valeur_devise` = pesée × prix) ; rien sans montant de facture, sans marchandise, ou si une ligne n'est pas dans la devise de la facture ; `ecart` = facture − reçu, `part` = écart ÷ reçu (1 si reçu nul), `hors_tolerance` si |écart| > 0,005 et |part| > `toler_facture_import`. La valorisation **reste à la pesée × prix** (question ouverte n° 4 de l'audit). | `IMP:317-319`, `MOT:3703-3721` ; commit `58f507c` |
| R-IMP-12 | `lignes_cours_bon` = nombre de lignes en devise dont le cours est **exactement** le cours figé de leur bon (la clôture ne les touche pas) ; `cours_disparates` = devises à plusieurs cours dans le dossier (second camion après une première clôture, cours saisi sur une seule ligne), à dire avant de clore. | `IMP:255-260`, `IMP:320-326` |
| R-IMP-13 | `a_la_main` = pas de facture ; `fournisseurs`, `factures`, `receptions`, `pieces` (facture → réceptions), `familles` (lignes regroupées par famille, triées par poids décroissant, avec valeur et revient par kg). | `IMP:292-293`, `IMP:328-338` |
| R-IMP-14 | **Échéancier du dossier** : une ligne par facture de marchandise (montant saisi, à défaut ce que sa marchandise au dossier a apporté — `estime`), une par frais (en MAD, avec prestataire, pièce, échéance, réglé le) ; tri : échéance croissante, sans échéance en dernier, puis libellé. | `IMP:364-385` ; commit `58f507c` |

### 4.3 Ce qui attend son dossier (`GET /dossiers-a-rattacher?locaux=`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-15 | **Ligne libre** = ligne de réception **validée**, non refusée, pesée > 0, qui n'est dans **aucun** dossier ; triées par date de réception décroissante. | `IMP:409-433` |
| R-IMP-16 | Un **fournisseur marocain** n'a pas de dossier d'importation (ni douane, ni fret international) : pays (strip, majuscules) ∈ {MAROC, MOROCCO, MA}, **ou** pays vide et devise du fournisseur MAD (vide = MAD). Ses lignes sont **écartées** (comptées dans `locaux` : factures, lignes), sauf `locaux=true`. | `IMP:109-113`, `IMP:456-462` ; commit `bb1109d` ; essai `test_les_fournisseurs_marocains_n_ont_pas_de_dossier` |
| R-IMP-17 | Regroupements : `factures` (par facture : réceptions, nombre de lignes, kilos, **valeurs par devise** — jamais un total qui mêle deux devises —, familles, et le **dossier qui la porte déjà** s'il y en a un : la suite y rentre) ; `sans_facture` (par réception : la facture se saisit sur la réception, puis ouvre son dossier) ; `lignes` (toutes, avec `valeur_devise = pesée × prix`). | `IMP:436-509` |
| R-IMP-18 | **Porteurs d'une facture** : d'abord le dossier dont c'est **la** facture (`facture_id`), puis les dossiers (repris de l'ERP Fil, sans facture) qui portent déjà une marchandise de cette facture. | `IMP:146-166` |

### 4.4 Ouverture d'un dossier (`POST /dossiers`)

Entrée `DossierEntree` : `numero` ≤ 16 (facultatif : un dossier d'avant la mise en service garde
son vrai numéro), `libelle` ≤ 160, `date_arrivee` (année **2000–2100**, sinon 422 « date
d'arrivée hors période »), `banque` ≤ 32, `commentaire` ≤ 2000, `facture_id`, `local_confirme`
(défaut faux) (`IMP:512-529`).

| # | Règle | Référence |
|---|---|---|
| R-IMP-19 | **Depuis une facture** : elle doit exister ; elle ne doit être portée par **aucun** dossier (le sien ou un repris) ; un fournisseur marocain **se confirme** (`local_confirme`) ; le dossier prend **toute** la marchandise libre de la facture (réceptions **verrouillées en partage** jusqu'à l'enregistrement) — refus s'il n'en reste pas. | `IMP:596-609`, `IMP:549-557` ; commits `8116063`, `6f3a340` |
| R-IMP-20 | **Sans facture** (saisi à la main) : dossier vide, à remplir ligne par ligne (§ 4.7). Aucune condition de date « d'avant la mise en service » n'est contrôlée. | `IMP:609-616` |
| R-IMP-21 | Période close : les dates des réceptions rattachées ne doivent pas être dans la période close (geste « ouverture du dossier »). | `IMP:610` |
| R-IMP-22 | Date d'arrivée = saisie, sinon la **plus ancienne** date de réception rattachée, sinon aujourd'hui. Libellé = saisi (strip), sinon `f"{fournisseur} — facture {numéro}"` quand il y a de la marchandise. Banque, commentaire strip. | `IMP:611-616` |
| R-IMP-23 | **Numéro** : saisi (strip) → doit être libre ; sinon série `DOS` de l'**année d'arrivée** (« NN/AA »), en **sautant** les numéros déjà pris à la main. | `IMP:560-570` ; décision « les dossiers ont leur numéro dès l'ouverture » (`final-B`) |
| R-IMP-24 | Chaque ligne rattachée (`_rattacher`) : `quantite = poids_kg = pesée`, `valeur_devise = pesée × prix` de la ligne de réception, devise de la ligne, **cours = cours figé de son bon** (si le bon est dans la même devise, non MAD, cours > 0), sinon 0 (cours du jour) — « c'est le cours convenu ; le cours payé à la banque le remplacera » ; lot, fournisseur de la réception. | `IMP:532-546`, `IMP:116-128` ; commit `bb1109d` ; essai `test_deux_devises_un_cours_chacune_et_cours_du_bon` |
| R-IMP-25 | Journal « ouverture dossier », détail `f"{numéro} · {n} ligne(s)"` + `f" · facture {numéro facture}"` ou `" · saisi à la main"` + `" · fournisseur marocain, confirmé"` s'il y a lieu. | `IMP:624-627` |
| R-IMP-26 | **Concurrence** : deux postes qui ouvrent ensemble le dossier d'une même facture (ou rattachent la même ligne) — le premier l'emporte (index uniques), l'autre reçoit un **409 clair** qui nomme le dossier gagnant, pas une erreur 500. | `IMP:573-590`, `IMP:617-623` ; commit `6f3a340` ; essai `test_trois_creations_simultanees_un_seul_dossier` |

### 4.5 En-tête (`PUT /dossiers/{did}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-27 | Dossier **ouvert** seulement, verrouillé (`_ouvert`). Libellé, banque, commentaire remplacés (strip) ; date d'arrivée seulement si donnée. Le numéro et la facture **ne changent pas** par cette route. Journal « modification dossier ». | `IMP:632-650` |

### 4.6 Rattacher (`POST /dossiers/{did}/rattacher`, corps `{facture_id, reception_lignes[]}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-28 | Factures acceptées : **celle du dossier** ; pour un dossier repris sans facture, **celles qu'il porte déjà** ; un dossier saisi à la main (sans facture ni réception) n'en prend **aucune** (une marchandise reçue entre par sa facture, dans le dossier de cette facture). | `IMP:662-668` ; essai `test_un_second_camion_de_la_meme_facture_rejoint_son_dossier` |
| R-IMP-29 | `facture_id` donné : toute sa marchandise libre (sous verrou partagé). `reception_lignes` : chaque ligne doit être libre et d'une facture acceptée (les doublons avec la facture sont ignorés). | `IMP:669-693` |
| R-IMP-30 | Période close (geste « rattachement », dates des réceptions à rattacher), puis rattachement (R-IMP-24). Journal « marchandises dossier », détail `f"{numéro} · {n} ligne(s)"` + `f" · plusieurs cours : {EUR à 10.9 et 11.0, …}"` si des cours disparates en résultent (« un second camion arrivé après une première clôture … ne prend pas en silence un cours différent »). | `IMP:696-711` |

### 4.7 Ligne saisie à la main (`POST /dossiers/{did}/ligne-manuelle`)

Entrée `LigneManuelle` : `article_id`, `lot_numero` ≤ 80, `fournisseur_id`, `quantite` > 0 ≤ 1e9,
`valeur_devise` 0–1e10, `devise` ≤ 3 (défaut MAD), `cours` 0–1000, `commentaire` ≤ 300
(`IMP:714-724`). Exigence M53 : saisir un dossier ancien après coup, comme un stock initial.

| # | Règle | Référence |
|---|---|---|
| R-IMP-31 | **Réservée aux dossiers d'avant la mise en service** : refusée sur le dossier d'une facture, et sur un dossier qui porte des réceptions (repris de l'ancien ERP : sa marchandise entre par ses factures, telle que reçue). | `IMP:731-739` ; commit `58f507c` ; essai `test_la_saisie_a_la_main_est_reservee_aux_dossiers_d_avant` |
| R-IMP-32 | Un lot **déjà reçu** (réception validée, même matière, même numéro) est refusé : son coût vient du dossier de sa facture (sinon la saisie donnerait son coût à cette réception ou le mêlerait au sien). | `IMP:743-755` ; essai `test_un_lot_saisi_a_la_main_ne_donne_pas_son_cout_a_une_reception` |
| R-IMP-33 | Devise en majuscules, connue ; fournisseur (s'il est donné) connu, à défaut **celui de la matière**. Un **lot inconnu est créé** (sans stock, date d'entrée = date d'arrivée du dossier, à défaut aujourd'hui) : un stock d'ouverture saisi plus tard sous le même numéro prendra le coût de ce dossier. Période close (geste « marchandise saisie à la main », date d'entrée du lot). Ligne : `poids_kg = quantite`, **cours 0 si MAD**, commentaire strip. Journal « marchandise saisie à la main », détail `f"{numéro} · {référence}"` + `f" · lot {lot}"`. | `IMP:756-776` ; essai `test_ligne_a_la_main_lot_inconnu_numero_saisi` |
| R-IMP-34 | Le coût d'une ligne saisie à la main se retrouve **par (référence, lot)** (moyenne au poids si plusieurs) ; celui d'une ligne venue d'une réception **par sa ligne de réception, jamais par son lot** (un numéro de lot qui revient d'une livraison à l'autre ferait prendre à l'une le coût de l'autre). | `MOT:3724-3760` ; commit `5ca0960` |

### 4.8 Cours et commentaire d'une marchandise (`PUT /dossiers/{did}/lignes/{lid}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-35 | Dossier ouvert. `cours` (0–1000) : le cours **réellement payé à la banque** en face de la marchandise ; refusé non nul sur une ligne en MAD (« une marchandise facturée en MAD n'a pas de cours ») ; un cours **changé** passe le contrôle de période close (geste « cours ») ; journal « cours », détail `f"{numéro} · {référence} · {cours}"`. `commentaire` (≤ 300, strip) : journal « commentaire marchandise ». Champs absents = inchangés. | `IMP:779-805` ; essai `test_une_ligne_en_dirhams_n_a_pas_de_cours` |

### 4.9 Un cours pour toute une devise (`PUT /dossiers/{did}/cours`, `{cours 0–1000, devise}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-36 | **Un cours vaut pour une devise** (l'euro et le dollar n'ont jamais le même) : devise saisie (majuscules), sinon la seule devise étrangère du dossier ; refus si le dossier en mêle plusieurs sans devise dite, s'il n'a aucune marchandise en devise, ou si la devise dite n'y est pas. Période close (« cours »). Toutes les lignes de cette devise prennent le cours. Journal « cours », détail `f"{numéro} · {devise} à {cours}"`. | `IMP:808-832` ; commit `bb1109d` (« un cours par devise ») |

### 4.10 Remettre le cours des bons (`POST /dossiers/{did}/cours-des-bons`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-37 | Remet sur chaque ligne (en devise, issue d'une réception dont le bon a un cours figé **dans la même devise**) le cours figé de son bon. Période close (« cours ») contrôlée **avant**. Refus si aucune ligne n'est concernée. Journal « cours », détail `f"{numéro} · cours des bons sur {n} ligne(s)"`. | `IMP:835-850` |

### 4.11 Retirer une marchandise (`DELETE /dossiers/{did}/lignes/{lid}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-38 | Seulement une ligne **saisie à la main** : une marchandise **reçue** ne sort pas seule (elle couperait sa facture ou sa réception en deux) — elle sort avec toute sa réception (« Détacher la réception »), frais gardés. Refus aussi si un frais est **visé sur cette seule marchandise** (il n'aurait plus où se poser : l'affecter à tout le dossier ou le retirer). Période close (« retrait d'une marchandise »). Journal « marchandise retirée », détail `f"{numéro} · {référence}"`. | `IMP:853-880` ; commit `6f3a340` |

### 4.12 Détacher une réception (`POST /dossiers/{did}/detacher`, `{reception_id}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-39 | Toute la marchandise de la réception sort du dossier et **attend de nouveau son dossier** (celui de sa facture, qu'elle rejoindra) ; **les frais restent au dossier** (droits, fret, transit ont été payés pour l'arrivée). C'est **le** chemin pour annuler une réception portée par un dossier ou corriger le numéro de sa facture. Le dossier reste ouvert ; vide, ses frais attendent leur marchandise (il ne se clôt pas ainsi). | `IMP:887-896` ; commit `6f3a340` |
| R-IMP-40 | Dossier ouvert ; réception existante et présente dans le dossier ; refus si un frais vise une de ses marchandises (le reporter sur tout le dossier, onglet Frais « Porte sur ») ; période close (« détachement d'une réception »). Un frais à **répartition figée** qui avait une part sur une ligne sortante **perd toutes ses parts** : il se répartit de nouveau à la clé de son poste. Journal « réception détachée », détail `f"{numéro} · {réception} · {n} ligne(s) · {k} frais gardés ({montant:,.2f} MAD)"` (milliers séparés par une espace). | `IMP:897-925` |

### 4.13 Frais (`POST/PUT/DELETE /dossiers/{did}/charges[/{cid}]`)

Entrée `ChargeEntree` : `poste` ≤ 16, `montant` −1e9…1e9, `ligne_id`, `piece` ≤ 64,
`commentaire` ≤ 300, `prestataire` ≤ 120, `date_piece`, `echeance` (années **2000–2100**, sinon
422 « date hors période ») (`IMP:928-943`).

| # | Règle | Référence |
|---|---|---|
| R-IMP-41 | Dossier ouvert ; poste existant ; **montant non nul** (un **avoir** se saisit en négatif) ; marchandise visée (facultative) **de ce dossier**. Texte (pièce, commentaire, prestataire) strip. Montants **en MAD**. | `IMP:946-975` |
| R-IMP-42 | Ajout, retrait, et modification qui change poste, montant ou marchandise visée : contrôle de la période close (geste « frais »). | `IMP:983`, `IMP:999-1000`, `IMP:1020` |
| R-IMP-43 | Modification : si le frais avait une répartition figée et que son montant change (> 0,005) ou sa marchandise visée change, la **répartition figée est effacée** (le frais suit de nouveau la clé de son poste). Tous les champs sont remplacés. | `IMP:1001-1006` |
| R-IMP-44 | Après ajout, modification ou retrait : **un avoir ne rend aucune marchandise négative** (son revient sous zéro ne voudrait rien dire, et le coût moyen l'ignorerait en silence). | `IMP:956-968` ; commit `58f507c` ; essai `test_frais_aberrant_sur_une_ligne_et_avoir_negatif` |
| R-IMP-45 | Journaux : « frais », « frais modifié », « frais retiré », détail `f"{numéro} · {poste} {montant:,.2f}"` (format **anglais** « 1,234.50 »). | `IMP:986`, `IMP:1008`, `IMP:1023` |

### 4.14 Répartition des frais et coût de revient (moteur)

| # | Règle | Référence |
|---|---|---|
| R-IMP-46 | Valeur MAD d'une marchandise = `valeur_devise` si MAD (un cours porté par erreur est **ignoré**), sinon `valeur_devise × (cours de la ligne, à défaut cours du jour)`. | `MOT:3611-3621` ; commit `6f3a340` |
| R-IMP-47 | Un frais **visé** sur une ligne présente lui revient **entier**. Un frais à **répartition figée** garde ses parts **tant qu'elles portent toutes sur des lignes encore au dossier et couvrent son montant** (à 0,005 près). Sinon le frais est **global** : il se répartit **au prorata de la valeur MAD** de chaque ligne (clé `valeur`) ou **de ses kilos** (clé `poids`). Sans arrondi : la somme des revients retombe sur le total du dossier. | `MOT:3624-3686` ; cahier § 2.7 ; M51 |
| R-IMP-48 | Récupérable (hors coût, compté en TVA) : selon le **référentiel des postes** ; à défaut la liste d'origine (TVA). Revient = valeur + frais non récupérables ; surcoût = frais ÷ valeur ; décaissé = revient + TVA. | `MOT:3640-3643`, `CMO:554-558`, `MOT:3527-3565` |
| R-IMP-49 | Le **coût de revient** d'une marchandise venue d'une réception valorise **son** entrée en stock (CMUP) à ce qu'elle a réellement coûté, non au prix de la facture ; un dossier qui change revalorise les mois **non clos**. | `MOT:3724-3737` ; cahier § 5.5 |
| R-IMP-50 | Le moteur lit le poids d'une ligne comme **sa quantité** (en kg depuis le 8 octobre 2026) ; `DossierLigne.poids_kg` est écrit (rattachement, saisie, clôture) mais n'est **pas transmis** au moteur. | `CMO:575-578`, `IMP:74-95`, `MOD:918-925` |

### 4.15 Clôture (`POST /dossiers/{did}/cloturer`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-51 | **Clore, c'est figer le coût** : dossier ouvert ; au moins une marchandise ; **aucun frais non réparti**. Chaque ligne sans `poids_kg` le reçoit (= quantité) ; chaque ligne **en devise sans cours** prend le **cours du jour**, écrit sur la ligne, et son commentaire reçoit `f"cours du jour {cours:g} figé à la clôture du {JJ/MM/AAAA}"` (ajouté après « · » à l'ancien commentaire tronqué pour tenir en 300) — sinon le coût d'un dossier clos bougerait avec le cours de demain. Une ligne restée **au cours de son bon** le garde (l'écran le dit avant et propose le cours de la banque). Statut `clos`, `clos_le` = maintenant. Journal « clôture dossier », détail `numéro` + `f" · cours du jour figé : {réf à cours, …}"` + `f" · {n} ligne(s) au cours du bon"`. | `IMP:1028-1065` ; commits `6f3a340`, `bb1109d` ; essais `test_cloture_fige_cours_et_cle`, `test_la_cloture_dit_le_cours_du_bon_et_trace_le_cours_fige` |
| R-IMP-52 | La clôture est **permise même sur une marchandise d'une période close** (pas de contrôle § 0.5) : le cours du jour et le poids qui s'y figent sont ceux que le calcul applique déjà — rien ne se revalorise. | `IMP:1047-1050` |
| R-IMP-53 | Les **alertes** de clôture (cours vides, cours à plus de 5 % du cours du jour, plusieurs fournisseurs, aucun droit, droits ≠ attendus, aucune TVA, TVA ≠ attendue) sont posées par **l'écran** à partir de la fiche ; le serveur ne les bloque pas. | `final-B` (« Achats M18 ») ; `IMP:320-326` |

### 4.16 Réouverture (`POST /dossiers/{did}/rouvrir`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-54 | Dossier verrouillé ; seulement un dossier **clos** ; période close (geste « réouverture ») ; statut `ouvert`, `clos_le` vidé. Les cours figés à la clôture **restent** sur les lignes. Journal « réouverture dossier ». | `IMP:1068-1079` |

### 4.17 Suppression (`DELETE /dossiers/{did}`)

| # | Règle | Référence |
|---|---|---|
| R-IMP-55 | Seulement un dossier **ouvert** ; période close (« suppression ») ; **perd ses frais** (l'écran dit combien avant de demander ; pour les garder, détacher la réception) ; sa facture attend de nouveau son dossier ; lignes et frais supprimés en cascade (les lots créés par saisie à la main restent). Journal « suppression dossier », détail `numéro` + `f" · {n} frais perdus ({montant:,.2f} MAD)"` (milliers séparés par une espace). Réponse `{ok, frais_perdus, frais_perdus_mad}`. | `IMP:1082-1093` ; commit `6f3a340` |

### 4.18 Refus des importations

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-IMP-01 | dossier inconnu | 404 | `"Dossier introuvable."` | `IMP:403-405`, `IMP:633-635`, `IMP:1071-1072` |
| X-IMP-02 | geste d'écriture sur un dossier clos | 409 | `"Ce dossier est clos : le rouvrir pour y toucher (c'est tracé)."` | `IMP:636-637` |
| X-IMP-03 | facture inconnue (ouverture, rattachement) | 404 | `"Facture inconnue."` | `IMP:550-552`, `IMP:597-598` |
| X-IMP-04 | facture sans marchandise libre | 409 | `f"La facture « {f.numero} » n'a plus de marchandise à rattacher : elle est déjà dans un dossier, ou ses réceptions ne sont pas validées."` | `IMP:553-556` |
| X-IMP-05 | facture déjà portée par **son** dossier | 409 | `f"Cette facture a déjà son dossier, {num} : un dossier par facture. Ce qui en reste à rattacher (un second camion) s'y ajoute."` | `IMP:180-185`, `IMP:602-604` |
| X-IMP-06 | facture déjà portée par un dossier repris | 409 | `f"La facture {f.numero} est déjà dans le dossier {num} (repris de l'ancien ERP) : une facture ne se partage pas entre deux dossiers. Ce qui en reste à rattacher s'y ajoute."` | `IMP:186-187` |
| X-IMP-07 | fournisseur marocain non confirmé | 409 | `f"{f.fournisseur.nom} est un fournisseur marocain : ni douane, ni fret international, sa facture {f.numero} n'a normalement pas de dossier d'importation. L'ouvrir quand même se confirme."` | `IMP:605-608` |
| X-IMP-08 | numéro de dossier saisi déjà pris | 409 | `f"Le dossier « {voulu} » existe déjà."` | `IMP:562-564` |
| X-IMP-09 | concurrence : un autre poste a enregistré la facture | 409 | `f"Un autre poste vient d'enregistrer cette facture dans le dossier {porteurs[0][1]} : l'ouvrir pour la suite (rien n'est perdu)."` | `IMP:584-588` |
| X-IMP-10 | concurrence : autre conflit d'unicité | 409 | `"Un autre poste vient d'enregistrer la même chose (même numéro de dossier, ou même marchandise) : recharger la page, puis reprendre."` | `IMP:589-590` |
| X-IMP-11 | période close (ouverture, rattachement, saisie à la main, cours, retrait, détachement, frais, réouverture, suppression) | 409 | D4 (§ 0.5) avec le geste nommé | `IMP:610`, `IMP:696`, `IMP:767`, `IMP:798`, `IMP:826`, `IMP:839`, `IMP:876`, `IMP:912`, `IMP:983`, `IMP:1000`, `IMP:1020`, `IMP:1075`, `IMP:1087` |
| X-IMP-12 | rattacher à un dossier saisi à la main | 409 | `"Ce dossier est saisi à la main (d'avant la mise en service) : une marchandise reçue entre par sa facture, dans le dossier de cette facture."` | `IMP:666-668` |
| X-IMP-13 | rattacher une autre facture au dossier d'une facture | 409 | `f"Un dossier, une facture : {d.numero} est celui de la facture {d.facture.numero}. La facture {nom} ouvre son propre dossier."` (`nom` = numéro de l'autre facture, ou « choisie ») | `IMP:669-674` |
| X-IMP-14 | rattacher une facture étrangère à un dossier repris | 409 | `f"Le dossier {d.numero}, repris de l'ancien ERP, ne prend que la suite des factures qu'il porte déjà. La facture {nom} ouvre son propre dossier."` | `IMP:675-676` |
| X-IMP-15 | ligne choisie non libre | 409 | `"Une des lignes choisies est déjà dans un dossier, ou n'est pas une réception validée."` | `IMP:684-686` |
| X-IMP-16 | ligne choisie d'une autre facture | 409 | dossier d'une facture : `f"Un dossier, une facture : cette ligne n'est pas de la facture {d.facture.numero}."` ; dossier repris : `f"Le dossier {d.numero} ne prend que la suite des factures qu'il porte déjà : cette ligne n'en est pas."` | `IMP:687-691` |
| X-IMP-17 | rien à rattacher | 422 | `"Rien à rattacher."` | `IMP:694-695` |
| X-IMP-18 | saisie à la main sur le dossier d'une facture | 409 | `f"Le dossier de la facture {d.facture.numero} porte ce qu'elle a apporté, tel que reçu : la saisie à la main est réservée aux dossiers d'avant la mise en service."` | `IMP:731-733` |
| X-IMP-19 | saisie à la main sur un dossier qui porte des réceptions | 409 | `f"Le dossier {d.numero} porte des réceptions : sa marchandise entre par ses factures, telle que reçue. La saisie à la main est réservée aux dossiers d'avant la mise en service."` | `IMP:734-739` |
| X-IMP-20 | saisie à la main : matière inconnue | 422 | `"Matière inconnue."` | `IMP:741-742` |
| X-IMP-21 | saisie à la main sur un lot déjà reçu | 409 | `f"Le lot « {lot} » de {a.reference} est arrivé par la réception {recu} : son coût vient du dossier de sa facture. La saisie à la main ne vaut que pour un lot d'avant la mise en service."` | `IMP:752-755` |
| X-IMP-22 | saisie à la main : devise inconnue | 422 | `f"Devise inconnue : « {devise} »."` | `IMP:757-758` |
| X-IMP-23 | saisie à la main : fournisseur inconnu | 422 | `"Fournisseur inconnu."` | `IMP:759-760` |
| X-IMP-24 | marchandise inconnue dans ce dossier (modifier, retirer) | 404 | `"Marchandise introuvable dans ce dossier."` | `IMP:792-793`, `IMP:858-859` |
| X-IMP-25 | cours non nul sur une ligne en MAD | 422 | `"Une marchandise facturée en MAD n'a pas de cours."` | `IMP:795-796` |
| X-IMP-26 | cours pour tout : plusieurs devises sans devise dite | 422 | `f"Le dossier mêle {', '.join(sorted(devises))} : donner le cours de chaque devise à part."` | `IMP:821-823` |
| X-IMP-27 | cours pour tout : aucune marchandise en devise | 422 | `"Aucune marchandise en devise dans ce dossier."` | `IMP:822-823` |
| X-IMP-28 | cours pour tout : la devise dite n'y est pas | 422 | `f"Aucune marchandise en {devise} dans ce dossier."` | `IMP:824-825` |
| X-IMP-29 | cours des bons : aucune ligne concernée | 422 | `"Aucune ligne de ce dossier ne vient d'un bon au cours figé."` | `IMP:846-847` |
| X-IMP-30 | retirer une marchandise reçue | 409 | `f"Une marchandise reçue ne sort pas seule du dossier : elle sort avec toute sa réception {reception} (« Détacher la réception »), et les frais restent au dossier."` | `IMP:860-869` |
| X-IMP-31 | retirer une marchandise visée par `n` frais | 409 | `f"{len(lies)} frais porte(nt) sur cette seule marchandise : les affecter à tout le dossier, ou les retirer, avant de la retirer."` | `IMP:872-875` |
| X-IMP-32 | détacher : réception inconnue | 404 | `"Réception inconnue."` | `IMP:898-900` |
| X-IMP-33 | détacher : réception absente du dossier | 404 | `f"La réception {r.numero} n'est pas dans le dossier {d.numero}."` | `IMP:903-904` |
| X-IMP-34 | détacher : `n` frais visent une de ses marchandises | 409 | `f"{len(lies)} frais porte(nt) sur une marchandise de la réception {r.numero} : les affecter à tout le dossier (onglet Frais, « Porte sur ») avant de la détacher — sinon ils sortiraient avec elle."` | `IMP:907-911` |
| X-IMP-35 | frais : poste inconnu | 422 | `f"Poste de frais inconnu : « {e.poste} » (attendu : {connus})."` (codes triés par ordre) | `IMP:947-949` |
| X-IMP-36 | frais à montant nul | 422 | `"Un frais a un montant (un avoir se saisit en négatif)."` | `IMP:950-951` |
| X-IMP-37 | frais visant une marchandise étrangère au dossier | 422 | `"La marchandise visée n'appartient pas à ce dossier."` | `IMP:952-953` |
| X-IMP-38 | frais qui rendrait une marchandise négative | 409 | `f"Ce frais rendrait {x.reference} négatif ({montant} MAD) : un avoir ne dépasse pas ce que la marchandise a coûté. Le porter sur tout le dossier, ou revoir son montant."` (montant « −1 234,00 » à espaces) | `IMP:964-968` |
| X-IMP-39 | frais inconnu dans ce dossier | 404 | `"Frais introuvable dans ce dossier."` | `IMP:996-997`, `IMP:1018-1019` |
| X-IMP-40 | clôture d'un dossier sans marchandise | 422 | `"Un dossier sans marchandise n'a rien à clore."` | `IMP:1038-1039` |
| X-IMP-41 | clôture avec frais non répartis | 409 | `"Des frais ne trouvent pas de marchandise où se répartir : les affecter à tout le dossier, ou les retirer, avant de clore."` | `IMP:1042-1044` |
| X-IMP-42 | réouverture d'un dossier ouvert | 409 | `"Ce dossier est déjà ouvert."` | `IMP:1073-1074` |
| X-IMP-43 | dates hors 2000–2100 (arrivée, pièce, échéance) | 422 | Pydantic, textes `"date d'arrivée hors période"` / `"date hors période"` | `IMP:524-529`, `IMP:938-943` |

### 4.19 Analyse du coût de revient (`ANA`, achats)

| # | Règle | Référence |
|---|---|---|
| R-IMP-56 | `GET /importations/analyse/revient` : ce que la matière importée a coûté **rendue usine**, regroupé par **axe** : référence, composition (à défaut nature), type de fil, titrage (« valeur unité »), couleur (à défaut désignation), fournisseur (de la ligne, à défaut de la matière), rôle, dossier, lot (exigence M52). | `ANA:27-37`, `ANA:80-115` |
| R-IMP-57 | Filtres **cumulés** : période sur la date d'arrivée du dossier (`debut`, `fin` ; un dossier sans date passe), statut (« Ouvert »/« Clos »), composition, type, titrage, couleur, fournisseur (égalité exacte), `references` (liste séparée par « ; »), `qualite` (les fils de sa recette ; cumulée avec `references` = intersection), `selection` = **réunion de combinaisons** JSON (`[{"composition":"PES","titrage":"1500"},{"composition":"PP","titrage":"1800"}]`, critères combinables : composition, type_fil, titrage, couleur, fournisseur ; chaque combinaison cumule ses critères) (M54), texte `q` : **plusieurs mots, dans n'importe quel ordre, sans accents ni majuscules**, chacun doit se trouver dans numéro et libellé du dossier, référence, lot, fournisseur, nature, composition, type et **libellé du type** (« frisé » trouve FRZ), titrage, couleur, désignation. | `ANA:40-77`, `ANA:116-203` |
| R-IMP-58 | Par groupe : lignes, dossiers, quantité (kg, « des kilos, le cuir, les franges et le ruban compris »), poids, marchandise, charges, TVA, revient, décaissé, coût par kg, surcoût, détail par poste ; groupes triés par revient décroissant ; totaux. Avec `detail` : les lignes une à une (d'où vient chaque kilo), triées par date d'arrivée décroissante. | `ANA:205-322` ; commit `58f507c` (« des kilos jamais mêlés de mètres ») |
| R-IMP-59 | **Frais non répartis** (dossier vide) comptés à part (`frais_non_repartis_mad`, `dossiers_non_repartis`), comme la liste des dossiers ; sous un filtre matière ou texte, ils ne comptent que pour un dossier dont une marchandise répond — ou, vide et sans filtre matière, dont le numéro ou le libellé répond au texte. | `ANA:150-154`, `ANA:264-273` ; essai `test_les_frais_non_repartis_suivent_les_filtres` |
| R-IMP-60 | `GET /importations/analyse/qualite/{code}` : coût d'une qualité **pondéré par la recette** : pour chaque rôle, son poids au m² réparti entre ses fils selon leur part, au **coût hors TVA par kg** de chaque fil importé (× kg/m², la densité convertissant les ml/m² d'un rôle linéaire) ; `cout_m2` (fils connus), `cout_m2_estime` (étendu au poids du rôle à partir de ce qui est connu), `couverture` (part du poids en kg connue), `cout_kg_tapis` (rôles au poids seulement, dont un fil au moins est importé), `roles_sans_cout`. | `ANA:325-415` ; commit `bb1109d` ; essai `test_cout_d_une_qualite_pondere_par_la_recette` |
| R-IMP-61 | `GET /export/revient` : la même analyse en classeur (feuille « Par {axe} » + total ; feuille « Lot par lot ») ; `GET /export/dossiers?statut=` (`""`, `ouvert`, `clos`) : feuilles Dossiers, Marchandises, Frais (répartition : marchandise visée, « figée à la clôture », ou clé), Échéancier. | `ANA:418-470`, `IMP:1099-1153` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| X-IMP-44 | axe inconnu | 400 | `f"axe inconnu : « {axe} » (attendu : {', '.join(AXES)})"` | `ANA:116-117` |
| X-IMP-45 | qualité inconnue ou sans recette (filtre ou analyse par qualité) | 404 | `f"qualité inconnue ou sans recette : « {qualite} »"` / `f"qualité inconnue ou sans recette : « {code} »"` | `ANA:121-124`, `ANA:339-341` |
| X-IMP-46 | sélection JSON illisible | 400 | `f"sélection illisible : {erreur.msg}"` | `ANA:47-50` |
| X-IMP-47 | sélection qui n'est pas une liste d'objets | 400 | `"la sélection doit être une liste de combinaisons"` | `ANA:51-52` |
| X-IMP-48 | critère inconnu dans une combinaison | 400 | `f"critère inconnu dans la sélection : {', '.join(inconnus)}"` | `ANA:55-57` |
| X-IMP-49 | export des dossiers : statut hors `""`/`ouvert`/`clos` | 422 | Pydantic (`pattern`) | `IMP:1100` |

### 4.20 Décisions (commits)

| Hash | Décision |
|---|---|
| `8116063` | Un dossier par facture ; il s'ouvre depuis la facture d'une réception et en prend toute la marchandise ; un second camion le rejoint ; une réception sans facture attend ; seul un dossier d'avant la mise en service se saisit à la main (étape de schéma 6 : `dossier.facture_id` unique). |
| `6f3a340` | Une facture n'a qu'un dossier, même face aux dossiers repris ; détacher garde les frais ; trois créations simultanées → un seul dossier, 409 nommant le gagnant ; ligne MAD sans cours ; fournisseur marocain à confirmer ; frais aberrants (C35, 100 % réglable) ; droits attendus seulement si toutes les matières ont un code actif ; TVA attendue = 20 % × (CAF + droits + TPI 0,25 %), écart toléré 5 % ; la clôture dit les lignes au cours du bon et les cours disparates. |
| `bb1109d` | Un cours par devise et cours figé du bon ; frais non répartis à part ; fournisseurs marocains hors « à rattacher » ; coût d'une qualité pondéré par la recette ; clôture qui dit ses alertes. |
| `b925e81` | Le contrôle C36 rend l'écart de la facture comme une **part** (0,035), arrondie à 4 décimales, que l'écran met en pourcentage (il s'affichait 350 % au lieu de 3,5 %) ; la confirmation d'un montage dit que le fil monté est du stock en machine. |
| `58f507c` | Poids en kilos ; poids figé à l'entrée ; changer la clé ne fait plus éclater les frais des dossiers clos (`dossier_charge_part`, une pièce ; étape 13 recolle les anciens éclatements) ; ligne à la main refusée sur un lot reçu et sur un dossier qui porte des réceptions ; verrous partagés à l'ouverture et au rattachement ; C36 (2 %) ; C35 ligne par ligne ; avoir négatif refusé ; échéancier (réglé, estimé) ; TPI et ASSUR créés d'office ; seul le poste TVA comparé à l'attendue. |
| `f6f3acc`, `f216509` | Période close : le coût d'une marchandise entrée dans un mois clos ne change plus — y compris par changement de clé ou de nature d'un poste. |
| M51 (exigences) | Répartition **à la valeur, pas au poids** par défaut ; le poids n'est qu'une option par poste, « que Mohamed choisira ou non » ; TVA 20 % paramétrée ; frais saisis **après** la réception. |
| Cahier § 10 | « Frais estimés puis réels » **non retenu** (un dossier reste ouvert tant que les frais réels n'y sont pas) ; clé « aux palettes » non retenue (`final-B`). |
| Audit 8 oct., « Ce qui reste à Mohamed » | Valorisation à la pesée (pas à la facture) à confirmer ; TVA attendue avec TPI 0,25 % à faire confirmer ; codes douaniers à saisir. |

---

## 5. Parité ERP Fil et mode « classeur » (partie A)

| # | Ce qui relève de la parité | Référence |
|---|---|---|
| PAR-01 | En service, la méthode de calcul est **toujours « corrigée »** (forcée au chargement des réglages) ; le mode « classeur » n'est activé que par les essais (`tests/test_plan_besoins.py`) et l'outil de comparaison. Une réécriture qui veut garder la **preuve de parité** doit garder les branches « classeur » du moteur ci-dessous. | `PAR:185`, `CMO:125-137` |
| PAR-02 | Coût au m² et nomenclature : perte **1,0** en mode classeur (pas de `taux_perte`), y compris dans `GET /qualites/facteurs-cout`. | `REF:833`, `MOT:369` |
| PAR-03 | Contrôle des recettes (C01) : tolérance **1e-6** en mode classeur, **0,01 point** sinon (la même qu'à l'enregistrement). | `MOT:427-430` |
| PAR-04 | Un brouillon (ou un bon à approuver non numéroté, lu « Brouillon ») compte comme **commandé** en mode classeur ; jamais en mode corrigé. | `CMO:398-405`, `DEP:23-40` |
| PAR-05 | Reste à livrer : en mode classeur, `max(0, commandé − reçu)` au kilo près, même soldé ; en mode corrigé, 0 si soldé/annulé ou si le reste est dans `toler_in_full`. | `CMO:408-425` |
| PAR-06 | Contrôle C06 (bon en retard) : en mode classeur, date du bon + 60 jours, sans retard toléré, sur le total reçu ; en mode corrigé, arrivée attendue (ETA, sinon date promise) + retard toléré, ligne par ligne. | `gestion_mp/calcul/controles.py:322-356` |
| PAR-07 | OTIF : en mode classeur, complétude sur les lignes présentes dans le camion et une réception hors commande comptée incomplète ; en mode corrigé, lignes **dues**, réception qui ne doit rien non jugée. | `MOT:2671-2700` |
| PAR-08 | Devise d'une matière pour le moteur : en mode classeur, celle de son **fournisseur** ; en mode corrigé, celle de la **fiche** (« SBR 821 : 16 % d'écart, 50 643 MAD sur une ligne »). | `CMO:728-738` |
| PAR-09 | Répartition des frais d'importation **à la valeur** : « la règle du métier, et celle du classeur » ; l'analyse du coût de revient est « reprise de l'ERP Fil, où elle est vérifiée au centime ». | `MOT:3513-3519`, `ANA:1-4` |
| PAR-10 | Reprise : le décodage des références a classé les 124 références du classeur ; les lots internes continuent la série `LOT-AAAA-NNNN` de l'ERP Fil (le compteur rattrape le plus grand numéro en base) ; un dossier repris peut porter plusieurs factures (règles « porteurs », § 4.3) ; un bon soldé repris sans trace ne se rouvre que par des retours ; une ligne de dossier « MAD » portant un cours reprend la devise de sa réception ; une annulation de l'ERP Fil est datée du jour de ce qu'elle annule. | `CLA:17-18`, `REC:50-67`, `IMP:146-187`, `ACH:580-602` ; commits `6f3a340`, `673c02c` |
| PAR-11 | Comparaison ERP Fil / Gestion MP sur l'année d'essai : **0 écart inexpliqué** ; chaque écart attribué à une correction voulue et prouvé en ramenant la correction à la règle de l'ERP Fil (« moteur à interrupteurs »). | `docs/COMPARAISON-ERP-FIL.md`, `docs/AUDIT-2026-10-08.md` ; commit `9042a98` |
| PAR-12 | L'ERP Fil comptait le cuir, la bande et le ruban **en kilos** (mètres × densité) avec un prix au kilo : c'est la règle retenue le 8 octobre (après un essai « tout en mètres » défait par l'étape de schéma 14). | commits `b6a6270`, `45c3d2c`, `d2e1e39` |

---

## 6. Points incohérents ou ambigus

| # | Constat | Références |
|---|---|---|
| I-01 | **Une réception entièrement refusée ne peut pas être annulée** : elle n'a écrit aucun mouvement, donc `contrepasser_document` ne trouve rien et répond 409 « Ce document a déjà été annulé. » (message faux). | `REC:581-601`, `STK:249-251` |
| I-02 | `POST /lots/numero-interne` **réserve un numéro de lot interne tout de suite** (compteur commité) : il recrée les trous que la règle « numéroté à la validation, pas avant » voulait supprimer. Route vraisemblablement résiduelle. | `REC:45-47` vs `REC:665-670` ; commit `b6b751c` |
| I-03 | Format du lot interne : le cahier (§ 5.2) dit `LOT-AAAA-NNNNN` (5 chiffres), le code et la décision de recette (« M8 », `final-A`) disent **4 chiffres**. | `REC:67`, cahier § 5.2 |
| I-04 | « Les numéros suivent les dates » (cahier § 6.4) n'est pas garanti : un bon envoyé avec une date passée, une réception antidatée validée plus tard, prennent le numéro **suivant** de la série de leur année (un numéro plus grand pour une date plus ancienne). | `SEC:179-198`, `ACH:503-515`, `REC:543` |
| I-05 | Un bon qui passe par la direction **perd sa date d'envoi saisie** : l'approbation le numérote **au jour de l'approbation** (pas de date d'envoi possible). | `ACH:691-716`, `ACH:719-727` |
| I-06 | La confirmation des prix est permise sur un **brouillon** (et un bon à approuver, ou soldé) : le cours se fige alors **avant l'envoi** ; sur un brouillon à approuver, elle ne le renvoie pas en brouillon (le garde-fou est sauté), contrairement à une modification de lignes (« la direction ne relit pas un bon qui bouge sous ses yeux »). | `ACH:814-841`, `ACH:265-270` |
| I-07 | Confirmer un prix avec mise à jour du catalogue écrit le prix **dans la devise du bon** sur la fiche **sans conversion** : si la fiche a changé de devise depuis la création du bon, le catalogue reçoit un prix dans la mauvaise devise (alors que la lecture, elle, convertit, R-CMD-09). Cette mise à jour de la fiche n'a pas de journal « modification matière » (seul le journal du bon la dit). | `ACH:826-831`, `ACH:153-160` |
| I-08 | Aucune vérification d'**activité** à la commande ou à la réception : une matière ou un fournisseur désactivé se commande et se reçoit ; un métier arrêté ou une matière désactivée se monte. | `ACH:434-460`, `REC:390-438`, `REF:1343-1368` |
| I-09 | Deux définitions d'un **fournisseur local** : fiche fournisseurs = pays ∈ {MAROC, MOROCCO, vide} ; importations = pays ∈ {MAROC, MOROCCO, **MA**} **ou** (pays vide **et** devise MAD). Un fournisseur sans pays facturé en USD est « local » dans la liste mais a un dossier d'importation ; « MA » est local pour l'un, pas pour l'autre. | `REF:332`, `IMP:109-113` |
| I-10 | Modifier une matière n'a **aucun garde d'historique** : changer son **rôle** alors qu'elle est dans une recette peut défaire la règle des 100 % sans refus (seul C01 le signalera) ; changer devise, unité du prix ou densité avec du stock et des bons ouverts change en silence `prix_kg` et les estimations. | `REF:623-653`, `REF:951-984` |
| I-11 | La **fiche qualité** accepte un poids > 0 sur un rôle sans matière (simple avertissement), alors que l'**enregistrement de la recette** le refuse (X-REF-48) : la fiche peut créer l'état que la recette interdit, et toute écriture de recette suivante sera refusée tant qu'on ne l'a pas corrigé. | `REF:893-899` vs `REF:973-981` |
| I-12 | Import du tableur : aucune borne numérique (un prix, un stock minimum, une contenance négatifs passent l'aperçu puis violent une contrainte de la base à l'application → erreur serveur ; une densité ou une couverture négatives sont acceptées) ; pas de règle « unité ≠ kg ⇒ contenance » ni de contenance forcée à 1 en kg ; devise, classification et code douanier comparés **à la casse près** (« usd » refusé) ; une matière nouvelle **désactivée** exige quand même un fournisseur (plus strict que l'écran) ; pas de contrôle de longueur de la référence ; `priorite_equiv` absent du tableur. | `SUI:752-808`, `MOD:270-278` vs `REF:427-453`, `REF:566-604` |
| I-13 | Casse des doublons : valeurs de classification et références de matière **sensibles** à la casse (« pp » et « PP » coexistent) ; rôles, fournisseurs **insensibles** ; le renommage d'un rôle contrôle la casse **exacte** alors que l'ajout l'ignore. | `REF:208`, `REF:611`, `REF:126`, `REF:150`, `REF:371` |
| I-14 | Une valeur de classification **désactivée** reste acceptée par le serveur sur une matière (seul l'écran la cache). | `REF:574-579` |
| I-15 | Formats de nombres incohérents dans les messages et le journal : « {detenu:,.0f} kg » (milliers « , » à l'anglaise) pour un magasin ; frais du dossier journalisés `{montant:,.2f}` (« 1,234.50 ») ; ailleurs « 1 234,50 » (espace et virgule). | `REF:1096`, `IMP:986`, `IMP:1008`, `IMP:1023` vs `STK:23-24` |
| I-16 | L'**empreinte est facultative** : un client qui ne l'envoie pas écrase en silence une fiche modifiée entre-temps (fournisseur, qualité, recette, métier, montage). Le **plan** d'une qualité n'a ni empreinte ni verrou. | `REF:54-55`, `REF:1034-1046` |
| I-17 | À la **création** d'une qualité, aucune version de recette ne semble naître (les poids n'ont pas encore leur `qualite_id` au moment où l'écouteur les note) : la première version apparaît au premier enregistrement de recette ou de poids. À vérifier par un essai lors de la réécriture. | `SUI:441-454`, `REF:846-857` |
| I-18 | `PUT /commandes/{cid}/expedition` **remplace tous les jalons** : un appel qui n'envoie qu'un jalon efface les autres (comportement voulu par l'écran, qui renvoie tout, mais piège pour un autre client). | `ACH:879-880` |
| I-19 | Indicateur `approbation_requise` de la liste des bons (= estimé × cours > seuil et pas d'`approuvee_par`) ≠ règle du garde-fou (montant de référence, marge, bon parti sous le seuil) : l'écran peut annoncer « approbation requise » sur un bon parti que le serveur laisse passer, et inversement. | `ACH:331` vs `ACH:246-291` |
| I-20 | Facture saisie avec la réception (`_facture`) : elle **n'efface rien** et met à jour date/montant d'une facture existante, même partagée avec d'autres réceptions ou portée par un dossier, sans contrôle ; `PUT /receptions/{rid}/facture`, lui, **remplace** (vide date et montant non envoyés) et contrôle le dossier. Deux sémantiques pour la même facture. | `REC:361-387` vs `REC:614-662` |
| I-21 | Un même numéro de lot fournisseur reçu deux fois pour la même matière **fusionne** dans un seul lot (date d'entrée = la première ; poids de bobine = le dernier mesuré). Voulu (un lot reçu en deux camions, `DEP:70-81`) mais aussi vrai pour deux livraisons sans rapport au même numéro. | `STK:35-60` |
| I-22 | Montage d'un étage hors limites : **404** par la route d'étage, **422** (même message) par la vérification générale. | `REF:1427-1428` vs `REF:1355-1356` |
| I-23 | Clôture d'un dossier : seuls les **frais hors TVA** non répartis bloquent ; une TVA non répartie (cas de lignes toutes à valeur et poids nuls) ne bloque pas. | `IMP:1042-1044`, `IMP:204-207` |
| I-24 | `DossierLigne.poids_kg` est écrit (rattachement, saisie, clôture — « poids figé ») mais le moteur lit la **quantité** : la colonne est sans effet depuis que tout est en kilos. | `IMP:544`, `IMP:769`, `IMP:1052-1053`, `CMO:575-578` |
| I-25 | Rouvrir un dossier ne défait pas les **cours du jour figés** à la clôture (ni la note dans le commentaire) : une nouvelle clôture ne les reprend pas. Voulu (le coût d'alors) ou non : non écrit. | `IMP:1054-1058`, `IMP:1068-1079` |
| I-26 | Un dossier **saisi à la main** se crée à tout moment : rien ne vérifie qu'il est « d'avant la mise en service ». Sa date d'arrivée se modifie sans contrôle de période close (elle ne change pas le coût, mais elle classe le dossier dans l'analyse par période). | `IMP:593-629`, `IMP:641-650` |
| I-27 | Supprimer un rôle supprime ses lignes `QualitePoids` à poids 0 : l'écouteur de versions crée alors une **version de recette** pour chaque qualité touchée (sans changement réel de la recette). | `REF:177`, `SUI:441-476` |
| I-28 | Le « fil monté » a changé trois fois de statut : information seulement (`202d1a0`), dans le disponible mais valeur à part (`f33a428`), puis **dans le stock et sa valeur** (`169dfdc`, en vigueur, `REF:1198-1211`). Le bilan du mois précise qu'à une date passée il n'est pas compté (« son montage n'a pas d'historique » : seul le journal en garde la trace). | `REF:1198-1211`, `SUI:665-666` |
| I-29 | Documents de conformité **périmés** par rapport au code : `final-A` dit qu'un bon numéroté renvoyé « redevient brouillon » et « ne se reçoit pas » tant qu'il attend la direction, et que le bon imprimé montre « nos prix à confirmer », « prix (EUR / kg), montant » — le code garde le bon parti (version partie), le laisse recevoir (avertissement) et imprime **sans aucun prix** ; `final-B` dit que le changement de clé « éclate » les frais au centime (reste sur la plus grosse ligne) et que seuls DD, TVA, FRET sont protégés — le code fige des **parts sans arrondi** et protège **cinq** postes (DD, TPI, TVA, FRET, ASSUR) ; `final-C` décrit le retour à une version par `PUT …/recette?motif=` et un import qui ne vérifie pas « en service ⇒ fournisseur » — il existe une route dédiée de restauration et l'import vérifie. Le **code fait foi**. | `docs/conformite/final-A-achats.md`, `final-B-importations.md`, `final-C-referentiels.md` |
| I-30 | Cahier § 2.7 : clé « poids » **proposée** pour le fret, le port et la TMSA ; exigence M51 et code : **tout à la valeur** par défaut, le poids n'étant qu'une option que Mohamed choisira. Cahier § 2.8 / § 5.1 : « import du plan de production par tableur » promis — aucune route d'import du plan n'existe (seul `PUT /production/plan`). | `MAIN:59-73`, `MOD:449`, `docs/EXIGENCES-MOHAMED.md` M51 |
| I-31 | Le mode classeur garde des branches dans `facteurs-cout` et le contrôle C01 alors qu'il est **inatteignable** en service (méthode forcée) ; en mode classeur, une recette acceptée à 99,995 % serait déclarée fausse par C01 (1e-6). | `REF:833`, `MOT:429`, `PAR:185` |
| I-32 | `modifier_valeur` (classification) cite dans son refus le code **non nettoyé** (`e.code`), et journalise `« X → X »` même sans renommage. | `REF:228-232` |


# Règles de gestion et refus — partie B : stock, production, atelier, suivi, comptes, exploitation

Inventaire tiré du **code** de Gestion MP (`~/gestion-mp`, état du 8 octobre 2026, dernier
commit `2d588b9`), lu intégralement pour les fichiers du périmètre, complété par les documents
(`docs/CAHIER-DES-CHARGES.md`, `docs/EXIGENCES-MOHAMED.md`, `docs/AUDIT-2026-10-08.md`,
`docs/CONFORMITE.md`, `docs/conformite/final-D-direction.md`, `final-E-stock-atelier.md`,
`5-a-faire-suivi.md`), par les essais (`tests/*.py`) et par les messages de commit (décisions
de Mohamed, avec leur hash). Objectif : qu'une autre équipe reconstruise ces domaines **sans
relire l'ancien code**. Les conventions communes (forme des refus, journal, numérotation de base,
`date_permise`, `cout_hors_periode_close`, empreintes, réglages, mode classeur) sont posées au
§ 0 de la partie A ; on ne les répète ici que pour les compléter.

Périmètre : (1) stock — écriture, lots, transferts, contre-passation, lectures, opérations,
« À valider », inventaires, période close ; (2) production — proposition, ordres de fabrication,
retours, annulation, plan, réalisé, besoins ; (3) atelier (rôle alimentation) ; (4) suivi —
réclamations, signalements, pièces jointes, échéancier, versions de recettes, indicateurs, bilan,
courriel ; (5) comptes, sessions, droits, prix masqués, journal, paramètres, devises, protections
HTTP ; (6) sauvegardes, restauration, courriel, tâches de fond, numérotation complète.

## B.0 Conventions complémentaires

### B.0.1 Abréviations des fichiers (s'ajoutent à celles de la partie A)

| Abrév. | Fichier |
|---|---|
| `STK` | `gestion_mp/services/stock.py` (même abréviation que la partie A) |
| `APS` | `gestion_mp/api/stock.py` |
| `OPE` | `gestion_mp/api/operations.py` |
| `INV` | `gestion_mp/api/inventaires.py` |
| `PRO` | `gestion_mp/api/production.py` |
| `PPL` | `gestion_mp/api/production_plan.py` |
| `BRO` | `gestion_mp/api/brouillons.py` |
| `SUI` | `gestion_mp/api/suivi.py` |
| `CPT` | `gestion_mp/api/comptes.py` |
| `SEC` | `gestion_mp/securite.py` |
| `MAIN` | `gestion_mp/main.py` |
| `SAU` | `gestion_mp/services/sauvegarde.py` |
| `COU` | `gestion_mp/services/courriel.py` |
| `DEP` | `gestion_mp/depot.py` |
| `MOD` | `gestion_mp/modeles.py` |
| `PAR` | `gestion_mp/parametres.py` |
| `CFG` | `gestion_mp/config.py` |
| `DB` | `gestion_mp/db.py` |
| `PIL` | `gestion_mp/api/pilotage.py` |
| `EXP` | `gestion_mp/api/exports.py` |
| `REF` | `gestion_mp/api/referentiels.py` |
| `REC` | `gestion_mp/api/receptions.py` |
| `ACH` | `gestion_mp/api/achats.py` |
| `MOT` | `gestion_mp/calcul/moteur.py` |
| `CMO` | `gestion_mp/calcul/modele.py` |
| `CTL` | `gestion_mp/calcul/controles.py` |
| `T:fichier` | `tests/fichier` |

Toutes les routes sont sous `/api` (`MAIN:131-134`).

### B.0.2 Précision sur la forme des refus (complète A § 0.2)

| # | Règle | Référence |
|---|---|---|
| C1 | Un refus métier : `erreur(message, code=422)` → `HTTPException` → corps `{"detail": "<message>"}`. | `SEC:28-29` |
| C2 | **Les refus de schéma (Pydantic) sont traduits en français** par un gestionnaire global : pour chaque erreur, `champ` = les éléments de `loc` hors `body`/`query`/`path` joints par « . », `texte` = message anglais où l'on remplace dans l'ordre : « Field required » → « à renseigner », « Input should be a valid » → « valeur incorrecte », « should be greater than or equal to » → « doit être au moins », « should be greater than » → « doit être supérieur à », « should be less than or equal to » → « doit être au plus », « should be less than » → « doit être inférieur à », « should have at least » → « trop court : au moins », « should have at most » → « trop long : au plus », « characters » → « caractères », « character » → « caractère », « String » → « Texte », « Input » → « La valeur », « List » → « La liste », « item after validation » → « élément », « items » → « éléments ». Chaque message devient `"{champ} : {texte}"` (ou `texte` seul sans champ) ; ils sont joints par « ; » ; réponse **422** `{"detail": "<chaîne>"}`. (La partie A dit « message anglais » : c'est inexact, voir B.9.) | `MAIN:164-187` |
| C3 | Une exception non prévue (Python) donne la réponse 500 générique de FastAPI (pas de gestionnaire). Cas connus dans ce périmètre : voir B.9. | `MAIN` (absence) |
| C4 | Format des nombres dans les messages : `kg(v, d)` = séparateur de milliers espace, virgule décimale, `d` décimales (2 par défaut) — « 6 221,43 ». `kg_et_metres(v, article)` = « 14,30 kg » et, pour une matière au mètre (densité `kg_par_ml` > 0), « 14,30 kg ≈ 1 021 ml » (kilos ÷ densité, 0 décimale). | `STK:23-32` |
| C5 | Seuil de nullité du stock : `POUSSIERE = 1e-3` kg (sous le gramme, un solde est nul). | `STK:20` |

### B.0.3 Dates

`date_permise` (refus D1–D3 de la partie A § 0.5, `SEC:210-226`) est appelée dans ce périmètre :
à la création / modification d'un brouillon d'opération (`OPE:252`), à sa validation (`OPE:402`),
dans ses blocages (`OPE:86-89`) ; à la création / modification d'un bon de sortie (`PRO:266`),
dans ses blocages (`PRO:298-301`), à sa validation (`PRO:502`) ; à l'ouverture et à la validation
d'un inventaire (`INV:271`, `INV:395`) ; et **dans toute écriture de stock** (`STK:148`) — donc
aussi dans toute contre-passation (datée du jour de l'original). « Écriture antidatée » : il n'y a
**pas** de limite en jours dans le passé ; seules l'année < 2000 (faute de frappe, « 2006 pour
2026 ») et la période close sont refusées. Le fuseau est celui du Maroc : `TZ` forcé à
`GESTION_MP_FUSEAU` (défaut `Africa/Casablanca`) au chargement de la configuration, et chaque
connexion PostgreSQL ouvre avec `-c timezone=<fuseau>` (`CFG:9-13`, `DB:13-14`). « Aujourd'hui »
= `date.today()` du serveur.

---

## B.1 Stock

### B.1.1 Le journal des mouvements (modèle)

| # | Règle | Référence |
|---|---|---|
| S1 | Le **journal des mouvements** (`mouvement`) est la seule écriture de stock ; un mouvement n'est jamais effacé ni modifié : une annulation s'y lit comme une ligne inverse. | `MOD:1-16`, `APS:100-101` |
| S2 | Champs : `date_effet` (date du fait), `date_saisie` (horodatage `maintenant()`), `type`, `article_id`, `lot_id` (**obligatoire** : tout mouvement nomme son lot, exigence M64), `magasin_id`, `quantite` **signée** (kg), `prix` (prix d'achat d'une entrée, dans sa devise, défaut 0), `devise` (défaut « MAD »), `cours` (cours figé, défaut 0), `document` (« reception », « sortie », « operation », « inventaire »), `document_id`, `document_numero`, `ordre_id` (FK `bon_sortie`), `paire` (les deux lignes d'un transfert), `motif` (80), `commentaire` (300), `auteur` (80, le **nom** de la personne), `contrepasse_id` (FK `mouvement`, **unique**). | `MOD:497-549` |
| S3 | Contraintes base : `type IN (types)`, `quantite <> 0`, `contrepasse_id` unique (un mouvement ne se contre-passe qu'**une** fois), index `(article_id, date_effet)`, index sur `date_effet`, `lot_id`, `document_id`. | `MOD:505-509`, `MOD:545-547` |
| S4 | Types et libellés (et code du moteur ERP Fil) : `OUVERTURE` « Stock d'ouverture » (`STOCK_INITIAL`, +) ; `RECEPTION` « Entrée de réception » (`ENTREE_RECEPTION`, +) ; `SORTIE` « Sortie vers les machines » (`SORTIE_PROD`, −) ; `RETOUR_MACHINE` « Retour des machines » (`RETOUR_PRODUCTION`, +) ; `RETOUR_FOURNISSEUR` « Retour au fournisseur » (`RETOUR_FOURNISSEUR`, −) ; `AJUSTEMENT` « Ajustement d'inventaire » (`AJUSTEMENT_INVENTAIRE`, signé) ; `TRANSFERT` « Transfert entre magasins » (`TRANSFERT_MAGASIN`, 0). Le moteur connaît aussi `QUARANTAINE` (signe 0), jamais écrit par Gestion MP. | `MOD:486-494`, `CMO:28-37` |
| S5 | Signes écrits dans Gestion MP : ouverture, réception, retour machine > 0 ; sortie, retour fournisseur < 0 ; ajustement ± ; transfert = deux lignes (−q à la source, +q à la destination) ; une contre-passation = la quantité opposée, **même type** que l'original. | `OPE:432`, `PRO:523`, `STK:220-227`, `STK:256-258` |
| S6 | Le **solde** `(lot, magasin)` est un cache du journal, tenu dans la même transaction et sous verrou de ligne. Contrainte base `quantite >= -0.0005` (`ck_solde_positif`). Clé primaire `(lot_id, magasin_id)`. | `MOD:475-483` |
| S7 | Le **lot** : `article_id`, `numero` (80, unique **par article** : un même numéro peut exister pour deux matières), `fournisseur_id` facultatif, `entre_le` (date d'entrée, obligatoire), `poids_bobine` (mesuré à la réception, défaut 0), `commentaire`. Pas de statut stocké (calculé, voir S60). | `MOD:458-472`, cahier § 10 |
| S8 | Le cours `cours` est **figé sur le mouvement** à la validation : changer le cours d'une devise demain ne réécrit pas ce qu'a coûté une entrée d'hier (étape de schéma 7, commit `5ca0960`). | `MOD:527-530`, `STK:143-145` |

### B.1.2 Le chemin unique d'écriture : `ecrire`

`ecrire(s, *, type, lot, magasin_id, quantite, jour, document, document_id, document_numero,
auteur, prix=0, devise="MAD", ordre_id=None, paire=None, motif="", commentaire="",
contrepasse_id=None, cours=None)` — `STK:122-212`. Tous les gestes de stock (réceptions,
sorties, opérations, inventaires, contre-passations) passent par elle.

Règles (dans l'ordre d'exécution) :

| # | Règle | Référence |
|---|---|---|
| S10 | Refus d'une quantité nulle (`abs(quantite) < 1e-9`). | `STK:146-147` |
| S11 | `date_permise(jour)` (D1–D3). | `STK:148` |
| S12 | Magasin inconnu refusé ; un magasin **désactivé ne reçoit plus rien** (refus si `quantite > 0`) mais **on peut encore en sortir** (quantité < 0 acceptée). | `STK:149-153` |
| S13 | **Verrou** : le solde `(lot, magasin)` est créé à 0 s'il manque (`INSERT … ON CONFLICT DO NOTHING`) puis relu `SELECT … FOR UPDATE` avec `populate_existing` (la valeur relue est celle de la base, pas celle en mémoire). Deux personnes qui sortent la même palette : la seconde attend, puis lit le solde à jour. | `STK:63-74`, `STK:156`, `T:test_parcours.py:238-261` |
| S14 | Ordre des verrous : le solde **d'abord**, l'inventaire ensuite — un inventaire qui s'ouvre au même instant attend ce mouvement (et le compte), ou bien ce mouvement le voit ouvert et s'arrête. | `STK:154-156` |
| S15 | **Inventaire ouvert** : si `document != "inventaire"` et qu'il existe un inventaire au statut « ouvert » sur ce magasin **ou sur tous les magasins** (`magasin_id IS NULL`), l'écriture est refusée — **tout** le magasin est suspendu (entrées comprises, toutes matières, même hors du périmètre de l'inventaire). | `STK:157-168` |
| S16 | **Solde jamais négatif** : refus si `solde.quantite + quantite < -POUSSIERE`. | `STK:169-178` |
| S17 | Toute écriture négative doit être **couverte à sa date** (`couvert_a_sa_date`, B.1.3). | `STK:179-180` |
| S18 | Devise : `devise = (devise or "MAD").upper()`. Cours : si devise = MAD **ou** prix nul → `cours = cours or 0.0` (le cours passé est gardé, sinon 0) ; sinon, sans cours passé → `Devise.taux` actuel de cette devise, ou 0 si la devise n'existe pas. | `STK:181-186` |
| S19 | Le solde est mis à jour `round(solde + quantite, 6)` ; s'il est sous `POUSSIERE` en valeur absolue il est remis à **0,0** exactement. | `STK:187-189` |
| S20 | Le mouvement est ajouté et `flush()` (son `id` est connu immédiatement — sert à la paire d'un transfert et aux contre-passations). Aucun commit : c'est l'appelant qui valide la transaction (tout ou rien). | `STK:190-212` |

Refus :

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR1 | `abs(quantite) < 1e-9` | 422 | `"Une écriture de stock ne peut pas être nulle."` | `STK:146-147` |
| SR2 | `date_permise` | 422 | D1, D2, D3 (partie A § 0.5) | `STK:148` |
| SR3 | `s.get(Magasin, magasin_id) is None` | 422 | `"Magasin inconnu."` | `STK:150-151` |
| SR4 | `not magasin.actif and quantite > 0` | 422 | `f"Le magasin « {magasin.code} » est désactivé : il ne reçoit plus rien."` | `STK:152-153` |
| SR5 | inventaire `statut == "ouvert"` et (`magasin_id == magasin_id` ou `magasin_id IS NULL`), document ≠ « inventaire » | 409 | `f"L'inventaire {ouvert.numero} est en cours sur « {magasin.code} » : les mouvements y sont suspendus jusqu'à sa validation."` | `STK:157-168` |
| SR6 | `solde.quantite + quantite < -POUSSIERE` | 409 | `f"Le lot « {lot.numero} » de « {lot.article.reference} » ne porte que {kg(solde.quantite, 3)} kg dans « {magasin.code} », {kg(-quantite, 3)} kg demandés. Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là."` (au gramme, 3 décimales : « 6 221,43 demandés pour 6 221,43 » ne disait pas où était l'écart — `T:test_audit2_atelier.py:168-180`) | `STK:169-178` |
| SR7 | `quantite < 0` et non couvert à sa date | 409 | SR8 ou SR9 ci-dessous | `STK:179-180` |

### B.1.3 « Couvert à sa date » (une sortie ne prend pas un lot absent à sa date)

`couvert_a_sa_date(s, lot, magasin, quantite, jour)` — `STK:77-119`. Décision : audit 2-G, B1
(commit `61027e4`) — une sortie datée d'hier pouvait prendre un lot arrivé ce matin, le stock
était négatif hier, et la sortie partait à coût nul.

| # | Règle | Référence |
|---|---|---|
| S21 | On lit le journal du lot **dans ce magasin**, sommé par `date_effet`, trié par date. Le solde étant déjà verrouillé, ce journal ne bouge pas pendant la lecture (un brouillon le lit sans verrou pour annoncer d'avance un refus). | `STK:86-91` |
| S22 | Cumul jour par jour ; pour chaque date `>= jour`, si `cumul (fin de ce jour) + quantite < -POUSSIERE`, le **premier** jour en défaut est retenu (`manque = (date, cumul)`). | `STK:92-96` |
| S23 | En plus : `au_jour` = somme des mouvements datés `<= jour` ; si `au_jour + quantite < -POUSSIERE`, le manque est **remplacé** par `(jour, au_jour)` (le défaut le jour même prime). | `STK:97-99` |
| S24 | Sans manque : accepté. Sinon `entree` = la **première date où la somme du jour est positive** (pas `lot.entre_le`). | `STK:100-102` |
| S25 | Le stock du lot dans ce magasin ne doit passer sous zéro **à aucune date à partir de `jour`** : « assez aujourd'hui ne suffit pas ». | `STK:79-83`, `T:test_valeur_et_dates.py:68-115` |

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR8 | manque et (`entree is None` ou `entree > jour`) | 409 | `f"Le lot {ref} {quand} : une écriture datée du {jour:%d/%m/%Y} ne peut pas le prendre. La dater au jour où la matière était là, ou choisir un lot présent à cette date."` avec `ref = f"« {lot.numero} » de « {lot.article.reference} »"` et `quand = f"n'est entré dans « {magasin.code} » que le {entree:%d/%m/%Y}"` si `entree`, sinon `f"n'est jamais entré dans « {magasin.code} »"` | `STK:103-111` |
| SR9 | manque et le lot était entré à `jour` | 409 | `f"Au {date_manque:%d/%m/%Y}, il n'y avait que {kg(max(disponible, 0.0))} kg du lot {ref} dans « {magasin.code} », {kg(-quantite)} kg demandés au {jour:%d/%m/%Y}"` + (`" : la matière est sortie depuis par d'autres écritures."` si `date_manque > jour`, sinon `"."`) + `" Choisir un autre lot, ou dater l'écriture après l'entrée de la matière."` | `STK:112-119` |

### B.1.4 Lots

| # | Règle | Référence |
|---|---|---|
| S30 | `lot_ou_creer(article_id, numero, entre_le, fournisseur_id=None, poids_bobine=0)` : numéro `strip()` ; refus s'il est vide ; lot cherché par `(article, numero)` (sensible à la casse) ; s'il manque il est créé par `INSERT … ON CONFLICT DO NOTHING` (deux postes simultanés → un seul lot) puis relu. | `STK:35-54` |
| S31 | Lot existant : son fournisseur est complété s'il n'en avait pas (`fournisseur_id` donné et lot sans fournisseur) ; son `poids_bobine` est **remplacé** si un poids non nul est donné ; `entre_le` ne change jamais. | `STK:55-60` |
| S32 | Créent des lots : la validation d'une réception (partie A), la validation d'un stock d'ouverture ou d'un ajustement « matière retrouvée » sur un lot nommé (`OPE:429-431`, `entre_le` = date de l'opération, sans fournisseur), et la **saisie** d'un lot trouvé à l'inventaire (`INV:369`, `entre_le` = date de l'inventaire — créé dès le comptage, avant validation). | `OPE:429-431`, `INV:369` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR10 | `numero.strip() == ""` | 422 | `"Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne »."` | `STK:43-45` |

### B.1.5 Transfert entre magasins

| # | Règle | Référence |
|---|---|---|
| S35 | `transferer` écrit deux lignes de type `TRANSFERT`, même document, même jour, même motif et commentaire, prix 0 : d'abord la **sortie** (−q) de la source — dont `paire` = son propre id —, puis l'**entrée** (+q) dans la destination avec `paire` = id de la sortie. Chaque ligne passe par `ecrire` (verrou, inventaire ouvert, solde, couvert à sa date côté source, magasin désactivé côté destination). | `STK:215-227` |
| S36 | Un transfert ne change pas le stock total ; il ne compte ni en entrée ni en sortie (historique des lots, bilan). La « libération de quarantaine » et la « mise en quarantaine » sont des transferts (B.1.9). | `APS:177`, `SUI:549-552` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR11 | `source_id == destination_id` | 422 | `"Un transfert va d'un magasin à un autre."` | `STK:218-219` |

### B.1.6 Contre-passation (annulation d'un document validé)

`contrepasser_document(s, document, document_id, auteur)` — `STK:230-270`. Utilisée par
l'annulation d'une opération (`OPE:452`), d'un ordre et de ses retours (`PRO:567-569`), d'une
réception (partie A).

| # | Règle | Référence |
|---|---|---|
| S40 | Lignes visées : tous les mouvements du document (`document`, `document_id`) qui **ne sont pas eux-mêmes des contre-passations**, moins ceux déjà contre-passés. S'il n'en reste aucune : refus « déjà annulé ». | `STK:233-251` |
| S41 | Ordre : les sorties de l'original (quantité < 0) sont défaites **d'abord**, les entrées ensuite (tri `(quantite > 0, id)`) : on remet ce qui était sorti avant de retirer ce qui était entré. | `STK:252-254` |
| S42 | Chaque inverse passe par `ecrire` : **même type**, `quantite = -x.quantite`, **datée de la date d'effet de l'original** (la date de saisie dit, elle, quand on a annulé), même `document_numero`, `prix`, `devise`, `cours`, `ordre_id`, `motif` ; `commentaire = f"Annulation du mouvement n°{x.id}"` ; `contrepasse_id = x.id` ; `auteur` = qui annule. Conséquences : une annulation est **refusée dans une période close** (D3), refusée si un inventaire est ouvert sur le magasin (SR5), refusée si le lot n'a plus la matière (SR6 — p. ex. une réception dont le lot est déjà sorti), refusée si l'inverse négative n'est pas couverte à la date d'origine (SR8/SR9). | `STK:255-263`, cahier § 5.2 |
| S43 | Paires de transfert : la première inverse d'une paire prend `paire = son propre id`, la seconde reçoit ce même id. | `STK:264-269` |
| S44 | Renvoie le nombre de lignes annulées. Aucun journal d'audit ici (l'appelant l'écrit). | `STK:270` |
| S45 | Décision (commit `673c02c`, reprise) : une annulation est datée du jour de ce qu'elle annule — aussi pour les annulations reprises de l'ERP Fil. | `git 673c02c` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR12 | aucune ligne à annuler | 409 | `"Ce document a déjà été annulé."` | `STK:250-251` |

### B.1.7 Disponible et FIFO

| # | Règle | Référence |
|---|---|---|
| S50 | `disponibles(article, magasin=None)` : les lots de la matière avec un solde `> POUSSIERE` dans un magasin **qui n'est pas de type « Quarantaine »**, triés par `lot.entre_le` puis `lot.id` (du plus ancien au plus récent = l'ordre de sortie FIFO). Un magasin désactivé n'est **pas** exclu. Champs : `lot_id`, `lot`, `magasin_id`, `magasin`, `quantite`, `entre_le`, `poids_bobine` (du lot). | `STK:273-300` |
| S51 | `solde_article(article)` = somme de tous les soldes de ses lots (quarantaine comprise). | `STK:303-310` |
| S52 | Types de magasin : `"Stock courant"` ou `"Quarantaine"` (CHECK base). À l'installation, s'il n'existe aucun magasin de ce type et aucun magasin de ce code : « Magasin principal » (Stock courant) et « Quarantaine » (Quarantaine) sont créés. | `MOD:388-397`, `MAIN:46`, `MAIN:78-82` |

### B.1.8 Coût et valeur d'un mouvement (lecture)

| # | Règle | Référence |
|---|---|---|
| S55 | Le coût unitaire (MAD) de chaque mouvement vient d'un **seul** calcul, celui de la Valorisation : `moteur.couts_du_journal(depot.charger(s))` → `(unitaire par id de mouvement, CMUP actuel par référence)`. | `APS:60-71`, `MOT:1820` |
| S56 | Règles de ce calcul (résumé ; détail dans la partie « calculs ») : CMUP glissant recalé à chaque entrée ; un achat entre à son **coût de revient** quand le dossier d'importation le connaît (retrouvé par la ligne de réception), sinon à `prix × cours figé` du mouvement ; une **annulation** défait l'écriture annulée **à son coût** ; un **retour au fournisseur** sort au coût d'entrée **de son lot** ; un retour des machines / un excédent d'inventaire rentre au coût moyen sans le déplacer ; tout le reste passe au coût moyen du moment. | `APS:60-69`, `MOT:1820-1846`, commits `5ca0960`, `61027e4` |
| S57 | La valeur d'un mouvement n'est **pas stockée** : recalculée à la lecture (elle suit un dossier d'importation complété après coup). | final-E, audit 1 n° 29 |

### B.1.9 Lectures du stock (`APS`)

Toutes les routes de `APS` exigent une session (`APIRouter(dependencies=[Depends(acteur)])`,
`APS:27`) : direction, achats et alimentation lisent.

| # | Règle | Référence |
|---|---|---|
| S60 | **Statut d'un lot** (calculé, jamais stocké) à partir de ses soldes : `partiel` (« En partie en quarantaine ») si quarantaine > POUSSIERE **et** disponible > POUSSIERE ; `quarantaine` (« En quarantaine ») si quarantaine > POUSSIERE ; `disponible` (« Disponible ») si disponible > POUSSIERE ; sinon `epuise` (« Épuisé »). Disponible = soldes des magasins non-quarantaine (désactivés compris). | `APS:31-32`, `APS:50-57` |
| S61 | `GET /mouvements` : filtres `article_id`, `lot_id`, `magasin_id`, `type`, `document`, `du`/`au` (date d'effet incluse), `q` (≤ 80 car.) ; tri `date_effet DESC, id DESC` ; pagination `decalage` (≥ 0) et `limite` (1–5000, défaut 1000) ; renvoie `lignes`, `tronque` (il en reste), `decalage`, `suivant` (= `decalage + limite` s'il en reste, sinon `null`), `types` (code → libellé). | `APS:90-153` |
| S62 | Recherche `q` : **chaque mot** (séparés par des blancs) doit se trouver quelque part (ET entre mots, OU entre colonnes), `ILIKE '%mot%'` sur : référence et désignation de la matière, numéro du lot, n° de document, motif, commentaire, auteur. Les jokers `%` et `_` tapés ne sont pas échappés. | `APS:122-130` |
| S63 | `avec_valeur=true` : ajoute `cout_mad` (coût unitaire du mouvement S55 ; pour la ligne d'arrivée d'un transfert, le coût de sa ligne de départ via `paire` ; à défaut le CMUP actuel de la référence ; à défaut 0) et `valeur_mad = quantite × cout_mad`. | `APS:137-146` |
| S64 | Champs d'une ligne : `id, date, saisi_le (minutes), type, libelle, article_id, reference, lot_id, lot, magasin_id, magasin, quantite, prix, devise, cours, document, document_id, document_numero, ordre_id, paire, motif, commentaire, auteur, contrepasse_id`. | `APS:74-87` |
| S65 | `GET /soldes` : lots et ce qu'ils portent, **un objet par lot** (agrégé sur ses magasins), tri référence → `entre_le` → id ; `en_stock=true` par défaut (soldes > POUSSIERE seulement) ; filtres `article_id`, `fournisseur_id` (fournisseur du lot **ou** de la matière), `magasin_id`, `q` (mots sur référence, désignation, n° de lot, rôle, code du magasin, nom du fournisseur du lot à défaut de la matière). Champs : `lot_id, lot, article_id, reference, designation, role, kg_par_ml, fournisseur, entre_le, poids_bobine` (du lot, à défaut catalogue), `bobines_palette, quantite, disponible, quarantaine, magasins[{magasin_id, magasin, type, quantite}]` (soldes non nuls), `bobines = round(quantite / poids_bobine)` (ou `null`), `statut`. | `APS:196-257` |
| S66 | `avec_historique=true` ajoute `entre`, `sorti`, `dernier_mouvement`, `ordres[{id, numero}]` (B.1.10). | `APS:249-256` |
| S67 | `GET /lots/{id}` : 404 si inconnu ; fiche complète : identité, matière, `poids_bobine` (lot sinon catalogue), fournisseur (lot sinon matière), `quantite` totale, `bobines`, `disponible`, `statut`, historique, `soldes` non nuls, `reception` = **la première réception validée** (par date) qui porte ce lot (`id, numero, date, bl, facture, pesee, qualite`), `mouvements` (tout le journal du lot, du plus ancien au plus récent ; prix masqués pour l'alimentation). | `APS:260-305` |
| S68 | `GET /controles/soldes` (**achats**, direction) : confronte chaque solde tenu à la somme du journal par `(lot, magasin)` ; écart > POUSSIERE listé ; compte les soldes négatifs (< −POUSSIERE) ; `conforme` = aucun écart et aucun négatif ; `lots` = nombre de soldes. | `APS:418-433` |

Refus :

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| SR13 | `decalage < 0` | 422 | `"Décalage négatif."` | `APS:105-106` |
| SR14 | lot inconnu (`/lots/{id}`) | 404 | `"Lot introuvable."` | `APS:263-265` |

### B.1.10 Historique d'un lot

`historique_lots(ids)` — `APS:156-193`.

| # | Règle | Référence |
|---|---|---|
| S70 | `dernier_mouvement` = la plus récente date d'effet, **toutes lignes comprises** (annulations et transferts compris). | `APS:175-176` |
| S71 | Ne comptent ni en entrée ni en sortie : les contre-passations, les lignes contre-passées, les transferts. | `APS:177-178` |
| S72 | « Entré » = ce que le lot a **reçu** (lignes > 0 hors retour machine) ; « Sorti » = sorties **nettes** : un `RETOUR_MACHINE` **réduit** le sorti (ce n'est pas une entrée) ; donc Entré − Sorti = Reste. (Recette direction 34.) | `APS:179-186` |
| S73 | `ordres` = les bons dont une ligne `SORTIE` (non annulée) a pris ce lot, triés par numéro. | `APS:187-192` |

### B.1.11 Opérations de stock (`OPE`) — règles communes

Cinq types de document « opération » : brouillon (corrigeable, supprimable, **sans numéro**, sans
effet) → validée (numérotée, écrite) → annulée (contre-passée, une fois).

| # | Règle | Référence |
|---|---|---|
| S80 | Types et libellés : `ouverture` « Stock d'ouverture », `retour_machine` « Retour des machines », `transfert` « Transfert entre magasins », `ajustement` « Ajustement justifié », `retour_fournisseur` « Retour au fournisseur ». Statuts `brouillon`, `validee`, `annulee` (CHECK base). | `MOD:764-798` |
| S81 | Séries de numéros (à la **validation**, M65) : ouverture `OUV`, retour machine `RET`, transfert `TRF`, ajustement `AJU`, retour fournisseur `RFO` → `OUV-2026-0001`… (année de la **date de l'opération**). | `OPE:25-26`, `OPE:409` |
| S82 | **Qui fait quoi** (`QUI`, un seul endroit) : ouverture → achats ; retour machine → alimentation ; transfert → achats **et** alimentation ; ajustement → achats ; retour fournisseur → achats. La direction passe partout. Les routes d'écriture exigent `STOCK` (achats ou alimentation) puis `_autorise(type)`. | `OPE:29-35`, `OPE:64-69` |
| S83 | Motifs proposés par type (liste **indicative**, non contrôlée par le serveur sauf quarantaine — voir B.9) : retour machine : « Reliquat de fin d'ordre », « Changement de série / arrêt machine », « Erreur de prélèvement » ; retour fournisseur : « Non-conformité qualité », « Excédent de réception », « Bobines endommagées », « Refus après quarantaine » ; ajustement : « Écart constaté au comptage », « Matière retrouvée », « Perte / casse », « Correction de saisie » ; transfert : « Rangement », « Libération de quarantaine », « Mise en quarantaine », « Approvisionnement de l'atelier ». | `OPE:36-45` |
| S84 | **Codes R1–R6 de l'ERP Fil** (parité, lus par le contrôle « retour sans motif » C03 et la traçabilité) : « Reliquat de fin d'ordre » R1, « Changement de série / arrêt machine » R2, « Erreur de prélèvement » R4 (famille retour des machines : R1, R2, R4) ; « Non-conformité qualité » R3, « Excédent de réception » R5, « Bobines endommagées » R6, « Refus après quarantaine » R3 (famille retour fournisseur : R3, R5, R6). `code_motif` est renvoyé avec chaque opération (vide si le motif n'est pas dans la table). Au moteur, `_code_motif` accepte aussi un motif qui **commence** par « R » + chiffre (reprise ERP Fil : « R1 … » → « R1 »). C03 vérifie aussi la **famille** du motif (commit `96db9ea`). | `OPE:46-53`, `OPE:183`, `DEP:226-233`, `CTL:92`, `CTL:222` |
| S85 | Libellés exacts des motifs de quarantaine : `LIBERATION = "Libération de quarantaine"`, `MISE_EN_QUARANTAINE = "Mise en quarantaine"`. | `OPE:54-55` |
| S86 | Type de mouvement écrit : ouverture → `OUVERTURE`, retour machine → `RETOUR_MACHINE`, ajustement → `AJUSTEMENT`, retour fournisseur → `RETOUR_FOURNISSEUR`, transfert → `TRANSFERT` (deux lignes). | `OPE:56-57` |
| S87 | `GET /operations/motifs` (tous) : `types`, `motifs`, `codes`, `droits` (type → rôles). | `OPE:72-75` |
| S88 | `GET /operations?type=` : 1 000 au plus, tri date ↓ puis id ↓ ; `GET /operations/{id}` (404 sinon). Chaque opération : `id, numero, type, type_libelle, statut, date, bon_id, bon (n°), fournisseur_id, fournisseur, motif, code_motif, commentaire, cree_par, validee_par, cree_le, validee_le, lignes[{id, article_id, reference, kg_par_ml, lot_id, lot (n° du lot, à défaut lot_numero), magasin_id, magasin, magasin_destination_id, magasin_destination, quantite, prix, devise}], total (Σ quantités signées), blocages`. Pour l'alimentation, `prix = null` et `devise = ""` sur les lignes (seulement sur ces deux routes de lecture). | `OPE:173-224` |
| S89 | Nom d'une opération dans le journal : son numéro, sinon `f"brouillon n° {o.id}"`. | `OPE:60-61` |

Saisie d'une opération (`OperationEntree`, `LigneOperation`) — `OPE:227-247` :

| Champ | Contrainte | Référence |
|---|---|---|
| `type` | texte ; inconnu → refus OR1 | `OPE:242`, `OPE:65-66` |
| `date` | obligatoire | `OPE:243` |
| `bon_id` | facultatif ; retenu **seulement** pour un retour des machines | `OPE:244`, `OPE:263` |
| `motif` | ≤ 80 | `OPE:245` |
| `commentaire` | ≤ 300 | `OPE:246` |
| `lignes` | au moins 1 | `OPE:247` |
| ligne.`article_id`, `magasin_id` | obligatoires | `OPE:228-231` |
| ligne.`lot_id` | facultatif ; `lot_numero` ≤ 80 | `OPE:229-230` |
| ligne.`magasin_destination_id` | facultatif (transfert) | `OPE:232` |
| ligne.`quantite` | −1e9 … 1e9 (signée pour l'ajustement) | `OPE:233` |
| ligne.`unite` | ≤ 10 car. ; vide = kg ; « kg », « Bobine », « Palette » | `OPE:236`, `PRO:30` |
| ligne.`prix` | 0 … 1e7 (≥ 0) | `OPE:237` |
| ligne.`devise` | ≤ 3, défaut « MAD » | `OPE:238` |

### B.1.12 Remplir un brouillon d'opération (`_remplir`, création et modification)

`OPE:250-332`. Tout est vérifié **dès le brouillon** (« dit tout de suite, plutôt qu'à la
validation »).

| # | Règle | Référence |
|---|---|---|
| S90 | `date_permise(date)` dès la saisie (audit 2 n° 2). | `OPE:251-252` |
| S91 | Motif **obligatoire** (non vide) pour retour machine, retour fournisseur, ajustement. Le transfert et l'ouverture n'en exigent pas (sauf quarantaine). | `OPE:253-254` |
| S92 | Un ajustement se **justifie** : commentaire d'au moins 5 caractères (après `strip`). | `OPE:255-256` |
| S93 | Un retour des machines se rattache à un ordre **validé** (`bon_id` d'un bon au statut `valide`) et n'est **pas daté avant l'ordre** (`date >= bon.date`). | `OPE:257-262`, `OPE:165-170` |
| S94 | L'en-tête est réécrit (`date`, `bon_id` si retour machine sinon `None`, `motif`, `commentaire`) ; **toutes** les lignes sont remplacées (supprimées puis recréées). | `OPE:263-265` |
| S95 | Par ligne : matière connue ; magasin connu ; si `lot_id` donné, le lot doit être de cette matière ; unité valide ; pas de bobine ni de palette pour un stock d'ouverture (« il fixe le prix au kilo »). | `OPE:267-281` |
| S96 | Conversion : `quantite = signe × en_unite_de_stock(article, lot, |quantite|, unite)` (B.2.1) : la quantité saisie en bobines ou palettes est ramenée en kilos, arrondie au millième ; le signe saisi est conservé. | `OPE:282-283` |
| S97 | **Ouverture** : devise MAD ou connue dans la table des devises (devise contrôlée — commit `f6f3acc`) ; numéro de lot obligatoire (`lot_numero` non vide, même si `lot_id` est donné) ; quantité > 0. Le prix (≥ 0, 0 admis) et la devise (en majuscules) sont gardés sur la ligne. | `OPE:284-291`, `OPE:326-327`, `T:test_valeur_et_dates.py:358-374` |
| S98 | **Ajustement** : un lot désigné (`lot_id`) **ou** nommé (`lot_numero`, matière retrouvée — le lot sera créé à la validation) ; quantité ≠ 0 (après conversion). | `OPE:292-296` |
| S99 | **Retour machine, transfert, retour fournisseur** : `lot_id` obligatoire ; quantité > 0. | `OPE:297-301` |
| S100 | **Transfert** : destination renseignée et différente de la source ; destination connue. **Libération** (source de type Quarantaine → destination non-quarantaine) : réservée aux achats et à la direction (403) et motif exactement « Libération de quarantaine ». **Mise en quarantaine** (source non-quarantaine → destination Quarantaine) : motif exactement « Mise en quarantaine » (l'atelier peut y mettre un lot douteux). Quarantaine → quarantaine : aucun motif imposé. | `OPE:302-318`, final-E « Décisions prises » |
| S101 | **Retour fournisseur** : les lots de toutes les lignes doivent avoir **le même fournisseur** (`lot.fournisseur_id`, `None` compté comme une valeur) ; `operation.fournisseur_id` = ce fournisseur (ou `None`). Aucun contrôle de type de magasin : on peut rendre depuis la quarantaine (« Refus après quarantaine »). | `OPE:319-320`, `OPE:329-332` |
| S102 | Ligne enregistrée : `lot_numero` = numéro saisi (strip) sinon celui du lot ; `magasin_destination_id` seulement pour un transfert ; `prix` et `devise` seulement pour une ouverture (sinon 0 et « MAD »). | `OPE:321-328` |

Refus de `_remplir` (dans l'ordre) :

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| OR1 | `type not in QUI` (création, ou `o.type` à la modification) | 422 | `"Type d'opération inconnu."` | `OPE:65-66` |
| OR2 | rôle ≠ direction et rôle ∉ `QUI[type]` | 403 | `f"« {m.TYPES_OPERATION[type_]} » est réservé à : " + ", ".join(m.ROLES[r].lower() for r in QUI[type_]) + "."` (ex. « « Stock d'ouverture » est réservé à : responsable achats. ») | `OPE:67-69` |
| OR3 | `date_permise` | 422 | D1, D2, D3 | `OPE:252` |
| OR4 | type ∈ {retour_machine, retour_fournisseur, ajustement} et `not e.motif` | 422 | `"Choisir le motif : il dit pourquoi le stock bouge."` | `OPE:253-254` |
| OR5 | ajustement et `len(e.commentaire.strip()) < 5` | 422 | `"Un ajustement se justifie : écrire en quelques mots ce qui a été constaté."` | `OPE:255-256` |
| OR6 | retour machine et (bon absent ou `bon.statut != "valide"`) | 422 | `"Un retour des machines se rattache à l'ordre d'où la matière revient."` | `OPE:258-261` |
| OR7 | retour machine et `date < bon.date` | 422 | `f"Ce retour est daté du {o_date:%d/%m/%Y}, avant l'ordre {bon.numero} du {bon.date:%d/%m/%Y} : la matière n'était pas encore partie. Dater le retour du jour où elle est revenue."` | `OPE:165-170`, `T:test_audit2_atelier.py:128-139` |
| OR8 | matière inconnue | 422 | `"Matière inconnue."` | `OPE:268-270` |
| OR9 | magasin (source) inconnu | 422 | `"Magasin inconnu."` | `OPE:271-273` |
| OR10 | `lot is not None and lot.article_id != a.id` | 422 | `"Ce lot est d'une autre matière."` | `OPE:275-276` |
| OR11 | `x.unite and x.unite not in UNITES` | 422 | `"Unité : kg, bobine ou palette — le cuir, les franges et le ruban se comptent aussi en kilos."` | `OPE:277-279` |
| OR12 | unité Bobine ou Palette et type ouverture | 422 | `"Un stock d'ouverture se saisit en kg : il fixe le prix au kilo."` | `OPE:280-281` |
| OR13 | conversion impossible (palette sans bobines par palette) | 422 | `f"« {article.reference} » : le nombre de bobines par palette n'est pas connu, saisir en bobines ou en kg."` | `PRO:58-60` |
| OR14 | conversion impossible (poids de bobine inconnu) | 422 | `f"« {article.reference} » : le poids de bobine n'est pas connu, saisir en kg."` | `PRO:61` |
| OR15 | ouverture, `devise.upper() != "MAD"` et devise absente de la table | 422 | `f"« {a.reference} » : devise inconnue (« {x.devise} »). L'ajouter d'abord dans Réglages › Devises, avec son cours."` | `OPE:285-287` |
| OR16 | ouverture et `not x.lot_numero.strip()` | 422 | `f"« {a.reference} » : le numéro de lot du stock d'ouverture manque."` | `OPE:288-289` |
| OR17 | ouverture et `quantite <= 0` | 422 | `"Un stock d'ouverture est positif."` | `OPE:290-291` |
| OR18 | ajustement, `lot is None and not x.lot_numero.strip()` | 422 | `"Désigner le lot ajusté (ou en nommer un, pour une matière retrouvée)."` | `OPE:293-294` |
| OR19 | ajustement et `quantite == 0` | 422 | `"Un ajustement ne peut pas être nul."` | `OPE:295-296` |
| OR20 | autres types et `lot is None` | 422 | `f"« {a.reference} » : choisir le lot."` | `OPE:298-299` |
| OR21 | autres types et `quantite <= 0` | 422 | `"La quantité est positive."` | `OPE:300-301` |
| OR22 | transfert et (destination absente ou = source) | 422 | `"Un transfert va d'un magasin à un autre."` | `OPE:303-304` |
| OR23 | transfert et destination inconnue | 422 | `"Magasin de destination inconnu."` | `OPE:305-307` |
| OR24 | libération et rôle ∉ {achats, direction} | 403 | `"Libérer une quarantaine est une décision des achats, après contrôle de la matière."` | `OPE:310-313` |
| OR25 | libération et `e.motif != "Libération de quarantaine"` | 422 | `f"Une sortie de quarantaine se fait avec le motif « {LIBERATION} »."` → « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». » | `OPE:314-315` |
| OR26 | mise en quarantaine et `e.motif != "Mise en quarantaine"` | 422 | `f"Une entrée en quarantaine se fait avec le motif « {MISE_EN_QUARANTAINE} »."` | `OPE:316-318` |
| OR27 | retour fournisseur et plus d'un fournisseur parmi les lots | 422 | `"Un retour au fournisseur ne mêle pas deux fournisseurs."` | `OPE:329-331` |

### B.1.13 Blocages annoncés sur un brouillon d'opération

`blocages_operation(s, o, magasins)` — `OPE:78-138`. Calculés **sans rien écrire**, renvoyés
dans `blocages` de chaque opération et utilisés par « À valider » (audit 2 n° 26). Liste vide pour
une opération non brouillon. Les raisons sont dédoublonnées dans l'ordre d'apparition.

| # | Raison annoncée (texte exact) | Condition | Réf. |
|---|---|---|---|
| OB1 | `"aucune ligne"` | aucune ligne | `OPE:84-85` |
| OB2 | message de `date_permise` | date refusée | `OPE:86-89` |
| OB3 | `f"l'inventaire {inv_numero} est en cours ({nom})"`, `nom` = code du magasin, ou « tous les magasins » | inventaire ouvert sur un magasin touché (source ou destination) ou global | `OPE:90-96` |
| OB4 | `f"lot {lot.numero} de {lot.article.reference} : " + ("épuisé" si présent ≤ POUSSIERE sinon f"{kg(present)} seulement") + f" dans « {code} », {kg(q)} demandés"` | Σ retiré par `(lot, magasin)` (transfert et retour fournisseur : la quantité ; ajustement négatif : sa valeur absolue) > solde actuel + POUSSIERE | `OPE:97-116` |
| OB5 | message SR8 / SR9 | assez aujourd'hui mais pas couvert à la date de l'opération | `OPE:117-123` |
| OB6 | `f"le magasin « {g.code} » est désactivé"` | magasin cible désactivé (la **destination** pour un transfert, sinon le magasin de la ligne) — sauf retour fournisseur | `OPE:124-128` |
| OB7 | `f"daté du {o.date:%d/%m/%Y}, avant l'ordre {bon.numero} du {bon.date:%d/%m/%Y}"` | retour machine daté avant son ordre | `OPE:129-133` |
| OB8 | `f"lot {lot.numero} : seulement {_quantite(sorti, lot)} partis pour cet ordre, {_quantite(rendu, lot)} rendus"` (`_quantite` = « x,xx kg », jamais « -0 ») | retour machine : rendu > sorti net + 0,001 | `OPE:134-137`, `OPE:141-143` |

### B.1.14 Créer, modifier, supprimer, valider, annuler une opération

| # | Règle | Référence |
|---|---|---|
| S110 | **Créer** (`POST /operations`, 201, rôle `STOCK` + OR1/OR2) : `numero = NULL`, `cree_par = nom`, `_remplir`, journal `f"{libellé en minuscules} (brouillon)"` (« stock d'ouverture (brouillon) », « retour des machines (brouillon) », « transfert entre magasins (brouillon) », « ajustement justifié (brouillon) », « retour au fournisseur (brouillon) »), objet `operation`, détail `brouillon n° {id}` ; commit. | `OPE:345-356` |
| S111 | **Verrou du document** : modifier, supprimer, valider, annuler relisent l'opération `SELECT … FOR UPDATE OF operation` : deux clics ne valident pas deux fois. | `OPE:359-363` |
| S112 | **Modifier** (`PUT /operations/{id}`) : brouillon seulement ; le type ne change pas ; `_remplir` ; journal « modification opération ». | `OPE:366-378` |
| S113 | **Supprimer** (`DELETE /operations/{id}`) : brouillon seulement ; suppression physique (lignes en cascade) ; journal « suppression opération » (détail : le nom) ; renvoie `{"ok": true}`. Aucun numéro consommé. | `OPE:381-392` |
| S114 | **Valider** (`POST /operations/{id}/valider`) : brouillon seulement ; `date_permise` ; re-contrôle de la libération pour un rôle autre qu'achats/direction (une libération préparée par les achats ne se valide pas par l'alimentation) ; **numéro attribué** (`numero(SERIES[type], date)`). | `OPE:395-409`, `T:test_stock_atelier.py:133-148` |
| S115 | Retour machine : le **bon est verrouillé** (`FOR UPDATE`) — deux retours du même ordre en même temps : le second attend puis relit ce qui est déjà revenu ; date ≥ date de l'ordre (OR7) ; pour chaque lot, Σ des lignes du retour (deux lignes du même lot s'additionnent) ≤ sorti net de l'ordre pour ce lot (+0,001), où sorti net = −Σ de **tous** les mouvements portant `ordre_id = bon` et ce lot (sorties, retours, contre-passations compris). Un lot qui n'est pas parti avec l'ordre a un sorti de 0 : refusé. | `OPE:410-419`, `OPE:146-162`, `T:test_parcours.py:367-389` |
| S116 | Écritures : transfert → `transferer` (deux lignes) ; sinon le lot est créé s'il manque (`lot_ou_creer(article, lot_numero, date)` : ouverture, ajustement « matière retrouvée ») et sa ligne prend le `lot_id` ; quantité négative pour un retour fournisseur, telle quelle sinon ; `prix`/`devise` de la ligne (seule l'ouverture en porte) — le cours est alors celui **du jour** de la devise (S18) ; `ordre_id = bon_id` pour un retour machine ; document « operation », `document_numero` = numéro, motif et commentaire de l'opération copiés sur chaque mouvement. | `OPE:420-435` |
| S117 | Statut `validee`, `validee_par`, `validee_le = maintenant()` ; journal `f"validation — {libellé en minuscules}"` (« validation — retour des machines »…). | `OPE:436-438` |
| S118 | **Recalage des bons de commande** (retour fournisseur et **tout** transfert) : `recaler_soldes(commandes_des_lots(lots des lignes), raison)` avec raison « retour au fournisseur » ou « sortie de quarantaine » — un retour au fournisseur rouvre le bon qu'il dégarnit ; une libération solde le bon qui n'attendait plus qu'elle (règles en partie A). | `OPE:335-342`, `OPE:439-440`, `T:test_parcours.py:201-213` |
| S119 | **Annuler** (`POST /operations/{id}/annuler`) : opération validée seulement ; `contrepasser_document("operation", id)` ; statut `annulee` ; journal « annulation opération » ; recalage des bons (raison `f"{numéro} annulé"`). Une opération ne s'annule qu'une fois. N'importe quel rôle autorisé pour le type annule (pas seulement l'auteur). | `OPE:445-457` |
| S120 | Les réponses des routes d'écriture renvoient l'opération **sans** masquage des prix (le masquage n'est appliqué qu'aux deux GET). | `OPE:356`, `OPE:378`, `OPE:442`, `OPE:457` |

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| OR28 | opération inconnue (GET, PUT, DELETE, valider, annuler) | 404 | `"Opération introuvable."` | `OPE:221-223`, `OPE:361-362` |
| OR29 | modifier et `statut != "brouillon"` | 409 | `"Une opération validée ne se modifie plus : l'annuler."` | `OPE:371-372` |
| OR30 | modifier et `e.type != o.type` | 422 | `"Le type d'une opération ne change pas."` | `OPE:373-374` |
| OR31 | supprimer et `statut != "brouillon"` | 409 | `"Une opération validée ne se supprime pas : l'annuler."` | `OPE:386-387` |
| OR32 | valider et `statut != "brouillon"` (validée **ou annulée**) | 409 | `"Cette opération est déjà validée."` | `OPE:400-401` |
| OR33 | valider, transfert, rôle ∉ {achats, direction}, une ligne de magasin Quarantaine vers non-quarantaine | 403 | `"Libérer une quarantaine est une décision des achats, après contrôle de la matière."` | `OPE:403-408` |
| OR34 | valider retour machine : `rendu > sorti + 1e-3` pour un lot | 409 | `f"Le lot « {lot.numero} » n'est sorti que de {_quantite(sorti, lot)} pour cet ordre ({_quantite(rendu, lot)} rendus) : on ne rend pas plus que ce qui est parti."` | `OPE:415-419` |
| OR35 | valider : refus de l'écriture | 409/422 | SR1–SR11 | `OPE:420-435` |
| OR36 | annuler et `statut != "validee"` | 409 | `"Seule une opération validée s'annule ; un brouillon se supprime."` | `OPE:450-451` |
| OR37 | annuler : déjà annulé / refus de l'écriture | 409/422 | SR12, SR2–SR9 | `OPE:452` |

### B.1.15 « À valider » et « Tout valider » (`BRO`)

Décision (final-E E9, « Décisions prises ») : valider d'un coup ce que l'atelier et le bureau ont
préparé, dans l'ordre des dates, chacun dans sa transaction.

| # | Règle | Référence |
|---|---|---|
| S130 | `GET /brouillons` (tous) : les ordres de fabrication et les opérations au statut brouillon, chacun avec `genre` (« ordre » / « operation »), `type`, `id`, `date`, `libelle`, `resume` (ordre : « 8F 120 m², … » ou « hors recette » + « · n lot(s) » ; opération : motif · deux premières références + « + n »), `quantite`, `cree_par`, `cree_le`, `blocages` (B.1.13, B.2.5), `peut_valider`, `lien` (`/sorties?onglet=brouillon&ordre={id}` ou `/operations?onglet={type}&operation={id}`). Totaux : `nombre`, `bloques`, `validables` (peut valider et sans blocage). | `BRO:38-84` |
| S131 | Tri : date, puis **rang du même jour** — ce qui apporte la matière avant ce qui la prend : ouverture 0, transfert 1, ajustement 2, ordre 3, retour machine 4, retour fournisseur 5 (autres 9) —, puis id. | `BRO:26-27`, `BRO:68` |
| S132 | `peut_valider` : direction toujours ; un ordre → alimentation seulement ; une opération → rôles de `QUI[type]`. Les achats **voient** les ordres sans pouvoir les valider. | `BRO:30-35`, `T:test_stock_atelier.py:161-197` |
| S133 | `POST /brouillons/valider` (rôle `STOCK`) : corps facultatif `{"brouillons": [{"genre": "ordre"|"operation", "id"}]}` (≤ 1 000) ; vide = tout ce que ce compte peut valider. Les brouillons retenus (peut valider, et dans la sélection) sont validés **dans l'ordre de S131**, chacun par la **même fonction** qu'une validation à l'unité (`valider_bon`, `operations.valider`, qui committent chacun) ; un refus (`HTTPException`) → `rollback`, ajouté à `refuses` avec `raison` = le message du refus ; une panne inattendue → `rollback`, `raison = f"erreur inattendue : {panne}"` ; on continue avec les suivants. Réponse : `valides[{genre, type, id, date, libelle, resume, lien, numero}]`, `refuses[{…, raison}]`, `ignores` = nombre demandé − nombre retenu (0 sans sélection). Un brouillon refusé reste brouillon, intact. | `BRO:86-125` |

### B.1.16 Inventaires (`INV`)

Principe (`INV:1-6`) : on fige le stock théorique, on compte lot par lot, on valide ; pendant
qu'il est ouvert, les mouvements sont suspendus sur le magasin compté (SR5) ; au-delà de la
tolérance un écart se justifie ; la validation écrit **un ajustement par écart**, lot par lot.

Modèle : `inventaire` (`numero` unique **obligatoire**, `libelle`, `statut` ∈ {ouvert, valide},
`date`, `magasin_id` facultatif = tous les magasins, `tolerance` défaut 0,02, `cree_par`,
`valide_par`, `valide_le` ; pas de `cree_le`) ; `inventaire_ligne` (`lot_id`, `magasin_id`,
`theorique`, `compte`, `nb_palettes`, `nb_bobines`, `second_compte`, `second_par`,
`justification` ≤ 300 ; unique `(inventaire, lot, magasin)`) — `MOD:825-867`.

| # | Règle | Référence |
|---|---|---|
| S140 | Comptage **retenu** = le second comptage (recompté par une autre personne) s'il existe, sinon le premier. | `INV:35-37` |
| S141 | **Hors tolérance** : pas de comptage → non ; écart (retenu − théorique) < POUSSIERE en valeur absolue → non ; sinon oui si théorique ≤ 0 (lot trouvé) **ou** `|écart| / théorique > tolérance` (strictement). | `INV:40-50` |
| S142 | **À recompter** : pas encore de second comptage et le **premier** comptage est hors tolérance. | `INV:53-55` |
| S143 | Tolérance par défaut = réglage `tolerance_inventaire` (« Tolérance d'écart d'inventaire », famille « Stock et inventaire », défaut 2 %, bornes 0–100 %) ; une tolérance donnée à l'ouverture (0–1) la remplace, figée sur l'inventaire. | `PAR:94-96`, `INV:259`, `INV:289` |
| S144 | **Valorisation des écarts** (en kilos **et** en dirhams — un net en kilos ne dit rien : 50 kg de trop à 10 MAD et 50 kg de moins à 90 MAD font 0 kg et 4 000 MAD de perte) : un inventaire validé valorise chaque écart au coût de **l'ajustement qu'il a écrit** (mouvement non annulé de ce document, même lot et magasin) ; sinon au **CMUP actuel** de la référence (`moteur.cmup_par_reference`). | `INV:58-85`, `INV:70-73` |
| S145 | Champs d'une ligne : `id, lot_id, lot, article_id, reference, designation, kg_par_ml, poids_bobine (lot sinon catalogue), bobines_palette, magasin_id, magasin, theorique, compte, justification, palettes, bobines, second_compte, second_par, retenu, ecart (null sans comptage), cmup_mad, valeur_ecart_mad, hors_tolerance, a_recompter`. En-tête : `id, numero, libelle, statut, date, magasin_id, magasin (« Tous les magasins » si global), tolerance, cree_par, valide_par, valide_le, nb_lignes, nb_comptees, hors_tolerance, a_recompter, recomptees, ecart_total (net kg), ecart_absolu, ecart_valeur_mad, ecart_valeur_absolue_mad` (+ `lignes` en détail). | `INV:87-121` |
| S146 | Pour l'alimentation : `ecart_valeur_mad`, `ecart_valeur_absolue_mad`, et par ligne `cmup_mad`, `valeur_ecart_mad` → `null`. | `INV:123-127`, `INV:161-162` |
| S147 | `GET /inventaires` (tous) : liste sans détail, id ↓. `GET /inventaires/{id}` (tous) : détail (404 sinon). | `INV:165-169`, `INV:247-252` |
| S148 | `GET /inventaires/defauts` (tous) : `tolerance` (réglage), `roles` et `compositions` des matières qui ont du stock (> POUSSIERE), `cadence_jours`. | `INV:172-186` |
| S149 | **Inventaire tournant** (`GET /inventaires/a-compter`, tous, `magasin_id` facultatif) : cadence par classe ABC — A 30 j, B 90 j, C 365 j (« pratique courante », codée en dur) ; classe de chaque matière = `moteur.etat_stock(aujourd'hui).classe_abc`, « C » à défaut. Dernier comptage = date du dernier inventaire **validé** ayant une ligne **comptée** (`compte` non nul) de cette matière **dans ce magasin**. Une matière est due dès qu'**un** magasin qui la détient (solde > POUSSIERE, quarantaine comprise) n'a jamais été compté ou l'a été il y a `>= cadence` jours (audit 2-G M2 : un fil compté à Morocco sortait du tournant avec ses 1 288 kg jamais comptés ailleurs ; commit `f6f3acc`). Par matière : `article_id, reference, role, classe_abc, stock` (Σ des magasins dus), `kg_par_ml, dernier_comptage` (le plus ancien des magasins dus, « jamais » l'emporte), `jours, magasins` (codes triés). Tri : classe A, B, C ; jamais compté d'abord, puis le plus ancien ; référence. | `INV:30-32`, `INV:189-244`, `T:test_valeur_et_dates.py:377-393` |
| S150 | **Ouvrir** (`POST /inventaires`, **achats**, 201) : `date_permise(date)` ; magasin connu (s'il est donné) ; pas d'autre inventaire ouvert sur ce magasin **ni global** (et pour un inventaire global : aucun inventaire ouvert du tout) ; matières citées connues ; classes ∈ {A, B, C}. | `INV:268-288` |
| S151 | **Périmètre** (cahier § 5.8, « par famille ou classe ABC ») : rien = tout le stock (du magasin) ; sinon les soldes qui passent **tous** les critères donnés : matières choisies (`articles`), rôles (`roles`), compositions (`compositions`), classes ABC (`classes_abc`, calculées comme S149). Seuls les soldes **> 0** sont figés (pas la règle POUSSIERE). Un inventaire global fige aussi la quarantaine. | `INV:255-265`, `INV:290-303` |
| S152 | Numéro `INV-AAAA-NNNN` attribué **à l'ouverture** (année de la date de l'inventaire) ; libellé par défaut « Inventaire ». | `INV:304-306` |
| S153 | **Verrou** : les soldes figés sont lus `FOR UPDATE OF solde` (un mouvement en cours finit d'abord, et il est compté) ; `theorique` = solde. | `INV:307-310` |
| S154 | **Pas d'inventaire daté avant le dernier mouvement** d'un lot qu'il fige (dans son magasin) : un comptage porte sur le stock d'aujourd'hui ; un ajustement daté avant écrirait l'écart dans le passé (commit `5ca0960`). | `INV:131-158`, `INV:311` |
| S155 | Journal « ouverture inventaire », objet `inventaire`, détail `f"{numero} · {n} lot(s) figés"`. | `INV:314-315` |
| S156 | **Compter** (`POST /inventaires/{id}/comptage`, **achats**, liste de `Comptage`) — inventaire verrouillé (`FOR UPDATE`), ouvert. Ligne existante (`ligne_id`) : `compte`, `justification`, `palettes`, `bobines` **remplacés** par ce qui est envoyé (absents → vidés) ; `second_compte` : **présent** dans la requête → posé (avec `second_par` = nom de qui l'enregistre) ou effacé (`null`) ; un recomptage exige un premier comptage ; **absent** → inchangé, sauf si le premier comptage est vidé (alors le second aussi). | `INV:320-360`, `T:test_stock_atelier.py:253-284` |
| S157 | **Lot trouvé** (pas de `ligne_id`) : matière, numéro de lot et magasin (celui du comptage ou celui de l'inventaire) obligatoires ; matière et magasin connus ; un inventaire d'un magasin ne reçoit de lot trouvé que dans ce magasin ; le lot est créé s'il n'existe pas (`entre_le` = date de l'inventaire) ; refusé s'il est déjà une ligne de l'inventaire ; nouvelle ligne `theorique = 0` avec le comptage. | `INV:361-375` |
| S158 | Journal « comptage », détail `f"{numero} · {n} ligne(s)"` ; commit. | `INV:376-377` |
| S159 | **Valider** (`POST /inventaires/{id}/valider`, **achats**) — verrouillé, ouvert ; au moins une ligne comptée ; tout écart hors tolérance **justifié** (≥ 3 caractères après `strip`) ; `date_permise(date)` ; pas de mouvement après la date sur les lots **en écart** (S154 relu : un lot trouvé a pu vivre après la date) ; pour chaque ligne comptée dont |retenu − théorique| ≥ POUSSIERE : `ecrire(type="AJUSTEMENT", quantite = écart, jour = date de l'inventaire, document "inventaire", document_numero = numéro, motif "Écart d'inventaire", commentaire = justification et « recompté par {second_par} » joints par « · », tronqué à 300)`. Une ligne **non comptée n'est pas ajustée** (pas d'écart supposé). Statut `valide`, `valide_par`, `valide_le` ; journal « validation inventaire », détail `f"{numero} · {n} lot(s) comptés · {k} ajustement(s)"`. | `INV:381-415` |
| S160 | **Abandonner** (`DELETE /inventaires/{id}`, achats) : inventaire ouvert seulement ; supprimé (lignes en cascade), rien n'est ajusté, les mouvements reprennent ; journal « abandon inventaire » (détail : numéro). Le numéro reste consommé ; les lots créés comme « lots trouvés » restent. | `INV:418-430` |
| S161 | **Feuille de comptage** (`GET /inventaires/{id}/feuille`, tous) : HTML imprimable A4 paysage, une page par magasin (tri par code), lots triés référence → `entre_le` → numéro ; colonnes N°, Référence (désignation dessous si différente), Lot, Conditionnement (« {poids 4 décimales sans zéros} kg / bobine · {n} bob. / palette »), [Théorique], Palettes, Bobines, Compté (kg), Observations ; en-tête « Compté par / Contrôlé par » ; pied : « Un lot trouvé sur place et absent de la liste : l'écrire au dos… », tolérance en %. **À l'aveugle par défaut** (sans le théorique) ; `theorique=true` l'ajoute ; `recomptage=true` ne garde que les lignes à recompter, **avec** le théorique, titre « Feuille de recomptage ». Sans ligne : « Aucun lot figé dans cet inventaire. ». | `INV:433-504`, final-E « Décisions prises » |
| S162 | Un inventaire validé ne bouge plus (comptage et validation refusés, IR8 ; abandon refusé, IR19) ; il n'existe **pas** de statut « annulé » ni de route qui contre-passe ses ajustements (voir B.9). | `INV:425`, `MOD:827` |

Refus des inventaires :

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| IR1 | inventaire inconnu (GET, comptage, valider, abandonner, feuille) | 404 | `"Inventaire introuvable."` | `INV:250-251`, `INV:339-340`, `INV:384-385`, `INV:422-423`, `INV:441-442` |
| IR2 | ouvrir : `date_permise` | 422 | D1, D2, D3 | `INV:271` |
| IR3 | ouvrir : `magasin_id` donné et inconnu | 422 | `"Magasin inconnu."` | `INV:272-273` |
| IR4 | ouvrir : un inventaire ouvert sur ce magasin ou global (ou n'importe lequel pour un global) | 409 | `f"L'inventaire {conflit.numero} est déjà ouvert sur ce magasin."` | `INV:274-281` |
| IR5 | ouvrir : matières inconnues | 422 | `"Matière inconnue : n° " + ", ".join(inconnus[:5]) + "."` | `INV:282-286` |
| IR6 | ouvrir : une classe ∉ {A, B, C} | 422 | `"Classe ABC : A, B ou C."` | `INV:287-288` |
| IR7 | ouvrir ou valider : un lot figé (en écart, à la validation) a un mouvement daté après la date | 409 | `f"L'inventaire est daté du {jour:%d/%m/%Y}, mais des lots qu'il fige ont bougé depuis : {', '.join(noms[:5])}{' …' if len(noms) > 5 else ''}. Un comptage porte sur le stock d'aujourd'hui : le dater au plus tôt du dernier mouvement."` avec chaque nom `f"« {lot.article.reference} », lot {lot.numero} (le {d:%d/%m/%Y})"` | `INV:150-158` |
| IR8 | comptage / valider : `statut != "ouvert"` | 409 | `"Cet inventaire est déjà validé."` | `INV:341-342`, `INV:386-387` |
| IR9 | comptage : `ligne_id` étranger | 422 | `"Ligne étrangère à cet inventaire."` | `INV:347-348` |
| IR10 | comptage : `second_compte` non nul et `compte` nul | 422 | `f"« {x.lot.article.reference} », lot {x.lot.numero} : un recomptage suit un premier comptage."` | `INV:352-354` |
| IR11 | lot trouvé sans matière, numéro ou magasin | 422 | `"Un lot trouvé se décrit : matière, numéro de lot, magasin."` | `INV:361-362` |
| IR12 | lot trouvé : matière inconnue | 422 | `"Matière inconnue."` | `INV:363-364` |
| IR13 | lot trouvé : magasin inconnu | 422 | `"Magasin inconnu."` | `INV:365-366` |
| IR14 | lot trouvé dans un autre magasin que celui de l'inventaire | 422 | `"Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé."` | `INV:367-368` |
| IR15 | lot trouvé déjà dans l'inventaire | 422 | `"Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne."` | `INV:371-372` |
| IR16 | valider : aucune ligne comptée | 422 | `"Aucun lot compté : saisir les comptages avant de valider."` | `INV:389-390` |
| IR17 | valider : écart(s) hors tolérance avec justification < 3 caractères | 422 | `"Écart hors tolérance sans justification : " + ", ".join(références[:8]) + "."` | `INV:391-394` |
| IR18 | valider : `date_permise` ; refus d'écriture | 422/409 | D1–D3 ; SR3–SR9 | `INV:395`, `INV:406` |
| IR19 | abandonner un inventaire validé | 409 | `"Un inventaire validé reste : ses ajustements sont au journal."` | `INV:424-425` |
| IR20 | schéma : `tolerance` hors 0–1 ; `compte`, `second_compte` hors 0–1e9 ; `palettes` hors 0–1e5 ; `bobines` hors 0–1e6 ; `libelle` > 120 ; `justification`, > 300 ; `lot_numero` > 80 | 422 | message traduit (C2) | `INV:255-332` |

### B.1.17 Période close et coût figé d'un mois clos

| # | Règle | Référence |
|---|---|---|
| S170 | Réglage `date_cloture` (« Période close jusqu'au », famille Société, vide par défaut) : rien ne s'écrit plus à cette date **ni avant** (D3) — ni saisie antidatée, ni contre-passation (datée de l'original), ni brouillon (refusé dès la saisie). | `PAR:138-139`, `SEC:219-226`, cahier § 5.2 |
| S171 | Seule la **direction** règle la date (`PUT /parametres`) ; on ne clôt qu'une **période passée** (`date < aujourd'hui`) ; la vider rouvre tout ; chaque changement est historisé et journalisé (B.5.7). | `CPT:312-317` |
| S172 | Le **coût** d'une marchandise entrée dans un mois clos ne change plus (frais, cours, rattachement, réouverture, suppression d'un dossier ; changement de clé ou de nature d'un poste de frais) : refus D4 de `cout_hors_periode_close` (partie A § 0.5) ; corriger = la direction rouvre la période (tracé), on saisit, elle referme (commits `f6f3acc`, `f216509`). | `SEC:235-276`, `IMP:610…839`, `RIM:169` |
| S173 | Essai : « un mois clos ne se revalorise pas » ; « une période close ne bouge plus » (ouverture datée d'hier refusée avec « clos » dans le message). | `T:test_valeur_et_dates.py:241`, `T:test_parcours.py:326-338` |

### B.1.18 La base traduite pour le moteur (`DEP`)

Le moteur de calcul est celui de l'ERP Fil (vérifié au centime) ; il ne lit pas la base, il
reçoit un instantané `Donnees` fabriqué par `depot.charger`.

| # | Règle | Référence |
|---|---|---|
| S180 | Articles par **référence**, lots par **numéro**, magasins par **code** : le moteur ne connaît que ces clés. | `DEP:1-7` |
| S181 | Statut d'une commande pour le moteur : brouillon et à approuver → « Brouillon » ; envoyée « Envoyée », confirmée « Confirmée », soldée « Soldée », annulée « Annulée » ; **mais** un bon déjà numéroté (parti) qui repasse par la direction reste « Confirmée » (toutes ses lignes ont un prix confirmé) ou « Envoyée ». Qualité de réception : conforme « Conforme », réserve « Réserve », refusé « Refusé ». | `DEP:23-40` |
| S182 | Solde « à la main » d'un bon : la dernière action « commande soldée » du journal, si son détail ne finit pas par « tout reçu ». | `DEP:43-52` |
| S183 | Reçu net par ligne de commande = pesées des réceptions **validées**, lignes non refusées, **moins** les retours au fournisseur du lot répartis au prorata des pesées du lot (sans dépasser la pesée de la ligne) ; « en quarantaine » par ligne = la part sous réserve encore en magasin Quarantaine, au prorata. (Détail : partie A.) | `DEP:59-128` |
| S184 | Poids de bobine **mesuré** par matière (M43) : celui du lot **sorti** le plus récemment vers les machines (SORTIE < 0, lot pesé), sinon celui du dernier lot **reçu** (pesé) ; renvoie `(kg, n° de lot, « sorti » | « reçu »)`. Sert aux fils montés. | `DEP:131-149` |
| S185 | Versions du plan : actions « plan de production » sur l'objet `qualite` dont le détail contient `plan=` suivi du JSON `{"avant": {b, c, a}, "apres": {…}}` ; illisible → ignoré. Le plan d'avant le premier changement vaut « depuis toujours » (croissance comptée depuis l'ouverture = premier mouvement) ; seule une nouvelle **base** déplace l'origine de la croissance (un coefficient de saisonnalité seul ne la remet pas à zéro). Une qualité arrêtée sans arrêt tracé : son plan vaut jusqu'à la fin du mois de son **dernier ordre validé** (rien du tout si jamais tissée), au plus tard jusqu'à la première version tracée. | `DEP:153-223`, `DEP:283-313`, commit `db25831`, `30b31c3` |
| S186 | Versions de recette (`recette_version`) passées au moteur par code qualité, JSON illisible ignoré. | `DEP:314-325` |
| S187 | Réceptions **annulées** exclues (ni pesée, ni OTIF, ni prix) ; numéros provisoires `BC-brouillon-{id}`, `REC-brouillon-{id}` ; une réception de plusieurs bons n'est jugée à l'heure sur aucun d'eux seul (`numero_bc` vide). | `DEP:339-418` |
| S188 | Ordres passés au moteur : bons **validés** seulement, avec leur prévu figé (`theorique` JSON : `fils`, `perte`) et `valide_le`. | `DEP:486-497` |
| S189 | **Traduction du journal** : quantité **positive** et signe porté par le type pour les types à signe ± fixe ; mais un `AJUSTEMENT` (signe +1 au moteur) garde sa quantité **signée** et une contre-passation garde la quantité opposée (le moteur reçoit donc parfois des quantités négatives) ; un transfert = **une** ligne moteur source → destination (les deux lignes appariées par `paire`) ; `motif_retour` = code R ; `numero_of` = n° du bon ; `fournisseur` = celui **du lot** ; `cours` = cours figé ; `ligne_reception_id` = la ligne de réception de l'entrée (appariée dans l'ordre des lignes, ou, pour une entrée reprise de l'ERP Fil sans réception, par lot + date + poids). | `DEP:562-660` |
| S190 | **Cache** des données du moteur (relire un an de journal coûte ~0,5 s) : gardé tant que la **signature** ne change pas — (date du jour, max id du journal d'audit, max id des mouvements, max `modifie_le` des paramètres, nombre de mouvements, Σ des soldes) ; un cache par variante `avec_journal` ; protégé par un verrou de thread. Un chiffre affiché n'est jamais périmé (`T:test_parcours.py:419`). | `DEP:663-703` |
| S191 | `charger_au(jour)` : les données « le soir du `jour` » — le journal rejoué jusqu'à cette date (`moteur.a_la_date`). `controler(…)` : contrôles de stock et de plan sur les données du jour, contrôles d'intégrité (C12, C14, C27, C37) sur **toutes** les données. | `DEP:686-712` |

---

## B.2 Production : ordres de fabrication, retours, plan, réalisé, besoins

Vocabulaire : le **bon de sortie** (`bon_sortie`) **est** l'ordre de fabrication (OF) : ce qu'on
tisse (une ou plusieurs qualités et leurs m²) et les fils (lots) qu'on envoie aux machines
(`PRO:1-8`, `MOD:699-730`). Exigences M64, M67, M68 : un OF sert **une fois, un jour** ; un OF
porte plusieurs fils, plusieurs lots, une ou plusieurs qualités ; ses numéros suivent les dates.

### B.2.1 Unités de saisie

| # | Règle | Référence |
|---|---|---|
| P1 | Unités admises : « kg », « Bobine », « Palette » ; vide = kg. Le stock est **toujours en kilos**, cuir, franges et ruban compris (décision de Mohamed du 8 octobre 2026, commits `d2e1e39`, `b75bc24`) ; leurs mètres (kg ÷ densité) ne sont qu'indicatifs. | `PRO:30`, `PRO:35-47`, cahier § 5.2 |
| P2 | Contenance d'une unité : kg → 1 ; Bobine → poids de bobine **mesuré du lot** s'il est connu (> 0), sinon celui du catalogue ; Palette → bobine × `bobines_palette` (0 si inconnu). | `PRO:35-47` |
| P3 | `en_unite_de_stock` = `round(quantite × contenance, 3)` (au gramme). Une bobine ou une palette peuvent être fractionnaires (aucun contrôle d'entier côté serveur). | `PRO:50-62` |

Refus : OR11 (unité inconnue, `PRO:53-55`), OR13 (palette sans bobines par palette,
`PRO:58-60`), OR14 (poids de bobine inconnu, `PRO:61`).

### B.2.2 Lots présents à une date

| # | Règle | Référence |
|---|---|---|
| P5 | `presents_au(magasin, lots, jour)` : ce que chaque lot peut donner **à la date `jour`** dans ce magasin. Un lot dont `entre_le > jour` donne **0**. Sinon on part du solde d'aujourd'hui et on remonte jour par jour les mouvements datés **après** `jour` : le plus **bas** de ces soldes du soir (aujourd'hui compris) est ce qu'on peut encore prendre (ce qui est sorti depuis est déjà parti) ; jamais négatif. C'est `couvert_a_sa_date` dit en quantité. | `PRO:117-153` |
| P6 | `disponibles_au(article, magasin, jour)` : les lots disponibles (S50, hors quarantaine, FIFO) ; si `jour` est vide ou ≥ aujourd'hui → tels quels ; sinon quantités ramenées à `presents_au` et lots à ≤ POUSSIERE retirés. | `PRO:156-163` |

### B.2.3 Proposition de sortie (FIFO à la date de l'ordre)

`POST /bons/proposition` (tous ; n'écrit rien) — corps `Demande` : `fabrications` (≥ 1, chaque
`qualite_id` et `m2` ∈ ]0 ; 1e8]), `magasin_id`, `date` facultative (aujourd'hui sinon) —
`PRO:177-237`.

| # | Règle | Référence |
|---|---|---|
| P10 | Chaque qualité doit être connue (404) et **en service** (422) — une qualité arrêtée ne part plus (commit `202d1a0`). Les m² d'une même qualité citée deux fois s'additionnent. | `PRO:166-174`, `PRO:196-198` |
| P11 | Besoin par fil = Σ sur les lignes de nomenclature (`moteur.nomenclature`, kg/m² > 0) des qualités demandées de `kg_m2 × m² × (1 + taux_perte)` — **perte comprise**, comme Production & besoins (recette atelier n° 4 : 100 m² × 1 kg/m² → 102 kg). Un fil qui sert plusieurs qualités n'apparaît **qu'une fois**, avec `par_qualite` (besoin par code qualité). Les rôles au mètre (cuir, franges, ruban) sont en kilos : ml/m² × densité. | `PRO:199-217`, `T:test_stock_atelier.py:308-322` |
| P12 | Pour chaque fil : lots `disponibles_au(fil, magasin, date)` (hors quarantaine, FIFO par date d'entrée du lot, présents à la date), poids de bobine du lot à défaut celui du catalogue ; on prend dans l'ordre `min(lot, reste)` jusqu'à couvrir (seuil 1e-6), `proposee` arrondie au gramme ; `manque = max(0, reste)`. | `PRO:218-230`, `T:test_audit2_atelier.py:59-95` |
| P13 | Réponse : `theorique` (Σ), `manque` (Σ), `taux_perte`, `recettes_incompletes`, `lignes` triées par rôle puis référence, chacune `{article_id, reference, designation, role, theorique, par_qualite, kg_par_ml, poids_bobine, bobines_palette, lots[{…, proposee}], manque, disponibles}`. | `PRO:231-237` |
| P14 | **Recette incomplète** signalée (au lieu d'omettre en silence) pour chaque qualité demandée dont le contrôle de recette a un écart : rôle sans matière → `f"{qualite} : le rôle {role} pèse {poids:g} au m², mais la recette ne nomme aucune matière pour lui : rien ne lui est proposé. La direction doit compléter la recette."` ; parts ≠ 100 % → `f"{qualite} : le rôle {role} fait {somme:g} % dans la recette au lieu de 100 % : sa proposition est faussée. La direction doit corriger la recette."` (commit `e44613f`). | `PRO:93-114` |
| P15 | La proposition **ne vérifie pas** le magasin (inconnu ou quarantaine → aucune proposition, pas de refus) ni la date (future → stock d'aujourd'hui). | `PRO:190-237` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR1 | qualité inconnue | 404 | `"Qualité inconnue."` | `PRO:168-170` |
| PR2 | qualité arrêtée (`not q.actif`) | 422 | `f"La qualité {q.code} est arrêtée : elle ne se tisse plus. La direction la remet en service (Qualités) si une série doit encore partir."` | `PRO:171-173` |

### B.2.4 Brouillon d'ordre : saisie et contrôles

Corps `BonEntree` (`PRO:240-253`) : `date` (obligatoire), `magasin_id`, `metier_id` facultatif,
`commentaire` ≤ 300, `fabrications` (liste, **vide admise** = ordre « hors recette »), `lignes`
(≥ 1 : `article_id`, `lot_id` **obligatoire**, `quantite` ∈ ]0 ; 1e9], `unite`).

| # | Règle | Référence |
|---|---|---|
| P20 | Magasin connu et **pas de type Quarantaine** (la matière en quarantaine ne part pas aux machines — cahier § 6 règle 6) ; métier connu s'il est donné ; `date_permise` dès le brouillon ; une qualité **une seule fois** par ordre (additionner ses m²) ; chaque qualité connue et en service (P10). | `PRO:256-269`, `PRO:274-276` |
| P21 | En-tête réécrit (`date`, `magasin_id`, `metier_id`, `commentaire`) ; fabrications et lignes **entièrement remplacées**. | `PRO:270-273` |
| P22 | Chaque ligne : matière et lot connus **et** le lot est de cette matière ; quantité convertie en kilos (P3). Un même lot peut figurer sur plusieurs lignes (additionné aux contrôles). Une matière hors recette est admise (ordre « hors recette » ou fil ajouté à la main). Le magasin désactivé n'est pas refusé (on peut en sortir, S12). | `PRO:277-283` |
| P23 | Contraintes base : `bon_fabrication.m2 > 0`, `bon_ligne.quantite > 0`, `bon_sortie.statut IN ('brouillon','valide','annule')`, `numero` unique (nul en brouillon). | `MOD:707`, `MOD:735`, `MOD:747` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR3 | magasin inconnu | 422 | `"Magasin inconnu."` | `PRO:258-259` |
| PR4 | magasin de type Quarantaine | 422 | `"La matière en quarantaine ne part pas aux machines : la libérer d'abord (transfert « Libération de quarantaine », décidé par les achats)."` | `PRO:260-262` |
| PR5 | `metier_id` donné et inconnu | 422 | `"Métier inconnu."` | `PRO:263-264` |
| PR6 | `date_permise` | 422 | D1, D2, D3 (essai : « 1999-12-31 » → « ancienne ») | `PRO:266`, `T:test_stock_atelier.py:105-113` |
| PR7 | une qualité citée deux fois | 422 | `"Une qualité ne figure qu'une fois sur un ordre : additionner ses m²."` | `PRO:267-269` |
| PR8 | qualité inconnue / arrêtée | 404 / 422 | PR1 / PR2 | `PRO:275` |
| PR9 | matière ou lot inconnu, ou lot d'une autre matière | 422 | `"Lot inconnu, ou d'une autre matière."` | `PRO:278-281` |
| PR10 | unité / conversion | 422 | OR11, OR13, OR14 | `PRO:283` |

### B.2.5 Blocages annoncés sur un brouillon d'ordre

`blocages_bon(s, b, dernier)` — `PRO:290-318` (vide si l'ordre n'est pas brouillon). Annoncés
sur l'ordre, dans « À valider », et Valider grisé à l'écran (recette atelier 22).

| # | Raison annoncée (texte exact) | Condition | Réf. |
|---|---|---|---|
| PB1 | `"aucune matière à sortir"` | aucune ligne | `PRO:296-297` |
| PB2 | message de `date_permise` | date refusée | `PRO:298-301` |
| PB3 | `f"un ordre daté du {dernier:%d/%m/%Y} est déjà validé : dater ce bon au moins de ce jour"` | `b.date < dernier` (dernier = date max des ordres **non brouillons** : validés **et annulés**) | `PRO:286-287`, `PRO:302-304` |
| PB4 | `f"« {magasin.code} » est un magasin de quarantaine"` | magasin de type Quarantaine | `PRO:307-308` |
| PB5 | `f"l'inventaire {ouvert} est en cours sur « {magasin.code} »"` | inventaire ouvert sur ce magasin ou global | `PRO:309-313` |
| PB6 | `"qualité arrêtée : " + ", ".join(codes)` | une fabrication sur une qualité arrêtée | `PRO:314-316` |
| PB7 | lots manquants (P30) | voir ci-dessous | `PRO:317` |

**Lots manquants** (`lots_manquants`, `PRO:321-354`) — par lot (lignes du même lot additionnées) :

| # | Règle / texte | Réf. |
|---|---|---|
| P30 | Si la quantité voulue ≤ présent à la date (P5) + POUSSIERE : on applique en plus `couvert_a_sa_date` (sans écrire) ; un refus donne `f"lot {lot.numero} de {reference} : {refus.detail}"`. | `PRO:333-343` |
| P31 | Sinon : état = `f"entré le {entre_le:%d/%m/%Y}, après la date de l'ordre"` si le lot est entré après la date ; `"épuisé" + passe` si présent ≤ POUSSIERE ; sinon `f"{kg(q, 3)} kg seulement{passe}"`, avec `passe = f" au {b.date:%d/%m/%Y}"` si l'ordre est daté avant aujourd'hui, sinon vide. Message : `f"lot {lot.numero} de {reference} : {etat} dans « {code magasin ou '?'} », {kg(voulu, 3)} kg demandés"`. | `PRO:344-353` |

### B.2.6 Créer, modifier, supprimer un brouillon d'ordre

| # | Règle | Référence |
|---|---|---|
| P40 | Créer (`POST /bons`, 201, **alimentation** + direction) : `cree_par` = nom ; `_remplir` ; journal « bon de sortie (brouillon) », objet `bon`, détail `f"{n} fil(s), {total:,.1f} kg"` (séparateur de milliers « , » à l'anglaise, voir B.9). | `PRO:436-446` |
| P41 | Le bon est relu `FOR UPDATE OF bon_sortie` pour modifier, supprimer, valider, annuler. | `PRO:449-453` |
| P42 | Modifier (`PUT /bons/{id}`) : brouillon seulement ; journal « modification bon de sortie » (détail vide). | `PRO:456-465` |
| P43 | Supprimer (`DELETE /bons/{id}`) : brouillon seulement ; journal « suppression bon de sortie » ; `{"ok": true}`. | `PRO:468-477` |
| P44 | Les **achats** ne créent ni ne valident d'ordre (403) : ils lisent. | `T:test_parcours.py:85`, cahier § 4 |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR11 | bon inconnu (GET, PUT, DELETE, valider, annuler) | 404 | `"Bon introuvable."` | `PRO:451-452`, `PRO:586-587` |
| PR12 | modifier un bon non brouillon | 409 | `"Un bon validé ne se modifie plus : l'annuler, puis en faire un autre."` | `PRO:460-461` |
| PR13 | supprimer un bon non brouillon | 409 | `"Un bon validé ne se supprime pas : l'annuler."` | `PRO:472-473` |

### B.2.7 Valider un ordre (numéro, prévu figé, sorties sous verrou)

`POST /bons/{id}/valider` (alimentation + direction) — `PRO:496-530`.

| # | Règle | Référence |
|---|---|---|
| P50 | Brouillon seulement ; `date_permise` ; aucune qualité arrêtée ; **lots présents à la date de l'ordre** (P30-P31 : la proposition ne prend que ceux-là, la validation le vérifie pour une saisie à la main ou un brouillon gardé quelques jours — commit `202d1a0`). | `PRO:500-512` |
| P51 | **Verrou consultatif** `pg_advisory_xact_lock(7426110)` (constante `VERROU_ORDRES`) **avant** de lire la date du dernier ordre : deux validations au même instant se suivent — sinon les deux passaient et les numéros ne suivaient plus les dates (commit `a794812`, essai `T:test_audit2_atelier.py:248-270`). Le verrou est libéré à la fin de la transaction. | `PRO:31-32`, `PRO:513-516` |
| P52 | **Les numéros suivent les dates** (M67) : refus si `b.date < max(date des ordres non brouillons)` (validés **et annulés**) ; la même date est admise. Consigne d'atelier pour une sortie oubliée hier : dater du dernier ordre et écrire la vraie date en commentaire (recette atelier 12). | `PRO:516-519`, final-E recette « Atelier 12 » |
| P53 | Numéro `OF-AAAA-NNNN` (année de la date de l'ordre), donné **à la validation**. | `PRO:520` |
| P54 | **Prévu figé** (`bon_sortie.theorique`, JSON `{"perte": taux_perte, "fils": {référence: kg hors perte}}`) : Σ `kg_m2 × m²` par fil sur la nomenclature du moment des qualités de l'ordre. Modifier ensuite une recette ou un poids au m² ne réécrit pas l'écart de cet ordre (étape de schéma 9, commit `db25831`). Vide pour un ordre validé avant cette étape (le moteur le recalcule alors avec la recette de son jour). | `PRO:480-493`, `PRO:521`, `MOD:722-726` |
| P55 | Une **sortie** par ligne : `ecrire(type="SORTIE", quantite = −kg, jour = date de l'ordre, document "sortie", document_id = bon, document_numero = numéro, ordre_id = bon)` — tout passe ou rien (verrou de solde, inventaire ouvert, solde, couvert à sa date). | `PRO:522-525` |
| P56 | Statut `valide`, `valide_par`, `valide_le` ; journal « validation bon de sortie », détail `f"{numero} · {n} fil(s) · {total:,.1f} kg"`. | `PRO:526-529` |

| # | Condition exacte | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR14 | `statut != "brouillon"` (validé ou annulé) | 409 | `"Ce bon est déjà validé."` | `PRO:500-501` |
| PR15 | `date_permise` | 422 | D1, D2, D3 | `PRO:502` |
| PR16 | qualités arrêtées | 409 | `f"Qualité arrêtée ({', '.join(arretees)}) : elle ne se tisse plus. La retirer de l'ordre, ou demander à la direction de la remettre en service."` | `PRO:503-506` |
| PR17 | lots manquants | 409 | `"À la date de l'ordre, " + " ; ".join(manquants) + ". Choisir un autre lot, ou dater l'ordre du jour où la matière était là."` | `PRO:509-512` |
| PR18 | `dernier and b.date < dernier` | 409 | `f"Un ordre daté du {dernier:%d/%m/%Y} existe déjà : les numéros suivent les dates, un bon ne se valide pas à une date antérieure."` | `PRO:517-519` |
| PR19 | refus d'écriture | 409/422 | SR3–SR9 (dont SR5 inventaire ouvert, SR6 deux sorties simultanées sur la même palette → une seule passe) | `PRO:523`, `T:test_parcours.py:238-261`, `T:test_parcours.py:264-275` |

### B.2.8 Retours des machines

Le retour des machines est une **opération** `retour_machine` (B.1.11-B.1.14) rattachée à
l'ordre (`bon_id`) : série `RET`, motif obligatoire (R1, R2, R4), réservé à l'alimentation
(+ direction), daté au plus tôt du jour de l'ordre, jamais plus que le sorti net de l'ordre par
lot (verrou sur l'ordre). Le mouvement `RETOUR_MACHINE` porte `ordre_id`.

| # | Règle | Référence |
|---|---|---|
| P60 | `retours_par_ordre(ids)` : les retours d'un ordre se lisent **au journal** (mouvements `RETOUR_MACHINE` avec `ordre_id`), hors contre-passations et lignes contre-passées ; regroupés par (document, id du document s'il s'agit d'une opération, date) : `{id, numero, date, quantite}` — `numero` = n° de l'opération, ou `f"retour repris de l'ERP Fil du {date:%d/%m/%Y}"` pour un retour **sans document** (reprise de l'ERP Fil). | `PRO:357-382` |
| P61 | `GET /bons/{id}/lots-sortis` (tous) : ce que l'ordre a emporté, lot par lot, **net** des retours (−Σ de tous les mouvements `ordre_id = bon`, contre-passations comprises), seulement > 0,001 : `{lot_id, lot, article_id, reference, sorti_net, kg_par_ml, bobines_palette, poids_bobine}` — ce qui peut revenir. | `PRO:591-607` |

### B.2.9 Annuler un ordre (avec ses retours) — « ordre repris »

`POST /bons/{id}/annuler` (alimentation + direction) — `PRO:557-580`. Décisions : recette
atelier 6 (commit `a536296`) et audit 2 (commit `202d1a0` : « Annuler un ordre repris comptait
ses retours deux fois — 2 793 kg de stock fantôme sur 84 ordres »).

| # | Règle | Référence |
|---|---|---|
| P70 | Seul un ordre **validé** s'annule ; un brouillon se supprime. | `PRO:561-562` |
| P71 | Annuler un ordre, c'est annuler **aussi tout ce qui en est revenu** (sinon la matière rendue compterait deux fois) — **tout passe, ou rien** (une seule transaction) : (1) contre-passation des sorties de l'ordre (document « sortie ») ; (2) pour chaque opération `retour_machine` **validée** de cet ordre : contre-passation, statut `annulee`, journal « annulation opération » détail `f"{r.numero} (avec {b.numero})"` ; (3) les **retours sans document** (repris de l'ERP Fil) encore actifs sont contre-passés un par un (`commentaire = f"Annulation du mouvement n°{x.id} (avec {b.numero})"`, datés de l'original, même document que l'original). | `PRO:563-574`, `PRO:533-554` |
| P72 | Statut `annule` ; journal « annulation bon de sortie », détail `numero` + `f" et {n} retour(s)"` si des retours ont été annulés. Le numéro reste attribué (pas de trou). | `PRO:575-579` |
| P73 | Un retour encore **brouillon** de cet ordre reste brouillon ; sa validation sera refusée (sorti net 0, OR34). | `OPE:415-419` |
| P74 | Un ordre annulé ne consomme rien : exclu de la consommation (`/ordres-fabrication`), du bilan, du moteur (seuls les validés lui sont passés) ; ni ses sorties ni ses retours contre-passés ne comptent. Il compte pourtant comme « dernier ordre » pour PB3/PR18. | `PIL:690-705`, `DEP:487`, commit `db25831` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR20 | `statut != "valide"` | 409 | `"Seul un bon validé s'annule ; un brouillon se supprime."` | `PRO:561-562` |
| PR21 | refus de contre-passation (période close, inventaire ouvert, matière revenue déjà ressortie, déjà annulé) | 409/422 | SR12, D3, SR5, SR6, SR8/SR9 | `PRO:567-574` |

### B.2.10 Lecture d'un ordre et de sa consommation

| # | Règle | Référence |
|---|---|---|
| P80 | Consommation par ordre (`moteur.consommation_par_of`) ajustée pour l'atelier (`ajuster_ordre`) : prévu par fil = théorique × (1 + perte) — **perte comprise**, la même règle que la proposition et Production & besoins ; un ordre validé garde **son** taux de perte figé (`taux_perte_fige`) ; `kg_par_ml` par fil ; `ecart` par fil = sorti − prévu (si le moteur en donne un) ; totaux `theorique`, `net` (sorti net des retours), `ecart = net − theorique` et `ecart_relatif = écart / theorique` (null sans théorique), `taux_perte`. | `PRO:65-90` |
| P81 | Fiche d'un ordre (`bon_dict`) : `id, numero, statut, date, magasin_id, magasin, metier_id, metier (nom à défaut code), commentaire, cree_par, valide_par, cree_le, valide_le, fabrications[{qualite_id, qualite, nom, m2}], lignes[{id, article_id, reference, designation, kg_par_ml, lot_id, lot, quantite, poids_bobine, bobines_palette}], total (Σ kg), retours (n°), retours_detail, revenu (Σ kg revenus, reprise comprise), theorique, net (à défaut Σ des lignes), ecart, ecart_relatif, par_fil, blocages`. Pas de prix. | `PRO:385-416` |
| P82 | `GET /bons?du=&au=` (tous) : tous les ordres (brouillons, validés, annulés), date ↓ puis id ↓. `GET /bons/{id}` (tous). | `PRO:419-433`, `PRO:583-588` |
| P83 | `GET /export/sorties?statut=&du=&au=` (tous) : classeur « Sorties » des ordres d'un statut (`valide` par défaut, `brouillon`, `annule`) : Ordre (« Brouillon » sans n°), Date (JJ/MM/AAAA), Fabrication (« 8F 1 200 m² · … » ou « hors recette »), m², Métier, Magasin, Prévu par la recette (kg), Sorti net (kg), Écart (kg), Écart (%), Revenu (kg), Retours, Commentaire, Par ; titre « Sorties vers les machines ({validées|brouillons|annulées}) — exporté le … », ligne « Période : … » ; fichier `sorties-{statut}-{AAAA-MM-JJ}.xlsx`. | `PRO:610-644` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PR22 | export : statut ∉ {valide, brouillon, annule} | 422 | `"Statut : valide, brouillon ou annule."` | `PRO:618-619` |

### B.2.11 Plan de production (`PPL`)

Le plan d'une qualité = une **base mensuelle** (m²) et **douze coefficients** de saisonnalité ;
le plan glissant n'est pas stocké : base × coefficient du mois × croissance annuelle
(`PPL:1-17`).

| # | Règle | Référence |
|---|---|---|
| P90 | `GET /production/plan?date_reference=` (tous) : date de référence = aujourd'hui sauf date explicite (année 2000–2100) ; par qualité (tri par code) : `id, code, nom, actif, base_mensuelle, saisonnalite[12]` (1,0 par défaut), `total_annuel = Σ base × coef`, `glissant` (12 mois à venir, `moteur.plan_mensuel`), `total_glissant`, `kg_m2` (Σ des kg/m² de la recette × (1 + perte)), `lignes_recette`, `recette_conforme`, `tisse_mois_en_cours` (dernier des 12 mois écoulés du réalisé = M0) ; plus `mois` (fins de mois), `croissance_annuelle`, `taux_perte`, `tisse_hors_plan` (qualités tissées ce mois sans être au plan, m² > 0). | `PPL:87-143` |
| P91 | `PUT /production/plan` (**direction**) : `lignes` (1–1 000) `{qualite_id, base_mensuelle ∈ [0 ; 1e9], saisonnalite: 12 nombres exactement}` ; **tout passe ou rien** : doublon, qualité inconnue ou coefficient hors [0 ; 20] refusent l'ensemble avant toute écriture. Une qualité arrêtée peut être planifiée. | `PPL:146-183`, `PPL:38` |
| P92 | Écriture : `base_mensuelle` remplacée ; coefficient de chaque mois mis à jour ou créé. **Chaque chemin qui change le plan** (base, saisonnalité, arrêt, remise en service — y compris la fiche qualité de la partie A) appelle `noter_plan` : si le plan `{b, c, a}` d'après diffère de celui d'avant, journal « plan de production », objet `qualite`, détail `f"{code} : {base:g} m²/mois\nplan={json {'avant':…, 'apres':…}}"` — c'est ce qui permet de juger un mois clos sur le plan **en vigueur pendant ce mois** (commit `db25831`, recette direction 8). Réponse `{"ok": true, "modifiees": n}` (qualités réellement changées). | `PPL:42-74`, `PPL:177-183` |
| P93 | `GET /production/realise` (tous) : plan face au réalisé, **douze mois écoulés**, chaque mois clos jugé sur le plan en vigueur pendant ce mois (`moteur.realise_par_qualite`), `plan_fige: true`. (Remplace la route du même chemin de `pilotage.py`, enregistrée après et donc masquée.) | `PPL:186-198`, `T:test_stock_atelier.py:353` |
| P94 | `GET /production/besoins` (tous) : MRP par référence et par mois — **à une date passée, le stock, les commandes et les sorties de ce jour-là** (`charger_au`) ; `kg` = besoin tiré du plan par les recettes, perte comprise (le même que `/besoins`) ; `retenu` = celui du plan d'achat (corrigé par le coefficient de réalisation quand l'atelier a déjà consommé) ; par ligne : `reference, nature, designation, fournisseur, role, kg_par_ml, kg[12], total, retenu, total_retenu, coefficient_realisation, conso_reelle, stock_disponible, bc_en_cours, stock_projete, couverture_jours, statut, quantite_a_commander, unite_achat, quantite_a_commander_achat, qualites[{qualite, kg_m2, kg[12], total}]` (triées par total ↓) ; plus `mois`, `taux_perte`, `fenetre_realisation_jours`, `roles` (rôles de nomenclature dans leur ordre). Pas de prix. | `PPL:204-286` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| PP1 | `date_reference` hors années 2000–2100 | 400 | `f"date de référence hors période : {reference.isoformat()}"` | `PPL:77-81` |
| PP2 | même `qualite_id` deux fois | 422 | `"Une qualité apparaît deux fois dans le plan envoyé."` | `PPL:164-165` |
| PP3 | qualité inconnue | 404 | `"Qualité introuvable : le plan n'a pas été enregistré."` | `PPL:169-170` |
| PP4 | un coefficient `< 0` ou `> 20` | 422 | `f"{q.code} : un coefficient de saisonnalité reste entre 0 et {COEFFICIENT_MAXI}. Rien n'a été enregistré."` (COEFFICIENT_MAXI = 20) | `PPL:171-175` |
| PP5 | schéma : pas exactement 12 coefficients, base hors bornes, 0 ou > 1 000 lignes | 422 | message traduit (C2) | `PPL:146-153` |

---

## B.3 Atelier (rôle « alimentation des machines », téléphone, sans prix)

Décision de Mohamed (3 octobre 2026, cahier § 2.1) : trois rôles ; l'**alimentation** est
« l'homme de l'atelier, au téléphone : sorties vers les machines, retours, déplacements,
consultation des lots ». Écran d'accueil : quatre grands boutons (Envoyer aux machines, Retour
des machines, Trouver un lot — recherche ou QR —, Déplacer), plus « Signaler un besoin » et
« Monter les fils » (cahier § 3, final-E seconde vague).

### B.3.1 Ce que l'alimentation peut faire (serveur)

| # | Geste | Route(s) | Garde | Référence |
|---|---|---|---|---|
| A1 | Ordres : proposition, créer, modifier, supprimer, valider, annuler | `POST /bons/proposition`, `POST/PUT/DELETE /bons…`, `…/valider`, `…/annuler` | `acteur` (proposition) ; `ALIMENTATION` | `PRO:190`, `PRO:436-580` |
| A2 | Retours des machines (opération `retour_machine`) | `POST/PUT/DELETE /operations…`, `…/valider`, `…/annuler` | `STOCK` + `QUI` | `OPE:29-35` |
| A3 | Transferts (« Déplacer »), dont **mise** en quarantaine — **pas** la libération (403 à la création et à la validation) | idem | `STOCK` + `QUI` + OR24/OR33 | `OPE:310-318`, `OPE:403-408` |
| A4 | « Tout valider » ses ordres et ses opérations permises | `POST /brouillons/valider` | `STOCK` + `_peut` | `BRO:30-35` |
| A5 | Signaler un besoin | `POST /signalements` | `acteur` | `SUI:198-207` |
| A6 | Monter les fils sur un métier (tout le montage, ou un étage) | `PUT /metiers/{id}/fils`, `PUT /metiers/{id}/etages/{n}` | `ALIMENTATION` (+ direction) ; verrou de ligne sur le métier, empreinte facultative ; journal « montage » objet `metier` (détail : fils montés et effet « sur les métiers {avant} → {après} kg ») | `REF:1397-1443`, partie A |
| A7 | Changer son code ; se déconnecter | `POST /moi/code`, `POST /deconnexion` | `acteur` / aucune | `CPT:124-152` |

Interdits (403) : inventaires (ouvrir, compter, valider, abandonner), ouverture de stock,
ajustement, retour fournisseur, libération de quarantaine, commandes, réceptions (même en
lecture), importations, réclamations, pièces jointes, échéancier, bilan, historique des
indicateurs, import tableur, contrôle des soldes, cockpit, plan d'achat, valorisation,
opportunités, contrôles, prix, performance fournisseurs, journal d'audit, comptes, paramètres
(écriture), devises (écriture), sauvegardes (`T:test_parcours.py:68-86`, `392-401`,
`T:test_suivi.py:22`, `30`).

Lectures permises (`acteur`) : mouvements, soldes, lots, scan, étiquettes, QR d'accès, opérations,
motifs, inventaires (liste, détail, défauts, tournant, **feuille** — y compris avec le théorique),
ordres, lots sortis, export des sorties, plan, réalisé, besoins détaillés, brouillons,
signalements (tous, pas seulement les siens), versions de recettes, paramètres, devises et leur
historique, `/stock`, `/besoins`, `/nomenclature`, `/lots`, `/lots/disponibles`, `/tracabilite`,
`/ordres-fabrication`, `/export/mouvements`, `/articles`, `/qualites`, `/metiers`, `/magasins`,
`/fournisseurs`, `/classification`, `/postes-frais`, `/montage/references` (relevé des routes
par import du code, sans serveur).

### B.3.2 Prix masqués : comment, où, quels champs

Principe (`APS:35-38`, `REF:539-541`) : « l'alimentation ne voit ni prix ni montant : le
serveur les retire de ce qu'il lui renvoie (le menu les cache, le serveur ne les donne pas) ».
Le test est `role == "alimentation"` (la direction et les achats voient tout). Le filtrage est
**route par route, par liste de clés explicite**, à un ou deux niveaux de profondeur — **pas** un
filtre générique récursif (le plan PRO le demande « à toute profondeur », voir B.9).

| # | Route | Champs neutralisés | Profondeur | Référence |
|---|---|---|---|---|
| M1 | `GET /mouvements` (et donc `GET /export/mouvements`) | `prix`, `cours`, `cout_mad`, `valeur_mad` → `null` ; `devise` → `""` | chaque ligne | `APS:41-47`, `APS:147-148` |
| M2 | `GET /export/mouvements` | colonnes « Prix / kg » et « Devise » **retirées** du classeur | feuille | `EXP:256-293` |
| M3 | `GET /lots/{id}` | les mêmes clés sur chaque `mouvements[]` | 1 niveau | `APS:302-304` |
| M4 | `GET /operations`, `GET /operations/{id}` | `lignes[].prix` → `null`, `lignes[].devise` → `""` | 1 niveau | `OPE:201-206` |
| M5 | `GET /inventaires`, `GET /inventaires/{id}` | `ecart_valeur_mad`, `ecart_valeur_absolue_mad` ; `lignes[].cmup_mad`, `lignes[].valeur_ecart_mad` → `null` | 0-1 niveau | `INV:123-127` |
| M6 | `GET /stock` | `prix_kg, prix_unite, montant_a_commander, montant_a_commander_mad, valeur_conso_annuelle, valeur_conso_annuelle_mad, valeur_machine_mad` → `null` ; `devise`, `action` → `""` | chaque ligne | `PIL:40-41`, `PIL:58-62` |
| M7 | `GET /nomenclature` | `prix`, `prix_kg`, `cout_m2_mad` → `null`, `devise` → `""` (dernière fuite fermée, commit `96db9ea`) | chaque ligne | `PIL:115-117` |
| M8 | `GET /articles` | `prix`, `prix_kg` → `null` | chaque ligne | `REF:544-561` |
| M9 | `GET /qualites` | `cout_m2_mad` ; `recette[].prix_kg, prix, unite_prix, cout_m2_mad` → `null` (commit `ac615a6`, « trouvé en passant toutes les routes avec son compte ») | 1 niveau | `REF:819-822` |
| M10 | `GET /metiers` | `fils[].valeur_mad`, `valeur_mad` du métier → `null` (le CMUP n'est même pas calculé) | 1 niveau | `REF:1220-1244` |
| M11 | Routes de prix, montants, budgets | interdites (`ACHATS`) : cockpit, plan d'achat, valorisation, opportunités, contrôles, prix, performances, échéancier, bilan, historique des indicateurs, analyse du coût de revient, exports d'analyse | — | `T:test_parcours.py:392-401` |

Non masqué alors que lisible par l'alimentation : voir B.9 (réponses des routes d'écriture
d'opérations, paramètres en MAD, cours des devises).

Essai : `T:test_stock_atelier.py:287-305` (« l'alimentation ne voit aucun prix ») ; audit
« chaque route lue avec le compte de l'alimentation » (`CONFORMITE.md` § 7).

### B.3.3 QR, étiquettes, scan de lot

| # | Règle | Référence |
|---|---|---|
| A10 | Le QR d'une étiquette contient une **adresse** `{base}/lot/{id}` : la caméra du téléphone ouvre la fiche du lot, rien à installer (cahier § 2.2). | `APS:376` |
| A11 | Adresse de base : le réglage `adresse_publique` s'il est rempli (sans « / » final ; ex. `http://mac-usine:8030`, nom Tailscale qui marche en Wi-Fi comme en 4G/5G) ; sinon l'adresse par laquelle on appelle le serveur, **sauf** `localhost`, `127.0.0.1`, `::1`, `*.localhost` (que le téléphone ne joindrait pas), remplacée par `{schéma}://{IP réseau}:{port ou 80}`. | `APS:332-342`, `PAR:143-146` |
| A12 | IP réseau : adresse locale d'un socket UDP « connecté » à `10.255.255.255:1` (aucun paquet envoyé) ; à défaut `127.0.0.1`. | `APS:322-329` |
| A13 | `GET /acces` : `adresse_reseau` (`http://{IP}:{port}`), `nom_machine` (`http://{nom court en minuscules}:{port}`), `adresse_qr`. `GET /acces/qr` : SVG inline (correction d'erreur « m », échelle 6, marge 2) de l'adresse d'accès. | `APS:345-358` |
| A14 | `GET /lots/etiquettes?ids=1,2,3` (≤ 4 000 car.) : une étiquette **100 × 70 mm** par lot (page `@page size 100mm 70mm; margin 4mm`), QR (échelle 4, marge 0, 34 mm), référence, « Lot {numéro} », fournisseur (lot sinon matière), « Entré le JJ/MM/AAAA », quantité **à l'impression** (kg, et ≈ ml pour une matière au mètre), « N° {id} », et le bandeau **« QUARANTAINE — NE PAS SORTIR »** si le lot a du stock en quarantaine (> POUSSIERE) (recette achats G19). Identifiants non numériques ou inconnus ignorés ; texte échappé HTML ; bouton « Imprimer ». | `APS:361-415` |
| A15 | `GET /lots/scan?code=` (1–300 car.) : si le texte contient `/lot/{n}` → le lot d'id n ; sinon les lots dont le numéro est **égal** (sans casse, espaces retirés) — plusieurs possibles (deux matières). Renvoie `[{lot_id, lot, reference, quantite (tous magasins, quarantaine comprise)}]`. | `APS:308-319`, `T:test_parcours.py:359-364` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| AR1 | aucun lot étiquetable | 404 | `"Aucun lot à étiqueter."` | `APS:397-398` |

### B.3.4 Signalements (vus depuis l'atelier)

Voir B.4.2 : tout compte connecté signale (l'atelier d'abord) ; les achats traitent ; la réponse
revient sur le téléphone (liste « mes signalements », relue toutes les minutes à l'écran).

### B.3.5 Codes à 4 chiffres et session longue

| # | Règle | Référence |
|---|---|---|
| A20 | Longueur minimale du code : **4 caractères pour l'alimentation** (« un code court suffit au téléphone de l'atelier »), **8 pour les autres** (« pas à qui achète et valide »). Le serveur ne vérifie **pas** que ce sont des chiffres (l'écran propose un pavé à 4 chiffres qui se connecte sans « Entrer », commit `c2c9108`). | `SEC:50-52` |
| A21 | Session de 30 jours par défaut (`GESTION_MP_SESSION_JOURS`) : le téléphone reste connecté. | `CFG:35`, `SEC:62-80` |

---

## B.4 Suivi (`SUI`)

Ce que promettait le cahier (§ 5.4, 5.5, 5.9, 5.10, 2.6, 2.8) — commit `3e12a08` (étape de
schéma 5). L'import des matières par tableur (`SUI:679-835`) est traité par la **partie A**.

### B.4.1 Réclamations aux fournisseurs (achats + direction)

Modèle `reclamation` : `numero` (unique, obligatoire), `fournisseur_id`, `reception_id`?,
`lot_id`?, `motif` (80), `description`, `quantite` (kg en cause), `montant_demande`, `devise`,
`reponse`, `issue` (40), `montant_obtenu`, `statut` ∈ {ouverte, close}, `ouverte_le`,
`close_le`, `cree_par` (`MOD:967-990`).

| # | Règle | Référence |
|---|---|---|
| U1 | Motifs proposés : « Qualité (défaut du fil) », « Quantité manquante », « Poids des bobines », « Bobines endommagées », « Retard de livraison », « Documents (facture, BL, certificat) », « Autre » — **non contrôlés** à l'ouverture (texte libre ≤ 80). Issues (contrôlées) : « Avoir », « Remplacement », « Remise sur la prochaine commande », « Refusée », « Abandonnée ». | `SUI:44-47` |
| U2 | `GET /reclamations` : `motifs`, `issues`, `reclamations` (id ↓), chacune `{id, numero, fournisseur_id, fournisseur, reception_id, reception (n°), lot_id, lot, reference, motif, description, quantite, montant_demande, devise, reponse, issue, montant_obtenu, statut, ouverte_le, close_le, cree_par, jours}` avec `jours = (close_le ou aujourd'hui) − ouverte_le`. | `SUI:50-70` |
| U3 | **Ouvrir** (`POST /reclamations`, 201) — on réclame à un fournisseur **ce qu'il a livré** : fournisseur connu ; réception (si donnée) connue, **de ce fournisseur**, **validée** ; lot (si donné) connu, livré par ce fournisseur (fournisseurs des réceptions portant ce lot, tous statuts, ∪ fournisseur du lot — si cet ensemble est vide, pas de contrôle) et, si une réception est donnée, présent dans ses lignes ; quantité réclamée ≤ ce que la réception (ou ce lot dans la réception) a livré (Σ des pesées, lignes refusées comprises) + 1e-6 ; devise (majuscules, « MAD » par défaut) présente dans la table ; date d'ouverture (aujourd'hui par défaut) ni future ni antérieure à la réception. | `SUI:85-129` |
| U4 | Numéro `RCL-AAAA-NNNN` attribué **à l'ouverture** (année de `ouverte_le`) ; `cree_par` ; journal « réclamation ouverte », détail `f"{numero} · {motif}"`. | `SUI:130-136` |
| U5 | **Répondre / clore / rouvrir** (`PUT /reclamations/{id}`) : `reponse` (≤ 4 000), `issue` (∈ ISSUES ou vide), `montant_obtenu` (≥ 0) sont **toujours remplacés** par ce qui est envoyé. Une réclamation **close garde son issue** : la modifier sans `rouvrir` et sans issue est refusé ; avec une issue, on peut changer réponse/issue/montant d'une réclamation close sans la rouvrir. `clore` (sur une ouverte) exige une issue → statut `close`, `close_le = aujourd'hui`. `rouvrir` (sur une close) → statut `ouverte`, `close_le = null` ; une réponse complétée **ne rouvre pas** (commit `bcb14b5`). Journal « réclamation », détail `f"{numero} · {statut} · {issue}"`. | `SUI:139-169` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| UR1 | fournisseur inconnu | 422 | `"Fournisseur inconnu."` | `SUI:88-90` |
| UR2 | réception inconnue | 422 | `"Réception inconnue."` | `SUI:93-95` |
| UR3 | réception d'un autre fournisseur | 422 | `f"La réception {rec.numero or rec.id} est de {rec.fournisseur.nom}, pas de {f.nom}."` | `SUI:96-97` |
| UR4 | réception non validée | 422 | `"On réclame sur ce que le fournisseur a livré : cette réception " + ("n'est pas encore validée." si brouillon sinon "est annulée.")` | `SUI:98-100` |
| UR5 | lot inconnu | 422 | `"Lot inconnu."` | `SUI:103-104` |
| UR6 | lot non livré par ce fournisseur | 422 | `f"Le lot {lot.numero} n'a pas été livré par {f.nom}."` | `SUI:110-111` |
| UR7 | lot absent de la réception donnée | 422 | `f"Le lot {lot.numero} n'est pas dans la réception {rec.numero or rec.id}."` | `SUI:112-113` |
| UR8 | `quantite > livré + 1e-6` (réception donnée) | 422 | `f"{e.quantite:,.1f} réclamés pour {livre:,.1f} livrés par la réception {rec.numero}.".replace(",", " ")` (ex. « 1 200.0 réclamés pour 800.0 livrés … » — point décimal, voir B.9) | `SUI:115-120` |
| UR9 | devise absente de la table | 422 | `f"Devise inconnue : {devise}."` | `SUI:121-123` |
| UR10 | `ouverte_le > aujourd'hui` | 422 | `"Une réclamation ne s'ouvre pas dans le futur."` | `SUI:124-126` |
| UR11 | `ouverte_le < date de la réception` | 422 | `f"Une réclamation ne précède pas la réception qu'elle vise ({rec.date:%d/%m/%Y})."` | `SUI:127-129` |
| UR12 | réclamation inconnue | 404 | `"Réclamation introuvable."` | `SUI:151-153` |
| UR13 | issue ∉ ISSUES (non vide) | 422 | `f"Issue : {', '.join(ISSUES)}."` | `SUI:154-155` |
| UR14 | close, sans `rouvrir`, sans issue | 422 | `"Cette réclamation est close : elle garde son issue. La rouvrir pour la reprendre."` | `SUI:157-159` |
| UR15 | `clore` sur une ouverte sans issue | 422 | `"Pour clore, dire comment elle s'est terminée (avoir, remplacement, refusée…)."` | `SUI:161-163` |
| UR16 | schéma : motif > 80, description > 4 000, quantité hors 0–1e9, montant hors 0–1e10, devise > 3, issue > 40 | 422 | message traduit (C2) | `SUI:73-82`, `SUI:139-145` |

### B.4.2 Besoins signalés par l'atelier

Modèle `signalement` : `quand`, `par`, `article_id`?, `texte` (500), `urgence` (« normale » /
« urgente »), `traite_par`, `traite_le`, `reponse` (500) — `MOD:993-1006`.

| # | Règle | Référence |
|---|---|---|
| U10 | **Signaler** (`POST /signalements`, 201, **tout compte**) : `texte` 2–500 car., `urgence` = « normale » (défaut) ou « urgente » (motif `^(normale|urgente)$`), matière facultative ; `par` = nom ; journal « besoin signalé », objet `signalement`, détail = texte[:120]. | `SUI:175-207` |
| U11 | `GET /signalements` (tous) : les **non traités** par défaut ; `tous=true` : tous ; id ↓, 300 au plus ; `{id, quand, par, article_id, reference, texte, urgence, traite, traite_par, traite_le, reponse}`. | `SUI:181-195` |
| U12 | **Traiter** (`POST /signalements/{id}/traiter`, **achats** + direction) : réponse ≤ 500 ; `traite_par`, `traite_le = maintenant()`, `reponse` (un signalement déjà traité peut l'être de nouveau : écrasé) ; journal « besoin traité », détail = réponse[:120]. Le besoin disparaît de la liste par défaut. | `SUI:210-223`, `T:test_suivi.py:25-31` |
| U13 | Les signalements non traités sont comptés au courriel du lundi et au Cockpit (« Besoins signalés par l'atelier »). | `COU:49`, final-D recette 29 |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| UR20 | signalement inconnu | 404 | `"Signalement introuvable."` | `SUI:217-219` |
| UR21 | texte < 2 ou > 500 ; urgence autre ; réponse > 500 | 422 | message traduit (C2) | `SUI:175-178`, `SUI:210-211` |

### B.4.3 Pièces jointes (achats + direction)

Modèle `piece_jointe` : `objet` (20), `objet_id`, `nom` (200), `type_mime` (100), `taille`,
`chemin` (300), `par`, `quand` (`MOD:1009-1022`). Cahier § 6 règle 9 : « une pièce jointe ne
s'exécute jamais dans le navigateur ».

| # | Règle | Référence |
|---|---|---|
| U20 | Objets admis : `dossier`, `reception`, `commande`, `reclamation`, `inventaire`, `fournisseur`, `article` ; l'objet doit exister. | `SUI:228-230`, `SUI:251-252` |
| U21 | Type MIME = celui déclaré par le navigateur, sinon deviné du nom du fichier ; admis s'il correspond **exactement** à : `application/pdf`, `image/(jpeg|png|gif|webp|heic|heif|tiff|bmp)`, `text/plain`, `text/csv`, `application/vnd.<n'importe quoi>`, `application/msword`, `application/zip`. **SVG refusé** (une image SVG peut porter du script : seules les images « à points » entrent — commit `d8882d4`). | `SUI:231-233`, `SUI:253-255` |
| U22 | Taille ≤ **20 Mio** (20 × 1024 × 1024 octets), mesurée après lecture complète. | `SUI:234`, `SUI:256-258` |
| U23 | Stockage **hors base** : `{GESTION_MP_PIECES}/{objet}/{id}/{uuid4 hex}{extension}` (dossier créé au besoin) ; extension = suffixe du nom limité à 9 caractères, ne gardant que lettres, chiffres et « . » ; défaut du dossier racine `~/gestion-mp-pieces/` (+ sous-dossier au nom de la base si ce n'est pas `gestion_mp`). Le nom d'origine est gardé (200 car., « document » à défaut). | `SUI:259-265`, `CFG:42-45` |
| U24 | Journal « pièce jointe », objet = l'objet, `objet_id`, détail = nom du fichier. | `SUI:268` |
| U25 | `GET /pieces/{objet}/{id}` : liste (id ↑) `{id, objet, objet_id, nom, type, taille, par, quand}`. `GET /piece/{id}/fichier` : le fichier, en **téléchargement** (`Content-Disposition: attachment`, type enregistré) — avec `X-Content-Type-Options: nosniff` (B.5.9) il ne s'exécute pas. | `SUI:237-245`, `SUI:273-278` |
| U26 | **Retirer** (`DELETE /piece/{id}`) : la ligne est supprimée, **le fichier reste sur le disque** (« une pièce retirée par erreur se retrouve ») ; journal « pièce retirée ». Les pièces sont recopiées à chaque sauvegarde dans un miroir qui ne perd rien (B.6.1). | `SUI:281-290`, `SAU:82-88` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| UR30 | objet non admis ou inexistant | 404 | `"Document inconnu."` | `SUI:251-252` |
| UR31 | type refusé | 422 | `"Type de fichier refusé : PDF, image, tableur, texte ou document seulement."` | `SUI:254-255`, `T:test_suivi.py:42-45` |
| UR32 | > 20 Mio | 422 | `"Fichier trop lourd (20 Mo au plus)."` | `SUI:257-258` |
| UR33 | pièce inconnue (fichier, retrait) | 404 | `"Pièce introuvable."` | `SUI:276-277`, `SUI:284-285` |

### B.4.4 Échéancier et paiements (achats + direction)

| # | Règle | Référence |
|---|---|---|
| U30 | Ce qu'il faudra payer, et quand : **factures fournisseurs** et **frais d'importation** (`dossier_charge`). | `SUI:320-329` |
| U31 | Montant d'une facture = son montant saisi, sinon ce que ses réceptions **validées** ont apporté (Σ pesée × prix des lignes non refusées) — marqué `estime` (pas de montant saisi et montant > 0). | `SUI:296-340` |
| U32 | Une facture dont **toutes** les réceptions sont **annulées** n'est plus due : listée à part (`ecartees`) — réglée : raison « réglée, réception annulée : avoir à demander » ; non réglée et montant > 0 : « réception annulée : plus due ». Une facture qui ne porte **que des brouillons** de réception n'est **pas encore due** : absente. Une facture sans aucune réception : traitée normalement. | `SUI:313-357` |
| U33 | Une facture **réglée** (`payee_le`) sort de l'échéancier (liste `reglees`, payée la plus récente d'abord, 300 au plus) ; non réglée avec échéance → `lignes` ; sans échéance et montant > 0 → `a_dater` (« pour ne pas l'oublier »). Les frais suivent la même règle (montant en MAD), **même d'un dossier clos** (« clore fige le coût, pas le paiement du transitaire »). | `SUI:347-374` |
| U34 | Montant en MAD = montant × cours **actuel** de la devise (1 si inconnue ou MAD). | `SUI:330-334` |
| U35 | Filtres `du`/`au` : seulement sur `lignes` (par date d'échéance). `lignes` triées par échéance ; `par_mois` (« AAAA-MM » → MAD) ; `echu_mad` = Σ des lignes échues (date < aujourd'hui) ; chaque ligne `en_retard` ; `a_dater_mad` ; `total_mad`. Champs : `id, objet (facture|frais), genre (« Facture fournisseur » / f"Frais d'importation ({poste})"), tiers (fournisseur, ou prestataire, ou « — »), piece (n° de facture, ou « {dossier} · {pièce} »), montant, estime, devise, montant_mad, date`. | `SUI:336-392` |
| U36 | **Régler** (`PUT /echeancier/paiement`, `{objet: facture|frais, id, payee_le}`) : `payee_le` vide = règlement **annulé** (la pièce redevient due) ; un règlement n'est ni futur (« c'est un fait constaté ») ni antérieur à la pièce (date de la facture, à défaut la première réception qui la porte ; pour un frais, la date de sa pièce) ; journal « règlement » / « règlement annulé », objet `facture`/`frais`, détail `f"facture {numero} · {fournisseur}"` ou `f"frais {poste} · dossier {numero}"` + `f" · réglé le {date:%d/%m/%Y}"`. Pas de contrôle de période close. | `SUI:395-435` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| UR40 | pièce inconnue | 404 | `"Pièce introuvable."` | `SUI:416-418` |
| UR41 | `payee_le > aujourd'hui` | 422 | `"Un règlement ne se date pas dans le futur : c'est un fait constaté."` | `SUI:419-420` |
| UR42 | `payee_le < début de la pièce` | 422 | `f"Le règlement ({e.payee_le:%d/%m/%Y}) précède la pièce qu'il règle ({debut:%d/%m/%Y})."` | `SUI:423-426` |
| UR43 | `objet` ∉ {facture, frais} | 422 | message traduit (C2) | `SUI:398` |

### B.4.5 Versions des recettes (lecture et prise automatique)

| # | Règle | Référence |
|---|---|---|
| U40 | **Toute recette enregistrée garde sa version**, datée et signée, sans que les routes s'en occupent : un écouteur global `before_flush` (sur **toutes** les sessions) note les qualités touchées — lignes de recette (`Recette`) ou poids au m² (`QualitePoids`) créés, modifiés ou supprimés, ou collection `poids` d'une qualité existante modifiée — et l'auteur (nom de la dernière ligne de journal ajoutée dans la transaction) ; un écouteur `before_commit` photographie, juste avant de valider, la recette de chaque qualité touchée encore existante : `contenu` = JSON `[{reference, role, pourcentage}]` trié par rôle, `poids` = JSON `{rôle: poids}`, `par` = auteur (vide sinon). | `SUI:441-476` |
| U41 | Changer un **poids au m²** crée une version comme changer un pourcentage (il change autant ce que la recette demande — commit `db25831`). Une version est prise même si le contenu n'a pas changé (dès qu'une ligne est « touchée »). | `MOD:1025-1038`, `SUI:446-451` |
| U42 | `GET /qualites/{id}/versions` (tous) : id ↓, `{id, quand (minutes), par, lignes, poids (null pour une version d'avant qu'on les garde)}`. « Revenir à cette version » (direction, motif obligatoire) est une route de la partie A (`/qualites/{id}/versions/{v}/restaurer`). | `SUI:479-484`, `T:test_audit2_atelier.py:183-203` |
| U43 | Les versions servent à juger le passé (coefficient de réalisation, prévu des ordres) sur la recette **de son époque**. | `DEP:314-325`, commit `db25831` |

### B.4.6 Historique des indicateurs (photo quotidienne)

| # | Règle | Référence |
|---|---|---|
| U50 | Une photo **par jour** (`indicateur_jour`, clé = date ; « la dernière l'emporte ») : `valeur_stock_mad`, `couverture_jours` (couverture pondérée), `ruptures`, `critiques`, `urgents`, `a_commander_mad` (budget à commander), `commandes_en_cours_mad`, `otif_moyen`. Calcul : `moteur.etat_stock` + `moteur.cockpit` à la date. | `SUI:490-513`, `MOD:1041-1047` |
| U51 | **OTIF moyen** : une seule définition, celle d'Analyse › Fournisseurs et du bilan — la part des réceptions **notées** qui sont parfaites (une réception, une voix), pas la moyenne des fournisseurs (commit `96db9ea`) ; `null` sans réception notée. | `SUI:496-499` |
| U52 | Prise **automatique** par la tâche de fond si la photo du jour manque (B.6.3) ; prise **à la main** par la direction (`POST /indicateurs/photographier`, réécrit celle du jour). Pas de journal d'audit. | `SUI:841-847`, `SUI:861-863` |
| U53 | `GET /indicateurs/historique` (achats + direction) : toutes les photos, jour ↑, `{jour, …contenu}`. L'année reprise n'a pas de photo (pas de reconstitution, recette direction 12). | `SUI:516-519` |

### B.4.7 Bilan du mois (achats + direction)

`GET /bilan?mois=AAAA-MM` → page HTML imprimable — `SUI:528-674`.

| # | Règle | Référence |
|---|---|---|
| U60 | Bornes : du 1er du mois (inclus) au 1er du mois suivant (exclu). Tout en **kilos** (cuir, franges, ruban compris). | `SUI:529-537` |
| U61 | Stock au début = Σ des quantités datées avant le 1er ; à la fin = Σ datées avant le 1er du mois suivant (tous types, annulations comprises). | `SUI:545-548` |
| U62 | Flux du mois par type (hors transferts) : réceptions (entrées), sorties, retours des machines, retours fournisseur, ajustements, **ouvertures** (case affichée seulement si non nulle — sans elle le premier mois ne s'équilibrait pas, audit 2-F G2). Les **annulations** (lignes `contrepasse_id`) datées du mois ont leur **ligne à part** (par type) : elles ne comptent ni en sorties ni en entrées (sinon une sortie annulée en octobre ferait des sorties négatives — recette direction 9, commit `f85dabd`). Égalité écrite : fin = début + entrées + ouvertures − sorties + retours machines − retours fournisseur + ajustements + annulations. | `SUI:538-558`, `SUI:604-607`, `SUI:665-670` |
| U63 | Valeur des entrées (MAD) = Σ réceptions × prix × (1 si MAD, sinon **cours figé** du mouvement, à défaut cours actuel) ; une réception **annulée** n'apporte aucun dirham (ses kilos se retirent sur la ligne des annulations — audit 2-G G4). | `SUI:553-558` |
| U64 | m² tissés par qualité : ordres **validés** datés du mois. Commandes émises : bons numérotés dont `date_commande` est dans le mois. Réceptions : validées du mois. OTIF : réceptions notées du mois (U51). | `SUI:559-574` |
| U65 | Ordres du mois lus comme l'écran Sorties (prévu perte comprise, retours déduits) ; les **8 plus grands écarts** relatifs (en valeur absolue). | `SUI:575-583` |
| U66 | « À la fin du mois » : le soir du dernier jour (au plus tard aujourd'hui), journal rejoué (`moteur.a_la_date`) — ruptures et critiques à cette date ; valeur du stock au début (la veille du 1er) et à la fin au **coût moyen** (celles de la Valorisation à ces dates ; le fil monté n'est pas compté à une date passée) ; consommation = coût des sorties du mois (`couts_du_journal(...).consommation`). | `SUI:584-597`, `SUI:665-667` |
| U67 | Page : raison sociale, « Bilan matières premières — MM/AAAA », cases (stock début/fin en kg et MAD, ouvertures, entrées « hors réceptions annulées », sorties « dont x kg revenus · coût net … MAD », tissé, commandes et réceptions, OTIF, ajustements et retours fournisseur), annulations détaillées par type, tableau des m² par qualité (« Aucun ordre ce mois-ci. »), tableau des écarts (« Aucun. »), ruptures et critiques ; nombres à la française, jamais « -0 ». | `SUI:617-674` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| UR50 | `mois` ne respecte pas `^\d{4}-\d{2}$` | 422 | message traduit (C2) | `SUI:618` |
| UR51 | mois `00` ou `13`… (motif respecté, date impossible) | 500 | (aucun message : `ValueError` non gérée, voir B.9) | `SUI:529` |

### B.4.8 Aperçu du courriel (direction)

`GET /courriel/apercu` : `sujet`, `texte` (ce que le courriel du lundi dirait aujourd'hui, B.6.4),
`serveur_configure` (variable `GESTION_MP_SMTP_HOTE` présente), `destinataires` (réglage) —
`SUI:850-858`.

---

## B.5 Comptes, sessions, droits, journal, paramètres, devises, protections

### B.5.1 Rôles et matrice des droits

| # | Règle | Référence |
|---|---|---|
| K1 | Trois rôles (décision de Mohamed du 3 octobre 2026, remplaçant les sept envisagés) : `direction` « Direction », `achats` « Responsable achats », `alimentation` « Responsable alimentation machines » ; CHECK base `role IN ('direction','achats','alimentation')`. | `MOD:42-50`, `MOD:75`, cahier § 2.1 |
| K2 | **Interdit par défaut** : toute route qui écrit déclare ses rôles avec `droit(...)` ; un essai parcourt toutes les routes (sans connexion : 401 partout sauf les routes publiques) ; la **direction passe partout**. | `SEC:1-6`, `SEC:104-114`, `T:test_parcours.py:48-59` |
| K3 | Dépendances : `acteur` (toute personne connectée), `DIRECTION = droit()`, `ACHATS = droit(achats)`, `ALIMENTATION = droit(alimentation)`, `STOCK = droit(achats, alimentation)` ; `LECTURE` et `TOUS` sont définis mais **jamais utilisés**. La fonction de garde porte `.roles` (lu par l'essai). | `SEC:113-122` |
| K4 | Routes **publiques** (sans session) : `GET /etat`, `GET /visages`, `POST /installation`, `POST /connexion`, `POST /deconnexion`, `GET /sante`, et l'écran (fichiers statiques). | `CPT:54-128`, `MAIN:190-214`, `T:test_parcours.py:49-50` |

Matrice effective (code) pour le périmètre B — « L » lire, « É » écrire/valider :

| Domaine | Direction | Achats | Alimentation |
|---|---|---|---|
| Mouvements, soldes, lots, scan, étiquettes, QR d'accès | L | L | L |
| Contrôle soldes = journal (`/controles/soldes`) | L | L | — |
| Ouverture, ajustement, retour fournisseur | É | É | — (lecture de la liste : L) |
| Retour des machines | É | — (lecture : L) | É |
| Transfert | É | É | É (sauf libération de quarantaine) |
| Libération de quarantaine | É | É | — |
| « À valider » (liste) / « Tout valider » | L / É | L / É (opérations permises) | L / É (ordres et opérations permises) |
| Inventaires : lire, défauts, tournant, feuille | L | L | L |
| Inventaires : ouvrir, compter, valider, abandonner | É | É | — |
| Ordres de fabrication (bons), proposition | É | L (proposition : oui) | É |
| Plan de production (écrire) | É | — | — |
| Plan, réalisé, besoins détaillés | L | L | L |
| Réclamations, pièces jointes, échéancier, paiements, bilan, historique des indicateurs, import tableur | É | É | — |
| Signaler un besoin / traiter | É / É | É / É | É / — |
| Versions de recettes (lecture) | L | L | L |
| Photographier les indicateurs, aperçu du courriel | É | — | — |
| Comptes, journal d'audit, historique des paramètres, sauvegardes, restauration, état du serveur | É | — | — |
| Paramètres : lire / écrire | L / É | L / — | L / — |
| Devises : lire / écrire (cours) | L / É | L / É | L / — |
| Son propre code | É | É | É |

### B.5.2 Secrets (codes)

| # | Règle | Référence |
|---|---|---|
| K10 | Empreinte d'un code : **scrypt** (n = 2¹⁴, r = 8, p = 1, 32 octets) avec un sel aléatoire de 16 octets, stockée `"scrypt${sel hex}${empreinte hex}"`. Vérification en temps constant (`hmac.compare_digest`) ; une empreinte illisible = refus. | `SEC:35-47` |
| K11 | Longueur minimale : 4 (alimentation), 8 (autres) — A20. Longueur maximale 200 (schéma). Aucune autre règle de complexité. | `SEC:50-52`, `CPT:80`, `CPT:137-138`, `CPT:163` |

### B.5.3 Installation du premier compte

`POST /installation` (publique, 201) — `CPT:76-99`.

| # | Règle | Référence |
|---|---|---|
| K20 | Ne sert **qu'une fois** : refusée dès qu'un compte existe. | `CPT:86-87` |
| K21 | Champs : `societe` ≤ 160 (facultatif), `identifiant` 2–40, `nom` 2–80, `secret` 8–200. Le compte créé est **direction** ; identifiant normalisé `strip().lower()` ; nom `strip()`. Si `societe` est donnée, elle devient le réglage `nom_entreprise`. | `CPT:76-95` |
| K22 | Journal « installation », objet `utilisateur` ; une **session est ouverte** aussitôt (cookie). Réponse : le compte (`_compte`). | `CPT:96-99` |
| K23 | `GET /etat` (public) : `installe` (au moins un compte existe), `societe` (raison sociale) — « ce que l'écran de connexion a besoin de savoir, et rien de plus » ; un serveur qui ne répond pas ne doit pas faire proposer la création du compte de direction (commit `cafb0ce`, côté écran). Exemple de nom proposé à l'installation : « MAZARI » (exigence M15). | `CPT:54-61` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR1 | un compte existe déjà | 409 | `"Gestion MP est déjà installé : connectez-vous."` | `CPT:86-87` |

### B.5.4 Connexion, verrouillage après tentatives, sessions

| # | Règle | Référence |
|---|---|---|
| K30 | `GET /visages` (public) : les comptes **actifs**, triés par nom, `{identifiant, nom, role, role_libelle}` — pour choisir son nom à la connexion. | `CPT:64-73` |
| K31 | `POST /connexion` `{identifiant ≤ 40, secret ≤ 200}` : identifiant normalisé `strip().lower()`. Si l'identifiant est en **attente** (blocage en cours), refus 429 sans compter d'échec. Sinon, compte inconnu, **inactif** ou code faux → un échec est compté et refus 401 (même message dans les trois cas). Succès → les échecs de cet identifiant sont effacés, session ouverte, journal « connexion » (objet `utilisateur`), réponse = le compte. Un échec n'est **pas** journalisé. | `CPT:102-121` |
| K32 | **Compteur d'échecs** par identifiant (table `tentative` : `identifiant`, `echecs`, `bloque_jusqua`), incrémenté par **un seul ordre SQL** (`INSERT … ON CONFLICT DO UPDATE SET echecs = echecs + 1 RETURNING echecs`) : plusieurs essais au même instant ne se marchent pas dessus (commit `d8882d4`) ; validé (`commit`) **avant** de répondre 401. | `SEC:135-147`, `MOD:98-105`, `T:test_zz_restauration.py:70-92` |
| K33 | **Blocage** : à partir du 5ᵉ échec (`ECHECS_TOLERES = 5`), `bloque_jusqua = maintenant + min(900, 30 × 2^(échecs − 5))` secondes → 30 s (5ᵉ), 60 s, 120 s, 240 s, 480 s, puis 900 s (¼ h) au-delà. Le compteur n'est pas remis à zéro à la fin d'un blocage (seul un succès l'efface) : chaque nouvel échec rallonge. Attente restante = `max(0, int(secondes))`. | `SEC:25`, `SEC:128-147` |
| K34 | **Session** : jeton aléatoire `token_urlsafe(32)` remis en cookie `gestion_mp_session` (`HttpOnly`, `SameSite=Lax`, `Secure` si `GESTION_MP_HTTPS=1`, `Path=/`, `Max-Age` = durée) ; seule son **empreinte SHA-256** est stockée (`session_ouverte`: `empreinte`, `utilisateur_id`, `expire_le`). Durée **fixe** `GESTION_MP_SESSION_JOURS` (défaut 30 j), non prolongée à l'usage. `vu_le` du compte = l'heure de la **connexion** (pas de chaque requête). | `SEC:24`, `SEC:55-80`, `MOD:88-95`, `CFG:18`, `CFG:35` |
| K35 | `acteur` : cookie absent, session inconnue ou **expirée** → 401 ; compte supprimé ou **inactif** → 401. Le rôle est relu en base à chaque requête (un changement de rôle vaut tout de suite). Les sessions expirées ne sont jamais purgées. | `SEC:92-101` |
| K36 | `POST /deconnexion` (publique) : supprime la session du cookie (si elle existe) et efface le cookie ; `{"ok": true}` ; pas de journal. | `SEC:83-89`, `CPT:124-128` |
| K37 | `GET /moi` : le compte connecté `{id, identifiant, nom, role, role_libelle, email, actif, vu_le}`. | `CPT:41-51`, `CPT:131-133` |
| K38 | `POST /moi/code` `{ancien, nouveau}` : l'ancien code doit correspondre ; le nouveau respecte la longueur du rôle ; journal « changement de code ». Les autres sessions de la personne restent ouvertes ; un mauvais « ancien » n'est pas compté comme échec de connexion. | `CPT:136-152` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR10 | identifiant bloqué | 429 | `f"Trop d'essais : patientez {patienter} secondes."` | `CPT:110-112` |
| KR11 | inconnu, inactif ou code faux | 401 | `"Identifiant ou code incorrect."` | `CPT:113-116` |
| KR12 | pas de session valide (toute route gardée) | 401 | `"Connectez-vous pour continuer."` | `SEC:95-97` |
| KR13 | compte inactif ou supprimé | 401 | `"Ce compte n'est plus actif."` | `SEC:98-100` |
| KR14 | rôle insuffisant | 403 | `f"Cette action est réservée à : {permis}."` — `permis` = libellés en minuscules des rôles admis joints par « , » (ex. « responsable achats », « responsable achats, responsable alimentation machines »), « la direction » pour `DIRECTION` | `SEC:107-110` |
| KR15 | `/moi/code` : ancien faux | 403 | `"Le code actuel ne correspond pas."` | `CPT:145-146` |
| KR16 | `/moi/code` : nouveau trop court | 422 | `f"Le nouveau code doit faire au moins {longueur_mini(u.role)} caractères."` | `CPT:147-148` |

### B.5.5 Comptes (direction)

| # | Règle | Référence |
|---|---|---|
| K40 | `GET /utilisateurs` : tous les comptes, triés par nom. | `CPT:167-169` |
| K41 | **Créer** (`POST /utilisateurs`, 201) : `identifiant` 2–40 (normalisé `strip().lower()`, **unique**), `nom` 2–80 (strip), `role` ∈ rôles, `email` ≤ 120 (non vérifié), `secret` (longueur du rôle), `actif` (vrai par défaut). Le code est fixé par la direction (pas de changement imposé à la première connexion). Journal « création de compte », détail `f"{nom} ({libellé du rôle})"`. | `CPT:158-188` |
| K42 | **Modifier** (`PUT /utilisateurs/{id}`) : nom, rôle, email, actif remplacés ; l'**identifiant ne change pas** (champ exigé par le schéma mais ignoré) ; le code n'est changé que si `secret` est non vide (longueur du **nouveau** rôle) ; on ne peut pas se retirer à soi-même la direction ni se désactiver ; **désactiver** supprime toutes les sessions ouvertes du compte. Journal « modification de compte ». Pas de suppression de compte. | `CPT:191-210` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR20 | rôle inconnu (créer, modifier) | 422 | `"Rôle inconnu."` | `CPT:175-176`, `CPT:197-198` |
| KR21 | identifiant déjà pris | 409 | `f"L'identifiant « {identifiant} » est déjà pris."` | `CPT:178-179` |
| KR22 | code trop court (créer ; modifier avec code) | 422 | `f"Le code doit faire au moins {longueur_mini(e.role)} caractères."` | `CPT:180-181`, `CPT:203-204` |
| KR23 | compte inconnu | 404 | `"Compte introuvable."` | `CPT:195-196` |
| KR24 | soi-même : rôle ≠ direction ou inactif | 409 | `"Vous ne pouvez pas retirer vos propres droits de direction."` | `CPT:199-200` |

### B.5.6 Journal d'audit (lecture, direction)

| # | Règle | Référence |
|---|---|---|
| K50 | Écriture : partie A § 0.3 (`journal()`, détail ≤ 2 000, `utilisateur` = **nom** de la personne, « système » sans personne, `role`, `quand`). | `SEC:159-176` |
| K51 | `GET /journal` : filtres exacts `utilisateur`, `action`, `objet` ; `du`/`au` sur la date (`au` inclus jusqu'à minuit) ; `q` : jusqu'à **6 mots**, mis en minuscules, chacun cherché (`ILIKE`, ET entre mots) dans utilisateur, action, objet ou détail — **`%`, `_` et `\` échappés** (chercher « % » ne ramène plus tout — commit `96db9ea`) ; tri id ↓ ; `limite` ramenée dans 1–5 000 (défaut 300). Ligne : `{id, quand (secondes), utilisateur, role, action, objet, objet_id, detail}`. | `CPT:213-259` |
| K52 | `GET /journal/valeurs` : valeurs distinctes non vides d'`utilisateur`, `action`, `objet` (pour les filtres). Export Excel `GET /export/journal` (direction, partie « exports »). | `CPT:262-270`, final-D D9 |
| K53 | Le journal est **relu** par des règles (partie A § 0.3 ; ici : versions du plan `plan=`, auteur d'une version de recette, solde à la main). | `DEP:43-52`, `DEP:156-170`, `SUI:452-453` |

Actions écrites par le périmètre B (texte contractuel) :

| Objet | Actions | Référence |
|---|---|---|
| `operation` | « {type} (brouillon) », « modification opération », « suppression opération », « validation — {type} », « annulation opération » | `OPE:354`, `376`, `390`, `437`, `454`, `PRO:571` |
| `inventaire` | « ouverture inventaire », « comptage », « validation inventaire », « abandon inventaire » | `INV:314`, `376`, `412`, `428` |
| `bon` | « bon de sortie (brouillon) », « modification bon de sortie », « suppression bon de sortie », « validation bon de sortie », « annulation bon de sortie » | `PRO:443`, `463`, `475`, `527`, `577` |
| `qualite` | « plan de production » (détail avec `plan=`) | `PPL:58-59` |
| `reclamation` | « réclamation ouverte », « réclamation » | `SUI:134`, `SUI:167` |
| `signalement` | « besoin signalé », « besoin traité » | `SUI:205`, `SUI:221` |
| objet de la pièce | « pièce jointe », « pièce retirée » | `SUI:268`, `SUI:288` |
| `facture` / `frais` | « règlement », « règlement annulé » | `SUI:432` |
| `article` | « import des matières » (partie A) | `SUI:832` |
| `utilisateur` | « installation », « connexion », « changement de code », « création de compte », « modification de compte » | `CPT:96`, `119`, `150`, `186`, `208` |
| `parametre` | « paramètre » (détail « {libellé} : {avant} → {après} ») | `CPT:329-330` |
| `devise` | « cours de change » (détail « {code} : {taux} MAD ») | `CPT:443-444` |
| `sauvegarde` | « sauvegarde » (détail : nom du fichier), « restauration » (écrite après coup dans la base restaurée, rôle « direction ») | `CPT:500`, `SAU:193-196` |
| `metier` | « montage » | `REF:1415`, `REF:1445` |

Non journalisés : déconnexion, échec de connexion, photo des indicateurs, envoi du courriel
(seul le réglage `courriel_dernier_envoi` change), consultation.

### B.5.7 Paramètres (réglages)

| # | Règle | Référence |
|---|---|---|
| K60 | Liste fermée `REGLAGES` (clé, libellé, famille, défaut, bornes basse/haute, unité, échelle d'affichage — 100 pour un taux saisi en % —, aide) ; **tous écrits en base à l'installation** avec leur défaut (« un réglage qu'on ne voit pas n'existe pas »), jamais écrasés ensuite. | `PAR:1-5`, `PAR:41-148`, `PAR:152-157`, `MAIN:84` |
| K61 | Familles : « Couverture et statuts », « Approvisionnement », « Classification ABC / XYZ », « Politique d'achat », « Réceptions et fournisseurs », « Prix », « Trésorerie », « Société », « Stock et inventaire ». Réglages propres à ce périmètre : `tolerance_inventaire` (2 %, 0–100 %), `taux_perte` (2 %, 0–50 %, « ajouté aux besoins et au coût de la matière »), `croissance_annuelle` (0 %, −90 %…+1 000 % : à −100 % la production s'annule et un mois passé se divise par zéro), `fenetre_realisation_jours` (90 j, 0–730), `date_cloture`, `courriel_destinataires` (« Adresses séparées par des virgules. Vide : pas de courriel »), `adresse_publique` (QR). Le reste (achats, réceptions, prix, ABC/XYZ, société) : partie A et partie « calculs ». | `PAR:31-148` |
| K62 | `GET /parametres` (tous) : chaque réglage `{cle, libelle, famille, unite, echelle, aide, bas, haut, texte (défaut textuel), defaut, valeur (en base, sinon défaut)}`. | `CPT:276-289` |
| K63 | Lecture numérique (`nombre`) : valeur en base convertie, sinon le défaut (valeur vide ou illisible → défaut). Le moteur reçoit les réglages qui correspondent à ses champs, `methode = "corrigee"` forcée, le **cours de chaque devise** de la table, et les taux EUR/USD tirés de la table. | `PAR:164-189` |
| K64 | **Écrire** (`PUT /parametres`, direction ; corps `{clé: valeur}`) : clés inconnues refusées ; nombre : virgule acceptée (`"9,5"`), borné `bas ≤ x ≤ haut` (valeurs en **fraction** pour un taux : 0,02 = 2 %) ; normalisé en texte (`repr` si non entier, entier sinon) ; `date_cloture` : vide (rouvrir) ou date ISO **strictement passée** ; `adresse_publique` : vide ou commence par `http://`/`https://`, ≤ 200, sans espace ; autres textes ≤ 500 car. Valeur inchangée → rien. Sinon : valeur, `modifie_le`, `modifie_par` ; ligne d'**historique** (`parametre_historique` : clé, valeur, par, quand) ; journal « paramètre » détail `f"{libellé} : {avant} → {après}"` en lisible (`_lisible` : « 9,5 », un taux en « 20 % », « — » pour vide ; arrondi à 6 décimales pour éviter « 7.000000000000001 »). | `CPT:292-338`, `CPT:355-366` |
| K65 | **Seuils dans l'ordre**, vérifiés après l'écriture de tout le lot (« des seuils qui se contredisent vident une catégorie sans le dire ») : `seuil_critique < seuil_alerte`, `seuil_abc_a < seuil_abc_b`, `seuil_xyz_x < seuil_xyz_y`, `score_surveiller < score_standard`, `score_standard < score_strategique` ; sinon **annulation de tout** (`rollback`) et refus (recette direction 23, commit `f85dabd`). | `CPT:332-352` |
| K66 | `GET /parametres/historique` (direction) : les 500 derniers changements (id ↓) `{cle, libelle, valeur, avant (valeur précédente de la même clé, sinon le défaut), quand, par}` — y compris les cours de devises (`cours_XXX`). | `CPT:369-387` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR30 | clés inconnues | 422 | `f"Paramètres inconnus : {', '.join(sorted(inconnus))}."` | `CPT:295-297` |
| KR31 | nombre illisible | 422 | `f"« {r.libelle} » attend un nombre."` | `CPT:302-305` |
| KR32 | hors bornes | 422 | `f"« {r.libelle} » doit rester entre {r.bas * r.echelle:g} et {r.haut * r.echelle:g} {r.unite} — reçu {nombre * r.echelle:g}."` | `CPT:306-310` |
| KR33 | `date_cloture >= aujourd'hui` | 422 | `"On ne clôt qu'une période passée."` | `CPT:312-315` |
| KR34 | `date_cloture` illisible | 422 | `"Date de clôture illisible (AAAA-MM-JJ)."` | `CPT:316-317` |
| KR35 | `adresse_publique` invalide | 422 | `"L'adresse commence par http:// ou https:// (ex. http://mac-usine:8030)."` | `CPT:318-320` |
| KR36 | autre texte > 500 | 422 | `f"« {r.libelle} » : texte trop long."` | `CPT:321-322` |
| KR37 | `seuil_critique >= seuil_alerte` | 422 | `"La couverture critique doit rester inférieure à la couverture d'ATTENTION : sinon plus aucune matière ne serait en ATTENTION."` | `CPT:343-345` |
| KR38 | `seuil_abc_a >= seuil_abc_b` | 422 | `"La part cumulée de la classe A doit rester sous celle de la classe B."` | `CPT:346` |
| KR39 | `seuil_xyz_x >= seuil_xyz_y` | 422 | `"Le CV maximum de la classe X doit rester sous celui de la classe Y."` | `CPT:347` |
| KR40 | `score_surveiller >= score_standard` | 422 | `"Le score « ATTENTION » doit rester sous le score « standard »."` | `CPT:348-349` |
| KR41 | `score_standard >= score_strategique` | 422 | `"Le score « standard » doit rester sous le score « stratégique »."` | `CPT:350-351` |

### B.5.8 Devises et cours (historique)

| # | Règle | Référence |
|---|---|---|
| K70 | Table `devise` : `code` (3, clé), `nom` (40), `taux` (vers le dirham, CHECK > 0), `actif`. Créées à l'installation si absentes : MAD « Dirham » 1, USD « Dollar américain » 10, EUR « Euro » 10,8. | `MOD:159-165`, `MAIN:45`, `MAIN:74-77` |
| K71 | `GET /devises` (tous) : `{code, nom, taux, actif, cours_le}` — `cours_le` = date du dernier cours saisi (historique `cours_{CODE}`), `null` si jamais saisi (« cours de la reprise » à l'écran). `GET /devises/{code}/historique` (tous) : les 500 derniers cours `{taux, quand, par}`, le plus récent d'abord (code mis en majuscules, 3 premiers caractères). | `CPT:400-427` |
| K72 | **Écrire un cours** (`PUT /devises`, **achats** + direction) `{code (exactement 3), nom ≤ 40, taux ∈ ]0 ; 10 000], actif}` : code en majuscules ; devise créée si elle n'existe pas ; sinon nom (gardé si vide), taux et actif remplacés ; le **dirham** garde le cours 1 ; **chaque** écriture ajoute une ligne d'historique `cours_{CODE}` (même sans changement) et un journal « cours de change ». Réponse : la liste des devises. | `CPT:393-446` |
| K73 | Effet d'un cours : vaut **pour les écritures à venir** qui n'apportent pas leur cours (stock d'ouverture en devise, S18) et pour les calculs « au cours du jour » (échéancier, estimations) ; les mouvements passés gardent leur cours figé (S8). Pas de cours datés (« conversion des prix passés au cours de leur date » non retenue, `CONFORMITE.md`). | `STK:181-186`, `SUI:330-334` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR50 | MAD et taux ≠ 1 | 422 | `"Le dirham est la devise de référence : son cours reste 1."` | `CPT:439-440` |
| KR51 | schéma (code ≠ 3 caractères, taux ≤ 0 ou > 10 000) | 422 | message traduit (C2) | `CPT:393-397` |

### B.5.9 Protections HTTP communes (`MAIN`)

| # | Règle | Référence |
|---|---|---|
| K80 | **Anti-falsification de requête** : toute requête d'écriture (méthode autre que GET, HEAD, OPTIONS) sur `/api/…` doit porter l'en-tête `X-Gestion-MP: 1` — une page d'un autre site ne peut pas l'ajouter ; exemptées : `/api/connexion`, `/api/installation`, `/api/deconnexion`. Un envoi de fichier (multipart) porte aussi cet en-tête. | `MAIN:136-151`, `5-a-faire-suivi.md` |
| K81 | En-têtes ajoutés à toute réponse (s'ils manquent) : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (pas d'affichage dans un cadre), `Referrer-Policy: same-origin`. Sur `/api/…` : `Cache-Control: no-store` et `X-Heure-Serveur: AAAA-MM-JJTHH:MM:SS` (l'heure du serveur, que l'écran affiche plutôt que celle du poste, qui peut compter un autre fuseau — commits `238729e`, `9724d96`). | `MAIN:152-161` |
| K82 | `GET /api/sante` (publique, surveillance) : `{etat: "ok", schema (dernière étape de schéma), version (contenu du fichier VERSION à la racine, sinon « projet »), sauvegarde_age_h, sauvegarde_alerte}`. | `MAIN:190-200` |
| K83 | Écran : `/assets` en fichiers statiques ; toute autre adresse sert le fichier demandé s'il existe **dans** le dossier de l'écran (protection contre la remontée de chemin) — `sw.js` et `manifest.webmanifest` en `no-cache` —, sinon `index.html` (`no-cache`) ; une adresse `api/…` inconnue → 404 `"Route inconnue"`. Le serveur en service lit une **copie figée** de l'écran et de la version (commit `64cd996`). | `MAIN:203-214`, `CFG:31-34` |
| K84 | Documentation OpenAPI : `/api/docs`, `/api/openapi.json` ; titre « Gestion MP », version « 1.0.0 ». | `MAIN:126-129` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| KR60 | écriture `/api/` sans `X-Gestion-MP: 1` (hors 3 routes) | 403 | `"Requête refusée : elle ne vient pas de l'écran de Gestion MP."` | `MAIN:147-151`, `T:test_parcours.py:62-65` |
| KR61 | `GET /api/…` inconnue (via l'écran) | 404 | `"Route inconnue"` | `MAIN:208-209` |

### B.5.10 État du serveur (direction)

`GET /etat-serveur` — `CPT:505-560` : version de l'application, étape de schéma, Python,
système, nom de la machine, base (nom, hôte — « ce serveur (connexion locale) » sans hôte —,
port 5432 par défaut, version PostgreSQL, taille), adresse réseau, port, HTTPS, tâches de fond
actives, durée de session, sauvegardes (dossier, copie, chemins de `pg_dump` / `pg_restore`,
nombre et dernière **de cette base**, politique « une par jour gardée 14 jours, puis la première
de chaque mois gardée 12 mois ; les manuelles et « avant restauration » ne s'effacent jamais
seules »), sessions ouvertes non expirées par personne (`{nom, role, vu_le, nb, expire_le}`).
Les durées (session, échecs tolérés, dossiers) se règlent par variables d'environnement, pas à
l'écran (`CONFORMITE.md`).

---

## B.6 Exploitation : sauvegardes, restauration, courriel, tâches de fond, numérotation

### B.6.1 Sauvegardes (`SAU`)

| # | Règle | Référence |
|---|---|---|
| X1 | Outils `pg_dump` / `pg_restore` cherchés **par chemin complet** (un service n'a pas le PATH d'un terminal) : si `GESTION_MP_PG_BIN` est réglé, seulement dans ce dossier ; sinon le PATH, puis `/opt/homebrew/bin`, `/opt/homebrew/opt/postgresql@*/bin`, `/usr/local/bin`, `/usr/lib/postgresql/*/bin`, `/usr/pgsql-*/bin`, `/usr/bin`, `/Applications/Postgres.app/Contents/Versions/latest/bin` (versions les plus récentes d'abord). | `SAU:22-40`, `CFG:30` |
| X2 | Dossier : `GESTION_MP_SAUVEGARDES`, défaut `~/gestion-mp-sauvegardes/` — et un **sous-dossier au nom de la base** si ce n'est pas `gestion_mp` (une base d'essai ou de démonstration ne mêle pas ses sauvegardes à celles de la production, commit `7eff5e7`). Copie externe facultative : `GESTION_MP_SAUVEGARDES_COPIE` (« celle qui compte le jour J »). | `CFG:21-29` |
| X3 | Nom : quotidienne `gestion-mp-{AAAA-MM-JJ}.dump` ; autres `gestion-mp-{AAAA-MM-JJ-HHMMSS}-{genre}.dump` (genres : `manuelle`, `avant-restauration`). Format personnalisé `pg_dump -Fc`, délai 30 min. Écrite d'abord dans un fichier provisoire `.{nom}.{pid}.partiel`, **relue** (`pg_restore --list` : code retour 0 et au moins une « TABLE DATA »), puis renommée atomiquement ; le provisoire est toujours effacé. | `SAU:53-81` |
| X4 | **Pièces jointes** recopiées à chaque sauvegarde dans `{sauvegardes}/pieces-jointes` (et dans la copie externe) en complétant, sans rien effacer (une pièce retirée de l'écran reste dans le miroir — commit `eb60466`). Puis le fichier de sauvegarde est copié dans la copie externe. | `SAU:82-92` |
| X5 | **Quotidienne** : si le fichier du jour n'existe pas, sauvegarde « quotidienne » puis **purge**. | `SAU:96-102` |
| X6 | **Purge** (quotidiennes seulement) : on garde les **14** dates les plus récentes et le **premier fichier de chaque mois** pour les **12** mois les plus récents ; les manuelles et « avant-restauration » ne s'effacent jamais seules. | `SAU:105-118` |
| X7 | **État** : liste des `gestion-mp-*.dump` (nom, taille, date de modification), la plus récente d'abord ; âge de la dernière en heures ; alerte (si les tâches tournent) : « Les sauvegardes sont arrêtées : pg_dump est introuvable sur le serveur. » / `f"La sauvegarde automatique a échoué : {ETAT['erreur']}"` / « Aucune sauvegarde récente. » (plus de 26 h, après un premier essai de la boucle). Un échec ne se tait jamais (affiché en rouge à la direction). | `SAU:121-144` |
| X8 | **État de cette base** (écran) : la base de chaque fichier est lue dans son en-tête (`pg_restore --list`, ligne `dbname:`, mémorisée par chemin et date de modification) ; les fichiers d'une **autre base** sont listés et signalés mais ne comptent pas (nombre, dernière, âge) ; alerte `f"Aucune sauvegarde de la base « {courante} » : le dossier ne contient que d'autres bases."` ; 30 fichiers au plus (recette direction 18). | `CPT:452-489` |
| X9 | Routes (direction) : `GET /sauvegardes` (état), `POST /sauvegardes` (« Sauvegarder maintenant » : sauvegarde manuelle, journal « sauvegarde » avec le nom du fichier, renvoie l'état). | `CPT:492-502` |

### B.6.2 Restauration (direction)

`POST /sauvegardes/{nom}/restaurer` — `CPT:563-580`, `SAU:147-196`. Elle écrase la base pour
tous les postes : opération de direction, **réversible** (exigence M04).

| # | Règle | Référence |
|---|---|---|
| X10 | Le nom est réduit à son nom de fichier (pas de chemin) ; le fichier doit exister dans le dossier et commencer par `gestion-mp-`. | `CPT:566`, `SAU:171-173` |
| X11 | Une sauvegarde d'une **autre base** est refusée (409). | `CPT:568-573` |
| X12 | La requête **rend sa connexion** d'abord (`commit`, `close`) : sinon pg_restore attendrait qu'elle lâche ses tables, et elle attendrait pg_restore (commit `d8882d4`, audit : « Restaurer une sauvegarde depuis l'écran se bloquait »). | `CPT:575-578`, `T:test_zz_restauration.py:30-67` |
| X13 | Ordre : relire le fichier (`verifier`) → **sauvegarder l'état actuel** (« avant-restauration ») → fermer le pool de connexions du serveur → **couper toutes les autres connexions** à la base (`pg_terminate_backend`, les postes se reconnectent d'eux-mêmes) → `pg_restore --clean --if-exists --no-owner -d <base>` (30 min) → journal « restauration » (objet `sauvegarde`, détail = nom du fichier, utilisateur = qui a restauré, rôle « direction ») écrit **dans la base restaurée**. | `SAU:163-196` |
| X14 | Échec si `pg_restore` rend un code ≠ 0 **et** que sa sortie d'erreur contient « error » (des avertissements seuls ne font pas échouer). Réponse : l'état des sauvegardes. | `SAU:188-189`, `CPT:580` |

| # | Condition | HTTP | Message exact | Réf. |
|---|---|---|---|---|
| XR1 | fichier absent ou ne commençant pas par `gestion-mp-` | 404 | `"Sauvegarde introuvable."` | `SAU:172-173` |
| XR2 | base du fichier ≠ base courante | 409 | `f"Cette sauvegarde est celle de la base « {base} », pas de « {courante} » : la restaurer remplacerait toutes les données par celles d'une autre base."` | `CPT:570-573` |
| XR3 | `pg_restore` introuvable | 500 | `"pg_restore est introuvable sur le serveur."` | `SAU:177-178` |
| XR4 | `pg_restore` en erreur | 500 | `f"La restauration a échoué : {r.stderr.strip()[:300]}"` | `SAU:188-189` |
| XR5 | fichier illisible (relecture) | 500 | aucun message propre : `RuntimeError(f"Sauvegarde illisible : {stderr[:200] or 'vide'}")` non convertie (voir B.9) | `SAU:53-59` |
| XR6 | `pg_dump` introuvable / en échec (sauvegarde manuelle, avant-restauration) | 500 | `RuntimeError("pg_dump est introuvable : installez les outils de PostgreSQL ou indiquez leur dossier dans GESTION_MP_PG_BIN.")` / `RuntimeError(f"pg_dump a échoué : {stderr[:300]}")` non converties | `SAU:63-77` |

### B.6.3 Tâches de fond

| # | Règle | Référence |
|---|---|---|
| X20 | Au démarrage (`lifespan`) : `initialiser()` — migrations du schéma par étapes numérotées sous verrou consultatif `7426101` ; rôles de nomenclature, postes de frais (un poste ajouté à une base remplie prend sa place après son précédent, les suivants descendent), devises, magasins, réglages — **ce qui existe n'est jamais écrasé**. | `MAIN:50-85`, `DB:376-405` |
| X21 | Si `GESTION_MP_TACHES=1` (défaut) : un **seul processus** porte les tâches — celui qui obtient `pg_try_advisory_lock(7426102)` (verrou de **session**, sa connexion est gardée ouverte). | `MAIN:88-98`, `CFG:19-20` |
| X22 | Boucle (fil d'exécution démon), toutes les **15 minutes** : (1) `taches_du_jour` — photo des indicateurs si celle du jour manque, puis courriel du lundi ; une erreur est écrite sur la sortie d'erreur (`[indicateurs] …`) et n'arrête pas la boucle ; (2) sauvegarde du jour (X5) — un échec est gardé dans `ETAT["erreur"]` (300 car.) et affiché, un succès l'efface ; `ETAT["essai"]` = heure du passage. | `MAIN:100-115`, `SUI:841-847` |

### B.6.4 Courriel du lundi (`COU`)

| # | Règle | Référence |
|---|---|---|
| X30 | Actif dès que **deux** choses sont réglées : le serveur d'envoi dans l'environnement (`GESTION_MP_SMTP_HOTE`, `GESTION_MP_SMTP_PORT` défaut 587, `GESTION_MP_SMTP_UTILISATEUR`, `GESTION_MP_SMTP_MOT_DE_PASSE`, `GESTION_MP_SMTP_EXPEDITEUR`) et les destinataires (réglage `courriel_destinataires`). | `COU:1-9`, `COU:27-28` |
| X31 | Envoyé **un lundi**, **une fois** : rien si ce n'est pas lundi, pas de serveur, pas de destinataire, ou si `courriel_dernier_envoi` vaut déjà la date du jour. Après l'envoi : `courriel_dernier_envoi` = date du jour (paramètre créé au besoin, `modifie_par` « système » — hors liste des réglages). | `COU:73-98` |
| X32 | Envoi : STARTTLS toujours, authentification si un utilisateur est réglé, délai 30 s ; expéditeur = `…EXPEDITEUR` sinon l'utilisateur ; `To` = le réglage tel quel (adresses séparées par des virgules). | `COU:83-93` |
| X33 | Contenu (sujet `f"Gestion MP — la semaine du {jour:%d/%m/%Y}"`) : en-tête (+ « — {raison sociale} »), valeur du stock (MAD) et couverture pondérée (jours), ruptures / critiques / urgentes, « À commander selon le plan » (MAD), commandes en retard (numérotées, statut envoyée, confirmée ou à approuver, **au-delà du retard toléré**, pas un bon dont tout est arrivé — « reçu sous réserve » ; les 8 premiers numéros cités), commandes à approuver, brouillons en attente (réceptions, ordres de fabrication, opérations), besoins signalés non traités, réclamations ouvertes, « Le détail : ouvrir Gestion MP (Cockpit). ». Les mêmes chiffres que l'écran (commit `91448ce`). | `COU:31-70` |

### B.6.5 Numérotation — toutes les séries

Compteur `compteur(serie, annee, dernier)` unique par (série, année) ; `numero()` sous verrou de
ligne (partie A § 0.4). L'**année est celle de la date de la pièce**, pas d'aujourd'hui.

| Série | Format | Document | Moment de l'attribution | Référence |
|---|---|---|---|---|
| `BC` | `BC-2026-0001` | Bon de commande | à l'**envoi** (ou à l'approbation qui envoie) — date d'envoi, qui peut être passée | `ACH:493-515` |
| `REC` | `REC-2026-0001` | Réception | à la **validation** (date de la réception) | `REC:543` |
| `LOT` | `LOT-2026-0001` | Lot interne (« LOT INTERNE » saisi) | à la **validation** de la réception ; le compteur **rattrape** d'abord le plus grand `LOT-AAAA-NNNN` déjà en base (lots repris de l'ERP Fil) ; **aussi** à la demande par `POST /lots/numero-interne` (achats, date du jour — numéro consommé tout de suite) | `REC:45-67`, `REC:541-542`, `REC:665-670` |
| `OF` | `OF-2026-0001` | Ordre de fabrication (bon de sortie) | à la **validation**, sous verrou consultatif ; numéros **dans l'ordre des dates** (PR18) | `PRO:513-520` |
| `OUV`, `RET`, `TRF`, `AJU`, `RFO` | `TRF-2026-0001`… | Opérations de stock | à la **validation** (date de l'opération) | `OPE:25-26`, `OPE:409` |
| `INV` | `INV-2026-0001` | Inventaire | à l'**ouverture** (date de l'inventaire) — un abandon laisse un trou | `INV:304` |
| `RCL` | `RCL-2026-0001` | Réclamation | à l'**ouverture** (date d'ouverture) — pas de brouillon | `SUI:130` |
| `DOS` | `01/26` (2 chiffres minimum / 2 derniers chiffres de l'année) | Dossier d'importation | à l'**ouverture** (date d'arrivée) ; un numéro saisi à la main (reprise) est admis s'il est libre ; le compteur saute les numéros déjà pris | `SEC:195-196`, `IMP:560-570` |

| # | Règle | Référence |
|---|---|---|
| X40 | M65 « numéros à la validation » : un brouillon supprimé ne laisse **pas de trou** (commandes, réceptions, opérations, ordres : `numero` nul tant que brouillon, étape de schéma 3). Le numéro est attribué dans la même transaction que les écritures : un refus annule aussi l'incrément du compteur. | `MOD:559-561`, `MOD:640-642`, `MOD:781-783`, `DB:42-44`, commit `08c6df7` |
| X41 | Libellé d'un document sans numéro : `brouillon n° {id}` (opérations), `BC-brouillon-{id}`, `REC-brouillon-{id}` (moteur). | `OPE:60-61`, `DEP:340`, `DEP:388` |
| X42 | « Les numéros ne se répètent jamais et suivent les dates (par année de la pièce) » (cahier § 6 règle 4) : **non-répétition** garantie partout (verrou + unicité) ; **suivre les dates** n'est imposé que pour les **OF** (voir B.9). | cahier § 6, `PRO:513-519` |

---

## B.7 Parité ERP Fil (mode classeur) dans ce périmètre

| # | Règle | Référence |
|---|---|---|
| Q1 | Le moteur est celui de l'ERP Fil, vérifié au centime ; Gestion MP le nourrit par `depot.charger` (articles par référence, lots par numéro, magasins par code). Dans le serveur, `methode = "corrigee"` est **forcée** (`pour_le_moteur`) : le **mode classeur** n'est jamais actif depuis une route ; il ne sert qu'aux essais de parité (`tests/test_parite.py`) et à l'outil de comparaison (`outils/comparer_erp_fil.py`), avec 0 écart inexpliqué. | `DEP:1-7`, `PAR:185`, `CMO:125-137`, `CONFORMITE.md` § 3 |
| Q2 | Branches classeur qui touchent ce périmètre (toutes inactives en service) : perte non ajoutée aux besoins (`MOT:369`), tolérance de la règle des 100 % à 1e-6 au lieu de 0,01 point (`MOT:429`), stock en machine ignoré (`MOT:857`), fenêtre du réalisé à 0 (`MOT:868`), classe XYZ sans décalage d'un mois clos (`MOT:914`), retours de production comptés comme le classeur (`MOT:941-958`), CMUP glissant remplacé par la moyenne de tous les achats (`MOT:1985-1991`, `MOT:2395`), OTIF moyenné sur toutes les réceptions (`MOT:2870-2875`). Le coût au m² des recettes (`REF:833`) lit aussi le mode. | `MOT` (lignes citées) |
| Q3 | Codes de motif **R1–R6** de l'ERP Fil gardés (S84) ; un motif repris écrit « R… » se lit par son préfixe. | `OPE:46-53`, `DEP:226-233` |
| Q4 | Reprise de l'ERP Fil (décisions) : retours des machines **sans document** rattachés à l'ordre et annulés avec lui (P60, P71) ; une annulation reprise est datée du jour de ce qu'elle annule (`673c02c`) ; une entrée reprise retrouve sa ligne de réception par lot, date et poids (S189) ; la numérotation des lots internes continue celle de l'ERP Fil (`LOT-AAAA-NNNN`) ; les inventaires **inachevés** de l'ERP Fil ne sont pas repris (`7eff5e7`) ; « Atelier 34 » : un brouillon d'ordre repris avec un numéro est signalé à l'écran (« numéro repris, sans doute à supprimer ou à redater »). | `PRO:357-382`, `PRO:533-554`, `DEP:562-598`, `REC:50-67`, final-D |
| Q5 | Le statut « classeur » de couverture (`seuil_critique`, `seuil_alerte`) n'est affiché que **pour comparaison** ; le statut du Cockpit, du plan d'achat et du courriel compare le stock projeté au seuil d'alerte. | `PAR:42-48` |

---

## B.8 Décisions de Mohamed et des audits (tirées des commits et documents)

| Décision | Source |
|---|---|
| Trois rôles (direction, achats, alimentation) ; l'alimentation au téléphone, **sans aucun prix** ; « le serveur refuse ce que le menu cache ». | cahier § 2.1 (3 oct.), `a536296`, `ac615a6`, `96db9ea` |
| Stock **toujours en kilos**, cuir, franges et ruban compris ; prix au kilo ou au mètre ; mètres indicatifs (la correction « tout en mètres » a été défaite, étape de schéma 14). | 8 oct., `d2e1e39`, `b75bc24`, AUDIT § « Défauts bloquants » |
| Stock **en magasin ou en machine** : le fil monté, pas encore tissé, compte dans le stock global et sa valeur, et dans ce qu'on a avant de commander. | `169dfdc`, `f33a428` |
| Numéros donnés par le logiciel, à l'envoi ou à la validation ; un OF sert une fois, un jour, numéros dans l'ordre des dates. | M65, M67, `08c6df7`, `a794812` |
| Lot obligatoire sur tout mouvement ; ordre sur toute sortie. | M64 |
| Saisie en deux temps (brouillon, puis validé) ; annuler = contre-passer, une fois, daté de l'original ; expliqué et confirmé sur la ligne. | M72, M73 |
| Une sortie ne prend pas un lot absent à sa date ; la proposition ne prend que les lots présents à la date de l'ordre ; contrôle C37. | `61027e4`, `202d1a0`, AUDIT |
| Annuler un ordre annule ses retours (y compris ceux repris de l'ERP Fil). | `a536296`, `202d1a0` |
| Libération de quarantaine = décision des achats, motif imposé ; mise en quarantaine possible par l'atelier, motif imposé. | final-E « Décisions prises » |
| Inventaire : feuille à l'aveugle, second comptage par une autre personne, tournant par classe **et par magasin**, refusé s'il est daté avant le dernier mouvement d'un lot figé, écarts valorisés. | final-E, `f6f3acc`, `5ca0960` |
| Période close : rien ne s'y écrit ; le coût d'un mois clos ne change plus ; la direction rouvre (tracé), saisit, referme. | `f6f3acc`, `f216509`, AUDIT |
| Prévu des ordres figé à la validation ; le passé jugé sur le plan et les recettes de son époque (versions du plan au journal, versions de recette). | `db25831` |
| Une qualité arrêtée ne part plus (proposition, brouillon, validation). | `202d1a0` |
| Bilan : annulations à part ; dirhams sans réceptions annulées ; ouverture affichée. | `f85dabd`, audit 2-G G4, 2-F G2 |
| Une seule définition de l'OTIF moyen. | `96db9ea` |
| Pas d'image SVG en pièce jointe ; échecs de connexion simultanés sans erreur ; restauration qui ne s'attend plus elle-même. | `d8882d4` |
| Sauvegardes et pièces des bases d'essai rangées à part ; QR joignable par le téléphone ; sauvegardes de cette base seulement ; restauration d'une autre base refusée. | `7eff5e7`, `59d897d`, `f85dabd` |
| Seuils de réglages refusés dans le désordre. | `f85dabd` |
| Une seule heure : celle du serveur (Maroc). | `238729e`, `9724d96` |
| Non retenus : emplacements sous le magasin, plusieurs sources par matière, table de motifs modifiable, durée de session réglable à l'écran, API par jeton, notifications (remplacées par « Ma journée », « À valider », courriel du lundi). | cahier § 10, `CONFORMITE.md` |

---

## B.9 Points incohérents ou ambigus

Relevés en lisant le code ; chacun est à **trancher** pour Gestion MP PRO (garder, corriger, ou
écrire la décision). Classés par domaine.

### Transverse

| # | Constat | Référence |
|---|---|---|
| I1 | La partie A (§ 0.2) dit que les refus Pydantic sont « en anglais » : ils sont en fait **traduits** en français par un gestionnaire global (C2) — à harmoniser à la fusion. | `MAIN:164-187` |
| I2 | Plusieurs pannes donnent une **500 sans message français** (contraire au cahier § 5.10 « aucune erreur serveur sur une saisie fausse ») : `GET /bilan?mois=2026-13` (`ValueError`, `SUI:529`) ; `POST /signalements` avec un `article_id` inconnu (clé étrangère, aucun contrôle, `SUI:198-203`) ; `POST /sauvegardes` sans `pg_dump` et restauration d'un fichier illisible (`RuntimeError`, `SAU:53-77`). | cités |
| I3 | Formats de nombres incohérents dans des textes : journal des ordres `f"{total:,.1f} kg"` → « 1,234.5 kg » (virgule de milliers, point décimal — `PRO:444`, `PRO:528`) ; refus UR8 « 1 200.0 réclamés » (point décimal, `SUI:119-120`) ; ailleurs « 1 234,50 » (`STK:23-24`). | cités |
| I4 | Deux définitions de « l'entrée » d'un lot : `presents_au` utilise `lot.entre_le` (`PRO:141-144`) ; `couvert_a_sa_date` utilise le premier jour où la somme des mouvements **du magasin** est positive (`STK:102`) — un jour avec entrée et sortie qui s'annulent n'est pas vu comme une entrée. | cités |
| I5 | « Écriture antidatée » : aucune limite en jours ; seule l'année < 2000 et la période close bloquent. Une faute « 2025 pour 2026 » passe si la période n'est pas close. | `SEC:213-226` |
| I6 | `LECTURE` et `TOUS` sont définis mais jamais utilisés. | `SEC:117-118` |
| I7 | Le journal d'audit enregistre le **nom** de la personne, pas son identifiant : renommer un compte coupe son histoire en deux (« Mohamed / MOHAMED », recette direction 32). Idem `auteur` des mouvements, `cree_par`, `valide_par`. | `SEC:169`, `MOD:532` |

### Stock et opérations

| # | Constat | Référence |
|---|---|---|
| I10 | Un inventaire ouvert suspend **tout le magasin** (entrées comprises, toutes matières), même hors de son périmètre ; le cahier § 5.8 dit « mouvements suspendus sur ce qui est compté » (final-E : « blocage limité aux matières comptées : ⛔ »). Un inventaire au périmètre **vide** s'ouvre quand même et bloque le magasin. | `STK:157-168`, `INV:290-311` |
| I11 | Les motifs ne sont **pas contrôlés** contre la liste (seul le motif est exigé non vide) : un retour « Reliquat » est accepté (`T:test_parcours.py:377`) mais n'a pas de code R, que le contrôle C03 relève ensuite. « Non-conformité qualité » et « Refus après quarantaine » ont le même code R3. | `OPE:253-254`, `OPE:49-53` |
| I12 | Blocage OB6 faux positif : un **ajustement négatif** dans un magasin désactivé est annoncé « désactivé » alors que `ecrire` accepte les sorties d'un magasin désactivé. | `OPE:124-128`, `STK:152-153` |
| I13 | Messages : valider une opération **annulée** répond « Cette opération est déjà validée. » ; valider un ordre **annulé** répond « Ce bon est déjà validé. ». | `OPE:400-401`, `PRO:500-501` |
| I14 | L'alimentation peut **supprimer** un brouillon de libération de quarantaine préparé par les achats (aucun contrôle à la suppression) et **annuler** une libération validée (remettant la matière en quarantaine) : la règle « libérer est une décision des achats » ne couvre ni la suppression ni l'annulation. | `OPE:381-392`, `OPE:445-457` |
| I15 | Le recalage des bons de commande est lancé pour **tout** transfert avec la raison « sortie de quarantaine », même un simple rangement. | `OPE:338-342`, `OPE:439-440` |
| I16 | Le cours d'un **stock d'ouverture** en devise est celui du **jour de la validation**, pas celui de la date de l'opération (une ouverture antidatée prend le cours d'aujourd'hui). Un prix 0 est admis (stock entré à coût nul). | `STK:181-186`, `OPE:237` |
| I17 | Retour fournisseur : un lot **sans fournisseur** compte comme un fournisseur « `None` » ; mêler un tel lot et un lot de F est refusé « deux fournisseurs », et l'opération peut porter `fournisseur_id = NULL`. | `OPE:319-332` |
| I18 | `stock.disponibles` (FIFO, proposition) ne retire pas les magasins **désactivés**. | `STK:273-300` |
| I19 | Les **réponses** des routes d'écriture d'opérations ne masquent pas les prix (seuls les deux GET le font) — sans fuite aujourd'hui (l'alimentation n'écrit que des retours et transferts à prix 0), mais le filtre n'est pas générique. | `OPE:356`, `OPE:442` |
| I20 | `GET /operations` est tronqué à 1 000 sans le dire (`tronque` absent, contrairement à `/mouvements`). | `OPE:216` |
| I21 | Le cahier § 5.2 décrit « mise en quarantaine / libération (changement de statut, sans quantité) » ; le code en fait des **transferts** de quantité entre magasins (le statut du lot est calculé). | cahier § 5.2, `OPE:308-318`, `APS:50-57` |
| I22 | Le cahier § 4 donne à l'alimentation la **lecture** des réceptions et factures : `/api/receptions` et `/api/factures` sont réservées aux achats. | cahier § 4, partie A |
| I23 | La recherche `q` de `/mouvements` et `/soldes` n'échappe pas `%` et `_` (contrairement au journal d'audit, corrigé). | `APS:126`, `APS:226`, `CPT:228-229` |

### Inventaires

| # | Constat | Référence |
|---|---|---|
| I30 | Numéro `INV` attribué **à l'ouverture** : un inventaire abandonné laisse un **trou** dans la série (contraire à l'esprit de M65). | `INV:304`, `INV:418-430` |
| I31 | Un lot trouvé est **créé comme lot** dès la saisie du comptage (avant validation) et reste si l'inventaire est abandonné. | `INV:369` |
| I32 | Un enregistrement de comptage qui renvoie une ligne sans `compte` **efface** le comptage (et palettes, bobines, justification) : le corps doit toujours tout renvoyer. | `INV:349-350` |
| I33 | Conflit d'ouverture : le message dit « déjà ouvert sur ce magasin » même quand le conflit vient d'un inventaire **global**, ou quand on ouvre un global. Un inventaire global fige aussi la **quarantaine**. | `INV:274-281` |
| I34 | Aucune annulation d'un inventaire **validé** (pas de statut, pas de route) ; ses ajustements ne se contre-passent pas. Pas de `cree_le`. Le premier compteur n'est pas en base (le recomptage « à quatre yeux » n'est que signalé à l'écran). | `MOD:825-842`, final-E « Achats M22 » |
| I35 | Cadences du tournant (30/90/365 j) codées en dur, pas en réglage. | `INV:32` |
| I36 | Les soldes figés sont `> 0` (pas `> POUSSIERE`) alors que partout ailleurs le seuil est le gramme (sans effet pratique, `ecrire` remet à 0 sous le gramme). | `INV:291` |

### Production

| # | Constat | Référence |
|---|---|---|
| I40 | « Numéros dans l'ordre des dates » : la date du **dernier ordre** compte aussi les ordres **annulés** — un ordre validé puis annulé aujourd'hui interdit encore de valider un ordre daté d'hier, alors qu'il n'a rien consommé. (Effet voulu pour la suite des numéros, mais non écrit.) | `PRO:286-287`, `PRO:516` |
| I41 | La proposition ne contrôle ni le magasin (inconnu, quarantaine) ni la date (future = stock d'aujourd'hui). | `PRO:190-237` |
| I42 | Décision écrite « une bobine se compte entière à la conversion » (final-E) : le serveur accepte des bobines et palettes **fractionnaires**. | `PRO:62` |
| I43 | La route `/production/realise` existe aussi dans `pilotage.py`, masquée par l'ordre d'enregistrement des routeurs (code mort à retirer). | `PPL:186-198`, final-E « Direction 8 » |
| I44 | Un retour **brouillon** d'un ordre annulé reste en brouillon (sa validation sera refusée) au lieu d'être signalé ou supprimé avec l'ordre. | `PRO:565-566` |

### Suivi

| # | Constat | Référence |
|---|---|---|
| I50 | Réclamation : motif libre (non contrôlé, contrairement à l'issue) ; la quantité « livrée » compte les lignes **refusées** ; un `PUT` remplace réponse, issue et montant même vides ; une réclamation **close** se modifie sans être rouverte dès qu'une issue est envoyée ; numéro `RCL` donné à l'ouverture (pas de brouillon). | `SUI:73-169` |
| I51 | Pièces jointes : le type MIME est celui **déclaré** par le navigateur ; le motif `application/vnd\..+` admet n'importe quel type « vnd » (y compris `application/vnd.microsoft.portable-executable`) ; la taille est contrôlée **après** lecture complète en mémoire ; la liste `GET /pieces/{objet}/{id}` ne vérifie pas l'objet. La sécurité repose sur le téléchargement forcé + `nosniff`. | `SUI:231-278` |
| I52 | Échéancier : conversion en MAD au cours **actuel** (pas au cours figé) ; une devise inconnue vaut 1 ; `du`/`au` ne filtrent que les échéances (pas « à dater » ni « réglées ») ; un règlement n'est contrôlé ni contre la période close ni contre l'an 2000. | `SUI:330-392`, `SUI:412-426` |
| I53 | Versions de recettes : une version est prise dès qu'une ligne est « touchée », même sans changement ; l'auteur vient de `s.info["auteur"]`, jamais remis à zéro entre deux transactions de la même session (auteur périmé possible) et vide si la transaction n'écrit pas de journal. | `SUI:441-476` |
| I54 | Signalement : un signalement déjà traité peut être « traité » de nouveau (réponse écrasée) ; tout le monde lit tous les signalements. | `SUI:214-223`, `SUI:190-195` |
| I55 | Bilan : `mois` « 0000-00 » ou « 2026-13 » passe le motif puis tombe en 500 (I2). | `SUI:618-622` |

### Comptes et sécurité

| # | Constat | Référence |
|---|---|---|
| I60 | « Code à 4 chiffres » : le serveur exige 4 **caractères**, pas des chiffres. Passer un compte de l'alimentation aux achats **sans** nouveau code garde un code de 4 caractères (la longueur n'est vérifiée que si un code est fourni). | `SEC:50-52`, `CPT:202-205` |
| I61 | `vu_le` (« dernière activité ») n'est mis à jour qu'à la **connexion** ; les sessions expirées ne sont jamais purgées ; changer son code ne ferme pas ses autres sessions ; un mauvais « ancien code » n'est pas compté comme échec. | `SEC:71`, `CPT:141-152` |
| I62 | Le verrouillage est **par identifiant** (même inconnu) : n'importe qui peut bloquer un compte réel en se trompant 5 fois (déni de service) ; la table `tentative` garde les identifiants inconnus. `/visages` (public) liste les identifiants et rôles actifs (voulu pour l'écran de connexion). | `SEC:128-147`, `CPT:64-73` |
| I63 | `PUT /utilisateurs/{id}` exige un `identifiant` (2–40) qu'il ignore. | `CPT:158-201` |
| I64 | `courriel_dernier_envoi` est un paramètre hors de la liste des réglages : invisible dans `GET /parametres`, refusé par `PUT /parametres`. | `COU:94-97`, `CPT:295-297` |
| I65 | Prix masqués : filtre **route par route** par listes de clés, pas générique ; l'alimentation lit encore des **montants** dans `GET /parametres` (seuils en MAD : `seuil_bc_urgent`, `seuil_approbation`, tiers…) et les **cours** des devises (`GET /devises`, historique). | `CPT:276-289`, `CPT:400-427` |
| I66 | `date_cloture` peut être **reculée** (réouverture partielle) ou vidée sans autre contrôle que la trace ; clore ne vérifie pas qu'il reste des brouillons datés dans la période (ils deviennent invalidables). | `CPT:312-317` |

### Exploitation

| # | Constat | Référence |
|---|---|---|
| I70 | `/api/sante` et l'alerte du Cockpit lisent `sauvegarde.etat()` (**tous** les fichiers du dossier) alors que Réglages lit `etat_sauvegardes()` (**cette base** seulement) : une sauvegarde d'une autre base rendue au même dossier peut faire paraître la sauvegarde « fraîche ». | `MAIN:195-200`, `SAU:129-144`, `CPT:473-489` |
| I71 | Restauration : couper « toutes les autres connexions » coupe aussi la connexion qui tient le verrou des tâches de fond (`7426102`) — le verrou est perdu en silence (la boucle continue) ; le journal d'audit postérieur à la sauvegarde disparaît (seule la ligne « restauration » est ajoutée) ; les sessions sont celles de la sauvegarde (la personne qui restaure peut être déconnectée). | `SAU:147-196`, `MAIN:92-98` |
| I72 | Purge : seules les quotidiennes sont purgées, et seulement après une sauvegarde quotidienne ; les manuelles et « avant-restauration » s'accumulent sans limite. | `SAU:96-118` |
| I73 | Tâches : si la photo des indicateurs échoue, le courriel n'est pas tenté à ce passage ; une erreur d'envoi est écrite sous l'étiquette « [indicateurs] ». | `SUI:841-847`, `MAIN:102-105` |
| I74 | Numérotation : « les numéros suivent les dates » (cahier § 6 règle 4) n'est imposé que pour les OF ; une réception, une opération, un bon de commande validés plus tard pour une date antérieure prennent un numéro plus grand. Les séries `INV`, `RCL`, `DOS` sont numérotées à la création (trou possible si l'objet est supprimé), et `POST /lots/numero-interne` consomme un `LOT` immédiatement alors que le code dit « à la validation (pas avant : … ne laisse pas de trou) ». | `REC:45-47`, `REC:665-670`, cahier § 6 |
| I75 | Le cahier § 5.2 annonce le lot interne `LOT-AAAA-NNNNN` (5 chiffres) ; le code en donne 4. | cahier § 5.2, `REC:67` |
| I76 | Le **cache** du moteur repose sur une signature (max des id, somme des soldes…) : une écriture qui ne toucherait ni le journal d'audit, ni les mouvements, ni les paramètres, ni les soldes (par ex. une modification directe en base) ne l'invaliderait pas. | `DEP:673-683` |

