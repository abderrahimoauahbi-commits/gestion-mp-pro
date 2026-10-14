# Audit du domaine ACHATS — Gestion MP PRO (14/10/2026)

Audit demandé par Mohamed (« audit complet, corrige quand tu es vraiment sûr »).
Branche `audit-achats` depuis `main` (1443f33). Base d'essai `gestion_mp_pro_achats_essai`,
copie des vraies données (`pg_dump -Fc gestion_mp_pro` → `pg_restore`), alembic à `0008` (tête).

## Périmètre couvert

- Plan d'achat : suggestions, besoins, conseil d'achat (`calcul/plan_achat.py`,
  `calcul/stock/`, `api/plan_achat/`, `frontend/src/pages/plan-achat/`).
- Préparation d'une commande : unités kg/bobine/palette, conteneurs
  (`frontend/src/pages/plan-achat/calculPreparation.ts`, `conteneur.ts`,
  `TablePreparation.tsx`, `useSaisiePreparation.ts`).
- Commandes : brouillon, envoi, approbation (direction), confirmation des prix,
  modification après envoi, soldée (`services/commandes.py`, `commandes_socle.py`,
  `approbation.py`, `commandes_gestes.py`, `api/commandes/`).
- Bon de commande fournisseur : A4, anglais, sans prix, papier à en-tête
  (`services/bon_fournisseur.py`, `api/commandes/routes_documents.py`,
  `api/documents/`).
- Fournisseurs (`services/fournisseurs.py`, `api/fournisseurs/`).
- Droits `alimentation` (aucun prix/montant/cours) : `securite/prix.py`, `droits.py`.

## Conclusion

**Aucun défaut CERTAIN trouvé dans le domaine ACHATS.** Les règles vérifiées sont
respectées et cohérentes avec les décisions (DECISIONS §5 A1–A25, U2, R14r, V3, F10→version).
`make verifier` reste vert (aucune modification de code ; ce document seul est ajouté).

Ce qui a été vérifié et tient :

