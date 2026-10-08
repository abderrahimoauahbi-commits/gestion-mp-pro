/**
 * L'écran du registre que sert l'adresse courante : chaque route d'écran porte `handle: {ecran}`
 * (App.tsx) ; le fil d'Ariane, le menu actif, le « ? » et la page « à venir » le lisent ici.
 */
import { useMatches } from 'react-router'

import type { Ecran } from '../../routes'

export interface PoigneeEcran {
  ecran: Ecran
}

function estPoignee(h: unknown): h is PoigneeEcran {
  return typeof h === 'object' && h !== null && 'ecran' in h
}

/** L'écran courant (le plus profond qui en déclare un), ou `null` hors registre. */
export function useEcranCourant(): Ecran | null {
  const correspondances = useMatches()
  for (let i = correspondances.length - 1; i >= 0; i--) {
    const poignee = correspondances[i]?.handle
    if (estPoignee(poignee)) return poignee.ecran
  }
  return null
}
