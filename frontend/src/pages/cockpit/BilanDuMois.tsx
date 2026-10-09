/**
 * « Bilan du mois » dans l'en-tête du Cockpit : le mois choisi (le précédent par défaut, le mois en
 * cours au plus — l'heure de l'usine), et le document A4 du serveur (route 234) dans un nouvel
 * onglet. Le choix est une liste : un mois mal écrit ou à venir ne peut pas se choisir.
 */
import { useId, useState } from 'react'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { classes } from '../../composants/mise-en-page/classes'
import controle from '../../composants/saisie/controle.module.css'
import { mois as moisLisible } from '../../lib/format'
import { moisCourant } from '../../lib/heure'
import styles from './cockpit.module.css'

/** Les mois proposés, du plus récent (le mois en cours) au plus ancien, sur trois ans. */
export function moisProposes(courant: string, nombre = 36): string[] {
  const [a, m] = courant.split('-').map(Number)
  if (!a || !m) return []
  return Array.from({ length: nombre }, (_, i) => {
    const rang = a * 12 + (m - 1) - i
    return `${Math.floor(rang / 12)}-${String((rang % 12) + 1).padStart(2, '0')}`
  })
}

export function BilanDuMois() {
  const id = useId()
  const mois = moisProposes(moisCourant())
  const [choisi, setChoisi] = useState(mois[1] ?? mois[0] ?? '')
  return (
    <div className={styles.bilan}>
      <label htmlFor={id} className="masque-accessible">
        Le mois du bilan
      </label>
      <select
        id={id}
        className={classes(controle.controle, styles.mois)}
        value={choisi}
        title="Le mois du bilan"
        onChange={(e) => setChoisi(e.target.value)}
      >
        {mois.map((x) => (
          <option key={x} value={x}>
            {moisLisible(x)}
          </option>
        ))}
      </select>
      <BoutonImprimer
        route="/documents/bilan"
        parametres={{ mois: choisi }}
        libelle="Bilan du mois"
        titre="Le bilan du mois choisi — entrées, sorties, stock de début et de fin, production, achats — dans une page à imprimer (nouvel onglet)"
      />
    </div>
  )
}
