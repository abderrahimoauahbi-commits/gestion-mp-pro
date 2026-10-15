# Lot FOND-DE-LOT — les fonds de lot et leur mise au rebut

Branche `fond-de-lot-rebut` (depuis main 6f6b82a, fusion de main a00150f avant remise). Révision
Alembic **0009** (réservée par le coordinateur). Route **258** (`POST /lots/{id}/rebut`).

## La décision (Mohamed, 15 octobre 2026 — DECISIONS U22, O14)

« À partir d'un certain poids, un fond de lot doit être mis au rebut : il ne sert à rien. En
dessous d'environ **100 g**, un fond de lot est du rebut. » Contexte : le stress de trois ans
(`STRESS-3-ANS.md`, A8) a montré la proposition FIFO de « Envoyer aux machines » offrant d'abord
un lot dont il ne restait qu'un fond (3,151 kg, moins qu'une bobine) ; 497 fois le même lot,
539 brouillons abandonnés. Le seuil doit rester **réglable** par la direction, 0 = désactivé.

## Ce qui est fait

1. **Réglage** `seuil_rebut` « Seuil de rebut » (famille Stock et inventaire, kg, défaut **0,1**,
   bornes 0–1000, 0 = désactivé) : clé ajoutée à la liste fermée (CHECK `ck_parametre_cle_connue`,
   58 clés), semée `0.1` ; historique et journal comme tout réglage (routes 23–25). Lu par
   `services/fonds_de_lot.seuil`.
2. **Motif d'ajustement « Rebut »** semé par 0009 (après « Correction de saisie ») ; recréé par
   `services/operations/rebut.motif_rebut` s'il manquait.
3. **La règle** (`services/fonds_de_lot`) : un solde (lot, magasin) `0 < q < seuil` est un *fond
   de lot*. Il **ne change aucun chiffre** du moteur (stock, valeur, disponible, projeté, bilan).
   - `lots.lister` (route 107) : `LotSolde.fond_de_lot`, `fond_de_lot_kg`, `magasins[].fond_de_lot`,
     et la `version` du lot (1 + ses lignes de journal, en une requête) ;
   - `lots_lecture.disponibles` (111) : `LotDisponible.fond_de_lot` ;
   - `ordres/proposition` (134) : `_servir` **saute** un fond de lot (le lot suivant est servi), le
     garde dans `disponibles` marqué (`LotPropose.fond_de_lot`), et le nomme dans
     `Proposition.fonds_de_lot` (« POIL — lot HT-… : 56 g dans Morocco, fond de lot (< 100 g),
     laissé en stock (à mettre au rebut). ») ;
   - `GET /contexte` porte `seuil_rebut` : l'écran écrit la marque « fond de lot (< 100 g) ».
4. **Le geste** `POST /lots/{id}/rebut` `{magasin_id, version, motif}` (route 258, C) →
   `services/operations/rebut.mettre_au_rebut` : un **ajustement en moins au motif « Rebut »** sur
   tout le reste du lot dans ce magasin, créé et validé dans une transaction par
   `gestes.creer(valider=True, droit_tranche=True)` (le droit du type est tranché par le rebut :
   l'alimentation, qui ne fait pas d'ajustement, peut mettre au rebut un fond de lot hors
   quarantaine) ; numéro `AJU-…`, journal de l'opération et ligne « rebut fond de lot » sur le lot
   (sa version avance) ; valorisation au coût moyen comme tout ajustement ; période close,
   inventaire en cours, solde insuffisant : les refus habituels de `stock.ecrire`. Refus :
   version périmée → 409 `conflit_version` ; reste ≥ seuil hors direction → 409
   `pas_un_fond_de_lot` « Ce n'est pas un fond de lot : … » ; direction au-dessus du seuil sans
   motif (5 caractères) → 422 `motif_requis` ; alimentation sur une quarantaine → 403.
   Le fil monté sur un métier n'est pas en magasin : pas de rebut depuis le montage.
