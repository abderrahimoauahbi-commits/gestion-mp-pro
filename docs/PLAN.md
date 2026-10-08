# Gestion MP PRO — plan de réalisation

Demande de Mohamed (8 octobre 2026) : « Mon informaticien a vu ton ERP et m'a dit qu'il ne
faisait pas professionnel. Conçois une version Pro complète, Gestion MP PRO, dans le dossier
Mohamed. Tiens compte du travail déjà fait dans Gestion MP. N'oublie rien, sois précis, ne me
demande rien jusqu'à la livraison. N'oublie aucune notion, et fais des tests à la fin pour
vérifier les résultats, la structure, la justesse des calculs. »

## Ce que « Pro » veut dire ici

Le standard est celui de **GMAO PRO** (`~/gmao-pro`, même usine, même famille), que le
service informatique connaît :

| Domaine | Exigence |
|---|---|
| Code serveur | Paquet Python installable (`pyproject.toml`), couches nettes : `api/` (routes minces), `services/` (logique métier sans HTTP, dont le moteur de calcul découpé par domaine), `modeles.py`, `securite.py`, `db.py` (migrations numérotées), `config.py` (environnement `GESTIONMPPRO_*`). Typage, ruff, docstrings. |
| Code écran | React + TypeScript strict + Vite ; système de composants (`DataTable` : recherche sans accents, filtres, tri numérique et naturel, pagination, export ; `Form` : bouton qui dit ce qui manque, sélecteur au clavier ; `Layout` : en-tête avec fil d'Ariane, cartes, fenêtres, tiroirs, onglets, confirmations ; `Feedback` : KPI avec formule, badges ; `Charts` SVG) ; coque avec barre latérale par rôle, recherche globale, notifications, menu du compte ; prettier, eslint, tsc strict, vitest. |
| Données | PostgreSQL 16, contraintes d'intégrité, verrous de ligne, champ `version` contre les modifications simultanées, journal d'audit (avant/après), historique par fiche. |
| Droits | Le serveur décide (`droit(...)` par route), filtre des prix générique (`sans_prix`) à toute profondeur, l'écran n'affiche que ce que le serveur acceptera. |
| Documents | Bon de commande (anglais), étiquettes QR, bilan du mois, fiches imprimables : A4, papier à en-tête de l'usine. |
| Exploitation | Docker Compose + Caddy (HTTPS) + systemd, ou poste Mac (démarrage automatique) ; sauvegarde quotidienne relue + copie externe ; `/api/sante` (version, schéma, sauvegarde) ; journal du serveur. |
| Documentation | README, CAHIER-DES-CHARGES, NOTICE (une source : `frontend/src/aide.json`), ARCHITECTURE, EXPLOITATION, RECETTE ; OpenAPI sur `/api/docs`. |
| Vérification | pytest (processus, droits, prix masqués, calculs, migrations, concurrence), vitest, vérification indépendante des chiffres, scénario de bout en bout, recette navigateur par rôle, épreuve de charge, **parité de calcul avec Gestion MP** sur l'année d'essai. |

## Ce qui ne change pas : le métier de Gestion MP

Tout ce que Gestion MP sait faire et toutes les décisions de Mohamed sont repris — l'inventaire
exhaustif est dans `docs/heritage/`. Rappel des décisions structurantes :

- Trois rôles métier : direction (tout), achats, alimentation des machines (téléphone, sans
  aucun prix) ; GMAO PRO ajoute un administrateur technique — repris ici.
- Stock en **kg** pour toutes les matières ; prix au kg ou au mètre (densité) ; recettes des
  rôles au mètre (cuir, franges, ruban) en ml/m² ; mètres indicatifs.
- Stock **en magasin ou en machine** (fil monté), les deux comptés et valorisés ; la
  **quarantaine** est en stock, à part, sans compter pour les achats.
- **Un dossier d'importation = une facture = une livraison**.
- Coût moyen pondéré, cours figé sur chaque mouvement, période close figée, écritures
  antidatées refusées, annulation par contre-passation.
- Bon de commande fournisseur : A4, **en anglais**, **sans prix**, papier à en-tête.
- Approbation de la direction au-delà d'un seuil, au montant approuvé et au cours figé.
- Le passé (coefficient de réalisation, prévu des ordres) jugé sur le plan et les recettes de
  son époque.

## Ports, bases, dossiers

| | Gestion MP PRO | Gestion MP (inchangé) | GMAO PRO | GMAO |
|---|---|---|---|---|
| Port | **8050** (écran de développement 5196) | 8030 | 8040 | 8020 |
| Base | `gestion_mp_pro` (essais : `gestion_mp_pro_essai`) | `gestion_mp` | `gmao_pro` | `gmao` |

Jamais touchés : `~/erp-fil`, `~/gestion-mp` et sa base, `~/gmao*`.

## Étapes

1. Inventaire exhaustif de Gestion MP (données, règles, calculs, contrôles, réglages, écrans,
   décisions) → `docs/heritage/`.
2. Serveur : fondations (schéma consolidé, sécurité, migrations), puis domaines.
3. Écran : système de composants et coque, puis écrans par domaine.
4. Reprise : référentiels réels depuis la base de Gestion MP ; année d'essai pour la parité.
5. Exploitation : déploiement, sauvegardes, raccourci « Gestion MP PRO ».
6. Vérification : essais, parité, chiffres, scénario, recette navigateur, charge, audit
   indépendant ; corrections.
7. Documentation et livraison.
