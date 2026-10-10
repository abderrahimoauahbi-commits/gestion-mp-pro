# Gestion MP PRO

ERP des matières premières de l'usine de tapis : achats, réceptions, importations, stock en kg
(magasin, quarantaine, sur les métiers), alimentation des machines au téléphone, pilotage.
Réécriture professionnelle de Gestion MP (`~/gestion-mp`), au standard de GMAO PRO, avec le
**même métier** et les **mêmes chiffres** (parité prouvée). Gestion MP reste en service à côté.

> Installation et exploitation : voir la section « Avant d'ouvrir au réseau » ci-dessous et
> [`docs/EXPLOITATION.md`](docs/EXPLOITATION.md) (lot X3).

## En bref

| | |
|---|---|
| Serveur | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL 16, Alembic — `backend/` |
| Écran | React 19, TypeScript strict, Vite — `frontend/` |
| Port | **8050** (écran de développement : 5196) — Gestion MP garde 8030 |
| Base | `gestion_mp_pro` ; essais : `gestion_mp_pro_essai` (jamais une autre) |
| API | `/api`, documentation OpenAPI sur `/api/docs` |
| Conception | `docs/ARCHITECTURE.md`, `MODELE-DONNEES.md`, `API-PRO.md`, `ECRANS-PRO.md`, `LOTS-DE-TRAVAIL.md`, héritage dans `docs/heritage/` |
| Référence et recette | `docs/CAHIER-DES-CHARGES.md`, `RECETTE.md`, `COMPARAISON-GESTION-MP.md`, `EXPLOITATION.md`, `LIVRAISON.md` |

## Les documents

| Pour | Document |
|---|---|
| Comprendre ce que fait le logiciel (par domaine, par rôle, les décisions de métier) | [`docs/CAHIER-DES-CHARGES.md`](docs/CAHIER-DES-CHARGES.md) |
| Le rapport de recette : verdict critère par critère (A1–A14), anomalies corrigées, état des défauts de Gestion MP, questions ouvertes | [`docs/RECETTE.md`](docs/RECETTE.md) |
| La preuve que PRO dit les mêmes chiffres que Gestion MP, et comment le vérifier soi-même | [`docs/COMPARAISON-GESTION-MP.md`](docs/COMPARAISON-GESTION-MP.md) |
| Installer, sauvegarder, restaurer, surveiller (poste Mac et serveur Linux) | [`docs/EXPLOITATION.md`](docs/EXPLOITATION.md) |
| Le rapport de livraison, en une page (pour Mohamed) | [`docs/LIVRAISON.md`](docs/LIVRAISON.md) |
| Comment c'est fait (couches, modèle de données, API, écrans) | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |

## Démarrer en développement

Prérequis : Python 3.12 (`python3.12`), PostgreSQL 16 qui tourne, Node 22 pour l'écran.

```bash
make installer                     # backend/.venv, dépendances figées, écran, crochet pre-commit
createdb gestion_mp_pro_essai      # base des essais (une fois)
make verifier                      # ruff, ruff format, mypy strict, pytest (+ écran s'il existe)
GESTIONMPPRO_BASE=postgresql+psycopg:///gestion_mp_pro make demarrer   # http://127.0.0.1:8050
```

`make aide` liste toutes les cibles : `installer`, `verifier`, `verifier-rapide`, `essais`
(complets), `matrice` (droits), `types` (types de l'écran depuis l'OpenAPI), `parite`,
`comparer`, `miroir`, `construire`, `docker`, `demarrer`, `verrouiller` (versions figées dans
`backend/requirements.lock` et `requirements-dev.lock`). Une cible dont l'outil n'est pas encore
livré le dit et s'arrête.

## Configuration

Uniquement par l'environnement, variables `GESTIONMPPRO_*` (liste complète :
`docs/ARCHITECTURE.md` § 16 ; lues une fois par `backend/gestion_mp_pro/config.py`, seul
module qui lit l'environnement). Les plus courantes :

| Variable | Défaut |
|---|---|
| `GESTIONMPPRO_BASE` | `postgresql+psycopg://gestion_mp_pro@localhost/gestion_mp_pro` |
| `GESTIONMPPRO_PORT` / `GESTIONMPPRO_ECOUTE` | `8050` / `127.0.0.1` |
| `GESTIONMPPRO_FUSEAU` | `Africa/Casablanca` (passé à PostgreSQL et à `zoneinfo`, jamais au processus) |
| `GESTIONMPPRO_TACHES` | `1` (`0` : ce processus ne porte pas les tâches de fond) |
| `GESTIONMPPRO_JOURNAL_NIVEAU` / `_FICHIER` | `INFO` / sortie standard |
| `GESTIONMPPRO_SAUVEGARDES`, `_PIECES` | `~/gestion-mp-pro-sauvegardes/<base>`, `~/gestion-mp-pro-pieces/<base>` |

Les essais lisent `GESTIONMPPRO_BASE_ESSAI` (défaut `postgresql+psycopg:///gestion_mp_pro_essai`)
et refusent toute base dont le nom ne finit pas par `_essai`.

## Organisation du code serveur

