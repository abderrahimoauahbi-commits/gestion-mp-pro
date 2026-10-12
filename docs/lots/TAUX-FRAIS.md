# Lot TAUX-FRAIS — le taux d'un frais de dossier

Branche `lot-taux-frais` (depuis main 36e3e1b). Révision Alembic **0006** (réservée par le
coordinateur). `make verifier` vert : 2889 essais serveur (5 sautés), 842 essais d’écran (1 sauté).

## La demande (Mohamed, 12 octobre 2026)
Importations › un dossier › Frais : entre « Poste » et « Montant (MAD) », un champ **Taux (%)**
(TVA 20 %, droits 2,5 % ou 3 %…). Le logiciel calcule le montant ; la douane arrondit parfois :
l'utilisateur garde le montant calculé ou le corrige. **Une fois enregistré, c'est fini** : même
dossier rouvert, le montant n'est jamais recalculé.

## Règles appliquées
1. **Base** (MAD), calculée à l'écran sur la fiche déjà servie (`frontend/.../tauxFrais.ts`) :
   - « Porte sur » tout le dossier → somme des marchandises ; une marchandise → elle seule ;
   - poste de nature `tva` : valeur en douane + droits + TPI déjà saisis (postes de nature
     `droits` et `tpi` : la liste des frais pour le dossier, `frais_par_poste` de la ligne pour
     une marchandise) — comme `calcul.importations.tva_attendue` côté serveur ;
   - tout autre poste : la valeur en douane (`LigneDossier.valeur_douane_mad` = marchandise au
     cours payé + sa part de fret et d'assurance) ;
   - note sous le champ Taux : « 20 % de 69 804,00 MAD (valeur en douane + droits + TPI) ».
2. **Pré-remplissage** (ligne d'ajout) : tant que le montant n'est pas tapé, montant =
   arrondi(base × taux / 100, 2) (`lib/format.arrondi`, demi éloigné de zéro), recalculé quand le
   taux, le poste ou « Porte sur » changent. Tapé : « à la main » (`montant_a_la_main`), plus
   recalculé ; vidé : retour au calcul ; un taux changé ensuite recalcule (geste explicite).
   « Proposer les droits » pose un montant à la main (le changement de poste ne l'efface pas).
3. **Serveur** : `dossier_frais.taux NUMERIC(7,4)` vide permis, CHECK
   `ck_dossier_frais_taux_borne` (`taux IS NULL OR (taux > 0 AND taux <= 100)`) et
   `ck_dossier_frais_taux_nombre` (NaN). `FraisEntree.taux` facultatif (`gt=0`, `le=100`,
   4 décimales au plus, sinon 422), `FraisSaisi.taux`, `FraisDossier.taux` en sortie. Le montant
   reçu est enregistré **tel quel** ; aucun code serveur ne lit le taux pour calculer. Journal :
   « 01/26 · TVA 12 001,37 MAD (20 %) » ; la photo d'audit porte `taux` (différences avant/après).
4. **Frais rouvert** (modification en ligne du tableau, déjà existante) : colonne « Taux »
   (champ `NombreEnregistre`, entre Poste et Montant) ; le montant enregistré s'affiche sans
   recalcul ; un taux changé (en quittant le champ) recalcule le montant sur la base du frais et
   enregistre les deux ; un taux vidé ne touche pas au montant ; une base nulle laisse le montant.
   Frais réglé ou dossier non modifiable : lecture « 20 % » (ou « — »).
5. **Exports** : feuille « Frais » du classeur des dossiers (route 205) : colonne « Taux » avant
   « Montant MAD », fraction au format `0.00##%`, vide sans taux. L'export CSV du tableau de
   l'écran prend la colonne d'office. L'historique lit `taux` « Taux (%) ».
6. **Droits** : aucune route nouvelle, matrice inchangée (`make matrice` sans écart). Le rôle
   alimentation ne voit pas les importations (403) ; la clé `frais` est de toute façon monétaire.

Cours payé (onglet Marchandises) : inchangé. Vérifié par essai : un cours payé passé de 10 à 12
porte la valeur en douane de 60 000 à 72 000 MAD, le frais à taux garde son montant.

## Fichiers
- Serveur : `migrations/versions/0006_taux_des_frais.py` ; `modeles/types.py` (`TAUX_FRAIS`
  7,4) ; `modeles/importations.py` ; `api/importations/schemas.py`, `schemas_fiche.py` ;
  `services/importations/frais.py`, `modele.py`, `parties.py` ; `exports/importations.py`.
- Essais serveur : `tests/test_importations_taux.py` (10) ; `tests/test_migrations.py`
  (aller-retour 0006, liste des révisions) ; `tests/modele_cas.py` (cas du CHECK).
- Écran : `pages/importations/tauxFrais.ts` (base, montant, note), `AjoutFrais.tsx`,
  `VoletFrais.tsx`, `useDossier.ts`, `Importations.module.css`, `donneesEssai.json` (`taux`) ;
  `composants/documents/libellesHistorique.ts` ; `lib/types.gen.ts` régénéré (depuis l'OpenAPI
  de la branche, pas du serveur 8050) ; essais `pages/importations/TauxFrais.test.tsx` (7).
- Documents : MODELE-DONNEES § 3.8.3 et § 11, API-PRO route 199, ECRANS-PRO § 5.9, aide.json →
  NOTICE.md.

## À savoir pour les lots suivants
- `make types` lit par défaut l'OpenAPI du serveur 8050 (main en service) : pour une branche,
  générer l'OpenAPI depuis `creer_application().openapi()` dans un fichier, puis
  `scripts/generer_types.sh <fichier>`.
- Le taux n'est qu'une mémoire : ne jamais en tirer un montant côté serveur (contrôles, reprise,
  analyses), le montant saisi fait foi.
