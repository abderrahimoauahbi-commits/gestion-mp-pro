/**
 * Un choix dans un référentiel court (couleur, composition) : les valeurs en puces, les plus
 * utiles d'abord, « + N autres » pour tout voir ; toucher la valeur choisie la retire ; `libre` :
 * « Autre… » pour une valeur nouvelle (Entrée l'ajoute, Échap renonce sans fermer la fenêtre).
 */
import { useState } from 'react'

import { nombre } from '../../lib/format'
import { classes } from '../mise-en-page/classes'
import { useChamp } from './Champ'
import styles from './Puces.module.css'

export interface PucesProps {
  valeur: string
  options: readonly string[]
  onChange: (valeur: string) => void
  libre?: boolean
  max?: number
  libelle?: string
}

/** « Autre… » : une valeur nouvelle, Entrée l'ajoute, Échap renonce sans fermer la fenêtre autour. */
function NouvelleValeur({ onValeur, onRenoncer }: { onValeur: (v: string) => void; onRenoncer: () => void }) {
  const [texte, setTexte] = useState('')
  return (
    <input
      className={styles.nouvelle}
      autoFocus
      value={texte}
      aria-label="Nouvelle valeur"
      placeholder="Nouvelle valeur, puis Entrée"
      onChange={(e) => setTexte(e.target.value)}
      onBlur={onRenoncer}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && texte.trim()) {
          e.preventDefault()
          onValeur(texte.trim())
        } else if (e.key === 'Escape') {
          e.stopPropagation()
          e.nativeEvent.stopImmediatePropagation()
          onRenoncer()
        }
      }}
    />
  )
}

export function Puces({ valeur, options, onChange, libre, max = 12, libelle }: PucesProps) {
  const liens = useChamp()
  const [tout, setTout] = useState(false)
  const [autre, setAutre] = useState(false)
  const base = !valeur || options.includes(valeur) ? options : [valeur, ...options]
  const vues = tout ? base : base.slice(0, max)
  const reste = base.length - vues.length
  return (
    <div
      className={styles.puces}
      role="group"
      aria-label={libelle ?? undefined}
      aria-labelledby={libelle ? undefined : liens?.libelleId}
    >
      {vues.map((o) => (
        <button
          key={o}
          type="button"
          aria-pressed={valeur === o}
          className={classes(styles.puce, valeur === o && styles.actif)}
          onClick={() => onChange(valeur === o ? '' : o)}
        >
          {o}
        </button>
      ))}
      {reste > 0 ? (
        <button type="button" className={classes(styles.puce, styles.plus)} onClick={() => setTout(true)}>
          + {nombre(reste)} {reste > 1 ? 'autres' : 'autre'}
        </button>
      ) : null}
      {libre && autre ? (
        <NouvelleValeur
          onValeur={(v) => {
            onChange(v)
            setAutre(false)
          }}
          onRenoncer={() => setAutre(false)}
        />
      ) : null}
      {libre && !autre ? (
        <button type="button" className={classes(styles.puce, styles.plus)} onClick={() => setAutre(true)}>
          Autre…
        </button>
      ) : null}
    </div>
  )
}
