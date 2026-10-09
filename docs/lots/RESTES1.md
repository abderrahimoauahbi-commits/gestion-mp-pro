# Lot RESTES1 — première série de restes : ce que les lots suivants doivent savoir

Branche `lot-RESTES1`. Lignes traitées retirées de `docs/lots/RESTES.md`.

## 1. Révision 0004 (`0004_versions_et_genres`)

- `role_nomenclature.version` (défaut 1, `AvecVersion`) : la route 59 **exige** `version`
  (422 sans elle) et la contrôle (409 `conflit_version` « Ce rôle a été modifié entre-temps par
  … ») ; `RoleFiche` rend `version`. **F7** : envoyer la `version` lue avec la classification.
- `OrigineCours.periode_close` : le cours figé par la clôture d'une période (et celui gardé au
  changement d'un cours, E-02) ; le commentaire de la marchandise n'est plus touché.
  `devises.figer_cours_periode_close(...)` n'a plus de paramètre `geste` (**D7**).
- `GenreSauvegarde.avant_vidage`, `avant_mise_a_jour` : le registre les inscrit
  (`sauvegarde_registre.GENRES_DU_REGISTRE` = tous les genres du disque) ; jamais purgées ;
  `outils/vider_activite.py` sauvegarde d'abord en `avant_vidage`. **X2** : `sauvegarder(
  "avant-mise-a-jour")` avant une mise à jour.
- Retour arrière : `periode_close` → `saisi`, lignes du registre des deux genres retirées
  (fichiers gardés), CHECK remis, colonne retirée. 685 colonnes.

## 2. Essais

- `tests/conftest.py` : `GESTIONMPPRO_SAUVEGARDES` et `GESTIONMPPRO_PIECES` dans un dossier
  temporaire de séance (`DOSSIER_DES_ESSAIS`, effacé à la fin), `GESTIONMPPRO_SAUVEGARDES_COPIE`
  retirée. Un essai qui veut ses dossiers les pose encore lui-même (`fabriques.exploitation`).
- `tests/fabriques/serveur_jetable.py` : la base jetable s'appelle `<base d'essai>_jetable_essai`
  (avant : `gestion_mp_pro_d10_jetable_essai`, commune à tous les lots — deux lots qui jouaient
  leurs essais en même temps se la disputaient : `createdb` en échec).
- `tests/test_catalogue_api.py` : l'OpenAPI servi contre API-PRO § 1 (méthode, chemin, rôles,
  `summary`, une étiquette, réponse de succès décrite, 401/403 déclarés) ; les routes du
  catalogue pas encore servies sont listées par lot (lecture de LOTS-DE-TRAVAIL) dans un
  **saut** (`pytest -rs`) jusqu'à ce que `docs/RECETTE.md` existe, en échec ensuite. À la date
  du lot : 106 attendues (C1, D4, D5, D6, D7, D8).

## 3. Comportements changés

- `/acces` (route 5) : adresse réseau et nom de la machine au schéma et au port **de la
  requête** (`appareils.adresse_de`, déplacée de `services/serveur.py` qui la réexporte) :
  derrière HTTPS, `https://<ip>` sans « :8050 » (G-13).
- Désactiver un compte **expire** ses sessions (gardées jusqu'à la purge, 7 jours) au lieu de
  les effacer : la requête suivante reçoit 401 `compte_inactif` « Ce compte n'est plus actif. »
  (H-09) ; l'écran le lisait déjà (`lib/session.tsx`, `motifLisible`). Réactivé, le compte doit
  se reconnecter (la session ne revit pas). Changement de rôle ou de code : sessions effacées
  comme avant.
- Étiquettes (route 114) : kilos à la règle § 9.3 des documents (`documents.format.kg`, une
  décimale, espaces insécables), mètres « ≈ 1 021 ml », et « ≈ N bobines » (poids du lot, sinon
  du catalogue ; rien sans poids ni sous une demi-bobine). `conversions.kg_et_metres` supprimée
  (plus employée).
- Cache du moteur : la signature compte aussi `Σ parametre.version` et `Σ devise.version` ; un
  réglage ou un cours changé à horloge figée se voit. `fabriques/achats.reglage` et `cours`
  n'appellent plus `donnees_moteur.invalider()` (les autres invalidations de D3, matières
  écrites sans journal, restent nécessaires).
- `make notice` : régénère docs/NOTICE.md.

## 4. Documents de conception

API-PRO (§ 1.1–1.5, 1.7–1.9, 1.12), ARCHITECTURE (§ 3, 5.1, 7, 13.3), ECRANS-PRO (E16, 4.29,
4.30, 4.11, P7), MODELE-DONNEES (§ 2, 3.2.3, 3.10.1, 9, 10, 11) : écarts des lots S2, S4, D1,
D9, D10, R1 reportés.

## 5. Ce qui reste

- `frontend/src/lib/types.gen.ts` n'est pas régénéré (`RoleFiche.version`,
  `RoleModification.version` obligatoire) : **F7/F8** lancent `make types`.
- Lignes de RESTES.md déjà faites par leur destinataire mais pas retirées (pas dans ce lot) :
  S4 → D9 (route 114 branchée par D9), D1 → D9 (classeurs par `exports/classeur.py`), R1 → D10
  (`reprise/sauvegarde.py` passe par le service de D10).
