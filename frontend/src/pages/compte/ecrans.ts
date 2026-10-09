/** L'écran « Mon compte » (lot E2), rassemblé par `routes.ts` : hors menu, ouvert par le menu du compte. */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/compte',
    titre: 'Mon compte',
    roles: ['direction', 'achats', 'alimentation', 'administrateur'],
    aide: 'compte',
    page: () => import('./MonCompte'),
  },
]
