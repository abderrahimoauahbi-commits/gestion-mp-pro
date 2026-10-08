/**
 * Une note dans la page : information, attention, critique ou succès, avec son icône (la couleur
 * n'est jamais seule à parler). `uneLigne` : tenue sur une ligne, le texte entier en infobulle
 * (une méthode de calcul sous un tableau, sans prendre sa hauteur).
 */
import type { ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './Note.module.css'

export type TonNote = 'info' | 'attention' | 'critique' | 'ok'

const ICONES = { info: 'info', attention: 'attention', critique: 'attention', ok: 'coche' } as const

export function Note({
  ton = 'info',
  children,
  uneLigne,
}: {
  ton?: TonNote
  children: ReactNode
  uneLigne?: string
}) {
  return (
    <div className={classes(styles.note, styles[ton], uneLigne && styles.uneLigne)} title={uneLigne}>
      <Icone nom={ICONES[ton]} />
      <div className={styles.texte}>{children}</div>
    </div>
  )
}
