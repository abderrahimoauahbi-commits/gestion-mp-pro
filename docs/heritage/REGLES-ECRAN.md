# Héritage de Gestion MP — les règles d'écran appliquées, et ce que les recettes ont corrigé

Établi le 8 octobre 2026, en lecture seule, pour Gestion MP PRO. Sources : la règle officielle
`gestion-mp/docs/REGLES-ECRAN.md` (98 lignes, reprise et commentée ici), les exigences de Mohamed
(`EXIGENCES-MOHAMED.md`, M06, M24, M34, M41, M44, M45, M69, M71-M76), la mémoire « préférences
d'écran » (ERP Fil), les trois recettes par clics du 4 octobre (`docs/recette/achats.md`,
`atelier.md`, `direction.md` : 7 bloquants, 54 gênants, 59 mineurs), les rapports de conformité
(`docs/conformite/3-ecrans-exigences.md`, `final-A…E`), l'audit du 8 octobre et les commits.
Références de code relatives à `gestion-mp/ecran/src`.

**Tout ce qui suit est une exigence pour Gestion MP PRO**, réalisée avec le système de
composants de GMAO PRO (voir `AMELIORATIONS-PRO.md`). La dernière section dit ce que PRO doit
faire mieux que Gestion MP sur ces règles.

---

## 1. L'origine : ce que Mohamed a demandé, mot pour mot

| Demande | Date | Devenue la règle |
|---|---|---|
| « Améliorer la présentation, aligner ce qui doit l'être » | 18/09 (M06) | champs d'une rangée alignés, chiffres à droite |
| « La recherche perd la main pendant la frappe » | 30/09 (M24) | la recherche ne perd jamais le focus |
| « Arrondir » et « Revenir à la suggestion » mal alignés | 01/10 (M34) | alignement des boutons d'un pied |
| Expliquer BL, bobines ; **agrandir** la fenêtre et les champs | 01/10 (M41) | fenêtres `large` / `tresLarge`, aide sur place |
| Le champ des bobines n'est pas aligné, il fait monter le champ | 01/10 (M44) | alignement des champs d'une ligne de saisie |
| Des onglets dans Réceptions : « **c'est horrible de descendre autant** » | 01/10 (M45) | jamais de longue page |
| Lots : **en-tête fixe**, date des OF, rechercher par fil, par lot, ne pas descendre sans fin | 01/10 (M69) | tableau qui défile dans son cadre, en-tête fixe |
| Journal : la recherche **affine à mesure qu'on écrit**, sans la référence exacte | 01/10 (M71) | recherche multi-mots à la frappe |
| « Contre-passer » : que signifie ce bouton ? | 02/10 (M72) | infobulle qui explique + confirmation sur la ligne |
| Raccourci de la fiche d'un fil vers **ses lots non nuls, filtre posé** | 02/10 (M74) | liens entre écrans, filtre posé, `?onglet=` |
| Choisir un fournisseur **réduit la liste des fils aux siens** ; recherche libre ; réorganiser les filtres | 02/10 (M75) | filtres liés, recherche en tête des filtres |
| Le badge « 3 » du menu **rogné** | 01/10 (M76) | pastille qui garde la largeur de son nombre (`ajouts.css:495`) |
| Prix dans leur monnaie, **courbe de la couleur du fil**, pastilles d'état | 01/10 (M82, M86) | `lib/teintes.ts`, axe par devise |

Mémoire « préférences d'écran » (ERP Fil, redemandé page après page : Réceptions, Importations,
Prix, Lots, Mouvements) : « ne jamais obliger à faire défiler une longue page ; découper en
onglets ; faire défiler les tableaux dans leur cadre avec l'en-tête fixe ; ouvrir les détails
dans une fenêtre par-dessus la liste ; une recherche qui affine à la frappe (plusieurs mots, sur
toute la base et pas seulement sur ce qui est affiché) ; champs d'une même rangée alignés, assez
larges pour lire ce qu'on tape. » À appliquer **d'emblée** à tout nouvel écran.

