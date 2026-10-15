# Stress « 3 ans d'exploitation » — le simulateur et ce qu'il a trouvé

Demande de Mohamed (15/10/2026) : « fais subir un stress test sur 10 ans d'exploitation, tout
doit y passer. Remplis **comme un humain**, pas directement dans la base, pour juger des
défaillances et blocages que je pourrai rencontrer. Correctif à condition d'être sûr. » Règle
ajoutée le même jour : **travailler sur une copie, laisser ses référentiels tels quels** ; les
besoins du scénario ajoutent des éléments d'essai dont le nom finit par « (stress) ». Décision du
même jour en cours de route : **trois années pour le moment, pas dix** — la simulation a été
arrêtée proprement après la troisième (15/10/2026 → 14/10/2029).

Branche `stress-simulateur`. Rien n'est écrit dans `gestion_mp_pro` (8050) : la simulation
tourne sur `gestion_mp_pro_stress_essai`, copie du dump des référentiels du 15/10/2026
(124 matières, 18 qualités, 319 recettes, 12 fournisseurs, 4 métiers, 3 magasins, 11 postes,
7 unités de titrage, activité vide), migrée `head`. À la fin, les référentiels de Mohamed ont été
comparés colonne par colonne à la production (matières, qualités avec poids, recettes et
saisonnalité, fournisseurs, métiers, magasins, postes, unités, codes douaniers) : **0 ligne de
différence** (voir § 4, C3, pour les 9 prix remis par la route).

## 1. Le simulateur (`backend/essais/stress/`)

    cd backend
    .venv/bin/python -m essais.stress.simulateur --dump <référentiels.dump> --annees 3
    .venv/bin/python -m essais.stress.simulateur --depuis-annee 2 --annees 10   # reprise

| Module | Rôle |
|---|---|
| `socle.py` | environnement (base `gestion_mp_pro_stress*_essai` exigée, aucune tâche de fond), `Horloge` (jour de l'usine fixé par `services.horloge.fixer`, une minute par appel), `Poste` (un `TestClient` par compte : chaque appel consigné et jugé contre le statut attendu), `Journal` (`appels-annee-N.csv`, `anomalies.jsonl`, `journal-10-ans.md`, compteurs). |
| `monde.py` | les trois comptes (`stress-direction`, `stress-achats`, `stress-alimentation`, codes de `tests/fabrique.py`), le catalogue **relu par l'API**, le hasard à graine (`graine-année`). |
| `achats_commandes.py` | plan d'achat lu → un à trois bons par semaine (lundi, jeudi), envoi, approbation de la direction au-delà du seuil (renvoi parfois), prix confirmés (au mètre pour le cuir, en deux fois parfois, hausse qui repasse par la direction), jalons d'expédition. Le catalogue n'est mis à jour que si **toutes** les lignes sont des matières d'essai. |
| `achats_receptions.py` | camions des bons arrivés (mardi, vendredi) : lignes non livrées laissées vides, lots du fournisseur ou internes, pesées dans et hors tolérance, lignes sous réserve (quarantaine) et refusées, factures par devise ou complétées après validation ; brouillons repris/supprimés ; réclamations ; libérations et retours au fournisseur. |
| `importations.py` | chaque fin de mois : dossiers depuis les factures étrangères (une ou deux par dossier), cours payé, frais au **taux** (droits 2,5 %, TPI 0,25 %, TVA 20 %, montant arrondi comme la douane), fret et assurance, clôture ; une facture arrivée après la clôture fait **rouvrir la période** par la direction ; règlements de l'échéancier. |
| `atelier.py` | deux à six ordres par jour (proposition FIFO reprise à la main, bobines entières, excédent, hors recette), retours des machines, annulations, montages/démontages (effet confirmé comme l'écran, 409 `effet_change` relu), transferts, besoins signalés et traités, scans de lot. |
| `periodes.py` | fin de mois (dossiers, règlements, inventaire tournant avec recomptage, ajustement, brouillons de la période, **clôture**, lectures de la direction, invariants) ; trimestre (matière « (stress) » — au mètre un trimestre sur deux —, qualité et recette, version de recette et prix sur les éléments d'essai, désactivation d'essai, poste de frais, cours) ; année (plans d'essai refaits, croissance, unité de titrage, compte atelier, code remis à zéro, **sauvegarde puis restauration sur une base à part**, exports et documents de l'année, contrôles lus). |
| `erreurs.py` | chaque mercredi, deux ou trois erreurs humaines : date future, date 2006, période close, version périmée, double validation, plus que le stock, lot inconnu, hors droits, deux postes, inventaire en double — chacune **doit** être refusée. |
| `verifications.py` | fins de mois : `GET /controles/soldes` et le même recompte en SQL, Entré − Sorti = Reste, `GET /stock` contre la somme SQL des soldes et des fils montés (net, quarantaine, machine, disponible), échéancier (pièces non réglées) contre la base, **vérificateur V1 (`verification_chiffres.py`) joué en mémoire** ; fin d'année : restauration de la sauvegarde sur `gestion_mp_pro_stress_restaure_essai` et comptes de lignes. |
| `simulateur.py` | la boucle des jours ouvrés (jamais le dimanche, samedi léger), les rendez-vous, le dump `annee-N.dump` par année simulée, la reprise. |

Classes d'anomalie : `erreur_500` (CERTAIN), `refus_inattendu` / `refus_manquant` (PROBABLE,
jusqu'à l'analyse), `lenteur` (> 1 s PRÉSENTATION, > 3 s PROBABLE), `invariant` (PROBABLE jusqu'à
l'analyse), `controle_referentiel` (QUESTION MÉTIER : un contrôle qui vise un référentiel de
Mohamed, consigné, jamais corrigé par une donnée), `exception` (GENERATEUR : faute du simulateur).

Réglage changé sur la copie (un réglage, pas un référentiel) : `seuil_approbation` 0 → 300 000 MAD,
pour que l'approbation de la direction soit jouée ; `croissance_annuelle` 0 → 3 % au premier
janvier. Le stock de départ est posé par la direction en opération « stock d'ouverture » (116 lots
internes, un à deux mois de consommation par matière consommée).

