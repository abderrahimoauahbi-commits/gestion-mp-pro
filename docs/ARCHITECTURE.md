# Gestion MP PRO — architecture technique

Document destiné au service informatique et aux équipes de réalisation : comment Gestion MP PRO
est construit, où se trouve chaque chose, quelles règles le code respecte, pourquoi ces choix,
et comment le vérifier. Il complète `MODELE-DONNEES.md` (schéma), `API-PRO.md` (routes),
`ECRANS-PRO.md` (écrans) et `LOTS-DE-TRAVAIL.md` (réalisation). Le métier repris est décrit
dans `docs/heritage/` ; PRO le reprend à l'identique, prouvé par la parité de calcul.

Sommaire : 1. Vue d'ensemble · 2. Choix structurants · 3. Arborescence · 4. Flux d'une requête ·
5. Sécurité · 6. Données, transactions, concurrence · 7. Moteur de calcul · 8. Numérotation,
dates, période close · 9. Conventions · 10. Écran · 11. Documents et exports · 12. Tâches de
fond · 13. Exploitation · 14. Coexistence et comparaison avec Gestion MP · 15. Vérification ·
16. Configuration · 17. Décisions de conception tranchées · 18. Limites et risques.

---

## 1. Vue d'ensemble

```
 Poste du bureau (1366×768)      Téléphone de l'atelier (PWA)        Poste local (Mac)
          │                                │                              │
          └──────────── HTTPS (Caddy : HSTS, CSP) ─────────────┘   http://127.0.0.1:8050
                                   │  cookie de session + en-tête X-Gestion-MP-PRO
                                   ▼
        FastAPI (uvicorn, 2 processus) — gestion_mp_pro
          api/ (routes minces, schémas)  →  services/ (métier, transactions)  →  calcul/ (moteur pur)
          securite.py (sessions, droit(), sans_prix, journal)   taches/ (un seul porteur)
          documents/ (Jinja2 → HTML A4)   exports/ (openpyxl)
                                   │  SQLAlchemy 2 (typé) / psycopg 3
                                   ▼
        PostgreSQL 16 — base gestion_mp_pro (Alembic)       ← reprise lecture seule ← base gestion_mp
          sauvegarde quotidienne relue (pg_dump -Fc) + pièces jointes + copie externe
```

| Couche | Technologie (versions minimales) | Rôle |
|---|---|---|
| Écran | React 19, TypeScript 5 strict, Vite 7, React Router 7, TanStack Query 5 | ≈ 26 écrans de bureau, 11 écrans d'atelier, système de composants maison |
| API | FastAPI ≥ 0.115, Pydantic 2, uvicorn | 245 routes typées (entrée **et** sortie), OpenAPI `/api/docs` |
| Métier | Python 3.12, paquet `gestion_mp_pro` | `services/` (un module par domaine), `calcul/` (moteur sans base) |
| Données | SQLAlchemy 2 (`Mapped[...]`), psycopg 3, PostgreSQL 16, Alembic | 71 tables, `NUMERIC`, CHECK, FK, index, verrous, `version` |
| Documents | Jinja2, segno (QR), openpyxl | bon de commande anglais A4, étiquettes QR, feuille de comptage, bilan |
| Exploitation | Docker Compose (postgres, application, Caddy), systemd ; poste Mac : launchd + copie figée | `/api/sante`, sauvegardes relues, journaux |

Aucun service externe ni abonnement : tout tourne sur le serveur de l'usine (ou le Mac).

---

## 2. Choix structurants et leurs raisons

| # | Choix | Raison |
|---|---|---|
| C1 | Code et vocabulaire **en français**, au plus près du métier (`matiere`, `ordre`, `dossier`, `contrepasser`) ; anglais seulement pour les mots-clés des bibliothèques | Le service informatique connaît GMAO PRO et Gestion MP, écrits ainsi ; un seul vocabulaire de l'écran à la base (REGLES-ECRAN § 5) |
| C2 | **Le métier de Gestion MP est repris à l'identique** ; le moteur calcule en `float` sur des valeurs lues en `NUMERIC` | Parité prouvée sur l'année d'essai ; deux audits et 292 essais valident ce métier |
| C3 | Trois couches serveur strictes : `api/` (HTTP seulement), `services/` (transactions et règles, sans HTTP), `calcul/` (fonctions pures sur des `dataclasses`, sans base) | Testabilité (essais du moteur sans base, essais de services sans HTTP) ; fin des routes de 95 lignes (R4) |
| C4 | Le moteur de Gestion MP **découpé** en modules par domaine, chaque fonction ≤ 60 lignes, sans changer un calcul | `moteur.py` de 3 760 lignes, `controler()` de 869 lignes (R3) |
| C5 | Données : tout ce qui vivait dans le journal ou du JSON devient colonnes et tables ; ids partout ; devises en FK ; énumérations avec CHECK ; `version` | Fragilité relevée (DONNEES § 14 n° 17-19) |
| C6 | **Alembic**, révisions linéaires contiguës, migration initiale propre, aucune révision n'importe le code applicatif | Étapes trouées et migrations dépendantes du code vivant (DONNEES § 14 n° 1-3) |
| C7 | **Le serveur décide** : `droit(...)` sur chaque route, matrice générée et testée route par route ; filtre des prix générique à toute profondeur | Gestion MP filtrait à la main (20 appels : un oubli = une fuite, R8) |
| C8 | Quatre rôles : direction, achats, alimentation, **administrateur technique** sans accès métier | PLAN.md ; standard GMAO PRO ; l'informatique ne lit pas les prix |
| C9 | Une convention d'erreur unique (`{detail, code}`, 422/409/404/403/401), jamais de 500 pour une saisie | Codes hétérogènes, 500 sur saisies (API B.13-9/10) |
| C10 | Numéros sans trou donnés à l'envoi/validation ; documents numérotés jamais supprimés | M65 |
| C11 | Écran sur le système de composants de GMAO PRO **avec** les dix arbitrages de `AMELIORATIONS-PRO.md` partie 4 au profit des exigences de Mohamed | Le standard s'applique à la forme du code, le comportement reste celui exigé |
| C12 | Documents imprimés **rendus par le serveur** (Jinja2), pas en React | Décision du coordinateur : un seul rendu pour l'écran, le PDF et les essais (texte lisible par l'essai « aucun prix ») ; fin du HTML en f-strings (R4) |
| C13 | Aide et notice d'**une seule source** (`frontend/src/aide.json`) | Mode d'emploi en 595 lignes de JSX (R19, A7) |
| C14 | Deux exploitations : serveur (Docker Compose + Caddy ou systemd) et poste Mac (launchd + copie figée) | Le Mac de l'usine reste la première cible ; le serveur est la cible « Pro » |
| C15 | PRO **coexiste** avec Gestion MP sur le même Mac sans rien partager, et une reprise rejouable + un comparateur prouvent qu'ils disent les mêmes chiffres | Exigence du propriétaire (8 octobre) : pouvoir comparer les deux versions |
| C16 | Horloge injectable (`services/horloge.py`) ; fuseau passé à PostgreSQL et à `zoneinfo`, **jamais** au processus | `config.py` de Gestion MP changeait `TZ` à l'import (R17) ; essais dépendants de la date du jour |
| C17 | Journal du serveur par `logging` structuré, une ligne par requête (durée, utilisateur, statut, identifiant) | 14 `print` (R18) |

---

## 3. Arborescence

Plafonds : **400 lignes par fichier, 60 lignes par fonction** (ruff `PLR0915`/`C901`, eslint
`max-lines`, `max-lines-per-function`), sauf fichiers générés et gabarits.

