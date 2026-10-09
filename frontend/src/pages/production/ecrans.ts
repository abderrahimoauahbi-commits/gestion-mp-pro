/**
 * Écrans du domaine « Production & besoins » (lot F2), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F2 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/production',
    titre: 'Production & besoins',
    groupe: 'Tous les jours',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'production',
    onglets: [
      { cle: 'plan', libelle: 'Plan de production' },
      { cle: 'glissant', libelle: 'Plan glissant' },
      { cle: 'realise', libelle: 'Plan et réalisé' },
      { cle: 'besoins', libelle: 'Besoins matière' },
    ],
    lot: 'F2',
    page: aVenir,
  },
]
