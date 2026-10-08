/** Oui ou non, au clic ou à la barre d'espace (rôle `switch`). Le libellé est à côté et le nomme. */
import type { ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import styles from './Interrupteur.module.css'

export function Interrupteur({
  valeur,
  onChange,
  libelle,
  desactive,
}: {
  valeur: boolean
  onChange: (valeur: boolean) => void
  libelle: ReactNode
  desactive?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={valeur}
      disabled={desactive}
      className={classes(styles.interrupteur, valeur && styles.actif)}
      onClick={() => onChange(!valeur)}
    >
      <span className={styles.piste} aria-hidden="true" />
      <span>{libelle}</span>
    </button>
  )
}
