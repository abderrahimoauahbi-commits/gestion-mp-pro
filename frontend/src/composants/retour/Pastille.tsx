/**
 * La pastille d'un compteur (menu, onglet) : elle garde la largeur de son nombre (M76 : le « 3 »
 * rogné), chiffres tabulaires ; rien à zéro. Le titre dit ce qu'elle compte.
 */
import { nombre as enNombre } from '../../lib/format'
import type { Ton } from '../../lib/statuts'
import { classes } from '../mise-en-page/classes'
import styles from './Pastille.module.css'

export function Pastille({
  nombre,
  ton = 'critique',
  titre,
}: {
  nombre: number | null | undefined
  ton?: Ton
  titre: string
}) {
  if (!nombre) return null
  return (
    <span
      className={classes(styles.pastille, styles[ton])}
      title={titre}
      aria-label={`${enNombre(nombre)} — ${titre}`}
    >
      {enNombre(nombre)}
    </span>
  )
}
