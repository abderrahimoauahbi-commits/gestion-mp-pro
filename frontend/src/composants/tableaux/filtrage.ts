/**
 * La logique des listes, sans écran : tri numérique puis naturel, filtres liés, recherche sur
 * champs cachés, totaux par unité. `DataTable`, `Filtres` et `SelecteurMatiere` la partagent.
 */
import { correspond, texteDe } from '../../lib/recherche'

export type Brute = string | number | boolean | null | undefined

/** Un filtre de liste : une valeur par ligne (texte), un libellé, une clé d'adresse. */
export interface Filtre<T> {
  /** Le nom du paramètre d'adresse et d'export (`fournisseur`, `statut`). */
  cle: string
  libelle: string
  valeur: (ligne: T) => string | null | undefined
  /** Le texte d'une valeur dans la liste (un code → son libellé). */
  libelleValeur?: (valeur: string) => string
  /** Liste fixée (liste paginée au serveur : les options ne se déduisent pas des lignes chargées). */
  options?: readonly string[]
  /** Le mot de « tous » quand le libellé est féminin (« Nature : toutes »). */
  tous?: string
  /** Le rang d'une valeur dans la liste (ordre métier) ; sans lui, l'ordre alphabétique. */
  rang?: (valeur: string) => number
}

/** Les valeurs choisies, par clé de filtre ('' ou absent : pas de filtre). */
export type Choix = Readonly<Record<string, string | undefined>>

const vide = (v: Brute) => v == null || v === ''

/**
 * Tri numérique puis naturel (« LOT-9 » avant « LOT-10 »), sans souci des accents ni des
 * majuscules ; deux nombres se comparent comme des nombres.
 */
export function comparer(a: Brute, b: Brute): number {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), 'fr', { numeric: true, sensitivity: 'base' })
}

/** Les lignes triées sur une valeur ; les vides vont toujours à la fin, quel que soit le sens. */
export function trier<T>(lignes: readonly T[], valeur: (l: T) => Brute, sens: 1 | -1): T[] {
  return [...lignes].sort((x, y) => {
    const a = valeur(x)
    const b = valeur(y)
    if (vide(a) && vide(b)) return 0
    if (vide(a)) return 1
    if (vide(b)) return -1
    return comparer(a, b) * sens
  })
}

/** Vrai si la ligne passe tous les filtres choisis, sauf celui nommé `sauf`. */
export function passe<T>(ligne: T, filtres: readonly Filtre<T>[], choix: Choix, sauf?: string): boolean {
  return filtres.every((f) => f.cle === sauf || !choix[f.cle] || (f.valeur(ligne) ?? '') === choix[f.cle])
}

export interface OptionFiltre {
  valeur: string
  libelle: string
  /** Le nombre de lignes qui l'ont, parmi celles qui passent les autres filtres. */
  nombre: number
}

/**
 * Les options **liées** d'un filtre (A1, M75) : les valeurs des lignes qui passent les autres
 * filtres (et la recherche), avec leur nombre ; la valeur choisie reste proposée même sans ligne.
 */
export function optionsLiees<T>(
  lignes: readonly T[],
  filtres: readonly Filtre<T>[],
  choix: Choix,
  filtre: Filtre<T>,
  dansRecherche: (l: T) => boolean = () => true,
): OptionFiltre[] {
  const comptes = new Map<string, number>()
  if (filtre.options) for (const o of filtre.options) comptes.set(o, 0)
  for (const l of lignes) {
    if (!passe(l, filtres, choix, filtre.cle) || !dansRecherche(l)) continue
    const v = filtre.valeur(l)
    if (!vide(v) && v != null) comptes.set(v, (comptes.get(v) ?? 0) + 1)
  }
  const choisie = choix[filtre.cle]
  if (choisie && !comptes.has(choisie)) comptes.set(choisie, 0)
  const nom = filtre.libelleValeur ?? ((v: string) => v)
  return [...comptes.entries()]
    .map(([valeur, nombre]) => ({ valeur, libelle: nom(valeur), nombre }))
    .sort(
      (a, b) =>
        (filtre.rang ? filtre.rang(a.valeur) - filtre.rang(b.valeur) : 0) || comparer(a.libelle, b.libelle),
    )
}

/** Le nombre de filtres posés. */
export function nombreDeCriteres(choix: Choix): number {
  return Object.values(choix).filter(Boolean).length
}

/** Vrai si le texte réuni des champs (visibles ou cachés) contient chaque mot de la recherche. */
export function trouve(champs: readonly unknown[], recherche: string): boolean {
  return correspond(texteDe([...champs]), recherche)
}

/**
 * Les totaux d'une colonne **par unité** : des kilos et des mètres, deux devises ne
 * s'additionnent jamais (REGLES-ECRAN § 3). Les vides et les non-nombres sont sautés.
 */
export function totauxParUnite<T>(
  lignes: readonly T[],
  valeur: (l: T) => Brute,
  unite: (l: T) => string,
): Map<string, number> {
  const totaux = new Map<string, number>()
  for (const l of lignes) {
    const v = valeur(l)
    if (typeof v !== 'number' || !Number.isFinite(v)) continue
    const u = unite(l)
    totaux.set(u, (totaux.get(u) ?? 0) + v)
  }
  return totaux
}