```
gestion-mp-pro/
├── README.md                       démarrer, développer (make verifier), documents, API (/api/docs)
├── Makefile                        installer, verifier, essais, parite, comparer, construire, docker
├── .gitignore  .dockerignore  .editorconfig  .pre-commit-config.yaml (ruff, prettier, eslint)
├── backend/
│   ├── pyproject.toml              paquet gestion-mp-pro, Python ≥ 3.12, bornes minimales, [build-system]
│   ├── requirements.lock           versions figées (uv pip compile)
│   ├── alembic.ini
│   ├── gestion_mp_pro/
│   │   ├── __init__.py             __version__
│   │   ├── main.py                 application, cycle de vie, middlewares, routeurs, écran statique (poste Mac)
│   │   ├── config.py               Reglages(BaseSettings) : GESTIONMPPRO_* (§ 16), lu une fois
│   │   ├── db.py                   moteur, fabrique de sessions, dépendance `session`, verrous consultatifs nommés
│   │   ├── securite.py             sessions, appareils, acteur, droit(), matrice, sans_prix, journal(), notifier()
│   │   ├── journalisation.py       configuration de logging (format, niveau, rotation), middleware de trace
│   │   ├── modeles/
│   │   │   ├── __init__.py         importe tout (métadonnées complètes pour Alembic)
│   │   │   ├── base.py             Base, MetaData(naming_convention), colonnes communes (version, cree_le…),
│   │   │   │                       fk(), enfants()/vers(), completer_le_schema() (CHECK _enum et _nombre)
│   │   │   ├── types.py            QUANTITE, PRIX, MONTANT, COURS, TAUX, POURCENTAGE, MESURE… ; arrondir(valeur, categorie)
│   │   │   ├── enums.py            les 36 énumérations (MODELE-DONNEES § 2)
│   │   │   ├── longueurs.py        longueurs partagées modèle ↔ schémas
│   │   │   ├── socle.py            utilisateur, session (modèle SessionOuverte), tentative, appareil, journal,
│   │   │   │                       parametre(_historique) et CLES_REGLAGES (57 clés), compteur
│   │   │   ├── communication.py    notification(_lecture), courriel, tache_execution, sauvegarde
│   │   │   ├── referentiels.py     devise(_cours), composition, type_fil, titrage, couleur, role_nomenclature,
│   │   │   │                       code_douanier, magasin, poste_frais, motif
│   │   │   ├── catalogue.py        fournisseur, matiere
│   │   │   ├── qualites.py         qualite, qualite_poids, qualite_saison, recette, recette_version(_ligne/_poids),
│   │   │   │                       plan_version(_saison)
│   │   │   ├── metiers.py          metier, metier_etage, montage, montage_evenement
│   │   │   ├── stock.py            lot, solde, mouvement
│   │   │   ├── achats.py           commande, commande_ligne, commande_version(_ligne), commande_decision, facture
│   │   │   ├── receptions.py       reception, reception_ligne
│   │   │   ├── production.py       ordre, ordre_qualite, ordre_ligne, ordre_prevu
│   │   │   ├── operations.py       operation, operation_ligne
│   │   │   ├── inventaires.py      inventaire, inventaire_critere, inventaire_matiere, inventaire_ligne
│   │   │   ├── importations.py     dossier, dossier_ligne, dossier_frais, dossier_frais_part
│   │   │   ├── suivi.py            reclamation, signalement, piece_jointe, indicateur_jour
│   │   │   ├── reprise.py          reprise_correspondance, reprise_execution
│   │   │   └── recherche.py        normaliser() (règle unique, la même que l'écran), écouteur before_flush de
│   │   │                           texte_recherche, recalculer_table() après une écriture SQL directe
│   │   ├── migrations/
│   │   │   ├── env.py  script.py.mako
│   │   │   └── versions/0001_schema_initial.py  0002_semences.py  (puis 0003…, contiguës)
│   │   ├── api/
│   │   │   ├── __init__.py         ROUTEURS (ordre d'inclusion), tags OpenAPI
│   │   │   ├── erreurs.py          Refus(code, http, detail), gestionnaires (validation traduite, 500 tracé), CODES
│   │   │   ├── dependances.py      session, acteur, date_reference, pagination, version_attendue
│   │   │   ├── communs.py          Page[T], Message, schémas partagés (MatiereCourte, LotCourt, Personne…)
│   │   │   ├── systeme/            routes.py, schemas.py        (§ 1.1 de API-PRO)
│   │   │   ├── comptes/            routes.py, schemas.py        (1.2)
│   │   │   ├── reglages/           routes.py, schemas.py        (1.3)
│   │   │   ├── exploitation/       routes.py, schemas.py        (1.4)
│   │   │   ├── journal/            routes.py, schemas.py        (1.5)
│   │   │   ├── notifications/      routes.py, schemas.py        (1.6, recherche comprise)
│   │   │   ├── classification/  fournisseurs/  matieres/  qualites/  metiers/
│   │   │   ├── stock/  operations/  inventaires/  ordres/  production/  plan_achat/
│   │   │   ├── commandes/  receptions/  reclamations/  importations/  pilotage/  suivi/
│   │   │   ├── reprise/            état et rafraîchissement du miroir de Gestion MP (243–244)
│   │   │   └── documents/          routes.py (HTML imprimables : bon, étiquettes, feuille, bilan)
│   │   ├── services/               un module par domaine ; transactions ; aucun objet HTTP
│   │   │   ├── horloge.py          aujourd_hui(), maintenant() (injectables), FUSEAU (zoneinfo)
│   │   │   ├── audit.py            écouteur avant/après, journal(), historique(objet, id)
│   │   │   ├── numerotation.py     numero(serie, jour) sous FOR UPDATE ; format SERIE-AAAA-NNNN, NN/AA
│   │   │   ├── periode.py          date_permise(), fin_de_periode_close(), cout_hors_periode_close(), clore()
│   │   │   ├── installation.py     migrer() (Alembic sous verrou), premier compte, vérification des semences
│   │   │   ├── notifications.py    notifier(role|personne, texte, lien, ton, cle) ; règles d'émission
│   │   │   ├── recherche.py        recherche globale filtrée par rôle (normaliser() de modeles/recherche.py)
│   │   │   ├── comptes.py          comptes, codes (scrypt), sessions, tentatives, visages
│   │   │   ├── appareils.py        enrôlement, jetons, révocation
│   │   │   ├── reglages.py         lire, écrire (bornes, ordres), historique ; registre_reglages.py (les clés de CLES_REGLAGES)
│   │   │   ├── devises.py          cours, historique ; taux(devise)
│   │   │   ├── classification.py   valeurs, rôles de nomenclature
│   │   │   ├── fournisseurs.py     fiches, usages, délai mesuré
│   │   │   ├── matieres.py         fiches, usages, composition de référence, classement
│   │   │   ├── tableur_matieres.py modèle, aperçu, application (mêmes règles que la fiche)
│   │   │   ├── qualites.py         qualités, recettes (100 %), versions, plan (versions)
│   │   │   ├── metiers.py          métiers, étages, montage (effet, alerte 30 j, événement)
│   │   │   ├── stock.py            LE chemin d'écriture : lot_ou_creer, ecrire, transferer, contrepasser,
│   │   │   │                       couvert_a_sa_date, suspension par inventaire
│   │   │   ├── conversions.py      kg ↔ bobines ↔ palettes (poids mesuré du lot, sinon catalogue)
│   │   │   ├── lots.py             soldes, fiche de lot, scan, disponibles, statut calculé, étiquettes
│   │   │   ├── operations.py       brouillons, blocages, validation, annulation ; table des droits par type
│   │   │   ├── brouillons.py       « À valider », « Tout valider » (ordre des dates)
│   │   │   ├── inventaires.py      ouverture (périmètre), comptages, lots trouvés, validation, abandon, tournant
│   │   │   ├── ordres.py           proposition FIFO, brouillons, blocages, validation (verrou ORDRES), annulation
│   │   │   ├── production.py       plan global, réalisé, besoins détaillés
│   │   │   ├── plan_achat.py       plan d'achat, préparation par fournisseur
│   │   │   ├── commandes.py        brouillons, envoi, prix, expédition, solde, réouverture, recaler_soldes
│   │   │   ├── approbation.py      garde-fou du montant, versions parties, décisions
│   │   │   ├── receptions.py       brouillons, recalage, blocages, validation, annulation, lot interne
│   │   │   ├── factures.py         facture d'une réception, échéance, règlement
│   │   │   ├── reclamations.py     ouverture, réponse, clôture, réouverture
│   │   │   ├── importations.py     dossiers, rattachement, lignes, cours, frais, parts figées, clôture, annulation
│   │   │   ├── analyse_revient.py  coût de revient par axe, coût d'une qualité
│   │   │   ├── pilotage.py         cockpit, valorisation, prix, opportunités, contrôles, performance
│   │   │   ├── suivi.py            signalements
│   │   │   ├── pieces.py           pièces jointes (types, taille, empreinte, chemin relatif, retrait logique)
│   │   │   ├── echeancier.py       factures et frais dus, règlements
│   │   │   ├── indicateurs.py      photo du jour, historique
│   │   │   ├── bilan.py            bilan du mois (données)
│   │   │   ├── courriel.py         contenu du lundi, file, envoi SMTP
│   │   │   ├── sauvegarde.py       pg_dump relu, pièces, copie, purge, restauration (garde les pièces, migre)
│   │   │   └── donnees_moteur.py   chargeur Donnees (requêtes groupées), cache par signature, charger_au(jour)
│   │   ├── calcul/                 moteur pur : aucune base, aucune date « du jour » implicite
│   │   │   ├── modele.py           dataclasses du moteur (Parametres, Article, Mouvement… = CALCULS § 1)
│   │   │   ├── constantes.py       MOIS, JOURS_PAR_MOIS, POUSSIERE, statuts, tiers, points du score…
│   │   │   ├── outils.py           arrondi (ARRONDI d'Excel), dates, mois glissants, clamp
│   │   │   ├── a_la_date.py        rejouer les données au soir d'une date
│   │   │   ├── classification.py   lire et composer une référence de fil
│   │   │   ├── plan.py             m2_du_mois, plan_mensuel, plan_en_vigueur, m2_passe
│   │   │   ├── nomenclature.py     nomenclature, poids_du_role, controle_recettes
│   │   │   ├── besoins.py          besoins mensuels, besoins passés, besoin sur fenêtre, coefficient de réalisation
│   │   │   ├── stock/              etat_stock découpé : __init__ (assemblage), consommation.py, couverture.py,
│   │   │   │                       machine.py (sur les métiers), projete.py, statuts.py, classes.py (ABC/XYZ), ligne.py
│   │   │   ├── achats.py           pas_partie, reste_a_livrer, reçu net par ligne
│   │   │   ├── plan_achat.py       quantités, arrondis au conditionnement, tiers, urgences, budget
│   │   │   ├── valorisation.py     couts_du_journal (CMUP), cmup_par_reference, valorisation
│   │   │   ├── prix.py             prix constatés, coûts rendus, comparer, opportunités, historique, matrice
│   │   │   ├── fournisseurs.py     performance des réceptions (OTIF), score, devises pratiquées
│   │   │   ├── receptions.py       pesées, écarts de bobine, évolution des bobines
│   │   │   ├── lots.py             stock par lot, lots disponibles, traçabilité
│   │   │   ├── production.py       consommation par ordre, prévu, réalisé par qualité
│   │   │   ├── importations.py     revient d'un dossier, TVA et droits attendus, aberrants, écart de facture
│   │   │   ├── inventaire.py       écarts valorisés
│   │   │   ├── pilotage.py         coût matière annuel, cockpit, concentration des devises
│   │   │   └── controles/          base.py (Controle, gravités, GARANTIS, registre), synthese.py,
│   │   │                           recettes.py (C01), production.py (C02 C03 C25 C31 C32),
│   │   │                           stock.py (C04 C12 C14 C16 C18 C20 C26 C27 C37),
│   │   │                           catalogue.py (C05 C07 C09 C10 C15 C17 C19 C21 C33 C38),
│   │   │                           achats.py (C06 C08 C13 C30), devises.py (C11),
│   │   │                           metiers.py (C22 C23 C24), importations.py (C28 C29 C34 C35 C36)
│   │   ├── taches/
│   │   │   ├── planificateur.py    porteur unique (verrou consultatif TACHES), boucle 15 min, isolement des échecs
│   │   │   ├── sauvegarde_du_jour.py  photo_du_jour.py  courriels.py  purges.py  alertes.py (notifications quotidiennes)
│   │   ├── documents/
│   │   │   ├── rendu.py            environnement Jinja2 (autoescape), filtres fr/en, société (papier à en-tête)
│   │   │   ├── anglais.py          traductions du bon (conditionnements, dates « 08 Oct 2026 »)
│   │   │   ├── qr.py               segno → SVG
│   │   │   └── gabarits/  _papier_a_en_tete.html  _impression.css  bon_commande.html  etiquettes.html
│   │   │                  feuille_comptage.html  bilan.html
│   │   ├── exports/
│   │   │   ├── classeur.py         conventions communes (en-tête, formats, largeurs, volets, filtre, dates, `=` en texte)
│   │   │   ├── referentiels.py  achats.py  receptions.py  stock.py  ordres.py  importations.py
│   │   │   └── pilotage.py  journal.py  echeancier.py  bon_fournisseur.py
│   │   └── reprise/
│   │       ├── __main__.py         python -m gestion_mp_pro.reprise --source … --mode …
│   │       ├── source.py           connexion lecture seule, photo REPEATABLE READ, empreinte
│   │       ├── normalisation.py    arrondis à l'échelle des colonnes, rapport des arrondis
│   │       ├── personnes.py        noms → comptes (historiques au besoin)
│   │       ├── referentiels.py     référentiels (correspondances, mise à jour)
│   │       ├── activite.py         lots, mouvements, documents (ids gardés), soldes recalculés
│   │       ├── journal_en_tables.py plan, soldes à la main, décisions, annulations, montages
│   │       ├── pieces.py           copie des fichiers, empreintes
│   │       ├── compteurs.py        compteurs et séquences recalés
│   │       └── controle.py         comptes, sommes, empreintes, rapport
│   ├── tests/                      pytest (base gestion_mp_pro_essai) — voir PLAN-DE-RECETTE-PRO § 1
│   │   ├── conftest.py  fabrique.py  horloge.py  matrice_droits.csv
│   │   ├── moteur/                 un fichier par module de calcul/ (Donnees écrites à la main)
│   │   ├── test_securite.py  test_matrice_droits.py  test_prix_masques.py  test_erreurs.py
│   │   ├── test_migrations.py  test_catalogue_api.py  test_<domaine>.py …  test_concurrence.py
│   │   └── test_reprise.py  test_documents.py  test_exports.py  test_sauvegarde.py  test_robustesse.py
│   └── essais/
│       ├── verification_chiffres.py   recalcul indépendant (n'importe pas gestion_mp_pro)
│       ├── parite_gestion_mp.py       parité statique, par l'API, dynamique (PLAN-DE-RECETTE § 7)
│       ├── gestion_mp_calcul.py       côté Gestion MP : copie de comparaison_calcul (lancée par le Python de ~/gestion-mp)
│       ├── charge.py  concurrence.py
├── frontend/                       voir § 10 et ECRANS-PRO.md
│   ├── package.json  tsconfig.json  vite.config.ts  eslint.config.js  .prettierrc.json  index.html
│   ├── public/  manifest.webmanifest  sw.js  icone.svg  icone-180.png  icone-192.png  icone-512.png
│   └── src/
│       ├── main.tsx  App.tsx  routes.ts (registre unique des écrans)  aide.json
│       ├── lib/      api.ts  requetes.ts (TanStack Query)  session.tsx  droits.ts  heure.ts  format.ts
│       │             recherche.ts  unites.ts  teintes.ts  adresse.ts  statuts.ts  types.gen.ts  types.ts
│       ├── styles/   jetons.css (seules couleurs du projet)  base.css  impression.css
│       ├── composants/  coque/  mise-en-page/  tableaux/  saisie/  retour/  graphiques/  documents/  atelier/
│       │                (chaque composant : X.tsx, X.module.css, X.test.tsx)
│       └── pages/    connexion/ accueil/ cockpit/ stock/ sorties/ production/ plan-achat/ commandes/
│                     receptions/ importations/ inventaire/ operations/ catalogue/ qualites/ metiers/
│                     analyse/ reglages/ administration/ aide/ compte/ atelier/
├── deploiement/
│   ├── Dockerfile                  étape Node 22 (build écran) + Python 3.12 slim, postgresql-client 16, non root, HEALTHCHECK
│   ├── docker-compose.yml          base (postgres:16), application, https (caddy:2) ; volumes donnees, sauvegardes, pieces, caddy
│   ├── Caddyfile                   reverse_proxy application:8050, HSTS, nosniff, CSP, Referrer-Policy
│   ├── exemple.env                 toutes les GESTIONMPPRO_* commentées
│   ├── gestion-mp-pro.service      systemd (EnvironmentFile, Restart=always, NoNewPrivileges, ProtectSystem=full)
│   └── mac/
│       ├── fr.usine.gestion-mp-pro.plist   launchd : démarrage à l'ouverture de session, KeepAlive, journaux
│       ├── creer-raccourci.sh      ~/Desktop/Gestion MP PRO.app (ouvre http://localhost:8050, démarre au besoin)
│       ├── installer.sh            base, rôle, venv, construction, launchd, raccourci (idempotent)
│       └── GestionMPPRO.icns  icone.svg
├── scripts/
│   ├── demarrer.sh                 copie figée (git archive + dist construit) puis uvicorn ; écrit VERSION
│   ├── arreter.sh  restaurer.sh (tout ou rien, pièces comprises, migre)  sauvegarder.sh
│   ├── generer_types.sh            openapi.json → frontend/src/lib/types.gen.ts
│   └── generer_notice.py           aide.json → docs/NOTICE.md
├── outils/
│   ├── comparer_avec_gestion_mp.py  comparaison chiffre par chiffre GMP (8030) / PRO (8050) (§ 14)
│   ├── gestion_mp_extraire.py      calcul canonique côté Gestion MP (lancé par ~/gestion-mp/.venv, lecture seule)
│   ├── vider_activite.py           garde les référentiels (liste des tables dérivée des modèles), base vide de référence
│   ├── routes_ecran.py             chaque appel de l'écran vise une route de l'OpenAPI
│   └── verifier_heritage.py        les 292 preuves de Gestion MP sont citées par un essai PRO
├── essais/                         scenario_complet.py, recette_navigateur.js, comptes-essai.md, resultat-*.txt
└── docs/                           ARCHITECTURE, MODELE-DONNEES, API-PRO, ECRANS-PRO, LOTS-DE-TRAVAIL,
                                    CAHIER-DES-CHARGES, EXPLOITATION, NOTICE (générée), RECETTE,
                                    COMPARAISON-GESTION-MP, PLAN, heritage/
```