## 2. Ce qui a été rejoué (trois années, 15/10/2026 → 14/10/2029)

**62 743 appels** par les routes, en **86 min** de machine (13,9 + 32,8 + 39,5 min : la durée
croît avec le journal). Statuts : 200 × 55 008, 201 × 5 587, 204 × 857, 401 × 101 (sessions
expirées à 30 jours, reconnexion), 403 × 111 (droits éprouvés), 404 × 642 (dont 630 du
vérificateur V1 sur les tables non exposées, attendus), 409 × 353, 422 × 84. **Aucune erreur 500.**

| Famille | Volume sur 3 ans (gestes réussis) |
|---|---|
| Achats | 403 bons de commande (26 approbations, 1 renvoi), 451 confirmations de prix, 770 jalons d'expédition |
| Réceptions | 442 réceptions dont 420 validées, 926 lots reçus, 43 brouillons modifiés, 18 supprimés, 87 factures complétées après validation, 38 réclamations ouvertes et closes, 44 libérations de quarantaine, 24 retours au fournisseur |
| Importations | 254 dossiers (253 clos), 1 300 frais, 65 secondes factures, 9 périodes rouvertes pour une facture tardive, 1 540 règlements |
| Atelier | 3 304 ordres saisis, 2 534 validés, 327 hors recette, 98 annulés, 450 retours des machines, 116 montages et 33 démontages, 313 transferts, 157 besoins signalés et traités, 313 scans |
| Mois | 36 clôtures de période, 36 inventaires (35 validés, 1 abandonné, 20 recomptages, 7 lots trouvés), 22 ajustements, 36 séries de lectures de la direction (bilan, Cockpit, document A4, contrôles, valorisation, exports) |
| Trimestres / années | 12 matières, 12 qualités, 12 postes de frais, 2 unités de titrage « (stress) », 11 versions de recette et 11 prix changés sur les matières d'essai, 9 désactivations d'essai, 24 cours, 15 plans refaits, 3 comptes créés, 3 codes remis à zéro, 3 sauvegardes puis restaurations sur une base à part, 3 séries d'exports de l'année, 114 contrôles lus |
| Erreurs humaines | 386 jouées, toutes refusées proprement (4xx, message clair) |

