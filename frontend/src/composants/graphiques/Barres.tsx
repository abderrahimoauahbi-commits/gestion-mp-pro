/**
 * Des barres verticales, une ou plusieurs séries côte à côte, SVG maison (sans dépendance). Une
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
}

const MARGES = { g: 52, d: 10, h: 22, b: 26 }

interface PanneauProps {
  etiquettes: readonly string[]
  series: SerieTracee[]
  unite: string
  hauteur: number
  format: (v: number) => string
  libelle: string
}

function Panneau({ etiquettes, series, unite, hauteur, format, libelle }: PanneauProps) {
  const { ticks, y } = echelleY(series, hauteur, MARGES)
  const pasX = (LARGEUR - MARGES.g - MARGES.d) / Math.max(1, etiquettes.length)
  const barre = Math.min(34, (pasX * 0.72) / Math.max(1, series.length))
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
          {series.map((s, j) => {
            const v = s.valeurs[i]
            if (v == null) return null
            const x = MARGES.g + pasX * i + (pasX - barre * series.length) / 2 + j * barre
            return (
              <rect
                key={s.nom}
                x={x}
                y={Math.min(y(v), y(0))}
                width={Math.max(1, barre - 2)}
                height={Math.abs(y(0) - y(v))}
                rx="2"
                style={{ fill: s.couleur }}
              >
                <title>{`${e} · ${s.nom} : ${format(v)}${suffixe}`}</title>
              </rect>
            )
          })}
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
        />
      ))}
      {tracees.length > 1 ? <Legende series={tracees} barres /> : null}
    </figure>
  )
}
