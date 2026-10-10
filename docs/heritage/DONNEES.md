# Héritage de Gestion MP — les données

> Inventaire exhaustif du **modèle de données** de Gestion MP (`/Users/mohamed/gestion-mp`, commit
> `959aefc` du 8 octobre 2026), écrit pour qu'une équipe reconstruise Gestion MP PRO **sans relire
> l'ancien code**. Source de vérité : le code. Les références `fichier:ligne` renvoient à
> `gestion_mp/` sauf mention contraire (`modeles.py:497` = `gestion_mp/modeles.py`, ligne 497).
>
> Contrôles faits pour écrire ce document (lecture seule) : lecture intégrale de `modeles.py`,
> `db.py`, `main.py`, `config.py`, `parametres.py`, `securite.py`, `services/stock.py`,
> `verificateur.py`, `depot.py`, `reprise.py` et des routes qui écrivent les tables ; DDL
> PostgreSQL rendu hors ligne depuis les modèles (aucune connexion) ; catalogue de la base en
> service `gestion_mp` lu en `default_transaction_read_only=on` (contraintes, index, défauts,
> `schema_version`, données semées) ; `git log` / `git log -p -- gestion_mp/db.py gestion_mp/modeles.py`.

## Sommaire

1. [Chiffres clés](#1-chiffres-clés)
2. [Conventions de lecture](#2-conventions-de-lecture)
3. [Connexion, moteur SQLAlchemy, fuseau, verrous](#3-connexion-moteur-sqlalchemy-fuseau-verrous)
4. [Évolution du schéma : `schema_version` et les 12 étapes](#4-évolution-du-schéma--schema_version-et-les-12-étapes)
5. [Données semées au démarrage](#5-données-semées-au-démarrage)
6. [Les énumérations (toutes les valeurs possibles)](#6-les-énumérations-toutes-les-valeurs-possibles)
7. [Les tables, une par une](#7-les-tables-une-par-une) — socle, référentiels, stock, achats, production, opérations, inventaire, importations, suivi, schéma
8. [Contenus JSON et données rangées dans du texte](#8-contenus-json-et-données-rangées-dans-du-texte)
9. [Le journal d'audit utilisé comme source de données](#9-le-journal-daudit-utilisé-comme-source-de-données)
10. [Schéma des relations (toutes les clés étrangères)](#10-schéma-des-relations-toutes-les-clés-étrangères)
11. [Cycle de vie : ce qui s'écrit, se fige, se supprime](#11-cycle-de-vie--ce-qui-sécrit-se-fige-se-supprime)
12. [Les invariants](#12-les-invariants)
13. [Glossaire des notions](#13-glossaire-des-notions)
14. [Points incohérents ou ambigus](#14-points-incohérents-ou-ambigus)

---

## 1. Chiffres clés

| Élément | Nombre | Détail |
|---|---|---|
| Tables | **49** | 48 déclarées dans `modeles.py` + `schema_version` (créée par `db.py:398-403`) |
| Colonnes | **405** | 402 dans les 48 tables des modèles + 3 dans `schema_version` |
| Clés étrangères | 73 | liste en § 10 |
| Contraintes CHECK | 39 | dont 4 nommées explicitement (`ck_article_unite_kg`, `ck_article_unite_prix`, `ck_article_prix_au_metre`, `ck_solde_positif`) |
| Contraintes UNIQUE (hors PK) | 24 | + 1 index unique (`dossier_facture_id_key` dans une base migrée) |
| Index non uniques | 9 | `ix_journal_quand`, `ix_parametre_historique_cle`, `ix_piece_jointe_objet_id`, `ix_recette_version_qualite_id`, `ix_lot_article_id`, `ix_mouvement_article_date`, `ix_mouvement_date_effet`, `ix_mouvement_lot_id`, `ix_mouvement_document_id` |
| Étapes de migration | **12** | numérotées 1 à 9, 11, 13, 14 — **10 et 12 n'existent pas** (§ 4.3) |
| Réglages (`parametre`) | 55 + 1 caché | § 7.1.5 |
| Invariants recensés | 42 | § 12 |
| Type numérique | `FLOAT` partout | **aucune colonne `Numeric`** : quantités, prix, montants, taux sont des `double precision` |

Familles (en-tête de `modeles.py:1-17`) : **socle** (comptes, sessions, journal, paramètres,
numérotation), **référentiels** (classification des fils, fournisseurs, articles, qualités,
recettes, plan, magasins, métiers, devises, postes de frais), **activité** (lots, soldes, journal
des mouvements, et les documents qui l'écrivent : commandes, réceptions, factures, bons de
sortie, opérations, inventaires, dossiers d'importation), **suivi** (réclamations, signalements,
pièces jointes, versions de recettes, indicateurs du jour).

---

## 2. Conventions de lecture

### 2.1 Traduction des types SQLAlchemy → PostgreSQL 16

| Déclaration (modèle) | Type PostgreSQL réel | Remarque |
|---|---|---|
| `Mapped[int] = mapped_column(primary_key=True)` | `SERIAL` (= `INTEGER` + séquence `<table>_id_seq`) | SQLAlchemy 2.1.3 ; pas d'`IDENTITY` |
| `String(n)` | `VARCHAR(n)` | longueur stricte : un texte plus long fait une erreur base |
| `Text` | `TEXT` | |
| `Float` | `FLOAT` = `double precision` (8 octets) | **jamais `Numeric`** (ni précision ni échelle) |
| `Integer` | `INTEGER` | |
| `Boolean` | `BOOLEAN` | |
| `Date` | `DATE` | |
| `DateTime` | `TIMESTAMP WITHOUT TIME ZONE` | heure **locale de Casablanca** (§ 3.2) |
| `mapped_column(ForeignKey("devise.code"))` sans type | type de la cible (`VARCHAR(3)` ici) | idem pour `role` (32), `composition` (32), `type_fil` (32), `titrage` (48), `couleur` (64), `code_douanier` (20), `poste` (16) |

### 2.2 Les trois fabriques de colonnes (`modeles.py:52-65`)

| Fabrique | Produit | Défaut Python | Défaut serveur |
|---|---|---|---|
| `maintenant()` (`:52-53`) | `datetime.now()` naïf (heure du processus, forcée à Casablanca) | — | — |
| `_texte(longueur=120, defaut="")` (`:56-57`) | `VARCHAR(longueur) NOT NULL` | `defaut` | `'defaut'` (ex. `DEFAULT ''`, `DEFAULT 'kg'`) |
| `_nombre(defaut=0.0)` (`:60-61`) | `FLOAT NOT NULL` | `defaut` | `str(defaut)` (ex. `DEFAULT '0'`, `'60'`, `'4.2'`, `'0.02'`) |
| `_actif()` (`:64-65`) | `BOOLEAN NOT NULL` | `True` | `'true'` |

Dans les tableaux ci-dessous, « défaut Py » est la valeur posée par l'ORM, « défaut SQL » celle
posée par la base. **Une colonne qui n'a qu'un défaut Python n'a AUCUN défaut en base** : une
insertion hors ORM (SQL brut, outil d'import) doit la fournir (liste en § 14, point 28).

### 2.3 Noms des contraintes

`Base` (`db.py:18-19`) n'a **pas de `naming_convention`**. Les noms sont donc ceux que PostgreSQL
génère, relevés dans la base en service :

- CHECK sans nom portant sur une colonne : `<table>_<colonne>_check` ; sur plusieurs colonnes :
  `<table>_check`, puis `<table>_check1`… ;
- UNIQUE : `<table>_<col1>_<col2>_key` ; FK : `<table>_<colonne>_fkey` ; PK : `<table>_pkey` ;
- index `index=True` : `ix_<table>_<colonne>` (convention SQLAlchemy par défaut).

Abréviations : **PK** clé primaire, **FK** clé étrangère, **UQ** unique, **CK** check,
**IX** index, **ODC** `ON DELETE CASCADE`, **OUC** `ON UPDATE CASCADE`.

### 2.4 Unités

- **Toute quantité de matière est en kilos** (décision de Mohamed du 8 octobre 2026, étape 14),
  cuir, franges et ruban compris. Les mètres linéaires (ml) ne sont qu'**indicatifs** :
  `kilos ÷ densité` pour un article d'un rôle linéaire (`Article.kg_par_ml`, `modeles.py:323-327`).
- Un **prix unitaire de mouvement, de ligne de commande, de réception, d'opération** est **au kilo**,
  dans la **devise** de la ligne (ou du bon).
- `article.prix` est exprimé dans l'unité `article.unite_prix` (`kg` ou `ml`) ; `prix_kg`
  (`modeles.py:315-321`) le ramène au kilo : `prix` si `kg`, `prix ÷ densite` si `ml`.
- Les **frais d'importation** (`dossier_charge.montant`, `dossier_charge_part.montant`) et
  `commande.montant_approuve` sont en **MAD**.
- Un **taux** est une fraction (0,02 = 2 %) sauf `recette.pourcentage` et
  `fil_monte.pourcentage` (0 à 100).
- Un **cours** (`devise.taux`, `*.cours`) = nombre de MAD pour 1 unité de devise.

---

## 3. Connexion, moteur SQLAlchemy, fuseau, verrous

### 3.1 Configuration (`config.py`, variables d'environnement)

| Variable | Défaut | Rôle | Réf. |
|---|---|---|---|
| `GESTION_MP_FUSEAU` | `Africa/Casablanca` | fuseau du processus **et** de chaque connexion | `config.py:11-13` |
| `GESTION_MP_BASE` | `postgresql+psycopg:///gestion_mp` | URL de la base (psycopg 3, socket local) | `config.py:15` |
| `GESTION_MP_PORT` | `8030` | port HTTP | `config.py:16` |
| `GESTION_MP_HTTPS` | `0` | cookie `secure` | `config.py:18` |
| `GESTION_MP_TACHES` | `1` | ce processus porte les tâches de fond | `config.py:20` |
| `GESTION_MP_SAUVEGARDES` | `~/gestion-mp-sauvegardes/` (+ sous-dossier au nom de la base si ce n'est pas `gestion_mp`) | sauvegardes `pg_dump -Fc` | `config.py:23-27` |
| `GESTION_MP_SAUVEGARDES_COPIE` | vide | second dossier de copie | `config.py:29` |
| `GESTION_MP_PG_BIN` | vide | dossier de `pg_dump` / `pg_restore` | `config.py:30` |
| `GESTION_MP_ECRAN` | `ecran/dist` | écrans construits | `config.py:33` |
| `GESTION_MP_SESSION_JOURS` | `30` | durée d'une session | `config.py:34` |
| `GESTION_MP_ERP_FIL` | `~/Library/Application Support/ERP Fil/gestion-fil.db` | base SQLite de l'ERP Fil (reprise, lecture seule) | `config.py:36-41` |
| `GESTION_MP_PIECES` | `~/gestion-mp-pieces/` (+ sous-dossier au nom de la base) | fichiers des pièces jointes | `config.py:44-45` |
| `GESTION_MP_SMTP_HOTE`, `_PORT` (587), `_UTILISATEUR`, `_MOT_DE_PASSE`, `_EXPEDITEUR` | — | courriel du lundi | `services/courriel.py:85-93` |

Versions en service : SQLAlchemy 2.1.3, psycopg 3.3.6, FastAPI 0.142.2, PostgreSQL 16 (Homebrew
`postgresql@16`), Python ≥ 3.12 (`pyproject.toml`).

### 3.2 Le fuseau horaire

- `config.py:11-13` : `os.environ["TZ"] = FUSEAU; time.tzset()` — **tout le processus** compte
  l'heure du Maroc, quel que soit le réglage du Mac. `date.today()` et `datetime.now()` (donc
  `maintenant()`) sont l'heure de Casablanca.
- `db.py:13-14` : chaque connexion reçoit `options="-c timezone=Africa/Casablanca"` : `now()`,
  `LOCALTIMESTAMP`, `CURRENT_DATE` côté base sont aussi l'heure du Maroc.
- Toutes les colonnes horodatées sont `TIMESTAMP WITHOUT TIME ZONE` : elles contiennent une
  heure **locale** de Casablanca, sans décalage enregistré.
- Le serveur renvoie son heure dans l'en-tête `X-Heure-Serveur` (`main.py:158-160`) : l'écran
  l'affiche plutôt que celle du poste (commit 238729e, 9724d96).

### 3.3 Le moteur et les sessions (`db.py:13-28`)

```
moteur = create_engine(config.BASE, pool_pre_ping=True, pool_size=10, max_overflow=20,
                       connect_args={"options": f"-c timezone={config.FUSEAU}"})
Sessions = sessionmaker(bind=moteur, autoflush=False, expire_on_commit=False)
```

- `pool_pre_ping=True` : une connexion morte (base redémarrée, restauration) est remplacée.
- `pool_size=10`, `max_overflow=20` : jusqu'à 30 connexions par processus.
- `autoflush=False` : rien n'est envoyé à la base avant un `flush()` / `commit()` explicite.
- `expire_on_commit=False` : les objets restent lisibles après `commit()`.
- `session()` (`db.py:22-28`) : dépendance FastAPI, une session par requête, fermée dans un `finally`.
- Niveau d'isolation : celui par défaut de PostgreSQL (**READ COMMITTED**) ; la cohérence repose
  sur les verrous ci-dessous.

### 3.4 Les verrous

| Verrou | Nature | Où | Pourquoi |
|---|---|---|---|
| `pg_advisory_xact_lock(7426101)` | consultatif, transaction | `db.py:397` | un seul processus migre ; les autres attendent |
| `pg_try_advisory_lock(7426102)` | consultatif, **session** (tenu par une connexion dédiée gardée ouverte) | `main.py:92-98` | un seul processus porte les tâches de fond (photo des indicateurs, courriel du lundi, sauvegarde du jour, toutes les 15 min) |
| `pg_advisory_xact_lock(7426110)` | consultatif, transaction | `api/production.py:32,515` | la validation d'un ordre de fabrication lit la date du dernier ordre sans course |
| `SELECT … FOR UPDATE` sur `solde` | ligne | `services/stock.py:63-74` | **le** verrou du stock : sérialise toute écriture sur un même (lot, magasin) |
| `FOR UPDATE` sur `compteur` | ligne | `securite.py:178-196`, `api/receptions.py:59-60` | numéros sans doublon |
| `FOR UPDATE` sur `commande`, puis `commande_ligne` (triés par id) | ligne | `api/receptions.py:522-528` | deux réceptions sur la même ligne de bon passent l'une après l'autre |
| `FOR UPDATE OF solde` à l'ouverture d'un inventaire | ligne | `api/inventaires.py:308` | figer le théorique sans mouvement en cours |
| `FOR UPDATE OF commande/operation/reception/bon_sortie/inventaire/dossier` | ligne | `api/achats.py:520`, `api/operations.py:360,413`, `api/receptions.py:464`, `api/production.py:450`, `api/inventaires.py:338,383,421`, `api/importations.py:633,1070` | modifier/valider un document une seule fois |
| `FOR UPDATE` sur `fournisseur`, `article`, `qualite`, `metier`, `poste_frais`, `code_douanier` | ligne | `api/referentiels.py:384,626,878,940,996,1300,1403,1424`, `api/referentiels_import.py:117,148,253` | modifications concurrentes des fiches |
| `FOR SHARE` (`read=True`) sur `reception` | ligne | `api/importations.py:432` | rattacher des lignes à un dossier |
| Verrou optimiste `article.version` | applicatif | `api/referentiels.py:629-644` | refus 409 si la fiche a changé entre lecture et écriture |
| Verrou optimiste « empreinte » du métier | applicatif (empreinte calculée, non stockée) | `api/referentiels.py:1118-1133,1144-1145` | montage d'un étage depuis le téléphone |
| Verrou Python `_verrou_cache` | processus | `depot.py:669-703` | cache des données du moteur |

---

## 4. Évolution du schéma : `schema_version` et les 12 étapes

### 4.1 Le mécanisme (`db.py:374-414`)

```
ETAPES: list[tuple[int, str, Callable[[Connection], None]]] = [(1, …), …, (14, …)]

def migrer():
    with moteur.begin() as c:                                  # UNE transaction pour tout
        c.execute("SELECT pg_advisory_xact_lock(7426101)")     # un seul migrateur
        c.execute("CREATE TABLE IF NOT EXISTS schema_version (numero INTEGER PRIMARY KEY, "
                  "libelle TEXT NOT NULL, applique_le TIMESTAMP NOT NULL DEFAULT now())")
        faites = {numero de schema_version}
        for numero, libelle, etape in ETAPES:
            if numero in faites: continue
            etape(c)
            INSERT INTO schema_version (numero, libelle) VALUES (:n, :l)
```

- Règle écrite (`db.py:374-375`) : « On n'édite jamais une étape livrée : on en ajoute une. »
- **Tout ou rien** : toutes les étapes manquantes s'appliquent dans la même transaction ; une
  erreur annule l'ensemble. `applique_le = now()` = instant de début de la transaction : les
  étapes d'un même démarrage portent la même heure (vu en base : 7, 8, 9 à `2026-10-08
  15:33:49.630603` ; 11 et 13 à `16:25:09.876281`).
- Appelée par `main.initialiser()` à chaque démarrage (`main.py:53`), par `reprise.py`, par les
  outils (`outils/importer_erp_fil.py`, `outils/vider_activite.py`).
- La version du schéma est exposée : `GET /api/sante` → `SELECT MAX(numero) FROM schema_version`
  (`main.py:193-194`) et l'écran Installation (`api/comptes.py:513`).
- **Base neuve** : l'étape 1 fait `Base.metadata.create_all()` avec les modèles **d'aujourd'hui** :
  toutes les colonnes ajoutées plus tard existent donc déjà ; les étapes 2 à 14 ne font alors que
  des `IF NOT EXISTS` sans effet et des mises à jour de données sur des tables vides.
- **Base ancienne** : chaque étape ajoute ce qui manque et convertit les données.

### 4.2 Les 12 étapes

| N° | Libellé (`schema_version.libelle`) | Fonction | Commit d'origine |
|---|---|---|---|
| 1 | schéma initial | `_schema_initial` `db.py:31-34` | ad52be7 (03/10) |
| 2 | inventaire : palettes et bobines comptées | `_inventaire_palettes` `db.py:37-39` | 783c4d5 (03/10) |
| 3 | numéros donnés à l'envoi ou à la validation | `_numeros_a_la_validation` `db.py:42-44` | 08c6df7 (03/10) |
| 4 | compléments de l'audit de conformité | `_complements_audit` `db.py:47-74` | 590027d (03/10) |
| 5 | réclamations, besoins signalés, pièces jointes, historiques | `_suivi` `db.py:77-87` | 3e12a08 (03/10) |
| 6 | un dossier d'importation par facture | `_dossier_par_facture` `db.py:111-116` | 8116063 (08/10 13:41) |
| 7 | le cours de la devise figé sur chaque mouvement | `_cours_des_mouvements` `db.py:119-145` | 5ca0960 (08/10 14:51) |
| 8 | montant approuvé des bons, paiements, bons soldés rouverts | `_commandes_et_paiements` `db.py:148-164` | bcb14b5 (08/10 14:48) |
| 9 | prévu des ordres figé, poids gardés avec les recettes | `_theorique_fige` `db.py:167-193` | db25831 (08/10 14:58) |
| 11 | version partie des bons, date promise comptée à l'envoi | `_version_partie_des_bons` `db.py:196-227` | d68dbb2 (08/10 15:53) |
| 13 | importations : poids des marchandises et répartition des frais figés | `_importations_figees` `db.py:233-279` | 58f507c (08/10 15:58) |
| 14 | stock en kilos, prix au kilo ou au mètre | `_stock_en_kilos` `db.py:282-371` | d2e1e39 (08/10 19:19) |

#### Étape 1 — schéma initial (`db.py:31-34`)

- **Crée** : `Base.metadata.create_all(c)` après import de `modeles` — les 48 tables, leurs PK,
  FK, UQ, CK, index, séquences, **dans la forme actuelle des modèles**.
- **Reprend** : rien.
- **Idempotence** : `create_all` ignore une table existante (`checkfirst`) ; il ne modifie jamais
  une table existante.

#### Étape 2 — palettes et bobines comptées à l'inventaire (`db.py:37-39`)

- `ALTER TABLE inventaire_ligne ADD COLUMN IF NOT EXISTS nb_palettes DOUBLE PRECISION`
- `ALTER TABLE inventaire_ligne ADD COLUMN IF NOT EXISTS nb_bobines DOUBLE PRECISION`
- Nullables, sans défaut. Aucune donnée reprise. Idempotente (`IF NOT EXISTS`).

#### Étape 3 — numéros donnés à l'envoi ou à la validation (`db.py:42-44`)

- `ALTER TABLE {commande, reception, operation} ALTER COLUMN numero DROP NOT NULL`.
- Raison : exigence **M65** — un brouillon supprimé ne laisse pas de trou dans la série ; le numéro
  n'est donné qu'à l'envoi (bon de commande) ou à la validation. (`bon_sortie.numero` était déjà
  nullable.)
- Idempotente (retirer `NOT NULL` d'une colonne déjà nullable ne fait rien).

#### Étape 4 — compléments de l'audit de conformité (`db.py:47-74`)

`ADD COLUMN IF NOT EXISTS` de 17 colonnes :

| Table | Colonne | Type ajouté |
|---|---|---|
| composition | composition_detaillee | `VARCHAR(160) NOT NULL DEFAULT ''` |
| composition, type_fil, titrage, couleur, metier | commentaire | `TEXT NOT NULL DEFAULT ''` |
| magasin | contenu | `VARCHAR(120) NOT NULL DEFAULT ''` |
| fil_monte | commentaire | `VARCHAR(300) NOT NULL DEFAULT ''` |
| poste_frais | cle | `VARCHAR(8) NOT NULL DEFAULT 'valeur'` |
| fournisseur | port_chargement | `VARCHAR(80) NOT NULL DEFAULT ''` |
| fournisseur | banque | `VARCHAR(120) NOT NULL DEFAULT ''` |
| commande | acompte_le, arrivee_usine_le | `DATE` |
| reception | controle_par | `VARCHAR(80) NOT NULL DEFAULT ''` |
| dossier_ligne | commentaire | `VARCHAR(300) NOT NULL DEFAULT ''` |
| dossier_charge | prestataire | `VARCHAR(120) NOT NULL DEFAULT ''` |
| dossier_charge | date_piece, echeance | `DATE` |

Puis :
- `CREATE TABLE IF NOT EXISTS code_douanier (code VARCHAR(20) PRIMARY KEY, libelle VARCHAR(120) NOT NULL DEFAULT '', taux_droits DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (taux_droits >= 0 AND taux_droits <= 1), actif BOOLEAN NOT NULL DEFAULT true)` ;
- `ALTER TABLE code_douanier ALTER COLUMN libelle TYPE VARCHAR(160)` ;
- `ALTER TABLE article ADD COLUMN IF NOT EXISTS code_douanier VARCHAR(20) REFERENCES code_douanier(code) ON UPDATE CASCADE`.

Aucune donnée reprise. Idempotente (l'`ALTER TYPE` rejoué est sans effet).

#### Étape 5 — suivi (`db.py:77-87`)

- Crée (depuis les modèles **actuels**, `checkfirst=True`) : `reclamation`, `signalement`,
  `piece_jointe`, `recette_version`, `indicateur_jour`.
- `inventaire_ligne.second_compte DOUBLE PRECISION` ; `inventaire_ligne.second_par VARCHAR(80) NOT NULL DEFAULT ''`.
- Aucune donnée reprise. Idempotente.

#### Étape 6 — un dossier d'importation par facture (`db.py:90-116`)

- `ALTER TABLE dossier ADD COLUMN IF NOT EXISTS facture_id INTEGER REFERENCES facture(id)` ;
- `CREATE UNIQUE INDEX IF NOT EXISTS dossier_facture_id_key ON dossier (facture_id)` (dans une
  base neuve, c'est une **contrainte** UNIQUE du même nom que crée l'étape 1 ; dans une base
  migrée, un **index** unique — même effet) ;
- **Reprise** : `relier_dossiers_aux_factures(c)` (`db.py:90-108`) :

```sql
UPDATE dossier d SET facture_id = x.facture_id FROM (
  SELECT dl.dossier_id, MIN(r.facture_id) AS facture_id FROM dossier_ligne dl
  LEFT JOIN reception_ligne rl ON rl.id = dl.reception_ligne_id
  LEFT JOIN reception r ON r.id = rl.reception_id
  GROUP BY dl.dossier_id
  HAVING COUNT(*) = COUNT(r.facture_id) AND COUNT(DISTINCT r.facture_id) = 1) x
WHERE d.id = x.dossier_id AND d.facture_id IS NULL
  AND (nombre de dossiers distincts portant une ligne de cette facture) = 1
  AND NOT EXISTS (SELECT 1 FROM dossier d3 WHERE d3.facture_id = x.facture_id)
```

  Un dossier dont **toute** la marchandise vient d'**une seule** facture, que nul autre dossier
  ne porte, prend cette facture ; les autres (plusieurs factures, facture partagée, lignes
  saisies à la main) restent sans. Rend le nombre de dossiers reliés. Réutilisée à la fin de
  l'import de l'activité de l'ERP Fil (`outils/importer_erp_fil.py:332`).
- Idempotente : ne touche que les dossiers sans facture et les factures sans dossier.

#### Étape 7 — cours de la devise figé sur chaque mouvement (`db.py:119-145`)

- `ALTER TABLE mouvement ADD COLUMN IF NOT EXISTS cours DOUBLE PRECISION NOT NULL DEFAULT 0`.
- **Reprise 1** : pour chaque mouvement `document='reception' AND type='RECEPTION' AND devise <> 'MAD'`,
  retrouver sa ligne de réception (même lot, même article, même devise, réception = `document_id` ;
  ou, pour une entrée reprise de l'ERP Fil sans `document_id`, même date et même pesée à 1e-6
  près) et poser `cours = MAX(COALESCE(cours de la ligne de dossier si même devise et > 0, cours de
  la commande si même devise et > 0))`, seulement si `mv.cours = 0`.
- **Reprise 2** : tout mouvement restant en devise étrangère avec `prix > 0` et `cours = 0` prend
  le **cours actuel** de la devise (`devise.taux`) — « à défaut de mieux ».
- Idempotente : la condition `cours = 0` empêche de réécrire.

#### Étape 8 — montant approuvé, paiements, bons rouverts (`db.py:148-164`)

- `commande.montant_approuve DOUBLE PRECISION NOT NULL DEFAULT 0` ; `facture.payee_le DATE` ;
  `dossier_charge.payee_le DATE`.
- **Reprise** : ouvre une session ORM sur la connexion de migration et appelle
  `api.achats.recaler_soldes(s, None, {toutes les commandes 'soldee'}, "reçu recompté net des
  retours (mise à jour)")` : un bon soldé de lui-même que des retours au fournisseur (ou une
  quarantaine non libérée) ont dégarni se **rouvre** (statut `envoyee`/`confirmee`), avec une
  ligne de journal « commande rouverte » au nom de « système ».
- Dépend du **code applicatif vivant** (`api/achats.py:572-603`) : la migration n'est pas figée.
- Convergente (rejouée, elle ne rouvrirait que ce qui doit l'être) ; protégée par `schema_version`.

#### Étape 9 — prévu des ordres figé, poids gardés avec les recettes (`db.py:167-193`)

- `bon_sortie.theorique TEXT` ; `recette_version.poids TEXT`.
- **Reprise 1** : la **dernière** version de chaque qualité (`MAX(id)` par `qualite_id`) sans poids
  reçoit les poids actuels : `COALESCE(json_object_agg(p.role, p.poids), '{}')` de `qualite_poids`.
- **Reprise 2** : une qualité qui a des lignes de recette mais **aucune** version en reçoit une :
  `par = 'relevé à la mise à jour'`, `quand = LOCALTIMESTAMP`, `contenu = json_agg({reference,
  role, pourcentage} ORDER BY role)`, `poids` = JSON des poids.
- Les ordres déjà validés restent sans `theorique` : le moteur les recalcule avec la recette en
  vigueur le jour de leur validation.
- Idempotente (conditions `poids IS NULL`, `NOT EXISTS`).

#### Étape 11 — version partie des bons, date promise à l'envoi (`db.py:196-227`)

- `commande.version_approuvee TEXT NOT NULL DEFAULT ''`.
- **Reprise 1** : efface la date promise d'un brouillon non numéroté (`numero IS NULL`, statut
  `brouillon` ou `a_approuver`) quand elle vaut exactement `date_commande + FLOOR(delai_jours)`
  (la date comptée d'office à la création) : elle se compte désormais **à l'envoi**.
- **Reprise 2** : pour chaque bon numéroté, statut ≠ `a_approuver`, `version_approuvee = ''` :
  `figer_version(s, bon, montant=True)` (`api/achats.py:220-230`), puis, si `montant_approuve`,
  `v["montant"] = montant_approuve / (cours du bon ou taux du jour ou 1)` (le montant de
  référence ramené dans la devise du bon). Dépend du code applicatif vivant.
- Idempotente (condition `version_approuvee = ''`).

#### Étape 13 — importations : poids et répartition figés (`db.py:233-279`)

- `dossier_ligne.poids_kg DOUBLE PRECISION` ; `UPDATE dossier_ligne SET poids_kg = quantite ×
  (densite si article.unite = 'ml', sinon 1) WHERE poids_kg IS NULL`.
- Crée `dossier_charge_part` (depuis le modèle).
- **Reprise** des « morceaux » : les frais qu'un ancien changement de clé avait éclatés (un par
  marchandise, `ligne_id NOT NULL`, commentaire contenant `NOTE_FIGEAGE = "avant le changement de
  clé du"`, `db.py:230`) sont regroupés par (dossier, poste, pièce, prestataire, date de pièce,
  échéance, commentaire d'origine, note) — le commentaire a la forme « *origine* · réparti … avant
  le changement de clé du jj/mm/aaaa ». Pour chaque groupe d'au moins 2 morceaux : une nouvelle
  charge (`ligne_id NULL`, `montant = round(Σ, 2)`, `commentaire = origine`, `payee_le` = la plus
  tardive des dates de règlement des morceaux), une `dossier_charge_part` par ligne (Σ des
  morceaux de la ligne), puis `DELETE` des morceaux.
- Idempotente en pratique (plus de morceaux après le premier passage).

#### Étape 14 — stock en kilos, prix au kilo ou au mètre (`db.py:282-371`)

Décision de Mohamed (8 octobre 2026) : une matière « au mètre » (`article.unite = 'ml'`) passe au
kilo. Pour chaque article `unite = 'ml' AND densite > 0` (`d` = sa densité, kg/ml) — les montants
(quantité × prix) ne bougent pas :

| Table | Conversion (`t` = ligne, `x.d` = densité) |
|---|---|
| article (nouvelle colonne) | `unite_prix VARCHAR(4) NOT NULL DEFAULT 'kg'` |
| mouvement | `quantite × d`, `prix ÷ d` |
| commande_ligne | `quantite × d`, `prix ÷ d`, `contenance = 1` si `unite_achat ∈ {kg, ml}` sinon `× d`, `unite_achat 'ml' → 'kg'` |
| reception_ligne | `quantite_attendue`, `quantite_bl`, `quantite_pesee × d` ; `prix ÷ d` |
| bon_ligne | `quantite × d` |
| operation_ligne | `quantite × d`, `prix ÷ d` |
| dossier_ligne | `poids_kg = COALESCE(poids_kg, quantite × d)`, `quantite × d` |
| lot | `poids_bobine × d` |
| solde (par le lot) | `quantite × d` |
| inventaire_ligne (par le lot) | `theorique`, `compte`, `second_compte × d` |
| reclamation (par le lot) | `quantite × d` |
| article | `stock_min`, `minimum_commande`, `poids_bobine × d` ; `contenance_achat` et `unite_achat` comme commande_ligne |
| bon_sortie.theorique (JSON) | `fils[référence] × densité` pour les références concernées |
| commande.version_approuvee (JSON) | pour chaque ligne de l'article : `quantite × k`, `prix ÷ k`, `unite_achat/contenance` comme ci-dessus |

Puis : `UPDATE article SET unite = 'kg', unite_prix = 'kg' WHERE unite <> 'kg'` (le **prix du
catalogue garde sa valeur**, désormais lue au kilo : le propriétaire le corrige ou choisit « au
mètre ») ; `DROP CONSTRAINT IF EXISTS` `article_unite_check` (le CHECK `unite IN ('kg','ml')` de
l'étape 1), `ck_article_densite_lineaire`, `ck_article_unite_kg`, `ck_article_unite_prix`,
`ck_article_prix_au_metre` ; `ADD CONSTRAINT ck_article_unite_kg CHECK (unite = 'kg')`,
`ck_article_unite_prix CHECK (unite_prix IN ('kg','ml'))`, `ck_article_prix_au_metre CHECK
(unite_prix = 'kg' OR densite > 0)`.

Non convertis : `inventaire_ligne.nb_palettes/nb_bobines` (des comptes), `qualite_poids` (reste en
ml/m² pour un rôle linéaire), `fil_monte.metres` (mètres de laize), `reclamation.montant_*`.
Idempotente : après le premier passage aucun article n'est plus en `ml` ; les contraintes sont
supprimées puis recréées.

### 4.3 Pourquoi il n'y a ni étape 10 ni étape 12

- `git log --all -p -- gestion_mp/db.py` : **aucune** ligne `(10, …)` ni `(12, …)` n'a jamais
  existé, sur aucune branche (le dépôt n'a que `main`).
- Les étapes 6 à 13 ont été écrites le 8 octobre par des **équipes parallèles** (copies de
  travail fusionnées : commits « Fusion : … », « Fusion de main : … »). Les numéros ont visiblement
  été **réservés d'avance par équipe** : l'étape **8** (bcb14b5, 14:48) a été livrée **avant** la
  **7** (5ca0960, 14:51) ; l'étape 11 (branche achats, d68dbb2) et l'étape 13 (branche
  importations, 58f507c) ont été fusionnées par 93fd464 (« l'étape 11 se range avant la 13 ») —
  le parent 1 de cette fusion avait `…, 9, 11`, le parent 2 `…, 9, 13`. Les numéros 10 et 12,
  réservés pour d'autres équipes, n'ont jamais servi (déduction : aucun message ne le dit).
- La correction « matières au mètre comptées en mètres partout » (45c3d2c, 14:51), défaite par
  l'étape 14, **n'avait pas d'étape de schéma** (elle ne changeait que le code et les CHECK
  restaient ceux de l'étape 1).
- Conséquence : la boucle `migrer()` ne suppose pas des numéros contigus ; `MAX(numero)` (14) n'est
  pas le nombre d'étapes (12).

---

## 5. Données semées au démarrage

`main.initialiser()` (`main.py:50-85`), appelée à chaque démarrage (`main.py:119-123`) et par la
reprise : d'abord `migrer()`, puis, **sans jamais écraser ce qui existe** :

### 5.1 Rôles de nomenclature (`main.py:55-58`, `calcul/modele.py:23-24`)

Pour chaque code de `ROLES` absent : `RoleNomenclature(code, lineaire = code ∈ ROLES_LINEAIRES, ordre = index)`.

| code | lineaire | ordre | Unité du poids au m² (`qualite_poids.poids`) |
|---|---|---|---|
| Poil | false | 0 | kg/m² |
| Chaîne | false | 1 | kg/m² |
| Trame | false | 2 | kg/m² |
| Colle | false | 3 | kg/m² |
| **Cuir** | **true** | 4 | **ml/m²** (× densité = kg/m²) |
| **Franges** | **true** | 5 | **ml/m²** |
| **Ruban** | **true** | 6 | **ml/m²** |
| Plastique | false | 7 | kg/m² |

Ces 8 codes sont des **rôles de base** : non supprimables, non renommables
(`api/referentiels.py:138-139,168-169`) ; `lineaire` doit valoir exactement `code ∈ {Cuir,
Franges, Ruban}` (`api/referentiels.py:109-116`). D'autres rôles peuvent être ajoutés par la
direction (`lineaire = false` obligatoire).

### 5.2 Postes de frais d'importation (`main.py:59-73`, `calcul/modele.py:518-534`)

Pour chaque poste de `POSTES_IMPORT` absent : `PosteFrais(code, libelle, recuperable, ordre)` ;
`cle` prend le défaut serveur `'valeur'`. Un poste ajouté à une base déjà remplie se place juste
après son prédécesseur dans la liste, les suivants descendent d'un rang (`main.py:63-71`).

| ordre | code | libellé | récupérable | clé (défaut) | Poste « système » (`api/referentiels_import.py:40`) |
|---|---|---|---|---|---|
| 0 | DD | Droits de douane | non | valeur | oui (coût) |
| 1 | TPI | Taxe parafiscale à l'importation | non | valeur | oui (coût ; 0,25 % de la valeur en douane, entre dans la base de la TVA) |
| 2 | TVA | TVA à l'importation | **oui** | valeur | oui (récupérable : jamais dans le coût) |
| 3 | PORT | Port Med | non | valeur | |
| 4 | FRET | Fret | non | valeur | oui |
| 5 | ASSUR | Assurance | non | valeur | oui (entre dans la valeur en douane CAF) |
| 6 | TRANSIT | Transitaire | non | valeur | |
| 7 | TIMBRE | Timbre | non | valeur | |
| 8 | INT_OC | Intérêts / ordre de change | non | valeur | |
| 9 | TMSA | TMSA | non | valeur | |
| 10 | AUTRE | Autre frais | non | valeur | |

Un poste système ne se supprime pas et ne change pas de nature (récupérable/coût). Un poste qui
porte des frais ne se supprime pas ; qui porte des frais dans un dossier clos ne change pas de
nature (`api/referentiels_import.py:150-186`).

### 5.3 Devises (`main.py:45,74-77`)

| code | nom | taux semé (MAD pour 1) |
|---|---|---|
| MAD | Dirham | 1.0 |
| USD | Dollar américain | 10.0 |
| EUR | Euro | 10.8 |

Seulement si le code est absent. (Base en service : EUR 11, USD 9,5 — saisis ou repris de l'ERP Fil
par `reprise.py:97-103`.) Le cours de MAD reste 1 (`api/comptes.py:439-440`).

### 5.4 Magasins (`main.py:46,78-82`)

| code (= nom) | type |
|---|---|
| Magasin principal | Stock courant |
| Quarantaine | Quarantaine |

Chacun n'est créé que si **aucun magasin de ce type** n'existe **et** que ce code n'existe pas :
« un magasin courant, une quarantaine : toujours ». (Base en service : `Polyfashions`, `Morocco`
repris de l'ERP Fil, et `Quarantaine`.)

### 5.5 Réglages (`main.py:84`, `parametres.installer` `parametres.py:149-154`)

Les 55 réglages de `REGLAGES` absents sont écrits avec leur valeur par défaut
(`valeur = str(defaut)`, `modifie_par = 'installation'`). Liste en § 7.1.5.

### 5.6 Ce qui n'est pas semé

- **Compteurs** : aucun ; une ligne `(serie, annee)` naît au premier numéro demandé
  (`securite.py:189-191,199-206`, `INSERT … ON CONFLICT DO NOTHING`). Le compteur `LOT` rattrape
  d'abord le plus grand `LOT-AAAA-NNNN` déjà en base (`api/receptions.py:50-67`).
- **Utilisateurs** : aucun ; `POST /api/installation` crée le **premier** compte (direction), une
  seule fois (`api/comptes.py:84-101`). Le vérificateur crée/réactive un compte technique
  `verificateur` (rôle direction, désactivé en dehors de son exécution, `verificateur.py:335-351`).
- **Classification, fournisseurs, articles, qualités, recettes, métiers, fils montés** : repris de
  l'ERP Fil par `python -m gestion_mp.reprise` (§ 7.11).

---

## 6. Les énumérations (toutes les valeurs possibles)

### 6.1 Rôles des utilisateurs (`modeles.py:41-49`)

| Valeur | Libellé | Droits essentiels (`securite.py:131-136`) |
|---|---|---|
| `direction` | Direction | passe partout (`droit()` laisse toujours passer la direction) |
| `achats` | Responsable achats | achats, réceptions, importations, référentiels, inventaire, suivi |
| `alimentation` | Responsable alimentation machines | ordres de fabrication, retours machine, transferts, montage ; **ne voit aucun prix** ; code de 4 caractères minimum (8 pour les autres, `securite.py:47-49`) |

### 6.2 Types de magasin (`modeles.py:390`)

`Stock courant` (stock disponible) · `Quarantaine` (en stock, à part : n'est pas disponible pour
sortir, ne compte pas pour les achats ; on y entre par une réception « sous réserve » ou une
« Mise en quarantaine », on en sort par « Libération de quarantaine » ou un retour au fournisseur).

### 6.3 Types de mouvement (`modeles.py:486-494`, `calcul/modele.py:28-37`)

| `mouvement.type` | Libellé | Code du moteur | Signe | Document qui l'écrit | Quantité écrite |
|---|---|---|---|---|---|
| `OUVERTURE` | Stock d'ouverture | `STOCK_INITIAL` | + | `operation` type `ouverture` | > 0, avec prix et devise |
| `RECEPTION` | Entrée de réception | `ENTREE_RECEPTION` | + | `reception` | pesée > 0 (ligne non refusée) |
| `SORTIE` | Sortie vers les machines | `SORTIE_PROD` | − | `sortie` (bon_sortie) | < 0, `ordre_id` = l'ordre |
| `RETOUR_MACHINE` | Retour des machines | `RETOUR_PRODUCTION` | + | `operation` type `retour_machine` | > 0, `ordre_id` = l'ordre |
| `RETOUR_FOURNISSEUR` | Retour au fournisseur | `RETOUR_FOURNISSEUR` | − | `operation` type `retour_fournisseur` | < 0 |
| `AJUSTEMENT` | Ajustement d'inventaire | `AJUSTEMENT_INVENTAIRE` | ± | `operation` type `ajustement` ou `inventaire` | signée |
| `TRANSFERT` | Transfert entre magasins | `TRANSFERT_MAGASIN` | 0 (2 lignes) | `operation` type `transfert` | −q à la source, +q à la destination, même `paire` |

Le moteur connaît aussi `QUARANTAINE` (« 🚫 Quarantaine », signe 0, `calcul/modele.py:36`) que la
base **refuse** (CHECK) : la quarantaine est un magasin, pas un type de mouvement. Une
contre-passation garde le **type** de l'original avec la quantité opposée.

### 6.4 `mouvement.document` (valeurs écrites, sans CHECK)

| Valeur | `document_id` pointe vers | Écrit par |
|---|---|---|
| `reception` | `reception.id` | `api/receptions.py:557` |
| `sortie` | `bon_sortie.id` | `api/production.py:524` |
| `operation` | `operation.id` | `api/operations.py:421` |
| `inventaire` | `inventaire.id` | `api/inventaires.py:407` |
| `reprise` | NULL | seulement dans une base `_comparaison` (`outils/importer_erp_fil.py:60-62`) |

Libellés d'affichage : `api/exports.py:43-44`.

### 6.5 Motifs de mouvement et codes R1–R6 (`api/operations.py:36-56`)

| Type d'opération | Motifs proposés | Code ERP Fil |
|---|---|---|
| retour_machine | Reliquat de fin d'ordre | **R1** |
| | Changement de série / arrêt machine | **R2** |
| | Erreur de prélèvement | **R4** |
| retour_fournisseur | Non-conformité qualité | **R3** |
| | Excédent de réception | **R5** |
| | Bobines endommagées | **R6** |
| | Refus après quarantaine | **R3** |
| ajustement | Écart constaté au comptage · Matière retrouvée · Perte / casse · Correction de saisie | — |
| transfert | Rangement · **Libération de quarantaine** · **Mise en quarantaine** · Approvisionnement de l'atelier | — |
| (inventaire) | « Écart d'inventaire » (`api/inventaires.py:408`) | — |

Le motif est obligatoire pour retour machine, retour fournisseur, ajustement ; un ajustement
exige aussi un commentaire d'au moins 5 caractères (`api/operations.py:242-245`). Le moteur lit le
code R par `depot._code_motif` (`depot.py:226-233`) : libellé → code, ou deux premiers caractères
« R<chiffre> » d'un motif repris.

Commentaires conventionnels d'un mouvement : « sous réserve » (entrée en quarantaine,
`api/receptions.py:560`), « Annulation du mouvement n°X » (contre-passation, `services/stock.py:261`),
« Annulation du mouvement n°X (avec OF-…) » (retour repris annulé avec son ordre,
`api/production.py:546`), justification d'inventaire + « recompté par … ».

### 6.6 Statuts de commande (`modeles.py:542-549`)

| Statut | Libellé | Sens | Statut pour le moteur (`depot.py:23-40`) |
|---|---|---|---|
| `brouillon` | Brouillon | en préparation, sans numéro | Brouillon (mais « Envoyée »/« Confirmée » s'il a un numéro) |
| `a_approuver` | À approuver | **sans numéro** : brouillon au-delà du seuil, soumis à la direction ; **avec numéro** : bon parti dont une hausse attend la direction (il reste attendu du fournisseur) | idem |
| `envoyee` | Envoyée | parti chez le fournisseur (numéro donné), prix pas tous confirmés | Envoyée |
| `confirmee` | Confirmée | parti, toutes les lignes ont un prix confirmé | Confirmée |
| `soldee` | Soldée | n'attend plus rien : tout reçu (automatique) ou soldé à la main | Soldée |
| `annulee` | Annulée | clos sans aucune réception validée | Annulée |

Transitions : `brouillon →(envoyer, sous le seuil)→ envoyee|confirmee` ; `brouillon →(envoyer, au-delà
du seuil)→ a_approuver →(approuver)→ envoyee|confirmee` ou `→(renvoyer)→ brouillon` ;
`envoyee →(tous prix confirmés)→ confirmee` ; parti `→(hausse au-delà du seuil ou de la
référence)→ a_approuver` (avec numéro) `→(approuver | ramener | renvoyer = version partie
rétablie)→ envoyee|confirmee` ; `envoyee|confirmee →(chaque ligne reçue, rien en quarantaine)→ soldee`
(`api/achats.py:594-597`) ; `soldee (auto) →(retour, annulation de réception)→ envoyee|confirmee`
(« commande rouverte ») ; clôture à la main → `soldee` si une réception validée existe, sinon
`annulee` (`api/achats.py:902`). Un brouillon modifié pendant l'approbation redevient brouillon
(`api/achats.py:265-271`).

États de livraison dérivés (non stockés, `api/achats.py:79-102`) : 🟢 Livré · ⚫ Soldé · ⚫ Soldé
sans livraison · ⚫ Annulé · 🟡 Reçu sous réserve · 🟡 En cours · 🟠 Partiel retard · ⚪ Attendu ·
🔴 En retard.

### 6.7 Statuts des autres documents

| Table | Valeurs (CHECK) | Défaut | Sens |
|---|---|---|---|
| `reception.statut` | `brouillon`, `validee`, `annulee` | brouillon | validée = entrées écrites ; annulée = entrées contre-passées |
| `reception_ligne.qualite` | `conforme`, `reserve`, `refuse` | conforme | Conforme ; « Sous réserve » → magasin de quarantaine ; Refusé → n'entre pas en stock (moteur : Conforme / Réserve / Refusé, `depot.py:31`) |
| `bon_sortie.statut` | `brouillon`, `valide`, `annule` | brouillon | (masculin) |
| `operation.statut` | `brouillon`, `validee`, `annulee` | brouillon | |
| `operation.type` | `ouverture`, `retour_machine`, `transfert`, `ajustement`, `retour_fournisseur` | — | `modeles.py:764-770` ; « libération » = transfert avec motif |
| `inventaire.statut` | `ouvert`, `valide` | ouvert | ouvert = mouvements suspendus sur son magasin ; abandon = suppression |
| `dossier.statut` | `ouvert`, `clos` | ouvert | clos = coût figé (moteur « Ouvert » / « Clos ») |
| `reclamation.statut` | `ouverte`, `close` | ouverte | |
| `signalement.urgence` | `normale`, `urgente` (contrôle API seulement, `api/suivi.py:182`) | normale | |
| `signalement` « traité » | `traite_le IS NOT NULL` | — | |
| `facture` « payée » | `payee_le IS NOT NULL` | — | sort de l'échéancier |
| `dossier_charge` « réglé » | `payee_le IS NOT NULL` | — | sort de l'échéancier |

Opérations — qui a le droit (`api/operations.py:28-34`) : ouverture, ajustement, retour
fournisseur = achats ; retour machine = alimentation ; transfert = achats et alimentation (mais
**libérer une quarantaine** = achats ou direction, `api/operations.py:302-308,402-407`). Direction : tout.

### 6.8 Réclamations (`api/suivi.py:43-46`)

- Motifs : Qualité (défaut du fil) · Quantité manquante · Poids des bobines · Bobines endommagées ·
  Retard de livraison · Documents (facture, BL, certificat) · Autre (pas de CHECK ; 80 caractères).
- Issues (contrôlées par l'API) : Avoir · Remplacement · Remise sur la prochaine commande · Refusée ·
  Abandonnée. Clore exige une issue.

### 6.9 Pièces jointes (`api/suivi.py:228-233`)

`piece_jointe.objet` ∈ `dossier`, `reception`, `commande`, `reclamation`, `inventaire`,
`fournisseur`, `article` (contrôle API ; aucun CHECK). Types MIME permis : `application/pdf`,
`image/(jpeg|png|gif|webp|heic|heif|tiff|bmp)`, `text/plain`, `text/csv`, `application/vnd.*`,
`application/msword`, `application/zip` (pas de SVG). Taille ≤ 20 Mo. Fichier rangé dans
`PIECES/<objet>/<objet_id>/<uuid4 hex><extension>`.

### 6.10 Autres valeurs codées

| Notion | Valeurs | Où |
|---|---|---|
| `article.unite` | `kg` (seule permise) | CHECK |
| `article.unite_prix` | `kg`, `ml` | CHECK |
| `article.unite_achat`, `commande_ligne.unite_achat` | texte libre : `kg`, `Palette`, `Fût`, `Sac`, `Bobine`… ; **jamais `ml`** (API) | `api/referentiels.py:592-597` |
| Unités de saisie d'une sortie / opération | `kg`, `Bobine`, `Palette` (converties en kg ; une bobine au poids mesuré du lot) | `api/production.py:30-60` |
| `poste_frais.cle` | `valeur`, `poids` (API : `^(valeur|poids)$`) | `api/referentiels_import.py:79` |
| `reception_ligne.lot_numero` spécial | `LOT INTERNE` → numéro `LOT-AAAA-NNNN` donné à la validation | `api/receptions.py:47,536-537` |
| `compteur.serie` | `BC`, `REC`, `OF`, `OUV`, `RET`, `TRF`, `AJU`, `RFO`, `INV`, `RCL`, `LOT`, `DOS` | § 7.1.7 |
| Classes ABC / XYZ (calculées, non stockées) | A, B, C ; X, Y, Z | réglages `seuil_abc_*`, `seuil_xyz_*` |
| Clés de `parametre_historique` | les 55 clés de réglage + `cours_<CODE>` (historique des cours) | `api/comptes.py:328,442` |

### 6.11 Actions et objets du journal (`journal.action`, `journal.objet`)

| objet | actions |
|---|---|
| `utilisateur` | installation, connexion, changement de code, création de compte, modification de compte |
| `parametre` | paramètre |
| `devise` | cours de change |
| `sauvegarde` | sauvegarde, restauration |
| `composition`, `type_fil`, `titrage`, `couleur` | ajout / modification / suppression *libellé* (« ajout composition »…) |
| `role` | ajout / modification / suppression rôle de nomenclature |
| `fournisseur` | création / modification / suppression fournisseur |
| `article` | création / modification / suppression matière, import des matières, classement du catalogue |
| `code_douanier` | création / modification / suppression code douanier |
| `poste_frais` | création / modification / suppression poste de frais |
| `qualite` | création / modification / suppression qualité, recette, **plan de production** |
| `magasin` | création / modification magasin |
| `metier` | création / suppression métier, réglage métier, **montage** |
| `commande` | création commande, modification commande, envoi commande, **commande à approuver**, approbation commande, **renvoi aux achats**, version partie rétablie, approbation plus nécessaire, retour en brouillon, prix confirmés, expédition, **commande soldée**, commande annulée, commande rouverte, suppression commande |
| `reception` | création / modification / suppression réception, validation réception, **annulation réception**, facture complétée, facture détachée |
| `bon` | bon de sortie (brouillon), modification / validation / annulation / suppression bon de sortie |
| `operation` | « <type> (brouillon) », modification / suppression opération, « validation — <type> », annulation opération |
| `inventaire` | ouverture inventaire, comptage, validation inventaire, abandon inventaire |
| `dossier` | ouverture / modification / clôture / réouverture / suppression dossier, marchandises dossier, marchandise saisie à la main, marchandise retirée, commentaire marchandise, réception détachée, cours, frais, frais modifié, frais retiré, frais figés |
| `reclamation` | réclamation ouverte, réclamation |
| `signalement` | besoin signalé, besoin traité |
| objet de la pièce | pièce jointe, pièce retirée |
| `facture` / `frais` | règlement, règlement annulé |
| (vide) | activité vidée (`outils/vider_activite.py`) |

Les actions en **gras** sont relues comme données (§ 9).

---

## 7. Les tables, une par une

Colonnes des tableaux : **Colonne** · **Type** · **Null** (O = nullable) · **Défaut Py** ·
**Défaut SQL** · **Contraintes** · **Sens métier** · **Réf.** (ligne de `modeles.py`).

### 7.1 Socle

#### 7.1.1 `utilisateur` — classe `Utilisateur` (`modeles.py:73-85`)

Les comptes. Pas de suppression : un compte se désactive (ses sessions sont alors supprimées,
`api/comptes.py:206-207`) ; un utilisateur ne peut retirer ses propres droits de direction.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | séquence | `nextval` | PK | | 77 |
| identifiant | VARCHAR(40) | | — | — | UQ `utilisateur_identifiant_key` | identifiant de connexion, **en minuscules** (`.strip().lower()`) | 78 |
| nom | VARCHAR(80) | | `''` | `''` | | nom affiché ; **c'est lui qu'on recopie** dans tous les `*_par`, `auteur`, `journal.utilisateur` | 79 |
| role | VARCHAR(20) | | — | — | CK `utilisateur_role_check` : `role IN ('direction','achats','alimentation')` | § 6.1 | 80 |
| email | VARCHAR(120) | | `''` | `''` | | | 81 |
| empreinte | VARCHAR(200) | | `''` | `''` | | `scrypt$<sel 16 o hex>$<hash 32 o hex>`, scrypt n=2¹⁴ r=8 p=1 (`securite.py:35-44`) | 82 |
| actif | BOOLEAN | | true | true | | inactif = ne se connecte plus, absent de la liste « visages » | 83 |
| cree_le | TIMESTAMP | | `maintenant()` | — | | création | 84 |
| vu_le | TIMESTAMP | O | — | — | | dernière connexion (`securite.py:72`) | 85 |

#### 7.1.2 `session_ouverte` — classe `SessionOuverte` (`modeles.py:88-95`)

Une session de connexion. Le navigateur garde le jeton (`secrets.token_urlsafe(32)`) dans le
cookie `gestion_mp_session` (httponly, SameSite=Lax, `secure` si HTTPS, durée `SESSION_JOURS`) ; la
base n'en garde que l'empreinte.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| empreinte | VARCHAR(64) | | — | — | PK | SHA-256 hex du jeton (`securite.py:56-57`) | 91 |
| utilisateur_id | INTEGER | | — | — | FK → `utilisateur.id` **ODC** | | 92-94 |
| expire_le | TIMESTAMP | | — | — | | `maintenant() + SESSION_JOURS` ; une session expirée vaut 401 (jamais purgée) | 95 |

#### 7.1.3 `tentative` — classe `Tentative` (`modeles.py:98-105`)

Les échecs de connexion par identifiant saisi (même inexistant).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| identifiant | VARCHAR(40) | | — | — | PK | identifiant saisi (minuscules) | 103 |
| echecs | INTEGER | | 0 | — | | compté par un seul `INSERT … ON CONFLICT DO UPDATE SET echecs = echecs + 1 RETURNING` (`securite.py:144-150`) | 104 |
| bloque_jusqua | TIMESTAMP | O | — | — | | à partir de 5 échecs : `maintenant() + min(900 s, 30 s × 2^(échecs−5))` (`securite.py:151-153`) ; une connexion réussie supprime la ligne | 105 |

#### 7.1.4 `journal` — classe `Journal` (`modeles.py:108-120`)

Le journal d'audit : qui a fait quoi, quand, sur quoi. Jamais modifié ni purgé. **Sert aussi de
source de données** (§ 9). Écrit par `securite.journal()` (`securite.py:160-177`), par la
restauration (`services/sauvegarde.py:194`) et par `outils/vider_activite.py`.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | ordre d'écriture | 113 |
| quand | TIMESTAMP | | `maintenant()` | — | IX `ix_journal_quand` | | 114 |
| utilisateur | VARCHAR(80) | | `''` | `''` | | **nom** de l'utilisateur, « système » si aucun | 115 |
| role | VARCHAR(20) | | `''` | `''` | | rôle au moment du geste | 116 |
| action | VARCHAR(80) | | `''` | `''` | | § 6.11 | 117 |
| objet | VARCHAR(40) | | `''` | `''` | | § 6.11 | 118 |
| objet_id | INTEGER | O | — | — | aucune FK (polymorphe) | id de l'objet dans la table désignée par `objet` | 119 |
| detail | TEXT | | `''` | — | | texte libre, tronqué à 2 000 caractères ; contient parfois du JSON (§ 9) | 120 |

#### 7.1.5 `parametre` — classe `Parametre` (`modeles.py:123-129`)

Les réglages, un par clé, valeur **texte** (`parametres.py`). Un nombre s'écrit `str(int)` s'il est
entier, sinon `repr(float)` (`api/comptes.py:303-312`) ; un taux est rangé en fraction et affiché
× `echelle`.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| cle | VARCHAR(60) | | — | — | PK | clé du réglage | 126 |
| valeur | TEXT | | `''` | — | | valeur en texte | 127 |
| modifie_le | TIMESTAMP | | `maintenant()` | — | | dernier changement (entre dans la signature du cache du moteur, `depot.py:678`) | 128 |
| modifie_par | VARCHAR(80) | | `''` | `''` | | nom, « installation », « reprise ERP Fil », « système » | 129 |

Les 55 réglages (`parametres.py:39-144`) — famille, défaut, bornes [bas ; haut], unité,
échelle d'affichage :

| Clé | Libellé | Famille | Défaut | Bornes | Unité (×échelle) |
|---|---|---|---|---|---|
| seuil_critique | Couverture critique | Couverture et statuts | 60 | 1–3650 | jours |
| seuil_alerte | Couverture d'attention | Couverture et statuts | 90 | 1–3650 | jours |
| seuil_dormant | Stock dormant | Couverture et statuts | 180 | 1–3650 | jours |
| delai_defaut | Délai par défaut | Approvisionnement | 60 | 1–730 | jours |
| marge_jours | Couverture de commande | Approvisionnement | 30 | 0–730 | jours |
| marge_securite | Marge de sécurité | Approvisionnement | 0.2 | 0–5 | % (×100) |
| taux_perte | Taux de perte matière | Approvisionnement | 0.02 | 0–0.5 | % (×100) |
| securite_a | Sécurité classe A | Approvisionnement | 30 | 0–365 | jours |
| securite_b | Sécurité classe B | Approvisionnement | 30 | 0–365 | jours |
| securite_c | Sécurité classe C | Approvisionnement | 30 | 0–365 | jours |
| fenetre_realisation_jours | Prévision — fenêtre du réalisé | Approvisionnement | 90 | 0–730 | jours |
| plafond_stock_min_mois | Stock minimum — plafond | Approvisionnement | 3 | 0–60 | mois |
| croissance_annuelle | Croissance annuelle du plan | Approvisionnement | 0.0 | −0.9–10 | % (×100) |
| seuil_abc_a | Classe A — valeur cumulée | Classification ABC / XYZ | 0.8 | 0–1 | % (×100) |
| seuil_abc_b | Classe B — valeur cumulée | Classification ABC / XYZ | 0.95 | 0–1 | % (×100) |
| seuil_xyz_x | Classe X — CV maximum | Classification ABC / XYZ | 0.25 | 0–10 | — |
| seuil_xyz_y | Classe Y — CV maximum | Classification ABC / XYZ | 0.5 | 0–10 | — |
| seuil_bc_urgent | BC urgent | Politique d'achat | 300000 | 0–1e12 | MAD |
| seuil_bc_groupe | BC groupé | Politique d'achat | 100000 | 0–1e12 | MAD |
| seuil_tier1 | Tier 1 (classe A) | Politique d'achat | 300000 | 0–1e12 | MAD |
| seuil_tier2 | Tier 2 | Politique d'achat | 200000 | 0–1e12 | MAD |
| seuil_tier3 | Tier 3 | Politique d'achat | 100000 | 0–1e12 | MAD |
| seuil_approbation | Approbation des commandes au-delà de | Politique d'achat | 0 (= jamais) | 0–1e12 | MAD |
| toler_in_full | Tolérance de livraison complète | Réceptions et fournisseurs | 0.02 | 0–0.2 | % (×100) |
| toler_ecart_pesee | Tolérance d'écart de pesée | Réceptions et fournisseurs | 0.02 | 0–1 | % (×100) |
| toler_excedent | Excédent de livraison toléré | Réceptions et fournisseurs | 0.1 | 0–10 | % (×100) |
| toler_poids_bobine | Tolérance du poids de bobine | Réceptions et fournisseurs | 0.05 | 0–1 | % (×100) |
| tolerance_inventaire | Tolérance d'écart d'inventaire | Stock et inventaire | 0.02 | 0–1 | % (×100) |
| toler_retard_jours | Retard toléré dans la ponctualité | Réceptions et fournisseurs | 0 | 0–60 | jours |
| cible_otif | Cible OTIF | Réceptions et fournisseurs | 0.95 | 0–1 | % (×100) |
| score_strategique | Score — Stratégique | Réceptions et fournisseurs | 85 | 0–100 | /100 |
| score_standard | Score — Standard | Réceptions et fournisseurs | 65 | 0–100 | /100 |
| score_surveiller | Score — ATTENTION | Réceptions et fournisseurs | 45 | 0–100 | /100 |
| seuil_hausse_forte | Forte hausse de prix à partir de | Prix | 0.05 | 0.005–10 | % (×100) |
| fenetre_prix_jours | Écart maximal entre deux prix comparés | Prix | 90 | 1–3650 | jours |
| taux_tva_import | TVA à l'importation | Prix | 0.2 | 0–1 | % (×100) |
| taux_tpi_import | Taxe parafiscale à l'importation (TPI) | Prix | 0.0025 | 0–0.1 | % (×100) |
| seuil_surcout_import | Frais d'un dossier à vérifier au-delà de | Prix | 1.0 | 0.05–100 | % (×100) |
| toler_facture_import | Facture d'un dossier à rapprocher au-delà de | Prix | 0.02 | 0–1 | % (×100) |
| dso | Délai client moyen (DSO) | Trésorerie | 60 | 0–3650 | jours |
| nom_entreprise | Raison sociale | Société | `""` | texte | |
| forme_juridique | Forme juridique et capital | Société | `""` | texte | |
| secteur | Secteur | Société | `Fabrication de tapis mécaniques` | texte | |
| adresse | Siège social | Société | `""` | texte | |
| ville | Ville | Société | `""` | texte | |
| telephone | Téléphone | Société | `""` | texte | |
| banques | Banques (séparées par « · ») | Société | `""` | texte | |
| ice | ICE | Société | `""` | texte | |
| rc | R.C | Société | `""` | texte | |
| identifiant_fiscal | N.I.F | Société | `""` | texte | |
| cnss | C.N.S.S | Société | `""` | texte | |
| patente | Patente | Société | `""` | texte | |
| date_cloture | Période close jusqu'au | Société | `""` | ISO `AAAA-MM-JJ`, strictement passée | |
| courriel_destinataires | Courriel du lundi : à qui | Société | `""` | adresses séparées par des virgules | |
| adresse_publique | Adresse du serveur pour les téléphones | Société | `""` | `http(s)://…`, ≤ 200, sans espace | |

Règles d'écriture (`api/comptes.py:292-344`) : clé inconnue refusée ; nombre hors bornes refusé ;
texte ≤ 500 ; ordre imposé `seuil_critique < seuil_alerte`, `seuil_abc_a < seuil_abc_b`,
`seuil_xyz_x < seuil_xyz_y`, `score_surveiller < score_standard < score_strategique` ; chaque
changement → `parametre_historique` + journal. **Clé cachée** (pas dans `REGLAGES`) :
`courriel_dernier_envoi` (date ISO du dernier courriel du lundi envoyé, `services/courriel.py:77-97`).
Pour le moteur, `pour_le_moteur()` (`parametres.py:172-189`) ajoute `methode = "corrigee"` et les
cours des devises.

#### 7.1.6 `parametre_historique` — classe `ParametreHistorique` (`modeles.py:132-139`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 135 |
| cle | VARCHAR(60) | | — | — | IX `ix_parametre_historique_cle` ; pas de FK | clé de réglage **ou** `cours_<CODE>` (historique des cours de devise) | 136 |
| valeur | TEXT | | — | — | | nouvelle valeur (l'ancienne = la ligne précédente de la même clé, sinon le défaut) | 137 |
| quand | TIMESTAMP | | `maintenant()` | — | | | 138 |
| par | VARCHAR(80) | | `''` | `''` | | nom | 139 |

#### 7.1.7 `compteur` — classe `Compteur` (`modeles.py:142-151`)

Une suite de numéros par série et par **année de la pièce** (pas l'année de saisie).
`securite.numero()` (`securite.py:178-196`) : lit la ligne `FOR UPDATE`, la crée si absente
(`ON CONFLICT DO NOTHING`), incrémente `dernier`.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 148 |
| serie | VARCHAR(10) | | — | — | UQ `compteur_serie_annee_key` (serie, annee) | série | 149 |
| annee | INTEGER | | — | — | (idem) | année de la date de la pièce | 150 |
| dernier | INTEGER | | 0 | — | | dernier numéro donné | 151 |

| Série | Format | Donné quand | Table.colonne |
|---|---|---|---|
| BC | `BC-AAAA-NNNN` | à l'envoi (ou à l'approbation) | commande.numero |
| REC | `REC-AAAA-NNNN` | à la validation | reception.numero |
| OF | `OF-AAAA-NNNN` | à la validation (verrou 7426110, dates croissantes) | bon_sortie.numero |
| OUV, RET, TRF, AJU, RFO | `OUV-AAAA-NNNN`… | à la validation (`api/operations.py:25-26`) | operation.numero |
| INV | `INV-AAAA-NNNN` | **à l'ouverture** | inventaire.numero |
| RCL | `RCL-AAAA-NNNN` | à l'ouverture | reclamation.numero |
| LOT | `LOT-AAAA-NNNN` | à la validation d'une réception « LOT INTERNE », ou sur demande (`POST /lots/numero-interne`) | lot.numero |
| DOS | **`NN/AA`** (`{dernier:02d}/{année%100:02d}`) | à la création du dossier (année = date d'arrivée) ; un numéro déjà pris (saisi à la main) est sauté | dossier.numero |

### 7.2 Référentiels

#### 7.2.1 `devise` — classe `Devise` (`modeles.py:159-166`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(3) | | — | — | PK | ISO (MAD, USD, EUR…) saisi en majuscules | 163 |
| nom | VARCHAR(40) | | `''` | `''` | | | 164 |
| taux | FLOAT | | — | — | CK `devise_taux_check` : `taux > 0` | **cours du jour** : MAD pour 1 unité ; MAD = 1 ; chaque saisie historisée en `parametre_historique` `cours_<CODE>` | 165 |
| actif | BOOLEAN | | true | true | | | 166 |

#### 7.2.2 `composition` — classe `Composition` (`modeles.py:169-179`)

La matière du fil (polypropylène, polyester, jute…). Ex-« natures » de l'ERP Fil.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(32) | | — | — | PK ; cible de `article.composition` (OUC) | | 174 |
| libelle | VARCHAR(120) | | `''` | `''` | | lu par le moteur comme « nature » | 175 |
| famille | VARCHAR(64) | | `''` | `''` | | | 176 |
| actif | BOOLEAN | | true | true | | | 177 |
| composition_detaillee | VARCHAR(160) | | `''` | `''` | | « 100 % polypropylène » | 178 |
| commentaire | TEXT | | `''` | `''` | | | 179 |

#### 7.2.3 `type_fil` — classe `TypeFil` (`modeles.py:182-190`)

La façon dont le fil est travaillé (frisé, shrink, filament continu…).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(32) | | — | — | PK ; cible OUC | | 187 |
| libelle | VARCHAR(120) | | `''` | `''` | | | 188 |
| actif | BOOLEAN | | true | true | | | 189 |
| commentaire | TEXT | | `''` | `''` | | | 190 |

#### 7.2.4 `titrage` — classe `Titrage` (`modeles.py:193-202`)

La grosseur du fil (2900 Dtex, 1500 Deniers, 20/2 Nm). Un code saisi sans valeur se décompose en
« valeur unité » (`api/referentiels.py:205-206`).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(48) | | — | — | PK ; cible OUC | « 2900 Dtex » | 198 |
| valeur | VARCHAR(32) | | `''` | `''` | | « 2900 » | 199 |
| unite | VARCHAR(16) | | `''` | `''` | | « Dtex », « Deniers », « Nm » | 200 |
| actif | BOOLEAN | | true | true | | | 201 |
| commentaire | TEXT | | `''` | `''` | | | 202 |

#### 7.2.5 `couleur` — classe `Couleur` (`modeles.py:205-212`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(64) | | — | — | PK ; cible OUC | | 208 |
| libelle | VARCHAR(120) | | `''` | `''` | | | 209 |
| famille | VARCHAR(64) | | `''` | `''` | | famille de couleur (opportunités « même couleur ») | 210 |
| actif | BOOLEAN | | true | true | | | 211 |
| commentaire | TEXT | | `''` | `''` | | | 212 |

Une valeur de classification portée par un article ne se supprime pas (on la désactive) ;
renommer son code fait suivre les articles (OUC) (`api/referentiels.py:214-253`).

#### 7.2.6 `role_nomenclature` — classe `RoleNomenclature` (`modeles.py:215-222`)

Le rôle d'une matière dans le tapis (poil, chaîne, trame, colle, cuir, franges, ruban, plastique).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(32) | | — | — | PK ; cible de `article.role`, `qualite_poids.role` (sans OUC) | | 220 |
| lineaire | BOOLEAN | | false | — | | vrai : le poids au m² de la qualité est en **ml/m²** (× densité = kg/m²) ; vrai ⇔ Cuir, Franges, Ruban | 221 |
| ordre | INTEGER | | 0 | — | | ordre d'affichage | 222 |

#### 7.2.7 `fournisseur` — classe `Fournisseur` (`modeles.py:225-250`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 233 |
| nom | VARCHAR(160) | | — | — | UQ `fournisseur_nom_key` | raison sociale (clé lisible pour le moteur) | 234 |
| code | VARCHAR(32) | | `''` | `''` | | code court | 235 |
| pays | VARCHAR(80) | | `''` | `''` | | « Maroc » = fournisseur local : pas de dossier d'importation sans confirmation (`api/importations.py:109`) | 236 |
| contact | VARCHAR(120) | | `''` | `''` | | | 237 |
| telephone | VARCHAR(60) | | `''` | `''` | | | 238 |
| email | VARCHAR(160) | | `''` | `''` | | | 239 |
| devise | VARCHAR(3) | | `'MAD'` | — | FK → `devise.code` | devise habituelle (proposée sur bon et facture) | 240 |
| delai_jours | FLOAT | | 60 | `'60'` | CK `fournisseur_delai_jours_check` : `> 0` | délai de livraison (jours) : date promise = envoi + délai | 241 |
| couverture_commande_jours | FLOAT | | 0 | `'0'` | CK `…_couverture_commande_jours_check` : `>= 0` | pas de commande : jours de besoin qu'une commande couvre (0 = réglage `marge_jours`) | 242 |
| mode_paiement | VARCHAR(40) | | `''` | `''` | | | 243 |
| delai_paiement_jours | FLOAT | | 0 | `'0'` | CK `…_delai_paiement_jours_check` : `>= 0` | échéance d'une facture = date + délai | 244 |
| conditions_paiement | VARCHAR(160) | | `''` | `''` | | | 245 |
| incoterm | VARCHAR(20) | | `''` | `''` | | imprimé sur le bon | 246 |
| notes | TEXT | | `''` | — | | | 247 |
| port_chargement | VARCHAR(80) | | `''` | `''` | | | 248 |
| banque | VARCHAR(120) | | `''` | `''` | | domiciliation du paiement | 249 |
| actif | BOOLEAN | | true | true | | | 250 |

#### 7.2.8 `code_douanier` — classe `CodeDouanier` (`modeles.py:253-263`)

Position du tarif douanier et son taux de droits (exigence M53) : droits attendus d'un dossier.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(20) | | — | — | PK ; cible OUC de `article.code_douanier` | « 5402.47.00.00 » | 260 |
| libelle | VARCHAR(160) | | `''` | `''` | | | 261 |
| taux_droits | FLOAT | | 0 | `'0'` (base migrée : `0`) | CK `code_douanier_taux_droits_check` : `taux_droits >= 0 AND taux_droits <= 1` | fraction (0,10 = 10 %) | 262 |
| actif | BOOLEAN | | true | true | | | 263 |

#### 7.2.9 `article` — classe `Article` (`modeles.py:266-327`)

Une matière (fil ou intrant). La **référence** est son nom lisible et sa clé pour le moteur.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 281 |
| reference | VARCHAR(160) | | — | — | UQ `article_reference_key` | nom lisible, unique ; **clé des JSON historiques** (§ 8) | 282 |
| designation | VARCHAR(160) | | `''` | `''` | | | 283 |
| role | VARCHAR(32) | | — | — | FK → `role_nomenclature.code` | rôle dans le tapis | 284 |
| composition | VARCHAR(32) | O | — | — | FK → `composition.code` OUC | | 285-287 |
| type_fil | VARCHAR(32) | O | — | — | FK → `type_fil.code` OUC | | 288 |
| titrage | VARCHAR(48) | O | — | — | FK → `titrage.code` OUC | | 289 |
| couleur | VARCHAR(64) | O | — | — | FK → `couleur.code` OUC | | 290 |
| couleur_code | VARCHAR(32) | | `''` | `''` | | code couleur du fournisseur | 291 |
| unite | VARCHAR(4) | | `'kg'` | `'kg'` | CK `ck_article_unite_kg` : `unite = 'kg'` | unité du stock : **toujours le kilo** | 292 |
| unite_prix | VARCHAR(4) | | `'kg'` | `'kg'` | CK `ck_article_unite_prix` : `unite_prix IN ('kg','ml')` | unité du **prix saisi** | 293 |
| densite | FLOAT | | 0 | `'0'` | CK `ck_article_prix_au_metre` : `unite_prix = 'kg' OR densite > 0` | kg par mètre linéaire ; obligatoire (API) pour un rôle linéaire | 294 |
| fournisseur_id | INTEGER | O | — | — | FK → `fournisseur.id` | fournisseur unique ; obligatoire (API) pour une matière active (contrôle C05) | 295 |
| prix | FLOAT | | 0 | `'0'` | CK `article_prix_check` : `prix >= 0` | prix du catalogue dans `devise`, par `unite_prix` ; mis à jour par une confirmation de prix | 296 |
| devise | VARCHAR(3) | | `'MAD'` | — | FK → `devise.code` | devise du prix | 297 |
| unite_achat | VARCHAR(32) | | `'kg'` | `'kg'` | | unité de commande (kg, Palette, Fût, Sac…), jamais `ml` | 298 |
| contenance_achat | FLOAT | | 1 | `'1'` | CK `article_check1` : `contenance_achat >= 0 AND minimum_commande >= 0` | kg par unité d'achat (1 si kg) | 299 |
| minimum_commande | FLOAT | | 0 | `'0'` | (idem) | kg | 300 |
| poids_bobine | FLOAT | | 0 | `'0'` | CK `article_check` : `stock_min >= 0 AND poids_bobine >= 0 AND bobines_palette >= 0` | kg par bobine (catalogue) | 301 |
| bobines_palette | FLOAT | | 0 | `'0'` | (idem) | bobines par palette | 302 |
| stock_min | FLOAT | | 0 | `'0'` | (idem) | kg ; plafonné par `plafond_stock_min_mois` | 303 |
| couv_min_mois | FLOAT | | 0 | `'0'` | | couverture minimum (mois) | 304 |
| groupe_equiv | VARCHAR(64) | | `''` | `''` | | groupe de fils interchangeables | 305 |
| priorite_equiv | FLOAT | O | — | — | | rang dans le groupe (0–100, API) | 306 |
| actif | BOOLEAN | | true | true | | | 307 |
| version | INTEGER | | 1 | — | | **verrou optimiste** (+1 à chaque modification) | 308 |
| modifie_le | TIMESTAMP | O | — | — | | | 309 |
| modifie_par | VARCHAR(80) | | `''` | `''` | | | 310 |
| code_douanier | VARCHAR(20) | O | — | — | FK → `code_douanier.code` OUC | | 311 |

Relations : `fournisseur` (`lazy="joined"`, `:313`). Propriétés calculées : `prix_kg` (`:315-321`),
`kg_par_ml` (`:323-327`, densité si rôle linéaire, sinon 0).

#### 7.2.10 `qualite` — classe `Qualite` (`modeles.py:330-346`)

Une qualité de tapis : poids de chaque rôle au m², plan de production.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 335 |
| code | VARCHAR(32) | | — | — | UQ `qualite_code_key` | « 8S »… (clé pour le moteur) | 336 |
| nom | VARCHAR(120) | | `''` | `''` | | | 337 |
| base_mensuelle | FLOAT | | 0 | `'0'` | | m² par mois **avant** saisonnalité (plan) | 338 |
| actif | BOOLEAN | | true | true | | « en service » ; arrêtée = ne se tisse plus (refus de valider un ordre, `api/production.py:503-507`) | 339 |

Relations : `poids` → `QualitePoids` (`cascade="all, delete-orphan"`, `selectin`, `:341-343`) ;
`saisons` → `QualiteSaison` (idem, `order_by mois`, `:344-346`).

#### 7.2.11 `qualite_poids` — classe `QualitePoids` (`modeles.py:349-356`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 353 |
| qualite_id | INTEGER | | — | — | FK → `qualite.id` ODC ; UQ `qualite_poids_qualite_id_role_key` (qualite_id, role) | | 354 |
| role | VARCHAR(32) | | — | — | FK → `role_nomenclature.code` | | 355 |
| poids | FLOAT | | 0 | `'0'` | CK `qualite_poids_poids_check` : `>= 0` | **kg/m²**, ou **ml/m²** pour un rôle linéaire | 356 |

#### 7.2.12 `qualite_saison` — classe `QualiteSaison` (`modeles.py:359-370`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 367 |
| qualite_id | INTEGER | | — | — | FK → `qualite.id` ODC ; UQ `qualite_saison_qualite_id_mois_key` | | 368 |
| mois | INTEGER | | — | — | CK `qualite_saison_mois_check` : `mois BETWEEN 1 AND 12` | mois civil | 369 |
| coefficient | FLOAT | | 1 | `'1'` | CK `qualite_saison_coefficient_check` : `>= 0` | multiplicateur de la base (≤ 20, API `production_plan.py:38`) ; mois absent = 1 | 370 |

#### 7.2.13 `recette` — classe `Recette` (`modeles.py:373-385`)

Une ligne de nomenclature : la part d'un article dans **son** rôle pour une qualité (le rôle vient
de `article.role`, il n'est pas stocké ici).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 382 |
| qualite_id | INTEGER | | — | — | FK → `qualite.id` ODC ; UQ `recette_qualite_id_article_id_key` (qualite_id, article_id) | | 383 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 384 |
| pourcentage | FLOAT | | 0 | `'0'` | CK `recette_pourcentage_check` : `>= 0 AND <= 100` | part (%) de l'article dans le rôle ; la somme par (qualité, rôle) doit faire 100 (contrôle C01, non garanti en base) | 385 |

Kilos d'un article par m² = `poids du rôle (kg/m², ou ml/m² × densité) × pourcentage / 100`
(× (1 + `taux_perte`) pour les besoins). Toute écriture sur `recette` ou `qualite_poids` crée une
`recette_version` au commit (§ 7.10.4).

#### 7.2.14 `magasin` — classe `Magasin` (`modeles.py:388-397`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 392 |
| code | VARCHAR(64) | | — | — | UQ `magasin_code_key` | nom court (clé pour le moteur) | 393 |
| nom | VARCHAR(120) | | `''` | `''` | | | 394 |
| type | VARCHAR(20) | | `'Stock courant'` | `'Stock courant'` | CK `magasin_type_check` : `type IN ('Stock courant','Quarantaine')` | § 6.2 ; ne change pas s'il détient du stock (API) | 395 |
| actif | BOOLEAN | | true | true | | désactivé = ne reçoit plus rien ; ne se désactive pas s'il détient du stock | 396 |
| contenu | VARCHAR(120) | | `''` | `''` | | ce qu'on y range (« Tout », « Fils PP »…) | 397 |

#### 7.2.15 `metier` — classe `Metier` (`modeles.py:400-420`)

Un métier à tisser. Le **fil monté** (non encore tissé) compte dans le stock global et sa valeur
(décision de Mohamed, commits 169dfdc, f33a428), à part du stock en magasin.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 409 |
| code | VARCHAR(32) | | — | — | UQ `metier_code_key` | « CRM 1 » | 410 |
| nom | VARCHAR(120) | | `''` | `''` | | | 411 |
| laize | FLOAT | | 4.2 | `'4.2'` | CK `metier_check` : `laize >= 0 AND densite >= 0` | largeur d'un étage (m) | 412 |
| densite | FLOAT | | 0 | `'0'` | (idem) | **bobines par mètre de laize** | 413 |
| etages | INTEGER | | 6 | — | CK `metier_etages_check` : `etages BETWEEN 1 AND 40` | nombre d'étages | 414 |
| actif | BOOLEAN | | true | true | | | 415 |
| commentaire | TEXT | | `''` | `''` | | | 416 |

Relation : `fils` → `FilMonte` (`all, delete-orphan`, `selectin`, `order_by etage`, `:418-420`).

#### 7.2.16 `fil_monte` — classe `FilMonte` (`modeles.py:423-436`)

Un fil monté sur un étage d'un métier.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 430 |
| metier_id | INTEGER | | — | — | FK → `metier.id` ODC ; UQ `fil_monte_metier_id_etage_article_id_key` (metier_id, etage, article_id) | | 431 |
| etage | INTEGER | | 1 | — | (pas de CK ; 1–40 par l'API ; ≤ `metier.etages` : contrôle C24) | | 432 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 433 |
| metres | FLOAT | | 0 | `'0'` | CK `fil_monte_check` : `metres >= 0 AND pourcentage BETWEEN 0 AND 100` | mètres de laize occupés | 434 |
| pourcentage | FLOAT | | 100 | `'100'` | (idem) | remplissage des bobines (à quel point elles sont pleines) | 435 |
| commentaire | VARCHAR(300) | | `''` | `''` | | | 436 |

Bobines d'un fil = `metres × metier.densite × pourcentage / 100` ; poids = bobines × poids d'une
bobine (celui du lot sorti le plus récemment, sinon du dernier lot reçu, sinon du catalogue —
`depot.py:131-149`, `api/referentiels.py:1161-1167`).

#### 7.2.17 `poste_frais` — classe `PosteFrais` (`modeles.py:439-450`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| code | VARCHAR(16) | | — | — | PK ; cible de `dossier_charge.poste` | § 5.2 | 444 |
| libelle | VARCHAR(80) | | `''` | `''` | | | 445 |
| recuperable | BOOLEAN | | false | — | | vrai (TVA) : pèse sur la trésorerie, **jamais** sur le coût de revient | 446 |
| ordre | INTEGER | | 0 | — | | ordre d'affichage (0–999) | 447 |
| cle | VARCHAR(8) | | `'valeur'` | `'valeur'` | (pas de CK) | répartition d'un frais global : `valeur` (au prorata de la valeur MAD) ou `poids` (au prorata des kilos) | 450 |

### 7.3 Lots, soldes, journal des mouvements

#### 7.3.1 `lot` — classe `Lot` (`modeles.py:458-472`)

Un lot : le numéro du fournisseur (ou le nôtre, `LOT-AAAA-NNNN`). Créé par `stock.lot_ou_creer`
(`services/stock.py:35-60`, `INSERT … ON CONFLICT (article_id, numero) DO NOTHING`) à la première
entrée (réception, ouverture, ajustement « matière retrouvée », lot trouvé à l'inventaire).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 464 |
| article_id | INTEGER | | — | — | FK → `article.id` ; IX `ix_lot_article_id` ; UQ `lot_article_id_numero_key` (article_id, numero) | | 465 |
| numero | VARCHAR(80) | | — | — | (idem) ; jamais vide (API) | numéro du lot (espaces retirés) | 466 |
| fournisseur_id | INTEGER | O | — | — | FK → `fournisseur.id` | premier fournisseur connu (posé s'il manquait) | 467 |
| entre_le | DATE | | — | — | | date de la première entrée ; ordre FIFO des sorties (`services/stock.py:285`) | 468 |
| poids_bobine | FLOAT | | 0 | `'0'` | | kg/bobine **mesuré** = pesée ÷ nb de bobines à la réception ; écrasé par une réception suivante du même lot | 469 |
| commentaire | VARCHAR(300) | | `''` | `''` | | jamais écrit ni lu par l'API | 470 |

Relation : `article` (`joined`, `:472`).

#### 7.3.2 `solde` — classe `Solde` (`modeles.py:475-483`)

Ce qu'un lot détient dans un magasin : **le cache** du journal, tenu dans la même transaction que
chaque mouvement, sous verrou de ligne. Une ligne à 0 reste (jamais supprimée).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| lot_id | INTEGER | | — | — | PK (lot_id, magasin_id) ; FK → `lot.id` | | 481 |
| magasin_id | INTEGER | | — | — | PK ; FK → `magasin.id` | | 482 |
| quantite | FLOAT | | 0 | `'0'` | CK **`ck_solde_positif`** : `quantite >= -0.0005` | kg ; arrondi à 6 décimales, mis à 0 sous le gramme | 483 |

#### 7.3.3 `mouvement` — classe `Mouvement` (`modeles.py:497-535`)

**L'unique écriture de stock.** Une ligne = un lot, un magasin, une quantité signée. Jamais
modifiée ni supprimée : une erreur se corrige par **contre-passation**. Un transfert = deux lignes
liées par `paire`. Écrit **uniquement** par `services/stock.ecrire` (`services/stock.py:122-212`).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 511 |
| date_effet | DATE | | — | — | IX `ix_mouvement_date_effet` ; IX `ix_mouvement_article_date` (article_id, date_effet) | date du fait (jamais future, ≥ 2000, hors période close) ; une contre-passation prend celle de l'original | 512 |
| date_saisie | TIMESTAMP | | `maintenant()` | — | | instant d'écriture | 513 |
| type | VARCHAR(20) | | — | — | CK `mouvement_type_check` : `type IN ('OUVERTURE','RECEPTION','SORTIE','RETOUR_MACHINE','RETOUR_FOURNISSEUR','AJUSTEMENT','TRANSFERT')` | § 6.3 | 514 |
| article_id | INTEGER | | — | — | FK → `article.id` | **copie** de `lot.article_id` | 515 |
| lot_id | INTEGER | | — | — | FK → `lot.id` ; IX `ix_mouvement_lot_id` | | 516 |
| magasin_id | INTEGER | | — | — | FK → `magasin.id` | | 517 |
| quantite | FLOAT | | — | — | CK `mouvement_quantite_check` : `quantite <> 0` | kg **signés** (+ entrée, − sortie) | 518 |
| prix | FLOAT | | 0 | `'0'` | | prix d'achat **au kg** d'une entrée (ouverture, réception), dans `devise` ; 0 pour les autres types ; recopié par une contre-passation | 519 |
| devise | VARCHAR(3) | | `'MAD'` | `'MAD'` | pas de FK | devise de `prix` (majuscules) | 520 |
| cours | FLOAT | | 0 | `'0'` (base migrée : `0`) | | cours **figé à l'écriture** : celui de la commande s'il l'a figé dans la même devise, sinon celui du jour ; **0** = MAD, prix nul, ou cours inconnu | 524 |
| document | VARCHAR(20) | | `''` | `''` | pas de CK | § 6.4 | 525 |
| document_id | INTEGER | O | — | — | IX `ix_mouvement_document_id` ; **pas de FK** (polymorphe) | id dans la table du document | 526 |
| document_numero | VARCHAR(40) | | `''` | `''` | | numéro du document (BC/REC/OF/OUV…/INV) recopié | 527 |
| ordre_id | INTEGER | O | — | — | FK → `bon_sortie.id` | l'ordre de fabrication (SORTIE, RETOUR_MACHINE) | 528 |
| paire | INTEGER | O | — | — | pas de FK | id de la ligne **sortie** d'un transfert, sur ses deux lignes ; pour une contre-passation de transfert : id de la première ligne inverse | 529 |
| motif | VARCHAR(80) | | `''` | `''` | | § 6.5 | 530 |
| commentaire | VARCHAR(300) | | `''` | `''` | | § 6.5 | 531 |
| auteur | VARCHAR(80) | | `''` | `''` | | **nom** de l'utilisateur qui valide | 532 |
| contrepasse_id | INTEGER | O | — | — | FK → `mouvement.id` ; **UQ `mouvement_contrepasse_id_key`** | sur une contre-passation : l'id de la ligne qu'elle annule ; une ligne ne s'annule qu'une fois | 533-535 |

Le **coût** d'une écriture n'est pas stocké : le moteur le calcule (`moteur.couts_du_journal`,
`api/stock.py:60-71`) — achat au coût de revient de son dossier sinon à `prix × cours` ; annulation
au coût de ce qu'elle annule ; retour fournisseur au coût d'entrée du lot ; le reste au coût moyen
pondéré (CMUP) du moment.

### 7.4 Achats

#### 7.4.1 `commande` — classe `Commande` (`modeles.py:552-593`)

Un bon de commande fournisseur (BC). Imprimé en **anglais, sans prix**, sur papier à en-tête.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens métier | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 558 |
| numero | VARCHAR(32) | O | — | — | UQ `commande_numero_key` | `BC-AAAA-NNNN`, donné **au départ** du bon ; **« parti » ⇔ numéro non nul** (`api/achats.py:60-65`) | 561 |
| fournisseur_id | INTEGER | | — | — | FK → `fournisseur.id` | | 562 |
| date_commande | DATE | | — | — | | date de création, **remplacée par la date d'envoi** au numérotage (`api/achats.py:511-514`) | 563 |
| date_livraison_prevue | DATE | O | — | — | | **date promise** : saisie, ou envoi + `delai_jours` ; figée à la confirmation des prix ; ne se repousse plus une fois passée ; jamais avant l'envoi. Sert à la ponctualité | 564 |
| statut | VARCHAR(20) | | `'brouillon'` | `'brouillon'` | CK `commande_statut_check` (6 valeurs, § 6.6) | | 565 |
| devise | VARCHAR(3) | | — | — | FK → `devise.code` | devise du bon | 566 |
| cours | FLOAT | | 0 | `'0'` | | cours **figé à la première confirmation de prix** (`api/achats.py:832-833`) ; 0 = pas encore figé (on lit le cours du jour) | 567 |
| observations | TEXT | | `''` | — | | remarques au fournisseur (imprimées) | 568 |
| proforma_le | DATE | O | — | — | | jalon : proforma reçue | 570 |
| embarquee_le | DATE | O | — | — | | jalon : embarquement | 571 |
| eta | DATE | O | — | — | | arrivée estimée : **remplace la date promise dans la prévision** et le « en retard », pas dans la ponctualité | 572 |
| au_port_le | DATE | O | — | — | | jalon | 573 |
| dedouanee_le | DATE | O | — | — | | jalon | 574 |
| conteneur | VARCHAR(60) | | `''` | `''` | | | 575 |
| navire | VARCHAR(80) | | `''` | `''` | | | 576 |
| acompte_le | DATE | O | — | — | | jalon : acompte payé | 577 |
| arrivee_usine_le | DATE | O | — | — | | jalon : arrivée à l'usine | 578 |
| cree_par | VARCHAR(80) | | `''` | `''` | | | 579 |
| cree_le | TIMESTAMP | | `maintenant()` | — | | | 580 |
| approuvee_par | VARCHAR(80) | | `''` | `''` | | remis à `''` quand une hausse redemande l'approbation | 581 |
| approuvee_le | TIMESTAMP | O | — | — | | | 582 |
| montant_approuve | FLOAT | | 0 | `'0'` (base migrée : `0`) | | **MAD** au cours du bon : montant pour lequel le bon est parti (approuvé, ou sous le seuil à l'envoi) ; 0 = inconnu | 585 |
| version_approuvee | TEXT | | `''` | **aucun** (base migrée : `''`) | | JSON de la « version partie » (§ 8.2) ; `''` = inconnue | 588 |

Relations : `fournisseur` (`joined`) ; `lignes` → `CommandeLigne` (`all, delete-orphan`,
`selectin`, `order_by id`) (`:590-593`). Jalons dans l'ordre : `proforma_le, acompte_le,
embarquee_le, eta, au_port_le, dedouanee_le, arrivee_usine_le` (`api/achats.py:105-106`).

#### 7.4.2 `commande_ligne` — classe `CommandeLigne` (`modeles.py:596-614`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 603 |
| commande_id | INTEGER | | — | — | FK → `commande.id` ODC ; UQ `commande_ligne_commande_id_article_id_key` (commande_id, article_id) | une matière par bon | 604 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 605 |
| quantite | FLOAT | | — | — | CK `commande_ligne_check` : `quantite > 0 AND contenance > 0 AND prix >= 0` | **kg** commandés | 606 |
| unite_achat | VARCHAR(32) | | `'kg'` | `'kg'` | | unité d'achat de la ligne | 607 |
| contenance | FLOAT | | 1 | `'1'` | (idem) | kg par unité d'achat | 608 |
| prix | FLOAT | | 0 | `'0'` | (idem) | prix **au kg** dans la devise du bon ; tant qu'il n'est pas confirmé, l'estimation lit le catalogue converti | 609 |
| prix_confirme | BOOLEAN | | false | — | | confirmé par le fournisseur | 610 |
| confirme_le | TIMESTAMP | O | — | — | | | 611 |
| confirme_par | VARCHAR(80) | | `''` | `''` | | | 612 |

Relation : `article` (`joined`). **Reçu d'une ligne** (calculé, `depot.recu_par_ligne`
`depot.py:97-108`) = Σ pesées des lignes de réception **validées** non refusées qui la visent, **moins**
les retours au fournisseur de leurs lots (au prorata des pesées du lot).

#### 7.4.3 `facture` — classe `Facture` (`modeles.py:617-632`)

Une facture fournisseur. Elle désigne ce qui est arrivé ; plusieurs réceptions (camions) peuvent
la partager ; **un dossier d'importation au plus**.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 623 |
| fournisseur_id | INTEGER | | — | — | FK → `fournisseur.id` ; UQ `facture_fournisseur_id_numero_key` (fournisseur_id, numero) | | 624 |
| numero | VARCHAR(64) | | — | — | (idem) | numéro du fournisseur | 625 |
| date | DATE | O | — | — | | | 626 |
| montant | FLOAT | | 0 | `'0'` | CK `facture_montant_check` : `>= 0` | dans `devise` ; 0 = pas saisi (l'échéancier prend Σ pesée × prix des réceptions validées) | 627 |
| devise | VARCHAR(3) | | `'MAD'` | — | FK → `devise.code` | = devise des lignes de sa réception (API) ; ne change pas si d'autres réceptions la portent | 628 |
| echeance | DATE | O | — | — | | saisie, sinon date + `fournisseur.delai_paiement_jours` (≥ date) | 629 |
| payee_le | DATE | O | — | — | | réglée : sort de l'échéancier | 630 |

Relation : `fournisseur` (`joined`). Créée/complétée par `PUT /receptions/{id}/facture`
(`api/receptions.py:610-660`) ; un numéro vide détache la facture de la réception.

#### 7.4.4 `reception` — classe `Reception` (`modeles.py:635-659`)

L'arrivée d'un camion (un BL), **une devise par réception**. Brouillon modifiable/supprimable, puis
validation (écrit les entrées), puis éventuelle annulation (contre-passation).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 639 |
| numero | VARCHAR(32) | O | — | — | UQ `reception_numero_key` | `REC-AAAA-NNNN` à la validation | 642 |
| statut | VARCHAR(12) | | `'brouillon'` | `'brouillon'` | CK `reception_statut_check` | § 6.7 | 643 |
| date | DATE | | — | — | | date d'arrivée = `date_effet` des entrées | 644 |
| fournisseur_id | INTEGER | | — | — | FK → `fournisseur.id` | | 645 |
| numero_bl | VARCHAR(64) | | `''` | `''` | | bon de livraison | 646 |
| facture_id | INTEGER | O | — | — | FK → `facture.id` | | 647 |
| observations | TEXT | | `''` | — | | | 648 |
| cree_par | VARCHAR(80) | | `''` | `''` | | réceptionnaire (moteur : `receptionnaire`) | 649 |
| cree_le | TIMESTAMP | | `maintenant()` | — | | | 650 |
| validee_par | VARCHAR(80) | | `''` | `''` | | qui a validé (moteur : `controleur_qualite`, `depot.py:396`) | 651 |
| controle_par | VARCHAR(80) | | `''` | `''` | | qui a contrôlé la qualité au quai | 652 |
| validee_le | TIMESTAMP | O | — | — | | | 653 |

Relations : `fournisseur`, `facture` (`joined`) ; `lignes` → `ReceptionLigne` (`all,
delete-orphan`, `selectin`, `order_by id`). Le motif d'une annulation est dans le journal (§ 9).

#### 7.4.5 `reception_ligne` — classe `ReceptionLigne` (`modeles.py:662-691`)

Une ligne pesée : un article, un lot, éventuellement la ligne de bon qu'elle livre.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 673 |
| reception_id | INTEGER | | — | — | FK → `reception.id` ODC | | 674 |
| commande_ligne_id | INTEGER | O | — | — | FK → `commande_ligne.id` | NULL = hors commande | 675 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 676 |
| lot_numero | VARCHAR(80) | | `''` | `''` | | numéro de lot de l'étiquette, ou `LOT INTERNE` | 677 |
| quantite_attendue | FLOAT | | 0 | `'0'` | | kg restant à livrer sur la ligne de bon, **recalé** à chaque lecture/validation d'un brouillon (0 si bon soldé/annulé ou reste ≤ tolérance) | 678 |
| quantite_bl | FLOAT | | 0 | `'0'` | CK `reception_ligne_check` : `quantite_pesee >= 0 AND quantite_bl >= 0 AND nb_palettes >= 0 AND bobines_en_plus >= 0` | kg annoncés par le BL | 679 |
| quantite_pesee | FLOAT | | 0 | `'0'` | (idem) | kg **pesés** = ce qui entre en stock (> 0 exigé à la validation) | 680 |
| nb_palettes | FLOAT | | 0 | `'0'` | (idem) | | 681 |
| bobines_en_plus | FLOAT | | 0 | `'0'` | (idem) | bobines en vrac | 682 |
| nb_bobines | FLOAT | | 0 | `'0'` | | total = palettes × `article.bobines_palette` + vrac (`api/receptions.py:430`) | 683 |
| magasin_id | INTEGER | O | — | — | FK → `magasin.id` | rangement ; **remplacé par la quarantaine** pour une ligne sous réserve ; NULL possible pour un refus | 684 |
| qualite | VARCHAR(10) | | `'conforme'` | `'conforme'` | CK `reception_ligne_qualite_check` | § 6.7 | 685 |
| observations | VARCHAR(300) | | `''` | `''` | | | 686 |
| prix | FLOAT | | 0 | `'0'` | (pas de CK) | prix au kg dans `devise` ; recalé sur le prix confirmé de la ligne de bon | 687 |
| devise | VARCHAR(3) | | `'MAD'` | `'MAD'` | pas de FK | une seule devise par réception | 688 |
| lot_id | INTEGER | O | — | — | FK → `lot.id` | posé à la validation (NULL pour un refus) | 689 |

Relation : `article` (`joined`).

### 7.5 Production : ordres de fabrication

#### 7.5.1 `bon_sortie` — classe `BonSortie` (`modeles.py:699-730`)

Un **ordre de fabrication** (OF) : ce qu'on tisse (m² par qualité) et les fils envoyés aux
machines (lot par lot). Un ordre sert une fois, un jour ; les numéros suivent les dates.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 709 |
| numero | VARCHAR(32) | O | — | — | UQ `bon_sortie_numero_key` | `OF-AAAA-NNNN` à la validation | 710 |
| statut | VARCHAR(12) | | `'brouillon'` | `'brouillon'` | CK `bon_sortie_statut_check` : `brouillon, valide, annule` | | 711 |
| date | DATE | | — | — | | date des sorties ; ≥ date du dernier ordre non brouillon | 712 |
| magasin_id | INTEGER | | — | — | FK → `magasin.id` | magasin d'où sortent les fils | 713 |
| metier_id | INTEGER | O | — | — | FK → `metier.id` | métier visé (facultatif) | 714 |
| commentaire | VARCHAR(300) | | `''` | `''` | | | 715 |
| cree_par | VARCHAR(80) | | `''` | `''` | | | 716 |
| cree_le | TIMESTAMP | | `maintenant()` | — | | | 717 |
| valide_par | VARCHAR(80) | | `''` | `''` | | | 718 |
| valide_le | TIMESTAMP | O | — | — | | sert à retrouver la recette en vigueur le jour de la validation | 719 |
| theorique | TEXT | O | — | — | | **prévu figé** à la validation (JSON, § 8.1) ; NULL = validé avant l'étape 9 | 723 |

Relations : `fabrications` → `BonFabrication`, `lignes` → `BonLigne` (`all, delete-orphan`,
`selectin`, `order_by id`) (`:725-730`). Net emporté par un ordre = −Σ `mouvement.quantite` où
`ordre_id` = l'ordre (sorties moins retours).

#### 7.5.2 `bon_fabrication` — classe `BonFabrication` (`modeles.py:733-742`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 737 |
| bon_id | INTEGER | | — | — | FK → `bon_sortie.id` ODC | | 738 |
| qualite_id | INTEGER | | — | — | FK → `qualite.id` | qualité tissée (en service) | 739 |
| m2 | FLOAT | | — | — | CK `bon_fabrication_m2_check` : `m2 > 0` | m² à tisser | 740 |

Relation : `qualite` (`joined`). Pas d'unicité (bon, qualité) : une qualité peut figurer deux fois.

#### 7.5.3 `bon_ligne` — classe `BonLigne` (`modeles.py:745-756`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 749 |
| bon_id | INTEGER | | — | — | FK → `bon_sortie.id` ODC | | 750 |
| article_id | INTEGER | | — | — | FK → `article.id` | copie de `lot.article_id` | 751 |
| lot_id | INTEGER | | — | — | FK → `lot.id` | lot à sortir (présent à la date de l'ordre) | 752 |
| quantite | FLOAT | | — | — | CK `bon_ligne_quantite_check` : `> 0` | kg (saisis en kg, bobines ou palettes, convertis) | 753 |

Relations : `article`, `lot` (`joined`).

### 7.6 Opérations de stock

#### 7.6.1 `operation` — classe `Operation` (`modeles.py:773-798`)

Les autres gestes de stock, chacun son document : stock d'ouverture, retour des machines, transfert
(dont mise en quarantaine et libération), ajustement justifié, retour au fournisseur.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 780 |
| numero | VARCHAR(32) | O | — | — | UQ `operation_numero_key` | `OUV/RET/TRF/AJU/RFO-AAAA-NNNN` à la validation | 783 |
| type | VARCHAR(20) | | — | — | CK `operation_type_check` (5 valeurs) | ne change jamais | 784 |
| statut | VARCHAR(12) | | `'brouillon'` | `'brouillon'` | CK `operation_statut_check` | | 785 |
| date | DATE | | — | — | | date_effet des mouvements ; retour machine ≥ date de l'ordre | 786 |
| bon_id | INTEGER | O | — | — | FK → `bon_sortie.id` | **retour machine** : l'ordre (validé) d'où revient la matière | 787 |
| fournisseur_id | INTEGER | O | — | — | FK → `fournisseur.id` | retour fournisseur (un seul fournisseur par opération) | 788 |
| motif | VARCHAR(80) | | `''` | `''` | | § 6.5 | 789 |
| commentaire | VARCHAR(300) | | `''` | `''` | | justification | 790 |
| cree_par | VARCHAR(80) | | `''` | `''` | | | 791 |
| cree_le | TIMESTAMP | | `maintenant()` | — | | | 792 |
| validee_par | VARCHAR(80) | | `''` | `''` | | | 793 |
| validee_le | TIMESTAMP | O | — | — | | | 794 |

Relation : `lignes` → `OperationLigne` (`all, delete-orphan`, `selectin`, `order_by id`).

#### 7.6.2 `operation_ligne` — classe `OperationLigne` (`modeles.py:801-817`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 805 |
| operation_id | INTEGER | | — | — | FK → `operation.id` ODC | | 806 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 807 |
| lot_id | INTEGER | O | — | — | FK → `lot.id` | NULL pour une ouverture ou une matière retrouvée : le lot se crée à la validation | 808 |
| lot_numero | VARCHAR(80) | | `''` | `''` | | numéro du lot à créer (ou recopie) | 809 |
| magasin_id | INTEGER | | — | — | FK → `magasin.id` | magasin (source pour un transfert) | 810 |
| magasin_destination_id | INTEGER | O | — | — | FK → `magasin.id` | transfert seulement, ≠ source | 811 |
| quantite | FLOAT | | — | — | CK `operation_ligne_check` : `quantite <> 0 AND prix >= 0` | kg ; > 0 sauf ajustement (signé) ; un retour fournisseur est stocké **positif** et écrit négatif | 812 |
| prix | FLOAT | | 0 | `'0'` | (idem) | ouverture seulement : prix au kg | 813 |
| devise | VARCHAR(3) | | `'MAD'` | `'MAD'` | pas de FK | ouverture seulement | 814 |

Relations : `article`, `lot` (`joined`). L'alimentation ne reçoit ni `prix` ni `devise`
(`api/operations.py:201-206`).

### 7.7 Inventaire

#### 7.7.1 `inventaire` — classe `Inventaire` (`modeles.py:825-842`)

Un comptage, tournant (par magasin, matières, rôles, compositions, classes ABC) ou complet.
Ouvert : les mouvements sont **suspendus** sur son magasin (tous les magasins si `magasin_id` NULL).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 829 |
| numero | VARCHAR(32) | | — | — | UQ `inventaire_numero_key` ; NOT NULL | `INV-AAAA-NNNN` **à l'ouverture** | 830 |
| libelle | VARCHAR(120) | | `''` | `''` | | « Inventaire » par défaut | 831 |
| statut | VARCHAR(10) | | `'ouvert'` | `'ouvert'` | CK `inventaire_statut_check` : `ouvert, valide` | | 832 |
| date | DATE | | — | — | | date des ajustements ; aucun lot figé ne doit avoir bougé après | 833 |
| magasin_id | INTEGER | O | — | — | FK → `magasin.id` | NULL = tous les magasins | 834 |
| tolerance | FLOAT | | 0.02 | `'0.02'` | | écart relatif au-delà duquel une justification est exigée (défaut : réglage `tolerance_inventaire`) | 835 |
| cree_par | VARCHAR(80) | | `''` | `''` | | | 836 |
| valide_par | VARCHAR(80) | | `''` | `''` | | | 837 |
| valide_le | TIMESTAMP | O | — | — | | | 838 |

Relation : `lignes` → `InventaireLigne` (`all, delete-orphan`, `selectin`, `order_by id`).

#### 7.7.2 `inventaire_ligne` — classe `InventaireLigne` (`modeles.py:845-862`)

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 849 |
| inventaire_id | INTEGER | | — | — | FK → `inventaire.id` ODC ; UQ `inventaire_ligne_inventaire_id_lot_id_magasin_id_key` | | 850 |
| lot_id | INTEGER | | — | — | FK → `lot.id` | | 851 |
| magasin_id | INTEGER | | — | — | FK → `magasin.id` | | 852 |
| theorique | FLOAT | | 0 | `'0'` | | kg du solde **figé à l'ouverture** (0 pour un lot trouvé) | 853 |
| compte | FLOAT | O | — | — | | kg comptés (premier comptage) ; NULL = pas compté | 854 |
| nb_palettes | FLOAT | O | — | — | | ce que le compteur a vu | 856 |
| nb_bobines | FLOAT | O | — | — | | | 857 |
| second_compte | FLOAT | O | — | — | | recomptage par une autre personne : **remplace** `compte` à la validation | 858 |
| second_par | VARCHAR(80) | | `''` | `''` | | | 859 |
| justification | VARCHAR(300) | | `''` | `''` | | obligatoire (≥ 3 car.) si l'écart sort de la tolérance | 860 |

Relation : `lot` (`joined`). À la validation : pour chaque ligne comptée, écart = (second_compte
sinon compte) − theorique ; si |écart| ≥ 1 g → mouvement `AJUSTEMENT`, `document='inventaire'`,
motif « Écart d'inventaire ».

### 7.8 Importations

#### 7.8.1 `dossier` — classe `Dossier` (`modeles.py:870-895`)

Un dossier d'importation = **une facture** du fournisseur, la marchandise qu'elle a apportée (une
livraison, parfois en deux camions) et les frais payés pour elle. Sans facture : dossier d'avant la
mise en service, saisi à la main (ou repris de l'ERP Fil, pouvant alors mêler plusieurs factures).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 879 |
| numero | VARCHAR(16) | | — | — | UQ `dossier_numero_key` | `NN/AA` (ou saisi à la main) | 880 |
| libelle | VARCHAR(160) | | `''` | `''` | | « <fournisseur> — facture <n°> » par défaut | 881 |
| date_arrivee | DATE | O | — | — | | défaut : la plus ancienne réception de la facture ; année du numéro | 882 |
| banque | VARCHAR(32) | | `''` | `''` | | banque du paiement | 883 |
| statut | VARCHAR(8) | | `'ouvert'` | `'ouvert'` | CK `dossier_statut_check` : `ouvert, clos` | clos = coût figé | 884 |
| clos_le | TIMESTAMP | O | — | — | | instant de clôture | 885 |
| commentaire | TEXT | | `''` | — | | | 886 |
| facture_id | INTEGER | O | — | — | FK → `facture.id` ; **UQ `dossier_facture_id_key`** | la facture du dossier ; NULL = saisi à la main / repris | 887 |

Relations : `facture` (`joined`) ; `lignes`, `charges` (`all, delete-orphan`, `selectin`,
`order_by id`) (`:889-895`).

#### 7.8.2 `dossier_ligne` — classe `DossierLigne` (`modeles.py:898-925`)

Une marchandise du dossier : une ligne de réception rattachée, ou une ligne saisie à la main.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 902 |
| dossier_id | INTEGER | | — | — | FK → `dossier.id` ODC | | 903 |
| reception_ligne_id | INTEGER | O | — | — | FK → `reception_ligne.id` ; **UQ `dossier_ligne_reception_ligne_id_key`** | NULL = saisie à la main | 904-906 |
| article_id | INTEGER | | — | — | FK → `article.id` | | 907 |
| lot_id | INTEGER | O | — | — | FK → `lot.id` | | 908 |
| fournisseur_id | INTEGER | O | — | — | FK → `fournisseur.id` | | 909 |
| quantite | FLOAT | | 0 | `'0'` | CK `dossier_ligne_check` : `quantite >= 0 AND valeur_devise >= 0 AND cours >= 0` | **kg** (= pesée) | 910 |
| valeur_devise | FLOAT | | 0 | `'0'` | (idem) | valeur **totale** dans `devise` = pesée × prix (pas le montant de la facture) | 911 |
| devise | VARCHAR(3) | | `'MAD'` | `'MAD'` | pas de FK | | 912 |
| cours | FLOAT | | 0 | `'0'` | (idem) | cours de la ligne : à l'entrée, celui **figé par le bon** ; puis celui payé à la banque ; à la clôture un 0 devient le cours du jour. **0 = « le cours de la devise »** (lu au jour) ; en MAD, pas de cours | 913 |
| commentaire | VARCHAR(300) | | `''` | `''` | | reçoit « cours du jour X figé à la clôture du … » | 914 |
| poids_kg | FLOAT | O | — | — | | poids figé en kg ; recopie `quantite` depuis l'étape 14 ; posé à l'entrée et à la clôture | 918 |

Relations : `article`, `lot` (`joined`). Propriété `kilos` = `quantite` (`:923-925`).

#### 7.8.3 `dossier_charge` — classe `DossierCharge` (`modeles.py:928-947`)

Un frais (une **pièce**) du dossier, en **MAD**.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 931 |
| dossier_id | INTEGER | | — | — | FK → `dossier.id` ODC | | 932 |
| poste | VARCHAR(16) | | — | — | FK → `poste_frais.code` | | 933 |
| montant | FLOAT | | 0 | `'0'` | **aucun CK** | MAD ; ≠ 0 ; **négatif = avoir** (ne doit pas rendre une marchandise négative) | 934 |
| ligne_id | INTEGER | O | — | — | FK → `dossier_ligne.id` **ODC** | NULL = frais **global** réparti selon la clé du poste ; sinon frais d'une seule marchandise | 935 |
| piece | VARCHAR(64) | | `''` | `''` | | n° de quittance, facture du transitaire… | 936 |
| commentaire | VARCHAR(300) | | `''` | `''` | | | 937 |
| prestataire | VARCHAR(120) | | `''` | `''` | | | 938 |
| date_piece | DATE | O | — | — | | | 939 |
| echeance | DATE | O | — | — | | | 940 |
| payee_le | DATE | O | — | — | | réglé : sort de l'échéancier | 941 |

Relation : `parts` → `DossierChargePart` (`all, delete-orphan`, `selectin`, `order_by ligne_id`).

#### 7.8.4 `dossier_charge_part` — classe `DossierChargePart` (`modeles.py:950-959`)

La part d'un frais global **figée** sur une marchandise : posée quand la clé d'un poste change
alors que le dossier est clos (`api/referentiels_import.py:107-143`), ou reprise par l'étape 13.
Elle l'emporte sur la clé tant qu'elle couvre tout le frais (Σ parts = montant à 0,005 près,
`verificateur.py:173-178`). Effacée si le frais change de montant ou de marchandise, ou si une
marchandise qui en a une part est détachée.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| charge_id | INTEGER | | — | — | PK (charge_id, ligne_id) ; FK → `dossier_charge.id` ODC | | 955-956 |
| ligne_id | INTEGER | | — | — | PK ; FK → `dossier_ligne.id` ODC | | 957-958 |
| montant | FLOAT | | 0 | `'0'` | | MAD (non arrondi) | 959 |

### 7.9 Suivi

#### 7.9.1 `reclamation` — classe `Reclamation` (`modeles.py:967-990`)

Une réclamation au fournisseur sur une livraison, suivie jusqu'à sa réponse.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 974 |
| numero | VARCHAR(32) | | — | — | UQ `reclamation_numero_key` | `RCL-AAAA-NNNN` | 975 |
| fournisseur_id | INTEGER | | — | — | FK → `fournisseur.id` | | 976 |
| reception_id | INTEGER | O | — | — | FK → `reception.id` | réception **validée** du même fournisseur | 977 |
| lot_id | INTEGER | O | — | — | FK → `lot.id` | lot livré par ce fournisseur (et dans la réception si donnée) | 978 |
| motif | VARCHAR(80) | | `''` | `''` | | § 6.8 | 979 |
| description | TEXT | | `''` | — | | | 980 |
| quantite | FLOAT | | 0 | `'0'` | | kg en cause (≤ livré par la réception) | 981 |
| montant_demande | FLOAT | | 0 | `'0'` | | dans `devise` | 982 |
| devise | VARCHAR(3) | | `'MAD'` | `'MAD'` | pas de FK (contrôle API) | | 983 |
| reponse | TEXT | | `''` | — | | | 984 |
| issue | VARCHAR(40) | | `''` | `''` | | § 6.8 | 985 |
| montant_obtenu | FLOAT | | 0 | `'0'` | | | 986 |
| statut | VARCHAR(8) | | `'ouverte'` | `'ouverte'` | CK `reclamation_statut_check` : `ouverte, close` | | 987 |
| ouverte_le | DATE | | — | — | | ≤ aujourd'hui, ≥ date de la réception | 988 |
| close_le | DATE | O | — | — | | | 989 |
| cree_par | VARCHAR(80) | | `''` | `''` | | | 990 |

#### 7.9.2 `signalement` — classe `Signalement` (`modeles.py:993-1006`)

Un besoin signalé par l'atelier (« il manque du rouge 2900 pour demain ») ; tout le monde signale,
les achats traitent.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 998 |
| quand | TIMESTAMP | | `maintenant()` | — | | | 999 |
| par | VARCHAR(80) | | `''` | `''` | | nom | 1000 |
| article_id | INTEGER | O | — | — | FK → `article.id` | matière visée (facultatif) | 1001 |
| texte | VARCHAR(500) | | `''` | `''` | | 2 à 500 car. | 1002 |
| urgence | VARCHAR(12) | | `'normale'` | `'normale'` | (pas de CK) | `normale` / `urgente` | 1003 |
| traite_par | VARCHAR(80) | | `''` | `''` | | | 1004 |
| traite_le | TIMESTAMP | O | — | — | | NULL = à traiter | 1005 |
| reponse | VARCHAR(500) | | `''` | `''` | | | 1006 |

#### 7.9.3 `piece_jointe` — classe `PieceJointe` (`modeles.py:1009-1022`)

Un document attaché (facture, BL, déclaration douanière, photo d'un défaut). Le fichier est sur le
disque (`config.PIECES`), recopié à chaque sauvegarde (commit eb60466).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 1014 |
| objet | VARCHAR(20) | | — | — | pas de CK | § 6.9 | 1015 |
| objet_id | INTEGER | | — | — | IX `ix_piece_jointe_objet_id` ; pas de FK | | 1016 |
| nom | VARCHAR(200) | | `''` | `''` | | nom d'origine du fichier | 1017 |
| type_mime | VARCHAR(100) | | `''` | `''` | | | 1018 |
| taille | INTEGER | | 0 | — | | octets (≤ 20 Mo) | 1019 |
| chemin | VARCHAR(300) | | `''` | `''` | | chemin **absolu** du fichier | 1020 |
| par | VARCHAR(80) | | `''` | `''` | | | 1021 |
| quand | TIMESTAMP | | `maintenant()` | — | | | 1022 |

Retirer une pièce supprime la ligne, **pas le fichier** (`api/suivi.py:290`).

#### 7.9.4 `recette_version` — classe `RecetteVersion` (`modeles.py:1025-1038`)

Chaque recette enregistrée, datée et signée. Écrite **automatiquement** par deux écouteurs de
session (`api/suivi.py:440-476`) : `before_flush` note les qualités dont une `Recette` ou un
`QualitePoids` est créé/modifié/supprimé ; `before_commit` photographie leur recette et leurs poids.

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| id | SERIAL | | | | PK | | 1030 |
| qualite_id | INTEGER | | — | — | FK → `qualite.id` ODC ; IX `ix_recette_version_qualite_id` | | 1031 |
| quand | TIMESTAMP | | `maintenant()` | — | | à partir de quand cette recette vaut | 1032 |
| par | VARCHAR(80) | | `''` | `''` | | auteur (celui du journal écrit dans la même transaction) | 1033 |
| contenu | TEXT | | `'[]'` | — | | JSON des lignes (§ 8.3) | 1034 |
| poids | TEXT | O | — | — | | JSON {rôle: poids} ; NULL = version d'avant l'étape 9 | 1038 |

#### 7.9.5 `indicateur_jour` — classe `IndicateurJour` (`modeles.py:1041-1047`)

La photo du jour des indicateurs du cockpit (une par jour ; la dernière l'emporte). Prise par la
tâche de fond si absente pour aujourd'hui (`api/suivi.py:841-847`) ou à la demande (direction).

| Colonne | Type | Null | Défaut Py | Défaut SQL | Contraintes | Sens | Réf. |
|---|---|---|---|---|---|---|---|
| jour | DATE | | — | — | PK | | 1046 |
| contenu | TEXT | | `'{}'` | — | | JSON (§ 8.4) | 1047 |

### 7.10 `schema_version` (hors modèles, `db.py:398-403`)

| Colonne | Type | Null | Défaut SQL | Contraintes | Sens |
|---|---|---|---|---|---|
| numero | INTEGER | | — | PK | n° d'étape (§ 4) |
| libelle | TEXT | | — | | libellé de l'étape |
| applique_le | TIMESTAMP | | `now()` | | début de la transaction de migration (heure de Casablanca) |

### 7.11 Reprise des référentiels de l'ERP Fil (`reprise.py`)

`python -m gestion_mp.reprise [--source …] [--essai]` lit une **copie** de la base SQLite de l'ERP
Fil (empreinte SHA-256 vérifiée avant/après, jamais écrite) et ajoute ce qui manque (jamais
d'écrasement) : classification (`natures→composition`, `types_fil`, `titrages`, `couleurs`), cours
USD/EUR (`taux_usd_mad`, `taux_eur_mad`), réglages connus (sauf `devise`, `date_saisie`,
`taux_eur_mad`, `taux_usd_mad`, `methode`), fournisseurs (délai ≤ 0 → 60), articles (tout au kilo,
`unite_achat 'ml' → 'kg'`, titrage retrouvé par valeur et unité ou créé), qualités (8 colonnes de
poids → `qualite_poids`, saisonnalité `"c1;c2;…"` → `qualite_saison`), recettes, magasins (type
« Quarantaine » conservé), métiers, fils montés. **L'activité n'est pas reprise.** Si la base est
vide de magasins, ceux de l'ERP Fil sont créés **avant** `initialiser()`, qui n'ajoute alors que la
quarantaine. L'import **complet** (activité comprise) n'existe que pour une base `…_comparaison`
(`outils/importer_erp_fil.py`).

---

## 8. Contenus JSON et données rangées dans du texte

### 8.1 `bon_sortie.theorique` (`api/production.py:480-493`)

```json
{"perte": 0.02, "fils": {"<article.reference>": <kg hors perte>, …}}
```
`fils[ref] = Σ (kg/m² de la référence dans la qualité × m² de l'ordre)` sur les fabrications de
l'ordre ; `perte` = `taux_perte` du jour. Clé = **référence** de l'article (texte).

### 8.2 `commande.version_approuvee` (`api/achats.py:209-230`)

```json
{"montant": <montant de référence dans la devise du bon>,
 "lignes": [{"article_id": 12, "quantite": 1000.0, "unite_achat": "kg", "contenance": 1.0,
             "prix": 2.5, "prix_confirme": true, "confirme_par": "…", "confirme_le": "2026-10-08T10:00:00" | null}]}
```
La version du bon **que le fournisseur a** : figée à l'envoi et à l'approbation (`montant` relevé),
et à chaque geste accepté sans la direction (`montant` gardé). Une hausse se mesure à `montant`
(ou, faute de version, à `montant_approuve ÷ cours du bon`) ; un renvoi de la direction rétablit
ces lignes (une ligne déjà reçue reste).

### 8.3 `recette_version.contenu` et `.poids` (`api/suivi.py:471-474`, `db.py:186-193`)

```json
contenu: [{"reference": "<article.reference>", "role": "Poil", "pourcentage": 60.0}, …]   (trié par rôle)
poids:   {"Poil": 1.2, "Cuir": 0.85, …}   (kg/m², ml/m² pour un rôle linéaire)
```

### 8.4 `indicateur_jour.contenu` (`api/suivi.py:489-512`)

```json
{"valeur_stock_mad": …, "couverture_jours": …, "ruptures": …, "critiques": …, "urgents": …,
 "a_commander_mad": …, "commandes_en_cours_mad": …, "otif_moyen": … | null}
```

### 8.5 Autres textes porteurs de sens

| Où | Contenu |
|---|---|
| `parametre.valeur` | nombre en texte, date ISO (`date_cloture`, `courriel_dernier_envoi`), texte |
| `parametre_historique.cle = 'cours_<CODE>'` | historique des cours d'une devise (valeur = taux) |
| `utilisateur.empreinte` | `scrypt$sel$hash` |
| `dossier_ligne.commentaire` | « cours du jour X figé à la clôture du jj/mm/aaaa » |
| `dossier_charge.commentaire` (ancien) | « … · réparti … avant le changement de clé du jj/mm/aaaa » (repris par l'étape 13) |
| `mouvement.commentaire` | « Annulation du mouvement n°X », « sous réserve » |

---

## 9. Le journal d'audit utilisé comme source de données

Certaines informations **n'existent que dans `journal`** ; la réécriture doit leur donner une
place (ou relire le journal à l'identique).

| Information | Écrite par | Lue par | Format |
|---|---|---|---|
| **Versions du plan de production** (base, saisonnalité, en service) de chaque qualité, avant/après | `production_plan.noter_plan` (`api/production_plan.py:49-61`), action `plan de production`, objet `qualite`, `objet_id` = qualité | `depot.versions_plan` (`depot.py:156-170`) : juger un mois passé sur le plan de son époque | `detail = "<texte>\nplan={\"avant\": {\"b\": base, \"c\": [12 coefficients], \"a\": en service}, \"apres\": {…}}"` (`MARQUE_PLAN = "plan="`, `depot.py:153`) ; `a` absent = en service |
| **Bon soldé à la main** et quand | action `commande soldée` (`api/achats.py:597,903`) | `depot.soldes_a_la_main` (`depot.py:43-52`), `origine_du_solde` (`api/achats.py:550-559`) | `detail` finissant par « tout reçu » = solde automatique ; sinon = à la main ; aucune ligne = bon repris |
| **Dernier renvoi de la direction** et son motif | action `renvoi aux achats` | `api/achats.py:136-146` (annulé par une action ultérieure `commande à approuver`, `envoi commande`, `approbation commande`) | `detail = "<n° du bon> · <motif>"` |
| **Motif d'annulation d'une réception** | action `annulation réception` | `api/receptions.py:253-258` | `detail = "<n°> · <motif>"` (« sans motif » par défaut) |
| **Dernier montage d'un métier** (qui, quand, quoi) | action `montage`, objet `metier` | `api/referentiels.py:1188-1195` | texte |
| **Auteur d'une version de recette** | `s.info["auteur"]` = utilisateur du dernier `Journal` ajouté à la session | `api/suivi.py:452-453` | |

---

## 10. Schéma des relations (toutes les clés étrangères)

73 clés étrangères. ODC = `ON DELETE CASCADE`, OUC = `ON UPDATE CASCADE` ; sinon `NO ACTION`
(suppression refusée tant qu'une ligne pointe).

| # | table.colonne | → cible | Règle | Remarque |
|---|---|---|---|---|
| 1 | session_ouverte.utilisateur_id | utilisateur.id | ODC | |
| 2 | fournisseur.devise | devise.code | | |
| 3 | article.role | role_nomenclature.code | | |
| 4 | article.composition | composition.code | OUC | |
| 5 | article.type_fil | type_fil.code | OUC | |
| 6 | article.titrage | titrage.code | OUC | |
| 7 | article.couleur | couleur.code | OUC | |
| 8 | article.fournisseur_id | fournisseur.id | | |
| 9 | article.devise | devise.code | | |
| 10 | article.code_douanier | code_douanier.code | OUC | |
| 11 | qualite_poids.qualite_id | qualite.id | ODC | |
| 12 | qualite_poids.role | role_nomenclature.code | | |
| 13 | qualite_saison.qualite_id | qualite.id | ODC | |
| 14 | recette.qualite_id | qualite.id | ODC | |
| 15 | recette.article_id | article.id | | |
| 16 | fil_monte.metier_id | metier.id | ODC | |
| 17 | fil_monte.article_id | article.id | | |
| 18 | lot.article_id | article.id | | |
| 19 | lot.fournisseur_id | fournisseur.id | | |
| 20 | solde.lot_id | lot.id | | PK |
| 21 | solde.magasin_id | magasin.id | | PK |
| 22 | mouvement.article_id | article.id | | redondant avec lot |
| 23 | mouvement.lot_id | lot.id | | |
| 24 | mouvement.magasin_id | magasin.id | | |
| 25 | mouvement.ordre_id | bon_sortie.id | | |
| 26 | mouvement.contrepasse_id | mouvement.id | | UNIQUE |
| 27 | commande.fournisseur_id | fournisseur.id | | |
| 28 | commande.devise | devise.code | | |
| 29 | commande_ligne.commande_id | commande.id | ODC | |
| 30 | commande_ligne.article_id | article.id | | |
| 31 | facture.fournisseur_id | fournisseur.id | | |
| 32 | facture.devise | devise.code | | |
| 33 | reception.fournisseur_id | fournisseur.id | | |
| 34 | reception.facture_id | facture.id | | |
| 35 | reception_ligne.reception_id | reception.id | ODC | |
| 36 | reception_ligne.commande_ligne_id | commande_ligne.id | | |
| 37 | reception_ligne.article_id | article.id | | |
| 38 | reception_ligne.magasin_id | magasin.id | | |
| 39 | reception_ligne.lot_id | lot.id | | |
| 40 | bon_sortie.magasin_id | magasin.id | | |
| 41 | bon_sortie.metier_id | metier.id | | |
| 42 | bon_fabrication.bon_id | bon_sortie.id | ODC | |
| 43 | bon_fabrication.qualite_id | qualite.id | | |
| 44 | bon_ligne.bon_id | bon_sortie.id | ODC | |
| 45 | bon_ligne.article_id | article.id | | |
| 46 | bon_ligne.lot_id | lot.id | | |
| 47 | operation.bon_id | bon_sortie.id | | |
| 48 | operation.fournisseur_id | fournisseur.id | | |
| 49 | operation_ligne.operation_id | operation.id | ODC | |
| 50 | operation_ligne.article_id | article.id | | |
| 51 | operation_ligne.lot_id | lot.id | | |
| 52 | operation_ligne.magasin_id | magasin.id | | |
| 53 | operation_ligne.magasin_destination_id | magasin.id | | |
| 54 | inventaire.magasin_id | magasin.id | | |
| 55 | inventaire_ligne.inventaire_id | inventaire.id | ODC | |
| 56 | inventaire_ligne.lot_id | lot.id | | |
| 57 | inventaire_ligne.magasin_id | magasin.id | | |
| 58 | dossier.facture_id | facture.id | | UNIQUE |
| 59 | dossier_ligne.dossier_id | dossier.id | ODC | |
| 60 | dossier_ligne.reception_ligne_id | reception_ligne.id | | UNIQUE |
| 61 | dossier_ligne.article_id | article.id | | |
| 62 | dossier_ligne.lot_id | lot.id | | |
| 63 | dossier_ligne.fournisseur_id | fournisseur.id | | |
| 64 | dossier_charge.dossier_id | dossier.id | ODC | |
| 65 | dossier_charge.poste | poste_frais.code | | |
| 66 | dossier_charge.ligne_id | dossier_ligne.id | **ODC** | supprimer une marchandise supprime ses frais propres (l'API l'interdit d'abord) |
| 67 | dossier_charge_part.charge_id | dossier_charge.id | ODC | |
| 68 | dossier_charge_part.ligne_id | dossier_ligne.id | ODC | |
| 69 | reclamation.fournisseur_id | fournisseur.id | | |
| 70 | reclamation.reception_id | reception.id | | |
| 71 | reclamation.lot_id | lot.id | | |
| 72 | signalement.article_id | article.id | | |
| 73 | recette_version.qualite_id | qualite.id | ODC | pas de relationship ORM : cascade côté base |

**Références sans clé étrangère** (à rendre explicites dans PRO) :

| Colonne | Désigne | Nature |
|---|---|---|
| mouvement.document + document_id | reception / bon_sortie / operation / inventaire | polymorphe |
| mouvement.paire | mouvement.id (ligne sortie du transfert) | auto-référence |
| journal.objet + objet_id | toute table | polymorphe |
| piece_jointe.objet + objet_id | 7 tables | polymorphe |
| mouvement.devise, reception_ligne.devise, operation_ligne.devise, dossier_ligne.devise, reclamation.devise | devise.code | texte |
| tous les `*_par`, `cree_par`, `auteur`, `par`, `journal.utilisateur` | utilisateur.**nom** | texte (nom, pas id) |
| parametre_historique.cle | parametre.cle ou `cours_<devise>` | texte |
| bon_sortie.theorique, recette_version.contenu | article.**reference** | JSON |
| commande.version_approuvee | article.id | JSON |
| journal « plan de production » | qualite.id (objet_id) | JSON dans le texte |

Relations ORM (`relationship`, toutes sans `back_populates`) : Article→Fournisseur ; Qualite→poids,
saisons (ordre `mois`) ; Metier→fils (ordre `etage`) ; Lot→Article ; Commande→Fournisseur, lignes ;
CommandeLigne→Article ; Facture→Fournisseur ; Reception→Fournisseur, Facture, lignes ;
ReceptionLigne→Article ; BonSortie→fabrications, lignes ; BonFabrication→Qualite ;
BonLigne→Article, Lot ; Operation→lignes ; OperationLigne→Article, Lot ; Inventaire→lignes ;
InventaireLigne→Lot ; Dossier→Facture, lignes, charges ; DossierLigne→Article, Lot ;
DossierCharge→parts (ordre `ligne_id`). Les collections « lignes/fils/poids/saisons/charges/parts »
sont en `cascade="all, delete-orphan"`, `lazy="selectin"`, ordonnées par `id` sauf mention.

```
fournisseur ─┬─< article >── role_nomenclature, composition, type_fil, titrage, couleur, devise, code_douanier
             ├─< commande ─< commande_ligne >── article
             ├─< facture ─┬─< reception ─< reception_ligne >── article, magasin, lot, commande_ligne
             │            └── dossier (0..1) ─┬─< dossier_ligne >── reception_ligne (0..1), article, lot
             │                                └─< dossier_charge >── poste_frais ; ─< dossier_charge_part
             ├─< lot ─< solde >── magasin
             │       └─< mouvement >── magasin, bon_sortie (ordre), mouvement (contre-passation)
qualite ─< qualite_poids, qualite_saison, recette, recette_version ; ─< bon_fabrication >── bon_sortie
bon_sortie ─< bon_ligne >── lot ; ─< operation (retour machine) ─< operation_ligne >── lot, magasin×2
metier ─< fil_monte >── article ;  inventaire ─< inventaire_ligne >── lot, magasin
utilisateur ─< session_ouverte
```

---

## 11. Cycle de vie : ce qui s'écrit, se fige, se supprime

| Document | Création | Modification | Validation (écrit le stock) | Annulation | Suppression physique |
|---|---|---|---|---|---|
| commande | brouillon (sans n°) | lignes, dates, jalons ; hausse → approbation | envoi (n° BC, date, promesse, version partie) | clôture à la main (soldee/annulee) ; réouverture | **brouillon non parti** seulement (lignes en cascade) |
| reception | brouillon | brouillon seulement (recalé à chaque lecture) | n° REC, lots, entrées (`RECEPTION`), solde auto des bons | contre-passation, statut `annulee` ; interdite si portée par un dossier | brouillon seulement |
| bon_sortie | brouillon | brouillon seulement | n° OF, `theorique`, sorties | contre-passe ses sorties **et ses retours** (opérations + retours repris) | brouillon seulement |
| operation | brouillon | brouillon (type figé) | n° OUV/RET/TRF/AJU/RFO, mouvements | contre-passation, `annulee` | brouillon seulement |
| inventaire | ouvert (n° INV, théorique figé) | comptages | ajustements | — | **ouvert** (abandon) |
| dossier | ouvert (n° DOS) | lignes, frais, cours, réouverture | (pas de stock) clôture : cours et poids figés | réouverture (période close vérifiée) | ouvert seulement (frais perdus) |
| reclamation | ouverte (n° RCL) | réponse, issue | clôture (issue obligatoire) | réouverture | jamais |
| signalement | à traiter | — | traité | — | jamais |
| piece_jointe | ajout | — | — | — | ligne supprimée, fichier gardé |
| référentiels | — | — | — | désactivation | si non utilisé (FK) |

Ce qui ne se supprime **jamais** : `mouvement`, `solde`, `journal`, `parametre_historique`,
`recette_version`, `lot`, un document validé.

---

## 12. Les invariants

« Base » = garanti par PostgreSQL ; « Code » = garanti par le serveur ; « Vérif. » = vérifié a
posteriori par `verificateur.py` (SQL direct comparé aux écrans) ou par les contrôles
`calcul/controles.py` (C01–C38).

| # | Invariant | Base | Code | Vérif. |
|---|---|---|---|---|
| I01 | Le journal `mouvement` est la **seule** écriture de stock ; tout passe par `stock.ecrire` | — | `services/stock.py:1-7,122-212` (seuls appelants : réceptions, ordres, opérations, inventaires, contre-passations) | — |
| I02 | **Solde(lot, magasin) = Σ mouvement.quantite (lot, magasin)** | — (pas de déclencheur) | mise à jour du solde et ajout du mouvement dans la même transaction (`services/stock.py:187-211`) | `verificateur.py:65-73` ; contrôle **C12** (bloquant) via `depot._soldes` (`depot.py:550-559`) ; la Σ des soldes entre dans la signature du cache (`depot.py:680-682`) |
| I03 | **Un solde n'est jamais négatif** | CK `ck_solde_positif` `quantite >= -0.0005` (`modeles.py:479`) | refus si `solde + q < −0,001` (`services/stock.py:169-178`) ; arrondi 6 décimales ; < 1 g ⇒ 0 (`:187-189`) | `verificateur.py:70` ; C27 |
| I04 | Deux écritures sur le même (lot, magasin) se sérialisent | ligne de solde verrouillée | `INSERT … ON CONFLICT DO NOTHING` puis `SELECT … FOR UPDATE` avec `populate_existing` (`services/stock.py:63-74`) | — |
| I05 | **Aucun lot sous zéro à une date passée** (une sortie datée trouve la matière ce jour-là et ne la fait pas manquer ensuite) | — | `couvert_a_sa_date` sur toute écriture négative (`services/stock.py:77-119,179-180`), sous le verrou du solde | `verificateur.py:263-275` ; **C37** (bloquant) |
| I06 | Une écriture n'est jamais nulle | CK `quantite <> 0` (`modeles.py:507`) | `abs(q) < 1e-9` refusé (`services/stock.py:146-147`) | — |
| I07 | **Date permise** : ≥ 01/01/2000, ≤ aujourd'hui, > `date_cloture` | — | `date_permise` (`securite.py:199-216`), appelée par `ecrire` et à chaque saisie/validation | C14 (mouvement futur) |
| I08 | **Période close figée** : le coût d'une marchandise entrée dans une période close ne change plus (frais, cours, rattachement, retrait, réouverture, suppression de dossier, clé/nature d'un poste) | — | `cout_hors_periode_close` (`securite.py:225-276`) ; `api/importations.py`, `api/referentiels_import.py:170-179` | — |
| I09 | Une contre-passation est **datée comme l'original** — donc impossible dans une période close | — | `services/stock.py:256-262` + I07 | — |
| I10 | **Contre-passation unique** : une ligne ne s'annule qu'une fois | UQ `mouvement_contrepasse_id_key` + FK vers `mouvement` | `contrepasser_document` exclut les lignes déjà annulées et refuse 409 s'il ne reste rien (`services/stock.py:230-251`) | `verificateur.py:288-295` (annulation au coût exact de l'original) |
| I11 | Une contre-passation recopie type, lot, magasin, prix, devise, **cours**, ordre, motif ; quantité opposée ; sorties ré-entrées d'abord | — | `services/stock.py:252-270` | — |
| I12 | **Inventaire ouvert ⇒ mouvements suspendus** sur son magasin (tous si magasin NULL), sauf ses propres ajustements | — | `services/stock.py:154-168` (lu après le verrou du solde) | — |
| I13 | Au plus un inventaire ouvert par magasin (un inventaire global exclut tout autre) | — | `api/inventaires.py:274-282` | — |
| I14 | Un magasin désactivé ne reçoit rien ; ne se désactive pas ni ne change de type s'il détient du stock | — | `services/stock.py:152-153` ; `api/referentiels.py` `modifier_magasin` | — |
| I15 | **Transfert = deux lignes** de même `paire` (= id de la sortie), source ≠ destination | — | `services/stock.transferer` (`:215-227`) | traduit en une ligne par `depot._journal` (`depot.py:613-623`) |
| I16 | **Cours figé sur chaque mouvement** : MAD ou prix nul ⇒ 0 ; sinon cours de la commande (même devise, > 0), sinon cours du jour | — | `services/stock.py:181-186`, `api/receptions.py:552-559` | — |
| I17 | **Coût de chaque écriture** déterminé (non stocké) : la valeur se conserve, aucune écriture à coût nul sans raison | — | moteur `couts_du_journal` | `verificateur.py:251-261` (entrées − sorties = valeur du stock, à 1 MAD) ; `:277-286` (coût nul seulement pour une matière sans prix) ; `:297-319` (ordre de grandeur lot par lot) |
| I18 | **Numéros uniques** par document | UQ sur `commande`, `reception`, `bon_sortie`, `operation`, `inventaire`, `reclamation`, `dossier` `.numero` ; UQ `compteur(serie, annee)` | `securite.numero` sous `FOR UPDATE` (`securite.py:178-196`) | — |
| I19 | **Pas de trou** dans BC, REC, OF, OUV…RFO, LOT interne (M65) | (numero nullable) | numéro donné à l'envoi / validation (`api/achats.py:497-514`, `api/receptions.py:536-539`, `api/production.py:520`, `api/operations.py:409`) | — |
| I20 | **Les numéros d'OF suivent les dates** | — | verrou 7426110 + refus d'une date antérieure au dernier ordre (`api/production.py:513-519`) | C (ordres) |
| I21 | **Un dossier par facture** | UQ `dossier.facture_id` | `_porteurs` (dossiers repris sans facture qui portent déjà une marchandise de la facture) ; `IntegrityError` → 409 clair (`api/importations.py:146-188,573-591`) | — |
| I22 | Une ligne de réception est dans **au plus un** dossier | UQ `dossier_ligne.reception_ligne_id` | `_lignes_libres` sous `FOR SHARE` | C34 (marchandise sans dossier) |
| I23 | Une réception portée par un dossier ne s'annule pas (la détacher d'abord) | — | `api/receptions.py:589-591` | — |
| I24 | **Unité de stock = kg** (figée) | CK `ck_article_unite_kg` | — | — |
| I25 | Prix au kg ou au mètre ; au mètre ⇒ densité > 0 | CK `ck_article_unite_prix`, `ck_article_prix_au_metre` | aussi pour un rôle linéaire ; `unite_achat ≠ 'ml'` ; contenance > 0 hors kg (`api/referentiels.py:580-597`) | — |
| I26 | Rôle linéaire ⇔ Cuir, Franges, Ruban ; rôles de base intouchables | — | `api/referentiels.py:109-116,138-169` | — |
| I27 | **Recette à 100 % par rôle** | seulement 0 ≤ % ≤ 100 par ligne | — | **C01** ; `verificateur.py:130-139` |
| I28 | Toute recette enregistrée a sa version datée et signée | — | écouteurs `before_flush`/`before_commit` (`api/suivi.py:440-476`) | — |
| I29 | **Prévu d'un ordre figé** à sa validation ; plan versionné au journal ; le passé est jugé sur le plan et les recettes de son époque | — | `api/production.py:480-493,521` ; `noter_plan` ; `depot.py:156-196,314-325` | — |
| I30 | Lot unique par (article, numéro) | UQ `lot_article_id_numero_key` | `lot_ou_creer` idempotent (`services/stock.py:35-60`) | — |
| I31 | `mouvement.article_id = lot.article_id` (idem `bon_ligne`, `operation_ligne`, `reception_ligne`, `dossier_ligne`) | — | `ecrire` prend `lot.article_id` (`services/stock.py:193`) ; « Ce lot est d'une autre matière » (`api/operations.py:262-263`) | C16 (intégrité des mouvements) |
| I32 | **Reçu net** d'une ligne de bon = pesées validées non refusées − retours fournisseur du lot au prorata | — | `depot.recu_par_ligne` (`depot.py:59-108`) | `verificateur.py:75-94` |
| I33 | Bon **soldé automatiquement** quand chaque ligne est reçue (tolérance `toler_in_full`) et rien n'attend en quarantaine ; rouvert s'il ne l'est plus (sauf solde à la main) | — | `recaler_soldes` (`api/achats.py:572-603`) | — |
| I34 | Excédent de réception ≤ reste + `toler_excedent` × ligne ; bon parti, non annulé, daté avant la réception | — | `blocages` (`api/receptions.py:116-176`) ; bons verrouillés par id croissant | — |
| I35 | Une réception = une devise ; sa facture dans la même devise | — | `api/receptions.py:70-77,640-648` | C19 |
| I36 | Ligne refusée ⇒ aucune entrée ; ligne sous réserve ⇒ quarantaine ; sortie de quarantaine = décision des achats/direction avec motif « Libération de quarantaine » | — | `api/receptions.py:533-561` ; `api/operations.py:297-311,400-407` | — |
| I37 | Retour des machines ≤ ce qui est parti pour cet ordre, lot par lot ; daté ≥ l'ordre ; annuler un ordre annule ses retours | — | `api/operations.py:410-420` ; `api/production.py:556-580` | `verificateur.py:96-108` (net de chaque ordre) ; C03 (motif R) |
| I38 | Inventaire : écart hors tolérance justifié ; le second comptage l'emporte ; lots figés immobiles après la date | — | `api/inventaires.py:35-56,150-158,384-410` | C20 |
| I39 | Dossier clos : cours vides figés au cours du jour, poids figé, pas de frais non répartis ; un avoir ne rend aucune marchandise négative | — | `api/importations.py:956-968,1033-1065` | `verificateur.py:110-128` (coût HT et TVA de chaque dossier) ; C28, C29, C35, C36 |
| I40 | Cours d'une devise > 0 ; MAD = 1 | CK `devise_taux_check` | `api/comptes.py:439-440` | C11 (garanti) |
| I41 | Rôle d'un utilisateur ∈ 3 valeurs ; on ne retire pas ses propres droits de direction | CK `utilisateur_role_check` | `api/comptes.py:199-200` | — |
| I42 | **Une seule migration, une seule boucle de tâches à la fois** ; cache du moteur jamais périmé | — | verrous 7426101 / 7426102 ; signature (jour, max journal.id, max mouvement.id, max parametre.modifie_le, nb de mouvements, Σ soldes) (`depot.py:673-683`) | — |

Contrôles que le code déclare « garantis par la base » (`calcul/controles.py:176-183`) : C09 (prix
≥ 0), C10 (délai > 0), C11 (cours > 0), C16 (FK des mouvements), C21 (devise d'un prix = FK).

---

## 13. Glossaire des notions

| Notion | Définition (dans Gestion MP) |
|---|---|
| **Article / matière** | Un fil ou un intrant (colle, plastique, cuir…), désigné par sa **référence** lisible. Stock en kg. |
| **Rôle (de nomenclature)** | La place d'une matière dans le tapis : Poil, Chaîne, Trame, Colle, Cuir, Franges, Ruban, Plastique. **Linéaire** : Cuir, Franges, Ruban (recette en ml/m²). |
| **Densité** | kg par mètre linéaire d'une matière ; convertit ml ↔ kg (aussi : `metier.densite` = bobines par mètre de laize, autre notion). |
| **Qualité** | Un modèle de tapis : poids de chaque rôle au m², recette, plan mensuel, saisonnalité. |
| **Recette / nomenclature** | Pour une qualité, la part (%) de chaque article dans son rôle. |
| **Version de recette** | Photo datée et signée de la recette et des poids d'une qualité, prise à chaque enregistrement. |
| **Plan** | `base_mensuelle` (m²/mois) × coefficient du mois (saisonnalité), avec croissance annuelle ; versionné au journal. |
| **Lot** | Un numéro (du fournisseur, ou `LOT-AAAA-NNNN` interne) qui identifie une matière reçue ; porte sa date d'entrée et le poids mesuré d'une bobine. |
| **Magasin** | Lieu de stockage : « Stock courant » ou « Quarantaine ». |
| **Quarantaine** | Magasin où la matière reçue « sous réserve » attend une décision : en stock, valorisée, mais non disponible et hors du calcul des achats ; on en sort par libération (transfert) ou retour au fournisseur. |
| **Solde** | Ce qu'un lot détient dans un magasin (kg) : cache du journal, jamais négatif. |
| **Mouvement** | Une écriture du journal du stock : lot, magasin, quantité signée, date d'effet, type, document. |
| **Document / document_id** | Le document qui a écrit un mouvement (`reception`, `sortie`, `operation`, `inventaire`) et son id. |
| **Contre-passation** | Annulation d'un document validé par l'écriture de l'inverse de chacune de ses lignes, à la même date ; `contrepasse_id` pointe l'original ; une seule fois. |
| **Paire** | Lien entre les deux lignes d'un transfert. |
| **Cours figé** | Le cours de la devise enregistré sur un mouvement (ou un bon, une ligne de dossier) au moment du fait : changer le cours demain ne réécrit pas hier. |
| **CMUP / coût moyen** | Coût unitaire moyen pondéré par matière, recalculé par le moteur en rejouant le journal. |
| **Coût de revient** | Prix d'achat converti en MAD + frais non récupérables du dossier d'importation, par kg. |
| **Bon de commande (BC)** | Commande au fournisseur ; « parti » dès qu'il a un numéro. |
| **Version partie** | Les lignes et le montant de référence du bon tel que le fournisseur l'a (`version_approuvee`). |
| **Montant approuvé** | Montant MAD pour lequel le bon est parti (approuvé ou sous le seuil) ; référence de toute hausse. |
| **Date promise / ETA** | Date de livraison convenue (ponctualité) / date d'arrivée annoncée (prévision, retard). |
| **Jalon** | Étape d'expédition datée : proforma, acompte, embarquement, ETA, port, dédouanement, arrivée usine. |
| **Soldé** | Bon qui n'attend plus rien : tout reçu (automatique) ou décidé à la main. |
| **Reçu net** | Pesées validées d'une ligne de bon moins les retours au fournisseur de ses lots. |
| **Réception** | Arrivée d'un camion (BL) : lignes pesées, lots, magasin, qualité (conforme / réserve / refusé). |
| **Lot interne** | Lot numéroté par l'usine quand l'étiquette n'en porte pas (`LOT INTERNE` → `LOT-AAAA-NNNN`). |
| **Facture** | Facture du fournisseur ; partagée par ses réceptions ; un dossier au plus ; échéance et règlement. |
| **Ordre de fabrication (OF) / bon de sortie** | Ce qu'on tisse (m² par qualité) et les fils sortis vers les machines, lot par lot. |
| **Bon de fabrication** | Une ligne « qualité × m² » d'un ordre. |
| **Prévu (théorique)** | Ce que la recette demandait pour un ordre, figé à sa validation. |
| **Fil monté** | Fil installé sur un étage d'un métier, pas encore tissé : compte dans le stock global et sa valeur. |
| **Métier, étage, laize** | Métier à tisser ; ses étages ; la largeur d'un étage (m). |
| **Opération** | Geste de stock documenté : ouverture, retour machine, transfert (dont quarantaine/libération), ajustement, retour fournisseur. |
| **Motif R1–R6** | Codes de motif de retour hérités de l'ERP Fil (§ 6.5). |
| **Inventaire (tournant)** | Comptage d'une partie du stock ; théorique figé à l'ouverture ; ajustements à la validation. |
| **Dossier d'importation** | Une facture importée, sa marchandise et ses frais ; donne le coût de revient. |
| **Charge / frais** | Une pièce de frais du dossier (MAD), sur tout le dossier ou une marchandise. |
| **Clé de répartition** | `valeur` ou `poids` : comment un frais global se répartit. |
| **Part (figée)** | Montant d'un frais attribué à une marchandise, gardé quand la clé change sur un dossier clos. |
| **Récupérable** | Frais (TVA) qui ne coûte pas : hors du coût de revient. |
| **Code douanier** | Position tarifaire et taux de droits, pour les droits attendus. |
| **Période close** | Tout ce qui est daté jusqu'à `date_cloture` est figé (stock et coût). |
| **Réclamation** | Litige avec un fournisseur sur une livraison, jusqu'à son issue. |
| **Signalement (besoin signalé)** | Message de l'atelier aux achats, traité ou non. |
| **Pièce jointe** | Fichier attaché à un document. |
| **Indicateur du jour** | Photo quotidienne des grands chiffres du cockpit. |
| **Contrôles C01–C38** | Vérifications d'intégrité et de cohérence calculées par le moteur (`calcul/controles.py`). |
| **Vérificateur** | Programme qui recompte en SQL direct ce que montrent les écrans. |
| **Journal (d'audit)** | Trace de chaque geste ; aussi support de certaines données (§ 9). |
| **Poussière** | Seuil de 1 g (`POUSSIERE = 1e-3`) en dessous duquel une quantité est nulle. |

---

## 14. Points incohérents ou ambigus

1. **Numérotation des étapes trouée (1–9, 11, 13, 14 ; ni 10 ni 12).** Jamais présentes dans
   l'historique ; probable réservation par équipe parallèle (§ 4.3). `MAX(numero)` = 14 ≠ 12
   étapes. Le libellé du commit 93fd464 « l'étape 11 se range avant la 13 » ne parle que de l'ordre.
2. **Une base neuve et une base migrée diffèrent** : `commande.version_approuvee` sans défaut
   serveur (neuve) / `DEFAULT ''` (migrée) ; `dossier.facture_id` contrainte UNIQUE (neuve) /
   index unique (migrée) ; défauts `'0'` / `0` ; ordre des colonnes (`article.unite_prix` en fin).
   L'étape 1 crée les tables **dans leur forme actuelle**, les étapes 5 et 13 aussi.
3. **Des migrations appellent le code applicatif vivant** (étape 8 `recaler_soldes`, étape 11
   `figer_version`, `taux_des_devises`) : rejouées sur une vieille base avec un code futur, elles
   ne feraient pas la même chose. Contraire à « on n'édite jamais une étape livrée ».
4. **Aucun `Numeric`** : quantités, prix, montants MAD, cours, taux en `double precision`. D'où
   des tolérances partout (1e-9, 1e-6, 1 g, 0,005 MAD, 1 MAD).
5. **Deux seuils de négativité** : CHECK `quantite >= -0.0005` en base, `POUSSIERE = 1e-3` dans le
   code, `< -0.0005` dans le vérificateur.
6. **`article_id` redondant** sur `mouvement`, `bon_ligne`, `operation_ligne`, `reception_ligne`,
   `dossier_ligne` sans contrainte d'égalité avec `lot.article_id`.
7. **Devise tantôt FK, tantôt texte** : FK sur `fournisseur`, `article`, `commande`, `facture` ;
   simple `VARCHAR(3)` sur `mouvement`, `reception_ligne`, `operation_ligne`, `dossier_ligne`,
   `reclamation`.
8. **Trois sens de « cours = 0 »** : `commande.cours` = pas encore figé ; `dossier_ligne.cours` =
   « lire le cours de la devise » ; `mouvement.cours` = MAD, prix nul ou cours inconnu.
9. **Statuts au genre variable** : `validee`/`annulee` (réception, opération) contre `valide`/`annule`
   (ordre) et `valide` (inventaire) ; `clos` (dossier) contre `close` (réclamation).
10. **`a_approuver` a deux sens** selon que `numero` est NULL (brouillon soumis) ou non (bon parti
    dont une hausse attend). `statut_moteur` gère aussi un `brouillon` numéroté, état que le code
    ne produit pas. Pas d'état « approuvée ».
11. **Numéros donnés à l'ouverture** pour `inventaire` (INV), `dossier` (DOS), `reclamation` (RCL) :
    l'abandon d'un inventaire ou la suppression d'un dossier ouvert laisse un **trou**, contraire
    à l'esprit de M65.
12. **`dossier.numero` en `NN/AA`** : format différent de toutes les autres séries ; un numéro
    saisi à la main peut être n'importe quoi (16 car.) ; au-delà de 99 dossiers, `100/26`.
13. **`dossier_ligne.poids_kg` est devenu une copie de `quantite`** (étape 14, propriété `kilos`,
    vérificateur qui lit `quantite`) : colonne morte.
14. **`article.unite` ne peut valoir que `'kg'`** : colonne constante gardée pour compatibilité.
15. **`lot.commentaire` n'est jamais écrit ni lu** par l'API. `mouvement.date_saisie` n'est
    qu'affichée.
16. **`reception.controle_par` (qui a contrôlé au quai) n'est pas lu par le moteur** :
    `depot.py:396` passe `controleur_qualite = r.validee_par`.
17. **Le journal sert de base de données** (§ 9) : plan versionné en JSON dans `detail`
    (tronqué à 2 000 car.), « soldé à la main » déduit d'un suffixe de texte (« tout reçu »),
    motifs de renvoi et d'annulation. Fragile (texte libre, traductions).
18. **Liens par texte** : `recette_version.contenu` et `bon_sortie.theorique` désignent les
    articles par leur **référence**, qui peut être renommée (`api/referentiels.py:640-646`) ; tous
    les `*_par`/`auteur`/`journal.utilisateur` désignent l'utilisateur par son **nom** (modifiable).
19. **Références polymorphes sans FK** : `mouvement.document/document_id`, `journal.objet/objet_id`,
    `piece_jointe.objet/objet_id`, `mouvement.paire` ; valeurs sans CHECK : `mouvement.document`,
    `piece_jointe.objet`, `poste_frais.cle`, `signalement.urgence`, `reclamation.motif/issue`.
20. **CHECK absents** : `dossier_charge.montant` (avoir négatif voulu, mais sans borne) ;
    `reception_ligne.prix`, `quantite_attendue`, `nb_bobines` ; `fil_monte.etage ≤ metier.etages` ;
    `reception_ligne.magasin_id` non nul hors refus ; somme des recettes à 100 % ; rôle linéaire ⇒
    densité > 0.
21. **Longueurs d'API incohérentes avec la base** : `ValeurClassification.code` accepte 64 car.
    (`api/referentiels.py:185`) alors que `composition.code`/`type_fil.code` font 32 et
    `titrage.code` 48 → erreur base (500) au lieu d'un refus clair.
22. **`role_nomenclature` sans `ON UPDATE CASCADE`** (contrairement aux autres classifications) :
    renommer un rôle = supprimer puis recréer, seulement s'il n'est pas utilisé.
23. **Sessions expirées et tentatives jamais purgées** ; `utilisateur` jamais supprimé, donc
    l'`ON DELETE CASCADE` de `session_ouverte` ne sert pas.
24. **Pièce jointe retirée = fichier gardé** sur disque sans ligne en base (voulu, mais orphelins).
25. **`lot.poids_bobine` écrasé** par chaque nouvelle réception du même lot ; `lot.fournisseur_id`
    = premier fournisseur connu.
26. **`fil_monte.metres` et `metier.densite`** : « densité » désigne ici des bobines par mètre de
    laize, à ne pas confondre avec `article.densite` (kg/ml).
27. **Étape 14 : un article `ml` sans densité** passe à `kg` **sans conversion** de ses quantités ;
    le prix catalogue d'un article au mètre est gardé tel quel mais lu au kilo (à corriger à la main).
28. **Colonnes sans défaut serveur** (défaut Python seulement) : `utilisateur.cree_le`,
    `tentative.echecs`, `journal.quand/detail`, `parametre.valeur/modifie_le`,
    `parametre_historique.quand`, `compteur.dernier`, `role_nomenclature.lineaire/ordre`,
    `fournisseur.devise/notes`, `article.devise/version`, `metier.etages`, `fil_monte.etage`,
    `poste_frais.recuperable/ordre`, `mouvement.date_saisie`, `commande.observations/cree_le/
    version_approuvee`, `commande_ligne.prix_confirme`, `facture.devise`,
    `reception.observations/cree_le`, `bon_sortie.cree_le`, `operation.cree_le`,
    `dossier.commentaire`, `reclamation.description/reponse`, `signalement.quand`,
    `piece_jointe.taille/quand`, `recette_version.quand/contenu`, `indicateur_jour.contenu`.
29. **`dossier.clos_le` est un horodatage** alors que `reclamation.close_le` est une date.
30. **Doc trompeuse** : l'en-tête de `modeles.py` cite « libération » comme opération (c'est un
    transfert avec motif) ; le moteur connaît un type `QUARANTAINE` que la base refuse ; le
    commentaire de `contrepasser_document` (« Les entrées d'abord en dernier ») est confus — le tri
    traite d'abord l'inverse des **sorties** (ré-entrées), puis celui des entrées.
31. **R3 sert deux motifs** (Non-conformité qualité, Refus après quarantaine).
32. **`outils/vider_activite.py` est obsolète** : sa liste `ACTIVITE` ignore `dossier_charge_part`,
    `reclamation`, `signalement`, `piece_jointe`, `recette_version`, `indicateur_jour` ; un
    `TRUNCATE` de `dossier_charge`, `reception` ou `lot` alors que `dossier_charge_part` /
    `reclamation` les référencent devrait être refusé par PostgreSQL (pas de `CASCADE`).
33. **`compteur` LOT rattrapé par un `LIKE 'LOT-AAAA-%'`** sur les lots : un numéro fournisseur qui
    ressemblerait à `LOT-2026-9999` décalerait la série interne.
34. **Indices manquants pour les lectures fréquentes** : rien sur `mouvement(lot_id, magasin_id,
    date_effet)` (lu par `couvert_a_sa_date` sous verrou), `mouvement.ordre_id`,
    `mouvement.contrepasse_id` hors UQ, `reception_ligne.commande_ligne_id`, `journal(objet,
    objet_id, action)` alors que le journal est relu comme donnée.
35. **`fournisseur.delai_jours`, `couverture_commande_jours`, `delai_paiement_jours` en FLOAT**
    (des jours) ; arrondis par `int()` / `FLOOR` selon les endroits.
36. **`bon_fabrication` sans unicité (bon, qualité)** : une qualité peut apparaître deux fois dans
    un ordre (les m² s'additionnent dans `theorique_fige`).
37. **Le vérificateur écrit en base** : il crée et (dés)active un compte `verificateur` de
    direction (`verificateur.py:335-351`).
