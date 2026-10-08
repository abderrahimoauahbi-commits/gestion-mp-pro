/** Une fiche lue : libellé → valeur ; une valeur absente se dit « — ». */
import type { ReactNode } from 'react'

import { VIDE } from '../../lib/format'
import { classes } from './classes'
import styles from './Definitions.module.css'

export function Definitions({
  items,
  colonnes = 2,
}: {
  items: readonly (readonly [string, ReactNode])[]
  colonnes?: 1 | 2 | 3
}) {
  return (
    <dl className={classes(styles.definitions, styles[`c${colonnes}`])}>
      {items.map(([libelle, valeur]) => (
        <div key={libelle} className={styles.paire}>
          <dt>{libelle}</dt>
          <dd>{valeur === '' || valeur == null || valeur === false ? VIDE : valeur}</dd>
        </div>
      ))}
    </dl>
  )
}
