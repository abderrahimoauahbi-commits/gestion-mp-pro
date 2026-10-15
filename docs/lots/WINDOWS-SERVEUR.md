# Lot WINDOWS-SERVEUR — préparer Gestion MP PRO pour un serveur Windows

Demande de Mohamed (15 octobre 2026, « oui » pour le préparer maintenant) : Gestion MP PRO
s'installera sur un **Windows Server** (version et lieu — usine ou hébergeur — pas encore
choisis). Jusqu'ici PRO tournait sur le Mac (scripts bash) et était prévu sur Linux (Docker,
systemd) ; **aucun kit Windows n'existait**. Le test réel se fera plus tard, sur le serveur.

Livré : l'audit de portabilité du serveur Python (corrigé là où c'est sûr, chaque correction avec
un essai qui tourne aussi sur le Mac), le kit `deploiement/windows`, le paquet fait sur le Mac
(`scripts/paquet_windows.sh`), le guide [INSTALLATION-WINDOWS.md](../INSTALLATION-WINDOWS.md) avec
la procédure de transfert depuis le Mac et la recette sur le serveur. Aucune révision Alembic,
aucun changement d'API ni de métier : les chiffres ne bougent pas.

---

## 1. Audit de portabilité du serveur (backend/gestion_mp_pro)

Classement : **corrigé** (avec son essai), **sans effet** (déjà portable, vérifié), **à vérifier
sur le serveur** (ne se prouve pas sans Windows).

