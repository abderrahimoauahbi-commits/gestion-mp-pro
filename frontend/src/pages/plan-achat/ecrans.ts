/**
 * Écrans du domaine « Plan d'achat » (lot F4), rassemblés par `routes.ts`. La préparation s'ouvre
 * en fenêtre par-dessus le plan, à adresse stable (même page).
 */
import type { Ecran } from '../../routes'

const page = () => import('./PlanAchat')

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
    page,
  },
  {
    chemin: '/plan-achat/preparer/:fournisseurId',
    titre: 'Préparer une commande',
    parent: '/plan-achat',
    roles: ['direction', 'achats'],
    aide: 'preparation',
    page,
  },
]
