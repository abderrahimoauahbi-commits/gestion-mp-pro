/**
 * Écrans du domaine « Importations & coût de revient » (lot F5), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F5 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/importations',
    titre: 'Importations & coût de revient',
    groupe: 'Achats',
    roles: ['direction', 'achats'],
    aide: 'importations',
    onglets: [
      { cle: 'ouverts', libelle: 'Dossiers ouverts' },
      { cle: 'clos', libelle: 'Dossiers clos' },
      { cle: 'rattacher', libelle: 'En attente de dossier' },
    ],
    lot: 'F5',
    page: aVenir,
  },
]
