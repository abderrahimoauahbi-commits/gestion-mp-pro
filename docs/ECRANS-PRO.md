# Gestion MP PRO — écrans

L'arborescence des écrans de Gestion MP PRO par rôle, le système de composants, puis la
correspondance de **chaque** écran, onglet, fenêtre, geste et document de Gestion MP
(`docs/heritage/ECRANS.md` : 38 écrans, ≈ 160 onglets et sous-vues, ≈ 48 fenêtres, 4 documents,
≈ 500 gestes, 209 anomalies). Les routes d'API citées sont celles de `API-PRO.md` (sans le
préfixe `/api`) ; les composants, ceux du § 3 ci-dessous ; les règles transverses, celles de
`ARCHITECTURE.md` § 10 et de `docs/heritage/REGLES-ECRAN.md`.

Sommaire : 1. Principes · 2. Arborescence par rôle · 3. Système de composants · 4. Registre des
routes d'écran · 5. Arbitrages de l'architecte · 6. Correspondance, parties 1 à 8 · 7. Comptes.

---

## 1. Principes (exigences de Mohamed, rendues vérifiables)

| Règle | Mise en œuvre | Essai |
|---|---|---|
| Aucune page ne défile à 1366 × 768 (ni 1920 × 1080) | `Page` = `EnTete` + `Indicateurs` + `Onglets` + `Carte` ; le `DataTable` prend la hauteur restante (`Cadre`) | recette navigateur : `scrollHeight` de chaque route × onglet × rôle |
| Tableau qui défile dans son cadre, en-tête fixe | `Cadre` (mesure `useLayoutEffect`, plancher 200 px ; hauteur fixe en fenêtre) | vitest + recette |
| Onglets plutôt que longues pages ; jamais deux rangées | `Onglets` (compteur, libellé court + infobulle), `Bascule` pour 2 à 6 vues d'une carte (6 : la classification, lot UNITES-TITRAGE) | contrôle statique |
| Détail dans une fenêtre par-dessus la liste, adresse stable | `useFicheAdresse` : `/commandes/12` = liste + `Fenetre` | vitest (fermer → liste, filtres gardés) |
| Recherche à la frappe, multi-mots, sans accents, sur toute la base, garde le focus | `Recherche`, `Colonne.recherche`, `?q=` au serveur | vitest (focus, « frise rouge » trouve « IMP FRISÉ ROUGE ») |
| Filtres liés, « Effacer les filtres » dès deux | `Filtres` | vitest |
| Champs d'une rangée alignés, chiffres à droite | `Grille` de `Form`, `Colonne.droite` | contrôle visuel de recette |
| Ne jamais perdre une saisie | `Fenetre({sale})`, `beforeunload`, saisie gardée à l'atelier | vitest (Échap demande) |
| Geste irréversible confirmé sur la ligne ; jamais `window.confirm` | `Confirmer` | eslint `no-restricted-syntax` + essai |
| Ne pas laisser cliquer pour découvrir un refus | `Bouton({manque, blocages})` ; `blocages` calculés par le serveur | essai : tout bouton grisé a une raison |
| Vocabulaire unique | REGLES-ECRAN § 5 ; libellés dans `aide.json` et les composants | contrôle statique des chaînes interdites |
| Aucun prix ni montant chez l'alimentation | filtre serveur + écrans sans colonnes de prix pour L | vitest (DOM) + recette (texte monétaire) |
| Cibles tactiles ≥ 44 × 44 px à l'atelier ; aucun débordement à 360 et 375 px | composants `atelier/` | recette navigateur |
| Heure de l'usine | `lib/heure.ts` (`X-Heure-Serveur`) | vitest |

---

## 2. Arborescence par rôle

### 2.1 Menu du bureau (barre latérale, une seule source : `routes.ts`)

| Groupe | Entrée (libellé = titre de la page) | Route | D | A | L | T |
|---|---|---|---|---|---|---|
| Tous les jours | Ma journée | `/accueil` | — | ✓ | ✓ | — |
| | Cockpit | `/cockpit` | ✓ | — | — | — |
| | Stock, lots & mouvements | `/stock` | ✓ | ✓ | ✓ (sans prix) | — |
| | Sorties vers les machines | `/sorties` | ✓ | ✓ (lecture) | ✓ | — |
| | Écran atelier (téléphone) | `/atelier` | ✓ | — | ✓ | — |
| Achats | Plan d'achat | `/plan-achat` | ✓ | ✓ | — | — |
| | Commandes | `/commandes` | ✓ | ✓ | — | — |
| | Réceptions | `/receptions` | ✓ | ✓ | — | — |
| | Importations & coût de revient | `/importations` | ✓ | ✓ | — | — |
| Stock | Inventaire | `/inventaire` | ✓ | ✓ | — | — |
| | Ouvertures, transferts, ajustements | `/operations` | ✓ | ✓ | ✓ (transferts, retours machine) | — |
| Référentiels | Matières, classification, fournisseurs | `/catalogue` | ✓ | ✓ | ✓ (matières, lecture sans prix) | — |
| | Qualités et recettes | `/qualites` | ✓ | ✓ (lecture) | ✓ (lecture sans coût) | — |
| | Métiers à tisser | `/metiers` | ✓ | ✓ (lecture) | ✓ (fils montés) | — |
| | Production & besoins | `/production` | ✓ | ✓ | ✓ | — |
| Pilotage | Analyse | `/analyse` | ✓ | ✓ | — | — |
| | Réglages | `/reglages` | ✓ | ✓ (devises ; autres onglets en lecture) | — | — |
| | Administration | `/administration` | ✓ | — | — | ✓ |
| Aide | Mode d'emploi | `/aide` | ✓ | ✓ | ✓ | ✓ |

En-tête (56 px) : fil d'Ariane, `RechercheGlobale` (C), `Cloche` (tous), `MenuCompte` (Mon
compte `/compte`, Aide de l'écran, Signaler un besoin, Se déconnecter — confirmé). Pastilles :
Stock = ruptures + critiques ; Analyse = contrôles en anomalie (et lignes en infobulle) ;
Commandes = à approuver (D) ; Réceptions = brouillons. `BandeauServeur` (D, T) : sauvegarde en
défaut, base en retard, base d'essai, HTTPS absent sur le réseau.

Arrivée : D → `/cockpit` ; A → `/accueil` ; L → `/atelier` au téléphone, `/accueil` au bureau ;
T → `/administration`. `/` mène à l'arrivée du rôle.

### 2.2 Écrans, onglets, fiches

| Écran (route) | Onglets `?onglet=` | Fiches en fenêtre (adresse stable) | Documents, exports |
|---|---|---|---|
| Ma journée `/accueil` | — (cartes À faire, À valider, Arrivées 7 j, Besoins signalés) | `/accueil?signalement=ID` | — |
| Cockpit `/cockpit` | `faire`, `alertes`, `ensemble`, `evolution`, `economies` | `/cockpit?signalement=ID` | bilan du mois |
| Stock `/stock` | `matieres`, `lots`, `mouvements`, `ordres`, `a-valider` | `/stock/matieres/:id`, `/lots/:id`, `/tracabilite?…` | étiquettes ; exports mouvements, lots, ordres |
| Sorties `/sorties` | `valide`, `brouillon`, `annule` | `/ordres/:id`, `/ordres/nouveau`, `/ordres/:id/retour` | export ordres |
| Production `/production` | `plan`, `glissant`, `realise`, `besoins` | `/production/besoins/:matiereId` | export production |
| Plan d'achat `/plan-achat` | `fournisseurs`, `references` | `/plan-achat/preparer/:fournisseurId` | export plan d'achat, pilotage |
| Commandes `/commandes` | `brouillon`, `a_approuver`, `envoyee`, `confirmee`, `clos` (+ `filtre=retard`) | `/commandes/:id?onglet=lignes\|prix\|expedition\|receptions\|approbation\|pieces\|historique`, `/commandes/nouvelle?fournisseur=ID` | bon fournisseur HTML + Excel ; export commandes |
| Réceptions `/receptions` | `brouillon`, `validee`, `annulee`, `reclamations`, `bobines`, `pesees` | `/receptions/:id`, `/receptions/nouvelle[?brouillon=ID]`, `/reclamations/:id`, `/reclamations/nouvelle` | exports réceptions, pesées, bobines |
| Importations `/importations` | `ouverts`, `clos` (bascule « Clos · Annulés »), `rattacher` | `/dossiers/:id?onglet=…`, `/dossiers/nouveau` | export dossiers |
| Inventaire `/inventaire` | `cours`, `passes` (« Inventaires clos », filtre d'état) | `/inventaires/:id?onglet=lots\|pieces\|historique`, `/inventaires/nouveau` | feuille de comptage / recomptage ; exports |
| Opérations `/operations` | `ouverture`, `transfert`, `ajustement`, `retour_fournisseur`, `retour_machine` | `/operations/:id`, `/operations/nouvelle?type=` | export opérations |
| Catalogue `/catalogue` | `matieres`, `classification` (`&liste=`), `fournisseurs` | `/matieres/:id`, `/matieres/nouvelle`, `/fournisseurs/:id`, `/fournisseurs/nouveau`, `/catalogue/tableur` | exports matières, fiches fournisseurs |
| Qualités `/qualites` | `qualites`, `nomenclature` | `/qualites/:id?onglet=recette\|plan\|versions\|historique`, `/qualites/nouvelle` | export qualités |
| Métiers `/metiers` | — | `/metiers/:id?onglet=fils\|reglages\|historique`, `/metiers/nouveau` | export métiers |
| Analyse `/analyse` | `valorisation`, `matrice`, `historique`, `opportunites`, `fournisseurs`, `revient`, `echeancier`, `controles`, `production` | fenêtres : comparaison des prix, détail d'un contrôle (`&controle=Cxx`) | exports par onglet ; bilan |
| Réglages `/reglages` | `parametres` (familles en liste verticale), `devises`, `magasins`, `postes`, `codes`, `periode` | `&poste=ID`, `&code=ID`, `&magasin=ID` | — |
| Administration `/administration` | `comptes`, `appareils`, `sauvegardes`, `journal`, `courriel`, `serveur`, `telephone`, `technique`, `reprise` (miroir de Gestion MP : état pour D, T ; « Rafraîchir le miroir » pour D, confirmation en fenêtre) | `&compte=ID` | export journal ; QR d'accès |
| Mode d'emploi `/aide` | `regles`, `roles`, `pas`, `calculs`, `analyse`, `ecrans`, `telephone` | — | (NOTICE.md générée) |
| Mon compte `/compte` | — | — | — |

### 2.3 Atelier au téléphone (hors coque, PWA)

`/atelier` (tuiles : Envoyer aux machines, Retour des machines, Ordres, Trouver un lot, Déplacer
un lot, Monter un fil, Signaler un besoin ; bandeau des blocages ; « Se déconnecter » confirmé) ·
`/atelier/envoyer` (`?ordre=ID`) en deux temps (la demande ; lots à prendre, vue repliée « tout
est conforme », `ResumeValidation` collant) · `/atelier/ordres` · `/atelier/ordres/:id` ·
`/atelier/retour` (`?ordre=ID`) · `/atelier/chercher` (caméra `ScanQR`) · `/atelier/lots/:id` ·
`/atelier/deplacer` (`?lot=ID`, mise en quarantaine permise, libération non) ·
`/atelier/montage` (`?metier=ID&etage=N`) · `/atelier/signaler`. Barre du bas : Accueil,
Envoyer, Retour, Lots. QR `/lot/:id` : téléphone et rôle L → `/atelier/lots/:id` ; sinon `/lots/:id`.

---

## 3. Système de composants (`frontend/src/composants/`)

Chaque composant : `Nom.tsx`, `Nom.module.css` (jetons seulement), `Nom.test.tsx`. Repris de
GMAO PRO pour la forme, corrigé des dix arbitrages (ARCHITECTURE § 10.2).

| Famille | Composant | Contrat (props essentielles) | Comportement exigé | Essais vitest |
|---|---|---|---|---|
| coque | `Coque` | `children` | barre latérale repliable, en-tête 56 px, `<main>` ; tient en 1366 × 768 | menu tient sans défiler |
| | `BarreLaterale` | menu dérivé de `routes.ts` + rôle | pastilles qui gardent leur largeur (M76) | une entrée par droit |
| | `EnTete` | `titre, fil[], actions, aide` | fil d'Ariane obligatoire au second niveau ; « ? » ouvre l'aide de l'écran ; boutons à place fixe | présence du fil |
| | `RechercheGlobale` | — | `GET recherche`, flèches + Entrée, résultats filtrés par rôle, jamais de prix | navigation clavier |
| | `Cloche` | — | `GET notifications`, non lues, « tout marquer comme lu », ouvre le lien | lecture |
| | `MenuCompte` | — | Mon compte, Aide, Signaler un besoin, Se déconnecter (confirmé) | — |
| | `BandeauServeur` | `contexte.alerte_serveur` | rouge si sauvegarde en défaut | — |
| | `EcranReserve` | `chemin` | « L'écran demandé (…) est réservé à un autre rôle : vous êtes revenu à votre accueil. » | garde |
| mise en page | `Page`, `Carte`, `Grille`, `Definitions`, `Indicateurs` | | une rangée de KPI ; six sur une rangée au Cockpit | |
| | `Onglets` | `onglets[{cle, libelle, court?, compte?}]`, `?onglet=` | un seul niveau ; libellé court + nom complet en infobulle ; « • » si saisie non enregistrée | adresse |
| | `Bascule` | 2 à 6 vues | dans une carte | |
| | `Fenetre` | `taille: normale\|large\|tresLarge, tiroir?, sale?, pied?, onFermer` | pile ; Échap ferme celle du dessus ; clic voile / × / Échap avec `sale` → « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » ; la page dessous ne défile pas | garde de saisie, pile |
| | `FenetreConfirmation` | `titre, texte, motif?, caseJaiCompris?` | lecture longue seulement (restauration, clôture de dossier, clôture de période) | — |
| tableaux | `DataTable<T>` | `colonnes: Colonne<T>[]` (`cle, titre, rendu, valeur, recherche, droite, unite, exporte, largeur, lien`), `lignes`, `filtres`, `pied`, `cliquable`, `chargerPlus?` | tri numérique puis naturel (`localeCompare` numérique) ; compteur « n / total » ; ligne cliquable (curseur, filet) ; pied de totaux (jamais kg + ml, jamais deux devises) | tri, recherche, filtres, export |
| | `Cadre` | `hauteur: page\|court\|fenetre` | hauteur restante mesurée, en-tête collant | mesure |
| | `Filtres` | `[{libelle, valeur(l)}]` | liés ; « Effacer les filtres » dès 2 ; « N critère(s) » | liaison |
| | `Recherche` | `valeur, onChange` | garde le focus ; multi-mots sans accents | focus |
| | `ExportExcel` | `route, parametres` | envoie onglet, recherche, filtres ; « Exporter en Excel » | paramètres |
| | `ChargerPlus` | `Page[T]` | « Charger les 500 suivants » | — |
| saisie | `Champ`, `Saisie`, `Zone`, `Interrupteur`, `Segments`, `Puces` | | étiquette = nom accessible ; aide en description | accessibilité |
| | `Nombre` | `valeur, decimales, min, max, unite` | saisie à la française, virgule acceptée, bornes contrôlées à la frappe | formats |
| | `Quantite` | `kg, unite: kg\|bobine\|palette, poidsBobine, bobinesPalette` | convertit en kg, dit l'arrondi (« 3 bobines = 7,49 kg ») | conversions (P3) |
| | `Prix` | `valeur, devise, unite: kg\|ml, densite` | affiche l'équivalent au kg | — |
| | `DateChamp` | `min (après clôture), max (aujourd'hui serveur)` | jalons constatés ≤ aujourd'hui | bornes |
| | `Selecteur` | `options[{id, titre, sous, groupe}]` | recherche à la frappe, clavier (reprise de `ChoixRecherche`) | clavier |
| | `SelecteurMatiere` | filtres composition, type, titrage, couleur, fournisseur | recherche cumulative (M22) | — |
| | `SelecteurLot` | `matiere, date, magasin` | lots présents à la date, FIFO, quarantaine exclue | — |
| | `Bouton` | `manque?, blocages?, occupe?, titre?, variante` | grisé avec raison (infobulle au bureau, texte dessous au téléphone) ; libellé d'attente sur le bouton touché | raison obligatoire |
| | `Confirmer` | `question, oui, motif?: facultatif\|exige, onOui` | « question · Non · Oui, … » sur place ; motif saisi dans la confirmation | sur place |
| | `Blocages` | `blocages[]` | « Sera refusé : … » | — |
| retour | `Messages` | `dire(texte, ton)` | toasts ; refus du serveur affichés tels quels | — |
| | `Chargement`, `Vide`, `Note`, `Erreur` | | « Chargement… » honnête ; « Pas de réseau » distinct d'une liste vide | — |
| | `Badge` | `statut` | table unique statut → libellé → ton (`lib/statuts.ts`) ; jamais « Brouillon / Brouillon » | table complète |
| | `Kpi` | `titre, valeur, unite, formule (obligatoire), lien?, ton?` | bulle « ? » avec la formule (`aide.json`) ; filet de couleur + texte | formule présente |
| | `KgEtMetres`, `Montant`, `Pastille`, `Progression` | | « 14,3 kg ≈ 1 020 ml » ; devise toujours dite | formats |
| graphiques | `Barres`, `Courbes`, `BarresH`, `Sparkline` | séries, axes | SVG maison ; axe par devise ; couleur du fil (`teintes.ts`) ; trait différent à teinte égale | rendu |
| documents | `PiecesJointes` | `objet, id` | ajouter, télécharger, retirer (confirmé) ; types et taille annoncés | — |
| | `Historique` | `objet, id` | journal de la fiche, différences avant → après lisibles (formats français) | — |
| | `LienDocument` | `genre, id, numero` | n° → fiche ; « Brouillon » sans numéro | — |
| | `BoutonImprimer` | `route` | ouvre le document dans un nouvel onglet | — |
| atelier | `EcranAtelier` | `titre, retour, enTete, pied` | gabarit d'écran téléphone | 360 px |
| | `Tuile`, `Compteur` (pas 0,1/1/10 kg, bobine, palette), `SegmentsTactiles`, `BarreBas`, `BandeauBlocages`, `ResumeValidation` (collant), `ScanQR` | | cibles ≥ 44 px, champs 46 px / 16 px, `inputmode=numeric` | cibles |

Bibliothèque `lib/` : `api.ts` (fetch, en-tête anti-falsification, erreurs `{detail, code}` → `Refus`),
`requetes.ts` (TanStack : relance sur statut, invalidation globale), `session.tsx` (`/contexte`),
`droits.ts` (menu et `permis` depuis `routes.ts`), `heure.ts`, `format.ts` (règle unique,
ARCHITECTURE § 9.3), `recherche.ts`, `unites.ts`, `teintes.ts`, `adresse.ts` (`useOngletAdresse`,
`useFicheAdresse`, `useFiltresAdresse`), `statuts.ts`, `types.gen.ts` (généré), `types.ts`.

---

## 4. Registre des routes d'écran (`frontend/src/routes.ts`)

```ts
type Ecran = {
  chemin: string            // '/commandes/:id'
  titre: string             // = libellé du menu (une seule source)
  groupe?: Groupe           // entrée de menu si présent
  roles: Role[]             // garde de route et menu
  aide: CleAide             // section de aide.json (essai : chacune existe)
  onglets?: { cle: string; libelle: string; court?: string; roles?: Role[] }[]
  parent?: string           // fil d'Ariane, fiche en fenêtre sur la liste parente
  atelier?: true            // branche hors coque
  page: () => Promise<{ default: ComponentType }>   // chargement à la demande
}
```

Essais : chaque entrée de menu d'un rôle est permise (`permis`) ; chaque écran a son aide ; chaque
appel d'API d'un écran vise une route de l'OpenAPI permise au rôle (matrice) ; chaque route
d'écran est ouverte par la recette navigateur.

---

## 5. Arbitrages de l'architecte sur les parties ci-dessous

Les huit parties du § 6 ont été rédigées en parallèle sur un contrat commun ; là où un rédacteur
a tranché seul, la décision ci-dessous l'emporte.

| # | Sujet | Proposé dans la partie | Décision |
|---|---|---|---|
| E1 | Code de l'alimentation | exactement 4 chiffres (partie 1) | **retenu** (ARCHITECTURE T10) |
| E2 | Bilan du mois et fil sur les métiers | compté à toute date par l'historique des montages (partie 1) | d'abord non retenu (parité) ; **décidé depuis par Mohamed (le fil monté est du stock) et construit par D8** : PRO compte le fil monté à toute date (rejeu de `montage_evenement`) dans la valorisation, le cockpit, les contrôles et le bilan — Gestion MP ne le compte qu'au jour même ; écart voulu, déclaré à la parité et à la comparaison |
| E3 | Case « Envoyer avec nos prix du catalogue, à confirmer » | supprimée (partie 4) | **gardée et rendue effective** (`prix_catalogue_a_confirmer`, API 154 = `sans_prix=false` de Gestion MP) : prix du catalogue posés, non confirmés ; décochée (défaut) = bon sans prix. L'onglet « Prix » reste réservé aux bons partis |
| E4 | Contrôle d'ordre Tier 1 ≥ Tier 2 ≥ Tier 3 (partie 8) | proposé | d'abord non retenu (écart de parité) ; **construit depuis** : Tier 3 < Tier 2 et Tier 1 ≥ Tier 2 font partie des 7 contrôles d'ordre des réglages (Réglages › Paramètres) |
| E5 | Qualité arrêtée : rôle sans matière accepté avec avertissement (partie 8) | proposé | **non retenu** : règle de Gestion MP gardée (recette refusée si un rôle pesant n'a pas de fil, F13) ; l'écran grise « Enregistrer » avec la raison |
| E6 | `seuil_bc_urgent` | gardé, lecture seule « sans effet, gardé pour mémoire » (partie 8) | retenu |
| E7 | « Score — ATTENTION » contre classement « À surveiller » | gardé tel quel (partie 8) | retenu ; signalé à Mohamed (deux noms pour deux notions, REGLES-ECRAN § 5) |
| E8 | Libellé de C29 | corrigé (partie 8) | retenu (texte seulement) |
| E9 | Poids nuls d'une qualité | ne s'enregistrent plus (partie 8) | retenu (renommer un rôle n'est plus bloqué par un poids à 0) |
| E10 | Création + validation en une transaction (`valider: true`) | parties 2, 3, 6 | retenu (API-PRO § 1.24) |
| E11 | Abandon d'inventaire, annulation de dossier : motif | exigé (parties 5, 6) | retenu ; de même pour l'annulation d'un inventaire validé (Gestion MP corrigé, étape 17 ; API-PRO 245) |
| E12 | « Théorique » gardé dans l'inventaire | partie 6 | retenu (mot du comptage, exception documentée au vocabulaire) |
| E13 | Achats et postes de frais / codes douaniers | lecture pour A (partie 5) | retenu (API 34, 38) |
| E14 | Pièces jointes d'un dossier clos | on joint, on ne retire plus (partie 5) | retenu |
| E15 | Frais réglé | ni poste, ni montant, ni ligne modifiables sans annuler le règlement (partie 5) | retenu (I20) |
| E16 | Papier à en-tête du bon anglais | partie 4 | **révisé le 8 octobre** : le bon fournisseur est en anglais jusque dans l'en-tête et le pied du papier (« HEAD OFFICE », « BANKS ») ; les documents français gardent « SIÈGE SOCIAL » et « BANQUES » (`documents/rendu.rendre(…, langue="en")`, lot D9) |
| E17 | Noms de colonnes cités dans les parties | | les noms font foi dans `MODELE-DONNEES.md` (`commande_decision`, `solde_origine`, `annulation_motif`…) |

---

## 6. Correspondance Gestion MP → PRO

Les huit parties suivent l'ordre de `heritage/ECRANS.md` ; chacune est une section de niveau 2.
Abréviations : D, A, L, T (rôles), C = D, A, L ; « anom. » = anomalie numérotée de la partie GMP.


## Partie 1 — Coque, composants partagés, connexion et installation, accueil, cockpit, mode d'emploi, page du lot

Source : `ECRANS.md` lignes 84-1249. Rôles : D direction · A achats · L alimentation · T administrateur
technique · C = D, A, L. Les numéros « P1-n » renvoient aux anomalies de la Partie 1 de `ECRANS.md`
(liste complète en fin de partie).

**Texte unique « Sur les métiers »** (clé `aide.json` `sur_les_metiers`, repris mot pour mot partout où le
fil monté est expliqué, Partie 1 comme Partie 2) : « Sur les métiers : le fil monté, pas encore tissé. C'est
du stock : il compte dans le stock, sa valeur, le disponible et le stock projeté. Monter n'écrit aucun
mouvement : le fil a déjà été sorti par un ordre. » Aucune autre formulation (notamment celle de GMP qui
présentait ces kilos comme consommés et sans effet sur le stock) n'est reprise.

**Arrivée après connexion** (registre `routes.ts`, fonction `accueilDe`) : D → `/cockpit` ; A → `/accueil` ;
L au bureau → `/accueil` ; L au téléphone → `/atelier` ; T → `/administration`. `/` mène toujours à
l'accueil du rôle (plus de `/` → `/sorties` pour L, P1-4).

---

### Socle technique — `frontend/index.html`, manifeste, service worker, client de requêtes

Gestion MP : `index.html`, `public/manifest.webmanifest`, `public/sw.js`, `main.tsx` → PRO :
`frontend/index.html`, `frontend/public/manifest.webmanifest`, `frontend/public/sw.js`, `frontend/src/main.tsx`
(TanStack Query), tous rôles.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `<title>Gestion MP</title>` unique, `lang=fr` | titre « {titre de la route} — Gestion MP » posé par `Page` depuis `routes.ts` | un titre par écran (onglets du navigateur, historique) |
| `theme-color #17497f`, `apple-mobile-web-app-*`, icônes `/icone.svg`, `/icone-180.png`, `viewport-fit=cover` | identique | — |
| Manifeste : name « Gestion MP — matières premières », short_name « Gestion MP », start_url `/`, `standalone`, fonds `#f4f6f8` / `#17497f`, `fr`, icônes svg/192/512 | identique ; `start_url` `/` (→ accueil du rôle) | — |
| SW minimal : `skipWaiting`, `clients.claim`, aucun cache ; principe « un stock d'hier … pire qu'un message pas de réseau » | identique (aucun cache de données) | enregistré réellement : accès en HTTPS (Caddy, nom local) → contexte sécurisé (P1-2) |
| Serveur : `sw.js` et manifeste `Cache-Control: no-cache` | identique | — |
| React Query : `refetchOnWindowFocus`, `staleTime` 15 s, 1 nouvel essai sauf 401/403/404 testés sur le **message** | TanStack Query mêmes réglages ; pas de nouvel essai si `erreur.statut` ∈ {401, 403, 404, 409, 422} | test sur le statut (P1-1) ; invalidation globale après chaque mutation |
| `BrowserRouter`, `StrictMode`, `index.css` + `ajouts.css` | routeur unique alimenté par `routes.ts` ; jetons CSS uniques (`frontend/src/styles/jetons.css`) | une seule feuille de jetons |

**Gestes** : aucun.

---

### Briques `lib/` — correspondance vers `frontend/src/lib/`

Gestion MP : `ecran/src/lib/*` → PRO : `frontend/src/lib/*`, tous rôles.

**Ce qu'on voit (fonctions et règles)**

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| **api.ts** : `/api{chemin}`, `credentials same-origin`, cookie `gestion_mp_session`, en-tête `X-Gestion-MP: 1`, JSON | `lib/api.ts` : mêmes règles (cookie `HttpOnly; Secure; SameSite=Strict`, en-tête anti-CSRF gardé) | — |
| `api.get/post/put/supprimer` | `api.get/post/put/supprimer` + `api.envoyerFichier` (multipart) | multipart centralisé (PiecesJointes) |
| Réseau injoignable : « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). » | identique (statut 0) | — |
| Erreur = `detail` texte, ou `msg` joints « · », sinon « Erreur {code} » ; `ErreurApi(message, statut)` | `ErreurApi(message, statut, champs?, blocages?)` | champs fautifs et blocages portés (surlignage `Champ`) |
| 401 hors `/connexion` → événement `gestion-mp:session-perdue` | même événement, **avec le motif** du serveur | affiché sur la Connexion (P1-6) |
| 204 → `undefined` | identique | — |
| `X-Heure-Serveur` → `recalerHorloge` ; `heureServeur()` « 13:20:46 » | identique (`lib/heure.ts`) | — |
| `qs(params)` (saute `''`, `null`, `undefined`, `false`) | identique | — |
| `ouvrir(chemin)` → `window.open('/api'+chemin)` (bon, étiquettes, bilan) | `BoutonImprimer` (→ `/api/documents/...`) et `ExportExcel` (→ `/api/export/...`) | deux composants nommés |
| `messageErreur(e)` | identique | — |
| Serveur : écriture sans en-tête → 403 « Requête refusée : elle ne vient pas de l'écran de Gestion MP. » ; 422 traduits « champ : message » (table de 13 traductions) | identique côté serveur | — |
| 401 « Connectez-vous pour continuer. » / « Ce compte n'est plus actif. » | identiques, affichés à la Connexion | P1-6 |
| **session.tsx** : `Role` = direction, achats, alimentation ; `Compte {id, identifiant, nom, role, role_libelle, email, actif, vu_le}` ; `peut(...roles)` (D passe partout) ; `deconnecter`, `rafraichir` ; erreur « useSession hors de la session » | `lib/session.tsx` : `Role` + `technique` (T) ; `peut` : D passe partout **sauf** routes T réservées (comptes, appareils techniques) ; `T` ne passe sur aucune donnée métier | rôle T ; `rafraichir` utilisé après `PUT moi` (P1-24) |
| **heure.ts** : décalage serveur − poste ; `maintenant()`, `jourIso(d)`, `jourDansN(n)` ; raison (Maroc +01) | `lib/heure.ts` identique ; `DateChamp` lit `max` = jour serveur | — |
| **format.ts** : `nombre(v,d)` (insécable U+00A0, d=0/1/2 exact, d≥3 jusqu'à 4, vide « — ») | `lib/format.ts` `nombre(v, d, dMax?)` : d exact, `dMax` explicite | P1-23 (plus de « 3 → 4 » implicite) |
| `montant`, `montantCourt` (« 17,4 M MAD », exact en infobulle), `montants` (devises jamais additionnées, « · ») | identiques ; rendus par `Montant` | — |
| `classementLisible` (« À surveiller » → « ATTENTION ») | identique | — |
| `prixUnite` (2 déc., 4 si < 0,1), `metres`, `kgEtMetres` (« 14,3 kg ≈ 1 020 ml ») | identiques ; `KgEtMetres` composant | partout où un kg de cuir/franges/ruban s'affiche (P1-14) |
| `pourcent`, `part`, `jours` (« 45 j »), `date`, `horodatage`, `aujourdhui` | identiques | — |
| `tonStatut` (RUPTURE→rupture … NON CONSOMM→neutre, sinon ok), `tonTier` | table unique `Badge` (statut → libellé → ton), `tonStatut` la lit | doublons supprimés (P2-8) |
| Statuts de stock « ⚫ RUPTURE », « 🔴 CRITIQUE », « 🟠 URGENT », « 🟡 ATTENTION », « 🟢 OK », « ⚪ NON CONSOMMÉE » ; en alerte = 4 premiers ; action « 📝 Créer BC - {fournisseur} » / « — » | le serveur rend des **codes** (`statut`, `statut_couverture` ∈ `RUPTURE`, `CRITIQUE`, `URGENT`, `ATTENTION`, `OK`, `NON_CONSOMMEE` ; `action` ∈ `CREER_BC`, `AUCUNE`) ; l'écran les traduit (`lib/statuts.ts › cleStock`) en libellés sans émoji (« RUPTURE »… « NON CONSOMMÉE ») + `Pastille` de couleur ; même règle « en alerte » | pas d'émoji (vocabulaire) ; codes au serveur (lot RESTES3) |
| Couleurs de ton (ok `#146c44`, attention `#8d5c07`, urgent `#a1560b`, critique `#a92c2c`, rupture `#2d3440`, neutre, accent `#1f5fa8`) ; filet 3 px | jetons CSS identiques ; `Kpi` garde le filet | — |
| **recherche.ts** : `sansAccents` (NFD), `correspond` (chaque mot, ordre libre), `filtrer(liste, recherche, champs)` | `lib/recherche.ts` identique ; `Colonne.recherche` ; même règle serveur `?q=` (`unaccent`, tous les mots) | serveur sans accents (P2-20) |
| **donnees.ts** : `useMagasins`, `useFournisseurs`, `useArticles`, `useDevises`, `useMetiers`, `useQualites` (clé par liste, 60 s) ; structures `Magasin`, `Fournisseur`, `Article`, `Devise`, `Metier`, `QualiteResume`, `Solde` ; `ROLES_AU_METRE` | `lib/donnees.ts` : `useMagasins` (GET magasins), `useFournisseurs` (GET fournisseurs, résumé pour L), `useMatieres` (GET matieres, prix masqués), `useDevises` (GET devises, D,A), `useMetiers`, `useQualites` ; types générés depuis OpenAPI (`Matiere`, `Lot`…) ; `ROLES_AU_METRE` lu du serveur (`GET contexte`) | `/articles` → `/matieres`, `/soldes` → `/lots` ; types générés, plus recopiés |
| **commandes.ts** : hors suivi, `enRetard`, `prixAConfirmer`, `brouillon`, `aApprouver`, `ongletCommande`, `numeroOuBrouillon`, `montantMad` (estimé), `versCommandes` | `lib/commandes.ts` lit des champs **calculés par le serveur** (`en_retard`, `prix_a_confirmer`, `hors_suivi`, `montant_mad_estime`) ; `versCommandes` : 1 commande → `/commandes/{id}`, plusieurs → `/commandes?onglet=…[&filtre=retard]` | une seule définition, aussi pour `?filtre=retard` de Commandes (P1-11) ; adresse stable (A5) |
| Statuts commande « Brouillon », « À approuver », « Envoyée », « Confirmée », « Soldée », « Annulée » | table `Badge` | — |
| **teintes.ts** : 31 motifs couleur → teinte ; palette de repli 6 couleurs ; traits `stylesDesFils` ; palette direction 8 couleurs | `lib/teintes.ts` identique ; `Courbes` (couleur du fil) et `Barres` (palette 8) | une palette par usage, nommée |

**Gestes** : aucun.

---

### Coque de bureau — toutes les routes du bureau

Gestion MP : `App.tsx` (`Bureau`, menu, pastilles, gardes) → PRO : `Coque`, `BarreLaterale`, `EnTete`,
`RechercheGlobale`, `Cloche`, `MenuCompte`, `BandeauServeur`, `EcranReserve` ; registre `routes.ts`, tous rôles.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/moi` (clé `moi`, sans nouvel essai, 60 s) ; « Un instant — chargement : Gestion MP… » | GET `moi` + GET `contexte` (rôle, réglages d'affichage, compteurs du menu, base d'essai) ; `Chargement` | contexte en un appel |
| Pas de compte ou session perdue → Connexion ; après connexion : cache vidé, `/moi` relu | identique → `/connexion?retour={adresse}` | l'adresse demandée est rouverte après connexion |
| Chargement paresseux « … l'écran… » | `Chargement` | — |
| Routage : `/atelier/*` si `peut('alimentation')` ; `/lot/:id` au téléphone → `/atelier/lot/:id` ; `/` → `/sorties` (L bureau) ou accueil ; `*` → coque | `/atelier/*` hors coque (L ; D peut ouvrir) ; `/lot/:id` : téléphone **et** rôle L → `/atelier/lots/:id`, sinon `/lots/:id` ; `/` → accueil du rôle | P1-3, P1-4 |
| `accueilDe` : D `/cockpit`, L `/atelier` (téléphone) ou `/accueil`, A `/accueil` ; téléphone = `max-width: 700px` | idem + T `/administration` ; téléphone = `(max-width: 700px) and (pointer: coarse)` | « étroit **et** tactile » comme le dit le commentaire |
| Menu à gauche ; < 1080 px repli derrière « ☰ Menu » (290 px, 85 vw), refermé à chaque navigation | `BarreLaterale` repliable (bouton du `EnTete`), repliée sous 1080 px, refermée à la navigation ; état replié mémorisé (localStorage) | — |
| Marque « Gestion MP » / « Matières premières » | en tête de `BarreLaterale` | — |
| Bas du menu : nom, `role_libelle`, « Se déconnecter » | `MenuCompte` (en-tête 56 px) : nom + rôle ; Mon compte, Aide, Signaler un besoin, Se déconnecter | regroupé à droite de l'en-tête |
| Menu par rôle (6 groupes, 18 liens, infobulle = détail ou libellé) ; groupe vide masqué ; lien actif filet bleu ; tient en 1366 × 768 | menu généré par `routes.ts` (titre = libellé, rôles) ; mêmes groupes : Tous les jours (Accueil [A,L], Cockpit [D], Stock, lots & mouvements [C], Sorties vers les machines [C], Écran atelier [L, D]) · Achats (Plan d'achat, Commandes, Réceptions, Importations & coût de revient [D,A]) · Stock (Inventaire [D,A], Ouvertures, transferts, ajustements [D,A,L]) · Référentiels (Matières, classification, fournisseurs [D,A,L lecture]; Qualités et recettes [C]; Métiers à tisser [C]; Production & besoins [C]) · Pilotage (Analyse [D,A], Réglages [D,A]) · Administration [T,D] · Aide (Mode d'emploi [tous]) | **D n'a pas l'Accueil** (gardé) ; L voit Opérations (transferts, retours machine) et le catalogue des matières en lecture ; A voit Réglages (devises en écriture, reste en lecture) (P1-28) ; T ne voit que Administration, Mode d'emploi, Mon compte |
| Pastille « Stock » = ruptures + critiques (GET `/cockpit`, 180 s, **non lue pour L**) ; pastille « Analyse » = anomalies, le lien mène alors à `?onglet=controles` | `Pastille` sur `BarreLaterale`, compteurs de GET `contexte` (relu 180 s et après chaque mutation) : Stock = « alerte rouge » (ruptures + critiques) pour C ; Analyse = anomalies (D,A) → `/analyse?onglet=controles` | L voit aussi la pastille Stock (aucun prix) ; définition nommée unique (P1-9) |
| Style pastille rouge, mini 20 px, chiffres tabulaires | `Pastille` ton critique | — |
| — | `Cloche` (tous, T compris) : GET `notifications` ; liste, « Tout marquer lu » ; une notification ouvre le document (adresse stable) | nouveau (A10) |
| — | `RechercheGlobale` (C) : GET `recherche?q=` (matières, lots, ordres, commandes, réceptions, fournisseurs, filtrés par rôle) | nouveau |
| — | `BandeauServeur` : sauvegarde en défaut (D,T), schéma en retard, « base d'essai » | nouveau |
| — | `EnTete({titre, fil, actions, aide})` : fil d'Ariane, bouton « ? » (entrée `aide.json` de l'écran) | nouveau (A7) |
| `garde(roles)` → accueil du rôle, état `refuse` | garde du registre `routes.ts` | une seule source rôles/menu/garde |
| Gardes : `/accueil` aucune ; `/cockpit` D ; `/stock`, `/production`, `/guide`, `/lot/:id` aucune ; `/sorties`, `/metiers` A,L ; achats : 9 écrans ; `/reglages` A (devises seules, hors menu) | gardes = rôles du registre (cf. contrat) ; `/accueil` A,L ; T refusé sur tout écran métier | gardes = menu (P1-28) |
| Chemin inconnu → accueil sans message | `EcranReserve` variante « L'adresse demandée ({chemin}) n'existe pas : vous êtes revenu à votre accueil. » | message |
| « L'écran demandé ({chemin}) est réservé à un autre rôle : vous êtes revenu à votre accueil. » (jusqu'à la navigation suivante) | `EcranReserve` même texte | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Se déconnecter » | tous | POST `deconnexion` | aucune au bureau ; quoi qu'il arrive retour à `/connexion`, cache vidé | dans `MenuCompte` |
| « ☰ Menu » | tous | — | — | bouton de repli de `BarreLaterale` |
| (lien de menu) | selon registre | — | — | — |
| — | tous | GET `notifications`, POST `notifications/{id}/lue`, POST `notifications/lues` | — | `Cloche` (nouveau) |
| — | C | GET `recherche?q=` | — | `RechercheGlobale` (nouveau) |
| — | C | POST `signalements` | — | `MenuCompte` › Signaler un besoin (fenêtre : référence, texte, urgence) |

---

### Composants partagés — correspondance des 20 composants GMP

Gestion MP : `components/ui.tsx`, `components/direction/commun.tsx`, `components/PiecesJointes.tsx` → PRO :
`frontend/src/composants/`.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| 1 `Page` (h1 titre, sous-titre, actions) | `Page` + `EnTete({titre, fil, actions, aide})` | fil d'Ariane, bouton « ? », titre d'onglet |
| 2 `Carte` (titre h2, `extra`, corps) | `Carte` | — |
| 3 `Indicateur` (libellé, valeur, détail, ton, infobulle) ; sans ombre en carte | `Kpi({valeur, unite, formule, lien})` dans `Indicateurs` (rangée) ; `Formule` en infobulle | formule toujours disponible ; cliquable s'il a un écran (P1-27) |
| 4 `Etiquette` (tons ok … accent) | `Badge` (table unique statut → libellé → ton) | libellés centralisés |
| 5 `Bouton` (principal, neutre, danger ; `titre`, `disabled`) | `Bouton({manque, blocages, occupe, titre})` | raison du grisé toujours dite (P2-11) |
| 6 `Champ` (libellé, aide, `large`, `duo`) | `Champ` (dans `Form`) + `Grille` | champs alignés ; erreur serveur sous le champ |
| 7 `ChampNombre` (milliers hors saisie, vide à 0, sélection totale, molette neutre, `echelle`, `pas`) | `Nombre` (fr) ; `Quantite` (kg/bobines/palettes → kg, dit l'arrondi) ; `Prix` (devise + kg/ml) | mêmes comportements de saisie |
| 8 `Message` (erreur/succès/info) | `Messages` (toasts persistants jusqu'à fermeture pour erreur) ; `Note` (info) ; `Erreur` (page) | succès visibles même si la fenêtre se ferme (P2-14) |
| 9 `Chargement` « Un instant — chargement : {quoi}… » | `Chargement` même texte | — |
| 10 `BarreRecherche` « Rechercher… » | `Recherche` (garde le focus, A6) | — |
| 11 `Onglets` (compteur dès `compte != null`) | `Onglets` (compteur, libellé court + infobulle, `?onglet=`, `useOngletAdresse`) | onglet toujours dans l'adresse |
| 12 `Dialogue` (×, Échap haut de pile, fond, `sale`, blocage du défilement, `large`/`tres-large`) | `Fenetre({taille: normale|large|tresLarge, tiroir, sale, pied})` + pile ; garde « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » | garde aussi sur les boutons « Fermer »/« Annuler » et à la navigation (P1-22, P2-10) ; libellé unique (P1-7) |
| 13 `Confirmer` (question sur place, « Non », `oui`) | `Confirmer` (motif facultatif ou exigé, « Oui » grisé et `occupe` pendant l'envoi, erreur rattrapée → `Messages`) ; `FenetreConfirmation` pour lecture longue | P1-21 |
| 14 `Bascule` (2 à 6 vues d'une carte) | `Bascule` (vue dans l'adresse `?vue=`) | P2-5 |
| 15 `HAUT` (page/court/dialogue) et `Cadre` (hauteur mesurée, ≥ 200 px, en-tête fixe) | `Cadre` (hauteur restante mesurée, en-tête fixe) ; `HAUT` supprimé | — |
| 16 `useEnvoi` (occupe, messages, effacer) | `useMutation` TanStack enveloppé dans `Bouton`/`Confirmer` (`occupe`), `Messages`, invalidation globale | — |
| 17 `ChoixRecherche` (« Taper pour chercher… », 60 résultats, Entrée si un seul, Échap, « Rien ne correspond. ») | `Selecteur` (clavier ↑↓, Entrée) ; `SelecteurMatiere` (composition/type/titrage/couleur/fournisseur cumulés) ; `SelecteurLot` | recherche sur champs cachés |
| 18 `Vide` | `Vide` (dit pourquoi c'est vide) | — |
| 19 Briques direction : `HAUT_DIALOGUE`, `COULEURS_SERIES`, `signe`, `MOIS_NOMS`, `moisLisible`, `LigneVide`, `trier`, `pluriel` | `signe`, `moisLisible` (« sept. 2026 »), `pluriel` → `lib/format.ts` ; `LigneVide` → `DataTable` (vide intégré) ; `trier` → `DataTable` (tri par en-tête) ; `COULEURS_SERIES` → `lib/teintes.ts` | code mort supprimé (`HAUT_DIALOGUE`, `MOIS_NOMS`, P1-24) |
| 20 `PiecesJointes` | `PiecesJointes` (section suivante) | — |
| (cité, inexistant) `Tableau` | `DataTable<T>` (colonnes `Colonne<T>` : `rendu`, `valeur`, `recherche`, `droite`, `unite`, `exporte`, `largeur`, `lien`), `Filtres` (liés), `ExportExcel`, `ChargerPlus`, pied de totaux | composant réel (P1-25) |

**Gestes (mécanismes partagés)**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| × / Échap / clic sur le fond (Dialogue) | tous | — | si `sale` : bandeau d'abandon | Échap ferme la fenêtre du dessus |
| « Non, continuer la saisie » | tous | — | — | — |
| « Oui, abandonner » | tous | — | — | — |
| bouton de `Confirmer` → « Non » / « Oui, … » | selon geste | selon geste | « Oui » grisé pendant l'envoi | erreur rattrapée |

---

### Pièces jointes — composant `PiecesJointes` (fiches commande, réception, réclamation, dossier, inventaire, fournisseur, matière)

Gestion MP : `components/PiecesJointes.tsx` → PRO : `PiecesJointes` (onglet ou carte de la fiche), D, A
(L ne voit jamais de pièce).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Objets `dossier, reception, commande, reclamation, inventaire, fournisseur, article` | mêmes, `article` → `matiere` | — |
| GET `/pieces/{objet}/{id}` (clé partagée avec `NombrePieces`) | GET `pieces?objet=&id=` ; compteur d'onglet | — |
| « Joindre un document… » (« Envoi… ») + note « ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » | identique | — |
| Zone de dépôt (pointillé bleu 2 px) ; ignorée en lecture seule | identique | — |
| Sélecteur multiple `.pdf, image/*, .txt, .csv, .xlsx, .xls, .ods, .docx, .doc, .odt, .zip` | liste explicite des images « à points » (`.jpg .jpeg .png .gif .webp .heic .heif .tif .tiff .bmp`) | SVG refusé avant envoi (P1-20) |
| Colonnes Document (lien de téléchargement, infobulle « Télécharger le document »), Genre, Taille (o/Ko/Mo), Par, Joint le, « Retirer » | `DataTable` mêmes colonnes ; `Cadre` | — |
| Ordre serveur (plus ancien d'abord), pas de recherche/filtre/tri | identique (liste courte) | — |
| Vide « Aucun document joint. » | `Vide` même texte | — |
| Lecture seule (L ; DetailDossier/Inventaire hors achats ; matière non modifiable) | `lectureSeule` selon droit d'écriture de la fiche | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Joindre un document… » / glisser-déposer | D, A | POST `pieces` (multipart `fichier`, `objet`, `id`), un fichier après l'autre | 20 Mo vérifiés avant envoi : « « {nom} » est trop lourd : 20 Mo au plus. » ; refus serveur (« Type de fichier refusé… », « Fichier trop lourd… », « Document inconnu. ») | liste relue après **chaque** fichier ; bilan « n joints, m refusés : … » (P1-20) |
| clic sur le nom | D, A | GET `pieces/{id}/fichier` | « Pièce introuvable. » | — |
| « Retirer » | D, A | DELETE `pieces/{id}` | `Confirmer` « Retirer ce document ? » · « Non » · « Oui, retirer » (danger) ; infobulle « Retirer « {nom} » de la liste (le retrait est tracé) » | fichier gardé sur disque, journal « pièce retirée » |

---

### Connexion — `/connexion`

Gestion MP : `pages/Connexion.tsx` (toute adresse sans session) → PRO : `/connexion` (hors coque), public.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/etat` → `{installe, societe}` ; GET `/visages` (comptes actifs, triés par nom) | GET `etat` (public) ; GET `visages` (public **sur poste local ou appareil enrôlé seulement**) | ailleurs : champ identifiant + code (P1-26) |
| « Un instant — chargement : Gestion MP… » | `Chargement` | — |
| `/etat` en erreur : « Le serveur ne répond pas. Vérifiez le réseau, puis rechargez la page. » ; seul `installe=false` mène à l'installation | identique ; `installe=false` → `/installation` | adresse distincte |
| h1 « Gestion MP » ; note « {société ou « Matières premières »} — touchez votre nom, puis tapez votre code. » | identique | — |
| Grille de visages (nom gras, rôle) ; choisi `actif` | identique ; T compris | — |
| Champ « Code d'{nom} » / « Code de {nom} » (voyelle ou h), mot de passe, `current-password`, focus, clavier numérique pour L | identique | — |
| Entrée automatique à 4 chiffres (L) | gardée : le code L est **exactement 4 chiffres** (exigé à la création, POST `utilisateurs/{id}/code`) | plus d'échec garanti à 5+ chiffres (P1-5) |
| Message d'erreur rouge ; « Entrer » (« Connexion… », grisé si code vide/envoi) | `Erreur` sous le champ ; `Bouton({manque:['code']})` | — |
| — | bandeau du motif de retour : « Votre session a expiré : reconnectez-vous. » / « Ce compte n'est plus actif. » | P1-6 |
| Pied « Code oublié : la direction le remet à zéro dans Réglages › Comptes. » | « Code oublié : la direction ou l'administrateur le remet à zéro dans Administration › Comptes. » | onglet déplacé |
| Changer de visage efface code et erreur | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Toucher un nom | public | — | — | — |
| « Entrer » (Entrée, 4 chiffres L) | public | POST `connexion {identifiant, secret}` | « Identifiant ou code incorrect. » (code vidé) ; 5 échecs : « Trop d'essais : patientez {n} secondes. » (30 s doublant jusqu'à 15 min) | retour à l'adresse demandée (`?retour=`) |

---

### Première installation — `/installation`

Gestion MP : même adresse quand aucun compte → PRO : `/installation` (hors coque), public tant que `installe=false`.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| h1 « Bienvenue dans Gestion MP » ; note « Premier lancement : créez le compte de la direction… (Réglages › Comptes). » | identique, « (Administration › Comptes) » | onglet déplacé |
| Société (≤ 160, → `nom_entreprise`) ; Votre nom (≥ 2, ≤ 80, exemple « MAZARI ») ; Identifiant (aide « ce qui vous désigne à la connexion », exemple « mazari », vide → nom en minuscules, points) ; Code (aide « 8 caractères au moins ») | `Form` : `Saisie` ×3, `Saisie` mot de passe ; mêmes contrôles | — |
| Pas de garde d'abandon | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Créer le compte et entrer » | public | POST `installation {societe, nom, identifiant, secret}` | `Bouton({manque})` nom < 2 / code < 8 ; « Gestion MP est déjà installé : connectez-vous. » (409) ; 422 traduits | entrée au `/cockpit` ; journal « installation » |

---

### Installation et accès (hors écran) — Administration › Serveur / Téléphone

Gestion MP : `README.md`, `docs/MISE-EN-SERVICE.md` → PRO : `EXPLOITATION.md` + `/administration?onglet=serveur|telephone`, T, D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Raccourci bureau « Gestion MP.app » : sonde `localhost:8030/api/sante`, lance `scripts/demarrer.sh`, attend 60 s, ouvre le navigateur ; alertes « Le dossier de Gestion MP est introuvable… », « Gestion MP n'a pas démarré… » ; `arreter.sh` | raccourci équivalent (port 8050, GET `sante`) ou service systemd/launchd ; mêmes alertes | port PRO 8050 |
| Serveur 8030, `0.0.0.0`, copie figée des écrans | Caddy HTTPS devant le serveur, copie figée | exposition fermée (HTTPS) |
| Premier lancement → compte D ; puis comptes A (code ≥ 8), L (code « de 4 chiffres », serveur ≥ 4) | D ou T crée les comptes (POST `utilisateurs`) ; L : exactement 4 chiffres | P1-5 |
| Téléphone Wi-Fi : `http://<adresse>:8030`, adresse dans Réglages › Téléphone ; écran d'accueil iPhone/Android | `/administration?onglet=telephone` : adresse HTTPS + QR (GET `acces`, GET `acces/qr`) ; enrôlement de l'appareil (POST `appareils/enroler`) | P1-18 vocabulaire « Administration › Téléphone » |
| 4G/5G : Tailscale | identique | — |
| Étiquettes QR → `{adresse pour téléphones}/lot/{id}` (réglage Société, jamais « localhost ») | identique (paramètre technique, T) | — |

**Gestes** : aucun dans l'écran (opérations d'exploitation, cf. `EXPLOITATION.md`).

---

### Ma journée (achats) — `/accueil`

Gestion MP : `pages/Accueil.tsx` version achats (A et D par l'adresse) → PRO : `/accueil` (`Page`, `Indicateurs`,
`Carte`, listes de tâches), A (D : hors menu, sa liste « À faire » est au Cockpit).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Bonjour {nom} », sous-titre « Ce qui attend une action aujourd'hui. » | `EnTete` titre « Ma journée », sous-titre « Bonjour {nom} — ce qui attend une action aujourd'hui. » | titre = libellé de route |
| Données : `/commandes`, `/receptions`, `/cockpit`, `/bons`, `/operations`, `/dossiers-a-rattacher`, `/signalements`, `/reclamations`, `/inventaires` | GET `commandes`, `receptions`, `cockpit`, `brouillons`, `dossiers/a-rattacher`, `signalements`, `reclamations`, `inventaires` | `/bons`+`/operations` → `brouillons` |
| KPI « Ruptures, critiques, urgentes » = ruptures + critiques + urgents, détail « au plan d'achat », ton critique/ok, non cliquable | `Kpi` « À commander vite » (formule : RUPTURE + CRITIQUE + URGENT) → `/plan-achat` | nom = formule ; cliquable (P1-9, P1-27) |
| KPI « Arrivées dans les 7 jours » (n°, ni soldée ni annulée, ETA sinon livraison prévue, d'hier à J+7) | `Kpi` même formule → carte Arrivées (ancre) | — |
| KPI « Commandes en retard » (`enRetard`, ton urgent/ok) | `Kpi` (champ serveur `en_retard`) → `/commandes?filtre=retard` | même définition que la liste (P1-11) |
| KPI « Anomalies de contrôle » (ton critique/attention/ok, « voir les contrôles → ») | `Kpi` → `/analyse?onglet=controles` | — |
| Carte « À faire ({n}) » — 1 besoins signalés (urgents d'abord, « Besoin signalé : {réf} », étiquette « urgent », note « « {texte} » — {par}, le {date} », bouton « Traiter ») | `Carte` « À faire » ; ligne besoin + `Badge` urgent + `Bouton` « Traiter » → `/accueil?signalement={id}` | adresse stable de la fenêtre |
| 2 alertes « {n} matière(s) en rupture, critiques ou urgentes » → `/plan-achat` | identique | — |
| 3 retards « {n} commande(s) en retard » + 4 « {n°} · {fournisseur} » → `versCommandes(…,'retard')` | identique ; 1 commande → `/commandes/{id}` | A5 |
| 4 prix à confirmer « {n} commande(s) attendent la confirmation des prix » | identique | — |
| 5 « {n} bon(s) de commande en brouillon à envoyer » | « {n} commande(s) en brouillon à envoyer » | vocabulaire |
| 6 factures sans dossier → `/importations?onglet=rattacher` | identique | — |
| 7 réceptions importées sans facture → idem | identique | — |
| 8 « Inventaire {numéro} en cours » (**premier** seulement) « {comptés} / {lignes} lots comptés — le magasin est suspendu… » → `/inventaire?inventaire={id}` | une ligne **par inventaire ouvert** → `/inventaires/{id}` | P1-10 |
| 9 réclamations ouvertes (« {n°} · {fournisseur} · {motif} ({jours} j) ») → `/receptions?onglet=reclamations` | identique ; 1 → `/reclamations/{id}` | — |
| 10 contrôles en anomalie → `/analyse?onglet=controles` | identique | — |
| Vide « Rien n'attend : tout est à jour. » ; « quelques » : 4 + « — … (+{reste}) » | identique | — |
| Carte « À valider ({n}) » : réceptions brouillon (« La matière n'est pas encore en stock. » ; 1 → fiche), sorties brouillon (« Le fil n'est pas encore sorti du stock. » ; numéro repris), opérations brouillon | `Carte` « À valider » : réceptions → `/receptions/{id}` ou `?onglet=brouillon` ; ordres → `/ordres/{id}` ou `/sorties?onglet=brouillon` ; opérations → `/operations/{id}` ou `?onglet={type}` ; lien « Tout valider… » → `/stock?onglet=a-valider` | « sorties » → « ordres » (vocabulaire) |
| Vide « Aucun brouillon : tout ce qui a été saisi est validé. » | identique | — |
| Carte « Arrivées attendues dans les 7 jours ({n}) », la plus proche d'abord, « {n°} · {fournisseur} », « prévue le {date} · {état} » → commande | identique → `/commandes/{id}` | — |
| Vide « Aucune arrivée annoncée cette semaine. » | identique | — |
| Classe `fiche clic` | ligne-lien standard (`LienDocument`) | P1-12 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| clic sur une tâche / fiche (liens) | A | — | — | adresses stables |
| « Traiter » | A (D au Cockpit) | — | — | ouvre la fenêtre « Besoin signalé » |
| clic KPI | A | — | — | nouveau (P1-27) |

---

### Ma journée (alimentation au bureau) — `/accueil`

Gestion MP : `pages/Accueil.tsx` version alimentation → PRO : `/accueil` (`Tuile` du bureau + `Carte` « À valider »), L.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Bonjour {nom} » / « Alimentation des machines » | `EnTete` « Ma journée », sous-titre « Bonjour {nom} — alimentation des machines » | — |
| Grille 2 colonnes (≥ 340 px) : tuiles + « À valider » | `Grille` | — |
| Tuile ⇢ « Envoyer aux machines » (principale) « Qualité et m² : les fils et les lots sont proposés. » → `/atelier/envoyer` | `Tuile` → `/ordres/nouveau` (saisie de bureau) | écran de bureau au bureau |
| Tuile ⇠ « Retour des machines » → `/atelier/retour` | `Tuile` → `/sorties?onglet=valide` (« choisir l'ordre, puis Faire un retour ») | le retour part de l'ordre |
| Tuile ☰ « Les ordres » → `/sorties` | `Tuile` → `/sorties` | — |
| Tuile ▦ « Métiers à tisser » → `/metiers` | `Tuile` → `/metiers` | — |
| — | `Tuile` « Déplacer un lot » → `/operations/nouvelle?type=transfert` | L transfère au bureau (P1-19) |
| Carte « À valider » : sorties brouillon ; opérations (retour_machine, transfert) → `/atelier` | ordres → `/ordres/{id}` ; opérations → `/operations/{id}` | lien vers le document, pas l'atelier |
| Aucun prix, aucun indicateur | identique | — |
| `/` → `/sorties` au bureau | `/` → `/accueil` | P1-4 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| clic tuile / tâche | L | — | — | cibles de bureau |

---

### Fenêtre « Besoin signalé par {par} » — `/accueil?signalement={id}` (et `/cockpit?signalement={id}`)

Gestion MP : fenêtre « Traiter » de l'Accueil achats → PRO : `Fenetre({taille:normale, sale})`, D, A.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Besoin signalé par {par} » ; « {référence} : « {texte} » » | identique ; `Definitions` (référence, texte, urgence, date) | ouvrable aussi depuis la `Cloche` et le Cockpit |
| « Réponse à l'atelier » (`Zone` 3 lignes, 500 car., focus, facultative), aide « ce qui est fait : commandé, en route, remplacé par… — l'atelier la lit sur son téléphone » | `Zone` identique | — |
| `sale` si réponse non vide | `sale` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Annuler » | D, A | — | passe par la garde `sale` | P1-22 |
| « Marquer traité » (« Enregistrement… ») | D, A | POST `signalements/{id}/traiter {reponse}` | « Signalement introuvable. » | toast « Besoin traité. » ; notification à l'auteur ; journal « besoin traité » |

---

### Cockpit — en-tête et indicateurs — `/cockpit`

Gestion MP : `pages/Cockpit.tsx` → PRO : `/cockpit` (`EnTete`, `Indicateurs` de 6 `Kpi`, `Onglets`), D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/cockpit` (180 s ; `date_reference` serveur) | GET `cockpit` (D,A) | — |
| `?onglet=` lu/écrit (`replace`), « faire » efface, inconnu → faire | `useOngletAdresse` | — |
| Chargement « … le cockpit… » ; erreur « Le cockpit est indisponible. » | `Chargement`, `Erreur` | — |
| Titre « Cockpit » ; sous-titre « Situation au {date}, recalculée à chaque ouverture depuis le journal des mouvements. » | sous-titre « … depuis les mouvements de stock. » | vocabulaire (« journal » réservé) |
| Champ mois (`type=month`, 160 px, infobulle « Le mois du bilan », défaut mois précédent, max mois en cours) + « Bilan du mois » | `DateChamp` mode mois (max = mois serveur) + `BoutonImprimer` | — |
| KPI « Valeur du stock » `montantCourt(valeur_mad)` ; infobulle « … les magasins, au coût moyen pondéré[, dont {x} en machine…] » ; détail « {n} matière(s) · + {x} sur les métiers (info) » | `Kpi` valeur ; formule « Σ (magasins, quarantaine comprise, + sur les métiers) × coût moyen pondéré (sinon catalogue × cours) » ; détail « {n} matières · dont {x} sur les métiers » ; infobulle = texte unique « Sur les métiers » ; → `/analyse?onglet=valorisation` | P1-8 : un seul sens (« dont ») |
| KPI « Couverture pondérée » `jours(…)` ; « pondérée par la valeur » | `Kpi` + formule (Σ projeté>0 × prix × cours ÷ conso valorisée journalière) → `/stock` | cliquable |
| KPI « À commander » budget ; « selon le plan d'achat » ; ton attention | `Kpi` → `/plan-achat` | cliquable |
| KPI « Commandé » = nombre de bons actifs ; infobulle reste à livrer (confirmé/catalogue, cours figé/jour, dont estimé) ; détail « en cours · {montant} · {n} en retard » ; ton urgent si retards | `Kpi` → `/commandes?onglet=confirmee` ; détail « n en retard » → `/commandes?filtre=retard` | cliquable |
| KPI « Rotation du stock » « {r} × » ; base consommation / plan (2 infobulles) ; « par an · cycle de trésorerie {CCC} j » | `Kpi` + `Formule` (2 bases) → `/analyse?onglet=valorisation` | cliquable |
| KPI « Contrôles » « {conformes} / {total} » ; détail bloquants / anomalies / « tout est conforme » ; ton critique/attention/ok | `Kpi` → `/analyse?onglet=controles` | cliquable |
| « Aucun indicateur du Cockpit n'est cliquable » | tous cliquables | P1-27 |
| Onglets `faire` (compte `aFaire.total`, masqué si 0), `alertes` (`nb_alertes`, même à 0), `ensemble`, `evolution`, `economies` (`nb_opportunites`, même à 0) | `Onglets` mêmes clés/libellés/compteurs | — |
| — | `Cloche` présente (D compris) | A10 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choix du mois | D | — | `DateChamp` borné | — |
| « Bilan du mois » | D (A depuis Analyse) | GET `/api/documents/bilan?mois=AAAA-MM` (nouvel onglet) | `Bouton({manque:['mois']})` ; infobulle « Le bilan du mois choisi — entrées, sorties, stock de début et de fin, production, achats — dans une page à imprimer » | route documents |
| changement d'onglet | D | — | — | — |
| clic KPI | D | — | — | nouveau |

---

### Cockpit › À faire et à valider — `/cockpit` (`?onglet=faire`)

Gestion MP : `CockpitAFaire.tsx` → PRO : bandeau `Note`, `Carte` « Commandes à approuver » (`DataTable`),
`Carte` « Ce qui attend une action » (liste), D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Bandeau rouge « {n} matière(s) en alerte rouge : {r} en RUPTURE, {c} CRITIQUE(S) — et {u} URGENT, {a} en ATTENTION. Voir le plan d'achat → » / vert « Aucune rupture ni matière critique — … » | `Note` ton critique / ok, mêmes textes ; « alerte rouge » = définition nommée | P1-9 |
| Données : `/commandes`, `/receptions`, `/bons`, `/operations`, `/inventaires`, `/sauvegardes`, `/signalements`, `/reclamations` | GET `commandes`, `receptions`, `brouillons`, `inventaires`, `sauvegardes`, `signalements`, `reclamations` | — |
| Carte « Commandes à approuver ({n}) », lien « Toutes les commandes → » ; colonnes Bon (n° ou « À approuver », note « par {créé par} »), Fournisseur, Passée le, Montant (devise ; note « estimé, prix du catalogue »), Montant MAD, « Examiner » | `DataTable` mêmes colonnes (`Montant`), `Cadre` ; lien → `/commandes?onglet=a_approuver` | — |
| Ligne / « Examiner » (infobulle « Ouvrir le bon pour le relire, puis l'approuver ou le renvoyer aux achats ») → DetailCommande, cockpit relu à la fermeture | → `/commandes/{id}` (fiche en fenêtre) ; fermer revient au Cockpit (historique) | adresse stable (A5) |
| Vide « Aucune commande n'attend votre approbation. » | `Vide` | — |
| « Ce qui attend une action » : rouges, approuver (3 « {fournisseur}, {montant MAD}[ estimé] »), retards, prix, réceptions brouillon, sorties brouillon (« Fil préparé mais pas encore sorti du stock. »), opérations brouillon, inventaires (rouge, « … aucune réception, sortie ni transfert ne passe dans ce magasin… »), besoins (rouge si urgent), réclamations, contrôles | même liste, mêmes comptes/tons/textes ; liens : `/plan-achat`, `/commandes…`, `/receptions/{id}` ou `?onglet=brouillon`, `/ordres/{id}` ou `/sorties?onglet=brouillon`, `/operations/{id}` ou `?onglet=`, `/inventaires/{id}` ou `/inventaire`, besoins → `Bouton` « Traiter » (`/cockpit?signalement={id}`), `/receptions?onglet=reclamations`, `/analyse?onglet=controles` | besoins traités sur place (plus de lien « Accueil des achats ») |
| Ligne Sauvegarde : « Sauvegardes : état illisible » / « Sauvegarde à vérifier » / « Sauvegarde à jour » ; note alerte serveur ou « Dernière sauvegarde le … (il y a {n} h) · {nb} conservée(s). » / « Aucune sauvegarde n'a encore été faite. » ; alerte si > 26 h ; +1 au total ; lien « Sauvegardes → » `/reglages?onglet=sauvegardes` | identique ; lien → `/administration?onglet=sauvegardes` ; aussi dans `BandeauServeur` | onglet déplacé |
| « Rien d'autre n'attend : tout est à jour. » | `Vide` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Examiner » / clic ligne | D | GET `commandes/{id}` (puis POST `commandes/{id}/approuver` ou `/renvoyer` dans la fiche) | dans la fiche | adresse stable |
| « Toutes les commandes → » et liens « {lien} → » | D | — | — | — |
| « Traiter » (besoin) | D | POST `signalements/{id}/traiter` | fenêtre | nouveau sur le Cockpit |
| « Sauvegardes → » | D | — | — | `/administration` |

---

### Cockpit › Matières en alerte — `/cockpit?onglet=alertes`

Gestion MP : `CockpitAlertes.tsx` → PRO : `Carte` + `Recherche` + `DataTable` (`Cadre`), D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Matières en alerte — les 24 plus pressées sur {total} » / « …, la plus pressée d'abord — {total} » ; liens « Plan d'achat → », « Stock → » | « Matières en alerte, la plus pressée d'abord — {total} » ; mêmes liens | toutes les matières en alerte (plus de limite 24) |
| Données = 24 lignes de `/cockpit` | GET `stock` (lignes RUPTURE, CRITIQUE, URGENT, ATTENTION) | recherche sur tout le jeu (P1-13) |
| Recherche « Référence, fournisseur, statut… plusieurs mots » (réf., nature, désignation, titrage, fournisseur, statut, statut de couverture, action) ; « Effacer les filtres » ; note « Cliquer une matière l'ouvre dans le Stock. » | `Recherche` (A6) + `Filtres` liés (statut, fournisseur) + « Effacer les filtres » dès 2 + « N critère(s) » | filtres liés (A1) |
| Ordre : couverture croissante ; pas de tri cliquable | tri par défaut identique ; tri par en-tête | — |
| Colonnes Référence (note « nature · titrage · désignation »), Fournisseur, Stock projeté (note « dont {n} sur les métiers », infobulle « Stock détenu (magasins et métiers) + commandé à temps − sorties prévues pendant le délai »), Conso / mois, Couverture, Délai, À commander (note ≈ ml), Statut (`Badge`, infobulle seuil ; infobulle statut de couverture si différent), Action | mêmes colonnes ; quantités `KgEtMetres` (unité « kg », ≈ ml pour cuir/franges/ruban) ; « dont {n} kg sur les métiers » | P1-14, P1-15 |
| Action : « Préparer la commande » (infobulle « {action lisible} : ouvrir la préparation de commande ») sinon action lisible ; action lisible sans émoji | `Bouton` → `/plan-achat/preparer/{fournisseurId}` | adresse stable |
| Ligne (infobulle « Ouvrir cette matière dans le Stock ») → `/stock?onglet=matieres&q={réf.}` | → `/stock/matieres/{id}` | fiche directe |
| Vides « Aucune matière ne correspond à cette recherche. » / « Aucune matière en alerte. » | `Vide` | — |
| Création depuis PreparationCommande → `/commandes?onglet=brouillon&commande={id}` | → `/commandes/{id}` | A5 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| recherche / « Effacer les filtres » | D | — | — | filtres liés |
| clic ligne | D | — | — | fiche matière |
| « Préparer la commande » | D | GET `plan-achat/fournisseurs/{id}` (puis POST `commandes`) | dans la préparation | — |

---

### Cockpit › Vue d'ensemble — `/cockpit?onglet=ensemble`

Gestion MP : `CockpitEnsemble.tsx` → PRO : 2 `Carte`, `Barres`, `DataTable`, D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Les matières par statut » (lien « Stock → ») : histogramme RUPTURE/CRITIQUE/URGENT/ATTENTION/OK/« Sans consommation » (couleurs), infobulle « {n} matière(s) » | `Barres` mêmes couleurs ; clic barre → `/stock?onglet=matieres&statut=…` | barre cliquable |
| Liste : classes ABC ; mono/multi-source ; stock dormant (« … {montant} immobilisés, soit {part} de la valeur du stock ») | `Definitions` mêmes phrases | — |
| « Le budget à commander, par devise » (lien « Plan d'achat → ») : Devise, Matières, Montant MAD, Part ; vide « Rien à commander. » | `DataTable` + pied total | — |
| Coût matière annuel/mensuel ; rotation (DIO, base) ; cycle de trésorerie (CCC = DIO + DSO − DPO) ; « {n} fournisseur(s) référencé(s). » | `Definitions` + `Formule` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Stock → », « Plan d'achat → » | D | — | — | — |

---

### Cockpit › Évolution — `/cockpit?onglet=evolution`

Gestion MP : `CockpitEvolution.tsx` → PRO : `Carte` + `Bascule` + `Courbes`, `Carte` + `DataTable`, D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/indicateurs/historique` (photo par jour) ; chargement/erreur | GET `indicateurs/historique` | — |
| Bascule 4 vues : « Valeur et achats » (3 séries, axe « {n} M »), « Alertes » (3), « Couverture », « OTIF » (%) ; points r=3, axe temps, légende, infobulle, trous reliés | `Bascule` (`?vue=`) + `Courbes` (axe par devise) | vue dans l'adresse |
| < 2 photos : message « L'évolution repose sur une photo par jour… » + « Une seule photo… » / « Aucune photo encore. » + « « Photographier aujourd'hui » prend celle du jour tout de suite. » ; aucune photo → pas de graphique | `Note` mêmes textes | — |
| « Les photos, la plus récente d'abord ({n}) » : Jour, Valeur du stock, Couverture, Rupt. · crit. · urg., À commander, OTIF ; vide « Aucune photo. » | `DataTable` mêmes colonnes ; `ExportExcel` (colonnes `exporte`) | export |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Photographier aujourd'hui » | D | POST `indicateurs/photographier` | infobulle « Prendre tout de suite la photo du jour (le serveur la prend aussi seul, chaque jour) » ; occupe | toast « La photo d'aujourd'hui est prise. » |
| Bascule (4 vues) | D | — | — | — |

---

### Cockpit › Opportunités d'économies — `/cockpit?onglet=economies`

Gestion MP : `CockpitEconomies.tsx` → PRO : `Carte` + `Note` + `DataTable`, D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Les plus fortes opportunités d'économies — {n} au total, {montant} par an » ; lien « Toutes les opportunités → » | identique → `/analyse?onglet=opportunites` | — |
| Note « Un fil de même composition, même type et même titrage s'achète moins cher ailleurs… pas une décision… » | `Note` identique | — |
| 5 plus fortes (même couleur) : Référence · fournisseur actuel, Composition × titrage, Prix actuel (MAD / kg) (note base et date), Comparable moins cher · chez, Son prix (MAD / kg), Écart (badge ambre « −x,x % »), Conso / an (kg), Économie / an | `DataTable` mêmes colonnes ; ligne → `/stock/matieres/{id}` | lignes cliquables |
| Vide « Aucune opportunité d'économie détectée. » ; formule (prix − comparable) × conso annuelle, coût rendu usine | `Vide` ; `Formule` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Toutes les opportunités → » | D | — | — | — |
| (nouveau) clic ligne | D | — | — | fiche matière |

---

### Document « Bilan du mois » — `GET /api/documents/bilan?mois=AAAA-MM`

Gestion MP : GET `/api/bilan?mois=` (HTML) → PRO : gabarit Jinja2 A4 papier à en-tête (nouvel onglet), D, A.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Bilan {MM/AAAA} », bouton « Imprimer » masqué à l'impression, h1 « Bilan matières premières — {MM/AAAA} », société | identique, papier à en-tête | — |
| « Le mois en chiffres » : Stock au début / à la fin (kg, MAD), [Stock d'ouverture saisi], Entrées, Sorties vers les machines (« dont {kg} revenus · coût net »), Tissé (m², ordres), Commandes émises, OTIF, Ajustements (« retours fournisseur ») | mêmes cases ; stock de début/fin = magasins + **sur les métiers** (montages en vigueur à la date, historique GET `metiers/{id}/montages`) | point tranché : le fil monté est du stock à toute date |
| Paragraphe : valeurs au CMUP ; « à une date passée le fil monté n'est pas compté » ; « Stock à la fin = début + entrées + ouvertures − sorties + retours − retours fournisseur + ajustements + annulations » ; « Annulations… datées du mois : {kg} » | équation des mouvements identique + « ± variation sur les métiers (montages et tissage ; monter n'écrit aucun mouvement) » ; annulations à part | phrase « pas compté » supprimée |
| « Fabrication, qualité par qualité » (Qualité, m²) ; vide « Aucun ordre ce mois-ci. » | identique | — |
| « Les plus grands écarts entre la recette et le réel » : Ordre, Qualité, Prévu (kg), Sorti net (kg), Écart (%) ; vide « Aucun. » | titre « … entre le prévu par la recette et le sorti net » | vocabulaire |
| « À la fin du mois » : ruptures, critiques | identique | — |
| 422 si mois mal formé | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer » | D, A | — | — | — |

---

### Mode d'emploi — `/aide?onglet=regles|roles|pas|calculs|analyse|ecrans|telephone`

Gestion MP : `pages/Guide.tsx`, `/guide` → PRO : `/aide` (`Onglets`, `Carte` défilante, contenu tiré de `aide.json`), tous.

**Ce qu'on voit (page)**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Mode d'emploi », sous-titre « Les règles, qui fait quoi, les gestes pas à pas, les calculs, et où est passé chaque écran de l'ERP Fil. » | identique | — |
| `?onglet=` (« regles » efface) | `useOngletAdresse` | `/guide` → `/aide` (redirection) |
| Texte qui défile dans sa carte (`Defile`) | `Cadre` | — |
| Liens bleus gras ; un lien interdit → accueil + « écran réservé » | liens **filtrés par rôle** (non lien si l'écran est refusé, avec « (réservé : …) ») | plus de lien vers un refus (P1-19) |
| Source : texte en dur dans `Guide.tsx` | `aide.json` (une seule source : Mode d'emploi, « ? » de chaque `EnTete`, formules des `Kpi`) | A7 |

**Mode d'emploi › Les règles** (`regles`) — carte « Les règles qui tiennent le stock juste »

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| 1 Journal des mouvements, seule écriture de stock (contrôle « Soldes et journal ») | « Les mouvements de stock sont la seule écriture de stock » | vocabulaire « journal » réservé |
| 2 Brouillon puis validation (numéros REC/OF/BC sans trou ; « Brouillon », « À approuver ») | identique | — |
| 3 Annuler (contre-passation), annulations reprises datées de la reprise | identique | — |
| 4 Stock en kilos, commande en conditionnements (« 12 × Palette de 900 kg ») | identique | — |
| 5 Cuir, franges, ruban : kilos en stock, mètres en recette ; densité ; « 14,3 kg ≈ 1 020 ml » | identique | — |
| 6 Prix de facture ≠ coût (dossier par facture, Coût hors TVA / Coût TTC) | identique | — |
| 7 Lot sur toutes les écritures, ordre sur les sorties ; « Lot interne » | identique | — |
| 8 Référence en quatre parties (lien Classification) | lien `/catalogue?onglet=classification` | — |
| 9 Stock en magasin ou sur les métiers (formule montage, cantre, retour, C25) | réécrite avec le **texte unique « Sur les métiers »** + formule du montage + « fil monté sans sortie : contrôle C25 » | point tranché |
| 10 Devise du prix ; jamais d'addition | identique | — |
| 11 Deux horloges | identique | — |
| 12 Jamais sous zéro ; quarantaine détenue non disponible ; libération motivée | identique | — |
| 13 Les dates tiennent (période close « Réglages › Paramètres › Société ») | identique | — |
| 14 Chaque geste est signé ; lien « Journal des actions » `/reglages?onglet=journal` | lien `/administration?onglet=journal` (D,T) ; colonne « Par » ; « Historique » de chaque fiche | onglet déplacé |

**Mode d'emploi › Qui fait quoi** (`roles`)

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| Carte Direction (voit et peut tout, Cockpit, approuve, Réglages, métiers, plan) | identique ; Réglages métier + Administration | — |
| Carte Achats (… n'ont pas les réglages, comptes, sauvegardes, approbation) | « … Réglages en lecture, devises en écriture ; ni comptes, ni sauvegardes, ni approbation » | P1-28 |
| Carte Alimentation (téléphone : envoyer, retour, trouver, déplacer ; bureau : sorties, transferts, stock, métiers, production en lecture ; ni prix…) | identique ; transferts et retours au bureau réellement permis (`/operations`) | P1-19 |
| — | Carte Administrateur technique (comptes, appareils, sauvegardes, journal, serveur, courriel ; aucune donnée métier) | rôle T |

**Mode d'emploi › Pas à pas** (`pas`) — 9 procédures, lien « Ouvrir → »

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| 1 Passer une commande depuis le plan `/plan-achat` | identique | — |
| 2 Commander sans le plan `/commandes` | lien `/commandes/nouvelle` | — |
| 3 Réceptionner `/receptions` | lien `/receptions/nouvelle` | — |
| 4 Monter un fil `/metiers` (bobines, poids, « Sur les métiers », 60/40 %, C25) | texte unique « Sur les métiers » | point tranché |
| 5 Sortir de la matière pour un ordre `/sorties` (téléphone « Envoyer aux machines » / bureau « Nouvelle sortie ») | lien `/ordres/nouveau` | — |
| 6 Savoir ce qu'un fil a coûté `/analyse?onglet=revient` | identique | — |
| 7 Retrouver d'où vient un fil `/stock?onglet=lots` | identique (+ `/tracabilite`) | — |
| 8 Faire l'inventaire `/inventaire` | lien `/inventaires/nouveau` | — |
| 9 Le point hebdomadaire `/cockpit` | lien selon rôle : D `/cockpit`, A `/accueil` ; « Réglages › Sauvegardes » → « Administration › Sauvegardes » | P1-19 |

**Mode d'emploi › Les calculs** (`calculs`) — tableau « Grandeur | Comment elle est obtenue »

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| 21 grandeurs (Besoin du mois, Prix au kilo, Besoin retenu, Stock détenu, Stock projeté, Sorties prévues, Seuil d'alerte, Statut, Statut de couverture, Couverture, Quantité à commander, ABC, XYZ, Valeur du stock, Coût hors TVA, Opportunité, OTIF, Rotation, Cycle de trésorerie…) ; pied « Les seuils… Réglages › Paramètres (direction)… » | mêmes 21, tirées de `aide.json` (mêmes formules que les `Kpi`) ; Stock détenu / Valeur : texte unique « Sur les métiers » | P1-8 (Guide disait « valorisé à part ») |

**Mode d'emploi › L'analyse** (`analyse`) — 9 lignes

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| Note D,A « Menu « Analyse »… Excel… adresse en favori » ; L « L'analyse est réservée aux achats et à la direction. » (sans liens) | identique, liens filtrés par rôle | — |
| Valorisation, Matrice, Prix payés, Opportunités, Fournisseurs, Coût de revient, Échéancier, Contrôles (« Trente-huit vérifications »), Production | identique | — |

**Mode d'emploi › Les écrans de l'ERP Fil** (`ecrans`) — 25 lignes

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| Écran ERP Fil → Dans Gestion MP (lien) → Ce qui a changé (Cockpit, Stock, Plan d'achat, Production, Métiers, Mouvements, Bon de sortie, Commandes, Réceptions, Lots, Importations, Coût de revient, Inventaire, Catalogue, Classification, Fournisseurs, Qualités & recettes, Valorisation, Prix & matrice, Contrôles, Paramètres → Réglages (…), Guide → Mode d'emploi, nouveaux : Comptes · Journal, Écran atelier) | mêmes 25 lignes ; « Paramètres → Réglages (Paramètres, Devises, Magasins, Frais, Douane, Période) · Administration (Comptes, Appareils, Sauvegardes, Journal des actions, Courriel, Serveur, Téléphone) » ; « Qualités et recettes » | P1-18 |
| Pied « Un lien vers un écran que votre rôle ne voit pas vous ramène à votre accueil. » | « Les écrans que votre rôle ne voit pas sont indiqués sans lien. » | — |

**Mode d'emploi › Le téléphone** (`telephone`) — 4 étapes

| Élément GMP | Élément PRO | Changement |
|---|---|---|
| Wi-Fi `http://192.168.1.20:8030` (« Réglages › Accès téléphone donne l'adresse exacte et un QR ») ; 4G/5G Tailscale ; écran d'accueil ; appareil photo lit les QR | adresse HTTPS ; « Administration › Téléphone donne l'adresse exacte et un QR » ; + enrôlement de l'appareil | P1-18 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| changement d'onglet | tous | — | — | — |
| liens internes (« Ouvrir → »…) | tous | — | — | filtrés par rôle |

---

### Fiche de lot — `/lots/:id` (fenêtre sur `/stock?onglet=lots`) ; QR `/lot/:id`

Gestion MP : page `/lot/:id` (`Lot.tsx`, `FicheLotBureau`, `Liberation`) et fenêtre de lot du Stock → PRO :
`Fenetre({taille:tresLarge})` sur `/stock?onglet=lots` à l'adresse `/lots/:id` (une seule fiche ; la page
autonome disparaît), C. `/lot/:id` : téléphone + L → `/atelier/lots/:id`, sinon `/lots/:id`.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/lots/{id}` (prix des mouvements masqués pour L) | GET `lots/{id}` (`sans_prix`) | — |
| « Un instant — chargement : le lot… » ; toute erreur → « Lot introuvable. » | 404 → « Lot introuvable. » ; autre → `Erreur` avec le message | P1-16 |
| Titre « Lot {numéro} » (page) / « {référence} — lot {n°} » (fenêtre) ; sous-titre « {référence} · {rôle} · {fournisseur} » + statut | titre « {référence} — lot {n°} » + `Badge` statut ; sous-titre identique | un seul titre |
| Statuts `disponible` « Disponible », `partiel` « En partie en quarantaine », `quarantaine` « En quarantaine », `epuise` « Épuisé » | table `Badge` | — |
| KPI Reste (`quantite`, « {n} bobines », ton attention si quarantaine) | `Kpi` Reste en `KgEtMetres` | — |
| KPI Disponible (détail = statut) | `Kpi` « Disponible » kg | — |
| KPI « Entré · sorti » « {entré sans unité} · {sorti kg} » ; « dernier mouvement le {date} » | deux `Kpi` « Entré » et « Sorti » en kg (net des retours) | P1-15, P2-16 |
| KPI kg / bobine (2 déc. ; « {n} bobines / palette ») ; KPI Entré le (fournisseur) | identiques | — |
| Ligne réception « Reçu par {REC lien A/D} le {date}[ · BL][ · facture] · pesé {q} » | « Réception {REC-…} du {date} · BL … · facture … · pesé {q} kg » ; `LienDocument` → `/receptions/{id}` (D,A) | P2-24 |
| Soldes « {code} {q} » (quarantaine en rouge) ; « Ordres servis : » liens OF → `/sorties?ordre=` | `Badge` par magasin ; `LienDocument` → `/ordres/{id}` | — |
| « Où ce lot est-il allé ? » (infobulle « D'où vient ce lot, quels ordres de fabrication il a servis, et quand ») → `/stock?onglet=lots&lot_id=…` | → `/tracabilite?lot={id}` (fenêtre empilée) | n'oblige plus l'onglet Lots (P2-18) |
| Bloc « Libération de quarantaine » (D,A, si quarantaine > 0,0005) : « En quarantaine : {q} dans « {magasin} » », « vers {code} » (défaut premier), « Ce qui a été contrôlé (obligatoire) » (300, ≥ 3) | même bloc, **une ligne par magasin de quarantaine** (total affiché) ; `Selecteur` destination ; `Zone` contrôle ; `sale` si saisi | P1-17 |
| Tableau des mouvements (`Cadre`) : Date, Mouvement (badge « annulation », « · motif »), Document (lien selon rôle), Magasin, Quantité (« +12,5 » sans unité, vert/rouge), Par ; infobulle = commentaire ; le plus récent d'abord | `DataTable` : mêmes colonnes ; « Quantité (kg) » ; `LienDocument` (ordre `/ordres/{id}`, opération `/operations/{id}` [D,A ; L pour transfert/retour machine], réception `/receptions/{id}` [D,A], inventaire `/inventaires/{id}` [D,A]) ; prix non affichés | P1-15 |
| Pied : « Page du lot », « Imprimer l'étiquette » | `BoutonImprimer` « Imprimer l'étiquette » ; « Historique » (journal de la fiche) | page autonome supprimée |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer l'étiquette » | C | GET `/api/documents/etiquettes?lots={id}` | — | route documents |
| « Où ce lot est-il allé ? » | C | GET `tracabilite?lot_id=` | — | `/tracabilite?lot=` |
| liens d'ordres servis / documents | selon rôle | — | — | `LienDocument` |
| « Page du lot » | C | — | — | supprimé (l'adresse `/lots/:id` est partageable) |
| « Libérer » | D, A | POST `operations` {valider: true, type transfert, motif « Libération de quarantaine », commentaire, une ligne par magasin de quarantaine} (route ajoutée, API-PRO § 1.24 : variante `?valider=1`, création + validation dans une transaction) | `Bouton({manque:['ce qui a été contrôlé','destination']})` ; `Confirmer` « Libérer {q} : la matière devient disponible pour les machines ? » · « Non » · « Oui, libérer » ; refus : « Libérer une quarantaine est une décision de la direction ou des achats, après contrôle de la matière. » (OR24, lot RESTES3), « Une sortie de quarantaine se fait avec le motif « Libération de quarantaine ». », inventaire en cours, date | tout libéré (P1-17) ; plus de DELETE de rattrapage ; toast « {TRF-…} : {q} libérés, disponibles pour les machines. » |

---

### Document « Étiquettes de lots » — `GET /api/documents/etiquettes?lots=1,2`

Gestion MP : GET `/api/lots/etiquettes?ids=` → PRO : gabarit Jinja2 100 × 70 mm, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Une page par lot, 100 × 70 mm, « Imprimer » masqué à l'impression | identique | — |
| QR 34 mm de `{adresse pour téléphones}/lot/{id}` ; référence 13 pt gras ; « Lot {n°} » 16 pt ; fournisseur ; « Entré le {date} » ; « {kg[ ≈ ml]} à l'impression » ; « N° {id} » ; cadre « QUARANTAINE — NE PAS SORTIR » | identique (QR en HTTPS) | — |
| « Aucun lot à étiqueter. » (404) | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer » | C | — | — | — |

---

### Mon compte — `/compte` (nouveau)

Gestion MP : aucun écran (route POST `/moi/code` sans écran, P1-24) → PRO : `/compte` (`Form`), tous.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| — | nom, identifiant, rôle, courriel ; changer son code ; appareils enrôlés | nouveau |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| — | tous | PUT `moi` | — | nouveau |
| — | tous | PUT `moi/code` | ancien code exigé | nouveau (P1-24) |

---

### Anomalies GMP corrigées — Partie 1

| # | Anomalie GMP | Traitement PRO |
|---|---|---|
| P1-1 | Nouvel essai testé sur le message, pas le statut | `retry` teste `ErreurApi.statut` (401/403/404/409/422 jamais retentés) |
| P1-2 | Service worker jamais enregistré au téléphone (HTTP) | accès HTTPS (Caddy) → contexte sécurisé, SW et installation PWA réels |
| P1-3 | QR au téléphone pour un acheteur → `/accueil` sans fiche | `/lot/:id` : téléphone **et** L → atelier ; sinon `/lots/:id` |
| P1-4 | `/` → `/sorties` pour L au bureau, `accueilDe` → `/accueil` | `/` → accueil du rôle (L bureau `/accueil`) partout |
| P1-5 | Entrée auto à 4 chiffres alors que le code peut être plus long | code L exactement 4 chiffres, exigé par le serveur |
| P1-6 | Session perdue sans explication | motif du 401 affiché sur `/connexion` |
| P1-7 | Libellé du bandeau d'abandon divergent de la doc | libellé unique « Des modifications ne sont pas enregistrées. Les abandonner ? » (contrat A4) dans `Fenetre` et la doc |
| P1-8 | « Valeur du stock » : « dont » vs « + … (info) », Guide « valorisé à part » | une formule (magasins + sur les métiers), « dont {x} sur les métiers », texte unique « Sur les métiers » partout |
| P1-9 | Trois comptes de « matières en alerte » | trois définitions nommées servies par le serveur : « alerte rouge » (rupt.+crit. : pastille, bandeau), « à commander vite » (+ urgentes : Ma journée), « en alerte » (4 statuts : onglet) ; formule en infobulle |
| P1-10 | Accueil : premier inventaire ouvert seulement | une ligne par inventaire ouvert |
| P1-11 | `estEnRetard` redéfini dans Commandes | champ serveur `en_retard` unique, lu par `lib/commandes.ts` et `?filtre=retard` |
| P1-12 | Classe interdite `fiche clic` | ligne-lien standard |
| P1-13 | Recherche des alertes limitée aux 24 envoyées | toutes les alertes (GET `stock`), recherche sur tout le jeu |
| P1-14 | Mètres indicatifs incomplets (alertes) | `KgEtMetres` dans toute colonne de kg d'une matière au mètre |
| P1-15 | Unités manquantes (Entré · sorti, Quantité, « dont … sur les métiers ») | `Colonne.unite` obligatoire pour une quantité ; KPI séparés en kg |
| P1-16 | Toute erreur = « Lot introuvable. » | 404 seul ; autres erreurs par `Erreur` |
| P1-17 | Libération du seul premier magasin de quarantaine | une ligne par magasin, total libéré |
| P1-18 | « Réglages › Accès téléphone » vs onglet « Téléphone » ; « Qualités & recettes » | « Administration › Téléphone » ; « Qualités et recettes » partout (vocabulaire depuis `routes.ts`) |
| P1-19 | Guide : transferts au bureau pour L refusés ; « Ouvrir → » du point hebdo refusé aux achats | `/operations` ouvert à L (transferts, retours machine) ; liens du Mode d'emploi filtrés par rôle |
| P1-20 | Pièces : liste non relue après échec partiel ; SVG accepté puis refusé | relecture après chaque fichier, bilan ; SVG exclu du sélecteur |
| P1-21 | `Confirmer` sans filet, « Oui » jamais grisé | erreur rattrapée vers `Messages`, « Oui » `occupe` |
| P1-22 | « Annuler » contourne la garde | tout bouton de fermeture passe par la garde `sale` |
| P1-23 | `nombre(v, 3)` → jusqu'à 4 décimales | décimales exactes, maximum explicite `dMax` |
| P1-24 | Code mort (`HAUT_DIALOGUE`, `MOIS_NOMS`, `rafraichir`) ; `/moi/code` sans écran | supprimés ; `/compte` avec PUT `moi/code` |
| P1-25 | `Tableau` cité mais inexistant | `DataTable<T>` réel |
| P1-26 | GET `/visages` public pour tout le réseau | visages seulement sur poste local ou appareil enrôlé ; ailleurs identifiant + code |
| P1-27 | Indicateurs du Cockpit non cliquables | `Kpi({lien})` sur les six |
| P1-28 | `/reglages` ouvert aux achats par l'adresse, hors menu | A voit Réglages au menu (devises en écriture, reste en lecture) ; garde = menu |

### Comptes de la partie 1

- Écrans / pages : 10 — coque, Connexion, Première installation, Ma journée (achats), Ma journée (alimentation),
  Cockpit, Mode d'emploi, Fiche de lot (`/lots/:id`, remplace la page du lot), Mon compte (nouveau), installation et
  accès (hors écran → Administration).
- Onglets / sous-vues : 16 GMP repris (Cockpit 5, Mode d'emploi 7, Bascule Évolution 4).
- Fenêtres : 4 GMP (Besoin signalé, DetailCommande → `/commandes/{id}`, PreparationCommande →
  `/plan-achat/preparer/:id`, mécanismes `sale`/`Confirmer`) + panneau de menu ; + fiche de lot en fenêtre.
- Documents : 2 (Bilan du mois, Étiquettes).
- Composants partagés : 20 GMP → 20 correspondances (+ `DataTable` pour le `Tableau` absent) ; briques `lib/` : 8 (+ `main.tsx`).
- Gestes GMP : 30, tous repris (☰ Menu, Se déconnecter, toucher un nom, Entrer, Créer le compte et entrer, Traiter,
  Marquer traité, Annuler, choix du mois, Bilan du mois, Examiner/ligne, Préparer la commande, Effacer les filtres,
  ligne d'alerte, Photographier aujourd'hui, Bascule Évolution, Imprimer l'étiquette, Où ce lot est-il allé ?, Libérer
  [Non / Oui, libérer], Joindre un document…, glisser-déposer, télécharger, Retirer [Non / Oui, retirer], ×/Échap/fond,
  Non continuer la saisie, Oui abandonner, Imprimer bilan, Imprimer étiquettes, onglets Cockpit, onglets Mode d'emploi) ;
  1 supprimé (« Page du lot », fondu dans l'adresse stable) ; nouveaux : clic KPI, Cloche, RechercheGlobale, Signaler un
  besoin, Traiter au Cockpit, PUT moi, PUT moi/code.
- Anomalies : 28, toutes traitées.

### Routes demandées par la partie 1 (reportées dans API-PRO § 1.24)

- `POST /api/operations (valider: true)` : création et validation d'une opération dans une seule transaction (libération de
  quarantaine ; aussi retour des machines, Partie 2). À défaut : POST `operations` puis POST `operations/{id}/valider`.
- Champs à exposer (pas de nouvelle route) : `GET contexte` → compteurs du menu (alerte rouge, anomalies) par rôle ;
  `GET cockpit` → `alerte_rouge`, `a_commander_vite`, `en_alerte` ; `GET commandes` → `en_retard`, `hors_suivi`,
  `prix_a_confirmer`, `montant_mad_estime`.

---

## Partie 2 — Stock, sorties vers les machines, production & besoins

Source : `ECRANS.md` lignes 1252-1970. Numéros « P2-n » = anomalies de la Partie 2. Conventions reprises :
`quantite()` → `KgEtMetres` (« 12,5 kg », 2 déc. sous 10 kg, « ≈ 1 020 ml ») ; refus de date communs (`date_permise` :
« Date trop ancienne… », « Date dans le futur… », « La période jusqu'au … est close… ») gardés mot pour mot et
annoncés par `DateChamp` (bornes) avant envoi ; refus de rôle 403 « Cette action est réservée à : … » gardés.

**Définitions de stock appliquées dans toute la partie** (point tranché, une seule définition serveur) :
Stock = magasins (quarantaine comprise) + sur les métiers ; Disponible = Stock − quarantaine ; Projeté = Disponible +
Commandé (dans le délai) − Demande pendant le délai ; Valeur = Stock × CMUP. « Sur les métiers » porte partout le texte
unique (voir en tête de Partie 1).

---

### Accès — `/stock`, `/sorties`, `/production`

Gestion MP : menu « Tous les jours », gardes `App.tsx` → PRO : registre `routes.ts`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `/stock` : menu A, L (+D), aucune garde ; pastille rupt.+crit. (pas pour L) | C ; `Pastille` « alerte rouge » pour C (GET `contexte`) | L voit la pastille |
| `/sorties` : menu A, L (+D), garde A, L ; `/` → `/sorties` pour L bureau | C ; `/` → `/accueil` | P1-4 |
| `/production` : menu A, L (+D), aucune garde ; écriture D | C ; plan écrit par D | — |
| Garde refusée → bandeau « L'écran demandé … » | `EcranReserve` | — |

**Gestes** : aucun.

---

### Stock, lots & mouvements — `/stock?onglet=matieres|lots|mouvements|ordres|a-valider`

Gestion MP : `pages/Stock.tsx` → PRO : `/stock` (`Page`, `EnTete`, `Onglets`), C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Stock, lots & mouvements » ; sous-titre « Par matière, lot par lot, chaque mouvement de stock, les ordres de fabrication, et ce qui attend d'être validé. » | identique | — |
| `?onglet=` (ou `?volet=` ; `tracabilite` → `ordres` ; inconnu → `matieres`) | `useOngletAdresse` ; anciens `?volet=`, `?onglet=tracabilite` redirigés | — |
| `?article=ID` → Lots filtré | `?matiere=ID` (filtre de l'onglet Lots, `useFiltresAdresse`) | nom PRO |
| `?q=` recherche initiale | `?q=` (tous onglets) | — |
| `?lot_id=&lot=`, `?ordre=`, `?reference=` → fenêtre de suivi | `/tracabilite?lot=|ordre=|matiere=` (fenêtre sur `/stock?onglet=ordres`, ou sur l'onglet d'origine) | adresse stable (A5) |
| Changer d'onglet remplace toute l'adresse ; tout changement ferme la fiche de lot | chaque onglet garde ses filtres dans l'adresse ; fiches = adresses (`/lots/:id`, `/stock/matieres/:id`) | filtres conservés au retour |
| Onglets « Par matière », « Lots », « Mouvements de stock », « Ordres de fabrication », « À valider » (compteur brouillons, masqué si 0) | `Onglets` identiques | — |
| L : aucun prix ni montant ni « Action » ; liens réceptions/opérations/inventaires D,A ; « Libérer » D,A | `sans_prix` serveur ; `LienDocument` filtré ; L ouvre aussi ses opérations (transferts, retours machine) | P2-13 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| changement d'onglet | C | — | — | filtres gardés |

---

### Stock › Par matière — `/stock?onglet=matieres`

Gestion MP : `StockParMatiere.tsx:248-516` → PRO : `Indicateurs`, `Bascule`, `Recherche`, `Filtres` liés,
`ExportExcel`, `DataTable` (`Cadre`, pied de totaux), C (montants D,A).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données GET `/stock` (`date_reference`, `magasins`, `lignes`), `/articles`, `/magasins` ; L : prix, montants, devise, action, valeur masqués | GET `stock` (rôle de la matière inclus), GET `magasins` ; `sans_prix` | `/articles` inutile |
| « Un instant — chargement : le stock… » ; erreur rouge | `Chargement`, `Erreur` | — |
| KPI « Matières affichées » (« sur N ») | `Kpi` | — |
| KPI « Stock affiché » Σ `stock_net` | `Kpi` Σ Stock (magasins + sur les métiers), formule en infobulle | point tranché |
| KPI « Ruptures » (« stock projeté à zéro », ton rupture/ok) | `Kpi` → filtre statut RUPTURE | cliquable |
| KPI « Critiques » (« sous le seuil critique ») | `Kpi` détail « projeté ≤ 50 % du seuil d'alerte » → filtre CRITIQUE | P2-7 |
| KPI « Budget à commander » (D,A ; `montantCourt`, « N matière(s) », ton attention) | `Kpi` → `/plan-achat` | cliquable |
| Bascule maison (`role=tablist`) « Approvisionnement » / « Classement et risque » / « Où se trouve la matière » (infobulles), non mémorisée | `Bascule` `?vue=appro|classement|ou` | P2-5 |
| Recherche « Référence, couleur, fournisseur, titrage… plusieurs mots affinent » (10 champs) | `Recherche` (`Colonne.recherche`, champs cachés) | — |
| « Exporter en Excel » (D,A) → `/api/export/pilotage` (infobulle « Stock par matière, plan d'achat, besoins mois par mois et contrôles… ») | `ExportExcel` → GET `export/pilotage` (D,A) | — |
| 9 filtres liés (statuts par rang, fournisseurs, rôles, compositions, types de fil, titrages, ABC, XYZ [infobulles], magasins avec stock) ; cases « En stock », « À commander » ; « Effacer les filtres » dès 1 | `Filtres` liés (A1) mêmes listes, mêmes tris ; cases ; « Effacer les filtres » dès 2 + « N critère(s) » | A1 |
| Note « {aide de la vue}. Un clic sur une ligne ouvre la fiche… ; un clic sur un en-tête trie. Situation au {date}. » | `Note` identique | — |
| Tri : tous en-têtes, 1er clic décroissant (num.) / croissant ; défaut statut puis couverture | `DataTable` identique | — |
| Colonnes fixes Référence (note « rôle · désignation »), Fournisseur, Statut (`Badge`, « Du plus urgent au plus calme ») | identiques | — |
| Rendu `Kg` : null « — », |v|<0,0005 « 0 » grisé, négatif rouge, sans unité (kg en en-tête), ≈ ml | `Colonne.unite = 'kg'`, `KgEtMetres` | — |
| Vue Appro : « Statut classeur » (infobulle « Statut de couverture… ») | colonne « Statut de couverture » | P2-7 (jargon) |
| Vue Appro : Stock (`stock_net`, « Tout ce que détiennent les magasins, quarantaine comprise ») | « Stock » = magasins (quarantaine comprise) + sur les métiers ; infobulle idem | P2-6 |
| Vue Appro : Sur les métiers (« … compté dans le stock, sa valeur et le disponible ») | infobulle = texte unique « Sur les métiers » | point tranché |
| Vue Appro : Disponible (« Les magasins hors quarantaine, plus le stock en machine… »), Commandé, Demande pendant le délai, Projeté, Conso / mois, Couverture (« N j », sans valeur triée en fin), À commander (≈ ml), Montant MAD (D,A), Action (D,A) | identiques ; Disponible = Stock − quarantaine ; Action → `Bouton` « Préparer la commande » (`/plan-achat/preparer/{fournisseurId}`) quand à commander > 0 | vocabulaire « Préparer la commande » |
| Vue Classement : ABC (« rang N · X % »), Conso / an MAD (D,A), XYZ (« CV »), Sourcing, Équivalences (« N substitut(s) »), Dernière sortie (« N j », badge « dormant ») | identiques | — |
| Vue Où : Stock ; une colonne par magasin actif hors quarantaine non vide ; Quarantaine (badge rouge) ; Sur les métiers ; Disponible (gras, « Les magasins, hors quarantaine ») ; Commandé ; Commandé au-delà ; Projeté | identiques ; Disponible infobulle « Le stock hors quarantaine : magasins et sur les métiers » | P2-6 |
| Pied « Total des N matière(s) » + Σ (doublon de code) | pied de totaux `DataTable` | P2-8 |
| Pas de pagination ; ligne cliquable → fiche ; vide « Aucune matière ne correspond à ces filtres. » | `Cadre` défilant ; ligne → `/stock/matieres/{id}` ; `Vide` | A2, A5 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Approvisionnement / Classement et risque / Où se trouve la matière | C | — | — | `Bascule` dans l'adresse |
| clic en-tête | C | — | — | — |
| Effacer les filtres | C | — | dès 2 critères | « N critère(s) » |
| Exporter en Excel | D, A | GET `export/pilotage` | — | — |
| clic ligne | C | GET `stock/{matiere_id}` | — | `/stock/matieres/{id}` |
| (nouveau) clic KPI | C | — | — | filtre posé |

---

### Fiche matière — `/stock/matieres/:id` (fenêtre sur `/stock`)

Gestion MP : fenêtre « Fiche matière » (`StockParMatiere.tsx:539-768`) → PRO : `Fenetre({taille:tresLarge})`,
`Kpi`, `Carte`, `Definitions`, `DataTable`, C (prix D,A).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre = référence ; `Badge` statut ; note « rôle · désignation · composition · type de fil · couleur · titrage » | identique | — |
| KPI Stock net (« kg en magasin » + ≈ ml) | `Kpi` « Stock » détail « magasins et sur les métiers » | P2-6 |
| KPI Sur les métiers (« {valeur} · stock en machine » D,A ; infobulle « … compte dans le stock et sa valeur, dans le disponible et le stock projeté — donc avant de commander. ») | `Kpi` ; infobulle = texte unique « Sur les métiers » | point tranché |
| KPI Disponible (« magasins, hors quarantaine ») | détail « stock hors quarantaine (magasins et métiers) » | P2-6 |
| KPI Demande pendant le délai (« N j de délai ; puis X sur la période… ») ; Stock projeté (ton statut) ; Couverture (« sans consommation prévue » / « après le délai ; seuil d'alerte : N j ») ; À commander (ml / unités / palettes ; ton attention) | `Kpi` identiques avec `Formule` | — |
| Carte « Approvisionnement » : Fournisseur, Délai, Prix (D,A ; « 0,000 DEV / kg », note au ml), Stock minimum (catalogue) (note retenu), Seuil d'alerte (note), Consommation retenue / mois (notes coefficient, hérité), Besoin annuel retenu, Déjà en préparation (« brouillon n° N, BC-… »), Montant à commander (D,A, note MAD) | `Definitions` identiques ; `Prix` ; « Déjà en préparation » → `LienDocument` `/commandes/{id}` | liens |
| Carte « Classement et risque » : ABC, Valeur consommée / an (D,A), XYZ, Sourcing, Groupe d'équivalence, Dernière sortie, Sans mouvement depuis, Dormant | identiques | — |
| Carte « Où se trouve la matière » : magasins (quarantaine rouge), Disponible, Sur les métiers (« stock en machine, compté dans le disponible »), Commandé (délai / au-delà), Demande pendant le délai (« − X »), Stock projeté à la livraison | identiques ; Sur les métiers : texte unique ; ajout « Stock » total | P2-6 |
| Messages « Action : {action} » (D,A) ; « Rien ne se rachète pour cette matière ({sans_achat})… » ; « Substituts disponibles dans le même groupe : … » | `Note` identiques ; D,A : `Bouton` « Préparer la commande » si à commander > 0 | geste ajouté |
| Carte « Besoins du plan, mois par mois (kg) » : mois « oct. 26 », Total | `DataTable` une ligne, mois « oct. 2026 » | P2-21 |
| Pas de saisie | `Historique` (journal avant/après de la matière, D,A) | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Voir les lots → » (principal si stock ; infobulle « Les lots de cette matière… (cocher « épuisés »…) ») | C | — | — | → `/stock?onglet=lots&matiere={id}` |
| « Où cette matière est-elle allée ? » | C | GET `tracabilite?reference=` | — | → `/tracabilite?matiere={id}` (empilée) |
| « Ses mouvements » (infobulle « Le journal filtré sur cette matière ») | C | GET `mouvements?q=` | — | infobulle « Les mouvements de stock de cette matière » (P2-2) |
| × / Échap / fond | C | — | — | → `/stock` avec filtres |
| (nouveau) « Préparer la commande » | D, A | GET `plan-achat/fournisseurs/{id}` | — | → `/plan-achat/preparer/{fournisseurId}` |

---

### Stock › Lots — `/stock?onglet=lots`

Gestion MP : `Stock.tsx:179-404` → PRO : `Indicateurs`, `Recherche`, `Filtres` liés, `DataTable` à cases,
`BoutonImprimer`, `ExportExcel`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/soldes?avec_historique=true&en_stock=…` ; `/articles` | GET `lots?avec_epuises=` | `/soldes` → `/lots` |
| Règles du lot : statuts (seuil 1 g), Entré (hors transferts/annulations), Sorti (net des retours), Reste | identiques (serveur) | — |
| Arrivée `?q=` coche « épuisés » ; `?article=` pose la matière | `?q=` idem ; `?matiere=` | — |
| KPI Lots affichés (« N en stock »), Reste (Σ, « dans les lots affichés »), En quarantaine (« X kg à libérer ou rendre » / « aucun lot bloqué », ton), Ordres servis (« par les lots affichés ») | `Kpi` identiques ; En quarantaine cliquable (filtre) | — |
| Recherche « Lot, matière, couleur, fournisseur, ordre… plusieurs mots affinent » | `Recherche` | — |
| Liste de tri (4 ordres, défaut référence puis entrée) | tri par en-tête (Référence, Dernier mouvement, Entré le, Reste) ; défaut identique | composant standard |
| « Étiquettes (N) » (grisé si 0, sans raison) | `BoutonImprimer` « Étiquettes (N) » `Bouton({manque:['cocher au moins un lot']})` | P2-11 |
| Filtres liés « Tous les fournisseurs (n) », « Toutes les matières (n) », « Tous les magasins (n) », « Tous les rôles (n) » (infobulles) ; case « Voir aussi les lots épuisés » ; « Effacer les filtres » | `Filtres` liés identiques + case ; « Effacer » dès 2 + « N critère(s) » | A1 |
| Colonnes : ☐ (« Cocher tous les lots affichés »), Lot (mono, badge statut, « entré le »), Référence (« rôle · fournisseur »), Dernier mouvement, Entré, Sorti, Reste (gras), Bobines, Magasins (badge quarantaine), Ordres servis (≤ 2 sinon « N ordres »), « Suivre » | identiques ; Entré/Sorti/Reste en `KgEtMetres` ; ordres en `LienDocument` | — |
| Ligne → fiche de lot ; pas de pied, pas de pagination | ligne → `/lots/{id}` ; pied Σ Reste | pied ajouté |
| Vides « Aucun lot ne correspond. » / « Aucun lot : les lots naissent des réceptions et des stocks d'ouverture. » ; chargement « … les lots… » | identiques | — |
| Pas d'export | `ExportExcel` (route ajoutée, API-PRO § 1.24 : GET `export/lots`) | P2-19 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Étiquettes (N) | C | GET `/api/documents/etiquettes?lots=1,2` | manque si 0 coché | raison dite |
| Cocher / tout cocher | C | — | — | — |
| Suivre (infobulle « D'où vient ce lot, quels ordres il a servis, et quand ») | C | GET `tracabilite?lot_id=` | — | `/tracabilite?lot={id}` |
| clic ligne | C | GET `lots/{id}` | — | `/lots/{id}` |
| Effacer les filtres | C | — | — | — |
| (nouveau) Exporter en Excel | C | (route ajoutée, API-PRO § 1.24 : GET `export/lots`) | — | — |

Document « Étiquettes de lots » : voir Partie 1 (`GET /api/documents/etiquettes`).

---

### Fiche de lot (fenêtre du Stock) — `/lots/:id`

Gestion MP : `DialogueLot` / `FicheLotBureau` / `Liberation` (`Stock.tsx:579-763`) → PRO : la fiche unique décrite
en Partie 1 (« Fiche de lot — `/lots/:id` »), C ; Libérer D, A.

**Ce qu'on voit** — reprise intégrale (titre « {référence} — lot {n°} », « Lot » en chargement ; KPI Reste, Disponible,
Entré · sorti → Entré / Sorti, kg / bobine, Entré le ; ligne de réception ; soldes ; ordres servis ; bloc Libérer ;
mouvements Date · Mouvement · Document · Magasin · Quantité · Par ; pied) ; `lienDocument` GMP (sortie, opération [A/D ;
retour rattaché → l'ordre pour L], réception, inventaire) → `LienDocument` PRO (`/ordres/{id}`, `/operations/{id}` [L
compris pour transferts et retours machine], `/receptions/{id}`, `/inventaires/{id}`).

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Où ce lot est-il allé ? | C | GET `tracabilite` | — | `/tracabilite?lot=` sans changer d'onglet (P2-18) |
| Libérer | D, A | POST `operations (valider: true)` | `Confirmer` « Libérer X kg : la matière devient disponible pour les machines ? » ; refus GMP gardés (dont « Un transfert va d'un magasin à un autre. », « L'inventaire INV-… est en cours sur « MAG »… », « Le lot « N » de « REF » ne porte que X kg… », date) | tous magasins de quarantaine (P1-17) |
| Page du lot | C | — | — | supprimé (adresse `/lots/:id`) |
| Imprimer l'étiquette | C | GET `/api/documents/etiquettes?lots={id}` | — | — |

---

### Stock › Mouvements de stock — `/stock?onglet=mouvements`

Gestion MP : `Stock.tsx:406-575` → PRO : `Recherche` (serveur), `Filtres`, `DataTable`, `ChargerPlus`, `ExportExcel`, C (prix D,A).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/mouvements?q&type&magasin_id&du&au&limite=500&decalage&avec_valeur` ; `suivant` ; `types` | GET `mouvements` (pages de 500) | — |
| Recherche serveur ILIKE (référence, désignation, lot, document, motif, commentaire, auteur), temporisée 300 ms | `Recherche` → `?q=` serveur **sans accents**, tous les mots (A6) | P2-20 |
| Filtres : « Tous les types » (7 types), « Tous les magasins » (actifs ou non), « Du », « Au », « Effacer les filtres » ; non liés | `Filtres` liés (le serveur renvoie types et magasins présents compte tenu des autres filtres) ; `DateChamp` ; « Effacer » dès 2 + « N critère(s) » | A1 |
| « Exporter en Excel » → `/api/export/mouvements?…` (sans limite, sans prix pour L) | `ExportExcel` GET `export/mouvements` (mêmes filtres) | — |
| Note « N mouvement(s) affiché(s)[, d'autres plus anciens suivent] — le plus récent d'abord.[ La valeur est au coût moyen du moment…] Le document s'ouvre d'un clic. » | `Note` identique | — |
| Colonnes : Date (note « saisi … »), Type (badge « annulation »), Document (lien), Référence, Lot · magasin (bouton-lien « La fiche du lot »), Quantité (« +X,X » sans unité), Prix (D,A, « 0,000 DEV »), Valeur MAD (D,A ; infobulle coût unitaire), Motif (note commentaire), Par | identiques ; « Quantité (kg) » ; Prix « 0,000 DEV / kg » ; Document `LienDocument` ; lot → `/lots/{id}` | P2-15 |
| Infobulle de ligne = commentaire ; ligne non cliquable | identique | — |
| « Charger les 500 suivants » (« Lecture… ») | `ChargerPlus` | — |
| Vide « Aucun mouvement ne correspond. » ; chargement « … les mouvements… » | identiques | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Effacer les filtres | C | — | — | — |
| Exporter en Excel | C | GET `export/mouvements` | — | — |
| Charger les 500 suivants | C | GET `mouvements?decalage=` | occupe | — |
| ouvrir le lot | C | GET `lots/{id}` | — | `/lots/{id}` |
| lien document | selon rôle | — | — | `LienDocument` |

---

### Stock › Ordres de fabrication — `/stock?onglet=ordres`

Gestion MP : `Tracabilite.tsx:131-250` (`VueOrdres`) → PRO : `Indicateurs`, `Recherche`, `Filtres`, `DataTable`, `ExportExcel`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/ordres-fabrication` (annulés exclus, fin la plus récente d'abord) | GET `ordres/consommation` | renommage |
| Chargement « … les ordres de fabrication… » ; erreur | identiques | — |
| KPI Ordres de fabrication (« sur N »), Sorti net (« X kg revenus, déduits » / « aucun retour »), Prévu par la recette (« N ordre(s) selon recette »), Écart (`EcartRecette`, « X kg sortis pour Y prévus ») | `Kpi` identiques | — |
| `EcartRecette` : ≤ 5 % ok, > +5 % attention, < −5 % critique | `Badge` écart (une seule règle, P2-8) | — |
| Recherche « Un ordre, une qualité, une référence, un lot… plusieurs mots affinent » ; « Du »/« Au » (chevauchement) ; « Effacer » ; note « le plus récent d'abord · « Suivre » : quelles matières et quels lots sont partis dans l'ordre » | identiques ; `Filtres` + « N critère(s) » | — |
| Colonnes Ordre, Date (« → fin »), Fabrication (code + « X m² » / « hors recette »), Prévu par la recette, Sorti net (« dont X revenus »), Écart, Matières (≤ 2 / « N matières »), Lots (« — sans lot »), « Suivre » | identiques, kg en `unite` ; Ordre en `LienDocument` `/ordres/{id}` | — |
| Ligne → suivi | ligne → `/tracabilite?ordre={id}` | — |
| Vides « Aucun ordre ne correspond. » / « Aucun ordre de fabrication au journal. » | « … » / « Aucun ordre de fabrication validé. » | P2-2 |
| Pas d'export | `ExportExcel` GET `export/ordres?vue=consommation` | P2-19 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Effacer les filtres | C | — | — | — |
| clic ligne / Suivre (infobulle « Quelles matières et quels lots sont partis dans cet ordre ») | C | GET `tracabilite?ordre=` | — | `/tracabilite?ordre=` |
| (nouveau) Exporter en Excel | C | GET `export/ordres` | — | — |

---

### Suivi de traçabilité — `/tracabilite?ordre=|lot=|matiere=` (fenêtre sur `/stock?onglet=ordres`)

Gestion MP : fenêtre de suivi (`Tracabilite.tsx:260-476`, ouverte par `?lot_id=|ordre=|reference=` sur tout onglet)
→ PRO : `Fenetre({taille:tresLarge})` empilable, `Kpi`, `Bascule`, `DataTable`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titres « Traçabilité du lot {n°} » / « Ordre de fabrication OF-… » / « Parcours de la matière {REF} » | identiques | — |
| GET `/tracabilite?lot_id|ordre|reference` ; `/ordres-fabrication` pour la comparaison ; refus 400 « préciser un lot, un ordre de fabrication ou un fil », 404 « Lot introuvable. » | GET `tracabilite` (comparaison par matière incluse) ; 400 « préciser un lot, un ordre de fabrication ou une matière » | vocabulaire |
| Fil d'Ariane : « ← Revenir au {lot N | ordre OF-… | matière REF} » + « Chemin : a → b → c » (pile locale perdue) | `EnTete` de fenêtre : fil d'Ariane gardé dans l'adresse (`&depuis=`), « ← Revenir au lot N / à l'ordre OF-… / à la matière REF » | P2-17 ; retour arrière du navigateur |
| « Ouvrir l'ordre » (`/sorties?ordre=` ; « L'ordre de fabrication, ses lots et ses retours ») ; « Fiche du lot » (`/lot/ID`) | → `/ordres/{id}` ; → `/lots/{id}` | adresses stables |
| KPI Entré, Sorti, Ordres servis (3 premiers), Lots consommés / Lots, Matières / Reste (entré − sorti) ; hors annulations et transferts ; retours réduisent le sorti | `Kpi` identiques, kg | — |
| Bascule « Prévu et sorti, par matière (N) » / « Mouvements (N) » | `Bascule` `?vue=` | — |
| Sous-vue par matière : note « Tissé sous cet ordre : … » ; Référence (lien « Suivre cette matière », « · hors recette », « · pas sorti »), Prévu par la recette (kg), Sorti net (kg), Écart (kg), Écart % ; pied Total | `DataTable` identique + pied | — |
| Sous-vue Mouvements : note « Le plus récent en haut… » ; Date, Mouvement (libellés locaux dont « Ajustement » ; « Annulation — … » + badge ; badge « annulé »), Document (pas de lien), Référence (lien), Quantité (± couleur ; transfert neutre), Lot (lien), Ordre (lien), Magasin (« source → destination »), Par ; vide « Aucun mouvement. » | identique ; libellés du **serveur** (« Ajustement d'inventaire ») ; Document en `LienDocument` ; « Quantité (kg) » | P2-17, P2-15 |
| Chargement « … la traçabilité… » | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| ← Revenir au … | C | GET `tracabilite` | — | libellé corrigé |
| Ouvrir l'ordre | C | — | — | `/ordres/{id}` |
| Fiche du lot | C | — | — | `/lots/{id}` |
| liens de suivi (référence, lot, ordre) | C | GET `tracabilite` | — | adresse mise à jour |
| Bascule (2 vues) | C | — | — | — |
| × / Échap | C | — | — | revient à l'onglet d'origine |

---

### Stock › À valider — `/stock?onglet=a-valider`

Gestion MP : `AValider.tsx` → PRO : `Indicateurs`, `Recherche`, `Filtres`, `DataTable`, `Confirmer`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Qui valide quoi : ordre → L (+D) ; ouverture, ajustement, retour fournisseur → A (+D) ; transfert → A, L ; retour machine → L (+D) | droits du contrat : ordre D,L ; ouverture/ajustement/retour fournisseur D,A ; transfert D,A,L ; retour machine D,L | — |
| GET `/brouillons` (`genre, type, id, date, libelle, resume, quantite, cree_par, cree_le, blocages, peut_valider, lien` ; `nombre, bloques, validables`) ; tri date, rang, id | GET `brouillons` + `valide_par` (libellé des rôles qui valident) | P2-13 |
| KPI Brouillons (« ordres et opérations, le stock n'a pas bougé »), Seraient refusés (ton critique/ok), Que vous pouvez valider (blocages compris, « selon votre rôle ») | `Kpi` ; « Que vous pouvez valider » = `validables` (**sans** les bloqués) | P2-12 |
| Recherche « Type, matière, motif, personne, raison… » ; case « Seulement ceux qui seraient refusés » ; « Effacer » ; « Tout valider (N) » | identiques ; `Filtres` (type, auteur) liés | — |
| Colonnes Date, Document (libellé ; « Brouillon »), Contenu, Quantité (1 déc.), Par (horodatage), À la validation (« sera refusé : {raison} » / badge « passera » ; note « validé par l'alimentation »/« par les achats »), « Ouvrir » ; ligne rouge pâle si blocages | identiques ; « Quantité (kg) » ; note = `valide_par` serveur ; `Blocages` | P2-13, P2-15 |
| « Ouvrir » → `/sorties?onglet=brouillon&ordre=` ou `/operations?onglet=TYPE&operation=` | → `/ordres/{id}` ou `/operations/{id}` (L ouvre ses transferts et retours) | P2-13 |
| Vides « Aucun brouillon ne correspond. » / « Aucun brouillon : tout ce qui a été saisi est validé. » | identiques | — |
| Blocages serveur (ordre : « aucune matière à sortir », dates, « un ordre daté du … est déjà validé… », quarantaine, inventaire, « qualité arrêtée », lots épuisés/entrés après/insuffisants ; opération : « aucune ligne », date, inventaire, lot insuffisant) | identiques, champ `blocages` des fiches (A8) | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Tout valider (N) (infobulle « Valide chaque brouillon que votre rôle permet, dans l'ordre des dates ; le stock bouge pour chacun ») | C | POST `brouillons/valider {documents: [{genre, id, version}]}` (ou `{tous: true}`) → `{valides, refuses, ignores}`, chaque élément avec sa `raison` | N = validables sans blocage ; `Bouton({manque})` si 0 ; `Confirmer` « Valider N brouillon(s), du plus ancien au plus récent ? Ceux qui sont refusés restent en brouillon. » · « Non » · « Oui, tout valider » | bilan en `Messages` : « N brouillon(s) validé(s) : OF-…, TRF-…. » + « N refusé(s), restés en brouillon : … » (liens) |
| Ouvrir | C | — | — | adresses stables accessibles au rôle |
| Effacer les filtres | C | — | — | — |

---

### Sorties vers les machines — `/sorties?onglet=valide|brouillon|annule`

Gestion MP : `pages/Sorties.tsx:57-261` → PRO : `/sorties` (`EnTete`, `Indicateurs`, `Onglets`, `Recherche`,
`Filtres`, `DataTable`, `ExportExcel`), C ; écriture D, L.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Sorties vers les machines » ; sous-titre « Chaque ordre de fabrication : la matière partie, les retours, et l'écart avec ce que prévoit la recette. » | identique | — |
| Garde A, L (+D) ; « Nouvelle sortie » L, D ; aucun prix | C ; « Nouvelle sortie » D, L | — |
| `?onglet=` (défaut `valide`), `?ordre=` (id ou n°) ouvre le détail | `useOngletAdresse` ; détail = `/ordres/{id}` ; ancien `?ordre=` redirigé | A5 |
| GET `/bons` (tous les ordres, champs `numero, statut, date, magasin, metier, commentaire, cree/valide, fabrications, lignes, total, retours, retours_detail, revenu, theorique, net, ecart, ecart_relatif, par_fil, blocages`) | GET `ordres` (mêmes champs) | `/bons` → `/ordres` |
| Chargement « … les sorties… » | « … les ordres… » | — |
| KPI Ordres affichés (« du … au … » / « toute la période ») | `Kpi` | — |
| KPI Sorti net / « À sortir » (Brouillons) (« rien n'a encore bougé au stock » / « retours déduits : X kg revenus » / « aucun retour ») | `Kpi` identique | — |
| KPI Écart à la recette (« X kg sortis pour Y kg prévus » ; ton ok ≤ 5 %, sinon attention) | ton : ok ≤ 5 %, attention > +5 %, **critique** < −5 % | P2-25 |
| KPI Brouillons (« N seraient refusés » / « à valider » ; ton critique/attention/ok) | `Kpi` → `?onglet=brouillon` | cliquable |
| Onglets « Validées », « Brouillons », « Annulées » (comptes filtrés par période) | `Onglets` identiques | — |
| Recherche « N° d'ordre, qualité, fil, lot, métier, commentaire… » | « N° d'ordre, qualité, matière, lot, métier, commentaire… » | P2-1 |
| « Du » / « Au » ; « Effacer les filtres » | `DateChamp` ; `Filtres` liés (métier, magasin, qualité) + « N critère(s) » | A1 |
| « Exporter en Excel » → `/api/export/sorties?statut&du&au` (infobulle ; colonnes Ordre [« Brouillon »], Date, Fabrication, m², Métier, Magasin, Prévu par la recette (kg), Sorti net (kg), Écart (kg), Écart, Revenu (kg), Retours, Commentaire, Par) | `ExportExcel` GET `export/ordres?statut=&du=&au=` (mêmes colonnes) | renommage |
| Onglet Brouillons : « Tout valider… » → `/stock?onglet=a-valider` (infobulle) | identique | — |
| Note « N ordre(s) · X kg à sortir à la validation. » / « … sortis nets, retours déduits (dont Y kg revenus). » | `Note` | — |
| Message de succès persistant (jamais effacé) | `Messages` (toast) | P2-14 |
| Colonnes Ordre (n° ou « sans n° » ; « sera refusé » rouge, infobulle raisons), Date, Fabrication (« QUAL · X m² » / « hors recette » ; commentaire), Métier, Prévu par la recette, Sorti net (brouillon : `total` ; « dont X revenus »), Écart (`EcartOrdre`), Retours (RET-… ou « retour repris de l'ERP Fil du … »), Par | Ordre : n° ou « Brouillon » (P2-3) ; en-tête « À sortir » sur l'onglet Brouillons (P2-4) ; kg en `unite` ; Retours en `LienDocument` `/operations/{id}` ; Écart `Badge` unique | P2-3, P2-4, P2-8 |
| Ligne cliquable ; rouge pâle si blocages ; vide « Aucun ordre ici. » | ligne → `/ordres/{id}` ; `Vide` « Aucun ordre dans cet onglet. » | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Nouvelle sortie | D, L | — | — | → `/ordres/nouveau` |
| Effacer les filtres | C | — | — | — |
| Exporter en Excel | C | GET `export/ordres` | — | — |
| Tout valider… | C | — | ≥ 1 brouillon | → `/stock?onglet=a-valider` |
| clic ligne | C | GET `ordres/{id}` | — | `/ordres/{id}` |

---

### Fiche d'ordre — `/ordres/:id` (fenêtre sur `/sorties`)

Gestion MP : fenêtre « Détail d'un ordre » (`Sorties.tsx:263-431`) → PRO : `Fenetre({taille:tresLarge})`, `Kpi`,
`Blocages`, `Bascule`, `DataTable`, `Confirmer`, C ; gestes D, L.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « OF-… — {date} » / « Ordre du {date} » + badge (« Brouillon » attention, « Validé » ok, « Annulé » neutre) | identique ; brouillon « Brouillon du {date} » | — |
| Ligne d'info « Magasin X · métier Y · saisi par Z le … · validé par W le … · « commentaire » » | `Definitions` (Magasin, Métier, Par, Validé par, Commentaire) | « saisi par » → « Par » (vocabulaire) |
| KPI Fabrication (« X m² » / « hors recette » ; « QUAL X m² · … » / « échantillons, série spéciale ») ; Prévu par la recette ; Sorti net / À sortir (« X kg sortis, dont Y kg revenus ») ; Écart (« +X kg ») | `Kpi` identiques | — |
| Bandeau rouge « Sera refusé à la validation : » + raisons | `Blocages` (« sera refusé : … ») | — |
| Bascule « Lots sortis (N) » / « Lots à sortir (N) » ; « Prévu par la recette et sorti net, par matière (N) » ; note « Retours : RET-… du … (X kg) » | `Bascule` `?vue=` ; retours en `LienDocument` | — |
| Sous-vue Lots : Référence (infobulle désignation), Lot (lien `/lot/ID`), Sorti / À sortir (≈ ml) | lot → `/lots/{id}` ; `KgEtMetres` | — |
| Sous-vue par matière : Référence (+ « hors recette »), Prévu par la recette, Sorti net, Écart, Écart % ; vide « Calculé à la validation. » / « Ordre hors recette : rien à comparer. » | identique | — |
| Pied : « Traçabilité de l'ordre » (infobulle « Quels fils et quels lots sont partis dans cet ordre, et d'où ils venaient ») ; boutons selon statut ; « Fermer » | infobulle « Quelles matières et quels lots… » (P2-1) ; `Historique` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Supprimer (infobulle « Supprimer le brouillon : rien n'a bougé au stock ») | D, L (brouillon) | DELETE `ordres/{id}` | `Confirmer` « Supprimer ce brouillon ? » · « Non » · « Oui, supprimer » ; refus « Un ordre validé ne se supprime pas : l'annuler. », « Ordre introuvable. » | toast « Brouillon supprimé. » visible après fermeture (P2-14) |
| Modifier (« Rouvrir la saisie : qualités, lots, quantités ») | D, L (brouillon) | — | — | bascule la fenêtre en saisie (même adresse `/ordres/{id}`) |
| Valider la sortie (« Valider : le stock sort et l'ordre reçoit son numéro ») | D, L (brouillon) | POST `ordres/{id}/valider` | `Bouton({blocages})` (raisons en infobulle, P2-11) ; `Confirmer` « Sortir X kg du stock ? » · « Non » · « Oui, valider » ; refus GMP gardés (déjà validé, dates, qualité arrêtée, lots manquants à la date, ordre postérieur validé, inventaire, lot insuffisant) | toast « Ordre {OF-…} validé : le stock est sorti. » |
| Faire un retour (« Ce qui revient des machines, lot par lot ») | D, L (validé) | — | — | → `/ordres/{id}/retour` |
| Annuler (contre-passation) (« … une écriture inverse remet la matière en stock ») | D, L (validé) | POST `ordres/{id}/annuler` | `Confirmer` (motif facultatif) : « Annuler l'ordre ? Toute sa matière revient en stock, à la date de l'ordre. » / « Annuler l'ordre et ses retours (RET-…) ? La matière sortie revient en stock, une seule fois, à la date de l'ordre. » · « Non » · « Oui, annuler (contre-passation) » ; refus « Seul un ordre validé s'annule ; un brouillon se supprime. », « Ce document a déjà été annulé. », inventaire, période close | toast « Ordre annulé. » |
| Fermer | C | — | — | → `/sorties` avec filtres et onglet |
| Traçabilité de l'ordre | C | — | — | → `/tracabilite?ordre={id}` (empilée) |
| Bascule (2 vues) | C | — | — | — |

---

### Saisie d'ordre — `/ordres/nouveau` ; modification d'un brouillon `/ordres/:id`

Gestion MP : fenêtre « Nouvelle sortie vers les machines — Brouillon » / « Modifier l'ordre — Brouillon »
(`SaisieSortie.tsx`, `atelier/sortie.ts` partagé avec le téléphone) → PRO : `Fenetre({taille:tresLarge, sale, pied})`,
`Form`, `DateChamp`, `Selecteur`, `Bascule`, `Quantite`, `SelecteurLot`, `Blocages`, `Confirmer` ; moteur de saisie
partagé `frontend/src/lib/ordre.ts` (bureau et atelier), D, L.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Nouvelle sortie vers les machines — Brouillon » / « Modifier l'ordre — Brouillon » | « Nouvel ordre — Brouillon » / « Modifier l'ordre — Brouillon » | vocabulaire « ordre » |
| `sale` = saisie touchée (garde sur ×, Échap, fond) | `sale` (garde aussi sur « Fermer » et à la navigation) | — |
| Données `/magasins`, `/metiers`, `/qualites`, `/soldes?magasin_id=`, POST `/bons/proposition`, `/inventaires`, `/bons` (dernier validé) | GET `magasins`, `metiers`, `qualites` ; GET `lots/disponibles?magasin_id=&date=` ; POST `ordres/proposition` (renvoie aussi `blocages` : inventaire, date du dernier ordre) | lots à la date de l'ordre (P2-23) ; empêchements calculés par le serveur |
| Bandeaux d'empêchement : « L'inventaire INV-… (MAG, du …) est en cours : les mouvements y sont suspendus… Garder en brouillon, ou attendre. » ; « Un ordre du … est déjà validé : les numéros suivent les dates… Pour un oubli, le dater du … et écrire la vraie date dans le commentaire. » | `Blocages` en tête, mêmes textes | — |
| Date (max aujourd'hui usine) | `DateChamp` (max jour serveur, min = max(lendemain de clôture, date du dernier ordre validé)) | refus annoncé |
| Magasin de sortie (actifs hors quarantaine ; défaut le plus garni ; aide « changer de magasin efface les lots choisis ») | `Selecteur` identique | — |
| Métier (« — » + actifs « CODE · Nom ») | `Selecteur` | — |
| Commentaire (300, « Équipe, consigne, incident… ») | `Zone` | — |
| « 1 · Ce qu'on tisse » : Bascule « Selon les recettes » / « Ordre hors recette » ; notes ; Qualité (« Code ou nom de la qualité… », « CODE — Nom »), m² à tisser, « Retirer » ; « + Une autre qualité » ; « Proposer les fils à sortir » / « Recalculer les fils » (infobulle) ; note « La demande a changé : recalculer remplace les lots proposés (les fils ajoutés à la main restent). » | identiques ; libellés « Proposer les matières à sortir » / « Recalculer », note « … (les matières ajoutées à la main restent) » | P2-1 |
| Proposition serveur (kg/m² × m² × (1 + perte) ; lots les plus anciens à la date ; `manque` ; `recettes_incompletes` 2 textes ; refus « Qualité inconnue. », « La qualité Q est arrêtée… ») | identique (POST `ordres/proposition`) | — |
| « 2 · Les fils qui sortent » : « Recette incomplète — … » (rouge) ; « Il manque dans ce magasin : REF (X kg) · … Les transférer d'abord, ou sortir ce qu'il y a… » | « 2 · Les matières qui sortent » ; mêmes messages (`Note`) | P2-1 |
| Tableau : Fil (référence, rôle / « hors recette », « + un autre lot… »), Prévu par la recette (« N qualités »), Lot, Dans ce lot, Unité (kg / bobines (X,XX kg) / palettes (N bob.) ; « arrondi : … »), Quantité, Sorti (« poids de bobine inconnu », « plus que le lot »), Écart du fil (`EcartFil`), « retirer » | colonnes « Référence », …, « Écart » ; `Quantite` (unité + arrondi dit) ; `SelecteurLot` « + un autre lot… » ; Dans ce lot = disponible **à la date de l'ordre** | P2-1, P2-23 |
| Lignes : « aucun lot pris[ — rien dans ce magasin] » ; rouge pâle si dépassement ; vides « Choisir ce qu'on tisse puis « Proposer les fils à sortir »… » / « Ajouter un fil ci-dessous. » ; pied Total | identiques (« … Proposer les matières à sortir… », « Ajouter une matière ci-dessous. ») | P2-1 |
| « + Ajouter un fil hors recette : référence ou lot… » / « + Ajouter un fil : référence ou lot… » (« REF · lot N », « X kg ») | `SelecteurLot` « + Ajouter une matière hors recette : référence ou lot… » | P2-1 |
| Brouillon rouvert : bobines si entier ; prévu relu à la date | identique | — |
| Pied : note « N ligne(s) · X kg » | identique | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule « Selon les recettes » / « Ordre hors recette » | D, L | — | — | — |
| « + Une autre qualité » | D, L | — | — | — |
| « Retirer » (qualité) | D, L | — | — | — |
| « Proposer les fils à sortir » / « Recalculer les fils » | D, L | POST `ordres/proposition` | `Bouton({manque:['magasin','date','qualité','m²']})` | P2-11 |
| « + un autre lot… » | D, L | GET `lots/disponibles` | — | `SelecteurLot` |
| « retirer » (lot ; infobulle « Ne pas prendre ce lot ») | D, L | — | — | — |
| changer d'unité | D, L | — | arrondi dit | `Quantite` |
| « + Ajouter un fil… » | D, L | GET `lots/disponibles?date=` | — | dispo à la date (P2-23) |
| Fermer (Confirmer « Abandonner cette saisie ? » · « Oui, abandonner » ; infobulle « Fermer sans enregistrer ») | D, L | — | garde `sale` unique de `Fenetre` | libellé unique |
| Garder en brouillon (« Enregistrer sans sortir le stock : l'ordre reste modifiable ») | D, L | POST `ordres` / PUT `ordres/{id}` | `Bouton({manque:['au moins une ligne > 0','contenance de la ligne …']})` ; refus GMP gardés (magasin inconnu, quarantaine « … la libérer d'abord… », métier, dates, « Une qualité ne figure qu'une fois sur un ordre… », lot inconnu, unités, poids de bobine, « Un ordre validé ne se modifie plus : l'annuler, puis en faire un autre. ») | toast « Ordre gardé en brouillon : le stock n'a pas bougé. » ; → `/ordres/{id}` (onglet Brouillons) |
| Valider la sortie | D, L | POST/PUT `ordres` puis POST `ordres/{id}/valider` | `Bouton({manque, blocages})` (raison en infobulle, P2-11) ; `Confirmer` « Sortir X kg le {date} ({aujourd'hui|hier}) · MAG · CODE · Métier ? Le stock est débité tout de suite. » · « Non » · « Oui, valider la sortie » ; refus suffixé « — l'ordre est gardé en brouillon, modifiable. » | toast « Ordre OF-… validé : X kg sortis. » ; → `/ordres/{id}` (onglet Validées) |

---

### Retour des machines — `/ordres/:id/retour` (fenêtre sur `/sorties`)

Gestion MP : fenêtre « Retour des machines — OF-… » (`RetourBureau.tsx`) → PRO : `Fenetre({taille:tresLarge, sale})`,
`Form`, `Quantite`, `Confirmer`, D, L (opération `retour_machine`).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Retour des machines — OF-… » | identique | — |
| Données GET `/bons/{id}/lots-sortis` (net des retours, > 1 g), `/operations/motifs`, `/magasins`, `/inventaires` | GET `ordres/{id}/lots-sortis`, GET `motifs`, GET `magasins` ; blocage inventaire dans la réponse | renommages |
| `sale` si quantité > 0 ou commentaire | `sale` | — |
| Bandeau de suspension d'inventaire | `Blocages` | — |
| Date du retour (min date de l'ordre, max aujourd'hui) | `DateChamp` mêmes bornes | — |
| Ranger dans le magasin (défaut magasin de l'ordre) | `Selecteur` | — |
| Pourquoi revient-elle ? (« R1 · Reliquat de fin d'ordre », « R2 · Changement de série / arrêt machine », « R4 · Erreur de prélèvement » ; défaut le premier) | `Selecteur` (motifs du serveur) | — |
| Commentaire (300, « Bobines entamées, arrêt du métier… ») | `Zone` | — |
| « Tout ce qui est parti sur cet ordre est déjà revenu. » | `Note` | — |
| Tableau Référence, Lot, Parti (net), Unité, Revient, Soit (« plus que ce qui est parti »), « tout » | identique ; `Quantite` ; « Soit (kg) » | — |
| Pied : raison grise (« Un inventaire est en cours… », « N lot(s) dépassent ce qui est parti », « Saisir ce qui revient, lot par lot ») ; « Fermer » ; bouton principal | raisons portées par `Bouton({manque, blocages})` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Remettre X kg en stock » (« Le retour est validé tout de suite : le stock remonte ») | D, L | POST `operations` {valider: true, type `retour_machine`, `ordre_id`, date, motif, commentaire, lignes} (route ajoutée, API-PRO § 1.24 : variante `?valider=1`) | `Confirmer` « Remettre X kg en stock (MAG) ? » · « Non » · « Oui, enregistrer le retour » ; refus GMP (« Un retour des machines se rattache à l'ordre d'où la matière revient. », « Le lot « N » n'est sorti que de X kg pour cet ordre… », date antérieure, inventaire, magasin désactivé, dates, unités) | une transaction (plus de DELETE) ; toast « RET-… enregistré : la matière est revenue en stock. » |
| tout | D, L | — | — | — |
| Fermer | D, L | — | garde `sale` | P2-10 |

---

### Production & besoins — `/production?onglet=plan|glissant|realise|besoins`

Gestion MP : `pages/Production.tsx` → PRO : `/production` (`EnTete`, `Indicateurs`, `Onglets`), C ; plan écrit par D.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Production & besoins » ; sous-titre « Plan glissant sur douze mois dès {mois année} (base mensuelle × saisonnalité) ; les besoins matière en découlent par les recettes, perte comprise. » + « Lecture seule : seule la direction modifie le plan. » (non-D) | identique | — |
| Onglet lu ; Plan → pas de paramètre ; ancien `?volet=` | `useOngletAdresse` ; `?volet=` redirigé | — |
| GET `/production/plan`, `/production/realise`, `/production/besoins` (à l'ouverture de Besoins) | GET `production/plan`, `production/realise`, `production/besoins` | — |
| Chargements / erreurs (« … le plan de production… », « Le plan de production est indisponible. », « … le réalisé… », « Le réalisé est indisponible. », « … les besoins matière… », « Les besoins sont indisponibles. ») | `Chargement` / `Erreur` mêmes textes | — |
| Brouillon du plan survit au changement d'onglet ; `beforeunload` seul | brouillon gardé ; garde de navigation (menu, lien, retour) « Des modifications ne sont pas enregistrées. Les abandonner ? » | P2-10 |
| KPI Plan des douze mois à venir (« X m² par mois en moyenne · N qualité(s) ») | `Kpi` | — |
| KPI Mois en cours (« tissés sur Y prévus (Z %) · W % du mois écoulé » / « aucun plan ce mois-ci » ; attention si > 20 % écoulé et < prorata − 15 pts) | `Kpi` + `Formule` | — |
| KPI Écart au plan, mois clos (`signe` ; « … » ; « — » ; ok ≤ 10 %) | `Kpi` → `?onglet=realise` | cliquable |
| KPI Matière nécessaire sur douze mois (infobulle « Les fils, et le cuir… ») ; « perte de X,X % comprise » | `Kpi` → `?onglet=besoins` ; infobulle « Les matières, cuir, franges et ruban compris (leurs mètres × densité)… » | P2-1 |
| KPI masqués sur Besoins | identique | — |
| Onglets « Plan de production » (« N modifiée(s) »), « Plan glissant », « Plan et réalisé », « Besoins matière » (compteur) | `Onglets` identiques | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| changement d'onglet | C | — | — | — |

---

### Production › Plan de production — `/production?onglet=plan`

Gestion MP : `VoletPlan.tsx` → PRO : `Carte`, `Bascule`, `Recherche`, `Interrupteur`, `DataTable` éditable (colonne
figée, pied figé), `Nombre`, `Confirmer`, C (écriture D).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Plan de production — m² par qualité » + Bascule « Coefficients » / « m² par mois » | identique (`?vue=`) | — |
| Recherche « Qualité, nom… » ; case « Inactives (N) » ; D en saisie : « Tout annuler », « Enregistrer tout (N) » | `Recherche`, `Interrupteur`, `Bouton`s | — |
| Lignes : actives, + inactives si cochées, + modifiées | identique | — |
| Colonnes Qualité (code, nom ; D : « Enregistrer » · « Annuler » ; filet bleu si modifiée ; inactive grisée), Base / mois (« m² », saisissable dans les deux vues), Janv.…Déc. (« coef. »/« m² », mois courant surligné ; pas 0,05 / 1 ; rouge hors [0 ; 20] « Un coefficient reste entre 0 et 20 »), Total / an (« coef. moyen 1,08 », infobulle), État (« inactive, hors plan », « sans recette », « recette incomplète », « au plan », « pas de plan ») | identiques ; `Badge` État ; « recette incomplète » → lien `/qualites/{id}?onglet=recette` | lien vers la recette |
| `depuisM2` (base = moyenne arrondie 0,01 ; coef = m² ÷ base, 6 déc. ; base ≤ 0 → 0 et 1) | **changé le 12/10/2026 (Mohamed)** : les m² d'un mois donnent son seul coefficient (m² ÷ base, 6 déc.) ; la base ne change jamais d'elle-même ; base ≤ 0 → cellules m² grisées (« Saisir d'abord la base / mois… ») | la base n'est plus la moyenne |
| Pied « Total (m²) » ; note « qualités actives affichées » | pied de totaux | — |
| Vides « Aucune qualité ne correspond. » / « Aucune qualité : créez-les dans l'écran Qualités & recettes. » | « … dans l'écran Qualités et recettes. » (lien `/qualites/nouvelle`, D) | P2-22 |
| Notes (coefficient 1,2 ; m² → base moyenne ; plan glissant + croissance ; filet bleu) | `Note` ; en m² : « les m² d'un mois donnent son coefficient (m² ÷ base) ; la base ne change que si vous la saisissez » | — |
| Lecture (non-D) : valeurs, note « Lecture seule… » | identique | — |
| Version du plan tracée au journal (passé jugé sur le plan de son époque) | identique ; `Historique` + GET `qualites/{id}/plan/versions` | — |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Coefficients / m² par mois | C | — | — | — |
| case « Inactives (N) » | C | — | — | — |
| Enregistrer (ligne) | D | PUT `qualites/{id}/plan {base_mensuelle, coefficients[12], motif, version}` (en entrée `coefficients`, rendus en `saisonnalite`) | `Bouton({manque:['coefficient entre 0 et 20']})` ; refus « Un coefficient de saisonnalité reste entre 0 et 20. », « Qualité introuvable. » | grisé avant refus (P2-12) ; toast « Plan de CODE enregistré : besoins en fil et plan d'achat sont recalculés. » |
| Annuler (ligne) | D | — | — | — |
| Tout annuler | D | — | `Confirmer` « Oublier les N modifications ? » · « Non » · « Oui, tout annuler » | P2-10 |
| Enregistrer tout (N) | D | PUT `production/plan {qualites:[{qualite_id, base_mensuelle, coefficients[12], version}], motif}` (tout ou rien) → `PlanProduction` + `modifiees` (nombre de qualités changées) ; version périmée : 409 nommant la qualité | `Bouton({manque})` coefficient hors bornes (raison dite, P2-11) ; refus « Une qualité apparaît deux fois… », « Qualité introuvable : le plan n'a pas été enregistré. », « CODE : un coefficient… Rien n'a été enregistré. » | toast « Plan enregistré pour N qualité(s)… » |

---

### Production › Plan glissant — `/production?onglet=glissant`

Gestion MP : `VoletGlissant.tsx` → PRO : `Carte`, `Bascule`, `Recherche`, `DataTable` (pied figé), `Barres`, `ExportExcel`, C (lecture).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Plan glissant — m² planifiés » + Bascule « Tableau » / « Graphique » ; recherche « Qualité, nom… » | identique | — |
| Message « N qualité(s) modifiée(s) dans le plan de production ne sont pas encore enregistrées… » | `Note` | — |
| Lignes : plan > 0 ou tissé ce mois | identique | — |
| Colonnes Qualité (figée), 12 mois (« oct. 2026 », « en cours » / « M+1 »… ; M0 « tissé X · Y % » + infobulle), Total (« 12 mois »), Fil (« kg/m² », infobulle « Fil consommé par m², perte comprise » ; « — » rouge « Aucune recette : ce plan ne tire aucun fil ») | colonne « Matière (kg/m²) », infobulle « Matière consommée par m², perte comprise » ; « Aucune recette : ce plan ne tire aucune matière » ; qualité → `/qualites/{id}?onglet=plan` | P2-1 |
| Pied « Total (m²) » (+ « tissé X ») ; « Matière nécessaire (kg) » (infobulle) | identique | — |
| Graphique barres empilées (7 + « Autres ») | `Barres` | — |
| Vides « Aucune qualité ne correspond. » / « Aucune qualité au plan : saisissez une base mensuelle dans le plan de production. » | identiques | — |
| Note « Base mensuelle × coefficient… perte de X % comprise. [N qualité(s) sans plan…] [Tissé ce mois-ci hors plan : …] » | identique | — |
| Pas d'export | `ExportExcel` (route ajoutée, API-PRO § 1.24 : GET `export/production?onglet=glissant`) | P2-19 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule Tableau / Graphique | C | — | — | — |
| (nouveau) Exporter en Excel | C | (route ajoutée, API-PRO § 1.24 : GET `export/production`) | — | — |

---

### Production › Plan et réalisé — `/production?onglet=realise`

Gestion MP : `VoletRealise.tsx` → PRO : `Carte`, `Bascule`, `Recherche` / `Selecteur`, `DataTable`, `Barres`, `ExportExcel`, C (lecture).

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/production/realise` (12 mois, `mois_clos`, plan en vigueur pendant chaque mois) | GET `production/realise` | — |
| Carte « Plan et réalisé — m², douze mois écoulés » + Bascule ; recherche « Qualité… » / liste « Toutes les qualités » | identique (`?vue=&qualite=`) | — |
| Deux lignes par qualité : Qualité (figée, rowSpan, « Cliquer pour voir son graphique »), « prévu » / « tissé », 12 mois (« en cours », « non compté » + infobulle), Total, Écart (« mois clos » ; `signe` ; ≤ 10 % ok, > attention, < critique ; « — » + infobulle ; « hors plan ») | identiques | — |
| Teinte tissé : rouge gras < −10 %, orange gras > +10 % | identique | — |
| Clic ligne (classe `clic` sans style) → graphique de la qualité | ligne cliquable standard (`DataTable`) | P2-9 |
| Graphique « Plan » (gris) / « Tissé » | `Barres` | — |
| Vides « Aucune qualité ne correspond. » / « Aucune qualité au plan, et aucun ordre de fabrication. » ; note « Tissé d'après les ordres… Un écart durable dit qu'il faut revoir la base ou la saisonnalité… » | identiques | — |
| Pas d'export | `ExportExcel` (route ajoutée, API-PRO § 1.24 : GET `export/production?onglet=realise`) | P2-19 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule Tableau / Graphique | C | — | — | — |
| clic qualité → graphique | C | — | — | — |
| choix de qualité (graphique) | C | — | — | — |
| (nouveau) Exporter en Excel | C | (route ajoutée, API-PRO § 1.24) | — | — |

---

### Production › Besoins matière — `/production?onglet=besoins`

Gestion MP : `VoletBesoins.tsx` → PRO : `Carte`, `Bascule`, `Recherche`, `Filtres` liés, `DataTable` (pied), `ExportExcel`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| GET `/production/besoins` (`mois, taux_perte, fenetre_realisation_jours, roles, lignes[…]`, aucun prix) | GET `production/besoins` | — |
| Carte « Besoins matière (MRP) » (infobulle « En kg, le cuir… compris… ») + Bascule « Besoin du plan » / « Retenu par le plan d'achat » | identique (`?vue=`) | — |
| Note « N référence(s)[ · M à commander] » ; « Ouvrir le plan d'achat → » (D,A ; « Ce qu'il faut commander, regroupé par fournisseur ») | identique | — |
| Explications (besoin du plan ; retenu × 0,5–1,5) + « Cliquer sur une référence pour voir les qualités qui la tirent. » | `Note` | — |
| Recherche « Référence, couleur, fournisseur, qualité… » ; « Tous les rôles » ; « Tous les fournisseurs » ; tri (« Les plus lourdes d'abord », « Couverture la plus courte », « Par référence », « Par fournisseur ») ; case « Avec besoin seulement » (cochée) ; pas d'« Effacer » | `Filtres` **liés** (rôle, fournisseur, qualité) + case + « Effacer les filtres » dès 2 + « N critère(s) » ; tri par en-tête (défaut total décroissant) | P2-19 |
| Colonnes Référence (figée ; « nature · désignation »), Rôle, Fournisseur, 12 mois (« en cours » / « M+i »), Total (≈ ml ; « × 0,00 » en Retenu), Disponible (« Stock disponible aujourd'hui, hors quarantaine »), Couverture (badge), À commander (≈ ml) | identiques ; Disponible infobulle « Le stock hors quarantaine : magasins et sur les métiers » | P2-6 |
| Ligne (« Les qualités qui tirent cette matière ») → détail ; pied Σ ; vides « Aucune référence ne correspond. » / « Aucun besoin : le plan de production est vide ou les recettes ne sont pas saisies. » | ligne → `/production/besoins/{matiereId}` ; pied ; `Vide` | A5 |
| Pas d'export | `ExportExcel` (route ajoutée, API-PRO § 1.24 : GET `export/production?onglet=besoins`) | P2-19 |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule de lecture | C | — | — | — |
| clic référence → détail | C | — | — | `/production/besoins/{id}` |
| Ouvrir le plan d'achat → | D, A | — | — | → `/plan-achat` |
| (nouveau) Effacer les filtres | C | — | — | — |
| (nouveau) Exporter en Excel | C | (route ajoutée, API-PRO § 1.24) | — | — |

---

### Besoin d'une matière — `/production/besoins/:matiereId` (fenêtre sur `/production?onglet=besoins`)

Gestion MP : fenêtre « {REF} — d'où vient le besoin » (`VoletBesoins.tsx:252-379`) → PRO : `Fenetre({taille:tresLarge})`, `Kpi`, `DataTable`, C.

**Ce qu'on voit**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « {REF} — d'où vient le besoin » ; note « rôle · nature · désignation · fournisseur » | identique | — |
| KPI Besoin du plan (« douze mois, perte comprise[ · ≈ N ml] ») ; Retenu par le plan d'achat (« corrigé par le réel : × 0,00 (+N %) » / « hors plan : … » / « pas encore de consommation… » ; attention si |coef − 1| > 0,15) ; Disponible (`kgEtMetres` ; « X kg en commande · couverture N j ») ; À commander (« rien » ; ton statut) | `Kpi` identiques + `Formule` | — |
| Tableau Qualité (figée), kg/m² (3 déc., infobulle « Fil de cette référence par m²… »), 12 mois, Total ; vide « Aucune qualité au plan n'utilise cette référence. » ; pied « Besoin du plan » et « Retenu (achats) » si écart > 0,5 kg | identiques ; infobulle « Cette matière par m² de la qualité, perte comprise » ; qualité → `/qualites/{id}?onglet=recette` | P2-1 |
| « Ouvrir le plan d'achat → » (D,A) | → `/plan-achat?onglet=references&q={REF}` | ciblé sur la matière |

**Gestes**

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Ouvrir le plan d'achat → | D, A | — | — | ciblé |
| × / Échap | C | — | — | → `/production?onglet=besoins` (filtres gardés) |
| (nouveau) « Fiche matière » | C | — | — | → `/stock/matieres/{id}` |

---

### Exports Excel de la partie

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `/api/export/pilotage` (D,A) | `ExportExcel` GET `export/pilotage` | — |
| `/api/export/mouvements` (C, sans prix pour L) | GET `export/mouvements` | — |
| `/api/export/sorties` (C) | GET `export/ordres` (statut, dates ; + `vue=consommation` pour l'onglet Ordres de fabrication) | renommage |
| — | GET `export/lots`, GET `export/production` (routes à ajouter) | P2-19 |

---

### Anomalies GMP corrigées — Partie 2

| # | Anomalie GMP | Traitement PRO |
|---|---|---|
| P2-1 | « Fil » en en-tête / textes (saisie, recherche, infobulle, Plan glissant) | « Référence », « Écart », « matière » partout (vocabulaire § 5) |
| P2-2 | « Journal » pour les mouvements de stock | « Mouvements de stock » ; vide « Aucun ordre de fabrication validé. » |
| P2-3 | Brouillon affiché « sans n° » | « Brouillon » (comme l'export) |
| P2-4 | En-tête « Sorti net » sur l'onglet Brouillons | « À sortir » sur cet onglet |
| P2-5 | Bascule maison, vue hors adresse | composant `Bascule`, `?vue=` |
| P2-6 | « Disponible » et « Stock » contradictoires (machine) | une définition serveur : Stock = magasins + sur les métiers ; Disponible = Stock − quarantaine ; texte unique « Sur les métiers » |
| P2-7 | « sous le seuil critique » faux ; « Statut classeur » jargon | « projeté ≤ 50 % du seuil d'alerte » ; « Statut de couverture » |
| P2-8 | Code mort / doublons (pied, `tonStock`, `EcartOrdre`, `.ouvrable`, `CLIQUABLE`) | pied `DataTable` ; table `Badge` unique ; un seul badge d'écart ; CSS/exports morts supprimés (ESLint) |
| P2-9 | Ligne cliquable avec classe `clic` sans style | ligne cliquable standard de `DataTable` |
| P2-10 | Saisie perdue sans question (retour « Fermer », plan hors `beforeunload`, « Tout annuler ») | garde `sale` sur « Fermer » ; garde de navigation du plan ; `Confirmer` sur « Tout annuler » |
| P2-11 | Boutons grisés sans raison (Valider la sortie, Garder en brouillon, Proposer, Enregistrer tout, Étiquettes (0)) | `Bouton({manque, blocages})` partout |
| P2-12 | Clic pour découvrir un refus (Enregistrer ligne hors bornes ; Tout valider compte les bloqués) | ligne grisée hors bornes ; N = validables sans blocage |
| P2-13 | À valider : « validé par les achats » faux ; « Ouvrir » vers un écran refusé à L | `valide_par` serveur ; `/operations/{id}` ouvert à L pour transferts et retours machine |
| P2-14 | « Brouillon supprimé. » invisible ; message de page jamais effacé | `Messages` (toasts) indépendants de la fenêtre |
| P2-15 | Prix sans « / kg » ; « Quantité » sans unité | « 0,000 DEV / kg » ; « Quantité (kg) » (`Colonne.unite`) |
| P2-16 | « Entré · sorti » mal formé | deux `Kpi` en kg |
| P2-17 | « ← Revenir au matière » ; « Ajustement » ≠ serveur | « à la matière » ; libellés de mouvement du serveur |
| P2-18 | « Où ce lot est-il allé ? » force l'onglet Lots | `/tracabilite?lot=` empilée sur l'écran courant |
| P2-19 | Besoins : filtres non liés, sans « Effacer » ; pas d'export (besoins, glissant, réalisé, lots, ordres) | `Filtres` liés + « Effacer » ; `ExportExcel` sur chaque liste (`export/ordres`, routes à ajouter `export/lots`, `export/production`) |
| P2-20 | Recherche serveur des mouvements sensible aux accents | `unaccent` + tous les mots, même règle que l'écran |
| P2-21 | Mois « oct. 26 » vs « oct. 2026 » | `moisLisible` unique « oct. 2026 » |
| P2-22 | « écran Qualités & recettes » | « Qualités et recettes » (titre de `routes.ts`) |
| P2-23 | Lot ajouté à la main : disponible d'aujourd'hui, pas à la date de l'ordre | GET `lots/disponibles?magasin_id=&date=` |
| P2-24 | « Reçu par REC-… » (« par » = auteur ailleurs) | « Réception REC-… du … » |
| P2-25 | Écart des Sorties en `attention` dans les deux sens | manque < −5 % en critique, comme le badge |

### Comptes de la partie 2

- Écrans : 3 (`/stock`, `/sorties`, `/production`) + 1 adresse de fiche autonome (`/tracabilite`).
- Onglets : 12 (Stock 5, Sorties 3, Production 4), tous repris.
- Sous-vues (bascules) : 17 reprises (Par matière 3 ; Suivi 2 ; Fiche d'ordre 2 ; Saisie recette/hors recette 2 ; Plan 2 ;
  Glissant 2 ; Réalisé 2 ; Besoins 2), toutes dans l'adresse `?vue=`.
- Fenêtres : 7 (Fiche matière `/stock/matieres/:id`, Fiche de lot `/lots/:id` avec Libérer, Suivi `/tracabilite`, Fiche
  d'ordre `/ordres/:id`, Saisie `/ordres/nouveau` et modification, Retour `/ordres/:id/retour`, Besoin
  `/production/besoins/:matiereId`) ; document : 1 (étiquettes) ; exports : 3 GMP + 2 nouveaux (lots, production) + 1
  étendu (ordres de fabrication).
- Gestes GMP : 72, tous repris (Stock 32, Sorties 27, Production 13) ; 1 supprimé (« Page du lot », adresse stable) ;
  nouveaux : clics KPI, Préparer la commande (fiche matière, vue Appro), Exporter (lots, ordres de fabrication, glissant,
  réalisé, besoins), Effacer les filtres (besoins), Fiche matière depuis un besoin.
- Anomalies : 25, toutes traitées.

### Routes demandées par la partie 2 (reportées dans API-PRO § 1.24)

- `POST /api/operations (valider: true)` (déjà listée en Partie 1) : retour des machines et libération de quarantaine créés et
  validés dans une transaction.
- `GET /api/export/lots` (D,A,L ; filtres de l'onglet Lots).
- `GET /api/export/production?onglet=glissant|realise|besoins` (C ; sans prix).
- Paramètres à accepter (pas de nouvelle route) : `GET lots/disponibles?magasin_id=&date=` (disponible à la date de
  l'ordre) ; `GET export/ordres?vue=consommation` ; `GET mouvements` renvoie les types et magasins présents pour les
  filtres liés ; `GET brouillons` renvoie `valide_par` ; `POST ordres/proposition` renvoie `blocages` (inventaire, date
  du dernier ordre validé).

---

## Partie 3 — L'atelier au téléphone, les métiers à tisser, les étiquettes QR

Source : `docs/heritage/ECRANS.md` Partie 3 (§ 0 à § 5, anomalies 1 à 29). Routes d'API sans préfixe = `/api/…`.
Rôles : D direction · A achats · L alimentation · C = D, A, L. « (an. n) » renvoie à l'anomalie n de la partie.

Points tranchés appliqués partout dans cette partie :
- **(a) Sur les métiers.** Le fil monté est du stock « sur les métiers » : il compte dans le stock global, sa valeur,
  le disponible et le projeté. Monter n'écrit **aucun mouvement** (le fil a déjà été sorti par un ordre). Texte unique,
  téléphone et bureau, dans toute confirmation de montage :
  « Monter n'écrit aucun mouvement : ce fil est déjà sorti par un ordre. Le stock sur les métiers passe de {avant} à
  {après} kg ({±x} kg) ; il compte dans le stock global, sa valeur, le disponible et le projeté. » (écart < 0,05 kg :
  « Le stock sur les métiers ne change pas. » ; métier arrêté : « Métier arrêté : rien n'est compté sur lui. »).
  Alerte au-delà de ce qui est parti en 30 jours (règle `1,1 × sorti 30 j + 1 kg`) : « {réf} : {x} kg sur les métiers
  pour {y} kg partis aux machines en 30 jours : vérifier qu'il est bien sorti par un ordre avant de le monter. »
  Chaque montage s'écrit dans la table d'historique des montages (lue par `GET metiers/{id}/montages`, onglet
  « Historique »). « Ces kilos sont déjà sortis et consommés » n'est repris nulle part. Verrou par champ `version`
  (plus d'empreinte).
- **(b)** L'inventaire ne suspend que **son périmètre** (matières comptées, dans son magasin ou dans tous s'il est global).
- **(d)** Transferts ouverts à L (téléphone : Déplacer ; bureau : `/operations?onglet=transfert`) ; libération de
  quarantaine D, A seulement ; L peut mettre en quarantaine (motif imposé « Mise en quarantaine », observations obligatoires).
- **(e)** `?bon=` devient `?ordre=` et rouvre vraiment le brouillon ; coupure réseau = **« Pas de réseau »** (jamais liste
  vide ni « introuvable ») ; « Lots à prendre » replié « tout est conforme », Valider collant.

### Cadre commun de l'atelier — `/atelier/*`

Gestion MP : `pages/atelier/Atelier.tsx`, `commun.tsx` (`Ecran`, briques), `public/sw.js`, garde `peutAvec(['alimentation'])`
→ PRO : branche `/atelier/*` hors `Coque` (registre `routes.ts`), `EcranAtelier`, `BarreBas`, `BandeauBlocages`, `Tuile`,
`Compteur`, `SegmentsTactiles`, `ScanQR`, `ResumeValidation` ; rôles L (D peut ouvrir) ; A et T → accueil + `EcranReserve`.

Ce qu'on voit

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde `/atelier/*` : L + D ; achats renvoyés **sans message** | garde du registre (L, D) ; autre rôle → son accueil + `EcranReserve` « L'écran demandé (…) est réservé à un autre rôle : vous êtes revenu à votre accueil. » | message dit (an. 2) |
| Menu bureau « Écran atelier (téléphone) » (L, D) | entrée `BarreLaterale` identique → `/atelier` | — |
| Arrivée : téléphone ≤ 700 px → L `/atelier` ; poste → `/accueil` ; `/` → `/sorties` pour L au poste | même test `matchMedia('(max-width: 700px)')` ; `/` mène toujours à l'arrivée du rôle (`/accueil` pour L au poste) | une seule arrivée par rôle |
| QR `/lot/:id` : téléphone → `/atelier/lot/:id` **quel que soit le rôle** ; poste → page du lot ; sans session : connexion puis adresse rejouée | `/lot/:id` : téléphone **et** rôle L → `/atelier/lots/:id` ; tout autre cas → `/lots/:id` ; sans session : `/connexion` puis adresse rejouée | an. 2 |
| Routes internes `envoyer`, `bons`, `bons/:id`, `retour`, `chercher`, `lot/:id`, `deplacer`, `montage`, `signaler`, `*` → accueil | `/atelier/envoyer`, `/atelier/ordres`, `/atelier/ordres/:id`, `/atelier/retour`, `/atelier/chercher`, `/atelier/lots/:id`, `/atelier/deplacer`, `/atelier/montage`, `/atelier/signaler` ; `*` → `/atelier` | `bons` → `ordres`, `lot` → `lots` |
| En-tête collant fond accent, « ‹ » (`aria-label="Retour"`, page précédente ou adresse), h1 18 px, zone `droite` jamais utilisée | `EcranAtelier({titre, retour})`, « ‹ » 44 × 44 ; zone droite supprimée | an. 16 |
| Corps colonne, écart 12, padding 14, largeur max 720 centrée | idem (jetons CSS du système) | — |
| Barre du bas : « ⌂ Accueil » (actif à l'exact), « ⇢ Envoyer », « ⇠ Retour », « ⌕ Lots » ; icône 22 / libellé 12 gras ; safe-area ; corps réserve 84 px | `BarreBas` : mêmes 4 cases et libellés, icônes SVG du système | saisie gardée en quittant (an. 17) |
| Tailles : bouton ≥ 46 px et ≥ 44 × 44, police 15 ; `.large` ; champ 46 px police 16 ; Compteur 52·1fr·52 ; Segments ≥ 44 ; lien-geste ≥ 44 ; tuile 2 col. ; bouton d'étage ≥ 56 ; confirmation pleine largeur ; carte `.fiche` alerte/ok/clic ; `.grand-nombre` 26 px | `Bouton` taille atelier, `Tuile`, `Compteur`, `SegmentsTactiles`, `Confirmer` pleine largeur (question sur sa ligne), `Carte` tons alerte/ok, `Kpi` grand ; notes ≥ 14 px | cibles ≥ 44 px vérifiées par essai automatique |
| `Compteur` : −/+ ramènent au multiple du pas ; `inputMode=decimal`, virgule/point, espaces ignorés, vide = 0, tout sélectionné au focus ; « − » pas sous `min`, frappe négative acceptée | `Compteur({min, max, pas})` mêmes gestes ; bornes appliquées aussi à la frappe | an. 12 |
| `pasPour` : bobine/palette 1 ; kg 0,1 (< 10), 1 (< 100), 10 | idem | — |
| Unités kg / Bobine / Palette ; libellés « kg », « bobines (X,XX kg) », « palettes (N bob.) » ; contenance (pesé au lot, sinon catalogue) ; `convertir` (bobine entière, palette centième, kg dixième) ; `toutRendre` vers le bas | `Quantite` (mode tactile) : mêmes unités, dit l'arrondi ; toute conversion bornée (retour, déplacement) arrondit **vers le bas** | an. 24 |
| `quantite` « 12,5 kg » (2 déc. sous 10 kg), « 14,30 kg ≈ 1 021 ml » ; `bobines` « ≈ N bobines » | `KgEtMetres` ; « ≈ N bobines » | — |
| `Bandeau` rouge ; `Blocages` « Sera refusé à la validation : » + puces | `BandeauBlocages` (blocages serveur, en tête) ; `Blocages` | — |
| `STATUTS_BON` brouillon/valide/annule | `Badge` (table unique) « Brouillon » attention, « Validé » ok, « Annulé » neutre | — |
| `aujourdhuiLocal` à l'heure du serveur | heure serveur (`X-Heure-Serveur`) | — |
| `magasinParDefaut` : actif, non quarantaine, le plus garni | idem | — |
| `useSuspension(magasin)` : bandeau dès qu'un inventaire ouvert porte sur le magasin ou sur tous | bandeau seulement si un inventaire ouvert **compte une matière concernée** dans ce magasin (ou tous) : « L'inventaire {n°} ({magasin}, du {jj/mm/aaaa}) compte « {réf} » : ses mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre. » ; calculé au serveur (`blocages`) | (b) |
| `useDernierOrdre` : date du plus récent ordre validé **ou annulé** | lu au serveur dans `blocages` / proposition | — |
| Client : préfixe `/api`, cookie, `X-Gestion-MP: 1` sur les écritures (sinon 403 « Requête refusée… ») | idem (client unique) | — |
| Injoignable : « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). » sur les gestes ; **lectures muettes** (liste vide, compteurs à 0, « introuvable ») | `Erreur` atelier **« Pas de réseau »** + « vérifiez le Wi-Fi ou la 4G/5G » + bouton « Réessayer », sur **toute** lecture et tout geste | (e), an. 3 |
| 401 « Connectez-vous pour continuer. » / « Ce compte n'est plus actif. » → connexion | idem, adresse rejouée | — |
| 422 Pydantic « champ : message ; … » | idem | — |
| Relecture au focus, fraîcheur 15 s, 1 retry testé sur le **texte** `/40[134]/` | TanStack Query : retry décidé sur le **statut** (aucun retry sur 401, 403, 404, 409, 422) | an. 4 |
| Service worker sans cache : l'appli installée ne s'ouvre pas hors réseau ; manifeste « Gestion MP — matières premières » / « Gestion MP », standalone, `#17497f` | SW met en cache **l'enveloppe** (HTML, JS, CSS, icônes), jamais les données : l'appli s'ouvre et dit « Pas de réseau » ; même manifeste | an. 4 |
| Seule saisie gardée : sortie en cours (`gestion-mp:sortie-en-cours`) | chaque saisie de l'atelier gardée en `sessionStorage` par écran (Envoyer, Retour, Déplacer, Monter, Signaler) et reprise | an. 17 |
| Aucun prix pour L : `masquer_prix` sur `lots/{id}`, `articles` (garde `devise`, `unite_prix`), `qualites` (garde `devise`), `metiers`, `inventaires`, `operations/{id}` | `sans_prix` générique sur toute réponse lue par L : prix, cours, coûts, valeurs **et** `devise`, `unite_prix` retirés ; essai DOM « aucun montant » | an. 27 |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Case de la barre du bas (4) | L, D | — | aucune | la saisie en cours est gardée et reprise |
| « ‹ » (en-tête) | L, D | — | aucune | idem |
| (nouveau) « Réessayer » | L, D | relit la requête | — | sur « Pas de réseau » |

### Accueil de l'atelier — `/atelier`

Gestion MP : `Atelier.tsx` (`Tableau`), `/atelier` → PRO : `/atelier`, `EcranAtelier` + 7 `Tuile` + `BarreBas` ; L, D.

Ce qu'on voit

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /bons` ; `GET /signalements?tous=true` relu 60 s | `GET ordres` (du jour) ; `GET signalements` relu 60 s, « mes » = filtre par **identifiant** du compte | an. 25 |
| Titre « Atelier », pas de « ‹ » | idem | — |
| « Bonjour {nom}. Aujourd'hui, pour tout l'atelier : {N} ordre(s) validé(s), {X kg} envoyés aux machines. » — X = Σ `total` **brut** ; 0 pendant le chargement | « … {N} ordre(s) validé(s), {X kg} sortis net. » — X = Σ sorti net (brut − retours) des ordres validés du jour ; `Chargement` (pas 0) ; « Pas de réseau » sinon | an. 22, an. 3 |
| Tuile principale « Envoyer aux machines » — « Qualité et m² à fabriquer : les fils et les lots à prendre sont proposés. » | `Tuile` principale, même texte → `/atelier/envoyer` | — |
| « Retour des machines » — « Ce qui revient d'un ordre, lot par lot. » | `Tuile` → `/atelier/retour` | — |
| « Trouver un lot » — « Chercher ou scanner une étiquette. » | `Tuile` → `/atelier/chercher` | — |
| « Déplacer » — « D'un magasin à un autre. » | `Tuile` → `/atelier/deplacer` | — |
| « Monter les fils » — « Ce qui est monté sur chaque métier, étage par étage. » | `Tuile` → `/atelier/montage` (écran titré pareil) | an. 20 |
| « Signaler un besoin » — « {n} en attente · {r} réponse(s) des achats » ou « Un fil qui manque, une palette qui finit. » | `Tuile` → `/atelier/signaler`, compteurs sur **mes** signalements (identifiant) | an. 25 |
| « Ordres » — « {n} brouillon(s) à finir » (tout l'atelier) ou « Les sorties récentes » | `Tuile` → `/atelier/ordres` | — |
| Note « Astuce : … « Ajouter à l'écran d'accueil »… L'appareil photo lit les étiquettes QR… » | `Note` identique | — |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Toucher une tuile (×7) | L, D | — | — | — |
| « Se déconnecter » (bas, loin des tuiles) | L, D | `POST deconnexion` | `Confirmer` pleine largeur « Se déconnecter ({nom}) ? » · « Non » · « Oui, se déconnecter » | cache vidé, `/connexion` |
| Barre du bas (×4) | L, D | — | — | voir cadre |

### Envoyer aux machines — étape 1 « la demande » — `/atelier/envoyer` (`?ordre=ID`)

Gestion MP : `Envoyer.tsx` (aiguillage, `SaisieTelephone`, `Demande`), `/atelier/envoyer?bon=ID` → PRO : `/atelier/envoyer?ordre=ID`,
`EcranAtelier`, `DateChamp`, `SegmentsTactiles`, `Selecteur` (tactile), `Compteur`, `Zone`, `BandeauBlocages`,
`Bouton({manque, blocages})` ; L, D (lecture de la proposition : C).

Ce qu'on voit

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Adresse `?bon=ID` ; chaque visite recrée l'écran (clé bon + `location.key`) ; sortie en cours reprise | `?ordre=ID` ; même reprise | (e) |
| Aiguillage : « Un instant — chargement : l'ordre… » ; non brouillon → écran « Ordre validé » ; **échec de lecture → ordre vierge (ou sortie gardée)** | `Chargement` ; brouillon → étape 2 rouverte **sur ce brouillon** ; non brouillon → `/atelier/ordres/:id` ; 404 → « Ordre introuvable » ; coupure → « Pas de réseau » + « Réessayer », jamais d'ordre vierge | (e), an. 3, an. 10 |
| Données : magasins, métiers, qualités, inventaires, `GET /bons`, `GET /bons/{id}` | `GET magasins`, `GET metiers`, `GET qualites`, `GET inventaires` (ouverts), `GET ordres` (dernier non brouillon), `GET ordres/{id}` | — |
| Titre « Envoyer aux machines » / « Modifier l'ordre (brouillon) » ; « ‹ » seulement sans lot choisi | mêmes titres ; « ‹ » toujours là (la saisie est gardée) | an. 17 |
| Bandeau 1 : suspension d'inventaire du magasin | `BandeauBlocages`, par périmètre (seulement si une matière en jeu est comptée) | (b) |
| Bandeau 2 : « Un ordre du {date} est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être daté avant. Pour un oubli, le dater du {date} et écrire la vraie date dans le commentaire. » | même texte, « … dans les observations. » | vocabulaire |
| Note « La sortie commencée tout à l'heure est reprise telle quelle ; « Abandonner cette sortie », en bas de l'écran des lots, repart à vide. » | identique | — |
| « Date de la sortie » (max aujourd'hui ; change → demande changée) | `DateChamp` (max aujourd'hui serveur, min après clôture) | min posé |
| « Magasin d'où sort la matière » : `Segments` si ≤ 3 magasins courants, sinon liste ; masqué s'il n'y en a qu'un ; aide « changer de magasin efface les lots choisis » | `SegmentsTactiles` / `Selecteur` ; même aide ; changement avec lots → `Confirmer` | saisie protégée |
| « Métier (facultatif) » : actifs (+ celui du brouillon), tri nom puis code, « CODE · Nom » | `Selecteur`, libellé « CODE · Nom » (repris partout) | an. 20 |
| Bascule « Selon les recettes » / « Ordre hors recette » ; note hors recette « Échantillons, série spéciale : … à l'étape suivante. » | `SegmentsTactiles` ; même note | — |
| Carte « Qualité à fabriquer » / « Qualité n° i » : `ChoixRecherche` (multi-mots, sans accents, **60 premiers**, « Rien ne correspond. », « Taper le code ou le nom… », Entrée si 1 résultat), qualités actives non déjà prises, « CODE — Nom » | `Selecteur` tactile, même recherche ; liste défilante complète | coupure muette retirée (an. 18) |
| « Mètres carrés » : `Compteur` pas 50, > 0 | `Compteur` pas 50, min 0 | — |
| « Retirer cette qualité » (≥ 2) ; « + Une autre qualité sur le même ordre » | idem | — |
| « Commentaire (facultatif) » 300, « Équipe, consigne, incident… » | « Observations (facultatif) », 300 | vocabulaire (an. 8) |
| « Revenir aux lots » (lots + demande inchangée) | idem | — |
| Bouton de calcul : « Calcul… » / « Choisir les fils et les lots » / « Recalculer les fils et les lots » / « Voir les fils et les lots à prendre » ; raison sous le bouton : « Choisir le magasin d'où sort la matière » · « Choisir la date » · « Ajouter une qualité à fabriquer » · « Choisir la qualité à fabriquer » · « Saisir les mètres carrés à fabriquer » | `Bouton({manque})`, mêmes libellés et raisons écrites sous le bouton | — |
| Note « Recalculer remplace les lots proposés ; les fils ajoutés à la main sont gardés. » | idem | — |
| Demande complète = magasin + date + (hors recette ou ≥ 1 qualité avec qualité et m² > 0) | idem | — |
| Erreur serveur en bandeau (« La qualité {code} est arrêtée : … », « Qualité inconnue. », réseau) | `Erreur` ; réseau = « Pas de réseau » | (e) |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « ‹ » | L, D | — | — | toujours affiché (saisie gardée) |
| Changer de magasin (lots déjà choisis) | L, D | — | `Confirmer` « Changer de magasin efface les {n} lots choisis ? » · « Non » · « Oui, changer » | effacement annoncé |
| Bascule recette / hors recette | L, D | — | — | marque « demande changée » |
| « Retirer cette qualité » | L, D | — | ≥ 2 qualités | — |
| « + Une autre qualité sur le même ordre » | L, D | — | — | — |
| « Revenir aux lots » | L, D | — | lots + demande inchangée | — |
| « Voir les fils et les lots à prendre » / « Recalculer les fils et les lots » / « Choisir les fils et les lots » | L, D | selon recettes `POST ordres/proposition` `{magasin_id, date, fabrications:[{qualite_id, m2}]}` ; hors recette : aucun appel | grisé + raison sous le bouton | — |

### Envoyer aux machines — étape 2 « Lots à prendre » — `/atelier/envoyer` (étape lots)

Gestion MP : `Envoyer.tsx` (`Lots`, `FilCarte`), `sortie.ts` → PRO : même route, `EcranAtelier`, `ResumeValidation` (collant),
`Carte` repliable, `SegmentsTactiles`, `Compteur`, `SelecteurLot` tactile, `Badge` d'écart, `BandeauBlocages`, `Confirmer` ; L, D.

Ce qu'on voit

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Lots à prendre », sans « ‹ » | idem | — |
| Données `GET /soldes?magasin_id=` (disponible **du jour**) ; brouillon rouvert : `POST /bons/proposition` à la date de l'ordre | `GET lots/disponibles?magasin_id=&date={date de l'ordre}` (disponible **à la date de l'ordre**) ; brouillon rouvert : `POST ordres/proposition` à la date | an. 23 |
| Bandeaux d'empêchement (comme étape 1) | `BandeauBlocages` | (b) |
| Carte récapitulative « {CODE} {m²} m² · … » / « Ordre hors recette » ; note « Le {jj/mm/aaaa (aujourd'hui/hier)} · {magasin} · {CODE · Nom} · {commentaire} » ; bouton « Modifier la demande » | `ResumeValidation` en tête, même contenu (« observations ») | — |
| Recettes incomplètes (2 textes « Recette incomplète — {CODE} : le rôle … ») | `Note` alerte par recette, mêmes textes, titre « Recettes incomplètes » | vocabulaire |
| Note « Les quantités proposées suivent la recette, perte matière comprise… Corrigez au réel avant de valider. » | idem | — |
| Une carte par fil, ouverte, toutes affichées (5 800 px pour 16 fils) | **Vue repliée** : les fils conformes (écart « conforme », sans manque, sans dépassement ni contenance manquante) regroupés dans une carte « {n} fil(s) conforme(s) — tout est conforme » (toucher déplie) ; restent ouverts les fils en écart, en manque, en dépassement, sans poids de bobine et hors recette ; tout conforme → une seule carte « Tout est conforme : {n} fils, {total} » | (e), REGLES 6.1 |
| Titre de carte = référence ; carte rouge si manque > 0,05 kg | idem | — |
| Fil de recette : « {rôle} · prévu {q} » (+ « {CODE} : {q} · … » si plusieurs qualités, aussi en infobulle) ; à droite « pris {q} » + `EcartFil` | idem ; détail par qualité en texte (pas d'infobulle au doigt) | — |
| Fil hors recette : « hors recette · pris {q} » | idem | — |
| « Il manque {q} dans ce magasin (la quarantaine ne compte pas). » | idem | — |
| Ligne de lot : « Lot {n°} », « dispo {q} ≈ N bobines » (vide tant qu'un brouillon rouvert n'a pas relu) | idem ; dispo toujours connu (relu à la date) | an. 23 |
| `Segments` d'unité ; « arrondi : {après} au lieu de {avant} » (> 0,01 kg) | `SegmentsTactiles`, même message | — |
| `Compteur` (pas `pasPour`) ; « = {kg} » ou « ≈ N ml, à titre indicatif » | idem | — |
| « Retirer ce lot » (aligné à droite) | idem | — |
| Alertes « Plus que ce que porte le lot. » ; « Le poids de bobine n'est pas connu : saisir en kg. » | idem | — |
| « + Prendre aussi un autre lot… » : options « {n° lot} — {q} » | `SelecteurLot` tactile | — |
| Carte « Ajouter un fil » / « Ajouter un fil hors recette » : lots du magasin dispo > 0 non pris, « {réf} · lot {n°} », détail dispo, « Référence ou numéro de lot… » | `SelecteurLot` tactile, dispo à la date de l'ordre | an. 23 |
| Totaux : « Prévu par la recette », « Total à sortir » (grand), « Écart » | `ResumeValidation` **collant en bas** (au-dessus de `BarreBas`) avec Total à sortir, Écart, et le bouton Valider | (e) |
| `EcartFil` : « — » sans prévu ; « conforme » (|écart| < 0,05 kg ou < 0,5 %) ; « ±X kg (±Y %) » gris ≤ 5 %, attention au-dessus en plus, critique au-dessus en moins | `Badge` d'écart, mêmes seuils | — |
| Corps envoyé `{date, magasin_id, metier_id, commentaire, fabrications, lignes:[{article_id, lot_id, quantite, unite}]}` (prises > 0) ; relecture d'une liste de clés | `{date, magasin_id, metier_id, commentaire, fabrications, lignes:[{matiere_id, lot_id, quantite, unite}]}` ; invalidation globale | `article_id` → `matiere_id` |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Modifier la demande » | L, D | — | — | rien perdu |
| Segment d'unité | L, D | — | — | arrondi dit |
| − / + / saisie | L, D | — | — | bornes à la frappe |
| « Retirer ce lot » | L, D | — | — | — |
| « + Prendre aussi un autre lot… » | L, D | — | autres lots du fil disponibles | — |
| Ajouter un fil (choix) | L, D | — | — | — |
| (nouveau) Déplier / replier « tout est conforme » | L, D | — | — | (e) |
| « Valider la sortie » (« Enregistrement… ») | L, D | `POST ordres` ou `PUT ordres/{id}`, puis `POST ordres/{id}/valider` | grisé, raison **sous le bouton** : « Aucune quantité à sortir » · « Validation impossible pour l'instant (voir le bandeau en tête) » · « {n} lot(s) : plus que ce qu'ils portent » · « Un poids de bobine manque : saisir ces lots en kg » ; `Confirmer` pleine largeur « Sortir {total} le {date lisible · magasin · métier} ? Le stock est débité tout de suite. » · « Non » · « Oui, valider la sortie » | bouton collant ; raison « aucune quantité » enfin affichée (an. 9) ; succès → « Sortie enregistrée » ; refus de validation seule : « {message} — l'ordre est gardé en brouillon, modifiable. » |
| « Garder en brouillon (sans sortir le stock) » | L, D | `POST ordres` ou `PUT ordres/{id}` | grisé, raison **sous le bouton** (« Aucune quantité à sortir », « Un poids de bobine manque… ») | an. 9 |
| « Abandonner cette sortie » (rouge, nouvel ordre) | L, D | — | `Confirmer` « Abandonner cette sortie ? Rien n'est enregistré. » · « Non » · « Oui, abandonner » | efface la saisie gardée et revient à `/atelier` **sans recharger l'appli** (an. 26) |

Refus serveur repris tels quels, « bon » remplacé par « ordre » (an. 5) : « Magasin inconnu. » ; « La matière en quarantaine ne part
pas aux machines : la libérer d'abord (transfert « Libération de quarantaine », décidé par les achats ou la direction). » ;
« Métier inconnu. » ; dates (« Date trop ancienne… », « Date dans le futur… », « La période jusqu'au … est close… ») ;
« Une qualité ne figure qu'une fois sur un ordre : additionner ses m². » ; qualité arrêtée / inconnue ; « Lot inconnu, ou d'une
autre matière. » ; unités (3 textes) ; « lignes : … » ; « Un ordre validé ne se modifie plus : l'annuler, puis en faire un
autre. » (409) ; à la validation : « Cet ordre est déjà validé. » ; « Qualité arrêtée ({codes}) : … » ; « À la date de l'ordre,
lot {n°} de {réf} : {état} … » ; « Un ordre daté du {date} existe déjà : les numéros suivent les dates, un ordre ne se valide
pas à une date antérieure. » ; suspension par périmètre « L'inventaire {n°} compte « {réf} » dans « {mag} » : ses mouvements y
sont suspendus jusqu'à sa validation. » ; stock insuffisant ; antidate (`couvert_a_sa_date`).

### Sortie enregistrée — `/atelier/envoyer` (fin)

Gestion MP : `Envoyer.tsx:99-130` → PRO : même route (état final), `EcranAtelier`, `Carte` ok ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Sortie enregistrée », « ‹ » → `/atelier` | idem | — |
| Carte verte « Ordre {OF-AAAA-NNNN} validé » / « Ordre gardé en brouillon » | idem | — |
| « Matière sortie » / « Matière à sortir » {total} ; « Magasin » ; « Métier » (nom **ou** code selon le serveur) | idem ; « Métier » = « CODE · Nom » | an. 20 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouvel ordre » | L, D | — | — | → `/atelier/envoyer` |
| « Voir l'ordre » | L, D | — | — | → `/atelier/ordres/{id}` |
| « Revenir à l'accueil » | L, D | — | — | → `/atelier` |

### Ordre validé ou annulé ouvert pour modification — `/atelier/envoyer?ordre=ID` (non brouillon)

Gestion MP : `Envoyer.tsx:40-45`, titre « Ordre validé » pour tout non brouillon → PRO : redirection vers `/atelier/ordres/:id`
avec `Note` ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Ordre validé » ; « Cet ordre est déjà validé : il ne se modifie plus (l'annuler, puis en refaire un). » — **aussi pour un annulé** | validé : même note ; annulé : « Cet ordre est annulé : il ne se modifie plus (en refaire un). » ; titre selon le statut | an. 10 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « ‹ » → `/atelier/bons` | L, D | — | — | → `/atelier/ordres` |

### Ordres — `/atelier/ordres`

Gestion MP : `Bons.tsx:11-43`, `/atelier/bons` → PRO : `/atelier/ordres`, `EcranAtelier`, `Carte` cliquable, `Badge`, `ChargerPlus` ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /bons` ; « Un instant — chargement : les ordres… » | `GET ordres` (liste complète, non paginée au serveur : API-PRO 135 ; plus récent d'abord) ; `Chargement` ; « Pas de réseau » | an. 3 |
| Brouillons en tête, puis date décroissante ; **60 premiers sans le dire** | même tri ; 50 puis `ChargerPlus` « {n} sur {total} — charger les suivants » | an. 18 |
| Carte rouge si blocages ; « **{n° OF}** » ou « **Ordre du {date}** » (brouillon) + statut | « **Brouillon** » + date en note pour un brouillon | an. 6 |
| Note « {date} · {CODE m² m², …} ou « hors recette » · {métier} » ; quantité (net si validé, total sinon ; 1 déc. < 100 kg) + « sorti net » / « à sortir » / « annulé » | idem, métier « CODE · Nom » | an. 20 |
| « ⚠ sera refusé : {première raison} » ; « Retours : {n°, …} » | « sera refusé : … » (sans symbole) ; retours | — |
| Vide « Aucune sortie pour l'instant. » | `Vide` identique | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Toucher une carte | L, D | — | — | → `/atelier/ordres/{id}` |
| (nouveau) « Charger les suivants » | L, D | — (la liste est déjà lue en entier : 50 cartes de plus montrées) | — | an. 18 |

### Détail d'un ordre — `/atelier/ordres/:id`

Gestion MP : `Bons.tsx:45-201`, `/atelier/bons/:id` → PRO : `/atelier/ordres/:id`, `EcranAtelier`, `Definitions`, `Blocages`,
`Bouton({blocages})`, `Confirmer` pleine largeur ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « {n° OF} » ou « Ordre du {date} » ; « ‹ » → `/atelier/bons` | « {n° OF} » ou « Brouillon » ; « ‹ » → `/atelier/ordres` | an. 6 |
| `GET /bons/{id}` ; introuvable : « Ordre introuvable. » **sans en-tête** ; erreur réseau confondue | `GET ordres/{id}` ; 404 : « Ordre introuvable » avec en-tête et « ‹ » ; coupure : « Pas de réseau » | an. 3 |
| Identité : « Statut », « Date », « Magasin », « Métier », une ligne par qualité « {CODE} — {Nom} » / « {m²} m² » ou « Fabrication » / « hors recette », « Commentaire », « Par » (créé le … ; validé par … le …) | `Definitions` mêmes lignes ; « Observations » ; métier « CODE · Nom » | an. 8, an. 20 |
| « Matière à sortir » / « Matière sortie » : « {réf} / lot {n°} » → q ; « **Total** » ; « dont revenu des machines − {kg} » | idem ; n° de lot touchable → `/atelier/lots/:id` | raccourci |
| Note « Retours faits sur cet ordre : {RET-…, « retour repris de l'ERP Fil du … »} » | idem | — |
| `Blocages` puis messages | idem | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Valider la sortie » (brouillon) | L, D | `POST ordres/{id}/valider` | grisé si blocages (raison sous le bouton) ; `Confirmer` « Sortir {total} le {date · magasin · métier} ? Le stock est débité tout de suite. » · « Non » · « Oui, valider » | question alignée sur l'étape 2 ; succès « Sortie validée. » |
| « Modifier le brouillon » | L, D | — | — | → `/atelier/envoyer?ordre={id}` (rouvre vraiment ce brouillon) |
| « Supprimer le brouillon » (rouge) | L, D | `DELETE ordres/{id}` | `Confirmer` « Supprimer ce brouillon ? Rien n'est sorti du stock. » · « Non » · « Oui, supprimer » | refus « Un ordre validé ne se supprime pas : l'annuler. », « Ordre introuvable. » (an. 5) |
| « Faire un retour sur cet ordre » (validé) | L, D | — | — | → `/atelier/retour?ordre={id}` |
| « Annuler l'ordre (erreur de saisie) » (rouge, validé) | L, D | `POST ordres/{id}/annuler` | `Confirmer` avec retours « Annuler tout l'ordre et ses retours ({n°…}) ? La matière sortie revient en stock, une seule fois, à la date de l'ordre. » ; sans « Annuler tout l'ordre ? Toute sa matière revient en stock, à la date de l'ordre. » · « Non » · « Oui, annuler (contre-passation) » | succès « Ordre annulé : la matière est revenue en stock. » ; refus « Seul un ordre validé s'annule ; un brouillon se supprime. », « Ce document a déjà été annulé. », période close, suspension par périmètre |
| Ordre annulé : aucun geste | — | — | — | — |

Annuler un ordre contre-passe aussi ses retours (RET passés « annulée ») et les retours repris de l'ERP Fil, datés comme les originaux (inchangé).

### Retour des machines — choix de l'ordre — `/atelier/retour`

Gestion MP : `Retour.tsx:61-115` → PRO : `/atelier/retour`, `EcranAtelier`, `Recherche` (garde le focus), `Carte` cliquable,
`ChargerPlus` ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /bons` ; chargement « les ordres » | `GET ordres?statut=valide&q=` (recherche serveur sans accents) | an. 3, an. 18 |
| Note « De quel ordre revient la matière ? » | idem | — |
| Recherche (si > 10 validés) « N° d'ordre, qualité, métier… » sur n°, date lisible, métier, codes qualité | idem | — |
| Liste des **validés** : 10 derniers sans recherche, 30 premiers avec | idem + `ChargerPlus` | an. 18 |
| Carte « **{n° OF}** » ; à droite sorti net + « sorti net » ; note « {date} · {CODE m²…} / « hors recette » · {métier} » | idem, métier « CODE · Nom » | an. 20 |
| Pied « {n} autre(s) : préciser la recherche » / « les 10 derniers sur {total} : chercher un ordre plus ancien » | idem | — |
| Vides « Aucun ordre ne correspond. » / « Aucun ordre validé. » | `Vide` identiques | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Saisie de la recherche | L, D | `GET ordres?q=` | — | serveur, sans accents |
| Toucher une carte | L, D | — | — | → `/atelier/retour?ordre={id}` |

### Retour sur un ordre — `/atelier/retour?ordre=ID`

Gestion MP : `Retour.tsx:117-287`, `?bon=ID` → PRO : `/atelier/retour?ordre=ID`, `EcranAtelier`, `Carte` par lot,
`SegmentsTactiles`, `Compteur`, `Selecteur`, `DateChamp`, `Zone`, `BandeauBlocages`, `Bouton({manque, blocages})`, `Confirmer` ;
D, L (type `retour_machine` : D, L).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Retour — {n° OF} » (« Retour — ordre » avant chargement) ; « ‹ » → `/atelier/retour` | idem | — |
| Droit serveur `retour_machine` = alimentation (« « Retour des machines » est réservé à : responsable alimentation machines. ») | D, L | contrat |
| Données `GET /bons/{id}`, `GET /bons/{id}/lots-sortis`, `GET /operations/motifs`, `GET /magasins`, `GET /inventaires` | `GET ordres/{id}`, `GET ordres/{id}/lots-sortis`, `GET motifs`, `GET magasins`, `GET inventaires` | — |
| Vide « Tout ce qui est parti sur cet ordre est déjà revenu. » | idem | — |
| Carte par lot parti (rouge si dépassement) : référence ; « lot {n°} » ; « parti (net) : {q} » ; unité ; Compteur ; « = {kg} » ; « Tout ce qui est parti » ; « On ne rend pas plus que ce qui est parti. » | « Sorti net : {q} » ; conversion d'unité arrondie **vers le bas** | an. 21, an. 24 |
| « Ranger dans le magasin » (si > 1 courant ; défaut magasin de l'ordre) | `Selecteur` / `SegmentsTactiles` | — |
| « Pourquoi revient-elle ? » : « R1 · Reliquat de fin d'ordre », « R2 · Changement de série / arrêt machine », « R4 · Erreur de prélèvement » (défaut le premier) | `Selecteur` des motifs `retour_machine` | — |
| « Date du retour » (min date de l'ordre, max aujourd'hui) | `DateChamp` (+ min après clôture) | — |
| « Commentaire (facultatif) » 300, « Bobines entamées, arrêt du métier… » | « Observations (facultatif) » | an. 8 |
| Bandeau de suspension (magasin de rangement) | `BandeauBlocages` par périmètre | (b) |
| Saisie perdue en quittant | gardée (`sessionStorage`) | an. 17 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Unité / − / + / saisie | D, L | — | — | arrondi vers le bas |
| « Tout ce qui est parti » | D, L | — | — | — |
| « Remettre {X kg} en stock » (« Enregistrement… ») | D, L | `POST operations` `{type:'retour_machine', ordre_id, date, motif, commentaire, lignes:[{matiere_id, lot_id, magasin_id, quantite, unite}], valider:true}` (création et validation dans une transaction) | grisé ; raison sous le bouton : « {n} lot(s) dépassent ce qui est parti : {réf} (lot {n°}), … » · « Saisir ce qui revient, lot par lot. » · inventaire en cours (bandeau) · motif / magasin / date manquants ; `Confirmer` « Remettre {X kg} en stock ({magasin}) ? » · « Non » · « Oui, enregistrer le retour » | plus de création puis suppression en cas d'échec ; succès « Retour enregistré — {RET-AAAA-NNNN} : {X kg} remis en stock. » + « Revenir à l'accueil » ; quantités et observations remises à zéro |
| « Effacer les quantités » | D, L | — | `Confirmer` « Effacer les quantités saisies ? » | saisie protégée |

Refus serveur repris : « Choisir le motif : il dit pourquoi le stock bouge. » ; « Un retour des machines se rattache à l'ordre d'où
la matière revient. » ; « Ce retour est daté du {date}, avant l'ordre {n°} du {date} : … » ; « « {réf} » : choisir le lot. » ;
« La quantité est positive. » ; « Le lot « {n°} » n'est sorti que de {x} kg pour cet ordre ({y} kg rendus) : on ne rend pas plus que
ce qui est parti. » (409) ; « Le magasin « {code} » est désactivé : il ne reçoit plus rien. » ; suspension par périmètre ; dates.

### Trouver un lot — `/atelier/chercher` (+ caméra)

Gestion MP : `Chercher.tsx` (`Scanner`) → PRO : `/atelier/chercher`, `EcranAtelier`, `Recherche`, `ScanQR`, `Carte` cliquable,
`Badge`, `ChargerPlus` ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Champ (focus auto) « Référence, couleur, numéro de lot… » ; envoi 250 ms après la frappe à `GET /soldes?q=` | `Recherche` (garde le focus), `GET lots?q=` 250 ms | — |
| Serveur : chaque mot dans référence, désignation, n° de lot, rôle, code magasin, fournisseur ; `ILIKE` **sensible aux accents** ; solde > 1 g ; tri référence puis date d'entrée | même règle, **sans accents** (`?q=` du contrat) | an. 18 |
| Caméra si `BarcodeDetector` : « 📷 Scanner une étiquette » / « Fermer la caméra » ; sinon note « Pour scanner : ouvrez l'appareil photo… » | `ScanQR` : « Scanner une étiquette » / « Fermer la caméra » ; même note de repli | sans émoji |
| Scanner : caméra arrière, vidéo pleine largeur, détection 250 ms ; `/lot/{n}` → fiche ; sinon `GET /lots/scan?code=` : 1 lot → fiche ; 0 ou plusieurs → **rien** | idem ; 0 → « Aucun lot pour cette étiquette ({texte lu}). » ; plusieurs → « {n} lots portent ce numéro : choisir ci-dessous » et la liste filtrée ; le scan continue | an. 19 |
| Échec caméra « La caméra n'est pas accessible ici (elle demande une adresse sécurisée https). Utilisez l'appareil photo du téléphone. » | idem | — |
| Liste **80 premiers** sans le dire ; carte « **{réf}** » ; « lot {n°} · entré le » / quantité (0 déc.) ; magasins / « ≈ N bobines » ; étiquette rouge « {q} en quarantaine » | 50 + `ChargerPlus` ; même carte ; « Reste » ; `Badge` quarantaine | an. 18 |
| Chargement « les lots » ; vide « Aucun lot en stock ne correspond. » (aussi sur coupure) | `Chargement` ; `Vide` ; coupure → « Pas de réseau » | (e), an. 3 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Saisie de la recherche | L, D | `GET lots?q=` | — | sans accents |
| « Scanner une étiquette » / « Fermer la caméra » | L, D | `GET lots/scan?code=` | — | messages 0 / plusieurs |
| Toucher une carte | L, D | — | — | → `/atelier/lots/{id}` |
| (nouveau) « Charger les suivants » | L, D | `GET lots` page suivante | — | an. 18 |

### Fiche du lot — `/atelier/lots/:id` (arrivée par QR `/lot/:id`)

Gestion MP : `LotFiche.tsx`, `/atelier/lot/:id` → PRO : `/atelier/lots/:id`, `EcranAtelier`, `Carte`, `Badge`, `Definitions`,
`LienDocument`, `BoutonImprimer`, `ChargerPlus` ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Lot {n°} », « ‹ » = page précédente | idem | — |
| `GET /lots/{id}` (prix masqués) | `GET lots/{id}` (`sans_prix`) | an. 27 |
| Toute erreur → titre « Lot introuvable », « ‹ » → `/atelier/chercher`, « Ce lot n'existe pas (étiquette d'une autre installation, ou lot supprimé). » + « Chercher un lot » | **404 seulement** → même écran ; coupure → « Pas de réseau » + « Réessayer » | (e), an. 3 |
| Carte (rouge si reste ≤ 1 g) : référence + statut (« Disponible », « En partie en quarantaine », « En quarantaine », « Épuisé ») ; note « {rôle} · {fournisseur} · entré le » | `Badge` (table unique) ; idem | — |
| « En stock » {q} (grand) ; « Bobines » « ≈ N bobines de X kg » | « Reste » {q} ; idem | vocabulaire « Reste » |
| Une ligne par magasin {code} / {q} ; quarantaine : code + étiquette « quarantaine », ou code seul en étiquette s'il contient « quarantaine » | un seul libellé de quarantaine (jamais « Quarantaine quarantaine ») | REGLES 6.4 |
| « Ordres servis : » liens « {n° OF} » → `/atelier/bons/{id}` | `LienDocument` → `/atelier/ordres/{id}` | — |
| « Ce qu'il a vécu » : « Reçu le {date} ({n° réception}, BL {n°}) — pesé {q} » ; **30 derniers** mouvements « {date} · {type} » / « {n° doc} · {magasin} · {auteur} » / « +q » vert, « −q » rouge ; libellés des 7 types | idem ; 30 puis `ChargerPlus` « voir les {n} autres » ; « Par » | an. 18 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Déplacer ce lot » | L, D | — | disponible hors quarantaine > 0, sinon raison sous le bouton « Rien de disponible hors quarantaine » | → `/atelier/deplacer?lot={id}` |
| « Imprimer l'étiquette » | L, D | `GET documents/etiquettes?lots={id}` (nouvel onglet) | — | `BoutonImprimer` |
| Lien n° d'ordre | L, D | — | — | → `/atelier/ordres/{id}` |
| (nouveau) « Charger les suivants » (mouvements) | L, D | `GET mouvements?lot_id=` page suivante | — | an. 18 |

### Déplacer — choix du lot — `/atelier/deplacer`

Gestion MP : `Deplacer.tsx:111-128` → PRO : `/atelier/deplacer`, `EcranAtelier`, `SelecteurLot` tactile, `ScanQR` ; D, A, L
(l'écran atelier : L, D).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /soldes` (lots en stock) | `GET lots/disponibles` | — |
| « Quel lot ? » : lots dispo > 0, « {réf} · lot {n°} », détail dispo, « Référence ou numéro de lot… » | `SelecteurLot` tactile, recherche sans accents | — |
| Note « Ou scannez l'étiquette de la palette, puis « Déplacer ce lot ». » | même note + bouton `ScanQR` sur place | raccourci |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Choisir un lot | L, D | — | — | → `?lot={id}` |
| (nouveau) « Scanner une étiquette » | L, D | `GET lots/scan?code=` | — | → `?lot={id}` |

### Déplacer un lot — `/atelier/deplacer?lot=ID`

Gestion MP : `Deplacer.tsx:37-110, 130-245` → PRO : `/atelier/deplacer?lot=ID`, `EcranAtelier`, `Selecteur`, `SegmentsTactiles`,
`Compteur`, `DateChamp`, `Zone`, `BandeauBlocages`, `Bouton({manque, blocages})`, `Confirmer` ; transfert D, A, L ;
**mise en quarantaine D, A, L ; libération D, A** (pas d'ici).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /lots/{id}`, `GET /magasins`, `GET /operations/motifs`, `GET /inventaires` | `GET lots/{id}`, `GET magasins`, `GET motifs`, `GET inventaires` | — |
| Carte : référence, « lot {n°} » | idem | — |
| Rien de disponible : « Ce lot n'a pas de matière disponible à déplacer » + « : il est en quarantaine, et seuls les achats le libèrent. » / « . » | « … : il est en quarantaine, et seuls les achats ou la direction le libèrent. » | (d) |
| « Depuis » : « {code} — {q} », non quarantaine, le plus garni d'abord ; quantité = tout | idem | — |
| « Vers » : « Choisir… » + magasins actifs autres ; quarantaine « (quarantaine : matière douteuse) » | idem | — |
| Unité (kg / bobines / palettes), plafonnée au disponible | `SegmentsTactiles`, arrondi vers le bas | an. 24 |
| « Quantité (disponible : {q}) » Compteur ; « Plus que ce qui est là. » ; « = {kg} » | idem | — |
| « Pourquoi ? » : « Rangement », « Approvisionnement de l'atelier » ; vers quarantaine : figé « Mise en quarantaine » ; défaut « Rangement » | idem (libération absente) | (d) |
| « Date » (max aujourd'hui) | `DateChamp` (+ min après clôture) | — |
| « Commentaire (facultatif) » / vers quarantaine « Commentaire (ce qui est douteux) » ≥ 3 car. | « Observations (facultatif) » / « Observations (ce qui est douteux) », obligatoires vers une quarantaine | (d), an. 8 |
| Bandeau : suspension du magasin de départ **ou** d'arrivée | `BandeauBlocages`, par périmètre (la matière du lot) | (b) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Tout le lot » | L, D | — | — | renommé « Tout ce qui est dans {code départ} » (an. 24) |
| « Déplacer {X kg} » | L, D | `POST operations` `{type:'transfert', date, motif, commentaire, lignes:[{matiere_id, lot_id, magasin_id, magasin_destination_id, quantite, unite}], valider:true}` | grisé ; raison sous le bouton : « Un inventaire est en cours (voir le bandeau) » · « Choisir le magasin d'arrivée » · « Saisir la quantité » · « Plus que ce qui est là » · « Écrire ce qui est douteux, dans les observations » ; `Confirmer` « Déplacer {X kg} de {départ} vers {arrivée} ? » · « Non » · « Oui, déplacer » | transaction unique ; succès « Fait — {TRF-AAAA-NNNN} : {X kg} déplacés. » + « Voir le lot » ; quantité **relue** sur le nouveau disponible (an. 24) |

Refus repris : « Un transfert va d'un magasin à un autre. » ; « Magasin de destination inconnu. » ; « Libérer une quarantaine est une
décision de la direction ou des achats, après contrôle de la matière. » (403) ; « Une entrée en quarantaine se fait avec le motif
« Mise en quarantaine ». » ; « Une mise en quarantaine se justifie : écrire ce qui est douteux. » (nouveau, serveur) ; « « {réf} » :
choisir le lot. » ; « La quantité est positive. » ; stock insuffisant ; magasin désactivé ; suspension ; dates.

### Monter les fils — choix du métier — `/atelier/montage`

Gestion MP : `Montage.tsx:28-65`, titre « Monter un fil » → PRO : `/atelier/montage`, `EcranAtelier`, `Carte` cliquable ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Monter un fil » | « Monter les fils » (comme la tuile) | an. 20 |
| `GET /metiers` (30 s) ; chargement ; erreur : message rouge **sans en-tête** | `GET metiers` ; `Chargement` ; erreur dans `EcranAtelier` avec « ‹ » ; coupure « Pas de réseau » | an. 3 |
| Note « Sur quel métier ? » | idem | — |
| Carte par métier **en service** (rouge si étage trop large ou densité 0) : « **{CODE · Nom}** » / « {kg montés} » ; note « {n} étage(s) garni(s) sur {N} · {f} fil(s) » + « · densité à saisir (direction) » | « {kg} sur les métiers » | an. 7 |
| Vide « Aucun métier en service. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Toucher un métier | L, D | — | — | → `?metier={id}` |

### Monter les fils — choix de l'étage — `/atelier/montage?metier=ID`

Gestion MP : `Montage.tsx:67-91` → PRO : même adresse, `EcranAtelier`, grille de `Tuile` d'étage (≥ 56 px) ; L, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « {CODE · Nom} », « ‹ » → `/atelier/montage` | idem | — |
| Note « Laize {L} m par étage · {kg} montés · {n} bobines. Quel étage ? » | « … · {kg} sur les métiers · … » | an. 7 |
| Boutons « **Étage {n}** », « {occupé} / {laize} m » ou « vide », « {f} fil(s) · {kg} » ; vert pâle garni, rouge pâle trop large | idem | — |
| Commentaire du métier en note | « Observations » du métier | an. 8 |
| Étage hors bornes → grille | idem | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Toucher un étage | L, D | — | — | → `?metier={id}&etage={n}` |

### Monter un étage — `/atelier/montage?metier=ID&etage=N`

Gestion MP : `Montage.tsx:96-374` (`MonterEtage`) → PRO : même adresse, `EcranAtelier`, `Carte`, `Progression` (largeur),
`Compteur`, `Zone`, `SelecteurMatiere` tactile, `Bouton({manque})`, `Confirmer` (carte de confirmation) ; L, D ;
`PUT metiers/{id}/etages/{etage}` (D, L).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Lecture seule : l'alimentation monte les fils. » (inatteignable) | supprimé | an. 16 |
| Données `GET /metiers`, `GET /articles` (prix masqués), `GET /montage/references` (poids retenu, sorti 30 j, déjà monté) | `GET metiers/{id}` (avec `version`), `GET montage/matieres` (matières montables, poids retenu, sorti 30 j, déjà monté) | — |
| Titre « {CODE} · étage {n} » | « {CODE · Nom} · étage {n} » | an. 20 |
| Carte « Largeur montée » « {m} / {laize} m » ; barre 10 px (rouge si trop, plafond 100 %) ; « {n} bobines » / « {kg} » ; « Plus large que la laize : {x} m de trop. » ; « La densité de ce métier n'est pas saisie : le poids reste à zéro (direction). » | `Progression` + mêmes textes | — |
| Note d'aide « **Mètres montés** … **Bobines pleines (%)** … Bobines = mètres × {densité} ; poids = bobines × kg par bobine pesé au lot × remplissage des bobines. » | idem | — |
| Formules : largeur = Σ mètres ; bobines = mètres × densité ; poids = bobines × kg/bobine retenu (pesé au lot : dernier sorti, sinon dernier reçu ; à défaut catalogue) × remplissage des bobines / 100 | idem (aide.json, une seule source) | — |
| Vide « L'étage {n} est vide : monter un fil ci-dessous. » | idem | — |
| Carte par fil (rouge si mètres ≤ 0) : référence ; « {désignation} · {X,XXX} kg / bobine · {lot … (sorti) / (reçu) / catalogue} » ou « poids de bobine inconnu : ce fil ne pèse rien » ; « Mètres montés » (pas 0,1) ; « Part du fil (%) » (pas 5, ≤ 100) ; « Commentaire » 300 ; « {n} bobines » / « {kg} » ; « Retirer ce fil » | idem ; « Part du fil (%) » bornée 0…100 aussi à la frappe ; « Observations » | an. 12, an. 8 |
| Ajout « Monter un fil à l'étage {n} » : matières actives hors rôles au mètre (Cuir, Franges, Ruban), pas déjà là ; « {réf} — {désignation} » ; détail « {X,XX} kg / bobine » (poids retenu) ; « Taper : rouge 2900, beige… » ; prend les mètres restants (≥ 0), 100 % | `SelecteurMatiere` tactile, **même poids retenu qu'au bureau** | an. 11 |
| Garde : `beforeunload` seulement ; naviguer dans l'appli perd la saisie | saisie gardée (`sessionStorage`) avec la `version` lue ; à la reprise, si la version a changé : « L'étage a été modifié ailleurs depuis : le recharger. » | an. 17 |
| Carte de confirmation (rouge si alertes) : « **Enregistrer l'étage {n} ?** » / « **Vider l'étage {n} ?** » ; « Le poids « sur les métiers » {augmente/baisse} de {x kg} ({avant} → {après}). C'est une information : le fil est déjà sorti, le stock ne change pas. » ; « … ne change pas. » ; « Métier arrêté : rien n'est compté sur lui. » ; alertes 30 j « … vérifier qu'il est bien parti aux machines (Envoyer) avant de le monter. » | même carte, **texte unique (a)** ; alerte 30 j (a) | an. 1 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| − / + / saisie (mètres, part), commentaire | L, D | — | — | bornes à la frappe |
| « Retirer ce fil » | L, D | — | — | — |
| Choisir un fil à monter | L, D | — | — | poids retenu (an. 11) |
| « Enregistrer l'étage {n}… » / « Saisir les mètres de chaque fil » | L, D | — | grisé, raison sous le bouton : « Aucune modification » · « Plus large que la laize » · « Saisir les mètres de chaque fil » ; ouvre la carte de confirmation | raison visible (an. 9) |
| « Oui, enregistrer » / « Oui, vider l'étage » (« Enregistrement… ») | L, D | `PUT metiers/{id}/etages/{etage}` `{version, fils:[{matiere_id, metres, pourcentage, commentaire}]}` | carte ouverte | succès « Étage {n} enregistré : {f} fil(s), {kg} ; sur les métiers {±x} kg. » ; ligne ajoutée à l'historique des montages ; invalidation globale ; 409 `version` → « L'étage {n} a été modifié entre-temps sur un autre poste : rechargez pour repartir de sa dernière version, puis refaites la modification. » + « Recharger l'étage » |
| « Non, revenir au montage » | L, D | — | — | — |
| « Annuler les modifications » | L, D | — | `Confirmer` « Annuler les modifications de l'étage ? » | saisie protégée |
| « Recharger l'étage » | L, D | `GET metiers/{id}` | après conflit | — |

Refus serveur repris : version 409 (texte ci-dessus, « modifié » sans « (e) ») ; « Étage {n} : ce métier n'en a que {N}. » (404) ;
« Matière inconnue. » ; « « {réf} » ({rôle}) se pose au mètre linéaire : elle ne se monte pas en bobines sur un métier. » ;
« « {réf} » est monté deux fois à l'étage {n}. » ; « « {réf} » à l'étage {n} : saisir les mètres montés. » ; « Étage {n} : {x} m
montés (mètres de chaque fil) pour une laize de {L} m. » ; bornes mètres 0…1000, remplissage des bobines 0…100, observations 300. Trace : journal
(action « montage ») **et** table d'historique des montages (métier, étage, par, le, fils avant/après, kg avant → après, écart,
origine téléphone/bureau).

### Signaler un besoin — `/atelier/signaler`

Gestion MP : `Signaler.tsx` → PRO : `/atelier/signaler`, `EcranAtelier`, `SelecteurMatiere` tactile, `Zone`, `SegmentsTactiles`,
`Bouton({manque})`, `Carte`, `Badge`, `ChargerPlus` ; C (`POST signalements`) ; traitement D, A (`POST signalements/{id}/traiter`).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /articles` ; `GET /signalements?tous=true` (300 plus récents de tous, 60 s) | `GET matieres` (sans prix) ; `GET signalements` filtrés **au serveur** sur le compte (identifiant), 60 s | an. 25 |
| « Matière (facultatif) » : matières actives « {réf} — {désignation} », « Référence, couleur… » | `SelecteurMatiere` tactile | — |
| « Quel besoin ? » zone 96 px, max 500, « Plus que deux palettes de beige, la série 8F commence lundi… » | `Zone` identique | — |
| `Segments` « Normal » / « Urgent » (défaut Normal) | `SegmentsTactiles` | — |
| « Mes signalements » : filtrés sur `par === nom`, 40 plus récents (« Les 40 plus récents sont affichés. ») ; carte rouge si urgent non traité ; « **{réf} / Sans matière précise** » ; « traité » / « urgent, en attente » / « en attente » ; texte ; « Signalé le … » ; « **Réponse de {nom}** le {date} : {réponse ou « — »} » | filtre par identifiant ; 40 puis `ChargerPlus` ; `Badge` mêmes libellés | an. 25, an. 18 |
| Chargement ; vide « Aucun signalement pour l'instant. » | `Chargement`, `Vide` ; coupure « Pas de réseau » | an. 3 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Segments Normal / Urgent | L, D | — | — | — |
| « Signaler aux achats » (« Envoi… ») | L, D | `POST signalements` `{matiere_id|null, texte, urgence}` | grisé, raison sous le bouton « Écrire le besoin (2 caractères au moins) » | an. 9 ; succès « Signalé : les achats le voient sur leur accueil. » ; saisie gardée jusqu'à l'envoi (an. 17) |
| (nouveau) « Charger les suivants » | L, D | `GET signalements` page suivante | — | an. 18 |

### Logique de l'envoi (règles partagées téléphone / bureau `/ordres/nouveau`)

Gestion MP : `pages/atelier/sortie.ts` + `SaisieSortie.tsx`, `production.py` (`/bons/proposition`, `blocages_bon`) → PRO : module de
saisie d'ordre partagé par `/atelier/envoyer` et `/ordres/nouveau`, `/ordres/:id` ; `POST ordres/proposition`, `POST ordres`,
`PUT ordres/{id}`, `POST ordres/{id}/valider`.

| Règle GMP | PRO | Changement |
|---|---|---|
| Trois temps : demande → lots → brouillon (modifiable, stock intact) ou validation (OF-AAAA-NNNN, tout ou rien) | idem | — |
| Saisie gardée : téléphone, nouvel ordre seulement (`sessionStorage`), effacée à l'enregistrement et à l'abandon, survit au rechargement | idem au téléphone ; au bureau, `Fenetre({sale})` | — |
| Proposition : qualités tissables ; besoin = Σ (kg/m² × m²) × (1 + taux de perte) ; fil commun = une ligne + `par_qualite` | idem | — |
| Lots `disponibles` : hors quarantaine, solde > 1 g, ordre d'entrée puis id, **tels qu'à la date de l'ordre** (`presents_au`, plus bas solde depuis) ; FIFO `min(porté, reste)` au gramme ; `manque` ; `disponibles` complets ; poids de bobine du lot sinon catalogue | idem ; la même lecture à la date sert l'ajout hors recette (`GET lots/disponibles?date=`) | an. 23 |
| `recettes_incompletes` (rôle sans matière, parts ≠ 100 %) | idem | — |
| Réponse : `theorique`, `manque`, `taux_perte`, `recettes_incompletes`, `lignes` (rôle puis référence) | idem + `blocages` connus à ce stade (date, inventaire du périmètre) | (b) |
| Recalculer remplace les prises de recette, garde les fils ajoutés à la main ; hors recette : pas d'appel | idem | — |
| Changer de magasin efface les prises ; date / hors recette / qualités / m² → « demande changée » ; métier et commentaire non | idem ; effacement confirmé | — |
| Brouillon rouvert : ligne au gramme ; en bobines si entier (± 0,002, ≥ 1) sinon kg ; dispo relu ; prévu relu à la date | idem ; dispo relu **à la date** | an. 23 |
| Un lot une seule fois ; calculs `sorti`, `écart`, `aEnvoyer`, `depassements` (> dispo + 0,001), `sansContenance`, totaux | idem | — |
| Refus à la validation laisse le brouillon enregistré et le dit | idem | — |
| Blocages serveur : « aucune matière à sortir » ; date ; « un ordre daté du … est déjà validé : dater ce bon … » ; magasin de quarantaine ; inventaire en cours sur le magasin ; qualité arrêtée ; lot (entré après / épuisé / x kg seulement) | mêmes blocages ; « dater cet ordre au moins de ce jour » ; inventaire : « l'inventaire {n°} compte « {réf} » dans « {mag} » » (périmètre) | an. 5, (b) |

### Métiers à tisser — `/metiers`

Gestion MP : `pages/Metiers.tsx`, `MetiersTisser.tsx:85-191`, `/metiers` (`?metier=ID|nouveau`) → PRO : `/metiers`, `Page`, `EnTete`,
`Indicateurs` (`Kpi`), `Carte`, `Filtres`, `Recherche`, `Interrupteur`, `DataTable` dans `Cadre`, `ExportExcel` ; C (lecture),
réglages D, fils montés D, L.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Menu « Référentiels › Métiers à tisser » (A, L + D) | `BarreLaterale` idem | — |
| Adresse `?metier=ID` / `?metier=nouveau` (replace), pas de `?onglet=` | `/metiers/:id?onglet=…` et `/metiers/nouveau` en fenêtre sur `/metiers` (filtres et défilement gardés) | A5, an. 29 |
| Titre « Métiers à tisser » ; sous-titre « … Ce poids, « Sur les métiers », est du stock en machine : il compte dans le stock de l'usine et sa valeur, et dans ce qu'on a avant de commander… » + texte par rôle (L / A / D) | `EnTete` ; sous-titre réécrit : « … Ce poids, « Sur les métiers », est du stock : il compte dans le stock global, sa valeur, le disponible et le projeté. Monter n'écrit aucun mouvement : le fil a déjà été sorti par un ordre. » + mêmes textes par rôle | an. 1, an. 7, (a) |
| `GET /metiers` (30 s) ; chargement ; erreur | `GET metiers` (valeur masquée pour L) ; `Chargement` ; `Erreur` | — |
| Indicateur « Métiers en service » (n ; « {n} arrêté(s) ») | `Kpi` idem, formule « métiers actifs » | — |
| Indicateur « Poids monté » « {Σ} kg » ; détail « {valeur} au coût moyen · stock en machine » (D, A) ou « sur les métiers en service · stock en machine » ; infobulle « Stock en machine : … » | `Kpi` « **Sur les métiers** » ; détail valeur au coût moyen (D, A) ; formule « Σ bobines × kg/bobine retenu, métiers en service ; compte dans le stock global, sa valeur, le disponible et le projeté » | an. 7, (a) |
| « Étages garnis » (Σ ; « sur {Σ} disponibles ») ; « Bobines » (Σ ; « montées sur les métiers en service ») | `Kpi` idem | — |
| Carte « Les métiers à tisser » ; « Nouveau métier » (D) → `?metier=nouveau` | action `EnTete`/carte (D) → `/metiers/nouveau` | — |
| `BarreRecherche` « Métier, fil monté, couleur… » (code, nom, commentaire, « référence désignation » des fils) ; case « montrer les métiers arrêtés » ; « {n} métier(s) » ; pas d'« Effacer » | `Recherche` (`Colonne.recherche` sur champs cachés) ; `Interrupteur` « Montrer les métiers arrêtés » ; « {n} métier(s) » ; « Effacer les filtres » + « N critère(s) » dès 2 | A1, A6 |
| Colonnes : « Métier » (**CODE · Nom** ; note « {commentaire} · monté par {nom} le {jj/mm/aa hh:mm} ») · « Laize (m) » (2 déc.) · « Densité (bobines/m) » (1 déc., « — » si 0) · « Étages garnis » (« g / e ») · « Fils montés » · « Bobines » · « Poids monté (kg) » · « À voir » (« densité à saisir », « étage{s} {n} trop large{s} », « {n} fil(s) sans poids de bobine », « {n} bobine(s) mesurée(s) ≠ catalogue ») · « État » (« en service » / « arrêté ») | mêmes colonnes ; « Poids monté (kg) » → « **Sur les métiers (kg)** » ; « monté par » lu dans l'historique des montages ; « Observations » ; tri au clic ; pied de totaux (Σ bobines, Σ kg) | an. 7, A2 |
| Ordre serveur (nom puis code), pas de tri, `Cadre court` | `Cadre` hauteur restante, tri au clic | A2 |
| Ligne cliquable → `?metier={id}` ; arrêté éteint | `lien` → `/metiers/{id}` | A5 |
| Vides « Aucun métier ne correspond. » / « Aucun métier. La direction les crée ici. » | `Vide` identiques | — |
| Pas d'« Exporter en Excel » | `ExportExcel` (route ajoutée, API-PRO § 1.24 : `GET /api/export/metiers`) | an. 29 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau métier » | D | — | — | → `/metiers/nouveau` |
| Recherche | C | — | — | champs cachés |
| Case « montrer les métiers arrêtés » | C | — | — | `Interrupteur` |
| (nouveau) « Effacer les filtres » | C | — | dès 2 filtres | A1 |
| Clic sur une ligne | C | `GET metiers/{id}` | — | → `/metiers/{id}` |
| (nouveau) « Exporter en Excel » | C | (route ajoutée, API-PRO § 1.24 : `GET /api/export/metiers`) | — | an. 29 |

### Nouveau métier — `/metiers/nouveau`

Gestion MP : `MetiersTisser.tsx:250-277` (`?metier=nouveau`, `ChampsMetier`) → PRO : `/metiers/nouveau`, `Fenetre({taille:'large', sale})`,
`Form` (`Saisie`, `Nombre`, `Interrupteur`, `Zone`), `Bouton({manque})` ; D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Ouverte **pour tous les rôles** par l'adresse ; seul le bouton réservé à D | A, L → `/metiers` avec « La création d'un métier est réservée à la direction. » | an. 15 |
| Garde « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » (sale = code, nom ou commentaire) | `Fenetre({sale})`, mêmes textes (sale = tout champ) | A4 |
| « Code » — « le repère court, utilisé dans les ordres et les contrôles » | `Saisie` 1…32 | — |
| « Nom » — « Métier du fond, Van de Wiele n° 2… » — « celui qu'on emploie à l'atelier » | `Saisie` ≤ 120 | — |
| « Laize d'un étage (m) » 4,2 — « largeur utile : … » | `Nombre` 0…100 à la frappe | — |
| « Densité (bobines par mètre) » 0 — « 320 = 320 bobines par mètre de laize monté » | `Nombre` 0…100 000 | — |
| « Nombre d'étages » 6 (entier) — « de 1 à 40 ; six ou huit selon la machine » | `Nombre` entier 1…40 | — |
| Case « métier en service (un métier arrêté ne compte pas dans le stock) » cochée | `Interrupteur` | — |
| « Commentaire » (zone 2 lignes) | « Observations » (`Zone`) ≤ 2 000 | an. 8 |
| Note « Une fois créé, le métier s'ouvre : l'alimentation y monte ensuite ses fils, étage par étage. » | `Note` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Abandonner » (si saisie) / « Annuler » | D | — | garde `sale` | — |
| « Créer le métier » (« Création… ») | D | `POST metiers` `{code, nom, laize, bobines_par_metre, etages, actif, commentaire}` (`bobines_par_metre` : la « densité » de Gestion MP) | grisé avec raison (infobulle) : « le code », « un nombre d'étages de 1 à 40 » | an. 9 ; succès → `/metiers/{id}` ; refus « Le métier « {code} » existe déjà. » (409), « Cette action est réservée à : la direction. » (403), bornes |

### Fiche métier — onglet « Fils montés » — `/metiers/:id?onglet=fils`

Gestion MP : `MetiersTisser.tsx:320-723` (`FicheMetier`), `?metier=ID` → PRO : `/metiers/:id?onglet=fils`,
`Fenetre({taille:'tresLarge', sale})`, `Onglets`, `Note`, `DataTable` de saisie (groupée par étage) dans `Cadre`, `Nombre`,
`Selecteur`, `SelecteurMatiere`, `Badge`, `LienDocument` ; lecture C ; fils D, L ; réglages D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Métier {CODE · Nom} » + étiquette « arrêté » | idem, `Badge` | — |
| Garde si (monteur et fils modifiés) ou (D et réglage modifié) | `Fenetre({sale})` | — |
| Achats : « Lecture seule : l'alimentation monte les fils, la direction règle le métier. » ; tout figé, pas de pied | idem | — |
| Onglets « Fils montés » (compteur, « • » si modifié) / « Réglages du métier » ; **hors adresse** | `Onglets` `?onglet=fils|reglages|historique` (« • » si modifié) ; 3ᵉ onglet « Historique » | an. 29, (a) |
| Note « Laize {L} m par étage · densité {d} bobines par mètre (ou « à saisir (réglages) ») · bobines = mètres × densité ; poids = bobines × kg / bobine pesé au lot × remplissage des bobines … Monté : **{kg} kg**, {n} bobines. » + « Métier arrêté : ce poids ne compte pas dans le stock. » | « … Sur les métiers : **{kg} kg**, {n} bobines. » ; même note d'arrêt | an. 7 |
| « Dernier montage : {nom}, le {date} — {détail du journal} » | lu dans l'historique des montages ; lien vers l'onglet « Historique » | (a) |
| Erreur de catalogue (message rouge) | `Erreur` | — |
| Ligne d'étage : « Étage {n} · {f} fil(s) » / « vide » + « — au-delà du dernier étage » / « — plus large que la laize » ; « {occupé} / {laize} m » (rouge si trop) ; Σ bobines ; Σ poids (1 déc.) | idem | — |
| Colonne « **Fil** » : référence ; « {désignation} · {X,XXX} kg / bobine · {source} » + « (catalogue X,XXX kg) » ; `Badge` critique « aucun poids de bobine (ni pesé, ni au catalogue) : ce fil ne pèse rien dans le stock » ou attention « pesé ±X % au catalogue : le catalogue est à revoir » ; lien « ouvrir la matière » → `/catalogue?matiere=` (A, D, dans ces deux cas) | en-tête « **Référence** » ; mêmes notes et badges ; lien → `/matieres/{id}` (D, A) | an. 8 |
| « Mètres » (110 px) `ChampNombre` | `Nombre` 0…1000 | — |
| « Part (%) » (100 px) **sans plafond** | `Nombre` 0…100 à la frappe | an. 12 |
| « Bobines » (entier) ; « Poids (kg) » (1 déc.) | idem | — |
| « Étage » : « Étage {n} » (option grisée « (déjà monté) ») + « Étage {n} (hors machine) » ; « Déplacer ce fil à un autre étage » | `Selecteur` idem | — |
| « Commentaire » 300 | « Observations » | an. 8 |
| Bouton « Retirer » (« Retirer ce fil du métier ») | idem | — |
| Ligne de fil rouge si mètres ≤ 0 | idem | — |
| Pied « Toute la machine » : Σ mètres **bruts**, Σ bobines, Σ kg | Σ **largeur occupée** (Σ mètres), Σ bobines, Σ kg | an. 13 |
| Ajout : « Monter à l'étage {n} ({occupé} / {laize} m) » + recherche (matières actives hors rôles au mètre, pas déjà là) ; « {réf} — {désignation} · {fournisseur} » ; détail poids **catalogue** ou « poids de bobine inconnu » ; « Taper quelques mots : référence, couleur, fournisseur… » ; mètres restants, 100 % | `Selecteur` d'étage + `SelecteurMatiere` ; détail = **poids retenu par le montage** (comme au téléphone) | an. 11 |
| Alertes « Des fils sont montés au-delà du dernier étage : les déplacer ou les retirer. » ; « Saisir les mètres montés de : {réf, …}. » | `Blocages` | — |

Gestes : voir « Pied de la fiche métier » ci-dessous (saisies de cellule, « Retirer », ajout).

### Fiche métier — onglet « Réglages du métier » — `/metiers/:id?onglet=reglages`

Gestion MP : même fenêtre, onglet « Réglages du métier » → PRO : `?onglet=reglages`, champs de « Nouveau métier » ; écriture D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Champs de § 3.2 figés hors direction | idem (`Form` en lecture pour A, L) | — |
| Note « Changer la densité change le stock compté sur le métier. Réduire les étages ou la laize demande d'abord de retirer ou déplacer les fils qui dépasseraient. » + « Nommé par {n} ordre(s) de fabrication. » | « Changer la densité change le stock sur les métiers. … » ; même suite | an. 1 |

### Fiche métier — onglet « Historique » (nouveau) — `/metiers/:id?onglet=historique`

Gestion MP : absent (seul le « dernier montage » du journal) → PRO : `?onglet=historique`, `DataTable` + `ChargerPlus` + `Historique`
(journal avant/après des réglages) ; C.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Dernier montage : … » (journal, texte) | tableau des montages : « Le » (jj/mm/aaaa hh:mm) · « Par » · « Étage » · « Fils » (avant → après) · « Sur les métiers avant (kg) » · « après (kg) » · « Écart (kg) » · « Origine » (téléphone / bureau) ; `GET metiers/{id}/montages` ; l'origine est déduite de l'étage de l'événement (route 100 → « téléphone », routes 97 et 99, même d'un seul étage → « bureau » : MODELE-DONNEES `montage_evenement`) | (a) |
| Journal des réglages | `Historique` (`GET historique/metier/{id}`) | — |
| — | vide « Aucun montage enregistré. » | — |

### Pied de la fiche métier et gestes — `/metiers/:id`

Gestion MP : `MetiersTisser.tsx` § 3.5 → PRO : pied de `Fenetre`, `Bouton({manque, blocages})`, `Confirmer` ; fils D, L ; réglages D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Étage(s) trop large(s) : {n, …}. » (rouge) / « Modifications non enregistrées. » / « Aucune modification. » | idem | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Onglets « Fils montés » / « Réglages du métier » | C | — | — | + « Historique », dans l'adresse |
| Saisie mètres / part / étage / commentaire, « Retirer », ajout d'un fil | D, L | — | — | part 0…100 |
| Champs du réglage | D | — | — | — |
| « Supprimer » (rouge) | D | `DELETE metiers/{id}?version=` | grisé : « Des fils y sont montés : les retirer d'abord » · « Nommé par {n} ordre(s) : l'arrêter plutôt (réglages) » ; `Confirmer` « Supprimer le métier {CODE} ? » · « Non » · « Oui, supprimer » | refus 409 repris |
| « Annuler les modifications » / « Fermer » | D, L | — | « Annuler… » si modifié | — |
| « Enregistrer » (« Enregistrement… ») | D, L | L (fils) : `PUT metiers/{id}/montage` `{etages: [{etage, version, fils:[{matiere_id, metres, pourcentage, commentaire}]}], confirme_effet_kg}` (seuls les étages envoyés sont remplacés ; API-PRO 99 fait foi) ; D : `PUT metiers/{id}` `{code, nom, laize, bobines_par_metre, etages, actif, commentaire, version, montage?}` (**réglage et montage dans une seule transaction** ; réponse `MetierModifie` = la fiche + `montage`) | grisé avec raison **qui suit l'état** (« Aucune modification », « Étage {n} trop large », « Fils hors machine », « Saisir les mètres de … », « le code », « étages de 1 à 40 ») ; `Confirmer` : **texte unique (a)** + « **Attention : {alertes 30 j}.** » + « Enregistrer ? » · « Non » · « Oui, enregistrer » | an. 1, an. 9, an. 14 ; succès « Enregistré : le stock sur les métiers est recalculé. » ; ligne d'historique ; 409 `version` → « Il a été modifié sur un autre poste (ou au téléphone) : le recharger avant de refaire la modification. » + « Recharger le métier » ; refus repris (« Le métier « {code} » existe déjà. », « Des fils sont montés à l'étage {n} : … ramener le métier à {N} étage(s). », « Étage {n} : {x} m montés, plus que la laize de {L} m demandée. Retirer d'abord du fil. », refus de `_verifier_fils`) |
| « Recharger le métier » | D, L | `GET metiers/{id}` | après conflit | « Métier rechargé dans sa dernière version : refaire la modification. » |
| Fermer la fenêtre (×, Échap, fond) | C | — | garde `sale` | retour à `/metiers` (filtres gardés) |

Notions reprises : laize, densité, étage, remplissage des bobines, largeur occupée = Σ mètres, poids de bobine retenu (pesé au lot :
dernier sorti, sinon dernier reçu ; à défaut catalogue — M43), tolérance de bobine (= tolérance de réception), métier en service /
arrêté (un arrêté ne compte pas), « Sur les métiers » (a), **`version`** (remplace l'empreinte), historique des montages, « sorti
récent » = 30 jours.

### Document « Étiquettes de lots » — `GET /api/documents/etiquettes?lots=1,2`

Gestion MP : `GET /api/lots/etiquettes?ids=` (`stock.py:361-415`), HTML produit par le code → PRO : gabarit Jinja2,
`GET documents/etiquettes?lots=`, ouvert par `BoutonImprimer` (nouvel onglet) ; C.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Paramètre `ids` (≤ 4 000 car.) ; morceau non numérique ou lot inconnu **ignoré sans rien dire** ; aucun valide → **JSON brut** 404 « Aucun lot à étiqueter. » | `lots` ; ignorés listés en tête de page (« Ignorés : {…} ») masqué à l'impression ; aucun valide → page HTML lisible « Aucun lot à étiqueter. » | an. 28 |
| QR = `{base}/lot/{id}` ; base = réglage « Adresse du serveur pour les téléphones » (http(s)://, ≤ 200, sans espace) sinon adresse d'appel, « localhost » → IP du serveur ; `segno`, correction M, SVG | idem | — |
| Page « Étiquettes de lots », bouton « Imprimer » masqué à l'impression ; une page par étiquette `@page 100mm 70mm, marge 4mm` ; bloc 60 mm ; QR 34 × 34 mm à gauche ; texte 10 pt ; bordure pointillée écran | idem (gabarit) | — |
| 1 référence (13 pt gras) · 2 « **Lot {n°}** » (16 pt) · 3 fournisseur (du lot, sinon de la matière) · 4 « Entré le » · 5 « {q} kg à l'impression » (**quarantaine comprise**) ou « {x} kg ≈ {y} ml » · 6 « N° {id} » (9 pt gris) · 7 si quarantaine > 1 g « **QUARANTAINE — NE PAS SORTIR** » | 1 à 4 idem ; 5 « Reste {q} kg à l'impression » + « dont {x} kg en quarantaine » si une part y est, + « ≈ N bobines » si poids connu ; 6, 7 idem | an. 28 |
| Points d'appel (7) : atelier fiche du lot « Imprimer l'étiquette » ; page bureau du lot (action d'en-tête) ; Stock fenêtre d'un lot ; Stock liste des lots « Étiquettes ({n}) » (« Imprimer les étiquettes QR des lots cochés », grisé sans case) ; réception validée — message « Imprimer les étiquettes QR à coller sur les palettes » ; réception validée — pied « Imprimer les étiquettes des lots » ; liste des réceptions « Étiquettes » | `/atelier/lots/:id` ; `/lots/:id` (action `EnTete`, sert aussi de fenêtre sur `/stock?onglet=lots`) ; `/stock?onglet=lots` « Étiquettes ({n}) » ; `/receptions/:id` message et pied ; `/receptions?onglet=validee` « Étiquettes » — 6 points (lot bureau et fenêtre Stock fondus) | A5 |
| Lecture : appareil photo → `/lot/{id}` → téléphone `/atelier/lot/{id}` ; scanner intégré | `/lot/{id}` : téléphone + L → `/atelier/lots/{id}`, sinon `/lots/{id}` | an. 2 |
| Route voisine `GET /api/acces/qr` (QR de l'adresse, Réglages) et `GET /api/acces` | `GET acces/qr`, `GET acces` montrés dans `/administration?onglet=telephone` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer » (dans le document) | C | — (`window.print()`) | — | — |

### Droits serveur des routes de l'atelier et des métiers

| Route GMP (garde) | Route PRO (rôles) |
|---|---|
| `GET /bons`, `/bons/{id}`, `/bons/{id}/lots-sortis`, `POST /bons/proposition` (tout connecté) | `GET ordres`, `ordres/{id}`, `ordres/{id}/lots-sortis`, `POST ordres/proposition` (C) |
| `POST /bons`, `PUT/DELETE /bons/{id}`, `/valider`, `/annuler` (alimentation + D) | `POST ordres`, `PUT/DELETE ordres/{id}`, `/valider`, `/annuler` (D, L) |
| `GET /operations/motifs`, `/operations`, `/operations/{id}` (tout connecté) | `GET motifs`, `GET operations`, `GET operations/{id}` (C ; `sans_prix` pour L) |
| écritures `/operations…` : `STOCK` puis `_autorise` (retour machine L ; transfert A, L ; libération A) | droit par type : retour machine D, L ; transfert D, A, L ; mise en quarantaine D, A, L ; libération D, A |
| `GET /soldes`, `/lots/{id}`, `/lots/scan`, `/lots/etiquettes`, `/mouvements` | `GET lots`, `lots/{id}`, `lots/scan`, `lots/disponibles`, `documents/etiquettes`, `mouvements` (C) |
| `GET /metiers`, `/montage/references`, `/magasins`, `/articles`, `/qualites` | `GET metiers`, `montage/matieres`, `magasins`, `matieres`, `qualites` (C) |
| `POST /metiers`, `PUT/DELETE /metiers/{id}` (D) | idem (D) |
| `PUT /metiers/{id}/fils`, `PUT /metiers/{id}/etages/{n}` (alimentation + D) | `PUT metiers/{id}/montage`, `PUT metiers/{id}/etages/{etage}` (D, L) ; + `GET metiers/{id}/montages` (C) |
| `GET/POST /signalements` (tout connecté) ; `POST /signalements/{id}/traiter` (achats) | idem (C) ; traiter (D, A) |
| `GET /inventaires` (tout connecté, prix masqués) | idem (C, `sans_prix`) |
| Refus « Cette action est réservée à : {rôles}. » ; « « {type} » est réservé à : {rôles}. » | mêmes textes, rôles lus dans le registre |

### Anomalies GMP corrigées (Partie 3)

1. Fil « sur les métiers » contradictoire → texte unique (a) partout ; compté dans le stock global, sa valeur, le disponible et le projeté ; aucun mouvement au montage.
2. QR scanné au téléphone par les achats, renvoyé sans dire → `/lot/:id` ne mène à l'atelier que pour L ; sinon `/lots/:id` ; `EcranReserve` dit pourquoi.
3. Erreurs réseau vues comme listes vides / « introuvable » / ordre vierge → « Pas de réseau » + « Réessayer » sur toute lecture ; « introuvable » sur 404 seulement ; `?ordre=` rouvre le brouillon ou dit l'erreur ; montage avec en-tête.
4. Hors ligne et retry sur texte → SW qui garde l'enveloppe (jamais les données) ; retry selon le statut HTTP.
5. « bon » dans les messages serveur → « ordre » partout (« Ordre introuvable. », « Cet ordre est déjà validé. », « dater cet ordre… »).
6. « Ordre du {date} » pour un brouillon → « Brouillon » + date en note.
7. « stock en machine », « Poids monté » → « Sur les métiers » (indicateur, colonne, notes).
8. « Fil » en en-tête → « Référence » ; « Commentaire » → libellé « Observations » partout (champ API `commentaire` inchangé) — REGLES § 5 « Remarques → Observations ».
9. Boutons grisés sans raison au téléphone → `Bouton({manque, blocages})` : raison écrite sous le bouton (Garder en brouillon, Valider sans quantité, Signaler, Enregistrer l'étage) ; au bureau infobulle qui suit l'état (Créer le métier, Enregistrer).
10. Ordre annulé présenté comme validé → titre et note selon le statut (« Ordre annulé »).
11. Poids de bobine différent téléphone / bureau dans l'ajout → poids retenu par le montage aux deux endroits.
12. Part sans plafond au bureau, nombre négatif tapé → `Nombre` / `Compteur` bornés 0…100 à la frappe, min 0.
13. Pied « Toute la machine » en mètres bruts → largeur occupée pondérée par la part.
14. Enregistrement fils + réglage en deux appels → un seul `PUT metiers/{id}` transactionnel pour D (fils facultatifs) ; L : `PUT metiers/{id}/montage`.
15. `?metier=nouveau` ouvert à tous → `/metiers/nouveau` réservé à D, message pour A, L.
16. Code mort (« Lecture seule… » au téléphone, zone `droite`) → retirés.
17. Saisies perdues en naviguant (Montage, Retour, Déplacer, Signaler) → chaque saisie atelier gardée et reprise (avec `version` pour le montage).
18. Listes tronquées sans le dire (80 lots, 60 ordres, 30 mouvements), recherche serveur sensible aux accents → `ChargerPlus` qui dit « n sur total » ; `?q=` sans accents.
19. Scanner muet → messages « Aucun lot pour cette étiquette » / « {n} lots portent ce numéro ».
20. Nom du métier variable, titres « Monter les fils » / « Monter un fil » → « CODE · Nom » partout (champ serveur unique) ; titre « Monter les fils » partout.
21. « parti (net) » → « Sorti net ».
22. Accueil atelier en brut → « sortis net » (brut − retours).
23. Fil hors recette au disponible du jour → `lots/disponibles?date=` à la date de l'ordre, comme la proposition.
24. Après déplacement, quantité qui reste ; « Tout le lot » trompeur ; arrondi au-dessus au retour → quantité relue ; « Tout ce qui est dans {code} » ; conversion bornée vers le bas.
25. « Mes signalements » sur le nom affiché, 300 derniers de tous → filtre serveur par identifiant, paginé.
26. « Abandonner cette sortie » recharge l'appli → remise à zéro de l'état et navigation interne.
27. Résidus `devise` / `unite_prix` pour L → `sans_prix` générique les retire ; essai DOM.
28. Étiquettes : ids ignorés en silence, 404 JSON brut, quantité avec quarantaine sans le dire, pas de bobines → ignorés listés, page d'erreur HTML, « Reste … dont … en quarantaine », « ≈ N bobines ».
29. Onglets de la fiche métier hors adresse, pas d'export → `?onglet=fils|reglages|historique` ; `ExportExcel` (route ajoutée, API-PRO § 1.24).

### Comptes de la partie 3

- **Écrans / pages** : 20 sections d'écran PRO — atelier 17 (cadre commun, accueil, envoyer étape 1, étape 2, sortie enregistrée,
  ordre non brouillon, ordres, détail d'un ordre, retour choix, retour sur un ordre, trouver un lot, fiche du lot, déplacer choix,
  déplacer un lot, montage métier, montage étage, monter un étage, signaler ; « ordre non brouillon » devient une redirection),
  bureau 1 (`/metiers`) ; + règles d'envoi et table des droits (2 sections de référence). Les 18 écrans GMP sont tous repris.
- **Onglets / sous-vues** : 7 — fiche métier « Fils montés », « Réglages du métier », « Historique » (nouveau) ; bascule recette /
  hors recette (2) ; vue caméra `ScanQR` ; carte de confirmation de montage ; (+ vue repliée « tout est conforme », nouvelle).
- **Fenêtres** : 2 (`/metiers/nouveau`, `/metiers/:id`) + 1 document (« Étiquettes de lots », 6 points d'appel PRO pour 7 GMP).
- **Gestes** : 92 gestes GMP repris (accueil 12, demande 6, lots 9, sortie enregistrée 3, ordre non brouillon 1, ordres 1, détail 5,
  retour choix 2, retour sur ordre 6, trouver 3, fiche du lot 4, déplacer 6, montage 11, signaler 3, métiers page 4, nouveau 3,
  fiche 12, document 1) ; + 14 nouveaux (Réessayer, changer de magasin confirmé, déplier « tout est conforme », 5 « Charger les
  suivants », scanner au choix du lot, Effacer les filtres et Exporter sur `/metiers`, confirmations « Effacer les quantités » et
  « Annuler les modifications » de l'étage, onglet Historique).
- **Anomalies** : 29 / 29 traitées.

### Routes demandées par la partie 3 (reportées dans API-PRO § 1.24)

- `GET /api/export/metiers` (C ; valeur masquée pour L) — « Exporter en Excel » de `/metiers`.
- Aucune autre : les retours et transferts du téléphone passent par `POST operations` avec `valider: true` (champ du corps, pas une
  route) ; le filtre « mes signalements » est un paramètre de `GET signalements`.


---

---

## Partie 4 — Achats : plan d'achat, préparation, commandes, réceptions, réclamations, poids des bobines, archive des pesées, bon de commande fournisseur

Source : `docs/heritage/ECRANS.md` l. 2957-4018. Rôles : D direction, A achats (L et T n'ont aucun de ces
écrans : `EcranReserve`). Routes d'API écrites sans le préfixe `/api`. « anom. 4.n » renvoie à la liste
numérotée de la fin de la partie.

**Points tranchés appliqués ici** : bon de commande fournisseur A4, anglais, sans prix/montant/devise,
papier à en-tête, même contenu en HTML (gabarit Jinja2) et en Excel ; doublon français avec prix
`/export/bon-de-commande/{id}` supprimé ; l'approbation porte la date réelle d'envoi ; historique des
décisions d'approbation = table `commande_decision` (demande, approbation, renvoi + motif, version
rétablie) affichée sur la fiche ; `commande.solde_origine` (+ `solde_par_id`, `solde_le`) et
`reception.annulation_motif` sont de vraies colonnes ; une réception entièrement refusée peut être
annulée ; la case « Envoyer avec nos prix du catalogue » est **supprimée** (voir 4.4) ; un camion en deux
devises s'enregistre en **une** requête atomique (`POST receptions` renvoie la liste créée).

### 4.0 Règles transverses de la partie — (toutes les routes ci-dessous)

Gestion MP : rappels transverses de la Partie 4 (garde `['achats']`, `useEnvoi`, `Confirmer`, `Dialogue sale`, `useOuvrirDepuisAdresse`, `BoutonExport`, `CLES_ACHATS`) → PRO : registre `routes.ts`, `Coque`, `Messages`, `Confirmer`, `Fenetre`, `useFicheAdresse`, `ExportExcel` ; rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde `garde(['achats'])` (`App.tsx:253-256`), renvoi à l'accueil avec `refuse` | `routes.ts` rôles D, A ; `EcranReserve` « L'écran demandé (…) est réservé à un autre rôle » | même effet, une source |
| Droits serveur `ACHATS` / `DIRECTION`, 403 « Cette action est réservée à : responsable achats. » / « … : la direction. » ; 401 « Connectez-vous pour continuer. » / « Ce compte n'est plus actif. » | mêmes textes ; garde déclarée par route, essai qui balaie toutes les routes | — |
| Refus métier 422 `detail` affiché tel quel | `Messages` (toast rouge = `detail`) ; refus prévisibles calculés d'avance dans `blocages` des fiches (A8) | refus annoncés avant le clic |
| `useEnvoi` (occupe, bandeau vert / rouge) | `Bouton({occupe})` + `Messages` | toasts au lieu du bandeau de carte |
| `Confirmer` « question · Non · Oui… » | `Confirmer` (motif facultatif ou exigé) | — |
| `Dialogue sale` « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » | `Fenetre({sale})`, pile, Échap ferme celle du dessus | — |
| « Un instant — chargement : {quoi}… » | `Chargement` (même texte) | — |
| `lib/format.ts` (`nombre`, `montant`, `montantCourt`, `montants`, `part`, `jours`, `date`, `horodatage`, `metres`) ; `signe(x,d)` (« 0 % », jamais « −0,0 % ») en double | `format.ts` unique ; `Montant`, `KgEtMetres` | une seule `signe` |
| `useOngletAdresse` ; `useOuvrirDepuisAdresse` (`?ouvrir=`, `?reception=`, `?commande=`, effacés à la fermeture) | `useOngletAdresse`, `useFicheAdresse` : `/commandes/:id`, `/receptions/:id`, `/reclamations/:id` ; anciens `?ouvrir=ID`/`?commande=ID`/`?reception=ID` redirigés | adresse stable (A5, R22) |
| `BoutonExport` « Exporter en Excel » (infobulle « La liste affichée (onglet et recherche) dans un classeur Excel ») | `ExportExcel` : envoie onglet, recherche **et tous les filtres** | export = liste affichée |
| `CLES_ACHATS` (27 caches rafraîchis) | invalidation globale TanStack après chaque mutation | — |
| Recherche `filtrer` (mots, tout ordre, sans accents) ; exports refont la recherche | `Recherche` + `Colonne.recherche` (champs cachés) ; `?q=` même règle au serveur (A6) | — |
| `brouillons.py` « Tout valider » ignore commandes et réceptions (anom. 4.20) | `GET brouillons` inclut les réceptions brouillons (validées selon le droit D, A) ; brouillons de commande dans « Ma journée » (à envoyer, l'envoi porte une date : pas d'envoi en masse) | file commune |
| Fiches sans onglet « Historique » | onglet « Historique » (`Historique`, `GET historique/{objet}/{id}`) sur commande, réception, réclamation | journal avant/après |

---

### 4.1 Plan d'achat (en-tête, indicateurs) — `/plan-achat`

Gestion MP : « Plan d'achat » `/plan-achat` (`PlanAchat.tsx`) → PRO : `/plan-achat` (`Page`, `EnTete`, `Indicateurs`/`Kpi`, `Onglets`, `Messages`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /plan-achat` (+ `date_reference` non utilisée) et `GET /stock` (disponible, commandé, couverture, kg_par_ml) | `GET plan-achat` seul : chaque ligne porte disponible, commandé, couverture, `kg_par_ml`, unités possibles | une lecture au lieu de deux ; date de référence = aujourd'hui serveur (non exposée, comme GMP) |
| Chargement « … le plan d'achat… » ; erreur bandeau, sinon « Le plan d'achat est indisponible. » | `Chargement` ; `Erreur` (même texte) | — |
| Titre « Plan d'achat » ; sous-titre « Ce qu'il faut commander au {date}, chez qui, et quand. « Préparer la commande » ouvre la proposition à arbitrer. » | `EnTete({titre, fil « Achats › Plan d'achat », aide « ? »})` + sous-titre identique | aide `aide.json#plan-achat` |
| Bandeau succès après création : 1 bon « Bon de commande créé en brouillon, sans numéro tant qu'il n'est pas envoyé. Relisez-le, imprimez-le et envoyez-le depuis l'écran Commandes. » + « Ouvrir le brouillon » ; n bons « {n} bons de commande créés en brouillon (un par devise : USD, EUR), sans numéro … » + « Ouvrir les brouillons » | `Messages` (toast persistant jusqu'au clic) + `LienDocument` → `/commandes/:id` ou `/commandes?onglet=brouillon` | lien vers l'adresse stable |
| KPI « Références à commander » = nb lignes à commander > 0 ; détail « dont {n} en alerte » (statut ∈ `STATUTS_EN_ALERTE`) | `Kpi({formule})` même formule | formule dans `aide.json` |
| KPI « Budget indicatif » `montantCourt(budget_mad)`, détail « {kg} kg · prix catalogue », infobulle montant exact | `Kpi` + `Montant` | — |
| KPI « Références classe A » détail « à commander » | `Kpi` | — |
| KPI « Ruptures » (teinte rupture/ok), détail « {c} crit. · {u} urg. · {a} ATTENTION », compté sur **toutes** les lignes de stock | `Kpi` ; détail « sur toutes les matières · {c} crit. · {u} urg. · {a} ATTENTION » ; `lien` → `/stock?onglet=matieres&statut=rupture` | dit son périmètre (anom. 4.14) |
| KPI « À émettre cette semaine » = lignes Tier 1 (teinte critique), détail « {n} sous 7 jours » (Tier 2) ; règle des tiers (`moteur.py:1605-1626`) | `Kpi` ; libellés « Tier 1 »… sans émoticône | `lien` → onglet Références filtré Priorité = Tier 1 |
| Onglets « Par fournisseur » (compte fournisseurs) · « Références à commander » (compte lignes), défaut `fournisseurs`, `?onglet=` | `Onglets` (compteur), `?onglet=fournisseurs|references` | — |
| Une `BarreRecherche` partagée, valeur gardée entre onglets | `Recherche` dans `?q=` (partagée) | — |
| Aucun filtre, pas de tri, pas de pagination | `Filtres` liés par onglet (voir 4.2, 4.3) + « Effacer les filtres » dès 2 + « N critère(s) » ; en-têtes triables (défaut = ordre serveur) ; `Cadre` hauteur restante | A1, A2 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Besoins des mois à venir » (lien, infobulle « Les kilos que le plan de production consommera, mois par mois ») | D, A | — (→ `/production?onglet=besoins`) | — | — |
| « Exporter en Excel » (`/export/pilotage`, infobulle « Le stock, le plan d'achat, les fournisseurs, les besoins et les contrôles dans un classeur Excel ») | D, A | `GET export/plan-achat?onglet=&q=&…` (route ajoutée, API-PRO § 1.24 : `GET /api/export/plan-achat`) pour la liste affichée ; menu « Classeur de pilotage complet » → `GET export/pilotage` | — | export = liste affichée (anom. 4.14) ; classeur complet gardé à part |
| « Ouvrir le brouillon » / « Ouvrir les brouillons » (bandeau) | D, A | — (→ `/commandes/:id` ou `/commandes?onglet=brouillon`) | — | adresse stable |

### 4.2 Plan d'achat › Par fournisseur (table des fournisseurs, partagée) — `/plan-achat?onglet=fournisseurs`

Gestion MP : onglet « Par fournisseur » + `TableFournisseurs.tsx` (aussi dans « Nouvelle commande ») → PRO : `DataTable` (colonnes partagées `colonnesFournisseursPlan`), `Badge`, pied de totaux, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre de carte « Fournisseurs à solliciter, le plus gros budget d'abord » | `Carte` même titre | — |
| Recherche : nom, pays, contact, urgence, devises ; placeholder « Fournisseur, pays, devise… » | `Colonne.recherche` mêmes champs | — |
| — | `Filtres` liés : Urgence, Devise, Pays — transmis aussi à l'export (`GET export/plan-achat?onglet=fournisseurs&urgence=&devise=&pays=`) | ajout (A1) |
| Col. « Fournisseur » : **nom** ; note contact ; note « {n} référence(s) en rupture » | `Colonne` `rendu` + `lien` → `/fournisseurs/:id` (fenêtre) | lien fiche fournisseur |
| « Pays » (ou « — ») | idem | — |
| « Devise(s) » (infobulle « Un bon de commande par devise ») ; note « un bon par devise » si > 1 | idem | — |
| « Délai » (infobulle « Délai de livraison déclaré du fournisseur ») `jours` | `droite`, `unite: 'j'` | — |
| « Références » (infobulle « Matières que le calcul propose de commander chez lui ») ; « — » sans plan | idem | — |
| « Quantité » (infobulle « En kilos, le cuir, les franges et le ruban compris ») « {n} kg » | « Quantité (kg) » `unite` | unité dans l'en-tête |
| « Montant en devise » (infobulle « Au prix du catalogue, avant confirmation par le fournisseur ») une ligne par devise | `Montant` par devise, jamais additionnées | — |
| « Contre-valeur MAD » (infobulle « Au cours du jour de chaque devise ») | `droite`, `unite: 'MAD'` | — |
| « Part » (infobulle « Part de ce fournisseur dans le budget du plan d'achat ») | idem | — |
| « Urgence » : « 🚨 Urgent · 2 rupt. · 1 crit. · 3 urg. », « 📋 À grouper », « 📝 Standard » ; note « rien à commander » ; règle serveur (`moteur.py:1728-1738`) | `Badge` « Urgent · n rupt. · n crit. · n urg. » (rupture), « À grouper » (attention), « Standard » (neutre) | sans émoticône (REGLES § 5) |
| Bouton « Préparer la commande » (principal si plan) | `Bouton` sur la ligne | — |
| Ligne cliquable (infobulle « Préparer la commande ») | `DataTable` ligne `lien` | — |
| Pied (si > 1 fournisseur avec plan) « {n} fournisseurs à solliciter » · Σ réf. · Σ kg · Σ MAD | pied de totaux (lignes visibles) | — |
| Vide « Aucun fournisseur ne correspond. » / « Rien à commander aujourd'hui. » | `Vide` mêmes textes | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne ou « Préparer la commande » (infobulle « Ouvre la proposition : vous cochez, ajustez, et le bon est créé en brouillon ») | D, A | — (→ `/plan-achat/preparer/:fournisseurId`) | — | adresse stable de la préparation |

### 4.3 Plan d'achat › Références à commander — `/plan-achat?onglet=references`

Gestion MP : onglet « Références à commander » (`PlanAchat.tsx:230-355`) → PRO : `DataTable`, `Badge`, `KgEtMetres`, `Montant`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Références à commander, triées par montant pondéré par la classe ABC (× 3 en A, × 2 en B) » + infobulle (« Toutes les références que le budget compte. Une ligne au statut OK est une commande de réapprovisionnement… ») | `Carte` + infobulle identiques | — |
| Recherche : référence, nature, désignation, fournisseur, statut, tier, « classe A/B/C », risque, action | `Colonne.recherche` mêmes champs | — |
| — | `Filtres` liés : Statut, Priorité, Classe ABC, Fournisseur — transmis aussi à l'export (`GET export/plan-achat?onglet=references&statut=&priorite=&abc=&fournisseur=`) | ajout (A1) |
| « Référence » + note « nature · désignation » ; infobulle = `relance` du serveur | `lien` → `/stock/matieres/:id` ; infobulle gardée | lien fiche matière |
| « Fournisseur » bouton-lien (infobulle « Préparer la commande de ce fournisseur ») | `lien` → `/plan-achat/preparer/:fournisseurId` | — |
| « ABC » (infobulle « Classe ABC : A, les matières qui pèsent le plus dans la consommation en valeur ») | idem | — |
| « Statut » étiquette (« 🔴 RUPTURE », CRITIQUE, URGENT, ATTENTION, « 🟢 OK ») ; note « réapprovisionnement » si OK ; teinte `tonStatut` | `Badge` (table unique) sans émoticône : le serveur rend le code (`RUPTURE`… `NON_CONSOMMEE`), l'écran le traduit (`cleStock`) ; `relance` sans émoji | codes au serveur (RESTES3) |
| « Disponible (kg) », « Commandé (kg) », « Couverture » (`jours`, « — ») ; infobulles gardées | idem, lus dans `GET plan-achat` | — |
| « À commander » « {kg} kg » ; notes palettes (`quantiteEnUnites`), « soit {n} ml » (facturé au mètre) ou « ≈ N ml », « déjà en préparation : {kg} kg (brouillon n° 7, BC-…) » | « À commander (kg) » ; `KgEtMetres` ; note « déjà en préparation : {kg} kg (Brouillon, BC-…) » + `LienDocument` | unité dans l'en-tête (anom. 4.14) ; plus de « brouillon n° 7 » (REGLES : « Brouillon ») |
| « Palettes » + note « entière(s) » ; « — » si 0 | idem | — |
| « Montant » (infobulle « Au prix du catalogue ; en MAD au cours du jour ») ; note MAD si devise ≠ MAD | `Montant` | — |
| « Priorité · action » : tier (« 🔥 TIER 1 »…), note action, note risque | `Badge` « Tier 1 »… ; notes gardées | sans émoticône |
| Ligne non cliquable ; tri serveur (montant MAD × 3 A, × 2 B) ; pas de pied | tri serveur par défaut, en-têtes triables ; pied « {n} références · Σ kg · Σ MAD » | ajout du pied |
| Vide « Aucune référence ne correspond. » / « Rien à commander aujourd'hui. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic sur le nom du fournisseur | D, A | — (→ `/plan-achat/preparer/:fournisseurId`) | — | — |

### 4.4 Préparer une commande — `/plan-achat/preparer/:fournisseurId` (et `/commandes/nouvelle?fournisseur=ID`)

Gestion MP : fenêtre « Préparer une commande — {fournisseur} » (`PreparationCommande.tsx`, `Dialogue tresLarge sale`) → PRO : `Fenetre({taille: tresLarge, sale})` sur la page appelante, `Indicateurs`, `Form` (`DateChamp`, `Nombre`, `Selecteur`, `SelecteurMatiere`, `Zone`, `Quantite`), `DataTable` de saisie, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /plan-achat/fournisseur/{nom}` ; 404 « fournisseur inconnu : « {nom} » » ; `useFournisseurs`, `useArticles`, `useDevises` | `GET plan-achat/fournisseurs/{id}` (lignes, `unites_possibles` déjà filtrées, prix indicatif, en préparation) ; 404 « Fournisseur inconnu. » | par id, pas par nom |
| Titre « Préparer une commande — {fournisseur} » + note « {pays} · {contact} · {email} · délai {n} j · calcul au {date} » + infobulle (quantités du calcul…) | titre de `Fenetre` + `Note` identiques | — |
| Chargement « … les quantités suggérées… » ; erreur | `Chargement`, `Erreur` | — |
| Départ : une ligne par suggestion présente au catalogue ; unité = `unite_commande` si possible, sinon dernière unité, sinon kg ; quantité suggérée (au kilo arrondie au kg supérieur) ; tout coché ; note « déjà en préparation : {kg} kg (brouillon n° 7), déduits » | même règle, calculée par le serveur (`ligne.depart`) | note « (Brouillon) » |
| KPI « Lignes retenues » « {retenues} / {total} » | `Kpi` | — |
| KPI « Quantité totale » « {Σ} kg » | `Kpi` | — |
| KPI « Palettes » `nombre(Σ/contenance,1)` ; détail « {n,nn} conteneur(s) » ou « palettes / conteneur ? » ; attention si > 0,05 palette libre | `Kpi` | — |
| KPI « Montant indicatif » `montants(par devise)` ; infobulle « Au prix du catalogue : le fournisseur confirmera le sien » ; détail « ≈ {MAD} au cours du jour » / « au prix du catalogue » | `Kpi` + `Montant` | — |
| « Livraison prévue » (date, min aujourd'hui) ; aide « vide : date d'envoi + {délai} j (délai du fournisseur) » | `DateChamp` (min = aujourd'hui serveur) | — |
| « Palettes par conteneur » (placeholder « ex. 20 »), ni `sale` ni envoyée (anom. 4.19) | `Nombre` libellé « Palettes par conteneur (aide de calcul) », retenu par poste et par fournisseur (stockage local) | n'est plus perdu à la fermeture ; reste hors du bon |
| « Ajouter une matière de ce fournisseur » (`ChoixRecherche` 340 px ; matières actives du fournisseur absentes ; « {réf} — {désignation} », détail devise ; placeholder « Référence, couleur, titrage… ») ; ligne « ajoutée » (unité = dernière possible, qté = 1 unité ou minimum, prix catalogue) | `SelecteurMatiere` (filtre fournisseur imposé) | — |
| « Remarques au fournisseur » (textarea 2 l., pleine largeur ; aide « imprimées sur le bon, qui est en anglais : les écrire en anglais (ex. « Deliver in one shipment ») » ; ≤ 2000) | `Zone` pleine largeur, même aide ; champ `observations` de l'API (`CommandeCreation`, lot D3 ; et non `remarques_fournisseur`) | case à part (A23) ; vocabulaire (anom. 4.11) |
| Message « Il reste la place de **{n} palette(s)** dans le dernier conteneur ({N} au total). » | `Note` « {N}ᵉ conteneur : {p} palette(s) sur {C} — il manque **{n} palette(s)** pour le remplir. » ; plein à 0,05 palette près ; une ligne en palettes compte le nombre tapé (12/10/2026, Mohamed) | libellé plus clair ; plus de conteneur fantôme |
| Col. « Cmd. » (case ; ligne décochée à 50 %) | colonne case à cocher | — |
| « Référence » + note « nature · désignation · devise » | idem | — |
| « Statut · couverture » (étiquette ou « ajoutée » ; note « classe A · couvre 45 j ») | `Badge` | — |
| « Stock projeté (kg) », « Conso / mois (kg) » | idem | — |
| « Suggéré (kg) » (infobulle « La quantité que le calcul propose, et la même dans l'unité de commande ») ; notes unités et « déjà en préparation » | idem | — |
| « Commandé en » : « kg », « Bobine (2,5 kg) », « Palette (862,4 kg) », « Fût (200 kg) »… ; changer garde les kilos | `Selecteur` sur `unites_possibles` du serveur (jamais « ml ») | anom. 4.15 |
| « Quantité » (unités, 2 déc. ; pas 1 ou 10) | `Quantite` (unités → kg, dit l'arrondi) | — |
| « Soit (kg) » (1 déc.) ; note mètres ; note orange « sous le minimum ({min} kg) » / « {unité} entamée » | `KgEtMetres` + `Note` d'avertissement | — |
| « Écart » (infobulle « Ce que vous commandez face à la suggestion du calcul ») : « non commandée » / « hors calcul » / « — » / « suggestion » (< 0,5 %) / `signe` (ok ≤ 10 %, attention au-dessus, critique en dessous) | `Badge` mêmes règles | — |
| « Montant indicatif » (infobulle « Au prix du catalogue, avant confirmation par le fournisseur ») + note « {prix} {devise} / kg » ; « — » sans prix | `Montant` | — |
| Bouton « Retirer » (lignes ajoutées) | `Bouton` danger sur la ligne | — |
| Vide « Rien à commander chez ce fournisseur selon le calcul. Ajoutez ci-dessous les matières que vous voulez commander quand même. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Cocher / décocher une ligne | D, A | — (local) | — | — |
| Choisir « Commandé en » / saisir « Quantité » | D, A | — (local) | avertissement minimum / unité entamée, non bloquant | — |
| « Ajouter une matière de ce fournisseur » | D, A | `GET matieres?fournisseur=ID&actives=1` | — | — |
| « Retirer » (ligne ajoutée) | D, A | — (local) | — | — |
| « Arrondir au conditionnement » (infobulle « Chaque quantité monte au conditionnement entier suivant ») | D, A | — (local) | — | — |
| « Revenir à la suggestion » (infobulle « Retrouver les quantités calculées, sans les lignes ajoutées ») | D, A | — (local) | — | — |
| Case « Envoyer sans les prix (le fournisseur les annonce) » / « Envoyer avec nos prix du catalogue, « à confirmer » » (`sans_prix`) | — | — | — | **supprimée** (anom. 4.2) : le bon ne porte jamais de prix (A2, A22) ; les lignes naissent `prix = NULL` (à confirmer) ; le montant estimé lit le catalogue ; « Reprendre les prix du catalogue » reste dans le volet Prix |
| « Annuler » (si saisie « Abandonner la préparation ? » · « Oui, abandonner ») | D, A | — | garde `sale` de `Fenetre` | retour à `/plan-achat` (ou `/commandes`) avec filtres |
| « Créer le bon en brouillon · {Σ} kg » / « Créer {n} bons (un par devise : EUR, USD) · {Σ} kg » (« Création… ») | D, A | `POST commandes` `{fournisseur_id, date_livraison_prevue|null, prix_catalogue_a_confirmer, observations, lignes:[{matiere_id, quantite, unite_achat, contenance}]}` → liste des bons créés (un par devise, même transaction) | `Bouton({manque: ["Cochez au moins une ligne"], occupe})` ; refus serveur gardés : « Fournisseur inconnu. », « Matière inconnue dans la commande. », « « {réf} » n'est pas fournie par ce fournisseur. », « … figure deux fois : regrouper les quantités. », « … commandée en kg, la contenance vaut 1. », « … ne se commande pas en « {unité} » … », « … une {unité} contient {x} kg, pas {y} … », quantité > 0 | raison du grisé dite (anom. 4.9) ; succès : toast + `LienDocument` (4.1) ou fiche ouverte `/commandes/:id` (un bon) |

### 4.5 Commandes (liste) › Brouillons · À approuver · Envoyées · Confirmées · Soldées / annulées — `/commandes?onglet=brouillon|a_approuver|envoyee|confirmee|clos&filtre=retard&q=`

Gestion MP : « Commandes » `/commandes` (`Commandes.tsx`) → PRO : `/commandes` (`Page`, `EnTete`, `Indicateurs`/`Kpi`, `Onglets`, `Filtres`, `Recherche`, `DataTable` dans `Cadre`, `ExportExcel`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /commandes` (tout, id décroissant) | `GET commandes?…` (résumés, chargement groupé) | — |
| Chargement « … les commandes… » ; erreur | `Chargement`, `Erreur` | — |
| Titre « Commandes » ; sous-titre « Un bon part sans prix, le fournisseur les confirme, puis il est reçu. Tant que rien n'est reçu, il se modifie. » ; actions export + « Nouvelle commande » | `EnTete` (fil « Achats › Commandes », aide) | — |
| Bandeau succès de page (suppression « {numéro ou Brouillon} supprimé. », création 1 ou n bons), effacé au changement d'onglet | `Messages` (toasts) | — |
| KPI « Bons ouverts » (hors soldés/annulés) ; détail « {b} brouillon(s) · {a} à approuver » ; D : infobulle « Votre accord est attendu », teinte urgent ; A : « En attente de la direction » | `Kpi({lien: '/commandes?onglet=a_approuver'})`, textes par rôle gardés | clic mène à l'onglet |
| KPI « Montant engagé » `montantCourt(Σ montant_estime_mad envoyés+confirmés)` ; détail « {n} bon(s) partis » ; infobulle « … dont {k} bon(s) estimé(s) au prix du catalogue, prix à confirmer » | `Kpi({formule})` | — |
| KPI « Reste à recevoir » `montantCourt(Σ reste_estime_mad)` ; détail « pas encore arrivé » | `Kpi` libellé « Reste à livrer (MAD) » | vocabulaire unique (anom. 4.11) |
| KPI « Prix à confirmer » (bons partis avec ≥ 1 prix non confirmé ; attention ; « bons partis ») | `Kpi({lien: '?onglet=envoyee'})` | — |
| KPI « En retard » (état contient « retard » ; critique/ok ; « date prévue dépassée ») | `Kpi({lien: '?filtre=retard'})` | — |
| KPI sur tous les bons, quels que soient filtre et recherche | idem, sous-titre de la rangée « tous les bons » | dit son périmètre |
| Onglets (compte = bons trouvés par la recherche) : « Brouillons » (aide « Pas encore partis, sans numéro : relire, imprimer, envoyer »), « À approuver » (« Au-delà du seuil : la direction approuve ou renvoie »), « Envoyées » (« Partis, prix pas encore tous confirmés »), « Confirmées » (« Prix confirmés : suivre l'expédition et l'arrivée »), « Soldées / annulées » (« Reçus, soldés ou annulés : « Rouvrir » remet en attente ») ; défaut = 1er onglet non vide | `Onglets` (compteur, libellé + infobulle = aide) ; même défaut | — |
| Note « {n} bon(s) trouvé(s), tous onglets » | `Note` | — |
| Case « en retard seulement » (infobulle « Livraison prévue ou ETA dépassée »), `?filtre=retard` | `Filtres` : interrupteur « En retard seulement » (`?filtre=retard`) + listes liées Fournisseur, Devise, État de livraison ; « Effacer les filtres » ; « N critère(s) » | A1 (anom. 4.13) |
| Recherche placeholder « N°, fournisseur, référence, conteneur… » : n° (ou « Brouillon »), fournisseur, pays, devise, état, statut, créé par, observations, conteneur, navire, « réf. désignation » des lignes | `Colonne.recherche` mêmes champs (+ remarques au fournisseur) | — |
| Col. « N° · date » (infobulle « La date du bon est celle de son envoi ») : n° ou « Brouillon » ; note date ou « daté à l'envoi » | `Badge` « Brouillon » / « À approuver » pour un bon sans numéro | anom. 4.12 |
| « Fournisseur » (nom ; note « {1re réf.} + {n−1} » ; infobulle toutes les références) | idem | — |
| « Quantité » (infobulle « En kilos, le cuir, les franges et le ruban compris ») | « Quantité (kg) » | unité dans l'en-tête |
| « Montant » : « prix à confirmer » + note « ≈ {estimé} » ou estimé + note « {n} prix à confirmer » | `Montant` + `Badge` | — |
| « Montant MAD » (infobulle « Au cours figé à la confirmation, sinon au cours du jour ; prix du catalogue tant que le prix n'est pas confirmé ») | idem | — |
| « Livré » `part` ou « — » | idem | — |
| « État de livraison » (infobulle « Où en est la livraison du bon ») ; note « pas envoyé » ; note « livrée le » / « dernière arrivée le » ; `tonLivraison` | `Badge` (table unique) : « Livré », « Soldé », « Soldé à la main », « Soldé sans livraison », « Annulé », « Reçu sous réserve », « En cours », « Partiel retard », « Attendu », « En retard » | sans émoticône ; « Soldé à la main » lu sur la colonne `solde_origine` |
| « Livraison prévue / ETA » ; note « ETA · {conteneur} » | idem | — |
| « Statut » (Brouillon, À approuver, Envoyée, Confirmée, Soldée/Annulée) ; note « renvoyé par la direction » | `Badge` ; note lue sur la dernière décision | — |
| Bouton « Saisir les prix » (infobulle « Ouvre le bon sur les prix du fournisseur ») ou « Ouvrir » (principal si à approuver) | `Bouton` sur la ligne | — |
| Ligne cliquable → fiche sur « Lignes et livraison » ; ordre id décroissant ; ni pied, ni tri, ni pagination | `lien` → `/commandes/:id` ; tri cliquable ; pied « {n} bons · Σ kg · Σ MAD » ; `Cadre` | ajout du pied |
| Vide : recherche « Aucun bon de cet onglet ne correspond (voir les autres onglets). » ; Brouillons « Aucun brouillon. Préparez un bon depuis le plan d'achat ou avec « Nouvelle commande ». » ; autres « Aucun bon ici. » | `Vide` mêmes textes | — |
| Liens entrants `versCommandes` `?onglet=&commande=ID`, `?filtre=retard`, `?ouvrir=ID` | `/commandes/:id`, `/commandes?filtre=retard` ; anciens liens redirigés | A5 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouvelle commande » | D, A | — (→ `/commandes/nouvelle`) | — | — |
| « Exporter en Excel » (`/export/commandes?onglet&q`) | D, A | `GET export/commandes?onglet=&q=&filtre=&fournisseur=&…` | — | filtre « en retard » et filtres liés transmis (anom. 4.13) |
| Case « en retard seulement » | D, A | `GET commandes?filtre=retard` | — | — |
| Clic ligne / « Ouvrir » | D, A | `GET commandes/{id}` | — | `/commandes/:id?onglet=lignes` |
| « Saisir les prix » | D, A | `GET commandes/{id}` | — | `/commandes/:id?onglet=prix` (anom. 4.18) |

### 4.6 Nouvelle commande — chez quel fournisseur ? — `/commandes/nouvelle`

Gestion MP : fenêtre « Nouvelle commande — chez quel fournisseur ? » (`ChoixFournisseurCommande.tsx`) → PRO : `Fenetre({taille: tresLarge})` sur `/commandes`, `DataTable` (colonnes de 4.2), `Recherche`, `Interrupteur`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `useFournisseurs` + `GET /plan-achat` | `GET plan-achat` (fournisseurs) + `GET fournisseurs` (actifs) | — |
| Texte « La préparation s'ouvre avec les quantités que le calcul suggère … on ne commande jamais sans arbitrer. » | `Note` identique | — |
| Recherche (placeholder « Nom, pays, contact, devise… » : nom, pays, contact, devises, urgence) | `Recherche` | — |
| Case « Montrer aussi les fournisseurs chez qui rien n'est à commander » ; défaut : actifs avec suggestion ; tri MAD décroissant puis nom | `Interrupteur` même libellé | — |
| Table des fournisseurs (devises = celles de la fiche) | colonnes de 4.2 | — |
| Vide « Aucun fournisseur ne correspond. » / « Rien n'est à commander aujourd'hui : cochez la case pour voir tous les fournisseurs. » | `Vide` | — |
| Chargement « … les fournisseurs et le plan d'achat… » ; erreur du plan | `Chargement`, `Erreur` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne / « Préparer la commande » | D, A | `GET plan-achat/fournisseurs/{id}` | — | → `/commandes/nouvelle?fournisseur=ID` (préparation 4.4 en fenêtre, pile) |
| Case « Montrer aussi… » | D, A | — (local) | — | — |
| « Fermer » | D, A | — | — | retour `/commandes` |

### 4.7 Fiche commande (titre, indicateurs, bandeaux, pied) — `/commandes/:id`

Gestion MP : fiche « Bon de commande {n° | (brouillon)} — {fournisseur} » (`DetailCommande.tsx`, `Dialogue tresLarge sale`) → PRO : `/commandes/:id?onglet=lignes|prix|expedition|receptions|approbation|pieces|historique` (`Fenetre({taille: tresLarge, sale})` sur la liste, `Indicateurs`, `Onglets`, `Bouton({blocages})`, `Confirmer`, `BoutonImprimer`), rôles D, A (approbation D).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données : la fiche relit le bon **dans la liste** `GET /commandes`, `useArticles`, `GET /pieces/commande/{id}` ; relecture sans écraser la saisie | `GET commandes/{id}` (lignes, versions partie, `decisions`, `blocages`, `fin_possible`, réceptions, nb pièces) ; relecture sans écraser la saisie | fiche complète en une lecture |
| Bon disparu : « Chargement… » puis « Ce bon n'existe plus. » | 404 → `Vide` « Ce bon n'existe plus. » ; `Chargement` honnête | — |
| Titre « Bon de commande {n°} — {fournisseur} » / « Bon de commande (brouillon) — … » | « Bon de commande BC-… — {fournisseur} » ; sans numéro : `Badge` « Brouillon » ou « À approuver » | anom. 4.12 |
| Étiquette statut + étiquette état de livraison (si parti) | `Badge` × 2 | — |
| Note « {pays} · envoyé le {date} | pas encore envoyé · créé par {nom} le {horodatage} · {devise} · approuvé par {nom} le {horodatage} » | `Note` ; « approuvé par » lu sur la dernière décision ; + « soldé à la main par {nom} le {date} » | colonnes réelles |
| KPI « Commandé » « {Σ} kg » ; « {n} ligne(s) » | `Kpi` | — |
| KPI « Reçu » ; « livré en entier le {date} » / « {x %} livré · dernière réception le {date} » / « {x %} livré » ; ok ≥ 98 %, attention si > 0 | `Kpi` | — |
| KPI « Montant estimé » / « Montant » ; infobulle « Prix confirmés, et prix du catalogue pour ceux qui restent à confirmer » ; détail « {n} prix à confirmer » / « prix confirmés » + « ≈ {MAD} » | `Kpi` + `Montant` | — |
| KPI « Arrivée prévue (ETA) » / « Livraison prévue » ; « conteneur {n°} » | `Kpi` | — |
| KPI « Cours figé » (devise ≠ MAD) « 1 USD = {cours} MAD » / « — » ; « à la confirmation du {date} » / « pas encore : cours du jour {taux} » | `Kpi` | — |
| Bandeau renvoi « **Renvoyé aux achats** par {nom} le {horodatage} : « {motif} ». » + (parti) « Le changement n'est pas accepté : le bon reste chez le fournisseur tel qu'il était parti. » / (brouillon) « Corrigez le bon, puis soumettez-le de nouveau — ou supprimez-le. » | `Note` (ton attention) lue sur la dernière décision `renvoi` ; même condition d'affichage | source = table des décisions |
| Bandeau à approuver : (parti) « Ce bon, déjà chez le fournisseur, a changé de montant (≈ {MAD}, seuil {seuil}) : » / (brouillon) « Ce bon dépasse le seuil d'approbation ({seuil}) : » + D « relisez-le, puis « Approuver et envoyer », ou « Renvoyer aux achats » avec un motif. » ; A parti « il attend l'accord de la direction. Ne confirmez pas le changement au fournisseur avant. » ; A brouillon « il attend l'accord de la direction avant de partir. » | `Note` (textes gardés, par rôle) | — |
| Bandeau (nouveau) raison sociale non réglée | `Note` « La raison sociale de l'usine n'est pas réglée (Réglages › Paramètres › Société) : elle manque en tête du bon. » | dit sur la fiche, plus seulement sur le document |
| Volets (état local, hors adresse) : « Lignes et livraison » (compte), « Prix du fournisseur » (« {n} à saisir »), « Suivi de l'expédition », « Réceptions » (compte), « Pièces jointes » (compte) | `Onglets` dans `?onglet=` : `lignes`, `prix`, `expedition`, `receptions`, `approbation` (nouveau, compte des décisions, présent dès une décision), `pieces`, `historique` (nouveau) | anom. 4.18 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer le bon » (infobulle « Ouvre le bon prêt à imprimer ou à enregistrer en PDF »), tous statuts | D, A | `GET documents/commandes/{id}/bon` (`BoutonImprimer`, nouvel onglet) | 404 « Commande introuvable. » | document 4.17 |
| « Excel pour le fournisseur » (infobulle « Le bon dans un classeur Excel, prêt à envoyer au fournisseur ») | D, A | `GET export/commandes/{id}/bon` | 404 « Bon de commande introuvable. » | même contenu que le document (4.18) |
| « Marquer comme envoyé » / « Envoyer, ou demander l'approbation » (infobulles « Le montant dépasse le seuil : le bon part d'abord à la direction » / « Le bon reçoit son numéro et sa date : il est parti chez le fournisseur ») | D, A | `POST commandes/{id}/envoyer` `{date}` | `Confirmer` : sous le seuil « Envoyé le [`DateChamp` défaut aujourd'hui, max aujourd'hui serveur, min après clôture] : le bon reçoit son numéro. » (ou « : le bon {n°} repart corrigé. ») · « Oui, il est envoyé » ; au-delà « ≈ {MAD} : au-delà du seuil de {seuil}, le bon attendra l'accord de la direction. » · « Oui, demander l'approbation » ; `Bouton({manque: ["Enregistrez d'abord vos modifications"], blocages})` : « Ce bon attend l'approbation de la direction. », « Ce bon est déjà parti. », « La livraison prévue ({date}) est déjà passée : la corriger, ou la vider… », « … précède l'envoi du bon… », `date_permise` (trop ancienne, futur, période close) | refus annoncés avant le clic (anom. 4.10) ; la demande écrit une décision `demande` ; succès « Bon envoyé : il porte désormais le n° {n°}, daté du {date}. Les prix seront à confirmer au retour du fournisseur. » / « Bon soumis à la direction : il partira à son approbation. » ; notification D |
| « Approuver et envoyer » (infobulle « Le bon reçoit son numéro et part chez le fournisseur ») | D | `POST commandes/{id}/approuver` `{date}` | `Confirmer` « Approuver {montant estimé} chez {fournisseur}, envoyé le [`DateChamp`, défaut aujourd'hui] ? » · « Oui, approuver et envoyer » ; blocages « Ce bon n'attend pas d'approbation. », date close | **date réelle d'envoi** ; décision `approbation` (par, le, montant MAD, cours, date d'envoi) ; succès « Bon approuvé : il a reçu son numéro et est marqué comme envoyé. Les achats l'impriment et le transmettent. » ; notification A |
| « Renvoyer aux achats… » (infobulles « Le changement n'est pas accepté : le bon revient à sa version partie, avec votre motif » / « Le bon redevient un brouillon, avec votre motif ») | D | `POST commandes/{id}/renvoyer` `{motif}` | `Confirmer` motif **exigé** (« Motif du renvoi aux achats », aide « les achats le liront sur le bon », placeholder « ex. couper en deux livraisons, attendre la baisse annoncée… », 3-500 car.) · « Non » · « Oui, renvoyer aux achats » `manque` « Motif : 3 caractères au moins » ; blocages « Seul un bon qui attend l'approbation se renvoie aux achats. », « Le bon {n°} est parti, mais sa version d'alors n'est pas connue … » (bons repris seulement) | décision `renvoi` (+ `version_retablie` si parti) ; raison du grisé dite (anom. 4.9) ; notification A |
| « Supprimer le bon » (infobulle « Un bon qui n'est pas parti se supprime : il n'a pas encore de numéro ») | D, A | `DELETE commandes/{id}` | `Confirmer` « Supprimer définitivement ce brouillon ? » · « Oui, supprimer » ; blocages « Ce bon a des réceptions : le solder plutôt que le supprimer. », « Le bon {n°} est parti chez le fournisseur : l'annuler plutôt que le supprimer … » | toast « Brouillon supprimé. » ; retour `/commandes?onglet=brouillon` |
| « Solder (ne plus attendre le reste) » / « Annuler la commande » (infobulles « Solder le bon : on n'attend plus le reste à livrer » / « Annuler la commande : rien n'a été reçu, le bon garde son numéro ») | D, A | `POST commandes/{id}/solder` | `Confirmer` « On n'attend plus le reste ({kg} kg) : il sort des quantités commandées. » · « Oui, solder » / « Rien n'a été reçu : le bon sera annulé (il garde son numéro). » · « Oui, annuler la commande » ; blocages « Ce bon est déjà clos. », « Le bon {n°} attend l'approbation de la direction … », « Ce bon n'est pas parti : il se supprime, il ne se solde pas. » | libellé, infobulle et question lus sur un seul champ serveur `fin_possible` (`a_ete_livre`) (anom. 4.4) ; écrit `solde_origine`, `solde_par`, `solde_le` ; toasts « Bon soldé. » / « Commande annulée. » |
| « Rouvrir le bon » (infobulle « Le bon attend de nouveau ce qui reste à livrer ») | D, A | `POST commandes/{id}/rouvrir` | `Confirmer` « Rouvrir ce bon ? Le reste redevient attendu. » · « Oui, rouvrir » ; blocage « Ce bon n'est pas clos. » | efface `solde_origine` ; au-delà de l'approuvé → « À approuver » (décision `demande`) ; toast « Bon rouvert : le reste est de nouveau attendu. » |
| « Fermer » | D, A | — | garde `sale` (« Des modifications ne sont pas enregistrées. Les abandonner ? ») | retour `/commandes` (onglet, filtres, défilement gardés) |

### 4.8 Fiche commande › Lignes et livraison — `/commandes/:id?onglet=lignes`

Gestion MP : volet « Lignes et livraison » → PRO : `DataTable` de saisie, `DateChamp`, `Saisie`, `SelecteurMatiere`, `Quantite`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `modifiable` = ni soldé ni annulé **et** aucune ligne nommée par une réception (même brouillon/annulée) | champ serveur `modifiable` + `blocages` | — |
| Parti : bandeau « Ce bon est déjà parti. Vous pouvez encore le corriger (rien n'est reçu) : pensez à renvoyer le bon réimprimé au fournisseur. » | `Note` | — |
| « Livraison prévue » (160 px) ; aides « figée avec les prix : une nouvelle date va dans l'ETA » (grisé), « promise par le fournisseur », « vide : date d'envoi + délai du fournisseur » ; min = date du bon si parti | `DateChamp` (bornes serveur) ; vider = `null` réellement pris en compte (recalcul envoi + délai) ; grisé avec raison « figée avec les prix » / « date promise passée : elle ne se repousse plus » | anom. 4.1, 4.10 |
| « Remarques au fournisseur (imprimées sur le bon, en anglais) » (280 px) | `Zone` « Remarques au fournisseur » (pleine largeur) | même libellé partout (anom. 4.11) |
| « Ajouter une matière ({devise}) » (infobulle « Seules les matières de ce fournisseur, dans la devise du bon ») | `SelecteurMatiere` (fournisseur + devise imposés) | — |
| Non modifiable : clos « Ce bon est clos : il ne se modifie plus. « Rouvrir » le remet en attente de livraison. » ; livré « Ce bon a commencé à être livré : ses lignes sont figées. Pour un complément, préparez un autre bon ; s'il ne viendra rien de plus, soldez-le. » + « Observations : {remarques} » | `Note` ; « Remarques au fournisseur : {texte} » | vocabulaire (anom. 4.11) |
| Col. « Référence » + désignation | idem, `lien` → `/stock/matieres/:id` | lien |
| « Commandé en » (liste ou libellé ; une unité déjà sur le bon reste proposée) | `Selecteur` sur `unites_possibles` (+ l'unité du bon) | anom. 4.15 |
| « Quantité » (unités 2 déc.) | `Quantite` | — |
| « Soit (kg) » + mètres | `KgEtMetres` | — |
| « Reçu (kg) » (infobulle « Pesé aux réceptions validées, moins ce qui est reparti chez le fournisseur ») ; « {x %} » ; « dont {n} en quarantaine » (infobulle « Reçu sous réserve : le bon ne se solde qu'à sa libération ») | idem | — |
| « Reste à livrer (kg) » (infobulle « Commandé moins reçu ; un reliquat sous la tolérance compte pour complet ») ; « complet » ; « — » si clos | idem, `Badge` « complet » | — |
| « Prix / kg » confirmé ; note « {prix} à confirmer » (infobulle « Notre prix proposé, imprimé « à confirmer » ») ; ou « à confirmer » | confirmé : prix ; sinon `Badge` « à confirmer » + note « catalogue {prix} » | plus de prix « proposé imprimé » (case supprimée, anom. 4.2) |
| « Montant » (kg × prix confirmé, sinon « — ») | `Montant` | — |
| « Retirer » (grisé s'il reste une ligne, infobulle « Un bon garde au moins une ligne : supprimez le bon » / « Retirer cette matière du bon ») | `Bouton({manque})` | — |
| Pied « Total » · Σ kg · reçu · reste (vide si clos) · montant confirmé ou « — » | pied de totaux | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Saisir « Livraison prévue », « Remarques au fournisseur », « Commandé en », « Quantité » | D, A | — (local, `sale`) | bornes de `DateChamp` | — |
| « Ajouter une matière ({devise}) » | D, A | `GET matieres?fournisseur=&devise=` | — | — |
| « Retirer » (ligne) | D, A | — (local) | `manque` si une seule ligne | — |
| « Annuler les changements » | D, A | — | — | — |
| « Enregistrer » | D, A | `PUT commandes/{id}` `{version, date_livraison_prevue|null, observations, lignes:[{matiere_id, quantite, unite_achat, contenance}]}` | `Bouton({manque: ["Rien n'a changé"], occupe})` ; contrôle « Chaque ligne doit avoir une quantité : retirez celles qu'on ne commande plus. » ; refus « Ce bon est clos. », « Ce bon a déjà des réceptions … », « La livraison promise ({date}) est figée depuis la confirmation des prix … ETA … », « La livraison était promise pour le {date}, date passée … », « La livraison prévue ({date}) précède la date du bon ({date}). », « Ce bon est en {devise} : une matière d'une autre devise va sur un autre bon. » + refus de lignes de 4.4 | messages de succès gardés (« Bon modifié pendant que la direction le relisait : il revient en brouillon… », « Bon ramené à ce que la direction avait accepté … », « Bon modifié : il dépasse désormais le seuil d'approbation (≈ {MAD}) … », « Bon modifié. Il est déjà parti : réimprimez-le… », « Bon modifié. ») ; décisions `demande` / `version_retablie` écrites ; raison du grisé (anom. 4.9) |

### 4.9 Fiche commande › Prix du fournisseur — `/commandes/:id?onglet=prix`

Gestion MP : volet « Prix du fournisseur » → PRO : `DataTable` de saisie, `Prix`, `Interrupteur`, `DateChamp`, `Confirmer`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Ouvert à tout statut sauf annulé ; annulé « Ce bon est annulé : ses prix ne se confirment plus. » | ouvert aux bons **partis** non annulés ; brouillon / à approuver : `Note` « Le bon n'est pas encore parti : les prix se confirment au retour du fournisseur. » | le cours ne se fige plus avant l'envoi (anom. 4.8) |
| Texte « Recopiez les prix que le fournisseur a confirmés (proforma, courriel), **au kilo, en {devise}** … le cours de la devise se fige à la première confirmation. » | `Note` : « en {devise}, tels qu'il les annonce : au kilo, ou **au mètre** pour une matière dont la fiche est au mètre (le logiciel ramène au kilo par la densité ; l'équivalent au kilo s'affiche sous la saisie) » | U2 (audit n° 2 des achats) : une fiche au mètre se confirme au mètre, `unite: 'ml'` |
| Col. « Référence » + désignation ; « Quantité (kg) » + mètres ; « Prix catalogue / kg » (+ « soit {x} / ml ») ; « Prix confirmé / kg » (saisie « à saisir » + « soit {x} / ml ») ; « Écart » (« — » / « identique » < 0,5 % / `signe` attention hausse, ok baisse) ; « Montant » ; « État » (« confirmé » / « à confirmer » ; « par {nom} le {horodatage} ») | mêmes colonnes, « Prix catalogue » et « Prix confirmé » sans unité dans l'en-tête ; `Prix` (devise du bon, unité de la ligne : kg, ou ml pour une fiche au mètre — l'équivalent dans l'autre unité dessous, l'écart et le montant comptés au kilo) ; `Badge` | U2 (audit n° 2 des achats) |
| — | `DateChamp` « Livraison prévue confirmée par le fournisseur » (si la date n'est pas encore figée) | le serveur l'acceptait déjà (anom. 4.7) |
| Case « Mettre aussi à jour le prix du catalogue (conseillé : c'est le prix du moment) » (cochée) | `Interrupteur` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Saisir un prix confirmé | D, A | — (local, `sale`) | — | — |
| Case « Mettre aussi à jour le prix du catalogue » | D, A | — (local) | — | — |
| « Reprendre les prix du catalogue » (infobulle « Remplit les prix vides avec ceux du catalogue — à vérifier avant de confirmer ») | D, A | — (local) | `manque` « Le catalogue n'est pas dans la devise du bon » si devises différentes | bouton visible, grisé avec raison |
| « Confirmer ces prix » (infobulle « Enregistre les prix comme confirmés par le fournisseur ») | D, A | `POST commandes/{id}/prix` `{prix:[{ligne_id, prix}], mettre_a_jour_catalogue, date_livraison_prevue?}` | `Confirmer` « Confirmer {n} prix ? Le prix du catalogue changera pour : {réfs}. » / « Aucun prix du catalogue ne change. » / « Le catalogue garde ses prix. » · « Oui, confirmer » ; `manque` « Saisissez au moins un prix. » ; refus « Ce bon est annulé. », « Ligne étrangère à ce bon. », règles de date promise ; (nouveau) « Le bon n'est pas encore parti … » | succès « {n} prix confirmé(s), {k} reporté(s) au catalogue. Il reste {r} prix à confirmer. » ; règles serveur gardées (cours figé à la 1re confirmation, envoyée → confirmée, catalogue × densité, hausse ≤ 5 % sans direction) |

### 4.10 Fiche commande › Suivi de l'expédition — `/commandes/:id?onglet=expedition`

Gestion MP : volet « Suivi de l'expédition » → PRO : `Form` (`DateChamp`, `Saisie`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Non parti « Ce bon n'est pas encore parti : son expédition se suivra après l'envoi. » | `Note` | — |
| Texte « Les étapes du voyage, à remplir au fil des nouvelles … elle remplace la livraison prévue dans le calcul du stock projeté. » | `Note` | — |
| « Proforma reçue le » (« la facture provisoire du fournisseur »), « Acompte payé le » (« le virement d'avance, s'il y en a un »), « Embarquée le » (« date de départ (connaissement) »), « Arrivée prévue (ETA) » (« remplace la livraison prévue dans le calcul »), « Arrivée au port le » (« déchargement constaté »), « Dédouanée le » (« mainlevée de la douane »), « Arrivée à l'usine le » (« le camion à la bascule ») ; dates max aujourd'hui sauf ETA | `DateChamp` (max aujourd'hui serveur sauf ETA) mêmes aides | — |
| « N° de conteneur » (« ex. MSCU1234567 », ≤ 60), « Navire » (≤ 80) | `Saisie` (`maxLength` du schéma) | — |
| Message rouge « « {jalon} » ne se date pas dans le futur : seule l'ETA est une attente. » | impossible (borne du champ) ; `Blocages` si date serveur différente | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Saisir les jalons | D, A | — (local, `sale`) | bornes | — |
| « Annuler les changements » | D, A | — | — | — |
| « Enregistrer le suivi » | D, A | `PUT commandes/{id}/expedition` | `Bouton({manque: ["Rien n'a changé"]})` ; refus « Ce bon n'est pas encore parti : son expédition se suit après l'envoi. », « « {libellé} » ne se date pas dans le futur : c'est un fait constaté… » | raison du grisé (anom. 4.9) ; succès « Suivi enregistré. L'arrivée prévue (ETA) du {date} remplace la livraison prévue dans le calcul du stock. » / « Suivi de l'expédition enregistré. » |

### 4.11 Fiche commande › Réceptions — `/commandes/:id?onglet=receptions`

Gestion MP : volet « Réceptions » → PRO : `DataTable`, `LienDocument`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Col. « Réception » (n° ou « Brouillon »), « Arrivée », « Statut » (Validée ok / Annulée rupture / Brouillon attention), lien « Ouvrir la réception » | mêmes colonnes ; `Badge` ; `LienDocument` | + colonne « Pesé (kg) » imputé à ce bon |
| Ligne cliquable → `/receptions?ouvrir={id}` | `lien` → `/receptions/:id` | adresse stable |
| Vide « Rien n'est encore arrivé sur ce bon. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne / « Ouvrir la réception » | D, A | `GET receptions/{id}` | — | → `/receptions/:id` |

### 4.12 Fiche commande › Approbation (nouveau) — `/commandes/:id?onglet=approbation`

Gestion MP : aucune vue (renvoi et approbation lus sur des champs du bon, journal) → PRO : `DataTable` sur `commande_decision` (champ `decisions` de `GET commandes/{id}`), rôles D, A (lecture).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `montant_approuve`, version partie (`achats.py:201-243`), renvoi (`achats.py:133-146`) épars | table : « Le » (horodatage) · « Par » · « Décision » (`Badge` : Demande d'approbation, Approuvé et envoyé, Renvoyé aux achats, Version partie rétablie) · « Montant estimé (MAD) » (avant → après : `montant_avant`, `montant_apres`) · « Motif » ; ni le cours ni le seuil du moment (colonnes absentes de `commande_decision` : l'écran lit le cours du bon) | vraie table, ordre chronologique ; `decisions [{quand, par, decision, motif, montant_avant, montant_apres}]` (lot D3) |
| — | sous la table : « Version partie » (lignes et montant de référence) en `Definitions` | lisible sans le journal |
| — | Vide : onglet absent tant qu'aucune décision | — |

Gestes : aucun (lecture).

### 4.13 Fiche commande › Pièces jointes — `/commandes/:id?onglet=pieces`

Gestion MP : volet « Pièces jointes » (`PiecesJointes objet="commande"`) → PRO : `PiecesJointes`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Joindre un document… » (« Envoi… »), glisser-déposer, note « ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » | `PiecesJointes` mêmes textes | — |
| Colonnes Document, Genre, Taille, Par, Joint le, (Retirer) ; vide « Aucun document joint. » | idem | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Joindre un document… » / glisser | D, A | `POST pieces` `{objet: 'commande', id, fichier}` | refus « Type de fichier refusé : PDF, image, tableur, texte ou document seulement. », « Fichier trop lourd (20 Mo au plus). » ; écran « « {nom} » est trop lourd : 20 Mo au plus. » | — |
| Ouvrir un document | D, A | `GET pieces/{id}/fichier` | « Document inconnu. » | — |
| « Retirer » | D, A | `DELETE pieces/{id}` | `Confirmer` « Retirer ce document ? » · « Oui, retirer » | retrait tracé |

### 4.14 Fiche commande › Historique (nouveau) — `/commandes/:id?onglet=historique`

Gestion MP : journal des actions seulement (Réglages) → PRO : `Historique` (`GET historique/commande/{id}`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Entrées « création commande », modifications, envoi, prix, solde… au journal général | liste « Le · Par · Geste · Avant → Après » de ce bon | journal avant/après sur la fiche |

Gestes : aucun.

### 4.15 Réceptions (liste) › Brouillons · Validées · Annulées — `/receptions?onglet=brouillon|validee|annulee&q=`

Gestion MP : « Réceptions » `/receptions` (`Receptions.tsx`) → PRO : `/receptions` (`Page`, `EnTete`, `Onglets`, `Recherche`, `Filtres`, `DataTable`, `ExportExcel`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /receptions` (brouillons recalés à chaque lecture, sans écrire ; tout renvoyé, N+1) ; `GET /receptions/pesees`, `GET /reclamations` pour les comptes | `GET receptions?onglet=&q=` (résumés, chargement groupé, compteurs des 6 onglets dans la réponse) | perf. (R11) |
| Chargement « … les réceptions… » ; erreur | `Chargement`, `Erreur` | — |
| Titre « Réceptions » ; sous-titre « Le poste de pesée. C'est le poids pesé qui entre en stock, à la validation. » ; « Nouvelle réception » | `EnTete` (fil « Achats › Réceptions ») | — |
| Bandeau d'erreur « La réception {n°} vient d'être validée ou annulée : elle ne se corrige plus. » | toast rouge (même texte) | — |
| Onglets « Brouillons », « Validées », « Annulées » (comptes suivant la recherche), « Réclamations ouvertes » / « Réclamations » (compte ouvertes), « Poids des bobines » (sans compte), « Archive des pesées » (compte lignes) ; défaut Brouillons s'il y en a, sinon Validées | `Onglets` `?onglet=brouillon|validee|annulee|reclamations|bobines|pesees` mêmes règles | — |
| Titres de carte + infobulles : Brouillons « Pas encore entrées en stock ni numérotées : corriger, puis valider » ; Validées « Entrées en stock : étiquettes, facture, annulation » ; Annulées « Annulées : leurs entrées ont été contre-passées » | `Carte` mêmes textes | — |
| Note « {n} trouvée(s), tous onglets » ; recherche « N°, fournisseur, BL, facture, bon, lot… » (n°, fournisseur, BL, facture, créé par, contrôlé par, observations, n° des bons, « réf. désignation lot ») | `Recherche`, `Colonne.recherche` | — |
| — | `Filtres` liés : Fournisseur, Hors commande / sur bon, Facture (avec / « à compléter »), Qualité (avec réserve / refus) | ajout (A1) |
| Col. « N° » (REC-… ou « Brouillon ») ; « Arrivée » ; « Fournisseur » + note « par {créé par} · contrôlé par {nom} » ; « Bon(s) de commande » (ou « hors commande ») ; « N° du BL » ; « Facture » (« à compléter ») ; « Lignes » ; « Pesé (kg) » (hors refus) ; « Statut » (+ « {n} point(s) à régler », infobulle = blocages) | mêmes colonnes ; « Bon(s) de commande » en `LienDocument` ; `Badge` ; blocages lus sur le champ `blocages` | — |
| Bouton de ligne : brouillon « Corriger » ; validée « Étiquettes » (grisé sans lot, infobulle « Les étiquettes QR des lots de cette réception ») ; « Ouvrir / valider » (brouillon) ou « Ouvrir » | `Bouton` sur la ligne | — |
| Ligne cliquable → fiche | `lien` → `/receptions/:id` | — |
| — | pied « {n} réceptions · Σ pesé » | ajout |
| Vide : recherche « Aucune réception de cet onglet ne correspond (voir les autres onglets). » ; Brouillons « Aucun brouillon en attente. Un camion arrive ? « Nouvelle réception ». » ; autres « Aucune réception ici. » | `Vide` | — |
| Après enregistrement : onglet Brouillons, fiche ouverte, « Réception enregistrée en brouillon. Relisez-la puis validez-la … » / « Le camion portait {n} devises : {n} réceptions enregistrées en brouillon (EUR, USD), chacune avec sa facture. Relisez-les puis validez-les. » | toast + `/receptions/:id` (1re créée) | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouvelle réception » | D, A | — (→ `/receptions/nouvelle`) | — | — |
| « Corriger » (relit la liste ; refus si plus brouillon) | D, A | `GET receptions/{id}` | toast « La réception {n°} vient d'être validée ou annulée : elle ne se corrige plus. » | → `/receptions/nouvelle?brouillon=ID` |
| « Étiquettes » | D, A | `GET documents/etiquettes?lots=1,2` | `manque` « Aucun lot (tout refusé) » | raison du grisé |
| « Ouvrir / valider » / « Ouvrir » / clic ligne | D, A | `GET receptions/{id}` | — | → `/receptions/:id` |
| « Exporter en Excel » | D, A | `GET export/receptions?onglet=&q=&…filtres` | — | filtres transmis (4.19) |

### 4.16 Saisie de réception — `/receptions/nouvelle` (et `?brouillon=ID` pour « Corriger la réception »)

Gestion MP : fenêtre « Nouvelle réception » / « Corriger la réception — {n° | Brouillon} » (`SaisieReception.tsx`, `Dialogue tresLarge sale`) → PRO : `Fenetre({taille: tresLarge, sale})` sur `/receptions`, `Form`, `Selecteur`, `SelecteurMatiere`, `DateChamp`, `Nombre`, `Prix`, `Segments`, `DataTable` de saisie, `Blocages`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `useFournisseurs`, `useArticles`, `useCommandes`, `useMagasins`, `useDevises`, `useTolerances` (`GET /parametres` : écart pesée 2 %, poids bobine 5 %, excédent 10 %) | `GET fournisseurs`, `GET commandes?ouvertes=1&fournisseur=`, `GET magasins`, `GET devises`, `GET parametres` (A lecture : tolérances) | — |
| Mode d'emploi en `details` (6 points ; ouvert la 1re fois, `localStorage` « gestion-mp.aide-reception ») | `Note` repliable alimentée par `aide.json#reception-saisie` (état replié par poste) | une seule source d'aide (A7) |
| « N° du bon de commande » (aide « le chauffeur l'apporte : il choisit le fournisseur et coche le bon ») : bons ouverts numérotés, envoyée/confirmée/à approuver, reste > 0 ; « {n°} — {fournisseur} », détail « {kg} kg à livrer » ; placeholder « ou taper le n° du bon… » | `Selecteur` (340 px) | un bon « À approuver » est proposé mais sa ligne porte le blocage « attend l'approbation » (A8) |
| Changer de fournisseur par le bon : « Le bon {n°} est de {fournisseur} : passer à ce fournisseur efface les {n} ligne(s) déjà là, dont {k} saisie(s). Continuer ? » · « Non » · « Oui, changer de fournisseur » | `Confirmer` même texte | — |
| « Fournisseur » (actifs ou l'actuel ; détail pays ; « Taper le nom du fournisseur… ») ; changement : « Changer de fournisseur efface les {n} ligne(s) de la réception, dont {k} déjà saisie(s) (lot, pesée). Continuer ? » · « Oui, changer de fournisseur » ; un seul bon ouvert → ses lignes se chargent | `Selecteur` + `Confirmer` | — |
| « Date d'arrivée » (défaut, max aujourd'hui) | `DateChamp` (max aujourd'hui serveur, min après clôture) | — |
| « N° du BL » (« bon de livraison ») ; « Contrôlé par » (« au quai », ≤ 80) ; « Observations » (« état du camion, retard… ») | `Saisie` | — |
| Facture (`details` ; résumé « n° {n} · {montant} {devise} · échéance {date} » ou « facultative ici : elle se complète aussi après la validation ») : « N° de facture », « Date de facture » (sans max, anom. 4.16), « Montant de la facture », « Devise de la facture » (aide multi-devises), « Échéance » (min date ; « proposée : date de facture + {n} j » / « le délai de paiement du fournisseur n'est pas réglé » ; suit tant que non saisie) | `Carte` repliable ; `DateChamp` date de facture **max aujourd'hui** ; autres champs grisés « sans n° » avec raison | anom. 4.16 |
| « Bons de commande dans ce camion » : case par bon « {n°} · {n} ligne(s) à livrer · {x %} déjà reçu » ; « {n°} (plus rien à livrer) » ; aucun : note « Aucun bon envoyé n'attend de livraison chez ce fournisseur : ajoutez les matières hors commande. » (infobulle « Un bon encore en brouillon doit d'abord être marqué comme envoyé ») | `Puces` cochables, passent à la ligne | — |
| Décocher un bon saisi : « Décocher le bon {n°} retire ses {n} ligne(s), dont {k} déjà saisie(s). Continuer ? » · « Oui, retirer ce bon » | `Confirmer` | — |
| Avertissement « Ce camion porte deux devises ({liste}) : deux réceptions seront enregistrées, une par devise, chacune avec sa facture. » | `Note` (attention) | — |
| « Ajouter une matière hors commande » (infobulle « Une livraison sans bon, un échantillon, un complément ») : actives, celles du fournisseur d'abord ; prix = catalogue si même devise, sinon 0 ; devise du fournisseur | `SelecteurMatiere` | — |
| Col. « Référence · bon » (note « bon {n°} » / « hors commande ») | idem | — |
| « Lot du fournisseur » (placeholder « n° de lot ») + lien « Lot interne » (écrit « LOT INTERNE ») | `Saisie` + `Interrupteur` « Lot interne » (case de la ligne ; numéroté à la validation) | contrat : plus de `LOT INTERNE` en texte |
| « Reste à livrer (kg) » (+ « déjà reçu {kg} » ; note rouge « excédent refusé » ; règle pesé > max(0, commandé − reçu) + commandé × excédent) | idem ; excédent calculé **tous lots de la ligne de bon ensemble**, comme le serveur | anom. 4.6 |
| — | bouton de ligne « + un autre lot » : duplique la ligne de bon pour un second lot | deux lots d'une ligne de bon (anom. 4.6) |
| « Annoncé BL (kg) » | `Nombre` | — |
| « Pesé (kg) » (longue infobulle « Le poids relevé à la bascule… ») ; note mètres ; `signe` (critique au-delà) + « ±{kg} kg » (« Pesé moins annoncé BL (à défaut, moins le reste à livrer) ») ; attendu = BL, sinon reste seulement si pesé ≥ reste × (1 − tol.) | `Nombre` + `KgEtMetres` + `Badge` ; même règle (R13r) | — |
| « Palettes » (+ « × {n} bob. » ; « — » si catalogue muet, infobulle) | `Nombre` | — |
| « Bobines en plus · kg / bobine » (« = {n} bobines » ; `Badge` « {kg} kg » attention > 5 % ; « catalogue {x} kg ») | `Nombre` + `Badge` | — |
| « Prix / kg » : bon confirmé = prix (« {devise} · confirmé ») non modifiable ; sinon saisie (« prix ») + « {devise} / kg » ou liste des devises (hors commande) | `Prix` (devise imposée ou `Selecteur` de devise hors commande) | — |
| « Magasin » (« — choisir — » ; hors Quarantaine ; réserve → code quarantaine ; refusé « n'entre pas » ; défaut 1er magasin de rangement) | `Selecteur` | — |
| « Qualité » Conforme / Sous réserve / Refusé (infobulle) | `Segments` | — |
| « Observations » (« motif… » hors conforme) | `Saisie` | — |
| « × » (infobulle « Retirer cette ligne (absente du camion) ») ; saisie : « Retirer « {réf} » (lot {n}) déjà saisie ? Elle reste due sur le bon. » · « Oui, retirer la ligne » | `Bouton` + `Confirmer` | — |
| Vide « Cochez un bon de commande ci-dessus, ou ajoutez une matière hors commande. » ; pied « {n} ligne(s) » · Σ BL · Σ pesé (hors refus) · « {n} écart(s) de pesée au-delà de 2 % : vérifiez la bascule et le BL, notez-le en observation. » | `Vide` ; pied de totaux ; `Note` | — |
| Pied : note « Brouillon saisi par {nom}, arrivée du {date}. Enregistrer ne fait rien entrer en stock : la validation viendra ensuite. » | `Fenetre` `pied` | — |
| — | `Blocages` « sera refusé à la validation : … » (calculés comme le serveur : lot manquant, pesée nulle, magasin, excédent, inventaire en cours, bon non parti/annulé/à approuver, date) | annoncé dès la saisie (A8) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Choisir « N° du bon de commande » | D, A | `GET commandes?ouvertes=1` | `Confirmer` si changement de fournisseur | — |
| Choisir « Fournisseur » | D, A | `GET commandes?ouvertes=1&fournisseur=` | `Confirmer` si lignes saisies | — |
| Cocher / décocher un bon du camion | D, A | — (local) | `Confirmer` au décochage d'un bon saisi | — |
| « Ajouter une matière hors commande » | D, A | `GET matieres` | — | — |
| « Lot interne » | D, A | — (local) | — | case, plus de texte « LOT INTERNE » |
| « + un autre lot » (nouveau) | D, A | — (local) | — | anom. 4.6 |
| « × » (retirer une ligne) | D, A | — (local) | `Confirmer` si saisie | — |
| Saisir facture, pesées, palettes, bobines, prix, magasin, qualité, observations | D, A | — (local, `sale`) | bornes | — |
| « Annuler » (si saisie « Abandonner la saisie ? » · « Oui, abandonner ») | D, A | — | garde `sale` | — |
| « Enregistrer le brouillon » / « Enregistrer les corrections » | D, A | nouvelle : `POST receptions` `{date, fournisseur_id, numero_bl, controle_par, observations, factures:{"EUR": {numero, date, montant, echeance}, …} (dictionnaire par devise, API-PRO 169), lignes:[{commande_ligne_id, matiere_id, lot_numero, lot_interne, quantite_bl, quantite_pesee, nb_palettes, bobines_en_plus, magasin_id, qualite, observations, prix|null, devise}]}` → **liste** des réceptions créées (une par devise, une transaction) ; correction : `PUT receptions/{id}` même corps + `version`, **une seule devise** (422 « Une réception ne mêle pas deux devises… ») → la fiche | `Bouton({manque: ["Choisissez d'abord le fournisseur, ou tapez le n° du bon.", "Ajoutez au moins une ligne : cochez un bon de commande, ou ajoutez une matière hors commande."]})` ; « Une réception ne se date pas dans le futur. » ; refus serveur gardés (« Fournisseur inconnu. », « Matière inconnue dans la réception. », « Qualité : conforme, réserve ou refusé. », « Magasin inconnu. », « Ligne de commande inconnue. », « La commande {n°} n'est pas de {fournisseur} … », « « {réf} » n'est pas sur la ligne choisie de {n°}. », `probleme_du_bon` (brouillon pas parti, annulé, réception avant l'envoi), « Le bon {n°} est en {devise} : sa réception aussi. », « Devise inconnue : {code}. », refus de facture, « Une réception validée est entrée en stock : elle ne se modifie plus. L'annuler… ») | **atomique** : tout ou rien, plus de doublon (anom. 4.5) ; raison du grisé (anom. 4.9) |

### 4.17 Fiche réception (en-tête, indicateurs, bandeaux, facture, gestes) — `/receptions/:id`

Gestion MP : fiche « Réception — {n° | Brouillon} » (`DetailReception.tsx`, `Dialogue tresLarge sale`, relue toutes les 30 s) → PRO : `/receptions/:id?onglet=lignes|reclamations|pieces|historique` (`Fenetre({taille: tresLarge, sale})`, `Indicateurs`, `Onglets`, `Blocages`, `Bouton({blocages})`, `Confirmer`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Relecture toutes les 30 s ; serveur recale le brouillon à chaque lecture | `GET receptions/{id}` relu à l'ouverture, au retour de focus et toutes les 30 s pour un brouillon ; recalage serveur gardé (R6r) | — |
| Disparue : « Chargement… » puis « Cette réception n'existe plus. » | `Chargement` honnête ; 404 → `Vide` | — |
| Données `GET /receptions`, `useDevises`, `useTolerances`, `GET /reclamations`, `GET /pieces/reception/{id}` | `GET receptions/{id}` (lignes, `blocages`, `avertissements`, facture, réclamations, nb pièces, tolérances) | une lecture |
| En-tête : **fournisseur** ; note « arrivée du {date} · BL {n° | —} · bon(s) » + liens vers chaque bon (« Ouvrir le bon de commande ») ou « · hors commande » ; statut ; « Saisie par {nom} le {horodatage} · contrôlée au quai par {nom} · validée par {nom} le {horodatage} » | `Definitions` ; `LienDocument` → `/commandes/:id` ; `Badge` ; « Par » | adresse stable |
| KPI « Pesé (entre en stock) » « {Σ hors refus} kg » ; « {n} ligne(s) » | `Kpi` | — |
| KPI « Écarts de pesée » (nb |écart| > tol. ; « au-delà de 2 % de l'annonce » ; critique/ok) | `Kpi` (tolérance lue au serveur) | — |
| KPI « Sous réserve / refusé » « {r} / {f} » ; « quarantaine / n'entre pas » | `Kpi` | — |
| KPI « Facture » n° ; détails réglée / échéance (dans N j, dépassée de N j, aujourd'hui, non fixée) / « montant non saisi » / « pas encore reçue » ; teintes | `Kpi` + `Montant` | — |
| Bandeau brouillon « Brouillon : rien n'est encore entré en stock, pas encore de numéro. Il se remet à jour tout seul (reste à livrer, prix confirmés) si d'autres réceptions passent avant lui. » | `Note` | — |
| Bandeau blocages « **Avant de valider :** » + résumé (`resumerBlocages` : > 2 lignes sans pesée, > 2 sans lot) + « Le détail, ligne par ligne ({n}) » | `Blocages` (résumé + détail repliable), lus sur `blocages` serveur | — |
| Blocages serveur : `date_permise` ; problèmes du bon ; excédent « « {réf} » : {kg} kg reçus (tous lots ensemble) pour {kg} kg restant… » ; « L'inventaire {n°} est en cours … » ; « « {réf} » : la pesée est à zéro … » ; « « {réf} » : le numéro de lot manque … » ; « Une ligne sous réserve va en quarantaine : créer d'abord un magasin de type « Quarantaine » … » ; « « {réf} » : choisir le magasin de rangement. » ; lignes refusées non contrôlées ; lignes de bon laissées vides (non livrées par ce camion) non contrôlées, retirées à la validation et toujours dues ; toutes vides : « Rien n'est pesé : saisir ce que le camion a apporté (les lignes laissées vides restent dues sur le bon). » (LIVRAISON-PARTIELLE) | mêmes textes, même calcul | — |
| Avertissements « **À savoir avant de valider :** » : bon soldé ; bon parti avec modification à approuver | `Note` (info) | — |
| Bandeau annulée « Réception annulée par {nom} le {horodatage} — motif : {motif}. Ses entrées en stock ont été contre-passées ; les bons concernés attendent de nouveau leur marchandise. » | `Note` ; motif lu sur la colonne `annulation_motif` | colonne réelle |
| Bandeau validée « Réception validée sous le n° {n°} : {n} lot(s) créé(s) ou complété(s), la marchandise est en stock. » + « Imprimer les étiquettes QR à coller sur les palettes » | toast + `BoutonImprimer` | — |
| Panneau « Facture du fournisseur » : « N° de facture » (« vide : détache la facture » ; en dossier : grisé « dans le dossier {n°} : pour le changer, l'en détacher d'abord (dossier › Marchandises) ») ; « Date de facture » (max aujourd'hui) ; « Montant » ; « Devise » ; « Échéance » (min date ; « proposée : date + {n} j » / « délai de paiement non réglé ») ; note « La facture ne touche pas au stock : elle se complète ou se corrige même après la validation. » | `Carte` en ligne dans la fenêtre (`sale` propre) ; `DateChamp`, `Montant`/`Prix`, `Selecteur` ; numéro grisé avec raison + `LienDocument` → `/dossiers/:id?onglet=marchandises` | lien direct vers le dossier |
| Onglets « Lignes pesées » (compte), « Pièces jointes » (compte), « Réclamations » (compte) ; état local | `Onglets` `?onglet=lignes|reclamations|pieces|historique` | anom. 4.18 ; + Historique |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Corriger » (infobulle « Rouvre la saisie de ce brouillon ») | D, A | `GET receptions/{id}` | toast si validée/annulée entre-temps | → `/receptions/nouvelle?brouillon=ID` |
| « Supprimer le brouillon » (infobulle « Rien n'est entré en stock : le brouillon s'efface ») | D, A | `DELETE receptions/{id}` | `Confirmer` « Supprimer ce brouillon ? » · « Oui, supprimer » ; refus « Une réception validée ne se supprime pas : l'annuler. » | toast « Brouillon supprimé. » ; retour liste |
| « Valider la réception » (infobulle « Écrit les lots, les entrées en stock et les prix payés ; la réception reçoit son numéro ») | D, A | `POST receptions/{id}/valider` | `Bouton({blocages})` (infobulle « Avant de valider : {1er blocage} ») ; `Confirmer` « {n} ligne(s) en stock disponible, {q} en quarantaine, {r} refusée(s) — {kg} kg. {e} écart(s) de pesée hors tolérance. Ensuite, elle ne se modifie plus. » ou « Toutes les lignes sont refusées : rien n'entre en stock, la réception reste la trace du refus. … » · « Oui, valider » ; refus « Cette réception est déjà validée. », date, 1er blocage (avec son code : 409 pour un état — excédent, bon clos ou pas parti, inventaire en cours, période close —, 422 pour une saisie) | validation serveur gardée (verrou des bons, quarantaine, lot interne `LOT-AAAA-NNNN`, n° REC, mouvement au prix payé et cours figé, solde automatique, journal) ; notification de la file « À valider » levée |
| « Imprimer les étiquettes des lots » | D, A | `GET documents/etiquettes?lots=…` | `manque` « Aucun lot : toutes les lignes sont refusées » | raison du grisé (anom. 4.9) |
| « Compléter la facture » / « Corriger la facture » (infobulle « La facture se complète ou se corrige sans toucher au stock ») | D, A | — (ouvre le panneau) | — | — |
| « Enregistrer la facture » | D, A | `PUT receptions/{id}/facture` | refus « Cette réception est annulée : sa facture ne se modifie plus. », « La date, le montant et l'échéance de la facture {n°} se corrigent ici ; son numéro, non. … dossier … », « L'échéance ne précède pas la date de la facture. », « Cette réception est en {d} : sa facture aussi. … », « Devise inconnue : {d}. », « La facture {n°} est en {d} et porte d'autres réceptions : elle ne change pas de devise. » | succès « Facture {n°} enregistrée. » / « Facture détachée de la réception. » |
| « Annuler » (panneau facture) | D, A | — | garde `sale` du panneau | — |
| « Marquer réglée » (infobulle « La facture est payée : elle sort de l'échéancier et de l'« échu, non réglé » ») | D, A | `PUT echeancier/paiement` `{objet: 'facture', id, payee_le}` | `Confirmer` « Réglée le [`DateChamp` : min date de facture, max aujourd'hui] » · « Oui, réglée » ; refus « Un règlement ne se date pas dans le futur … », « Le règlement ({date}) précède la pièce qu'il règle ({date}). », « Pièce introuvable. » | borne min = date de facture (anom. 4.10) ; succès « Facture {n°} réglée le {date}. » |
| « Annuler le règlement » (infobulle « La facture redevient due : elle revient dans l'échéancier ») | D, A | `PUT echeancier/paiement` `{…, payee_le: null}` | `Confirmer` « Annuler le règlement ? » · « Oui, annuler le règlement » | succès « Règlement de la facture {n°} annulé. » |
| « Réclamer au fournisseur » (infobulle « Un défaut constaté (qualité, manque, bobines, retard) : ouvrir une réclamation, lot et quantité préremplis ») | D, A | — | — | → `/reclamations/nouvelle?reception=ID` (pile au-dessus de la fiche) |
| « Annuler (contre-passation) » (infobulle « Chaque entrée est contre-passée par un mouvement inverse, à la même date ; tout reste tracé ») | D, A | `POST receptions/{id}/annuler` `{motif}` | `Confirmer` motif **exigé** (« Annuler ? Les entrées seront contre-passées. Motif : » placeholder « ex. saisie en double ») · « Oui, annuler (contre-passation) » ; `Bouton({blocages})` « Elle est dans le dossier d'importation {n°} : [le rouvrir, puis] l'en détacher d'abord (dossier › Marchandises › « Détacher la réception ») — ses frais restent au dossier » ; refus « Seule une réception validée s'annule ; un brouillon se supprime. », refus de contre-passation (matière plus là), période close | motif en colonne `annulation_motif` (R18r) ; **une réception entièrement refusée s'annule** (aucun mouvement à contre-passer, statut annulée) ; toast « Réception {n°} annulée : ses entrées sont contre-passées. » (anom. 4.16) |
| « Fermer » | D, A | — | si facture en saisie « La facture saisie n'est pas enregistrée. L'abandonner ? » · « Oui, abandonner » | retour `/receptions` (onglet, filtres gardés) |

### 4.18 Fiche réception › Lignes pesées — `/receptions/:id?onglet=lignes`

Gestion MP : volet « Lignes pesées » → PRO : `DataTable`, `LienDocument`, `Badge`, `KgEtMetres`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Référence · bon » ; note lien « bon {n°} » → `/commandes?ouvrir={id}` ou « hors commande » | `LienDocument` → `/commandes/:id` | adresse stable |
| « Lot » lien `/lot/{id}` (infobulle « La fiche du lot : où il est, où il est allé ») ; brouillon « lot interne » (infobulle « Un lot à nous sera donné à la validation ») ; vide « à saisir » (« — » si refusé) | `LienDocument` → `/lots/:id` ; `Badge` | — |
| « Reste à livrer (kg) » (brouillon) / « Reste après (kg) » (validée/annulée) ; note « déjà reçu {kg} » ; « — » hors commande | idem | — |
| « Annoncé BL (kg) » ; « Pesé (kg) » + mètres ; « Écart » (`signe` + « ±{kg} kg » ; « — » sans attendu) | idem | — |
| « Bobines » (« {p} pal. + {n} ») ; « kg / bobine » (attention > 5 % ; « catalogue {x} ({±%}) ») | idem | — |
| « Magasin » (« n'entre pas » / « quarantaine » / code / « à choisir ») ; « Qualité » (Conforme / Sous réserve / Refusé + observations) | `Badge` | — |
| « Prix / kg » (infobulle « Le prix payé : celui du bon confirmé, sinon celui saisi (ou du catalogue) ») 3 déc. ; « {devise} · du bon » | `Prix` (lecture) | — |
| « Observations : {texte} » sous le tableau | `Note` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Lien « bon {n°} » | D, A | `GET commandes/{id}` | — | → `/commandes/:id` |
| Lien du lot | D, A | `GET lots/{id}` | — | → `/lots/:id` |

### 4.19 Fiche réception › Réclamations — `/receptions/:id?onglet=reclamations`

Gestion MP : volet « Réclamations » → PRO : `DataTable`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| N° · Ouverte le · Lot · référence (« toute la réception » sans lot) · Motif · Quantité (kg) · Issue (« {issue} » ok / « ouverte » attention) | mêmes colonnes ; référence gardée même sans lot (ligne refusée) | anom. 4.17 |
| Ligne cliquable → fiche ; vide « Aucune réclamation sur cette réception. » | `lien` → `/reclamations/:id` ; `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne | D, A | `GET reclamations/{id}` | — | → `/reclamations/:id` |

### 4.20 Fiche réception › Pièces jointes — `/receptions/:id?onglet=pieces`

Gestion MP : `PiecesJointes objet="reception"` → PRO : `PiecesJointes` (`objet: 'reception'`), rôles D, A. Contenu et gestes identiques à 4.13 (`POST pieces`, `GET pieces/{id}/fichier`, `DELETE pieces/{id}` avec `Confirmer`).

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Joindre un document… » / glisser ; ouvrir ; « Retirer » | D, A | `POST pieces` ; `GET pieces/{id}/fichier` ; `DELETE pieces/{id}` | mêmes refus ; `Confirmer` au retrait | — |

### 4.21 Fiche réception › Historique (nouveau) — `/receptions/:id?onglet=historique`

Gestion MP : journal général seulement → PRO : `Historique` (`GET historique/reception/{id}`), rôles D, A. Gestes : aucun.

### 4.22 Réceptions › Réclamations — `/receptions?onglet=reclamations&etat=ouvertes|closes|toutes&q=`

Gestion MP : onglet « Réclamations » (`Reclamations.tsx`) → PRO : `Indicateurs`, `Bascule` (dans l'adresse), `Recherche`, `Filtres`, `DataTable`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| KPI « Ouvertes » (attention/ok ; « dont {n} depuis plus de 30 jours » / « en attente du fournisseur ») | `Kpi({lien: '?etat=ouvertes'})` | — |
| KPI « Closes » (« réponse obtenue ou abandon ») | `Kpi` | — |
| KPI « Délai de réponse » (moyenne `jours` des closes, « en moyenne, des closes ») | `Kpi({formule})` | — |
| KPI « Obtenu » (`montants` par devise ; « avoirs et remises, par devise ») | `Kpi` + `Montant` | — |
| Titre = Bascule « Ouvertes ({n}) » · « Closes ({n}) » · « Toutes » (défaut Ouvertes, hors adresse) | `Bascule` `?etat=` | anom. 4.18 |
| Recherche « Fournisseur, lot, motif, n°… » (n°, fournisseur, réception, lot, référence, motif, description, issue, réponse) | `Recherche` | — |
| — | `Filtres` liés : Fournisseur, Motif, Issue | ajout (A1) |
| « Nouvelle réclamation » (infobulle « Une réclamation sans réception : un retard, une facture fausse… ») | `Bouton` | — |
| Col. N° (RCL-…) · Ouverte le · Fournisseur · Réception · lot (n° ou « sans réception » ; note « lot {n} · {réf} ») · Motif (+ description tronquée 80 car.) · Quantité (kg) · Demandé · Obtenu · Issue (`Badge` ; neutre si Refusée/Abandonnée) · Durée (infobulle « Depuis l'ouverture (jusqu'à la clôture pour une close) » ; critique > 30 j ouverte) | mêmes colonnes ; Réception en `LienDocument` | — |
| Ligne cliquable ; vide « Aucune réclamation ne correspond. » / « Aucune réclamation. Un défaut à la réception ? Ouvrez la réception, puis « Réclamer au fournisseur ». » | `lien` → `/reclamations/:id` ; `Vide` | — |
| Chargement « … les réclamations… » ; erreur | `Chargement`, `Erreur` | — |
| Motifs (« Qualité (défaut du fil) », « Quantité manquante », « Poids des bobines », « Bobines endommagées », « Retard de livraison », « Documents (facture, BL, certificat) », « Autre ») ; issues (« Avoir », « Remplacement », « Remise sur la prochaine commande », « Refusée », « Abandonnée ») | listes servies par le serveur (`GET motifs`) | une source |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule Ouvertes / Closes / Toutes | D, A | `GET reclamations?etat=` | — | dans l'adresse |
| « Nouvelle réclamation » | D, A | — | — | → `/reclamations/nouvelle` |
| Clic ligne | D, A | `GET reclamations/{id}` | — | → `/reclamations/:id` |

### 4.23 Nouvelle réclamation / Réclamer au fournisseur — `/reclamations/nouvelle?reception=ID&ligne=ID`

Gestion MP : fenêtre « Nouvelle réclamation » / « Réclamer au fournisseur — {fournisseur} » (`NouvelleReclamation`, `Dialogue large sale`) → PRO : `Fenetre({taille: large, sale})`, `Form`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Note « Réception {n°} du {date} · BL {n°}. La réclamation reçoit son numéro tout de suite ; joignez ensuite les photos et les documents. » | `Note` | — |
| « Ligne en cause » (« — toute la réception — » + « {réf} · lot {n} · {qualité} » ; défaut 1re non conforme ; recopie quantité, devise, observations) | `Selecteur` ; la ligne choisie est envoyée par `reception_ligne_id` (référence gardée même sans lot) | anom. 4.17 |
| Sans réception : « Fournisseur » (actifs ; pose sa devise) | `Selecteur` | — |
| « Motif » (défaut « Qualité (défaut du fil) » si non conforme) ; « Ouverte le » (max aujourd'hui) ; « Quantité en cause (kg) » (« pesé : {kg} kg ») ; « Montant demandé » (« avoir ou remise attendue ; vide si on demande un remplacement ») ; « Devise » ; « Ce qui a été constaté » (≤ 4000, placeholder « ex. 12 bobines tachées d'huile sur la palette 4, photos jointes ») | `Selecteur`, `DateChamp` (min date de réception, max aujourd'hui), `Nombre`, `Prix`, `Zone` | bornes de date posées |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Changer de « Ligne en cause » | D, A | — (local) | — | — |
| « Annuler » (si saisie « Abandonner la réclamation ? » · « Oui, abandonner ») | D, A | — | garde `sale` | — |
| « Ouvrir la réclamation » | D, A | `POST reclamations` `{fournisseur_id, reception_id, reception_ligne_id, lot_id, motif, description, quantite, montant_demande, devise, ouverte_le}` | `Bouton({manque: ["Choisissez le fournisseur.", "Choisissez le motif."]})` ; refus « Fournisseur inconnu. », « Réception inconnue. », « La réception {n°} est de {f}, pas de {f}. », « On réclame sur ce que le fournisseur a livré : cette réception n'est pas encore validée. / est annulée. », « Lot inconnu. », « Le lot {n} n'a pas été livré par {f}. », « Le lot {n} n'est pas dans la réception {n°}. », « {q} réclamés pour {l} livrés par la réception {n°}. », « Devise inconnue : {d}. », « Une réclamation ne s'ouvre pas dans le futur. », « Une réclamation ne précède pas la réception qu'elle vise ({date}). » | raison du grisé (anom. 4.9) ; succès → `/reclamations/:id` (n° RCL) |

### 4.24 Fiche réclamation — `/reclamations/:id?onglet=reponse|pieces|historique`

Gestion MP : fenêtre « Réclamation {n°} — {fournisseur} » (`DetailReclamation`, `Dialogue large sale`) → PRO : `Fenetre({taille: large, sale})` sur `/receptions?onglet=reclamations`, `Indicateurs`, `Onglets`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre + étiquette « close : {issue} » / « ouverte » ; disparue « Cette réclamation n'existe plus. » | `Badge` ; 404 → `Vide` | — |
| KPI « Motif » (« ouverte le {date} par {nom} ») ; « En cause » (« {kg} kg » ; lien « réception {n°} · lot {n} » → `/receptions?ouvrir=` ou « sans réception ») ; « Demandé / obtenu » ; « Durée » (« close le » / « depuis l'ouverture » ; critique > 30 j) | `Kpi` ; `LienDocument` → `/receptions/:id`, `/lots/:id` | adresse stable |
| Bandeau « Constaté : {description} » | `Note` | — |
| Volet « Réponse du fournisseur » : « Issue » (« — pas encore — » + issues ; « obligatoire pour clore ») ; « Montant obtenu ({devise}) » (« avoir, remise ») ; « Réponse du fournisseur » (≤ 4000, placeholder « ce qu'il a répondu, ce qui est convenu (avoir n°, remplacement par le prochain conteneur…) ») | onglet `reponse` : `Selecteur`, `Prix`, `Zone` ; sur une close l'issue est en lecture | anom. 4.17 |
| Volet « Pièces jointes » (compte) | onglet `pieces` (`PiecesJointes objet: 'reclamation'`) | — |
| — | onglet `historique` (`Historique`, `GET historique/reclamation/{id}`) | nouveau |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Enregistrer la réponse » | D, A | `PUT reclamations/{id}` `{version, reponse, description, montant_obtenu}` (champ absent = inchangé ; permis aussi sur une **close** : l'avoir arrive après la clôture) ; l'issue se pose par `POST reclamations/{id}/clore` `{version, issue, montant_obtenu, close_le, reponse}` | `Bouton({manque: ["Rien n'a changé"]})` ; refus « Réclamation introuvable. », « Issue : Avoir, Remplacement, … », clore une close : 409 « Cette réclamation est close avec l'issue « {issue} » : elle la garde. La rouvrir pour changer d'issue. » | raison du grisé ; issue verrouillée sur une close (anom. 4.17) ; succès « Réponse enregistrée. » (répondre ne rouvre pas) |
| « Clore la réclamation » (infobulles « Choisissez d'abord l'issue » / « La réclamation est terminée ») | D, A | `POST reclamations/{id}/clore` `{issue, montant_obtenu, reponse}` | `Bouton({manque: ["Choisissez d'abord l'issue"]})` ; `Confirmer` « Clore avec l'issue « {issue} » ? » · « Oui, clore » ; refus « Pour clore, dire comment elle s'est terminée (avoir, remplacement, refusée…). » | `close_le` = aujourd'hui serveur ; succès « Réclamation close : {issue}. » |
| « Rouvrir » (infobulle « La réclamation redevient ouverte : on attend de nouveau le fournisseur ») | D, A | `POST reclamations/{id}/rouvrir` | `Confirmer` « Rouvrir cette réclamation ? » · « Oui, rouvrir » | succès « Réclamation rouverte. » |
| Pièces jointes (joindre, ouvrir, retirer) | D, A | `POST pieces` ; `GET pieces/{id}/fichier` ; `DELETE pieces/{id}` | `Confirmer` au retrait | — |
| « Fermer » (si saisie « La réponse n'est pas enregistrée. L'abandonner ? » · « Oui, abandonner ») | D, A | — | garde `sale` | retour à la liste |

### 4.25 Réceptions › Poids des bobines — `/receptions?onglet=bobines&ecarts=1&q=`

Gestion MP : onglet « Poids des bobines » (`PoidsBobines.tsx`) → PRO : `Indicateurs`, `Recherche`, `Filtres`, `DataTable`, `ExportExcel`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /receptions/bobines` (tolérance `toler_poids_bobine`, lignes par matière, `hors_tolerance`) ; chargement « … le poids des bobines… » | `GET receptions/bobines` | — |
| KPI « Matières suivies » (« bobines pesées et comptées ») ; « Hors catalogue » (attention/ok ; « dernière pesée à ±5 % et plus ») ; « Bobines qui s'alourdissent » (≥ 2 réceptions, hausse > tol. ; « hausse de plus de 5 % depuis la 1re réception ») ; « Bobines qui s'allègent » | `Kpi({formule, lien})` (tolérance lue au réglage, pas écrite en dur) | — |
| Carte « Par matière » (infobulle « Poids pesé ÷ bobines comptées, à chaque réception validée. Un clic sur une ligne montre sa courbe. ») ; recherche « Référence, fournisseur… » ; case « écarts seulement » | `Carte` ; `Recherche` ; `Filtres` : interrupteur « Écarts seulement » (`?ecarts=1`) + Fournisseur lié ; « Effacer les filtres » | A1 (anom. 4.13) |
| Col. Référence · Fournisseur · Catalogue kg / bobine (« — ») · Premier · Dernier (gras + « le {date} ») · Évolution (« — » si 1 réception ; neutre < 0,5 %, attention > tol., sinon ok) · vs catalogue (critique hors tol.) · Mini – maxi · Réceptions · bouton « Courbe » | mêmes colonnes ; `Badge` ; Référence `lien` → `/stock/matieres/:id` | — |
| Ligne cliquable → courbe ; vide « Aucune matière ne correspond. » / « Dès qu'une réception validée porte un nombre de bobines, le poids moyen de la bobine s'inscrit ici et se suit dans le temps. » | `lien` → `?matiere=ID` ; `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne / « Courbe » (infobulle « La courbe du poids et chaque réception ») | D, A | `GET receptions/bobines?matiere=ID` | — | fenêtre 4.26 dans l'adresse |
| Case « écarts seulement » | D, A | — (filtre ; `?ecarts=1`) | — | — |
| « Exporter en Excel » (`/export/receptions/bobines?q&ecarts`) | D, A | `GET export/receptions/bobines?q=&ecarts=&fournisseur=` | — | feuilles « Par matière » et « Mesures » gardées |

### 4.26 Poids de la bobine — {réf} — `/receptions?onglet=bobines&matiere=ID`

Gestion MP : fenêtre « Poids de la bobine — {réf} » (`Dialogue large`) → PRO : `Fenetre({taille: large})`, `Indicateurs`, `Courbes`, `DataTable`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| KPI « Catalogue » (« {x} kg » ; « poids inscrit au catalogue ») ; « Dernière réception » (« {±%} du catalogue · {date} » ; attention hors tol.) ; « Évolution » (« de {a} à {b} kg ») ; « Moyenne » (« {n} réception(s) · {mini}–{maxi} ») | `Kpi` | — |
| Courbe (axe du temps réel, pointillé « catalogue », infobulle « Réception du {date} » / « {x} kg » « kg / bobine ») | `Courbes` | — |
| Tableau Date · Réception · Fournisseur · Lot · Pesé (kg) · Bobines · kg / bobine · vs catalogue (récent d'abord) ; vide « Aucune mesure. » | `DataTable` ; Réception et Lot en `LienDocument` | liens ajoutés |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Fermer | D, A | — | — | retour `?onglet=bobines` (filtres gardés) |

### 4.27 Réceptions › Archive des pesées — `/receptions?onglet=pesees&ecarts=1&q=`

Gestion MP : onglet « Archive des pesées » (`ArchivePesees.tsx`) → PRO : `Indicateurs`, `Recherche`, `Filtres`, `DataTable` dans `Cadre` (pagination serveur transparente `ChargerPlus` au-delà de 500 lignes), `ExportExcel`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /receptions/pesees` + `GET /receptions` (pour le bon de chaque ligne) ; chargement « … l'archive des pesées… » | `GET receptions/pesees` (porte le bon de chaque ligne, paginé) | une lecture |
| KPI « Lignes pesées » (« {kg} kg pesés ») ; « Écarts de pesée » (« au-delà de ±2 % de l'annonce ») ; « Lignes non conformes » (« sous réserve ou refusées ») ; « Bobines hors catalogue » (« kg / bobine à ±5 % et plus ») | `Kpi({formule, lien})` | — |
| Titre « {n} ligne(s) · {kg} kg pesés » (infobulle « Chaque ligne reçue, lot par lot : {kg} kg pesés pour {kg} kg annoncés ») | `Carte` | — |
| Recherche « Référence, lot, fournisseur, réception, bon… » ; case « écarts seulement » (infobulle « Écart de pesée, de poids de bobine, ou ligne non conforme ») | `Recherche` ; `Filtres` : « Écarts seulement », Fournisseur, Qualité, Magasin (liés) ; « Effacer les filtres » | A1 (anom. 4.13) |
| Col. Réception (n° ou « Brouillon » ; note date + statut si non validée) · Référence (« bon {n°} » / « hors commande ») · Lot · Magasin · Fournisseur · Annoncé BL (kg) (infobulle « Le bon de livraison ; à défaut, ce que la commande attendait ») · Pesé (kg) · Écart (+ « ±{kg} kg ») · Bobines (« {p} pal. ») · kg / bobine (« cat. {x} ({±%}) ») · Qualité (+ observations) | mêmes colonnes ; « Annoncé BL (kg) » = BL seul (« — » sans BL), l'écart dit « vs reste à livrer » quand il s'y compare ; Réception, bon, lot en `LienDocument` | anom. 4.11 ; lignes menant aux documents |
| Non cliquable ; vide « Aucune pesée ne correspond. » / « Chaque pesée saisie viendra s'inscrire ici, avec son lot et son écart. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Case « écarts seulement » | D, A | `GET receptions/pesees?ecarts=1` | — | — |
| « Exporter en Excel » (`/export/receptions/pesees?q&ecarts`) | D, A | `GET export/receptions/pesees?q=&ecarts=&…` | — | feuille « Pesées » gardée (+ ligne des tolérances) ; « Annoncé BL (kg) » = BL seul |

### 4.28 Exports Excel des listes de la partie — (routes `GET export/…`)

Gestion MP : `exports_achats.py` → PRO : `ExportExcel` (classeurs `openpyxl` côté serveur, mêmes filtres que l'écran), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /export/commandes?onglet&q` : « commandes-AAAA-MM-JJ.xlsx », titre « Bons de commande — exporté le … », « Filtres : … » ; feuille « Commandes » (N°, Date du bon, Fournisseur, Pays, Statut, Livraison, Lignes, Commandé (kg), Reçu (kg), Reste à livrer (kg), Livré, Devise, Montant confirmé, Montant estimé, Montant MAD, Reste à recevoir MAD, Prix à confirmer, Cours figé, Livraison prévue, ETA, Livrée le, Dernière réception, Conteneur, Par, Approuvé par, Observations) ; feuille « Lignes » (… Prix confirmé « oui » / « non (prix du catalogue) », Confirmé par, Confirmé le, Montant) | `GET export/commandes` mêmes feuilles ; « Livraison » → « État de livraison » ; « Reste à recevoir MAD » → « Reste à livrer (MAD) » ; « Observations » → « Remarques au fournisseur » ; + « Soldé à la main » ; filtre retard et filtres liés transmis | anom. 4.11, 4.13 |
| `GET /export/receptions?onglet&q` : feuilles « Réceptions » (N°, Arrivée, Fournisseur, Bons de commande, N° du BL, Facture, Date facture, Montant facture, Devise facture, Échéance, Lignes, Pesé (kg), Statut, Par, Contrôlé par, Validée par, Observations) et « Lignes » (N°, Arrivée, Fournisseur, Bon de commande, Référence, Lot, Reste à livrer (kg), Annoncé BL (kg), Pesé (kg), Écart (kg), Écart (%), Palettes, Bobines, kg / bobine, Magasin, Qualité, Prix / kg, Devise, Observations) | `GET export/receptions` mêmes feuilles + « Motif d'annulation » | colonne réelle |
| `GET /export/receptions/pesees` (feuille « Pesées » 21 colonnes + ligne des tolérances) ; `GET /export/receptions/bobines` (« Par matière », « Mesures ») | `GET export/receptions/pesees`, `GET export/receptions/bobines` | — |
| `GET /export/pilotage` (classeur complet) | gardé ; + export de la liste du plan (route ajoutée, API-PRO § 1.24 : `GET /api/export/plan-achat`) | anom. 4.14 |

Gestes : ceux des listes (4.1, 4.5, 4.15, 4.25, 4.27).

### 4.29 Document — Bon de commande fournisseur (HTML A4, anglais) — `GET /api/documents/commandes/{id}/bon`

Gestion MP : `GET /api/commandes/{id}/impression` (HTML écrit en Python, `achats.py:1035-1147`) → PRO : gabarit Jinja2 `documents/bon_commande.html` (A4, papier à en-tête), données d'un service unique `services/documents/bon_commande.py` partagé avec l'Excel (4.30), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Bouton « Imprimer le bon » de la fiche, tous statuts, nouvel onglet ; 404 « Commande introuvable. » | `BoutonImprimer` de la fiche | — |
| HTML `lang=en`, `@page{size:A4;margin:12mm 13mm 16mm}` ; feuille A4 simulée à l'écran, barre collante « Imprimer / enregistrer en PDF (A4) » masquée à l'impression ; Arial 10 pt ; `<title>` « BC-2026-0012 » / « brouillon n° 7 » ; écran < 820 px : largeur libre | même mise en page ; `<title>` « BC-2026-0012 » ou « Draft — not sent » | titre anglais, plus de « brouillon n° 7 » |
| **Aucun prix ni montant** | aucun prix, montant **ni devise** | point tranché |
| Avertissement écran (non imprimé) si la raison sociale manque : « La raison sociale de l'usine n'est pas réglée (Réglages › Paramètres › Société) : elle manque en tête du bon. » | gardé sur le document (hors impression) **et** sur la fiche (4.7) | — |
| Réglages « Société » : `nom_entreprise`, `forme_juridique`, `adresse`, `ville`, `telephone`, `banques`, `ice`, `rc`, `identifiant_fiscal`, `cnss`, `patente` ; `secteur` non utilisé | mêmes réglages (`GET parametres` famille Société) ; `secteur` imprimé sous la raison sociale s'il est réglé (DECISIONS A22) | conforme à A22 |
| 1. En-tête papier : raison sociale rouge #d40000 19 pt, initiale 28 pt ; forme et capital ; « SIEGE SOCIAL » + adresse ; ville ; téléphone ; Times New Roman ; lignes vides omises | identique (jetons du gabarit) ; le papier est en anglais sur ce bon : « HEAD OFFICE » au lieu de « SIÈGE SOCIAL » (décision du 8 octobre, E16) | bon entièrement en anglais |
| 2. Titre : « Purchase order » ; n° ou « Draft — not sent » ; « Date » (`date_en` « 08 Oct 2026 » ou « on sending ») ; « Expected delivery » (date ou « to be agreed ») | identique ; date = date d'envoi réelle (envoi ou approbation) | — |
| 3. Cadres « Supplier » (nom, pays, contact, téléphone, e-mail) et « Deliver to » (raison sociale ou « — », adresse, ville, « Expected date », « Incoterm ») | identique | — |
| 4. Tableau (en-tête répété, ligne insécable) : « No. » · « Item » (référence + désignation) · « Packing » (`conditionnement_en` : « By weight », « Pallet », « Drum », « Bobbin », « Cone », « Bag », « Roll », « Carton », « Bale », « Case », « Can », sinon tel quel ; « of {contenance} kg ») · « Qty » (format anglais « 1,234.5 », « — » au poids) · « Total weight » (« {kg} kg » ; « ≈ {m} m » cuir, franges, ruban) ; pied « Total ordered » · « {Σ} kg » | colonnes communes HTML et Excel : « No. » · « Item » · « Description » · « Packing » · « Qty » · « Total weight (kg) » · « Length (m, indicative) » (colonne présente seulement si une ligne a des mètres) ; pied « Total ordered » | une seule définition pour les deux formes ; « m » en anglais (« ml » reste à l'écran) |
| 5. « Remarks » (si `observations`) | « Remarks » = `observations` du bon | — |
| 6. « Please confirm this order by return — quantities and delivery date — and quote its number on your delivery note and on your invoice. » | identique (même phrase dans l'Excel) | — |
| 7. Signatures « For {raison sociale | the buyer} / Purchasing manager » et « Accepted by the supplier / Stamp and signature » | identique (l'Excel les porte aussi) | — |
| 8. Pied du papier (Times 8,5 pt, fixé en bas de chaque page) : « **BANQUES** » + banques ; identifiants légaux « ICE : … R.C : … N.I.F : … C.N.S.S : … PATENTE : … » | « **BANKS** » + banques ; identifiants légaux inchangés | pied en anglais (E16) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer / enregistrer en PDF (A4) » (barre du document) | D, A | — (`print()` du navigateur) | — | — |

### 4.30 Document — Excel du bon pour le fournisseur — `GET /api/export/commandes/{id}/bon`

Gestion MP : « Excel pour le fournisseur » (`exporter_bon_fournisseur`, `exports_achats.py:324-419`) → PRO : même route, classeur bâti sur le service de 4.29, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Lien `download` ; 404 « Bon de commande introuvable. » ; fichier « {n°}.xlsx » / « brouillon-{id}.xlsx » | idem ; brouillon « draft-{id}.xlsx » | nom anglais pour le fournisseur |
| Feuille « Purchase order », anglais, sans prix ni montant | idem, sans devise ; mise en page A4 portrait (`fitToWidth`, en-têtes répétés) | identique au HTML |
| En-tête usine (Times 18 pt rouge ; ou « Raison sociale à régler (Réglages › Paramètres › Société) ») ; forme, « SIEGE SOCIAL », ville, téléphone | mêmes blocs, « HEAD OFFICE » (E16) ; raison sociale absente → **409** « La raison sociale de l'usine n'est pas réglée (Réglages › Paramètres › Société) : le bon ne part pas sans elle. » (pas de classeur sans elle ; jamais un texte interne français dans le document fournisseur) ; avertissement sur la fiche | Gestion MP corrigé A-18 (lot D3, décision 2) |
| « PURCHASE ORDER {n°} » / « PURCHASE ORDER — draft, not sent » ; « Date » ; « Expected delivery » | « Purchase order » + n° / « Draft — not sent », mêmes libellés que le HTML | libellés unifiés |
| « Supplier » (Name, Country, Contact, Phone, Email) ; « Deliver to » (Company, Address, City, Expected date, Incoterm) | mêmes blocs que le HTML | — |
| Tableau « No. », « Item », « Description », « Packing », « Qty », « Total weight (kg) », « Length (m, indicative) » ; « Total ordered » | colonnes communes (4.29) | — |
| « Remarks » ; phrase de confirmation (variante entre parenthèses) ; pied « BANQUES » et identifiants ; largeurs A–G 16, 30, 36, 24, 12, 14, 14 | même phrase que le HTML ; + signatures ; pied « BANKS » comme le HTML | identique dans ses deux formes |

Gestes : celui de la fiche (4.7).

### 4.31 Document supprimé — `GET /api/export/bon-de-commande/{id}`

Gestion MP : `exporter_bon_de_commande` (`exports.py:307-419`), français, avec prix, « Livraison souhaitée », « Observations », aucun écran ne l'appelle → PRO : **supprimé** (anom. 4.3) ; les prix d'un bon se lisent dans la fiche et dans `GET export/commandes` (feuille « Lignes »). Aucun geste.

### Anomalies GMP corrigées — Partie 4

- **4.1** Livraison prévue impossible à vider (`None` ignoré) → le schéma distingue « absent » et `null` ; `null` = recalcul envoi + délai ; aide et refus d'envoi deviennent vrais.
- **4.2** Case « Envoyer avec nos prix du catalogue » sans effet → **supprimée** ; lignes créées `prix = NULL` ; montant estimé au catalogue ; « Reprendre les prix du catalogue » au volet Prix.
- **4.3** Route morte `/export/bon-de-commande/{id}` (français, prix, « Livraison souhaitée ») → supprimée.
- **4.4** Solder/Annuler : infobulle sur `recu > 0`, geste sur `dejaLivre` → libellé, infobulle et question lus sur un seul champ serveur `fin_possible`.
- **4.5** Enregistrement multi-devises en plusieurs requêtes (doublon possible) → une requête atomique, réponse = liste des réceptions.
- **4.6** Excédent calculé ligne par ligne à l'écran, tous lots au serveur ; deux lots d'une ligne de bon impossibles → même règle des deux côtés, bouton « + un autre lot ».
- **4.7** Date confirmée par le fournisseur acceptée au serveur sans champ → champ « Livraison prévue confirmée par le fournisseur » au volet Prix.
- **4.8** Confirmer des prix sur un brouillon fige le cours → volet Prix réservé aux bons partis (blocage serveur et écran).
- **4.9** Boutons grisés sans raison (Enregistrer des lignes, Enregistrer le suivi, Oui renvoyer, Confirmer ces prix, Créer le bon, Enregistrer le brouillon, Imprimer les étiquettes, Ouvrir la réclamation, Enregistrer la réponse) → `Bouton({manque, blocages})` partout.
- **4.10** Refus découverts au clic (envoi avec livraison passée ou période close, promesse passée, règlement avant la facture) → `blocages` serveur affichés avant le clic, bornes min/max des `DateChamp`.
- **4.11** Vocabulaire : « Remarques au fournisseur » partout (fiche figée, export) ; « Reste à recevoir » → « Reste à livrer (MAD) » ; « Annoncé BL (kg) » = BL seul ; « HEAD OFFICE » / « BANKS » sur le bon anglais (E16, révisé le 8 octobre) ; « m » dans le document anglais, « ml » à l'écran.
- **4.12** Bon sans numéro à approuver affiché « Brouillon » → `Badge` « À approuver » (table unique statut → libellé).
- **4.13** Filtres sans « Effacer les filtres », filtre retard non exporté → `Filtres` liés + « Effacer les filtres » + `ExportExcel` avec tous les filtres.
- **4.14** Plan d'achat : « À commander » sans unité, « Ruptures » sur toutes les matières sans le dire, export = tout le pilotage → « À commander (kg) », détail « sur toutes les matières », export de la liste (route ajoutée, API-PRO § 1.24) + classeur complet à part.
- **4.15** Unité « ml » proposée puis refusée → `unites_possibles` servies par le serveur, sans « ml ».
- **4.16** Date de facture sans maximum à la saisie ; annulation de réception sans message → `DateChamp` max aujourd'hui ; toast d'annulation.
- **4.17** Réclamation sur ligne refusée perd sa référence ; issue « — pas encore — » sur une close refusée au serveur → `reception_ligne_id` stocké ; issue en lecture sur une close.
- **4.18** Volets de fiches et Bascule hors adresse → `?onglet=` des fiches, `?etat=` des réclamations, `?matiere=` de la courbe.
- **4.19** « Palettes par conteneur » perdu → aide de calcul retenue par poste et par fournisseur (stockage local), hors du bon.
- **4.20** « Tout valider » ignore commandes et réceptions → réceptions brouillons dans `GET brouillons` ; commandes à envoyer dans « Ma journée ».
- **4.21** Commentaire orphelin (`DetailReception.tsx:59`) → sans objet (code neuf).

### Comptes de la partie 4

- Écrans (pages) : 3 — Plan d'achat, Commandes, Réceptions.
- Onglets / sous-vues : 2 (plan) + 5 (commandes) + 7 (fiche commande, dont 2 nouveaux) + 6 (réceptions) + 4 (fiche réception, dont 1 nouveau) + 3 (Bascule réclamations) + 3 (fiche réclamation, dont 1 nouveau) = 30.
- Fenêtres : 8 — Préparer une commande, Nouvelle commande, fiche commande, Saisie de réception, fiche réception, Poids de la bobine, Nouvelle réclamation, fiche réclamation (+ panneau facture en ligne).
- Documents : 2 gardés (bon HTML A4, Excel du bon, identiques) + 1 supprimé ; 5 exports de listes (+ 1 à ajouter).
- Gestes : 96 lignes dans les tableaux « Gestes » (les 77 de GMP, détaillés — saisies locales, liens et pièces jointes comptés à part —, dont la case « sans prix » supprimée ; nouveaux : « + un autre lot », date réelle d'approbation, bascule et liens d'adresse, bouton d'impression du document).
- Sections : 32 (4.0 à 4.31).
- Anomalies : 21, toutes traitées.

### Routes demandées par la partie 4 (reportées dans API-PRO § 1.24)

- `GET /api/export/plan-achat?onglet=&q=&statut=&priorite=&abc=&fournisseur=&urgence=&devise=&pays=` (D, A) : la liste affichée du plan d'achat, filtres liés compris (l'actuel `GET export/pilotage` reste le classeur complet).

---

## Partie 5 — Importations & coût de revient (dont Réglages › Postes de frais et Codes douaniers)

Source : `docs/heritage/ECRANS.md` l. 4021-4919. Rôles : D, A (L et T : `EcranReserve`) ; Réglages ›
Postes de frais et Codes douaniers : écriture D, **lecture A** (contrat ; GMP les cachait aux achats).
« anom. 5.n » renvoie à la liste de la fin de la partie.

**Points tranchés appliqués ici** : « Supprimer le dossier » devient **« Annuler le dossier »** (`POST
dossiers/{id}/annuler`, motif exigé, numéro gardé, marchandise rendue à « En attente », frais gardés en
lecture mais **retirés du coût**) ; le cours d'une marchandise sans cours payé vaut **NULL** (« cours du
jour »), plus jamais 0 ; la fiche dossier a une adresse stable `/dossiers/:id` et s'ouvre en fenêtre
par-dessus la liste (ou par-dessus l'analyse qui l'a ouverte) ; onglets « Pièces jointes » et
« Historique ». Un dossier n'est **jamais supprimé** : tout dossier, même saisi à la main, s'annule (motif 3–300,
refusé sur un clos et en période close) ; un annulé garde numéro, lignes détachées et frais, et ne se rouvre pas ; la liste
le montre sous `?statut=annule`. Le champ « Observations » de l'écran est `commentaire` à l'API. Rattacher se fait **par
facture seulement** (`{version, facture_id}` : plus de `reception_ligne_ids`, qui pouvait couper une réception).

### 5.0 Notions et règles transverses — (service `services/importations/`, toutes les routes de la partie)

Gestion MP : § 0 « Notions transversales » (`importations.py`, `moteur.py:3520-3730`, `securite.py`) → PRO : mêmes règles, calculées une fois au serveur, formules dans `aide.json` (A7, `Formule`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Dossier = une facture = une livraison ; s'ouvre depuis la facture d'une réception validée, en prend toute la marchandise libre ; second camion rejoint ; réception sans facture attend ; dossier d'avant la mise en service à la main ; dossier repris de l'ERP Fil multi-factures | identique (I3), **sauf** : un dossier (un arrivage, une déclaration en douane) porte **une ou plusieurs factures** — « Ajouter une facture », « Retirer » (5.6 b) ; une facture n'est que dans un seul dossier ; C36 facture par facture | décision de Mohamed du 12/10/2026 (lot PLUSIEURS-FACTURES) |
| Numéro dès l'ouverture, série `DOS` « NN/AA » (année de la date d'arrivée) ; numéro saisi ≤ 16 car., unique ; suivant si pris | identique ; un dossier annulé **garde** son numéro (série sans trou) | annulation |
| Statuts `ouvert` / `clos` (« Ouvert » / « Clos le jj/mm/aaaa hh:mm ») | `ouvert` / `clos` / `annule` (`Badge` « Annulé le … ») | point tranché |
| Entrée = pesée × prix (pas le montant facture) ; `poids_kg` figé ; lignes prises : réception validée, non refusée, pesée > 0, hors dossier | identique (I18) | — |
| Cours : cours figé du bon si même devise, sinon **0 = cours du jour** ; cours payé à la banque le remplace ; MAD sans cours ; clôture écrit le cours du jour + commentaire « cours du jour X figé à la clôture du jj/mm/aaaa » | sans cours = **NULL** (« cours du jour ») ; à la clôture, le cours du jour écrit porte `cours_origine = clos_au_jour` (pas de note en commentaire), remis à NULL à la réouverture ; le reste identique | point tranché |
| Achat MAD = valeur devise × (cours ou taux du jour) | identique | — |
| Postes de frais d'origine DD, TPI, TVA (récupérable), PORT, FRET, ASSUR, TRANSIT, TIMBRE, INT_OC, TMSA, AUTRE ; récupérable ou coût ; clé `valeur` / `poids` ; postes système DD, TPI, TVA, FRET, ASSUR | identique | — |
| Répartition : part valeur / part poids ; frais visé sur une ligne = entier ; répartition figée (`parts`) ; sans arrondi | identique | — |
| Charges hors TVA, TVA, Coût hors TVA (= revient), Coût TTC, Charges / achat, Coût hors TVA / kg (dossier, ligne, famille), Achat / kg | identique ; vocabulaire de REGLES § 5 | — |
| Frais non répartis (> 0,005) dans aucun coût, montrés à part ; dossier vide ne se clôt pas | identique (I15), même chiffre partout | — |
| Valeur en douane (CAF) = achat + FRET + ASSUR | identique ; **tous les textes disent « achat + fret + assurance »** | anom. 5.3 |
| Droits attendus = valeur en douane × taux du code actif ; seulement si toutes les matières ont un code actif (sinon `matieres_sans_code`) ; droits saisis = Σ DD | identique | — |
| Écart des droits (écran seul) : `|saisis − attendus| > max(50 MAD, 2 %)` | calculé **au serveur** (`ecart_droits`), seuils lus dans `parametres` | anom. 5.4 |
| TVA attendue = taux TVA × (CAF + DD + TPI) ; TPI = frais TPI sinon CAF × taux TPI ; TVA saisie = poste TVA seul ; écart toléré 5 % (`TOLERANCE_TVA_IMPORT`) | identique ; **une seule définition** de « TVA saisie » (poste TVA) ; textes lisent les taux réglés ; écart toléré lu dans le réglage **`toler_tva_import`** (5 %, Réglages › Prix ; semé par la révision 0003), le même pour C29 et pour la fiche (`tva_ecart_tolere_mad`, API-PRO 189) | anom. 5.2, 5.4 ; Gestion MP corrigé (E-10) |
| Frais hors norme (C35) dossier / ligne, seuil « Frais d'un dossier d'importation à vérifier au-delà de » (100 %, 5-10 000 %) | identique | — |
| Marchandise négative (avoir trop gros) refusée | identique | — |
| Écart facture ↔ reçu (C36), tolérance 2 % ; coût reste pesée × prix | identique | — |
| Cours éloigné (écran) > 5 % ; cours disparates ; lignes au cours du bon | calculés au serveur (`alertes`) | une source pour liste, fiche, clôture (anom. 5.8) |
| Fournisseur marocain : hors « En attente » (compté) ; ouverture confirmée (`local_confirme`) | identique (I16) | — |
| Période close : gestes qui changent le coût refusés (409 + marche à suivre) ; clôture permise | identique ; annulation de dossier soumise à la période close | — |
| Échéancier du dossier (factures marchandise + frais ; trié échéance puis quoi ; réglé = `payee_le`, saisi dans Analyse › Échéancier) | identique ; en-tête et échéancier lisent la même source | anom. 5.19 |
| Famille de fil « composition + façon + titrage » | identique | — |
| Pièces jointes (facture, DUM, connaissement, certificat, factures de frais, quittances), même clos | joindre permis même clos ; **retirer refusé sur un clos** (le rouvrir) | anom. 5.20 |
| Journal : « ouverture dossier », « modification dossier », « marchandises dossier », « marchandise saisie à la main », « cours », « commentaire marchandise », « marchandise retirée », « réception détachée », « frais », « frais modifié », « frais retiré », « clôture dossier », « réouverture dossier », « suppression dossier », « frais figés », postes et codes | mêmes gestes, journal avant/après ; « suppression dossier » → « annulation dossier » | onglet « Historique » des fiches |
| Droits : routes dossiers, a-rattacher, exports, analyse, postes (GET), codes (GET), pièces : `ACHATS` ; écritures postes et codes : `DIRECTION` | identique (D, A ; écritures postes/codes D) | — |
| Rafraîchissement après écriture (13 caches) | invalidation globale | — |
| Teintes (`importations.css` : ligne-groupe, entete-dossier, enregistre, controles-dossier, ecart, saisie.frais, ligne bleue `tr.nouvelle`, reunion, indicateurs serres, filtres etroits ; `Etiquette` urgent/attention/ok/accent/neutre) | jetons CSS ; `Badge` (table unique) ; `Carte` « contrôle » ton `ecart` ; ligne d'ajout `DataTable` ton accent | 0 hex hors `:root` |

### 5.1 Importations & coût de revient (en-tête, indicateurs, onglets) — `/importations`

Gestion MP : « Importations & coût de revient » `/importations` (`Importations.tsx`) → PRO : `/importations?onglet=ouverts|clos|rattacher` (`Page`, `EnTete`, `Indicateurs`/`Kpi`, `Onglets`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde `['achats']` ; `peut('achats')` / `interdit` toujours vrais/faux (code mort) | `routes.ts` D, A ; plus de test de rôle dans l'écran | anom. 5.13 |
| Adresse : `onglet` absent ou hors liste → `ouverts` ; `?dossier=ID` ouvre la fenêtre (retiré à la fermeture) | `?onglet=` ; `/dossiers/:id` (A5) ; ancien `?dossier=ID` redirigé | adresse stable |
| Liens entrants : Accueil (« N facture(s) reçue(s) sans dossier d'importation », « N réception(s) importée(s) sans facture » → `?onglet=rattacher`) ; Analyse › Contrôles → `?dossier=ID` ; Mode d'emploi | Accueil → `?onglet=rattacher&vue=factures` / `&vue=receptions` ; Contrôles → `/dossiers/:id` ; notifications → `/dossiers/:id` | vue exacte |
| Données `GET /dossiers` (résumés, date d'arrivée décroissante nulls en dernier, puis id) ; `GET /dossiers-a-rattacher[?locaux=true]` | `GET dossiers?statut=&q=` ; `GET dossiers/a-rattacher?locaux=` | — |
| Titre « Importations & coût de revient » ; sous-titre « Une facture, un dossier : la livraison et ses frais, répartis à la valeur ou au poids. La TVA reste hors du coût. » ; actions lien « Analyse du coût de revient », « Nouveau dossier » | `EnTete` (fil « Achats › Importations », aide) | — |
| KPI « Dossiers » (« dont N ouvert(s) ») | `Kpi` | sous-titre de rangée « tous les dossiers, ouverts et clos (hors annulés) » (anom. 5.9) |
| KPI « Achat » `montantCourt(Σ marchandise_mad)` ; infobulle exacte ; « marchandise, en MAD » | `Kpi({formule})` | — |
| KPI « Charges hors TVA » (attention) ; « x,x % de l'achat » / « toutes les charges sauf la TVA » ; rouge « · + N non répartis » (infobulle « Frais sans marchandise, dans aucun coût : 01/26 (1 234 MAD), … ») | `Kpi` ; « + N non répartis » avec liste de `LienDocument` | chaque dossier cité ouvrable |
| KPI « Coût hors TVA » (ok) ; « achat + charges, rendu usine » | `Kpi` | — |
| Onglets « Dossiers ouverts » (compte) · « Dossiers clos » (compte) · « En attente de dossier » (compte factures + réceptions sans facture) ; erreur rouge ; chargement « … les dossiers… » | `Onglets` (compteur) ; `Erreur`, `Chargement` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Analyse du coût de revient » (infobulle « Par matière, titrage, fournisseur, qualité… dans la page Analyse ») | D, A | — (→ `/analyse?onglet=revient`) | — | — |
| « Nouveau dossier » | D, A | — (→ `/dossiers/nouveau`) | — | — |

### 5.2 Importations › Dossiers ouverts · Dossiers clos (· Annulés) — `/importations?onglet=ouverts|clos&etat=annules&q=`

Gestion MP : `ListeDossiers` (`Importations.tsx:185-370`) → PRO : `Carte`, `Recherche`, `Filtres`, `Bascule` (onglet clos : « Clos » · « Annulés »), `DataTable` dans `Cadre`, `ExportExcel`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Dossiers ouverts » / « Dossiers clos » | `Carte` ; onglet clos : `Bascule` « Clos » / « Annulés » (`?etat=annules`) | dossiers annulés visibles |
| Lien « N arrivée(s) attendent leur dossier » (ouverts, si > 0) → `rattacher` | `LienDocument` → `?onglet=rattacher` | — |
| « Exporter en Excel » (`/api/export/dossiers?statut=ouvert|clos`, infobulle « Ces dossiers, leurs marchandises, leurs frais et leur échéancier dans un classeur ») | `ExportExcel` → `GET export/dossiers?statut=&q=&…` | recherche et filtres transmis |
| Recherche (mots, sans accents : numéro, libellé, banque, commentaire, factures, réceptions, familles) ; placeholder « Numéro, libellé, facture, réception, famille de fil (« frisé 2900 »)… » ; compteur « N dossier(s) » ; aucun filtre, pas de tri, pas de pagination | `Recherche` (+ observations) ; `Filtres` liés : Fournisseur, Famille de fil, « À vérifier seulement » ; « Effacer les filtres » ; en-têtes triables ; `Cadre` | A1, A2 |
| Col. « Dossier » : **numéro** + étiquette « à vérifier » (infobulle = raisons « frais non répartis », « droits ≠ attendus », « TVA ≠ attendue », « facture ≠ marchandise reçue », « frais hors norme sur une marchandise », « marchandise négative (avoir) ») ; note libellé | `Badge` « à vérifier » alimenté par les `alertes` serveur, **toutes** (dont frais hors norme du dossier, cours disparates, cours éloignés) | anom. 5.8 |
| « Arrivée » ; « Clos le » (onglet clos) | idem ; Annulés : « Annulé le » + « Motif » | — |
| « Facture · réceptions » (n° + « REC-… · REC-… » ; dossier repris : chaque pièce ou « sans facture » ; « saisi à la main » ; « — ») | idem ; réceptions en `LienDocument` | liens (§ 6 GMP : aucun) |
| « Familles de fil » (3 premières « famille · N kg », « + N autre(s) », « aucune marchandise » ; tri poids) | idem | — |
| « Poids » ; « Achat MAD » ; « Charges hors TVA » (infobulle d'en-tête « toutes les charges sauf la TVA » ; note % de l'achat, « — à vérifier » rouge, « + N non répartis » rouge) ; « Coût hors TVA » (gras + « x,xx MAD / kg ») ; « Coût TTC » (+ « dont TVA N ») | `droite` + `unite` (kg, MAD) | — |
| Ligne cliquable (infobulle « Ouvrir le dossier ») | `lien` → `/dossiers/:id` | — |
| Pied (si > 1) « Total des N dossiers » ; Σ poids, achat, charges (+ %), coût (+ MAD/kg), TTC (+ TVA) ; lignes visibles | pied « Total des N dossiers affichés » | dit qu'il suit la recherche (anom. 5.9) |
| Vide : « Aucun dossier ne correspond à la recherche. » ; ouverts « Aucun dossier ouvert. « Nouveau dossier » en ouvre un depuis une facture. » ; clos « Aucun dossier clos. » | `Vide` ; + annulés « Aucun dossier annulé. » | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne | D, A | `GET dossiers/{id}` | — | → `/dossiers/:id` |
| « N arrivée(s) attendent leur dossier » | D, A | — | — | → `?onglet=rattacher` |
| « Exporter en Excel » (→ `dossiers-importation-AAAA-MM-JJ.xlsx`) | D, A | `GET export/dossiers?statut=&q=&…` | — | filtres transmis |
| Bascule « Clos » / « Annulés » (nouveau) | D, A | `GET dossiers?statut=annule` | — | — |

### 5.3 Importations › En attente de dossier — `/importations?onglet=rattacher&vue=factures|receptions&locaux=1`

Gestion MP : `VueARattacher` (`Importations.tsx:405-476`) + `ReceptionsSansFacture` (`:479-537`) → PRO : `Carte`, `Bascule` (dans l'adresse), `Interrupteur`, `ChoixFacture` (5.4), `DataTable`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « En attente de dossier » (infobulle « Tant qu'une arrivée n'est dans aucun dossier, son coût est le seul prix de la facture : ses frais (droits, fret, transitaire…) manquent au coût moyen du stock. ») ; chargement « … ce qui attend un dossier… » | `Carte`, `Chargement` | — |
| Bascule « Factures reçues (N) » / « Réceptions sans facture (N) » ; défaut Factures sauf si aucune facture et des réceptions | `Bascule` `?vue=factures|receptions` | dans l'adresse (anom. 5.16) |
| Case « Fournisseurs marocains (N) » / « Fournisseurs marocains montrés » (infobulle « Un fournisseur marocain facture en dirhams, sans douane ni fret international : il n'a pas de dossier d'importation ») ; relit `?locaux=true` | `Interrupteur` `?locaux=1` (texte « en MAD » au lieu de « en dirhams ») | vocabulaire (« MAD ») |
| Factures reçues : note « Un dossier, une facture : c'est à chaque livraison qu'on paie les droits, le fret et le transitaire. La facture ouvre son dossier avec toute la marchandise qu'elle a apportée ; un second camion de la même facture rejoint son dossier. » + `ChoixFacture` ; bouton « Ouvrir son dossier » ou « Ajouter au dossier 12/26 » | `Note` + `ChoixFacture` | — |
| Réceptions sans facture : note « Pas de dossier sans facture : saisir le numéro de la facture sur la réception (il se complète même après la validation), puis la facture ouvre son dossier ci-dessus. » | `Note` | — |
| Col. Réception (gras) · Fournisseur · Reçue le · BL (« — ») · Lots (nb de lignes libres) · Poids (kg) · Valeur (une ligne par devise, jamais additionnées) · « Saisir la facture » | mêmes colonnes ; « Lots » = lots distincts ; Réception `LienDocument` | anom. 5.14 |
| Non cliquable ; pas de recherche ; vide « Toutes les réceptions de l'étranger ont leur facture. » ; tri date décroissante | `Recherche` ajoutée (n°, fournisseur, BL) ; `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule Factures / Réceptions | D, A | — (`?vue=`) | — | — |
| Case « Fournisseurs marocains » | D, A | `GET dossiers/a-rattacher?locaux=true` | — | — |
| « Ouvrir son dossier » | D, A | `POST dossiers` `{facture_id, local_confirme}` | fournisseur marocain sans dossier : `Confirmer` « {fournisseur} est un fournisseur marocain : ni douane, ni fret international. Ouvrir quand même un dossier d'importation ? » · « Non » · « Oui, l'ouvrir » (infobulle « Un fournisseur marocain n'a normalement pas de dossier d'importation ») ; `Bouton({occupe})` ; refus de 5.5 | succès « Facture {n°} : dossier {NN/AA} ouvert. » → `/dossiers/:id` |
| « Ajouter au dossier {NN/AA} » (second camion) | D, A | `POST dossiers/{id}/rattacher` `{facture_id}` | refus de 5.12 ; `Bouton({blocages})` si le dossier est clos (« le rouvrir d'abord ») | succès « Facture {n°} : le second camion rejoint le dossier {NN/AA}. » (+ « Ses marchandises n'ont pas le même cours que les premières (USD, …) : vérifier l'avis de la banque. ») → `/dossiers/:id` |
| « Saisir la facture » | D, A | — | — | → `/receptions/:id` (panneau facture ouvert) |

### 5.4 Choisir une facture (composant `ChoixFacture`, 4 usages : 5.3, 5.5, 5.6 b, 5.12) — (sous-vue)

Gestion MP : `ChoixFacture.tsx` → PRO : `ChoixFacture` = `Filtres` (fournisseur lié) + `Recherche` + `DataTable`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Liste « Tous les fournisseurs (N) » / « {nom} ({nb factures}) » triée, infobulle « Fournisseur » | `Selecteur` lié : comptes recalculés sur les factures qui passent le texte | anom. 5.15 |
| Texte « Numéro de facture — la liste se réduit à mesure qu'on écrit » (`autoFocus` en création) : numéro sans ponctuation ni casse (« FA-2026/117 » = « fa 2026 117 »), ou tous les mots dans « numéro + réceptions + familles » | `Recherche` (même normalisation, `Colonne.recherche`) | — |
| Compteur « N facture(s) » ; pas d'« Effacer les filtres » | compteur + « Effacer les filtres » | anom. 5.15 |
| Col. Facture (**n°** + réceptions) · Fournisseur (note « fournisseur marocain », infobulle « Un fournisseur marocain n'a pas de dossier d'importation ») · Reçue le · Lots · Poids (kg) · Valeur facture (une ligne par devise `nombre(v,2) DEV`) · Familles de fil arrivées · (bouton) | mêmes colonnes ; « Lots » = lots distincts | anom. 5.14 |
| Bouton : `Confirmer` si fournisseur local sans dossier, sinon principal | idem | — |
| Vide total « Aucune facture n'attend de dossier. Le numéro de facture se saisit sur la réception ; une facture dont toute la marchandise est dans son dossier n'apparaît plus ici, ni une réception pas encore validée. » ; filtré « Aucune facture en attente ne correspond. Vérifier le numéro saisi sur la réception — ou la facture a déjà son dossier. » | `Vide` | — |
| Tri date décroissante (serveur) | idem | — |

Gestes : le bouton d'action de la ligne (voir 5.3, 5.5, 5.12) ; filtres locaux.

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Choisir le fournisseur / taper le numéro | D, A | — (local) | — | filtres liés + « Effacer les filtres » |

### 5.5 Nouveau dossier d'importation — `/dossiers/nouveau?onglet=facture|main`

Gestion MP : fenêtre `CreationDossier` (`Importations.tsx:541-687`, très large, garde en mode « main ») → PRO : `Fenetre({taille: tresLarge, sale})` sur `/importations`, `Onglets` (`?onglet=`), `ChoixFacture`, `Form`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde « Abandonner les modifications ? » seulement en mode main (numéro, libellé, banque ou commentaire saisi) | `Fenetre({sale})` texte standard (A4) | texte unique |
| Onglet « Depuis la facture reçue » (compte = factures sans dossier) ; note « Un dossier, une facture. Choisir le fournisseur, taper le numéro de facture : toute la marchandise qu'elle a apportée entre au dossier, le libellé et la date d'arrivée se remplissent seuls. Il ne restera qu'à saisir les frais. » ; `ChoixFacture` ; info « N réception(s) attendent leur facture : elle se saisit sur la réception (onglet « En attente de dossier »), puis elle ouvre son dossier ici. » | `Onglets` `facture` ; `Note` ; `ChoixFacture` ; `Note` + `LienDocument` → `?onglet=rattacher&vue=receptions` | — |
| Libellé auto serveur « {fournisseur} — facture {n°} » ; date d'arrivée = plus ancienne réception | identique | — |
| Onglet « Dossier d'avant la mise en service » ; note « Pour un dossier d'avant la mise en service seulement : il garde son vrai numéro, et ses marchandises se saisissent à la main. Toute arrivée depuis la mise en service a sa réception, donc sa facture : elle s'ouvre « Depuis la facture reçue ». » | `Onglets` `main` ; `Note` | — |
| « Numéro » (aide « vide : le suivant (NN/AA) ; un ancien dossier garde le sien » ; max 16 ; placeholder « automatique » ; « Le dossier « X » existe déjà. ») | `Saisie` (`maxLength` du schéma) | — |
| « Libellé » (`duo`, autoFocus ; « Fournisseur, n° de facture, conteneur… » ; ≤ 160) | `Saisie` `maxLength` 160 | anom. 5.17 |
| « Date d'arrivée » (défaut aujourd'hui ; 2000-2100, « date d'arrivée hors période ») | `DateChamp` (bornes serveur) | — |
| « Banque » (« AWB, BMCI… » ; ≤ 32) | `Saisie` `maxLength` 32 | anom. 5.17 |
| « Commentaire » (« Transitaire, n° de DUM, observations… » ; ≤ 2000) | `Zone` « Observations » `maxLength` 2000 ; champ `commentaire` de l'API (colonne du modèle, lot D7) | vocabulaire d'écran (anom. 5.14) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Ouvrir son dossier » (onglet facture) | D, A | `POST dossiers` `{facture_id, local_confirme}` | `Confirmer` si fournisseur marocain ; refus (§ 8 GMP) : « Facture inconnue. », « Cette facture a déjà son dossier, {NN/AA} : un dossier par facture. … », « La facture {F} est déjà dans le dossier {NN/AA} (repris de l'ancien ERP) … », « {fournisseur} est un fournisseur marocain … L'ouvrir quand même se confirme. », « La facture « {F} » n'a plus de marchandise à rattacher … », concurrence (« Un autre poste vient d'enregistrer cette facture dans le dossier {NN/AA} : l'ouvrir pour la suite (rien n'est perdu). » + `LienDocument`), période close « (ouverture du dossier refusé) » | → `/dossiers/:id` |
| « Ouvrir le dossier à saisir à la main » (onglet main) | D, A | `POST dossiers` `{numero, libelle, date_arrivee, banque, commentaire}` (numéro au format `NN/AA` ; date d'arrivée exigée, jamais dans le futur) | `Bouton({occupe})` ; « Le dossier « X » existe déjà. » ; « date d'arrivée hors période » | → `/dossiers/:id?onglet=main` |
| « Annuler » | D, A | — | garde `sale` | retour `/importations` |

### 5.6 Fiche dossier (titre, en-tête, indicateurs, bandeaux, gestes) — `/dossiers/:id`

Gestion MP : fenêtre « Dossier {NN/AA} » (`DetailDossier.tsx`, très large, `sale`) → PRO : `/dossiers/:id?onglet=familles|marchandises|frais|echeancier|pieces|facture|main|historique` (`Fenetre({taille: tresLarge, sale})` sur `/importations` ou sur l'écran d'origine, `Definitions`, `Indicateurs`, `Note`, `Onglets`, `Bouton({blocages})`, `Confirmer`, `FenetreConfirmation`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `modifiable = ouvert && peut('achats')` ; clos : tout en lecture ; serveur `_ouvert()` « Ce dossier est clos : le rouvrir pour y toucher (c'est tracé). » (409) | `modifiable` + `blocages` du serveur ; annulé : tout en lecture | — |
| Données `GET /dossiers/{id}`, `GET /postes-frais/complet`, `GET /pieces/dossier/{id}`, `GET /dossiers-a-rattacher` **sans locaux** | `GET dossiers/{id}` (porte `a_rattacher` = factures de second camion, **locaux compris**, nb pièces, alertes, blocages) + `GET postes-frais` | anom. 5.10 |
| Chargement « … le dossier… » ; 404 « Dossier introuvable. » | `Chargement`, `Vide` | — |
| Enregistrement en quittant le champ (ou Entrée) ; « Enregistré à HH:MM » (heure serveur, vert, 4 s) ; seuls les ajouts ont un bouton | identique (`X-Heure-Serveur`) | — |
| Titre « Dossier {numéro} » + « — {libellé} » + « Ouvert » (attention) / « Clos le jj/mm/aa hh:mm » (ok) | titre de `Fenetre` ; `Badge` « Ouvert » / « Clos le … » / « Annulé le … » | — |
| Rangée d'en-tête : « Arrivée le … » ; « Banque : … » ; facture « Facture **{n°}** du {date} · {montant} {devise} · échéance {date} (REC-…, REC-…) » / dossier repris (pièces) / « Saisi à la main (avant la mise en service) » ; commentaire entre « » ; « Modifier l'en-tête » ; « Enregistré à … » ; « Clôturer le dossier » / « Rouvrir pour corriger » | `Definitions` ; « Facture **{n°}** » ou « Factures **{n°}** · **{n°}** » (le détail — date, montant, échéance, réceptions — est dans le bloc « Factures du dossier », 5.6 b) ; REC en `LienDocument` → `/receptions/:id` ; observations | liens vers les réceptions (§ 6 GMP) ; plusieurs factures (12/10/2026) |
| Panneau « Modifier l'en-tête » : « Libellé » (« Conteneur Izmir, camion Globaltex… »), « Date d'arrivée » (vide → rien), « Banque » (« AWB, BMCI… »), « Commentaire » (aide « transitaire, n° de DUM, remarques… ») ; au blur ; « Terminé » (« Chaque champ s'enregistre en le quittant ») ; « Supprimer le dossier » | `Carte` en ligne ; `Saisie` avec `maxLength` 160 / 32 / 2000 ; « Observations » (aide « transitaire, n° de DUM… ») ; « Annuler le dossier » | anom. 5.14, 5.17 |
| KPI « Poids » (« N lot(s) ») ; « Coût hors TVA » (ok ; « x,xx MAD / kg » / « achat + charges ») ; « Achat » (« marchandise, en MAD ») ; « Charges hors TVA » (attention ; % / « toutes les charges sauf la TVA ») ; « Coût TTC » (urgent si écart droits/TVA ; « dont TVA N MAD » ou lien « droits ≠ attendu : voir les frais » / « TVA ≠ attendu : … » / « droits et TVA ≠ attendus : voir les frais », infobulle « Voir les contrôles de l'onglet Frais ») | `Kpi({formule, lien: '?onglet=frais'})` | — |
| Bandeau non répartis « Frais non répartis : {N MAD} hors TVA[ et {N MAD} de TVA] ne trouvent pas de marchandise où se répartir (dossier vide). … Le dossier ne se clôt pas ainsi. » | `Note` (erreur) | — |
| Bandeau « Frais hors norme : {charges} de frais pour {marchandise} … (au-delà de {seuil %}, réglable dans Réglages › Prix). Un zéro de trop, ou les frais d'un autre dossier ? … » + lien « les vérifier sur leurs pièces » | `Note` + lien `?onglet=frais` | — |
| Bandeau « Coût sous zéro : {réf.} — un avoir dépasse ce que la marchandise a coûté. » + « Frais hors norme sur une seule marchandise : {réf.} … » + « Un frais visé sur une seule ligne nourrit le coût moyen de ce lot : » « le vérifier » | `Note` + lien | — |
| Bandeau info « Facture {n°} : {montant} {devise} facturés pour {reçu} {devise} reçus (pesée × prix), soit {x,x %} d'écart (tolérance {x,x %}, Réglages › Prix). … (contrôle C36). » | `Note` (info), **un par facture** hors tolérance (chacune rapprochée de ce qu'elle a apporté) | plusieurs factures |
| Messages de succès / d'erreur du dernier geste sous les bandeaux | `Messages` (toasts) | — |
| Onglets (un niveau) : « Par famille de fil » (nb familles), « Marchandises » (nb lignes), « Frais » / « Frais ● » (brouillon), « Échéancier » (nb), « Documents » (nb pièces), « Second camion de la facture » (si modifiable et second camion), « Saisie à la main » / « … ● » (si modifiable et sans facture) ; défaut « Saisie à la main » si dossier vide à la main, sinon familles ; onglet devenu impossible → familles ; brouillons gardés ; **hors adresse** | `Onglets` `?onglet=` : `familles`, `marchandises`, `frais` (● si brouillon), `echeancier`, `pieces` (« Pièces jointes »), `facture`, `main`, `historique` (nouveau) ; mêmes règles de présence et de défaut | anom. 5.16 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Modifier l'en-tête » (infobulle « Libellé, date d'arrivée, banque, commentaire — et supprimer le dossier ») | D, A | — | `blocages` si clos/annulé | infobulle « … — et annuler le dossier » |
| Champ d'en-tête quitté (changé) | D, A | `PUT dossiers/{id}` `{version, libelle, date_arrivee, banque, commentaire}` (fiche entière ; schéma strict : `numero`, `facture_id` refusés) | refus clos ; 422 « date d'arrivée hors période » | « Enregistré à … » ; anom. 5.13 |
| « Terminé » | D, A | — | — | — |
| « Supprimer le dossier » (danger ; infobulle « Supprimer le dossier : sa facture attend de nouveau son dossier[, ses N frais sont perdus] » ; « Supprimer le dossier {n°} ? La facture {F} attendra de nouveau son dossier. » + « N frais saisi(s), {montant}, seront perdus — pour les garder, détacher plutôt la réception (onglet Marchandises). » / « Aucun frais n'est saisi. » · « Non » · « Oui, supprimer ») | D, A | `POST dossiers/{id}/annuler` `{motif}` | **« Annuler le dossier »** ; `Confirmer` motif exigé : « Annuler le dossier {n°} ? Il garde son numéro. La facture {F} (ou : les factures {F}, {G} attendront de nouveau leur dossier ; ou : ses marchandises) attendra de nouveau son dossier. N frais saisi(s), {montant}, sortiront du coût — pour les garder, détacher plutôt la réception (onglet Marchandises). Motif : [ ] » · « Non » · « Oui, annuler le dossier » ; `Bouton({blocages})` : « Ce dossier est clos : le rouvrir d'abord. », période close « (annulation refusé) » | point tranché ; marchandises détachées de leurs lignes reçues (`reception_ligne_id` vidé, D7) pour qu'un nouveau dossier les reprenne ; frais gardés en lecture, hors coût ; frais dus hors échéancier, frais réglés gardés comme réglés ; toast « Dossier {n°} annulé : sa facture attend de nouveau son dossier ; N frais ({montant}) sortis du coût. » (anom. 5.12) |
| « Clôturer le dossier » (principal ; infobulle « Figer le coût hors TVA : un dossier clos ne se modifie plus (il se rouvre si une facture de frais arrive en retard, c'est tracé) ») | D, A | `POST dossiers/{id}/cloturer` | `Bouton({blocages})` : « Un dossier sans marchandise n'a rien à clore. », « Des frais ne trouvent pas de marchandise où se répartir : les affecter à tout le dossier, ou les retirer, avant de clore. » ; `FenetreConfirmation` (A3) : « Clore ? » + avertissements serveur dans l'ordre (1 cours vides → cours du jour écrit ; 2 N ligne(s) au cours du bon ; 3 cours multiples par devise ; 4 frais > {seuil %} de l'achat ; 5 frais hors norme sur {réf.} ; 6 facture ≠ reçu {x,x %} ; 7 cours > 5 % du jour ; 8 N fournisseurs ; 9 aucun droit saisi ; 10 droits ≠ attendus ; 11 aucune TVA / TVA ≠ attendue), sinon « Le coût hors TVA devient celui des lots en stock. » · « Non » · « Oui, clôturer » | grisé avec raison, y compris frais non répartis (anom. 5.7) ; effets serveur gardés (`poids_kg`, cours NULL ← taux du jour avec `cours_origine = clos_au_jour`, `clos_le`, journal) ; toast « Dossier clôturé : son coût est figé. » |
| « Rouvrir pour corriger » (infobulle « Rouvrir le dossier pour y ajouter un frais arrivé en retard, ou corriger ») | D, A | `POST dossiers/{id}/rouvrir` | `Confirmer` « Rouvrir pour corriger ? La réouverture est tracée. » (motif facultatif) · « Non » · « Oui, rouvrir » ; refus « Ce dossier est déjà ouvert. », période close « (réouverture refusé) » | motif au journal ; les cours écrits à la clôture (`clos_au_jour`) redeviennent « cours du jour » (NULL) ; toast « Dossier rouvert : il se modifie de nouveau. » |
| Liens « voir les frais », « les vérifier sur leurs pièces », « le vérifier » | D, A | — | — | → `?onglet=frais` |
| « Fermer » | D, A | — | garde `sale` (brouillon de frais ou de saisie à la main) | retour à l'écran d'origine (filtres gardés) |

### 5.6 b Fiche dossier › Factures du dossier (lot PLUSIEURS-FACTURES) — `/dossiers/:id`

Décision de Mohamed du 12/10/2026 (amende I3) : un dossier — une déclaration en douane, un arrivage —
regroupe **une ou plusieurs factures** (deux factures du même fournisseur dans le même conteneur, ou de
fournisseurs différents groupés) ; une facture n'appartient qu'à **un seul** dossier. PRO :
`FacturesDossier` (bloc de la fiche, entre l'en-tête et les indicateurs), `DataTable({hauteur:
'fenetre', recherche: false})` — **aucun tableau qui défile dans la fenêtre** : toutes les lignes, la
fenêtre défile —, `Bouton({blocages})`, `Confirmer`, `Fenetre` + `ChoixFacture` (5.4), rôles D, A.
Absent d'un dossier saisi à la main ou repris de l'ERP Fil (leurs factures se lisent dans l'en-tête).

| Élément | Élément PRO (composant) | Règle |
|---|---|---|
| Titre « Facture du dossier » / « Factures du dossier (N) » + « Ajouter une facture » | `strong` + `Bouton` (grisé avec la raison du serveur, `actions.ajouter_facture` : clos, annulé, saisi à la main) | caché sur un dossier annulé |
| Une ligne par facture, la première ajoutée d'abord : Facture (n° ; « libérée » sur un dossier annulé) · Fournisseur · Date · Montant (dans **sa** devise, jamais additionné) · Échéance (« réglée le … ») · Réceptions (liens) · Rapprochement (« conforme » ; `Badge` « écart x,x % » hors tolérance, infobulle « {montant} facturés pour {reçu} reçus (pesée × prix) » ; « montant non saisi ») · « Retirer » | `DataTable` (`FactureDossier` de la fiche, API-PRO 189) | C36 facture par facture |
| Dossier sans plus aucune facture | `Vide` « Plus aucune facture dans ce dossier : « Ajouter une facture » y fait entrer la marchandise d'une facture reçue. » | — |

| Geste | Rôles | Route API PRO | Confirmation / blocages | Effet |
|---|---|---|---|---|
| « Ajouter une facture » | D, A | `POST dossiers/{id}/factures` `{version, facture_id, local_confirme}` (253) | `Fenetre` « Ajouter une facture au dossier {n°} » : `Note` + `ChoixFacture` des factures d'« En attente » sans dossier, geste « Ajouter au dossier » (fournisseur marocain : `Confirmer` « … L'ajouter quand même à ce dossier d'importation ? » · « Oui, l'ajouter ») ; refus serveur : facture déjà dans un dossier (409 qui le nomme ; deux postes : le perdant nomme le gagnant), version périmée, période close, dossier saisi à la main | toute sa marchandise libre entre ; toast « Facture {F} ajoutée au dossier {n°} : N lot(s), N kg. » ; journal « facture ajoutée » |
| « Retirer » (danger) | D, A | `DELETE dossiers/{id}/factures/{fid}?version=` (254) | `Confirmer` « Retirer la facture {F} du dossier {n°} ? Sa marchandise (N ligne(s)) en sort et attendra de nouveau son dossier ; les frais restent au dossier et se répartissent sur ce qui reste. » · « Oui, retirer la facture » ; grisé avec la raison du serveur (`retrait`) : « N frais porte(nt) sur une marchandise de la facture {F} : les affecter à tout le dossier (onglet Frais, « Porte sur »), ou les retirer, avant de retirer la facture — sinon ils sortiraient avec elle. », clos, annulé | sa marchandise attend de nouveau (« En attente de dossier ») ; toast « Facture {F} retirée du dossier {n°} : sa marchandise attend de nouveau son dossier. » ; journal « facture retirée » |

Ailleurs : « Détacher la réception » (5.8) retire aussi la facture dont c'était la dernière réception
au dossier (elle attend de nouveau) ; « Annuler le dossier » libère toutes ses factures ; la liste
(5.2) et sa recherche citent toutes les factures (« Facture · réceptions », filtre « Fournisseur » :
celui d'une de ses factures) ; le panneau « Facture du fournisseur » d'une réception (4.x) mène à son
dossier quelle que soit la facture.

### 5.7 Fiche dossier › Par famille de fil — `/dossiers/:id?onglet=familles`

Gestion MP : onglet « Par famille de fil » → PRO : `DataTable` (pied de totaux), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Vide « Le dossier n'a pas encore de marchandise. » + lien « Ajouter une facture » (→ onglet `facture`, absent sans second camion) « , des lignes de réception, ou une saisie à la main. » | `Vide` ; liens seulement vers des onglets présents : « Second camion » si une facture attend, « Saisie à la main » si dossier à la main ; sinon « Sa marchandise a été détachée : elle revient par sa facture (Importations › En attente). » | lien mort supprimé (anom. 5.1) |
| Col. Famille de fil (gras) · Références · Lots · Poids (kg) · Achat MAD · Charges hors TVA (infobulle « toutes les charges sauf la TVA ») · Coût hors TVA (gras) · Achat / kg · Coût hors TVA / kg (gras) · Charges / achat (% ou « — ») | mêmes colonnes ; « Lots » = lots distincts | anom. 5.14 |
| Tri poids décroissant ; pied « Tout le dossier » (Lots, Poids, Achat, Charges, Coût, Achat/kg, Coût/kg, `surcout`) ; non cliquable ; cadre dialogue | idem ; ligne cliquable → `?onglet=marchandises&q={famille}` | accès au détail |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Lien « Ajouter une facture » (vide) | D, A | — | — | → `?onglet=facture` seulement s'il existe (anom. 5.1) |
| Clic ligne (nouveau) | D, A | — | — | → Marchandises filtrées |

### 5.8 Fiche dossier › Marchandises — `/dossiers/:id?onglet=marchandises&q=`

Gestion MP : onglet « Marchandises » (+ `CoursLigne`) → PRO : `Recherche`, `Prix`/`Nombre` (cours), `DataTable` de saisie, `Note`, `LienDocument`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Recherche (« Référence, lot, famille, facture, réception, commentaire… » : référence, lot, fournisseur, famille, facture, réception, commentaire) | `Recherche` dans `?q=` (« observations » au lieu de « commentaire ») | vocabulaire |
| Par devise ≠ MAD (modifiable) : « 1 USD = [placeholder = cours du jour 4 déc.] MAD [Appliquer aux USD] » (infobulle « Le cours payé à la banque pour toutes les marchandises en USD du dossier ») | `Nombre` + `Bouton({manque: ["Saisissez le cours"]})` par devise | raison du grisé (anom. 5.7) |
| « Cours des bons (N) » (si des lignes ont un cours de bon ≠ leur cours) | `Bouton` | — |
| Notes : (rouge) « N ligne(s) à un cours éloigné de plus de 5 % du cours du jour … » ; « N marchandise(s) en devise sans cours payé : elles sont comptées au cours du jour des réglages (*). La clôture l'écrira sur la ligne … » ; « N marchandise(s) au cours de leur bon : … » ; (rouge, par devise) « Les marchandises en USD n'ont pas toutes le même cours (10,1 et 10,2 MAD) — un second camion arrivé après une clôture ? … » ; « Chaque marchandise entre à sa **pesée × son prix** … (X DEV facturés, Y reçus, écart z %) … ne change pas le coût. » | `Note` (mêmes textes, alertes serveur) | — |
| Col. « Référence » (note « famille · facture F · REC-… » / « famille · saisie à la main ») | `LienDocument` référence → `/stock/matieres/:id`, REC → `/receptions/:id` | liens (§ 6 GMP) |
| « Lot » (mono ou « — ») | `LienDocument` → `/lots/:id` | lien |
| « Poids » ; « Valeur facture » (2 déc. + devise ; « x,xxxx DEV / kg ») | `Montant` | — |
| « Cours payé » : MAD « — » ; lecture : cours 4 déc. + « * » si cours du jour (infobulle « cours payé » / « cours du jour (réglages) ») ; saisie : placeholder = cours appliqué + note « cours du jour * » / « cours du bon BC-… » / « +7 % / cours du jour » (rouge > 5 %) / « 1 USD = 10,1234 MAD » ; infobulles « cours du jour : X MAD » / « cours figé du bon BC-… : X MAD » / « cours retenu : X MAD » ; quitter envoie le cours (vide → 0) | `Nombre` ; **vide → `null`** (« cours du jour ») ; « BC-… » en `LienDocument` → `/commandes/:id` | point tranché ; lien bon |
| « Achat MAD » (infobulle « x % de la valeur du dossier ») ; « Charges hors TVA » (infobulle d'en-tête « toutes les charges sauf la TVA ; le détail par poste en infobulle » ; note % ; infobulle cellule « Fret : 1 234,56 MAD » par poste ou « aucun frais ») ; « Coût hors TVA » ; « Coût hors TVA / kg » (infobulle « Au kilo, le cuir, les franges et le ruban compris » ; note « achat x,xx » ; « négatif : un avoir de trop » / « frais hors norme ») | idem ; `Badge` | — |
| « Commentaire » (≤ 300, « bobines abîmées, écart de poids… » ; blur) | « Observations » `Saisie` `maxLength` 300 | anom. 5.14 |
| Geste de ligne : « Détacher la réception » (1re ligne d'une réception), note « avec REC-… » (infobulle « Une marchandise reçue sort avec toute sa réception »), « Retirer » (ligne à la main) | idem | — |
| Pied « Tout le dossier » (Poids, Achat, Charges, Coût, Coût/kg) ; vide « Aucune marchandise ne correspond. » / « Aucune marchandise dans ce dossier. » | pied ; `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Appliquer aux {DEV} » | D, A | `PUT dossiers/{id}/cours` `{cours, devise}` | `manque` « Saisissez le cours » ; refus « Le dossier mêle EUR, USD : donner le cours de chaque devise à part. », « Aucune marchandise en devise dans ce dossier. », « Aucune marchandise en {DEV} dans ce dossier. », période close « (cours refusé) », 422 > 1000 | toast « Cours {x,xxxx} MAD appliqué à toutes les marchandises en {DEV}. » |
| « Cours des bons (N) » (infobulle « Remettre sur chaque ligne le cours figé de son bon de commande à la confirmation des prix ») | D, A | `POST dossiers/{id}/cours-des-bons` | refus « Aucune ligne de ce dossier ne vient d'un bon au cours figé. », période close | toast « Cours figés des bons remis sur les lignes. » |
| Cours d'une ligne (blur) | D, A | `PUT dossiers/{id}/lignes/{lid}` `{cours | null}` | refus « Marchandise introuvable dans ce dossier. », « Une marchandise facturée en MAD n'a pas de cours. », période close | `null` au lieu de 0 ; « Enregistré à … » |
| Commentaire d'une ligne (blur) | D, A | `PUT dossiers/{id}/lignes/{lid}` `{version, commentaire}` | ≤ 300 | — |
| « Détacher la réception » (danger ; infobulle « Une marchandise reçue sort du dossier avec toute sa réception — pour annuler la réception ou corriger le numéro de sa facture. Les frais payés restent au dossier. ») | D, A | `POST dossiers/{id}/detacher` `{reception_id}` | `Confirmer` « Détacher la réception {REC} (N ligne(s)) ? Sa marchandise attendra de nouveau son dossier ; les frais restent à celui-ci. » · « Non » · « Oui, détacher » ; `Bouton({blocages})` « N frais porte(nt) sur une marchandise de la réception {REC} : les affecter à tout le dossier (onglet Frais, « Porte sur ») avant de la détacher … » ; refus « Réception inconnue. », « La réception {REC} n'est pas dans le dossier {n°}. », période close | blocage annoncé avant le clic ; effet sur répartition figée gardé ; toast « Réception {REC} détachée : sa marchandise attend de nouveau son dossier, les frais restent ici. » |
| « Retirer » (ligne à la main ; infobulle « Retirer cette marchandise du dossier ») | D, A | `DELETE dossiers/{id}/lignes/{lid}` | `Confirmer` « Retirer cette ligne ? » · « Non » · « Oui, retirer » ; `Bouton({blocages})` « N frais porte(nt) sur cette seule marchandise : les affecter à tout le dossier, ou les retirer, avant de la retirer. » ; refus ligne reçue « Une marchandise reçue ne sort pas seule du dossier : elle sort avec toute sa réception {REC} … », période close | toast « {réf.} retirée du dossier. » |

### 5.9 Fiche dossier › Frais — `/dossiers/:id?onglet=frais`

Gestion MP : onglet « Frais » (2 encarts de contrôle + tableau + ligne bleue) → PRO : `Carte` × 2 (ton `ecart`), `DataTable` de saisie, `Selecteur`, `Montant`, `DateChamp`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Encart « Droits de douane » (rouge si écart ; infobulle « Droits attendus = taux du code douanier de chaque matière × sa valeur en douane (achat + fret). Le code se porte sur la fiche matière. ») : « saisis {N} · attendus **{N}** » ; rouge « écart {±N MAD} » (infobulle « Vérifier la quittance, la valeur déclarée ou le code douanier des matières ») ; note « rien d'attendu : N matière(s) sans code actif » (infobulle + liste, « (code désactivé) ») | `Carte` ; écart lu sur `ecart_droits` serveur ; texte « (achat + fret + assurance) » ; matières sans code en `LienDocument` → `/matieres/:id` | anom. 5.3, 5.4 ; lien pour poser le code |
| « Proposer les droits » (attendus connus, aucun DD, modifiable ; infobulle « Pré-remplir un frais « Droits de douane » au montant attendu, à vérifier sur la quittance ») → ligne d'ajout DD, montant arrondi au centime, commentaire « proposé par les codes douaniers » | `Bouton` ; observations « proposé par les codes douaniers » | — |
| Encart « TVA à l'importation » (infobulle « Attendue = 20 % (taux réglé) × (valeur en douane + droits + TPI), … la TPI 0,25 % … Écart toléré : 5 % … ») : « saisie {Σ récupérables} · attendue **{N}** » (« — » sans marchandise, infobulle « Sans marchandise, pas de valeur en douane : rien n'est attendu ») ; rouge « écart {±N MAD} » (« Au-delà de l'écart toléré : vérifier la quittance de douane ») | `Carte` : « saisie » = **poste TVA seul** (+ note « autres récupérables : N MAD » s'il y en a) ; cadre rouge et écart sur la même valeur ; taux TVA, TPI et tolérance lus aux réglages | anom. 5.2, 5.4 |
| Col. « Poste » (liste « {libellé} — {hors coût | à la valeur | au poids} », enregistré aussitôt ; lecture : libellé + « récupérable ») | `Selecteur` | — |
| — (nouveau, lot TAUX-FRAIS) Col. « Taux » entre Poste et Montant ; ligne d'ajout « Taux (%) » entre Poste et Montant, note sous le champ « 20 % de 69 804,00 MAD (valeur en douane + droits + TPI) » | `Nombre` (% , 4 déc., ]0 ; 100]) ; base : valeur en douane (`valeur_douane_mad`) du dossier ou de la marchandise visée, + droits et TPI saisis (postes `droits`, `tpi`) pour un poste de nature `tva` ; montant proposé = arrondi(base × taux / 100, 2) tant qu'il n'est pas tapé à la main (vidé : recalculé) ; frais enregistré : montant affiché tel quel, **seul un taux changé** le recalcule (et l'enregistre) ; lecture « 20 % » ou « — » | demande de Mohamed (12/10/2026) : le serveur garde le taux pour mémoire, ne recalcule jamais le montant |
| « Montant (MAD) » (classe `manque` si vide ; blur ; lecture 2 déc.) | `Montant` ; vidé → valeur précédente rétablie + message « Un frais a un montant : pour l'enlever, « Retirer ». » | anom. 5.6 |
| « Porte sur » (« Tout le dossier » / « {réf.} · lot {lot} » ; « ? » si introuvable) | `Selecteur` | — |
| « Répartition » (« hors coût (récupérable) » / « sur cette marchandise » / « figée (clé d'avant son changement) » / « à la valeur » / « au poids ») | texte calculé ; libellé figé unique « figée (clé d'avant son changement) » (écran et export) | anom. 5.14 |
| « Prestataire », « Pièce », « Date de la pièce », « Échéance » (lecture : + « réglé le jj/mm/aaaa »), « Commentaire » ; « Retirer » | `Saisie`, `DateChamp` ; « Observations » ; **« réglé le » affiché aussi en saisie** ; frais réglé : poste, montant, porte sur, retrait **bloqués** (« Frais réglé le … : annuler d'abord le règlement (Analyse › Échéancier) ») | anom. 5.5 (I20) |
| Valeur modifiée ailleurs remplacée, champ en cours non écrasé | identique | — |
| Ligne d'ajout (« la ligne bleue ») : Poste (1er), Montant (« avoir : négatif »), Porte sur (« Tout le dossier »), Répartition, Prestataire (« transitaire, transporteur… »), Pièce (« n° de facture, quittance »), Date de la pièce, Échéance, Commentaire ; « Ajouter », « Effacer » (« Vider la ligne d'ajout ») | ligne d'ajout `DataTable` (ton accent) | — |
| Pied « Charges hors TVA » · Σ non récupérables · « dans le coût · TVA récupérable, hors coût : {Σ} MAD » | pied de totaux | — |
| Vide lecture « Aucun frais saisi : le coût hors TVA est celui de la facture. » ; modifiable « Aucun frais encore : le coût hors TVA est celui de la facture. Saisir droits, fret, transitaire, banque… dès que les pièces arrivent, sur la ligne bleue. » | `Vide` (« sur la ligne d'ajout ») | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Proposer les droits » | D, A | — (remplit la ligne d'ajout) | visible si attendus connus et aucun DD | — |
| « Ajouter » (frais) | D, A | `POST dossiers/{id}/frais` `{version, poste_id, montant, ligne_id, prestataire, piece, date_piece, echeance, commentaire}` | `Bouton({manque: ["Montant", "Poste"]})` ; refus « Poste de frais inconnu … », « Un frais a un montant (un avoir se saisit en négatif). », « La marchandise visée n'appartient pas à ce dossier. », « Ce frais rendrait {réf.} négatif ({N} MAD) : … », période close « (frais refusé) », 422 bornes (±1e9, pièce 64, prestataire 120, observations 300, « date hors période ») | raison du grisé (anom. 5.7) ; toast « Frais « {libellé} » ajouté. » |
| « Effacer » | D, A | — | brouillon non vide | — |
| Modifier un frais (poste, porte sur aussitôt ; montant, textes, dates au blur) | D, A | `PUT dossiers/{id}/frais/{fid}` | refus « Frais introuvable dans ce dossier. » + contrôles de l'ajout ; `blocages` frais réglé | autre montant/ligne efface la répartition figée (gardé) |
| « Retirer » (frais ; infobulle « Retirer le frais « {libellé} » de {N,NN} MAD ») | D, A | `DELETE dossiers/{id}/frais/{fid}` | `Confirmer` « Retirer ce frais ? » · « Non » · « Oui, retirer » ; refus ligne négative, période close ; `blocages` frais réglé | toast « Frais « {libellé} » retiré. » |

### 5.10 Fiche dossier › Échéancier — `/dossiers/:id?onglet=echeancier`

Gestion MP : onglet « Échéancier » → PRO : `DataTable` groupé par mois, `Badge`, `Montant`, rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Infobulle du tableau « Ce que le dossier engage à payer, mois par mois … Les devises ne s'additionnent pas. » ; vide « Ni facture de marchandise, ni frais dans ce dossier : rien à payer encore. » | idem ; `Vide` | — |
| Groupes « **octobre 2026** » / « **Sans échéance** · lien « la saisir sur le frais » (celle d'une facture de marchandise se saisit à la réception) » ; total « à payer 12 345,00 USD · 3 000,00 MAD » / « tout est réglé » | lignes de groupe ; liens → `?onglet=frais` et `/receptions/:id` (panneau facture) | lien vers la réception |
| Col. Échéance · Nature (« marchandise » accent / « frais » neutre) · Quoi (« Facture {n°} » / poste) · Tiers · Pièce (+ « du {date} ») · Montant (+ « estimé », infobulle « La facture n'a pas de montant saisi : ce que sa marchandise au dossier a apporté, pesée × prix ») · Devise · Règlement (« réglé le … » / « à payer ») | mêmes colonnes | — |
| Facture d'origine perdue si toutes ses réceptions sont détachées (en-tête la montre encore) | même source que l'en-tête : facture d'origine affichée « marchandise détachée », sans montant à payer | anom. 5.19 |
| Aucun geste de règlement (Analyse › Échéancier) | idem ; lien « Régler dans Analyse › Échéancier » → `/analyse?onglet=echeancier&q={pièce}` | lien |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Lien « la saisir sur le frais » | D, A | — | — | → `?onglet=frais` |

### 5.11 Fiche dossier › Pièces jointes — `/dossiers/:id?onglet=pieces`

Gestion MP : onglet « Documents » (`PiecesJointes objet="dossier"`) → PRO : onglet « Pièces jointes » (`PiecesJointes`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Note « La facture du fournisseur, la déclaration en douane (DUM), le connaissement, le certificat d'origine, les factures de frais et les quittances : tout ce qui justifie le coût du dossier, même clos. » | `Note` | libellé d'onglet unifié |
| « Joindre un document… » (« Envoi… ») + « ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; formats `.pdf, image/*, .txt, .csv, .xlsx, .xls, .ods, .docx, .doc, .odt, .zip` ; contour pointillé | `PiecesJointes` | — |
| Col. Document (lien `/api/piece/{id}/fichier`, « Télécharger le document ») · Genre (PDF / Image / Tableur / Document / Archive / Texte) · Taille (o / Ko / Mo) · Par · Joint le · (Retirer) ; vide « Aucun document joint. » | idem | — |
| Messages « « {nom} » est trop lourd : 20 Mo au plus. », « « {nom} » joint. », « N documents joints. », « « {nom} » retiré. » | toasts | — |
| Modifiable même clos (dépôt et retrait) | dépôt permis même clos ; retrait refusé sur clos/annulé | anom. 5.20 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Joindre un document… » / glisser | D, A | `POST pieces` `{objet: 'dossier', id, fichier}` | refus type / poids | — |
| Télécharger | D, A | `GET pieces/{id}/fichier` | — | — |
| « Retirer » (infobulle « Retirer « {nom} » de la liste (le retrait est tracé) ») | D, A | `DELETE pieces/{id}` | `Confirmer` « Retirer ce document ? » · « Oui, retirer » ; `blocages` « Dossier clos : le rouvrir pour retirer une pièce. » | anom. 5.20 |

### 5.12 Fiche dossier › Second camion d'une facture — `/dossiers/:id?onglet=facture`

Gestion MP : onglet « Second camion de la facture » → PRO : `Note` + `ChoixFacture` (5.4), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Note « La facture {n°} est arrivée en plus d'un camion : ce qui est reçu depuis rejoint son dossier. » ; vide pour un dossier repris (« La facture  est arrivée… ») | dossier à facture : même note ; dossier repris : « Les factures de ce dossier sont arrivées en plus d'un camion : ce qui est reçu depuis rejoint ce dossier. » | anom. 5.11 |
| Présent si modifiable et second camion (lu **sans** locaux) | lu sur `a_rattacher` de `GET dossiers/{id}`, locaux compris | anom. 5.10 |
| `ChoixFacture` (cadre dialogue), action « Ajouter au dossier » | `ChoixFacture` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Ajouter au dossier » | D, A | `POST dossiers/{id}/rattacher` `{facture_id}` | refus (§ 8 GMP) : clos ; « Ce dossier est saisi à la main (d'avant la mise en service) : une marchandise reçue entre par sa facture, dans le dossier de cette facture. » ; « La facture {G} n'est pas dans le dossier {NN/AA} : l'y ajouter d'abord (« Ajouter une facture », toute sa marchandise entre), ou elle ouvre son propre dossier. » (12/10/2026 ; avant : « Un dossier, une facture : … ») ; « Le dossier {NN/AA}, repris de l'ancien ERP, ne prend que la suite des factures qu'il porte déjà. … » ; « Rien à rattacher. » ; facture épuisée ; concurrence ; période close « (rattachement refusé) » | rattachement par `reception_lignes` retiré de l'API (anom. 5.13) ; toast « Second camion de la facture {F} ajouté : N lot(s), N kg. » ; journal « plusieurs cours : … » gardé |

### 5.13 Fiche dossier › Saisie à la main — `/dossiers/:id?onglet=main`

Gestion MP : onglet « Saisie à la main » (dossier d'avant la mise en service) → PRO : `Form` (`SelecteurMatiere`, `Saisie`, `Selecteur`, `Nombre`, `Prix`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Note « Pour un dossier d'avant la mise en service : la marchandise n'a pas de réception dans Gestion MP. Un numéro de lot inconnu est créé (sans stock) : un stock d'ouverture saisi sous le même numéro prendra le coût de ce dossier. » | `Note` | — |
| « Matière » (actives ; « réf. — désignation », détail fournisseur ; « Quelques mots de la référence ou de la désignation… ») → devise, prix, valeur | `SelecteurMatiere` | — |
| « Numéro de lot » (« facultatif » ; ≤ 80) | `Saisie` | — |
| « Fournisseur » (« par défaut, celui de la matière » ; « {fournisseur} (matière) » / « Celui de la matière » + actifs) | `Selecteur` | — |
| « Poids (kg) » (> 0 ; recalcule valeur) ; « Prix ({DEV} / kg) » (recalcule valeur) ; « Valeur facture ({DEV}) » (« le total de la ligne » ; recalcule prix 4 déc. ; ≥ 0) | `Quantite`, `Prix`, `Montant` liés | — |
| « Devise » (actives + en cours, « USD — Dollar ») | `Selecteur` | — |
| « Cours payé (MAD pour 1 {DEV}) » (« vide : le cours du jour des réglages » ; 0-1000 ; si ≠ MAD) | `Nombre` ; vide = `null` | point tranché |
| « Commentaire » (≤ 300) | « Observations » | anom. 5.14 |
| Après succès : brouillon vidé, garde fournisseur, devise, cours | identique | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Ajouter au dossier » | D, A | `POST dossiers/{id}/lignes` `{version, matiere_id, lot_numero, fournisseur_id, quantite_kg, valeur_devise, devise, cours|null, commentaire}` | `Bouton({manque: ["Matière", "Poids", "Valeur"]})` ; refus « Le dossier de la facture {F} porte ce qu'elle a apporté, tel que reçu : la saisie à la main est réservée aux dossiers d'avant la mise en service. », « Le dossier {n°} porte des réceptions : … », « Le lot « {lot} » de {réf.} est arrivé par la réception {REC} : son coût vient du dossier de sa facture. … », « Matière inconnue. », « Devise inconnue : « X ». », « Fournisseur inconnu. », période close « (marchandise saisie à la main refusé) » | ancienne route `/ligne-manuelle` ; raison du grisé (anom. 5.7) ; toast « {réf.} ajoutée au dossier[, lot {lot}]. » |

### 5.14 Fiche dossier › Historique (nouveau) — `/dossiers/:id?onglet=historique`

Gestion MP : journal général seulement → PRO : `Historique` (`GET historique/dossier/{id}`), rôles D, A ; entrées avant/après (ouverture, en-tête, marchandises, cours, frais, détachement, clôture, réouverture, annulation, frais figés). Gestes : aucun.

### 5.15 Analyse › Coût de revient (filtres, indicateurs, vues) — `/analyse?onglet=revient&vue=groupe|lots|qualite&axe=&q=&statut=&du=&au=&qualite=&matieres=&combinaisons=&composition=&titrage=&type=&couleur=&fournisseur=`

Gestion MP : onglet « Coût de revient » de `/analyse` (`AnalyseRevient.tsx`, sous-titre « Ce que chaque fil a coûté rendu usine, frais d'importation répartis. ») → PRO : `/analyse?onglet=revient` (`Carte`, `Bascule`, `Filtres` liés, `Puces`, `Indicateurs`, `DataTable`, `ExportExcel`), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde `/analyse` `['achats']` ; serveur `ACHATS` ; rien ne change selon le rôle | `routes.ts` D, A | — |
| Adresse : seul `?onglet=revient` ; vue, axe, filtres hors adresse | tout l'état dans l'adresse (`useFiltresAdresse`) | anom. 5.16 (M74) |
| Données `GET /importations/analyse/revient?axe&q&debut&fin&statut&qualite&references&(composition…|selection)&detail` ; `GET /importations/analyse/qualite/{code}?debut&fin` ; résultats précédents gardés pendant le rechargement | `GET analyse/revient?…` ; `GET analyse/revient/qualites/{id}?du=&au=` ; `keepPreviousData` | par id de qualité |
| Carte « Ce que la matière importée a coûté, rendue usine » ; Bascule « Regroupé » / « Lot par lot » / « Recette d'une qualité » | `Carte` ; `Bascule` `?vue=` | — |
| « Exporter en Excel » (hors vue qualité ; infobulle « Le regroupement et le détail lot par lot dans un classeur » ; `cout-de-revient-AAAA-MM-JJ.xlsx`, feuilles « Par {axe} » + Total, « Lot par lot ») | `ExportExcel` → `GET export/revient?…` | — |
| Texte (« Dossier, référence, lot, fournisseur, couleur… »), envoyé 300 ms après la frappe ; serveur : mots sans accents dans numéro, libellé, référence, lot, fournisseur, nature, composition, type (code et libellé), titrage + unité, couleur, désignation | `Recherche` (`?q=`, même délai, même règle) | — |
| « + Ajouter une matière… » (infobulle « Ajouter une matière : l'analyse ne garde que les matières choisies ») → puces (× « Retirer cette matière ») | `SelecteurMatiere` + `Puces` (`?matieres=`) | — |
| (Regroupé) « Regrouper par » : référence, titrage (défaut), composition, type de fil, couleur, fournisseur, dossier, lot, rôle | `Selecteur` `?axe=` | — |
| Statut (« Statut du dossier ») : « Ouverts et clos » / « Dossiers clos » / « Dossiers ouverts » | `Segments` `?statut=` ; dossiers annulés jamais comptés | annulation |
| Période « Du … au … » (« Date d'arrivée du dossier ») ; sans date jamais exclu | `DateChamp` × 2 (`?du=&au=`) | — |
| Qualité « Toutes qualités » / « CODE — nom » (« Ne garder que les fils de la recette d'une qualité ») | `Selecteur` `?qualite=` | — |
| 5 listes liées « Toutes compositions », « Tous titrages », « Tous types de fil », « Toutes couleurs », « Tous fournisseurs » (tri naturel) | `Filtres` liés (A1) | — |
| « + Combinaison » (grisé sans critère ; « + Ajouter cette combinaison : la retenir, puis en composer une autre ; le résultat les réunit ») ; puces « Réunion de : » « PES · 1500 » (× « Retirer cette combinaison ») ; « + en cours : … » | `Bouton({manque: ["Choisissez au moins un critère"]})` ; `Puces` (`?combinaisons=` JSON) | raison du grisé |
| « Effacer les filtres » dès 2 filtres (tout vidé) | idem + « N critère(s) » | — |
| Règles : ET dans une combinaison, OU entre combinaisons ; qualité ∩ matières ; erreurs 400 (axe inconnu, sélection illisible, liste attendue, critère inconnu) ; 404 « qualité inconnue ou sans recette : « X » » | identique (schéma Pydantic) | — |
| KPI « Poids » (« N lot(s) ») ; « Coût hors TVA » (ok ; « x,xx MAD / kg · achat + charges ») ; « Achat » (« marchandise, en MAD ») ; « Charges hors TVA » (attention ; % + lien rouge « + N non répartis », infobulle « Frais saisis sans marchandise où se répartir, dans aucun coût : 03/26 (1 200 MAD), …. Cliquer pour ouvrir le dossier. » → **premier** dossier) ; « Coût TTC » (« dont TVA N MAD ») | `Kpi({formule})` ; « + N non répartis » ouvre une liste de `LienDocument` (un par dossier) | chaque dossier atteignable |
| Non répartis comptés pour un dossier s'il répond aux critères | identique | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Bascule de vue | D, A | `GET analyse/revient?vue=` / `GET analyse/revient/qualites/{id}` | — | `?vue=` |
| « Exporter en Excel » | D, A | `GET export/revient?…` | hors vue qualité | — |
| « + Ajouter une matière… » / × | D, A | `GET analyse/revient?matieres=` | — | — |
| « + Combinaison » / × | D, A | `GET analyse/revient?selection=` | `manque` sans critère | — |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |
| Choisir texte, axe, statut, période, qualité, listes liées | D, A | `GET analyse/revient?…` | — | dans l'adresse |
| « + N non répartis » | D, A | — | — | liste de liens au lieu du 1er dossier |

### 5.16 Analyse › Coût de revient › Regroupé — `/analyse?onglet=revient&vue=groupe&axe=`

Gestion MP : vue « Regroupé » → PRO : `DataTable` (pied « Total »), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Col. {libellé de l'axe} (gras, « — », titrage « valeur unité ») · Lots · Poids · Achat MAD · Charges hors TVA (infobulle %) · Coût hors TVA (gras) · Coût hors TVA / kg (+ « achat x,xx ») · TVA · Coût TTC · Dossiers (4 premiers n° boutons + « +N », infobulle liste) | mêmes colonnes ; dossiers en `LienDocument` | — |
| Tri coût hors TVA décroissant ; ligne cliquable (« Voir ses références une à une ») si axe composition/titrage/type/couleur/fournisseur : pose le filtre (titrage = 1er mot), axe → Référence | identique, état écrit dans l'adresse | — |
| Pied « Total » (> 1 ligne) ; vide « Aucune marchandise importée ne répond à ces critères. » (`colSpan` 11 pour 10 colonnes) | pied ; `Vide` (`DataTable` gère la largeur) | anom. 5.18 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Clic ligne (axe combinable) | D, A | `GET analyse/revient?axe=reference&…` | — | — |
| N° de dossier | D, A | `GET dossiers/{id}` | — | → `/dossiers/:id` en fenêtre sur l'analyse (fermer = retour à l'analyse filtrée) |

### 5.17 Analyse › Coût de revient › Lot par lot — `/analyse?onglet=revient&vue=lots`

Gestion MP : vue « Lot par lot » (`detail=true`, axe forcé référence) → PRO : `DataTable` (pagination serveur transparente si > 500 lignes), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Col. Dossier (lien → fenêtre ; « ouvert ») · Arrivée · Référence · Lot (« — ») · Fournisseur · Titrage · Poids (kg) · Achat MAD · Charges hors TVA (infobulle %) · Coût hors TVA (gras) · Coût hors TVA / kg (`revient_kg` + « achat x,xx » = `valeur_unite`) · TVA · Coût TTC | mêmes colonnes ; Dossier, Référence, Lot en `LienDocument` | liens matière et lot |
| Tri arrivée puis dossier décroissants ; pied « Total » ; vide « Aucune marchandise importée ne répond à ces critères. » ; non cliquable | identique | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Lien du dossier | D, A | `GET dossiers/{id}` | — | → `/dossiers/:id` (fenêtre sur l'analyse) |

### 5.18 Analyse › Coût de revient › Recette d'une qualité — `/analyse?onglet=revient&vue=qualite&qualite=ID&du=&au=`

Gestion MP : vue « Recette d'une qualité » → PRO : `Selecteur`, `DateChamp`, `Indicateurs`, `DataTable` (pied par rôle), rôles D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Qualité « Choisir une qualité… » / « CODE — nom » (« Qualité de tapis ») ; période ; note « N matière(s) importée(s) sur M dans la recette » ; sans qualité « Choisir une qualité : on croise sa recette … dans les dossiers d'importation. » | `Selecteur` ; `Note` ; `Vide` | — |
| KPI « Coût matière / m² » (ok ; « recette × coût hors TVA de chaque fil · x,xxx kg / m² ») ; « Coût / kg de tapis » (« pondéré par la recette · sans {rôles} » / « … (rôles en kilos) ») ; « Recette couverte » (attention < 99,9 % ; « du poids : N fil(s) importé(s) sur M ») ; « Poids importé » (« N lot(s) · {coût} hors TVA ») | `Kpi({formule})` (formules `analyse_import.py:325-415` dans `aide.json`) | — |
| Col. Référence · Rôle · Part du rôle (« … les parts d'un rôle font 100 % ») · kg / m² (« Poids du rôle au m² × part du fil ») · Lots · Poids · Achat MAD · Charges hors TVA · Coût hors TVA · Coût hors TVA / kg · Coût / m² (« kg au m² (un cuir, des franges, un ruban : leurs ml/m² × la densité) × coût hors TVA au kilo ») · Dossiers | mêmes colonnes ; lien qualité → `/qualites/:id` | — |
| Pied par rôle « Rôle X » · « N fil(s) importé(s) sur M » · kg/m² · « aucun fil importé : rôle hors du coût calculé » / « coût connu sur x % du rôle, étendu au reste » / « coût connu pour tout le rôle » + « · rôle au mètre (ml/m²), hors du poids au m² » · coût/m² ; dernière ligne « Coût matière de la qualité » | pied identique | — |
| Vide « Aucun fil de cette recette n'a encore été importé dans un dossier. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Choisir la qualité / la période | D, A | `GET analyse/revient/qualites/{id}?du=&au=` | — | dans l'adresse |

### 5.19 Réglages › Postes de frais — `/reglages?onglet=postes`

Gestion MP : `/reglages?onglet=postes` (`ReglagesPostesFrais.tsx`, onglet court « Frais », direction seule) → PRO : `/reglages?onglet=postes` (`Carte`, `DataTable`), rôles D (écriture), A (lecture).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Onglet réservé à la direction (achats : Devises seul) ; serveur GET `ACHATS`, écritures `DIRECTION` | onglet visible D et A ; gestes d'écriture D seuls (A : lignes en lecture, fenêtre sans boutons) | contrat |
| Sous-titre « Les frais d'un dossier d'importation : récupérables ou non, répartis à la valeur ou au poids. » | `EnTete` du réglage | — |
| Données `GET /postes-frais/complet` (avec usage) ; `GET /postes-frais` (liste simple) ; chargement « … les postes de frais… » ; erreur | `GET postes-frais` (usage compris, `complet` fondu) | contrat |
| Carte « Postes de frais d'importation », « Nouveau poste » ; note « Un frais global d'un dossier se répartit … Changer une clé recalcule les dossiers ouverts ; les dossiers clos gardent leur répartition. Cliquer sur un poste pour le modifier. » | `Carte` + `Note` | — |
| Col. Ordre · Code (mono + « calculs », infobulle « Lu par les calculs du dossier (TVA attendue) : il ne se supprime pas et garde sa nature ») · Libellé · Répartition (« — » / « au poids » / « à la valeur ») · Nature (« récupérable, hors coût » / « coût ») · Frais saisis · Dossiers ouverts · Dossiers clos | mêmes colonnes ; `Badge` | — |
| Tri ordre puis code ; ligne cliquable (« Modifier le poste ») ; pas de recherche ni de vide | idem ; `Recherche` (code, libellé) ; `Vide` « Aucun poste de frais. » | ajouts mineurs |
| Où les postes s'affichent ailleurs : liste « Poste » du dossier, infobulle Charges, « Quoi » de l'échéancier, feuille « Frais » de l'export | identique | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau poste » | D | — | — | → `?onglet=postes&poste=nouveau` |
| Clic ligne | D, A | `GET postes-frais` | — | → `?onglet=postes&poste=ID` (A : lecture) |

### 5.20 Poste de frais (fenêtre) — `/reglages?onglet=postes&poste=ID|nouveau`

Gestion MP : fenêtre « Poste {CODE} — {libellé} » / « Nouveau poste de frais » (`sale`) → PRO : `Fenetre({sale})`, `Form`, `Onglets` (« Poste » · « Historique »), rôles D (A lecture).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Garde « Abandonner les modifications ? » | `Fenetre({sale})` texte standard | — |
| « Code » (mono, majuscules, ≤ 16 ; figé en modification ; aides « le code ne change pas : les frais le portent » / « lettres, chiffres ou « _ » (ex. MANUT) » ; serveur `[A-Z0-9_]{1,16}` « Le code d'un poste : lettres, chiffres ou « _ », sans espace (ex. MANUT). », « Le poste « X » existe déjà. ») | `Saisie` (contrôle à la frappe) | — |
| « Libellé » (≤ 80 ; « le libellé est obligatoire ») | `Saisie` | — |
| « Répartition » « à la valeur » / « au poids » (« au prorata de la valeur de chaque marchandise, ou de ses kilos ») | `Segments` | — |
| « Ordre » (0-999 ; « place dans les listes ; vide : à la fin ») | `Nombre` | — |
| Case « récupérable : hors du coût (comme la TVA) » (grisée si système ou porté par un clos ; notes « Nature figée : les calculs du dossier lisent ce poste ainsi. » / « Nature figée : il porte des frais dans N dossier(s) clos : créer un autre poste. » ; refus serveur correspondants) | `Interrupteur({manque/blocages})` | — |
| Message au changement de clé « Les N dossier(s) ouvert(s) seront recalculés {au poids}. Les N dossier(s) clos gardent leur coût : leurs frais de ce poste seront éclatés sur leurs marchandises, {à la valeur} (c'est tracé). » ; serveur : parts figées à l'ancienne clé (≥ 2 lignes), journal « frais figés », refus période close pour un ouvert touché | `Note` identique ; après succès, toast avec les nombres renvoyés par le serveur (`dossiers_ouverts`, `parts_figees`, lus tels quels — lot F5) | anom. 5.12 |
| — | onglet « Historique » (`GET historique/poste-frais/{id}`) | nouveau |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Supprimer » (danger) | D | `DELETE postes-frais/{id}` | `Bouton({blocages})` : « Ce poste sert aux calculs du dossier : il ne se supprime pas » / « Ce poste porte N frais dans des dossiers : il ne se supprime pas » (sinon « Supprimer ce poste, qui ne porte aucun frais ») ; `Confirmer` « Supprimer ce poste ? » · « Non » · « Oui, supprimer » ; refus « « X » sert aux calculs du dossier … », « Ce poste porte des frais dans des dossiers … », « Poste de frais introuvable. » | par id |
| « Annuler » | D | — | garde `sale` | — |
| « Enregistrer » / « Créer le poste » | D | `PUT postes-frais/{id}` / `POST postes-frais` | `Bouton({manque: ["Code", "Libellé", "Rien n'a changé"]})` ; refus ci-dessus | raison du grisé ; toast avec dossiers recalculés / figés |

### 5.21 Réglages › Codes douaniers — `/reglages?onglet=codes&q=`

Gestion MP : `/reglages?onglet=codes` (`ReglagesCodesDouaniers.tsx`, court « Douane », direction seule) → PRO : `/reglages?onglet=codes` (`Carte`, `Recherche`, `DataTable`), rôles D (écriture), A (lecture).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Sous-titre « Les positions du tarif douanier et leur taux de droits : de quoi prévoir et vérifier les droits d'un dossier. » | idem | — |
| Carte « Codes douaniers », « Nouveau code » ; note « … un dossier d'importation en déduit les droits attendus — taux × valeur en douane (achat + fret) — et signale l'écart avec la quittance. » | `Note` « (achat + fret + assurance) » | anom. 5.3 |
| Recherche (code, libellé ; « Code, libellé… ») ; compteur « N code(s) » | `Recherche` ; `Filtres` : État (actif / désactivé) | — |
| Col. Code (mono gras) · Libellé (« — ») · Taux de droits (% 1 déc.) · Matières (nb) · État (« actif » / « désactivé ») | mêmes colonnes ; « Matières » lien → `/catalogue?onglet=matieres&code={code}` | lien vers les matières |
| Ligne cliquable (« Modifier le code ») ; vide « Aucun code ne correspond. » / « Aucun code douanier. « Nouveau code » : 5402.47.00.00 (fils de polypropylène), son taux de droits… » | `lien` ; `Vide` | — |
| Chargement « … les codes douaniers… » | `Chargement` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau code » | D | — | — | → `?onglet=codes&code=nouveau` |
| Clic ligne | D, A | `GET codes-douaniers` | — | → `?onglet=codes&code=ID` |

### 5.22 Code douanier (fenêtre) — `/reglages?onglet=codes&code=ID|nouveau`

Gestion MP : fenêtre « Code douanier {code} » / « Nouveau code douanier » (`sale`) → PRO : `Fenetre({sale})`, `Form`, `Onglets` (« Code » · « Historique »), rôles D (A lecture).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Code » (≤ 20 ; aides « N matière(s) le portent : elles suivront la correction » / « chiffres et points (ex. 5402.47.00.00) » ; serveur « un code douanier s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00) », ≥ 2 car., « Le code douanier « X » existe déjà. ») | `Saisie` (contrôle à la frappe) | — |
| « Libellé » (`duo`, ≤ 160, « Fils de polypropylène… ») | `Saisie` | — |
| « Taux de droits (%) » (saisi en %, stocké 0-1, pas 0,1, « ex. 10 », aide « sur la valeur en douane : achat + fret » ; rouge « Un taux de droits va de 0 à 100 %. ») | `Nombre` ; aide « … : achat + fret + assurance (CAF) » | anom. 5.3 |
| Case « code actif (proposé dans la fiche matière) » ; un code désactivé compte « sans code » | `Interrupteur` | — |
| — | onglet « Historique » (`GET historique/code-douanier/{id}`) | nouveau |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Supprimer » | D | `DELETE codes-douaniers/{id}` | `Bouton({blocages})` « N matière(s) portent ce code : le leur retirer, ou le désactiver » (sinon « Supprimer ce code, qu'aucune matière ne porte ») ; `Confirmer` « Supprimer ce code ? » · « Oui, supprimer » ; refus « N matière(s) portent ce code : le leur retirer d'abord, ou le désactiver. » | — |
| « Annuler » | D | — | garde `sale` | — |
| « Enregistrer » / « Créer le code » | D | `PUT codes-douaniers/{id}` / `POST codes-douaniers` | `Bouton({manque: ["Code", "Taux de 0 à 100 %", "Rien n'a changé"]})` | raison du grisé |

### Anomalies GMP corrigées — Partie 5

- **5.1** Lien mort « Ajouter une facture » (onglet absent) et « des lignes de réception » (onglet disparu) → liens seulement vers les onglets présents ; texte juste quand la marchandise a été détachée.
- **5.2** « TVA saisie » à deux définitions (tous récupérables à l'écran, poste TVA au serveur) → une seule : poste TVA ; autres récupérables montrés à part.
- **5.3** Valeur en douane décrite « achat + fret » alors que le calcul ajoute l'assurance → tous les textes (encarts, codes douaniers, aide) disent « achat + fret + assurance (CAF) ».
- **5.4** Taux écrits en dur (TPI 0,25 %, 20 %) ; écart des droits calculé à l'écran seul → textes lus aux réglages ; `ecart_droits` calculé au serveur (seuils réglés).
- **5.5** Frais réglés modifiables sans le voir (le règlement se perd) → « réglé le » affiché en saisie ; poste, montant, ligne visée et retrait bloqués tant que le règlement n'est pas annulé.
- **5.6** Montant de frais vidé = silence → valeur rétablie + message « Un frais a un montant : pour l'enlever, « Retirer ». »
- **5.7** Boutons grisés sans raison (Clôturer, Ajouter un frais, Ajouter à la main, Appliquer aux {DEV}) ; Clôturer actif malgré des frais non répartis → `Bouton({manque, blocages})`, Clôturer grisé avec la raison.
- **5.8** Étiquette « à vérifier » incomplète → nourrie par la même liste d'alertes serveur que la clôture (frais hors norme du dossier, cours disparates, cours éloignés compris).
- **5.9** Indicateurs (tous les dossiers) ≠ pied (dossiers visibles) sans le dire → périmètres écrits (« tous les dossiers, ouverts et clos » ; « Total des N dossiers affichés »).
- **5.10** Second camion d'un fournisseur marocain invisible dans la fiche → `a_rattacher` de `GET dossiers/{id}` inclut les locaux.
- **5.11** « La facture  est arrivée… » pour un dossier repris → texte propre au dossier repris.
- **5.12** Retours serveur perdus (suppression sans message, `frais_perdus` et `dossiers_figes` non montrés ; PRO rend `dossiers_ouverts` et `parts_figees`) → toasts d'annulation et de changement de clé avec les nombres.
- **5.13** Code mort (`voletInitial`, `interdit`, `peut('achats')`, rattachement par `reception_lignes`, `lignes` de `ARattacher`, `numero`/`facture_id` ignorés par `PUT`) → supprimés ; schémas stricts (champ inconnu refusé).
- **5.14** Vocabulaire : « Commentaire » → « Observations » ; libellé de répartition figée unique ; « Lots » = lots distincts.
- **5.15** `ChoixFacture` : deux filtres non liés, sans « Effacer les filtres » → `Selecteur` fournisseur lié au texte + « Effacer les filtres ».
- **5.16** État de l'analyse et onglet de la fenêtre du dossier hors adresse → tout dans l'adresse (`?vue=`, `?axe=`, filtres, `/dossiers/:id?onglet=`).
- **5.17** Longueurs d'en-tête non bornées (422 technique) → `maxLength` tirés du schéma (160 / 32 / 2000).
- **5.18** `colSpan` faux dans la vue Regroupé → `DataTable` calcule la largeur du vide.
- **5.19** Échéancier qui perd la facture après détachement total, en-tête qui la garde → une seule source, facture d'origine affichée « marchandise détachée ».
- **5.20** Pièces jointes d'un dossier clos modifiables → joindre permis (I21), retirer refusé sur un clos ou annulé.

### Comptes de la partie 5

- Écrans : 4 — `/importations` ; Coût de revient (`/analyse?onglet=revient`) ; Postes de frais et Codes douaniers (`/reglages`).
- Onglets / sous-vues : 3 (page) + 1 (Bascule Clos/Annulés, nouvelle) + 2 (En attente) + 2 (création) + 8 (fiche dossier, dont « Historique » nouveau) + 3 (analyse) + 2 + 2 (onglets « Historique » des fenêtres poste et code, nouveaux) = 23.
- Fenêtres : 4 — Nouveau dossier, fiche dossier (sur `/importations` ou sur l'analyse), Poste de frais, Code douanier ; + panneau d'en-tête en ligne ; clôture en `FenetreConfirmation` ; composant partagé `ChoixFacture` (3 usages).
- Gestes : 63 lignes dans les tableaux « Gestes » (les 59 de GMP, dont « Supprimer le dossier » devenu « Annuler le dossier » ; nouveaux : Bascule Clos/Annulés, clic ligne famille, filtres de `ChoixFacture`, choix de qualité/période, « + N non répartis » en liste).
- Sections : 23 (5.0 à 5.22).
- Anomalies : 20, toutes traitées.

### Routes demandées par la partie 5 (reportées dans API-PRO § 1.24)

Aucune : toutes les routes employées figurent au contrat (`dossiers/*`, `dossiers/a-rattacher`, `analyse/revient*`, `export/dossiers`, `export/revient`, `postes-frais`, `codes-douaniers`, `pieces`, `historique/{objet}/{id}`). Paramètres nouveaux sur des routes existantes : `GET dossiers?statut=annule`, `GET dossiers/{id}` → champ `a_rattacher` (locaux compris), `PUT dossiers/{id}/lignes/{lid}` `{cours: null}`, `POST dossiers/{id}/annuler` `{motif}`, `POST dossiers/{id}/rouvrir` `{motif?}`.

---

### Comptes des parties 4 et 5

| | Partie 4 | Partie 5 | Total |
|---|---|---|---|
| Écrans (pages) | 3 | 4 | 7 |
| Onglets / sous-vues | 30 | 23 | 53 |
| Fenêtres | 8 | 4 | 12 |
| Documents (gardés / supprimés) | 2 / 1 | 0 | 2 / 1 |
| Lignes de gestes | 96 | 63 | 159 |
| Anomalies traitées | 21 | 20 | 41 |
| Routes manquantes | 1 | 0 | 1 |

Route manquante unique : `GET /api/export/plan-achat` (D, A).

---

## Partie 6 — Inventaire et opérations de stock (ouvertures, transferts, ajustements, retours, libérations)

Source : `docs/heritage/ECRANS.md` Partie 6 (inventaire, opérations, anomalies 1 à 25). « (an. n) » renvoie à l'anomalie n de cette partie.

Points tranchés appliqués :
- **(b) Inventaire.** La suspension ne porte que sur **son périmètre** : les matières comptées, dans son magasin (dans tous les
  magasins s'il est global) ; les autres matières du même magasin continuent de bouger. Un seul inventaire **ouvert par
  magasin** (un inventaire de tous les magasins exclut tout autre) : deux périmètres disjoints d'un même magasin ne
  s'ouvrent pas ensemble (lot D5). Abandonner **garde** l'inventaire au statut
  « abandonné » (son numéro INV reste, aucun trou). Un inventaire **validé** s'**annule** (Gestion MP corrigé, étape 17 : D, A,
  motif obligatoire) : ses ajustements sont contre-passés une fois, il garde son numéro au statut « Annulé ». Un second comptage
  fait par la même personne que le premier (ou que l'ouvreur) est **signalé** (pas refusé).
- **(c) Lot interne.** Plus de bouton qui prend un numéro d'avance (`POST /lots/numero-interne` supprimée) : une case « Lot interne »
  sur la ligne ; numéro `LOT-AAAA-NNNN` donné à la validation.
- **(d)** Transferts ouverts à L (`/operations?onglet=transfert`) ; libération de quarantaine D, A ; L peut mettre en quarantaine
  (motif imposé « Mise en quarantaine », observations obligatoires).

### Conventions communes (inventaire et opérations)

Gestion MP : `components/ui.tsx` (`Dialogue`, `Confirmer`, `useEnvoi`), `securite.py`, `services/stock.py` → PRO : `Fenetre`,
`Confirmer`, `Messages`, `Erreur`, `Chargement`, `DateChamp`, `Bouton({manque, blocages})`, moteur de stock du serveur.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `Dialogue … sale` : « Des modifications ne sont pas enregistrées. Les abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » | `Fenetre({sale})`, mêmes textes, pile (Échap ferme celle du dessus) | A4 |
| `Confirmer` « question · Non · Oui, … » | `Confirmer` sur la ligne | A3 |
| `useEnvoi` : `occupe`, erreur `Message erreur`, succès `Message succes`, message effacé au nouvel envoi | `Bouton({occupe})` ; succès en `Messages` ; erreur dans la fenêtre (`Erreur`) | — |
| 422 traduit « champ : texte ; … » ; injoignable « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). » | idem ; « Pas de réseau » | — |
| « Un instant — chargement : {quoi}… » | `Chargement` | — |
| Refus de droit « Cette action est réservée à : responsable achats. » (403) ; D passe partout | « Cette action est réservée à : {rôles}. » selon le registre | — |
| Dates : « Date trop ancienne (…) : vérifier l'année. » ; « Date dans le futur (…) : un mouvement se saisit le jour où il a lieu. » ; « La période jusqu'au … est close : … » | mêmes refus ; `DateChamp` borné (max aujourd'hui serveur, min après clôture) | anticipé (an. 18) |
| Moteur : « Une écriture de stock ne peut pas être nulle. » ; « Magasin inconnu. » ; « Le magasin « {code} » est désactivé : il ne reçoit plus rien. » | idem | — |
| Suspension : « L'inventaire {n°} est en cours sur « {code} » : les mouvements y sont suspendus jusqu'à sa validation. » (tout mouvement du magasin, ou de tous) | « L'inventaire {n°} compte « {réf} » dans « {code} » : ses mouvements y sont suspendus jusqu'à sa validation. » — seulement pour une matière du périmètre | (b) |
| Stock insuffisant « Le lot « {lot} » de « {réf} » ne porte que … Choisir un autre lot, ou faire d'abord un ajustement justifié si la matière est bien là. » | idem | — |
| Antidate (`couvert_a_sa_date`) : « … n'est entré dans « {code} » que le … » / « n'est jamais entré … » / « Au {date}, il n'y avait que … » | idem | — |
| « Un transfert va d'un magasin à un autre. » ; « Ce document a déjà été annulé. » | idem | — |
| « Un lot doit avoir un numéro : celui du fournisseur, ou « Lot interne ». » | « … celui du fournisseur, ou cocher « Lot interne ». » | (c) |

### Inventaire — `/inventaire?onglet=cours|passes`

Gestion MP : `pages/Inventaire.tsx` (`InventairePage`), `/inventaire` (`?onglet=passes`, `?inventaire=ID`) → PRO :
`/inventaire?onglet=cours|passes`, `Page`, `EnTete`, `Onglets`, `Carte`, `Note`, `Filtres`, `Recherche`, `DataTable` dans `Cadre`,
`Badge`, `ExportExcel` ; D, A (L, T → `EcranReserve`).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Menu « Stock › Inventaire » (A + D) ; garde : autre rôle → accueil + « L'écran demandé (/inventaire) est réservé à un autre rôle : vous êtes revenu à votre accueil. » | `BarreLaterale` ; `EcranReserve` même texte | — |
| « Ouvrir un inventaire » si `peut('achats')` | action `EnTete` (D, A) → `/inventaires/nouveau` | A5 |
| `GET /inventaires` (tous connectés ; MAD null pour L) ; écritures : achats | `GET inventaires` (C, `sans_prix`) ; écritures D, A | — |
| `?onglet=passes` (absent = cours) ; `?inventaire=ID` ouvre la fenêtre sur tout onglet ; après création : `inventaire=ID` | `?onglet=cours|passes` ; `/inventaires/:id` (fenêtre sur la liste, onglet gardé) ; après création → `/inventaires/:id` | A5 |
| Titre « Inventaire » ; sous-titre « On fige le stock théorique, on compte lot par lot, on valide : chaque écart devient un ajustement de stock tracé. Au-delà de la tolérance, un écart se justifie. » | idem | — |
| Pas d'indicateurs | pas d'indicateurs | — |
| Onglets « En cours de comptage » (compteur ouverts) · « Inventaires validés » (total − en cours) | « En cours de comptage » (ouverts) · « Inventaires clos » (infobulle « Validés, abandonnés et annulés » ; compteur validés + abandonnés + annulés) | (b), étape 17 |
| Erreur de lecture ; chargement « les inventaires » | `Erreur`, `Chargement` | — |

**Onglet « En cours de comptage »**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Inventaires en cours » ; info « Tant qu'un inventaire est ouvert, aucun mouvement ne s'écrit sur le magasin compté (…) — sur tous les magasins s'il porte sur tout le stock. Valider ou abandonner l'inventaire rend la main. » | `Note` : « Tant qu'un inventaire est ouvert, les matières qu'il compte ne bougent plus dans son magasin (dans tous les magasins s'il est global) : réceptions, sorties, transferts et retours de ces matières attendent. Les autres matières continuent de bouger. Valider ou abandonner l'inventaire rend la main. » | (b) |
| « Inventaire » : **numéro** + libellé en note | idem | — |
| « Date » (jj/mm/aaaa) | idem | — |
| « Magasin » : code ou « Tous les magasins » | idem | — |
| — | (nouveau) « Périmètre » : « Tout le stock » · « Par famille : {critères} » · « {n} matière(s) » · « Tournant » | (b) le périmètre fait la suspension |
| « Tolérance » (« 2 % ») | idem | — |
| « Lots comptés » « c / n » | idem | — |
| « Hors tolérance » : `Etiquette` critique si > 0 | `Badge` : critique s'il reste des écarts hors tolérance **sans justification**, attention s'ils sont tous justifiés, « 0 » sinon (même règle dans les deux onglets) | an. 23 |
| « Écart à ce stade » kg signé 1 déc., **non coloré** | « Écart (kg) » signé, coloré par signe comme l'onglet clos | an. 23 |
| « Valeur de l'écart » MAD net + « {abs} sans signe » ; infobulle « Au coût moyen (CMUP)… » | idem (`Montant`) | — |
| « Ouvert par » | « Par » | an. 11 |
| Pas de recherche, filtre, tri, pagination, pied | tri au clic ; défilement dans le `Cadre` | A2 |
| Ligne cliquable (« Ouvrir le comptage ») → `?inventaire=ID` | `lien` → `/inventaires/{id}` | A5 |
| Vide « Aucun inventaire en cours. « Ouvrir un inventaire » fige le stock d'un magasin (ou de tout le stock) pour le compter. » | `Vide` : « … fige le stock d'un périmètre pour le compter. » | (b) |

**Onglet « Inventaires clos » (`passes`)**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Inventaires validés » | « Inventaires clos » | (b) |
| `BarreRecherche` « Numéro, libellé, magasin, personne… » sur numéro, libellé, magasin, ouvert par, validé par, date ; pas dans l'adresse | `Recherche` (+ `?q=` dans l'adresse) | — |
| — | (nouveau) `Filtres` « État » : Validé / Abandonné / Annulé ; « Effacer les filtres » + « N critère(s) » dès 2 | (b), A1, étape 17 |
| « Inventaire », « Date », « Magasin », « Lots comptés » | idem + « Périmètre » | — |
| « Hors tolérance » : `Etiquette` attention | `Badge` (règle unique, voir plus haut) | an. 23 |
| « Écart total » kg signé, rouge < −0,001, vert > 0,001 | « Écart (kg) » idem | — |
| « Valeur de l'écart » MAD (au coût de chaque ajustement écrit) + « sans signe » | idem ; abandonné : « — » ; annulé : celle de ses ajustements d'origine (contre-passés depuis), comme Gestion MP corrigé | — |
| « Ouvert par » ; « Validé par » + date-heure | « Par » : « {ouvreur} · validé (ou abandonné) par {nom} le {jj/mm/aaaa hh:mm} »[ « · annulé par {nom} le … »] | an. 11, (b), étape 17 |
| — | (nouveau) « État » : `Badge` « Validé » ok / « Abandonné » neutre / « Annulé » neutre (comme Gestion MP corrigé) | (b), étape 17 |
| Ligne cliquable (« Voir les écarts ») → `?inventaire=ID` | → `/inventaires/{id}` | — |
| Vides « Aucun inventaire validé. » / « Aucun inventaire validé ne correspond. » | « Aucun inventaire clos. » / « Aucun inventaire ne correspond. » | — |
| Pas d'export | `ExportExcel` (route ajoutée, API-PRO § 1.24 : `GET /api/export/inventaires`) | an. 10 |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Ouvrir un inventaire » | D, A | — | — | → `/inventaires/nouveau` |
| Clic sur une ligne (en cours) | D, A | `GET inventaires/{id}` | — | → `/inventaires/{id}` ; 404 « Inventaire introuvable. » dans la fenêtre |
| Clic sur une ligne (clos) | D, A | `GET inventaires/{id}` | — | idem |
| Recherche (onglet clos) | D, A | — | — | dans l'adresse |
| (nouveau) Filtre État ; « Effacer les filtres » | D, A | — | — | A1 |
| (nouveau) « Exporter en Excel » | D, A | (route ajoutée, API-PRO § 1.24 : `GET /api/export/inventaires`) | — | an. 10 |

### Ouvrir un inventaire — `/inventaires/nouveau`

Gestion MP : `Inventaire.tsx:347-640` (`OuvrirInventaire`, Dialogue `tresLarge`) → PRO : `/inventaires/nouveau`,
`Fenetre({taille:'tresLarge', sale})`, `Form` (`Saisie`, `DateChamp`, `Selecteur`, `Nombre`, `Segments`, `Puces`,
`SelecteurMatiere`), `DataTable` (matières dues), `Note`, `Bouton({manque, blocages})`, `Confirmer` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /inventaires/defauts`, `GET /magasins`, `GET /articles`, `GET /soldes?magasin_id=`, `GET /inventaires/a-compter?magasin_id=` (tournant) | `GET inventaires/defauts`, `GET magasins`, `GET matieres`, `GET lots?magasin_id=`, `GET inventaires/a-compter?magasin_id=` | — |
| « Libellé » (placeholder « Inventaire {code} » / « Inventaire de fin de mois, tournant… », ≤ 120) ; vide → « Inventaire tournant » / « Inventaire {code} » / « Inventaire de tout le stock » | libellé auto selon **périmètre et magasin** : « Inventaire de tout le stock[ {code}] », « Inventaire par famille ({critères})[ — {code}] », « Inventaire de {n} matière(s)[ — {code}] », « Inventaire tournant[ — {code}] » | an. 16 |
| « Date du comptage » (aujourd'hui, max aujourd'hui, obligatoire) | `DateChamp` (max aujourd'hui serveur, min après clôture) | an. 18 |
| « Magasin compté » : « Tous les magasins » (vide) + magasins actifs « {code}[ (quarantaine)] — {stock} kg » | `Selecteur` idem | — |
| « Tolérance (%) » — « au-delà, l'écart se justifie ; proposée par les réglages » ; défaut réglage × 100 (2 %) ; vide → grisé ; non bornée à l'écran | `Nombre` borné 0…100 **à la frappe** | an. 18 |
| Périmètre « **Ce qu'on compte :** » radios : « Tout le stock[ de ce magasin] » (défaut) · « Par rôle, composition ou classe ABC » · « Certaines matières » · « Inventaire tournant (matières dues) » | `Segments` mêmes 4 choix | — |
| Famille : cases « Rôles » (« — » si aucun), « Compositions », « Classes ABC » (« A : l'essentiel de la valeur consommée » ; Classe A/B/C) ; note « Une matière est comptée si elle passe tous les critères cochés. » (ET entre familles, OU dedans) | `Puces` cochables, même note | — |
| « Certaines matières » : « Ajouter une matière à compter » (« Taper quelques mots de la référence… ») parmi matières à **stock global** > 0 ; « RÉF — désignation », « {kg} kg[ ≈ ml] en stock » ; puces « RÉF × » (« Retirer RÉF ») ; « Aucune matière choisie. » | `SelecteurMatiere` limité aux matières **en stock dans le magasin choisi** (ou partout si tous) ; `Puces` ; retirer une puce marque la saisie modifiée | an. 17 |
| Tournant : note cadence « A tous les 30 jours, B tous les 90 jours, C tous les 365 jours… » ; chargement « les matières dues » ; vide « Aucune matière n'est due : toutes ont été comptées à temps. » ; tableau (case · Référence · Rôle · Classe · Stock « kg[ ≈ ml] » · Dernier comptage « jj/mm/aaaa (il y a N j) » / « jamais compté » + magasins dus, infobulle « Un comptage vaut pour le magasin compté… ») ; décoché → ligne éteinte ; tri A→C, jamais d'abord, référence | `DataTable` dans `Cadre`, mêmes colonnes, tri et règle serveur (dû si > 0,001 kg et dernier comptage **validé avec quantité** ≥ cadence ou absent) | — |
| Info calculée : « Calcul… » ; « Les lots des matières retenues seront figés au théorique (la classe ABC se calcule à l'ouverture). » / « {N} lot(s) en stock seront figés au théorique. » | idem | — |
| « Pendant le comptage, les mouvements sont **suspendus** sur {le magasin CODE / tous les magasins} : réceptions, sorties…, transferts et retours attendront la validation (ou l'abandon) de l'inventaire. Ouvrir l'inventaire au moment de compter, pas avant. » | « Pendant le comptage, les mouvements **des matières comptées** sont suspendus dans {le magasin CODE / tous les magasins} : … Les autres matières continuent de bouger. Ouvrir l'inventaire au moment de compter, pas avant. » | (b) |
| Conflit : inventaire ouvert sur le même magasin, ou sur tous, ou ouverture sur tous avec un ouvert → « L'inventaire {n°} ({magasin}) est déjà ouvert sur ce périmètre : le valider ou l'abandonner d'abord. » + grisé | conflit = **un inventaire ouvert par magasin** (index unique `uq_inventaire_ouvert_magasin`, lot D5) : un inventaire ouvert sur ce magasin ou sur tous bloque l'ouverture, et un inventaire de tous les magasins attend que tout autre soit clos ; refus du serveur (409, Gestion MP corrigé C-07) « L'inventaire {n°} est déjà ouvert sur « {CODE} ». » / « … sur tous les magasins. » (pour une ouverture sur tous : « … : un inventaire de tous les magasins attend qu'il soit validé ou abandonné. »), repris tel quel sur « Ouvrir et figer le stock » grisé, suivi de « Le valider ou l'abandonner d'abord. » | (b) ; D5 décision 1 (et non des périmètres qui se recoupent) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| Choix du périmètre, cases, ajout / retrait d'une matière, décocher une matière due | D, A | — | — | retrait = saisie modifiée (an. 17) |
| « Annuler » (pied) | D, A | — | si modifié : garde `sale` (« Des modifications ne sont pas enregistrées. Les abandonner ? ») ; infobulle « Fermer sans ouvrir l'inventaire » | texte de garde unique |
| « Ouvrir et figer le stock » | D, A | `POST inventaires` `{libelle, date, magasin_id, tolerance, matieres[], roles[], compositions[], classes_abc[]}` | grisé, raison en infobulle **qui suit l'état** : « la date » · « la tolérance (0 à 100 %) » · « au moins un critère coché » · « au moins une matière » · « aucune matière due retenue » · « {n°} compte déjà ces matières » ; `Confirmer` « Figer {N} lot(s) {du magasin CODE / de tous les magasins} et suspendre leurs mouvements ? » · « Non » · « Oui, ouvrir l'inventaire » | an. 5, an. 16 ; succès → `/inventaires/{id}` ; refus repris : droits, dates, « Magasin inconnu. », « L'inventaire {n°} compte déjà ces matières dans ce magasin. » (409), « Matière inconnue : n° x, y. », « Classe ABC : A, B ou C. », « L'inventaire est daté du {date}, mais des lots qu'il fige ont bougé depuis : … » (409, 5 lots au plus) |

Serveur à l'ouverture : numéro `INV-{année}-{NNNN}` dès l'ouverture ; libellé ; une ligne par solde (lot × magasin) > 0 du
périmètre, théorique verrouillé à la lecture ; **périmètre enregistré** (matières × magasin) qui commande la suspension ; journal
« ouverture inventaire » « {n°} · N lot(s) figés ».

### Comptage d'un inventaire — `/inventaires/:id`

Gestion MP : `Inventaire.tsx:654-1115` (`Comptage`), `?inventaire=ID` → PRO : `/inventaires/:id` (fenêtre sur `/inventaire`),
`Fenetre({taille:'tresLarge', sale})`, `Badge`, `Indicateurs` (`Kpi`), `Onglets` (« Lots à compter » / « Pièces jointes »,
proposé `?onglet=lots|pieces`), `Filtres`, `Recherche`, `DataTable` de saisie dans `Cadre`, `Nombre`, `Saisie`, `BoutonImprimer`,
`ExportExcel`, `Bouton({manque, blocages})`, `Confirmer` ; lecture D, A ; saisie D, A si ouvert.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Saisie si ouvert ET achats ; validé = lecture seule | saisie si **ouvert** et D, A ; validé, abandonné **ou annulé** = lecture seule | (b) |
| Données `GET /inventaires/{id}` ; `GET /pieces/inventaire/{id}` | `GET inventaires/{id}` ; `GET pieces?objet=inventaire&id=` | — |
| Avant réception : fenêtre « Inventaire » + chargement ou « Inventaire introuvable. » | `Chargement` / `Erreur` | — |
| Titre « {n°} · {libellé} » + « Comptage en cours » (attention) / « Validé par {nom} » (ok) | + « Abandonné par {nom} » (neutre) ; « Annulé par {nom} » (neutre) | (b), étape 17 |
| Barre : « {magasin} · compté le {date} · tolérance {N %} · ouvert par {nom}[ · validé le {date heure}] » puis boutons à place fixe | « {magasin} · {périmètre} · compté le … · tolérance … · par {nom}[ · validé / abandonné le … par …][ · annulé le … par … : {motif}][ · motif d'abandon] » ; boutons à place fixe | (b), an. 11 |
| Indicateur « Lots figés » (lignes, lots trouvés compris) | `Kpi` idem | — |
| « Comptés » « c / n », détail « {%} du comptage », ok si tout compté | `Kpi` idem, formule | — |
| « Hors tolérance » (sur le retenu), détail « N sans justification » / « tous justifiés », ton rupture / attention / ok | `Kpi` idem | — |
| « À recompter » (premier comptage hors tolérance, sans recomptage), détail « {N} recompté(s) · le recomptage ajuste » | `Kpi` idem | — |
| « Écart total » « ±x,x kg », « retenu − théorique, lots comptés » | `Kpi` idem | — |
| (non montré) `cmup_mad`, `valeur_ecart_mad` | (nouveau) `Kpi` « Valeur de l'écart » MAD net + « sans signe » (CMUP tant qu'ouvert, coût de l'ajustement une fois validé) | an. 15 |
| (nouveau) | `Kpi` « Recomptages à quatre yeux » : « {n} par la même personne » (attention si > 0) | (b), an. 7 |
| Note de saisie « Saisir le poids compté en kg (…), ou les palettes et bobines : … Une ligne laissée vide n'est pas comptée et ne sera pas ajustée. Un écart hors tolérance **en rouge** demande une justification. » | `Note` identique | — |
| Bascule « Lots à compter ({n}) » / « Pièces jointes[ ({n})] », hors adresse | `Onglets` avec compteurs, `?onglet=lots|pieces` | REGLES § 1 |

**Sous-vue « Lots à compter »**

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `BarreRecherche` « Référence, lot, magasin… » (référence, désignation, lot, magasin) | `Recherche` | — |
| Vues : « Tous les lots (n) » (défaut si ouvert) · « À compter (n) » · « Comptés (n) » · « Avec un écart (n) » (défaut si clos) · « Hors tolérance (n) » · « À recompter (n) » · « Non enregistrés (n) » (saisie) ; note « {N} ligne(s) » ; **pas d'« Effacer les filtres »** | `Segments` mêmes vues et compteurs ; « Effacer les filtres » + « N critère(s) » dès 2 (recherche + vue) | an. 9 |
| « Référence » (+ désignation ; infobulle « RÉF — désignation ») | idem | — |
| « Lot » (mono) + « trouvé, non prévu » si théorique 0 ; **pas de lien** | `lien` → `/lots/{id}` (un lot trouvé non encore créé : pas de lien, note « créé à la validation ») | an. 12, an. 19 |
| « Magasin » (si tous magasins) | idem | — |
| « Théorique (kg) » 1 déc. + « ≈ N ml » + « ≈ N bobines » | « Théorique (kg) » **gardé** : terme d'inventaire reconnu (stock figé), distinct de « Prévu par la recette » interdit par REGLES § 5 ; exception notée au vocabulaire | an. 11 (tranché) |
| « Palettes » (saisie, « × {bob./palette} bob. », sinon « — ») ; « Bobines » (saisie, « × {poids, 4 déc.} kg », infobulle « Le poids de bobine du lot… ») | `Nombre` idem | — |
| « Compté (kg) » (placeholder « non compté » ; lecture : valeur ou « non compté ») | idem + note « par {nom} » (premier compteur **enregistré**) | an. 7 |
| « Recompté (kg) » (infobulle « Un écart hors tolérance se recompte, par une autre personne : ce second comptage ajuste ») ; saisie si compté et (à recompter ou déjà recompté) ; « par {nom} » + « — la personne qui a ouvert l'inventaire : un recomptage se fait à quatre yeux » | idem ; signalement `Badge` attention « même personne que le premier comptage » ou « … que l'ouvreur : un recomptage se fait à quatre yeux » (calculé au serveur, non bloquant) | (b), an. 7 |
| « Écart (kg) » signé, coloré seulement hors tolérance | idem | — |
| « Écart » (`Etiquette` « juste » / « {%} » / « non prévu », critique si hors tolérance) | en-tête « **Écart (%)** » | an. 11 |
| « Justification » (placeholder « Obligatoire : ce qui a été constaté » si hors tolérance ; rouge si < 3 car.) | `Saisie` idem | — |
| (non montré) valeur de l'écart par ligne | (nouveau) « Valeur de l'écart (MAD) » | an. 15 |
| Teintes `ligne-alerte` (hors tolérance sans justification), `ligne-modifiee` | idem | — |
| Vides « Aucune ligne dans cette vue. » / « Aucun lot en stock dans ce périmètre : ajouter les lots trouvés. » | `Vide` identiques | — |
| Pas de tri, pagination, pied | tri au clic ; pied de totaux (théorique, retenu, écart kg, valeur) | A2 |
| Calcul en direct : brouillon local par ligne ; palettes/bobines → Compté = arrondi 2 déc. de (palettes × bob./palette + bobines) × poids du lot ; saisir compté efface palettes/bobines ; retenu = recompté sinon compté ; écart ; hors tolérance (compté, |écart| ≥ 0,001, théorique ≤ 0 ou |écart|/théorique > tolérance) ; à recompter ; justification manquante | mêmes règles pour les lignes **modifiées localement** ; pour les lignes enregistrées, `retenu`, `hors_tolerance`, `a_recompter` **lus** dans la réponse du serveur | an. 15 |

Gestes de la fenêtre Comptage

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Feuille de comptage » | D, A | `GET documents/inventaires/{id}/feuille` (nouvel onglet) | infobulle « La feuille à imprimer pour compter sur place, sans le théorique (comptage à l'aveugle) » | `BoutonImprimer` |
| « Feuille de recomptage » | D, A | `GET documents/inventaires/{id}/feuille?recomptage=true` | grisé si aucune ligne **enregistrée** à recompter (« Aucun lot à recompter ») ou s'il reste des comptages non enregistrés (« Enregistrer d'abord le comptage : la feuille ne lit que ce qui est enregistré ») ; sinon « {N} lot(s) hors tolérance à recompter, avec le théorique : pour la personne qui recompte » | an. 8 |
| (nouveau) « Feuille avec le théorique » | D | `GET documents/inventaires/{id}/feuille?theorique=true` | infobulle « Pour un contrôle, pas pour compter (le comptage se fait à l'aveugle) » | paramètre enfin proposé (an. 15) |
| « Lot trouvé… » | D, A (saisie) | — | infobulles « Un lot trouvé sur place, absent du théorique » / « Refermer la saisie du lot trouvé » | ouvre l'encart |
| « Abandonner » (danger) | D, A (saisie) | `POST inventaires/{id}/abandonner` `{motif}` | `Confirmer` motif **exigé** (≥ 3 : « Dire pourquoi l'inventaire est abandonné. ») : « Abandonner {INV-…} ? Rien n'est ajusté, les mouvements reprennent ; l'inventaire reste au statut « Abandonné » avec ses comptages. » · « Non » · « Oui, abandonner » | (b) : plus de suppression, numéro gardé ; motif rangé dans `inventaire.abandon_motif` ; succès « {n°} abandonné : les mouvements reprennent. » ; refus « Un inventaire validé reste : ses ajustements sont au journal. » (409), « Inventaire introuvable. », droits |
| « Enregistrer le comptage » | D, A (saisie) | `PUT inventaires/{id}/comptages` `[{ligne_id, compte, palettes, bobines, second_compte, justification}]` (lignes modifiées) | grisé : « Rien à enregistrer » / sinon infobulle « {N} ligne(s) à enregistrer » | succès « {N} comptage(s) enregistré(s). » ; serveur note `premier_par` et `second_par` ; refus repris : « Cet inventaire est déjà validé. » (+ « … est abandonné. »), « Ligne étrangère à cet inventaire. », « « RÉF », lot X : un recomptage suit un premier comptage. », bornes |
| « Valider l'inventaire » (principal) | D, A (saisie) | enregistre d'abord les modifications, puis `POST inventaires/{id}/valider` | grisé : « {N} écart(s) hors tolérance sans justification : écrire d'abord ce qui a été constaté (lignes en rouge) » / « Aucun lot compté » ; `Confirmer` « Valider ? {c} lot(s) comptés, {a} écart(s) ajusté(s) ({±x,x kg})[, {n} non comptés restent au théorique][, {r} recomptage(s) faits par la même personne]. Seule une annulation (contre-passation, avec un motif) la défait. » · « Non » · « Oui, valider l'inventaire » | garde-fous écran inatteignables retirés (an. 15) ; succès « Inventaire validé : {a} ajustement(s) écrit(s) au stock. » + vue « Avec un écart » ; refus serveur repris (déjà validé, aucun lot compté, « Écart hors tolérance sans justification : RÉF1… » (8 au plus), dates, « … des lots qu'il fige ont bougé depuis … », moteur de stock) |
| (Gestion MP corrigé) « Annuler l'inventaire » (danger ; inventaire **validé** seulement ; infobulle « Annuler (contre-passation) : chaque ajustement de cet inventaire est contre-passé, avec un motif ») | D, A | `POST inventaires/{id}/annuler` `{version, motif}` (API-PRO 245) | `Confirmer` motif **exigé** (≥ 3 caractères, sinon « Le motif de l'annulation fait au moins 3 caractères. ») : « Annuler l'inventaire {n°} ? Ses ajustements sont contre-passés à leur date (refusé en période close ou si la matière est déjà repartie). Motif : [ ] » · « Non » · « Oui, annuler l'inventaire » | étape 17 ; succès « Inventaire {n°} annulé : ses ajustements sont contre-passés. » ; statut `annule`, numéro gardé, une seule contre-passation ; refus repris (409) : « Seul un inventaire validé s'annule ; un inventaire en cours s'abandonne. », « L'inventaire {n°} est déjà annulé. », « L'inventaire {n°} est en cours : les mouvements sont suspendus jusqu'à sa validation. », période close, stock insuffisant ; 422 « Dire pourquoi l'inventaire est annulé. » |
| Saisies de cellule (palettes, bobines, compté, recompté, justification) | D, A (saisie) | local jusqu'à « Enregistrer » | — | ligne « modifiée » |
| Bascule « Lots à compter » / « Pièces jointes » | D, A | — | — | `Onglets` dans l'adresse |
| (nouveau) Recherche / vue / « Effacer les filtres » | D, A | — | — | an. 9 |
| (nouveau) « Exporter en Excel » (lignes du comptage) | D, A | (route ajoutée, API-PRO § 1.24 : `GET /api/export/inventaires/{id}`) | — | an. 10 |
| Fermer la fenêtre | D, A | — | garde `sale` | retour à `/inventaire` (onglet gardé) |

Serveur à la validation (inchangé) : un `AJUSTEMENT` par ligne comptée dont |retenu − théorique| ≥ 0,001, daté du jour de
l'inventaire, document « inventaire » + n°, motif « Écart d'inventaire », commentaire « {justification} · recompté par {nom} » ;
statut `valide`, validé par / le ; mouvements du périmètre repris ; un inventaire validé ne se défait que par son **annulation**
(contre-passation de chaque ajustement, une fois, avec un motif ; statut `annule`) ; non comptés restent au
théorique ; **lots trouvés créés à ce moment** (an. 19), numéros internes `LOT-AAAA-NNNN` donnés à ce moment (c).

### Encart « Lot trouvé » — dans `/inventaires/:id`

Gestion MP : `Inventaire.tsx:1118-1247` (`LotTrouve`) → PRO : encart de la fenêtre Comptage, `Form` (`SelecteurMatiere`, `Saisie`,
`Interrupteur` « Lot interne », `Selecteur`, `Nombre`, `Saisie` large), `Bouton({manque})` ; D, A (saisie).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Un lot trouvé sur place, que le stock théorique ne connaissait pas » | idem | — |
| Données `GET /articles`, `GET /magasins` | `GET matieres`, `GET magasins` | — |
| « Matière » : toutes les matières, « RÉF — désignation », détail fournisseur, « Taper quelques mots de la référence… » | `SelecteurMatiere` | — |
| « Numéro de lot » (« Celui de l'étiquette ») + **bouton « Lot interne »** (« Le lot n'a pas d'étiquette lisible ») qui prend un numéro tout de suite | `Saisie` + **case « Lot interne »** (« Le lot n'a pas d'étiquette lisible ») : cochée, le champ se grise « numéro donné à la validation (LOT-AAAA-NNNN) » | (c) |
| « Magasin » : figé sur celui de l'inventaire, sinon « Choisir… » + actifs | idem | — |
| « Bobines » (« × {poids **catalogue**, 2 déc.} kg ») → Compté = arrondi 2 déc. | poids du **lot** s'il existe déjà au référentiel, sinon catalogue ; l'aide dit lequel | an. 19 |
| « Compté (kg) » (« ≈ N ml, à titre indicatif ») | `Nombre` | — |
| « Justification » (« obligatoire : un lot hors du théorique est toujours un écart à expliquer » ; « Palette retrouvée derrière le rayonnage B, étiquette arrachée… » ; ≥ 3 car.) | idem | — |
| Lot **créé tout de suite** au référentiel (date d'entrée = date de l'inventaire), ligne de théorique 0, toujours hors tolérance | ligne enregistrée **sans créer le lot** ; lot créé à la validation ; une matière hors périmètre l'y ajoute (sa suspension commence) | an. 19, (b) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Lot interne » (bouton, `POST /lots/numero-interne`) | D, A | aucune (case) | — | (c) : route supprimée |
| « Ajouter le lot au comptage » | D, A | `POST inventaires/{id}/lots-trouves` `{matiere_id, lot_numero|null, lot_interne, magasin_id, compte, justification}` | grisé avec raison (infobulle) : « la matière » · « le numéro de lot (ou cocher Lot interne) » · « le magasin » · « le poids compté » · « la justification (3 caractères au moins) » | an. 5 ; succès « Lot trouvé ajouté au comptage. » ; refus repris (« Un lot trouvé se décrit : matière, numéro de lot, magasin. », « Matière inconnue. », « Magasin inconnu. », « Cet inventaire ne compte qu'un magasin : le lot trouvé y est rangé. », « Ce lot est déjà dans l'inventaire : saisir son comptage sur sa ligne. », « Un lot doit avoir un numéro : … », « Cet inventaire est déjà validé. ») |
| (nouveau) Fermer l'encart rempli | D, A | — | `Confirmer` « Abandonner ce lot trouvé ? » | saisie protégée |

### Pièces jointes de l'inventaire — `/inventaires/:id?onglet=pieces`

Gestion MP : `PiecesJointes objet="inventaire"` (`suivi.py:242-290`, achats) → PRO : `PiecesJointes` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Lecture seule si pas achats (jamais ici) ; dépôt possible sur un validé | idem (aussi sur un abandonné ou un annulé) | — |
| « Joindre un document… » (« Envoi… ») + note « ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; zone de dépôt | idem | — |
| Note « La feuille de comptage signée, scannée ; une photo d'un lot trouvé ou abîmé. » | idem | — |
| Colonnes « Document » (lien, « Télécharger le document ») · « Genre » · « Taille » (o/Ko/Mo) · « Par » · « Joint le » · « Retirer » | idem | — |
| Vide « Aucun document joint. » ; messages « « nom » joint. » / « N documents joints. » / « « nom » retiré. » ; « « nom » est trop lourd : 20 Mo au plus. » ; serveur « Type de fichier refusé… », « Fichier trop lourd (20 Mo au plus). », « Document inconnu. », « Pièce introuvable. » | idem | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Joindre un document… » / glisser-déposer | D, A | `POST pieces` (objet `inventaire`) | — | — |
| Télécharger (lien) | D, A | `GET pieces/{id}/fichier` | — | — |
| « Retirer » | D, A | `DELETE pieces/{id}` | `Confirmer` « Retirer ce document ? » · « Oui, retirer » ; infobulle « Retirer « nom » de la liste (le retrait est tracé) » | — |

### Document « Feuille de comptage / de recomptage » — `GET /api/documents/inventaires/{id}/feuille?recomptage=&theorique=`

Gestion MP : `GET /api/inventaires/{id}/feuille` (`inventaires.py:433-504`, HTML produit par le code) → PRO : gabarit Jinja2, A4
paysage, papier à en-tête, nouvel onglet ; C.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Une page A4 **paysage** par magasin (codes triés), saut de page ; bouton « Imprimer » masqué à l'impression | idem | — |
| Titre d'onglet « Feuille de comptage {n°} » même pour un recomptage | « Feuille de recomptage {n°} » pour un recomptage | cohérence |
| h1 « Feuille de comptage — {n°} » / « Feuille de recomptage — {n°} » ; « {libellé} · compté le … · magasin **{code}** · N lot(s)[ · avec le théorique] » ; « Compté par : ____ » / « Contrôlé par : ____ » | idem ; inventaire abandonné : mention « Abandonné » | (b) |
| Colonnes « N° » · « Référence » (+ désignation si différente) · « Lot » · « Conditionnement » (« {poids} kg / bobine · {n} bob. / palette ») · [« Théorique » si recomptage ou `theorique=true`] · « Palettes » · « Bobines » · « Compté (kg) » · « Observations » (large) | idem | — |
| Tri référence, date d'entrée, n° de lot | idem | — |
| Recomptage : lignes à recompter **enregistrées**, avec le théorique | idem (le bouton n'est plus actif sur des saisies non enregistrées) | an. 8 |
| Pied « Un lot trouvé sur place et absent de la liste : l'écrire au dos (référence, lot, quantité). Un écart se justifie à la saisie, au-delà de la tolérance de {N} %. » | idem | — |
| Vide « Aucun lot figé dans cet inventaire. » | idem | — |
| `theorique=true` jamais proposé | proposé à D (« Feuille avec le théorique ») | an. 15 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Imprimer » | C | — (`window.print()`) | — | — |

### Notions métier — Inventaire (PRO)

- Document numéroté **dès l'ouverture** (`INV-AAAA-NNNN`) ; statuts `ouvert` (« Comptage en cours ») → `valide` (« Validé ») ou
  **`abandonne` (« Abandonné »)** : un abandon garde le document, ses comptages et son numéro (pas de trou), rien n'est ajusté ;
  un inventaire validé peut passer à **`annule` (« Annulé »)** (Gestion MP corrigé, étape 17) : chaque ajustement est contre-passé
  une fois, à sa date, motif obligatoire ; `valide_le` reste, `annule_le`, `annule_par_id`, `annulation_motif` s'ajoutent ; refusé en
  période close, si la matière ajustée est déjà repartie, ou si un inventaire ouvert couvre ses magasins.
- Figer le théorique : chaque solde lot × magasin > 0 du périmètre devient une ligne.
- **Suspension par périmètre** : tant qu'il est ouvert, aucun mouvement des **matières comptées** ne s'écrit dans son magasin (dans
  tous s'il est global) ; les autres matières bougent. Deux inventaires ouverts ne peuvent pas compter la même matière dans le même
  magasin. Un lot trouvé d'une matière hors périmètre l'y ajoute.
- Périmètre : tout le stock (d'un magasin ou de tous), famille (rôle, composition, classe ABC — critères cumulés), matières
  choisies, tournant (cadence A 30 j, B 90 j, C 365 j, par magasin).
- Classe ABC calculée à l'ouverture ; tolérance (réglage, défaut 2 %, 0…100 %) ; seuil 0,001 kg ; théorique nul + compté > 0 =
  hors tolérance ; justification ≥ 3 car. (écran et serveur) ; comptage à l'aveugle.
- **Recomptage** : pour un premier comptage hors tolérance ; retenu s'il existe ; premier et second compteurs enregistrés ; même
  personne (ou l'ouvreur) **signalée** partout (ligne, indicateur, confirmation de validation), jamais bloquée.
- Retenu, écart, écart net (kg), valeur de l'écart (MAD : CMUP tant qu'ouvert, coût de l'ajustement une fois validé), « sans signe ».
- Lot trouvé, non prévu (théorique 0), **créé à la validation** : jusque-là sa ligne porte sa matière, son numéro (ou la case
  « Lot interne ») et pas de lot (MODELE-DONNEES § 3.7.3) ; lot interne numéroté `LOT-AAAA-NNNN` à la validation ; un même lot
  trouvé (matière, numéro, magasin) ne se saisit qu'une fois.
- Ajustement d'inventaire : `AJUSTEMENT` par écart non nul, motif « Écart d'inventaire », daté du jour de l'inventaire.
- Contrôle d'antidate à l'ouverture (lots figés) et à la validation (lots ajustés).
- Palettes / bobines au poids de bobine du lot (sinon catalogue) ; mètres indicatifs pour cuir, franges, ruban.

### Ouvertures, transferts, ajustements — `/operations?onglet=ouverture|transfert|ajustement|retour_fournisseur|retour_machine`

Gestion MP : `pages/Operations.tsx` (`Operations`), `/operations` (`?onglet=`, `?operation=ID`) → PRO : `/operations?onglet=…`,
`Page`, `EnTete`, `Onglets`, `Carte`, `Note`, `Filtres`, `Recherche`, `DataTable` dans `Cadre`, `ChargerPlus`, `Badge`,
`ExportExcel` ; D, A (tous les onglets) ; **L : onglets « Transferts » et « Retours machine »** (les autres masqués).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Menu « Stock › Ouvertures, transferts, ajustements » et garde : **achats seuls** (+ D) — L renvoyée à son accueil | menu et garde D, A, L ; L ne voit que ses deux onglets | an. 1, (d) |
| Droits par type (`GET /operations/motifs` → `droits`) : ouverture A ; transfert A, L ; ajustement A ; retour fournisseur A ; retour machine L (+ D partout) ; « « {type} » est réservé à : {rôles}. » ; « Type d'opération inconnu. » | `GET motifs` → droits : ouverture D, A ; transfert D, A, L ; **mise en quarantaine D, A, L** ; **libération D, A** ; ajustement D, A ; retour fournisseur D, A ; retour machine D, L ; mêmes refus | (d), contrat |
| A : « Nouveau … » sur 4 onglets, Retours machine en lecture ; D : tout, mais retour machine non modifiable | D, L : retour machine créé, modifié (brouillon), validé, supprimé, annulé ; A : lecture | an. 24 |
| `GET /operations` et `/{id}` ouverts à tous ; prix et devise masqués pour L | idem (`sans_prix`) | — |
| `?onglet=` (inconnu → ouverture) ; `?operation=ID` ouvre la fenêtre **si elle est dans la liste chargée** et force l'onglet ; changer d'onglet vide la recherche ; création hors adresse | `?onglet=` (défaut : premier onglet permis) ; `/operations/:id` lit l'opération **directement** (`GET operations/{id}`) et pose l'onglet de son type ; `/operations/nouvelle?type=` ; après le premier enregistrement → `/operations/:id` | an. 13, an. 14, an. 22 |
| Liens entrants : Stock › Mouvements `/operations?operation=ID` ; Cockpit / Accueil `/operations?onglet={type}` ; À valider `/operations?onglet={type}&operation={id}` | `/operations/{id}` ; `/operations?onglet={type}` ; `/operations/{id}` (ouvert à L pour ses types) | an. 1, an. 13 |
| `GET /operations/motifs` (cache 10 min) ; `GET /operations` (**1000 au plus**, avec lignes, total, `blocages`) | `GET motifs` ; `GET operations?type=&etat=&q=` paginé (500, `ChargerPlus`), recherche serveur | an. 14 |
| Titre « Ouvertures, transferts, ajustements » (omet les retours) ; sous-titre « Chaque geste de stock a son document : … elle s'annule par une écriture inverse. » | titre imposé par le registre ; sous-titre complété « … ouvertures, transferts (dont quarantaine), ajustements, retours fournisseur et retours des machines… » | an. 11 |
| Action selon l'onglet : « Nouveau stock d'ouverture » · « Nouveau transfert » · « Nouvel ajustement » · « Nouveau retour au fournisseur » ; rien pour Retours machine | mêmes + « Nouveau retour des machines » (D, L) → choix de l'ordre validé puis `/ordres/{id}/retour` | an. 24 |
| Pas d'indicateurs | idem | — |
| Onglets « Ouverture de stock » · « Transferts » · « Ajustements » · « Retours fournisseur » · « Retours machine », compteur « N brouillon(s) » | « **Stock d'ouverture** » (comme le titre de la fenêtre) · « Transferts » · « Ajustements » · « Retours fournisseur » · « Retours machine » | an. 11 |
| Erreur ; chargement « les opérations » | `Erreur`, `Chargement` | — |
| Notes d'onglet : Ouverture « Le stock réel de départ… Le lot se crée à la validation. » ; Transferts « Déplacer un lot d'un magasin à un autre — dont la libération d'une quarantaine… » ; Ajustements « Corriger le stock d'un lot hors inventaire… » ; Retours fournisseur « … Un retour ne mêle pas deux fournisseurs… » ; Retours machine « … se saisissent surtout depuis l'écran atelier, au téléphone ; ils se consultent ici. » | mêmes notes ; Transferts : « … dont la mise en quarantaine (achats, direction, alimentation) et la libération d'une quarantaine (achats, direction, après contrôle)… » ; Retours machine : « … se saisissent au téléphone (Retour des machines) ou depuis l'ordre (`/ordres/:id/retour`). » | (d), an. 24 |
| `BarreRecherche` « Numéro, référence, lot, magasin, motif, personne… » (numéro ou « Brouillon », motif, code, commentaire, fournisseur, ordre, créé/validé par, référence, lot, magasins) | `Recherche` (`?q=`, serveur, sans accents) | A6 |
| Liste d'état « Tous les états (n) » · « Brouillons (n) » · « Validées (n) » · « Annulées (n) » ; hors adresse ; gardée au changement d'onglet (la recherche, elle, est vidée) | `Filtres` État dans l'adresse ; recherche et état **gardés tous deux** au changement d'onglet | an. 23 |
| « Effacer les filtres » (recherche ou état) | « Effacer les filtres » + « N critère(s) » dès 2 | A1 |
| Note « {N} opération(s) » | « {N} opération(s) » (total serveur) | — |
| « Tout valider… ({N}) » → `/stock?onglet=a-valider` (« Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout valider » ») | idem | — |
| « Numéro » : n° gras ou « Brouillon » ; note rouge « sera refusée » (infobulle = blocages) | idem | — |
| « Date » | idem | — |
| « Motif » / « Fournisseur » / « Ordre » selon l'onglet (motif « R? · motif » ; fournisseur + motif ; lien d'ordre → `/sorties?ordre={id}` + motif ; commentaire en note) | fournisseur → `LienDocument` `/fournisseurs/{id}` (D, A) ; ordre → `/ordres/{id}` ; « observations » en note | an. 12 |
| « Lots » : 2 premières lignes « RÉF · lot X · MAG » (« · DE → VERS ») + « + N autre(s) » | idem | — |
| « Quantité » « x,x kg » ; ajustement « + » | idem | — |
| « Valeur » (Ouverture seulement) Σ quantité × prix par devise, jamais additionnées | idem (`Montant`, D, A) | — |
| « État » : « Brouillon » / « Validée » / « Annulée » | `Badge` | — |
| « Par » « {créé par}[ · validée par {nom}] » | + « · annulée par {nom} le {date} » | an. 21 |
| Teintes : annulée éteinte ; brouillon bloqué rouge pâle | idem | — |
| Ligne cliquable → `?operation=ID` | → `/operations/{id}` | A5 |
| Vides « Aucune opération ne correspond. » / « Aucune opération de ce type pour l'instant. » | `Vide` identiques | — |
| Pas de tri, pagination, pied, export | tri au clic ; `ChargerPlus` ; `ExportExcel` (route ajoutée, API-PRO § 1.24 : `GET /api/export/operations`) | an. 10, an. 14 |
| Blocages serveur (brouillons) : « aucune ligne » ; date ; « l'inventaire {n°} est en cours ({code / tous les magasins}) » ; lot épuisé / x seulement (transfert, retour fournisseur, ajustement négatif, cumulé) ; antidate ; magasin désactivé ; retour machine « daté du …, avant l'ordre … », « lot … : seulement {x} kg partis pour cet ordre, {y} kg rendus » | mêmes blocages ; inventaire : « l'inventaire {n°} compte « {réf} » ({code / tous les magasins}) » ; + matière retrouvée en « − » (an. 3), lot de quarantaine sans motif de libération (an. 2), fournisseurs mêlés (an. 4) | (b) |

Gestes

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau stock d'ouverture » / « Nouveau transfert » / « Nouvel ajustement » / « Nouveau retour au fournisseur » | selon le type (D, A ; transfert D, A, L) | — | — | → `/operations/nouvelle?type=…` |
| (nouveau) « Nouveau retour des machines » | D, L | `GET ordres?statut=valide` | — | → `/ordres/{id}/retour` (an. 24) |
| Recherche | selon onglets | `GET operations?q=` | — | serveur |
| Liste d'état | idem | `GET operations?etat=` | — | dans l'adresse |
| « Effacer les filtres » | idem | — | — | — |
| « Tout valider… ({N}) » | C | — | — | → `/stock?onglet=a-valider` |
| Clic sur une ligne | selon le type | `GET operations/{id}` | — | → `/operations/{id}` |
| Lien d'ordre (Retours machine) | C | — | n'ouvre pas la ligne | → `/ordres/{id}` |
| (nouveau) « Charger les 500 suivants » | idem | `GET operations` page suivante | — | an. 14 |
| (nouveau) « Exporter en Excel » | selon le type (sans prix pour L) | (route ajoutée, API-PRO § 1.24 : `GET /api/export/operations`) | — | an. 10 |

### Fenêtre d'une opération — `/operations/:id` ; `/operations/nouvelle?type=`

Gestion MP : `Operations.tsx:376-771` (`EditeurOperation`, `versSaisie`), Dialogue `tresLarge` → PRO : `Fenetre({taille:'tresLarge', sale})`,
`Badge`, `Note`, `Blocages`, `BandeauBlocages`, `Form` (`DateChamp`, `Selecteur`, `Saisie`/`Zone`), `DataTable` des lignes (pied de
totaux), encart de ligne, `Bouton({manque, blocages})`, `Confirmer`, `LienDocument` ; droit du type. **Historique** : la fenêtre
d'opération n'a ni onglet ni volet « Historique » (lot F6 : elle tient en 1366 × 768 sans lui, quatre lignes visibles) ;
l'historique d'une opération se lit au journal (`GET historique/operation/{id}`, Administration › Journal). L'inventaire,
lui, a son volet `?onglet=historique`.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| **Modifiable** = droit ET brouillon ET type ≠ retour machine | droit du type ET brouillon (retour machine compris, D, L) | an. 24 |
| Titre « {libellé du type} — {n° / Brouillon} » ou « — nouveau brouillon » + état (ex. « Stock d'ouverture — nouveau brouillon ») | idem | — |
| Note « Saisie par {nom}[ le …][ · validée par …][ · ordre {n°}][ · fournisseur {nom}][ · le numéro est donné à la validation] » ; ordre et fournisseur **en texte** | « Par {nom} le … · validée par … le … · **annulée par … le …** · ordre `LienDocument` · fournisseur `LienDocument` · … » | an. 12, an. 21 |
| Blocages (brouillon enregistré non modifié) « **Sera refusé à la validation :** » | `Blocages` | — |
| (absent) suspension d'inventaire avant d'enregistrer | `BandeauBlocages` dès le choix des lots : inventaire ouvert qui compte la matière | an. 20, (b) |
| « Date » (`max` aujourd'hui ; grisé si non modifiable ; futur → manque « une date qui ne soit pas dans le futur ») | `DateChamp` (+ min après clôture) | an. 18 |
| « Motif (obligatoire) » / « Motif » (absent pour une ouverture) : « Choisir le motif… » / « Sans motif particulier » (transfert) ; motifs du type (+ courant) ; « R1 · … » | `Selecteur` ; pour L, « Libération de quarantaine » absente | (d) |
| Motifs : retour machine R1, R2, R4 ; retour fournisseur « Non-conformité qualité » (R3), « Excédent de réception » (R5), « Bobines endommagées » (R6), « Refus après quarantaine » (R3) ; ajustement « Écart constaté au comptage », « Matière retrouvée », « Perte / casse », « Correction de saisie » ; transfert « Rangement », « Libération de quarantaine », « Mise en quarantaine », « Approvisionnement de l'atelier » | idem (`GET motifs`) | — |
| « Commentaire (obligatoire) » / « Commentaire » ; ajustement ≥ 5 car. (aide « ce qui a été constaté, en quelques mots ») ; placeholders « Bobines écrasées au déchargement, palette retrouvée… » / « Comptage du magasin principal, mise en service… » ; 300 | « Observations (obligatoires) » / « Observations » ; ajustement ≥ 5 ; **mise en quarantaine ≥ 3 (« ce qui est douteux »)** | (d), vocabulaire (P3 an. 8) |
| Info libération « Libération de quarantaine (décision des achats, après contrôle) : choisir un lot dans le magasin de quarantaine ; … Dire dans le commentaire ce qui a été contrôlé. » | « … (décision des achats ou de la direction, après contrôle) … dans les observations … » | (d) |
| (nouveau) Info mise en quarantaine | « Mise en quarantaine : choisir un lot hors quarantaine ; il part vers un magasin de quarantaine et ne sort plus aux machines. Dire dans les observations ce qui est douteux. » | (d) |
| Encart « Nouvelle ligne » (ouvert d'office) ou « + Ajouter une ligne » | idem | — |
| Lignes : « Référence » · « Lot » (mono ou « — » ; « lot créé à la validation ») · « De » / « Magasin » · « Vers » (transfert) · « Ajustement » / « Quantité » (« x,xx kg[ ≈ ml] », signe et couleur pour un ajustement, « N bobine(s) / palette(s) », rouge « plus que les {x kg} du lot ») · « **Prix / unité** » (ouverture, 4 déc.) · « Valeur » (ouverture) · « Modifier » / « Retirer » | « Lot » → `lien` `/lots/{id}` ; lot interne « LOT-… donné à la validation » ; « Prix / unité » → « **Prix / kg** » (« {prix} {devise} / kg ») ; reste idem | an. 11, an. 12, (c) |
| Ligne en cours de modification teintée | idem | — |
| Pied (> 1 ligne) « {n} lignes » · total kg (net, sans mètres) · valeur par devise (ouverture) | pied de totaux idem | — |
| Vide « Aucune ligne. Remplir le formulaire au-dessus, puis « Ajouter la ligne ». » (affiché **aussi en lecture**) | ce texte seulement si modifiable ; sinon « Aucune ligne. » | an. 23 |
| « Pour enregistrer, il manque : … » (« au moins une ligne », « le motif », « le commentaire (ce qui a été constaté) », « une date qui ne soit pas dans le futur ») | `Bouton({manque})` mêmes raisons (« les observations… ») | — |

Gestes de la fenêtre

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « + Ajouter une ligne » | modifiable | — | visible si l'encart est fermé | — |
| « Modifier » (ligne) | modifiable | — | — | encart « Modifier la ligne RÉF » |
| « Retirer » (ligne) | modifiable | — (local) | aucune (fenêtre « sale ») | inchangé (choix assumé, an. 25) |
| « Supprimer le brouillon » (danger) | droit, brouillon enregistré | `DELETE operations/{id}` | `Confirmer` « Supprimer ce brouillon ? Rien n'a encore bougé au stock. » · « Oui, supprimer » ; infobulle « Supprimer le brouillon : rien n'a bougé au stock » | succès en `Messages` (« Brouillon supprimé. ») ; refus « Une opération validée ne se supprime pas : l'annuler. », « Opération introuvable. », droit |
| « Annuler (contre-passation) » (danger) | droit, validée | `POST operations/{id}/annuler` | `Confirmer` « Annuler ? Une écriture inverse remet le stock comme avant ; les deux restent aux mouvements, et l'annulation ne se défait pas. » · « Oui, annuler (contre-passation) » ; grisé avec raison si le serveur l'annonce refusée (matière déjà consommée, inventaire, période close) | succès « {n°} annulée. » ; auteur et date de l'annulation affichés (an. 21) ; refus repris |
| « Fermer » | tous | — | si modifié : garde `sale` (texte unique) ; infobulle « Fermer sans enregistrer » | retour à la liste (onglet du type, filtres gardés, an. 13) |
| « Enregistrer le brouillon » | modifiable | nouvelle `POST operations` ; existante `PUT operations/{id}` — `{type, date, ordre_id, motif, commentaire, lignes:[{matiere_id, lot_id, lot_numero, lot_interne, magasin_id, magasin_destination_id, quantite, unite, prix, devise}]}` | grisé, raison en infobulle **qui suit l'état** (« Rien de modifié », « Il manque : … ») | succès « Brouillon enregistré : le stock ne bouge qu'à la validation. » ; adresse → `/operations/{id}` (an. 22) ; blocages affichés |
| « Valider : le stock bouge » (principal) | droit, brouillon (nouvelle comprise) | enregistre d'abord si besoin, puis `POST operations/{id}/valider` | grisé **aussi en cas de blocages** (raison = blocages) et si une ligne est en cours de saisie dans l'encart (« Une ligne est en cours de saisie : l'ajouter ou l'annuler ») ; `Confirmer` « Valider ? Le stock bouge maintenant ({n} ligne(s)) ; ensuite l'opération ne se modifie plus. » · « Oui, valider » | an. 5, an. 6 ; succès « {n°} validée : le stock est à jour. » ; fenêtre en lecture |
| (nouveau) Liens d'ordre, de fournisseur, de lot | C (fournisseur D, A) | — | — | an. 12 |

Refus à l'enregistrement repris (`operations.py:250-332`) : « Une opération validée ne se modifie plus : l'annuler. » ; « Le type
d'une opération ne change pas. » ; dates ; « Choisir le motif : il dit pourquoi le stock bouge. » ; « Un ajustement se justifie :
écrire en quelques mots ce qui a été constaté. » ; « Un retour des machines se rattache à l'ordre d'où la matière revient. » ;
« Ce retour est daté du … » ; « Matière inconnue. » ; « Magasin inconnu. » ; « Ce lot est d'une autre matière. » ; unités (3) ;
« Un stock d'ouverture se saisit en kg : il fixe le prix au kilo. » ; « « RÉF » : devise inconnue (« XXX »). L'ajouter d'abord dans
Réglages › Devises, avec son cours. » ; « « RÉF » : le numéro de lot du stock d'ouverture manque (ou cocher « Lot interne »). » ;
« Un stock d'ouverture est positif. » ; « Désigner le lot ajusté (ou en nommer un, pour une matière retrouvée). » ; « Un ajustement
ne peut pas être nul. » ; (nouveau) « Une matière retrouvée s'ajoute au stock : sens « + ». » ; « « RÉF » : choisir le lot. » ;
« La quantité est positive. » ; « Un transfert va d'un magasin à un autre. » ; « Magasin de destination inconnu. » ; « Libérer une
quarantaine est une décision de la direction ou des achats, après contrôle de la matière. » (403) ; « Une sortie de quarantaine se
fait avec le motif « Libération de quarantaine ». » ; « Une entrée en quarantaine se fait avec le motif « Mise en quarantaine ». » ;
(nouveau) « Une mise en quarantaine se justifie : écrire ce qui est douteux. » ; « Un retour au fournisseur ne mêle pas deux
fournisseurs. » ; bornes (lignes ≥ 1, motif ≤ 80, observations ≤ 300, lot ≤ 80, prix 0…1e7, devise 3 car.).
Refus à la validation repris : « Cette opération est déjà validée. » ; dates ; libération par un non-autorisé (403) ; retour machine
(daté avant l'ordre ; « Le lot « X » n'est sorti que de … : on ne rend pas plus que ce qui est parti. ») ; moteur de stock
(suspension par périmètre, stock insuffisant, antidate, magasin désactivé, lot sans numéro).
Supprimer ou annuler une libération par un rôle qui ne libère pas (403) : « Supprimer une libération de
quarantaine est une décision de la direction ou des achats. » / « Annuler une libération de quarantaine est une
décision de la direction ou des achats. » (lot RESTES3 ; REGLES OR24, note PRO).

Effets de la validation (inchangés sauf (c)) : numéro `{OUV|TRF|AJU|RFO|RET}-{année}-{NNNN}` à la validation (brouillon supprimé =
pas de trou) ; transfert = deux `TRANSFERT` appariés ; ouverture et matière retrouvée = lot créé (date d'entrée = date de
l'opération ; **lot interne numéroté `LOT-AAAA-NNNN` à ce moment**) puis `OUVERTURE` / `AJUSTEMENT` (prix et devise pour
l'ouverture) ; retour fournisseur `RETOUR_FOURNISSEUR` négatif (rouvre le solde de la commande) ; retour machine `RETOUR_MACHINE`
rattaché à l'ordre ; sortie de quarantaine solde la commande qui n'attendait qu'elle (et l'inverse à l'annulation) ; motif et
observations recopiés sur les mouvements. Annulation = contre-passation de chaque mouvement non contre-passé, datée comme
l'original, sorties d'abord, « Annulation du mouvement n°{id} », une fois ; **auteur et date de l'annulation enregistrés** (an. 21).

### Encart « Nouvelle ligne » / « Modifier la ligne RÉF » — dans la fenêtre d'opération

Gestion MP : `Operations.tsx:775-1121` (`FormeLigne`) → PRO : encart de `Fenetre`, `Form` (`SelecteurMatiere`, `SelecteurLot`,
`Saisie`, `Interrupteur` « Lot interne », `Selecteur`, `Segments`, `Quantite`, `Prix`), `Bouton({manque})`, `Confirmer`.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /articles`, `GET /magasins`, `GET /devises`, `GET /soldes?article_id=` (sauf ouverture) | `GET matieres`, `GET magasins`, `GET devises` (D, A), `GET lots/disponibles?matiere_id=` | — |
| « Matière » : ouverture et ajustement → actives ; autres → stock > 0 ; « RÉF — désignation », « {x} kg[ ≈ ml] en stock » ; changer vide le lot et remet kg ; ouverture : préremplit prix (catalogue au kg) et devise | `SelecteurMatiere` idem | — |
| « Lot et magasin de départ » / « Lot » : grisé sans matière (« Choisir d'abord la matière ») ; « Choisir le lot… » ; « Lot {lot} · {mag}[ (quarantaine)] · {x} kg[ ≈ ml][ · entré le …] » ; ajustement : « Un lot qui n'est pas en stock (matière retrouvée)… » ; aides « Lecture des lots… » / « Aucun lot de cette matière n'est en quarantaine » / « Tous les lots de cette matière sont déjà en quarantaine » / « Aucun lot en stock pour cette matière » | `SelecteurLot` idem ; **retour fournisseur : le fournisseur du lot affiché dans l'option** ; après une première ligne, seuls les lots du même fournisseur proposés | an. 4 |
| Filtrage (transfert) : libération → lots en quarantaine ; mise en quarantaine → hors quarantaine ; **autres motifs ou motif vide → tous** (quarantaine comprise) ; ligne rouverte dont le lot n'est plus en stock gardée (quantité 0) | autres motifs ou vide → **hors quarantaine seulement** (un lot en quarantaine ne se propose qu'avec « Libération de quarantaine », réservé D, A) ; changer de motif revérifie les lignes déjà posées (ligne incompatible en rouge + blocage) | an. 2, (d) |
| « Numéro de lot » (« Celui de l'étiquette ») + **bouton « Lot interne »** → `POST /lots/numero-interne` (ouverture, ajustement « matière retrouvée ») ; erreur dans l'encart | `Saisie` + **case « Lot interne »** (« Le lot n'a pas d'étiquette lisible ») : champ grisé « numéro donné à la validation (LOT-AAAA-NNNN) » | (c) |
| « Magasin » (« Choisir… » + actifs « CODE[ (quarantaine)] ») | idem | — |
| « Vers le magasin » (transfert) : actifs sauf départ ; proposé : lot en quarantaine → premier hors quarantaine ; mise en quarantaine → premier magasin de quarantaine | idem ; mise en quarantaine : **seulement** les magasins de quarantaine | (d) |
| « Sens » (ajustement) « Retirer du stock (−) » / « Ajouter au stock (+) » ; défaut **Retirer**, même pour « Matière retrouvée » | défaut « Ajouter (+) » quand le motif est « Matière retrouvée » ou le lot « pas en stock » ; « Retirer » alors indisponible (raison dite) | an. 3 |
| « Unité » (si > 1, jamais pour une ouverture) : « kg », « bobines ({poids} kg) », « palettes ({n} bob.) » ; aide « = {x} kg » ; poids du lot sinon catalogue | `Quantite` idem | — |
| « Quantité ({kg / bobines / palettes}) » ; aides : rouge « plus que les {x} kg du lot » (hors ouverture/ajustement) ; ajustement « stock du lot après : {x} kg » ; lien « tout le lot : {x} kg » ; « ≈ N ml, à titre indicatif » | `Quantite` idem ; dépassement = blocage (et non simple avertissement) | an. 6 |
| « Prix d'achat / kg » (ouverture) ; aide « catalogue : {prix_kg} {devise} / kg[ ({prix} / ml)] » | `Prix` (D, A) | — |
| « Devise » (ouverture) : actives (+ courante) ; MAD si non chargée ; défaut devise de la matière | `Selecteur` | — |
| Calculs : kg = quantité × contenance ; ajustement « − » négatif ; « stock du lot après » ; dépassement > dispo + 0,001 | idem | — |
| Pied « Il manque : {liste}. » ; « Annuler » (sans confirmation) ; « Ajouter la ligne » / « Enregistrer la ligne » (grisé sans infobulle) ; prix 0 et MAD hors ouverture | `Bouton({manque})` (raison en infobulle et note) ; « Annuler » confirmé si l'encart est rempli | an. 5, an. 25 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Lot interne » (bouton) | D, A | aucune (case « Lot interne ») | — | (c) |
| « tout le lot : {x} kg » | modifiable | — | — | — |
| « Annuler » (encart) | modifiable | — | si rempli : `Confirmer` « Abandonner cette ligne ? » · « Oui, abandonner » | an. 25 |
| « Ajouter la ligne » / « Enregistrer la ligne » | modifiable | — (local) | grisé avec raison | an. 5 |

### Notions métier — Opérations (PRO)

- Un document par geste : stock d'ouverture, transfert (dont **mise en quarantaine** et **libération**), ajustement justifié, retour
  au fournisseur, retour des machines. Cycle brouillon (« Brouillon », corrigeable, supprimable) → validée (numéro, stock bouge) →
  annulée (contre-passation, une fois, auteur et date notés).
- Numéro à la validation (M65) : OUV / TRF / AJU / RFO / RET `-{année}-{NNNN}`.
- Blocages annoncés d'avance (« sera refusée »), Valider grisé ; « Tout valider » (`POST brouillons/valider`, chaque document selon
  son droit ; ordre : dates, puis ouverture < transfert < ajustement < ordre < retour machine < retour fournisseur).
- Motif et code motif (R1…R6) ; motif obligatoire pour ajustement et retours ; observations obligatoires pour un ajustement (≥ 5)
  et une mise en quarantaine (≥ 3).
- Droits : ouverture, ajustement, retour fournisseur D, A ; transfert D, A, L ; mise en quarantaine D, A, L ; libération D, A ;
  retour machine D, L.
- Stock d'ouverture en kg avec prix et devise (coût moyen de départ) ; lot créé à la validation.
- Quarantaine : magasin de type « Quarantaine » ; libération = transfert quarantaine → stock courant, motif imposé ; mise en
  quarantaine = l'inverse, motif imposé ; aucun autre motif ne touche un lot en quarantaine.
- Matière retrouvée : ajustement « + » sur un lot hors stock, nommé ou « Lot interne », créé à la validation.
- **Lot interne** : case sur la ligne ; `LOT-AAAA-NNNN` donné à la validation (plus de numéro pris d'avance).
- Retour fournisseur : un fournisseur par retour (montré au choix du lot) ; rouvre le solde de la commande.
- Retour des machines : rattaché à un ordre validé, pas avant sa date, jamais plus que le net sorti par lot.
- Unités kg, bobine (poids du lot), palette ; stock en kg ; mètres indicatifs.
- Suspension par inventaire : seulement pour les matières de son périmètre.
- Valeur d'une ouverture par devise, jamais additionnée.

### Anomalies GMP corrigées (Partie 6)

1. Opérations interdites à L malgré le serveur et les règles → `/operations` ouvert à L (onglets Transferts et Retours machine) ; liens « À valider » valides pour elle.
2. Sortie de quarantaine sans le bon motif, découverte à l'enregistrement → lots en quarantaine proposés seulement avec « Libération de quarantaine » ; changer de motif revérifie les lignes.
3. Matière retrouvée en « Retirer », sens par défaut « Retirer » → défaut « + », « − » indisponible pour une matière retrouvée ; refus serveur et blocage dès l'enregistrement.
4. Fournisseur du lot non montré en retour fournisseur → affiché dans l'option ; lots filtrés au fournisseur de la première ligne.
5. Boutons grisés sans raison (Valider, Enregistrer le brouillon, Ouvrir et figer, Ajouter la ligne, Ajouter le lot) → `Bouton({manque, blocages})`, infobulle qui suit l'état.
6. Valider cliquable malgré des blocages ; ligne de l'encart perdue en silence → Valider grisé par les blocages et par une ligne en cours de saisie.
7. Recomptage « à quatre yeux » non garanti, premier compteur non enregistré → premier et second compteurs enregistrés ; même personne signalée (ligne, indicateur, confirmation), non bloquée (b).
8. Feuille de recomptage active sur des saisies non enregistrées → bouton actif seulement sur les lignes enregistrées, raison « Enregistrer d'abord le comptage ».
9. Comptage : recherche + vue sans « Effacer les filtres » → « Effacer les filtres » + « N critère(s) ».
10. Pas d'export (inventaires, comptage, opérations) → `ExportExcel` (3 routes à ajouter).
11. Vocabulaire (« Ouvert par », « Validé par », « Prix / unité », « Théorique », deux « Écart », « Ouverture de stock », titre sans retours) → « Par » ; « Prix / kg » ; « Théorique » gardé en inventaire (terme reconnu, exception notée) ; « Écart (kg) » / « Écart (%) » ; onglet « Stock d'ouverture » ; retours dans le sous-titre (titre fixé par le registre).
12. Raccourcis manquants (lots, ordre, fournisseur) → liens `/lots/{id}`, `/ordres/{id}`, `/fournisseurs/{id}`.
13. Fermer une opération ouverte par lien ramène à « Ouverture » → `/operations/:id` pose l'onglet de son type ; fermer y revient.
14. Liste limitée à 1000 en silence, `?operation=` ancien sans effet → pagination serveur (`ChargerPlus`) ; fiche lue par `GET operations/{id}`.
15. Données reçues non montrées, code mort → valeur de l'écart (indicateur et colonne) ; `retenu`, `hors_tolerance`, `a_recompter` lus au serveur ; garde-fous inatteignables, constante `unites`, remise à zéro inutile retirés ; « Feuille avec le théorique » proposée à D.
16. Libellé et confirmation « tout le stock » pour un inventaire partiel → libellé et question selon le périmètre et le nombre de lots.
17. « Certaines matières » hors du magasin choisi ; retrait non marqué → matières du magasin seulement ; retrait = saisie modifiée.
18. Tolérance non bornée, période close non anticipée → `Nombre` 0…100 à la frappe ; `DateChamp` min après clôture (inventaire et opérations).
19. Lot trouvé créé tout de suite (reste après abandon), poids catalogue → lot créé à la validation ; poids du lot s'il existe.
20. Suspension non annoncée dans les opérations → `BandeauBlocages` dès le choix des lots (par périmètre).
21. Annulation non tracée à l'écran → auteur et date de l'annulation enregistrés et affichés (liste et fenêtre).
22. Création hors adresse → `/operations/{id}` posé au premier enregistrement.
23. Présentations incohérentes (tons « Hors tolérance », écart non coloré, vide trompeur en lecture, filtre d'état hors adresse) → règle de ton unique ; écart coloré dans les deux onglets ; vide selon modifiable ; filtres dans l'adresse, gardés ensemble.
24. Retours machine : D peut tout sauf modifier, pas de lien vers la saisie → brouillon modifiable par D, L ; « Nouveau retour des machines » → `/ordres/{id}/retour`.
25. « Annuler » l'encart rempli sans garde → confirmation si l'encart est rempli (« Retirer » une ligne reste sans confirmation, fenêtre « sale »).

### Comptes de la partie 6

- **Écrans / pages** : 2 (`/inventaire`, `/operations`) + 1 section de conventions communes.
- **Onglets / sous-vues** : 9 GMP repris — Inventaire 2 onglets (« En cours de comptage », « Inventaires clos ») + 2 volets du
  comptage (« Lots à compter », « Pièces jointes », désormais `Onglets`) ; Opérations 5 onglets. (+ 7 vues du comptage, 4 périmètres.)
- **Fenêtres / encarts / documents** : 7 — `/inventaires/nouveau`, `/inventaires/:id`, `/operations/:id` et
  `/operations/nouvelle?type=` (5 types) ; encarts « Lot trouvé », « Nouvelle ligne / Modifier la ligne » ; document « Feuille de
  comptage / de recomptage » ; panneau « Pièces jointes ».
- **Gestes** : 36 gestes GMP repris (inventaire 19, opérations 17) ; + 17 nouveaux (filtre État, Effacer ×3, Exporter ×3, Feuille
  avec le théorique, fermer l'encart lot trouvé confirmé, Nouveau retour des machines, Charger les 500 suivants, liens ordre /
  fournisseur / lot, Annuler l'encart confirmé, fermer la fenêtre de comptage, recherche du comptage) ; + 1 repris de Gestion MP
  corrigé (« Annuler l'inventaire », étape 17).
- **Anomalies** : 25 / 25 traitées.

### Routes demandées par la partie 6 (reportées dans API-PRO § 1.24)

- `GET /api/export/inventaires` (D, A) — liste des inventaires avec les filtres.
- `GET /api/export/inventaires/{id}` (D, A) — lignes d'un comptage.
- `GET /api/export/operations` (C selon le type ; sans prix pour L) — liste des opérations avec les filtres.

Paramètres d'écran à ajouter au registre (pas des routes d'API) : `/inventaires/:id?onglet=lots|pieces` ;
`/inventaire?onglet=passes&q=&etat=` ; `/operations?onglet=…&q=&etat=`. Corps d'API étendus (pas de nouvelle route) :
`POST operations` accepte `valider: true` (création et validation en une transaction, retour et déplacement du téléphone) et
`lot_interne` par ligne ; `PUT metiers/{id}` accepte `fils` (D, transaction unique) ; `POST inventaires/{id}/abandonner` prend
`{motif}` ; `POST inventaires/{id}/lots-trouves` prend `lot_interne`. Route reprise de Gestion MP corrigé (étape 17, ajoutée
à API-PRO § 1.14 sous le n° 245) : `POST /api/inventaires/{id}/annuler` `{version, motif}` (D, A).

---

## Partie 7 — Catalogue (matières, classification, fournisseurs, import tableur), qualités et recettes

Source : `docs/heritage/ECRANS.md` lignes 5674-6305. GMP = Gestion MP. Routes d'API sans le préfixe
`/api`. Rôles : D direction · A achats · L alimentation · T administrateur technique · C = D, A, L.

**Règles communes à toute la partie (valent pour chaque section ci-dessous, sans être répétées)**

- R1 — Fiches matière, fournisseur, qualité : adresse stable **et** `Fenetre` par-dessus la liste
  (A5) ; fermer revient à la liste en gardant onglet, filtres, défilement. Anciennes adresses
  (`/catalogue?matiere=12`, `?fournisseur=3`, `/qualites?qualite=7`) redirigées vers les nouvelles.
- R2 — Chaque fiche porte un champ `version` (remplace `version` et `empreinte` de GMP) ; un `PUT`
  avec une version périmée renvoie 409 « Cette fiche a été modifiée entre-temps par {nom} :
  rechargez-la pour repartir de sa dernière version, puis refaites la modification. » (accord exact
  par objet : « Cette matière… modifiée », « Ce fournisseur… modifié », « Cette qualité…
  modifiée ») ; l'écran affiche alors `Bouton` « Recharger la fiche » et le texte « La fiche affichée
  n'est plus la dernière : la recharger avant de modifier. » ; succès « Fiche rechargée dans sa
  dernière version : refaire la modification. »
- R3 — Chaque fiche a un onglet **Historique** (`Historique`, `GET historique/{objet}/{id}`) : le
  journal des actions de la fiche, champ par champ, avant → après, par, quand.
- R4 — `Fenetre({sale})` : ×, Échap, fond **et** les boutons « Abandonner les modifications »,
  « Annuler », « Fermer » passent par la garde « Des modifications ne sont pas enregistrées. Les
  abandonner ? » · « Non, continuer la saisie » · « Oui, abandonner » (corrige P7-22).
- R5 — Bornes, longueurs, listes fermées : **une seule déclaration serveur** (schéma de la fiche,
  renvoyé avec la fiche) ; contrôle à la frappe (`Champ` en rouge + message français) **et** au
  serveur ; aucun message pydantic anglais n'atteint l'écran (corrige P7-19, P7-20).
- R6 — `Bouton({manque, blocages})` : « Pour enregistrer, il manque : … » (liens vers l'onglet
  fautif) et raisons métier du serveur (`blocages` de la fiche : traces qui interdisent une
  suppression, etc.) en infobulle ; jamais un bouton cliquable qui sera refusé (P7-4, P7-5, P7-6).
- R7 — `Confirmer` sur la ligne (texte et « Oui, … » de GMP gardés) ; jamais `window.confirm`.
- R8 — Refus de rôle : 403 « Cette action est réservée à : {rôles}. » gardé ; écran non permis →
  `EcranReserve`. Après chaque écriture : invalidation globale TanStack Query (remplace la liste
  `types.ts:313-314` et le doublon de hook P7-17).
- R9 — Prix toujours « 12,50 USD / kg » (`Prix`, `Montant`) — une seule graphie (P7-2) ; vocabulaire
  REGLES-ECRAN § 5 : « Référence » jamais « Fil » en en-tête (P7-1), « Observations » (P7-3).
- R10 — L (alimentation) : lit les matières **sans aucun prix ni montant** (colonne Prix, volet
  Achat chiffré, coûts masqués par le serveur) ; aucune écriture au catalogue ; lit qualités et
  nomenclature sans coûts (`GET qualites`, `GET nomenclature` coûts masqués). GMP la refusait :
  ouverture en lecture conforme au contrat.

---

### Matières, classification, fournisseurs (page) — `/catalogue?onglet=matieres|classification|fournisseurs`

Gestion MP : page « Matières, classification, fournisseurs », `/catalogue` (`?onglet`, `?matiere`,
`?fournisseur`, `?liste`, `?fournisseur_filtre`) → PRO : `/catalogue` (`Page`, `EnTete`, `Onglets`,
`useOngletAdresse`, `useFiltresAdresse`) ; D, A ; L : onglet Matières seul, lecture sans prix.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Matières, classification, fournisseurs » | `EnTete({titre, fil, aide})` | titre = libellé du menu (registre `routes.ts`) |
| Sous-titre « Le référentiel des achats : une nouvelle matière se crée ici… on le désactive. » | ligne sous le titre + entrée `aide.json` (« ? ») | inchangé |
| Pas d'indicateurs | — | — |
| Onglet « Matières » (compteur = actives) | `Onglets` compteur | inchangé |
| Onglet « Classification » (compteur = toutes valeurs, désactivées comprises, rôles exclus) | compteur = valeurs **actives** (même compte que la `Bascule`) | P7-27 |
| Onglet « Fournisseurs » (compteur = actifs) | `Onglets` compteur | inchangé ; L ne voit pas Classification ni Fournisseurs |
| `?onglet=` ; valeur inconnue → matieres ; changer d'onglet efface toute l'adresse | `?onglet=` ; chaque onglet garde ses filtres dans l'adresse | les filtres ne se perdent plus au changement d'onglet |
| `?matiere=ID|nouvelle`, `?fournisseur=ID|nouveau` | routes `/matieres/:id`, `/matieres/nouvelle`, `/fournisseurs/:id`, `/fournisseurs/nouveau` | R1 |
| `?fournisseur_filtre=ID` | filtre « Fournisseur » dans l'adresse (`?onglet=matieres&fournisseur=ID`) | effacé par « Effacer les filtres » (P7-28) |
| `?liste=` (composition par défaut, type_fil, titrage, couleur, roles) | `?onglet=classification&liste=` (+ `unites-titrage`, lot UNITES-TITRAGE) | inchangé |
| Données `GET /articles`, `/fournisseurs`, `/classification` (acteur) | `GET matieres` (prix masqués pour L), `GET fournisseurs` (L : résumé), `GET classification` | routes renommées |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir un onglet | D, A (L : Matières seul) | — | — | filtres de l'onglet quitté gardés |

Anomalies : P7-18, P7-27, P7-28.

---

### Onglet Matières — `/catalogue?onglet=matieres`

Gestion MP : onglet Matières (`CatalogueMatieres.tsx:115-358`) → PRO : `Carte` + `Filtres` (liés) +
`Recherche` + `DataTable` dans `Cadre` ; D, A ; L lecture (sans colonne Prix, sans « Exporter »,
« Tableur », « Nouvelle matière »).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Un instant — chargement : le catalogue… » ; erreur en bandeau | `Chargement`, `Erreur` | — |
| En-tête de carte « Matières » + « Exporter en Excel », « Tableur », « Nouvelle matière » (principal) | `Carte` actions : `ExportExcel`, `Bouton`, `Bouton` principal | masqués pour L |
| Recherche « Plusieurs mots, dans n'importe quel ordre : « rouge 2900 frisé »… » ; mots dans tout ordre, sans accents ; champs : référence, désignation, fournisseur, rôle, composition (code — libellé), type de fil, titrage, couleur, code couleur, groupe, code douanier | `Recherche` (garde le focus) + `Colonne.recherche` (champs cachés compris) ; même règle au serveur `?q=` (A6) | inchangé |
| « N matière(s) · K critère(s) · X kg en stock » (stock des matières visibles) | compteur de `Filtres` | inchangé |
| 7 filtres liés : « Rôle : tous », « Fournisseur : tous », « Composition : tous », « Type de fil : tous », « Couleur : tous », « Titrage : tous », « Unité du titrage : tous » ; options « code — libellé (n) », valeur choisie gardée à (0), tri français numérique ; filtre posé teinté | `Filtres` liés (A1) | inchangé |
| État : « Actives » (défaut), « Actives et désactivées », « Désactivées » | `Filtres` (liste d'état) | — |
| « Effacer les filtres » dès 1 critère ; vide texte + 7 filtres, **pas** l'état ; `fournisseur_filtre` reste dans l'adresse | « Effacer les filtres » dès 2 filtres (A1) ; remet **tout**, état compris (défaut Actives), et nettoie l'adresse | P7-28, P7-31 |
| Col. « Référence » (désignation dessous, coupée à 160 px, infobulle) | `Colonne` `rendu` + `recherche` | — |
| Col. « Rôle » | `Colonne` | — |
| Col. « Fournisseur » (sinon badge « aucun » attention) | `Colonne` + `Badge` | — |
| Col. « Composition » (code ; libellé dessous s'il diffère) | `Colonne` | — |
| Col. « Type » (infobulle « Type de fil, et titrage dessous ») | `Colonne` (infobulle d'en-tête) | — |
| Col. « Couleur » (code classification ; code couleur fournisseur dessous) | `Colonne` | — |
| Col. « Prix » : « 12,50 USD/kg » / « 3,20 MAD/ml », « — » si nul ; au mètre : dessous « X MAD/kg » | `Prix` : « 12,50 USD / kg », dessous « soit X MAD / kg » ; colonne **absente pour L** | P7-2 |
| Col. « Stock min. » + « couv. min » (infobulle) : « 500 kg », dessous « 1,5 mois » | `Colonne` `droite`, `unite` kg | — |
| Col. « Conditionnement » : « au kilo » ou badge « Palette · 1 080 kg » (accent déclarée / neutre déduite) ; dessous « bobine 12,50 kg × 96 · mini 500 kg · déduit » | `Colonne` + `Badge` | — |
| Col. « Groupe » (dessous « priorité N ») | `Colonne` | — |
| Col. « En stock » : kg ; badge « désactivée » ; badge attention si < stock min ; « ≈ 1 020 ml » (cuir, franges, ruban) | `Colonne` + `Badge` + `KgEtMetres` | — |
| Tri serveur (référence), non cliquable ; ni pagination ni pied | `DataTable` tri par défaut référence, défilement dans le `Cadre` (A2) | — |
| Ligne cliquable → fiche ; désactivée grisée | `lien` → `/matieres/:id` ; ligne éteinte | adresse stable |
| Vide : « Aucune matière ne correspond à la recherche et aux filtres. » / « Le catalogue est vide. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Toutes les matières, avec leur classification et leur stock, dans un classeur Excel ») | D, A | `GET export/matieres` (avec les filtres posés) | — | `ExportExcel` suit les filtres ; 26 colonnes gardées (Référence … Active) + « Priorité dans le groupe » ; `matieres-AAAA-MM-JJ.xlsx`, feuille « Matières », titre « Matières — exporté le JJ/MM/AAAA » |
| « Tableur » (infobulle « Télécharger le catalogue en tableur, le corriger, le réimporter avec aperçu ») | D, A | ouvre `/catalogue/tableur` | — | adresse stable |
| « Nouvelle matière » | D, A | ouvre `/matieres/nouvelle` | — | reprend les filtres posés (rôle, composition, type, titrage, couleur, fournisseur + sa devise) |
| « Effacer les filtres » | C | — | visible dès 2 filtres | remet aussi l'état et l'adresse |
| clic sur une ligne | C | `GET matieres/{id}` | — | `/matieres/:id` (L : lecture) |

Anomalies : P7-2, P7-28, P7-31.

---

### Fiche matière (fenêtre) — `/matieres/:id`, `/matieres/nouvelle` (sur `/catalogue?onglet=matieres`)

Gestion MP : fenêtre « Fiche matière » `/catalogue?matiere=ID|nouvelle` (`CatalogueMatieres.tsx:360-1121`) →
PRO : `Fenetre({taille:'large', sale, pied})` + `Onglets` (`?onglet=classification|achat|conditionnement|pieces|historique`)
+ `Form` ; D, A en écriture ; L lecture sans volet Achat chiffré ni Pièces jointes. (`/stock/matieres/:id`
reste la fiche de stock de la matière, Partie 2.)

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre = référence ou « Nouvelle matière » + badge « désactivée » | titre de `Fenetre` + `Badge` | — |
| `sale = change && modifiable` → « Les abandonner ? » | `Fenetre({sale})` | aussi sur « Abandonner les modifications » (R4) |
| Données : devises, codes douaniers, catalogue, pièces, `POST /articles/composer` (250 ms) | `GET devises`, `GET codes-douaniers`, `GET matieres/{id}`, `GET pieces?objet=matiere&id=`, `GET matieres/reference` (temporisé 250 ms) | routes renommées |
| Bandeau : « 1 234,0 kg ≈ 1 020 ml en stock · modifiée le … par Nadia » | `Note` + `KgEtMetres` | — |
| Liens « Voir ses lots », « Ses mouvements de stock » | `LienDocument` | voir gestes |
| Création : note « Choisir d'abord la classification : la référence et la désignation s'écrivent seules… » | `Note` | — |
| Volets : « Classification et référence », « Achat », « Conditionnement et stock », « Pièces jointes » (existante ; compteur, « … » en lecture) ; « ! » sur un volet où il manque un champ | `Onglets` (compteur, « ! ») + onglet **« Historique »** (existante) | R3 ; L : ni Pièces jointes ni chiffres d'Achat |
| Défauts de création : 1er rôle, MAD, prix au kg, active, unité d'achat vide (= déduite) ; reprise des filtres de la liste et de la devise du fournisseur filtré | mêmes défauts, renvoyés par le schéma serveur | — |
| **Classification et référence** : Composition, Type de fil, Titrage, Couleur (`ChoixClasse`, placeholders « Taper : PP, polyester… », « Taper : FRZ, shrink… », « Taper : 2900 Dtex… », « Taper : rouge, beige… ») | `Selecteur` (recherche à la frappe, clavier) avec ajout sur place | voir gestes ChoixClasse |
| Code couleur (aide « celui du fournisseur : 7612, A-304… », ≤ 32) | `Saisie` | — |
| Suffixe fournisseur (aide « la marque de fin du fournisseur : Hs, Oz, Tat… ») — non enregistré | `Saisie` (sert à composer) | — |
| Référence (mono, obligatoire ≥ 2, ≤ 160) ; rouge + « Une autre matière porte déjà cette référence. » ; aides « composée à partir de la classification » / « La classification compose : `<réf>` (déjà au catalogue) [la reprendre] » | `Saisie` + contrôle de doublon (`GET matieres/reference` → `existe`) | — |
| Désignation (≤ 160 ; composée : couleur atelier + code couleur) | `Saisie` | — |
| Rôle dans le tapis (ordre de la classification ; « Cuir (au mètre) ») | `Selecteur` | — |
| Densité (kg / ml) — si rôle au mètre ; aide « obligatoire pour le cuir, les franges, le ruban… » | `Nombre` (bornes 0-1000) | R5 |
| Référence composée : composition + type + titrage (valeur unité) + couleur + code couleur + suffixe ; remplacée tant que non retouchée ; existante = libre | même règle (`GET matieres/reference` → `{reference, existe, designation}`) | — |
| ChoixClasse : « code — libellé » ; liste des valeurs actives (+ actuelle désactivée) ; recherche sur code, libellé, famille, composition détaillée ; « 60 premières sur N : affiner la recherche. » ; « Aucune valeur. » / « Rien ne correspond. » ; détail « famille · composition détaillée » | `Selecteur` (mêmes textes) | — |
| Panneau d'ajout en ligne : titre « Ajouter une composition à la classification » (type / titrage / couleur), « Code » (aide « valeur et unité : « 2900 Dtex » » ou « tel qu'il s'écrit dans la référence ») + champs de la liste ; note « Elle rejoint la classification et se choisit aussitôt pour cette matière. » ; code en MAJUSCULES (composition, type) ; titrage « 2900 dtex » → 2900 + Dtex | panneau dans la fenêtre (`Form`) | longueurs alignées sur la matière (P7-19) |
| **Achat** : Fournisseur (« — aucun — » + actifs + actuel, « Nom (PAYS) » ; aide « PAYS · délai 60 j · devise par défaut USD » ; obligatoire si en service, aide « obligatoire pour une matière en service : le plan d'achat sait ainsi à qui la commander » ; en création reprend sa devise) | `Selecteur` | L : nom du fournisseur seul |
| Prix d'achat + « DEVISE / » + unité kg/ml (infobulle « L'unité du prix… ») ; aides « soit 4,10 MAD/kg — le stock et tous les calculs sont au kilo » / « au mètre : saisir la densité pour le ramener au kilo » / « le dernier prix confirmé d'une commande s'y inscrit » | `Prix` (devise + unité kg|ml) ; bornes 0-10 000 000 | masqué pour L ; « 4,10 MAD / kg » |
| Densité (prix au mètre, rôle non linéaire) ; aide « obligatoire pour un prix au mètre : il se ramène au kilo par elle » | `Nombre` | — |
| Devise (« USD — Dollar », repli MAD) ; aide « celle du prix ; un bon de commande par devise » | `Selecteur` | masqué pour L |
| Unité d'achat (suggestions Fût, Sac, Big-bag, Palette, Bobine, Carton, Rouleau ; placeholder « déduite : Palette ») ; aides « déclarée : le plan d'achat commande dans cette unité » / « vide = déduite : Palette (1 080 kg) — palette si… sinon bobine, sinon kilo » | `Selecteur` liste fermée (sans « ml ») + vide = déduite | P7-20 |
| Contenance (kg par <unité>) si unité déclarée ; aide « obligatoire pour une unité déclarée : une colle en fûts de 200 kg se déclare, elle ne se devine pas » | `Quantite` | — |
| Minimum de commande (kg) ; aide « Le plan d'achat ne proposera jamais moins » | `Quantite` | — |
| Code douanier (« 5402.47.00.00 — Fils de PP (10,0 %) » ; si liste en erreur : texte libre « liste des codes douaniers indisponible : taper le code ») ; aides « libellé · droits 10,0 % » / « sert à prévoir et vérifier les droits de douane d'un dossier d'importation » | `Selecteur` | repli texte libre gardé |
| Unité déduite (bobine × bobines/palette → Palette ; bobine → Bobine ; sinon kg) ; envoi vide → `kg`, 1 | même règle, calculée au serveur (champ `unite_deduite`) | une seule source |
| **Conditionnement et stock** : kg / bobine (« au catalogue ; le poids mesuré du lot sert aux sorties en bobines ») ; Bobines par palette (« une palette ≈ 1 080 kg » / « avec le poids d'une bobine : la palette devient l'unité d'achat déduite ») ; Stock minimum (kg) (« sous ce seuil, la matière est signalée ») ; Couverture minimum (mois) (« mois de consommation à garder d'avance », ≤ 60) ; Groupe d'équivalence (suggestions ; « des matières interchangeables portent le même groupe ») ; Priorité dans le groupe (grisée sans groupe ; « la plus petite passe en premier », 0-100) | `Nombre`, `Quantite`, `Selecteur` (groupe), bornes R5 | bornes contrôlées à la frappe (P7-20) |
| **Pièces jointes** : note « Fiche technique, certificat, photo d'un échantillon… » ; « Joindre un document… » / « Envoi… », glisser-déposer, « PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le télécharge. » ; types acceptés ; tableau Document · Genre · Taille · Par · Joint le · [Retirer] ; vide « Aucun document joint. » ; messages « « nom » est trop lourd : 20 Mo au plus. », « « nom » joint. », « N documents joints. », « « nom » retiré. », « Type de fichier refusé… », « Fichier trop lourd (20 Mo au plus). », « Document inconnu. », « Pièce introuvable. » | `PiecesJointes` | D, A seulement |
| « Pour enregistrer, il manque : la référence (onglet Classification et référence), le rôle, la densité…, le fournisseur, la contenance d'une unité d'achat (Fût) » (liens vers le volet) | `Bouton({manque})` + `Blocages` (liens vers l'onglet) | — |
| Refus serveur : longueurs/bornes (référence 2-160, désignation ≤ 160, rôle ≤ 32, composition/type ≤ 32, titrage ≤ 48, couleur ≤ 64, code couleur ≤ 32, densité 0-1000, prix 0-1e7, devise 3, unité ≤ 32, contenance 0-1e7, minimum 0-1e9, kg/bobine 0-1000, bobines/palette 0-10 000, stock min 0-1e9, couverture 0-60, groupe ≤ 64, priorité 0-100, code douanier ≤ 20) ; « Rôle inconnu : « X ». » ; « Composition inconnue : « X ». L'ajouter d'abord dans la classification. » (type, titrage, couleur) ; « Unité du prix : au kilo (kg) ou au mètre (ml). » ; densité cuir ; densité prix au mètre ; « Une matière en service a un fournisseur… (contrôle C05). » ; « Fournisseur inconnu. » ; « Devise inconnue… (Réglages › Devises). » ; unité « ml » ; contenance ; « Code douanier inconnu… » ; 409 « La matière « REF » existe déjà. » ; 409 version ; 404 « Matière introuvable. » | mêmes messages, en français, champ libellé (pas de clé technique) | accords « Type de fil inconnu », « Titrage inconnu » (P7-13) ; code douanier : « … demander à la direction de l'ajouter (Réglages › Codes douaniers). » (P7-15) |
| Journal « création matière », « modification matière » (ancienne → nouvelle référence), « suppression matière » ; version +1, `modifie_le`, `modifie_par` | journal champ par champ (avant → après), onglet Historique | R3 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Créer la matière » | D, A | `POST matieres` | `manque` ; blocage « référence déjà au catalogue » | succès « Matière créée : elle se commande dès maintenant. » ; la fenêtre passe à `/matieres/:id` |
| « Enregistrer » | D, A | `PUT matieres/{id}` + `version` | grisé si envoi, manque, doublon, rien changé | « Fiche enregistrée. » ; 409 → R2 |
| « Recharger la fiche » | D, A | `GET matieres/{id}` | — | R2 |
| « Désactiver » | D, A | `PUT matieres/{id}` : la fiche entière avec `actif: false` et `version` (API-PRO § 1.24 ; seul ce qui change est revalidé) | `Confirmer` danger « Désactiver « REF » ? Elle ne sera plus proposée aux commandes ni aux recettes ; son historique et son stock restent. » / « Oui, désactiver » ; blocage « Enregistrer d'abord les changements » | ne revalide plus toute la fiche (P7-21) ; « Matière désactivée. » |
| « Réactiver » | D, A | `PUT matieres/{id}` `{actif:true, version}` | blocage « Choisir d'abord son fournisseur (onglet Achat) » ; infobulle « La remettre en service » | « Matière réactivée. » |
| « Supprimer » | D, A | `DELETE matieres/{id}` | `Confirmer` danger « Supprimer définitivement « REF » ? » / « Oui, supprimer » ; `blocages` serveur : « des mouvements de stock », « des lots en stock ou passés », « des commandes », « des réceptions », « des ordres de fabrication », « des opérations (brouillons compris) », « des dossiers d'importation », « des recettes », « des fils montés sur les métiers », « des pièces jointes » avec les infobulles de GMP | ferme la fenêtre ; message « « REF » supprimée. » ajouté |
| « Fermer » / « Abandonner les modifications » (infobulle « Fermer sans enregistrer : les modifications sont perdues ») | C | — | garde `sale` | P7-22 |
| « la reprendre » | D, A | `GET matieres/reference` | — | — |
| « Voir ses lots » | C | — | — | → `/stock?onglet=lots&matiere=ID` |
| « Ses mouvements de stock » | C | — | — | → `/stock?onglet=mouvements&matiere=ID` |
| ChoixClasse : choisir (Entrée : code exact, sinon seule trouvée, sinon ajout ; Échap ferme) | D, A | `GET classification` | — | `Selecteur` |
| « + Ajouter « XYZ » » (détail « nouvelle valeur de la classification (Entrée) ») | D, A | — (ouvre le panneau) | — | code en majuscules |
| « × » (infobulle « Retirer cette valeur ») | D, A | — | — | — |
| Panneau : « Annuler » / « Ajouter « CODE » » | D, A | `POST classification/{liste}` | grisé si code vide ou envoi ; 409 « « X » existe déjà. » | la valeur est aussitôt choisie |
| « Joindre un document… » / glisser-déposer | D, A | `POST pieces` (objet `matiere`) | > 20 Mo refusé à l'écran | — |
| ouvrir un document (lien, infobulle « Télécharger le document ») | D, A | `GET pieces/{id}/fichier` | — | — |
| « Retirer » (infobulle « Retirer « nom » de la liste (le retrait est tracé) ») | D, A | `DELETE pieces/{id}` | `Confirmer` « Retirer ce document ? » / « Oui, retirer » | fichier gardé, retrait au journal |
| choisir un volet | C | — | — | `?onglet=` dans la fenêtre |
| ouvrir l'onglet « Historique » | C | `GET historique/matiere/{id}` | — | nouveau (R3) |

Anomalies : P7-2, P7-13, P7-15, P7-18, P7-19, P7-20, P7-21, P7-22.

---

### Le catalogue par tableur (fenêtre) — `/catalogue/tableur`

Gestion MP : fenêtre « Le catalogue par tableur » (sans adresse, `TableurMatieres.tsx`, serveur
`suivi.py:678-838`) → PRO : `Fenetre({taille:'large', sale})` sur `/catalogue?onglet=matieres`,
`Indicateurs`, `Onglets`, `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Le catalogue par tableur » ; `sale` = aperçu lu, non appliqué, ≥ 1 matière à écrire | `Fenetre({sale})` | — |
| Mode d'emploi 1-2-3 (« Télécharger le modèle : c'est le catalogue actuel, une matière par ligne. » ; « Le corriger ou le compléter dans Excel… » ; « Le relire ici : rien n'est écrit tant qu'on n'a pas vu ce qui changera et cliqué « Appliquer ». ») | `Note` (liste numérotée) | + phrase « Une case vide ne change rien ; pour vider une case, nommer sa colonne dans « Vider ». » (P7-12) |
| Colonnes du modèle (ordre, intitulés exacts) : Référence, Désignation, Rôle, Composition, Type de fil, Titrage, Couleur, Code couleur, Densité, Fournisseur, Prix, Unité du prix, Devise, Unité d'achat, Contenance, Minimum de commande, kg / bobine, Bobines par palette, Stock minimum, Couverture minimum (mois), Groupe d'équivalence, Code douanier, En service ; info « Se commande en (lecture seule) » | `GET matieres/tableur` (modèle) : mêmes colonnes **+ « Priorité dans le groupe »** (P7-12) **+ « Vider »** (noms de colonnes à vider, séparés par « ; ») **+ « Version »** (lecture, relue) | mêmes règles que la fiche |
| Seule « Référence » obligatoire ; colonnes lues par intitulé ; ancien « Poids d'une bobine » lu ; « Unité » abandonnée ; ligne sans référence sautée ; case vide = rien ; virgule ou point ; « En service » vrai si oui/1/vrai/true/x ; fournisseur par nom sans casse ; jamais de suppression | idem, sauf : case vide = ne change pas **sauf** colonne nommée dans « Vider » | P7-12 |
| Contrôles ligne par ligne (« densite n'est pas un nombre », « fournisseur inconnu « X » », « composition inconnu « X » (l'ajouter d'abord à la classification) », « unité du prix : kg ou ml », « une matière en service a un fournisseur », « un prix au mètre a besoin de la densité (kg par mètre) », « une matière du rôle Cuir a besoin de sa densité… », « la commande se compte en kilos : un prix au mètre se dit dans « Unité du prix » », « une matière nouvelle a besoin de son rôle », « … de son fournisseur ») | **mêmes contrôles que la fiche** (R5 : bornes, longueurs, négatifs, contenance d'une unité déclarée, doublon de référence, couverture ≤ 60…), messages avec le libellé de colonne : « Densité : pas un nombre », « Composition « X » inconnue : l'ajouter d'abord à la classification », « Devise « X » inconnue : l'ajouter d'abord (Réglages › Devises) », « Rôle « X » inconnu », « Code douanier « X » inconnu : demander à la direction de l'ajouter » ; fournisseur exigé seulement pour une matière **en service** ; version : « modifiée entre-temps par {nom} depuis le modèle : retélécharger le modèle » | P7-9, P7-10 |
| Erreurs de fichier : « Tableur illisible : <détail> » ; « La colonne « Référence » est obligatoire (télécharger le modèle). » ; « N ligne(s) en erreur : corriger le tableur d'abord, rien n'a été écrit. » | `Erreur` (détail technique au journal serveur, pas à l'écran) | — |
| « Choisir le tableur à relire… » / « Choisir un autre tableur… » (.xlsx), nom affiché, « Lecture… » ; aperçu lancé aussitôt | `Bouton` fichier → `POST matieres/tableur/apercu` | — |
| Indicateurs « Créées » (« matières nouvelles », ok si > 0), « Modifiées » (« au moins un champ change »), « Inchangées » (« rien à faire »), « Erreurs » (« à corriger dans le tableur » / « tableur juste », critique / ok) | `Indicateurs` (`Kpi`) | — |
| Volets « Erreurs (n) », « Modifiées (n) », « Créées (n) » ; ouvert d'office : Erreurs, sinon Modifiées, sinon Créées | `Onglets` (compteurs) | — |
| Erreurs : Ligne (n° Excel) · Référence · Ce qui ne va pas (« ; ») | `DataTable` | — |
| Modifiées : Référence · Champs qui changent (noms traduits) — valeurs avant/après non montrées ; `unite_prix`, `code_douanier` affichés bruts | Référence · Champ · Avant · Après (une ligne par champ, libellés traduits pour **tous** les champs) | P7-11 |
| Créées : Référence créée | `DataTable` (+ fournisseur, rôle) | — |
| Vide « Rien ici. » | `Vide` | — |
| Pied : « Corriger les erreurs dans le tableur, puis le relire : un tableur en erreur n'écrit rien. » / « N matière(s) seront écrites. » / « Rien à écrire : le tableur dit la même chose que le catalogue. » | `Note` du pied de `Fenetre` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Télécharger le modèle (.xlsx) » | D, A | `GET matieres/tableur` | — | `matieres.xlsx`, feuille « Matières », + colonnes Priorité, Vider, Version |
| « Choisir le tableur à relire… » | D, A | `POST matieres/tableur/apercu` (multipart `fichier`) | — | aperçu avant/après |
| « Appliquer » | D, A | `POST matieres/tableur/appliquer` (même fichier, revérifié) | `Confirmer` principal « Écrire N matière(s) au catalogue ? » / « Oui, appliquer » ; blocages « Des lignes sont en erreur : corriger le tableur d'abord » / rien à écrire ; infobulle « Créer et modifier les matières lues » | succès « Tableur appliqué : le catalogue est à jour, chaque changement est au journal. » ; journal « import des matières » « N créée(s), M modifiée(s) » + une entrée par matière (avant/après), version +1 |
| « Fermer » | D, A | — | garde `sale` | R4 |

Anomalies : P7-9, P7-10, P7-11, P7-12.

---

### Onglet Classification — `/catalogue?onglet=classification&liste=composition|type_fil|titrage|unites-titrage|couleur|roles`

Gestion MP : onglet Classification (`CatalogueClassification.tsx`) → PRO : `Carte` « Classification des
matières » + `Bascule` 6 vues + `DataTable` ; compositions, types, titrages, unités de titrage,
couleurs : D, A en écriture ; rôles : D en écriture, A en lecture ; L : pas d'accès (la route 57,
qui porte aussi les unités, reste lisible par L pour les fiches).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « Un instant — chargement : la classification… » ; erreur | `Chargement`, `Erreur` | — |
| Bascule « Compositions · N », « Types de fil · N », « Titrages · N », « Couleurs · N » (actives), « Rôles · N » (tous) ; écrit `?liste=` | `Bascule` + `?liste=` ; **« Unités de titrage · N »** (actives) après « Titrages » | vue ajoutée (décision de Mohamed du 12/10/2026, DECISIONS F29) |
| — (Gestion MP : unités figées dans le code) | **Unités de titrage** : note « Les unités du titrage, telles qu'elles s'écrivent dans les références : « 2900 Dtex », « 20 Ne », « 8 lbs »… employée, elle ne se supprime ni ne se renomme : ajouter la nouvelle, désactiver l'ancienne. » ; recherche « Chercher une unité… » ; « Montrer les unités désactivées (N) » ; « Ajouter une unité » ; colonnes Code (mono, grisé si désactivée) · Libellé · Ordre · Titrages (infobulle « Titrages qui écrivent cette unité ») · Matières · État · gestes ; tri par ordre ; ligne → fenêtre « Unité de titrage » | `Note`, `DataTable`, `Interrupteur`, `Bouton` | nouveau (lot UNITES-TITRAGE) |
| Bouton « Relire les références » (pas sur Rôles) | `Bouton` | voir fenêtre Classer |
| Notes d'explication des 4 listes (« La matière du fil : PP… Le code ouvre la référence. » ; « La façon du fil… » ; « La grosseur du fil, avec son unité… » ; « Les couleurs du catalogue, telles que l'atelier les nomme… ») | `Note` | — |
| Recherche « Chercher dans les compositions… » (code, libellé, famille, valeur, unité, composition détaillée, commentaire) | `Recherche` + `Colonne.recherche` | « commentaire » → « observations » |
| Case « Montrer les valeurs désactivées (N) » (décochée) ; « N valeur(s) » | `Interrupteur` + compteur | — |
| « Ajouter une composition » / « … un type de fil » / « … un titrage » / « … une couleur » | `Bouton` principal | — |
| Colonnes : Code (mono gras) ; Libellé (compo, type, couleur ; « — ») ; Famille (compo, couleur) ; Composition détaillée (compo) ; Valeur, Unité (titrage) ; Commentaire (coupé 260 px, infobulle) ; Matières (droite) ; État (badge « active » / « désactivée ») ; actions | mêmes colonnes ; « Commentaire » → **« Observations »** | P7-3 |
| Tri par code ; ligne cliquable → fenêtre d'édition ; désactivée grisée | `DataTable` | — |
| Vide « Aucune valeur ne correspond. » / « Aucune valeur. « Relire les références » propose de les déduire des références du catalogue. » | `Vide` | — |
| **Rôles** : note « Le rôle d'une matière dans le tapis… L'ordre est celui des listes et des colonnes. » + (achats) « Seule la direction ajoute ou modifie un rôle. » | `Note` | — |
| Rangée d'ajout (D) : « Nouveau rôle (compté au kilo) : Velours… », « ordre » (défaut dernier + 1), « Ajouter le rôle » ; nouveau rôle toujours au kilo | `Form` en ligne | — |
| Tableau Rôles : Rôle (« · rôle du calcul » pour les 8 de base) · Compté (« au mètre (ml) » accent / « au kilo ») · Ordre · Matières · Qualités · (D) actions ; tri ordre puis code | `DataTable` | « Qualités » compte les qualités qui **portent** le rôle (poids > 0 ; les poids nuls ne sont plus enregistrés, P7-5) |
| Rôles de base : Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique ; au mètre : Cuir, Franges, Ruban | `blocages` serveur | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir une vue (Bascule) | D, A | — | — | `?liste=` |
| « Ajouter une composition » (… type, titrage, couleur) | D, A | ouvre la fenêtre d'édition | — | — |
| clic ligne | D, A | — | — | fenêtre d'édition (A : écriture ; rôles exclus) |
| « Désactiver » / « Réactiver » (infobulles « Ne plus la proposer pour une nouvelle matière ; celles qui la portent la gardent » / « La proposer de nouveau ») | D, A | `PUT classification/{liste}/{id}` `{actif}` | `Confirmer` « Désactiver « PP » ? » / « Oui, désactiver » (réactiver sans) | succès « « PP » désactivé : il n'est plus proposé pour une nouvelle matière. » / « « PP » réactivé. » ; confirmation ajoutée (P7-23) |
| « Supprimer » (valeur) | D, A | `DELETE classification/{liste}/{id}` | `Confirmer` « Supprimer « PP » ? » / « Oui, supprimer » ; blocage « Portée par N matière(s) : la reclasser d'abord, ou la désactiver » ; infobulle « Supprimer cette valeur, qu'aucune matière ne porte » | « « PP » supprimé. » ; 409/404 inchangés |
| « Relire les références » | D, A | `GET matieres/classement` | — | voir fenêtre Classer ; ne lit que les unités de titrage **actives** |
| « Désactiver » / « Réactiver » (unité de titrage ; infobulle « Ne plus la proposer ni la lire dans une nouvelle référence ; les titrages qui l'écrivent la gardent ») | D, A | `PUT classification/unites-titrage/{id}` `{actif}` (route 256) | `Confirmer` « Désactiver « Ne » ? » / « Oui, désactiver » | « Unité « Ne » désactivée : elle n'est plus proposée. » ; employée : l'avertissement du serveur (« « Ne » reste écrite sur N titrage(s) (M matière(s))… ces titrages la gardent. ») |
| « Supprimer » (unité de titrage) | D, A | `DELETE classification/unites-titrage/{id}?version=` (route 257) | `Confirmer` « Supprimer l'unité « Ne » ? » ; blocage = `raison_garder` du serveur (« Écrite sur N titrage(s) (M matière(s)) : la désactiver plutôt que la supprimer ») | « Unité « Ne » supprimée. » |
| « Ajouter le rôle » | D | `POST classification/roles` `{code, lineaire:false, ordre}` | grisé si vide ou envoi (raison en infobulle) | « Rôle « X » ajouté : il se choisit pour une matière et reçoit un poids dans chaque qualité. » ; 409 « Le rôle « X » existe déjà. » |
| « Modifier » (rôle) (infobulles « Changer l'ordre (le nom reste : rôle du calcul ou déjà porté) » / « Renommer ou changer l'ordre ») | D | — | nom éditable seulement si ni de base ni porté (`blocages`) | même règle écran et serveur (P7-5) |
| « Annuler » (rôle en édition) | D | — | — | — |
| « Enregistrer » (rôle) | D | `PUT classification/roles/{id}` | grisé si envoi ou nom vide ; refus « « X » est un rôle de base du calcul : il garde son nom. », « « X » est porté par des matières ou des qualités : il garde son nom. », « Le rôle « Y » existe déjà. », « Rôle introuvable. », contrôle linéaire « Le calcul compte au mètre Cuir, Franges, Ruban, et eux seuls… » | « Rôle enregistré. » |
| « Supprimer » (rôle) | D | `DELETE classification/roles/{id}` | `Confirmer` « Supprimer le rôle « X » ? » / « Oui, supprimer » ; blocages « Rôle du calcul : il ne se supprime pas » / « Porté par N matière(s) et M qualité(s) : les changer d'abord » ; infobulle « Supprimer ce rôle, qu'aucune matière ni qualité ne porte » | « Rôle « X » supprimé. » |

Anomalies : P7-3, P7-5, P7-23, P7-27.

---

### Valeur de classification (fenêtre) — sur `/catalogue?onglet=classification&liste=…`

Gestion MP : fenêtre `EditionValeur` « Composition « PP » » / « Ajouter une composition » → PRO :
`Fenetre({taille:'normale', sale})` + `Form` (pas d'adresse propre : référentiel court) ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Composition « PP » » (Type de fil / Titrage / Couleur) ou « Ajouter une composition » | titre de `Fenetre` | — |
| Note « Portée par N matière(s) du catalogue. » + « Désactivée, elle ne sera plus proposée… » ; ajout : explication + « Exemple : « PP » » (« FRZ », « 2900 Dtex », « Rouge ») | `Note` | — |
| Code (1-64, obligatoire) | `Saisie` ; longueur = celle de la matière (composition, type ≤ 32 ; titrage ≤ 48 ; couleur ≤ 64) ; MAJUSCULES pour composition et type | P7-19 |
| Libellé (compo, type, couleur ; aides « Polypropylène, Polyester… », « Frisé, Shrink, Filament… », « comme l'atelier la nomme » ; ≤ 120) | `Saisie` | — |
| Famille (compo, couleur ; suggestions ; « Synthétique, Naturel, Intrant » / « Rouges, Beiges, Gris… » ; ≤ 64) | `Selecteur` avec saisie libre | — |
| Composition détaillée (« « 100 % polypropylène » », ≤ 160) | `Saisie` | — |
| Valeur (titrage ; « lue dans le code si vide », ≤ 32) ; Unité (Dtex, Deniers, Nm, Tex, Nec ; ≤ 16) | `Saisie`, `Selecteur` : les unités **actives** du référentiel (route 57, `unites_titrage`), et l'unité déjà posée même désactivée ; aide « Dtex, Deniers, Nm, Tex, Nec, lbs (Classification › Unités de titrage) » | liste tenue dans l'écran (lot UNITES-TITRAGE) au lieu d'une constante |
| Commentaire (zone 3 lignes, ≤ 500) | `Zone` « Observations » | P7-3 |
| Case « Active (proposée pour une nouvelle matière) » | `Interrupteur` | — |
| Info « Changer le code renomme la valeur sur les N matière(s) qui la portent ; leurs références déjà écrites ne changent pas. » | `Note` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Supprimer » | D, A | `DELETE classification/{liste}/{id}` | `Confirmer` « Supprimer « CODE » ? » / « Oui, supprimer » ; blocage « Portée par N matière(s)… » ; infobulle ajoutée « Supprimer cette valeur, qu'aucune matière ne porte » | P7-23 |
| « Fermer » / « Abandonner les modifications » | D, A | — | garde `sale` | P7-22 |
| « Ajouter » / « Enregistrer » | D, A | `POST classification/{liste}` / `PUT classification/{liste}/{id}` | grisé si envoi, code vide, rien modifié (raison en infobulle) ; refus « « X » existe déjà. », « Valeur introuvable. » | ferme ; message ajouté « « X » enregistré. » ; journal avant → après |

Anomalies : P7-3, P7-19, P7-22, P7-23.

---

### Unité de titrage (fenêtre) — sur `/catalogue?onglet=classification&liste=unites-titrage`

Nouveau (lot UNITES-TITRAGE, décision de Mohamed du 12/10/2026) : `Fenetre({sale})`, D, A.
`FenetreUnite.tsx`.

| Élément | Élément PRO (composant) | Règle |
|---|---|---|
| Titre « Unité « Dtex » » ou « Ajouter une unité de titrage » | titre de `Fenetre` | — |
| Note (modification) « Écrite sur N titrage(s), portés par M matière(s). Désactivée, elle n'est plus proposée ni lue dans une nouvelle référence… » ; (ajout) « L'unité du titrage, telle qu'elle s'écrit dans les références : « 20 Ne », « 8 lbs »… » | `Note` | — |
| Code (obligatoire, ≤ 16 ; aide « comme dans les références : « Dtex », « lbs » » ou, employée, « employée : sa casse seule se corrige ») · Libellé (facultatif, ≤ 120) · Ordre (0–9999 ; vide : après la dernière) · « Active (proposée, et lue dans les références) » | `Saisie`, `Nombre`, `Interrupteur` | serveur : lettres seules (2 à 16), unique sans casse, « Den » refusé |
| Conflit de version (409 `conflit_version`) gardé sur la fiche avec « Recharger la fiche » | `BandeauConflit` | — |

| Geste | Rôles | Route API PRO | Confirmation / blocages | Message |
|---|---|---|---|---|
| « Ajouter » | D, A | `POST classification/unites-titrage` (route 255) | grisé si code vide | « Unité « Ne » ajoutée : elle se choisit pour un titrage et se lit dans les références. » ; refus « L'unité « lbs » existe déjà (« LBS »). », « Une unité de titrage s'écrit en lettres seules… » |
| « Enregistrer » | D, A | `PUT classification/unites-titrage/{id}` (route 256) | grisé sans modification | « Unité « X » enregistrée. » ou l'avertissement ; refus « « Ne » est écrite sur N titrage(s) (M matière(s)) : son code ne se change pas. Ajouter l'unité « Nx », puis désactiver « Ne ». » |
| « Supprimer » | D, A | `DELETE classification/unites-titrage/{id}?version=` (route 257) | blocage `raison_garder` | « Unité « X » supprimée. » |

---

### Classer le catalogue d'après les références (fenêtre) — sur `/catalogue?onglet=classification`

Gestion MP : fenêtre ouverte par « Relire les références » (`CatalogueClassification.tsx:539-641`,
serveur `referentiels.py:680-741`) → PRO : `Fenetre({taille:'tresLarge'})` + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Note « Chaque référence dit sa composition, son type, son titrage et sa couleur. Les cases vides sont complétées d'après elle ; ce qui est déjà renseigné n'est jamais remplacé. » | `Note` | — |
| Rien à faire : « Toutes les matières sont déjà classées : rien à compléter. » | `Vide` (ton ok) | — |
| Tableau Référence · Composition · Type · Titrage · Couleur · Code couleur (cases complétées seulement) | `DataTable` | — |
| Note « Valeurs nouvelles qui seront ajoutées à la classification : Compositions : PP, PES · Types de fil : FRZ · … » | `Note` | — |
| Règles serveur : décomposition ; couleur prise de la désignation (≤ 40, sans parenthèses) ; majuscules ; valeurs nouvelles créées avec libellé/famille connus | inchangées | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Relire les références » (infobulle « Lire les références et montrer ce qui serait complété, sans rien écrire ») | D, A | `GET matieres/classement` | — | aperçu |
| « Classer le catalogue (N matière(s)) » (infobulle « Écrire la classification déduite dans les cases vides ») | D, A | `POST matieres/classement` | `Confirmer` « Compléter N matière(s) ? » / « Oui, classer » | « Catalogue classé. » ; version +1 par matière ; journal « classement du catalogue » + avant/après par matière |
| « Fermer » | D, A | — | — | — |

---

### Onglet Fournisseurs — `/catalogue?onglet=fournisseurs`

Gestion MP : onglet Fournisseurs (`CatalogueFournisseurs.tsx:113-307`) → PRO : `Carte` + `Filtres`
(liés) + `DataTable` dans `Cadre` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /fournisseurs` (+ local, devises, articles, commandes, réceptions, pièces, délai mesuré 12 mois, livraisons mesurées, empreinte) ; `GET /fournisseurs/performance` rapproché **par nom** | `GET fournisseurs` (+ `version`, `blocages`) ; `GET fournisseurs/performance` rapproché **par id** | P7-25 |
| « Un instant — chargement : les fournisseurs… » ; erreur | `Chargement`, `Erreur` | — |
| Titre « Fournisseurs » + note « le délai et la couverture règlent le plan d'achat » | `Carte` | — |
| Recherche « Nom, pays, contact, devise, incoterm, port, banque… » (nom, code, pays, contact, téléphone, e-mail, devise, incoterm, mode de paiement, conditions, port, banque, observations) | `Recherche` + `Colonne.recherche` + `?q=` | — |
| Origine « Locaux et étrangers » / « Locaux (Maroc) » / « Étrangers (importation) » ; devise « Toutes les devises » (défaut ou pratiquée) ; état « Fournisseurs actifs » / « Actifs et désactivés » / « Désactivés seulement » ; filtres non liés | `Filtres` **liés** (A1) | A1 |
| « Effacer les filtres » dès 1 filtre (remet tout, état compris) ; « N fournisseur(s) » | dès 2 filtres, remet tout (même règle que Matières) ; compteur + « N critère(s) » | P7-31 |
| Col. « Fournisseur » (nom gras + badge « désactivé » ; code dessous) | `Colonne` + `Badge` | — |
| Col. « Pays » (ou « Maroc ») | `Colonne` | — |
| Col. « Devises » (badges « USD · 12 », défaut en accent ; « un bon de commande par devise » ; « MAD (par défaut) ») | `Colonne` + `Badge` | — |
| Col. « Délai » (« 60 j » ; dessous « mesuré 72 j », infobulle « Moyenne commande → réception validée, sur N livraison(s) en douze mois ») | `Colonne` `droite` | — |
| Col. « Couverture » (« 90 j » ou « — (réglage général) ») | `Colonne` | — |
| Col. « Paiement » (mode + délai ; conditions dessous) | `Colonne` | — |
| Col. « Incoterm » (port dessous) | `Colonne` | — |
| Col. « OTIF » (infobulle « Livraisons à l'heure, complètes et conformes ») : badge « 92 % · 12 réc. » critique / ok ; « — » | `Colonne` + `Badge` | — |
| Col. « Matières » | `Colonne` `droite` | — |
| Col. « Contact » (téléphone · e-mail dessous) | `Colonne` | — |
| Tri nom ; ligne cliquable ; désactivé grisé | `DataTable`, `lien` → `/fournisseurs/:id` | — |
| Vide « Aucun fournisseur ne correspond. » / « Aucun fournisseur pour le moment. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Les fiches des fournisseurs dans un classeur Excel ») | D, A | `GET export/fournisseurs/fiches` (avec les filtres) | — | 19 colonnes gardées (Fournisseur … Actif) ; `fournisseurs-fiches-AAAA-MM-JJ.xlsx` |
| « Nouveau fournisseur » | D, A | ouvre `/fournisseurs/nouveau` | — | — |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |
| clic ligne | D, A | `GET fournisseurs/{id}` | — | `/fournisseurs/:id` |

Anomalies : P7-25, P7-31.

---

### Fiche fournisseur (fenêtre) — `/fournisseurs/:id`, `/fournisseurs/nouveau` (sur `/catalogue?onglet=fournisseurs`)

Gestion MP : fenêtre « Fiche fournisseur » `/catalogue?onglet=fournisseurs&fournisseur=ID|nouveau`
(`CatalogueFournisseurs.tsx:309-696`) → PRO : `Fenetre({taille:'large', sale})` + `Indicateurs` +
`Onglets` (`?onglet=fiche|pieces|historique`) + `Form` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre = nom ou « Nouveau fournisseur » + badge « désactivé » | `Fenetre` + `Badge` | — |
| Kpi « Matières » (nb ; « 12 en USD, 3 en MAD » / « aucune au catalogue ») | `Kpi` | — |
| Kpi « Délai » (« 60 j » ; « mesuré 72 j sur 5 livraison(s) » / « déclaré ; pas encore de livraison mesurée » ; attention si mesuré > 1,2 × déclaré et ≥ 3 livraisons, sans raison dite) | `Kpi({formule})` : la règle « attention : mesuré au-delà de 120 % du déclaré, sur 3 livraisons au moins » dans `Formule` | P7-24 |
| Kpi « Livraisons parfaites (OTIF) » (« 92 % » / « — » ; « N réception(s) notée(s) » ; critique / ok) | `Kpi({formule})` | rapproché par id (P7-25) |
| Kpi « Score » (« 78 / 100 » ; badge du classement sans émoji ; action conseillée ; « se calcule dès la première réception ») ; Stratégique ok, Standard neutre, surveiller attention, challenger critique | `Kpi` + `Badge` | badge « À surveiller » (nom du classement, vocabulaire § 5) au lieu d'« ATTENTION » |
| Rangée « N commande(s) · M réception(s) » ; liens « Voir ses matières », « Voir l'analyse des fournisseurs » | `Note` + `LienDocument` | voir gestes |
| Volets « Fiche » (« • » si modifié), « Pièces jointes (n) » (note « Contrat, coordonnées bancaires (RIB), certificats, catalogue du fournisseur : rangés avec sa fiche. ») | `Onglets` + onglet **« Historique »** | R3 |
| **Identité et contact** : Nom (≥ 2, ≤ 160, unique sans casse) ; Code (« abréviation interne, facultative », ≤ 32) ; Pays (liste « — (MAROC) » + pays connus + « Autre pays… » → libre en majuscules + « Liste » (infobulle « Revenir à la liste des pays ») ; aides « MAROC ou vide : fournisseur local » / « un pays absent de la liste, écrit en majuscules ») ; Contact (≤ 120) ; Téléphone (≤ 60) ; E-mail (≤ 160) | `Saisie`, `Selecteur` (saisie libre) | e-mail : forme `x@y.z` contrôlée (R5) |
| **Approvisionnement** : Délai (jours, défaut 60, > 0 et ≤ 730, « de la commande à l'arrivée à l'usine : il règle le stock projeté ») ; Couverture (jours, 0, ≤ 730, « … 0 = le réglage général ») ; Devise par défaut (repli MAD, « pré-remplit une nouvelle matière ; chaque prix garde la sienne ») ; Incoterm (« — », EXW … DDP + actuelle, ≤ 20) ; Port de chargement (« d'où part la marchandise : Mersin, Ningbo… ») | `Nombre`, `Selecteur` | — |
| **Paiement** : Mode (suggestions Virement, Crédit documentaire (LC), Remise documentaire, Traite / LCN, Chèque, Espèces, Open account ; ≤ 40) ; Délai de paiement (jours, ≤ 730, « sert au calcul du crédit fournisseur ») ; Banque (« la domiciliation du paiement ») ; Conditions (placeholder « 30 % à la commande, solde à l'expédition… », ≤ 160) ; Observations (≤ 2000) | `Selecteur`, `Nombre`, `Saisie`, `Zone` | — |
| « Pour enregistrer, il manque : le nom, le délai d'approvisionnement, un délai de deux ans au plus, une couverture de deux ans au plus, un délai de paiement de deux ans au plus. » | `Bouton({manque})` | — |
| Pièces jointes (même composant, objet `fournisseur`) | `PiecesJointes` | — |
| Journal « création / modification / suppression fournisseur » | journal avant → après, onglet Historique | R3 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Créer le fournisseur » | D, A | `POST fournisseurs` | `manque` ; refus « Le fournisseur « X » existe déjà. », « Devise inconnue… » | « Fournisseur créé : ses matières peuvent maintenant le désigner. » ; passe à `/fournisseurs/:id` |
| « Enregistrer » | D, A | `PUT fournisseurs/{id}` + `version` | grisé si envoi, manque, rien changé | « Fiche enregistrée. » ; 409 → R2 (« modifié entre-temps par {nom} », P7-14) |
| « Recharger la fiche » | D, A | `GET fournisseurs/{id}` | — | R2 |
| « Désactiver » | D, A | `PUT fournisseurs/{id}` `{actif:false, version}` | `Confirmer` « Désactiver « NOM » ? Il ne sera plus proposé pour une commande ni une matière ; son historique reste. » / « Oui, désactiver » ; blocage « Enregistrer d'abord les changements » ; infobulle « Ne plus le proposer » | « Fournisseur désactivé. » |
| « Réactiver » | D, A | `PUT fournisseurs/{id}` `{actif:true, version}` | blocage « Enregistrer d'abord les changements » ; infobulle ajoutée « Le proposer de nouveau » | P7-23 ; « Fournisseur réactivé. » |
| « Supprimer » | D, A | `DELETE fournisseurs/{id}` | `Confirmer` « Supprimer définitivement « NOM » ? » / « Oui, supprimer » ; `blocages` serveur complets : matières, commandes, réceptions, **lots, opérations, factures**, pièces jointes (« Il a 3 matière(s), 2 commande(s)… à retirer d'abord : le désactiver plutôt ») ; infobulle « Supprimer un fournisseur qui n'a jamais servi » | P7-4 ; ferme |
| « Fermer » / « Abandonner les modifications » | D, A | — | garde `sale` | P7-22 |
| « Voir ses matières » | D, A | — | si ≥ 1 matière | → `/catalogue?onglet=matieres&fournisseur=ID` |
| « Voir l'analyse des fournisseurs » | D, A | — | — | → `/analyse?onglet=fournisseurs&fournisseur=ID` (ouvre ses réceptions ; corrige P8-1) |
| « Joindre un document… », ouvrir, « Retirer » | D, A | `POST pieces`, `GET pieces/{id}/fichier`, `DELETE pieces/{id}` | `Confirmer` « Retirer ce document ? » | comme la fiche matière |
| choisir « Pays » « Autre pays… » / « Liste » | D, A | — | — | — |
| ouvrir l'onglet « Historique » | D, A | `GET historique/fournisseur/{id}` | — | nouveau |

Anomalies : P7-4, P7-14, P7-22, P7-23, P7-24, P7-25.

---

### Codes douaniers (vus depuis le catalogue) — `/reglages?onglet=codes`

Gestion MP : § 1.8 (onglet « Douane » de Réglages, direction seule ; liste de choix dans la fiche
matière) → PRO : décrit en Partie 8 (« Codes douaniers ») ; D écriture, **A lecture** (l'onglet lui
est désormais visible : le refus « Code douanier inconnu » qui l'y renvoie devient lisible).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Écran inaccessible aux achats alors que le message serveur les y envoie | A lit `/reglages?onglet=codes` ; message « … demander à la direction de l'ajouter (Réglages › Codes douaniers). » | P7-15 |
| Format non contrôlé à l'écran ; « Value error, … » | contrôle `\d[\d.]{1,19}` à la frappe et au serveur, message « Un code douanier s'écrit en chiffres, éventuellement séparés de points (ex. 5402.47.00.00). » | P7-16 |
| Pas de filtre actifs / désactivés ; bouton « Annuler » | filtre d'état ; « Fermer » / « Abandonner les modifications » (garde `sale`) | P7-16 |
| Deux hooks `useCodesDouaniers` sur la même clé | une seule requête `GET codes-douaniers` (TanStack Query) | P7-17 |

Gestes : voir Partie 8 (`POST/PUT/DELETE codes-douaniers`).

---

### Qualités et recettes (page) — `/qualites?onglet=qualites|nomenclature`

Gestion MP : page « Qualités et recettes » `/qualites` (`?onglet=nomenclature`, `?qualite=ID`) →
PRO : `/qualites` (`Page`, `EnTete`, `Indicateurs`, `Onglets`) ; D écriture ; A lecture (coûts
compris) ; L lecture **sans coût ni prix** (GMP : aucun accès).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /qualites` (base mensuelle, poids, saisonnalité, recette, contrôle, coût, kg/m², fabrications, empreinte), `/classification`, `/articles`, `/qualites/facteurs-cout`, `/nomenclature` | `GET qualites` (facteurs de coût fondus ; coûts masqués pour L), `GET classification`, `GET matieres`, `GET nomenclature` | route `facteurs-cout` fondue (contrat) |
| « Un instant — chargement : les qualités… » ; erreur | `Chargement`, `Erreur` | — |
| Titre « Qualités et recettes » ; sous-titre D « … Le plan se saisit dans la page Production. » / A « … Lecture seule : la direction les modifie. » | `EnTete` + ligne par rôle (L : comme A) | — |
| « Exporter en Excel » (colonnes Qualité, Nom, Fabriquée, Rôle, Référence, Fournisseur, Part du rôle (%), kg / m², Prix d'achat, Unité du prix, Coût / m² (MAD), Coût de la qualité / m² (MAD)) | `ExportExcel` → `GET export/qualites` (D, A) | — |
| « Nouvelle qualité » (D) | `Bouton` principal | — |
| Kpi « Qualités fabriquées » (actives ; « N arrêtée(s) ») | `Kpi({formule})` | — |
| Kpi « Recettes incomplètes » (actives non conformes ; codes ou « chaque rôle fait 100 % » ; critique / ok) | `Kpi({formule})` ; même base que la Nomenclature (actives), arrêtées signalées à part « (arrêtées : n) » | P7-27 |
| Kpi « Plan mensuel » (« 12 345 m² » = Σ base des actives ; « avant saisonnalité · le saisir » → plan) | `Kpi({formule, lien:'/production?onglet=plan'})` | — |
| Kpi « Coût matière moyen » (« 54,21 MAD/m² » = Σ(coût × base)/Σ base, « pondéré par le plan ») | `Kpi({formule})` ; masqué pour L | — |
| Onglets « Qualités (N) », « Nomenclature (N lignes) » | `Onglets` | changer d'onglet ne ferme plus une fiche ouverte (`/qualites/:id` garde l'onglet de la liste, P7-29) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Les qualités et leurs recettes, fil par fil, dans un classeur Excel ») | D, A | `GET export/qualites` | — | infobulle « … matière par matière … » (P7-1) |
| « Nouvelle qualité » | D | ouvre `/qualites/nouvelle` | — | — |
| lien « le saisir » (Plan mensuel) | C | — | — | → `/production?onglet=plan` |
| choisir un onglet | C | — | — | `?onglet=` |

Anomalies : P7-27, P7-29.

---

### Onglet Qualités — `/qualites?onglet=qualites`

Gestion MP : onglet « Qualités » → PRO : `Carte` « Les qualités » + `Filtres` + `DataTable` ; C.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| « N qualité(s) », case « avec les arrêtées », recherche « Code, nom, fil de la recette… » placées dans l'en-tête de carte | rangée `Filtres` sous le titre ; placeholder « Code, nom, matière de la recette… » | P7-26, P7-1 |
| Col. « Qualité » (code gras + badge « arrêtée » ; nom dessous) | `Colonne` + `Badge` | — |
| Une colonne par rôle utilisé (code ; « kg/m² » / « ml/m² » dessous ; infobulle « Poil en kg/m² ») : poids ou « — », 4 déc. | `Colonne` dynamique `droite` | — |
| « Poids recette » kg/m² (infobulle « Ce que pèsent les fils de la recette pour un m² ») | `Colonne` | infobulle « … les matières de la recette … » |
| « Coût » MAD/m² (2 déc.) | `Colonne` ; absente pour L | — |
| « Plan » m²/mois | `Colonne` | — |
| « Recette » : badge critique « Poil 98,0 % · Ruban 0,0 % » ; ok « juste · N fil(s) » ; attention « aucun fil » | `Badge` : « juste · N matière(s) », « aucune matière » | P7-1 |
| Tri code ; ligne cliquable ; arrêtée grisée | `lien` → `/qualites/:id` | — |
| Vide « Aucune qualité ne correspond. » / « Aucune qualité pour le moment. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| case « avec les arrêtées » | C | — | — | `Filtres` |
| clic ligne | C | `GET qualites/{id}` | — | `/qualites/:id` |

Anomalies : P7-1, P7-26.

---

### Onglet Nomenclature — `/qualites?onglet=nomenclature`

Gestion MP : onglet « Nomenclature » → PRO : `Carte` + `Filtres` + `DataTable` ; C (coûts et prix
masqués pour L).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Nomenclature : chaque fil de chaque qualité » | « Nomenclature : chaque matière de chaque qualité » | P7-1 |
| Note « N ligne(s) · recettes à corriger : A, B » / « · toutes les recettes sont justes » (toutes qualités) ; infobulle « Coût au m² = kg/m² × prix au kilo × cours de la devise, perte matière comprise. Cliquer sur une ligne ouvre sa qualité. » | `Note` + `Formule` ; base = qualités actives (arrêtées signalées à part) | P7-27 |
| Recherche « Qualité, fil, rôle, fournisseur… » (qualité, référence, rôle, nature, désignation, fournisseur) dans l'en-tête de carte | rangée `Filtres` ; « Qualité, matière, rôle, fournisseur… » | P7-26 |
| « Un instant — chargement : la nomenclature… » ; erreur | `Chargement`, `Erreur` | — |
| Col. Qualité (dessous en rouge « recette à corriger ») · Rôle (ou « matière inconnue ») · Référence (« nature · désignation ») · Fournisseur · Part (%) · kg / m² (dessous ml / m²) · Prix d'achat (« 12,50 USD / kg » ; infobulle au mètre « soit 4,10 USD / kg par la densité ») · Coût (MAD/m²) | `DataTable` ; Prix et Coût absents pour L | — |
| Ordre du moteur ; ligne → qualité en gardant l'onglet | `lien` → `/qualites/:id` (retour à `?onglet=nomenclature`) | — |
| Vide « Rien ne correspond. » / « Aucune recette saisie. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| clic ligne | C | `GET qualites/{id}` | — | `/qualites/:id` |

Anomalies : P7-1, P7-26, P7-27.

---

### Nouvelle qualité (fenêtre) — `/qualites/nouvelle`

Gestion MP : fenêtre « Nouvelle qualité » (direction) → PRO : `Fenetre({taille:'large', sale})` + `Form` ; D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `sale` si code, nom ou un poids saisi | `Fenetre({sale})` | — |
| « Code » (aide « tel qu'il figure sur les ordres de fabrication », focus, obligatoire, 1-32, unique) | `Saisie` | — |
| « Nom » (≤ 120) | `Saisie` | — |
| Intertitre « Poids d'un m² de tapis, rôle par rôle (laisser à zéro les rôles qui n'entrent pas) » ; un champ par rôle (aide « mètres linéaires par m² de tapis » / « kilos par m² de tapis » ; unité ml/m² / kg/m²) | `Nombre` par rôle (≥ 0) | poids nuls non enregistrés (P7-5) |
| Note « Une fois créée, la qualité s'ouvre sur sa recette. Son plan se saisit ensuite dans la page Production. » | `Note` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Annuler » / « Abandonner » | D | — | garde `sale` | P7-22 |
| « Créer la qualité » (« Création… ») | D | `POST qualites` `{code, nom, actif:true, poids:[{role_id, poids}]}` (liste par id de rôle) | grisé si code vide ou envoi (raison en infobulle) ; refus « La qualité « X » existe déjà. », « Rôle inconnu : « X ». », « Un poids au m² ne peut pas être négatif. » | ouvre `/qualites/:id?onglet=recette` ; journal « création qualité » |

---

### Fiche qualité (fenêtre) — `/qualites/:id?onglet=recette|plan|versions|historique`

Gestion MP : fenêtre « Qualité CODE — nom » `/qualites?qualite=ID` (`QualiteDetail.tsx`) → PRO :
`Fenetre({taille:'tresLarge', sale, pied})` + `Indicateurs` + `Onglets` ; D écriture ; A lecture ;
L lecture sans coût ni prix. Le volet GMP « Fiche et poids au m² » est **fondu en tête de l'onglet
`recette`** (le contrat ne garde que recette, plan, versions, historique) : code, nom, active et poids
par rôle s'éditent au-dessus de la recette qu'ils commandent.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Titre « Qualité CODE — nom » + badge « arrêtée » | `Fenetre` + `Badge` | — |
| A : bandeau « Lecture seule : seule la direction modifie les qualités et les recettes. », champs grisés, **pas de pied** | `Note` + champs en lecture ; pied réduit à « Fermer » | P7-30 |
| `sale` = D et (fiche ou parts modifiées) ; saisie tenue au-dessus des volets ; **un seul « Enregistrer »** fiche puis recette (deux requêtes) | un seul « Enregistrer » → **une seule requête** `PUT qualites/{id}` portant fiche + recette (transaction unique) | P7-8 |
| Kpi « Coût matière » (Σ coût/m² ; « selon la saisie, perte matière comprise » / « perte matière comprise ») | `Kpi({formule})` ; masqué pour L | — |
| Kpi « Poids de la recette » (Σ kg/m² ; « ce que pèsent les fils d'un m² ») | `Kpi` ; « … les matières d'un m² » | P7-1 |
| Kpi « Recette » (« N rôle(s) faux » / « N rôle(s) sans fil » / « Juste » ; « N fil(s) · M rôle(s) » ; critique / attention / ok) | `Kpi` ; « sans matière », « N matière(s) » | P7-1 |
| Kpi « Plan » (« 1 200 m²/mois » ; « coût d'un mois : 65 052 MAD ») | `Kpi({formule})` ; coût masqué pour L | — |
| Formules à la frappe : ml/m² = part/100 × poids ; kg/m² = ml/m² × densité ou part/100 × poids ; coût/m² = kg/m² × prix au kilo × cours × perte ; juste si \|Σ − 100\| ≤ 0,01 ; fautif ; sans fil ; bloquant = sans fil si active | mêmes formules (`aide.json`, `Formule`) ; **même règle au serveur** : rôle sans matière bloquant pour une qualité active seulement, accepté avec avertissement si arrêtée | P7-6 |
| Volets « Recette (N lignes) », « Fiche et poids au m² » (« • »), « Plan de production », « Versions (N) » | onglets `recette` (fiche + poids + recette), `plan`, `versions`, **`historique`** | R3 |
| **Recette** : note « Dans chaque rôle utilisé, les parts des fils totalisent 100 %… en rouge, le rôle n'y est pas encore. » | `Note` (« … des matières … ») | P7-1 |
| Bandeau « N ligne(s) de la recette visent une matière disparue du catalogue (REF1, REF2) : elles seront retirées à l'enregistrement. » | `Erreur` | — |
| Tableau groupé par rôle : ligne de rôle « Poil · 0,8000 kg/m² » (rouge si faux) ; colonnes **« Fil »** (référence ; « nature · désignation ») · Fournisseur · Part du rôle (%) (total vert / rouge) · ml / m² (infobulle) · kg / m² (infobulle « 0,1200 ml/m² × 0,0500 kg/ml » ; « densité manquante ») · Prix d'achat (« 12,50 USD / kg » ; « 4,10 / kg ») · Coût / m² · Sert aussi à (« le rôle est complet » / « aucun fil : en ajouter un ci-dessous » / « 2,00 % de trop » / « il manque 2,00 % » ; codes des autres qualités) · (D) « Retirer » | `DataTable` en saisie ; « Fil » → **« Référence »** ; « aucune matière : en ajouter une ci-dessous » ; Prix et Coût absents pour L | P7-1 |
| Pied « Toute la recette » · Σ kg/m² · Σ coût | pied de totaux | — |
| Vide « Aucun rôle n'a de poids : renseigner d'abord les poids au m² (onglet Fiche et poids au m²). » | `Vide` « … (en tête de cet onglet). » | — |
| Ajout (D) : « Ajouter un fil (il rejoint son rôle) : » + recherche « Taper quelques mots : référence, couleur, rôle, fournisseur… » ; options = matières actives du rôle affiché pas déjà là ; « REF — désignation · rôle · fournisseur », détail « rôle · 12,50 USD / kg » ; nouvelle ligne = reste du rôle | `SelecteurMatiere` ; « Ajouter une matière (elle rejoint son rôle) : » | P7-1 |
| Bandeau « Rôle(s) avec un poids au m² mais sans matière : Ruban. Leurs kilos manqueraient… avant d'enregistrer. » | `Blocages` | — |
| **Fiche et poids** : « Code » (obligatoire), « Nom », case « qualité fabriquée (active) » ; intertitre « Poids d'un m² de tapis, rôle par rôle » ; note « Un rôle à zéro n'entre pas dans la qualité… Une qualité arrêtée ne compte plus dans le plan. » ; poids par rôle | bloc en tête de `recette` (`Form`) | poids nuls non enregistrés (P7-5) |
| **Plan de production** (lecture) : bandeau « Le plan de production (base mensuelle et saisonnalité) se saisit dans la page Production, toutes qualités ensemble. » ; « Base mensuelle : 1 200 m² par mois ordinaire (coefficient 1) » ; « Sur l'année : 14 400 m² » (+ « — qualité arrêtée : elle ne compte pas dans les besoins ») ; grille 12 mois (infobulle « coefficient 1,20 ») ; note « m² prévus chaque mois… La croissance annuelle réglée s'y ajoute pour les mois à venir. » | onglet `plan` (`Definitions`, `Grille`) + liste des versions du plan (`GET qualites/{id}/plan/versions`, lecture) | versions du plan ajoutées ; `PUT qualites/{id}/plan` reste écrit par Production (P7-33) |
| **Versions** : version née à chaque changement de lignes ou de poids (photo + poids, signée) ; pas de date d'effet ; « Lecture des versions… » ; vide « Aucune version enregistrée : la recette n'a pas été modifiée depuis la mise en service du suivi des versions. » | onglet `versions` ; date d'effet = horodatage (décision gardée, dite dans l'aide) | P7-32 |
| Tableau des versions : Enregistrée le (« en vigueur » sous la 1re) · Par (« reprise ERP Fil » / « — ») · Fils ; choisie surlignée ; défaut la 2e | `DataTable` ; « Fils » → « Matières » | P7-1 |
| Comparaison : « Version du … par X, comparée à la recette en vigueur : N différence(s). » / « identique. » ; « Poids au m² : Poil 0,800 (en vigueur : 0,750)… » / « non gardés avec cette version… » ; tableau Rôle · Référence · Part dans cette version · Part en vigueur · Écart (« ajouté depuis », « retiré depuis », « +2,00 pt ») | `Note` + `DataTable` | — |
| Note « Pour revenir à cette version : la direction, sans autre modification en cours dans la fenêtre. » | `Bouton({blocages})` (texte en infobulle) | — |
| Bas : « Contrôle enregistré : Poil 98,0 % · Ruban 0,0 %. » ; conflit « Elle a été modifiée sur un autre poste : la recharger avant de refaire la modification. » + « Recharger la qualité » | `Note` ; R2 (« modifiée entre-temps par {nom} ») | P7-14 |
| État du pied : « À corriger avant d'enregistrer : Poil, Ruban. » / « Non enregistré : la fiche et la recette. » / « Aucune modification. » | `Note` du pied | — |
| `avertissement` serveur de `PUT /qualites/{id}` (rôles sans matière) jamais affiché | `Messages` (avertissement) après enregistrement | P7-7 |
| Arrêter / remettre en service note une version du plan (« CODE : arrêtée » / « remise en service ») ; tolérance 0,01 (= C01) | inchangé | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir une matière à ajouter | D | — (brouillon local) | — | `SelecteurMatiere` |
| « Retirer » (infobulle « Retirer ce fil de la recette ») | D | — (brouillon) | sans confirmation (réversible avant « Enregistrer ») | infobulle « Retirer cette matière de la recette » |
| « Enregistrer » (« Enregistrement… ») | D | `PUT qualites/{id}` `{code, nom, actif, poids:[{role_id, poids}], recette:[{matiere_id, pourcentage}], motif, version}` (une transaction) | grisé si envoi, rôle faux, rôle bloquant (qualité active), code vide, rien modifié ; refus « La qualité « X » existe déjà. », « Rôle inconnu », poids négatif, « Matière inconnue dans la recette. », « « REF » figure deux fois dans la recette. », « Dans chaque rôle, la recette doit faire 100 % : Poil 98 %. », « La recette oublie le rôle Ruban (0,12 au m²)… » (pluriel), 409 version | « Qualité enregistrée : les besoins, les coûts et le plan d'achat sont recalculés. » ; tout ou rien (P7-8) ; `PUT qualites/{id}/recette` reste pour une recette seule |
| « Annuler les modifications » / « Fermer » | D (A, L : « Fermer ») | — | garde `sale` (« Annuler les modifications » demande « Les abandonner ? ») | P7-22, P7-30 |
| « Supprimer » | D | `DELETE qualites/{id}?version=` | `Confirmer` « Supprimer la qualité CODE, sa recette et son plan ? » / « Oui, supprimer » ; blocage « Fabriquée par N ordre(s) : elle appartient à l'historique. La désactiver plutôt (fiche). » ; infobulle « Supprimer une qualité qui n'a jamais été fabriquée » | ferme |
| « Recharger la qualité » | D | `GET qualites/{id}` | — | R2 |
| « Ouvrir le plan de production » | C | — | — | → `/production?onglet=plan` |
| choisir une version (ligne) | C | `GET qualites/{id}/versions` | — | — |
| « Revenir à cette version » | D | `POST qualites/{id}/versions/{vid}/restaurer` `{motif, version}` | `Confirmer` danger, motif exigé « Pourquoi revenir à cette version ? (obligatoire) » (≤ 300) ; question « Remplacer la recette en vigueur par cette version ? » / « Oui, revenir à cette version » ; blocages « Écrire d'abord le motif », saisie en cours, version en vigueur, matières disparues (« Ces matières n'existent plus au catalogue : X, Y. La version ne peut pas revenir telle quelle. ») ; infobulles « La recette reprend les parts et les poids au m² de cette version ; une nouvelle version est signée » / « … avec les poids au m² de la version suivante qui les a gardés… » | « Recette revenue à cette version, parts et poids au m² : une nouvelle version, signée et motivée, est enregistrée. » ; journal « CODE : retour à la version du … — motif » |
| choisir un onglet | C | — | — | `?onglet=` |
| ouvrir l'onglet « Historique » | C | `GET historique/qualite/{id}` | — | nouveau |

Anomalies : P7-1, P7-5, P7-6, P7-7, P7-8, P7-14, P7-22, P7-23, P7-30, P7-32, P7-33.

---

### Anomalies GMP corrigées — Partie 7

1. « Fil » / « Fils » en en-tête et titres → « Référence », « Matières », « Nomenclature : chaque matière de chaque qualité », « Code, nom, matière de la recette… » (vocabulaire § 5).
2. Deux graphies « USD/kg » et « USD / kg » → composant `Prix` unique : « 12,50 USD / kg » partout.
3. « Commentaire » (classification) → « Observations ».
4. Suppression d'un fournisseur cliquable puis refusée (lots, opérations, factures) → `blocages` serveur complets, bouton grisé avec la raison.
5. Renommer un rôle refusé au clic (poids à 0) → les poids nuls ne s'enregistrent plus ; « porté » = même définition écran et serveur, livrée par `blocages`.
6. Recette d'une qualité arrêtée refusée au clic → une seule règle : rôle sans matière bloquant pour une qualité active, accepté avec avertissement si arrêtée (serveur aligné).
7. Avertissement serveur ignoré → affiché dans `Messages` après l'enregistrement.
8. Enregistrement fiche + recette en deux temps → une seule requête `PUT qualites/{id}` (transaction unique).
9. Import tableur moins strict que la fiche → mêmes contrôles (bornes, longueurs, négatifs, contenance, doublons, version) ; fournisseur exigé seulement en service.
10. Messages techniques du tableur → libellés de colonne, accords justes, renvoi juste (devise → Réglages › Devises ; code douanier → direction).
11. `NOMS_CHAMPS` incomplet, avant/après non montrés → libellés pour tous les champs, colonnes Avant / Après dans l'aperçu.
12. On ne peut pas vider une case, priorité non importable → colonne « Vider », colonne « Priorité dans le groupe », règle dite dans le mode d'emploi de la fenêtre.
13. « Type de fil inconnue », « Titrage inconnue » → accord par liste (« inconnu »).
14. « modifié(e) » générique → message de version accordé à l'objet, avec le nom de l'auteur (R2).
15. Codes douaniers : renvoi des achats vers un écran fermé → A lit `/reglages?onglet=codes` ; message « demander à la direction de l'ajouter ».
16. Codes douaniers : format non contrôlé, « Annuler », pas de filtre d'état → contrôle à la frappe, « Fermer » gardé par `sale`, filtre d'état.
17. Doublon de hook `useCodesDouaniers` → une requête, une clé, invalidation globale.
18. Branches lecture seule mortes → vivantes et voulues : L lit les matières (sans prix), A lit les qualités, droits par rôle du registre `routes.ts`.
19. Longueurs incohérentes (classification 64 / matière 32-48) et majuscules à un seul endroit → longueurs d'une seule déclaration ; majuscules dans les deux saisies.
20. Unité d'achat « ml » tapable, bornes non contrôlées → liste fermée sans « ml », bornes à la frappe (R5).
21. Désactiver revalide toute la fiche → `PUT` de la fiche entière (`actif: false`, `version`), le serveur ne revalide que ce qui change (H-28).
22. Boutons « Abandonner… » / « Annuler les modifications » sans question → tous passent par la garde `sale`.
23. Gestes sans infobulle → infobulle sur « Réactiver » fournisseur, « Supprimer » valeur, « Retirer » ; `Confirmer` ajouté à « Désactiver » une valeur.
24. Délai en ton attention sans raison → `Kpi({formule})` dit la règle (mesuré > 120 % du déclaré, ≥ 3 livraisons).
25. OTIF et score rapprochés par le nom → par id du fournisseur.
26. Recherche des Qualités / Nomenclature dans l'en-tête de carte → rangée `Filtres` sous le titre.
27. Compteurs incohérents → onglet Classification = valeurs actives (comme la Bascule) ; Recettes incomplètes et Nomenclature sur la même base (actives, arrêtées signalées à part).
28. `?fournisseur_filtre=` survit à « Effacer les filtres » → filtres dans l'adresse effacés avec eux (`useFiltresAdresse`).
29. Changer d'onglet ferme la qualité ouverte → la fiche a son adresse ; l'onglet de la liste est gardé dessous.
30. Pas de « Fermer » pour les achats sur une qualité → pied toujours présent (« Fermer »).
31. « Effacer les filtres » n'efface pas l'état (matières) mais l'efface (fournisseurs) → même règle : tout revient au défaut, état compris.
32. Pas de date d'effet de recette → décision gardée : une version vaut à son horodatage ; dit dans l'aide de l'onglet Versions.
33. `PUT qualites/{id}/plan` appelé par Production seulement → gardé ; l'onglet `plan` de la fiche est en lecture avec ses versions et un lien.

### Comptes de la partie 7

- Écrans PRO : 2 pages (`/catalogue`, `/qualites`) ; Codes douaniers logés dans `/reglages` (Partie 8).
- Onglets / sous-vues : 23 GMP → 24 PRO (catalogue 3 ; Bascule classification 5 ; fiche matière 5 dont Historique ; fiche fournisseur 3 dont Historique ; tableur 3 ; qualités 2 ; fiche qualité 4 — « Fiche et poids » fondu dans `recette`, `historique` ajouté).
- Fenêtres : 8 GMP → 8 PRO (fiche matière, tableur, valeur de classification, classer le catalogue, fiche fournisseur, code douanier [Partie 8], nouvelle qualité, fiche qualité) + 1 panneau d'ajout en ligne ; 4 fiches à adresse stable (matière, fournisseur, qualité, tableur).
- Gestes : 71 GMP, tous repris ; 82 lignes PRO (gestes GMP éclatés ligne par ligne + 3 « Historique », « choisir un onglet », « choisir un volet », « Recharger »).
- Anomalies : 33 traitées (P7-1 à P7-33).

### Routes demandées par la partie 7 (reportées dans API-PRO § 1.24)

Aucune : chaque geste a sa route dans le contrat. Précisions de contrat (pas de nouvelle route) :
`PUT matieres/{id}` et `PUT fournisseurs/{id}` reçoivent la fiche entière (API-PRO § 1.24, lot D1) ; désactiver ne revalide que ce qui change ;
`PUT qualites/{id}` accepte `recette` dans le même corps (transaction unique) ;
`GET matieres/tableur` ajoute les colonnes « Priorité dans le groupe », « Vider », « Version ».

---

## Partie 8 — Analyse, Réglages (partagés entre Réglages et Administration), Bilan du mois

Source : `docs/heritage/ECRANS.md` lignes 6308-7785 (dont la synthèse). Mêmes règles communes R1-R10
que la partie 7 (garde `sale`, `Confirmer` sur la ligne, `Bouton({manque, blocages})`, une seule
source d'aide, vocabulaire § 5). Rappels GMP repris tels quels : refus 403 « Cette action est
réservée à : … » ; 401 « Connectez-vous pour continuer. » / « Ce compte n'est plus actif. » ;
réseau « Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G). » ; formats `montant`
(« 17,4 M MAD » au-delà du million, montant exact en infobulle — `Montant`), `part` (« 4,2 % »),
`prixUnite` (2 déc., 4 sous 0,1), `jours` (« 60 j »), `moisLisible` (« sept. 2026 ») ; `Confirmer`
« {question} · Non · {oui} » sur place ; `LigneVide` → `Vide`.

**Partage des Réglages GMP (11 onglets) en PRO**

| Onglet GMP | PRO | Rôles PRO |
|---|---|---|
| parametres (familles 1-9, sauf 3 réglages ci-dessous) | `/reglages?onglet=parametres` | D écrit ; A lit ; L refusé |
| parametres › Société › « Période close jusqu'au » | `/reglages?onglet=periode` (`PUT periode-close`, motif) | D écrit ; A lit |
| parametres › « Méthode de calcul » | texte d'aide (`aide.json` : aide « ? » de `/reglages` + Mode d'emploi › Les calculs) — plus un réglage | tous (lecture) |
| parametres › Société › « Courriel du lundi : à qui » | `/administration?onglet=courriel` (famille technique) | D, T |
| parametres › Société › « Adresse du serveur pour les téléphones » | `/administration?onglet=technique` (famille technique) | D, T |
| devises | `/reglages?onglet=devises` | D, A écrivent |
| magasins | `/reglages?onglet=magasins` | D écrit ; A lit |
| postes | `/reglages?onglet=postes` | D écrit ; A lit |
| codes | `/reglages?onglet=codes` | D écrit ; A lit |
| comptes | `/administration?onglet=comptes` | T, D |
| sauvegardes | `/administration?onglet=sauvegardes` | T, D |
| journal | `/administration?onglet=journal` | T, D |
| courriel | `/administration?onglet=courriel` | T, D (aperçu chiffré : D seule) |
| serveur | `/administration?onglet=serveur` | T, D |
| telephone | `/administration?onglet=telephone` | T, D |
| (aucun) | `/administration?onglet=appareils` (nouveau) | T, D |

---

### Analyse (page) — `/analyse?onglet=valorisation|matrice|historique|opportunites|fournisseurs|revient|echeancier|controles|production`

Gestion MP : page « Analyse » `/analyse` (`Analyse.tsx`) → PRO : `/analyse` (`Page`, `EnTete`,
`Onglets`, `useOngletAdresse`) ; D, A (L : `EcranReserve`).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Menu « Pilotage › Analyse », infobulle « Prix, fournisseurs, valorisation, contrôles » ; pastille = `controles.anomalies` de `/cockpit` (relu 180 s), lien vers `?onglet=controles` | `BarreLaterale` (pastille, `GET cockpit`) | inchangé |
| Les neuf onglets pour D et A | idem | P8-25 : décision gardée (REGLES § 4 à mettre à jour) |
| Défaut : D → `valorisation`, A → `matrice` ; `?onglet=prix` → `matrice` ; inconnu → défaut ; défaut = adresse nue | `useOngletAdresse` (défaut par rôle, alias gardé) | — |
| `?fournisseur=` lu comme recherche des Fournisseurs (jamais rempli) | `?onglet=fournisseurs&fournisseur=ID` ouvre la fenêtre « ses réceptions » (lien de la fiche fournisseur) | P8-1 |
| Titre « Analyse » ; sous-titre = phrase de l'onglet (9 phrases exactes) + « · Réceptions : bobines · pesées » (liens, infobulles « Le poids moyen des bobines, fil par fil, au fil des réceptions » / « Chaque pesée face au bon de livraison ») | `EnTete({titre, fil, actions, aide})` ; phrases dans `aide.json` ; liens → `/receptions?onglet=bobines`, `/receptions?onglet=pesees` | infobulle « … matière par matière … » |
| Onglets : « Valeur » (infobulle « Valorisation »), « Matrice » (compteur lignes), « Prix payés » (compteur), « Opportunités » (infobulle « Opportunités d'économies », compteur), « Fournisseurs », « Coût de revient », « Échéancier », « Contrôles » (compteur = contrôles en anomalie), « Production » ; tient sur une ligne à 1366 px | `Onglets` (libellé court + infobulle, compteurs) | — |
| Page charge `/prix/matrice`, `/prix/historique`, `/opportunites?…`, `/controles` pour les compteurs ; l'en-tête du fichier prétend le contraire | mêmes requêtes, en parallèle, cache partagé avec les onglets ; texte faux retiré | P8-26 |
| (Bilan du mois offert au seul Cockpit) | action d'`EnTete` « Bilan du mois » (D, A) | P8-24 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir un onglet | D, A | — | — | `?onglet=` |
| lien « bobines » | D, A | — | — | → `/receptions?onglet=bobines` |
| lien « pesées » | D, A | — | — | → `/receptions?onglet=pesees` |
| « Bilan du mois » (nouveau ici) | D, A | `GET documents/bilan?mois=` | mois AAAA-MM, pas futur | voir « Bilan du mois » |

---

### Valorisation — `/analyse?onglet=valorisation`

Gestion MP : onglet Valorisation (`AnalyseValorisation.tsx`) → PRO : `Indicateurs` + `Carte` +
`Filtres` + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /valorisation?date_reference=` (absent = aujourd'hui ; 400 « date de référence hors période : {date} » hors 2000-2100) ; résultat précédent gardé pendant le rechargement | `GET valorisation?date_reference=` (TanStack `placeholderData`) | — |
| Calcul : stock = magasins (quarantaine comprise) + sur les métiers ; valeur = CMUP × stock ; écart = valeur − stock × prix catalogue/kg × cours du jour | inchangé ; formules dans `aide.json` | — |
| Kpi « Valeur du stock détenu » (`montantCourt` ; « {kg} kg » ; infobulle « {montant} au {date} ») | `Kpi({formule})` + `Montant` | — |
| Kpi « Dans les magasins » | `Kpi` | — |
| Kpi « Sur les métiers (info) » : détail « {kg} kg montés, **hors stock** » ; infobulle « … compris dans la valeur du stock » | détail « {kg} kg montés, compris dans le stock » — un seul texte | P8-2 |
| Kpi « Matières en stock » (« n sur N » ; « avec stock ou fil monté ») | `Kpi` | — |
| Kpi « Écart avec le catalogue » (« coût payé − catalogue » ; infobulle « … frais d'approche, hausse non reportée ») ; attention si \|écart\| > 2 % (en dur) | `Kpi({formule})` : seuil fixe 2 % écrit dans la formule | P8-4 |
| Titre « Valeur par matière, la plus lourde d'abord — {n} matière(s), {total filtré} » | `Carte` | — |
| « Au » : « aujourd'hui », 12 fins de mois « fin {mois} ({jj/mm/aaaa}) », « autre date… » (champ date, max aujourd'hui) ; infobulle « La valeur au soir de ce jour : le journal rejoué jusque-là » | `Selecteur` + `DateChamp` (max = aujourd'hui serveur) | — |
| Recherche « Référence, fournisseur, devise… plusieurs mots » (référence, nature, fournisseur, devise) | `Recherche` + `Colonne.recherche` | — |
| Case « montrer aussi les matières sans stock » | `Interrupteur` | — |
| « Effacer les filtres » dès 1 filtre | dès 2 filtres (A1) | — |
| Note (date passée) « Au {date} au soir : le stock et le coût moyen rejoués sur le journal jusqu'à ce jour-là. Le fil monté sur les métiers n'y est pas compté… » | `Note` « Au {date} au soir : le stock et le coût moyen rejoués sur le journal jusqu'à ce jour-là. » ; le fil monté **y est compté** (montages en vigueur ce soir-là, rejoués sur l'historique `montage_evenement`, `services/pilotage_machine.py`) | phrase « pas compté » supprimée (U8, lot D8) ; écart voulu à Gestion MP, qui ne le compte qu'au jour même |
| Col. Référence (nature dessous) · Fournisseur · Magasins (kg ; infobulle « En kg, le cuir, les franges et le ruban compris ») · Sur les métiers (info) (« — ») · Stock détenu (gras ; « ≈ ml ») · Coût moyen (MAD) (« / kg » ; infobulle CMUP) · Prix catalogue (« {devise} / kg ») · Valeur (MAD) (entier) · Écart catalogue (« — » si 0) | `DataTable` (`unite`, `droite`, `KgEtMetres`) | — |
| Tri valeur décroissante, non cliquable ; ni pagination ni pied | tri par défaut ; pied de totaux (kg, valeur, écart) ajouté | — |
| Vide « Aucune matière ne correspond à cette recherche. » / « Aucun stock à valoriser. » ; chargement « …la valorisation… » | `Vide`, `Chargement` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « La valorisation au {date ou « jour »}, matière par matière, dans un classeur ») | D, A | `GET export/valorisation?date_reference=` (+ filtres) | — | `valorisation-AAAA-MM-JJ.xlsx` |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |
| choisir « Au » / « autre date… » | D, A | `GET valorisation?date_reference=` | — | — |

Anomalies : P8-2, P8-4.

---

### Matrice — `/analyse?onglet=matrice`

Gestion MP : onglet Matrice (`AnalysePrix.tsx` vue matrice) → PRO : `Indicateurs` + légende +
`Filtres` liés + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Données `GET /prix/historique`, `/prix/matrice` (prix moyen pondéré par mois, devise de facture, 36 mois ; stable 0,005, forte = `seuil_hausse_forte`), `/opportunites?meme_couleur=true&autre_fournisseur=true` | `GET prix/historique`, `GET prix/matrice`, `GET opportunites` | — |
| Kpi « Achats enregistrés » (« {total} au total · {n} mois d'historique ») ; « Hausses de prix » (> 0,5 % ; « dont {n} forte(s), au-delà de {seuil} » ; critique / attention / ok) ; « Baisses obtenues » (« face au prix précédent du même fil ») ; « Opportunités d'économies » (« par an · {n} opportunité(s), onglet « Opportunités » » / « calcul en cours ») | `Indicateurs` (`Kpi({formule})`) — communs avec Prix payés | — |
| Légende « Premier prix » (accent), « Stable », « Baisse » (ok), « Légère hausse » (attention), « Forte hausse » (critique) ; note « prix moyen pondéré du mois · stable à ±0,5 % près · forte hausse au-delà de {5 %} » | `Badge` (table statut → ton) | — |
| Règle de teinte : variation face au dernier prix **antérieur** | inchangée (serveur) | — |
| Titre « Matrice des prix — {n} fil(s) » | « … — {n} matière(s) » | vocabulaire |
| Recherche « Référence, fournisseur, couleur… plusieurs mots » (8 champs) ; 5 listes liées « Toutes compositions », « Tous types de fil », « Tous titrages », « Toutes couleurs », « Tous fournisseurs » ; « Effacer les filtres » dès 1 | `Recherche` + `Filtres` liés ; effacer dès 2 | — |
| Col. « Référence » (case + réf. ; « composition · type · titrage · couleur » ; infobulle « Prix moyen du mois, pondéré par les quantités… le mois le plus récent à gauche ») · « Fournisseur » · « Prix en » (« {devise} / kg » ; infobulle « La monnaie de la facture… ») · bouton « Courbe » · un par mois, récent à gauche (étiquette ; « · » sans achat ; infobulle « {Mouvement} : {+x,x %} ({avant} → {prix} {devise} / kg) ») | `DataTable` (colonnes dynamiques, `Badge`) | case grisée au-delà de 8 avec raison (P8-6) |
| Tri référence ; pas de pied ni de ligne cliquable | — | — |
| Vide « Aucun fil ne correspond à ces filtres. » / « La matrice se remplira à la première réception validée : une colonne par mois, jusqu'à trente-six mois. » | `Vide` (« Aucune matière ne correspond… ») | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Comparer les {n} fils affichés » | D, A | — (fenêtre Évolution) | grisé si 0 ou > 8 ; « Filtrer jusqu'à 8 fils au plus pour les comparer tous » / « Tous les fils du tableau sur une même courbe » | « … matières … » |
| « Comparer les {n} fils cochés » / « Cocher des fils à comparer » | D, A | — | grisé sans case ; « Cocher des fils dans le tableau, puis voir leurs prix sur une même courbe » | — |
| « Tout décocher » | D, A | — | si ≥ 1 cochée | — |
| case à cocher de ligne | D, A | — | 8 au plus ; raison ajoutée « 8 matières au plus sur une même courbe » | P8-6 |
| « Courbe » (infobulle « La courbe des prix de {réf} ») | D, A | — | — | — |
| « Exporter en Excel » (infobulle « L'historique des achats et la matrice, dans un classeur ») | D, A | `GET export/prix` | — | `prix-AAAA-MM-JJ.xlsx` |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |

Anomalies : P8-6.

---

### Prix payés — `/analyse?onglet=historique`

Gestion MP : onglet Prix payés (`AnalysePrix.tsx` vue historique) → PRO : mêmes `Indicateurs` et
légende que Matrice + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /prix/historique` : précédent = dernier prix du même triplet (référence, fournisseur, devise) ; `montant_mad` au cours du jour ; récent d'abord | `GET prix/historique` | — |
| Titre « Historique des achats — {n} prix payé(s) » ; note « le plus récent d'abord · cliquer un achat montre la courbe de ce fil » | `Carte` + `Note` | « … de cette matière » |
| Recherche « Référence, fournisseur, n° de bon… plusieurs mots » ; case « seulement les hausses » ; « Effacer les filtres » | `Recherche`, `Interrupteur`, `Filtres` | — |
| Col. Date · Bon · Référence (« nature · désignation ») · Fournisseur · Quantité (kg) · Prix payé (« {prix} {devise} / kg ») · Prix précédent · Évolution (« 1er prix » / « +x,x % ») · Montant (MAD) | `DataTable` ; « Bon » → `LienDocument` vers `/commandes/:id` | lien ajouté |
| Ligne cliquable → courbe de ce fil | `lien` → fenêtre Évolution | — |
| Vide « Aucun achat ne correspond. » / « L'historique se remplira à la première réception validée. » | `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| clic ligne | D, A | — | — | fenêtre Évolution |
| « Exporter en Excel » | D, A | `GET export/prix` | — | — |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |

---

### Évolution des prix payés (fenêtre) — sur `/analyse?onglet=matrice|historique|opportunites`

Gestion MP : fenêtre « Évolution des prix payés, fil par fil » (`ComparaisonPrix.tsx`) → PRO :
`Fenetre({taille:'tresLarge'})` + `Courbes` + `Bascule` + `DataTable` ; D, A. Titre « Évolution des
prix payés, matière par matière ».

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| 8 fils au plus ; info « 8 fils au plus sur une même courbe : les {n} suivants sont laissés de côté. » ; « Jamais acheté, donc sans courbe : {réf}. Seul un prix de catalogue existe pour {ce fil|ces fils}, et il n'a pas de date. » | `Note` | « matière(s) » |
| Graphique 320 px, X = calendrier, une échelle Y par monnaie (2 au plus), bornes ×0,95/×1,05 ; infobulle « Achat du {date} » « {prix} {devise} / kg · {n° bon} » ; légende « {réf} — {fournisseur} » ; couleur = teinte du fil (palette de repli) ; traits distincts | `Courbes` (axe par devise, couleur du fil) | — |
| Bascule « Résumé par fil » / « Chaque achat ({n}) » ; note « Prix payés, au kilo, dans la monnaie de la facture. » + « Deux monnaies : l'échelle de gauche est en {D1}, celle de droite en {D2}… » | `Bascule` « Résumé par matière » | — |
| Résumé : Référence (pastille) · Fournisseur · Achats (« jamais acheté ») · Premier prix · Le · Dernier prix · Le · Évolution (critique > 5 % **en dur**, attention > 0,5 %, ok < −0,5 %) · Mini – maxi | `DataTable` ; seuil « forte » = réglage `seuil_hausse_forte` | P8-4 |
| Chaque achat : Date · Référence · Fournisseur · Bon · Quantité (kg) · Prix payé · Contre-valeur (MAD) ; vide « Aucun achat pour ces fils. » | `DataTable`, `Vide` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir une vue (Bascule) | D, A | — | — | — |
| fermer (× / Échap) | D, A | — | — | `Fenetre` |

Anomalies : P8-4.

---

### Opportunités d'économies — `/analyse?onglet=opportunites`

Gestion MP : onglet Opportunités (`AnalyseOpportunites.tsx`) → PRO : `Indicateurs` + `Filtres` +
`DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /opportunites?meme_couleur=&autre_fournisseur=&prix_catalogue=&fenetre_jours=` (fenêtre vide = réglage, 1-3650) ; règle serveur (matière consommée, dernier prix payé rendu usine sinon facture × cours, rivaux même composition/type/titrage [+couleur] [+autre fournisseur], prix le plus proche dans la fenêtre, écartées « hors_fenetre » / « sans_date », économie/an = (actuel − mini) × conso annuelle) | `GET opportunites` (mêmes paramètres) | — |
| Kpi « Économie possible » (« par an, au rythme de consommation actuel »), « Opportunités » (« dont {n} à plus de {forte} d'écart »), « La plus forte », « Écartées » (« {n} sans date · {n} à plus de {fenêtre} j d'écart » + infobulle) | `Kpi({formule})` | — |
| Titre « Opportunités d'économies — {n} affichée(s) » | `Carte` | — |
| Recherche « Fil, fournisseur, couleur… plusieurs mots » ; note « Comparé à : » ; cases « même couleur » (cochée), « autre fournisseur » (cochée), « prix de catalogue aussi » ; liste « à {N} j au plus (réglage) », 30/45/60/90/180 j (infobulles exactes) ; « mise à jour… » ; **pas de « Effacer les filtres »** | `Recherche` (« Matière, fournisseur, couleur… »), `Interrupteur` ×3, `Selecteur` ; « Effacer les filtres » ajouté (remet les défauts) | P8-5 |
| Avertissement une ligne (texte serveur complet en infobulle : « Comparaison entre fils de même composition… c'est une opportunité à négocier, pas une décision. ») | `Note` | — |
| Col. **« Fil · fournisseur actuel »** · « Prix actuel (MAD / kg) » (note base + date ; « catalogue, non daté » ; infobulle) · « Comparable le moins cher · chez » · « Son prix (MAD / kg) » · « Écart » (« −x,x % », critique > forte ; « à {n} j d'écart ») · « Conso / an (kg) » · « Économie / an » · bouton « Courbes » | `DataTable` ; 1re colonne « Référence · fournisseur actuel » | vocabulaire § 5 |
| Vide « Aucune opportunité ne correspond à cette recherche. » / « Aucun fil comparable ne s'achète moins cher avec ces critères. » | `Vide` (« Aucune matière comparable… ») | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Les opportunités affichées, avec ces critères, dans un classeur ») | D, A | `GET export/opportunites?…` | — | `opportunites-AAAA-MM-JJ.xlsx` + avertissement |
| « Courbes » (infobulle « Les prix des deux fils dans le temps, sur une même courbe ») | D, A | — | — | fenêtre Évolution [réf., réf. alternative] |
| « Effacer les filtres » (nouveau) | D, A | — | dès 2 filtres | P8-5 |

Anomalies : P8-5.

---

### Fournisseurs (classement) — `/analyse?onglet=fournisseurs`

Gestion MP : onglet Fournisseurs (`AnalyseFournisseurs.tsx`) → PRO : `Indicateurs` + `Note` +
`DataTable` + fenêtre ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /fournisseurs/performance` (cible, seuils, lignes, réceptions notées) ; OTIF = à l'heure × complète × conforme ; score = OTIF × 60 + retours (20 → 0 dès 5 %) + délai (20 jusqu'à 15 j, −1 par 5 j) ; classements « 🟢 Stratégique » (Fidéliser + négocier volume), « 🟡 Standard » (Maintenir relation), « 🟠 À surveiller » (Audit qualité + relance), « 🔴 À challenger » (Chercher alternative) ; sous-performant = OTIF < cible | `GET fournisseurs/performance` (clé = id) ; classements **sans émoji** ; « À surveiller » affiché tel quel (nom de classement, distinct du statut ATTENTION) | vocabulaire § 5, P8-23 |
| Kpi « Livraisons parfaites (OTIF) » (« … · cible {95 %} »), « Sous la cible » (3 premiers noms / « aucun fournisseur »), « Réceptions notées » (« sur {n} réception(s) validée(s) »), « Fournisseurs notés » (« stratégique dès {85}/100 ») | `Kpi({formule})` | — |
| Titre « Le classement des fournisseurs — {n} affiché(s) » | `Carte` | — |
| Recherche (initialisée par `?fournisseur=`) « Fournisseur, pays, classement… plusieurs mots » ; case « montrer aussi ceux sans commande » ; « Effacer les filtres » | `Recherche`, `Interrupteur`, `Filtres` | `?fournisseur=ID` ouvre la fenêtre (P8-1) |
| Note « Score sur 100 : … Cliquer sur un fournisseur montre ses réceptions une à une. » | `Note` + `Formule` | — |
| Col. Fournisseur (« pays · devise ») · Délai · Commandes · Acheté (MAD) · Réceptions · À l'heure (« Livrées à la date promise ») · Complètes (« Chaque ligne livrée en entier ») · Conformes (« … ni réserve ni refus ») · OTIF (badge) · Retours · Écart de pesée · Score · Classement (badge + action ; « pas encore noté ») ; tri score décroissant | `DataTable` ; Fournisseur → `LienDocument` `/fournisseurs/:id` | lien ajouté |
| Vide « Aucun fournisseur ne correspond. » | `Vide` | — |
| Fenêtre « {fournisseur} — ses réceptions » : Kpi Score (« {n} / 100 »), OTIF, Acheté (« {n} commande(s) »), Action conseillée ; tableau Réception · Date · À l'heure · Complète · Conforme (Oui/Non/—) · Parfaite (badge) · Lignes hors tolérance · Écart de pesée ; vide « Aucune réception validée pour ce fournisseur. » ; note « « — » dans « À l'heure » … elle n'entre pas dans l'OTIF. » | `Fenetre({taille:'large'})` sur `?onglet=fournisseurs&fournisseur=ID` ; Réception → `LienDocument` `/receptions/:id` | adresse stable, lien ajouté |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Le classement et les réceptions notées, dans un classeur ») | D, A | `GET export/fournisseurs` | — | 2 feuilles ; classement « À surveiller » sans émoji (P8-23) |
| clic ligne | D, A | — | — | fenêtre « ses réceptions » (`&fournisseur=ID`) |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |

Anomalies : P8-1, P8-23.

---

### Coût de revient — `/analyse?onglet=revient`

Gestion MP : onglet Coût de revient (`AnalyseRevient.tsx`, aussi Partie 5) → PRO : `Bascule` 3 vues
+ `Filtres` liés + `Puces` + `Indicateurs` + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /importations/analyse/revient?axe=&q=&debut=&fin=&statut=&qualite=&references=&selection=|composition=…&detail=` ; vue qualité `GET /importations/analyse/qualite/{code}` ; refus 400 « axe inconnu… », « sélection illisible… », « la sélection doit être une liste de combinaisons », « critère inconnu dans la sélection… », 404 « qualité inconnue ou sans recette… » | `GET analyse/revient` ; `GET analyse/revient/qualites/{id}` (id au lieu du code) | routes renommées (contrat) |
| Carte « Ce que la matière importée a coûté, rendue usine » ; Bascule « Regroupé » / « Lot par lot » / « Recette d'une qualité » | `Carte` + `Bascule` | — |
| Filtres : texte (300 ms, sans accents) « Dossier, référence, lot, fournisseur, couleur… » ; « + Ajouter une matière… » ; « Par {axe} » (Référence, Titrage — défaut —, Composition, Type de fil, Couleur, Fournisseur, Dossier, Lot, Rôle) ; statut « Ouverts et clos » / « Dossiers clos » / « Dossiers ouverts » ; période « Du … au … » ; « Toutes qualités » + 5 listes liées ; « + Combinaison » (grisé sans critère) ; « Effacer les filtres » dès 2 ; puces « Matières : », « Réunion de : » (×), « + en cours : … » | `Recherche`, `SelecteurMatiere`, `Selecteur`, `DateChamp`, `Filtres` liés, `Puces` ; selects alignés (`Champ`) | P8-27 |
| Kpi Poids, Coût hors TVA (« {coût/kg} MAD / kg · achat + charges »), Achat, Charges hors TVA (« {%} de l'achat » + lien « + {montant} non répartis »), Coût TTC (« dont TVA … ») | `Kpi({formule, lien})` | — |
| Tableau Regroupé : {axe} · Lots · Poids · Achat MAD · Charges hors TVA (infobulle) · Coût hors TVA · Coût hors TVA / kg (« achat {prix/kg} ») · TVA · Coût TTC · Dossiers (4 liens + « +n ») ; ligne cliquable si l'axe est un critère (« Voir ses références une à une ») ; pied « Total » ; vide « Aucune marchandise importée ne répond à ces critères. » | `DataTable` + pied de totaux ; dossiers → `LienDocument` `/dossiers/:id` | — |
| Tableau Lot par lot : Dossier (lien + « ouvert ») · Arrivée · Référence · Lot · Fournisseur · Titrage · Poids · Achat MAD · Charges hors TVA · Coût hors TVA · Coût hors TVA / kg · TVA · Coût TTC + Total | `DataTable` ; Lot → `/lots/:id` | lien ajouté |
| Vue Recette d'une qualité : « Choisir une qualité… » + période ; texte vide ; Kpi « Coût matière / m² », « Coût / kg de tapis », « Recette couverte » (attention < 99,9 %), « Poids importé » ; colonnes Rôle, Part du rôle, kg / m², Coût / m² ; pied par rôle (« aucun fil importé : rôle hors du coût calculé » / « coût connu sur {x %} du rôle, étendu au reste » / « coût connu pour tout le rôle » / « · rôle au mètre… ») ; ligne « Coût matière de la qualité » | `Selecteur`, `Kpi`, `DataTable` ; « aucune matière importée… » | vocabulaire |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir une vue (Bascule) | D, A | — | — | — |
| « Exporter en Excel » (infobulle « Le regroupement et le détail lot par lot dans un classeur ») | D, A | `GET export/revient?…` | hors vue qualité | — |
| « + Ajouter une matière… » | D, A | `GET analyse/revient?references=` | — | — |
| « + Combinaison » (infobulle « + Ajouter cette combinaison : la retenir, puis en composer une autre ; le résultat les réunit ») | D, A | `GET analyse/revient?selection=` | grisé sans critère, raison en infobulle | — |
| × sur une puce | D, A | — | — | — |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |
| clic ligne regroupée (« Voir ses références une à une ») | D, A | `GET analyse/revient?axe=reference` | — | — |
| lien n° de dossier | D, A | — | — | → `/dossiers/:id` (fenêtre sur `/importations`) |
| lien « + {montant} non répartis » | D, A | — | — | → `/dossiers/:id` (1er dossier) |
| « Choisir une qualité… » | D, A | `GET analyse/revient/qualites/{id}` | — | — |

Anomalies : P8-27.

---

### Échéancier — `/analyse?onglet=echeancier`

Gestion MP : onglet Échéancier (`AnalyseEcheancier.tsx`) → PRO : `Indicateurs` + `Bascule` 4 vues +
`Filtres` + `DataTable` ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /echeancier?du=&au=` ; règles (facture = montant saisi sinon Σ pesée × prix « estimé » ; réceptions annulées → écartée « réception annulée : plus due » / « réglée, réception annulée : avoir à demander » ; brouillons → absente ; réglée / échéance / à dater ; frais d'importation « Frais d'importation ({poste}) », « {n° dossier} · {pièce} » ; cours du jour ; réglées ≤ 300) | `GET echeancier?q=&nature=&du=&au=` : **tous** les filtres au serveur | P8-21 |
| Kpi « À payer » (« {n} échéance(s) connue(s) »), « Échu, non réglé » (critique / ok), « Dans les 30 jours » (attention), « À dater » (attention) | `Kpi({formule})` — suivent les filtres | P8-21 |
| Info « {n} facture(s) de réceptions annulées ne sont plus dues… Les détacher de la réception, ou faire établir un avoir. » (6 au plus) | `Note` (ton info) | — |
| Bascule « Échéances ({n} · {total}) » / « Par mois » / « À dater ({n}) » / « Réglées ({n}) » | `Bascule` | — |
| Recherche « Fournisseur, prestataire, n° de pièce… » ; « Toutes les échéances » + natures ; « Du » (« Échéances à partir de ce jour », max = Au) ; « Au » (« … inclus », min = Du) ; « Effacer les filtres » dès 1 | `Recherche`, `Selecteur`, `DateChamp` ; effacer dès 2 | — |
| Échéances : Échéance (rouge gras si en retard) · Nature · Fournisseur ou prestataire · Pièce · Montant (« estimé », infobulle « Montant non saisi sur la facture : la pesée × le prix de ses réceptions ») · Montant MAD · « en retard » · « Réglée… » ; tri échéance ; vides « Aucune échéance ne correspond. » / « Aucune échéance connue : elles viennent de l'échéance des factures (réceptions) et des frais d'importation. » | `DataTable` ; Pièce → `LienDocument` (`/receptions/:id` ou `/dossiers/:id`) | lien ajouté |
| Par mois : Mois · À payer (MAD) ; mois passés en rouge ; vide « Rien à payer. » ; ignore nature et recherche ; pas de total | `DataTable` + pied de totaux ; suit tous les filtres | P8-21 |
| À dater : Nature · Fournisseur ou prestataire · Pièce · Montant · Montant MAD · « Réglée… » ; vide « Toutes les factures et tous les frais connus ont leur échéance. » | `DataTable` | — |
| Réglées : Réglée le · Échéance · Nature · Fournisseur ou prestataire · Pièce · Montant · Montant MAD · « Annuler le règlement » ; vide « Aucun règlement noté : « Réglée… » sur une échéance le note. » | `DataTable` | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Réglée… » (infobulle « Payée : elle sort de l'échéancier et de l'« échu, non réglé » ») | D, A | `PUT echeancier/paiement` `{objet, id, payee_le}` | `Confirmer` « Réglée le [date, défaut et max aujourd'hui serveur] · Non · Oui, réglée » ; refus 404 « Pièce introuvable. », « Un règlement ne se date pas dans le futur : c'est un fait constaté. », « Le règlement ({date}) précède la pièce qu'il règle ({date}). » (borne min de `DateChamp`) | « {pièce} réglée le {date}. » ; journal « règlement » |
| « Annuler le règlement » (infobulle « La pièce redevient due : elle revient dans l'échéancier ») | D, A | `PUT echeancier/paiement` `{…, payee_le:null}` | `Confirmer` « Annuler le règlement ? · Non · Oui, annuler » | « Règlement de {pièce} annulé : elle redevient due. » ; journal « règlement annulé » |
| « Exporter en Excel » (infobulle « L'échéancier ligne par ligne, par mois, et ce qui est à dater, dans un classeur ») | D, A | `GET export/echeancier?…` (filtres) | — | feuilles Échéances, À dater, Par mois **+ Réglées** (P8-21) |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |
| choisir une vue (Bascule) | D, A | — | — | — |

Anomalies : P8-21.

---

### Contrôles — `/analyse?onglet=controles` (fenêtre `&controle=Cxx`)

Gestion MP : onglet Contrôles (`AnalyseControles.tsx`, règles `calcul/controles.py`) → PRO :
`Indicateurs` + `Filtres` + `DataTable` + `Fenetre({taille:'tresLarge'})` du détail ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /controles` → date, synthèse {total, conformes, garantis, anomalies, bloquants, score}, contrôles {code, libelle, anomalies, conforme, garanti, gravite, quoi_faire, vers, detail[]}, colonnes ; intégrité (C12, C14, C27, C37) sur toutes les données ; `GET /controles/soldes` | `GET controles`, `GET controles/soldes` ; détail complet d'un contrôle (route ajoutée, API-PRO § 1.24 : `GET controles/{code}`, pages, recherche serveur) | détail plus coupé à 200 lignes (A2) |
| Synthèse : anomalies = contrôles non conformes ; garantis exclus du total ; score = conformes / total | inchangée (formule dans `aide.json`) | — |
| Kpi « Score » (« {c} conformes sur {t} vérifiés[ · {g} garantis par la base] » ; « Au {date} » ; critique / attention / ok) ; « Anomalies » (« contrôles à revoir ») ; « Bloquants » (« le pilotage en est faussé » / « aucun ») ; « Soldes et journal » (« Concordants » / « Écart ! » / « … » / « — » ; « {n} soldes = journal » / « {n} écart(s), {n} solde(s) négatif(s) ») | `Kpi({formule})` | — |
| Erreur si soldes non conformes « Le stock tenu ne retombe pas sur le journal des mouvements (…). Une écriture a contourné le chemin normal : prévenir la personne qui entretient le serveur avant toute nouvelle saisie. » + 8 lignes « lot n° {id}, magasin n° {id} : journal {x} kg, solde {y} kg » | `Erreur` ; « … prévenir l'administrateur technique … » ; lignes avec `LienDocument` `/lots/:id` | — |
| Titre « Les contrôles — {n} affiché(s) » | `Carte` | — |
| Recherche « Code, libellé, gravité… plusieurs mots » ; case « seulement les anomalies » (cochée) ; bandeau « {n} bloquant(s) : le pilotage est faussé tant que {C01, C05…} n'{a|ont} pas été corrigé(s). » ; « Effacer les filtres » → remet la case cochée | `Recherche`, `Interrupteur`, `Erreur` en rangée, `Filtres` | — |
| Col. Code · Ce qui est vérifié · Gravité (« Bloquant » / « À corriger » / « Pour information ») · Anomalies (« garanti par la base » neutre / « OK » ok / nombre : critique si bloquant, neutre si information, attention sinon) · Quoi faire (« Ne peut pas sonner : {raison} » / « — » / texte) ; tri non conformes, puis gravité ; ligne cliquable si non conforme | `DataTable` + `Badge` | — |
| Vide « Aucune anomalie : tous les contrôles sont conformes. » / « Aucun contrôle ne correspond. » | `Vide` | — |
| Fenêtre « {code} — {libellé} » : « **Quoi faire :** {texte} » (erreur si bloquant, info sinon) + « Ouvrir l'écran → » ; badge gravité ; « {n} ligne(s) à examiner[ (les {k} premières affichées)]. » ; recherche « Chercher dans les lignes… » ; colonnes dynamiques libellées par `COLONNES` (clé jamais affichée) ; entiers « 1 234 », décimaux 2 déc., dates jj/mm/aaaa, Oui/Non ; vide « Rien ne correspond. » / « Ce contrôle ne détaille pas ses lignes. » | `Fenetre` à adresse `&controle=Cxx` ; `DataTable` (`ChargerPlus`) ; colonnes typées par le serveur (`unite`) | adresse stable |
| Colonne `ecart` affichée par `part()` (×100) : C36 déjà en % → « 350,0 % » | **une seule échelle** : le serveur envoie tout écart relatif en fraction (C08, C30, C36, C35 « Frais / marchandise ») avec `unite:'%'` ; l'écran et l'export le formatent une seule fois | P8-3 |
| Liens de cellules : reference → `/stock?onglet=matieres&q=` ; numero_of → `/sorties?ordre=` ; lot → `/stock?onglet=lots&q=` ; metier → `/metiers` ; numero → `/commandes?commande=` ; dossier → `/importations?dossier=` ; reception → `/receptions?reception=` ; qualite → `/qualites?qualite=` ; fournisseur → `/catalogue?onglet=fournisseurs&fournisseur=` | par **id** (le détail porte `matiere_id`, `lot_id`, …) : `/stock/matieres/:id`, `/ordres/:id`, `/lots/:id`, `/metiers/:id`, `/commandes/:id`, `/dossiers/:id`, `/receptions/:id`, `/qualites/:id`, `/fournisseurs/:id` (`LienDocument`) | plus de recherche par texte |

**Les 38 contrôles en PRO** — code, libellé, gravité, garanti et colonnes gardés ; « quoi faire » =
texte exact de `CONTROLES.md` / ECRANS.md P8 § 1.9, servi par `GET controles` (`quoi_faire`), où
seuls les noms d'écran suivent les titres PRO et « la personne qui entretient le serveur » devient
« l'administrateur technique » ; `_HORS_SAISIE` (C02, C04, C14, C16, C26, C31, C32) gardé ainsi.

| Code | Libellé (gardé sauf mention) | Gravité | Garanti | Colonnes du détail | « Ouvrir l'écran » PRO | Changement |
|---|---|---|---|---|---|---|
| C01 | Recette dont un rôle ne fait pas 100 % | bloquant | — | Qualité, Rôles | `/qualites` | « Qualités et recettes › Recette » |
| C02 | Sortie vers les machines sans ordre (n° OF) | avertissement | — | Date, Référence | `/sorties` | — |
| C03 | Retour sans motif, ou avec le motif d'une autre famille | avertissement | — | Date, Référence, Type, Motif | `/operations?onglet=retour_machine` | — |
| C04 | Mouvement de stock sans auteur | avertissement | — | Date, Référence | `/stock?onglet=mouvements` | — |
| C05 | Matière sans fournisseur | bloquant | — | Référence | `/catalogue?onglet=matieres` | — |
| C06 | Commande non livrée à sa date prévue (ou 60 jours après la commande) | avertissement | — | N°, Fournisseur, Date de la commande, Jours, Retard (j) | `/commandes?filtre=retard` | — |
| C07 | Matière jamais utilisée (ni recette, ni mouvement) | information | — | Référence | `/catalogue?onglet=matieres` | — |
| C08 | Écart de pesée supérieur à 2 % | avertissement | — | Réception, Référence, Attendu, Pesé, Écart (%) | `/receptions?onglet=pesees` | « 2 % » avec espace (P8-14) |
| C09 | Prix négatif au catalogue | bloquant | oui | Référence, Prix | `/catalogue?onglet=matieres` | — |
| C10 | Délai fournisseur nul ou négatif | avertissement | oui | Fournisseur, Délai (j) | `/catalogue?onglet=fournisseurs` | — |
| C11 | Cours de change à zéro | bloquant | oui | Cours, Valeur (MAD) | `/reglages?onglet=devises` | — |
| C12 | Stock tenu (soldes des lots) différent du journal des mouvements | bloquant | — | Référence, Lot, Magasin, Stock, Attendu | `/stock?onglet=mouvements` | « administrateur technique » |
| C13 | Stock projeté négatif pendant le délai d'approvisionnement | avertissement | — | Référence, Stock net, Stock projeté, Manque | `/plan-achat` | — |
| C14 | Mouvement de stock à une date future | avertissement | — | Date, Référence | `/stock?onglet=mouvements` | — |
| C15 | Matière d'une recette sans prix d'achat | avertissement | — | Qualité, Référence | `/catalogue?onglet=matieres` | — |
| C16 | Intégrité référentielle des mouvements | bloquant | oui | Référence/Fournisseur, Date | `/stock?onglet=mouvements` | — |
| C17 | Matière en alerte sans second fournisseur | information | — | Référence, Fournisseur, À commander (MAD) | `/catalogue?onglet=matieres` | — |
| C18 | Stock dormant depuis plus de 180 jours | information | — | Référence, Stock, Jours sans mouvement | `/stock` | — |
| C19 | Fournisseur qui facture en plusieurs devises | information | — | Fournisseur, Devises, Devise par défaut | `/catalogue?onglet=fournisseurs` | lien vers les fournisseurs (GMP : `/catalogue`) |
| C20 | Stock négatif sur une matière sans consommation | bloquant | — | Référence, Stock net | `/inventaire` | — |
| C21 | Prix au catalogue sans devise | bloquant | oui | Référence, Prix, Fournisseur | `/catalogue?onglet=matieres` | — |
| C22 | Étage monté plus large que la laize du métier | avertissement | — | Métier, Étage, Laize (m), Mètres montés, Fils | `/metiers` | colonne « Fils » → « Matières » |
| C23 | Fil monté sans poids de bobine au catalogue | bloquant | — | Métier, Étage, Référence, Mètres | `/catalogue?onglet=matieres` | — |
| C24 | Fil monté à un étage que le métier n'a pas | avertissement | — | Métier, Étage, Étages du métier, Référence | `/metiers` | — |
| C25 | Fil monté sans sortie de magasin enregistrée (le magasin le compte encore) | avertissement | — | Métier, Étage, Référence, Poids (kg) | `/sorties` | texte à aligner sur le modèle « sur les métiers » tranché (synthèse 1) |
| C26 | Sortie de stock sans numéro de lot | avertissement | — | Date, Référence, Quantité, Ordre (n° OF), Par | `/stock?onglet=mouvements` | — |
| C27 | Lot dont il est sorti plus qu'il n'est entré | bloquant | — | Référence, Lot, Stock, Entré, Sorti | `/stock?onglet=lots` | « Suivre » → `/tracabilite?lot=` |
| C28 | Dossier d'importation arrivé depuis plus de {delai_frais_import_jours} jours et sans frais hors TVA | avertissement | — | Dossier, Arrivée, Marchandises, Jours | `/importations` | délai lu dans le réglage `delai_frais_import_jours` (30 j, 1–365) ; « sans frais hors TVA » (Gestion MP corrigé, E-10) |
| C29 | TVA d'importation éloignée de 20 % de la valeur en douane | avertissement | — | Dossier, TVA saisie (MAD), TVA attendue (MAD), Écart (MAD) | `/importations` | libellé corrigé « TVA d'importation à plus de {toler_tva_import} de la TVA attendue (20 % de la valeur en douane, droits et TPI compris) » (P8-15, Gestion MP corrigé E-10) ; tolérance lue dans le réglage `toler_tva_import` (5 %), la même que la fiche du dossier |
| C30 | Poids de bobine reçu éloigné du catalogue de plus de 5 % | information | — | Référence, Fournisseur, Catalogue (kg / bobine), Constaté (kg / bobine), Écart (%), Réception | `/receptions?onglet=bobines` | « 5 % » (P8-14) |
| C31 | Ordre de fabrication servi à plusieurs dates | avertissement | — | Ordre (n° OF), Dates, Jours | `/sorties` | — |
| C32 | Ordre de fabrication daté avant un ordre de numéro inférieur | information | — | Ordre (n° OF), Date, Après, Date de l'ordre suivant | `/sorties` | — |
| C33 | Stock minimum du catalogue supérieur à 3 mois de consommation | information | — | Référence, Stock minimum, Conso / mois, Mois, Retenu | `/catalogue?onglet=matieres` | — |
| C34 | Dossier d'importation avec des frais mais sans marchandise | avertissement | — | Dossier, Frais (MAD) | `/importations?onglet=rattacher` | — |
| C35 | Dossier d'importation (ou une de ses marchandises) dont les frais dépassent 100 % de la marchandise | avertissement | — | Dossier, Référence, Marchandise (MAD), Frais hors TVA (MAD), Frais / marchandise (%) | `/importations` | échelle unique (P8-3) |
| C36 | Facture d'un dossier d'importation éloignée de plus de 2 % de la marchandise reçue | avertissement | — | Dossier, Facture, Facture (devise), Reçu, pesée × prix (devise), Devise, Écart (%) | `/importations` | **écart envoyé en fraction** : fin du « 350,0 % » (P8-3) |
| C37 | Lot sous zéro à une date passée (écriture datée avant l'entrée de la matière) | bloquant | — | Référence, Lot, Magasin, Date (1er jour), Manque (creux) | `/stock?onglet=mouvements` | — |
| C38 | Prix du catalogue à plus de 3 fois (ou moins d'un 3e) du dernier prix payé | avertissement | — | Référence, Fournisseur, Prix du catalogue, Dernier prix payé, Date, Catalogue / payé | `/catalogue?onglet=matieres` | — |

Totaux gardés : 38 contrôles ; 5 garantis (C09, C10, C11, C16, C21) ; 11 bloquants ; 7 information ;
20 « à corriger ». Les seuils entre parenthèses (2 %, 3 mois, 5 %, 100 %, 180 jours, 20 %) suivent les
réglages et s'écrivent au format français.

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Les contrôles, quoi faire, et les lignes fautives de chacun ») | D, A | `GET export/controles` | — | `controles-AAAA-MM-JJ.xlsx` : feuille « Contrôles » (Code, Ce qui est vérifié, Gravité, Anomalies, État, Quoi faire + ligne de synthèse) + une feuille par contrôle en anomalie (≤ 31 car.) ; même échelle des écarts que l'écran |
| clic ligne (non conforme) | D, A | `GET controles/{code}` (route ajoutée, API-PRO § 1.24) | — | `&controle=Cxx` |
| « Ouvrir l'écran → » | D, A | — | — | route PRO du tableau ci-dessus ; ferme la fenêtre |
| lien de cellule (« Ouvrir pour corriger ») | D, A | — | — | fiche par id (`LienDocument`) |
| « Effacer les filtres » | D, A | — | si recherche ou case décochée | remet la case cochée |
| « Chercher dans les lignes… » | D, A | `GET controles/{code}?q=` | — | recherche sur tout le détail |

Anomalies : P8-3, P8-14, P8-15.

---

### Production (rendement par ordre) — `/analyse?onglet=production`

Gestion MP : onglet Production (`AnalyseProduction.tsx`) → PRO : `Indicateurs` + `Filtres` +
`DataTable` + fenêtre d'ordre ; D, A.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /ordres-fabrication` (session seule) : sorti, retours, sorti net, prévu par la recette perte comprise, écart, écart relatif ; totaux sur les ordres qui disent leur qualité | `GET ordres/consommation` (C) | route renommée |
| Kpi « Sorti net par les ordres » (« {kg} kg », « {n} ordre(s) de fabrication, retours déduits ») ; « Sorti face à la recette » (ok ≤ 5 %, attention au-delà ; « {kg} kg sortis pour {kg} kg prévus par la recette ») ; « Ordres au-delà de 5 % d'écart » (« {n} sur {n} », « parmi les ordres qui disent leur qualité ») ; seuil 5 % en dur | `Kpi({formule})` ; seuil fixe 5 % écrit dans la formule | P8-4 |
| Carte « Rendement par ordre — {n} ordre(s) » ; lien « Plan et réalisé par qualité → » | `Carte` + `LienDocument` → `/production?onglet=realise` | — |
| Recherche « Ordre, qualité, lot, référence… plusieurs mots » ; case « seulement les écarts de plus de 5 % » ; « Effacer les filtres » | `Recherche`, `Interrupteur`, `Filtres` | — |
| Col. Ordre (n° + commentaire) · Période · Qualité (« hors recette ») · Surface (m²) · Sorti net (kg) · Prévu par la recette (kg) · Écart (badge, attention > 5 %) · Lots ; note « Cliquer un ordre montre, fil par fil, le sorti net face au prévu par la recette. » | `DataTable` ; note « … matière par matière … » | vocabulaire |
| Vide « Aucun ordre ne correspond. » / « Aucune sortie n'a encore été rattachée à un ordre de fabrication. » | `Vide` | — |
| Fenêtre « Ordre de fabrication {n°} » : Kpi Sorti (« {kg} kg rendus » / « aucun retour »), Sorti net (« sorti moins les retours »), Prévu par la recette (« {qualité} : {m²} m² · … » / « qualité non précisée »), Écart ; tableau Référence · Sorti net (kg) · Prévu par la recette (kg) · Écart (kg) · « hors recette » / « pas sorti » ; « Lots utilisés : {…} » / « aucun lot nommé » ; « Traçabilité de l'ordre → » | `Fenetre({taille:'large'})` sur `&ordre=ID` (même contenu que l'onglet « Prévu par la recette et sorti net, par matière » de la fiche d'ordre) ; `GET ordres/{id}` ; lots → `/lots/:id` ; « Ouvrir l'ordre » → `/ordres/:id` | adresse stable |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Plan et réalisé par qualité → » | D, A | — | — | → `/production?onglet=realise` |
| clic ligne | D, A | `GET ordres/{id}` | — | fenêtre `&ordre=ID` |
| « Traçabilité de l'ordre → » | D, A | — | — | → `/tracabilite?ordre=ID` (GMP : `/stock?onglet=tracabilite&ordre=`) |
| « Effacer les filtres » | D, A | — | dès 2 filtres | — |

Anomalies : P8-4.

---

### Réglages (page) — `/reglages?onglet=parametres|devises|magasins|postes|codes|periode`

Gestion MP : page « Réglages » `/reglages` (11 onglets ; menu direction seule ; route ouverte aux
achats, onglet Devises seul) → PRO : `/reglages` (`Page`, `EnTete`, `Onglets`) — partie métier ;
D écrit tout ; A : devises en écriture, autres onglets en lecture ; L : `EcranReserve` (aucun réglage
chiffré ni cours) ; T : `EcranReserve` (sa partie est `/administration`).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Menu « Pilotage › Réglages », infobulle « Réglages, comptes, sauvegardes » (D seule) ; achats : route ouverte mais absente du menu | menu « Réglages » pour D et A ; infobulle « Seuils, devises, magasins, frais, douane, période close » | A voit l'entrée |
| Message « Les réglages sont réservés à la direction. » (inatteignable) | `EcranReserve` | P8-17 |
| Bouton d'en-tête « Métiers à tisser → » (D ; infobulle « Les métiers à tisser, leurs réglages et les fils montés : une page à part ») | action d'`EnTete` → `/metiers` (D) | — |
| Onglets (libellé court + infobulle, sans compteur) : « Paramètres », « Devises », « Magasins », « Frais » (« Postes de frais »), « Douane » (« Codes douaniers ») ; sous-titres exacts | `Onglets` + entrée `aide.json` par onglet ; + onglet **« Période close »** | 6 onglets métier |
| `?onglet=` inconnu ou non permis → 1er permis ; « parametres » = adresse nue | `useOngletAdresse` | — |
| Brouillon de Paramètres / Devises perdu au changement d'onglet | garde `sale` au changement d'onglet (« Des modifications ne sont pas enregistrées. Les abandonner ? ») | P8-8 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir un onglet | D, A | — | garde `sale` | P8-8 |
| « Métiers à tisser → » | D | — | — | → `/metiers` |

---

### Paramètres — `/reglages?onglet=parametres`

Gestion MP : onglet Paramètres (`ReglagesParametres.tsx`, `parametres.py`) → PRO : `Carte` titrée
par la famille + liste verticale des familles (compteur de modifications) + `Form` en `Grille` ;
D écrit, A lit ; L refusé (`GET parametres` 403) ; T ne voit que la famille technique (dans
`/administration`).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /parametres` (toute session, alimentation comprise) → `reglages[] {cle, libelle, famille, unite, echelle, aide, bas, haut, texte, defaut, valeur}` ; taux rangé en fraction, saisi en % | `GET parametres` (D, A ; famille technique : T) ; même forme | L refusé (REGLAGES 9.7) |
| Familles à gauche (200 px ; compteur « {n} modification(s) pas encore enregistrée(s) ») ; titre de carte = famille active ; phrase d'aide de famille ; champs en grille ≥ 300 px ; familles en ligne sous 900 px | `Bascule` verticale + `Carte` + `Note` + `Grille` | — |
| 10 familles : Couverture et statuts · Approvisionnement · Classification ABC / XYZ · Politique d'achat · Réceptions et fournisseurs · Stock et inventaire (**sans phrase**) · Prix · Trésorerie · Société · Méthode de calcul (texte seul) | 9 familles (phrases exactes gardées) ; « Stock et inventaire » reçoit une phrase : « La tolérance proposée à l'ouverture d'un inventaire : au-delà, un écart de comptage se justifie avant la validation. » ; « Méthode de calcul » → aide (`aide.json`, texte et 7 corrections inchangés) | P8-18 ; décision « Méthode de calcul » |
| Société : 15 champs dont « Période close jusqu'au », « Courriel du lundi : à qui », « Adresse du serveur pour les téléphones » | Société : 12 champs ; les 3 autres déplacés (Période close, Administration › Courriel, Administration › Technique) | partage tranché |
| Un champ : libellé (infobulle « {libellé} ({unité})[ — modifié, pas encore enregistré] ») ; aide = « {aide serveur **ou** aide d'écran} · entre {bas} et {haut} {unité} · par défaut : {défaut}[ · avant : {valeur}] » ; nombre fr (molette neutralisée, % en pourcent) + unité ; modifié : bordure accent ; hors bornes : rouge | `Champ` + `Nombre` (fr) ; **aide d'une seule source** : la déclaration serveur, enrichie des textes d'écran (les 11 textes d'écran et les 6 textes masqués par l'aide serveur fusionnés ; aides écrites pour `score_*`, `seuil_hausse_forte`, `dso`) | REGLAGES 9.8 |
| Contrôles d'ordre à l'écran (5 phrases) et au serveur (phrases différentes, la 1re plus longue) | **7 contrôles d'ordre** (et non 5 : `services/registre_reglages.py`, `ORDRES_STRICTS` et `ORDRES_LARGES`), **même phrase** à la frappe et au serveur ; les 5 de Gestion MP plus Tier 3 < Tier 2 (« Le montant du Tier 3 doit rester sous celui du Tier 2 : sinon plus aucune ligne ne serait en Tier 3. ») et Tier 1 ≥ Tier 2, égalité permise (« Le montant du Tier 1 (classe A) ne peut pas être inférieur à celui du Tier 2. ») ; pour les 5 (la plus complète : « La couverture critique doit rester inférieure à la couverture d'ATTENTION : sinon plus aucune matière ne serait en ATTENTION. » ; « La part cumulée de la classe A doit rester sous celle de la classe B. » ; « Le CV maximum de la classe X doit rester sous celui de la classe Y. » ; « Le score « ATTENTION » doit rester sous le score « standard ». » ; « Le score « standard » doit rester sous le score « stratégique ». ») ; l'égalité est refusée sauf pour Tier 1 / Tier 2 (K65) | REGLAGES 9.3 ; construit (lot F8) |
| Refus serveur « Paramètres inconnus : {clés}. », « « {libellé} » attend un nombre. », « … doit rester entre {bas} et {haut} {unité} — reçu {x}. », « « {libellé} » : texte trop long. » | inchangés | — |
| Historique (`ParametreHistorique`) + journal « paramètre » « {libellé} : {avant} → {après} » | inchangé ; valeurs localisées (P8-13) | — |
| Fenêtre « Historique des paramètres et des cours de change » : note « Les 500 derniers changements, le plus récent d'abord. » ; recherche « Paramètre, personne… » ; Quand · Paramètre (« Cours {XXX} → MAD ») · Avant · Nouvelle valeur · Par ; vide « Aucun changement. » ; cours brut « 10.85 » | `Fenetre({taille:'large'})` + `DataTable` + `ChargerPlus` ; nombres fr « 10,85 » | P8-13 ; D seule (route D, T) |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir une famille | D, A | — | — | brouillon des autres familles gardé |
| « Historique des changements » | D | `GET parametres/historique` | — | fenêtre |
| « Annuler » (≥ 1 modification) | D | — | `Confirmer` « Abandonner {n} modification(s) ? · Non · Oui, abandonner » | P8-8 |
| « Enregistrer {n} modification(s) » / « Aucune modification » / « Enregistrement… » | D | `PUT parametres` (clé → valeur) | `Bouton({manque, blocages})` : raisons en infobulle (bornes, ordres, « Aucune modification ») | « {n} paramètre(s) enregistré(s) : tout le pilotage est recalculé. » ; invalidation globale ; la clôture n'y passe plus (P8-9) |

**Les 57 réglages** — les 56 clés semées par la révision 0002 (`modeles.CLES_REGLAGES`) et
`toler_tva_import`, à semer par la révision 0003 (MODELE-DONNEES § 3.1.6) ; libellé, famille, unité,
défaut, bornes gardés ; aide = déclaration serveur (« srv ») ou texte d'écran versé dans la
déclaration (« écran → srv ») ; textes exacts dans ECRANS.md P8 § 2.1 et REGLAGES.md § 3, et pour
les deux réglages ajoutés par Gestion MP corrigé (E-10), `gestion_mp/parametres.py`. Écriture D sauf
mention ; A lit ; L jamais.

| Clé | Libellé | Onglet PRO / famille | Unité | Défaut | Bornes | Aide | Changement |
|---|---|---|---|---|---|---|---|
| seuil_critique | Couverture critique | parametres / Couverture et statuts | jours | 60 | 1-3650 | srv | ordre < seuil_alerte |
| seuil_alerte | Couverture d'attention | parametres / Couverture | jours | 90 | 1-3650 | srv | — |
| seuil_dormant | Stock dormant | parametres / Couverture | jours | 180 | 1-3650 | srv (C18) | — |
| delai_defaut | Délai par défaut | parametres / Approvisionnement | jours | 60 | 1-730 | srv | — |
| marge_jours | Couverture de commande | parametres / Appro | jours | 30 | 0-730 | srv | — |
| marge_securite | Marge de sécurité | parametres / Appro | % | 20 % | 0-500 % | écran → srv | — |
| taux_perte | Taux de perte matière | parametres / Appro | % | 2 % | 0-50 % | srv | — |
| securite_a | Sécurité classe A | parametres / Appro | jours | 30 | 0-365 | écran → srv | — |
| securite_b | Sécurité classe B | parametres / Appro | jours | 30 | 0-365 | écran → srv | — |
| securite_c | Sécurité classe C | parametres / Appro | jours | 30 | 0-365 | écran → srv | — |
| fenetre_realisation_jours | Prévision — fenêtre du réalisé | parametres / Appro | jours | 90 | 0-730 | srv | — |
| plafond_stock_min_mois | Stock minimum — plafond | parametres / Appro | mois | 3 | 0-60 | srv (C33) | — |
| croissance_annuelle | Croissance annuelle du plan | parametres / Appro | % | 0 % | −90 %-1000 % | écran → srv | — |
| seuil_abc_a | Classe A — valeur cumulée | parametres / Classification ABC / XYZ | % | 80 % | 0-100 % | écran → srv | ordre < seuil_abc_b |
| seuil_abc_b | Classe B — valeur cumulée | parametres / ABC-XYZ | % | 95 % | 0-100 % | écran → srv | — |
| seuil_xyz_x | Classe X — CV maximum | parametres / ABC-XYZ | — | 0,25 | 0-10 | écran → srv | ordre < seuil_xyz_y |
| seuil_xyz_y | Classe Y — CV maximum | parametres / ABC-XYZ | — | 0,5 | 0-10 | écran → srv | — |
| seuil_bc_urgent | BC urgent | parametres / Politique d'achat | MAD | 300 000 | 0-1e12 | écran → srv | **sans effet** (méthode corrigée seule) : affiché en lecture avec la mention « sans effet, gardé pour mémoire » (P8-17) |
| seuil_bc_groupe | BC groupé | parametres / Achat | MAD | 100 000 | 0-1e12 | écran → srv | — |
| seuil_tier1 | Tier 1 (classe A) | parametres / Achat | MAD | 300 000 | 0-1e12 | écran → srv | ordre ≥ tier2 (égalité permise) |
| seuil_tier2 | Tier 2 | parametres / Achat | MAD | 200 000 | 0-1e12 | écran → srv | ordre > tier3 |
| seuil_tier3 | Tier 3 | parametres / Achat | MAD | 100 000 | 0-1e12 | écran → srv | — |
| seuil_approbation | Approbation des commandes au-delà de | parametres / Achat | MAD | 0 | 0-1e12 | srv | — |
| toler_in_full | Tolérance de livraison complète | parametres / Réceptions et fournisseurs | % | 2 % | 0-20 % | srv + écran (fusion) | — |
| toler_ecart_pesee | Tolérance d'écart de pesée | parametres / Réception | % | 2 % | 0-100 % | écran → srv (C08) | — |
| toler_excedent | Excédent de livraison toléré | parametres / Réception | % | 10 % | 0-1000 % | srv + écran (fusion) | — |
| toler_poids_bobine | Tolérance du poids de bobine | parametres / Réception | % | 5 % | 0-100 % | écran → srv (C30) | — |
| toler_retard_jours | Retard toléré dans la ponctualité | parametres / Réception | jours | 0 | 0-60 | srv + écran (« … et une commande n'est dite « en retard » … qu'au-delà de ces N jours. ») | — |
| cible_otif | Cible OTIF | parametres / Réception | % | 95 % | 0-100 % | écran → srv | — |
| score_strategique | Score — Stratégique | parametres / Réception | /100 | 85 | 0-100 | à écrire (« classement Stratégique à partir de ce score ») | ordre > standard |
| score_standard | Score — Standard | parametres / Réception | /100 | 65 | 0-100 | à écrire | ordre > ATTENTION |
| score_surveiller | Score — ATTENTION | parametres / Réception | /100 | 45 | 0-100 | à écrire (« classement « À surveiller » ; en deçà « À challenger » ») | libellé gardé (consigne) ; l'aide nomme le classement « À surveiller » |
| tolerance_inventaire | Tolérance d'écart d'inventaire | parametres / Stock et inventaire | % | 2 % | 0-100 % | srv | rangée dans sa famille (REGLAGES 9.10) |
| seuil_hausse_forte | Forte hausse de prix à partir de | parametres / Prix | % | 5 % | 0,5 %-1000 % | à écrire | sert aussi à la fenêtre Évolution (P8-4) |
| fenetre_prix_jours | Écart maximal entre deux prix comparés | parametres / Prix | jours | 90 | 1-3650 | srv | — |
| taux_tva_import | TVA à l'importation | parametres / Prix | % | 20 % | 0-100 % | écran → srv (C29) | — |
| taux_tpi_import | Taxe parafiscale à l'importation (TPI) | parametres / Prix | % | 0,25 % | 0-10 % | srv + écran (fusion) | — |
| seuil_surcout_import | Frais d'un dossier d'importation à vérifier au-delà de | parametres / Prix | % | 100 % | 5 %-10 000 % | srv + écran (C35) | — |
| toler_facture_import | Facture d'un dossier à rapprocher au-delà de | parametres / Prix | % | 2 % | 0-100 % | srv + écran (C36) | — |
| toler_tva_import | TVA d'importation à vérifier au-delà de | parametres / Prix | % | 5 % | 0-100 % | srv (C29 et fiche du dossier) | ajouté par Gestion MP corrigé (E-10) ; **absent des semences 0002** : révision 0003 |
| delai_frais_import_jours | Dossier sans frais à signaler après | parametres / Prix | jours | 30 | 1-365 | srv (C28) | ajouté par Gestion MP corrigé (E-10) ; semé par 0002 |
| dso | Délai client moyen (DSO) | parametres / Trésorerie | jours | 60 | 0-3650 | à écrire (« cycle de trésorerie du Cockpit ») | — |
| nom_entreprise | Raison sociale | parametres / Société | texte | (vide) | ≤ 500 | srv | — |
| forme_juridique | Forme juridique et capital | parametres / Société | texte | — | ≤ 500 | srv | exemple de l'aide « … 20 000 000 MAD » (P8-23) |
| secteur | Secteur | parametres / Société | texte | « Fabrication de tapis mécaniques » | ≤ 500 | srv | — |
| adresse | Siège social | parametres / Société | texte | — | ≤ 500 | srv | — |
| ville | Ville | parametres / Société | texte | — | ≤ 500 | — | — |
| telephone | Téléphone | parametres / Société | texte | — | ≤ 500 | — | — |
| banques | Banques | parametres / Société | texte | — | ≤ 500 | srv | — |
| ice | ICE | parametres / Société | texte | — | ≤ 500 | — | — |
| rc | R.C | parametres / Société | texte | — | ≤ 500 | — | — |
| identifiant_fiscal | N.I.F (identifiant fiscal) | parametres / Société | texte | — | ≤ 500 | — | — |
| cnss | C.N.S.S | parametres / Société | texte | — | ≤ 500 | — | — |
| patente | Patente | parametres / Société | texte | — | ≤ 500 | — | — |
| date_cloture | Période close jusqu'au | **periode** | date | (vide) | passée | srv | `PUT periode-close` + motif (P8-9) |
| courriel_destinataires | Courriel du lundi : à qui | **administration / courriel** (famille technique) | texte | — | adresses `x@y.z` | srv | D, T ; adresses contrôlées au serveur (P8-19) |
| adresse_publique | Adresse du serveur pour les téléphones | **administration / technique** (famille technique) | texte | — | http(s)://, ≤ 200, sans espace | srv | D, T |

Anomalies : P8-6, P8-8, P8-13, P8-17, P8-18, P8-19.

---

### Devises — `/reglages?onglet=devises`

Gestion MP : onglet Devises (`ReglagesDevises.tsx` ; D et A) → PRO : `Carte` « Cours de change »
(`DataTable` en saisie) + `Carte` « Ajouter une devise » + fenêtre des cours ; D, A (L : rien).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /devises`, `GET /devises/{code}/historique` (toute session) ; `PUT /devises` (ACHATS) | `GET devises`, `GET devises/{code}/cours`, `POST devises`, `PUT devises/{code}` (D, A) | L refusé |
| Note « Le cours dit combien de dirhams vaut une unité de la devise (1 EUR = 10,8 MAD, par exemple)… Le dirham reste à 1. Chaque nouveau cours est daté et gardé : une commande garde le cours figé à la confirmation de ses prix, un dossier d'importation celui de la banque. » | `Note` ; « dirhams » → « MAD » | vocabulaire § 5 |
| Col. Code · Nom (éditable) · Cours (MAD) (170 px, grisé pour MAD) · Depuis le (« référence » / horodatage / « cours de la reprise », infobulle « Aucun changement depuis la mise en service : c'est le cours repris ») · Utilisée (case « active », grisée pour MAD) · actions ; tri code ; vide « Aucune devise. » | `DataTable` en saisie (`Nombre` fr) | — |
| Carte « Ajouter une devise » : Code (3 lettres, aide « GBP, CNY, TRY… », majuscules) ; Nom ; Cours en dirhams | `Form` ; « Cours (MAD) » | — |
| Fenêtre « Les cours du {nom} ({CODE} → MAD) » : Saisi le · Cours (MAD) (4 déc.) · Variation · Par ; vide « Aucun cours saisi depuis la mise en service. » ; note « Le plus récent d'abord. Le cours en vigueur est le premier de la liste. » | `Fenetre({taille:'large'})` + `DataTable` | — |
| Chaque enregistrement (même renommage) écrit un nouveau cours | un cours n'est écrit que si **le taux change** ; nom et activation → journal seul | P8-12 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Enregistrer » (ligne) | D, A | `PUT devises/{code}` `{nom, taux, actif}` | blocage « cours > 0 » en infobulle ; refus « Le dirham est la devise de référence : son cours reste 1. », taux (> 0, ≤ 10 000) | « Cours {CODE} enregistré : {cours} MAD. » ; P8-6 |
| « Annuler » (ligne) | D, A | — | — | retire la ligne du brouillon |
| « Historique » (infobulle « Les cours successifs de cette devise, qui les a saisis et quand ») | D, A | `GET devises/{code}/cours` | — | fenêtre |
| « Ajouter la devise » | D, A | `POST devises` | blocages en infobulle : « Code de 3 lettres », « Cours > 0 », « Devise déjà connue » | « Devise {CODE} ajoutée. » ; P8-6 |

Anomalies : P8-6, P8-8, P8-12, P8-13.

---

### Magasins — `/reglages?onglet=magasins`

Gestion MP : onglet Magasins (`ReglagesMagasins.tsx`) → PRO : `Carte` + `DataTable` + `Fenetre({sale})` ;
D écrit ; A lit.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Les magasins » + « Nouveau magasin » ; note « « Stock courant » : la matière disponible pour les machines. « Quarantaine » : … Cliquer sur un magasin pour le modifier. » | `Carte` + `Note` | — |
| Col. Code · Nom · Type (badge attention Quarantaine) · Contenu (« Tout ») · Stock détenu (kg) · État ; tri type puis code ; vide « Aucun magasin. » | `DataTable` | — |
| Fenêtre « Magasin {code} » / « Nouveau magasin » : Code (≤ 64) ; Nom ; Type (grisé si > 0,001 kg, aide « il détient de la matière : son type ne change plus ») ; Contenu (≤ 120 ; suggestions Tout, Fils, Fils PP, Fils PES, Chaîne et trame, Colles et intrants, Franges et cuir) ; case « magasin actif » ; message « Ce magasin détient encore {n} kg : transférer la matière avant de le désactiver. » | `Fenetre({sale})` + `Form` ; case « actif » grisée avec cette raison quand il détient (`blocages`) | P8-7 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau magasin » | D | — | — | fenêtre |
| clic ligne | D (A : lecture) | — | — | fenêtre |
| « Annuler » | D | — | garde `sale` | P8-8 |
| « Enregistrer » / « Créer le magasin » / « Enregistrement… » | D | `PUT magasins/{id}` / `POST magasins` | grisé si code vide (raison en infobulle) ; refus « Type de magasin : « Stock courant » ou « Quarantaine ». », « Le magasin « X » existe déjà. », « « X » détient encore 1 234 kg : transférer le stock avant de désactiver le magasin. », « Un magasin qui détient de la matière ne change pas de type. », « Magasin introuvable. » | message « Magasin enregistré. » ajouté ; format fr (P8-14) |

Anomalies : P8-6, P8-7, P8-8, P8-14.

---

### Postes de frais — `/reglages?onglet=postes`

Gestion MP : onglet « Frais » (`ReglagesPostesFrais.tsx`) → PRO : `Carte` + `DataTable` +
`Fenetre({sale})` ; D écrit ; A lit.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /postes-frais/complet` (ACHATS) | `GET postes-frais` (fondue) | contrat |
| Carte « Postes de frais d'importation » + « Nouveau poste » ; note « Un frais global d'un dossier se répartit… à la valeur… ou au poids… Changer une clé recalcule les dossiers ouverts ; les dossiers clos gardent leur répartition. Cliquer sur un poste pour le modifier. » | `Carte` + `Note` | — |
| Col. Ordre · Code (+ « calculs » pour DD, TPI, TVA, FRET, ASSUR, infobulle) · Libellé · Répartition (« à la valeur » / « au poids » ; « — » si récupérable) · Nature (« récupérable, hors coût » / « coût ») · Frais saisis · Dossiers ouverts · Dossiers clos ; ligne « Modifier le poste » | `DataTable` + `Badge` | — |
| Fenêtre « Poste {code} — {libellé} » / « Nouveau poste de frais » : Code (≤ 16, majuscules, figé ; aides) ; Libellé (≤ 80) ; Répartition (aide) ; Ordre (0-999) ; case « récupérable : hors du coût (comme la TVA) » (grisée : « Nature figée : les calculs du dossier lisent ce poste ainsi. » / « … il porte des frais dans {n} dossier(s) clos : créer un autre poste. ») ; message de changement de clé « Les {n} dossier(s) ouvert(s) seront recalculés… [Les {n} dossier(s) clos gardent leur coût…] » | `Fenetre({sale})` + `Form` + `Segments` (répartition) ; selects alignés | P8-27 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau poste » | D | — | — | fenêtre |
| clic ligne | D (A : lecture) | — | — | fenêtre |
| « Supprimer » | D | `DELETE postes-frais/{id}` | `Confirmer` « Supprimer ce poste ? · Non · Oui, supprimer » ; blocages « Ce poste sert aux calculs du dossier : il ne se supprime pas » / « Ce poste porte {n} frais dans des dossiers : il ne se supprime pas » ; infobulle « Supprimer ce poste, qui ne porte aucun frais » | — |
| « Annuler » | D | — | garde `sale` | P8-8 |
| « Enregistrer » / « Créer le poste » | D | `PUT postes-frais/{id}` / `POST postes-frais` | grisé si libellé ou code vide, ou rien modifié ; refus : code (« lettres, chiffres ou « _ »… »), « Le poste « X » existe déjà. », nature figée, dossiers clos, période close (« … changement du poste « … » refusé »), « Poste de frais introuvable. », « libellé : … » | frais globaux des dossiers clos figés à l'ancienne clé (journal « frais figés ») |

Anomalies : P8-8, P8-27.

---

### Codes douaniers — `/reglages?onglet=codes`

Gestion MP : onglet « Douane » (`ReglagesCodesDouaniers.tsx`, aussi Partie 7 § 1.8) → PRO : `Carte`
+ `Filtres` + `DataTable` + `Fenetre({sale})` ; D écrit ; A lit.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /codes-douaniers` (ACHATS) ; écritures DIRECTION | `GET codes-douaniers` (D, A) ; `POST/PUT/DELETE codes-douaniers` (D) | — |
| « Un instant — chargement : les codes douaniers… » ; erreur | `Chargement`, `Erreur` | — |
| Carte « Codes douaniers » + « Nouveau code » ; note « La position du tarif douanier et son taux de droits… signale l'écart avec la quittance. » | `Carte` + `Note` | « valeur en douane » : une seule définition (synthèse 6) |
| Recherche « Code, libellé… » ; « {n} code(s) » ; pas de filtre d'état | `Recherche` + filtre d'état (actifs / tous / désactivés) | P7-16 |
| Col. Code (mono gras) · Libellé · Taux de droits (« 10,0 % ») · Matières · État ; tri code ; ligne « Modifier le code » ; vide « Aucun code ne correspond. » / « Aucun code douanier. « Nouveau code » : 5402.47.00.00 (fils de polypropylène), son taux de droits… » | `DataTable`, `Vide` | — |
| Fenêtre « Code douanier {code} » / « Nouveau code douanier » : Code (≤ 20 ; aides « {n} matière(s) le portent : elles suivront la correction » / « chiffres et points (ex. 5402.47.00.00) ») ; Libellé (≤ 160) ; Taux de droits (%) (pas 0,1 ; aide « sur la valeur en douane : achat + fret ») ; case « code actif (proposé dans la fiche matière) » ; « Un taux de droits va de 0 à 100 %. » | `Fenetre({sale})` + `Form` ; format du code contrôlé à la frappe | P7-16 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau code » | D | — | — | fenêtre |
| clic ligne | D (A : lecture) | — | — | fenêtre |
| « Supprimer » | D | `DELETE codes-douaniers/{id}` | `Confirmer` « Supprimer ce code ? · Non · Oui, supprimer » ; blocage « {n} matière(s) portent ce code : le leur retirer, ou le désactiver » ; infobulle « Supprimer ce code, qu'aucune matière ne porte » | — |
| « Annuler » | D | — | garde `sale` | « Fermer » / « Abandonner les modifications » (P7-16, P8-8) |
| « Enregistrer » / « Créer le code » | D | `PUT codes-douaniers/{id}` / `POST codes-douaniers` | grisé si code vide, taux absent ou hors 0-100 %, rien modifié ; refus « Un code douanier s'écrit en chiffres… », « Le code douanier « X » existe déjà. », « Code douanier introuvable. » | journal « ancien · 10,00 % → nouveau · 12,00 % · désactivé » |

Anomalies : P7-15, P7-16, P8-8.

---

### Période close — `/reglages?onglet=periode`

Gestion MP : aucun écran ; « Période close jusqu'au » dans Paramètres › Société (`date_cloture`, D,
sans confirmation, part avec « Enregistrer N modification(s) ») → PRO : onglet `periode` (`Carte`,
`Definitions`, `DataTable`, `FenetreConfirmation`) ; D écrit ; A lit.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Champ date dans la famille Société ; aide « Rien ne s'écrit plus à cette date ni avant. » | `Definitions` « Période close jusqu'au : {date} » / « Aucune période close » + aide | onglet dédié |
| Refus serveur « On ne clôt qu'une période passée. » / « Date de clôture illisible (AAAA-MM-JJ). » (non vérifié à l'écran) | `DateChamp` max = veille (heure serveur) ; même refus au serveur | P8-7 |
| Effets : écriture datée ≤ clôture refusée « La période jusqu'au {date} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir. » ; coût d'une marchandise importée entrée dans la période refusé (409) « La marchandise {du dossier X | rattachée} est entrée le {date}, dans la période close jusqu'au {date} : son coût a été rendu avec le mois et ne change plus ({geste} refusé). Pour corriger ce mois, la direction rouvre la période (Réglages › Période close jusqu'au — c'est tracé), on saisit, puis elle la referme. » | textes gardés, affichés dans l'onglet ; « Réglages › Période close » | — |
| Rouvrir = vider le champ ; reculer la date sans garde | « Rouvrir la période » explicite ; reculer = rouvrir en partie, dit dans la fenêtre (« Vous rouvrez du {a} au {b} ») ; motif obligatoire | REGLAGES 9.13 |
| Trace au journal « paramètre » | historique des clôtures (date avant → après, motif, par, quand) | journal avant/après |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| poser « Période close jusqu'au » + « Enregistrer N modification(s) » | D | `PUT periode-close` `{date, motif}` | `FenetreConfirmation` « Clore la période jusqu'au {date} ? » : lecture de ce qui sera refusé ensuite (écritures datées, coûts des dossiers entrés dans la période) + nombre de brouillons datés dans la période ; motif saisi dedans (obligatoire) | bouton « Clore la période… » ; P8-9 |
| vider le champ (rouvrir) | D | `PUT periode-close` `{date:null|antérieure, motif}` | `FenetreConfirmation` « Rouvrir la période ? » + motif obligatoire | bouton « Rouvrir la période… » |

Anomalies : P8-7, P8-9.

---

### Administration (page) — `/administration?onglet=comptes|appareils|sauvegardes|journal|courriel|serveur|telephone|technique`

Gestion MP : 6 onglets techniques de Réglages (comptes, sauvegardes, journal, courriel, serveur,
téléphone) + 2 réglages de la famille Société → PRO : `/administration` (`Page`, `EnTete`,
`Onglets`) ; T, D ; T ne voit **aucune donnée métier** (pas d'aperçu chiffré du courriel).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Sous-titres : « Qui se connecte, avec quel rôle et quel code. » ; « Les copies de la base : leur état, leur conservation, en faire une, revenir à l'une d'elles. » ; « Qui a fait quoi, sur quoi, et quand — filtré et exportable. » ; « La synthèse de la semaine envoyée chaque lundi : à qui, et ce qu'elle dirait aujourd'hui. » ; « La version, la base, les sauvegardes, l'adresse sur le réseau et qui est connecté. » ; « Ouvrir Gestion MP sur un téléphone, dans l'usine ou en dehors. » | `aide.json` + ligne sous le titre par onglet ; + « Appareils » (« Les appareils enrôlés qui ouvrent l'écran de connexion. ») et « Technique » (« Les réglages techniques : l'adresse publique du serveur. ») | onglets nouveaux |
| Onglets « Comptes », « Sauvegardes », « Journal des actions », « Courriel » (« Courriel du lundi »), « Serveur », « Téléphone » | `Onglets` (libellé court + infobulle) | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| choisir un onglet | T, D | — | garde `sale` | — |

---

### Comptes — `/administration?onglet=comptes`

Gestion MP : onglet Comptes (`ReglagesComptes.tsx`, DIRECTION) → PRO : `Carte` + `Filtres` +
`DataTable` + `Fenetre({taille:'large', sale})` ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Les comptes » ; recherche « Nom, identifiant, rôle… » + « Nouveau compte » dans l'en-tête de carte ; note « Chacun a son compte : tout ce qui s'enregistre porte son nom. Un compte désactivé ne se connecte plus, et ses sessions ouvertes sont fermées. Cliquer sur un compte pour le modifier ou lui remettre un code. » | `Carte` + rangée `Filtres` (recherche) + `Note` | — |
| Col. Nom · Identifiant (mono) · Rôle (« Direction » / « Responsable achats » / « Responsable alimentation machines » / **« Administrateur technique »**) · Courriel · Dernière activité (« jamais connecté ») · État ; tri nom ; vide « Aucun compte ne correspond. » ; message sous le tableau | `DataTable` + `Messages` | rôle T ajouté |
| Fenêtre « Compte de {nom} » / « Nouveau compte » : Nom affiché (« tel qu'il apparaît à la connexion et dans le journal ») ; Identifiant (minuscules, sans espace ; figé ; aides) ; Rôle (descriptions exactes ; grisé pour soi ; défaut achats) ; Courriel (facultatif) ; Code / Nouveau code (« 4 chiffres au moins (saisi au téléphone) » / « 8 caractères au moins » ; changement de rôle : « nouveau rôle : un nouveau code est nécessaire, … ») ; Retaper le code (« les deux saisies diffèrent ») ; case « compte actif dès maintenant » ; messages « C'est votre compte : vous ne pouvez ni changer votre rôle ni vous désactiver. » / « Ce compte est désactivé : il ne peut plus se connecter. » | `Fenetre({sale})` + `Form` ; le code se remet par un geste à part (« Remettre un code ») ; description T : « comptes, appareils, sauvegardes, journal, serveur : aucune donnée métier » | P8-10, P8-11 |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Nouveau compte » | T, D | — | — | fenêtre |
| clic ligne | T, D | — | — | fenêtre |
| « Désactiver le compte » (infobulle « Le compte ne pourra plus se connecter et ses sessions ouvertes sont fermées ; il se réactive plus tard ») | T, D | `PUT utilisateurs/{id}` `{actif:false}` **seul** | `Confirmer` « Désactiver {nom} ? · Non · Oui, désactiver » ; blocage soi-même ; refus « Vous ne pouvez pas retirer vos propres droits de direction. » | n'envoie plus le reste du formulaire (P8-10) ; « Compte de {nom} désactivé : ses sessions sont fermées. » |
| « Réactiver le compte » | T, D | `PUT utilisateurs/{id}` `{actif:true}` | blocage soi-même | « Compte de {nom} réactivé. » |
| « Annuler » | T, D | — | garde `sale` | P8-8 |
| « Créer le compte » / « Enregistrer » / « Enregistrer et remettre le code » | T, D | `POST utilisateurs` / `PUT utilisateurs/{id}` + `POST utilisateurs/{id}/code` | `Bouton({manque})` : nom < 2, identifiant < 2, code trop court (« Le code doit faire au moins {n} caractères »), codes différents (« Les deux codes diffèrent ») ; refus « Rôle inconnu. », « L'identifiant « x » est déjà pris. », « Le code doit faire au moins {4|8} caractères. », « Compte introuvable. » ; **le serveur exige un nouveau code** quand un compte alimentation change de rôle | « Compte créé : {nom} (identifiant « {id} »). » / « Compte de {nom} enregistré, nouveau code remis. » / « Compte de {nom} enregistré. » ; P8-6, P8-11 |

Journal « création de compte » / « modification de compte » (« {nom} ({rôle}) ») avec avant/après.
Anomalies : P8-6, P8-8, P8-10, P8-11.

---

### Appareils (nouveau) — `/administration?onglet=appareils`

Gestion MP : aucun (un téléphone perdu se retirait par la console Tailscale + désactivation du
compte, note de l'onglet Téléphone) → PRO : `DataTable` des appareils enrôlés ; T, D (enrôler : depuis
l'appareil lui-même).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| note « Un téléphone perdu se retire depuis la console Tailscale, et son compte Gestion MP se désactive dans l'onglet « Comptes ». » | `Note` « Un appareil perdu se retire ici ; Tailscale le retire du réseau. » | nouveau |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| (aucun) « Enrôler cet appareil » | T, D | `POST appareils/enroler` | — | nouveau |
| (aucun) « Retirer » | T, D | `DELETE appareils/{id}` | `Confirmer` « Retirer cet appareil ? » | nouveau |

---

### Sauvegardes — `/administration?onglet=sauvegardes`

Gestion MP : onglet Sauvegardes (`ReglagesSauvegardes.tsx`, DIRECTION) → PRO : `Indicateurs` +
`Carte` + `DataTable` + `FenetreConfirmation` (restauration) ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Règles : `pg_dump -Fc` relue (`pg_restore --list`) ; noms quotidienne / manuelle / avant-restauration ; pièces jointes en miroir ; copie de sécurité ; purge 14 j + 1re du mois 12 mois ; alertes (pg_dump introuvable, échec, > 26 h, autres bases seulement) ; autres bases listées non comptées | inchangées ; alerte aussi dans `BandeauServeur` | — |
| Kpi « Dernière sauvegarde » (horodatage / « aucune » ; « il y a … » ; critique si alerte ou > 26 h) ; « Sauvegardes conservées » (« 14 jours, puis une par mois sur 12 mois » + infobulle) ; « Copie de sécurité » (Oui/Non ; chemin / « aucun second emplacement réglé sur le serveur ») | `Kpi({formule})` | — |
| Carte « Les sauvegardes » + « Sauvegarder maintenant » ; note (dossier, copie, **Conservation**, « Restaurer remplace toute la base… la restauration se défait. ») | `Carte` + `Note` | — |
| Col. Faite le · Nature (« automatique » / « manuelle » / « avant une restauration ») · Fichier · Base (« cette base » / autre base en attention) · Taille · « Restaurer… » ; 30 au plus ; vide « Aucune sauvegarde pour le moment. » ; notes « {n} fichier(s) du dossier sont des sauvegardes d'autres bases… » et « Les {n} plus récentes sont listées, sur {nb}. » (comptes mélangés) | `DataTable` (`ChargerPlus`) ; note de compte sur la même base | P8-28 |
| Fenêtre « Restaurer la sauvegarde du {date} » (non fermable pendant l'envoi) : étape 1 message, 3 puces, case « J'ai compris : la base va revenir en arrière. », « Annuler » / « Continuer » ; étape 2 « Dernière confirmation : taper RESTAURER… », « Restaurer maintenant » / « Restauration en cours… » ; succès « La base est revenue à l'état du {date}. Les autres postes doivent rouvrir leur écran ; si la session est perdue, se reconnecter. » + « Fermer » | `FenetreConfirmation` (lecture longue, A3) : mêmes 2 étapes et textes | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Sauvegarder maintenant » / « Sauvegarde en cours… » | T, D | `POST sauvegardes` | — | « Sauvegarde faite. » ; échec : message serveur lisible (« Sauvegarde impossible : pg_dump est introuvable sur le serveur. » / « La sauvegarde a échoué : … ») au lieu de « Erreur 500 » (P8-16) |
| « Restaurer… » | T, D | — | `Confirmer` « Revenir à l'état du {date} ? · Non · Oui, continuer… » ; blocage autre base (« Sauvegarde de la base « {b} », pas de celle-ci (« {base} ») : elle ne se restaure pas ici ») ; infobulle « Remplacer toute la base par cette sauvegarde (l'état actuel est d'abord sauvegardé) » | ouvre la `FenetreConfirmation` |
| « Continuer » | T, D | — | case cochée | étape 2 |
| « Restaurer maintenant » | T, D | `POST sauvegardes/{nom}/restaurer` | mot RESTAURER (casse indifférente) ; refus « Cette sauvegarde est celle de la base « X », pas de « Y »… », « Sauvegarde introuvable. », « pg_restore est introuvable sur le serveur. », « La restauration a échoué : … » | invalide tout ; journal « restauration » |
| « Annuler » (×2), « Fermer » | T, D | — | — | — |

Anomalies : P8-16, P8-28.

---

### Journal des actions — `/administration?onglet=journal`

Gestion MP : onglet Journal des actions (`ReglagesJournal.tsx`, DIRECTION) → PRO : `Carte` +
`Filtres` + `DataTable` + `ChargerPlus` ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `GET /journal/valeurs` ; `GET /journal?q=&utilisateur=&action=&objet=&du=&au=&limite=1000` (6 mots, `ILIKE` **avec accents**, 250 ms) | `GET journal/valeurs` ; `GET journal?q=&…` paginé (500 par page) ; recherche **sans accents**, tous les mots (A6) | P8-22 |
| Titre « Journal des actions — {n} entrée(s) » / « … — les 1 000 plus récentes » ; « recherche… » | `Carte` + compteur ; « Charger les 500 suivants » (A2) | plus de plafond muet |
| Filtres « Mots cherchés partout… », « Tout le monde » (« Qui »), « Toutes les actions » (« Quoi »), « Sur tout » (« Sur quoi »), « Du » (« À partir de ce jour »), « Au » (« Jusqu'à ce jour inclus ») ; « Effacer les filtres » dès 1 | `Recherche`, `Filtres` liés, `DateChamp` ; effacer dès 2 | A1 |
| Note « Chaque connexion, création, validation, annulation, modification de réglage s'inscrit ici et ne s'efface pas. Les 1 000 entrées les plus récentes… l'export les prend toutes. » | `Note` (« … chargées 500 par 500 … ») | — |
| Col. Quand · Par (nom + rôle) · Action · Sur (objet + « n° {id} ») · Détail ; vides « Rien ne correspond à ces filtres. » / « Le journal est vide. » | + colonnes **Avant** et **Après** (champ par champ) ; « Sur » → `LienDocument` vers la fiche | journal avant/après |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Exporter en Excel » (infobulle « Toutes les entrées qui répondent à ces filtres (sans limite), dans un classeur ») | T, D | `GET export/journal?…` | — | `journal-des-actions-AAAA-MM-JJ.xlsx` (100 000 au plus, ligne « Filtres — … ») ; colonnes Quand, Par, Rôle, Action, Sur, N°, Détail **+ Avant, Après** |
| « Effacer les filtres » | T, D | — | dès 2 filtres | — |
| « Charger les 500 suivants » (nouveau) | T, D | `GET journal?…&apres=` | — | A2 |

Anomalies : P8-22.

---

### Courriel du lundi — `/administration?onglet=courriel`

Gestion MP : onglet Courriel (`ReglagesCourriel.tsx` ; aperçu DIRECTION ; enregistrement par
`PUT /parametres`) → PRO : `Carte` « À qui, et comment » + `Carte` « Ce qu'il dirait aujourd'hui » (D)
+ file des courriels ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Destinataires (placeholder « direction@usine.ma, achats@usine.ma » ; aide « Adresses séparées par des virgules. Vide : pas de courriel. Il part chaque lundi matin. » / « Adresse(s) illisible(s) : … ») — **aussi** éditable dans Paramètres › Société sans contrôle | un seul endroit ; adresses contrôlées à la frappe **et** au serveur | P8-19 |
| Badge « serveur d'envoi réglé » / « non réglé » + notes « Le serveur sait envoyer… » / « … règle GESTION_MP_SMTP_HOTE (et l'expéditeur) dans son fichier de lancement. » | `Badge` + `Note` | — |
| Aperçu : « Objet : Gestion MP — la semaine du {jj/mm/aaaa} » + texte (valeur du stock, couverture pondérée, ruptures/critiques/urgentes, à commander, commandes en retard (8 n°), à approuver, brouillons, besoins signalés, réclamations, « Le détail : ouvrir Gestion MP (Cockpit). ») | `GET courriel/apercu` (**D seule** : chiffres métier) ; + lignes « Contrôles bloquants : {n} » et « Dernière sauvegarde : {date} » | P8-20 |
| Envoi réel : boucle de fond, un lundi, une fois (`courriel_dernier_envoi` caché), SMTP STARTTLS 587 | inchangé ; **file des courriels** (envoyés, en échec, motif) `GET courriels` | nouveau : visibilité des envois |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Annuler » (si modifié) | T, D | — | — | — |
| « Enregistrer les destinataires » | T, D | `PUT parametres` `{courriel_destinataires}` (famille technique) | blocages en infobulle : envoi, rien modifié, « Adresse illisible : … » | « Le courriel du lundi partira à {n} adresse(s). » / « Plus de courriel du lundi. » ; P8-6 |

Anomalies : P8-6, P8-19, P8-20.

---

### Serveur — `/administration?onglet=serveur`

Gestion MP : onglet Serveur (`ReglagesServeur.tsx`, `GET /etat-serveur` relu 60 s) → PRO :
`Indicateurs` + `Definitions` + `DataTable` ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Kpi « Gestion MP » (« version {v} », « schéma de base n° {n} · Python {v} ») ; « Base de données » (nom ; infobulle hôte:port ; « PostgreSQL {v} · {taille} ») ; « Adresse sur le réseau » (« http://ip:port » ; « {machine} · {système} ») ; « Sauvegardes » (« {n} conservée(s) » ok / « arrêtées » critique ; « dernière le … » / « aucune encore ») ; « Connectés » (« comptes avec une session ouverte ») | `GET serveur` (relu 60 s) + `Kpi` | route renommée |
| Carte « L'installation » (infobulle « Ces réglages se changent dans le fichier de lancement du serveur (variables GESTION_MP_…), pas ici… ») : Base · Serveur (HTTPS / réseau sans chiffrement) · Tâches de fond · Durée d'une session (« {30} jours sans se reconnecter ») · Dossier des sauvegardes · Copie de sécurité · Outils PostgreSQL (« pg_dump ou pg_restore introuvable : les sauvegardes ne se font pas ») · Conservation | `Definitions` ; tâches de fond détaillées par `GET taches` | — |
| Carte « Sessions ouvertes ({n}) » : Compte · Rôle · Dernière activité · Appareils · Expire le ; vide « Personne n'est connecté. » ; note « Une session par appareil… Désactiver un compte (onglet Comptes) ferme toutes ses sessions. » | `DataTable` | — |

Gestes : aucun (GMP : aucun).

---

### Téléphone — `/administration?onglet=telephone`

Gestion MP : onglet Téléphone (`AccesTelephone`, `GET /acces`, `GET /acces/qr`) → PRO : 2 `Carte` ;
T, D (le QR reste ouvert à C ailleurs).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Carte « Dans l'usine, sur le Wi-Fi » : adresse en grand ; erreur si l'adresse des QR contient localhost/127.0.0.1 (« … Régler « Adresse du serveur pour les téléphones » (Paramètres › Société)… ») ; QR SVG 150 px (`GET /acces/qr`) + note « Visez ce QR… Paramètres › Société › « Adresse du serveur pour les téléphones ». » ; étapes 1-4 (« Ajouter à l'écran d'accueil ») | `GET acces`, `GET acces/qr` ; renvois → « Administration › Technique » (lien `/administration?onglet=technique`) | droit T à ajouter sur `acces` |
| Carte « En dehors de l'usine, en 4G ou 5G » : Tailscale (texte, étapes, « ici probablement {machine} », `http://<nom-tailscale-du-serveur>:{port}`) ; note « Tailscale doit rester allumé sur le serveur. Un téléphone perdu se retire depuis la console Tailscale, et son compte… » ; port par défaut 8030 | `Note` ; la note renvoie aussi à l'onglet Appareils | — |
| Adresse des QR : `adresse_publique` sinon adresse d'appel | inchangé | — |

Gestes : aucun (lien vers Technique).

---

### Technique — `/administration?onglet=technique`

Gestion MP : réglage « Adresse du serveur pour les téléphones » (Paramètres › Société) → PRO :
`Form` de la famille technique ; T, D.

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| `adresse_publique` : aide « Ce que contiennent les QR des étiquettes, par exemple http://mac-usine:8030 (nom Tailscale…). Vide : l'adresse du serveur sur le réseau de l'usine. » ; refus « L'adresse commence par http:// ou https:// (ex. http://mac-usine:8030). » | `Champ` + contrôle à la frappe | déplacé |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Enregistrer » (via « Enregistrer N modification(s) » des Paramètres) | T, D | `PUT parametres` `{adresse_publique}` | `Bouton({manque})` | « Adresse des téléphones enregistrée. » |

---

### Bilan du mois (document) — `GET /api/documents/bilan?mois=AAAA-MM`

Gestion MP : page HTML `GET /api/bilan?mois=` ouverte par « Bilan du mois » du Cockpit (D) → PRO :
document serveur (gabarit Jinja2, A4, papier à en-tête, nouvel onglet) `GET documents/bilan` ;
données `GET bilan` ; D, A ; lancé du Cockpit (D) **et** de l'en-tête d'Analyse (D, A).

| Élément GMP | Élément PRO (composant) | Changement |
|---|---|---|
| Champ mois (défaut mois précédent, max mois en cours ; infobulle « Le mois du bilan ») + « Bilan du mois » (grisé si pas AAAA-MM ; infobulle « Le bilan du mois choisi — entrées, sorties, stock de début et de fin, production, achats — dans une page à imprimer ») | `DateChamp` (mois) + `BoutonImprimer` | offert aussi aux achats (P8-24) |
| Droits ACHATS ; `mois` `^\d{4}-\d{2}$` ; mois 13 → 500 ; mois futur accepté | `GET documents/bilan` (D, A) ; 422 « Mois illisible (AAAA-MM, de 01 à 12). » ; mois futur refusé « Le bilan d'un mois à venir n'existe pas encore. » | P8-16, P8-24 |
| Page HTML autonome (titre « Bilan MM/AAAA », 13 px, bouton « Imprimer » masqué à l'impression, grille 4 colonnes, « 1 234 », « -0 » → « 0 ») | gabarit A4 papier à en-tête (raison sociale, forme et capital, siège, ville, banques…) ; mêmes formats | P8-24 (en-tête complet) |
| Calculs : stock début/fin (journal, quarantaine comprise) ; flux par type, contre-passations en annulations ; entrées (kg, valeur au cours figé, hors annulées) ; sorties, retours machine, retours fournisseur, ajustements, ouvertures, annulations ; valeur début (veille du 1er), valeur fin (min(fin, aujourd'hui)) ; consommation au coût du journal ; m² par qualité (ordres validés) ; 8 plus grands écarts ; commandes numérotées du mois ; réceptions validées ; OTIF ; ruptures / critiques | mêmes calculs, sauf : « Commandes émises » **hors annulées** ; kilos et valeur de fin sur la même base (journal, sans le fil monté, dit dans la note) | P8-24 |
| h1 « Bilan matières premières — {MM/AAAA} » + raison sociale | idem + en-tête complet | — |
| h2 « Le mois en chiffres » : « Stock au début », « Stock à la fin », « Stock d'ouverture saisi » (si ≠ 0), « Entrées (réceptions) » (« … MAD, hors réceptions annulées »), « Sorties vers les machines » (« dont {kg} kg revenus · coût net … »), « Tissé », « Commandes émises » (« {n} réception(s) »), « Livraisons parfaites (OTIF) », « Ajustements » (« retours fournisseur {kg} kg ») | idem ; « Sorties vers les machines » détail « retours des machines {kg} kg · coût net {…} MAD » | P8-23 |
| Paragraphe « Valeurs au coût moyen pondéré… Stock à la fin = début + entrées + ouvertures − sorties + retours des machines − retours fournisseur + ajustements + annulations. Annulations (contre-passations) datées du mois : {kg} kg (…) — elles défont des écritures… » | idem | — |
| h2 « Fabrication, qualité par qualité » (Qualité · m² tissés ; « Aucun ordre ce mois-ci. ») | idem | — |
| h2 « Les plus grands écarts entre la recette et le réel » (Ordre · Qualité · Prévu (kg) · Sorti net (kg) · Écart) ; « Aucun. » | « Les plus grands écarts entre le prévu par la recette et le sorti net » ; « Prévu par la recette (kg) » | P8-23 |
| h2 « À la fin du mois » (« {n} matière(s) en rupture, {n} critique(s). ») | idem | — |
| Libellés des types d'annulation (Stock d'ouverture, Entrée de réception, Sortie vers les machines, Retour des machines, Retour au fournisseur, Ajustement d'inventaire, Transfert entre magasins) | `Badge` (table unique statut → libellé) | — |

| Geste GMP (libellé exact) | Rôles | Route API PRO | Confirmation / blocages | Changement PRO |
|---|---|---|---|---|
| « Bilan du mois » (Cockpit ; et en-tête d'Analyse) | D (Cockpit), D, A (Analyse) | `GET documents/bilan?mois=` | mois AAAA-MM, pas futur | nouvel onglet |
| « Imprimer » | D, A | — | — | impression du navigateur |

Anomalies : P8-16, P8-23, P8-24.

---

### Exports Excel de la partie 8

| Bouton (onglet) | Route GMP | Route PRO | Droit PRO | Changement |
|---|---|---|---|---|
| Valorisation | `/export/valorisation?date_reference=` | `GET export/valorisation` | D, A | suit les filtres |
| Matrice / Prix payés | `/export/prix` | `GET export/prix` | D, A | — |
| Opportunités | `/export/opportunites?…` | `GET export/opportunites` | D, A | — |
| Fournisseurs | `/export/fournisseurs` | `GET export/fournisseurs` | D, A | « À surveiller » sans émoji |
| Coût de revient | `/export/revient?…` | `GET export/revient` | D, A | — |
| Échéancier | `/export/echeancier?du=&au=` | `GET export/echeancier` | D, A | + feuille Réglées ; tous les filtres |
| Contrôles | `/export/controles` | `GET export/controles` | D, A | échelle unique des écarts |
| Journal des actions | `/export/journal?…` | `GET export/journal` | D, T | + Avant, Après |

---

### Anomalies GMP corrigées — Partie 8

1. `?fournisseur=` de l'Analyse jamais rempli → `/analyse?onglet=fournisseurs&fournisseur=ID` ouvre « ses réceptions » ; la fiche fournisseur y mène.
2. Valorisation : « hors stock » contre « compris » → un seul texte (« compris dans le stock »), conforme au calcul.
3. Écart de C36 affiché ×100 → une seule échelle : tous les écarts relatifs en fraction avec `unite:'%'`, formatés une fois (écran et export).
4. Seuils en dur → Évolution des prix suit `seuil_hausse_forte` ; Production (5 %) et Valorisation (2 %) restent fixes mais sont écrits dans la `Formule` du Kpi.
5. Opportunités sans « Effacer les filtres » → ajouté (remet les défauts).
6. Boutons grisés sans raison → `Bouton({manque, blocages})` partout (case > 8, « Ajouter la devise », cours ≤ 0, destinataires, comptes, magasin, « Aucune modification »).
7. Refus découverts au clic (magasin qui détient, date de clôture future) → `blocages` du magasin ; `DateChamp` max = veille.
8. Saisies perdues (brouillons au changement d'onglet, « Annuler » des fenêtres) → garde `sale` au changement d'onglet et sur chaque « Annuler » ; « Annuler » des Paramètres confirmé sur place.
9. Clôture de période sans confirmation → onglet `periode`, `FenetreConfirmation` avec motif, `PUT periode-close`.
10. Désactiver un compte envoie le formulaire → `PUT utilisateurs/{id}` `{actif}` seul ; code par `POST utilisateurs/{id}/code`.
11. Nouveau code au changement de rôle exigé à l'écran seulement → exigé par le serveur.
12. Historique des cours faussé (cours réécrit à chaque enregistrement) → cours écrit seulement si le taux change.
13. « 10.85 » dans l'historique → valeurs localisées (« 10,85 »).
14. « 1,234 kg » et « 2% » → format français partout (« 1 234 kg », « 2 % »), libellés C08 et C30 compris.
15. Libellé C29 trompeur → « TVA d'importation à plus de 5 % de la TVA attendue (20 % de la valeur en douane, droits et TPI compris) », la tolérance tirée du réglage `toler_tva_import` (Gestion MP corrigé, E-10).
16. Erreurs 500 brutes (sauvegarde, mois 13) → messages serveur lisibles (503 / 422).
17. Réglage et code morts (`seuil_bc_urgent`, branches classeur, message inatteignable, `HAUT_DIALOGUE`) → `seuil_bc_urgent` affiché en lecture « sans effet, gardé pour mémoire » ; branches classeur non reprises ; `EcranReserve` ; `Cadre` mesure la hauteur.
18. Famille « Stock et inventaire » sans aide → phrase ajoutée.
19. Destinataires du courriel édités à deux endroits sans contrôle serveur → un seul endroit (Administration › Courriel), adresses vérifiées au serveur.
20. Contenu du courriel en deçà de sa promesse → lignes « Contrôles bloquants » et « Dernière sauvegarde » ajoutées.
21. Échéancier : « Par mois » et indicateurs ignorent les filtres, pas de total, export sans réglées → filtres au serveur pour tout, pied de totaux, feuille « Réglées ».
22. Recherche du journal avec accents → sans accents, tous les mots, au serveur.
23. Vocabulaire du bilan, « DH », classement « À surveiller » → « prévu par la recette » / « sorti net », « retours des machines », « MAD », « À surveiller » (classement) partout, sans émoji.
24. Bilan : commandes annulées comptées, bases kg/valeur différentes, sans en-tête, mois futur, réservé à la direction à l'écran → annulées exclues, même base, papier à en-tête, mois futur refusé, offert aux achats depuis l'Analyse.
25. Achats voient Coût de revient, Échéancier, Production (hors REGLES § 4) → décision gardée (contrat : `/analyse` D, A) ; REGLES § 4 à mettre à jour.
26. Page Analyse charge tout pour les compteurs malgré son commentaire → comportement gardé (cache partagé), commentaire faux retiré.
27. Selects sans classe `entree` → `Champ` / `Selecteur` alignés partout.
28. Note des sauvegardes compare deux comptes différents → compte sur la même base.

### Synthèse transverse de GMP (lignes 7713-7783) — traitement PRO

1. Fil monté décrit de trois façons → un seul texte, porté par `aide.json` (« Sur les métiers : compris dans le stock et sa valeur ») ; modèle tranché dans `DECISIONS.md` § 16.1 ; C25 aligné.
2. Boutons cliquables puis refusés → `Bouton({manque, blocages})` calculé au serveur pour tous ceux listés (fournisseur, rôle, recette, quarantaine, magasin, « Tout valider », clôture de dossier…).
3. Saisies perdues sans question → garde `sale` sur fenêtres, onglets et boutons « Annuler / Fermer ».
4. Droits écran ≠ serveur → registre unique `routes.ts` + mêmes rôles côté API ; QR `/lot/:id` : téléphone + L → atelier, sinon `/lots/:id` ; transferts ouverts à L dans `/operations` ; codes douaniers lisibles par A ; `/compte` pour changer son code (`PUT moi/code`).
5. Vocabulaire hors règle → vocabulaire § 5 appliqué (contrôle statique des libellés).
6. Chiffres contradictoires → échelle unique des écarts (C36), une définition de la valeur en douane et de la TVA saisie, TPI lue dans son réglage, un seul compte des matières en alerte.
7. Gestes sans effet, code mort → non repris (case « nos prix du catalogue », route `exporter_bon_de_commande`, « BC urgent » en lecture, `?fournisseur=` rempli).
8. Réseau et téléphone → erreur réseau distincte d'une liste vide, `?ordre=ID` rouvre le brouillon, relance des requêtes sur le statut HTTP.
9. Atomicité → une transaction par geste (camion multi-devises, métier, qualité fiche + recette).
10. Contrôles faibles → tableur aussi strict que la fiche, clôture confirmée, journal et mouvements paginés sans plafond muet.
11. Documents d'exploitation en retard → titres d'onglets PRO dans la notice, générés depuis `routes.ts`.

### Comptes de la partie 8

- Écrans PRO : 3 pages (`/analyse`, `/reglages`, `/administration`) + 1 document (Bilan du mois) — GMP : 2 pages + 1 document.
- Onglets : Analyse 9 ; Réglages 6 (dont `periode`, nouveau) ; Administration 8 (dont `appareils` et `technique`, nouveaux) = 23 (GMP : 20). Sous-vues : Bascule Évolution 2, Coût de revient 3, Échéancier 4, familles de Paramètres 9 (Méthode de calcul devenue aide) = 18 (GMP : 19).
- Fenêtres : 11 GMP repris (Évolution des prix, réceptions d'un fournisseur, détail d'un contrôle, ordre de fabrication, historique des paramètres, cours d'une devise, magasin, poste de frais, code douanier, compte, restauration en `FenetreConfirmation`) + 2 `FenetreConfirmation` de période (clore, rouvrir) = 13 ; 3 à adresse stable (`&fournisseur=`, `&controle=`, `&ordre=`).
- Contrôles décrits : 38 ; réglages décrits : 57 (55 dans `/reglages` : 54 dans `parametres`, dont `seuil_bc_urgent` en lecture, et 1 dans `periode` ; 2 dans `/administration`) — 56 semés par 0002, `toler_tva_import` par 0003.
- Gestes : 82 GMP, tous repris ; 98 lignes PRO (nouveaux : « Bilan du mois » d'Analyse, « Effacer les filtres » des Opportunités, « Charger les 500 suivants », « Chercher dans les lignes » serveur, appareils 2, période 2).
- Anomalies : 28 traitées (P8-1 à P8-28) + 11 incohérences transverses de la synthèse.

### Routes demandées par la partie 8 (reportées dans API-PRO § 1.24)

- `GET controles/{code}` (D, A) — détail complet d'un contrôle, paginé (`apres=`), recherche `?q=` sans accents ; remplace le détail coupé à 200 lignes dans `GET controles`.

Précisions de contrat (pas de nouvelle route) :
- `GET echeancier` reçoit aussi `q` et `nature` (tous les filtres au serveur).
- `GET journal` reçoit `apres=` pour la pagination « Charger les 500 suivants ».
- `PUT parametres` : D pour les familles métier, **T et D** pour la famille technique (`courriel_destinataires`, `adresse_publique`).
- `GET acces`, `GET acces/qr` : droit à étendre à **T** (onglet Téléphone de l'Administration).
- `PUT periode-close` : corps `{date|null, motif}` (clore, reculer, rouvrir).
- `GET parametres/historique` : D, T seulement — l'onglet Période close montre à A la date en vigueur, pas l'historique.

---

## 7. Comptes

| Partie (heritage/ECRANS.md) | Écrans GMP → PRO | Onglets, sous-vues | Fenêtres | Documents | Gestes GMP repris | Anomalies GMP traitées |
|---|---|---|---|---|---|---|
| 1 Coque, connexion, accueil, cockpit, mode d'emploi, lot | 7 → 10 (`/compte`, `/administration` en arrivée de T ; page du lot fondue dans `/lots/:id`) | 16 | 4 + menu | 2 (appels) | 30 / 30 | 28 / 28 |
| 2 Stock, sorties, production | 3 → 3 + `/tracabilite` | 29 | 7 | 1 (appel) | 72 / 72 | 25 / 25 |
| 3 Atelier, métiers, étiquettes | 18 → 18 (+ onglet Historique des métiers) | 7 | 2 | 1 | 92 / 92 (+ 14 nouveaux) | 29 / 29 |
| 4 Achats | 3 → 3 | 30 | 8 | 2 (1 doublon supprimé) | 77 / 77 | 21 / 21 |
| 5 Importations | 1 (+ 3 logés ailleurs) → 4 | 23 | 4 | — | 59 / 59 | 20 / 20 |
| 6 Inventaire, opérations | 2 → 2 | 9 | 7 | 1 | 36 / 36 (+ 17 nouveaux) | 25 / 25 |
| 7 Catalogue, qualités | 2 → 2 | 23 | 9 | — | 71 / 71 | 33 / 33 |
| 8 Analyse, réglages, bilan | 2 → 3 (`/reglages` et `/administration` se partagent les 11 onglets) | 39 | 11 | 1 | 82 / 82 | 28 / 28 |
| **Total** | **38 → 46 écrans PRO** (les 17 écrans du téléphone gardés un par un ; au bureau, `/compte`, `/administration`, `/tracabilite` en plus) | **≈ 176** | **≈ 52** | **4 documents** + 28 classeurs | **519 / 519** | **209 / 209** |

Chaque geste de Gestion MP a sa ligne dans la partie qui le décrit, avec sa route d'API PRO ;
chaque anomalie a son traitement. Les routes que la rédaction des parties a demandées sont
ajoutées à `API-PRO.md` § 1.24.
