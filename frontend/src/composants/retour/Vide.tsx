/** Une liste vide qui dit pourquoi (« Aucun document joint. », « Aucune ligne ne répond à ces critères. »). */
import type { ReactNode } from 'react'

import { Icone } from '../mise-en-page/Icone'
import styles from './Vide.module.css'

export function Vide({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className={styles.vide}>
      <Icone nom="document" taille={24} />
      <div>{children}</div>
      {action}
    </div>
  )
}
