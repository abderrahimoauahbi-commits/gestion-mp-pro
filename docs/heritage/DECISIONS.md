# Héritage de Gestion MP — toutes les décisions métier, datées, avec leur raison

Inventaire établi le 8 octobre 2026, en lecture seule, pour la réécriture « Gestion MP PRO ».
Chaque décision prise depuis le 17 septembre 2026 (ERP Fil puis Gestion MP) est ici, avec sa
date, sa raison et sa source. **Toutes restent valables dans Gestion MP PRO** sauf mention
contraire ; une décision « non retenue » l'est aussi (ne pas la réintroduire sans la rouvrir).

## Comment lire

| Marque | Sens |
|---|---|
| **[M]** | Décision ou demande explicite de Mohamed (le propriétaire). |
| **[D]** | Décision déléguée : Mohamed a demandé le 2 octobre « fais au mieux selon ton expérience, coller le plus possible à la réalité » (M14) ; l'équipe a tranché selon la pratique d'usine et l'a écrit. Mohamed ne l'a pas contredite. |
| **[N]** | Non retenu, volontairement, avec la raison. |
| **[?]** | Reste à trancher par Mohamed (au 8 octobre 2026). |
| **[R]** | Revirement : la décision a changé ; seule la dernière vaut. |

Sources (dépôt `/Users/mohamed/gestion-mp`) : `docs/EXIGENCES-MOHAMED.md` (M01…M86, « EX »),
`docs/CAHIER-DES-CHARGES.md` (« CDC », §2 les dix questions, §6 règles, §10 tranché le
3 octobre), `docs/CONFORMITE.md` (« CONF »), `docs/AUDIT-2026-10-08.md` (« AUD »),
`docs/conformite/final-A…E` (« FA…FE », sections « Décisions prises » et « Recette »),
`docs/recette/*.md` (« REC-achats / atelier / direction »), `docs/COMPARAISON-ERP-FIL.md`
(« CMP »), messages de commit (`git log`, hachés cités), la liste du coordinateur du
8 octobre 2026 (« COORD »), et le code quand il fixe la règle (`fichier:ligne`).

---

