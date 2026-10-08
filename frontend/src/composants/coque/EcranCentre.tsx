/** Un écran hors coque, centré (connexion, installation, chargement de la session, panne). */
import type { ReactNode } from 'react'

import styles from './EcranCentre.module.css'

export function EcranCentre({ children, large }: { children: ReactNode; large?: boolean }) {
  return (
    <div className={styles.fond}>
      <main className={large ? styles.large : styles.boite}>{children}</main>
    </div>
  )
}
