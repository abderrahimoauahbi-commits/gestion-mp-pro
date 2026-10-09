# Lot RESTES4 — restes côté écran : ce que les lots suivants doivent savoir

Branche `lot-RESTES4`. Lignes de `docs/lots/RESTES.md` destinées aux lots d'écran (E0, E1, F1…F8)
traitées et retirées, plus la ligne V1 (bon reçu sous réserve). `backend/` n'est pas touché.
Chaque comportement corrigé a son essai vitest, qui échoue sans la correction.

## 1. Ce qui a changé, point par point

| Reste | Ce qui est fait | Essai |
|---|---|---|
| E0 statuts d'inventaire | `lib/statuts.ts › inventaire` : « Comptage en cours » (ouvert), « Annulé » ; la table locale de F6 (`inventaire/types.ts`) est retirée, les badges passent par `Badge famille="inventaire"`. | `lib/statuts.test.ts` |
| E1 `Bascule` | `flex-wrap` et `max-width: 100%` : trois vues passent à la ligne au téléphone au lieu de sortir de la carte. | `Bascule.test.tsx` (feuille lue) |
| E1 `Barres` | `empiler` : une barre par étiquette, chaque série posée sur la précédente, l'axe va au total, l'infobulle dit la part et le total. Plan glissant (F2) : sept qualités empilées + « Autres » (gris), et la matière en kg dans son propre panneau. | `Barres.test.tsx`, `Production.test.tsx` |
| E1 `Confirmer` | `motifMin`, `libelleMotif`, `exempleMotif`, `motifMax` ; `MOTIF_MIN = 3`, `manqueMotif()`. « Oui » grisé avec « un motif de 3 caractères au moins ». `commandes/ConfirmerMotif.tsx` supprimé (renvoi aux achats, annulation de réception, réouverture de réclamation, annulation de règlement) ; l'inventaire (abandon, annulation) grise « Oui » au lieu de refuser après coup. | `Confirmer.test.tsx`, `Inventaire.test.tsx` |
| E1 `FenetreConfirmation` | `etapes` (lectures avec « Continuer » et leur case), `mot` à taper, `motifMin`/`motifMax`/`aideMotif`, `fermerApres={false}` + `issue` (l'opération suivie dans la même fenêtre, non fermable tant qu'elle court). La restauration (F8) y passe. | `FenetreConfirmation.test.tsx`, `Administration.test.tsx` |
| E1 `Onglets` | `garde` : changer d'onglet demande « Les abandonner ? » (`proteger`) tant qu'une saisie est en cours. Aucune page ne le pose encore (Réglages et Production tiennent leurs brouillons au niveau de la page : rien ne se perd). | `Onglets.test.tsx` |
| E1 `Interrupteur` | `manque`, `blocages`, `grise` : grisé avec sa raison (`data-raison`, infobulle, description). Postes de frais (F5) : la nature figée grise l'interrupteur, la note la redit. | `Interrupteur.test.tsx`, `PostesFrais.test.tsx` |
| E1 `PiecesJointes` | `mode="complet" | "joindre" | "lecture"` (`lectureSeule` = lecture). Dossier : ouvert complet, clos « joindre seulement », annulé lecture (`FicheDossier.modePieces`). | `PiecesJointes.test.tsx`, `FicheDossier.test.tsx` |
| E1 `LienDocument` | `state` (`{ retour }`) et `titre` ; le clic ne remonte pas à la ligne cliquable. `revient/liens.tsx` n'a plus sa copie : `LienDossier` passe par `LienDocument` (le fichier garde `Dossiers`, `LienMatiere`, `useRetour`). | `LienDocument.test.tsx` |
| E1 `DataTable` | `videFiltre` (texte de la page quand les critères ne retiennent rien ; dossiers : « Aucun dossier ne correspond à la recherche. ») ; `groupe` : une ligne d'en-tête (`th scope="rowgroup"`) avant chaque suite de même clé. L'échéancier du dossier (F5) l'emploie : un mois par ligne de groupe (« à payer … » par devise, « la saisir sur le frais ») au lieu de la colonne « Mois ». | `DataTable.test.tsx`, `FicheDossier.test.tsx` |
| E1 `ScanQR` | Un QR qui n'est pas une adresse de lot est relu par `GET /lots/scan` (`lireEtiquette`) : un lot → sa fiche ; aucun → « Aucun lot pour cette étiquette ({texte}). » ; plusieurs → « {n} lots portent ce numéro : choisir ci-dessous » et `onPlusieurs(numéro)` (Trouver un lot filtre sa liste). Un même texte n'est relu qu'une fois tant qu'il reste devant la caméra. | `ScanQR.test.tsx` |
| E1 `SelecteurLot` | Forme `Schema<'LotDisponible'>` de la route 111 (une ligne par lot et magasin) ; magasin facultatif (un lot dans deux magasins proposé une fois, kilos ajoutés, magasins nommés) ; `onChange(id, lignes)`. | `SelecteurLot.test.tsx` |
| E1 `BoutonImprimer` | `taille="atelier"` : toute la largeur, 46 px ; la règle de l'atelier le vérifie ; l'étiquette de la fiche du lot l'emploie (plus de surcharge dans `atelier.module.css`). | `atelier.test.tsx` |
| E1 `.masque-accessible` | `top: 0; left: 0` : le texte masqué ne rallonge plus la page qui défile ; le contournement `position: relative` de F1 (accueil, cockpit) est retiré. | `styles/base.test.ts` |
| F2/F3 moteur unique | `lib/ordre.ts` (+ `ordreEcarts.ts`, `ordreBlocages.ts`) : prises **en kilos** (unité de comptage à part), proposition, « Recalculer », fils, écart (une seule règle), blocages avec les phrases du serveur, ce qui manque, corps envoyé (lignes en kg), `demanderProposition`, `enregistrerOrdre` (brouillon puis validation ; un refus garde le brouillon). `sorties/ordre.ts` et `atelier/sortie.ts` supprimés ; `useSaisieOrdre` (bureau) et `useSaisieSortie` (téléphone, saisie gardée) n'ont plus de règle à eux. Le téléphone saisit par `Quantite tactile` (conversion et arrondi dits par le composant). | `lib/ordre.test.ts` (essais F2 et F3 réunis), `Envoyer.test.tsx`, `Sorties.test.tsx` |
| F1 retour au Cockpit | « Examiner » ouvre `/commandes/{id}` avec `state.retour` ; `useListeEtFiches` le retient tant que la fiche reste ouverte (changer de volet le perdait) et y ramène en fermant (aussi pour les réceptions). | `Cockpit.test.tsx` |
| F3 tuiles à 360 × 640 | « Envoyer aux machines » sur toute la largeur (`Tuile principale`), icône à côté du titre, détails raccourcis (deux lignes au plus) : les sept tuiles tiennent au-dessus de la barre du bas (mesuré : dernière tuile à 490 px, barre à 576 px). | `Ordres.test.tsx` |
| F6 `/operations/:id` | Déjà déclarée par F6 ; F2 la liait par `permis` (rien à faire). Atelier : les retours d'un ordre et les n° de transferts et retours du journal d'un lot mènent à leur fiche d'opération (les ordres à `/atelier/ordres/:id`). | `Ordres.test.tsx`, `Lots.test.tsx` |
| F5 en-tête | `importations/ecrans.ts` ne cite plus `PageAnalyse` / `PageReglages`. | — |
| V1 réserve | Ligne du bon : « dont X kg reçus sous réserve, en quarantaine : attendus jusqu'à leur libération » sous le reste à livrer (`messages.texteReserve`) ; fiche : note « Reçu : Dont X kg… » + l'explication `formule.commande_reserve` d'`aide.json`, aussi ajoutée à la formule du « Commandé » du Cockpit (`formuleKpi`). X = `LigneCommande.en_quarantaine` (déjà servi). | `Commandes.test.tsx`, `Cockpit.test.tsx` |

