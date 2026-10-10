/**
 * Écrans du domaine « Production & besoins » (lot F2), rassemblés par `routes.ts`. D'où vient le
 * besoin d'une matière s'ouvre en fenêtre par-dessus l'onglet des besoins (même page, adresse stable).
 */
import type { Ecran } from '../../routes'

const page = () => import('./Production')

export const ecrans: readonly Ecran[] = [
  {
    chemin: '/production',
    titre: 'Production & besoins',
    groupe: 'Référentiels',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'production',
    onglets: [
      { cle: 'plan', libelle: 'Plan de production' },
      { cle: 'glissant', libelle: 'Plan glissant' },
      { cle: 'realise', libelle: 'Plan et réalisé' },
      { cle: 'besoins', libelle: 'Besoins matière' },
    ],
    page,
  },
  {
    chemin: '/production/besoins/:matiereId',
    titre: 'Besoin d’une matière',
    parent: '/production',
    roles: ['direction', 'achats', 'alimentation'],
    aide: 'production',
    page,
  },
]
