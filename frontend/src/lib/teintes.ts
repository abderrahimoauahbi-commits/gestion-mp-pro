/**
 * La couleur d'un fil traduite en couleur d'écran : un fil rouge a une courbe rouge (exigence M86).
 *
 * Seul fichier de couleurs hors de `styles/jetons.css` (ECRANS-PRO § 3) : les graphiques SVG en
 * tirent leurs traits. Repris de Gestion MP (lui-même repris de l'ERP Fil), à l'identique.
 *
 * Les noms viennent du catalogue, en français ou en anglais, parfois abrégés (« L.Beige »,
 * « Dk Vison », « D.Turkoi »). Les teintes claires sont volontairement assombries : un fil blanc
 * ou crème doit rester lisible sur un fond blanc.
 */
import { sansAccents } from './recherche'

/** Du plus précis au plus général : « bleu marine » avant « bleu ». 30 motifs. */
const TEINTES: readonly (readonly [RegExp, string])[] = [
  [/bleu marine|navy|marine/, '#1b2f5e'],
  [/turk|turq/, '#1295a8'],
  [/bleu|blue/, '#2563b8'],
  [/vert fonce|d\.? ?green|dark green/, '#1e5b3a'],
  [/olive|oilve|kaki|khaki/, '#6b7a2a'],
  [/vert|green/, '#2e8b57'],
  [/bordeau|bordo/, '#7b1e2b'],
  [/brique|brick/, '#b5532f'],
  [/rouge|red/, '#c62828'],
  [/rose|pink/, '#d6589a'],
  [/orange/, '#e07b1a'],
  [/jaune|yellow/, '#d4b400'],
  [/\bor\b|gold/, '#c79a00'],
  [/camel/, '#b8864b'],
  [/beige fonce|d\.? ?beige/, '#a98f63'],
  [/l\.? ?beige/, '#cdb891'],
  [/beige/, '#bfa57a'],
  [/cream|creme|ivory|ivoire|ecru/, '#d1c089'],
  [/l\.? ?brown/, '#9a7354'],
  [/marron|brown/, '#6d4c33'],
  [/khave|kahve|cafe|coffee/, '#5c4033'],
  [/dk vison|dk vizon/, '#5f4b3d'],
  [/vison|vizon/, '#8a6f5a'],
  [/taupe/, '#8b7d70'],
  [/noir|black/, '#1f2933'],
  [/gris clair|l\.? ?grey|l\.? ?gris/, '#a5aeb8'],
  [/dark grey|d\.? ?grey|gris fonce/, '#4b5560'],
  [/gris|grris|grey|gray/, '#7a8591'],
  [/violet|mauve|purple/, '#7c3aed'],
  [/blanc|white/, '#9fb0c2'],
]

/** Les traits qui distinguent deux fils de la même couleur : plein, tirets, pointillés, mixte. */
export const TRAITS: readonly string[] = ['', '8 5', '2 4', '12 4 2 4']

/** Ce qui reste quand la couleur du fil ne dit rien (« C5N », « Cvr »), dans cet ordre. */
export const PALETTE_FILS: readonly string[] = [
  '#1f5fa8',
  '#c2410c',
  '#146c44',
  '#7c3aed',
  '#b45309',
  '#0e7490',
]

/** Les courbes des écrans de pilotage (séries sans couleur de fil) : huit au plus, toujours dans cet ordre. */
export const PALETTE_SERIES: readonly string[] = [
  '#2a78d6',
  '#eb6834',
  '#1baf7a',
  '#eda100',
  '#e87ba4',
  '#008300',
  '#4a3aa7',
  '#e34948',
]

/** La teinte d'un nom de couleur du catalogue, ou `null` si le nom n'en dit aucune. */
export function teinteDuFil(couleur: string | null | undefined): string | null {
  const nom = sansAccents(couleur ?? '')
  if (!nom) return null
  for (const [motif, teinte] of TEINTES) if (motif.test(nom)) return teinte
  return null
}

export interface StyleDeFil {
  couleur: string
  trait: string
}

/**
 * Une couleur et un trait par fil : la teinte du fil quand son nom en dit une, sinon la palette ;
 * deux fils de même teinte se distinguent par le trait.
 */
export function stylesDesFils(
  fils: readonly { cle: string; couleur?: string | null }[],
): Map<string, StyleDeFil> {
  const dejaPrises = new Map<string, number>()
  let sansTeinte = 0
  const styles = new Map<string, StyleDeFil>()
  for (const f of fils) {
    const couleur = teinteDuFil(f.couleur) ?? PALETTE_FILS[sansTeinte++ % PALETTE_FILS.length] ?? '#1f5fa8'
    const rang = dejaPrises.get(couleur) ?? 0
    dejaPrises.set(couleur, rang + 1)
    styles.set(f.cle, { couleur, trait: TRAITS[rang % TRAITS.length] ?? '' })
  }
  return styles
}

/** La couleur de la n-ième série d'un graphique de pilotage. */
export function couleurDeSerie(rang: number): string {
  return (
    PALETTE_SERIES[((rang % PALETTE_SERIES.length) + PALETTE_SERIES.length) % PALETTE_SERIES.length] ??
    '#2a78d6'
  )
}
