/**
 * Les formes du catalogue, lues dans l'OpenAPI (`types.gen.ts`, routes 57–81 du lot D1) : aucune
 * n'est recopiée à la main. Les quatre listes de la classification et ce qui les distingue
 * (libellés, longueur du code, majuscules, champs) sont déclarés ici une fois.
 */
import type { Schema } from '../../lib/types'

export type Matiere = Schema<'MatiereResume'>
export type MatiereFiche = Schema<'MatiereFiche'>
export type MatiereCorps = Schema<'MatiereModification'>
export type Fournisseur = Schema<'FournisseurFiche'>
export type FournisseurResume = Schema<'FournisseurResume'>
export type FournisseurCorps = Schema<'FournisseurModification'>
export type Classification = Schema<'Classification'>
export type Valeur = Schema<'ValeurFiche'>
export type RoleNomenclature = Schema<'RoleFiche'>
export type Devise = Schema<'DeviseFiche'>
export type CodeDouanier = Schema<'CodeDouanierFiche'>
export type ApercuImport = Schema<'ApercuImport'>
export type LigneImport = Schema<'LigneImport'>
export type ApercuClassement = Schema<'ApercuClassement'>

/** Une liste de la classification, telle que la route la nomme (`/classification/{liste}`). */
export type Liste = 'compositions' | 'types-fil' | 'titrages' | 'couleurs'

/** Un champ d'une valeur de classification, selon sa liste. */
export type ChampValeur = 'libelle' | 'famille' | 'composition_detaillee' | 'valeur' | 'unite'

export interface DefinitionListe {
  liste: Liste
  /** La clé de la liste dans `Classification` (et l'identifiant de la matière : `<champ>_id`). */
  cle: 'compositions' | 'types_fil' | 'titrages' | 'couleurs'
  /** Le champ de la matière (`composition_id`…). */
  champ: 'composition_id' | 'type_fil_id' | 'titrage_id' | 'couleur_id'
  /** « Compositions », pour la bascule. */
  pluriel: string
  /** « composition » ; « une composition » ; « Composition « PP » ». */
  nom: string
  un: string
  /** Le genre du nom : l'accord des messages (« désactivé », « désactivée »). */
  feminin: boolean
  /** La longueur du code : celle de la colonne de la matière (P7-19). */
  longueur: number
  /** Le code s'écrit en majuscules (composition, type de fil). */
  majuscules: boolean
  champs: readonly ChampValeur[]
  exemple: string
  /** La note d'explication de la liste (Gestion MP). */
  note: string
  placeholder: string
}

export const LISTES: readonly DefinitionListe[] = [
  {
    liste: 'compositions',
    cle: 'compositions',
    champ: 'composition_id',
    pluriel: 'Compositions',
    nom: 'composition',
    un: 'une composition',
    feminin: true,
    longueur: 32,
    majuscules: true,
    champs: ['libelle', 'famille', 'composition_detaillee'],
    exemple: 'PP',
    note: 'La matière du fil : PP (polypropylène), PES (polyester)… Le code ouvre la référence.',
    placeholder: 'Taper : PP, polyester…',
  },
  {
    liste: 'types-fil',
    cle: 'types_fil',
    champ: 'type_fil_id',
    pluriel: 'Types de fil',
    nom: 'type de fil',
    un: 'un type de fil',
    feminin: false,
    longueur: 32,
    majuscules: true,
    champs: ['libelle'],
    exemple: 'FRZ',
    note: 'La façon du fil : frisé (FRZ), shrink, filament… Le code suit la composition dans la référence.',
    placeholder: 'Taper : FRZ, shrink…',
  },
  {
    liste: 'titrages',
    cle: 'titrages',
    champ: 'titrage_id',
    pluriel: 'Titrages',
    nom: 'titrage',
    un: 'un titrage',
    feminin: false,
    longueur: 48,
    majuscules: false,
    champs: ['valeur', 'unite'],
    exemple: '2900 Dtex',
    note: 'La grosseur du fil, avec son unité : 2900 Dtex, 1500 Deniers… La valeur se lit dans le code si on ne la donne pas.',
    placeholder: 'Taper : 2900 Dtex…',
  },
  {
    liste: 'couleurs',
    cle: 'couleurs',
    champ: 'couleur_id',
    pluriel: 'Couleurs',
    nom: 'couleur',
    un: 'une couleur',
    feminin: true,
    longueur: 64,
    majuscules: false,
    champs: ['libelle', 'famille'],
    exemple: 'Rouge',
    note: 'Les couleurs du catalogue, telles que l’atelier les nomme : la référence les reprend avant le code couleur du fournisseur.',
    placeholder: 'Taper : rouge, beige…',
  },
]

/** La définition d'une liste par son nom de route. */
export function definition(liste: Liste): DefinitionListe {
  return LISTES.find((l) => l.liste === liste) ?? LISTES[0]
}

/** Le fournisseur complet (direction, achats) ou résumé (alimentation : nom, pays, état). */
export function estComplet(f: Fournisseur | FournisseurResume): f is Fournisseur {
  return 'version' in f
}
