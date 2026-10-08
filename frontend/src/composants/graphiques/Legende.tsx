/** La légende d'un graphique : un échantillon de la couleur **et du trait** de chaque série. */
import type { SerieTracee } from './echelle'
import styles from './Graphique.module.css'

export function Legende({ series, barres }: { series: readonly SerieTracee[]; barres?: boolean }) {
  return (
    <div className={styles.legende}>
      {series.map((s) => (
        <span key={s.nom} className={styles.entree}>
          <svg className={styles.echantillon} viewBox="0 0 22 10" aria-hidden="true">
            {barres ? (
              <rect x="4" y="1" width="14" height="8" rx="2" style={{ fill: s.couleur }} />
            ) : (
              <line
                x1="1"
                y1="5"
                x2="21"
                y2="5"
                strokeWidth="2.5"
                strokeDasharray={s.trait || undefined}
                style={{ stroke: s.couleur }}
              />
            )}
          </svg>
          {s.nom}
          {s.unite ? ` (${s.unite})` : ''}
        </span>
      ))}
    </div>
  )
}
