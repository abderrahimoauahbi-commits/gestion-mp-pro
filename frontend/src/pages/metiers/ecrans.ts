/**
 * Écrans du domaine « Métiers à tisser » (lot F3), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F3 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/metiers',
    titre: 'Métiers à tisser',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'metiers',
    lot: 'F3',
    page: aVenir,
  },
]
