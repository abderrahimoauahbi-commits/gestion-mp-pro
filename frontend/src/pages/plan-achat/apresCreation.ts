/**
 * Après la création d'un ou de plusieurs bons depuis la préparation : ce que dit l'écran, et où il
 * mène (le bon seul, ou les brouillons) — que la préparation vienne du plan d'achat ou des commandes.
 */
import { useCallback } from 'react'
import { useNavigate } from 'react-router'

import { dire } from '../../composants/retour/Messages'
import type { CommandeCreee } from './types'

export function apresCreation(bons: readonly CommandeCreee[]): { texte: string; adresse: string } {
  const premier = bons[0]
  if (bons.length === 1 && premier)
    return {
      texte:
        'Bon de commande créé en brouillon, sans numéro tant qu’il n’est pas envoyé. Relisez-le, imprimez-le et envoyez-le depuis l’écran Commandes.',
      adresse: `/commandes/${premier.id}`,
    }
  return {
    texte: `${bons.length} bons de commande créés en brouillon (un par devise : ${bons.map((b) => b.devise).join(', ')}), sans numéro tant qu’ils ne sont pas envoyés. Relisez-les, imprimez-les et envoyez-les.`,
    adresse: '/commandes?onglet=brouillon',
  }
}

/** Dit la création et mène aux bons créés. */
export function useApresCreation() {
  const navigate = useNavigate()
  return useCallback(
    (bons: CommandeCreee[]) => {
      const { texte, adresse } = apresCreation(bons)
      dire(texte)
      navigate(adresse)
    },
    [navigate],
  )
}
