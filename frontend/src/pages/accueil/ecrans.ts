/**
 * Écrans du domaine « Ma journée » (lot F1), rassemblés par `routes.ts`. La fenêtre d'un besoin
 * signalé s'ouvre par l'adresse (`/accueil?signalement=ID`), sur la même page.
 */
import type { Ecran } from '../../routes'

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/accueil',
    titre: 'Ma journée',
    groupe: 'Tous les jours',
    roles: ['achats', 'alimentation'],
    aide: 'accueil',
    page: () => import('./Accueil'),
  },
]
