/**
 * Écrans du domaine « Stock, lots & mouvements » (lot F2), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F2 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/stock',
    titre: 'Stock, lots & mouvements',
    groupe: 'Tous les jours',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'stock',
    onglets: [
      { cle: 'matieres', libelle: 'Par matière' },
      { cle: 'lots', libelle: 'Lots' },
      { cle: 'mouvements', libelle: 'Mouvements de stock' },
      { cle: 'ordres', libelle: 'Ordres de fabrication' },
      { cle: 'a-valider', libelle: 'À valider' },
    ],
    lot: 'F2',
    page: aVenir,
  },
  {
    chemin: '/lots/:id',
    titre: 'Fiche de lot',
    parent: '/stock',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'lot',
    lot: 'F2',
    page: aVenir,
  },
  {
    chemin: '/tracabilite',
    titre: 'Suivi de traçabilité',
    parent: '/stock',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'tracabilite',
    lot: 'F2',
    page: aVenir,
  },
]
