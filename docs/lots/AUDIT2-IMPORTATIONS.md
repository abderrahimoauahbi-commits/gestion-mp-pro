# Audit n° 2 — IMPORTATIONS & COÛT DE REVIENT, avec modifications (14/10/2026)

Branche `audit2-importations` (depuis main 9b20443). Point de départ : `docs/lots/AUDIT-IMPORTATIONS.md`
(passage n° 1 : aucune correction, un constat PROBABLE P-IMP-1 et deux questions, tranchées par le
coordinateur — décisions IMPORTATIONS de `AUDIT2-PRO-CONSIGNES`). Aucune révision Alembic (la 0010
réservée n'a pas servi) : rien de nouveau dans le schéma, le journal suffit.

## Méthode
- Base d'essai à soi `gestion_mp_pro_imp2_essai` (jamais `gestion_mp_pro`, ni 8050/8030), venv et
  écran installés dans le worktree ; types de l'écran régénérés depuis l'OpenAPI **de la branche**
  (`creer_application().openapi()` → fichier → `scripts/generer_types.sh <fichier>`).
- Chaque correction : un essai qui **échoue avant** (13 essais rejoués sur le code de `main` :
  13 échecs) et **passe après** (13 réussites), le plus petit changement juste.
- Sondes de robustesse (`scratchpad/imp2_sondes.py`, 25 entrées limites sur les routes 187–208,
  253–254, 34–37) : toutes refusées en clair (422/404/409 nommant la cause), sauf deux cas corrigés
  ci-dessous. Aucune 500.
- `make verifier` complet vert (serveur, écran, outils) — voir le rapport final.

## Modifications

| # | Quoi | Pourquoi | Preuve |
|---|---|---|---|
| 1 | **Repères par la nature des postes** (`calcul/modele/flux.ChargeImport` : `nature`, `entre_valeur_douane`, propriétés `est_droits`, `est_tpi`, `est_tva`, `dans_valeur_douane` ; `calcul/importations.tva_attendue`, C29 `calcul/controles/importations`, fiche `_sommes`, `lignes._Lecteur.droits`, les deux chargeurs `services/chargeur/production._frais` et `services/importations/socle.vue`) | Décision IMPORTATIONS n° 1 (P-IMP-1 du passage 1) : « droits attendus », « TVA attendue » et « valeur en douane » suivaient les codes DD/TPI/TVA/FRET/ASSUR en dur, alors que l'écran (base du taux) et le vérificateur indépendant lisent `nature` et `entre_valeur_douane`. Un poste sur mesure de nature « droits » était ignoré dans ces repères. | `tests/test_importations_nature.py` (6) : poste neuf `DDX…` de nature droits 10 000 → `droits_mad` 11 000 et TVA attendue qui les compte (avant : 1 000 et 12 230) ; poste `TVAX` de nature tva = TVA de la douane (alerte « Aucune TVA saisie » éteinte, C29 juste/faux selon l'écart) ; poste `FRETX` « entre dans la valeur en douane » compté dans `valeur_douane_mad` et la TVA attendue, un « MANUT » autre non ; TPI sur mesure prise telle quelle ; **parité** : les cinq postes système donnent la même TVA attendue par le code seul ou par la nature (`est_droits`, `dans_valeur_douane` identiques) ; clôture d'un dossier au poste sur mesure. |
| 2 | **Parité conservée** : sans nature (jeux du moteur `tests/moteur/*`, données d'origine), le code fait foi ; les 5 postes semés (`0002_semences`) ont nature et drapeau alignés sur leur code. Le coût de revient lui-même n'a pas changé (il ne lit que `recuperable`). Deux neutralisations **côté essais seulement**, avec leur raison : `tests/fabriques/moteur_attendu.py` (le monde attendu porte la nature de ses deux frais DD et FRET) et `tests/test_donnees_moteur_jeu.py::_nature_des_postes` (le jeu réel de Gestion MP n'avait que le code ; `NATURE_DES_POSTES` = les semences). Aucun chiffre comparé ne change (sorties du moteur sur les 4 jeux réels : identiques). | Ne pas changer un chiffre « prouvé à l'identique de Gestion MP ». | Essai de parité ci-dessus ; 40 constructions `ChargeImport(` des essais du moteur inchangées et vertes ; `test_donnees_moteur*.py`, `test_scenario_court.py` verts ; `verif_importations.py` (droits = nature `droits`, TVA attendue par `entre_valeur_douane` et natures) est désormais **le même chemin** que le serveur. |
| 3 | **Ré-ajout non silencieux** (`services/importations/cours_repris.py`, nouveau ; `factures_dossier.ajouter`, `ouverture.rattacher` et `_depuis_facture`, `fiche.fiche(…, avis)`, `routeur.fiche_relue`, routes 190/192/253 ; `DossierFiche.avis: list[str]`) | Décision IMPORTATIONS n° 2 (question 2 du passage 1) : retirer puis ré-ajouter une facture (ou détacher/rattacher sa réception, annuler puis rouvrir) ramenait la marchandise **au cours du bon** sans rien dire (−22 339,80 MAD de valeur en douane sur le dossier 01/26 de l'exemple). | `tests/test_importations_reprise_cours.py` (5) : la réponse porte `avis` = « Facture F : reprise de 1 marchandise au cours du bon BC-… (10 MAD pour 1 XXX) — le cours payé saisi avant sa sortie ne revient pas (le cours payé à la banque se ressaisit dans l'onglet Marchandises). Dernier cours payé saisi : XXX à 10,05. » ; première entrée (pas une reprise) : « … au cours du bon … le cours du bon est celui des réglages à la confirmation des prix ; le cours payé … se ressaisit … » ; sans bon : « … sans cours payé (comptée au cours du jour) » ; une lecture de la fiche (route 189) a `avis = []`. |
| 4 | **Dernier cours payé retrouvé sans schéma** : le retrait d'une facture, le détachement d'une réception et l'annulation du dossier écrivent au journal `avant.cours_payes = {ligne reçue: cours}` (tout cours qui n'est pas celui du bon) ; le retour relit le journal (JSONB `?|`), la sortie la plus récente d'abord, et **propose** le cours (il ne le remet pas : la règle « revient au cours du bon » tient). Le détail du journal de l'ajout porte « · reprise : le cours payé d'avant la sortie ne revient pas ». | « Si tu peux retrouver sans schéma le dernier cours payé (journal) et le proposer, fais-le. » | Mêmes essais : `avant.cours_payes == {"412": 10.05}` au retrait, `[9.9]` au détachement, `[10.2]` à l'annulation ; rien de gardé pour une ligne restée au cours du bon ou sans cours. |
| 5 | **Écran** : `useDossier.direLesAvis` (un message « info » par avis) après « Ajouter une facture » (`FacturesDossier`), le second camion (`VoletSecondCamion`, `EnAttente`) et l'ouverture d'un dossier depuis « En attente ». | « La réponse et l'écran le disent. » | `FacturesDossier.test.tsx` : la réponse 253 avec `avis` affiche le texte intégral ; `make verifier-ecran` vert. |
| 6 | **« Proposer les droits »** (`VoletFrais.tsx`) choisit le poste de nature `droits` (le système d'abord) et se grise si un frais de cette nature existe déjà — plus `code === 'DD'`. | Même alignement que le serveur ; sur les 5 postes système, même comportement. | `tsc`, `eslint`, essais d'écran verts (le bouton n'avait pas d'essai propre ; comportement identique avec les postes semés). |
| 7 | **Refus clair : frais sous le centime** (`services/importations/frais._verifier`) : 0,004 MAD arrondit à zéro ; la base le refusait par `ck_dossier_frais_montant_non_nul` → 409 « Cette saisie contredit une règle de la base… ». Désormais 422 « Un frais a un montant d'au moins un centime (un avoir se saisit en négatif). » | Trouvé par sonde (du neuf) : message trompeur. | `tests/test_importations_refus_clairs.py::test_un_frais_sous_le_centime_est_refuse_en_clair` (avant : 409 `regle_de_la_base`). |
| 8 | **Refus clair : poste système** (`services/postes_frais._verifier_nature`) : décocher « entre dans la valeur en douane » de FRET répondait « « Fret » est un coût par nature : les calculs du dossier (TVA attendue) le lisent ainsi. ». Désormais : « « Fret » est un poste système : il reste un coût, de nature « fret » et entre dans la valeur en douane — les calculs du dossier (valeur en douane, droits et TVA attendus) le lisent ainsi. Une autre nature se crée comme un autre poste. » | Trouvé par sonde : le refus ne disait pas ce qu'on avait touché ; avec la modification n° 1, la nature compte d'autant plus. | `test_un_poste_systeme_dit_ce_qui_ne_change_pas` ; `test_magasins_postes.py` mis au nouveau texte (TVA). |
| 9 | Documents : `docs/MODELE-DONNEES.md` (NatureFrais et `poste_frais` : lus par le moteur), `docs/API-PRO.md` (routes 189 et 192 : `avis`). | — | — |

Fichiers : `backend/gestion_mp_pro/calcul/{modele/flux.py, importations.py, controles/importations.py}`,
`services/chargeur/production.py`, `services/importations/{socle,fiche,lignes,modele,ouverture,
factures_dossier,marchandises,etats,frais,cours_repris}.py`, `services/postes_frais.py`,
`api/importations/{routeur,routes,routes_gestes,schemas_fiche}.py` ; `frontend/src/pages/importations/
{useDossier.ts, FacturesDossier.tsx, VoletSecondCamion.tsx, EnAttente.tsx, VoletFrais.tsx,
ControlesFrais.tsx}`, `lib/types.gen.ts` (régénéré) ; essais `test_importations_nature.py`,
`test_importations_reprise_cours.py`, `test_importations_refus_clairs.py`, `FacturesDossier.test.tsx`.

## Ce qui est vérifié et n'a pas changé
Tout le tableau « vérifié JUSTE » du passage 1 tient (197 + 13 essais serveur d'importation verts) :
coût de revient sans doublon à plusieurs factures, C36 facture par facture, échéancier, annulation qui
libère, taux jamais recalculé au serveur, exports, rôle `alimentation` à 403 partout (matrice inchangée :
aucune route nouvelle, `avis` n'est servi qu'à D et A).

## Ce qui reste (non corrigé, dit pour Mohamed)
- **Analyse du coût de revient, `du` après `au`** : le serveur répond 200 avec une analyse vide plutôt
  qu'un refus « la date de début est après la fin ». L'écran ne le propose pas ; une 422 serait plus
  parlante en appel direct. Pas de chiffre faux : non corrigé, à décider.
- **Changer « entre dans la valeur en douane » d'un poste sur mesure** porté par des dossiers ouverts
  change leurs repères (TVA attendue, valeur en douane) sans passer par la protection de période close
  (`_proteger_periode_close` ne regarde que la clé et récupérable/nature). Le **coût** ne bouge pas,
  seuls les repères : laissé tel quel, signalé.
- Le dernier cours payé n'est retrouvé que pour les sorties **postérieures** à cette version (le journal
  d'avant ne porte pas `cours_payes`) ; un dossier repris de l'ERP Fil n'a pas de ligne de liaison et
  passe par le même chemin sans avis particulier.
- Les documents d'héritage (`REGLES R-IMP-08/09`, `CALCULS § 9`) décrivent toujours Gestion MP par ses
  codes : ce sont des preuves d'origine, non réécrites (« le code fait foi »).
