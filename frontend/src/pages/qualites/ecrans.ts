/**
 * Écrans du domaine « Qualités et recettes » (lot F7), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F7 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/qualites',
    titre: 'Qualités et recettes',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'qualites',
    onglets: [
      { cle: 'qualites', libelle: 'Qualités' },
      { cle: 'nomenclature', libelle: 'Nomenclature' },
    ],
    lot: 'F7',
    page: aVenir,
  },
]