## 2. Mise en page

| Règle | Comment Gestion MP l'applique | Exigence PRO |
|---|---|---|
| **Aucune page ne défile à 1366 × 768** (poste de l'usine), ni à 1920 × 1080. Mesure : `document.scrollingElement.scrollHeight == 768`. | Une page = `Page` (en-tête) + éventuellement une rangée d'`Indicateur` + `Onglets` + une `Carte` dont le tableau défile dans son `Cadre`. `Cadre` (`components/ui.tsx:544`) **mesure la hauteur restante** (`useLayoutEffect` : hauteur de la fenêtre − haut du cadre − marges, voisins et paddings dessous ; plancher 200 px) ; dans une fenêtre, hauteur fixe `HAUT.dialogue`. Constantes `HAUT` (`ui.tsx:409`) : `page: max(320px, 100vh − 290px)`, `court: max(240px, 100vh − 470px)`, `dialogue: max(280px, 100vh − 420px)` (repli avant mesure). | Le `DataTable` de PRO prend la hauteur restante de la même façon ; essai automatique (vitest / navigateur) qui mesure `scrollHeight` sur chaque route et chaque onglet en 1366 × 768. |
| **Tableau qui défile dans son cadre, en-tête fixe** (`thead` collant). | classes `table-enveloppe fenetre` | idem |
| **Onglets** pour les vues d'un écran, avec compteur quand il a un sens ; **jamais deux rangées d'onglets empilées** (aplatir) ; une `Bascule` seulement pour 2 à 5 vues d'une même carte. | `Onglets`, `Bascule` (`ui.tsx:234`, `:386`). Analyse : Matrice, Prix payés, Opportunités aplatis en onglets de page (FD « Décisions » 2). Réglages › Paramètres : **familles en liste verticale** à gauche (la bascule de dix familles débordait : Société, Méthode de calcul, Trésorerie non cliquables, 3f8c3ed). | Composant `Tabs` avec compteur ; libellé court + nom complet en infobulle quand la rangée déborde (« Opportunités », « Frais », « Douane », « Courriel »). |
| **Onglet dans l'adresse** : chaque écran à onglets lit et écrit `?onglet=` (`useSearchParams`) ; un document s'ouvre par l'adresse (`?commande=`, `?reception=`, `?ordre=`, `?inventaire=`, `?dossier=`, `?qualite=`, `?matiere=`, `?fournisseur=`, `?metier=`, `?ouvrir=`, `?q=`, `?filtre=retard`, `/lot/ID`). | `useOngletAdresse` (`components/achats/commun.tsx:11`) et équivalents par écran. | Routeur PRO : état d'onglet, de filtre et de fiche dans l'adresse, partout (copier-coller d'un lien = même vue). |
| **Détail dans une fenêtre** (`Dialogue`, `large` ou `tresLarge`), jamais une page de plus ; pas de petite fenêtre de choix : la fenêtre de choix montre ce qu'il faut pour choisir. Deux fenêtres superposées : **Échap ne ferme que celle du dessus** (`ui.tsx:286`). La page dessous ne défile pas. | `Dialogue` | Fenêtres et **tiroirs** de GMAO PRO ; même comportement d'Échap. |
| **Champs d'une rangée alignés**, assez larges ; **chiffres alignés à droite** (`className="num"`). | classes `formulaire`, `rangee`, `filtres`, `table.saisie` | Composant `Form` en grille ; colonnes numériques alignées à droite par type. |
| **Le menu tient sans défiler en 1366 × 768** : libellés courts, détail en infobulle, Analyse et Réglages dans un groupe « Pilotage », compte sur une rangée. | `App.tsx:41-86` ; 0ec3eeb | Barre latérale PRO repliable ; même contrainte. |
| Libellé du menu = titre de la page (« Stock, lots & mouvements » / « Stock » ; « Qualités & recettes » / « Qualités et recettes » ont divergé). | conformité 3 § 3 | Un seul libellé, source unique (registre des routes). |

