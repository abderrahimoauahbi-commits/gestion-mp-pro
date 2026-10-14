# Audit RÉFÉRENTIELS / PRODUCTION-BESOINS / PILOTAGE / COMPTES / SOCLE (14/10/2026)

Branche `audit-referentiels` (depuis `main` 1443f33). Base d'audit : copie des vraies données
(`pg_dump -Fc gestion_mp_pro | pg_restore -d gestion_mp_pro_referentiels_essai`, à la révision
0008). Aucune écriture dans `gestion_mp_pro`, `gestion_mp`, ni sur 8050/8030.

**Résultat : aucun défaut CERTAIN trouvé dans le périmètre.** Les corrections récentes sont en
place et non régressées ; les garanties fortes (droits, prix masqués, calcul MRP, vérificateur
indépendant) tiennent sur les vraies données. Pas de correction de code (donc pas de révision
Alembic 0012). Quelques QUESTIONS MÉTIER pour Mohamed à la fin.

## Ce qui a été vérifié, et comment

| # | Vérification | Méthode (autre chemin) | Résultat |
|---|---|---|---|
| 1 | Matrice des droits sans écart | `python -m gestion_mp_pro.securite matrice` puis `diff` avec `tests/matrice_droits.csv` | **0 écart** (257 routes) |
| 2 | Rôle `alimentation` sans aucun prix | balayage de **toutes** les routes GET en alimentation ET administrateur, sur les vraies données peuplées (nomenclature, qualités, stock, besoins, lots…) | **0 fuite** (41 réponses JSON alimentation, 18 administrateur) |
| 3 | Besoins MRP corrects | recompute indépendant en SQL brut (qualite, qualite_saison, recette, qualite_poids, matiere, role_nomenclature) comparé à `calcul.besoins.besoins_mensuels` | **0 écart** sur 89 références |
| 4 | Plan glissant correct | recompute indépendant (base × saisonnalité, arrondi) comparé à `calcul.plan.plan_mensuel` | **0 écart** sur 18 qualités |
| 5 | Vérificateur indépendant | `essais/verification_chiffres.py --dates 13` (n'importe rien de `gestion_mp_pro`, SQL + HTTP) sur la copie | **0 écart / 17 206 vérifications** (dont nomenclature kg/m² ×957, C01 ×19, cockpit, bilan) |
| 6 | `make verifier` | serveur (pytest + alembic), écran (eslint/tsc/vitest), outils | **vert** (3 cibles, exit 0) |
| 7 | Impression sans date/heure/adresse | lecture des gabarits : `@page { margin: 0 }` dans `_papier_a_en_tete.html` et `etiquettes.html` ; bon de commande, bilan, feuille de comptage héritent tous du papier à en-tête ; marges refaites par la tête/le pied du tableau | conforme |
| 8 | Nombres kg ≤ 2 décimales | `lib/format.ts` : `kg()` = `nombre(v, 0, 2)` (zéros inutiles enlevés), généralisé | conforme |

## Corrections récentes contrôlées (non régressées)

- **« La base m²/mois ne change jamais d'elle-même »** (c51e57b) : `plan.ts::depuisM2` ne touche
  que le coefficient du mois (`m² ÷ base`, 6 déc.) ; la base n'est modifiée que saisie ; sans base
  (≤ 0) les m² sont grisés (`SANS_BASE`). Cohérent avec la décision du 12/10.
- **« Besoins par qualité : le filtre réduit la quantité »** (dbe131c) : `OngletBesoins.tsx::parQualite`
  réduit `kg`, `total`, `retenu`, `total_retenu` à la qualité choisie ; le stock reste au niveau
  matière. Le backend (`_detail_par_qualite`) applique le **même taux de perte** (×1,02) que le total
  matière, donc `Σ q.kg[i] = x.kg[i]` et la ventilation du retenu est cohérente. Pas de bug.
- **« Production & besoins déplacé sous Référentiels »** (ff392d0, 4d82fe1) : menu, essai, notice suivis.
- **Unités de titrage, référentiel gérable** (F29, révision 0008) : sur les vraies données,
  `unites_titrage.actives` rend `Dtex, Deniers, Nm, Tex, Nec, lbs, Cm` ; `decomposer('… 20 lbs')`
  lit « lbs », `decomposer('… 150 Den')` lit « Deniers ». Renommer/supprimer une unité employée
  refusés, casse corrigeable : testé (`test_unites_titrage.py`).
- **Fil monté (U8)** : la confirmation de montage de PRO dit le bon texte (« … il compte dans le
  stock global, sa valeur, le disponible et le projeté »), **pas** l'ancien « ces kilos sont déjà
  sortis et consommés » signalé comme à ne pas reprendre (DECISIONS §16 n° 1).

## Limite connue

Le recompute indépendant du plan glissant a été fait avec `croissance_annuelle = 0` (valeur des
vraies données) : le facteur `(1 + croissance)^(mois/12)` et l'ancre `depuis` n'ont pas été
re-vérifiés par un second chemin ici (ils restent couverts par les essais unitaires du moteur).

## QUESTIONS MÉTIER pour Mohamed

1. **Franges (reprise de Q2, toujours d'actualité)** : 6 qualités (8M, 8S, LP, MN, MP, SH) portent
   un poids au rôle **Franges** mais **aucune matière Franges** n'existe → le rôle somme 0 % au lieu
   de 100 %, donc contrôle C01 bloquant sur ces 6 qualités. Faut-il **créer la matière Franges**
   (densité obligatoire) ou **mettre le poids Franges à 0** pour ces qualités ? (Exemple : 8M
   demande 0,8 ml/m² de Franges sans fil en face.)
2. **Unité « Cm » dans les titrages** : la base en service porte une unité de titrage **« Cm »**
   (libellé vide), employée par 7 titrages (100, 35, 45, 50, 65, 80 en « Cm » et 140 en « cm » —
   casse mélangée). Le titrage mesure normalement la finesse du fil (Dtex, Nm…) ; « Cm » ressemble
   à une largeur en centimètres saisie dans le champ titrage lors de la reprise. Est-ce une vraie
   unité à garder (alors lui donner un libellé et unifier la casse « Cm »/« cm ») ou une donnée à
   corriger ?
3. **Prix bande/cuir au kilo ou au mètre (reprise de Q1)** : les prix catalogue (bande 2,5 ; cuir
   0,074) sont lus **au kilo**. À confirmer sur une facture SOFIA TEXTILE, sinon passer ces fiches
   « au mètre » (densité connue).
