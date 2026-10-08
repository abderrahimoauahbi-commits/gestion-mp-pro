/**
 * Écrans du domaine « Inventaire » (lot F6), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F6 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/inventaire',
    titre: 'Inventaire',
    groupe: 'Stock',
    roles: ['direction', 'achats'],
    aide: 'inventaire',
    onglets: [
      { cle: 'cours', libelle: 'En cours' },
      { cle: 'passes', libelle: 'Inventaires clos' },
    ],
    lot: 'F6',
    page: aVenir,
  },
  {
    chemin: '/inventaires/nouveau',
    titre: 'Ouvrir un inventaire',
    parent: '/inventaire',
    roles: ['direction', 'achats'],
    aide: 'inventaire',
    lot: 'F6',
    page: aVenir,
  },
]
