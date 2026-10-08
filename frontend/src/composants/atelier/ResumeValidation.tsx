/**
 * Le résumé collant au bas d'une saisie de l'atelier : il rappelle **la date (« hier »), le
 * magasin, le métier** et ce qui partira, au-dessus du bouton qui valide — on ne valide pas
 * sans avoir relu ce qui compte.
 */
import type { ReactNode } from 'react'

import styles from './ResumeValidation.module.css'

export function ResumeValidation({
  lignes,
  children,
}: {
  lignes: readonly (readonly [string, ReactNode])[]
  children: ReactNode
}) {
  return (
    <section className={styles.resume} aria-label="Résumé avant validation">
      <dl className={styles.lignes}>
        {lignes.map(([libelle, valeur]) => (
          <div key={libelle} className={styles.ligne}>
            <dt>{libelle}</dt>
            <dd>{valeur}</dd>
          </div>
        ))}
      </dl>
      <div className={styles.gestes}>{children}</div>
    </section>
  )
}
