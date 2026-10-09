/**
 * La question posée avant de quitter une saisie non enregistrée (`garde.ts`) : en haut de
 * l'écran, au-dessus des fenêtres. Posé une fois, à la racine de l'application (routeur de
 * données : `useBlocker` y retient « Précédent » et « Suivant »).
 */
import { useEffect, useState } from 'react'
import { useBlocker, useLocation, useNavigate } from 'react-router'

import { QUESTION_ABANDON } from '../mise-en-page/Fenetre'
import { Bouton } from '../saisie/Bouton'
import { ecouterDemandes, lienRetenu, saisieEnCours } from './garde'
import styles from './GardeNavigation.module.css'

export function GardeNavigation() {
  const naviguer = useNavigate()
  const { pathname } = useLocation()
  const [demande, setDemande] = useState<(() => void) | null>(null)
  // « Précédent » et « Suivant » (POP) vers une autre page : retenus tant qu'une saisie est en cours.
  const bloqueur = useBlocker(
    ({ currentLocation, nextLocation, historyAction }) =>
      historyAction === 'POP' && saisieEnCours() && currentLocation.pathname !== nextLocation.pathname,
  )
  useEffect(() => ecouterDemandes((action) => setDemande(() => action)), [])
  // Un clic sur un lien de l'application : retenu, puis suivi après « Oui, abandonner ».
  useEffect(() => {
    const clic = (e: MouseEvent) => {
      if (!saisieEnCours()) return
      const vers = lienRetenu(e, pathname)
      if (!vers) return
      e.preventDefault()
      e.stopPropagation()
      setDemande(() => () => naviguer(vers))
    }
    document.addEventListener('click', clic, true)
    return () => document.removeEventListener('click', clic, true)
  }, [naviguer, pathname])
  const bloque = bloqueur.state === 'blocked'
  if (!bloque && !demande) return null
  const non = () => {
    if (bloqueur.state === 'blocked') bloqueur.reset()
    setDemande(null)
  }
  const oui = () => {
    if (bloqueur.state === 'blocked') bloqueur.proceed()
    const action = demande
    setDemande(null)
    action?.()
  }
  return (
    <div className={styles.garde} role="alertdialog" aria-label="Saisie non enregistrée">
      <span className={styles.question}>{QUESTION_ABANDON}</span>
      <Bouton onClick={non}>Non, continuer la saisie</Bouton>
      <Bouton variante="danger" onClick={oui}>
        Oui, abandonner
      </Bouton>
    </div>
  )
}
