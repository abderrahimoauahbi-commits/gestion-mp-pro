# Gestion MP PRO

ERP des matières premières de l'usine de tapis : achats, réceptions, importations, stock en kg
(magasin, quarantaine, sur les métiers), alimentation des machines au téléphone, pilotage.
Réécriture professionnelle de Gestion MP (`~/gestion-mp`), au standard de GMAO PRO, avec le
**même métier** et les **mêmes chiffres** (parité prouvée). Gestion MP reste en service à côté.

> Première version du README (lot S0, socle). Les sections « Documents » et « Exploitation »
> seront complétées par les lots D9, X1, X2 et X3.

## En bref

| | |
|---|---|
| Serveur | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, PostgreSQL 16, Alembic — `backend/` |
| Écran | React 19, TypeScript strict, Vite — `frontend/` |
| Port | **8050** (écran de développement : 5196) — Gestion MP garde 8030 |
| Base | `gestion_mp_pro` ; essais : `gestion_mp_pro_essai` (jamais une autre) |
| API | `/api`, documentation OpenAPI sur `/api/docs` |
| Conception | `docs/ARCHITECTURE.md`, `MODELE-DONNEES.md`, `API-PRO.md`, `ECRANS-PRO.md`, `LOTS-DE-TRAVAIL.md`, héritage dans `docs/heritage/` |

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

## Contribuer

Un commit = un changement, titre en français à l'impératif (≤ 72 caractères) ; `make verifier`
vert avant de proposer ; le crochet pre-commit bloque si la partie rapide échoue. Un fichier n'a
qu'un lot propriétaire (`docs/LOTS-DE-TRAVAIL.md` § 0).
