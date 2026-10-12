# Livraison partielle — les lignes qu'un camion n'a pas apportées

Correction demandée par Mohamed le 12/10/2026 (défaut constaté en service). Branche
`lot-livraison-partielle`.

## Le défaut

Une commande arrive en plusieurs camions. Choisir le bon dans la saisie d'une réception reprend
**toutes** ses lignes qui restent à livrer (`useSaisieReception.ts`, `.filter((l) => l.reste > 0)`).
Mohamed a pesé la seule ligne apportée ; les 23 autres sont restées vides. La validation était
refusée pour chacune (« la pesée est à zéro. La saisir, ou marquer la ligne « refusé » »,
« le numéro de lot manque ») : retirer 23 lignes une à une n'est pas raisonnable, et « refusé »
est faux (rien n'a été refusé : ce n'était pas dans ce camion).

## La règle

Une **ligne non livrée** est une ligne de réception rattachée à une ligne de bon
(`commande_ligne_id` non nul), de qualité autre que « refusé », **entièrement vide** :
`quantite_bl = 0`, `quantite_pesee = 0`, `nb_palettes = 0`, `nb_bobines = 0`,
`bobines_en_plus = 0`, `lot_numero` vide et `lot_interne` faux (les observations ne comptent pas).

1. Elle ne produit **aucun blocage** (date mise à part, qui est celle de la réception) : ni
   pesée, ni lot, ni magasin, ni excédent, ni inventaire en cours, ni problème du bon — côté
   serveur (`blocages`, donc la fiche, `actions.valider`, la liste, « À valider ») comme dans
   l'aperçu de la saisie (`blocagesSaisie`). Elle ne produit pas non plus d'avertissement (bon
   soldé, approbation en attente, matière désactivée) : elle ne sera pas reçue.
2. À la **validation**, le serveur la retire de la réception, dans la même transaction, avant de
   créer lots et mouvements. Journal : une ligne « lignes non livrées retirées » (détail
   `« brouillon n° 12 · 2 ligne(s) non livrée(s) par ce camion, toujours due(s) sur BC-… : réf, réf »`,
   `avant` = la photo de chaque ligne retirée), et le détail de « validation réception » se
   complète de `« · N ligne(s) non livrée(s) retirée(s), dues sur le bon »`. Rien n'est reçu pour
   elles : la ligne de bon garde son reste à livrer, le bon reste ouvert (envoyé/confirmé,
   livraison « en cours » ou « partiel retard ») et se reçoit au camion suivant.
3. Si **toutes** les lignes de la réception sont non livrées, la validation est refusée
   (422 `quantite_invalide`) et le brouillon l'annonce : **« Rien n'est pesé : saisir ce que le
   camion a apporté (les lignes laissées vides restent dues sur le bon). »** — phrase unique,
   `RIEN_N_EST_PESE` côté serveur (`services/receptions_non_livrees.py`) et côté écran
   (`calculSaisie.ts`), comparée mot pour mot dans les deux suites d'essais. Une réception dont
   il ne reste, après retrait, que des lignes refusées se valide comme avant (« tout refusé »).
4. La **question** posée avant le « Oui » de la validation (`calculFiche.ts`
   `questionValidation`) le dit : « 23 lignes non livrées par ce camion seront retirées : elles
   restent dues sur le bon BC-2026-0001. » (singulier : « 1 ligne … sera retirée : elle reste
   due … » ; plusieurs bons : « sur les bons X, Y »). Les comptes de la question (en stock, en
   quarantaine, refusées, écarts) ne comptent plus les lignes non livrées. La fiche serveur ne
   rédige pas cette question (rien à changer côté serveur). Dans la saisie, une note discrète :
   « N lignes vides : non livrées par ce camion, elles resteront dues sur le bon. »
5. Une ligne **hors bon** vide, ou une ligne de bon **partiellement remplie** (BL saisi sans
   pesée, pesée sans lot, palettes seules, « Lot interne » coché…), garde les blocages d'avant,
   mot pour mot.

Le mode d'emploi de la saisie (`aide.json`, `docs/NOTICE.md` régénérée) dit désormais : laisser
vide une ligne absente du camion, ou la retirer.

## Ce qui a été vérifié ailleurs (rien à changer)

- **C08 « écart de pesée »** (`calcul/controles/achats.py`) : une ligne pas encore pesée d'une
  réception en cours est déjà ignorée ; une fois validée, la ligne non livrée n'existe plus.
- **Écart de pesée, « livraison partielle sans BL »** (R13r, `ecart_de_pesee`,
  `attenduDe`/`ecartDe`) : sans BL ni pesée, aucun attendu, aucun écart.