### 3.1 Responsabilités par couche

| Couche | Fait | Ne fait jamais |
|---|---|---|
| `api/<domaine>/routes.py` | déclare chemin, droits, schémas, `summary` ; convertit les paramètres ; appelle **un** service ; rend le schéma de sortie | SQL, règle métier, `commit` explicite (la dépendance `session` le fait), HTML |
| `api/<domaine>/schemas.py` | Pydantic 2 (`model_config = ConfigDict(extra="forbid")` en entrée), bornes et longueurs (depuis `modeles/longueurs.py`), exemples | logique |
| `services/<domaine>.py` | règles, refus (`Refus`), verrous, écriture, journal, notifications ; reçoit une `Session` SQLAlchemy et l'`Acteur` | importer FastAPI, lire `Request` |
| `calcul/` | fonctions pures sur `Donnees` ; mêmes formules que Gestion MP | lire la base, l'horloge, les réglages (reçus en paramètres) |
| `modeles/` | tables, contraintes, relations (`lazy="raise"` par défaut : tout chargement est explicite) | méthodes métier lourdes |
| `taches/` | planification, appels de services | règle métier propre |
| `documents/`, `exports/` | mise en forme de données déjà calculées par un service | calcul |

---

## 4. Flux d'une requête

Exemple : `POST /api/receptions/42/valider` par la responsable des achats.

