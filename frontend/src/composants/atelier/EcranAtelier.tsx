/**
 * Le gabarit d'un écran de l'atelier au téléphone (A9) : en-tête collant à la couleur de la
 * marque avec « ‹ » (44 × 44, « Retour » : l'adresse donnée, sinon la page précédente) et le
 * titre ; un bandeau (`enTete` : les blocages) ; le corps en colonne, 720 px au plus ; un pied
 * collant (`pied` : le résumé de validation) ; la barre du bas. Aucun débordement à 360 px.
 */
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { Icone } from '../mise-en-page/Icone'
import { BarreBas } from './BarreBas'
import styles from './EcranAtelier.module.css'

export interface EcranAtelierProps {
  titre: string
  /** Où mène « ‹ » ; absent : la page précédente ; `false` : pas de retour (l'accueil). */
  retour?: string | false
  enTete?: ReactNode
  pied?: ReactNode
  children: ReactNode
  sansBarre?: boolean
}

export function EcranAtelier({ titre, retour, enTete, pied, children, sansBarre }: EcranAtelierProps) {
  const naviguer = useNavigate()
  return (
    <div className={styles.ecran}>
      <header className={styles.entete}>
        {retour === false ? (
          <span className={styles.place} />
        ) : (
          <button
            type="button"
            className={styles.retour}
            aria-label="Retour"
            onClick={() => (retour ? naviguer(retour) : naviguer(-1))}
          >
            <Icone nom="precedent" taille={22} />
          </button>
        )}
        <h1 className={styles.titre}>{titre}</h1>
      </header>
      {enTete}
      <main className={styles.corps}>{children}</main>
      {pied ? <div className={styles.pied}>{pied}</div> : null}
      {sansBarre ? null : <BarreBas />}
    </div>
  )
}
