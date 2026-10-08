/** Un texte de plusieurs lignes (observations, motif) ; compteur quand une longueur maximale est donnée. */
import { useId } from 'react'

import { nombre } from '../../lib/format'
import { classes } from '../mise-en-page/classes'
import { attributsDuChamp, useChamp } from './Champ'
import styles from './controle.module.css'

export interface ZoneProps {
  valeur: string
  onChange: (valeur: string) => void
  lignes?: number
  max?: number
  placeholder?: string
  desactive?: boolean
  libelle?: string
  autoFocus?: boolean
}

export function Zone({
  valeur,
  onChange,
  lignes = 3,
  max,
  placeholder,
  desactive,
  libelle,
  autoFocus,
}: ZoneProps) {
  const liens = useChamp()
  const id = useId()
  return (
    <>
      <textarea
        {...attributsDuChamp(liens, max ? id : undefined, libelle)}
        className={classes(styles.controle, styles.zone)}
        rows={lignes}
        value={valeur}
        maxLength={max}
        placeholder={placeholder}
        disabled={desactive}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
      />
      {max ? (
        <span id={id} className={styles.note}>
          {nombre(valeur.length)} / {nombre(max)} caractères
        </span>
      ) : null}
    </>
  )
}
