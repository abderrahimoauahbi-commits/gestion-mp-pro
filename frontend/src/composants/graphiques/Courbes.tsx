/**
 * Des courbes sur une même échelle par unité (« axe par devise » : un panneau par unité, jamais
 * deux devises sur un axe). La couleur d'un fil est celle du fil (`teintes.ts`, M86) ; deux
 * séries de même teinte se distinguent par le trait, repris dans la légende. Un vide coupe la
 * courbe ; chaque point dit sa valeur en infobulle.
 */
import { nombre } from '../../lib/format'
import { Axe, echelleY, LARGEUR } from './Axe'
import { parUnite, tracer, type Serie, type SerieTracee } from './echelle'
import styles from './Graphique.module.css'
import { Legende } from './Legende'

export interface CourbesProps {
  etiquettes: readonly string[]
  series: readonly Serie[]
  libelle: string
  hauteur?: number
  format?: (v: number) => string
}

const MARGES = { g: 52, d: 14, h: 22, b: 26 }

/** Les morceaux d'une courbe : un vide la coupe (pas de trait inventé entre deux mois). */
export function morceaux(points: readonly (readonly [number, number] | null)[]): string[] {
  const traits: string[] = []
  let courant: string[] = []
  for (const p of points) {
    if (p) courant.push(`${p[0]},${p[1]}`)
    else if (courant.length) {
      traits.push(courant.join(' '))
      courant = []
    }
  }
  if (courant.length) traits.push(courant.join(' '))
  return traits
}

interface PanneauProps {
  etiquettes: readonly string[]
  series: SerieTracee[]
  unite: string
  hauteur: number
  format: (v: number) => string
  libelle: string
}

function Trace({
  s,
  x,
  y,
  etiquettes,
  format,
  unite,
}: {
  s: SerieTracee
  x: (i: number) => number
  y: (v: number) => number
  etiquettes: readonly string[]
  format: (v: number) => string
  unite: string
}) {
  const points = s.valeurs.map((v, i) => (v == null ? null : ([x(i), y(v)] as const)))
  return (
    <g data-serie={s.nom}>
      {morceaux(points).map((pts) => (
        <polyline
          key={pts}
          points={pts}
          fill="none"
          strokeWidth="2.2"
          strokeLinejoin="round"
          strokeDasharray={s.trait || undefined}
          style={{ stroke: s.couleur }}
        />
      ))}
      {s.valeurs.map((v, i) =>
        v == null ? null : (
          <circle key={i} cx={x(i)} cy={y(v)} r="3" style={{ fill: s.couleur }}>
            <title>{`${etiquettes[i] ?? ''} · ${s.nom} : ${format(v)}${unite ? ` ${unite}` : ''}`}</title>
          </circle>
        ),
      )}
    </g>
  )
}

function Panneau({ etiquettes, series, unite, hauteur, format, libelle }: PanneauProps) {
  const { ticks, y } = echelleY(series, hauteur, MARGES, false)
  const pasX = (LARGEUR - MARGES.g - MARGES.d) / Math.max(1, etiquettes.length - 1)
  const x = (i: number) => MARGES.g + pasX * i
  const lecture = Math.max(1, Math.ceil(etiquettes.length / 12))
  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${LARGEUR} ${hauteur}`}
      role="img"
      aria-label={unite ? `${libelle} (${unite})` : libelle}
    >
      <Axe ticks={ticks} y={y} unite={unite} marges={MARGES} />
      {etiquettes.map((e, i) =>
        i % lecture === 0 ? (
          <text key={`${e}-${i}`} className={styles.texte} x={x(i)} y={hauteur - 8} textAnchor="middle">
            {e}
          </text>
        ) : null,
      )}
      {series.map((s) => (
        <Trace key={s.nom} s={s} x={x} y={y} etiquettes={etiquettes} format={format} unite={unite} />
      ))}
    </svg>
  )
}

export function Courbes({
  etiquettes,
  series,
  libelle,
  hauteur = 220,
  format = (v) => nombre(v, 0, 2),
}: CourbesProps) {
  const tracees = tracer(series)
  if (!etiquettes.length || !tracees.length)
    return <div className={styles.vide}>Pas de données à montrer.</div>
  return (
    <figure className={styles.graphique} aria-label={libelle}>
      {parUnite(tracees).map(([unite, groupe]) => (
        <Panneau
          key={unite}
          etiquettes={etiquettes}
          series={groupe}
          unite={unite}
          hauteur={hauteur}
          format={format}
          libelle={libelle}
        />
      ))}
      <Legende series={tracees} />
    </figure>
  )
}