## 1. Le projet, sa forme, sa méthode

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| P1 [M] | 17/09 | Partir du classeur « GESTION Fil » pour un « super ERP » ; refaire toutes les feuilles importantes (la Matrice d'abord). | Le classeur était l'outil réel de l'usine. | EX M01, M05 |
| P2 [M] | 17/09 | Un exécutable et un **raccourci sur le bureau**. | Mohamed ouvre l'outil d'un double-clic. | EX M02 ; `~/Desktop/Gestion MP.app` |
| P3 [M] | 17/09 | Vérifier que tous les chiffres concordent ; si le classeur se trompe, **proposer d'abord** la correction, l'écrire et la justifier. | Aucune méthode ne change en silence. | EX M03 ; CMP (« 0 écart inexpliqué », chaque correction voulue attribuée) |
| P4 [M] | 17/09 | Sauvegarder avant tout essai ; stresser ; pouvoir remettre les valeurs d'origine. | Ne jamais perdre la base réelle. | EX M04 |
| P5 [M] | 25/09 | **PostgreSQL**, multi-postes, sur serveur, plusieurs intervenants. | Travail à plusieurs ; l'ERP Fil (SQLite puis double moteur) avait laissé passer des validations en double. | EX M07, M08 ; CDC §7 |
| P6 [M] | 28/09 | Audit complet « comme un humain qui s'en sert » : logique, calculs, transitions, boutons. | — | EX M09 → vérificateur indépendant, recette par clics, année simulée |
| P7 [M] | 01/10 | Remplir la base avec les vrais référentiels pour mesurer la performance. | — | EX M10 ; `docs/PERFORMANCE.md` (aucun écran > 1 s, 20 postes en 1,9 s) |
| P8 [M] | 01/10 | **Seuls catalogue, classification, fournisseurs, qualités et recettes sont vrais ; ne jamais les supprimer.** Une donnée fausse est **signalée, pas corrigée en silence**. | Ce sont les données réelles de l'entreprise ; l'activité est un jeu d'essai. | EX M11 ; CDC §6.8 |
| P9 [M] | 02/10 | Pouvoir vider l'activité en gardant les référentiels, et **garder la base vide de référence**. | Repartir de zéro à la mise en service. | EX M12 ; `outils/vider_activite.py` |
| P10 [M] | 02/10 | Une **année d'épreuve** saisie comme un humain, dans l'ordre des dates, tout le catalogue, ≥ 3 achats par référence. | Vérifier chiffres et prévisions. | EX M13 (l'année de l'ERP Fil sert d'année simulée) |
| P11 [M] | 02/10 | « **Fais au mieux selon ton expérience, coller le plus possible à la réalité.** » | Mohamed n'est pas informaticien ; il attend le choix d'un professionnel et corrige par des faits de terrain. | EX M14 ; fonde toutes les décisions [D] |
| P12 [M] | 02/10 | Titre **« Gestion MP »** ; exemple de nom **« MAZARI »** (premier compte direction proposé). | — | EX M15 |
| P13 [M] | 02/10 | Vérifier intégrité, stabilité, performance, justesse. | — | EX M16 (vérificateur 0 écart, entrées malformées sans erreur 500, < 0,3 s) |
| P14 [M] | 03/10 | Un **nouvel ERP**, intuitif, agile, précis, juste ; **ne pas toucher l'ERP Fil** ; **ne rien oublier** ; faire mieux ; « ne me demande plus rien, livre un travail fini ». | Leçon de la GMAO, conçue sans inventaire de l'existant. | EX M17 ; CDC §2.10 |
| P15 [M] | 08/10 | **Gestion MP PRO** : version professionnelle complète au standard de GMAO PRO, dans `~/gestion-mp-pro`, sans rien oublier, sans questions jusqu'à la livraison, avec des tests finaux (résultats, structure, justesse des calculs). | L'informaticien a jugé que Gestion MP « ne faisait pas professionnel ». | `gestion-mp-pro/docs/PLAN.md` |
| P16 [D] | 03/10 | Reprise depuis l'ERP Fil **en lecture seule**, sur une copie, empreinte vérifiée ; **pas l'activité** ; mise en service par un **stock d'ouverture lot par lot**. | L'activité de l'ERP Fil est une année d'essai. | CDC §2.9 ; `docs/MISE-EN-SERVICE.md` |
| P17 [D] | 03/10 | Méthode de calcul unique (« corrigée ») ; le mode « classeur » abandonné, la parité reste prouvée par la comparaison. | Le mode classeur ne servait que le portage. | INVENTAIRE-ERP-FIL l. 986 ; CMP |

## 2. Rôles et droits

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| D1 [M] | 03/10 | **Trois rôles** (au lieu de sept) : **Direction** (Mohamed : tout, plus comptes, réglages, sauvegardes, approbations, recettes), **Achats** (la responsable : commandes, réceptions, inventaire, importations et frais, ouvertures, ajustements, création des matières), **Alimentation des machines** (l'homme de l'atelier, au téléphone : sorties, retours, déplacements, lots). | La taille réelle de l'usine. | CDC §2.1 ; mémoire projet |
| D2 [M] | 03/10 | L'alimentation travaille **au téléphone**, en Wi-Fi de l'usine **et** en 4G/5G (Tailscale ; Mohamed crée le compte lui-même). | L'atelier n'a pas de poste. | CDC §3 ; `MISE-EN-SERVICE.md` |
| D3 [D] | 03/10 | **Interdit par défaut** : toute route déclare ses rôles, un essai les parcourt toutes ; « le serveur refuse ce que le menu cache ». Matrice à un seul endroit (`securite.py`, `QUI` d'`operations.py`). | Ne pas compter sur l'écran pour protéger. | CDC §4, §6.1 ; AUD (204 routes × 3 rôles, 0 anomalie) |
| D4 [D] | 03/10 | Matrice : référentiels matières/classification/fournisseurs É direction + achats, L alimentation ; qualités, recettes, plan, magasins, métiers É direction, L achats, L alimentation (**fils montés : É** alimentation) ; plan d'achat, commandes É V direction, É achats (approbation : direction) ; réceptions, factures, étiquettes É V direction + achats, L alimentation ; dossiers d'importation É V direction + achats ; sorties et retours des machines É V direction + alimentation, L achats ; transferts É V les trois ; ouvertures, ajustements, retours fournisseur, inventaire É V direction + achats ; pilotage L pour tous. Réglages : direction ; les achats n'y voient que **Devises** (É). | — | CDC §4 ; `App.tsx` (route `/reglages` gardée `['achats']`, onglet Devises seul) |
| D5 [M] | 08/10 (confirmé) | **Aucun prix ni montant chez l'alimentation** : ni à l'écran, ni par l'API, ni dans les exports (stock, mouvements, lots, opérations, nomenclature, qualités, articles). | L'homme de l'atelier n'a pas à connaître les prix. | REC-atelier n° 1 (bloquant) ; FE « Atelier 1 » ; ac615a6 ; 96db9ea (« la dernière fuite, par la nomenclature, est fermée ») |
| D6 [D] | 04/10 | Libération de quarantaine : **décision des achats (ou direction)** ; l'alimentation peut **mettre** en quarantaine un lot douteux (motif imposé « Mise en quarantaine », commentaire obligatoire), pas l'en sortir (403 « décision des achats »). | Séparer qui signale et qui décide. | FE « Décisions prises » |
| D7 [D] | 03/10 | Annuler un retour des machines : rôle alimentation (et direction) ; les achats lisent. Annuler un ordre annule aussi ses retours (même transaction). | L'alimentation n'avait aucun écran pour annuler un retour (REC-atelier n° 6). | FE « Atelier 6 » ; 202d1a0 |
| D8 [D] | 03/10 | Codes douaniers et postes de frais : **écriture direction**, lecture achats. | Donnée de mise en service, tarif douanier. | FB « Recette » G16 |
| D9 [D] | 04/10 | Le compte de la direction ne peut ni se désactiver ni changer de rôle. | Ne jamais perdre l'administration. | REC-direction § 4 |
| D10 [D] | 04/10 | Connexion : on touche son nom puis on tape son code ; **code à 4 chiffres** pour l'alimentation (validation automatique au 4ᵉ chiffre), **8 caractères au moins** pour achats et direction ; après 5 échecs, le compte patiente. Premier lancement : création du compte direction. | Rapidité au téléphone, sûreté au bureau. | `MISE-EN-SERVICE.md` ; c2c9108 |
| D11 [N] | 03/10 | Durée de session, nombre d'échecs tolérés, dossiers de sauvegarde **non réglables à l'écran** (variables d'environnement, affichées dans Réglages › Serveur). | Ne se règlent pas au quotidien. | CONF « non retenu » |
| D12 [M→PRO] | 08/10 | GMAO PRO ajoute un **administrateur technique** : repris dans Gestion MP PRO (en plus des trois rôles métier). | Standard du service informatique. | PLAN.md |

## 3. Unités, stock, lots, quarantaine, machines

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| U1 [M][R] | **08/10 19:19** | **Le stock est toujours en kilos**, pour toutes les matières, **cuir, bande (ruban) et franges compris** : réceptions, sorties, retours, transferts, inventaires, commandes, besoins. Plus d'« unité de stock » sur la fiche ; plus de saisie en ml ; un seul total en kg. | Une seule unité de stock, comme les pesées réelles. Remplace la décision de 14:51 (voir R1). | COORD ; d2e1e39, b75bc24 ; AUD bloquant 1 |
| U2 [M] | 08/10 | **Le prix se saisit au kg (par défaut) ou au mètre** (`unite_prix` = kg ou ml) ; un prix au mètre est **ramené au kilo par la densité** (`prix_kg = prix ÷ densité`) ; **tous les calculs lisent le prix au kilo**. Un prix au mètre se lit aussi au mètre là où l'on confirme un prix et au plan d'achat (le fournisseur qui facture au mètre lit des mètres). Un prix confirmé sur un bon passe au catalogue au mètre (× densité) quand la fiche est au mètre. | Certains fournisseurs facturent au mètre. | COORD ; d2e1e39 |
| U3 [M] | 08/10 | Recettes : les **rôles au mètre (Cuir, Franges, Ruban)** se saisissent en **ml/m²** ; le logiciel calcule les **kg/m²** par la densité (`poids_du_role`) ; la nomenclature montre les deux. | C'est ainsi qu'on mesure ces rôles sur un tapis. | COORD ; d2e1e39, b75bc24 |
| U4 [M] | 08/10 | **Mètres affichés à titre indicatif** à côté des kilos pour cuir, franges, ruban : « 14,3 kg ≈ 1 020 ml » (`kg ÷ densité`, `kgEtMetres` de `lib/format.ts`, `kg_par_ml` donné par l'API). | Lisible pour l'atelier sans changer l'unité de stock. | COORD ; `docs/REGLES-ECRAN.md` § 2 |
| U5 [M] | 08/10 | **Franges = même logique que cuir et bande** (rôle au mètre, densité obligatoire, stock en kg, prix au kg ou au mètre). | — | COORD |
| U6 [D] | 08/10 | **Densité (kg/ml) obligatoire** pour un cuir, des franges, un ruban, et pour tout prix au mètre. « ml » n'est plus une unité d'achat. | Sans densité, ni kilos ni prix au kilo. | d2e1e39 |
| U7 [D] | 08/10 | Étape de schéma 14 : une matière tenue « ml » passe au kilo (quantités × densité, prix ÷ densité partout), **montants inchangés** ; prouvé par un essai. Le prix catalogue de Bande (2,5) et Cuir (0,074) garde sa valeur, **lu au kilo**. | Migration sans perte de valeur. | d2e1e39 ; CMP |
| U8 [M] | **08/10 18:20** | **Le stock est en magasin ou en machine** : le fil **monté sur les métiers**, pas encore tissé, **compte dans le stock global**, **dans sa valeur** et **dans le disponible / projeté pour commander**. « Ne jamais l'en retirer. » | Les bobines du cantre tisseront les prochains tapis : les ignorer ferait racheter ce qui est déjà sur la machine ; elles appartiennent à l'usine. Remplace R2. | COORD ; 169dfdc ; mémoire projet ; `moteur.py` `valorisation` (stock = magasin + machine), `cockpit.detenu` |
| U9 [M] | 08/10 | **La quarantaine est en stock** (détenue, payée, **valorisée**) mais **à part** : ni disponible, ni sortie, ni stock projeté, **ne compte pas pour les achats**. | Confirmé par Mohamed le même jour. | COORD ; CDC §6.6 ; `moteur.cockpit` |
| U10 [M] | 18/09 | Avant de commander : **stock + stock sur machine + commandes non arrivées** (à leur **ETA**). | — | EX M62 |
| U11 [M] | 18/09 | La **valorisation compte tout** le stock : magasins et machines. | — | EX M63 (cohérent avec U8) |
| U12 [M] | 30/09 | Le **numéro de lot** sur la sortie de production et sur **toutes** les écritures ; l'ordre de fabrication sur toute sortie. | Traçabilité. | EX M64 |
| U13 [D] | 03/10 | **Statut du lot calculé**, pas saisi (disponible, en quarantaine, « en partie en quarantaine », épuisé). | Le stocker ferait deux vérités. | CDC §10 ; FE « Atelier 36 » |
| U14 [N] | 03/10 | **Emplacements sous le magasin** non retenus ; pas de magasin « Annexe ». | Deux magasins et une quarantaine ; chaque palette porte le QR de son lot ; une saisie d'emplacement ralentirait l'atelier. | CDC §10 ; CONF |
| U15 [D] | 03/10 | Le **journal** est la seule écriture de stock ; soldes (lot, magasin) tenus dans la même transaction sous **verrou de ligne** ; un contrôle confronte soldes et journal (C12). | Interdire deux sorties de la même palette. | CDC §5.2, §6.2 |
| U16 [D] | 03/10 | **Le stock d'un lot ne passe jamais sous zéro**, même à plusieurs ; « sous le gramme, un stock est nul » (`POUSSIERE = 1e-3`). | — | CDC §6.3 ; `moteur.py:732` |
| U17 [D] | 08/10 | **Écritures antidatées refusées** si elles feraient passer un lot sous zéro **à leur date ou après** : une sortie datée d'hier ne prend pas un lot arrivé ce matin ; la proposition ne prend que les lots **présents à la date de l'ordre**. Contrôle C37 (lot sous zéro à une date passée). | Une sortie d'hier partait à coût nul sur un stock négatif (audit 2-G B1). | COORD ; AUD bloquant 4 ; `services/stock.py:77` `couvert_a_sa_date` |
| U18 [D] | 03/10 | **Un fait ne se date ni dans le futur, ni avant l'an 2000** (faute de frappe 2006/2026), **ni dans une période close**. Dit dès le brouillon, pas seulement à la validation. | — | CDC §6.5 ; `securite.py:210` `date_permise` |
| U19 [D] | 03/10 | **Saisie en deux temps** pour tout document : **brouillon** (corrigeable, supprimable, sans effet, **sans numéro**) → **validé** (recontrôlé, écrit, immuable) → **annulation par contre-passation, une seule fois, datée de la date d'effet d'origine**, date de saisie à côté. | Brouillon puis validé (M73) ; « contre-passer » expliqué (M72). | CDC §5.2, §6.2 ; EX M46, M72, M73 |
| U20 [D] | 03/10 | Unités de saisie : kg, **bobine** (au poids **mesuré du lot**, à défaut catalogue ; une bobine se compte entière), **palette** (peut être entamée) ; une unité vide = kg. | — | FE « Décisions » |
| U21 [D] | 04/10 | Valeur d'un mouvement = **coût moyen du moment** (une entrée d'achat à son coût de revient si le dossier le connaît, sinon prix × cours), calculée à la lecture, même calcul que la Valorisation. | Suit les dossiers complétés après coup. | FE « Décisions » |

## 4. Référentiels (matières, classification, fournisseurs, qualités, métiers)

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| F1 [M] | 17/09 | Un fournisseur facture en **deux devises** (SBR en EUR, chaîne en USD) : la devise appartient au **prix de la matière**, pas au fournisseur ; **les montants ne s'additionnent jamais entre devises**. | — | EX M20 ; CDC §6.7 |
| F2 [M] | 25/09 | **Titrage, composition (nature), type de fil, couleur** en référentiels séparés ; la **référence se compose** (composition + type + titrage + couleur + code + suffixe fournisseur), en **semi-automatique** (on choisit les parties, elle reste modifiable) ; **recherche cumulative** par nature, type, titrage partout où un fil se choisit. | — | EX M21, M22 |
| F3 [M] | 30/09 | Pouvoir **supprimer** une valeur de classification — si aucune matière ne la porte ; sinon reclasser ou désactiver (« Portée par N matière(s) »). | — | EX M23 |
| F4 [M] | 02/10 | **Un fil peut servir à plusieurs qualités** ; besoins additionnés par fil ; un ordre peut porter plusieurs qualités, le fil commun sort une fois. | Fait de terrain. | EX M25 ; mémoire « décider au plus près du réel » |
| F5 [N] | 03/10 | **Plusieurs sources (fournisseurs) par matière : non retenu.** Une matière = un fournisseur (prix, devise, délai) ; l'alternative est une autre matière du même **groupe d'équivalence**. | Le plan d'achat et les opportunités comparent déjà les groupes. | CDC §10 ; CONF |
| F6 [N] | 03/10 | **Plusieurs contacts par fournisseur : non retenu** (le principal + Observations). | — | CONF |
| F7 [D] | 03/10 | Une valeur nouvelle de classification se crée **depuis la fiche matière** avec ses champs (libellé, famille…), pas en texte libre. | La référence et la désignation en dépendent. | FC « Décisions » |
| F8 [D] | 03/10 | **Unité d'achat vide = déduite** (palette si bobines/palette connues, sinon bobine, sinon kilo) ; « kg » n'est plus proposé comme unité d'achat. | Même règle que le plan d'achat. | FC « Décisions » |
| F9 [D] | 03/10 | Une matière **en service exige un fournisseur** (C05). « Supprimer » une matière, un fournisseur, une valeur, une qualité, un métier : **grisé si historique** (mouvements, lots, commandes, réceptions, ordres, opérations, dossiers, recettes, fils montés, **pièces jointes**). | Rien ne disparaît en silence. | FC ; `referentiels.py` `USAGES_ARTICLE` |
| F10 [D] | 03/10 | **Verrou optimiste par empreinte** (pas de colonne `version`) pour matière, fournisseur, qualité, métier, étage : refus 409 « modifié(e) entre-temps », bouton « Recharger ». | Deux postes ne s'écrasent pas. | FC « Décisions » — **à remplacer par un champ `version` dans PRO** (PLAN.md) |
| F11 [D] | 08/10 | **Pays choisi dans une liste** (pays saisis + courants, en majuscules, « Autre pays… »). | BELGIUM / Turquie / TURKEY cohabitaient. | FC « Recette » (achats M5) |
| F12 [D] | 03/10 | Délai fournisseur **déclaré** et délai **mesuré** (commande → réception validée, 12 mois) ; ATTENTION au-delà de +20 % sur ≥ 3 livraisons. | — | FC C3 |
| F13 [D] | 03/10 | **Règle des 100 %** : la recette d'un rôle doit faire 100 % (tolérance unique 0,01 point, à l'enregistrement comme dans C01) ; une recette qui **oublie un rôle pesant** (poids au m² > 0 sans fil) est **refusée** ; la sortie vers les machines signale une recette incomplète. | Une recette fausse fausse besoins et coûts. | CDC §5.1 ; db25831, 202d1a0, e44613f |
| F14 [D] | 03/10 | **Recettes versionnées, datées, signées** : chaque enregistrement crée une version ; un poids au m² changé crée aussi une version ; « **Revenir à cette version** » (direction, **motif obligatoire**, tracé) remet parts **et** poids d'un bloc ; la plus ancienne sans auteur se dit « reprise ERP Fil ». | Savoir ce qu'on fabriquait à une date. | CDC §10 ; FC « Recette » (dir. 36) ; 202d1a0 |
| F15 [N] | 03/10 | **Nature « au mètre » d'un rôle non modifiable** : Cuir, Franges, Ruban sont au mètre par constante ; les rôles s'ajoutent et se renomment (direction), pas leur nature ; les huit rôles de base ne se renomment ni ne se suppriment. | Changer ce réglage fausserait besoins et coûts sans rien dire. | CONF ; FC C6 |
| F16 [M] | 17/09 | **Quatre métiers à tisser** : nom choisi, densité, mètres et **pourcentage** par couleur ; poids = mètres × densité × poids de bobine × %. | — | EX M60 |
| F17 [M] | 18/09 | Chaque métier a **6 ou 8 étages de 4,20 m**, réglables machine par machine. | — | EX M61 |
| F18 [M] | 08/10 | **Fils montés : bobines × poids pesé** — bobines = mètres × densité du métier × part du fil ; poids = bobines × **poids de bobine pesé au lot** (le dernier lot **sorti** vers les machines, sinon le dernier **reçu**, sinon le catalogue). Un seul chiffre partout (moteur, API, écrans). | Le Noir 8001 pèse 2,91–2,95 kg au lieu de 3,15 au catalogue (+8 %). | COORD ; 2010f4f ; `moteur.py:678` `fils_en_machine` ; `depot.py:131` |
| F19 [D] | 08/10 | **Montage explicite** : avant d'enregistrer, l'effet sur le stock est annoncé et confirmé (« le stock sur les métiers augmente de 1 395,8 kg (0 → 1 396 kg) ») ; **alerte** si l'on monte plus que ce qui est parti aux machines en 30 jours (retours déduits) ; **trace** au journal (qui, quoi, effet) ; vider un étage se confirme. Au téléphone, **un étage s'écrit seul** (empreinte d'étage). | Le montage ajoutait 2 117 kg au disponible sans contrôle (REC-atelier n° 11). | FC « Recette » ; FC « Décisions » |
| F20 [D] | 08/10 | Métiers nommés « **CRM 1 · Métier 1** », rangés par nom puis code, partout (Envoyer, Montage, bureau). | Listes « 1, 3, 4, 2 » et noms différents. | FC « Recette » |
| F21 [N] | 03/10 | Croissance du plan **par qualité** non retenue (le plan se saisit mois par mois dans Production ; la croissance globale reste). | — | CONF |
| F22 [N] | 03/10 | Table des **motifs** non modifiable : les six motifs **R1–R6** de l'ERP Fil (codes uniques). | Suffisent ; les ajouter passe par le logiciel. | CONF ; REC-achats M14 (R3 en double, corrigé) |
| F23 [D] | 03/10 | Import des matières **par tableur** : modèle = le catalogue actuel, **aperçu avant d'écrire**, rien n'est supprimé, « Appliquer » grisé s'il y a une erreur. | — | CDC §10 |

## 5. Achats : plan, préparation, commandes, approbation, bon fournisseur

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| A1 [M] | 17/09 | **Ne jamais créer un bon sans laisser choisir** les quantités : une fenêtre propose, en kilos **et en palettes**, un champ pour augmenter ou baisser (remplir le conteneur), puis confirmer. « Nouvelle commande » mène à la même préparation. | — | EX M30 ; INVENTAIRE l. 1409 (`/commandes/depuis-plan` ABANDONNÉ) |
| A2 [M] | 17/09 | Le **bon part sans prix** ; le fournisseur **confirme le prix** ; on le saisit ; c'est ce qui **fait bouger le prix** du catalogue et vivre la matrice. | — | EX M31 |
| A3 [M] | 17/09 | Choisir **l'unité de commande** (kilo, palette, fût…) ; l'équivalent en palettes à côté des kilos ; choisir le nombre de palettes ; arrondi au conditionnement. | — | EX M32 |
| A4 [M] | 17/09 | Un bouton **« Nouvelle commande »** ; pouvoir **supprimer** un bon (brouillon) ; un bon **parti ne se supprime plus**, il s'annule et garde son numéro. | — | EX M33 ; FA « Décisions » 5 |
| A5 [D] | 03/10 | **Un bon par devise.** | Montants jamais additionnés entre devises. | CDC §5.3 |
| A6 [M]/[D] | 03/10 | **Approbation** : pas de demande d'achat séparée ; un bon **au-delà d'un seuil** (réglage « Approbation des commandes au-delà de », MAD) doit être approuvé par la direction avant envoi. Bouton « **Envoyer, ou demander l'approbation** » ; la direction « **Approuver et envoyer** » (le numéro est donné, le bon part) ou « **Renvoyer aux achats** » (motif obligatoire, affiché sur le bon). | Contrôle de la dépense par Mohamed. | CDC §2.6 ; FA |
| A7 [N] | 03/10 | **Pas d'état « Approuvée » distinct d'« Envoyée »** : « Approuver et envoyer », le journal garde qui et quand. | — | CONF ; FA rapport 1 n° 7 |
| A8 [M] | 08/10 | **Approbation au montant approuvé et au cours figé** : le montant approuvé est mémorisé ; un bon parti (ou approuvé) dont le montant **augmente** au-delà du seuil, ou le **franchit**, **repasse « À approuver »** (approbation effacée, n° conservé) ; la hausse se mesure **dans la devise du bon, à la version partie** ; le seuil se compare **au cours figé** ; une baisse ne repasse jamais par la direction ; un bon « À approuver » modifié par les achats **revient en brouillon** ; un prix confirmé **plus cher de plus de 5 %** déclenche aussi la règle ; le journal garde le montant avant → après ; **un bon à approuver ne se reçoit pas et ne se solde pas** ; **rouvrir repasse par l'approbation** ; renvoyé par la direction, un bon numéroté revient à sa **version partie**. | Un bon de 6 fûts passé à 20 fûts (235 400 MAD), un bon approuvé passé de 261 872 à 905 379 MAD, un bon de 420 000 MAD reçu sans accord (solder puis rouvrir). | COORD ; REC-achats B1 ; REC-direction 1 ; AUD bloquant 6 ; d68dbb2, b6b751c ; `api/achats.py:246` `_controler_montant` |
| A9 [D] | 08/10 | Montant d'un bon à approuver = **montant estimé** (prix confirmé, sinon catalogue, « estimé, prix du catalogue ») : c'est lui qui déclenche l'approbation et sur lui que la direction décide. | Le Cockpit affichait « 0 MAD ». | FD « Recette » dir. 4 |
| A10 [M] | 30/09 | **Numérotation automatique** ; numéro donné **à l'envoi** (commandes) ou **à la validation** (réceptions, opérations, ordres, lots internes) ; un brouillon affiche « **Brouillon** », sans numéro ; **dossiers et inventaires** ont leur numéro **dès l'ouverture**. Numéros sans trou ni doublon, dans l'ordre des dates, par année. | Un brouillon supprimé ne laisse pas de trou. | EX M65 ; CDC §6.4 ; CONF |
| A11 [D] | 03/10 | Le bon est **daté à l'envoi** ; une date d'envoi passée se saisit, jamais future ni en période close. | — | FA rapport 1 n° 6 |
| A12 [D] | 03/10 | Le **cours se fige à la première confirmation** de prix. | Le cours était refiguré à chaque confirmation partielle. | FA rapport 3 M31 |
| A13 [D] | 08/10 | **Date promise** comptée à l'envoi, **figée** avec les prix ; une date promise passée ne se repousse plus ; la **ponctualité se juge sur la date promise** ; l'**ETA** ne sert qu'à la prévision et au « en retard ». | — | d68dbb2, bcb14b5 |
| A14 [D] | 03/10 | **Jalons constatés jamais dans le futur** (proforma, acompte, embarquée, port, dédouanée, usine) ; seule l'ETA est une attente ; suivi d'expédition seulement après l'envoi ; l'**ETA remplace la date prévue** dans le stock projeté. | — | CDC §2.5 ; FA « Décisions » 3 |
| A15 [D] | 03/10 | **Montant engagé** = bons partis (envoyés + confirmés), au prix confirmé, sinon catalogue ; **reste à recevoir** au même prix. « Prix à confirmer » ne compte qu'une commande **partie**. | — | FA « Décisions » 4 ; FD « Décisions » 5 |
| A16 [D] | 08/10 | Un **brouillon (ou bon à approuver) n'est attendu de personne** : hors du commandé, du stock projeté, du cockpit, de C06, du DPO ; « déjà en préparation » sur la ligne, déduit de la quantité à commander, non reproposé. | — | 30b31c3, bcb14b5 |
| A17 [D] | 08/10 | Plan d'achat : **ce qui ne se consomme plus ne se rachète pas** (matière désactivée, fournisseur désactivé, ni recette du plan ni sortie) ; **budget = somme des lignes affichées** (OK compris) ; sous le gramme une quantité est nulle ; commandes arrivant après le délai mais dans la couverture retranchées. | — | 30b31c3, db25831 |
| A18 [D] | 08/10 | **Tier et urgence selon le statut, pas le montant** : CRITIQUE → Tier 1, URGENT → Tier 2 au moins ; l'urgence d'un fournisseur suit sa pire ligne ; le montant ne fait que « gros montant / à grouper » ; libellés « Urgent · n rupt. · n crit. · n urg. ». | « BC URGENT » ne voulait dire qu'un gros montant. | db25831 ; CMP ; REC-achats G14 ; REC-direction 20 |
| A19 [D] | 08/10 | Couverture cible = **seuil d'alerte en jours** (comparable à la couverture) ; la fiche montre la **« Demande pendant le délai »** (celle que retranche le projeté) : Disponible + Commandé − demande pendant le délai = Projeté. | L'addition affichée ne tombait pas juste. | db25831 ; FE « Recette » G3 ; FD dir. 5 |
| A20 [N] | 03/10 | **Création groupée de bons depuis le plan : non retenue.** | L'acheteur arbitre chaque bon (contact, devise, conteneur) ; un clic par fournisseur mène à sa préparation. | CONF |
| A21 [N] | 03/10 | Le serveur ne peut pas refuser un bon « sans préparation » ; l'écran n'offre pas d'autre chemin. | — | FA rapport 3 M30 |
| A22 [M] | **08/10 19:18 et 20:13** | **Bon de commande fournisseur : une page A4, en anglais, sans aucun prix ni montant** (à l'écran comme dans l'Excel), **sur le papier à en-tête** de l'usine : **raison sociale en rouge avec grande initiale**, **forme juridique et capital**, **siège**, **ville** (et le secteur sous la raison sociale) ; **pied : banques, ICE, R.C, N.I.F, C.N.S.S, patente**. Tailles en points, dates « 08 Oct 2026 », conditionnements traduits ; kilos, et pour cuir/franges/ruban les **mètres indicatifs** (prix au mètre pour un fournisseur qui facture au mètre — dans l'Excel interne). Avertissement à l'écran si la raison sociale n'est pas réglée. Nouveaux réglages « Société » : forme et capital, ville, banques (séparées par « · »), C.N.S.S, patente. | Document remis au fournisseur étranger ; les prix se confirment à part (A2). | COORD ; dbabfc8, 2d588b9, be3a25b ; `parametres.py:120-137` |
| A23 [M] | 08/10 | **Remarques au fournisseur dans une case à part**, seule, sur toute la largeur. | Le « 18 » de BC-2026-0001 avait été tapé dans Observations, collé à « Palettes par conteneur ». | COORD ; 2d588b9 |
| A24 [D] | 08/10 | Excel du bon fournisseur (`/export/commandes/{id}/bon`) : contenance exacte au format français, « Livraison prévue », prix « (EUR / kg) », total, identité de l'usine. | « Bobine de 2 kg » pour 2,5 ; 6720.000000000001. | FA « Recette » G5 |
| A25 [D] | 08/10 | Score fournisseur : **OTIF × 60 + retours 20 (0 % renvoyé = 20, 5 % = 0) + délai 20 (jusqu'à 15 j)**, plafonnés. | L'ancien (OTIF × 40 + (1 − retours) × 40) ne discriminait pas (49/100 à 0 % d'OTIF). | bcb14b5 ; CMP ; REC-direction sugg. 7 |

## 6. Réceptions, quarantaine, réclamations

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| R1r [M] | 30/09 | Une arrivée regroupe **une ou plusieurs commandes, entières ou partielles** ; le bon se dit **par ligne**. | — | EX M40 |
| R2r [M] | 01/10 | **Expliquer** BL, bobines ; fenêtre et champs **larges**. | — | EX M41 |
| R3r [M] | 01/10 | Saisie en **palettes complètes + bobines en plus** ; total calculé ; sert le **poids moyen de bobine**. | — | EX M42 |
| R4r [M] | 01/10 | Suivre **l'évolution du poids des bobines** (hausse/baisse) : poids **mesuré par lot**, courbe par fil, écart au catalogue, alerte. | — | EX M43 |
| R5r [M] | 01/10 | **Onglets** dans Réceptions (« c'est horrible de descendre autant »). | — | EX M45 |
| R6r [M] | 02/10 | **Modifier une réception tant qu'elle n'est pas validée** ; un brouillon rouvert **se remet à jour** seul (reste à livrer et prix recalés à chaque ouverture et à la validation). | — | EX M46, M47 |
| R7r [D] | 03/10 | **On ne reçoit que sur un bon parti** (numéroté) ; un bon en brouillon, à approuver ou annulé est refusé avec la marche à suivre ; sinon « hors commande » (la devise se choisit). | — | FA « Décisions » 1 ; d68dbb2 |
| R8r [D] | 08/10 | **Une réception par devise** : un camion à deux devises donne deux réceptions (même BL, même date), chacune avec **sa** facture dans sa devise ; le serveur refuse le mélange. | Une facture EUR disparaissait, « 5 387 EUR/USD ». | FA « Recette » B2 |
| R9r [D] | 03/10 | **Le poids pesé fait foi** (la bascule donne le net de la ligne). | — | CDC §6.7 |
| R10r [N] | 03/10 | **Pesée palette par palette (brut, tare, net) : non retenue.** | La bascule donne le net ; palettes et bobines donnent le poids réel d'une bobine. | CDC §10 ; CONF |
| R11r [D] | 03/10 | Ligne **« sous réserve » → quarantaine** (en stock, valorisée, non disponible) ; elle ne **solde** la ligne du bon qu'à sa **libération** ; **refusée** → rien en stock. | — | CDC §2.4 ; bcb14b5 |
| R12r [D] | 03/10 | Une **réception entièrement refusée** est gardée comme **trace** du camion renvoyé (numérotée, rien en stock). | — | FA rapport 2 n° 27 |
| R13r [D] | 03/10 | **Une livraison partielle sans BL n'est pas un écart** : la pesée se compare au BL ; sans BL, au reste à livrer seulement quand on pèse au moins ce reste. | — | FA « Décisions » 2 ; 5a59a8d |
| R14r [D] | 08/10 | **Excédent toléré par ligne de bon** (réglage « Excédent de livraison toléré »), sous verrou ; au-delà, la validation est bloquée. | — | bcb14b5, d68dbb2 |
| R15r [D] | 08/10 | **Reçu d'un bon net des retours** au fournisseur (par le lot, au prorata des pesées) ; un retour **rouvre** le bon soldé ; annuler une réception recale les soldes (un bon soldé à la main le reste). | — | bcb14b5, d68dbb2 |
| R16r [D] | 08/10 | **OTIF** : une seule tolérance de date (jours) ; complétude (In-Full) sur les **lignes dues** du bon ; une réception qui ne devait rien n'entre pas dans l'OTIF ; moyenne sur les réceptions notées ; **camion de plusieurs bons : chaque pesée garde son bon, à l'heure si chacun l'est**. | — | bcb14b5, 6143421 ; CMP |
| R17r [D] | 08/10 | **Lot interne** numéroté **à la validation**, jamais pour une ligne refusée, à la suite du plus grand LOT-AAAA-NNNN, sur 4 chiffres. | La série avait des trous et repartait à 1. | FA « Recette » M8 |
| R18r [D] | 08/10 | Annuler une réception demande un **motif**, affiché « annulée par … le … — motif ». | — | FA « Recette » M6 |
| R19r [D] | 03/10 | **Facture complétable après validation** (numéro figé si une ligne est en dossier ; date, montant, échéance corrigeables) ; échéance proposée = date + délai de paiement du fournisseur ; « Marquer réglée » / « Annuler le règlement ». | — | FA rapport 1 n° 1-2 ; 3167707 |
| R20r [D] | 03/10 | **Réclamations** : ouvertes depuis une réception ou un lot (ligne sous réserve ou refusée proposée d'abord), suivi, **issue** (avoir, remplacement, rien) obligatoire pour clore, montant obtenu, pièces jointes ; rouvrir se demande, répondre ne rouvre pas. | — | CDC §10 ; FA ; 3167707 |
| R21r [D] | 08/10 | Étiquette d'un lot en quarantaine : « **QUARANTAINE — NE PAS SORTIR** » ; « Libérer » sur la fiche du lot (achats, commentaire obligatoire). | — | FE « Recette » G19 |

## 7. Importations et coût de revient

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| I1 [M] | 30/09 | Le dossier calcule le **coût de revient** (étude « IMPORTATION 2026 »). | — | EX M50 |
| I2 [M] | 30/09 | Charges directes affectées au dossier ; **répartition à la valeur, pas au poids** (le poids n'est qu'une **option par poste**) ; **TVA 20 %** ; montants globaux saisis **après** la réception. | Usage de la maison. | EX M51 |
| I3 [M] | **08/10 13:41** | **Un dossier d'importation = une facture = une livraison.** Le dossier (numéro de la maison **NN/AA**) s'ouvre **depuis la facture d'une réception** et en prend **toute** la marchandise ; un **second camion de la même facture rejoint son dossier** ; une réception sans facture **attend** qu'on la saisisse ; **seul un dossier d'avant la mise en service se saisit à la main**. Une facture déjà portée par un dossier n'en ouvre pas un second (même dossier repris, même à deux postes : 409 qui nomme le gagnant). Une ligne reçue ne sort pas seule d'un dossier : elle sort avec toute sa réception. | Une commande arrive en plusieurs fois et **c'est à chaque livraison qu'on paie droits, fret et transit**. | COORD ; CDC §5.5 ; 8116063, 6f3a340 |
| I4 [M] | 30/09 | Coût de revient en fin d'année **par fil**, par **caractéristiques** (frisé 2900, polyester 1500), par **plusieurs fils** combinés, par **qualité**, par période ; **filtres multiples** à la fois. | — | EX M52, M54 |
| I5 [M] | 30/09 | **Droits égaux à marchandise comparable** → **taux par code douanier** ; pouvoir saisir un **dossier ancien après coup**. | — | EX M53 |
| I6 [M] | 01/10 | Dossier **dans une fenêtre** ; ce qui compte : **poids** et coût **hors TVA** (achat + charges sauf TVA), **TTC à côté**. | — | EX M55 |
| I7 [M] | 02/10 | Remplir le dossier **par la facture** (je choisis le fournisseur, je tape le numéro, tout se remplit) ; voir **les familles de fil** arrivées. | — | EX M56 |
| I8 [D] | 03/10 | **Clé de répartition par poste** (valeur par défaut ; poids possible) réglée par la direction ; changer la clé recalcule les dossiers **ouverts**, jamais les clos ; dans les clos chaque frais garde sa répartition à part (une seule pièce, réglée ou due). | Un même poste se répartit de la même façon partout. | CDC §2.7 ; FB ; 58f507c |
| I9 [N] | 03/10 | Clé « **aux palettes** » non retenue (les palettes suivent le poids). | — | CONF |
| I10 [N] | 03/10 | **Frais estimés puis réels** non retenus : un frais se corrige sur sa ligne quand la vraie facture arrive ; le dossier reste ouvert jusque-là. | — | CDC §10 ; CONF |
| I11 [D] | 03/10 | **Valeur en douane = achat + fret** (CAF) pour les droits attendus ; écart signalé au-delà de 2 % (≥ 50 MAD) ; « Proposer les droits » seulement tant qu'aucun droit n'est saisi ; droits attendus seulement si **toutes** les matières ont un code actif. | La quittance fait foi. | FB « Décisions » 1-2 ; 6f3a340 |
| I12 [D] | 08/10 | **TVA attendue** = 20 % × (valeur en douane CAF + droits + **TPI 0,25 %**, réglable) ; rien d'attendu sans marchandise ; écart toléré 5 % ; la TVA **n'est pas un coût**. | Comme la douane. | 6f3a340 ; CMP ; CDC §6.7 |
| I13 [D] | 08/10 | Une ligne rattachée entre **au cours figé de son bon** (« cours du bon BC-… ») ; le cours payé à la banque le remplace ; **un cours par devise** (« Appliquer aux EUR ») ; cours à plus de 5 % du cours du jour signalé ; une ligne en MAD n'a pas de cours. | Un même cours appliqué à l'euro et au dollar (+15 % sur un fil). | FB « Recette » G2, dir. 19 |
| I14 [D] | 03/10 | **Clôturer fige le cours** (cours du jour écrit sur une ligne sans cours) ; la clôture est refusée si des frais ne trouvent pas de marchandise ; la question de clôture **énumère les alertes** (cours vides ou disparates, plusieurs fournisseurs, aucun droit, droits ≠ attendus, TVA absente ou ≠ attendue). | — | FB « Décisions » 4 ; FB « Recette » M18 |
| I15 [D] | 08/10 | **Frais non répartis** (sans marchandise) affichés **à part**, partout pareil (Importations, dossier, Analyse, export). | 8,4 M contre 1,9 M entre deux écrans. | FB « Recette » G17 |
| I16 [D] | 08/10 | **Un fournisseur marocain n'a pas de dossier d'importation** (pays Maroc, ou sans pays et facturé en MAD) : hors « à rattacher » ; ouvrir son dossier se confirme. | 104 factures locales en bruit permanent. | FB « Recette » G12 ; 6f3a340 |
| I17 [D] | 08/10 | **Coût d'une qualité pondéré par la recette** (poids du rôle au m² réparti entre ses fils selon leur part, au coût hors TVA) : coût matière / m², coût / kg de tapis, recette couverte. | La moyenne non pondérée ne disait pas ce que coûte la qualité. | FB « Recette » G18 |
| I18 [D] | 08/10 | Poids d'une marchandise de dossier **figé à son entrée** ; le poids additionne des **kilos vrais** ; coût par unité seulement par matière. | SOFIA 367 919 kg à 4,17 au lieu de 49 514 kg à 30,96. | AUD bloquant 8 ; 58f507c |
| I19 [D] | 08/10 | « **Détacher la réception** » : la marchandise attend de nouveau son dossier, **les frais restent** au dossier ; supprimer un dossier dit combien de frais seront perdus ; retirer une marchandise portant un frais affecté à elle seule est refusé. | Droits, fret, transit ont été payés. | 6f3a340 ; FB « Décisions » 5 |
| I20 [D] | 08/10 | Contrôles C35 (frais aberrants > 100 % de la marchandise, réglable), C36 (facture ≠ marchandise reçue pesée × prix, tolérance 2 %), un frais réglé ne redevient jamais dû, un avoir qui rendrait une marchandise négative est refusé. | — | 58f507c, 6f3a340 |
| I21 [D] | 03/10 | Lot inconnu saisi à la main : créé sans stock à la date d'arrivée du dossier ; un stock d'ouverture saisi plus tard sous le même numéro prend ce coût. Documents (DUM, facture, BL, certificat) joignables même à un dossier clos. | — | FB « Décisions » 6, 9 |
| I22 [D] | 03/10 | Le coût de revient par lot nourrit le coût moyen ; un dossier qui change **revalorise les mois non clos** (jamais les clos, cf. V3). | — | CDC §5.5 |

## 8. Production, sorties vers les machines, retours

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| O1 [M] | 01/10 | Un OF ne peut pas avoir **plusieurs dates**, ni des numéros **plus grands avant des plus petits** : **un OF sert une fois** ; numéro et date donnés à la validation ; **un ordre ne se date pas avant le dernier ordre validé** (Valider grisé, annoncé dès le choix de la date ; consigne : dater du dernier ordre et écrire la vraie date en commentaire). | M67. | EX M67 ; FE « Recette » atelier 12 |
| O2 [M] | 01/10 | **Un OF peut porter plusieurs articles et plusieurs qualités** (une palette de rouge, une de noir) ; une qualité une seule fois par ordre. | — | EX M68 |
| O3 [D] | 03/10 | **Proposition FIFO** par recettes et m², lots **disponibles à la date de l'ordre** (hors quarantaine), validation **tout ou rien** ; sortie au QR possible. | — | CDC §5.6 ; 202d1a0 |
| O4 [D] | 08/10 | Proposition et prévu **pertes comprises** (taux de perte des réglages), comme Production & besoins. | Deux « prévus » différents (117,3 contre 119,6 kg). | FE « Recette » atelier 4 |
| O5 [D] | 08/10 | **Prévu de l'ordre et taux de perte figés à la validation** (étape 9) ; ordres anciens recalculés avec la recette de leur jour. | Le passé ne bouge plus. | db25831 |
| O6 [D] | 08/10 | **Une qualité arrêtée ne part plus dans un ordre.** | — | 202d1a0 |
| O7 [D] | 08/10 | Retour des machines : pas daté avant son ordre ; on ne rend **pas plus que ce qui est parti** ; deux lignes du même lot s'additionnent avant comparaison ; « Tout ce qui est parti » arrondit vers le bas. | — | 202d1a0, e44613f |
| O8 [D] | 08/10 | **Annuler un ordre contre-passe aussi tous ses retours** (y compris ceux repris sans document) ; un ordre annulé ne compte nulle part (ni ses sorties, ni ses retours). | 2 793 kg de stock fantôme sur 84 ordres. | AUD bloquant 7 ; 202d1a0 |
| O9 [D] | 08/10 | Kilos et mètres jamais additionnés dans les totaux d'ordres. | — | FE atelier 5 (puis tout en kg, U1) |
| O10 [D] | 03/10 | « **Tout valider** » : dans l'ordre des dates ; le même jour, ce qui apporte la matière (ouverture, transfert, ajustement) avant l'ordre qui la sort, puis les retours ; chaque brouillon dans sa transaction ; seulement ce que le rôle permet. | — | FE « Décisions » |
| O11 [D] | 08/10 | Coefficient de réalisation : **le passé est jugé sur le plan et les recettes de son époque** (versions du plan au journal, versions de recette) ; borné 0,5–1,5 ; un mois ne juge le plan que si l'atelier sortait déjà dans sa première semaine ; fenêtre en mois au demi supérieur (75 j = 3 mois) ; plan révisé au **prorata des jours** ; croissance comptée depuis la saisie de la base. | Plan × 1,5 donnait besoin × 1,03 au lieu de × 1,44. | AUD bloquant 3 ; db25831, 30b31c3 ; `moteur.py:727` |
| O12 [D] | 03/10 | Besoin signalé par l'atelier (« Signaler ») → arrive chez les achats (« Traiter », réponse à l'atelier). | — | CDC §2.6, §10 |
| O13 [D] | 08/10 | La sortie en cours au téléphone est **gardée** (reprise après navigation ou rechargement) ; « Abandonner cette sortie » se confirme. | Saisie perdue par la barre du bas. | FE atelier 3 |

## 9. Valorisation, change, période close

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| V1 [D] | 03/10 | **Coût moyen pondéré glissant (CMUP)** au coût rendu usine ; **une seule implémentation** (`moteur.couts_du_journal`) lue par Valorisation, Cockpit, journal valorisé, inventaire ; à défaut d'achat, prix catalogue. | Deux pages ne disent jamais deux chiffres. | CDC §5.7 ; 5ca0960 |
| V2 [D] | 08/10 | **Une annulation défait l'écriture annulée à son coût** ; un retour au fournisseur sort **au coût d'entrée de son lot** ; une ré-entrée sur stock vide reprend ce qu'elle a coûté ; un coût nul est un coût. | Une réception annulée laissait son prix (×6,7). | AUD bloquant 2 ; 5ca0960, 61027e4 |
| V3 [M] | 08/10 | **Mois clos figé** : la direction clôt (réglage « Période close jusqu'au ») ; plus aucune écriture d'effet antérieur (ni saisie, ni contre-passation) ; **le coût d'une marchandise entrée dans un mois clos ne change plus** (frais, cours, rattachement, retrait, réouverture, suppression de dossier, changement de clé ou de nature d'un poste refusés, 409 avec la marche à suivre) ; corriger = la direction **rouvre** la période (tracé), on saisit, elle referme. | Un mois clos est rendu à la comptabilité ; la valeur au 30/06 changeait après clôture. | COORD ; CDC §5.2 ; AUD bloquant 5 ; f6f3acc ; `securite.py:236` |
| V4 [D] | 08/10 | **Cours de devise figé sur chaque mouvement** à la validation (dossier, sinon commande, sinon cours du jour). | — | 5ca0960 (étape 7) |
| V5 [D] | 08/10 | Une **date de référence passée rejoue** journal, réceptions, commandes (stock, valorisation, cockpit, plan d'achat, contrôles, exports) ; Valorisation à une fin de mois choisie. | — | 5ca0960, a32e662 |
| V6 [D] | 08/10 | XYZ sur les **sorties nettes** des 12 derniers mois clos ; **dormant** = en magasin, ni sorti ni reçu depuis le seuil (dernière sortie **ou** entrée) ; une sortie annulée n'est pas la dernière sortie. | — | 5ca0960 ; CMP |
| V7 [D] | 08/10 | Rotation et jours de stock : stock au CMUP / consommation réelle au CMUP des 12 mois clos. | — | CMP |
| V8 [N] | 03/10 | **Conversion des prix passés au cours de leur date : non retenue** (prix dans la monnaie de la facture, M86 ; le coût rendu prend le cours figé). Pas de table de cours datés : impossible de saisir le cours d'un jour passé. | — | CONF ; FD dir. 30 |
| V9 [?] | 08/10 | Valorisation des importations **à la pesée × prix** (comme l'ERP Fil) plutôt qu'**à la facture** : C36 signale l'écart. | À confirmer. | AUD « reste à Mohamed » 4 |

## 10. Inventaire

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| N1 [D] | 03/10 | Inventaire **figé à l'ouverture** (numéro dès l'ouverture), par magasin, famille (rôle, composition) ou classe ABC ; **mouvements suspendus** sur le magasin inventorié ; comptage par lot (kg, bobines, palettes) ; **second comptage** sur écart (à quatre yeux, signalé) ; justification obligatoire au-delà de la **tolérance** (réglage, 2 %) ; ajustements par lot ; écarts valorisés ; **feuille de comptage à l'aveugle** (la feuille de recomptage montre le théorique) ; **inventaire tournant** (A 30 j, B 90 j, C 365 j). | — | CDC §5.8 ; FE |
| N2 [D] | 08/10 | Inventaire **refusé s'il est daté avant le dernier mouvement** d'un lot qu'il fige ; inventaire ouvert **annoncé dès l'ouverture** de chaque saisie (Valider grisé avec la raison) ; Valider grisé tant qu'un écart hors tolérance n'est pas justifié. | L'usine était à l'arrêt sans le savoir (deux inventaires repris ouverts). | 5ca0960 ; FE atelier 2 ; REC-direction 3 |
| N3 [N] | 08/10 | **Blocage limité aux matières comptées : non fait** (le périmètre n'est pas en base) — un inventaire d'une seule matière suspend tout le magasin. | Changement de modèle. | FE « Recette » atelier 2 — **à reprendre dans PRO** (REC-direction 15 : « comme en usine ») |

## 11. Prix, opportunités, pilotage, contrôles

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| T1 [M] | 17/09 | La feuille **Matrice** (évolution des prix) doit exister. | — | EX M80 |
| T2 [M] | 01/10 | La matrice compare **d'une arrivée à l'autre**, suit le temps comme le poids des bobines, dans **son propre onglet**, en haut. | — | EX M81 |
| T3 [M] | 01/10 | **Quatre ou cinq couleurs** en **pastilles** : prix initial, stable, baisse, légère hausse, **forte hausse** (seuil réglé). | — | EX M82 |
| T4 [M] | 01/10 | Ordre du temps **inversé : les plus récents d'abord**. | — | EX M83 |
| T5 [M] | 01/10 | **Opportunités d'économies** : les expliquer et les refaire justes ; **ne pas comparer deux fournisseurs à des dates différentes** (les matières montent depuis février) ; composition, type, titrage égaux, **même époque**, **coût rendu usine**. | — | EX M84 |
| T6 [D] | 08/10 | Opportunités : **même couleur par défaut** (écran, API, export, Cockpit, Matrice) ; fenêtre réglable 30/45/60/90/180 j. | Rouge comparé à crème : 3,5 M MAD d'« économies » au lieu de 907 k. | FD « Recette » G4 |
| T7 [M] | 01/10 | **Rechercher et comparer deux fils identiques** de fournisseurs différents dans le temps (cases, courbes superposées). | — | EX M85 |
| T8 [M] | 01/10 | Prix dans leur **monnaie d'origine** ; **courbe de la couleur du fil** (rouge → rouge ; à teinte égale, trait différent) ; un axe par devise (« se comparent en tendance, pas en hauteur »). | — | EX M86 ; FD D1 |
| T9 [D] | 03/10 | **Coût rendu usine** = coût hors TVA du dossier si la réception y est, sinon prix × cours figé du bon, sinon cours du jour. | Comparer un fil turc et un fil local une fois dédouanés. | FD « Décisions » 1 |
| T10 [D] | 03/10 | Cockpit : **six indicateurs** (Valeur, Couverture pondérée, À commander, Commandé, Rotation, Contrôles) ; un seul statut par matière (celui du plan d'achat). | — | FD « Décisions » 4 ; FD dir. 6 |
| T11 [D] | 08/10 | Contrôles impossibles par construction (C09, C10, C11, C16, C21) dits « **garantis par la base** », hors de la note (conformes / vérifiés) ; chaque contrôle dit **quoi faire** et **mène au document** ; 38 contrôles (C01…C38). | Honnêteté du score. | 96db9ea, 93fd464 |
| T12 [N] | 03/10 | **Notifications remplacées** par « Ma journée » (Accueil), la carte « À valider » et le **courriel du lundi**. | Ce qui demande une action est là où l'on travaille. | CDC §10 — **PRO reprend les notifications de GMAO PRO (PLAN.md) : compatible, garder aussi l'Accueil** |
| T13 [N] | 03/10 | **API par jeton : non retenue** (exports Excel). | Aucun autre logiciel ne lit Gestion MP. | CDC §10 ; CONF — PRO expose OpenAPI `/api/docs` (lecture humaine) |
| T14 [D] | 03/10 | **Bilan du mois** imprimable ; **courriel du lundi** (même rubriques que le Cockpit) ; **historique des indicateurs** (photo quotidienne, « Photographier aujourd'hui »). Bilan : annulations sur une ligne à part. | — | CDC §5.9 ; FD |
| T15 [N] | 08/10 | Reconstitution de 12 mois d'évolution depuis le journal : **non faite**. | Une photo = moteur complet à une date passée, à décider. | FD dir. 12 |
| T16 [D] | 08/10 | OTIF : une seule définition (moyenne des réceptions, comme Analyse). | Deux définitions sous le même mot (24 % / 26,1 %). | 96db9ea |

## 12. Écrans (exigences générales de Mohamed)

| # | Date | Décision | Source |
|---|---|---|---|
| E1 [M] | 18/09 | **Améliorer la présentation, aligner** ce qui doit l'être. | EX M06 |
| E2 [M] | 30/09 | La recherche du catalogue **ne perd jamais la main** pendant la frappe. | EX M24 |
| E3 [M] | 01/10 | « Arrondir » et « Revenir à la suggestion » **alignés** ; champ des bobines aligné. | EX M34, M44 |
| E4 [M] | 01/10 | **Jamais de longue page** : onglets, tableaux qui défilent dans leur cadre avec en-tête fixe, détail dans une fenêtre. | EX M45, M69 ; mémoire « préférences d'écran » |
| E5 [M] | 01/10 | Recherche qui **affine à la frappe**, plusieurs mots, sans la référence exacte, sur toute la base. | EX M71 |
| E6 [M] | 02/10 | Bouton « Contre-passer » : **expliquer sur place**, **confirmer sur la ligne**. | EX M72 |
| E7 [M] | 02/10 | Depuis la fiche d'un fil, **raccourci vers ses lots non nuls, filtre posé** ; raccourcis partout. | EX M74 |
| E8 [M] | 02/10 | Recherche libre ; **filtres liés** (un fournisseur réduit la liste des fils aux siens) ; filtres réorganisés. | EX M75 |
| E9 [M] | 01/10 | Badge du menu non **rogné**. | EX M76 |
| E10 [M] | 01/10 | Lots et traçabilité : **en-tête fixe**, **date des OF** visible, recherche par fil, par lot ; où sont allés les lots d'un fil, quand. | EX M69, M70 |

Le détail des règles d'écran et de ce que les recettes ont corrigé est dans `REGLES-ECRAN.md`.

## 13. Exploitation

| # | Date | Décision | Raison | Source |
|---|---|---|---|---|
| X1 [D] | 08/10 | **Une seule heure** : serveur et base à l'heure du Maroc (le Mac est juste, +00) ; l'écran se recale sur l'en-tête `X-Heure-Serveur` ; ne jamais lire « aujourd'hui » sur l'horloge du navigateur (Chrome compte le Maroc à +01). | Date du jour, « hier », mois du bilan, échéances justes. | 238729e, 9724d96 ; `lib/heure.ts` |
| X2 [D] | 03/10 | Sauvegarde quotidienne **vérifiée** (14 quotidiennes + 12 mensuelles, manuelles jamais purgées), copie sur un second disque, échec en rouge à la direction, **restauration réversible** (sauvegarde « avant restauration »), sauvegardes **de cette base seulement** (colonne Base, restauration d'une autre base refusée). | M04. | CDC §5.10 ; FD dir. 18 |
| X3 [D] | 08/10 | Le serveur en service tourne sur une **copie figée** de la version, refaite à chaque démarrage, et dit sa version (`/api/sante`). | Travailler dans le projet ne touche pas la production. | 64cd996 |
| X4 [D] | 03/10 | **Pièces jointes** stockées hors base, jamais exécutées dans le navigateur (téléchargement `attachment`), **pas de SVG**, `.exe` refusé ; recopiées à chaque sauvegarde. | — | CDC §6.9 ; d8882d4 ; eb60466 |
| X5 [D] | 03/10 | **QR = une adresse** (`/lot/ID`) : la caméra du téléphone ouvre la fiche du lot, rien à installer ; le QR porte l'adresse réseau détectée, alerte rouge s'il mène à localhost. | — | CDC §2.2 ; FD dir. 14 |
| X6 [D] | 03/10 | Application **installable** sur le téléphone (manifest, service worker qui ne garde que l'enveloppe, jamais les données). | — | `ecran/src/main.tsx` |

## 14. Revirements (seule la dernière décision vaut)

| # | Sujet | Chronologie | Décision finale |
|---|---|---|---|
| R1 | **Unité des matières au mètre** | ERP Fil : cuir/bande « ml », prix au kilo = prix ÷ densité, quantités en kg × densité. → 03/10 : « une matière au mètre se saisit et s'affiche en ml » (FE audit 2 n° 19). → **08/10 14:51** (45c3d2c) : cuir, bande, ruban comptés **en mètres partout**, prix au mètre. → **08/10 19:19** (d2e1e39, décision de Mohamed) : **tout en kilos**, prix au kg ou au mètre, recettes en ml/m², mètres indicatifs ; l'étape de schéma 14 défait la conversion. | U1–U7 |
| R2 | **Fil monté sur les métiers** | ERP Fil (classeur) : ignoré. → **08/10 15:51** (202d1a0) : « une information » (poids et valeur), hors disponible, projeté, valeur, plan d'achat (« déjà sorti, déjà consommé »). → **08/10 16:30** (f33a428) : compte dans le **disponible et le projeté** (pour commander), **valeur à part**. → **08/10 18:20** (169dfdc, décision de Mohamed) : **stock « en machine »**, compté dans le stock global, **sa valeur**, le disponible et le projeté. | U8 |
| R3 | **Numérotation des documents** | Au départ : numéro à la création du brouillon (BC, réception, opération, inventaire, dossier). → 03/10 : à l'envoi / à la validation ; dossiers et inventaires dès l'ouverture. | A10 |
| R4 | **Répartition d'un frais d'un dossier clos quand la clé change** | 03/10 : frais éclatés sur les marchandises à l'ancienne clé (FB « Décisions » 3). → 08/10 (58f507c) : plus d'éclatement ; chaque frais garde sa répartition à part, reste une pièce (étape 13 recolle les morceaux). | I8 |
| R5 | **Opportunités** | Toutes couleurs, fenêtre fixe. → 08/10 : même couleur par défaut, fenêtre réglable. | T6 |
| R6 | **Poids d'un fil monté** | 03/10 : poids catalogue, mesuré « en alerte » seulement (FC « Décisions »). → 08/10 : poids pesé du lot (F18). | F18 |

## 15. Ce qui reste à trancher par Mohamed (au 8 octobre 2026)

| # | Question | État | Source |
|---|---|---|---|
| Q1 [?] | **Prix de la bande (2,5 USD) et du cuir (0,074 USD)** : au kilo (lecture actuelle, cohérente avec les achats de l'année d'essai) ou au mètre (passer la fiche « au mètre », densité connue) — à vérifier sur une facture SOFIA TEXTILE. | C38 ne sonne plus | AUD ; mémoire projet |
| Q2 [?] | **Franges** : 6 qualités (8M, 8S, LP, MN, MP, SH) demandent 0,8 ml/m² sans matière Franges : créer la matière (densité obligatoire) ou mettre ce poids à 0. | C01 bloquant | AUD ; REC-direction |
| Q3 [?] | **Codes douaniers** à saisir (référentiel vide) ; **compte d'envoi du courriel** (variables SMTP) ; **Tailscale** pour la 4G/5G. | Mise en service | AUD ; MISE-EN-SERVICE |
| Q4 [?] | Valorisation des importations **à la facture** plutôt qu'à la pesée. | Pesée × prix ; C36 signale | AUD |
| Q5 [?] | **TPI 0,25 %** dans la TVA attendue : à confirmer par le transitaire ou le comptable (taux réglable). | Réglable | AUD |
| Q6 [?] | Chemin de rattrapage d'une **sortie oubliée de la veille** quand un ordre du jour est déjà validé (M67 l'interdit ; consigne actuelle : dater du dernier ordre, vraie date en commentaire). | Consigne provisoire | REC-atelier n° 12 ; FE |

## 16. Points de tension relevés pour Gestion MP PRO (à arbitrer en conception, sans rouvrir les décisions)

1. **Fil monté compté deux fois en valeur ?** Le fil monté est sorti du magasin par un ordre (sa
   consommation est valorisée dans l'ordre) **et**, depuis U8, compté dans la valeur du stock.
   Le montage **n'a pas d'écriture** au journal (« le vérificateur confronte au journal la seule
   part des magasins », `moteur.py` `valorisation`), et **pas d'historique** (`stock_en_machine` :
   rien à une date passée, donc une valorisation datée n'a pas de stock machine). Recommandation
   PRO : modéliser « en machine » comme un **lieu de stock** (la sortie vers la machine devient un
   transfert, la consommation se constate au tissage ou au démontage), ou à défaut documenter
   explicitement que la valeur « en machine » est une **information de détention** sans écriture.
   La décision de Mohamed (le fil monté est du stock, valorisé, et compte pour commander) reste.
   Les écrans de Gestion MP n'ont pas tous suivi le dernier revirement : la confirmation de montage
   dit encore « ces kilos sont déjà sortis et consommés, ils ne changent ni le stock ni le plan
   d'achat » (`ecran/src/components/referentiels/MetiersTisser.tsx:707`, `pages/atelier/Montage.tsx:340`)
   — à ne pas reprendre (voir `ECRANS.md`, synthèse, point 1).
2. **Inventaire qui bloque tout le magasin** (N3) : la pratique d'usine voudrait ne bloquer que les
   matières comptées ; PRO a le modèle pour le faire (périmètre en base).
3. **Verrou optimiste par empreinte** (F10) → champ `version` dans PRO (PLAN.md).
4. **Notifications** (T12 non retenues) : PRO les reprend de GMAO PRO ; garder aussi « Ma journée ».
5. Rôle « au mètre » des rôles de nomenclature en **constante** (`calcul/modele.py:23`) : dans PRO,
   le lire dans les données (`lineaire`) mais garder le refus de le modifier.
6. Délai **mesuré** affiché mais non utilisé par la prévision (FC « Ce qu'il reste », 3c).
7. Pas de table des **cours datés** (V8) : un cours ne se saisit qu'au jour même.
8. Données de reprise signalées, jamais corrigées : couleurs « Oilve », « Turkoise » ; lot
   GLO260914-884 sur deux matières ; dossier 80/26 (6,55 M MAD de droits sans marchandise) ;
   brouillons repris numérotés (OF-2026-0224, REC-2026-0276) ; utilisateurs « Mohamed / MOHAMED ».
