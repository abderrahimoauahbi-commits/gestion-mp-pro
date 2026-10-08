/**
 * La bulle « ? » d'un indicateur : la formule de son calcul (une seule source, `aide.json`,
 * clés `formule.<cle>`). Elle s'ouvre au survol, au focus, et au doigt (toucher la bascule).
 */
import { useId, useState } from 'react'

import { classes } from '../mise-en-page/classes'
import styles from './Formule.module.css'

export function Formule({ texte, de }: { texte: string; de?: string }) {
  const id = useId()
  const [ouverte, setOuverte] = useState(false)
  return (
    <span className={classes(styles.formule, ouverte && styles.ouverte)}>
      <button
        type="button"
        className={styles.bouton}
        aria-label={de ? `Formule : ${de}` : 'Formule'}
        aria-describedby={id}
        aria-expanded={ouverte}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setOuverte(!ouverte)
        }}
        onBlur={() => setOuverte(false)}
      >
        ?
      </button>
      <span id={id} role="tooltip" className={styles.bulle}>
        {texte}
      </span>
    </span>
  )
}
