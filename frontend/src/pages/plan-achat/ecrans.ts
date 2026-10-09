/**
 * Écrans du domaine « Plan d'achat » (lot F4), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F4 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/plan-achat',
    titre: 'Plan d’achat',
    groupe: 'Achats',
    roles: ['direction', 'achats'],
    aide: 'plan_achat',
    onglets: [
      { cle: 'fournisseurs', libelle: 'Par fournisseur' },
      { cle: 'references', libelle: 'Références à commander' },
    ],
    lot: 'F4',
    page: aVenir,
  },
]
