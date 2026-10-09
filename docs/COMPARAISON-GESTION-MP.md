# Gestion MP PRO comparé à Gestion MP

*Pour Mohamed et son informaticien.* Ce document montre que **Gestion MP PRO dit les mêmes
chiffres que Gestion MP**, explique chaque différence voulue entre les deux versions, et dit
comment le vérifier soi-même. Il s'appuie sur un outil de comparaison qui interroge les deux
logiciels, chiffre par chiffre, à plusieurs dates (`outils/comparer_avec_gestion_mp.py`).

Tant que PRO n'est pas mis en service, sa base est un **miroir** de celle de Gestion MP :
Gestion MP reste le logiciel qui travaille, PRO recopie ses données (reprise) pour qu'on
puisse comparer les deux sur les **mêmes** données.

---

## 1. Les chiffres sont identiques — ce qui a été prouvé

La comparaison a été jouée sur les deux bases de Gestion MP, telle une photo de chacune :

| Base comparée | Dates | Valeurs comparées | Différences voulues | **À corriger** |
|---|---|---:|---:|---:|
| **Production** `gestion_mp` (référentiels réels : 124 matières, 18 qualités, 319 recettes, sa commande réelle) | aujourd'hui + 12 fins de mois | **292 359** | 0 | **0** |
| **Année d'essai** `gestion_mp_comparaison` (import de l'ERP Fil : 10 438 mouvements, 317 réceptions, 320 ordres) | aujourd'hui + 12 fins de mois | **2 151 240** | 114 926 | **0** |

À quoi s'ajoute la parité de calcul de fond (lot R2), rejouée sur l'année d'essai à 19 dates,
par l'écran (155 paires de routes) et geste par geste (un mois d'usine joué dans les deux
logiciels) : **à corriger 0**, 188 579 différences toutes expliquées.

Chaque nombre de l'état du stock (par magasin, sur les métiers, en quarantaine), de la
valorisation (CMUP, valeurs), des besoins, du plan d'achat, des contrôles, du cockpit, du coût
de revient des dossiers, des commandes et de l'échéancier a été comparé à celui de Gestion MP.
« À corriger : 0 » veut dire : **aucune différence qui ne soit pas voulue et prouvée**.

Les rapports datés sont dans `backend/essais/` :
`resultat-comparaison-production-2026-10-08.md`, `resultat-comparaison-essai-2026-10-08.md`
(moteurs) et `resultat-comparaison-essai-api-2026-10-08.md` (par les écrans). Versions
comparées : Gestion MP `c1133ba`/`d10180e`, Gestion MP PRO `0.1.0`.

Pendant toute la comparaison, l'empreinte de `gestion_mp` et de `gestion_mp_comparaison` est
relevée avant et après : **inchangée**. Rien n'est jamais écrit dans les bases de Gestion MP
(lecture seule vérifiée), ni dans ses dossiers.

---

## 2. Les différences voulues, en une phrase chacune

Une différence n'est « voulue » que si une règle de l'outil **recalcule** son ampleur à partir
de la source : sinon, elle serait « à corriger ». Voici toutes celles qui existent.

### 2.1 Reprise des données (une seule fois, à la mise en service)