5. **Écrans** :
   - Stock › Lots : KPI « Fonds de lot » (N, « X kg à mettre au rebut (< 100 g) », pose
     `?fonds=1`), case « Fonds de lot seulement », badge « fond de lot (< 100 g) » sur le lot et
     « fond » sur le solde du magasin, « Mettre au rebut » par magasin sur la ligne (direction,
     achats ; `Confirmer` sur place) ;
   - Fiche de lot (bureau) : badge dans le sous-titre et sur le solde ; carte « Fond de lot » avec
     « Mettre au rebut » par magasin (direction, achats) ; la direction voit aussi le geste sur un
     solde au-dessus du seuil, avec le motif exigé dans la confirmation ;
   - Atelier : « Stock des fils » (badge « fond de lot » sur la carte du lot), fiche du lot (badge,
     « Mettre au rebut (56 g, Morocco) » hors quarantaine, grisé avec la raison sur une
     quarantaine, aucun montant), « Envoyer aux machines » (note « Fonds de lot laissés en stock
     (pas proposés) : … », « + Prendre aussi un autre lot… » dit « · fond de lot ») ;
   - Sorties (bureau) : la même note et la même mention dans « + un autre lot… » ;
   - Réglages › Paramètres : « Seuil de rebut » dans Stock et inventaire (écran générique) ;
   - aide.json (écran Stock, fiche de lot, atelier, réglages ; formule `fonds_de_lot`) → NOTICE.
6. **Docs** : DECISIONS U22, O14 ; REGLAGES § 3.6 (réglage PRO) ; CALCULS § 6 (règle nouvelle,
   aucun chiffre du moteur ne change) ; API-PRO (3, 107, 111, 134, 258, § 1.3) ; ECRANS-PRO ;
   MODELE-DONNEES § 3.2.12 ; STRESS-3-ANS A8 (tranché) ; matrice des droits régénérée.

## Ce qui n'est pas fait, et pourquoi

- **Pas de ligne « rebuts » dans le bilan du mois** : le bilan n'a pas de familles d'ajustement
  (une seule ligne « ajustements » par type de mouvement, `calcul/suivi_bilan`) ; le rebut y
  entre, comme demandé « sinon dans les ajustements ». L'essai le prouve (−0,056 kg).
- **Pas de contrôle C39 « fonds de lot »** : les 38 contrôles sont une liste gelée (DECISIONS T11)
  et aucune famille ne convient ; l'indicateur « N fonds de lot, X kg » vit dans l'écran Stock.
- **Pas de rebut depuis le montage** (décision : le fil monté n'est pas concerné).

## Essais

- `backend/tests/test_fonds_de_lot.py` (12) : seuil et marque ; la liste marque les fonds (par
  magasin, quarantaine comprise) et dit la version ; la proposition FIFO saute un fond, le nomme,
  le garde dans `disponibles`, et redevient comme avant à seuil 0 ; 3,151 kg restent proposés ;
  le rebut écrit un `AJU-…` « Rebut » validé, vide le lot, journalise, avance la version, se voit
  dans la traçabilité, et n'a plus rien à sortir la seconde fois ; au-dessus du seuil : achats et
  alimentation refusés (409), direction sans motif (422), avec motif (201) ; seuil désactivé ;
  quarantaine (403 atelier, permis achats) ; alimentation hors quarantaine ; période close,
  inventaire en cours, version périmée, lot/magasin inconnus ; fil sorti vers un métier non
  concerné ; API : l'alimentation met au rebut sans qu'aucune clé monétaire porte une valeur, le
  lot quitte la liste, la fiche montre l'écriture, les mouvements valorisés la comptent à 20 MAD/kg
  (−1,12 MAD), le bilan du mois compte −0,056 kg d'ajustements ; refus 409/422/403 par l'API.
- `test_reglages.py` : 58 clés ; `matrice_droits.csv` régénérée (route 258 : C).
- Écran : `pages/stock/fonds.test.ts` (marque, poids, compte, droits, fonds laissés) ;
  `Stock.test.tsx` (achats : badge, KPI, « Mettre au rebut » envoie `{magasin_id, version, motif}` ;
  alimentation : badge sans le geste, case « Fonds de lot seulement ») ; atelier `Lots.test.tsx`
  (fiche d'un fond de lot : badge, « Mettre au rebut (56 g, …) » envoie la version, aucun prix).

## Vérification à l'écran (copie de `gestion_mp_pro_stress_essai`, migrée 0009)

Voir le rapport de remise : 10 fonds de lot sous 100 g (0,391 kg) dans la base « 3 ans », vus
dans Stock › Lots (1 440 × 900) et dans « Stock des fils » (375 × 812) ; un rebut joué au bureau
et un au téléphone sur la copie.

## Parité

La parité (`make parite`) ne compare pas la proposition de sortie ; aucun chiffre du moteur ne
change (le fond reste compté et valorisé). Les champs nouveaux (`fond_de_lot`, `version`,
`fonds_de_lot`, `seuil_rebut`) sont des ajouts de PRO, pas des champs de Gestion MP renommés.
