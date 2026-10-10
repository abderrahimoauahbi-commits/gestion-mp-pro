# Défauts de Gestion MP : tri, vérification et plan de correction

Le 8 octobre 2026, après le commit `b925e81` de `~/gestion-mp`. Ce document est fait **pour corriger Gestion MP en service**, pendant que Gestion MP PRO se construit à côté.

**Sources.** Les sections d'incohérences des inventaires de `docs/heritage/` :

- API (parties A et B) ;
- CALCULS (parties A et B) ;
- CONTROLES ;
- DONNEES ;
- EXPLOITATION ;
- REGLAGES ;
- REGLES (parties A et B) ;
- ECRANS (huit parties et la synthèse transverse) ;
- ESSAIS (§ 15 à 18) ;
- REGLES-ECRAN (§ 7) ;
- AMELIORATIONS-PRO (partie 2) ;
- DECISIONS (§ 15 et 16).

On a relevé environ 560 constats bruts. Les doublons sont fusionnés : un même défaut vu par plusieurs inventaires forme une seule entrée, et toutes ses sources sont citées.

**Méthode.** Chaque point qui le méritait a été relu dans le code à `b925e81`. Le verdict est noté ainsi :

- **vérifié** : le code fait bien ce qui est dit ;
- **partiel** : le constat n'est vrai qu'en partie, ou sa gravité est différente ;
- **non confirmé** : le code ne fait pas ce qui est dit ;
- **déjà corrigé** : un commit après l'inventaire a réglé le point.

Les chemins sont relatifs à `~/gestion-mp/`. Pour le serveur, le préfixe `gestion_mp/` est omis : `api/achats.py` désigne `gestion_mp/api/achats.py`. Les numéros de ligne sont ceux de `b925e81`.

**Abréviations des sources.**

| Abréviation | Inventaire et section |
|---|---|
| API-A n | `API.md`, § A.12, point n |
| API-B n | `API.md`, § 13, point n |
| CAL-A n | `CALCULS.md`, § 6, point n |
| CAL-B n | `CALCULS.md`, § 12, point n |
| CTL n | `CONTROLES.md`, § 6, point n |
| DON n | `DONNEES.md`, § 14, point n |
| EXP n | `EXPLOITATION.md`, § 13, point n |
| RGL n | `REGLAGES.md`, § 9, point n |
| RG-A I-nn | `REGLES.md`, partie A, § 6 |
| RG-B Inn | `REGLES.md`, partie B, § B.9 |
| ECR p.n | `ECRANS.md`, partie p, anomalie n |
| ECR-T n | `ECRANS.md`, synthèse transverse, point n |
| ESS | `ESSAIS.md`, § 15 à 18 |
| REC | `REGLES-ECRAN.md`, § 7 |
| AML Rn | `AMELIORATIONS-PRO.md`, partie 2 |
| DEC | `DECISIONS.md` |

## Les quatre classes

- **À CORRIGER DANS GESTION MP** : un défaut visible ou une menace sur les données. Exemples : faux chiffre, règle contraire à une décision, refus faux ou message trompeur, erreur 500, perte de saisie ou de données, fuite de prix ou de droits, trou de numérotation, contrôle qui ne contrôle pas, texte contraire au comportement, outil cassé, sauvegarde ou restauration en défaut. Les commentaires faux en font partie, en priorité basse.
- **PRO SEULEMENT** : un changement de structure lourd, sans défaut visible aujourd'hui. Il est à faire dans Gestion MP PRO et ne doit pas être reproduit.
- **DÉCISION DE MOHAMED** : un vrai choix métier, avec une recommandation au plus près de la pratique d'usine.
- **PAS UN DÉFAUT** : un comportement voulu, une décision déjà prise, du code mort sans effet ou une documentation à mettre à jour sans conséquence.

Quand un choix technique n'engageait pas le métier, il a été tranché ici selon la pratique d'usine, comme Mohamed l'a demandé le 2 octobre (« fais au mieux… coller le plus possible à la réalité », DECISIONS P11). Il n'est donc pas renvoyé à Mohamed.

Gravité :

- **bloquant** : faux chiffre de stock, de valeur ou d'achat, faille de droits, ou outil indispensable cassé ;
- **gênant** : l'utilisateur est trompé, perd une saisie, ou une donnée se dégrade ;
- **mineur** : libellé, cas rare, confort.

## Synthèse

### Nombre d'entrées par classe

On est parti d'environ 560 constats bruts. Une fois les doublons fusionnés, il reste **268 entrées**.

| Classe | Entrées |
|---|---|
| **À CORRIGER DANS GESTION MP** | **166** |
| **PRO SEULEMENT** | **40** (28 dans les domaines + 12 chantiers transverses) |
| **DÉCISION DE MOHAMED** | **9** |
| **PAS UN DÉFAUT** | **53** (dont 2 déjà corrigés par `b925e81` ; la 3ᵉ correction déjà faite, la route `/production/realise` en double, est notée dans D-20) |

