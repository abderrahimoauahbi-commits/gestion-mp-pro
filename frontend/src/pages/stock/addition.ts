/**
 * Une addition affichée tombe juste (critère du lot F2) : « Disponible + Commandé − Demande
 * pendant le délai = Stock projeté », écrite au dixième de kilo, ne doit jamais se lire
 * « 100,0 + 0,0 − 33,3 = 66,6 ». Chaque terme est arrondi, puis le reste de l'arrondi est porté
 * par le terme qui en a perdu le plus (méthode du plus fort reste) : le total affiché reste
 * l'arrondi du total du serveur, et les termes affichés s'y additionnent exactement.
 *
 * La fiche matière lit **une seule fois** ces valeurs : ses indicateurs et sa carte « Où se
 * trouve la matière » disent les mêmes chiffres.
 */
import { arrondi } from '../../lib/format'
import { estQuarantaine, type LigneStock } from './types'

/** Le pas d'arrondi des kilos affichés au bureau (une décimale, `format.kg`). */
export const DECIMALES_KG = 1

/**
 * Des termes signés arrondis à `decimales` dont la somme vaut l'arrondi de `total`. Les termes
 * d'indice `fixes` gardent leur valeur (déjà affichée ailleurs) ; si tous sont fixes, rien ne bouge.
 */
export function repartir(
  termes: readonly number[],
  total: number,
  { decimales = DECIMALES_KG, fixes = [] }: { decimales?: number; fixes?: readonly number[] } = {},
): number[] {
  const pas = 10 ** -decimales
  const ronds = termes.map((t, i) => (fixes.includes(i) ? t : arrondi(t, decimales)))
  const cible = arrondi(total, decimales)
  let reste = Math.round((cible - ronds.reduce((a, b) => a + b, 0)) / pas)
  const candidats = termes
    .map((t, i) => ({ i, perte: t - (ronds[i] ?? 0) }))
    .filter((c) => !fixes.includes(c.i))
  while (reste !== 0 && candidats.length) {
    const sens = Math.sign(reste)
    // Le terme dont l'arrondi a le plus perdu dans le sens du reste reçoit un pas.
    candidats.sort((a, b) => b.perte * sens - a.perte * sens)
    const c = candidats[0]
    if (!c) break
    ronds[c.i] = arrondi((ronds[c.i] ?? 0) + sens * pas, decimales)
    c.perte -= sens * pas
    reste -= sens
  }
  return ronds
}

export interface MagasinAffiche {
  code: string
  quarantaine: boolean
  kg: number
}

/** Ce que la fiche matière affiche, au dixième de kilo, additions justes. */
export interface AffichageMatiere {
  magasins: MagasinAffiche[]
  metiers: number
  disponible: number
  quarantaine: number
  /** Stock = magasins (quarantaine comprise) + sur les métiers. */
  stock: number
  commande: number
  auDela: number
  demande: number
  projete: number
}

const n = (v: number | null | undefined) => v ?? 0

/**
 * Les trois additions de la fiche : magasins courants + sur les métiers = Disponible ;
 * Disponible + quarantaine = Stock ; Disponible + Commandé − Demande pendant le délai = Projeté.
 * `types` : le type de chaque magasin par son code (`GET magasins`).
 */
export function affichageMatiere(l: LigneStock, types: ReadonlyMap<string, string>): AffichageMatiere {
  const lus = Object.entries(l.par_magasin ?? {})
    .filter(([, kg]) => Math.abs(kg) >= 0.0005)
    .map(([code, kg]) => ({ code, kg, quarantaine: estQuarantaine(types.get(code)) }))
    .sort((a, b) => Number(a.quarantaine) - Number(b.quarantaine) || a.code.localeCompare(b.code, 'fr'))
  const courants = lus.filter((m) => !m.quarantaine)
  const bloques = lus.filter((m) => m.quarantaine)
  const dispo = repartir([...courants.map((m) => m.kg), n(l.stock_machine)], n(l.stock_disponible))
  const disponible = arrondi(n(l.stock_disponible), DECIMALES_KG)
  const stockTotal = n(l.stock_net) + n(l.stock_machine)
  const q = repartir([disponible, ...bloques.map((m) => m.kg)], stockTotal, { fixes: [0] })
  const projection = repartir([disponible, n(l.bc_en_cours), -n(l.demande_delai)], n(l.stock_projete), {
    fixes: [0],
  })
  const magasins = [
    ...courants.map((m, i) => ({ ...m, kg: dispo[i] ?? 0 })),
    ...bloques.map((m, i) => ({ ...m, kg: q[i + 1] ?? 0 })),
  ]
  return {
    magasins,
    metiers: dispo[courants.length] ?? 0,
    disponible,
    quarantaine: arrondi(
      q.slice(1).reduce((a, b) => a + b, 0),
      DECIMALES_KG,
    ),
    stock: arrondi(stockTotal, DECIMALES_KG),
    commande: projection[1] ?? 0,
    auDela: arrondi(n(l.bc_hors_horizon), DECIMALES_KG),
    demande: -(projection[2] ?? 0),
    projete: arrondi(n(l.stock_projete), DECIMALES_KG),
  }
}

/**
 * Un tableau mois par mois qui s'additionne juste, en kilos entiers : chaque colonne tombe sur son
 * total affiché, et ces totaux tombent sur l'arrondi du total général (la somme du serveur). Rend
 * les lignes et les totaux affichés ; le total d'une ligne est la somme de ses cellules.
 */
export function tableauJuste(
  lignes: readonly (readonly number[])[],
  totaux: readonly number[],
): { lignes: number[][]; totaux: number[] } {
  const general = totaux.reduce((a, b) => a + b, 0)
  const colonnes = repartir(totaux, general, { decimales: 0 })
  const cellules = colonnes.map((t, i) =>
    repartir(
      lignes.map((l) => l[i] ?? 0),
      t,
      { decimales: 0 },
    ),
  )
  return { lignes: lignes.map((_, r) => colonnes.map((_t, i) => cellules[i]?.[r] ?? 0)), totaux: colonnes }
}
