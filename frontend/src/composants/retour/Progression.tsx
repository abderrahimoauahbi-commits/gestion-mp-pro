/** Une part accomplie (0 à 1) : barre avec son rôle et sa valeur dite (« 62 % »). */
import { part as enPart } from '../../lib/format'
import type { Ton } from '../../lib/statuts'
import { classes } from '../mise-en-page/classes'
import styles from './Progression.module.css'

export function Progression({
  part,
  libelle,
  ton = 'accent',
}: {
  part: number | null | undefined
  libelle: string
  ton?: Ton
}) {
  const v = Math.max(0, Math.min(1, part ?? 0))
  return (
    <div
      className={classes(styles.progression, styles[ton])}
      role="progressbar"
      aria-label={libelle}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(v * 100)}
      aria-valuetext={enPart(part ?? 0, 0)}
    >
      <div className={styles.barre} style={{ width: `${v * 100}%` }} />
    </div>
  )
}
