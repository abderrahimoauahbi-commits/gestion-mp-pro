# Lot PLUSIEURS-FACTURES — un dossier d'importation, plusieurs factures

Branche `lot-plusieurs-factures` (depuis main 0140a0c). Révision Alembic **0007** (réservée par le
coordinateur). Routes nouvelles **253** et **254**. `make verifier` vert : 2937 essais serveur
(5 sautés), 851 essais d'écran (1 sauté), outils (routes de l'écran, preuves héritées) sans écart.

## La demande (Mohamed, 12 octobre 2026)
« Un dossier d'importation peut avoir plusieurs factures. » Elle **amende I3** (08/10 : « un dossier =
une facture = une livraison ») sur ce seul point : un dossier — une déclaration en douane, un arrivage —
regroupe une ou plusieurs factures (deux factures du même fournisseur dans le même conteneur, ou de
fournisseurs différents groupés). Le reste de I3 tient : ouverture depuis une facture reçue (à la main
seulement d'avant la mise en service), réception sans facture qui attend, second camion qui rejoint,
ligne reçue qui ne sort qu'avec sa réception, **une facture dans un seul dossier** (non annulé ; à deux
postes, 409 qui nomme le gagnant). Écrite en **I23** et **R7** dans `docs/heritage/DECISIONS.md` (I3 n'est
pas réécrite).

