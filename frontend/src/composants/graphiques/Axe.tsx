/**
 * L'axe vertical commun aux barres et aux courbes : graduations rondes, lignes de grille (zéro
 * appuyé), nombres courts, unité de l'axe en haut à gauche (une unité par axe).
 */
import { bornes, court, graduation, type Serie } from './echelle'
import styles from './Graphique.module.css'

/** La largeur logique d'un graphique (le SVG s'étire à sa boîte). */
export const LARGEUR = 640

export interface Marges {
  g: number
  d: number
  h: number
  b: number
}

/** Les graduations d'un panneau et la position verticale d'une valeur. */
export function echelleY(series: readonly Serie[], hauteur: number, m: Marges, avecZero = true) {
  const [min, max] = bornes(series)
  const ticks = graduation(min, max, 4, avecZero)
  const bas = ticks[0] ?? 0
  const haut = ticks[ticks.length - 1] ?? 1
  const y = (v: number) => m.h + (hauteur - m.h - m.b) * (1 - (v - bas) / (haut - bas || 1))
  return { ticks, y }
}

export function Axe({
  ticks,
  y,
  unite,
  marges,
}: {
  ticks: readonly number[]
  y: (v: number) => number
  unite: string
  marges: Marges
}) {
  return (
    <g>
      {ticks.map((t) => (
        <g key={t}>
          <line
            className={t === 0 ? styles.zero : styles.grille}
            x1={marges.g}
            x2={LARGEUR - marges.d}
            y1={y(t)}
            y2={y(t)}
          />
          <text className={styles.texte} x={marges.g - 6} y={y(t) + 4} textAnchor="end">
            {court(t)}
          </text>
        </g>
      ))}
      {unite ? (
        <text className={styles.unite} x={4} y={9}>
          {unite}
        </text>
      ) : null}
    </g>
  )
}
