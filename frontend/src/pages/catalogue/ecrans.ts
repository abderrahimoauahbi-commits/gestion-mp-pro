/**
 * Écrans du domaine « Matières, classification, fournisseurs » (lot F7), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F7 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/catalogue',
    titre: 'Matières, classification, fournisseurs',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'catalogue',
    onglets: [
      { cle: 'matieres', libelle: 'Matières' },
      { cle: 'classification', libelle: 'Classification', roles: ['direction', 'achats'] },
      { cle: 'fournisseurs', libelle: 'Fournisseurs', roles: ['direction', 'achats'] },
    ],
    lot: 'F7',
    page: aVenir,
  },
]
