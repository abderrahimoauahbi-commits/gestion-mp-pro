/**
 * Les champs d'une rangée, alignés (M06, M44) : une grille de 1 à 4 colonnes égales, les champs
 * alignés sur leur bas (un libellé sur deux lignes ne fait pas monter son champ). Un `Champ large`
 * prend toute la rangée.
 */
import type { ReactNode } from 'react'

import { classes } from './classes'
import styles from './Grille.module.css'

export function Grille({
  colonnes = 2,
  children,
  className,
}: {
  colonnes?: 1 | 2 | 3 | 4
  children: ReactNode
  className?: string
}) {
  return <div className={classes(styles.grille, styles[`c${colonnes}`], className)}>{children}</div>
}
