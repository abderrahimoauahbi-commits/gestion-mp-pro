/**
 * « Bilan du mois » (ECRANS-PRO partie 8, document `GET documents/bilan?mois=AAAA-MM`) : le mois
 * choisi — entrées, sorties, stock de début et de fin, production, achats — sur le papier à
 * en-tête, dans un nouvel onglet. Mois précédent par défaut ; le mois en cours au plus (un mois à
 * venir n'a pas de bilan, P8-24) ; grisé avec sa raison tant que le mois n'est pas lisible.
 * Direction et achats (en-tête de l'Analyse) ; le Cockpit (lot F1) peut le reprendre tel quel.
 */
import { useId, useState } from 'react'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Bouton } from '../../composants/saisie/Bouton'
import { moisCourant } from '../../lib/heure'
import styles from './analyse.module.css'

/** Le mois d'avant « AAAA-MM ». */
export function moisPrecedent(mois: string): string {
  const [a, m] = mois.split('-').map(Number)
  if (!a || !m) return mois
  return m === 1 ? `${a - 1}-12` : `${a}-${String(m - 1).padStart(2, '0')}`
}

/** Pourquoi ce mois n'a pas de bilan (`''` s'il en a un). */
export function raisonMois(mois: string, courant: string): string {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(mois)) return 'Choisir un mois (AAAA-MM, de 01 à 12).'
  if (mois > courant) return 'Le bilan d’un mois à venir n’existe pas encore.'
  return ''
}

export function BilanDuMois() {
  const courant = moisCourant()
  const [mois, setMois] = useState(() => moisPrecedent(courant))
  const id = useId()
  const raison = raisonMois(mois, courant)
  const titre =
    'Le bilan du mois choisi — entrées, sorties, stock de début et de fin, production, achats — dans une page à imprimer'
  return (
    <span className={styles.bilan}>
      <label htmlFor={id} className={styles.note}>
        Mois
      </label>
      <input
        id={id}
        type="month"
        value={mois}
        max={courant}
        title="Le mois du bilan"
        onChange={(e) => setMois(e.target.value)}
      />
      {raison ? (
        <Bouton grise={raison}>Bilan du mois</Bouton>
      ) : (
        <BoutonImprimer
          route="/documents/bilan"
          parametres={{ mois }}
          libelle="Bilan du mois"
          titre={titre}
        />
      )}
    </span>
  )
}
