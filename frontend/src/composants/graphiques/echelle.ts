/**
 * Les échelles des graphiques SVG maison : graduations rondes (1, 2, 2,5, 5 × 10^n), nombres
 * courts sur les axes (« 17,4 M », « 12,5 k »), traits qui distinguent deux séries de même teinte.
 */
import { nombre } from '../../lib/format'
import { couleurDeSerie, TRAITS } from '../../lib/teintes'

/**
 * Les graduations d'un axe qui couvre [min, max] : zéro compris pour des barres (une barre part
 * de zéro) ; pour des courbes (`avecZero` faux), l'axe serre les valeurs (des prix de 2,6 à 2,9
 * ne s'écrasent pas en bas d'un axe de 0 à 4).
 */
export function graduation(min: number, max: number, cible = 4, avecZero = true): number[] {
  const bas = avecZero ? Math.min(0, min) : min
  const haut = avecZero ? Math.max(0, max) : max
  if (bas === haut) return bas === 0 ? [0, 1] : graduation(bas * 0.9, haut * 1.1, cible, avecZero)
  const brut = (haut - bas) / cible
  const p = 10 ** Math.floor(Math.log10(brut))
  const pas = [1, 2, 2.5, 5, 10].map((k) => k * p).find((k) => k >= brut) ?? brut
  const debut = Math.floor(bas / pas)
  const fin = Math.ceil(haut / pas)
  return Array.from({ length: fin - debut + 1 }, (_, i) => Number(((debut + i) * pas).toPrecision(12)))
}

/** Un nombre court pour un axe : « 17,4 M », « 12,5 k », « 950 ». */
export function court(v: number): string {
  const a = Math.abs(v)
  if (a >= 1e6) return `${nombre(v / 1e6, 0, 1)}\u00a0M`
  if (a >= 1e4) return `${nombre(v / 1e3, 0, 1)}\u00a0k`
  return nombre(v, 0, 2)
}

export interface Serie {
  nom: string
  valeurs: readonly (number | null)[]
  couleur?: string
  /** Le trait (`stroke-dasharray`) ; posé seul quand deux séries ont la même teinte. */
  trait?: string
  /** L'unité de la série : une devise, des kilos. Jamais deux unités sur un même axe. */
  unite?: string
}

export interface SerieTracee extends Serie {
  couleur: string
  trait: string
}

/** Couleur (palette des séries si absente) et trait (différent à teinte égale) de chaque série. */
export function tracer(series: readonly Serie[]): SerieTracee[] {
  const vues = new Map<string, number>()
  return series.map((s, i) => {
    const couleur = s.couleur ?? couleurDeSerie(i)
    const rang = vues.get(couleur) ?? 0
    vues.set(couleur, rang + 1)
    return { ...s, couleur, trait: s.trait ?? TRAITS[rang % TRAITS.length] ?? '' }
  })
}

/** Les séries rangées par unité, dans l'ordre d'apparition : un axe par unité. */
export function parUnite<S extends Serie>(series: readonly S[]): [string, S[]][] {
  const groupes = new Map<string, S[]>()
  for (const s of series) {
    const u = s.unite ?? ''
    groupes.set(u, [...(groupes.get(u) ?? []), s])
  }
  return [...groupes.entries()]
}

/** Les bornes des valeurs (vides sautés). */
export function bornes(series: readonly Serie[]): [number, number] {
  const v = series.flatMap((s) => s.valeurs.filter((x): x is number => x != null && Number.isFinite(x)))
  return v.length ? [Math.min(...v), Math.max(...v)] : [0, 0]
}
