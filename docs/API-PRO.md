# Gestion MP PRO — catalogue de l'API

Le catalogue des routes de Gestion MP PRO, domaine par domaine (méthode, chemin, rôles, schéma
d'entrée, schéma de sortie), puis la correspondance de **chacune** des 206 routes de Gestion MP
(`docs/heritage/API.md` : 97 routes de la partie A, notées A1…A97 ; 109 de la partie B, notées
B1…B109). Rien ne se perd : une route de Gestion MP sans successeur est déclarée « morte » avec
sa raison. Les règles et les messages de refus de chaque route sont ceux de `heritage/API.md` et
`heritage/REGLES.md`, sauf ce que la colonne « Changement » dit. L'OpenAPI servi sur `/api/docs`
est la forme exécutable de ce document ; l'essai `test_catalogue_api.py` compare les deux.

---

## 0. Conventions

### 0.1 Forme

- Préfixe `/api`, JSON UTF-8, dates ISO `AAAA-MM-JJ`, instants ISO avec décalage. Nombres :
  les `NUMERIC` sortent en **nombres JSON** (pas en chaînes), à l'échelle de leur colonne.
- Ressources au pluriel en français (`/matieres`, `/commandes`, `/ordres`) ; identifiant entier
  dans le chemin (`/commandes/12`) ; gestes métier = `POST` sur une sous-ressource verbale
  (`/commandes/12/envoyer`) ; modification = `PUT` (remplacement de ce que la fiche permet de
  modifier) ; `PATCH` n'est pas employé.
- Chaque route déclare `response_model`, `summary` (une phrase), `tags` (= domaine), et
  `responses` (codes de refus possibles). Schémas Pydantic dans `api/<domaine>/schemas.py` :
  entrée `<Objet>Creation`, `<Objet>Modification`, `<Geste>` ; sortie `<Objet>Fiche` (détail),
  `<Objet>Resume` (élément de liste), `<Objet>Liste`, `Page[T]`.
- Toute écriture d'une fiche ou d'un document **reçoit sa `version`** (lue avec la fiche) ; une
  version périmée → **409** `conflit_version` « Cette commande a été modifiée entre-temps par
  {nom} ({heure}) : rouvrez-la pour repartir de sa dernière version. » Gestes de document
  (envoyer, valider, annuler…) : `{version, …}` dans le corps.
- Listes : tableau complet pour les référentiels et les documents (la recherche multi-mots
  `?q=` et les filtres s'appliquent au serveur) ; **`Page[T]` = `{elements, total, suivant}`**
  (curseur opaque `?apres=`, `?limite=` ≤ 5 000, défaut 500) pour `mouvements`, `journal`,
  `notifications`, `operations`, `signalements`, `receptions/pesees`. Plus aucune liste n'est
  coupée sans le dire (incohérence B.13-19).
- Date de référence : `?date=AAAA-MM-JJ` sur les lectures calculées (stock, plan d'achat,
  cockpit, valorisation, contrôles, besoins, exports) ; bornée 2000-01-01 … aujourd'hui → 422.

### 0.2 Rôles

**P** public · **D** direction · **A** achats · **L** alimentation · **T** administrateur
technique · **C** = D, A, L (rôles métier) · **Tous** = D, A, L, T. Déclarés par
`dependencies=[droit(...)]` ; la matrice complète est générée depuis les routes
(`securite/matrice.py`) et versionnée (`tests/matrice_droits.csv`). La direction **ne passe
plus partout par principe** : elle figure explicitement dans chaque `droit(...)` (la matrice
le montre) ; l'administrateur n'est dans aucune route métier.

### 0.3 Erreurs

Corps unique `{"detail": "<phrase française>", "code": "<code>"}` (+ `"champs": {chemin: message}`
pour 422 de saisie). Codes HTTP : **422** saisie (types, bornes, valeurs inconnues, règle de
saisie) · **409** conflit ou état (statut qui interdit, version périmée, stock insuffisant,
période close, inventaire en cours, doublon) · **404** introuvable · **410** fichier d'une pièce jointe disparu du disque (`fichier_disparu`) · **403** droit (ou en-tête
anti-falsification absent) · **401** non connecté · **429** trop d'essais de connexion · **503**
base en retard de migration ou restauration en cours. **Jamais de 500 pour une saisie** : toute
exception non prévue est journalisée avec l'identifiant de requête et rendue 500
`{"detail": "Erreur du serveur (réf. a1b2c3d4).", "code": "erreur_serveur"}`. Les codes
`code` sont listés dans `api/erreurs.py` (≈ 60 : `saisie_invalide`, `introuvable`,
`conflit_version`, `etat_incompatible`, `periode_close`, `date_future`, `date_trop_ancienne`,
`stock_insuffisant`, `lot_absent_a_la_date`, `inventaire_en_cours`, `numero_pris`,
`deja_annule`, `approbation_requise`, `droit_refuse`, `non_connecte`, `compte_inactif`,
`trop_d_essais`, `entete_absente`…).

### 0.4 Filtre des prix

Toute réponse JSON passe, pour un rôle hors `VOIT_PRIX = {D, A}`, par le filtre générique
`securite.sans_prix` qui met à `null`, **à toute profondeur**, les clés de la liste
`CLES_MONETAIRES` (motifs : `prix*`, `montant*`, `valeur*`, `cout*`, `cmup*`, `budget*`, `cours*`,
`taux_droits`, `economie*`, `revient*`, `tva*`, `droits*`, `frais*`, `devise_prix`, `*_mad`) —
liste déclarée une fois, essai qui parcourt toutes les routes GET en rôle L. En plus, les routes
« C » ont un **schéma de sortie réduit** pour L quand des champs entiers n'ont pas de sens
(fournisseur résumé, stock sans conseil d'achat chiffré). Une écriture de L ne peut pas changer
un prix (champs monétaires interdits dans ses schémas d'entrée).

### 0.5 Anti-falsification, en-têtes

Toute requête non GET sous `/api` (y compris **`/deconnexion`**, contrairement à Gestion MP)
porte `X-Gestion-MP-PRO: 1`, sauf `/connexion`, `/installation`, `/appareils/enroler`. Réponses :
`Cache-Control: no-store`, `X-Heure-Serveur`, `X-Requete` (identifiant de requête), et les
en-têtes de sécurité (aussi sur les refus du middleware). Documents HTML : `Content-Disposition:
inline` ; pièces jointes : `attachment`.

---

## 1. Catalogue PRO

Colonnes : **N°** · **Méthode** · **Chemin** (sans `/api`) · **Rôles** · **Entrée** · **Sortie** · **← GMP**.

### 1.1 Système (`api/systeme`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 1 | GET | `/sante` | P | — | `Sante` {etat, version, schema (révision Alembic), schema_attendu, base_ms, sauvegarde_age_h, sauvegarde_alerte, taches `{tâche: "ok" \| "échec : …" \| "jamais" \| "en cours"}` (+ `restauration` dès qu'il y en a eu une), courriels_en_attente} | B1 |
| 2 | GET | `/etat` | P | — | `EtatInstallation` {installe, societe, version} | B2 |
| 3 | GET | `/contexte` | Tous | — | `Contexte` {moi, menu (entrées permises), heure_serveur, date_cloture, inventaires_ouverts [{numero, magasin, matieres}], societe, roles_au_metre, base_essai, compteurs {clé: nombre} (pastilles du menu), alerte_serveur (D, T)} | nouveau (remplace plusieurs lectures de démarrage) |
| 4 | GET | `/serveur` | D, T | — | `EtatServeur` (versions, base, réseau, tâches, sauvegardes, sessions par compte) | B22 |
| 5 | GET | `/acces` | C | — | `Acces` {adresses, adresse_publique, adresse_qr, alerte_localhost} (schéma et port **de la requête**, port implicite omis : derrière HTTPS, `https://nom` sans « :8050 », G-13) | B28 |
| 6 | GET | `/acces/qr` | C | `?adresse=` | SVG | B29 |
| 7 | GET | `/donnees/{table}` | D | `?date=` (facultatif : borne les tables datées au soir de ce jour) | `DonneesBrutes` {table, date_reference, colonnes, lignes} : JSON brut d'une table métier (liste fermée, `services/donnees_brutes.py`) pour la vérification indépendante ; table hors liste → 404. Servie par le routeur `pilotage` (étiquette « Pilotage et analyse ») | nouveau |

### 1.2 Comptes et appareils (`api/comptes`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 8 | GET | `/visages` | P (poste local ou appareil enrôlé ; sinon liste vide) | — | `[Visage]` {id, nom, role, role_libelle, longueur_code} | B3 |
| 9 | POST | `/installation` | P (une fois) | `Installation` {societe, identifiant, nom, code} | `Moi` | B4 |
| 10 | POST | `/connexion` | P | `Connexion` {identifiant \| compte (id du visage : poste local ou appareil enrôlé, 403 `poste_non_autorise` sinon), code} | `Moi` (cookie) | B5 |
| 11 | POST | `/deconnexion` | Tous | — | 204 | B6 |
| 12 | GET | `/moi` | Tous | — | `Moi` {id, identifiant, nom, role, role_libelle, email, voit_prix, droits, vu_le, version} | B7 |
| 13 | PUT | `/moi` | Tous | `MoiModification` {email, version} | `Moi` | nouveau |
| 14 | PUT | `/moi/code` | Tous | `ChangementCode` {ancien, nouveau} | 204 (ferme les autres sessions) | B8 |
| 15 | GET | `/utilisateurs` | D, T | — | `[UtilisateurFiche]` {id, identifiant, nom, role, role_libelle, email, actif, historique, vu_le, code_change_le, cree_le, version, sessions_ouvertes} | B9 |
| 16 | POST | `/utilisateurs` | D, T | `UtilisateurCreation` {identifiant, nom, role, email, code} | `UtilisateurFiche` | B10 |
| 17 | PUT | `/utilisateurs/{id}` | D, T | `UtilisateurModification` {nom, role, email, actif, version, code (facultatif : un changement de rôle qui exige un nouveau code se fait en une requête)} | `UtilisateurFiche` | B11 |
| 18 | POST | `/utilisateurs/{id}/code` | D, T | `NouveauCode` {code} | 204 (ferme ses sessions) | B11 (champ `code`) |
| 19 | GET | `/appareils` | D, T | — | `[AppareilFiche]` {id, nom, actif, enrole, enrole_le, enrolement_expire_le, vu_le, cree_le, cree_par, sessions_ouvertes} | nouveau |
| 20 | POST | `/appareils` | D, T | `AppareilCreation` {nom} | `Enrolement` {id, nom, lien, qr_svg, expire_le} | nouveau |
| 21 | DELETE | `/appareils/{id}` | D, T | — | 204 (révoque, ferme ses sessions) | nouveau |
| 22 | POST | `/appareils/enroler` | P (jeton unique) | `{jeton}` | 204 (cookie d'appareil) | nouveau |

### 1.3 Réglages (`api/reglages`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 23 | GET | `/parametres` | D ; A (lecture) ; T (familles techniques) | — | `[Reglage]` {cle, libelle, famille, unite, echelle, aide, bas, haut, texte, defaut, valeur, technique, modifiable, version, version_globale} | B14 |
| 24 | PUT | `/parametres` | D (métier) ; D, T (techniques) | `{valeurs: {clé: valeur}, version_globale}` (Σ des `version` des 57 lignes ; périmée → 409 ; tout ou rien) | `[Reglage]` | B15 |
| 25 | GET | `/parametres/historique` | D, T | `?cle=` | `Page[ReglageHistorique]` {cle, libelle, avant, apres, quand, par, motif} | B16 |
| 26 | PUT | `/periode-close` | D | `ClotureEntree` {date_cloture \| null, motif ≥ 3, version} (celle de la ligne `date_cloture`) | `Periode` {date_cloture, par, quand, version} | B15 (clé `date_cloture`) |
| 246 | GET | `/periode-close/brouillons` | D | `?date=AAAA-MM-JJ` | `BrouillonsPeriode` {jusqu_au, total, genres [{genre, libelle, nombre}], message} : les brouillons datés jusqu'à cette date, qui empêcheraient de clore la période jusque-là | nouveau (lot RESTES3) |
| 27 | GET | `/devises` | D, A | — | `[DeviseFiche]` {code, nom, cours, cours_le, cours_repris, actif, version} | B17 |
| 28 | GET | `/devises/{code}/cours` | D, A | — | `Page[CoursHistorique]` {id, cours, saisi_le, par, variation} | B18 |
| 29 | POST | `/devises` | D, A | `DeviseCreation` {code, nom, cours} | `DeviseFiche` | B19 (création) |
| 30 | PUT | `/devises/{code}` | D, A | `DeviseModification` {nom, cours, actif, version} | `DeviseFiche` | B19 (modification) |
| 31 | GET | `/magasins` | C | — | `[MagasinFiche]` {id, code, nom, type, contenu, actif, kg_detenus, version} | A26 |
| 32 | POST | `/magasins` | D | `MagasinCreation` | `MagasinFiche` | A27 |
| 33 | PUT | `/magasins/{id}` | D | `MagasinModification` (+version) | `MagasinFiche` | A28 |
| 34 | GET | `/postes-frais` | D, A | — | `[PosteFiche]` {id, code, libelle, recuperable, nature, entre_valeur_douane, cle, ordre, systeme, frais_ouverts, frais_clos, dossiers_ouverts, dossiers_clos, utilise, version} | A36, A40 |
| 35 | POST | `/postes-frais` | D | `PosteCreation` | `PosteFiche` | A41 |
| 36 | PUT | `/postes-frais/{id}` | D | `PosteModification` (+version) | `PosteFiche` (+ `parts_figees` : nombre de frais de dossiers clos figés) | A42 |
| 37 | DELETE | `/postes-frais/{id}` | D | `?version=` | 204 | A43 |
| 38 | GET | `/codes-douaniers` | D, A | — | `[CodeDouanierFiche]` {id, code, libelle, taux_droits, actif, nb_matieres, version} | A44 |
| 39 | POST | `/codes-douaniers` | D | `CodeDouanierCreation` | `CodeDouanierFiche` | A45 |
| 40 | PUT | `/codes-douaniers/{id}` | D | `CodeDouanierModification` | `CodeDouanierFiche` | A46 |
| 41 | DELETE | `/codes-douaniers/{id}` | D | `?version=` (facultatif, contrôlé s'il est donné) | 204 | A47 |
| 42 | GET | `/motifs` | C | — | `Motifs` {types [{type, libelle, roles}], motifs [{id, type, libelle, code_r, impose_role}], reclamation_motifs, reclamation_issues} | B32 |

Clés des routes 23–25 : la liste fermée `modeles.CLES_REGLAGES` (MODELE-DONNEES § 3.1.6 ; une clé
inconnue → 422), soit 56 clés semées par la révision 0002, dont `delai_frais_import_jours`
(« Dossier sans frais à signaler après », famille Prix, jours, défaut 30, bornes 1–365 ; lu par C28)
et `seuil_bc_urgent` (sans effet, gardé pour mémoire). `toler_tva_import` (« TVA d'importation à
vérifier au-delà de », famille Prix, %, défaut 5 %, bornes 0–100 % ; lu par C29 et par la fiche du
dossier, route 189) entre avec la révision **0003** (57 clés ensuite).

### 1.4 Exploitation (`api/exploitation`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 43 | GET | `/sauvegardes` | D, T | — | `EtatSauvegardes` {base, derniere, age_h, alerte, politique, dossier, copie, nb, autres, outils, fichiers [{nom, genre, nature, base, autre_base, taille, quand, tables, pieces, copie}]} | B20 |
| 44 | POST | `/sauvegardes` | D, T | — | `EtatSauvegardes` | B21 |
| 45 | POST | `/sauvegardes/{nom}/restaurer` | D, T | `Restauration` {confirmation: "RESTAURER" (casse indifférente, 422 `confirmation_requise` sinon), motif 3–300} | 202 `EtatRestauration` {etat, fichier, avant, debut, message} dès la sauvegarde « avant restauration » faite (refus tous synchrones : 404, 409, 422, 503) ; l'écran suit `/sante` → `taches.restauration` | B23 |
| 46 | GET | `/taches` | D, T | — | `[TacheEtat]` | nouveau |
| 47 | GET | `/courriels` | D, T | — | `Page[CourrielFiche]` | nouveau |
| 48 | GET | `/courriel/apercu` | D | — | `ApercuCourriel` {sujet, texte, serveur_configure, destinataires, illisibles} | B98 |

### 1.5 Journal et historique (`api/journal`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 49 | GET | `/journal` | D, T | `?q=&utilisateur=&action=&objet=&objet_id=&du=&au=` | `Page[LigneJournal]` {id, quand, utilisateur, utilisateur_id, role, action, objet, objet_id, numero, detail, avant, apres} (`utilisateur=` : l'id du compte) | B12 |
| 50 | GET | `/journal/valeurs` | D, T | — | `ValeursJournal` {utilisateurs: [{id, nom}], actions, objets} | B13 |
| 51 | GET | `/historique/{objet}/{id}` | droit de lecture de la fiche (prix filtrés pour L) | — | `[LigneHistorique]` (différences lisibles) | nouveau |
| 52 | GET | `/export/journal` | D, T | mêmes filtres | xlsx | B108 |

### 1.6 Notifications et recherche

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 53 | GET | `/notifications` | Tous | `?non_lues=` | `Page[Notification]` {id, texte, lien, ton, quand, lue} + `non_lues` | nouveau |
| 54 | POST | `/notifications/{id}/lue` | Tous | — | 204 | nouveau |
| 55 | POST | `/notifications/lues` | Tous | — | 204 | nouveau |
| 56 | GET | `/recherche` | C | `?q=` (≥ 2 car.) | `[ResultatRecherche]` {genre, id, titre, sous_titre, lien} — matières, lots, commandes, réceptions, dossiers, fournisseurs, qualités, ordres, filtrés par rôle | nouveau |

### 1.7 Classification (`api/classification`)

`{liste}` ∈ `compositions`, `types-fil`, `titrages`, `couleurs`.

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 57 | GET | `/classification` | C | — | `Classification` {compositions, types_fil, titrages, couleurs: [ValeurFiche + nb_matieres], roles: [RoleFiche {id, code, lineaire, de_base, ordre, version} + nb_matieres, nb_qualites]} | A1 |
| 58 | POST | `/classification/roles` | D | `RoleCreation` {code, ordre} | `RoleFiche` | A2 |
| 59 | PUT | `/classification/roles/{id}` | D | `RoleModification` {code, ordre, version} | `RoleFiche` | A3 |
| 60 | DELETE | `/classification/roles/{id}` | D | — | 204 | A4 |
| 61 | POST | `/classification/{liste}` | D, A | `ValeurCreation` | `ValeurFiche` | A5 |
| 62 | PUT | `/classification/{liste}/{id}` | D, A | `ValeurModification` (+version) | `ValeurFiche` (+ `avertissement` : une valeur désactivée encore portée) | A6 |
| 63 | DELETE | `/classification/{liste}/{id}` | D, A | `?version=` (facultatif) | 204 | A7 |

### 1.8 Fournisseurs (`api/fournisseurs`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 64 | GET | `/fournisseurs` | C (L : `FournisseurResume` {id, nom, pays, actif}) | `?q=&actif=` | `[FournisseurFiche \| FournisseurResume]` (+ `nb_matieres`, `nb_commandes`, `nb_receptions`, `nb_lots`, `nb_operations`, `nb_factures`, `nb_pieces`, délai mesuré, `local`, `devises`, `utilise`, `empechements`) | A8 |
| 65 | GET | `/fournisseurs/{id}` | D, A | — | `FournisseurFiche` | nouveau (fiche à adresse stable) |
| 66 | POST | `/fournisseurs` | D, A | `FournisseurCreation` | `FournisseurFiche` | A9 |
| 67 | PUT | `/fournisseurs/{id}` | D, A | `FournisseurModification` (+version) | `FournisseurFiche` | A10 |
| 68 | DELETE | `/fournisseurs/{id}` | D, A | `?version=` (facultatif) | 204 | A11 |
| 69 | GET | `/export/fournisseurs/fiches` | D, A | — | xlsx | A38 |

### 1.9 Matières (`api/matieres`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 70 | GET | `/matieres` | C (prix filtrés) | `?q=&role=&fournisseur=&actif=` | `[MatiereResume]` (référence, classification en codes **et** ids — `role_id`, `composition_id`, `type_fil_id`, `titrage_id`, `couleur_id`, `code_douanier_id`, `fournisseur_id` —, prix, unite_prix, prix_kg, devise, densité, kg_par_ml, conditionnement, stock, utilisée, version) | A12 |
| 71 | GET | `/matieres/{id}` | C | — | `MatiereFiche` (champs de `MatiereResume` + usages, modifie_le, modifie_par) | nouveau |
| 72 | POST | `/matieres` | D, A | `MatiereCreation` | `MatiereFiche` | A13 |
| 73 | PUT | `/matieres/{id}` | D, A | `MatiereModification` (+version) | `MatiereFiche` | A14 |
| 74 | DELETE | `/matieres/{id}` | D, A | `?version=` (facultatif) | 204 | A15 |
| 75 | GET | `/matieres/reference` | C | `?composition_id=&type_fil_id=&titrage_id=&couleur_id=&couleur_code=&suffixe=` | `ReferenceComposee` {reference, designation} | A17 (POST → GET : lecture) |
| 76 | GET | `/matieres/classement` | D, A | — | `ApercuClassement` | A16 (`appliquer=false`) |
| 77 | POST | `/matieres/classement` | D, A | `{ids, versions}` | `ResultatClassement` | A16 (`appliquer=true`) |
| 78 | GET | `/matieres/tableur` | D, A | — | xlsx (modèle = catalogue actuel, avec colonne `version`) | B96 |
| 79 | POST | `/matieres/tableur/apercu` | D, A | fichier xlsx | `ApercuImport` {lignes [{ligne, reference, etat: nouvelle\|modifiee\|inchangee\|erreur, changements, erreurs}], creees, modifiees, inchangees, erreurs, appliquable, empreinte_apercu} | B97 (`appliquer=false`) |
| 80 | POST | `/matieres/tableur/appliquer` | D, A | formulaire : fichier xlsx + champ `empreinte_apercu` (plan d'écriture refait ; différent → 409) | `ResultatImport` (mêmes compteurs) | B97 (`appliquer=true`) |
| 81 | GET | `/export/matieres` | D, A | `?q=…` | xlsx | A37 |

### 1.10 Qualités, recettes, plan (`api/qualites`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 82 | GET | `/qualites` | C (coûts filtrés) | — | `[QualiteResume]` (poids `[{role_id, role, lineaire, poids}]`, plan : `base_mensuelle` et `saisonnalite` (12), recette calculée, contrôle 100 %, `fabrications`, `facteurs_cout` {perte, cours} — A19 fondue ; cours filtrés hors D/A) | A18 + A19 |
| 83 | GET | `/qualites/{id}` | C | — | `QualiteFiche` (= `QualiteResume` + `avertissement`) | nouveau |
| 84 | POST | `/qualites` | D | `QualiteCreation` {code, nom, actif, poids `[{role_id, poids}]`} (liste par id de rôle, plus de dictionnaire par code) | `QualiteFiche` (201) | A20 |
| 85 | PUT | `/qualites/{id}` | D | `QualiteModification` {code, nom, actif, poids `[{role_id, poids}]`, recette (facultative : `[{matiere_id, pourcentage}]`), motif, version} | `QualiteFiche` (+ avertissement) | A21 |
| 86 | DELETE | `/qualites/{id}` | D | `?version=` (obligatoire) | 204 | A22 |
| 87 | PUT | `/qualites/{id}/recette` | D | `RecetteEntree` {lignes [{matiere_id, pourcentage}], motif, version} | `QualiteFiche` | A23 |
| 88 | GET | `/qualites/{id}/versions` | C | — | `[RecetteVersionFiche]` {numero, valide_depuis, par, origine, motif, lignes, poids} | B93 |
| 89 | POST | `/qualites/{id}/versions/{vid}/restaurer` | D | `{motif, version}` | `QualiteFiche` ; vers la recette déjà en vigueur → 409 « La recette en vigueur est déjà celle de cette version : rien à restaurer. » | A24 |
| 90 | PUT | `/qualites/{id}/plan` | D | `PlanQualiteEntree` {base_mensuelle, coefficients[12], motif, version} | `QualiteFiche` (les coefficients reviennent en `saisonnalite`) | A25 |
| 91 | GET | `/qualites/{id}/plan/versions` | C | — | `[PlanVersionFiche]` | nouveau |
| 92 | GET | `/nomenclature` | C (prix filtrés) | `?date=` (accepté et borné, **sans effet** : la nomenclature est celle en vigueur ; les recettes passées sont dans les versions, 88) | `Nomenclature` {lignes, controle [{qualite_id, qualite, actif, roles_utilises, roles_conformes, ecarts, conforme}]} | B65 |
| 93 | GET | `/export/qualites` | D, A | — | xlsx | A39 |

### 1.11 Métiers et montage (`api/metiers`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 94 | GET | `/metiers` | C (valeurs filtrées) | — | `[MetierFiche]` (étages, fils montés, bobines, kg, valeur, version par étage) | A29 |
| 95 | GET | `/metiers/{id}` | C | — | `MetierFiche` | nouveau |
| 96 | POST | `/metiers` | D | `MetierCreation` | `MetierFiche` | A31 |
| 97 | PUT | `/metiers/{id}` | D | `MetierModification` {code, nom, laize, bobines_par_metre (la « densité » de Gestion MP), etages, actif, commentaire, version, montage (facultatif, `MontageEntree`)} ; des fils au-delà du nouveau nombre d'étages → 422 (X-REF-62) | `MetierModifie` (= `MetierFiche` + `montage` : `ResultatMontage` ou null) | A32 |
| 98 | DELETE | `/metiers/{id}` | D | `?version=` (obligatoire) | 204 | A33 |
| 99 | PUT | `/metiers/{id}/montage` | D, L | `MontageEntree` {etages: [{etage, version, fils}], confirme_effet_kg} : seuls les étages envoyés sont remplacés, les autres ne bougent pas (Gestion MP remplaçait tout le montage) ; étage hors du métier → **404** « Étage N : ce métier n'en a que M. » | `ResultatMontage` {metier, effet_kg, avant_kg, apres_kg, alertes, message} | A34 |
| 100 | PUT | `/metiers/{id}/etages/{etage}` | D, L | `EtageEntree` {version, fils [{matiere_id, metres, pourcentage, commentaire}], confirme_effet_kg} ; étage hors du métier → 404 (comme 99) | `ResultatMontage` | A35 |
| 101 | GET | `/metiers/{id}/montages` | C | — | `[MontageEvenementFiche]` {id, quand, par, etage, origine, avant, apres, avant_kg, apres_kg, effet_kg, alerte} ; `origine` déduite de `etage` (MODELE-DONNEES `montage_evenement`) | nouveau |
| 102 | GET | `/montage/matieres` | C | — | `[MatiereMontage]` {matiere, poids_bobine_compte, origine_poids, sorti_30_j, deja_monte} | A30 |

### 1.12 Stock et lots (`api/stock`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 103 | GET | `/stock` | C (L : `LigneStockAtelier`, sans montants ni conseil d'achat) | `?date=&q=` | `[LigneStock]` (tous les champs de `LigneStock`, CALCULS § 3.9 ; `statut`, `statut_couverture` en codes `RUPTURE` \| `CRITIQUE` \| `URGENT` \| `ATTENTION` \| `OK` \| `NON_CONSOMMEE`, `action` en `CREER_BC` \| `AUCUNE` — l'écran les traduit, § 2) | B63 |
| 104 | GET | `/stock/{matiere_id}` | C | `?date=` | `FicheStockMatiere` (ligne + d'où vient le besoin + lots + sur les métiers) | nouveau (agrège ce que la fenêtre « Fiche matière » lisait) |
| 105 | GET | `/mouvements` | C (prix filtrés) | `?q=&matiere=&lot=&magasin=&type=&document=&du=&au=&avec_valeur=&apres=&limite=` | `Page[MouvementLigne]` | B24 |
| 106 | GET | `/export/mouvements` | C (colonnes de prix absentes pour L) | mêmes filtres | xlsx | B101 |
| 107 | GET | `/lots` | C | `?matiere=&magasin=&statut=&non_nuls=&q=` | `[LotSolde]` (soldes par magasin, statut calculé) | B25 |
| 108 | GET | `/lots/{id}` | C (prix filtrés) | — | `LotFiche` (en-tête, soldes, mouvements, réception, poids de bobine, commentaire, version) | B26 |
| 109 | PUT | `/lots/{id}` | D, A | `{commentaire, version}` | `LotFiche` | nouveau (`lot.commentaire`) |
| 110 | GET | `/lots/scan` | C | `?code=` | `[LotResume]` (un même numéro peut exister pour deux matières) ; 404 si vide | B27 |
| 111 | GET | `/lots/disponibles` | C | `?matiere=&date=&magasin=` | `[LotDisponible]` (présents à la date, hors quarantaine, FIFO) | B78 |
| 112 | GET | `/tracabilite` | C | `?lot=&ordre=&matiere=` | `Tracabilite` (vocabulaire de la base, plus de codes ERP Fil à émojis) | B79 |
| 113 | GET | `/controles/soldes` | D, A | — | `ControleSoldes` (libellés : référence, lot, magasin) | B31 |
| 114 | GET | `/documents/etiquettes` | C | `?lots=1,2,3` | HTML, une étiquette QR de 100 × 70 mm par page (404 HTML « Aucun lot à étiqueter. ») | B30 |

### 1.13 Opérations de stock et brouillons (`api/operations`)

Droit par type (`services/operations/droits.py`, une table) : ouverture, ajustement, retour
fournisseur → D, A ; retour machine → D, L ; transfert → D, A, L ; motif « Libération de
quarantaine » → D, A ; motif « Mise en quarantaine » → D, A, L (commentaire obligatoire).

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 115 | GET | `/operations` | C (prix filtrés) | `?type=&statut=&q=&apres=&limite=` | `PageOperations` = `Page[OperationFiche]` | B33 |
| 116 | GET | `/operations/{id}` | C | — | `OperationFiche` (+ `blocages`, `peut_agir`, `raison`, `liberation`, `mise_en_quarantaine`, `valeurs [{devise, montant}]`, `annulee_par`, `annulee_le`, `annulation_motif`, `version`) | B34 |
| 117 | POST | `/operations` | C selon le type | `OperationCreation` {type, date, ordre_id, fournisseur_id (ignoré : le fournisseur est celui des lots, S101), motif_id, commentaire, valider, lignes [{matiere_id, lot_id, lot_numero, lot_interne, magasin_id, magasin_destination_id, quantite, unite (kg\|bobine\|palette), prix, devise}]} | `OperationFiche` | B35 |
| 118 | PUT | `/operations/{id}` | idem | `OperationModification` (+version) | `OperationFiche` | B36 |
| 119 | DELETE | `/operations/{id}` | idem | `?version=` | 204 | B37 |
| 120 | POST | `/operations/{id}/valider` | idem | `{version}` | `OperationFiche` | B38 |
| 121 | POST | `/operations/{id}/annuler` | idem | `{version, motif}` (motif facultatif) | `OperationFiche` | B39 |
| 122 | GET | `/brouillons` | C | — | `Brouillons` {lignes (tous, dans l'ordre de validation), ordres, operations, receptions (D, A), nombre, bloques, validables} ; chaque élément avec `version`, `blocages`, `peut_valider`, `raison`, `valide_par` | A69 |
| 123 | POST | `/brouillons/valider` | C | `{documents: [{genre, id, version}]}` ou `{tous: true}` (corps vide → 422 « Choisir les documents à valider, ou demander de tout valider. ») | `ResultatValidationGroupee` {valides, refuses, ignores} (clés sans accents ; `ignores` = le `non_permis` de Gestion MP corrigé, C-17), chaque élément {genre, type, id, date, libelle, resume, lien, numero, raison} | A70 |

### 1.14 Inventaires (`api/inventaires`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 124 | GET | `/inventaires` | C (montants filtrés) | `?statut=` | `[InventaireResume]` (+ `perimetre`, `criteres`, `nb_matieres_suspendues`, `abandonne_par/le`, `abandon_motif`, `annule_par/le`, `annulation_motif`, `sans_justification`, `recomptes_meme_personne`, `version`) | B40 |
| 125 | GET | `/inventaires/defauts` | D, A | — | `DefautsInventaire` {tolerance, roles `[{id, code}]`, compositions `[{id, code}]` (Gestion MP : des codes), cadence_jours} | B41 |
| 126 | GET | `/inventaires/a-compter` | D, A | `?magasin=` | `[MatiereACompter]` | B42 |
| 127 | GET | `/inventaires/{id}` | C | — | `InventaireFiche` = `InventaireResume` + blocages, lignes (+ `lot_trouve`, `lot_interne`, `compte_par`, `second_par`, `quatre_yeux`, `ecart_pourcent`) | B43 |
| 128 | POST | `/inventaires` | D, A | `InventaireOuverture` {date, magasin_id, libelle, tolerance, criteres: {matieres, roles, compositions, classes_abc}} | `InventaireFiche` | B44 |
| 129 | PUT | `/inventaires/{id}/comptages` | D, A | `{version, lignes: [{ligne_id, compte, palettes, bobines, justification, second_compte?}]}` (un champ absent = inchangé ; `null` explicite = vidé) | `InventaireFiche` | B45 (lignes existantes) |
| 130 | POST | `/inventaires/{id}/lots-trouves` | D, A | `{version, matiere_id, lot_numero, lot_interne, magasin_id, compte, palettes, bobines, justification}` | `InventaireFiche` | B45 (lot trouvé) |
| 131 | POST | `/inventaires/{id}/valider` | D, A | `{version}` | `InventaireFiche` | B46 |
| 132 | POST | `/inventaires/{id}/abandonner` | D, A | `{version, motif}` (motif exigé, ≥ 3 : « Dire pourquoi l'inventaire est abandonné. ») | `InventaireFiche` (statut `abandonne` ; numéro, comptages et lignes gardés ; motif dans `abandon_motif`) | B47 |
| 245 | POST | `/inventaires/{id}/annuler` | D, A | `{version, motif}` (motif ≥ 3 caractères, obligatoire) | `InventaireFiche` (statut `annule`, numéro gardé, ajustements contre-passés) | nouveau : Gestion MP corrigé, étape 17 (`POST /inventaires/{iid}/annuler`, U19) |
| 133 | GET | `/documents/inventaires/{id}/feuille` | C | `?recomptage=&theorique=` | HTML A4 paysage | B48 |

États d'un inventaire (`?statut=` de 124 et 239) : `ouvert`, `valide`, `abandonne`, **`annule`**. Un
inventaire **en cours** s'abandonne (132 : rien n'est ajusté) ; un inventaire **validé** s'annule (245) :
chacun de ses ajustements est contre-passé **une fois** (UQ `mouvement.contrepasse_id`), daté comme lui ;
refus 409 si l'inventaire n'est pas validé (« Seul un inventaire validé s'annule ; un inventaire en cours
s'abandonne. »), s'il est déjà annulé, si la période est close, si la matière ajustée est déjà repartie
(stock insuffisant), ou si un inventaire ouvert suspend une matière ajustée dans son magasin ; 422 sans motif (« Dire pourquoi
l'inventaire est annulé. »). `valide_le` reste posé ; `annule_le`, `annule_par_id`, `annulation_motif`
s'y ajoutent ; journal « annulation inventaire » « {n°} · {motif} ».

Un seul inventaire **ouvert par magasin**, et un inventaire de tous les magasins exclut tout autre
(index unique `uq_inventaire_ouvert_magasin`, vérifié sous le verrou `INVENTAIRE_GLOBAL`) : 128 refuse
(409) « … déjà ouvert sur « CODE ». » / « … sur tous les magasins. ». L'abandon (132) range son motif
dans `abandon_motif` (révision 0005), l'annulation (245) dans `annulation_motif`.

### 1.15 Ordres de fabrication (`api/ordres`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 134 | POST | `/ordres/proposition` | C (lecture en POST : corps structuré) | `DemandeProposition` {date (facultative : aujourd'hui), magasin_id, metier_id, qualites [{qualite_id, m2}]} ; magasin inconnu → 404 | `Proposition` {date, magasin_id, taux_perte, prevu (perte comprise), manque, lignes FIFO [{matiere_id, reference, designation, role, prevu, par_qualite [{qualite_id, qualite, kg}], kg_par_ml, poids_bobine, bobines_palette, lots, disponibles, manque}], manques, recettes_incompletes, blocages} | B49 |
| 135 | GET | `/ordres` | C | `?statut=&q=&du=&au=&metier=&magasin=&qualite=` (ids) ; `du > au` → 422 | `[OrdreResume]` (net, écart, lots) — liste complète, non paginée | B50 |
| 136 | GET | `/ordres/{id}` | C | — | `OrdreFiche` = `OrdreResume` + `lignes`, `par_matiere`, `message` ; vocabulaire PRO : `prevu` (Gestion MP : `theorique`), `par_matiere` (`par_fil`), `retours [{id, numero, date, quantite}]` (`retours_detail`), `revenu`, `fabrication`, `m2`, `lots`, `matieres`, `taux_perte`, `prevu_fige`, `annule_par/le`, `annulation_motif`, `version`, `blocages` ; un brouillon : `prevu` 0 et `par_matiere` vide | B56 |
| 137 | POST | `/ordres` | D, L | `OrdreCreation` {date, magasin_id, metier_id, commentaire, qualites, lignes [{lot_id, quantite, unite, matiere_id?}]} (la matière se lit sur le lot ; `matiere_id` ne sert qu'au contrôle) | `OrdreFiche` | B51 |
| 138 | PUT | `/ordres/{id}` | D, L | `OrdreModification` (+version) | `OrdreFiche` | B52 |
| 139 | DELETE | `/ordres/{id}` | D, L | `?version=` | 204 | B53 |
| 140 | POST | `/ordres/{id}/valider` | D, L | `{version}` | `OrdreFiche` | B54 |
| 141 | POST | `/ordres/{id}/annuler` | D, L | `{version, motif}` (motif facultatif) | `OrdreFiche` (annule aussi ses retours, brouillons de retour supprimés avec le dire) | B55 |
| 142 | GET | `/ordres/{id}/lots-sortis` | C | — | `[LotSorti]` (net des retours ; + `designation`, `blocage` : l'inventaire qui suspend la matière) | B57 |
| 143 | GET | `/ordres/consommation` | C | `?du=&au=&qualite=` | `[ConsommationOrdre]` (+ `ordre_id` ; les totaux se font à l'écran) | B80 |
| 144 | GET | `/export/ordres` | C | `?statut=&q=&du=&au=&metier=&magasin=&qualite=&vue=ordres\|consommation` | xlsx `ordres-AAAA-MM-JJ.xlsx` ou `consommation-ordres-AAAA-MM-JJ.xlsx` (colonne « Statut » en plus : les statuts peuvent être mêlés) | B58 |

### 1.16 Production et besoins (`api/production`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 145 | GET | `/production/plan` | C | `?date=` | `PlanProduction` | B59 |
| 146 | PUT | `/production/plan` | D | `PlanGlobalEntree` {qualites [{qualite_id, base_mensuelle, coefficients (12), version}], motif} ; une qualité deux fois → 422 ; qualité inconnue → 404 « Qualité introuvable : le plan n'a pas été enregistré. » ; version périmée → 409 nommant la qualité | `PlanProduction` (coefficients rendus en `saisonnalite`) + `modifiees` (nombre de qualités changées) | B60 |
| 147 | GET | `/production/realise` | C | `?date=` | `PlanEtRealise` | B61 |
| 148 | GET | `/production/besoins` | C | `?date=&matiere=` | `BesoinsDetailles` | B62 |

### 1.17 Plan d'achat (`api/plan_achat`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 149 | GET | `/plan-achat` | D, A | `?date=` | `PlanAchat` {date_reference, indicateurs (à commander, en alerte, budget MAD, quantité, classe A, ruptures… par statut, tiers), fournisseurs (montants par devise), lignes} (`api/plan_achat/schemas.py`) | B66 |
| 150 | GET | `/plan-achat/fournisseurs/{id}` | D, A | `?date=` | `PreparationCommande` {fournisseur_id, fournisseur, pays, contact, email, delai_jours, devise_par_defaut, date_reference, lignes (+ `depart` {unite, contenance, quantite, unites} : l'unité de commande proposée)} | B67 (par id, plus par nom) |
| 151 | GET | `/export/pilotage` | D, A | `?date=` | xlsx (stock, plan d'achat, fournisseurs, besoins, contrôles) | B100 |

### 1.18 Commandes (`api/commandes`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 152 | GET | `/commandes` | D, A | `?statut=&filtre=retard&fournisseur=&q=` (`statut` : un statut, ou `clos` = soldés et annulés, onglet « Soldées / annulées ») | `[CommandeResume]` (état de livraison, montants estimés, reçu, reste, jalons, renvoi… : détail dans `api/commandes/schemas.py` ; `en_retard` (bool, la règle de `?filtre=retard`), `arrivee_attendue` (ETA sinon livraison prévue, pour un bon parti ni soldé ni annulé ; sinon null)) | A48 |
| 153 | GET | `/commandes/{id}` | D, A | — | `CommandeFiche` = `CommandeResume` + lignes (reçu net, `kg_en_quarantaine` : reçu sous réserve encore en quarantaine, attendu jusqu'à sa libération ; reste), `promesse_figee` (la phrase qui dit pourquoi la date promise ne se change plus, ou null), `actions` (geste → null ou phrase du refus), `fin_possible`, `modifiable`, `raison_sociale_reglee`, `decisions`, `version_partie`, `renvoi`, `receptions` [{id, numero, date, statut, pese}], contact du fournisseur, `seuil_approbation` | nouveau |
| 154 | POST | `/commandes` | D, A | `CommandeCreation` {fournisseur_id, date_livraison_prevue, prix_catalogue_a_confirmer: bool, observations, lignes [{matiere_id, quantite, unite_achat, contenance, prix}]} | `[CommandeFiche]` (un bon par devise) | A49 |
| 155 | PUT | `/commandes/{id}` | D, A | `CommandeModification` (+version) | `CommandeFiche` | A50 |
| 156 | DELETE | `/commandes/{id}` | D, A | `?version=` | 204 | A58 |
| 157 | POST | `/commandes/{id}/envoyer` | D, A | `{version, date}` | `CommandeFiche` | A51 |
| 158 | POST | `/commandes/{id}/approuver` | D | `{version, date}` (date réelle d'envoi) | `CommandeFiche` | A52 |
| 159 | POST | `/commandes/{id}/renvoyer` | D | `{version, motif 3–500}` | `CommandeFiche` | A53 |
| 160 | POST | `/commandes/{id}/prix` | D, A | `{version, lignes [{ligne_id, prix, unite: kg\|ml}], mettre_a_jour_catalogue, date_livraison_prevue}` (champ `lignes`, et non `prix` ; un prix au mètre se ramène au kilo par la densité) | `CommandeFiche` | A54 |
| 161 | PUT | `/commandes/{id}/expedition` | D, A | `{version, jalons…}` (champ absent = inchangé, `null` = vidé) | `CommandeFiche` | A55 |
| 162 | POST | `/commandes/{id}/solder` | D, A | `{version, motif}` (motif facultatif, au journal) | `CommandeFiche` | A56 |
| 163 | POST | `/commandes/{id}/rouvrir` | D, A | `{version}` | `CommandeFiche` | A57 |
| 164 | GET | `/documents/commandes/{id}/bon` | D, A | — | HTML A4 anglais sans prix (route déclarée dans `api/commandes/routes_documents.py`, étiquette « Commandes ») | A59 |
| 165 | GET | `/export/commandes/{id}/bon` | D, A | — | xlsx anglais sans prix (même contenu que 164) ; raison sociale de l'usine non réglée → 409 | A97 |
| 166 | GET | `/export/commandes` | D, A | mêmes filtres que 152 | xlsx | A93 |

### 1.19 Réceptions, factures (`api/receptions`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 167 | GET | `/receptions` | D, A | `?statut=&q=&du=&au=&fournisseur=` | `[ReceptionResume]` (brouillons recalés **sans écrire**) | A60 |
| 168 | GET | `/receptions/{id}` | D, A | — | `ReceptionFiche` (+ blocages, avertissements, reste après) | nouveau |
| 169 | POST | `/receptions` | D, A | `ReceptionCreation` {date, fournisseur_id, numero_bl, controle_par, observations, factures: {devise: FactureEntree {numero, date, montant, echeance}} (**dictionnaire par devise** ; une facture pour une devise sans ligne → 422), lignes [{commande_ligne_id, matiere_id, lot_numero, lot_interne, quantite_bl, quantite_pesee, nb_palettes, bobines_en_plus, magasin_id, qualite, observations, prix, devise (hors commande)}]} ; bon pas parti → 409 dès la saisie | `[ReceptionFiche]` (une par devise, **une transaction** : aucune laissée en brouillon si une autre est refusée) | A61 |
| 170 | PUT | `/receptions/{id}` | D, A | `ReceptionModification` = la saisie de 169 + `version`, **une seule devise** (422 « Une réception ne mêle pas deux devises… ») | `ReceptionFiche` (la fiche, pas une liste) | A62 |
| 171 | DELETE | `/receptions/{id}` | D, A | `?version=` | 204 | A63 |
| 172 | POST | `/receptions/{id}/valider` | D, A | `{version}` | `ReceptionFiche` ; un blocage garde son code : `excedent`, `bon_clos`, `etat_incompatible`, `inventaire_en_cours`, `periode_close` → **409** ; `date_invalide`, `quantite_invalide`, `saisie_invalide` → 422 (Gestion MP : 422 pour tout) | A64 |
| 173 | POST | `/receptions/{id}/annuler` | D, A | `{version, motif}` (motif **exigé**, 3–300) | `ReceptionFiche` (une réception toute refusée s'annule) | A65 |
| 174 | PUT | `/receptions/{id}/facture` | D, A | `FactureCorrection` {version (**de la réception**), numero?, date?, montant?, echeance?} — pas de `devise` (celle de la réception) ; champ absent = inchangé ; `numero: ""` détache ; `montant: null` vide le montant — validée seulement (brouillon → 409) | `ReceptionFiche` | A66 |
| 175 | GET | `/factures` | D, A | `?fournisseur=&q=&sans_dossier=` | `[FactureResume]` (+ `payee_par`, `montant_estime` = Σ pesée × prix des réceptions validées, `poids`, `recue_le`, `receptions`, `dossier`, `version`) | A68 |
| 176 | GET | `/receptions/pesees` | D, A | `?q=&ecarts=&fournisseur=&qualite=&magasin=&apres=&limite=` | `PagePesees` = `Page[Pesee]` + {tolerance, tolerance_bobine, kg_pesees, hors_tolerance, non_conformes, bobines_hors_tolerance} | B73 |
| 177 | GET | `/receptions/bobines` | D, A | `?q=&ecarts=&matiere=&fournisseur=` (ids) | `EvolutionBobines` {tolerance, lignes, hors_tolerance, alourdies, allegees} | B74 |
| 178 | GET | `/export/receptions` | D, A | mêmes filtres que 167 | xlsx | A94 |
| 179 | GET | `/export/receptions/pesees` | D, A | mêmes filtres que 176 | xlsx | A95 |
| 180 | GET | `/export/receptions/bobines` | D, A | mêmes filtres que 177 | xlsx | A96 |

### 1.20 Réclamations (`api/reclamations`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 181 | GET | `/reclamations` | D, A | `?statut=ouverte\|close&fournisseur=&reception=&q=` | `[ReclamationResume]` | B81 |
| 182 | GET | `/reclamations/{id}` | D, A | — | `ReclamationFiche` | nouveau |
| 183 | POST | `/reclamations` | D, A | `ReclamationCreation` {fournisseur_id, reception_id, reception_ligne_id, lot_id, motif (code ou libellé), description, quantite, montant_demande, devise, ouverte_le} | `ReclamationFiche` | B82 |
| 184 | PUT | `/reclamations/{id}` | D, A | `ReclamationModification` {reponse, description, montant_obtenu, version} (champ absent = inchangé) — permis aussi sur une **close** (l'avoir arrive après la clôture), sans changer son issue ni la rouvrir | `ReclamationFiche` | B83 (répondre) |
| 185 | POST | `/reclamations/{id}/clore` | D, A | `{version, issue, montant_obtenu, close_le, reponse (facultative)}` ; une close → 409 | `ReclamationFiche` | B83 (clore) |
| 186 | POST | `/reclamations/{id}/rouvrir` | D, A | `{version, motif}` | `ReclamationFiche` | B83 (rouvrir) |

### 1.21 Importations et coût de revient (`api/importations`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 187 | GET | `/dossiers` | D, A | `?statut=ouvert\|clos\|annule&q=&fournisseur=` (sans statut : ouverts et clos ; `q` : mots sans accents sur numéro, libellé, banque, commentaire, factures, réceptions, familles, fournisseurs) | `[DossierResume]` | A71 |
| 188 | GET | `/dossiers/a-rattacher` | D, A | `?locaux=` | `EnAttente` {factures: `[FactureARattacher]`, sans_facture: `[ReceptionSansFacture]`, locaux: {factures, lignes}} ; valeurs par devise en liste `[{devise, valeur}]` | A73 |
| 189 | GET | `/dossiers/{id}` | D, A | — | `DossierFiche` (marchandise, frais, répartition, coût hors TVA, TVA, attendus — dont `tva_ecart_tolere_mad` = \|TVA attendue\| × `toler_tva_import`, le même écart que C29 —, `tva_ecart_mad`, `toler_tva_import`, `cours_eloignes`, `alertes` de clôture, `a_verifier`, `echeancier`, `actions` (geste → null ou phrase du refus), `a_rattacher`, `nb_pieces`, `version` ; détail dans `api/importations/schemas_fiche.py`) | A72 |
| 190 | POST | `/dossiers` | D, A | `DossierCreation` {facture_id \| null, numero (à la main seulement, format `NN/AA`), libelle, date_arrivee (exigée à la main), banque, commentaire, local_confirme} | `DossierFiche` | A74 |
| 191 | PUT | `/dossiers/{id}` | D, A | `DossierModification` {libelle, banque, commentaire, date_arrivee \| null, version} (fiche entière ; `commentaire` = colonne du modèle, « Observations » à l'écran) | `DossierFiche` | A75 |
| 192 | POST | `/dossiers/{id}/rattacher` | D, A | `{version, facture_id}` — par facture seulement (pas de `reception_ligne_ids` : un rattachement par lignes pouvait couper une réception, contraire à « un dossier = une facture = une livraison ») | `DossierFiche` | A76 |
| 193 | POST | `/dossiers/{id}/lignes` | D, A | `LigneManuelle` {matiere_id, lot_numero, fournisseur_id, quantite_kg, valeur_devise, devise, cours (nul = cours du jour), commentaire, version} | `DossierFiche` | A77 |
| 194 | PUT | `/dossiers/{id}/lignes/{lid}` | D, A | `{cours, commentaire, version}` | `DossierFiche` | A78 |
| 195 | DELETE | `/dossiers/{id}/lignes/{lid}` | D, A | `?version=` | `DossierFiche` | A81 |
| 196 | PUT | `/dossiers/{id}/cours` | D, A | `{devise, cours, version}` | `DossierFiche` | A79 |
| 197 | POST | `/dossiers/{id}/cours-des-bons` | D, A | `{version}` | `DossierFiche` | A80 |
| 198 | POST | `/dossiers/{id}/detacher` | D, A | `{reception_id, version}` | `DossierFiche` | A82 |
| 199 | POST | `/dossiers/{id}/frais` | D, A | `FraisEntree` {poste_id, montant, ligne_id, piece, prestataire, date_piece, echeance, commentaire, version} | `DossierFiche` | A83 |
| 200 | PUT | `/dossiers/{id}/frais/{fid}` | D, A | `FraisEntree` (`version` = celle **du frais**) | `DossierFiche` | A84 |
| 201 | DELETE | `/dossiers/{id}/frais/{fid}` | D, A | `?version=` (celle du frais) | `DossierFiche` | A85 |
| 202 | POST | `/dossiers/{id}/cloturer` | D, A | `{version, alertes_lues}` (`alertes_lues` vaut confirmation : s'il y a des alertes et qu'il est faux → 422 `confirmation_requise`) | `DossierFiche` | A86 |
| 203 | POST | `/dossiers/{id}/rouvrir` | D, A | `{version, motif}` (motif facultatif, au journal ; refusé en période close) | `DossierFiche` | A87 |
| 204 | POST | `/dossiers/{id}/annuler` | D, A | `{version, motif}` (motif **exigé**, 3–300 ; refusé sur un clos et en période close) | `DossierFiche` (statut `annule`, numéro, lignes détachées et frais gardés, marchandise libérée ; un annulé ne se rouvre pas ; un dossier n'est **jamais supprimé**) | A88 |
| 205 | GET | `/export/dossiers` | D, A | mêmes filtres que 187 | xlsx (4 feuilles) | A89 |
| 206 | GET | `/analyse/revient` | D, A | `?axe=&q=&statut=ouvert\|clos&du=&au=&qualite=` (id) `&matieres=` (ids répétés) `&selection=` (JSON) `&composition=&type_fil=&titrage=&couleur=&fournisseur=` (nom) `&detail=` ; axe, sélection, statut inconnus → 422 | `AnalyseRevient` | A90 |
| 207 | GET | `/analyse/revient/qualites/{id}` | D, A | `?du=&au=` | `CoutQualite` | A91 (par id) |
| 208 | GET | `/export/revient` | D, A | mêmes filtres | xlsx | A92 |

### 1.22 Pilotage et analyse (`api/pilotage`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 209 | GET | `/cockpit` | D, A | `?date=` | `Cockpit` {date_reference, kpi [{cle, libelle, valeur, unite, detail, formule, lien, ton}], stock (+ `valeur_magasins_mad`, `kg_machine`), achats (+ `en_retard`), finance, abc, dormant, sourcing, economies (`top[]` avec ids), nb_alertes, alerte_rouge, alertes (avec ids), devises, controles (synthèse)} ; « À faire » et « Évolution » de l'écran viennent d'autres routes (commandes, réceptions…, 231) | B68 |
| 210 | GET | `/valorisation` | D, A | `?date=` | `Valorisation` | B69 |
| 211 | GET | `/opportunites` | D, A | `?date=&meme_couleur=&fenetre_jours=` | `Opportunites` | B70 |
| 212 | GET | `/controles` | D, A | `?date=` | `Controles` {date_reference, synthese, controles [{code, libelle, gravite, garanti, anomalies, conforme, quoi_faire, lien, colonnes [{cle, libelle, unite}], lignes (200 au plus), lignes_total, tronque}]} | B71 |
| 213 | GET | `/prix/historique` | D, A | `?q=&du=&au=` | `HistoriquePrix` {lignes `[PrixPaye]`, total_achats_mad, hausses, fortes_hausses, baisses, seuils} (les indicateurs de l'écran ne se recalculent pas à l'écran) | B72 |
| 214 | GET | `/prix/matrice` | D, A | `?q=` | `MatricePrix` | B75 |
| 215 | GET | `/fournisseurs/performance` | D, A | `?du=&au=` | `PerformanceFournisseurs` {du, au, cible_otif, seuils, lignes, receptions} (les chemins `/fournisseurs/{ident:int}` de 1.8 ne la masquent pas) | B76 |
| 216 | GET | `/export/controles` | D, A | `?date=` | xlsx | B103 |
| 217 | GET | `/export/valorisation` | D, A | `?date=` | xlsx | B104 |
| 218 | GET | `/export/prix` | D, A | `?q=` | xlsx | B105 |
| 219 | GET | `/export/opportunites` | D, A | `?date=&meme_couleur=&fenetre_jours=` | xlsx | B106 |
| 220 | GET | `/export/fournisseurs` | D, A | `?du=&au=` | xlsx | B107 |

### 1.23 Suivi (`api/suivi`)

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 221 | GET | `/signalements` | C | `?a_traiter=` (vrai : en attente ; faux : traités ; absent : tous) `&mes=true` (les miens) `&apres=&limite=` | `Page[SignalementFiche]` (le plus récent d'abord) | B84 |
| 222 | POST | `/signalements` | C | `{matiere_id, texte, urgence}` | `SignalementFiche` (201 ; la direction et les achats sont prévenus) | B85 |
| 223 | POST | `/signalements/{id}/traiter` | D, A | `{reponse}` | `SignalementFiche` (l'auteur est prévenu ; déjà traité → 409) | B86 |
| 224 | GET | `/pieces` | D, A | `?objet=&id=` | `[PieceFiche]` {id, objet, objet_id, nom, type, taille, empreinte, par, par_id, quand} | B87 |
| 225 | POST | `/pieces` | D, A | multipart {objet, id, fichier} | `PieceFiche` | B88 |
| 226 | GET | `/pieces/{id}/fichier` | D, A | — | fichier (`attachment`) ; fichier disparu du disque → **410** `fichier_disparu` | B89 |
| 227 | DELETE | `/pieces/{id}` | D, A | — (pas de `version` : la table n'en a pas) | 204 (retrait logique) ; déjà retirée → 409 | B90 |
| 228 | GET | `/echeancier` | D, A | `?q=&nature=facture\|frais&du=&au=` (le futur est permis) | `Echeancier` {aujourdhui, lignes, par_mois, total_mad, echu_mad, echues, dans_30_jours_mad, a_dater, a_dater_mad, reglees, ecartees} (l'échu se compte quelle que soit la période) | B91 |
| 229 | PUT | `/echeancier/paiement` | D, A | `{genre: facture\|frais, id, payee_le \| null, version, motif}` ; facture par `services.factures.regler` (D4), frais aux mêmes règles ; annuler un règlement (`payee_le: null`) : direction seule (403), `motif` exigé (≥ 3, 422 `motif_requis`) ; date dans le futur, en période close ou avant la pièce → refus | `EcheanceLigne` (+ `etat`) | B92 |
| 230 | GET | `/export/echeancier` | D, A | mêmes filtres | xlsx (feuilles Échéances, À dater, Par mois, Réglées, Écartées) | B109 |
| 231 | GET | `/indicateurs/historique` | D, A | `?du=&au=` | `[IndicateurJour]` | B94 |
| 232 | POST | `/indicateurs/photographier` | D | — | `IndicateurJour` (journalisé) | B99 |
| 233 | GET | `/bilan` | D, A | `?mois=AAAA-MM` (mois valide, passé ou en cours) | `BilanMois` (JSON) : celui du moteur + magasins et métiers (`stock_debut_magasins_kg`, `metiers_debut_kg`, `variation_metiers_kg`, `…_mad`), `du`, `au`, `mois_iso`, `sorties_nettes_kg`, `alerte_rouge` ; les sorties comptent la sortie annulée, l'annulation a sa ligne à part ; l'écart est une fraction | nouveau |
| 234 | GET | `/documents/bilan` | D, A | `?mois=` | HTML A4 (papier à en-tête) | B95 |

### 1.24 Routes ajoutées par la conception des écrans (`ECRANS-PRO.md`) et pour la coexistence

| N° | M | Chemin | Rôles | Entrée | Sortie | ← GMP |
|---|---|---|---|---|---|---|
| 235 | GET | `/controles/{code}` | D, A | `?date=&q=&apres=&limite=` | `PageControle` = `Page` (lignes avec les ids des fiches qu'elles nomment) + {code, libelle, gravite, quoi_faire, lien, colonnes} (détail complet, cherchable ; la liste 212 n'en rend que les 200 premières en le disant) | B71 (détail) |
| 236 | GET | `/export/lots` | C (sans valeur pour L) | mêmes filtres que 107 | xlsx | nouveau |
| 237 | GET | `/export/production` | C | `?onglet=glissant\|realise\|besoins&date=` | xlsx | nouveau |
| 238 | GET | `/export/metiers` | C (valeur masquée pour L) | — | xlsx | nouveau |
| 239 | GET | `/export/inventaires` | D, A | `?statut=` | xlsx | nouveau |
| 240 | GET | `/export/inventaires/{id}` | D, A | — | xlsx (lignes, écarts en kg et en MAD) | nouveau |
| 241 | GET | `/export/operations` | C (sans prix pour L ; types permis au rôle) | `?type=&statut=&q=` | xlsx | nouveau |
| 242 | GET | `/export/plan-achat` | D, A | `?onglet=fournisseurs\|references&q=&date=` + les filtres liés de l'écran : `statut, priorite, abc, fournisseur` (onglet références), `urgence, devise, pays` (onglet fournisseurs) | xlsx (la liste affichée, filtres compris ; 151 reste le classeur complet) | nouveau |
| 243 | GET | `/reprise` | D, T | — | `EtatMiroir` {dernières exécutions, signature de la source, à jour: bool, rapport} | nouveau (coexistence) |
| 244 | POST | `/reprise` | D | `{mode: tout, remplacer_activite: true, confirmation: "REMPLACER"}` | 202 `ExecutionReprise` (tâche ; sauvegarde « avant reprise » d'abord) | nouveau (coexistence) |

Précisions de corps retenues : `POST /operations` accepte `valider: true` (création et validation
dans **une** transaction : déplacer un lot, libérer une quarantaine, retour des machines au
téléphone — fin de l'enchaînement « créer, valider, supprimer si refus » de Gestion MP) ;
`PUT /qualites/{id}` accepte la recette (`recette` facultative) dans le même corps et la même
transaction ; `PUT /metiers/{id}` accepte le montage (`montage` facultatif, versions d'étage
comprises) ; `GET /acces` et `GET /acces/qr` sont ouverts aussi à T ; `GET /echeancier` reçoit
`q` et `nature` ; `GET /lots/disponibles` reçoit `magasin` et `date` ; `GET /export/ordres`
reçoit `vue=consommation` ; `POST /commandes/{id}/approuver` reçoit `date` ; `PUT /dossiers/{id}/lignes/{lid}` accepte `cours: null` (« cours du jour ») ; `GET /dossiers/{id}` porte `a_rattacher` ; `GET /receptions/bobines` reçoit `matiere`. Le `PUT` d'une fiche reste un remplacement complet (l'écran envoie
la fiche entière, y compris pour « désactiver ») : pas de corps partiel.

**Total : 246 routes PRO** (dont 28 classeurs xlsx — modèle du tableur compris —, 4 documents HTML imprimables, 1 SVG), plus le
service de l'écran (`GET /{chemin}` hors API, B « — »), `/api/docs` et `/api/openapi.json`.

---

## 2. Changements de règles portés par les routes

| Route(s) PRO | Changement par rapport à Gestion MP | Raison |
|---|---|---|
| Toutes | Refus en 422 (saisie) / 409 (état) / 404 ; plus de 400 ni de messages en minuscules (`analyse_import`, `pilotage`, `production_plan`) | convention unique (incohérences A.12-5, B.13-10) |
| Toutes les écritures de fiche | `version` exigée, 409 `conflit_version` | remplace l'empreinte (F10) et l'absence de contrôle |
| 8 | Liste des visages réservée au poste local ou à un appareil enrôlé | exposition réseau (R7, B.13-17) |
| 11 | Déconnexion exige l'en-tête anti-falsification | B.13-17 |
| 14, 18 | Changer un code ferme les autres sessions | B.13-16 |
| 23 | Alimentation : 403 ; achats : lecture | « aucun prix, ni réglage chiffré » (coordinateur ; REGLAGES § 9 n° 7) |
| 26 | Clôture de période : route dédiée, motif obligatoire, refus d'avancer la date au-delà d'hier, journal avant/après | REGLAGES § 9 n° 13 |
| 27–30 | Alimentation : 403 sur les devises et cours ; pas de ligne d'historique sans changement ; MAD inactif refusé | coordinateur ; B.13-16 |
| 34 | Une seule lecture des postes (fin du doublon court/complet) ; ouverte à D, A | A.12-3 |
| 64 | Alimentation : nom et pays seulement | A.12-2 |
| 75 | `POST /articles/composer` devient `GET /matieres/reference` | lecture (A.12-1) |
| 79–80 | Import tableur : mêmes contrôles que la fiche, doublons, bornes, longueurs, `version` par ligne, empreinte d'aperçu ; colonne « Vider » explicite | B.13-14 |
| 82 | Facteurs de coût inclus pour D, A (plus de 403 sur un second appel) | A.12-3 |
| 99–100 | Montage : `version` d'étage, effet confirmé (`confirme_effet_kg` = effet calculé, sinon 409 « l'effet a changé »), trace en table ; 99 ne remplace que les étages envoyés ; étage hors du métier → 404 | F19, empreinte |
| 103, 104, 145, 149, 150, 209 | `statut` et `statut_couverture` rendus en **codes** (`RUPTURE`, `CRITIQUE`, `URGENT`, `ATTENTION`, `OK`, `NON_CONSOMMEE`) et `action` d'une ligne de stock en `CREER_BC` \| `AUCUNE` (`null` pour l'alimentation) au lieu des libellés à émoji de Gestion MP (« 🔴 CRITIQUE », « 📝 Créer BC - … ») : l'écran les traduit (`lib/statuts.ts`), les classeurs les écrivent en clair ; `relance` du plan d'achat sans émoji | vocabulaire de la base (lot RESTES3) |
| 103, 104 | `/stock?date=` passé : le fil monté **de ce soir-là** (historique des montages) est compté, comme la Valorisation (210) ; chaque ligne porte `role_id`, `fournisseur_id` ; `EtatStock.magasin_ids` {code → id} (`par_magasin` reste par code) | deux pages, un chiffre (E-06, U8) ; liens de l'écran (lot RESTES3) |
| 105, 108 | `MouvementLigne.devise` à `null` hors direction et achats | an. 27 : aucune devise lue par l'alimentation (lot RESTES3) |
| 112 | `Tracabilite` + `matiere_id`, `ordre_id` ; chaque `EtapeTracee` + `matiere_id`, `ordre_id`, `document_type`, `document_id` | liens de l'écran (lot RESTES3) |
| 101 | Origine « bureau » pour tout montage des routes 97 et 99, même d'un seul étage (`etage` nul) ; « téléphone » pour la route 100 | origine réelle (lot RESTES3) |
| 135 | `OrdreResume.metier` = « CODE · Nom » (le code seul sans nom distinct) | champ serveur unique (ECRANS-PRO ; lot RESTES3) |
| 152, 153 | `en_retard`, `arrivee_attendue`, `arrivee_sous_7_jours`, `kg_en_quarantaine` comptés au serveur ; la fiche dit `promesse_figee` ; chaque ligne garde `en_quarantaine` (reçu sous réserve, attendu jusqu'à sa libération) | P1-11, D-02 (lots RESTES3, V1) |
| 176 | `Pesee.numero` d'un brouillon = « Brouillon » | vocabulaire « brouillon n° 6 » retiré (lot RESTES3) |
| 175, 187, 228 | La recherche trouve un numéro à la ponctuation près (« FA-2026/117 » = « FA-2026-117 ») | lot RESTES3 (F5) |
| 222, 223 | Lien de la notification d'un besoin : `/cockpit?signalement=` pour la direction, `/accueil?signalement=` pour les achats, `/atelier` pour l'alimentation | la direction n'a pas « Ma journée » (lot RESTES3) |
| 6, 20 | QR en SVG **avec** l'espace de noms (`xmlns`) : il s'affiche dans une `<img>` | lot RESTES3 (F8) |
| 242 | Filtres liés de l'écran appliqués au classeur : `statut`, `priorite`, `abc`, `fournisseur` (références), `urgence`, `devise`, `pays` (fournisseurs), valeurs affichées | ECRANS-PRO 4.28 (lot RESTES3) |
| 117 | Plus de numéro de lot interne pris d'avance : case `lot_interne` | A.12-11, M65 |
| 123 | Validation groupée : ce que le rôle ne peut pas valider est rendu dans `ignores` avec la raison | A.12-4 |
| 128–132 | Suspension limitée au périmètre ; abandon conservé ; champ absent = inchangé | N3 ; B.13-15 |
| 245 | Un inventaire validé s'annule (contre-passation unique, motif obligatoire, numéro gardé, état `annule`) au lieu de rester définitif | Gestion MP corrigé, étape 17 (U19) |
| 141 | Annuler un ordre supprime ses brouillons de retour et le dit | B.13-13 |
| 154 | « Prix du catalogue à confirmer » rendu effectif (prix catalogue posés, non confirmés) ; sinon bon sans prix | ECRANS synthèse 7 |
| 158 | Approbation datée du jour réel d'envoi | A.12-15 |
| 160 | Confirmation des prix refusée sur un brouillon non parti, sur un `a_approuver` sans numéro (il n'est pas parti : le retour en brouillon ne s'applique donc jamais) et sur un bon soldé ou annulé | A.12-14 |
| 161 | Jalons : champ absent = inchangé ; refusé sur un bon soldé ou annulé | A.12-16 |
| 162 | Solder : motif facultatif gardé (`solde_origine = manuel`) | colonne réelle |
| 167 | La lecture ne recale plus des objets en mémoire : le recalage est calculé (`services/receptions.recalage`) et rendu, il s'écrit à la modification et à la validation | A.12-27 |
| 169 | Un camion en deux devises = une requête, une transaction | ECRANS synthèse 9 |
| 172 | Un blocage garde son code à la validation : 409 pour un état (excédent, bon clos ou pas parti, inventaire en cours, période close), 422 pour une saisie (deux postes qui valident la même réception : [200, 409], Gestion MP [200, 422]) | convention PRO |
| 173 | Une réception toute refusée s'annule (statut `annulee`, aucun mouvement) ; annuler une validée exige un motif (3–300) | A.12-12 ; ECRANS-PRO 4.17 |
| 174 | Facture : sémantique unique (absent = inchangé), réservée à une réception validée (le brouillon porte sa facture dans son corps) | A.12-17 |
| 184 | Une réclamation close se complète encore (réponse, montant obtenu : l'avoir arrive après la clôture) sans changer son issue | R20r |
| 190–191 | `PUT` n'accepte que ce qu'il modifie ; `date_arrivee` peut se vider | A.12-19 |
| 192 | Rattacher par facture seulement (plus de `reception_ligne_ids`) | un dossier = une facture = une livraison (I3) |
| 204 | Annuler un dossier au lieu de le supprimer, pour **tout** dossier, même saisi à la main (numéro gardé, frais sortis du coût, motif exigé) : plus aucune suppression | DONNEES 11, B-02 |
| 205–208 | Statuts `ouvert`/`clos` en minuscules partout ; dates en vraies dates Excel ; titre corrigé | A.12-8/9/10 |
| 212 | Écart (%) sur une seule échelle (pourcentage) ; synthèse = contrôles en anomalie **et** lignes | CONTROLES § 6 n° 1, 27 |
| 212, 235 | C28 : délai lu dans `delai_frais_import_jours` (30 j), « …sans frais hors TVA » ; C29 : tolérance lue dans `toler_tva_import` (5 %), « TVA d'importation à plus de 5 % de la TVA attendue (20 % de la valeur en douane, droits et TPI compris) » | Gestion MP corrigé (DEFAUTS E-10) |
| 216–220, 52, 106 | Exports homogènes : vraies dates, gravités traduites, mêmes filtres que l'écran, `date` acceptée partout | B.13-18 |
| 229 | Un frais réglé ne redevient dû que par « annuler le règlement » explicite ; annuler un règlement (facture ou frais) : direction seule, motif exigé | I20 ; D4 |
| 233 | Bilan : mois invalide → 422 ; kilos et dirhams sur la même base (annulations sur leur ligne) ; stock sur les métiers compté | B.13-9, 11 |
| 234, 164, 114, 133 | Gabarits Jinja2 sur le papier à en-tête | PLAN |

---

## 3. Correspondance de chaque route de Gestion MP

### 3.1 Partie A (97 routes)

| GMP | Route GMP | → PRO |
|---|---|---|
| A1 | GET /classification | 57 |
| A2 | POST /classification/roles | 58 |
| A3 | PUT /classification/roles/{code} | 59 (par id) |
| A4 | DELETE /classification/roles/{code} | 60 |
| A5 | POST /classification/{nom} | 61 (`{liste}` au pluriel) |
| A6 | PUT /classification/{nom}/{code} | 62 (par id) |
| A7 | DELETE /classification/{nom}/{code} | 63 |
| A8 | GET /fournisseurs | 64 |
| A9 | POST /fournisseurs | 66 |
| A10 | PUT /fournisseurs/{fid} | 67 |
| A11 | DELETE /fournisseurs/{fid} | 68 |
| A12 | GET /articles | 70 |
| A13 | POST /articles | 72 |
| A14 | PUT /articles/{aid} | 73 |
| A15 | DELETE /articles/{aid} | 74 |
| A16 | POST /catalogue/classer?appliquer= | 76 (aperçu) + 77 (appliquer) |
| A17 | POST /articles/composer | 75 |
| A18 | GET /qualites | 82 |
| A19 | GET /qualites/facteurs-cout | **fondue dans 82** (champ `facteurs_cout` pour D, A) |
| A20 | POST /qualites | 84 |
| A21 | PUT /qualites/{qid} | 85 |
| A22 | DELETE /qualites/{qid} | 86 |
| A23 | PUT /qualites/{qid}/recette | 87 (corps objet, motif et version dans le corps) |
| A24 | POST /qualites/{qid}/versions/{vid}/restaurer | 89 |
| A25 | PUT /qualites/{qid}/plan | 90 |
| A26 | GET /magasins | 31 |
| A27 | POST /magasins | 32 |
| A28 | PUT /magasins/{gid} | 33 |
| A29 | GET /metiers | 94 |
| A30 | GET /montage/references | 102 |
| A31 | POST /metiers | 96 |
| A32 | PUT /metiers/{mid} | 97 |
| A33 | DELETE /metiers/{mid} | 98 |
| A34 | PUT /metiers/{mid}/fils | 99 |
| A35 | PUT /metiers/{mid}/etages/{etage} | 100 |
| A36 | GET /postes-frais | 34 |
| A37 | GET /export/matieres | 81 |
| A38 | GET /export/fournisseurs/fiches | 69 |
| A39 | GET /export/qualites | 93 (colonne « En service » au lieu de « Fabriquée » + colonne « Fabriquée » vraie) |
| A40 | GET /postes-frais/complet | **fondue dans 34** |
| A41 | POST /postes-frais | 35 |
| A42 | PUT /postes-frais/{code} | 36 |
| A43 | DELETE /postes-frais/{code} | 37 |
| A44 | GET /codes-douaniers | 38 |
| A45 | POST /codes-douaniers | 39 |
| A46 | PUT /codes-douaniers/{code} | 40 |
| A47 | DELETE /codes-douaniers/{code} | 41 |
| A48 | GET /commandes | 152 (+ 153 pour la fiche) |
| A49 | POST /commandes | 154 |
| A50 | PUT /commandes/{cid} | 155 |
| A51 | POST /commandes/{cid}/envoyer | 157 |
| A52 | POST /commandes/{cid}/approuver | 158 |
| A53 | POST /commandes/{cid}/renvoyer | 159 |
| A54 | POST /commandes/{cid}/prix | 160 |
| A55 | PUT /commandes/{cid}/expedition | 161 |
| A56 | POST /commandes/{cid}/solder | 162 |
| A57 | POST /commandes/{cid}/rouvrir | 163 |
| A58 | DELETE /commandes/{cid} | 156 |
| A59 | GET /commandes/{cid}/impression | 164 |
| A60 | GET /receptions | 167 (+ 168) |
| A61 | POST /receptions | 169 |
| A62 | PUT /receptions/{rid} | 170 |
| A63 | DELETE /receptions/{rid} | 171 |
| A64 | POST /receptions/{rid}/valider | 172 |
| A65 | POST /receptions/{rid}/annuler | 173 |
| A66 | PUT /receptions/{rid}/facture | 174 |
| A67 | POST /lots/numero-interne | **morte** : un numéro pris d'avance troue la série LOT (M65) ; remplacée par la case `lot_interne` des lignes (169, 117, 130), numéro donné à la validation |
| A68 | GET /factures | 175 (désormais lue par l'écran : choix de facture des importations, échéancier) |
| A69 | GET /brouillons | 122 |
| A70 | POST /brouillons/valider | 123 |
| A71 | GET /dossiers | 187 |
| A72 | GET /dossiers/{did} | 189 |
| A73 | GET /dossiers-a-rattacher | 188 |
| A74 | POST /dossiers | 190 |
| A75 | PUT /dossiers/{did} | 191 |
| A76 | POST /dossiers/{did}/rattacher | 192 |
| A77 | POST /dossiers/{did}/ligne-manuelle | 193 |
| A78 | PUT /dossiers/{did}/lignes/{lid} | 194 |
| A79 | PUT /dossiers/{did}/cours | 196 |
| A80 | POST /dossiers/{did}/cours-des-bons | 197 |
| A81 | DELETE /dossiers/{did}/lignes/{lid} | 195 |
| A82 | POST /dossiers/{did}/detacher | 198 |
| A83 | POST /dossiers/{did}/charges | 199 |
| A84 | PUT /dossiers/{did}/charges/{cid} | 200 |
| A85 | DELETE /dossiers/{did}/charges/{cid} | 201 |
| A86 | POST /dossiers/{did}/cloturer | 202 |
| A87 | POST /dossiers/{did}/rouvrir | 203 |
| A88 | DELETE /dossiers/{did} | 204 |
| A89 | GET /export/dossiers | 205 |
| A90 | GET /importations/analyse/revient | 206 |
| A91 | GET /importations/analyse/qualite/{code} | 207 (par id) |
| A92 | GET /export/revient | 208 |
| A93 | GET /export/commandes | 166 |
| A94 | GET /export/receptions | 178 |
| A95 | GET /export/receptions/pesees | 179 |
| A96 | GET /export/receptions/bobines | 180 |
| A97 | GET /export/commandes/{cid}/bon | 165 |

### 3.2 Partie B (109 routes)

| GMP | Route GMP | → PRO |
|---|---|---|
| B1 | GET /sante | 1 |
| B2 | GET /etat | 2 |
| B3 | GET /visages | 8 |
| B4 | POST /installation | 9 |
| B5 | POST /connexion | 10 |
| B6 | POST /deconnexion | 11 |
| B7 | GET /moi | 12 |
| B8 | POST /moi/code | 14 (PUT) |
| B9 | GET /utilisateurs | 15 |
| B10 | POST /utilisateurs | 16 |
| B11 | PUT /utilisateurs/{uid} | 17 + 18 (le code se change par sa route) |
| B12 | GET /journal | 49 |
| B13 | GET /journal/valeurs | 50 |
| B14 | GET /parametres | 23 |
| B15 | PUT /parametres | 24 (+ 26 pour `date_cloture`) |
| B16 | GET /parametres/historique | 25 (les cours vont en 28) |
| B17 | GET /devises | 27 |
| B18 | GET /devises/{code}/historique | 28 |
| B19 | PUT /devises | 29 (création) + 30 (modification) |
| B20 | GET /sauvegardes | 43 |
| B21 | POST /sauvegardes | 44 |
| B22 | GET /etat-serveur | 4 |
| B23 | POST /sauvegardes/{nom}/restaurer | 45 |
| B24 | GET /mouvements | 105 |
| B25 | GET /soldes | 107 |
| B26 | GET /lots/{lid} | 108 |
| B27 | GET /lots/scan | 110 |
| B28 | GET /acces | 5 |
| B29 | GET /acces/qr | 6 |
| B30 | GET /lots/etiquettes | 114 |
| B31 | GET /controles/soldes | 113 |
| B32 | GET /operations/motifs | 42 |
| B33 | GET /operations | 115 |
| B34 | GET /operations/{oid} | 116 |
| B35 | POST /operations | 117 |
| B36 | PUT /operations/{oid} | 118 |
| B37 | DELETE /operations/{oid} | 119 |
| B38 | POST /operations/{oid}/valider | 120 |
| B39 | POST /operations/{oid}/annuler | 121 |
| B40 | GET /inventaires | 124 |
| B41 | GET /inventaires/defauts | 125 |
| B42 | GET /inventaires/a-compter | 126 |
| B43 | GET /inventaires/{iid} | 127 |
| B44 | POST /inventaires | 128 |
| B45 | POST /inventaires/{iid}/comptage | 129 + 130 |
| B46 | POST /inventaires/{iid}/valider | 131 |
| B47 | DELETE /inventaires/{iid} | 132 |
| B48 | GET /inventaires/{iid}/feuille | 133 |
| B49 | POST /bons/proposition | 134 |
| B50 | GET /bons | 135 |
| B51 | POST /bons | 137 |
| B52 | PUT /bons/{bid} | 138 |
| B53 | DELETE /bons/{bid} | 139 |
| B54 | POST /bons/{bid}/valider | 140 |
| B55 | POST /bons/{bid}/annuler | 141 |
| B56 | GET /bons/{bid} | 136 |
| B57 | GET /bons/{bid}/lots-sortis | 142 |
| B58 | GET /export/sorties | 144 |
| B59 | GET /production/plan | 145 |
| B60 | PUT /production/plan | 146 |
| B61 | GET /production/realise | 147 |
| B62 | GET /production/besoins | 148 |
| B63 | GET /stock | 103 |
| B64 | GET /besoins | **morte** : orpheline (aucun écran), doublon simplifié de 148 (même `plan_mensuel` + `besoins_mensuels`, rendus par 148 et 145) |
| B65 | GET /nomenclature | 92 |
| B66 | GET /plan-achat | 149 |
| B67 | GET /plan-achat/fournisseur/{nom} | 150 |
| B68 | GET /cockpit | 209 |
| B69 | GET /valorisation | 210 |
| B70 | GET /opportunites | 211 |
| B71 | GET /controles | 212 (+ 235 pour le détail complet d'un contrôle) |
| B72 | GET /prix/historique | 213 |
| B73 | GET /receptions/pesees | 176 |
| B74 | GET /receptions/bobines | 177 |
| B75 | GET /prix/matrice | 214 |
| B76 | GET /fournisseurs/performance | 215 |
| B77 | GET /lots (moteur) | **morte** : orpheline, double vue des lots (« (sans lot) », `negatif`) ; la vue lot par lot du moteur sert C27 et la traçabilité en interne (`calcul/lots.stock_par_lot`), la vue d'écran est 107 |
| B78 | GET /lots/disponibles | 111 (désormais utilisée par la saisie d'ordre et la proposition) |
| B79 | GET /tracabilite | 112 |
| B80 | GET /ordres-fabrication | 143 |
| B81 | GET /reclamations | 181 |
| B82 | POST /reclamations | 183 |
| B83 | PUT /reclamations/{rid} | 184 + 185 + 186 |
| B84 | GET /signalements | 221 |
| B85 | POST /signalements | 222 |
| B86 | POST /signalements/{sid}/traiter | 223 |
| B87 | GET /pieces/{objet}/{oid} | 224 |
| B88 | POST /pieces/{objet}/{oid} | 225 |
| B89 | GET /piece/{pid}/fichier | 226 |
| B90 | DELETE /piece/{pid} | 227 |
| B91 | GET /echeancier | 228 |
| B92 | PUT /echeancier/paiement | 229 |
| B93 | GET /qualites/{qid}/versions | 88 |
| B94 | GET /indicateurs/historique | 231 |
| B95 | GET /bilan | 234 (document) + 233 (données) |
| B96 | GET /import/matieres/modele | 78 |
| B97 | POST /import/matieres | 79 + 80 |
| B98 | GET /courriel/apercu | 48 |
| B99 | POST /indicateurs/photographier | 232 |
| B100 | GET /export/pilotage | 151 |
| B101 | GET /export/mouvements | 106 |
| B102 | GET /export/bon-de-commande/{cid} | **morte** : doublon jamais appelé, en français et **avec les prix**, contraire à la décision A22 de Mohamed ; le bon fournisseur est 164 / 165 |
| B103 | GET /export/controles | 216 |
| B104 | GET /export/valorisation | 217 |
| B105 | GET /export/prix | 218 |
| B106 | GET /export/opportunites | 219 |
| B107 | GET /export/fournisseurs | 220 |
| B108 | GET /export/journal | 52 |
| B109 | GET /export/echeancier | 230 |
| — | GET /{chemin} (écran) | servi par Caddy (Docker) ou par l'application (`main.py`, poste Mac) : fichiers de `frontend/dist`, repli `index.html`, `/api/*` inconnu → 404 JSON |

**Bilan** : 206 routes de Gestion MP → **202 reprises** (dont 8 éclatées en deux ou trois routes
plus claires — A16, B11, B15, B19, B45, B83, B95, B97 — et 2 fondues dans une voisine — A19,
A40), **4 mortes justifiées** (A67, B64, B77, B102). PRO compte 246 routes : 200 cibles directes
des routes reprises, 8 nées d'un éclatement, **26 nouvelles** (contexte, données brutes,
`PUT /moi`, appareils ×4, tâches, courriels, historique, notifications ×3, recherche, fiches à
adresse stable ×7, versions du plan, montages, commentaire de lot, fiche stock d'une matière,
bilan en JSON), **8 ajoutées** par la conception des écrans (235–242 : détail d'un contrôle, sept exports), **2 pour la coexistence** avec Gestion MP (243–244 : état et rafraîchissement du miroir), et **1 reprise
de Gestion MP corrigé** (245 : annulation d'un inventaire validé), et **1 ajoutée par le lot RESTES3** (246 : brouillons qui empêcheraient de clore une période).

---

## 4. Matrice des droits

Déclarée une fois (`securite/matrice.py`, générée depuis les dépendances des routes et exportée en
`tests/matrice_droits.csv`) : 246 routes × {anonyme, D, A, L, T} → code attendu. L'essai
`test_matrice_droits` la rejoue entièrement (paramètres remplis par les fabriques) ; une route
nouvelle absente de la matrice fait échouer l'essai ; l'essai structurel
`test_toute_route_declare_ses_roles` échoue si une route (hors 1, 2, 8, 9, 10, 22) n'a pas de
`droit(...)`. Résumé par rôle :

| Rôle | Routes permises | Interdites notables |
|---|---|---|
| Anonyme | 1, 2, 8, 9, 10, 22 | tout le reste (401) |
| Direction | toutes les routes métier et techniques (239 hors routes publiques) | aucune |
| Achats | lectures et écritures achats, réceptions, importations, stock (sauf retour machine), inventaires, référentiels matières/fournisseurs/classification (valeurs), devises, pilotage, suivi | approbation (158, 159), plan et recettes (84–90, 146), rôles, postes, codes, magasins, métiers (écriture), montage, ordres (écriture), comptes, sauvegardes, journal, période close |
| Alimentation | lectures « C » (prix filtrés), ordres, retours machine, transferts, mise en quarantaine, montage, signalements, notifications, recherche | tout ce qui est D/A : commandes, réceptions, importations, plan d'achat, pilotage, réglages, devises, exports chiffrés |
| Administrateur | 3, 4, 11–25 (techniques), 43–55 | toute route métier (403) : il ne lit ni stock, ni prix, ni documents |