| Thème | Preuve |
|---|---|
| Prix catalogue kg ↔ ml × densité | `calcul/modele/referentiels.prix_kg` (÷ densité si `ml`), `commandes_socle.prix_catalogue_kg`, `commandes._prix_au_kg` (confirmé au mètre ÷ densité) et `_au_catalogue` (retour au catalogue × densité) : aller-retour exact. Recalcul SQL : Cuir 0,074 USD/ml ÷ 0,014 = 5,286 USD/kg ; Bande 2,5 USD/kg (densité 0,005). |
| Garde-fou d'approbation (A8) | `approbation.controler_montant` : brouillon soumis modifié → brouillon ; bon parti qui franchit le seuil et dépasse sa version de référence → « À approuver » (n° gardé) ; baisse ne repasse jamais ; prix confirmé +5 % max toléré ; mesure dans la devise du bon, au cours figé. Recalcul sur BC-2026-0002 : estimé envoi 450 172,80 MAD, prix confirmé 3,0 USD = +3,4 % < 5 % → pas de ré-approbation. Cohérent. |
| Version périmée → 409 | Tous les gestes d'écriture (modifier, supprimer, envoyer, approuver, renvoyer, prix, expédition, solder, rouvrir) passent `version` à `commandes_socle.verifier` → `audit.verifier_version`. |
| Période close (V3) | `commandes_socle.numeroter` appelle `periode.date_permise` à l'envoi/approbation ; un brouillon (sans effet, sans date d'effet) n'est pas concerné. |
| Excédent toléré à la réception (R14r) | `receptions_blocages._excedent` : `total ≤ reste + quantité_ligne × excédent` ; par ligne de bon, tous lots sommés ; un bon soldé n'en reçoit pas plus. |
| Conteneur « complété ne redemande plus un conteneur entier » (fix b25693a) | `calculPreparation.palettesDe` compte le nombre tapé en palettes (sans repasser par les kilos) ; `placeRestante` plein à `TOLERANCE_PALETTE=0,05` près. Tests `calculPreparation.test.ts` couvrent 18,0000004 → 1 conteneur, 0 libre. |
| Bon fournisseur sans prix, anglais, A4, en-tête | `bon_fournisseur` ne porte aucun prix/montant/devise ; colonnes No./Item/Description/Packing/Qty/Total weight (kg)/Length (m, indicative) ; remarques à part. Routes 164–166 `droit(D, A)`. |
| Alimentation ne voit aucun prix | Toutes les routes achats sont `droit(D, A)` (alimentation n'y accède pas). La liste fournisseurs (`droit(*C)`) rend `FournisseurResume` (nom, pays, actif) pour l'alimentation (`peut(qui,"voir_prix")`). Filtre générique `securite/prix.sans_prix` sur **toute** réponse JSON (RouteSansPrix) pour les rôles hors direction/achats. Essai `test_prix_masques` : balayage de toutes les routes GET en rôle alimentation ET administrateur, aucune clé monétaire porteuse de valeur. |
| Grands tableaux de lignes lisibles | Fiche (`VoletLignes`) et préparation (`TablePreparation`) : `DataTable hauteur="fenetre"` (défilement dans le cadre, en-tête fixe, « Agrandir ») — fix cfa7a3c/983bd04. |

## Constats (PROBABLE / QUESTION — non corrigés)

| # | Gravité | Classe | Constat | Preuve | Action |
|---|---|---|---|---|---|
| P1 | faible | PROBABLE | `bon_fournisseur.contenu` calcule `metres = kg / densite` à partir du champ `densite` en base, et non du drapeau `lineaire` du rôle (contrairement à `calcul/modele/referentiels.kg_par_ml` qui lit `ROLES_LINEAIRES`). Dans le catalogue réel seuls les rôles au mètre (Cuir, Ruban) portent une densité, donc le comportement est juste aujourd'hui ; mais une matière d'un rôle non linéaire à qui l'on donnerait une densité afficherait à tort la colonne « Length (m) » du bon fournisseur. | SQL : densité > 0 uniquement sur Cuir et Bande (rôle Ruban), tous deux linéaires. | Non corrigé (non reproductible sur les vraies données ; cosmétique). À harmoniser sur `lineaire` lors d'un prochain lot. |
| P2 | moyenne | QUESTION | À la confirmation des prix (`VoletPrix`), l'écran envoie toujours `unite:'kg'` et demande à l'acheteur de **diviser lui-même** un prix au mètre par la densité (texte : « au kilo … son prix au mètre ÷ la densité »). La décision **U2** prévoit qu'« un prix au mètre se lit aussi au mètre là où l'on confirme un prix ». Le serveur accepte déjà `unite:'ml'` (`PrixLigne`), l'écran ne s'en sert jamais. Ne concerne que les matières au mètre (aujourd'hui le seul Cuir, lui-même en question ouverte Q1). | `VoletPrix.tsx:56` (`unite:'kg'`), `:140-141`, `:195-198`. | Non corrigé (choix métier à trancher). Voir QUESTION 1. |
| P3 | très faible | PROBABLE | Le filtre de masquage des prix (`CLES_MONETAIRES`) ne couvre pas un motif générique `taux*` : le champ `taux_du_jour` (cours de change, `CommandeResume`) et assimilés échappent au masquage automatique. Sans fuite aujourd'hui (confiné aux routes `droit(D, A)`). Volontaire : ajouter `taux*` masquerait `taux_perte`, nécessaire à l'alimentation (production). | `api/commandes/schemas.py:153` ; `securite/prix.py:31` ; `taux_du_jour` absent de `MONETAIRES`. | Non corrigé. La protection repose, pour les cours nommés `taux_*`, sur la garde de route et non sur le filtre : à garder en tête (ne pas ouvrir une route portant un `taux_*` de change à l'alimentation). |

## Essais

Aucun essai ajouté (aucune correction CERTAINE). La couverture existante du domaine
(commande, approbation, bon fournisseur, préparation, réception) est verte.

## QUESTIONS MÉTIER pour Mohamed

1. **Confirmer un prix d'une matière facturée au mètre (le cuir).** Aujourd'hui, l'écran
   vous demande de diviser vous-même le prix au mètre par la densité et de saisir le prix
   au kilo. Voulez-vous plutôt saisir le prix **au mètre** directement, le logiciel faisant
   la division (c'est ce que prévoyait la décision du 8/10) ? Exemple : le fournisseur
   annonce 0,074 USD/ml → vous tapez 0,074 « au mètre », le logiciel enregistre 5,29 USD/kg.

2. **Excédent toléré à la réception.** La tolérance s'applique en pourcentage de la
   quantité **de la ligne du bon**, pas du reste à livrer. Exemple : ligne de 1 000 kg,
   excédent toléré 5 % → on accepte jusqu'à 1 050 kg reçus au total sur cette ligne, même
   après plusieurs camions. Est-ce bien le comportement voulu ?

3. **Écart « critique » quand on commande moins que la suggestion.** Dans la préparation,
   commander **moins** de 10 % sous la suggestion affiche un badge rouge « critique », et
   **plus** de 10 % au-dessus un badge orange « attention ». Exemple : suggéré 1 000 kg,
   commandé 850 kg → badge rouge. Voulez-vous garder le rouge pour un « moins » décidé
   exprès par l'acheteuse, ou un ton plus doux ?
