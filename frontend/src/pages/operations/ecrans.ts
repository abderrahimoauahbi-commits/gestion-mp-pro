/**
 * Écrans du domaine « Opérations de stock » (lot F6), rassemblés par `routes.ts`. Pré-rempli par le lot E2 avec
 * les entrées du menu (ECRANS-PRO § 2.1 et § 2.2) ; le lot F6 remplace `page` par ses pages et
 * ajoute ses fiches (docs/lots/E2.md, « Déclarer un écran »).
 */
import type { Ecran } from '../../routes'

const aVenir = () => import('../../composants/coque/EcranAVenir')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/operations',
    titre: 'Ouvertures, transferts, ajustements',
    groupe: 'Stock',
    detail: 'Ouvertures, transferts, ajustements, retours au fournisseur et retours des machines',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'operations',
    onglets: [
      { cle: 'ouverture', libelle: 'Ouvertures', roles: ['direction', 'achats'] },
      { cle: 'transfert', libelle: 'Transferts' },
      { cle: 'ajustement', libelle: 'Ajustements', roles: ['direction', 'achats'] },
      {
        cle: 'retour_fournisseur',
        libelle: 'Retours au fournisseur',
        court: 'Retours fournisseur',
        roles: ['direction', 'achats'],
      },
      { cle: 'retour_machine', libelle: 'Retours des machines' },
    ],
    lot: 'F6',
    page: aVenir,
  },
]
