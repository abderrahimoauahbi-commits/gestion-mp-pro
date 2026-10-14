# Audit n° 2 du domaine ACHATS, avec modifications — Gestion MP PRO (14/10/2026)

Suite du passage n° 1 (`AUDIT-ACHATS.md`), qui n'avait rien corrigé. Branche `audit2-achats`
depuis `main` (9b20443). Base d'essai `gestion_mp_pro_achats2_essai` (schéma recréé par les
essais ; les fabriques font les données), supprimée à la fin. Types de l'écran vérifiés contre
l'OpenAPI de la branche (`scripts/generer_types.sh --verifier` : à jour, aucun schéma n'a changé).

## Modifications

| # | Quoi | Pourquoi | Preuve | Risque |
|---|---|---|---|---|
| 1 | **P1 — mètres indicatifs selon le rôle.** `commandes_socle.kg_par_ml(m)` : la densité d'une matière dont le rôle est `lineaire` (Cuir, Franges, Ruban), 0 sinon ; les fiches sont chargées avec leur rôle (`charger_matieres`). La fiche du bon (`kg_par_ml`, `metres`) et le bon fournisseur (colonne « Length (m, indicative) ») la lisent ; plus la seule présence d'une densité. | Décision du coordinateur (P1) : même règle que le moteur (`calcul.modele.Article.kg_par_ml`). Un poil à qui l'on donne une densité n'a pas de mètres. | `test_audit2_achats::test_les_metres_indicatifs_suivent_le_role_pas_la_densite` (échouait avant : `kg_par_ml` = 0,5 et « Length » imprimée pour un poil). Le cuir garde ≈ 1 200 m (`test_bon_fournisseur` inchangé). | Nul sur les vraies données (densité seulement sur Cuir et Bande, rôles linéaires) ; une requête de plus par lecture (rôles, 8 lignes). |
| 2 | **U2 — un prix au mètre se confirme au mètre** (`VoletPrix.tsx`). `uniteDe(l)` : `ml` quand la fiche est au mètre (`unite_prix = ml`, densité > 0), sinon `kg`. La saisie se fait dans cette unité (« USD / ml »), l'écran dit « soit 5,71 / kg » dessous, le catalogue s'affiche dans l'unité de la ligne avec l'équivalent dans l'autre, l'écart et le montant se comptent au kilo, « reprendre le catalogue » propose le prix au mètre ; le corps envoie `unite: 'ml'` (le serveur ramène au kilo par la densité, route 160, inchangée). Le texte du volet dit la règle. | Décision de Mohamed du 08/10 (U2), non implémentée à l'écran (passage 1, P2 / question 1). | `VoletPrix.test.ts` (5 essais : unité, aller-retour, corps envoyé, comparaison au catalogue, reprise du catalogue) ; côté serveur `test_audit2_achats::test_un_prix_au_metre_se_confirme_au_metre` (0,074 / ml, densité 0,014 → 5,285714 / kg ; catalogue au mètre 0,074 ; refus clair pour une fiche sans densité). **Rejoué à l'écran** sur la copie (serveur 8160, bon BC-2026-0001, cuir 0,074 USD/ml + poil 2,80 USD/kg) : 0,08 / ml tapé → « soit 5,71 / kg », +8,1 %, 8 000 USD ; confirmé → bon « Confirmée », catalogue 0,08 USD / ml, montant 14 960 USD. | Faible : une matière au kilo ne change pas (`liste.test.ts` inchangé). Aujourd'hui aucune fiche réelle n'est au mètre (Q1 ouverte sur le cuir). |
| 3 | **Prix confirmé nul une fois arrondi** (`commandes.confirmer_prix`) : un prix > 0 qui vaut 0 au millionième (0,0000001) est refusé en clair (422 : « … vaut 0 au kilo une fois arrondi au millionième : saisir le prix réel. »). | Avant : ligne « confirmée » à 0, bon « Confirmée », montant nul — trompeur. | `test_un_prix_nul_une_fois_arrondi_est_refuse`. | Nul. |
| 4 | **Quantité ou contenance nulle au gramme** (`commandes_saisie.verifier_quantite`) : 0,0001 kg passe la borne (> 0) mais vaut 0 au gramme ; refus 422 `quantite_invalide` « « POIL » : la quantité (0,0001 kg) vaut 0 au gramme près : saisir au moins 0,001 kg. », à la création comme à la modification. | Avant : la base refusait (CHECK `quantite_positive`) et l'écran disait un 409 « Cette saisie contredit une règle de la base… » obscur. | `test_une_quantite_nulle_au_gramme_est_refusee_en_clair` (échouait avant : 409). | Nul. |
| 5 | **P3 — `taux_du_jour` clé monétaire** (`securite/prix.CLES_MONETAIRES`) : le cours de change de la liste des bons est masqué comme `cours*` pour un rôle qui ne voit pas les prix. | Passage 1, P3 : la protection reposait sur la garde de route seule. `taux_perte` reste visible (production). | `test_le_cours_du_jour_d_un_bon_est_monetaire` ; `test_prix_masques` (liste `MONETAIRES` complétée). | Nul (routes déjà D, A). |
| 6 | **Aide de l'excédent toléré** (`registre_reglages`, `toler_excedent`) : « … plus cette part de la **quantité commandée sur la ligne** (pas du reste), **tous les camions ensemble** : une ligne de 1 000 kg à 5 % reçoit au plus 1 050 kg en tout, même en plusieurs livraisons. Au-delà, la réception est refusée… ». Fixture d'écran `reglages/essais/parametres.json` alignée. | Décision du coordinateur (question 2 du passage 1) : la règle ne change pas, l'aide la dit. | Lecture de la route 23 (texte du registre) ; aucun chiffre comparé. | Nul. |
| 7 | **Infobulle du badge d'écart** (`TablePreparation.Ecart`, `calculPreparation.expliquerEcart`) : rouge « critique » : « Commandé 15 % sous la suggestion du calcul : le besoin ne serait pas couvert jusqu'à la commande suivante, risque de rupture. » ; orange : « … au-dessus … : plus de stock et de trésorerie immobilisés que le besoin. » ; vert : « À 5 % de la suggestion du calcul (10 % près…) ». | Décision du coordinateur (question 3 du passage 1) : garder le rouge, dire pourquoi. | `calculPreparation.test.ts` (« l'infobulle du badge dit pourquoi »). | Nul. |
| 8 | **Kilos à 2 décimales** dans la préparation (`TablePreparation.Kilos`, `decimales={2}` au lieu de 3), comme la fiche du bon (`VoletLignes`). | Règle « kg jusqu'à 2 décimales utiles ». | Essais de l'écran verts. | Très faible : une quantité déduite d'un nombre d'unités garde ses 3 décimales (règle serveur). |
| 9 | Documentation : `ECRANS-PRO.md` § 4.9 (volet Prix) dit le nouveau texte et les colonnes sans unité dans l'en-tête ; docstring du bon fournisseur. | — | — | — |

Aucune décision de Mohamed (DECISIONS.md) n'est touchée ; aucune révision Alembic.

## Ce qui a été vérifié de plus et tient

- Envoi, approbation, renvoi, solde, réouverture : dates refusées dans le futur et en période close
  (`periode.date_permise`), version périmée → 409 partout, garde-fou d'approbation (R-CMD-16).
- Préparation d'une commande (route 150) : `possibles` a toujours le kilo, `_depart` ne divise jamais
  par 0 ; un fournisseur inconnu → 404.
- Fournisseurs : devise inconnue / hors service refusées en clair, nom unique sans la casse,
  suppression refusée avec ce qui pèse (matières, commandes, réceptions…).
- Bon fournisseur : toujours sans prix, montant ni devise ; un bon mêlant cuir et poil imprime la
  colonne « Length » avec la cellule du poil vide (rejoué sur la copie).
- `make verifier` complet vert (serveur, écran, outils) ; `generer_types.sh --verifier` : à jour.

## Ce qui reste

- **Q1 (DECISIONS)** : la fiche du cuir réel est au kilo ; tant qu'elle n'est pas passée « au mètre »,
  le volet Prix le confirme au kilo. Dès que la fiche est au mètre, l'écran bascule seul.
- Une préparation de commande chez un fournisseur **désactivé** s'ouvre (route 150) ; c'est la
  création du bon qui refuse (« désactivé : le réactiver »). Le plan ne suggère rien chez lui en
  pratique ; à signaler plus tôt si un cas se présente (QUESTION d'écran, pas corrigé).
- Deux `ligne_id` identiques dans une même confirmation de prix : le dernier prix gagne, sans
  refus (l'écran ne peut pas le produire).