| Code | Ce que PRO fait | Pourquoi |
|---|---|---|
| **K8a** | Le prix des sorties, transferts et retours machine n'est pas repris (mis à 0). | Ces mouvements sont valorisés au coût moyen ; leur prix d'origine ne sert à rien et n'était pas fiable (8 747 lignes sur l'année d'essai). |
| **K8b** | Une réception payée en **deux devises** est **scindée** en une réception par devise (chaque ligne garde sa devise). | Une réception n'a qu'une devise dans PRO ; le découpage garde les identifiants et les quantités, et les stocks et valeurs en dirhams sont inchangés (4 réceptions → 8). |
| **K8c** | Une unité d'achat sans contenance (« Palette ») est lue au kilo. | Gestion MP déduisait déjà la palette du catalogue : même stock. |
| **K8d** | Un brouillon qui portait un numéro le perd (le numéro est gardé pour n'être jamais redonné). | Dans PRO, un brouillon n'a pas de numéro tant qu'il n'est pas validé. |
| **K8e** | Un ordre validé sans heure prend la fin de son jour (23:59:59). | C'est l'instant que le moteur de Gestion MP prenait déjà à défaut : même recette en vigueur. |
| **K8f** | Un numéro de lot contenant des espaces voit ses espaces remplacés par « _ ». | La base interdit les espaces dans un numéro de lot ; écart de libellé seulement. |
| **K8g** | Une entrée de réception sans document retrouvé est rattachée à sa réception par (lot, date). | Rétablit le lien que l'ERP Fil ne portait pas, sans changer aucun chiffre. |
| **K8h** | Un prix confirmé sans date prend la date de création du bon. | Date manquante à l'import ; sans effet sur les calculs. |
| **K8i** | Une entrée en devise sans cours prend le cours du jour de la reprise. | Ainsi un changement de cours ne revalorise plus un mois déjà clos (1 101 entrées). |

### 2.2 Choix de métier (décisions tranchées pour PRO)

| Code | Ce que PRO fait | Pourquoi |
|---|---|---|
| **K1** | Les valeurs sont arrondies à l'échelle de leur colonne (3 décimales pour les kg, 2 pour les montants). | La base range les nombres proprement ; les écarts sont ≤ 0,001 kg ou 0,01 MAD par valeur. |
| **K2** | Un inventaire ne suspend que **son périmètre**, pas tout le magasin. | Pratique d'usine demandée par la direction : on peut sortir une autre matière pendant un inventaire. |
| **K3** | Un inventaire abandonné (ou un dossier annulé) garde ses lignes, hors des calculs. | Pour garder la trace ; Gestion MP effaçait les lignes. |
| **K4** | Une réception entièrement refusée peut être **annulée**. | Gestion MP la bloquait (depuis corrigé : même comportement). |
| **K7** | Le fil monté sur les métiers est compté comme du stock **à toute date**. | Décision de Mohamed : le fil monté est du stock. Gestion MP ne le comptait qu'au jour même (+445,5 kg à une date passée côté PRO). |
| **K9** | Vu à une date passée, les opportunités du cockpit ne lisent que les achats reçus **jusqu'à cette date**. | Sinon on comparait des prix pas encore connus ce jour-là. Gestion MP a été corrigé de même (`d10180e`). |

### 2.3 Forme des réponses (même valeur, autre écriture)

- Les statuts du stock sont rendus en **codes** (`RUPTURE`, `CRITIQUE`… ; `CREER_BC`/`AUCUNE`)
  au lieu des libellés à émoji (« 🔴 CRITIQUE », « 📝 Créer BC - … ») : l'écran les retraduit,
  les classeurs les écrivent en clair.
- Les instants portent le fuseau (ISO 8601) ; « rien » est `null` au lieu de `0` ou `""` ; les
  personnes de la reprise (« ERP Fil », « système ») ne désignent personne.
- Chaque ligne de stock porte en plus `role_id`, `fournisseur_id` ; la traçabilité porte les
  identifiants des objets liés (pour les liens de l'écran). Ce sont des **ajouts**, jamais des
  valeurs changées.

> `controle_par` lu comme contrôleur (K5) et l'alimentation sans réglages ni cours (K6) sont
> sans effet sur les chiffres (`controle_par` est vide dans toute l'année ; l'alimentation ne
> voit aucun prix). Le « mode classeur » de calcul de Gestion MP (P17) n'est pas repris : il
> ne changeait aucune sortie.

---

## 3. Les différences entre les deux logiciels, et leur raison

### 3.1 Écran

| Sujet | Gestion MP | Gestion MP PRO | Raison |
|---|---|---|---|
| Vocabulaire | mélange français/anglais, émojis dans les statuts | un seul vocabulaire métier français, émojis seulement à l'affichage | un mot = une notion, de la base à l'écran |
| Adresses | — | chaque écran a une adresse stable (onglet, filtre dans l'URL) | revenir, partager, mettre en favori |
| Bon fournisseur | doublon français avec prix | un seul bon, en anglais jusqu'à l'en-tête | A22 |
| Prix du catalogue à confirmer | case ambiguë | case « Envoyer avec nos prix du catalogue, à confirmer » rendue effective | exigence de Mohamed (E3) |
| Aide et notice | 595 lignes dans le code | une seule source (`aide.json`), notice générée | A7 |

### 3.2 Structure (sous le capot)

| Sujet | Gestion MP | Gestion MP PRO | Raison |
|---|---|---|---|
| Couches | moteur de 3 760 lignes, routes de 95 lignes | trois couches strictes (HTTP / règles / calcul pur), fonctions ≤ 60 lignes | testable, lisible |
| Nombres | `float` en base | valeurs en **`NUMERIC`** (le moteur calcule toujours en `float`, comme Gestion MP) | parité prouvée, rangement propre |
| Tables / colonnes | 49 tables, 405 colonnes | **71 tables, 686 colonnes** ; 0 donnée métier cachée dans du texte ou du JSON | fin des 17 fragilités relevées |
| Migrations | étapes trouées, dépendantes du code | **Alembic**, révisions linéaires contiguës, migration propre | mises à jour sûres |
| Contraintes | 39 CHECK, 73 clés étrangères | **291 CHECK, 171 clés étrangères, 41 unicités, 3 déclencheurs** (dont un stock immuable) | la base refuse elle-même l'incohérent |
| Journal des changements | partiel | avant/après systématique (qui, quoi, quand) | traçabilité |
| Modifications simultanées | empreinte fragile | un numéro de `version` par fiche : 409 si deux postes modifient en même temps | plus de perte silencieuse |

### 3.3 Sécurité

| Sujet | Gestion MP | Gestion MP PRO | Raison |
|---|---|---|---|
| Prix masqués | filtrés à la main (20 endroits : un oubli = une fuite) | **filtre unique et générique** à toute profondeur ; essai « aucun prix pour l'alimentation » | une fuite de moins |
| Rôles | 3 rôles | **4 rôles** : direction, achats, alimentation, et un **administrateur technique sans aucune donnée métier** | l'informatique n'a pas à lire les prix |
| Droits | contrôle épars | `droit(...)` sur **chaque** route ; matrice générée et testée route par route | le serveur décide, pas l'écran |
| Connexions | exposées | liste des visages réservée au poste local ; déconnexion et changement de code protégés | exposition réseau fermée |
| Sessions | — | changer un code ferme les autres sessions ; sessions suivies | vol de session |

### 3.4 Exploitation

| Sujet | Gestion MP | Gestion MP PRO | Raison |
|---|---|---|---|
| Sauvegardes | simples | sauvegardes **relues** (vérifiées), avec les pièces jointes, jamais purgées pour les « avant » | une sauvegarde qu'on ne peut pas relire ne sert à rien |
| Restauration | risquée | **réversible** (sauvegarde « avant restauration »), tout ou rien, migrée, les autres postes prévenus | revenir en arrière sans peur |
| Coexistence | — | PRO tourne **à côté** de Gestion MP sur le même Mac, sans rien partager (dossiers, port, base, cookies distincts) | comparer les deux sans risque |
| Santé | — | `/api/sante` public, surveillance | savoir si le serveur va bien |
| Journaux | 14 `print` | journal structuré, une ligne par requête | diagnostiquer |

### 3.5 Vérification

| Sujet | Gestion MP | Gestion MP PRO | Raison |
|---|---|---|---|
| Essais | deux audits | **plus de 2 600 essais** automatiques, verts avant chaque changement | ne rien casser |
| Parité | — | parité prouvée sur l'année d'essai (19 dates, par les écrans, geste par geste) : **0 écart à corriger** | PRO calcule comme Gestion MP |
| Vérification indépendante | — | les chiffres relus par un autre chemin (`/api/donnees/{table}`) | un chiffre vérifié deux fois |
| Scénario | — | un mois d'usine joué de bout en bout dans les deux logiciels | preuve de bout en bout |
| Comparateur | — | cet outil, rejouable quand on veut | se convaincre soi-même |

---

## 4. Comparer soi-même

Les deux logiciels tournent côte à côte sur le Mac (Gestion MP sur le port 8030, PRO sur 8050,
raccourcis distincts sur le bureau). Pour rafraîchir le miroir et comparer :

1. **Rafraîchir le miroir** (recopier Gestion MP dans PRO), au choix :
   - dans PRO : *Administration › Reprise › « Rafraîchir le miroir… »* (direction) ;
   - en ligne de commande, depuis `~/gestion-mp-pro` : `make miroir`.
   Une sauvegarde « avant reprise » de PRO est toujours faite d'abord.

2. **Comparer chiffre par chiffre** (sur des copies, sans toucher aux serveurs en service) :

   ```
   backend/.venv/bin/python outils/comparer_avec_gestion_mp.py \
       --source gestion_mp_comparaison --mode moteurs \
       --sortie backend/essais/resultat-comparaison-$(date +%F).md
   ```

   - `--source` : `gestion_mp` (la production) ou `gestion_mp_comparaison` (l'année d'essai) ;
   - `--mode moteurs` : les deux moteurs de calcul, sans serveur ; `--mode api` : deux serveurs
     lancés par l'outil, interrogés par leurs écrans (plus lent, plus complet) ;
   - `--dates`, `--sections` : restreindre si on veut ; `--resynchroniser` : relancer la reprise
     si les deux bases ont divergé.

   L'outil copie la base de Gestion MP (lecture seule), vérifie que PRO en est bien le miroir
   (même signature, sinon il refuse), compare, et écrit un rapport Markdown. Il rend « à
   corriger : 0 » quand tout concorde.

L'outil est lui-même mis à l'épreuve : son essai injecte quatre fautes dans PRO (un CMUP
gonflé, un contrôle muet, un stock décalé d'1 kg, un coût de revient faux) et vérifie qu'il
**les voit** — pour qu'un « 0 » signifie vraiment quelque chose.

---

## 5. Ce que Gestion MP fait encore que PRO ne fait pas — honnêtement

Gestion MP PRO **reprend tout le métier** de Gestion MP et y ajoute (l'administrateur
technique, les contraintes de base, les sauvegardes relues, la coexistence). Les seules
différences dans l'autre sens sont voulues :

- **Les défauts corrigés.** Là où Gestion MP se trompait, PRO ne reproduit pas l'erreur : il ne
  la « fait plus ». Exemples : l'inventaire qui bloquait tout le magasin (K2), les opportunités
  qui comparaient des prix futurs (K9, depuis corrigé aussi dans Gestion MP), les 500 sur une
  saisie. La liste complète est dans `docs/heritage/DEFAUTS-GESTION-MP.md`.
- **Le « mode classeur »** de calcul (un second mode de Gestion MP, jamais utilisé en service)
  n'est pas repris (P17) : il ne changeait aucune sortie.
- **La mise en service réelle** (vider l'année d'essai, reprendre la production définitive)
  reste à faire par l'informaticien **le jour de la livraison** ; d'ici là, PRO n'est qu'un
  miroir.

Quelques points de métier restent **ouverts pour Mohamed** : là où Gestion MP n'avait pas
tranché, PRO garde son comportement et le signale (il ne change rien en silence) — par exemple
les prix de la bande et du cuir, le rôle « Franges », la valorisation à la facture. Ces points
sont listés dans le rapport de reprise et dans `docs/heritage/DECISIONS.md`.

---

*Dernière vérification : 2026-10-08. Rapports dans `backend/essais/resultat-comparaison-*.md`.*
