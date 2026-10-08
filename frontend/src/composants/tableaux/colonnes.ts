/**
 * Les colonnes d'un `DataTable` (ECRANS-PRO § 3) : ce qu'elles affichent (`rendu`), leur valeur
 * brute (`valeur` : tri, recherche, totaux, export), leurs champs cachés cherchés (`recherche`),
 * leur unité (totaux par unité), leur lien.
 */
import type { ReactNode } from 'react'

import { kg, montant, nombre, VIDE } from '../../lib/format'
import { totauxParUnite, type Brute } from './filtrage'

export interface Colonne<T> {
  cle: string
  titre: string
  /** L'infobulle du titre (ce que la colonne compte). */
  aide?: string
  /** Ce qu'on affiche ; par défaut la valeur, mise en forme. */
  rendu?: (ligne: T) => ReactNode
  /** La valeur brute ; par défaut la propriété `cle` de la ligne. */
  valeur?: (ligne: T) => Brute
  /** Des champs cherchés sans être affichés (code, fournisseur, couleur…). */
  recherche?: (ligne: T) => readonly unknown[]
  /** Chiffres alignés à droite. */
  droite?: boolean
  /** L'unité de la valeur : fixe, ou par ligne (kg et ml mêlés, plusieurs devises). */
  unite?: string | ((ligne: T) => string)
  /** Un total au pied : par unité, jamais additionnées entre elles. */
  total?: boolean | ((somme: number, unite: string) => string)
  /** `false` : hors de l'export CSV de ce qui est affiché. */
  exporte?: boolean
  largeur?: number | string
  /** L'adresse où mène la cellule (n° → document, lot → sa fiche). */
  lien?: (ligne: T) => string | null | undefined
  triable?: boolean
  /** Colonne cherchée et exportée, mais pas affichée. */
  cache?: boolean
}

const estObjet = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

/** La valeur brute d'une cellule. */
export function brute<T>(c: Colonne<T>, ligne: T): Brute {
  if (c.valeur) return c.valeur(ligne)
  if (!estObjet(ligne)) return undefined
  const v = ligne[c.cle]
  return typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean' ? v : undefined
}

/** Le contenu par défaut d'une cellule : un nombre à la française, un texte, ou « — ». */
export function contenu<T>(c: Colonne<T>, ligne: T): ReactNode {
  if (c.rendu) return c.rendu(ligne)
  const v = brute(c, ligne)
  if (v == null || v === '') return VIDE
  if (typeof v === 'number') return nombre(v, 0, 3)
  if (typeof v === 'boolean') return v ? 'oui' : 'non'
  return v
}

/** Le texte cherchable d'une ligne : chaque colonne (valeur et champs cachés) et les champs de la table. */
export function champsCherches<T>(
  colonnes: readonly Colonne<T>[],
  ligne: T,
  caches?: (l: T) => readonly unknown[],
) {
  const champs: unknown[] = []
  for (const c of colonnes) {
    champs.push(brute(c, ligne))
    if (c.recherche) champs.push(...c.recherche(ligne))
  }
  if (caches) champs.push(...caches(ligne))
  return champs
}

/** L'unité d'une cellule. */
export function uniteDe<T>(c: Colonne<T>, ligne: T): string {
  return typeof c.unite === 'function' ? c.unite(ligne) : (c.unite ?? '')
}

/** Un total dans son unité : kilos à une décimale, devises entières, le reste à la française. */
export function totalLisible(somme: number, unite: string): string {
  if (unite === 'kg') return kg(somme)
  if (/^[A-Z]{3}$/.test(unite)) return montant(somme, unite)
  return unite ? `${nombre(somme, 0, 2)}\u00a0${unite}` : nombre(somme, 0, 2)
}

/** Le pied d'une colonne : les totaux de chaque unité, côte à côte, du plus gros au plus petit. */
export function piedDeColonne<T>(c: Colonne<T>, lignes: readonly T[]): string {
  if (!c.total) return ''
  const totaux = totauxParUnite(
    lignes,
    (l) => brute(c, l),
    (l) => uniteDe(c, l),
  )
  const ecrire = typeof c.total === 'function' ? c.total : totalLisible
  return [...totaux.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([u, s]) => ecrire(s, u))
    .join(' · ')
}
