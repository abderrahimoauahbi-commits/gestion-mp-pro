/**
 * Écrans du domaine « Sorties vers les machines » (lot F2), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F2 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/sorties',
    titre: 'Sorties vers les machines',
    groupe: 'Tous les jours',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'sorties',
    onglets: [
      { cle: 'valide', libelle: 'Validés' },
      { cle: 'brouillon', libelle: 'Brouillons' },
      { cle: 'annule', libelle: 'Annulés' },
    ],
    lot: 'F2',
    page: aVenir,
  },
  {
    chemin: '/ordres/nouveau',
    titre: 'Nouvelle sortie',
    parent: '/sorties',
    roles: ['direction', 'alimentation'],
    aide: 'sorties',
    lot: 'F2',
    page: aVenir,
  },
]