## 1 bis. Adaptation à RESTES3 (`make types` après la fusion)

| Changement du serveur | Ce que fait l'écran | Essai |
|---|---|---|
| Statuts du stock en codes (`RUPTURE`…, `NON_CONSOMMEE`), `action` `CREER_BC`/`AUCUNE` | `cleStock` ne lit plus que les codes (`CLES_STOCK`, type `CleStock`) ; les jeux d'essai (`*/essais/*.json`, `plan-achat/donneesEssai.ts`) portent les codes. | `lib/statuts.test.ts` |
| `LigneStock.fournisseur_id`, `role_id` | « Préparer la commande » (Cockpit, Stock, fiche matière) lit `fournisseur_id` de la ligne ; le Cockpit ne lit plus `/matieres`. Le rôle (nom) reste lu dans `/matieres` (la ligne n'a que son id). | `Cockpit.test.tsx` |
| `EtapeTracee.document_type/document_id`, `matiere_id`, `ordre_id` | Le n° de document d'une étape mène à sa fiche (`lienMouvement`, `permis`) ; matière et ordre se suivent par leur id (plus de table référence → id ni numéro → id). | `Stock.test.tsx` |
| `MouvementLigne.devise` nulle hors direction et achats | La colonne prix ne s'écrit qu'avec une devise. | (tsc) |
| `CommandeResume.en_retard`, `arrivee_attendue`, `arrivee_sous_7_jours`, `kg_en_quarantaine` ; `CommandeFiche.promesse_figee` | Ma journée et Cockpit : retards = `en_retard` (plus de `GET /commandes?filtre=retard`), arrivées = `arrivee_sous_7_jours` triées par `arrivee_attendue` (plus de calcul de dates à l'écran) ; fiche du bon : la date promise figée dit `promesse_figee`, la note de réserve lit `kg_en_quarantaine`. | `taches.test.ts`, `Commandes.test.tsx` |
| Route 246 `GET /periode-close/brouillons` | Réglages › Période : dès la date choisie, les brouillons datés de la période sont annoncés (genres présents) et « Clore la période… » est grisé avec le refus du serveur. | `Reglages.test.tsx` |
| QR avec `xmlns` | `administration/qr.ts` n'ajoute plus rien (vu au navigateur : l'image s'affiche). | — |
| `OrdreResume.metier` « CODE · Nom » | L'atelier l'écrit tel quel (liste, fiche, sortie enregistrée) ; `useNomMetier` ne sert plus qu'à la saisie (métier choisi par id). | `Ordres.test.tsx` |
| `InventaireFiche.abandon_motif` | L'en-tête d'un inventaire abandonné lit son motif là (plus dans `annulation_motif`). | `Inventaire.test.tsx` |
| Signalements (`Schema<'SignalementFiche'>`) | Déjà lus dans l'OpenAPI (fait par F1) : ligne de RESTES.md retirée. | — |
| Lien de la cloche selon le rôle | Le filtre `permis` de la cloche reste (règle générale d'E2 : aucun lien que le rôle ne peut ouvrir). | — |

Inchangés à l'écran : filtres du classeur du plan d'achat (l'écran envoyait déjà `statut`, `priorite`, `abc`, `fournisseur`, `urgence`, `devise`, `pays`) ; pesée « Brouillon » (l'écran lisait déjà le statut) ; recherche à la ponctuation près (côté serveur).

## 2. Décisions

1. **Prises tenues en kilos** dans le moteur unique (choix de F2) : le téléphone envoyait la quantité
   dans son unité (bobines) ; il envoie désormais des kilos, comme le bureau, et ses retours et
   déplacements (F3, décision 4). La saisie gardée du téléphone change de clé (`envoyer2`) pour
   ne pas relire une saisie de l'ancienne forme.
2. **Une seule règle d'écart** : « conforme » sous 0,05 kg ou 0,5 % ; puis ok à 5 % près (P2-25) ;
   au-delà excès attention, manque critique. Le téléphone montrait la zone 0,5–5 % en gris
   (`neutre`) : elle est désormais `ok`, comme le badge des Sorties.
3. **Phrases** : celles du serveur pour les blocages (date future, période close, inventaire,
   ordre plus récent, lot qui ne porte pas assez) ; « commentaire » y devient « observations »
   (vocabulaire an. 8) et le champ du bureau s'appelle « Observations (facultatif) » comme au
   téléphone. Ce qui manque se dit pareil aux deux endroits (« À renseigner : le magasin, la
   date, la qualité de chaque ligne, les m² à tisser de chaque qualité. »).
4. **Inventaire qui suspend un magasin** : le contexte nomme le magasin par son **nom** ; le bureau
   le comparait au **code** (un inventaire d'un seul magasin n'était jamais annoncé au bureau).
   Le moteur compare le nom ; les phrases des lots manquants gardent le code (celles du serveur).
5. Tuiles de l'atelier : textes raccourcis (ECRANS-PRO partie 3 à reporter) — « Qualité et m² à
   fabriquer : fils et lots proposés. », « Ce qui revient, lot par lot. », « Chercher, scanner
   l'étiquette. », « Par métier, étage par étage. », « Fil qui manque, palette qui finit. »,
   « {n} en attente · {r} réponse(s) ».
6. Pas de pastille « factures sans dossier » (reste D7 → F1) : ECRANS-PRO § 2.1 n'en prévoit pas,
   Ma journée en fait déjà une tâche.

## 3. Écarts aux documents (à reporter)

- ECRANS-PRO partie 3 (accueil de l'atelier) : textes des tuiles (décision 5), « Envoyer aux
  machines » sur toute la largeur.
- ECRANS-PRO P2-25 / `EcartFil` : la zone 0,5–5 % est `ok`, plus grise (décision 2).
- ECRANS-PRO « Logique de l'envoi » : `lib/ordre.ts` existe (il était prévu), avec deux
  sous-modules ; les lignes partent en kilos des deux côtés.
- Serveur (`services/ordres/proposition.empechements`) : la phrase dit « dans le commentaire » ;
  l'écran dit « dans les observations ». À aligner côté serveur (vocabulaire an. 8).

## 4. Vérification

- `npm run verifier` : voir le rapport du lot (nombre d'essais).
- Navigateur : Chrome sans tête à profil séparé (`--user-data-dir` à soi, port CDP 9364), serveur
  du lot sur 8164 et Vite sur 5264, base `gestion_mp_pro_restes4_essai` (copie de la base de
  parité de R2, trois comptes d'essai), arrêtés et supprimée ensuite.
