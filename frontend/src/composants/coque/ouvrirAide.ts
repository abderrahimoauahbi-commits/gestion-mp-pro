/**
 * Ouvrir l'aide de l'écran (« ? » de l'en-tête, « Aide de l'écran » du menu du compte) : la coque
 * fournit l'ouverture ; hors coque (page publique, essai), rien ne s'ouvre.
 */
import { createContext, useContext } from 'react'

import type { CleAide } from '../../routes'

export type OuvrirAide = (cle?: CleAide) => void

export const ContexteAide = createContext<OuvrirAide | null>(null)

/** La fonction qui ouvre l'aide (celle de l'écran courant sans argument), ou `null` hors coque. */
export function useOuvrirAide(): OuvrirAide | null {
  return useContext(ContexteAide)
}
