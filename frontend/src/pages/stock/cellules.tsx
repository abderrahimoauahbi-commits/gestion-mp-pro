/**
 * Les cellules communes des listes du stock, des sorties et de la production : des kilos sans
 * unité (elle est dans l'en-tête), discrets quand ils sont nuls, rouges quand ils sont négatifs,
 * avec les mètres d'un cuir, de franges, d'un ruban dessous, à titre indicatif ; une quantité
 * signée (« +12,5 », vert ou rouge) ; une liste trop longue pour une cellule.
 */
import type { ReactNode } from 'react'

import { classes } from '../../composants/mise-en-page/classes'
import { metres, nombre, VIDE } from '../../lib/format'
import styles from './stock.module.css'
import { POUSSIERE } from './types'

/** Des kilos dans une cellule : jusqu'à deux décimales sans zéros inutiles (« 1 234,5 », « 3,15 »),
 * « 0 » grisé, « −3,2 » en rouge, « ≈ 1 020 ml » dessous. `d` fige un nombre exact de décimales
 * (le cockpit arrondit à l'entier, `d={0}`). */
export function Kg({ v, kgParMl, d }: { v: number | null | undefined; kgParMl?: number | null; d?: number }) {
  if (v == null) return <span className={styles.nul}>{VIDE}</span>
  if (Math.abs(v) < POUSSIERE) return <span className={styles.nul}>0</span>
  const m = kgParMl ? metres(v, kgParMl) : ''
  return (
    <span className={classes(v < 0 && styles.negatif)}>
      {d == null ? nombre(v, 0, 2) : nombre(v, d)}
      {m ? <span className={styles.dessous}>{m}</span> : null}
    </span>
  )
}

/** Une quantité signée : « +12,5 » en vert, « −3,15 » en rouge ; un transfert reste neutre. */
export function Signe({ v, neutre }: { v: number; neutre?: boolean }) {
  const texte = nombre(v, 0, 2)
  return (
    <span className={classes(!neutre && (v < 0 ? styles.negatif : styles.positif))}>
      {v > 0 && !neutre ? `+${texte}` : texte}
    </span>
  )
}

/** Une liste dans une cellule : deux valeurs écrites, au-delà leur nombre et le détail au survol. */
export function Liste({
  valeurs,
  nom,
  vide = VIDE,
}: {
  valeurs: readonly string[]
  nom: string
  vide?: string
}) {
  if (!valeurs.length) return <span className={styles.nul}>{vide}</span>
  if (valeurs.length <= 2) return <span className={styles.note}>{valeurs.join(' · ')}</span>
  return (
    <span className={styles.note} title={valeurs.join(' · ')}>
      {valeurs.length} {nom}
    </span>
  )
}

/** Un texte principal et sa note dessous (référence et rôle, date et heure de saisie…). */
export function Double({ haut, bas, mono }: { haut: ReactNode; bas?: ReactNode; mono?: boolean }) {
  return (
    <span className={styles.double}>
      <span className={classes(styles.fort, mono && styles.mono)}>{haut}</span>
      {bas ? <span className={styles.dessous}>{bas}</span> : null}
    </span>
  )
}
