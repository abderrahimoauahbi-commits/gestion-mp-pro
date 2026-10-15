# PRODUCTION-DOUZE-MOIS — les douze mois d'un coup dans Production & besoins (15/10/2026)

Point de confort retenu par le coordinateur (AUDIT2-REFERENTIELS, « Ce qui reste » n° 2) : dans
**Production & besoins › Plan de production** et **› Besoins matière**, à 1 440 × 900 (le Mac de
Mohamed), les douze mois dépassaient le cadre ; le tableau défilait dans son cadre (E4), mais sur
Mac la barre horizontale ne se montre qu'au glissement : les derniers mois passaient pour absents.

Travail d'écran seulement : ni API, ni base, ni calcul (`production/plan.ts` intact ; la base / mois
reste saisie seule et ne change jamais d'elle-même, décision du 12/10/2026).

## Mesure avant (copie de la base « 3 ans », horloge au 15/10/2029, compte de direction d'essai)

`scrollWidth` / `clientWidth` du cadre du tableau, mesurés en JavaScript dans le navigateur
(`main` à 33a1451, servi par Vite sur la même copie) :

| Écran | 1 440 × 900 | Colonnes hors du cadre à 1 440 | 1 920 × 1 080 | 790 × 900 |
|---|---|---|---|---|
| Plan (coefficients et m²) | 1 581 / 1 142 | Nov., Déc., Total / an, État | 1 622 / 1 622 | 1 581 / 740 (9 colonnes hors) |
| Besoins, toutes qualités | 2 317 / 1 142 | **mars → sept. 2030** (7 mois), Total, Disponible, Couverture, À commander | 2 317 / 1 622 (août, sept. hors) | 2 317 / 740 (14 hors) |
| Besoins « Retenu » | 2 254 / 1 142 | mars → sept. 2030, Total, stock | — | — |
| Besoins par qualité (30 filtres) | 2 026 à 2 245 / 1 142 | 5 ou 6 mois selon la qualité | — | — |

Causes mesurées (largeur du contenu de chaque colonne) :

- Plan : chaque mois = champ de 62 px + 2 × 12 px de marge = 86 px ; le champ ne laissait que
  40 px de texte (bord 1 px + 10 px de marge intérieure de chaque côté).
- Besoins : le **pied** fixait la largeur des mois (« 275 936,42 kg », 84 px) alors que les
  cellules n'en demandaient que 40 ; l'en-tête « OCT. 2029 (EN COURS) » faisait 133 px ; la
  référence (avec « nature · désignation ») 321 px.

## Changement

**Composants communs** (opt-in, les autres listes ne changent pas — essai vitest) :

- `DataTable` : `serre` (cellules à 4 px de marge, en-têtes sur deux lignes au besoin) et `figee`
  (première colonne collée à gauche, fond plein, filet ; ombre dès que des colonnes sont passées
  dessous).
- `Cadre` : `horizontal` — barre de défilement **toujours visible** (`::-webkit-scrollbar` stylée :
  Chrome et Safari sur Mac la gardent affichée) et **ombre au bord droit** tant qu'il reste des
  colonnes à voir (`data-droite` / `data-gauche` sur une enveloppe, suivis au défilement, au
  redimensionnement et au changement de largeur du tableau ; l'ombre se pose devant la barre
  verticale). Fonction pure `debord()` essayée.

**Plan de production** : `serre` + `figee` ; champ d'un mois 54 px à 4 px de marge intérieure
(**44 px de texte, 40 avant** : « 42 000 », « 0,833 » se lisent entiers) ; base / mois 76 px ;
code + nom de qualité limités à 104 px, nom complet au survol ; « Enregistrer » et « Annuler »
passent l'un sous l'autre quand une ligne est modifiée ; état au plan sur deux lignes si long
(« recette / incomplète ») ; total de l'année : « moy. 0,66 » (le mot entier en infobulle :
« Coefficient moyen de l'année »), sans retour à la ligne.

**Besoins matière** : `serre` + `figee` (la référence reste à gauche) ; en-tête du mois en cours
« oct. 2029 ● » (comme le plan), « (mois en cours) » et l'unité en infobulle ; totaux des mois au
pied en **kilos entiers**, comme les cellules (l'unité est dans le titre de la carte et l'infobulle) ;
référence limitée à 190 px, « référence — nature · désignation » au survol.

## Mesure après (mêmes conditions)

| Écran | 1 440 × 900 | Hors du cadre à 1 440 | Largeur minimale du tableau | 1 920 × 1 080 | 790 × 900 |
|---|---|---|---|---|---|
| Plan (coefficients et m²) | **1 134 / 1 134** | **rien** | 1 104 (30 px de marge) | 1 614 / 1 614 | 1 104 / 732, Qualité figée, ombre, barre |
| Besoins, toutes qualités | 1 400 / 1 134 | Disponible, Couverture, À commander | 1 400 | 1 614 / 1 614 (tout) | 1 400 / 732, Référence figée |
| Besoins « Retenu » | 1 349 / 1 134 | Disponible, Couverture, À commander | 1 349 | 1 614 / 1 614 | 1 349 / 732 |
| Besoins par qualité (30 filtres) | 1 171 à 1 302 / 1 134-1 142 | **aucun mois** (stock seulement) | — | — | — |

(`clientWidth` 1 134 au lieu de 1 142 : la barre verticale, désormais toujours visible, prend 8 px.)

Positions à 1 440 (px depuis le bord du cadre) :

- Plan : Qualité 0-120 · Base 120-210 · Janv. 210-272 … Déc. 892-954 · Total / an 954-1 024 ·
  État 1 024-1 134.
- Besoins : Référence 0-206 · Rôle 206-268 · Fournisseur 268-363 · oct. 2029 ● 363-418 …
  sept. 2030 968-1 023 · Total 12 mois 1 023-1 126 · Disponible, Couverture, À commander au-delà
  (ombre à droite, barre visible, référence figée en défilant).

Aucun champ dont le texte déborde (`scrollWidth > clientWidth` des 390 champs : 0), ni en
coefficients ni en m², ni après la saisie de « 12 345 » ; aucune page qui défile (`scrollHeight` =
hauteur de la fenêtre) aux trois tailles. Au défilement complet : `data-gauche` posé, `data-droite`
retiré, colonne figée à 0 px avec son ombre.

## Mêmes chiffres

Sur la copie « 3 ans », l'écran de `main` (Vite à part) et celui de la branche lisent le même
serveur ; pour 34 vues (plan en coefficients et en m², besoins « plan » et « retenu », besoins
filtrés par chacune des 30 qualités), le texte de chaque cellule du corps (valeurs des champs
comprises) donne la **même empreinte SHA-256** des deux côtés, et le pied, ramené au kilo entier,
est identique (empreinte d'ensemble `c3cb1cfbcb02ca8e` des deux côtés). Seule normalisation : le
libellé « coef. moyen » devenu « moy. ». Les totaux au pied des mois des besoins s'affichent
arrondis au kilo (ils l'étaient au centième) ; le calcul, l'export et les autres colonnes ne
changent pas.

## Non changé

- Besoins : les colonnes de stock (Disponible, Couverture, À commander) restent au-delà du cadre à
  1 440 px — il faudrait 266 px de plus ; elles sont signalées (ombre, barre) et la référence reste
  visible quand on y va. Rôle et Fournisseur gardent leur place (ordre des colonnes inchangé).
- La fenêtre « d'où vient le besoin » (tableau écrit à la main, première colonne déjà figée).
- Firefox sur Mac garde ses barres flottantes (il ignore `::-webkit-scrollbar`) : l'ombre du bord
  droit y dit seule le débordement.