## Le modèle choisi : une table de liaison `dossier_facture`
`dossier_facture(dossier_id, facture_id)` — PK composite, `dossier_id` FK ON DELETE CASCADE,
`facture_id` FK RESTRICT, `ajoutee_le`, `ajoutee_par_id`, `liberee_le` — et l'index unique partiel
`uq_dossier_facture (facture_id) WHERE liberee_le IS NULL` (le même nom qu'avant, déplacé de `dossier`).
`dossier.facture_id` **disparaît** : une seule source de vérité (la « facture d'ouverture » n'est que la
première ajoutée, `ajoutee_le` puis `facture_id`).

Pourquoi pas `facture.dossier_id` : la reprise écrit les factures **avant** les dossiers (clé étrangère
impossible à poser dans l'ordre), chaque ajout aurait monté la `version` de la facture (409 à tort sur
la correction d'une facture depuis sa réception), et un dossier annulé aurait perdu la trace de ses
factures. Avec la liaison : l'unicité « une facture, un dossier vivant » est un index (deux postes : le
perdant prend l'`IntegrityError` dans un point de reprise → 409 qui nomme le gagnant, comme à
l'ouverture) ; un dossier **annulé garde** ses lignes de liaison, `liberee_le` posé (la facture est libre,
la fiche annulée dit lesquelles) ; retirer une facture **supprime** sa ligne (le journal du dossier la
garde).

Migration 0007 : une ligne par `dossier.facture_id` non nul (ajoutée à `cree_le` par `cree_par_id` ;
libérée à `annule_le` si le dossier est annulé), puis la colonne et son index retirés. Base de Mohamed :
1 dossier, 1 facture → 1 ligne. Retour arrière : la première facture revient dans `dossier.facture_id` ;
**refusé** (message qui nomme les dossiers) si un dossier vivant a plusieurs factures — elles seraient
perdues en silence. Essai `test_migrations_0007.py::test_0007_un_dossier_garde_sa_facture` (montée, contenu,
refus, descente, remontée) ; aller-retour complet et `alembic check` verts. 72 tables, 691 colonnes,
173 clés étrangères, 195 index (MODELE-DONNEES § 3.8.5 et § 11, vérifiés en base).

## Les règles appliquées
1. **Ajouter une facture** (route 253, `POST /dossiers/{id}/factures` `{version, facture_id,
   local_confirme}`, D + A) : dossier ouvert (`ouvert()` : version → 409, clos/annulé → 409), pas un
   dossier saisi à la main (409, `actions.ajouter_facture` le dit d'avance) ; facture connue (404), dans
   aucun dossier vivant (409 `doublon` qui nomme le dossier — le texte X-IMP-05 de l'ouverture) ;
   fournisseur marocain : 409 « … L'ajouter quand même se confirme. » sans `local_confirme` (I16), et
   le dossier garde `local_confirme` ; toute sa marchandise libre entre (`ouverture.marchandises` : pesée
   × prix, cours figé du bon) ; période close respectée (`cout_hors_periode_close`, « ajout d'une
   facture ») ; journal « facture ajoutée ». Autre devise, autre fournisseur : permis, chaque ligne garde
   sa devise.
2. **Retirer une facture** (route 254, `DELETE /dossiers/{id}/factures/{fid}?version=`) : sa
   marchandise sort (parts figées des frais qui la touchaient effacées, comme au détachement : ces
   frais se répartissent de nouveau à la clé de leur poste sur ce qui reste) et attend de nouveau ;
   refusé (409) si un frais vise une de ses marchandises — la phrase est celle du `retrait` de la fiche,
   mot pour mot ; 404 si la facture n'est pas dans le dossier ; journal « facture retirée ». Retirer la
   dernière facture est permis (corriger un dossier ouvert depuis la mauvaise facture : retirer, puis
   ajouter la bonne) ; le dossier vide ne se clôt pas.
3. **Détacher une réception** : si c'était tout ce que sa facture avait apporté au dossier, la facture
   le quitte (« · facture X sortie du dossier » au journal) et attend de nouveau.
4. **Annuler** : toutes ses factures sont libérées (`liberee_le`) ; journal « factures A, C libérées ».
5. **Second camion** : `factures_acceptees` = ses factures (non libérées) ∪ celles de ses marchandises
   (dossier repris) ; rattacher la suite d'une facture qui n'est pas au dossier : « La facture G n'est pas
   dans le dossier NN/AA : l'y ajouter d'abord (« Ajouter une facture », toute sa marchandise entre), ou
   elle ouvre son propre dossier. »
6. **C36 facture par facture** : le moteur (`calcul.modele.FactureImport` : numéro, montant, devise,
   identifiants des marchandises qu'elle a apportées ; `DossierImport.factures` remplace `facture`,
   `facture_montant`, `facture_devise`) rapproche chaque facture de **ses** marchandises
   (`ecart_facture(dossier, facture, p)`, `ecarts_factures`). « Montant de la facture non saisi » sonne
   dès que le dossier a des marchandises (comme Gestion MP) ; « marchandise en … : ne se rapproche pas »
   et l'écart portent sur ses seules marchandises. Une ligne de C36 par facture. C11 lit la devise de
   chaque facture.
7. **Lecture** : `DossierResume.factures` = `[FactureDossier]` {…, `ajoutee_le`, `liberee_le`,
   `receptions`, `lignes`, `ecart`, `retrait`} (remplace `facture`, `ecart_facture` et l'ancienne liste
   de numéros) ; `pieces` cite aussi une facture du dossier sans marchandise ; échéancier : une échéance de
   marchandise par facture ; alertes et « à vérifier » : « La facture F s'écarte de x % de la marchandise
   qu'elle a apportée. » ; liste : recherche sur les numéros **et les fournisseurs** de ses factures,
   filtre « fournisseur » = celui d'**une** de ses factures (annulés compris), options du filtre idem ;
   classeur : colonne « Factures » = ses factures ; route 175 (factures) et `factures.porteur` lisent la
   liaison ; le panneau « Facture du fournisseur » d'une réception mène à son dossier (par la ligne
   reçue, inchangé), numéro figé.
8. **Saisi à la main / repris** : `a_la_main(d)` = `saisi_a_la_main` sans facture ni marchandise reçue (un
   dossier ouvert depuis une facture ne le devient jamais, même vidé) ; `repris(d)` = `saisi_a_la_main`
   avec des marchandises reçues. Un dossier repris de l'ERP Fil n'a **pas** de ligne de liaison : ses
   factures se lisent sur ses marchandises (`pieces`), comme avant.

## Écran
- `pages/importations/FacturesDossier.tsx` : bloc « Factures du dossier » de la fiche (entre l'en-tête et
  les indicateurs), `DataTable` sans recherche, `hauteur="fenetre"` (aucun défilement dans la fenêtre) :
  n°, fournisseur, date, montant (sa devise), échéance, réceptions (liens), rapprochement (« conforme » /
  `Badge` « écart x % »), « Retirer » (`Confirmer`, grisé avec `retrait`). « Ajouter une facture »
  (grisé avec `actions.ajouter_facture`) ouvre une `Fenetre` avec `ChoixFacture` (nouvelle prop `ajout`
  pour la confirmation d'un fournisseur marocain) sur les factures d'« En attente » sans dossier.
- En-tête : « Factures F · G » ; annulation : « Les factures F, G attendront de nouveau leur dossier » ;
  bandeau C36 et note de cours : un par facture ; liste : « Facture · réceptions » par `pieces`, recherche
  locale avec les fournisseurs des factures ; notes « Un dossier, une facture » remplacées.
- `lib/types.gen.ts` régénéré depuis l'OpenAPI **de la branche** (`creer_application().openapi()` →
  fichier → `scripts/generer_types.sh <fichier>`), pas du serveur 8050. `donneesEssai.json` mis à la
  forme nouvelle. `pages/administration/DonneesBrutes.tsx` : `dossier_facture` dans la liste fermée
  (route 7, `services/donnees_brutes.TABLES`).
- `aide.json` → `docs/NOTICE.md` (`make notice`).

## Essais
- Serveur : `tests/test_importations_factures.py` (14) — A puis B (même fournisseur) puis C (autre
  fournisseur, autre devise) : quatre marchandises, trois factures dans l'ordre, trois échéances de
  marchandise ; C36 par facture (fiche, alertes, contrôle) ; coût de revient sans doublon (analyse =
  dossier, 4 lignes) et classeur ; recherche et filtre fournisseur ; facture déjà dans un dossier (409
  qui le nomme), version périmée ; deux postes au même instant ([200, 409], le perdant nomme le
  gagnant) ; retirer B (marchandise en attente, fret réparti sur le reste, B peut revenir) ; retrait
  refusé si un frais vise C (phrase = `retrait`) ; détacher la dernière réception de C (C attend) ;
  annuler (A et C attendent, trace libérée, A rouvre un dossier neuf) ; second camion d'une facture
  ajoutée ; panneau de la réception et route 175 ; fournisseur marocain confirmé ; dossier saisi à la
  main refusé. `test_importations_transitions.py` : la table passe à 8 gestes (ajouter, retirer) × 3
  statuts × 4 rôles, et les deux gestes en version périmée. `test_migrations_0007.py` (à part :
  `test_migrations.py` touchait le plafond de 400 lignes),
  `test_modele.py` (unicité sur la liaison), moteur (`test_dossiers.py`, `test_controles_c26_c38.py` :
  une ligne C36 par facture).
- Écran : `pages/importations/FacturesDossier.test.tsx` (7) — une ligne par facture, ajout (fenêtre,
  POST avec la version), ajout grisé avec la raison, retrait grisé avec la raison, retrait confirmé
  (DELETE avec la version), en-tête, pas de bloc pour un dossier saisi à la main.

## Écarts aux documents de conception (à reporter)
- **REGLES X-IMP-13** (« Un dossier, une facture : {NN/AA} est celui de la facture {F}. La facture {G}
  ouvre son propre dossier. ») n'est plus vrai : remplacé par « La facture {G} n'est pas dans le dossier
  {NN/AA} : l'y ajouter d'abord (« Ajouter une facture », toute sa marchandise entre), ou elle ouvre son
  propre dossier. » ; X-IMP-05 (« … un dossier par facture … ») est gardé mot pour mot (une facture n'a
  toujours qu'un dossier).
- **B-07** (`test_echeancier_dossier_garde_sa_facture_apres_detachement`) : amendé — la facture dont on
  détache la dernière réception quitte le dossier (elle reste à payer dans l'échéancier général et revient
  dans « En attente ») ; une facture liée sans marchandise (donnée reprise d'avant 0007) reste lue
  « détachée » dans l'échéancier du dossier.
- **API 189** : `facture` et `ecart_facture` remplacés par `factures` (et l'ancienne `factures: [str]`) ;
  les outils de parité (`essais/parite_donnees.sans_index`, `parite_api_formes.dossier_comme_gestion_mp`,
  `tests/moteur/jeux_outils`, `sorties_pro._ecart_unique`) ramènent PRO à la forme de Gestion MP (une
  facture par dossier) : même valeur, autre forme. `essais/verif_importations.py` recompte C36 et l'écart
  facture par facture.
- `docs/API-PRO.md` « Bilan » (« PRO compte 246 routes… ») non recompté : il était déjà antérieur aux
  routes 245–252.

## À savoir pour les lots suivants
- Lire les factures d'un dossier par `socle.factures_vives(d)` (non libérées, ordre d'ajout) ou
  `factures_lues(d)` (avec celles qu'un annulé a libérées) ; jamais par les marchandises seules (un
  dossier repris excepté). `charger()` et la liste chargent `Dossier.factures`.
- Le porteur d'une facture : `libres.porteurs` (liaison d'abord, puis dossiers repris par leurs
  marchandises) ou `services.factures.porteur` (liaison seule).
- Ordre des factures : `ajoutee_le` puis `facture_id` — sous l'horloge figée des essais, deux ajouts ont
  le même instant ; ne pas en tirer d'ordre métier plus fin.
- Ce qui reste : aucun écran ne montre encore l'historique des factures retirées autrement que par le
  journal du dossier ; l'écran n'a pas été vu dans un navigateur (vitest seulement).
