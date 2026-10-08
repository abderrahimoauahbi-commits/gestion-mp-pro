/**
 * Une tuile de l'accueil de l'atelier : un geste par tuile (Envoyer aux machines, Retour des
 * machines…), grande cible, un compte quand il dit quelque chose (« 2 brouillons »). `Tuiles` les
 * range par deux ; à 360 × 640, toutes restent visibles.
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import type { Ton } from '../../lib/statuts'
import { classes } from '../mise-en-page/classes'
import { Icone, type NomIcone } from '../mise-en-page/Icone'
import styles from './Tuile.module.css'

export function Tuile({
  titre,
  detail,
  vers,
  icone,
  ton,
}: {
  titre: string
  detail?: ReactNode
  vers: string
  icone?: NomIcone
  ton?: Ton
}) {
  return (
    <Link to={vers} className={classes(styles.tuile, ton && styles[ton])}>
      {icone ? <Icone nom={icone} taille={26} /> : null}
      <span className={styles.titre}>{titre}</span>
      {detail ? <span className={styles.detail}>{detail}</span> : null}
    </Link>
  )
}

export function Tuiles({ children }: { children: ReactNode }) {
  return (
    <nav className={styles.tuiles} aria-label="Gestes de l’atelier">
      {children}
    </nav>
  )
}
