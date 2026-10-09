/**
 * Une tuile de l'accueil de l'atelier : un geste par tuile (Envoyer aux machines, Retour des
 * machines…), grande cible, un compte quand il dit quelque chose (« 2 brouillons »). `Tuiles` les
 * range par deux ; la tuile `principale` prend toute la largeur ; à 360 × 640, toutes restent
 * visibles au-dessus de la barre du bas (icône à côté du titre, détails courts : deux lignes au
 * plus).
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
  principale = false,
}: {
  titre: string
  detail?: ReactNode
  vers: string
  icone?: NomIcone
  ton?: Ton
  /** Le geste principal de l'écran, sur toute la largeur. */
  principale?: boolean
}) {
  return (
    <Link to={vers} className={classes(styles.tuile, ton && styles[ton], principale && styles.principale)}>
      <span className={styles.tete}>
        {icone ? <Icone nom={icone} taille={22} /> : null}
        <span className={styles.titre}>{titre}</span>
      </span>
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