- **Excédent** : une ligne vide n'apporte rien (0 kg) au total d'une ligne de bon.
- **OTIF / complétude** (`calcul/fournisseurs.py`) : ne lit que les réceptions validées et
  juge la complétude sur les **lignes du bon** (reste dû) — la ligne retirée n'y entre pas
  comme ligne de réception. Le premier camion d'un bon livré en deux fois reste « pas complet »
  (in full = 0) : c'est la définition héritée de l'OTIF (le fournisseur n'a pas tout livré),
  identique à ce que donnait le retrait des lignes à la main ; ce n'est pas un écart de
  réception.
- **Dossiers d'importation** : un dossier ne prend que les lignes des réceptions validées de sa
  facture ; les lignes retirées n'y paraissent pas. Un dossier par facture.
- L'**archive des pesées** montre les lignes d'un brouillon telles qu'elles sont jusqu'à la
  validation (0 kg, sans écart, non comptées hors tolérance) ; elles disparaissent à la
  validation. Laissé tel quel.

## Écart à une règle héritée (à reporter par le coordinateur)

- **X-RCP-B5 / B6 / B8** (REGLES § 3.6) : « ligne non refusée à pesée ≤ 0 », « sans numéro de
  lot », « conforme sans magasin » bloquaient **toute** ligne non refusée. Désormais une ligne de
  bon entièrement vide en est exemptée (décision de Mohamed ci-dessus). Les messages restent mot
  pour mot pour toutes les autres lignes.
- **X-RCP-B2 / B3 / B4** (problème du bon, excédent, inventaire en cours) et **A-RCP-01/02**,
  A-11 : ne s'appliquent plus à une ligne non livrée.
- **R-RCP-20 / R-RCP-25** (validation) : un pas de plus entre les blocages et l'écriture
  (retrait des lignes non livrées, journalisé) ; nouveau refus `RIEN_N_EST_PESE`.
- Aucune décision de DECISIONS.md n'est contredite : R1r (« une arrivée regroupe une ou
  plusieurs commandes, entières ou partielles ») et R13r (« une livraison partielle sans BL
  n'est pas un écart ») vont dans le même sens.
- ECRANS-PRO § 4.16 (liste des blocages serveur) : la mention des lignes non livrées et du refus
  « Rien n'est pesé … » y est ajoutée dans cette branche. Le tableau § 2.1 suit aussi le menu de
  main (« Production & besoins » sous Référentiels, commit séparé : l'essai du menu et la notice
  étaient rouges sur main depuis ff392d0).

## Fichiers touchés

- `backend/gestion_mp_pro/services/receptions_non_livrees.py` (nouveau) : `non_livree`,
  `tout_est_vide`, `RIEN_N_EST_PESE`, `retirer`.
- `backend/gestion_mp_pro/services/receptions_blocages.py` : lignes non livrées sautées
  (blocages, avertissements) ; « Rien n'est pesé » quand toutes le sont.
- `backend/gestion_mp_pro/services/receptions.py` : `_controler` (blocages puis retrait) appelé
  par `valider` ; détail du journal de validation.
- `frontend/src/pages/receptions/calculSaisie.ts` : `RIEN_N_EST_PESE`, `nonLivree`,
  `noteNonLivrees`, `annonceNonLivrees` ; `blocagesSaisie` les ignore.
- `frontend/src/pages/receptions/calculFiche.ts` : `questionValidation` annonce le retrait.
- `frontend/src/pages/receptions/SaisieReception.tsx` : la note discrète.
- `frontend/src/aide.json`, `docs/NOTICE.md` (régénérée) : le mode d'emploi.
- Aucune route, aucun schéma, aucune colonne, aucune révision Alembic : matrice et types
  inchangés.

## Essais

- `backend/tests/test_receptions_livraison_partielle.py` (5 essais) :
  - le scénario de Mohamed : bon de 3 lignes parti (fournisseur étranger) ; réception 1 :
    ligne 1 pesée (lot, magasin), lignes 2-3 vides, facture F1 dans le brouillon → aucun
    blocage, validée, 2-3 retirées (journal vérifié), bon partiel avec 600 et 400 kg à livrer
    exactement ; réception 2 : seules 2-3 restent dues, pesées, validée sans facture → bon
    soldé, livré ; facture F2 complétée **après** validation (route facture) ; dossier ouvert
    depuis F1 (ligne 1 seule), droits de douane ajoutés ; second dossier pour F2 (lignes 2-3) ;
  - toutes les lignes vides → refus 422 « Rien n'est pesé … », annoncé sur le brouillon et dans
    `actions.valider`, rien retiré, bon entier ;
  - ligne de bon à moitié remplie (BL sans pesée ; pesée sans lot) → blocages mot pour mot ;
  - ligne hors bon vide → blocages mot pour mot (à côté d'une ligne de bon pesée) ;
  - une ligne refusée et une ligne vide → validée « tout refusé », la vide retirée, bon entier.
- `frontend/src/pages/receptions/calculSaisie.test.ts` : aperçu sans blocage pour les lignes non
  livrées, note, « Rien n'est pesé » ; lignes à moitié remplies, refusées, hors bon : blocages
  gardés (l'essai d'avant passe à une ligne avec BL, qui reste « à moitié remplie »).
- `frontend/src/pages/receptions/calculFiche.test.ts` : la question annonce « 23 lignes non
  livrées … seront retirées : elles restent dues sur le bon … », le singulier, le cas « tout
  refusé », toutes vides.
