# Lot SAUVEGARDES-CALENDRIER — la nature des sauvegardes, et leurs heures

Branche `sauvegardes-calendrier` (depuis main 81bddb5). Révision Alembic **0010**. Aucune route
nouvelle ; trois descriptions de champs de la route 43 changées (types de l'écran régénérés).

## La demande (Mohamed, 15 octobre 2026 — DECISIONS X7, revirement R8)

« Sauvegarde : il faut indiquer la nature de la sauvegarde : manuelle, quotidienne, hebdomadaire
et mensuelle, en plus des autres… afin que je puisse m'y retrouver. La sauvegarde quotidienne
doit se faire vers 22H00 et l'hebdomadaire le dimanche, la mensuelle fin de mois vers 22H00. »

Précision du 15/10 : PRO sera aussi installé sur un **serveur** (Docker, systemd) — les heures
sont celles de l'usine même si le système est en UTC, et la copie externe y est indispensable.

## Mesure avant

- Une seule automatique, `quotidienne`, faite **au premier passage de la tâche après minuit** (ou
  au démarrage) : chez Mohamed, les quotidiennes du 9 au 15 octobre sont à 11:11, 10:23, 04:13,
  08:18, 08:05, 08:39 et 00:05 — l'heure dépend du réveil du Mac, jamais du soir.
- Écran : la colonne « Nature » dit « **automatique** » pour toutes les automatiques ; rien pour
  trier. Le dossier en service compte 44 fichiers, dont 31 « avant une mise à jour » ; l'écran
  n'en listait que les **30** plus récents (les plus anciens invisibles).
- Rotation : 14 quotidiennes + la première quotidienne de chacun des 12 derniers mois ; KPI
  « 14 jours, puis une par mois sur 12 mois ».

## Cause

L'ancienne règle (X2, 03/10, héritée de Gestion MP X5–X6) : « si le fichier du jour n'existe pas,
le faire » ; la mensuelle n'était qu'une quotidienne gardée plus longtemps, sans nom à elle.

## Changement

1. **Trois genres automatiques, chacun son fichier** : `quotidienne`, `hebdomadaire`,
   `mensuelle` (`sauvegarde_outils.GENRES`, `LIBELLES` en clair : « quotidienne »,
   « hebdomadaire », « mensuelle » ; les autres inchangés). Registre : `GenreSauvegarde` +
   `hebdomadaire`, `mensuelle`, **révision 0010** (CHECK `ck_sauvegarde_genre_enum` remplacé ;
   retour arrière : les deux genres retirés du registre, fichiers laissés).
2. **Calendrier** (`services/sauvegarde_calendrier.py`, fonctions pures) : une échéance par genre
   à **22:00 heure de l'usine** (`horloge.FUSEAU`) — chaque jour ; chaque dimanche ; le dernier
   jour du mois. Une automatique est **due** dès que la dernière échéance passée de son genre n'a
   aucune sauvegarde de ce genre faite depuis : faite entre 22:00 et 22:15 par la boucle de
   15 minutes, **rattrapée** une seule fois au passage suivant si le Mac (ou le serveur) était
   éteint, au plus une de chaque genre au premier démarrage.
3. **Tâche** (`taches/sauvegarde_du_jour.py` → `sauvegarde.automatiques()`) : les genres dus, dans
   l'ordre quotidienne, hebdomadaire, mensuelle (trois fichiers un dimanche 31), puis la purge.
   Une copie de sécurité manquée n'empêche plus les genres suivants : les fichiers sont faits, la
   tâche finit en échec (503, alerte rouge) ; au passage suivant la copie manquante de la plus
   récente de chaque genre est refaite (comme avant pour la quotidienne).
4. **Conservation** (`calendrier.a_effacer`, dossier **et** copie externe) : 14 quotidiennes,
   8 hebdomadaires, 12 mensuelles, **la mensuelle de fin décembre jamais effacée** (reconnue à son
   échéance : celle faite le 31/12 à 22 h ou rattrapée début janvier) ; manuelles, « avant-* » et
   base vide de référence jamais. Les anciennes quotidiennes (dont celles gardées comme « première
   du mois ») suivent la règle des 14 : la base n'est en service que depuis le 9/10.
5. **Alerte** « Aucune sauvegarde récente » : inchangée, 26 h, sur les sauvegardes de cette base
   (toutes natures). D'un soir à l'autre il s'écoule au plus 24 h 15 : essai à 22:14 la veille /
   22:13 le soir même → pas d'alerte ; à 27 h → alerte.
6. **Écran** (Administration › Sauvegardes) : Nature en clair ; **filtre « Nature : toutes »**
   au-dessus du tableau, puis chaque nature présente avec son nombre, dans l'ordre quotidienne,
   hebdomadaire, mensuelle, manuelle, avant… (le filtre lié standard des listes, A1/M75 : il gagne
   deux options génériques, `tous` = « toutes » et `rang` = ordre métier) ; compteur « n / total » ;
   tri par date inchangé. KPI « Sauvegardes conservées » : « à 22 h : chaque soir (14 jours), le
   dimanche (8 semaines), le dernier jour du mois (12 mois, fin décembre gardée) » ; `POLITIQUE`
   (note de la carte) et l'aide `sauvegarde_conservees` disent la même règle. L'écran liste
   désormais les **100** plus récentes (au lieu de 30 : les seules automatiques en gardent 34).
7. **Heure de l'usine sur un serveur** : rien ne lit le fuseau du système ; essai lancé dans un
   sous-processus `TZ=UTC`, `TZ=Asia/Tokyo`, `TZ=America/New_York`, usine `Africa/Casablanca` ou
   `Europe/Paris` : échéances, sauvegardes dues, nom du fichier et `horloge.maintenant()` à l'heure
   de l'usine.
8. **Docs** : EXPLOITATION § 3.1, § 3.2 (copie externe **indispensable** sur un serveur, 22 h de
   l'usine), § 7 ; DECISIONS X7 et R8 (X2 garde sa trace) ; REGLES X6 (note PRO) ; ARCHITECTURE,
   MODELE-DONNEES (0010), ECRANS-PRO, LOTS-DE-TRAVAIL. `essais/stress/app_figee.py` accepte un
   instant (`GESTIONMPPRO_STRESS_DATE=2030-03-31T22:05`) pour l'épreuve d'écran.
   `outils/verifier_heritage.py` : aucun essai hérité ne portait l'ancienne purge (rien à adapter).

## Essais

`tests/test_sauvegarde_calendrier.py` (horloge fixée) : quotidienne pas due à 21:59:59, due à
22:00, une seule par soir ; deux soirs manqués → une seule au démarrage du matin, puis 22 h ;
hebdomadaire le dimanche 22:00 seulement, rattrapée le lundi ; mensuelle les 31/10, 30/11,
28/02/2027, 29/02/2028, 31/12 à 22:00, pas la veille ; premier démarrage : au plus une de chaque ;
système en UTC/Tokyo/New York ; purge 14/8/12 avec fin décembre gardée (dont une rattrapée le
2 janvier), manuelles et avant-* jamais, archives parties avec leur dump, copie identique ; vrai
`pg_dump` un dimanche 31 janvier 2027 : rien à 21:59, trois fichiers à 22:05, rien à 22:20, copies
refaites ; alerte d'un soir à l'autre ; aller-retour de 0010. Les anciens essais de purge « 14 + 12 »
et de « quotidienne une fois par jour » de `test_sauvegarde.py` sont remplacés par ceux-ci.
Écran (vitest, `Administration.test.tsx`) : natures en clair, options du filtre et leurs nombres,
filtre posé (2 / 6), texte du KPI.

## Mesure après (preuve à l'écran)

Copie de la base « 3 ans » (`gestion_mp_pro_stress_essai` copiée, migrée à 0010), dossiers de
sauvegarde et de copie dans le scratchpad, historique posé à la main (vrais dumps de la copie,
noms datés) : 21 quotidiennes (10–30 mars 2030, 22:05), 13 hebdomadaires (30/12/2029–24/03/2030),
16 mensuelles (30/11/2028–28/02/2030), une manuelle, une « avant mise à jour », une base vide —
53 fichiers. Serveur d'essai `essais.stress.app_figee:app`, horloge figée au **dimanche
31 mars 2030 à 22:05**, `GESTIONMPPRO_TACHES=1`, un passage de la tâche :

- trois fichiers écrits et relus (73 tables chacun) : `…-2030-03-31-220500-quotidienne`,
  `-hebdomadaire`, `-mensuelle` ; tâche « sauvegarde » ok, alerte vide, âge 0 h ;
- purge : 18 effacés, **38** restants dans le dossier **et** dans la copie : 14 quotidiennes,
  8 hebdomadaires, 13 mensuelles (les 12 dernières, avril 2029 → mars 2030, **plus fin décembre
  2028**, gardée ; novembre 2028 et janvier–mars 2029 effacées), manuelle, avant mise à jour et base
  vide intactes ;
- Administration › Sauvegardes à 1 440 × 900 : KPI « Dernière sauvegarde 31/03/2030 22:05 »,
  « Sauvegardes conservées 38 — à 22 h : chaque soir (14 jours), le dimanche (8 semaines), le
  dernier jour du mois (12 mois, fin décembre gardée) », copie « Oui » ; colonne Nature
  « quotidienne », « mensuelle », « hebdomadaire »… ; filtre « Nature : toutes », « quotidienne
  (14) », « hebdomadaire (8) », « mensuelle (13) », « manuelle (1) », « avant une mise à jour
  (1) », « base vide de référence (1) » ; « mensuelle » posé : 13 / 38, la plus ancienne
  31/12/2028 ; l'aide du KPI dit la règle.

Aucun chiffre métier n'est touché : le diff ne change que les sauvegardes (services, tâche,
registre, écran, documents) ; `make verifier` vert (3 041 essais serveur, 883 écran).

## Chez Mohamed, le premier soir après la mise en service

Dossier en service le 15/10 : 7 quotidiennes (la dernière le 15/10 à 00:05), aucune hebdomadaire
ni mensuelle. Au redémarrage de la mise à jour (sauvegarde « avant mise à jour » et migration 0010
comme toujours), premier passage de la tâche :

- **quotidienne** : pas due si la mise en service a lieu avant 22 h (celle de 00:05 couvre
  l'échéance du 14 au soir) ; due tout de suite si elle a lieu après 22 h ;
- **hebdomadaire** et **mensuelle** : aucune encore → **une de chaque, tout de suite** (elles
  valent pour le dimanche 11/10 et le 30/09) ; pas d'avalanche ;
- purge : 7 quotidiennes < 14, rien d'effacé ;
- **le soir même entre 22:00 et 22:15**, la quotidienne (Mac éteint ou en veille : dans le quart
  d'heure qui suit son retour) ; dimanche 18/10 à 22 h : quotidienne + hebdomadaire ; samedi 31/10
  à 22 h : quotidienne + mensuelle ;
- l'écran liste désormais toutes ses sauvegardes (plus de 30 : il y en a déjà 44, dont une
  trentaine « avant une mise à jour ») ; le filtre « Nature » les sépare.
