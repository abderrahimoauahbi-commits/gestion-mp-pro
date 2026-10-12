/**
 * « Agrandir » un tableau : le tableau entier (recherche, filtres, lignes) passe en plein écran
 * par-dessus la page ou la fenêtre, avec les mêmes champs (on y coche, on y saisit), puis
 * « Réduire » (ou Échap) le remet à sa place. Sous un en-tête chargé ou dans une fenêtre, un
 * tableau n'a que la place qui reste : ce geste donne de quoi lire et choisir à l'aise.
 */
import { useEffect, useRef, useState } from 'react'

import styles from './Agrandir.module.css'

export function useAgrandir<E extends HTMLElement>() {
  const boite = useRef<E>(null)
  const [grand, setGrand] = useState(false)
  useEffect(() => {
    if (!grand) return
    // Échap réduit le tableau sans fermer la fenêtre qui le porte (écouté avant elle).
    const clavier = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      setGrand(false)
    }
    window.addEventListener('keydown', clavier, true)
    return () => window.removeEventListener('keydown', clavier, true)
  }, [grand])
  const bouton = (
    <button
      type="button"
      className={grand ? styles.reduire : styles.agrandir}
      onClick={() => setGrand((g) => !g)}
      title={grand ? 'Remettre le tableau à sa place (Échap)' : 'Ouvrir le tableau en grand'}
      aria-pressed={grand}
    >
      {grand ? '✕ Réduire' : '⤢ Agrandir'}
    </button>
  )
  return { boite, grand, classe: grand ? styles.grand : undefined, bouton }
}
