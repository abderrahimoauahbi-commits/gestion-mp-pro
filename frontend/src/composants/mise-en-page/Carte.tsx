/**
 * Une carte : un titre, des actions à place fixe à droite (REGLES-ECRAN § 3, « boutons à place
 * fixe »), un corps. `remplir` : la carte prend la hauteur qui reste dans la page (le `Cadre`
 * de son tableau la mesure) ; `serre` : corps sans marge (un tableau bord à bord) ; `ton` : un
 * filet de couleur à gauche (fiche d'alerte ou conforme, à l'atelier).
 */
import type { ReactNode } from 'react'

import type { Ton } from '../../lib/statuts'
import { classes } from './classes'
import styles from './Carte.module.css'

export interface CarteProps {
  titre?: ReactNode
  sous?: ReactNode
  actions?: ReactNode
  children?: ReactNode
  serre?: boolean
  remplir?: boolean
  ton?: Ton
  className?: string
}

export function Carte({ titre, sous, actions, children, serre, remplir, ton, className }: CarteProps) {
  return (
    <section
      className={classes(styles.carte, remplir && styles.remplir, ton && styles[`ton-${ton}`], className)}
    >
      {titre || actions ? (
        <header className={styles.entete}>
          <div className={styles.titres}>
            {titre ? <h2>{titre}</h2> : null}
            {sous ? <p className={styles.sous}>{sous}</p> : null}
          </div>
          {actions ? <div className={styles.actions}>{actions}</div> : null}
        </header>
      ) : null}
      <div className={classes(styles.corps, serre && styles.serre)}>{children}</div>
    </section>
  )
}
