/**
 * Écrans du domaine « Opérations de stock » (lot F6), rassemblés par `routes.ts` : la liste à cinq
 * onglets (l'alimentation : transferts et retours des machines) et la fenêtre d'une opération à
 * adresse stable, `/operations/nouvelle?type=` et `/operations/:id`. Les trois chemins mènent à la
 * même page (la liste dessous).
 */
import type { Ecran } from '../../routes'

const page = () => import('./Operations')
const roles = ['direction', 'achats', 'alimentation'] as const

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/operations',
    titre: 'Ouvertures, transferts, ajustements',
    groupe: 'Stock',
    detail: 'Ouvertures, transferts, ajustements, retours au fournisseur et retours des machines',
    roles,
    aide: 'operations',
    onglets: [
      { cle: 'ouverture', libelle: 'Stock d’ouverture', roles: ['direction', 'achats'] },
      { cle: 'transfert', libelle: 'Transferts' },
      { cle: 'ajustement', libelle: 'Ajustements', roles: ['direction', 'achats'] },
      {
        cle: 'retour_fournisseur',
        libelle: 'Retours au fournisseur',
        court: 'Retours fournisseur',
        roles: ['direction', 'achats'],
      },
      { cle: 'retour_machine', libelle: 'Retours des machines', court: 'Retours machine' },
    ],
    page,
  },
  {
    chemin: '/operations/nouvelle',
    titre: 'Nouvelle opération',
    parent: '/operations',
    roles,
    aide: 'operations',
    page,
  },
  {
    chemin: '/operations/:id',
    titre: 'Opération',
    parent: '/operations',
    roles,
    aide: 'operations',
    page,
  },
]
