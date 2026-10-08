/**
 * Un choix parmi quelques valeurs, toutes visibles (unité, type, sens) : un groupe de boutons
 * radio. ← → changent le choix ; seul le choix courant est dans l'ordre de tabulation. Posé dans
 * un `Champ groupe`, il est nommé par son libellé. `tactile` : cibles de 44 px (atelier).
 */
import { useRef, type KeyboardEvent } from 'react'

import { classes } from '../mise-en-page/classes'
import { useChamp } from './Champ'
import styles from './Segments.module.css'

export interface Segment<T extends string | number> {
  valeur: T
  libelle: string
  titre?: string
}

export interface SegmentsProps<T extends string | number> {
  valeur: T | null
  options: readonly Segment<T>[]
  onChange: (valeur: T) => void
  libelle?: string
  tactile?: boolean
  desactive?: boolean
}

export function Segments<T extends string | number>({
  valeur,
  options,
  onChange,
  libelle,
  tactile,
  desactive,
}: SegmentsProps<T>) {
  const liens = useChamp()
  const rangee = useRef<HTMLDivElement>(null)
  const courant = Math.max(
    0,
    options.findIndex((o) => o.valeur === valeur),
  )
  const clavier = (e: KeyboardEvent, i: number) => {
    const pas =
      e.key === 'ArrowRight' || e.key === 'ArrowDown'
        ? 1
        : e.key === 'ArrowLeft' || e.key === 'ArrowUp'
          ? -1
          : 0
    if (!pas) return
    e.preventDefault()
    const j = (i + pas + options.length) % options.length
    const o = options[j]
    if (!o) return
    onChange(o.valeur)
    rangee.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]')[j]?.focus()
  }
  return (
    <div
      ref={rangee}
      role="radiogroup"
      aria-label={libelle ?? undefined}
      aria-labelledby={libelle ? undefined : liens?.libelleId}
      className={classes(styles.segments, tactile && styles.tactile)}
    >
      {options.map((o, i) => (
        <button
          key={String(o.valeur)}
          type="button"
          role="radio"
          aria-checked={o.valeur === valeur}
          tabIndex={i === courant ? 0 : -1}
          title={o.titre}
          disabled={desactive}
          className={classes(styles.segment, o.valeur === valeur && styles.actif)}
          onClick={() => onChange(o.valeur)}
          onKeyDown={(e) => clavier(e, i)}
        >
          {o.libelle}
        </button>
      ))}
    </div>
  )
}
