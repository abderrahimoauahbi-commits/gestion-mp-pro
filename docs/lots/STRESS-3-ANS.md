# Stress « 10 ans d'exploitation » — le simulateur et ce qu'il a trouvé

Demande de Mohamed (15/10/2026) : « fais subir un stress test sur 10 ans d'exploitation, tout
doit y passer. Remplis **comme un humain**, pas directement dans la base, pour juger des
défaillances et blocages que je pourrai rencontrer. Correctif à condition d'être sûr. » Règle
ajoutée le même jour : **travailler sur une copie, laisser ses référentiels tels quels** ; les
besoins du scénario ajoutent des éléments d'essai dont le nom finit par « (stress) ».

Branche `stress-simulateur`. Rien n'est écrit dans `gestion_mp_pro` (8050) : la simulation
tourne sur `gestion_mp_pro_stress_essai`, copie du dump des référentiels du 15/10/2026
(124 matières, 18 qualités, 319 recettes, 12 fournisseurs, 4 métiers, 3 magasins, 11 postes,
7 unités de titrage, activité vide), migrée `head`.

## 1. Le simulateur (`backend/essais/stress/`)

    cd backend
    .venv/bin/python -m essais.stress.simulateur --dump <référentiels.dump> --annees 10
    .venv/bin/python -m essais.stress.simulateur --depuis-annee 3 --annees 10   # reprise

| Module | Rôle |
|---|---|
| `socle.py` | environnement (base `gestion_mp_pro_stress*_essai` exigée, aucune tâche de fond), `Horloge` (jour de l'usine fixé par `services.horloge.fixer`, une minute par appel), `Poste` (un `TestClient` par compte : chaque appel consigné et jugé), `Journal` (`appels-annee-N.csv`, `anomalies.jsonl`, `journal-10-ans.md`, compteurs). |
| `monde.py` | les trois comptes (`stress-direction`, `stress-achats`, `stress-alimentation`, codes de `tests/fabrique.py`), le catalogue **relu par l'API**, le hasard à graine (`graine-année`). |
| `achats_commandes.py` | plan d'achat lu → un à trois bons par semaine (lundi, jeudi), envoi, approbation de la direction au-delà du seuil (renvoi parfois), prix confirmés (au mètre pour le cuir, en deux fois parfois, hausse qui repasse par la direction), jalons d'expédition. |
| `achats_receptions.py` | camions des bons arrivés (mardi, vendredi) : lignes non livrées laissées vides, lots du fournisseur ou internes, pesées dans et hors tolérance, lignes sous réserve (quarantaine) et refusées, factures par devise ou complétées après validation ; brouillons repris/supprimés ; réclamations ; libérations et retours au fournisseur. |
| `importations.py` | chaque fin de mois : dossiers depuis les factures étrangères (une ou deux par dossier), cours payé, frais au **taux** (droits 2,5 %, TPI 0,25 %, TVA 20 %, montant arrondi comme la douane), fret et assurance, clôture ; une facture arrivée après la clôture fait **rouvrir la période** par la direction ; règlements de l'échéancier. |
| `atelier.py` | deux à six ordres par jour (proposition FIFO reprise à la main, bobines entières, excédent, hors recette), retours des machines, annulations, montages/démontages (effet confirmé comme l'écran, 409 `effet_change` relu), transferts, besoins signalés et traités, scans de lot. |
| `periodes.py` | fin de mois (dossiers, règlements, inventaire tournant avec recomptage, ajustement, brouillons de la période, **clôture**, lectures de la direction, invariants) ; trimestre (matière « (stress) » — au mètre un trimestre sur deux —, qualité et recette, version de recette et prix sur les éléments d'essai, désactivation d'essai, poste de frais, cours) ; année (plans d'essai refaits, croissance, unité de titrage, compte atelier, code remis à zéro, **sauvegarde puis restauration sur une base à part**, exports et documents de l'année, contrôles lus). |
| `erreurs.py` | chaque mercredi, deux ou trois erreurs humaines : date future, date 2006, période close, version périmée, double validation, plus que le stock, lot inconnu, hors droits, deux postes, inventaire en double — chacune **doit** être refusée. |
| `verifications.py` | fins de mois : `GET /controles/soldes` et le même recompte en SQL, Entré − Sorti = Reste, `GET /stock` contre la somme SQL des soldes et des fils montés (net, quarantaine, machine, disponible), échéancier contre les factures et frais non réglés, **vérificateur V1 (`verification_chiffres.py`) joué en mémoire** ; fin d'année : restauration de la sauvegarde sur `gestion_mp_pro_stress_restaure_essai` et comptes de lignes. |
| `simulateur.py` | la boucle des jours ouvrés (jamais le dimanche, samedi léger), les rendez-vous, le dump `annee-N.dump` par année simulée, la reprise. |

Classes d'anomalie : `erreur_500` (CERTAIN), `refus_inattendu` / `refus_manquant` (PROBABLE,
jusqu'à l'analyse), `lenteur` (> 1 s PRÉSENTATION, > 3 s PROBABLE), `invariant` (PROBABLE jusqu'à
l'analyse), `controle_referentiel` (QUESTION MÉTIER : un contrôle qui vise un référentiel de
Mohamed, consigné, jamais corrigé par une donnée), `exception` (GENERATEUR : faute du simulateur).

Réglage changé sur la copie (un réglage, pas un référentiel) : `seuil_approbation` 0 → 300 000 MAD,
pour que l'approbation de la direction soit jouée. Le stock de départ est posé par la direction en
opération « stock d'ouverture » (un à deux mois de consommation par matière consommée).

## 2. Ce qui a été rejoué

_(rempli à la fin de la simulation)_

## 3. Anomalies

_(rempli à la fin de la simulation)_

## 4. Correctifs

### C1 — La facture d'un brouillon de réception supprimé restait due (CERTAIN, corrigé)

Trouvé dès la première année simulée, confirmé par deux chemins indépendants : le recompte SQL
du simulateur (« factures écran 17 / SQL 16 ») et le vérificateur V1 (« facture 9 due : dans
l'échéancier sans être due »). Fait : le 11/12/2026 les achats saisissent un brouillon avec sa
facture INV-2612-873 (5 279,96 USD) ; le 14/12 ils suppriment le brouillon (camion refait). La
facture restait en base, portée par aucune réception ; `calcul.suivi.factures_dues` ne connaît
que les factures portées par une réception (brouillon → « pas encore due », toutes annulées →
« écartée ») : celle que **rien** ne porte était comptée **due**, à l'échéance, dans l'échu et
les totaux. Même chose si le brouillon est corrigé avec un autre numéro, ou si la facture d'une
réception validée est détachée (`numero: ""`) ou renumérotée : l'ancienne restait due.

Correctif (`services/factures.oublier_si_orpheline`, appelé par `receptions.supprimer`,
`receptions.modifier`, `receptions_facture.completer_facture`) : la facture que la réception
portait seule disparaît avec elle quand rien d'autre ne la porte — ni réception, ni dossier
d'importation (même annulé), pas réglée ; journal « facture oubliée ». Essai
`tests/test_factures_brouillon_supprime.py` (3 cas : échoue avant, passe après). Aucune décision
de Mohamed touchée (I3/I23 : une facture reste portée par ses réceptions et son dossier).

## 5. Questions pour Mohamed

_(rempli à la fin de la simulation)_
