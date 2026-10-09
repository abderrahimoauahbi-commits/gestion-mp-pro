/**
 * Écrans du domaine « Ma journée » (lot F1), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F1 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/accueil',
    titre: 'Ma journée',
    groupe: 'Tous les jours',
    roles: ['achats', 'alimentation'],
    aide: 'accueil',
    lot: 'F1',
    page: aVenir,
  },
]
