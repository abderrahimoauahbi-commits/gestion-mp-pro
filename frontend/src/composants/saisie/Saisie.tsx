/** Une ligne de texte (nom, référence, motif court). Posée dans un `Champ`, elle en prend le nom. */
import { classes } from '../mise-en-page/classes'
import { attributsDuChamp, useChamp } from './Champ'
import styles from './controle.module.css'

export interface SaisieProps {
  valeur: string
  onChange: (valeur: string) => void
  type?: 'text' | 'email' | 'tel' | 'search' | 'password'
  placeholder?: string
  max?: number
  desactive?: boolean
  autoFocus?: boolean
  /** Le nom accessible hors d'un `Champ`. */
  libelle?: string
  autoComplete?: string
  className?: string
}

export function Saisie({
  valeur,
  onChange,
  type = 'text',
  placeholder,
  max,
  desactive,
  autoFocus,
  libelle,
  autoComplete,
  className,
}: SaisieProps) {
  const liens = useChamp()
  return (
    <input
      {...attributsDuChamp(liens, undefined, libelle)}
      type={type}
      className={classes(styles.controle, className)}
      value={valeur}
      maxLength={max}
      placeholder={placeholder}
      disabled={desactive}
      autoFocus={autoFocus}
      autoComplete={autoComplete ?? 'off'}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