## 3. Saisie et gestes

| Règle | Détail | Origine |
|---|---|---|
| **Recherche qui affine à la frappe** | Plusieurs mots, dans n'importe quel ordre, **sans accents ni majuscules** (`lib/recherche.ts` : `sansAccents`, `correspond`, `filtrer` — chaque mot doit être quelque part dans la ligne : « rouge 2900 hasi » trouve « PP FRZ-2900 Dtex-Red… » de HASIRCI) ; côté serveur la même règle pour les longues listes (mouvements, coût de revient). Placée dans la rangée `.filtres` sous le titre de la carte. **Ne perd jamais le focus.** | M24, M71 |
| **Filtres liés** | Choisir un fournisseur ne propose plus que ses matières, etc. ; « **Effacer les filtres** » dès qu'il y a au moins deux filtres ; compteur « N critère(s) ». | M75 |
| **Ne jamais perdre une saisie** | Toute fenêtre de saisie passe `sale={modifie}` à `Dialogue` : Échap, fond, × affichent dans la fenêtre « **Des modifications ne sont pas enregistrées. Les abandonner ?** » · « **Non, continuer la saisie** » · « **Oui, abandonner** » (`ui.tsx:327`). Au téléphone : la sortie en cours est gardée (`sessionStorage`) et reprise, « Abandonner cette sortie » se confirme. Changer d'onglet dans une fiche ne perd rien (onglet marqué « • »). | REC-atelier n° 3 ; FC C4 |
| **Geste irréversible confirmé sur place** | Composant `Confirmer` (`ui.tsx:342`) : le bouton devient « *question* · **Non** · **Oui, …** ». **Plus aucun `window.confirm`** (vérifié : 0 occurrence). La question dit l'effet (« Sortir 445,4 kg de Morocco pour FB + MF, daté d'hier 03/10 ? », « Clore ? Aucun droit de douane saisi. ») ; un motif se demande dans la confirmation quand il est exigé (annulation de réception, renvoi aux achats, retour à une version de recette). Restauration d'une sauvegarde : confirmation sur la ligne **puis** fenêtre avec case « J'ai compris » et bouton grisé. | M72 |
| **Le geste dit ce qu'il fait** | Infobulle (`titre`) : envoyer, valider, annuler (contre-passation), solder, supprimer, restaurer… | M72 |
| **Ne pas laisser cliquer pour découvrir un refus** | Un bouton que le serveur refusera est **grisé, avec la raison en infobulle** et, au téléphone, **écrite sous le bouton** (l'infobulle n'existe pas au doigt). Le serveur calcule les blocages d'un brouillon (`blocages` : date, inventaire ouvert, quarantaine, lot épuisé ou insuffisant, magasin désactivé, retour > sorti, ordre plus récent validé, bon à approuver) ; l'écran les affiche (« sera refusé : … ») avant tout clic. Bornes des paramètres contrôlées **à la frappe**. Dates maximales posées dans les champs (jalons constatés ≤ aujourd'hui). | REC-direction 23, 24 ; REC-atelier 22, 24, 25 |
| **Ligne cliquable** | classe `cliquable` sur `<tr>` (curseur + filet au survol) ; plus de `dir-clic` ni `clic`. Une ligne mène à son document (contrôles : référence → stock filtré, n° → commande, dossier, qualité, réception, ordre, fournisseur). | REC-direction 28 |
| **Raccourcis d'un écran à l'autre, filtre posé** | Un n° de document mène au document, un lot à sa fiche (`/lot/ID`), une matière à ses lots (`/stock?onglet=lots&article=ID`), un ordre à sa traçabilité ; chaque tâche de l'Accueil / du Cockpit ouvre le document s'il est seul, la liste filtrée sinon. | M74 ; REC-achats G12 |
| **Numéros** | Commandes, réceptions, opérations, ordres : « **Brouillon** » tant qu'ils n'ont pas de numéro (`numero: null`), jamais « Brouillon n° 331 » ; un bon à approuver s'affiche « À approuver ». Dossiers et inventaires : numéro dès l'ouverture. | M65 ; REC-achats M1 |
| **Unités** | Un prix ou une quantité dit son unité (« USD / kg », « MAD / ml », « kg / bobine »). **Stock toujours en kilos** (cuir, franges, ruban compris) ; leurs mètres **à titre indicatif** à côté (« 14,3 kg ≈ 1 020 ml », `metres`, `kgEtMetres` de `lib/format.ts:80-91`, `kg_par_ml` de l'API). Un prix se saisit au kilo ou au mètre (`unite_prix`), se lit au kilo dans tous les calculs. **Jamais de total qui additionne kg et ml**, ni deux devises. Un prix au mètre garde ses décimales (0,0011 USD / ml, pas 0,00). | décision du 8/10 ; REC-direction 21 |
| **Format des nombres** | Format français (espace des milliers, virgule décimale, « − » unique), pas de « -0 », « −0,0 % », « 0 ml » de reste d'arrondi ; 1 décimale sous 100 kg, 2 sous 10 kg au téléphone ; m² arrondis ; kg entiers quand on commande au kilo ; accords (« 3 palettes », pas « 3,0 Palette »). | REC-achats M3, M13 ; REC-atelier 7, 17, 19 |
| **Export** | Chaque liste importante a « **Exporter en Excel** » (`/api/export/...`), qui respecte les filtres ; les dates en vraies dates, l'unité de chaque ligne. | REC-atelier 8 (Sorties sans export, corrigé) |
| **Heure** | « Aujourd'hui », « hier », mois du bilan, échéances : **heure du serveur** (`lib/heure.ts`, en-tête `X-Heure-Serveur`), jamais l'horloge du navigateur. | 238729e |
| **Chargement honnête** | « Chargement… » tant que la liste se relit, jamais un faux « Cette réception n'existe plus » ; après un enregistrement, le détail montre les chiffres à jour (cache rempli avant d'ouvrir). | REC-achats G6, G7 |
| **Boutons à place fixe** | Les boutons d'un en-tête ne changent pas de place selon l'état (un clic est tombé sur « Valider l'inventaire »). Les gestes destructifs écartés des compteurs. | REC-achats G15 ; REC-atelier 13 |
| **Accessibilité** | Le nom accessible d'un bouton = son libellé visible ; l'infobulle en description (Gestion MP mettait l'infobulle en `title`, qui remplaçait le nom). | REC-achats M10 — **non corrigé dans Gestion MP (`ui.tsx`)** |

## 4. Le téléphone de l'atelier

| Règle | Détail |
|---|---|
| Une tâche par écran, **grands boutons** (tuiles), barre du bas (Accueil, Envoyer, Retour, Lots…). | `pages/atelier/Atelier.tsx` |
| **Cibles tactiles ≥ 44 × 44 px** (« en gants ») : boutons, en-têtes, segments, compteurs, liens-gestes (`ajouts.css:505-520`). Avant correction : « Retirer ce lot » 80 × 20, retour « ‹ » 30 × 36, « Sortir » 61 × 36. |
| Champs de **46 px de haut, police 16 px** (pas de zoom automatique sous iOS) ; clavier numérique (`inputmode=numeric`). |
| Textes de note **≥ 14 px** pour « dispo », « prévu », écarts (12,5 px gris illisible en atelier, suggestion REC-atelier 9). |
| **Aucun débordement horizontal** en 375 × 812 et 360 × 640 ; à 360 × 640 toutes les tuiles visibles. |
| Compteurs **− / +** au pas adapté à la ligne (0,1 / 1 / 10 kg, une bobine, une palette), alignés sur la grille ; changement d'unité qui **dit** l'arrondi. |
| **Bandeau des blocages en tête** d'Envoyer, Retour, Déplacer (inventaire en cours, date trop ancienne, magasin en quarantaine) ; Valider grisé avec la raison écrite sous le bouton. |
| Le résumé et la question de validation rappellent **date (« hier »), magasin, métier**. |
| « **Se déconnecter** » (pas « Sortir », confondu avec une sortie de stock), confirmé, en bas de l'accueil. |
| « Ordres » (pas « Mes ordres ») : la liste est celle de tout l'atelier. |
| `/lot/ID` (QR) ouvre la fiche atelier au téléphone, la page du lot au bureau ; « Lot introuvable » avec en-tête, retour et « Chercher un lot ». |
| Application installable (manifest, icônes 180/192/512, service worker sans données). |

## 5. Vocabulaire unique (officiel, `REGLES-ECRAN.md` § 3)

| Notion | Mot à employer | À ne plus employer |
|---|---|---|
| L'article du catalogue | **matière** ; sa colonne : **Référence** | « fil » comme en-tête, « réf. », « Réf. » |
| Le journal des mouvements de stock | **Mouvements de stock** | « Journal » (réservé à **Journal des actions**, Réglages) |
| Annuler un document validé | **Annuler (contre-passation)** ; étiquette **annulation** | « contre-passer » seul |
| La matière montée sur les métiers | **Sur les métiers** (stock « en machine » dans les textes de valorisation) | « En machine » en en-tête, « Montée sur les métiers » |
| Ce qui est commandé et pas reçu | **Commandé** (en cours) | « BC en cours », « BC » |
| Ce qui reste d'un lot | **Reste** | « Quantité » seule |
| Ce qui reste à livrer d'une commande | **Reste à livrer** ; après réception validée : **Reste après (kg)** | « Reste attendu » |
| L'ordre de fabrication | **ordre** (OF-…) ; menu « Sorties vers les machines » ; téléphone « Envoyer aux machines » | « bon », « bon de sortie » |
| Prévu, consommé | **Prévu par la recette**, **Sorti net**, **Écart** | « Recette », « Réel », « Théorique » |
| L'auteur | **Par** | « Utilisateur », « Auteur », « Saisi par » |
| Date de livraison d'une commande | **Livraison prévue** ; état : **État de livraison** | « souhaitée », deux « Livraison » |
| Quantité du bon de livraison | **Annoncé BL (kg)** | « BL (kg) », « Annoncé » |
| Remarques | **Observations** ; au fournisseur : case à part « remarques au fournisseur » | « Remarque » |
| Poids d'une bobine | **kg / bobine** | « Poids d'une bobine » en colonne |
| Coûts d'un dossier | **Achat**, **Charges hors TVA**, **Coût hors TVA** (= coût de revient), **TVA**, **Coût TTC** | « Frais HT », « Revient », « Décaissé », « DH » |
| Monnaie marocaine | **MAD** | « DH », « dirhams », « MAD — Dirham » |
| Pistes d'économies | **Opportunités d'économies** | « Pistes », « Pistes de négociation » |
| Statut de couverture | **ATTENTION** | « À surveiller » (reste le nom d'un **classement fournisseur**, distinct) |
| Couverture du stock | **Couverture pondérée** | « Couverture moyenne » |
| Le mode d'emploi | **Mode d'emploi** | « Guide » |
| Recette incomplète | **Recettes incomplètes** | « Recettes fausses » |
| Action d'achat | **Préparer la commande** (bouton) | « 📝 Créer BC - … » (texte), émoticônes |
| Urgence du plan d'achat | « Urgent · n rupt. · n crit. · n urg. », « Gros montant », « À grouper » | « BC URGENT », « BC groupé » |

## 6. Ce que les recettes et audits ont corrigé à l'écran (à ne pas réintroduire)

### 6.1 Hauteur et mise en page
| Défaut constaté | Correction |
|---|---|
| Pages qui défilaient à 1366 × 768 : Stock 818 px, Production 783, Besoins 850, Matrice 804, Prix payés 804, Fournisseurs 789, Coût de revient 884, Opportunités 858 (et jusqu'à 1 127 en 1920) ; Valorisation 772, Cockpit › Matières en alerte 778 (plancher de `HAUT.court`, padding de 64 px) | `Cadre` mesure la hauteur restante (c2c9108, bbc916e) ; `HAUT.court` abaissé ; filtres sur une ligne, méthode sur une ligne avec texte entier en infobulle (`.note.une-ligne`) |
| Tableaux trop courts : Commandes 3 lignes visibles (N° sur 3 lignes), Stock › Par matière 2 lignes + défilement horizontal, Mouvements (colonne Motif sur 8 lignes) | N° sur une ligne avec la date dessous, une seule matière « + N », colonnes fondues (lignes de 72 px) |
| Saisie de réception : la rangée des bons ne passait pas à la ligne, tout le corps défilait horizontalement (2 867 px) ; Mode d'emploi toujours déplié | Bons à la ligne, en-tête de largeurs fixes, mode d'emploi ouvert la première fois seulement |
| Réglages › Paramètres : dix familles en bascule qui débordait | liste verticale à gauche, nombre de modifications non enregistrées à côté |
| Liste de suggestions du n° de bon trop étroite | champ de 340 px |
| Écran « Lots à prendre » de 5 800 px (16 fils) au téléphone | suggestion : vue repliée « tout est conforme », Valider collant — **à faire dans PRO** |

### 6.2 Gestes et refus
| Défaut | Correction |
|---|---|
| Inventaire ouvert découvert au clic sur Valider (atelier, réceptions) | annoncé dès l'ouverture de chaque saisie, Valider grisé avec la raison |
| Valider actif malgré « ⚠ sera refusé » | grisé |
| « Remettre 52,4 kg en stock » grisé sans raison, à 15 écrans de la carte fautive | raison rappelée près du bouton (« 1 ligne dépasse ce qui est parti ») |
| « Déplacer » grisé sans dire que le commentaire est obligatoire ; magasin de départ = le premier de la liste | raison écrite ; magasin le plus garni d'abord |
| Sortie d'hier refusée seulement à la validation | annoncée dès la date choisie |
| Jalon futur refusé après Enregistrer | date maximale + bouton grisé |
| Couverture critique ≥ ATTENTION acceptée, bornes contrôlées au clic | refus serveur des désordres + contrôle à la frappe |
| « Enregistrement… » sur le mauvais bouton | libellé d'attente sur le bouton touché |
| Vider un étage, déconnexion : sans confirmation | confirmés |
| Montage qui ajoutait du stock sans le dire | effet annoncé et confirmé, alerte, trace |
| « Sauvegarder maintenant » en erreur 500 muette | message « Sauvegarde faite », liste à jour |
| Pas de message après « Enregistrer et remettre le code » ; identifiant normalisé en silence | message après chaque geste ; l'aide annonce l'identifiant retenu |

### 6.3 Liens et navigation
| Défaut | Correction |
|---|---|
| Fiche du lot jamais ouverte au bureau (route `/lot/:id` perdue) | route corrigée (bbc916e) |
| Écran réservé → renvoi silencieux vers `/atelier` étiré sur 1366 px | accueil bureau + message « L'écran demandé (…) est réservé à un autre rôle » (`App.tsx:206`) |
| « Faire un retour » au bureau ouvrait l'écran téléphone | fenêtre `RetourBureau` |
| Tâches « 8 commandes en retard » → liste non filtrée ; chaque arrivée → la même liste | `/commandes?filtre=retard`, document ouvert s'il est seul |
| Lignes de contrôle non cliquables | chaque ligne mène à son document |
| RET-…, ordres servis : pas des liens | liens |
| Impression dans le même onglet, « Retour » ne rouvre pas la fenêtre | **non corrigé** (REC-achats M9) — PRO : nouvel onglet ou retour à la fenêtre d'origine |
| `?matiere=nouvelle` après création | `?matiere=<n°>` |

### 6.4 Chiffres affichés
| Défaut | Correction |
|---|---|
| « Stock projeté = disponible + commandé − sorties prévues » faux à l'écran (61 504 au lieu de 88 981) | colonne « Demande pendant le délai » : l'addition affichée tombe juste |
| Deux statuts contradictoires (statut classeur / statut), « aucune matière critique » contredit | un seul statut ; l'autre en infobulle |
| kg et ml additionnés (253,2 = 251,3 kg + 1,9 ml) ; −92,1 kg = −27,8 kg − 64,3 ml | tout en kg (décision du 8/10) |
| Bande « 500 USD/kg » dans la recette, matrice sans unité | prix dans son unité (« 2,50 USD / ml »), colonne « Prix en » |
| « 0 USD / 0 MAD » pour un bon à approuver | montant estimé, « estimé, prix du catalogue » |
| Charges 8,4 M (Importations) / 1,9 M (Analyse) | frais non répartis à part, partout |
| Bilan du mois : sorties négatives | annulations sur leur ligne |
| Traçabilité : annulation comptée en entrée, « Entré 2 775 » pour 2 675 reçus | « Entré » = reçu ; retours en déduction du sorti ; annulations marquées |
| « × 2,50 kg » affiché, 2,49524 calculé ; rouge dans la tolérance | poids réel à 4 décimales ; rouge réservé au hors tolérance |
| « sorti » / « net » non dits ; « 9 kg » pour 8,5 | « sorti net » / « à sortir » sous le chiffre ; 1 décimale sous 100 kg |
| Prix « 2,8 / kg » sans devise ; « 7 795,20 » sans devise | « 2,8 USD / kg » |
| Sauvegardes « il y a 0,0 heure(s) », triées par nom | « il y a 40 min / 3 h », tri par date, colonne Base |
| Journal : « 9.5 », « 20 % → 25 % » en décimales | format français ; colonne « Avant » |
| « Brouillon / Brouillon », « Quarantaine quarantaine » | un seul libellé |

## 7. Ce qui n'a jamais été garanti par un essai dans Gestion MP (à combler dans PRO)

Le rapport de conformité 3 (3 octobre) l'a écrit : « aucun essai d'écran n'en garantit une
seule » ; au 8 octobre, `ecran/` n'a **aucun fichier de test** (pas de vitest ni Playwright) ; la
seule garde automatique est `npm run controle` (eslint, règles des hooks React, ajoutée après la
page blanche de « Retour des machines », cec5a72). Les hauteurs ont été **mesurées à la main**
par les recetteurs (`scrollHeight`). Exigences d'essais pour PRO :

1. Pour chaque route et chaque onglet, par rôle : la page ne défile pas en 1366 × 768 ; aucun
   débordement horizontal en 375 et 360 px (atelier).
2. La recherche garde le focus pendant la frappe (M24) ; une recherche « mot1 mot2 » sans accents
   trouve la ligne.
3. Les boutons d'un pied sont alignés (M34) ; la pastille du menu n'est pas rognée (M76).
4. Aucun `window.confirm` / `alert` (contrôle statique) ; toute fenêtre de saisie protège sa saisie.
5. L'alimentation ne voit aucun prix ni montant dans **le DOM** (en plus de l'essai serveur).
6. Les cibles tactiles de l'atelier font ≥ 44 × 44 px.
7. Tout bouton grisé a une raison (attribut lu par l'essai).
8. Le vocabulaire interdit (§ 5, colonne de droite) n'apparaît dans aucun libellé (contrôle
   statique des chaînes).