Les 166 entrées à corriger se répartissent ainsi : 152 vérifiées entièrement dans le code et 14 vérifiées en partie (le défaut existe, mais pas tout à fait comme l'inventaire le disait). Quinze constats des inventaires n'ont **pas été confirmés**. Ils sont rangés en « PAS UN DÉFAUT », avec leur raison.

### À corriger : domaine × gravité

| Domaine | Bloquant | Gênant | Mineur | Total |
|---|---|---|---|---|
| **A** Achats, réceptions, fournisseurs, matières, échéancier, réclamations | 3 | 9 | 18 | **30** |
| **B** Importations, dossiers, frais | 1 | 1 | 9 | **11** |
| **C** Stock, opérations, inventaires, valorisation, numérotation | 2 | 2 | 16 | **20** |
| **D** Production, atelier, recettes, métiers, plan, besoins | 3 | 4 | 14 | **21** |
| **E** Pilotage, contrôles, réglages, exports, bilan, courriel | 4 | 4 | 11 | **19** |
| **F** Comptes, sécurité, droits, sessions | 2 | 4 | 3 | **9** |
| **G** Exploitation, sauvegardes, restauration, outils, pièces jointes | 4 | 4 | 6 | **14** |
| **H** Écrans | 2 | 23 | 17 | **42** |
| **Total** | **21** | **51** | **94** | **166** |

### Les 21 bloquants

| # | Entrée | En une ligne |
|---|---|---|
| 1 | **C-01** | L'alimentation annule une mise en quarantaine : elle libère de la matière sans les achats (D6). |
| 2 | **E-01** + **H-03** | L'alimentation reçoit le conseil d'achat, les seuils en dirhams, les banques et les cours (D5). |
| 3 | **G-02** | Restaurer une sauvegarde ancienne peut laisser une base mêlée, avec un schéma en retard. |
| 4 | **G-03** | Pièces jointes : aucun miroir dans les sauvegardes réelles, chemin absolu, mêlées aux essais. |
| 5 | **G-04** | Le compte « verificateur » a le rôle de direction et un code écrit en dur. Il reste actif si le vérificateur est interrompu. |
| 6 | **G-01** | « Vider l'activité » échoue (clés étrangères) : la mise en service est impossible (P9). |
| 7 | **F-01** + **H-01** | Un code d'atelier de 5 chiffres ne se tape pas. Un compte promu à la direction garde un code de 4 caractères. |
| 8 | **F-02** | N'importe qui bloque n'importe quel compte ; une rafale de connexions dépasse le seuil de 5 échecs. |
| 9 | **D-01** | Un « NaN » dans le plan ou dans un poids au m² fait tomber en 500 le stock, les besoins, le plan d'achat et le cockpit. |
| 10 | **D-02** | La matière reçue « sous réserve » est proposée au rachat alors que son bon n'est pas soldé (R11r). |
| 11 | **E-02** | Changer un cours de devise revalorise des marchandises de mois clos (V3). |
| 12 | **A-04** | Une réception réécrit une facture réglée, partagée ou portée par un dossier clos. |
| 13 | **B-01** | Un frais d'importation réglé se modifie, se retire ou disparaît avec son dossier (I20). |
| 14 | **C-02** | Une entrée à prix 0 est valorisée au prix du catalogue : le CMUP est faux (V2). |
| 15 | **E-03** | Le bilan du mois ne s'équilibre pas en valeur, compte des bons annulés, et tombe en 500 sur un mois invalide. |
| 16 | **A-02** | Changer le rôle d'une matière qui est dans une recette casse la règle des 100 % sans refus (F13). |
| 17 | **A-03** | L'import tableur des matières passe l'aperçu puis tombe en 500, ou désactive une matière par une faute de frappe. |
| 18 | **D-03** | Renommer une matière casse les versions de recette, le prévu des ordres et le coefficient de réalisation. |
| 19 | **E-04** | La matrice des prix fait la moyenne de dollars et d'euros. |

**C-03** renvoie à G-01 et n'est pas compté deux fois. H-01 et H-03 sont les volets écran des lignes 7 et 2 : ils comptent comme bloquants dans le domaine H, ce qui donne 21.

### Ordre de travail conseillé

1. **Tout de suite, sans attendre les équipes.** En production, désactiver le compte `verificateur` s'il est actif (G-04). Puis faire une sauvegarde **manuelle**, et vérifier à la main que le dossier `pieces-jointes` existe bien dans les sauvegardes (G-03).
2. **Vague 1 : les bloquants**, les huit domaines en parallèle. G livre d'abord les étapes de schéma demandées : `reclamation.reception_ligne_id`, `commande.soldee_le` / `annulee_le`, `operation.annulee_par` / `annulee_le`, CHECK NaN, statut « abandonne » de l'inventaire, unicité (ordre, qualité), ordres d'avant l'étape 9.
3. **Vague 2 : les gênants.**
4. **Vague 3 : les mineurs**, y compris les commentaires faux.

À chaque vague : `pytest` (tous les essais, plus `tests/test_defauts_*.py`), puis `python -m gestion_mp.verificateur` (0 écart), puis une recette à la main des écrans de H au bon rôle.

## Décisions de Mohamed

Ces choix sont métier. Ils ne bloquent aucune correction ci-dessous. Pour chacun, on recommande ce qui suit la pratique d'usine.

| # | Question | État aujourd'hui | Recommandation au plus près de la pratique |
|---|---|---|---|
| **DM-01** | Prix de la **bande (2,5 USD)** et du **cuir (0,074 USD)** : au kilo ou au mètre ? (DEC Q1) | Lus au kilo. | Regarder une facture SOFIA TEXTILE. Si elle dit « / m » ou « / ml », passer la fiche « au mètre » (densité connue). Sinon, garder le kilo. Le prix d'un cuir à 0,074 le kilo semble invraisemblable, alors qu'au mètre il est plausible : **probablement au mètre**. |
| **DM-02** | **Franges** : six qualités (8M, 8S, LP, MN, MP, SH) demandent 0,8 ml/m² sans matière Franges. (DEC Q2) | C01 bloquant. | Si ces tapis portent bien des franges, **créer la matière Franges**, avec son fournisseur et sa densité pesée (kg par mètre). Sinon, mettre le poids à 0. Le contrôle reste bloquant tant que ce n'est pas tranché, ce qui est juste. |
| **DM-03** | Valoriser une importation **à la pesée × prix** ou **à la facture** ? (DEC Q4, V9) | Pesée × prix ; C36 signale l'écart. | **Garder la pesée × prix confirmé** pour le stock, c'est-à-dire ce qui est réellement entré. Un écart avec la facture est une **réclamation au fournisseur** (manquant, surfacturation), pas un coût de la matière. La comptabilité paie la facture. |
| **DM-04** | **TPI 0,25 %** dans la TVA attendue. (DEC Q5) | Réglable, 0,25 %. | Le faire confirmer par le transitaire sur une DUM réelle. Garder le réglage. |
| **DM-05** | **Sortie oubliée de la veille** quand un ordre du jour est déjà validé. (DEC Q6, M67) | Consigne : dater l'ordre du dernier ordre validé, et écrire la vraie date en commentaire. | Garder la consigne : le numéro suit l'ordre de saisie, comme sur un registre d'atelier, et la vraie date est écrite. Seule exception à prévoir : un ordre oublié **à cheval sur une fin de mois**. La direction le passe alors à la vraie date, avec un motif. Cela fausse sinon la consommation du mois clos. |
| **DM-06** | **Données de reprise signalées** (P8) : couleurs « Oilve » et « Turkoise » ; lot GLO260914-884 sur deux matières ; dossier 80/26 (6,55 M MAD de droits sans marchandise) ; brouillons repris numérotés ; comptes « Mohamed » et « MOHAMED ». (DEC § 16.8) | Signalées, jamais corrigées. | Approuver la correction d'orthographe des deux couleurs : ce sont des référentiels réels, une faute de frappe, sans effet sur les quantités. Les autres points relèvent de l'**activité d'essai**, qui disparaît au « vider l'activité » de la mise en service (G-01). Fusionner les deux comptes. |
| **DM-07** | **Consommation et fil monté** : une sortie vers les machines compte comme consommée (bilan, DIO, coefficient de réalisation, XYZ), **et** le fil monté compte dans le stock (U8). La même matière est donc à la fois consommée et en stock. (CAL-A 4, CAL-B 8, DEC § 16.1) | U8 est décidé ; la consommation n'est pas retouchée. | Garder U8. En pratique d'atelier, la **consommation réelle d'une période = sorties nettes − hausse du stock sur les métiers** : ce qui est sur le cantre n'est pas encore tissé. Dans Gestion MP, le montage n'a pas d'historique : se contenter d'afficher le stock sur les métiers à part dans le bilan (E-03). Dans PRO, modéliser « en machine » comme un lieu de stock. |
| **DM-08** | **« Les numéros suivent les dates »** (A10, cahier § 6.4) pour les réceptions, les bons et les opérations. Aujourd'hui, une pièce antidatée validée plus tard prend un numéro plus grand. (RG-A I-04, RG-B I74) | Imposé aux seuls ordres de fabrication (M67). | **Numéroter dans l'ordre de validation** (registre), avec la date d'effet à côté. C'est l'usage d'un registre d'arrivage. Corriger la phrase du cahier. Imposer l'ordre des dates aux réceptions bloquerait la saisie d'un camion de la veille. |
| **DM-09** | **À fournir pour la mise en service** (DEC Q3) : codes douaniers (référentiel vide), compte d'envoi du courriel (SMTP), Tailscale pour la 4G/5G. | Manquants. | Donner la liste des codes du transitaire, une adresse d'envoi dédiée, et créer le compte Tailscale. |

## Chantiers PRO SEULEMENT (transverses)

Ces chantiers ne sont pas à faire dans Gestion MP. Ils ne cachent ni fuite ni faux chiffre : ceux qui en cachaient un ont reçu un correctif local ci-dessous, indiqué entre parenthèses.

| # | Chantier | Sources |
|---|---|---|
| P-01 | `Numeric` au lieu de `float`, et un seul seuil de poussière. | DON 4, DON 5, CTL 9 |
| P-02 | Filtre `sans_prix` générique, à toute profondeur, et classe de route. (Correctifs locaux : **E-01**, **A-14**, essai **F-05**.) | API-A 2, API-B 1, AML R8 |
| P-03 | Codes et formes d'erreur uniformes, et modèles de réponse. (Correctif local : **F-06**, **F-07**.) | API-A 5-7, API-B 10, AML R16 |
| P-04 | Découper les fichiers et fonctions géants : `moteur.py` 3 760 l., `controler()` 869 l., `etat_stock()` 640 l. | AML R2, R3, R4 |
| P-05 | Schéma consolidé, migrations contiguës et figées (Alembic ou équivalent). | DON 1-3, AML R10 |
| P-06 | Champ `version` au lieu de l'empreinte. Empreinte obligatoire. | DEC F10, RG-A I-16 |
| P-07 | Identifiants partout : utilisateur au lieu du nom, `article_id` dans les JSON (correctif local : **D-03**), FK au lieu des liens polymorphes. | DON 6, 7, 18, 19, RG-B I7 |
| P-08 | « En machine » comme lieu de stock, avec écriture et historique. Inventaire limité à son périmètre. | DEC § 16.1, 16.2, N3 |
| P-09 | Exploitation professionnelle : Docker ou systemd, HTTPS, plusieurs processus, cache partagé, journalisation structurée. (Correctifs locaux : **G-07**, **G-11**.) | AML R6, R7, R12, R17, R18, EXP 10 |
| P-10 | Écran : TypeScript strict, composants (tableau, formulaire), une route par fiche, styles, types générés, essais d'écran. | AML R1, R5, R13-R15, R21, R22, REC § 7 |
| P-11 | Essais : rangés par domaine, sans ordre, valeurs chiffrées au lieu d'essais de fumée, table de transitions de l'approbation, balayage générique des droits et des prix. | ESS § 15-18, AML R9, R23 |
| P-12 | Dépendances bornées, paquet déclaré, historique git lisible, documentation technique. | AML R19, R20, R24 |

Restent quelques points traités comme PAS UN DÉFAUT sans tableau propre :

- DON 12 (format NN/AA) : c'est le numéro de la maison ;
- DON 14 à 16 et DON 25 à 27 : colonnes constantes ou inutilisées, poids du dernier lot voulu, étape 14 déjà passée ;
- CAL-A 26 : dormants conformes à V6 ;
- API-A 30 : ordre des routes ;
- API-B 22 : `POST /bons/proposition` en lecture ;
- RG-B I21 : cahier ;
- RG-B I64 : réglage caché du courriel ;
- DEC § 16.5 à 16.7 : constante de rôle, délai mesuré, cours datés, pour PRO.

## Domaines d'équipe et fichiers possédés

Une entrée appartient au domaine qui **possède les fichiers qu'elle modifie**. Quand un défaut touche à la fois le serveur et l'écran, il a deux entrées : la partie serveur va au domaine A à G, la partie écran au domaine H, et chacune renvoie à l'autre.

Trois fichiers sont partagés entre plusieurs domaines : `calcul/moteur.py`, `api/referentiels.py` et `api/suivi.py`, plus `api/comptes.py` et `main.py`. Pour ces fichiers, la propriété se fait **par fonction ou par plage de routes**, comme l'indique le tableau. Deux équipes ne modifient jamais la même fonction.

| Domaine | Fichiers possédés en entier | Parties possédées dans un fichier partagé |
|---|---|---|
| **A** Achats, réceptions, fournisseurs, matières, échéancier, réclamations | `api/achats.py`, `api/receptions.py`, `api/exports_achats.py` | `api/referentiels.py` : classification et rôles (l. 83-343), fournisseurs (344-543), matières, catalogue, `composer` (544-782), exports matières et fournisseurs (1471-1519) · `api/suivi.py` : réclamations (66-189), échéancier (320-478), import des matières (701-849) · `api/exports.py` : `exporter_bon_de_commande` (307-fin, à supprimer) · `calcul/moteur.py` : `performance_receptions`, `points_score`, `scorecard_fournisseurs`, `devises_pratiquees` (2630-2950), `pesees`, `evolution_bobines` (3013-3176) |
| **B** Importations, dossiers, frais | `api/importations.py`, `api/referentiels_import.py`, `api/analyse_import.py` | `api/referentiels.py` : `GET /postes-frais` (1450-1470) · `calcul/moteur.py` : `LigneRevient` jusqu'à la fin du fichier (3529-3760 : `tva_attendue`, `valeur_ligne_import`, `revient_dossier`, `ecart_facture`, `revient_par_*`) |
| **C** Stock, opérations, inventaires, valorisation, numérotation | `services/stock.py`, `api/stock.py`, `api/operations.py`, `api/inventaires.py`, `api/brouillons.py`, `depot.py` | `securite.py` : `numero` et `_inserer_compteur` (l. 179-205) · `api/referentiels.py` : magasins (1060-1197) · `calcul/moteur.py` : `a_la_date` (85-190), `LigneValorisation` à `valorisation` (1781-2053), `stock_par_lot`, `lots_disponibles`, `tracabilite` (3177-3325) |
| **D** Production, atelier, recettes, métiers, plan de production, besoins et plan d'achat | `api/production.py`, `api/production_plan.py`, `calcul/modele.py`, `calcul/classification.py` | `api/referentiels.py` : qualités, recettes, versions, plan (783-1059), métiers et montage (1198-1449), export des qualités (1520-fin) · `api/suivi.py` : signalements (190-241), versions de recettes (479-515) · `calcul/moteur.py` : des fonctions du plan à `_tier` et `plan_achat` (191-1780), `consommation_par_of`, `realise_par_qualite` (3326-3528) |
| **E** Pilotage, contrôles, réglages, exports, bilan, courriel | `api/pilotage.py`, `calcul/controles.py`, `parametres.py`, `api/exports_analyse.py`, `services/courriel.py` | `api/exports.py` : `/export/pilotage`, `/export/mouvements` (1-306) · `api/suivi.py` : indicateurs, bilan, courriel (516-700, 850-fin) · `api/comptes.py` : paramètres, historique, devises (276-491) · `calcul/moteur.py` : `Opportunite` jusqu'à `_concentration_devises` (2054-2629 : opportunités, cockpit), `historique_prix` (2951-3012), `arrondi` et utilitaires de dates (52-84) |
| **F** Comptes, sécurité, droits, prix masqués, sessions | `securite.py` (sauf `numero`), `config.py` | `api/comptes.py` : état, visages, installation, connexion, déconnexion, moi, utilisateurs, journal (54-275) · `main.py` : middleware `protections` et traduction des erreurs (136-200) · nouvel essai `tests/test_droits_toutes_routes.py` |
| **G** Exploitation, sauvegardes, restauration, outils, pièces jointes, migrations, documentation | `services/sauvegarde.py`, `db.py`, `modeles.py`, `reprise.py`, `verificateur.py`, `outils/*`, `scripts/*`, `.claude/launch.json`, `docs/*.md` (sauf `REGLES-ECRAN.md`) | `api/suivi.py` : pièces jointes (242-319) · `api/comptes.py` : sauvegardes, état du serveur, restauration (492-fin) · `main.py` : `initialiser`, `demarrer_taches`, `vie`, `/api/sante`, service de l'écran (1-135, 188-fin) |
| **H** Écrans : textes, gestes, chiffres affichés, droits d'écran | tout `ecran/` (`src/**`, `public/*`), `docs/REGLES-ECRAN.md` | — |

Règles de travail en parallèle :

1. **Schéma de la base.** `modeles.py` et `db.py` appartiennent à G. Un domaine qui a besoin d'une colonne ou d'une contrainte la demande à G. G numérote les étapes de migration à la suite (15, 16…), dans l'ordre d'arrivée, et les livre en premier.
2. **Essais.** Chaque domaine écrit ses essais dans un fichier à lui : `tests/test_defauts_a.py` … `tests/test_defauts_h.py` pour le serveur, et `ecran/` pour H s'il ajoute vitest. Personne ne modifie l'essai d'un autre domaine, sauf pour supprimer un essai qui exerce une route supprimée (entrée A-12).
3. **Messages d'erreur.** Le serveur et l'écran gardent le même texte. Si H a besoin d'un nouveau champ dans une réponse (une raison, un auteur…), il le demande au domaine propriétaire de la route.
4. **Fusion.** Chaque domaine travaille sur sa branche. On fusionne dans cet ordre : G (schéma), F, C, A, B, D, E, puis H. `pytest` et `npm run controle` passent à chaque fusion.

## Les entrées, domaine par domaine

Format d'une entrée : **identifiant · titre** — gravité · verdict. Puis les sources, les fichiers et lignes à `b925e81`, la correction proposée et l'essai à écrire. À la fin de chaque domaine, un tableau donne ce qui n'est pas retenu (PAS UN DÉFAUT, PRO SEULEMENT), avec la raison.

### Domaine A — Achats, réceptions, fournisseurs, matières, échéancier, réclamations

Constat commun : le serveur ne traduit ni `IntegrityError` ni `DataError` (`main.py:177` ne traite que `RequestValidationError`). Une contrainte de base violée donne donc une **500**. Les entrées A-03, A-06 et A-12 en découlent. Le filet global est l'entrée **F-08**.

**A-01 · Une réception entièrement refusée ne s'annule pas, avec un message faux** — **gênant** · vérifié
Sources : API-A 12, RG-A I-01.
Fichiers : `api/receptions.py:581-601` (`annuler`, appel l. 592), `services/stock.py:249-251`.
Constat : l'annulation répond 409 « Ce document a déjà été annulé. ». La réception reste validée pour toujours, alors que l'écran propose « Annuler » (`DetailReception.tsx:730`).
Correction : si aucune ligne n'est acceptée ni sous réserve, ne pas contre-passer. Passer directement le statut à « annulee », avec le motif, puis `recaler_soldes` et le journal.
Essai : `test_une_reception_toute_refusee_s_annule` attend 200, le statut « annulee », aucun mouvement, et le bon de nouveau attendu.

**A-02 · Changer le rôle d'une matière qui est dans une recette casse la règle des 100 %, sans refus** — **bloquant** (faux besoins et faux coûts, contraire à F13) · vérifié
Sources : RG-A I-10.
Fichiers : `api/referentiels.py:623-648`, et l'import tableur (A-03).
Correction : si le rôle change et qu'une recette cite la matière, répondre 409 « « X » figure dans N recette(s) (rôle R) : la retirer des recettes avant de changer son rôle. ». Même contrôle dans l'import.
Essai : `test_le_role_d_une_matiere_en_recette_ne_change_pas`.

**A-03 · L'import tableur des matières passe l'aperçu puis tombe en 500, ou laisse passer des erreurs** — **bloquant** (outil de référentiel réel, perte de saisie, données fausses) · vérifié
Sources : API-B 14, RG-A I-12, ECR 7.9-7.12, ECR-T 10.
Fichiers : `api/suivi.py:734-835`.
Cas en **500** :
- une référence nouvelle en double dans le fichier ;
- un prix, un stock minimum, un poids de bobine, un nombre de bobines par palette, une contenance ou un minimum de commande négatif ;
- une densité négative sur une matière au mètre ;
- un texte plus long que la colonne (désignation > 160 caractères, code couleur > 32, groupe > 64, unité d'achat > 32).

Cas qui passent **en silence** :
- une couverture négative ;
- une densité négative avec un prix au kilo ;
- « nan » ;
- une faute de frappe dans « En service », qui désactive la matière ;
- une référence existante en double : la dernière ligne gagne.

Autres constats :
- la devise, le rôle, la classification et le code douanier sont comparés à la casse près ;
- une case vide ne vide pas le champ ;
- les messages sont bruts (« densite n'est pas un nombre », « devise inconnu … classification ») ;
- rien ne vérifie que la fiche n'a pas changé entre l'aperçu et l'application ;
- le fichier lu est la feuille active, et non la feuille « Matières ».

Correction :
- passer chaque ligne par les mêmes validations que la fiche (`ArticleEntree` et `_verifier_article`), y compris le refus de A-02 ;
- refuser les doublons avec « Ligne n : la référence X figure déjà ligne m. » ;
- borner les nombres (`ge=0`, `isfinite`) et les longueurs ;
- comparer les codes sans tenir compte de la casse ;
- écrire les libellés en français (« Densité : ce n'est pas un nombre », « Devise inconnue « usd » ») ;
- lire la feuille « Matières » ;
- renvoyer une empreinte à l'aperçu et la vérifier à l'application.

« Appliquer » reste grisé tant qu'il y a une erreur (décision F23). L'écran est dans **H-30**.
Essais : `test_l_import_refuse_une_reference_en_double_sans_500`, `test_l_import_refuse_un_prix_negatif_a_l_apercu`, `test_l_import_refuse_un_changement_de_role_en_recette`.

**A-04 · Une facture réglée, partagée ou portée par un dossier clos est réécrite par une réception** — **bloquant** (donnée comptable, période close) · vérifié
Sources : API-A 17, RG-A I-20.
Fichiers : `api/receptions.py:361-387` (`_facture`), `:614-662` (`completer_facture`).
Constat :
- `_facture` met à jour la date, le montant et l'échéance d'une facture existante sans regarder si elle est réglée, partagée avec une autre réception ou portée par un dossier, même clos ;
- l'échéance n'est pas recalculée ;
- `completer_facture` remplace tout (un montant 0 efface) et ne contrôle le dossier que si le numéro change.
Correction :
- `_facture` ne modifie jamais une facture existante : elle l'attache seulement ;
- dans `completer_facture`, refuser :
  - si la facture est réglée : « La facture N est réglée le … : annuler d'abord le règlement (Échéancier). » ;
  - si elle est portée par un dossier clos ou par d'autres réceptions : « … la corriger depuis le dossier après l'avoir rouvert. » ;
- appeler `cout_hors_periode_close` quand la date ou le montant change.
Essai : `test_une_reception_ne_reecrit_pas_une_facture_reglee`.

**A-05 · Les prix se confirment sur un brouillon, sur un bon soldé et sur un bon à approuver, sans garde-fou** — **gênant** (contraire à A8 et A12) · vérifié
Sources : API-A 14, RG-A I-06, ECR 4.8.
Fichiers : `api/achats.py:815`, `:832-833`, `:840-841`, `:271`, `:276`.
Constat :
- sur un brouillon, le cours se fige avant l'envoi ;
- sur un bon « à approuver » sans numéro, le bon ne revient pas en brouillon ;
- sur un bon soldé, rien n'est contrôlé ;
- une hausse de plus de 5 % ne repasse à la direction que si le seuil est aussi dépassé.
Correction :
- refuser sur un brouillon (409) : « Ce bon n'est pas encore parti : le fournisseur n'a pas pu confirmer ses prix. L'envoyer d'abord. » ;
- refuser sur un bon soldé (409) : « Ce bon est soldé : ses prix ne se confirment plus. Le rouvrir d'abord. » ;
- appeler toujours `_controler_montant`, ce qui ramène en brouillon un bon à approuver modifié.
Essais : `test_confirmer_les_prix_d_un_brouillon_est_refuse`, `test_un_prix_confirme_pendant_l_approbation_renvoie_en_brouillon`.

**A-06 · Un code de classification trop long donne une 500** — **gênant** · vérifié
Sources : DON 21, ECR 7.19.
Fichiers : `api/referentiels.py:185` (64 caractères admis) contre `modeles.py:174`, `:187` (32 caractères) et `:198` (48 caractères).
Correction : borner la longueur selon la table, avec le message « Le code fait au plus 32 caractères. ».
Essai : `test_un_code_de_composition_trop_long_est_refuse` attend 422.

**A-07 · La route du bon fournisseur en français, avec prix et conditions de paiement, reste ouverte** — **gênant** (contraire à A22) · vérifié
Sources : API-B 4, B 5, ECR 4.3, ECR-T 7, ESS § 17.
Fichiers : `api/exports.py:307-419`. Essais concernés : `tests/test_exports.py:91-122`, `tests/test_matieres_au_metre.py:289`.
Correction : supprimer la route. Réécrire les deux essais sur `/api/export/commandes/{cid}/bon`. Retirer « Livraison souhaitée ».
Essai : `test_le_bon_fournisseur_ne_dit_aucun_prix` (aucun « Prix » ni « Montant »), et l'ancienne route rend 404.

**A-08 · « Livraison prévue » ne se vide pas, alors que l'aide et les refus disent « la vider »** — **gênant** · vérifié
Sources : ECR 4.1, ECR-T 7.
Fichiers : `api/achats.py:619`, messages `:508-510` et `:703-705`. Côté écran, `DetailCommande.tsx:246`, qui envoie `null`.
Constat : un brouillon dont la date est passée reste bloqué.
Correction : si `date_livraison_prevue` est envoyé à `null` :
- bon non parti : la date est vidée ;
- bon parti : refus « La livraison promise d'un bon parti ne se vide pas : noter la nouvelle date dans l'ETA. ».
Essai : `test_vider_la_livraison_prevue_d_un_brouillon`.

**A-09 · Une réception de deux devises peut créer un brouillon en double** — **gênant** · vérifié
Sources : ECR 4.5, ECR-T 9.
Fichiers : `ecran/src/components/achats/SaisieReception.tsx:464-471`, qui fait une requête par devise.
Correction côté serveur (A) : `POST /receptions/par-devise` crée toutes les réceptions dans une seule transaction. L'écran (**H-20**) l'appelle.
Essai : `test_une_reception_en_deux_devises_s_enregistre_d_un_coup` : si la 2ᵉ devise est invalide, aucun brouillon n'est créé.

**A-10 · Une réclamation sur une ligne refusée perd sa référence** — **gênant** (le cas le plus courant, R20r) · vérifié
Sources : ECR 4.17.
Fichiers : `modeles.py:967-990` (pas de `reception_ligne_id`), `api/suivi.py:85-136`, `Reclamations.tsx:296`.
Correction :
- colonne `reclamation.reception_ligne_id`, à demander à G ;
- contrôler que la ligne appartient bien à la réception ;
- borner la quantité à la pesée de la ligne ;
- prendre la référence depuis la ligne.
Essai : `test_une_reclamation_sur_une_ligne_refusee_garde_sa_reference`.

**A-11 · Une matière, un fournisseur ou une valeur de classification désactivés restent utilisables** — **gênant** (contraire à A17 : « ce qui ne se consomme plus ne se rachète pas ») · vérifié
Sources : RG-A I-08 (achats), I-14.
Fichiers : `api/achats.py:434-460`, `api/receptions.py:390-400`, `:444-446`, `api/referentiels.py:574-579`.
Correction :
- commande : refuser une matière ou un fournisseur désactivé, avec « « X » est désactivée : la réactiver avant de la commander. » ;
- réception sur un bon : avertir seulement, le camion est là ;
- réception hors commande : refuser ;
- fiche matière : refuser une valeur désactivée si elle change.
Essais : `test_une_matiere_desactivee_ne_se_commande_pas`, `test_une_valeur_desactivee_ne_se_pose_pas_sur_une_matiere`.

**A-12 · Doublons de classification et de référence qui ne diffèrent que par la casse** — **mineur** · vérifié
Sources : RG-A I-13.
Fichiers : `api/referentiels.py:208`, `:229`, `:611`, `:636`.
Correction : comparer avec `lower()`, et refuser avec « « PP » existe déjà (« pp ») ».
Essai : `test_pp_et_PP_ne_coexistent_pas`.

**A-13 · Renommer un rôle de nomenclature est refusé à cause de poids à 0** — **mineur** (refus faux) · vérifié
Sources : API-A 26, DON 22, ECR 7.5, ECR-T 2.
Fichiers : `api/referentiels.py:146-149` contre `:72` et `:173-177`.
Correction : ne compter que les poids > 0, comme pour la suppression. Supprimer les lignes à 0, ou les reporter sur le nouveau code.
Essai : `test_un_role_aux_poids_nuls_se_renomme`.

**A-14 · L'alimentation reçoit la banque et les conditions de paiement des fournisseurs** — **mineur** (donnée inutile à l'atelier) · vérifié
Sources : API-A 2.
Fichiers : `api/referentiels.py:329-331`, `:344-348`.
Correction : pour l'alimentation, vider `banque`, `conditions_paiement`, `mode_paiement` et `delai_paiement_jours`.
Essai : `test_l_alimentation_ne_voit_pas_la_banque_du_fournisseur`.

**A-15 · Le prix confirmé passe au catalogue dans la mauvaise devise, sans journal** — **mineur** (cas rare, faux prix catalogue) · vérifié
Sources : RG-A I-07.
Fichiers : `api/achats.py:826-831`.
Correction : convertir le prix si la devise de la fiche diffère de celle du bon, ou refuser la mise à jour avec « La fiche de « X » est en EUR, ce bon en USD : le catalogue n'est pas mis à jour. ». Ajouter un journal « prix catalogue » sur la matière.
Essai : `test_le_prix_confirme_respecte_la_devise_de_la_fiche`.

**A-16 · Expédition : un jalon absent est effacé, et la route reste permise sur un bon annulé** — **mineur** · vérifié
Sources : API-A 16, RG-A I-18.
Fichiers : `api/achats.py:865-884`.
Correction :
- refuser sur un bon annulé : « Ce bon est annulé : son expédition ne se suit plus. » ;
- ne remplacer que les champs envoyés.
Essai : `test_l_expedition_d_un_bon_annule_est_refusee`.

**A-17 · L'indicateur « approbation requise » se trompe pour un bon parti ou soldé** — **mineur** · partiel (juste pour un brouillon, seul cas lu par l'écran)
Sources : RG-A I-19.
Fichiers : `api/achats.py:331`.
Correction : pour un bon parti, l'indicateur vaut `statut == "a_approuver"` ; pour un brouillon, la règle reste celle d'`envoyer`.
Essai : `test_un_bon_solde_n_annonce_pas_d_approbation`.

**A-18 · Le bon anglais garde des mots français ; l'Excel sans raison sociale imprime un texte français** — **mineur** · vérifié
Sources : API-A 25, ECR 4.11.
Fichiers : `api/achats.py:980` (« SIEGE SOCIAL »), `:1146` (« BANQUES »), `api/exports_achats.py:342`, `:346`, `:413`.
Correction :
- écrire « HEAD OFFICE » et « BANKS » ;
- sans raison sociale réglée, répondre 409 « La raison sociale de l'usine n'est pas réglée (Réglages › Paramètres › Société) : le bon ne part pas sans elle. » ;
- marquer « DRAFT » en filigrane sur un brouillon (l'écran est dans **H-21**).
Essai : `test_le_bon_anglais_ne_contient_pas_de_francais`.

**A-19 · Export des commandes : prix catalogue dans la devise de la fiche, colonne « Devise » du bon** — **mineur** (faux chiffre dans l'export) · vérifié
Sources : API-A 23.
Fichiers : `api/exports_achats.py:136-137`.
Correction : prix estimé = montant estimé ÷ quantité, dans la devise du bon.
Essai : `test_l_export_des_commandes_dit_le_prix_dans_la_devise_du_bon`, avec prix × quantité = montant.

**A-20 · Archive des pesées : la colonne « Annoncé BL » ne contient pas le BL** — **mineur** · vérifié
Sources : API-A 21, A 22, ECR 4.11.
Fichiers : `api/exports_achats.py:256`, `:262`, `depot.py:388` (domaine C, qui accepte la retouche).
Correction :
- renommer la colonne « Attendu : BL, sinon reste (kg) » et ajouter une colonne « BL (kg) » ;
- écrire « brouillon n° ID » plutôt que « REC-brouillon-ID ».
Essai : `test_l_archive_distingue_bl_et_attendu`.

**A-21 · Échéancier : l'échu change avec le filtre de dates ; règlement sans contrôle de période close ; cours inconnu compté 1** — **gênant** · vérifié
Sources : API-B 20, CAL-B 5 (pour l'échéancier), CAL-B 26, RG-B I52, ECR 8.21 (pour le serveur).
Fichiers : `api/suivi.py:330-392`, `:412-435`.
Constat : avec `du` = aujourd'hui, l'échu vaut 0. Un règlement peut être daté dans une période close.
Correction :
- calculer l'échu sur toutes les lignes, avant le filtre ;
- pour une devise sans cours, afficher « cours inconnu » au lieu de compter 1 ;
- dans `regler`, appeler `date_permise(s, e.payee_le)`.

La conversion au cours du jour des factures **dues** est gardée : c'est ce qu'elles coûteront à payer (voir « Non retenus »).
Essais : `test_l_echu_ne_depend_pas_du_filtre_de_dates`, `test_un_reglement_en_periode_close_est_refuse`.

**A-22 · Réclamations : issue changée sans réouverture, motif libre, refusées comptées dans « livré », nombres à l'anglaise** — **mineur** · vérifié
Sources : API-B 21, RG-B I50, RG-B I3.
Fichiers : `api/suivi.py:77`, `:116-120`, `:157-160`.
Correction :
- une réclamation close dont on change l'issue est refusée : « Cette réclamation est close : la rouvrir pour changer son issue. » ;
- le motif doit être dans la liste ;
- « livré » ne compte pas les lignes refusées ;
- écrire « 1 200,0 kg réclamés pour … kg livrés ».
Essai : `test_une_reclamation_close_ne_change_pas_d_issue`.

**A-23 · Deux définitions du « fournisseur local »** — **mineur** · vérifié
Sources : RG-A I-09.
Fichiers : `api/referentiels.py:332` contre `api/importations.py:109-113` (domaine B).
Correction : B expose une seule fonction `est_local(f)`, que `referentiels.py` importe.
Essai : `test_un_fournisseur_sans_pays_en_usd_n_est_local_nulle_part`.

**A-24 · Classification : journal « X → X » sans renommage, code non nettoyé dans le refus, désactivation d'une valeur portée sans avertissement** — **mineur** · vérifié
Sources : API-A 29, RG-A I-32.
Fichiers : `api/referentiels.py:218-234`.
Correction :
- n'écrire « ancien → nouveau » que s'il y a un vrai renommage ;
- utiliser `e.code.strip()` dans le refus ;
- répondre avec l'avertissement « « X » reste porté par N matière(s). ».
Essai : `test_modifier_une_valeur_sans_la_renommer_ne_journalise_pas_de_fleche`.

**A-25 · Supprimer un fournisseur : l'écran ne connaît pas tous les empêchements** — **mineur** · vérifié
Sources : ECR 7.4, ECR-T 2.
Fichiers : `api/referentiels.py:405-417`.
Correction : exposer les compteurs de lots, d'opérations et de factures dans `_comptes_fournisseurs`. L'écran les lit (**H-31**).
Essai : `test_le_fournisseur_dit_tout_ce_qui_empeche_sa_suppression`.

**A-26 · Le champ « priorité dans le groupe » ne sert à rien** — **mineur** (champ d'écran sans effet) · vérifié
Sources : CAL-A 21.
Fichiers : `modeles.py:306`, `depot.py:270`, `calcul/modele.py:196`. Le champ n'est lu nulle part dans le moteur.
Correction : retirer le champ de la fiche (**H-28**). Ne pas l'utiliser sans une décision.
Essai : aucun.

**A-27 · L'approbation numérote à la date du jour et oublie la date d'envoi saisie** — **mineur** · vérifié
Sources : API-A 15, RG-A I-05.
Fichiers : `api/achats.py:727`, `:503`.
Correction : `approuver` accepte une date d'envoi facultative, contrôlée par `date_permise`. Sans date, c'est le jour même : c'est ce jour-là que le bon approuvé part.
Essai : `test_l_approbation_date_le_bon_du_jour_d_envoi_saisi`.

**A-28 · Formats anglais dans les messages et le journal des réceptions** — **mineur** · vérifié
Sources : RG-A I-15.
Fichiers : `api/receptions.py:660` (journal « 1 234.50 »).
Correction : utiliser `nombre_fr` (`api/achats.py:939`). La partie « magasin » est dans **C-19**, la partie « réclamations » dans **A-22**.
Essai : `test_journal_facture_nombre_francais`.

**A-29 · Commentaire faux sur l'unité du prix de réception** — **mineur** (priorité basse) · vérifié
Sources : API-A 13, CTL 17.
Fichiers : `api/receptions.py:342-344`.
Correction : « Le prix payé, au kilo (un prix au mètre se ramène au kilo par la densité). »

**A-30 · DPO sur tout l'historique, bon soldé compté à sa quantité commandée ; retours d'un lot sans fournisseur comptés pour personne** — **mineur** (faux indicateur) · vérifié
Sources : CAL-B 12, B 22.
Fichiers : `calcul/moteur.py:2459-2474` (DPO, dans `cockpit`, partie E : le calcul est fait par **E-09**), `:2850` et `depot.py:639`, `:655` (taux de retours).
Correction :
- DPO : voir E-09 ;
- un retour fournisseur d'un lot sans fournisseur s'attribue au fournisseur de l'opération (`Operation.fournisseur_id`).
Essai : `test_retour_lot_d_ouverture_compte_pour_le_fournisseur_de_l_operation`.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| Format du lot interne : 4 chiffres dans le code, 5 dans le cahier (RG-A I-03, RG-B I75) | PAS UN DÉFAUT | Décision R17r (4 chiffres). Le cahier est à corriger (G). |
| Un même n° de lot fournisseur reçu deux fois fusionne (RG-A I-21) | PAS UN DÉFAUT | Voulu : un lot qui arrive en deux camions. |
| Conversion de l'échéancier au cours du jour (API-B 20, RG-B I52) | PAS UN DÉFAUT | Une dette en devise se paie au cours du jour de paiement : c'est la pratique de trésorerie. |
| Montant estimé d'une facture sans contrôle de devise (CAL-B 26) | PAS UN DÉFAUT | Non confirmé : la facture et ses lignes ont la même devise (contrôle à la saisie). |
| Clé In-Full (bc, référence) partagée (CAL-B 21) | PAS UN DÉFAUT | Non confirmé : une même référence ne peut pas être deux fois sur un bon (`achats.py:444`). |
| `ecart_pesee_moyen` sur toutes les réceptions (CAL-B 20) | PAS UN DÉFAUT | L'écart de pesée a du sens même pour une réception hors OTIF. |
| `LigneEntree.id` ignoré ; recalage des réceptions à la lecture (API-A 18, A 27) | PRO SEULEMENT | Sans effet visible. |
| Réceptions et factures fermées à l'alimentation (RG-B I22) | PAS UN DÉFAUT | Décision D5 (pas de prix chez l'alimentation), postérieure à D4. Le cahier est à mettre à jour (G). |
| « Tout valider » ignore les commandes et les réceptions (ECR 4.20) | PAS UN DÉFAUT | Un bon part par « Envoyer », une réception se valide après pesée. |
| `GET /api/factures` appelée seulement par les essais (API-A 28) | PAS UN DÉFAUT | — |
| Date confirmée par le fournisseur absente du volet Prix (ECR 4.7) | PAS UN DÉFAUT | La date promise se saisit dans la fiche du bon. |
| Changer la devise d'une matière qui a des bons ouverts (RG-A I-10, 2ᵉ partie) | PAS UN DÉFAUT | La devise appartient au prix de la matière (F1) ; les bons gardent la leur. |
| Empreinte facultative côté serveur ; plan d'une qualité sans verrou (RG-A I-16) | PRO SEULEMENT | L'écran envoie toujours l'empreinte ; PRO prévoit un champ `version`. |

### Domaine B — Importations, dossiers, frais

**B-01 · Un frais réglé se modifie, se retire ou se perd avec son dossier** — **bloquant** (trésorerie ; contraire à I20 : « un frais réglé ne redevient jamais dû ») · vérifié, plus grave que décrit
Sources : ECR 5.5, ECR-T 10.
Fichiers : `api/importations.py:991-1025` (modifier et retirer), `:1082-1093` (supprimer le dossier). L'annulation d'un règlement (`api/suivi.py:396`) est dans le domaine A et se corrige par **A-21**, en ne réservant l'annulation qu'à la direction, avec un motif.
Constat :
- le montant, le poste et la marchandise d'un frais réglé changent sans aucun contrôle ;
- le retrait d'un frais efface son règlement ;
- la suppression du dossier fait de même.
Correction :
- `modifier_charge` : 409 « Ce frais est réglé (le JJ/MM/AAAA) : son poste, son montant et sa marchandise ne changent plus. Un remboursement se saisit en avoir (montant négatif). » ;
- `retirer_charge` : 409 « Ce frais est réglé (le …) : il ne se retire pas. Saisir un avoir. » ;
- `supprimer` : refusé si un frais du dossier est réglé.
L'écran (**H-26**) grise ces gestes et affiche « réglé le ».
Essai : `test_frais_regle_ne_se_modifie_ni_ne_se_retire`. Après règlement, la modification et le retrait rendent 409, et le frais reste dans l'échéancier avec sa date de règlement.

**B-02 · Supprimer un dossier laisse un trou dans la série NN/AA** — **gênant** (contraire à M65) · vérifié
Sources : DON 11, RG-B I74.
Fichiers : `api/importations.py:560-570` (numéro automatique `numero(s,"DOS")`, sauf si on le saisit), `:1082-1093`.
Correction : un dossier **numéroté automatiquement** ne se supprime plus. Il se vide (« Détacher » chaque réception) et garde son numéro, avec la mention « sans marchandise ». C'est la pratique d'un registre de dossiers : un numéro de dossier ouvert chez le transitaire ne disparaît pas. La suppression reste permise pour un dossier dont le numéro a été saisi à la main.
Essai : `test_dossier_numerote_ne_se_supprime_pas`.

**B-03 · Dossier saisi à la main après la mise en service ; date d'arrivée modifiable en période close** — **mineur** (contraire à I3) · vérifié
Sources : RG-A I-26.
Fichiers : `api/importations.py:593-650`, `:766`.
Correction :
- la mise en service = la date de la première réception validée. Au-delà de cette date, une création sans facture est refusée avec « Un dossier saisi à la main est d'avant la mise en service (avant le JJ/MM/AAAA) : après, la marchandise entre par sa facture. » ;
- dans `modifier`, appeler `cout_hors_periode_close` quand la date d'arrivée change, car un lot créé à la main prend cette date comme date d'entrée.
Essai : `test_dossier_a_la_main_refuse_apres_mise_en_service`.

**B-04 · La TVA non répartie ne bloque pas la clôture** — **mineur** · vérifié
Sources : RG-A I-23, ECR 5.7.
Fichiers : `api/importations.py:1042-1044`.
Constat : seuls les frais hors TVA non répartis bloquent la clôture.
Correction : refuser aussi la clôture si `tva_non_repartie_mad` n'est pas nulle. Une TVA posée sur une marchandise retirée ne doit pas rester en l'air dans un dossier clos.
Essai : `test_cloture_refusee_tva_non_repartie`.

**B-05 · Le texte « TPI 0,25 % » est écrit en dur ; l'écart des droits n'est calculé qu'à l'écran** — **mineur** · vérifié
Sources : ECR 5.4.
Fichiers : `api/importations.py:298` (`dossier_dict`).
Correction :
- renvoyer `taux_tpi_import` ;
- calculer côté serveur `droits_ecart_mad` (`moteur.ecart_droits` : écart si plus de 2 % et au moins 50 MAD, décision I11), que l'écran lit (**H-26**).
Essai : `test_droits_ecart_calcule_au_serveur`.

**B-06 · Le second camion d'un fournisseur marocain est introuvable depuis son dossier** — **mineur** · partiel
Sources : ECR 5.10.
Fichiers : `api/importations.py:457-462` (`a_rattacher`).
Correction : ne pas écarter une ligne locale dont la facture a déjà un dossier.
Essai : `test_second_camion_local_visible_pour_son_dossier`.

**B-07 · L'échéancier du dossier perd la facture marchandise quand toutes ses réceptions sont détachées** — **mineur** · partiel (l'échéancier général la garde)
Sources : ECR 5.19.
Fichiers : `api/importations.py:240-241`, `:354`.
Correction : `if d.facture: factures_objets.setdefault(d.facture.id, d.facture)`.
Essai : `test_echeancier_dossier_garde_sa_facture_apres_detachement`.

**B-08 · Rouvrir un dossier laisse les cours du jour figés à la clôture, comme s'ils avaient été saisis** — **mineur** · vérifié
Sources : RG-A I-25.
Fichiers : `api/importations.py:1054-1079`.
Correction : marquer d'office à la clôture les lignes dont le cours a été figé (colonne demandée à G). À la réouverture, remettre ces cours à 0 et l'écrire au journal (« cours du jour figé à la clôture retiré »), pour que l'avertissement « cours vides » revienne.
Essai : `test_rouvrir_signale_cours_figes`.

**B-09 · Export des dossiers : titre « closs », libellé « figée à la clôture », statut écrit en deux casses** — **mineur** · vérifié
Sources : API-A 8, A 9, A 20, ECR 5.14.
Fichiers : `api/importations.py:1123`, `:1143`, `api/analyse_import.py:92`, `:160`.
Correction :
- titres « — ouverts » et « — clos » ;
- libellé « figée (clé d'avant son changement) » ;
- `statut` contrôlé par un motif, sans tenir compte de la casse (une valeur inconnue rend 422).
Essais : `test_export_dossiers_titre_clos`, `test_analyse_statut_insensible_a_la_casse`.

**B-10 · Le message « Code douanier inconnu » renvoie les achats vers un écran de la direction** — **mineur** · vérifié
Sources : API-A 3, ECR 7.15, ECR-T 4.
Fichiers : `api/referentiels.py:603-604`. Ce fichier appartient à A : B fournit le texte, A le pose.
Correction : « Code douanier inconnu : « X ». La direction l'ajoute (Réglages › Codes douaniers) ; en attendant, laisser le code vide. »
Essai : `test_code_douanier_inconnu_message`.

**B-11 · Le dossier repris est confondu avec un dossier saisi à la main** — **mineur** · vérifié
Sources : ECR 5.11.
Fichiers : `api/importations.py:293` (`a_la_main` est vrai pour un dossier repris).
Correction : renvoyer `repris` à part, pour que l'écran ne propose pas une saisie à la main que le serveur refuse ensuite (l. 734).
Essai : `test_dossier_repris_n_est_pas_a_la_main`.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| `GET /qualites/facteurs-cout` réservé aux achats (API-A 3) | PAS UN DÉFAUT | Non confirmé : la page Qualités est fermée à l'alimentation. |
| Ligne sans cours au cours du jour tant que le dossier est ouvert (CAL-B 5) | PAS UN DÉFAUT | I13 et I14 : provisoire jusqu'à la clôture. Le vrai trou (période close) est **E-02**. |
| Frais perdus quand la clé de répartition a une base nulle (CAL-B 25) | PAS UN DÉFAUT | Montrés « non répartis » (I15), et la clôture est refusée (I14). |
| Postes récupérables mêlés (CAL-B 23) | PAS UN DÉFAUT | Cas théorique : le référentiel donne une valeur par poste. |
| `dossier_ligne.poids_kg` colonne morte (DON 13, RG-A I-24, CAL-B 24) | PRO SEULEMENT | Égale à la quantité depuis l'étape 14. Le commentaire de `LigneRevient.poids_kg`, qui parle de mètres, est à corriger (priorité basse). |
| `PUT /dossiers` ignore numéro et facture (API-A 19) | PRO SEULEMENT | Sans effet visible. |
| Pièces jointes d'un dossier clos modifiables (ECR 5.20) | PAS UN DÉFAUT | Décision I21. |
| Dates ISO texte dans les exports (API-A 10) | PRO SEULEMENT | Convention d'export commune à revoir dans PRO. Les dates de l'analyse sont traitées par **E-15**. |

### Domaine C — Stock, opérations, inventaires, valorisation, numérotation

**C-01 · L'alimentation peut sortir de la matière de quarantaine sans les achats** — **bloquant** · vérifié, plus grave que les inventaires ne le disent
Sources : RG-B I14.
Fichiers : `api/operations.py:381-392` (`supprimer`), `:445-457` (`annuler`). `_autorise` ne regarde que le type, et `QUI["transfert"]` inclut l'alimentation.
Constat : l'alimentation reçoit un 403 si elle veut libérer. Mais elle peut :
- **annuler une mise en quarantaine validée**, ce qui remet la matière en stock disponible ;
- supprimer un brouillon de libération préparé par les achats ;
- annuler une libération validée.
Cela contourne la décision D6 : « libérer est une décision des achats ».
Correction : écrire `_touche_quarantaine(s, o)`, vrai si une ligne a pour source ou pour destination un magasin de type Quarantaine. Dans `supprimer` et dans `annuler` :
- vérifier `if _touche_quarantaine(s, o) and qui.role not in (ACHATS, DIRECTION)` ;
- si c'est le cas, lever une 403 avec le message « Une opération qui entre en quarantaine ou en sort se supprime ou s'annule par les achats. ».
Essai : `test_alimentation_ne_peut_annuler_une_mise_en_quarantaine` vérifie la 403 et que le solde de quarantaine ne bouge pas. `test_alimentation_ne_supprime_pas_une_liberation_des_achats` vérifie la même chose pour la suppression.

**C-02 · Une entrée à prix 0 est valorisée au prix du catalogue** — **bloquant** (faux CMUP) · vérifié
Sources : CAL-B 3, RG-B I16.
Fichiers : `calcul/moteur.py:1872-1876` (`cout_d_entree` : `if mouvement.prix_unite:`).
Constat : une ouverture saisie à 0 entre au prix `article.prix_kg × cours` au lieu de 0. C'est aussi le cas d'une réception à 0, ce qui est permis par `api/receptions.py:345`. C'est contraire à V2 : « un coût nul est un coût ».
Correction : ne retomber sur le catalogue que si le prix est **inconnu** (`None`). Un prix 0 saisi est un coût de 0.
Essai : `test_ouverture_a_prix_zero_entre_a_zero` vérifie `couts_du_journal(d).cmup()[ref] == 0`.

**C-03 · L'outil « vider l'activité » est cassé** — voir **G-01**, qui possède `outils/` (vérifié ici).

**C-04 · Un inventaire au périmètre vide s'ouvre et gèle le magasin** — **gênant** · vérifié, plus grave que décrit
Sources : RG-B I10.
Fichiers : `api/inventaires.py:308-316`.
Constat : rien n'empêche d'ouvrir un inventaire qui ne contient aucun lot. Il ne pourra jamais être validé (« Aucun lot compté »). Pendant ce temps, il suspend tous les mouvements du magasin, ou de **tous** les magasins s'il est global.
Correction : après le figeage, si `not i.lignes`, lever une 409 avec le message « Aucun lot en stock dans ce périmètre : rien à compter, l'inventaire n'est pas ouvert. ».
Essai : `test_inventaire_perimetre_vide_refuse` vérifie la 409 et qu'aucun inventaire n'est créé.

**C-05 · Abandonner un inventaire laisse un trou dans la série INV** — **gênant** (contraire à M65) · vérifié
Sources : DON 11, RG-B I30, I74.
Fichiers : `api/inventaires.py:304` (numéro donné à l'ouverture, conforme à A10), `:418-430` (`abandonner` fait `s.delete(i)`).
Correction : ne plus supprimer l'inventaire. On garde la ligne avec le statut « abandonne » (demander à G d'étendre la contrainte de statut), on vide ses lignes, et on écrit au journal. Le numéro reste dans la série, ce qui suit la pratique d'un registre. Les listes affichent « Abandonné ».
Essai : `test_abandon_inventaire_ne_laisse_pas_de_trou`. On ouvre puis on abandonne INV-1, on ouvre INV-2 : INV-1 est toujours listé avec le statut « abandonne ».

**C-06 · Un lot « trouvé » en inventaire est créé dès la saisie et reste après un abandon** — **mineur** · vérifié
Sources : API-B 15, RG-B I31, ECR 6.19.
Fichiers : `api/inventaires.py:369` (`stock.lot_ou_creer`).
Constat : la fiche du lot existe dès la saisie et survit à un abandon. Elle survit aussi à une faute de frappe sur le numéro.
Correction : à l'abandon, et quand on retire la ligne, supprimer les lots créés par ce comptage qui n'ont aucun mouvement, aucun solde et aucun autre usage.
Essai : `test_lot_trouve_disparait_si_inventaire_abandonne`.

**C-07 · Le refus « déjà ouvert sur ce magasin » est faux quand le conflit vient d'un inventaire global** — **mineur** · vérifié
Sources : RG-B I33.
Fichiers : `api/inventaires.py:274-281`.
Correction : le message dépend du conflit.
- Si le conflit est un inventaire global : « L'inventaire INV-… est déjà ouvert sur tous les magasins. »
- Sinon : « … est déjà ouvert sur « CODE ». »
Essai : `test_conflit_inventaire_global_message`.

**C-08 · Deux postes qui comptent en même temps peuvent effacer un recomptage** — **mineur** · partiel
Sources : API-B 15, RG-B I32.
Fichiers : `api/inventaires.py:349-359`.
Constat : un champ absent du corps efface la valeur enregistrée, sauf `second_compte`. L'écran renvoie tous les champs, donc il n'y a pas de bug seul. Mais quand deux postes comptent ensemble, l'écran renvoie un `second_compte` périmé et écrase le recomptage de l'autre personne.
Correction : n'appliquer que les champs envoyés (`c.model_fields_set`).
Essai : `test_comptage_partiel_ne_efface_pas_la_justification`.

**C-09 · Motifs d'opération hors de la liste acceptés** — **mineur** (un contrôle rattrape ce que la saisie devrait refuser) · vérifié
Sources : RG-B I11, CTL 26, DON 31.
Fichiers : `api/operations.py:253-254`, `:49-53`.
Constat : un retour « Reliquat » est accepté, puis le contrôle C03 le signale.
Correction : si le type d'opération a une liste de motifs, refuser un motif absent de la liste avec le message « Motif inconnu pour « {type} » : choisir dans la liste. ». Le motif d'un transfert reste libre ou vide.
Essai : `test_motif_hors_liste_refuse`.

**C-10 · Retour fournisseur d'un lot sans fournisseur** — **mineur** · vérifié
Sources : RG-B I17.
Fichiers : `api/operations.py:319-332`.
Constat : un lot sans fournisseur compte comme un fournisseur « None ». On obtient un faux refus « deux fournisseurs », ou une opération dont le fournisseur est NULL.
Correction :
- prendre `lot.fournisseur_id or lot.article.fournisseur_id` ;
- si on ne trouve toujours rien, refuser avec le message « Le lot {n} n'a pas de fournisseur connu : on ne sait pas à qui le rendre. ».
Essai : `test_retour_fournisseur_lot_sans_fournisseur`.

**C-11 · Valider une opération annulée répond « déjà validée »** — **mineur** · vérifié
Sources : RG-B I13, ECR 3.10.
Fichiers : `api/operations.py:400-401`. La partie « ordre » est dans **D-09**.
Correction : si le statut est « annulee », répondre « Cette opération est annulée : elle ne se valide plus. ».
Essai : `test_valider_operation_annulee_message`.

**C-12 · Blocage « magasin désactivé » annoncé à tort pour un ajustement négatif** — **mineur** · vérifié
Sources : RG-B I12.
Fichiers : `api/operations.py:124-128` contre `services/stock.py:152`.
Correction : ne pas annoncer le blocage pour un ajustement de quantité négative. Un magasin désactivé détient au plus de la poussière.
Essai : `test_ajustement_negatif_magasin_desactive_sans_blocage`.

**C-13 · Liste des opérations coupée à 1 000 sans le dire** — **mineur** · vérifié
Sources : API-B 19, RG-B I20, ECR 6.14.
Fichiers : `api/operations.py:216`. L’écran est dans **H-33**.
Constat : en plus, `?operation=ID` n'ouvre rien, en silence, pour une opération plus ancienne que les 1 000 listées.
Correction : renvoyer `tronque: true` comme le fait `/mouvements`, et ajouter `GET /operations/{id}`.
Essai : `test_operations_signale_troncature`.

**C-14 · Recherche des mouvements et des soldes : `%` et `_` non échappés, accents non ignorés** — **mineur** (contraire à E5 : chercher sans accents) · vérifié
Sources : RG-B I23, ECR 2.20, 3.18.
Fichiers : `api/stock.py:125-130`, `:225-229`.
Correction :
- reprendre l'échappement de `api/comptes.py:228-235` ;
- comparer sans accents, avec `func.unaccent` des deux côtés. L'extension `unaccent` est à installer par G. Faute de mieux, utiliser `translate()`.
Essai : `test_recherche_mouvements_sans_accents_et_pourcent` : « frise » trouve « frisé », et « % » ne ramène rien.

**C-15 · Vue à une date passée : statut et commandé des bons faux** — **mineur** · vérifié (a, b, d)
Sources : CAL-A 9.
Fichiers : `calcul/moteur.py:135-170` (`a_la_date`).
Trois défauts :
- (a) un bon livré après la date repasse « Confirmée » même s'il était « Envoyée » ;
- (b) un bon soldé à la main, ou annulé, **après** la date paraît déjà clos à cette date, donc le commandé du passé est sous-estimé ;
- (d) le retour au prorata n'est pas plafonné, contrairement à `depot._au_prorata`.
Correction :
- (a) recalculer le statut comme `depot.py:39` ;
- (b) demander à G les colonnes `commande.soldee_le` et `annulee_le`, les remplir dans `api/achats.py` (coordination avec A), puis les relire ici ;
- (d) plafonner avec `min(q, …)`.
Essai : `test_a_la_date_commande_soldee_apres_reste_due`, `test_a_la_date_retour_plafonne`.

**C-16 · Le compteur des lots internes peut sauter** — **mineur** · vérifié (peu probable)
Sources : DON 33.
Fichiers : `api/receptions.py:55-64`. Ce fichier appartient à A : C écrit la correction, A la relit.
Constat : le rattrapage du compteur cherche `LIKE 'LOT-AAAA-%'` sur tous les lots, y compris ceux des fournisseurs.
Correction : ne rattraper que les numéros de la forme exacte `LOT-\d{4}-\d{4}` qui sont internes, c'est-à-dire sans fournisseur ou repris.
Essai : `test_lot_fournisseur_forme_lot_ne_decale_pas_la_serie`.

**C-17 · « Tout valider » : ordres ignorés en silence, lien inaccessible** — **mineur** · vérifié
Sources : API-A 4, ECR 2.13, 6.1.
Fichiers : `api/brouillons.py:30-35`, `:67-79`, `:102-121`. L’écran est dans **H-23**.
Deux défauts :
- un compte achats qui appelle `POST /brouillons/valider` voit ses ordres de fabrication écartés sans le savoir ;
- l'alimentation reçoit des liens `/operations?…` alors que cet écran lui est fermé.
Correction :
- renvoyer `non_permis`, la liste des brouillons que ce rôle ne peut pas valider, avec la raison ;
- calculer `lien` selon le rôle. Pour l'alimentation, mener à l'écran de l'atelier où elle saisit ses transferts et ses retours.
Essai : `test_tout_valider_achats_signale_ordres_non_permis`, `test_liens_a_valider_selon_le_role`.

**C-18 · Étiquettes : identifiants inconnus ignorés, 404 en JSON brut** — **mineur** · vérifié
Sources : ECR 3.28.
Fichiers : `api/stock.py:367-383`, `:397-398`.
Correction :
- lister en tête de la page les identifiants ignorés ;
- renvoyer une page HTML « Aucun lot à étiqueter. » au lieu d'un JSON brut ;
- quand le lot est en partie en quarantaine, imprimer « dont X kg en quarantaine ».
Essai : `test_etiquettes_id_inconnu_signale`.

**C-19 · Refus de désactivation d'un magasin écrit à l'anglaise (« 1,234 kg »)** — **mineur** · vérifié
Sources : RG-A I-15, ECR 8.14.
Fichiers : `api/referentiels.py:1095-1096` (`{detenu:,.0f}`).
Correction : utiliser `stock.kg(detenu, 0)`.
Essai : `test_desactivation_magasin_message_format_francais` attend « 1 288 kg ».

**C-20 · Un inventaire validé ne s'annule pas** — **mineur** · vérifié
Sources : RG-B I34.
Fichiers : `api/inventaires.py:401-425`.
Constat : ses ajustements sont des mouvements `document="inventaire"`, que `contrepasser_document` sait déjà défaire. C'est contraire à U19 : tout document validé s'annule par contre-passation, une fois, avec un motif.
Correction : ajouter `POST /inventaires/{iid}/annuler` (achats et direction, motif obligatoire), qui contre-passe ses ajustements, passe l'inventaire au statut « annule » et refuse si la période est close.
Essai : `test_annuler_inventaire_valide_remet_les_soldes`.

**C-21 · Commentaires faux sur la valeur du stock et sur la contre-passation** — **mineur** (priorité basse) · vérifié
Sources : API-B 7, CAL-B 7, DON 30.
Fichiers :
- `calcul/moteur.py:1792`, `:1795` : ils disent « les magasins seuls », alors que le code compte magasin + machine ;
- `modeles.py:10`, `:760-761` : « libération » y est citée comme une opération (ce fichier appartient à G, qui fait la correction) ;
- `services/stock.py:252` : « Les entrées d'abord en dernier ».
Correction :
- dans `moteur.py` : « magasins (quarantaine comprise) + machine » ;
- dans `services/stock.py` : « On défait d'abord les sorties (la matière revient), puis les entrées : le solde ne passe jamais sous zéro. »
Essai : aucun.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| Réponses d'écriture des opérations non masquées (API-B 2, RG-B I19) | PAS UN DÉFAUT | Non confirmé : l'alimentation n'écrit que des transferts et des retours, à prix forcé à 0 (`operations.py:326`). Le filtre générique est l'affaire de PRO. |
| `disponibles` ne retire pas les magasins désactivés (RG-B I18) | PAS UN DÉFAUT | Non confirmé : désactiver un magasin qui détient de la matière est refusé, et les entrées dans un magasin désactivé aussi. |
| Jambe de transfert orpheline ignorée (CAL-A 23, CTL 10) | PAS UN DÉFAUT | Non confirmé : l'application écrit toujours les deux jambes ensemble. Le vérificateur peut l'ajouter (G). |
| Cours d'une ouverture en devise = celui du jour de validation (RG-B I16) | PAS UN DÉFAUT | Décision V8 : pas de cours datés. |
| Recalage des bons lancé pour tout transfert depuis la quarantaine (RG-B I15) | PAS UN DÉFAUT | Le recalage ne change rien quand il n'y a rien à recaler. |
| Deux définitions de l'entrée d'un lot ; contrôle par jour (RG-B I4, CAL-A 25) | PAS UN DÉFAUT | Les dates n'ont pas d'heure : le jour est la bonne granularité. |
| Écriture antidatée sans limite en jours (RG-B I5) | PAS UN DÉFAUT | Décision U18 : ni futur, ni avant 2000, ni période close. |
| Inventaire qui suspend tout le magasin (RG-B I10, DEC N3, § 16.2) | PRO SEULEMENT | Non retenu le 8 octobre (N3) ; le périmètre en base est prévu dans PRO. |
| Recomptage « à quatre yeux » seulement signalé (ECR 6.7, RG-B I34) | PAS UN DÉFAUT | Conforme à N1 (« signalé ») ; une seule personne aux achats. |
| Cadences du tournant en dur ; soldes figés `> 0` (RG-B I35, I36) | PRO SEULEMENT | Sans effet visible. |
| Valorisation qui multiplie le stock du journal par le CMUP après une sortie au-delà du stock (CAL-B 29) | PAS UN DÉFAUT | Le stock d'un lot ne passe jamais sous zéro (U16, U17, C37). |
| Deux vocabulaires de mouvements ; `/api/lots` et `/api/soldes` (API-B 6) | PRO SEULEMENT | L'écran traduit les codes (`Tracabilite.tsx:80-88`) ; rien de visible. |
| Numéro donné à l'ouverture des réclamations (DON 11) | PAS UN DÉFAUT | Aucune route ne supprime une réclamation : pas de trou. |

### Domaine D — Production, atelier, recettes, métiers, plan, besoins et plan d'achat

**D-01 · Un « NaN » dans le plan ou dans un poids au m² fait tomber tous les calculs en 500** — **bloquant** · vérifié, plus grave que décrit
Sources : API-B 22 (les coefficients sont contrôlés dans le code et pas dans le modèle).
Fichiers : `api/production_plan.py:148-149`, `:171`, `api/referentiels.py:842`, `:865`, `:1030-1031`, `:1040`.
Constat :
- « NaN » passe Pydantic, puis le test `c < 0 or c > 20`, puis le CHECK SQL (`'NaN' >= 0` est vrai en PostgreSQL) ;
- ensuite `arrondi()` lève une erreur : le stock, les besoins, le plan d'achat, le cockpit et le plan de production rendent tous une 500.
Correction :
- contraintes dans les modèles : `Field(ge=0, le=20, allow_inf_nan=False)` pour les coefficients, `Field(ge=0, allow_inf_nan=False)` pour les poids ;
- CHECK `<> 'NaN'`, à demander à G ;
- en même temps, refuser un plan sur une qualité arrêtée.
Essai : `test_plan_refuse_nan`. Le PUT rend 422, puis `GET /stock` rend 200. Faire de même pour un poids.

**D-02 · La matière reçue « sous réserve » est proposée au rachat alors que son bon n'est pas soldé** — **bloquant** (faux plan d'achat, double commande possible ; contraire à R11r) · vérifié
Sources : CAL-A 5.
Fichiers : `depot.py:358` (`quantite_recue = recu`, quarantaine comprise ; ce fichier appartient à C, D écrit la correction et C la relit), `calcul/moteur.py:997-1000`, `:1154-1157`.
Constat : la quarantaine est retirée du projeté (U9), et en même temps le reste à livrer baisse. La matière n'est donc ni en stock ni attendue.
Correction : `quantite_recue = recu − en_quarantaine_par_ligne(s)[ligne]`. Tant qu'elle n'est pas libérée, la ligne reste attendue. Si la matière est refusée puis renvoyée, le reste à livrer reste dû.
Essai : `test_quarantaine_ne_declenche_pas_rachat`. Pour 1 000 kg sous réserve sur un bon de 1 000 kg, la quantité à commander ne change pas et `bc_en_cours` vaut 1 000.

**D-03 · Renommer une matière casse les versions de recette, le prévu figé des ordres et le coefficient de réalisation** — **bloquant** (faux besoins) · vérifié, plus grave que décrit
Sources : DON 18.
Fichiers : `api/referentiels.py:640-646` (matières, partie A : le correctif se fait à deux, A pour la route, D pour les JSON), `calcul/moteur.py:335-340`, `:3383-3385`, `api/referentiels.py:1013-1016`.
Constat : `recette_version.contenu` et `bon_sortie.theorique` désignent les matières par leur **référence**. Après un renommage :
- le prévu passé du fil vaut 0 ;
- il n'a plus de coefficient de réalisation ;
- les ordres passés montrent un « hors recette » et un « manquant » ;
- « Revenir à cette version » est refusé.
Correction : dans la même transaction que le renommage, réécrire les clés des deux JSON (`recette_version.contenu`, `bon_sortie.theorique`) et le journal du plan si besoin. À terme, PRO stocke `article_id`.
Essai : `test_renommer_matiere_garde_ecart_des_ordres`. L'écart de l'ordre est identique avant et après, et le coefficient n'est pas `None`.

**D-04 · Versions de recette créées sans changement réel** — **gênant** (fausse l'historique signé F14 et les mois « stables » du coefficient) · vérifié (autre cause que celle décrite)
Sources : RG-A I-27, RG-B I53.
Fichiers : `api/suivi.py:441-476`, `api/referentiels.py:867-870`, `:982-984`.
Constat : modifier le nom ou l'état d'une qualité, ou enregistrer une recette identique, crée une version.
Correction : comparer le contenu et les poids à la dernière version avant d'en ajouter une.
Essai : `test_recette_identique_ne_cree_pas_de_version`.

**D-05 · La fiche qualité accepte un rôle pesant sans matière ; son avertissement n'est pas affiché** — **gênant** (crée l'état que la recette interdit, F13) · vérifié
Sources : RG-A I-11, ECR 7.6, ECR 7.7, ECR-T 2.
Fichiers : `api/referentiels.py:893-899` contre `:973-981`.
Correction : refuser côté fiche avec le même message que la recette, pour une qualité active. Pour une qualité arrêtée, accepter la fiche et la recette avec un avertissement, puisqu'elle ne part plus dans un ordre (O6). L'écran affiche l'avertissement (**H-29**).
Essai : `test_fiche_poids_sans_matiere_refusee`, `test_recette_qualite_arretee_acceptee_avec_avertissement`.

**D-06 · Poids de bobine d'un fil monté pris sur une sortie annulée** — **gênant** (faux stock en machine) · vérifié
Sources : CAL-A 24.
Fichiers : `depot.py:133-149`, `:509-511` (fichier de C, correctif écrit par D).
Correction : exclure les mouvements contre-passés, et leurs contre-passations, de `poids_bobine_mesures`.
Essai : `test_poids_bobine_ignore_sortie_annulee`.

**D-07 · Les ordres d'avant l'étape 9 n'ont pas de prévu figé : un réglage de perte réécrit leur écart** — **gênant** (contraire à O5) · vérifié
Sources : CAL-B 19.
Fichiers : `api/production.py:71-72`, `calcul/moteur.py:3418`, `db.py:167-193`.
Correction : étape de migration (G) qui fige `theorique` et le taux de perte de ces ordres une fois pour toutes. On prend la recette de `valide_le` et le taux relu dans l'historique des réglages, sinon le taux courant. Avant cela, mesurer en production combien d'ordres sont concernés : `SELECT count(*) FROM bon_sortie WHERE statut='valide' AND theorique IS NULL`.
Essai : `test_changer_taux_perte_ne_reecrit_pas_ordre_ancien`.

**D-08 · Bobines et palettes fractionnaires acceptées** — **mineur** (contraire à U20 : « une bobine se compte entière ») · vérifié
Sources : RG-B I42.
Fichiers : `api/production.py:50-62`, `:243`. Côté réceptions, opérations et inventaires : `api/receptions.py:337-338` (A), `api/operations.py:233`, `:283` (C), `api/inventaires.py:328-329` (C). Chaque domaine pose le même contrôle.
Correction : dans `en_unite_de_stock`, refuser avec « Une bobine se compte entière : 2 ou 3, pas 2,5. ».
Essai : `test_sortie_refuse_bobine_fractionnaire`.

**D-09 · Messages de production : « bon » au lieu d'« ordre », ordre annulé dit « déjà validé », nombres à l'anglaise** — **mineur** · vérifié
Sources : ECR 3.5, ECR-T 5, RG-B I3, I13.
Fichiers : `api/production.py:303`, `:452`, `:461`, `:473`, `:500-501`, `:519`, `:562`, `:587` ; formats `:444`, `:528`.
Correction :
- écrire « ordre » ;
- pour un ordre annulé : « Cet ordre est annulé : il ne se valide plus. » ;
- utiliser `stock.kg(...)`.
Essai : `test_messages_ordre_en_francais`.

**D-10 · L'annulation d'un ordre laisse ses brouillons de retour, qu'on ne peut plus valider** — **mineur** · vérifié
Sources : API-B 13, RG-B I44.
Fichiers : `api/production.py:565-566`. Le message de blocage est dans `api/operations.py:129-137` (C).
Correction : `annuler_bon` supprime les brouillons de retour rattachés et l'écrit au journal.
Essai : `test_annuler_ordre_retire_brouillon_de_retour`.

**D-11 · La proposition de sortie ne contrôle ni le magasin ni la date ; `magasin_id=0` propose les lots de tous les magasins** — **mineur** · vérifié
Sources : RG-B I41.
Fichiers : `api/production.py:190-237`, `services/stock.py:287` (C, qui remplace le test par `if magasin_id is not None`).
Correction : reprendre en tête de `proposition` les contrôles de `_remplir` (magasin connu, hors quarantaine) et `date_permise`.
Essai : `test_proposition_refuse_magasin_quarantaine_et_date_future`.

**D-12 · Montage accepté sur un métier arrêté, ou avec une matière désactivée : le fil « disparaît » du stock** — **mineur** · vérifié
Sources : RG-A I-08 (montage).
Fichiers : `api/referentiels.py:1343-1368`.
Correction : refuser avec « Le métier X est arrêté : le remettre en service avant d'y monter du fil. ».
Essai : `test_montage_refuse_metier_arrete`.

**D-13 · Signalements : un article inconnu donne une 500 ; un signalement déjà traité peut être retraité** — **mineur** · vérifié
Sources : RG-B I2, I54.
Fichiers : `api/suivi.py:198-207`, `:214-223`.
Correction :
- article inconnu : 404 ;
- signalement déjà traité : 409 « Ce signalement a déjà été traité le … ».
Essais : `test_signalement_article_inconnu_404`, `test_signalement_deja_traite_409`.

**D-14 · Prévision : mois comptés à 30 jours fixes ; fenêtre à 0 qui retombe sur la règle du classeur ; rupture jugée sans le stock en machine** — **mineur** (faux besoins aux bords) · vérifié (a, d, f), partiel (b)
Sources : CAL-A 3, 6, 7, 8, 15.
Fichiers : `calcul/moteur.py:852`, `:604-620`, `:1047`, `:1110-1119`, `:1138`, `:1148`.
Correction :
- (a) jours restants = jusqu'à la vraie fin du mois, prorata sur sa longueur ;
- (d) fenêtre nulle : consommation = besoin annuel ÷ 12, sans `max(historique, …)` ;
- (f) rupture jugée sur le stock disponible plus le stock en machine (U8) ;
- (b) prolonger la courbe au-delà de 12 mois ;
- (c) `int(delai)` remplacé par l'arrondi au jour supérieur.
Essais : `test_jours_restants_fevrier`, `test_fenetre_zero_ne_prend_pas_le_max_historique`, `test_coefficient_baisse_si_fil_en_machine`, `test_conso_horizon_delai_long_non_dilue`.

**D-15 · Délai d'un fournisseur inconnu : 0 dans le groupe du plan d'achat, délai par défaut sur la ligne** — **mineur** · vérifié
Sources : CAL-A 17.
Fichiers : `calcul/moteur.py:1745`, `calcul/modele.py:741-750`.
Correction : `delai_jours=donnees.delai_fournisseur(nom)`.
Essai : `test_groupe_fournisseur_inconnu_delai_defaut`.

**D-16 · XYZ : une demande parfaitement régulière est classée « — » au lieu de X** — **mineur** · vérifié
Sources : CAL-A 16.
Fichiers : `calcul/moteur.py:1454-1455`.
Correction : « — » seulement quand la moyenne est nulle.
Essai : `test_xyz_serie_constante_est_X`.

**D-17 · Plan de production : `total_annuel` ignore la croissance et l'arrêt ; `hors_plan` toujours vide** — **mineur** · vérifié
Sources : CAL-B 27.
Fichiers : `api/production_plan.py:100`, `:126`, `:142`.
Correction :
- appliquer la croissance et l'arrêt, ou libeller « hors croissance » ;
- `hors_plan` = les qualités tissées dont le plan est à 0.
Essai : `test_tisse_hors_plan_qualite_base_zero`.

**D-18 · Une qualité créée n'a pas de version de recette avant son premier enregistrement** — **mineur** · vérifié
Sources : RG-A I-17.
Fichiers : `api/referentiels.py:846-857`, `api/suivi.py:447-451`.
Correction : créer la version après le flush, dans `creer_qualite`.
Essai : `test_creation_qualite_cree_version`.

**D-19 · Export des qualités : la colonne « Fabriquée » contient l'état « actif »** — **mineur** · vérifié
Sources : API-A 24.
Fichiers : `api/referentiels.py:1526`, `:1532`.
Correction : renommer la colonne « En service ».
Essai : `test_export_qualites_entete_en_service`.

**D-20 · Commentaires faux (tri du plan d'achat, route `/production/realise`)** — **mineur** (priorité basse) · vérifié (la route en double, elle, est **déjà corrigée**)
Sources : CAL-A 1, API-B 7, RG-B I43.
Fichiers : `calcul/moteur.py:1649-1669`, `api/production_plan.py:194`.
Correction :
- clé de tri `(-(M×poids), position)`, conforme au commentaire « rang du catalogue d'abord » ;
- retirer « (Remplace la vue de pilotage.py du même chemin) ».
Essai : `test_plan_achat_ex_aequo_ordre_catalogue`.

**D-21 · Contrainte d'unicité (ordre, qualité) absente en base** — **mineur** · partiel (l'API refuse déjà le doublon, `api/production.py:267-269`)
Sources : DON 36.
Correction : `UniqueConstraint("bon_id","qualite_id")`, étape demandée à G.
Essai : `test_ordre_qualite_en_double_refusee_en_base`.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| Le « dernier ordre » compte les ordres annulés (API-B 12, RG-B I40) | PAS UN DÉFAUT | Un ordre annulé garde son numéro : le compter maintient la suite numéros/dates voulue par M67. |
| Plan versionné dans un journal tronqué à 2 000 caractères (DON 17) | PAS UN DÉFAUT | Non confirmé : une ligne par qualité fait environ 800 caractères au plus. Le détail des montages peut être tronqué ; PRO aura une colonne JSON. |
| `fils_remplaces` sur rôle None (CAL-A 13) | PAS UN DÉFAUT | Non confirmé : le rôle d'une matière est obligatoire. Le cas réel est **D-03**. |
| `m2_passe` qui ignore `jusqu_a` (CAL-B 18) | PAS UN DÉFAUT | Non confirmé : le total est renormalisé. |
| Versions de recette partielles : rôle et densité lus aujourd'hui (CAL-A 11) | PRO SEULEMENT | La densité est obligatoire et change rarement ; à versionner dans PRO. |
| `besoins_passes`, ancre de croissance, fenêtre au niveau usine (CAL-A 10, 12, 14) | PAS UN DÉFAUT | Conforme à O11, ou cas sans effet en service. |
| Arrondi au conditionnement seulement au-delà de 1 kg ; montants au prix du catalogue (CAL-A 19, 20) | PAS UN DÉFAUT | A3 et A9. |
| Tri SQL du catalogue ; ABC sur des négatifs ; statut classeur (CAL-A 2, 18, 28) | PAS UN DÉFAUT | Sans effet en service. |
| Fil monté sans écriture au journal (CAL-A 4, CAL-B 8, DEC § 16.1, RG-A I-28) | PRO SEULEMENT | Décision U8 de Mohamed. Le modèle « lieu de stock » est pour PRO. Le chiffre de consommation est la décision **DM-07**. |
| Étage hors limites : 404 contre 422 (API-A 5, RG-A I-22) | PRO SEULEMENT | Même message, codes à uniformiser. |
| `PUT /production/plan` sur une qualité arrêtée (API-B 22) | traité dans **D-01** | — |

### Domaine E — Pilotage, contrôles, réglages, exports, bilan, courriel

**E-01 · L'alimentation reçoit le conseil d'achat, les seuils en dirhams, les banques et les cours** — **bloquant** (contraire à D5 : « aucun prix ni montant chez l'alimentation ») · vérifié, plus grave que décrit
Sources : API-B 3, RGL 7, RG-B I65, AML R8.
Fichiers :
- `api/pilotage.py:39-62` : `MONTANTS_STOCK` ne retire que les montants. Les quantités à commander, la classe ABC, le rang et la part cumulée restent, et l'écran les affiche (`StockParMatiere.tsx:173`, `:191`, `:197`) ;
- `api/comptes.py:276-277` (`/parametres`), `:400-401` (`/devises`), `:416-418` (historique des cours) : ouverts à tout rôle. On y lit les seuils d'approbation et de tiers en MAD, la banque, l'ICE, la date de clôture, les adresses de courriel.
Aucun écran de l'atelier n'appelle ces trois routes.
Correction :
- `Depends(ACHATS)` sur `/parametres`, `/devises` et `/devises/{code}/historique` ;
- dans `/stock` et `/stock/{référence}` pour l'alimentation, mettre aussi à `None` : `quantite_a_commander(_achat)`, `palettes_a_commander`, `unites_a_commander`, `bons_en_preparation`, `bc_en_preparation`, `sans_achat`, `classe_abc`, `rang`, `pourcentage_cumule`.
L'écran retire ces colonnes (**H-03**).
Essais : `test_alimentation_ne_lit_ni_parametres_ni_devises` (403), `test_stock_alimentation_sans_conseil_achat`.

**E-02 · Changer un cours de devise revalorise les mois clos** — **bloquant** (contraire à V3 : « le coût d'une marchandise entrée dans un mois clos ne change plus ») · vérifié
Sources : CAL-B 5 (pour les dossiers ouverts), signalé par la vérification B28.
Fichiers : `api/comptes.py:430-446` (`ecrire_devise`), `calcul/moteur.py:3618-3621` (une ligne de dossier sans cours prend le cours courant), `api/comptes.py:312-317` (clôture).
Constat :
- une ligne hors commande d'un dossier ouvert suit le cours du jour ;
- changer le cours dans Réglages › Devises change donc son coût de revient, et le CMUP de matière déjà sortie, même dans un mois clos ;
- clore une période n'exige pas que ses dossiers soient clos.
Correction :
- dans `ecrire_devise`, avant de changer le cours, figer le cours actuel sur les lignes sans cours des dossiers ouverts qui ont une entrée en période close, avec la note « cours figé au changement du JJ/MM » ;
- à la clôture de période, refuser s'il reste un dossier ouvert portant une entrée de la période : « Le dossier X est ouvert et porte des entrées de la période : le clore d'abord. ».
Essai : `test_changer_cours_ne_revalorise_pas_un_mois_clos`.

**E-03 · Le bilan du mois ne s'équilibre pas et tombe en 500 sur un mois invalide** — **bloquant** (faux chiffres sur un document rendu) · vérifié
Sources : API-B 9, B 11, CAL-B 9, B 10, RG-B I2, I55, ECR 8.16, 8.23, 8.24.
Fichiers : `api/suivi.py:529-530`, `:552-557`, `:566-571`, `:586-601`, `:618`, `:658-670`, `:683`.
Défauts :
- (a) « 2026-13 » ou « 0000-00 » donnent une 500 ;
- (b) un mois futur est accepté ;
- (c) les kilos d'entrées comptent les réceptions annulées, alors que la valeur les exclut ;
- (d) pour le mois en cours, la valeur de fin compte le fil monté, alors que les kilos de fin et la valeur de début l'excluent ;
- (e) les entrées sont valorisées au prix de facture, le reste au coût de revient ;
- (f) « Commandes émises » compte les bons annulés ;
- (g) « Sorties … dont X revenus » alors que les retours ne sont pas compris dans les sorties ; et « parfois d'un mois précédent », alors qu'une annulation prend la date de l'original.
Correction :
- (a, b) mois de 1 à 12, année de 2000 à 2100, mois ≤ mois courant ; sinon 422 « Mois invalide : AAAA-MM, pas dans le futur. » ;
- (c) retirer les annulées des kilos et de la ligne « annulations » ;
- (d) valoriser la fin sans le montage et afficher le stock en machine à part ;
- (e) entrées au coût de revient (`couts_du_journal().unitaire`) ;
- (f) `statut != "annulee"` ;
- (g) « X kg revenus, net Y kg », et retirer « parfois d'un mois précédent ».
Essais : `test_bilan_mois_invalide_422`, `test_bilan_equilibre_en_valeur` (début + entrées − consommation ± autres = fin, à 1 MAD près, avec un dossier d'importation), `test_bilan_commandes_hors_annulees`.

**E-04 · La matrice des prix mélange les devises et affiche la devise du catalogue** — **bloquant** (faux chiffre ; contraire à T8, prix dans leur monnaie d'origine) · vérifié, plus grave que décrit
Sources : CAL-B 6.
Fichiers : `api/pilotage.py:455-473`, `:485`.
Correction : moyenner par référence, mois **et devise de la facture**, et renvoyer la devise réelle de chaque cellule.
Essai : `test_matrice_ne_melange_pas_les_devises`.

**E-05 · Les opportunités gonflent les économies : dernier prix d'un jour = le plus cher ; article inactif comparé ; moteur pas en « même couleur » par défaut ; fenêtre de l'export non bornée** — **gênant** · vérifié
Sources : CAL-B 13, 16, 17, API-B 18, RGL 16 (pour l'export).
Fichiers : `calcul/moteur.py:2165`, `:2177`, `:2185`, `:2255`, `:2269`, `:2291`, `:2344`, `:2379`, `api/exports_analyse.py:161-170`, `api/pilotage.py:218-228`.
Correction :
- trier par date seule, sur une requête rangée par date puis par identifiant de ligne : le dernier saisi gagne ;
- ignorer un article inactif ;
- `meme_couleur=True` par défaut dans le moteur (décision T6) ;
- export : `fenetre_jours` borné (`Query(None, ge=1, le=3650)`) et `date_reference` accepté ;
- un rival « hors fenêtre » est compté dès qu'un de ses prix est inférieur.
Essais : `test_dernier_prix_meme_jour_est_le_dernier_saisi`, `test_opportunites_ignore_article_inactif`, `test_export_opportunites_fenetre_negative_422`.

**E-06 · Le Cockpit et la Valorisation peuvent dire deux valeurs du stock** — **gênant** (contraire à V1 : « deux pages ne disent jamais deux chiffres ») · vérifié, rare
Sources : CAL-B 1, B 2.
Fichiers : `calcul/moteur.py:2391-2405` (Cockpit : un CMUP nul retombe sur le catalogue, et `detenu > 0` seulement) contre `:2018-2029`.
Correction :
- `cout[ref] if ref in cout else catalogue(ligne)` ;
- une seule règle pour les stocks négatifs : les deux pages les excluent.
Essai : `test_cockpit_egale_total_valorisation`.

**E-07 · Contrôles qui contredisent le reste de l'application** — **gênant** · vérifié
Sources : CTL 4, CTL 5.
Fichiers : `calcul/controles.py:310` (C05), `:368-369` (C07), `:494-503` (C13), `:525-531` (C15), `:328-331` (C06, 60 jours en dur), C19 par `moteur.py:2941`. Côté achats : `api/achats.py:95-98` et `services/courriel.py:39-43`.
Constat :
- les matières désactivées restent comptées, alors que le « quoi faire » dit de les désactiver ;
- C13 dit « Commander tout de suite » pour une matière que le plan ne proposera jamais ;
- C06 déclare un bon en retard à 60 jours, alors que ni la liste des commandes ni le courriel ne le disent.
Correction :
- filtrer `actif` dans C05, C07 et C19 ;
- C13 exclut `sans_achat` ;
- C15 dit « matière désactivée encore dans la recette » ;
- une seule échéance, `modele.echeance_commande(c, p)` : ETA, sinon date promise, sinon date du bon + délai du fournisseur. C06, `_statut_livraison` (A) et le courriel l'utilisent.
Essais : `test_matiere_inactive_hors_C05_C07_C13`, `test_retard_meme_verdict_ecran_courriel_c06`.

**E-08 · La note des contrôles est gonflée, la pastille toujours allumée** — **gênant** (contraire à T11 : honnêteté du score) · vérifié
Sources : CTL 6, CTL 7, CTL 27.
Fichiers : `calcul/controles.py` (GARANTIS ; `:420-427` C10 ; `:1141` synthèse).
Constat :
- C02, C04, C14, C24, C26, C31 et C32 sont refusés dès la saisie, mais comptent « conformes » dans la note ;
- C27 tient tant que C12 tient ;
- la pastille compte aussi les contrôles d'information.
Correction :
- ajouter ces contrôles à GARANTIS (« garanti par la saisie ») ;
- C10 passe en « bloquant » comme les autres garantis ;
- C20 utilise le seuil `< -POUSSIERE` ;
- la synthèse renvoie `a_corriger`, sans les contrôles d'information, et c'est lui que lit la pastille (**H-07**).
Essais : `test_synthese_ne_compte_pas_les_garantis_de_saisie`, `test_pastille_ignore_information`.

**E-09 · DPO et fournisseurs du Cockpit faux** — **mineur** · vérifié (DPO), partiel (fournisseurs)
Sources : CAL-B 11, B 12.
Fichiers : `calcul/moteur.py:2459-2474`, `:2493-2501`, `:2524`, `:2540`.
Correction :
- DPO pondéré par le montant **reçu** sur 12 mois glissants ;
- `fournisseurs_actifs` ne compte que les actifs.
Essais : `test_dpo_bon_solde_pese_le_recu`, `test_cockpit_fournisseurs_actifs_exclut_inactifs`.

**E-10 · Contrôles : libellés et seuils trompeurs** — **mineur** · vérifié
Sources : CTL 2, 3, 13, 14, 16, 17, 19, 22, ECR 8.14, 8.15.
Fichiers : `calcul/controles.py:7`, `:192-219`, `:359`, `:402`, `:689-697`, `:763-785`, `:823`, `:916`, `:987`, `:1039-1040`.
Correction :
- C29 : « TVA d'importation à plus de 5 % de la TVA attendue (20 % de la valeur en douane, droits et TPI compris) », avec la tolérance tirée d'un réglage `toler_tva_import` ;
- C23 : « Fil monté sans poids de bobine (ni pesé au lot, ni au catalogue) », en avertissement ;
- C28 : « …sans frais hors TVA », avec un réglage `delai_frais_import_jours` ;
- C34 : la TVA dans sa propre colonne ;
- colonnes « Jours depuis la commande », « Jours depuis l'arrivée », « Nombre de dates » ;
- `devise` ajoutée à COLONNES, les six clés mortes retirées ;
- « 2 % » avec une espace ;
- docstring : « Six contrôles du classeur ont disparu ».
Essais : `test_colonnes_controles_toutes_libellees`, `test_libelles_pourcent_avec_espace`, `test_c29_libelle_dit_la_tolerance`, `test_c34_tva_a_part`.

**E-11 · Contrôles qui ne contrôlent pas** — **mineur** · vérifié
Sources : CTL 8, 12, 15, 18.
Fichiers : `calcul/controles.py:428-441` (C11), `:652`, `:668-673` (C24, C25), C17 par `moteur.py:1413-1418`, C36 par `moteur.py:3711-3714`.
Correction :
- C11 devient « Devise employée (catalogue, bons, dossiers) sans cours » ;
- C25 exige une sortie **nette** de la référence depuis le dernier montage ;
- C24 ne regarde que les métiers actifs ;
- C17 : une matière sans groupe d'équivalence est mono-source ;
- C36 signale les dossiers dont la facture n'a pas de montant ou n'est pas dans la même devise ;
- C38 compare dans la même devise.
Essais : `test_c11_devise_sans_cours`, `test_c25_sortie_annulee_ne_suffit_pas`, `test_c17_matiere_sans_groupe_mono_source`, `test_dossier_facture_sans_montant_signale`.

**E-12 · Exports : gravité brute dans le pilotage, écart C36 sans format %, dates en texte, `q` limité à 120 caractères, classement « À surveiller » non traduit** — **mineur** · vérifié
Sources : CTL 24, API-B 18, ECR 8.23.
Fichiers : `api/exports.py:228-234`, `api/exports_analyse.py:80-86`, `:139`, `:183`, `:186`, `:207`, `:217`, `:231`, `:280`.
Correction :
- gravité et état en clair, comme dans `exports_analyse.py:58-63` ;
- format pourcentage pour `ecart` ;
- vraies dates Excel ;
- même limite de `q` à l'écran et à l'export ;
- « ATTENTION ».
Essais : `test_export_pilotage_controles_gravite_en_clair`, `test_export_prix_dates_sont_des_dates`.

**E-13 · Devises : historique de cours écrit sans changement de cours ; MAD désactivable ; code non alphabétique** — **mineur** (faux historique) · vérifié
Sources : API-B 16, RGL 15, ECR 8.12.
Fichiers : `api/comptes.py:393-446`.
Correction :
- n'historiser que si le cours change ;
- motif `^[A-Za-z]{3}$` ;
- MAD toujours au cours 1 et actif.
Essais : `test_devise_renommage_sans_ligne_de_cours`, `test_mad_ne_se_desactive_pas`.

**E-14 · Clore une période sans voir les brouillons qui y restent** — **mineur** · partiel
Sources : RGL 13, RG-B I66.
Fichiers : `api/comptes.py:312-317`.
Correction : en clôturant, refuser en listant les réceptions, ordres, opérations et inventaires en brouillon datés au plus tard à la date de clôture. Le recul de la date reste permis à la direction et tracé (V3).
Essai : `test_cloture_refusee_si_brouillon_dans_periode`.

**E-15 · Courriel : adresses non validées, échec écrit sous « [indicateurs] », courriel non tenté si la photo échoue** — **mineur** · vérifié
Sources : EXP 15, RGL 14, RG-B I73, ECR 8.19.
Fichiers : `api/comptes.py:298-322`, `api/suivi.py:841-847` (tâches), `main.py:102-105` (G retouche le libellé).
Correction :
- valider chaque adresse côté serveur ;
- deux blocs `try` séparés, « [photo] » et « [courriel] ».
Essais : `test_parametres_courriel_adresse_invalide_refusee`, `test_taches_du_jour_courriel_tente_si_photo_echoue`.

**E-16 · Réglage « BC urgent » affiché mais sans effet ; ordre des tiers non contrôlé** — **mineur** · vérifié (BC urgent), non confirmé (seuils critique et alerte, qui servent au statut classeur affiché)
Sources : RGL 1, 2, 3, ECR 8.17.
Fichiers : `parametres.py:185`, `calcul/moteur.py:1725`, `api/comptes.py:342-352`.
Correction :
- retirer `seuil_bc_urgent` de la liste des réglages modifiables (garder la valeur) ;
- contrôler tier1 ≥ tier2 ≥ tier3.
Essais : `test_seuil_bc_urgent_absent_des_reglages`, `test_parametres_tiers_desordonnes_refuses`.

**E-17 · Photo des indicateurs remplacée sans journal ; OTIF moyen depuis toujours** — **mineur** · vérifié
Sources : CAL-B 28, API-B 22.
Fichiers : `api/suivi.py:489-513`, `:861-863`.
Correction :
- écrire au journal la photographie manuelle ;
- OTIF sur 12 mois glissants, comme l'analyse.
Essai : `test_photographier_trace_au_journal`.

**E-18 · « Moucheté » jamais reconnu comme mot de couleur** — **mineur** · vérifié
Sources : CAL-A 22.
Fichiers : `calcul/classification.py:104`, `:135`.
Ce fichier appartient à D, qui accepte la retouche d'une ligne.
Correction : retirer les accents des mots de la liste.
Essai : `test_mot_couleur_mouchete`.

**E-19 · Commentaires et docstrings périmés** — **mineur** (priorité basse) · vérifié
Sources : API-B 7, CAL-A 21, RGL 4, RGL 5, RG-A I-30.
Fichiers :
- `api/suivi.py:3` : import du plan par tableur, qui n'existe pas ;
- `calcul/modele.py:62` : « 43 cellules » au lieu de 45 (fichier de D) ;
- `calcul/modele.py:124` : secteur par défaut ;
- `TAUX_TVA_IMPORT`.
Correction : mettre les textes à jour.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| `LignePrix.date_bc` est la date de réception (CAL-B 14) | PAS UN DÉFAUT | Non confirmé : l'écran et l'export l'appellent « Date ». Renommer la clé dans PRO. |
| `/controles/soldes` en double de C12 (CTL 10) | PRO SEULEMENT | Doublon sans faux chiffre ; l'indicateur se retire avec PRO. |
| Seuils critique et alerte « inertes » (RGL 1) | PAS UN DÉFAUT | Non confirmé : ils règlent le statut classeur affiché, et leur aide le dit. |
| `seuil_approbation` en MAD au cours figé, hausse dans la devise du bon (RGL 17) | PAS UN DÉFAUT | Décision A8. |
| `fenetre_prix_jours` surchargeable par la requête (RGL 16) | PAS UN DÉFAUT | Décision T6 (fenêtre réglable à l'écran). |
| Tier 1 réservé à la classe A (RGL 3) | PAS UN DÉFAUT | Voulu (A18). |
| Valeurs de réglages illisibles avalées ; bornes larges ; aides doubles (RGL 6, 8, 11, 12, 19, 20) | PRO SEULEMENT | Sans effet visible. Les aides d’écran sont dans **H-38**. |
| Epsilons différents ; ordre et troncatures des contrôles (CTL 9, 20, 21, 25) | PRO SEULEMENT | — |
| Branches du mode classeur mortes (CTL 11, RGL 18, RG-A I-31) | PRO SEULEMENT | Inatteignables en service ; ne pas les recopier. |
| `prix_constates` mort, `origine` vide (CAL-B 15) | PAS UN DÉFAUT | Code mort sans effet. |
| Arrondi du bilan au pair (CAL-B 30) | PRO SEULEMENT | Invisible sauf sur un demi exact. |
| Le bilan sans en-tête de l'usine (API-B 11) | PRO SEULEMENT | Les papiers à en-tête A4 sont prévus dans PRO. |

### Domaine F — Comptes, sécurité, droits, prix masqués, sessions

**F-01 · Codes : un code d'atelier de 5 chiffres ou plus ne se tape pas ; un compte promu garde un code de 4 caractères** — **bloquant** (compte inutilisable, et faille sur un compte de direction ; contraire à D10) · vérifié, plus grave que décrit
Sources : RG-B I60, ECR 1.5, 8.11.
Fichiers : `securite.py:50-52`, `api/comptes.py:180`, `:201-205`. L'écran est dans `Connexion.tsx:99-100`, voir **H-01**.
Constat :
- le serveur accepte « 4 caractères au moins », de toute nature ;
- l'écran envoie au 4ᵉ chiffre puis vide le champ : un code de 5 chiffres échoue à chaque fois, jusqu'au blocage ;
- passer un compte de l'alimentation aux achats sans donner de nouveau code garde un code de 4 caractères.
Correction :
- alimentation : exactement 4 chiffres (`^\d{4}$`), refusé sinon avec « Le code de l'atelier est fait de 4 chiffres. » ;
- dans `modifier_compte`, si le nouveau rôle exige un code plus long et qu'aucun code n'est fourni, 422 « Ce rôle demande un code de 8 caractères au moins : en donner un nouveau. ».
Essais : `test_code_alimentation_exactement_4_chiffres`, `test_promouvoir_sans_nouveau_code_refuse`.

**F-02 · N'importe qui bloque n'importe quel compte ; une rafale de connexions dépasse le seuil de 5 échecs** — **bloquant** (sécurité : les codes de l'atelier n'ont que 4 chiffres) · vérifié, plus grave que décrit
Sources : RG-B I62, API-B 17, AML R7.
Fichiers : `securite.py:128-153`, `api/comptes.py:64-73`, `:108-116`.
Constat :
- le blocage est fait par identifiant : 30 s, puis doublé, jusqu'à 15 minutes. Le vrai titulaire est bloqué aussi ;
- `/visages` (public) donne tous les identifiants ;
- l'attente est lue **avant** de noter l'échec, si bien que des essais parallèles passent tous.
Correction :
- noter la tentative sous verrou de ligne (`SELECT … FOR UPDATE`) **avant** de vérifier le code ;
- compter aussi par adresse IP ;
- `/visages` ne renvoie que le nom et le rôle, avec un identifiant opaque.
Le choix « toucher son nom » (D10) est gardé.
Essais : `test_rafale_de_connexions_ne_depasse_pas_le_seuil` (20 essais parallèles → au plus 5 vérifications), `test_visages_ne_donne_pas_l_identifiant`.

**F-03 · Changer un code ne ferme pas les sessions ; un ancien code faux n'est pas compté ; sessions et tentatives jamais purgées** — **gênant** (un code changé après une fuite laisse la session volée valable 30 jours) · vérifié
Sources : RG-B I61, API-B 16, DON 23, EXP 9.
Fichiers : `api/comptes.py:141-152`, `:202-207`, `securite.py:71`.
Correction :
- après un changement de code, supprimer les sessions du compte, sauf la session courante pour `/moi/code` ;
- `noter_echec` sur un ancien code faux ;
- `vu_le` mis à jour dans `acteur`, au plus une fois par heure ;
- purge quotidienne des sessions expirées et des vieilles tentatives (la boucle des tâches est à G, qui l'appelle).
Essais : `test_changer_le_code_ferme_les_autres_sessions`, `test_ancien_code_faux_compte_un_echec`.

**F-04 · Aucun essai ne prouve que chaque route déclare ses rôles** — **gênant** (contraire à D3 : « un essai les parcourt toutes » ; le commentaire de `securite.py:113` annonce un essai qui n'existe pas) · vérifié
Sources : AML R9, ESS § 18, API-A 1, RG-B I6.
Fichiers : `securite.py:113`, `:117-118` (`TOUS` et `LECTURE` morts), `tests/test_parcours.py:48-59` (ne teste que l'accès sans connexion, en GET).
Constat : environ 50 lectures n'ont que la garde de session. Elles sont donc ouvertes à tout rôle connecté. C'est l'origine des fuites **A-14** et **E-01**.
Correction :
- écrire `tests/test_droits_toutes_routes.py`, qui déplie les routeurs (`_IncludedRouter`) et exige un `droit(...)` sur chaque route, sauf une liste blanche écrite : `etat`, `visages`, `installation`, `connexion`, `deconnexion`, `sante`, `moi`, `moi/code` ;
- remplacer `acteur` par `droit(LECTURE)` sur les lectures ouvertes à tous ;
- supprimer `TOUS` s'il reste inutilisé.
Essai : `test_chaque_route_declare_ses_roles`.

**F-05 · Un essai qui balaie toutes les lectures pour l'alimentation** — **gênant** (D5 n'est garanti aujourd'hui que route par route) · vérifié
Sources : API-A 2, API-B 1, ECR 3.27, AML R8, ESS § 16, REC 5.
Constat : aucun prix ni montant chiffré ne sort aujourd'hui. Mais restent : `devise`, `unite_prix` et `minimum_commande` dans `/articles`, et `devise` dans `/qualites`. Sans essai de balayage, la prochaine route ouverte à tous peut fuir.
Correction : un essai qui parcourt chaque GET accessible à l'alimentation, sur une base avec des prix, et qui échoue si une clé `prix*`, `cout*`, `valeur*`, `montant*`, `cours`, `taux`, `*_a_commander`, `classe_abc` ou `pourcentage_cumule` porte une valeur non vide. Les corrections des fuites sont **A-14** et **E-01** ; le masquage de `devise` et `unite_prix` se fait dans `referentiels.py`, par A pour les matières et par D pour les qualités. Le masqueur générique reste l'affaire de PRO.
Essai : `test_alimentation_ne_recoit_aucun_montant`.

**F-06 · Messages de saisie à moitié anglais (« valeur incorrecte integer, unable to parse… »)** — **mineur** · vérifié
Sources : API-B 10, RG-B I1.
Fichiers : `main.py:164-187`.
Correction : traduire selon `e["type"]` : `int_parsing` donne « nombre entier attendu », `float_parsing` « nombre attendu », `missing` « champ obligatoire »…
Essai : `test_erreur_de_saisie_entierement_en_francais`.

**F-07 · Les erreurs de base de données deviennent des 500** — **gênant** (filet commun pour A-03, A-06, D-13 et les cas oubliés) · vérifié
Sources : API-B 9, RG-B I2.
Fichiers : `main.py` (aucun gestionnaire pour `IntegrityError` ni `DataError`).
Correction : un gestionnaire global qui annule la transaction et répond 409 « Cette saisie contredit une règle de la base (doublon, valeur hors limites) : la vérifier. ». Il écrit aussi l'erreur technique dans le journal du serveur. Les corrections de chaque domaine restent à faire : ce filet n'est qu'un dernier recours.
Essai : `test_violation_de_contrainte_donne_un_refus_clair`.

**F-08 · La déconnexion se fait sans l'en-tête anti-falsification ; le refus 403 du middleware part sans en-têtes de sécurité** — **mineur** · vérifié
Sources : API-B 17.
Fichiers : `main.py:136`, `:147-151`.
Correction :
- retirer `/api/deconnexion` de `SANS_ENTETE` ;
- poser les en-têtes de sécurité sur le refus.
Essais : `test_deconnexion_sans_entete_refusee`, `test_refus_403_porte_les_entetes`.

**F-09 · Recherche du journal sensible aux accents** — **mineur** (contraire à E5) · partiel (`%` et `_` sont échappés)
Sources : ECR 8.22.
Fichiers : `api/comptes.py:227-236`.
Correction : `unaccent` des deux côtés, comme **C-14**.
Essai : `test_journal_trouve_sans_accent`.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| `/visages` public (ECR 1.26, AML R7) | PAS UN DÉFAUT | D10 (toucher son nom) ; l'identifiant est retiré par F-02. |
| `PUT /utilisateurs` exige un identifiant qu'il ignore (RG-B I63) | PRO SEULEMENT | Sans effet visible. |
| Journal au nom et non à l'identifiant (RG-B I7, DON 18) | PRO SEULEMENT | Changement de modèle ; « Mohamed / MOHAMED » est la décision **DM-06**. |
| HTTP en clair, cookie sans `Secure` (AML R7) | PRO SEULEMENT | HTTPS et Caddy sont prévus dans PRO. Tailscale chiffre déjà l'accès en 4G. |
| Codes d'erreur hétérogènes (API-A 5, API-B 10) | PRO SEULEMENT | — |

### Domaine G — Exploitation, sauvegardes, restauration, outils, pièces jointes, migrations

**G-01 · « Vider l'activité » ne marche plus** — **bloquant** (contraire à P9 : outil de mise en service) · vérifié
Sources : DON 32, EXP 1.
Fichiers : `outils/vider_activite.py:36-38`, `:69`, `modeles.py:955-958`, `:976-978`.
Constat :
- la liste ACTIVITE oublie `reclamation`, `dossier_charge_part`, `piece_jointe`, `signalement` et `indicateur_jour` ;
- PostgreSQL refuse de tronquer une table référencée par une table qui n'est pas tronquée : l'outil échoue. Rien n'est cassé (transaction annulée, sauvegarde faite avant), mais on ne peut pas vider.
Correction :
- ajouter `dossier_charge_part`, `reclamation`, `signalement` et `indicateur_jour`, sans `CASCADE` ;
- pour `piece_jointe` : `DELETE` des pièces d'activité (objet ∈ réception, commande, facture, dossier, réclamation, lot) et des fichiers correspondants. On garde celles des matières et des fournisseurs ;
- garder `recette_version` et `parametre_historique`, qui sont l'historique des référentiels ;
- faire l'essai sur une copie, puis refaire la « base vide de référence ».
Essais : `test_vider_activite_couvre_toutes_les_cles_etrangeres` (essai statique sur `Base.metadata`), `test_vider_activite_sur_une_base_d_essai`.

**G-02 · La restauration d'une sauvegarde ancienne peut laisser une base mêlée, sans migration** — **bloquant** (le seul point qui peut corrompre la production) · vérifié, plus grave que décrit
Sources : EXP 2.
Fichiers : `services/sauvegarde.py:163-196` (`pg_restore --clean --if-exists` sans transaction unique), `main.py:53`, `:120`.
Constat :
- une table créée après la sauvegarde (par exemple `dossier_charge_part`, étape 13) reste, et peut empêcher les `DROP` ;
- la restauration s'arrête à mi-chemin ;
- le serveur continue sur un schéma en retard jusqu'au prochain redémarrage.
Correction :
- `--single-transaction --exit-on-error`, ou restaurer dans une base temporaire puis renommer ;
- puis `migrer()` et `initialiser()` ;
- refuser une sauvegarde dont le schéma est plus récent que le code.
Essai : `test_restaurer_une_sauvegarde_ancienne_remet_le_schema_a_jour`.

**G-03 · Pièces jointes : chemin absolu, jamais restaurées, mêlées à celles des essais ; le miroir est absent des sauvegardes réelles** — **bloquant** (données) · vérifié
Sources : EXP 4, EXP 5.
Fichiers : `api/suivi.py:259-265`, `services/sauvegarde.py:84-88`, `config.py:44-45`.
Constat :
- `~/gestion-mp-pieces/` contient la production **et** 18 dossiers d'essai ou de démo ;
- aucun dossier `pieces-jointes` n'existe dans `~/gestion-mp-sauvegardes`, alors qu'il y a des quotidiennes du 5 au 8 octobre et 263 fichiers. Le miroir ne se fait donc pas, et la cause n'est pas identifiée.
Correction :
- trouver d'abord pourquoi le miroir ne se fait pas, et le prouver ;
- chemin relatif à `PIECES` ;
- production dans `~/gestion-mp-pieces/gestion_mp`, essais dans un dossier temporaire (`conftest.py`) ;
- le miroir ne copie que la base courante ;
- un geste « restaurer les pièces » depuis le miroir.
Essais : `test_piece_jointe_chemin_relatif`, `test_essais_n_ecrivent_pas_dans_les_pieces_reelles`, `test_sauvegarde_du_jour_recopie_les_pieces`.

**G-04 · Un compte de direction au code public, écrit en dur, reste actif si le vérificateur est interrompu** — **bloquant** (faille de droits) · vérifié, plus grave que décrit
Sources : DON 37, EXP 16.
Fichiers : `verificateur.py:335-352` (code `"verificateur-interne"` dans git).
Correction : ne plus utiliser de compte. Le vérificateur appelle l'application avec `dependency_overrides[acteur]`. À défaut, un code aléatoire à chaque lancement, et la suppression de ses sessions. Désactiver tout de suite le compte s'il existe en production.
Essai : `test_verificateur_ne_laisse_aucun_compte_actif`.

**G-05 · Sauvegarde ou restauration impossibles : erreur 500 brute** — **gênant** · vérifié
Sources : API-B 9, RG-B I2, ECR 8.16.
Fichiers : `api/comptes.py:497-502`, `services/sauvegarde.py:62-78`, `:174`.
Correction :
- sauvegarde : 503 « La sauvegarde a échoué : {raison} (pg_dump). » ;
- fichier illisible à restaurer : 422.
Essais : `test_sauvegarde_sans_pg_dump_message_clair`, `test_restaurer_un_fichier_illisible_422`.

**G-06 · L'alerte de sauvegarde regarde toutes les bases** — **gênant** (surveillance trompée) · partiel (chaque base a son sous-dossier, mais l'alerte est calculée sur tout)
Sources : API-B 8, EXP 6, RG-B I70.
Fichiers : `main.py:195-200`, `api/comptes.py:485-487`, `services/sauvegarde.py:126-144`.
Correction :
- l'alerte est calculée sur l'âge de la sauvegarde de **cette** base ;
- `/api/sante` lit `etat_sauvegardes()`.
Essai : `test_sante_ignore_les_sauvegardes_d_une_autre_base`.

**G-07 · Un double lancement remplace la copie en service ; écrans et dépendances non figés** — **gênant** · partiel (`c902c2c` a corrigé démo contre production)
Sources : EXP 7, AML R6.
Fichiers : `scripts/demarrer.sh:12-26`.
Constat :
- `rm -rf "$VERSION"` passe avant la vérification du port ;
- `ecran/dist` vient de l'arbre de travail, pas du commit ;
- le `.venv` est partagé.
Correction :
- verrou (`lockf`) ou contrôle du port **avant** de toucher la copie ;
- construire les écrans depuis l'archive du commit, ou vérifier un tampon du commit dans `dist`.
Essai : manuel, `essai_double_lancement` : après deux lancements, la copie du premier est intacte.

**G-08 · La restauration coupe le verrou des tâches de fond** — **mineur** · vérifié
Sources : EXP 3, RG-B I71.
Fichiers : `services/sauvegarde.py:147-160`, `:182-183`, `main.py:88-115`.
Correction : épargner la connexion qui tient le verrou consultatif 7426102, ou reprendre le verrou à chaque tour de boucle.
Essai : `test_restauration_garde_le_verrou_des_taches`.

**G-09 · La copie externe des sauvegardes n'est jamais purgée** — **mineur** (le disque se remplit) · vérifié
Sources : EXP 11, RG-B I72.
Fichiers : `services/sauvegarde.py:89-92`, `:105-118`.
Correction : appliquer `purger` aussi à la copie externe. Les manuelles restent gardées (X2), mais on n'en conserve que les 20 dernières « avant-* ».
Essai : `test_purge_aussi_la_copie_externe`.

**G-10 · Pièces jointes : type déclaré cru sur parole, `vnd.*` admet un exécutable, `.exe` gardé, taille lue en entier ; fichier disparu donne une 500** — **gênant** (contraire à X4 : « .exe refusé ») · partiel (seuls les achats déposent)
Sources : RG-B I51, API-B 9, API-B 22.
Fichiers : `api/suivi.py:232-233`, `:242-245`, `:253-261`, `:273-278`.
Correction :
- liste blanche d'extensions accordée au type ;
- contrôle des premiers octets (`%PDF`, JPEG, PNG, `PK`) ;
- types Office écrits en entier au lieu de `vnd.*` ;
- lecture par blocs avec arrêt à 20 Mo ;
- `objet` contrôlé à la lecture ;
- fichier absent : 410 « Le fichier de cette pièce a disparu du disque : la redéposer. ».
Essais : `test_piece_exe_refusee`, `test_piece_trop_lourde_refusee_sans_tout_lire`, `test_piece_disparue_410`.

**G-11 · Pas de démarrage automatique ni de redémarrage du serveur** — **mineur** · vérifié
Sources : EXP 13, AML R6.
Correction : un LaunchAgent `ma.gestion-mp` (`RunAtLoad`, `KeepAlive`). Le lanceur du bureau ne fait plus qu'ouvrir le navigateur.
Essai : manuel. On tue le processus, et `/api/sante` répond en moins de 15 s.

**G-12 · `reprise.py --essai` dit « Rien n'a été écrit » mais écrit** — **mineur** (message trompeur) · vérifié
Sources : EXP 8.
Fichiers : `reprise.py:259-283`.
Correction : en mode essai, refuser une base vide ou pas à jour, ou tout faire dans une seule transaction annulée.
Essai : `test_reprise_essai_n_ecrit_rien`.

**G-13 · Adresse du QR fausse derrière HTTPS** — **mineur** · vérifié
Sources : API-B 22.
Fichiers : `api/stock.py:342`, `:348` (domaine C, retouche écrite par G), `api/comptes.py:524`, `:539`.
Correction : reprendre le schéma et le port implicite de la requête.
Essai : `test_acces_https_sans_port`.

**G-14 · Outils et documents périmés** — **mineur** (priorité basse) · vérifié
Sources : EXP 12, EXP 14, CTL 23, RG-A I-29, I-30, AML R19.
Fichiers et constat :
- `outils/comparer_erp_fil.py:66-76` : bloc « À COLLER » ;
- `outils/comparaison_calcul.py:92` : chemin `/Users/...` écrit en dur ;
- `docs/MISE-EN-SERVICE.md` : nom de la sauvegarde de référence ;
- `docs/ETAT-DES-LIEUX.md:576-613` et `docs/conformite/final-A`, `-B`, `-C` : périmés ;
- le cahier : lot interne à 5 chiffres, alimentation qui lit les réceptions, import du plan ;
- `calcul/moteur.py:7` renvoie à un document absent.
Correction : mettre à jour, avec la mention « le code fait foi ».

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| Migrations à trous, appel au code vivant, DDL en f-string (DON 1-3, AML R10) | PRO SEULEMENT | Inoffensif en service. PRO consolide le schéma. |
| `Numeric`, CHECK manquants, FK polymorphes, colonnes sans défaut serveur, index (DON 4, 6-10, 19, 20, 28, 29, 34, 35) | PRO SEULEMENT | Sans défaut visible. |
| Cache du moteur par signature (EXP 10, RG-B I76) | PRO SEULEMENT | Toutes les routes écrivent au journal. |
| Pièce retirée gardée sur le disque (DON 24) | PAS UN DÉFAUT | Voulu (rien ne disparaît). |
| Manuelles jamais purgées (EXP 11) | PAS UN DÉFAUT | Décision X2. |
| Service worker sans cache (ECR 3.4) | PAS UN DÉFAUT | Décision X6. Le texte d'installation est traité par **H-05**. |

### Domaine H — Écrans : textes, gestes, chiffres affichés, droits d'écran

Les chemins partent de `ecran/src/`. `ecran/` n'a aucun essai automatique (REC § 7). Chaque correction de H est donc vérifiée à la main, dans le navigateur, au rôle indiqué. Ajouter vitest n'est pas obligatoire pour ces corrections. Si l'équipe l'ajoute, elle le fait dans `ecran/` seulement.

**H-01 · Connexion : un code d'atelier de 5 chiffres ou plus ne se tape pas** — **bloquant** pour ces comptes · vérifié
Sources : ECR 1.5, ECR-T 8.
Fichiers : `pages/Connexion.tsx:99-100`, qui envoie au 4ᵉ chiffre et vide le champ si la connexion échoue.
Correction : avec **F-01**, le code de l'atelier fait exactement 4 chiffres, et l'envoi automatique devient juste. Tant que F-01 n'est pas fusionné, n'envoyer automatiquement que si `/visages` indique une longueur de 4.
Vérification : un compte de l'atelier à 4 chiffres se connecte au 4ᵉ chiffre. Aucun compte à 5 chiffres ne peut plus exister.

**H-02 · Au téléphone, une panne de réseau ressemble à des données** — **gênant** · vérifié
Sources : ECR 1.16, ECR 3.3, ECR-T 8.
Fichiers :
- `pages/atelier/Retour.tsx:89` et `:200` : « Tout ce qui est parti sur cet ordre est déjà revenu » ;
- `Bons.tsx:19` ;
- `Chercher.tsx:53` ;
- `Atelier.tsx:55-71` : compteurs à 0 ;
- `pages/Lot.tsx:13` et `pages/atelier/LotFiche.tsx:67-71` : « Ce lot n'existe pas ».
Correction : tester `isError` partout. Afficher « Le serveur ne répond pas : vérifiez le Wi-Fi, puis réessayez. » avec un bouton « Réessayer ». Garder « Ce lot n'existe pas » pour le seul cas 404.

**H-03 · Le conseil d'achat est affiché à l'alimentation** — **bloquant** (avec **E-01**) · vérifié
Fichiers : `components/stock/StockParMatiere.tsx:173`, `:191`, `:197`.
Correction : pour l'alimentation, retirer les colonnes « À commander » et « ABC », ainsi que le rang et la part cumulée.

**H-04 · Si l'ordre ne se lit pas, `?bon=ID` ouvre un ordre vierge ; un ordre annulé s'affiche « Ordre validé »** — **gênant** (risque de doublon) · vérifié
Fichiers : `pages/atelier/Envoyer.tsx:38-48`.
Correction :
- si l'ordre ne se lit pas, afficher un message d'erreur avec « Réessayer », et non un ordre vierge ;
- si l'ordre est annulé, afficher le titre « Ordre annulé » et « Cet ordre est annulé : il ne se modifie plus. ».

**H-05 · L'astuce « installer » promet une application qui ne s'installe pas en http** — **mineur** · partiel
Sources : ECR 1.2, ECR 3.4.
Fichiers : `pages/atelier/Atelier.tsx:115-116`, `main.tsx:32`.
Correction : en http, écrire « Astuce : « Ajouter à l'écran d'accueil » crée un raccourci vers Gestion MP. ».

**H-06 · Le fil sur les métiers est encore dit « hors stock » ou « pour information »** — **gênant** (texte contraire au calcul et à la décision U8 de Mohamed) · vérifié
Sources : ECR 1.8, ECR 2.6, ECR 3.1, ECR 8.2, ECR-T 1, DEC § 16.1.
Fichiers :
- `pages/Cockpit.tsx:90-92`, `:96` ;
- `components/direction/AnalyseValorisation.tsx:97`, `:100`, `:175` ;
- `pages/Guide.tsx:376`, `:426` ;
- `components/stock/StockParMatiere.tsx:227`, `:592` ;
- `pages/PlanAchat.tsx:241` ;
- `components/production/VoletBesoins.tsx:157`.
`MetiersTisser.tsx:707` et `Montage.tsx:340` sont déjà corrigés par `b925e81`.
Correction : un seul texte partout.
- Valeur : « le stock détenu (magasins et métiers), au coût moyen pondéré, dont X sur les métiers ».
- Disponible : « magasins hors quarantaine, plus le fil sur les métiers ».
- Retirer « (info) » et « hors stock ».
Vocabulaire : `REGLES-ECRAN.md` § 3 interdit « en machine », et plusieurs textes l'emploient. Écrire partout « sur les métiers ».

**H-07 · « Matières en alerte » : trois nombres différents ; pastille des contrôles toujours allumée** — **gênant** · vérifié
Sources : ECR 1.9, ECR-T 6, CTL 27.
Fichiers : `App.tsx:191`, `:192`, `pages/Accueil.tsx:247`, `:248`, `pages/Cockpit.tsx:58`, `:149`.
Correction :
- un seul compte, rupture plus critique, avec le même libellé partout (« N en rupture ou critiques ») ;
- l'onglet « Matières en alerte » dit ce qu'il contient ;
- la pastille des contrôles lit `a_corriger` (**E-08**).

**H-08 · Un acheteur ou la direction qui scanne un QR au téléphone arrive sur l'accueil, sans la fiche** — **gênant** · vérifié
Sources : ECR 1.3, ECR 3.2, ECR-T 4.
Fichiers : `App.tsx:163`, `:167`.
Correction : rediriger `/lot/:id` vers `/atelier/lot/:id` pour l'alimentation **seulement**. Les autres rôles gardent la page du lot.

**H-09 · Session expirée ou compte désactivé : retour à la connexion sans explication** — **gênant** · vérifié
Sources : ECR 1.6.
Fichiers : `App.tsx:118-155`, `lib/api.ts:45-47`.
Correction : transmettre le motif à l'écran de connexion, sauf pour un « Se déconnecter » volontaire.
- Session expirée : « Votre session a expiré : touchez votre nom et retapez votre code. »
- Compte désactivé : « Ce compte n'est plus actif : voyez la direction. »

**H-10 · Des saisies se perdent sans question** — **gênant** (règle « ne jamais perdre une saisie ») · vérifié
Sources : ECR 1.22, ECR 2.10, ECR 3.17, ECR 6.25, ECR 7.22, ECR 8.8, ECR-T 3.
Fichiers :
- `pages/Accueil.tsx:119` (Traiter) ;
- `components/production/RetourBureau.tsx:184` ;
- `pages/Production.tsx:50-57` (plan) ;
- `components/production/VoletPlan.tsx:157` (« Tout annuler ») ;
- `pages/atelier/commun.tsx:230` (bouton ‹ de Retour, Déplacer, Signaler et Montage) ;
- `CatalogueMatieres.tsx:1107`, `CatalogueFournisseurs.tsx:682`, `CatalogueClassification.tsx:366`, `pages/Qualites.tsx:323` ;
- `ReglagesComptes.tsx:251`, `ReglagesMagasins.tsx:147`, `ReglagesPostesFrais.tsx:203`, `ReglagesCodesDouaniers.tsx:160` ;
- brouillons des Paramètres et des Devises perdus au changement d'onglet (`pages/Reglages.tsx:118-119`).
Correction :
- partout, `<Confirmer question="Abandonner les modifications ?" oui="Oui, abandonner">` quand la saisie a changé ;
- une prop `sale` sur l'`Ecran` de l'atelier ;
- `useBlocker` pour la navigation par le menu.

**H-11 · Opérations : « Valider » perd en silence la ligne remplie mais pas ajoutée, et n'est pas grisé malgré les blocages** — **gênant** (perte de saisie) · vérifié
Sources : ECR 6.6, ECR-T 2.
Fichiers : `pages/Operations.tsx:509`, `:569-590`, `:736-745`.
Correction : griser « Valider » et « Enregistrer » tant que l'encart de ligne est rempli, avec « Ajouter ou annuler la ligne en cours ». Les griser aussi tant qu'il y a des blocages, en donnant la liste des blocages en infobulle.

**H-12 · Une sortie ou une entrée de quarantaine est proposée avec un mauvais motif ; le refus n'arrive qu'à l'enregistrement** — **gênant** · vérifié
Sources : ECR 6.2, ECR-T 2.
Fichiers : `pages/Operations.tsx:519-534`, `:846-855`.
Correction :
- hors des motifs « Libération » et « Mise en quarantaine », ne proposer ni lot en quarantaine ni destination de quarantaine ;
- après un changement de motif, signaler en rouge les lignes devenues incohérentes.

**H-13 · « Matière retrouvée » et « nouveau lot » partent en « Retirer » par défaut** — **gênant** (stock écrit à l'envers sur un lot existant) · vérifié
Sources : ECR 6.3.
Fichiers : `pages/Operations.tsx:822`, `:945-951`.
Correction : sens « Ajouter » pour le motif « Matière retrouvée » ; sens imposé pour un nouveau lot.

**H-14 · Inventaire en cours non annoncé à l'ouverture d'une opération** — **gênant** (contraire à N2) · vérifié
Sources : ECR 6.20.
Fichiers : `pages/Operations.tsx`, qui n'utilise pas `useSuspension` (`pages/atelier/commun.tsx:177`).
Correction : un bandeau en tête de saisie, comme à l'atelier.

**H-15 · La valeur de l'écart d'inventaire n'apparaît pas dans le comptage** — **gênant** (contraire à N1 : « écarts valorisés ») · partiel (seul le total est affiché dans les listes)
Sources : ECR 6.15, ECR-T 6.
Fichiers : `pages/Inventaire.tsx:70-71`, comptage `:965-1000`.
Correction : une colonne « Valeur de l'écart (MAD) » et un total en pied.

**H-16 · La feuille de recomptage part de saisies non enregistrées** — **gênant** · vérifié
Sources : ECR 6.8, ECR-T 10.
Fichiers : `pages/Inventaire.tsx:703`, `:845-855`.
Correction : griser le bouton tant que des comptages ne sont pas enregistrés, avec « Enregistrer d'abord les comptages : la feuille part de ce qui est enregistré. ».

**H-17 · Inventaire : libellé « tout le stock » pour un inventaire partiel ; matières absentes du magasin ; tolérance non bornée ; poids du catalogue** — **mineur** · vérifié
Sources : ECR 6.16-6.19.
Fichiers : `pages/Inventaire.tsx:419`, `:465`, `:474-476`, `:508`, `:526`, `:630`, `:1187-1196`.
Correction :
- libellé et question selon le périmètre (« Figer {n} lot(s) des matières retenues et suspendre les mouvements de tous les magasins ? ») ;
- ne proposer que les matières en stock dans ce magasin ;
- tolérance de 0 à 100 % ;
- date minimale = le lendemain de la clôture ;
- poids du lot mesuré, sinon « (poids catalogue) ».

**H-18 · « Période close jusqu'au » s'enregistre sans confirmation, et une date future n'est pas bloquée** — **gênant** (geste comptable lourd) · vérifié
Sources : ECR 8.7, ECR 8.9.
Fichiers : `components/direction/ReglagesParametres.tsx:177-186`, `:276-282`.
Correction :
- `Confirmer` « Clore jusqu'au … ? Plus rien ne s'écrira à cette date ni avant. » ;
- date maximale = hier.

**H-19 · Un ordre antidaté propose, pour les fils ajoutés à la main, les quantités d'aujourd'hui** — **gênant** · vérifié
Sources : ECR 2.23, ECR 3.23.
Fichiers : `components/production/SaisieSortie.tsx:208-214`, `pages/atelier/Envoyer.tsx:315-321`, `pages/atelier/sortie.ts:214-222`.
Correction : `/soldes?magasin_id=…&date=jour`, avec une clé de cache qui contient le jour.

**H-20 · Réceptions : brouillon en double avec deux devises ; impossible de recevoir deux lots sur une même ligne de bon** — **gênant** · vérifié
Sources : ECR 4.5, ECR 4.6, ECR-T 9.
Fichiers : `components/achats/SaisieReception.tsx:310-312`, `:464-471`, `:819-822`.
Correction :
- appeler la route unique de **A-09** ;
- bouton « Ajouter un lot » sur une ligne de bon, qui garde le même `commande_ligne_id` ;
- contrôle d'excédent sur la somme des lots de la ligne, comme le serveur.

**H-21 · Achats : petits écarts entre le geste et le texte** — **mineur** · vérifié
Sources : ECR 4.2, 4.4, 4.12, 4.13, 4.14, 4.16, 4.19, ECR-T 7.
Fichiers et corrections :
- `DetailCommande.tsx:1063-1066` : l'infobulle Solder/Annuler lit `dejaLivre` ;
- `Commandes.tsx:339`, `DetailCommande.tsx:340` : « À approuver » au lieu de « Brouillon » (`numeroOuBrouillon`) ;
- `PreparationCommande.tsx:617-635` : « Pré-remplir nos prix du catalogue (non imprimés, à confirmer par le fournisseur) » ;
- `Commandes.tsx:145` : l'export reçoit le filtre « en retard » ;
- `Commandes.tsx:68`, `:70` : `enRetard` et `prixAConfirmer` viennent de `lib/commandes` ;
- `PlanAchat.tsx:263` : « À commander (kg) » ;
- `SaisieReception.tsx:628-634` : date de facture au plus aujourd'hui ;
- `DetailReception.tsx:730` : message « Réception annulée : les entrées sont contre-passées. » ;
- `PreparationCommande.tsx:388` : aide « pour le calcul seulement, non enregistré » ;
- `DetailCommande.tsx:957-968` : « Imprimer » et « Excel » d'un brouillon marqués « Brouillon — non envoyé ».

**H-22 · Une réclamation sur une ligne refusée part sans référence** — **mineur** (avec **A-10**) · vérifié
Fichiers : `components/achats/Reclamations.tsx:296`.
Correction : envoyer `reception_ligne_id`.

**H-23 · « Tout valider » : compte faux, note de rôle fausse, lien refusé** — **gênant** · vérifié
Sources : ECR 2.12, ECR 2.13, ECR 6.1, ECR-T 2, ECR-T 4.
Fichiers : `components/stock/AValider.tsx:58`, `:106`, `:171`, `:174`.
Correction :
- compter `peut_valider && !blocages.length` ;
- note « validé par l'alimentation » pour un ordre, un retour des machines ou un transfert ;
- lien selon le rôle (**C-17**).

**H-24 · Opérations : navigation et traçabilité** — **mineur** · vérifié
Sources : ECR 6.12, 6.13, 6.21, 6.22, ECR 1.17.
Fichiers : `pages/Operations.tsx:193-196`, `:321-326`, `:450-455`, `:499-508`, `:610-614` ; `pages/Stock.tsx:678`.
Correction :
- liens `/lot/ID` ;
- `onglet` = type à la fermeture ;
- `?operation=` posé après création ;
- « annulée par X le … » (colonnes `annulee_par` et `annulee_le` à demander à G, renvoyées par C) ;
- libération d'un lot en quarantaine dans deux magasins : choisir la source.

**H-25 · Mode d'emploi et règles : textes faux** — **mineur** · partiel
Sources : ECR 1.18, ECR 1.19, ECR 1.28, ECR 7.15.
Fichiers : `pages/Guide.tsx:207`, `:224`, `:234`, `:325`, `:577`.
Corrections :
- « Réglages › Téléphone » ;
- « Les achats n'ont des réglages que les devises » ;
- « Au bureau : sorties vers les machines, stock et lots, métiers à tisser ; les déplacements de lots passent par l'écran atelier » ;
- lien du point hebdomadaire masqué pour les achats.

**H-26 · Dossier d'importation : TVA saisie fausse, « Clôturer » cliquable malgré des frais non répartis, frais réglé non signalé, lien « Ajouter une facture » mort** — **gênant** (chiffre affiché faux) · vérifié
Sources : ECR 5.1, 5.2, 5.5, 5.6, 5.7, ECR-T 6.
Fichiers : `components/importations/DetailDossier.tsx:207-210`, `:317`, `:543-546`, `:665`, `:1005`, `:1067`, `:1076`, `:1152`, `:1263-1264`, `:1283`, `:1351`, `:1486`, `:1623`.
Correction :
- encart TVA sur `d.tva_saisie_mad`, le seul poste TVA ;
- « Clôturer » grisé si des frais ou de la TVA ne sont pas répartis, avec la raison ;
- « réglé le » affiché en modification, et montant, poste et « Retirer » grisés pour un frais réglé (**B-01**) ;
- montant vidé : message « Montant obligatoire : pour supprimer le frais, utiliser « Retirer ». » ;
- lien « Ajouter une facture » seulement s'il y a un second camion, et texte sans « lignes de réception » ;
- « La facture  est arrivée » corrigé pour un dossier sans facture ;
- raisons sur les boutons grisés.

**H-27 · Importations : textes et totaux** — **mineur** · vérifié
Sources : ECR 5.3, 5.4, 5.8, 5.9, 5.12, 5.14, 5.15, 5.17, 5.18.
Fichiers :
- valeur en douane « achat + fret + assurance (CAF) » : `DetailDossier.tsx:1023`, `ReglagesCodesDouaniers.tsx:4`, `:35`, `:134` ;
- TPI lue du serveur (**B-05**) : `DetailDossier.tsx:1063` ;
- étiquette « à vérifier » complète : `Importations.tsx:263-270` ;
- indicateurs calculés sur la vue : `Importations.tsx:75-80` ;
- colonne « Lignes » : `Importations.tsx:494` ;
- message après un changement de clé : `ReglagesPostesFrais.tsx:117-125` ;
- `maxLength` 160, 32 et 2000 : `DetailDossier.tsx:501-513` ;
- `colSpan` : `AnalyseRevient.tsx:666` ;
- « Effacer les filtres » : `ChoixFacture.tsx:59-75`.

**H-28 · Catalogue : une ancienne matière incomplète ne se désactive pas ; « ml » tapable ; bornes non contrôlées ; champ « priorité » sans effet** — **gênant** · vérifié
Sources : ECR 7.20, ECR 7.21.
Fichiers : `components/referentiels/CatalogueMatieres.tsx:911-918`, `:1073`.
Correction :
- désactiver par une route qui ne change que `actif` : A ajoute `PUT /articles/{aid}/actif`, sans revalider la fiche ;
- unité d'achat dans une liste, sans « ml » ;
- `min` et `max` comme le serveur ;
- retirer le champ « priorité dans le groupe » (**A-26**).

**H-29 · Qualités : recette d'une qualité arrêtée, avertissement serveur ignoré, enregistrement en deux appels** — **gênant** · vérifié
Sources : ECR 7.6-7.8.
Fichiers : `components/referentiels/QualiteDetail.tsx:141`, `:166`, `:188-215`.
Correction :
- afficher `avertissement` ;
- bloquer dès qu'un rôle pesant n'a pas de fil, selon la règle de **D-05** ;
- si la recette est refusée : « Fiche enregistrée ; recette refusée : … ».

**H-30 · Import tableur : champs bruts, aperçu sans valeurs** — **mineur** (avec **A-03**) · vérifié
Sources : ECR 7.11, ECR 7.12.
Fichiers : `components/referentiels/TableurMatieres.tsx:22-44`, `:191`.
Correction :
- ajouter « Unité du prix » et « Code douanier » ;
- retirer `unite` ;
- afficher « Champ : avant → après » ;
- dire qu'une case vide ne vide pas le champ.

**H-31 · Fournisseurs et classification : suppression et renommage proposés puis refusés ; ton « Délai » sans raison ; liens par nom** — **mineur** · vérifié
Sources : ECR 7.4, 7.5, 7.24, 7.25, ECR 8.1.
Fichiers : `CatalogueFournisseurs.tsx:135`, `:231`, `:292`, `:393-400`, `:436-440`, `:472`, `:673` ; `CatalogueClassification.tsx:454-459`, `:500-505`.
Correction :
- lire les compteurs de **A-25** et **A-13** ;
- infobulle « Délai mesuré supérieur de plus de 20 % au délai déclaré : corriger la fiche » ;
- rapprocher par identifiant ;
- lien `&fournisseur=` vers l'Analyse.

**H-32 · Métiers au bureau : deux poids de bobine pour le même fil ; « Part (%) » sans plafond ; pied en mètres bruts ; enregistrement en deux appels ; `?metier=nouveau` pour tous** — **mineur** (le double poids contredit F18 : « un seul chiffre partout ») · vérifié
Sources : ECR 3.11-3.15.
Fichiers : `components/referentiels/MetiersTisser.tsx:187`, `:350`, `:393-400`, `:430`, `:563`, `:609`, `:635` ; `pages/Metiers.tsx:18`.
Correction :
- afficher `poids_bobine_utilise` ;
- `max=100` ;
- pied = Σ mètres ;
- message « fils enregistrés, réglage refusé » si le second appel échoue ;
- création réservée à la direction.

**H-33 · Listes coupées sans le dire ; scanner muet** — **gênant** au téléphone · vérifié
Sources : ECR 3.18, ECR 3.19, ECR 6.14.
Fichiers :
- `pages/atelier/Chercher.tsx:34`, `:51`, `:101-106` ;
- `Bons.tsx:16` ;
- `LotFiche.tsx:142` ;
- `pages/Operations.tsx:194`, avec **C-13**.
Correction :
- « Les {n} premiers sur {total} : préciser la recherche. » ;
- au scanner, si le lot est inconnu, afficher « Étiquette lue mais lot inconnu : {code} », retenir le code et ne pas relancer la caméra à chaque rendu.

**H-34 · Échéancier : la vue « Par mois » et les indicateurs ignorent les filtres ; pas de total ; export sans les réglées** — **gênant** · vérifié
Sources : ECR 8.21.
Fichiers : `components/direction/AnalyseEcheancier.tsx:118-131`, `:340-360`. L'export est dans `api/exports_analyse.py` (E).
Correction :
- calculer « Par mois » sur les lignes filtrées ;
- pied de total ;
- feuille « Réglées » ajoutée par E.

**H-35 · Comptes et magasins : la désactivation emporte le formulaire ; « Enregistrer » laisse découvrir un 409** — **gênant** · vérifié
Sources : ECR 8.7, ECR 8.10.
Fichiers : `ReglagesComptes.tsx:127-138`, `ReglagesMagasins.tsx:141-151`.
Correction :
- désactiver n'envoie que `actif`, ou bien le bouton est grisé si la fiche a changé ;
- « Enregistrer » grisé quand on désactive un magasin qui détient de la matière, avec la raison.

**H-36 · Seuils écrits en dur au lieu du réglage** — **mineur** · vérifié
Sources : ECR 8.4.
Fichiers : `ComparaisonPrix.tsx:257` (5 % au lieu de `seuil_hausse_forte`), `AnalyseProduction.tsx:46`, `:65`, `:87`, `:105`, `AnalyseValorisation.tsx:111`.
Correction :
- lire `seuil_hausse_forte` ;
- pour les autres, une constante commune nommée, avec sa valeur dite dans l'infobulle.

**H-37 · Réglages : historique des cours au format brut, famille sans aide, destinataires réglables à deux endroits, note des sauvegardes fausse** — **mineur** · vérifié
Sources : ECR 8.13, 8.18, 8.19, 8.28, RGL 8, RGL 10.
Fichiers : `ReglagesParametres.tsx:34-50`, `:342` ; `ReglagesSauvegardes.tsx:164-166` ; `ReglagesCourriel.tsx:1-2`.
Correction :
- cours au format `nombre(v, 4)` MAD ;
- aide de la famille « Stock et inventaire » ;
- retirer les destinataires de la famille Société ;
- « Les {k} plus récentes de cette base sont listées, sur {nb}. ».

**H-38 · Aides des réglages : quatre réglages sans aide, deux sources d'aide** — **mineur** · vérifié
Sources : RGL 8, RGL 9.
Fichiers : `ReglagesParametres.tsx` (`AIDES_REGLAGE`).
Correction :
- aides de `score_*`, `seuil_hausse_forte` et `dso` ;
- l'aide de `toler_ecart_pesee` dit son second rôle (« sert aussi à juger une livraison partielle »).

**H-39 · Vocabulaire hors des règles d'écran** — **mineur** · vérifié
Sources : ECR 2.1-2.4, 2.17, 2.22, 2.24, 3.5-3.8, 3.20, 3.21, 6.11, 7.1-7.3, ECR-T 5.
Corrections :
- « Référence » au lieu de « Fil » en en-tête de colonne : `SaisieSortie.tsx:163`, `:170`, `MetiersTisser.tsx:486`, `QualiteDetail.tsx:334`, `VoletGlissant.tsx:83` ;
- « Brouillon » au lieu de « sans n° » et « Ordre du {date} » : `Sorties.tsx:203`, `:279`, `Bons.tsx:23`, `:59` ;
- « À sortir (kg) » sur l'onglet Brouillons : `Sorties.tsx:193` ;
- « Sorti net » : `Retour.tsx:209` ;
- « Les mouvements de stock de cette matière » : `StockParMatiere.tsx:580` ;
- « Aucun ordre de fabrication. » : `Tracabilite.tsx:184` ;
- « ← Revenir : … » : `Tracabilite.tsx:286` ;
- classe `cliquable` au lieu de `clic` : `Accueil.tsx:51`, `VoletRealise.tsx:128`, `:151`, `Bons.tsx:21`, `Retour.tsx:91`, `Chercher.tsx:57`, `Montage.tsx:49` ;
- nom du métier « CODE · Nom » partout : `Bons.tsx:29`, `:76`, `Retour.tsx:100`, `Envoyer.tsx:115`, `Sorties.tsx:211`, `Montage.tsx:231` ; côté serveur, `production.py:395` est corrigé par D ;
- « USD / kg » et « MAD / m² » : `types.ts:326-329`, `Qualites.tsx:155`, `:369` ;
- « Par » au lieu de « Ouvert par » et « Validé par » : `Inventaire.tsx:223`, `:282-283` ;
- « Prix (devise / kg) » : `Operations.tsx:603` ;
- un seul terme, « Stock d'ouverture » : `Operations.tsx:136` ;
- `REGLES-ECRAN.md` dit si « Commentaire » est permis. La règle n'interdit que « Remarque » : le garder.

**H-40 · Boutons grisés sans leur raison** — **mineur** · vérifié
Sources : ECR 2.11, 3.9, 4.9, 5.7, 6.5, 8.6.
Fichiers :
- `Sorties.tsx:397` ;
- `SaisieSortie.tsx:131`, `:240`, `:251` ;
- `Envoyer.tsx:365` (retirer `&& s.aEnvoyer.length`) ;
- `DetailCommande.tsx:782`, `:939` ;
- `SaisieReception.tsx:1067` ;
- `Stock.tsx:280` ;
- `VoletPlan.tsx:160`, `:207` (coefficient hors de 0 à 20) ;
- `Operations.tsx:729`, `:736-740`, `:1115` ;
- `Inventaire.tsx:629-632`, `:1219-1223` ;
- `AnalysePrix.tsx:255` ;
- `ReglagesDevises.tsx:108-110`, `:158-165` ;
- `ReglagesCourriel.tsx:86` ;
- `ReglagesComptes.tsx:252-256` ;
- `ReglagesMagasins.tsx:150` ;
- `ReglagesParametres.tsx:195-199` ;
- `Signaler.tsx:89` ;
- `Montage.tsx:359` ;
- `MetiersTisser.tsx:271`, `:713-714`.
Correction : donner la raison dans `titre`, et l'afficher sous le bouton au téléphone.

**H-41 · Unités et mètres indicatifs manquants** — **mineur** · partiel
Sources : ECR 1.14, 1.15, 2.15, 2.16.
Fichiers et corrections :
- `CockpitAlertes.tsx:88-92` : « kg » et « ≈ ml » pour le cuir, les franges et le ruban ;
- `Stock.tsx:503`, `:635` : « Quantité (kg) » ;
- `Stock.tsx:546` : prix « … / kg » ;
- `Stock.tsx:591` : « Entré · sorti » avec les deux unités ;
- `Tracabilite.tsx:397`, `AValider.tsx:141` : unités dans les en-têtes.

**H-42 · Divers : relances, accueil, compteurs, mises en forme** — **mineur** · vérifié
Sources : ECR 1.1, 1.4, 1.10, 1.11, 1.13, 1.20, 1.21, 1.23, 2.14, 2.18, 2.19, 2.21, 2.25, 3.24, 3.25, 5.16, 6.9, 6.23, 7.26-7.31, 8.5, 8.27.
Corrections :
- `main.tsx:15` : relance selon `e.statut` ;
- `App.tsx:170` : `accueilDe` ;
- `Accueil.tsx:245` : tous les inventaires ouverts ;
- `CockpitAlertes.tsx:126` : « Aucune des {n} plus pressées ne correspond » ;
- `PiecesJointes.tsx:37`, `:103-108` : liste relue dans un `finally`, `accept` sans SVG ;
- `ui.tsx:373-376` : `try/catch` ;
- `format.ts:34` : trois décimales au plus ;
- `Sorties.tsx:70`, `:180`, `:267-272` : message visible ;
- `Stock.tsx:622` : garder l'onglet ;
- « Effacer les filtres » : `VoletBesoins.tsx`, `Inventaire.tsx:965-976`, `AnalyseOpportunites.tsx:132-164` ;
- mois écrits d'une seule façon ;
- `Retour.tsx:215` : plafonner au net parti ;
- `Signaler.tsx:42`, `Atelier.tsx:64` : par identifiant (D renvoie `par_id`) ;
- compteurs et filtres du catalogue (`Catalogue.tsx:38`, `:58`, `:88`, `Qualites.tsx:112`, `:343`, `QualiteDetail.tsx:581`) ;
- `entree` sur les `select` de `ReglagesPostesFrais.tsx:154` et `AnalyseRevient.tsx:276-330`.

Non retenus dans ce domaine :

| Point | Classe | Raison |
|---|---|---|
| Écart C36 affiché à 350 % (ECR 8.3, ECR-T 6, CTL 1) | **déjà corrigé** | `b925e81`. Reste le format % de l'export (**E-12**). |
| Confirmation de montage « déjà consommé » (DEC § 16.1) | **déjà corrigé** | `b925e81`. |
| `Tableau` absent, bascule maison, code mort, `HAUT_DIALOGUE` (ECR 1.24, 1.25, 2.5, 2.8, 3.16, 5.13, 7.18) | PAS UN DÉFAUT | Sans effet visible ; PRO a ses composants. |
| Onglets de fenêtres hors adresse, état de l'analyse hors adresse (ECR 3.29, 4.18, 5.16) | PRO SEULEMENT | Une route par fiche dans PRO. |
| Exports manquants (inventaires, opérations, besoins, lots, métiers) (ECR 2.19, 6.10) | PRO SEULEMENT | Nouvelles fonctions et non défauts. |
| Libellé du bandeau d'abandon (ECR 1.7) | PAS UN DÉFAUT | Même sens. |
| Achats voyant Coût de revient, Échéancier, Production (ECR 8.25) | PAS UN DÉFAUT | D4 : pilotage lisible par tous ; la règle d'écran est à compléter. |
| « Abandonner cette sortie » recharge l'application (ECR 3.26) | PAS UN DÉFAUT | Effet voulu : repartir de zéro. |
| Matrice et opportunités : même couleur par défaut (ECR 8.x) | PAS UN DÉFAUT | Non confirmé : l'écran est conforme à T6. |
| Changer d'onglet ferme la qualité ouverte (ECR 7.29) | PAS UN DÉFAUT | Non confirmé (fenêtre modale). |
| Plan d'achat : l'export sort tout le classeur (ECR 4.14) | PAS UN DÉFAUT | Dit dans l'infobulle. |
| Déplacer garde la quantité, « Tout le lot » (ECR 3.24) | PAS UN DÉFAUT | Non confirmé : la conversion est plafonnée. |
| Aucun essai d'écran (REC § 7, AML R1) | PRO SEULEMENT | — |
| TypeScript non strict, fichiers géants, styles dispersés, doublons, types locaux (AML R1-R5, R13-R15, R21, R22) | PRO SEULEMENT | — |