Base finale (`gestion_mp_pro_stress_essai`, remise exactement au dump `annee-2.dump`) : 38 266
mouvements, 982 lots, 1 240 soldes, 2 544 ordres, 856 opérations, 424 réceptions, 403 bons,
254 dossiers, 420 factures, 78 inventaires, 17 481 lignes de journal d'audit ; compteurs par année
(BC 34/82/184/103, REC 15/104/191/114, OF 195/1 019/860/469, DOS 5/72/109/68…) : la numérotation
repart bien à 0001 chaque année. Période close jusqu'au 30/09/2029.

**Invariants (36 fins de mois)** : soldes = journal (API et SQL), aucun solde négatif, Entré − Sorti
= Reste, stock par matière écran = SQL (net, quarantaine, machine, disponible), échéancier des
pièces non réglées = base, restauration à part = mêmes comptes : **toujours justes**. Vérificateur
V1 en mémoire : de 9 355 à 137 564 vérifications par fin de mois, **0 écart** hors les deux attentes
fausses du vérificateur décrites en § 3 (plafond des 300 règlements, C07).

**Durées** : p50 20 ms, p95 448 ms, p99 1,0 s, max 2,93 s ; 626 appels > 1 s (3 la première année,
23 la deuxième, 600 la troisième), aucun > 3 s. Détail § 3.

## 3. Anomalies classées

