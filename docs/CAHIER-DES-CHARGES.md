# Gestion MP PRO — Cahier des charges

*Document de référence, pour Mohamed et son informaticien.* Ce que **fait** Gestion MP PRO, par
domaine et par rôle, avec les décisions de métier de Mohamed qui le fondent et les règles qui le
tiennent. Il décrit le logiciel livré, pas l'historique du projet : l'historique daté des choix
est dans [`docs/heritage/DECISIONS.md`](heritage/DECISIONS.md) (codes `P*`, `D*`, `U*`, `F*`,
`A*`, `R*r`, `I*`, `O*`, `V*`, `N*`, `T*` cités ici), la conception technique dans
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`MODELE-DONNEES.md`](MODELE-DONNEES.md),
[`API-PRO.md`](API-PRO.md) et [`ECRANS-PRO.md`](ECRANS-PRO.md), la preuve dans
[`RECETTE.md`](RECETTE.md), la comparaison chiffrée avec Gestion MP dans
[`COMPARAISON-GESTION-MP.md`](COMPARAISON-GESTION-MP.md).

Gestion MP PRO est la **réécriture professionnelle** de Gestion MP (l'ERP des matières premières
d'une usine de tapis, en service), au standard de GMAO PRO. Le métier est **le même**, les
chiffres sont **les mêmes** (parité prouvée) ; ce qui change est la robustesse, la sécurité, la
structure et la vérification (voir `COMPARAISON-GESTION-MP.md § 3`).

---

## 1. Objectifs

Repris des demandes de Mohamed (M01–M86) et tranchés au plus près de la pratique d'usine là où il
a délégué (« fais au mieux… colle le plus possible à la réalité », P11).

| # | Objectif | Mesure tenue |
|---|---|---|
| O-1 | **Les mêmes chiffres** que Gestion MP, et que le classeur d'origine ; toute correction d'un calcul faux est **proposée, écrite et justifiée**, jamais faite en silence (P3). | Parité 0 écart à corriger (RECETTE A6) ; corrections déclarées K1–K9 (`COMPARAISON § 2`). |
| O-2 | **Juste, stable, performant** : vérificateur à 0 écart, aucune erreur 500 sur une saisie, chaque écran courant sous 0,3 s (M16). | RECETTE A5, A9, A13. |
| O-3 | **Multi-postes** sans validation en double, sur PostgreSQL, serveur partagé (P5). | Verrous, concurrence 50× (A10). |
| O-4 | **Atelier au téléphone**, en Wi-Fi et en 4G/5G, **sans aucun prix** (D2, D5). | Balayage « aucun prix » (A4) ; recette navigateur (A8). |
| O-5 | **Reprendre toute l'activité** depuis Gestion MP / l'ERP Fil en lecture seule, vider l'activité en gardant les référentiels, garder une base vide de référence (P8, P9, P16). | Reprise idempotente (A11) ; `outils/`. |
| O-6 | **Sauvegarder avant tout, pouvoir revenir en arrière** (P4). | Sauvegardes relues, restauration réversible (A12). |
| O-7 | Un **exécutable** et un **raccourci sur le bureau** ; coexistence avec Gestion MP sur le même Mac (P2, P15). | Lot X2 (poste Mac) ; coexistence vérifiée. |

Les données **réelles** de l'entreprise — catalogue, classification, fournisseurs, qualités et
recettes — ne sont **jamais supprimées** ni corrigées en silence ; l'activité présente est une
**année d'épreuve** qui disparaît à la mise en service (P8).

---

## 2. Rôles et droits

Quatre rôles : trois métier (D1) et un technique (D12). Le serveur **refuse ce que le menu
cache** : chaque route déclare ses rôles (`droit(...)`), une matrice versionnée les rejoue toutes
(D3, RECETTE A3). Les prix ne sortent **jamais** vers l'alimentation (D5, A4).

| Rôle | Peut | Ne peut pas |
|---|---|---|
| **Direction** (Mohamed) | **Tout** : comptes, réglages, sauvegardes, journal, **approbation** des commandes, plan de production, qualités et recettes, codes douaniers et postes de frais, clôture de période, reprise et miroir. | — |
| **Achats** (la responsable) | Matières, classification, fournisseurs ; plan d'achat, commandes (envoi, pas approbation), réceptions, étiquettes, factures, importations et frais, réclamations ; ouvertures, ajustements, retours fournisseur, transferts, inventaire ; **lecture** du pilotage. | Approuver un bon, comptes, journal, réglages (sauf **Devises**), plan/recettes, monter des fils. |
| **Alimentation des machines** (l'atelier, au téléphone) | Sorties vers les machines, retours, transferts, déplacements, **montage des fils** sur les métiers, signaler un besoin, chercher un lot (QR). Lecture du stock (quantités, statuts), du plan de production, des métiers. | **Voir le moindre prix, montant, cours, budget ou conseil d'achat** (écran, API, exports) ; cockpit, plan d'achat, commandes, réceptions, analyse, réglages. |
| **Administrateur technique** | Réglages techniques, sauvegardes, état du serveur, comptes, journal des actions (noms d'actions, **aucune valeur**). | **Aucune route métier** d'écriture (vérifié : il n'est nommé que sur les routes techniques). |

Connexion (D10) : on touche son nom, on tape son code ; **4 chiffres exactement** pour
l'alimentation (validation au 4ᵉ), **8 caractères au moins** pour achats et direction ; après
5 échecs, le compte patiente. Le compte de direction ne se désactive ni ne change de rôle (D9) ;
changer son code ferme les autres sessions. Le premier lancement crée le compte de direction
(exemple de nom proposé : « MAZARI », P12).

---

## 3. Ce que fait le logiciel, domaine par domaine

### 3.1 Référentiels (matières, classification, fournisseurs, qualités, métiers)

- **Matières** : la référence **se compose** (composition + type de fil + titrage + couleur +
  code + suffixe), modifiable, recherche cumulative par nature/type/titrage (F2). Une matière en
  service exige un fournisseur (F9) ; une devise appartient au **prix de la matière**, jamais au
  fournisseur (F1). Import par tableur avec aperçu avant d'écrire, « Appliquer » grisé s'il reste
  une erreur (F23).
- **Un fournisseur = une matière = un prix = une devise** (F5) ; l'alternative est une autre
  matière du même **groupe d'équivalence**. Pays choisi dans une liste (F11) ; délai **déclaré**
  et délai **mesuré** (F12).
- **Unités (U1–U8)** : le **stock est toujours en kilos**, pour toutes les matières, **cuir, bande
  (ruban) et franges compris**. Le **prix** se saisit au kg ou **au mètre** (ramené au kilo par la
  densité) ; un fournisseur qui facture au mètre lit des mètres (U2). Les rôles de recette **au
  mètre** (Cuir, Franges, Ruban) se saisissent en ml/m², convertis en kg/m² par la densité
  obligatoire (U3, U6) ; les mètres sont affichés **à titre indicatif** à côté des kilos (U4).
- **Qualités et recettes** : un fil sert **plusieurs qualités** (F4) ; la recette d'un rôle fait
  **100 %** (tolérance 0,01 pt) ; une recette qui oublie un rôle pesant est **refusée** (F13).
  Recettes **versionnées, datées, signées** ; « revenir à une version » remet parts **et** poids,
  motif obligatoire (F14). Les rôles « au mètre » et les huit rôles de base ne changent pas de
  nature (F15).
- **Métiers** : quatre métiers, 6 ou 8 étages de 4,20 m (F16, F17) ; nommés « CRM 1 · Métier 1 »,
  rangés par nom (F20).
- **Supprimer** une matière, un fournisseur, une valeur de classification, une qualité, un métier
  est **grisé s'il existe un historique** ; sinon reclasser ou désactiver (F3, F9).

### 3.2 Achats : plan, commandes, approbation, bon fournisseur

- **Jamais de bon sans laisser choisir** : une fenêtre propose les quantités en kilos **et en
  palettes**, arrondies au conditionnement (A1, A3). Le **bon part sans prix** ; le fournisseur
  confirme ; la saisie du prix confirmé fait vivre le catalogue et la matrice (A2).
- **Un bon par devise** (A5) ; numéro donné **à l'envoi** (A10) ; daté à l'envoi, jamais dans le
  futur ni en période close (A11). Un brouillon affiche « Brouillon », sans numéro ; un bon parti
  ne se supprime plus, il s'annule et garde son numéro (A4).
- **Approbation** (A6, A8) : un bon au-delà du seuil (réglage, MAD) passe « À approuver » ; la
  direction « Approuve et envoie » (numéro donné) ou « Renvoie aux achats » (motif obligatoire,
  affiché sur le bon). Un bon dont le montant augmente ou franchit le seuil repasse « À
  approuver », approbation effacée, numéro conservé ; la hausse se mesure dans la devise du bon au
  **cours figé** ; un bon à approuver ne se reçoit ni ne se solde ; rouvrir repasse par
  l'approbation. Le montant qui déclenche est le **montant estimé** (A9).
- **Cours figé à la première confirmation** de prix (A12) ; **date promise** figée avec les prix,
  la ponctualité se juge sur elle, l'**ETA** sert à la prévision et au « en retard » (A13).
  Jalons d'expédition jamais dans le futur, après l'envoi seulement (A14).
- **Bon fournisseur** : **une page A4, en anglais, sans aucun prix**, sur le **papier à en-tête**
  de l'usine (raison sociale, forme juridique, capital, siège ; pied : banques, ICE, R.C, N.I.F,
  C.N.S.S, patente) ; conditionnements traduits, kilos, mètres indicatifs pour cuir/franges/ruban
  (A22). Remarques au fournisseur dans une case à part (A23).
- **Score fournisseur** = OTIF × 60 + retours 20 (0 % → 20, 5 % → 0) + délai 20 (jusqu'à 15 j),
  plafonné (A25).

### 3.3 Réceptions, quarantaine, réclamations

- Une arrivée regroupe **une ou plusieurs commandes**, entières ou partielles, dite **par ligne**
  (R1r). On ne reçoit que sur un **bon parti** ; sinon « hors commande » (devise choisie) (R7r).
  **Une réception par devise** : un camion à deux devises donne deux réceptions, même BL, chacune
  sa facture (R8r).
- Saisie en **palettes complètes + bobines** ; le **poids pesé fait foi** (R3r, R9r) ; le poids de
  bobine est **mesuré par lot** et suivi dans le temps (R4r). Excédent toléré **par ligne**, sous
  verrou (R14r). Une livraison partielle sans BL n'est pas un écart (R13r).
- Ligne **« sous réserve » → quarantaine** (en stock, valorisée, non disponible), ne solde la
  ligne qu'à sa **libération** (décision des achats, D6) ; ligne **refusée** → rien en stock
  (R11r). Une réception entièrement refusée est gardée comme trace, numérotée (R12r). **Lot
  interne** numéroté à la validation, jamais pour une ligne refusée (R17r).
- Reçu d'un bon **net des retours** au fournisseur ; un retour **rouvre** le bon soldé (R15r).
  **OTIF** : tolérance de date unique, complétude sur les lignes dues, camion de plusieurs bons —
  chaque pesée garde son bon (R16r).
- **Facture complétable après validation** (R19r). **Réclamations** ouvertes depuis une réception
  ou un lot, issue (avoir, remplacement, rien) obligatoire pour clore (R20r).

### 3.4 Importations et coût de revient

- **Un dossier = une facture = une livraison** (numéro de la maison `NN/AA`), ouvert **depuis la
  facture** d'une réception, prenant toute sa marchandise ; un second camion de la même facture
  rejoint son dossier ; une facture déjà portée n'en ouvre pas un second (I3). Un **fournisseur
  marocain n'a pas de dossier** (I16).
- Le dossier calcule le **coût de revient** (I1) : marchandise au **cours figé**, **répartition
  des frais à la valeur** (poids en option par poste, I2, I8), **droits attendus par code
  douanier** sur la valeur en douane CAF (I11), **TVA attendue** = 20 % × (valeur en douane +
  droits + **TPI 0,25 %**, réglable) — la TVA n'est **pas un coût** (I12). Poids figé à l'entrée,
  en kilos vrais (I18).
- **Clôturer fige le cours** et énumère les alertes (I14) ; dans un mois clos, le coût d'une
  marchandise **ne change plus** (I22, V3). **Frais non répartis** affichés à part partout (I15).
  Contrôles C35 (frais aberrants) et C36 (facture ≠ pesée × prix) (I20). **Coût d'une qualité
  pondéré par la recette** (I17).

### 3.5 Stock, lots, production, atelier

- **Le journal est la seule écriture de stock** ; soldes (lot, magasin) tenus dans la même
  transaction sous verrou de ligne ; un contrôle confronte soldes et journal (U15). **Le stock
  d'un lot ne passe jamais sous zéro** (« sous le gramme, un stock est nul », U16). **Saisie en
  deux temps** : brouillon (sans numéro, sans effet) → validé (immuable) → annulation par
  **contre-passation** datée de l'effet d'origine (U19).
- **Le stock est en magasin ou en machine** : le fil **monté sur les métiers** compte dans le
  stock, sa valeur et le disponible/projeté — « ne jamais l'en retirer » (U8, décision **K7** côté
  parité). Les fils montés = bobines × **poids de bobine pesé au lot** (F18) ; montage **explicite
  et confirmé**, tracé, avec alerte si l'on monte plus que sorti en 30 jours (F19). La
  **quarantaine est en stock mais à part** : ni disponible, ni sortie, ne compte pas pour les
  achats (U9). **Statut du lot calculé** (U13).
- **Écritures antidatées** refusées si elles feraient passer un lot sous zéro **à leur date ou
  après** (U17) ; aucun fait dans le futur, avant 2000, ni en période close (U18).
- **Ordres de fabrication** : un OF sert une fois, numéro et date à la validation, **jamais daté
  avant le dernier ordre validé** (O1) ; porte plusieurs articles et qualités (O2). **Proposition
  FIFO** par recettes et m², lots disponibles à la date de l'ordre, validation tout ou rien (O3) ;
  prévu **pertes comprises**, figé à la validation (O4, O5). Une qualité arrêtée ne part plus
  (O6). **Retour des machines** : pas plus que ce qui est parti (O7) ; **annuler un ordre
  contre-passe aussi ses retours** (O8). La sortie en cours au téléphone est gardée (O13).

### 3.6 Valorisation, change, période close

- **CMUP** (coût moyen pondéré glissant) au coût rendu usine, **une seule implémentation** lue par
  la Valorisation, le Cockpit, le journal valorisé et l'inventaire (V1) ; à défaut d'achat, prix
  catalogue. Une **annulation défait l'écriture à son coût** ; un retour fournisseur sort au coût
  d'entrée de son lot ; **un coût nul est un coût** (V2).
- **Mois clos figé** (V3) : la direction clôt (réglage « Période close jusqu'au ») ; plus aucune
  écriture d'effet antérieur ; le coût d'une marchandise entrée dans un mois clos **ne change
  plus**. Corriger = la direction **rouvre** (tracé), on saisit, elle referme. **Cours figé sur
  chaque mouvement** à la validation (V4). Une **date passée rejoue** journal, réceptions et
  commandes (V5).

### 3.7 Inventaire

Inventaire **figé à l'ouverture** (numéro dès l'ouverture), par magasin, famille ou classe ABC ;
**mouvements suspendus sur son périmètre** (K2 : pas tout le magasin — pratique d'usine demandée
par la direction) ; comptage par lot, **second comptage** sur écart, justification au-delà de la
tolérance (réglage 2 %), écarts valorisés, feuille à l'aveugle, **inventaire tournant** (A 30 j,
B 90 j, C 365 j) (N1). Refusé s'il est daté avant le dernier mouvement d'un lot qu'il fige (N2).
Un inventaire abandonné garde ses lignes, hors des calculs (K3).

### 3.8 Pilotage, analyse, contrôles

- **Plan d'achat** : avant de commander, Disponible + Commandé (à l'**ETA**) − demande pendant le
  délai = Projeté (A19, U10) ; **ce qui ne se consomme plus ne se rachète pas** (A17) ; tier et
  urgence **selon le statut**, pas le montant (A18). Un brouillon n'est attendu de personne (A16).
- **Cockpit** : six indicateurs (Valeur, Couverture pondérée, À commander, Commandé, Rotation,
  Contrôles) ; un seul statut par matière (T10). La **valorisation compte tout** le stock, magasins
  et machines (U11). Rotation et DIO au CMUP sur la consommation des 12 mois clos (V7) ; XYZ sur
  les sorties nettes, dormants par dernière sortie **ou** entrée (V6).
- **Matrice des prix** (évolution par arrivée, pastilles de couleur, plus récents d'abord, T1–T4)
  et **opportunités d'économies** (même composition/type/titrage, **même couleur par défaut**,
  **coût rendu usine**, fenêtre réglable — ne jamais comparer deux dates différentes, T5, T6, T9) ;
  prix dans leur monnaie d'origine, un axe par devise (T8).
- **38 contrôles** (C01…C38) : chacun dit **quoi faire** et **mène au document** ; ceux
  impossibles par construction sont « garantis par la base », hors de la note (T11). **Bilan du
  mois** équilibré en kg et en MAD. **Courriel du lundi** (retards, alertes, échéances) + Accueil
  « Ma journée » (T12).
- **Montants jamais additionnés entre devises** (F1). Toute valeur affichée au format français ;
  kg à 3 décimales, « — » pour une valeur nulle, jamais « -0 ».

### 3.9 Exploitation et administration

- **Sauvegardes relues** (`pg_restore --list`), avec les pièces jointes, jamais purgées pour les
  « avant » ; copie externe. **Restauration réversible** (sauvegarde « avant restauration »), tout
  ou rien, migrée, les autres sessions prévenues. `/api/sante` public signale une sauvegarde de
  plus de 26 h. **Journal des actions** avant/après (qui, quoi, quand), réservé à la direction (et
  lu, sans valeur, par l'administrateur).
- **Reprise** depuis Gestion MP en lecture seule (miroir tant que PRO n'est pas en service),
  **idempotente**, numéros gardés. **Vider l'activité** en gardant les référentiels ; **base vide
  de référence** gardée (P8, P9). Coexistence avec Gestion MP : rien de partagé (dossier, port
  8050, base, rôle PostgreSQL, cookie, verrous).

---

## 4. Règles structurantes (ce qui tient tout le logiciel)

1. **Une méthode de calcul unique** (la « corrigée ») ; le mode « classeur » abandonné, la parité
   restant prouvée par la comparaison (P17).
2. **Le serveur décide des droits**, pas l'écran : `droit(...)` sur chaque route, matrice générée
   et rejouée (D3).
3. **Aucun prix chez l'alimentation**, à toute profondeur, par un filtre unique et générique (D5,
   P-02).
4. **Le journal est la seule écriture de stock** ; un lot jamais sous zéro ; verrous de ligne
   (U15, U16).
5. **Brouillon → validé → contre-passation** ; numéros sans trou ni doublon, dans l'ordre des
   dates **de validation** (registre), la date d'effet à côté (U19, A10, décision **DM-08**).
6. **Dates** : rien dans le futur, avant 2000, ni en période close ; dit dès le brouillon (U18).
7. **Mois clos figé** : la valeur du passé ne bouge plus (V3) ; un changement de cours ne
   revalorise jamais un mois clos (décision **K8i**/K9).
8. **Verrou optimiste** par champ `version` sur chaque fiche : 409 « modifié entre-temps » si deux
   postes écrivent (F10, adapté en `version` pour PRO).
9. **La base refuse elle-même l'incohérent** : 291 CHECK, 171 clés étrangères, 41 unicités,
   déclencheurs (stock immuable) ; une contrainte violée devient un refus propre (409), **jamais
   une 500** (RECETTE A13).
10. **Toute donnée réelle est intouchable** : référentiels jamais supprimés, données douteuses
    **signalées, pas corrigées en silence** (P8, exigence M11).

---

## 5. Décisions qui restent à confirmer par Mohamed

Là où Gestion MP n'avait pas tranché, PRO garde un comportement et le signale (il ne change rien
en silence). Ces neuf points (DM-01 à DM-09 de `DEFAUTS-GESTION-MP.md`) et les points de revue de
`docs/lots/RESTES.md` sont la liste d'ouverture de la livraison ; le détail et la recommandation
« pratique d'usine » sont dans [`RECETTE.md § 7`](RECETTE.md) et dans
[`heritage/DECISIONS.md`](heritage/DECISIONS.md) (V9, et les `[?]`). En résumé : prix de la bande
et du cuir (au kilo ou au mètre), matière « Franges », TPI 0,25 %, sortie oubliée à cheval sur une
fin de mois, données de reprise signalées, consommation et fil monté, « les numéros suivent les
dates », réceptions payées en deux devises (garder ou scinder), et ce que l'administrateur
technique voit du journal.

---

*Référence : Gestion MP PRO 0.1.0. Décisions sources : `docs/heritage/DECISIONS.md`. Preuve :
`docs/RECETTE.md`.*
