/**
 * La recherche qui affine à la frappe (A6, M24, M71) : plusieurs mots, dans n'importe quel ordre,
 * sans accents ni majuscules. Elle **garde le focus** pendant la frappe : c'est un champ
 * contrôlé qui ne se recrée jamais (Gestion MP le perdait quand la liste se relisait). Échap
 * efface une recherche posée (sans fermer la fenêtre autour).
 */
import { useRef, useState } from 'react'

import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './Recherche.module.css'

export const INVITE_RECHERCHE = 'Rechercher : plusieurs mots, dans n’importe quel ordre'

/**
 * Le texte tapé s'affiche **tout de suite**, même si la page le range dans l'adresse en différé
 * (le routeur écrit l'adresse dans une transition : sans ce relais, des lettres tapées vite
 * arrivaient en retard). Une valeur venue d'ailleurs (« Effacer les filtres ») est reprise ; celles
 * qui reviennent de notre propre frappe ne la réécrivent pas.
 */
function useTexteImmediat(valeur: string, onChange: (v: string) => void) {
  const [texte, setTexte] = useState(valeur)
  const [vu, setVu] = useState(valeur)
  const attendu = useRef<string | null>(null)
  if (valeur !== vu) {
    setVu(valeur)
    if (attendu.current === null) setTexte(valeur)
    else if (valeur === attendu.current) attendu.current = null
  }
  const changer = (v: string) => {
    setTexte(v)
    attendu.current = v
    onChange(v)
  }
  return { valeur: texte, changer }
}

export function Recherche({
  valeur,
  onChange,
  placeholder = INVITE_RECHERCHE,
  libelle = 'Rechercher',
  className,
}: {
  valeur: string
  onChange: (valeur: string) => void
  placeholder?: string
  libelle?: string
  className?: string
}) {
  const texte = useTexteImmediat(valeur, onChange)
  return (
    <span className={classes(styles.recherche, className)}>
      <Icone nom="recherche" className={styles.icone} />
      <input
        type="search"
        className={styles.champ}
        value={texte.valeur}
        placeholder={placeholder}
        aria-label={libelle}
        autoComplete="off"
        spellCheck={false}
        onChange={(e) => texte.changer(e.target.value)}
        onKeyDown={(e) => {
          if (e.key !== 'Escape' || !valeur) return
          e.preventDefault()
          e.stopPropagation()
          e.nativeEvent.stopImmediatePropagation()
          texte.changer('')
        }}
      />
    </span>
  )
}