| # | Classe | Quoi | Exemple chiffré | État |
|---|---|---|---|---|
| A1 | **CERTAIN, corrigé** | La facture saisie avec un brouillon de réception restait **due** dans l'échéancier quand le brouillon était supprimé (ou corrigé avec un autre n°, ou la facture détachée/renumérotée après validation). | Brouillon n° 9 du 11/12/2026 avec INV-2612-873 (5 279,96 USD, échéance 09/01/2027) supprimé le 14/12 → facture comptée due dans l'échu et les totaux ; vu par le recompte SQL (« factures écran 17 / SQL 16 ») **et** par V1 (« facture 9 due : dans l'échéancier sans être due »). | Correctif C1 (§ 4). |
| A2 | Attente du vérificateur fausse (PRÉSENTATION pour Mohamed) | L'échéancier ne rend que les **300 règlements les plus récents** (`calcul.suivi.REGLEES_AU_PLUS`, voulu) ; V1 attendait chaque pièce réglée dans « Réglées ». 124 écarts de ce type sur 3 ans, grossissant avec le temps. | Septembre 2027 : 304 règlements → frais 30, 33, 34, 35 (réglés le 01/01/2027) « attendus dans reglees, vu [] » ; fin 2029 : 1 540 règlements, 1 240 hors liste. | V1 corrigé (`essais/verif_achats.py`, règle valable pour les factures et les frais) ; vérifié sur une copie : famille Échéancier ✓ 1 496 vérifications. **Application inchangée.** Pour Mohamed : l'écran dit « Réglées (300) » sans dire que la liste et la feuille Excel « Réglées » sont bornées ; une pièce réglée plus ancienne se retrouve sur sa fiche (réception, dossier). |
| A3 | Attente du vérificateur fausse (bordure du recompte) | C07 « matière jamais utilisée » : le contrôle ne regarde que les matières **en service** ; le SQL de V1 oubliait `m.actif`. Écran 34, recompté 35 puis 36 (18 écarts). | Matières d'essai désactivées sans recette ni mouvement : 129 « Essai 5 (stress) » (01/04/2028), puis 126 « Ruban PES 25 mm (stress) 2 » (01/07/2028) et 131 « Essai 7 (stress) » (01/01/2029) : 34 + 2 = 36. | V1 corrigé (`essais/verif_controles.py`). **Application inchangée.** |
| A4 | PRÉSENTATION (lenteur, croît avec le volume) | `POST /ordres/{id}/valider` : la réponse (fiche de l'ordre) recharge **tout le moteur** (`donnees_moteur.charger`, 37 914 mouvements) pour calculer la consommation de tous les ordres (`services/ordres/consommation.consommations`, P80) : la validation elle-même prend 0,3 s, la fiche 1,2 s. Même cause pour `GET /ordres` (p95 0,96 s, max 2,78 s) et `POST /ordres/{id}/annuler`. | 2 574 validations : p95 1,20 s, max 2,93 s, 567 > 1 s (toutes la troisième année) ; profil `cProfile` sur une copie de la base « 3 ans » : 1,69 s dont 1,21 s de chargement du moteur (deux fois). | **Corrigé le 15/10/2026** (docs/lots/ORDRE-FICHE-LEGERE.md) : la fiche d'un ordre et une page de liste calculent la consommation sur le journal **de ces ordres seuls** (`consommations_de`, `donnees_moteur.charger_ordres`), mêmes chiffres prouvés sur les 2 543 ordres de la base « 3 ans » ; fiche après validation 811 → 33 ms (p50), p95 864 → 56 ms ; `GET /ordres` (50) 888 → 70 ms. Reste `GET /ordres/ouverts` sans filtre (liste entière, 0,8 s : volume des lignes, pas le moteur). |
| A5 | PRÉSENTATION (lenteur) | `GET /bilan` 108 appels, p95 1,44 s, max 1,60 s ; `GET /export/mouvements` (année entière) 2,64 s ; `PUT /inventaires/{id}/comptages` 2,26 s ; `GET /courriel/apercu` 1,05 s. | fins de mois et d'année | Non corrigé ; à surveiller à l'écran (indicateur d'attente). |
| A6 | QUESTION MÉTIER (déjà DM-02) | C01 Franges : 6 qualités (8S, 8M, LP, MN, MP, SH) ont un poids Franges sans matière Franges → un ordre « selon la recette » sur ces qualités est **bloqué à la saisie**, message clair (créer la matière Franges ou mettre le poids à 0). | 19 blocages consignés ; le générateur évite ces qualités (sauf 5 % pour le consigner). | Consigné, **pas corrigé par une donnée** (règle de Mohamed). |
| A7 | Refus attendus et justes (pas des anomalies) | 409 `cout_periode_close` à l'ouverture d'un dossier pour une facture arrivée après la clôture (→ la direction rouvre la période, dossier, re-clôture : 9 fois) ; 409 sur l'ajout d'une facture d'un mois clos (15) ; 409 `stock_insuffisant` pour un brouillon d'ordre validé le lendemain, lot épuisé entre-temps (abandonné) ; 422 « livraison prévue avant la date du bon » (3, fournisseur local à 4 jours) ; 422 code d'unité « Ustr@ » (1) ; 422 frais à 0,00 (1). | | Générateur corrigé pour ne plus les provoquer ; messages jugés clairs. |
| A8 | Bordure (générateur) | 539 brouillons d'ordres bloqués à la saisie la troisième année : la proposition FIFO propose un lot presque vide (« HT-280502-0427 : 3,151 kg seulement dans Morocco ») et la bobine entière demandée dépasse de quelques grammes ; l'atelier abandonne le brouillon. | 497 fois le même lot | Générateur à affiner (prendre le lot suivant) ; côté application, question de confort : la proposition pourrait sauter un reliquat plus petit qu'une bobine. |

Aucun 5xx, aucun refus manquant, aucune faute du générateur (classe GENERATEUR) sur les trois ans.

## 4. Correctifs

### C1 — La facture d'un brouillon de réception supprimé restait due (CERTAIN, corrigé, a38091b)

Fait (année 0) : le 11/12/2026 les achats saisissent un brouillon avec sa facture INV-2612-873
(5 279,96 USD) ; le 14/12 ils suppriment le brouillon (camion refait). La facture restait en base,
portée par aucune réception ; `calcul.suivi.factures_dues` ne connaît que les factures portées par
une réception (brouillon → « pas encore due », toutes annulées → « écartée ») : celle que **rien**
ne porte était comptée **due**, à l'échéance, dans l'échu et les totaux. Même chose si le brouillon
est corrigé avec un autre numéro, ou si la facture d'une réception validée est détachée
(`numero: ""`) ou renumérotée : l'ancienne restait due. Les factures ne naissent que par une
réception (`factures.attacher`, `preparer_cible`) : une facture orpheline n'a pas d'autre origine.

Correctif (`services/factures.oublier_si_orpheline`, appelé par `receptions.supprimer`,
`receptions.modifier`, `receptions_facture.completer_facture`) : la facture que la réception
portait seule disparaît avec elle quand rien d'autre ne la porte — ni réception, ni dossier
d'importation (même annulé), pas réglée ; journal « facture oubliée ». Essai
`tests/test_factures_brouillon_supprime.py` (3 cas : échoue avant, passe après). Aucune décision
de Mohamed touchée (I3/I23 : une facture reste portée par ses réceptions et son dossier). Les
années 1 et 2 ont tourné avec le correctif : plus aucune facture orpheline (recompte SQL de
l'échéancier ✓ à chacune des 24 fins de mois suivantes).

### C2 — Vérificateur V1 (essais, pas l'application) : dc505d3, eff43a0

Plafond des 300 règlements (A2) et matières en service pour C07 (A3) : deux attentes du vérificateur
corrigées ; l'application n'a pas changé.

### C3 — Le générateur avait réécrit 9 prix catalogue de Mohamed (copie seulement) : 8801db8

Une confirmation de prix qui mêlait une matière d'essai et des matières de Mohamed passait
`mettre_a_jour_catalogue` à vrai pour toutes les lignes (2 bons, BC-2027-0045 et BC-2029-0095 :
9 matières, prix 2,72 → 2,7457 USD/kg etc., journalisé « prix confirmé »). Contraire à la règle du
15/10. Générateur corrigé (le catalogue n'est mis à jour que si **toutes** les lignes sont d'essai) ;
sur la base « 3 ans », les 9 prix d'origine ont été **remis par la route** (achats,
`PUT /matieres`, journalisé le 14/10/2029) et le dump `annee-2.dump` refait. Comparaison finale
production ↔ base « 3 ans » de tous les référentiels : 0 différence. La production n'a jamais
été touchée.

## 5. Vérifications et emplacements

- `make verifier` complet, machine à vide, après les correctifs : serveur **2 984 passés, 5 sautés**
  (ruff, format, mypy strict, `alembic check` sans écart), écran **863 passés, 1 sauté**, outils
  (342 appels de l'écran dans l'OpenAPI, 289 preuves héritées) sans écart.
- `git merge main` : main (3b4a694) n'a pas bougé pendant le chantier.
- Base gardée : `gestion_mp_pro_stress_essai` (état « 3 ans », = `annee-2.dump`) pour l'épreuve
  d'écran. Dumps : `~/gestion-mp-pro-sauvegardes/stress/annee-{0,1,2}.dump` (1,0 / 1,8 / 2,4 Mo) ;
  `app/` : les sauvegardes faites par l'application elle-même pendant la simulation.
- Journal : `backend/essais/stress/journal-10-ans.md` (le fil des 36 mois), `anomalies.jsonl`
  (775 lignes classées), `appels-annee-{0,1,2}.csv` (62 743 appels, non commités).
- Bases d'essai supprimées : `gestion_mp_pro_stress_pytest_essai`, `gestion_mp_pro_stress_restaure_essai`,
  `gestion_mp_pro_stress_profil_essai`, `gestion_mp_pro_stress_verif_essai`.

## 6. Pour Mohamed (une phrase chacune)

1. **Réglées (300)** : l'échéancier et sa feuille Excel ne montrent que les 300 derniers règlements
   (1 540 au bout de trois ans) — faut-il le dire à l'écran, ou une période « du / au » sur les
   réglées ?
2. **Valider un ordre au téléphone** prend 1,2 s après trois ans (2 500 ordres), parce que la fiche
   rendue recalcule la consommation de tous les ordres : à dix ans ce serait ~5 s — veut-il qu'on
   allège la fiche (ne charger que les lots de l'ordre) ?
3. **Franges (DM-02)** : toujours en attente ; tant que la matière n'existe pas, 6 qualités ne
   lancent pas d'ordre « selon la recette » (message clair).
4. **Proposition FIFO** : quand le premier lot ne contient plus qu'un reliquat plus petit qu'une
   bobine, elle le propose quand même ; faut-il sauter au lot suivant ?
5. **Épreuve d'écran** sur la base « 3 ans » (listes paginées, 12 mois, exports, Cockpit) : non
   jouée ici (le simulateur passe par les routes) ; la base est gardée pour la faire.