| # | Point | Risque sous Windows | Classement | Preuve / essai |
|---|---|---|---|---|
| 1 | `open()` / `read_text()` / `write_text()` sans `encoding=` | Windows lit et écrit en cp1252 : accents abîmés, `UnicodeDecodeError` | **corrigé** | Le paquet n'en avait aucun ; 9 dans `essais/` et `tests/`, corrigés. Règle ruff **PLW1514** activée (seule règle « preview », `explicit-preview-rules`) : un oubli futur bloque `make verifier`. |
| 2 | Sortie texte des outils (`subprocess.run(text=True)`) | Décodée dans la page de code locale ; un message de `pg_restore` en cp850 levait `UnicodeDecodeError` → sauvegarde en 500 | **corrigé** | `lancer` lit en UTF-8, `errors="replace"`. Essai `test_sortie_d_un_outil_dans_une_autre_page_de_code` (octets `\xe9`, `\x82`). |
| 3 | Fuseau de l'usine (`zoneinfo`) | Windows n'a pas la base IANA : `ZoneInfoNotFoundError`, le serveur refuse de démarrer | **corrigé** | `tzdata ; sys_platform == 'win32'` dans `pyproject.toml` (psycopg l'exige aussi sous Windows) ; présent dans `requirements-windows.lock`. Démarrage du serveur = preuve, sur le serveur. |
| 4 | `GESTIONMPPRO_PG_BIN` + `outil()` | Cherchait `dossier / "pg_dump"`, sans `.exe` : sauvegardes et restaurations en 503 | **corrigé** | `SUFFIXES = (".exe", "")` sous Windows. Essais `test_pg_bin_trouve_pg_dump_exe`, `test_pg_bin_sur_le_mac_inchange`. |
| 5 | Dossiers de recherche des outils | Aucun dossier Windows ; tri lexical (`9.6` avant `16`) | **corrigé** | `C:/Program Files/PostgreSQL/*/bin` ajouté, tri par numéros. Essai `test_dossiers_connus_de_windows_et_version_la_plus_haute_d_abord`. |
| 6 | Chemin du `passfile` dans l'adresse libpq | Non encodé : un profil « Jean Dupont » (espace) est refusé par libpq (« unexpected spaces ») ; `%` ou `&` mal lus | **corrigé** | `quote(chemin, safe="")`, décodé par libpq. Essai `test_passfile_dans_un_dossier_avec_espaces` (lu par `conninfo_to_dict`, la lecture même de libpq). |
| 7 | **Mot de passe sur la ligne de commande de pg_dump / pg_restore / psql** (toutes plates-formes) | `URL.set(password=None)` ne retire rien (None = « inchangé ») : le mot de passe partait dans les arguments, lisible de tout compte dans la liste des processus. Sans effet sur le Mac (base sans mot de passe), réel sur tout serveur | **corrigé** | Adresse refaite par `URL.create(…)` sans mot de passe ; seul le `passfile` le porte. Essai `test_le_mot_de_passe_ne_passe_jamais_sur_la_ligne_de_commande` (échouait avant). |
| 8 | `fichier.touch(mode=0o600)` du `passfile` | Sans effet sous Windows (pas de droits Unix) | **sans effet** (dit dans le module) | Le fichier est dans le dossier temporaire du compte du service (fermé aux autres comptes) et effacé dès l'outil fini ; libpq ne vérifie pas ses droits sous Windows. À constater : le TEMP du compte SERVICE LOCAL. |
| 9 | Dossiers par défaut `~/gestion-mp-pro-*` | Sous un compte de service, `~` est son profil (`C:\Windows\ServiceProfiles\…`) | **corrigé** | Défaut `C:\ProgramData\Gestion MP PRO\{sauvegardes,pieces}` sous Windows (`config.dossier_par_defaut`, sans lire l'environnement : `test_config`) ; le kit écrit de toute façon les chemins réels. Essais `test_dossiers_par_defaut_*`. |
| 10 | Noms venus de l'extérieur (adresse de l'écran, membre d'une archive de pièces) | `Path(racine) / "\\hôte\partage\x"` (ou `C:\…`) **remplace** la racine ; `is_file()` / `resolve()` contacterait le partage (fuite NTLM) avant le contrôle `is_relative_to` | **corrigé** | `services/chemins.relatif_sur` (lecteur, racine, partage, `:` de flux NTFS refusés, contrôle lexical pour les deux systèmes) dans `main._servir_ecran` et `sauvegarde_pieces._sur`. Essais `test_ecran_n_interroge_jamais_un_partage` (aucun `is_file` appelé ; échouait avant), `test_archive_de_pieces_sans_lecteur_ni_partage`. `StaticFiles` de Starlette 1.7 contrôle déjà par `abspath` + `commonpath` avant tout accès. |
| 11 | Chemins des pièces jointes | Séparateurs `\` | **sans effet** | En base : `relatif.as_posix()` ; archives `.pieces.tar` : `arcname=…as_posix()`. Une archive du Mac se remet telle quelle (répétition § 3). |
| 12 | Sous-processus | Shell, guillemets, mots de passe | **sans effet** (+ n° 7) | Arguments en liste, chemin complet de l'outil, jamais de shell ; mot de passe par `passfile` seulement. |
| 13 | `os.replace(provisoire, cible)` (sauvegarde, archive, pièces) | Remplacer un fichier ouvert échoue sous Windows | **sans effet** / **à vérifier** | La cible est toujours un nom neuf (horodaté, ou tiré au hasard) : rien d'ouvert n'est remplacé. Reste un antivirus qui tiendrait le provisoire au moment du renommage (`WinError 32`) : guide § 11 (exclusion du dossier). |
| 14 | Effacement des vieilles sauvegardes (rotation) et bouton « Supprimer » | `unlink` d'un fichier ouvert ailleurs (copie en cours, antivirus) lève `PermissionError` sous Windows, pas sous Unix | **à vérifier sur le serveur** | Zone du chantier « sauvegardes-calendrier » (fusionné dans main), non touchée ici : **recommandation** — dans `sauvegarde._purger_dossier`, attraper `OSError` par fichier (journaliser, réessayer à la passe suivante) pour qu'une sauvegarde réussie ne finisse pas en échec de tâche. |
| 15 | Restauration (`services/restauration.py`) avec des fichiers ouverts | Remplacement de la base ou des pièces sous un fichier ouvert | **sans effet** | La base est remplacée **dans PostgreSQL** (`DROP SCHEMA` / script, une transaction : aucun fichier) ; le script `.sql` est effacé après la fin de `psql` ; les pièces ne sont qu'**ajoutées** (jamais écrasées ni effacées). |
| 16 | Fin de ligne des exports | CRLF / LF | **sans effet** | Les exports sont des classeurs `.xlsx` (binaires) ; le fichier temporaire d'un export en flux est fermé avant d'être relu (`NamedTemporaryFile(delete=False)`), ce que Windows exige. Le seul CSV (matrice des droits, outil de développement) fixe `lineterminator="\n"`. |
| 17 | Signaux, arrêt | Pas de SIGTERM sous Windows | **à vérifier sur le serveur** | Le paquet n'utilise aucun signal (tâches de fond : un fil `daemon`). L'arrêt par `arreter.ps1` est un arrêt net du processus : PostgreSQL annule toute transaction en cours ; `arreter.ps1` attend d'abord la fin d'un `pg_dump` / `psql` en cours (10 min au plus). |
| 18 | `uvloop` | N'existe pas sous Windows ; `requirements.lock` (figé sur le Mac, sans marqueurs) le contenait : `pip install -r` **échouait** sous Windows | **corrigé** | `requirements-windows.lock` : mêmes versions que `requirements.lock`, sans uvloop, avec tzdata, **roues Windows 64 bits cp312 prouvées** (`uv pip compile --python-platform x86_64-pc-windows-msvc --only-binary :all:`, qui refuse uvloop) ; `make verrouiller` le refait. Uvicorn choisit asyncio seul : essai `test_uvicorn_demarre_sans_uvloop`, et un vrai serveur lancé sans uvloop sur le Mac (`/api/sante` 200). Essai de cohérence des deux verrous (`test_requirements_windows_memes_versions_sans_uvloop`). |
| 19 | Journal tournant (`RotatingFileHandler`) | Renommer un journal ouvert par un autre processus échoue sous Windows | **à vérifier sur le serveur** | Le kit sert **un seul processus** (pas de `--workers`) ; reste un lecteur ou un antivirus qui tiendrait `serveur.log` au moment de la rotation (la ligne est alors perdue, le serveur continue). |
| 20 | Fuseau du processus (`TZ`) | — | **sans effet** | Jamais posé (C16) ; l'heure de l'usine vient de `zoneinfo` et de PostgreSQL. |
| 21 | Accès asynchrone à la base (boucle Proactor de Windows) | psycopg asynchrone refuse la boucle Proactor | **sans effet** | Tout l'accès à la base est synchrone (SQLAlchemy + psycopg, fils). |
| 22 | Tri des textes de la base | Locale Windows (`French_France.1252`…) au lieu de `en_US.UTF-8` | **à vérifier sur le serveur** | N'affecte que l'ordre des listes, jamais un chiffre. La recette contrôle `a<B`, `é<z`, `lower(É)=é`, `upper(ç)=Ç` (mêmes réponses que la base du Mac : `t|f|t|t`). |
| 23 | Sortie standard et console | cp1252/cp850 | **sans effet** | Le kit pose `PYTHONUTF8=1` (comme `commun.sh` sur le Mac) et un journal fichier en UTF-8 ; PowerShell lit la sortie de Python en UTF-8. |

## 2. Le kit (deploiement/windows) et le paquet

PowerShell **5.1** (celui de Windows Server), commentaires en français, fichiers en **UTF-8 avec
BOM** (sans BOM, PowerShell 5.1 lit en cp1252 et « — » y devient un guillemet), aucun binaire
tiers téléchargé ni commité, comptes Windows désignés par leur SID (noms traduits selon la langue).

| Fichier | Rôle |
|---|---|
| `installer.ps1` | Prérequis (Windows 64 bits, administrateur, service PostgreSQL ≥ 16 en marche, `pg_dump` pas plus ancien que le serveur, Python 3.12 64 bits installé pour tous), rôle `gestion_mp_pro` (mot de passe demandé ou tiré au hasard, 32 caractères, passé à psql par son entrée, jamais affiché ni écrit ailleurs que dans le fichier environnement) et base (UTF-8, `template0`, connexion retirée à PUBLIC), version dans `C:\Program Files\Gestion MP PRO\versions\<version>` avec son environnement Python (roues seulement), données dans `C:\ProgramData\Gestion MP PRO` fermées aux autres comptes (`icacls` par SID), fichier `environnement` (base, écoute `0.0.0.0:8050`, dossiers, `GESTIONMPPRO_SAUVEGARDES_COPIE`, `PG_BIN`), migrations (`poste.py migrer` : Alembic `upgrade head` sous verrou, semences contrôlées), base vide de référence, tâche planifiée, pare-feu, démarrage et attente de `/api/sante`. Idempotent. |
| `lancer-serveur.ps1` | Porté par la tâche planifiée : lit l'environnement, sert la version en service (`uvicorn`, un processus, `--proxy-headers` derrière HTTPS), relance après 10 s s'il tombe ; `lanceur.log`, `demarrage.log`. |
| `demarrer.ps1`, `arreter.ps1` | Tâche démarrée / arrêtée, puis processus du serveur arrêté (et lui seul : port **et** ligne de commande `gestion_mp_pro.main:app`), sauvegarde en cours attendue ; `-Desactiver`. |
| `etat.ps1` | `/api/sante` (lu en UTF-8), tâche, trois dernières sauvegardes du dossier **et** de la copie, place libre. |
| `sauvegarder.ps1` | `manuelle` ou `avant-mise-a-jour`, par le même service que l'écran. |
| `restaurer.ps1` | Serveur arrêté ; copie d'un fichier venu d'une clé (avec son `.pieces.tar`) ; confirmation tapée ; `-Comptes` compare la base restaurée à un autre serveur. |
| `mettre-a-jour.ps1` | Nouvelle version préparée à côté, **arrêt puis** sauvegarde « avant mise à jour » (rien ne peut changer entre les deux), passage, contrôle `/api/sante` (version et schéma, 3 min), **retour arrière automatique** (ancienne version, et restauration si la base avait été migrée) ; `-RetourArriere` plus tard. Deux versions gardées. |
| `desinstaller.ps1` | Retire programme, tâche, règle ; garde base, sauvegardes, pièces, réglages ; `-SupprimerLaBase` (dernière sauvegarde d'abord) et `-SupprimerLesDonnees` exigent chacune une phrase **tapée** ; la copie n'est jamais touchée. |
| `recette.ps1` | Contrôles automatiques (guide § 10). |
| `commun.ps1`, `fonctions-admin.ps1` | Fonctions communes. |

**Démarrage automatique : tâche planifiée, pas service Windows.** Native (rien à télécharger,
rien à compiler), « au démarrage du système » (30 s après), compte **SERVICE LOCAL** (intégré,
sans mot de passe, peu de droits), sans limite de durée (`PT0S` : la limite par défaut de 3 jours
arrêterait le serveur), relance chaque minute en cas d'échec, priorité normale (la priorité par
défaut d'une tâche est « inférieure à la normale »). Un service Windows aurait demandé un exe
enveloppe (NSSM, WinSW : binaires tiers) ou `pywin32` (dépendance, compte à gérer) pour un gain
nul ici. Une copie sur un partage réseau demande un compte à mot de passe : `-Compte`.

**Paquet** (`scripts/paquet_windows.sh`, `make paquet-windows`) : `git archive` du commit demandé
(rien de non commité), écran construit avec `npm run build`, `VERSION` (lu par `/api/sante`),
`backend/{gestion_mp_pro, pyproject.toml, requirements-windows.lock}`, `frontend/dist`, `windows/`
(kit + `poste.py`), le guide ; garde-fous : ni `.dump`, ni `.pieces.tar`, ni `.env`,
`environnement`, journaux, `__pycache__`, `node_modules`, tests, ni adresse avec mot de passe
(sinon rien n'est écrit) ; zip + empreinte SHA-256 ; `--avec-roues` pour un serveur sans Internet
(`pip download` des roues Windows, **non joué ici**).

**Transfert** : `scripts/compter.sh` (Mac) et `poste.py comptes` / `comparer-comptes` comptent les
lignes de chaque table et comparent ; les quatre tables d'exploitation (journal, sessions,
registre des sauvegardes, état des tâches) sont dites, toute autre différence est un écart.
`poste.py --qui` nomme l'auteur au journal (« serveur Windows (scripts) »).

## 3. Mesures et preuves sur le Mac

- **Répétition du transfert** (15/10/2026, base « 3 ans » de l'épreuve de charge copiée en
  `gestion_mp_pro_wint_essai`) : `poste.py sauvegarder` puis `comptes` (171 245 lignes, dont
  38 266 mouvements, révision 0009) ; base supprimée, recréée **vide et migrée** (le serveur neuf) ;
  `poste.py --qui "serveur Windows (scripts)" restaurer … --confirmation RESTAURER` en **1,8 s** ;
  `comparer-comptes` : « **Mêmes lignes dans les 69 tables métier (153 700 lignes en tout)** »,
  remarques seulement sur `sauvegarde` (44 → 2), `session` (4 → 0), `tache_execution` (5 → 6) ;
  journal : la ligne « restauration » au nom de « serveur Windows (scripts) ».
- **Le paquet** (`gestion-mp-pro-windows-950a9f7.zip`, 3,1 Mo, 705 fichiers) déballé et servi tel
  quel (`PYTHONPATH=<paquet>/backend`, sans uvloop) : `/api/sante` 200, `version` = `950a9f7`
  (le `VERSION` du paquet), schéma migré au démarrage, écran servi depuis `frontend/dist` sans
  réglage, `/%5C%5Chote%5Cpartage%5Cx` → l'application (aucun accès au partage).
- **Mêmes chiffres** : aucune ligne de calcul, de requête métier ni d'API n'a changé ; la suite
  complète (parité de calcul comprise) passe à l'identique (`make verifier`, § 5) ; le transfert
  rend les mêmes lignes table par table.
- PowerShell n'est pas installé sur ce Mac (`pwsh` absent ; rien n'a été installé) : la syntaxe
  des scripts est contrôlée par `test_kit_windows.py` (BOM, `#Requires -Version 5.1`, blocs
  `() {} []` équilibrés hors chaînes et commentaires, aucun opérateur de PowerShell 7, réglages
  écrits connus de `config.py`, aucun secret ni téléchargement).

## 4. Ce qui ne pourra être prouvé que sur le serveur

Les scripts PowerShell eux-mêmes ; la tâche planifiée sous SERVICE LOCAL (démarrage au boot,
relance, arrêt) ; `icacls` et le TEMP du compte du service ; l'installation des roues depuis
`requirements-windows.lock` ; le démarrage avec `tzdata` ; points 13, 14, 17, 19, 22 de l'audit ;
le pare-feu et les profils réseau ; Caddy en service Windows (guide § 8.2). La recette
(`recette.ps1` + liste à cocher, guide § 10) est faite pour les constater en une fois.

## 5. Vérification

`make verifier` (base vide `gestion_mp_pro_win_verif_essai`, après `git merge main`) : **vert** —
ruff (PLW1514 comprise), ruff format, mypy strict (228 fichiers), pytest **3 125 réussis, 5 sautés**,
alembic check, prettier, eslint, stylelint, tsc, vitest **883 réussis, 1 sauté**, outils (345
appels de l'écran tous dans l'OpenAPI ; 289 preuves héritées reprises). `deploiement/verifier_fichiers.sh` :
30 ok, 0 KO (comme main).
Essais ajoutés : `tests/test_portabilite_windows.py` (36), `tests/test_kit_windows.py` (44).
