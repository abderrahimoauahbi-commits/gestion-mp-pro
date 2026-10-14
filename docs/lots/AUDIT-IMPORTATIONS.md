# Audit IMPORTATIONS & COÛT DE REVIENT (14/10/2026)

Branche `audit-importations` (depuis main 1443f33). **Aucune correction** : rien de CERTAIN n'a
été trouvé dans le périmètre. Ce document décrit les constats, les preuves et les questions.

## Méthode suivie
- Base d'essai `gestion_mp_pro_importations_essai`, copie `pg_dump -Fc` des vraies données
  (`gestion_mp_pro`, révision 0008 = tête de la branche, aucun `alembic upgrade` nécessaire).
  3 dossiers, 4 liens `dossier_facture`, 6 marchandises, 8 frais. **Base supprimée à la fin.**
- Coût de revient recalculé par un autre chemin (SQL pur, puis moteur sur cas synthétiques) et
  comparé à l'écran (routes 187/189).
- Scénarios joués sur la copie (retrait/ré-ajout d'une facture, changement de cours, poste de
  nature « droits »), puis `rollback`.
- Vérificateur indépendant `essais/verification_chiffres.py` passé sur la copie : **0 écart**
  (2854 vérifications ; familles coût/TVA/répartition/C29/C36 toutes vertes).
- Essais existants verts : 197 essais serveur d'importation + 14 essais d'écran (taux, factures).

## Ce qui est vérifié JUSTE (aucun défaut)

| Sujet | Preuve |
|---|---|
| Coût de revient des 3 dossiers (dont 02/26 à **2 factures**) | SQL pur = écran au centime (revient 5 388 914,76 / 5 568 089,68 / 459 360,00 ; décaissé idem + TVA) |
| Plusieurs factures : coût **sans doublon** | revient dossier = Σ des 4 marchandises une seule fois ; `factures_vives`/liaison `liberee_le IS NULL` partout (moteur, chargeur, C36) |
| C36 **facture par facture** | mapping facture→marchandise par réception juste ; 2 factures sans montant → « non saisi » (pas « conforme ») |
| Échéancier : **une échéance de marchandise par facture** | dossier 02/26 : 2 échéances estimées (329 495,04 et 195 796,44) + 3 frais, sans doublon |
| Annulation **libère** les factures | `liberee_le` posé sur toutes les vives, trace gardée, marchandises détachées |
| Retrait d'une facture / détachement d'une réception | marchandise sort, parts figées effacées (`sans_parts_sur`), frais redistribués, refus si un frais vise sa marchandise |
| Taux (%) : montant **jamais recalculé** au serveur | cours 10,05→12 (base 4,49 M→5,36 M) : montant du frais à taux inchangé (898 059,96). Aucun code serveur ne lit `dossier_frais.taux` pour un montant (seuls affichage/export/journal) |
| Taux : pré-remplissage (base = valeur en douane ; TVA = douane+droits+TPI) et **colonne Taux** | `tauxFrais.ts`, colonne `taux` dans `VoletFrais` (`hauteur="fenetre"`, pas de défilement caché) et dans l'export (format `0.00##%` avant « Montant MAD ») |
| Cours payé → contre-valeur MAD ; répartition valeur/poids/une marchandise ; **TVA récupérable hors coût** | cas synthétique moteur = calcul à la main (FRET à la valeur, TRANSIT au poids, PORT direct, AUTRE figé, TVA récupérable exclue du coût) |
| Exports Excel (route 205) | classeur généré sans erreur, colonnes Taux / Montant MAD / Factures présentes |
| Rôle `alimentation` **sans accès** aux importations | matrice des droits : **403** sur toutes les routes `/api/dossiers*`, `/api/analyse/revient*`, `/api/export/dossiers`, `/api/export/revient` (test `test_matrice_droits.py` vert) |

## Constat PROBABLE (non corrigé — décision métier)

**P-IMP-1 — La « TVA attendue », les « droits attendus » et la « valeur en douane » sont câblés
sur les codes DD / TPI / TVA / FRET / ASSUR, et ignorent les champs `nature` et
`entre_valeur_douane` du référentiel des postes.**

- `calcul/importations.py` : `POSTES_VALEUR_EN_DOUANE = ("FRET","ASSUR")`, droits = poste de
  code `"DD"`, TPI = `"TPI"`, TVA de la douane = `"TVA"` (codes en dur). Le référentiel des
  postes, lui, porte `nature` (droits/tpi/tva/fret/assurance/autre) et `entre_valeur_douane`, et
  la route `POST /postes-frais` (direction) permet de **créer un poste non-système** avec une de
  ces natures.
- L'écran (base du taux, `tauxFrais.ts`) et le vérificateur indépendant (`verif_importations.py`)
  s'appuient, eux, sur `nature` / `entre_valeur_douane`.
- **Preuve** (scénario, copie) : ajout d'un frais de 10 000 MAD avec un poste neuf de
  `nature='droits'` (code `DDX`) au dossier 03/26 → `droits_mad` reste 9 360 et `tva_attendue_mad`
  reste 92 097 ; la formule documentaire (droits par nature) donne 94 097. Le serveur **ignore**
  ce poste dans la TVA attendue et le contrôle des droits.
- **Portée** : seuls les repères de contrôle (TVA attendue, droits attendus, C29, C36-droits,
  alertes « TVA ≠ attendue » / « Droits ≠ attendus ») sont concernés. **Le coût de revient
  lui-même reste juste** (il somme tous les frais selon le seul `recuperable`). Sur les données
  réelles actuelles, les 5 postes système sont alignés code↔nature↔drapeau, donc le vérificateur
  est vert — le défaut n'apparaît qu'après création d'un poste de nature spéciale. D'où PROBABLE,
  non CERTAIN.
- **Non corrigé** : aligner le moteur sur `nature`/`entre_valeur_douane` changerait un calcul
  « prouvé à l'identique de Gestion MP » → décision de Mohamed (voir questions).

## QUESTIONS MÉTIER pour Mohamed

1. **Postes de frais « sur mesure » et TVA/droits attendus.** Si vous créez un poste de frais de
   nature « droits » (ou « tpi », « fret »…) en plus des 5 postes système, voulez-vous qu'il
   compte dans la « TVA attendue » et les « droits attendus » du dossier ? Aujourd'hui le serveur
   ne regarde que les postes DD/TPI/TVA/FRET/ASSUR : un poste « Droits additionnels » de 10 000 MAD
   serait ignoré dans ces repères (le coût de revient, lui, le compte bien). Faut-il que ces
   repères suivent la *nature* du poste, ou bien ces 5 rôles doivent-ils rester réservés aux
   postes système (et interdire d'en créer d'autres de ces natures) ?
2. **Retrait puis ré-ajout d'une facture : le cours payé revient au cours du bon.** Quand on
   retire une facture d'un dossier puis qu'on la ré-ajoute (ou qu'on détache puis rattache sa
   réception), sa marchandise rentre « comme à l'ouverture », au **cours figé du bon**. Exemple :
   une marchandise où vous aviez saisi 10,05 (cours payé banque) revient à 10,00 (cours du bon),
   soit −22 339,80 MAD de valeur en douane sur le dossier 01/26 — silencieusement. Est-ce bien
   voulu, ou faut-il garder/retrouver le dernier cours payé saisi ?