```
backend/gestion_mp_pro/
  main.py            application, cycle de vie, protections (en-tête, 503), écran construit
  config.py          Reglages (GESTIONMPPRO_*), constantes de coexistence (cookie, en-tête)
  db.py              moteur, session par requête, verrous consultatifs nommés, disponibilité
  journalisation.py  journal du serveur, middleware trace (une ligne par requête)
  api/               un paquet par domaine (routes.py, schemas.py) ; erreurs, dépendances, communs
  services/          métier sans HTTP (un module par domaine) ; horloge.py (heure de l'usine)
  calcul/            moteur de calcul pur
  taches/ documents/ exports/ reprise/
backend/tests/       pytest sur gestion_mp_pro_essai, horloge figée au 8 octobre 2026
```

Couches strictes : `api/` (HTTP seulement) → `services/` (règles, transactions) → `calcul/`
(fonctions pures). Plafonds : 400 lignes par fichier, 60 lignes par fonction ; docstring en
français sur chaque module et fonction publique ; aucun `print` (journal `logging`).

## Conventions de l'API

- Erreurs : `{"detail": "<phrase française>", "code": "<code>"}` (+ `champs` pour une saisie) ;
  422 saisie · 409 état · 404 · 403 · 401 · 429 · 503 ; jamais de 500 pour une saisie, un 500
  imprévu cite sa référence (`réf. …`, début de l'en-tête `X-Requete`). Codes : `api/erreurs.py`.
- Toute écriture sous `/api` porte `X-Gestion-MP-PRO: 1` (sauf connexion, installation,
  enrôlement d'un appareil), y compris la déconnexion.
- Réponses : `X-Requete`, `X-Heure-Serveur` (heure de l'usine), `Cache-Control: no-store`,
  en-têtes de sécurité (`nosniff`, `DENY`, `same-origin`, CSP).
- Listes longues : `Page[T]` = `{elements, total, suivant}`, `?apres=&limite=` (≤ 5 000).

## Coexistence avec Gestion MP

Rien n'est partagé : autre dossier, port (8050), base, rôle PostgreSQL, cookie
(`gestion_mp_pro_session`), en-tête, verrous (7426201–7426209), dossiers de sauvegardes et de
pièces. PRO ne lit la base `gestion_mp` qu'en lecture seule (reprise, comparaison) et ne
touche jamais `~/gestion-mp`.

## Avant d'ouvrir au réseau

Le détail de l'installation et de l'exploitation (poste Mac, serveur Linux, sauvegardes,
restauration, miroir, surveillance) est dans [`docs/EXPLOITATION.md`](docs/EXPLOITATION.md). Avant
d'ouvrir Gestion MP PRO aux postes et aux téléphones de l'usine, l'informaticien tient cette
liste :

1. **Premier compte de direction** créé (écran d'installation, `POST /installation`, une seule
   fois), puis un compte par personne avec son rôle (direction, achats, alimentation,
   administrateur technique). Le code de l'alimentation fait **exactement 4 chiffres**.
2. **HTTPS** en place là où les téléphones se connectent : Caddy sur un serveur Linux
   (`tls internal` pour un nom interne, à installer une fois sur chaque appareil ; ou certificat
   public), ou Tailscale sur le poste Mac. HTTPS est **nécessaire** pour l'appareil photo (QR des
   lots) et pour installer PRO comme une application.
3. **Écoute réseau** assumée : `127.0.0.1` par défaut ; `GESTIONMPPRO_ECOUTE=0.0.0.0` seulement
   derrière HTTPS (une écoute réseau sans HTTPS est signalée en rouge dans Administration ›
   Serveur). Sur un serveur, seuls 80/443 de Caddy sont publiés ; le 8050 ne l'est pas.
4. **Mot de passe fort sur la base** (serveur exposé : `pg_hba` en `scram-sha-256`, mot de passe
   dans `GESTIONMPPRO_BASE`) — inutile sur le Mac en `trust` local.
5. **Copie des sauvegardes hors du serveur** : `GESTIONMPPRO_SAUVEGARDES_COPIE` vers un disque ou
   un partage monté (une sauvegarde sur le même disque que la base ne protège pas d'une panne).
6. **Surveillance** branchée sur `GET /api/sante` **en lisant `etat`** (pas seulement le code
   HTTP) : il dit l'âge de la dernière sauvegarde et les alertes.
7. **Adresse publique** (`GESTIONMPPRO_ADRESSE`) fixée **avant** d'imprimer les QR d'enrôlement des
   appareils, qui la portent.
8. **Essai de restauration** réussi sur une base d'essai (`essais/sauvegarde_restauration.sh`),
   à refaire chaque mois.

Gestion MP PRO est conçu pour tourner **à côté de Gestion MP** (port 8030) sur le même Mac, sans
rien partager : voir la section « Coexistence » ci-dessus et `docs/EXPLOITATION.md` § 6.

## Contribuer

Un commit = un changement, titre en français à l'impératif (≤ 72 caractères) ; `make verifier`
vert avant de proposer ; le crochet pre-commit bloque si la partie rapide échoue. Un fichier n'a
qu'un lot propriétaire (`docs/LOTS-DE-TRAVAIL.md` § 0).