1. **Caddy** (Docker) termine TLS, ajoute HSTS/CSP, transmet à `application:8050`.
2. **Middleware `trace`** (`journalisation.py`) : identifiant de requête (16 hex) → en-tête
   `X-Requete`, chronomètre.
3. **Middleware `protections`** (`main.py`) : méthode d'écriture sous `/api` sans
   `X-Gestion-MP-PRO: 1` → 403 `entete_absente` (avec les en-têtes de sécurité) ; base pas à
   `head` ou restauration en cours → 503.
4. **Routage** FastAPI → `api/receptions/routes.py: valider()`. Dépendances : `session` (une
   session SQLAlchemy, transaction ouverte), `acteur` (cookie → empreinte SHA-256 → `session`
   non expirée, compte actif ; `vu_le` mis à jour au plus une fois par minute), `droit(D, A)`
   → 401/403 sinon. Corps validé par `ValidationVersion` (extra interdits) → 422 traduit.
5. **Service** `services.receptions.valider(s, acteur, id, version)` : `SELECT … FOR UPDATE`
   de la réception (404 sinon), contrôle `version` (409), `date_permise`, blocages (bons
   verrouillés par id croissant, excédent, approbation), numéro `REC-AAAA-NNNN`
   (`numerotation.numero`), lots (`stock.lot_ou_creer`, lot interne), écritures
   (`stock.ecrire` : verrou du solde, suspension d'inventaire, couvert à sa date, cours figé),
   `commandes.recaler_soldes`, `journal(...)` avec avant/après, `notifier(...)`.
6. **Fin de la dépendance `session`** : `commit` (ou `rollback` sur toute exception) ;
   `Refus` → réponse `{detail, code}` au code prévu ; autre exception → 500 tracé.
7. **Filtre des prix** (`securite.sans_prix`, classe de route posée sur **tous** les routeurs) :
   rôle hors {D, A} → clés monétaires mises à `null` à toute profondeur.
8. **Middleware `trace`** : en-têtes `Cache-Control: no-store`, `X-Heure-Serveur` ; une ligne de
   journal serveur `requete=… utilisateur=… role=… POST /api/receptions/42/valider 200 38 ms`.
9. **Écran** : la mutation TanStack Query invalide toutes les requêtes ouvertes (rafraîchissement
   global), le toast « Réception REC-2026-0318 validée : 3 lots entrés. » s'affiche.

---

## 5. Sécurité

### 5.1 Comptes, sessions, appareils

- Codes : `scrypt` (n = 2¹⁴, r = 8, p = 1, sel 16 octets) ; alimentation **exactement 4
  chiffres** (saisie automatique au 4ᵉ chiffre, D10), achats et direction ≥ 8 caractères,
  administrateur ≥ 12. Anti-force brute par identifiant (5 échecs puis 30 s × 2ⁿ, 15 min au
  plus) + limitation globale par adresse (429).
- Session : jeton `secrets.token_urlsafe(32)` dans le cookie **`gestion_mp_pro_session`**
  (nom distinct de Gestion MP : les cookies ne sont pas isolés par port), `HttpOnly`,
  `SameSite=Lax`, `Secure` derrière HTTPS ; en base la seule empreinte. Durée
  `GESTIONMPPRO_SESSION_JOURS` (30). Changement de code, désactivation, révocation d'appareil
  → sessions fermées.
- Appareils enrôlés (téléphones de l'atelier) : QR d'enrôlement à usage unique (15 min) depuis
  Administration › Appareils ; cookie d'appareil `gestion_mp_pro_appareil` (400 jours). Les
  « visages » (choisir son nom) ne s'affichent que sur le poste local (`127.0.0.1`/`::1`) ou un
  appareil enrôlé ; ailleurs on tape son identifiant.
- Installation : `POST /installation` une seule fois (409 ensuite), crée la direction.

### 5.2 Droits

- `droit(*roles)` : dépendance qui porte ses rôles (`.roles`). **Pas de passe-droit implicite** :
  la direction est nommée dans chaque route qui lui est ouverte, l'administrateur n'est nommé
  que dans les routes techniques. La matrice (route × rôle → code attendu) est générée
  (`securite.matrice()`), versionnée (`tests/matrice_droits.csv`) et rejouée entièrement par
  l'essai ; un essai structurel échoue si une route hors liste publique n'a pas de `droit`.
- Droits fins dans les services (tables uniques) : type d'opération × rôle
  (`services/operations.py: DROITS`), libération de quarantaine (D, A), mise en quarantaine
  (D, A, L), approbation (D), montage (D, L).
- L'écran dérive son menu et ses gardes du **même** registre (`frontend/src/routes.ts` + rôles
  renvoyés par `/api/contexte`) ; un essai vitest vérifie que chaque entrée de menu d'un rôle
  appelle des routes que la matrice lui permet.

### 5.3 Prix jamais montrés à l'alimentation

Quatre barrières : (1) les routes chiffrées sont fermées à L (403) ; (2) le filtre générique
`sans_prix` met à `null` les clés de `CLES_MONETAIRES` à toute profondeur sur toutes les
réponses (classe de route par défaut des routeurs) ; (3) des schémas de sortie réduits pour L
(fournisseur, stock) ; (4) les documents, exports et messages d'erreur destinés à L sont
produits sans prix (contrôle par l'essai qui cherche montants et symboles monétaires). Ni
réglages, ni devises, ni cours pour L.

### 5.4 Réseau, en-têtes, fichiers

- Écoute `127.0.0.1` par défaut (poste Mac) ; exposition au réseau seulement derrière Caddy
  (HTTPS) ou par décision explicite (`GESTIONMPPRO_ECOUTE=0.0.0.0`, signalé en rouge dans
  Administration › Serveur quand HTTPS est absent).
- En-têtes : anti-falsification `X-Gestion-MP-PRO` sur toute écriture (déconnexion comprise) ;
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, CSP
  `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'`.
- Pièces jointes : types permis (PDF, images sauf SVG, texte, CSV, bureautique, zip), 20 Mo,
  nom assaini (aucun chemin), empreinte SHA-256, servies en `attachment`, chemin relatif.
- Recherche : `%` et `_` échappés ; aucune requête SQL concaténée (SQLAlchemy ou `text()`
  paramétré, vérifié par ruff `S608`).
- Exports : cellules commençant par `=`, `+`, `-`, `@` forcées en texte.
- Secrets uniquement par l'environnement (`.env` jamais versionné).

### 5.5 Audit

`journal` (avant/après JSONB) écrit dans la transaction du geste ; jamais modifié ; lisible par
D et T (Journal des actions, filtrable comme dans Gestion MP, plus `objet_id`) ; historique de
chaque fiche (`/api/historique/{objet}/{id}`) dans un onglet « Historique » de la fiche.

---

## 6. Données, transactions, concurrence

- Une session SQLAlchemy par requête, `autoflush=False`, `expire_on_commit=False`, isolation
  READ COMMITTED ; la cohérence repose sur les verrous ci-dessous. Connexions :
  `options=-c timezone=Africa/Casablanca -c statement_timeout=30000`, `pool_pre_ping`.
- Verrous consultatifs nommés (`db.VERROUS`, plage 7426201–7426209, distincte de Gestion MP) :
  `MIGRATION` (7426201), `TACHES` (7426202, porteur unique des tâches), `ORDRES` (7426203,
  numéros d'OF dans l'ordre des dates), `INVENTAIRE_GLOBAL` (7426204), `RESTAURATION` (7426205),
  `REPRISE` (7426206).
- Verrous de ligne : `solde` (le verrou du stock), `compteur`, document modifié/validé, bons
  d'une réception (par id croissant), fiche de référentiel, `metier_etage`.
- Verrou optimiste : `version` sur toutes les fiches et documents (MODELE-DONNEES § 1.2) ;
  409 `conflit_version` qui nomme l'auteur de la version courante (dernière ligne de journal).
- Écriture du stock : **un seul chemin** (`services/stock.py`), essai qui interdit `Mouvement(`
  ailleurs ; contre-passation datée comme l'original ; transfert en deux lignes liées.
- Montants : calculés en `Decimal`, arrondis une fois à l'écriture (`ROUND_HALF_UP`).
- Requêtes : chargements explicites (`selectinload`), aucune requête par ligne (essai qui compte
  les requêtes des listes : plafond par route) ; listes longues paginées par curseur.

---

## 7. Moteur de calcul

- **Entrée** : `Donnees` (dataclasses de `calcul/modele.py`, identiques à celles de Gestion MP,
  CALCULS § 1) construites par `services/donnees_moteur.py` en une dizaine de requêtes groupées.
  Les `Decimal` deviennent des `float` ; les clés textuelles du moteur (référence, code de
  qualité, nom de fournisseur, code de magasin) sont gardées **pour l'affichage**, mais versions
  de recette, plan et prévus sont reliés par id avant d'être traduits.
- **Cache** : par processus, clé = signature lue en base à chaque appel (`jour`, `max(journal.id)`,
  `max(mouvement.id)`, `max(parametre.modifie_le)`, `count(mouvement)`, `Σ solde.quantite`) ;
  jamais périmé, juste avec plusieurs processus (la signature est en base, pas en mémoire).
- **Date de référence** : `charger_au(jour)` = `calcul.a_la_date` (journal, réceptions, commandes,
  prix, ordres tronqués ; dossiers, catalogue et réglages d'aujourd'hui ; fil monté inconnu à une
  date passée), comme Gestion MP.
- **Méthode** : uniquement la méthode « corrigée » de Gestion MP. Les branches « classeur » ne
  sont **pas** reprises (DECISIONS P17) ; la parité avec le classeur reste prouvée par l'héritage.
- **Constantes** (`calcul/constantes.py`) : celles de REGLAGES § 8, chacune documentée ; aucune
  ne devient réglage sans décision (parité). Exception : la tolérance de TVA (5 %), le seuil C38
  (3), « dossier sans frais » (30 j) restent des constantes nommées.
- **Contrôles** : registre (`@controle("C08", gravite=…, garanti=…, lien=…)`), une fonction par
  contrôle, ordre numérique C01…C38, détail complet (plus de troncature silencieuse : la
  réponse dit « 200 premières sur 412 »), colonnes déclarées avec leur unité, une seule échelle
  pour « Écart (%) ».
- **Arrondi** : `calcul.outils.arrondi` = ARRONDI d'Excel (demi loin de zéro) ; même règle à
  l'affichage (`format.ts`).

---

## 8. Numérotation, dates, période close

- Séries `BC, REC, OF, OUV, RET, TRF, AJU, RFO, LOT, INV, RCL` : `SERIE-AAAA-NNNN` (année de la
  pièce) ; `DOS` : `NN/AA`. Numéro donné **à l'envoi** (BC) ou **à la validation** (REC, OF,
  OUV…RFO, LOT interne), dans la transaction (un refus l'annule) ; **à l'ouverture** pour INV,
  RCL, DOS (décision A10), ces documents ne se supprimant plus (abandon, annulation).
- Les numéros d'OF suivent les dates : validation sous le verrou `ORDRES`, refus d'une date
  antérieure au dernier ordre non brouillon (annulés compris, pour que les numéros restent
  dans l'ordre des dates).
- Dates permises : ≥ 2000-01-01, ≤ aujourd'hui (heure de l'usine), > `date_cloture` ; dites dès
  le brouillon (blocages). Période close : `PUT /periode-close` (direction, motif) ; le coût
  d'une marchandise entrée dans un mois clos ne change plus (`periode.cout_hors_periode_close`).

---

## 9. Conventions

### 9.1 Code serveur

- Python 3.12, typage complet (`mypy --strict` sur `services/` et `calcul/`), ruff
  (`E,F,W,I,UP,B,S,PL,C90,DTZ`, longueur 100) et `ruff format`. Docstring d'une ligne en
  français sur chaque module et fonction publique, avec la règle et sa source (« M65 »,
  « DECISIONS A8 »).
- Noms : modules et fonctions en français ; `routeur` (pas `router`) ; schémas en `PascalCase`.
- Refus : `raise Refus.etat("Ce bon est clos.", code="bon_clos")` (409), `Refus.saisie(...)`
  (422), `Refus.introuvable(...)` (404). Les messages de Gestion MP sont repris **mot pour mot**
  (`heritage/REGLES.md`), sauf correction de vocabulaire (REGLES-ECRAN § 5).
- Une anomalie trouvée = un essai de non-régression.

### 9.2 Code écran

TypeScript `strict`, ESLint (`js.recommended`, `typescript-eslint`, `react-hooks/rules-of-hooks`
en erreur, `exhaustive-deps`, `max-lines` 400, `no-restricted-syntax` contre `window.confirm` /
`alert`, `consistent-type-assertions` : pas de `as` hors tests), Prettier (110 colonnes, sans
point-virgule, guillemets simples), stylelint (aucune couleur hors `jetons.css`, aucun `style={{}}`
sauf mesure calculée). Types de l'API **générés** depuis l'OpenAPI (`types.gen.ts`).

### 9.3 Règle unique d'arrondi et d'affichage

Une fonction par grandeur dans `frontend/src/lib/format.ts`, reprise à l'identique par les
gabarits (`documents/rendu.py`, filtres Jinja2) et les formats Excel (`exports/classeur.py`) :

| Grandeur | Règle | Exemple |
|---|---|---|
| Arrondi | ARRONDI d'Excel (demi loin de zéro) sur la valeur brute, jamais d'arrondi en cascade | |
| Milliers, décimales | espace insécable U+00A0, virgule ; « − » ; jamais « -0 » ni « −0,0 % » | 17 398 184 |
| Kilos (bureau) | 1 décimale ; Excel `#,##0.0` | 1 234,5 kg |
| Kilos (téléphone) | entier ≥ 100 kg ; 1 décimale de 10 à 100 ; 2 sous 10 | 445 kg ; 52,4 kg ; 2,49 kg |
| Kilos commandés au kilo | entier | 5 029 kg |
| Mètres indicatifs | `≈ N ml` entier, kg ÷ densité, cuir/franges/ruban | 14,3 kg ≈ 1 020 ml |
| Montant | 0 décimale dans les tableaux et KPI (exact en infobulle) ; 2 décimales dans les documents, échéancier, dossiers ; « 17,4 M MAD » au-delà d'un million dans un KPI ; devise toujours dite | 1 234 MAD |
| Prix unitaire | 2 décimales ; jusqu'à 4 si 0 < \|p\| < 0,1 ; unité dite | 2,80 USD / kg ; 0,0011 USD / ml |
| Cours | 4 décimales | 10,0500 |
| Pourcentage | 1 décimale, espace insécable | 12,5 % |
| Poids de bobine | jusqu'à 4 décimales sans zéros | 2,4952 kg / bobine |
| m² | entier | 1 200 m² |
| Dates | JJ/MM/AAAA ; horodatage JJ/MM/AAAA HH:MM ; « aujourd'hui », « hier » selon l'heure du serveur | 08/10/2026 |
| Vide | « — » | |
| Devises | jamais additionnées : « 61 888 USD · 53 132 EUR » | |

---

## 10. Écran

### 10.1 Organisation

- `App.tsx` : `QueryClientProvider`, `Session` (lit `/api/contexte`), routeur. Branches : `/connexion`
  et `/installation` hors coque ; `/atelier/*` hors coque (téléphone) ; tout le reste dans `Coque`.
- `routes.ts` : **registre unique** des écrans (chemin, titre = libellé du menu, groupe, rôles,
  clé d'aide, onglets). Menu, fil d'Ariane, garde de route, aide contextuelle et essais en sont
  dérivés. Une adresse interdite renvoie à l'accueil du rôle avec le bandeau « L'écran demandé
  (…) est réservé à un autre rôle ».
- Arrivée : direction → `/cockpit` ; achats → `/accueil` ; alimentation → `/atelier` au téléphone
  (≤ 700 px), `/accueil` au bureau ; administrateur → `/administration`.
- Données : TanStack Query, une clé par route d'API ; **invalidation globale** après chaque
  mutation réussie ; relance sur statut (5xx, réseau), jamais sur 4xx ; « Pas de réseau » dit
  comme tel. Heure de l'usine par `X-Heure-Serveur`.
- Fiches : **adresse stable + fenêtre** (A5) : `/commandes/12` rend la liste des commandes et
  la fiche 12 en `Fenetre` ; fermer revient à `/commandes` avec filtres, onglet et défilement
  gardés (état dans l'adresse : `?onglet=`, `?q=`, filtres).

### 10.2 Les dix arbitrages (AMELIORATIONS-PRO partie 4) appliqués

| # | Composant | Comportement PRO |
|---|---|---|
| A1 | `Filtres` du `DataTable` | filtres **liés** (options sur les lignes qui passent les autres filtres), « Effacer les filtres » dès 2, « N critère(s) » |
| A2 | `DataTable` + `Cadre` | pas de pagination visuelle : le tableau défile dans son cadre (hauteur restante mesurée, en-tête collant) ; pagination serveur transparente « Charger les 500 suivants » ; recherche sur tout le jeu (serveur si paginé) ; tient en 1366 × 768 |
| A3 | `Confirmer` | confirmation **sur la ligne** (« question · Non · Oui, … ») pour tout geste ; `FenetreConfirmation` seulement pour les lectures longues (restauration, clôture de dossier avec alertes, clôture de période) ; aucun `window.confirm` (lint + essai) |
| A4 | `Fenetre` | fenêtre ou tiroir de GMAO PRO + garde `sale` (« Des modifications ne sont pas enregistrées. Les abandonner ? ») + pile (Échap ferme celle du dessus) + `beforeunload` |
| A5 | fiches | adresse stable et fenêtre par-dessus la liste |
| A6 | recherche | multi-mots, sans accents, sur des champs cachés (`Colonne.recherche`), même règle au serveur (`texte_recherche`) ; garde le focus |
| A7 | aide | `aide.json` : Mode d'emploi (7 onglets), une entrée par écran (« ? » de l'`EnTete`), formules des KPI ; `generer_notice.py` → `docs/NOTICE.md` |
| A8 | `Bouton` | `manque` (champs) **et** `blocages` (raisons métier calculées par le serveur) ; infobulle au bureau, texte sous le bouton au téléphone ; tout bouton grisé a sa raison (essai) |
| A9 | atelier | branche `/atelier/*` hors coque : `Tuile`, `Compteur`, `SegmentsTactiles`, `BarreBas`, `BandeauBlocages`, cibles ≥ 44 px, champs 46 px / 16 px, saisie gardée (`sessionStorage`), PWA |
| A10 | notifications | cloche **et** « Ma journée » / Cockpit « À faire » ; une notification ouvre le document par son adresse |

### 10.3 Système de composants (`frontend/src/composants/`)

Le détail (props, comportements, essais) est dans `ECRANS-PRO.md` § 3. Familles : `coque/`
(Coque, BarreLaterale, EnTete + fil d'Ariane, RechercheGlobale, Cloche, MenuCompte,
BandeauServeur, EcranReserve), `mise-en-page/` (Page, Carte, Onglets, Bascule, Fenetre,
FenetreConfirmation, Definitions, Grille, Indicateurs), `tableaux/` (DataTable, Cadre, Filtres,
Recherche, ExportExcel, ChargerPlus), `saisie/` (Champ, Saisie, Zone, Nombre, Quantite, Prix,
DateChamp, Interrupteur, Segments, Puces, Selecteur, SelecteurMatiere, SelecteurLot, Bouton,
Confirmer, Blocages), `retour/` (Messages, Chargement, Vide, Note, Erreur, Badge, Kpi, Formule,
Progression, Pastille, KgEtMetres, Montant), `graphiques/` (Barres, Courbes, BarresH, Sparkline,
SVG maison, couleurs des jetons et de `teintes.ts`), `documents/` (PiecesJointes, Historique,
LienDocument, BoutonImprimer), `atelier/` (EcranAtelier, Tuile, Compteur, SegmentsTactiles,
BarreBas, BandeauBlocages, ResumeValidation, ScanQR).

### 10.4 Atelier (PWA)

`manifest.webmanifest` (« Gestion MP PRO », court « MP PRO », `start_url /atelier`, icônes
180/192/512), `sw.js` qui ne garde que l'enveloppe (jamais de données : un stock d'hier serait
pire qu'un « pas de réseau »), enregistré en HTTPS ou sur localhost. Accès au téléphone :
appareil enrôlé + HTTPS (Caddy) ou réseau privé (Tailscale) vers le poste.

---

## 11. Documents et exports

- Gabarits Jinja2 (`documents/gabarits/`) héritant de `_papier_a_en_tete.html` : raison sociale en
  rouge avec grande initiale, secteur, forme juridique et capital, siège, ville ; pied : banques,
  ICE, R.C, N.I.F, C.N.S.S, patente (réglages « Société ») ; A4 (`@page`), tailles en points ;
  sans raison sociale réglée, le document affiche un bandeau « En-tête non réglé » **à l'écran
  seulement** (classe `ecran-seulement`).
- Bon de commande : **anglais, sans prix, sans montant, sans devise**, conditionnements traduits,
  kilos et mètres indicatifs, remarques au fournisseur dans une case à part, brouillon marqué
  « DRAFT — not sent » ; l'Excel (`exports/bon_fournisseur.py`) a exactement le même contenu.
- Étiquettes QR 100 × 70 mm (QR = adresse `/lot/{id}` de `adresse_publique`, alerte si
  localhost) ; « QUARANTAINE — NE PAS SORTIR » pour un lot en quarantaine.
- Feuille de comptage (à l'aveugle par défaut, recomptage avec théorique) ; bilan du mois.
- Exports Excel : conventions communes de Gestion MP (`exports/classeur.py`) **et** vraies dates
  partout, gravités traduites, mêmes filtres que l'écran ; aucun montant dans un export lisible
  par l'alimentation.

---

## 12. Tâches de fond (`taches/`)

Un seul processus les porte (verrou `TACHES`), boucle toutes les 15 minutes, chaque tâche
isolée (`try`), état écrit dans `tache_execution` (lu par `/api/sante` et l'écran) :

| Tâche | Quand | Effet |
|---|---|---|
| `sauvegarde_du_jour` | si la quotidienne du jour manque | `pg_dump -Fc` relu (`pg_restore --list`), pièces jointes, copie externe, purge (14 + 12 ; manuelles et « avant » jamais) |
| `photo_du_jour` | si `indicateur_jour` du jour manque | photo des indicateurs |
| `courriels` | chaque passage | lundi : met en file le courriel de la semaine (une fois, clé `lundi:AAAA-MM-JJ`) ; envoie la file (reprises) |
| `alertes` | une fois par jour | notifications : ruptures/critiques, commandes en retard, dossiers sans frais, contrôles bloquants, sauvegarde en échec |
| `purges` | une fois par jour | sessions expirées, tentatives anciennes, notifications lues anciennes |

---

## 13. Exploitation

Le détail des procédures sera dans `docs/EXPLOITATION.md` (lot X3). Principes :

### 13.1 Serveur (Docker Compose)

`deploiement/docker-compose.yml` : `base` (postgres:16, volume `donnees`, healthcheck
`pg_isready`), `application` (image construite : écran compilé servi par l'application,
2 processus uvicorn, utilisateur non root, `HEALTHCHECK` sur `/api/sante`, volumes
`sauvegardes`, `pieces`, montage facultatif de la copie externe), `https` (caddy:2, 80/443,
`tls internal` pour un nom interne). `.env` obligatoire (mot de passe de base, nom, SMTP).
L'image est **construite et essayée** avant livraison (critère de LOTS X1). Variante sans
Docker : `deploiement/gestion-mp-pro.service` (systemd).

### 13.2 Poste Mac de l'usine

- PostgreSQL 16 de Homebrew (le même serveur que Gestion MP, **une autre base** :
  `gestion_mp_pro`, rôle propriétaire `gestion_mp_pro`).
- `deploiement/mac/installer.sh` : crée base et rôle, `.venv`, construit l'écran, installe le
  LaunchAgent `fr.usine.gestion-mp-pro` (démarrage à l'ouverture de session, `KeepAlive` =
  relance automatique, journaux `~/Library/Logs/Gestion MP PRO/serveur.log` avec rotation),
  crée le raccourci `~/Desktop/Gestion MP PRO.app`.
- `scripts/demarrer.sh` : **copie figée** (dernier commit `git archive` + écran construit) dans
  `~/Library/Application Support/Gestion MP PRO/version/`, fichier `VERSION` (hash), puis uvicorn
  `127.0.0.1:8050` (`GESTIONMPPRO_ECOUTE` pour ouvrir au réseau). Travailler dans le projet ne
  touche pas la production avant le redémarrage.

### 13.3 Sauvegardes et restauration

Quotidienne relue + manuelle + « avant restauration » + « avant reprise » + « base vide de
référence » ; dossier propre à la base (`~/gestion-mp-pro-sauvegardes/<base>/`) ; pièces jointes
**incluses** dans une archive à côté du dump (`.pieces.tar`) ; copie externe ; purge 14 + 12.
Restauration (écran ou `scripts/restaurer.sh`) : tout ou rien (`pg_restore --list` d'abord,
`--single-transaction`), sauvegarde « avant restauration », coupure des autres connexions,
pièces jointes restaurées, **migration à `head`** après restauration d'une sauvegarde plus
ancienne, journal écrit dans la base restaurée, base d'une autre base refusée.

### 13.4 Santé et journaux

`/api/sante` (public, sans donnée métier) : version servie, révision Alembic et révision
attendue, temps de réponse de la base, âge et alerte de la sauvegarde **de cette base**, état
des tâches, courriels en attente. Journal serveur : `logging` (format horodaté, une ligne par
requête, niveau `GESTIONMPPRO_JOURNAL_NIVEAU`), vers stdout (Docker/systemd) ou fichier tournant
(Mac).

---

## 14. Coexistence et comparaison avec Gestion MP

Exigence du propriétaire : Gestion MP (8030), corrigé en parallèle, **reste en service** ;
PRO (8050) tourne à côté, et l'on doit pouvoir **comparer** les deux.

### 14.1 Coexistence sur le même Mac — rien de partagé

| | Gestion MP (inchangé) | Gestion MP PRO |
|---|---|---|
| Dossier du projet | `~/gestion-mp` | `~/gestion-mp-pro` |
| Port | 8030 | **8050** (écran de développement 5196) |
| Base | `gestion_mp` | **`gestion_mp_pro`** (essais `gestion_mp_pro_essai`, parité `gestion_mp_pro_parite`, charge `gestion_mp_pro_charge_*`) |
| Rôle PostgreSQL | utilisateur du Mac | `gestion_mp_pro` (propriétaire de sa base seulement) |
| Copie figée | `~/Library/Application Support/Gestion MP/version` | `~/Library/Application Support/Gestion MP PRO/version` |
| Sauvegardes | `~/gestion-mp-sauvegardes/` | `~/gestion-mp-pro-sauvegardes/` |
| Pièces jointes | `~/gestion-mp-pieces/` | `~/gestion-mp-pro-pieces/` |
| Journal du serveur | `~/Library/Logs/Gestion MP.log` | `~/Library/Logs/Gestion MP PRO/` |
| Raccourci | `~/Desktop/Gestion MP.app` | `~/Desktop/Gestion MP PRO.app` (icône distincte, titre « Gestion MP PRO ») |
| Démarrage | double-clic | LaunchAgent `fr.usine.gestion-mp-pro` |
| Cookie de session | `gestion_mp_session` | `gestion_mp_pro_session` (les cookies ne s'isolent pas par port) |
| En-tête anti-falsification | `X-Gestion-MP` | `X-Gestion-MP-PRO` |
| Verrous consultatifs | 7426101–7426110 | 7426201–7426209 |
| Variables | `GESTION_MP_*` | `GESTIONMPPRO_*` |
| Application installée au téléphone | « Gestion MP » | « Gestion MP PRO » (autre origine, autre manifeste) |

PRO ne lit la base `gestion_mp` qu'en **lecture seule** (transaction `READ ONLY`, aucun `GRANT`,
aucun objet créé dans cette base) et ne touche jamais `~/gestion-mp` ni ses dossiers. Un essai
(`test_coexistence.py`) vérifie qu'aucun chemin, port, nom de cookie, de base ou de verrou de
la configuration PRO ne coïncide avec ceux de Gestion MP.

### 14.2 Reprise rejouable (référentiels et activité)

`python -m gestion_mp_pro.reprise --source postgresql+psycopg:///gestion_mp --mode tout
--remplacer-activite` (MODELE-DONNEES § 10) : référentiels mis à jour par correspondance,
activité remplacée entière (identifiants et numéros gardés), soldes recalculés, journal relu en
tables, pièces jointes copiées, compteurs recalés, rapport de contrôle. Une seule transaction
sur la cible, photo cohérente de la source, < 1 minute au volume réel. Tant que PRO n'est pas
mis en service, sa base est un **miroir** de Gestion MP rafraîchi à la demande (onglet
Administration › Reprise, routes 243–244, ou `make miroir`) ; la reprise refuse d'écraser une activité saisie
dans PRO sans `--remplacer-activite` explicite (et sauvegarde « avant reprise » toujours faite).
La signature de la source (`max(mouvement.id)`, `max(journal.id)`, empreinte) est gardée dans
`reprise_execution`.

### 14.3 Le comparateur `outils/comparer_avec_gestion_mp.py`

```
python outils/comparer_avec_gestion_mp.py \
   --gestion-mp http://localhost:8030 --pro http://localhost:8050 \
   --dates 2026-10-08,fins-de-mois [--sections stock,valorisation,…] [--mode api|moteurs] \
   [--resynchroniser] --sortie essais/resultat-comparaison-2026-10-08.md
```

- **Même base** : vérifie que la signature de `gestion_mp` égale celle de la dernière reprise
  (sinon refuse, ou relance la reprise avec `--resynchroniser`) ; consigne la version servie de
  chaque logiciel (`/api/sante`).
- **Deux modes** : `api` (par défaut) — interroge les deux API avec un compte direction de chacun
  (identifiants demandés ou lus dans l'environnement, jamais écrits) ; `moteurs` — lance
  `outils/gestion_mp_extraire.py` avec `~/gestion-mp/.venv/bin/python` (lecture seule de
  `gestion_mp`) et le calcul symétrique de PRO par ses services, sans HTTP.
- **Sections comparées chiffre par chiffre**, à chaque date : stock par matière (toutes les
  colonnes de l'état du stock), lots et soldes, valorisation (stock, magasin, sur les métiers,
  CMUP, valeurs), journal valorisé (coût de chaque mouvement), besoins (12 mois, par qualité),
  plan d'achat (lignes, fournisseurs, budget, tiers, urgences), contrôles (nombre d'anomalies et
  éléments signalés, par code), cockpit (six KPI et listes), coût de revient des dossiers
  (marchandise, frais par ligne, coût hors TVA, TVA, attendus, écart de facture), commandes
  (statuts, reçu, reste, montants), performance fournisseurs (OTIF, score), ordres (prévu, net,
  écart), échéancier, bilan du mois.
- **Tolérances** (PLAN-DE-RECETTE § 7.5) : 0,001 kg, 0,01 MAD ou 1e-6 relatif, ratios 1e-6,
  textes et dates exacts (table de correspondance des libellés déclarée).
- **Explications** : une différence n'est « expliquée » que par une règle qui recalcule son
  ampleur (corrections K1–K6 de MODELE-DONNEES § 10.5) ; toute autre est « à corriger ».
  La réciproque est vérifiée (chaque champ de Gestion MP existe dans PRO).
- **Rapport** : Markdown (volumes, tableau par section : comparés, identiques, expliqués, à
  corriger ; détail des écarts) ; code de sortie 0 seulement si « à corriger : 0 ». Il alimente
  `docs/COMPARAISON-GESTION-MP.md` (lot C1).

### 14.4 `docs/COMPARAISON-GESTION-MP.md`

Produit par le lot C1 « Comparaison » : (1) les chiffres identiques prouvés (rapport du
comparateur aux 13 dates, parité dynamique du scénario) ; (2) le tableau des différences
**d'écran** (arbitrages, adresses stables, composants), **de structure** (couches, tables,
routes, migrations), **de sécurité** (rôles, filtre des prix, appareils, HTTPS, matrice) et
**d'exploitation** (Docker, launchd, sauvegardes avec pièces, santé, journaux), chacune
expliquée et renvoyant à son exigence.

---

## 15. Vérification

Le plan complet est `docs/heritage/PLAN-DE-RECETTE-PRO.md` (critères A1–A14), avec trois
adaptations : les migrations sont des révisions Alembic (essai de contiguïté sur les
identifiants `0001…`), la vérification indépendante lit `/api/donnees/{table}` (direction),
et la comparaison avec Gestion MP en service s'ajoute à la parité sur l'année d'essai.
Commande unique : `make verifier` = `ruff check` + `ruff format --check` + `mypy` + `pytest`
(essais complets) + `npm run verifier` (prettier, eslint, tsc, vitest) + `outils/routes_ecran.py`
+ `outils/verifier_heritage.py` + `alembic check`. Un crochet `pre-commit` bloque le commit si
la partie rapide échoue.

---

## 16. Configuration (`config.py`, variables `GESTIONMPPRO_*`)

| Variable | Défaut | Rôle |
|---|---|---|
| `GESTIONMPPRO_BASE` | `postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro` | URL de la base |
| `GESTIONMPPRO_FUSEAU` | `Africa/Casablanca` | fuseau de l'usine (PostgreSQL + `zoneinfo`) |
| `GESTIONMPPRO_PORT` | `8050` | port |
| `GESTIONMPPRO_ECOUTE` | `127.0.0.1` | adresse d'écoute |
| `GESTIONMPPRO_HTTPS` | `0` | cookies `Secure`, alerte si 0 et écoute réseau |
| `GESTIONMPPRO_ADRESSE` | vide | adresse publique (QR, liens des courriels) ; le réglage `adresse_publique` la complète |
| `GESTIONMPPRO_PROCESSUS` | `2` | workers uvicorn (Docker, systemd) |
| `GESTIONMPPRO_TACHES` | `1` | ce processus tente de porter les tâches |
| `GESTIONMPPRO_SESSION_JOURS` | `30` | durée de session |
| `GESTIONMPPRO_SAUVEGARDES` | `~/gestion-mp-pro-sauvegardes` (+ `/<base>`) | sauvegardes |
| `GESTIONMPPRO_SAUVEGARDES_COPIE` | vide | copie externe |
| `GESTIONMPPRO_PIECES` | `~/gestion-mp-pro-pieces` (+ `/<base>`) | pièces jointes |
| `GESTIONMPPRO_PG_BIN` | vide | dossier de `pg_dump`/`pg_restore` |
| `GESTIONMPPRO_ECRAN` | `frontend/dist` | écran construit (servi par l'application hors Docker+Caddy) |
| `GESTIONMPPRO_SMTP_HOTE`, `_PORT` (587), `_UTILISATEUR`, `_MOT_DE_PASSE`, `_EXPEDITEUR` | vide | courriels |
| `GESTIONMPPRO_JOURNAL_NIVEAU` | `INFO` | niveau du journal serveur |
| `GESTIONMPPRO_JOURNAL_FICHIER` | vide (stdout) | fichier tournant (Mac) |
| `GESTIONMPPRO_SOURCE_GESTION_MP` | `postgresql+psycopg:///gestion_mp` | source de la reprise (lecture seule) |
| `GESTIONMPPRO_PIECES_GESTION_MP` | `~/gestion-mp-pieces` | pièces de la source (copiées) |
| `GESTIONMPPRO_ESSAIS_COMPLETS` | `0` | `1` : les essais qui demandent un vrai serveur ou les outils PostgreSQL échouent au lieu d'être sautés |

`config.Reglages` (pydantic-settings) est lu une fois ; aucune autre lecture de `os.environ`
dans le paquet (essai). `deploiement/exemple.env` les liste toutes.

---

## 17. Décisions de conception tranchées

| # | Sujet | Décision PRO | Raison |
|---|---|---|---|
| T1 | Fil monté sur les métiers (DECISIONS § 16.1) | Décision de Mohamed gardée : le fil monté est du stock « sur les métiers », compté dans le stock global, sa valeur, le disponible et le projeté. **Monter n'écrit aucun mouvement** (le fil est déjà sorti par un ordre, sa consommation y est valorisée) : la valeur « sur les métiers » est une **information de détention**, dite comme telle, avec historique (`montage_evenement`). Un seul texte partout (`aide.json` clé `sur_les_metiers`). À une date passée, le moteur ne le compte pas (comme Gestion MP : parité) ; l'historique permet de le décider plus tard. | Parité et décision de Mohamed ; modéliser un « lieu machine » changerait la consommation des ordres |
| T2 | Inventaire qui bloque tout le magasin (N3) | Suspension limitée au périmètre (K2) | Pratique d'usine (REC-direction 15), le modèle le permet |
| T3 | Trous de séries INV/DOS | Abandon/annulation au lieu de suppression (K3) | M65 + A10 |
| T4 | Notifications (T12) | Cloche **et** Ma journée | PLAN.md, A10 |
| T5 | Verrou par empreinte | `version` | PLAN.md |
| T6 | Rôle « au mètre » | lu dans les données (`lineaire`), non modifiable | DECISIONS § 16.5 |
| T7 | Lot interne pris d'avance | supprimé : case sur la ligne | M65 |
| T8 | Bon fournisseur doublon français avec prix | supprimé | A22 |
| T9 | Alimentation et réglages, cours | 403 | consigne « aucun prix ni montant nulle part » |
| T10 | Code de l'alimentation | exactement 4 chiffres | D10 ; la saisie part au 4ᵉ chiffre |
| T11 | Mode « classeur » du moteur | non repris | P17 |
| T12 | Réception toute refusée | annulable (K4) | anomalie A.12-12 |
| T13 | Documents imprimés | gabarits serveur Jinja2 | décision du coordinateur (C12) |
| T14 | Questions encore ouvertes pour Mohamed (DECISIONS § 15 : prix bande/cuir, Franges, codes douaniers, valorisation à la facture, TPI, sortie oubliée) | Non tranchées par PRO ; le comportement de Gestion MP est gardé et les points restent signalés (contrôles, rapport de reprise) | Mohamed décide ; PRO ne change rien en silence (M11) |

---

## 18. Limites et risques

| Risque | Parade |
|---|---|
| Gestion MP change pendant la réalisation (corrigé en parallèle) | Le comparateur consigne la version de chaque côté ; une différence qui vient d'une correction de Gestion MP est reportée dans PRO (lot « Comparaison ») ou déclarée |
| Arrondis de la reprise (float → NUMERIC) | Normalisation documentée, règle K1 qui recalcule l'écart attendu |
| Performance du moteur « tout en mémoire » | Cache par signature ; mesures ×10 et ×30 (A9) ; un calcul optimisé doit rendre les mêmes chiffres octet pour octet |
| Docker jamais construit (défaut de GMAO PRO) | Critère de fin du lot X1 : image construite, `docker compose up`, recette navigateur à travers Caddy |
| Deux serveurs sur un Mac | § 14.1, essai de coexistence |
