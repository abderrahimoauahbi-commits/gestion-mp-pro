/**
 * Le bandeau d'une adresse refusée : l'écran est réservé à un autre rôle, ou l'adresse n'existe
 * pas ; on est revenu à son accueil. Il reste jusqu'à la navigation suivante (il vit dans l'état
 * de l'entrée d'historique) ; × le ferme.
 */
import { useState } from 'react'

import { Icone } from '../mise-en-page/Icone'
import styles from './EcranReserve.module.css'

/** L'état de navigation qui porte le refus (posé par la garde de route). */
export interface EtatRefus {
  refuse?: string
  inconnue?: string
}

export function texteRefus(etat: EtatRefus | null | undefined): string | null {
  if (etat?.refuse)
    return `L’écran demandé (${etat.refuse}) est réservé à un autre rôle : vous êtes revenu à votre accueil.`
  if (etat?.inconnue)
    return `L’adresse demandée (${etat.inconnue}) n’existe pas : vous êtes revenu à votre accueil.`
  return null
}

function estEtatRefus(v: unknown): v is EtatRefus {
  return typeof v === 'object' && v !== null && ('refuse' in v || 'inconnue' in v)
}

export function EcranReserve({ etat }: { etat: unknown }) {
  const texte = estEtatRefus(etat) ? texteRefus(etat) : null
  const [ferme, setFerme] = useState<string | null>(null)
  if (!texte || ferme === texte) return null
  return (
    <div className={styles.bandeau} role="alert">
      <Icone nom="info" />
      <span className={styles.texte}>{texte}</span>
      <button
        type="button"
        className={styles.fermer}
        aria-label="Fermer ce message"
        onClick={() => setFerme(texte)}
      >
        <Icone nom="croix" />
      </button>
    </div>
  )
}
