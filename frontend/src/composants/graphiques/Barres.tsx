/**
 * Des barres verticales, une ou plusieurs séries côte à côte — ou empilées (`empiler` : la part de
 * chaque série dans un total, le plan glissant par qualité) —, SVG maison (sans dépendance). Une
 * seule unité par graphique (« axe par devise ») : des séries d'unités différentes font un
 * graphique par unité. Couleurs : la palette des séries (`lib/teintes.ts`) ou celle donnée ;
 * chaque barre dit sa valeur en infobulle.
 */
import { nombre } from '../../lib/format'
import { Axe, echelleY, LARGEUR } from './Axe'
import { parUnite, tracer, type Serie, type SerieTracee } from './echelle'
import styles from './Graphique.module.css'
import { Legende } from './Legende'

export interface BarresProps {
  etiquettes: readonly string[]
  series: readonly Serie[]
  libelle: string
  hauteur?: number
  format?: (v: number) => string
  /** Empiler les séries d'une même unité (une barre par étiquette, le total en haut). */
  empiler?: boolean
}

const MARGES = { g: 52, d: 10, h: 22, b: 26 }

interface PanneauProps {
  etiquettes: readonly string[]
  series: SerieTracee[]
  unite: string
  hauteur: number
  format: (v: number) => string
  libelle: string
  empiler: boolean
}

/** Les sommes positives et négatives de chaque étiquette : les bornes d'un axe empilé. */
function totauxEmpiles(etiquettes: readonly string[], series: readonly SerieTracee[]): Serie[] {
  const somme = (i: number, signe: 1 | -1) =>
    series.reduce((t, s) => {
      const v = s.valeurs[i] ?? 0
      return v * signe > 0 ? t + v : t
    }, 0)
  return [
    { nom: 'dessus', valeurs: etiquettes.map((_, i) => somme(i, 1)) },
    { nom: 'dessous', valeurs: etiquettes.map((_, i) => somme(i, -1)) },
  ]
}

/** Les rectangles d'une étiquette, empilés : chaque série part de là où la précédente s'arrête. */
function Pile({ e, i, x, largeur, series, y, format, suffixe }: PileProps) {
  let dessus = 0
  let dessous = 0
  const total = series.reduce((t, s) => t + (s.valeurs[i] ?? 0), 0)
  return series.map((s) => {
    const v = s.valeurs[i]
    if (v == null || v === 0) return null
    const depart = v > 0 ? dessus : dessous
    const fin = depart + v
    if (v > 0) dessus = fin
    else dessous = fin
    return (
      <rect
        key={s.nom}
        x={x}
        y={Math.min(y(depart), y(fin))}
        width={largeur}
        height={Math.abs(y(depart) - y(fin))}
        style={{ fill: s.couleur }}
      >
        <title>{`${e} · ${s.nom} : ${format(v)}${suffixe} (total ${format(total)}${suffixe})`}</title>
      </rect>
    )
  })
}

/** Les rectangles d'une étiquette, côte à côte : une colonne par série. */
function CoteACote({ e, i, x, largeur, series, y, format, suffixe }: PileProps) {
  return series.map((s, j) => {
    const v = s.valeurs[i]
    if (v == null) return null
    return (
      <rect
        key={s.nom}
        x={x + j * largeur}
        y={Math.min(y(v), y(0))}
        width={Math.max(1, largeur - 2)}
        height={Math.abs(y(0) - y(v))}
        rx="2"
        style={{ fill: s.couleur }}
      >
        <title>{`${e} · ${s.nom} : ${format(v)}${suffixe}`}</title>
      </rect>
    )
  })
}

interface PileProps {
  e: string
  i: number
  x: number
  largeur: number
  series: readonly SerieTracee[]
  y: (v: number) => number
  format: (v: number) => string
  suffixe: string
}

function Panneau({ etiquettes, series, unite, hauteur, format, libelle, empiler }: PanneauProps) {
  const { ticks, y } = echelleY(empiler ? totauxEmpiles(etiquettes, series) : series, hauteur, MARGES)
  const pasX = (LARGEUR - MARGES.g - MARGES.d) / Math.max(1, etiquettes.length)
  const colonnes = empiler ? 1 : Math.max(1, series.length)
  const barre = Math.min(empiler ? 40 : 34, (pasX * 0.72) / colonnes)
  const suffixe = unite ? ` ${unite}` : ''
  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${LARGEUR} ${hauteur}`}
      role="img"
      aria-label={unite ? `${libelle} (${unite})` : libelle}
    >
      <Axe ticks={ticks} y={y} unite={unite} marges={MARGES} />
      {etiquettes.map((e, i) => (
        <g key={`${e}-${i}`}>
          {empiler ? (
            <Pile
              e={e}
              i={i}
              x={MARGES.g + pasX * i + (pasX - barre) / 2}
              largeur={Math.max(1, barre - 2)}
              series={series}
              y={y}
              format={format}
              suffixe={suffixe}
            />
          ) : (
            <CoteACote
              e={e}
              i={i}
              x={MARGES.g + pasX * i + (pasX - barre * series.length) / 2}
              largeur={barre}
              series={series}
              y={y}
              format={format}
              suffixe={suffixe}
            />
          )}
          <text
            className={styles.texte}
            x={MARGES.g + pasX * i + pasX / 2}
            y={hauteur - 8}
            textAnchor="middle"
          >
            {e}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function Barres({
  etiquettes,
  series,
  libelle,
  hauteur = 220,
  format = (v) => nombre(v, 0, 2),
  empiler = false,
}: BarresProps) {
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
          empiler={empiler}
        />
      ))}
      {tracees.length > 1 ? <Legende series={tracees} barres /> : null}
    </figure>
  )
}
