/**
 * La rangée d'indicateurs d'une page : une seule rangée (six au Cockpit), chaque `Kpi` de même
 * largeur ; au téléphone, deux par rangée.
 */
import type { ReactNode } from 'react'

import styles from './Indicateurs.module.css'

export function Indicateurs({
  children,
  libelle = 'Indicateurs',
}: {
  children: ReactNode
  libelle?: string
}) {
  return (
    <section className={styles.indicateurs} aria-label={libelle}>
      {children}
    </section>
  )
}
