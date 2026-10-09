/**
 * Bornes et longueurs d'une fiche (R5, P7-19, P7-20) : elles sont déclarées **une fois au
 * serveur** (`services/matieres.py` `BORNES`, `modeles/longueurs.py`, schémas des fournisseurs) ;
 * l'écran les reprend pour les contrôler à la frappe. L'essai `bornes.test.ts` relit les sources
 * du serveur et échoue si l'une d'elles change sans que l'écran suive.
 */

/** Les nombres d'une matière : [plus petit, plus grand] (`services.matieres.BORNES`). */
export const BORNES_MATIERE = {
  densite: [0, 1000],
  prix: [0, 1e7],
  contenance_achat: [0, 1e7],
  minimum_commande: [0, 1e9],
  poids_bobine: [0, 1000],
  bobines_palette: [0, 10000],
  stock_min: [0, 1e9],
  couv_min_mois: [0, 60],
} as const satisfies Record<string, readonly [number, number]>

export type ChampBorne = keyof typeof BORNES_MATIERE

/** Les longueurs des textes (`modeles.longueurs`). */
export const LONGUEURS = {
  REFERENCE: 160,
  DESIGNATION: 160,
  COULEUR_CODE: 32,
  UNITE_ACHAT: 32,
  GROUPE_EQUIV: 64,
  LIBELLE: 120,
  FAMILLE: 64,
  COMPOSITION_DETAILLEE: 160,
  VALEUR_TITRAGE: 32,
  UNITE_TITRAGE: 16,
  CODE_ROLE: 32,
  NOM_FOURNISSEUR: 160,
  CODE_FOURNISSEUR: 32,
  PAYS: 80,
  CONTACT: 120,
  TELEPHONE: 60,
  EMAIL_FOURNISSEUR: 160,
  MODE_PAIEMENT: 40,
  CONDITIONS_PAIEMENT: 160,
  INCOTERM: 20,
  PORT: 80,
  BANQUE: 120,
} as const

/** Délais d'un fournisseur (jours) et longueur des observations (`api/fournisseurs/schemas.py`). */
export const DELAI_MAX = 730
export const NOTES_MAX = 2000
/** Les observations d'une valeur de classification (`api/classification/schemas.py`). */
export const COMMENTAIRE_MAX = 500
/** Le suffixe d'une référence composée (`GET /matieres/reference`). */
export const SUFFIXE_MAX = 16
